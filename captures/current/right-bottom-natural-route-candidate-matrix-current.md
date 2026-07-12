# Right-Bottom Natural Route Candidate Matrix

- Status: PASS
- Generated: `2026-07-12T16:08:34+02:00`
- Runtime policy: repo/local metadata only; reads generated save-scan JSON and existing hidden-desktop CDB artifacts, and does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: passes only when current evidence shows an action-eligible installed save record exists, the archived slot-0 natural route clicks owner record index 0 but is blocked by owner flag 0x00, slot 2 loads yet misses the bit-2 record with the current click, and slot 5 has a route-compatible bit-2 record but the current load harness times out before LOADSAVE
- Promotion ready: `False`
- Save scan: `captures\current\castle-save-owner-flag-scan-current.json`
- Baseline run: `captures\archive\cdb-surface-dump-20260712-150434`
- Slot 2 run: `captures\archive\cdb-surface-dump-20260712-153503`
- Slot 5 run: `captures\archive\cdb-surface-dump-20260712-153529`

## Classification

- Action-eligible owner records: `7`
- Baseline route record index: `0`
- Baseline owner-flag blocker: `True`
- Route-compatible candidate: save slot `5`, record `0`, position `[14, 20]`, flags `0x0B`
- Slot 2 exploratory status: `loads_but_click_misses_castle`
- Slot 2 first map tile: `{'x': 43, 'y': 45, 'mouse_x': 352, 'mouse_y': 272, 'selected': -1, 'current': 0}`
- Slot 2 action record: `{'save': 'C:\\Clash\\save\\2.dat', 'save_slot': 2, 'record_index': 1, 'position': [1, 23], 'owner': 1, 'flags_1a0': 22, 'flags_1a0_hex': '0x16', 'flags_1a4_hex': '0x00', 'bit2': 2, 'bit1': 0, 'bit8': 0, 'action_eligible': True}`
- Slot 5 exploratory status: `timeout_before_loadsave`
- Current blocker: route-compatible save slot 5 has owner flag bit 0x02 at record index 0, but the hidden CDB load-slot route currently times out before LOADSAVE; slot 2 confirms alternate-slot loading works but the current map click misses its bit-2 castle

## Next Proof Options

- fix the hidden CDB load-slot selection path for slot 5 and rerun the natural owner/action probe
- or build an isolated working-directory fixture that maps the slot-5 save state to a route-compatible slot without mutating C:\Clash\save
- or retarget the CDB map click/scroll path to the slot-2 bit-2 castle at record index 1

![slot2 hidden route surface](C:\Users\andrz\git\clash-hd\scripts\cdb\..\..\captures\archive\cdb-surface-dump-20260712-153503\surface.png)
