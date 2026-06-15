# Load Slot Timeout Phase

- Status: PASS
- Generated: `2026-06-15T22:14:10+02:00`
- Runtime policy: repo-only; reads archived hidden-desktop CDB logs, summaries, and timeout stacks; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: passes only when slot 2 still proves the full load-menu accept path while slots 3-5 and the current slot-5 right-bottom attempt all stall after early load-menu descriptor rows but before 0044895A load-menu entry, forced select, LOADSAVE, and PlayGame
- Promotion ready: `False`
- Slot 2 phase: `load_menu_accept_success`
- Blocked slots: `[3, 4, 5]`
- Recent slot-5 blocked: `True`
- Next probe target: instrument the transition between the early 00419B80 load descriptors and 0044895A load-menu entry for rows 3-5

## Divergence

slot 2 reaches the 0044895A load-menu entry and accept path; slots 3-5 reach early 00419B80 load-coordinate descriptor rows, then time out before 0044895A load-menu entry, forced select, LOADSAVE, or PlayGame

## Phase Matrix

| Label | Slot | Status | Load coords | Last coord | Last marker | Stack category |
| --- | ---: | --- | ---: | --- | --- | --- |
| slot2_success | 2 | `load_menu_accept_success` | 10 | `{'entry': '0x000efcdd', 'seq': 9, 'choice': 5, 'ex': 409, 'ey': 468, 'mouse_x': 320, 'mouse_y': 210, 'selected': 2, 'accept': 1}` | `SURFDUMP_READY` | `None` |
| slot3_timeout | 3 | `stalled_after_load_button_before_load_menu_loop` | 1 | `{'entry': '0x000efa5d', 'seq': 0, 'choice': 5, 'ex': 232, 'ey': 228, 'mouse_x': 320, 'mouse_y': 232, 'selected': 0, 'accept': 0}` | `SURFDUMP_LOAD_COORD` | `qpc_timing_poll_before_load_menu_loop` |
| slot4_timeout | 4 | `stalled_after_load_button_before_load_menu_loop` | 2 | `{'entry': '0x000efa5d', 'seq': 1, 'choice': 5, 'ex': 232, 'ey': 228, 'mouse_x': 320, 'mouse_y': 254, 'selected': 0, 'accept': 0}` | `SURFDUMP_LOAD_COORD` | `qpc_timing_poll_before_load_menu_loop` |
| slot5_timeout | 5 | `stalled_after_load_button_before_load_menu_loop` | 3 | `{'entry': '0x000efa92', 'seq': 2, 'choice': 5, 'ex': 265, 'ey': 264, 'mouse_x': 320, 'mouse_y': 276, 'selected': 0, 'accept': 0}` | `SURFDUMP_LOAD_COORD` | `win32_message_poll_before_load_menu_loop` |
| recent_slot5_timeout | 5 | `stalled_after_load_button_before_load_menu_loop` | 4 | `{'entry': '0x000efa92', 'seq': 3, 'choice': 5, 'ex': 265, 'ey': 264, 'mouse_x': 320, 'mouse_y': 276, 'selected': 0, 'accept': 0}` | `SURFDUMP_LOAD_COORD` | `engine_timing_poll_before_load_menu_loop` |

![slot2 load route surface](C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\cdb-surface-dump-20260520-202424\surface.png)
