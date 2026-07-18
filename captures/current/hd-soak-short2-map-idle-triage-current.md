# HD Soak Failure Triage

- Overall: FAIL
- Generated: `2026-07-18T08:18:22.367847+00:00`
- Runtime policy: repo-only soak failure triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Source report: `captures\current\hd-soak-short2-map-idle-current.json`
- Source selection: `None`
- Canonical first-step report: `None`
- Canonical first-step present: `None`
- Legacy report: `None`
- Canonical runtime report missing: `None`
- Classification: `intro_skip_input_drift_exit`
- Next probe: previous intro-skip postmessage repeats crossed a window/intro transition; make the harness stop or reacquire after the transition, retain explicit windowed-mode verification, then rerun only after fresh visible-window approval
- Tier / route: `short2` / `map-idle`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Output directory: `C:\ClashCaptures\hd-soak\hd-soak-20260717-152525-short2-map-idle`
- Final route marker: `intro-skip`

## Failure Context

- Failure timestamp: `2026-07-17T15:25:41.2959501+02:00` source=`last_process_sample`
- Crash/hang class: `intro_skip_input_drift_exit`
- Last route marker: `intro-skip`
- Next probe: previous intro-skip postmessage repeats crossed a window/intro transition; make the harness stop or reacquire after the transition, retain explicit windowed-mode verification, then rerun only after fresh visible-window approval

## Visual Anomalies

- Overall: `PASS`
- Black/blank patch risk frames: `0`
- Palette/stripe risk frames: `0`
- Missing nonblack bounds frames: `0`

## Probe Environment

- Checked route logs: `1`
- Readable route logs: `1`
- Input-API permission-denied routes: `0`
- Affected routes: ``

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

- Last route: `intro-skip` path=`False` click=`False` drift=`None` sample_drift=`None` click_mode=`postmessage` repeat=`8`
- Last frame: `None` size=`NonexNone` nonblack=`None` luma=`None` colors=`None`
- Last process: exited=`True` exit_code=`1` working_set=`None` handles=`None`

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
- `input_max_abs_error`: `None`
- `input_max_sample_abs_error`: `None`
- `max_input_drift_px`: `1`
- `process_sample_count`: `2`
- `working_set_growth_bytes`: `None`
- `private_memory_growth_bytes`: `None`
- `handle_growth`: `None`
- `artifact_bytes`: `56508`
- `guard_validation_evaluated`: `False`
- `guard_validation_overall`: `None`
- `guard_validation_failure_count`: `0`

## Source Failures

- process exited unexpectedly with code 1
- expected at least 2 frame samples
- nonblack percent dropped below 10
- unique sampled colors dropped below 8
- route/input probe failures: 1
- input drift exceeded 1px or metric missing: 1
- intro skip rounds never verified the main menu on screen
- no launch attempt produced an interactive menu (engine cursor never responded to pulse input)
- route did not reach the gameplay map
- working-set growth metric unavailable
- private-memory growth metric unavailable
- handle growth metric unavailable
