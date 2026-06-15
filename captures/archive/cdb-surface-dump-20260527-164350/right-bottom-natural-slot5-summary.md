# Right-Bottom Slot Fixture Result Summary

- Log: `captures\cdb-surface-dump-20260527-164350\cdb-surface-dump.log`
- Proof class: `natural_slot5_right_bottom_route`
- Status: `owner_action_reached`
- Expected slot: `5`
- Selected arg: `5`
- Selected global: `5`
- LOADSAVE slot values: `[5, 5]`
- LOADSAVE slot consistent: `True`
- LOADSAVE slot expected match: `True`
- Expected slot match: `True`
- Rows parsed: `17`
- Access violations: `0`
- Load success: `True`
- Owner loop reached: `True`
- Owner flag test: `{'owner': 69715738, 'owner_flag': 11, 'bit2': 2, 'bit1': 1, 'bit8': 8, 'ret': 4333600, 'd532150': 69715738, 'd53214c': 1, 'd532154': 167862544}`
- Owner/action route count: `1`
- Owner/action draw count: `0`
- Castle hitmap sample: `{'surface': 171619384, 'size': [640, 480], 'base': 172163120, 'displayed': [231, 366], 'displayed_sample': 12, 'native': [151, 306], 'native_sample': 254, 'bbox_min': [77, 306], 'bbox_min_sample': 254, 'bbox_max': [237, 426], 'bbox_max_sample': 53, 'expected_raw': 254}`
- Castle command-99 target: `{'native': [151, 306], 'displayed_hint': [231, 366], 'raw': [9664, 19584]}`
- Castle hit count: `1`
- Last castle hit: `{'raw_hit': 254, 'adjusted': 6, 'expected_raw': 254, 'command': 99, 'callback': 4406304, 'owner_screen': 69715738}`

## Marker Counts

- `SURFDUMP_LOADSAVE`: `1`
- `SURFDUMP_PLAYGAME`: `2`
- `SURFDUMP_READY`: `0`
- `SURFDUMP_HOST_READY`: `0`
- `NOWNER_HEADER`: `1`
- `NOWNER_FORCE_MAP_CASTLE_CLICK`: `1`
- `NOWNER_MAP_TILE`: `1`
- `NOWNER_BUILDING_TILE`: `1`
- `NOWNER_CASTLE_OVERVIEW_ENTRY`: `1`
- `NOWNER_CASTLE_HIT_GIVEUP`: `0`
- `NOWNER_CASTLE_HITMAP_SAMPLE`: `1`
- `NOWNER_CASTLE_CMD99_TARGET`: `1`
- `NOWNER_CASTLE_HIT`: `1`
- `NOWNER_CASTLE_CMD99_GATE`: `1`
- `NOWNER_CASTLE_CALLBACK`: `1`
- `NOWNER_433C20_ENTRY`: `1`
- `NOWNER_OWNER_FLAG_TEST`: `1`
- `NOWNER_OWNER_SCREEN_DESC_DRAW`: `1`
- `NOWNER_OWNER_DESC_RESULT_SURFDUMP_READY`: `0`
- `NOWNER_4338E0_ENTRY`: `1`
- `NOWNER_4338E0_SURFDUMP_READY`: `0`
- `NOWNER_4338E0_OWNER_FLAG_BLOCKED`: `0`
- `NOWNER_ACTION_CALL_WRAPPER`: `0`
- `NOWNER_OWNER_435BC0_ENTRY`: `0`
- `NOWNER_WRAPPER_COPYBACK_DONE`: `0`
- `AV_SURFDUMP`: `0`

## Classification

- LOADSAVE and PlayGame were reached
- observed load slot matches the expected fixture slot
- castle command-99 owner loop was reached
- castle overview hitmap samples were captured around command 0x63
- owner flag bit 0x02 was set
- owner/action route markers were observed

## Key Rows

