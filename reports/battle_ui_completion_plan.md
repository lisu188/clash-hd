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
- Battle centered-input probe validation:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter-inputprobe`

The battle probe validation stage now selects `castlecenter-all` plus the
narrow `battle-ui-center-present-wrapper` group after hidden CDB force-entry
evidence proved the live battle route.
The inputprobe stage adds validation-only battle grid and descriptor input
wrappers after route evidence identified the exact callsites.

## Existing Passing Evidence To Preserve

- Stable HD map candidate SHA:
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Stable patch-stage status: `118` patched, `0` original, `0` unexpected.
- Fixed castle validation candidate SHA:
  `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`
- Fixed castle overview runs:
  `captures\archive\cdb-surface-dump-20260515-105041`,
  `captures\archive\cdb-surface-dump-20260515-105411`,
  `captures\archive\cdb-surface-dump-20260515-105458`, and
  `captures\archive\cdb-surface-dump-20260515-105557`.

## New Probe Artifacts

- `probes/cdb/battle/clash95_battle_ui_catalog_extra.cdb`
- `probes/cdb/battle/clash95_battle_ui_present_extra.cdb`
- `probes/cdb/battle/clash95_battle_ui_input_extra.cdb`
- `probes/cdb/battle/clash95_battle_force_attack_entry_extra.cdb`
- `probes/cdb/battle/clash95_battle_force_command_hit_extra.cdb`
- `probes/cdb/battle/clash95_battle_force_command_callback_extra.cdb`
- `probes/cdb/battle/clash95_battle_force_command_enabled_callback_extra.cdb`
- `probes/cdb/battle/clash95_battle_force_grid_hit_extra.cdb`
- `probes/cdb/battle/clash95_battle_force_modal_classified_extra.cdb`
- `probes/cdb/battle/clash95_battle_centered_input_wrapper_extra.cdb`
- `probes/cdb/battle/clash95_battle_post_ready_redraw_extra.cdb`
- `tools\battle_ui_summary.py`
- `tools\battle_ui_evidence_matrix.py`
- `tools\battle_ui_gate.py`
- `scripts/cdb/run_cdb_battle_visible_input_probe.ps1`
- `tools\raw_sendinput_click.py`
- `tools\battle_visible_input_summary.py`
- `tools\battle_visible_harness_guard.py`

The CDB templates log `BATTLE_*` rows only. They do not patch code, do not force
input, and do not claim a route is patch-safe.

## Required Evidence Before Additional Battle Patches

- Deterministic hidden/no-popup route into a battle screen.
- Battle surface pointer and size.
- Battle draw/present or copyback call sites with runtime rows.
- Battle command descriptors, callback entry, and callback result branch.
- Tactical-grid hit or coordinate conversion route.
- Post-ready battle-loop present/copyback sampling after `BATTLE_READY`.
- Modal/dialog route, or explicit not-reached classification.
- No `c0000005`, `BATTLE_AV`, or failure-exit rows.
- Patch-stage report for the battle stage with `original=0` and
  `unexpected=0`.
- Stable HD-map smoke still passing.
- Castle/interior validation unchanged if included.

## Patch Boundary

Do not add any additional groups until probe evidence identifies exact
addresses. The validation-only centered-input groups now have exact wrapper
proof but still require natural/manual cadence before promotion:

- `battle-ui-center-present`
- `battle-ui-ensure-800-surface`
- `battle-ui-centered-input` validation group exists, promotion blocked
- `battle-grid-centered-input` validation group exists, promotion blocked
- `battle-modal-centered-input`
- `battle-present-bounds`

Do not patch `640`, `480`, `0x27F`, `0x1DF`, tactical-grid dimensions, or
battle draw loops broadly.

## Current Blocker

The repo now has a deterministic harness-only battle-entry route, a passing
initial battle-centering proof, controlled command descriptor hit proof,
harnessed command callback-entry proof, harness-forced enabled-command
callback-result proof, and post-ready present/copyback sampling. The natural
save-state command callback result is still
`precondition-disabled` (`unit_type=5`, `avail=8`, `enabled=0`), and the
enabled branch is reached only after forcing unit type `8` under CDB. The
current availability scan finds zero naturally enabled units in this forced
battle fixture, and the current save-slot scan finds zero naturally enabled
units across slots `0`, `1`, and `2` while slots `3`, `4`, and `5` time out
before unit scan under the hidden CDB route. A read-only save-file inventory
parses all six local `.dat` saves directly and still finds zero naturally
enabled command units; those saves only expose Peasant, Light infantry, Light
cavalry, Highlander, and Builder. The command table target list now names the
enabled types to hunt for next: Dragon cavalry, Archer, Crossbower, Musketeer,
Catapult, Cannon, Forester, Cyklop, Wizard, Winger, and Dragon. Manual cadence
proof and a richer natural enabled-state source remain blockers. The actual
battle grid and descriptor
centered-input wrapper mechanics are now validation-proven under CDB, but helper
bodies are skipped after entry in that focused proof.

The visible-input bridge now proves that a real visible-window run can reach
the battle command input window with descriptor list `00514b78` and expected
displayed/native command point `(588,440)->(508,380)`. It does not yet prove
that a real OS click is consumed by the command descriptor or reaches callback
`0042D4E0`. Current focused battle/right-bottom command-lane completion is
`99.91%`; full-game reverse engineering is not `100%`.

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
  `captures\archive\cdb-surface-dump-20260515-114101`.
- Catalog summary:
  `battle_reached=False`, `surface_size=[800,600]`, `av_count=0`.
- Battle gate:
  `captures\archive\battle-ui-gate-20260515-114101.json`, fail-closed because battle
  mode was not reached.
- Static route refinement:
  `0042E9E0` is the likely live battle runner/owner; `0042E5A0`
  `HandleBattleResults` is a later post-battle marker.

## 2026-05-18 Force-Entry And Initial Centering

- Force-entry probe:
  `probes\cdb\battle\clash95_battle_force_attack_entry_extra.cdb`.
- Baseline uncentered battle proof:
  `captures\archive\cdb-surface-dump-20260518-214535`, candidate SHA
  `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`,
  `battle_reached=True`, `battle_ready=True`, `surface_size=[800,600]`.
- Initial centering patch group:
  `battle-ui-center-present-wrapper` patches callsite `0042F2F5` and cave
  `0051BA00`.
- Exact centered proof:
  `captures\archive\cdb-surface-dump-20260518-221018`, candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`,
  `Dump method: cdb-writemem`, `visual_mode=centered-native-640x480`,
  `centered_wrapper_seen=True`, `av_count=0`.

