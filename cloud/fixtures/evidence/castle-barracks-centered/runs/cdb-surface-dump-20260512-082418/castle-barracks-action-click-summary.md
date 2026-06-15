# Castle Barracks Centered Action Click Probe

- Log: `captures\archive\cdb-surface-dump-20260512-082418\cdb-surface-dump.log`
- Expected descriptor: `005151cf`
- Expected callback: `004356c0`
- Rows parsed: 13
- Access violations: 0
- Descriptor click ok: True
- Action exit ok: False
- 004356c0 success branch ok: False
- 004356c0 controlled stop ok: True
- Pre-gate click ok: True
- Failure exits: 0
- Click flag trace armed: 1
- Click flag writes: 0

## Classification

- centered action coordinate was installed
- selected barracks addon was forced before action-panel draw
- descriptor 005151cf callback resolved to 004356c0
- 00435620 action click dispatch was not entered
- 004356c0 action callback was entered
- 004356c0 action callback stopped at the controlled dump point
- action click did not prove dword_532210 exit state
- dword_544D04 trace was armed after centered click injection
- action descriptor 005151cf saw click_flag=1 before stock gates
- surface dump reached ready state

## Screenshot

![castle barracks action click](.\captures\archive\cdb-surface-dump-20260512-082418\surface.png)

## Key Rows

- line 204: `APBARRACKS_SELECT_FORCED ret=00435d84 forced_index=1 selected_addon=1 list=(0,1,3,16,17,37,38,39,-1,-1,-1,-1) APBARRACKS_PANEL_DRAW_4347A0 ret=00435d84 owner=0402c71a selected_index=1 selected_addon=1 render=0a2fedd0 map_surface=0a2fedd0 sz=(800,600) APBARRACKS_GRID_DRAW_434E20 ret=00435172 owner=0402c71a selected_index=1 selected_addon=1 hover_slot=-1 render=0a2fedd0 map_surface=0a2fedd0 sz=(800,600)`
- line 204: `APBARRACKS_ACTION_BOX_435500 ret=00435d93 owner=0402c71a selected_index=1 selected_addon=1 hover_slot=-1 action_state=0 mouse=(320,166) render=0051d4c0 map_surface=0a2fedd0 APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=0402c71a selected_index=1 selected_addon=1 hover_slot=-1 render=0051d4c0 map_surface=0a2fedd0 sz=(800,600)`
- line 204: `APBARRACKS_CLICKFLAG_WATCH_ARMED pass_index=1 mouse=(276,501) raw=(00004500,00007d40) click_flag=00000001 button0=0x80`
- line 204: `APBARRACKS_ACTION_FORCE_CENTERED target=bottom-second-action pass_index=1 centered=(276,501) expected_native=(196,441) shift=6 raw=(00004500,00007d40) click_flag=00000001 button0=0x80 selected_index=1 selected_addon=1 hover_slot=-1 action_state=0`
- line 204: `APBARRACKS_ACTION_DESCRIPTOR_ENTRY desc=00515130 mouse=(196,441) raw=(00003100,00006e40) click_flag=00000001 button0=0x80 selected_index=1 hover_slot=-1 action_state=0`
- line 204: `APBARRACKS_ACTION_WIDGET_PRE_GATES desc=005151cf reason=no_rearm_trace click_flag=00000001 button0=0x80 mouse=(196,441)`
- line 204: `APBARRACKS_ACTION_WIDGET_CLICK_GATE desc=005151cf desc_xy=(156,425) state=0x01 hover_cb=00419770 click_cb=004356c0 type=0x02 mouse=(196,441) click_flag=00000001 button0=0x80`
- line 204: `APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=005151cf click_gate=1 click_cb=004356c0 state=0x01 mouse=(196,441) click_flag=00000001`
- line 204: `APBARRACKS_ACTION_DESCRIPTOR_CALLBACK desc=005151cf callback=004356c0 desc_xy=(156,425) state=0x01 mouse=(196,441) action_state=0`
- line 204: `APBARRACKS_ACTION_CLICK_4356C0_ENTRY desc=005151cf mouse=(196,441) action_state_before=0 selected_index=1 selected_addon=1 hover_slot=-1`
- line 204: `APBARRACKS_ACTION_CLICK_4356C0_CONTROLLED_STOP reason=entry_before_privileged_probe selected_index=1 selected_addon=1 action_state=1 surface=0a2fedd0 size=(800,600) base=0a5a0030 bytes=480000`
- line 204: `APBARRACKS_SURFDUMP_READY after_action=controlled_stop surface=0a2fedd0 size=(800,600) base=0a5a0030 bytes=480000 d532150=0402c71a d532218=0402c71a selected_index=1 selected_addon=1 hover_slot=-1 action_state=1 scroll=(10,17)`
- line 204: `SURFDUMP_READY redraw_seq=993 surface=0a2fedd0 size=(800,600) base=0a5a0030 bytes=480000 SURFDUMP_HOST_READY`
