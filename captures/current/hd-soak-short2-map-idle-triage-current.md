# HD Soak Failure Triage

- Overall: FAIL
- Generated: `2026-07-18T08:58:23.240080+00:00`
- Runtime policy: repo-only soak failure triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Source report: `captures\current\hd-soak-short2-map-idle-current.json`
- Source selection: `None`
- Canonical first-step report: `None`
- Canonical first-step present: `None`
- Legacy report: `None`
- Canonical runtime report missing: `None`
- Classification: `input_environment_permission_denied`
- Next probe: SetForegroundWindow was silently denied on every aim iteration, so the foreground-mode DirectInput never received the injected pulses; rerun the exact tokenized route command DIRECTLY from an interactive session with input standing (never via Start-Job or any detached/non-interactive wrapper), and do not change patches or lower visual thresholds
- Tier / route: `short2` / `map-idle`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Output directory: `C:\ClashCaptures\hd-soak\hd-soak-20260718-102547-short2-map-idle`
- Final route marker: `intro-skip`

## Failure Context

- Failure timestamp: `2026-07-18T10:28:08.1537210+02:00` source=`last_process_sample`
- Crash/hang class: `input_environment_permission_denied`
- Last route marker: `intro-skip`
- Next probe: SetForegroundWindow was silently denied on every aim iteration, so the foreground-mode DirectInput never received the injected pulses; rerun the exact tokenized route command DIRECTLY from an interactive session with input standing (never via Start-Job or any detached/non-interactive wrapper), and do not change patches or lower visual thresholds

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
- Cursor probes checked: `1`
- Foreground-denied attempts: `1`
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

- Last route: `intro-skip` path=`True` click=`False` drift=`0` sample_drift=`80` click_mode=`postmessage` repeat=`8`
- Last frame: `frame-0007` size=`800x600` nonblack=`0.017` luma=`0.035` colors=`6`
- Last process: exited=`False` exit_code=`None` working_set=`42201088` handles=`648`

## Metrics

- `frame_sample_count`: `8`
- `frame_hash_unique_count`: `2`
- `frame_progress_expected`: `False`
- `frame_stability_class`: `progressing`
- `nonblack_percent_min`: `0.017`
- `nonblack_percent_max`: `60.487`
- `mean_luma_min`: `0.035`
- `mean_luma_max`: `49.409`
- `unique_sample_colors_min`: `6`
- `unique_sample_colors_max`: `157`
- `input_max_abs_error`: `0`
- `input_max_sample_abs_error`: `80`
- `max_input_drift_px`: `1`
- `process_sample_count`: `9`
- `working_set_growth_bytes`: `876544`
- `private_memory_growth_bytes`: `704512`
- `handle_growth`: `6`
- `artifact_bytes`: `1657609`
- `guard_validation_evaluated`: `False`
- `guard_validation_overall`: `None`
- `guard_validation_failure_count`: `0`

## Source Failures

- nonblack percent dropped below 10
- unique sampled colors dropped below 8
- no launch attempt produced an interactive menu (engine cursor never responded to pulse input)
- route did not reach the gameplay map
