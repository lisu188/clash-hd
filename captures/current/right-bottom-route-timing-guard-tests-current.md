# Right-Bottom Route Timing Guard Tests

- Status: PASS
- Generated: `2026-07-18T21:30:22+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the right-bottom route timing guard rejects missing copyback/grid markers, marker-order regressions, visible fallback, surface/stage/SHA drift, grid proof failures, failure-exit rows, and AV rows

## Tests

- `right_bottom_route_timing_guard passes with clean hidden patch/full-start/grid logs`
- `right_bottom_route_timing_guard fails when a required route/copyback marker is missing`
- `right_bottom_route_timing_guard fails when marker order regresses`
- `right_bottom_route_timing_guard fails on visible fallback, wrong surface, wrong stage, or SHA disagreement`
- `right_bottom_route_timing_guard fails on grid proof, failure-exit, or AV regressions`
- `right_bottom_route_timing_guard CLI writes JSON/Markdown and returns 2 on --require-pass failure`
