# HD Endurance Next Actions

- Overall: FAIL
- Generated: `2026-07-12T17:43:40.197115+00:00`
- Runtime policy: repo-only endurance next-action triage; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Status: `repo_only_followup_available`
- Current short step: `short2_menu_idle`
- Full game complete: `False`
- Open requirements: `12`

## Next Action

- `refresh_short2_menu_idle_dry_run_plan`: `dry_run_plan_required`
- Requires visible runtime: `False`
- Requires explicit user approval: `False`
- Why: The release checklist cannot progress until one protected-stage short2 menu-idle soak passes, but visible-runtime approval must start from a fresh tokened dry-run plan.

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

Rejected legacy runtime command:

- Safe to run: `False`
- Reason: visible-runtime execution now requires a current dry-run plan command with -VisibleRuntimeApprovalExpiresUtc and -VisibleRuntimeApprovalToken
- Command body: omitted from Markdown; retained in JSON for audit.

Post-run handoff refresh:

- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_dry_run_plan.py --write-json captures\current\hd-soak-dry-run-plan-current.json --write-markdown captures\current\hd-soak-dry-run-plan-current.md --require-pass`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_endurance_release_checklist.py --write-json captures\current\hd-endurance-release-checklist-current.json --write-markdown captures\current\hd-endurance-release-checklist-current.md`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_intro_skip_rerun_readiness.py --write-json captures\current\hd-soak-intro-skip-rerun-readiness-current.json --write-markdown captures\current\hd-soak-intro-skip-rerun-readiness-current.md`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_endurance_next_actions.py --write-json captures\current\hd-endurance-next-actions-current.json --write-markdown captures\current\hd-endurance-next-actions-current.md --require-pass`
- `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\hd_soak_approval_preflight.py --write-json captures\current\hd-soak-approval-preflight-current.json --write-markdown captures\current\hd-soak-approval-preflight-current.md --require-pass`

## Open Requirement Groups

- `render baseline`: `first_mission_visual_clean`
- `endurance`: `short2_menu_idle_soak, long_soak_representative_routes`
- `manual input`: `stable_menu_real_input, stable_hd_map_real_input`
- `screen route`: `right_bottom_action_menu, castle_and_barracks_centered_input, tactical_battle_entry_return`
- `state continuity`: `save_load_roundtrip, turn_advancement, campaign_routes`
- `repo hygiene`: `artifact_and_process_hygiene`

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
- `artifact_and_process_hygiene` (`repo hygiene`, `blocked`): artifact or process hygiene guard is not passing Next probe: clear hygiene guard failures before accepting runtime evidence

## Failures

- intro-skip rerun readiness is not passing
- intro-skip rerun readiness status is 'not_ready'
