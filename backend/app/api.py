"""Local single-user operations API. Bind to loopback; no external address requests."""

import copy, html, json, os
from functools import lru_cache
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .core import config, ROOT
from .ingestion import ingest
from .addresses import resolve_all
from .routing import plan, make_stops, schedule, service
from .validation import validate
from .metrics import metrics
from . import storage

app = FastAPI(title="Sahra Express dispatch planner", version="0.1.0")
CLIENT = os.environ.get("SAHRA_CLIENT", "sahra_express")


@lru_cache(maxsize=1)
def initial():
    cfg = config(CLIENT)
    data = ingest(cfg)
    addresses, _ = resolve_all(data, cfg)
    return cfg, data, addresses


def context(version):
    cfg, data, _ = initial()
    try:
        return storage.load(version, cfg, data)
    except KeyError as e:
        raise HTTPException(404, str(e))


def finalize(ctx, event):
    p = ctx["plan"]
    p["addresses"] = copy.deepcopy(ctx["addresses"])
    p["validation"] = validate(p, ctx["data"], ctx["addresses"], ctx["cfg"])
    p["metrics"] = metrics(p, ctx["data"], ctx["cfg"])
    if event.get("operation") not in ["approve", "dispatch"]:
        p["state"] = "VALIDATED" if p["validation"]["valid"] else "DRAFT"
    return storage.save(ctx, event)


class Generate(BaseModel):
    plan_date: str | None = None
    method: str = "optimized"
    solver_seconds: float = Field(default=5, ge=0, le=30)


@app.get("/api/health")
def health():
    return {"ok": True, "mode": "local-single-user", "external_geocoder": False}


@app.get("/api/overview")
def overview():
    cfg, d, a = initial()
    from collections import Counter

    return {
        "config": cfg,
        "counts": d["raw_counts"],
        "dispositions": dict(Counter(c["disposition"] for c in d["consignments"])),
        "address_quality": dict(Counter(p["quality"] for p in a)),
        "available_drivers": sum(
            x["status"] == "AVAILABLE" and not x["problems"] for x in d["drivers"]
        ),
        "available_vehicles": sum(
            x["status"] == "AVAILABLE" and not x["problems"] for x in d["vehicles"]
        ),
        "fleet_weight_capacity_kg": sum(
            min(v["max_weight_kg"], cfg["vehicle_types"][v["type"]]["weight"])
            for v in d["vehicles"]
            if v["status"] == "AVAILABLE" and not v["problems"]
        ),
        "fleet_volume_capacity_m3": sum(
            min(v["max_volume_m3"], cfg["vehicle_types"][v["type"]]["volume"])
            for v in d["vehicles"]
            if v["status"] == "AVAILABLE" and not v["problems"]
        ),
        "backend_note": "Distances use a road approximation. Map tiles need internet; route lines and stop lists work without them.",
    }


@app.get("/api/inputs")
def inputs():
    _, d, _ = initial()
    return {k: v for k, v in d.items() if k not in ["history", "areas"]}


@app.get("/api/addresses")
def addresses():
    return initial()[2]


@app.get("/api/evidence")
def evidence():
    result = {}
    for name in ["evaluation", "comparison", "data_audit"]:
        p = ROOT / f"outputs/{name}.json"
        result[name] = json.loads(p.read_text()) if p.exists() else None
    return result


@app.post("/api/plans")
def generate(body: Generate):
    from datetime import date

    cfg, d, a = initial()
    try:
        date.fromisoformat(body.plan_date or cfg["plan_date"])
    except ValueError:
        raise HTTPException(422, "Use ISO date YYYY-MM-DD")
    if body.method not in ["optimized", "baseline"]:
        raise HTTPException(422, "Unknown planning method")
    ctx = {
        "cfg": copy.deepcopy(cfg),
        "data": copy.deepcopy(d),
        "addresses": copy.deepcopy(a),
    }
    planning_date = body.plan_date or cfg["plan_date"]
    ctx["cfg"]["plan_date"] = planning_date
    ctx["data"]["history"] = [h for h in d["history"] if h["date"] < planning_date]
    if planning_date != cfg["plan_date"]:
        ctx["addresses"], _ = resolve_all(ctx["data"], ctx["cfg"])
    ctx["plan"] = plan(
        ctx["data"],
        ctx["addresses"],
        ctx["cfg"],
        planning_date,
        body.method,
        body.solver_seconds,
    )
    return finalize(ctx, {"operation": "generate", "method": body.method})


