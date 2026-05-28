---
title: Log
type: log
status: active
created: 2026-04-22
updated: 2026-05-15
tags:
  - log
---

# Log

## [2026-05-15] correction | Right-bottom action-menu visual gate

- Source updated: `[source: tools/current_evidence_refresh.py]`,
  `[source: tools/right_bottom_compose_evidence_matrix.py]`,
  `[source: tools/right_bottom_compose_promotion_decision.py]`,
  `[source: captures/right-bottom-compose-evidence-current.md]`, and
  `[source: captures/right-bottom-compose-promotion-decision-current.md]`.
- Pages updated: [[Clash95 HD Mod Progress]],
  [[Clash95 Engine Viewport Patch Notes]], and [[Log]].
- Contradictions: previous right-bottom reports treated controlled CDB/proxy
  evidence as passing validation even though the screenshot showed stripey,
  misplaced action/status buttons.
- Resolution: the controlled grid-hit screenshot is diagnostic only. Natural
  owner/action draw rows are now required; the current right-bottom compose
  matrix and promotion decision fail closed with `RBUI_PANEL_DRAW=0` and
  `RBUI_ACTION_BOX=0`.
- Open questions: find a natural owner/action route with acceptable final
  placement, then revisit anchor/copyback and paired hitboxes.

## [2026-05-15] maintenance | Manual proof contract

- Source updated: `[source: tools/manual_directinput_checklist.py]`,
  `[source: tools/manual_directinput_proof_template.py]`,
  `[source: captures/manual-directinput-validation-checklist-tests-current.md]`,
  and `[source: captures/manual-directinput-proof-template-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Clash95 HD Mod Progress]],
  [[Clash95 Engine Viewport Patch Notes]], and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/visible DirectInput proof remains unsupplied and still
  requires explicit approval before any visible runtime.
- Notes: manual proof manifests now require approval record, candidate path,
  executable SHA, no-stale-process cleanup, and per-target stage, observation,
  evidence, pass/fail notes, and no-crash rows.
- Notes: checklist fixture tests now pass with `test_count=9`; no Clash95, CDB,
  wrapper, PowerShell harness, or visible window was launched.

## [2026-05-14] maintenance | No-popup boundary guard count

- Source updated: `[source: tools/no_popup_boundary_guard.py]`,
  `[source: tools/test_no_popup_guards.py]`,
  `[source: captures/no-popup-boundary-guard-current.md]`, and
  `[source: captures/current-evidence-refresh-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[Clash95 HD Mod Progress]], and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/visible DirectInput proof remains unsupplied and still
  requires explicit approval.
- Notes: the no-popup boundary guard now records `required_guard_count=6`,
  `required_supporting_report_count=34`, and `required_report_count=40`; the
  six core guards include the visible-runtime launcher guard.
- Notes: no visible Clash95, CDB, wrapper, PowerShell harness, or visible
  window was launched.

## [2026-05-14] maintenance | Visible runtime launcher guard

