# Right-Bottom Slot Fixture Result Summary

- Log: `captures\cdb-surface-dump-20260527-121204\cdb-surface-dump.log`
- Status: `castle_route_not_reached`
- Expected slot: `0`
- Selected arg: `0`
- Selected global: `0`
- LOADSAVE slot values: `[0, 0, 0, 0]`
- LOADSAVE slot consistent: `True`
- LOADSAVE slot expected match: `True`
- Expected slot match: `True`
- Rows parsed: `15`
- Access violations: `0`
- Load success: `True`
- Owner loop reached: `False`
- Owner flag test: `{}`
- Owner/action route count: `0`

## Marker Counts

- `SURFDUMP_LOADSAVE`: `2`
- `SURFDUMP_PLAYGAME`: `2`
- `SURFDUMP_READY`: `1`
- `SURFDUMP_HOST_READY`: `1`
- `NOWNER_HEADER`: `1`
- `NOWNER_FORCE_MAP_CASTLE_CLICK`: `1`
- `NOWNER_MAP_TILE`: `7`
- `NOWNER_BUILDING_TILE`: `0`
- `NOWNER_CASTLE_OVERVIEW_ENTRY`: `0`
- `NOWNER_CASTLE_CMD99_GATE`: `0`
- `NOWNER_CASTLE_CALLBACK`: `0`
- `NOWNER_433C20_ENTRY`: `0`
- `NOWNER_OWNER_FLAG_TEST`: `0`
- `NOWNER_OWNER_SCREEN_DESC_DRAW`: `0`
- `NOWNER_OWNER_DESC_RESULT_SURFDUMP_READY`: `0`
- `NOWNER_4338E0_ENTRY`: `0`
- `NOWNER_4338E0_OWNER_FLAG_BLOCKED`: `0`
- `NOWNER_ACTION_CALL_WRAPPER`: `0`
- `NOWNER_OWNER_435BC0_ENTRY`: `0`
- `NOWNER_WRAPPER_COPYBACK_DONE`: `0`
- `AV_SURFDUMP`: `0`

## Classification

- LOADSAVE and PlayGame were reached
- observed load slot matches the expected fixture slot
- castle command-99 owner loop was not fully reached
- owner flag bit 0x02 was not set
- owner/action renderer route markers were not observed

## Key Rows

- line 201: `SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=09520030`
- line 202: `SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=09520030`
- line 203: `SURFDUMP_PLAYGAME gd=09520030 map=(100,100) scroll=(11,17) surface=0820c9a0 size=(640,480)`
- line 204: `SURFDUMP_PLAYGAME gd=09520030 map=(100,100) scroll=(11,17) surface=0820c9a0 size=(640,480)`
- line 205: `NOWNER_HEADER gd=09520030 player=0 scroll=(11,17) surface=0a57f030 size=(800,600) SURFDUMP_REDRAW seq=0 scroll=(11,17) end12=(23,26) map=(100,100) surface=0a57f030 size=(800,600)`
- line 206: `NOWNER_FORCE_MAP_CASTLE_CLICK screen=(352,272) raw=(00005800,00004400)`
- line 206: `NOWNER_MAP_TILE map=(16,21) mouse=(352,272) selected=-1 current=0 NOWNER_REARM_MAP_COMMIT map=(16,21) mouse=(352,272) SURFDUMP_REDRAW seq=1 scroll=(11,17) end12=(23,26) map=(100,100) surface=0a57f030 size=(800,600)`
- line 207: `NOWNER_MAP_TILE map=(16,21) mouse=(352,272) selected=-1 current=0 NOWNER_REARM_MAP_COMMIT map=(16,21) mouse=(352,272) SURFDUMP_REDRAW seq=2 scroll=(11,17) end12=(23,26) map=(100,100) surface=0a57f030 size=(800,600)`
- line 208: `NOWNER_MAP_TILE map=(16,21) mouse=(352,272) selected=-1 current=0 NOWNER_REARM_MAP_COMMIT map=(16,21) mouse=(352,272) SURFDUMP_REDRAW seq=3 scroll=(11,17) end12=(23,26) map=(100,100) surface=0a57f030 size=(800,600)`
- line 209: `SURFDUMP_READY redraw_seq=4 surface=0a57f030 size=(800,600) base=0a820030 bytes=480000`
- line 221: `SURFDUMP_HOST_READY`
- line 222: `NOWNER_MAP_TILE map=(16,21) mouse=(352,272) selected=-1 current=0 NOWNER_REARM_MAP_COMMIT map=(16,21) mouse=(352,272) SURFDUMP_REDRAW seq=4 scroll=(11,17) end12=(23,26) map=(100,100) surface=0a57f030 size=(800,600)`
- line 223: `NOWNER_MAP_TILE map=(16,21) mouse=(352,272) selected=-1 current=0 NOWNER_REARM_MAP_COMMIT map=(16,21) mouse=(352,272) SURFDUMP_REDRAW seq=5 scroll=(11,17) end12=(23,26) map=(100,100) surface=0a57f030 size=(800,600)`
- line 224: `NOWNER_MAP_TILE map=(16,21) mouse=(352,272) selected=-1 current=0 NOWNER_REARM_MAP_COMMIT map=(16,21) mouse=(352,272) SURFDUMP_REDRAW seq=6 scroll=(11,17) end12=(23,26) map=(100,100) surface=0a57f030 size=(800,600)`
- line 225: `NOWNER_MAP_TILE map=(16,21) mouse=(352,272) selected=-1 current=0 NOWNER_REARM_MAP_COMMIT map=(16,21) mouse=(352,272) eax=00511e14 ebx=00511e14 ecx=00000000 edx=00511e14 esi=000001a0 edi=000001e0`
