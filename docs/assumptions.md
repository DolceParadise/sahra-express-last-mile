# Assumption register

The v2 brief controls. These decisions require client confirmation before production.

- The sample has no shift date. Default to 2026-10-14, the day after the last historical date. Date is explicit on every plan. Summer tests use August.
- Weight is total consignment weight. Dimensions describe each piece; volume is dimensions times pieces. A total weight above 30 kg conservatively requires a large van. Heavy and chilled together are held because no supplied vehicle satisfies both rules.
- Duplicate IDs quarantine every involved row. Row keys preserve distinct input identity. Weights and slots need source corrections.
- Standard slots are hard arrival constraints. Nonstandard, reversed and out-of-hours slots are held. Service may finish after slot end but before operating close.
- Use configured area aliases and unique high similarity suggestions with building evidence. Never auto-route an area centre. Masked phones alone cannot establish a destination.
- Historical GPS can be wrong. Require two geographically consistent successful observations and reject isolated outliers. Scores measure that support and have not been calibrated as probabilities.
- Driver work starts at route departure. Loading is outside the modeled shift. Regular shift end is a soft overtime boundary, with a hard ten-hour total and 21:00 return. A 30-minute break occurs by six hours of work when the route exceeds six hours.
- Summer bikes use a conservative early shift ending by 12:30. No afternoon restart is implemented.
- Multi-parcel service means one additional minute per extra consignment; base stop type uses text rules, default apartment eight minutes. COD adds two minutes per COD consignment. Gate adds five minutes per stop.
- Salik and live road restrictions are excluded. Distance is 1.4 times Haversine. Travel integrates peak/off-peak speed boundaries. No paid geocoder or runtime LLM.
- Both planners estimate failure cost with the same overall historical failure rate. This scenario has not been calibrated for the planned addresses. Expected successes are estimates; the app records no deliveries.
- Prototype is local and single-user. SQLite preserves versions and review events. Authentication, concurrent edits and live driver GPS are deferred. No public deployment or data upload.

- Driver departure is fixed to the later of the delivery opening and roster start. The prototype does not search later departures to reduce waiting. This can overstate workload and overtime on evening-only routes.
- Source history ends on 2026-10-13. A selected earlier planning date excludes future historical events, and can have much lower coverage. Each history row records whether matching used it and why.
- The raw roster has 25 AVAILABLE drivers, but only 24 pass validation; overview capacity uses usable records rather than status alone.
