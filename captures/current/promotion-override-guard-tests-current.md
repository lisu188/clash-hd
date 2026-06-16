# Promotion Override Guard Tests

- Status: PASS
- Generated: `2026-06-16T18:05:26+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the current evidence fails closed if CDB-only promotion overrides, manual proof, or promotion-ready states become active unexpectedly

## Tests

- `promotion_override_guard passes when current override/proof flags are inactive`
- `promotion_override_guard rejects a right-bottom CDB-only override`
- `promotion_override_guard rejects a castle overview CDB-only override`
- `promotion_override_guard rejects a promotion-ready manual checklist override`
- `promotion_override_guard rejects manual proof in current no-popup evidence`
- `promotion_override_guard rejects missing promotion/checklist JSON`
- `promotion_override_guard CLI writes JSON/Markdown and returns 2 on --require-pass failure`
