# Docs Consistency Guard

- Overall: FAIL
- Generated: `2026-07-12T16:09:27+02:00`
- Runtime policy: repo-only docs/source inspection; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Stable stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Manual target IDs: `['stable_menu_load', 'stable_hd_map_input', 'right_bottom_validation_input', 'castle_barracks_centered_input', 'castle_overview_centered_input']`
- No-popup preference: `Do not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows unless the user explicitly approves.`
- No-popup boundary counts: `required_guard_count=6`, `required_supporting_report_count=86`, `required_report_count=92`
- Right-bottom status: `validation_stage_only`
- Castle status: `validation_stage_only`

## Checks

- `manual_target_ids`: `PASS`
- `stable_stage`: `PASS`
- `runtime_boundary`: `PASS`
- `boundary_counts`: `FAIL`
  - no-popup boundary guard is not passing
- `map_boundary_counts`: `PASS`
- `validation_only_status`: `PASS`
- `screenshot_files`: `PASS`
- `docs_codex_loop`: `FAIL`
  - codex_loop does not keep castlecenter-all validation-only
  - codex_loop does not document stable_stage_should_change=False
  - codex_loop does not document no-popup boundary PASS status
- `docs_readme_progress`: `PASS`
- `docs_evidence_index`: `PASS`
- `docs_wiki_summaries`: `PASS`
- `docs_current_screenshot_paths`: `FAIL`
  - evidence index missing current screenshot path normal_post_owner: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260506-190037\surface.png
  - evidence index missing current screenshot path forced_visible_post_owner: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260506-201114\surface.png
  - evidence index missing current screenshot path right_bottom_owner_route: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-160131\surface.png
  - evidence index missing current screenshot path right_bottom_compose_probe: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-144922\surface.png
  - evidence index missing current screenshot path right_bottom_compose_patch: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-160204\surface.png
  - evidence index missing current screenshot path right_bottom_compose_fullstart_route: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-160351\surface.png
  - evidence index missing current screenshot path right_bottom_compose_normal_gate: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260513-121513\surface.png
  - evidence index missing current screenshot path right_bottom_compose_ui_probe: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-160441\surface.png
  - evidence index missing current screenshot path right_bottom_grid_hit: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-150240\surface.png

## Current Screenshot Paths

- `normal_post_owner`: `C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260506-190037\surface.png`
- `forced_visible_post_owner`: `C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260506-201114\surface.png`
- `right_bottom_owner_route`: `C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-160131\surface.png`
- `right_bottom_compose_probe`: `C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-144922\surface.png`
- `right_bottom_compose_patch`: `C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-160204\surface.png`
- `right_bottom_compose_fullstart_route`: `C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-160351\surface.png`
- `right_bottom_compose_normal_gate`: `C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260513-121513\surface.png`
- `right_bottom_compose_ui_probe`: `C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-160441\surface.png`
- `right_bottom_grid_hit`: `C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-150240\surface.png`

## Failures

- boundary_counts: no-popup boundary guard is not passing
- docs_codex_loop: codex_loop does not keep castlecenter-all validation-only
- docs_codex_loop: codex_loop does not document stable_stage_should_change=False
- docs_codex_loop: codex_loop does not document no-popup boundary PASS status
- docs_current_screenshot_paths: evidence index missing current screenshot path normal_post_owner: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260506-190037\surface.png
- docs_current_screenshot_paths: evidence index missing current screenshot path forced_visible_post_owner: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260506-201114\surface.png
- docs_current_screenshot_paths: evidence index missing current screenshot path right_bottom_owner_route: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-160131\surface.png
- docs_current_screenshot_paths: evidence index missing current screenshot path right_bottom_compose_probe: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-144922\surface.png
- docs_current_screenshot_paths: evidence index missing current screenshot path right_bottom_compose_patch: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-160204\surface.png
- docs_current_screenshot_paths: evidence index missing current screenshot path right_bottom_compose_fullstart_route: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-160351\surface.png
- docs_current_screenshot_paths: evidence index missing current screenshot path right_bottom_compose_normal_gate: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260513-121513\surface.png
- docs_current_screenshot_paths: evidence index missing current screenshot path right_bottom_compose_ui_probe: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-160441\surface.png
- docs_current_screenshot_paths: evidence index missing current screenshot path right_bottom_grid_hit: C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260712-150240\surface.png
