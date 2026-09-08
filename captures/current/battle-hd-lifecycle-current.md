# Battle HD Evidence

- Overall: FAIL
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlehd`
- Candidate SHA: `34AF0AEF07B11D2336B91AB33BFB9B72F86A3CBA2F1312A66CFED25BF0BE1D66`
- Runtime candidate: `C:\ClashTests\battle-hd-1280x720\candidate\clash95_hd_surfdump_20260908_105408.exe`
- Byte-verification candidate: `C:\ClashTests\battle-hd-1280x720\clash95_battlehd_review_v2.exe` (same SHA-256)
- Resolution: `[1280, 720]`
- Evidence class: `forced_validation`
- Launch/input: `hidden-desktop-cdb` / `debugger_memory_register_writes_and_direct_calls`
- Wrapper: `memory-only ddraw_surfdump_proxy installed as ddraw.dll; SHA256=A515F5D101B73F06786FCEBE44921062F1D10A0C5DA403D9BD424EC3957B2EBF`
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

## Forced lifecycle diagnostics

- Sequence completed: `True`
- Observed banner-return mouse: `[[4, 360]]`
- Observed modal-return mouse: `[[576, 360]]`

| Measurement | Result | Meaning |
|---|---|---|
| banner_geometry | PASS | An inclusive banner rectangle was measured within one pixel of the battlefield center; final colors and pixels are separate. |
| banner_render_hook_restore | PASS | Measured render and hook pointers matched their saved values after forced banner dismissal. |
| banner_cursor_return | UNPROVEN | The logical cursor must actually read (576,360) at the banner-return observation; intended patch coordinates alone do not pass. |
| disabled_callback_state | PASS | Unit type and descriptor state were forced before a direct callback; returned state is observed, without physical click or grid-action proof. |
| enabled_callback_state | PASS | Unit type and descriptor state were forced before a direct callback; returned state is observed, without physical click or grid-action proof. |
| modal_yes_and_render_restore | PASS | Centered modal geometry, directly forced Yes callback result, and render-pointer restoration were observed in order; No and real input remain unproven. |
| modal_cursor_return | PASS | The logical cursor must actually read (576,360) after modal restoration. |
| results_geometry | PASS | The shared results message measured native size at the battlefield center while battle-specific scope was1. |
| results_copy_rectangles | PASS | Results background save/restore copy calls used matching rectangles and the same temporary buffer; final pixels remain separate. |
| results_scope_restore | PASS | After results dismissal, battle-specific scope returned0 and the renderer matched its saved pointer. |
| cursor_targets_queued | PASS | Banner, modal, and results queued(576,360) before the immediate input poll; this does not prove the poll retained that target. |
| results_cursor_return | UNPROVEN | The results cursor must still read(576,360) after its immediate input poll. |
| owner_hook_and_map_state_restore | PASS | Battle owner hook/input bounds matched entry; after Unit_Attack continuation the map poll also matched entry render pointer. This does not prove correct restored pixels or map input. |
| results_and_forced_map_redraw | PASS | Results and their return preceded the restored map poll and a direct map-redraw return; this is a forced lifecycle diagnostic. |

## Missing or failing evidence

- The previously observed right-edge battle-sidebar residue is absent from this candidate's hidden post-return PNG. This verifies removal of that specific software-surface residue, not full map composition or visible-wrapper rendering.
- New queued/post-poll markers separate cursor assignment from polling: banner, modal, and results queue(576,360), while banner/results polls produce(4,360). The parser keeps those two cursor-return checks unproven.
- No natural or manual command input is inferred from direct callback calls.
- The hidden software surface does not prove final visible-wrapper colors, composed HUD/minimap layers, or natural map input.
- Banner and results queued logical cursor(576,360), but their immediate input polls replaced X with4. Modal cursor retained(576,360); visible input behavior remains unproven.
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
