# Manual DirectInput Validation Checklist

- Overall: PASS
- Generated: `2026-07-18T21:30:47+02:00`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Checklist policy: manual DirectInput evidence is tracked separately from CDB/proxy proof; visible/manual validation requires explicit user approval; Do not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows unless the user explicitly approves.
- No-popup operator preference: Do not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows unless the user explicitly approves.
- Status: `pending_manual_validation`
- Promotion ready: `False`
- Stable stage should change: `False`
- Visible runtime requires approval: `True`
- Manual proof supplied: `False`
- Manual proof valid: `False`
- Explicit CDB-only override: `False`

## Checklist

### Stable HD map stage menu load and held-click route

- ID: `stable_menu_load`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Status: `pending_manual`
- Input route: real mouse movement plus held left-clicks on the active desktop
- Expected observation: startup reaches the menu, centered 640x480 menu hitboxes respond, and held clicks are not missed by DirectInput polling
- Current CDB evidence: dynamic-origin/menu CDB and route evidence only
- Promotion relevance: blocks treating synthetic input proof as manual menu proof

### Stable HD map edge scroll, minimap, and selection input

- ID: `stable_hd_map_input`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Status: `pending_manual`
- Input route: real mouse movement near map edges plus held clicks on map/minimap targets
- Expected observation: map cursor movement, edge scrolling, minimap/action-panel clicks, and right/bottom tile selection align with the 800x600 presentation
- Current CDB evidence: hidden CDB/proxy map and grid-hit evidence only
- Promotion relevance: blocks broader stable HD input promotion

### Right-bottom composition validation-stage manual input

- ID: `right_bottom_validation_input`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- Status: `pending_manual`
- Input route: real mouse movement and held clicks around the recovered lower/right UI
- Expected observation: status/action UI remains recovered while owner/action hit-tests and grid selection still respond at the expected displayed positions
- Current CDB evidence: right-bottom composition matrix, route timing guard, and controlled native (450,73) grid-hit proof
- Promotion relevance: blocks promoting rightbottomcompose into the stable stage

### Castle barracks centered manual input

- ID: `castle_barracks_centered_input`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`
- Status: `pending_manual`
- Input route: real mouse movement and held clicks on centered barracks descriptors/actions
- Expected observation: barracks descriptor and action callbacks remain reachable through the centered 80,60 presentation
- Current CDB evidence: barracks controlled-stop descriptor/action CDB proof
- Promotion relevance: blocks treating barracks CDB proof as real input proof

### Full castle overview centered manual input

- ID: `castle_overview_centered_input`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`
- Status: `pending_manual`
- Input route: real mouse movement and held clicks on visible overview descriptors
- Expected observation: visible overview commands such as 0x86, 0x63, and 0x87 respond at displayed centered coordinates without using debugger-forced state
- Current CDB evidence: focused overview hitbox, visible multi-hit, dormant multi-hit, and castle overview probe guard evidence
- Promotion relevance: blocks promoting castlecenter-all into the stable stage