@app.get("/api/versions")
def versions():
    return storage.versions(initial()[0])


@app.get("/api/events")
def events():
    return storage.events(initial()[0])


@app.get("/api/plans/{version}")
def get_plan(version: int):
    return context(version)["plan"]


@app.get("/api/plans/{version}/context")
def get_context(version: int):
    ctx = context(version)
    return {
        "drivers": ctx["data"]["drivers"],
        "vehicles": ctx["data"]["vehicles"],
        "consignments": ctx["data"]["consignments"],
    }


def rebuild(ctx):
    p = ctx["plan"]
    cons = {c["consignment_id"]: c for c in ctx["data"]["consignments"]}
    drivers = {d["driver_id"]: d for d in ctx["data"]["drivers"]}
    vehicles = {v["vehicle_id"]: v for v in ctx["data"]["vehicles"]}
    for i, r in enumerate(p["routes"]):
        if not r["stops"]:
            continue
        if r["driver_id"] not in drivers or r["vehicle_id"] not in vehicles:
            continue
        stops = []
        completed = {s.get("stop_id"): s.get("completed", False) for s in r["stops"]}
        for s in r["stops"]:
            cs = [cons[cid] for cid in s["consignment_ids"] if cid in cons]
            if not cs:
                continue
            stops.append(
                {
                    **s,
                    "consignments": cs,
                    "service_min": service(cs, ctx["cfg"]),
                    "weight_kg": sum(c["weight_kg"] for c in cs),
                    "volume_m3": sum(c["volume_m3"] for c in cs),
                    "cash_aed": sum(c["cod_amount_aed"] for c in cs),
                    "window": [
                        max(c["window"][0] for c in cs),
                        min(c["window"][1] for c in cs),
                    ],
                }
            )
        new = schedule(
            stops,
            vehicles[r["vehicle_id"]],
            drivers[r["driver_id"]],
            ctx["cfg"],
            p["plan_date"],
            enforce=False,
        )
        if new:
            for s in new["stops"]:
                s["completed"] = completed.get(s["stop_id"], False)
            p["routes"][i] = {**new, "route_id": r["route_id"]}
    p["routes"] = [r for r in p["routes"] if r["stops"]]


class Edit(BaseModel):
    operation: str
    route_id: str | None = None
    target_route_id: str | None = None
    stop_index: int = 0
    target_index: int = 0
    resource_id: str | None = None
    reviewer: str = Field(min_length=1)
    reason: str = Field(min_length=1)


@app.post("/api/plans/{version}/edit")
def edit(version: int, b: Edit):
    ctx = context(version)
    p = ctx["plan"]
    if p["state"] == "DISPATCHED":
        raise HTTPException(
            409,
            "Dispatched plans are frozen. Operational events hold affected pending stops for manual recovery.",
        )
    r = next((r for r in p["routes"] if r["route_id"] == b.route_id), None)
    if not r:
        raise HTTPException(404, "Route not found")
    before = copy.deepcopy(p["metrics"])
    if b.operation in ["driver", "vehicle"]:
        kind = "drivers" if b.operation == "driver" else "vehicles"
        key = "driver_id" if b.operation == "driver" else "vehicle_id"
        if not any(x[key] == b.resource_id for x in ctx["data"][kind]):
            raise HTTPException(422, "Unknown resource")
        r[key] = b.resource_id
    elif b.operation in ["move", "reorder", "hold"]:
        if not 0 <= b.stop_index < len(r["stops"]):
            raise HTTPException(422, "Stop index out of range")
        s = r["stops"].pop(b.stop_index)
        if b.operation == "hold":
            for cid in s["consignment_ids"]:
                c = next(
                    c for c in ctx["data"]["consignments"] if c["consignment_id"] == cid
                )
                p["unassigned"].append(
                    {
                        "consignment_id": cid,
                        "row_key": c["row_key"],
                        "reason": "Manager hold: " + b.reason,
                    }
                )
                for a in ctx["addresses"]:
                    if a["row_key"] == c["row_key"]:
                        a.update(
                            action="HOLD_FOR_CORRECTION", manual_review_required=True
                        )
        else:
            target = (
                r
                if b.operation == "reorder"
                else next(
                    (r for r in p["routes"] if r["route_id"] == b.target_route_id), None
                )
            )
            if not target:
                raise HTTPException(422, "Target route missing")
            target["stops"].insert(max(0, min(b.target_index, len(target["stops"]))), s)
    else:
        raise HTTPException(422, "Unsupported edit")
    rebuild(ctx)
    p["change_summary"] = {
        "operation": b.operation,
        "previous_metrics": before,
        "reason": b.reason,
    }
    return finalize(ctx, b.model_dump())


