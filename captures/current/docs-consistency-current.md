# Docs Consistency Guard

- Overall: FAIL
- Generated: `2026-06-15T20:47:23+02:00`
- Runtime policy: repo-only docs/source inspection; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Stable stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Manual target IDs: `['stable_menu_load', 'stable_hd_map_input', 'right_bottom_validation_input', 'castle_barracks_centered_input', 'castle_overview_centered_input']`
- No-popup preference: `Do not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows unless the user explicitly approves.`
- No-popup boundary counts: `required_guard_count=6`, `required_supporting_report_count=82`, `required_report_count=88`
- Right-bottom status: `validation_stage_only`
- Castle status: `validation_stage_only`

## Checks

- `manual_target_ids`: `PASS`
- `stable_stage`: `PASS`
- `runtime_boundary`: `PASS`
- `boundary_counts`: `FAIL`
  - no-popup boundary guard is not passing
- `map_boundary_counts`: `PASS`
- `validation_only_status`: `FAIL`
  - castle validation matrix/decision is not passing
- `screenshot_files`: `FAIL`
  - normal_post_owner: missing path
  - forced_visible_post_owner: missing path
- `docs_codex_loop`: `PASS`
- `docs_readme_progress`: `PASS`
- `docs_evidence_index`: `PASS`
- `docs_wiki_summaries`: `PASS`
- `docs_current_screenshot_paths`: `FAIL`
  - evidence index missing current screenshot path normal_post_owner: None
  - evidence index missing current screenshot path forced_visible_post_owner: None

## Current Screenshot Paths

- `normal_post_owner`: `None`
- `forced_visible_post_owner`: `None`
- `right_bottom_owner_route`: `C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\archive\cdb-surface-dump-20260513-112339\surface.png`
- `right_bottom_compose_probe`: `C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\archive\cdb-surface-dump-20260513-115303\surface.png`
- `right_bottom_compose_patch`: `C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\archive\cdb-surface-dump-20260513-120712\surface.png`
- `right_bottom_compose_fullstart_route`: `C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\archive\cdb-surface-dump-20260513-122928\surface.png`
- `right_bottom_compose_normal_gate`: `C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\archive\cdb-surface-dump-20260513-121513\surface.png`
- `right_bottom_compose_ui_probe`: `C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\archive\cdb-surface-dump-20260513-122200\surface.png`
- `right_bottom_grid_hit`: `C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\archive\cdb-surface-dump-20260514-140601\surface.png`

## Failures

- boundary_counts: no-popup boundary guard is not passing
- validation_only_status: castle validation matrix/decision is not passing
- screenshot_files: normal_post_owner: missing path
- screenshot_files: forced_visible_post_owner: missing path
- docs_current_screenshot_paths: evidence index missing current screenshot path normal_post_owner: None
- docs_current_screenshot_paths: evidence index missing current screenshot path forced_visible_post_owner: None
