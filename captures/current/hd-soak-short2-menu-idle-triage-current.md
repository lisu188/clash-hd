# HD Soak Failure Triage

- Overall: PASS
- Generated: `2026-07-12T18:47:58.405913+00:00`
- Runtime policy: repo-only soak failure triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Source report: `captures\current\hd-soak-short2-menu-idle-current.json`
- Source selection: `None`
- Canonical first-step report: `None`
- Canonical first-step present: `None`
- Legacy report: `None`
- Canonical runtime report missing: `None`
- Classification: `passing_run_no_failure`
- Next probe: repeat short2 or move to short10 only after preserving the report and validation guard output
- Tier / route: `short2` / `menu-idle`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Output directory: `C:\ClashCaptures\hd-soak\hd-soak-20260712-204302-short2-menu-idle`
- Final route marker: `intro-skip`

## Failure Context

- Failure timestamp: `2026-07-12T20:45:13.8595221+02:00` source=`last_process_sample`
- Crash/hang class: `passing_run_no_failure`
- Last route marker: `intro-skip`
- Next probe: repeat short2 or move to short10 only after preserving the report and validation guard output

## Visual Anomalies

- Overall: `PASS`
- Black/blank patch risk frames: `0`
- Palette/stripe risk frames: `0`
- Missing nonblack bounds frames: `0`

## Last Evidence

- Last route: `intro-skip` path=`True` click=`True` drift=`0` sample_drift=`0` click_mode=`postmessage` repeat=`8`
- Last frame: `frame-0007` size=`800x600` nonblack=`60.487` luma=`49.409` colors=`157`
- Last process: exited=`False` exit_code=`None` working_set=`43745280` handles=`643`

## Metrics

- `frame_sample_count`: `8`
- `frame_hash_unique_count`: `1`
- `frame_progress_expected`: `False`
- `frame_stability_class`: `stable_idle`
- `nonblack_percent_min`: `60.487`
- `nonblack_percent_max`: `60.487`
- `mean_luma_min`: `49.409`
- `mean_luma_max`: `49.409`
- `unique_sample_colors_min`: `157`
- `unique_sample_colors_max`: `157`
- `input_max_abs_error`: `0`
- `input_max_sample_abs_error`: `0`
- `max_input_drift_px`: `1`
- `process_sample_count`: `9`
- `working_set_growth_bytes`: `-188416`
- `private_memory_growth_bytes`: `-331776`
- `handle_growth`: `-2`
- `artifact_bytes`: `1541848`
- `guard_validation_evaluated`: `True`
- `guard_validation_overall`: `True`
- `guard_validation_failure_count`: `0`
