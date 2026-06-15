# Action Panel Route Summary

- Log: `captures\cdb-surface-dump-20260506-102113\cdb-surface-dump.log`
- Ready: True
- AV rows: 0
- Owner/global rows: 0
- Panel route rows: 0
- Draw rows: 0
- Nonzero owner rows: 0
- PlayGame line: 199
- Ready line: 209

## Classification
- surface dump reached gameplay ready state
- PlayGame setup route rows were observed
- action-panel owner/global route was not reached
- no action-panel poll hit-test or draw rows fired
- right-bottom action/status draw functions did not execute
- dword_532218 stayed zero in observed route rows

## Marker Counts
- APROUTE_PLAYGAME_SETUP_40A400: 1
- APROUTE_PLAYGAME_CALL_40A500: 1
- APROUTE_40A400_ENTRY: 1
- APROUTE_40A500_ENTRY: 1
- APROUTE_40A500_CALL_423B40: 0
- APROUTE_40A500_CALL_423B00: 0
- APROUTE_WRITE_532218: 0
- APROUTE_WRITE_5322C8: 0
- APROUTE_CASTLE_UI_ENTRY: 0
- APROUTE_CASTLE_UI_CALL_435BC0: 0
- APROUTE_OWNER_435BC0_ENTRY: 0
- APROUTE_OWNER_POLL_435B90: 0
- APROUTE_HOVER_435A00_ENTRY: 0
- APROUTE_SCROLLBOX_435AC0_ENTRY: 0
- APROUTE_GRID_HIT_ENTRY: 0
- APROUTE_GRID_HIT_FAIL: 0
- APROUTE_GRID_HIT_OK: 0
- APROUTE_CLICK_DISPATCH_435620: 0
- APROUTE_PANEL_DRAW_4347A0: 0
- APROUTE_GRID_DRAW_434E20: 0
- APROUTE_STATUS_DRAW_435280: 0
- APROUTE_ACTION_BOX_435500: 0
- SURFDUMP_PLAYGAME: 2
- SURFDUMP_REDRAW: 5
- SURFDUMP_READY: 1
- SURFDUMP_HOST_READY: 1
- SURFDUMP_DONE: 0
- AV_SURFDUMP: 0

## First Route Rows
- line 199: SURFDUMP_PLAYGAME gd=04490030 map=(100,100) scroll=(10,17) surface=042fc8e0 size=(640,480)
- line 200: SURFDUMP_PLAYGAME gd=04490030 map=(100,100) scroll=(10,17) surface=042fc8e0 size=(640,480)
- line 201: APROUTE_PLAYGAME_SETUP_40A400 ret=00000000 selected=-1 prior=-1 d532218=00000000 d5322c8=0 mouse=(320,166) scroll=(10,17)
- line 202: APROUTE_40A400_ENTRY ret=0040b7b3 eax=0000004c edx=00000002 ecx=0050edb4 selected=-1 prior=-1 d532218=00000000 d5322c8=0
- line 203: APROUTE_PLAYGAME_CALL_40A500 ret=00000000 selected=-1 prior=-1 d532218=00000000 d5322c8=0 mouse=(320,166) scroll=(10,17)
- line 204: APROUTE_40A500_ENTRY ret=0040b7b8 eax=0050edb4 edx=00000002 ecx=0050edb4 ebp=ffffffff selected=-1 prior=-1 d532218=00000000 d5322c8=0
- line 205: SURFDUMP_REDRAW seq=0 scroll=(10,17) end12=(22,26) map=(100,100) surface=0a57edb0 size=(800,600)
- line 206: SURFDUMP_REDRAW seq=1 scroll=(10,17) end12=(22,26) map=(100,100) surface=0a57edb0 size=(800,600)
- line 207: SURFDUMP_REDRAW seq=2 scroll=(10,17) end12=(22,26) map=(100,100) surface=0a57edb0 size=(800,600)
- line 208: SURFDUMP_REDRAW seq=3 scroll=(10,17) end12=(22,26) map=(100,100) surface=0a57edb0 size=(800,600)
- line 209: SURFDUMP_READY redraw_seq=4 surface=0a57edb0 size=(800,600) base=0a820030 bytes=480000
- line 221: SURFDUMP_HOST_READY
- line 222: SURFDUMP_REDRAW seq=4 scroll=(10,17) end12=(22,26) map=(100,100) surface=0a57edb0 size=(800,600)
