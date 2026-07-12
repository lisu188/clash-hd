# HD Soak Route Coverage

- Overall: PASS
- Generated: `2026-07-12T18:04:02.571608+00:00`
- Runtime policy: repo-only soak route coverage inventory; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Harness script: `scripts\smoke\run_hd_soak.ps1`
- Release checklist: `captures\current\hd-endurance-release-checklist-current.json` state=`present`
- Implemented routes: `menu-idle, map-idle, map-pan, custom`
- Implemented tiers: `short2, short10, short30, custom`
- Release lanes implemented: `3/10`
- Release lanes with current blockers: `10`
- Coverage complete: `False`
- Next runtime route: `menu-idle`

## Release Lanes

- `menu_idle`: status=`implemented_pending_first_soak` route=`menu-idle` implemented=`True` proof=`approval_gated_visible_runtime` readiness=`implemented_blocked_by_current_requirements` blockers=`2`
  - blocker `short2_menu_idle_soak`: status=`blocked` summary=short2 visible-runtime soak has not produced passing frame/process evidence; current short-step status is failed_classified_intro_skip_input_drift_exit
  - blocker `stable_menu_real_input`: status=`blocked` summary=menu-load proof remains pending manual DirectInput validation
- `map_idle`: status=`implemented_waiting_on_short2_menu` route=`map-idle` implemented=`True` proof=`approval_gated_visible_runtime` readiness=`implemented_blocked_by_current_requirements` blockers=`3`
  - blocker `short2_menu_idle_soak`: status=`blocked` summary=short2 visible-runtime soak has not produced passing frame/process evidence; current short-step status is failed_classified_intro_skip_input_drift_exit
  - blocker `stable_hd_map_real_input`: status=`blocked` summary=HD map input proof remains pending manual DirectInput validation
  - blocker `first_mission_visual_clean`: status=`blocked` summary=first-mission visual audit is not clean (selected_unit_action_bar_on_bottom_but_black_ui_patches_remain); black patches: right_below_minimap, bottom_right_panel, minimap_interior
- `map_pan`: status=`implemented_waiting_on_map_idle` route=`map-pan` implemented=`True` proof=`approval_gated_visible_runtime` readiness=`implemented_blocked_by_current_requirements` blockers=`3`
  - blocker `long_soak_representative_routes`: status=`blocked` summary=2h+ representative-route soak blocked (locked_short_ladder_incomplete): 2h+ representative-route soak evidence is locked or missing
  - blocker `stable_hd_map_real_input`: status=`blocked` summary=HD map input proof remains pending manual DirectInput validation
  - blocker `first_mission_visual_clean`: status=`blocked` summary=first-mission visual audit is not clean (selected_unit_action_bar_on_bottom_but_black_ui_patches_remain); black patches: right_below_minimap, bottom_right_panel, minimap_interior
- `castle_overview_enter_exit`: status=`planned_not_implemented` route=`not-yet-scripted` implemented=`False` proof=`future_visible_or_manual_input` readiness=`planned_blocked_by_current_requirements` blockers=`1`
  - blocker `castle_and_barracks_centered_input`: status=`blocked` summary=castle/barracks centered input remains validation-only or manual-proof blocked
- `barracks_castle_centered_input`: status=`planned_not_implemented` route=`not-yet-scripted` implemented=`False` proof=`future_visible_or_manual_input` readiness=`planned_blocked_by_current_requirements` blockers=`1`
  - blocker `castle_and_barracks_centered_input`: status=`blocked` summary=castle/barracks centered input remains validation-only or manual-proof blocked
- `right_bottom_action_menu`: status=`planned_blocked_by_manual_or_natural_proof` route=`not-yet-scripted` implemented=`False` proof=`future_visible_or_manual_input` readiness=`planned_blocked_by_current_requirements` blockers=`1`
  - blocker `right_bottom_action_menu`: status=`blocked` summary=right-bottom action/menu remains validation-only or manual-proof blocked
- `tactical_battle_entry_return`: status=`planned_not_implemented` route=`not-yet-scripted` implemented=`False` proof=`future_visible_or_manual_input` readiness=`planned_blocked_by_current_requirements` blockers=`1`
  - blocker `tactical_battle_entry_return`: status=`blocked` summary=battle evidence remains validation-only or missing visible click-to-callback proof
- `save_load_roundtrip`: status=`planned_not_implemented` route=`not-yet-scripted` implemented=`False` proof=`future_safe_test_save_continuity` readiness=`planned_blocked_by_current_requirements` blockers=`1`
  - blocker `save_load_roundtrip`: status=`blocked` summary=save/load continuity proof blocked (blocked_missing_proof): continuity proof is missing or not sufficient for release
