# HD Soak Approval Preflight

- Overall: PASS
- Generated: `2026-07-18T08:59:08.658752+00:00`
- Runtime policy: repo-only visible-runtime approval preflight; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Status: `ready_for_explicit_approval`
- Current step: `short2_map_idle`
- Current step status: `failed_classified_input_environment_permission_denied`
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

- Classification: `input_environment_permission_denied`
- Next probe: SetForegroundWindow was silently denied on every aim iteration, so the foreground-mode DirectInput never received the injected pulses; rerun the exact tokenized route command DIRECTLY from an interactive session with input standing (never via Start-Job or any detached/non-interactive wrapper), and do not change patches or lower visual thresholds
- Final route marker: `intro-skip`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Visual anomaly passed: `True`
- Black/blank patch risk count: `0`
- Palette/stripe risk count: `0`
- Missing nonblack bounds count: `0`

## Approval Limits

- sample_interval_sec: `15`
- max_input_drift_px: `1`
- min_nonblack_percent: `10`
- min_unique_sample_colors: `8`
- max_artifact_mb: `250`
- max_working_set_growth_mb: `64`
- max_private_memory_growth_mb: `64`
- max_handle_growth: `128`
- approval_token_kind: `sha256-16`
- approval_expires_utc: `2026-07-18T20:58:58.0600415+00:00`
- approval_remaining_seconds: `43189.401793`
- min_approval_ttl_minutes: `30`
- window_health_stop_required: `True`

## Safe Dry Run

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route map-idle -ReportJson captures\current\hd-soak-short2-map-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-map-idle-current.md -IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 -SampleIntervalSec 15 -MaxInputDriftPx 1 -MinNonblackPercent 10 -MinUniqueSampleColors 8 -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 -Json
```

## Approval-Gated Runtime Command

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\andrz\git\clash-hd\scripts\smoke\run_hd_soak.ps1' -InputExe 'C:\Clash\clash95.exe' -WorkDir 'C:\Clash' -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch' -Tier 'short2' -Route 'map-idle' -CandidateDir 'C:\ClashTests\hd-soak' -CandidateName 'clash95_hd_soak_20260718_105858.exe' -OutputRoot 'C:\ClashCaptures\hd-soak' -ReportJson 'C:\Users\andrz\git\clash-hd\captures\current\hd-soak-short2-map-idle-current.json' -ReportMarkdown 'C:\Users\andrz\git\clash-hd\captures\current\hd-soak-short2-map-idle-current.md' -IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' -SampleIntervalSec '15' -MaxInputDriftPx '1' -MinNonblackPercent '10' -MinUniqueSampleColors '8' -MaxArtifactMB '250' -MaxWorkingSetGrowthMB '64' -MaxPrivateMemoryGrowthMB '64' -MaxHandleGrowth '128' -VisibleRuntimeApprovalExpiresUtc '2026-07-18T20:58:58.0600415+00:00' -VisibleRuntimeApprovalToken '74bb576847312baf' -Execute -AllowVisibleRuntime -RequirePass -Json
```

## Dry-Run Plan

- Plan: `captures\current\hd-soak-dry-run-plan-current.json`
- Status: `ready_for_explicit_approval`
- Current step: `short2_map_idle`
- Candidate path: `C:\ClashTests\hd-soak\clash95_hd_soak_20260718_105858.exe`
- Passing: `True`
- Freshness passing: `True`
- Max age hours: `12`

Plan-emitted execute command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\andrz\git\clash-hd\scripts\smoke\run_hd_soak.ps1' -InputExe 'C:\Clash\clash95.exe' -WorkDir 'C:\Clash' -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch' -Tier 'short2' -Route 'map-idle' -CandidateDir 'C:\ClashTests\hd-soak' -CandidateName 'clash95_hd_soak_20260718_105858.exe' -OutputRoot 'C:\ClashCaptures\hd-soak' -ReportJson 'C:\Users\andrz\git\clash-hd\captures\current\hd-soak-short2-map-idle-current.json' -ReportMarkdown 'C:\Users\andrz\git\clash-hd\captures\current\hd-soak-short2-map-idle-current.md' -IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' -SampleIntervalSec '15' -MaxInputDriftPx '1' -MinNonblackPercent '10' -MinUniqueSampleColors '8' -MaxArtifactMB '250' -MaxWorkingSetGrowthMB '64' -MaxPrivateMemoryGrowthMB '64' -MaxHandleGrowth '128' -VisibleRuntimeApprovalExpiresUtc '2026-07-18T20:58:58.0600415+00:00' -VisibleRuntimeApprovalToken '74bb576847312baf' -Execute -AllowVisibleRuntime -RequirePass -Json
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
