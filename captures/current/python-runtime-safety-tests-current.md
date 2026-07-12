# Python Runtime Safety Guard Tests

- Status: PASS
- Generated: `2026-07-12T19:23:21+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves risky Python runtime/window/input helpers are gated, exempt, or fail closed

## Tests

- `python_runtime_safety_guard rejects unclassified risky helpers`
- `python_runtime_safety_guard allows gated/exempt helpers and test fixtures`
- `python_runtime_safety_guard CLI writes outputs and fails closed under --require-pass`
