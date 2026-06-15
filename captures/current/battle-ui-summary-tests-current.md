# Battle UI Summary Tests

- Status: PASS
- Generated: `2026-06-15T18:34:49+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for parser CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves battle summary classification is marker-driven, centered-offset aware, AV-aware, and refuses to promote route-candidate rows into battle-screen proof

## Tests

- `battle_ui_summary classifies centered native battle rows with command, grid, and modal proof`
- `battle_ui_summary classifies uncentered HD surface rows and AV rows without crashing`
- `battle_ui_summary does not treat route-candidate rows alone as battle-screen reachability`
- `battle_ui_summary CLI writes JSON/Markdown outputs`
