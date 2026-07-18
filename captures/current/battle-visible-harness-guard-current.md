# Battle Visible Harness Guard

- Overall: PASS
- Generated: `2026-07-18T21:30:35+02:00`
- Runtime policy: repo-only source inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Script: `scripts\cdb\run_cdb_battle_visible_input_probe.ps1`
- Wait-LogPattern lines: `[107]`

## Checks

- `visible runtime guard`: `PASS`
- `raw screen input mode`: `PASS`
- `wait log function`: `PASS`
- `fatal CDB pattern: Unable to insert breakpoint`: `PASS`
- `fatal CDB pattern: Unable to remove breakpoint`: `PASS`
- `fatal CDB pattern: Break instruction exception - code 80000003`: `PASS`
- `post-g break exception gate`: `PASS`
- `incremental log scan`: `PASS`
- `fatal wait failure throws`: `PASS`
