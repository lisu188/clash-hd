# Battle UI Probe Lane

Generated: 2026-05-15

Battle UI support remains probe-first. The current validation target is safe
complete mode: keep the native 640x480 battle UI intact, center it inside the
800x600 HD surface at `(80,60)`, and prove command, tactical-grid, and modal
input routes before adding any battle-specific patch group.

## Stage

`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`

This stage now selects `castlecenter-all` plus the
`battle-ui-center-present-wrapper` group. The battle group is intentionally
narrow: it wraps the initial battle `Render_Present` call at `0042F2F5` and
centers the native 640x480 frame after hidden CDB evidence proved the
`Unit_Attack -> 0042E9E0` route.

## Artifacts

- `probes/cdb/battle/clash95_battle_ui_catalog_extra.cdb`
- `probes/cdb/battle/clash95_battle_ui_present_extra.cdb`
- `probes/cdb/battle/clash95_battle_ui_input_extra.cdb`
- `probes/cdb/battle/clash95_battle_force_attack_entry_extra.cdb`
- `probes/cdb/battle/clash95_battle_force_command_hit_extra.cdb`
- `probes/cdb/battle/clash95_battle_force_command_callback_extra.cdb`
- `probes/cdb/battle/clash95_battle_force_command_enabled_callback_extra.cdb`
- `probes/cdb/battle/clash95_battle_force_grid_hit_extra.cdb`
- `probes/cdb/battle/clash95_battle_force_modal_classified_extra.cdb`
- `probes/cdb/battle/clash95_battle_post_ready_redraw_extra.cdb`
- `probes/cdb/battle/clash95_battle_unit_scan_extra.cdb`
- `tools/battle_ui_summary.py`
- `tools/battle_ui_evidence_matrix.py`
- `tools/battle_command_availability.py`
- `tools/battle_slot_scan_summary.py`
- `tools/battle_save_unit_inventory.py`
- `tools/battle_ui_gate.py`
- `tools/test_battle_ui_summary.py`
- `tools/test_battle_ui_evidence_matrix.py`
- `tools/test_battle_command_availability.py`
- `tools/test_battle_slot_scan_summary.py`
- `tools/test_battle_save_unit_inventory.py`
- `tools/test_battle_ui_gate.py`

## Required Evidence Before Patching

- Deterministic hidden/no-popup route into a battle screen.
- `BATTLE_READY` plus battle surface pointer and size.
- Centered-native visual proof or an explicit unclassified/native result.
- Battle draw/present/copyback rows with battle-scoped callsites.
- Command descriptor and command-hit rows.
- Command callback row plus callback result branch.
- Tactical-grid hit or coordinate-conversion rows.
- Modal hit or explicit modal-path classification.
- Zero AV rows.
- Patch-stage report for the battle stage with `original=0` and `unexpected=0`.
- Existing HD map smoke evidence still passing.

Additional stable `battle-ui-*` patch groups remain blocked until
natural/manual enabled-command cadence is proven in a richer battle state. The
centered input wrapper mechanics and longer post-ready redraw/copyback behavior
are validation-proven under CDB, but not yet natural/manual proof.

## 2026-05-20 Combined Evidence Matrix

- Added `tools/battle_ui_evidence_matrix.py`, a repo-only gate over the current
  focused battle summaries plus `captures\current\patch-stage-battlecenter-current.json`
  and `captures\current\hd-map-smoke-current.json`.
- Current matrix: `captures\current\battle-ui-evidence-current.md` and
  `captures\current\battle-ui-evidence-current.json`.
