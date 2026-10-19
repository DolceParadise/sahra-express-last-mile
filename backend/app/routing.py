"""Bounded OR-Tools CVRPTW seed plus deterministic feasibility repair/insertion."""

import collections, copy, math, time
from datetime import date
from .core import road, travel, hhmm


def compatible(c, v, d, cfg):
    kind = v["type"]
    rules = cfg["vehicle_types"][kind]
    return (
        not c["problems"]
        and not v["problems"]
        and not d["problems"]
        and v["status"] == "AVAILABLE"
        and d["status"] == "AVAILABLE"
        and d["licence_type"] in ["BOTH", rules["licence"]]
        and (
            c["handling"] != "CHILLED" or (kind == "CHILLED_VAN" and v["refrigerated"])
        )
        and (c["weight_kg"] <= 30 or kind == "LARGE_VAN")
        and (
            kind != "MOTORBIKE"
            or (
                c["weight_kg"] <= rules["max_item_weight"]
                and max(c["length_cm"], c["width_cm"], c["height_cm"])
                <= rules["max_item_cm"]
            )
        )
    )


def service(cons, cfg):
    text = " ".join(
        c["normalized_address"] + " " + c.get("notes", "") for c in cons
    ).lower()
    s = cfg["service_min"]
    base = (
        s["villa"]
        if any(x in text for x in ["villa", "street"])
        else s["office"] if any(x in text for x in ["office", "mall"]) else s["default"]
    )
    return (
        base
        + s["extra"] * (len(cons) - 1)
        + s["cod"] * sum(c["payment_type"] == "COD" for c in cons)
        + (
            s["gated"]
            if any(x in text for x in ["gated", "gate security", "community entrance"])
            else 0
        )
    )


def fleet(data, cfg):
    drivers = sorted(
        [
            d
            for d in data["drivers"]
            if d["status"] == "AVAILABLE" and not d["problems"]
        ],
        key=lambda d: (d["licence_type"] == "BOTH", d["driver_id"]),
    )
    vehicles = sorted(
        [
            v
            for v in data["vehicles"]
            if v["status"] == "AVAILABLE" and not v["problems"]
        ],
        key=lambda v: (
            0 if v["type"] == "CHILLED_VAN" else 1 if v["type"] == "LARGE_VAN" else 2,
            v["fixed_cost_aed_day"],
            v["vehicle_id"],
        ),
    )
    pairs = []
    for v in vehicles:
        requirement = cfg["vehicle_types"][v["type"]]["licence"]
        eligible = [d for d in drivers if d["licence_type"] in [requirement, "BOTH"]]
        if eligible:
            d = min(
                eligible,
                key=lambda d: (d["licence_type"] == "BOTH", d["start"], d["driver_id"]),
            )
            drivers.remove(d)
            pairs.append((v, d))
    return pairs


def make_stops(data, addresses, cfg):
    byrow = {a["row_key"]: a for a in addresses}
    groups = {}
    for c in data["consignments"]:
        a = byrow[c["row_key"]]
        if (
            c["problems"]
            or a["action"] not in ["AUTO_ROUTE", "MANUAL_OVERRIDE"]
            or a["lat"] is None
        ):
            continue
        # Historical physical identity must agree; manual locations only share exact coordinate + building.
        physical = (
            tuple(a["candidates"][0]["key"])
            if a["source"] == "HISTORICAL_CLUSTER"
            else (a["lat"], a["lng"], a["components"]["building"])
        )
        key = (physical, tuple(c["window"]))
        if key not in groups:
            groups[key] = {
                "consignments": [],
                "lat": a["lat"],
                "lng": a["lng"],
                "physical_key": str(physical),
                "window": c["window"],
                "area": (
                    a["candidates"][0]["key"][0]
                    if a["source"] == "HISTORICAL_CLUSTER"
                    else c["area"]
                ),
            }
        groups[key]["consignments"].append(c)
    stops = []
    for i, g in enumerate(groups.values(), 1):
        g.update(
            stop_id=f"S{i:03d}",
            consignment_ids=[c["consignment_id"] for c in g["consignments"]],
            service_min=service(g["consignments"], cfg),
            weight_kg=sum(c["weight_kg"] for c in g["consignments"]),
            volume_m3=sum(c["volume_m3"] for c in g["consignments"]),
            cash_aed=sum(c["cod_amount_aed"] for c in g["consignments"]),
            address=g["consignments"][0]["normalized_address"],
        )
        stops.append(g)
    return stops


