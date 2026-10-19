"""Verify actual loopback HTTP boundary with a running local server."""

import json, time, urllib.request
from backend.app.core import ROOT, dump


def call(path, body=None):
    request = urllib.request.Request(
        "http://127.0.0.1:8000" + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
        return response.status, (
            json.loads(raw)
            if "application/json" in response.headers.get("Content-Type", "")
            else raw.decode()
        )


def main():
    statuses = {}
    for path in ["/api/health", "/", "/api/overview", "/api/inputs", "/api/addresses"]:
        status, body = call(path)
        assert status == 200
        statuses[path] = status
        if path == "/api/overview":
            assert body["counts"]["consignments"] == 432
    started = time.monotonic()
    _, p = call("/api/plans", {"plan_date": "2026-10-14", "solver_seconds": 5})
    elapsed = time.monotonic() - started
    assert (
        p["validation"]["valid"]
        and p["metrics"]["planned_consignments"] + len(p["unassigned"]) == 432
    )
    status, approved = call(
        f"/api/plans/{p['version']}/approve",
        {
            "reviewer": "Verification script",
            "reason": "Real sample independently validated; held queue acknowledged",
        },
    )
    assert status == 200 and approved["state"] == "APPROVED"
    status, export = call(f"/api/plans/{approved['version']}/export")
    assert status == 200 and export["routes"] == approved["routes"]
    status, sheets = call(f"/api/plans/{approved['version']}/sheets")
    assert status == 200 and approved["routes"][0]["driver_id"] in sheets
    result = {
        "checks": statuses,
        "planning_request_seconds": round(elapsed, 3),
        "declared_smoke_budget_seconds": 30,
        "within_budget": elapsed < 30,
        "planned": p["metrics"]["planned_consignments"],
        "unassigned": len(p["unassigned"]),
        "hard_violations": p["validation"]["hard_count"],
        "approved_version": approved["version"],
        "export_and_sheets": True,
    }
    assert result["within_budget"]
    dump(ROOT / "outputs/http_smoke.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
