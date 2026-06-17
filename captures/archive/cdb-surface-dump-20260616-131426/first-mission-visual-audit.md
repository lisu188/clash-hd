# First Mission Visual Audit

- Overall: FAIL
- Generated: `2026-06-16T13:16:46+02:00`
- Runtime policy: repo-only PNG audit; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: first-mission frames must keep the play area rendered, avoid horizontal or vertical stripe signatures, and expose remaining large black UI patches as non-playable blockers instead of hiding them behind route success
- Current status: `selected_unit_action_bar_on_bottom_but_black_ui_patches_remain`
- First mission visual clean: `False`
- Primary frame: `post_redraw_action_bar_bottom_rerun`
- Primary play area nonblack: `97.21`%
- Primary selected action bar nonblack: `96.461`%
- Primary selected action bar mean luma: `89.549`
- Primary selected action bar visible: `True`
- Primary legacy middle action bar nonblack: `99.982`%
- Primary legacy middle action bar mean luma: `102.651`
- Primary legacy middle action bar visible: `False`
- Primary black patch regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Stripe failure frames: `[]`
- Diagnostic black frames: `[]`

## Frames

### post_redraw_action_bar_bottom_rerun

- Role: fresh corrected bottom action-bar frame
- Path: `captures\archive\cdb-surface-dump-20260616-131426\surface.png`
- Status: `black_patch_or_diagnostic_frame`
- Frame clean for playability: `False`
- Play area nonblack: `97.21`%
- Expected bottom action bar nonblack: `96.461`%
- Expected bottom action bar mean luma: `89.549`
- Expected bottom action bar visible: `True`
- Legacy middle action bar nonblack: `99.982`%
- Legacy middle action bar mean luma: `102.651`
- Legacy middle action bar visible: `False`
- Bottom tooltip black: `32.536`%
- Right below minimap black: `76.407`%
- Minimap interior black: `98.581`%
- Stripe pass: `True` horizontal_high=`0.783`% vertical_high=`0.542`%
- Black patch regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`

## Failures

- primary first-mission frame is not visually clean for playability: black patch: right_below_minimap, black patch: bottom_right_panel, black patch: minimap_interior
