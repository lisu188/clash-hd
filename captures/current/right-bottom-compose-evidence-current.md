# Right-Bottom Compose Evidence Matrix

- Overall: FAIL
- Generated: `2026-06-15T22:14:11+02:00`
- Runtime policy: repo-only; does not launch Clash95, CDB, wrappers, or visible windows
- Promotion status: `validation_stage_only`
- Stable stage should change: `False`
- Current stable stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Validation stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- Candidate SHA-256: `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`

## Required Checks

- `right_bottom_compose_patch`: `PASS`
- `right_bottom_compose_fullstart_route`: `PASS`
- `right_bottom_compose_normal_gate`: `PASS`
- `right_bottom_compose_ui_probe`: `FAIL`
- `right_bottom_grid_hit`: `PASS`
- `right_bottom_natural_route_guard`: `PASS`
- `right_bottom_route_timing_guard`: `PASS`
- `right_bottom_compose_promotion_decision`: `FAIL`

## Key Evidence

- Patch group: `{'patched': 4, 'total': 4}`
- Full-start route ready: `True`
- Full-start route AV count: `0`
- Bottom-right corner nonblack: `48.228`
- r8c10 nonblack: `54.102`
- r8c11 nonblack: `42.822`
- Normal map gate surface: `[800, 600]`
- Normal gate unexplained blanks: `0`
- Natural UI descriptor switch rows: `35`
- Natural UI owner/action rows: `RBUI_PANEL_DRAW=0`, `RBUI_ACTION_BOX=0`
- Controlled grid hit: `ok=True`, `entry=[450, 73]`, `result=0`
- Controlled grid forced gates/failure exits: `1` / `0`
- Natural route state-gated: `True`
- Natural route owner entry flag: `0x00`
- Natural route owner flag test: `{'owner_flag': '0x00', 'bit2': 0, 'bit1': 0, 'bit8': 0}`
- Natural route action descriptor: `{'slot': 'd1', 'x': 1000, 'y': 426, 'callback': '004338e0'}`
- Natural route descriptor result: `{'result': 0, 'owner': '041bc71a', 'owner_flag': '0x00', 'surface': [800, 600]}`
- Natural route owner/action rows / AV rows: `0` / `0`
- Route timing ordered markers: `patch=29`, `fullstart=29`, `grid=25`
- Route timing failure exits / AV rows: `0` / `0`
- Promotion decision: `defer_stable_promotion`

## Failures

- right_bottom_compose_ui_probe: right-bottom compose UI did not naturally enter owner/action draw rows
- right_bottom_compose_promotion_decision: right_bottom_compose_ui_probe: right-bottom compose UI did not naturally enter owner/action draw rows
- right_bottom_compose_promotion_decision: right-bottom natural UI probe did not enter owner/action draw rows
- natural UI probe did not enter owner/action draw rows
