# Expanded battle HD validation candidate

Reviewable 1280x720 candidate; acceptance remains pending. The stable stage is unchanged.

The source is merged through [PR #61](https://github.com/lisu188/clash-hd/pull/61) at `b747b2e72c36e593149f9d852899e5d6365c813d`. All 19 GitHub checks passed on `10f852d199319b91e82c612d453e68bb40ba0b1e`. A merge does not promote this validation stage.

The harness geometry compatibility fix is merged through [PR #63](https://github.com/lisu188/clash-hd/pull/63) at `6ea7ab0626af49774784924b7b259246cc82a94a`. All four applicable GitHub checks passed on `694988309f66966220677e88093c5492288ea116`. Candidate bytes are unchanged.

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

The required repo-only refresh completed on **2026-09-08T12:17:37+02:00** at source `694988309f66966220677e88093c5492288ea116` with **9/167 failing checks**. All **326 framed fixtures in 32 suites passed, with zero skips or expected failures**. This dated run includes the geometry fix later merged in PR #63; it predates later upstream fixture additions and is not a fresh aggregate of September 13 main.

The immutable [aggregate summary](C:/ClashTests/battle-hd-1280x720/aggregate-final-geometry-compatible-complete/current-evidence-refresh-current.md) and [JSON](C:/ClashTests/battle-hd-1280x720/aggregate-final-geometry-compatible-complete/current-evidence-refresh-current.json) retain every failure. The [stdout log](C:/ClashTests/battle-hd-1280x720/aggregate-final-geometry-compatible.log) and archive manifest are SHA-bound in this report's JSON companion. Repository-wide current reports retain their incoming main versions.

The ten geometry-related failures from the prior 19/167 run now pass. The nine remaining failures concern missing castle raw evidence, long/manual release proof, five inherited Python scanner findings and downstream guards. The [geometry compatibility report](../../reports/battle_hd_geometry_guard_compatibility.md) records the unchanged scanner findings; none is converted to a pass.

- `castle_overview_evidence`: owner_records: missing owner records raw dump: captures\current\castle-owner-records-current.raw; forced_hitmap: missing forced hitmap raw dump: captures\archive\castle-overview-hitmap-flags1f.raw
- `castle_overview_promotion_decision`: castle overview evidence matrix is not passing
- `castle_overview_baseline_recheck`: latest_castle_overview_matrix: owner_records: missing owner records raw dump: captures\current\castle-owner-records-current.raw; latest_castle_overview_matrix: forced_hitmap: missing forced hitmap raw dump: captures\archive\castle-overview-hitmap-flags1f.raw
- `stable_stage_guard`: castle_overview_promotion_decision: castle overview promotion decision is not passing; castle_overview_evidence_matrix: castle overview evidence matrix is not passing
- `python_runtime_safety_guard`: src/launcher/gui.py uses risky Python runtime/input APIs but is not gated or exempt; tools/framed_army_portrait_trace.py uses risky Python runtime/input APIs but is not gated or exempt; tools/framed_army_transition_trace.py uses risky Python runtime/input APIs but is not gated or exempt; tools/framed_primary_surface.py uses risky Python runtime/input APIs but is not gated or exempt; tools/run_framed_offline_tests.py uses risky Python runtime/input APIs but is not gated or exempt
- `hd_soak_long_report_guard`: long soak proof manifest is missing: captures\current\hd-soak-long-proof-current.json; missing passing 2h+ representative route: map-idle; missing passing 2h+ representative route: map-pan
- `hd_endurance_release_checklist`: protected_stable_stage: stable-stage guard does not prove the protected boundary; long_soak_representative_routes: 2h+ representative-route soak blocked (blocked_missing_long_proof): 2h+ representative-route soak evidence is locked or missing; stable_menu_real_input: menu-load proof remains pending manual DirectInput validation; stable_hd_map_real_input: HD map input proof remains pending manual DirectInput validation; right_bottom_action_menu: right-bottom action/menu remains validation-only or manual-proof blocked; castle_and_barracks_centered_input: castle/barracks centered input remains validation-only or manual-proof blocked; tactical_battle_entry_return: battle promotion evidence is absent or remains validation-only; callback proof alone is not promotion; no_speculative_promotion: one or more promotion boundaries are not fail-closed
- `no_popup_boundary_guard`: stable_stage_guard: refresh check is not passing: stable_stage_guard; python_runtime_safety_guard: refresh check is not passing: python_runtime_safety_guard; castle_overview_baseline_recheck: refresh check is not passing: castle_overview_baseline_recheck; docs_consistency_guard: refresh check is not passing: docs_consistency_guard
- `docs_consistency_guard`: generated_state: no-popup boundary is failing

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
