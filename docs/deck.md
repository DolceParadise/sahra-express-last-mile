## 1. 93 consignments ready for review

- 93 planned consignments on 8 routes, with 0 hard violations
- 339 input rows held or unassigned, each with a reason
- The manager can inspect, edit, validate, approve and export a plan.
- Confirm more building locations to increase dispatch coverage.

## 2. Source errors hold 23 rows

- 432 consignment rows, 5856 historical attempts and 89 areas
- Three duplicate IDs affect six rows. All six stay held.
- Missing weights and unsupported slots need source corrections.
- V01 is a bike marked refrigerated. Chilled parcels still require a chilled van.

## 3. Review the shift in one dashboard

- Inspect imports and addresses, then plan, validate and approve.
- Every edit saves a version. Hard violations block approval.
- Driver sheets list stops, parcels, arrival times, cash, breaks and return.
- Screenshot from the running local app.

## 4. 10 of 50 locations predicted

- Coverage 20.0%; 40 records left unresolved
- Among predictions, median error 20.24 m, mean 24.30 m, P90 42.29 m
- Within 50 m: 90.0% of predictions, 18.0% of all references
- Matching needs a building identity and consistent historical GPS.
- Scores measure support. Reference coordinates enter only the evaluator.

## 5. Local planning with a separate validator

- CSV imports keep original values, normalized records and row problems.
- Historical matching supplies eligible stops to OR-Tools and insertion repair.
- A separate validator checks routes before approval and export.
- React displays results. FastAPI handles actions. SQLite saves versions.
- The single-user app needs no paid API or runtime model.

## 6. Invalid edits block approval

- Checks cover capacity, cash, licence, availability and bike limits.
- Chilled parcels require refrigeration and a chilled van. Heavy loads need a large van with a helper.
- Arrivals must meet booked slots. Work includes breaks and hub return.
- Routes allow at most ten hours. Summer bikes return by 12:30.
- Change R01 to a bike to see the block. Restore V17 to repair it.

## 7. More consignments at lower modeled cost

- Area baseline: 90 consignments, 15 routes, 1054.72 km
- Proposed plan: 93 consignments, 8 routes, 664.08 km
- Scenario cost: AED 3,801.61 baseline, AED 2,135.66 proposed
- Per scenario success: AED 50.21 baseline, AED 27.30 proposed
- Both pass validation and use the same historical failure rate.
- Coverage differs. These simulations do not measure actual operating savings.

## 8. Hold affected work before dispatch

- An absence or breakdown holds one route's parcels and preserves other sequences.
- Urgent records start held. Rescheduled routes run through validation again.
- If the solver times out without a solution, insertion supplies a validated fallback.
- When map tiles fail, route lines and stop lists remain available.
- Dispatch freezes the plan. Coordinate later recovery manually.

## 9. Start rollout with one hub

- 80 hubs and 60,000 parcels per day are design targets that still need load tests.
- Queue jobs by client, hub and date. Limit each job's time and resources.
- Measure held parcels, confirmed corrections, review time, address failures and overtime.
- Assumed infrastructure budget: AED 2.32 per hub-day, subject to supplier checks.
- Production needs authentication, road routing, driver location and delivery records.

## 10. Testing caught three generated-code errors

- Codex helped write the code, tests, documents and artifact generators.
- OR-Tools rejected a Python list. Vehicle exclusion constraints fixed the binding.
- Leaflet cleanup failed during navigation. Stopping animations fixed it.
- A test tried to parse a blank weight. The test now handles blanks.
- Saved test results and validated plans record what ran.
- The implementation remains local. Use a private submission channel.