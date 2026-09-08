# Astra repository preparation verification

- Generated: `2026-09-05T07:44:46+00:00`
- Result: preparation complete; broader repository failures reported below.
- Configuration: `model = "gpt-6-astra"` only; reasoning effort inherits the user setting. TOML parsing and Git ignore checks pass. Local Codex state remains ignored.
- Both focused documentation fixture suites pass, including tracked defaults without local notes, missing documents, legacy overrides, stale claims, and required evidence references.
- Final handoff freshness guard: PASS. Final documentation consistency guard: FAIL solely because the no-popup boundary is failing.
- Aggregate: **157/166 passing; 9 failing**, generated `2026-09-05T09:41:47+02:00`. The command completed with exit code 0; that does not mean its checks all passed.
- No game/debugger execution, patch changes, promotion, artifact cleanup, or commit/push in this preparation validation.

## Aggregate failures

- `python_runtime_safety_guard`
- `hd_soak_execution_boundary`
- `hd_soak_dry_run_plan`
- `hd_soak_intro_skip_rerun_readiness`
- `hd_soak_long_report_guard`
- `hd_endurance_release_checklist`
- `hd_soak_approval_preflight`
- `no_popup_boundary_guard`
- `docs_consistency_guard`

## Interpretation

- python_runtime_safety_guard flags the existing hidden_soak_report_assembler.py as unclassified; no safety classification was weakened.
- The four negative approval probes and visible-harness dry-run fail because their PowerShell child cannot resolve Get-FileHash. All reported candidate/output side-effect flags remain false.
- Intro-skip readiness still assumes short2_map_idle although existing hidden evidence advances the status to short10_map_idle; related dry-run and preflight checks also fail.
- The short ladder is incomplete and both 2h representative routes lack passing proof. The endurance release checklist remains incomplete.
- no_popup_boundary_guard propagates these failures; docs_consistency_guard fails only with generated_state: no-popup boundary is failing. Both documentation fixture suites pass.

## Evidence and preservation

- [Aggregate summary](current-evidence-refresh-current.json)
- [Detailed preparation record](astra-preparation-current.json)
- [Current agent handoff](../../docs/hd/AGENT_HANDOFF.md)
- The earlier missing-dispatcher attempt is historical; current sources contain that function. The existing September 5 hidden 120-second pass was read as prior evidence, not executed by this preparation validation. Longer endurance and manual proof remain unfinished.
- Compared the final tree with the saved dirty-tree hash inventory. Existing non-report work and patcher source remain unchanged outside the configuration/onboarding/documentation-guard scope. Generated changes are reports from the explicitly requested aggregate refresh.
- The shared setting follows [official Codex configuration guidance](https://learn.chatgpt.com/docs/config-file/config-basic); global settings and permissions were not edited.
