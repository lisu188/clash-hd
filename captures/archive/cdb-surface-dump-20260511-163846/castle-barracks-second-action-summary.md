# Castle Barracks Centered Action Click Probe

- Log: `captures\cdb-surface-dump-20260511-163846\cdb-surface-dump.log`
- Expected descriptor: `005151cf`
- Expected callback: `004356c0`
- Rows parsed: 14
- Access violations: 0
- Descriptor click ok: True
- Action exit ok: False
- Pre-gate click ok: True
- Failure exits: 0
- Click flag trace armed: 1
- Click flag writes: 0

## Classification

- centered action coordinate was installed
- descriptor 005151cf callback resolved to 004356c0
- 00435620 action click dispatch was not entered
- 004356c0 action callback was entered
- action click did not prove dword_532210 exit state
- dword_544D04 trace was armed after centered click injection
- action descriptor 005151cf saw click_flag=1 before stock gates
- surface dump reached ready state

## Screenshot

![castle barracks action click](C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\cdb-surface-dump-20260511-163846\surface.png)

## Key Rows

- line 209: `APBARRACKS_ACTION_BOX_435500 ret=00435d93 owner=042fc71a selected_index=0 selected_addon=0 hover_slot=-1 action_state=0 mouse=(320,166) render=0051d4c0 map_surface=0a2fedb0 APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=042fc71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a2fedb0 sz=(800,600)`
- line 209: `APBARRACKS_CLICKFLAG_WATCH_ARMED pass_index=1 mouse=(276,501) raw=(00004500,00007d40) click_flag=00000001 button0=0x80`
- line 209: `APBARRACKS_ACTION_FORCE_CENTERED target=bottom-second-action pass_index=1 centered=(276,501) expected_native=(196,441) shift=6 raw=(00004500,00007d40) click_flag=00000001 button0=0x80 selected_index=0 selected_addon=0 hover_slot=-1 action_state=0`
- line 209: `APBARRACKS_ACTION_DESCRIPTOR_ENTRY desc=00515130 mouse=(196,441) raw=(00003100,00006e40) click_flag=00000001 button0=0x80 selected_index=0 hover_slot=-1 action_state=0`
- line 209: `APBARRACKS_ACTION_WIDGET_PRE_GATES desc=005151cf reason=no_rearm_trace click_flag=00000001 button0=0x80 mouse=(196,441)`
- line 209: `APBARRACKS_ACTION_WIDGET_CLICK_GATE desc=005151cf desc_xy=(156,425) state=0x01 hover_cb=00419770 click_cb=004356c0 type=0x02 mouse=(196,441) click_flag=00000001 button0=0x80`
- line 209: `APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=005151cf click_gate=1 click_cb=004356c0 state=0x01 mouse=(196,441) click_flag=00000001`
- line 209: `APBARRACKS_ACTION_DESCRIPTOR_CALLBACK desc=005151cf callback=004356c0 desc_xy=(156,425) state=0x01 mouse=(196,441) action_state=0`
- line 209: `APBARRACKS_ACTION_CLICK_4356C0_ENTRY desc=005151cf mouse=(196,441) action_state_before=0 selected_index=0 selected_addon=0 hover_slot=-1 APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=042fc71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a2fedb0 sz=(800,600) APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=042fc71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a2fedb0 sz=(800,600)`
- line 209: `APBARRACKS_ACTION_CLICK_4356C0_CHECK_RET check_result=0 selected_index=0 selected_addon=0 action_state=0`
- line 209: `APBARRACKS_ACTION_CLICK_4356C0_EARLY_RETURN reason=check_failed check_result=0 selected_index=0 selected_addon=0 action_state=1 proof_exit=1 APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=042fc71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a2fedb0 sz=(800,600) APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=042fc71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a2fedb0 sz=(800,600) APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=042fc71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a2fedb0 sz=(800,600) APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=042fc71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a2fedb0 sz=(800,600)`
- line 209: `APBARRACKS_ACTION_DESCRIPTOR_RESULT result=3 pass_index=4 mouse=(276,501) action_state=1 APBARRACKS_4338E0_AFTER_435BC0 ret=0040ae16 d532218=042fc71a selected_index=0 selected_addon=0 hover_slot=-1 action_state=1 surface=0a2fedb0 sz=(800,600)`
- line 209: `APBARRACKS_SURFDUMP_READY after_action=1 surface=0a2fedb0 size=(800,600) base=0a5a0030 bytes=480000 d532150=042fc71a d532218=042fc71a selected_index=0 selected_addon=0 hover_slot=-1 action_state=1 scroll=(10,17)`
- line 209: `SURFDUMP_READY redraw_seq=991 surface=0a2fedb0 size=(800,600) base=0a5a0030 bytes=480000 SURFDUMP_HOST_READY`
