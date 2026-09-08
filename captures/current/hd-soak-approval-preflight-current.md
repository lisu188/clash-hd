# HD Soak Approval Preflight

- Overall: FAIL
- Generated: `2026-09-08T09:22:07.408580+00:00`
- Runtime policy: repo-only visible-runtime approval preflight; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Status: `not_ready`
- Current step: `short2_map_idle`
- Current step status: `failed_classified_window_missing_while_process_alive`
- Canonical runtime report missing: `False`
- Stable stage should change: `False`
- Right-bottom promotion blocked: `True`

## Current Step Artifacts

- Report JSON: `captures\current\hd-soak-short2-map-idle-current.json` exists=`True`
- Guard JSON: `captures\current\hd-soak-short2-map-idle-guard-current.json` exists=`True`
- Triage JSON: `captures\current\hd-soak-short2-map-idle-triage-current.json` exists=`True`

## Approval Prompt

Approve the short2_map_idle visible-runtime soak using the exact approval-gated command in this report. This will open a visible Clash95 game window in explicitly windowed mode using token-pinned display=application and presentation=windowed configuration. It will generate a patched candidate under C:\ClashTests\hd-soak and raw frame artifacts under C:\ClashCaptures\hd-soak; it must not modify C:\Clash\clash95.exe, uses postmessage intro-skip harness prep (8 clicks plus 4 space pulses), does not treat intro skip as manual DirectInput proof, and enforces input drift <= 1px, frame thresholds, artifact budget, process-growth limits, and a fresh copy-exact approval token. The harness samples target-window responsiveness around every route/capture phase and stops further input and capture at the first hung or missing live target window.

## Current Failure

- Classification: `window_missing_while_process_alive`
- Next probe: inspect window_health_samples and wrapper transitions at the first missing-window phase before requesting any visible rerun
- Final route marker: `confirm-load`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Visual anomaly passed: `True`
- Black/blank patch risk count: `0`
- Palette/stripe risk count: `0`
- Missing nonblack bounds count: `0`

## Approval Limits

- sample_interval_sec: `None`
- max_input_drift_px: `None`
- min_nonblack_percent: `None`
- min_unique_sample_colors: `None`
- max_artifact_mb: `None`
- max_working_set_growth_mb: `None`
- max_private_memory_growth_mb: `None`
- max_handle_growth: `None`
- approval_token_kind: `None`
- approval_expires_utc: `None`
- approval_remaining_seconds: `None`
- min_approval_ttl_minutes: `30`
- window_health_stop_required: `True`

## Safe Dry Run

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route map-idle -ReportJson captures\current\hd-soak-short2-map-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-map-idle-current.md -IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 -SampleIntervalSec 15 -MaxInputDriftPx 1 -MinNonblackPercent 10 -MinUniqueSampleColors 8 -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 -Json
```

## Approval-Gated Runtime Command

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route map-idle -ReportJson captures\current\hd-soak-short2-map-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-map-idle-current.md -IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 -SampleIntervalSec 15 -MaxInputDriftPx 1 -MinNonblackPercent 10 -MinUniqueSampleColors 8 -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 -Execute -AllowVisibleRuntime -RequirePass -Json
```

## Dry-Run Plan

- Plan: `captures\current\hd-soak-dry-run-plan-current.json`
- Status: `dry_run_plan_invalid`
- Current step: `short2_map_idle`
- Candidate path: `None`
- Passing: `False`
- Freshness passing: `True`
- Max age hours: `12`

Plan-emitted execute command:

```powershell

```

## Focused Post-Run Validation

- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_short_validation_refresh.py --write-json captures\current\hd-soak-short-validation-refresh-current.json --write-markdown captures\current\hd-soak-short-validation-refresh-current.md --require-pass`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_short_step_status.py --write-json captures\current\hd-soak-short-step-status-current.json --write-markdown captures\current\hd-soak-short-step-status-current.md --require-pass`
- `git diff --check`

## Post-Run Handoff Refresh

- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_dry_run_plan.py --write-json captures\current\hd-soak-dry-run-plan-current.json --write-markdown captures\current\hd-soak-dry-run-plan-current.md --require-pass`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_endurance_release_checklist.py --write-json captures\current\hd-endurance-release-checklist-current.json --write-markdown captures\current\hd-endurance-release-checklist-current.md`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_intro_skip_rerun_readiness.py --write-json captures\current\hd-soak-intro-skip-rerun-readiness-current.json --write-markdown captures\current\hd-soak-intro-skip-rerun-readiness-current.md`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_endurance_next_actions.py --write-json captures\current\hd-endurance-next-actions-current.json --write-markdown captures\current\hd-endurance-next-actions-current.md --require-pass`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_approval_preflight.py --write-json captures\current\hd-soak-approval-preflight-current.json --write-markdown captures\current\hd-soak-approval-preflight-current.md --require-pass`

## Broad Evidence Refresh

- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\current_evidence_refresh.py --write-json captures\current\current-evidence-refresh-current.json --write-markdown captures\current\current-evidence-refresh-current.md`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\evidence_index_check.py captures\current\hd-map-evidence-current.md --require-pass`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\current_completion_summary.py --write-json captures\current\current-completion-summary-current.json --write-markdown captures\current\current-completion-summary-current.md --require-pass`
- `git diff --check`

