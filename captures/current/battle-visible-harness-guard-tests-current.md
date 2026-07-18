# Battle Visible Harness Guard Tests

- Status: PASS
- Generated: `2026-07-18T22:14:32+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the visible battle input harness keeps explicit approval, fatal CDB log detection, post-g gating, and incremental log scanning before any future manual run

## Tests

- `visible battle harness guard accepts a source-safe harness with explicit runtime approval`
- `visible battle harness guard rejects missing fatal CDB breakpoint patterns`
- `visible battle harness guard rejects missing post-g break-instruction gating`
- `visible battle harness guard rejects non-incremental CDB log scans`
- `visible battle harness guard CLI writes outputs and fails closed under --require-pass`
