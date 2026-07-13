# HD Soak Short Validation Refresh Tests

- Status: PASS
- Generated: `2026-07-13T08:55:01+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves canonical short soak reports are automatically guarded and triaged before step-status evaluation, while missing reports remain a safe pending repo-only state

## Tests

- `hd_soak_short_validation_refresh passes as pending when no canonical reports exist`
- `hd_soak_short_validation_refresh writes guard and triage artifacts for passing canonical reports`
- `hd_soak_short_validation_refresh writes failed guard and classified triage for failed canonical reports`
- `hd_soak_short_validation_refresh fails closed when a canonical report mismatches its step`
- `hd_soak_short_validation_refresh fails closed when the manifest is missing`
- `hd_soak_short_validation_refresh CLI writes JSON/Markdown and respects --require-pass`
