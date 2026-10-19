# Exceptions and fallbacks

| Failure or uncertainty | Detection | Manager action | Verification |
|---|---|---|---|
| Duplicate consignment ID | Ingestion counts all IDs | Quarantine every associated row, correct identity at source | duplicate test, row ledger |
| Negative/missing package values | Finite positive numeric validation | Hold; no guessed correction | ingestion tests |
| Reversed/unusual slot | Normalize time then configured-slot membership | Quarantine, ask shop to confirm | invalid slot tests |
| PO Box or wrong emirate | Address rules and configured service regions | Hold for physical address/correct courier | address report |
| Same building name, conflicting GPS | Historical neighbourhood support threshold | Abstain; ask customer to confirm pin | conflicting-history test |
| Geocoder outage/no key | Provider intentionally disabled | Continue with history and manual review; hold unresolved locations | no-centroid and isolation tests |
| LLM outage | No runtime model dependency | Deterministic parser continues | complete offline run |
| Map tiles unavailable | Leaflet tileerror event | Show map outage message; paths and stop list remain | browser outage test |
| Solver unavailable/timeout | No incumbent/import/runtime error | Deterministic insertion; independent validation | forced-zero-budget test/UI |
| Insufficient fleet | No feasible insertion | Valid partial routes plus explicit unassigned reasons | real sample run |
| Invalid manager assignment | Independent validation after recomputation | Save draft, block approval, allow repair | browser workflow + API tests |
| Driver absence/vehicle breakdown before dispatch | Explicit simulation | Hold affected route only; review and reoptimize separately | exception tests |
| Urgent incoming record | Same ingestion/address pipeline | Append auditable held record; review then reoptimize | urgent intake tests |
| Customer reschedule | Configured supported slot | Recompute affected route, validate again | reschedule test |
| Post-dispatch disruption | Frozen dispatched state | Block global replan; driver contact and manual custody transfer | frozen-state API behavior |
| Backend unavailable | Client request failure | Visible error; use a previously exported printable route sheet | No offline browser database |
| Whole-file unreadable/missing required columns | Import raises error | Stop startup with terminal evidence; restore file from source | No GUI reimport wizard |

The controls simulate events before dispatch. The app cannot record completed stops or route live parcel transfers. After dispatch, keep the frozen plan and coordinate recovery manually.
