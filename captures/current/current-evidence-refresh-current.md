# Current Evidence Refresh

- Overall: FAIL
- Generated: `2026-06-15T22:14:58+02:00`
- Runtime policy: repo/local metadata only; does not launch Clash95, CDB, wrappers, or visible windows

## Checks

### Hd Map Smoke

- Status: FAIL
- JSON: `captures\current\hd-map-smoke-current.json`
- Markdown: `captures\current\hd-map-smoke-current.md`
- patch_stage_passed: `False`
- post_owner_passed: `False`
- candidate_sha256: `None`
- Failures:
  - patch-stage: no candidate executable path was found
  - post-owner evidence matrix failed

### No Popup Map Evidence

- Status: PASS
- JSON: `captures\current\no-popup-map-evidence-current.json`
- Markdown: `captures\current\no-popup-map-evidence-current.md`
- normal_run: `captures\archive\cdb-surface-dump-20260429-140916`
- normal_blank_active_count: `13`
- normal_unexplained_blank_count: `0`
- normal_visibility_status_counts: `{'visibility_zero': 13}`
- forced_run: `captures\archive\cdb-surface-dump-20260429-135242`
- forced_blank_active_count: `0`
- forced_visible_exit_code: `0`
- forced_visret_nonzero_count: `54`
- forced_post_nonblack_count: `54`

### No Popup Map Evidence Tests

- Status: PASS
- JSON: `captures\current\no-popup-map-evidence-tests-current.json`
- Markdown: `captures\current\no-popup-map-evidence-tests-current.md`
- test_count: `5`
- guard_policy: `proves the no-popup map evidence matrix requires a visibility-explained normal run, a forced-visible edge proof, latest-run selection, and CLI fail-closed behavior`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for matrix CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Patch Manifest Compare

- Status: PASS
- JSON: `captures\current\patch-manifest-compare-current-vs-partial12.json`
- Markdown: `captures\current\patch-manifest-compare-current-vs-partial12.md`
- structural_diff_count: `5`
- left_nonpatched: `0`
- right_nonpatched: `0`
- added_records: `0`
- removed_records: `0`
- changed_records: `3`

### Barracks Success Branch

- Status: PASS
- ready: `True`
- descriptor_click_ok: `True`
- success_4356c0_ok: `True`
- failure_exit_count: `0`
- av_count: `0`
- last_select_forced: `{'ret': 4411998, 'forced_index': 1, 'selected_addon': 1, 'list': [0, 1, 3, 16, 17, 37, 38, 39, -1, -1, -1, -1], 'owner': 67028762, 'selected_index': 1, 'render': 5362880, 'map_surface': 170913200, 'sz': [800, 600], 'hover_slot': -1}`
- last_success_4356c0: `{'selected_index': 1, 'selected_addon': 1, 'action_state': 0}`

### Right Bottom Ui Probe

- Status: PASS
- surface_dump_passed: `True`
- rbui_markers_seen: `True`
- rbui_desc_switch: `26`
- rbui_viewport_switch: `1`
- rbui_panel_draw: `0`
- rbui_action_box: `0`
- surfdump_playgame: `1`
- surfdump_ready: `1`
- bounds: `{'bottom_tooltip': {'nonblack_percent': 66.451, 'black_percent': 33.549, 'flags': ['large_black_component', 'black_touches_bottom_right']}, 'bottom_right_panel': {'nonblack_percent': 21.43, 'black_percent': 78.57, 'flags': ['large_black_component', 'black_touches_bottom_right']}, 'bottom_frame': {'nonblack_percent': 32.306, 'black_percent': 67.694, 'flags': ['large_black_component', 'black_touches_bottom_right']}}`

### Right Bottom Owner Route

- Status: PASS
- surface_dump_passed: `True`
- hidden_desktop: `True`
- map_validation_skipped: `True`
- candidate_sha256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- ready: `True`
- av_count: `0`
- owner_rows: `11`
- panel_rows: `11`
- draw_rows: `4`
- nonzero_owner_rows: `12`
- appost_action_box: `0`
- tooltip_action_box: `1`
- apredir_after_action_box: `1`
- apredir_copyback_after_call: `1`
- composition_text_rows: `13`
- composition_present_rows: `0`
- composition_present_null_rows: `5`
- composition_sample_rows: `2`
- composition_present_by_region: `{'frame_left': 0, 'frame_top': 0, 'right_frame_under_minimap': 0, 'bottom_tooltip': 0, 'bottom_right_panel': 0, 'bottom_frame': 0}`
- composition_present_null_by_region: `None`
- bounds: `{'minimap_top_right': {'nonblack_percent': 61.468, 'black_percent': 38.532, 'flags': ['black_touches_bottom_right']}, 'right_side_total': {'nonblack_percent': 46.831, 'black_percent': 53.169, 'flags': ['large_black_component', 'black_touches_bottom_right']}, 'right_side_below_minimap': {'nonblack_percent': 38.366, 'black_percent': 61.634, 'flags': ['large_black_component', 'black_touches_bottom_right']}, 'bottom_strip': {'nonblack_percent': 51.75, 'black_percent': 48.25, 'flags': ['large_black_component', 'black_touches_bottom_right']}, 'bottom_right_ui_corner': {'nonblack_percent': 21.43, 'black_percent': 78.57, 'flags': ['large_black_component', 'black_touches_bottom_right']}, 'bottom_right_tile_r8c9': {'nonblack_percent': 46.24, 'black_percent': 53.76, 'flags': ['large_black_component', 'black_touches_bottom_right']}, 'bottom_right_tile_r8c10': {'nonblack_percent': 0.0, 'black_percent': 100.0, 'flags': ['mostly_black', 'large_black_component', 'black_touches_bottom_right']}, 'bottom_right_tile_r8c11': {'nonblack_percent': 0.0, 'black_percent': 100.0, 'flags': ['mostly_black', 'large_black_component', 'black_touches_bottom_right']}}`

### Right Bottom Compose Probe

- Status: PASS
- surface_dump_passed: `True`
- hidden_desktop: `True`
- map_validation_skipped: `True`
- candidate_sha256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- ready: `True`
- av_count: `0`
- owner_rows: `11`
- draw_rows: `5`
- apcompose_status_call: `1`
- apcompose_status_done: `1`
- apcompose_action_call: `1`
- apcompose_action_done: `1`
- composition_sample_rows: `6`
- bottom_right_ui_corner_nonblack: `48.228`
- bottom_right_ui_corner_delta: `26.798`
- bottom_right_tile_r8c10_nonblack: `54.102`
- bottom_right_tile_r8c10_delta: `54.102`
- bottom_right_tile_r8c11_nonblack: `42.822`
- bottom_right_tile_r8c11_delta: `42.822`
- bottom_strip_delta: `3.297`

### Right Bottom Compose Patch

- Status: PASS
- surface_dump_passed: `True`
- hidden_desktop: `True`
- map_validation_skipped: `True`
- stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- candidate_sha256: `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`
- manifest_patched: `122`
- right_bottom_patch_group: `{'patched': 4, 'total': 4}`
- current_hd_map_gate: `True`
- ready: `True`
- av_count: `0`
- owner_rows: `11`
- draw_rows: `5`
- composition_text_rows: `13`
- composition_present_rows: `0`
- composition_present_null_rows: `5`
- bottom_right_ui_corner_nonblack: `48.228`
- bottom_right_ui_corner_delta: `26.798`
- bottom_right_tile_r8c10_nonblack: `54.102`
- bottom_right_tile_r8c10_delta: `54.102`
- bottom_right_tile_r8c11_nonblack: `42.822`
- bottom_right_tile_r8c11_delta: `42.822`
- bottom_strip_delta: `3.297`

### Right Bottom Compose Fullstart Route

- Status: PASS
- surface_dump_passed: `True`
- hidden_desktop: `True`
- map_validation_skipped: `True`
- no_skip_start_anims: `True`
- fast_forward_start_anims: `False`
- stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- candidate_sha256: `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`
- manifest_patched: `122`
- right_bottom_patch_group: `{'patched': 4, 'total': 4}`
- current_hd_map_gate: `True`
- ready: `True`
- av_count: `0`
- owner_rows: `11`
- draw_rows: `5`
- composition_text_rows: `13`
- composition_present_rows: `0`
- composition_present_null_rows: `5`
- bottom_right_ui_corner_nonblack: `48.228`
- bottom_right_ui_corner_delta: `26.798`
- bottom_right_tile_r8c10_nonblack: `54.102`
- bottom_right_tile_r8c10_delta: `54.102`
- bottom_right_tile_r8c11_nonblack: `42.822`
- bottom_right_tile_r8c11_delta: `42.822`
- bottom_strip_delta: `3.297`

### Right Bottom Compose Normal Gate

- Status: PASS
- surface_dump_passed: `True`
- hidden_desktop: `True`
- map_validation_skipped: `False`
- no_skip_start_anims: `True`
- fast_forward_start_anims: `False`
- stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- candidate_sha256: `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`
- surface: `[800, 600]`
- gameplay_frame_likely: `True`
- active_cells: `108`
- blank_active_cells: `13`
- visibility_require_explained: `True`
- visibility_explained_gate: `True`
- visibility_unexplained_blank_cells: `0`
- visibility_zero: `13`
- current_hd_map_gate: `True`
- right_bottom_patch_group: `{'patched': 4, 'total': 4}`

### Right Bottom Compose Ui Probe

- Status: FAIL
- surface_dump_passed: `True`
- hidden_desktop: `True`
- map_validation_skipped: `False`
- no_skip_start_anims: `True`
- stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- candidate_sha256: `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`
- rbui_markers_seen: `True`
- rbui_desc_switch: `35`
- rbui_viewport_switch: `1`
- rbui_panel_draw: `0`
- rbui_action_box: `0`
- surfdump_playgame: `1`
- surfdump_ready: `1`
- av_count: `0`
- current_hd_map_gate: `True`
- right_bottom_patch_group: `{'patched': 4, 'total': 4}`
- bounds: `{'minimap_top_right': {'nonblack_percent': 12.936, 'black_percent': 87.064, 'flags': ['large_black_component', 'black_touches_bottom_right']}, 'right_side_total': {'nonblack_percent': 19.688, 'black_percent': 80.312, 'flags': ['large_black_component', 'black_touches_bottom_right']}, 'right_side_below_minimap': {'nonblack_percent': 23.593, 'black_percent': 76.407, 'flags': ['large_black_component', 'black_touches_bottom_right']}, 'bottom_strip': {'nonblack_percent': 51.75, 'black_percent': 48.25, 'flags': ['large_black_component', 'black_touches_bottom_right']}, 'bottom_right_ui_corner': {'nonblack_percent': 21.43, 'black_percent': 78.57, 'flags': ['large_black_component', 'black_touches_bottom_right']}, 'bottom_right_tile_r8c9': {'nonblack_percent': 46.24, 'black_percent': 53.76, 'flags': ['large_black_component', 'black_touches_bottom_right']}, 'bottom_right_tile_r8c10': {'nonblack_percent': 0.0, 'black_percent': 100.0, 'flags': ['mostly_black', 'large_black_component', 'black_touches_bottom_right']}, 'bottom_right_tile_r8c11': {'nonblack_percent': 0.0, 'black_percent': 100.0, 'flags': ['mostly_black', 'large_black_component', 'black_touches_bottom_right']}}`
- Failures:
  - right-bottom compose UI did not naturally enter owner/action draw rows

### Right Bottom Grid Hit

- Status: PASS
- JSON: `captures\current\right-bottom-grid-hit-current.json`
- Markdown: `captures\current\right-bottom-grid-hit-current.md`
- surface_dump_passed: `True`
- hidden_desktop: `True`
- allow_visible_desktop: `False`
- use_ddraw_proxy: `True`
- map_validation_skipped: `True`
- no_skip_start_anims: `False`
- fast_forward_start_anims: `True`
- stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- candidate_sha256: `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`
- surface: `[800, 600]`
- current_hd_map_gate: `True`
- right_bottom_patch_group: `{'patched': 4, 'total': 4}`
- ready: `True`
- grid_hit_ok: `True`
- last_grid_entry: `[450, 73]`
- last_grid_result: `0`
- forced_gate_count: `1`
- failure_exit_count: `0`
- draw_row_count: `5`
- av_count: `0`

