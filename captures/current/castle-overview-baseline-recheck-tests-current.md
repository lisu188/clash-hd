# Castle Overview Baseline Recheck Tests

- Status: PASS
- Generated: `2026-06-17T09:48:06+02:00`
- Runtime policy: repo-only in-process fixture tests; does not launch Clash95, CDB, wrappers, PowerShell, Python child processes, or visible windows
- Guard policy: proves the castle overview baseline recheck rejects stale overview visual baselines, stale barracks controlled-stop baselines, and failing latest castle overview matrices, including matrices without visible/dormant target-done completion proof

## Tests

- `castle_overview_baseline_recheck passes with overview, barracks, and latest matrix inputs passing`
- `castle_overview_baseline_recheck fails when the overview visual baseline fails`
- `castle_overview_baseline_recheck fails when the barracks controlled-stop baseline fails`
- `castle_overview_baseline_recheck fails when the latest castle overview matrix fails`
- `castle_overview_baseline_recheck fails when latest matrix target-done completion proof is missing`
- `castle_overview_baseline_recheck writes JSON and Markdown outputs`
