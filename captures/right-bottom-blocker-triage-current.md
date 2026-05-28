# Right-Bottom Blocker Triage

- Overall: PASS
- Generated: `2026-05-28T10:21:56+02:00`
- Runtime policy: repo-only evidence triage; reads generated JSON reports and does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: passes only while the current blocker is explicitly classified as non-promoting: controlled composition is recovered, natural owner/action rows are absent, the natural route is either owner-flag gated or blocked inside the slot5 Render_Begin/DD_Pump/copyback lane, and the next proof path remains hidden diagnosis or approved manual input
- Classification: `controlled_recovered_but_natural_route_blocked`
- Promotion ready: `False`
- stable_stage_should_change: `False`
- Conclusion: The right-bottom action/menu surface is not stable-promotable yet. Controlled composition recovers the lower/right UI, but natural owner/action copyback remains absent. The current slot 5 natural route reaches owner bit 0x02, 004338E0, Render_Begin exit, and owner/action draw entry, then stops before wrapper copyback.

## Checks

- `controlled_composition_recovered`: `PASS`
- `natural_ui_owner_action_rows_absent`: `PASS`
- `natural_route_blocker_documented`: `PASS`
- `hidden_fixture_plan_ready`: `PASS`
- `manual_plan_waiting_for_approval`: `PASS`
- `promotion_deferred`: `PASS`

## Observations

- Controlled bottom-right corner nonblack: `48.228`
- Controlled r8c10/r8c11 nonblack: `54.102` / `42.822`
- Natural UI owner/action rows: `0`
- Natural route owner flag test: `{'owner_flag': '0x00', 'bit2': 0, 'bit1': 0, 'bit8': 0}`
- Natural route action descriptor: `{'slot': 'd1', 'x': 1000, 'y': 426, 'callback': '004338e0'}`
- Natural slot5 status: `owner_action_draw_reached`
- Natural slot5 Render_Begin stalled: `False`
- Natural slot5 DD_Pump wait stalled: `False`
- Natural slot5 Render_Begin late-armed count: `1`
- Natural slot5 last flip result: `{'iter': 1, 'eax': 0, 'render': 5524696, 'callback': 0, 'd544d10': 1, 'd544d04': 0, 'button0': 0, 'raw': [11520, 28160], 'd543d78': 1, 'd543d7c': 5}`
- Natural slot5 last lost result: `{'iter': 1, 'eax': 0, 'render': 5524696, 'callback': 0, 'd544d10': 1, 'd544d04': 0, 'button0': 0, 'raw': [11520, 28160], 'd543d78': 1, 'd543d7c': 5}`
- Natural slot5 render flag unique values: `[1, 0]`
- Natural slot5 render flag held: `False`
- Natural slot5 click-release rows: `1`
- Natural slot5 owner/action draw count: `2`
- Natural slot5 wrapper copyback count: `0`
- Natural slot5 copyback path marker count: `None`
- Natural slot5 00435BC0 loop/return count: `None` / `None`
- Grid hit: `ok=True`, `entry=[450, 73]`, `result=0`
- Fixture proof class / load slot: `non_natural_isolated_fixture` / `0`
- Legacy load-slot gap / blocked rows: `after_main_load_callback_before_load_menu_case_entry` / `[3, 4, 5]`
- Manual run-plan command count: `5`

## Next Proof Options

- run the hidden v8 copyback trace to classify wrapper entry, stock 00435BC0 return, copyback call/return, or loop stall before 0051B86D
- collect approved visible/manual DirectInput proof and validate the manual proof manifest
