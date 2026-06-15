# Castle Overview Centered Hitbox Probe

- Log: `captures\archive\cdb-surface-dump-20260515-103705\cdb-surface-dump.log`
- Expected command: `0x86`
- Expected callback: `0x0044FE70`
- Expected raw hit: `248`
- Rows parsed: 14
- Access violations: 0
- Displayed result: `{'raw_hit': 248, 'adjusted_hit': 0, 'mouse': [371, 107], 'raw': [23744, 6848], 'target_raw': 248}`
- Native result: `None`
- Descriptor ok: True
- Displayed hit ok: True
- Native hit ok: False
- Click gate ok: True
- Callback suppressed: True
- Callback called: False
- Ready surface size: `[800, 600]`

## Classification

- displayed coordinate 371,107 was installed
- displayed coordinate hit the target overview command
- debugger-side native transform was not installed
- native coordinate did not prove target raw hit 0xF8
- displayed coordinate reached the target through the binary input wrapper
- descriptor command 0x86 callback 0x0044FE70 was installed
- stock click gate returned 1 for the target descriptor
- target callback was suppressed after gate proof
- surface dump reached ready state

## Key Rows

- line 200: `CASTLEOV_HITBOX_INVOKE_PLAYGAME castle_index=0 gd=040f0030 current_player=0 surface=038cc920 sz=(640,480) SURFDUMP_PLAYGAME gd=040f0030 map=(100,100) scroll=(10,17) surface=038cc920 size=(640,480)`
- line 201: `CASTLEOV_HITBOX_OVERVIEW_POST_DRAW main_surface=0a06fd90 main_size=(800,600) overview_surface=0a06fcd0 overview_size=(640,480) owner_screen=0416c71a mouse=(371,107) click_flag=00000001 button0=0x80`
- line 201: `CASTLEOV_HITBOX_DISPLAYED_SET target=command86 displayed=(371,107) expected_native=(291,47) raw=(00005cc0,00001ac0) shift=6`
- line 201: `CASTLEOV_HITBOX_DISPLAYED_HITTEST_BEGIN displayed=(371,107) expected_native=(291,47) raw=(00005cc0,00001ac0) click_flag=00000001 button0=0x80`
- line 201: `CASTLEOV_HITBOX_DISPLAYED_RESULT raw_hit=248 adjusted_hit=0 mouse=(371,107) raw=(00005cc0,00001ac0) target_raw=248`
- line 201: `CASTLEOV_HITBOX_DISPLAYED_WRAPPER_OK raw_hit=248 mouse=(371,107) raw=(00005cc0,00001ac0) target_raw=248`
- line 201: `CASTLEOV_HITBOX_DESCRIPTOR_INSTALL command=134 callback=0044fe70 text=00000003 arg_count=5171110 owner_screen=0416c71a surface=0a06fd90 sz=(800,600) mouse=(371,107)`
- line 201: `CASTLEOV_HITBOX_CLICK_STATE command=134 callback=0044fe70 mouse=(371,107) click_flag=00000001 button0=0x80`
- line 201: `CASTLEOV_HITBOX_CLICK_GATE command=134 callback=0044fe70 gate=1 mouse=(371,107) click_flag=00000001 button0=0x80`
- line 201: `CASTLEOV_HITBOX_CLICK_GATE_OK command=134 callback=0044fe70 gate=1 displayed=(371,107) native=(291,47) surface=0a06fd90 size=(800,600) base=0a130030 bytes=480000`
- line 201: `CASTLEOV_HITBOX_SURFDUMP_READY reason=click_gate_ok surface=0a06fd90 size=(800,600) base=0a130030 bytes=480000 owner_screen=0416c71a exit_flag=0`
- line 201: `SURFDUMP_READY redraw_seq=995 surface=0a06fd90 size=(800,600) base=0a130030 bytes=480000`
- line 201: `SURFDUMP_HOST_READY`
- line 202: `CASTLEOV_HITBOX_CALLBACK_SUPPRESSED command=134 callback=0044fe70 reason=probe_gate_complete eax=00513d98 ebx=00000000 ecx=00000000 edx=00513d98 esi=0000001f edi=0050ee24`
