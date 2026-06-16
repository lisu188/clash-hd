# Bottom Tooltip Current Evidence

Date: 2026-05-27

Status: tooltip/status not recovered. The selected-unit action-bar post-redraw
validation pass now places the selected-unit panel at the centered bottom edge,
but the persistent native bottom tooltip strip at `x=32..585`, `y=528..599` is
still separate owner/state work.

2026-06-16 correction: accepted selected-unit action-bar placement is now
`x=215..585`, `y=580..599`. The old `y=455..500` frame is route evidence only;
`captures/archive/cdb-surface-dump-20260616-133855` and
`captures/archive/cdb-surface-dump-20260616-135148` prove the route at lower
but superseded placements. Current black-patch audit rerun
`captures/archive/cdb-surface-dump-20260616-153751` adds minimap backing samples
and is now the first-mission visual audit primary.

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
- Archived result at the old visual target: `evidence_pass=True`, `unit_basic_pass=True`,
  `post_redraw_route=True`, `hover_sequence_observed=True`,
  `tooltip_owner_evidence=False`, `action_bar_visible=True`,
  `tooltip_strip_visible=False`, and `av_count=0`.
- Current parser result after the 2026-06-16 bottom target correction:
  `evidence_pass=False`, `unit_basic_pass=True`, `post_redraw_route=True`,
  `hover_sequence_observed=True`, `tooltip_owner_evidence=False`,
  `action_bar_visible=False`, `tooltip_strip_visible=False`, and `av_count=0`.
- The old selected-unit action-bar visual gate passed after the later redraw
  cadence with `99.982%` nonblack at `x=150..520`, `y=455..500`; that placement
  is now rejected as middle-screen/legacy placement.
- The current selected-unit action-bar visual target is the centered bottom
  edge at `x=215..585`, `y=580..599`; fresh run
  `captures/archive/cdb-surface-dump-20260616-153751` proves that target.
- Tooltip/status owner rows still do not fire: text rows `0`, non-null present
  rows `0`, and null-destination bottom-region rows only.

Fresh selected-unit bottom placement probe:

- Run: `captures/archive/cdb-surface-dump-20260616-133855`
- Screenshot: `captures/archive/cdb-surface-dump-20260616-133855/surface.png`
- Summary: `captures/archive/cdb-surface-dump-20260616-133855/unit-selection-tooltip-summary.md`
- Result: hidden-desktop dump passed with no AV rows; `action_bar_visible=True`
  at the corrected bottom target, and the black/red gauge strip is no longer
  visible in the lower-map fragment.
- Tooltip/status remains unrecovered: `tooltip_owner_evidence=False`,
  `tooltip_strip_visible=False`, and no native tooltip text/present owner rows
  fired.

Combined natural selected-unit/right-bottom validation probe:

- Run: `captures/archive/cdb-surface-dump-20260616-135148`
- Screenshot: `captures/archive/cdb-surface-dump-20260616-135148/surface.png`
- Summary: `captures/archive/cdb-surface-dump-20260616-135148/unit-selection-tooltip-summary.md`
- Result: hidden-desktop dump passed with no AV rows; all five hover states
  were forced, `action_bar_visible=True`, `tooltip_owner_evidence=False`, and
  `tooltip_strip_visible=False`.
- This remains the broad hover-state evidence. The current first-mission visual
  audit primary is `captures/archive/cdb-surface-dump-20260616-153751`, which
  adds minimap backing samples while preserving the centered bottom selected-unit
  bar.

Current minimap-surface black-patch audit:

- Run: `captures/archive/cdb-surface-dump-20260616-153751`
- Screenshot: `captures/archive/cdb-surface-dump-20260616-153751/surface.png`
- Summary: `captures/current/first-mission-minimap-surface-current.md`
- Result: hidden-desktop dump passed with no AV rows. It reports no stripe
  failures and confirms the selected-unit action bar remains centered at the
  bottom edge.
  The image-only audit still sees black regions at `right_below_minimap`,
  `bottom_right_panel`, and `minimap_interior`, but the same run's visibility
  coverage explains all 13 active right/bottom map blank cells as
  `visibility_zero`.
- Minimap backing samples are already mostly black-like before final HD surface
  sampling, so the next tooltip/right-bottom target is owner/state population
  or natural panel composition, not another selected-unit action-bar move or
  right/bottom tile draw patch.

Controlled post-owner diagnostic with the same candidate:

- Run: `captures/archive/cdb-surface-dump-20260616-135432`
- Screenshot: `captures/archive/cdb-surface-dump-20260616-135432/surface.png`
- Result: APPOST/APCOMPOSE rows fired and copied controlled right/bottom
  regions, but the dumped PNG is stripe-heavy and lacks the selected-unit
  bottom-bar visual gate. It is diagnostic evidence only, not a playable
  first-mission frame.

## Current Interpretation

The bottom tooltip strip is not missing because the selected-unit action-bar
route is missing. The route now persists after redraw in the validation lane,
and visual centered bottom-edge placement is proven by the fresh selected-unit
frame.
The true bottom strip remains a separate owner/state problem. In the latest
evidence, the full-redraw path reaches rectangles that cover the strip, but
only through null-destination low-level rows and without any tooltip text/status
owner rows.

The next tooltip patch should not move the selected-unit action panel again.
The next debugging target is the bottom-tooltip owner/state trigger: prove which
routine is supposed to populate `y=528..599`, then either force the correct
owner after redraw or copy its native output to `dword_5202E0`.
