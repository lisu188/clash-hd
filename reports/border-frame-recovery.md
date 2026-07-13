# Border Frame Recovery Investigation

Date: 2026-04-30

Scope: investigate how to recover the Clash95 gameplay border frame for the
current 800x600 HD map path. This report uses only local repo notes, scripts,
captures, CDB probe files, and local reverse-engineering exports. It does not
touch proprietary binaries or assets.

Current UI reference:

![current HD UI](../captures/map-minimapaction-minimapright-dynvswitch-v2-frame-20260424.png)

## Current Visual Problem

The best color UI capture currently shows:

- The original ornate top frame is still visible across most of the 800-wide
  view.
- The original ornate left frame is still visible only down to the old native
  bottom area.
- The HD map now fills the enlarged terrain area, but the lower/right frame
  and bottom tooltip/status band are not recovered. The lower-left frame strip
  drops into black below the old 480-high extent, and the lower-right UI area
  remains a large black block.
- The moved minimap is in the upper-right corner and no longer duplicates in
  the old position.

Relevant capture evidence:

- `captures/map-minimapaction-minimapright-dynvswitch-v2-frame-20260424.png`
  is the current color UI reference, target-owned at `1200x900`.
- `captures/map-minimapaction-minimapright-dynvswitch-v2-frame-20260424.png.json`
  reports the same image hash and `NonblackPercent=95.317`.
- `captures/archive/right-bottom-ui-bounds-baseline-20260429.json` measures the current
  black lower/right UI regions. In that baseline, `bottom_right_ui_corner`
  is only `10.704%` nonblack, and the bottom-right logical cells `r8c10` and
  `r8c11` are about `1%` nonblack.
- `captures/current/no-popup-map-evidence-current.md` proves the HD 12x9 map drawing
  path itself is valid under CDB-only no-popup evidence: normal dark cells are
  explained by visibility/fog, and a forced-visible CDB proof draws the same
  right/bottom map cells when visibility permits.

## Geometry Ground Truth

Native map geometry is visible in both notes and decompilation:

- Map cells are 64x64.
- Native map tile origin is logical `x=32`, `y=16`.
- Native visible tile region is effectively 9x7 with a special clipped bottom
  row.
- HD target is 12x9 at 800x600:
  - X cells: `32..799`
  - Y cells: `16..591`

The native UI frame therefore appears to reserve:

- top band: `y=0..15`
- left band: `x=0..31`
- old native lower edge near `y=464..479`
- old native right/UI edge near `x=608..639`

Inference: the current patch successfully expands the terrain coordinate view,
but it does not yet provide a new HD owner for the old frame/tooltip regions
that used to live at the native right and bottom edges.

## Patch State That Matters

Current recommended stage:

`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`

Important patch groups from `patch_clash95_hd.py`:

- `display`, `gameplay-surface`, and `map-surface-upgrade-scrollclamp` grow
  surfaces/window paths to 800x600.
- `main-loops`, `full-redraw-12x9`, and `helpers` grow gameplay map drawing and
  scroll helpers from native 9x7 toward 12x9.
- `full-redraw-present-bounds-800` changes native full-redraw present bounds:
  - `0x4188DD` right edge `607 -> 799`, file offset `0x017CDE`
  - `0x41896A` right compare `607 -> 799`, file offset `0x017D6C`
  - `0x418981` right strip edge `607 -> 799`, file offset `0x017D82`
  - `0x418997` bottom compare `463 -> 591`, file offset `0x017D99`
  - `0x418A5D` bottom strip edge `463 -> 591`, file offset `0x017E5E`
  - `0x418A67` bottom strip right edge `607 -> 799`, file offset `0x017E68`
- `minimap-hd-right-anchor` moves the minimap anchor from `608` to `800` at
  `0x40D390`, file offset `0x00C790`.
- There is no explicit border-frame or bottom-tooltip recovery patch yet.

This strongly suggests the present map patch deliberately made the terrain
occupy the HD area, while the decorative gameplay frame and bottom tooltip
still need their own explicit redraw/anchor strategy.

## Static Leads

File offsets below use the repo note formula for code in `AUTO`:
`file_offset = VA - 0x400C00`.

### `sub_418700` - full map redraw and native frame-adjacent bounds

- VA: `0x00418700`
- File offset: `0x017B00`
- Local evidence: `C:\Clash\clash95.c`, `patch_clash95_hd.py`,
  `docs/hd/CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md`

This is the highest-value border-frame lead. Decompilation shows it:

- sets `g_RenderDevice = dword_5202E0`;
- draws the map from logical `x=32`, `y=16`;
- originally loops full rows with `v2 < 6` and columns with `v3 < 9`;
- draws a special clipped bottom row when `!dword_526994`;
- calls optional `dword_526990()` after tile drawing;
- uses hard native dirty/present limits such as `607` and `463`.

