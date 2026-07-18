# First Mission Visual Audit

- Overall: PASS
- Generated: `2026-07-18T10:41:55+02:00`
- Runtime policy: repo-only PNG audit; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: first-mission frames must keep the play area rendered, avoid horizontal or vertical stripe signatures, and expose unexplained large black UI patches as non-playable blockers; a raw proxy-black region is classified as a capture artifact only when a supplied real-runtime frame positively corroborates it
- Corroboration method: per-region render-presence corroboration; not a same-state pixel comparison
- Real-runtime corroboration frame: `captures\archive\visual-smoke-20260712-202900\after-map-path.png`
- Real-runtime corroboration frame present: `True`
- Corroborated rendered regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Current status: `selected_unit_action_bar_on_bottom_black_patches_are_proxy_artifacts`
- First mission visual clean: `True`
- Primary frame: `centered_bottom_edge_panel`
- Primary frame path: `captures\archive\cdb-surface-dump-20260616-153751\surface.png`
- Next probe: rerun first_mission_visual_audit.py after the next first-mission visual evidence refresh
- Primary play area nonblack: `97.21`%
- Primary selected action bar nonblack: `91.954`%
- Primary selected action bar mean luma: `66.995`
- Primary selected action bar visible: `True`
- Primary legacy middle action bar nonblack: `99.982`%
- Primary legacy middle action bar mean luma: `107.377`
- Primary legacy middle action bar visible: `False`
- Primary raw proxy-black regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Confirmed proxy-artifact regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Primary unresolved black patch regions: `[]`
- Stripe failure frames: `[]`
- Diagnostic black frames: `['tooltip_owner_probe', 'hover_selection_probe', 'combined_tooltip_action_bar']`

## Real-Runtime Corroboration

- `right_below_minimap` scaled_rect=`[879, 345, 1198, 898]` real_black=`1.794`% real_nonblack=`98.206`% corroborated_rendered=`True`
- `bottom_right_panel` scaled_rect=`[879, 792, 1198, 898]` real_black=`9.287`% real_nonblack=`90.713`% corroborated_rendered=`True`
- `minimap_interior` scaled_rect=`[891, 36, 1189, 330]` real_black=`0.0`% real_nonblack=`100.0`% corroborated_rendered=`True`

## Frames

### baseline_selection

- Role: baseline first-mission selected-unit route
- Path: `captures\archive\cdb-surface-dump-20260527-092117\surface.png`
- Status: `black_patch_or_diagnostic_frame`
- Frame clean for playability: `False`
- Play area nonblack: `97.21`%
- Expected bottom action bar nonblack: `60.0`%
- Expected bottom action bar mean luma: `63.506`
- Expected bottom action bar visible: `False`
- Legacy middle action bar nonblack: `99.982`%
- Legacy middle action bar mean luma: `107.377`
- Legacy middle action bar visible: `False`
- Bottom tooltip black: `32.539`%
- Right below minimap black: `76.407`%
- Minimap interior black: `98.581`%
- Stripe pass: `True` horizontal_high=`0.587`% vertical_high=`0.542`%
- Raw proxy-black regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Confirmed proxy-artifact regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Unresolved black patch regions: `[]`

### pre_redraw_action_bar

- Role: pre-redraw selected-unit action-bar recovery
- Path: `captures\archive\cdb-surface-dump-20260527-100641\surface.png`
- Status: `black_patch_or_diagnostic_frame`
- Frame clean for playability: `False`
- Play area nonblack: `97.21`%
- Expected bottom action bar nonblack: `60.0`%
- Expected bottom action bar mean luma: `63.506`
- Expected bottom action bar visible: `False`
- Legacy middle action bar nonblack: `99.982`%
- Legacy middle action bar mean luma: `92.244`
- Legacy middle action bar visible: `True`
- Bottom tooltip black: `32.539`%
- Right below minimap black: `76.407`%
- Minimap interior black: `98.581`%
- Stripe pass: `True` horizontal_high=`0.783`% vertical_high=`0.542`%
- Raw proxy-black regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Confirmed proxy-artifact regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Unresolved black patch regions: `[]`

### tooltip_owner_probe

- Role: bottom-tooltip owner diagnostic
- Path: `captures\archive\cdb-surface-dump-20260527-101402\surface.png`
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
- Raw proxy-black regions: `['bottom_right_panel', 'minimap_interior']`
- Confirmed proxy-artifact regions: `['bottom_right_panel', 'minimap_interior']`
- Unresolved black patch regions: `[]`

### hover_selection_probe

- Role: hover/selection diagnostic
- Path: `captures\archive\cdb-surface-dump-20260527-101727\surface.png`
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
- Right below minimap black: `100.0`%
- Minimap interior black: `98.515`%
- Stripe pass: `True` horizontal_high=`0.0`% vertical_high=`0.0`%
- Raw proxy-black regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Confirmed proxy-artifact regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Unresolved black patch regions: `[]`

### combined_tooltip_action_bar

- Role: combined tooltip/action-bar diagnostic before post-redraw fix
- Path: `captures\archive\cdb-surface-dump-20260527-111658\surface.png`
- Status: `black_patch_or_diagnostic_frame`
- Frame clean for playability: `False`
- Play area nonblack: `0.0`%
- Expected bottom action bar nonblack: `60.0`%
- Expected bottom action bar mean luma: `63.506`
- Expected bottom action bar visible: `False`
- Legacy middle action bar nonblack: `0.0`%
- Legacy middle action bar mean luma: `0.0`
- Legacy middle action bar visible: `False`
- Bottom tooltip black: `32.539`%
- Right below minimap black: `95.83`%
- Minimap interior black: `98.561`%
- Stripe pass: `True` horizontal_high=`0.0`% vertical_high=`0.0`%
- Raw proxy-black regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Confirmed proxy-artifact regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Unresolved black patch regions: `[]`

