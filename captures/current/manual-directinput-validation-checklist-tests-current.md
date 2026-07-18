# Manual DirectInput Checklist Tests

- Status: PASS
- Generated: `2026-07-18T10:42:35+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for checklist CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the manual DirectInput checklist enumerates the remaining manual targets, keeps promotion blocked without valid proof, validates manual proof manifests including isolated C:\ClashTests candidate path, stage, observation, no-crash, and process-hygiene records, records the no-popup operator preference, and fails closed for incomplete checklist data

## Tests

- `manual_directinput_checklist passes structurally while keeping promotion blocked`
- `manual_directinput_checklist records the no-popup operator preference`
- `manual_directinput_checklist fails when a required manual target is missing`
- `manual_directinput_checklist fails when a required checklist field is missing`
- `manual_directinput_checklist marks promotion ready only when a valid proof manifest is supplied`
- `manual_directinput_checklist rejects placeholder manual proof files`
- `manual_directinput_checklist rejects proof manifests missing observation, no-crash, or process hygiene records`
- `manual_directinput_checklist rejects live-original or repository-local candidate paths`
- `manual_directinput_checklist marks promotion ready when an explicit CDB-only override is supplied`
- `manual_directinput_checklist CLI writes JSON/Markdown and fails --require-promotion-ready without proof`
