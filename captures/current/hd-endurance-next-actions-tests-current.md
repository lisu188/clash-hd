# HD Endurance Next Actions Tests

- Status: PASS
- Generated: `2026-06-16T18:05:31+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the next-action report stays repo-only, separates safe dry-run commands from approval-gated visible runtime commands, pins canonical short-step report outputs, starts focused post-run validation with the failure-safe guard/triage refresh, keeps broad evidence refresh separate, keeps the short ladder ahead of later manual milestones, preserves classified failure triage, records current-step artifact inventory, records post-run validation steps, and requires the dry-run plan to verify the base executable

## Tests

- `hd_endurance_next_actions emits the exact approval-gated short2 runtime command with canonical report paths and explicit input-drift limit`
- `hd_endurance_next_actions fails closed when the release checklist is missing`
- `hd_endurance_next_actions switches complete fixtures to release-audit mode`
- `hd_endurance_next_actions keeps later pending short-soak steps ahead of manual milestones`
- `hd_endurance_next_actions includes the stricter dry-run-plan execute command when available`
- `hd_endurance_next_actions records current short-step report, guard, and triage artifact inventory`
- `hd_endurance_next_actions fails closed when the dry-run plan does not match the next short step`
- `hd_endurance_next_actions fails closed when the dry-run plan is stale`
- `hd_endurance_next_actions fails closed when the dry-run plan does not verify the base executable`
- `hd_endurance_next_actions starts focused post-run validation with the failure-safe guard/triage refresh`
- `hd_endurance_next_actions requests repo-only triage when a failed short-step report lacks triage`
- `hd_endurance_next_actions points classified failed short steps at their next probe`
- `hd_endurance_next_actions turns a classified intro-skip failure into a rerun approval only after readiness passes`
- `hd_endurance_next_actions CLI writes JSON/Markdown and passes as a triage artifact`
