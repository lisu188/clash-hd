# Load Slot Transition Summary

- Log: `captures\cdb-surface-dump-20260527-163809\cdb-surface-dump.log`
- Status: `late_entry_load_success`
- Expected slot: `5`
- Target slot: `5`
- Target slot values: `[5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]`
- Target slot consistent: `True`
- Target slot expected match: `True`
- LOADSAVE slot match: `True`
- PlayGame slot match: `True`
- Expected slot match: `True`
- Rows parsed: `46`
- Access violations: `0`
- Last callback entry: `{'choice_before': 0, 'exit_before': 0, 'target_slot': 5, 'mouse': [300, 218], 'lbtn': 128}`
- Last wait gate: `{'seq': 0, 'choice': 0, 'exit': 0, 'target_slot': 5, 'selected': 0, 'accept': 0, 'mouse': [1, 1], 'lbtn': 0}`
- Last wait-loop pump: `{'seq': 0, 'choice': 0, 'exit': 0, 'target_slot': 5, 'ecx_before': 0, 'mouse': [1, 1], 'lbtn': 0}`
- Last wait-loop compare: `{'seq': 2, 'choice': 5, 'exit': 1, 'target_slot': 5, 'ecx_after': 0, 'will_loop': 0, 'mouse': [300, 218], 'lbtn': 128}`
- Last wait-loop exit: `{'seq': 3, 'choice': 5, 'exit': 1, 'target_slot': 5, 'ecx': 0, 'selected': 0, 'accept': 0}`
- Last switch dispatch: `{'seq': 2, 'choice': 5, 'exit': 1, 'case_index': 4, 'target_slot': 5, 'selected': 0, 'accept': 0}`
- Last late mouse: `{'target_slot': 5, 'mouse': [320, 276], 'raw': [20480, 17664], 'lbtn': 128}`
- LOADSAVE: `{'selected_arg': 5, 'selected_global': 5, 'accept': 1, 'choice': 5, 'gd': 70516784, 'target_slot': 5}`
- PlayGame: `{'gd': 70516784, 'map': [100, 100], 'scroll': [11, 17], 'surface': 70502720, 'size': [640, 480]}`

## Marker Counts

- `LSTRANS_LOAD_CALLBACK_ENTRY`: `1`
- `LSTRANS_AFTER_MAIN_CALLBACK`: `2`
- `LSTRANS_MAIN_WAIT_GATE`: `1`
- `LSTRANS_WAIT_LOOP_PUMP`: `1`
- `LSTRANS_WAIT_LOOP_COMPARE`: `2`
- `LSTRANS_WAIT_LOOP_EXIT`: `1`
- `LSTRANS_MAIN_SWITCH_DISPATCH`: `2`
- `LSTRANS_MAIN_DISPATCH_POLL`: `0`
- `LSTRANS_LOAD_MENU_ENTRY`: `2`
- `LSTRANS_LATE_MOUSE_SET`: `2`
- `LSTRANS_LOAD_SLOT_DRAW`: `23`
- `LSTRANS_LOAD_MENU_LOOP`: `1`
- `LSTRANS_LATE_FORCE_SELECT`: `2`
- `LSTRANS_LATE_FORCE_ACCEPT`: `2`
- `LSTRANS_LOAD_ACCEPT_CALL`: `1`
- `LSTRANS_LOADSAVE`: `2`
- `LSTRANS_PLAYGAME`: `1`

## Classification

- all observed target_slot values match expected slot 5
- main Load callback entry was observed
- main Load callback handoff was observed
- main dispatch wait-gate rows were observed before the case switch
- main dispatch wait-loop pump rows were observed before the case switch
- main dispatch wait-loop compare was ready to fall through toward the case switch
- main dispatch wait-loop exit rows were observed before the case switch
- main switch-dispatch rows were observed before the load-menu entry
- real 0044895A load-menu entry was reached
- late mouse placement after load-menu entry was observed
- load-slot row drawing was observed
- late force-select row was observed
- late force-accept row was observed
- load accept helper was reached
- LOADSAVE was reached
- PlayGame was reached

## Key Rows

- line 228: `LSTRANS_LOAD_SLOT_DRAW seq=14 slot=7 selected=-1 accept=0 target_slot=5 mouse=(320,276) lbtn=0x80`
- line 229: `LSTRANS_LOAD_SLOT_DRAW seq=15 slot=8 selected=-1 accept=0 target_slot=5 mouse=(320,276) lbtn=0x80`
- line 230: `LSTRANS_LOAD_SLOT_DRAW seq=16 slot=8 selected=-1 accept=0 target_slot=5 mouse=(320,276) lbtn=0x80`
- line 231: `LSTRANS_LOAD_SLOT_DRAW seq=17 slot=9 selected=-1 accept=0 target_slot=5 mouse=(320,276) lbtn=0x80`
- line 232: `LSTRANS_LOAD_SLOT_DRAW seq=18 slot=9 selected=-1 accept=0 target_slot=5 mouse=(320,276) lbtn=0x80`
- line 233: `LSTRANS_LOAD_SLOT_DRAW seq=19 slot=9 selected=-1 accept=0 target_slot=5 mouse=(320,276) lbtn=0x80`
- line 234: `LSTRANS_LOAD_SLOT_DRAW seq=20 slot=9 selected=-1 accept=0 target_slot=5 mouse=(320,276) lbtn=0x80`
- line 235: `LSTRANS_LOAD_SLOT_DRAW seq=21 slot=9 selected=-1 accept=0 target_slot=5 mouse=(320,276) lbtn=0x80`
- line 236: `LSTRANS_LOAD_MENU_LOOP exit=0 selected=-1 accept=0 target_slot=5 mouse=(320,276) lbtn=0x80`
- line 237: `LSTRANS_LATE_FORCE_SELECT target_slot=5 mouse=(320,276) selected=-1 accept=0`
- line 238: `LSTRANS_LATE_FORCE_SELECT target_slot=5 mouse=(320,276) selected=-1 accept=0`
- line 239: `LSTRANS_LOAD_SLOT_DRAW seq=22 slot=5 selected=5 accept=0 target_slot=5 mouse=(320,276) lbtn=0x80`
- line 240: `LSTRANS_LATE_FORCE_ACCEPT target_slot=5 selected=5 accept=0 mouse=(320,276)`
- line 241: `LSTRANS_LATE_FORCE_ACCEPT target_slot=5 selected=5 accept=0 mouse=(320,276)`
- line 242: `LSTRANS_LOAD_ACCEPT_CALL arg=0 selected=5 accept_before=0 target_slot=5 mouse=(320,276)`
- line 248: `LSTRANS_LOADSAVE selected_arg=5 selected_global=5 accept=1 choice=5 gd=04340030 target_slot=5`
- line 249: `LSTRANS_LOADSAVE selected_arg=5 selected_global=5 accept=1 choice=5 gd=04340030 target_slot=5`
- line 250: `SURFDUMP_PLAYGAME gd=04340030 map=(100,100) scroll=(11,17) surface=0433c940 size=(640,480)`
