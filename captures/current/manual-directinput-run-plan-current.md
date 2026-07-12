# Manual DirectInput Run Plan

- Overall: PASS
- Generated: `2026-07-12T20:47:54+02:00`
- Runtime policy: repo-only command planner; reads generated JSON and writes JSON/Markdown reports; does not run PowerShell, launch Clash95, CDB, wrappers, move the mouse, or open visible windows
- Guard policy: manual DirectInput commands remain templates until explicit user approval; every visible runtime command must carry -AllowVisibleRuntime and the proof manifest must be validated before promotion
- Candidate path policy: candidate placeholders must resolve to freshly built, hashed executables under C:\ClashTests; never use C:\Clash\clash95.exe or a repository-local executable
- Candidate root: `C:\ClashTests`
- Visible runtime requires approval: `True`
- Proof ready: `False`
- Manual target count: `5`
- All commands have -AllowVisibleRuntime: `True`
- Manual proof valid: `False`
- Promotion ready: `False`

## Commands

### Stable HD map stage menu load and held-click route

- ID: `stable_menu_load`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate placeholder: `C:\ClashTests\manual-directinput\<stable-hd-map-candidate-exe>`
- Candidate path policy: candidate placeholders must resolve to freshly built, hashed executables under C:\ClashTests; never use C:\Clash\clash95.exe or a repository-local executable
- Route: `load-slot0`
- Load-route points: `300,218;320,166;400,226`
- Follow-up manual points: `n/a`
- Notes: proves the centered menu load route and held-click cadence with real DirectInput

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\smoke\run_clash_visual_smoke.ps1' -Exe 'C:\ClashTests\manual-directinput\<stable-hd-map-candidate-exe>' -WorkDir 'C:\Clash' -Route 'load-slot0' -Points '300,218;320,166;400,226' -MoveMode auto -ClickMode sendinput -ClickHoldMs 300 -ClickRepeat 2 -AllowVisibleRuntime
```

### Stable HD map edge scroll, minimap, and selection input

- ID: `stable_hd_map_input`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate placeholder: `C:\ClashTests\manual-directinput\<stable-hd-map-candidate-exe>`
- Candidate path policy: candidate placeholders must resolve to freshly built, hashed executables under C:\ClashTests; never use C:\Clash\clash95.exe or a repository-local executable
- Route: `load-slot0`
- Load-route points: `300,218;320,166;400,226`
- Follow-up manual points: `400,300;780,300;400,580;760,560`
- Notes: the command reaches gameplay through the load route; then manually exercise the listed map edge/minimap/selection points

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\smoke\run_clash_visual_smoke.ps1' -Exe 'C:\ClashTests\manual-directinput\<stable-hd-map-candidate-exe>' -WorkDir 'C:\Clash' -Route 'load-slot0' -Points '300,218;320,166;400,226' -MoveMode auto -ClickMode sendinput -ClickHoldMs 300 -ClickRepeat 2 -AllowVisibleRuntime
```

### Right-bottom composition validation-stage manual input

- ID: `right_bottom_validation_input`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- Candidate placeholder: `C:\ClashTests\manual-directinput\<rightbottomcompose-candidate-exe>`
- Candidate path policy: candidate placeholders must resolve to freshly built, hashed executables under C:\ClashTests; never use C:\Clash\clash95.exe or a repository-local executable
- Route: `load-slot0`
- Load-route points: `300,218;320,166;400,226`
- Follow-up manual points: `588,440;450,73;760,560`
- Notes: the command reaches gameplay through the load route; then manually check the recovered lower/right action UI and displayed grid/action positions

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\smoke\run_clash_visual_smoke.ps1' -Exe 'C:\ClashTests\manual-directinput\<rightbottomcompose-candidate-exe>' -WorkDir 'C:\Clash' -Route 'load-slot0' -Points '300,218;320,166;400,226' -MoveMode auto -ClickMode sendinput -ClickHoldMs 300 -ClickRepeat 2 -AllowVisibleRuntime
```

### Castle barracks centered manual input

- ID: `castle_barracks_centered_input`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`
- Candidate placeholder: `C:\ClashTests\manual-directinput\<castlecenter-all-candidate-exe>`
- Candidate path policy: candidate placeholders must resolve to freshly built, hashed executables under C:\ClashTests; never use C:\Clash\clash95.exe or a repository-local executable
- Route: `load-slot0`
- Load-route points: `300,218;320,166;400,226`
- Follow-up manual points: `400,300;231,366;180,440`
- Notes: the command reaches gameplay through the load route; then manually check centered barracks descriptor/action positions

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\smoke\run_clash_visual_smoke.ps1' -Exe 'C:\ClashTests\manual-directinput\<castlecenter-all-candidate-exe>' -WorkDir 'C:\Clash' -Route 'load-slot0' -Points '300,218;320,166;400,226' -MoveMode auto -ClickMode sendinput -ClickHoldMs 300 -ClickRepeat 2 -AllowVisibleRuntime
```

### Full castle overview centered manual input

- ID: `castle_overview_centered_input`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`
- Candidate placeholder: `C:\ClashTests\manual-directinput\<castlecenter-all-candidate-exe>`
- Candidate path policy: candidate placeholders must resolve to freshly built, hashed executables under C:\ClashTests; never use C:\Clash\clash95.exe or a repository-local executable
- Route: `load-slot0`
- Load-route points: `300,218;320,166;400,226`
- Follow-up manual points: `231,366;180,440;503,426`
- Notes: the command reaches gameplay through the load route; then manually check centered castle overview descriptors and callbacks

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\smoke\run_clash_visual_smoke.ps1' -Exe 'C:\ClashTests\manual-directinput\<castlecenter-all-candidate-exe>' -WorkDir 'C:\Clash' -Route 'load-slot0' -Points '300,218;320,166;400,226' -MoveMode auto -ClickMode sendinput -ClickHoldMs 300 -ClickRepeat 2 -AllowVisibleRuntime
```

## Proof Validation

```powershell
python 'tools\manual_directinput_checklist.py' --manual-proof 'captures\current\manual-directinput-proof-current.json' --require-pass --require-promotion-ready
```

## Runtime Prerequisites

- user explicitly approves a visible/manual DirectInput validation pass
- candidate executable path placeholders are replaced with freshly built, hashed candidates
- candidate placeholders must resolve to freshly built, hashed executables under C:\ClashTests; never use C:\Clash\clash95.exe or a repository-local executable
- stale clash95*/cdb processes are killed and recorded before launching a visible runtime
- each manual target captures observed result, screenshot or notes, pass/fail notes, and no-crash status
- captures/current/manual-directinput-proof-current.json is filled from the approved run and validated before promotion
