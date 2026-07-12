# Process Hygiene Guard

- Overall: FAIL
- Generated: `2026-07-12T19:43:28+02:00`
- Runtime policy: local process inspection only; does not launch Clash95, CDB, wrappers, or visible windows
- Guard policy: no cdb.exe or clash95*.exe process may be running after evidence refresh
- Inspection source: `CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS)`
- Matching runtime processes: `2`

## Matching Processes

- `cdb.exe` pid=`16436` parent=`32976` session=`1`
- `clash95_hd_surfdump_20260712_193922.exe` pid=`33668` parent=`16436` session=`1`

## Failures

- runtime processes still running: cdb.exe pid=16436, clash95_hd_surfdump_20260712_193922.exe pid=33668
