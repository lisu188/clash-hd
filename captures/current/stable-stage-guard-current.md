# Stable Stage Guard

- Overall: PASS
- Generated: `2026-07-17T15:36:44+02:00`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, or visible windows
- Current stable stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Patcher default stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Validation-only groups in stable stage: `[]`
- Mapsurface stages checked: `['gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapclip', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter-inputprobe', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-framerestore', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-hdlayout', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-hdlayout-framerestore', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter-no-castleinput', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose-unitselectactionbarpostredraw', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-tooltipbottomcenter', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitcommandpanel-rightbottom', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitselectactionbar', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitselectactionbarpostredraw', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-vswitch', 'gameplay-menu640-centered-map12-hybridmouse-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch']`
- Mapsurface stages with menu-surface: `[]`
- Mapsurface stages missing upgrade: `[]`

## Checks

- `patcher_default_stage`: `PASS`
- `stable_stage_defined`: `PASS`
- `stable_stage_validation_groups_absent`: `PASS`
- `validation_stage_scope_rightbottomcompose`: `PASS`
- `validation_stage_scope_tooltipbottomcenter`: `PASS`
- `validation_stage_scope_unitcommandpanel_rightbottom`: `PASS`
- `validation_stage_scope_hdlayout`: `PASS`
- `validation_stage_scope_framerestore`: `PASS`
- `validation_stage_scope_hdlayout_framerestore`: `PASS`
- `validation_stage_scope_castlecenter`: `PASS`
- `validation_stage_scope_castlecenter_hitbox`: `PASS`
- `validation_stage_scope_castlecenter_all`: `PASS`
- `validation_stage_scope_castlecenter_all_battlecenter`: `PASS`
- `validation_stage_scope_castlecenter_all_battlecenter_inputprobe`: `PASS`
- `menu_surface_replaced_by_map_surface_upgrade`: `PASS`
- `right_bottom_promotion_decision`: `PASS`
- `right_bottom_evidence_matrix`: `PASS`
- `castle_overview_promotion_decision`: `PASS`
  - `focused_displayed_wrapper_ok`: `True`
  - `visible_multihit_completion_ok`: `True`
  - `dormant_multihit_completion_ok`: `True`
- `castle_overview_evidence_matrix`: `PASS`
  - `focused_displayed_wrapper_ok`: `True`
  - `visible_multihit_completion_ok`: `True`
  - `dormant_multihit_completion_ok`: `True`

## Validation-Only Groups

- `right-bottom-compose-proof`
- `terrain-tooltip-bottom-center`
- `selected-unit-command-panel-right-bottom`
- `castle-ui-center-present`
- `castle-ui-center-present-wrapper`
- `castle-ui-centered-input`
- `castle-overview-center-present-wrapper`
- `castle-overview-centered-input`
- `battle-ui-center-present-wrapper`
- `battle-grid-centered-input`
- `battle-ui-centered-input`
- `frame-restore-bands`

## Validation Stages

- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`: `['right-bottom-compose-proof']`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-tooltipbottomcenter`: `['terrain-tooltip-bottom-center']`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitcommandpanel-rightbottom`: `['selected-unit-command-panel-right-bottom']`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-hdlayout`: `['terrain-tooltip-bottom-center', 'selected-unit-command-panel-right-bottom']`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-framerestore`: `['frame-restore-bands']`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-hdlayout-framerestore`: `['terrain-tooltip-bottom-center', 'selected-unit-command-panel-right-bottom', 'frame-restore-bands']`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter`: `['castle-ui-center-present']`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox`: `['castle-ui-center-present', 'castle-ui-centered-input']`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`: `['castle-ui-center-present-wrapper', 'castle-ui-centered-input', 'castle-overview-center-present-wrapper', 'castle-overview-centered-input']`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`: `['castle-ui-center-present-wrapper', 'castle-ui-centered-input', 'castle-overview-center-present-wrapper', 'castle-overview-centered-input', 'battle-ui-center-present-wrapper']`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter-inputprobe`: `['castle-ui-center-present-wrapper', 'castle-ui-centered-input', 'castle-overview-center-present-wrapper', 'castle-overview-centered-input', 'battle-ui-center-present-wrapper', 'battle-grid-centered-input', 'battle-ui-centered-input']`
