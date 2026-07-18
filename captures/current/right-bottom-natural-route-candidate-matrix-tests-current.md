# Right-Bottom Natural Route Candidate Matrix Tests

- Status: PASS
- Generated: `2026-07-18T21:36:13+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the right-bottom natural-route candidate matrix is a non-promoting repo-only classifier for save-state route candidates and current harness blockers

## Tests

- `right_bottom_natural_route_candidate_matrix passes with current slot0, slot2, and slot5 blocker shape`
- `right_bottom_natural_route_candidate_matrix fails without a slot5 route-compatible bit-2 record`
- `right_bottom_natural_route_candidate_matrix fails closed if slot5 no longer times out before LOADSAVE`
- `right_bottom_natural_route_candidate_matrix fails closed if slot2 no longer proves the current click misses`
- `right_bottom_natural_route_candidate_matrix CLI writes JSON/Markdown and honors --require-pass`
