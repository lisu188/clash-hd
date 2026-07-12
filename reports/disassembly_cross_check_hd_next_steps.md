# Disassembly Cross-Check: HD Mod Next Steps

Generated: 2026-06-30

## Purpose

The three remaining HD mod blockers — the right-bottom building action menu,
the in-battle unit command, and the castle overview centering — are all proven
under CDB/debugger harness but stay `validation-only` because no *natural*
(non-forced) route reaches them. This report cross-checks each route against the
recovered C decompilation in the companion `clash-disassembly` repository
(`clash95.c`) to (a) confirm the HD mod's address/coordinate assumptions are
correct and (b) determine, from ground-truth control flow, what each "natural"
route actually requires. All line numbers below cite `clash-disassembly/clash95.c`.

## Method

For each blocker route the HD patcher (`src/patcher/patch_clash95_hd.py`) hooks a
small set of VAs. We read the recovered function at each VA, traced the gating
conditions, and compared them to the runtime observations recorded in
`README.md`, `captures/current/right-bottom-blocker-triage-current.md`,
`reports/battle_ui_route_inventory.md`, and `reports/battle_ui_completion_plan.md`.

## Findings

### 1. Right-bottom building action menu — gate is a building-state bit, not a patch defect

HD observation (triage): the action descriptor for callback `004338E0` is parked
off-screen at `(1000,426)` with `owner_flag=0x00`, and `RBUI_PANEL_DRAW` /
`RBUI_ACTION_BOX` never appear on the natural route.

Disassembly confirms this exactly and explains why:

- The "owner_flag" is the byte at **`building_record + 416`** (`addon_flags`,
  clash95.c:37742).
- In `BuildingGarrisonDialog_*` action-widget setup, the production action
  descriptor is written at **`x = (addon_flags & 2) ? 155 : 1000`, `y = 426`**
  (clash95.c:37758–37759). `owner_flag=0x00` → bit `0x02` clear → parked at
  `x=1000`. This is the mod's observed `(1000,426)` precisely.
- More importantly, the *entire* production panel render block is gated:
  `BuildingGarrisonDialog_ShowProductionDialog` (`004338E0`) runs its draw calls
  — including `Castle_ShowUnitProductionPanel` (`00435BC0`) — only inside
  `if ( (*(_BYTE *)(g_BuildingGarrisonDialogActiveBuilding + 416) & 2) != 0 )`
  (clash95.c:49999). With bit `0x02` clear, the panel and action rows are skipped
  entirely. That is why `RBUI_PANEL_DRAW=0`/`RBUI_ACTION_BOX=0` on the natural route.
- `Castle_ShowUnitProductionPanel` draws to surface `dword_5202E0` with the
  action box at `Render_FillRect(dword_5202E0, 0, 425, 285, 0x1C2, 0x15E, 0x11D, 0x1A9)`
  (clash95.c:50769) — i.e. native `(285,425)`-anchored geometry, matching the
  HD mod's `right-bottom-action-descriptor-anchor` / native-center wrapper assumptions.

**Decisive point:** bit `0x02` is *written by the game*, not by the save loader
alone. `Building_New` (`0041D030`) clears `addon_flags` to `& 0xE0`
(clash95.c:34135) and sets bit `0x02` **only when called as `Building_New(1, …)`**
(clash95.c:34184–34186; callsites at clash95.c:20239 and 65907). Bits `0x08` and
`0x04` are set by separate upgrade paths (clash95.c:35254, 35289). So the natural
production/action menu is available only when the clicked building is of the
category created with `a1 == 1`. The local saves' clicked castle is not that
category, so `owner_flag` is legitimately `0x00`.

> Conclusion: the right-bottom blocker is a **building-state gate**, not a missing
> patch. The HD geometry/centering work is correct; the natural route cannot draw
> action rows until the player interacts with a building whose `addon_flags & 2`
> is set. This is directly analogous to the already-solved battle "constructed
> fixture" problem.

### 2. In-battle unit command — gate is unit-type capability tables

