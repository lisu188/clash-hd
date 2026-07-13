# HD Soak Short-Tier Ladder Tests

- Status: PASS
- Generated: `2026-07-12T21:36:14+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the short soak ladder is ordered, approval-gated, non-promoting, and keeps long/future lanes locked until prerequisite soak evidence exists

## Tests

- `hd_soak_short_tier_ladder passes as a repo-only plan while current short2 menu-idle is approval-gated and input-drift bounded`
- `hd_soak_short_tier_ladder advances to short2 map-idle after a passing short2 menu-idle fixture`
- `hd_soak_short_tier_ladder fails closed when a required harness route is missing`
- `hd_soak_short_tier_ladder catches a mismatched first-step next-action command`
- `hd_soak_short_tier_ladder CLI writes JSON/Markdown and respects --require-pass`