class Review(BaseModel):
    row_key: str
    action: str
    lat: float | None = None
    lng: float | None = None
    reviewer: str = Field(min_length=1)
    reason: str = Field(min_length=1)


@app.post("/api/plans/{version}/address-review")
def review(version: int, b: Review):
    ctx = context(version)
    if ctx["plan"]["state"] == "DISPATCHED":
        raise HTTPException(409, "Dispatched plans are frozen")
    a = next((a for a in ctx["addresses"] if a["row_key"] == b.row_key), None)
    if not a:
        raise HTTPException(404, "Input row not found")
    if b.action == "MANUAL_OVERRIDE":
        import math

        bounds = ctx["cfg"]["manual_coordinate_bounds"]
        if (
            b.lat is None
            or b.lng is None
            or not math.isfinite(b.lat)
            or not math.isfinite(b.lng)
            or not bounds[0] <= b.lat <= bounds[1]
            or not bounds[2] <= b.lng <= bounds[3]
        ):
            raise HTTPException(
                422,
                "Enter customer-confirmed coordinates within the service region",
            )
        a.update(
            explanation=f"Location confirmed by {b.reviewer}: {b.reason}",
            lat=b.lat,
            lng=b.lng,
            source="MANUAL_CONFIRMATION",
            quality="GOOD",
            confidence=1,
            confidence_kind="Human confirmation, not measured accuracy",
            action=b.action,
            manual_review_required=False,
            evidence=[f"{b.reviewer}: {b.reason}"],
        )
    elif b.action in [
        "VERIFY_WITH_CUSTOMER",
        "VERIFY_WITH_SHOP",
        "HOLD_FOR_CORRECTION",
    ]:
        a.update(action=b.action, manual_review_required=True)
    else:
        raise HTTPException(422, "Unsupported review action")
    a["review"] = {"reviewer": b.reviewer, "reason": b.reason, "action": b.action}
    # Avoid silently retaining routes at a changed or held destination.
    for r in ctx["plan"]["routes"]:
        for s in list(r["stops"]):
            if a["consignment_id"] in s["consignment_ids"]:
                s["consignment_ids"].remove(a["consignment_id"])
                ctx["plan"]["unassigned"].append(
                    {
                        "consignment_id": a["consignment_id"],
                        "row_key": a["row_key"],
                        "reason": "Address changed; reoptimize to insert after review",
                    }
                )
                if not s["consignment_ids"]:
                    r["stops"].remove(s)
    rebuild(ctx)
    return finalize(ctx, b.model_dump())


class Identity(BaseModel):
    reviewer: str = Field(min_length=1)
    reason: str = "Reviewed all hard constraints"


@app.post("/api/plans/{version}/reoptimize")
def reoptimize(version: int, b: Identity):
    ctx = context(version)
    if ctx["plan"]["state"] == "DISPATCHED":
        raise HTTPException(409, "No global replanning after dispatch")
    old = ctx["plan"]["metrics"]
    ctx["plan"] = plan(
        ctx["data"], ctx["addresses"], ctx["cfg"], ctx["plan"]["plan_date"]
    )
    ctx["plan"]["change_summary"] = {"operation": "reoptimize", "previous_metrics": old}
    return finalize(ctx, {"operation": "reoptimize", **b.model_dump()})


@app.post("/api/plans/{version}/validate")
def revalidate(version: int):
    return finalize(context(version), {"operation": "validate"})