def schedule(stops, v, d, cfg, plan_date, enforce=True):
    if not stops:
        return None
    if enforce and any(
        not compatible(c, v, d, cfg) for s in stops for c in s["consignments"]
    ):
        return None
    weight = sum(s["weight_kg"] for s in stops)
    volume = sum(s["volume_m3"] for s in stops)
    cash = sum(s["cash_aed"] for s in stops)
    if enforce and (
        weight
        > min(v["max_weight_kg"], cfg["vehicle_types"][v["type"]]["weight"]) + 1e-8
        or volume
        > min(v["max_volume_m3"], cfg["vehicle_types"][v["type"]]["volume"]) + 1e-8
        or cash > cfg["cash_limit_aed"] + 1e-8
    ):
        return None
    depart = max(cfg["delivery_hours"][0], d["start"])
    t = depart
    last = cfg["hub"]
    distance = 0
    output = []
    breaks = []

    def rest_before(duration):
        nonlocal t
        if not breaks and t + duration > depart + cfg["break_after_min"]:
            breaks.append(
                {
                    "start": hhmm(t),
                    "end": hhmm(t + cfg["break_min"]),
                    "duration_min": cfg["break_min"],
                }
            )
            t += cfg["break_min"]

    for i, s in enumerate(stops, 1):
        km = road(last, [s["lat"], s["lng"]], cfg)
        drive = travel(km, t, v["type"], cfg)
        # Break before a segment whose travel, waiting and service crosses six hours.
        duration = max(t + drive, s["window"][0]) + s["service_min"] - t
        rest_before(duration)
        drive = travel(km, t, v["type"], cfg)
        eta = math.ceil(max(t + drive, s["window"][0]) - 1e-8)
        if enforce and eta > s["window"][1]:
            return None
        t = eta + s["service_min"]
        distance += km
        last = [s["lat"], s["lng"]]
        output.append(
            {k: copy.deepcopy(val) for k, val in s.items() if k != "consignments"}
            | {"seq": i, "eta": hhmm(eta), "completed": False}
        )
    km = road(last, cfg["hub"], cfg)
    rest_before(travel(km, t, v["type"], cfg))
    t = math.ceil(t + travel(km, t, v["type"], cfg) - 1e-8)
    distance += km
    if enforce and (t - depart > cfg["max_work_min"] or t > cfg["delivery_hours"][1]):
        return None
    if (
        enforce
        and v["type"] == "MOTORBIKE"
        and date.fromisoformat(plan_date).month in cfg["summer_months"]
        and depart < cfg["summer_bike_resume"]
        and t > cfg["summer_bike_stop"]
    ):
        return None
    overtime = max(0, t - d["end"]) * cfg["overtime_aed_hour"] / 60
    return {
        "driver_id": d["driver_id"],
        "vehicle_id": v["vehicle_id"],
        "vehicle_type": v["type"],
        "licence": d["licence_type"],
        "depart_hub": hhmm(depart),
        "return_hub": hhmm(t),
        "distance_km": round(distance, 3),
        "stops": output,
        "breaks": breaks,
        "weight_kg": round(weight, 3),
        "volume_m3": round(volume, 5),
        "cash_aed": round(cash, 2),
        "duration_min": t - depart,
        "weight_utilization": weight
        / min(v["max_weight_kg"], cfg["vehicle_types"][v["type"]]["weight"]),
        "volume_utilization": volume
        / min(v["max_volume_m3"], cfg["vehicle_types"][v["type"]]["volume"]),
        "fixed_cost_aed": v["fixed_cost_aed_day"],
        "running_cost_aed": round(distance * v["cost_per_km_aed"], 2),
        "overtime_cost_aed": round(overtime, 2),
        "cost_aed": round(
            v["fixed_cost_aed_day"] + distance * v["cost_per_km_aed"] + overtime, 2
        ),
    }


