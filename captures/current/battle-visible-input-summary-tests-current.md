# Battle Visible Input Summary Tests

- Status: PASS
- Generated: `2026-07-12T19:43:25+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for parser CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves visible-input evidence cannot be promoted from command readiness to pass until a real visible click is consumed by the battle command callback

## Tests

- `visible input summary keeps command-ready runs partial until a real click reaches the callback`
- `visible input summary requires both visible input JSON and callback/click-gate evidence for click consumption`
- `visible input summary rejects invalid CDB breakpoint and post-g break-instruction failures`
- `visible input summary CLI writes JSON/Markdown current artifacts`
- `visible input summary aggregate pass requires at least one consumed-click run`
