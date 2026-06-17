# No-Visible Runtime Guard Tests

- Status: PASS
- Generated: `2026-06-17T09:48:12+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the no-visible runtime guard requires hidden-desktop launch summaries, explicit no-visible runtime policy text, present run summaries, and CLI fail-closed behavior

## Tests

- `no_visible_runtime_guard passes hidden-desktop surface-dump summaries`
- `no_visible_runtime_guard rejects weak runtime policy text`
- `no_visible_runtime_guard rejects visible runtime regression summaries`
- `no_visible_runtime_guard rejects missing run summaries`
- `no_visible_runtime_guard CLI writes JSON/Markdown and returns 2 on --require-pass failure`
