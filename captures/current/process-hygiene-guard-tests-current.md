# Process Hygiene Guard Tests

- Status: PASS
- Generated: `2026-06-15T20:47:05+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the process hygiene guard rejects leftover cdb.exe/clash95* processes, snapshot failures, and CLI fail-closed cases

## Tests

- `process_hygiene_guard passes when no target process names are present`
- `process_hygiene_guard fails when exact cdb.exe or clash95* prefix matches are present`
- `process_hygiene_guard fails when the process snapshot API fails`
- `process_hygiene_guard target matching is case-insensitive`
- `process_hygiene_guard CLI writes JSON/Markdown and returns 2 on --require-pass failure`
