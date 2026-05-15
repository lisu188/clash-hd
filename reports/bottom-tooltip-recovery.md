# Clash95 HD Bottom Tooltip Recovery Report

Date: 2026-04-30

Scope: investigate the next HD-map target, especially the missing/recovered
bottom tooltip/status text and related lower UI layout. This report is
evidence-only. It does not modify raw sources, proprietary binaries, assets, or
patch code. All proposed runtime validation is CDB-only.

Current UI evidence:

![Current HD gameplay UI capture](../captures/map-minimapaction-minimapright-dynvswitch-v2-frame-20260424.png)

The current capture shows the widened 800x600 map body and the moved minimap,
but the lower-right/lower strip remains black or uncomposited. The top and left
map border frame are visible; the bottom/right frame and bottom status/tooltip
area are not recovered yet.

## Evidence Reviewed

- `AGENTS.md`: current workflow is CDB-only, with host and hidden-desktop CDB
  harnesses as the preferred validation path.
- `CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md`: current HD map stage has 800x600
  map surface, widened `sub_418700` present bounds, right-anchored minimap, and
  12x9 redraw helpers.
- `patch_clash95_hd.py`: current recommended stage is
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`.
- `captures/map-minimapaction-minimapright-dynvswitch-v2-frame-20260424.png`:
  visible baseline for lower UI defects.
- `probes/cdb/ui/clash95_right_bottom_ui_probe.cdb` and
  `probes/cdb/ui/clash95_right_bottom_ui_extra.cdb`: existing CDB-only probe material for
  right-bottom action/status UI.
- `C:\Clash\reverse\ghidra-out\functions.csv`: recovered function names and
  addresses.
- Static CDB disassembly of `C:\Clash\clash95.exe` for the functions below.

## High-Value Functions And Offsets

Assumption for code addresses in `.text`: file offset = `VA - 0x400C00`. This
matches known patch notes, for example `004347A0 -> 0x033BA0`.

| Area | VA | File offset | Evidence |
| --- | ---: | ---: | --- |
| Low-level blit/fill/present helper | `004024E0` | `0x0018E0` | Called by map redraw, panels, text boxes, and UI overlays. Current probes already log it as `RBUI_PRESENT`. |
| Text draw | `0040BE50` | `0x00B250` | Draws plain string glyphs. Args appear to be `x`, `y`, `string`. |
| Formatted text draw | `0040C150` | `0x00B550` | Formats to `00520520`, then enters the multiline/text renderer. Args are suitable for CDB logging as `x`, `y`, `right_or_width`, `style`, `fmt`, varargs. |
| Text layout / wrapped renderer | `0040BEE0` | `0x00B2E0` | Internal text renderer used by `0040C150`. |
| Unit info pane | `00419F70` | `0x019370` | Draws selected-unit details and multiple formatted text rows. Called from `Unit_Info` at `0041A7B2` / file offset `0x019BB2`. |
| UI state/action dispatcher helper | `00419ED0` | `0x0192D0` | Called by `00435620`; changes descriptor state and triggers UI redraw behavior. |
| Right action/status panel composite | `004347A0` | `0x033BA0` | Existing right-bottom probe names this `RBUI_PANEL_DRAW`. Calls text renderer and panel surface ops. |
| Action grid draw | `00434E20` | `0x034220` | Draws the 4x3 action grid. |
| Building/status text panel | `00435280` | `0x034680` | Draws a native right-side status text rectangle and several text rows. |
| Action box draw | `00435500` | `0x034900` | Draws the action box at native lower UI coordinates. |
| Action grid hit-test | `00435580` | `0x034980` | Native hitbox base `x=426`, `y=32`, step `48x82`, max `4x3`. |
| Action click dispatch | `00435620` | `0x034A20` | Calls `00419ED0` and writes selected action state. |
| Generic panel with sprite/text | `004438A0` | `0x042CA0` | Draws panel-like UI with text rows. Likely useful for border/status overlays but not confirmed as the bottom tooltip. |
| Notify text panel | `00447330` | `0x046730` | Centers a notification panel using native `640` (`0x280`) width math. Probably modal/notification, not the persistent bottom tooltip. |
| Mission status panel entry | `00447610` | `0x046A10` | Builds mission/status message data and calls another info-window path. |

## Static Findings

### Text Renderer

`UI_DrawText` at `0040BE50` formats/draws plain strings through the low-level
glyph path around `0040BC00`. `UI_DrawTextFmt` at `0040C150` writes a formatted
string into global buffer `00520520`, then calls the wrapped renderer at
`0040BEE0`.

Useful CDB argument probes:

```text
bp 0040BE50 ".printf \"TEXT ret=%p x=%d y=%d str=%ma\n\", poi(@esp), poi(@esp+4), poi(@esp+8), poi(@esp+0c); gc"
bp 0040C150 ".printf \"TEXTFMT ret=%p x=%d y=%d right=%d style=%d fmt=%ma\n\", poi(@esp), poi(@esp+4), poi(@esp+8), poi(@esp+0c), poi(@esp+10), poi(@esp+14); gc"
```

These should be filtered by return address ranges before use in a long run, or
they will be too noisy.

### Unit Info / Bottom Tooltip Candidate

`UI_DrawUnitInfoPane` at `00419F70` is a strong bottom-tooltip/status candidate.
It has:

- multiple calls to `UI_DrawTextFmt` at `0041A158`, `0041A1DC`, `0041A1FE`,
  `0041A22F`, `0041A2CC`, `0041A31B`, `0041A35C`, and `0041A642`;
- a present/fill call to `004024E0` at `0041A112`;
- caller `Unit_Info` at `0041A7B2`.

The disassembly shows coordinates are mostly relative to caller-provided pane
arguments, with repeated offsets such as `+0x40`, `+0x55`, `+0x69`, `+0x84`,
`+0x94`, `+0xA0`, `+0xBF`, and y-ish offsets such as `+0x05`, `+0x32`,
`+0x4A`, and `+0x5F`. This suggests a minimal patch probably belongs at the
pane anchor/caller, not inside every text call.

Open question: whether this function is the hover tooltip/status bar the user
means, or only selected-unit/building information. Runtime CDB rows are needed
before patching.

### Right/Lower Action Panel Candidate

The right-bottom UI probe already targets the important native panel cluster:

- `004347A0`: composite panel draw.
- `00434E20`: action grid draw.
- `00435280`: selected building/status text panel.
- `00435500`: action box draw.
- `00435580`: grid hit-test.
- `00435620`: click/action dispatch.

Static CDB disassembly confirms native lower/right constants:

- `00435280` starts with a fill/present call using constants around
  `x=401..593` and `y=288..357`, then text rows at roughly `y=297`, `317`,
  and `337`.
- `00435500` draws the action box using native constants around
  `x=285..450`, `y=350..425`, then writes formatted text.
- `00435580` tests action-grid mouse against native `base=(426,32)`,
  `step=(48,82)`, `max=(4,3)`.

If the action panel is moved visually, `00435580` must move with it. But for the
bottom tooltip/status recovery, first prove whether these routines still draw
after the HD map redraw and whether their presents reach `dword_5202E0`.

### Notify / Mission Status Panel

`UI_NotifyText` at `00447330` is probably not the persistent bottom tooltip. It
uses native `0x280` / 640-width centering math and builds a temporary panel via
`0051D4C0`, then draws text around a centered rectangle. It is still worth
logging because it proves how old UI panels handle surface/resource switching.

`UI_ShowMissionStatusPanel` at `00447610` builds mission-status data and calls a
separate info-window path. It may be game-start status UI, but static evidence
does not tie it to the missing lower tooltip in the current capture.

## Likely Failure Modes In The Current HD Patch

1. **Map redraw overwrites native lower UI.** The current stage intentionally
   widens full-redraw present bounds to the HD map area. Existing notes show
   `sub_418700` present rectangles widened from native bottom `463` to `591`.
   If bottom UI was drawn before this, the HD map redraw can repaint over it.

2. **Bottom/right UI draws to the wrong surface or resource handle.** Several UI
   functions temporarily change `00511230` / render resource state and use
   `dword_5202E0` or `0051D4C0`. The current patch swaps `dword_5202E0` to an
   800x600 map surface after menu dispatch. A native UI routine may still draw
   into a scratch/menu surface or present only a native subrect.

3. **Native panel coordinates are still 640x480-era.** The action/status panel
   routines use x/y constants built for the old side/bottom layout. They may be
   visually valid for old UI but no longer align with the 800x600 map surface
   and right-anchored minimap.

4. **Surface dumps may miss final UI composition.** `scripts\cdb\run_cdb_surface_dump.ps1`
   dumps `dword_5202E0`. If the missing tooltip/status is composited via another
   surface or final front-buffer operation, the raw map-surface PNG may not show
   it even if the user-facing frame would.

## Minimal CDB-Only Validation Plan

1. Create a narrow `clash95_bottom_tooltip_probe.cdb` or extend
   `probes/cdb/ui/clash95_right_bottom_ui_extra.cdb`.

2. Late-arm after gameplay, like the existing right-bottom probe. Do not arm hot
   text/present breakpoints from process start.

3. Log text calls only when `poi(@esp)` is in these caller ranges:

   - `00419F70..0041A690` for unit/bottom info pane.
   - `004347A0..00435680` for action/status panel.
   - `004438A0..00443B60` for generic panel-with-sprite text.
   - `00447330..00447610` for notify/mission status.

4. Log `004024E0` only for those same ranges. Include:

   - return address;
   - source surface pointer and size;
   - destination surface pointer/width;
   - source/destination rectangle args;
   - `dword_5202E0`;
   - current `00511230` resource/surface pointer;
   - current mouse logical x/y, because hover text may be conditional.

5. Run through a CDB-only harness, preferably hidden-desktop/no-popup:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_cdb_surface_dump.ps1 `
  -UseDdrawProxy `
  -NoSkipStartAnims `
  -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch `
  -CandidateDir C:\ClashTests\cdb-surface-dump `
  -RunSeconds 120
