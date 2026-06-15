# Load Slot Transition Probe Guard

- Overall: PASS
- Generated: `2026-06-15T20:46:32+02:00`
- Runtime policy: repo-only source inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: the focused transition extra probe must avoid early 00419B80 coordinate forcing, late-arm load-row selection only after 0044895A, keep select/accept conditions parameterized by __LOAD_SLOT__, and the surface-dump harness must replace load-slot placeholders in extra probe templates
- Probe: `probes\cdb\menu\clash95_load_slot_entry_transition_extra.cdb`
- Surface-dump script: `scripts\cdb\run_cdb_surface_dump.ps1`
- Late-entry breakpoint: `0044895A`
- Early descriptor breakpoint avoided: `True`
- Slot conditions parameterized: `True`
- Extra probe placeholders replaced: `True`
- Late load-slot forcing only supported: `True`

## Probe Breakpoints

- `00447780`: `PASS` - main Load callback entry before state write
- `00419C60`: `PASS` - post-main-callback descriptor return state
- `00447BF1`: `PASS` - main dispatch wait gate before case switch
- `00447C0D`: `PASS` - main wait-loop pump call before case switch
- `00447C1E`: `PASS` - main wait-loop compare after descriptor walker
- `00447C26`: `PASS` - main wait-loop exit before case switch
- `00447C3A`: `PASS` - main switch dispatch choice read
- `00447D61`: `PASS` - main dispatch poll before case entry
- `0044895A`: `PASS` - real case-5 load-menu entry
- `0044A140`: `PASS` - load-slot row draw after case entry
- `00448A45`: `PASS` - load-menu loop after entry
- `00448A68`: `PASS` - late force-select inside load-menu loop
- `00448AE3`: `PASS` - late force-accept inside load-menu loop
- `0044A110`: `PASS` - load accept helper
- `00444490`: `PASS` - LOADSAVE after accepted slot
- `0040B660`: `PASS` - PlayGame after LOADSAVE

## Probe Markers

- `LSTRANS_LOAD_CALLBACK_ENTRY`: `PASS` - callback pre-write state row
- `LSTRANS_AFTER_MAIN_CALLBACK`: `PASS` - post callback state row
- `LSTRANS_MAIN_WAIT_GATE`: `PASS` - pre-switch wait-gate row
- `LSTRANS_WAIT_LOOP_PUMP`: `PASS` - pre-switch wait-loop pump row
- `LSTRANS_WAIT_LOOP_COMPARE`: `PASS` - pre-switch wait-loop compare row
- `LSTRANS_WAIT_LOOP_EXIT`: `PASS` - pre-switch wait-loop exit row
- `LSTRANS_MAIN_SWITCH_DISPATCH`: `PASS` - switch-dispatch row before case jump
- `LSTRANS_MAIN_DISPATCH_POLL`: `PASS` - main dispatch polling row
- `LSTRANS_LOAD_MENU_ENTRY`: `PASS` - real load-menu entry row
- `LSTRANS_LATE_MOUSE_SET`: `PASS` - late mouse placement after load-menu entry
- `LSTRANS_LOAD_SLOT_DRAW`: `PASS` - load-slot draw row
- `LSTRANS_LOAD_MENU_LOOP`: `PASS` - load-loop row
- `LSTRANS_LATE_FORCE_SELECT`: `PASS` - late select force row
- `LSTRANS_LATE_FORCE_ACCEPT`: `PASS` - late accept force row
- `LSTRANS_LOAD_ACCEPT_CALL`: `PASS` - load accept helper row
- `LSTRANS_LOADSAVE`: `PASS` - save load row
- `LSTRANS_PLAYGAME`: `PASS` - gameplay transition row

## Slot Conditions

- `00448A68`: `PASS` - late force-select must be target-row parameterized
- `00448AE3`: `PASS` - late force-accept must be target-row parameterized

## Runner Placeholder Replacement

- `$extraProbeText = $extraProbeText.Replace('__LOAD_SLOT__'`: `PASS`
- `$extraProbeText = $extraProbeText.Replace('__LOAD_MOUSE_RAW_X__'`: `PASS`
- `$extraProbeText = $extraProbeText.Replace('__LOAD_MOUSE_RAW_Y__'`: `PASS`

## Late Load-Slot Forcing Support

- `[switch]$LateLoadSlotForcingOnly`: `PASS`
- `__PRE_ENTRY_LOAD_COORD_ACTION__`: `PASS`
- `SURFDUMP_PRE_ENTRY_SLOT_DEFERRED`: `PASS`
