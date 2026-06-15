# Right-Bottom Grid Hit Summary Tests

- Status: PASS
- Generated: `2026-06-15T20:46:35+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for parser CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the right-bottom grid-hit parser requires ready rows, native coordinate (450,73), expected grid result 0, draw rows, no failure-exit rows, and no AV rows

## Tests

- `right_bottom_grid_hit_summary parses controlled native grid-hit proof rows`
- `right_bottom_grid_hit_summary CLI writes JSON/Markdown and returns 2 on required proof regressions`
