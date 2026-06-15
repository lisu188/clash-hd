# HD Soak Harness Guard Tests

- Status: PASS
- Generated: `2026-06-15T22:14:55+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the opt-in soak harness stays protected-stage, approval-gated, non-promoting, and artifact-safe

## Tests

- `hd_soak_harness_guard passes the current opt-in soak harness`
- `hd_soak_harness_guard rejects protected stage drift`
- `hd_soak_harness_guard rejects repository candidate defaults`
- `hd_soak_harness_guard rejects missing explicit approval text`
- `hd_soak_harness_guard rejects missing required report metrics`
- `hd_soak_harness_guard CLI writes JSON/Markdown and fails closed`