- Result: PASS with candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`, no
  failures, screenshot links, and `promotion_status=validation_stage_only`.
- The matrix now includes post-ready redraw/copyback, centered input wrapper,
  command availability, save-slot scan, and save-file inventory gates. The
  slot scan reports 6 save attempts, 3 routed slots, 3 pre-unit-scan timeouts,
  and 0 natural enabled command units. The read-only save inventory parses 63
  units across all six local `.dat` files and also finds 0 natural enabled
  command units. The decoded local-save unit types are Peasant, Light
  infantry, Light cavalry, Highlander, and Builder; the enabled command-table
  targets to hunt for next are Dragon cavalry, Archer, Crossbower, Musketeer,
  Catapult, Cannon, Forester, Cyklop, Wizard, Winger, and Dragon.
- Constructed-fixture planning/runtime scan is now represented by
  `captures\current\battle-constructed-save-fixture-current.md` and
  `captures\current\battle-constructed-fixture-unit-scan-current.md`. The helper wrote
  only a copied save under
  `C:\ClashTests\battle-enabled-fixture-20260520-210728`; hidden CDB loaded
  that isolated slot `0` and parsed one naturally enabled Dragon cavalry unit
  (`availability=10`, `enabled=3`).
- Constructed-fixture command callback is summarized by
  `captures\current\battle-constructed-fixture-command-callback-current.md`. It reaches
  `0042D4E0` with `unit_type=8`, `avail=10`, `enabled=3`, records
  `branch=state1`, observes the click gate returning `eax=1`, and has zero
  `BATTLE_COMMAND_FORCE_ENABLED_UNIT` or `BATTLE_COMMAND_CLICK_GATE_FORCE`
  rows.
- Important limitation: this is a combined evidence checkpoint, not stable
  promotion and not manual input proof.

## 2026-05-20 Modal/Input Classification Probe

- Added `probes/cdb/battle/clash95_battle_force_modal_classified_extra.cdb`, a harness-only
  extension of the force-entry route. It waits for `BATTLE_READY`, skips the
  turn banner, and records the battle loop input updater at `004605D0`.
- Hidden-desktop proof: `captures\archive\cdb-surface-dump-20260520-103714`.
- Current summary: `captures\current\battle-ui-modal-classified-current.md` records
  `battle_ready=True`, `visual_mode=centered-native-640x480`,
  `modal_classified=True`, and `av_count=0`.
- Important limitation: this is an explicit no-hit classification for the
  current forced route: `BATTLE_MODAL_CLASSIFIED
  status=input_update_seen_no_modal`. It does not prove a separate modal dialog
  hit, and it does not prove natural/manual input cadence.

## 2026-05-20 Tactical-Grid Coordinate Probe

- Added `probes/cdb/battle/clash95_battle_force_grid_hit_extra.cdb`, a harness-only extension of
  the force-entry route. It skips the turn banner, probes displayed visual
  coordinate `(144,108)`, then probes native coordinate `(64,48)` through
  battle grid helper `0042CB50`.
- Hidden-desktop proof: `captures\archive\cdb-surface-dump-20260520-103155`.
- Current summary: `captures\current\battle-ui-grid-hit-current.md` records
  `battle_ready=True`, `visual_mode=centered-native-640x480`,
  `grid_hit_ok=True`, and `av_count=0`.
- Important limitation: this classifies the current coordinate mismatch. The
  displayed visual point lands in cell `(1,1)`, while the native point lands in
  cell `(0,0)`. It proves the hit-test route and the need for a centered-input
  transform, not a complete battle action or natural/manual click cadence.

## 2026-05-20 Enabled Command Callback Probe

- Added `probes/cdb/battle/clash95_battle_force_command_enabled_callback_extra.cdb`, a
  harness-only extension of the command-callback probe. It temporarily changes
  the selected unit type from `5` to `8` inside the throwaway CDB process so the
  command availability table reports `avail=10`, `enabled=3`.
- Hidden-desktop proof: `captures\archive\cdb-surface-dump-20260520-101859`.
- Current summary: `captures\current\battle-ui-command-enabled-callback-current.md`
  records `battle_ready=True`, `visual_mode=centered-native-640x480`,
  `command_callback_ok=True`, `command_callback_result_ok=True`,
  `command_render_begin_skip_seen=True`, and `av_count=0`.
- Important limitation: this proves the enabled branch of callback `0042D4E0`
  under CDB-forced preconditions. The render-begin call is skipped as a harness
  gate, and this does not prove natural/manual click cadence or a legitimate
  selected-unit state.

## 2026-05-20 Command-Callback Probe

- Added `probes/cdb/battle/clash95_battle_force_command_callback_extra.cdb`, a harness-only
  extension of the force-entry route. It opens the `Unit_Attack` wait gate at
  `0041CE7A`, forces the command descriptor click gate for descriptor
  `00514b78`, and logs callback `0042D4E0`.
- Hidden-desktop proof: `captures\archive\cdb-surface-dump-20260520-100717`.
- Current summary: `captures\current\battle-ui-command-callback-current.md` records
  `battle_ready=True`, `visual_mode=centered-native-640x480`,
  `command_callback_ok=True`, `command_callback_result_ok=True`, and
  `av_count=0`.
- Important limitation: this proves descriptor-to-callback activation under
  CDB-forced gates, then records `branch=precondition-disabled` for
  `unit_index=0`, `unit_type=5`, `avail=8`, `enabled=0`. It does not yet prove
  an enabled command state transition or natural/manual input cadence.

## 2026-05-20 Command-Hit Probe

- Added `probes/cdb/battle/clash95_battle_force_command_hit_extra.cdb`, a harness-only extension
  of the force-entry route. It skips the turn banner/frame waits, probes the
  centered visual command coordinate `(588,440)`, then probes the native
  coordinate `(508,380)` against the same descriptor list.
- Hidden-desktop proof: `captures\archive\cdb-surface-dump-20260520-094032`.
- Current summary: `captures\current\battle-ui-command-hit-current.md` records
  `battle_ready=True`, `visual_mode=centered-native-640x480`,
  `command_hit_ok=True`, `command_native_hit_ok=True`, `grid_hit_ok=False`,
  and `av_count=0`.
- Important limitation: this proves the descriptor hit-test can see the
  command button under controlled CDB mouse state. It does not itself prove a
  natural/manual click cadence, callback activation, modal routing, or later
  redraw behavior.

## 2026-05-18 Force-Entry And Initial Centering

- Added `probes/cdb/battle/clash95_battle_force_attack_entry_extra.cdb`, a harness-only route
  probe that scans live unit records, picks a current-player attacker and an
  enemy defender, makes them adjacent in the throwaway process, sets the combat
  animation gate, and forces one `Unit_Attack` call.
- Baseline forced battle-entry run:
  `captures\archive\cdb-surface-dump-20260518-214535`. It reaches
  `BATTLE_OWNER_ENTRY source=BattleRunner eip=0042e9e0`, dumps an 800x600
  battle surface, and shows the uncentered HD-native battle composition.
- Added patch group `battle-ui-center-present-wrapper`: `0042F2F5` now calls
  DGROUP cave `0051BA00`, which copies the native 640x480 battle frame to
  scratch, clears the 800x600 target, copybacks at `(80,60)`, then calls stock
  `Render_Present`.
- Exact CDB `.writemem` proof:
  `captures\archive\cdb-surface-dump-20260518-221018`. The run is hidden-desktop,
  `cdb-writemem`, no AV rows, candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`, and
  `battle-ui-force-entry-current.md` classifies
  `visual_mode=centered-native-640x480`, `centered_offset=[80,60]`,
  `centered_wrapper_seen=True`.
