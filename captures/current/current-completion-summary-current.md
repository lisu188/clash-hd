# Current Completion Summary

- Overall: PASS
- Generated: `2026-07-12T20:48:02+02:00`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Percent policy: Percentages are computed from generated evidence gates and checklist counts. They are progress indicators, not a claim that full-game reverse engineering is complete.
- Full game complete: `False`
- Full game percent statement: not 100%; manual DirectInput proof, stable promotion, endurance soaks, continuity, and current visual blockers remain open

## Percentages

- Current repo evidence gates: `90.26%`
  Basis: 139/154 refresh checks pass
- Repo-only Python test sweep: `100.00%`
  Basis: 92/92 tools/test_*.py files pass
- Focused battle/right-bottom command lane: `99.89%`
  Basis: remaining blocker: real visible click-to-callback proof (command-ready runs: 0; click-consumed runs: 0)
- Right-bottom promotion gate: `85.71%`
  Basis: 6/7 required promotion checks pass
- Manual DirectInput validation: `0.00%`
  Basis: 0/5 manual checklist items have accepted proof

## Remaining Blockers

- Manual DirectInput pending IDs: `['stable_menu_load', 'stable_hd_map_input', 'right_bottom_validation_input', 'castle_barracks_centered_input', 'castle_overview_centered_input']`
- First mission visual status: `selected_unit_action_bar_on_bottom_but_black_ui_patches_remain`
- First mission black patch regions: `['right_below_minimap', 'bottom_right_panel', 'minimap_interior']`
- First mission stripe failure frames: `[]`
- Right-bottom failures: `['right_bottom_compose_ui_probe: right-bottom compose UI wrapper reported failure', 'right_bottom_compose_ui_probe: right-bottom compose UI descriptor switch rows were not observed', 'right_bottom_compose_ui_probe: right-bottom compose UI did not naturally enter owner/action draw rows', 'right-bottom natural UI probe did not enter owner/action draw rows']`
- Battle open items: `['real visible click-to-callback proof remains open']`
