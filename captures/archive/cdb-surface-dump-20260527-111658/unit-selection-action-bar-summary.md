# Unit Selection Action Bar Summary

- Log: `captures\cdb-surface-dump-20260527-111658\cdb-surface-dump.log`
- Expected load slot: `0`
- Load slot match: `True`
- Ready: `True`
- Pre-redraw dump: `False`
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
- surface dump happened after the normal redraw cadence

## Marker Counts
- UNITSEL_ROUTE_START: 1
- UNITSEL_INVOKE_408030_THEN_406980: 1
- UNITSEL_SELECT_ENTRY: 0
- UNITSEL_SELECT_TILE: 1
- UNITSEL_SELECT_SUCCESS: 0
- UNITSEL_SELECT_FAIL: 0
- UNITSEL_WRITE_511B58: 1
- UNITSEL_WRITE_514194: 0
- UNITSEL_406980_ENTRY: 1
- UNITSEL_406980_PRESENT_HELPER: 1
- UNITSEL_406980_RENDER_PRESENT: 1
- UNITSEL_406980_RETURN_DUMP: 0
- UNITSEL_40A490_ENTRY: 1
- UNITSEL_40A500_ENTRY: 1
- UNITSEL_40A500_CALL_423B00: 1
- UNITSEL_423B00_ENTRY: 1
- SURFDUMP_LOADSAVE: 1
- SURFDUMP_PLAYGAME: 1
- SURFDUMP_REDRAW: 5
- SURFDUMP_READY: 1
- SURFDUMP_HOST_READY: 1
- AV_SURFDUMP: 0

## First Rows
- line 201: SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=04340030
- line 202: SURFDUMP_PLAYGAME gd=04340030 map=(100,100) scroll=(10,17) surface=0433c920 size=(640,480)
- line 221: UNITSEL_ROUTE_START gd=04340030 player=0 scroll=(10,17) map=(100,100) selected=-1 prior=-1 shift=6 surface=0a43ee10 size=(800,600)
- line 222: UNITSEL_INVOKE_408030_THEN_406980 screen=(448,176) raw=(0x00007000,0x00002c00) select_return=00406980 update_return=0040b0c3
- line 223: UNITSEL_SELECT_TILE map=(16,19) tile=3 selected_before=-1 current=0
- line 224: UNITSEL_WRITE_511B58 eip=00408131 ret=00544cd8 new=3 prior=-1 mouse=(448,176)
- line 225: UNITSEL_406980_ENTRY ret=0040b0c3 selected=3 prior=-1 d526994=0 render=0a43ee10 map_surface=0a43ee10 sz=(800,600)
- line 226: UNITSEL_40A490_ENTRY ret=0040698c selected=3 prior=-1 current=0 d526994=0
- line 227: UNITSEL_40A500_ENTRY ret=0040a4f2 eax=00000010 edx=000001b3 ecx=04340030 ebp=00000000 selected=3 prior=-1 d526994=0
- line 228: UNITSEL_40A500_CALL_423B00 ret=00000003 selected=3 prior=-1 d526994=0
- line 229: UNITSEL_423B00_ENTRY ret=0040a5f3 eax=00000008 edx=0000087f ecx=04340030 ebp=00000000 selected=3 prior=-1 d526994=0
- line 236: UNITSEL_406980_PRESENT_HELPER ret=00000063 src=03a6e9e0 dst=00000000 src_ltrb=(0,0,8,363) dxy=(468,1) selected=3 prior=3 render=03a6e9e0 map_surface=0a43ee10
- line 237: UNITSEL_406980_RENDER_PRESENT ret=00000001 eax=00ebfdd0 selected=3 prior=3 render=03a6e9e0 map_surface=0a43ee10 sz=(800,600)
- line 241: SURFDUMP_REDRAW seq=0 scroll=(10,17) end12=(22,26) map=(100,100) surface=0a43ee10 size=(800,600)
- line 242: SURFDUMP_REDRAW seq=1 scroll=(10,17) end12=(22,26) map=(100,100) surface=0a43ee10 size=(800,600)
- line 258: SURFDUMP_REDRAW seq=2 scroll=(10,17) end12=(22,26) map=(100,100) surface=0a43ee10 size=(800,600)
- line 266: SURFDUMP_REDRAW seq=2 scroll=(10,17) end12=(22,26) map=(100,100) surface=0a43ee10 size=(800,600)
- line 282: SURFDUMP_REDRAW seq=3 scroll=(0,51) end12=(12,60) map=(100,100) surface=0a43ee10 size=(800,600)
- line 283: SURFDUMP_READY redraw_seq=4 surface=0a43ee10 size=(800,600) base=0a820030 bytes=480000
- line 295: SURFDUMP_HOST_READY
