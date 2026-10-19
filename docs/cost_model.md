# Cost model

Route cost is the vehicle's activation cost, plus distance times its running cost, plus overtime. Costs come from the v2 brief and supplied vehicle rows. CSV costs take precedence over type defaults. Type capacity limits cap unusually large CSV capacities; smaller CSV capacities still apply.

The comparison adds AED 12 per planned consignment times the overall historical failure rate. It also allows AED 5 per consignment outside its slot. Both generated plans meet every booked arrival slot, so that penalty is zero.

Both plans use the same historical failure rate. It does not account for which addresses enter each plan and has not been calibrated for them. Scenario successes equal planned consignments times one minus that rate. Cost per scenario success uses that estimate. Revenue would be AED 16 per actual successful consignment, but the prototype records no delivery outcomes, so it cannot measure profit.

Exports separate fleet, distance, overtime, missed-slot and failure-scenario costs. Route metrics show workload, weight, volume, cash and return time. Plan metrics show average duration and workload spread. Actual completions remain zero because the app has no proof-of-delivery import.

The local run makes no paid geocoding, road-routing or model calls. OpenStreetMap tiles require a connection; route lines and stops do not. [Scaling costs](scaling.md) are budget assumptions for a later deployment, not supplier quotes.