### Right Bottom Grid Hit Probe Guard

- Status: PASS
- JSON: `captures\current\right-bottom-grid-hit-probe-guard-current.json`
- Markdown: `captures\current\right-bottom-grid-hit-probe-guard-current.md`
- guard_policy: `focused right-bottom grid-hit proof must keep the owner/action/grid breakpoints, continue to prove native coordinate (450,73) returns grid cell 0, and stay hidden-desktop with no failure-exit or AV rows`
- runtime_policy: `repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`
- expected_stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- grid_hit_ok: `True`
- last_grid_entry: `[450, 73]`
- last_grid_result: `0`
- failure_exit_count: `0`
- av_count: `0`

### Right Bottom Natural Route Guard

- Status: PASS
- JSON: `captures\current\right-bottom-natural-route-guard-current.json`
- Markdown: `captures\current\right-bottom-natural-route-guard-current.md`
- hidden_desktop: `True`
- stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter`
- candidate_sha256: `D3FF331FD6A7B10A91C55A55FF891685CFAC376917816557B40A483EBDBC569C`
- owner_entry_flag: `0x00`
- owner_flag_test: `{'owner_flag': '0x00', 'bit2': 0, 'bit1': 0, 'bit8': 0}`
- action_descriptor: `{'slot': 'd1', 'x': 1000, 'y': 426, 'callback': '004338e0'}`
- descriptor_result: `{'result': 0, 'owner': '041bc71a', 'owner_flag': '0x00', 'surface': [800, 600]}`
- action_route_count: `0`
- state_gated_by_owner_flag: `True`
- av_count: `0`

### Castle Save Owner Flag Scan

- Status: PASS
- JSON: `captures\current\castle-save-owner-flag-scan-current.json`
- Markdown: `captures\current\castle-save-owner-flag-scan-current.md`
- save_count: `6`
- candidate_block_count: `6`
- active_record_count: `22`
- records_with_any_owner_flag_count: `9`
- action_eligible_save_count: `3`
- action_eligible_record_count: `7`
- recommended_save: `C:\Clash\save\2.dat`
- recommended_record_index: `1`
- recommended_position: `[1, 23]`
- recommended_owner: `1`
- recommended_flags_1a0: `0x16`
- current_blocker: `None`
- guard_policy: `finds whether any installed save naturally has castle owner flag bit 0x02 set, which is required before the 004338E0 owner/action lane can be routed without debugger-forced owner flags`
- runtime_policy: `local save metadata inspection only; reads installed save files but does not copy raw saves, launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Natural Route Candidate Matrix

- Status: PASS
- JSON: `captures\current\right-bottom-natural-route-candidate-matrix-current.json`
- Markdown: `captures\current\right-bottom-natural-route-candidate-matrix-current.md`
- save_scan_passed: `True`
- action_eligible_record_count: `7`
- baseline_route_index: `0`
- baseline_owner_flag_zero_blocker: `True`
- route_compatible_candidate: `{'save': 'C:\\Clash\\save\\5.dat', 'save_slot': 5, 'record_index': 0, 'position': [14, 20], 'owner': 0, 'flags_1a0': 11, 'flags_1a0_hex': '0x0B', 'flags_1a4_hex': '0x01', 'bit2': 2, 'bit1': 1, 'bit8': 8, 'action_eligible': True}`
- slot2_status: `{'status': 'loads_but_click_misses_castle', 'load_succeeded': True, 'map_click_hits_building': False, 'castle_overview_reached': False, 'first_map_tile': {'x': 43, 'y': 45, 'mouse_x': 352, 'mouse_y': 272, 'selected': -1, 'current': 0}, 'action_record': {'save': 'C:\\Clash\\save\\2.dat', 'save_slot': 2, 'record_index': 1, 'position': [1, 23], 'owner': 1, 'flags_1a0': 22, 'flags_1a0_hex': '0x16', 'flags_1a4_hex': '0x00', 'bit2': 2, 'bit1': 0, 'bit8': 0, 'action_eligible': True}}`
- slot5_status: `{'status': 'timeout_before_loadsave', 'timed_out': True, 'load_succeeded': False, 'loadsave': None, 'route_compatible_candidate': {'save': 'C:\\Clash\\save\\5.dat', 'save_slot': 5, 'record_index': 0, 'position': [14, 20], 'owner': 0, 'flags_1a0': 11, 'flags_1a0_hex': '0x0B', 'flags_1a4_hex': '0x01', 'bit2': 2, 'bit1': 1, 'bit8': 8, 'action_eligible': True}}`
- current_blocker: `route-compatible save slot 5 has owner flag bit 0x02 at record index 0, but the hidden CDB load-slot route currently times out before LOADSAVE; slot 2 confirms alternate-slot loading works but the current map click misses its bit-2 castle`
- next_proof_options: `['fix the hidden CDB load-slot selection path for slot 5 and rerun the natural owner/action probe', 'or build an isolated working-directory fixture that maps the slot-5 save state to a route-compatible slot without mutating C:\\Clash\\save', 'or retarget the CDB map click/scroll path to the slot-2 bit-2 castle at record index 1']`

### Load Slot Route Limit Guard

- Status: PASS
- JSON: `captures\current\load-slot-route-limit-current.json`
- Markdown: `captures\current\load-slot-route-limit-current.md`
- static_load_rows: `0..9`
- harness_mouse_formula: `x=320, y=166 + 22 * LoadSlot`
- archived_success_slots: `[2]`
- archived_blocked_slots: `[3, 4, 5]`
- recent_slot5_blocked: `True`
- current_boundary: `static code and harness parameters allow rows 0-9, but current archived hidden evidence only proves the slot-2 row path. Slots 3, 4, and 5, plus the current slot-5 right-bottom attempt, stall before force-select/accept and LOADSAVE.`
- next_proof_options: `['debug why rows 3-5 stop before the forced load-select breakpoint under the current CDB route', 'or create an isolated test working directory that maps the slot-5 save state to a proven row without editing C:\\Clash\\save', 'or use a direct-loader probe, but label it non-natural route evidence until menu selection is proven']`
- cohort_candidate_sha256: `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`
- cohort_stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`

### Right Bottom Slot Fixture Plan

- Status: PASS
- JSON: `captures\current\right-bottom-slot-fixture-plan-current.json`
- Markdown: `captures\current\right-bottom-slot-fixture-plan-current.md`
- candidate_matrix_passed: `True`
- load_slot_route_limit_passed: `True`
- baseline_route_index: `0`
- route_candidate: `{'save': 'C:\\Clash\\save\\5.dat', 'save_slot': 5, 'record_index': 0, 'position': [14, 20], 'owner': 0, 'flags_1a0': 11, 'flags_1a0_hex': '0x0B', 'flags_1a4_hex': '0x01', 'bit2': 2, 'bit1': 1, 'bit8': 8, 'action_eligible': True}`
- slot2_status: `loads_but_click_misses_castle`
- slot5_status: `timeout_before_loadsave`
- recent_slot5_blocked: `True`
- fixture_save: `C:\ClashTests\right-bottom-slot5-as-slot0-fixture\save\0.dat`
- proof_class: `non_natural_isolated_fixture`
- promotion_ready: `False`
- stable_stage_should_change: `False`

### Right Bottom Slot Fixture Script Guard

- Status: PASS
- JSON: `captures\current\right-bottom-slot-fixture-script-guard-current.json`
- Markdown: `captures\current\right-bottom-slot-fixture-script-guard-current.md`
- guard_policy: `the fixture preparation script must default to dry-run, copy only after -Execute, optionally seed a non-save isolated workdir, refuse repository and live C:\Clash\save outputs, and avoid visible-runtime APIs`
- runtime_policy: `repo-only source inspection; does not run PowerShell, copy saves, launch Clash95, CDB, wrappers, or visible windows`
- script: `scripts\smoke\prepare_right_bottom_slot_fixture.ps1`
- dry_run_exit_line: `122`
- copy_line: `149`
- risky_visible_lines: `[]`

### Right Bottom Slot Fixture Runtime Plan

- Status: PASS
- JSON: `captures\current\right-bottom-slot-fixture-runtime-plan-current.json`
- Markdown: `captures\current\right-bottom-slot-fixture-runtime-plan-current.md`
- proof_class: `non_natural_isolated_fixture`
- promotion_ready: `False`
- stable_stage_should_change: `False`
- fixture_root: `C:\ClashTests\right-bottom-slot5-as-slot0-fixture`
- fixture_save: `C:\ClashTests\right-bottom-slot5-as-slot0-fixture\save\0.dat`
- candidate_dir: `C:\ClashTests\right-bottom-slot5-as-slot0-fixture\candidate`
- target_load_slot: `0`
- prepare_seed_workdir: `True`
- stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter`
- run_seconds: `120`
- result_log_template: `captures\cdb-surface-dump-FIXTURE-RUN\cdb-surface-dump.log`
- result_json_template: `captures\cdb-surface-dump-FIXTURE-RUN\right-bottom-slot-fixture-result-summary.json`
- result_md_template: `captures\cdb-surface-dump-FIXTURE-RUN\right-bottom-slot-fixture-result-summary.md`

### Load Slot Timeout Phase

- Status: PASS
- JSON: `captures\current\load-slot-timeout-phase-current.json`
- Markdown: `captures\current\load-slot-timeout-phase-current.md`
- slot2_phase: `load_menu_accept_success`
- blocked_slots: `[3, 4, 5]`
- recent_slot5_blocked: `True`
- current_divergence: `slot 2 reaches the 0044895A load-menu entry and accept path; slots 3-5 reach early 00419B80 load-coordinate descriptor rows, then time out before 0044895A load-menu entry, forced select, LOADSAVE, or PlayGame`
- timeout_stack_categories: `{'slot3_timeout': 'qpc_timing_poll_before_load_menu_loop', 'slot4_timeout': 'qpc_timing_poll_before_load_menu_loop', 'slot5_timeout': 'win32_message_poll_before_load_menu_loop', 'recent_slot5_timeout': 'engine_timing_poll_before_load_menu_loop'}`
- next_probe_target: `instrument the transition between the early 00419B80 load descriptors and 0044895A load-menu entry for rows 3-5`

### Load Slot Entry Gap

- Status: FAIL
- JSON: `captures\current\load-slot-entry-gap-current.json`
- Markdown: `captures\current\load-slot-entry-gap-current.md`
- current_gap: `Rows 3-5 are stopped in the transition after the forced main Load callback and before 0044895A load-menu entry. They are not yet evidence of invalid save rows because 0044A110/sub_444750, LOADSAVE, and PlayGame are never reached.`
- slot2_post_entry_success: `True`
- blocked_rows: `[3, 4, 5]`
- recent_slot5_same_gap: `True`
- next_probe_targets: `['add a CDB transition row between 00447780 and 0044895A to prove when case 5 is dispatched', 'late-arm row forcing only after 0044895A instead of relying on early 00419B80 descriptor hits', 'log dword_543D7C and dword_543D78 immediately before and after the main dispatch consumes the load callback']`
- next_non_promoting_route_option: `use an isolated slot fixture or direct-loader probe only if it is labeled non-natural route evidence until the menu transition is proven`
- Failures:
  - cdb_probe: missing marker pre_entry_load_coord_placeholder: __PRE_ENTRY_LOAD_COORD_ACTION__

### Load Slot Transition Probe Guard

- Status: PASS
- JSON: `captures\current\load-slot-transition-probe-guard-current.json`
- Markdown: `captures\current\load-slot-transition-probe-guard-current.md`
- probe: `probes\cdb\menu\clash95_load_slot_entry_transition_extra.cdb`
- surface_dump_script: `scripts\cdb\run_cdb_surface_dump.ps1`
- late_entry_breakpoint: `0044895A`
- early_descriptor_breakpoint_avoided: `True`
- slot_conditions_parameterized: `True`
- extra_probe_placeholders_replaced: `True`
- late_load_slot_forcing_only_supported: `True`

### Load Slot Transition Run Plan

