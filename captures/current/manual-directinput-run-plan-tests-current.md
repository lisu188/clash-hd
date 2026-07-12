# Manual DirectInput Run Plan Tests

- Status: PASS
- Generated: `2026-07-12T19:23:34+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the manual DirectInput run plan remains repo-only, keeps visible commands approval-gated with -AllowVisibleRuntime, keeps candidate placeholders under C:\ClashTests, and cannot substitute for a valid manual proof manifest

## Tests

- `manual_directinput_run_plan passes but does not claim proof or promotion readiness`
- `manual_directinput_run_plan emits one approval-gated command per required manual target`
- `manual_directinput_run_plan fails when a required checklist item is missing`
- `manual_directinput_run_plan fails when a visible command source lacks AllowVisibleRuntime`
- `manual_directinput_run_plan fails when a candidate placeholder is not under C:\ClashTests`
- `manual_directinput_run_plan CLI writes JSON and Markdown outputs`
