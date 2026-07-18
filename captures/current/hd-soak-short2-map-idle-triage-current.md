# HD Soak Failure Triage

- Overall: FAIL
- Generated: `2026-07-18T19:36:44.846279+00:00`
- Runtime policy: repo-only soak failure triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Source report: `captures\current\hd-soak-short2-map-idle-current.json`
- Source selection: `None`
- Canonical first-step report: `None`
- Canonical first-step present: `None`
- Legacy report: `None`
- Canonical runtime report missing: `None`
- Classification: `window_missing_while_process_alive`
- Next probe: inspect window_health_samples and wrapper transitions at the first missing-window phase before requesting any visible rerun
- Tier / route: `short2` / `map-idle`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Output directory: `C:\ClashCaptures\hd-soak\hd-soak-20260718-210958-short2-map-idle`
- Final route marker: `confirm-load`

## Failure Context

- Failure timestamp: `2026-07-18T21:10:32.6147253+02:00` source=`last_process_sample`
- Crash/hang class: `window_missing_while_process_alive`
- Last route marker: `confirm-load`
- Next probe: inspect window_health_samples and wrapper transitions at the first missing-window phase before requesting any visible rerun

## Visual Anomalies

- Overall: `PASS`
- Black/blank patch risk frames: `0`
- Palette/stripe risk frames: `0`
- Missing nonblack bounds frames: `0`

## Probe Environment

- Checked route logs: `4`
- Readable route logs: `4`
- Input-API permission-denied routes: `0`
- Affected routes: ``
- Cursor probes checked: `1`
- Foreground-denied attempts: `0`
- Engine cursor responded at least once: `True`

## Hidden CDB Follow-up

- Matched: `True`
- Status: `cdb_exit_not_reproduced_hidden_memory_proxy`
- Summary: `C:\ClashCaptures\hd-soak-cdb-crash\cdb-surface-dump-20260715-070814\summary.json`
- Scope limit: The hidden memory-only DirectDraw proxy differs from the approved application/windowed wrapper plus visible input and capture path, so this pass does not clear or replace the visible unexpected-exit failure.

## Windows Error Reporting Follow-up

- Matched: `True`
- Status: `application_hang_confirmed_wer_closed`
- Event: `AppHangB1`
- Window-health mitigation ready: `True`
- Scope limit: WER proves an application hang and OS closure, but provides no readable archived stack under the current ACL and does not identify which route step or wrapper interaction first stopped responding.

## Last Evidence

- Last route: `confirm-load` path=`False` click=`False` drift=`None` sample_drift=`None` click_mode=`sendinput-hold-while-pulsing` repeat=`3`
- Last frame: `None` size=`NonexNone` nonblack=`None` luma=`None` colors=`None`
- Last process: exited=`False` exit_code=`None` working_set=`46260224` handles=`642`

## Metrics

- `frame_sample_count`: `0`
- `frame_hash_unique_count`: `0`
- `frame_progress_expected`: `False`
- `frame_stability_class`: `no_frames`
- `nonblack_percent_min`: `0`
- `nonblack_percent_max`: `0`
- `mean_luma_min`: `0`
- `mean_luma_max`: `0`
- `unique_sample_colors_min`: `0`
- `unique_sample_colors_max`: `0`
- `input_max_abs_error`: `0`
- `input_max_sample_abs_error`: `0`
- `max_input_drift_px`: `1`
- `process_sample_count`: `2`
- `working_set_growth_bytes`: `0`
- `private_memory_growth_bytes`: `0`
- `handle_growth`: `0`
- `artifact_bytes`: `499449`
- `guard_validation_evaluated`: `False`
- `guard_validation_overall`: `None`
- `guard_validation_failure_count`: `0`

## Source Failures

- visible application window disappeared while the process remained alive
- capture errors: 1
- expected at least 2 frame samples
- expected at least 2 render-evidence frame samples
- nonblack percent dropped below 10
- unique sampled colors dropped below 8
- route/input probe failures: 2
- input drift exceeded 1px or metric missing: 3
- route did not reach the gameplay map
