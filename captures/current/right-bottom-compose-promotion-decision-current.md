# Right-Bottom Compose Promotion Decision

- Decision record: PASS
- Decision: `defer_stable_promotion`
- Stable stage should change: `False`
- Generated: `2026-07-17T12:35:24+02:00`
- Current stable stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Validation stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
- Candidate SHA-256: `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`
- Manual input proof: `None`
- Manual input proof supplied: `False`
- Manual input proof valid: `False`
- Manual input proof SHA-256: `None`
- Manual input proof checked items: `0`
- CDB-only promotion override: `False`
- Bare CDB-only promotion blocked: `False`
- Promotion override manifest: `None`
- Promotion override manifest supplied: `False`
- Promotion override manifest valid: `False`
- Promotion override scope: `None`
- Promotion override SHA-256: `None`

## Required Checks

- `right_bottom_compose_patch`: `PASS`
- `right_bottom_compose_fullstart_route`: `PASS`
- `right_bottom_compose_normal_gate`: `PASS`
- `right_bottom_compose_ui_probe`: `PASS`
- `right_bottom_grid_hit`: `PASS`
- `right_bottom_natural_route_guard`: `PASS`
- `right_bottom_route_timing_guard`: `PASS`

## Evidence Summary

- Patch group: `{'patched': 4, 'total': 4}`
- Current HD map gate: `True`
- Full-start route ready: `True`
- Full-start route AV count: `0`
- Normal map gate surface: `[800, 600]`
- Normal gate unexplained blanks: `0`
- Natural UI descriptor switch rows: `0`
- Natural UI owner/action rows: `RBUI_PANEL_DRAW=0`, `RBUI_ACTION_BOX=0`
- Natural draw source: `slot5_as_slot0_fixture`
- Fixture natural-draw accepted: `True`
- Fixture natural-draw evidence: `{'ruling': 'user ruling 2026-07-14: slot5-as-slot0 fixture accepted as natural-draw evidence', 'fixture_run': 'captures\\archive\\cdb-surface-dump-20260712-155528', 'log': 'captures\\archive\\cdb-surface-dump-20260712-155528\\cdb-surface-dump.log', 'result_summary_json': 'captures\\archive\\cdb-surface-dump-20260712-155528\\right-bottom-slot-fixture-result-summary.json', 'marker_counts': {'NOWNER_435BC0_PANEL_DRAW': 1, 'NOWNER_435BC0_GRID_DRAW': 10, 'NOWNER_WRAPPER_COPYBACK_DONE': 1, 'NOWNER_WRAPPER_PRESENT_CALL': 1}, 'av_count': 0, 'proof_class': 'non_natural_isolated_fixture', 'expected_slot_match': True, 'row_count': 272, 'stage': 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter', 'candidate_sha256': 'D3FF331FD6A7B10A91C55A55FF891685CFAC376917816557B40A483EBDBC569C'}`
- Controlled grid hit: `grid_hit_ok=True`, `entry=[450, 73]`, `result=0`
- Controlled grid hit AV count: `0`
- Natural route state-gated: `True`
- Natural route owner flag test: `{'owner_flag': '0x00', 'bit2': 0, 'bit1': 0, 'bit8': 0}`
- Natural route action descriptor: `{'slot': 'd1', 'x': 1000, 'y': 426, 'callback': '004338e0'}`
- Natural route owner/action rows / AV rows: `0` / `0`
- Route timing guard ordered markers: `patch=29`, `fullstart=29`, `grid=25`
- Route timing guard failure exits / AV rows: `0` / `0`
- Bottom-right corner nonblack: `48.228`
- r8c10 nonblack: `54.102`
- r8c11 nonblack: `42.822`

## Reasons

- right-bottom validation evidence gates are passing
- current proof is repo-only CDB/proxy evidence
- controlled native grid-hit proof is present
- route timing/order guard is present
- natural route owner-flag save-state proof is present
- natural route action descriptor is parked off-screen
- manual/visible DirectInput validation has not been supplied
- promotion override manifest has not been supplied
- natural draw evidence accepted from the slot5-as-slot0 fixture (user ruling 2026-07-14: slot5-as-slot0 fixture accepted as natural-draw evidence)
- visible/manual runs require explicit user approval

## Next Actions

- keep the patcher default stable HD map stage unchanged
- keep right-bottom composition hooks scoped to rightbottomcompose
- continue with repo-only or hidden-desktop/CDB route and input safety evidence
- request explicit approval before any visible/manual input validation
