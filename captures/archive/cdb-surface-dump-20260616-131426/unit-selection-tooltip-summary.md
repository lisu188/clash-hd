# Unit Selection Tooltip And Action Bar Summary

- Log: `captures\archive\cdb-surface-dump-20260616-131426\cdb-surface-dump.log`
- PNG: `captures\archive\cdb-surface-dump-20260616-131426\surface.png`
- Expected slot: `0`
- Evidence pass: `True`
- Overall tooltip recovered: `False`
- Decision: `NO_PATCH_OWNER_NOT_REACHED`
- Unit route pass: `True`
- Post-redraw action-bar route: `True`
- Hover sequence observed: `True`
- Missing hover modes: `[]`
- Tooltip owner evidence: `False`
- Tooltip owner row count: `0`
- Tooltip present rows by region: `{'frame_left': 0, 'frame_top': 0, 'right_frame_under_minimap': 0, 'bottom_tooltip': 0, 'bottom_right_panel': 0, 'bottom_frame': 0}`
- Tooltip null-present rows by region: `{'frame_left': 0, 'frame_top': 0, 'right_frame_under_minimap': 4, 'bottom_tooltip': 4, 'bottom_right_panel': 4, 'bottom_frame': 4}`
- Action-bar visible: `True`
- Tooltip strip nonblack: `True`
- Tooltip strip visible: `False`
- AV rows: `0`

## Classification
- first-mission selection and post-redraw 00406980 action-bar route passed
- all five tooltip/action hover states were forced
- native tooltip/status owner evidence was not observed
- selected-unit action-bar visual regression gate passed at the expected bottom strip
- native bottom tooltip strip has nonblack pixels without owner evidence
- no AV rows were observed

## Hover Modes
- selected_unit_hover
- bottom_tooltip_hover
- action_grid_hover
- action_box_hover
- safe_center_hold

## PNG Regions
- `selected_unit_action_bar`: nonblack `96.461%`, black `3.539%`, mean_luma `89.549`, rect `[150, 528, 520, 573]`
- `bottom_tooltip_strip`: nonblack `67.464%`, black `32.536%`, mean_luma `64.848`, rect `[32, 528, 585, 599]`

## First Tooltip Entries
- none
