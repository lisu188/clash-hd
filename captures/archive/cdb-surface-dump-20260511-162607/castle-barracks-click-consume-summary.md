# Castle Barracks Centered Action Click Probe

- Log: `captures\cdb-surface-dump-20260511-162607\cdb-surface-dump.log`
- Rows parsed: 24
- Access violations: 0
- Descriptor click ok: False
- Action exit ok: False
- Failure exits: 1
- Click flag watch armed: 1
- Click flag writes: 0

## Classification

- centered action coordinate was installed
- descriptor callback did not prove 00435620 action click dispatch
- 00435620 action click dispatch was not entered
- action click did not prove dword_532210 exit state
- dword_544D04 watchpoint was armed after centered click injection
- descriptor probe used failure exit
- surface dump reached ready state

## Screenshot

![castle barracks action click](C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\cdb-surface-dump-20260511-162607\surface.png)

## Key Rows

- line 205: `APBARRACKS_ACTION_DESCRIPTOR_RESULT result=2 pass_index=1 mouse=(161,501) action_state=0`
- line 205: `APBARRACKS_ACTION_FORCE_CENTERED target=bottom-left-action pass_index=2 centered=(161,501) expected_native=(81,441) shift=6 raw=(00002840,00007d40) click_flag=00000001 button0=0x80 selected_index=0 selected_addon=0 hover_slot=-1 action_state=0`
- line 205: `APBARRACKS_ACTION_DESCRIPTOR_ENTRY desc=00515130 mouse=(81,441) raw=(00001440,00006e40) click_flag=00000001 button0=0x80 selected_index=0 hover_slot=-1 action_state=0`
- line 205: `APBARRACKS_ACTION_WIDGET_PRE_GATES desc=0051519a reason=no_rearm_trace click_flag=00000000 button0=0x00 mouse=(81,441)`
- line 205: `APBARRACKS_ACTION_WIDGET_CLICK_GATE desc=0051519a desc_xy=(41,425) state=0x05 hover_cb=00419770 click_cb=00435620 type=0x02 mouse=(81,441) click_flag=00000000 button0=0x00`
- line 205: `APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=0 click_cb=00435620 state=0x05 mouse=(81,441) click_flag=00000000`
- line 205: `APBARRACKS_ACTION_DESCRIPTOR_RESULT result=0 pass_index=2 mouse=(161,501) action_state=0 APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=043bc71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a2fedb0 sz=(800,600)`
- line 205: `APBARRACKS_ACTION_FORCE_CENTERED target=bottom-left-action pass_index=3 centered=(161,501) expected_native=(81,441) shift=6 raw=(00002840,00007d40) click_flag=00000001 button0=0x80 selected_index=0 selected_addon=0 hover_slot=-1 action_state=0`
- line 205: `APBARRACKS_ACTION_DESCRIPTOR_ENTRY desc=00515130 mouse=(81,441) raw=(00001440,00006e40) click_flag=00000001 button0=0x80 selected_index=0 hover_slot=-1 action_state=0`
- line 205: `APBARRACKS_ACTION_WIDGET_PRE_GATES desc=0051519a reason=no_rearm_trace click_flag=00000000 button0=0x00 mouse=(81,441)`
- line 205: `APBARRACKS_ACTION_WIDGET_CLICK_GATE desc=0051519a desc_xy=(41,425) state=0x05 hover_cb=00419770 click_cb=00435620 type=0x02 mouse=(81,441) click_flag=00000000 button0=0x00`
- line 205: `APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=0 click_cb=00435620 state=0x05 mouse=(81,441) click_flag=00000000`
- line 205: `APBARRACKS_ACTION_DESCRIPTOR_RESULT result=0 pass_index=3 mouse=(161,501) action_state=0`
- line 205: `APBARRACKS_ACTION_DESCRIPTOR_FAIL_EXIT pass_index=3 action_state=1 APBARRACKS_4338E0_AFTER_435BC0 ret=0040ae16 d532218=043bc71a selected_index=0 selected_addon=0 hover_slot=-1 action_state=1 surface=0a2fedb0 sz=(800,600)`
- line 205: `APBARRACKS_SURFDUMP_READY after_action=1 surface=0a2fedb0 size=(800,600) base=0a5a0030 bytes=480000 d532150=043bc71a d532218=043bc71a selected_index=0 selected_addon=0 hover_slot=-1 action_state=1 scroll=(10,17)`
- line 205: `SURFDUMP_READY redraw_seq=981 surface=0a2fedb0 size=(800,600) base=0a5a0030 bytes=480000 SURFDUMP_HOST_READY`
