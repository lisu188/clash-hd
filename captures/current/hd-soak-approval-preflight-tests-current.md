# HD Soak Approval Preflight Tests

- Status: PASS
- Generated: `2026-06-15T22:14:56+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the first short2 visible-runtime soak remains explicit-approval gated, pins canonical per-step report paths, keeps dry-runs non-executing, and requires clean harness/runtime/process/executable guards before requesting approval

## Tests

- `hd_soak_approval_preflight passes with a canonical first-step approval packet`
- `hd_soak_approval_preflight fails closed when runtime command approval flags or paths drift`
- `hd_soak_approval_preflight fails closed when dry-run command can execute`
- `hd_soak_approval_preflight catches next-actions and short-step command mismatches`
- `hd_soak_approval_preflight fails closed when the current short-step status is not pending`
- `hd_soak_approval_preflight fails closed when source guards are not passing`
- `hd_soak_approval_preflight CLI writes JSON/Markdown and respects --require-pass`
