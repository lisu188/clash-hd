# Right-Bottom Grid Hit Probe Guard

- Overall: PASS
- Generated: `2026-07-13T08:53:43+02:00`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: focused right-bottom grid-hit proof must keep the owner/action/grid breakpoints, continue to prove native coordinate (450,73) returns grid cell 0, and stay hidden-desktop with no failure-exit or AV rows
- Expected stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- Expected entry/result: `[450, 73]` -> `0`

## Probe Script

- Status: PASS
- Script: `probes\cdb\ui\clash95_right_bottom_grid_hit_extra.cdb`

### Required Breakpoints

- `00433D5F`: PASS - right-bottom owner surface pointer write short-return
- `0040AE16`: PASS - debugger-routed owner/action sequence and surface-ready row
- `00433914`: PASS - action descriptor call into owner route
- `00433919`: PASS - post-owner return and fallback ready row
- `00435BC0`: PASS - right-bottom owner route entry
- `00435BCA`: PASS - right-bottom owner pointer write
- `00435C3E`: PASS - right-bottom hover-slot write
- `004347A0`: PASS - right-bottom panel draw
- `00434E20`: PASS - right-bottom grid draw
- `00435280`: PASS - right-bottom status draw
- `00435500`: PASS - right-bottom action-box draw
- `00435B90`: PASS - native grid coordinate injection
- `00435A00`: PASS - grid route entry
- `00435A0E`: PASS - grid gate result
- `00435A17`: PASS - grid hit-test call
- `00435580`: PASS - grid hit-test entry
- `0043560E`: PASS - grid hit-test result and accept
- `004355FF`: PASS - grid failure sentinel
- `00435A9A`: PASS - selection-update sentinel
- `00435AA0`: PASS - selection-after sentinel

### Required Markers

- `RBGRID_OWNER_SETUP_CALL`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_OWNER_FLAG_FORCED`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_WRITE_532154`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_ACTION_CALL`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_433914_CALL_435BC0`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_OWNER_435BC0_ENTRY`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_WRITE_532218`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_WRITE_5322C8`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_PANEL_DRAW_4347A0`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_GRID_DRAW_434E20`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_STATUS_DRAW_435280`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_ACTION_BOX_435500`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_FORCE_NATIVE`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_GRID_ROUTE_ENTRY`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_GRID_GATE`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_GRID_CALL`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_GRID_ENTRY`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_GRID_RESULT`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_GRID_ACCEPT`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_GRID_FAIL`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_FAIL_EXIT_ARM`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_SELECTION_UPDATE`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_SELECTION_AFTER`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_4338E0_AFTER_435BC0`: PASS - recognized right-bottom controlled grid-hit probe row
- `RBGRID_SURFDUMP_READY`: PASS - recognized right-bottom controlled grid-hit probe row
- `SURFDUMP_READY`: PASS - recognized right-bottom controlled grid-hit probe row

## Focused Grid-Hit Log

- Status: PASS
- Run: `captures\archive\cdb-surface-dump-20260712-150240`
- Log: `captures\archive\cdb-surface-dump-20260712-150240\cdb-surface-dump.log`
- Hidden desktop: `True`
- Allow visible desktop: `False`
- DirectDraw proxy: `True`
- Fast-forward startup: `True`
- Skip map validation: `True`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- Surface: `[800, 600]`
- Ready sizes: `[[800, 600], [800, 600]]`
- Grid hit ok: `True`
- Last grid entry: `[450, 73]`
- Last grid result: `0`
- Forced hidden flip gates: `1`
- Failure exits: `0`
- Draw rows: `5`
- Access violations: `0`
