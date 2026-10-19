# Scaling proposal

The prototype is a local, single-user, hub planner. It has not been load-tested at 60,000 parcels/day.

At 80 hubs, partition all input, versions, overrides and travel caches by tenant, hub and shift date. Replace SQLite with Postgres and append-only object storage for source files. Index tenant/hub/date/version, normalized building identity and region-scoped confirmed address keys. Store source checksum, schema version, configuration version and resolver version with each job. Enforce tenant identity at every query and encrypt operational locations with restricted retention.

Move generation to independent queue jobs per hub/date. Use fair scheduling and per-tenant concurrency budgets, bounded matrix size, solver time limits and cancellation. Schedule jobs before local hub deadlines and isolate failures by job. Avoid global fleet optimization across countries. A worker pool scales horizontally with hub jobs; regional workers keep data and privacy policies local. Versioned country configs define licence, cash, heat, driving hours, units, currency, service regions and cost rules.

Normalize and deduplicate addresses before lookup. Reuse customer-confirmed building coordinates with provenance and expiry. Require confirmed evidence before saving a location to the shared cache. A key includes region, area, building and villa identity. Maintain time-bucketed road matrices per vehicle class; 400 stops produce 160,000 origin-destination entries before deduplication. Geographic clustering and incremental matrix updates reduce work. Regional road routing is a later improvement to the 1.4 approximation.

Alert on planning deadline misses, no solver solution, independent hard findings, increased holds, stale confirmations, external outage, queues and failed imports. Track p95 end-to-end duration, version conflicts, tenant query failures and solver outcomes. Operational metrics include customer-confirmed correction rate, address failures per attempt, reuse of validated locations, review minutes, abstention, post-dispatch corrections, cash and overtime guardrails, workload spread, and score calibration against verified destinations. Roll out in shadow mode, then one hub with manager sign-off, then staged regional expansion.

Proposed daily infrastructure budget per hub. Each price below is an assumption that needs a supplier check.

| Component | Explicit assumption | Assumed AED/hub-day |
|---|---|---:|
| Geocoding | 40 uncertain addresses at assumed AED 0.02/query | 0.80 |
| Runtime model inference | Deterministic pipeline, no calls | 0 |
| Road routing | Shared regional service allocated AED 40/day across 80 hubs | 0.50 |
| Planning compute | 2 vCPU-minutes at assumed AED 0.01/vCPU-minute | 0.02 |
| Storage/monitoring | Assumed AED 80/day allocated across 80 hubs | 1.00 |
| Total | Excludes labour, mobile devices, network and support | 2.32 |

Check supplier prices and benchmark resource use before adopting this budget. The actual local run uses no external geocoding, inference or road API. Input ingestion, matrix construction and insertion repair also consume time beyond the solver budget.