- `turn_advancement`: status=`planned_not_implemented` route=`not-yet-scripted` implemented=`False` proof=`future_state_continuity` readiness=`planned_blocked_by_current_requirements` blockers=`1`
  - blocker `turn_advancement`: status=`blocked` summary=turn advancement proof blocked (blocked_missing_proof): continuity proof is missing or not sufficient for release
- `campaign_route`: status=`planned_not_implemented` route=`not-yet-scripted` implemented=`False` proof=`future_long_visible_runtime` readiness=`planned_blocked_by_current_requirements` blockers=`2`
  - blocker `long_soak_representative_routes`: status=`blocked` summary=2h+ representative-route soak blocked (locked_short_ladder_incomplete): 2h+ representative-route soak evidence is locked or missing
  - blocker `campaign_routes`: status=`blocked` summary=campaign route proof blocked (blocked_missing_proof): continuity proof is missing or not sufficient for release

## Locked Future Route Plan

- `castle_overview_enter_exit`: proposed_route=`castle-overview-enter-exit` contract=`locked_not_scripted` ready_to_script=`False` safe_to_execute_now=`False`
  - steps: `load-button, load-slot0, confirm-load, enter-castle-overview, exit-castle-overview`
  - unlock_requirements: `short2_menu_idle_soak, stable_hd_map_real_input, castle_and_barracks_centered_input`
  - current_blockers: `castle_and_barracks_centered_input`
  - policy: do not add to run_hd_soak ValidateSet until short map routes pass and castle overview input has natural or approved manual proof
- `barracks_castle_centered_input`: proposed_route=`castle-barracks-enter-exit` contract=`locked_not_scripted` ready_to_script=`False` safe_to_execute_now=`False`
  - steps: `load-button, load-slot0, confirm-load, enter-castle-overview, enter-barracks, exit-barracks, exit-castle-overview`
  - unlock_requirements: `short2_menu_idle_soak, stable_hd_map_real_input, castle_and_barracks_centered_input`
  - current_blockers: `castle_and_barracks_centered_input`
  - policy: do not script barracks routing until castle overview entry/exit is stable and centered input proof exists
- `right_bottom_action_menu`: proposed_route=`right-bottom-action-menu` contract=`locked_not_scripted` ready_to_script=`False` safe_to_execute_now=`False`
  - steps: `load-button, load-slot0, confirm-load, pan-to-right-bottom, natural-select-right-bottom-target, open-action-menu`
  - unlock_requirements: `short2_menu_idle_soak, stable_hd_map_real_input, right_bottom_action_menu`
  - current_blockers: `right_bottom_action_menu`
  - policy: keep forced coordinate evidence diagnostic; script only after natural or approved manual right-bottom action-menu proof exists
- `tactical_battle_entry_return`: proposed_route=`battle-entry-return` contract=`locked_not_scripted` ready_to_script=`False` safe_to_execute_now=`False`
  - steps: `load-button, load-slot0, confirm-load, enter-battle, verify-battle-ui, return-to-map`
  - unlock_requirements: `short2_menu_idle_soak, stable_hd_map_real_input, tactical_battle_entry_return`
  - current_blockers: `tactical_battle_entry_return`
  - policy: do not script battle routing until representative map and castle routes are stable and battle entry/return proof is available
- `save_load_roundtrip`: proposed_route=`save-load-roundtrip` contract=`locked_not_scripted` ready_to_script=`False` safe_to_execute_now=`False`
  - steps: `prepare-isolated-save, save-roundtrip, load-roundtrip, compare-continuity-markers`
  - unlock_requirements: `short2_menu_idle_soak, stable_hd_map_real_input, save_load_roundtrip`
  - current_blockers: `save_load_roundtrip`
  - policy: do not script save mutation until an isolated disposable save fixture and continuity markers are defined
- `turn_advancement`: proposed_route=`turn-advancement` contract=`locked_not_scripted` ready_to_script=`False` safe_to_execute_now=`False`
  - steps: `load-safe-fixture, advance-turn, verify-turn-state-markers, verify-map-still-renders`
  - unlock_requirements: `short2_menu_idle_soak, save_load_roundtrip, turn_advancement`
  - current_blockers: `turn_advancement`
  - policy: do not script turn advancement until save/load continuity is safe and deterministic state markers exist
- `campaign_route`: proposed_route=`campaign-representative-route` contract=`locked_not_scripted` ready_to_script=`False` safe_to_execute_now=`False`
  - steps: `load-campaign-safe-fixture, route-campaign-objective, return-to-map, sample-continuity`
  - unlock_requirements: `short2_menu_idle_soak, long_soak_representative_routes, campaign_routes`
  - current_blockers: `long_soak_representative_routes, campaign_routes`
  - policy: do not script campaign routing until short/medium soak tiers and continuity gates are already passing
