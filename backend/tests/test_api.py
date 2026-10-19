import copy, json
import pytest
from fastapi.testclient import TestClient
from backend.app import api


@pytest.fixture
def client(small, tmp_path, monkeypatch):
    cfg, d, a, p = small
    monkeypatch.setenv("SAHRA_DB", str(tmp_path / "plans.sqlite3"))
    monkeypatch.setattr(api, "initial", lambda: (cfg, d, a))
    with TestClient(api.app) as c:
        yield c


def generate(client):
    r = client.post("/api/plans", json={"solver_seconds": 0})
    assert r.status_code == 200, r.text
    return r.json()


def test_full_approval_export_flow(client):
    p = generate(client)
    assert p["state"] == "VALIDATED"
    approved = client.post(
        f"/api/plans/{p['version']}/approve",
        json={"reviewer": "Tester", "reason": "All checks reviewed"},
    )
    assert approved.status_code == 200
    v = approved.json()["version"]
    export = client.get(f"/api/plans/{v}/export")
    assert export.status_code == 200
    body = export.json()
    assert {
        "plan_date",
        "client_id",
        "hub_id",
        "assumptions",
        "routes",
        "unassigned",
        "addresses",
    } <= body.keys()
    r = body["routes"][0]
    assert {
        "route_id",
        "driver_id",
        "vehicle_id",
        "depart_hub",
        "return_hub",
        "distance_km",
        "stops",
    } <= r.keys()
    assert {"seq", "consignment_ids", "lat", "lng", "eta", "service_min"} <= r["stops"][
        0
    ].keys()
    assert "TEST1" in client.get(f"/api/plans/{v}/sheets").text
    assert (
        client.post(f"/api/plans/{v}/dispatch", json={"reviewer": "Tester"}).json()[
            "state"
        ]
        == "DISPATCHED"
    )
    assert len(client.get("/api/versions").json()) == 3


def test_invalid_edit_blocks_approval_and_repair(client, small):
    p = generate(client)
    v = p["version"]
    r = p["routes"][0]
    # Mutate canonical driver in fixture through a new generated context.
    ctx = api.context(v)
    ctx["data"]["drivers"][0]["licence_type"] = "MOTORCYCLE"
    bad = api.finalize(ctx, {"operation": "test_invalid_driver"})
    assert bad["validation"]["hard_count"] > 0
    response = client.post(
        f"/api/plans/{bad['version']}/approve", json={"reviewer": "Tester"}
    )
    assert response.status_code == 409
    repaired = api.context(bad["version"])
    repaired["data"]["drivers"][0]["licence_type"] = "BOTH"
    good = api.finalize(repaired, {"operation": "repair"})
    assert (
        client.post(
            f"/api/plans/{good['version']}/approve", json={"reviewer": "Tester"}
        ).status_code
        == 200
    )


def test_manual_stop_hold_persists_reoptimization(client):
    p = generate(client)
    held = client.post(
        f"/api/plans/{p['version']}/edit",
        json={
            "operation": "hold",
            "route_id": p["routes"][0]["route_id"],
            "reviewer": "Tester",
            "reason": "Customer not available",
        },
    ).json()
    assert held["metrics"]["planned_consignments"] == 0 and held["validation"]["valid"]
    after = client.post(
        f"/api/plans/{held['version']}/reoptimize", json={"reviewer": "Tester"}
    ).json()
    assert after["metrics"]["planned_consignments"] == 0
    assert (
        client.get(f"/api/plans/{p['version']}").json()["metrics"][
            "planned_consignments"
        ]
        == 1
    )


def test_address_review_is_auditable_and_not_truth_prefilled(client):
    p = generate(client)
    body = {
        "row_key": "consignments:2",
        "action": "MANUAL_OVERRIDE",
        "reviewer": "Tester",
        "reason": "Customer confirmed pin",
    }
    assert (
        client.post(f"/api/plans/{p['version']}/address-review", json=body).status_code
        == 422
    )
    body.update(lat=25.15, lng=55.26)
    response = client.post(f"/api/plans/{p['version']}/address-review", json=body)
    assert response.status_code == 200, response.text
    reviewed = response.json()
    assert reviewed["addresses"][0]["source"] == "MANUAL_CONFIRMATION"
    assert reviewed["validation"]["valid"] and not reviewed["routes"]
    assert client.get("/api/events").json()[0]["reviewer"] == "Tester"


@pytest.mark.parametrize(
    "kind,resource", [("driver_absence", "TD1"), ("vehicle_breakdown", "TV1")]
)
def test_absence_breakdown_hold_only_affected_route(client, kind, resource):
    p = generate(client)
    response = client.post(
        f"/api/plans/{p['version']}/exceptions",
        json={
            "kind": kind,
            "resource_id": resource,
            "reviewer": "Tester",
            "reason": "Simulation",
        },
    )
    assert response.status_code == 200, response.text
    after = response.json()
    assert not after["routes"] and after["validation"]["valid"]
    assert after["change_summary"]["affected_routes"] == ["R01"]


def test_urgent_dirty_record_quarantined(client):
    p = generate(client)
    response = client.post(
        f"/api/plans/{p['version']}/exceptions",
        json={
            "kind": "urgent",
            "consignment": {"consignment_id": "URGENT-1"},
            "reviewer": "Tester",
            "reason": "Simulation",
        },
    )
    assert response.status_code == 200, response.text
    after = response.json()
    assert after["validation"]["valid"] and len(after["unassigned"]) == 1
    ctx = api.context(after["version"])
    assert ctx["data"]["consignments"][-1]["problems"]


