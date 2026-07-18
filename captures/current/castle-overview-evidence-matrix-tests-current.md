# Castle Overview Evidence Matrix Tests

- Status: PASS
- Generated: `2026-07-18T21:30:25+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for matrix CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the castle overview evidence matrix aggregates every required component gate, fails when any required gate fails, accepts archived patch-stage reports when live candidate executables are absent, requires displayed-wrapper proof in the focused hitbox gate, reports target-done completion proof in multi-hit gates, preserves validation-stage-only status, and its CLI fails closed under --require-pass

## Tests

- `castle_overview_evidence_matrix passes when every component gate passes`
- `castle_overview_evidence_matrix fails when each required component gate fails`
- `castle_overview_evidence_matrix accepts an archived patch-stage report when the live candidate is absent`
- `castle_overview_evidence_matrix focused hitbox gate requires displayed-wrapper proof`
- `castle_overview_evidence_matrix multihit gates report target-done completion proof`
- `castle_overview_evidence_matrix CLI writes JSON/Markdown and returns 2 on --require-pass failure`
