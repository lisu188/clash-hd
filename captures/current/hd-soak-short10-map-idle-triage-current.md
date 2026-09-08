# HD Soak Failure Triage

- Overall: PASS
- Generated: `2026-09-06T03:57:57.690642+00:00`
- Runtime policy: repo-only soak failure triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Source report: `captures\current\hd-soak-short10-map-idle-current.json`
- Source selection: `None`
- Canonical first-step report: `None`
- Canonical first-step present: `None`
- Legacy report: `None`
- Canonical runtime report missing: `None`
- Classification: `passing_run_no_failure`
- Next probe: preserve the hidden-CDB report and guard, then continue the next unlocked hidden map tier
- Tier / route: `short10` / `map-idle`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Output directory: `C:\ClashCaptures\hd-soak\hidden\hidden-soak-20260905-094801-748-map-idle`
- Final route marker: `None`

## Failure Context

- Failure timestamp: `2026-09-05T09:58:35.5656210+02:00` source=`last_process_sample`
- Crash/hang class: `passing_run_no_failure`
- Last route marker: `None`
- Next probe: preserve the hidden-CDB report and guard, then continue the next unlocked hidden map tier

## Visual Anomalies

- Overall: `FAIL`
- Black/blank patch risk frames: `None`
- Palette/stripe risk frames: `None`
- Missing nonblack bounds frames: `None`

## Probe Environment

- Checked route logs: `0`
- Readable route logs: `0`
- Input-API permission-denied routes: `0`
- Affected routes: ``
- Cursor probes checked: `0`
- Foreground-denied attempts: `0`
- Engine cursor responded at least once: `False`

## Last Evidence

- Last route: `None` path=`None` click=`None` drift=`None` sample_drift=`None` click_mode=`None` repeat=`None`
- Last frame: `frame-0041` size=`800x600` nonblack=`97.339` luma=`None` colors=`197`
- Last process: exited=`False` exit_code=`None` working_set=`37212160` handles=`607`

## Metrics

- `frame_sample_count`: `41`
- `frame_hash_unique_count`: `32`
- `frame_progress_expected`: `False`
- `frame_stability_class`: `progressing`
- `nonblack_percent_min`: `97.339`
- `nonblack_percent_max`: `97.34`
- `mean_luma_min`: `None`
- `mean_luma_max`: `None`
- `unique_sample_colors_min`: `166`
- `unique_sample_colors_max`: `198`
- `input_max_abs_error`: `None`
- `input_max_sample_abs_error`: `None`
- `max_input_drift_px`: `None`
- `process_sample_count`: `41`
- `working_set_growth_bytes`: `110592`
- `private_memory_growth_bytes`: `-102400`
- `handle_growth`: `-9`
- `artifact_bytes`: `4054990`
- `guard_validation_evaluated`: `True`
- `guard_validation_overall`: `True`
- `guard_validation_failure_count`: `0`
