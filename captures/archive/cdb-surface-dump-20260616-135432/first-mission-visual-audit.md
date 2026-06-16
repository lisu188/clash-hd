# First Mission Visual Audit

- Overall: FAIL
- Generated: `2026-06-16T13:55:43+02:00`
- Runtime policy: repo-only PNG audit; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: first-mission frames must keep the play area rendered, avoid horizontal or vertical stripe signatures, and expose remaining large black UI patches as non-playable blockers instead of hiding them behind route success
- Current status: `first_mission_visual_playability_not_proven`
- First mission visual clean: `False`
- Primary frame: `combined_controlled_postowner`
- Primary play area nonblack: `73.723`%
- Primary selected action bar nonblack: `75.161`%
- Primary selected action bar mean luma: `121.914`
- Primary selected action bar visible: `False`
- Primary legacy middle action bar nonblack: `94.293`%
- Primary legacy middle action bar mean luma: `141.202`
- Primary legacy middle action bar visible: `False`
- Primary black patch regions: `[]`
- Stripe failure frames: `['combined_controlled_postowner']`
- Diagnostic black frames: `['combined_controlled_postowner']`

## Frames

### combined_controlled_postowner

- Role: combined_validation_controlled_postowner_frame
- Path: `captures\archive\cdb-surface-dump-20260616-135432\surface.png`
- Status: `black_patch_or_diagnostic_frame`
- Frame clean for playability: `False`
- Play area nonblack: `73.723`%
- Expected bottom action bar nonblack: `75.161`%
- Expected bottom action bar mean luma: `121.914`
- Expected bottom action bar visible: `False`
- Legacy middle action bar nonblack: `94.293`%
- Legacy middle action bar mean luma: `141.202`
- Legacy middle action bar visible: `False`
- Bottom tooltip black: `39.14`%
- Right below minimap black: `56.42`%
- Minimap interior black: `37.645`%
- Stripe pass: `False` horizontal_high=`37.378`% vertical_high=`0.181`%
- Black patch regions: `[]`

## Failures

- primary first-mission frame is not visually clean for playability: play area is mostly black or missing, primary frame selected-unit action bar is not visible, stripe signature detected in play area
- stripe signatures detected: ['combined_controlled_postowner']
