# Manual DirectInput Proof Template Tests

- Status: PASS
- Generated: `2026-06-16T18:05:25+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for template CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the manual DirectInput proof template documents the proof shape, pins candidate placeholders under C:\ClashTests, stays invalid until placeholders are replaced, and can become valid only after all required manual proof fields are supplied

## Tests

- `manual_directinput_proof_template remains invalid as proof until placeholders are replaced`
- `manual_directinput_proof_template pins candidate placeholders under C:\ClashTests`
- `manual_directinput_proof_template reports every required manual target id`
- `manual_directinput_proof_template can become valid after all proof fields are replaced`
- `manual_directinput_proof_template CLI writes template JSON, report JSON, and Markdown`
