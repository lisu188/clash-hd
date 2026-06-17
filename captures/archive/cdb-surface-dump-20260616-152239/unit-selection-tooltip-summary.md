# Unit Selection Tooltip And Action Bar Summary

- Log: `captures\archive\cdb-surface-dump-20260616-152239\cdb-surface-dump.log`
- PNG: `captures\archive\cdb-surface-dump-20260616-152239\surface.png`
- Expected slot: `0`
- Evidence pass: `False`
- Overall tooltip recovered: `False`
- Decision: `BASIC_EVIDENCE_FAILED`
- Unit route pass: `False`
- Post-redraw action-bar route: `False`
- Hover sequence observed: `False`
- Missing hover modes: `['action_box_hover', 'action_grid_hover', 'bottom_tooltip_hover', 'safe_center_hold', 'selected_unit_hover']`
- Tooltip owner evidence: `False`
- Tooltip owner row count: `0`
- Tooltip present rows by region: `{'frame_left': 0, 'frame_top': 0, 'right_frame_under_minimap': 0, 'bottom_tooltip': 0, 'bottom_right_panel': 0, 'bottom_frame': 0}`
- Tooltip null-present rows by region: `{'frame_left': 0, 'frame_top': 0, 'right_frame_under_minimap': 0, 'bottom_tooltip': 0, 'bottom_right_panel': 0, 'bottom_frame': 0}`
- Action-bar visible: `True`
- Tooltip strip nonblack: `True`
- Tooltip strip visible: `False`
- AV rows: `0`

## Classification
- first-mission selection/post-redraw action-bar route failed one or more gates
- tooltip/action hover sequence was incomplete
- native tooltip/status owner evidence was not observed
- selected-unit action-bar visual regression gate passed at the expected bottom strip
- native bottom tooltip strip has nonblack pixels without owner evidence
- no AV rows were observed

## Hover Modes
- none

## PNG Regions
- `selected_unit_action_bar`: nonblack `76.268%`, black `23.732%`, mean_luma `64.666`, rect `[150, 555, 520, 599]`
- `bottom_tooltip_strip`: nonblack `68.324%`, black `31.676%`, mean_luma `64.48`, rect `[32, 528, 585, 599]`

## First Tooltip Entries
- none
