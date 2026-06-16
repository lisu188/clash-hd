# Process Hygiene Guard

- Overall: PASS
- Generated: `2026-06-16T18:11:53+02:00`
- Runtime policy: local process inspection only; does not launch Clash95, CDB, wrappers, or visible windows
- Guard policy: no cdb.exe or clash95*.exe process may be running after evidence refresh
- Inspection source: `CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS)`
- Matching runtime processes: `0`

## Matching Processes

- None
