# Unit Selection Tooltip And Action Bar Current Evidence

Date: 2026-05-27

Status: selected-unit action bar recovered in the final post-redraw surface
dump. Native bottom-tooltip/status recovery remains evidence-only because no
owner rows fired.

## Stage

`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitselectactionbarpostredraw`

Patch groups:

- `unit-selection-action-bar-map-surface`: 6/6 patched, 0 original, 0 unexpected.
- `unit-selection-action-bar-post-redraw`: 3/3 patched, 0 original, 0 unexpected.

Combined probe:

- `probes/cdb/ui/clash95_unit_selection_tooltip_action_bar_extra.cdb`

Candidate:

- `C:\ClashTests\unit-selection-actionbar-postredraw\clash95_hd_surfdump_20260527_114559.exe`
- SHA-256: `85BC35640196192020598C6E9EFCCCDFA3D1997B22A1A995FF14DBA134351ADE`

## Evidence

Run:

- `captures/archive/cdb-surface-dump-20260527-114559`
- Screenshot: `captures/archive/cdb-surface-dump-20260527-114559/surface.png`
- Combined summary: `captures/archive/cdb-surface-dump-20260527-114559/unit-selection-tooltip-summary.md`
- Action-bar summary: `captures/archive/cdb-surface-dump-20260527-114559/unit-selection-action-bar-summary.md`
- Hover summary: `captures/archive/cdb-surface-dump-20260527-114559/hover-selection-ui-summary.md`
- Border/tooltip summary: `captures/archive/cdb-surface-dump-20260527-114559/border-tooltip-summary.md`
- Patch manifest: `captures/archive/patch-stage-unit-selection-actionbar-postredraw-20260527.json`

Combined summary:

- `evidence_pass=True`
- `unit_basic_pass=True`
- `post_redraw_route=True`
- `hover_sequence_observed=True`
- `tooltip_owner_evidence=False`
- `action_bar_visible=True`
- `tooltip_strip_visible=False`
- `av_count=0`
- `decision=NO_PATCH_OWNER_NOT_REACHED`

The probe forced five states: `selected_unit_hover`, `bottom_tooltip_hover`,
`action_grid_hover`, `action_box_hover`, and `safe_center_hold`.

The selected-unit action-bar visual gate passes in the final post-redraw PNG:
`selected_unit_action_bar` at `x=150..520`, `y=455..500` is `99.982%`
nonblack.

The true native bottom strip `x=32..585`, `y=528..599` has `67.461%`
nonblack pixels in the final PNG, but the combined parser classifies that as
non-owner-backed coverage. The tooltip owner row count is `0`, text rows are
`0`, non-null present rows are `0`, and null-destination rows overlap
`bottom_tooltip=5`, `bottom_right_panel=5`, and `bottom_frame=5`.

## Patch Decision

The selected-unit action-bar recovery patch is validated for this first-mission
lane. No native tooltip/status patch group was added because the plan requires
native tooltip/status owner evidence first, and this run did not produce owner
rows.

Next useful tooltip work is to identify the missing owner/state trigger that
should populate the native bottom strip after redraw, then rerun this same
combined first-mission lane.

## Percentage Summary

- This implementation pass: `100.00%` complete for post-redraw action-bar recovery.
- Current repo evidence gates: `97.37%`
- Focused battle/right-bottom command lane: `99.91%`
- Right-bottom promotion gate: `85.71%`
- Manual DirectInput validation: `0.00%`
- Full game: not `100%`; manual DirectInput proof and stable promotion remain blocked.
