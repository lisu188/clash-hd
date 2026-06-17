# HD Soak Report Guard

- Overall: FAIL
- Generated: `2026-06-17T07:48:26.976457+00:00`
- Runtime policy: `repo-only soak report inspection; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows`
- Source report: `captures\current\hd-soak-short2-menu-idle-current.json`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Tier / route: `short2` / `menu-idle`
- Duration seconds: `120`
- Sample interval seconds: `15`

## Checks

- `executed`: `PASS`
- `source_status`: `FAIL`
- `protected_stage`: `PASS`
- `tier_route`: `PASS`
- `patch_evidence`: `PASS`
- `promotion_boundary`: `PASS`
- `artifact_locations`: `PASS`
- `capture_integrity`: `PASS`
- `frame_inventory`: `FAIL`
- `render_metrics`: `FAIL`
- `visual_anomalies`: `FAIL`
- `frame_progression`: `PASS`
- `process_liveness`: `FAIL`
- `process_growth`: `FAIL`
- `elapsed_coverage`: `FAIL`
- `input_responsiveness`: `FAIL`
- `route_completion_marker`: `PASS`
- `summary_consistency`: `PASS`
- `artifact_budget`: `FAIL`

## Failures

- source soak report did not mark itself passed
- source soak report contains 8 failure(s)
- frame sample count 1 is below 2
- minimum nonblack percent 9.697 is below 10.0
- 1 frame sample(s) show black/blank patch risk
- process exited unexpectedly with code 1
- process was not stopped cleanly by the harness
- 2 process samples reported HasExited=True
- working_set_growth_bytes is missing
- private_memory_growth_bytes is missing
- handle_growth is missing
- frame sample elapsed coverage could not be computed
- process sample elapsed coverage 16.606s is below required 103.000s
- 1 route/input rows did not verify
- 1 route/input rows exceeded drift limit, omitted drift metrics, or had bad probe exit codes
- max_artifact_mb is missing
- artifact_limit_bytes is missing
