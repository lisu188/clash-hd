# Castle Barracks Centered Hitbox Probe

- Log: `captures\cdb-surface-dump-20260511-144739\cdb-surface-dump.log`
- Rows parsed: 10
- Access violations: 0
- Last grid entry: `None`
- Last grid result: `None`
- Grid hit ok: False
- Selection updates: 0

## Classification

- forced centered coordinate was installed
- owner-poll wrapper transformed the coordinate to native space
- barracks grid hit-test was not reached
- grid hit-test did not prove expected cell 0 at native coordinate 450,73
- grid selection update was not observed
- surface dump reached ready state

## Screenshot

![castle barracks centered hitbox](C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\cdb-surface-dump-20260511-144739\surface.png)

## Key Rows

- line 204: `APBARRACKS_HITBOX_FORCE_CENTERED target=grid0 centered=(530,133) expected_native=(450,73) shift=6 raw=(00008480,00002140) selected_index=0 selected_addon=0 hover_slot=-1`
- line 204: `APBARRACKS_HITBOX_OWNER_NATIVE mouse=(450,73) raw=(00007080,00001240) shift=6 selected_index=0 hover_slot=-1 APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=03adc71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a2fedb0 sz=(800,600)`
- line 204: `APBARRACKS_HITBOX_OWNER_RESTORED mouse=(530,133) raw=(00008480,00002140) shift=6 selected_index=0 hover_slot=-1`
- line 204: `APBARRACKS_HITBOX_DESCRIPTOR_RESULT result=0 mouse=(530,133) selected_index=0 hover_slot=-1`
- line 204: `APBARRACKS_HITBOX_EXIT_ARM selected_index=0 selected_addon=0 hover_slot=-1 mouse=(4,133)`
- line 204: `APBARRACKS_HITBOX_OWNER_NATIVE mouse=(-76,73) raw=(ffffed00,00001240) shift=6 selected_index=0 hover_slot=-1`
- line 204: `APBARRACKS_HITBOX_OWNER_RESTORED mouse=(4,133) raw=(00000100,00002140) shift=6 selected_index=0 hover_slot=-1`
- line 204: `APBARRACKS_HITBOX_DESCRIPTOR_RESULT result=0 mouse=(4,133) selected_index=0 hover_slot=-1 APBARRACKS_4338E0_AFTER_435BC0 ret=0040ae16 d532218=03adc71a selected_index=0 selected_addon=0 hover_slot=-1 surface=0a2fedb0 sz=(800,600)`
- line 204: `APBARRACKS_SURFDUMP_READY after_action=1 surface=0a2fedb0 size=(800,600) base=0a5a0030 bytes=480000 d532150=03adc71a d532218=03adc71a selected_index=0 selected_addon=0 hover_slot=-1 scroll=(10,17)`
- line 204: `SURFDUMP_READY redraw_seq=961 surface=0a2fedb0 size=(800,600) base=0a5a0030 bytes=480000 SURFDUMP_HOST_READY`
