# HD Soak Failure Triage Tests

- Status: PASS
- Generated: `2026-06-15T22:14:55+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves soak failures are classified into approval, crash, render/palette, input-route, capture, artifact-budget, cleanup, or unclassified buckets with next probes

## Tests

- `hd_soak_failure_triage classifies pending visible-runtime approval separately from a game failure`
- `hd_soak_failure_triage classifies AV crashes from exit code 0xC0000005`
- `hd_soak_failure_triage classifies render/palette metric regressions`
- `hd_soak_failure_triage classifies route/input probe failures`
- `hd_soak_failure_triage classifies passing runs without failure`
- `hd_soak_failure_triage CLI writes JSON/Markdown and fails closed for failed reports`
