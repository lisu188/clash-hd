# Unit Selection Tooltip And Action Bar Current Evidence

Date: 2026-05-27

Status: selected-unit route and bottom visual placement recovered in the
validation lane. Native bottom-tooltip/status recovery remains evidence-only
because no owner rows fired.

2026-06-16 correction: accepted selected-unit action-bar placement is the
centered bottom edge at `x=215..585`, `y=580..599`. The archived
`20260527-114559` frame is route evidence only; `20260616-133855` and
`20260616-135148` prove the route at a lower but still too-high placement;
`20260616-153155` proves bottom-edge placement; and `20260616-153751` is the
current centered bottom-edge black-patch audit primary.

## Stage

`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitselectactionbarpostredraw`

Patch groups:

- `unit-selection-action-bar-map-surface`: 4/4 patched, 0 original, 0 unexpected.
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

Archived combined summary at the old visual target:

- `evidence_pass=True`
- `unit_basic_pass=True`
- `post_redraw_route=True`
- `hover_sequence_observed=True`
- `tooltip_owner_evidence=False`
- `action_bar_visible=True`
- `tooltip_strip_visible=False`
- `av_count=0`
- `decision=NO_PATCH_OWNER_NOT_REACHED`

Current parser result over the same archived run after the 2026-06-16 bottom
target correction:

- `evidence_pass=False`
- `unit_basic_pass=True`
- `post_redraw_route=True`
- `hover_sequence_observed=True`
- `tooltip_owner_evidence=False`
- `action_bar_visible=False`
- `tooltip_strip_visible=False`
- `av_count=0`
- `decision=BASIC_EVIDENCE_FAILED`

Fresh bottom-placement run:

- Run: `captures/archive/cdb-surface-dump-20260616-133855`
- Screenshot: `captures/archive/cdb-surface-dump-20260616-133855/surface.png`
- Summary: `captures/archive/cdb-surface-dump-20260616-133855/unit-selection-tooltip-summary.md`
- Candidate SHA-256: `1E778769F5DC5E99DF09278EA53107CA2FF7165C4699FCD6CA25F7999F51A5FF`
- `unit_basic_pass=True`
- `post_redraw_route=True`
- `action_bar_visible=True`
- `tooltip_owner_evidence=False`
- `tooltip_strip_visible=False`
- `av_count=0`
- `decision=BASIC_EVIDENCE_FAILED`

The fresh run proves the selected-unit panel and black/red gauge are in the
bottom strip, but it is not a complete tooltip-owner pass: the forced hover
sequence stopped before `action_box_hover` and `safe_center_hold`, and native
tooltip owner rows still did not fire.

Combined natural first-mission rerun:

- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose-unitselectactionbarpostredraw`
- Run: `captures/archive/cdb-surface-dump-20260616-135148`
- Screenshot: `captures/archive/cdb-surface-dump-20260616-135148/surface.png`
- Summary: `captures/archive/cdb-surface-dump-20260616-135148/unit-selection-tooltip-summary.md`
- Candidate SHA-256: `F1B11E22C9CFB0AAA1CCC325526FC08B952CA6323739CEED3D279B7CB07FB440`
- Result: `evidence_pass=True`, `unit_basic_pass=True`,
  `post_redraw_route=True`, `hover_sequence_observed=True`,
  `action_bar_visible=True`, `tooltip_owner_evidence=False`,
  `tooltip_strip_visible=False`, `av_count=0`, and
  `decision=NO_PATCH_OWNER_NOT_REACHED`.
- This rerun forced all five states: `selected_unit_hover`,
  `bottom_tooltip_hover`, `action_grid_hover`, `action_box_hover`, and
  `safe_center_hold`.
- This rerun remains the broad hover-state evidence. The first-mission visual
  audit now uses `captures/archive/cdb-surface-dump-20260616-153751` as the
  current primary because that run proves the centered bottom-edge placement
  and samples minimap backing memory.

Current minimap-surface black-patch audit:

- Run: `captures/archive/cdb-surface-dump-20260616-153751`
- Screenshot: `captures/archive/cdb-surface-dump-20260616-153751/surface.png`
- Summary: `captures/current/first-mission-minimap-surface-current.md`
- Result: hidden-desktop dump passed with no AV rows, selected-unit route
  reached `selected_after=3`, the selected-unit action bar remains visible at
  the centered bottom-edge target, and the visual audit reports no stripe
  failures.
- Image-only black regions are still visible at `right_below_minimap`,
  `bottom_right_panel`, and `minimap_interior`, but the same run's
  `visibility-coverage-full.json` explains all 13 active right/bottom map
  blank cells as `visibility_zero`. The minimap backing samples are already
  mostly black-like before final HD surface sampling, so this run does not
  support another minimap anchor/read-past patch.

Controlled post-owner diagnostic with the same combined candidate:

- Run: `captures/archive/cdb-surface-dump-20260616-135432`
- Screenshot: `captures/archive/cdb-surface-dump-20260616-135432/surface.png`
- Result: APPOST/APCOMPOSE rows fire, including `APCOMPOSE_STATUS_SHIFT_DONE`
  and `APCOMPOSE_ACTION_SHIFT_DONE`, but the dumped PNG is stripe-heavy with
  `stripe_pass=False` and is not first-mission playability evidence.

The old selected-unit action-bar visual gate passed in the final post-redraw
PNG at `x=150..520`, `y=455..500`; user review found that location wrong.
Later `x=150..520`, `y=528..573` and `x=150..520`, `y=580..599` runs prove the
route but are visually superseded. The current gate expects centered
bottom-edge placement at `x=215..585`, `y=580..599`; fresh run
`captures/archive/cdb-surface-dump-20260616-153751` proves that target.

The true native bottom strip `x=32..585`, `y=528..599` has `67.461%`
nonblack pixels in the final PNG, but the combined parser classifies that as
non-owner-backed coverage. The tooltip owner row count is `0`, text rows are
`0`, non-null present rows are `0`, and null-destination rows overlap
`bottom_tooltip=5`, `bottom_right_panel=5`, and `bottom_frame=5`.

## Patch Decision

The selected-unit action-bar route and bottom placement are validated for this
first-mission lane. No native tooltip/status patch group was added because the
plan requires native tooltip/status owner evidence first, and the fresh run did
not produce owner rows.

Next useful tooltip work is to identify the missing owner/state trigger that
should populate the native bottom strip after redraw, then rerun this same
combined first-mission lane.

## Percentage Summary

- This implementation pass: `100.00%` complete for post-redraw action-bar
  route recovery and focused bottom-strip visual placement.
- Current repo evidence gates: `97.37%`
- Focused battle/right-bottom command lane: `99.91%`
- Right-bottom promotion gate: `85.71%`
- Manual DirectInput validation: `0.00%`
- Full game: not `100%`; manual DirectInput proof and stable promotion remain blocked.
