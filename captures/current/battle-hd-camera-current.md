# Battle HD Evidence

- Overall: FAIL
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlehd`
- Candidate SHA: `FACE6859084183EC1F221D966DF6FDB54756746324D136E967AF6CE9A2E44DAA`
- Runtime candidate: `C:\ClashTests\battle-hd-1280x720\candidate\clash95_hd_surfdump_20260908_104050.exe`
- Byte-verification candidate: `C:\ClashTests\battle-hd-1280x720\clash95_battlehd_review.exe` (same SHA-256)
- Resolution: `[1280, 720]`
- Evidence class: `forced_validation`
- Launch/input: `hidden-desktop-cdb` / `debugger_memory_register_writes_and_direct_calls`
- Wrapper: `memory-only ddraw_surfdump_proxy installed as ddraw.dll; SHA256=CB7F65867E9AFAA2DC5659D9B2647E26919B328205970858B56872793BEA9654`
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

- Sequence completed: `False`
- Observed arena dimensions: `[]`

| Measurement | Result | Meaning |
|---|---|---|
| camera_endpoints | UNPROVEN | Forced out-of-range camera values followed by direct clamp calls; keyboard, drag, repeat, and selection recentering are separate claims. |
| mouse_cell_boundaries | UNPROVEN | Forced raw mouse values and direct mouse-cell helper returns; no physical or injected input and no grid action callback are inferred. |
| full_tile_projection | UNPROVEN | Direct full-redraw call visited each existing visible tile and produced the expected tile origins; copy bounds and final composition remain separate. |
| dirty_tile_projection | UNPROVEN | Direct dirty redraw reached and returned from tile (8,0), including its expected pixel origin; natural animation and dirty copy bounds remain separate. |
| hud_descriptor_coordinates | UNPROVEN | Six descriptor positions and unchanged callback pointers were read from memory; command enabled/disabled behavior remains unproven. |
| frame_copy_rectangles | UNPROVEN | Eight native border/sidebar source rectangles reached the expected destination copy calls; completion and final pixels require separate evidence. |
| present_surface | UNPROVEN | A direct present call saw the 1280x720 software surface; this is not final wrapper composition or a bounds check. |

## Forced camera fixture

Arena widths17/20 and unit0 coordinates were forced only around direct clamp/recenter calls. No rendering was allowed with fixture state; natural 17/20-column arenas, camera input, and frame correctness remain separate.

- Original state restored: `True`

| Case | Arena | Camera | Unit0 | Result |
|---|---|---|---|---|
| width17_lower | [17, 7] | [0, 0] | [1, 3] | PASS |
| width17_upper | [17, 7] | [0, 0] | [1, 3] | PASS |
| width20_lower | [20, 7] | [0, 0] | [1, 3] | PASS |
| width20_upper | [20, 7] | [3, 0] | [1, 3] | PASS |
| recenter_left | [20, 7] | [0, 0] | [0, 3] | PASS |
| recenter_right | [20, 7] | [3, 0] | [19, 3] | PASS |
| retain_visible | [20, 7] | [3, 0] | [10, 3] | PASS |

## Forced lifecycle diagnostics

- Sequence completed: `False`
- Observed banner-return mouse: `[]`
- Observed modal-return mouse: `[]`

| Measurement | Result | Meaning |
|---|---|---|
| banner_geometry | UNPROVEN | An inclusive banner rectangle was measured within one pixel of the battlefield center; final colors and pixels are separate. |
| banner_render_hook_restore | UNPROVEN | Measured render and hook pointers matched their saved values after forced banner dismissal. |
| banner_cursor_return | UNPROVEN | The logical cursor must actually read (576,360) at the banner-return observation; intended patch coordinates alone do not pass. |
| disabled_callback_state | UNPROVEN | Unit type and descriptor state were forced before a direct callback; returned state is observed, without physical click or grid-action proof. |
| enabled_callback_state | UNPROVEN | Unit type and descriptor state were forced before a direct callback; returned state is observed, without physical click or grid-action proof. |
| modal_yes_and_render_restore | UNPROVEN | Centered modal geometry, directly forced Yes callback result, and render-pointer restoration were observed in order; No and real input remain unproven. |
| modal_cursor_return | UNPROVEN | The logical cursor must actually read (576,360) after modal restoration. |
| owner_hook_and_map_state_restore | UNPROVEN | Battle owner hook/input bounds matched entry; after Unit_Attack continuation the map poll also matched entry render pointer. This does not prove correct restored pixels or map input. |
| results_and_forced_map_redraw | UNPROVEN | Results and their return preceded the restored map poll and a direct map-redraw return; this is a forced lifecycle diagnostic. |

## Missing or failing evidence

- Width17/20 are explicit debugger fixtures, not naturally generated arena dimensions.
- No rendering occurred while fixture arena state was installed. Natural scrolling, real input, and final composition remain unproven.
- route_catalog: owner BANNER was not observed
- route_catalog: owner CAMERA was not observed
- route_catalog: owner DIALOG was not observed
- route_catalog: owner DIRTY_REDRAW was not observed
- route_catalog: owner ENTRY was not observed
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