### post_redraw_action_bar

- Role: legacy lower-map post-redraw action-bar frame
- Path: `captures\archive\cdb-surface-dump-20260527-114559\surface.png`
- Status: `black_patch_or_diagnostic_frame`
- Frame clean for playability: `False`
- Play area nonblack: `97.21`%
- Expected bottom action bar nonblack: `60.0`%
- Expected bottom action bar mean luma: `63.506`
- Expected bottom action bar visible: `False`
- Legacy middle action bar nonblack: `99.982`%
- Legacy middle action bar mean luma: `92.244`
- Legacy middle action bar visible: `True`
- Bottom tooltip black: `32.539`%
- Right below minimap black: `76.407`%
- Minimap interior black: `98.581`%
- Stripe pass: `True` horizontal_high=`0.783`% vertical_high=`0.542`%
- Raw proxy-black regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Confirmed proxy-artifact regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Unresolved black patch regions: `[]`

### post_redraw_action_bar_bottom_gauge

- Role: current first-mission bottom action-bar and gauge frame
- Path: `captures\archive\cdb-surface-dump-20260616-133855\surface.png`
- Status: `black_patch_or_diagnostic_frame`
- Frame clean for playability: `False`
- Play area nonblack: `97.21`%
- Expected bottom action bar nonblack: `60.0`%
- Expected bottom action bar mean luma: `63.506`
- Expected bottom action bar visible: `False`
- Legacy middle action bar nonblack: `99.982`%
- Legacy middle action bar mean luma: `107.377`
- Legacy middle action bar visible: `False`
- Bottom tooltip black: `32.536`%
- Right below minimap black: `76.407`%
- Minimap interior black: `98.581`%
- Stripe pass: `True` horizontal_high=`0.587`% vertical_high=`0.542`%
- Raw proxy-black regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Confirmed proxy-artifact regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Unresolved black patch regions: `[]`

### combined_natural_unit

- Role: current combined-stage natural selected-unit frame
- Path: `captures\archive\cdb-surface-dump-20260616-135148\surface.png`
- Status: `black_patch_or_diagnostic_frame`
- Frame clean for playability: `False`
- Play area nonblack: `97.21`%
- Expected bottom action bar nonblack: `60.0`%
- Expected bottom action bar mean luma: `63.506`
- Expected bottom action bar visible: `False`
- Legacy middle action bar nonblack: `99.982`%
- Legacy middle action bar mean luma: `107.377`
- Legacy middle action bar visible: `False`
- Bottom tooltip black: `32.536`%
- Right below minimap black: `76.407`%
- Minimap interior black: `98.581`%
- Stripe pass: `True` horizontal_high=`0.587`% vertical_high=`0.542`%
- Raw proxy-black regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Confirmed proxy-artifact regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Unresolved black patch regions: `[]`

### combined_minimap_surface_probe

- Role: current combined-stage selected-unit frame with minimap backing samples
- Path: `captures\archive\cdb-surface-dump-20260616-141733\surface.png`
- Status: `black_patch_or_diagnostic_frame`
- Frame clean for playability: `False`
- Play area nonblack: `97.21`%
- Expected bottom action bar nonblack: `60.0`%
- Expected bottom action bar mean luma: `63.506`
- Expected bottom action bar visible: `False`
- Legacy middle action bar nonblack: `99.982`%
- Legacy middle action bar mean luma: `107.377`
- Legacy middle action bar visible: `False`
- Bottom tooltip black: `32.536`%
- Right below minimap black: `76.407`%
- Minimap interior black: `98.581`%
- Stripe pass: `True` horizontal_high=`0.587`% vertical_high=`0.542`%
- Raw proxy-black regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Confirmed proxy-artifact regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Unresolved black patch regions: `[]`

### bottom_edge_panel_only

- Role: current bottom-edge selected-unit panel frame
- Path: `captures\archive\cdb-surface-dump-20260616-153155\surface.png`
- Status: `visual_clean_candidate`
- Frame clean for playability: `True`
- Play area nonblack: `97.21`%
- Expected bottom action bar nonblack: `86.617`%
- Expected bottom action bar mean luma: `66.211`
- Expected bottom action bar visible: `True`
- Legacy middle action bar nonblack: `99.982`%
- Legacy middle action bar mean luma: `107.377`
- Legacy middle action bar visible: `False`
- Bottom tooltip black: `25.231`%
- Right below minimap black: `76.407`%
- Minimap interior black: `98.581`%
- Stripe pass: `True` horizontal_high=`0.587`% vertical_high=`0.542`%
- Raw proxy-black regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Confirmed proxy-artifact regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Unresolved black patch regions: `[]`

### centered_bottom_edge_panel

- Role: current centered bottom-edge selected-unit panel frame
- Path: `captures\archive\cdb-surface-dump-20260616-153751\surface.png`
- Status: `visual_clean_candidate`
- Frame clean for playability: `True`
- Play area nonblack: `97.21`%
- Expected bottom action bar nonblack: `91.954`%
- Expected bottom action bar mean luma: `66.995`
- Expected bottom action bar visible: `True`
- Legacy middle action bar nonblack: `99.982`%
- Legacy middle action bar mean luma: `107.377`
- Legacy middle action bar visible: `False`
- Bottom tooltip black: `26.594`%
- Right below minimap black: `76.407`%
- Minimap interior black: `98.581`%
- Stripe pass: `True` horizontal_high=`0.587`% vertical_high=`0.542`%
- Raw proxy-black regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Confirmed proxy-artifact regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- Unresolved black patch regions: `[]`
