# Right-Bottom Slot Fixture Script Guard

- Status: PASS
- Generated: `2026-06-15T22:14:10+02:00`
- Runtime policy: repo-only source inspection; does not run PowerShell, copy saves, launch Clash95, CDB, wrappers, or visible windows
- Guard policy: the fixture preparation script must default to dry-run, copy only after -Execute, optionally seed a non-save isolated workdir, refuse repository and live C:\Clash\save outputs, and avoid visible-runtime APIs
- Script: `scripts\smoke\prepare_right_bottom_slot_fixture.ps1`
- Dry-run exit line: `122`
- Seed copy line: `144`
- Copy line: `149`
- Risky visible/runtime lines: `[]`

## Markers

- `default_source_slot5`: `PASS`
- `default_source_workdir`: `PASS`
- `default_fixture_root`: `PASS`
- `target_load_slot_zero`: `PASS`
- `seed_workdir_switch`: `PASS`
- `execute_switch`: `PASS`
- `repo_escape_switch`: `PASS`
- `repo_guard`: `PASS`
- `live_save_guard`: `PASS`
- `source_workdir_guard`: `PASS`
- `source_overwrite_guard`: `PASS`
- `non_promoting_proof_class`: `PASS`
- `promotion_ready_false`: `PASS`
- `stable_stage_false`: `PASS`
- `seed_excludes_save_dir`: `PASS`
- `seed_workdir_copy`: `PASS`
- `copy_item_literal`: `PASS`
