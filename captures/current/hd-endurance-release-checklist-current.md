# HD Endurance Release Checklist

- Overall: FAIL
- Generated: `2026-07-18T08:18:23.972328+00:00`
- Runtime policy: repo-only endurance release checklist; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Protected stable stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Full game complete: `False`
- Completion statement: not 100%; endurance, manual input, state continuity, or validation-route gates remain open
- Counts: `9/15` pass, `6` blocked, `0` missing

## Next Milestone

- `stable_menu_real_input`: Stable menu load has real input proof
- Next probe: collect approved manual menu-load proof or keep promotion blocked

## Requirements

- `protected_stable_stage`: `pass` - default stage and validation-only group boundary are intact
- `current_no_popup_map`: `pass` - hidden/no-popup map evidence still passes
- `first_mission_visual_clean`: `pass` - first-mission selected-unit frame is visually clean
- `short2_menu_idle_soak`: `pass` - canonical short2 menu-idle step status passes
  Canonical report: `captures\current\hd-soak-short2-menu-idle-current.json` present=`True`; guard: `captures\current\hd-soak-short2-menu-idle-guard-current.json` present=`True`; triage: `captures\current\hd-soak-short2-menu-idle-triage-current.json` present=`True`
- `long_soak_representative_routes`: `blocked` - 2h+ representative-route soak blocked (locked_short_ladder_incomplete): 2h+ representative-route soak evidence is locked or missing
- `stable_menu_real_input`: `blocked` - menu-load proof remains pending manual DirectInput validation
- `stable_hd_map_real_input`: `blocked` - HD map input proof remains pending manual DirectInput validation
- `right_bottom_action_menu`: `blocked` - right-bottom action/menu remains validation-only or manual-proof blocked
- `castle_and_barracks_centered_input`: `blocked` - castle/barracks centered input remains validation-only or manual-proof blocked
- `tactical_battle_entry_return`: `blocked` - battle evidence remains validation-only or missing visible click-to-callback proof
- `save_load_roundtrip`: `pass` - save/load continuity proof passes
- `turn_advancement`: `pass` - turn advancement proof passes
- `campaign_routes`: `pass` - campaign route proof passes
- `artifact_and_process_hygiene`: `pass` - artifact and process hygiene guards pass
- `no_speculative_promotion`: `pass` - stable-stage boundary remains unchanged while validation-only lanes stay non-promoting

## Open Items

- long_soak_representative_routes: 2h+ representative-route soak blocked (locked_short_ladder_incomplete): 2h+ representative-route soak evidence is locked or missing
- stable_menu_real_input: menu-load proof remains pending manual DirectInput validation
- stable_hd_map_real_input: HD map input proof remains pending manual DirectInput validation
- right_bottom_action_menu: right-bottom action/menu remains validation-only or manual-proof blocked
- castle_and_barracks_centered_input: castle/barracks centered input remains validation-only or manual-proof blocked
- tactical_battle_entry_return: battle evidence remains validation-only or missing visible click-to-callback proof
