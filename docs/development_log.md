# Development log

- Read both briefs in full using extracted PDF text. Inspected all six CSVs and saved exact schema/missing/categorical counts before implementation.
- Established assumptions and requirements matrix before core implementation. Local commit records this milestone.
- Initial ingestion found 23 quarantined consignment rows. Three distinct duplicated IDs involved six raw rows. Normalization preserved source strings.
- Address prediction produced 105 GOOD, 81 AMBIGUOUS, 219 INCOMPLETE and 27 INVALID records. Evaluation ran only after predictions were written to disk.
- Initial baseline execution succeeded. Optimized execution exposed an OR-Tools binding TypeError; fixed the binding and added a real-solver regression test.
- First backend suite had 55 passes and one failed test caused by a blank raw weight in the negative selector. Fixed the test and reran.
- React production build succeeded. Browser launch first failed under the sandbox and required approved local process execution.
- Browser test first timed out due to an overly restrictive label selector. Corrected it to a combobox role selector.
- Browser flow then completed the business actions but caught a Leaflet lifecycle exception. Fixed animation and map/layer cleanup, then reran the flow.
- Changed the baseline to prefer a resolved-area assignment. Its final metrics differ from the earlier lexicographic-address baseline; submission materials use the regenerated output.
- Added history row dispositions, region configuration and historical replay filtering after review. Original data was never modified.
