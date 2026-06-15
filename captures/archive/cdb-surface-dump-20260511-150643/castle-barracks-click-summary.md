# Castle Barracks Centered Hitbox Probe

- Log: `captures\cdb-surface-dump-20260511-150643\cdb-surface-dump.log`
- Rows parsed: 11
- Access violations: 0
- Last grid entry: `[450, 73]`
- Last grid result: `0`
- Raw grid gate ok: True
- Forced grid gates: 0
- Grid hit ok: True
- Selection updates: 0

## Classification

- forced centered coordinate was installed
- owner-poll wrapper transformed the coordinate to native space
- barracks grid hit-test was reached
- grid route gate passed from raw input/click state
- grid route gate was not debugger-forced
- grid hit-test returned expected cell 0 at native coordinate 450,73
- grid result was accepted and the probe armed loop exit
- grid selection update was not observed
- surface dump reached ready state

## Screenshot

![castle barracks centered hitbox](C:/Users/andrz/OneDrive/Pulpit/git/clash-hd/captures/cdb-surface-dump-20260511-150643/surface.png)

## Key Rows

- line 202: `APBARRACKS_HITBOX_FORCE_CENTERED target=grid0 centered=(530,133) expected_native=(450,73) shift=6 raw=(00008480,00002140) click_flag=00000001 button0=0x80 selected_index=0 selected_addon=0 hover_slot=-1`
- line 202: `APBARRACKS_HITBOX_OWNER_NATIVE mouse=(450,73) raw=(00007080,00001240) shift=6 selected_index=0 hover_slot=-1 click_flag=00000001 APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=03ebc71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a1bed90 sz=(800,600)`
- line 202: `APBARRACKS_HITBOX_OWNER_RESTORED mouse=(530,133) raw=(00008480,00002140) shift=6 selected_index=0 hover_slot=-1 click_flag=00000001`
- line 202: `APBARRACKS_HITBOX_DESCRIPTOR_RESULT result=0 mouse=(530,133) selected_index=0 hover_slot=-1 click_flag=00000000`
- line 202: `APBARRACKS_HITBOX_CLICK_STATE centered=(530,133) expected_native=(450,73) raw=(00008480,00002140) click_flag=00000001 button0=0x80 selected_index=0 hover_slot=-1 APBARRACKS_HITBOX_GRID_ROUTE_ENTRY selected_index=0 selected_addon=0 hover_slot=-1 mouse=(530,133)`
- line 202: `APBARRACKS_HITBOX_GRID_GATE raw_result=1 forced_result=none mouse=(530,133) click_flag=00000001 button0=0x80 APBARRACKS_HITBOX_GRID_CALL_WRAPPER mouse=(530,133) raw=(00008480,00002140) expected_centered=(530,133)`
- line 202: `APBARRACKS_HITBOX_GRID_ENTRY mouse=(450,73) raw=(00007080,00001240) expected_native=(450,73) shift=6 selected_index=0 hover_slot=-1`
- line 202: `APBARRACKS_HITBOX_GRID_RESULT result=0 expected=0 mouse=(450,73) selected_index=0 hover_slot=-1`
- line 202: `APBARRACKS_HITBOX_GRID_ACCEPT result=0 exit_armed=1 hover_slot=-1 raw_gate=passed APBARRACKS_4338E0_AFTER_435BC0 ret=0040ae16 d532218=03ebc71a selected_index=0 selected_addon=0 hover_slot=0 surface=0a1bed90 sz=(800,600)`
- line 202: `APBARRACKS_SURFDUMP_READY after_action=1 surface=0a1bed90 size=(800,600) base=0a460030 bytes=480000 d532150=03ebc71a d532218=03ebc71a selected_index=0 selected_addon=0 hover_slot=0 scroll=(10,17)`
- line 202: `SURFDUMP_READY redraw_seq=971 surface=0a1bed90 size=(800,600) base=0a460030 bytes=480000 SURFDUMP_HOST_READY`
