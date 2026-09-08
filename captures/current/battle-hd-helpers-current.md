# Battle HD Evidence

- Overall: FAIL
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlehd`
- Candidate SHA: `34AF0AEF07B11D2336B91AB33BFB9B72F86A3CBA2F1312A66CFED25BF0BE1D66`
- Runtime candidate: `C:\ClashTests\battle-hd-1280x720\candidate\clash95_hd_surfdump_20260908_105207.exe`
- Byte-verification candidate: `C:\ClashTests\battle-hd-1280x720\clash95_battlehd_review_v2.exe` (same SHA-256)
- Resolution: `[1280, 720]`
- Evidence class: `forced_validation`
- Launch/input: `hidden-desktop-cdb` / `debugger_memory_register_writes_and_direct_calls`
- Wrapper: `memory-only ddraw_surfdump_proxy installed as ddraw.dll; SHA256=AC0989FB869F5AFED7032B3DBECCC095529EA4C789E1039330B9AA2720FF4EFA`
- Promotion: `validation_stage_only`
- Stable stage should change: `False`

| Claim | Result |
|---|---|
| identity | PASS |
| runtime_health | PASS |
| route_catalog | FAIL |
| geometry | FAIL |
| render | FAIL |
| input | FAIL |
| modal | FAIL |
| return | FAIL |
| visible | FAIL |
| unforced_runtime | FAIL |

## Direct helper diagnostics

These forced debugger calls cannot satisfy end-to-end input, rendering, modal, lifecycle, or visible acceptance.

- Sequence completed: `True`
- Observed arena dimensions: `[(16, 7)]`

| Measurement | Result | Meaning |
|---|---|---|
| camera_endpoints | PASS | Forced out-of-range camera values followed by direct clamp calls; keyboard, drag, repeat, and selection recentering are separate claims. |
| mouse_cell_boundaries | PASS | Forced raw mouse values and direct mouse-cell helper returns; no physical or injected input and no grid action callback are inferred. |
| full_tile_projection | PASS | Direct full-redraw call visited each existing visible tile and produced the expected tile origins; copy bounds and final composition remain separate. |
| dirty_tile_projection | PASS | Direct dirty redraw reached and returned from tile (8,0), including its expected pixel origin; natural animation and dirty copy bounds remain separate. |
| hud_descriptor_coordinates | PASS | Six descriptor positions and unchanged callback pointers were read from memory; command enabled/disabled behavior remains unproven. |
| frame_copy_rectangles | PASS | Eight native border/sidebar source rectangles reached the expected destination copy calls; completion and final pixels require separate evidence. |
| present_surface | UNPROVEN | A direct present call saw the 1280x720 software surface; this is not final wrapper composition or a bounds check. |

## Missing or failing evidence

- No OS input, manual observation, visible-wrapper capture, or approval is inferred.
- Actual arena is 16 by 7; this run does not prove a 17-column or horizontally scrollable live arena.
- The dedicated phase14 present-entry marker was absent; accepted tile and helper observations do not imply copy bounds or final composition.
- route_catalog: owner BANNER was not observed
- route_catalog: owner CAMERA was not observed
- route_catalog: owner DIALOG was not observed
- route_catalog: owner DIRTY_REDRAW was not observed
- route_catalog: owner FRAME was not observed
- route_catalog: owner FULL_REDRAW was not observed
- route_catalog: owner GRID was not observed
- route_catalog: owner HUD was not observed
- route_catalog: owner PAN was not observed
- route_catalog: owner PROJECTION was not observed
- geometry: measured expanded battlefield/HUD geometry is missing
- render: FULL_REDRAW has no measured clipping/bounds observation
- render: DIRTY_REDRAW has no measured clipping/bounds observation
- render: battle HD presentation bounds are unproven
- input: grid top_left result is unproven
- input: grid top_right result is unproven
- input: grid bottom_left result is unproven
- input: grid bottom_right result is unproven
- input: grid hud result is unproven
- input: grid outside result is unproven
- input: grid top_padding result is unproven
- input: grid bottom_padding result is unproven
- input: enabled command outcome is unproven
- input: disabled command outcome is unproven
- input: left camera pan/clamp is unproven
- input: right camera pan/clamp is unproven
- input: up camera pan/clamp is unproven
- input: down camera pan/clamp is unproven
- modal: modal open/use/close and restored input are unproven
- return: ordered battle entry/results/Unit_Attack return/map poll was not observed
- return: post-return HD map rendering and input are unproven
- visible: matching visible composition proof is missing
- unforced_runtime: forced route/actions or debugger intervention remain present
