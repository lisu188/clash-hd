# HD Soak Failure Triage Tests

- Status: PASS
- Generated: `2026-07-17T15:36:58+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves soak failures are classified into approval, crash, render/palette, input-route, frame-progression, process-growth, capture, artifact-budget, insufficient-sample hang, elapsed-coverage, cleanup, or unclassified buckets with next probes

## Tests

- `hd_soak_failure_triage classifies pending visible-runtime approval separately from a game failure`
- `hd_soak_failure_triage classifies AV crashes from exit code 0xC0000005`
- `hd_soak_failure_triage classifies unexpected non-AV process exits`
- `hd_soak_failure_triage enriches missing route click mode from per-route probe JSON`
- `hd_soak_failure_triage classifies render/palette metric regressions`
- `hd_soak_failure_triage records visual anomaly summary counts`
- `hd_soak_failure_triage classifies route/input probe failures`
- `hd_soak_failure_triage classifies route/input drift failures`
- `hd_soak_failure_triage classifies frame progression failures`
- `hd_soak_failure_triage classifies process growth regressions`
- `hd_soak_failure_triage classifies artifact budget failures`
- `hd_soak_failure_triage classifies insufficient frame/process samples as hang/no-frame progress`
- `hd_soak_failure_triage classifies process cleanup failures`
- `hd_soak_failure_triage classifies passing runs without failure`
- `hd_soak_failure_triage rejects raw-passing runs when hd_soak_report guard validation fails`
- `hd_soak_failure_triage classifies raw-passing elapsed-coverage guard failures`
- `hd_soak_failure_triage CLI writes JSON/Markdown and fails closed for failed reports`