def ortools_seed(stops, pairs, cfg, plan_date, timeout):
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    if timeout <= 0:
        raise TimeoutError("Solver budget exhausted before start")
    n = len(stops)
    manager = pywrapcp.RoutingIndexManager(n + 1, len(pairs), 0)
    model = pywrapcp.RoutingModel(manager)
    points = [cfg["hub"]] + [[s["lat"], s["lng"]] for s in stops]
    matrix = [[road(a, b, cfg) for b in points] for a in points]
    for vi, (v, d) in enumerate(pairs):
        cost = model.RegisterTransitCallback(
            lambda a, b, v=v: int(
                matrix[manager.IndexToNode(a)][manager.IndexToNode(b)]
                * v["cost_per_km_aed"]
                * 100
            )
        )
        model.SetArcCostEvaluatorOfVehicle(cost, vi)
        model.SetFixedCostOfVehicle(int(v["fixed_cost_aed_day"] * 100), vi)
    for field, scale, cap in [
        ("weight_kg", 1000, "max_weight_kg"),
        ("volume_m3", 1000000, "max_volume_m3"),
        ("cash_aed", 100, None),
    ]:
        cb = model.RegisterUnaryTransitCallback(
            lambda a, field=field, scale=scale: (
                int(math.ceil(stops[manager.IndexToNode(a) - 1][field] * scale))
                if manager.IndexToNode(a) > 0
                else 0
            )
        )
        caps = [
            int(
                (
                    cfg["cash_limit_aed"]
                    if cap is None
                    else min(
                        v[cap],
                        cfg["vehicle_types"][v["type"]][
                            "weight" if cap == "max_weight_kg" else "volume"
                        ],
                    )
                )
                * scale
            )
            for v, d in pairs
        ]
        model.AddDimensionWithVehicleCapacity(cb, 0, caps, True, field)
    # Conservative peak-speed time matrix. Real ETAs are rebuilt with period integration.
    cb = model.RegisterTransitCallback(
        lambda a, b: math.ceil(
            matrix[manager.IndexToNode(a)][manager.IndexToNode(b)]
            / cfg["peak_speed_kmh"]
            * 60
        )
        + (
            stops[manager.IndexToNode(a) - 1]["service_min"]
            if manager.IndexToNode(a) > 0
            else 0
        )
    )
    model.AddDimension(cb, 720, 1440, False, "Time")
    td = model.GetDimensionOrDie("Time")
    for vi, (v, d) in enumerate(pairs):
        start = max(d["start"], cfg["delivery_hours"][0])
        end = min(
            start + cfg["max_work_min"] - cfg["break_min"], cfg["delivery_hours"][1]
        )
        if (
            v["type"] == "MOTORBIKE"
            and date.fromisoformat(plan_date).month in cfg["summer_months"]
        ):
            end = min(end, cfg["summer_bike_stop"])
        td.CumulVar(model.Start(vi)).SetRange(start, start)
        td.CumulVar(model.End(vi)).SetRange(start, max(start, end))
    for node, s in enumerate(stops, 1):
        idx = manager.NodeToIndex(node)
        td.CumulVar(idx).SetRange(*s["window"])
        allowed = [
            vi
            for vi, (v, d) in enumerate(pairs)
            if all(compatible(c, v, d, cfg) for c in s["consignments"])
        ]
        if allowed:
            for vi in range(len(pairs)):
                if vi not in allowed:
                    model.solver().Add(model.VehicleVar(idx) != vi)
        else:
            model.solver().Add(model.ActiveVar(idx) == 0)
        model.AddDisjunction([idx], cfg["objective"]["unassigned_penalty"])
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    )
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GREEDY_DESCENT
    )
    params.time_limit.FromMilliseconds(int(timeout * 1000))
    solution = model.SolveWithParameters(params)
    if solution is None:
        raise TimeoutError("No solver incumbent")
    result = []
    for vi in range(len(pairs)):
        route = []
        idx = model.Start(vi)
        while not model.IsEnd(idx):
            node = manager.IndexToNode(idx)
            if node:
                route.append(stops[node - 1])
            idx = solution.Value(model.NextVar(idx))
        result.append(route)
    return result


