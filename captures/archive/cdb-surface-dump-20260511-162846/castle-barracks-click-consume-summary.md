# Castle Barracks Centered Action Click Probe

- Log: `captures\cdb-surface-dump-20260511-162846\cdb-surface-dump.log`
- Rows parsed: 14
- Access violations: 0
- Descriptor click ok: True
- Action exit ok: True
- Pre-gate click ok: True
- Failure exits: 0
- Click flag trace armed: 1
- Click flag writes: 0

## Classification

- centered action coordinate was installed
- descriptor callback resolved to 00435620 action click dispatch
- 00435620 action click dispatch was entered
- action click set dword_532210 to exit the barracks loop
- dword_544D04 trace was armed after centered click injection
- action descriptor 0051519a saw click_flag=1 before stock gates
- surface dump reached ready state

## Screenshot

![castle barracks action click](C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\cdb-surface-dump-20260511-162846\surface.png)

## Key Rows

- line 205: `APBARRACKS_ACTION_BOX_435500 ret=00435d93 owner=043ec71a selected_index=0 selected_addon=0 hover_slot=-1 action_state=0 mouse=(320,166) render=0051d4c0 map_surface=0a1bed90 APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=043ec71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a1bed90 sz=(800,600)`
- line 205: `APBARRACKS_CLICKFLAG_WATCH_ARMED pass_index=1 mouse=(161,501) raw=(00002840,00007d40) click_flag=00000001 button0=0x80`
- line 205: `APBARRACKS_ACTION_FORCE_CENTERED target=bottom-left-action pass_index=1 centered=(161,501) expected_native=(81,441) shift=6 raw=(00002840,00007d40) click_flag=00000001 button0=0x80 selected_index=0 selected_addon=0 hover_slot=-1 action_state=0`
- line 205: `APBARRACKS_ACTION_DESCRIPTOR_ENTRY desc=00515130 mouse=(81,441) raw=(00001440,00006e40) click_flag=00000001 button0=0x80 selected_index=0 hover_slot=-1 action_state=0`
- line 205: `APBARRACKS_ACTION_WIDGET_PRE_GATES desc=0051519a reason=no_rearm_trace click_flag=00000001 button0=0x80 mouse=(81,441)`
- line 205: `APBARRACKS_ACTION_WIDGET_CLICK_GATE desc=0051519a desc_xy=(41,425) state=0x01 hover_cb=00419770 click_cb=00435620 type=0x02 mouse=(81,441) click_flag=00000001 button0=0x80`
- line 205: `APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=1 click_cb=00435620 state=0x01 mouse=(81,441) click_flag=00000001`
- line 205: `APBARRACKS_ACTION_DESCRIPTOR_CALLBACK desc=0051519a callback=00435620 desc_xy=(41,425) state=0x01 mouse=(81,441) action_state=0`
- line 205: `APBARRACKS_ACTION_CLICK_435620_ENTRY desc=0051519a mouse=(81,441) action_state_before=0 selected_index=0 selected_addon=0 hover_slot=-1 APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=043ec71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a1bed90 sz=(800,600) APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=043ec71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a1bed90 sz=(800,600) APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=043ec71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a1bed90 sz=(800,600) APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=043ec71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a1bed90 sz=(800,600)`
- line 205: `APBARRACKS_ACTION_CLICK_435620_BEFORE_SET edx=1 action_state_before=0`
- line 205: `APBARRACKS_ACTION_CLICK_EXIT_SET pass_index=4 action_state=1 selected_index=0 selected_addon=0 hover_slot=-1 APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=043ec71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a1bed90 sz=(800,600) APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=043ec71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a1bed90 sz=(800,600)`
- line 205: `APBARRACKS_ACTION_DESCRIPTOR_RESULT result=3 pass_index=4 mouse=(84,501) action_state=1 APBARRACKS_4338E0_AFTER_435BC0 ret=0040ae16 d532218=043ec71a selected_index=0 selected_addon=0 hover_slot=-1 action_state=1 surface=0a1bed90 sz=(800,600)`
- line 205: `APBARRACKS_SURFDUMP_READY after_action=1 surface=0a1bed90 size=(800,600) base=0a460030 bytes=480000 d532150=043ec71a d532218=043ec71a selected_index=0 selected_addon=0 hover_slot=-1 action_state=1 scroll=(10,17)`
- line 205: `SURFDUMP_READY redraw_seq=981 surface=0a1bed90 size=(800,600) base=0a460030 bytes=480000 SURFDUMP_HOST_READY`