@app.post("/api/plans/{version}/approve")
def approve(version: int, b: Identity):
    ctx = context(version)
    p = ctx["plan"]
    p["validation"] = validate(p, ctx["data"], ctx["addresses"], ctx["cfg"])
    if not p["validation"]["valid"]:
        raise HTTPException(
            409,
            {
                "message": "Hard violations block approval",
                "validation": p["validation"],
            },
        )
    if not p["routes"]:
        raise HTTPException(409, "Empty plan cannot be approved")
    if p["state"] == "DISPATCHED":
        raise HTTPException(409, "Already dispatched")
    p["state"] = "APPROVED"
    return finalize(ctx, {"operation": "approve", **b.model_dump()})


@app.post("/api/plans/{version}/dispatch")
def dispatch(version: int, b: Identity):
    ctx = context(version)
    if ctx["plan"]["state"] != "APPROVED":
        raise HTTPException(409, "Approve this version before dispatch")
    if not validate(ctx["plan"], ctx["data"], ctx["addresses"], ctx["cfg"])["valid"]:
        raise HTTPException(409, "Validation failed")
    ctx["plan"]["state"] = "DISPATCHED"
    return finalize(ctx, {"operation": "dispatch", **b.model_dump()})


class ExceptionEvent(BaseModel):
    kind: str
    resource_id: str | None = None
    consignment_id: str | None = None
    consignment: dict | None = None
    slot_start: str | None = None
    slot_end: str | None = None
    reviewer: str = Field(min_length=1)
    reason: str = Field(min_length=1)


@app.post("/api/plans/{version}/exceptions")
def exception(version: int, b: ExceptionEvent):
    ctx = context(version)
    p = ctx["plan"]
    before = copy.deepcopy(p["metrics"])
    affected = []
    if b.kind in ["driver_absence", "vehicle_breakdown"]:
        key = "driver_id" if b.kind == "driver_absence" else "vehicle_id"
        dataset = "drivers" if b.kind == "driver_absence" else "vehicles"
        resource = next(
            (r for r in ctx["data"][dataset] if r[key] == b.resource_id), None
        )
        if not resource:
            raise HTTPException(404, "Resource not found")
        if p["state"] == "DISPATCHED":
            raise HTTPException(
                409,
                "Recovery needs a transfer location and confirmed parcel handover. Export the frozen route sheet and coordinate the transfer manually.",
            )
        resource["status"] = "ON_LEAVE" if dataset == "drivers" else "IN_MAINTENANCE"
        for r in p["routes"]:
            if r[key] == b.resource_id:
                affected.append(r["route_id"])
                for s in r["stops"]:
                    for cid in s["consignment_ids"]:
                        c = next(
                            c
                            for c in ctx["data"]["consignments"]
                            if c["consignment_id"] == cid
                        )
                        p["unassigned"].append(
                            {
                                "consignment_id": cid,
                                "row_key": c["row_key"],
                                "reason": f"Simulated {b.kind}: confirm resource replacement or reoptimize",
                            }
                        )
        p["routes"] = [r for r in p["routes"] if r["route_id"] not in affected]
    elif b.kind == "reschedule":
        if p["state"] == "DISPATCHED":
            raise HTTPException(
                409,
                "Live reschedule requires driver confirmation. Frozen plan retained.",
            )
        from .core import minute

        try:
            window = [minute(b.slot_start or ""), minute(b.slot_end or "")]
        except ValueError:
            raise HTTPException(422, "Invalid slot")
        if window not in ctx["cfg"]["slots"]:
            raise HTTPException(422, "Use supported booked slot")
        c = next(
            (
                c
                for c in ctx["data"]["consignments"]
                if c["consignment_id"] == b.consignment_id
            ),
            None,
        )
        if not c:
            raise HTTPException(404, "Consignment not found")
        c["window"] = window
        for r in p["routes"]:
            if any(b.consignment_id in s["consignment_ids"] for s in r["stops"]):
                affected.append(r["route_id"])
        rebuild(ctx)
    elif b.kind == "urgent":
        if p["state"] == "DISPATCHED":
            raise HTTPException(
                409,
                "Urgent insertion after dispatch requires custody confirmation. Use a separate recovery plan.",
            )
        if not b.consignment:
            raise HTTPException(422, "Supply a full incoming consignment record")
        # Reuse the exact ingestion pipeline, with temporary files scoped to this call.
        import tempfile, csv
        from .core import read_csv

        with tempfile.TemporaryDirectory() as td:
            for name in [
                "consignments",
                "drivers",
                "vehicles",
                "areas",
                "delivery_history",
            ]:
                rows = read_csv(name, ctx["cfg"])
                if name == "consignments":
                    if any(
                        c["consignment_id"] == b.consignment.get("consignment_id")
                        for c in ctx["data"]["consignments"]
                    ):
                        raise HTTPException(409, "Incoming ID already exists")
                    fields = list(rows[0])
                    rows = [{k: str(b.consignment.get(k, "")) for k in fields}]
                else:
                    fields = list(rows[0])
                with open(Path(td) / f"{name}.csv", "w") as f:
                    w = csv.DictWriter(f, fieldnames=fields)
                    w.writeheader()
                    w.writerows(rows)
            incoming = ingest(ctx["cfg"], td)
            new = incoming["consignments"][0]
            new["row_key"] = f"urgent:{len(ctx['data']['consignments'])+1}"
            pred, _ = resolve_all(incoming, ctx["cfg"])
            pred[0]["row_key"] = new["row_key"]
            ctx["data"]["consignments"].append(new)
            ctx["addresses"].append(pred[0])
            p["unassigned"].append(
                {
                    "consignment_id": new["consignment_id"],
                    "row_key": new["row_key"],
                    "reason": "Urgent intake received; review validation and address, then reoptimize",
                }
            )
    else:
        raise HTTPException(422, "Unsupported exception")
    p["change_summary"] = {
        "operation": b.kind,
        "simulated": True,
        "affected_routes": affected,
        "previous_metrics": before,
        "next_action": "Review the held consignments and reoptimize before loading. Other route sequences remain unchanged",
    }
    return finalize(ctx, {"operation": "simulation", **b.model_dump()})


