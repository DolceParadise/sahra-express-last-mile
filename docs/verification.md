# Executed verification

The browser checks follow a hub manager through the supplied shift. The manager inspects addresses, generates routes and makes an invalid assignment. Approval blocks the edit. The manager repairs it, approves and exports the version.

| Boundary | Result | Execution evidence |
|---|---|---|
| Python unit/integration suite | PASS, 61 tests | `outputs/tests.log`, Pytest exit zero; four dependency deprecation warnings |
| React TypeScript + Vite production build | PASS | `npm --prefix frontend run build`, generated bundle in frontend/dist |
| Actual server startup | PASS | Uvicorn bound to 127.0.0.1:8000 and served dashboard/assets/API |
| UI, API and imported data | PASS | Six Playwright tests against real source CSVs, `outputs/browser-tests.json` |
| Cold initial browser load | PASS | Final browser run starts a fresh process; expectation allows 15 seconds for evidence initialization |
| Generate -> independent validator | PASS | Both offline plans have zero hard findings; every raw row assigned or explicitly unassigned |
| Manager invalid edit -> blocked approval -> repair | PASS | Chilled route changed to bike, hard findings shown, approval disabled; restored van and approved |
| Reorder/move/hold/driver change | PASS | Real API rebuild and validation tests; holds persist across reoptimization |
| Approval/version/export | PASS | Saved versions, JSON required fields, printable driver route sheets and browser download |
| Map outage and selective absence | PASS | Tile requests deliberately aborted; geometry/list available; only affected route held, other sequences identical |
| Address evaluation isolation | PASS | Production modules have no evaluation-set access; file-open denial test; predictions saved before truth opened |
| Real loopback HTTP job | PASS | `outputs/http_smoke.json` contains actual request timing, zero hard findings and approval/export checks |
| Deck/artifact consistency | PASS | PDF has 10 pages; report/deck/sample JSON read generated plan/evaluation artifacts |
| Confidential submission | LOCAL ONLY | No push/deployment. Cached origin/main contains only .gitignore, LICENSE and original README. GitHub metadata reported public. |

The solver defaults to five seconds. The declared HTTP smoke budget is 30 seconds after initialization; the observed request time is in `outputs/http_smoke.json`. These timings do not establish a production service guarantee. Initial historical evidence construction is separate and cached for the process lifetime. Alias lookups are memoized. Route distances are approximations, and planned on-time arrival is not actual successful delivery.

The first browser attempt against a fresh backend exceeded Playwright's default five-second expectation while historical evidence initialized. The application remained in its explicit loading state. Repeated alias lookups were cached, the test allowed 15 seconds for initialization, and the initial three-test suite passed. Earlier Leaflet and OR-Tools failures are described in ai_usage.md and were corrected before final verification.

Reproduction commands were run from the project root:

```sh
.venv/bin/python scripts/audit.py
.venv/bin/python -m scripts.run
.venv/bin/python -m pytest -q
npm --prefix frontend run build
.venv/bin/python -m scripts.submission
npm --prefix frontend exec -- playwright test --config frontend/playwright.config.ts
```

The browser tests and `python -m scripts.http_smoke` need the README server command running first. PDF text was inspected with pdftotext, page count checked with pdfinfo and a rendered slide inspected visually. The native application was tested on Python 3.14.7 and Node 26.10.0 on macOS ARM. Docker was not built or run. Authentication, live driver location, proof of delivery, parcel transfer recovery, completed deliveries and 60,000-parcel load remain untested or unimplemented. See the requirements matrix for each status. The remote must be made private or replaced by a private submission channel before sharing confidential content.

The subsequent coss UI refresh passed six browser checks and a new TypeScript/Vite build. See [UI refresh](ui_refresh.md) for the expanded keyboard, focus, native form and mobile checks. Earlier three-test results describe the initial implementation.

The copy edit passed 61 backend tests, the production build and all six browser checks. The report, evaluation, driver sheets and ten-page PDF were regenerated. PDF text and rendered slides were inspected. Route counts, costs and address-evaluation results match the previous run.