- Source updated: `[source: tools/visible_runtime_launcher_guard.py]`,
  `[source: tools/test_visible_runtime_launcher_guard.py]`,
  `[source: captures/visible-runtime-launcher-guard-current.md]`, and
  `[source: captures/visible-runtime-launcher-guard-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[No-Popup Surface Dump]], [[What Manual DirectInput Validation Remains]],
  [[Clash95 Engine Viewport Patch Notes]], [[Clash95 HD Mod Progress]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: manual/visible DirectInput proof remains unsupplied and
  should not run without explicit approval.
- Notes: the guard passes repo-only, checks 12 legacy visible-runtime
  launchers/helpers, and requires `-AllowVisibleRuntime` before risky runtime,
  window-focus, cursor, SendInput, PostMessage, or `CopyFromScreen` work.
- Notes: the guard now inventories root PowerShell risky calls and reports
  `15` risky scripts, `12` guarded scripts, `3` documented exemptions, and `0`
  unclassified scripts.
- Notes: fixture tests pass with `test_count=10`, covering gated launchers,
  gated foreground helpers, gated screen-capture helpers, missing switches,
  missing explicit-approval wording, guarded child-helper forwarding, late
  guards after risky calls, unclassified risky scripts, documented exemptions,
  and CLI fail-closed behavior.
- Notes: the current evidence refresh and no-popup boundary guard now require
  both visible-runtime launcher reports, and the evidence index reports `72`
  links, `9` images, `81` local records, and `0` missing records.
- Notes: the handoff freshness guard now also requires those visible-runtime
  launcher artifacts and the `-AllowVisibleRuntime` approval wording; its
  fixture tests pass with `test_count=11`, including stale legacy
  outside-debugger/visible-capture and VM/visual-smoke task cases.

## [2026-05-14] maintenance | Manual proof template

- Source updated: `[source: tools/manual_directinput_proof_template.py]`,
  `[source: tools/test_manual_directinput_proof_template.py]`,
  `[source: captures/manual-directinput-proof-template-current.md]`, and
  `[source: captures/manual-directinput-proof-template-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[What Manual DirectInput Validation Remains]],
  [[Clash95 Engine Viewport Patch Notes]], [[Clash95 HD Mod Progress]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: no manual/real DirectInput proof has been supplied; visible
  validation still requires explicit approval.
- Notes: the template report passes repo-only, records
  `template_valid_as_proof=False`, and lists the five required manual target
  IDs without launching Clash95, CDB, wrappers, PowerShell, or a visible window.
- Notes: the template tests pass with `test_count=4` and prove the template
  stays invalid until placeholders are replaced with approved manual evidence.
- Notes: the handoff freshness guard also requires the template artifact, the
  `template_valid_as_proof=False` marker, and the no-popup operator preference;
  its fixture report now passes with `test_count=10`, including missing
  proof-template artifact, missing no-popup-preference, missing
  visible-launcher-guard cases, and stale legacy outside-debugger/visible-capture
  task cases.

## [2026-05-14] maintenance | Promotion override guard

- Source updated: `[source: tools/promotion_override_guard.py]`,
  `[source: tools/test_promotion_override_guard.py]`,
  `[source: captures/promotion-override-guard-current.md]`, and
  `[source: captures/promotion-override-guard-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[What Manual DirectInput Validation Remains]],
  [[Clash95 Engine Viewport Patch Notes]], [[Clash95 HD Mod Progress]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: no manual/real DirectInput proof has been supplied; visible
  validation still requires explicit approval.
- Notes: the guard passes repo-only and verifies that right-bottom compose,
  castle overview, and manual checklist reports keep CDB-only promotion
  overrides inactive and stable-stage change flags false.
- Notes: the fixture tests pass with `test_count=7`, covering unexpected
  right-bottom/castle overrides, promotion-ready manual checklist state,
  manual proof appearing in current no-popup evidence, missing JSON, and CLI
  fail-closed behavior.
- Notes: the no-popup boundary guard now requires both promotion override
  reports, and the evidence index reports `70` links, `9` images, `79` local
  records, and `0` missing records.

## [2026-05-14] maintenance | Promotion proof manifest enforcement

- Source updated: `[source: tools/right_bottom_compose_promotion_decision.py]`,
  `[source: tools/castle_overview_promotion_decision.py]`,
  `[source: tools/test_right_bottom_compose_promotion_decision.py]`,
  `[source: tools/test_castle_overview_promotion_decision.py]`, and
  `[source: captures/current-evidence-refresh-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[What Manual DirectInput Validation Remains]],
  [[Clash95 Engine Viewport Patch Notes]], [[Clash95 HD Mod Progress]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: no manual/real DirectInput proof has been supplied; visible
  validation still requires explicit approval.
- Notes: both right-bottom and castle overview promotion decisions now validate
  `--manual-input-proof` with the manual DirectInput checklist schema, reject
  placeholder proof files, and currently report `manual_input_proof_valid=False`.
- Notes: the refreshed repo-only decision test reports pass with
  `test_count=6` for right-bottom and `test_count=7` for castle overview.

## [2026-05-14] maintenance | Manual DirectInput checklist

- Source updated: `[source: tools/manual_directinput_checklist.py]`,
  `[source: tools/test_manual_directinput_checklist.py]`,
  `[source: captures/manual-directinput-validation-checklist-current.md]`, and
  `[source: captures/manual-directinput-validation-checklist-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[What Manual DirectInput Validation Remains]], [[Clash95 HD Mod Progress]],
  and [[Log]].
- Contradictions: none recorded.
- Open questions: the five manual/real DirectInput targets are now enumerated,
  but no manual proof has been supplied and visible validation still requires
  explicit approval.
- Notes: the checklist is repo-only, records
  `status=pending_manual_validation`, `pending_count=5`,
  `promotion_ready=False`, `manual_proof_valid=False`, and
  `stable_stage_should_change=False`, plus the no-popup operator preference.
- Notes: placeholder proof files are rejected; promotion readiness now requires
  either a valid manual proof manifest or an explicit CDB-only override.
- Notes: the checklist fixture tests now pass with `test_count=9`, including
  coverage that the no-popup preference remains present and incomplete manual
  proof records fail closed.
- Notes: the no-popup boundary guard now requires the checklist and
  checklist-test reports, so pending manual proof remains part of the aggregate
  no-popup evidence gate.

## [2026-05-14] maintenance | Process hygiene guard tests

- Source updated: `[source: tools/test_process_hygiene_guard.py]` and
  `[source: captures/process-hygiene-guard-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[No-Popup Surface Dump]], [[Clash95 HD Mod Progress]], and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/visible DirectInput proof remains unsupplied and
  should not run without explicit approval.
- Notes: the test report passes repo-only with `test_count=5`, covering clean
  snapshots, exact `cdb.exe` matches, `clash95*` prefix matches, snapshot
  failures, case-insensitive matching, and CLI fail-closed behavior.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `process_hygiene_guard_tests`; the no-popup boundary guard requires the
  report, and the evidence index reports `64` links, `9` images, `73` local
  records, and `0` missing records.

## [2026-05-14] maintenance | Handoff freshness guard

- Source updated: `[source: tools/handoff_freshness_guard.py]`,
  `[source: tools/test_handoff_freshness_guard.py]`,
  `[source: captures/handoff-freshness-guard-current.md]`, and
  `[source: captures/handoff-freshness-guard-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[No-Popup Surface Dump]], [[How Should The Bottom Tooltip Be Recovered]],
  and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/visible DirectInput proof remains unsupplied and
  should not run without explicit approval.
- Notes: the guard passes repo-only and verifies current handoff/evidence docs
  mention the route timing guard, the manual/visible DirectInput or explicit
  CDB-only promotion blocker, the no-visible runtime warning, and the
  stable-stage boundary, keep the non-promoting manual proof template artifact
  visible, preserve the no-popup operator preference, and require the
  visible-runtime launcher approval guard.
- Notes: the fixture tests now pass with `test_count=10`, including missing
  manual proof-template artifact, missing no-popup-preference, missing
  visible-launcher-guard cases, and stale legacy outside-debugger/visible-capture
  task cases.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `handoff_freshness_guard` and `handoff_freshness_guard_tests`; the no-popup
  boundary guard requires both reports, and the evidence index reports `63`
  links, `9` images, `72` local records, and `0` missing records.

## [2026-05-14] evidence | Right-bottom route timing guard

- Source updated: `[source: tools/right_bottom_route_timing_guard.py]`,
  `[source: tools/test_right_bottom_route_timing_guard.py]`,
  `[source: captures/right-bottom-route-timing-guard-current.md]`, and
  `[source: captures/right-bottom-route-timing-guard-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[Right-Bottom UI And Bottom Tooltip Recovery]], [[Clash95 HD Mod Progress]],
  [[Clash95 Engine Viewport Patch Notes]], and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/visible DirectInput proof remains unsupplied and
  should not run without explicit approval.
- Notes: the guard passes repo-only and checks the archived validation patch
  route, full-start owner/action route, and controlled grid-hit route for
  hidden execution, 800x600 surfaces, candidate SHA agreement, stable marker
  ordering, and zero AV/failure-exit rows.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `right_bottom_route_timing_guard` and
  `right_bottom_route_timing_guard_tests`; the no-popup boundary guard now
  requires both reports, and the evidence index reports `61` links, `9`
  images, `70` local records, and `0` missing records.

## [2026-05-14] maintenance | Menu-surface scope guard

- Source updated: `[source: tools/stable_stage_guard.py]`,
  `[source: tools/test_stable_stage_guard.py]`,
  `[source: captures/stable-stage-guard-current.md]`, and
  `[source: captures/stable-stage-guard-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: visible/manual smoke remains blocked without explicit user
  approval.
- Notes: the stable-stage guard now checks 11 `mapsurface` stages and reports
  zero stages with the old global `menu-surface` group plus zero stages missing
  `map-surface-upgrade-scrollclamp`.
- Notes: stable-stage guard fixture coverage now has `test_count=10` and
  rejects `mapsurface` stages that reintroduce `menu-surface` or lose the
  gameplay-only upgrade.

## [2026-05-14] evidence | Right-bottom grid-hit probe guard

- Source updated: `[source: tools/right_bottom_grid_hit_probe_guard.py]`,
  `[source: tools/test_right_bottom_grid_hit_probe_guard.py]`,
  `[source: captures/right-bottom-grid-hit-probe-guard-current.md]`,
  and `[source: captures/right-bottom-grid-hit-probe-guard-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[Right-Bottom UI And Bottom Tooltip Recovery]], [[Clash95 HD Mod Progress]],
  [[Clash95 Engine Viewport Patch Notes]], and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/visible DirectInput proof remains unsupplied and
  should not run without explicit approval.
- Notes: the guard passes repo-only and verifies the focused right-bottom CDB
  script breakpoints, parser marker coverage, hidden-desktop launch policy,
  800x600 ready surface, native `(450,73) -> 0` proof, zero failure-exit rows,
  and zero AV rows.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `right_bottom_grid_hit_probe_guard` and
  `right_bottom_grid_hit_probe_guard_tests`; the no-popup boundary guard now
  requires both reports, and the evidence index reports `59` links, `9`
  images, `68` local records, and `0` missing records.

## [2026-05-14] evidence | Right-bottom controlled grid-hit proof

- Source updated: `[source: clash95_right_bottom_grid_hit_extra.cdb]`,
  `[source: tools/right_bottom_grid_hit_summary.py]`,
  `[source: captures/cdb-surface-dump-20260514-140601/right-bottom-grid-hit-summary.md]`,
  and `[source: captures/right-bottom-grid-hit-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[Right-Bottom UI And Bottom Tooltip Recovery]], [[Clash95 HD Mod Progress]],
  [[Clash95 Engine Viewport Patch Notes]], and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/visible DirectInput proof remains unsupplied and
  should not run without explicit approval.
- Notes: hidden-desktop CDB/proxy run
  `captures/cdb-surface-dump-20260514-140601` passed with native
  `(450,73)`, grid result `0`, `draw_row_count=5`, `failure_exit_count=0`,
  and `av_count=0`.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `right_bottom_grid_hit` and `right_bottom_grid_hit_summary_tests`; the
  no-visible runtime guard reports `19/19` hidden-desktop CDB runs.

## [2026-05-14] maintenance | No-popup guard test output isolation

- Source updated: `[source: tools/test_no_popup_guards.py]`,
  `[source: tools/current_evidence_refresh.py]`,
  `[source: captures/no-popup-guard-tests-current.md]`, and
  `[source: captures/surface-dump-policy-guard-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Clash95 HD Mod Progress]],
  [[Clash95 Engine Viewport Patch Notes]], and [[Log]].
- Contradictions: none recorded.
- Open questions: none for this repo-only test hygiene fix.
- Notes: the failing surface-dump policy CLI fixture now writes
  `bad-surface-policy.json/md` under
  `.codex-loop\tmp-tests\no-popup-guards-fixture`, so it cannot overwrite the
  current `captures/surface-dump-policy-guard-current.md/json` reports.
- Notes: the regression tests pass without launching Clash95, CDB, wrappers,
  PowerShell, or any visible window.

## [2026-05-14] maintenance | No-visible runtime guard tests

- Source updated: `[source: tools/test_no_visible_runtime_guard.py]`,
  `[source: tools/current_evidence_refresh.py]`,
  `[source: tools/no_popup_boundary_guard.py]`, and
  `[source: captures/no-visible-runtime-guard-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: none for this fixture guard; visible/manual runtime proof
  remains opt-in and should not run on the active desktop without explicit
  approval.
- Notes: `tools/test_no_visible_runtime_guard.py` passes repo-only, and
  `tools/current_evidence_refresh.py --require-pass` now includes
  `no_visible_runtime_guard_tests: PASS` with `test_count=5`.
- Notes: the fixture report covers hidden-desktop summaries, weak runtime
  policy text, visible runtime summary regressions, missing run summaries, and
  CLI `--require-pass` fail-closed behavior.
- Notes: the no-popup boundary guard now requires the fixture-test report, and
  no visible Clash window was used.

## [2026-05-14] maintenance | No-popup map evidence matrix tests

- Source updated: `[source: tools/test_no_popup_map_evidence_matrix.py]`,
  `[source: tools/current_evidence_refresh.py]`,
  `[source: tools/no_popup_boundary_guard.py]`, and
  `[source: captures/no-popup-map-evidence-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: none for this fixture guard; future HD-map changes still
  need no-popup or explicitly approved runtime evidence before baseline
  changes.
- Notes: `tools/test_no_popup_map_evidence_matrix.py` passes repo-only, and
  `tools/current_evidence_refresh.py --require-pass` now includes
  `no_popup_map_evidence_tests: PASS` with `test_count=5`.
- Notes: the fixture report covers explicit normal/forced inputs, latest
  passing-run selection, normal visibility-gate regressions, forced-visible
  gate regressions, and CLI `--require-pass` fail-closed behavior.
- Notes: the no-popup boundary guard now requires the fixture-test report, and
  no visible Clash window was used.

## [2026-05-14] maintenance | No-popup map evidence in current refresh

- Source updated: `[source: tools/current_evidence_refresh.py]`,
  `[source: tools/no_popup_boundary_guard.py]`,
  `[source: captures/no-popup-map-evidence-current.md]`, and
  `[source: captures/current-evidence-refresh-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: future HD-map improvements still need no-popup or explicitly
  approved runtime proof before changing the stable baseline.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `no_popup_map_evidence: PASS` and writes
  `captures/no-popup-map-evidence-current.md` plus `.json`.
- Notes: the no-popup map evidence baseline pairs
  `captures/cdb-surface-dump-20260429-140916` with
  `captures/cdb-surface-dump-20260429-135242`; the normal run has `13`
  blank active cells, `0` unexplained blanks, and `visibility_zero=13`, while
  the forced-visible run has `0` blank active cells and `54` nonzero
  visibility/nonblack post rows.
- Notes: the no-popup boundary guard now requires `no_popup_map_evidence`, and
  the no-visible runtime guard covers `18` hidden-desktop CDB surface-dump
  runs.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Right-bottom validation guard tests

- Source updated:
  `[source: tools/test_right_bottom_compose_promotion_decision.py]`,
  `[source: tools/test_right_bottom_compose_evidence_matrix.py]`,
  `[source: captures/right-bottom-compose-promotion-decision-tests-current.md]`,
  and `[source: captures/right-bottom-compose-evidence-matrix-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: broader right-bottom route/input safety remains separate and
  should stay no-popup unless explicitly approved.
- Notes: the promotion-decision tests cover default deferral, missing/failing
  route/grid/timing gates, manual-proof promotion eligibility, explicit
  CDB-only override eligibility, and CLI `--require-pass` failure behavior.
- Notes: the evidence-matrix tests cover required
  route/map/UI/grid-hit/timing/decision gates, hidden-desktop and full-start
  safety, normal visibility proof, candidate SHA agreement, deferred promotion
  status, and CLI `--require-pass` failure behavior.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `right_bottom_compose_promotion_decision_tests: PASS` and
  `right_bottom_compose_evidence_matrix_tests: PASS`; the no-popup boundary
  guard requires both supporting reports.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Castle overview multihit target-done rows

- Source updated: `[source: tools/castle_overview_multihit_summary.py]`,
  `[source: tools/test_castle_overview_multihit_summary.py]`, and
  `[source: captures/castle-overview-multihit-summary-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[Clash95 HD Mod Progress]],
  [[Clash95 Engine Viewport Patch Notes]], and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof remains opt-in and should not
  run on the active desktop without explicit approval.
- Notes: the multi-hit parser now recognizes `CASTLEOV_MULTI_TARGET_DONE`
  rows emitted by the current visible and dormant overview probes and requires
  each target's completion row to match raw, command, callback, and gate
  before `all_targets_ok` can pass.
- Notes: `tools/current_evidence_refresh.py --require-pass` reports
  `castle_overview_multihit_summary_tests: PASS`; regenerated visible and
  dormant multi-hit reports show `completion_ok=True` per target.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Castle overview matrix displayed-wrapper gate

- Source updated: `[source: tools/castle_overview_evidence_matrix.py]`,
  `[source: tools/test_castle_overview_evidence_matrix.py]`, and
  `[source: captures/castle-overview-evidence-matrix-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[Clash95 HD Mod Progress]],
  [[Clash95 Engine Viewport Patch Notes]], and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof remains opt-in and should not
  run on the active desktop without explicit approval.
- Notes: the castle overview evidence matrix now requires
  displayed-wrapper proof in its focused command `0x86` hitbox gate, and its
  fixture tests fail closed if `CASTLEOV_HITBOX_DISPLAYED_WRAPPER_OK` is
  missing from the focused log.
- Notes: `tools/current_evidence_refresh.py --require-pass` reports
  `castle_overview_evidence_matrix_tests: PASS` with `test_count=5`, including
  target-done completion reporting in the visible/dormant multi-hit gates.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Castle overview displayed-wrapper guard

- Source updated: `[source: tools/castle_overview_probe_guard.py]`,
  `[source: tools/test_castle_overview_probe_guard.py]`, and
  `[source: captures/castle-overview-probe-guard-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[Clash95 HD Mod Progress]],
  [[Clash95 Engine Viewport Patch Notes]], and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof remains opt-in and should not
  run on the active desktop without explicit approval.
- Notes: the probe guard now requires
  `CASTLEOV_HITBOX_DISPLAYED_WRAPPER_OK` in the focused CDB script, parser,
  and focused log, proving the displayed coordinate reached the target through
  the binary input wrapper before trusting click-gate proof.
- Notes: `tools/current_evidence_refresh.py --require-pass` reports
  `castle_overview_probe_guard: PASS` with `displayed_wrapper_ok=True`, and
  `castle_overview_probe_guard_tests: PASS`.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Castle overview probe guard focused-log tests

- Source updated: `[source: tools/test_castle_overview_probe_guard.py]`
  and `[source: captures/castle-overview-probe-guard-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[Clash95 HD Mod Progress]],
  [[Clash95 Engine Viewport Patch Notes]], and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof remains opt-in and should not
  run on the active desktop without explicit approval.
- Notes: the probe guard tests now fail closed when the focused hitbox log
  loses ready state, 800x600 main surface proof, 640x480 overview surface
  proof, displayed-hit proof, descriptor proof, click-gate proof, callback
  suppression, or when callback entry/AV rows are present.
- Notes: `tools/current_evidence_refresh.py --require-pass` reports
  `castle_overview_probe_guard_tests: PASS` with `test_count=8`.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Castle owner records summary tests

- Source updated: `[source: tools/test_castle_owner_records_summary.py]`
  and `[source: captures/castle-owner-records-summary-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[No-Popup Surface Dump]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof remains opt-in and should not
  run on the active desktop without explicit approval.
- Notes: `tools/test_castle_owner_records_summary.py` passes repo-only and
  covers active, retired, nonempty, interesting, and flag-value owner records,
  plus no-active, require-interesting, forbid-interesting, and truncated
  raw-dump fail-closed paths.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `castle_owner_records_summary_tests: PASS`; the no-popup boundary guard
  requires this supporting report.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Castle overview hitmap summary tests

- Source updated: `[source: tools/test_castle_overview_hitmap_summary.py]`
  and `[source: captures/castle-overview-hitmap-summary-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[No-Popup Surface Dump]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof remains opt-in and should not
  run on the active desktop without explicit approval.
- Notes: `tools/test_castle_overview_hitmap_summary.py` passes repo-only and
  covers raw command IDs, presence/absence, counts, bounding boxes, centered
  displayed coordinates, required present/absent CLI flags, and wrong
  raw-dimension handling.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `castle_overview_hitmap_summary_tests: PASS`; the no-popup boundary guard
  requires this supporting report.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Castle overview multihit summary tests

- Source updated: `[source: tools/test_castle_overview_multihit_summary.py]`
  and `[source: captures/castle-overview-multihit-summary-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[No-Popup Surface Dump]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof remains opt-in and should not
  run on the active desktop without explicit approval.
- Notes: `tools/test_castle_overview_multihit_summary.py` passes repo-only and
  covers target-set rows, hit-test results, descriptor and click-gate rows,
  target-done completion rows, callback entry, AV rows, ready surface size,
  and required CLI flag failures.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `castle_overview_multihit_summary_tests: PASS`; the no-popup boundary guard
  requires this supporting report.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Castle overview hitbox summary tests

- Source updated: `[source: tools/test_castle_overview_hitbox_summary.py]`
  and `[source: captures/castle-overview-hitbox-summary-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[No-Popup Surface Dump]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof remains opt-in and should not
  run on the active desktop without explicit approval.
- Notes: `tools/test_castle_overview_hitbox_summary.py` passes repo-only and
  covers focused displayed/native hit rows, descriptor and click-gate rows,
  callback suppression/callback entry, AV rows, ready surface size, and
  required CLI flag failures.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `castle_overview_hitbox_summary_tests: PASS`; the no-popup boundary guard
  requires this supporting report.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Castle overview gate tests

- Source updated: `[source: tools/test_castle_overview_gate.py]` and
  `[source: captures/castle-overview-gate-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[No-Popup Surface Dump]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof remains opt-in and should not
  run on the active desktop without explicit approval.
- Notes: `tools/test_castle_overview_gate.py` passes repo-only and covers
  overview readiness, AV rows, overview post-draw/surface-size regressions,
  missing expected commands, centered-geometry regression, barracks baseline
  regression, and JSON/Markdown CLI output plus `--require-pass` failure.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `castle_overview_gate_tests: PASS`; the no-popup boundary guard requires
  this supporting report.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Castle overview evidence matrix tests

- Source updated: `[source: tools/test_castle_overview_evidence_matrix.py]`
  and `[source: captures/castle-overview-evidence-matrix-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[No-Popup Surface Dump]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof remains opt-in and should not
  run on the active desktop without explicit approval.
- Notes: `tools/test_castle_overview_evidence_matrix.py` passes repo-only and
  covers all-checks-pass aggregation, every required component-gate failure,
  validation-stage-only status, and JSON/Markdown CLI output plus
  `--require-pass` failure.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `castle_overview_evidence_matrix_tests: PASS`; the no-popup boundary guard
  requires this supporting report.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Castle overview promotion decision tests

- Source updated: `[source: tools/test_castle_overview_promotion_decision.py]`
  and `[source: captures/castle-overview-promotion-decision-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[No-Popup Surface Dump]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: stable promotion still needs explicit promotion scope;
  manual/visible DirectInput proof remains opt-in and should not run on the
  active desktop without explicit approval.
- Notes: `tools/test_castle_overview_promotion_decision.py` passes repo-only
  and covers the default defer decision, failing-matrix fail-closed behavior,
  missing focused/multihit proof, manual-proof promotion eligibility, explicit
  CDB-only override eligibility, and JSON/Markdown CLI output plus
  `--require-pass` failure.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `castle_overview_promotion_decision_tests: PASS`; the no-popup boundary
  guard requires this supporting report.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Castle overview baseline recheck tests

- Source updated: `[source: tools/test_castle_overview_baseline_recheck.py]`
  and `[source: captures/castle-overview-baseline-recheck-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[No-Popup Surface Dump]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof remains opt-in and should not
  run on the active desktop without explicit approval.
- Notes: `tools/test_castle_overview_baseline_recheck.py` passes repo-only and
  covers stale overview visual baselines, stale barracks controlled-stop
  baselines, failing latest castle overview matrices, missing visible/dormant
  target-done completion proof, and JSON/Markdown output writing.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `castle_overview_baseline_recheck_tests: PASS`; the no-popup boundary guard
  requires this supporting report.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Stable stage guard tests

- Source updated: `[source: tools/test_stable_stage_guard.py]` and
  `[source: captures/stable-stage-guard-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[No-Popup Surface Dump]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: stable promotion still needs explicit promotion scope and
  manual/visible input proof remains opt-in.
- Notes: `tools/test_stable_stage_guard.py` passes repo-only and covers
  patcher-default drift, validation-only group leakage into stable, missing
  `castlecenter-all` validation groups, promotion decisions that would change
  stable, stale castle promotion decisions or evidence matrices without
  focused/multihit proof, and CLI `--require-pass` fail-closed behavior.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `stable_stage_guard_tests: PASS`; the no-popup boundary guard requires this
  supporting report.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Castle overview baseline recheck

- Source updated: `[source: tools/castle_overview_baseline_recheck.py]` and
  `[source: captures/castle-overview-baseline-recheck-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[Clash95 HD Mod Progress]],
  [[Clash95 Engine Viewport Patch Notes]], and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof remains opt-in and should not
  run on the active desktop without explicit approval.
- Notes: `tools/castle_overview_baseline_recheck.py` passes repo-only and
  checks `captures/cdb-surface-dump-20260512-101803`,
  `captures/cdb-surface-dump-20260512-082418`, and the latest
  `castlecenter-all` matrix.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `castle_overview_baseline_recheck: PASS`.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | No-popup guard regression tests

- Source updated: `[source: tools/test_no_popup_guards.py]` and
  `[source: captures/no-popup-guard-tests-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[No-Popup Surface Dump]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: none for these tests; broader right-bottom route/input
  safety remains separate and should stay no-popup unless explicitly approved.
- Notes: `tools/test_no_popup_guards.py` covers each missing boundary link,
  missing refresh checks, failed refresh checks, each missing supporting
  refresh check, and surface-dump launcher policy drift.
- Notes: the test passed without launching Clash95, CDB, wrappers, PowerShell,
  or any visible GUI process.
- Notes: `tools/current_evidence_refresh.py --require-pass` now includes
  `no_popup_guard_tests: PASS`.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | No-popup boundary guard

- Source updated: `[source: captures/no-popup-boundary-guard-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[No-Popup Surface Dump]], and [[Log]].
- Contradictions: none recorded.
- Open questions: none for this guard; broader right-bottom route/input safety
  remains separate and should stay no-popup unless explicitly approved.
- Notes: `tools/no_popup_boundary_guard.py` now passes repo-only and verifies
  that the current refresh includes the stable-stage, executable-artifact,
  surface-dump-policy, no-visible-runtime, and process-hygiene guards, plus
  the no-popup guard tests, castle overview baseline recheck, and castle
  overview probe guard reports.
- Notes: it also verifies that the current evidence index links each required
  report.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Surface dump policy guard

- Source updated: `[source: captures/surface-dump-policy-guard-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[No-Popup Surface Dump]], and [[Log]].
- Contradictions: none recorded.
- Open questions: none for this guard; broader right-bottom route/input safety
  remains separate and should stay no-popup unless explicitly approved.
- Notes: `tools/surface_dump_policy_guard.py` now passes repo-only and checks
  that `run_cdb_surface_dump.ps1` defaults to hidden desktop and requires
  explicit `-AllowVisibleDesktop` for active-desktop fallback.
- Notes: `run_cdb_surface_dump.ps1` now records `HiddenDesktop` and
  `AllowVisibleDesktop` in early failure and final summaries.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Process hygiene guard

- Source updated: `[source: captures/process-hygiene-guard-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[No-Popup Surface Dump]], and [[Log]].
- Contradictions: none recorded.
- Open questions: none for this guard; broader right-bottom route/input safety
  remains separate and should stay no-popup unless explicitly approved.
- Notes: `tools/process_hygiene_guard.py` now passes with
  `matching_process_count=0` for `cdb.exe` and `clash95*`.
- Notes: the guard uses a Windows Toolhelp process snapshot and launches no
  game, debugger, wrapper, shell helper, or visible GUI window.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | No-visible runtime guard

- Source updated: `[source: captures/no-visible-runtime-guard-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], and [[Log]].
- Contradictions: none recorded.
- Open questions: none for this guard; broader right-bottom route/input safety
  remains separate and should stay no-popup unless explicitly approved.
- Notes: `tools/no_visible_runtime_guard.py` now passes repo-only with `18`
  referenced CDB surface-dump runs and all `18` reporting
  `LaunchMode=hidden-desktop` plus `HiddenDesktop=True`.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-14] maintenance | Executable artifact guard

- Source updated: `[source: captures/exe-artifact-guard-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], and [[Log]].
- Contradictions: none recorded.
- Open questions: none for this hygiene guard; manual/real DirectInput proof
  remains separate and opt-in.
- Notes: `tools/exe_artifact_guard.py` now passes repo-only with `0`
  filesystem `.exe` files, `0` git-index `.exe` files,
  `allowed_staged_deletions=28`, and the root `.exe` ignore rule present.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-13] maintenance | Stable stage guard

- Source updated: `[source: captures/stable-stage-guard-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Active HD Map Stage]],
  [[Current Clash95 HD State]], and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof remains required before
  promoting validation-only castle or right-bottom groups into the stable HD
  map stage.
- Notes: `tools/stable_stage_guard.py` now passes repo-only and confirms
  validation-only groups are absent from the default stable dynvswitch stage.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-13] maintenance | Right-bottom evidence matrix

- Source updated: `[source: reports/border-tooltip-cdb-validation.md]`,
  `[source: reports/bottom-tooltip-recovery.md]`,
  `[source: captures/hd-map-evidence-current.md]`, and
  `[source: captures/right-bottom-compose-evidence-current.md]`.
- Pages updated: [[Current HD Map Evidence]],
  [[Border And Bottom Tooltip Recovery Reports]],
  [[Right-Bottom UI And Bottom Tooltip Recovery]],
  [[How Should The Bottom Tooltip Be Recovered]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]],
  [[Current Clash95 HD State]], [[HD Map Evidence Chain]], and [[Log]].
- Contradictions: none recorded.
- Open questions: broader route/input safety or approved manual proof remains
  necessary before stable-stage promotion.
- Notes: `tools/right_bottom_compose_evidence_matrix.py` records
  `overall=PASS`, `promotion_status=validation_stage_only`,
  `stable_stage_should_change=False`, and all required right-bottom validation
  checks passing.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-13] maintenance | Right-bottom promotion decision

- Source updated: `[source: reports/border-tooltip-cdb-validation.md]`,
  `[source: reports/bottom-tooltip-recovery.md]`,
  `[source: captures/hd-map-evidence-current.md]`, and
  `[source: captures/right-bottom-compose-promotion-decision-current.md]`.
- Pages updated: [[Current HD Map Evidence]],
  [[Border And Bottom Tooltip Recovery Reports]],
  [[Right-Bottom UI And Bottom Tooltip Recovery]],
  [[How Should The Bottom Tooltip Be Recovered]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]],
  [[Current Clash95 HD State]], [[HD Map Evidence Chain]], and [[Log]].
- Contradictions: none recorded.
- Open questions: broader route/input safety or approved manual proof remains
  necessary before stable-stage promotion.
- Notes: `tools/right_bottom_compose_promotion_decision.py` records
  `decision=defer_stable_promotion`, `stable_stage_should_change=False`, and
  all required right-bottom validation checks passing.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-13] maintenance | Right-bottom validation patch full-start route

- Source updated: `[source: reports/border-tooltip-cdb-validation.md]`,
  `[source: reports/bottom-tooltip-recovery.md]`,
  `[source: captures/hd-map-evidence-current.md]`, and
  `[source: captures/current-evidence-refresh-current.md]`.
- Pages updated: [[Current HD Map Evidence]],
  [[Border And Bottom Tooltip Recovery Reports]],
  [[Right-Bottom UI And Bottom Tooltip Recovery]],
  [[How Should The Bottom Tooltip Be Recovered]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]],
  [[Current Clash95 HD State]], [[HD Map Evidence Chain]], and [[Log]].
- Contradictions: none recorded.
- Open questions: broader route/input safety still blocks stable-stage
  promotion of the right-bottom validation patch.
- Notes: hidden-desktop run `captures/cdb-surface-dump-20260513-122928`
  passed the full-start controlled owner/action route on the
  `rightbottomcompose` validation stage with candidate SHA
  `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`,
  `ready=True`, `av_count=0`, `bottom_right_ui_corner=48.228%`,
  `r8c10=54.102%`, and `r8c11=42.822%`.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-13] maintenance | Right-bottom validation patch natural UI probe

- Source updated: `[source: reports/border-tooltip-cdb-validation.md]`,
  `[source: reports/bottom-tooltip-recovery.md]`,
  `[source: captures/hd-map-evidence-current.md]`, and
  `[source: captures/current-evidence-refresh-current.md]`.
- Pages updated: [[Current HD Map Evidence]],
  [[Border And Bottom Tooltip Recovery Reports]],
  [[Right-Bottom UI And Bottom Tooltip Recovery]],
  [[How Should The Bottom Tooltip Be Recovered]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]],
  [[Current Clash95 HD State]], [[HD Map Evidence Chain]], and [[Log]].
- Contradictions: none recorded.
- Open questions: final promotion still needs broader route/input timing safety
  because natural gameplay routing does not enter the owner/action draw rows.
- Notes: hidden-desktop run `captures/cdb-surface-dump-20260513-122200`
  passed the right-bottom UI launcher on the `rightbottomcompose` validation
  stage with `RBUI_DESC_SWITCH=35`, `RBUI_VIEWPORT_SWITCH=1`,
  `RBUI_PANEL_DRAW=0`, `RBUI_ACTION_BOX=0`, and candidate SHA
  `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-13] maintenance | Right-bottom validation patch normal gate

- Source updated: `[source: reports/border-tooltip-cdb-validation.md]`,
  `[source: reports/bottom-tooltip-recovery.md]`,
  `[source: captures/hd-map-evidence-current.md]`, and
  `[source: captures/current-evidence-refresh-current.md]`.
- Pages updated: [[Current HD Map Evidence]],
  [[Border And Bottom Tooltip Recovery Reports]],
  [[Right-Bottom UI And Bottom Tooltip Recovery]],
  [[How Should The Bottom Tooltip Be Recovered]],
  [[Clash95 HD Mod Progress]], [[Clash95 Engine Viewport Patch Notes]],
  [[Current Clash95 HD State]], [[HD Map Evidence Chain]], and [[Log]].
- Contradictions: none recorded.
- Open questions: route/input safety still blocks stable-stage promotion of
  the validation patch.
- Notes: hidden-desktop run `captures/cdb-surface-dump-20260513-121513`
  passed the normal map/visibility gate for `rightbottomcompose` with candidate
  SHA `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`,
  an 800x600 gameplay-like surface, `108` active cells, `13` visibility-zero
  blank cells, and zero unexplained blanks.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-13] maintenance | Right-bottom validation patch proof

- Source updated: `[source: reports/border-tooltip-cdb-validation.md]`,
  `[source: reports/bottom-tooltip-recovery.md]`,
  `[source: captures/hd-map-evidence-current.md]`, and
  `[source: captures/current-evidence-refresh-current.md]`.
- Pages updated: [[Current HD Map Evidence]],
  [[Border And Bottom Tooltip Recovery Reports]],
  [[Right-Bottom UI And Bottom Tooltip Recovery]],
  [[How Should The Bottom Tooltip Be Recovered]],
  [[Current Clash95 HD State]], [[HD Map Evidence Chain]], and [[Log]].
- Contradictions: none recorded.
- Open questions: broader safety and route/input coverage are still needed
  before promoting the right-bottom validation patch into the stable HD map
  stage.
- Notes: hidden-desktop run `captures/cdb-surface-dump-20260513-120712`
  passed with the validation-only `rightbottomcompose` stage,
  `right-bottom-compose-proof=4/4`, candidate SHA
  `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`,
  `av_count=0`, and bottom-right recovery matching the debugger proof.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-13] maintenance | Right-bottom debugger composition proof

- Source updated: `[source: reports/border-tooltip-cdb-validation.md]`,
  `[source: reports/bottom-tooltip-recovery.md]`,
  `[source: captures/hd-map-evidence-current.md]`, and
  `[source: captures/current-evidence-refresh-current.md]`.
- Pages updated: [[Current HD Map Evidence]],
  [[Border And Bottom Tooltip Recovery Reports]],
  [[Right-Bottom UI And Bottom Tooltip Recovery]],
  [[How Should The Bottom Tooltip Be Recovered]],
  [[What Owns The Gameplay Border Frame]], [[Clash95 HD Mod Progress]],
  [[Current Clash95 HD State]], [[HD Map Evidence Chain]], and [[Log]].
- Contradictions: none recorded.
- Open questions: implement the proven final-copy strategy as a narrow
  validation-stage binary patch before considering any stable-stage promotion.
- Notes: hidden-desktop run `captures/cdb-surface-dump-20260513-115303`
  passed with `-SkipMapValidation`, all `APCOMPOSE_*` markers, `av_count=0`,
  and bottom-right recovery from `21.43%` to `48.228%` nonblack.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-13] maintenance | Right-bottom action-box composition proof

- Source updated: `[source: reports/border-tooltip-cdb-validation.md]`,
  `[source: reports/bottom-tooltip-recovery.md]`, and
  `[source: captures/current-evidence-refresh-current.md]`.
- Pages updated: [[Border And Bottom Tooltip Recovery Reports]],
  [[Right-Bottom UI And Bottom Tooltip Recovery]],
  [[How Should The Bottom Tooltip Be Recovered]],
  [[What Owns The Gameplay Border Frame]], [[Current HD Map Evidence]],
  [[Clash95 HD Mod Progress]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], [[Index]], and [[Log]].
- Contradictions: none recorded.
- Open questions: right-bottom recovery now needs a narrow native-anchor or
  final-composition strategy around `00435280` / `00435500`.
- Notes: hidden-desktop run `captures/cdb-surface-dump-20260513-112339`
  passed with `-SkipMapValidation`, reached the owner/action route, logged
  native-positioned action/status rows, recorded `13` text rows, `0` final
  present rows, `5` null-destination present rows, `2` composition sample rows,
  and `av_count=0`.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-13] maintenance | Right-bottom owner route proof

- Source updated: `[source: reports/border-tooltip-cdb-validation.md]` and
  `[source: captures/current-evidence-refresh-current.md]`.
- Pages updated: [[Border And Bottom Tooltip Recovery Reports]],
  [[Right-Bottom UI And Bottom Tooltip Recovery]],
  [[How Should The Bottom Tooltip Be Recovered]],
  [[What Owns The Gameplay Border Frame]], [[Current HD Map Evidence]],
  [[Current Clash95 HD State]], [[HD Map Evidence Chain]], and [[Log]].
- Contradictions: none recorded.
- Open questions: right-bottom panel composition still needs
  render-target/copyback, anchor, or final-present proof.
- Notes: hidden-desktop run `captures/cdb-surface-dump-20260513-105411`
  passed with `-SkipMapValidation`, reached the action/status draw cluster,
  action-box redirect, copyback, and `SURFDUMP_READY`, and recorded
  `av_count=0`.
- Notes: no visible Clash window was used; `raw/` was not edited or
  reorganized.

## [2026-05-13] maintenance | Right-bottom UI launcher proof

- Source updated: `[source: reports/border-tooltip-cdb-validation.md]`.
- Pages updated: [[Border And Bottom Tooltip Recovery Reports]],
  [[Right-Bottom UI And Bottom Tooltip Recovery]],
  [[How Should The Bottom Tooltip Be Recovered]],
  [[What Owns The Gameplay Border Frame]], [[Current HD Map Evidence]], and
  [[Log]].
- Contradictions: none recorded.
- Open questions: route/state activation for the `004347A0..00435500`
  action/status owner path remains.
- Notes: hidden-desktop run `captures/cdb-surface-dump-20260513-104200`
  reached gameplay, `RBUI_DESC_SWITCH=26`, and `RBUI_VIEWPORT_SWITCH=1`, but
  `RBUI_PANEL_DRAW=0` and `RBUI_ACTION_BOX=0`.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-13] maintenance | Current evidence refresh

