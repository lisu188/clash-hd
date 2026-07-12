# HD Soak Harness Guard Tests

- Status: PASS
- Generated: `2026-07-12T20:35:04+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the opt-in soak harness stays protected-stage, approval-gated, non-promoting, artifact-safe, and preserves full render-range plus sample-interval, route/process/frame/capture inventory metrics

## Tests

- `hd_soak_harness_guard passes the current opt-in soak harness`
- `hd_soak_harness_guard rejects protected stage drift`
- `hd_soak_harness_guard rejects repository candidate defaults`
- `hd_soak_harness_guard rejects missing explicit approval text`
- `hd_soak_harness_guard rejects dry-run execute commands without -RequirePass semantics`
- `hd_soak_harness_guard rejects dry-run execute commands without JSON output`
- `hd_soak_harness_guard rejects missing visible-runtime approval token or expiry boundaries`
- `hd_soak_harness_guard rejects missing visible-runtime approval minimum TTL boundary`
- `hd_soak_harness_guard rejects runtime side effects before approval guards`
- `hd_soak_harness_guard rejects missing required report metrics`
- `hd_soak_harness_guard rejects missing sample-interval, render-range, or raw inventory metrics`
- `hd_soak_harness_guard CLI writes JSON/Markdown and fails closed`
