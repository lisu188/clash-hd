# Battle UI Completion Plan

Generated: 2026-05-15

## Scope

Battle UI support is a separate probe-first validation lane. The first release
target is safe complete mode: keep native 640x480 battle UI rendering intact,
center it inside the 800x600 HD surface at offset `(80,60)`, and prove command,
tactical-grid, and modal input routes map displayed coordinates back to native
coordinates.

This report does not promote battle support into the stable/default stage.

## Current Stages

- Stable HD map:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Castle/interior validation:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`
- Battle probe validation:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`

The battle probe validation stage now selects `castlecenter-all` plus the
narrow `battle-ui-center-present-wrapper` group after hidden CDB force-entry
evidence proved the live battle route.

## Existing Passing Evidence To Preserve

- Stable HD map candidate SHA:
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Stable patch-stage status: `118` patched, `0` original, `0` unexpected.
- Fixed castle validation candidate SHA:
  `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`
- Fixed castle overview runs:
  `captures\cdb-surface-dump-20260515-105041`,
  `captures\cdb-surface-dump-20260515-105411`,
  `captures\cdb-surface-dump-20260515-105458`, and
  `captures\cdb-surface-dump-20260515-105557`.

## New Probe Artifacts

- `clash95_battle_ui_catalog_extra.cdb`
- `clash95_battle_ui_present_extra.cdb`
- `clash95_battle_ui_input_extra.cdb`
- `clash95_battle_force_attack_entry_extra.cdb`
- `clash95_battle_force_command_hit_extra.cdb`
- `clash95_battle_force_command_callback_extra.cdb`
- `clash95_battle_force_command_enabled_callback_extra.cdb`
- `clash95_battle_force_grid_hit_extra.cdb`
- `clash95_battle_force_modal_classified_extra.cdb`
- `tools\battle_ui_summary.py`
- `tools\battle_ui_evidence_matrix.py`
- `tools\battle_ui_gate.py`

The CDB templates log `BATTLE_*` rows only. They do not patch code, do not force
input, and do not claim a route is patch-safe.

## Required Evidence Before Additional Battle Patches

- Deterministic hidden/no-popup route into a battle screen.
- Battle surface pointer and size.
- Battle draw/present or copyback call sites with runtime rows.
- Battle command descriptors, callback entry, and callback result branch.
- Tactical-grid hit or coordinate conversion route.
- Modal/dialog route, or explicit not-reached classification.
- No `c0000005`, `BATTLE_AV`, or failure-exit rows.
- Patch-stage report for the battle stage with `original=0` and
  `unexpected=0`.
- Stable HD-map smoke still passing.
- Castle/interior validation unchanged if included.

## Patch Boundary

Do not add any additional groups until probe evidence identifies exact
addresses:

- `battle-ui-center-present`
- `battle-ui-ensure-800-surface`
- `battle-ui-centered-input`
- `battle-grid-centered-input`
- `battle-modal-centered-input`
- `battle-present-bounds`

Do not patch `640`, `480`, `0x27F`, `0x1DF`, tactical-grid dimensions, or
battle draw loops broadly.

## Current Blocker

The repo now has a deterministic harness-only battle-entry route, a passing
initial battle-centering proof, controlled command descriptor hit proof,
harnessed command callback-entry proof, and harness-forced enabled-command
callback-result proof. The natural save-state command callback result is still
`precondition-disabled` (`unit_type=5`, `avail=8`, `enabled=0`), and the
enabled branch is reached only after forcing unit type `8` under CDB, so manual
cadence proof, natural enabled-state proof, the actual tactical-grid
centered-input transform, command/input transform proof, and redraw/input
evidence after the initial battle present remain blockers.

## Fresh Battlecenter Evidence

- Candidate build:
  `C:\ClashTests\battlecenter\clash95_hd_battlecenter_20260515_01.exe`.
- Runtime catalog candidate:
  `C:\ClashTests\battlecenter-catalog\clash95_hd_battlecenter_catalog_20260515_02.exe`.
- Candidate SHA-256:
  `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`.
- Patch-stage manifest:
  `reports\battlecenter_patch_stage_20260515_01.json`.
- Patch-stage status:
  `134` patched, `0` original, `0` unexpected.
- Catalog run:
  `captures\cdb-surface-dump-20260515-114101`.
- Catalog summary:
  `battle_reached=False`, `surface_size=[800,600]`, `av_count=0`.
- Battle gate:
  `captures\battle-ui-gate-20260515-114101.json`, fail-closed because battle
  mode was not reached.
- Static route refinement:
  `0042E9E0` is the likely live battle runner/owner; `0042E5A0`
  `HandleBattleResults` is a later post-battle marker.

## 2026-05-18 Force-Entry And Initial Centering

- Force-entry probe:
  `probes\cdb\battle\clash95_battle_force_attack_entry_extra.cdb`.
- Baseline uncentered battle proof:
  `captures\cdb-surface-dump-20260518-214535`, candidate SHA
  `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`,
  `battle_reached=True`, `battle_ready=True`, `surface_size=[800,600]`.
- Initial centering patch group:
  `battle-ui-center-present-wrapper` patches callsite `0042F2F5` and cave
  `0051BA00`.
- Exact centered proof:
  `captures\cdb-surface-dump-20260518-221018`, candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`,
  `Dump method: cdb-writemem`, `visual_mode=centered-native-640x480`,
  `centered_wrapper_seen=True`, `av_count=0`.

## 2026-05-20 Command Descriptor Hit

- Command-hit probe:
  `probes\cdb\battle\clash95_battle_force_command_hit_extra.cdb`.
- Exact proof:
  `captures\cdb-surface-dump-20260520-094032`, candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`.
