# HD Soak Dry-Run Plan Tests

- Status: PASS
- Generated: `2026-06-17T09:48:28+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the current short-soak dry-run handoff is machine-readable, non-executing, protected-stage, canonical-path, outside-repo, and fails closed unless copied execute commands include -RequirePass -Json with a fresh approval token, and the base executable exists with the expected SHA

## Tests

- `hd_soak_dry_run_plan accepts the current-step dry-run plan fixture`
- `hd_soak_dry_run_plan rejects executed plans`
- `hd_soak_dry_run_plan rejects protected-stage drift`
- `hd_soak_dry_run_plan rejects execute commands without -RequirePass or -Json`
- `hd_soak_dry_run_plan rejects visible-runtime execute commands without the approval token`
- `hd_soak_dry_run_plan rejects visible-runtime execute commands without the approval expiry`
- `hd_soak_dry_run_plan rejects visible-runtime approval packets that expire too soon`
- `hd_soak_dry_run_plan rejects execute commands missing explicit stage/input/workdir/output roots`
- `hd_soak_dry_run_plan rejects repository candidate output`
- `hd_soak_dry_run_plan rejects missing or unverified base executable input`
- `hd_soak_dry_run_plan CLI writes JSON/Markdown and respects --require-pass`
