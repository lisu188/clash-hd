# Castle Overview Gate Tests

- Status: PASS
- Generated: `2026-07-12T19:43:18+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for gate CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the castle overview visual/catalog gate rejects missing readiness, AV rows, missing or wrong overview post-draw and surface sizes, missing expected commands, centered-geometry regressions, barracks baseline regressions, and fails closed under --require-pass

## Tests

- `castle_overview_gate passes with catalog, geometry, and barracks baseline inputs passing`
- `castle_overview_gate fails on overview readiness, AV, post-draw, surface-size, command, and geometry regressions`
- `castle_overview_gate fails when the barracks baseline regresses`
- `castle_overview_gate CLI writes JSON/Markdown and returns 2 on --require-pass failure`
