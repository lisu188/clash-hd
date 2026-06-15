# Castle Overview Multi-Hitbox Probe

- Log: `captures\archive\cdb-surface-dump-20260515-103743\cdb-surface-dump.log`
- All targets ok: True
- Access violations: 0
- Callback called: False
- Ready surface size: `[800, 600]`

## Targets

- index 0: raw `0xF8`, command `0x86`, callback `0x0044FE70`, expected gate `1`, completion_ok=True, ok=True
- index 1: raw `0xFE`, command `0x63`, callback `0x00433C20`, expected gate `1`, completion_ok=True, ok=True
- index 2: raw `0xFF`, command `0x87`, callback `0x0042B0A0`, expected gate `1`, completion_ok=True, ok=True

## Classification

- target 0 raw 0xF8 command 0x86 gate 1: ok
- target 1 raw 0xFE command 0x63 gate 1: ok
- target 2 raw 0xFF command 0x87 gate 1: ok
- surface dump reached ready state

## Key Rows

- line 197: `CASTLEOV_MULTI_OVERVIEW_POST_DRAW index=0 main_surface=0a06fdb0 main_size=(800,600) overview_surface=0a06fcf0 overview_size=(640,480) owner_screen=041bc71a`
- line 197: `CASTLEOV_MULTI_TARGET_SET index=0 raw=248 command=134 callback=0044fe70 expected_gate=1 displayed=(371,107) native=(291,47)`
- line 197: `CASTLEOV_MULTI_HITTEST_BEGIN index=0 expected_raw=248 expected_command=134 expected_callback=0044fe70 mouse=(371,107) raw=(00005cc0,00001ac0) click_flag=00000001 button0=0x80`
- line 197: `CASTLEOV_MULTI_HITTEST_RESULT index=0 raw_hit=248 expected_raw=248 adjusted_hit=0 mouse=(371,107) raw=(00005cc0,00001ac0)`
- line 197: `CASTLEOV_MULTI_DESCRIPTOR_INSTALL index=0 command=134 expected_command=134 callback=0044fe70 expected_callback=0044fe70 text=00000003 arg_count=5171110 owner_screen=041bc71a surface=0a06fdb0 sz=(800,600) mouse=(371,107)`
- line 197: `CASTLEOV_MULTI_CLICK_GATE index=0 command=134 expected_command=134 callback=0044fe70 expected_callback=0044fe70 gate=1 expected_gate=1 mouse=(371,107) click_flag=00000001 button0=0x80`
- line 197: `CASTLEOV_MULTI_TARGET_DONE index=0 command=134 callback=0044fe70 gate=1 raw=248`
- line 197: `CASTLEOV_MULTI_TARGET_SET index=1 raw=254 command=99 callback=00433c20 expected_gate=1 displayed=(231,366) native=(151,306)`
- line 197: `CASTLEOV_MULTI_HITTEST_BEGIN index=1 expected_raw=254 expected_command=99 expected_callback=00433c20 mouse=(231,366) raw=(000039c0,00005b80) click_flag=00000001 button0=0x80`
- line 197: `CASTLEOV_MULTI_HITTEST_RESULT index=1 raw_hit=254 expected_raw=254 adjusted_hit=6 mouse=(231,366) raw=(000039c0,00005b80)`
- line 197: `CASTLEOV_MULTI_DESCRIPTOR_INSTALL index=1 command=99 expected_command=99 callback=00433c20 expected_callback=00433c20 text=00000003 arg_count=5171298 owner_screen=041bc71a surface=0a06fdb0 sz=(800,600) mouse=(231,366)`
- line 197: `CASTLEOV_MULTI_CLICK_GATE index=1 command=99 expected_command=99 callback=00433c20 expected_callback=00433c20 gate=1 expected_gate=1 mouse=(231,366) click_flag=00000001 button0=0x80`
- line 197: `CASTLEOV_MULTI_TARGET_DONE index=1 command=99 callback=00433c20 gate=1 raw=254`
- line 197: `CASTLEOV_MULTI_TARGET_SET index=2 raw=255 command=135 callback=0042b0a0 expected_gate=1 displayed=(635,405) native=(555,345)`
- line 197: `CASTLEOV_MULTI_HITTEST_BEGIN index=2 expected_raw=255 expected_command=135 expected_callback=0042b0a0 mouse=(635,405) raw=(00009ec0,00006540) click_flag=00000001 button0=0x80`
- line 197: `CASTLEOV_MULTI_HITTEST_RESULT index=2 raw_hit=255 expected_raw=255 adjusted_hit=7 mouse=(635,405) raw=(00009ec0,00006540)`
- line 197: `CASTLEOV_MULTI_DESCRIPTOR_INSTALL index=2 command=135 expected_command=135 callback=0042b0a0 expected_callback=0042b0a0 text=00000003 arg_count=5171275 owner_screen=041bc71a surface=0a06fdb0 sz=(800,600) mouse=(635,405)`
- line 197: `CASTLEOV_MULTI_CLICK_GATE index=2 command=135 expected_command=135 callback=0042b0a0 expected_callback=0042b0a0 gate=1 expected_gate=1 mouse=(635,405) click_flag=00000001 button0=0x80`
- line 197: `CASTLEOV_MULTI_TARGET_DONE index=2 command=135 callback=0042b0a0 gate=1 raw=255`
- line 197: `CASTLEOV_MULTI_SURFDUMP_READY targets_done=3 surface=0a06fdb0 size=(800,600) base=0a130030 bytes=480000 owner_screen=041bc71a exit_flag=0`
- line 197: `SURFDUMP_READY redraw_seq=997 surface=0a06fdb0 size=(800,600) base=0a130030 bytes=480000`
- line 197: `SURFDUMP_HOST_READY`
