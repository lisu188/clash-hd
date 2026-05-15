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

Future entries should be appended using this shape:

```markdown
## [YYYY-MM-DD] ingest | Source Title
- Source: raw/path
- Pages created:
- Pages updated:
- Contradictions:
- Open questions:
```
