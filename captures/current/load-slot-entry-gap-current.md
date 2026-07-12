# Load Slot Entry Gap

- Status: PASS
- Generated: `2026-07-12T19:42:51+02:00`
- Runtime policy: repo-only; reads decompilation text, CDB probe text, and generated timeout phase JSON; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: passes only when static code still places the real load-row loop after the main Load callback, the current probe spans both sides of that transition, slot 2 reaches the post-entry accept path, and slots 3-5 still stop before 0044895A load-menu entry
- Promotion ready: `False`
- Gap classification: `after_main_load_callback_before_load_menu_case_entry`
- Slot 2 post-entry success: `True`
- Blocked rows: `[3, 4, 5]`
- Recent slot-5 same gap: `True`

## Current Gap

Rows 3-5 are stopped in the transition after the forced main Load callback and before 0044895A load-menu entry. They are not yet evidence of invalid save rows because 0044A110/sub_444750, LOADSAVE, and PlayGame are never reached.

## Static And Probe Coverage

- Static decomp markers: `PASS`
- CDB probe markers: `PASS`
- Timeout phase report: `PASS`

## Blocked Rows

| Label | Slot | Status | Load coords | Last marker | Stack category |
| --- | ---: | --- | ---: | --- | --- |
| slot3_timeout | 3 | `stalled_after_load_button_before_load_menu_loop` | 1 | `SURFDUMP_LOAD_COORD` | `qpc_timing_poll_before_load_menu_loop` |
| slot4_timeout | 4 | `stalled_after_load_button_before_load_menu_loop` | 1 | `SURFDUMP_LOAD_COORD` | `avi_or_audio_worker_present` |
| slot5_timeout | 5 | `stalled_after_load_button_before_load_menu_loop` | 3 | `SURFDUMP_LOAD_COORD` | `avi_or_audio_worker_present` |
| recent_slot5_timeout | 5 | `stalled_after_load_button_before_load_menu_loop` | 2 | `SURFDUMP_LOAD_COORD` | `qpc_timing_poll_before_load_menu_loop` |

## Next Probe Targets

- add a CDB transition row between 00447780 and 0044895A to prove when case 5 is dispatched
- late-arm row forcing only after 0044895A instead of relying on early 00419B80 descriptor hits
- log dword_543D7C and dword_543D78 immediately before and after the main dispatch consumes the load callback

## Non-Promoting Route Option

use an isolated slot fixture or direct-loader probe only if it is labeled non-natural route evidence until the menu transition is proven

![slot2 load route surface](C:\Users\andrz\git\clash-hd\scripts\cdb\..\..\captures\archive\cdb-surface-dump-20260712-153805\surface.png)
