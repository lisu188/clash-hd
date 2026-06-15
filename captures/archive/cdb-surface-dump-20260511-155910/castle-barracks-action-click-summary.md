# Castle Barracks Centered Action Click Probe

- Log: `captures\cdb-surface-dump-20260511-155910\cdb-surface-dump.log`
- Rows parsed: 20
- Access violations: 0
- Descriptor click ok: False
- Action exit ok: False
- Failure exits: 1

## Classification

- centered action coordinate was installed
- descriptor callback did not prove 00435620 action click dispatch
- 00435620 action click dispatch was not entered
- action click did not prove dword_532210 exit state
- descriptor probe used failure exit
- surface dump reached ready state

## Screenshot

![castle barracks action click](C:/Users/andrz/OneDrive/Pulpit/git/clash-hd/captures/cdb-surface-dump-20260511-155910/surface.png)

## Key Rows

- line 200: `APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=0 click_cb=00435620 state=0x01 mouse=(81,441) click_flag=00000000`
- line 200: `APBARRACKS_ACTION_WIDGET_HOVER_ARM desc=0051519a desc_xy=(41,425) state_before=0x01 hover_cb=00419770 click_cb=00435620 type=0x02 mouse=(81,441)`
- line 200: `APBARRACKS_ACTION_DESCRIPTOR_RESULT result=2 pass_index=1 mouse=(161,501) action_state=0`
- line 200: `APBARRACKS_ACTION_FORCE_CENTERED target=bottom-left-action pass_index=2 centered=(161,501) expected_native=(81,441) shift=6 raw=(00002840,00007d40) click_flag=00000003 button0=0x80 selected_index=0 selected_addon=0 hover_slot=-1 action_state=0`
- line 200: `APBARRACKS_ACTION_DESCRIPTOR_ENTRY desc=00515130 mouse=(81,441) raw=(00001440,00006e40) click_flag=00000003 button0=0x80 selected_index=0 hover_slot=-1 action_state=0`
- line 200: `APBARRACKS_ACTION_WIDGET_CLICK_GATE desc=0051519a desc_xy=(41,425) state=0x05 hover_cb=00419770 click_cb=00435620 type=0x02 mouse=(81,441) click_flag=00000000 button0=0x00`
- line 200: `APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=0 click_cb=00435620 state=0x05 mouse=(81,441) click_flag=00000000`
- line 200: `APBARRACKS_ACTION_DESCRIPTOR_RESULT result=0 pass_index=2 mouse=(161,501) action_state=0 APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=0398c71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a2fedb0 sz=(800,600)`
- line 200: `APBARRACKS_ACTION_FORCE_CENTERED target=bottom-left-action pass_index=3 centered=(161,501) expected_native=(81,441) shift=6 raw=(00002840,00007d40) click_flag=00000003 button0=0x80 selected_index=0 selected_addon=0 hover_slot=-1 action_state=0`
- line 200: `APBARRACKS_ACTION_DESCRIPTOR_ENTRY desc=00515130 mouse=(81,441) raw=(00001440,00006e40) click_flag=00000003 button0=0x80 selected_index=0 hover_slot=-1 action_state=0`
- line 200: `APBARRACKS_ACTION_WIDGET_CLICK_GATE desc=0051519a desc_xy=(41,425) state=0x05 hover_cb=00419770 click_cb=00435620 type=0x02 mouse=(81,441) click_flag=00000000 button0=0x00`
- line 200: `APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=0 click_cb=00435620 state=0x05 mouse=(81,441) click_flag=00000000`
- line 200: `APBARRACKS_ACTION_DESCRIPTOR_RESULT result=0 pass_index=3 mouse=(161,501) action_state=0`
- line 200: `APBARRACKS_ACTION_DESCRIPTOR_FAIL_EXIT pass_index=3 action_state=1 APBARRACKS_4338E0_AFTER_435BC0 ret=0040ae16 d532218=0398c71a selected_index=0 selected_addon=0 hover_slot=-1 action_state=1 surface=0a2fedb0 sz=(800,600)`
- line 200: `APBARRACKS_SURFDUMP_READY after_action=1 surface=0a2fedb0 size=(800,600) base=0a5a0030 bytes=480000 d532150=0398c71a d532218=0398c71a selected_index=0 selected_addon=0 hover_slot=-1 action_state=1 scroll=(10,17)`
- line 200: `SURFDUMP_READY redraw_seq=981 surface=0a2fedb0 size=(800,600) base=0a5a0030 bytes=480000 SURFDUMP_HOST_READY`
