# Surface Dump Policy Guard

- Overall: PASS
- Generated: `2026-07-12T19:23:19+02:00`
- Runtime policy: repo-only source inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: surface-dump harness must default to hidden desktop and require -AllowVisibleDesktop for active-desktop fallback
- Script: `scripts\cdb\run_cdb_surface_dump.ps1`

## Checks

- `allow_visible_desktop_is_switch`: `PASS`
- `default_launch_mode_hidden`: `PASS`
- `createdesktop_failure_refuses_visible_fallback`: `PASS`
- `visible_branch_requires_explicit_switch`: `PASS`
- `hidden_branch_uses_createdesktop`: `PASS`
- `summary_records_hidden_desktop`: `PASS`
- `summary_records_allow_visible_desktop`: `PASS`
