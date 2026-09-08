# Hidden-CDB Soak Report Assembler Tests

- Status: PASS
- Generated: `2026-09-06T05:57:57+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves hidden-CDB reports are a distinct fail-closed evidence class with anchored runtime markers, real host process and ReadProcessMemory telemetry, a non-presenting memory proxy, explicit forced-entry disclosure, and input_responsiveness=not_applicable_hidden

## Tests

- `hidden soak startup prose cannot satisfy anchored runtime markers`
- `hidden soak samples require the exact environment and input sentinel`
- `hidden soak assembler output passes the shared environment-aware guard`
- `hidden map-pan evidence requires ordered forced-scroll rows and frame progression`
- `hidden reports retain host process, proxy, cleanup, patch, and surface-read provenance`
- `hidden runner remains dry-run-only until explicit execution opt-in`
