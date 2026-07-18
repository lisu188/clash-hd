# Launcher Policy Guard

- Overall: PASS
- Generated: `2026-07-18T22:14:34+02:00`
- Runtime policy: repo-only source inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: launcher visible launches must stay user-initiated (confirmed=True from the GUI Play button or the CLI double flag) and the launcher must never join the evidence refresh
- Launcher dir: `src\launcher`
- Scripts dir: `scripts\launcher`
- Doc: `docs\hd\LAUNCHER.md`

## Checks

- `core_source_present`: `PASS`
- `core_confirmed_gate`: `PASS`
- `core_write_refusal`: `PASS`
- `core_refresh_isolation_policy`: `PASS`
- `launch_call_sites`: `PASS`
- `refresh_isolation`: `PASS`
- `launcher_scripts_no_risky_calls`: `PASS`
- `doc_policy`: `PASS`
