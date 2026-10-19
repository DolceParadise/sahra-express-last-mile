# Requirements matrix

Each implemented row has code and an executed check. Partial and deferred rows describe what still needs work.

| Requirement | Component | Status | Test or demonstration | Known limitation |
|---|---|---|---|---|
| Full v2/v1 brief review; v2 precedence | docs, export contract | Implemented | pdftotext extracts read in session; Appendix B tests | No interpretation confirmed with client |
| Exact six-file audit, schema, missing, categories, IDs | scripts/audit.py | Implemented | outputs/data_audit.json; docs/data_audit.md | Type inference is explicit field-based numeric/string |
| Raw/normalized/problem/disposition separation | ingestion.py | Implemented | Negative, blank, alias, slot and duplicate tests | Whole-file missing schemas stop import |
| Distinct rows with duplicate IDs | ingestion.py | Implemented | Six rows for three IDs, unique row keys | No automatic ID repair |
| Historical attempt dispositions | addresses.py | Implemented | 5,856 ledger entries test | Failed GPS never used as successful evidence |
| Configurable hub, fleet, costs, rules, slots | config/clients | Implemented | Own config + mapping and non-Dubai synthetic tests | No second-client real records supplied |
| Actual vehicle-specific capacities/costs | routing/validation/metrics | Implemented | Capacity tests, real outputs | Type capacities are conservative upper caps |
| Service regions and city/area contradictions | addresses.py | Implemented | Conflict and non-Dubai tests | No complete UAE address gazetteer |
| Arabic-preserving normalization | core.py | Implemented | Unicode normalization test | No Arabic semantic NLP/transliteration |
| Apartment/building/villa/street/community parsing | addresses.py | Partial | Component tests; review candidates | Text patterns, not general parser; Makani extracted but not looked up |
| Historical successful matching, outliers, ambiguity | addresses.py | Implemented | Cluster/outlier/conflict tests; source records in outputs | 105/432 supported locations; many unresolved records |
| Provider interfaces and no-key fallback | provider classes | Implemented | Full offline run; no-centroid test | External provider disabled |
| Four quality classes and actionable holds | addresses.py, UI | Implemented | Per-row outputs, browser address inspection | Evidence scores uncalibrated |
| Auditable manual confirmation and verification queue | API/SQLite/UI | Implemented | Review API tests; reviewer events | No customer-service messaging integration |
| Evaluation-only truth, coverage, errors, thresholds | evaluation.py | Implemented | File-open isolation test; 50-row report | Small selected sample; scores uncalibrated |
| Historical date isolation | API/provider/storage | Implemented | Replay before first event produces no history/routes | No event-time incremental import service |
| Heterogeneous capacitated time windows | routing.py | Implemented | Actual OR-Tools test; real-data run | Conservative seed times and fixed resource pairing |
| Weight, volume, bike individual limits | routing + validator | Implemented | Deliberately invalid plan tests | Weight is total shipment weight |
| Chilled and heavy/helper rules | routing + validator | Implemented | CHILLED/HEAVY tests and UI invalid edit | Heavy plus chilled is held |
| Licence, availability, resource uniqueness | routing + validator | Implemented | Licence/unavailable tests; real validation | At most one route per resource, no multi-trip reuse |
| Cash, hours, breaks, summer exclusion | routing + validator | Implemented | Cash/hour/break/summer tests | Bikes conservatively finish before 12:30 |
| Delivery hours, hard slots, hub return | routing + validator | Implemented | ETA/window/return tests | Arrival commitment; service may finish after slot end |
| Shared verified stop service times | routing + validator | Implemented | Shared-stop service test | Only identical-slot groups are combined |
| Haversine road factor and peak boundaries | core.py | Implemented | Boundary integration test | No road graph, toll or live traffic |
| Cost/objective and workload balance | routing/metrics | Implemented | Comparison JSON; route metrics | Heuristic hierarchy, no global optimality claim |
| Time-limited solver and feasible fallback | routing.py | Implemented | Zero-budget test; browser control | Whole job can exceed solver budget |
| Complete row accounting and unassigned reasons | routing + validator | Implemented | 432-row smoke; accounting mutation test | Shortfall reasons can be broad across multiple constraints |
| Independent plan validator | validation.py | Implemented | 21 parameterized deliberately invalid constraints | Shares geometry/time helpers with planner |
| Revalidation after manual changes | API/rebuild | Implemented | API edits, browser invalid/repair | No arbitrary external plan upload |
| Morning overview / input audit / address review | React | Implemented | Desktop/mobile browser tests, screenshots | Original import totals are labelled separately from version state |
| Interactive map and route detail | Leaflet | Implemented | Browser route/map/outage tests | Distinct palette repeats above seven routes |
| Move/reorder/hold and change driver/vehicle | API/UI | Implemented | API hold persistence; browser vehicle edit | UI moves whole stops, not individual parcels within a grouped stop |
| DRAFT/VALIDATED/APPROVED/DISPATCHED, versions | storage/API/UI | Implemented | Approval gate, repair, export and history tests | Local single-user; no auth/concurrency control |
| Appendix B JSON and manager/driver exports | API/submission script | Implemented | Exact required key tests; browser download | Driver sheet is printable HTML, not mobile app |
| Absence, breakdown, urgent, reschedule | API/UI | Implemented before dispatch | Exception tests and selective browser absence | Urgent intake starts held until review/reoptimization |
| Preserve committed/completed work after dispatch | API | Safe fallback | Dispatched state freezes edits/replanning | Live recovery/POD/GPS and custody transfer deferred |
| Cost, on-time, utilization and workload metrics | metrics.py | Implemented | Measured comparison and plan JSON | Uniform historical failure scenario, not calibrated forecast |
| Same-input area baseline | routing.py | Implemented | Baseline/proposed both independently validated | Coverage differs; compare cost per scenario success too |
| Outages and safe degradation | core/UI/tests | Implemented core paths | Map outage, forced timeout, malformed input tests | Backend outage uses previously printed sheets; no offline data store |
| Scaling proposal and costs | docs/scaling.md | Documented design | Explicit assumed cost table | Not load-tested at 80 hubs or 60,000/day |
| README/report/diagram/demo/PDF/AI note | docs/submission.py | Implemented | Generated 10-page PDF, actual-output metrics | User must review before presenting |
| Backend startup / frontend build / real app data | native startup | Implemented | Verification report, HTTP/browser evidence | Docker recipe included but not built |
| Private repository and no public data | Local work / GitHub metadata | Partial | Remote metadata reports public; no push/deploy performed | Remote must become private or use private submission channel |
