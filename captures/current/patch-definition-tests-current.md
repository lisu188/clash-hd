# Patch Definition Guard Tests

- Status: PASS
- Generated: `2026-07-18T21:30:35+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves patch/stage definitions fail closed on drift, leakage, unknown groups, or incompatible offset overlaps

## Tests

- `patch_definition_guard passes a scoped fixture`
- `patch_definition_guard fails on default drift`
- `patch_definition_guard fails on validation leakage`
- `patch_definition_guard fails on unknown groups`
- `patch_definition_guard fails on overlapping incompatible bytes`
- `patch_definition_guard CLI writes current outputs`
