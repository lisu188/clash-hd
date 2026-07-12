# HD Endurance Next Actions

- Overall: PASS
- Generated: `2026-07-12T14:09:25.136503+00:00`
- Runtime policy: repo-only endurance next-action triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Status: `waiting_for_explicit_visible_runtime_approval`
- Current short step: `short2_menu_idle`
- Full game complete: `False`
- Open requirements: `11`

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
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 -Tier short2 -Route menu-idle -ReportJson captures\current\hd-soak-short2-menu-idle-current.json -ReportMarkdown captures\current\hd-soak-short2-menu-idle-current.md -IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 -SampleIntervalSec 15 -MaxInputDriftPx 1 -MinNonblackPercent 10 -MinUniqueSampleColors 8 -MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 -MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 -Json
```

Approval-gated runtime command (plan-verified):

- Dry-run plan status: `ready_for_explicit_approval`
- Candidate path: `C:\ClashTests\hd-soak\clash95_hd_soak_20260712_160923.exe`
- Output root: `C:\ClashCaptures\hd-soak`

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\andrz\git\clash-hd\scripts\smoke\run_hd_soak.ps1' -InputExe 'C:\Clash\clash95.exe' -WorkDir 'C:\Clash' -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch' -Tier 'short2' -Route 'menu-idle' -CandidateDir 'C:\ClashTests\hd-soak' -CandidateName 'clash95_hd_soak_20260712_160923.exe' -OutputRoot 'C:\ClashCaptures\hd-soak' -ReportJson 'C:\Users\andrz\git\clash-hd\captures\current\hd-soak-short2-menu-idle-current.json' -ReportMarkdown 'C:\Users\andrz\git\clash-hd\captures\current\hd-soak-short2-menu-idle-current.md' -IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' -SampleIntervalSec '15' -MaxInputDriftPx '1' -MinNonblackPercent '10' -MinUniqueSampleColors '8' -MaxArtifactMB '250' -MaxWorkingSetGrowthMB '64' -MaxPrivateMemoryGrowthMB '64' -MaxHandleGrowth '128' -VisibleRuntimeApprovalExpiresUtc '2026-07-13T02:09:23.6088567+00:00' -VisibleRuntimeApprovalToken 'f3d51c087254cec7' -Execute -AllowVisibleRuntime -RequirePass -Json
```

Rejected legacy runtime command:

- Safe to run: `False`
- Reason: superseded by the current dry-run plan command with visible-runtime approval token
- Command body: omitted from Markdown; retained in JSON for audit.

Current failure:

- Classification: `intro_skip_input_drift_exit`
- Next probe: previous intro-skip click used sendinput and drifted after button events; rerun only with the current tokenized postmessage/space-pulse intro-skip command after explicit visible-window approval
- Final route marker: `intro-skip`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Visual anomaly passed: `False`
- Black/blank patch risk count: `1`
- Palette/stripe risk count: `0`
- Missing nonblack bounds count: `0`

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

- `render baseline`: `first_mission_visual_clean`
- `endurance`: `short2_menu_idle_soak, long_soak_representative_routes`
- `manual input`: `stable_menu_real_input, stable_hd_map_real_input`
- `screen route`: `right_bottom_action_menu, castle_and_barracks_centered_input, tactical_battle_entry_return`
- `state continuity`: `save_load_roundtrip, turn_advancement, campaign_routes`

## Open Requirement Details

- `first_mission_visual_clean` (`render baseline`, `blocked`): first-mission visual audit is not clean (selected_unit_action_bar_on_bottom_but_black_ui_patches_remain); black patches: right_below_minimap, bottom_right_panel, minimap_interior Next probe: fix right/bottom/minimap black patches before treating first-mission playability as release-ready
- `short2_menu_idle_soak` (`endurance`, `blocked`): short2 visible-runtime soak has not produced passing frame/process evidence; current short-step status is failed_classified_intro_skip_input_drift_exit Next probe: run the approval-gated short2 menu-idle soak on the protected stage
- `long_soak_representative_routes` (`endurance`, `blocked`): 2h+ representative-route soak blocked (locked_short_ladder_incomplete): 2h+ representative-route soak evidence is locked or missing Next probe: add long-tier reports only after short2/short10/short30 are stable
- `stable_menu_real_input` (`manual input`, `blocked`): menu-load proof remains pending manual DirectInput validation Next probe: collect approved manual menu-load proof or keep promotion blocked
- `stable_hd_map_real_input` (`manual input`, `blocked`): HD map input proof remains pending manual DirectInput validation Next probe: collect approved manual map input proof after short soak is stable
- `right_bottom_action_menu` (`screen route`, `blocked`): right-bottom action/menu remains validation-only or manual-proof blocked Next probe: replace debugger-forced action-click proof with natural or approved manual input proof
- `castle_and_barracks_centered_input` (`screen route`, `blocked`): castle/barracks centered input remains validation-only or manual-proof blocked Next probe: collect approved centered castle/barracks input proof
- `tactical_battle_entry_return` (`screen route`, `blocked`): battle evidence remains validation-only or missing visible click-to-callback proof Next probe: prove battle entry, UI use, return, and post-return map health on an approved route
- `save_load_roundtrip` (`state continuity`, `blocked`): save/load continuity proof blocked (blocked_missing_proof): continuity proof is missing or not sufficient for release Next probe: add safe test-save roundtrip evidence after short-tier stability
- `turn_advancement` (`state continuity`, `blocked`): turn advancement proof blocked (blocked_missing_proof): continuity proof is missing or not sufficient for release Next probe: add deterministic turn-advance route evidence after save/load is safe
- `campaign_routes` (`state continuity`, `blocked`): campaign route proof blocked (blocked_missing_proof): continuity proof is missing or not sufficient for release Next probe: add representative campaign route soaks after short/medium tiers are stable
