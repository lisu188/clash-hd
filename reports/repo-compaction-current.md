# Repo Compaction Cleanup

- Overall: PASS
- Generated: `2026-06-15T18:36:20+02:00`
- Executed: `True`
- Runtime policy: repo-only dry-run by default; execute mode moves stale generated captures to the requested archive root and deletes only ignored cache directories; does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
- Guard policy: archive/delete candidates must be untracked, unmodified, inside approved generated-output areas, outside raw/.git, and must not include current or preserved HD evidence
- Archive root: `C:\ClashCaptures\repo-compaction-20260615-183619`
- Modified files: `287`
- Untracked paths: `2336`
- Archive candidates: `0`
- Archive candidate size: `0.00 MB`
- Delete candidates: `4`
- Delete candidate size: `2.24 MB`
- Moved files: `0`
- Archive-root manifest files: `0`
- Deleted paths: `2`

## Preserved Proof Entries

- `captures/cdb-surface-dump-20260429-111340`
- `captures/cdb-surface-dump-20260506-190037`
- `captures/cdb-surface-dump-20260506-201114`
- `captures/cdb-surface-dump-20260515-105041`
- `captures/cdb-surface-dump-20260515-105411`
- `captures/cdb-surface-dump-20260515-105458`
- `captures/cdb-surface-dump-20260515-105557`
- `captures/cdb-surface-dump-20260615-100407`

## Archive Candidates

- None

## Delete Candidates

- `__pycache__` (0.00 MB, ignored cache directory __pycache__)
- `captures/tmp-tests-probe` (0.00 MB, ignored temporary test directory)
- `src/patcher/__pycache__` (0.07 MB, ignored cache directory __pycache__)
- `tools/__pycache__` (2.17 MB, ignored cache directory __pycache__)

## Warnings

- delete skipped for __pycache__: [WinError 5] Access is denied: 'C:\\Users\\andrz\\OneDrive\\Pulpit\\git\\clash-hd\\__pycache__'
- delete skipped for captures/tmp-tests-probe: [WinError 5] Access is denied: 'C:\\Users\\andrz\\OneDrive\\Pulpit\\git\\clash-hd\\captures\\tmp-tests-probe\\child'

## Deleted Paths

- `src/patcher/__pycache__` (ignored cache directory __pycache__)
- `tools/__pycache__` (ignored cache directory __pycache__)
