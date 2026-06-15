# Right-Bottom Slot Fixture Result Summary

- Log: `captures\cdb-surface-dump-20260527-160557\cdb-surface-dump.log`
- Status: `castle_route_not_reached`
- Expected slot: `0`
- Selected arg: `0`
- Selected global: `0`
- LOADSAVE slot values: `[0, 0]`
- LOADSAVE slot consistent: `True`
- LOADSAVE slot expected match: `True`
- Expected slot match: `True`
- Rows parsed: `24`
- Access violations: `0`
- Load success: `True`
- Owner loop reached: `False`
- Owner flag test: `{}`
- Owner/action route count: `0`
- Castle hitmap sample: `{'surface': 172930744, 'size': [640, 480], 'base': 173473840, 'displayed': [231, 366], 'displayed_sample': 12, 'native': [151, 306], 'native_sample': 254, 'bbox_min': [77, 306], 'bbox_min_sample': 254, 'bbox_max': [237, 426], 'bbox_max_sample': 53, 'expected_raw': 254}`
- Castle command-99 target: `{'displayed': [231, 366], 'raw': [14784, 23424]}`
- Castle hit count: `12`
- Last castle hit: `{'raw_hit': 10, 'adjusted': -238, 'expected_raw': 254}`

## Marker Counts

- `SURFDUMP_LOADSAVE`: `1`
- `SURFDUMP_PLAYGAME`: `1`
- `SURFDUMP_READY`: `1`
- `SURFDUMP_HOST_READY`: `1`
- `NOWNER_HEADER`: `1`
- `NOWNER_FORCE_MAP_CASTLE_CLICK`: `1`
- `NOWNER_MAP_TILE`: `1`
- `NOWNER_BUILDING_TILE`: `1`
- `NOWNER_CASTLE_OVERVIEW_ENTRY`: `1`
- `NOWNER_CASTLE_HIT_GIVEUP`: `1`
- `NOWNER_CASTLE_HITMAP_SAMPLE`: `1`
- `NOWNER_CASTLE_CMD99_TARGET`: `1`
- `NOWNER_CASTLE_HIT`: `12`
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
- castle overview command hit target was not reached before bounded giveup
- castle overview hitmap samples were captured around command 0x63
- owner flag bit 0x02 was not set
- owner/action renderer route markers were not observed

## Key Rows

- line 199: `NOWNER_MAP_TILE map=(14,20) mouse=(224,224) selected=-1 current=0 NOWNER_REARM_MAP_COMMIT map=(14,20) mouse=(20,224)`
- line 199: `NOWNER_BUILDING_TILE map=(14,20) tile=32768 index=0 owner=0 mode=2 active=0 flags=0x0b`
- line 199: `NOWNER_CASTLE_OVERVIEW_ENTRY ret=0041ed6f castle_index=0 main_surface=0a1bf030 size=(800,600) NOWNER_CASTLE_OVERVIEW_POST_DRAW overview_surface=0a4eb6b8 size=(640,480) owner_screen=041bc71a`
- line 199: `NOWNER_CASTLE_HITMAP_SAMPLE surface=0a4eb6b8 size=(640,480) base=0a570030 displayed=(231,366) displayed_sample=0x0c native=(151,306) native_sample=0xfe bbox_min=(77,306) bbox_min_sample=0xfe bbox_max=(237,426) bbox_max_sample=0x35 expected_raw=254`
- line 199: `NOWNER_CASTLE_CMD99_TARGET displayed=(231,366) raw=(000039c0,00005b80)`
- line 199: `NOWNER_CASTLE_HIT raw_hit=12 adjusted=-236 expected_raw=254`
- line 199: `NOWNER_CASTLE_HIT raw_hit=10 adjusted=-238 expected_raw=254`
- line 199: `NOWNER_CASTLE_HIT raw_hit=10 adjusted=-238 expected_raw=254`
- line 199: `NOWNER_CASTLE_HIT raw_hit=10 adjusted=-238 expected_raw=254`
- line 199: `NOWNER_CASTLE_HIT raw_hit=10 adjusted=-238 expected_raw=254`
- line 199: `NOWNER_CASTLE_HIT raw_hit=10 adjusted=-238 expected_raw=254`
- line 199: `NOWNER_CASTLE_HIT raw_hit=10 adjusted=-238 expected_raw=254`
- line 199: `NOWNER_CASTLE_HIT raw_hit=10 adjusted=-238 expected_raw=254`
- line 199: `NOWNER_CASTLE_HIT raw_hit=10 adjusted=-238 expected_raw=254`
- line 199: `NOWNER_CASTLE_HIT raw_hit=10 adjusted=-238 expected_raw=254`
- line 199: `NOWNER_CASTLE_HIT raw_hit=10 adjusted=-238 expected_raw=254`
- line 199: `NOWNER_CASTLE_HIT raw_hit=10 adjusted=-238 expected_raw=254`
- line 199: `NOWNER_CASTLE_HIT_GIVEUP count=12 last_raw_hit=10 adjusted=-238 expected_raw=254 surface=0a1bf030 size=(800,600) base=0a460030 bytes=480000`
- line 199: `SURFDUMP_READY redraw_seq=996 surface=0a1bf030 size=(800,600) base=0a460030 bytes=480000`
- line 199: `SURFDUMP_HOST_READY`
