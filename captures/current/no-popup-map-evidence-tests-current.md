# No-Popup Map Evidence Matrix Tests

- Status: PASS
- Generated: `2026-07-12T20:47:04+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for matrix CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the no-popup map evidence matrix requires a visibility-explained normal run, a forced-visible edge proof, latest-run selection, and CLI fail-closed behavior

## Tests

- `no_popup_map_evidence_matrix passes with explicit normal and forced-visible runs`
- `no_popup_map_evidence_matrix scans and selects the latest passing normal and forced-visible runs`
- `no_popup_map_evidence_matrix rejects normal visibility-gate regressions`
- `no_popup_map_evidence_matrix rejects forced-visible gate regressions`
- `no_popup_map_evidence_matrix CLI writes JSON/Markdown and returns 2 on --require-pass failure`
