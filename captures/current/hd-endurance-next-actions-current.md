# HD Endurance Next Actions

- Overall: PASS
- Generated: `2026-09-08T09:22:06.644302+00:00`
- Runtime policy: repo-only endurance next-action triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Status: `repo_only_followup_available`
- Current short step: `short2_map_idle`
- Full game complete: `False`
- Open requirements: `8`

## Next Action

- `inspect_short2_map_idle_triage`: `triage_followup_required`
- Requires visible runtime: `False`
- Requires explicit user approval: `False`
- Why: inspect window_health_samples and wrapper transitions at the first missing-window phase before requesting any visible rerun

Current step artifacts:

- Report JSON: `captures\current\hd-soak-short2-map-idle-current.json` exists=`True`
- Guard JSON: `captures\current\hd-soak-short2-map-idle-guard-current.json` exists=`True`
- Triage JSON: `captures\current\hd-soak-short2-map-idle-triage-current.json` exists=`True`
- Canonical runtime report missing: `False`
- Post-run guard missing: `False`
- Post-run triage missing: `False`

Triage:

- Classification: `window_missing_while_process_alive`
- Next probe: inspect window_health_samples and wrapper transitions at the first missing-window phase before requesting any visible rerun
- Final route marker: `confirm-load`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`

Current failure:

- Classification: `window_missing_while_process_alive`
- Next probe: inspect window_health_samples and wrapper transitions at the first missing-window phase before requesting any visible rerun
- Final route marker: `confirm-load`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Visual anomaly passed: `True`
- Black/blank patch risk count: `0`
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

- `patch boundary`: `protected_stable_stage, no_speculative_promotion`
- `endurance`: `long_soak_representative_routes`
- `manual input`: `stable_menu_real_input, stable_hd_map_real_input`
- `screen route`: `right_bottom_action_menu, castle_and_barracks_centered_input, tactical_battle_entry_return`

## Open Requirement Details

- `protected_stable_stage` (`patch boundary`, `blocked`): stable-stage guard does not prove the protected boundary Next probe: fix stable-stage guard failures before considering any soak result
- `long_soak_representative_routes` (`endurance`, `blocked`): 2h+ representative-route soak blocked (locked_short_ladder_incomplete): 2h+ representative-route soak evidence is locked or missing Next probe: add long-tier reports only after short2/short10/short30 are stable
- `stable_menu_real_input` (`manual input`, `blocked`): menu-load proof remains pending manual DirectInput validation Next probe: collect approved manual menu-load proof or keep promotion blocked
- `stable_hd_map_real_input` (`manual input`, `blocked`): HD map input proof remains pending manual DirectInput validation Next probe: collect approved manual map input proof after short soak is stable
- `right_bottom_action_menu` (`screen route`, `blocked`): right-bottom action/menu remains validation-only or manual-proof blocked Next probe: replace debugger-forced action-click proof with natural or approved manual input proof
- `castle_and_barracks_centered_input` (`screen route`, `blocked`): castle/barracks centered input remains validation-only or manual-proof blocked Next probe: collect approved centered castle/barracks input proof
- `tactical_battle_entry_return` (`screen route`, `blocked`): battle promotion evidence is absent or remains validation-only; callback proof alone is not promotion Next probe: prove battle entry, UI use, return, and post-return map health on an approved route
- `no_speculative_promotion` (`patch boundary`, `blocked`): one or more promotion boundaries are not fail-closed Next probe: keep DEFAULT_STAGE unchanged until strict natural/manual/input and soak gates pass
