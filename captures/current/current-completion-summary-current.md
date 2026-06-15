# Current Completion Summary

- Overall: PASS
- Generated: `2026-06-15T22:36:20+02:00`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Percent policy: Percentages are computed from generated evidence gates and checklist counts. They are progress indicators, not a claim that full-game reverse engineering is complete.
- Full game complete: `False`
- Full game percent statement: not 100%; manual DirectInput proof and stable promotion remain blocked

## Percentages

- Current repo evidence gates: `88.97%`
  Basis: 121/136 refresh checks pass
- Focused battle/right-bottom command lane: `99.91%`
  Basis: remaining blocker: real visible click-to-callback proof (command-ready runs: 2; click-consumed runs: 0; invalid runs retained: 1)
- Right-bottom promotion gate: `85.71%`
  Basis: 6/7 required promotion checks pass
- Manual DirectInput validation: `0.00%`
  Basis: 0/5 manual checklist items have accepted proof

## Remaining Blockers

- Manual DirectInput pending IDs: `['stable_menu_load', 'stable_hd_map_input', 'right_bottom_validation_input', 'castle_barracks_centered_input', 'castle_overview_centered_input']`
- Right-bottom failures: `['right_bottom_compose_ui_probe: right-bottom compose UI did not naturally enter owner/action draw rows', 'right-bottom natural UI probe did not enter owner/action draw rows']`
- Battle open items: `['real visible click-to-callback proof remains open', '1 invalid visible-input run(s) are retained as negative evidence']`
