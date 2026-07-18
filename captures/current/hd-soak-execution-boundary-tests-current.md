# HD Soak Execution Boundary Tests

- Status: PASS
- Generated: `2026-07-18T22:14:46+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the negative execution-boundary reporter fails closed when bad visible-runtime approval packets would create candidate/output/report side effects

## Tests

- `hd_soak_execution_boundary accepts fake bad-approval failures before side effects`
- `hd_soak_execution_boundary rejects fake side effects before failure`
- `hd_soak_execution_boundary renders Markdown case rows`
- `hd_soak_execution_boundary writes JSON/Markdown reports`