- Source updated: `[source: captures/hd-map-evidence-current.md]` and
  `[source: captures/current-evidence-refresh-current.md]`.
- Pages updated: [[Current HD Map Evidence]], [[Current Clash95 HD State]],
  [[HD Map Evidence Chain]], and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof remains opt-in and should not
  run on the active desktop without explicit approval.
- Notes: `tools/current_evidence_refresh.py --require-pass` now refreshes the
  HD map smoke matrix, patch-manifest comparison, evidence-index check,
  barracks success-branch proof, right-bottom UI probe, right-bottom owner
  route proof, castle overview evidence matrix, and castle overview promotion
  decision.
- Notes: current refresh result is `PASS` and does not launch Clash95, CDB,
  wrappers, or visible windows.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-13] maintenance | Castle overview promotion decision

- Source updated: `[source: reports/castle-barracks-ui-cdb-validation.md]`.
- Pages updated: [[Castle Barracks UI CDB Validation]], [[Castle UI Centering State]],
  [[Which Castle Overview Path Needs Centering]],
  [[What Manual DirectInput Validation Remains]], and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof remains opt-in and should not
  run on the active desktop without explicit approval.
- Notes: `tools/castle_overview_promotion_decision.py` records
  `decision=defer_stable_promotion` and
  `stable_stage_should_change=False`.
