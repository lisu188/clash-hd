# Framed map resolution observations

Recorded 2026-09-06. All six software captures pass exact four-border, footer and six-cell action-bar checks. Two bounded runtime gates pass; the other outcomes remain failed.

| Resolution | Runtime | Initial trace | Frame and footer | Action bar |
| --- | --- | --- | --- | --- |
| 800x600 | FAIL: duplicate native exit | FAIL | Exact | 6/6 exact |
| 1024x768 | PASS | PASS | Exact | 6/6 exact |
| 1280x720 | FAIL: image heuristic; final summary absent | PASS | Exact | 6/6 exact |
| 1280x960 | FAIL: image heuristic; final summary absent | PASS | Exact | 6/6 exact |
| 1920x1080 | FAIL: image heuristic; final summary absent | PASS | Exact | 6/6 exact |
| 802x602 | PASS | PASS | Exact | 6/6 exact |

The larger images retain the `low_overall_gameplay_coverage` warning. The 1280x720 diagnostic explains all 100 blank cells with zero visibility; a stricter source-bound fog decision is being implemented separately. No failed artifact is reclassified here.

The minimap viewport rectangle still requires correction and separate evidence. Castle overview, battle and all castle-building screens are now requested checks. Their inherited native/modal paths are not accepted by these ordinary-map results.

[Detailed bindings and original outcomes](framed-map-resolution-matrix-current.json). No stable promotion or visible/manual proof.