- Status: FAIL
- JSON: `captures\current\load-slot-transition-run-plan-current.json`
- Markdown: `captures\current\load-slot-transition-run-plan-current.md`
- target_rows: `[3, 4, 5]`
- stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`
- candidate_root: `C:\ClashTests\load-slot-transition`
- result_root_template: `captures\cdb-surface-dump-TRANSITION-RUN`
- run_seconds: `120`
- late_entry_breakpoint: `0044895A`
- gap_classification: `after_main_load_callback_before_load_menu_case_entry`
- command_count: `3`
- summary_command_count: `3`
- visible_runtime_allowed: `False`
- Failures:
  - load-slot entry gap report is not passing

### Load Slot Transition Geometry Guard

- Status: FAIL
- JSON: `captures\current\load-slot-transition-geometry-guard-current.json`
- Markdown: `captures\current\load-slot-transition-geometry-guard-current.md`
- target_rows: `[3, 4, 5]`
- row_geometry: `[{'slot': 3, 'mouse_x': 320, 'mouse_y': 232, 'raw_x': 20480, 'raw_y': 14848, 'raw_x_hex': '00005000', 'raw_y_hex': '00003a00'}, {'slot': 4, 'mouse_x': 320, 'mouse_y': 254, 'raw_x': 20480, 'raw_y': 16256, 'raw_x_hex': '00005000', 'raw_y_hex': '00003f80'}, {'slot': 5, 'mouse_x': 320, 'mouse_y': 276, 'raw_x': 20480, 'raw_y': 17664, 'raw_x_hex': '00005000', 'raw_y_hex': '00004500'}]`
- formula: `mouse_x=320; mouse_y=166+22*slot; raw=logical<<6`
- run_plan_command_count: `3`
- run_plan_summary_command_count: `3`
- Failures:
  - transition geometry guard failed: run_plan_passed

### Load Slot Transition Probe Preview

- Status: FAIL
- JSON: `captures\current\load-slot-transition-probe-preview-current.json`
- Markdown: `captures\current\load-slot-transition-probe-preview-current.md`
- target_rows: `[3, 4, 5]`
- preview_count: `3`
- preview_sha256: `{'3': 'C64A3D0796E9A4000DA5D8DE27D5B4DA307BD2EBDE98FE7F8F45DC454A26F8C6', '4': '697C8481B5C0FA1FA109E4A85E8502FF2A57E723AF05E4F8B390C7C806826CD7', '5': '3864C049BB9E6CD91E7FB995163E999BDADEEFB8411CC4308756ECF87EB54509'}`
- row_geometry: `[{'slot': 3, 'mouse_x': 320, 'mouse_y': 232, 'raw_x': 20480, 'raw_y': 14848, 'raw_x_hex': '00005000', 'raw_y_hex': '00003a00'}, {'slot': 4, 'mouse_x': 320, 'mouse_y': 254, 'raw_x': 20480, 'raw_y': 16256, 'raw_x_hex': '00005000', 'raw_y_hex': '00003f80'}, {'slot': 5, 'mouse_x': 320, 'mouse_y': 276, 'raw_x': 20480, 'raw_y': 17664, 'raw_x_hex': '00005000', 'raw_y_hex': '00004500'}]`
- Failures:
  - transition probe preview failed: run_plan_passed
  - transition probe preview failed: geometry_guard_passed

### Right Bottom Owner Flag Inventory

- Status: PASS
- JSON: `captures\current\right-bottom-owner-flag-inventory-current.json`
- Markdown: `captures\current\right-bottom-owner-flag-inventory-current.md`
- scanned_log_count: `172`
- relevant_run_count: `80`
- classification_counts: `{'forced_owner_action_route': 64, 'natural_state_gated': 1, 'natural_ui_descriptor_only': 2, 'non_natural_isolated_fixture': 10, 'right_bottom_related': 3}`
- natural_state_gated_count: `1`
- forced_owner_action_route_count: `64`
- natural_action_route_count: `0`
- guard_policy: `right-bottom owner/action evidence must keep at least one controlled forced owner route, at least one current natural owner-flag-gated route, and no non-fixture archived natural route that already reaches the owner/action renderer without an explicit forced owner flag`
- runtime_policy: `repo-only; scans existing CDB logs and does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Route Timing Guard

- Status: PASS
- JSON: `captures\current\right-bottom-route-timing-guard-current.json`
- Markdown: `captures\current\right-bottom-route-timing-guard-current.md`
- guard_policy: `right-bottom validation evidence must keep hidden route/copyback/grid marker ordering, candidate SHA agreement, 800x600 surfaces, and no AV/failure-exit rows`
- runtime_policy: `repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`
- candidate_sha256: `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`
- patch_route_ordered_markers: `29`
- fullstart_route_ordered_markers: `29`
- grid_route_ordered_markers: `25`
- grid_hit_ok: `True`
- last_grid_entry: `[450, 73]`
- last_grid_result: `0`
- failure_exit_count: `0`
- av_count: `0`

### Right Bottom Compose Promotion Decision

- Status: FAIL
- JSON: `captures\current\right-bottom-compose-promotion-decision-current.json`
- Markdown: `captures\current\right-bottom-compose-promotion-decision-current.md`
- decision: `defer_stable_promotion`
- stable_stage_should_change: `False`
- current_stable_stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- validation_stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- candidate_sha256: `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`
- manual_input_proof_valid: `False`
- Failures:
  - right_bottom_compose_ui_probe: right-bottom compose UI did not naturally enter owner/action draw rows
  - right-bottom natural UI probe did not enter owner/action draw rows

### Right Bottom Compose Evidence

- Status: FAIL
- JSON: `captures\current\right-bottom-compose-evidence-current.json`
- Markdown: `captures\current\right-bottom-compose-evidence-current.md`
- promotion_status: `validation_stage_only`
- stable_stage_should_change: `False`
- candidate_sha256: `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`
- controlled_grid_hit_ok: `True`
- promotion_decision: `defer_stable_promotion`
- Failures:
  - right_bottom_compose_ui_probe: right-bottom compose UI did not naturally enter owner/action draw rows
  - right_bottom_compose_promotion_decision: right_bottom_compose_ui_probe: right-bottom compose UI did not naturally enter owner/action draw rows
  - right_bottom_compose_promotion_decision: right-bottom natural UI probe did not enter owner/action draw rows
  - natural UI probe did not enter owner/action draw rows

### Right Bottom Blocker Triage

- Status: PASS
- JSON: `captures\current\right-bottom-blocker-triage-current.json`
- Markdown: `captures\current\right-bottom-blocker-triage-current.md`
- classification: `controlled_recovered_but_natural_route_nonpromoting`
- promotion_ready: `False`
- stable_stage_should_change: `False`
- natural_ui_owner_action_rows: `0`
- natural_route_action_descriptor: `{'slot': 'd1', 'x': 1000, 'y': 426, 'callback': '004338e0'}`
- fixture_proof_class: `non_natural_isolated_fixture`
- load_slot_gap_classification: `after_main_load_callback_before_load_menu_case_entry`
- guard_policy: `passes only while the current blocker is explicitly classified as non-promoting: controlled composition is recovered, natural owner/action rows are absent, the natural route is either owner-flag gated, blocked inside the slot5 Render_Begin/DD_Pump/copyback lane, blocked by the documented loop-state/input-resample/source-hold lane, or has only debugger-forced native action-click copyback proof; the next proof path remains hidden diagnosis or approved manual input`
- runtime_policy: `repo-only evidence triage; reads generated JSON reports and does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Visual Artifact Guard

- Status: FAIL
- JSON: `captures\current\right-bottom-visual-artifact-guard-current.json`
- Markdown: `captures\current\right-bottom-visual-artifact-guard-current.md`
- visual_status: `visual_artifact_guard_stale`
- promotion_ready: `False`
- stable_stage_should_change: `False`
- natural_owner_action_rows: `0`
- natural_bottom_right_corner_black: `78.57`
- natural_r8c10_black: `100.0`
- natural_r8c11_black: `100.0`
- guard_policy: `passes only while the current natural right-bottom visual artifact remains explicitly blocked from promotion: controlled composition is recovered, natural owner/action rows are absent, and the lower/right natural regions still show the known black/striped incomplete state`
- runtime_policy: `repo-only visual artifact guard; reads generated JSON reports and does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`
- Failures:
  - visual artifact guard failed: blocker_triage_non_promoting

### Right Bottom Compose Promotion Decision Tests

- Status: PASS
- JSON: `captures\current\right-bottom-compose-promotion-decision-tests-current.json`
- Markdown: `captures\current\right-bottom-compose-promotion-decision-tests-current.md`
- test_count: `7`
- guard_policy: `proves the right-bottom compose promotion decision defers by default, fails closed for missing/failing route/grid/timing gates, rejects placeholder proof files, and only permits promotion with a valid manual proof manifest or an explicit CDB-only override`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for decision CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Compose Evidence Matrix Tests

- Status: PASS
- JSON: `captures\current\right-bottom-compose-evidence-matrix-tests-current.json`
- Markdown: `captures\current\right-bottom-compose-evidence-matrix-tests-current.md`
- test_count: `6`
- guard_policy: `proves the right-bottom compose evidence matrix requires all route gates, hidden-desktop/full-start safety, normal map/visibility proof, natural UI routing, controlled grid-hit proof, route timing/order proof, candidate SHA agreement, and deferred promotion status`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for matrix CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Blocker Triage Tests

- Status: PASS
- JSON: `captures\current\right-bottom-blocker-triage-tests-current.json`
- Markdown: `captures\current\right-bottom-blocker-triage-tests-current.md`
- test_count: `5`
- guard_policy: `proves current right-bottom action-menu triage stays non-promoting, distinguishes controlled composition recovery from natural UI proof, and fails closed if the owner-flag/load-route blocker shape changes`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Visual Artifact Guard Tests

- Status: PASS
- JSON: `captures\current\right-bottom-visual-artifact-guard-tests-current.json`
- Markdown: `captures\current\right-bottom-visual-artifact-guard-tests-current.md`
- test_count: `6`
- guard_policy: `proves the right-bottom visual artifact guard blocks the current stripy/out-of-place natural UI state from promotion and fails closed if the artifact or route state changes`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Grid Hit Summary Tests

- Status: PASS
- JSON: `captures\current\right-bottom-grid-hit-summary-tests-current.json`
- Markdown: `captures\current\right-bottom-grid-hit-summary-tests-current.md`
- test_count: `2`
- guard_policy: `proves the right-bottom grid-hit parser requires ready rows, native coordinate (450,73), expected grid result 0, draw rows, no failure-exit rows, and no AV rows`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for parser CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Grid Hit Probe Guard Tests

- Status: PASS
- JSON: `captures\current\right-bottom-grid-hit-probe-guard-tests-current.json`
- Markdown: `captures\current\right-bottom-grid-hit-probe-guard-tests-current.md`
- test_count: `6`
- guard_policy: `proves the right-bottom grid-hit probe guard rejects missing breakpoints, missing probe/parser markers, visible fallback, stage/surface regressions, missing grid proof, failure-exit rows, and AV rows`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Natural Route Guard Tests

- Status: PASS
- JSON: `captures\current\right-bottom-natural-route-guard-tests-current.json`
- Markdown: `captures\current\right-bottom-natural-route-guard-tests-current.md`
- test_count: `5`
- guard_policy: `proves the natural right-bottom action-route guard fails closed unless the command-99 owner loop is reached, the exact 00433C20 owner-loop descriptor model is present, the 004338E0 descriptor is parked at (1000,426), owner flag bits are zero, owner/action renderer rows are absent, and no AV rows are present`
- runtime_policy: `repo-only fixture tests; launches only in-process parser code; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Natural Route Candidate Matrix Tests

- Status: PASS
- JSON: `captures\current\right-bottom-natural-route-candidate-matrix-tests-current.json`
- Markdown: `captures\current\right-bottom-natural-route-candidate-matrix-tests-current.md`
- test_count: `5`
- guard_policy: `proves the right-bottom natural-route candidate matrix is a non-promoting repo-only classifier for save-state route candidates and current harness blockers`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Slot Fixture Plan Tests

- Status: PASS
- JSON: `captures\current\right-bottom-slot-fixture-plan-tests-current.json`
- Markdown: `captures\current\right-bottom-slot-fixture-plan-tests-current.md`
- test_count: `5`
- guard_policy: `proves the isolated slot5-as-slot0 workaround remains non-promoting, safe to stage outside the repository, and invalid once natural slot5 loading is proven`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Slot Fixture Script Guard Tests

