# No-Popup Guard Regression Tests

- Status: PASS
- Generated: `2026-07-12T21:11:17+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for guard CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the no-popup boundary guard and surface-dump launcher policy guard reject missing evidence links, missing/failing refresh checks, missing supporting reports, and ungated visible fallback while keeping negative CLI outputs out of current reports

## Tests

- `no_popup_boundary_guard passes with all boundary reports linked`
- `no_popup_boundary_guard fails when each evidence-index report link is missing`
- `no_popup_boundary_guard fails when a required refresh check is missing`
- `no_popup_boundary_guard fails when each required supporting refresh check is missing`
- `no_popup_boundary_guard fails when a required refresh check is failing`
- `surface_dump_policy_guard passes the expected hidden-desktop launcher shape`
- `surface_dump_policy_guard fails when visible fallback is not explicitly gated`
- `surface_dump_policy_guard failing CLI writes fixture outputs instead of current report paths`
