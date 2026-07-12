# Right-Bottom Controlled Grid Hit Probe

- Log: `captures\archive\cdb-surface-dump-20260712-150240\cdb-surface-dump.log`
- Rows parsed: 23
- Access violations: 0
- Ready: True
- Expected grid entry: `[450, 73]`
- Last grid entry: `[450, 73]`
- Last grid result: `0`
- Grid hit ok: True
- Forced hidden flip gates: 1
- Failure exits: 0
- Draw rows: 5
- Selection updates: 0

## Classification

- native grid coordinate was installed by the probe
- right-bottom owner/action route entered 00435BC0
- right-bottom panel/grid/status/action drawing rows fired
- hidden-desktop DD flip gate was reached
- hidden-desktop DD flip gate was debugger-forced
- right-bottom grid hit-test was reached
- grid hit-test returned expected cell 0 at native coordinate (450, 73)
- grid result was accepted and the probe armed loop exit
- grid selection update was not observed
- surface dump reached ready state

## Diagnostic Screenshot

This CDB/proxy frame is hit-test/control-flow evidence only. Do not use it as visual acceptance proof for the final right-bottom action menu layout.

![right-bottom controlled grid hit](captures/archive/cdb-surface-dump-20260712-150240/surface.png)

## Key Rows

- line 211: `RBGRID_OWNER_435BC0_ENTRY ret=00433919 owner_arg=044fc71a d532218_before=00000000 d5322c8_before=0 d532210_before=0 surface=0a1cf1b0 sz=(800,600) mouse=(320,166)`
- line 211: `RBGRID_WRITE_532218 ret=00000000 new=044fc71a selected_index=0 hover_slot=0 surface=0a1cf1b0 sz=(800,600)`
- line 211: `RBGRID_WRITE_5322C8 ret=00000000 new=-1 d532218=044fc71a selected_index=0 surface=0a1cf1b0 sz=(800,600)`
- line 211: `RBGRID_PANEL_DRAW_4347A0 ret=00435d84 owner=044fc71a selected_index=0 hover_slot=-1 render=0a1cf1b0 map_surface=0a1cf1b0 sz=(800,600)`
- line 211: `RBGRID_GRID_DRAW_434E20 ret=00435172 owner=044fc71a selected_index=0 hover_slot=-1 render=0a1cf1b0 map_surface=0a1cf1b0 sz=(800,600)`
- line 211: `RBGRID_STATUS_DRAW_435280 ret=00435d8e owner=044fc71a selected_index=0 hover_slot=-1 mouse=(320,166) render=0a1cf1b0 map_surface=0a1cf1b0`
- line 211: `RBGRID_ACTION_BOX_435500 ret=00435d93 owner=044fc71a selected_index=0 hover_slot=-1 mouse=(320,166) render=0051d4c0 map_surface=0a1cf1b0`
- line 211: `RBGRID_FORCE_NATIVE target=grid0 native=(450,73) shift=6 raw=(00007080,00001240) selected_index=0 hover_slot=-1`
- line 211: `RBGRID_GRID_DRAW_434E20 ret=00435274 owner=044fc71a selected_index=0 hover_slot=-1 render=0051d4c0 map_surface=0a1cf1b0 sz=(800,600)`
- line 211: `RBGRID_GRID_ROUTE_ENTRY selected_index=0 hover_slot=-1 mouse=(450,73)`
- line 211: `RBGRID_GRID_GATE raw_result=0 forced_result=1 mouse=(450,73)`
- line 211: `RBGRID_GRID_CALL mouse=(450,73) raw=(00007080,00001240) expected_native=(450,73)`
- line 211: `RBGRID_GRID_ENTRY mouse=(450,73) raw=(00007080,00001240) expected_native=(450,73) shift=6 selected_index=0 hover_slot=-1`
- line 211: `RBGRID_GRID_RESULT result=0 expected=0 mouse=(450,73) selected_index=0 hover_slot=-1`
- line 211: `RBGRID_GRID_ACCEPT result=0 exit_armed=1 hover_slot=-1`
- line 211: `RBGRID_4338E0_AFTER_435BC0 ret=0040ae16 d532218=044fc71a selected_index=0 hover_slot=0 surface=0a1cf1b0 sz=(800,600)`
- line 211: `RBGRID_SURFDUMP_READY after_action=1 surface=0a1cf1b0 size=(800,600) base=0a470030 bytes=480000 d532150=044fc71a d532218=044fc71a selected_index=0 hover_slot=0 scroll=(10,17)`
- line 211: `SURFDUMP_READY redraw_seq=991 surface=0a1cf1b0 size=(800,600) base=0a470030 bytes=480000 SURFDUMP_HOST_READY`