- Notes: the patcher default stable HD map stage remains unchanged, and castle
  overview wrappers remain scoped to `castlecenter-all`.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-14] maintenance | Castle overview focused hitbox refresh

- Source updated: `[source: captures/cdb-surface-dump-20260514-130015]`.
- Pages updated: [[Log]], [[Current Clash95 HD State]].
- Contradictions: none recorded.
- Open questions: keep castle overview wrappers scoped to `castlecenter-all`
  until manual/real input proof or an explicit CDB-only promotion decision is
  accepted.
- Notes: the focused `0x86` overview hitbox was rerun through the no-popup
  hidden-desktop CDB surface-dump harness with no `-AllowVisibleDesktop`;
  displayed `(371,107)` reached raw hit `248`, command `0x86`, callback
  `0044FE70`, click gate `1`, and `av_count=0`.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-13] maintenance | Castle overview evidence matrix

- Source updated: `[source: reports/castle-barracks-ui-cdb-validation.md]`.
- Pages updated: [[Castle Barracks UI CDB Validation]], [[Castle UI Centering State]],
  [[Which Castle Overview Path Needs Centering]],
  [[What Manual DirectInput Validation Remains]], and [[Log]].
- Contradictions: none recorded.
- Open questions: deliberate promotion decision before moving castle overview
  wrappers out of `castlecenter-all`.
