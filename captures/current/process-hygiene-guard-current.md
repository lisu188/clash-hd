# Process Hygiene Guard

- Overall: FAIL
- Generated: `2026-07-12T20:34:53+02:00`
- Runtime policy: local process inspection only; does not launch Clash95, CDB, wrappers, or visible windows
- Guard policy: no cdb.exe or clash95*.exe process may be running after evidence refresh
- Inspection source: `CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS)`
- Matching runtime processes: `1`

## Matching Processes

- `clash95_hd_castle_manual_20260712.exe` pid=`7832` parent=`37392` session=`1`

## Failures

- runtime processes still running: clash95_hd_castle_manual_20260712.exe pid=7832