- Remaining blockers: natural/manual enabled-command cadence, actual centered
  input-transform proof, and longer-loop redraw/input proof.

## 2026-05-15 Catalog Smoke

- Fixed the initial catalog/present/input probe templates to avoid invalid CDB
  pseudo-register `@$t20`; battle probes now use valid `@$t19`.
- Added `tools/test_battle_ui_probes.py` so invalid battle probe registers,
  standalone `g` commands, and semicolons in `.echo` lines are caught
  repo-only.
- Refined the route inventory: `0042E9E0` (`sub_42E9E0`) is now treated as
  the likely live battle runner/owner, while `0042E5A0`
  (`HandleBattleResults`) is treated as a post-battle result marker.
- Built battlecenter candidate:
  `C:\ClashTests\battlecenter\clash95_hd_battlecenter_20260515_01.exe`.
- Patch-stage manifest:
  `reports\battlecenter_patch_stage_20260515_01.json`.
- Catalog smoke run:
  `captures\archive\cdb-surface-dump-20260515-114101`.
- Runtime candidate:
  `C:\ClashTests\battlecenter-catalog\clash95_hd_battlecenter_catalog_20260515_02.exe`.
- Result:
  hidden/no-popup CDB and the DirectDraw proxy passed, the surface dump was
  800x600 with no AV, and the battle gate failed closed because battle mode was
  not reached.

Next target: replace the enabled-command CDB precondition with natural/manual
input evidence in a richer battle state. The current local save-slot scan does
not expose naturally enabled command units, and direct save-file inventory
confirms the same result across all six local `.dat` files. The search moves to
a different save, a constructed battle fixture, or manual cadence capture in a
state that naturally exposes one of the decoded enabled command-table targets.
The immediate constructed-fixture route is now less-intrusive command cadence
in that isolated work directory. The current hidden CDB inputprobe pass
(`captures\archive\cdb-surface-dump-20260520-220459`) starts the command at displayed
`(588,440)`, reaches native `(508,380)`, and exits `Render_Begin` naturally;
the remaining step is replacing that synthetic hidden-CDB click/release with
natural/manual cadence evidence.
