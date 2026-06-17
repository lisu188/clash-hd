# First Mission Visual Audit

- Overall: FAIL
- Generated: `2026-06-16T15:24:07+02:00`
- Runtime policy: repo-only PNG audit; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: first-mission frames must keep the play area rendered, avoid horizontal or vertical stripe signatures, and expose remaining large black UI patches as non-playable blockers instead of hiding them behind route success
- Current status: `first_mission_visual_playability_not_proven`
- First mission visual clean: `False`
- Primary frame: `current_bottom_edge`
- Primary play area nonblack: `97.21`%
- Primary selected action bar nonblack: `76.268`%
- Primary selected action bar mean luma: `64.666`
- Primary selected action bar visible: `False`
- Primary legacy middle action bar nonblack: `99.982`%
- Primary legacy middle action bar mean luma: `107.377`
- Primary legacy middle action bar visible: `False`
- Primary black patch regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Stripe failure frames: `[]`
- Diagnostic black frames: `[]`

## Frames

### current_bottom_edge

- Role: current_bottom_edge_selected_unit_frame
- Path: `captures\archive\cdb-surface-dump-20260616-152239\surface.png`
- Status: `black_patch_or_diagnostic_frame`
- Frame clean for playability: `False`
- Play area nonblack: `97.21`%
- Expected bottom action bar nonblack: `76.268`%
- Expected bottom action bar mean luma: `64.666`
- Expected bottom action bar visible: `False`
- Legacy middle action bar nonblack: `99.982`%
- Legacy middle action bar mean luma: `107.377`
- Legacy middle action bar visible: `False`
- Bottom tooltip black: `31.676`%
- Right below minimap black: `76.407`%
- Minimap interior black: `98.581`%
- Stripe pass: `True` horizontal_high=`0.587`% vertical_high=`0.542`%
- Black patch regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`

## Failures

- primary first-mission frame is not visually clean for playability: primary frame selected-unit action bar is not visible, black patch: right_below_minimap, black patch: bottom_right_panel, black patch: minimap_interior
