# Handoff Freshness Guard

- Overall: FAIL
- Generated: `2026-09-08T11:21:53+02:00`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: handoff docs must mention the current route timing guard, keep validation stages out of stable until required proof exists, retain current manual-proof and completion artifacts, preserve the no-popup runtime preference, require the visible-runtime approval guard, and avoid stale route/input or VM blockers
- Supporting project guide: `docs\hd\WORKING_WITH_THIS_REPO.md`

## Phrase Groups

- `route_timing_artifacts`: `PASS`
- `owner_flag_inventory_artifacts`: `PASS`
- `load_slot_route_limit_artifacts`: `PASS`
- `load_slot_transition_readiness_artifacts`: `PASS`
- `manual_or_override_blocker`: `PASS`
- `no_visible_runtime_warning`: `FAIL`
  - Missing: `['Do not run visible/manual', 'explicit user approval']`
- `no_popup_operator_preference`: `FAIL`
  - Missing: `['Do not launch Clash95, CDB, wrappers, PowerShell harnesses', 'visible windows unless the user explicitly approves']`
- `right_bottom_safety_done`: `FAIL`
  - Missing: `['stable-stage promotion']`
- `manual_checklist_artifact`: `FAIL`
  - Missing: `['pending_manual_validation']`
- `manual_proof_template_artifact`: `FAIL`
  - Missing: `['template_valid_as_proof=False']`
- `completion_summary_artifact`: `PASS`
- `visible_runtime_launcher_guard`: `PASS`

## Loop Phrase Groups

- `loop_load_slot_transition_readiness_artifacts`: `FAIL`
  - Missing: `['load-slot-transition-readiness-current.md', 'load-slot-transition-readiness-tests-current.md', 'ready_for_hidden_transition_probe']`

## Files

- `.codex-loop\NEXT.md`: `FAIL` exists=`False`
- `.codex-loop\STATE.md`: `FAIL` exists=`False`
- `.codex-loop\TASKS.md`: `FAIL` exists=`False`
- `captures\current\hd-map-evidence-current.md`: `PASS` exists=`True`
- `docs\hd\HD_MOD_PROGRESS.md`: `PASS` exists=`True`
- `docs\hd\WORKING_WITH_THIS_REPO.md`: `PASS` exists=`True`

## Failures

- missing handoff file: .codex-loop\NEXT.md
- missing handoff file: .codex-loop\STATE.md
- missing handoff file: .codex-loop\TASKS.md
- missing current handoff phrase for no_visible_runtime_warning: Do not run visible/manual
- missing current handoff phrase for no_visible_runtime_warning: explicit user approval
- missing current handoff phrase for no_popup_operator_preference: Do not launch Clash95, CDB, wrappers, PowerShell harnesses
- missing current handoff phrase for no_popup_operator_preference: visible windows unless the user explicitly approves
- missing current handoff phrase for right_bottom_safety_done: stable-stage promotion
- missing current handoff phrase for manual_checklist_artifact: pending_manual_validation
- missing current handoff phrase for manual_proof_template_artifact: template_valid_as_proof=False
- missing current handoff phrase for loop_load_slot_transition_readiness_artifacts: load-slot-transition-readiness-current.md
- missing current handoff phrase for loop_load_slot_transition_readiness_artifacts: load-slot-transition-readiness-tests-current.md
- missing current handoff phrase for loop_load_slot_transition_readiness_artifacts: ready_for_hidden_transition_probe
