# First Mission Visual Audit

- Overall: FAIL
- Generated: `2026-06-16T14:09:07+02:00`
- Runtime policy: repo-only PNG audit; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: first-mission frames must keep the play area rendered, avoid horizontal or vertical stripe signatures, and expose remaining large black UI patches as non-playable blockers instead of hiding them behind route success
- Current status: `first_mission_visual_playability_not_proven`
- First mission visual clean: `False`
- Primary frame: `stable_minimap_probe`
- Primary play area nonblack: `0.0`%
- Primary selected action bar nonblack: `0.0`%
- Primary selected action bar mean luma: `0.0`
- Primary selected action bar visible: `False`
- Primary legacy middle action bar nonblack: `0.0`%
- Primary legacy middle action bar mean luma: `0.0`
- Primary legacy middle action bar visible: `False`
- Primary black patch regions: `['bottom_right_panel', 'minimap_interior']`
- Stripe failure frames: `[]`
- Diagnostic black frames: `['stable_minimap_probe']`

## Frames

### stable_minimap_probe

- Role: stable_minimap_topband_probe
- Path: `captures\archive\cdb-surface-dump-20260616-140819\surface.png`
- Status: `black_patch_or_diagnostic_frame`
- Frame clean for playability: `False`
- Play area nonblack: `0.0`%
- Expected bottom action bar nonblack: `0.0`%
- Expected bottom action bar mean luma: `0.0`
- Expected bottom action bar visible: `False`
- Legacy middle action bar nonblack: `0.0`%
- Legacy middle action bar mean luma: `0.0`
- Legacy middle action bar visible: `False`
- Bottom tooltip black: `100.0`%
- Right below minimap black: `50.88`%
- Minimap interior black: `98.561`%
- Stripe pass: `True` horizontal_high=`0.0`% vertical_high=`0.0`%
- Black patch regions: `['bottom_right_panel', 'minimap_interior']`

## Failures

- primary first-mission frame is not visually clean for playability: play area is mostly black or missing, primary frame selected-unit action bar is not visible, black patch: bottom_right_panel, black patch: minimap_interior