- Status: PASS
- JSON: `captures\current\right-bottom-slot-fixture-script-guard-tests-current.json`
- Markdown: `captures\current\right-bottom-slot-fixture-script-guard-tests-current.md`
- test_count: `7`
- guard_policy: `proves the right-bottom fixture preparation helper stays dry-run by default, copies only after -Execute, refuses live-save/repo outputs, and avoids visible-runtime APIs`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Slot Fixture Runtime Plan Tests

- Status: PASS
- JSON: `captures\current\right-bottom-slot-fixture-runtime-plan-tests-current.json`
- Markdown: `captures\current\right-bottom-slot-fixture-runtime-plan-tests-current.md`
- test_count: `8`
- guard_policy: `proves the future slot fixture runtime route stays hidden-desktop, uses an isolated workdir plus child candidate dir, requires strict fixture slot acceptance, and remains non-promoting`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Slot Fixture Result Summary Tests

- Status: PASS
- JSON: `captures\current\right-bottom-slot-fixture-result-summary-tests-current.json`
- Markdown: `captures\current\right-bottom-slot-fixture-result-summary-tests-current.md`
- test_count: `10`
- guard_policy: `proves future right-bottom slot fixture CDB logs can be classified as load failure, owner-flag blocked, owner-loop without action, owner/action reached, slot mismatch, or AV failure with strict LOADSAVE slot consistency`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Load Slot Route Limit Guard Tests

- Status: PASS
- JSON: `captures\current\load-slot-route-limit-tests-current.json`
- Markdown: `captures\current\load-slot-route-limit-tests-current.md`
- test_count: `6`
- guard_policy: `proves the load-slot route boundary remains a non-promoting repo-only classifier for the current slot5/right-bottom harness blocker`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Load Slot Timeout Phase Tests

- Status: PASS
- JSON: `captures\current\load-slot-timeout-phase-tests-current.json`
- Markdown: `captures\current\load-slot-timeout-phase-tests-current.md`
- test_count: `4`
- guard_policy: `proves the load-slot timeout phase classifier preserves the current pre-load-menu-loop blocker shape for rows 3-5`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Load Slot Entry Gap Tests

- Status: PASS
- JSON: `captures\current\load-slot-entry-gap-tests-current.json`
- Markdown: `captures\current\load-slot-entry-gap-tests-current.md`
- test_count: `6`
- guard_policy: `proves the load-slot entry-gap report preserves the distinction between early descriptor rows and real load-menu case entry`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Load Slot Transition Probe Guard Tests

- Status: PASS
- JSON: `captures\current\load-slot-transition-probe-guard-tests-current.json`
- Markdown: `captures\current\load-slot-transition-probe-guard-tests-current.md`
- test_count: `6`
- guard_policy: `proves the focused transition extra probe and surface-dump runner are ready for parameterized late-armed load-row selection after real load-menu entry`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Load Slot Transition Run Plan Tests

- Status: PASS
- JSON: `captures\current\load-slot-transition-run-plan-tests-current.json`
- Markdown: `captures\current\load-slot-transition-run-plan-tests-current.md`
- test_count: `8`
- guard_policy: `proves the transition command plan stays hidden, targets the current rows 3-5 pre-entry blocker, and remains non-promoting`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Load Slot Transition Geometry Guard Tests

- Status: PASS
- JSON: `captures\current\load-slot-transition-geometry-guard-tests-current.json`
- Markdown: `captures\current\load-slot-transition-geometry-guard-tests-current.md`
- test_count: `6`
- guard_policy: `proves the transition plan stays tied to x=320, y=166+22*slot row geometry and requires entry/slot-match summaries`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Load Slot Transition Probe Preview Tests

- Status: PASS
- JSON: `captures\current\load-slot-transition-probe-preview-tests-current.json`
- Markdown: `captures\current\load-slot-transition-probe-preview-tests-current.md`
- test_count: `6`
- guard_policy: `proves generated row-specific transition probes have no unresolved placeholders, keep slot-specific select/accept conditions, and preserve the planned raw mouse values`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Load Slot Transition Summary Tests

- Status: PASS
- JSON: `captures\current\load-slot-transition-summary-tests-current.json`
- Markdown: `captures\current\load-slot-transition-summary-tests-current.md`
- test_count: `9`
- guard_policy: `proves future LSTRANS logs can be classified as pre-entry stalls, entry-without-LOADSAVE blockers, or late-entry load success, and fails closed on target-slot drift`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Load Slot Transition Readiness

- Status: FAIL
- JSON: `captures\current\load-slot-transition-readiness-current.json`
- Markdown: `captures\current\load-slot-transition-readiness-current.md`
- target_rows: `[3, 4, 5]`
- blocked_rows: `[3, 4, 5]`
- stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`
- candidate_root: `C:\ClashTests\load-slot-transition`
- command_count: `3`
- summary_command_count: `3`
- preview_sha256: `{'3': 'C64A3D0796E9A4000DA5D8DE27D5B4DA307BD2EBDE98FE7F8F45DC454A26F8C6', '4': '697C8481B5C0FA1FA109E4A85E8502FF2A57E723AF05E4F8B390C7C806826CD7', '5': '3864C049BB9E6CD91E7FB995163E999BDADEEFB8411CC4308756ECF87EB54509'}`
- result_acceptance: `['entry proof: load_slot_transition_summary.py --require-entry --require-slot-match passes for each row with consistent target_slot values', 'success proof: if LOADSAVE/PlayGame appear, rerun the same summary with --require-success and require those slot rows to match before treating it as load success', 'slot forcing proof: pre-0044895A load-slot coordinate forcing stays disabled; slot selection is armed only at or after the load-menu entry', 'promotion remains blocked until natural owner/action proof or approved manual DirectInput proof exists']`
- Failures:
  - transition readiness check failed: entry_gap_passed
  - transition readiness check failed: run_plan_passed
  - transition readiness check failed: geometry_guard_passed
  - transition readiness check failed: probe_preview_passed

### Load Slot Transition Readiness Tests

- Status: PASS
- JSON: `captures\current\load-slot-transition-readiness-tests-current.json`
- Markdown: `captures\current\load-slot-transition-readiness-tests-current.md`
- test_count: `7`
- guard_policy: `proves the aggregate transition readiness report stays hidden-desktop, row-specific, strict about summary and target-slot acceptance, and non-promoting`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Owner Flag Static Guard

- Status: PASS
- JSON: `captures\current\right-bottom-owner-flag-static-guard-current.json`
- Markdown: `captures\current\right-bottom-owner-flag-static-guard-current.md`
- exe: `C:\Clash\clash95.exe`
- actual_sha256: `500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE`
- pattern_count: `9`
- passed_pattern_count: `9`
- command_99_callback_verified: `True`
- owner_globals_verified: `True`
- action_bit2_gate_verified: `True`
- owner_loop_bit_gates_verified: `True`
- guard_policy: `the natural right-bottom action route must retain the command-99 owner-loop callback, owner-global writes, 004338E0 owner flag bit-2 early-return gate, and 00433C20 owner-loop bit gates before the current owner-flag blocker can be treated as understood evidence`
- runtime_policy: `local original-executable byte inspection only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Owner Flag Static Guard Tests

- Status: PASS
- JSON: `captures\current\right-bottom-owner-flag-static-guard-tests-current.json`
- Markdown: `captures\current\right-bottom-owner-flag-static-guard-tests-current.md`
- test_count: `4`
- guard_policy: `proves the static owner-flag guard fails closed on executable SHA drift, 004338E0 gate drift, and missing local executable evidence`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Owner Flag Inventory Tests

- Status: PASS
- JSON: `captures\current\right-bottom-owner-flag-inventory-tests-current.json`
- Markdown: `captures\current\right-bottom-owner-flag-inventory-tests-current.md`
- test_count: `3`
- guard_policy: `proves the owner-flag inventory preserves the current right-bottom conclusion: forced owner/action routes exist, the natural command-99 route is owner-flag gated, and no natural route already reaches owner/action rows`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Right Bottom Route Timing Guard Tests

- Status: PASS
- JSON: `captures\current\right-bottom-route-timing-guard-tests-current.json`
- Markdown: `captures\current\right-bottom-route-timing-guard-tests-current.md`
- test_count: `6`
- guard_policy: `proves the right-bottom route timing guard rejects missing copyback/grid markers, marker-order regressions, visible fallback, surface/stage/SHA drift, grid proof failures, failure-exit rows, and AV rows`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Castle Overview Evidence

- Status: FAIL
- JSON: `captures\current\castle-overview-evidence-current.json`
- Markdown: `captures\current\castle-overview-evidence-current.md`
- promotion_status: `validation_stage_only`
- candidate_sha256: `None`
- patches: `None`
- Failures:
  - patch_stage: candidate executable does not exist: C:\ClashTests\cdb-castle-overview-nativerender-flags1f-multihit\clash95_hd_surfdump_20260515_105557.exe

### Castle Owner Records Summary Tests

- Status: PASS
- JSON: `captures\current\castle-owner-records-summary-tests-current.json`
- Markdown: `captures\current\castle-owner-records-summary-tests-current.md`
- test_count: `3`
- guard_policy: `proves the castle owner-record parser recognizes active, retired, nonempty, interesting, and flag-value records, and fails closed for no-active, require-interesting, forbid-interesting, and truncated raw-dump cases`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for parser CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Castle Save Owner Flag Scan Tests

- Status: PASS
- JSON: `captures\current\castle-save-owner-flag-scan-tests-current.json`
- Markdown: `captures\current\castle-save-owner-flag-scan-tests-current.md`
- test_count: `4`
- guard_policy: `proves the installed-save owner-flag scan stores only metadata, detects natural 004338E0 bit-2 route candidates, and fails closed when required save evidence is unavailable`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Castle Overview Evidence Matrix Tests

- Status: PASS
- JSON: `captures\current\castle-overview-evidence-matrix-tests-current.json`
- Markdown: `captures\current\castle-overview-evidence-matrix-tests-current.md`
- test_count: `5`
- guard_policy: `proves the castle overview evidence matrix aggregates every required component gate, fails when any required gate fails, requires displayed-wrapper proof in the focused hitbox gate, reports target-done completion proof in multi-hit gates, preserves validation-stage-only status, and its CLI fails closed under --require-pass`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for matrix CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Castle Overview Gate Tests

- Status: PASS
- JSON: `captures\current\castle-overview-gate-tests-current.json`
- Markdown: `captures\current\castle-overview-gate-tests-current.md`
- test_count: `4`
- guard_policy: `proves the castle overview visual/catalog gate rejects missing readiness, AV rows, missing or wrong overview post-draw and surface sizes, missing expected commands, centered-geometry regressions, barracks baseline regressions, and fails closed under --require-pass`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for gate CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Castle Overview Hitbox Summary Tests

- Status: PASS
- JSON: `captures\current\castle-overview-hitbox-summary-tests-current.json`
- Markdown: `captures\current\castle-overview-hitbox-summary-tests-current.md`
- test_count: `3`
- guard_policy: `proves the focused castle overview hitbox parser recognizes displayed/native hit rows, descriptor and click-gate rows, callback suppression, ready size, callback entry, AV rows, and fails closed under required CLI flags`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for parser CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Castle Overview Hitmap Summary Tests

- Status: PASS
- JSON: `captures\current\castle-overview-hitmap-summary-tests-current.json`
- Markdown: `captures\current\castle-overview-hitmap-summary-tests-current.md`
- test_count: `3`
- guard_policy: `proves the castle overview hitmap parser recognizes raw command IDs, counts, bounding boxes, centered displayed coordinates, required present/absent flags, and wrong raw dimensions`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for parser CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Castle Overview Multihit Summary Tests

- Status: PASS
- JSON: `captures\current\castle-overview-multihit-summary-tests-current.json`
- Markdown: `captures\current\castle-overview-multihit-summary-tests-current.md`
- test_count: `3`
- guard_policy: `proves the castle overview multi-hit parser recognizes expected target rows, hit-test results, descriptor, click-gate, target-done rows, ready size, callback entry, AV rows, and fails closed under required CLI flags`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for parser CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Castle Overview Promotion Decision

