import copy, inspect, csv
from pathlib import Path
import pytest
from backend.app.core import config, norm, minute, hav, travel, read_csv
from backend.app.ingestion import ingest
from backend.app.addresses import (
    AreaAliasProvider,
    HistoricalLocationProvider,
    cluster,
    resolve_all,
    components,
)
from backend.app.routing import plan, schedule, service, make_stops, compatible
from backend.app.validation import validate
from backend.app.evaluation import evaluate


def test_exact_audit_counts(real):
    cfg, d, a = real
    assert d["raw_counts"] == {
        "consignments": 432,
        "drivers": 28,
        "vehicles": 24,
        "areas": 89,
        "delivery_history": 5856,
    }
    assert len(a) == 432


def test_duplicate_rows_preserved(real):
    _, d, _ = real
    rows = [c for c in d["consignments"] if "DUPLICATE_ID" in c["problems"]]
    assert len({c["consignment_id"] for c in rows}) == 3
    assert len(rows) == 6 and len({c["row_key"] for c in rows}) == 6
    assert all(c["disposition"] == "QUARANTINED" for c in rows)


def test_negative_weight_quarantined(real):
    _, d, _ = real
    negatives = [
        c
        for c in d["consignments"]
        if c["raw"]["weight_kg"] and float(c["raw"]["weight_kg"]) < 0
    ]
    assert negatives and all("INVALID_WEIGHT_KG" in c["problems"] for c in negatives)


def test_invalid_slots_held(real):
    _, d, _ = real
    assert any("INVALID_SLOT" in c["problems"] for c in d["consignments"])
    assert all(
        c["problems"] for c in d["consignments"] if c["raw"]["slot_start"] == "21:00"
    )


@pytest.mark.parametrize(
    "raw,expected", [("9:00 AM", 540), ("5:00 PM", 1020), ("13:00", 780)]
)
def test_time_normalization(raw, expected):
    assert minute(raw) == expected


def test_unicode_and_aliases(real):
    assert norm(" دبي  ،  Tower-2 ") == "دبي tower 2"
    provider = AreaAliasProvider(real[1]["areas"])
    assert provider.lookup("JVC")[0]["area_name"] == "Jumeirah Village Circle"
    assert provider.lookup("Al Nahda")  # May be multiple, never assume Dubai.


def test_apartment_is_not_building():
    c = components({"address_line_1": "Apt 1204", "address_line_2": "Al Noor Bldg"})
    assert (
        c["apartment"] == "1204"
        and c["building"] == "al noor building"
        and not c["villa"]
    )


def test_gps_outlier_rejected(real):
    cfg = real[0]
    obs = [
        {"point": [25.1, 55.2], "id": "H1"},
        {"point": [25.1001, 55.2001], "id": "H2"},
        {"point": [25.1002, 55.2], "id": "H3"},
        {"point": [25.4, 55.5], "id": "OUTLIER"},
    ]
    g = cluster(obs, cfg)
    assert g["support"] == 3 and g["outliers"] == ["OUTLIER"]
    assert hav(g["point"], [25.1, 55.2]) < 0.05


def test_conflicting_history_abstains(small):
    cfg, d, a, p = small
    c = d["consignments"][0]
    c.update(
        address_line_1="Flat 1",
        address_line_2="Test Tower",
        area="Dubai Marina",
        city="Dubai",
    )
    d["history"] = [
        dict(
            consignment_id=f"H{i}",
            outcome="DELIVERED",
            event_lat=str(25.08 + i * 0.003),
            event_lng="55.14",
            customer_phone=c["customer_phone"],
            address_line_1="Flat 1",
            address_line_2="Test Tower",
            area="Dubai Marina",
            city="Dubai",
            landmark="",
        )
        for i in range(4)
    ]
    preds, _ = resolve_all(d, cfg)
    assert preds[0]["quality"] == "AMBIGUOUS" and preds[0]["lat"] is None


def test_no_centroid_auto_routing(real):
    _, d, a = real
    assert all(x["source"] != "AREA_CENTROID" for x in a if x["action"] == "AUTO_ROUTE")
    assert all(x["lat"] is None for x in a if x["quality"] != "GOOD")


def test_truth_not_accessible_to_production():
    from backend.app import addresses, ingestion, routing, validation, api

    for m in [addresses, ingestion, routing, validation, api]:
        assert "true_lat" not in inspect.getsource(m)
        assert "ground_truth_sample" not in inspect.getsource(m)


