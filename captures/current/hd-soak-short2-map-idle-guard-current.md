# HD Soak Report Guard

- Overall: FAIL
- Generated: `2026-07-18T08:58:23.237081+00:00`
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
- `capture_integrity`: `PASS`
- `frame_inventory`: `PASS`
- `render_metrics`: `PASS`
- `capture_consistency`: `FAIL`
- `visual_anomalies`: `PASS`
- `frame_progression`: `PASS`
- `process_liveness`: `PASS`
- `process_growth`: `PASS`
- `elapsed_coverage`: `PASS`
- `input_responsiveness`: `PASS`
- `route_completion_marker`: `PASS`
- `route_screen_outcome`: `FAIL`
- `summary_consistency`: `FAIL`
- `artifact_budget`: `PASS`

## Failures

- source soak report did not mark itself passed
- source soak report contains 4 failure(s)
- capture mode changed mid-run; observed screen=1, windowdc-contaminated-fallback=7; frames from different capture paths are not comparable render evidence
- map route did not verify the gameplay map on screen (map_route_reached is not true)
- nonblack_percent_min summary 0.017 does not match detailed rows 60.487
- unique_sample_colors_min summary 6 does not match detailed rows 157
- mean_luma_min summary 0.035 does not match detailed rows 49.409
