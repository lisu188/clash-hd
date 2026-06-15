# HD Soak Report Guard

- Overall: FAIL
- Generated: `2026-06-15T18:47:22.596946+00:00`
- Runtime policy: `repo-only soak report inspection; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Tier / route: `short2` / `menu-idle`
- Duration seconds: `120`

## Checks

- `executed`: `FAIL`
- `protected_stage`: `PASS`
- `promotion_boundary`: `PASS`
- `artifact_locations`: `PASS`
- `frame_inventory`: `FAIL`
- `render_metrics`: `FAIL`
- `process_liveness`: `FAIL`
- `input_responsiveness`: `PASS`
- `artifact_budget`: `PASS`

## Failures

- soak report was not produced by an execution run
- frame sample count 0 is below 2
- minimum nonblack percent 0.0 is below 10.0
- minimum unique sampled colors 0.0 is below 8
- process was not stopped cleanly by the harness
