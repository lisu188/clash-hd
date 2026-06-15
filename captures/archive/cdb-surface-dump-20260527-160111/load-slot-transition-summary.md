# Load Slot Transition Summary

- Log: `captures\cdb-surface-dump-20260527-160111\cdb-surface-dump.log`
- Status: `stalled_before_load_menu_entry`
- Expected slot: `5`
- Target slot: `5`
- Target slot values: `[5, 5]`
- Target slot consistent: `True`
- Target slot expected match: `True`
- LOADSAVE slot match: `None`
- PlayGame slot match: `None`
- Expected slot match: `True`
- Rows parsed: `2`
- Access violations: `0`
- Last callback entry: `{'choice_before': 0, 'exit_before': 0, 'target_slot': 5, 'mouse': [300, 218], 'lbtn': 128}`
- Last wait gate: `{'seq': 0, 'choice': 0, 'exit': 0, 'target_slot': 5, 'selected': 0, 'accept': 0, 'mouse': [1, 1], 'lbtn': 0}`
- Last switch dispatch: `None`
- Last late mouse: `None`
- LOADSAVE: `None`
- PlayGame: `None`

## Marker Counts

- `LSTRANS_LOAD_CALLBACK_ENTRY`: `1`
- `LSTRANS_AFTER_MAIN_CALLBACK`: `0`
- `LSTRANS_MAIN_WAIT_GATE`: `1`
- `LSTRANS_MAIN_SWITCH_DISPATCH`: `0`
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
- main Load callback entry was observed
- main Load callback handoff was not observed
- main dispatch wait-gate rows were observed before the case switch
- real 0044895A load-menu entry was not reached

## Key Rows

- line 187: `LSTRANS_MAIN_WAIT_GATE seq=0 choice=0 exit=0 target_slot=5 selected=0 accept=0 mouse=(1,1) lbtn=0x00`
- line 191: `LSTRANS_LOAD_CALLBACK_ENTRY choice_before=0 exit_before=0 target_slot=5 mouse=(300,218) lbtn=0x80`
