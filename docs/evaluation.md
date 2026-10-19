# Address evaluation and plan comparison

Sample shift: 2026-10-14. Results come from the saved plan and evaluation files. The app has no field outcomes.

## Address coverage and error

The resolver predicted 10 of 50 reference locations and left 40 unresolved. Coverage is 20.0%.
Median error 20.24 m; mean 24.30 m; P90 42.29 m among the 10 predictions. P90 uses nearest rank.

| Threshold | Among predictions | Among all 50 samples |
|---|---:|---:|
| Within 50m | 90.0% | 18.0% |
| Within 100m | 100.0% | 20.0% |
| Within 500m | 100.0% | 20.0% |

The resolver leaves 80% of the reference sample unresolved. Read the error figures alongside that coverage. The 50 selected records may not represent the full shift. Scores measure historical support and have not been calibrated as probabilities.

## Raising the evidence threshold

| Evidence threshold | Predicted / all | Coverage | Median error, metres |
|---|---:|---:|---:|
| 0 | 10 / 50 | 20.0% | 20.24 |
| 0.85 | 10 / 50 | 20.0% | 20.24 |
| 0.9 | 10 / 50 | 20.0% | 20.24 |
| 0.95 | 2 / 50 | 4.0% | 12.91 |
| 0.98 | 1 / 50 | 2.0% | 11.24 |

## Results by address category

| Category | Samples | Predicted | Coverage | Median error, metres |
|---|---:|---:|---:|---:|
| AMBIGUOUS | 9 | 0 | 0.0% | n/a |
| GOOD | 10 | 10 | 100.0% | 20.24 |
| INCOMPLETE | 28 | 0 | 0.0% | n/a |
| INVALID | 3 | 0 | 0.0% | n/a |

## Examples with source records

- C0195: 7.0 m error; HISTORICAL_CLUSTER; evidence H004510, H005696. 2/2 successful GPS observations agree on one building location; 0 outliers excluded.
- C0414: 11.2 m error; HISTORICAL_CLUSTER; evidence H000101, H000129, H000169, H000297, H000367. 56/59 successful GPS observations agree on one building location; 3 outliers excluded.
- C0083: 12.9 m error; HISTORICAL_CLUSTER; evidence H000324, H002589, H005298. 3/3 successful GPS observations agree on one building location; 0 outliers excluded.
- C0165: a hypothetical route to its area centre would have 1480.2 m error. The planner did not route to this centre.
- C0260: a hypothetical route to its area centre would have 1449.7 m error. The planner did not route to this centre.
- C0371: History has 1/1 consistent observations; too few matching observations or conflicting GPS. MANAGER_REVIEW.
- C0091: History does not identify a building location. Confirm the destination with the customer. No coordinate is routed.

## Baseline and proposed planner

Both planners use the same eligibility rules and hard constraints. They plan different numbers of consignments, so compare coverage alongside cost per scenario success. Every route in both plans passed independent validation.

| Metric | Area baseline | Proposed |
|---|---:|---:|
| Planned consignments | 90 | 93 |
| Unassigned raw rows | 342 | 339 |
| Routes | 15 | 8 |
| Approximate km | 1054.72 | 664.08 |
| Fixed AED | 2480.0 | 1420.0 |
| Running AED | 718.76 | 411.09 |
| Overtime AED | 431.33 | 127.34 |
| Outside-slot AED | 0 | 0 |
| Failure-cost scenario AED | 171.52 | 177.23 |
| Total scenario AED | 3801.61 | 2135.66 |
| Predicted successes, scenario | 75.71 | 78.23 |
| AED per scenario success | 50.21 | 27.3 |
| Mean route minutes | 476.7 | 530.4 |
| Workload standard deviation, min | 147.7 | 35.1 |
| Mean weight utilization | 0.167 | 0.379 |

The modeled cost difference is AED 1665.95. Planned consignments differ by 3. No field comparison with the dispatcher was run.
Historical failure scenario: 15.9%. Both plans have 100.0% of planned arrivals in slot. Actual completed deliveries: 0.
Reported planner computation: baseline 0.089 s; proposed 1.296 s. These exclude ingestion/address resolution and vary by machine. The five-second solver limit excludes import, address matching and repair.

## Production measures

Track address failures per attempt, confirmed corrections, reused locations, review minutes, unresolved addresses and changes after dispatch. Check scores against verified destinations. Always report coverage with location error. Compare hub-days with similar parcels and fleet availability before replacing the dispatcher's process.