## 2026-05-20 Command Descriptor Hit

- Command-hit probe:
  `probes\cdb\battle\clash95_battle_force_command_hit_extra.cdb`.
- Exact proof:
  `captures\archive\cdb-surface-dump-20260520-094032`, candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`.
- Current summary:
  `captures\current\battle-ui-command-hit-current.md`, with
  `battle_ready=True`, `visual_mode=centered-native-640x480`,
  `command_hit_ok=True`, `command_native_hit_ok=True`, and `av_count=0`.
- Limitation:
  the probe controls mouse globals and skips turn-banner/frame waits. It proves
  the descriptor hit-test route, not yet natural/manual callback activation.

## 2026-05-20 Command Callback Entry

- Command-callback probe:
  `probes\cdb\battle\clash95_battle_force_command_callback_extra.cdb`.
- Exact proof:
  `captures\archive\cdb-surface-dump-20260520-100717`, candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`.
- Current summary:
  `captures\current\battle-ui-command-callback-current.md`, with
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
  `captures\archive\cdb-surface-dump-20260520-101859`, candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`.
- Current summary:
  `captures\current\battle-ui-command-enabled-callback-current.md`, with
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
  `captures\archive\cdb-surface-dump-20260520-103155`, candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`.
- Current summary:
  `captures\current\battle-ui-grid-hit-current.md`, with `battle_ready=True`,
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
  `captures\archive\cdb-surface-dump-20260520-103714`, candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`.
- Current summary:
  `captures\current\battle-ui-modal-classified-current.md`, with
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
  `captures\current\battle-ui-evidence-current.md` and
  `captures\current\battle-ui-evidence-current.json`.
- Result:
  PASS. The matrix combines force-entry centering, command hit/callback,
  enabled callback, grid coordinate classification, centered-input wrapper
  proof, post-ready redraw/copyback sampling, command availability scanning,
  modal no-hit classification, battlecenter and inputprobe patch-stage bytes,
  visible command-readiness evidence, and stable HD-map smoke.
- Limitation:
  `promotion_status=validation_stage_only`. The matrix does not replace
  real visible click-to-callback proof or natural/manual input validation.

## 2026-05-20 Centered Input Wrapper Proof

- Input-wrapper probe:
  `probes\cdb\battle\clash95_battle_centered_input_wrapper_extra.cdb`.
- Patch groups:
  `battle-grid-centered-input` wraps the `0042E4ED -> 0042CB50` tactical-grid
  call through cave `0051BAA0`; `battle-ui-centered-input` wraps the
  `0042E501 -> 00419DC0` descriptor call through cave `0051BAF0`.
- Exact proof:
  `captures\archive\cdb-surface-dump-20260520-111115`, candidate SHA
  `F84933776944E2B616F6BBCCF7708ABBF06498D5438FA8DF7B7AF1BB56CD180A`.
- Current summary:
  `captures\current\battle-ui-centered-input-current.md`, with `battle_ready=True`,
  `visual_mode=centered-native-640x480`, `grid_input_wrapper_ok=True`,
  `descriptor_input_wrapper_ok=True`, `centered_input_wrapper_ok=True`, and
  `av_count=0`.
- Limitation:
  this is a wrapper-mechanics proof. The probe logs pre/inner/post coordinates
  and intentionally skips each helper body after entry, so it does not replace
  natural/manual input cadence or enabled-command state validation.

## 2026-05-20 Post-Ready Redraw/Copyback Proof

- Post-ready redraw probe:
  `probes\cdb\battle\clash95_battle_post_ready_redraw_extra.cdb`.
- Exact proof:
  `captures\archive\cdb-surface-dump-20260520-195244`, candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`.
