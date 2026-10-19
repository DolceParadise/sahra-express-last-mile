import statistics


def metrics(plan, data, cfg):
    routes = plan["routes"]
    planned = sum(len(s["consignment_ids"]) for r in routes for s in r["stops"])
    durations = [r["duration_min"] for r in routes]
    failures = sum(h["outcome"] == "FAILED" for h in data["history"])
    rate = failures / len(data["history"]) if data["history"] else 0
    fixed = sum(r["fixed_cost_aed"] for r in routes)
    running = sum(r["running_cost_aed"] for r in routes)
    overtime = sum(r["overtime_cost_aed"] for r in routes)
    expected_success = planned * (1 - rate)
    risk = planned * rate * cfg["failure_cost_aed"]
    total = fixed + running + overtime + risk
    late = sum(
        len(s["consignment_ids"])
        for r in routes
        for s in r["stops"]
        if not s["window"][0]
        <= int(s["eta"][:2]) * 60 + int(s["eta"][3:])
        <= s["window"][1]
    )
    return {
        "planned_consignments": planned,
        "actual_completed": sum(
            len(s["consignment_ids"])
            for r in routes
            for s in r["stops"]
            if s.get("completed")
        ),
        "unassigned_rows": len(plan["unassigned"]),
        "active_routes": len(routes),
        "total_km": round(sum(r["distance_km"] for r in routes), 2),
        "fixed_cost_aed": round(fixed, 2),
        "running_cost_aed": round(running, 2),
        "overtime_cost_aed": round(overtime, 2),
        "late_penalty_aed": late * cfg["late_penalty_aed"],
        "failure_rate_scenario": round(rate, 5),
        "risk_cost_scenario_aed": round(risk, 2),
        "total_cost_scenario_aed": round(total + late * cfg["late_penalty_aed"], 2),
        "predicted_successes_scenario": round(expected_success, 2),
        "cost_per_success_scenario_aed": (
            round(total / expected_success, 2) if expected_success else None
        ),
        "planned_on_time_fraction": (planned - late) / planned if planned else None,
        "average_duration_min": (
            round(statistics.mean(durations), 1) if durations else 0
        ),
        "workload_stddev_min": (
            round(statistics.pstdev(durations), 1) if durations else 0
        ),
        "workload_range_min": [min(durations), max(durations)] if durations else [0, 0],
        "average_weight_utilization": (
            round(statistics.mean(r["weight_utilization"] for r in routes), 3)
            if routes
            else 0
        ),
        "available_drivers_used": len(routes),
        "risk_note": "Both plans use the overall historical failure rate. It has not been calibrated for these addresses; field savings have not been measured",
    }