def plan(data, addresses, cfg, plan_date=None, method="optimized", solver_seconds=None):
    started = time.monotonic()
    plan_date = plan_date or cfg["plan_date"]
    pairs = fleet(data, cfg)
    stops = make_stops(data, addresses, cfg)
    sequences = [[] for _ in pairs]
    engine = (
        "area-nearest-baseline"
        if method == "baseline"
        else "ortools-cvrptw + feasible insertion"
    )
    fallback = None
    if method != "baseline" and pairs and stops:
        try:
            seed = ortools_seed(
                stops,
                pairs,
                cfg,
                plan_date,
                cfg["solver_seconds"] if solver_seconds is None else solver_seconds,
            )
            for i, seq in enumerate(seed):
                for s in seq:
                    if schedule(sequences[i] + [s], *pairs[i], cfg, plan_date):
                        sequences[i].append(s)
        except (TimeoutError, ImportError, RuntimeError) as e:
            engine = "deterministic-feasible-insertion"
            fallback = str(e)
    remaining = [s for s in stops if not any(s in seq for seq in sequences)]
    remaining.sort(
        key=lambda s: (
            s["window"][1],
            (
                s.get("area", "") + " " + s["address"]
                if method == "baseline"
                else -s["weight_kg"]
            ),
            s["stop_id"],
        )
    )
    rejected = {}
    area_route = {}
    for s in remaining:
        choices = []
        for i, (v, d) in enumerate(pairs):
            if any(not compatible(c, v, d, cfg) for c in s["consignments"]):
                continue
            before = schedule(sequences[i], v, d, cfg, plan_date)
            positions = (
                [len(sequences[i])]
                if method == "baseline"
                else range(len(sequences[i]) + 1)
            )
            for pos in positions:
                trial = sequences[i][:pos] + [s] + sequences[i][pos:]
                scheduled = schedule(trial, v, d, cfg, plan_date)
                if scheduled:
                    score = (
                        road(
                            [s["lat"], s["lng"]],
                            (
                                [sequences[i][-1]["lat"], sequences[i][-1]["lng"]]
                                if sequences[i]
                                else cfg["hub"]
                            ),
                            cfg,
                        )
                        if method == "baseline"
                        else scheduled["cost_aed"]
                        - (before["cost_aed"] if before else 0)
                        + cfg["objective"]["balance_weight"] * scheduled["duration_min"]
                    )
                    if method == "baseline" and area_route.get(s.get("area", "")) == i:
                        score -= 100000
                    choices.append((score, i, pos))
        if choices:
            _, i, pos = min(choices)
            sequences[i].insert(pos, s)
            if method == "baseline":
                area_route.setdefault(s.get("area", ""), i)
        else:
            reason = (
                "No compatible available driver/vehicle"
                if not any(
                    all(compatible(c, v, d, cfg) for c in s["consignments"])
                    for v, d in pairs
                )
                else "No route fits the capacity, cash, slot, work-hour and summer limits"
            )
            rejected.update({cid: reason for cid in s["consignment_ids"]})
    routes = []
    for i, seq in enumerate(sequences):
        if seq:
            routes.append(
                schedule(seq, *pairs[i], cfg, plan_date)
                | {"route_id": f"R{len(routes)+1:02d}"}
            )
    assigned = {cid for r in routes for s in r["stops"] for cid in s["consignment_ids"]}
    byrow = {a["row_key"]: a for a in addresses}
    unassigned = []
    for c in data["consignments"]:
        if c["consignment_id"] not in assigned:
            a = byrow[c["row_key"]]
            reason = (
                "Input quarantine: " + ", ".join(c["problems"])
                if c["problems"]
                else (
                    a["explanation"]
                    if a["action"] not in ["AUTO_ROUTE", "MANUAL_OVERRIDE"]
                    else rejected.get(c["consignment_id"], "Fleet capacity exhausted")
                )
            )
            unassigned.append(
                {
                    "consignment_id": c["consignment_id"],
                    "row_key": c["row_key"],
                    "reason": reason,
                }
            )
    return {
        "plan_date": plan_date,
        "client_id": cfg["client_id"],
        "hub_id": cfg["hub_id"],
        "assumptions": [
            "Road km = 1.4 × Haversine; no Salik or live road routing",
            "Slots enforced as hard arrival constraints",
            "Confidence is heuristic; unresolved addresses held",
            "Costs use the historical failure rate, which has not been calibrated for these addresses",
        ],
        "routes": routes,
        "unassigned": unassigned,
        "addresses": copy.deepcopy(addresses),
        "state": "DRAFT",
        "engine": engine,
        "fallback_reason": fallback,
        "runtime_seconds": round(time.monotonic() - started, 3),
    }
