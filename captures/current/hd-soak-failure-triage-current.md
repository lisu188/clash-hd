# HD Soak Failure Triage

- Overall: FAIL
- Generated: `2026-06-15T20:36:18.144672+00:00`
- Runtime policy: repo-only soak failure triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Source report: `captures\current\hd-soak-short-current.json`
- Classification: `not_executed_pending_approval`
- Next probe: obtain explicit approval for the exact short2 visible-runtime command, then rerun the soak
- Tier / route: `short2` / `menu-idle`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Candidate SHA-256: `None`
- Output directory: `C:\ClashCaptures\hd-soak\pending-approval`
- Final route marker: `pending_approval`

## Last Evidence

- Last route: `None` path=`None` click=`None`
- Last frame: `None` size=`NonexNone` nonblack=`None` luma=`None` colors=`None`
- Last process: exited=`None` exit_code=`None` working_set=`None` handles=`None`

## Metrics

- `frame_sample_count`: `0`
- `frame_hash_unique_count`: `0`
- `nonblack_percent_min`: `0.0`
- `nonblack_percent_max`: `0.0`
- `mean_luma_min`: `0.0`
- `mean_luma_max`: `0.0`
- `unique_sample_colors_min`: `0`
- `unique_sample_colors_max`: `0`
- `process_sample_count`: `0`
- `working_set_growth_bytes`: `None`
- `handle_growth`: `None`
- `artifact_bytes`: `0`

## Source Failures

- short2 menu-idle soak was not executed because visible-runtime escalation was not approved
