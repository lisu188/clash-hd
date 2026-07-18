# Right-Bottom Compose Evidence Matrix

- Overall: PASS
- Generated: `2026-07-18T10:41:44+02:00`
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
- `right_bottom_compose_ui_probe`: `PASS`
- `right_bottom_grid_hit`: `PASS`
- `right_bottom_natural_route_guard`: `PASS`
- `right_bottom_route_timing_guard`: `PASS`
- `right_bottom_compose_promotion_decision`: `PASS`

## Key Evidence

- Patch group: `{'patched': 4, 'total': 4}`
- Full-start route ready: `True`
- Full-start route AV count: `0`
- Bottom-right corner nonblack: `48.228`
- r8c10 nonblack: `54.102`
- r8c11 nonblack: `42.822`
- Normal map gate surface: `[800, 600]`
- Normal gate unexplained blanks: `0`
- Natural UI descriptor switch rows: `0`
- Natural UI owner/action rows: `RBUI_PANEL_DRAW=0`, `RBUI_ACTION_BOX=0`
- Natural draw source: `slot5_as_slot0_fixture`
- Fixture natural-draw evidence: `{'ruling': 'user ruling 2026-07-14: slot5-as-slot0 fixture accepted as natural-draw evidence', 'fixture_run': 'captures\\archive\\cdb-surface-dump-20260712-155528', 'marker_counts': {'NOWNER_435BC0_PANEL_DRAW': 1, 'NOWNER_435BC0_GRID_DRAW': 10, 'NOWNER_WRAPPER_COPYBACK_DONE': 1, 'NOWNER_WRAPPER_PRESENT_CALL': 1}, 'av_count': 0, 'proof_class': 'non_natural_isolated_fixture', 'expected_slot_match': True}`
- Controlled grid hit: `ok=True`, `entry=[450, 73]`, `result=0`
- Controlled grid forced gates/failure exits: `1` / `0`
- Natural route state-gated: `True`
- Natural route owner entry flag: `0x00`
- Natural route owner flag test: `{'owner_flag': '0x00', 'bit2': 0, 'bit1': 0, 'bit8': 0}`
- Natural route action descriptor: `{'slot': 'd1', 'x': 1000, 'y': 426, 'callback': '004338e0'}`
- Natural route descriptor result: `{'result': 0, 'owner': '044fc71a', 'owner_flag': '0x00', 'surface': [800, 600]}`
- Natural route owner/action rows / AV rows: `0` / `0`
- Route timing ordered markers: `patch=29`, `fullstart=29`, `grid=25`
- Route timing failure exits / AV rows: `0` / `0`
- Promotion decision: `defer_stable_promotion`