- Notes: `tools/castle_overview_evidence_matrix.py` now provides a repo-only
  no-popup gate and passes with `promotion_status=validation_stage_only`.
- Notes: visible/manual overview input proof should not run on the active
  desktop without explicit approval.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-13] maintenance | Castle overview multi-hit proof

- Source updated: `[source: reports/castle-barracks-ui-cdb-validation.md]`.
- Pages updated: [[Castle Barracks UI CDB Validation]], [[Castle UI Centering State]],
  [[Current Clash95 HD State]], [[Which Castle Overview Path Needs Centering]],
  [[What Manual DirectInput Validation Remains]], and [[Log]].
- Contradictions: none recorded.
- Open questions: manual/real DirectInput proof or an explicit promotion
  decision before moving castle overview wrappers out of `castlecenter-all`.
- Notes: CDB/proxy proof now covers dormant overview commands `0x99`, `0x9C`,
  `0x9F`, and `0xA6` via a labeled debugger-forced owner-feature state.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-12] maintenance | Castle overview hitbox proof

- Source updated: `[source: reports/castle-barracks-ui-cdb-validation.md]`.
- Pages updated: [[Castle Barracks UI CDB Validation]], [[Castle UI Centering State]],
  [[Which Castle Overview Path Needs Centering]], and [[Log]].
- Contradictions: none recorded.
- Open questions: broader/manual full-overview input proof before promotion.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-12] maintenance | Clash95 knowledge-base synthesis

- Sources summarized: `[source: CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md]`,
  `[source: HD_MOD_PROGRESS.md]`, `[source: CLASH95_MENU_LOAD_ROUTE_NOTES.md]`,
  `[source: captures/hd-map-evidence-current.md]`,
  `[source: captures/hd-map-smoke-current.md]`,
  `[source: captures/post-owner-evidence-current.md]`,
  `[source: reports/border-frame-recovery.md]`,
  `[source: reports/border-tooltip-cdb-validation.md]`,
  `[source: reports/bottom-tooltip-recovery.md]`, and
  `[source: reports/castle-barracks-ui-cdb-validation.md]`.