- Status: FAIL
- JSON: `captures\current\castle-overview-promotion-decision-current.json`
- Markdown: `captures\current\castle-overview-promotion-decision-current.md`
- decision: `defer_stable_promotion`
- stable_stage_should_change: `False`
- current_stable_stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- focused_displayed_wrapper_ok: `True`
- visible_multihit_completion_ok: `True`
- dormant_multihit_completion_ok: `True`
- manual_input_proof_valid: `False`
- Failures:
  - castle overview evidence matrix is not passing

### Castle Overview Promotion Decision Tests

- Status: PASS
- JSON: `captures\current\castle-overview-promotion-decision-tests-current.json`
- Markdown: `captures\current\castle-overview-promotion-decision-tests-current.md`
- test_count: `7`
- guard_policy: `proves the castle overview promotion decision defers stable promotion by default, fails when the evidence matrix fails or when focused displayed-wrapper / visible-dormant multi-hit completion proof is missing, only marks the stable stage as changeable when a valid manual proof manifest or an explicit CDB-only override is supplied, rejects placeholder proof files, and its CLI fails closed under --require-pass`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for decision CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Castle Overview Baseline Recheck

- Status: FAIL
- JSON: `captures\current\castle-overview-baseline-recheck-current.json`
- Markdown: `captures\current\castle-overview-baseline-recheck-current.md`
- overview_baseline_run: `captures\archive\cdb-surface-dump-20260515-105041`
- overview_surface_size: `[800, 600]`
- overview_centered_geometry: `True`
- barracks_descriptor_click: `True`
- barracks_controlled_4356c0: `True`
- latest_matrix_promotion_status: `validation_stage_only`
- candidate_sha256: `None`
- visible_multihit_completion_ok: `True`
- dormant_multihit_completion_ok: `True`
- Failures:
  - latest_castle_overview_matrix: patch_stage: candidate executable does not exist: C:\ClashTests\cdb-castle-overview-nativerender-flags1f-multihit\clash95_hd_surfdump_20260515_105557.exe

### Castle Overview Baseline Recheck Tests

- Status: PASS
- JSON: `captures\current\castle-overview-baseline-recheck-tests-current.json`
- Markdown: `captures\current\castle-overview-baseline-recheck-tests-current.md`
- test_count: `6`
- guard_policy: `proves the castle overview baseline recheck rejects stale overview visual baselines, stale barracks controlled-stop baselines, and failing latest castle overview matrices, including matrices without visible/dormant target-done completion proof`
- runtime_policy: `repo-only in-process fixture tests; does not launch Clash95, CDB, wrappers, PowerShell, Python child processes, or visible windows`

### Castle Overview Probe Guard

- Status: PASS
- JSON: `captures\current\castle-overview-probe-guard-current.json`
- Markdown: `captures\current\castle-overview-probe-guard-current.md`
- breakpoints: `['00422544', '0042257E', '00422590', '0042262C']`
- displayed_hit_ok: `True`
- displayed_wrapper_ok: `True`
- click_gate_ok: `True`
- callback_called: `False`
- av_count: `0`
- guard_policy: `focused overview hitbox proof must keep the descriptor-loop breakpoints, forbid the old crashing overview descriptor-input wrapper marker, and continue to prove the displayed-coordinate wrapper and click gate with no AV`

### Castle Overview Probe Guard Tests

- Status: PASS
- JSON: `captures\current\castle-overview-probe-guard-tests-current.json`
- Markdown: `captures\current\castle-overview-probe-guard-tests-current.md`
- test_count: `8`
- guard_policy: `proves the castle overview probe guard rejects missing descriptor-loop breakpoints, missing probe/parser markers, old crashing overview wrapper markers, AV rows, missing wrapper/gate proof rows, and surface-size regressions in the focused hitbox log, while its CLI writes outputs and fails closed under --require-pass`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Battle Ui Summary Tests

- Status: PASS
- JSON: `captures\current\battle-ui-summary-tests-current.json`
- Markdown: `captures\current\battle-ui-summary-tests-current.md`
- test_count: `4`
- guard_policy: `proves battle summary classification is marker-driven, centered-offset aware, AV-aware, and refuses to promote route-candidate rows into battle-screen proof`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for parser CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Battle Ui Gate Tests

- Status: PASS
- JSON: `captures\current\battle-ui-gate-tests-current.json`
- Markdown: `captures\current\battle-ui-gate-tests-current.md`
- test_count: `4`
- guard_policy: `proves the battle UI gate is fail-closed across runtime evidence, patch-stage, candidate-location, and stable-regression boundaries before any battle patch group exists`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for gate CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Battle Visible Input Summary

- Status: PASS
- JSON: `captures\current\battle-visible-input-current.json`
- Markdown: `captures\current\battle-visible-input-summary-current.md`
- run_count: `3`
- focused_completion_percent: `99.91`
- summary_passed: `False`
- command_ready_run_count: `2`
- click_consumed_run_count: `0`
- invalid_run_count: `1`
- real_visible_click_consumed: `False`
- open_blocker: `real visible click-to-callback proof`

### Battle Visible Input Summary Tests

- Status: PASS
- JSON: `captures\current\battle-visible-input-summary-tests-current.json`
- Markdown: `captures\current\battle-visible-input-summary-tests-current.md`
- test_count: `5`
- guard_policy: `proves visible-input evidence cannot be promoted from command readiness to pass until a real visible click is consumed by the battle command callback`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for parser CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Battle Ui Evidence Matrix

- Status: FAIL
- JSON: `captures\current\battle-ui-evidence-current.json`
- Markdown: `captures\current\battle-ui-evidence-current.md`
- focused_completion_percent: `99.91`
- visible_input_summary_passed: `False`
- visible_input_command_ready_runs: `2`
- visible_input_click_consumed_runs: `0`
- visible_input_invalid_runs: `1`
- real_visible_click_consumed: `False`
- promotion_status: `validation_stage_only`
- stable_stage_should_change: `False`
- open_items: `['real visible click-to-callback proof remains open', '1 invalid visible-input run(s) are retained as negative evidence']`
- Failures:
  - stable_smoke: stable HD-map smoke did not pass

### Battle Ui Evidence Matrix Tests

- Status: PASS
- JSON: `captures\current\battle-ui-evidence-matrix-tests-current.json`
- Markdown: `captures\current\battle-ui-evidence-matrix-tests-current.md`
- test_count: `11`
- guard_policy: `proves the focused battle/right-bottom command lane stays below 100% until real visible click-to-callback evidence exists`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for matrix CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Battle Visible Harness Guard

- Status: PASS
- JSON: `captures\current\battle-visible-harness-guard-current.json`
- Markdown: `captures\current\battle-visible-harness-guard-current.md`
- script: `scripts\cdb\run_cdb_battle_visible_input_probe.ps1`
- runtime_policy: `repo-only source inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`
- check_count: `9`

### Battle Visible Harness Guard Tests

- Status: PASS
- JSON: `captures\current\battle-visible-harness-guard-tests-current.json`
- Markdown: `captures\current\battle-visible-harness-guard-tests-current.md`
- test_count: `5`
- guard_policy: `proves the visible battle input harness keeps explicit approval, fatal CDB log detection, post-g gating, and incremental log scanning before any future manual run`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Patch Definition Guard

- Status: PASS
- JSON: `captures\current\patch-definition-current.json`
- Markdown: `captures\current\patch-definition-current.md`
- patcher_default_stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- patch_count: `191`
- patch_group_count: `43`
- stage_count: `55`
- validation_groups_in_stable: `[]`
- overlap_failure_count: `0`
- guard_policy: `patch stage definitions must reference real groups, keep validation-only groups out of stable, keep validation stages scoped to stable plus expected extras, and avoid incompatible selected offset overlaps`
- runtime_policy: `repo-only patch-table inspection; does not read, build, or execute game executables`

### Patch Definition Guard Tests

- Status: PASS
- JSON: `captures\current\patch-definition-tests-current.json`
- Markdown: `captures\current\patch-definition-tests-current.md`
- test_count: `6`
- guard_policy: `proves patch/stage definitions fail closed on drift, leakage, unknown groups, or incompatible offset overlaps`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Stable Stage Guard

- Status: FAIL
- JSON: `captures\current\stable-stage-guard-current.json`
- Markdown: `captures\current\stable-stage-guard-current.md`
- current_stable_stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- patcher_default_stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- validation_only_groups_in_stable: `[]`
- mapsurface_stages_checked: `['gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapclip', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter-inputprobe', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter-no-castleinput', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitselectactionbar', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-unitselectactionbarpostredraw', 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-vswitch', 'gameplay-menu640-centered-map12-hybridmouse-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch']`
- mapsurface_with_menu_surface: `[]`
- mapsurface_missing_upgrade: `[]`
- Failures:
  - castle_overview_promotion_decision: castle overview promotion decision is not passing
  - castle_overview_evidence_matrix: castle overview evidence matrix is not passing

### Stable Stage Guard Tests

- Status: PASS
- JSON: `captures\current\stable-stage-guard-tests-current.json`
- Markdown: `captures\current\stable-stage-guard-tests-current.md`
- test_count: `10`
- guard_policy: `proves the stable-stage guard rejects patcher-default drift, validation-only group leakage into the stable stage, missing validation-stage groups, mapsurface stages that reintroduce global menu-surface allocation or lose the gameplay-only map surface upgrade, and promotion decisions/evidence matrices that would change the stable stage or omit required castle focused/multihit proof`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Exe Artifact Guard

- Status: PASS
- JSON: `captures\current\exe-artifact-guard-current.json`
- Markdown: `captures\current\exe-artifact-guard-current.md`
- filesystem_exes: `0`
- tracked_exes: `0`
- allowed_staged_deletions: `0`
- root_exe_ignore_present: `True`

### Surface Dump Policy Guard

- Status: PASS
- JSON: `captures\current\surface-dump-policy-guard-current.json`
- Markdown: `captures\current\surface-dump-policy-guard-current.md`
- script: `scripts\cdb\run_cdb_surface_dump.ps1`
- guard_policy: `surface-dump harness must default to hidden desktop and require -AllowVisibleDesktop for active-desktop fallback`

### Visible Runtime Launcher Guard

- Status: PASS
- JSON: `captures\current\visible-runtime-launcher-guard-current.json`
- Markdown: `captures\current\visible-runtime-launcher-guard-current.md`
- script_count: `8`
- passing_script_count: `8`
- inventory_risky_script_count: `0`
- inventory_unclassified_risky_script_count: `0`
- guard_policy: `legacy visible-runtime launchers/helpers must fail closed unless -AllowVisibleRuntime is explicitly supplied after user approval; guarded child helpers must receive the same switch; root PowerShell risky-call inventory must be guarded or explicitly exempt`

### Visible Runtime Launcher Guard Tests

- Status: PASS
- JSON: `captures\current\visible-runtime-launcher-guard-tests-current.json`
- Markdown: `captures\current\visible-runtime-launcher-guard-tests-current.md`
- test_count: `10`
- guard_policy: `proves legacy visible-runtime launchers/helpers require -AllowVisibleRuntime before any risky Start-Process, window-focus, cursor, SendInput, PostMessage, or CopyFromScreen call, requires guarded child helpers to receive the same switch, and proves root risky-call inventory rejects unclassified scripts while allowing documented exemptions`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Python Runtime Safety Guard