def test_truth_file_isolation(real, tmp_path, monkeypatch):
    # Deny all opens of the evaluation set. Ingestion + resolution still works unchanged.
    cfg, d, a = real
    original = Path.open

    def safe(path, *args, **kwargs):
        if path.name == "ground_truth_sample.csv":
            raise AssertionError("Truth leakage")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", safe)
    rerun, _ = resolve_all(ingest(cfg), cfg)
    assert rerun == a


def test_evaluation_denominators(real):
    e = evaluate(real[2])
    assert e["samples"] == 50
    assert e["predicted"] + e["abstained"] == 50
    assert e["coverage"] == e["predicted"] / 50
    if e["predicted"]:
        assert e["within_100m_all_samples"] == pytest.approx(
            e["within_100m_among_predictions"] * e["coverage"]
        )


@pytest.mark.parametrize(
    "change,code",
    [
        ("licence", "LICENCE"),
        ("weight", "WEIGHT"),
        ("volume", "VOLUME"),
        ("cash", "CASH"),
        ("chilled", "CHILLED"),
        ("heavy", "HEAVY"),
        ("driver_status", "DRIVER_UNAVAILABLE"),
        ("vehicle_status", "VEHICLE_UNAVAILABLE"),
        ("shift", "SHIFT"),
        ("hours", "WORK_HOURS"),
        ("eta", "ETA"),
        ("window", "TIME_WINDOW"),
        ("distance", "DISTANCE"),
        ("service", "SERVICE"),
        ("return", "RETURN_TIME"),
        ("address", "ADDRESS"),
        ("unknown", "IDENTITY"),
        ("duplicate", "DUPLICATE_ASSIGNMENT"),
        ("accounting", "ACCOUNTING"),
        ("break", "BREAK"),
        ("sequence", "SEQUENCE"),
    ],
)
def test_validator_rejects_real_constraint_violations(small, change, code):
    cfg, d, a, p = small
    c = d["consignments"][0]
    v = d["vehicles"][0]
    driver = d["drivers"][0]
    r = p["routes"][0]
    s = r["stops"][0]
    if change == "licence":
        driver["licence_type"] = "MOTORCYCLE"
    elif change == "weight":
        c["weight_kg"] = 601
    elif change == "volume":
        c["volume_m3"] = 3.1
    elif change == "cash":
        c.update(payment_type="COD", cod_amount_aed=5001)
    elif change == "chilled":
        c["handling"] = "CHILLED"
    elif change == "heavy":
        c["weight_kg"] = 31
    elif change == "driver_status":
        driver["status"] = "ON_LEAVE"
    elif change == "vehicle_status":
        v["status"] = "IN_MAINTENANCE"
    elif change == "shift":
        r["depart_hub"] = "08:00"
    elif change == "hours":
        r["return_hub"] = "20:00"
    elif change == "eta":
        s["eta"] = "09:00"
    elif change == "window":
        c["window"] = [780, 1020]
    elif change == "distance":
        r["distance_km"] = 999
    elif change == "service":
        s["service_min"] = 0
    elif change == "return":
        r["return_hub"] = "09:01"
    elif change == "address":
        a[0].update(lat=None, action="HOLD_FOR_CORRECTION")
    elif change == "unknown":
        s["consignment_ids"] = ["MISSING"]
    elif change == "duplicate":
        r["stops"].append(copy.deepcopy(s))
    elif change == "accounting":
        p["routes"] = []
    elif change == "break":
        r["return_hub"] = "16:00"
        r["breaks"] = []
    elif change == "sequence":
        s["seq"] = 4
    result = validate(p, d, a, cfg)
    assert not result["valid"]
    assert code in {x["code"] for x in result["findings"]}


def test_bike_dimensions_and_summer(small):
    cfg, d, a, p = small
    v = d["vehicles"][0]
    c = d["consignments"][0]
    driver = d["drivers"][0]
    v.update(type="MOTORBIKE", max_weight_kg=25, max_volume_m3=0.1)
    c["length_cm"] = 61
    assert not compatible(c, v, driver, cfg)
    r = p["routes"][0]
    r["return_hub"] = "13:00"
    p["plan_date"] = "2026-08-15"
    codes = {f["code"] for f in validate(p, d, a, cfg)["findings"]}
    assert {"SUMMER", "BIKE_ITEM"} <= codes


