# Castle Overview Hitbox Summary Tests

- Status: PASS
- Generated: `2026-06-16T18:04:58+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for parser CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the focused castle overview hitbox parser recognizes displayed/native hit rows, descriptor and click-gate rows, callback suppression, ready size, callback entry, AV rows, and fails closed under required CLI flags

## Tests

- `castle_overview_hitbox_summary parses displayed/native hits, descriptor, click gate, callback suppression, ready size, and AV count`
- `castle_overview_hitbox_summary CLI writes JSON/Markdown and passes all required flags on a good focused log`
- `castle_overview_hitbox_summary CLI returns 2 for missing readiness, wrong size, missing displayed/native hit, descriptor, click gate, suppression, callback entry, and AV rows`
