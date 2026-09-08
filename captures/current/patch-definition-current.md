# Patch Definition Guard

- Overall: PASS
- Generated: `2026-09-08T11:21:21+02:00`
- Runtime policy: repo-only patch-table inspection; does not read, build, or execute game executables
- Guard policy: patch stage definitions must reference real groups, keep validation-only groups out of stable, keep validation stages scoped to stable plus expected extras, and avoid incompatible selected offset overlaps
- Expected stable stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Patcher default stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Patch count: `480`
- Patch groups: `55`
- Stages: `63`
- Validation-only groups in stable: `[]`
- Incompatible selected overlaps: `0`

## Validation Stages

- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-validation` extras=`['battle-grid-centered-input', 'battle-ui-center-present-wrapper', 'battle-ui-centered-input', 'castle-overview-center-present-wrapper', 'castle-overview-centered-input', 'castle-ui-center-present-wrapper', 'castle-ui-centered-input', 'frame-restore-bands', 'right-bottom-compose-proof', 'selected-unit-command-panel-right-bottom', 'terrain-tooltip-bottom-center']` missing=`[]` unexpected=`[]`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose` extras=`['right-bottom-compose-proof']` missing=`[]` unexpected=`[]`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-tooltipbottomcenter` extras=`['terrain-tooltip-bottom-center']` missing=`[]` unexpected=`[]`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitcommandpanel-rightbottom` extras=`['selected-unit-command-panel-right-bottom']` missing=`[]` unexpected=`[]`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-hdlayout` extras=`['selected-unit-command-panel-right-bottom', 'terrain-tooltip-bottom-center']` missing=`[]` unexpected=`[]`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter` extras=`['castle-ui-center-present']` missing=`[]` unexpected=`[]`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox` extras=`['castle-ui-center-present', 'castle-ui-centered-input']` missing=`[]` unexpected=`[]`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all` extras=`['castle-overview-center-present-wrapper', 'castle-overview-centered-input', 'castle-ui-center-present-wrapper', 'castle-ui-centered-input']` missing=`[]` unexpected=`[]`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter` extras=`['battle-ui-center-present-wrapper', 'castle-overview-center-present-wrapper', 'castle-overview-centered-input', 'castle-ui-center-present-wrapper', 'castle-ui-centered-input']` missing=`[]` unexpected=`[]`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter-inputprobe` extras=`['battle-grid-centered-input', 'battle-ui-center-present-wrapper', 'battle-ui-centered-input', 'castle-overview-center-present-wrapper', 'castle-overview-centered-input', 'castle-ui-center-present-wrapper', 'castle-ui-centered-input']` missing=`[]` unexpected=`[]`
- `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlehd` extras=`['battle-hd-camera', 'battle-hd-descriptors', 'battle-hd-dialogs', 'battle-hd-frame', 'battle-hd-hud', 'battle-hd-input', 'battle-hd-section', 'battle-hd-tooltip', 'battle-hd-viewport', 'castle-overview-center-present-wrapper', 'castle-overview-centered-input', 'castle-ui-center-present-wrapper', 'castle-ui-centered-input']` missing=`[]` unexpected=`[]`
