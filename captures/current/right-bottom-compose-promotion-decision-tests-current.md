# Right-Bottom Compose Promotion Decision Tests

- Status: PASS
- Generated: `2026-06-15T18:34:35+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for decision CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the right-bottom compose promotion decision defers by default, fails closed for missing/failing route/grid/timing gates, rejects placeholder proof files, and only permits promotion with a valid manual proof manifest or an explicit CDB-only override

## Tests

- `right_bottom_compose_promotion_decision defers stable promotion by default`
- `right_bottom_compose_promotion_decision fails when any required route/gate/grid/natural-route/timing check is missing or failing`
- `right_bottom_compose_promotion_decision fails when natural route owner-flag, descriptor, action-route, or AV facts regress`
- `right_bottom_compose_promotion_decision allows stable promotion only with a valid manual/real input proof manifest`
- `right_bottom_compose_promotion_decision rejects placeholder manual input proof files`
- `right_bottom_compose_promotion_decision allows CDB-only promotion only with an explicit override`
- `right_bottom_compose_promotion_decision CLI writes JSON/Markdown and returns 2 on --require-pass failure`
