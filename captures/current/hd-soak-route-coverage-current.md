# HD Soak Route Coverage

- Overall: PASS
- Generated: `2026-06-15T20:36:17.975033+00:00`
- Runtime policy: repo-only soak route coverage inventory; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Harness script: `scripts\smoke\run_hd_soak.ps1`
- Implemented routes: `menu-idle, map-idle, map-pan, custom`
- Implemented tiers: `short2, short10, short30, custom`
- Release lanes implemented: `3/10`
- Coverage complete: `False`
- Next runtime route: `menu-idle`

## Release Lanes

- `menu_idle`: status=`implemented_pending_first_soak` route=`menu-idle` implemented=`True` proof=`approval_gated_visible_runtime`
- `map_idle`: status=`implemented_waiting_on_short2_menu` route=`map-idle` implemented=`True` proof=`approval_gated_visible_runtime`
- `map_pan`: status=`implemented_waiting_on_map_idle` route=`map-pan` implemented=`True` proof=`approval_gated_visible_runtime`
- `castle_overview_enter_exit`: status=`planned_not_implemented` route=`not-yet-scripted` implemented=`False` proof=`future_visible_or_manual_input`
- `barracks_castle_centered_input`: status=`planned_not_implemented` route=`not-yet-scripted` implemented=`False` proof=`future_visible_or_manual_input`
- `right_bottom_action_menu`: status=`planned_blocked_by_manual_or_natural_proof` route=`not-yet-scripted` implemented=`False` proof=`future_visible_or_manual_input`
- `tactical_battle_entry_return`: status=`planned_not_implemented` route=`not-yet-scripted` implemented=`False` proof=`future_visible_or_manual_input`
- `save_load_roundtrip`: status=`planned_not_implemented` route=`not-yet-scripted` implemented=`False` proof=`future_safe_test_save_continuity`
- `turn_advancement`: status=`planned_not_implemented` route=`not-yet-scripted` implemented=`False` proof=`future_state_continuity`
- `campaign_route`: status=`planned_not_implemented` route=`not-yet-scripted` implemented=`False` proof=`future_long_visible_runtime`
