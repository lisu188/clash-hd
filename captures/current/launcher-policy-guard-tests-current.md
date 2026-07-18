# Launcher Policy Guard Tests

- Status: PASS
- Generated: `2026-07-18T21:36:31+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the launcher policy guard fails closed on every policy regression

## Tests

- `launcher_policy_guard passes on a compliant launcher tree`
- `launcher_policy_guard fails on a missing confirmed=True gate`
- `launcher_policy_guard fails on missing candidates-root write refusals`
- `launcher_policy_guard fails on launch call sites outside core/gui/entry`
- `launcher_policy_guard fails when the refresh references the launcher`
- `launcher_policy_guard fails on risky launcher PowerShell calls`
- `launcher_policy_guard fails on missing policy doc phrases`
- `launcher_policy_guard CLI writes outputs and fails closed under --require-pass`