- Current summary:
  `captures\current\battle-ui-post-ready-redraw-current.md`, with
  `battle_ready=True`, `visual_mode=centered-native-640x480`,
  `post_ready_presents=9`, `post_ready_copybacks=6`,
  `post_ready_grid_attempts=1`, `post_ready_redraw_sample_ok=True`, and
  `av_count=0`.
- Limitation:
  this is still a hidden CDB forced battle route. It proves the later battle
  loop keeps presenting/copying the centered 800x600 surface after
  `BATTLE_READY`; it does not prove natural/manual enabled-command cadence.

## 2026-05-20 Command Availability Scan

- Availability scanner:
  `tools\battle_command_availability.py`.
- Current summary:
  `captures\current\battle-command-availability-current.md`, sourced from
  `captures\archive\cdb-surface-dump-20260520-195244` and `C:\Clash\clash95.exe`.
- Result:
  18 battle unit records were parsed. The selected natural unit is type `5`
  with `availability=8` and `enabled=0`; every natural unit type present in
  the fixture has `enabled=0`. The executable table scan through unit type
  `31` finds 11 command-enabled unit types, giving concrete target types for a
  richer battle fixture.
- Limitation:
  this is a repo-only/static classification of the current forced battle
  fixture. It explains why the enabled callback proof needs the type-8 CDB
  override, but it does not replace natural/manual input evidence from a richer
  battle state.

## 2026-05-20 Battle Save-Slot Scan

- Harness change:
  `scripts/cdb/run_cdb_surface_dump.ps1 -LoadSlot <0..9>` now generates load-menu
  coordinates instead of using the old hardcoded slot-0 coordinate.
- Unit-scan probe:
  `probes\cdb\battle\clash95_battle_unit_scan_extra.cdb`.
- Summary:
  `captures\current\battle-slot-scan-current.md`.
- Result:
  `run_count=6`, `routed_slot_count=3`,
  `timeout_before_unit_scan_count=3`, and
  `natural_enabled_unit_count=0`. Slots `0` and `1` expose the same 18-unit
  disabled roster, slot `2` exposes one disabled type-0 unit, and slots `3`
  through `5` time out before unit scan under the current route.
- Limitation:
  this is a local-save inventory pass, not a natural/manual enabled-command
  proof. It narrows the next search to a different save, constructed battle
  state, or manual cadence capture.

## 2026-05-20 Battle Save-File Inventory

- Inventory tool:
  `tools\battle_save_unit_inventory.py`.
- Summary:
  `captures\current\battle-save-unit-inventory-current.md`.
- Result:
  the save-file unit-record layout is present at offset `0x00023EF6`, which is
  16 bytes after the runtime game-data unit offset `0x00023EE6`. The tool reads
  all six `C:\Clash\save\*.dat` files, parses 63 units total, and reports
  `natural_enabled_unit_count=0`. The decoded local-save unit types are
  Peasant, Light infantry, Light cavalry, Highlander, and Builder.
- Target names:
  the executable command table scan now decodes the enabled unit types through
  type `31` as Dragon cavalry, Archer, Crossbower, Musketeer, Catapult, Cannon,
  Forester, Cyklop, Wizard, Winger, and Dragon.
- Constructed fixture:
  `tools\battle_constructed_save_fixture.py` wrote a copied-save mutation
  without editing `C:\Clash\save`. The current report
  `captures\current\battle-constructed-save-fixture-current.md` targets unit index `0`
  at save type offset `0x00023EFC`, changing Light cavalry (`enabled=0`) to
  Dragon cavalry (`enabled=3`) under
  `C:\ClashTests\battle-enabled-fixture-20260520-210728`.
