"""Create the report, <=10-page PDF deck and exports from measured run artifacts."""

import csv, json, copy, tempfile, os, hashlib, re
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from backend.app.core import ROOT, config, dump


def load(name):
    return json.loads((ROOT / "outputs" / name).read_text())


def pct(x):
    return f"{x*100:.1f}%" if x is not None else "n/a"


def fmt(x):
    return f"{x:,.2f}" if x is not None else "n/a"


def main():
    p = load("optimized_plan.json")
    b = load("baseline_plan.json")
    e = load("evaluation.json")
    audit = load("data_audit.json")
    m = p["metrics"]
    bm = b["metrics"]
    a = p["addresses"]
    assert p["validation"]["valid"] and b["validation"]["valid"]
    dump(ROOT / "outputs/sample_plan.json", p)
    with (ROOT / "outputs/route_summary.csv").open("w") as f:
        fields = [
            "route_id",
            "driver_id",
            "vehicle_id",
            "vehicle_type",
            "depart_hub",
            "return_hub",
            "distance_km",
            "duration_min",
            "weight_kg",
            "volume_m3",
            "cash_aed",
            "cost_aed",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: r[k] for k in fields} for r in p["routes"])
    # Use the real renderer over the exact offline plan, in an isolated temporary DB.
    from backend.app import api, storage
    from backend.app.ingestion import ingest

    cfg = config()
    d = ingest(cfg)
    old = os.environ.get("SAHRA_DB")
    with tempfile.TemporaryDirectory() as td:
        os.environ["SAHRA_DB"] = str(Path(td) / "export.sqlite3")
        saved = storage.save(
            {"cfg": cfg, "data": d, "addresses": a, "plan": copy.deepcopy(p)},
            {"operation": "offline_export"},
        )
        (ROOT / "outputs/driver_route_sheets.html").write_text(
            api.sheets(saved["version"])
        )
    if old is None:
        os.environ.pop("SAHRA_DB", None)
    else:
        os.environ["SAHRA_DB"] = old
    ev = [
        "# Address evaluation and plan comparison",
        "",
        f"Sample shift: {p['plan_date']}. Results come from the saved plan and evaluation files. The app has no field outcomes.",
        "",
        "## Address coverage and error",
        "",
        f"The resolver predicted {e['predicted']} of {e['samples']} reference locations and left {e['abstained']} unresolved. Coverage is {pct(e['coverage'])}.",
        f"Median error {fmt(e['median_error_m'])} m; mean {fmt(e['mean_error_m'])} m; P90 {fmt(e['p90_error_m'])} m among the {e['predicted']} predictions. P90 uses nearest rank.",
        "",
        "| Threshold | Among predictions | Among all 50 samples |",
        "|---|---:|---:|",
    ]
    for n in [50, 100, 500]:
        ev.append(
            f"| Within {n}m | {pct(e[f'within_{n}m_among_predictions'])} | {pct(e[f'within_{n}m_all_samples'])} |"
        )
    ev += [
        "",
        "The resolver leaves 80% of the reference sample unresolved. Read the error figures alongside that coverage. The 50 selected records may not represent the full shift. Scores measure historical support and have not been calibrated as probabilities.",
        "",
        "## Raising the evidence threshold",
        "",
        "| Evidence threshold | Predicted / all | Coverage | Median error, metres |",
        "|---|---:|---:|---:|",
    ]
    for t, s in e["thresholds"].items():
        ev.append(
            f"| {t} | {s['predicted']} / {s['samples']} | {pct(s['coverage'])} | {fmt(s['median_error_m'])} |"
        )
    ev += [
        "",
        "## Results by address category",
        "",
        "| Category | Samples | Predicted | Coverage | Median error, metres |",
        "|---|---:|---:|---:|---:|",
    ]
    for q, s in e["by_quality"].items():
        ev.append(
            f"| {q} | {s['samples']} | {s['predicted']} | {pct(s['coverage'])} | {fmt(s['median_error_m'])} |"
        )
    ev += ["", "## Examples with source records", ""]
    for row in sorted(
        [r for r in e["rows"] if r["error_m"] is not None], key=lambda r: r["error_m"]
    )[:3]:
        addr = next(x for x in a if x["consignment_id"] == row["consignment_id"])
        ev.append(
            f"- {row['consignment_id']}: {row['error_m']:.1f} m error; {addr['source']}; evidence {', '.join(addr['evidence'][:5])}. {addr['explanation']}."
        )
    for row in sorted(
        [r for r in e["rows"] if r["area_centroid_error_m"] is not None],
        key=lambda r: r["area_centroid_error_m"],
        reverse=True,
    )[:2]:
        ev.append(
            f"- {row['consignment_id']}: a hypothetical route to its area centre would have {row['area_centroid_error_m']:.1f} m error. The planner did not route to this centre."
        )
    ambiguous = next(x for x in a if x["quality"] == "AMBIGUOUS" and x["candidates"])
    incomplete = next(x for x in a if x["quality"] == "INCOMPLETE")
    ev += [
        f"- {ambiguous['consignment_id']}: {ambiguous['explanation']}. {ambiguous['action']}.",
        f"- {incomplete['consignment_id']}: {incomplete['explanation']}. No coordinate is routed.",
        "",
        "## Baseline and proposed planner",
        "",
        "Both planners use the same eligibility rules and hard constraints. They plan different numbers of consignments, so compare coverage alongside cost per scenario success. Every route in both plans passed independent validation.",
        "",
        "| Metric | Area baseline | Proposed |",
        "|---|---:|---:|",
    ]
    for label, key in [
        ("Planned consignments", "planned_consignments"),
        ("Unassigned raw rows", "unassigned_rows"),
        ("Routes", "active_routes"),
        ("Approximate km", "total_km"),
        ("Fixed AED", "fixed_cost_aed"),
        ("Running AED", "running_cost_aed"),
        ("Overtime AED", "overtime_cost_aed"),
        ("Outside-slot AED", "late_penalty_aed"),
        ("Failure-cost scenario AED", "risk_cost_scenario_aed"),
        ("Total scenario AED", "total_cost_scenario_aed"),
        ("Predicted successes, scenario", "predicted_successes_scenario"),
        ("AED per scenario success", "cost_per_success_scenario_aed"),
        ("Mean route minutes", "average_duration_min"),
        ("Workload standard deviation, min", "workload_stddev_min"),
        ("Mean weight utilization", "average_weight_utilization"),
    ]:
        ev.append(f"| {label} | {bm[key]} | {m[key]} |")
    ev += [
        "",
        f"The modeled cost difference is AED {bm['total_cost_scenario_aed']-m['total_cost_scenario_aed']:.2f}. Planned consignments differ by {m['planned_consignments']-bm['planned_consignments']}. No field comparison with the dispatcher was run.",
        f"Historical failure scenario: {pct(m['failure_rate_scenario'])}. Both plans have {pct(m['planned_on_time_fraction'])} of planned arrivals in slot. Actual completed deliveries: {m['actual_completed']}.",
        f"Reported planner computation: baseline {b['runtime_seconds']} s; proposed {p['runtime_seconds']} s. These exclude ingestion/address resolution and vary by machine. The five-second solver limit excludes import, address matching and repair.",
        "",
        "## Production measures",
        "",
        "Track address failures per attempt, confirmed corrections, reused locations, review minutes, unresolved addresses and changes after dispatch. Check scores against verified destinations. Always report coverage with location error. Compare hub-days with similar parcels and fleet availability before replacing the dispatcher's process.",
    ]
    (ROOT / "docs/evaluation.md").write_text("\n".join(ev) + "\n")
    report = f"""# Submission report

The sample plan assigns {m['planned_consignments']} consignments to {m['active_routes']} routes. The other {m['unassigned_rows']} input rows stay held or unassigned, each with a reason. The independent validator reports {p['validation']['hard_count']} hard violations. Address coverage limits how much of this shift can be dispatched.

The local app lets a manager inspect imports and address history, generate routes, edit assignments, validate changes, approve a version and export JSON or driver sheets. Exception controls simulate events before dispatch. Dispatch freezes the plan; later recovery needs manual coordination.

## Source records and address coverage

The v2 brief and Appendix B take precedence over the earlier brief. The source has {audit['consignments']['rows']} consignment rows, {audit['drivers']['rows']} drivers, {audit['vehicles']['rows']} vehicles, {audit['delivery_history']['rows']} historical attempts, {audit['ground_truth_sample']['rows']} reference locations and {audit['areas']['rows']} area definitions.

Three duplicate IDs affect six rows. Missing or negative package values, unsupported slots and conflicting fleet details also require review. The importer keeps original values beside normalized ones and holds invalid rows. A vehicle needs both the chilled-van type and refrigeration capability to carry chilled parcels.

See the [data audit](data_audit.md), [JSON audit](../outputs/data_audit.json), [assumptions](assumptions.md) and [requirements matrix](requirements_matrix.md). The address evaluator predicted {e['predicted']} of {e['samples']} reference locations, or {pct(e['coverage'])} coverage. Median error among predictions was {fmt(e['median_error_m'])} m. Those results leave most locations unresolved. Scores measure historical support and have not been calibrated as probabilities. Planning and the UI never read the reference coordinates.

## Manager and driver workflow

The manager reviews source errors, checks address evidence and generates a draft. Customer service must confirm unresolved destinations by 08:30 or leave the parcels held. A location correction needs coordinates, a reviewer and a reason. Editing an assignment creates a version and runs validation. Hard violations block approval.

Driver sheets list stops, arrival times, parcels, cash collection, handling notes, breaks and hub return. The app records no completed deliveries and sends no messages. Drivers need a separate tool for live location and proof of delivery.

## Routes and costs

[Routing](optimization.md) explains capacity, cash, handling, licence, work, break, summer, location and slot rules. Overtime has a price. A time-limited solver proposes routes; insertion repairs them or supplies a fallback. A separate validator checks the result. [Architecture](architecture.md) shows the modules and data flow.

The proposed plan costs AED {m['total_cost_scenario_aed']:,.2f} in the model and plans {m['planned_consignments']} consignments. The area baseline costs AED {bm['total_cost_scenario_aed']:,.2f} and plans {bm['planned_consignments']}. Both use the same overall historical failure rate to estimate failure costs. These figures compare two simulations. They do not measure operating savings or completed deliveries. See the [cost model](cost_model.md) and [evaluation](evaluation.md).

## Exceptions and production work

Before dispatch, an absence or breakdown holds the affected route's work and preserves other sequences. Urgent intake starts held. Rescheduling rebuilds and validates the route. See [exception handling](edge_cases.md) for map outages, solver timeouts and invalid records. After dispatch, use the frozen driver sheets and coordinate recovery manually.

The [scale proposal](scaling.md) partitions jobs by client and hub. Its infrastructure costs are budget assumptions. The prototype has not been load-tested at 60,000 parcels per day. The second-client example supplies configuration and synthetic tests; it has no real customer dataset.

## Run and review

Use the [README](../README.md) to start the app and reproduce the outputs. The [demo script](demo_script.md) takes about six minutes. [AI usage](ai_usage.md) records how Codex contributed and which errors testing found. [Verification](verification.md) lists executed checks and untested capabilities. This report, the PDF deck and exports read the same saved JSON. The remote was public when checked. Share the confidential case material through a private destination.
"""
    (ROOT / "docs/report.md").write_text(report)
    slides = [
        (
            f"{m['planned_consignments']} consignments ready for review",
            [
                f"{m['planned_consignments']} planned consignments on {m['active_routes']} routes, with {p['validation']['hard_count']} hard violations",
                f"{m['unassigned_rows']} input rows held or unassigned, each with a reason",
                "The manager can inspect, edit, validate, approve and export a plan.",
                "Confirm more building locations to increase dispatch coverage.",
            ],
        ),
        (
            "Source errors hold 23 rows",
            [
                f"{audit['consignments']['rows']} consignment rows, {audit['delivery_history']['rows']} historical attempts and 89 areas",
                "Three duplicate IDs affect six rows. All six stay held.",
                "Missing weights and unsupported slots need source corrections.",
                "V01 is a bike marked refrigerated. Chilled parcels still require a chilled van.",
            ],
        ),
        (
            "Review the shift in one dashboard",
            [
                "Inspect imports and addresses, then plan, validate and approve.",
                "Every edit saves a version. Hard violations block approval.",
                "Driver sheets list stops, parcels, arrival times, cash, breaks and return.",
                "Screenshot from the running local app.",
            ],
        ),
        (
            "10 of 50 locations predicted",
            [
                f"Coverage {pct(e['coverage'])}; {e['abstained']} records left unresolved",
                f"Among predictions, median error {fmt(e['median_error_m'])} m, mean {fmt(e['mean_error_m'])} m, P90 {fmt(e['p90_error_m'])} m",
                f"Within 50 m: {pct(e['within_50m_among_predictions'])} of predictions, {pct(e['within_50m_all_samples'])} of all references",
                "Matching needs a building identity and consistent historical GPS.",
                "Scores measure support. Reference coordinates enter only the evaluator.",
            ],
        ),
        (
            "Local planning with a separate validator",
            [
                "CSV imports keep original values, normalized records and row problems.",
                "Historical matching supplies eligible stops to OR-Tools and insertion repair.",
                "A separate validator checks routes before approval and export.",
                "React displays results. FastAPI handles actions. SQLite saves versions.",
                "The single-user app needs no paid API or runtime model.",
            ],
        ),
        (
            "Invalid edits block approval",
            [
                "Checks cover capacity, cash, licence, availability and bike limits.",
                "Chilled parcels require refrigeration and a chilled van. Heavy loads need a large van with a helper.",
                "Arrivals must meet booked slots. Work includes breaks and hub return.",
                "Routes allow at most ten hours. Summer bikes return by 12:30.",
                "Change R01 to a bike to see the block. Restore V17 to repair it.",
            ],
        ),
        (
            "More consignments at lower modeled cost",
            [
                f"Area baseline: {bm['planned_consignments']} consignments, {bm['active_routes']} routes, {bm['total_km']} km",
                f"Proposed plan: {m['planned_consignments']} consignments, {m['active_routes']} routes, {m['total_km']} km",
                f"Scenario cost: AED {fmt(bm['total_cost_scenario_aed'])} baseline, AED {fmt(m['total_cost_scenario_aed'])} proposed",
                f"Per scenario success: AED {fmt(bm['cost_per_success_scenario_aed'])} baseline, AED {fmt(m['cost_per_success_scenario_aed'])} proposed",
                "Both pass validation and use the same historical failure rate.",
                "Coverage differs. These simulations do not measure actual operating savings.",
            ],
        ),
        (
            "Hold affected work before dispatch",
            [
                "An absence or breakdown holds one route's parcels and preserves other sequences.",
                "Urgent records start held. Rescheduled routes run through validation again.",
                "If the solver times out without a solution, insertion supplies a validated fallback.",
                "When map tiles fail, route lines and stop lists remain available.",
                "Dispatch freezes the plan. Coordinate later recovery manually.",
            ],
        ),
        (
            "Start rollout with one hub",
            [
                "80 hubs and 60,000 parcels per day are design targets that still need load tests.",
                "Queue jobs by client, hub and date. Limit each job's time and resources.",
                "Measure held parcels, confirmed corrections, review time, address failures and overtime.",
                "Assumed infrastructure budget: AED 2.32 per hub-day, subject to supplier checks.",
                "Production needs authentication, road routing, driver location and delivery records.",
            ],
        ),
        (
            "Testing caught three generated-code errors",
            [
                "Codex helped write the code, tests, documents and artifact generators.",
                "OR-Tools rejected a Python list. Vehicle exclusion constraints fixed the binding.",
                "Leaflet cleanup failed during navigation. Stopping animations fixed it.",
                "A test tried to parse a blank weight. The test now handles blanks.",
                "Saved test results and validated plans record what ran.",
                "The implementation remains local. Use a private submission channel.",
            ],
        ),
    ]
    (ROOT / "docs/deck.md").write_text(
        "\n\n".join(
            f"## {i+1}. {title}\n\n" + "\n".join("- " + s for s in bullets)
            for i, (title, bullets) in enumerate(slides)
        )
    )
    c = canvas.Canvas(str(ROOT / "outputs/submission_deck.pdf"), pagesize=(960, 540))
    c.setTitle("Sahra Express dispatch planner | prototype results")
    for i, (title, bullets) in enumerate(slides):
        c.setFillColor(HexColor("#f2f5ee"))
        c.rect(0, 0, 960, 540, fill=1, stroke=0)
        c.setFillColor(HexColor("#183c32"))
        c.rect(0, 0, 18, 540, fill=1, stroke=0)
        c.setFont("Helvetica", 10)
        c.drawString(48, 505, "SAHRA EXPRESS / DISPATCH PLANNER / SHIPSY V2")
        c.setFont("Helvetica-Bold", 29)
        c.drawString(48, 450, title)
        style = ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=17,
            leading=25,
            textColor=HexColor("#375140"),
        )
        y = 400
        for line in bullets:
            para = Paragraph(line, style)
            w, h = para.wrap(860, 100)
            para.drawOn(c, 48, y - h)
            y -= h + 18
        if i == 2 and (ROOT / "outputs/overview.png").exists():
            # Small authentic screenshot on a workflow slide; text still supplies the meaning.
            c.drawImage(
                str(ROOT / "outputs/overview.png"),
                550,
                54,
                width=340,
                height=170,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
        c.setFont("Helvetica", 9)
        c.setFillColor(HexColor("#73816d"))
        c.drawString(
            48,
            24,
            f'Sample shift {p["plan_date"]} | All performance figures are model outputs | Confidential local submission',
        )
        c.drawRightString(918, 24, f"{i+1} / {len(slides)}")
        c.showPage()
    c.save()
    manifest = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (ROOT / "outputs").glob("*")
        if path.suffix in [".json", ".pdf", ".csv", ".html"]
        and path.name != "artifact_manifest.json"
    }
    dump(ROOT / "outputs/artifact_manifest.json", manifest)
    print(
        "Generated report, evaluation, 10-slide PDF deck, sample JSON, manager summary and route sheets"
    )


if __name__ == "__main__":
    main()
