# Unit Selection Action Bar Current Evidence

Date: 2026-05-27

Status: validation-only post-redraw visual pass. The first-mission selected
unit is proven, the `00406980` route is rerun after full redraw exits, and the
selected-unit bottom text/morale action panel remains visible in the final
800x600 surface dump.

## Stage

`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitselectactionbarpostredraw`

Patch groups:

- `unit-selection-action-bar-map-surface`: 6/6 patched, 0 original, 0 unexpected.
- `unit-selection-action-bar-post-redraw`: 3/3 patched, 0 original, 0 unexpected.

Candidate:

- `C:\ClashTests\unit-selection-actionbar-postredraw\clash95_hd_surfdump_20260527_114559.exe`
- SHA-256: `85BC35640196192020598C6E9EFCCCDFA3D1997B22A1A995FF14DBA134351ADE`

## Evidence

Baseline first-mission selection route:

- `captures/archive/cdb-surface-dump-20260527-092117/surface.png`
- Strict summary proved load slot 0, first-mission selection success, selected-unit route `00406980`, present helper, action update, pre-redraw dump, and no AV.
- Visual result: selected unit is highlighted, but the selected-unit action panel is not present on the dumped HD map surface.

Pre-redraw copyback proof:

- `captures/archive/cdb-surface-dump-20260527-100641/surface.png`
- `captures/archive/cdb-surface-dump-20260527-100641/unit-selection-action-bar-summary.md`
- Strict summary: `slot_match=True`, `ready=True`, `pre_redraw_dump=True`, `selection_success=True`, `unit_info_route=True`, `present_helper=True`, `action_update=True`, `av_count=0`.
- Visual result: the selected-unit text/morale panel appears before the later redraw cadence.

Post-redraw recovery proof:

- `captures/archive/cdb-surface-dump-20260527-114559/surface.png`
- `captures/archive/cdb-surface-dump-20260527-114559/unit-selection-action-bar-summary.md`
- `captures/archive/cdb-surface-dump-20260527-114559/unit-selection-tooltip-summary.md`
- `captures/archive/patch-stage-unit-selection-actionbar-postredraw-20260527.json`
- Strict summary: `slot_match=True`, `ready=True`, `selection_success=True`, `unit_info_route=True`, `post_redraw_route=True`, `present_helper=True`, `action_update=True`, `av_count=0`.
- Visual result: final post-redraw `selected_unit_action_bar` at `x=150..520`, `y=455..500` is `99.982%` nonblack.
- Patch manifest: 127/127 expected bytes patched, current HD map gate PASS.

Native/default layer probe:

- `captures/archive/cdb-surface-dump-20260527-093348`
- The default/front surface at `0051D4C0` reported `size=(800,600)` and `base=00000000`, so it is renderable but not dumpable through the current host memory-base surface path.

## Remaining Gap

This validates the selected-unit bottom panel only. The full unit info pane,
native bottom tooltip strip, and broader button-grid/menu route remain separate
UI work. They still need owner/state evidence before any additional binary
patch is added or promoted.
