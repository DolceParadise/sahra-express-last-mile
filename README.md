# Sahra Express dispatch planner

A local dispatch planner for the Shipsy v2 case study. A hub manager can inspect source errors and historical locations, generate routes, edit assignments, approve a version and export driver sheets. Every change runs through a separate validator.

The sample run resolves locations for 105 of 432 input rows. After parcel and fleet checks, it plans 93 consignments across eight routes. The other 339 rows stay held or unassigned, each with a reason. [Evaluation](docs/evaluation.md) reports address coverage, location error and the baseline comparison. These are planning results; the app records no completed deliveries.

## Start locally

Tested on macOS ARM with Python 3.14.7 and Node 26.10.0. No paid API, Docker or secret is required.

From this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
npm --prefix frontend ci --no-audit --no-fund
npm --prefix frontend run build
.venv/bin/python -m uvicorn backend.app.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. The production React build and API share one origin. The API reference is http://127.0.0.1:8000/docs. First load imports the CSVs and builds historical location records. If a source file fails, the terminal shows the cause and the dashboard shows a fetch error. Stop the server with Ctrl-C.

For frontend development, run `npm --prefix frontend run dev` in another terminal while the backend runs. Vite proxies `/api` to port 8000. No external address API is called. OpenStreetMap tiles require internet, but cached coordinates, paths and route lists still work without them.

An optional `docker compose up --build` recipe is included. It was not executed in this environment; the native commands above are the verified path. Docker exposes the app on loopback and persists versions in a named volume.

## Reproduce the evidence

```sh
.venv/bin/python scripts/audit.py
.venv/bin/python -m scripts.run
.venv/bin/python -m pytest -q
.venv/bin/python -m scripts.submission
```

`outputs/addresses.json` is saved before the offline evaluator opens the reference coordinates. Planning and address modules never read `ground_truth_sample.csv`. `outputs/validation.json` preserves the import decision for every consignment row; `outputs/history_rejections.json` has whether each historical attempt was used and why. `outputs/data_audit.json` contains all six schemas and missing/category/numeric results. The source CSV files are not changed.

`outputs/optimized_plan.json` and `outputs/baseline_plan.json` include the Appendix B fields plus diagnostics. `outputs/sample_plan.json` is the submission copy. The comparison, evaluation, PDF deck, manager summary and printable route sheets are generated from these artifacts. Rerunning replaces offline artifacts; application versions live separately in ignored `outputs/state/plans.sqlite3`.

Browser checks require the server to be running. Install the test browser once if absent, then run:

```sh
npm --prefix frontend exec -- playwright install chromium
npm --prefix frontend exec -- playwright test --config frontend/playwright.config.ts
```

Alternatively, from `frontend`, run `npx playwright test`. The tests generate a plan, inspect uncertain addresses and the map, construct an invalid assignment, observe blocked approval, repair it and download JSON. They also cover mobile navigation and map outage/absence simulation. See `outputs/browser-tests.json` and [verification](docs/verification.md). Playwright and its browser are development dependencies, not runtime requirements.

## Manager workflow

1. Open Morning overview and confirm shift date. The sample date is 2026-10-14, the day after the supplied history ends. The AVAILABLE roster count and usable count differ when validation finds invalid shifts.
2. Inspect Input audit for quarantined rows. Raw values remain inspectable. Duplicate IDs are held in full.
3. Generate a draft. Address review lets customer service inspect historical candidates, record verification requests, hold records, or confirm a customer-supplied location with reviewer and reason. It provides no default from reference coordinates. Reoptimize the reviewed draft to insert newly confirmed records.
4. Open Route planning for stops, ETA, vehicle/driver, cash, load, break, return and cost. Held rows remain in the ledger.
5. Use Edit & validate to move whole stops, reorder, hold, or change resource. Every edit rebuilds routes and checks the parcel, fleet and timing rules. You can inspect an invalid draft, but cannot approve it. Restore a compatible resource or hold affected work, then revalidate.
6. Review all unassigned reasons and priced overtime in Approval & export. Enter reviewer/reason, approve the valid partial plan, download JSON and print driver sheets. Mark dispatched only when ready; dispatched versions freeze.
7. Use Operational exceptions for labelled pre-dispatch absence, breakdown, urgent CSV-shaped intake or reschedule simulations. Events preserve unaffected route sequences; explicit reoptimization may then change the draft. After dispatch, coordinate parcel transfers manually.

