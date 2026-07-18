# Right-Bottom Compose Evidence Matrix Tests

- Status: PASS
- Generated: `2026-07-18T21:36:00+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for matrix CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the right-bottom compose evidence matrix requires all route gates, hidden-desktop/full-start safety, normal map/visibility proof, natural UI routing, controlled grid-hit proof, route timing/order proof, candidate SHA agreement, and deferred promotion status

## Tests

- `right_bottom_compose_evidence_matrix passes when all required route, map, UI, grid-hit, natural-route, timing, and decision checks pass`
- `right_bottom_compose_evidence_matrix fails when any required check is missing or failing`
- `right_bottom_compose_evidence_matrix rejects route, startup, hidden-desktop, AV, visibility, grid-hit, natural-route, timing, and decision regressions`
- `right_bottom_compose_evidence_matrix rejects nested natural-route owner flag, descriptor, and result regressions`
- `right_bottom_compose_evidence_matrix accepts the slot5-as-slot0 fixture natural-draw payload while still deferring promotion`
- `right_bottom_compose_evidence_matrix fails closed when the fixture natural-draw payload is missing or regresses`
- `right_bottom_compose_evidence_matrix rejects candidate SHA disagreement`
- `right_bottom_compose_evidence_matrix CLI writes JSON/Markdown and returns 2 on --require-pass failure`
