# HD Soak Report Guard

- Overall: FAIL
- Generated: `2026-07-18T19:36:44.842276+00:00`
- Runtime policy: `repo-only soak report inspection; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows`
- Source report: `captures\current\hd-soak-short2-map-idle-current.json`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Tier / route: `short2` / `map-idle`
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
- `capture_integrity`: `FAIL`
- `frame_inventory`: `FAIL`
- `render_metrics`: `FAIL`
- `capture_consistency`: `PASS`
- `visual_anomalies`: `PASS`
- `frame_progression`: `PASS`
- `process_liveness`: `PASS`
- `process_growth`: `PASS`
- `elapsed_coverage`: `FAIL`
- `input_responsiveness`: `FAIL`
- `route_completion_marker`: `PASS`
- `route_screen_outcome`: `FAIL`
- `summary_consistency`: `FAIL`
- `artifact_budget`: `PASS`

## Failures

- source soak report did not mark itself passed
- source soak report contains 9 failure(s)
- capture_errors contains 1 row(s)
- frame sample count 0 is below 2
- minimum nonblack percent 0.0 is below 10.0
- minimum unique sampled colors 0.0 is below 8
- frame sample elapsed coverage could not be computed
- process sample elapsed coverage 2.465s is below required 103.000s
- 2 route/input rows did not verify
- 3 route/input rows exceeded drift limit, omitted drift metrics, or had bad probe exit codes
- map route did not verify the gameplay map on screen (map_route_reached is not true)
- nonblack_percent_min summary 0.0 does not match detailed rows None
- nonblack_percent_max summary 0.0 does not match detailed rows None
- unique_sample_colors_min summary 0 does not match detailed rows None
- unique_sample_colors_max summary 0 does not match detailed rows None
- mean_luma_min summary 0.0 does not match detailed rows None
- mean_luma_max summary 0.0 does not match detailed rows None
