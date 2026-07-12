# HD Soak Failure Triage

- Overall: FAIL
- Generated: `2026-07-12T17:43:38.111115+00:00`
- Runtime policy: repo-only soak failure triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Source report: `captures\current\hd-soak-short2-menu-idle-current.json`
- Source selection: `None`
- Canonical first-step report: `None`
- Canonical first-step present: `None`
- Legacy report: `None`
- Canonical runtime report missing: `None`
- Classification: `intro_skip_input_drift_exit`
- Next probe: previous intro-skip click used sendinput and drifted after button events; rerun only with the current tokenized postmessage/space-pulse intro-skip command after explicit visible-window approval
- Tier / route: `short2` / `menu-idle`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Output directory: `C:\ClashCaptures\hd-soak\hd-soak-20260616-172005-short2-menu-idle`
- Final route marker: `intro-skip`

## Failure Context

- Failure timestamp: `2026-06-16T17:20:30.2497486+02:00` source=`last_process_sample`
- Crash/hang class: `intro_skip_input_drift_exit`
- Last route marker: `intro-skip`
- Next probe: previous intro-skip click used sendinput and drifted after button events; rerun only with the current tokenized postmessage/space-pulse intro-skip command after explicit visible-window approval

## Visual Anomalies

- Overall: `FAIL`
- Black/blank patch risk frames: `1`
- Palette/stripe risk frames: `0`
- Missing nonblack bounds frames: `0`

## Last Evidence

- Last route: `intro-skip` path=`True` click=`False` drift=`0` sample_drift=`324` click_mode=`sendinput` repeat=`1`
- Last frame: `frame-0000` size=`800x600` nonblack=`9.697` luma=`3.126` colors=`249`
- Last process: exited=`True` exit_code=`1` working_set=`None` handles=`None`

## Metrics

- `frame_sample_count`: `1`
- `frame_hash_unique_count`: `1`
- `frame_progress_expected`: `False`
- `frame_stability_class`: `stable_idle`
- `nonblack_percent_min`: `9.697`
- `nonblack_percent_max`: `9.697`
- `mean_luma_min`: `3.126`
- `mean_luma_max`: `3.126`
- `unique_sample_colors_min`: `249`
- `unique_sample_colors_max`: `249`
- `visual_anomaly`: `frame-0000` flags=`black_or_blank_patch_risk` nonblack=`9.697` colors=`249`
- `input_max_abs_error`: `0`
- `input_max_sample_abs_error`: `324`
- `max_input_drift_px`: `1`
- `process_sample_count`: `3`
- `working_set_growth_bytes`: `None`
- `private_memory_growth_bytes`: `None`
- `handle_growth`: `None`
- `artifact_bytes`: `124455`
- `guard_validation_evaluated`: `False`
- `guard_validation_overall`: `None`
- `guard_validation_failure_count`: `0`

## Source Failures

- process exited unexpectedly with code 1
- expected at least 2 frame samples
- nonblack percent dropped below 10
- route/input probe failures: 1
- input drift exceeded 1px or metric missing: 1
- working-set growth metric unavailable
- private-memory growth metric unavailable
- handle growth metric unavailable
