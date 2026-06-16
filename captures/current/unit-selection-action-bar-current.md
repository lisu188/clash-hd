# Unit Selection Action Bar Current Evidence

Date: 2026-05-27

Status: validation-only centered bottom-edge panel placement recovered. The
first-mission selected unit is proven, the `00406980` route is rerun after full
redraw exits, and the fresh hidden CDB frame places the selected-unit panel at
the centered bottom edge of the 800x600 surface. A combined validation-stage
rerun preserves that placement while confirming the remaining first mission
blockers are separate right/bottom/minimap black patches.

2026-06-16 correction: the accepted target for this panel is the screen bottom
edge at `x=215..585`, `y=580..599`. The old archived `y=455..500` frame remains
useful route evidence, the intermediate `y=528..573` frame proves the route but
is still too high, and the `x=150..520` bottom-edge frame is too far left.

## Stage

`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitselectactionbarpostredraw`

Patch groups:

- `unit-selection-action-bar-map-surface`: 4/4 patched, 0 original, 0 unexpected.
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
- Legacy visual result: final post-redraw `selected_unit_action_bar` at
  `x=150..520`, `y=455..500` is `99.982%` nonblack, which is now classified as
  the wrong middle-screen placement.
- Current required visual target: rerun this validation lane and prove the
  panel appears at the centered bottom edge at `x=215..585`, `y=580..599`.
- Patch manifest: 127/127 expected bytes patched, current HD map gate PASS.

Superseded lower-strip placement proof:

- `captures/archive/cdb-surface-dump-20260616-133855/surface.png`
- `captures/archive/cdb-surface-dump-20260616-133855/RUN-SUMMARY.md`
- `captures/archive/cdb-surface-dump-20260616-133855/unit-selection-tooltip-summary.md`
- Candidate SHA-256: `1E778769F5DC5E99DF09278EA53107CA2FF7165C4699FCD6CA25F7999F51A5FF`.
- Result: hidden-desktop surface dump passed with no AV rows. This proves the
  route and a lower placement at `x=150..520`, `y=528..573`, but that placement
  is now superseded because the visible bar still floats above the bottom edge.
- Legacy middle region is no longer classified as the selected-unit panel:
  `legacy_middle_action_bar_visible=False` in
  `captures/current/first-mission-visual-audit-current.md`.
- The old validation-only `0x51BC10` gauge copy wrapper is no longer part of
  the current byte set; a later bottom-edge attempt showed that inherited gauge
  source rectangles can corrupt or AV when moved down without their own source
  crop.

Combined-stage natural rerun:

- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose-unitselectactionbarpostredraw`
- Run: `captures/archive/cdb-surface-dump-20260616-135148`
- Screenshot: `captures/archive/cdb-surface-dump-20260616-135148/surface.png`
- Summary: `captures/archive/cdb-surface-dump-20260616-135148/unit-selection-tooltip-summary.md`
- Candidate SHA-256: `F1B11E22C9CFB0AAA1CCC325526FC08B952CA6323739CEED3D279B7CB07FB440`.
- Result: hidden-desktop surface dump passed with no AV rows. The selected-unit
  route and intermediate lower placement remain useful evidence, but the
  current centered bottom-edge target is proven by the later `20260616-153751`
  run.
- Remaining visual blockers in that same natural frame are
  `right_below_minimap`, `bottom_right_panel`, and `minimap_interior`.

Current first-mission centered bottom-edge/minimap/right-panel audit:

- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose-unitselectactionbarpostredraw`
- Run: `captures/archive/cdb-surface-dump-20260616-153751`
- Screenshot: `captures/archive/cdb-surface-dump-20260616-153751/surface.png`
- Minimap surface summary:
  `captures/current/first-mission-minimap-surface-current.md`
- Candidate SHA-256: `459C30639CBDF5FF0B8F5F6048B61DA409656390E96CC92493DBB916F189BF93`.
- Result: hidden-desktop surface dump passed with no AV rows. The first-mission
  visual audit uses this frame as the current primary and still reports no
  stripe failures, the selected-unit action bar visible at the centered
  bottom-edge target, and image-visible black regions in `right_below_minimap`,
  `bottom_right_panel`, and `minimap_interior`.
- The minimap backing probe reports bounds `586,16..799,229`, backing size
  `214x214`, and mostly black-like backing samples before final surface
  sampling, so the current minimap black interior is not treated as an HD anchor
  or read-past copy failure.
- Full map coverage for the same run reports 13 blank active cells, and
  `captures/archive/cdb-surface-dump-20260616-153751/visibility-coverage-full.json`
  explains all 13 as `visibility_zero` with no unexplained blank cells. The
  right/bottom map darkness in this frame is therefore visibility/fog evidence,
  not a tile draw failure.

Native/default layer probe:

- `captures/archive/cdb-surface-dump-20260527-093348`
- The default/front surface at `0051D4C0` reported `size=(800,600)` and `base=00000000`, so it is renderable but not dumpable through the current host memory-base surface path.

## Remaining Gap

This validates the selected-unit route and centered bottom-edge visual
placement in the validation lane only. The full unit info pane, gauge source
crop, native bottom tooltip strip, top/left edge frame fill, and broader
button-grid/menu route remain separate UI work. They still need owner/state
evidence before any additional binary patch is promoted.