- Pages created: [[Clash95 Engine Viewport Patch Notes]], [[Clash95 HD Mod Progress]],
  [[Clash95 Menu Load Route Notes]], [[Current HD Map Evidence]],
  [[Border And Bottom Tooltip Recovery Reports]],
  [[Castle Barracks UI CDB Validation]], [[Active HD Map Stage]],
  [[CDB-Only Validation]], [[No-Popup Surface Dump]],
  [[Visibility-Zero Versus Rendering Defect]], [[Dynamic-Origin Mouse Input]],
  [[Centered UI Coordinate Transform]], [[DirectDraw Surface Target Split]],
  [[Current Clash95 HD State]], [[HD Map Evidence Chain]],
  [[Right-Bottom UI And Bottom Tooltip Recovery]],
  [[Castle UI Centering State]], [[What Owns The Gameplay Border Frame]],
  [[How Should The Bottom Tooltip Be Recovered]],
  [[Which Castle Overview Path Needs Centering]], and
  [[What Manual DirectInput Validation Remains]].
- Pages updated: [[Index]], [[Log]].
- Contradictions: none recorded.
- Open questions: gameplay border owner, bottom-tooltip recovery design,
  castle overview centering path, and remaining manual DirectInput validation.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-15] maintenance | Battle UI catalog smoke

- Source updated: `[source: reports/battle_ui_catalog_probe_20260515.md]`.
- Pages updated: [[Log]].
- Contradictions: none recorded.
- Open questions: deterministic no-popup battle-entry route before any
  `battle-ui-*` patch group.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-17] maintenance | Right-bottom action native-center strict probe

- Source updated: `[source: captures/right-bottom-action-nativecenter-current.md]`.
- Pages updated: [[Log]].
- Contradictions: none recorded.
- Open questions: natural route/input proof still must enter the owner/action
  draw cluster before the right-bottom action-menu visual fix can be promoted.
- Notes: `rightbottomaction-nativecenter` keeps the controlled action-screen
  visual fix and candidate SHA
  `D3FF331FD6A7B10A91C55A55FF891685CFAC376917816557B40A483EBDBC569C`.
- Notes: the strict fast-forward natural UI run
  `captures/cdb-surface-dump-20260517-163734` passed the hidden map dump and
  visibility gate, but failed the right-bottom UI gate with
  `OwnerActionRowsSeen=false`, `RBUI_PANEL_DRAW=0`, and `RBUI_ACTION_BOX=0`.
- Notes: wrapper-aware controlled run
  `captures/cdb-surface-dump-20260517-172611` passed with
  `clash95_post_owner_action_nativecenter_extra.cdb`; it proves stock
  `00435BC0` drew on a temporary 640x480 surface and the wrapper copied the
  native action screen back to an 800x600 surface at `0051B86D`.
- Notes: unit-selection evidence at
  `captures/cdb-surface-dump-20260517-171559` is tracked as a separate
  selected-unit info/action route, not as right-bottom owner/action proof.
- Notes: `run_cdb_right_bottom_ui_probe.ps1` now requires owner/action rows by
  default; descriptor-only diagnostics require `-AllowDescriptorOnly`.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-18] maintenance | Natural castle-click route split

- Source updated: `[source: captures/right-bottom-action-nativecenter-current.md]`.
- Pages updated: [[Log]].
- Contradictions: none recorded.
- Open questions: the natural route still must drive castle overview command
  `0x63` or equivalent owner setup into `004338E0 -> 00435BC0` before the
  right-bottom action-menu visual fix can be promoted.
- Notes: focused hidden-desktop run
  `captures/cdb-surface-dump-20260518-092756` passed with candidate SHA
  `D3FF331FD6A7B10A91C55A55FF891685CFAC376917816557B40A483EBDBC569C`.
- Notes: `clash95_building_click_route_extra.cdb` forces the live
  map-handler call site at `0040B233` to screen `(352,272)` / map `(15,21)`,
  reaches castle tile `32768`, building index `0`, owner `0`, mode `2`,
  active `0`, and follows
  `sub_4084A0 -> Building_GetInto -> 00422180`.
- Notes: the run dumps a 640x480 castle overview surface at
  `captures/cdb-surface-dump-20260518-092756/surface.png`; it does not produce
  owner/action rows for `004338E0`, `00433914`, or `00435BC0`.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-18] maintenance | Castle command 0x63 owner setup split

- Source updated: `[source: captures/right-bottom-action-nativecenter-current.md]`.
- Pages updated: [[Log]].
- Contradictions: none recorded.
- Open questions: the natural route still needs the second right-bottom
  descriptor input after command `0x63` to enter `004338E0 -> 00433914 ->
  0051B7E0`.
- Notes: focused hidden-desktop run
  `captures/cdb-surface-dump-20260518-100917` passed with candidate SHA
  `D3FF331FD6A7B10A91C55A55FF891685CFAC376917816557B40A483EBDBC569C`.
- Notes: `clash95_castle_click_cmd99_to_action_extra.cdb` drives the natural
  castle-click route through overview raw hit `254`, command `99`, callback
  `00433C20`, and verifies writes to `dword_532150`, `dword_53214C`, and
  `dword_532154`.
- Notes: after owner setup, the first map-loop `00511D40` descriptor scan
  reports `result=0`, `d532218=00000000`, and no action-wrapper rows, so
  command `0x63` is owner-state setup rather than the action-screen opener by
  itself.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-18] maintenance | Battle UI force-entry and initial centering

- Source updated: `[source: captures/battle-ui-force-entry-current.md]`.
- Pages updated: [[Log]].
- Contradictions: none recorded.
- Open questions: battle command-button hits, tactical-grid hits,
  modal/dialog routing, and later battle-loop redraw centering still need
  runtime proof.
- Notes: the user-visible stripey/right-bottom button screenshot was traced to
  the battle UI lane, not the castle owner/action menu lane.
- Notes: baseline hidden-desktop run
  `captures/cdb-surface-dump-20260518-214535` reaches forced `Unit_Attack`,
  `BATTLE_OWNER_ENTRY source=BattleRunner`, and the bad uncentered 800x600
  battle composition.
- Notes: patched hidden-desktop run
  `captures/cdb-surface-dump-20260518-221018` uses CDB `.writemem`, logs
  wrapper return `0051ba63`, has no access violations, and classifies the
  initial battle frame as `centered-native-640x480` at offset `[80, 60]`.
- Notes: `battle-ui-center-present-wrapper` patches only initial battle
  `Render_Present` callsite `0042F2F5` to cave `0051BA00`; broad battle
  present wrapping remains unpromoted because earlier broad wrapping produced
  redraw artifacts.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-20] evidence | Battle UI command descriptor hit

- Source updated: `[source: captures/battle-ui-command-hit-current.md]`.
- Pages updated: [[Log]].
- Contradictions: none recorded.
- Open questions: command callback/manual cadence, tactical-grid hits,
  modal/dialog routing, and later battle-loop redraw centering still need
  runtime proof.
- Notes: hidden-desktop run
  `captures/cdb-surface-dump-20260520-094032` extends the forced battle route
  with controlled command descriptor probing.
- Notes: the run logs `BATTLE_COMMAND_HIT coord_mode=visual result=2` for the
  displayed command coordinate and `BATTLE_COMMAND_NATIVE_HIT
  coord_mode=native result=2` for the native coordinate, with no AV rows.
- Notes: the proof is harnessed: it controls mouse globals and skips turn
  banner/frame waits. It should not be treated as natural/manual click
  validation yet.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-20] evidence | Battle UI command callback entry

- Source updated: `[source: captures/battle-ui-command-callback-current.md]`.
- Pages updated: [[Log]].
- Contradictions: none recorded.
- Open questions: enabled-command state change, manual input cadence,
  tactical-grid hits, modal/dialog routing, and later battle-loop redraw
  centering still need runtime proof.
- Notes: hidden-desktop run
  `captures/cdb-surface-dump-20260520-100717` extends the forced battle route
  with a command callback probe.
- Notes: the run reaches descriptor `00514b78`, forces the descriptor click
  gate, enters callback `0042d4e0`, and records
  `BATTLE_COMMAND_CALLBACK_RESULT branch=precondition-disabled`.
- Notes: the disabled branch reports `unit_index=0`, `unit_type=5`,
  `avail=8`, and `enabled=0`, so it proves callback entry but not an enabled
  command state transition.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-20] evidence | Battle UI enabled command callback result

- Source updated: `[source: captures/battle-ui-command-enabled-callback-current.md]`.
- Pages updated: [[Log]].
- Contradictions: none recorded.
- Open questions: natural/manual enabled-command cadence, tactical-grid hits,
  modal/dialog routing, and later battle-loop redraw centering still need
  runtime proof.
- Notes: hidden-desktop run
  `captures/cdb-surface-dump-20260520-101859` extends the forced battle route
  with an enabled-command callback proof.
- Notes: the probe temporarily changes selected unit type `5` to `8`, records
  `avail=10`, `enabled=3`, skips the callback render-begin lock under CDB, and
  reaches `BATTLE_COMMAND_CALLBACK_RESULT branch=state2`.
- Notes: this is still harness evidence, not natural/manual input validation.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-20] evidence | Battle UI tactical-grid coordinate classification

- Source updated: `[source: captures/battle-ui-grid-hit-current.md]`.
- Pages updated: [[Log]].
- Contradictions: none recorded.
- Open questions: natural/manual enabled-command cadence, actual grid-input
  transform, modal/dialog routing, and later battle-loop redraw centering still
  need runtime proof.
- Notes: hidden-desktop run
  `captures/cdb-surface-dump-20260520-103155` extends the forced battle route
  with tactical-grid hit-test probing.
