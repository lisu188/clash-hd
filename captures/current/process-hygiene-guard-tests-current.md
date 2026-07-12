# Process Hygiene Guard Tests

- Status: FAIL
- Generated: `2026-07-12T20:34:53+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the process hygiene guard rejects leftover cdb.exe/clash95* processes, snapshot failures, and CLI fail-closed cases

## Tests

- `process_hygiene_guard passes when no target process names are present`
- `process_hygiene_guard fails when exact cdb.exe or clash95* prefix matches are present`
- `process_hygiene_guard fails when the process snapshot API fails`
- `process_hygiene_guard target matching is case-insensitive`
- `process_hygiene_guard CLI writes JSON/Markdown and returns 2 on --require-pass failure`

## Failures

- AssertionError: overall: FAIL
runtime-policy: local process inspection only; does not launch Clash95, CDB, wrappers, or visible windows
guard-policy: no cdb.exe or clash95*.exe process may be running after evidence refresh
matching-process-count: 1
failures:
  - runtime processes still running: clash95_hd_castle_manual_20260712.exe pid=7832

