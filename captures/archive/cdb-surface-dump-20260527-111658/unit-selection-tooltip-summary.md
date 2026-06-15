# Unit Selection Tooltip And Action Bar Summary

- Log: `captures\cdb-surface-dump-20260527-111658\cdb-surface-dump.log`
- PNG: `captures\cdb-surface-dump-20260527-111658\surface.png`
- Expected slot: `0`
- Evidence pass: `False`
- Overall tooltip recovered: `False`
- Decision: `BASIC_EVIDENCE_FAILED`
- Unit route pass: `True`
- Hover sequence observed: `True`
- Missing hover modes: `[]`
- Tooltip owner evidence: `False`
- Tooltip owner row count: `0`
- Tooltip present rows by region: `{'frame_left': 0, 'frame_top': 0, 'right_frame_under_minimap': 0, 'bottom_tooltip': 0, 'bottom_right_panel': 0, 'bottom_frame': 0}`
- Tooltip null-present rows by region: `{'frame_left': 0, 'frame_top': 0, 'right_frame_under_minimap': 9, 'bottom_tooltip': 7, 'bottom_right_panel': 7, 'bottom_frame': 7}`
- Action-bar visible: `False`
- Tooltip strip nonblack: `True`
- Tooltip strip visible: `False`
- AV rows: `0`

## Classification
- first-mission selection and 00406980 action-bar route passed
- all five tooltip/action hover states were forced
- native tooltip/status owner evidence was not observed
- selected-unit action-bar visual regression gate failed
- native bottom tooltip strip has nonblack pixels without owner evidence
- no AV rows were observed

## Hover Modes
- selected_unit_hover
- bottom_tooltip_hover
- action_grid_hover
- action_box_hover
- safe_center_hold

## PNG Regions
- `selected_unit_action_bar`: nonblack `0.0%`, black `100.0%`, rect `[150, 455, 520, 500]`
- `bottom_tooltip_strip`: nonblack `67.461%`, black `32.539%`, rect `[32, 528, 585, 599]`

## First Tooltip Entries
- none
