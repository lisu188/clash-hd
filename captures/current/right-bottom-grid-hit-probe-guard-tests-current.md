# Right-Bottom Grid Hit Probe Guard Tests

- Status: PASS
- Generated: `2026-07-18T10:42:09+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the right-bottom grid-hit probe guard rejects missing breakpoints, missing probe/parser markers, visible fallback, stage/surface regressions, missing grid proof, failure-exit rows, and AV rows

## Tests

- `right_bottom_grid_hit_probe_guard passes with the focused probe shape and clean hidden-desktop log`
- `right_bottom_grid_hit_probe_guard fails when each owner/action/grid breakpoint is missing`
- `right_bottom_grid_hit_probe_guard fails when each required probe or parser marker is missing`
- `right_bottom_grid_hit_probe_guard fails on visible fallback, wrong stage, or wrong surface size`
- `right_bottom_grid_hit_probe_guard fails on missing grid proof, failure-exit rows, or AV rows`
- `right_bottom_grid_hit_probe_guard CLI writes JSON/Markdown and returns 2 on --require-pass failure`
