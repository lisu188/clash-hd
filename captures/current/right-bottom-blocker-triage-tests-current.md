# Right-Bottom Blocker Triage Tests

- Status: PASS
- Generated: `2026-06-15T20:46:34+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves current right-bottom action-menu triage stays non-promoting, distinguishes controlled composition recovery from natural UI proof, and fails closed if the owner-flag/load-route blocker shape changes

## Tests

- `right_bottom_blocker_triage passes for the current controlled-recovered but natural-route-blocked shape`
- `right_bottom_blocker_triage fails if controlled composition no longer covers the lower/right UI`
- `right_bottom_blocker_triage fails if the owner-flag gate shape becomes obsolete`
- `right_bottom_blocker_triage fails if the isolated fixture plan becomes promoting`
- `right_bottom_blocker_triage CLI writes JSON/Markdown and honors --require-pass`
