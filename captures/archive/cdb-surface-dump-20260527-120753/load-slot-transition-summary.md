# Load Slot Transition Summary

- Log: `captures\cdb-surface-dump-20260527-120753\cdb-surface-dump.log`
- Status: `stalled_before_load_menu_entry`
- Expected slot: `5`
- Target slot: `5`
- Target slot values: `[5, 5, 5, 5, 5]`
- Target slot consistent: `True`
- Target slot expected match: `True`
- LOADSAVE slot match: `None`
- PlayGame slot match: `None`
- Expected slot match: `True`
- Rows parsed: `5`
- Access violations: `0`
- Last late mouse: `None`
- LOADSAVE: `None`
- PlayGame: `None`

## Marker Counts

- `LSTRANS_AFTER_MAIN_CALLBACK`: `5`
- `LSTRANS_MAIN_DISPATCH_POLL`: `0`
- `LSTRANS_LOAD_MENU_ENTRY`: `0`
- `LSTRANS_LATE_MOUSE_SET`: `0`
- `LSTRANS_LOAD_SLOT_DRAW`: `0`
- `LSTRANS_LOAD_MENU_LOOP`: `0`
- `LSTRANS_LATE_FORCE_SELECT`: `0`
- `LSTRANS_LATE_FORCE_ACCEPT`: `0`
- `LSTRANS_LOAD_ACCEPT_CALL`: `0`
- `LSTRANS_LOADSAVE`: `0`
- `LSTRANS_PLAYGAME`: `0`

## Classification

- all observed target_slot values match expected slot 5
- main Load callback handoff was observed
- real 0044895A load-menu entry was not reached

## Key Rows

- line 193: `LSTRANS_AFTER_MAIN_CALLBACK desc=0x000efa28 choice=5 exit=1 target_slot=5 mouse=(300,218) lbtn=0x80 flags=0x01`
- line 194: `LSTRANS_AFTER_MAIN_CALLBACK desc=0x000efa28 choice=5 exit=1 target_slot=5 mouse=(300,218) lbtn=0x80 flags=0x01`
- line 195: `LSTRANS_AFTER_MAIN_CALLBACK desc=0x000efa28 choice=5 exit=1 target_slot=5 mouse=(300,218) lbtn=0x80 flags=0x01`
- line 196: `LSTRANS_AFTER_MAIN_CALLBACK desc=0x000efa28 choice=5 exit=1 target_slot=5 mouse=(300,218) lbtn=0x80 flags=0x01`
- line 197: `LSTRANS_AFTER_MAIN_CALLBACK desc=0x000efa28 choice=5 exit=1 target_slot=5 mouse=(300,218) lbtn=0x80 flags=0x01`
