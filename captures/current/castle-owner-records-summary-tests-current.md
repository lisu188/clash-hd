# Castle Owner Records Summary Tests

- Status: PASS
- Generated: `2026-07-12T20:47:34+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for parser CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the castle owner-record parser recognizes active, retired, nonempty, interesting, and flag-value records, and fails closed for no-active, require-interesting, forbid-interesting, and truncated raw-dump cases

## Tests

- `castle_owner_records_summary classifies active, retired, nonempty, interesting, and flag-value records`
- `castle_owner_records_summary CLI writes JSON/Markdown and passes require-active plus forbid-interesting on a current-style raw dump`
- `castle_owner_records_summary fails closed for no active records, missing interesting records, forbidden interesting records, and truncated raw dumps`
