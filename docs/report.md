# Submission report

The sample plan assigns 93 consignments to 8 routes. The other 339 input rows stay held or unassigned, each with a reason. The independent validator reports 0 hard violations. Address coverage limits how much of this shift can be dispatched.

The local app lets a manager inspect imports and address history, generate routes, edit assignments, validate changes, approve a version and export JSON or driver sheets. Exception controls simulate events before dispatch. Dispatch freezes the plan; later recovery needs manual coordination.

## Source records and address coverage

The v2 brief and Appendix B take precedence over the earlier brief. The source has 432 consignment rows, 28 drivers, 24 vehicles, 5856 historical attempts, 50 reference locations and 89 area definitions.

Three duplicate IDs affect six rows. Missing or negative package values, unsupported slots and conflicting fleet details also require review. The importer keeps original values beside normalized ones and holds invalid rows. A vehicle needs both the chilled-van type and refrigeration capability to carry chilled parcels.

See the [data audit](data_audit.md), [JSON audit](../outputs/data_audit.json), [assumptions](assumptions.md) and [requirements matrix](requirements_matrix.md). The address evaluator predicted 10 of 50 reference locations, or 20.0% coverage. Median error among predictions was 20.24 m. Those results leave most locations unresolved. Scores measure historical support and have not been calibrated as probabilities. Planning and the UI never read the reference coordinates.

## Manager and driver workflow

The manager reviews source errors, checks address evidence and generates a draft. Customer service must confirm unresolved destinations by 08:30 or leave the parcels held. A location correction needs coordinates, a reviewer and a reason. Editing an assignment creates a version and runs validation. Hard violations block approval.

Driver sheets list stops, arrival times, parcels, cash collection, handling notes, breaks and hub return. The app records no completed deliveries and sends no messages. Drivers need a separate tool for live location and proof of delivery.

## Routes and costs

[Routing](optimization.md) explains capacity, cash, handling, licence, work, break, summer, location and slot rules. Overtime has a price. A time-limited solver proposes routes; insertion repairs them or supplies a fallback. A separate validator checks the result. [Architecture](architecture.md) shows the modules and data flow.

The proposed plan costs AED 2,135.66 in the model and plans 93 consignments. The area baseline costs AED 3,801.61 and plans 90. Both use the same overall historical failure rate to estimate failure costs. These figures compare two simulations. They do not measure operating savings or completed deliveries. See the [cost model](cost_model.md) and [evaluation](evaluation.md).

## Exceptions and production work

Before dispatch, an absence or breakdown holds the affected route's work and preserves other sequences. Urgent intake starts held. Rescheduling rebuilds and validates the route. See [exception handling](edge_cases.md) for map outages, solver timeouts and invalid records. After dispatch, use the frozen driver sheets and coordinate recovery manually.

The [scale proposal](scaling.md) partitions jobs by client and hub. Its infrastructure costs are budget assumptions. The prototype has not been load-tested at 60,000 parcels per day. The second-client example supplies configuration and synthetic tests; it has no real customer dataset.

## Run and review

Use the [README](../README.md) to start the app and reproduce the outputs. The [demo script](demo_script.md) takes about six minutes. [AI usage](ai_usage.md) records how Codex contributed and which errors testing found. [Verification](verification.md) lists executed checks and untested capabilities. This report, the PDF deck and exports read the same saved JSON. The remote was public when checked. Share the confidential case material through a private destination.
