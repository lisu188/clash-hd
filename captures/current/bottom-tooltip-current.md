# Bottom Tooltip Current Evidence

Date: 2026-05-27

Status: not recovered. The selected-unit action-bar post-redraw validation pass
restored a bottom text/morale panel around `y=455..500`, but that is not the
persistent bottom tooltip strip at `x=32..585`, `y=528..599`.

## Stage

`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitselectactionbarpostredraw`

Candidate SHA-256:
`85BC35640196192020598C6E9EFCCCDFA3D1997B22A1A995FF14DBA134351ADE`

## Fresh Evidence

Border/tooltip owner probe:

- Run: `captures/archive/cdb-surface-dump-20260527-101402`
- Extra probe: `probes/cdb/ui/clash95_border_tooltip_extra.cdb`
- Summary: `captures/archive/cdb-surface-dump-20260527-101402/border-tooltip-summary.md`
- Screenshot: `captures/archive/cdb-surface-dump-20260527-101402/surface.png`
- Result: `fullredraw=4`, `text=0`, `present=0`, `present_null=24`, `entries=0`, `av=0`.
- Null-destination rows overlap the bottom regions:
  `bottom_tooltip=4`, `bottom_right_panel=4`, `bottom_frame=4`.
- PNG bounds report the real bottom tooltip strip as `0.0%` nonblack.

Hover/selection UI probe:

- Run: `captures/archive/cdb-surface-dump-20260527-101727`
- Extra probe: `probes/cdb/ui/clash95_hover_selection_ui_extra.cdb`
- Summary: `captures/archive/cdb-surface-dump-20260527-101727/hover-selection-ui-summary.md`
- Screenshot: `captures/archive/cdb-surface-dump-20260527-101727/surface.png`
- Result: `ready=True`, `av_count=0`, `force_states=4`, `entries=0`, `presents=0`.
- Forced states were `map_hover`, `action_grid_hover`, `action_box_hover`, and
  `safe_center_hold`; no target tooltip/status/action UI function ran.
- PNG bounds again report `bottom_tooltip_strip=0.0%` nonblack.

Selected-unit action-bar comparison:

- Run: `captures/archive/cdb-surface-dump-20260527-100641`
- Summary: `captures/archive/cdb-surface-dump-20260527-100641/unit-selection-action-bar-summary.md`
- Result: selected-unit route `00406980` and action update
  `0040A500 -> 00423B00` pass, and the text/morale panel is visible around the
  lower middle of the map surface.
- Interpretation: this is a separate selected-unit bottom panel, not the
  persistent bottom tooltip strip.

Combined first-mission tooltip/action-bar regression probe:

- Run: `captures/archive/cdb-surface-dump-20260527-111658`
- Extra probe: `probes/cdb/ui/clash95_unit_selection_tooltip_action_bar_extra.cdb`
- Summary: `captures/archive/cdb-surface-dump-20260527-111658/unit-selection-tooltip-summary.md`
- Screenshot: `captures/archive/cdb-surface-dump-20260527-111658/surface.png`
- Result: `unit_basic_pass=True`, `hover_sequence_observed=True`,
  `tooltip_owner_evidence=False`, `action_bar_visible=False`,
  `tooltip_strip_visible=False`, and `av_count=0`.
- The probe forced selected-unit, bottom-tooltip, action-grid, action-box, and
  safe-center hover states. No native tooltip/status owner rows, text rows, or
  non-null bottom-strip present rows fired.
- The bottom strip has `67.461%` nonblack pixels in this final PNG, but those
  pixels are not owner-backed tooltip evidence. The selected-unit action-bar
  visual gate also fails after the later redraw cadence with `0.0%` nonblack at
  `x=150..520`, `y=455..500`.

Post-redraw action-bar recovery probe:

- Run: `captures/archive/cdb-surface-dump-20260527-114559`
- Extra probe: `probes/cdb/ui/clash95_unit_selection_tooltip_action_bar_extra.cdb`
- Summary: `captures/archive/cdb-surface-dump-20260527-114559/unit-selection-tooltip-summary.md`
- Screenshot: `captures/archive/cdb-surface-dump-20260527-114559/surface.png`
- Result: `evidence_pass=True`, `unit_basic_pass=True`,
  `post_redraw_route=True`, `hover_sequence_observed=True`,
  `tooltip_owner_evidence=False`, `action_bar_visible=True`,
  `tooltip_strip_visible=False`, and `av_count=0`.
- The selected-unit action-bar visual gate now passes after the later redraw
  cadence with `99.982%` nonblack at `x=150..520`, `y=455..500`.
- Tooltip/status owner rows still do not fire: text rows `0`, non-null present
  rows `0`, and null-destination bottom-region rows only.

## Current Interpretation

The bottom tooltip strip is not missing because the selected-unit action-bar
route is missing. The route now persists after redraw in the validation lane.
The true bottom strip remains a separate owner/state problem. In the latest
evidence, the full-redraw path reaches rectangles that cover the strip, but
only through null-destination low-level rows and without any tooltip text/status
owner rows.

The next tooltip patch should not move the selected-unit action panel again.
The next debugging target is the bottom-tooltip owner/state trigger: prove which
routine is supposed to populate `y=528..599`, then either force the correct
owner after redraw or copy its native output to `dword_5202E0`.