- Status: PASS
- JSON: `captures\current\python-runtime-safety-current.json`
- Markdown: `captures\current\python-runtime-safety-current.md`
- risky_file_count: `88`
- classification_counts: `{'safe': 111, 'exempt': 15, 'manual_visible_runtime_gated': 2, 'test_fixture': 71}`
- guard_policy: `Python helpers with process launch, ctypes, Win32 window/input, SendInput, or PostMessage usage must be test fixtures, explicitly gated, or explicitly exempt`
- runtime_policy: `repo-only source inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Python Runtime Safety Guard Tests

- Status: PASS
- JSON: `captures\current\python-runtime-safety-tests-current.json`
- Markdown: `captures\current\python-runtime-safety-tests-current.md`
- test_count: `3`
- guard_policy: `proves risky Python runtime/window/input helpers are gated, exempt, or fail closed`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### No Visible Runtime Guard

- Status: PASS
- JSON: `captures\current\no-visible-runtime-guard-current.json`
- Markdown: `captures\current\no-visible-runtime-guard-current.md`
- run_count: `19`
- hidden_run_count: `19`
- guard_policy: `all referenced CDB surface-dump runs must be hidden-desktop evidence`

### No Visible Runtime Guard Tests

- Status: PASS
- JSON: `captures\current\no-visible-runtime-guard-tests-current.json`
- Markdown: `captures\current\no-visible-runtime-guard-tests-current.md`
- test_count: `5`
- guard_policy: `proves the no-visible runtime guard requires hidden-desktop launch summaries, explicit no-visible runtime policy text, present run summaries, and CLI fail-closed behavior`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Process Hygiene Guard

- Status: PASS
- JSON: `captures\current\process-hygiene-guard-current.json`
- Markdown: `captures\current\process-hygiene-guard-current.md`
- matching_process_count: `0`
- target_exact_names: `['cdb.exe']`
- target_prefixes: `['clash95']`
- guard_policy: `no cdb.exe or clash95*.exe process may be running after evidence refresh`

### Process Hygiene Guard Tests

- Status: PASS
- JSON: `captures\current\process-hygiene-guard-tests-current.json`
- Markdown: `captures\current\process-hygiene-guard-tests-current.md`
- test_count: `5`
- guard_policy: `proves the process hygiene guard rejects leftover cdb.exe/clash95* processes, snapshot failures, and CLI fail-closed cases`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### No Popup Guard Tests

- Status: PASS
- JSON: `captures\current\no-popup-guard-tests-current.json`
- Markdown: `captures\current\no-popup-guard-tests-current.md`
- test_count: `8`
- guard_policy: `proves the no-popup boundary guard and surface-dump launcher policy guard reject missing evidence links, missing/failing refresh checks, missing supporting reports, and ungated visible fallback while keeping negative CLI outputs out of current reports`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Manual Directinput Checklist

- Status: PASS
- JSON: `captures\current\manual-directinput-validation-checklist-current.json`
- Markdown: `captures\current\manual-directinput-validation-checklist-current.md`
- status: `pending_manual_validation`
- item_count: `5`
- pending_count: `5`
- promotion_ready: `False`
- stable_stage_should_change: `False`
- visible_runtime_requires_approval: `True`
- manual_proof_valid: `False`

### Manual Directinput Checklist Tests

- Status: PASS
- JSON: `captures\current\manual-directinput-validation-checklist-tests-current.json`
- Markdown: `captures\current\manual-directinput-validation-checklist-tests-current.md`
- test_count: `9`
- guard_policy: `proves the manual DirectInput checklist enumerates the remaining manual targets, keeps promotion blocked without valid proof, validates manual proof manifests including candidate/stage, observation, no-crash, and process-hygiene records, records the no-popup operator preference, and fails closed for incomplete checklist data`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for checklist CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Manual Directinput Proof Template

- Status: PASS
- JSON: `captures\current\manual-directinput-proof-template-report-current.json`
- Markdown: `captures\current\manual-directinput-proof-template-current.md`
- template_json: `captures\current\manual-directinput-proof-template-current.json`
- template_valid_as_proof: `False`
- required_id_count: `5`
- template_failure_count: `32`
- guard_policy: `manual proof template must document the accepted manifest shape while remaining invalid as proof until approved manual evidence replaces every placeholder`
- runtime_policy: `repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Manual Directinput Proof Template Tests

- Status: PASS
- JSON: `captures\current\manual-directinput-proof-template-tests-current.json`
- Markdown: `captures\current\manual-directinput-proof-template-tests-current.md`
- test_count: `4`
- guard_policy: `proves the manual DirectInput proof template documents the proof shape, stays invalid until placeholders are replaced, and can become valid only after all required manual proof fields are supplied`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for template CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Manual Directinput Run Plan

- Status: PASS
- JSON: `captures\current\manual-directinput-run-plan-current.json`
- Markdown: `captures\current\manual-directinput-run-plan-current.md`
- manual_target_count: `5`
- command_count: `5`
- all_commands_have_allow_visible_runtime: `True`
- visible_runtime_requires_approval: `True`
- proof_ready: `False`
- promotion_ready: `False`
- guard_policy: `manual DirectInput commands remain templates until explicit user approval; every visible runtime command must carry -AllowVisibleRuntime and the proof manifest must be validated before promotion`
- runtime_policy: `repo-only command planner; reads generated JSON and writes JSON/Markdown reports; does not run PowerShell, launch Clash95, CDB, wrappers, move the mouse, or open visible windows`

### Manual Directinput Run Plan Tests

- Status: PASS
- JSON: `captures\current\manual-directinput-run-plan-tests-current.json`
- Markdown: `captures\current\manual-directinput-run-plan-tests-current.md`
- test_count: `5`
- guard_policy: `proves the manual DirectInput run plan remains repo-only, keeps visible commands approval-gated with -AllowVisibleRuntime, and cannot substitute for a valid manual proof manifest`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Promotion Override Manifest

- Status: PASS
- JSON: `captures\current\promotion-override-manifest-current.json`
- Markdown: `captures\current\promotion-override-manifest-current.md`
- override_active: `False`
- manifest_supplied: `False`
- manifest_valid: `False`
- guard_policy: `CDB-only promotion requires an explicit valid override manifest; absence of a manifest keeps current evidence override-inactive`
- runtime_policy: `repo-only manifest validation; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Promotion Override Manifest Tests

- Status: PASS
- JSON: `captures\current\promotion-override-manifest-tests-current.json`
- Markdown: `captures\current\promotion-override-manifest-tests-current.md`
- test_count: `5`
- guard_policy: `proves CDB-only promotion overrides require an explicit valid manifest`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Promotion Override Guard

- Status: PASS
- JSON: `captures\current\promotion-override-guard-current.json`
- Markdown: `captures\current\promotion-override-guard-current.md`
- right_bottom_override: `False`
- castle_override: `False`
- manual_checklist_override: `False`
- manual_checklist_promotion_ready: `False`
- guard_policy: `current evidence must keep CDB-only promotion overrides inactive until manual proof or an explicit override decision is intentionally supplied`
- runtime_policy: `repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Promotion Override Guard Tests

- Status: PASS
- JSON: `captures\current\promotion-override-guard-tests-current.json`
- Markdown: `captures\current\promotion-override-guard-tests-current.md`
- test_count: `7`
- guard_policy: `proves the current evidence fails closed if CDB-only promotion overrides, manual proof, or promotion-ready states become active unexpectedly`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Handoff Freshness Guard

- Status: PASS
- JSON: `captures\current\handoff-freshness-guard-current.json`
- Markdown: `captures\current\handoff-freshness-guard-current.md`
- guard_policy: `handoff docs must mention the current route timing guard, keep the right-bottom validation stage out of stable until manual proof or explicit CDB-only override, keep the non-promoting manual proof template visible, keep the percentage completion summary visible, keep the right-bottom owner-flag inventory visible, keep the load-slot route-limit boundary visible, keep the load-slot transition readiness matrix visible, preserve the user's no-popup runtime preference, require the visible-runtime launcher approval guard, and avoid stale route/input-safety, legacy visible-capture, or VM/visual-smoke blockers`
- phrase_groups: `{'route_timing_artifacts': True, 'owner_flag_inventory_artifacts': True, 'load_slot_route_limit_artifacts': True, 'load_slot_transition_readiness_artifacts': True, 'manual_or_override_blocker': True, 'no_visible_runtime_warning': True, 'no_popup_operator_preference': True, 'right_bottom_safety_done': True, 'manual_checklist_artifact': True, 'manual_proof_template_artifact': True, 'completion_summary_artifact': True, 'visible_runtime_launcher_guard': True}`
- loop_phrase_groups: `{'loop_load_slot_transition_readiness_artifacts': True}`

### Handoff Freshness Guard Tests

- Status: PASS
- JSON: `captures\current\handoff-freshness-guard-tests-current.json`
- Markdown: `captures\current\handoff-freshness-guard-tests-current.md`
- test_count: `16`
- guard_policy: `proves the handoff freshness guard rejects stale route/input blockers, missing route timing links, stale legacy outside-debugger or visible-capture tasks, stale VM/visual-smoke tasks, missing owner-flag inventory artifacts, missing load-slot transition readiness artifacts, missing loop-handoff load-slot transition readiness artifacts, missing manual-proof or explicit CDB-only promotion blockers, missing manual DirectInput checklist artifacts, missing manual proof template artifacts, missing completion summary artifacts, missing no-popup operator preference text, and missing visible runtime launcher guard artifacts`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Current Completion Summary Tests

- Status: PASS
- JSON: `captures\current\current-completion-summary-tests-current.json`
- Markdown: `captures\current\current-completion-summary-tests-current.md`
- test_count: `3`
- guard_policy: `proves the generated percentage summary stays machine-checkable and does not claim full-game completion while manual proof is absent`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Current Completion Summary

- Status: PASS
- JSON: `captures\current\current-completion-summary-current.json`
- Markdown: `captures\current\current-completion-summary-current.md`
- full_game_complete: `False`
- full_game_percent_statement: `not 100%; manual DirectInput proof and stable promotion remain blocked`
- percentages: `{'current_repo_evidence_gates': 85.29, 'focused_battle_right_bottom_lane': 99.91, 'right_bottom_promotion_gate': 85.71, 'manual_directinput_validation': 0.0}`

### Hd Soak Harness Guard

- Status: PASS
- JSON: `captures\current\hd-soak-harness-guard-current.json`
- Markdown: `captures\current\hd-soak-harness-guard-current.md`
- script: `scripts\smoke\run_hd_soak.ps1`
- guard_policy: `HD soak harness must stay opt-in, protected-stage, non-promoting, and artifact-safe`
- runtime_policy: `repo-only source inspection; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows`

### Hd Soak Harness Guard Tests

- Status: PASS
- JSON: `captures\current\hd-soak-harness-guard-tests-current.json`
- Markdown: `captures\current\hd-soak-harness-guard-tests-current.md`
- test_count: `6`
- guard_policy: `proves the opt-in soak harness stays protected-stage, approval-gated, non-promoting, and artifact-safe`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Hd Soak Route Coverage

- Status: PASS
- JSON: `captures\current\hd-soak-route-coverage-current.json`
- Markdown: `captures\current\hd-soak-route-coverage-current.md`
- implemented_routes: `['menu-idle', 'map-idle', 'map-pan', 'custom']`
- implemented_tiers: `['short2', 'short10', 'short30', 'custom']`
- counts: `{'release_lane_count': 10, 'implemented_lane_count': 3, 'planned_lane_count': 7, 'required_short_route_count': 3}`
- coverage_complete: `False`
- next_runtime_route: `menu-idle`
- runtime_policy: `repo-only soak route coverage inventory; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows`

### Hd Soak Route Coverage Tests

- Status: PASS
- JSON: `captures\current\hd-soak-route-coverage-tests-current.json`
- Markdown: `captures\current\hd-soak-route-coverage-tests-current.md`
- test_count: `5`
- guard_policy: `proves the soak harness exposes the required short routes and tiers while future castle, battle, right-bottom, save/load, turn, and campaign lanes stay planned/non-promoting`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Hd Soak Report Guard

- Status: FAIL
- JSON: `captures\current\hd-soak-report-guard-current.json`
- Markdown: `captures\current\hd-soak-report-guard-current.md`
- source_report: `captures\current\hd-soak-short-current.json`
- stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- tier: `short2`
- route: `menu-idle`
- duration_sec: `120`
- executed: `False`
- right_bottom_promotion_blocked: `True`
- runtime_policy: `repo-only soak report inspection; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows`
- Failures:
  - soak report was not produced by an execution run
  - candidate_sha256 is missing or is not a SHA-256 hex digest
  - patch_stage_report path is missing
  - frame sample count 0 is below 2
  - minimum nonblack percent 0.0 is below 10.0
  - minimum unique sampled colors 0.0 is below 8
  - process was not stopped cleanly by the harness

### Hd Soak Report Guard Tests

- Status: PASS
- JSON: `captures\current\hd-soak-report-guard-tests-current.json`
- Markdown: `captures\current\hd-soak-report-guard-tests-current.md`
- test_count: `6`
- guard_policy: `proves executed soak reports must carry protected-stage patch evidence, base/candidate SHA-256s, external artifact locations, stable frame metrics, clean process stop, and non-promoting input status`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Hd Soak Failure Triage

