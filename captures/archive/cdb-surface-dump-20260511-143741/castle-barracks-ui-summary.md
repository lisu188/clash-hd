# Castle Barracks UI Probe

- Log: `captures\cdb-surface-dump-20260511-143741\cdb-surface-dump.log`
- Rows parsed: 25
- Access violations: 0
- Last selected addon id: 1

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
- APBARRACKS_SELECT_FORCED: 1
- APBARRACKS_PANEL_DRAW_4347A0: 1
- APBARRACKS_GRID_DRAW_434E20: 2
- APBARRACKS_STATUS_DRAW_435280: 1
- APBARRACKS_ACTION_BOX_435500: 1
- APBARRACKS_ACTION_BOX_SET_TARGET: 1
- APBARRACKS_ACTION_BOX_AFTER_BACKUP: 1
- APBARRACKS_ACTION_BOX_BEFORE_RESTORE: 1
- APBARRACKS_AFTER_ACTION_BOX: 1
- APBARRACKS_COPYBACK_SET_TARGET: 1
- APBARRACKS_COPYBACK_AFTER_CALL: 1
- APBARRACKS_OWNER_POLL_EXIT_ARM: 1
- APBARRACKS_SURFDUMP_READY: 1
- SURFDUMP_READY: 1

## Screenshot

![castle barracks UI](C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\cdb-surface-dump-20260511-143741\surface.png)

## Key Rows

- line 204: `APBARRACKS_STATUS_DRAW_435280 ret=00435d8e owner=0395c71a selected_index=1 selected_addon=1 hover_slot=-1 mouse=(320,166) render=0a1bed90 map_surface=0a1bed90`
- line 204: `APBARRACKS_ACTION_BOX_435500 ret=00435d93 owner=0395c71a selected_index=1 selected_addon=1 hover_slot=-1 mouse=(320,166) render=0051d4c0 map_surface=0a1bed90 scratch=0051d4c0 scratch_sz=(800,600) scratch_base=00000000 map_base=0a460030`
- line 204: `APBARRACKS_ACTION_BOX_SET_TARGET ret=0000015e prior_render=0051d4c0 scratch=0051d4c0 map_surface=0a1bed90 scratch_sz=(800,600) map_sz=(800,600)`
- line 204: `APBARRACKS_ACTION_BOX_AFTER_BACKUP ret=0050ee24 current_render=0051d4c0 map_surface=0a1bed90 map_samples=(c1,01,01) scratch_samples=(00,66,93)`
- line 204: `APBARRACKS_ACTION_BOX_BEFORE_RESTORE ret=0050ee24 current_render=0051d4c0 restore_to=0051d4c0 map_surface=0a1bed90 map_samples=(c1,01,01) scratch_samples=(00,66,93)`
- line 204: `APBARRACKS_AFTER_ACTION_BOX ret=00000001 render=0051d4c0 scratch=0051d4c0 map_surface=0a1bed90 d53221c=0a4eb9d8 map_samples=(c1,01,01) scratch_samples=(00,66,93)`
- line 204: `APBARRACKS_COPYBACK_SET_TARGET ret=00000001 eax=0051d4c0 d53221c=0a4eb9d8 map_surface=0a1bed90 map_samples=(c1,01,01) scratch_samples=(00,66,93)`
- line 204: `APBARRACKS_COPYBACK_AFTER_CALL ret=00000001 map_surface=0a1bed90 map_samples=(c1,01,01) scratch_samples=(00,66,93)`
- line 204: `APBARRACKS_OWNER_POLL_EXIT_ARM ret=00435de3 owner=0395c71a selected_index=1 selected_addon=1 hover_slot=-1 d532210=1 mouse=(4,166)`
- line 204: `APBARRACKS_GRID_DRAW_434E20 ret=00435274 owner=0395c71a selected_index=1 selected_addon=1 hover_slot=-1 render=0051d4c0 map_surface=0a1bed90 sz=(800,600) APBARRACKS_4338E0_AFTER_435BC0 ret=0040ae16 d532218=0395c71a selected_index=1 selected_addon=1 hover_slot=-1 surface=0a1bed90 sz=(800,600)`
- line 204: `APBARRACKS_SURFDUMP_READY after_action=1 surface=0a1bed90 size=(800,600) base=0a460030 bytes=480000 d532150=0395c71a d532218=0395c71a selected_index=1 selected_addon=1 hover_slot=-1 scroll=(10,17)`
- line 204: `SURFDUMP_READY redraw_seq=961 surface=0a1bed90 size=(800,600) base=0a460030 bytes=480000 SURFDUMP_HOST_READY`
