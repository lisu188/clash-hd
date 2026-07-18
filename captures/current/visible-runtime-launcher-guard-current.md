# Visible Runtime Launcher Guard

- Overall: PASS
- Generated: `2026-07-18T10:18:08+02:00`
- Runtime policy: repo-only source inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: legacy visible-runtime launchers/helpers must fail closed unless -AllowVisibleRuntime is explicitly supplied after user approval; guarded child helpers must receive the same switch; root PowerShell risky-call inventory must be guarded or explicitly exempt
- Scripts checked: `8`
- Passing scripts: `8`

## Scripts

- `scripts\smoke\run_clash_visual_smoke.ps1`: `PASS` guard_lines=`[65]` first_risky_line=`490` child_helper_lines=`[]`
- `scripts\smoke\run_hd_soak.ps1`: `PASS` guard_lines=`[934]` first_risky_line=`1048` child_helper_lines=`[]`
- `scripts\cdb\run_cdb_map_probe.ps1`: `PASS` guard_lines=`[32]` first_risky_line=`222` child_helper_lines=`[]`
- `scripts\cdb\run_cdb_python_mouse_map.ps1`: `PASS` guard_lines=`[26]` first_risky_line=`94` child_helper_lines=`[]`
- `scripts\cdb\run_cdb_viewport_bounds_probe.ps1`: `PASS` guard_lines=`[16]` first_risky_line=`109` child_helper_lines=`[]`
- `scripts\cdb\run_cdb_battle_visible_input_probe.ps1`: `PASS` guard_lines=`[45]` first_risky_line=`230` child_helper_lines=`[]`
- `scripts\smoke\run_clash_windows_sandbox.ps1`: `PASS` guard_lines=`[20]` first_risky_line=`224` child_helper_lines=`[]`
- `scripts\capture\capture_clash_client_frame.ps1`: `PASS` guard_lines=`[13]` first_risky_line=`230` child_helper_lines=`[]`

## Root PowerShell Risky-Call Inventory

- Root: `C:\Users\andrz\git\clash-hd`
- Risky scripts: `0`
- Guarded risky scripts: `0`
- Exempt risky scripts: `0`
- Unclassified risky scripts: `0`