Current patches already modify the tile and present limits in this function.
That means `sub_418700` is both the HD terrain proof point and the main place
where border/tooltip preservation can be accidentally bypassed.

Open question: what is `dword_526990` during normal gameplay? It is called
immediately after the tile draw and before cursor dirty-region handling. If it
is a UI overlay/frame callback, then the minimal patch might be to preserve or
extend that callback rather than adding a new drawing path.

### `sub_418A90`, `sub_418C00`, `sub_418CE0` - partial repaint and centering

- `sub_418A90` VA `0x00418A90`, file offset `0x017E90`
- `sub_418C00` VA `0x00418C00`, file offset `0x018000`
- `sub_418CE0` VA `0x00418CE0`, file offset `0x0180E0`

These helpers encode native 9x7 assumptions and are already partially covered
by the `helpers` group. They matter for frame recovery because a one-time frame
draw is not enough: partial repaints can later overwrite or fail to restore
the frame/tooltip edges.

### `sub_419D80` and `sub_419DC0` - descriptor draw/hit-test viewport switch

- `sub_419D80` VA `0x00419D80`, file offset `0x019180`
- `sub_419DC0` VA `0x00419DC0`, file offset `0x0191C0`

`sub_419D80` skips descriptor entries with `x >= 640`. `sub_419DC0` also
triggers `sub_460D80` viewport switching when descriptor flags request it.
These are already important for centered menus and UI hit-testing. For border
recovery, they are likely relevant if the bottom tooltip/status band is driven
by descriptor entries that were never made HD-aware.

### `sub_4347A0`, `sub_434E20`, `sub_435500`, `sub_435580`

- `sub_4347A0` VA `0x004347A0`, file offset `0x033BA0`
- `sub_434E20` VA `0x00434E20`, file offset `0x034220`
- `UI_DrawActionBox` VA `0x00435500`, file offset `0x034900`
- `UI_GetGridIndexFromMouse` VA `0x00435580`, file offset `0x034980`

These are right-bottom/action-panel leads already targeted by
`probes/cdb/ui/clash95_right_bottom_ui_probe.cdb` and `probes/cdb/ui/clash95_right_bottom_ui_extra.cdb`.
Known native coordinates:

- action icon grid draw base: `x=426`, `y=32`, step `48x82`, `4x3`
- action grid hit-test base: `x=426`, `y=32`, step `48x82`, `4x3`
- status text area: `x=401..593`, y around `297`, `317`, `337`
- action box fill/text: `Render_FillRect(... left=285, top=350, bottom=425,
  right=450 ...)`, text around `x=285..349`, `y=430`

These look more like gameplay command/status UI than the map's ornate outer
frame, but they probably share the same bottom/right visual recovery problem:
they still use native coordinates and old surface assumptions.

### `UI_DrawPanelWithSprite`, `UI_ShowInfoWindow`, `UI_NotifyText`

From local Ghidra exports:

- `UI_DrawPanelWithSprite` VA `0x004438A0`, file offset `0x042CA0`
- `UI_ShowInfoWindow` VA `0x00445360`, file offset `0x044760`
- `UI_NotifyText` VA `0x00447330`, file offset `0x046730`
- `UI_ShowMissionStatusPanel` VA `0x00447610`, file offset `0x046A10`

`UI_DrawPanelWithSprite` creates a temporary sprite-backed surface and uses
fixed local origin values `v22=100`, `v23=100`. It is probably not the map
border itself, but it is a strong candidate for modal/info/tooltip-style
framed panels. CDB should prove whether these run during normal map hover or
bottom tooltip updates before any patch is made.

## Working Hypotheses

1. The ornate top/left frame persists because those bands are outside the map
   tile origin and not overwritten by expanded tile draws.
2. The bottom/right frame disappeared because the HD map expansion moved the
   terrain/present bounds into regions that were previously reserved for native
   UI frame/tooltip work.
3. The right/bottom black blocks are not a current 12x9 map rendering failure.
   The no-popup evidence matrix already proves the map can draw those cells
   when visibility permits. This is a UI composition/recovery problem.
4. The minimal patch is unlikely to be another global `640/480` replacement.
   It should either:
   - recover an existing frame/tooltip draw path and make only its anchors or
     bounds HD-aware; or
   - add a tiny post-map overlay helper after `sub_418700` that restores the
     frame/tooltip regions without disturbing tile loops or visibility.
5. The bottom tooltip should be investigated as a sibling target, not silently
   folded into map drawing. It likely has distinct text/panel call sites under
   `UI_ShowInfoWindow`, `UI_NotifyText`, action-panel code, or descriptor-driven
   UI.

