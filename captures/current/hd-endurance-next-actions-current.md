# HD Endurance Next Actions

- Overall: PASS
- Generated: `2026-06-16T16:05:30.994182+00:00`
- Runtime policy: repo-only endurance next-action triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Status: `waiting_for_explicit_visible_runtime_approval`
- Current short step: `short2_menu_idle`
- Full game complete: `False`
- Open requirements: `10`

## Next Action

- `rerun_short2_menu_idle_soak`: `approval_required`
- Requires visible runtime: `True`
- Requires explicit user approval: `True`
- Why: The previous short2 menu-idle run failed during intro-skip input, and the repo-only rerun readiness gate now proves the harness uses postmessage intro-skip prep. Rerun only after explicit visible-window approval.

Current step artifacts:

- Report JSON: `captures\current\hd-soak-short2-menu-idle-current.json` exists=`True`
- Guard JSON: `captures\current\hd-soak-short2-menu-idle-guard-current.json` exists=`True`
- Triage JSON: `captures\current\hd-soak-short2-menu-idle-triage-current.json` exists=`True`
- Canonical runtime report missing: `False`
- Post-run guard missing: `False`
- Post-run triage missing: `False`

Safe dry-run command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route menu-idle -ReportJson captures\current\hd-soak-short2-menu-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-menu-idle-current.md -IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 -MaxInputDriftPx 1 -Json
```

Approval-gated runtime command (plan-verified):

- Dry-run plan status: `ready_for_explicit_approval`
- Candidate path: `C:\ClashTests\hd-soak\clash95_hd_soak_20260616_180529.exe`
- Output root: `C:\ClashCaptures\hd-soak`

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\scripts\smoke\run_hd_soak.ps1' -InputExe 'C:\Clash\clash95.exe' -WorkDir 'C:\Clash' -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch' -Tier 'short2' -Route 'menu-idle' -CandidateDir 'C:\ClashTests\hd-soak' -CandidateName 'clash95_hd_soak_20260616_180529.exe' -OutputRoot 'C:\ClashCaptures\hd-soak' -ReportJson 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\current\hd-soak-short2-menu-idle-current.json' -ReportMarkdown 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\current\hd-soak-short2-menu-idle-current.md' -IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' -MaxInputDriftPx '1' -Execute -AllowVisibleRuntime -RequirePass -Json
```

Legacy step-status runtime command:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route menu-idle -ReportJson captures\current\hd-soak-short2-menu-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-menu-idle-current.md -IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 -MaxInputDriftPx 1 -Execute -AllowVisibleRuntime -RequirePass -Json
```

Focused post-run validation:

- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_short_validation_refresh.py --write-json captures\current\hd-soak-short-validation-refresh-current.json --write-markdown captures\current\hd-soak-short-validation-refresh-current.md --require-pass`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_short_step_status.py --write-json captures\current\hd-soak-short-step-status-current.json --write-markdown captures\current\hd-soak-short-step-status-current.md --require-pass`
- `git diff --check`

Post-run handoff refresh:

- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_dry_run_plan.py --write-json captures\current\hd-soak-dry-run-plan-current.json --write-markdown captures\current\hd-soak-dry-run-plan-current.md --require-pass`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_endurance_release_checklist.py --write-json captures\current\hd-endurance-release-checklist-current.json --write-markdown captures\current\hd-endurance-release-checklist-current.md`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_intro_skip_rerun_readiness.py --write-json captures\current\hd-soak-intro-skip-rerun-readiness-current.json --write-markdown captures\current\hd-soak-intro-skip-rerun-readiness-current.md`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_endurance_next_actions.py --write-json captures\current\hd-endurance-next-actions-current.json --write-markdown captures\current\hd-endurance-next-actions-current.md --require-pass`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_approval_preflight.py --write-json captures\current\hd-soak-approval-preflight-current.json --write-markdown captures\current\hd-soak-approval-preflight-current.md --require-pass`

Broad evidence refresh:

- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\current_evidence_refresh.py --write-json captures\current\current-evidence-refresh-current.json --write-markdown captures\current\current-evidence-refresh-current.md`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\evidence_index_check.py captures\current\hd-map-evidence-current.md --require-pass`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\current_completion_summary.py --write-json captures\current\current-completion-summary-current.json --write-markdown captures\current\current-completion-summary-current.md --require-pass`
- `git diff --check`

## Open Requirement Groups

- `endurance`: `short2_menu_idle_soak, long_soak_representative_routes`
- `manual input`: `stable_menu_real_input, stable_hd_map_real_input`
- `screen route`: `right_bottom_action_menu, castle_and_barracks_centered_input, tactical_battle_entry_return`
- `state continuity`: `save_load_roundtrip, turn_advancement, campaign_routes`
