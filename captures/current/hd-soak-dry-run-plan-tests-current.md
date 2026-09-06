# HD Soak Dry-Run Plan Tests

- Status: PASS
- Generated: `2026-09-06T05:58:02+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the current short-soak dry-run handoff is machine-readable, non-executing, protected-stage, canonical-path, outside-repo, and fails closed unless copied execute commands include -RequirePass -Json with a fresh approval token, and the base executable exists with the expected SHA

## Tests

- `hd_soak_dry_run_plan: valid plan passes`
- `hd_soak_dry_run_plan: rejects executed plan`
- `hd_soak_dry_run_plan: rejects stage drift`
- `hd_soak_dry_run_plan: rejects execute command without require pass or json`
- `hd_soak_dry_run_plan: rejects missing visible runtime token`
- `hd_soak_dry_run_plan: rejects missing visible runtime expiry`
- `hd_soak_dry_run_plan: rejects nearly expired visible runtime approval`
- `hd_soak_dry_run_plan: rejects missing intro skip plan fields`
- `hd_soak_dry_run_plan: rejects execute command without explicit stage or io roots`
- `hd_soak_dry_run_plan: rejects repo candidate path`
- `hd_soak_dry_run_plan: rejects missing or unverified base input`
- `hd_soak_dry_run_plan: cli writes outputs`
- `hd_soak_dry_run_plan: hidden plan uses real schema and preserves no input boundary`
- `hd_soak_dry_run_plan: hidden plan rejects provenance and command drift`
- `hd_soak_dry_run_plan: hidden default invokes only hidden dry run`
- `hd_soak_dry_run_plan: unknown environment never invokes a harness`
- `hd_soak_dry_run_plan: hidden plan rejects an arbitrary existing interpreter`
- `hd_soak_dry_run_plan: completed ladder never invokes a harness or reads a plan`
- `hd_soak_dry_run_plan: invalid completion never falls back to runtime planning`
- `hd_soak_dry_run_plan: completed ladder cli writes only terminal packet`
