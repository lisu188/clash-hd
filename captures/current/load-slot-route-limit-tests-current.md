# Load Slot Route Limit Guard Tests

- Status: PASS
- Generated: `2026-06-16T18:04:51+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the load-slot route boundary remains a non-promoting repo-only classifier for the current slot5/right-bottom harness blocker

## Tests

- `load_slot_route_limit_guard passes with static ten-row evidence, slot2 LOADSAVE, and slot3-5 timeout blockers`
- `load_slot_route_limit_guard fails without static ten-row load-menu evidence`
- `load_slot_route_limit_guard fails when the proven slot2 route no longer reaches LOADSAVE`
- `load_slot_route_limit_guard fails closed when a currently blocked slot reaches LOADSAVE`
- `load_slot_route_limit_guard fails closed when a currently blocked slot reaches forced load-select`
- `load_slot_route_limit_guard CLI writes JSON/Markdown and honors --require-pass`