HD observation: clicking a command descriptor reaches callback `0042D4E0` with
`branch=precondition-disabled`, `unit_type=5, enabled=0`; forcing the unit type
to `8` gives `enabled=3` and reaches `state1`/`state2`.

Disassembly confirms the gate is metadata-table-driven:

- `UnitBattle_ToggleSelectedShootingMode` (`0042D4E0`, clash95.c:46188) and the
  button-state refresh `UnitBattle_RefreshSelectedActionButtons` (`0042D2C0`,
  clash95.c:46100) gate the command on two per-unit-type tables indexed by
  `88 * unit_type`:
  - `byte_51257E` = `g_UnitTypeBaseMeleeAttack` (clash95.c:258)
  - `byte_512582` = `g_UnitTypeMaxRange` (clash95.c:262)
- A command is enabled (`dword_53205C=1`, `dword_514B80=2`) only when the
  selected unit type has **both** melee (`byte_51257E[...]`) and range
  (`byte_512582[...]`) non-zero (clash95.c:46111–46130). If range is zero the
  command is hard-disabled (`dword_514B80=1`).

This matches the HD save inventory exactly: the local `.dat` saves contain only
Peasant / Light infantry / Light cavalry / Highlander / Builder — unit types with
a zero in one of those tables — hence `enabled=0`. Dragon cavalry (the constructed
fixture's type 8) has both, hence enabled.

> Conclusion: the battle command blocker is a **unit-roster gate**. The HD input
> wrappers are correct; a natural enabled command requires a battle state whose
> selected unit type has both melee and range > 0. The constructed enabled-command
> fixture already proves this; the gap is real visible-click consumption, not the patch.

### 3. Castle overview — HD wrappers are correct; hit-test is pixel-color based

- `Castle_RebuildSceneBuffers` (`00422020`, clash95.c:37601) renders to the global
  `dword_5202E0` (clash95.c:37613, 37620) and to `g_CastleScreenSurface`
  (clash95.c:37648); it takes no surface argument. The HD
  `castle-overview-center-present-wrapper` (native-render-then-center to
  `(80,60)`) is therefore the correct shape.
- `Castle_OpenManagementScreen` (`00422180`, clash95.c:38684) installs
  `00422020` as the render hook (clash95.c:38737) and creates the native
  **640×480** surface (clash95.c:38782).
- The overview hit-test (`~00422520` region, clash95.c:38812–38819) is **pixel
  color** based: it reads one pixel from `g_CastleScreenSurface` at
  `(dword_544CFC >> byte_54512C, dword_544D00 >> byte_54512C)` and switches on
  color values `248..255` to pick the callback. No command/callback interception
  is needed; offsetting the mouse globals before the read is sufficient and correct.

### Unifying insight: one mouse-coordinate model across all input routes

All three hit-test routes — castle overview (clash95.c:38818), battle tactical
grid (`0042CB50`, clash95.c:45827), and battle/world descriptor poll
(`00419DC0`, clash95.c:32033, via the per-widget compare pattern at
clash95.c:18694) — read the **same** raw mouse globals:

- `dword_544CFC` = `g_RenderState[9]` (X) (clash95.c:12983)
- `dword_544D00` = `g_RenderState[10]` (Y) (clash95.c:12984)
- shifted right by `byte_54512C` (zoom/scale shift) (clash95.c:12987)

Battle grid math is `cell = ((coord >> shift) - 32/16) >> 6` (cell size 64, sprite
origin 32/16) plus the viewport origin at `dword_532048 + 808/+812`
(clash95.c:45827–45836) — exactly the `cell_x=(x-32)>>6` already noted in
`reports/battle_ui_route_inventory.md`.

Every HD "centered-input" wrapper subtracts `(80<<shift, 60<<shift)` from
`dword_544CFC`/`dword_544D00` and restores them. Because all three routes consume
those same globals, this single transform is the correct and complete coordinate
model for centered 640×480-in-800×600 input. No per-route coordinate divergence
exists in the binary.

## Synthesis

Two of the three blockers (right-bottom action menu, battle command) are **game/
save-state gates in the original binary**, not deficiencies in the HD patch:

| Blocker | Gate (disassembly) | Natural requirement |
|---|---|---|
| Right-bottom action menu | `addon_flags & 0x02` at `building_record+416` (clash95.c:49999) | A building created with `Building_New(1,…)` (bit 0x02 set) |
| Battle command enabled | `g_UnitTypeBaseMeleeAttack` AND `g_UnitTypeMaxRange` non-zero (clash95.c:46111) | A battle roster with a melee+range unit type |
| Castle overview centering | none — wrappers correct | already proven; only manual input pending |

The HD geometry, surface-centering, and coordinate-offset patches are all
confirmed correct against ground truth. The remaining work is therefore about
**reaching the required game states naturally and proving real input**, not about
more binary patching.

## Next Steps

Ordered, with the cheapest disassembly-confirmable work first.

1. **Right-bottom: build an `addon_flags & 0x02` save fixture (isolated).**
   Mirror the existing battle constructed-fixture pattern: produce an isolated
   copied save under `C:\ClashTests\...` (never mutate `C:\Clash\save`) whose
   clicked building has `addon_flags` bit `0x02` set, or identify a stock save/
   building category created via `Building_New(1,…)`. Then rerun the natural
   right-bottom UI probe and confirm `RBUI_PANEL_DRAW`/`RBUI_ACTION_BOX` appear
   *without* debugger-forced clicks. This is the disassembly-grounded answer to
   `controlled_recovered_but_natural_route_nonpromoting`.
   > Update 2026-07-03: the repo-only constructor for this fixture now exists as
   > `tools/right_bottom_constructed_save_fixture.py` (dry-run by default,
   > tested by `tools/test_right_bottom_constructed_save_fixture.py`). The
   > remaining work for this step is Windows-host only: run it with
   > `--output-save` under `C:\ClashTests\...` and rerun the natural probe.

2. **Battle: drive the existing enabled-command fixture to a real click.**
   The constructed Dragon-cavalry fixture already satisfies the
   `g_UnitTypeMaxRange`/`g_UnitTypeBaseMeleeAttack` gate. Per
   `battle_ui_completion_plan.md` steps 24–25, the only remaining item is real
   visible OS click consumption reaching `0042D4E0` — replace the synthetic
   hidden-CDB click/release with a true DirectInput click on the centered
   descriptor at displayed `(588,440) → native (508,380)`.

3. **Prove the input-source path for the right-bottom descriptor.**
   The triage's open question is the `00519620/00519622 → 004612E0` input-source
   path that naturally supplies the action click. With the fixture from step 1
   providing a *drawable* menu, trace whether a real click flows through that
   source path to descriptor `0051519A`/callback `00435620` without injected
   native coordinates. This converts the v17b debugger-forced proof into a
   natural one.

4. **Collect the five manual DirectInput proofs (after explicit approval).**
   `stable_menu_load`, `stable_hd_map_input`, `right_bottom_validation_input`,
   `castle_barracks_centered_input`, `castle_overview_centered_input`. Steps 1–3
   make targets 3–5 reachable on a natural route; the unified coordinate model
   (above) means a single centered-input transform validates all the offset hit-tests.

5. **Run the promotion-decision tools against the manual proof manifest.**
   Only then promote `rightbottomcompose`/`castlecenter-all`/`battlecenter` out of
   validation-only, or create the `complete-hd` alias.

## What not to do (confirmed by disassembly)

- Do **not** add more patches to "force" the right-bottom action rows to draw:
  the render block is correctly gated by `addon_flags & 0x02`; forcing it would
  paint a panel for a building that has no production state. The fix is the save
  fixture, not a wider patch.
- Do **not** override the selected unit type to fake an enabled battle command in
  a shippable stage: enablement is a legitimate unit-capability gate. Use a real
  roster (the isolated fixture) instead.
- Keep the centered-input offset on `dword_544CFC`/`dword_544D00` only; do not
  introduce per-route coordinate fudges — the binary uses one shared model.