def test_reschedule_recomputes_and_validates(client):
    p = generate(client)
    response = client.post(
        f"/api/plans/{p['version']}/exceptions",
        json={
            "kind": "reschedule",
            "consignment_id": "TEST1",
            "slot_start": "17:00",
            "slot_end": "21:00",
            "reviewer": "Tester",
            "reason": "Customer request",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["routes"][0]["stops"][0]["eta"] == "17:00"
    assert response.json()["validation"]["valid"]


def test_unknown_version_and_input_validation(client):
    assert client.get("/api/plans/999").status_code == 404
    assert (
        client.post("/api/plans", json={"plan_date": "not-a-date"}).status_code == 422
    )
    assert client.post("/api/plans", json={"solver_seconds": -1}).status_code == 422


def test_tenant_isolation(client):
    p = generate(client)
    from backend.app import storage

    cfg, d, a = api.initial()
    cfg = copy.deepcopy(cfg)
    cfg["client_id"] = "another-tenant"
    with pytest.raises(KeyError):
        storage.load(p["version"], cfg, d)


def test_real_sample_smoke(real, tmp_path, monkeypatch):
    cfg, d, a = real
    monkeypatch.setenv("SAHRA_DB", str(tmp_path / "real.sqlite3"))
    monkeypatch.setattr(api, "initial", lambda: (cfg, d, a))
    with TestClient(api.app) as client:
        assert client.get("/api/overview").json()["counts"]["consignments"] == 432
        response = client.post("/api/plans", json={"solver_seconds": 2})
        assert response.status_code == 200, response.text
        p = response.json()
        assert p["validation"]["valid"]
        assert p["metrics"]["planned_consignments"] + len(p["unassigned"]) == 432
        assert json.loads(client.get(f"/api/plans/{p['version']}/export").text)[
            "routes"
        ]


def test_historical_replay_uses_no_future_deliveries(client):
    response = client.post(
        "/api/plans", json={"plan_date": "2026-08-01", "solver_seconds": 0}
    )
    assert response.status_code == 200, response.text
    p = response.json()
    assert not p["routes"]
    ctx = api.context(p["version"])
    assert not ctx["data"]["history"]


def test_move_reorder_and_driver_change_call_real_rebuild(client):
    from backend.app.routing import make_stops, schedule

    p = generate(client)
    ctx = api.context(p["version"])
    cfg = ctx["cfg"]
    d = ctx["data"]
    a = ctx["addresses"]
    c2 = copy.deepcopy(d["consignments"][0])
    c2.update(consignment_id="TEST2", row_key="consignments:3")
    d["consignments"].append(c2)
    a2 = copy.deepcopy(a[0])
    a2.update(
        consignment_id="TEST2",
        row_key=c2["row_key"],
        lat=25.131,
        candidates=[{"key": ["Dubai Marina", "second tower", "building"]}],
    )
    a.append(a2)
    driver2 = copy.deepcopy(d["drivers"][0])
    driver2["driver_id"] = "TD2"
    d["drivers"].append(driver2)
    vehicle2 = copy.deepcopy(d["vehicles"][0])
    vehicle2["vehicle_id"] = "TV2"
    d["vehicles"].append(vehicle2)
    stops = make_stops(d, a, cfg)
    ctx["plan"]["routes"] = [
        schedule([stops[0]], d["vehicles"][0], d["drivers"][0], cfg, p["plan_date"])
        | {"route_id": "R01"},
        schedule([stops[1]], vehicle2, driver2, cfg, p["plan_date"])
        | {"route_id": "R02"},
    ]
    two = api.finalize(ctx, {"operation": "test_fixture_two_routes"})
    assert two["validation"]["valid"]
    response = client.post(
        f"/api/plans/{two['version']}/edit",
        json={
            "operation": "move",
            "route_id": "R01",
            "target_route_id": "R02",
            "target_index": 0,
            "reviewer": "Tester",
            "reason": "Consolidate",
        },
    )
    assert response.status_code == 200, response.text
    moved = response.json()
    assert (
        len(moved["routes"]) == 1
        and len(moved["routes"][0]["stops"]) == 2
        and moved["validation"]["valid"]
    )
    response = client.post(
        f"/api/plans/{moved['version']}/edit",
        json={
            "operation": "reorder",
            "route_id": "R02",
            "stop_index": 1,
            "target_index": 0,
            "reviewer": "Tester",
            "reason": "Change sequence",
        },
    )
    assert response.status_code == 200, response.text
    reordered = response.json()
    assert reordered["validation"]["valid"]
    assert (
        reordered["routes"][0]["stops"][0]["consignment_ids"]
        == moved["routes"][0]["stops"][1]["consignment_ids"]
    )
    response = client.post(
        f"/api/plans/{reordered['version']}/edit",
        json={
            "operation": "driver",
            "route_id": "R02",
            "resource_id": "TD1",
            "reviewer": "Tester",
            "reason": "Use available compatible driver",
        },
    )
    assert response.status_code == 200, response.text
    assert (
        response.json()["validation"]["valid"]
        and response.json()["routes"][0]["driver_id"] == "TD1"
    )