## Failures

- dry-run plan report is not passing
- dry-run plan status is 'dry_run_plan_invalid'
- dry-run plan payload is not marked as a dry run
- dry-run plan would change the stable stage
- dry-run plan does not keep right-bottom promotion blocked
- dry-run plan tier/route do not match the current step
- dry-run plan does not pin max input drift to 1 px
- dry-run plan sample_interval_sec is not 15
- dry-run plan does not pin min nonblack percent
- dry-run plan does not pin min unique sample colors
- dry-run plan growth limit max_artifact_mb is not 250
- dry-run plan growth limit max_working_set_growth_mb is not 64
- dry-run plan growth limit max_private_memory_growth_mb is not 64
- dry-run plan growth limit max_handle_growth is not 128
- dry-run plan intro_skip click_mode is not postmessage
- dry-run plan intro_skip click_repeat is not 8
- dry-run plan intro_skip does not stop repeated clicks on transition drift
- dry-run plan intro_skip space_pulses is not 4
- dry-run plan intro_skip proof_class is missing the non-manual proof boundary
- dry-run plan windowed-mode check is not required and passing
- dry-run plan window display is not application
- dry-run plan window presentation is not windowed
- dry-run plan windowed config SHA-256 is missing or malformed
- dry-run plan visible runtime approval token is missing or malformed
- dry-run plan visible runtime approval token_kind is not sha256-16
- dry-run plan visible runtime approval expires_utc is missing
- dry-run plan visible runtime approval min_ttl_minutes is not 30
- dry-run plan visible runtime approval expires_utc is missing or invalid
- dry-run plan visible runtime approval purpose is missing
- dry-run plan candidate_dir is not C:\ClashTests\hd-soak
- dry-run plan output_root is not C:\ClashCaptures\hd-soak
- dry-run plan input_exe does not exist or was not confirmed readable
- dry-run plan base_sha_status is None, expected 'ok'
- dry-run plan execute command missing fragment: -InputExe
- dry-run plan execute command missing fragment: C:\Clash\clash95.exe
- dry-run plan execute command missing fragment: -WorkDir
- dry-run plan execute command missing fragment: C:\Clash
- dry-run plan execute command missing fragment: -Stage
- dry-run plan execute command missing fragment: -OutputRoot
- dry-run plan execute command missing fragment: C:\ClashCaptures\hd-soak
- dry-run plan execute command missing fragment: -IntroSkipClickMode
- dry-run plan execute command missing fragment: postmessage
- dry-run plan execute command missing fragment: -IntroSkipClicks
- dry-run plan execute command missing fragment: 8
- dry-run plan execute command missing fragment: -SkipPulses
- dry-run plan execute command missing fragment: 4
- dry-run plan execute command missing fragment: -VisibleRuntimeApprovalExpiresUtc
- dry-run plan execute command missing fragment: -VisibleRuntimeApprovalToken
- dry-run plan execute command missing fragment: -Execute
- dry-run plan execute command missing fragment: -AllowVisibleRuntime
- dry-run plan execute command missing fragment: -RequirePass
- dry-run plan execute command missing fragment: -Json
- dry-run plan execute command missing fragment: -MaxInputDriftPx
- dry-run plan execute command missing fragment: -SampleIntervalSec
- dry-run plan execute command missing fragment: -MinNonblackPercent
- dry-run plan execute command missing fragment: -MinUniqueSampleColors
- dry-run plan execute command missing fragment: -MaxArtifactMB
- dry-run plan execute command missing fragment: -MaxWorkingSetGrowthMB
- dry-run plan execute command missing fragment: -MaxPrivateMemoryGrowthMB
- dry-run plan execute command missing fragment: -MaxHandleGrowth
- dry-run plan execute command does not include the canonical report JSON path
- dry-run plan execute command does not include the canonical report Markdown path
- current short-step status is 'failed_classified_window_missing_while_process_alive'
- dry_run_plan is not passing
- window-missing rerun readiness is missing window-health mitigation and passing harness-guard evidence
