# HD Soak Short-Step Status Tests

- Status: PASS
- Generated: `2026-07-12T20:04:01+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves per-step soak status stays repo-only, advances only after guarded passing output, rejects stale guard/triage artifacts that do not match the canonical report, and demands triage for failed canonical runtime reports

## Tests

- `hd_soak_short_step_status passes for the current pending approval state`
- `hd_soak_short_step_status advances after a guarded passing first-step fixture`
- `hd_soak_short_step_status fails closed when a canonical report lacks guard output`
- `hd_soak_short_step_status fails closed when guard output is stale or mismatched`
- `hd_soak_short_step_status accepts classified failed reports with triage output`
- `hd_soak_short_step_status fails closed when triage output is stale or mismatched`
- `hd_soak_short_step_status CLI writes JSON/Markdown and respects --require-pass`
