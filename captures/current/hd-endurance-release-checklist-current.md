# HD Endurance Release Checklist

- Overall: FAIL
- Generated: `2026-06-15T20:36:18.323950+00:00`
- Runtime policy: repo-only endurance release checklist; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Protected stable stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Full game complete: `False`
- Completion statement: not 100%; endurance, manual input, state continuity, or validation-route gates remain open
- Counts: `4/14` pass, `6` blocked, `4` missing

## Next Milestone

- `short2_menu_idle_soak`: First short2 menu-idle soak passes
- Next probe: run the approval-gated short2 menu-idle soak on the protected stage

## Requirements

- `protected_stable_stage`: `pass` - default stage and validation-only group boundary are intact
- `current_no_popup_map`: `pass` - hidden/no-popup map evidence still passes
- `short2_menu_idle_soak`: `blocked` - short2 visible-runtime soak has not produced passing frame/process evidence
- `long_soak_representative_routes`: `missing` - no 2h+ representative-route soak report is present
- `stable_menu_real_input`: `blocked` - menu-load proof remains pending manual DirectInput validation
- `stable_hd_map_real_input`: `blocked` - HD map input proof remains pending manual DirectInput validation
- `right_bottom_action_menu`: `blocked` - right-bottom action/menu remains validation-only or manual-proof blocked
- `castle_and_barracks_centered_input`: `blocked` - castle/barracks centered input remains validation-only or manual-proof blocked
- `tactical_battle_entry_return`: `blocked` - battle evidence remains validation-only or missing visible click-to-callback proof
- `save_load_roundtrip`: `missing` - save/load continuity proof is absent
- `turn_advancement`: `missing` - turn-advancement proof is absent
- `campaign_routes`: `missing` - campaign-route proof is absent
- `artifact_and_process_hygiene`: `pass` - artifact and process hygiene guards pass
- `no_speculative_promotion`: `pass` - stable-stage boundary remains unchanged while validation-only lanes stay non-promoting

## Open Items

- short2_menu_idle_soak: short2 visible-runtime soak has not produced passing frame/process evidence
- long_soak_representative_routes: no 2h+ representative-route soak report is present
- stable_menu_real_input: menu-load proof remains pending manual DirectInput validation
- stable_hd_map_real_input: HD map input proof remains pending manual DirectInput validation
- right_bottom_action_menu: right-bottom action/menu remains validation-only or manual-proof blocked
- castle_and_barracks_centered_input: castle/barracks centered input remains validation-only or manual-proof blocked
- tactical_battle_entry_return: battle evidence remains validation-only or missing visible click-to-callback proof
- save_load_roundtrip: save/load continuity proof is absent
- turn_advancement: turn-advancement proof is absent
- campaign_routes: campaign-route proof is absent
