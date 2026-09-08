# Bottom-right action bar: current screenshots fail full composition

Inspected **all six existing screenshots** under the current task's
`C:\ClashCaptures\combinedui-hidden` and `C:\ClashCaptures\hd-completion`
roots on 2026-09-05. The [pixel audit](action-bar-screenshot-audit-current.json)
binds every summary, raw surface, PNG, candidate, resolution, and source asset.

| Capture | Resolution | Complete source-matching cells | Observation |
| --- | --- | --- | --- |
| 20260905-115001 | 800×600 | 0/6 | Action bar absent at the expected bottom-right anchors. |
| 20260905-115157 | 1024×768 | 3/6 | Lower row matches exactly; upper row is partly overwritten. |
| 20260905-122508 | 800×600 | 0/6 | Action bar absent. |
| 20260905-124215 | 800×600 | 0/6 | Synthetic geometry passed, but the resulting screenshot lacks the bar. |
| 20260905-130340 | 800×600 | 0/6 | Post-day v5 capture lacks the bar. |
| 20260905-135344 | 800×600 | 0/6 | Post-day v6 capture lacks the bar. |

The six 64×32 cells should start at `(W−192,H−72)`, with three columns
and two rows. At 1024×768, the lower cells at `(832,728)`, `(896,728)`, and
`(960,728)` exactly match source sprites 6, 8, and 10. The upper cells at
Y=696 retain exact source rows 24–31; their first row is also an exact match,
but mostly missing rows 1–23 prevent a complete-cell pass. At 800×600 the
expected bar occupies X=608–799, Y=528–591.

The audit compares the unchanged indexed raw capture against opaque
`MAP_BUTT.S32` source variants and the native hover overlay. It performs no
image edits, palette conversion, exclusion masks, resampling, or tolerance.
Seven focused tests cover multiple resolutions, hover, a single missing
pixel, partial overwrites, legacy placement, malformed inputs, and tampering
with the PNG/raw/palette/candidate bindings. PNG bytes must match the recorded
raw surface and palette; this check reconstructs bytes in memory and does not
edit the screenshot.

These are failures of the captured software composition. Hidden captures
can omit separately composed layers; these results alone do not establish
the final visible wrapper's behavior. Passing draw-coordinate markers and
terrain gates remain separate evidence. No manual input or promotion is
proved, and the accepted historical right-bottom natural-draw ruling is
unchanged. New screenshots must receive the same complete action-bar check.
