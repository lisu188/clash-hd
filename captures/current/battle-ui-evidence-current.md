# Battle UI Evidence Matrix

- Overall: FAIL
- Generated: `2026-07-13T08:54:37+02:00`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`
- Inputprobe stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter-inputprobe`
- Candidate SHA-256: `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`
- Input candidate SHA-256: `F84933776944E2B616F6BBCCF7708ABBF06498D5438FA8DF7B7AF1BB56CD180A`
- Promotion status: `validation_stage_only`
- Stable stage should change: `False`

## Completion Summary

- Focused area: `battle/right-bottom command lane`
- Focused completion: `99.89%`
- Real visible click-to-callback proof: `open`
- Full-game status: `Full-game reverse engineering is not 100%.`
- Remaining blocker: `real visible click-to-callback proof`

## Checks

- force_entry: PASS
- command_hit: PASS
- command_callback: PASS
- enabled_callback: PASS
- grid_hit: PASS
- centered_input: PASS
- post_ready_redraw: PASS
- modal_classified: PASS
- patch_stage: PASS
- input_patch_stage: PASS
- availability_scan: PASS
- slot_scan: PASS
- save_inventory: PASS
- constructed_fixture_plan: PASS
- constructed_fixture_unit_scan: PASS
- constructed_fixture_command: PASS
- stable_smoke: PASS
- visible_input: FAIL

## Key Evidence

- centered_visual: `centered-native-640x480`
- command_hit_ok: `True`
- command_native_hit_ok: `True`
- command_callback_branch: `precondition-disabled`
- enabled_callback_branch: `state2`
- grid_visual_cell: `[1, 1]`
- grid_native_cell: `[0, 0]`
- centered_input_wrapper_ok: `True`
- grid_input_inner_mouse: `[64, 48]`
- descriptor_input_inner_mouse: `[508, 380]`
- post_ready_redraw_sample_ok: `True`
- post_ready_presents: `9`
- post_ready_copybacks: `6`
- post_ready_grid_native: `[64, 48]`
- post_ready_last_present_ret: `0x0042CB46`
- natural_enabled_unit_count: `0`
- selected_unit_naturally_disabled: `True`
- enabled_table_type_count: `11`
- enabled_table_type_names: `['Dragon cavalry', 'Archer', 'Crossbower', 'Musketeer', 'Catapult', 'Cannon', 'Forester', 'Cyklop', 'Wizard', 'Winger', 'Dragon']`
- slot_scan_routed_slots: `3`
- slot_scan_timeouts: `3`
- slot_scan_natural_enabled_units: `0`
- save_inventory_slots: `6`
- save_inventory_units: `63`
- save_inventory_natural_enabled_units: `0`
- constructed_fixture_status: `copied_save_written`
- constructed_fixture_change: `Light cavalry -> Dragon cavalry`
- constructed_fixture_type_offset: `0x00023EFC`
- constructed_fixture_natural_enabled_units: `1`
- constructed_fixture_enabled_unit: `Dragon cavalry`
- constructed_fixture_attempt_coord_mode: `visual-click`
- constructed_fixture_attempt_displayed: `[588, 440]`
- constructed_fixture_attempt_expected_native: `[508, 380]`
- constructed_fixture_callback_unit_type: `8`
- constructed_fixture_callback_enabled: `3`
- constructed_fixture_callback_branch: `state1`
- constructed_fixture_forced_unit_rows: `0`
- constructed_fixture_forced_click_gate_rows: `0`
- constructed_fixture_observed_click_gate_rows: `1`
- constructed_fixture_render_begin_skip_seen: `False`
- constructed_fixture_render_begin_enter_seen: `True`
- constructed_fixture_rearm_pre_gates_seen: `False`
- constructed_fixture_pre_gates_seen: `True`
- constructed_fixture_synthetic_release_seen: `True`
- constructed_fixture_render_begin_guard_seen: `False`
- constructed_fixture_render_begin_exit_seen: `True`
- modal_classified: `True`
- visible_input_focused_completion_percent: `99.89`
- visible_input_summary_passed: `False`
- visible_input_command_ready_runs: `0`
- visible_input_click_consumed_runs: `0`
- visible_input_invalid_runs: `0`
- visible_input_real_click_consumed: `False`

## Failures

- visible_input: visible input command readiness is not proven

## Open Items

- real visible click-to-callback proof remains open

## Screenshots

![battle UI evidence](captures\archive\cdb-surface-dump-20260518-221018\surface.png)
![battle UI evidence](captures\archive\cdb-surface-dump-20260520-094032\surface.png)
![battle UI evidence](captures\archive\cdb-surface-dump-20260520-100717\surface.png)
![battle UI evidence](captures\archive\cdb-surface-dump-20260520-101859\surface.png)
![battle UI evidence](captures\archive\cdb-surface-dump-20260520-103155\surface.png)
![battle UI evidence](captures\archive\cdb-surface-dump-20260520-111115\surface.png)
![battle UI evidence](captures\archive\cdb-surface-dump-20260520-195244\surface.png)
![battle UI evidence](captures\archive\cdb-surface-dump-20260520-103714\surface.png)
![battle UI evidence](captures\archive\cdb-surface-dump-20260520-220459\surface.png)
