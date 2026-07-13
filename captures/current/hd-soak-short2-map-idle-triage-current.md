# HD Soak Failure Triage

- Overall: PASS
- Generated: `2026-07-12T19:33:11.821796+00:00`
- Runtime policy: repo-only soak failure triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Source report: `captures\current\hd-soak-short2-map-idle-current.json`
- Source selection: `None`
- Canonical first-step report: `None`
- Canonical first-step present: `None`
- Legacy report: `None`
- Canonical runtime report missing: `None`
- Classification: `passing_run_no_failure`
- Next probe: repeat short2 or move to short10 only after preserving the report and validation guard output
- Tier / route: `short2` / `map-idle`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Output directory: `C:\ClashCaptures\hd-soak\hd-soak-20260712-212826-short2-map-idle`
- Final route marker: `confirm-load`

## Failure Context

- Failure timestamp: `2026-07-12T21:30:48.0945291+02:00` source=`last_process_sample`
- Crash/hang class: `passing_run_no_failure`
- Last route marker: `confirm-load`
- Next probe: repeat short2 or move to short10 only after preserving the report and validation guard output

## Visual Anomalies

- Overall: `PASS`
- Black/blank patch risk frames: `0`
- Palette/stripe risk frames: `0`
- Missing nonblack bounds frames: `0`

## Last Evidence

- Last route: `confirm-load` path=`True` click=`True` drift=`0` sample_drift=`0` click_mode=`sendinput` repeat=`1`
- Last frame: `frame-0007` size=`800x600` nonblack=`58.403` luma=`48.853` colors=`157`
- Last process: exited=`False` exit_code=`None` working_set=`43536384` handles=`641`

## Metrics

- `frame_sample_count`: `8`
- `frame_hash_unique_count`: `1`
- `frame_progress_expected`: `False`
- `frame_stability_class`: `stable_idle`
- `nonblack_percent_min`: `58.403`
- `nonblack_percent_max`: `58.403`
- `mean_luma_min`: `48.853`
- `mean_luma_max`: `48.853`
- `unique_sample_colors_min`: `157`
- `unique_sample_colors_max`: `157`
- `input_max_abs_error`: `0`
- `input_max_sample_abs_error`: `0`
- `max_input_drift_px`: `1`
- `process_sample_count`: `9`
- `working_set_growth_bytes`: `-135168`
- `private_memory_growth_bytes`: `-479232`
- `handle_growth`: `-4`
- `artifact_bytes`: `1524416`
- `guard_validation_evaluated`: `True`
- `guard_validation_overall`: `True`
- `guard_validation_failure_count`: `0`
