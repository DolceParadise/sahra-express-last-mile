# AI usage and verification

OpenAI Codex inspected the supplied PDFs and CSVs, wrote Python and TypeScript, implemented routing and validation, ran tests and prepared the documents. No other person or delegated agent produced or reviewed this submission. The app uses no runtime LLM or paid inference service and sends no address text to a geocoder or AI service.

The presenter still needs to review the work and understand its decisions. Automated tests check execution; they do not replace human code review. Python audited all six CSVs. Both briefs were read through `pdftotext`; the v2 export contract takes precedence. The plan validator imports no planner code. It shares geometry, time and configuration helpers.

Testing found three development errors:

1. The first OR-Tools integration called `SetAllowedVehiclesForIndex(list, index)`. Version 9.15 rejected the list with a TypeError involving `absl::Span<int const>`. The optimized run failed after the baseline succeeded. Per-vehicle exclusions on `VehicleVar` replaced that call. `test_actual_solver_compatibility_binding` now runs the installed solver, and the independent validator checks its output.
2. Leaflet cleanup removed a map during a zoom animation. Browser navigation reported `Cannot read properties of undefined (reading '_leaflet_pos')`. The fix disabled animations, stopped the map before removal and guarded layer cleanup. The browser test now checks for errors after the editing and export flow.
3. The negative-weight test called `float` on a blank raw value. Ingestion handled the blank, but the test failed. The test now skips blanks when selecting negative weights. The audit continues to count missing and negative weights separately.

Some commands also failed because they ran from the wrong directory. Dependency downloads, loopback binding and Chromium needed approved access outside the sandbox. Explicit paths and approved process access resolved those failures.

See [verification](verification.md), `outputs/tests.log`, `outputs/browser-tests.json`, `outputs/comparison.json` and `outputs/evaluation.json`. Screenshots come from the running app. Deck metrics come from generated JSON. GitHub metadata showed a public remote at verification time; the implementation and supplied material remain local.
