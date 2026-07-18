# Manual DirectInput Run Plan

- Overall: PASS
- Generated: `2026-07-18T09:43:16+02:00`
- Runtime policy: repo-only command planner; reads generated JSON and writes JSON/Markdown reports; does not run PowerShell, launch Clash95, CDB, wrappers, move the mouse, or open visible windows
- Guard policy: manual DirectInput commands remain templates until explicit user approval; every visible runtime command must carry -AllowVisibleRuntime and the proof manifest must be validated before promotion; the visible harness window must use the safe desktop offset so lower/right 800x600 client targets are not cursor-clamped
- Engine input policy: the game reads mouse position from the DirectInput accumulator, not the OS cursor, so SetCursorPos/absolute-SendInput moves are invisible to its hit test; every menu, map, and follow-up click in this plan is driven by pulse-mode relative injection through tools/menu_pulse_click.py with frame-diff engine-cursor feedback and per-point aim error
- Input mode: `pulse` (mechanism `pulse-relative-engine-aim`, tool `tools\menu_pulse_click.py`)
- DirectInput-invisible move modes (never sufficient alone): `setcursor, sendinput-absolute, auto`
- Candidate path policy: candidate placeholders must resolve to freshly built, hashed executables under C:\ClashTests; never use C:\Clash\clash95.exe or a repository-local executable
- Candidate root: `C:\ClashTests`
- Visible runtime requires approval: `True`
- Proof ready: `False`
- Manual target count: `5`
- All commands have -AllowVisibleRuntime: `True`
- All commands use safe window offset (0,-30): `True`
- All commands use the engine-visible pulse input mode: `True`
- Manual proof valid: `False`
- Promotion ready: `False`

## Commands

### Stable HD map stage menu load and held-click route

- ID: `stable_menu_load`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate placeholder: `C:\ClashTests\manual-directinput\<stable-hd-map-candidate-exe>`
- Candidate path policy: candidate placeholders must resolve to freshly built, hashed executables under C:\ClashTests; never use C:\Clash\clash95.exe or a repository-local executable
- Route: `load-slot0`
- Load-route points (legacy record): `300,218;320,166;400,226`
- Pulse engine-aim route steps: `load-button:302,211;load-slot0:320,166;confirm-load:400,226`
- Follow-up pulse aim points: `n/a`
- Input mode: `pulse` / `pulse-relative-engine-aim`
- Aim tolerance px: `10`
- Intro verify rounds: `12`
- Safe window origin: `[0, -30]`
- Notes: proves the centered menu load route and held-click cadence against the engine's DirectInput accumulator; the harness gates on a verified menu fingerprint, an engine-cursor liveness probe, and per-step aim error plus frame transition

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\smoke\run_clash_visual_smoke.ps1' -Exe 'C:\ClashTests\manual-directinput\<stable-hd-map-candidate-exe>' -WorkDir 'C:\Clash' -Route 'load-slot0' -Points '300,218;320,166;400,226' -InputMode pulse -PulseRouteSteps 'load-button:302,211;load-slot0:320,166;confirm-load:400,226' -PulseAimTolerancePx 10 -IntroMaxRounds 12 -MoveMode auto -ClickMode sendinput -ClickHoldMs 300 -ClickRepeat 2 -MoveWindowX 0 -MoveWindowY -30 -AllowVisibleRuntime
```

### Stable HD map edge scroll, minimap, and selection input

- ID: `stable_hd_map_input`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate placeholder: `C:\ClashTests\manual-directinput\<stable-hd-map-candidate-exe>`
- Candidate path policy: candidate placeholders must resolve to freshly built, hashed executables under C:\ClashTests; never use C:\Clash\clash95.exe or a repository-local executable
- Route: `load-slot0`
- Load-route points (legacy record): `300,218;320,166;400,226`
- Pulse engine-aim route steps: `load-button:302,211;load-slot0:320,166;confirm-load:400,226`
- Follow-up pulse aim points: `map-center:400,300;map-right-edge:780,300;map-bottom:400,580;minimap-right-bottom:760,560`
- Input mode: `pulse` / `pulse-relative-engine-aim`
- Aim tolerance px: `10`
- Intro verify rounds: `12`
- Safe window origin: `[0, -30]`
- Notes: the command reaches gameplay through the pulse load route, then aims and clicks each map edge/minimap/selection point with engine-cursor feedback; per-point aim error and frame delta are recorded, and edge-scroll behaviour still needs a human read of the frames

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\smoke\run_clash_visual_smoke.ps1' -Exe 'C:\ClashTests\manual-directinput\<stable-hd-map-candidate-exe>' -WorkDir 'C:\Clash' -Route 'load-slot0' -Points '300,218;320,166;400,226' -InputMode pulse -PulseRouteSteps 'load-button:302,211;load-slot0:320,166;confirm-load:400,226' -FollowupPoints 'map-center:400,300;map-right-edge:780,300;map-bottom:400,580;minimap-right-bottom:760,560' -PulseAimTolerancePx 10 -IntroMaxRounds 12 -MoveMode auto -ClickMode sendinput -ClickHoldMs 300 -ClickRepeat 2 -MoveWindowX 0 -MoveWindowY -30 -AllowVisibleRuntime
```