- Status: FAIL
- JSON: `captures\current\hd-soak-failure-triage-current.json`
- Markdown: `captures\current\hd-soak-failure-triage-current.md`
- classification: `not_executed_pending_approval`
- next_probe: `obtain explicit approval for the exact short2 visible-runtime command, then rerun the soak`
- route: `menu-idle`
- final_route_marker: `pending_approval`
- runtime_policy: `repo-only soak failure triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows`
- Failures:
  - short2 menu-idle soak was not executed because visible-runtime escalation was not approved

### Hd Soak Failure Triage Tests

- Status: PASS
- JSON: `captures\current\hd-soak-failure-triage-tests-current.json`
- Markdown: `captures\current\hd-soak-failure-triage-tests-current.md`
- test_count: `6`
- guard_policy: `proves soak failures are classified into approval, crash, render/palette, input-route, capture, artifact-budget, cleanup, or unclassified buckets with next probes`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Hd Endurance Release Checklist

- Status: FAIL
- JSON: `captures\current\hd-endurance-release-checklist-current.json`
- Markdown: `captures\current\hd-endurance-release-checklist-current.md`
- full_game_complete: `False`
- counts: `{'total': 14, 'passed': 4, 'blocked': 6, 'missing': 4}`
- next_milestone: `{'id': 'short2_menu_idle_soak', 'title': 'First short2 menu-idle soak passes', 'next_probe': 'run the approval-gated short2 menu-idle soak on the protected stage'}`
- runtime_policy: `repo-only endurance release checklist; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows`
- Failures:
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

### Hd Endurance Release Checklist Tests

- Status: PASS
- JSON: `captures\current\hd-endurance-release-checklist-tests-current.json`
- Markdown: `captures\current\hd-endurance-release-checklist-tests-current.md`
- test_count: `5`
- guard_policy: `proves the release-horizon checklist only passes when short/long soak, manual input, screen-route, continuity, hygiene, and promotion-boundary evidence are all current`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Hd Endurance Next Actions

- Status: PASS
- JSON: `captures\current\hd-endurance-next-actions-current.json`
- Markdown: `captures\current\hd-endurance-next-actions-current.md`
- status: `waiting_for_explicit_visible_runtime_approval`
- next_action: `run_short2_menu_idle_soak`
- requires_explicit_user_approval: `True`
- runtime_policy: `repo-only endurance next-action triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows`

### Hd Endurance Next Actions Tests

- Status: PASS
- JSON: `captures\current\hd-endurance-next-actions-tests-current.json`
- Markdown: `captures\current\hd-endurance-next-actions-tests-current.md`
- test_count: `4`
- guard_policy: `proves the next-action report stays repo-only, separates safe dry-run commands from approval-gated visible runtime commands, pins canonical short2 report outputs, and records post-run validation steps`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Hd Soak Short Tier Ladder

- Status: PASS
- JSON: `captures\current\hd-soak-short-tier-ladder-current.json`
- Markdown: `captures\current\hd-soak-short-tier-ladder-current.md`
- ladder_complete: `False`
- current_step: `short2_menu_idle`
- current_step_status: `approval_required`
- long_tiers_locked: `True`
- future_lanes_locked: `True`
- right_bottom_promotion_blocked: `True`
- runtime_policy: `repo-only short-tier soak ladder; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows`

### Hd Soak Short Tier Ladder Tests

- Status: PASS
- JSON: `captures\current\hd-soak-short-tier-ladder-tests-current.json`
- Markdown: `captures\current\hd-soak-short-tier-ladder-tests-current.md`
- test_count: `5`
- guard_policy: `proves the short soak ladder is ordered, approval-gated, non-promoting, and keeps long/future lanes locked until prerequisite soak evidence exists`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Hd Soak Short Artifact Manifest

- Status: PASS
- JSON: `captures\current\hd-soak-short-artifact-manifest-current.json`
- Markdown: `captures\current\hd-soak-short-artifact-manifest-current.md`
- step_count: `5`
- existing_step_report_count: `0`
- legacy_report_exists: `True`
- long_tiers_locked: `True`
- future_lanes_locked: `True`
- right_bottom_promotion_blocked: `True`
- runtime_policy: `repo-only short-soak artifact manifest; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows`

### Hd Soak Short Artifact Manifest Tests

- Status: PASS
- JSON: `captures\current\hd-soak-short-artifact-manifest-tests-current.json`
- Markdown: `captures\current\hd-soak-short-artifact-manifest-tests-current.md`
- test_count: `5`
- guard_policy: `proves each short soak ladder step has durable current report, guard, and triage paths, with execution commands gated by -Execute -AllowVisibleRuntime`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Hd Soak Short Validation Refresh

- Status: PASS
- JSON: `captures\current\hd-soak-short-validation-refresh-current.json`
- Markdown: `captures\current\hd-soak-short-validation-refresh-current.md`
- status: `pending_no_reports`
- counts: `{'steps': 5, 'reports_found': 0, 'guards_written': 0, 'triage_written': 0, 'validated_failed': 0}`
- runtime_policy: `repo-only short-soak validation refresh; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows`

### Hd Soak Short Validation Refresh Tests

- Status: PASS
- JSON: `captures\current\hd-soak-short-validation-refresh-tests-current.json`
- Markdown: `captures\current\hd-soak-short-validation-refresh-tests-current.md`
- test_count: `6`
- guard_policy: `proves canonical short soak reports are automatically guarded and triaged before step-status evaluation, while missing reports remain a safe pending repo-only state`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Hd Soak Short Step Status

- Status: PASS
- JSON: `captures\current\hd-soak-short-step-status-current.json`
- Markdown: `captures\current\hd-soak-short-step-status-current.md`
- ladder_complete: `False`
- counts: `{'total': 5, 'passed': 0, 'pending_or_missing': 1, 'locked': 4, 'failed_or_invalid': 0}`
- current_step: `short2_menu_idle`
- current_step_status: `pending_approval_legacy_compat`
- long_tiers_locked: `True`
- future_lanes_locked: `True`
- right_bottom_promotion_blocked: `True`
- runtime_policy: `repo-only short-soak step status; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows`

### Hd Soak Short Step Status Tests

- Status: PASS
- JSON: `captures\current\hd-soak-short-step-status-tests-current.json`
- Markdown: `captures\current\hd-soak-short-step-status-tests-current.md`
- test_count: `5`
- guard_policy: `proves per-step soak status stays repo-only, advances only after guarded passing output, and demands triage for failed canonical runtime reports`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Hd Soak Approval Preflight

- Status: PASS
- JSON: `captures\current\hd-soak-approval-preflight-current.json`
- Markdown: `captures\current\hd-soak-approval-preflight-current.md`
- status: `ready_for_explicit_approval`
- current_step: `short2_menu_idle`
- current_step_status: `pending_approval_legacy_compat`
- writes_outside_repo: `['C:\\ClashCaptures\\hd-soak', 'C:\\ClashTests\\hd-soak']`
- stable_stage_should_change: `False`
- right_bottom_promotion_blocked: `True`
- runtime_policy: `repo-only visible-runtime approval preflight; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows`

### Hd Soak Approval Preflight Tests

- Status: PASS
- JSON: `captures\current\hd-soak-approval-preflight-tests-current.json`
- Markdown: `captures\current\hd-soak-approval-preflight-tests-current.md`
- test_count: `7`
- guard_policy: `proves the first short2 visible-runtime soak remains explicit-approval gated, pins canonical per-step report paths, keeps dry-runs non-executing, and requires clean harness/runtime/process/executable guards before requesting approval`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Capture Corpus Index

