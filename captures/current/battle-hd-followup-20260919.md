# Expanded battle hidden validation follow-up — September 19

The present-call diagnostic gap is closed for the unchanged 1280x720 validation candidate. Hidden input polling is now classified; visible/input acceptance and stable promotion remain pending.

Candidate: `C:\ClashTests\battle-hd-20260919\clash95_battlehd.exe`; SHA-256 `7D04FE9005515DAD4E618DF507103946265D7E2A6421287281C1FC5F112D1E47`. All 283 patch records verify. The original executable SHA remains unchanged.

Diagnostic sources are merged in [PR #87](https://github.com/lisu188/clash-hd/pull/87) at `c485a61b94ba098618f39e9d4fc82400c712c475`. All four Windows/Linux CI jobs passed on `f590f851899d9704ceb786f85075e5c97388813c`. This merge does not promote the validation stage.

The retained Windows framed CI report covers 56 selected suites: 405 successful tests and 218 skip records. Its offline status passes, but selected coverage is explicitly incomplete. It includes the incoming modal lifecycle suite; this CI pass does not replace local fixtures or runtime evidence.

## Present observation

Run 115223 passes 7/7 helper diagnostics. One ordered dispatch → observed function body → return → completion sequence binds the same object, thread, stack and 1280x720 surface. The interior breakpoint follows a verified push instruction; it avoids relying on a software breakpoint at the exact resumed instruction. Full redraw covers 112 real 16x7 cells; dirty redraw reaches tile (8,0). Exact copy bounds, natural animation and final presentation remain separate claims.

![1280x720 expanded battle, hidden CDB software surface](C:/ClashTests/battle-hd-20260919/helper-captures/cdb-surface-dump-20260919-115223/surface.png)

Stage suffix `-castlecenter-all-battlehd`, hidden software capture. All four battlefield frame edges are visible. The unused seventeenth slot contains 0/28,672 nonblack pixels. Bottom-right command artwork is absent from this capture, so command composition is not verified.

## Cursor polling diagnosis

Final strict run 120433 observes three ordered cursor → device call/return → origin lookup → cursor return sequences. Each failed native input read returns `8007000C` without changing its 16-byte buffer. Origin lookup succeeds at (0,0); the updater then consumes those buffer values. The exact native Device_UpdateRect wrapper and all intervening return addresses are byte-bound.

| Dialog | Queued cursor | Returned cursor | Device read |
|---|---|---|---|
| Banner | (576,360) | (4,360) | Failed; unchanged buffer |
| Modal | (576,360) | (576,360) | Failed; unchanged buffer |
| Results | (576,360) | (4,360) | Failed; unchanged buffer |

This diagnoses consumption of an unchanged stack buffer after a failed read in the forced hidden path. It does not justify changing battle or generic input bytes and does not prove visible cursor behavior. Forced lifecycle diagnostics remain 12/14; both affected cursor checks remain unproven.

![1280x720 map after forced battle exit, hidden CDB software surface](C:/ClashTests/battle-hd-20260919/cursor-captures/cdb-surface-dump-20260919-120433/surface.png)

The map terrain/minimap return and cleared battle-sidebar area are visible. The bottom-right six action cells and complete four-sided map frame are absent from this software surface. Full restored-map composition and real input remain unverified.

## Verification and preserved attempts

All 16 focused suites pass, including 835 x86 core scenarios, 17 HUD tests, 19 renderer tests and 10 cursor contracts with both executable files and the retained stack log. No game is launched by these fixtures. Both final hidden runs have matching candidate identity, no timeout/runtime error and successful cleanup. Source snapshots, wrappers, probes, logs and captures are bound by hashes in the JSON companion.

- 114730 remains a failed debugger byte-comparison attempt followed by a 90-second harness timeout, with cleanup and no screenshot. Offline bytes matched; narrower comparisons succeeded. The exact integer-width cause remains inferred.
- 115400 remains an incomplete cursor observation: three entry/return pairs, with the initial interior filters missing the native wrapper.
- 115941 retains bounded raw stacks used to identify that wrapper. Final run 120433 uses corrected strict filters without the raw-stack fallback.
- The original September 8 helper, camera and lifecycle reports remain unchanged. Post-dump command-skipping notices remain recorded; no later natural interval is inferred.

## Aggregate

The fresh repo-only aggregate at `f590f851899d9704ceb786f85075e5c97388813c` completed with **10/167 failing checks**. Complete generated reports and stdout are retained under `C:\ClashTests\battle-hd-20260919\aggregate`; exact pre-run repository current reports were restored after archival. The JSON companion records every failing check.

Its local framed run records 567 successful tests across 55 selected suites, one symlink-privilege skip, 26 assertion-failure records and 40 error records across five army suites. There were no fixture timeouts. Those suites rejected the renderer checkout's CRLF bytes against its required LF source hash. The exact tracked LF bytes have been restored without changing text content or any source pin; frozen runtime source snapshots and the failed aggregate remain intact.

After updating to main `a6aef412d29fa759b3f638d0912444c10dff5ae1`, all 11 targeted integration/repair suites pass, with 2 unittest skip records. Their separate logs retain actual coverage; skipped cases are not proven. The original aggregate remains 10/167 failing; no replacement aggregate pass is claimed. It predates the incoming modal lifecycle and strengthened native-blitter fixture additions.

- `framed_offline_fixtures`: Five army suites reject CRLF renderer checkout bytes against the required LF source hash; one unrelated symlink-privilege skip also leaves coverage incomplete.
- `castle_overview_evidence`: owner_records: missing owner records raw dump: captures\current\castle-owner-records-current.raw; forced_hitmap: missing forced hitmap raw dump: captures\archive\castle-overview-hitmap-flags1f.raw
- `castle_overview_promotion_decision`: castle overview evidence matrix is not passing
- `castle_overview_baseline_recheck`: latest_castle_overview_matrix: owner_records: missing owner records raw dump: captures\current\castle-owner-records-current.raw; latest_castle_overview_matrix: forced_hitmap: missing forced hitmap raw dump: captures\archive\castle-overview-hitmap-flags1f.raw
- `stable_stage_guard`: castle_overview_promotion_decision: castle overview promotion decision is not passing; castle_overview_evidence_matrix: castle overview evidence matrix is not passing
- `python_runtime_safety_guard`: src/launcher/gui.py uses risky Python runtime/input APIs but is not gated or exempt; tools/complete_hd_army_movement_trace.py uses risky Python runtime/input APIs but is not gated or exempt; tools/complete_hd_manual_attach.py uses risky Python runtime/input APIs but is not gated or exempt; tools/complete_hd_manual_attach_win32.py uses risky Python runtime/input APIs but is not gated or exempt; tools/framed_army_portrait_trace.py uses risky Python runtime/input APIs but is not gated or exempt; tools/framed_army_transition_trace.py uses risky Python runtime/input APIs but is not gated or exempt; tools/framed_primary_surface.py uses risky Python runtime/input APIs but is not gated or exempt; tools/modal_slots_primary_surface.py uses risky Python runtime/input APIs but is not gated or exempt; tools/run_framed_offline_tests.py uses risky Python runtime/input APIs but is not gated or exempt
- `hd_soak_long_report_guard`: long soak proof manifest is missing: captures\current\hd-soak-long-proof-current.json; missing passing 2h+ representative route: map-idle; missing passing 2h+ representative route: map-pan
- `hd_endurance_release_checklist`: protected_stable_stage: stable-stage guard does not prove the protected boundary; long_soak_representative_routes: 2h+ representative-route soak blocked (blocked_missing_long_proof): 2h+ representative-route soak evidence is locked or missing; stable_menu_real_input: menu-load proof remains pending manual DirectInput validation; stable_hd_map_real_input: HD map input proof remains pending manual DirectInput validation; right_bottom_action_menu: right-bottom action/menu remains validation-only or manual-proof blocked; castle_and_barracks_centered_input: castle/barracks centered input remains validation-only or manual-proof blocked; tactical_battle_entry_return: battle promotion evidence is absent or remains validation-only; callback proof alone is not promotion; no_speculative_promotion: one or more promotion boundaries are not fail-closed
- `no_popup_boundary_guard`: stable_stage_guard: refresh check is not passing: stable_stage_guard; python_runtime_safety_guard: refresh check is not passing: python_runtime_safety_guard; castle_overview_baseline_recheck: refresh check is not passing: castle_overview_baseline_recheck; docs_consistency_guard: refresh check is not passing: docs_consistency_guard
- `docs_consistency_guard`: generated_state: no-popup boundary is failing

Visible runtime, OS input injection, live capture and manual observation remain unapproved. The [expanded-stage session plan](../../reports/battle_hd_visible_validation_plan.md) records preparation requirements; the old centered input harness cannot be reused unchanged. The stable stage, resolution statuses and 800x600 launcher default are unchanged.
