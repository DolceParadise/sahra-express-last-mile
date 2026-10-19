"""Independent acceptance checker. Does not import or trust routing/scheduling logic."""

import collections, math
from datetime import date
from .core import minute, road, travel, hav


def validate(plan, data, addresses, cfg):
    findings = []

    def add(
        code,
        explanation,
        route=None,
        cids=None,
        severity="HARD",
        correction="Correct assignment or hold affected consignments, then revalidate",
    ):
        findings.append(
            {
                "code": code,
                "severity": severity,
                "route": route.get("route_id") if route else None,
                "driver": route.get("driver_id") if route else None,
                "vehicle": route.get("vehicle_id") if route else None,
                "consignment_ids": cids or [],
                "explanation": explanation,
                "recommended_correction": correction,
            }
        )

    drivers = {r["driver_id"]: r for r in data["drivers"]}
    vehicles = {r["vehicle_id"]: r for r in data["vehicles"]}
    cons = collections.defaultdict(list)
    for c in data["consignments"]:
        cons[c["consignment_id"]].append(c)
    addr = {a["row_key"]: a for a in addresses}
    seen = collections.Counter()
    usedd = set()
    usedv = set()
    usedr = set()
    if plan["client_id"] != cfg["client_id"] or plan["hub_id"] != cfg["hub_id"]:
        add("TENANT", "Plan identity does not match active client/hub")
    for r in plan["routes"]:
        rid = r["route_id"]
        d = drivers.get(r["driver_id"])
        v = vehicles.get(r["vehicle_id"])
        if rid in usedr:
            add("ROUTE_DUPLICATE", "Route identifier repeated", r)
        usedr.add(rid)
        if r["driver_id"] in usedd:
            add("DRIVER_DUPLICATE", "Driver assigned more than one route", r)
        if r["vehicle_id"] in usedv:
            add("VEHICLE_DUPLICATE", "Vehicle assigned more than one route", r)
        usedd.add(r["driver_id"])
        usedv.add(r["vehicle_id"])
        for s in r["stops"]:
            seen.update(s["consignment_ids"])
        if not d or not v:
            add("UNKNOWN_RESOURCE", "Driver or vehicle does not exist", r)
            continue
        if d["status"] != "AVAILABLE" or d["problems"]:
            add("DRIVER_UNAVAILABLE", "Driver unavailable or invalid", r)
        if v["status"] != "AVAILABLE" or v["problems"]:
            add(
                "VEHICLE_UNAVAILABLE",
                "Vehicle unavailable, invalid or in maintenance",
                r,
            )
        kind = v["type"]
        rules = cfg["vehicle_types"].get(kind, {})
        if d["licence_type"] not in ["BOTH", rules.get("licence")]:
            add("LICENCE", "Driver licence incompatible with vehicle", r)
        try:
            depart = minute(r["depart_hub"])
            returned = minute(r["return_hub"])
        except ValueError:
            add("TIMESTAMP", "Unparseable route timestamp", r)
            continue
        if (
            depart < max(cfg["delivery_hours"][0], d["start"])
            or returned > cfg["delivery_hours"][1]
            or returned < depart
        ):
            add(
                "SHIFT", "Departure/return outside allowed working or delivery hours", r
            )
        if returned - depart > cfg["max_work_min"]:
            add("WORK_HOURS", "Route exceeds maximum working time including break", r)
        if returned > d["end"]:
            add(
                "OVERTIME",
                f"{returned-d['end']} overtime minutes charged",
                r,
                severity="SOFT",
                correction="Accept priced overtime or reduce workload",
            )
        if (
            kind == "MOTORBIKE"
            and date.fromisoformat(plan["plan_date"]).month in cfg["summer_months"]
            and depart < cfg["summer_bike_resume"]
            and returned > cfg["summer_bike_stop"]
        ):
            add("SUMMER", "Motorbike shift overlaps conservative summer exclusion", r)
        breaks = []
        for b in r.get("breaks", []):
            try:
                x, y = minute(b["start"]), minute(b["end"])
                breaks.append((x, y))
                if (
                    y - x < cfg["break_min"]
                    or x < depart
                    or y > returned
                    or x > depart + cfg["break_after_min"]
                ):
                    add("BREAK", "Break too short, late or outside route", r)
            except ValueError:
                add("BREAK", "Invalid break time", r)
        if returned - depart > cfg["break_after_min"] and not breaks:
            add("BREAK", "Route over six hours has no required break", r)
        if len(breaks) > 1:
            add("BREAK", "Prototype accepts one scheduled break per route", r)
        weight = volume = cash = distance = 0
        t = depart
        last = cfg["hub"]
        consumed_breaks = set()
        for i, s in enumerate(r["stops"], 1):
            ids = s["consignment_ids"]
            if s["seq"] != i:
                add("SEQUENCE", "Stop sequence is not contiguous", r, ids)
            if not ids:
                add("EMPTY_STOP", "Stop has no consignments", r)
            cs = []
            for cid in ids:
                if len(cons[cid]) != 1:
                    add(
                        "IDENTITY",
                        "Unknown or duplicate input identifier cannot be routed",
                        r,
                        [cid],
                    )
                    continue
                c = cons[cid][0]
                cs.append(c)
                a = addr[c["row_key"]]
                if c["problems"]:
                    add("INELIGIBLE", "Quarantined input assigned", r, [cid])
                if (
                    a["action"] not in ["AUTO_ROUTE", "MANUAL_OVERRIDE"]
                    or a["lat"] is None
                ):
                    add(
                        "ADDRESS",
                        "Unresolved, held or unconfirmed address assigned",
                        r,
                        [cid],
                    )
                elif hav([s["lat"], s["lng"]], [a["lat"], a["lng"]]) > 0.005:
                    add(
                        "LOCATION",
                        "Stop differs from canonical resolved coordinate",
                        r,
                        [cid],
                    )
                weight += c["weight_kg"]
                volume += c["volume_m3"]
                cash += c["cod_amount_aed"]
                if c["handling"] == "CHILLED" and (
                    kind != "CHILLED_VAN" or not v["refrigerated"]
                ):
                    add(
                        "CHILLED",
                        "Chilled consignment requires refrigerated chilled van",
                        r,
                        [cid],
                    )
                if c["weight_kg"] > 30 and kind != "LARGE_VAN":
                    add(
                        "HEAVY",
                        "Consignment over 30kg requires helper-equipped large van",
                        r,
                        [cid],
                    )
                if kind == "MOTORBIKE" and (
                    c["weight_kg"] > rules["max_item_weight"]
                    or max(c["length_cm"], c["width_cm"], c["height_cm"])
                    > rules["max_item_cm"]
                ):
                    add(
                        "BIKE_ITEM",
                        "Motorbike individual parcel weight or size exceeded",
                        r,
                        [cid],
                    )
            km = road(last, [s["lat"], s["lng"]], cfg)
            distance += km
            # A break must fit entirely before travel, during waiting, or after service.
            for bi, (x, y) in enumerate(breaks):
                if bi not in consumed_breaks and abs(x - t) < 0.01:
                    t = y
                    consumed_breaks.add(bi)
            arrival = t + travel(km, t, kind, cfg)
            try:
                eta = minute(s["eta"])
            except ValueError:
                add("ETA", "Invalid stop ETA", r, ids)
                eta = arrival
            for bi, (x, y) in enumerate(breaks):
                if bi not in consumed_breaks and arrival <= x and y <= eta:
                    consumed_breaks.add(bi)
            if eta + 0.01 < arrival:
                add("ETA", "ETA precedes independently computed arrival", r, ids)
            for c in cs:
                if not c["window"][0] <= eta <= c["window"][1]:
                    add(
                        "TIME_WINDOW",
                        "Arrival outside booked delivery slot",
                        r,
                        [c["consignment_id"]],
                    )
            text = " ".join(
                c["normalized_address"] + " " + c.get("notes", "") for c in cs
            ).lower()
            sv = cfg["service_min"]
            base = (
                sv["villa"]
                if any(x in text for x in ["villa", "street"])
                else (
                    sv["office"]
                    if any(x in text for x in ["office", "mall"])
                    else sv["default"]
                )
            )
            duration = (
                base
                + sv["extra"] * max(0, len(cs) - 1)
                + sv["cod"] * sum(c["payment_type"] == "COD" for c in cs)
                + (
                    sv["gated"]
                    if any(
                        x in text
                        for x in ["gated", "gate security", "community entrance"]
                    )
                    else 0
                )
            )
            if s["service_min"] != duration:
                add(
                    "SERVICE",
                    "Service duration does not match the parcel details and stop type",
                    r,
                    ids,
                )
            t = eta + duration
            last = [s["lat"], s["lng"]]
        for bi, (x, y) in enumerate(breaks):
            if bi not in consumed_breaks and abs(x - t) < 0.01:
                t = y
                consumed_breaks.add(bi)
        if len(consumed_breaks) != len(breaks):
            add(
                "BREAK_OVERLAP",
                "Break overlaps travel or service, or does not fit route timeline",
                r,
            )
        km = road(last, cfg["hub"], cfg)
        distance += km
        earliest = t + travel(km, t, kind, cfg)
        if returned + 0.01 < earliest:
            add("RETURN_TIME", "Return precedes travel back to hub", r)
        if abs(distance - r["distance_km"]) > 0.01:
            add(
                "DISTANCE",
                "Reported distance differs from hub-to-stops-to-hub geometry",
                r,
            )
        if weight > min(v["max_weight_kg"], rules.get("weight", 0)) + 1e-6:
            add("WEIGHT", "Vehicle-specific or configured weight capacity exceeded", r)
        if volume > min(v["max_volume_m3"], rules.get("volume", 0)) + 1e-6:
            add("VOLUME", "Vehicle-specific or configured volume capacity exceeded", r)
        if cash > cfg["cash_limit_aed"] + 1e-6:
            add("CASH", "Cash exposure exceeds driver limit", r)
    for cid, n in seen.items():
        if n > 1:
            add(
                "DUPLICATE_ASSIGNMENT",
                "Consignment assigned multiple times",
                cids=[cid],
            )
    unassigned = collections.Counter(u.get("row_key") for u in plan["unassigned"])
    for c in data["consignments"]:
        assigned = seen[c["consignment_id"]] > 0
        if assigned and unassigned[c["row_key"]]:
            add(
                "ACCOUNTING",
                "Input is both assigned and unassigned",
                cids=[c["consignment_id"]],
            )
        if not assigned and unassigned[c["row_key"]] != 1:
            add(
                "ACCOUNTING",
                "Input row missing or repeated in unassigned ledger",
                cids=[c["consignment_id"]],
            )
    validkeys = {c["row_key"] for c in data["consignments"]}
    if any(k not in validkeys for k in unassigned):
        add("ACCOUNTING", "Unknown row in unassigned ledger")
    hard = sum(f["severity"] == "HARD" for f in findings)
    return {
        "valid": hard == 0,
        "hard_count": hard,
        "soft_count": sum(f["severity"] == "SOFT" for f in findings),
        "findings": findings,
    }