- Notes: the probe reaches `0042CB50`, records displayed `(144,108)` landing
  in cell `(1,1)`, records native `(64,48)` landing in cell `(0,0)`, and has no
  AV rows.
- Notes: this is coordinate-classification evidence. It proves the live grid
  hit-test route and the need for a centered-input transform, not a complete
  battle action or natural/manual input validation.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-20] evidence | Battle UI modal input path classification

- Source updated: `[source: captures/battle-ui-modal-classified-current.md]`.
- Pages updated: [[Log]].
- Contradictions: none recorded.
- Open questions: natural/manual enabled-command cadence, actual centered
  input transforms, and post-ready battle-loop redraw centering still need
  runtime proof.
- Notes: hidden-desktop run
  `captures/cdb-surface-dump-20260520-103714` extends the forced battle route
  with modal/input path classification.
- Notes: the probe reaches battle loop input updater `004605D0`, records
  `BATTLE_MODAL_CLASSIFIED status=input_update_seen_no_modal`, and has no AV
  rows.
- Notes: this is a no-hit classification for the current route. It does not
  prove a separate modal dialog hit or natural/manual input validation.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-20] evidence | Battle UI combined evidence matrix

- Source updated: `[source: captures/battle-ui-evidence-current.md]`.
- Pages updated: [[Log]].
- Contradictions: none recorded.
- Open questions: natural/manual enabled-command cadence, centered-input
  wrapper mechanics, and post-ready battle-loop redraw centering still need
  runtime proof.
- Notes: added `tools/battle_ui_evidence_matrix.py` and
  `tools/test_battle_ui_evidence_matrix.py`.

## [2026-05-20] evidence | Battle UI centered input wrappers

- Source updated: `[source: captures/battle-ui-centered-input-current.md]`.
- Related source: `[source: captures/cdb-surface-dump-20260520-111115/RUN-SUMMARY.md]`.
- Claim: the validation-only `battlecenter-inputprobe` stage proves the battle
  grid and descriptor centered-input wrappers transform visual mouse
  coordinates to native coordinates and restore them afterward.
- Evidence:
  `captures/cdb-surface-dump-20260520-111115` passed hidden-desktop with
  candidate SHA
  `F84933776944E2B616F6BBCCF7708ABBF06498D5438FA8DF7B7AF1BB56CD180A`,
  `SURFDUMP_READY`, no AV rows, and a fresh 800x600 surface dump.
- Notes: `battle-grid-centered-input` wraps `0042E4ED -> 0042CB50` through
  cave `0051BAA0`; `battle-ui-centered-input` wraps `0042E501 -> 00419DC0`
  through cave `0051BAF0`. The focused probe skips helper bodies after entry,
  so natural/manual input cadence remains open.
- Follow-up: refreshed `[source: captures/battle-ui-evidence-current.md]` so
  the combined matrix includes the inputprobe summary and inputprobe
  patch-stage bytes.
- Notes: the matrix passes with no failures and combines force-entry
  centering, command hit/callback, enabled callback, tactical-grid coordinate
  classification, centered-input wrapper proof, modal no-hit classification,
  patch-stage bytes, and stable HD-map smoke evidence.
- Notes: this is a validation-stage checkpoint, not stable promotion or
  natural/manual input validation.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-20] evidence | Battle UI post-ready redraw

- Source updated: `[source: captures/battle-ui-post-ready-redraw-current.md]`.
- Related source: `[source: captures/cdb-surface-dump-20260520-195244/RUN-SUMMARY.md]`.
- Claim: the forced hidden-desktop battle route keeps producing centered
  800x600 post-ready present/copyback activity after the initial battle
  present.
- Evidence:
  `captures/cdb-surface-dump-20260520-195244` passed hidden-desktop with
  candidate SHA
  `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF`,
  `BATTLE_READY`, 9 post-ready presents, 6 post-ready copybacks, one forced
  grid point `(144,108)->(64,48)`, final present return `0042CB46`, no AV
  rows, and a fresh 800x600 surface dump.
- Follow-up: refreshed `[source: captures/battle-ui-evidence-current.md]` so
  the combined matrix includes `post_ready_redraw: PASS`.
- Open questions: natural/manual enabled-command cadence and stable-stage
  battle promotion remain open.
- Notes: this is validation evidence from a forced CDB route, not natural
  gameplay proof.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-20] evidence | Battle command availability scan

- Source updated: `[source: captures/battle-command-availability-current.md]`.
- Related source: `[source: captures/cdb-surface-dump-20260520-195244/RUN-SUMMARY.md]`.
- Claim: the current forced battle fixture does not contain a naturally enabled
  command unit, which explains why the enabled callback proof requires the CDB
  type-8 override.
- Evidence: 18 natural unit records were parsed. The selected unit is type `5`
  with `availability=8` and `enabled=0`; all unit types present in the fixture
  have `enabled=0`. The executable table scan through unit type `31` finds 11
  enabled unit types to hunt for in a richer fixture: Dragon cavalry, Archer,
  Crossbower, Musketeer, Catapult, Cannon, Forester, Cyklop, Wizard, Winger,
  and Dragon.
- Follow-up: refreshed `[source: captures/battle-ui-evidence-current.md]` so
  the combined matrix includes `availability_scan: PASS`.
- Open questions: find a richer natural battle state with enabled commands, or
  capture manual cadence in a state that naturally exposes one.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-20] evidence | Battle save-slot command-state scan

- Source updated: `[source: captures/battle-slot-scan-current.md]`.
- Related sources: `[source: run_cdb_surface_dump.ps1]`,
  `[source: clash95_surface_dump_probe.cdb]`,
  `[source: probes/cdb/battle/clash95_battle_unit_scan_extra.cdb]`,
  `[source: tools/battle_slot_scan_summary.py]`.
- Claim: the current local save slots do not contain a naturally enabled
  command unit for the battle UI proof.
- Evidence: six save-slot attempts were aggregated. Slots `0`, `1`, and `2`
  routed far enough to expose unit rows, with natural enabled command unit
  count `0`; slots `3`, `4`, and `5` timed out before unit scan under the
  current hidden CDB route.
- Follow-up: refreshed `[source: captures/battle-ui-evidence-current.md]` so
  the combined matrix includes `slot_scan: PASS`.
- Open questions: find or construct a richer battle state with enabled command
  units, or capture manual cadence in such a state.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-20] evidence | Battle save-file unit inventory

- Source updated: `[source: captures/battle-save-unit-inventory-current.md]`.
- Related source: `[source: tools/battle_save_unit_inventory.py]`.
- Claim: direct save-file parsing confirms the current local saves do not
  contain naturally enabled battle command units.
- Evidence: the save unit layout starts at `0x00023EF6`, 16 bytes after the
  runtime game-data unit offset `0x00023EE6`. The inventory reads all six
  `C:\Clash\save\*.dat` files, parses 63 units, and reports
  `natural_enabled_unit_count=0`. The decoded local-save unit types are
  Peasant, Light infantry, Light cavalry, Highlander, and Builder.
- Follow-up: refreshed `[source: captures/battle-ui-evidence-current.md]` so
  the combined matrix includes `save_inventory: PASS`.
- Open questions: obtain or construct a richer battle state with enabled unit
  types, then replace the current type-8 CDB override with natural/manual
  command cadence proof.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-20] evidence | Battle constructed save fixture

- Source updated: `[source: captures/battle-constructed-save-fixture-current.md]`.
- Related sources: `[source: tools/battle_constructed_save_fixture.py]`,
  `[source: captures/battle-constructed-fixture-unit-scan-current.md]`, and
  `[source: captures/cdb-surface-dump-20260520-210816/RUN-SUMMARY.md]`.
- Claim: an isolated copied-save fixture can load a naturally enabled battle
  command unit without editing `C:\Clash\save`.
- Evidence: unit index `0` in `C:\Clash\save\0.dat` has type offset
  `0x00023EFC`; changing Light cavalry (`enabled=0`) to Dragon cavalry
  (`enabled=3`) produces patched SHA-256
  `278126F248C5F7A84F396EEBF25F37B21948968557571838CF73462EDFD39CDC`. The
  copied save was written to
  `C:\ClashTests\battle-enabled-fixture-20260520-210728\game\save\0.dat`.
  Hidden CDB loaded slot `0` from that isolated work dir and parsed one
  naturally enabled Dragon cavalry unit with `availability=10`, `enabled=3`.
- Follow-up: refreshed `[source: captures/battle-ui-evidence-current.md]` so
  the combined matrix includes `constructed_fixture_plan: PASS` and
  `constructed_fixture_unit_scan: PASS`.
- Follow-up evidence:
  `[source: captures/battle-constructed-fixture-command-callback-current.md]`
  reaches `0042D4E0` from the isolated fixture with `unit_type=8`, `avail=10`,
  `enabled=3`, click gate `eax=1`, `branch=state1`, and zero
  `BATTLE_COMMAND_FORCE_ENABLED_UNIT` or `BATTLE_COMMAND_CLICK_GATE_FORCE`
  rows. The refreshed hidden CDB run `captures\cdb-surface-dump-20260520-220459`
  uses the battlecenter inputprobe stage, starts the attempt at displayed
  `(588,440)`, reaches `BATTLE_COMMAND_PRE_GATES` as native `(508,380)`,
  removes the descriptor-local pre-gate rearm, the direct render-begin skip,
  and the old `DD_IsLost` guard, then releases the synthetic click state before
  `Render_Begin`; the call exits naturally at iteration `1` with `guard=0`.
- Open questions: replace the remaining synthetic hidden-CDB click/release with
  natural/manual cadence proof.
- Notes: `raw/` was not edited or reorganized.

## [2026-05-27] evidence | Load-slot transition and slot5 fixture probe

- Source updated:
  `[source: CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md]`.