- Current summary:
  `captures\battle-ui-command-hit-current.md`, with
  `battle_ready=True`, `visual_mode=centered-native-640x480`,
  `command_hit_ok=True`, `command_native_hit_ok=True`, and `av_count=0`.
- Limitation:
  the probe controls mouse globals and skips turn-banner/frame waits. It proves
  the descriptor hit-test route, not yet natural/manual callback activation.

## 2026-05-20 Command Callback Entry

- Command-callback probe:
  `probes\cdb\battle\clash95_battle_force_command_callback_extra.cdb`.
- Exact proof:
  `captures\cdb-surface-dump-20260520-100717`, candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`.
- Current summary:
  `captures\battle-ui-command-callback-current.md`, with
  `battle_ready=True`, `visual_mode=centered-native-640x480`,
  `command_callback_ok=True`, `command_callback_result_ok=True`, and
  `av_count=0`.
- Limitation:
  this is a harnessed click-gate proof. It reaches descriptor `00514b78` and
  callback `0042D4E0`, then records `branch=precondition-disabled` for
  `unit_index=0`, `unit_type=5`, `avail=8`, `enabled=0`. It does not yet prove
  an enabled command state transition.

## 2026-05-20 Enabled Command Callback Result

- Enabled-command probe:
  `probes\cdb\battle\clash95_battle_force_command_enabled_callback_extra.cdb`.
- Exact proof:
  `captures\cdb-surface-dump-20260520-101859`, candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`.
- Current summary:
  `captures\battle-ui-command-enabled-callback-current.md`, with
  `battle_ready=True`, `visual_mode=centered-native-640x480`,
  `command_callback_ok=True`, `command_callback_result_ok=True`,
  `command_render_begin_skip_seen=True`, and `av_count=0`.
- Limitation:
  this is a harnessed precondition proof. It temporarily changes selected unit
  type `5` to type `8` so the availability table reports `avail=10`,
  `enabled=3`, skips the callback render-begin lock under CDB, and reaches
  `branch=state2`. It does not prove natural/manual input cadence.

## 2026-05-20 Tactical-Grid Coordinate Classification

- Grid-hit probe:
  `probes\cdb\battle\clash95_battle_force_grid_hit_extra.cdb`.
- Exact proof:
  `captures\cdb-surface-dump-20260520-103155`, candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`.
- Current summary:
  `captures\battle-ui-grid-hit-current.md`, with `battle_ready=True`,
  `visual_mode=centered-native-640x480`, `grid_hit_ok=True`, and `av_count=0`.
- Limitation:
  this is a harnessed coordinate-classification proof. The displayed visual
  coordinate `(144,108)` reaches grid cell `(1,1)`, while the native coordinate
  `(64,48)` reaches grid cell `(0,0)`. It proves `0042CB50` is the live grid
  hit-test path and that a centered-input transform is required; it does not
  prove a complete action or natural/manual input cadence.

## 2026-05-20 Modal/Input Path Classification

- Modal-classification probe:
  `probes\cdb\battle\clash95_battle_force_modal_classified_extra.cdb`.
- Exact proof:
  `captures\cdb-surface-dump-20260520-103714`, candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`.
- Current summary:
  `captures\battle-ui-modal-classified-current.md`, with
  `battle_ready=True`, `visual_mode=centered-native-640x480`,
  `modal_classified=True`, and `av_count=0`.
- Limitation:
  this is a no-hit classification for the current forced battle route. It logs
  `BATTLE_MODAL_CLASSIFIED status=input_update_seen_no_modal` at `004605D0`,
  which proves the battle loop input updater was reached without a modal dialog
  opening. It does not prove natural/manual input cadence or a separate modal
  dialog target.

## 2026-05-20 Combined Evidence Matrix

- Matrix tool:
  `tools\battle_ui_evidence_matrix.py`.
- Current output:
  `captures\battle-ui-evidence-current.md` and
  `captures\battle-ui-evidence-current.json`.
- Result:
  PASS. The matrix combines force-entry centering, command hit/callback,
  enabled callback, grid coordinate classification, modal no-hit
  classification, patch-stage bytes, and stable HD-map smoke.
- Limitation:
  `promotion_status=validation_stage_only`. The matrix does not replace
  natural/manual input validation or actual centered-input transform proof.

## Next Steps

1. Done: build the `battlecenter` candidate under `C:\ClashTests\battlecenter`.
2. Done: run `patch_stage_report.py` for the new stage.
3. Done: run the catalog probe through `run_cdb_surface_dump.ps1` on a hidden desktop.
4. Done: add a harness-only deterministic battle-entry route.
5. Done: add and prove the initial native-center battle present wrapper.
6. Done for command descriptors: prove visual and native command hits against
   the centered battle frame.
7. Done for command callback entry: prove descriptor `00514b78` reaches
   `0042D4E0` and records the current disabled precondition branch.
8. Done under harness: force an enabled command precondition and prove
   `0042D4E0` reaches the `state2` result branch.
9. Done under harness: classify the battle tactical-grid hit-test route and
   centered/native coordinate mismatch.
10. Done under harness: classify the modal/input path as
   `input_update_seen_no_modal` on the current forced route.
11. Done: publish a combined repo-only battle evidence matrix over the current
   focused summaries.
12. Next: replace the forced enabled-command precondition with natural/manual
   input evidence.
13. Next: prove actual command/grid centered-input transforms against the
   centered battle frame.
14. Next: prove manual cadence and redraw behavior after the
   initial battle present before broader
   battle-loop patching.