@app.get("/api/plans/{version}/export")
def export(version: int):
    p = context(version)["plan"]
    return JSONResponse(
        p,
        headers={
            "Content-Disposition": f'attachment; filename="sahra-plan-v{version}.json"'
        },
    )


@app.get("/api/plans/{version}/sheets", response_class=HTMLResponse)
def sheets(version: int):
    p = context(version)["plan"]
    esc = lambda x: html.escape(str(x))
    parts = [
        f'<html><head><title>Driver route sheets v{version}</title><style>body{{font:15px system-ui;margin:35px}}article{{break-after:page}}td,th{{padding:10px;border-bottom:1px solid #bbb;text-align:left}}small{{color:#555}}@media print{{button{{display:none}}}}</style></head><body><button onclick="print()">Print / save PDF</button>'
    ]
    for r in p["routes"]:
        breaks = ", ".join(f"{b['start']} to {b['end']}" for b in r["breaks"]) or "None scheduled"
        parts.append(
            f"<article><h1>{esc(r['route_id'])} · {esc(r['driver_id'])} · {esc(r['vehicle_id'])}</h1><p>{esc(p['plan_date'])}, v{version}, {esc(p['state'])}. Hub {esc(p['hub_id'])}. Depart {esc(r['depart_hub'])}, return {esc(r['return_hub'])}. Cash AED {r['cash_aed']:.2f}. Breaks {esc(breaks)}</p><p>Collect cash on delivery before handing over the parcel. Record the delivery with an OTP or photo. If the customer is unreachable, call them. Return collected cash and undelivered parcels to the hub.</p><table><tr><th>Stop / ETA</th><th>Address / parcels</th><th>COD / handling</th></tr>"
        )
        ctx = context(version)
        cs = {c["consignment_id"]: c for c in ctx["data"]["consignments"]}
        for s in r["stops"]:
            detail = "; ".join(
                f"{cid}: {cs[cid]['payment_type']} AED {cs[cid]['cod_amount_aed']}, {cs[cid]['handling']}, {cs[cid]['pieces']} pieces. {cs[cid].get('notes','')}"
                for cid in s["consignment_ids"]
            )
            parts.append(
                f"<tr><td>{s['seq']} / {esc(s['eta'])}</td><td>{esc(s['address'])}<br>{esc(', '.join(s['consignment_ids']))}<br><small>{s['lat']}, {s['lng']}</small></td><td>{esc(detail)}</td></tr>"
            )
        parts.append("</table></article>")
    return "".join(parts) + "</body></html>"


DIST = ROOT / "frontend/dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="dashboard")
