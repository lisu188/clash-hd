# Right-Bottom Visual Artifact Guard

- Overall: FAIL
- Generated: `2026-07-12T16:08:35+02:00`
- Runtime policy: repo-only visual artifact guard; reads generated JSON reports and does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: passes only while the current natural right-bottom visual artifact remains explicitly blocked from promotion: controlled composition is recovered, natural owner/action rows are absent, and the lower/right natural regions still show the known black/striped incomplete state
- Visual status: `visual_artifact_guard_stale`
- Promotion ready: `False`
- stable_stage_should_change: `False`
- Conclusion: The striped/out-of-place right-bottom action-menu view is still a blocked natural UI artifact, not stable evidence. Controlled composition proves the lower/right UI can be drawn, but natural gameplay has not entered the owner/action draw path.

## Checks

- `controlled_composition_recovered`: `PASS`
- `natural_owner_action_rows_absent`: `FAIL`
- `natural_visual_artifact_present`: `PASS`
- `controlled_vs_natural_visual_gap`: `PASS`
- `blocker_triage_non_promoting`: `PASS`
- `compose_matrix_non_promoting`: `PASS`

## Observations

- Controlled lower/right nonblack: corner `48.228`, r8c10 `54.102`, r8c11 `42.822`
- Natural owner/action rows: `0`
- Natural black percentages: corner `78.57`, r8c10 `100.0`, r8c11 `100.0`
- Natural corner flags: `['large_black_component', 'black_touches_bottom_right']`
- Natural r8c10 flags: `['mostly_black', 'large_black_component', 'black_touches_bottom_right']`
- Natural r8c11 flags: `['mostly_black', 'large_black_component', 'black_touches_bottom_right']`
- Triage classification: `controlled_recovered_but_natural_route_nonpromoting`

## Failures

- visual artifact guard failed: natural_owner_action_rows_absent
