# Manual DirectInput Run Plan

- Overall: PASS
- Generated: `2026-07-18T21:36:40+02:00`
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
- Follow-up pulse aim points: `castle-entry:470,397;castle-0x63:231,366;barracks-0x86:398,228`
- Input mode: `pulse` / `pulse-relative-engine-aim`
- Aim tolerance px: `10`
- Intro verify rounds: `12`
- Safe window origin: `[0, -30]`
- Notes: BARRACKS COORDINATE RESOLVED (2026-07-18): the live slot-0 castle DOES present command 0x86 (21906 hitmap pixels, native bbox [175,47,455,223]). The earlier 'no known coordinate / different castle layout' claim was a misdiagnosis: the committed hitmap is the live save's own castle (owner record 0, 'Drakefly', map pos 14,20 - 'Stormus' is an exe-resident scenario default name, not this record), and the 2026-07-12 miss happened because that session never loaded the save at all (SetCursorPos moved only the OS cursor, never the DirectInput accumulator - the bug fixed in 589f5700), so a default scenario with a different castle was on screen. Displayed (371,107) is evidence-backed twice on hidden slot-0 runs (cdb-surface-dump-20260712-144245 multihit and -144151 hitbox: raw 0xF8 -> command 0x86 -> callback 0044FE70, gate 1) but sits on the bbox top edge with ~1px clearance (75/289 of a +/-8px box). This command therefore aims (398,228) = native (318,168), the same region's interior with ~37px clearance (289/289 of a +/-8px box), derived statically from the committed hitmap raw and NOT yet live hit-tested - if it misses, fall back to the proven (371,107). The remaining work for this target is executing the 0044FE70 callback (hidden probes deliberately suppress it), not discovering a coordinate

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\smoke\run_clash_visual_smoke.ps1' -Exe 'C:\ClashTests\manual-directinput\<castlecenter-all-candidate-exe>' -WorkDir 'C:\Clash' -Route 'load-slot0' -Points '300,218;320,166;400,226' -InputMode pulse -PulseRouteSteps 'load-button:302,211;load-slot0:320,166;confirm-load:400,226' -FollowupPoints 'castle-entry:470,397;castle-0x63:231,366;barracks-0x86:398,228' -PulseAimTolerancePx 10 -IntroMaxRounds 12 -MoveMode auto -ClickMode sendinput -ClickHoldMs 300 -ClickRepeat 2 -MoveWindowX 0 -MoveWindowY -30 -AllowVisibleRuntime
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
- castle_barracks_centered_input aims the resolved barracks descriptor 0x86 at displayed (398,228); the 2026-07-12 miss at (371,107) is explained (that session never loaded the save - SetCursorPos never moved the DirectInput accumulator, fixed in 589f5700), and (371,107) itself is the evidence-backed fallback. Record this target as passing only if the run's own frames show the barracks build sub-screen actually entered (the 0044FE70 callback executing), not merely a click at the coordinate
- right_bottom_validation_input needs the slot5-as-slot0 right-bottom fixture staged (scripts/smoke/prepare_right_bottom_slot_fixture.ps1) so owner/action descriptors exist to hit