### Right-bottom composition validation-stage manual input

- ID: `right_bottom_validation_input`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- Candidate placeholder: `C:\ClashTests\manual-directinput\<rightbottomcompose-candidate-exe>`
- Candidate path policy: candidate placeholders must resolve to freshly built, hashed executables under C:\ClashTests; never use C:\Clash\clash95.exe or a repository-local executable
- Route: `load-slot0`
- Load-route points (legacy record): `300,218;320,166;400,226`
- Pulse engine-aim route steps: `load-button:302,211;load-slot0:320,166;confirm-load:400,226`
- Follow-up pulse aim points: `action-ui:588,440;grid-hit:450,73;minimap-right-bottom:760,560`
- Input mode: `pulse` / `pulse-relative-engine-aim`
- Aim tolerance px: `10`
- Intro verify rounds: `12`
- Safe window origin: `[0, -30]`
- Notes: the command reaches gameplay through the pulse load route, then aims the recovered lower/right action UI and the controlled native (450,73) grid-hit position; needs the slot5-as-slot0 right-bottom fixture staged so the owner/action descriptors exist

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\smoke\run_clash_visual_smoke.ps1' -Exe 'C:\ClashTests\manual-directinput\<rightbottomcompose-candidate-exe>' -WorkDir 'C:\Clash' -Route 'load-slot0' -Points '300,218;320,166;400,226' -InputMode pulse -PulseRouteSteps 'load-button:302,211;load-slot0:320,166;confirm-load:400,226' -FollowupPoints 'action-ui:588,440;grid-hit:450,73;minimap-right-bottom:760,560' -PulseAimTolerancePx 10 -IntroMaxRounds 12 -MoveMode auto -ClickMode sendinput -ClickHoldMs 300 -ClickRepeat 2 -MoveWindowX 0 -MoveWindowY -30 -AllowVisibleRuntime
```

### Castle barracks centered manual input

- ID: `castle_barracks_centered_input`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`
- Candidate placeholder: `C:\ClashTests\manual-directinput\<castlecenter-all-candidate-exe>`
- Candidate path policy: candidate placeholders must resolve to freshly built, hashed executables under C:\ClashTests; never use C:\Clash\clash95.exe or a repository-local executable
- Route: `load-slot0`
- Load-route points (legacy record): `300,218;320,166;400,226`
- Pulse engine-aim route steps: `load-button:302,211;load-slot0:320,166;confirm-load:400,226`
- Follow-up pulse aim points: `castle-entry:470,397;castle-0x63:231,366;owner-action:180,440`
- Input mode: `pulse` / `pulse-relative-engine-aim`
- Aim tolerance px: `10`
- Intro verify rounds: `12`
- Safe window origin: `[0, -30]`
- Notes: OPEN COORDINATE GAP: no barracks-entry coordinate is known for the slot-0 'Stormus' castle. The surfdump-catalog command-0x86 descriptor point (371,107) was clicked coordinate-perfectly on 2026-07-12 and hit a wall with the frame unchanged, because the Stormus keep presents a different building layout (4 of 8 catalog descriptors absent, shifted bboxes). This command reaches the castle overview only; the barracks build sub-screen cannot be entered until a real barracks coordinate is discovered, so this target must not be recorded as passing from this command alone

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\smoke\run_clash_visual_smoke.ps1' -Exe 'C:\ClashTests\manual-directinput\<castlecenter-all-candidate-exe>' -WorkDir 'C:\Clash' -Route 'load-slot0' -Points '300,218;320,166;400,226' -InputMode pulse -PulseRouteSteps 'load-button:302,211;load-slot0:320,166;confirm-load:400,226' -FollowupPoints 'castle-entry:470,397;castle-0x63:231,366;owner-action:180,440' -PulseAimTolerancePx 10 -IntroMaxRounds 12 -MoveMode auto -ClickMode sendinput -ClickHoldMs 300 -ClickRepeat 2 -MoveWindowX 0 -MoveWindowY -30 -AllowVisibleRuntime
```

### Full castle overview centered manual input

- ID: `castle_overview_centered_input`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`
- Candidate placeholder: `C:\ClashTests\manual-directinput\<castlecenter-all-candidate-exe>`
- Candidate path policy: candidate placeholders must resolve to freshly built, hashed executables under C:\ClashTests; never use C:\Clash\clash95.exe or a repository-local executable
- Route: `load-slot0`
- Load-route points (legacy record): `300,218;320,166;400,226`
- Pulse engine-aim route steps: `load-button:302,211;load-slot0:320,166;confirm-load:400,226`
- Follow-up pulse aim points: `castle-entry:470,397;castle-0x63:231,366;owner-action:180,440;overview-0x87:503,426`
- Input mode: `pulse` / `pulse-relative-engine-aim`
- Aim tolerance px: `10`
- Intro verify rounds: `12`
- Safe window origin: `[0, -30]`
- Notes: the command reaches gameplay through the pulse load route, enters the castle overview at the documented real-runtime (470,397) click, then aims the centered overview descriptors; 231,366 is the 0x63 displayed coordinate that a fixture run already recorded as sampling 0x0c rather than the descriptor, and 503,426 has no hitmap evidence behind it, so both need frame confirmation before being reported as hits

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\smoke\run_clash_visual_smoke.ps1' -Exe 'C:\ClashTests\manual-directinput\<castlecenter-all-candidate-exe>' -WorkDir 'C:\Clash' -Route 'load-slot0' -Points '300,218;320,166;400,226' -InputMode pulse -PulseRouteSteps 'load-button:302,211;load-slot0:320,166;confirm-load:400,226' -FollowupPoints 'castle-entry:470,397;castle-0x63:231,366;owner-action:180,440;overview-0x87:503,426' -PulseAimTolerancePx 10 -IntroMaxRounds 12 -MoveMode auto -ClickMode sendinput -ClickHoldMs 300 -ClickRepeat 2 -MoveWindowX 0 -MoveWindowY -30 -AllowVisibleRuntime
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
- the harness uses -MoveWindowX 0 -MoveWindowY -30 so the measured (3,26) non-client offset still leaves 800x600 lower/right client points inside the active desktop instead of cursor-clamping them
- each manual target captures observed result, screenshot or notes, pass/fail notes, and no-crash status
- captures/current/manual-directinput-proof-current.json is filled from the approved run and validated before promotion
- -InputMode pulse is used for every target: the engine reads the DirectInput accumulator, so setcursor/absolute moves never reach its hit test and any run without the pulse lane proves nothing about clicks
- each run reports IntroMenuVerified and CursorProbeAlive before trusting a route; a run that never verified the menu fingerprint or never woke the engine cursor is a failed run, not a failed build
- the pulse lane is automated-but-real OS SendInput; evidence_class stays manual_directinput only if the operator genuinely witnessed the run, and the harness-side proof class stays automated_visible_runtime_engine_aim_evidence
- castle targets need the documented real-runtime castle-entry click (470,397) before any overview descriptor point is reachable; the load route only reaches the map
- castle_barracks_centered_input has an OPEN coordinate gap: no barracks-entry coordinate is known for the slot-0 'Stormus' castle (the catalog 0x86 point 371,107 hit a wall on 2026-07-12), so it cannot honestly be recorded as passing from these commands
- right_bottom_validation_input needs the slot5-as-slot0 right-bottom fixture staged (scripts/smoke/prepare_right_bottom_slot_fixture.ps1) so owner/action descriptors exist to hit
