# Right-Bottom Owner-Flag Static Guard Tests

- Status: PASS
- Generated: `2026-07-12T20:03:35+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the static owner-flag guard fails closed on executable SHA drift, 004338E0 gate drift, and missing local executable evidence

## Tests

- `right_bottom_owner_flag_static_guard accepts the expected command-99, owner-global, action-gate, and owner-loop byte patterns`
- `right_bottom_owner_flag_static_guard rejects byte drift in the 004338E0 bit-2 early-return gate`
- `right_bottom_owner_flag_static_guard rejects original executable SHA drift`
- `right_bottom_owner_flag_static_guard CLI writes JSON/Markdown and fails closed under --require-pass`
