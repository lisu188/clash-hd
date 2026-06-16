# HD Soak Approval Preflight

- Overall: PASS
- Generated: `2026-06-16T16:05:31.432008+00:00`
- Runtime policy: repo-only visible-runtime approval preflight; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Status: `ready_for_explicit_approval`
- Current step: `short2_menu_idle`
- Current step status: `failed_classified_intro_skip_input_drift_exit`
- Canonical runtime report missing: `False`
- Stable stage should change: `False`
- Right-bottom promotion blocked: `True`

## Current Step Artifacts

- Report JSON: `captures\current\hd-soak-short2-menu-idle-current.json` exists=`True`
- Guard JSON: `captures\current\hd-soak-short2-menu-idle-guard-current.json` exists=`True`
- Triage JSON: `captures\current\hd-soak-short2-menu-idle-triage-current.json` exists=`True`

## Approval Prompt

Approve the short2_menu_idle visible-runtime soak using the exact approval-gated command in this report. This will open a visible Clash95 game window. It will generate a patched candidate under C:\ClashTests\hd-soak and raw frame artifacts under C:\ClashCaptures\hd-soak; it must not modify C:\Clash\clash95.exe, uses postmessage intro-skip harness prep (8 clicks plus 4 space pulses), does not treat intro skip as manual DirectInput proof, and enforces input drift <= 1px.

## Safe Dry Run

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route menu-idle -ReportJson captures\current\hd-soak-short2-menu-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-menu-idle-current.md -IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 -MaxInputDriftPx 1 -Json
```

## Approval-Gated Runtime Command

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\scripts\smoke\run_hd_soak.ps1' -InputExe 'C:\Clash\clash95.exe' -WorkDir 'C:\Clash' -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch' -Tier 'short2' -Route 'menu-idle' -CandidateDir 'C:\ClashTests\hd-soak' -CandidateName 'clash95_hd_soak_20260616_180529.exe' -OutputRoot 'C:\ClashCaptures\hd-soak' -ReportJson 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\current\hd-soak-short2-menu-idle-current.json' -ReportMarkdown 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\current\hd-soak-short2-menu-idle-current.md' -IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' -MaxInputDriftPx '1' -Execute -AllowVisibleRuntime -RequirePass -Json
```

## Dry-Run Plan

- Plan: `captures\current\hd-soak-dry-run-plan-current.json`
- Status: `ready_for_explicit_approval`
- Current step: `short2_menu_idle`
- Candidate path: `C:\ClashTests\hd-soak\clash95_hd_soak_20260616_180529.exe`
- Passing: `True`
- Freshness passing: `True`
- Max age hours: `12`

Plan-emitted execute command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\scripts\smoke\run_hd_soak.ps1' -InputExe 'C:\Clash\clash95.exe' -WorkDir 'C:\Clash' -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch' -Tier 'short2' -Route 'menu-idle' -CandidateDir 'C:\ClashTests\hd-soak' -CandidateName 'clash95_hd_soak_20260616_180529.exe' -OutputRoot 'C:\ClashCaptures\hd-soak' -ReportJson 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\current\hd-soak-short2-menu-idle-current.json' -ReportMarkdown 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\current\hd-soak-short2-menu-idle-current.md' -IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' -MaxInputDriftPx '1' -Execute -AllowVisibleRuntime -RequirePass -Json
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
