# Current Completion Summary Tests

- Status: PASS
- Generated: `2026-06-15T20:47:22+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the generated percentage summary stays machine-checkable and does not claim full-game completion while manual proof is absent

## Tests

- `current_completion_summary computes repo evidence, focused lane, promotion, and manual validation percentages`
- `current_completion_summary fails closed when focused completion percentage is missing`
- `current_completion_summary CLI writes JSON/Markdown and returns 2 under --require-pass failure`
