# HD Soak Route Coverage Tests

- Status: PASS
- Generated: `2026-07-12T19:43:40+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the soak harness exposes the required short routes and tiers while future castle, battle, right-bottom, save/load, turn, and campaign lanes stay planned/non-promoting with locked non-executable route contracts and current blocker annotations from the release checklist

## Tests

- `hd_soak_route_coverage passes the current short-route harness contract`
- `hd_soak_route_coverage keeps future release lanes non-promoting`
- `hd_soak_route_coverage keeps locked future route plans non-executable`
- `hd_soak_route_coverage annotates lanes with current release-checklist blockers`
- `hd_soak_route_coverage treats a missing release checklist as nonfatal`
- `hd_soak_route_coverage fails closed when linked release requirements go stale`
- `hd_soak_route_coverage fails closed when a required route is missing`
- `hd_soak_route_coverage fails closed when a short-tier duration drifts`
- `hd_soak_route_coverage CLI writes JSON/Markdown and respects --require-pass`
