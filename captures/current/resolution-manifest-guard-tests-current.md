# Resolution Manifest Guard Tests

- Status: PASS
- Generated: `2026-07-12T20:03:49+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the resolution status manifest guard fails closed on drift

## Tests

- `resolution_manifest_guard passes on a consistent manifest`
- `resolution_manifest_guard fails on missing/duplicate stable defaults`
- `resolution_manifest_guard fails on stable-stage or tile-formula drift`
- `resolution_manifest_guard fails on missing or visible evidence runs`
- `resolution_manifest_guard fails on failing smoke matrices and bad bounds`
- `resolution_manifest_guard CLI writes outputs and fails closed under --require-pass`
