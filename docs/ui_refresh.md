# coss interface refresh

All seven manager screens use official coss components and the neutral theme. The overview shows source counts, fleet availability, address coverage, records needing review and routes from the current plan. The sidebar groups screens by workspace, dispatch and operations.

Forms use coss fields, inputs and selects. Evidence opens in scrollable dialogs. Native required fields still block incomplete submissions. Assignment, review, approval, dispatch and export controls call the existing API.

The refresh passed these checks:

- TypeScript and Vite production build.
- Six Playwright tests against the local backend and supplied CSVs.
- Plan generation, address inspection, invalid assignment, blocked approval, repair and JSON download.
- Keyboard selection, dialog focus restoration, required fields, tile outage and selective driver absence.
- All screens and an evidence dialog at a 390-pixel viewport.

The mobile test found an evidence button that overflowed. Its CSS targeted the button slot, but the composed dialog trigger had a different slot. A class selector fixed it. Keyboard tests now wait for focus before sending navigation keys. The route test selects R01 explicitly so a saved partial plan cannot change the route under test.

Screenshots are in `outputs`. [Component notes](../frontend/COMPONENTS.md) record the sources, licensing and composition rules. The refresh preserved backend rules and source data. It was verified locally.
