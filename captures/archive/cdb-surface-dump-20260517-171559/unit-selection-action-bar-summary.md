# Unit Selection Action Bar Summary

- Log: `captures\cdb-surface-dump-20260517-171559\cdb-surface-dump.log`
- Expected load slot: `0`
- Load slot match: `True`
- Ready: `True`
- Pre-redraw dump: `False`
- Selection success: `True`
- 00406980 route: `True`
- Present helper: `False`
- Render present: `False`
- 0040A500 -> 00423B00 update: `True`
- AV rows: `0`

## Classification
- load route used expected slot 0
- first-mission unit selection succeeded
- selected-unit info/action updater 00406980 ran
- selected-unit action update route reached 0040A500 -> 00423B00
- surface dump happened after the normal redraw cadence

## Marker Counts
- UNITSEL_ROUTE_START: 1
- UNITSEL_INVOKE_408030_THEN_406980: 1
- UNITSEL_SELECT_ENTRY: 0
- UNITSEL_SELECT_TILE: 1
- UNITSEL_SELECT_SUCCESS: 1
- UNITSEL_SELECT_FAIL: 0
- UNITSEL_WRITE_511B58: 0
- UNITSEL_WRITE_514194: 1
- UNITSEL_406980_ENTRY: 2
- UNITSEL_406980_PRESENT_HELPER: 0
- UNITSEL_406980_RENDER_PRESENT: 0
- UNITSEL_406980_RETURN_DUMP: 0
- UNITSEL_40A490_ENTRY: 1
- UNITSEL_40A500_ENTRY: 1
- UNITSEL_40A500_CALL_423B00: 1
- UNITSEL_423B00_ENTRY: 2
- SURFDUMP_LOADSAVE: 2
- SURFDUMP_PLAYGAME: 1
- SURFDUMP_REDRAW: 16
- SURFDUMP_READY: 1
- SURFDUMP_HOST_READY: 1
- AV_SURFDUMP: 0

## First Rows
- line 203: SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=04220030
- line 204: SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=04220030
- line 205: SURFDUMP_PLAYGAME gd=04220030 map=(100,100) scroll=(10,17) surface=03e9c880 size=(640,480)
- line 206: RLOOPU_HEADER gd=04220030 player=0 scroll=(10,17) map=(100,100) selected=-1 prior=-1 shift=6 surface=03ace540 size=(800,600)
- line 207: RLOOPU_INVOKE_408030_THEN_406980 screen=(448,176) raw=(0x00007000,0x00002c00) select_return=00406980 update_return=0040b0c3
- line 208: RLOOPU_SELECT_TILE map=(16,19) tile=3 selected_before=-1 current=0
- line 209: RLOOPU_SELECT_SUCCESS eax=1 selected_after=3
- line 210: RLOOPU_406980_ENTRY ret=0040b0c3 selected=3 prior=-1 d526994=0 d532218=00000000 d5322c8=0 render=03ace540 map_surface=03ace540 sz=(800,600)
- line 211: RLOOPU_406980_ENTRY ret=0040b0c3 selected=3 prior=-1 d526994=0 d532218=00000000 d5322c8=0 render=03ace540 map_surface=03ace540 sz=(800,600)
- line 212: RLOOPU_40A490_ENTRY ret=0040698c selected=3 prior=-1 current=0 d526994=0 d532218=00000000 d5322c8=0
- line 216: RLOOPU_40A500_ENTRY ret=0040a4f2 eax=00000010 edx=000001b3 ecx=04220030 ebp=00000000 selected=3 prior=-1 d526994=0 d532218=00000000 d5322c8=0
- line 217: RLOOPU_40A500_CALL_423B00 ret=00000003 selected=3 prior=-1 d526994=0 d532218=00000000 d5322c8=0
- line 218: RLOOPU_423B00_ENTRY ret=0040a5f3 eax=00000008 edx=0000087f ecx=04220030 ebp=00000000 selected=3 prior=-1 d526994=0 d532218=00000000 d5322c8=0
- line 219: RLOOPU_423B00_ENTRY ret=0040a5f3 eax=00000008 edx=0000087f ecx=04220030 ebp=00000000 selected=3 prior=-1 d526994=0 d532218=00000000 d5322c8=0
- line 220: RLOOPU_WRITE_514194 eip=00423b1c ret=0000087f selected=3 new_prior=3 d526994=1 d532218=00000000 d5322c8=0
- line 221: SURFDUMP_REDRAW seq=0 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
- line 222: SURFDUMP_REDRAW seq=1 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
- line 223: SURFDUMP_REDRAW seq=2 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
- line 224: SURFDUMP_REDRAW seq=3 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
- line 225: SURFDUMP_READY redraw_seq=4 surface=03ace540 size=(800,600) base=03ad0030 bytes=480000
- line 237: SURFDUMP_HOST_READY
- line 238: SURFDUMP_REDRAW seq=4 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
- line 239: SURFDUMP_REDRAW seq=5 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
- line 240: SURFDUMP_REDRAW seq=6 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
- line 241: SURFDUMP_REDRAW seq=7 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
- line 242: SURFDUMP_REDRAW seq=8 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
- line 243: SURFDUMP_REDRAW seq=9 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
- line 244: SURFDUMP_REDRAW seq=10 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
- line 245: SURFDUMP_REDRAW seq=11 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
- line 246: SURFDUMP_REDRAW seq=12 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
- line 247: SURFDUMP_REDRAW seq=13 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
- line 248: SURFDUMP_REDRAW seq=14 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
- line 249: SURFDUMP_REDRAW seq=15 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
