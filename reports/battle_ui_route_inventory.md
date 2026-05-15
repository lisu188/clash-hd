# Battle UI Route Inventory

Generated: 2026-05-15

Sources inspected:

- `C:\Clash\reverse\ghidra-out\functions.csv`
- `C:\Clash\reverse\ghidra-out\selected_decompilation.c`
- `C:\Clash\clash95.c`
- `C:\Clash\clash95.map`
- existing repo CDB probes and summary tools

No route below is patch-safe yet. These are probe candidates only.

## Candidate Routes

Route:
  name: Unit attack entry
  suspected VA: `0041AD20`
  file offset: unknown in this report
  old bytes/context: `Unit_Attack` in `functions.csv`; called from map action paths in `C:\Clash\clash95.c`
  caller: adventure-map unit action routes
  callee: `CalculateBattleResult` and battle/result helpers in some paths
  runtime evidence: none in current repo evidence
  confidence: medium for battle logic, low for battle UI screen ownership
  safe to patch: no
  reason: logic entry only; does not prove draw target, UI panel, descriptor, or grid route

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
  caller: battle result flow after battle map/resource setup
  callee: battle map/resource, result presentation, and follow-up map update paths
  runtime evidence: none in current repo evidence
  confidence: high as a battle route candidate
  safe to patch: no
  reason: must first prove surface size, present/copyback path, descriptor list, and input handling at runtime

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
  runtime evidence: proven in other modes, not battle
  confidence: medium for battle descriptors if battle uses stock descriptor lists
  safe to patch: no
  reason: shared descriptor function, needs battle-specific caller/context before wrapping

Route:
  name: Descriptor input scan
  suspected VA: `00419DC0`
  file offset: unknown in this report
  old bytes/context: existing descriptor tracing uses this function for hit testing
  caller: many UI modes including map/castle
  callee: descriptor hit callbacks
  runtime evidence: proven in other modes, not battle
  confidence: medium for battle command/modal input if battle uses stock descriptors
  safe to patch: no
  reason: shared hit-test function, needs battle-specific callsite proof before any coordinate wrapper

Route:
  name: Present path
  suspected VA: `00460EA0`
  file offset: unknown in this report
  old bytes/context: `Render_Present`
  caller: many UI modes
  callee: DirectDraw present/flip path
  runtime evidence: proven broadly, not battle-specific
  confidence: high as shared present helper, low as patch site
  safe to patch: no
  reason: shared helper cannot be patched globally for battle without a proven battle-only callsite

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

## Missing Evidence

- No hidden/no-popup capture currently reaches battle mode.
- No battle `BATTLE_READY` row exists yet.
- No battle surface pointer/size is proven.
- No battle draw/present/copyback caller is battle-scoped.
- No battle command descriptor/callback is cataloged.
- No battle tactical-grid hit or coordinate converter is proven.
- No battle modal/dialog route is classified.
- No battle patch group should be added yet.
