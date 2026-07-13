# Process Hygiene Guard

- Overall: PASS
- Generated: `2026-07-12T21:35:58+02:00`
- Runtime policy: local process inspection only; does not launch Clash95, CDB, wrappers, or visible windows
- Guard policy: no cdb.exe or clash95*.exe process may be running after evidence refresh
- Inspection source: `CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS)`
- Matching runtime processes: `0`

## Matching Processes

- None
