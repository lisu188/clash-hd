# Castle Overview Promotion Decision Tests

- Status: PASS
- Generated: `2026-06-15T20:46:51+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for decision CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves the castle overview promotion decision defers stable promotion by default, fails when the evidence matrix fails or when focused displayed-wrapper / visible-dormant multi-hit completion proof is missing, only marks the stable stage as changeable when a valid manual proof manifest or an explicit CDB-only override is supplied, rejects placeholder proof files, and its CLI fails closed under --require-pass

## Tests

- `castle_overview_promotion_decision defers stable promotion by default`
- `castle_overview_promotion_decision fails closed when the evidence matrix fails`
- `castle_overview_promotion_decision fails closed when required focused/multihit proof is missing`
- `castle_overview_promotion_decision allows stable promotion with a valid manual input proof manifest`
- `castle_overview_promotion_decision rejects placeholder manual input proof files`
- `castle_overview_promotion_decision allows CDB-only promotion only with the explicit override flag`
- `castle_overview_promotion_decision CLI writes JSON/Markdown and returns 2 on --require-pass failure`
