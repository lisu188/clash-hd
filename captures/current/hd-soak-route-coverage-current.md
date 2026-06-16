# HD Soak Route Coverage

- Overall: PASS
- Generated: `2026-06-16T16:05:30.838419+00:00`
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
- `map_idle`: status=`implemented_waiting_on_short2_menu` route=`map-idle` implemented=`True` proof=`approval_gated_visible_runtime` readiness=`implemented_blocked_by_current_requirements` blockers=`2`
  - blocker `short2_menu_idle_soak`: status=`blocked` summary=short2 visible-runtime soak has not produced passing frame/process evidence; current short-step status is failed_classified_intro_skip_input_drift_exit
  - blocker `stable_hd_map_real_input`: status=`blocked` summary=HD map input proof remains pending manual DirectInput validation
- `map_pan`: status=`implemented_waiting_on_map_idle` route=`map-pan` implemented=`True` proof=`approval_gated_visible_runtime` readiness=`implemented_blocked_by_current_requirements` blockers=`2`
  - blocker `long_soak_representative_routes`: status=`blocked` summary=2h+ representative-route soak blocked (locked_short_ladder_incomplete): 2h+ representative-route soak evidence is locked or missing
  - blocker `stable_hd_map_real_input`: status=`blocked` summary=HD map input proof remains pending manual DirectInput validation
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
