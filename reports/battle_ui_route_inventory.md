# Battle UI Route Inventory

Generated: 2026-05-15
Updated: 2026-05-20

Sources inspected:

- `C:\Clash\reverse\ghidra-out\functions.csv`
- `C:\Clash\reverse\ghidra-out\selected_decompilation.c`
- `C:\Clash\clash95.c`
- `C:\Clash\clash95.map`
- existing repo CDB probes and summary tools

Only the initial battle-present centering route is patch-backed. Battle command
descriptor hits, descriptor-to-callback activation, and a harness-forced
enabled-command callback result are now proven on the centered frame.
Tactical-grid hit-test entry is classified through `0042CB50`: displayed
`(144,108)` reaches cell `(1,1)`, while native `(64,48)` reaches cell `(0,0)`.
Modal/input routing is classified as `input_update_seen_no_modal` at
`004605D0` for the current forced route. The natural save-state callback result
is disabled by command availability (`unit_type=5`, `avail=8`, `enabled=0`),
so actual centered input transforms, natural/manual enabled-command cadence,
and later battle-loop redraws are still probe candidates.

## Candidate Routes

Route:
  name: Unit attack entry
  suspected VA: `0041AD20`
  file offset: unknown in this report
  old bytes/context: `Unit_Attack` in `functions.csv`; called from map action paths in `C:\Clash\clash95.c`
  caller: adventure-map unit action routes
  callee: `CalculateBattleResult` and battle/result helpers in some paths
  runtime evidence: `captures\cdb-surface-dump-20260518-214535` and
  `captures\cdb-surface-dump-20260518-221018` force-entry rows call
  `Unit_Attack` with live attacker/defender unit records and log
  `BATTLE_ROUTE_CANDIDATE name=Unit_Attack_calls_BattleRunner eip=0041b145`
  confidence: high for the battle-entry route, low as a patch site
  safe to patch: no
  reason: harness-only entry route; not a visual/input centering callsite

Route:
  name: Unit attack building entry
  suspected VA: `0041B7D0`
  file offset: unknown in this report
  old bytes/context: `Unit_AttackBuilding` in `functions.csv`
  caller: adventure-map building attack routes
  callee: battle/result helpers in some paths
  runtime evidence: none in current repo evidence
  confidence: medium for battle logic, low for battle UI screen ownership
  safe to patch: no
  reason: logic entry only; separate from UI draw/input proof

Route:
  name: Battle result calculator
  suspected VA: `0041C4A0`
  file offset: unknown in this report
  old bytes/context: `CalculateBattleResult` in `functions.csv` and `C:\Clash\clash95.c`
  caller: `Unit_Attack`, `Unit_AttackBuilding`
  callee: battle result internals
  runtime evidence: none in current repo evidence
  confidence: high for battle logic, low for UI
  safe to patch: no
  reason: result computation is not a visual/input centering callsite

Route:
  name: Battle results handler and likely battle UI owner
  suspected VA: `0042E5A0`
  file offset: unknown in this report
  old bytes/context: `HandleBattleResults`; nearby strings include `BATTLE!!!`, `!!!!NEW BATTLE!!!!`, `battle`, `battle_bat_bkg*`, `battle_buttons_*`, and `battle_frame_*`
  caller: `sub_42E9E0` after the battle loop logs `END OF BATTLE`
  callee: battle result formation cleanup and follow-up map update paths
  runtime evidence: none in current repo evidence
  confidence: high as a post-battle result route candidate, lower as live battle UI owner
  safe to patch: no
  reason: decompilation shows this is reached after the battle runner, so it is
  useful as a completion marker but probably too late for live battle UI draw/input ownership

Route:
  name: Battle runner and likely live battle UI owner
  suspected VA: `0042E9E0`
  file offset: unknown in this report
  old bytes/context: `sub_42E9E0`; decompilation logs `END OF BATTLE`, calls
  `HandleBattleResults`, then tears down render hooks/resources
  caller: `Unit_Attack` and `Unit_AttackBuilding` flows after battle result setup
  callee: battle resource setup, live battle loop/draw paths, `HandleBattleResults`
  runtime evidence: `BATTLE_OWNER_ENTRY source=BattleRunner eip=0042e9e0`
  appears in `captures\cdb-surface-dump-20260518-214535` and
  `captures\cdb-surface-dump-20260518-221018`, with the same attacker/defender
  pointers from the forced `Unit_Attack` call
  confidence: high as the live battle owner route
  safe to patch: no
  reason: route owner only; individual draw/input callsites still need
  battle-scoped proof before patching

