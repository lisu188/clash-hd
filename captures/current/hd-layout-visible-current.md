# HD Layout Visible Evidence Summary

- Generated: `2026-07-18T10:41:24+02:00`
- Run: `captures\archive\visual-smoke-20260713-075818`
- Candidate SHA-256: `911A4F1CFB3CFEE7974F50742CC98FDD16DCC82EAA95C88F748E0976140E6FBD`
- Result: `PASS`
- Evidence class: `approved_visible_automated_layout_composition`
- Pass scope: Authentic visible 800x600 composition of the relocated terrain tooltip and active command-panel sprites, with exact automated Win32 hover placement.
- Manual DirectInput proof: `false`
- Command-click alignment: `false`
- Panel callback proof: `false`
- Stable-stage promotion ready: `false`
- Promotion ready: `false`

## Checks

| Check | Result |
| --- | --- |
| `candidate_identity` | `PASS` |
| `map_capture_authenticity` | `PASS` |
| `hover_capture_authenticity` | `PASS` |
| `gameplay_route` | `PASS` |
| `tooltip_bottom_center_visible` | `PASS` |
| `tooltip_legacy_location_absent` | `PASS` |
| `pre_fix_baseline_context` | `PASS` |
| `panel_right_bottom_visible` | `PASS` |
| `panel_legacy_location_unchanged` | `PASS` |
| `automated_hover_alignment` | `PASS` |
| `capture_tear_advisory_clean` | `PASS` |
| `process_liveness_until_cleanup` | `PASS` |

## Measured Layout

- Tooltip neutral-bright pixels: `516`; bounds: `{'x': 528, 'y': 880, 'right': 655, 'bottom': 896, 'width': 128, 'height': 17, 'center_x': 591.5, 'center_y': 888.0}`.
- Active panel diff: `99.936%`; bounds: `{'x': 912, 'y': 792, 'right': 1008, 'bottom': 888, 'width': 97, 'height': 97}`.
- Full six-slot panel-region diff: `30.231%`.
- Automated hover point: requested `[640, 544]`, actual `[640, 544]`, error `[0, 0]`.

## Failed Panel Click Attempt

- Attempt observed: `true`
- Requested client point: `[760, 560]`
- Actual client point: `[716, 493]`
- Client error: `[-44, -67]`
- Path verified: `false`
- Click path verified: `false`
- Alignment passed: `false`
- Classification: The requested screen point extended beyond the active desktop; Win32 clamped the cursor, so this attempt proves neither descriptor-5 click alignment nor a callback.

## Limitations

- The descriptor-5 click attempt was clamped by the desktop edge and failed alignment.
- SetCursor/GetCursorPos agreement is automated Win32 evidence, not manual DirectInput proof.
- Only active descriptors 0 and 3 are visibly populated in this save state; hidden CDB evidence covers all six coordinates.
- The tear result is an advisory content/ROI heuristic, not proof that a desktop grab is tear-free.
- This validation-only candidate is not the protected stable/default stage and this report does not promote it.
- A short/long soak, castle/battle continuity, and release validation remain separate gates.
