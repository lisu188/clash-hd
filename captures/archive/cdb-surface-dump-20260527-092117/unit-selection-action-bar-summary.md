# Unit Selection Action Bar Summary

- Log: `captures\cdb-surface-dump-20260527-092117\cdb-surface-dump.log`
- Expected load slot: `0`
- Load slot match: `True`
- Ready: `True`
- Pre-redraw dump: `True`
- Selection success: `True`
- 00406980 route: `True`
- Present helper: `True`
- Render present: `True`
- 0040A500 -> 00423B00 update: `True`
- AV rows: `0`

## Classification
- load route used expected slot 0
- first-mission unit selection succeeded
- selected-unit info/action updater 00406980 ran
- 00406980 reached its low-level present/copy helper
- selected-unit action update route reached 0040A500 -> 00423B00
- surface dump was armed before the later map redraw

## Marker Counts
- UNITSEL_ROUTE_START: 1
- UNITSEL_INVOKE_408030_THEN_406980: 1
- UNITSEL_SELECT_ENTRY: 0
- UNITSEL_SELECT_TILE: 1
- UNITSEL_SELECT_SUCCESS: 0
- UNITSEL_SELECT_FAIL: 0
- UNITSEL_WRITE_511B58: 1
- UNITSEL_WRITE_514194: 1
- UNITSEL_406980_ENTRY: 1
- UNITSEL_406980_PRESENT_HELPER: 1
- UNITSEL_406980_RENDER_PRESENT: 1
- UNITSEL_406980_RETURN_DUMP: 1
- UNITSEL_40A490_ENTRY: 1
- UNITSEL_40A500_ENTRY: 1
- UNITSEL_40A500_CALL_423B00: 1
- UNITSEL_423B00_ENTRY: 3
- SURFDUMP_LOADSAVE: 1
- SURFDUMP_PLAYGAME: 1
- SURFDUMP_REDRAW: 3
- SURFDUMP_READY: 1
- SURFDUMP_HOST_READY: 1
- AV_SURFDUMP: 0

## First Rows
- line 203: SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=04340030
- line 204: SURFDUMP_PLAYGAME gd=04340030 map=(100,100) scroll=(10,17) surface=038dc940 size=(640,480)
- line 205: UNITSEL_ROUTE_START gd=04340030 player=0 scroll=(10,17) map=(100,100) selected=-1 prior=-1 shift=6 surface=0a05ee10 size=(800,600)
- line 206: UNITSEL_INVOKE_408030_THEN_406980 screen=(448,176) raw=(0x00007000,0x00002c00) select_return=00406980 update_return=0040b0c3
- line 207: UNITSEL_SELECT_TILE map=(16,19) tile=3 selected_before=-1 current=0
- line 208: UNITSEL_WRITE_511B58 eip=00408131 ret=00544cd8 new=3 prior=-1 mouse=(448,176)
- line 209: UNITSEL_406980_ENTRY ret=0040b0c3 selected=3 prior=-1 d526994=0 render=0a05ee10 map_surface=0a05ee10 sz=(800,600)
- line 210: UNITSEL_40A490_ENTRY ret=0040698c selected=3 prior=-1 current=0 d526994=0
- line 211: UNITSEL_40A500_ENTRY ret=0040a4f2 eax=00000010 edx=000001b3 ecx=04340030 ebp=00000000 selected=3 prior=-1 d526994=0
- line 212: UNITSEL_40A500_CALL_423B00 ret=00000003 selected=3 prior=-1 d526994=0
- line 213: UNITSEL_423B00_ENTRY ret=0040a5f3 eax=00000008 edx=0000087f ecx=04340030 ebp=00000000 selected=3 prior=-1 d526994=0
- line 214: UNITSEL_423B00_ENTRY ret=0040a5f3 eax=00000008 edx=0000087f ecx=04340030 ebp=00000000 selected=3 prior=-1 d526994=0
- line 215: UNITSEL_423B00_ENTRY ret=0040a5f3 eax=00000008 edx=0000087f ecx=04340030 ebp=00000000 selected=3 prior=-1 d526994=0
- line 216: UNITSEL_406980_PRESENT_HELPER ret=00000063 src=0a62a440 dst=00000000 src_ltrb=(0,0,8,363) dxy=(468,1) selected=3 prior=3 render=0a62a440 map_surface=0a05ee10
- line 217: UNITSEL_406980_RENDER_PRESENT ret=00000001 eax=00ebfde0 selected=3 prior=3 render=0a62a440 map_surface=0a05ee10 sz=(800,600)
- line 218: UNITSEL_406980_RETURN_DUMP selected=3 prior=3 d526994=1 surface=0a05ee10 size=(800,600) base=0a5a0030 bytes=480000
- line 219: SURFDUMP_READY redraw_seq=900 surface=0a05ee10 size=(800,600) base=0a5a0030 bytes=480000
- line 220: SURFDUMP_HOST_READY
- line 221: Some commands were skipped because previous commands caused target execution inside an event handler.SURFDUMP_REDRAW seq=0 scroll=(10,17) end12=(22,26) map=(100,100) surface=0a05ee10 size=(800,600)
- line 222: UNITSEL_WRITE_514194 eip=004237c1 ret=00000000 selected=3 new_prior=3 d526994=1
- line 223: SURFDUMP_REDRAW seq=1 scroll=(10,17) end12=(22,26) map=(100,100) surface=0a05ee10 size=(800,600)
- line 224: SURFDUMP_REDRAW seq=2 scroll=(10,17) end12=(22,26) map=(100,100) surface=0a05ee10 size=(800,600)