## Minimal Patch Shapes To Consider

### Option A: find and extend the original frame draw owner

Best case: there is an existing function that draws the gameplay border frame
using sprite pieces or a UI descriptor. Patch only its constants/anchors:

- right edge from native `607/639` to `799`
- bottom edge from native `463/479` to `591/599`
- minimap-aware top-right exclusion stays at `586..799`, `16..229`

This is the cleanest path because it preserves authentic art and ordering.
CDB must first identify the function and prove it runs after terrain redraw.

### Option B: late post-map frame restore helper

Hook a code cave from `sub_418700` after the HD tile redraw and before final
present. The helper would redraw only non-map UI bands:

- top frame `y=0..15`
- left frame `x=0..31`
- bottom tooltip/frame band, likely at or below `y=592`
- right/bottom corner and any reserved action panel regions

Risk: drawing authentic ornate frame pieces probably needs sprite calls or a
copy from known native frame pixels, not a plain fill. A plain `Render_FillRect`
would be useful only as a diagnostic mask, not a shippable HD frame.

### Option C: reserve less terrain for UI

Reduce HD terrain coverage to leave room for the original bottom tooltip/frame
at native-like coordinates. This is small but probably undesirable because it
gives up the current 12x9 design and conflicts with the proven map path.

### Option D: wrapper/post-process composition

A DirectDraw wrapper could scale/preserve the native frame and compose HD map
content around it. This is not the current binary-minimal path, and it risks
becoming a parallel renderer. Keep it as a fallback, not the next patch.

## CDB-Only Validation Ideas

1. Add a CDB-only frame probe through `scripts\cdb\run_cdb_surface_dump.ps1` with
   `-ExtraProbeTemplate` that late-arms after `SURFDUMP_PLAYGAME`.
2. Break/log `sub_418700` at:
   - entry `00418700`
   - just before/after `dword_526990` at the `004187A0` area
   - present/fill branches around the already patched right/bottom constants
3. Log whether `dword_526990` is null, and if non-null, print its target:
   `poi(00526990)`.
4. Break/log UI frame candidates:
   - `004438A0` `UI_DrawPanelWithSprite`
   - `00445360` `UI_ShowInfoWindow`
   - `00447330` `UI_NotifyText`
   - `00447610` `UI_ShowMissionStatusPanel`
   - `004347A0`, `00434E20`, `00435280`, `00435500`
5. Add `004024E0` blit/present logging only after gameplay is reached. Filter
   callers to the ranges above and print source/destination rectangles that
   intersect:
   - `x < 32`
   - `y < 16`
   - `x >= 586`
   - `y >= 528`
6. Sample `dword_5202E0` pixels in the frame/tooltip bands at several phases:
   - before `sub_418700`
   - after tile loops
   - after `dword_526990`
   - after right-bottom UI candidates
   - at `SURFDUMP_READY`
7. Use existing screenshot-side helpers as validation:
   - `tools/map_tile_coverage.py` for gameplay sanity
   - `tools/right_bottom_ui_bounds.py` with custom regions for bottom strip,
     left-frame extension, and tooltip band
   - a future dedicated `border_frame_bounds.py` only if the custom-region path
     becomes too clumsy

Expected CDB proof shape:

- `SURFDUMP_PLAYGAME` and `SURFDUMP_READY` appear.
- The surface remains `800x600`.
- No AV rows.
- Frame/UI candidate rows show which function actually writes the bottom/right
  bands.
- Pixel samples prove whether black is present before terrain draw, introduced
  by terrain draw, or simply never repainted by UI.

## Evidence Still Missing

- Exact owner of the ornate gameplay border draw.
- Runtime value and call target of `dword_526990` during the HD map route.
- Whether bottom tooltip/status text is descriptor-driven, action-panel-driven,
  or a separate notification/info-window path.
- Palette/authentic-color evidence from the hidden CDB surface route. Current
  no-popup `surface.png` files are grayscale index visualizations, useful for
  geometry but not final art/color inspection.
- A CDB-only run of `probes/cdb/ui/clash95_right_bottom_ui_probe.cdb` or equivalent extra
  probe that reaches gameplay and records right-bottom UI/frame markers.

## Recommended Next Experiments

1. Write `clash95_border_frame_probe.cdb` as a CDB-only extra probe for
   `scripts\cdb\run_cdb_surface_dump.ps1`, focused on `sub_418700`, `dword_526990`, and the
   UI candidates listed above.
2. Run it with the current stage via hidden-desktop CDB and DirectDraw proxy,
   then attach the resulting `surface.png` as the required screenshot artifact.
3. Add custom-region analysis for:
   - `top_frame`: `0,0,799,15`
   - `left_frame_native`: `0,16,31,479`
   - `left_frame_hd_extension`: `0,480,31,599`
   - `bottom_tooltip_band`: `32,592,799,599`
   - `right_ui_band`: `586,230,799,599`
