# Castle Barracks UI Probe

- Log: `captures\cdb-surface-dump-20260511-084202\cdb-surface-dump.log`
- Rows parsed: 18
- Access violations: 0
- Last selected addon id: 0

## Classification

- owner setup globals were installed for the castle action path
- castle action-panel routine 00435BC0 was reached
- detail panel and 12-slot grid draw functions executed
- bottom action box draw function executed
- surface dump reached ready state

## Marker Counts

- APBARRACKS_OWNER_SETUP_CALL: 1
- APBARRACKS_OWNER_FLAG_FORCED: 1
- APBARRACKS_433C20_ENTRY: 0
- APBARRACKS_WRITE_532150: 1
- APBARRACKS_WRITE_53214C: 1
- APBARRACKS_WRITE_532154: 1
- APBARRACKS_ACTION_CALL: 1
- APBARRACKS_433914_CALL_435BC0: 1
- APBARRACKS_OWNER_435BC0_ENTRY: 1
- APBARRACKS_WRITE_532218: 1
- APBARRACKS_WRITE_5322C8: 1
- APBARRACKS_PANEL_DRAW_4347A0: 1
- APBARRACKS_GRID_DRAW_434E20: 2
- APBARRACKS_STATUS_DRAW_435280: 1
- APBARRACKS_ACTION_BOX_435500: 1
- APBARRACKS_OWNER_POLL_EXIT_ARM: 1
- APBARRACKS_SURFDUMP_READY: 1
- SURFDUMP_READY: 1

## Screenshot

![castle barracks UI](C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\cdb-surface-dump-20260511-084202\surface.png)

## Key Rows

- line 204: `APBARRACKS_433914_CALL_435BC0 ret=0040ae16 owner_arg=03fdc71a owner_global=03fdc71a owner_flag=0x02 d532218=00000000 d5322c8=0 surface=0a07ed90 sz=(800,600)`
- line 204: `APBARRACKS_OWNER_435BC0_ENTRY ret=00433919 owner_arg=03fdc71a d532218_before=00000000 d5322c8_before=0 d532210_before=0 surface=0a07ed90 sz=(800,600) mouse=(320,166)`
- line 204: `APBARRACKS_WRITE_532218 ret=00000000 new=03fdc71a selected_index=0 hover_slot=0 surface=0a07ed90 sz=(800,600)`
- line 204: `APBARRACKS_WRITE_5322C8 ret=00000000 new=-1 d532218=03fdc71a selected_index=0 surface=0a07ed90 sz=(800,600)`
- line 204: `APBARRACKS_PANEL_DRAW_4347A0 ret=00435d84 owner=03fdc71a selected_index=0 selected_addon=0 list=(0,1,3,16,17,-1,-1,-1,-1,-1,-1,-1) slots=(00,ff,ff,ff,ff,ff,ff,ff,ff,ff,ff,ff) render=0a07ed90 map_surface=0a07ed90 sz=(800,600)`
- line 204: `APBARRACKS_GRID_DRAW_434E20 ret=00435172 owner=03fdc71a selected_index=0 selected_addon=0 hover_slot=-1 render=0a07ed90 map_surface=0a07ed90 sz=(800,600)`
- line 204: `APBARRACKS_STATUS_DRAW_435280 ret=00435d8e owner=03fdc71a selected_index=0 selected_addon=0 hover_slot=-1 mouse=(320,166) render=0a07ed90 map_surface=0a07ed90`
- line 204: `APBARRACKS_ACTION_BOX_435500 ret=00435d93 owner=03fdc71a selected_index=0 selected_addon=0 hover_slot=-1 mouse=(320,166) render=0051d4c0 map_surface=0a07ed90 scratch=0051d4c0 scratch_sz=(800,600) scratch_base=00000000 map_base=0a320030`
- line 204: `APBARRACKS_OWNER_POLL_EXIT_ARM ret=00435de3 owner=03fdc71a selected_index=0 selected_addon=0 hover_slot=-1 d532210=1 mouse=(4,166)`
- line 204: `APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=03fdc71a selected_index=0 selected_addon=0 hover_slot=-1 render=0051d4c0 map_surface=0a07ed90 sz=(800,600) APBARRACKS_4338E0_AFTER_435BC0 ret=0040ae16 d532218=03fdc71a selected_index=0 selected_addon=0 hover_slot=-1 surface=0a07ed90 sz=(800,600)`
- line 204: `APBARRACKS_SURFDUMP_READY after_action=1 surface=0a07ed90 size=(800,600) base=0a320030 bytes=480000 d532150=03fdc71a d532218=03fdc71a selected_index=0 selected_addon=0 hover_slot=-1 scroll=(10,17)`
- line 204: `SURFDUMP_READY redraw_seq=961 surface=0a07ed90 size=(800,600) base=0a320030 bytes=480000 SURFDUMP_HOST_READY`
