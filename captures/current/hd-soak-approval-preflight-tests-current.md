# HD Soak Approval Preflight Tests

- Status: PASS
- Generated: `2026-09-06T05:58:13+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the first short2 visible-runtime soak remains explicit-approval gated, pins canonical per-step report paths, keeps dry-runs non-executing, can advance to later short steps, starts focused post-run validation with the failure-safe guard/triage refresh, keeps broad evidence refresh separate, requires next-action artifact inventory to match the preflight state, requires the actual harness dry-run plan and embedded next-action summary to match, requires visible-runtime approval TTL and limit summaries, requires verified base-executable input, and requires clean harness/runtime/process/executable guards before requesting approval

## Tests

- `hd_soak_approval_preflight: hidden preflight uses emitted plan without visible approval`
- `hd_soak_approval_preflight: hidden preflight rejects unbound or visible packets`
- `hd_soak_approval_preflight: current preflight passes with generated reports`
- `hd_soak_approval_preflight: current preflight records current step artifact inventory`
- `hd_soak_approval_preflight: runtime command requires visible runtime and canonical paths`
- `hd_soak_approval_preflight: dry run must not execute`
- `hd_soak_approval_preflight: step status command must match next actions`
- `hd_soak_approval_preflight: next actions dry run must match step status`
- `hd_soak_approval_preflight: next actions post run validation must match step status`
- `hd_soak_approval_preflight: next actions post run handoff refresh must match step status`
- `hd_soak_approval_preflight: next actions post run evidence refresh must match preflight`
- `hd_soak_approval_preflight: next actions artifact inventory must match preflight`
- `hd_soak_approval_preflight: next actions plan verified command must match dry run plan`
- `hd_soak_approval_preflight: next actions dry run plan summary must match current dry run plan`
- `hd_soak_approval_preflight: step status must be pending first step`
- `hd_soak_approval_preflight: intro skip rerun preflight passes with readiness gate`
- `hd_soak_approval_preflight: input environment rerun preflight requires fresh approval`
- `hd_soak_approval_preflight: application hang rerun preflight requires window health stop`
- `hd_soak_approval_preflight: next actions current failure must match preflight`
- `hd_soak_approval_preflight: guard source must pass`
- `hd_soak_approval_preflight: dry run plan source must pass`
- `hd_soak_approval_preflight: stale dry run plan fails closed`
- `hd_soak_approval_preflight: nearly expired approval fails closed`
- `hd_soak_approval_preflight: dry run plan must match current step and paths`
- `hd_soak_approval_preflight: dry run plan must confirm base input`
- `hd_soak_approval_preflight: dry run plan execute command must pin stage and roots`
- `hd_soak_approval_preflight: dry run plan must pin visible runtime token`
- `hd_soak_approval_preflight: dry run plan must pin visible runtime expiry`
- `hd_soak_approval_preflight: dry run plan must pin intro skip contract`
- `hd_soak_approval_preflight: dry run plan must pin windowed contract`
- `hd_soak_approval_preflight: later short step preflight uses step status without first next action`
- `hd_soak_approval_preflight: cli writes outputs`
- `hd_soak_approval_preflight: completed ladder produces no approval or runtime request`
- `hd_soak_approval_preflight: invalid completion cannot bypass approval preflight`
