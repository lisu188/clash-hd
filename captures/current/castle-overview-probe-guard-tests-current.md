# Castle Overview Probe Guard Tests

- Status: PASS
- Generated: `2026-07-12T20:03:45+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the castle overview probe guard rejects missing descriptor-loop breakpoints, missing probe/parser markers, old crashing overview wrapper markers, AV rows, missing wrapper/gate proof rows, and surface-size regressions in the focused hitbox log, while its CLI writes outputs and fails closed under --require-pass

## Tests

- `castle_overview_probe_guard passes with the focused probe shape and clean focused log`
- `castle_overview_probe_guard fails when each descriptor-loop breakpoint is missing`
- `castle_overview_probe_guard fails when each required probe marker is missing`
- `castle_overview_probe_guard fails when each required parser marker is missing`
- `castle_overview_probe_guard fails when either old crashing overview wrapper marker returns`
- `castle_overview_probe_guard fails when focused hitbox log AV rows are present`
- `castle_overview_probe_guard fails when focused hitbox log wrapper proof rows or surface sizes regress`
- `castle_overview_probe_guard CLI writes JSON/Markdown and returns 2 on --require-pass failure`