```

If the harness supports an extra probe include, add the bottom-tooltip probe
there. If not, the next engineering task should be adding an explicit
`-ExtraProbe` or `-Probe` include path to the CDB-only harness.

6. Validate with a current UI screenshot artifact. For no-popup runs, use the
reconstructed `surface.png`. For visible/manual confirmation later, use a
normal frame capture.

## Patch Direction After Proof

Do not globally replace lower UI constants. Candidate minimal patch directions,
in preferred order:

1. **Redraw ordering fix:** if CDB proves tooltip/status UI is drawn before
   `sub_418700` and then overwritten, patch the gameplay loop to redraw the
   specific bottom/status UI after the HD map redraw.

2. **Surface/present fix:** if CDB proves UI text draws to a scratch/menu
   surface and never reaches `dword_5202E0`, patch the small surface switch or
   present rectangle for that UI path only.

3. **Anchor relocation fix:** if CDB proves the correct text is drawn at native
   coordinates but simply hidden/misaligned, patch the pane anchor or caller,
   not every individual text call. `UI_DrawUnitInfoPane` looks anchor-relative,
   so the caller around `Unit_Info` / `0041A7B2` is the first place to inspect.

4. **Hitbox pairing:** if action-panel visuals move, pair the visual patch with
   the hit-test patch at `00435580`; otherwise clicks and hover text will drift.

## Open Questions

- Is the desired "bottom tooltip" the selected unit info pane
  (`00419F70`), the right/status action panel (`00435280` / `00435500`), or a
  hover-only text path elsewhere?
- Does the current surface dump represent final user-facing composition, or
  only the map surface before final overlays?
- In the current HD stage, are bottom/status UI routines called after gameplay
  route-injection, or are they skipped by state/mouse/selection conditions?
- Is the black lower-right area a missing UI panel, an intentional old UI
  reserved region, or an unpresented/cleared rectangle?
- Should the final HD design preserve a native-style bottom strip over the map,
  or allow the 12x9 map to occupy the whole 800x600 surface and place tooltip
  text as an overlay?

## Recommended Next Experiments

1. Add a CDB-only bottom-tooltip probe with filtered `TEXT`, `TEXTFMT`, and
   `RBUI_PRESENT` rows for the address ranges above.
2. Add `-ExtraProbe` support to `scripts\cdb\run_cdb_surface_dump.ps1` if it does not
   already exist, so right-bottom/bottom-tooltip probes can ride on the proven
   no-popup route.
3. Run one normal CDB-only hidden-desktop dump and confirm whether
   `UI_DrawUnitInfoPane`, `00435280`, or `00435500` executes during gameplay.
4. If text executes, compare its logged coordinates/rectangles with the
   reconstructed screenshot and decide between redraw-order, surface-present,
   or anchor-relocation patching.
5. Only after that evidence, add a tiny patch group to `patch_clash95_hd.py`
   with per-offset byte validation and a matching CDB proof.