Every edit saves a new version. The selector opens earlier versions and the review log records who changed what and why. The app supports one local operator. It has no login, protection against simultaneous edits or request deduplication.

## Configuration and second-client example

[config/clients/sahra_express.yaml](config/clients/sahra_express.yaml) contains hub, region, operating hours, standard slots, vehicle rules, licences, capacity caps, service and speed assumptions, costs, cash, breaks, heat rules, thresholds and objective weights. The CSV supplies each vehicle's costs and capacities. Configured type limits cap larger capacities. The second config changes hub, region, fleet definitions/costs, hours, cash and field mappings. It has no genuine second-client data.

Select a config using `SAHRA_CLIENT=example_courier`, with that client's own CSV files in the required format supplied in `data`. Use that client's own files. Field-mapping and synthetic non-Dubai tests verify the configuration path. Existing versions freeze their configuration. Restart after file changes; generate a new version to apply new settings. No dashboard config editor is provided.

History used for a selected planning date is restricted to earlier events. The supplied historical period is 2026-08-15 through 2026-10-13. A historical replay can therefore have less coverage than the default shift.

## Components and documents

Python/FastAPI, OR-Tools, PyYAML and SQLite form the backend. React, TypeScript, Vite, Tailwind, coss ui/Base UI and Leaflet form the dashboard. Pytest and Playwright verify the application. ReportLab creates the PDF deck.

- [Report](docs/report.md), [data audit](docs/data_audit.md), [requirements matrix](docs/requirements_matrix.md), [assumptions](docs/assumptions.md)
- [Architecture and Mermaid diagram](docs/architecture.md), [optimization](docs/optimization.md), [cost model](docs/cost_model.md)
- [Evaluation](docs/evaluation.md), [failure handling](docs/edge_cases.md), [scaling proposal and budget assumptions](docs/scaling.md)
- [AI usage and real corrections](docs/ai_usage.md), [six-minute demo script](docs/demo_script.md), [verification](docs/verification.md)
- [PDF deck](outputs/submission_deck.pdf), [sample JSON](outputs/sample_plan.json), [printable sheets](outputs/driver_route_sheets.html), [manager summary](outputs/route_summary.csv)

## Limits and confidentiality

Most addresses remain unresolved. The app has no external building geocoder or Makani lookup. Scores measure support in the available history. Distances are 1.4 times Haversine and exclude Salik, closures and live traffic. Fixed driver/vehicle pairing and insertion can miss better routes.

Summer bikes return by 12:30. Weight means total shipment weight; dimensions apply per piece. Heavy chilled consignments stay held. The UI moves whole stops. Reimporting a source file requires a command. Production still needs live driver location, proof of delivery, messaging, parcel handover support and load testing.

The existing GitHub remote reported PUBLIC during verification. Nothing from this implementation, source dataset or briefs was pushed or hosted. Keep this checkout and submission zip local until the remote is made private or a private submission channel is selected. Original case material is confidential; repository source licensing does not grant permission to publish the supplied brief or data.

Use Reoptimize reviewed draft to keep saved corrections and holds. Generate plan starts again from the source files. Confirmed locations do not carry into a new shift automatically.

The interface uses official coss components with the neutral theme. See [UI refresh verification](docs/ui_refresh.md) and [component integration](frontend/COMPONENTS.md). Six browser checks now include keyboard Select navigation, dialog focus restoration, required fields and every screen at mobile width.