- Related sources:
  `[source: captures/cdb-surface-dump-20260527-120235/load-slot-transition-summary.md]`,
  `[source: captures/cdb-surface-dump-20260527-120522/load-slot-transition-summary.md]`,
  `[source: captures/cdb-surface-dump-20260527-120753/load-slot-transition-summary.md]`,
  `[source: captures/cdb-surface-dump-20260527-121823/right-bottom-slot-fixture-result-summary.md]`,
  and
  `[source: clash95_castle_cmd99_owner_action_slot5_fixture_extra.cdb]`.
- Claim: slot `5` still does not reach the natural right-bottom owner/action
  acceptance route under hidden CDB, and the isolated fixture remains
  diagnostic rather than promotion-ready.
- Evidence: slots `3` and `4` produced no main-load handoff rows. Slot `5`
  matched the expected target slot but stalled before `LSTRANS_LOAD_MENU_ENTRY`,
  `LOADSAVE`, and `PlayGame`, with no AV rows. The guarded
  `non_natural_isolated_fixture` loaded slot `0` from a copy of
  `C:\Clash\save\5.dat`, reached `LOADSAVE`, `PlayGame`, map tile `(14,20)`,
  building index `0`, `flags=0x0b`, and castle overview entry, then gave up
  after bounded overview hit-test misses before command `0x63`.
- Follow-up: derive the correct centered/native castle overview command target
  or descriptor coordinates for this fixture before attempting any further
  right-bottom owner/action patch work.
- Notes: `raw/` was not edited or reorganized. `DEFAULT_STAGE` remains
  unchanged, and no validation-only group was promoted.

## [2026-05-27] evidence | Slot5 load gap rows and fixture native command target

- Source updated:
  `[source: CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md]`.
- Related sources:
  `[source: captures/cdb-surface-dump-20260527-160111/load-slot-transition-summary.md]`,
  `[source: captures/cdb-surface-dump-20260527-160557/right-bottom-slot-fixture-result-summary.md]`,
  `[source: captures/cdb-surface-dump-20260527-161047/right-bottom-slot-fixture-result-summary.md]`,
  `[source: clash95_load_slot_entry_transition_extra.cdb]`, and
  `[source: clash95_castle_cmd99_owner_action_slot5_fixture_extra.cdb]`.
- Claim: natural slot `5` still does not reach the load-menu entry, but the
  isolated fixture now explains and corrects the command `0x63` click target.
- Evidence: the hidden slot `5` transition run observed callback entry and the
  main wait-gate row, then timed out before switch-dispatch, `0044895A`,
  `LOADSAVE`, or `PlayGame`, with no AV rows. The fixture hitmap sample showed
  displayed `(231,366)` had raw byte `0x0c`, while native `(151,306)` had raw
  byte `0xfe`. After retargeting only the fixture probe to native `(151,306)`,
  the hidden fixture reached raw hit `254`, command `99`, owner flag `0x0b`
  with bit `0x02`, descriptor `004338E0`, and a bounded surface dump.
- Follow-up: keep debugging the natural slot `5` transition before promotion;
  use the fixture result only as diagnostic evidence for the native overview
  coordinate path.
- Notes: `raw/` was not edited or reorganized. `DEFAULT_STAGE` remains
  unchanged, no visible/manual runtime was run, and no validation-only group was
  promoted.

## [2026-05-27] evidence | Slot5 natural load success and right-bottom Render_Begin stall

- Source updated:
  `[source: CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md]`.
- Related sources:
  `[source: captures/cdb-surface-dump-20260527-163809/load-slot-transition-summary.md]`,
  `[source: captures/cdb-surface-dump-20260527-165909/right-bottom-natural-slot5-summary.md]`,
  `[source: captures/cdb-surface-dump-20260527-165909/timeout-stack.log]`,
  `[source: clash95_load_slot_entry_transition_extra.cdb]`, and
  `[source: clash95_castle_cmd99_owner_action_slot5_natural_extra.cdb]`.
- Claim: natural slot `5` now reaches `0044895A`, `LOADSAVE`, and `PlayGame`,
  but strict right-bottom promotion is still blocked inside the owner/action
  prelude before draw/copyback rows.
- Evidence: hidden run `captures/cdb-surface-dump-20260527-163809` used
  late-only slot forcing and produced strict `late_entry_load_success` for slot
  `5` with no AV rows. Hidden run `captures/cdb-surface-dump-20260527-165909`
  then reached slot `5`, map tile `(14,20)`, overview raw hit `254`, command
  `99`, owner flag `0x0b` with bit `0x02`, descriptor
  `d1=(155,426 cb=004338e0)`, and `NOWNER_4338E0_ENTRY`. It reached
  `NOWNER_419ED0_RENDER_BEGIN`, but did not return from that marker or reach
  `NOWNER_ACTION_CALL_WRAPPER`, `NOWNER_OWNER_435BC0_ENTRY`, or
  `NOWNER_WRAPPER_COPYBACK_DONE`.
- Follow-up: inspect or instrument the `Render_Begin` / `DD_Pump` wait in the
  natural owner/action prelude before attempting battle visible proof, manual
  DirectInput proof, or any stable-stage promotion.
- Notes: `raw/` was not edited or reorganized. `DEFAULT_STAGE` remains
  unchanged, no visible/manual runtime was run, and no validation-only group was
  promoted.

## [2026-05-27] evidence | Right-bottom Render_Begin/DD_Pump blocker classified

- Source updated:
  `[source: CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md]`.
- Related sources:
  `[source: captures/cdb-surface-dump-20260527-173354/right-bottom-natural-slot5-summary.md]`,
  `[source: captures/cdb-surface-dump-20260527-173354/summary.json]`,
  `[source: captures/cdb-surface-dump-20260527-173354/timeout-stack.log]`,
  `[source: clash95_castle_cmd99_owner_action_slot5_natural_extra.cdb]`, and
  `[source: tools/right_bottom_slot_fixture_result_summary.py]`.
- Claim: natural slot `5` right-bottom routing now has a precise non-AV
  `Render_Begin` / DirectDraw wait blocker, not a load-route or owner-bit
  blocker.
- Evidence: hidden run `captures/cdb-surface-dump-20260527-173354` used
  isolated candidate dir `C:\ClashTests\right-bottom-natural-slot5\v5-renderbegin`
  and candidate SHA-256
  `D3FF331FD6A7B10A91C55A55FF891685CFAC376917816557B40A483EBDBC569C`. The
  summary reports `status=owner_action_ddraw_wait_stalled`, matching slot `5`,
  `LOADSAVE`, `PlayGame`, owner flag `0x0b` with bit `0x02`,
  `NOWNER_RENDER_BEGIN_LATE_ARMED=1`, `NOWNER_DD_PUMP_ENTRY=1`,
  `NOWNER_DD_PUMP_MSG_PUMP_RETURN=1`, flip result `eax=1`, lost result
  `eax=1`, no `NOWNER_RENDER_BEGIN_EXIT`, and zero AV rows.
- Follow-up: keep the next work hidden/no-popup and explain why the
  owner/action `Render_Begin` remains lost/flipping before any visible/manual
  DirectInput, battle proof, or stable promotion attempt.
- Notes: `raw/` was not edited or reorganized. `DEFAULT_STAGE` remains
  unchanged, and no validation-only group was promoted.

## [2026-05-27] evidence | Right-bottom render flag clears and copyback remains blocked

- Source updated:
  `[source: CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md]`.
- Related sources:
  `[source: captures/cdb-surface-dump-20260527-193159/right-bottom-natural-slot5-summary.md]`,
  `[source: captures/cdb-surface-dump-20260527-193512/right-bottom-natural-slot5-summary.md]`,
  `[source: captures/right-bottom-blocker-triage-current.md]`, and
  `[source: clash95_castle_cmd99_owner_action_slot5_natural_release_extra.cdb]`.
- Claim: the natural slot `5` owner/action route is no longer blocked inside
  `Render_Begin`; the current hidden blocker is missing wrapper copyback after
  owner/action draw entry.
- Evidence: the v6 observation run showed `d544d04=1` on `004338E0` entry,
  then `DD_Pump` cleared it to `0`; `Render_Begin` exited on iteration `2`,
  and the route reached `NOWNER_ACTION_CALL_WRAPPER` plus
  `NOWNER_OWNER_435BC0_ENTRY` with no AV.
- Evidence: the v7 release run logged `NOWNER_RELEASE_OWNER_DESC_CLICK` after
  `004338E0`, changing `d544d04` from `1` to `0` and button0 from `0x80` to
  `0x00`; `Render_Begin` exited on iteration `1`.
- Follow-up: diagnose why `00435BC0` does not reach the `0051B86D`
  `NOWNER_WRAPPER_COPYBACK_DONE` row before attempting battle visible proof,
  manual DirectInput proof, or stable promotion.
- Notes: `raw/` was not edited or reorganized. `DEFAULT_STAGE` remains
  unchanged, no visible/manual runtime was run, and no validation-only group was
  promoted.

## [2026-05-28] tooling | Right-bottom copyback trace prepared

- Source updated:
  `[source: CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md]`.
- Related sources:
  `[source: clash95_castle_cmd99_owner_action_slot5_natural_extra.cdb]`,
  `[source: clash95_castle_cmd99_owner_action_slot5_natural_release_extra.cdb]`,
  `[source: tools/right_bottom_slot_fixture_result_summary.py]`, and
  `[source: captures/right-bottom-blocker-triage-current.md]`.
- Claim: the next hidden slot `5` right-bottom run can now distinguish whether
  the native-centering wrapper enters, stock `00435BC0` loops or returns, and
  whether wrapper copyback/present reaches `0051B86D`.
- Evidence: parser tests cover copyback reached, copyback missing after stock
  return, and bounded `00435BC0` loop-stall classifications while preserving
  older evidence status.
- Notes: no runtime proof, visible/manual validation, patch bytes, stable-stage
  change, or promotion was added in this tooling step.

Future entries should be appended using this shape:

```markdown
## [YYYY-MM-DD] ingest | Source Title
- Source: raw/path
- Pages created:
- Pages updated:
- Contradictions:
- Open questions:
```
