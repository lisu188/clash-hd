# HD Soak Route Coverage Tests

- Status: PASS
- Generated: `2026-06-15T22:36:18+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the soak harness exposes the required short routes and tiers while future castle, battle, right-bottom, save/load, turn, and campaign lanes stay planned/non-promoting

## Tests

- `hd_soak_route_coverage passes the current short-route harness contract`
- `hd_soak_route_coverage keeps future release lanes non-promoting`
- `hd_soak_route_coverage fails closed when a required route is missing`
- `hd_soak_route_coverage fails closed when a short-tier duration drifts`
- `hd_soak_route_coverage CLI writes JSON/Markdown and respects --require-pass`