- Status: PASS
- JSON: `captures\current\capture-corpus-index-current.json`
- Markdown: `captures\current\capture-corpus-index-current.md`
- artifact_count: `660`
- current_reference_count: `160`
- stale_visible_or_sandbox_count: `16`
- reference_status_counts: `{'archived_referenced': 283, 'current_referenced': 130, 'stale_unreferenced': 247}`
- era_counts: `{'cdb_surface_dump_unverified': 55, 'hidden_cdb_surface_dump': 118, 'other_capture_artifact': 471, 'visible_era': 16}`
- guard_policy: `current evidence capture references must resolve and must not reactivate visible-era or sandbox/VM artifacts as active blockers`
- runtime_policy: `repo-only capture index; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Capture Corpus Index Tests

- Status: PASS
- JSON: `captures\current\capture-corpus-index-tests-current.json`
- Markdown: `captures\current\capture-corpus-index-tests-current.md`
- test_count: `9`
- guard_policy: `proves capture references resolve, synthetic fixture/transition placeholders stay non-current, and stale visible-era artifacts cannot become active evidence silently`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### No Popup Boundary Guard

- Status: FAIL
- JSON: `captures\current\no-popup-boundary-guard-current.json`
- Markdown: `captures\current\no-popup-boundary-guard-current.md`
- required_guard_count: `6`
- required_supporting_report_count: `82`
- required_report_count: `88`
- required_guards: `['stable_stage_guard', 'exe_artifact_guard', 'surface_dump_policy_guard', 'visible_runtime_launcher_guard', 'no_visible_runtime_guard', 'process_hygiene_guard']`
- required_supporting_reports: `['no_popup_map_evidence', 'no_popup_map_evidence_tests', 'no_visible_runtime_guard_tests', 'no_popup_guard_tests', 'visible_runtime_launcher_guard_tests', 'python_runtime_safety_guard', 'python_runtime_safety_guard_tests', 'patch_definition_guard', 'patch_definition_guard_tests', 'capture_corpus_index', 'capture_corpus_index_tests', 'current_completion_summary', 'current_completion_summary_tests', 'process_hygiene_guard_tests', 'manual_directinput_checklist', 'manual_directinput_checklist_tests', 'manual_directinput_proof_template', 'manual_directinput_proof_template_tests', 'manual_directinput_run_plan', 'manual_directinput_run_plan_tests', 'promotion_override_guard', 'promotion_override_guard_tests', 'promotion_override_manifest', 'promotion_override_manifest_tests', 'handoff_freshness_guard', 'handoff_freshness_guard_tests', 'right_bottom_compose_promotion_decision_tests', 'right_bottom_compose_evidence_matrix_tests', 'right_bottom_blocker_triage', 'right_bottom_blocker_triage_tests', 'right_bottom_visual_artifact_guard', 'right_bottom_visual_artifact_guard_tests', 'right_bottom_grid_hit', 'right_bottom_grid_hit_summary_tests', 'right_bottom_grid_hit_probe_guard', 'right_bottom_grid_hit_probe_guard_tests', 'right_bottom_natural_route_guard', 'right_bottom_natural_route_guard_tests', 'right_bottom_slot_fixture_plan', 'right_bottom_slot_fixture_plan_tests', 'right_bottom_slot_fixture_script_guard', 'right_bottom_slot_fixture_script_guard_tests', 'right_bottom_slot_fixture_runtime_plan', 'right_bottom_slot_fixture_runtime_plan_tests', 'right_bottom_slot_fixture_result_summary_tests', 'load_slot_route_limit_guard', 'load_slot_route_limit_guard_tests', 'load_slot_timeout_phase', 'load_slot_timeout_phase_tests', 'load_slot_entry_gap', 'load_slot_entry_gap_tests', 'load_slot_transition_probe_guard', 'load_slot_transition_probe_guard_tests', 'load_slot_transition_run_plan', 'load_slot_transition_run_plan_tests', 'load_slot_transition_geometry_guard', 'load_slot_transition_geometry_guard_tests', 'load_slot_transition_probe_preview', 'load_slot_transition_probe_preview_tests', 'load_slot_transition_readiness', 'load_slot_transition_readiness_tests', 'load_slot_transition_summary_tests', 'right_bottom_owner_flag_static_guard', 'right_bottom_owner_flag_static_guard_tests', 'right_bottom_owner_flag_inventory', 'right_bottom_owner_flag_inventory_tests', 'right_bottom_route_timing_guard', 'right_bottom_route_timing_guard_tests', 'castle_overview_baseline_recheck', 'castle_overview_baseline_recheck_tests', 'castle_owner_records_summary_tests', 'castle_overview_evidence_matrix_tests', 'castle_overview_gate_tests', 'castle_overview_hitbox_summary_tests', 'castle_overview_hitmap_summary_tests', 'castle_overview_multihit_summary_tests', 'castle_overview_promotion_decision_tests', 'castle_overview_probe_guard', 'castle_overview_probe_guard_tests', 'stable_stage_guard_tests', 'docs_consistency_guard', 'docs_consistency_guard_tests']`
- required_reports: `['stable_stage_guard', 'exe_artifact_guard', 'surface_dump_policy_guard', 'visible_runtime_launcher_guard', 'no_visible_runtime_guard', 'process_hygiene_guard', 'no_popup_map_evidence', 'no_popup_map_evidence_tests', 'no_visible_runtime_guard_tests', 'no_popup_guard_tests', 'visible_runtime_launcher_guard_tests', 'python_runtime_safety_guard', 'python_runtime_safety_guard_tests', 'patch_definition_guard', 'patch_definition_guard_tests', 'capture_corpus_index', 'capture_corpus_index_tests', 'current_completion_summary', 'current_completion_summary_tests', 'process_hygiene_guard_tests', 'manual_directinput_checklist', 'manual_directinput_checklist_tests', 'manual_directinput_proof_template', 'manual_directinput_proof_template_tests', 'manual_directinput_run_plan', 'manual_directinput_run_plan_tests', 'promotion_override_guard', 'promotion_override_guard_tests', 'promotion_override_manifest', 'promotion_override_manifest_tests', 'handoff_freshness_guard', 'handoff_freshness_guard_tests', 'right_bottom_compose_promotion_decision_tests', 'right_bottom_compose_evidence_matrix_tests', 'right_bottom_blocker_triage', 'right_bottom_blocker_triage_tests', 'right_bottom_visual_artifact_guard', 'right_bottom_visual_artifact_guard_tests', 'right_bottom_grid_hit', 'right_bottom_grid_hit_summary_tests', 'right_bottom_grid_hit_probe_guard', 'right_bottom_grid_hit_probe_guard_tests', 'right_bottom_natural_route_guard', 'right_bottom_natural_route_guard_tests', 'right_bottom_slot_fixture_plan', 'right_bottom_slot_fixture_plan_tests', 'right_bottom_slot_fixture_script_guard', 'right_bottom_slot_fixture_script_guard_tests', 'right_bottom_slot_fixture_runtime_plan', 'right_bottom_slot_fixture_runtime_plan_tests', 'right_bottom_slot_fixture_result_summary_tests', 'load_slot_route_limit_guard', 'load_slot_route_limit_guard_tests', 'load_slot_timeout_phase', 'load_slot_timeout_phase_tests', 'load_slot_entry_gap', 'load_slot_entry_gap_tests', 'load_slot_transition_probe_guard', 'load_slot_transition_probe_guard_tests', 'load_slot_transition_run_plan', 'load_slot_transition_run_plan_tests', 'load_slot_transition_geometry_guard', 'load_slot_transition_geometry_guard_tests', 'load_slot_transition_probe_preview', 'load_slot_transition_probe_preview_tests', 'load_slot_transition_readiness', 'load_slot_transition_readiness_tests', 'load_slot_transition_summary_tests', 'right_bottom_owner_flag_static_guard', 'right_bottom_owner_flag_static_guard_tests', 'right_bottom_owner_flag_inventory', 'right_bottom_owner_flag_inventory_tests', 'right_bottom_route_timing_guard', 'right_bottom_route_timing_guard_tests', 'castle_overview_baseline_recheck', 'castle_overview_baseline_recheck_tests', 'castle_owner_records_summary_tests', 'castle_overview_evidence_matrix_tests', 'castle_overview_gate_tests', 'castle_overview_hitbox_summary_tests', 'castle_overview_hitmap_summary_tests', 'castle_overview_multihit_summary_tests', 'castle_overview_promotion_decision_tests', 'castle_overview_probe_guard', 'castle_overview_probe_guard_tests', 'stable_stage_guard_tests', 'docs_consistency_guard', 'docs_consistency_guard_tests']`
- evidence_index: `captures\current\hd-map-evidence-current.md`
- guard_policy: `current refresh must include all no-popup boundary reports and the evidence index must link each report`
- Failures:
  - stable_stage_guard: refresh check is not passing: stable_stage_guard
  - right_bottom_visual_artifact_guard: refresh check is not passing: right_bottom_visual_artifact_guard
  - load_slot_entry_gap: refresh check is not passing: load_slot_entry_gap
  - load_slot_transition_run_plan: refresh check is not passing: load_slot_transition_run_plan
  - load_slot_transition_geometry_guard: refresh check is not passing: load_slot_transition_geometry_guard
  - load_slot_transition_probe_preview: refresh check is not passing: load_slot_transition_probe_preview
  - load_slot_transition_readiness: refresh check is not passing: load_slot_transition_readiness
  - castle_overview_baseline_recheck: refresh check is not passing: castle_overview_baseline_recheck
  - docs_consistency_guard: refresh check is not passing: docs_consistency_guard

### Docs Consistency Guard

- Status: FAIL
- JSON: `captures\current\docs-consistency-current.json`
- Markdown: `captures\current\docs-consistency-current.md`
- check_count: `12`
- guard_policy: `generated current-evidence facts must agree with .codex-loop handoff docs, README/progress notes, the evidence index, and wiki summaries`
- runtime_policy: `repo-only docs/source inspection; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows`
- Failures:
  - boundary_counts: no-popup boundary guard is not passing
  - validation_only_status: castle validation matrix/decision is not passing
  - screenshot_files: normal_post_owner: missing path
  - screenshot_files: forced_visible_post_owner: missing path
  - docs_current_screenshot_paths: evidence index missing current screenshot path normal_post_owner: None
  - docs_current_screenshot_paths: evidence index missing current screenshot path forced_visible_post_owner: None

### Docs Consistency Guard Tests

- Status: PASS
- JSON: `captures\current\docs-consistency-tests-current.json`
- Markdown: `captures\current\docs-consistency-tests-current.md`
- test_count: `4`
- guard_policy: `proves current docs fail closed when generated counts or promotion-boundary facts go stale`
- runtime_policy: `repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows`

### Evidence Index Check

- Status: PASS
- JSON: `captures\current\hd-map-evidence-current-check.json`
- Index: `captures\current\hd-map-evidence-current.md`
- links: `143`
- images: `9`
- local_records: `152`
- missing: `0`
- image_missing: `0`
- image_wrong_extension: `0`

## Failures

- hd_map_smoke: patch-stage: no candidate executable path was found
- hd_map_smoke: post-owner evidence matrix failed
- right_bottom_compose_ui_probe: right-bottom compose UI did not naturally enter owner/action draw rows
- load_slot_entry_gap: cdb_probe: missing marker pre_entry_load_coord_placeholder: __PRE_ENTRY_LOAD_COORD_ACTION__
- load_slot_transition_run_plan: load-slot entry gap report is not passing
- load_slot_transition_geometry_guard: transition geometry guard failed: run_plan_passed
- load_slot_transition_probe_preview: transition probe preview failed: run_plan_passed
- load_slot_transition_probe_preview: transition probe preview failed: geometry_guard_passed
- right_bottom_compose_promotion_decision: right_bottom_compose_ui_probe: right-bottom compose UI did not naturally enter owner/action draw rows
- right_bottom_compose_promotion_decision: right-bottom natural UI probe did not enter owner/action draw rows
- right_bottom_compose_evidence: right_bottom_compose_ui_probe: right-bottom compose UI did not naturally enter owner/action draw rows
- right_bottom_compose_evidence: right_bottom_compose_promotion_decision: right_bottom_compose_ui_probe: right-bottom compose UI did not naturally enter owner/action draw rows
- right_bottom_compose_evidence: right_bottom_compose_promotion_decision: right-bottom natural UI probe did not enter owner/action draw rows
- right_bottom_compose_evidence: natural UI probe did not enter owner/action draw rows
- right_bottom_visual_artifact_guard: visual artifact guard failed: blocker_triage_non_promoting
- load_slot_transition_readiness: transition readiness check failed: entry_gap_passed
- load_slot_transition_readiness: transition readiness check failed: run_plan_passed
- load_slot_transition_readiness: transition readiness check failed: geometry_guard_passed
- load_slot_transition_readiness: transition readiness check failed: probe_preview_passed
- castle_overview_evidence: patch_stage: candidate executable does not exist: C:\ClashTests\cdb-castle-overview-nativerender-flags1f-multihit\clash95_hd_surfdump_20260515_105557.exe
- castle_overview_promotion_decision: castle overview evidence matrix is not passing
- castle_overview_baseline_recheck: latest_castle_overview_matrix: patch_stage: candidate executable does not exist: C:\ClashTests\cdb-castle-overview-nativerender-flags1f-multihit\clash95_hd_surfdump_20260515_105557.exe
- battle_ui_evidence_matrix: stable_smoke: stable HD-map smoke did not pass
- stable_stage_guard: castle_overview_promotion_decision: castle overview promotion decision is not passing
- stable_stage_guard: castle_overview_evidence_matrix: castle overview evidence matrix is not passing
- hd_soak_report_guard: soak report was not produced by an execution run
- hd_soak_report_guard: candidate_sha256 is missing or is not a SHA-256 hex digest
- hd_soak_report_guard: patch_stage_report path is missing
- hd_soak_report_guard: frame sample count 0 is below 2
- hd_soak_report_guard: minimum nonblack percent 0.0 is below 10.0
- hd_soak_report_guard: minimum unique sampled colors 0.0 is below 8
- hd_soak_report_guard: process was not stopped cleanly by the harness
- hd_soak_failure_triage: short2 menu-idle soak was not executed because visible-runtime escalation was not approved
- hd_endurance_release_checklist: short2_menu_idle_soak: short2 visible-runtime soak has not produced passing frame/process evidence
- hd_endurance_release_checklist: long_soak_representative_routes: no 2h+ representative-route soak report is present
- hd_endurance_release_checklist: stable_menu_real_input: menu-load proof remains pending manual DirectInput validation
- hd_endurance_release_checklist: stable_hd_map_real_input: HD map input proof remains pending manual DirectInput validation
- hd_endurance_release_checklist: right_bottom_action_menu: right-bottom action/menu remains validation-only or manual-proof blocked
- hd_endurance_release_checklist: castle_and_barracks_centered_input: castle/barracks centered input remains validation-only or manual-proof blocked
- hd_endurance_release_checklist: tactical_battle_entry_return: battle evidence remains validation-only or missing visible click-to-callback proof
- hd_endurance_release_checklist: save_load_roundtrip: save/load continuity proof is absent
- hd_endurance_release_checklist: turn_advancement: turn-advancement proof is absent
- hd_endurance_release_checklist: campaign_routes: campaign-route proof is absent
- no_popup_boundary_guard: stable_stage_guard: refresh check is not passing: stable_stage_guard
- no_popup_boundary_guard: right_bottom_visual_artifact_guard: refresh check is not passing: right_bottom_visual_artifact_guard
- no_popup_boundary_guard: load_slot_entry_gap: refresh check is not passing: load_slot_entry_gap
- no_popup_boundary_guard: load_slot_transition_run_plan: refresh check is not passing: load_slot_transition_run_plan
- no_popup_boundary_guard: load_slot_transition_geometry_guard: refresh check is not passing: load_slot_transition_geometry_guard
- no_popup_boundary_guard: load_slot_transition_probe_preview: refresh check is not passing: load_slot_transition_probe_preview
- no_popup_boundary_guard: load_slot_transition_readiness: refresh check is not passing: load_slot_transition_readiness
- no_popup_boundary_guard: castle_overview_baseline_recheck: refresh check is not passing: castle_overview_baseline_recheck
- no_popup_boundary_guard: docs_consistency_guard: refresh check is not passing: docs_consistency_guard
- docs_consistency_guard: boundary_counts: no-popup boundary guard is not passing
- docs_consistency_guard: validation_only_status: castle validation matrix/decision is not passing
- docs_consistency_guard: screenshot_files: normal_post_owner: missing path
- docs_consistency_guard: screenshot_files: forced_visible_post_owner: missing path
- docs_consistency_guard: docs_current_screenshot_paths: evidence index missing current screenshot path normal_post_owner: None
- docs_consistency_guard: docs_current_screenshot_paths: evidence index missing current screenshot path forced_visible_post_owner: None
