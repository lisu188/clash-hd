# Right-Bottom Blocker Triage

- Overall: PASS
- Generated: `2026-07-12T19:22:28+02:00`
- Runtime policy: repo-only evidence triage; reads generated JSON reports and does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: passes only while the current blocker is explicitly classified as non-promoting: controlled composition is recovered, natural owner/action rows are absent, the natural route is either owner-flag gated, blocked inside the slot5 Render_Begin/DD_Pump/copyback lane, blocked by the documented loop-state/input-resample/source-hold lane, or has only debugger-forced native action-click copyback proof; the next proof path remains hidden diagnosis or approved manual input
- Classification: `controlled_recovered_but_natural_route_nonpromoting`
- Promotion ready: `False`
- stable_stage_should_change: `False`
- Conclusion: The right-bottom action/menu surface is not stable-promotable yet. Controlled composition recovers the lower/right UI, and the v17b natural slot-5 diagnostic proves the right-bottom wrapper can allocate the native surface, enter stock 00435BC0, force a native action-button click at (81,441), reach descriptor 0051519a and callback 00435620, set the modal exit state, return from stock, and copy the native surface back into the 800x600 HD surface without an AV. That is debugger-forced proof, not a real input-source or manual DirectInput proof, so stable promotion remains deferred.

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
- Natural slot5 proof class: `natural_slot5_right_bottom_action_click_native`
- Natural slot5 status: `owner_action_copyback_reached`
- Natural slot5 Render_Begin stalled: `False`
- Natural slot5 DD_Pump wait stalled: `False`
- Natural slot5 Render_Begin late-armed count: `1`
- Natural slot5 last flip result: `{'iter': 7, 'eax': 0, 'render': 5524696, 'callback': 0, 'd544d10': 1, 'd544d04': 0, 'button0': 109, 'raw': [256, 28224], 'd543d78': 1, 'd543d7c': 5}`
- Natural slot5 last lost result: `{'iter': 7, 'eax': 0, 'render': 5524696, 'callback': 0, 'd544d10': 1, 'd544d04': 0, 'button0': 109, 'raw': [256, 28224], 'd543d78': 1, 'd543d7c': 5}`
- Natural slot5 render flag unique values: `[1, 0, 2, 3]`
- Natural slot5 render flag held: `False`
- Natural slot5 click-release rows: `1`
- Natural slot5 owner/action draw count: `3`
- Natural slot5 wrapper copyback count: `1`
- Natural slot5 copyback path marker count: `74`
- Natural slot5 native action-click marker count: `10`
- Natural slot5 native/display force counts: `1` / `0`
- Natural slot5 native action force/callback/00435620/exit counts: `1` / `1` / `1` / `1`
- Natural slot5 source-hold callsite/inner-004612E0 counts: `4` / `0`
- Natural slot5 input-source cb14=004612E0 seen: `True`
- Natural slot5 input-source status: `debugger_forced_action_click_only`
- Natural slot5 real input click proven: `False`
- Natural slot5 debugger-forced click only: `True`
- Natural slot5 last native action force marker: `NOWNER_ACTION_FORCE_NATIVE`
- Natural slot5 last native action force: `{'target': 'bottom-left-action', 'pass_index': 1, 'native': [81, 441], 'raw': [5184, 28224], 'click_flag': 1, 'button0': 128, 'selected_index': 0, 'hover_slot': -1, 'action_state': 0}`
- Natural slot5 last native action descriptor callback: `{'desc': 5329306, 'callback': 4412960, 'desc_xy': [41, 425], 'state': 1, 'mouse': [81, 441], 'action_state': 0}`
- Natural slot5 last native action click exit-set: `{'pass_index': 1, 'action_state': 1, 'selected_index': 0, 'hover_slot': -1}`
- Natural slot5 00435BC0 loop/return count: `1` / `1`
- Natural slot5 00435BC0 poll/limit count: `16` / `1`
- Natural slot5 00435BC0 grid route/fail/selection-update count: `0` / `0` / `0`
- Natural slot5 last 00435BC0 poll: `{'count': 16, 'd532210': 1, 'd532218': 68929306, 'd532220': 0, 'd5322c8': -1, 'mouse': [4, 441], 'raw': [256, 28224], 'd544d04': 0, 'button0': 109, 'surface': 61287224, 'size': [640, 480]}`
- Natural slot5 last 00435BC0 poll before action force: `{'count': 1, 'd532210': 0, 'd532218': 68929306, 'd532220': 0, 'd5322c8': -1, 'mouse': [180, 440], 'raw': [11520, 28160], 'd544d04': 0, 'button0': 0, 'surface': 61287224, 'size': [640, 480]}`
- Natural slot5 first 00435BC0 poll after action force: `{'count': 2, 'd532210': 0, 'd532218': 68929306, 'd532220': 0, 'd5322c8': -1, 'mouse': [81, 441], 'raw': [5184, 28224], 'd544d04': 1, 'button0': 128, 'surface': 61287224, 'size': [640, 480]}`
- Natural slot5 last 00435BC0 poll after action force: `{'count': 16, 'd532210': 1, 'd532218': 68929306, 'd532220': 0, 'd5322c8': -1, 'mouse': [4, 441], 'raw': [256, 28224], 'd544d04': 0, 'button0': 109, 'surface': 61287224, 'size': [640, 480]}`
- Natural slot5 last 00435BC0 grid gate: `None`
- Natural slot5 last 00435BC0 pump tick-return: `{'iter': 1, 'ret': 4414942, 'eax': 92018356, 'render': 5524696, 'd544d10': 1, 'd544d04': 0, 'button0': 0, 'raw': [11520, 28160], 'd543d78': 1, 'd543d7c': 5}`
- Natural slot5 last 00435BC0 pump cb14 call: `{'iter': 1, 'ret': 4414942, 'vtable': 5304836, 'cb14': 4592352, 'render': 5524696, 'raw': [11520, 28160], 'd544d04': 0, 'button0': 0}`
- Natural slot5 last 00435BC0 pump 608f0b call: `{'iter': 1, 'ret': 4414942, 'render': 5524696, 'raw': [11520, 28160], 'd544d04': 0, 'button0': 0}`
- Natural slot5 last 00435BC0 pump cb04 call: `{'iter': 1, 'ret': 4414942, 'vtable': 5304836, 'cb04': 4592032, 'render': 5524696, 'raw': [11520, 28160], 'd544d04': 0, 'button0': 0}`
- Natural slot5 first 00435BC0 pump tick-return: `{'iter': 1, 'ret': 4414942, 'eax': 92018356, 'render': 5524696, 'd544d10': 1, 'd544d04': 0, 'button0': 0, 'raw': [11520, 28160], 'd543d78': 1, 'd543d7c': 5}`
- Natural slot5 first 00435BC0 pump cb14 call: `{'iter': 1, 'ret': 4414942, 'vtable': 5304836, 'cb14': 4592352, 'render': 5524696, 'raw': [11520, 28160], 'd544d04': 0, 'button0': 0}`
- Natural slot5 first 00435BC0 pump 608f0b call: `{'iter': 1, 'ret': 4414942, 'render': 5524696, 'raw': [11520, 28160], 'd544d04': 0, 'button0': 0}`
- Natural slot5 timeout stack classification: `not_found`
- Grid hit: `ok=True`, `entry=[450, 73]`, `result=0`
- Fixture proof class / load slot: `non_natural_isolated_fixture` / `0`
- Legacy load-slot gap / blocked rows: `after_main_load_callback_before_load_menu_case_entry` / `[3, 4, 5]`
- Manual run-plan command count: `5`

## Next Proof Options

- run the refined exact entry/return markers around the cb14=004612e0 call so the 00519620/00519622 source-copy path is directly proven
- prove the real input-source path through 00519620/00519622 or 004612E0 that naturally supplies the action-button click without debugger-forced native coordinates
- finish interpreting the stock 00435BC0 grid route/selection-update behavior now that v17b proves the native action-button exit/copyback path
- decide whether the HD wrapper should drive a native-modal input transform or preserve the stock modal loop while copying back only after exit
- reduce the v17b diagnostic into a patch-stage decision that excludes debugger-only coordinate injection
- collect approved visible/manual DirectInput proof and validate the manual proof manifest
