# Expanded battle HD validation candidate

Reviewable 1280x720 candidate; acceptance remains pending. The stable stage is unchanged.

- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlehd`.
- Candidate: `C:\ClashTests\battle-hd-1280x720\clash95_battlehd_review_v3.exe`.
- SHA-256: `7D04FE9005515DAD4E618DF507103946265D7E2A6421287281C1FC5F112D1E47`.
- Patch integrity: all 283 records match; source SHA, old bytes, ranges and appended section are checked.
- Full inventory: `C:\ClashTests\battle-hd-1280x720\patch-stage-review-v3.json`.
- Geometry: up to 17x7 native tiles in `(32,136)-(1120,584)`; original sidebar at `(1120,120)-(1280,600)`.

## Checks

All 14 focused suites pass, including 835 x86 core cases and 17 HUD tests. Five additional merged-harness/launcher suites pass. Source-pin integration and fresh-checkout results are recorded in [the initial report](../../reports/battle_hd_source_binding_integration.md), [the PR60 follow-up](../../reports/battle_hd_source_binding_pr60.md), and [the latest main integration](../../reports/battle_hd_source_binding_checkpoint326.md). The launcher dry run passes and starts no process.

| Final hidden run | Diagnostic result | Evidence boundary |
|---|---|---|
| [Helpers](battle-hd-helpers-current.md), 111019 | 6/7 | Full redraw visits all 112 real tiles; dirty redraw reaches tile (8,0), using zero-based coordinates; dedicated present marker absent. |
| [Camera](battle-hd-camera-current.md), 111125 | 7/7 | Forced clamp/recenter cases at widths 17/20, original 16x7 arena restored. |
| [Lifecycle](battle-hd-lifecycle-current.md), 111326 | 12/14 | Forced commands, modal, results and return/map redraw complete; banner/results cursor polling unresolved. |

All runs use hidden x86 CDB and the memory-only DirectDraw proxy. Input is explicit debugger state/call forcing. Each report binds its exact executable and wrapper hashes. No natural or manual input is inferred.

The unused seventeenth slot has 0/28,672 nonblack pixels. After battle exit, the previously contaminated right gutter has 0/11,776 nonblack pixels. These are narrow saved-software-surface checks, not full restored-map composition proof.

## Saved screenshots

Stage `-castlecenter-all-battlehd`, 1280x720, hidden software captures. Geometry observations only; final visible colors and input remain pending.

![Expanded battle after full/dirty diagnostics](C:/ClashTests/battle-hd-1280x720/captures/cdb-surface-dump-20260908-111019/surface.png)

![Centered results and six native command controls](C:/ClashTests/battle-hd-1280x720/captures/cdb-surface-dump-20260908-111818/surface.png)

![HD map after forced battle exit](C:/ClashTests/battle-hd-1280x720/captures/cdb-surface-dump-20260908-111326/surface.png)

The results snapshot copies the native primary surface to a debugger-allocated buffer and stops before dismissal. It is separate from the lifecycle run. CDB logs retain command-skipping notices after HOST_READY. The older 105738 snapshot has a later probe failure and is retained only as a diagnostic.

## Aggregate refresh

The prior completed refresh had **23/165 failing checks**. Its immutable JSON is under `C:\ClashTests\battle-hd-1280x720\aggregate-after-main-artifacts\`. A fresh aggregate after the latest main integration is pending; the stopped intermediate run has no completed result. The incoming main snapshot is not a new validation of this branch.

- `load_slot_route_limit_guard`: harness: missing marker load_mouse_x: $loadMouseX = 320; harness: missing marker load_mouse_y_formula: $loadMouseY = 166 + (22 * $LoadSlot)
- `right_bottom_slot_fixture_plan`: load-slot route-limit guard is not passing
- `right_bottom_slot_fixture_runtime_plan`: right-bottom slot fixture plan is not passing
- `load_slot_transition_geometry_guard`: transition geometry guard failed: surface_formula_present; surface-dump script missing geometry token: $loadMouseX = 320; surface-dump script missing geometry token: $loadMouseY = 166 + (22 * $LoadSlot)
- `load_slot_transition_probe_preview`: transition probe preview failed: geometry_guard_passed
- `right_bottom_blocker_triage`: triage check failed: hidden_fixture_plan_ready
- `right_bottom_visual_artifact_guard`: visual artifact guard failed: blocker_triage_non_promoting
- `load_slot_transition_readiness`: transition readiness check failed: geometry_guard_passed; transition readiness check failed: probe_preview_passed
- `castle_overview_evidence`: owner_records: missing owner records raw dump: captures\current\castle-owner-records-current.raw; forced_hitmap: missing forced hitmap raw dump: captures\archive\castle-overview-hitmap-flags1f.raw
- `castle_overview_promotion_decision`: castle overview evidence matrix is not passing
- `castle_overview_baseline_recheck`: latest_castle_overview_matrix: owner_records: missing owner records raw dump: captures\current\castle-owner-records-current.raw; latest_castle_overview_matrix: forced_hitmap: missing forced hitmap raw dump: captures\archive\castle-overview-hitmap-flags1f.raw
- `stable_stage_guard`: castle_overview_promotion_decision: castle overview promotion decision is not passing; castle_overview_evidence_matrix: castle overview evidence matrix is not passing
- `python_runtime_safety_guard`: src/launcher/gui.py uses risky Python runtime/input APIs but is not gated or exempt; tools/hd_layout_observation_manifest.py uses risky Python runtime/input APIs but is not gated or exempt; tools/run_framed_offline_tests.py uses risky Python runtime/input APIs but is not gated or exempt
- `resolution_manifest_guard`: manifest missing, invalid, or wrong schema: src\launcher\resolutions.json
- `handoff_freshness_guard`: missing handoff file: .codex-loop\NEXT.md; missing handoff file: .codex-loop\STATE.md; missing handoff file: .codex-loop\TASKS.md; missing current handoff phrase for no_visible_runtime_warning: Do not run visible/manual; missing current handoff phrase for no_visible_runtime_warning: explicit user approval; missing current handoff phrase for no_popup_operator_preference: Do not launch Clash95, CDB, wrappers, PowerShell harnesses; missing current h
- `hd_soak_execution_boundary`: missing_token did not fail closed before side effects; missing_expiry did not fail closed before side effects; expired_packet did not fail closed before side effects; token_mismatch did not fail closed before side effects
- `hd_soak_dry_run_plan`: dry-run harness did not produce a readable JSON plan
- `hd_soak_intro_skip_rerun_readiness`: dry-run plan is not passing; dry-run plan status is 'dry_run_plan_invalid'; dry-run plan would change the stable stage; dry-run plan does not keep right-bottom promotion blocked; dry-run intro_skip click_mode is None, expected 'postmessage'; dry-run intro_skip click_repeat is None, expected 8; dry-run intro_skip space_pulses is None, expected 4; dry-run intro_skip stop_click_repeat_on_drift is None, expected True; dry-run intro_skip proof_class i
- `hd_soak_long_report_guard`: short ladder is not complete; long tiers remain locked; long soak proof manifest is missing: captures\current\hd-soak-long-proof-current.json; missing passing 2h+ representative route: map-idle; missing passing 2h+ representative route: map-pan
- `hd_endurance_release_checklist`: protected_stable_stage: stable-stage guard does not prove the protected boundary; long_soak_representative_routes: 2h+ representative-route soak blocked (locked_short_ladder_incomplete): 2h+ representative-route soak evidence is locked or missing; stable_menu_real_input: menu-load proof remains pending manual DirectInput validation; stable_hd_map_real_input: HD map input proof remains pending manual DirectInput validation; right_bottom_action_men
- `hd_soak_approval_preflight`: dry-run plan report is not passing; dry-run plan status is 'dry_run_plan_invalid'; dry-run plan payload is not marked as a dry run; dry-run plan would change the stable stage; dry-run plan does not keep right-bottom promotion blocked; dry-run plan tier/route do not match the current step; dry-run plan does not pin max input drift to 1 px; dry-run plan sample_interval_sec is not 15; dry-run plan does not pin min nonblack percent; dry-run plan does
- `no_popup_boundary_guard`: stable_stage_guard: refresh check is not passing: stable_stage_guard; python_runtime_safety_guard: refresh check is not passing: python_runtime_safety_guard; hd_soak_execution_boundary: refresh check is not passing: hd_soak_execution_boundary; resolution_manifest_guard: refresh check is not passing: resolution_manifest_guard; handoff_freshness_guard: refresh check is not passing: handoff_freshness_guard; right_bottom_blocker_triage: refresh check
- `docs_consistency_guard`: generated_state: no-popup boundary is failing; documents_handoff: missing document: .codex-loop\NEXT.md; documents_handoff: missing document: .codex-loop\STATE.md; documents_handoff: missing document: .codex-loop\TASKS.md

## Pending acceptance

- Dedicated phase-14 present observation is absent; expanded present/copy bounds retain separate runtime acceptance.
- Banner and results queue cursor (576,360), but their immediate hidden input polls replace X with 4. Natural cursor behavior is unresolved.
- Natural movement, attack targeting, commands, scrolling, hover/tooltips, and dialog input on displayed coordinates need approved visible runtime.
- Hidden full/dirty owner calls and emulator bounds checks do not establish every natural animation or absence of out-of-bounds accesses on all battle routes.
- Camera widths 17 and 20 were forced around clamp/recenter calls without rendering fabricated arena cells; real wider-arena rendering remains unproven.
- The forced lifecycle completes results, owner/input-bound restoration and map redraw, but complete restored map composition and actual map input remain unproven.
- Final wrapper colors/composition, tear-checked captures and manual observations require fresh explicit approval. No such approval is recorded.
- Other resolutions and stable promotion remain follow-up work.

No visible runtime, OS input injection, live capture or manual approval record has been created. The original executable remains unchanged and proprietary artifacts remain under `C:\ClashTests\`. See [the implementation report](../../reports/battle_hd_1280_validation.md) for reproduction and ownership details.