4. If `dword_526990` is non-null, disassemble and name its target before
   patching. If it is null, focus on post-map UI candidates and descriptor
   paths.
5. Prototype only diagnostic fills first, then replace them with authentic
   frame/sprite redraw once the correct owner and draw order are proven.

## Resolution (2026-07-13): `frame-restore-bands` post-map cave

Implemented as **Option B** with authentic on-surface art (no owner needed).

Root cause confirmed against the surfdump: the native 640x480 chrome (drawn once
at gameplay entry via `Render_DrawSprite` in `PlayGame`, not `sub_418700`; the
`dword_526990` post-tile callback is null in the HD route) leaves two genuine
black bands after the HD expansion, measured on
`captures/archive/cdb-surface-dump-20260713-072428/surface.png`:

- left gutter `left_frame_hd_extension (0,480,31,599)` = 100% black
- top-right strip `top_right_extension (640,0,799,15)` = 100% black

Fix: new patch group **`frame-restore-bands`** (validation-only stage
`...-minimapright-dynvswitch-framerestore`, kept out of `DEFAULT_STAGE`) that
hooks `sub_418700` at the single post-tile convergence point (`0x004187AF`,
displaced `test ebp,ebp; jz loc_4189A3`, inside the `if (a1)` present gate) and
jumps to a DGROUP cave at `0x0051BE00` (file `0x11A000`, 197 bytes in a verified
all-zero 256-byte region). The cave copies authentic already-drawn frame pixels
via the engine blit `0x4024E0` (`Render_FillRect`: `eax`=src surface, `edx`=dst
surface, `ebx`/`ecx`=src left/top, pushed dstTop/dstLeft/srcBottom/srcRight,
inclusive coords, callee-cleaned):

- native left frame `(0,360)-(31,479)` -> gutter `(0,480)` (continues the
  vertical ornament downward, seamless at y=479/480);
- native top frame `(480,0)-(639,15)` -> strip `(640,0)` (continues the top
  ornament rightward).

**Present-path lesson (why each band is painted twice).** The engine draws to
the offscreen back buffer `dword_5202E0` but presents only the map rectangle
(`x=32..799, y=16..591`) to the screen each frame via
`Render_FillRect(src, dst=0, ...)` — dst `0` is the managed DD-safe screen
target. So a back-buffer-only fill passes the surfdump proxy while remaining
invisible on the real screen (confirmed by visual-smoke `20260713-144505`).
Writing the raw DD primary object `0x51D4C0` instead crashes with
`DDERR_SURFACELOST` when the surface is lost mid-transition (confirmed by
visual-smoke `20260713-145714`). The working cave therefore paints each band on
the back buffer (keeps full re-presents and the proxy correct) and then, gated
on the saved `a1` present flag (`[esp+8]` after `pushad`), presents the same
source rect to the screen with dst=0, exactly like the engine's own map present.

The two destination bands are geometrically disjoint from the 12x9 terrain
(`x>=32, y=16..591`) and the moved minimap (`586..799,16..229`), so no runtime
exclusion is needed and nothing tears. The `x>=32` bottom strip (`y=592..599`)
is left as the intended ~8px letterbox.

Validation, hidden CDB surfdump (`captures/archive/cdb-surface-dump-20260713-143450`,
back-buffer half; re-run for the final gated cave, SHA
`FE9CBE3C67A16945371326CA4C7A668B70286A9D3C80AA6795B2C33B13F74C5E`):

- reached `SURFDUMP_READY` with **no access violation**;
- both bands flip to **100% non-black** with authentic-art histogram similarity
  `~0.68` (left) and `~0.79` (top-right) vs their native source bands
  (`tools/border_frame_bounds.py`; recorded in
  `captures/current/border-frame-restore-current.json`);
- `map_tile_coverage.py` edge coverage rose top `80%->100%`, left `80%->100%`
  with the terrain blank-cell (fog/visibility) pattern unchanged;
- `patch_stage_report.py` shows `frame-restore-bands 2/2` and the stable HD-map
  gate still `PASS`; `stable_stage_guard.py` stays `PASS`.

Validation, **real visible runtime** (user-approved, visual-smoke
`captures/archive/visual-smoke-20260713-150843/after-map-path.png`):

- `left_frame_hd_extension` and `top_right_extension` both **100% non-black on
  the actual screen** with authenticity `0.68`/`0.80`
  (`captures/current/border-frame-restore-realruntime-current.json`);
- minimap, terrain, and bottom tooltip (`Plain - 4ap`) unregressed;
- `capture_tear_check.py` clean (`tear_suspected=False`).