- Constructed runtime scan:
  hidden CDB run `captures\archive\cdb-surface-dump-20260520-210816` loaded the
  isolated slot `0`. `captures\current\battle-constructed-fixture-unit-scan-current.md`
  parses one naturally enabled unit, Dragon cavalry, with `availability=10`
  and `enabled=3`.
- Constructed command callback:
  hidden CDB run `captures\archive\cdb-surface-dump-20260520-220459` uses the same
  isolated fixture, the battlecenter inputprobe stage, and the non-type-forcing
  command callback probe. The attempt starts at displayed `(588,440)`, reaches
  pre-gate native `(508,380)`, then reaches `0042D4E0` with `unit_type=8`,
  `avail=10`, `enabled=3`, observes the click gate returning `eax=1`, records
  `branch=state1`, and has zero `BATTLE_COMMAND_FORCE_ENABLED_UNIT` or
  `BATTLE_COMMAND_CLICK_GATE_FORCE` rows. It no longer uses a pre-gate rearm,
  direct render-begin skip, or render-begin guard; the probe releases the
  synthetic click state before `Render_Begin`, then exits naturally on
  iteration `1` with `dd_is_flipping=0`, `dd_is_lost=0`, and `guard=0`.
- Matrix impact:
  the battle evidence matrix now includes `save_inventory: PASS`.
- Limitation:
  this is read-only state inventory, not input cadence proof. It says the local
  saves do not contain the enabled-command unit types needed to replace the
  current type-8 CDB override.

## 2026-05-22 Visible Input Readiness Bridge

- Visible harness:
  `scripts/cdb/run_cdb_battle_visible_input_probe.ps1`.
- Raw input helper:
  `tools\raw_sendinput_click.py`.
- Summary tool:
  `tools\battle_visible_input_summary.py`.
- Current summary:
  `captures\current\battle-visible-input-summary-current.md` and
  `captures\current\battle-visible-input-current.json`.
- Matrix integration:
  `tools\battle_ui_evidence_matrix.py` now includes a `visible_input` gate and
  a `completion_summary` block.
- Result:
  two visible runs reach `BATTLE_COMMAND_INPUT_WINDOW` with
  `coord_mode=visible-window`, expected displayed `(588,440)`, expected native
  `(508,380)`, and descriptor list `00514b78`.
- Limitation:
  no run proves real visible click consumption yet. The raw-send attempt is
  retained as negative evidence because it hit one post-`g` `80000003`
  break-instruction exception at `ntdll!NtReleaseMutant`, followed by 52 CDB
  breakpoint insert/remove failures before command readiness.
- Harness guard:
  `captures\current\battle-visible-harness-guard-current.md` now verifies
  `scripts/cdb/run_cdb_battle_visible_input_probe.ps1` will fail fast on those CDB failure
  signatures instead of waiting for a readiness marker after the debugger is
  already invalid.
- Completion summary:
  focused battle/right-bottom command lane is `99.91%`; full-game reverse
  engineering is not `100%`.

## Next Steps

1. Done: build the `battlecenter` candidate under `C:\ClashTests\battlecenter`.
2. Done: run `patch_stage_report.py` for the new stage.
3. Done: run the catalog probe through `scripts/cdb/run_cdb_surface_dump.ps1` on a hidden desktop.
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
12. Done under harness: prove actual command/grid centered-input wrapper
   mechanics against the centered battle frame.
13. Done under harness: sample post-ready battle redraw/copyback behavior after
   `BATTLE_READY`.
14. Done as CDB inventory: scan local save slots for natural enabled command
   units.
15. Done as read-only inventory: parse local save files for natural enabled
   command units.
16. Done: identify and write the minimal copied-save mutation for an isolated
   enabled-command fixture.
17. Done: run hidden CDB against that isolated fixture and prove it loads one
   naturally enabled Dragon cavalry unit.
18. Done under harness: prove command callback in the isolated fixture without
   a unit-type override.
19. Done under harness: remove the forced click gate; the constructed fixture
   naturally returns click gate `eax=1`.
20. Done under harness: replace the forced render-begin skip with a natural
   `Render_Begin` exit after synthetic click release.
21. Done under harness: remove the descriptor-local pre-gate click rearm.
22. Done under harness: move the constructed-fixture command click to the
   displayed inputprobe coordinate `(588,440)` and prove it reaches native
   `(508,380)`.
23. Done as visible readiness: prove visible-window command input readiness at
   descriptor list `00514b78` and displayed/native point `(588,440)->(508,380)`.
24. Next: replace the remaining synthetic hidden-CDB click/release with real
   visible OS click consumption that reaches the descriptor callback.
25. Next: capture natural/manual cadence in the constructed enabled-command
   fixture, or use an equivalent richer battle state that naturally exposes an
   enabled command.