- line 201: `SURFDUMP_LOADSAVE selected_arg=5 selected_global=5 accept=1 choice=5 gd=04200030`
- line 202: `SURFDUMP_PLAYGAME gd=04200030 map=(100,100) scroll=(11,17) surface=041fc8f8 size=(640,480)`
- line 203: `SURFDUMP_PLAYGAME gd=04200030 map=(100,100) scroll=(11,17) surface=041fc8f8 size=(640,480)`
- line 204: `NOWNER_HEADER gd=04200030 player=0 scroll=(11,17) surface=0a07ee10 size=(800,600) SURFDUMP_REDRAW seq=0 scroll=(11,17) end12=(23,26) map=(100,100) surface=0a07ee10 size=(800,600)`
- line 205: `NOWNER_FORCE_MAP_CASTLE_CLICK screen=(224,224) expected_map=(14,20) raw=(00003800,00003800)`
- line 205: `NOWNER_MAP_TILE map=(14,20) mouse=(224,224) selected=-1 current=0 NOWNER_REARM_MAP_COMMIT map=(14,20) mouse=(20,224)`
- line 205: `NOWNER_BUILDING_TILE map=(14,20) tile=32768 index=0 owner=0 mode=2 active=0 flags=0x0b`
- line 205: `NOWNER_CASTLE_OVERVIEW_ENTRY ret=0041ed6f castle_index=0 main_surface=0a07ee10 size=(800,600) NOWNER_CASTLE_OVERVIEW_POST_DRAW overview_surface=0a3ab438 size=(640,480) owner_screen=0427c71a`
- line 205: `NOWNER_CASTLE_HITMAP_SAMPLE surface=0a3ab438 size=(640,480) base=0a430030 displayed=(231,366) displayed_sample=0x0c native=(151,306) native_sample=0xfe bbox_min=(77,306) bbox_min_sample=0xfe bbox_max=(237,426) bbox_max_sample=0x35 expected_raw=254`
- line 205: `NOWNER_CASTLE_CMD99_TARGET native=(151,306) displayed_hint=(231,366) raw=(000025c0,00004c80)`
- line 205: `NOWNER_CASTLE_HIT raw_hit=254 adjusted=6 expected_raw=254 NOWNER_CASTLE_DESCRIPTOR command=99 callback=00433c20 owner_screen=0427c71a`
- line 205: `NOWNER_CASTLE_CMD99_GATE gate_before=1 forced_gate=1`
- line 205: `NOWNER_CASTLE_CALLBACK callback=00433c20 eax_arg=0427c71a command=99`
- line 205: `NOWNER_433C20_ENTRY ret=0042262e owner_arg=0427c71a owner_flag=0x0b d532150_before=00000000 surface=0a07ee10 size=(800,600)`
- line 205: `NOWNER_OWNER_FLAG_TEST owner=0427c71a owner_flag=0x0b bit2=2 bit1=1 bit8=8 NOWNER_WRITE_532154 continue_full ret=00422020 d532150=0427c71a d53214c=00000001 d532154=0a016110 owner_flag=0x0b`
- line 205: `NOWNER_OWNER_SCREEN_DESC_DRAW list=00514fc0 d0=(39,426 cb=004338c0) d1=(155,426 cb=004338e0) d2=(272,426 cb=00433a40) surface=0a07ee10 size=(800,600) NOWNER_FORCE_OWNER_DESC_CLICK native=(180,440) raw=(00002d00,00006e00) d1=(155,426 cb=004338e0) owner=0427c71a owner_flag=0x0b NOWNER_HITTEST_ENTRY count=1 desc=00514fc0 xy=(39,426) flags=0x01 hit=004338c0 mouse=(180,440) click=00000001 button0=0x80 NOWNER_HITTEST_ENTRY count=2 desc=00514ff5 xy=(155,426) flags=0x01 hit=004338e0 mouse=(180,440) click=00000001 button0=0x80 NOWNER_DESCRIPTOR_CALLBACK desc=00514ff5 xy=(155,426) flags=0x01 callback=004338e0 mouse=(180,440)`
- line 205: `NOWNER_4338E0_ENTRY ret=00419c60 eax_desc=00514ff5 owner=0427c71a owner_flag=0x0b d532218=00000000 d5322c8=0 surface=0a07ee10 size=(800,600)`
