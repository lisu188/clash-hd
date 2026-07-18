# Castle Overview Multihit Summary Tests

- Status: PASS
- Generated: `2026-07-18T10:18:02+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for parser CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the castle overview multi-hit parser recognizes expected target rows, hit-test results, descriptor, click-gate, target-done rows, ready size, callback entry, AV rows, and fails closed under required CLI flags

## Tests

- `castle_overview_multihit_summary parses target-set, hit-test, descriptor, click-gate, target-done, ready-size, callback, and AV rows`
- `castle_overview_multihit_summary CLI writes JSON/Markdown and passes all required flags on a good multi-hit log`
- `castle_overview_multihit_summary CLI returns 2 for missing readiness, wrong size, raw/descriptor/gate/completion mismatch, callback entry, and AV rows`