Route:
  name: Battle map resource filename
  suspected VA: `00441350`
  file offset: unknown in this report
  old bytes/context: `BattleMapFileName`; strings include `maps\` and `.mab`
  caller: battle result/setup flow
  callee: filename/string helpers
  runtime evidence: none in current repo evidence
  confidence: high for battle resource setup, low for UI draw/input
  safe to patch: no
  reason: useful route marker only

Route:
  name: Descriptor draw list
  suspected VA: `00419D80`
  file offset: unknown in this report
  old bytes/context: existing descriptor tracing uses this function for UI list draw
  caller: many UI modes including map/castle
  callee: descriptor draw callback path
  runtime evidence: `captures\cdb-surface-dump-20260518-221018` logs
  `BATTLE_DESCRIPTOR desc=00514b78 x=498 y=370 w=0 h=0 callback=0042d4e0`
  during the centered battle run; `captures\cdb-surface-dump-20260520-094032`
  repeats that descriptor before command-hit probing; and
  `captures\cdb-surface-dump-20260520-100717` reaches its click callback
  `0042d4e0`; `captures\cdb-surface-dump-20260520-101859` forces an enabled
  unit type and reaches the callback result branch
  confidence: medium for command-button cataloging and harnessed callback paths
  safe to patch: no
  reason: battle descriptor row is cataloged and callback behavior is
  harnessed, but natural/manual cadence is not proven yet

Route:
  name: Descriptor input scan
  suspected VA: `00419DC0`
  file offset: unknown in this report
  old bytes/context: existing descriptor tracing uses this function for hit testing
  caller: many UI modes including map/castle
  callee: descriptor hit callbacks
  runtime evidence: `captures\cdb-surface-dump-20260520-094032` uses the
  centered battle frame and logs `BATTLE_COMMAND_HIT coord_mode=visual result=2`
  plus `BATTLE_COMMAND_NATIVE_HIT coord_mode=native result=2`; summary
  `captures\battle-ui-command-hit-current.md` records
  `command_hit_ok=True`, `command_native_hit_ok=True`, and `av_count=0`;
  `captures\cdb-surface-dump-20260520-100717` then forces the command click
  gate, reaches callback `0042d4e0`, and records
  `BATTLE_COMMAND_CALLBACK_RESULT branch=precondition-disabled`;
  `captures\cdb-surface-dump-20260520-101859` temporarily changes selected
  unit type `5` to `8` and reaches
  `BATTLE_COMMAND_CALLBACK_RESULT branch=state2`
  confidence: medium for battle command/modal input if battle uses stock descriptors
  safe to patch: no
  reason: command descriptor hits are proven only under CDB-forced mouse state
  and turn-banner/frame skips; callback result paths are also harnessed;
  actual centered input transforms still need separate rows before wrapping input

Route:
  name: Present path
  suspected VA: `00460EA0`
  file offset: unknown in this report
  old bytes/context: `Render_Present`
  caller: many UI modes
  callee: DirectDraw present/flip path
  runtime evidence: proven broadly; battle rows in
  `captures\cdb-surface-dump-20260518-221018` include shared present returns
  from map/UI redraw callers plus wrapper return `ret=0051ba63`
  confidence: high as shared present helper, low as a global patch site
  safe to patch: no
  reason: shared helper cannot be patched globally for battle without a proven battle-only callsite

Route:
  name: Initial battle present callsite
  suspected VA: `0042F2F5`
  file offset: `0x02E6F5`
  old bytes/context: `e8 a6 1b 03 00` call to `Render_Present`
  caller: `BattleRunner` initial battle present path
  callee: cave `0051BA00`, then stock `Render_Present`
  runtime evidence: `captures\cdb-surface-dump-20260518-214535` reproduces the
  uncentered/stripey 800x600 battle frame; `captures\cdb-surface-dump-20260518-221018`
  logs `BATTLE_PRESENT_CALL ... ret=0051ba63`, `BATTLE_READY
  source=BattleInitialPresent`, and classifies `centered-native-640x480`
  at offset `[80, 60]`
  confidence: high for initial battle-present centering
  safe to patch: yes, validation-lane only
  reason: narrow callsite wrapper copies the native 640x480 battle frame to a
  scratch area, clears the 800x600 render target, copies back at `(80,60)`,
  and calls the stock present helper; it does not solve later redraw/input paths

Route:
  name: Copyback/dirty rectangle helpers
  suspected VA: `00460B20` / `00460BB0`
  file offset: unknown in this report
  old bytes/context: known render/copy helpers from existing map/castle probes
  caller: many UI modes
  callee: render copy/rect helpers
  runtime evidence: proven broadly, not battle-specific
  confidence: medium for present/copyback observation
  safe to patch: no
  reason: shared helper, only useful as a logged callsite until battle caller is known

Route:
  name: Tactical-grid or tile candidate
  suspected VA: `00416850`
  file offset: unknown in this report
  old bytes/context: `sub_416850` draws map/tile-like cells and is called by map redraw loops
  caller: map redraw paths in current decompilation
  callee: tile/sprite rendering
  runtime evidence: map evidence only, not battle
  confidence: low for battle tactical-grid input
  safe to patch: no
  reason: appears to be adventure-map tile draw, included only as a negative/control candidate

Route:
  name: Battle tactical-grid hit-test
  suspected VA: `0042CB50`
  file offset: unknown in this report
  old bytes/context: called from `0042E4ED` inside the live battle loop; static
  disassembly shows `cell_x=(x-32)>>6`, `cell_y=(y-16)>>6`
  caller: battle command/tactical input loop after the turn-banner gate
  callee: grid cell lookup and selection/action state handling
  runtime evidence: `captures\cdb-surface-dump-20260520-103155` logs
  `BATTLE_GRID_RESULT coord_mode=visual ... cell=(1,1)` for displayed
  `(144,108)`, then logs `BATTLE_GRID_HIT coord_mode=1 ... cell=(0,0)` for
  native `(64,48)`; summary `captures\battle-ui-grid-hit-current.md` records
  `grid_hit_ok=True`, centered-native visual mode, and `av_count=0`
  confidence: medium for the live battle grid hit-test route
  safe to patch: no
  reason: route and coordinate mismatch are classified under CDB-forced mouse
  state, but the actual centered-input transform and natural/manual cadence are
  not proven yet

Route:
  name: Battle loop input updater and modal no-hit classification
  suspected VA: `004605D0`
  file offset: unknown in this report
  old bytes/context: shared input/surface update helper called from battle loop
  at `0042E4E8`; neighboring helper `00460950` is a motion/button threshold
  classifier from the same input cluster
  caller: battle command/tactical input loop after the turn-banner gate
  callee: input state update, dirty rectangle redraw, and surface copy helpers
  runtime evidence: `captures\cdb-surface-dump-20260520-103714` logs
  `BATTLE_MODAL_CLASSIFIED status=input_update_seen_no_modal eip=004605d0`;
  summary `captures\battle-ui-modal-classified-current.md` records
  `modal_classified=True`, centered-native visual mode, and `av_count=0`
  confidence: medium for classifying that no modal dialog opened on the current
  forced battle route
  safe to patch: no
  reason: shared input/render updater and no-hit classifier only; useful as a
  route marker but not an input-transform patch site by itself

## Missing Evidence

- Hidden/no-popup force-entry now reaches battle mode, but the route is still a
  debugger harness path rather than natural gameplay proof.
- Initial `BATTLE_READY`, `BATTLE_OWNER_ENTRY`, and battle surface size are
  proven in `captures\cdb-surface-dump-20260518-221018`.
- Initial battle present centering is proven only at `0042F2F5` through cave
  `0051BA00`.
- Battle command descriptor hits are harness-proven in
  `captures\cdb-surface-dump-20260520-094032`; command callback entry is
  harness-proven in `captures\cdb-surface-dump-20260520-100717`; enabled
  callback result is harness-proven in
  `captures\cdb-surface-dump-20260520-101859`, but natural/manual input is not
  yet proven.
- Battle tactical-grid hit-test entry is harness-proven in
  `captures\cdb-surface-dump-20260520-103155`, but the actual centered-input
  transform is not patched or naturally/manual proven.
- Battle modal/input path is classified in
  `captures\cdb-surface-dump-20260520-103714` as
  `input_update_seen_no_modal`; no separate modal dialog hit is proven because
  the current forced route does not open one.
- No later battle-loop redraw centering patch is proven; previous broad present
  wrapping caused redraw artifacts and must not be restored without new proof.
