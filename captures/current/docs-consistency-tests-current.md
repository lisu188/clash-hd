# Docs Consistency Guard Tests

- Status: PASS
- Generated: `2026-06-15T18:35:00+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves current docs fail closed when generated counts or promotion-boundary facts go stale

## Tests

- `docs_consistency_guard passes current fact fixtures`
- `docs_consistency_guard fails stale boundary counts`
- `docs_consistency_guard fails missing manual target IDs`
- `docs_consistency_guard CLI writes outputs and fails closed`