def test_break_overlap_rejected(small):
    cfg, d, a, p = small
    r = p["routes"][0]
    r["breaks"] = [{"start": "09:00", "end": "09:30"}]
    assert not validate(p, d, a, cfg)["valid"]


def test_shared_stop_service_time(small):
    cfg, d, a, p = small
    c = d["consignments"][0]
    c.update(normalized_address="villa 1 gated community", payment_type="COD")
    assert service([c, c], cfg) == 4 + 1 + 4 + 5


def test_capacity_and_licence_block_schedule(small):
    cfg, d, a, p = small
    v = d["vehicles"][0]
    driver = d["drivers"][0]
    d["consignments"][0]["weight_kg"] = 601
    assert schedule(make_stops(d, a, cfg), v, driver, cfg, cfg["plan_date"]) is None


def test_vehicle_specific_capacity(small):
    cfg, d, a, p = small
    d["vehicles"][0]["max_weight_kg"] = 1
    result = plan(d, a, cfg, solver_seconds=0)
    assert not result["routes"] and len(result["unassigned"]) == 1


def test_deterministic_and_timeout_fallback(small):
    cfg, d, a, p = small
    p1 = plan(d, a, cfg, solver_seconds=0)
    p2 = plan(d, a, cfg, solver_seconds=0)
    p1.pop("runtime_seconds")
    p2.pop("runtime_seconds")
    assert (
        p1 == p2
        and p1["fallback_reason"]
        and p1["engine"] == "deterministic-feasible-insertion"
    )
    assert validate(p1, d, a, cfg)["valid"]


def test_actual_solver_compatibility_binding(small):
    cfg, d, a, p = small
    result = plan(d, a, cfg, solver_seconds=1)
    assert result["fallback_reason"] is None
    assert (
        result["engine"].startswith("ortools") and validate(result, d, a, cfg)["valid"]
    )


def test_peak_boundary_integrated(real):
    cfg = real[0]
    assert travel(10, 560, "SEDAN", cfg) == pytest.approx(10 + (10 - 20 / 6) / 30 * 60)
    assert travel(10, 600, "MOTORBIKE", cfg) == pytest.approx(10 / 36 * 60)


def test_second_client_mapping(tmp_path):
    cfg = config("example_courier")
    (tmp_path / "consignments.csv").write_text("order_reference,mass_kg\nEXAMPLE-1,2\n")
    assert read_csv("consignments", cfg, tmp_path) == [
        {"consignment_id": "EXAMPLE-1", "weight_kg": "2"}
    ]
    assert (
        cfg["hub"] != config()["hub"]
        and cfg["cash_limit_aed"] != config()["cash_limit_aed"]
    )


def test_history_row_dispositions_complete(real):
    cfg, d, a = real
    _, ledger = resolve_all(d, cfg)
    assert len(ledger["dispositions"]) == 5856
    assert len({r["row_key"] for r in ledger["dispositions"]}) == 5856


def test_non_dubai_client_uses_own_service_region(small):
    cfg, d, a, p = small
    cfg["client_id"] = "example-courier"
    cfg["service_emirates"] = ["Abu Dhabi"]
    d["areas"] = [
        {
            "area_name": "Example District",
            "aliases": "Example",
            "emirate": "Abu Dhabi",
            "centroid_lat": "24.45",
            "centroid_lng": "54.38",
        }
    ]
    d["consignments"][0].update(
        address_line_1="Flat 1",
        address_line_2="Example Tower",
        area="Example",
        city="Abu Dhabi",
    )
    d["history"] = [
        {
            "consignment_id": f"EX-H-{i}",
            "outcome": "DELIVERED",
            "event_lat": str(24.45 + i * 0.0001),
            "event_lng": "54.38",
            "address_line_1": "Flat 1",
            "address_line_2": "Example Tower",
            "area": "Example",
            "city": "Abu Dhabi",
            "customer_phone": "MASKED",
            "landmark": "",
        }
        for i in range(3)
    ]
    preds, _ = resolve_all(d, cfg)
    assert preds[0]["quality"] == "GOOD" and preds[0]["lat"] is not None


def test_conflicting_area_and_city_are_not_auto_routed(small):
    cfg, d, a, p = small
    d["consignments"][0].update(area="Dubai Marina", city="Al Karama")
    preds, _ = resolve_all(d, cfg)
    assert preds[0]["quality"] == "INVALID" and preds[0]["lat"] is None
