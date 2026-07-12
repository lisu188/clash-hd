# HD Endurance Release Checklist

- Overall: FAIL
- Generated: `2026-07-12T18:35:07.541708+00:00`
- Runtime policy: repo-only endurance release checklist; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Protected stable stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Full game complete: `False`
- Completion statement: not 100%; endurance, manual input, state continuity, or validation-route gates remain open
- Counts: `3/15` pass, `12` blocked, `0` missing

## Next Milestone

- `short2_menu_idle_soak`: First short2 menu-idle soak passes
- Next probe: run the approval-gated short2 menu-idle soak on the protected stage

## Requirements

- `protected_stable_stage`: `pass` - default stage and validation-only group boundary are intact
- `current_no_popup_map`: `pass` - hidden/no-popup map evidence still passes
- `first_mission_visual_clean`: `blocked` - first-mission visual audit is not clean (selected_unit_action_bar_on_bottom_but_black_ui_patches_remain); black patches: right_below_minimap, bottom_right_panel, minimap_interior
- `short2_menu_idle_soak`: `blocked` - short2 visible-runtime soak has not produced passing frame/process evidence; current short-step status is failed_classified_intro_skip_input_drift_exit
  Canonical report: `captures\current\hd-soak-short2-menu-idle-current.json` present=`True`; guard: `captures\current\hd-soak-short2-menu-idle-guard-current.json` present=`True`; triage: `captures\current\hd-soak-short2-menu-idle-triage-current.json` present=`True`
- `long_soak_representative_routes`: `blocked` - 2h+ representative-route soak blocked (locked_short_ladder_incomplete): 2h+ representative-route soak evidence is locked or missing
- `stable_menu_real_input`: `blocked` - menu-load proof remains pending manual DirectInput validation
- `stable_hd_map_real_input`: `blocked` - HD map input proof remains pending manual DirectInput validation
- `right_bottom_action_menu`: `blocked` - right-bottom action/menu remains validation-only or manual-proof blocked
- `castle_and_barracks_centered_input`: `blocked` - castle/barracks centered input remains validation-only or manual-proof blocked
- `tactical_battle_entry_return`: `blocked` - battle evidence remains validation-only or missing visible click-to-callback proof
- `save_load_roundtrip`: `blocked` - save/load continuity proof blocked (blocked_missing_proof): continuity proof is missing or not sufficient for release
- `turn_advancement`: `blocked` - turn advancement proof blocked (blocked_missing_proof): continuity proof is missing or not sufficient for release
- `campaign_routes`: `blocked` - campaign route proof blocked (blocked_missing_proof): continuity proof is missing or not sufficient for release
- `artifact_and_process_hygiene`: `blocked` - artifact or process hygiene guard is not passing
- `no_speculative_promotion`: `pass` - stable-stage boundary remains unchanged while validation-only lanes stay non-promoting

## Open Items

- first_mission_visual_clean: first-mission visual audit is not clean (selected_unit_action_bar_on_bottom_but_black_ui_patches_remain); black patches: right_below_minimap, bottom_right_panel, minimap_interior
- short2_menu_idle_soak: short2 visible-runtime soak has not produced passing frame/process evidence; current short-step status is failed_classified_intro_skip_input_drift_exit
- long_soak_representative_routes: 2h+ representative-route soak blocked (locked_short_ladder_incomplete): 2h+ representative-route soak evidence is locked or missing
- stable_menu_real_input: menu-load proof remains pending manual DirectInput validation
- stable_hd_map_real_input: HD map input proof remains pending manual DirectInput validation
- right_bottom_action_menu: right-bottom action/menu remains validation-only or manual-proof blocked
- castle_and_barracks_centered_input: castle/barracks centered input remains validation-only or manual-proof blocked
- tactical_battle_entry_return: battle evidence remains validation-only or missing visible click-to-callback proof
- save_load_roundtrip: save/load continuity proof blocked (blocked_missing_proof): continuity proof is missing or not sufficient for release
- turn_advancement: turn advancement proof blocked (blocked_missing_proof): continuity proof is missing or not sufficient for release
- campaign_routes: campaign route proof blocked (blocked_missing_proof): continuity proof is missing or not sufficient for release
- artifact_and_process_hygiene: artifact or process hygiene guard is not passing
