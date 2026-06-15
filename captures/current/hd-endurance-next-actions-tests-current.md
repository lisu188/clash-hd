# HD Endurance Next Actions Tests

- Status: PASS
- Generated: `2026-06-15T22:36:18+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the next-action report stays repo-only, separates safe dry-run commands from approval-gated visible runtime commands, pins canonical short2 report outputs, and records post-run validation steps

## Tests

- `hd_endurance_next_actions emits the exact approval-gated short2 runtime command with canonical report paths`
- `hd_endurance_next_actions fails closed when the release checklist is missing`
- `hd_endurance_next_actions switches complete fixtures to release-audit mode`
- `hd_endurance_next_actions CLI writes JSON/Markdown and passes as a triage artifact`
