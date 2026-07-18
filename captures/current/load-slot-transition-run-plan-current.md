# Load Slot Transition Run Plan

- Status: PASS
- Generated: `2026-07-18T22:13:54+02:00`
- Runtime policy: repo-only command planner; reads generated JSON and writes JSON/Markdown reports; does not run PowerShell, launch Clash95, CDB, wrappers, or visible windows
- Guard policy: passes only when rows 3-5 remain blocked before 0044895A, the transition probe guard is passing, and every future command stays hidden-desktop and non-promoting
- Promotion ready: `False`
- stable_stage_should_change: `False`
- Target rows: `[3, 4, 5]`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`
- Candidate root: `C:\ClashTests\load-slot-transition`
- Result root template: `captures\cdb-surface-dump-TRANSITION-RUN`
- Late entry breakpoint: `0044895A`

## Commands

### slot3_hidden_transition_probe

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\cdb\run_cdb_surface_dump.ps1' -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -LateLoadSlotForcingOnly -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter' -CandidateDir 'C:\ClashTests\load-slot-transition\slot3' -LoadSlot 3 -ExtraProbeTemplate 'probes\cdb\menu\clash95_load_slot_entry_transition_extra.cdb' -RunSeconds 120
```

### slot4_hidden_transition_probe

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\cdb\run_cdb_surface_dump.ps1' -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -LateLoadSlotForcingOnly -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter' -CandidateDir 'C:\ClashTests\load-slot-transition\slot4' -LoadSlot 4 -ExtraProbeTemplate 'probes\cdb\menu\clash95_load_slot_entry_transition_extra.cdb' -RunSeconds 120
```

### slot5_hidden_transition_probe

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\cdb\run_cdb_surface_dump.ps1' -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -LateLoadSlotForcingOnly -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter' -CandidateDir 'C:\ClashTests\load-slot-transition\slot5' -LoadSlot 5 -ExtraProbeTemplate 'probes\cdb\menu\clash95_load_slot_entry_transition_extra.cdb' -RunSeconds 120
```

## Summary Commands

### slot3_summarize_transition

```powershell
python 'tools\load_slot_transition_summary.py' 'captures\cdb-surface-dump-TRANSITION-RUN\slot3\cdb-surface-dump.log' --expected-slot 3 --write-json 'captures\cdb-surface-dump-TRANSITION-RUN\slot3\load-slot-transition-summary.json' --write-md 'captures\cdb-surface-dump-TRANSITION-RUN\slot3\load-slot-transition-summary.md' --require-entry --require-slot-match
```

### slot4_summarize_transition

```powershell
python 'tools\load_slot_transition_summary.py' 'captures\cdb-surface-dump-TRANSITION-RUN\slot4\cdb-surface-dump.log' --expected-slot 4 --write-json 'captures\cdb-surface-dump-TRANSITION-RUN\slot4\load-slot-transition-summary.json' --write-md 'captures\cdb-surface-dump-TRANSITION-RUN\slot4\load-slot-transition-summary.md' --require-entry --require-slot-match
```

### slot5_summarize_transition

```powershell
python 'tools\load_slot_transition_summary.py' 'captures\cdb-surface-dump-TRANSITION-RUN\slot5\cdb-surface-dump.log' --expected-slot 5 --write-json 'captures\cdb-surface-dump-TRANSITION-RUN\slot5\load-slot-transition-summary.json' --write-md 'captures\cdb-surface-dump-TRANSITION-RUN\slot5\load-slot-transition-summary.md' --require-entry --require-slot-match
```

## Expected Markers

- `LSTRANS_LOAD_CALLBACK_ENTRY`
- `LSTRANS_AFTER_MAIN_CALLBACK`
- `LSTRANS_MAIN_WAIT_GATE`
- `LSTRANS_WAIT_LOOP_PUMP`
- `LSTRANS_WAIT_LOOP_COMPARE`
- `LSTRANS_WAIT_LOOP_EXIT`
- `LSTRANS_MAIN_SWITCH_DISPATCH`
- `LSTRANS_MAIN_DISPATCH_POLL`
- `LSTRANS_LOAD_MENU_ENTRY`
- `LSTRANS_LATE_MOUSE_SET`
- `LSTRANS_LOAD_SLOT_DRAW`
- `LSTRANS_LOAD_MENU_LOOP`

## Result Acceptance

- entry proof: load_slot_transition_summary.py --require-entry --require-slot-match passes for each row with consistent target_slot values
- success proof: if LOADSAVE/PlayGame appear, rerun the same summary with --require-success and require those slot rows to match before treating it as load success
- slot forcing proof: pre-0044895A load-slot coordinate forcing stays disabled; slot selection is armed only at or after the load-menu entry
- promotion remains blocked until natural owner/action proof or approved manual DirectInput proof exists
