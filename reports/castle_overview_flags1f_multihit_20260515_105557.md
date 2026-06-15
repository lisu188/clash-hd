# Castle Overview Multi-Hitbox Probe

- Log: `captures\archive\cdb-surface-dump-20260515-105557\cdb-surface-dump.log`
- All targets ok: True
- Access violations: 0
- Callback called: False
- Ready surface size: `[800, 600]`

## Targets

- index 0: raw `0xFA`, command `0x99`, callback `0x0043DCE0`, expected gate `1`, completion_ok=True, ok=True
- index 1: raw `0xFB`, command `0x9C`, callback `0x0043D8E0`, expected gate `1`, completion_ok=True, ok=True
- index 2: raw `0xFC`, command `0x9F`, callback `0x0043DEE0`, expected gate `1`, completion_ok=True, ok=True
- index 3: raw `0xFD`, command `0xA6`, callback `0x0043DAE0`, expected gate `1`, completion_ok=True, ok=True

## Classification

- target 0 raw 0xFA command 0x99 gate 1: ok
- target 1 raw 0xFB command 0x9C gate 1: ok
- target 2 raw 0xFC command 0x9F gate 1: ok
- target 3 raw 0xFD command 0xA6 gate 1: ok
- surface dump reached ready state

## Key Rows

- line 206: `CASTLEOV_MULTI_DESCRIPTOR_INSTALL index=0 command=153 expected_command=153 callback=0043dce0 expected_callback=0043dce0 text=00000003 arg_count=5171145 owner_screen=043bc71a surface=0a013ed8 sz=(800,600) mouse=(170,134)`
- line 206: `CASTLEOV_MULTI_CLICK_GATE index=0 command=153 expected_command=153 callback=0043dce0 expected_callback=0043dce0 gate=1 expected_gate=1 mouse=(170,134) click_flag=00000001 button0=0x80`
- line 206: `CASTLEOV_MULTI_TARGET_DONE index=0 command=153 callback=0043dce0 gate=1 raw=250`
- line 206: `CASTLEOV_MULTI_TARGET_SET index=1 raw=251 command=156 callback=0043d8e0 expected_gate=1 displayed=(545,223) native=(465,163)`
- line 206: `CASTLEOV_MULTI_HITTEST_BEGIN index=1 expected_raw=251 expected_command=156 expected_callback=0043d8e0 mouse=(545,223) raw=(00008840,000037c0) click_flag=00000001 button0=0x80`
- line 206: `CASTLEOV_MULTI_HITTEST_RESULT index=1 raw_hit=251 expected_raw=251 adjusted_hit=3 mouse=(545,223) raw=(00008840,000037c0)`
- line 206: `CASTLEOV_MULTI_DESCRIPTOR_INSTALL index=1 command=156 expected_command=156 callback=0043d8e0 expected_callback=0043d8e0 text=00000003 arg_count=5171226 owner_screen=043bc71a surface=0a013ed8 sz=(800,600) mouse=(545,223)`
- line 206: `CASTLEOV_MULTI_CLICK_GATE index=1 command=156 expected_command=156 callback=0043d8e0 expected_callback=0043d8e0 gate=1 expected_gate=1 mouse=(545,223) click_flag=00000001 button0=0x80`
- line 206: `CASTLEOV_MULTI_TARGET_DONE index=1 command=156 callback=0043d8e0 gate=1 raw=251`
- line 206: `CASTLEOV_MULTI_TARGET_SET index=2 raw=252 command=159 callback=0043dee0 expected_gate=1 displayed=(350,329) native=(270,269)`
- line 206: `CASTLEOV_MULTI_HITTEST_BEGIN index=2 expected_raw=252 expected_command=159 expected_callback=0043dee0 mouse=(350,329) raw=(00005780,00005240) click_flag=00000001 button0=0x80`
- line 206: `CASTLEOV_MULTI_HITTEST_RESULT index=2 raw_hit=252 expected_raw=252 adjusted_hit=4 mouse=(350,329) raw=(00005780,00005240)`
- line 206: `CASTLEOV_MULTI_DESCRIPTOR_INSTALL index=2 command=159 expected_command=159 callback=0043dee0 expected_callback=0043dee0 text=00000003 arg_count=5171200 owner_screen=043bc71a surface=0a013ed8 sz=(800,600) mouse=(350,329)`
- line 206: `CASTLEOV_MULTI_CLICK_GATE index=2 command=159 expected_command=159 callback=0043dee0 expected_callback=0043dee0 gate=1 expected_gate=1 mouse=(350,329) click_flag=00000001 button0=0x80`
- line 206: `CASTLEOV_MULTI_TARGET_DONE index=2 command=159 callback=0043dee0 gate=1 raw=252`
- line 206: `CASTLEOV_MULTI_TARGET_SET index=3 raw=253 command=166 callback=0043dae0 expected_gate=1 displayed=(599,315) native=(519,255)`
- line 206: `CASTLEOV_MULTI_HITTEST_BEGIN index=3 expected_raw=253 expected_command=166 expected_callback=0043dae0 mouse=(599,315) raw=(000095c0,00004ec0) click_flag=00000001 button0=0x80`
- line 206: `CASTLEOV_MULTI_HITTEST_RESULT index=3 raw_hit=253 expected_raw=253 adjusted_hit=5 mouse=(599,315) raw=(000095c0,00004ec0)`
- line 206: `CASTLEOV_MULTI_DESCRIPTOR_INSTALL index=3 command=166 expected_command=166 callback=0043dae0 expected_callback=0043dae0 text=00000003 arg_count=5171247 owner_screen=043bc71a surface=0a013ed8 sz=(800,600) mouse=(599,315)`
- line 206: `CASTLEOV_MULTI_CLICK_GATE index=3 command=166 expected_command=166 callback=0043dae0 expected_callback=0043dae0 gate=1 expected_gate=1 mouse=(599,315) click_flag=00000001 button0=0x80`
- line 206: `CASTLEOV_MULTI_TARGET_DONE index=3 command=166 callback=0043dae0 gate=1 raw=253`
- line 206: `CASTLEOV_MULTI_SURFDUMP_READY targets_done=4 surface=0a013ed8 size=(800,600) base=0a160030 bytes=480000 owner_screen=043bc71a exit_flag=0`
- line 206: `SURFDUMP_READY redraw_seq=989 surface=0a013ed8 size=(800,600) base=0a160030 bytes=480000`
- line 206: `SURFDUMP_HOST_READY`
