#!/usr/bin/env python3
"""Refresh the repo-only Clash95 current evidence artifacts.

This is a no-runtime coordinator. It does not launch Clash95, CDB, wrappers, or
any visible window. It refreshes the current HD-map evidence artifacts and the
current castle overview validation/promotion artifacts from existing manifests,
captures, logs, and generated candidates.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import castle_overview_evidence_matrix
import castle_overview_baseline_recheck
import castle_overview_probe_guard
import castle_overview_promotion_decision
import castle_save_owner_flag_scan
import castle_barracks_action_click_summary
import battle_ui_evidence_matrix
import battle_visible_harness_guard
import battle_visible_input_summary
import capture_corpus_index
import current_completion_summary
import action_panel_route_summary
import border_frame_restore_check
import border_tooltip_summary
import docs_consistency_guard
import evidence_index_check
import exe_artifact_guard
import first_mission_visual_audit
import handoff_freshness_guard
import hd_endurance_release_checklist
import hd_endurance_next_actions
import hd_continuity_status
import hd_layout_summary
import hd_layout_visible_summary
import hd_layout_promotion_decision
import hd_soak_harness_guard
import hd_soak_execution_boundary
import hd_soak_dry_run_plan
import hd_soak_failure_triage
import hd_soak_intro_skip_rerun_readiness
import hd_soak_long_report_guard
import hd_soak_report
import hd_soak_route_coverage
import hd_soak_short_artifact_manifest
import hd_soak_short_step_status
import hd_soak_short_tier_ladder
import hd_soak_approval_preflight
import hd_soak_short_validation_refresh
import hd_map_smoke_matrix
import load_slot_entry_gap_plan
import load_slot_route_limit_guard
import load_slot_timeout_phase
import load_slot_transition_probe_guard
import load_slot_transition_geometry_guard
import load_slot_transition_probe_preview
import load_slot_transition_readiness_matrix
import load_slot_transition_run_plan
import load_slot_transition_summary
import manual_directinput_checklist
import manual_directinput_proof_template
import manual_directinput_run_plan
import no_popup_map_evidence_matrix
import no_popup_boundary_guard
import no_visible_runtime_guard
import patch_manifest_compare
import patch_definition_guard
import promotion_override_guard
import promotion_override_manifest
import process_hygiene_guard
import python_runtime_safety_guard
import launcher_policy_guard
import resolution_manifest_guard
import right_bottom_ui_bounds
import right_bottom_compose_evidence_matrix
import right_bottom_compose_promotion_decision
import right_bottom_grid_hit_probe_guard
import right_bottom_grid_hit_summary
import right_bottom_natural_route_candidate_matrix
import right_bottom_natural_route_guard
import right_bottom_blocker_triage
import right_bottom_visual_artifact_guard
import right_bottom_owner_flag_static_guard
import right_bottom_owner_flag_inventory
import right_bottom_route_timing_guard
import right_bottom_slot_fixture_plan
import right_bottom_slot_fixture_runtime_plan
import right_bottom_slot_fixture_script_guard
import stable_stage_guard
import surface_dump_policy_guard
import visible_runtime_launcher_guard
import test_right_bottom_compose_evidence_matrix
import test_right_bottom_compose_promotion_decision
import test_right_bottom_grid_hit_probe_guard
import test_right_bottom_grid_hit_summary
import test_right_bottom_natural_route_candidate_matrix
import test_right_bottom_natural_route_guard
import test_right_bottom_natural_slot2_summary
import test_right_bottom_blocker_triage
import test_right_bottom_visual_artifact_guard
import test_right_bottom_owner_flag_static_guard
import test_right_bottom_owner_flag_inventory
import test_right_bottom_route_timing_guard
import test_right_bottom_slot_fixture_plan
import test_right_bottom_slot_fixture_runtime_plan
import test_right_bottom_slot_fixture_result_summary
import test_right_bottom_slot_fixture_script_guard
import test_castle_owner_records_summary
import test_castle_save_owner_flag_scan
import test_castle_overview_evidence_matrix
import test_castle_overview_gate
import test_castle_overview_hitbox_summary
import test_castle_overview_hitmap_summary
import test_castle_overview_multihit_summary
import test_castle_overview_promotion_decision
import test_castle_overview_baseline_recheck
import test_castle_overview_probe_guard
import test_battle_ui_evidence_matrix
import test_battle_visible_harness_guard
import test_battle_visible_input_summary
import test_battle_ui_summary
import test_battle_ui_gate
import test_border_frame_restore_check
import test_no_popup_guards
import test_no_popup_map_evidence_matrix
import test_no_visible_runtime_guard
import test_patch_definition_guard
import test_patch_resolution
import test_promotion_override_guard
import test_promotion_override_manifest
import test_process_hygiene_guard
import test_python_runtime_safety_guard
import test_launcher_core
import test_launcher_policy_guard
import test_resolution_manifest_guard
import test_stable_stage_guard
import test_handoff_freshness_guard
import test_hd_endurance_release_checklist
import test_hd_endurance_next_actions
import test_hd_continuity_status
import test_hd_layout_summary
import test_hd_layout_visible_summary
import test_hd_layout_promotion_decision
import test_hd_soak_failure_triage
import test_hd_soak_dry_run_plan
import test_hd_soak_harness_guard
import test_hd_soak_execution_boundary
import test_hd_soak_intro_skip_rerun_readiness
import test_hd_soak_long_report_guard
import test_hd_soak_report
import test_hd_soak_route_coverage
import test_hd_soak_short_artifact_manifest
import test_hd_soak_short_step_status
import test_hd_soak_short_tier_ladder
import test_hd_soak_approval_preflight
import test_hd_soak_short_validation_refresh
import test_load_slot_entry_gap_plan
import test_load_slot_route_limit_guard
import test_load_slot_timeout_phase
import test_load_slot_transition_probe_guard
import test_load_slot_transition_geometry_guard
import test_load_slot_transition_probe_preview
import test_load_slot_transition_readiness_matrix
import test_load_slot_transition_run_plan
import test_load_slot_transition_summary
import test_manual_directinput_checklist
import test_manual_directinput_proof_template
import test_manual_directinput_run_plan
import test_visible_runtime_launcher_guard
import test_capture_corpus_index
import test_current_completion_summary
import test_docs_consistency_guard
import test_first_mission_visual_audit


REPO_ROOT = Path(__file__).resolve().parents[1]


DEFAULT_HD_MAP_SMOKE_JSON = Path("captures/current/hd-map-smoke-current.json")
DEFAULT_HD_MAP_SMOKE_MD = Path("captures/current/hd-map-smoke-current.md")
DEFAULT_HD_LAYOUT_LOG = Path(
    "captures/archive/cdb-surface-dump-20260713-072428/cdb-surface-dump.log"
)
DEFAULT_HD_LAYOUT_SUMMARY_JSON = Path("captures/current/hd-layout-summary-current.json")
DEFAULT_HD_LAYOUT_SUMMARY_MD = Path("captures/current/hd-layout-summary-current.md")
DEFAULT_HD_LAYOUT_SUMMARY_TESTS_JSON = Path(
    "captures/current/hd-layout-summary-tests-current.json"
)
DEFAULT_HD_LAYOUT_SUMMARY_TESTS_MD = Path(
    "captures/current/hd-layout-summary-tests-current.md"
)
DEFAULT_HD_LAYOUT_VISIBLE_RUN_DIR = Path(
    "captures/archive/visual-smoke-20260713-075818"
)
DEFAULT_HD_LAYOUT_VISIBLE_BASELINE_FRAME = Path(
    "captures/archive/manual-rightbottom-entry/after-load-map.png"
)
DEFAULT_HD_LAYOUT_VISIBLE_JSON = Path("captures/current/hd-layout-visible-current.json")
DEFAULT_HD_LAYOUT_VISIBLE_MD = Path("captures/current/hd-layout-visible-current.md")
DEFAULT_HD_LAYOUT_VISIBLE_TESTS_JSON = Path(
    "captures/current/hd-layout-visible-tests-current.json"
)
DEFAULT_HD_LAYOUT_VISIBLE_TESTS_MD = Path(
    "captures/current/hd-layout-visible-tests-current.md"
)
DEFAULT_HD_LAYOUT_PROMOTION_DECISION_JSON = hd_layout_promotion_decision.DEFAULT_OUTPUT_JSON
DEFAULT_HD_LAYOUT_PROMOTION_DECISION_MD = hd_layout_promotion_decision.DEFAULT_OUTPUT_MD
DEFAULT_HD_LAYOUT_PROMOTION_DECISION_TESTS_JSON = Path(
    "captures/current/hd-layout-promotion-decision-tests-current.json"
)
DEFAULT_HD_LAYOUT_PROMOTION_DECISION_TESTS_MD = Path(
    "captures/current/hd-layout-promotion-decision-tests-current.md"
)
DEFAULT_RIGHT_BOTTOM_NATURAL_SLOT2_TESTS_JSON = Path(
    "captures/current/right-bottom-natural-slot2-summary-tests-current.json"
)
DEFAULT_RIGHT_BOTTOM_NATURAL_SLOT2_TESTS_MD = Path(
    "captures/current/right-bottom-natural-slot2-summary-tests-current.md"
)
DEFAULT_NO_POPUP_MAP_EVIDENCE_JSON = Path("captures/current/no-popup-map-evidence-current.json")
DEFAULT_NO_POPUP_MAP_EVIDENCE_MD = Path("captures/current/no-popup-map-evidence-current.md")
DEFAULT_NO_POPUP_MAP_EVIDENCE_TESTS_JSON = Path("captures/current/no-popup-map-evidence-tests-current.json")
DEFAULT_NO_POPUP_MAP_EVIDENCE_TESTS_MD = Path("captures/current/no-popup-map-evidence-tests-current.md")
DEFAULT_HD_MAP_CAPTURES_ROOT = hd_map_smoke_matrix.DEFAULT_CAPTURES_ROOT
DEFAULT_HD_MAP_PATCH_REPORT_JSON = Path("captures/current/patch-stage-current-hd-map.json")
DEFAULT_CASTLE_PATCH_REPORT_JSON = Path("reports/castlecenter_all_patch_stage_20260712_144019.json")
DEFAULT_NO_POPUP_MAP_NORMAL_RUN = Path("captures/archive/cdb-surface-dump-20260429-140916")
DEFAULT_NO_POPUP_MAP_FORCED_RUN = Path("captures/archive/cdb-surface-dump-20260429-135242")
DEFAULT_PATCH_COMPARE_LEFT = Path(
    "captures/archive/patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-20260424.json"
)
DEFAULT_PATCH_COMPARE_RIGHT = Path("captures/archive/patch-stage-mapdraw-partial12-20260424.json")
DEFAULT_PATCH_COMPARE_JSON = Path("captures/current/patch-manifest-compare-current-vs-partial12.json")
DEFAULT_PATCH_COMPARE_MD = Path("captures/current/patch-manifest-compare-current-vs-partial12.md")
DEFAULT_EVIDENCE_INDEX = Path("captures/current/hd-map-evidence-current.md")
DEFAULT_EVIDENCE_INDEX_CHECK_JSON = Path("captures/current/hd-map-evidence-current-check.json")
DEFAULT_CASTLE_MATRIX_JSON = Path("captures/current/castle-overview-evidence-current.json")
DEFAULT_CASTLE_MATRIX_MD = Path("captures/current/castle-overview-evidence-current.md")
DEFAULT_CASTLE_OWNER_RECORDS_TESTS_JSON = Path("captures/current/castle-owner-records-summary-tests-current.json")
DEFAULT_CASTLE_OWNER_RECORDS_TESTS_MD = Path("captures/current/castle-owner-records-summary-tests-current.md")
DEFAULT_CASTLE_SAVE_OWNER_FLAG_SCAN_JSON = castle_save_owner_flag_scan.DEFAULT_JSON
DEFAULT_CASTLE_SAVE_OWNER_FLAG_SCAN_MD = castle_save_owner_flag_scan.DEFAULT_MD
DEFAULT_CASTLE_SAVE_OWNER_FLAG_SCAN_TESTS_JSON = Path(
    "captures/current/castle-save-owner-flag-scan-tests-current.json"
)
DEFAULT_CASTLE_SAVE_OWNER_FLAG_SCAN_TESTS_MD = Path(
    "captures/current/castle-save-owner-flag-scan-tests-current.md"
)
DEFAULT_CASTLE_MATRIX_TESTS_JSON = Path("captures/current/castle-overview-evidence-matrix-tests-current.json")
DEFAULT_CASTLE_MATRIX_TESTS_MD = Path("captures/current/castle-overview-evidence-matrix-tests-current.md")
DEFAULT_CASTLE_GATE_TESTS_JSON = Path("captures/current/castle-overview-gate-tests-current.json")
DEFAULT_CASTLE_GATE_TESTS_MD = Path("captures/current/castle-overview-gate-tests-current.md")
DEFAULT_CASTLE_HITBOX_SUMMARY_TESTS_JSON = Path("captures/current/castle-overview-hitbox-summary-tests-current.json")
DEFAULT_CASTLE_HITBOX_SUMMARY_TESTS_MD = Path("captures/current/castle-overview-hitbox-summary-tests-current.md")
DEFAULT_CASTLE_HITMAP_SUMMARY_TESTS_JSON = Path("captures/current/castle-overview-hitmap-summary-tests-current.json")
DEFAULT_CASTLE_HITMAP_SUMMARY_TESTS_MD = Path("captures/current/castle-overview-hitmap-summary-tests-current.md")
DEFAULT_CASTLE_MULTIHIT_SUMMARY_TESTS_JSON = Path("captures/current/castle-overview-multihit-summary-tests-current.json")
DEFAULT_CASTLE_MULTIHIT_SUMMARY_TESTS_MD = Path("captures/current/castle-overview-multihit-summary-tests-current.md")
DEFAULT_CASTLE_DECISION_JSON = Path("captures/current/castle-overview-promotion-decision-current.json")
DEFAULT_CASTLE_DECISION_MD = Path("captures/current/castle-overview-promotion-decision-current.md")
DEFAULT_CASTLE_DECISION_TESTS_JSON = Path("captures/current/castle-overview-promotion-decision-tests-current.json")
DEFAULT_CASTLE_DECISION_TESTS_MD = Path("captures/current/castle-overview-promotion-decision-tests-current.md")
DEFAULT_CASTLE_BASELINE_RECHECK_JSON = Path("captures/current/castle-overview-baseline-recheck-current.json")
DEFAULT_CASTLE_BASELINE_RECHECK_MD = Path("captures/current/castle-overview-baseline-recheck-current.md")
DEFAULT_CASTLE_BASELINE_RECHECK_TESTS_JSON = Path("captures/current/castle-overview-baseline-recheck-tests-current.json")
DEFAULT_CASTLE_BASELINE_RECHECK_TESTS_MD = Path("captures/current/castle-overview-baseline-recheck-tests-current.md")
DEFAULT_CASTLE_PROBE_GUARD_JSON = Path("captures/current/castle-overview-probe-guard-current.json")
DEFAULT_CASTLE_PROBE_GUARD_MD = Path("captures/current/castle-overview-probe-guard-current.md")
DEFAULT_CASTLE_PROBE_GUARD_TESTS_JSON = Path("captures/current/castle-overview-probe-guard-tests-current.json")
DEFAULT_CASTLE_PROBE_GUARD_TESTS_MD = Path("captures/current/castle-overview-probe-guard-tests-current.md")
DEFAULT_BATTLE_UI_SUMMARY_TESTS_JSON = Path("captures/current/battle-ui-summary-tests-current.json")
DEFAULT_BATTLE_UI_SUMMARY_TESTS_MD = Path("captures/current/battle-ui-summary-tests-current.md")
DEFAULT_BATTLE_UI_GATE_TESTS_JSON = Path("captures/current/battle-ui-gate-tests-current.json")
DEFAULT_BATTLE_UI_GATE_TESTS_MD = Path("captures/current/battle-ui-gate-tests-current.md")
DEFAULT_RIGHT_BOTTOM_COMPOSE_DECISION_JSON = Path(
    "captures/current/right-bottom-compose-promotion-decision-current.json"
)
DEFAULT_RIGHT_BOTTOM_COMPOSE_DECISION_MD = Path(
    "captures/current/right-bottom-compose-promotion-decision-current.md"
)
DEFAULT_RIGHT_BOTTOM_COMPOSE_MATRIX_JSON = Path("captures/current/right-bottom-compose-evidence-current.json")
DEFAULT_RIGHT_BOTTOM_COMPOSE_MATRIX_MD = Path("captures/current/right-bottom-compose-evidence-current.md")
DEFAULT_RIGHT_BOTTOM_GRID_HIT_JSON = Path("captures/current/right-bottom-grid-hit-current.json")
DEFAULT_RIGHT_BOTTOM_GRID_HIT_MD = Path("captures/current/right-bottom-grid-hit-current.md")
DEFAULT_RIGHT_BOTTOM_GRID_HIT_TESTS_JSON = Path("captures/current/right-bottom-grid-hit-summary-tests-current.json")
DEFAULT_RIGHT_BOTTOM_GRID_HIT_TESTS_MD = Path("captures/current/right-bottom-grid-hit-summary-tests-current.md")
DEFAULT_RIGHT_BOTTOM_GRID_HIT_PROBE_GUARD_JSON = Path(
    "captures/current/right-bottom-grid-hit-probe-guard-current.json"
)
DEFAULT_RIGHT_BOTTOM_GRID_HIT_PROBE_GUARD_MD = Path(
    "captures/current/right-bottom-grid-hit-probe-guard-current.md"
)
DEFAULT_RIGHT_BOTTOM_GRID_HIT_PROBE_GUARD_TESTS_JSON = Path(
    "captures/current/right-bottom-grid-hit-probe-guard-tests-current.json"
)
DEFAULT_RIGHT_BOTTOM_GRID_HIT_PROBE_GUARD_TESTS_MD = Path(
    "captures/current/right-bottom-grid-hit-probe-guard-tests-current.md"
)
DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_GUARD_JSON = Path("captures/current/right-bottom-natural-route-guard-current.json")
DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_GUARD_MD = Path("captures/current/right-bottom-natural-route-guard-current.md")
DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_GUARD_TESTS_JSON = Path(
    "captures/current/right-bottom-natural-route-guard-tests-current.json"
)
DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_GUARD_TESTS_MD = Path(
    "captures/current/right-bottom-natural-route-guard-tests-current.md"
)
DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_CANDIDATE_MATRIX_JSON = (
    right_bottom_natural_route_candidate_matrix.DEFAULT_JSON
)
DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_CANDIDATE_MATRIX_MD = (
    right_bottom_natural_route_candidate_matrix.DEFAULT_MD
)
DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_CANDIDATE_MATRIX_TESTS_JSON = Path(
    "captures/current/right-bottom-natural-route-candidate-matrix-tests-current.json"
)
DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_CANDIDATE_MATRIX_TESTS_MD = Path(
    "captures/current/right-bottom-natural-route-candidate-matrix-tests-current.md"
)
DEFAULT_RIGHT_BOTTOM_BLOCKER_TRIAGE_JSON = right_bottom_blocker_triage.DEFAULT_JSON
DEFAULT_RIGHT_BOTTOM_BLOCKER_TRIAGE_MD = right_bottom_blocker_triage.DEFAULT_MD
DEFAULT_RIGHT_BOTTOM_BLOCKER_TRIAGE_TESTS_JSON = Path(
    "captures/current/right-bottom-blocker-triage-tests-current.json"
)
DEFAULT_RIGHT_BOTTOM_BLOCKER_TRIAGE_TESTS_MD = Path(
    "captures/current/right-bottom-blocker-triage-tests-current.md"
)
DEFAULT_RIGHT_BOTTOM_VISUAL_ARTIFACT_GUARD_JSON = right_bottom_visual_artifact_guard.DEFAULT_JSON
DEFAULT_RIGHT_BOTTOM_VISUAL_ARTIFACT_GUARD_MD = right_bottom_visual_artifact_guard.DEFAULT_MD
DEFAULT_RIGHT_BOTTOM_VISUAL_ARTIFACT_GUARD_TESTS_JSON = Path(
    "captures/current/right-bottom-visual-artifact-guard-tests-current.json"
)
DEFAULT_RIGHT_BOTTOM_VISUAL_ARTIFACT_GUARD_TESTS_MD = Path(
    "captures/current/right-bottom-visual-artifact-guard-tests-current.md"
)
DEFAULT_BORDER_FRAME_RESTORE_EVIDENCE_JSON = border_frame_restore_check.DEFAULT_EVIDENCE_JSON
DEFAULT_BORDER_FRAME_RESTORE_REALRUNTIME_JSON = border_frame_restore_check.DEFAULT_REALRUNTIME_JSON
DEFAULT_BORDER_FRAME_RESTORE_CHECK_JSON = border_frame_restore_check.DEFAULT_JSON
DEFAULT_BORDER_FRAME_RESTORE_CHECK_MD = border_frame_restore_check.DEFAULT_MD
DEFAULT_BORDER_FRAME_RESTORE_CHECK_TESTS_JSON = Path(
    "captures/current/border-frame-restore-check-tests-current.json"
)
DEFAULT_BORDER_FRAME_RESTORE_CHECK_TESTS_MD = Path(
    "captures/current/border-frame-restore-check-tests-current.md"
)
DEFAULT_FIRST_MISSION_VISUAL_AUDIT_JSON = first_mission_visual_audit.DEFAULT_JSON
DEFAULT_FIRST_MISSION_VISUAL_AUDIT_MD = first_mission_visual_audit.DEFAULT_MD
DEFAULT_FIRST_MISSION_VISUAL_AUDIT_TESTS_JSON = Path(
    "captures/current/first-mission-visual-audit-tests-current.json"
)
DEFAULT_FIRST_MISSION_VISUAL_AUDIT_TESTS_MD = Path(
    "captures/current/first-mission-visual-audit-tests-current.md"
)
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_PLAN_JSON = right_bottom_slot_fixture_plan.DEFAULT_JSON
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_PLAN_MD = right_bottom_slot_fixture_plan.DEFAULT_MD
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_PLAN_TESTS_JSON = Path(
    "captures/current/right-bottom-slot-fixture-plan-tests-current.json"
)
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_PLAN_TESTS_MD = Path(
    "captures/current/right-bottom-slot-fixture-plan-tests-current.md"
)
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_SCRIPT_GUARD_JSON = right_bottom_slot_fixture_script_guard.DEFAULT_JSON
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_SCRIPT_GUARD_MD = right_bottom_slot_fixture_script_guard.DEFAULT_MD
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_SCRIPT_GUARD_TESTS_JSON = Path(
    "captures/current/right-bottom-slot-fixture-script-guard-tests-current.json"
)
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_SCRIPT_GUARD_TESTS_MD = Path(
    "captures/current/right-bottom-slot-fixture-script-guard-tests-current.md"
)
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RUNTIME_PLAN_JSON = right_bottom_slot_fixture_runtime_plan.DEFAULT_JSON
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RUNTIME_PLAN_MD = right_bottom_slot_fixture_runtime_plan.DEFAULT_MD
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RUNTIME_PLAN_TESTS_JSON = Path(
    "captures/current/right-bottom-slot-fixture-runtime-plan-tests-current.json"
)
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RUNTIME_PLAN_TESTS_MD = Path(
    "captures/current/right-bottom-slot-fixture-runtime-plan-tests-current.md"
)
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RESULT_SUMMARY_TESTS_JSON = Path(
    "captures/current/right-bottom-slot-fixture-result-summary-tests-current.json"
)
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RESULT_SUMMARY_TESTS_MD = Path(
    "captures/current/right-bottom-slot-fixture-result-summary-tests-current.md"
)
DEFAULT_LOAD_SLOT_ROUTE_LIMIT_JSON = load_slot_route_limit_guard.DEFAULT_JSON
DEFAULT_LOAD_SLOT_ROUTE_LIMIT_MD = load_slot_route_limit_guard.DEFAULT_MD
DEFAULT_LOAD_SLOT_ROUTE_LIMIT_TESTS_JSON = Path("captures/current/load-slot-route-limit-tests-current.json")
DEFAULT_LOAD_SLOT_ROUTE_LIMIT_TESTS_MD = Path("captures/current/load-slot-route-limit-tests-current.md")
DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_JSON = load_slot_timeout_phase.DEFAULT_JSON
DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_MD = load_slot_timeout_phase.DEFAULT_MD
DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_TESTS_JSON = Path("captures/current/load-slot-timeout-phase-tests-current.json")
DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_TESTS_MD = Path("captures/current/load-slot-timeout-phase-tests-current.md")
DEFAULT_LOAD_SLOT_ENTRY_GAP_JSON = load_slot_entry_gap_plan.DEFAULT_JSON
DEFAULT_LOAD_SLOT_ENTRY_GAP_MD = load_slot_entry_gap_plan.DEFAULT_MD
DEFAULT_LOAD_SLOT_ENTRY_GAP_TESTS_JSON = Path("captures/current/load-slot-entry-gap-tests-current.json")
DEFAULT_LOAD_SLOT_ENTRY_GAP_TESTS_MD = Path("captures/current/load-slot-entry-gap-tests-current.md")
DEFAULT_LOAD_SLOT_TRANSITION_PROBE_GUARD_JSON = load_slot_transition_probe_guard.DEFAULT_JSON
DEFAULT_LOAD_SLOT_TRANSITION_PROBE_GUARD_MD = load_slot_transition_probe_guard.DEFAULT_MD
DEFAULT_LOAD_SLOT_TRANSITION_PROBE_GUARD_TESTS_JSON = Path(
    "captures/current/load-slot-transition-probe-guard-tests-current.json"
)
DEFAULT_LOAD_SLOT_TRANSITION_PROBE_GUARD_TESTS_MD = Path(
    "captures/current/load-slot-transition-probe-guard-tests-current.md"
)
DEFAULT_LOAD_SLOT_TRANSITION_RUN_PLAN_JSON = load_slot_transition_run_plan.DEFAULT_JSON
DEFAULT_LOAD_SLOT_TRANSITION_RUN_PLAN_MD = load_slot_transition_run_plan.DEFAULT_MD
DEFAULT_LOAD_SLOT_TRANSITION_RUN_PLAN_TESTS_JSON = Path(
    "captures/current/load-slot-transition-run-plan-tests-current.json"
)
DEFAULT_LOAD_SLOT_TRANSITION_RUN_PLAN_TESTS_MD = Path(
    "captures/current/load-slot-transition-run-plan-tests-current.md"
)
DEFAULT_LOAD_SLOT_TRANSITION_GEOMETRY_GUARD_JSON = load_slot_transition_geometry_guard.DEFAULT_JSON
DEFAULT_LOAD_SLOT_TRANSITION_GEOMETRY_GUARD_MD = load_slot_transition_geometry_guard.DEFAULT_MD
DEFAULT_LOAD_SLOT_TRANSITION_GEOMETRY_GUARD_TESTS_JSON = Path(
    "captures/current/load-slot-transition-geometry-guard-tests-current.json"
)
DEFAULT_LOAD_SLOT_TRANSITION_GEOMETRY_GUARD_TESTS_MD = Path(
    "captures/current/load-slot-transition-geometry-guard-tests-current.md"
)
DEFAULT_LOAD_SLOT_TRANSITION_PROBE_PREVIEW_JSON = load_slot_transition_probe_preview.DEFAULT_JSON
DEFAULT_LOAD_SLOT_TRANSITION_PROBE_PREVIEW_MD = load_slot_transition_probe_preview.DEFAULT_MD
DEFAULT_LOAD_SLOT_TRANSITION_PROBE_PREVIEW_TESTS_JSON = Path(
    "captures/current/load-slot-transition-probe-preview-tests-current.json"
)
DEFAULT_LOAD_SLOT_TRANSITION_PROBE_PREVIEW_TESTS_MD = Path(
    "captures/current/load-slot-transition-probe-preview-tests-current.md"
)
DEFAULT_LOAD_SLOT_TRANSITION_READINESS_JSON = load_slot_transition_readiness_matrix.DEFAULT_JSON
DEFAULT_LOAD_SLOT_TRANSITION_READINESS_MD = load_slot_transition_readiness_matrix.DEFAULT_MD
DEFAULT_LOAD_SLOT_TRANSITION_READINESS_TESTS_JSON = Path(
    "captures/current/load-slot-transition-readiness-tests-current.json"
)
DEFAULT_LOAD_SLOT_TRANSITION_READINESS_TESTS_MD = Path(
    "captures/current/load-slot-transition-readiness-tests-current.md"
)
DEFAULT_LOAD_SLOT_TRANSITION_SUMMARY_TESTS_JSON = Path(
    "captures/current/load-slot-transition-summary-tests-current.json"
)
DEFAULT_LOAD_SLOT_TRANSITION_SUMMARY_TESTS_MD = Path(
    "captures/current/load-slot-transition-summary-tests-current.md"
)
DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_STATIC_GUARD_JSON = right_bottom_owner_flag_static_guard.DEFAULT_JSON
DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_STATIC_GUARD_MD = right_bottom_owner_flag_static_guard.DEFAULT_MD
DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_STATIC_GUARD_TESTS_JSON = Path(
    "captures/current/right-bottom-owner-flag-static-guard-tests-current.json"
)
DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_STATIC_GUARD_TESTS_MD = Path(
    "captures/current/right-bottom-owner-flag-static-guard-tests-current.md"
)
DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_INVENTORY_JSON = Path(
    "captures/current/right-bottom-owner-flag-inventory-current.json"
)
DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_INVENTORY_MD = Path(
    "captures/current/right-bottom-owner-flag-inventory-current.md"
)
DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_INVENTORY_TESTS_JSON = Path(
    "captures/current/right-bottom-owner-flag-inventory-tests-current.json"
)
DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_INVENTORY_TESTS_MD = Path(
    "captures/current/right-bottom-owner-flag-inventory-tests-current.md"
)
DEFAULT_RIGHT_BOTTOM_ROUTE_TIMING_GUARD_JSON = Path(
    "captures/current/right-bottom-route-timing-guard-current.json"
)
DEFAULT_RIGHT_BOTTOM_ROUTE_TIMING_GUARD_MD = Path(
    "captures/current/right-bottom-route-timing-guard-current.md"
)
DEFAULT_RIGHT_BOTTOM_ROUTE_TIMING_GUARD_TESTS_JSON = Path(
    "captures/current/right-bottom-route-timing-guard-tests-current.json"
)
DEFAULT_RIGHT_BOTTOM_ROUTE_TIMING_GUARD_TESTS_MD = Path(
    "captures/current/right-bottom-route-timing-guard-tests-current.md"
)
DEFAULT_RIGHT_BOTTOM_COMPOSE_DECISION_TESTS_JSON = Path(
    "captures/current/right-bottom-compose-promotion-decision-tests-current.json"
)
DEFAULT_RIGHT_BOTTOM_COMPOSE_DECISION_TESTS_MD = Path(
    "captures/current/right-bottom-compose-promotion-decision-tests-current.md"
)
DEFAULT_RIGHT_BOTTOM_COMPOSE_MATRIX_TESTS_JSON = Path(
    "captures/current/right-bottom-compose-evidence-matrix-tests-current.json"
)
DEFAULT_RIGHT_BOTTOM_COMPOSE_MATRIX_TESTS_MD = Path(
    "captures/current/right-bottom-compose-evidence-matrix-tests-current.md"
)
DEFAULT_STABLE_STAGE_GUARD_JSON = Path("captures/current/stable-stage-guard-current.json")
DEFAULT_STABLE_STAGE_GUARD_MD = Path("captures/current/stable-stage-guard-current.md")
DEFAULT_STABLE_STAGE_GUARD_TESTS_JSON = Path("captures/current/stable-stage-guard-tests-current.json")
DEFAULT_STABLE_STAGE_GUARD_TESTS_MD = Path("captures/current/stable-stage-guard-tests-current.md")
DEFAULT_EXE_ARTIFACT_GUARD_JSON = Path("captures/current/exe-artifact-guard-current.json")
DEFAULT_EXE_ARTIFACT_GUARD_MD = Path("captures/current/exe-artifact-guard-current.md")
DEFAULT_NO_VISIBLE_RUNTIME_GUARD_JSON = Path("captures/current/no-visible-runtime-guard-current.json")
DEFAULT_NO_VISIBLE_RUNTIME_GUARD_MD = Path("captures/current/no-visible-runtime-guard-current.md")
DEFAULT_NO_VISIBLE_RUNTIME_GUARD_TESTS_JSON = Path("captures/current/no-visible-runtime-guard-tests-current.json")
DEFAULT_NO_VISIBLE_RUNTIME_GUARD_TESTS_MD = Path("captures/current/no-visible-runtime-guard-tests-current.md")
DEFAULT_PROCESS_HYGIENE_GUARD_JSON = Path("captures/current/process-hygiene-guard-current.json")
DEFAULT_PROCESS_HYGIENE_GUARD_MD = Path("captures/current/process-hygiene-guard-current.md")
DEFAULT_PROCESS_HYGIENE_GUARD_TESTS_JSON = Path("captures/current/process-hygiene-guard-tests-current.json")
DEFAULT_PROCESS_HYGIENE_GUARD_TESTS_MD = Path("captures/current/process-hygiene-guard-tests-current.md")
DEFAULT_SURFACE_DUMP_POLICY_GUARD_JSON = Path("captures/current/surface-dump-policy-guard-current.json")
DEFAULT_SURFACE_DUMP_POLICY_GUARD_MD = Path("captures/current/surface-dump-policy-guard-current.md")
DEFAULT_VISIBLE_RUNTIME_LAUNCHER_GUARD_JSON = Path("captures/current/visible-runtime-launcher-guard-current.json")
DEFAULT_VISIBLE_RUNTIME_LAUNCHER_GUARD_MD = Path("captures/current/visible-runtime-launcher-guard-current.md")
DEFAULT_VISIBLE_RUNTIME_LAUNCHER_GUARD_TESTS_JSON = Path("captures/current/visible-runtime-launcher-guard-tests-current.json")
DEFAULT_VISIBLE_RUNTIME_LAUNCHER_GUARD_TESTS_MD = Path("captures/current/visible-runtime-launcher-guard-tests-current.md")
DEFAULT_NO_POPUP_BOUNDARY_GUARD_JSON = Path("captures/current/no-popup-boundary-guard-current.json")
DEFAULT_NO_POPUP_BOUNDARY_GUARD_MD = Path("captures/current/no-popup-boundary-guard-current.md")
DEFAULT_NO_POPUP_GUARD_TESTS_JSON = Path("captures/current/no-popup-guard-tests-current.json")
DEFAULT_NO_POPUP_GUARD_TESTS_MD = Path("captures/current/no-popup-guard-tests-current.md")
DEFAULT_HANDOFF_FRESHNESS_GUARD_JSON = Path("captures/current/handoff-freshness-guard-current.json")
DEFAULT_HANDOFF_FRESHNESS_GUARD_MD = Path("captures/current/handoff-freshness-guard-current.md")
DEFAULT_HANDOFF_FRESHNESS_GUARD_TESTS_JSON = Path("captures/current/handoff-freshness-guard-tests-current.json")
DEFAULT_HANDOFF_FRESHNESS_GUARD_TESTS_MD = Path("captures/current/handoff-freshness-guard-tests-current.md")
DEFAULT_MANUAL_DIRECTINPUT_CHECKLIST_JSON = Path("captures/current/manual-directinput-validation-checklist-current.json")
DEFAULT_MANUAL_DIRECTINPUT_CHECKLIST_MD = Path("captures/current/manual-directinput-validation-checklist-current.md")
DEFAULT_MANUAL_DIRECTINPUT_CHECKLIST_TESTS_JSON = Path(
    "captures/current/manual-directinput-validation-checklist-tests-current.json"
)
DEFAULT_MANUAL_DIRECTINPUT_CHECKLIST_TESTS_MD = Path(
    "captures/current/manual-directinput-validation-checklist-tests-current.md"
)
DEFAULT_MANUAL_DIRECTINPUT_PROOF_TEMPLATE_JSON = Path(
    "captures/current/manual-directinput-proof-template-current.json"
)
DEFAULT_MANUAL_DIRECTINPUT_PROOF_TEMPLATE_REPORT_JSON = Path(
    "captures/current/manual-directinput-proof-template-report-current.json"
)
DEFAULT_MANUAL_DIRECTINPUT_PROOF_TEMPLATE_MD = Path(
    "captures/current/manual-directinput-proof-template-current.md"
)
DEFAULT_MANUAL_DIRECTINPUT_PROOF_TEMPLATE_TESTS_JSON = Path(
    "captures/current/manual-directinput-proof-template-tests-current.json"
)
DEFAULT_MANUAL_DIRECTINPUT_PROOF_TEMPLATE_TESTS_MD = Path(
    "captures/current/manual-directinput-proof-template-tests-current.md"
)
DEFAULT_MANUAL_DIRECTINPUT_RUN_PLAN_JSON = manual_directinput_run_plan.DEFAULT_JSON
DEFAULT_MANUAL_DIRECTINPUT_RUN_PLAN_MD = manual_directinput_run_plan.DEFAULT_MD
DEFAULT_MANUAL_DIRECTINPUT_RUN_PLAN_TESTS_JSON = Path(
    "captures/current/manual-directinput-run-plan-tests-current.json"
)
DEFAULT_MANUAL_DIRECTINPUT_RUN_PLAN_TESTS_MD = Path(
    "captures/current/manual-directinput-run-plan-tests-current.md"
)
DEFAULT_PROMOTION_OVERRIDE_GUARD_JSON = Path("captures/current/promotion-override-guard-current.json")
DEFAULT_PROMOTION_OVERRIDE_GUARD_MD = Path("captures/current/promotion-override-guard-current.md")
DEFAULT_PROMOTION_OVERRIDE_GUARD_TESTS_JSON = Path("captures/current/promotion-override-guard-tests-current.json")
DEFAULT_PROMOTION_OVERRIDE_GUARD_TESTS_MD = Path("captures/current/promotion-override-guard-tests-current.md")
DEFAULT_PYTHON_RUNTIME_SAFETY_JSON = Path("captures/current/python-runtime-safety-current.json")
DEFAULT_PYTHON_RUNTIME_SAFETY_MD = Path("captures/current/python-runtime-safety-current.md")
DEFAULT_PYTHON_RUNTIME_SAFETY_TESTS_JSON = Path("captures/current/python-runtime-safety-tests-current.json")
DEFAULT_PYTHON_RUNTIME_SAFETY_TESTS_MD = Path("captures/current/python-runtime-safety-tests-current.md")
DEFAULT_PATCH_RESOLUTION_TESTS_JSON = Path("captures/current/patch-resolution-tests-current.json")
DEFAULT_PATCH_RESOLUTION_TESTS_MD = Path("captures/current/patch-resolution-tests-current.md")
DEFAULT_LAUNCHER_POLICY_GUARD_JSON = Path("captures/current/launcher-policy-guard-current.json")
DEFAULT_LAUNCHER_POLICY_GUARD_MD = Path("captures/current/launcher-policy-guard-current.md")
DEFAULT_LAUNCHER_POLICY_GUARD_TESTS_JSON = Path("captures/current/launcher-policy-guard-tests-current.json")
DEFAULT_LAUNCHER_POLICY_GUARD_TESTS_MD = Path("captures/current/launcher-policy-guard-tests-current.md")
DEFAULT_LAUNCHER_CORE_TESTS_JSON = Path("captures/current/launcher-core-tests-current.json")
DEFAULT_LAUNCHER_CORE_TESTS_MD = Path("captures/current/launcher-core-tests-current.md")
DEFAULT_RESOLUTION_MANIFEST_GUARD_JSON = Path("captures/current/resolution-manifest-guard-current.json")
DEFAULT_RESOLUTION_MANIFEST_GUARD_MD = Path("captures/current/resolution-manifest-guard-current.md")
DEFAULT_RESOLUTION_MANIFEST_GUARD_TESTS_JSON = Path("captures/current/resolution-manifest-guard-tests-current.json")
DEFAULT_RESOLUTION_MANIFEST_GUARD_TESTS_MD = Path("captures/current/resolution-manifest-guard-tests-current.md")
DEFAULT_PATCH_DEFINITION_JSON = Path("captures/current/patch-definition-current.json")
DEFAULT_PATCH_DEFINITION_MD = Path("captures/current/patch-definition-current.md")
DEFAULT_PATCH_DEFINITION_TESTS_JSON = Path("captures/current/patch-definition-tests-current.json")
DEFAULT_PATCH_DEFINITION_TESTS_MD = Path("captures/current/patch-definition-tests-current.md")
DEFAULT_BATTLE_UI_SUMMARY_TESTS_JSON = Path("captures/current/battle-ui-summary-tests-current.json")
DEFAULT_BATTLE_UI_SUMMARY_TESTS_MD = Path("captures/current/battle-ui-summary-tests-current.md")
DEFAULT_BATTLE_UI_GATE_TESTS_JSON = Path("captures/current/battle-ui-gate-tests-current.json")
DEFAULT_BATTLE_UI_GATE_TESTS_MD = Path("captures/current/battle-ui-gate-tests-current.md")
DEFAULT_BATTLE_VISIBLE_INPUT_JSON = battle_visible_input_summary.DEFAULT_JSON
DEFAULT_BATTLE_VISIBLE_INPUT_MD = battle_visible_input_summary.DEFAULT_MD
DEFAULT_BATTLE_VISIBLE_INPUT_RUNS = (
    # 2026-07-17: first natural visible click-to-callback run (painting proxy,
    # pump-restored passive probe, pulse SendInput; FORCE absent, eax=1 gate
    # row + 0042d4e0 callback consumed). Replaces the three 20260521 runs
    # whose raw logs were lost in the workspace move.
    Path("captures/archive/battle-visible-input-present-20260717-133221"),
)
DEFAULT_BATTLE_VISIBLE_INPUT_SUMMARY_TESTS_JSON = Path(
    "captures/current/battle-visible-input-summary-tests-current.json"
)
DEFAULT_BATTLE_VISIBLE_INPUT_SUMMARY_TESTS_MD = Path(
    "captures/current/battle-visible-input-summary-tests-current.md"
)
DEFAULT_BATTLE_UI_EVIDENCE_JSON = battle_ui_evidence_matrix.DEFAULT_MATRIX_JSON
DEFAULT_BATTLE_UI_EVIDENCE_MD = battle_ui_evidence_matrix.DEFAULT_MATRIX_MD
DEFAULT_BATTLE_UI_EVIDENCE_TESTS_JSON = Path(
    "captures/current/battle-ui-evidence-matrix-tests-current.json"
)
DEFAULT_BATTLE_UI_EVIDENCE_TESTS_MD = Path(
    "captures/current/battle-ui-evidence-matrix-tests-current.md"
)
DEFAULT_BATTLE_VISIBLE_HARNESS_GUARD_JSON = battle_visible_harness_guard.DEFAULT_JSON
DEFAULT_BATTLE_VISIBLE_HARNESS_GUARD_MD = battle_visible_harness_guard.DEFAULT_MD
DEFAULT_BATTLE_VISIBLE_HARNESS_GUARD_TESTS_JSON = Path(
    "captures/current/battle-visible-harness-guard-tests-current.json"
)
DEFAULT_BATTLE_VISIBLE_HARNESS_GUARD_TESTS_MD = Path(
    "captures/current/battle-visible-harness-guard-tests-current.md"
)
DEFAULT_CAPTURE_CORPUS_INDEX_JSON = Path("captures/current/capture-corpus-index-current.json")
DEFAULT_CAPTURE_CORPUS_INDEX_MD = Path("captures/current/capture-corpus-index-current.md")
DEFAULT_CAPTURE_CORPUS_INDEX_TESTS_JSON = Path("captures/current/capture-corpus-index-tests-current.json")
DEFAULT_CAPTURE_CORPUS_INDEX_TESTS_MD = Path("captures/current/capture-corpus-index-tests-current.md")
DEFAULT_HD_SOAK_HARNESS_SCRIPT = hd_soak_harness_guard.DEFAULT_SCRIPT
DEFAULT_HD_SOAK_HARNESS_GUARD_JSON = hd_soak_harness_guard.DEFAULT_JSON
DEFAULT_HD_SOAK_HARNESS_GUARD_MD = hd_soak_harness_guard.DEFAULT_MD
DEFAULT_HD_SOAK_HARNESS_GUARD_TESTS_JSON = Path("captures/current/hd-soak-harness-guard-tests-current.json")
DEFAULT_HD_SOAK_HARNESS_GUARD_TESTS_MD = Path("captures/current/hd-soak-harness-guard-tests-current.md")
DEFAULT_HD_SOAK_EXECUTION_BOUNDARY_JSON = hd_soak_execution_boundary.DEFAULT_JSON
DEFAULT_HD_SOAK_EXECUTION_BOUNDARY_MD = hd_soak_execution_boundary.DEFAULT_MD
DEFAULT_HD_SOAK_EXECUTION_BOUNDARY_TESTS_JSON = Path(
    "captures/current/hd-soak-execution-boundary-tests-current.json"
)
DEFAULT_HD_SOAK_EXECUTION_BOUNDARY_TESTS_MD = Path(
    "captures/current/hd-soak-execution-boundary-tests-current.md"
)
DEFAULT_HD_SOAK_DRY_RUN_PLAN_JSON = hd_soak_dry_run_plan.DEFAULT_JSON
DEFAULT_HD_SOAK_DRY_RUN_PLAN_MD = hd_soak_dry_run_plan.DEFAULT_MD
DEFAULT_HD_SOAK_DRY_RUN_PLAN_TESTS_JSON = Path("captures/current/hd-soak-dry-run-plan-tests-current.json")
DEFAULT_HD_SOAK_DRY_RUN_PLAN_TESTS_MD = Path("captures/current/hd-soak-dry-run-plan-tests-current.md")
DEFAULT_HD_SOAK_REPORT = Path("captures/current/hd-soak-short-current.json")
DEFAULT_HD_SOAK_FIRST_STEP_REPORT = Path("captures/current/hd-soak-short2-menu-idle-current.json")
DEFAULT_HD_SOAK_REPORT_GUARD_JSON = Path("captures/current/hd-soak-report-guard-current.json")
DEFAULT_HD_SOAK_REPORT_GUARD_MD = Path("captures/current/hd-soak-report-guard-current.md")
DEFAULT_HD_SOAK_REPORT_GUARD_TESTS_JSON = Path("captures/current/hd-soak-report-guard-tests-current.json")
DEFAULT_HD_SOAK_REPORT_GUARD_TESTS_MD = Path("captures/current/hd-soak-report-guard-tests-current.md")
DEFAULT_HD_SOAK_FAILURE_TRIAGE_JSON = hd_soak_failure_triage.DEFAULT_JSON
DEFAULT_HD_SOAK_FAILURE_TRIAGE_MD = hd_soak_failure_triage.DEFAULT_MD
DEFAULT_HD_SOAK_FAILURE_TRIAGE_TESTS_JSON = Path("captures/current/hd-soak-failure-triage-tests-current.json")
DEFAULT_HD_SOAK_FAILURE_TRIAGE_TESTS_MD = Path("captures/current/hd-soak-failure-triage-tests-current.md")
DEFAULT_HD_SOAK_ROUTE_COVERAGE_JSON = hd_soak_route_coverage.DEFAULT_JSON
DEFAULT_HD_SOAK_ROUTE_COVERAGE_MD = hd_soak_route_coverage.DEFAULT_MD
DEFAULT_HD_SOAK_ROUTE_COVERAGE_TESTS_JSON = Path("captures/current/hd-soak-route-coverage-tests-current.json")
DEFAULT_HD_SOAK_ROUTE_COVERAGE_TESTS_MD = Path("captures/current/hd-soak-route-coverage-tests-current.md")
DEFAULT_HD_SOAK_SHORT_TIER_LADDER_JSON = hd_soak_short_tier_ladder.DEFAULT_JSON
DEFAULT_HD_SOAK_SHORT_TIER_LADDER_MD = hd_soak_short_tier_ladder.DEFAULT_MD
DEFAULT_HD_SOAK_SHORT_TIER_LADDER_TESTS_JSON = Path(
    "captures/current/hd-soak-short-tier-ladder-tests-current.json"
)
DEFAULT_HD_SOAK_SHORT_TIER_LADDER_TESTS_MD = Path(
    "captures/current/hd-soak-short-tier-ladder-tests-current.md"
)
DEFAULT_HD_SOAK_SHORT_ARTIFACT_MANIFEST_JSON = hd_soak_short_artifact_manifest.DEFAULT_JSON
DEFAULT_HD_SOAK_SHORT_ARTIFACT_MANIFEST_MD = hd_soak_short_artifact_manifest.DEFAULT_MD
DEFAULT_HD_SOAK_SHORT_ARTIFACT_MANIFEST_TESTS_JSON = Path(
    "captures/current/hd-soak-short-artifact-manifest-tests-current.json"
)
DEFAULT_HD_SOAK_SHORT_ARTIFACT_MANIFEST_TESTS_MD = Path(
    "captures/current/hd-soak-short-artifact-manifest-tests-current.md"
)
DEFAULT_HD_SOAK_SHORT_VALIDATION_REFRESH_JSON = hd_soak_short_validation_refresh.DEFAULT_JSON
DEFAULT_HD_SOAK_SHORT_VALIDATION_REFRESH_MD = hd_soak_short_validation_refresh.DEFAULT_MD
DEFAULT_HD_SOAK_SHORT_VALIDATION_REFRESH_TESTS_JSON = Path(
    "captures/current/hd-soak-short-validation-refresh-tests-current.json"
)
DEFAULT_HD_SOAK_SHORT_VALIDATION_REFRESH_TESTS_MD = Path(
    "captures/current/hd-soak-short-validation-refresh-tests-current.md"
)
DEFAULT_HD_SOAK_SHORT_STEP_STATUS_JSON = hd_soak_short_step_status.DEFAULT_JSON
DEFAULT_HD_SOAK_SHORT_STEP_STATUS_MD = hd_soak_short_step_status.DEFAULT_MD
DEFAULT_HD_SOAK_SHORT_STEP_STATUS_TESTS_JSON = Path(
    "captures/current/hd-soak-short-step-status-tests-current.json"
)
DEFAULT_HD_SOAK_SHORT_STEP_STATUS_TESTS_MD = Path(
    "captures/current/hd-soak-short-step-status-tests-current.md"
)
DEFAULT_HD_SOAK_APPROVAL_PREFLIGHT_JSON = hd_soak_approval_preflight.DEFAULT_JSON
DEFAULT_HD_SOAK_APPROVAL_PREFLIGHT_MD = hd_soak_approval_preflight.DEFAULT_MD
DEFAULT_HD_SOAK_APPROVAL_PREFLIGHT_TESTS_JSON = Path(
    "captures/current/hd-soak-approval-preflight-tests-current.json"
)
DEFAULT_HD_SOAK_APPROVAL_PREFLIGHT_TESTS_MD = Path(
    "captures/current/hd-soak-approval-preflight-tests-current.md"
)
DEFAULT_HD_SOAK_INTRO_SKIP_RERUN_READINESS_JSON = hd_soak_intro_skip_rerun_readiness.DEFAULT_JSON
DEFAULT_HD_SOAK_INTRO_SKIP_RERUN_READINESS_MD = hd_soak_intro_skip_rerun_readiness.DEFAULT_MD
DEFAULT_HD_SOAK_INTRO_SKIP_RERUN_READINESS_TESTS_JSON = Path(
    "captures/current/hd-soak-intro-skip-rerun-readiness-tests-current.json"
)
DEFAULT_HD_SOAK_INTRO_SKIP_RERUN_READINESS_TESTS_MD = Path(
    "captures/current/hd-soak-intro-skip-rerun-readiness-tests-current.md"
)
DEFAULT_HD_ENDURANCE_RELEASE_CHECKLIST_JSON = hd_endurance_release_checklist.DEFAULT_JSON
DEFAULT_HD_ENDURANCE_RELEASE_CHECKLIST_MD = hd_endurance_release_checklist.DEFAULT_MD
DEFAULT_HD_ENDURANCE_RELEASE_CHECKLIST_TESTS_JSON = Path(
    "captures/current/hd-endurance-release-checklist-tests-current.json"
)
DEFAULT_HD_ENDURANCE_RELEASE_CHECKLIST_TESTS_MD = Path(
    "captures/current/hd-endurance-release-checklist-tests-current.md"
)
DEFAULT_HD_ENDURANCE_NEXT_ACTIONS_JSON = hd_endurance_next_actions.DEFAULT_JSON
DEFAULT_HD_ENDURANCE_NEXT_ACTIONS_MD = hd_endurance_next_actions.DEFAULT_MD
DEFAULT_HD_ENDURANCE_NEXT_ACTIONS_TESTS_JSON = Path(
    "captures/current/hd-endurance-next-actions-tests-current.json"
)
DEFAULT_HD_ENDURANCE_NEXT_ACTIONS_TESTS_MD = Path(
    "captures/current/hd-endurance-next-actions-tests-current.md"
)
DEFAULT_HD_LONG_SOAK_REPORT_GUARD_JSON = hd_soak_long_report_guard.DEFAULT_JSON
DEFAULT_HD_LONG_SOAK_REPORT_GUARD_MD = hd_soak_long_report_guard.DEFAULT_MD
DEFAULT_HD_LONG_SOAK_PROOF_JSON = hd_soak_long_report_guard.DEFAULT_PROOF_JSON
DEFAULT_HD_LONG_SOAK_REPORT_GUARD_TESTS_JSON = Path("captures/current/hd-soak-long-report-guard-tests-current.json")
DEFAULT_HD_LONG_SOAK_REPORT_GUARD_TESTS_MD = Path("captures/current/hd-soak-long-report-guard-tests-current.md")
DEFAULT_HD_CONTINUITY_JSON = hd_endurance_release_checklist.DEFAULT_CONTINUITY_JSON
DEFAULT_HD_CONTINUITY_MD = hd_continuity_status.DEFAULT_MD
DEFAULT_HD_CONTINUITY_PROOF_JSON = hd_continuity_status.DEFAULT_PROOF_JSON
DEFAULT_HD_CONTINUITY_TESTS_JSON = Path("captures/current/hd-continuity-tests-current.json")
DEFAULT_HD_CONTINUITY_TESTS_MD = Path("captures/current/hd-continuity-tests-current.md")
DEFAULT_PROMOTION_OVERRIDE_MANIFEST_JSON = Path("captures/current/promotion-override-manifest-current.json")
DEFAULT_PROMOTION_OVERRIDE_MANIFEST_MD = Path("captures/current/promotion-override-manifest-current.md")
DEFAULT_PROMOTION_OVERRIDE_MANIFEST_TESTS_JSON = Path(
    "captures/current/promotion-override-manifest-tests-current.json"
)
DEFAULT_PROMOTION_OVERRIDE_MANIFEST_TESTS_MD = Path(
    "captures/current/promotion-override-manifest-tests-current.md"
)
DEFAULT_DOCS_CONSISTENCY_JSON = Path("captures/current/docs-consistency-current.json")
DEFAULT_DOCS_CONSISTENCY_MD = Path("captures/current/docs-consistency-current.md")
DEFAULT_DOCS_CONSISTENCY_TESTS_JSON = Path("captures/current/docs-consistency-tests-current.json")
DEFAULT_DOCS_CONSISTENCY_TESTS_MD = Path("captures/current/docs-consistency-tests-current.md")
DEFAULT_CURRENT_COMPLETION_SUMMARY_JSON = current_completion_summary.DEFAULT_JSON
DEFAULT_CURRENT_COMPLETION_SUMMARY_MD = current_completion_summary.DEFAULT_MD
DEFAULT_CURRENT_COMPLETION_SUMMARY_TESTS_JSON = Path("captures/current/current-completion-summary-tests-current.json")
DEFAULT_CURRENT_COMPLETION_SUMMARY_TESTS_MD = Path("captures/current/current-completion-summary-tests-current.md")
DEFAULT_COMPLETION_BATTLE_JSON = current_completion_summary.DEFAULT_BATTLE_JSON
DEFAULT_REPO_TEST_SWEEP_JSON = current_completion_summary.DEFAULT_REPO_TEST_SWEEP_JSON
DEFAULT_BARRACKS_SUCCESS_RUN = Path("captures/archive/cdb-surface-dump-20260712-151015")
DEFAULT_RIGHT_BOTTOM_UI_RUN = Path("captures/archive/cdb-surface-dump-20260513-104200")
DEFAULT_RIGHT_BOTTOM_OWNER_ROUTE_RUN = Path("captures/archive/cdb-surface-dump-20260712-160131")
DEFAULT_RIGHT_BOTTOM_COMPOSE_BASELINE_RUN = DEFAULT_RIGHT_BOTTOM_OWNER_ROUTE_RUN
DEFAULT_RIGHT_BOTTOM_COMPOSE_RUN = Path("captures/archive/cdb-surface-dump-20260712-144922")
DEFAULT_RIGHT_BOTTOM_COMPOSE_PATCH_RUN = Path("captures/archive/cdb-surface-dump-20260712-160204")
DEFAULT_RIGHT_BOTTOM_COMPOSE_FULLSTART_RUN = Path("captures/archive/cdb-surface-dump-20260712-160351")
DEFAULT_RIGHT_BOTTOM_COMPOSE_NORMAL_RUN = Path("captures/archive/cdb-surface-dump-20260513-121513")
DEFAULT_RIGHT_BOTTOM_COMPOSE_UI_RUN = Path("captures/archive/cdb-surface-dump-20260712-160441")
# user ruling 2026-07-14: slot5-as-slot0 fixture accepted as natural-draw evidence
DEFAULT_RIGHT_BOTTOM_COMPOSE_UI_FIXTURE_RUN = Path("captures/archive/cdb-surface-dump-20260712-155528")
DEFAULT_RIGHT_BOTTOM_GRID_HIT_RUN = Path("captures/archive/cdb-surface-dump-20260712-150240")
DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_RUN = right_bottom_natural_route_guard.DEFAULT_RUN
DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_CANDIDATE_SLOT2_RUN = (
    right_bottom_natural_route_candidate_matrix.DEFAULT_SLOT2_RUN
)
DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_CANDIDATE_SLOT5_RUN = (
    right_bottom_natural_route_candidate_matrix.DEFAULT_SLOT5_RUN
)
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_ROOT = right_bottom_slot_fixture_plan.DEFAULT_FIXTURE_ROOT
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_SCRIPT = right_bottom_slot_fixture_script_guard.DEFAULT_SCRIPT
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RUNTIME_SURFACE_DUMP_SCRIPT = (
    right_bottom_slot_fixture_runtime_plan.DEFAULT_SURFACE_DUMP_SCRIPT
)
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RUNTIME_EXTRA_PROBE = (
    right_bottom_slot_fixture_runtime_plan.DEFAULT_EXTRA_PROBE
)
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RESULT_PARSER = right_bottom_slot_fixture_runtime_plan.DEFAULT_RESULT_PARSER
DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RUNTIME_STAGE = right_bottom_slot_fixture_runtime_plan.DEFAULT_STAGE
DEFAULT_LOAD_SLOT_ROUTE_LIMIT_DECOMP_C = load_slot_route_limit_guard.DEFAULT_DECOMP_C
DEFAULT_LOAD_SLOT_ROUTE_LIMIT_SURFACE_PROBE_SCRIPT = (
    load_slot_route_limit_guard.DEFAULT_SURFACE_PROBE_SCRIPT
)
DEFAULT_LOAD_SLOT_ROUTE_LIMIT_SLOT2_RUN = load_slot_route_limit_guard.DEFAULT_SLOT2_RUN
DEFAULT_LOAD_SLOT_ROUTE_LIMIT_SLOT3_RUN = load_slot_route_limit_guard.DEFAULT_SLOT3_RUN
DEFAULT_LOAD_SLOT_ROUTE_LIMIT_SLOT4_RUN = load_slot_route_limit_guard.DEFAULT_SLOT4_RUN
DEFAULT_LOAD_SLOT_ROUTE_LIMIT_SLOT5_RUN = load_slot_route_limit_guard.DEFAULT_SLOT5_RUN
DEFAULT_LOAD_SLOT_ROUTE_LIMIT_RECENT_SLOT5_RUN = (
    load_slot_route_limit_guard.DEFAULT_RECENT_SLOT5_RUN
)
DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_SLOT2_RUN = load_slot_timeout_phase.DEFAULT_SLOT2_RUN
DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_SLOT3_RUN = load_slot_timeout_phase.DEFAULT_SLOT3_RUN
DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_SLOT4_RUN = load_slot_timeout_phase.DEFAULT_SLOT4_RUN
DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_SLOT5_RUN = load_slot_timeout_phase.DEFAULT_SLOT5_RUN
DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_RECENT_SLOT5_RUN = load_slot_timeout_phase.DEFAULT_RECENT_SLOT5_RUN
DEFAULT_LOAD_SLOT_ENTRY_GAP_DECOMP_C = load_slot_entry_gap_plan.DEFAULT_DECOMP_C
DEFAULT_LOAD_SLOT_ENTRY_GAP_CDB_PROBE = load_slot_entry_gap_plan.DEFAULT_CDB_PROBE
DEFAULT_LOAD_SLOT_ENTRY_GAP_TIMEOUT_PHASE_JSON = load_slot_entry_gap_plan.DEFAULT_TIMEOUT_PHASE_JSON
DEFAULT_LOAD_SLOT_TRANSITION_PROBE = load_slot_transition_probe_guard.DEFAULT_PROBE
DEFAULT_LOAD_SLOT_TRANSITION_SURFACE_DUMP_SCRIPT = (
    load_slot_transition_probe_guard.DEFAULT_SURFACE_DUMP_SCRIPT
)
DEFAULT_RIGHT_BOTTOM_COMPOSE_PATCH_MANIFEST = Path(
    "captures/archive/patch-stage-right-bottom-compose-20260513.json"
)
DEFAULT_REFRESH_JSON = Path("captures/current/current-evidence-refresh-current.json")
DEFAULT_REFRESH_MD = Path("captures/current/current-evidence-refresh-current.md")

RIGHT_BOTTOM_COMPOSE_PATCH_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch-rightbottomcompose"
)
RIGHT_BOTTOM_FIXTURE_NATURAL_DRAW_RULING = (
    "user ruling 2026-07-14: slot5-as-slot0 fixture accepted as natural-draw evidence"
)
RBUI_DESC_SWITCH_UNASSERTED_REASON = (
    "RBUI_DESC_SWITCH is NOT asserted on the slot5-as-slot0 fixture path. The descriptor-switch "
    "row is emitted only by the widget poll 00419DC0, which genuinely cannot fire headlessly on "
    "the bare map, and the accepted fixture run carries only NOWNER_* wrapper/hittest rows, so it "
    "supplies no descriptor-switch equivalent to substitute. A PASS on this path is therefore NOT "
    "proof that right-bottom descriptor switching occurs; descriptor switching remains UNPROVEN."
)
RIGHT_BOTTOM_COMPOSE_UI_GUARD_POLICY_NATURAL = (
    "bare-map natural-rows path: asserts RBUI_VIEWPORT_SWITCH >= 1 and RBUI_DESC_SWITCH >= 1 "
    "alongside the surface-dump, stage, SHA, and patch-group gates"
)
RIGHT_BOTTOM_COMPOSE_UI_GUARD_POLICY_FIXTURE = (
    "slot5-as-slot0 fixture path: asserts RBUI_VIEWPORT_SWITCH >= 1 (unconditional, asserted on "
    "both paths) plus the fixture natural-draw gates (NOWNER_435BC0_PANEL_DRAW >= 1, "
    "NOWNER_435BC0_GRID_DRAW >= 1, NOWNER_WRAPPER_COPYBACK_DONE >= 1, av_count == 0, "
    "proof_class == non_natural_isolated_fixture, expected_slot_match is True) alongside the "
    "surface-dump, stage, SHA, and patch-group gates. DISCLOSURE: "
    + RBUI_DESC_SWITCH_UNASSERTED_REASON
)
RUNTIME_POLICY = "repo/local metadata only; does not launch Clash95, CDB, wrappers, or visible windows"


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def probe_template_matches(value: object, expected_rel: str) -> bool:
    normalized = str(value or "").replace("\\", "/").lower()
    expected = expected_rel.replace("\\", "/").lower()
    basename = expected.rsplit("/", 1)[-1]
    return expected in normalized or normalized.endswith("/" + basename) or normalized.endswith(basename)


def canonical_capture_path(value: object) -> str | None:
    if value is None:
        return None
    raw = str(value)
    if not raw:
        return raw
    path = Path(raw)
    if path.exists():
        return str(path.resolve())
    normalized = raw.replace("\\", "/")
    lower = normalized.lower()
    marker = "/captures/"
    suffix: str | None = None
    if marker in lower:
        index = lower.index(marker) + len(marker)
        suffix = normalized[index:]
    elif lower.startswith("captures/"):
        suffix = normalized[len("captures/") :]
    if not suffix:
        return raw
    candidates = [REPO_ROOT / "captures" / suffix]
    if suffix.lower().startswith("cdb-surface-dump-"):
        candidates.insert(0, REPO_ROOT / "captures" / "archive" / suffix)
    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())
    return raw


def build_hd_map_smoke(args: argparse.Namespace) -> dict[str, Any]:
    smoke_args = argparse.Namespace(
        captures_root=args.hd_map_captures_root,
        normal_run=args.normal_run,
        forced_run=args.forced_run,
        patch_exe=args.hd_map_patch_exe,
        stage=args.hd_map_stage,
        patch_report_json=args.hd_map_patch_report_json,
    )
    matrix = hd_map_smoke_matrix.build_matrix(smoke_args)
    write_json(args.hd_map_smoke_json, matrix)
    hd_map_smoke_matrix.write_markdown(args.hd_map_smoke_md, matrix)
    return {
        "passed": bool(matrix.get("passed")),
        "json": str(args.hd_map_smoke_json),
        "markdown": str(args.hd_map_smoke_md),
        "summary": {
            "patch_stage_passed": matrix.get("patch_stage", {}).get("passed"),
            "post_owner_passed": matrix.get("post_owner_evidence", {}).get("passed"),
            "candidate_sha256": matrix.get("patch_stage", {}).get("sha256"),
            "captures_root": matrix.get("captures_root"),
            "patch_report_json": matrix.get("patch_report_json"),
        },
        "failures": matrix.get("failures", []),
    }


def build_hd_layout_summary(args: argparse.Namespace) -> dict[str, Any]:
    log = args.hd_layout_log
    run = log.parent
    if not log.is_file():
        return {
            "passed": False,
            "json": str(args.hd_layout_summary_json),
            "markdown": str(args.hd_layout_summary_md),
            "log": str(log),
            "run": str(run),
            "summary": {
                "redraw_clip_proved": False,
                "marker_counts": {},
                "check_passes": {},
            },
            "failures": [f"missing HD layout CDB log: {log}"],
        }

    try:
        report = hd_layout_summary.summarize(log)
    except Exception as exc:
        return {
            "passed": False,
            "json": str(args.hd_layout_summary_json),
            "markdown": str(args.hd_layout_summary_md),
            "log": str(log),
            "run": str(run),
            "summary": {
                "redraw_clip_proved": False,
                "marker_counts": {},
                "check_passes": {},
            },
            "failures": [f"failed to parse HD layout CDB log: {type(exc).__name__}: {exc}"],
        }

    write_json(args.hd_layout_summary_json, report)
    hd_layout_summary.write_markdown(args.hd_layout_summary_md, report)
    check_passes = {
        name: bool(check.get("passed"))
        for name, check in (report.get("checks") or {}).items()
    }
    failures = [
        f"HD layout summary check failed: {name}"
        for name, passed in check_passes.items()
        if not passed
    ]
    if not report.get("passed") and not failures:
        failures.append("HD layout summary failed without a detailed check failure")
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.hd_layout_summary_json),
        "markdown": str(args.hd_layout_summary_md),
        "log": str(log),
        "run": str(run),
        "summary": {
            "redraw_clip_proved": bool(report.get("redraw_clip_proved")),
            "marker_counts": report.get("marker_counts") or {},
            "check_passes": check_passes,
        },
        "failures": failures,
    }


def build_hd_layout_summary_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_layout_summary,
        tests=[
            "HD layout summary passes exact anchors without requiring a tooltip draw marker",
            "HD layout summary rejects a wrong tooltip anchor",
            "HD layout summary rejects a missing command-panel descriptor draw",
            "HD layout summary rejects a wrong command-panel clip",
            "HD layout summary rejects access-violation markers",
            "HD layout summary requires an exact redraw-clip allow row after a redraw invocation",
            "HD layout summary CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="HD Layout Summary Tests",
        json_path=args.hd_layout_summary_tests_json,
        md_path=args.hd_layout_summary_tests_md,
        guard_policy=(
            "proves the hidden-CDB HD layout parser fails closed on anchor, descriptor, "
            "clip, redraw, and access-violation regressions"
        ),
    )


def build_hd_layout_visible_summary(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = args.hd_layout_visible_run_dir
    baseline_frame = args.hd_layout_visible_baseline_frame
    try:
        report = hd_layout_visible_summary.summarize(run_dir, baseline_frame)
    except Exception as exc:
        return {
            "passed": False,
            "json": str(args.hd_layout_visible_json),
            "markdown": str(args.hd_layout_visible_md),
            "run": str(run_dir),
            "summary": {
                "authentic_composition_passed": False,
                "command_click_alignment": False,
                "manual_directinput_proof": False,
                "promotion_ready": False,
            },
            "failures": [
                "failed to parse approved visible HD layout evidence: "
                f"{type(exc).__name__}: {exc}"
            ],
        }

    write_json(args.hd_layout_visible_json, report)
    hd_layout_visible_summary.write_markdown(args.hd_layout_visible_md, report)

    failures: list[str] = []
    if report.get("passed") is not True:
        failures.append("approved visible HD layout composition summary is not passing")
    for field in (
        "command_click_alignment",
        "panel_click_callback_proof",
        "manual_directinput_proof",
        "stable_stage_promotion_ready",
        "promotion_ready",
    ):
        if report.get(field) is not False:
            failures.append(f"approved visible HD layout boundary field must remain false: {field}")

    checks = report.get("checks") or {}
    tooltip_passed = bool((checks.get("tooltip_bottom_center_visible") or {}).get("passed"))
    panel_passed = bool((checks.get("panel_right_bottom_visible") or {}).get("passed"))
    hover_passed = bool((checks.get("automated_hover_alignment") or {}).get("passed"))
    failed_click = report.get("failed_panel_click_attempt") or {}
    if failed_click.get("classified_failed_attempt") is not True:
        failures.append("descriptor-5 click miss is not explicitly classified")
    if failed_click.get("alignment_passed") is not False:
        failures.append("descriptor-5 click attempt must remain a failed alignment result")

    return {
        "passed": not failures,
        "json": str(args.hd_layout_visible_json),
        "markdown": str(args.hd_layout_visible_md),
        "run": str(run_dir),
        "summary": {
            "evidence_class": report.get("evidence_class"),
            "candidate_sha256": report.get("candidate_sha256"),
            "authentic_composition_passed": tooltip_passed and panel_passed,
            "tooltip_bottom_center_visible": tooltip_passed,
            "panel_right_bottom_visible": panel_passed,
            "automated_no_click_hover_exact": hover_passed,
            "failed_descriptor5_click_requested": failed_click.get("requested_client"),
            "failed_descriptor5_click_actual": failed_click.get("actual_client"),
            "failed_descriptor5_click_error": failed_click.get("client_error"),
            "command_click_alignment": report.get("command_click_alignment"),
            "panel_click_callback_proof": report.get("panel_click_callback_proof"),
            "manual_directinput_proof": report.get("manual_directinput_proof"),
            "promotion_ready": report.get("promotion_ready"),
        },
        "failures": failures,
    }


def build_hd_layout_visible_summary_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_layout_visible_summary,
        tests=[
            "visible HD layout summary requires the exact isolated candidate identity",
            "visible HD layout summary detects tooltip and active-panel geometry",
            "visible HD layout summary classifies exact no-click hover as automated Win32 alignment only",
            "visible HD layout summary exposes the failed descriptor-5 click instead of hiding it",
            "visible HD layout summary passes the real archive while keeping manual/callback/promotion claims false",
            "visible HD layout summary CLI writes strict JSON/Markdown and honors --require-pass",
        ],
        title="HD Layout Visible Summary Tests",
        json_path=args.hd_layout_visible_tests_json,
        md_path=args.hd_layout_visible_tests_md,
        guard_policy=(
            "proves authentic visible composition stays separate from automated hover, "
            "failed click alignment, manual DirectInput, callbacks, and stable promotion"
        ),
    )


def build_hd_layout_promotion_decision(args: argparse.Namespace) -> dict[str, Any]:
    decision_args = argparse.Namespace(
        patch_json=args.hd_layout_promotion_patch_json,
        hidden_json=args.hd_layout_promotion_hidden_json,
        hidden_run_json=args.hd_layout_promotion_hidden_run_json,
        visible_json=args.hd_layout_visible_json,
        manual_json=args.manual_directinput_checklist_json,
        process_hygiene_json=args.process_hygiene_guard_json,
        current_stable_stage=hd_layout_promotion_decision.PROTECTED_STABLE_STAGE,
        allow_cdb_only_promotion=False,
        promotion_override_manifest=None,
    )
    decision = hd_layout_promotion_decision.build_decision(decision_args)
    write_json(args.hd_layout_promotion_decision_json, decision)
    hd_layout_promotion_decision.write_markdown(
        args.hd_layout_promotion_decision_md,
        decision,
    )

    failures: list[str] = []
    if decision.get("passed") is not True:
        failures.extend(
            decision.get("failures") or ["HD layout promotion decision is not passing"]
        )
    if decision.get("decision") != "defer_stable_promotion":
        failures.append("HD layout promotion decision must remain defer_stable_promotion")
    for field in (
        "stable_stage_should_change",
        "manual_directinput_proof",
        "command_click_alignment",
        "panel_click_callback_proof",
        "promotion_ready",
        "override_accepted",
    ):
        if decision.get(field) is not False:
            failures.append(f"HD layout promotion boundary field must remain false: {field}")

    return {
        "passed": not failures,
        "json": str(args.hd_layout_promotion_decision_json),
        "markdown": str(args.hd_layout_promotion_decision_md),
        "summary": {
            "decision": decision.get("decision"),
            "candidate_sha256": decision.get("candidate_sha256"),
            "current_stable_stage": decision.get("current_stable_stage"),
            "validation_stage": decision.get("validation_stage"),
            "manual_checklist": (
                f"{decision.get('manual_checked_item_count')}/"
                f"{decision.get('manual_checklist_item_count')}"
            ),
            "command_click_alignment": decision.get("command_click_alignment"),
            "panel_click_callback_proof": decision.get("panel_click_callback_proof"),
            "promotion_ready": decision.get("promotion_ready"),
            "stable_stage_should_change": decision.get("stable_stage_should_change"),
        },
        "failures": failures,
    }


def build_hd_layout_promotion_decision_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_layout_promotion_decision,
        tests=[
            "HD layout decision passes only while deferring stable promotion",
            "HD layout decision rejects candidate SHA drift across patch, hidden, or visible evidence",
            "HD layout decision rejects hidden or authentic-visible evidence regressions",
            "HD layout decision never reclassifies the failed descriptor-5 click as success",
            "HD layout decision rejects manual-proof or promotion-ready overclaims",
            "HD layout decision rejects stable-stage drift",
            "HD layout decision rejects every CDB-only override route",
            "HD layout decision CLI writes PASS/defer outputs and fails closed on regressions",
        ],
        title="HD Layout Promotion Decision Tests",
        json_path=args.hd_layout_promotion_decision_tests_json,
        md_path=args.hd_layout_promotion_decision_tests_md,
        guard_policy=(
            "proves authentic composition cannot promote the validation stage while "
            "command click, callback, and five-item manual DirectInput proof remain absent"
        ),
    )


def build_right_bottom_natural_slot2_summary_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_right_bottom_natural_slot2_summary,
        tests=[
            "natural slot-2 summary accepts a complete synthetic proof while preserving evidence limits",
            "natural slot-2 summary rejects a wrong target record flag",
            "natural slot-2 summary requires verified load choice 5 from slot 2",
            "natural slot-2 summary rejects missing or misordered composition markers",
            "natural slot-2 summary rejects visible fallback or the wrong probe profile",
            "natural slot-2 static guard rejects forbidden mutations and control-flow forcing",
            "natural slot-2 summary rejects runtime forcing markers",
            "natural slot-2 summary CLI writes JSON/Markdown and honors --require-pass",
            "natural slot-2 summary CLI returns 2 for a failing log",
        ],
        title="Right-Bottom Natural Slot-2 Summary Tests",
        json_path=args.right_bottom_natural_slot2_tests_json,
        md_path=args.right_bottom_natural_slot2_tests_md,
        guard_policy=(
            "proves the natural slot-2 parser and static probe guard fail closed; "
            "this support-only check is not a real runtime result"
        ),
    )


def build_no_popup_map_evidence(args: argparse.Namespace) -> dict[str, Any]:
    matrix_args = argparse.Namespace(
        captures_root=args.captures_root,
        normal_run=args.no_popup_map_normal_run,
        forced_run=args.no_popup_map_forced_run,
    )
    matrix = no_popup_map_evidence_matrix.build_matrix(matrix_args)
    write_json(args.no_popup_map_evidence_json, matrix)
    args.no_popup_map_evidence_md.parent.mkdir(parents=True, exist_ok=True)
    args.no_popup_map_evidence_md.write_text(
        no_popup_map_evidence_matrix.render_markdown(matrix),
        encoding="utf-8",
    )
    normal = matrix.get("normal", {})
    forced = matrix.get("forced_visible", {})
    return {
        "passed": bool(matrix.get("passed")),
        "json": str(args.no_popup_map_evidence_json),
        "markdown": str(args.no_popup_map_evidence_md),
        "summary": {
            "normal_run": normal.get("run"),
            "normal_blank_active_count": normal.get("blank_active_count"),
            "normal_unexplained_blank_count": normal.get("unexplained_blank_count"),
            "normal_visibility_status_counts": normal.get("visibility_status_counts"),
            "forced_run": forced.get("run"),
            "forced_blank_active_count": forced.get("blank_active_count"),
            "forced_visible_exit_code": forced.get("forced_visible_exit_code"),
            "forced_visret_nonzero_count": forced.get("vedge_visret_nonzero_count"),
            "forced_post_nonblack_count": forced.get("vedge_post_nonblack_count"),
        },
        "failures": [
            f"{row.get('kind', 'row')}: {failure}"
            for row in (normal, forced)
            for failure in row.get("failures", [])
        ],
    }


def write_no_popup_map_evidence_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# No-Popup Map Evidence Matrix Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_no_popup_map_evidence_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "no_popup_map_evidence_matrix passes with explicit normal and forced-visible runs",
        "no_popup_map_evidence_matrix scans and selects the latest passing normal and forced-visible runs",
        "no_popup_map_evidence_matrix rejects normal visibility-gate regressions",
        "no_popup_map_evidence_matrix rejects forced-visible gate regressions",
        "no_popup_map_evidence_matrix CLI writes JSON/Markdown and returns 2 on --require-pass failure",
    ]
    failures: list[str] = []
    try:
        test_no_popup_map_evidence_matrix.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for matrix CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the no-popup map evidence matrix requires a visibility-explained normal run, "
            "a forced-visible edge proof, latest-run selection, and CLI fail-closed behavior"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.no_popup_map_evidence_tests_json, result)
    write_no_popup_map_evidence_tests_markdown(args.no_popup_map_evidence_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.no_popup_map_evidence_tests_json),
        "markdown": str(args.no_popup_map_evidence_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_patch_compare(args: argparse.Namespace) -> dict[str, Any]:
    comparison = patch_manifest_compare.build_comparison(
        args.patch_compare_left,
        args.patch_compare_right,
    )
    write_json(args.patch_compare_json, comparison)
    patch_manifest_compare.write_markdown(args.patch_compare_md, comparison, args.patch_compare_limit)
    counts = comparison["counts"]
    no_bad_status = counts["left_nonpatched"] == 0 and counts["right_nonpatched"] == 0
    return {
        "passed": no_bad_status,
        "json": str(args.patch_compare_json),
        "markdown": str(args.patch_compare_md),
        "summary": {
            "structural_diff_count": counts["structural_diff_count"],
            "left_nonpatched": counts["left_nonpatched"],
            "right_nonpatched": counts["right_nonpatched"],
            "added_records": counts["added_records"],
            "removed_records": counts["removed_records"],
            "changed_records": counts["changed_records"],
        },
        "failures": [] if no_bad_status else ["patch manifest comparison has original/unexpected records"],
    }


def build_evidence_index_check(args: argparse.Namespace) -> dict[str, Any]:
    report = evidence_index_check.build_report(args.evidence_index.resolve())
    write_json(args.evidence_index_check_json, report)
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.evidence_index_check_json),
        "index": str(args.evidence_index),
        "summary": report.get("counts", {}),
        "failures": [] if report.get("passed") else ["evidence index check failed"],
    }


def build_castle_matrix(args: argparse.Namespace) -> dict[str, Any]:
    matrix_args = argparse.Namespace(
        stage=args.castle_stage,
        patch_exe=args.castle_patch_exe,
        patch_report_json=args.castle_patch_report_json,
        overview_run=args.castle_overview_run,
        barracks_run=args.castle_barracks_run,
        focused_hitbox_run=args.castle_focused_hitbox_run,
        visible_multihit_run=args.castle_visible_multihit_run,
        owner_records_raw=args.castle_owner_records_raw,
        forced_hitmap_raw=args.castle_forced_hitmap_raw,
        dormant_multihit_run=args.castle_dormant_multihit_run,
        threshold=args.castle_threshold,
        max_echo_percent=args.castle_max_echo_percent,
    )
    matrix = castle_overview_evidence_matrix.build_matrix(matrix_args)
    write_json(args.castle_matrix_json, matrix)
    castle_overview_evidence_matrix.write_markdown(args.castle_matrix_md, matrix)
    return {
        "passed": bool(matrix.get("passed")),
        "json": str(args.castle_matrix_json),
        "markdown": str(args.castle_matrix_md),
        "summary": {
            "promotion_status": matrix.get("promotion_status"),
            "candidate_sha256": matrix.get("checks", {}).get("patch_stage", {}).get("sha256"),
            "patches": matrix.get("checks", {}).get("patch_stage", {}).get("patches"),
        },
        "failures": matrix.get("failures", []),
    }


def write_castle_owner_records_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Castle Owner Records Summary Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_castle_owner_records_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "castle_owner_records_summary classifies active, retired, nonempty, interesting, and flag-value records",
        "castle_owner_records_summary CLI writes JSON/Markdown and passes require-active plus forbid-interesting on a current-style raw dump",
        "castle_owner_records_summary fails closed for no active records, missing interesting records, forbidden interesting records, and truncated raw dumps",
    ]
    failures: list[str] = []
    try:
        test_castle_owner_records_summary.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for parser CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the castle owner-record parser recognizes active, retired, nonempty, "
            "interesting, and flag-value records, and fails closed for no-active, "
            "require-interesting, forbid-interesting, and truncated raw-dump cases"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.castle_owner_records_tests_json, result)
    write_castle_owner_records_tests_markdown(args.castle_owner_records_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.castle_owner_records_tests_json),
        "markdown": str(args.castle_owner_records_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_castle_save_owner_flag_scan(args: argparse.Namespace) -> dict[str, Any]:
    report = castle_save_owner_flag_scan.build_report(
        args.castle_save_owner_flag_saves_root,
        args.castle_save_owner_flag_known_offset,
        args.castle_save_owner_flag_record_count,
    )
    write_json(args.castle_save_owner_flag_scan_json, report)
    castle_save_owner_flag_scan.write_markdown(args.castle_save_owner_flag_scan_md, report)
    summary = report.get("summary") or {}
    target = summary.get("recommended_route_target") or {}
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.castle_save_owner_flag_scan_json),
        "markdown": str(args.castle_save_owner_flag_scan_md),
        "summary": {
            "save_count": summary.get("save_count"),
            "candidate_block_count": summary.get("candidate_block_count"),
            "active_record_count": summary.get("active_record_count"),
            "records_with_any_owner_flag_count": summary.get("records_with_any_owner_flag_count"),
            "action_eligible_save_count": summary.get("action_eligible_save_count"),
            "action_eligible_record_count": summary.get("action_eligible_record_count"),
            "recommended_save": target.get("save"),
            "recommended_record_index": target.get("record_index"),
            "recommended_position": [target.get("x"), target.get("y")] if target else None,
            "recommended_owner": target.get("owner"),
            "recommended_flags_1a0": target.get("flags_1a0_hex"),
            "current_blocker": summary.get("current_blocker"),
            "guard_policy": report.get("guard_policy"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_castle_save_owner_flag_scan_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_castle_save_owner_flag_scan,
        tests=[
            "castle_save_owner_flag_scan reports current-style owner blocks without requiring bit 0x02",
            "castle_save_owner_flag_scan detects a natural action-eligible owner flag bit 0x02",
            "castle_save_owner_flag_scan CLI writes JSON/Markdown and fails closed under --require-action-eligible",
            "castle_save_owner_flag_scan fails closed when the saves root is missing",
        ],
        title="Castle Save Owner-Flag Scan Tests",
        json_path=args.castle_save_owner_flag_scan_tests_json,
        md_path=args.castle_save_owner_flag_scan_tests_md,
        guard_policy=(
            "proves the installed-save owner-flag scan stores only metadata, "
            "detects natural 004338E0 bit-2 route candidates, and fails closed "
            "when required save evidence is unavailable"
        ),
    )


def write_castle_matrix_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Castle Overview Evidence Matrix Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_castle_matrix_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "castle_overview_evidence_matrix passes when every component gate passes",
        "castle_overview_evidence_matrix fails when each required component gate fails",
        "castle_overview_evidence_matrix accepts an archived patch-stage report when the live candidate is absent",
        "castle_overview_evidence_matrix focused hitbox gate requires displayed-wrapper proof",
        "castle_overview_evidence_matrix multihit gates report target-done completion proof",
        "castle_overview_evidence_matrix CLI writes JSON/Markdown and returns 2 on --require-pass failure",
    ]
    failures: list[str] = []
    try:
        test_castle_overview_evidence_matrix.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for matrix CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the castle overview evidence matrix aggregates every required component gate, "
            "fails when any required gate fails, accepts archived patch-stage reports when live "
            "candidate executables are absent, requires displayed-wrapper proof in the focused "
            "hitbox gate, reports target-done completion proof in multi-hit gates, preserves "
            "validation-stage-only status, and its CLI fails closed under --require-pass"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.castle_matrix_tests_json, result)
    write_castle_matrix_tests_markdown(args.castle_matrix_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.castle_matrix_tests_json),
        "markdown": str(args.castle_matrix_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def write_castle_gate_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Castle Overview Gate Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_castle_gate_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "castle_overview_gate passes with catalog, geometry, and barracks baseline inputs passing",
        "castle_overview_gate fails on overview readiness, AV, post-draw, surface-size, command, and geometry regressions",
        "castle_overview_gate fails when the barracks baseline regresses",
        "castle_overview_gate CLI writes JSON/Markdown and returns 2 on --require-pass failure",
    ]
    failures: list[str] = []
    try:
        test_castle_overview_gate.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for gate CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the castle overview visual/catalog gate rejects missing readiness, AV rows, "
            "missing or wrong overview post-draw and surface sizes, missing expected commands, "
            "centered-geometry regressions, barracks baseline regressions, and fails closed "
            "under --require-pass"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.castle_gate_tests_json, result)
    write_castle_gate_tests_markdown(args.castle_gate_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.castle_gate_tests_json),
        "markdown": str(args.castle_gate_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def write_castle_hitbox_summary_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Castle Overview Hitbox Summary Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_castle_hitbox_summary_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "castle_overview_hitbox_summary parses displayed/native hits, descriptor, click gate, callback suppression, ready size, and AV count",
        "castle_overview_hitbox_summary CLI writes JSON/Markdown and passes all required flags on a good focused log",
        "castle_overview_hitbox_summary CLI returns 2 for missing readiness, wrong size, missing displayed/native hit, descriptor, click gate, suppression, callback entry, and AV rows",
    ]
    failures: list[str] = []
    try:
        test_castle_overview_hitbox_summary.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for parser CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the focused castle overview hitbox parser recognizes displayed/native hit rows, "
            "descriptor and click-gate rows, callback suppression, ready size, callback entry, AV rows, "
            "and fails closed under required CLI flags"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.castle_hitbox_summary_tests_json, result)
    write_castle_hitbox_summary_tests_markdown(args.castle_hitbox_summary_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.castle_hitbox_summary_tests_json),
        "markdown": str(args.castle_hitbox_summary_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def write_castle_hitmap_summary_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Castle Overview Hitmap Summary Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_castle_hitmap_summary_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "castle_overview_hitmap_summary maps raw IDs to commands, presence, counts, bounding boxes, and centered displayed coordinates",
        "castle_overview_hitmap_summary CLI writes JSON/Markdown and passes required present/absent flags on a good raw hitmap",
        "castle_overview_hitmap_summary rejects missing required raw IDs, present IDs required absent, and wrong raw dimensions",
    ]
    failures: list[str] = []
    try:
        test_castle_overview_hitmap_summary.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for parser CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the castle overview hitmap parser recognizes raw command IDs, "
            "counts, bounding boxes, centered displayed coordinates, required present/absent "
            "flags, and wrong raw dimensions"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.castle_hitmap_summary_tests_json, result)
    write_castle_hitmap_summary_tests_markdown(args.castle_hitmap_summary_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.castle_hitmap_summary_tests_json),
        "markdown": str(args.castle_hitmap_summary_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def write_castle_multihit_summary_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Castle Overview Multihit Summary Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_castle_multihit_summary_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "castle_overview_multihit_summary parses target-set, hit-test, descriptor, click-gate, target-done, ready-size, callback, and AV rows",
        "castle_overview_multihit_summary CLI writes JSON/Markdown and passes all required flags on a good multi-hit log",
        "castle_overview_multihit_summary CLI returns 2 for missing readiness, wrong size, raw/descriptor/gate/completion mismatch, callback entry, and AV rows",
    ]
    failures: list[str] = []
    try:
        test_castle_overview_multihit_summary.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for parser CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the castle overview multi-hit parser recognizes expected target rows, "
            "hit-test results, descriptor, click-gate, target-done rows, ready size, "
            "callback entry, AV rows, and fails closed under required CLI flags"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.castle_multihit_summary_tests_json, result)
    write_castle_multihit_summary_tests_markdown(args.castle_multihit_summary_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.castle_multihit_summary_tests_json),
        "markdown": str(args.castle_multihit_summary_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_castle_decision(args: argparse.Namespace) -> dict[str, Any]:
    decision_args = argparse.Namespace(
        matrix=args.castle_matrix_json,
        current_stable_stage=args.current_stable_stage,
        manual_input_proof=args.manual_input_proof,
        allow_cdb_only_promotion=args.allow_cdb_only_promotion,
    )
    decision = castle_overview_promotion_decision.build_decision(decision_args)
    write_json(args.castle_decision_json, decision)
    castle_overview_promotion_decision.write_markdown(args.castle_decision_md, decision)
    return {
        "passed": bool(decision.get("passed")),
        "json": str(args.castle_decision_json),
        "markdown": str(args.castle_decision_md),
        "summary": {
            "decision": decision.get("decision"),
            "stable_stage_should_change": decision.get("stable_stage_should_change"),
            "current_stable_stage": decision.get("current_stable_stage"),
            "focused_displayed_wrapper_ok": (decision.get("proof") or {}).get("focused_displayed_wrapper_ok"),
            "visible_multihit_completion_ok": (decision.get("proof") or {}).get("visible_multihit_completion_ok"),
            "dormant_multihit_completion_ok": (decision.get("proof") or {}).get("dormant_multihit_completion_ok"),
            "manual_input_proof_valid": decision.get("manual_input_proof_valid"),
        },
        "failures": decision.get("failures", []),
    }


def write_castle_decision_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Castle Overview Promotion Decision Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_castle_decision_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "castle_overview_promotion_decision defers stable promotion by default",
        "castle_overview_promotion_decision fails closed when the evidence matrix fails",
        "castle_overview_promotion_decision fails closed when required focused/multihit proof is missing",
        "castle_overview_promotion_decision allows stable promotion with a valid manual input proof manifest",
        "castle_overview_promotion_decision rejects placeholder manual input proof files",
        "castle_overview_promotion_decision allows CDB-only promotion only with the explicit override flag",
        "castle_overview_promotion_decision CLI writes JSON/Markdown and returns 2 on --require-pass failure",
    ]
    failures: list[str] = []
    try:
        test_castle_overview_promotion_decision.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for decision CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the castle overview promotion decision defers stable promotion by default, "
            "fails when the evidence matrix fails or when focused displayed-wrapper / "
            "visible-dormant multi-hit completion proof is missing, only marks the stable "
            "stage as changeable when a valid manual proof manifest or an explicit CDB-only "
            "override is supplied, rejects placeholder proof files, and its CLI fails "
            "closed under --require-pass"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.castle_decision_tests_json, result)
    write_castle_decision_tests_markdown(args.castle_decision_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.castle_decision_tests_json),
        "markdown": str(args.castle_decision_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_castle_baseline_recheck(args: argparse.Namespace) -> dict[str, Any]:
    recheck_args = argparse.Namespace(
        overview_run=args.castle_baseline_overview_run,
        barracks_run=args.castle_barracks_run,
        stage=args.castle_stage,
        patch_exe=args.castle_patch_exe,
        patch_report_json=args.castle_patch_report_json,
        latest_overview_run=args.castle_overview_run,
        focused_hitbox_run=args.castle_focused_hitbox_run,
        visible_multihit_run=args.castle_visible_multihit_run,
        owner_records_raw=args.castle_owner_records_raw,
        forced_hitmap_raw=args.castle_forced_hitmap_raw,
        dormant_multihit_run=args.castle_dormant_multihit_run,
        threshold=args.castle_threshold,
        max_echo_percent=args.castle_max_echo_percent,
    )
    recheck = castle_overview_baseline_recheck.build_recheck(recheck_args)
    write_json(args.castle_baseline_recheck_json, recheck)
    castle_overview_baseline_recheck.write_markdown(
        args.castle_baseline_recheck_md,
        recheck,
    )
    overview = recheck.get("checks", {}).get("overview_visual_baseline", {})
    barracks = recheck.get("checks", {}).get("barracks_controlled_stop", {})
    matrix = recheck.get("checks", {}).get("latest_castle_overview_matrix", {})
    return {
        "passed": bool(recheck.get("passed")),
        "json": str(args.castle_baseline_recheck_json),
        "markdown": str(args.castle_baseline_recheck_md),
        "summary": {
            "overview_baseline_run": overview.get("run"),
            "overview_surface_size": overview.get("surface_size"),
            "overview_centered_geometry": overview.get("centered_geometry_passed"),
            "barracks_descriptor_click": barracks.get("descriptor_click_ok"),
            "barracks_controlled_4356c0": barracks.get("controlled_4356c0_ok"),
            "latest_matrix_promotion_status": matrix.get("promotion_status"),
            "candidate_sha256": matrix.get("candidate_sha256"),
            "visible_multihit_completion_ok": matrix.get("visible_multihit_completion_ok"),
            "dormant_multihit_completion_ok": matrix.get("dormant_multihit_completion_ok"),
        },
        "failures": recheck.get("failures", []),
    }


def write_castle_baseline_recheck_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Castle Overview Baseline Recheck Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_castle_baseline_recheck_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "castle_overview_baseline_recheck passes with overview, barracks, and latest matrix inputs passing",
        "castle_overview_baseline_recheck fails when the overview visual baseline fails",
        "castle_overview_baseline_recheck fails when the barracks controlled-stop baseline fails",
        "castle_overview_baseline_recheck fails when the latest castle overview matrix fails",
        "castle_overview_baseline_recheck fails when latest matrix target-done completion proof is missing",
        "castle_overview_baseline_recheck writes JSON and Markdown outputs",
    ]
    failures: list[str] = []
    try:
        test_castle_overview_baseline_recheck.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only in-process fixture tests; does not launch Clash95, CDB, wrappers, "
            "PowerShell, Python child processes, or visible windows"
        ),
        "guard_policy": (
            "proves the castle overview baseline recheck rejects stale overview visual "
            "baselines, stale barracks controlled-stop baselines, and failing latest "
            "castle overview matrices, including matrices without visible/dormant "
            "target-done completion proof"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.castle_baseline_recheck_tests_json, result)
    write_castle_baseline_recheck_tests_markdown(args.castle_baseline_recheck_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.castle_baseline_recheck_tests_json),
        "markdown": str(args.castle_baseline_recheck_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_castle_probe_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard_args = argparse.Namespace(
        probe_script=args.castle_probe_script,
        summary_parser=args.castle_probe_summary_parser,
        patcher=args.castle_probe_patcher,
        focused_run=args.castle_focused_hitbox_run,
    )
    guard = castle_overview_probe_guard.build_guard(guard_args)
    write_json(args.castle_probe_guard_json, guard)
    castle_overview_probe_guard.write_markdown(args.castle_probe_guard_md, guard)
    probe = guard.get("checks", {}).get("probe_script", {})
    focused = guard.get("checks", {}).get("focused_hitbox_log", {})
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.castle_probe_guard_json),
        "markdown": str(args.castle_probe_guard_md),
        "summary": {
            "breakpoints": [
                address
                for address, record in (probe.get("breakpoints") or {}).items()
                if record.get("present")
            ],
            "displayed_hit_ok": focused.get("displayed_hit_ok"),
            "displayed_wrapper_ok": focused.get("displayed_wrapper_ok"),
            "click_gate_ok": focused.get("click_gate_ok"),
            "callback_called": focused.get("callback_called"),
            "av_count": focused.get("av_count"),
            "guard_policy": guard.get("guard_policy"),
        },
        "failures": guard.get("failures", []),
    }


def write_castle_probe_guard_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Castle Overview Probe Guard Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_castle_probe_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "castle_overview_probe_guard passes with the focused probe shape and clean focused log",
        "castle_overview_probe_guard fails when each descriptor-loop breakpoint is missing",
        "castle_overview_probe_guard fails when each required probe marker is missing",
        "castle_overview_probe_guard fails when each required parser marker is missing",
        "castle_overview_probe_guard fails when either old crashing overview wrapper marker returns",
        "castle_overview_probe_guard fails when focused hitbox log AV rows are present",
        "castle_overview_probe_guard fails when focused hitbox log wrapper proof rows or surface sizes regress",
        "castle_overview_probe_guard CLI writes JSON/Markdown and returns 2 on --require-pass failure",
    ]
    failures: list[str] = []
    try:
        test_castle_overview_probe_guard.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for guard CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the castle overview probe guard rejects missing descriptor-loop breakpoints, "
            "missing probe/parser markers, old crashing overview wrapper markers, AV rows, missing "
            "wrapper/gate proof rows, and surface-size regressions in the focused hitbox log, while "
            "its CLI writes outputs and fails closed under --require-pass"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.castle_probe_guard_tests_json, result)
    write_castle_probe_guard_tests_markdown(args.castle_probe_guard_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.castle_probe_guard_tests_json),
        "markdown": str(args.castle_probe_guard_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def write_right_bottom_grid_hit_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    lines = [
        "# Right-Bottom Controlled Grid Hit",
        "",
        f"- Status: {status_text(bool(report.get('passed')))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Run: `{report['run']}`",
        f"- Log: `{report['log']}`",
        f"- Screenshot: `{report['screenshot']}`",
        "- Screenshot policy: diagnostic CDB/proxy frame only; not visual acceptance proof for the final action-menu layout.",
        f"- Stage: `{summary.get('stage')}`",
        f"- Candidate SHA-256: `{summary.get('candidate_sha256')}`",
        f"- Surface: `{summary.get('surface')}`",
        f"- Fast-forward startup: `{summary.get('fast_forward_start_anims')}`",
        f"- Map validation skipped: `{summary.get('map_validation_skipped')}`",
        f"- Grid hit ok: `{summary.get('grid_hit_ok')}`",
        f"- Last grid entry: `{summary.get('last_grid_entry')}`",
        f"- Last grid result: `{summary.get('last_grid_result')}`",
        f"- Forced hidden flip gates: `{summary.get('forced_gate_count')}`",
        f"- Failure exits: `{summary.get('failure_exit_count')}`",
        f"- Draw rows: `{summary.get('draw_row_count')}`",
        f"- AV count: `{summary.get('av_count')}`",
        "",
        "## Classification",
        "",
    ]
    lines.extend(f"- {item}" for item in report["parser_summary"].get("classification", []))
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_right_bottom_grid_hit(args: argparse.Namespace) -> dict[str, Any]:
    run = args.right_bottom_grid_hit_run
    manifest_path = args.right_bottom_compose_patch_manifest
    summary_path = run / "summary.json"
    log = run / "cdb-surface-dump.log"
    screenshot = run / "surface.png"
    failures: list[str] = []

    for label, path in (
        ("right-bottom grid-hit summary", summary_path),
        ("right-bottom grid-hit log", log),
        ("right-bottom grid-hit screenshot", screenshot),
        ("right-bottom compose patch manifest", manifest_path),
    ):
        if not path.exists():
            return {
                "passed": False,
                "run": str(run),
                "manifest": str(manifest_path),
                "failures": [f"missing {label}: {path}"],
            }

    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    grid = right_bottom_grid_hit_summary.parse_log(log, [450, 73], 0)
    surface = summary.get("Surface") or {}
    patch_group = (manifest.get("groups") or {}).get("right-bottom-compose-proof") or {}
    status_counts = manifest.get("status_counts") or {}
    current_gate = manifest.get("current_hd_map_gate") or {}

    if not summary.get("Passed"):
        failures.append("right-bottom grid-hit surface dump did not pass")
    if summary.get("HiddenDesktop") is not True:
        failures.append("right-bottom grid-hit run was not hidden-desktop")
    if summary.get("AllowVisibleDesktop") is True:
        failures.append("right-bottom grid-hit run allowed visible desktop fallback")
    if not summary.get("UseDdrawProxy"):
        failures.append("right-bottom grid-hit run did not use the DirectDraw proxy")
    if not summary.get("FastForwardStartAnims"):
        failures.append("right-bottom grid-hit run did not fast-forward startup animations")
    if not summary.get("SkipMapValidation"):
        failures.append("right-bottom grid-hit run did not skip map validation for controlled input proof")
    if summary.get("Stage") != RIGHT_BOTTOM_COMPOSE_PATCH_STAGE:
        failures.append("right-bottom grid-hit stage mismatch")
    if not probe_template_matches(
        summary.get("ExtraProbeTemplate"),
        "probes/cdb/ui/clash95_right_bottom_grid_hit_extra.cdb",
    ):
        failures.append("right-bottom grid-hit extra probe template was not recorded")
    if str(summary.get("CandidateSha256") or "").upper() != str(manifest.get("exe_sha256") or "").upper():
        failures.append("right-bottom grid-hit manifest SHA does not match run candidate")
    if manifest.get("stage") != RIGHT_BOTTOM_COMPOSE_PATCH_STAGE:
        failures.append("right-bottom grid-hit manifest stage mismatch")
    if not current_gate.get("passed"):
        failures.append("right-bottom grid-hit manifest did not pass the current HD map gate")
    if int(status_counts.get("original") or 0) != 0 or int(status_counts.get("unexpected") or 0) != 0:
        failures.append("right-bottom grid-hit manifest has original/unexpected selected bytes")
    if int(patch_group.get("patched") or 0) != 4 or int(patch_group.get("total") or 0) != 4:
        failures.append("right-bottom grid-hit patch group is not fully patched")
    if int(surface.get("Width") or 0) != 800 or int(surface.get("Height") or 0) != 600:
        failures.append("right-bottom grid-hit surface was not 800x600")
    if not grid.get("ready"):
        failures.append("right-bottom grid-hit parser did not reach ready state")
    if not grid.get("grid_hit_ok"):
        failures.append("right-bottom grid-hit parser did not prove cell 0 at native coordinate (450,73)")
    if int(grid.get("forced_gate_count") or 0) <= 0:
        failures.append("right-bottom grid-hit hidden flip gate was not reached/forced")
    if int(grid.get("failure_exit_count") or 0) != 0:
        failures.append("right-bottom grid-hit probe used failure exit")
    if int(grid.get("draw_row_count") or 0) <= 0:
        failures.append("right-bottom grid-hit draw rows were not observed")
    if int(grid.get("av_count") or 0) != 0:
        failures.append("right-bottom grid-hit AV rows were observed")

    report = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": "existing hidden-desktop CDB/proxy evidence only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows",
        "run": str(run),
        "summary_json": str(summary_path),
        "log": str(log),
        "manifest": str(manifest_path),
        "screenshot": canonical_capture_path(summary.get("PngPath") or screenshot),
        "parser_summary": grid,
        "summary": {
            "surface_dump_passed": summary.get("Passed"),
            "hidden_desktop": summary.get("HiddenDesktop"),
            "allow_visible_desktop": summary.get("AllowVisibleDesktop"),
            "use_ddraw_proxy": summary.get("UseDdrawProxy"),
            "map_validation_skipped": summary.get("SkipMapValidation"),
            "no_skip_start_anims": summary.get("NoSkipStartAnims"),
            "fast_forward_start_anims": summary.get("FastForwardStartAnims"),
            "stage": summary.get("Stage"),
            "candidate_sha256": summary.get("CandidateSha256"),
            "surface": [surface.get("Width"), surface.get("Height")],
            "current_hd_map_gate": current_gate.get("passed"),
            "right_bottom_patch_group": patch_group,
            "ready": grid.get("ready"),
            "grid_hit_ok": grid.get("grid_hit_ok"),
            "last_grid_entry": grid.get("last_grid_entry"),
            "last_grid_result": grid.get("last_grid_result"),
            "forced_gate_count": grid.get("forced_gate_count"),
            "failure_exit_count": grid.get("failure_exit_count"),
            "draw_row_count": grid.get("draw_row_count"),
            "av_count": grid.get("av_count"),
        },
        "failures": failures,
    }
    write_json(args.right_bottom_grid_hit_json, report)
    write_right_bottom_grid_hit_markdown(args.right_bottom_grid_hit_md, report)
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.right_bottom_grid_hit_json),
        "markdown": str(args.right_bottom_grid_hit_md),
        "run": str(run),
        "summary_json": str(summary_path),
        "screenshot": report["screenshot"],
        "summary": report["summary"],
        "failures": failures,
    }


def build_right_bottom_grid_hit_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "right_bottom_grid_hit_summary parses controlled native grid-hit proof rows",
        "right_bottom_grid_hit_summary CLI writes JSON/Markdown and returns 2 on required proof regressions",
    ]
    failures: list[str] = []
    try:
        test_right_bottom_grid_hit_summary.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for parser CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the right-bottom grid-hit parser requires ready rows, native coordinate "
            "(450,73), expected grid result 0, draw rows, no failure-exit rows, and no AV rows"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.right_bottom_grid_hit_tests_json, result)
    write_right_bottom_grid_hit_tests_markdown(args.right_bottom_grid_hit_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.right_bottom_grid_hit_tests_json),
        "markdown": str(args.right_bottom_grid_hit_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def write_right_bottom_grid_hit_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Right-Bottom Grid Hit Summary Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_right_bottom_grid_hit_probe_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard_args = argparse.Namespace(
        probe_script=args.right_bottom_grid_hit_probe_script,
        summary_parser=args.right_bottom_grid_hit_probe_summary_parser,
        focused_run=args.right_bottom_grid_hit_run,
    )
    guard = right_bottom_grid_hit_probe_guard.build_guard(guard_args)
    write_json(args.right_bottom_grid_hit_probe_guard_json, guard)
    right_bottom_grid_hit_probe_guard.write_markdown(args.right_bottom_grid_hit_probe_guard_md, guard)
    focused = (guard.get("checks") or {}).get("focused_grid_hit_log") or {}
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.right_bottom_grid_hit_probe_guard_json),
        "markdown": str(args.right_bottom_grid_hit_probe_guard_md),
        "summary": {
            "guard_policy": guard.get("guard_policy"),
            "runtime_policy": guard.get("runtime_policy"),
            "expected_stage": guard.get("expected_stage"),
            "grid_hit_ok": focused.get("grid_hit_ok"),
            "last_grid_entry": focused.get("last_grid_entry"),
            "last_grid_result": focused.get("last_grid_result"),
            "failure_exit_count": focused.get("failure_exit_count"),
            "av_count": focused.get("av_count"),
        },
        "failures": guard.get("failures", []),
    }


def write_right_bottom_grid_hit_probe_guard_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Right-Bottom Grid Hit Probe Guard Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_right_bottom_grid_hit_probe_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "right_bottom_grid_hit_probe_guard passes with the focused probe shape and clean hidden-desktop log",
        "right_bottom_grid_hit_probe_guard fails when each owner/action/grid breakpoint is missing",
        "right_bottom_grid_hit_probe_guard fails when each required probe or parser marker is missing",
        "right_bottom_grid_hit_probe_guard fails on visible fallback, wrong stage, or wrong surface size",
        "right_bottom_grid_hit_probe_guard fails on missing grid proof, failure-exit rows, or AV rows",
        "right_bottom_grid_hit_probe_guard CLI writes JSON/Markdown and returns 2 on --require-pass failure",
    ]
    failures: list[str] = []
    try:
        test_right_bottom_grid_hit_probe_guard.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for guard CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the right-bottom grid-hit probe guard rejects missing breakpoints, missing "
            "probe/parser markers, visible fallback, stage/surface regressions, missing grid proof, "
            "failure-exit rows, and AV rows"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.right_bottom_grid_hit_probe_guard_tests_json, result)
    write_right_bottom_grid_hit_probe_guard_tests_markdown(
        args.right_bottom_grid_hit_probe_guard_tests_md,
        result,
    )
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.right_bottom_grid_hit_probe_guard_tests_json),
        "markdown": str(args.right_bottom_grid_hit_probe_guard_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def write_right_bottom_natural_route_guard_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Right-Bottom Natural Route Guard Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_right_bottom_natural_route_guard(args: argparse.Namespace) -> dict[str, Any]:
    report = right_bottom_natural_route_guard.build_report(args.right_bottom_natural_route_run)
    write_json(args.right_bottom_natural_route_guard_json, report)
    right_bottom_natural_route_guard.write_markdown(args.right_bottom_natural_route_guard_md, report)
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.right_bottom_natural_route_guard_json),
        "markdown": str(args.right_bottom_natural_route_guard_md),
        "run": str(args.right_bottom_natural_route_run),
        "summary_json": report.get("summary_json"),
        "screenshot": report.get("screenshot"),
        "summary": report.get("summary", {}),
        "failures": report.get("failures", []),
    }


def build_right_bottom_natural_route_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "right_bottom_natural_route_guard passes when command 99 reaches the owner loop with owner_flag 0x00 and the exact 00433C20 descriptor model",
        "right_bottom_natural_route_guard fails when the action descriptor leaves its expected parked coordinate",
        "right_bottom_natural_route_guard fails when the static owner-loop descriptor model drifts",
        "right_bottom_natural_route_guard fails when owner flag bits allow the action route",
        "right_bottom_natural_route_guard fails when owner/action renderer rows fire",
    ]
    failures: list[str] = []
    try:
        test_right_bottom_natural_route_guard.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only in-process parser code; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the natural right-bottom action-route guard fails closed unless the command-99 "
            "owner loop is reached, the exact 00433C20 owner-loop descriptor model is present, "
            "the 004338E0 descriptor is parked at (1000,426), owner flag bits are zero, "
            "owner/action renderer rows are absent, and no AV rows are present"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.right_bottom_natural_route_guard_tests_json, result)
    write_right_bottom_natural_route_guard_tests_markdown(
        args.right_bottom_natural_route_guard_tests_md,
        result,
    )
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.right_bottom_natural_route_guard_tests_json),
        "markdown": str(args.right_bottom_natural_route_guard_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_right_bottom_natural_route_candidate_matrix(args: argparse.Namespace) -> dict[str, Any]:
    report = right_bottom_natural_route_candidate_matrix.build_report(
        save_scan_json=args.right_bottom_natural_route_candidate_save_scan_json,
        baseline_run=args.right_bottom_natural_route_run,
        slot2_run=args.right_bottom_natural_route_candidate_slot2_run,
        slot5_run=args.right_bottom_natural_route_candidate_slot5_run,
    )
    write_json(args.right_bottom_natural_route_candidate_matrix_json, report)
    right_bottom_natural_route_candidate_matrix.write_markdown(
        args.right_bottom_natural_route_candidate_matrix_md,
        report,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.right_bottom_natural_route_candidate_matrix_json),
        "markdown": str(args.right_bottom_natural_route_candidate_matrix_md),
        "screenshot": report.get("screenshot"),
        "summary": report.get("summary", {}),
        "failures": report.get("failures", []),
    }


def build_right_bottom_natural_route_candidate_matrix_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_right_bottom_natural_route_candidate_matrix,
        tests=[
            "right_bottom_natural_route_candidate_matrix passes with current slot0, slot2, and slot5 blocker shape",
            "right_bottom_natural_route_candidate_matrix fails without a slot5 route-compatible bit-2 record",
            "right_bottom_natural_route_candidate_matrix fails closed if slot5 no longer times out before LOADSAVE",
            "right_bottom_natural_route_candidate_matrix fails closed if slot2 no longer proves the current click misses",
            "right_bottom_natural_route_candidate_matrix CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="Right-Bottom Natural Route Candidate Matrix Tests",
        json_path=args.right_bottom_natural_route_candidate_matrix_tests_json,
        md_path=args.right_bottom_natural_route_candidate_matrix_tests_md,
        guard_policy=(
            "proves the right-bottom natural-route candidate matrix is a non-promoting "
            "repo-only classifier for save-state route candidates and current harness blockers"
        ),
    )


def build_right_bottom_blocker_triage(args: argparse.Namespace) -> dict[str, Any]:
    report = right_bottom_blocker_triage.build_triage(
        compose_evidence_json=args.right_bottom_compose_matrix_json,
        promotion_decision_json=args.right_bottom_compose_decision_json,
        natural_route_json=args.right_bottom_natural_route_guard_json,
        slot_fixture_runtime_plan_json=args.right_bottom_slot_fixture_runtime_plan_json,
        load_slot_entry_gap_json=args.load_slot_entry_gap_json,
        manual_run_plan_json=args.manual_directinput_run_plan_json,
    )
    write_json(args.right_bottom_blocker_triage_json, report)
    right_bottom_blocker_triage.write_markdown(args.right_bottom_blocker_triage_md, report)
    observations = report.get("observations") or {}
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.right_bottom_blocker_triage_json),
        "markdown": str(args.right_bottom_blocker_triage_md),
        "summary": {
            "classification": report.get("classification"),
            "promotion_ready": report.get("promotion_ready"),
            "stable_stage_should_change": report.get("stable_stage_should_change"),
            "natural_ui_owner_action_rows": observations.get("natural_ui_owner_action_rows"),
            "natural_route_action_descriptor": observations.get("natural_route_action_descriptor"),
            "fixture_proof_class": observations.get("fixture_proof_class"),
            "load_slot_gap_classification": observations.get("load_slot_gap_classification"),
            "guard_policy": report.get("guard_policy"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_right_bottom_blocker_triage_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_right_bottom_blocker_triage,
        tests=[
            "right_bottom_blocker_triage passes for the current controlled-recovered but natural-route-blocked shape",
            "right_bottom_blocker_triage fails if controlled composition no longer covers the lower/right UI",
            "right_bottom_blocker_triage fails if the owner-flag gate shape becomes obsolete",
            "right_bottom_blocker_triage fails if the isolated fixture plan becomes promoting",
            "right_bottom_blocker_triage CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="Right-Bottom Blocker Triage Tests",
        json_path=args.right_bottom_blocker_triage_tests_json,
        md_path=args.right_bottom_blocker_triage_tests_md,
        guard_policy=(
            "proves current right-bottom action-menu triage stays non-promoting, "
            "distinguishes controlled composition recovery from natural UI proof, "
            "and fails closed if the owner-flag/load-route blocker shape changes"
        ),
    )


def build_right_bottom_visual_artifact_guard(args: argparse.Namespace) -> dict[str, Any]:
    report = right_bottom_visual_artifact_guard.build_guard(
        compose_evidence_json=args.right_bottom_compose_matrix_json,
        blocker_triage_json=args.right_bottom_blocker_triage_json,
    )
    write_json(args.right_bottom_visual_artifact_guard_json, report)
    right_bottom_visual_artifact_guard.write_markdown(
        args.right_bottom_visual_artifact_guard_md,
        report,
    )
    observations = report.get("observations") or {}
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.right_bottom_visual_artifact_guard_json),
        "markdown": str(args.right_bottom_visual_artifact_guard_md),
        "summary": {
            "visual_status": report.get("visual_status"),
            "promotion_ready": report.get("promotion_ready"),
            "stable_stage_should_change": report.get("stable_stage_should_change"),
            "natural_owner_action_rows": observations.get("natural_owner_action_rows"),
            "natural_bottom_right_corner_black": observations.get("natural_bottom_right_corner_black"),
            "natural_r8c10_black": observations.get("natural_r8c10_black"),
            "natural_r8c11_black": observations.get("natural_r8c11_black"),
            "guard_policy": report.get("guard_policy"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_right_bottom_visual_artifact_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_right_bottom_visual_artifact_guard,
        tests=[
            "right_bottom_visual_artifact_guard passes for the resolved fixture-accepted natural-draw state",
            "right_bottom_visual_artifact_guard fails if blocker triage is missing",
            "right_bottom_visual_artifact_guard accepts the current and legacy non-promoting triage classifications",
            "right_bottom_visual_artifact_guard fails closed if the fixture natural-draw payload is missing",
            "right_bottom_visual_artifact_guard fails closed if any fixture natural-draw marker regresses",
            "right_bottom_visual_artifact_guard fails closed if the fixture natural-draw log has AV rows",
            "right_bottom_visual_artifact_guard fails if the compose matrix stops passing",
            "right_bottom_visual_artifact_guard fails if the compose matrix would flip stable promotion",
            "right_bottom_visual_artifact_guard fails if controlled composition recovery regresses",
            "right_bottom_visual_artifact_guard CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="Right-Bottom Visual Artifact Guard Tests",
        json_path=args.right_bottom_visual_artifact_guard_tests_json,
        md_path=args.right_bottom_visual_artifact_guard_tests_md,
        guard_policy=(
            "proves the right-bottom visual artifact guard validates the resolved state "
            "(user ruling 2026-07-14: slot5-as-slot0 fixture accepted as natural-draw evidence) "
            "with promotion still deferred, and fails closed if the fixture evidence, compose "
            "matrix, triage, or controlled recovery state changes"
        ),
    )


def build_first_mission_visual_audit(args: argparse.Namespace) -> dict[str, Any]:
    audit_args = argparse.Namespace(
        threshold=args.first_mission_visual_threshold,
        bright_threshold=args.first_mission_visual_bright_threshold,
        diff_threshold=args.first_mission_visual_diff_threshold,
        max_stripe_high_percent=args.first_mission_visual_max_stripe_high_percent,
        max_stripe_excess_percent=args.first_mission_visual_max_stripe_excess_percent,
        real_runtime_frame=first_mission_visual_audit.REAL_RUNTIME_CORROBORATION_FRAME,
    )
    report = first_mission_visual_audit.build_report(
        first_mission_visual_audit.DEFAULT_FRAMES,
        audit_args,
    )
    first_mission_visual_audit.write_json(args.first_mission_visual_audit_json, report)
    first_mission_visual_audit.write_markdown(args.first_mission_visual_audit_md, report)
    summary = report.get("summary") or {}
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.first_mission_visual_audit_json),
        "markdown": str(args.first_mission_visual_audit_md),
        "summary": {
            "current_status": report.get("current_status"),
            "first_mission_visual_clean": report.get("first_mission_visual_clean"),
            "primary_frame": report.get("primary_frame"),
            "primary_frame_path": report.get("primary_frame_path"),
            "next_probe": report.get("next_probe") or summary.get("next_probe"),
            "primary_play_area_nonblack": summary.get("primary_play_area_nonblack"),
            "primary_selected_action_bar_visible": summary.get("primary_selected_action_bar_visible"),
            "primary_legacy_middle_action_bar_visible": summary.get(
                "primary_legacy_middle_action_bar_visible"
            ),
            "primary_black_patch_regions": summary.get("primary_black_patch_regions"),
            "primary_black_patch_details": summary.get("primary_black_patch_details"),
            "stripe_failure_frames": summary.get("stripe_failure_frames"),
            "diagnostic_black_frames": summary.get("diagnostic_black_frames"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_first_mission_visual_audit_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_first_mission_visual_audit,
        tests=[
            "first_mission_visual_audit passes a clean first-mission frame",
            "first_mission_visual_audit fails horizontal stripe signatures",
            "first_mission_visual_audit fails large black patch regions",
            "first_mission_visual_audit excuses a proxy-black region only when a real-runtime frame corroborates it as rendered",
            "first_mission_visual_audit keeps a proxy-black region failing when the real-runtime frame is also black",
            "first_mission_visual_audit fails legacy middle action-bar placement",
            "first_mission_visual_audit reports diagnostic black frames",
            "first_mission_visual_audit CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="First Mission Visual Audit Tests",
        json_path=args.first_mission_visual_audit_tests_json,
        md_path=args.first_mission_visual_audit_tests_md,
        guard_policy=(
            "proves first-mission visual audit detects stripe signatures, large black UI patches, "
            "legacy middle action-bar placement, and diagnostic black frames, and only excuses proxy-black "
            "regions with positive real-runtime corroboration, without launching runtime"
        ),
    )


def build_border_frame_restore_check(args: argparse.Namespace) -> dict[str, Any]:
    check_args = argparse.Namespace(
        evidence_json=args.border_frame_restore_evidence_json,
        realruntime_json=args.border_frame_restore_realruntime_json,
        proxy_run_token=border_frame_restore_check.DEFAULT_PROXY_RUN_TOKEN,
        real_runtime_run_token=border_frame_restore_check.DEFAULT_REAL_RUNTIME_RUN_TOKEN,
        repo_root=border_frame_restore_check.REPO_ROOT,
    )
    report = border_frame_restore_check.build_check(check_args)
    write_json(args.border_frame_restore_check_json, report)
    border_frame_restore_check.write_markdown(args.border_frame_restore_check_md, report)
    checks = report.get("checks") or {}
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.border_frame_restore_check_json),
        "markdown": str(args.border_frame_restore_check_md),
        "summary": {
            "patch_group": report.get("patch_group"),
            "validation_stage": report.get("validation_stage"),
            "real_runtime_frames": report.get("real_runtime_frames"),
            "proxy_surface_evidence_passed": bool(
                (checks.get("proxy_surface_evidence") or {}).get("passed")
            ),
            "real_runtime_evidence_passed": bool(
                (checks.get("real_runtime_evidence") or {}).get("passed")
            ),
            "guard_policy": report.get("guard_policy"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_border_frame_restore_check_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_border_frame_restore_check,
        tests=[
            "border_frame_restore_check passes the committed proxy plus real-runtime band evidence shape",
            "border_frame_restore_check fails when an evidence file is missing",
            "border_frame_restore_check fails when a border band region disappears",
            "border_frame_restore_check fails when an HD extension band goes black",
            "border_frame_restore_check fails when histogram authenticity similarity drops below the minimum",
            "border_frame_restore_check fails when the recorded gate failed",
            "border_frame_restore_check fails when the recorded gate thresholds were weakened",
            "border_frame_restore_check fails when the real-runtime frame reference is missing",
            "border_frame_restore_check fails when a referenced source frame no longer exists",
            "border_frame_restore_check CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="Border Frame-Restore Check Tests",
        json_path=args.border_frame_restore_check_tests_json,
        md_path=args.border_frame_restore_check_tests_md,
        guard_policy=(
            "proves the frame-restore-bands lane keeps every border band, passing "
            "authenticity gates at frozen thresholds, and a resolvable real-runtime "
            "frame reference, failing closed on any missing file or field"
        ),
    )


def build_right_bottom_slot_fixture_plan(args: argparse.Namespace) -> dict[str, Any]:
    report = right_bottom_slot_fixture_plan.build_plan(
        candidate_matrix_json=args.right_bottom_natural_route_candidate_matrix_json,
        load_slot_route_limit_json=args.load_slot_route_limit_json,
        fixture_root=args.right_bottom_slot_fixture_root,
        repo_root=Path.cwd(),
    )
    write_json(args.right_bottom_slot_fixture_plan_json, report)
    right_bottom_slot_fixture_plan.write_markdown(args.right_bottom_slot_fixture_plan_md, report)
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.right_bottom_slot_fixture_plan_json),
        "markdown": str(args.right_bottom_slot_fixture_plan_md),
        "summary": report.get("summary", {}),
        "failures": report.get("failures", []),
    }


def build_right_bottom_slot_fixture_plan_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_right_bottom_slot_fixture_plan,
        tests=[
            "right_bottom_slot_fixture_plan passes with current slot5-as-slot0 non-promoting fixture shape",
            "right_bottom_slot_fixture_plan fails if the candidate matrix becomes promotion-ready",
            "right_bottom_slot_fixture_plan fails if slot5 is no longer blocked before LOADSAVE",
            "right_bottom_slot_fixture_plan fails if the fixture output would be inside the repository",
            "right_bottom_slot_fixture_plan CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="Right-Bottom Slot Fixture Plan Tests",
        json_path=args.right_bottom_slot_fixture_plan_tests_json,
        md_path=args.right_bottom_slot_fixture_plan_tests_md,
        guard_policy=(
            "proves the isolated slot5-as-slot0 workaround remains non-promoting, "
            "safe to stage outside the repository, and invalid once natural slot5 loading is proven"
        ),
    )


def build_right_bottom_slot_fixture_script_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard = right_bottom_slot_fixture_script_guard.build_guard(args.right_bottom_slot_fixture_script)
    write_json(args.right_bottom_slot_fixture_script_guard_json, guard)
    right_bottom_slot_fixture_script_guard.write_markdown(
        args.right_bottom_slot_fixture_script_guard_md,
        guard,
    )
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.right_bottom_slot_fixture_script_guard_json),
        "markdown": str(args.right_bottom_slot_fixture_script_guard_md),
        "summary": {
            "guard_policy": guard.get("guard_policy"),
            "runtime_policy": guard.get("runtime_policy"),
            "script": guard.get("script"),
            "dry_run_exit_line": guard.get("dry_run_exit_line"),
            "copy_line": guard.get("copy_line"),
            "risky_visible_lines": guard.get("risky_visible_lines"),
        },
        "failures": guard.get("failures", []),
    }


def build_right_bottom_slot_fixture_script_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_right_bottom_slot_fixture_script_guard,
        tests=[
            "right_bottom_slot_fixture_script_guard passes with dry-run gated fixture copy shape",
            "right_bottom_slot_fixture_script_guard fails without the -Execute dry-run gate",
            "right_bottom_slot_fixture_script_guard fails if Copy-Item can run before dry-run exit",
            "right_bottom_slot_fixture_script_guard fails without the live C:\\Clash\\save output guard",
            "right_bottom_slot_fixture_script_guard fails without the workdir seed save-directory exclusion",
            "right_bottom_slot_fixture_script_guard fails on visible/runtime launcher APIs",
            "right_bottom_slot_fixture_script_guard CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="Right-Bottom Slot Fixture Script Guard Tests",
        json_path=args.right_bottom_slot_fixture_script_guard_tests_json,
        md_path=args.right_bottom_slot_fixture_script_guard_tests_md,
        guard_policy=(
            "proves the right-bottom fixture preparation helper stays dry-run by default, "
            "copies only after -Execute, refuses live-save/repo outputs, and avoids visible-runtime APIs"
        ),
    )


def build_right_bottom_slot_fixture_runtime_plan(args: argparse.Namespace) -> dict[str, Any]:
    report = right_bottom_slot_fixture_runtime_plan.build_plan(
        fixture_plan_json=args.right_bottom_slot_fixture_plan_json,
        script_guard_json=args.right_bottom_slot_fixture_script_guard_json,
        surface_dump_script=args.right_bottom_slot_fixture_runtime_surface_dump_script,
        extra_probe=args.right_bottom_slot_fixture_runtime_extra_probe,
        result_parser=args.right_bottom_slot_fixture_result_parser,
        stage=args.right_bottom_slot_fixture_runtime_stage,
        repo_root=Path.cwd(),
    )
    write_json(args.right_bottom_slot_fixture_runtime_plan_json, report)
    right_bottom_slot_fixture_runtime_plan.write_markdown(
        args.right_bottom_slot_fixture_runtime_plan_md,
        report,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.right_bottom_slot_fixture_runtime_plan_json),
        "markdown": str(args.right_bottom_slot_fixture_runtime_plan_md),
        "summary": report.get("summary", {}),
        "failures": report.get("failures", []),
    }


def build_right_bottom_slot_fixture_runtime_plan_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_right_bottom_slot_fixture_runtime_plan,
        tests=[
            "right_bottom_slot_fixture_runtime_plan builds hidden fixture preparation and CDB commands",
            "right_bottom_slot_fixture_runtime_plan requires strict selected_arg/selected_global slot-0 fixture acceptance",
            "right_bottom_slot_fixture_runtime_plan fails if the fixture plan becomes promoting",
            "right_bottom_slot_fixture_runtime_plan fails if the preparation script guard fails",
            "right_bottom_slot_fixture_runtime_plan fails if the preparation script no longer seeds non-save workdir files",
            "right_bottom_slot_fixture_runtime_plan fails if the fixture result parser is missing",
            "right_bottom_slot_fixture_runtime_plan fails if the fixture root is inside the repository",
            "right_bottom_slot_fixture_runtime_plan CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="Right-Bottom Slot Fixture Runtime Plan Tests",
        json_path=args.right_bottom_slot_fixture_runtime_plan_tests_json,
        md_path=args.right_bottom_slot_fixture_runtime_plan_tests_md,
        guard_policy=(
            "proves the future slot fixture runtime route stays hidden-desktop, "
            "uses an isolated workdir plus child candidate dir, requires strict fixture "
            "slot acceptance, and remains non-promoting"
        ),
    )


def build_right_bottom_slot_fixture_result_summary_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_right_bottom_slot_fixture_result_summary,
        tests=[
            "right_bottom_slot_fixture_result_summary classifies owner/action success",
            "right_bottom_slot_fixture_result_summary classifies owner-flag-blocked fixture logs",
            "right_bottom_slot_fixture_result_summary classifies missing LOADSAVE/PlayGame logs",
            "right_bottom_slot_fixture_result_summary classifies owner-loop-without-action logs",
            "right_bottom_slot_fixture_result_summary fails closed on AV rows",
            "right_bottom_slot_fixture_result_summary fails closed on conflicting LOADSAVE slot fields",
            "right_bottom_slot_fixture_result_summary fails closed on wrong LOADSAVE slot",
            "right_bottom_slot_fixture_result_summary CLI writes JSON/Markdown and honors owner-action gates",
            "right_bottom_slot_fixture_result_summary CLI fails when owner/action is required but blocked",
            "right_bottom_slot_fixture_result_summary CLI fails when slot match is required but LOADSAVE fields conflict",
        ],
        title="Right-Bottom Slot Fixture Result Summary Tests",
        json_path=args.right_bottom_slot_fixture_result_summary_tests_json,
        md_path=args.right_bottom_slot_fixture_result_summary_tests_md,
        guard_policy=(
            "proves future right-bottom slot fixture CDB logs can be classified as load failure, "
            "owner-flag blocked, owner-loop without action, owner/action reached, slot mismatch, or "
            "AV failure with strict LOADSAVE slot consistency"
        ),
    )


def build_load_slot_route_limit_guard(args: argparse.Namespace) -> dict[str, Any]:
    report = load_slot_route_limit_guard.build_report(
        decomp_c=args.load_slot_route_limit_decomp_c,
        surface_probe_script=args.load_slot_route_limit_surface_probe_script,
        slot2_run=args.load_slot_route_limit_slot2_run,
        slot3_run=args.load_slot_route_limit_slot3_run,
        slot4_run=args.load_slot_route_limit_slot4_run,
        slot5_run=args.load_slot_route_limit_slot5_run,
        recent_slot5_run=args.load_slot_route_limit_recent_slot5_run,
    )
    write_json(args.load_slot_route_limit_json, report)
    load_slot_route_limit_guard.write_markdown(args.load_slot_route_limit_md, report)
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.load_slot_route_limit_json),
        "markdown": str(args.load_slot_route_limit_md),
        "screenshot": report.get("screenshot"),
        "summary": report.get("summary", {}),
        "failures": report.get("failures", []),
    }


def build_load_slot_route_limit_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_load_slot_route_limit_guard,
        tests=[
            "load_slot_route_limit_guard passes with static ten-row evidence, slot2 LOADSAVE, and slot3-5 timeout blockers",
            "load_slot_route_limit_guard fails without static ten-row load-menu evidence",
            "load_slot_route_limit_guard fails when the proven slot2 route no longer reaches LOADSAVE",
            "load_slot_route_limit_guard fails closed when a currently blocked slot reaches LOADSAVE",
            "load_slot_route_limit_guard fails closed when a currently blocked slot reaches forced load-select",
            "load_slot_route_limit_guard CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="Load Slot Route Limit Guard Tests",
        json_path=args.load_slot_route_limit_tests_json,
        md_path=args.load_slot_route_limit_tests_md,
        guard_policy=(
            "proves the load-slot route boundary remains a non-promoting "
            "repo-only classifier for the current slot5/right-bottom harness blocker"
        ),
    )


def build_load_slot_timeout_phase(args: argparse.Namespace) -> dict[str, Any]:
    report = load_slot_timeout_phase.build_report(
        slot2_run=args.load_slot_timeout_phase_slot2_run,
        slot3_run=args.load_slot_timeout_phase_slot3_run,
        slot4_run=args.load_slot_timeout_phase_slot4_run,
        slot5_run=args.load_slot_timeout_phase_slot5_run,
        recent_slot5_run=args.load_slot_timeout_phase_recent_slot5_run,
    )
    write_json(args.load_slot_timeout_phase_json, report)
    load_slot_timeout_phase.write_markdown(args.load_slot_timeout_phase_md, report)
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.load_slot_timeout_phase_json),
        "markdown": str(args.load_slot_timeout_phase_md),
        "screenshot": report.get("screenshot"),
        "summary": report.get("summary", {}),
        "failures": report.get("failures", []),
    }


def build_load_slot_timeout_phase_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_load_slot_timeout_phase,
        tests=[
            "load_slot_timeout_phase passes when slot2 reaches load-menu accept and slots3-5 stall before load-menu entry",
            "load_slot_timeout_phase fails when slot2 no longer reaches LOADSAVE",
            "load_slot_timeout_phase fails when a blocked slot reaches load-menu entry",
            "load_slot_timeout_phase CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="Load Slot Timeout Phase Tests",
        json_path=args.load_slot_timeout_phase_tests_json,
        md_path=args.load_slot_timeout_phase_tests_md,
        guard_policy=(
            "proves the load-slot timeout phase classifier preserves the current "
            "pre-load-menu-loop blocker shape for rows 3-5"
        ),
    )


def build_load_slot_entry_gap(args: argparse.Namespace) -> dict[str, Any]:
    report = load_slot_entry_gap_plan.build_report(
        decomp_c=args.load_slot_entry_gap_decomp_c,
        cdb_probe=args.load_slot_entry_gap_cdb_probe,
        timeout_phase_json=args.load_slot_entry_gap_timeout_phase_json,
    )
    write_json(args.load_slot_entry_gap_json, report)
    load_slot_entry_gap_plan.write_markdown(args.load_slot_entry_gap_md, report)
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.load_slot_entry_gap_json),
        "markdown": str(args.load_slot_entry_gap_md),
        "screenshot": report.get("screenshot"),
        "summary": report.get("summary", {}),
        "failures": report.get("failures", []),
    }


def build_load_slot_entry_gap_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_load_slot_entry_gap_plan,
        tests=[
            "load_slot_entry_gap_plan passes with static case-5 row-loop evidence and current pre-entry blocked rows",
            "load_slot_entry_gap_plan fails without the static ten-row case-5 loop",
            "load_slot_entry_gap_plan fails without the 0044895A load-menu-entry breakpoint",
            "load_slot_entry_gap_plan fails without the pre-entry load-coordinate row",
            "load_slot_entry_gap_plan fails closed when a blocked row reaches load-menu entry",
            "load_slot_entry_gap_plan fails when slot2 no longer reaches LOADSAVE",
            "load_slot_entry_gap_plan CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="Load Slot Entry Gap Tests",
        json_path=args.load_slot_entry_gap_tests_json,
        md_path=args.load_slot_entry_gap_tests_md,
        guard_policy=(
            "proves the load-slot entry-gap report preserves the distinction between "
            "early descriptor rows and real load-menu case entry"
        ),
    )


def build_load_slot_transition_probe_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard = load_slot_transition_probe_guard.build_guard(
        probe=args.load_slot_transition_probe,
        surface_dump_script=args.load_slot_transition_surface_dump_script,
    )
    write_json(args.load_slot_transition_probe_guard_json, guard)
    load_slot_transition_probe_guard.write_markdown(args.load_slot_transition_probe_guard_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.load_slot_transition_probe_guard_json),
        "markdown": str(args.load_slot_transition_probe_guard_md),
        "summary": guard.get("summary", {}),
        "failures": guard.get("failures", []),
    }


def build_load_slot_transition_probe_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_load_slot_transition_probe_guard,
        tests=[
            "load_slot_transition_probe_guard passes with the late-entry transition probe and extra placeholder replacement",
            "load_slot_transition_probe_guard fails if the probe reintroduces early 00419B80 descriptor forcing",
            "load_slot_transition_probe_guard fails if the extra probe has a standalone g command",
            "load_slot_transition_probe_guard fails if the runner does not replace extra probe load-slot placeholders",
            "load_slot_transition_probe_guard fails if late select/accept are hard-coded to slot 5",
            "load_slot_transition_probe_guard CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="Load Slot Transition Probe Guard Tests",
        json_path=args.load_slot_transition_probe_guard_tests_json,
        md_path=args.load_slot_transition_probe_guard_tests_md,
        guard_policy=(
            "proves the focused transition extra probe and surface-dump runner are ready "
            "for parameterized late-armed load-row selection after real load-menu entry"
        ),
    )


def build_load_slot_transition_run_plan(args: argparse.Namespace) -> dict[str, Any]:
    report = load_slot_transition_run_plan.build_plan(
        entry_gap_json=args.load_slot_entry_gap_json,
        probe_guard_json=args.load_slot_transition_probe_guard_json,
        surface_dump_script=args.load_slot_transition_surface_dump_script,
        extra_probe=args.load_slot_transition_probe,
        result_parser=args.load_slot_transition_result_parser,
        candidate_root=args.load_slot_transition_candidate_root,
        result_root=args.load_slot_transition_result_root,
        repo_root=Path.cwd(),
    )
    write_json(args.load_slot_transition_run_plan_json, report)
    load_slot_transition_run_plan.write_markdown(args.load_slot_transition_run_plan_md, report)
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.load_slot_transition_run_plan_json),
        "markdown": str(args.load_slot_transition_run_plan_md),
        "summary": report.get("summary", {}),
        "failures": report.get("failures", []),
    }


def build_load_slot_transition_run_plan_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_load_slot_transition_run_plan,
        tests=[
            "load_slot_transition_run_plan builds hidden transition commands for rows 3, 4, and 5",
            "load_slot_transition_run_plan fails if the blocked row set changes",
            "load_slot_transition_run_plan fails if the transition probe guard is not passing",
            "load_slot_transition_run_plan fails if early descriptor forcing returns",
            "load_slot_transition_run_plan fails if extra-probe placeholder replacement is missing",
            "load_slot_transition_run_plan fails if late select/accept are not target-slot parameterized",
            "load_slot_transition_run_plan fails if the candidate root is inside the repository",
            "load_slot_transition_run_plan CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="Load Slot Transition Run Plan Tests",
        json_path=args.load_slot_transition_run_plan_tests_json,
        md_path=args.load_slot_transition_run_plan_tests_md,
        guard_policy=(
            "proves the transition command plan stays hidden, targets the current rows 3-5 "
            "pre-entry blocker, and remains non-promoting"
        ),
    )


def build_load_slot_transition_geometry_guard(args: argparse.Namespace) -> dict[str, Any]:
    report = load_slot_transition_geometry_guard.build_guard(
        run_plan_json=args.load_slot_transition_run_plan_json,
        surface_dump_script=args.load_slot_transition_surface_dump_script,
        extra_probe=args.load_slot_transition_probe,
    )
    write_json(args.load_slot_transition_geometry_guard_json, report)
    load_slot_transition_geometry_guard.write_markdown(
        args.load_slot_transition_geometry_guard_md,
        report,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.load_slot_transition_geometry_guard_json),
        "markdown": str(args.load_slot_transition_geometry_guard_md),
        "summary": report.get("summary", {}),
        "failures": report.get("failures", []),
    }


def build_load_slot_transition_geometry_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_load_slot_transition_geometry_guard,
        tests=[
            "load_slot_transition_geometry_guard records expected row geometry for slots 3, 4, and 5",
            "load_slot_transition_geometry_guard fails if the load-row formula drifts",
            "load_slot_transition_geometry_guard fails if CDB mouse placeholders are missing",
            "load_slot_transition_geometry_guard fails if commands target the wrong row",
            "load_slot_transition_geometry_guard fails if summary commands stop requiring entry",
            "load_slot_transition_geometry_guard CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="Load Slot Transition Geometry Guard Tests",
        json_path=args.load_slot_transition_geometry_guard_tests_json,
        md_path=args.load_slot_transition_geometry_guard_tests_md,
        guard_policy=(
            "proves the transition plan stays tied to x=320, y=166+22*slot row geometry "
            "and requires entry/slot-match summaries"
        ),
    )


def build_load_slot_transition_probe_preview(args: argparse.Namespace) -> dict[str, Any]:
    report = load_slot_transition_probe_preview.build_report(
        run_plan_json=args.load_slot_transition_run_plan_json,
        geometry_guard_json=args.load_slot_transition_geometry_guard_json,
        extra_probe=args.load_slot_transition_probe,
    )
    write_json(args.load_slot_transition_probe_preview_json, report)
    load_slot_transition_probe_preview.write_markdown(
        args.load_slot_transition_probe_preview_md,
        report,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.load_slot_transition_probe_preview_json),
        "markdown": str(args.load_slot_transition_probe_preview_md),
        "summary": report.get("summary", {}),
        "failures": report.get("failures", []),
    }


def build_load_slot_transition_probe_preview_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_load_slot_transition_probe_preview,
        tests=[
            "load_slot_transition_probe_preview renders row-specific previews for slots 3, 4, and 5",
            "load_slot_transition_probe_preview fails if placeholders survive generation",
            "load_slot_transition_probe_preview fails if select/accept conditions are hard-coded",
            "load_slot_transition_probe_preview fails if geometry rows do not match the run plan",
            "load_slot_transition_probe_preview fails if the run plan is not passing",
            "load_slot_transition_probe_preview CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="Load Slot Transition Probe Preview Tests",
        json_path=args.load_slot_transition_probe_preview_tests_json,
        md_path=args.load_slot_transition_probe_preview_tests_md,
        guard_policy=(
            "proves generated row-specific transition probes have no unresolved placeholders, "
            "keep slot-specific select/accept conditions, and preserve the planned raw mouse values"
        ),
    )


def build_load_slot_transition_readiness(args: argparse.Namespace) -> dict[str, Any]:
    report = load_slot_transition_readiness_matrix.build_matrix(
        entry_gap_json=args.load_slot_entry_gap_json,
        probe_guard_json=args.load_slot_transition_probe_guard_json,
        run_plan_json=args.load_slot_transition_run_plan_json,
        geometry_guard_json=args.load_slot_transition_geometry_guard_json,
        probe_preview_json=args.load_slot_transition_probe_preview_json,
        summary_tests_json=args.load_slot_transition_summary_tests_json,
    )
    write_json(args.load_slot_transition_readiness_json, report)
    load_slot_transition_readiness_matrix.write_markdown(
        args.load_slot_transition_readiness_md,
        report,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.load_slot_transition_readiness_json),
        "markdown": str(args.load_slot_transition_readiness_md),
        "summary": report.get("summary", {}),
        "failures": report.get("failures", []),
    }


def build_load_slot_transition_readiness_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_load_slot_transition_readiness_matrix,
        tests=[
            "load_slot_transition_readiness_matrix passes for the current hidden rows 3-5 transition plan",
            "load_slot_transition_readiness_matrix fails if a planned command allows visible runtime",
            "load_slot_transition_readiness_matrix fails if summary commands stop requiring entry proof",
            "load_slot_transition_readiness_matrix fails if result acceptance stops requiring target-slot consistency",
            "load_slot_transition_readiness_matrix fails if generated previews drift from rows 3-5",
            "load_slot_transition_readiness_matrix fails if transition readiness becomes promoting",
            "load_slot_transition_readiness_matrix CLI writes JSON/Markdown and honors --require-pass",
        ],
        title="Load Slot Transition Readiness Matrix Tests",
        json_path=args.load_slot_transition_readiness_tests_json,
        md_path=args.load_slot_transition_readiness_tests_md,
        guard_policy=(
            "proves the aggregate transition readiness report stays hidden-desktop, "
            "row-specific, strict about summary and target-slot acceptance, and non-promoting"
        ),
    )


def build_load_slot_transition_summary_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_load_slot_transition_summary,
        tests=[
            "load_slot_transition_summary classifies late-entry LOADSAVE/PlayGame success",
            "load_slot_transition_summary classifies pre-entry stalls before 0044895A",
            "load_slot_transition_summary classifies load-menu entry without LOADSAVE",
            "load_slot_transition_summary fails closed on AV evidence",
            "load_slot_transition_summary fails closed on conflicting target_slot rows",
            "load_slot_transition_summary fails closed on LOADSAVE slot mismatch",
            "load_slot_transition_summary CLI writes JSON/Markdown and honors success requirements",
            "load_slot_transition_summary CLI fails when entry is required but absent",
            "load_slot_transition_summary CLI fails when slot match is required but target_slot conflicts",
        ],
        title="Load Slot Transition Summary Tests",
        json_path=args.load_slot_transition_summary_tests_json,
        md_path=args.load_slot_transition_summary_tests_md,
        guard_policy=(
            "proves future LSTRANS logs can be classified as pre-entry stalls, "
            "entry-without-LOADSAVE blockers, or late-entry load success, and "
            "fails closed on target-slot drift"
        ),
    )


def build_right_bottom_owner_flag_static_guard(args: argparse.Namespace) -> dict[str, Any]:
    report = right_bottom_owner_flag_static_guard.build_guard(args.right_bottom_owner_flag_static_exe)
    write_json(args.right_bottom_owner_flag_static_guard_json, report)
    right_bottom_owner_flag_static_guard.write_markdown(
        args.right_bottom_owner_flag_static_guard_md,
        report,
    )
    summary = report.get("summary", {})
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.right_bottom_owner_flag_static_guard_json),
        "markdown": str(args.right_bottom_owner_flag_static_guard_md),
        "summary": {
            "exe": report.get("exe"),
            "actual_sha256": report.get("actual_sha256"),
            "pattern_count": summary.get("pattern_count"),
            "passed_pattern_count": summary.get("passed_pattern_count"),
            "command_99_callback_verified": summary.get("command_99_callback_verified"),
            "owner_globals_verified": summary.get("owner_globals_verified"),
            "action_bit2_gate_verified": summary.get("action_bit2_gate_verified"),
            "owner_loop_bit_gates_verified": summary.get("owner_loop_bit_gates_verified"),
            "guard_policy": report.get("guard_policy"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def write_right_bottom_owner_flag_static_guard_tests_markdown(
    path: Path,
    result: dict[str, Any],
) -> None:
    lines = [
        "# Right-Bottom Owner-Flag Static Guard Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_right_bottom_owner_flag_static_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "right_bottom_owner_flag_static_guard accepts the expected command-99, owner-global, action-gate, and owner-loop byte patterns",
        "right_bottom_owner_flag_static_guard rejects byte drift in the 004338E0 bit-2 early-return gate",
        "right_bottom_owner_flag_static_guard rejects original executable SHA drift",
        "right_bottom_owner_flag_static_guard CLI writes JSON/Markdown and fails closed under --require-pass",
    ]
    failures: list[str] = []
    try:
        test_right_bottom_owner_flag_static_guard.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for guard CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the static owner-flag guard fails closed on executable SHA drift, "
            "004338E0 gate drift, and missing local executable evidence"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.right_bottom_owner_flag_static_guard_tests_json, result)
    write_right_bottom_owner_flag_static_guard_tests_markdown(
        args.right_bottom_owner_flag_static_guard_tests_md,
        result,
    )
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.right_bottom_owner_flag_static_guard_tests_json),
        "markdown": str(args.right_bottom_owner_flag_static_guard_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_right_bottom_owner_flag_inventory(args: argparse.Namespace) -> dict[str, Any]:
    report = right_bottom_owner_flag_inventory.build_report(args.captures_root)
    write_json(args.right_bottom_owner_flag_inventory_json, report)
    right_bottom_owner_flag_inventory.write_markdown(
        args.right_bottom_owner_flag_inventory_md,
        report,
        args.right_bottom_owner_flag_inventory_max_markdown_rows,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.right_bottom_owner_flag_inventory_json),
        "markdown": str(args.right_bottom_owner_flag_inventory_md),
        "summary": {
            "scanned_log_count": report.get("scanned_log_count"),
            "relevant_run_count": report.get("relevant_run_count"),
            "classification_counts": report.get("classification_counts"),
            "natural_state_gated_count": report.get("natural_state_gated_count"),
            "forced_owner_action_route_count": report.get("forced_owner_action_route_count"),
            "natural_action_route_count": report.get("natural_action_route_count"),
            "guard_policy": report.get("guard_policy"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_right_bottom_owner_flag_inventory_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_right_bottom_owner_flag_inventory,
        tests=[
            "right_bottom_owner_flag_inventory classifies the natural owner-flag blocker, controlled forced owner route, and descriptor-only UI run",
            "right_bottom_owner_flag_inventory fails closed if an archived natural route already reaches owner/action rows",
            "right_bottom_owner_flag_inventory CLI writes JSON/Markdown and fails closed under --require-pass",
        ],
        title="Right-Bottom Owner-Flag Inventory Tests",
        json_path=args.right_bottom_owner_flag_inventory_tests_json,
        md_path=args.right_bottom_owner_flag_inventory_tests_md,
        guard_policy=(
            "proves the owner-flag inventory preserves the current right-bottom conclusion: "
            "forced owner/action routes exist, the natural command-99 route is owner-flag gated, "
            "and no natural route already reaches owner/action rows"
        ),
    )


def build_right_bottom_route_timing_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard_args = argparse.Namespace(
        patch_run=args.right_bottom_compose_patch_run,
        fullstart_run=args.right_bottom_compose_fullstart_run,
        grid_run=args.right_bottom_grid_hit_run,
    )
    guard = right_bottom_route_timing_guard.build_guard(guard_args)
    write_json(args.right_bottom_route_timing_guard_json, guard)
    right_bottom_route_timing_guard.write_markdown(args.right_bottom_route_timing_guard_md, guard)
    checks = guard.get("checks") or {}
    grid = checks.get("grid_route") or {}
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.right_bottom_route_timing_guard_json),
        "markdown": str(args.right_bottom_route_timing_guard_md),
        "summary": {
            "guard_policy": guard.get("guard_policy"),
            "runtime_policy": guard.get("runtime_policy"),
            "candidate_sha256": guard.get("candidate_sha256"),
            "patch_route_ordered_markers": len((checks.get("patch_route") or {}).get("ordered_markers") or []),
            "fullstart_route_ordered_markers": len((checks.get("fullstart_route") or {}).get("ordered_markers") or []),
            "grid_route_ordered_markers": len(grid.get("ordered_markers") or []),
            "grid_hit_ok": grid.get("grid_hit_ok"),
            "last_grid_entry": grid.get("last_grid_entry"),
            "last_grid_result": grid.get("last_grid_result"),
            "failure_exit_count": grid.get("failure_exit_count"),
            "av_count": grid.get("av_count"),
        },
        "failures": guard.get("failures", []),
    }


def write_right_bottom_route_timing_guard_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Right-Bottom Route Timing Guard Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_right_bottom_route_timing_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "right_bottom_route_timing_guard passes with clean hidden patch/full-start/grid logs",
        "right_bottom_route_timing_guard fails when a required route/copyback marker is missing",
        "right_bottom_route_timing_guard fails when marker order regresses",
        "right_bottom_route_timing_guard fails on visible fallback, wrong surface, wrong stage, or SHA disagreement",
        "right_bottom_route_timing_guard fails on grid proof, failure-exit, or AV regressions",
        "right_bottom_route_timing_guard CLI writes JSON/Markdown and returns 2 on --require-pass failure",
    ]
    failures: list[str] = []
    try:
        test_right_bottom_route_timing_guard.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for guard CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the right-bottom route timing guard rejects missing copyback/grid markers, "
            "marker-order regressions, visible fallback, surface/stage/SHA drift, grid proof failures, "
            "failure-exit rows, and AV rows"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.right_bottom_route_timing_guard_tests_json, result)
    write_right_bottom_route_timing_guard_tests_markdown(
        args.right_bottom_route_timing_guard_tests_md,
        result,
    )
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.right_bottom_route_timing_guard_tests_json),
        "markdown": str(args.right_bottom_route_timing_guard_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def write_battle_ui_summary_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Battle UI Summary Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_battle_ui_summary_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "battle_ui_summary classifies centered native battle rows with command, grid, and modal proof",
        "battle_ui_summary classifies uncentered HD surface rows and AV rows without crashing",
        "battle_ui_summary does not treat route-candidate rows alone as battle-screen reachability",
        "battle_ui_summary CLI writes JSON/Markdown outputs",
    ]
    failures: list[str] = []
    try:
        test_battle_ui_summary.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for parser CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves battle summary classification is marker-driven, centered-offset aware, "
            "AV-aware, and refuses to promote route-candidate rows into battle-screen proof"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.battle_ui_summary_tests_json, result)
    write_battle_ui_summary_tests_markdown(args.battle_ui_summary_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.battle_ui_summary_tests_json),
        "markdown": str(args.battle_ui_summary_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def write_battle_ui_gate_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Battle UI Gate Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_battle_ui_gate_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "battle_ui_gate passes only when centered battle evidence, command hit, grid hit, modal classification, clean patch stage, and stable smoke proof are present",
        "battle_ui_gate fails closed for missing battle reachability, command hit, grid hit, modal classification, visual classification, and AV rows",
        "battle_ui_gate fails closed for candidates outside C:\\ClashTests, wrong stages, base-SHA drift, original/unexpected bytes, and failing stable-smoke evidence",
        "battle_ui_gate CLI writes JSON/Markdown and returns 2 on --require-pass failure",
    ]
    failures: list[str] = []
    try:
        test_battle_ui_gate.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for gate CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the battle UI gate is fail-closed across runtime evidence, patch-stage, "
            "candidate-location, and stable-regression boundaries before any battle patch group exists"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.battle_ui_gate_tests_json, result)
    write_battle_ui_gate_tests_markdown(args.battle_ui_gate_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.battle_ui_gate_tests_json),
        "markdown": str(args.battle_ui_gate_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def battle_visible_input_paths(args: argparse.Namespace) -> list[Path]:
    return list(getattr(args, "battle_visible_input_runs", None) or DEFAULT_BATTLE_VISIBLE_INPUT_RUNS)


def write_refresh_tests_markdown(path: Path, title: str, result: dict[str, Any]) -> None:
    lines = [
        f"# {title}",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_battle_visible_input_summary(args: argparse.Namespace) -> dict[str, Any]:
    paths = battle_visible_input_paths(args)
    summary = battle_visible_input_summary.build_summary(paths)
    write_json(args.battle_visible_input_json, summary)
    args.battle_visible_input_md.parent.mkdir(parents=True, exist_ok=True)
    args.battle_visible_input_md.write_text(
        battle_visible_input_summary.markdown_for(summary, args.battle_visible_input_md),
        encoding="ascii",
    )

    command_ready = int(summary.get("command_ready_run_count") or 0)
    click_consumed = int(summary.get("click_consumed_run_count") or 0)
    invalid = int(summary.get("invalid_run_count") or 0)
    real_click = bool(summary.get("real_visible_click_consumed"))
    summary_passed = bool(summary.get("passed"))
    focused_completion = float(summary.get("focused_completion_percent") or 0.0)

    failures: list[str] = []
    if not paths:
        failures.append("no visible-input evidence paths configured")
    if command_ready < 1:
        failures.append("visible input summary has no command-ready run")
    if summary_passed and not real_click:
        failures.append("visible input summary claims pass without real visible click consumption")
    if real_click and click_consumed < 1:
        failures.append("visible input summary claims real click consumption without a click-consumed run")
    if focused_completion >= 100.0 and not real_click:
        failures.append("visible input summary claims 100% before real visible click consumption")

    return {
        "passed": not failures,
        "json": str(args.battle_visible_input_json),
        "markdown": str(args.battle_visible_input_md),
        "summary": {
            "run_count": summary.get("run_count"),
            "focused_completion_percent": summary.get("focused_completion_percent"),
            "summary_passed": summary_passed,
            "command_ready_run_count": command_ready,
            "click_consumed_run_count": click_consumed,
            "invalid_run_count": invalid,
            "real_visible_click_consumed": real_click,
            "open_blocker": None if real_click else "real visible click-to-callback proof",
        },
        "failures": failures,
    }


def build_battle_visible_input_summary_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "visible input summary keeps command-ready runs partial until a real click reaches the callback",
        "visible input summary requires both visible input JSON and callback/click-gate evidence for click consumption",
        "visible input summary rejects invalid CDB breakpoint and post-g break-instruction failures",
        "visible input summary CLI writes JSON/Markdown current artifacts",
        "visible input summary aggregate pass requires at least one consumed-click run",
    ]
    failures: list[str] = []
    try:
        test_battle_visible_input_summary.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for parser CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves visible-input evidence cannot be promoted from command readiness to pass "
            "until a real visible click is consumed by the battle command callback"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.battle_visible_input_summary_tests_json, result)
    write_refresh_tests_markdown(
        args.battle_visible_input_summary_tests_md,
        "Battle Visible Input Summary Tests",
        result,
    )
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.battle_visible_input_summary_tests_json),
        "markdown": str(args.battle_visible_input_summary_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_battle_ui_evidence_matrix(args: argparse.Namespace) -> dict[str, Any]:
    matrix_args = argparse.Namespace(
        force_entry_json=battle_ui_evidence_matrix.DEFAULT_FORCE_ENTRY_JSON,
        command_hit_json=battle_ui_evidence_matrix.DEFAULT_COMMAND_HIT_JSON,
        command_callback_json=battle_ui_evidence_matrix.DEFAULT_COMMAND_CALLBACK_JSON,
        enabled_callback_json=battle_ui_evidence_matrix.DEFAULT_ENABLED_CALLBACK_JSON,
        grid_hit_json=battle_ui_evidence_matrix.DEFAULT_GRID_HIT_JSON,
        centered_input_json=battle_ui_evidence_matrix.DEFAULT_CENTERED_INPUT_JSON,
        post_ready_redraw_json=battle_ui_evidence_matrix.DEFAULT_POST_READY_REDRAW_JSON,
        modal_classified_json=battle_ui_evidence_matrix.DEFAULT_MODAL_CLASSIFIED_JSON,
        patch_stage_json=battle_ui_evidence_matrix.DEFAULT_PATCH_STAGE_JSON,
        input_patch_stage_json=battle_ui_evidence_matrix.DEFAULT_INPUT_PATCH_STAGE_JSON,
        availability_json=battle_ui_evidence_matrix.DEFAULT_AVAILABILITY_JSON,
        slot_scan_json=battle_ui_evidence_matrix.DEFAULT_SLOT_SCAN_JSON,
        save_inventory_json=battle_ui_evidence_matrix.DEFAULT_SAVE_INVENTORY_JSON,
        constructed_fixture_json=battle_ui_evidence_matrix.DEFAULT_CONSTRUCTED_FIXTURE_JSON,
        constructed_fixture_unit_scan_json=battle_ui_evidence_matrix.DEFAULT_CONSTRUCTED_FIXTURE_UNIT_SCAN_JSON,
        constructed_fixture_command_json=battle_ui_evidence_matrix.DEFAULT_CONSTRUCTED_FIXTURE_COMMAND_JSON,
        stable_smoke_json=battle_ui_evidence_matrix.DEFAULT_STABLE_SMOKE_JSON,
        visible_input_json=args.battle_visible_input_json,
    )
    matrix = battle_ui_evidence_matrix.build_matrix(matrix_args)
    write_json(args.battle_ui_evidence_json, matrix)
    battle_ui_evidence_matrix.write_markdown(args.battle_ui_evidence_md, matrix)
    key = matrix.get("key_evidence", {})
    completion = matrix.get("completion_summary", {})
    return {
        "passed": bool(matrix.get("passed")),
        "json": str(args.battle_ui_evidence_json),
        "markdown": str(args.battle_ui_evidence_md),
        "summary": {
            "focused_completion_percent": completion.get("focused_completion_percent"),
            "visible_input_summary_passed": key.get("visible_input_summary_passed"),
            "visible_input_command_ready_runs": key.get("visible_input_command_ready_runs"),
            "visible_input_click_consumed_runs": key.get("visible_input_click_consumed_runs"),
            "visible_input_invalid_runs": key.get("visible_input_invalid_runs"),
            "real_visible_click_consumed": completion.get("real_visible_click_consumed"),
            "promotion_status": matrix.get("promotion_status"),
            "stable_stage_should_change": matrix.get("stable_stage_should_change"),
            "open_items": matrix.get("open_items", []),
        },
        "failures": matrix.get("failures", []),
    }


def build_battle_ui_evidence_matrix_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "battle UI evidence matrix accepts the current battle/right-bottom command evidence shape",
        "battle UI evidence matrix fails closed for AV or missing reachability in each summary",
        "battle UI evidence matrix rejects feature regressions in command, grid, input, redraw, and modal proof",
        "battle UI evidence matrix rejects constructed-fixture render-begin guard regressions",
        "battle UI evidence matrix rejects missing constructed-fixture synthetic release proof",
        "battle UI evidence matrix rejects constructed-fixture pre-gate rearm regressions",
        "battle UI evidence matrix rejects native-click attempts in the visual-click fixture",
        "battle UI evidence matrix rejects missing visible command readiness",
        "battle UI evidence matrix rejects visible-input pass overclaims without real click consumption",
        "battle UI evidence matrix rejects real-click count mismatches",
        "battle UI evidence matrix CLI writes JSON/Markdown outputs and honors --require-pass",
    ]
    failures: list[str] = []
    try:
        test_battle_ui_evidence_matrix.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for matrix CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the focused battle/right-bottom command lane stays below 100% until "
            "real visible click-to-callback evidence exists"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.battle_ui_evidence_tests_json, result)
    write_refresh_tests_markdown(
        args.battle_ui_evidence_tests_md,
        "Battle UI Evidence Matrix Tests",
        result,
    )
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.battle_ui_evidence_tests_json),
        "markdown": str(args.battle_ui_evidence_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_battle_visible_harness_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard = battle_visible_harness_guard.build_guard(args.battle_visible_harness_script)
    write_json(args.battle_visible_harness_guard_json, guard)
    battle_visible_harness_guard.write_markdown(args.battle_visible_harness_guard_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.battle_visible_harness_guard_json),
        "markdown": str(args.battle_visible_harness_guard_md),
        "summary": {
            "script": guard.get("script"),
            "runtime_policy": guard.get("runtime_policy"),
            "check_count": len(guard.get("checks", [])),
        },
        "failures": guard.get("failures", []),
    }


def build_battle_visible_harness_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "visible battle harness guard accepts a source-safe harness with explicit runtime approval",
        "visible battle harness guard rejects missing fatal CDB breakpoint patterns",
        "visible battle harness guard rejects missing post-g break-instruction gating",
        "visible battle harness guard rejects non-incremental CDB log scans",
        "visible battle harness guard CLI writes outputs and fails closed under --require-pass",
    ]
    failures: list[str] = []
    try:
        test_battle_visible_harness_guard.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for guard CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the visible battle input harness keeps explicit approval, fatal CDB log detection, "
            "post-g gating, and incremental log scanning before any future manual run"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.battle_visible_harness_guard_tests_json, result)
    write_refresh_tests_markdown(
        args.battle_visible_harness_guard_tests_md,
        "Battle Visible Harness Guard Tests",
        result,
    )
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.battle_visible_harness_guard_tests_json),
        "markdown": str(args.battle_visible_harness_guard_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_right_bottom_compose_decision(
    args: argparse.Namespace,
    checks: dict[str, Any],
) -> dict[str, Any]:
    decision_args = argparse.Namespace(
        current_stable_stage=args.current_stable_stage,
        validation_stage=RIGHT_BOTTOM_COMPOSE_PATCH_STAGE,
        manual_input_proof=args.right_bottom_compose_manual_input_proof,
        allow_cdb_only_promotion=args.allow_right_bottom_compose_cdb_only_promotion,
    )
    decision = right_bottom_compose_promotion_decision.build_decision_from_checks(
        decision_args,
        checks,
    )
    write_json(args.right_bottom_compose_decision_json, decision)
    right_bottom_compose_promotion_decision.write_markdown(
        args.right_bottom_compose_decision_md,
        decision,
    )
    return {
        "passed": bool(decision.get("passed")),
        "json": str(args.right_bottom_compose_decision_json),
        "markdown": str(args.right_bottom_compose_decision_md),
        "summary": {
            "decision": decision.get("decision"),
            "stable_stage_should_change": decision.get("stable_stage_should_change"),
            "current_stable_stage": decision.get("current_stable_stage"),
            "validation_stage": decision.get("validation_stage"),
            "candidate_sha256": decision.get("candidate_sha256"),
            "manual_input_proof_valid": decision.get("manual_input_proof_valid"),
        },
        "failures": decision.get("failures", []),
    }


def build_right_bottom_compose_matrix(
    args: argparse.Namespace,
    checks: dict[str, Any],
) -> dict[str, Any]:
    matrix_args = argparse.Namespace(
        current_stable_stage=args.current_stable_stage,
        validation_stage=RIGHT_BOTTOM_COMPOSE_PATCH_STAGE,
    )
    matrix = right_bottom_compose_evidence_matrix.build_matrix_from_checks(matrix_args, checks)
    write_json(args.right_bottom_compose_matrix_json, matrix)
    right_bottom_compose_evidence_matrix.write_markdown(
        args.right_bottom_compose_matrix_md,
        matrix,
    )
    return {
        "passed": bool(matrix.get("passed")),
        "json": str(args.right_bottom_compose_matrix_json),
        "markdown": str(args.right_bottom_compose_matrix_md),
        "summary": {
            "promotion_status": matrix.get("promotion_status"),
            "stable_stage_should_change": matrix.get("stable_stage_should_change"),
            "candidate_sha256": matrix.get("candidate_sha256"),
            "controlled_grid_hit_ok": matrix.get("key_evidence", {}).get("controlled_grid_hit_ok"),
            "promotion_decision": matrix.get("key_evidence", {}).get("promotion_decision"),
        },
        "failures": matrix.get("failures", []),
    }


def write_right_bottom_compose_decision_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Right-Bottom Compose Promotion Decision Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_right_bottom_compose_decision_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "right_bottom_compose_promotion_decision defers stable promotion by default",
        "right_bottom_compose_promotion_decision accepts fixture natural-draw evidence while still deferring promotion",
        "right_bottom_compose_promotion_decision fails closed when the fixture natural-draw payload regresses",
        "right_bottom_compose_promotion_decision fails when any required route/gate/grid/natural-route/timing check is missing or failing",
        "right_bottom_compose_promotion_decision fails when natural route owner-flag, descriptor, action-route, or AV facts regress",
        "right_bottom_compose_promotion_decision allows stable promotion only with a valid manual/real input proof manifest",
        "right_bottom_compose_promotion_decision rejects placeholder manual input proof files",
        "right_bottom_compose_promotion_decision allows CDB-only promotion only with an explicit override",
        "right_bottom_compose_promotion_decision CLI writes JSON/Markdown and returns 2 on --require-pass failure",
    ]
    failures: list[str] = []
    try:
        test_right_bottom_compose_promotion_decision.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for decision CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the right-bottom compose promotion decision defers by default, fails closed "
            "for missing/failing route/grid/timing gates, rejects placeholder proof files, "
            "and only permits promotion with a valid manual proof manifest or an explicit CDB-only override"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.right_bottom_compose_decision_tests_json, result)
    write_right_bottom_compose_decision_tests_markdown(args.right_bottom_compose_decision_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.right_bottom_compose_decision_tests_json),
        "markdown": str(args.right_bottom_compose_decision_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def write_right_bottom_compose_matrix_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Right-Bottom Compose Evidence Matrix Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_right_bottom_compose_matrix_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "right_bottom_compose_evidence_matrix passes when all required route, map, UI, grid-hit, natural-route, timing, and decision checks pass",
        "right_bottom_compose_evidence_matrix fails when any required check is missing or failing",
        "right_bottom_compose_evidence_matrix rejects route, startup, hidden-desktop, AV, visibility, grid-hit, natural-route, timing, and decision regressions",
        "right_bottom_compose_evidence_matrix rejects nested natural-route owner flag, descriptor, and result regressions",
        "right_bottom_compose_evidence_matrix accepts the slot5-as-slot0 fixture natural-draw payload while still deferring promotion",
        "right_bottom_compose_evidence_matrix fails closed when the fixture natural-draw payload is missing or regresses",
        "right_bottom_compose_evidence_matrix rejects candidate SHA disagreement",
        "right_bottom_compose_evidence_matrix CLI writes JSON/Markdown and returns 2 on --require-pass failure",
    ]
    failures: list[str] = []
    try:
        test_right_bottom_compose_evidence_matrix.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for matrix CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the right-bottom compose evidence matrix requires all route gates, "
            "hidden-desktop/full-start safety, normal map/visibility proof, natural UI routing, "
            "controlled grid-hit proof, route timing/order proof, candidate SHA agreement, and deferred promotion status"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.right_bottom_compose_matrix_tests_json, result)
    write_right_bottom_compose_matrix_tests_markdown(args.right_bottom_compose_matrix_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.right_bottom_compose_matrix_tests_json),
        "markdown": str(args.right_bottom_compose_matrix_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_stable_stage_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard_args = argparse.Namespace(
        current_stable_stage=args.current_stable_stage,
        right_bottom_decision=args.right_bottom_compose_decision_json,
        right_bottom_matrix=args.right_bottom_compose_matrix_json,
        castle_decision=args.castle_decision_json,
        castle_matrix=args.castle_matrix_json,
    )
    guard = stable_stage_guard.build_guard(guard_args)
    write_json(args.stable_stage_guard_json, guard)
    stable_stage_guard.write_markdown(args.stable_stage_guard_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.stable_stage_guard_json),
        "markdown": str(args.stable_stage_guard_md),
        "summary": {
            "current_stable_stage": guard.get("current_stable_stage"),
            "patcher_default_stage": guard.get("patcher_default_stage"),
            "validation_only_groups_in_stable": guard.get("validation_only_groups_in_stable"),
            "mapsurface_stages_checked": guard.get("mapsurface_stages_checked"),
            "mapsurface_with_menu_surface": guard.get("mapsurface_with_menu_surface"),
            "mapsurface_missing_upgrade": guard.get("mapsurface_missing_upgrade"),
        },
        "failures": guard.get("failures", []),
    }


def write_stable_stage_guard_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Stable Stage Guard Regression Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_stable_stage_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "stable_stage_guard passes with stable stage and deferred promotion decisions",
        "stable_stage_guard fails when the patcher default drifts from the stable stage",
        "stable_stage_guard fails when a validation-only group leaks into the stable stage",
        "stable_stage_guard fails when castlecenter-all loses an expected validation group",
        "stable_stage_guard fails when a mapsurface stage reintroduces the global menu-surface group",
        "stable_stage_guard fails when a mapsurface stage loses the gameplay-only map surface upgrade",
        "stable_stage_guard fails when a promotion decision would change the stable stage",
        "stable_stage_guard fails when the castle promotion decision lacks focused/multihit proof",
        "stable_stage_guard fails when the castle evidence matrix lacks focused/multihit proof",
        "stable_stage_guard CLI writes JSON/Markdown and returns 2 on --require-pass failure",
    ]
    failures: list[str] = []
    try:
        test_stable_stage_guard.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for guard CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the stable-stage guard rejects patcher-default drift, validation-only "
            "group leakage into the stable stage, missing validation-stage groups, mapsurface "
            "stages that reintroduce global menu-surface allocation or lose the gameplay-only "
            "map surface upgrade, and promotion decisions/evidence matrices that would change "
            "the stable stage or omit required castle focused/multihit proof"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.stable_stage_guard_tests_json, result)
    write_stable_stage_guard_tests_markdown(args.stable_stage_guard_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.stable_stage_guard_tests_json),
        "markdown": str(args.stable_stage_guard_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_exe_artifact_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard_args = argparse.Namespace(gitignore=args.gitignore)
    guard = exe_artifact_guard.build_guard(guard_args)
    write_json(args.exe_artifact_guard_json, guard)
    exe_artifact_guard.write_markdown(args.exe_artifact_guard_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.exe_artifact_guard_json),
        "markdown": str(args.exe_artifact_guard_md),
        "summary": {
            "filesystem_exes": len(guard.get("filesystem_exes") or []),
            "tracked_exes": len(guard.get("tracked_exes") or []),
            "allowed_staged_deletions": len(guard.get("allowed_staged_deletions") or []),
            "root_exe_ignore_present": guard.get("root_exe_ignore_present"),
        },
        "failures": guard.get("failures", []),
    }


def build_no_visible_runtime_guard(
    args: argparse.Namespace,
    checks: dict[str, Any],
) -> dict[str, Any]:
    payloads: list[dict[str, Any]] = [{"runtime_policy": RUNTIME_POLICY, "checks": checks}]
    for path in (args.hd_map_smoke_json, args.castle_matrix_json):
        if path.exists():
            payloads.append(json.loads(path.read_text(encoding="utf-8-sig")))
    guard = no_visible_runtime_guard.build_guard_from_payloads(
        payloads,
        runtime_policy=RUNTIME_POLICY,
    )
    write_json(args.no_visible_runtime_guard_json, guard)
    no_visible_runtime_guard.write_markdown(args.no_visible_runtime_guard_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.no_visible_runtime_guard_json),
        "markdown": str(args.no_visible_runtime_guard_md),
        "summary": {
            "run_count": guard.get("run_count"),
            "hidden_run_count": guard.get("hidden_run_count"),
            "guard_policy": guard.get("guard_policy"),
        },
        "failures": guard.get("failures", []),
    }


def write_no_visible_runtime_guard_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# No-Visible Runtime Guard Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_no_visible_runtime_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "no_visible_runtime_guard passes hidden-desktop surface-dump summaries",
        "no_visible_runtime_guard rejects weak runtime policy text",
        "no_visible_runtime_guard rejects visible runtime regression summaries",
        "no_visible_runtime_guard rejects missing run summaries",
        "no_visible_runtime_guard CLI writes JSON/Markdown and returns 2 on --require-pass failure",
    ]
    failures: list[str] = []
    try:
        test_no_visible_runtime_guard.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for guard CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the no-visible runtime guard requires hidden-desktop launch summaries, "
            "explicit no-visible runtime policy text, present run summaries, and CLI fail-closed behavior"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.no_visible_runtime_guard_tests_json, result)
    write_no_visible_runtime_guard_tests_markdown(args.no_visible_runtime_guard_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.no_visible_runtime_guard_tests_json),
        "markdown": str(args.no_visible_runtime_guard_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_process_hygiene_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard_args = argparse.Namespace(
        exact_name=args.process_guard_exact_name,
        prefix=args.process_guard_prefix,
    )
    guard = process_hygiene_guard.build_guard(guard_args)
    write_json(args.process_hygiene_guard_json, guard)
    process_hygiene_guard.write_markdown(args.process_hygiene_guard_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.process_hygiene_guard_json),
        "markdown": str(args.process_hygiene_guard_md),
        "summary": {
            "matching_process_count": guard.get("matching_process_count"),
            "target_exact_names": guard.get("target_exact_names"),
            "target_prefixes": guard.get("target_prefixes"),
            "guard_policy": guard.get("guard_policy"),
        },
        "failures": guard.get("failures", []),
    }


def write_process_hygiene_guard_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Process Hygiene Guard Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_process_hygiene_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "process_hygiene_guard passes when no target process names are present",
        "process_hygiene_guard fails when exact cdb.exe or clash95* prefix matches are present",
        "process_hygiene_guard fails when the process snapshot API fails",
        "process_hygiene_guard target matching is case-insensitive",
        "process_hygiene_guard CLI writes JSON/Markdown and returns 2 on --require-pass failure",
    ]
    failures: list[str] = []
    try:
        test_process_hygiene_guard.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for guard CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the process hygiene guard rejects leftover cdb.exe/clash95* processes, "
            "snapshot failures, and CLI fail-closed cases"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.process_hygiene_guard_tests_json, result)
    write_process_hygiene_guard_tests_markdown(args.process_hygiene_guard_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.process_hygiene_guard_tests_json),
        "markdown": str(args.process_hygiene_guard_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_surface_dump_policy_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard_args = argparse.Namespace(script=args.surface_dump_policy_script)
    guard = surface_dump_policy_guard.build_guard(guard_args)
    write_json(args.surface_dump_policy_guard_json, guard)
    surface_dump_policy_guard.write_markdown(args.surface_dump_policy_guard_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.surface_dump_policy_guard_json),
        "markdown": str(args.surface_dump_policy_guard_md),
        "summary": {
            "script": guard.get("script"),
            "guard_policy": guard.get("guard_policy"),
        },
        "failures": guard.get("failures", []),
    }


def build_visible_runtime_launcher_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard_args = argparse.Namespace(script=args.visible_runtime_launcher_script, root=Path("."), check_inventory=True)
    guard = visible_runtime_launcher_guard.build_guard(guard_args)
    write_json(args.visible_runtime_launcher_guard_json, guard)
    visible_runtime_launcher_guard.write_markdown(args.visible_runtime_launcher_guard_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.visible_runtime_launcher_guard_json),
        "markdown": str(args.visible_runtime_launcher_guard_md),
        "summary": {
            "script_count": guard.get("script_count"),
            "passing_script_count": guard.get("passing_script_count"),
            "inventory_risky_script_count": guard.get("inventory", {}).get("risky_script_count"),
            "inventory_unclassified_risky_script_count": guard.get("inventory", {}).get(
                "unclassified_risky_script_count"
            ),
            "guard_policy": guard.get("guard_policy"),
        },
        "failures": guard.get("failures", []),
    }


def write_visible_runtime_launcher_guard_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Visible Runtime Launcher Guard Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_visible_runtime_launcher_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "visible_runtime_launcher_guard passes for gated launchers",
        "visible_runtime_launcher_guard passes for gated foreground helpers",
        "visible_runtime_launcher_guard passes for gated screen-capture helpers",
        "visible_runtime_launcher_guard requires -AllowVisibleRuntime forwarding to guarded child helpers",
        "visible_runtime_launcher_guard rejects missing AllowVisibleRuntime switches",
        "visible_runtime_launcher_guard rejects missing explicit-approval text",
        "visible_runtime_launcher_guard rejects guards that appear after risky runtime calls",
        "visible_runtime_launcher_guard rejects unclassified risky root scripts",
        "visible_runtime_launcher_guard allows documented exempt risky root scripts",
        "visible_runtime_launcher_guard CLI writes JSON/Markdown and fails closed under --require-pass",
    ]
    failures: list[str] = []
    try:
        test_visible_runtime_launcher_guard.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for guard CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves legacy visible-runtime launchers/helpers require -AllowVisibleRuntime before "
            "any risky Start-Process, window-focus, cursor, SendInput, PostMessage, or CopyFromScreen call, "
            "requires guarded child helpers to receive the same switch, and proves root risky-call inventory "
            "rejects unclassified scripts while allowing documented exemptions"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.visible_runtime_launcher_guard_tests_json, result)
    write_visible_runtime_launcher_guard_tests_markdown(args.visible_runtime_launcher_guard_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.visible_runtime_launcher_guard_tests_json),
        "markdown": str(args.visible_runtime_launcher_guard_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_no_popup_boundary_guard(
    args: argparse.Namespace,
    checks: dict[str, Any],
) -> dict[str, Any]:
    guard = no_popup_boundary_guard.build_guard_from_checks(checks, args.evidence_index)
    write_json(args.no_popup_boundary_guard_json, guard)
    no_popup_boundary_guard.write_markdown(args.no_popup_boundary_guard_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.no_popup_boundary_guard_json),
        "markdown": str(args.no_popup_boundary_guard_md),
        "summary": {
            "required_guard_count": guard.get("required_guard_count"),
            "required_supporting_report_count": guard.get("required_supporting_report_count"),
            "required_report_count": guard.get("required_report_count"),
            "required_guards": guard.get("required_guards"),
            "required_supporting_reports": guard.get("required_supporting_reports"),
            "required_reports": guard.get("required_reports"),
            "evidence_index": guard.get("evidence_index"),
            "guard_policy": guard.get("guard_policy"),
        },
        "failures": guard.get("failures", []),
    }


def write_no_popup_guard_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# No-Popup Guard Regression Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_no_popup_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "no_popup_boundary_guard passes with all boundary reports linked",
        "no_popup_boundary_guard fails when each evidence-index report link is missing",
        "no_popup_boundary_guard fails when a required refresh check is missing",
        "no_popup_boundary_guard fails when each required supporting refresh check is missing",
        "no_popup_boundary_guard fails when a required refresh check is failing",
        "surface_dump_policy_guard passes the expected hidden-desktop launcher shape",
        "surface_dump_policy_guard fails when visible fallback is not explicitly gated",
        "surface_dump_policy_guard failing CLI writes fixture outputs instead of current report paths",
    ]
    failures: list[str] = []
    try:
        test_no_popup_guards.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for guard CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the no-popup boundary guard and surface-dump launcher policy guard reject "
            "missing evidence links, missing/failing refresh checks, missing supporting reports, "
            "and ungated visible fallback while keeping negative CLI outputs out of current reports"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.no_popup_guard_tests_json, result)
    write_no_popup_guard_tests_markdown(args.no_popup_guard_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.no_popup_guard_tests_json),
        "markdown": str(args.no_popup_guard_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_handoff_freshness_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard_args = argparse.Namespace(
        next_md=args.handoff_next_md,
        state_md=args.handoff_state_md,
        tasks_md=args.handoff_tasks_md,
        evidence_index=args.evidence_index,
        progress_md=args.handoff_progress_md,
        bottom_question_md=args.handoff_bottom_question_md,
    )
    guard = handoff_freshness_guard.build_guard(guard_args)
    write_json(args.handoff_freshness_guard_json, guard)
    handoff_freshness_guard.write_markdown(args.handoff_freshness_guard_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.handoff_freshness_guard_json),
        "markdown": str(args.handoff_freshness_guard_md),
        "summary": {
            "guard_policy": guard.get("guard_policy"),
            "phrase_groups": {
                name: result.get("passed")
                for name, result in (guard.get("phrase_groups") or {}).items()
            },
            "loop_phrase_groups": {
                name: result.get("passed")
                for name, result in (guard.get("loop_phrase_groups") or {}).items()
            },
        },
        "failures": guard.get("failures", []),
    }


def write_handoff_freshness_guard_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Handoff Freshness Guard Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_handoff_freshness_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "handoff_freshness_guard passes with current route timing and promotion-blocker wording",
        "handoff_freshness_guard fails when stale broader route/input safety wording returns",
        "handoff_freshness_guard fails when stale legacy outside-debugger or visible-capture tasks return",
        "handoff_freshness_guard fails when stale VM/visual-smoke task wording returns",
        "handoff_freshness_guard fails when route timing guard links are missing",
        "handoff_freshness_guard fails when owner-flag inventory artifacts are missing",
        "handoff_freshness_guard fails when load-slot route-limit artifacts are missing",
        "handoff_freshness_guard fails when load-slot transition readiness artifacts are missing",
        "handoff_freshness_guard fails when loop handoff misses load-slot transition readiness artifacts",
        "handoff_freshness_guard fails when manual proof or explicit CDB-only override wording is missing",
        "handoff_freshness_guard fails when the manual DirectInput checklist artifact is missing",
        "handoff_freshness_guard fails when the manual DirectInput proof template artifact is missing",
        "handoff_freshness_guard fails when the current completion summary artifact is missing",
        "handoff_freshness_guard fails when the no-popup operator preference is missing",
        "handoff_freshness_guard fails when the visible runtime launcher guard artifact is missing",
        "handoff_freshness_guard CLI writes JSON/Markdown and returns 2 on --require-pass failure",
    ]
    failures: list[str] = []
    try:
        test_handoff_freshness_guard.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for guard CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the handoff freshness guard rejects stale route/input blockers, missing route "
            "timing links, stale legacy outside-debugger or visible-capture tasks, "
            "stale VM/visual-smoke tasks, "
            "missing owner-flag inventory artifacts, "
            "missing load-slot transition readiness artifacts, "
            "missing loop-handoff load-slot transition readiness artifacts, "
            "missing manual-proof or explicit CDB-only promotion blockers, "
            "missing manual DirectInput checklist artifacts, missing manual proof template artifacts, "
            "missing completion summary artifacts, missing no-popup operator preference text, "
            "and missing visible runtime launcher guard artifacts"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.handoff_freshness_guard_tests_json, result)
    write_handoff_freshness_guard_tests_markdown(args.handoff_freshness_guard_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.handoff_freshness_guard_tests_json),
        "markdown": str(args.handoff_freshness_guard_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_manual_directinput_checklist(args: argparse.Namespace) -> dict[str, Any]:
    checklist_args = argparse.Namespace(
        manual_proof=args.manual_directinput_proof,
        allow_cdb_only_promotion=args.allow_manual_directinput_cdb_only_promotion,
    )
    checklist = manual_directinput_checklist.build_checklist(checklist_args)
    write_json(args.manual_directinput_checklist_json, checklist)
    manual_directinput_checklist.write_markdown(args.manual_directinput_checklist_md, checklist)
    summary = checklist.get("summary") or {}
    return {
        "passed": bool(checklist.get("passed")),
        "json": str(args.manual_directinput_checklist_json),
        "markdown": str(args.manual_directinput_checklist_md),
        "summary": {
            "status": checklist.get("status"),
            "item_count": summary.get("item_count"),
            "pending_count": summary.get("pending_count"),
            "promotion_ready": summary.get("promotion_ready"),
            "stable_stage_should_change": summary.get("stable_stage_should_change"),
            "visible_runtime_requires_approval": checklist.get("visible_runtime_requires_approval"),
            "manual_proof_valid": checklist.get("manual_proof_valid"),
        },
        "failures": checklist.get("failures", []),
    }


def write_manual_directinput_checklist_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Manual DirectInput Checklist Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_manual_directinput_checklist_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "manual_directinput_checklist passes structurally while keeping promotion blocked",
        "manual_directinput_checklist records the no-popup operator preference",
        "manual_directinput_checklist fails when a required manual target is missing",
        "manual_directinput_checklist fails when a required checklist field is missing",
        "manual_directinput_checklist marks promotion ready only when a valid proof manifest is supplied",
        "manual_directinput_checklist rejects placeholder manual proof files",
        "manual_directinput_checklist rejects proof manifests missing observation, no-crash, or process hygiene records",
        "manual_directinput_checklist rejects live-original or repository-local candidate paths",
        "manual_directinput_checklist marks promotion ready when an explicit CDB-only override is supplied",
        "manual_directinput_checklist CLI writes JSON/Markdown and fails --require-promotion-ready without proof",
    ]
    failures: list[str] = []
    try:
        test_manual_directinput_checklist.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for checklist CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the manual DirectInput checklist enumerates the remaining manual targets, "
            "keeps promotion blocked without valid proof, validates manual proof manifests "
            "including isolated C:\\ClashTests candidate path, stage, observation, no-crash, and process-hygiene records, "
            "records the no-popup operator preference, and fails closed for incomplete checklist data"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.manual_directinput_checklist_tests_json, result)
    write_manual_directinput_checklist_tests_markdown(args.manual_directinput_checklist_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.manual_directinput_checklist_tests_json),
        "markdown": str(args.manual_directinput_checklist_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_manual_directinput_proof_template(args: argparse.Namespace) -> dict[str, Any]:
    template = manual_directinput_proof_template.build_template()
    args.manual_directinput_proof_template_json.parent.mkdir(parents=True, exist_ok=True)
    args.manual_directinput_proof_template_json.write_text(
        json.dumps(template, indent=2) + "\n",
        encoding="utf-8",
    )
    report = manual_directinput_proof_template.build_report(
        args.manual_directinput_proof_template_json,
        template,
    )
    write_json(args.manual_directinput_proof_template_report_json, report)
    manual_directinput_proof_template.write_markdown(
        args.manual_directinput_proof_template_md,
        report,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.manual_directinput_proof_template_report_json),
        "markdown": str(args.manual_directinput_proof_template_md),
        "summary": {
            "template_json": str(args.manual_directinput_proof_template_json),
            "template_valid_as_proof": report.get("template_valid_as_proof"),
            "required_id_count": len(report.get("required_ids") or []),
            "template_failure_count": len(report.get("template_validation_failures") or []),
            "guard_policy": report.get("guard_policy"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def write_manual_directinput_proof_template_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Manual DirectInput Proof Template Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_manual_directinput_proof_template_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "manual_directinput_proof_template remains invalid as proof until placeholders are replaced",
        "manual_directinput_proof_template pins candidate placeholders under C:\\ClashTests",
        "manual_directinput_proof_template reports every required manual target id",
        "manual_directinput_proof_template can become valid after all proof fields are replaced",
        "manual_directinput_proof_template CLI writes template JSON, report JSON, and Markdown",
    ]
    failures: list[str] = []
    try:
        test_manual_directinput_proof_template.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for template CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the manual DirectInput proof template documents the proof shape, "
            "pins candidate placeholders under C:\\ClashTests, stays invalid until "
            "placeholders are replaced, and can become valid only after all required "
            "manual proof fields are supplied"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.manual_directinput_proof_template_tests_json, result)
    write_manual_directinput_proof_template_tests_markdown(
        args.manual_directinput_proof_template_tests_md,
        result,
    )
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.manual_directinput_proof_template_tests_json),
        "markdown": str(args.manual_directinput_proof_template_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_manual_directinput_run_plan(args: argparse.Namespace) -> dict[str, Any]:
    report = manual_directinput_run_plan.build_plan(
        checklist_json=args.manual_directinput_checklist_json,
        template_report_json=args.manual_directinput_proof_template_report_json,
    )
    write_json(args.manual_directinput_run_plan_json, report)
    manual_directinput_run_plan.write_markdown(args.manual_directinput_run_plan_md, report)
    summary = report.get("summary") or {}
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.manual_directinput_run_plan_json),
        "markdown": str(args.manual_directinput_run_plan_md),
        "summary": {
            "manual_target_count": report.get("manual_target_count"),
            "command_count": summary.get("command_count"),
            "all_commands_have_allow_visible_runtime": summary.get(
                "all_commands_have_allow_visible_runtime"
            ),
            "visible_runtime_requires_approval": report.get("visible_runtime_requires_approval"),
            "proof_ready": report.get("proof_ready"),
            "promotion_ready": summary.get("promotion_ready"),
            "guard_policy": report.get("guard_policy"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_manual_directinput_run_plan_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_manual_directinput_run_plan,
        tests=[
            "manual_directinput_run_plan passes but does not claim proof or promotion readiness",
            "manual_directinput_run_plan emits one approval-gated command per required manual target",
            "manual_directinput_run_plan fails when a required checklist item is missing",
            "manual_directinput_run_plan fails when a visible command source lacks AllowVisibleRuntime",
            "manual_directinput_run_plan fails when a candidate placeholder is not under C:\\ClashTests",
            "manual_directinput_run_plan CLI writes JSON and Markdown outputs",
        ],
        title="Manual DirectInput Run Plan Tests",
        json_path=args.manual_directinput_run_plan_tests_json,
        md_path=args.manual_directinput_run_plan_tests_md,
        guard_policy=(
            "proves the manual DirectInput run plan remains repo-only, "
            "keeps visible commands approval-gated with -AllowVisibleRuntime, "
            "keeps candidate placeholders under C:\\ClashTests, "
            "and cannot substitute for a valid manual proof manifest"
        ),
    )


def build_promotion_override_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard_args = argparse.Namespace(
        right_bottom_decision=args.right_bottom_compose_decision_json,
        castle_decision=args.castle_decision_json,
        manual_checklist=args.manual_directinput_checklist_json,
    )
    guard = promotion_override_guard.build_guard(guard_args)
    write_json(args.promotion_override_guard_json, guard)
    promotion_override_guard.write_markdown(args.promotion_override_guard_md, guard)
    checks = guard.get("checks") or {}
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.promotion_override_guard_json),
        "markdown": str(args.promotion_override_guard_md),
        "summary": {
            "right_bottom_override": (
                checks.get("right_bottom_compose_promotion_decision", {})
                .get("summary", {})
                .get("allow_cdb_only_promotion")
            ),
            "castle_override": (
                checks.get("castle_overview_promotion_decision", {})
                .get("summary", {})
                .get("allow_cdb_only_promotion")
            ),
            "manual_checklist_override": (
                checks.get("manual_directinput_checklist", {})
                .get("summary", {})
                .get("allow_cdb_only_promotion")
            ),
            "manual_checklist_promotion_ready": (
                checks.get("manual_directinput_checklist", {})
                .get("summary", {})
                .get("promotion_ready")
            ),
            "guard_policy": guard.get("guard_policy"),
            "runtime_policy": guard.get("runtime_policy"),
        },
        "failures": guard.get("failures", []),
    }


def write_promotion_override_guard_tests_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Promotion Override Guard Tests",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    for test in result["tests"]:
        lines.append(f"- `{test}`")
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_promotion_override_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    tests = [
        "promotion_override_guard passes when current override/proof flags are inactive",
        "promotion_override_guard rejects a right-bottom CDB-only override",
        "promotion_override_guard rejects a castle overview CDB-only override",
        "promotion_override_guard rejects a promotion-ready manual checklist override",
        "promotion_override_guard rejects manual proof in current no-popup evidence",
        "promotion_override_guard rejects missing promotion/checklist JSON",
        "promotion_override_guard CLI writes JSON/Markdown and returns 2 on --require-pass failure",
    ]
    failures: list[str] = []
    try:
        test_promotion_override_guard.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for guard CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": (
            "proves the current evidence fails closed if CDB-only promotion overrides, "
            "manual proof, or promotion-ready states become active unexpectedly"
        ),
        "tests": tests,
        "failures": failures,
    }
    write_json(args.promotion_override_guard_tests_json, result)
    write_promotion_override_guard_tests_markdown(args.promotion_override_guard_tests_md, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(args.promotion_override_guard_tests_json),
        "markdown": str(args.promotion_override_guard_tests_md),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def write_simple_tests_markdown(path: Path, title: str, result: dict[str, Any]) -> None:
    lines = [
        f"# {title}",
        "",
        f"- Status: {status_text(bool(result.get('passed')))}",
        f"- Generated: `{result['generated_at']}`",
        f"- Runtime policy: {result['runtime_policy']}",
        f"- Guard policy: {result['guard_policy']}",
        "",
        "## Tests",
        "",
    ]
    lines.extend(f"- `{test}`" for test in result["tests"])
    if result.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result["failures"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def simple_test_check(
    *,
    test_runner: Any,
    tests: list[str],
    title: str,
    json_path: Path,
    md_path: Path,
    guard_policy: str,
) -> dict[str, Any]:
    failures: list[str] = []
    try:
        test_runner.run_tests()
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")
    result = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": (
            "repo-only fixture tests; launches only Python child processes for CLI coverage; "
            "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
        ),
        "guard_policy": guard_policy,
        "tests": tests,
        "failures": failures,
    }
    write_json(json_path, result)
    write_simple_tests_markdown(md_path, title, result)
    return {
        "passed": bool(result.get("passed")),
        "json": str(json_path),
        "markdown": str(md_path),
        "summary": {
            "test_count": len(tests),
            "guard_policy": result.get("guard_policy"),
            "runtime_policy": result.get("runtime_policy"),
        },
        "failures": failures,
    }


def build_python_runtime_safety_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard_args = argparse.Namespace(root=Path("."), tools_dir=Path("tools"))
    guard = python_runtime_safety_guard.build_guard(guard_args)
    write_json(args.python_runtime_safety_json, guard)
    python_runtime_safety_guard.write_markdown(args.python_runtime_safety_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.python_runtime_safety_json),
        "markdown": str(args.python_runtime_safety_md),
        "summary": {
            "risky_file_count": guard.get("risky_file_count"),
            "classification_counts": guard.get("classification_counts"),
            "guard_policy": guard.get("guard_policy"),
            "runtime_policy": guard.get("runtime_policy"),
        },
        "failures": guard.get("failures", []),
    }


def build_python_runtime_safety_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_python_runtime_safety_guard,
        tests=[
            "python_runtime_safety_guard rejects unclassified risky helpers",
            "python_runtime_safety_guard allows gated/exempt helpers and test fixtures",
            "python_runtime_safety_guard CLI writes outputs and fails closed under --require-pass",
        ],
        title="Python Runtime Safety Guard Tests",
        json_path=args.python_runtime_safety_tests_json,
        md_path=args.python_runtime_safety_tests_md,
        guard_policy="proves risky Python runtime/window/input helpers are gated, exempt, or fail closed",
    )


def build_patch_resolution_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_patch_resolution,
        tests=[
            "frozen legacy table SHA pin and dispatch identity hold",
            "generator reproduces the legacy table byte-for-byte at 800x600",
            "preset profile math, tile formulas, and parse validation hold",
            "menu-hitbox and descriptor shifts derive from the centering offsets",
            "recipe coverage census and old-bytes invariance hold",
            "cave templates verify slots, branch targets, and relocation shape",
            "preset generation stays overlap-free across parameterized stages",
            "signed imm8 tile slots fail closed beyond the 127-tile ceiling",
            "coincident 800x600 formulas require acknowledged justification",
            "patch-stage report gate parameterizes tiles and keeps legacy keys",
            "archived 800x600 reports still pass the smoke-matrix gate",
            "synthetic candidates pass their own resolution gate and fail others",
        ],
        title="Patch Resolution Tests",
        json_path=args.patch_resolution_tests_json,
        md_path=args.patch_resolution_tests_md,
        guard_policy=(
            "proves multi-resolution generation cannot drift from the frozen "
            "800x600 byte-for-byte contract"
        ),
    )


def build_launcher_policy_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard_args = argparse.Namespace(
        launcher_dir=Path("src/launcher"),
        scripts_dir=Path("scripts/launcher"),
        refresh_script=Path("tools/current_evidence_refresh.py"),
        doc=Path("docs/hd/LAUNCHER.md"),
    )
    guard = launcher_policy_guard.build_guard(guard_args)
    write_json(args.launcher_policy_guard_json, guard)
    launcher_policy_guard.write_markdown(args.launcher_policy_guard_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.launcher_policy_guard_json),
        "markdown": str(args.launcher_policy_guard_md),
        "summary": {
            "launcher_dir": guard.get("launcher_dir"),
            "guard_policy": guard.get("guard_policy"),
            "runtime_policy": guard.get("runtime_policy"),
        },
        "failures": guard.get("failures", []),
    }


def build_launcher_policy_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_launcher_policy_guard,
        tests=[
            "launcher_policy_guard passes on a compliant launcher tree",
            "launcher_policy_guard fails on a missing confirmed=True gate",
            "launcher_policy_guard fails on missing candidates-root write refusals",
            "launcher_policy_guard fails on launch call sites outside core/gui/entry",
            "launcher_policy_guard fails when the refresh references the launcher",
            "launcher_policy_guard fails on risky launcher PowerShell calls",
            "launcher_policy_guard fails on missing policy doc phrases",
            "launcher_policy_guard CLI writes outputs and fails closed under --require-pass",
        ],
        title="Launcher Policy Guard Tests",
        json_path=args.launcher_policy_guard_tests_json,
        md_path=args.launcher_policy_guard_tests_md,
        guard_policy="proves the launcher policy guard fails closed on every policy regression",
    )


def build_launcher_core_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_launcher_core,
        tests=[
            "launcher core refuses repo/game-dir candidate roots and unknown stages",
            "launcher core builds, byte-gates, reuses, and rebuilds candidates",
            "launcher core refuses base executables with unexpected SHA-256",
            "launcher core launch gate requires confirmed=True and a deployed wrapper",
            "launcher core reports missing wrapper DLLs without failing deploy",
            "launcher environment report classifies base/wrapper/process state",
            "launcher settings round-trip and recover from corrupt files",
            "launcher single-instance lock handles live and stale owners",
            "launcher dxcfg rendering rejects unverified scaling modes",
            "launcher candidate cleanup stays inside the candidates root",
        ],
        title="Launcher Core Tests",
        json_path=args.launcher_core_tests_json,
        md_path=args.launcher_core_tests_md,
        guard_policy="proves the launcher patch/deploy/launch core enforces its safety refusals",
    )


def build_resolution_manifest_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard_args = argparse.Namespace(
        root=Path("."),
        manifest=Path("src/launcher/resolutions.json"),
        expected_default="800x600",
        expected_stable_stage=None,
    )
    guard = resolution_manifest_guard.build_guard(guard_args)
    write_json(args.resolution_manifest_guard_json, guard)
    resolution_manifest_guard.write_markdown(args.resolution_manifest_guard_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.resolution_manifest_guard_json),
        "markdown": str(args.resolution_manifest_guard_md),
        "summary": {
            "resolution_count": guard.get("resolution_count"),
            "status_counts": guard.get("status_counts"),
            "guard_policy": guard.get("guard_policy"),
            "runtime_policy": guard.get("runtime_policy"),
        },
        "failures": guard.get("failures", []),
    }


def build_resolution_manifest_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_resolution_manifest_guard,
        tests=[
            "resolution_manifest_guard passes on a consistent manifest",
            "resolution_manifest_guard fails on missing/duplicate stable defaults",
            "resolution_manifest_guard fails on stable-stage or tile-formula drift",
            "resolution_manifest_guard fails on missing or visible evidence runs",
            "resolution_manifest_guard fails on failing smoke matrices and bad bounds",
            "resolution_manifest_guard CLI writes outputs and fails closed under --require-pass",
        ],
        title="Resolution Manifest Guard Tests",
        json_path=args.resolution_manifest_guard_tests_json,
        md_path=args.resolution_manifest_guard_tests_md,
        guard_policy="proves the resolution status manifest guard fails closed on drift",
    )


def build_patch_definition_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard_args = argparse.Namespace()
    guard = patch_definition_guard.build_guard(guard_args)
    write_json(args.patch_definition_json, guard)
    patch_definition_guard.write_markdown(args.patch_definition_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.patch_definition_json),
        "markdown": str(args.patch_definition_md),
        "summary": {
            "patcher_default_stage": guard.get("patcher_default_stage"),
            "patch_count": guard.get("patch_count"),
            "patch_group_count": guard.get("patch_group_count"),
            "stage_count": guard.get("stage_count"),
            "validation_groups_in_stable": guard.get("validation_groups_in_stable"),
            "overlap_failure_count": guard.get("overlap_failure_count"),
            "guard_policy": guard.get("guard_policy"),
            "runtime_policy": guard.get("runtime_policy"),
        },
        "failures": guard.get("failures", []),
    }


def build_patch_definition_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_patch_definition_guard,
        tests=[
            "patch_definition_guard passes a scoped fixture",
            "patch_definition_guard fails on default drift",
            "patch_definition_guard fails on validation leakage",
            "patch_definition_guard fails on unknown groups",
            "patch_definition_guard fails on overlapping incompatible bytes",
            "patch_definition_guard CLI writes current outputs",
        ],
        title="Patch Definition Guard Tests",
        json_path=args.patch_definition_tests_json,
        md_path=args.patch_definition_tests_md,
        guard_policy="proves patch/stage definitions fail closed on drift, leakage, unknown groups, or incompatible offset overlaps",
    )


def build_capture_corpus_index(args: argparse.Namespace) -> dict[str, Any]:
    index_args = argparse.Namespace(
        root=Path("."),
        captures_root=args.captures_root,
        current_source=list(capture_corpus_index.CURRENT_REFERENCE_SOURCES),
        archived_source=list(capture_corpus_index.ARCHIVED_REFERENCE_SOURCES),
    )
    index = capture_corpus_index.build_index(index_args)
    write_json(args.capture_corpus_index_json, index)
    capture_corpus_index.write_markdown(args.capture_corpus_index_md, index)
    return {
        "passed": bool(index.get("passed")),
        "json": str(args.capture_corpus_index_json),
        "markdown": str(args.capture_corpus_index_md),
        "summary": {
            "artifact_count": index.get("artifact_count"),
            "current_reference_count": index.get("current_reference_count"),
            "stale_visible_or_sandbox_count": index.get("stale_visible_or_sandbox_count"),
            "reference_status_counts": index.get("reference_status_counts"),
            "era_counts": index.get("era_counts"),
            "guard_policy": index.get("guard_policy"),
            "runtime_policy": index.get("runtime_policy"),
        },
        "failures": index.get("failures", []),
    }


def build_capture_corpus_index_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_capture_corpus_index,
        tests=[
            "capture_corpus_index passes current hidden CDB references",
            "capture_corpus_index fails missing current references",
            "capture_corpus_index ignores fixture-run placeholder references",
            "capture_corpus_index ignores transition-run placeholder references",
            "capture_corpus_index ignores external C:\\ClashCaptures evidence paths",
            "capture_corpus_index reports stale visible artifacts without failing",
            "capture_corpus_index fails current visible/sandbox references",
            "capture_corpus_index fails current visible-fallback CDB references",
            "capture_corpus_index CLI writes outputs and fails closed",
        ],
        title="Capture Corpus Index Tests",
        json_path=args.capture_corpus_index_tests_json,
        md_path=args.capture_corpus_index_tests_md,
        guard_policy="proves capture references resolve, synthetic fixture/transition placeholders stay non-current, and stale visible-era artifacts cannot become active evidence silently",
    )


def build_hd_soak_harness_guard(args: argparse.Namespace) -> dict[str, Any]:
    guard = hd_soak_harness_guard.build_guard(args.hd_soak_harness_script)
    write_json(args.hd_soak_harness_guard_json, guard)
    hd_soak_harness_guard.write_markdown(args.hd_soak_harness_guard_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.hd_soak_harness_guard_json),
        "markdown": str(args.hd_soak_harness_guard_md),
        "summary": {
            "script": guard.get("script"),
            "guard_policy": guard.get("guard_policy"),
            "runtime_policy": guard.get("runtime_policy"),
        },
        "failures": guard.get("failures", []),
    }


def build_hd_soak_harness_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_soak_harness_guard,
        tests=[
            "hd_soak_harness_guard passes the current opt-in soak harness",
            "hd_soak_harness_guard rejects protected stage drift",
            "hd_soak_harness_guard rejects repository candidate defaults",
            "hd_soak_harness_guard rejects missing explicit approval text",
            "hd_soak_harness_guard rejects dry-run execute commands without -RequirePass semantics",
            "hd_soak_harness_guard rejects dry-run execute commands without JSON output",
            "hd_soak_harness_guard rejects missing visible-runtime approval token or expiry boundaries",
            "hd_soak_harness_guard rejects missing visible-runtime approval minimum TTL boundary",
            "hd_soak_harness_guard rejects runtime side effects before approval guards",
            "hd_soak_harness_guard rejects missing required report metrics",
            "hd_soak_harness_guard rejects missing sample-interval, render-range, or raw inventory metrics",
            "hd_soak_harness_guard CLI writes JSON/Markdown and fails closed",
        ],
        title="HD Soak Harness Guard Tests",
        json_path=args.hd_soak_harness_guard_tests_json,
        md_path=args.hd_soak_harness_guard_tests_md,
        guard_policy=(
            "proves the opt-in soak harness stays protected-stage, approval-gated, "
            "non-promoting, artifact-safe, and preserves full render-range plus "
            "sample-interval, route/process/frame/capture inventory metrics"
        ),
    )


def build_hd_soak_execution_boundary(args: argparse.Namespace) -> dict[str, Any]:
    boundary_args = argparse.Namespace(
        script=args.hd_soak_harness_script,
        fixture_root=args.hd_soak_execution_boundary_fixture_root,
        clean_fixture=True,
    )
    report = hd_soak_execution_boundary.build_report(boundary_args)
    hd_soak_execution_boundary.write_outputs(
        report,
        args.hd_soak_execution_boundary_json,
        args.hd_soak_execution_boundary_md,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.hd_soak_execution_boundary_json),
        "markdown": str(args.hd_soak_execution_boundary_md),
        "summary": {
            "case_count": report.get("case_count"),
            "runtime_policy": report.get("runtime_policy"),
            "guard_policy": report.get("guard_policy"),
            "cases": [
                {
                    "name": case.get("name"),
                    "passed": case.get("passed"),
                    "exit_code": case.get("exit_code"),
                    "expected_phrase_seen": case.get("expected_phrase_seen"),
                    "side_effects": case.get("side_effects"),
                }
                for case in (report.get("cases") or [])
            ],
        },
        "failures": report.get("failures", []),
    }


def build_hd_soak_execution_boundary_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_soak_execution_boundary,
        tests=[
            "hd_soak_execution_boundary accepts fake bad-approval failures before side effects",
            "hd_soak_execution_boundary rejects fake side effects before failure",
            "hd_soak_execution_boundary renders Markdown case rows",
            "hd_soak_execution_boundary writes JSON/Markdown reports",
        ],
        title="HD Soak Execution Boundary Tests",
        json_path=args.hd_soak_execution_boundary_tests_json,
        md_path=args.hd_soak_execution_boundary_tests_md,
        guard_policy=(
            "proves the negative execution-boundary reporter fails closed when "
            "bad visible-runtime approval packets would create candidate/output/report side effects"
        ),
    )


def selected_hd_soak_report_path(args: argparse.Namespace) -> tuple[Path, str]:
    canonical_first_step = getattr(args, "hd_soak_first_step_report", DEFAULT_HD_SOAK_FIRST_STEP_REPORT)
    if canonical_first_step.exists():
        return canonical_first_step, "canonical_first_short_step"
    return args.hd_soak_report, "legacy_compatibility"


def hd_soak_report_selection_metadata(args: argparse.Namespace, report_path: Path, report_source: str) -> dict[str, Any]:
    canonical_first_step = getattr(args, "hd_soak_first_step_report", DEFAULT_HD_SOAK_FIRST_STEP_REPORT)
    legacy_report = args.hd_soak_report
    canonical_present = canonical_first_step.exists()
    legacy_present = legacy_report.exists()
    return {
        "source_report_selection": report_source,
        "source_report": str(report_path),
        "canonical_first_step_report": str(canonical_first_step),
        "canonical_first_step_present": canonical_present,
        "legacy_report": str(legacy_report),
        "legacy_report_present": legacy_present,
        "canonical_runtime_report_missing": report_source == "legacy_compatibility" and not canonical_present,
    }


def build_hd_soak_report_guard(args: argparse.Namespace) -> dict[str, Any]:
    report_path, report_source = selected_hd_soak_report_path(args)
    selection = hd_soak_report_selection_metadata(args, report_path, report_source)
    if report_path.exists():
        evaluation = hd_soak_report.evaluate_report(hd_soak_report.load_json(report_path))
        evaluation["source_report"] = str(report_path)
        evaluation["source_report_selection"] = report_source
    else:
        evaluation = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "runtime_policy": hd_soak_report.RUNTIME_POLICY,
            "overall": False,
            "source_report": str(report_path),
            "source_report_selection": report_source,
            "stage": None,
            "tier": None,
            "route": None,
            "duration_sec": None,
            "checks": {},
            "failures": [f"soak report does not exist: {report_path}"],
        }
    evaluation.update(selection)
    write_json(args.hd_soak_report_guard_json, evaluation)
    args.hd_soak_report_guard_md.parent.mkdir(parents=True, exist_ok=True)
    args.hd_soak_report_guard_md.write_text(hd_soak_report.to_markdown(evaluation), encoding="ascii")
    checks = evaluation.get("checks") or {}
    return {
        "passed": bool(evaluation.get("overall")),
        "json": str(args.hd_soak_report_guard_json),
        "markdown": str(args.hd_soak_report_guard_md),
        "summary": {
            "source_report": str(report_path),
            "source_report_selection": report_source,
            "canonical_first_step_report": selection["canonical_first_step_report"],
            "canonical_first_step_present": selection["canonical_first_step_present"],
            "legacy_report": selection["legacy_report"],
            "legacy_report_present": selection["legacy_report_present"],
            "canonical_runtime_report_missing": selection["canonical_runtime_report_missing"],
            "stage": evaluation.get("stage"),
            "tier": evaluation.get("tier"),
            "route": evaluation.get("route"),
            "duration_sec": evaluation.get("duration_sec"),
            "executed": (checks.get("executed") or {}).get("summary", {}).get("executed"),
            "right_bottom_promotion_blocked": (
                (checks.get("promotion_boundary") or {}).get("summary", {}).get("right_bottom_promotion_blocked")
            ),
            "runtime_policy": evaluation.get("runtime_policy"),
        },
        "failures": evaluation.get("failures", []),
    }


def build_hd_soak_report_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_soak_report,
        tests=[
            "hd_soak_report accepts only executed protected-stage reports with passing patch evidence",
            "hd_soak_report rejects executed reports whose source status is failed or carries failures",
            "hd_soak_report rejects unexpected process exits",
            "hd_soak_report rejects raw process samples that already exited",
            "hd_soak_report rejects missing sample intervals or insufficient elapsed sample coverage",
            "hd_soak_report rejects repository-local candidates and raw artifacts",
            "hd_soak_report rejects noncanonical input, workdir, candidate, and output roots",
            "hd_soak_report rejects capture errors, invalid frame hashes, and bad probe exit codes",
            "hd_soak_report rejects invalid tier, route, or duration combinations",
            "hd_soak_report rejects weak render/palette metrics",
            "hd_soak_report allows stable idle frames but requires progression for map-pan",
            "hd_soak_report rejects missing or excessive process growth metrics",
            "hd_soak_report rejects missing, mismatched, or excessive artifact budget metrics",
            "hd_soak_report rejects missing or excessive route input drift metrics",
            "hd_soak_report rejects final route markers that do not match the last route/input row",
            "hd_soak_report rejects empty route evidence and summary/detail metric mismatches",
            "hd_soak_report rejects patch-stage manifests with original/unexpected bytes or failed HD gate",
            "hd_soak_report rejects missing patch-stage manifests",
            "hd_soak_report classifies pending approval without runtime metric noise",
        ],
        title="HD Soak Report Guard Tests",
        json_path=args.hd_soak_report_guard_tests_json,
        md_path=args.hd_soak_report_guard_tests_md,
        guard_policy=(
            "proves executed soak reports must carry protected-stage patch evidence, base/candidate SHA-256s, "
            "a passing source status, external artifact locations, stable/progressing frame metrics, clean process stop, "
            "elapsed frame/process sample coverage, valid route/input probe rows, and non-promoting input status with bounded working-set, private-memory, "
            "handle growth, artifact budget, valid capture/frame inventories, and consistent raw/sample summary metrics"
        ),
    )


def build_hd_soak_failure_triage(args: argparse.Namespace) -> dict[str, Any]:
    report_path, report_source = selected_hd_soak_report_path(args)
    selection = hd_soak_report_selection_metadata(args, report_path, report_source)
    if report_path.exists():
        triage = hd_soak_failure_triage.build_triage(
            hd_soak_failure_triage.load_json(report_path),
            report_path,
        )
        triage["source_report_selection"] = report_source
    else:
        triage = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "passed": False,
            "runtime_policy": hd_soak_failure_triage.RUNTIME_POLICY,
            "source_report": str(report_path),
            "source_report_selection": report_source,
            "classification": "missing_report",
            "next_probe": "run or regenerate the short-tier soak report before triage",
            "failures": [f"soak report does not exist: {report_path}"],
        }
    triage.update(selection)
    hd_soak_failure_triage.write_outputs(
        triage,
        args.hd_soak_failure_triage_json,
        args.hd_soak_failure_triage_md,
    )
    return {
        "passed": bool(triage.get("passed")),
        "json": str(args.hd_soak_failure_triage_json),
        "markdown": str(args.hd_soak_failure_triage_md),
        "summary": {
            "source_report": triage.get("source_report"),
            "source_report_selection": triage.get("source_report_selection"),
            "canonical_first_step_report": triage.get("canonical_first_step_report"),
            "canonical_first_step_present": triage.get("canonical_first_step_present"),
            "legacy_report": triage.get("legacy_report"),
            "legacy_report_present": triage.get("legacy_report_present"),
            "canonical_runtime_report_missing": triage.get("canonical_runtime_report_missing"),
            "classification": triage.get("classification"),
            "next_probe": triage.get("next_probe"),
            "route": triage.get("route"),
            "final_route_marker": triage.get("final_route_marker"),
            "visual_anomaly_passed": (triage.get("visual_anomalies") or {}).get("passed"),
            "black_patch_risk_count": (triage.get("visual_anomalies") or {}).get("black_patch_risk_count"),
            "palette_or_stripe_risk_count": (
                (triage.get("visual_anomalies") or {}).get("palette_or_stripe_risk_count")
            ),
            "missing_nonblack_bounds_count": (
                (triage.get("visual_anomalies") or {}).get("missing_nonblack_bounds_count")
            ),
            "runtime_policy": triage.get("runtime_policy"),
        },
        "failures": triage.get("failures", []),
    }


def build_hd_soak_failure_triage_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_soak_failure_triage,
        tests=[
            "hd_soak_failure_triage classifies pending visible-runtime approval separately from a game failure",
            "hd_soak_failure_triage classifies AV crashes from exit code 0xC0000005",
            "hd_soak_failure_triage classifies unexpected non-AV process exits",
            "hd_soak_failure_triage enriches missing route click mode from per-route probe JSON",
            "hd_soak_failure_triage classifies render/palette metric regressions",
            "hd_soak_failure_triage records visual anomaly summary counts",
            "hd_soak_failure_triage classifies route/input probe failures",
            "hd_soak_failure_triage classifies route/input drift failures",
            "hd_soak_failure_triage classifies frame progression failures",
            "hd_soak_failure_triage classifies process growth regressions",
            "hd_soak_failure_triage classifies artifact budget failures",
            "hd_soak_failure_triage classifies insufficient frame/process samples as hang/no-frame progress",
            "hd_soak_failure_triage classifies process cleanup failures",
            "hd_soak_failure_triage classifies passing runs without failure",
            "hd_soak_failure_triage rejects raw-passing runs when hd_soak_report guard validation fails",
            "hd_soak_failure_triage classifies raw-passing elapsed-coverage guard failures",
            "hd_soak_failure_triage CLI writes JSON/Markdown and fails closed for failed reports",
        ],
        title="HD Soak Failure Triage Tests",
        json_path=args.hd_soak_failure_triage_tests_json,
        md_path=args.hd_soak_failure_triage_tests_md,
        guard_policy=(
            "proves soak failures are classified into approval, crash, render/palette, "
            "input-route, frame-progression, process-growth, capture, artifact-budget, insufficient-sample hang, "
            "elapsed-coverage, cleanup, or unclassified buckets with next probes"
        ),
    )


def build_hd_soak_route_coverage(args: argparse.Namespace) -> dict[str, Any]:
    report = hd_soak_route_coverage.build_report(
        args.hd_soak_harness_script,
        args.hd_endurance_release_checklist_json,
    )
    hd_soak_route_coverage.write_outputs(
        report,
        args.hd_soak_route_coverage_json,
        args.hd_soak_route_coverage_md,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.hd_soak_route_coverage_json),
        "markdown": str(args.hd_soak_route_coverage_md),
        "summary": {
            "implemented_routes": report.get("implemented_routes"),
            "implemented_tiers": report.get("implemented_tiers"),
            "counts": report.get("counts"),
            "coverage_complete": report.get("coverage_complete"),
            "next_runtime_route": report.get("next_runtime_route"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_hd_soak_route_coverage_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_soak_route_coverage,
        tests=[
            "hd_soak_route_coverage passes the current short-route harness contract",
            "hd_soak_route_coverage keeps future release lanes non-promoting",
            "hd_soak_route_coverage keeps locked future route plans non-executable",
            "hd_soak_route_coverage annotates lanes with current release-checklist blockers",
            "hd_soak_route_coverage treats a missing release checklist as nonfatal",
            "hd_soak_route_coverage fails closed when linked release requirements go stale",
            "hd_soak_route_coverage fails closed when a required route is missing",
            "hd_soak_route_coverage fails closed when a short-tier duration drifts",
            "hd_soak_route_coverage CLI writes JSON/Markdown and respects --require-pass",
        ],
        title="HD Soak Route Coverage Tests",
        json_path=args.hd_soak_route_coverage_tests_json,
        md_path=args.hd_soak_route_coverage_tests_md,
        guard_policy=(
            "proves the soak harness exposes the required short routes and tiers while "
            "future castle, battle, right-bottom, save/load, turn, and campaign lanes stay planned/non-promoting "
            "with locked non-executable route contracts and current blocker annotations from the release checklist"
        ),
    )


def build_hd_continuity_status(args: argparse.Namespace) -> dict[str, Any]:
    report = hd_continuity_status.build_report(args.hd_continuity_proof_json)
    hd_continuity_status.write_outputs(
        report,
        args.hd_continuity_json,
        args.hd_continuity_md,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.hd_continuity_json),
        "markdown": str(args.hd_continuity_md),
        "summary": {
            "counts": report.get("counts"),
            "proof_manifest": report.get("proof_manifest"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_hd_continuity_status_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_continuity_status,
        tests=[
            "hd_continuity_status fails closed when no compact proof manifest exists",
            "hd_continuity_status accepts a valid future continuity proof fixture",
            "hd_continuity_status rejects mixed candidate SHA-256s across continuity lanes",
            "hd_continuity_status rejects live C:\\Clash\\save and forbidden repo artifact references",
            "hd_continuity_status rejects short or palette-corrupt campaign proofs",
            "hd_continuity_status rejects bad stage, SHA, and approval fields",
            "hd_continuity_status requires route markers and before/after observations",
            "hd_continuity_status CLI writes JSON/Markdown and respects --require-pass",
        ],
        title="HD Continuity Status Tests",
        json_path=args.hd_continuity_tests_json,
        md_path=args.hd_continuity_tests_md,
        guard_policy=(
            "proves save/load, turn, and campaign continuity remain blocked until a compact approved proof manifest "
            "documents isolated test-save evidence, route markers, before/after observations, one shared candidate SHA-256, "
            "and no live-save mutation or forbidden repo artifacts"
        ),
    )


def build_hd_soak_long_report_guard(args: argparse.Namespace) -> dict[str, Any]:
    report = hd_soak_long_report_guard.build_report(
        short_step_status_json=args.hd_soak_short_step_status_json,
        proof_json=args.hd_long_soak_proof_json,
    )
    hd_soak_long_report_guard.write_outputs(
        report,
        args.hd_long_soak_report_guard_json,
        args.hd_long_soak_report_guard_md,
    )
    return {
        "passed": bool(report.get("overall")),
        "json": str(args.hd_long_soak_report_guard_json),
        "markdown": str(args.hd_long_soak_report_guard_md),
        "summary": {
            "status": report.get("status"),
            "duration_sec": report.get("duration_sec"),
            "counts": report.get("counts"),
            "short_ladder": report.get("short_ladder"),
            "proof_manifest": report.get("proof_manifest"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_hd_soak_long_report_guard_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_soak_long_report_guard,
        tests=[
            "hd_soak_long_report_guard fails closed while the short ladder and long proof are missing",
            "hd_soak_long_report_guard accepts a valid future two-route 2h+ proof fixture",
            "hd_soak_long_report_guard accepts candidate SHA-256 from nested patch-evidence summaries",
            "hd_soak_long_report_guard rejects mixed candidate SHA-256s across representative routes",
            "hd_soak_long_report_guard rejects missing representative long routes",
            "hd_soak_long_report_guard rejects short duration and failed required checks",
            "hd_soak_long_report_guard rejects unprotected stages",
            "hd_soak_long_report_guard CLI writes JSON/Markdown and respects --require-pass",
        ],
        title="HD Soak Long Report Guard Tests",
        json_path=args.hd_long_soak_report_guard_tests_json,
        md_path=args.hd_long_soak_report_guard_tests_md,
        guard_policy=(
            "proves 2h+ representative-route soak evidence remains locked until the short ladder passes "
            "and approved long map-idle/map-pan soak report guards pass for the same candidate SHA-256"
        ),
    )


def build_hd_endurance_release_checklist(args: argparse.Namespace) -> dict[str, Any]:
    checklist_args = argparse.Namespace(
        stable_stage_json=args.stable_stage_guard_json,
        no_popup_json=args.no_popup_map_evidence_json,
        short_soak_json=args.hd_soak_report_guard_json,
        short_step_status_json=args.hd_soak_short_step_status_json,
        long_soak_json=args.hd_long_soak_report_guard_json,
        manual_json=args.manual_directinput_checklist_json,
        right_bottom_json=args.right_bottom_compose_decision_json,
        castle_json=args.castle_decision_json,
        battle_json=args.battle_ui_evidence_json,
        first_mission_visual_json=args.first_mission_visual_audit_json,
        completion_json=args.current_completion_summary_json,
        continuity_json=args.hd_continuity_json,
        exe_artifact_json=args.exe_artifact_guard_json,
        process_hygiene_json=args.process_hygiene_guard_json,
    )
    report = hd_endurance_release_checklist.build_checklist(checklist_args)
    hd_endurance_release_checklist.write_outputs(
        report,
        args.hd_endurance_release_checklist_json,
        args.hd_endurance_release_checklist_md,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.hd_endurance_release_checklist_json),
        "markdown": str(args.hd_endurance_release_checklist_md),
        "summary": {
            "full_game_complete": report.get("full_game_complete"),
            "counts": report.get("counts"),
            "next_milestone": report.get("next_milestone"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_hd_endurance_release_checklist_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_endurance_release_checklist,
        tests=[
            "hd_endurance_release_checklist can pass a fully proven future release fixture",
            "hd_endurance_release_checklist keeps pending short soaks as the next milestone with missing artifact details",
            "hd_endurance_release_checklist prefers classified per-step status over stale global missing-summary state",
            "hd_endurance_release_checklist accepts a guarded canonical short2 menu-idle step",
            "hd_endurance_release_checklist keeps pending manual DirectInput items blocked",
            "hd_endurance_release_checklist keeps validation-only right-bottom evidence blocked",
            "hd_endurance_release_checklist accepts top-level first-mission clean audit fields",
            "hd_endurance_release_checklist accepts summary-level first-mission clean audit fields",
            "hd_endurance_release_checklist keeps first-mission black-patch evidence release-blocking",
            "hd_endurance_release_checklist CLI writes JSON/Markdown and fails closed",
        ],
        title="HD Endurance Release Checklist Tests",
        json_path=args.hd_endurance_release_checklist_tests_json,
        md_path=args.hd_endurance_release_checklist_tests_md,
        guard_policy=(
            "proves the release-horizon checklist only passes when short/long soak, manual input, "
            "screen-route, first-mission visual, continuity, hygiene, and promotion-boundary evidence are all current"
        ),
    )


def build_hd_soak_intro_skip_rerun_readiness(args: argparse.Namespace) -> dict[str, Any]:
    readiness_args = argparse.Namespace(
        triage_json=hd_soak_intro_skip_rerun_readiness.DEFAULT_TRIAGE_JSON,
        step_status_json=args.hd_soak_short_step_status_json,
        harness_guard_json=args.hd_soak_harness_guard_json,
        dry_run_plan_json=args.hd_soak_dry_run_plan_json,
        visible_runtime_guard_json=args.visible_runtime_launcher_guard_json,
        process_hygiene_json=args.process_hygiene_guard_json,
        exe_artifact_json=args.exe_artifact_guard_json,
    )
    report = hd_soak_intro_skip_rerun_readiness.build_report(readiness_args)
    hd_soak_intro_skip_rerun_readiness.write_outputs(
        report,
        args.hd_soak_intro_skip_rerun_readiness_json,
        args.hd_soak_intro_skip_rerun_readiness_md,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.hd_soak_intro_skip_rerun_readiness_json),
        "markdown": str(args.hd_soak_intro_skip_rerun_readiness_md),
        "summary": {
            "status": report.get("status"),
            "current_step": (report.get("current_step") or {}).get("id"),
            "current_step_status": (report.get("current_step") or {}).get("status"),
            "triage_classification": (report.get("triage") or {}).get("classification"),
            "approval_boundary": report.get("approval_boundary"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_hd_soak_intro_skip_rerun_readiness_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_soak_intro_skip_rerun_readiness,
        tests=[
            "hd_soak_intro_skip_rerun_readiness passes only when the classified failure and guards support an explicit visible rerun",
            "hd_soak_intro_skip_rerun_readiness rejects wrong failure classifications",
            "hd_soak_intro_skip_rerun_readiness rejects approval-command intro-skip drift",
            "hd_soak_intro_skip_rerun_readiness rejects missing visible-runtime approval tokens",
            "hd_soak_intro_skip_rerun_readiness rejects missing visible-runtime approval expiry",
            "hd_soak_intro_skip_rerun_readiness CLI writes JSON/Markdown and respects --require-pass",
        ],
        title="HD Soak Intro-Skip Rerun Readiness Tests",
        json_path=args.hd_soak_intro_skip_rerun_readiness_tests_json,
        md_path=args.hd_soak_intro_skip_rerun_readiness_tests_md,
        guard_policy=(
            "proves a classified intro-skip input-drift failure can become a rerun approval packet "
            "only after repo-only harness, dry-run, visible-runtime, process, and exe-artifact guards pass"
        ),
    )


def build_hd_endurance_next_actions(args: argparse.Namespace) -> dict[str, Any]:
    action_args = argparse.Namespace(
        checklist_json=args.hd_endurance_release_checklist_json,
        short_step_status_json=args.hd_soak_short_step_status_json,
        dry_run_plan_json=args.hd_soak_dry_run_plan_json,
        intro_skip_readiness_json=args.hd_soak_intro_skip_rerun_readiness_json,
    )
    report = hd_endurance_next_actions.build_report(action_args)
    hd_endurance_next_actions.write_outputs(
        report,
        args.hd_endurance_next_actions_json,
        args.hd_endurance_next_actions_md,
    )
    current_step_artifacts = (report.get("next_action") or {}).get("current_step_artifacts") or {}
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.hd_endurance_next_actions_json),
        "markdown": str(args.hd_endurance_next_actions_md),
        "summary": {
            "status": report.get("status"),
            "next_action": (report.get("next_action") or {}).get("id"),
            "requires_explicit_user_approval": (
                (report.get("next_action") or {}).get("requires_explicit_user_approval")
            ),
            "has_plan_verified_execute_command": bool(
                (report.get("next_action") or {}).get("plan_verified_execute_command")
            ),
            "focused_post_run_validation_count": len(
                (report.get("next_action") or {}).get("post_run_validation") or []
            ),
            "handoff_refresh_count": len(
                (report.get("next_action") or {}).get("post_run_handoff_refresh") or []
            ),
            "broad_evidence_refresh_count": len(
                (report.get("next_action") or {}).get("post_run_evidence_refresh") or []
            ),
            "current_step_artifacts": {
                "report_json": current_step_artifacts.get("report_json"),
                "report_json_exists": current_step_artifacts.get("report_json_exists"),
                "guard_json": current_step_artifacts.get("guard_json"),
                "guard_json_exists": current_step_artifacts.get("guard_json_exists"),
                "triage_json": current_step_artifacts.get("triage_json"),
                "triage_json_exists": current_step_artifacts.get("triage_json_exists"),
                "canonical_runtime_report_missing": current_step_artifacts.get(
                    "canonical_runtime_report_missing"
                ),
                "post_run_guard_missing": current_step_artifacts.get("post_run_guard_missing"),
                "post_run_triage_missing": current_step_artifacts.get("post_run_triage_missing"),
            },
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_hd_endurance_next_actions_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_endurance_next_actions,
        tests=[
            "hd_endurance_next_actions requires a current dry-run plan before exposing a visible-runtime command",
            "hd_endurance_next_actions fails closed when the release checklist is missing",
            "hd_endurance_next_actions switches complete fixtures to release-audit mode",
            "hd_endurance_next_actions keeps later pending short-soak steps ahead of manual milestones",
            "hd_endurance_next_actions includes only the stricter dry-run-plan execute command when available",
            "hd_endurance_next_actions records current short-step report, guard, and triage artifact inventory",
            "hd_endurance_next_actions fails closed when the dry-run plan does not match the next short step",
            "hd_endurance_next_actions fails closed when the dry-run plan is stale",
            "hd_endurance_next_actions fails closed when the visible-runtime approval token expires too soon",
            "hd_endurance_next_actions fails closed when the dry-run plan does not verify the base executable",
            "hd_endurance_next_actions starts focused post-run validation with the failure-safe guard/triage refresh",
            "hd_endurance_next_actions requests repo-only triage when a failed short-step report lacks triage",
            "hd_endurance_next_actions points classified failed short steps at their next probe",
            "hd_endurance_next_actions turns a classified intro-skip failure into a rerun approval only after readiness passes",
            "hd_endurance_next_actions CLI writes JSON/Markdown and passes as a triage artifact",
        ],
        title="HD Endurance Next Actions Tests",
        json_path=args.hd_endurance_next_actions_tests_json,
        md_path=args.hd_endurance_next_actions_tests_md,
        guard_policy=(
            "proves the next-action report stays repo-only, separates safe dry-run commands from "
            "approval-gated tokened visible runtime commands, rejects legacy un-tokened runtime commands, "
            "pins canonical short-step report outputs, "
            "starts focused post-run validation with the failure-safe guard/triage refresh, "
            "keeps broad evidence refresh separate, keeps the "
            "short ladder ahead of later manual milestones, preserves classified failure triage, "
            "records current-step artifact inventory, records post-run validation steps, "
            "requires the dry-run plan to verify the base executable, and requires enough "
            "visible-runtime approval TTL before showing an executable command"
        ),
    )


def build_hd_soak_short_tier_ladder(args: argparse.Namespace) -> dict[str, Any]:
    ladder_args = argparse.Namespace(
        route_coverage_json=args.hd_soak_route_coverage_json,
        next_actions_json=args.hd_endurance_next_actions_json,
        soak_report_json=args.hd_soak_report_guard_json,
    )
    report = hd_soak_short_tier_ladder.build_report(ladder_args)
    hd_soak_short_tier_ladder.write_outputs(
        report,
        args.hd_soak_short_tier_ladder_json,
        args.hd_soak_short_tier_ladder_md,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.hd_soak_short_tier_ladder_json),
        "markdown": str(args.hd_soak_short_tier_ladder_md),
        "summary": {
            "ladder_complete": report.get("ladder_complete"),
            "current_step": (report.get("current_step") or {}).get("id"),
            "current_step_status": (report.get("current_step") or {}).get("status"),
            "long_tiers_locked": (report.get("locks") or {}).get("long_tiers_locked"),
            "future_lanes_locked": (report.get("locks") or {}).get("future_lanes_locked"),
            "right_bottom_promotion_blocked": (report.get("locks") or {}).get("right_bottom_promotion_blocked"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_hd_soak_short_tier_ladder_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_soak_short_tier_ladder,
        tests=[
            "hd_soak_short_tier_ladder passes as a repo-only plan while current short2 menu-idle is approval-gated and input-drift bounded",
            "hd_soak_short_tier_ladder advances to short2 map-idle after a passing short2 menu-idle fixture",
            "hd_soak_short_tier_ladder fails closed when a required harness route is missing",
            "hd_soak_short_tier_ladder catches a mismatched first-step next-action command",
            "hd_soak_short_tier_ladder CLI writes JSON/Markdown and respects --require-pass",
        ],
        title="HD Soak Short-Tier Ladder Tests",
        json_path=args.hd_soak_short_tier_ladder_tests_json,
        md_path=args.hd_soak_short_tier_ladder_tests_md,
        guard_policy=(
            "proves the short soak ladder is ordered, approval-gated, non-promoting, "
            "and keeps long/future lanes locked until prerequisite soak evidence exists"
        ),
    )


def build_hd_soak_short_artifact_manifest(args: argparse.Namespace) -> dict[str, Any]:
    manifest_args = argparse.Namespace(
        legacy_report_json=args.hd_soak_report,
        legacy_report_md=Path(str(args.hd_soak_report).replace(".json", ".md")),
    )
    report = hd_soak_short_artifact_manifest.build_report(manifest_args)
    hd_soak_short_artifact_manifest.write_outputs(
        report,
        args.hd_soak_short_artifact_manifest_json,
        args.hd_soak_short_artifact_manifest_md,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.hd_soak_short_artifact_manifest_json),
        "markdown": str(args.hd_soak_short_artifact_manifest_md),
        "summary": {
            "step_count": report.get("step_count"),
            "existing_step_report_count": report.get("existing_step_report_count"),
            "legacy_report_exists": (report.get("legacy_default_report") or {}).get("json_exists"),
            "long_tiers_locked": (report.get("locks") or {}).get("long_tiers_locked_until_step_reports_pass"),
            "future_lanes_locked": (report.get("locks") or {}).get("future_lanes_locked_until_step_reports_pass"),
            "right_bottom_promotion_blocked": (report.get("locks") or {}).get("right_bottom_promotion_blocked"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_hd_soak_short_artifact_manifest_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_soak_short_artifact_manifest,
        tests=[
            "hd_soak_short_artifact_manifest emits unique canonical report paths for every short ladder step",
            "hd_soak_short_artifact_manifest pins report outputs, input-drift limits, and keeps execution approval-gated",
            "hd_soak_short_artifact_manifest fails closed on duplicate canonical paths",
            "hd_soak_short_artifact_manifest fails closed when outputs leave captures/current",
            "hd_soak_short_artifact_manifest CLI writes JSON/Markdown and respects --require-pass",
        ],
        title="HD Soak Short Artifact Manifest Tests",
        json_path=args.hd_soak_short_artifact_manifest_tests_json,
        md_path=args.hd_soak_short_artifact_manifest_tests_md,
        guard_policy=(
            "proves each short soak ladder step has durable current report, guard, and triage paths, "
            "with execution commands gated by -Execute -AllowVisibleRuntime"
        ),
    )


def build_hd_soak_short_validation_refresh(args: argparse.Namespace) -> dict[str, Any]:
    refresh_args = argparse.Namespace(manifest_json=args.hd_soak_short_artifact_manifest_json)
    report = hd_soak_short_validation_refresh.build_report(refresh_args)
    hd_soak_short_validation_refresh.write_outputs(
        report,
        args.hd_soak_short_validation_refresh_json,
        args.hd_soak_short_validation_refresh_md,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.hd_soak_short_validation_refresh_json),
        "markdown": str(args.hd_soak_short_validation_refresh_md),
        "summary": {
            "status": report.get("status"),
            "counts": report.get("counts"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_hd_soak_short_validation_refresh_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_soak_short_validation_refresh,
        tests=[
            "hd_soak_short_validation_refresh passes as pending when no canonical reports exist",
            "hd_soak_short_validation_refresh writes guard and triage artifacts for passing canonical reports",
            "hd_soak_short_validation_refresh writes failed guard and classified triage for failed canonical reports",
            "hd_soak_short_validation_refresh fails closed when a canonical report mismatches its step",
            "hd_soak_short_validation_refresh fails closed when the manifest is missing",
            "hd_soak_short_validation_refresh CLI writes JSON/Markdown and respects --require-pass",
        ],
        title="HD Soak Short Validation Refresh Tests",
        json_path=args.hd_soak_short_validation_refresh_tests_json,
        md_path=args.hd_soak_short_validation_refresh_tests_md,
        guard_policy=(
            "proves canonical short soak reports are automatically guarded and triaged before "
            "step-status evaluation, while missing reports remain a safe pending repo-only state"
        ),
    )


def build_hd_soak_short_step_status(args: argparse.Namespace) -> dict[str, Any]:
    status_args = argparse.Namespace(
        manifest_json=args.hd_soak_short_artifact_manifest_json,
        legacy_report_json=args.hd_soak_report,
    )
    report = hd_soak_short_step_status.build_report(status_args)
    hd_soak_short_step_status.write_outputs(
        report,
        args.hd_soak_short_step_status_json,
        args.hd_soak_short_step_status_md,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.hd_soak_short_step_status_json),
        "markdown": str(args.hd_soak_short_step_status_md),
        "summary": {
            "ladder_complete": report.get("ladder_complete"),
            "counts": report.get("counts"),
            "current_step": (report.get("current_step") or {}).get("id"),
            "current_step_status": (report.get("current_step") or {}).get("status"),
            "long_tiers_locked": (report.get("locks") or {}).get("long_tiers_locked"),
            "future_lanes_locked": (report.get("locks") or {}).get("future_lanes_locked"),
            "right_bottom_promotion_blocked": (report.get("locks") or {}).get("right_bottom_promotion_blocked"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_hd_soak_short_step_status_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_soak_short_step_status,
        tests=[
            "hd_soak_short_step_status passes for the current pending approval state",
            "hd_soak_short_step_status advances after a guarded passing first-step fixture",
            "hd_soak_short_step_status fails closed when a canonical report lacks guard output",
            "hd_soak_short_step_status fails closed when guard output is stale or mismatched",
            "hd_soak_short_step_status accepts classified failed reports with triage output",
            "hd_soak_short_step_status fails closed when triage output is stale or mismatched",
            "hd_soak_short_step_status CLI writes JSON/Markdown and respects --require-pass",
        ],
        title="HD Soak Short-Step Status Tests",
        json_path=args.hd_soak_short_step_status_tests_json,
        md_path=args.hd_soak_short_step_status_tests_md,
        guard_policy=(
            "proves per-step soak status stays repo-only, advances only after guarded passing output, "
            "rejects stale guard/triage artifacts that do not match the canonical report, "
            "and demands triage for failed canonical runtime reports"
        ),
    )


def build_hd_soak_dry_run_plan(args: argparse.Namespace) -> dict[str, Any]:
    plan_args = argparse.Namespace(
        step_status_json=args.hd_soak_short_step_status_json,
        script=args.hd_soak_harness_script,
        read_plan_json=None,
    )
    report = hd_soak_dry_run_plan.build_report(plan_args)
    hd_soak_dry_run_plan.write_outputs(
        report,
        args.hd_soak_dry_run_plan_json,
        args.hd_soak_dry_run_plan_md,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.hd_soak_dry_run_plan_json),
        "markdown": str(args.hd_soak_dry_run_plan_md),
        "summary": {
            "status": report.get("status"),
            "current_step": (report.get("current_step") or {}).get("id"),
            "current_step_status": (report.get("current_step") or {}).get("status"),
            "dry_run": (report.get("plan") or {}).get("dry_run"),
            "candidate_dir": (report.get("plan") or {}).get("candidate_dir"),
            "output_root": (report.get("plan") or {}).get("output_root"),
            "stable_stage_should_change": (report.get("locks") or {}).get("stable_stage_should_change"),
            "right_bottom_promotion_blocked": (report.get("locks") or {}).get(
                "right_bottom_promotion_blocked"
            ),
            "focused_post_run_validation_count": len(report.get("post_run_validation") or []),
            "handoff_refresh_count": len(report.get("post_run_handoff_refresh") or []),
            "broad_evidence_refresh_count": len(report.get("post_run_evidence_refresh") or []),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_hd_soak_dry_run_plan_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_soak_dry_run_plan,
        tests=[
            "hd_soak_dry_run_plan accepts the current-step dry-run plan fixture",
            "hd_soak_dry_run_plan rejects executed plans",
            "hd_soak_dry_run_plan rejects protected-stage drift",
            "hd_soak_dry_run_plan rejects execute commands without -RequirePass or -Json",
            "hd_soak_dry_run_plan rejects visible-runtime execute commands without the approval token",
            "hd_soak_dry_run_plan rejects visible-runtime execute commands without the approval expiry",
            "hd_soak_dry_run_plan rejects visible-runtime approval packets that expire too soon",
            "hd_soak_dry_run_plan rejects execute commands missing explicit stage/input/workdir/output roots",
            "hd_soak_dry_run_plan rejects repository candidate output",
            "hd_soak_dry_run_plan rejects missing or unverified base executable input",
            "hd_soak_dry_run_plan CLI writes JSON/Markdown and respects --require-pass",
        ],
        title="HD Soak Dry-Run Plan Tests",
        json_path=args.hd_soak_dry_run_plan_tests_json,
        md_path=args.hd_soak_dry_run_plan_tests_md,
        guard_policy=(
            "proves the current short-soak dry-run handoff is machine-readable, "
            "non-executing, protected-stage, canonical-path, outside-repo, and "
            "fails closed unless copied execute commands include -RequirePass -Json "
            "with a fresh approval token, and the base executable exists with the expected SHA"
        ),
    )


def build_hd_soak_approval_preflight(args: argparse.Namespace) -> dict[str, Any]:
    preflight_args = argparse.Namespace(
        next_actions_json=args.hd_endurance_next_actions_json,
        step_status_json=args.hd_soak_short_step_status_json,
        hd_soak_harness_guard_json=args.hd_soak_harness_guard_json,
        hd_soak_dry_run_plan_json=args.hd_soak_dry_run_plan_json,
        intro_skip_readiness_json=args.hd_soak_intro_skip_rerun_readiness_json,
        visible_runtime_guard_json=args.visible_runtime_launcher_guard_json,
        process_hygiene_json=args.process_hygiene_guard_json,
        exe_artifact_json=args.exe_artifact_guard_json,
    )
    report = hd_soak_approval_preflight.build_report(preflight_args)
    hd_soak_approval_preflight.write_outputs(
        report,
        args.hd_soak_approval_preflight_json,
        args.hd_soak_approval_preflight_md,
    )
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.hd_soak_approval_preflight_json),
        "markdown": str(args.hd_soak_approval_preflight_md),
        "summary": {
            "status": report.get("status"),
            "current_step": (report.get("current_step") or {}).get("id"),
            "current_step_status": (report.get("current_step") or {}).get("status"),
            "dry_run_plan_status": (report.get("dry_run_plan_consistency") or {}).get("status"),
            "dry_run_plan_passed": (report.get("dry_run_plan_consistency") or {}).get("passed"),
            "writes_outside_repo": report.get("writes_outside_repo"),
            "stable_stage_should_change": (report.get("locks") or {}).get("stable_stage_should_change"),
            "right_bottom_promotion_blocked": (report.get("locks") or {}).get(
                "right_bottom_promotion_blocked"
            ),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_hd_soak_approval_preflight_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_hd_soak_approval_preflight,
        tests=[
            "hd_soak_approval_preflight passes with a canonical first-step approval packet and explicit input-drift limit",
            "hd_soak_approval_preflight records current-step report, guard, and triage artifact presence",
            "hd_soak_approval_preflight fails closed when runtime command approval flags or paths drift",
            "hd_soak_approval_preflight fails closed when dry-run command can execute",
            "hd_soak_approval_preflight catches next-actions and short-step command mismatches",
            "hd_soak_approval_preflight catches next-actions and short-step dry-run mismatches",
            "hd_soak_approval_preflight catches post-run validation mismatches and require-pass guard ordering regressions",
            "hd_soak_approval_preflight catches next-actions and short-step handoff-refresh mismatches",
            "hd_soak_approval_preflight catches next-actions and broad evidence-refresh mismatches",
            "hd_soak_approval_preflight catches stale next-action current-step artifact inventory",
            "hd_soak_approval_preflight catches next-actions and dry-run plan execute-command mismatches",
            "hd_soak_approval_preflight catches stale next-actions dry-run plan summaries",
            "hd_soak_approval_preflight fails closed when the current short-step status is not pending",
            "hd_soak_approval_preflight accepts a classified intro-skip rerun only when readiness passes",
            "hd_soak_approval_preflight fails closed when source guards are not passing",
            "hd_soak_approval_preflight fails closed when the dry-run plan is not passing",
            "hd_soak_approval_preflight fails closed when the dry-run plan is stale",
            "hd_soak_approval_preflight fails closed when the visible-runtime approval token expires too soon",
            "hd_soak_approval_preflight catches dry-run plan current-step and report-path mismatches",
            "hd_soak_approval_preflight fails closed when the dry-run plan does not verify the base executable",
            "hd_soak_approval_preflight catches dry-run plan execute commands missing explicit stage/input/root pins",
            "hd_soak_approval_preflight catches visible-runtime execute commands without the approval token",
            "hd_soak_approval_preflight catches visible-runtime execute commands without the approval expiry",
            "hd_soak_approval_preflight can gate the next short step after the first soak passes",
            "hd_soak_approval_preflight CLI writes JSON/Markdown and respects --require-pass",
        ],
        title="HD Soak Approval Preflight Tests",
        json_path=args.hd_soak_approval_preflight_tests_json,
        md_path=args.hd_soak_approval_preflight_tests_md,
        guard_policy=(
            "proves the first short2 visible-runtime soak remains explicit-approval gated, "
            "pins canonical per-step report paths, keeps dry-runs non-executing, can advance "
            "to later short steps, starts focused post-run validation with the failure-safe "
            "guard/triage refresh, keeps broad evidence refresh separate, requires next-action "
            "artifact inventory to match the preflight state, "
            "requires the actual harness dry-run plan and embedded next-action summary to match, "
            "requires visible-runtime approval TTL and limit summaries, "
            "requires verified base-executable input, and requires clean "
            "harness/runtime/process/executable guards before requesting approval"
        ),
    )


def build_promotion_override_manifest(args: argparse.Namespace) -> dict[str, Any]:
    report_args = argparse.Namespace(
        manifest=args.promotion_override_manifest,
        target_scope=None,
        candidate_stage=None,
        candidate_sha256=None,
    )
    report = promotion_override_manifest.build_report(report_args)
    write_json(args.promotion_override_manifest_json, report)
    promotion_override_manifest.write_markdown(args.promotion_override_manifest_md, report)
    return {
        "passed": bool(report.get("passed")),
        "json": str(args.promotion_override_manifest_json),
        "markdown": str(args.promotion_override_manifest_md),
        "summary": {
            "override_active": report.get("override_active"),
            "manifest_supplied": report.get("override_manifest", {}).get("supplied"),
            "manifest_valid": report.get("override_manifest", {}).get("valid"),
            "guard_policy": report.get("guard_policy"),
            "runtime_policy": report.get("runtime_policy"),
        },
        "failures": report.get("failures", []),
    }


def build_promotion_override_manifest_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_promotion_override_manifest,
        tests=[
            "promotion_override_manifest treats absent manifest as inactive",
            "promotion_override_manifest validates complete override manifests",
            "promotion_override_manifest rejects missing approval, bad SHA, and stale process evidence",
            "promotion_override_manifest rejects scope/stage/SHA mismatches",
            "promotion_override_manifest CLI writes outputs and fails closed",
        ],
        title="Promotion Override Manifest Tests",
        json_path=args.promotion_override_manifest_tests_json,
        md_path=args.promotion_override_manifest_tests_md,
        guard_policy="proves CDB-only promotion overrides require an explicit valid manifest",
    )


def build_docs_consistency_guard(args: argparse.Namespace, checks: dict[str, Any]) -> dict[str, Any]:
    synthetic_checks = dict(checks)
    synthetic_checks["docs_consistency_guard"] = {
        "passed": True,
        "json": str(args.docs_consistency_json),
        "markdown": str(args.docs_consistency_md),
        "summary": {"synthetic_for_docs_consistency_cycle": True},
        "failures": [],
    }
    synthetic_checks["docs_consistency_guard_tests"] = {
        "passed": True,
        "json": str(args.docs_consistency_tests_json),
        "markdown": str(args.docs_consistency_tests_md),
        "summary": {"synthetic_for_docs_consistency_cycle": True},
        "failures": [],
    }
    synthetic_boundary = no_popup_boundary_guard.build_guard_from_checks(
        synthetic_checks,
        args.evidence_index,
    )
    synthetic_checks["no_popup_boundary_guard"] = {
        "passed": bool(synthetic_boundary.get("passed")),
        "json": str(args.no_popup_boundary_guard_json),
        "markdown": str(args.no_popup_boundary_guard_md),
        "summary": {
            "required_guard_count": synthetic_boundary.get("required_guard_count"),
            "required_supporting_report_count": synthetic_boundary.get("required_supporting_report_count"),
            "required_report_count": synthetic_boundary.get("required_report_count"),
        },
        "failures": synthetic_boundary.get("failures", []),
    }
    guard_args = argparse.Namespace(
        refresh_json=args.write_json,
        refresh_payload={
            "passed": all(bool(check.get("passed")) for check in synthetic_checks.values()),
            "checks": synthetic_checks,
        },
        boundary_json=args.no_popup_boundary_guard_json,
        boundary_payload=synthetic_boundary,
        manual_checklist_json=args.manual_directinput_checklist_json,
        manual_template_json=args.manual_directinput_proof_template_report_json,
        stable_stage_json=args.stable_stage_guard_json,
        right_bottom_matrix_json=args.right_bottom_compose_matrix_json,
        right_bottom_decision_json=args.right_bottom_compose_decision_json,
        castle_matrix_json=args.castle_matrix_json,
        castle_decision_json=args.castle_decision_json,
        hd_map_smoke_json=args.hd_map_smoke_json,
        post_owner_evidence_json=docs_consistency_guard.DEFAULT_POST_OWNER_EVIDENCE_JSON,
        no_popup_map_json=args.no_popup_map_evidence_json,
        visible_runtime_json=args.visible_runtime_launcher_guard_json,
        no_visible_runtime_json=args.no_visible_runtime_guard_json,
        evidence_index=args.evidence_index,
        codex_loop_docs=docs_consistency_guard.DEFAULT_CODEX_LOOP_DOCS,
        readme_progress_docs=docs_consistency_guard.DEFAULT_README_PROGRESS_DOCS,
        wiki_summary_docs=docs_consistency_guard.DEFAULT_WIKI_SUMMARY_DOCS,
    )
    guard = docs_consistency_guard.build_guard(guard_args)
    write_json(args.docs_consistency_json, guard)
    docs_consistency_guard.write_markdown(args.docs_consistency_md, guard)
    return {
        "passed": bool(guard.get("passed")),
        "json": str(args.docs_consistency_json),
        "markdown": str(args.docs_consistency_md),
        "summary": {
            "check_count": len(guard.get("checks", {})),
            "guard_policy": guard.get("guard_policy"),
            "runtime_policy": guard.get("runtime_policy"),
        },
        "failures": guard.get("failures", []),
    }


def build_docs_consistency_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_docs_consistency_guard,
        tests=[
            "docs_consistency_guard passes current fact fixtures",
            "docs_consistency_guard falls back to durable post-owner screenshots when smoke output is fail-closed",
            "docs_consistency_guard fails stale boundary counts",
            "docs_consistency_guard fails stale boundary status",
            "docs_consistency_guard fails stale validation status",
            "docs_consistency_guard allows nonpassing right-bottom defer status",
            "docs_consistency_guard CLI writes outputs and fails closed",
        ],
        title="Docs Consistency Guard Tests",
        json_path=args.docs_consistency_tests_json,
        md_path=args.docs_consistency_tests_md,
        guard_policy="proves current docs fail closed when generated counts or promotion-boundary facts go stale",
    )


def build_current_completion_summary(args: argparse.Namespace, checks: dict[str, Any]) -> dict[str, Any]:
    counted = {
        name: check
        for name, check in checks.items()
        if name not in {"current_completion_summary", "current_completion_summary_tests"}
    }
    refresh_record = {
        "passed": all(bool(check.get("passed")) for check in counted.values()),
        "checks": dict(checks),
    }
    summary = current_completion_summary.build_summary_from_data(
        refresh=refresh_record,
        battle=current_completion_summary.load_json(args.completion_battle_json),
        checklist=current_completion_summary.load_json(args.manual_directinput_checklist_json),
        right_bottom=current_completion_summary.load_json(args.right_bottom_compose_decision_json),
        repo_test_sweep=current_completion_summary.load_repo_test_sweep(args.repo_test_sweep_json),
        source_artifacts={
            "refresh_json": str(args.write_json),
            "battle_json": str(args.completion_battle_json),
            "manual_checklist_json": str(args.manual_directinput_checklist_json),
            "right_bottom_decision_json": str(args.right_bottom_compose_decision_json),
            "repo_test_sweep_json": str(args.repo_test_sweep_json),
        },
    )
    write_json(args.current_completion_summary_json, summary)
    current_completion_summary.write_markdown(args.current_completion_summary_md, summary)
    percentages = {
        row["id"]: row.get("completion_percent")
        for row in summary.get("percentages", [])
    }
    return {
        "passed": bool(summary.get("passed")),
        "json": str(args.current_completion_summary_json),
        "markdown": str(args.current_completion_summary_md),
        "summary": {
            "full_game_complete": summary.get("full_game_complete"),
            "full_game_percent_statement": summary.get("full_game_percent_statement"),
            "percentages": percentages,
        },
        "failures": summary.get("failures", []),
    }


def build_current_completion_summary_tests(args: argparse.Namespace) -> dict[str, Any]:
    return simple_test_check(
        test_runner=test_current_completion_summary,
        tests=[
            "current_completion_summary computes repo evidence, test sweep, focused lane, promotion, and manual validation percentages",
            "current_completion_summary fails closed when focused completion percentage is missing",
            "current_completion_summary fails closed when the repo test sweep artifact is missing",
            "current_completion_summary fails closed when the repo test sweep reports failures",
            "current_completion_summary CLI writes JSON/Markdown and returns 2 under --require-pass failure",
        ],
        title="Current Completion Summary Tests",
        json_path=args.current_completion_summary_tests_json,
        md_path=args.current_completion_summary_tests_md,
        guard_policy=(
            "proves the generated percentage summary stays machine-checkable "
            "and does not claim full-game completion while manual proof is absent"
        ),
    )


def build_barracks_success(args: argparse.Namespace) -> dict[str, Any]:
    log = args.barracks_success_run / "cdb-surface-dump.log"
    failures: list[str] = []
    if not log.exists():
        return {
            "passed": False,
            "run": str(args.barracks_success_run),
            "log": str(log),
            "failures": [f"missing barracks success log: {log}"],
        }
    summary = castle_barracks_action_click_summary.parse_log(
        log,
        expected_desc=int(args.barracks_success_desc, 0),
        expected_callback=int(args.barracks_success_callback, 0),
    )
    ready = bool(
        summary["marker_counts"]["APBARRACKS_SURFDUMP_READY"]
        or summary["marker_counts"]["SURFDUMP_READY"]
    )
    if not ready:
        failures.append("barracks success surface-ready marker was not observed")
    if not summary.get("descriptor_click_ok"):
        failures.append("barracks success descriptor click was not observed")
    if not summary.get("success_4356c0_ok"):
        failures.append("barracks success branch was not observed")
    if summary.get("failure_exit_count"):
        failures.append("barracks success proof used a failure exit")
    if summary.get("av_count"):
        failures.append("barracks success AV rows were observed")
    return {
        "passed": not failures,
        "run": str(args.barracks_success_run),
        "log": str(log),
        "screenshot": str((args.barracks_success_run / "surface.png").resolve())
        if (args.barracks_success_run / "surface.png").exists()
        else None,
        "summary": {
            "ready": ready,
            "descriptor_click_ok": summary.get("descriptor_click_ok"),
            "success_4356c0_ok": summary.get("success_4356c0_ok"),
            "failure_exit_count": summary.get("failure_exit_count"),
            "av_count": summary.get("av_count"),
            "last_select_forced": summary.get("last_select_forced"),
            "last_success_4356c0": summary.get("last_success_4356c0"),
        },
        "failures": failures,
    }


def build_right_bottom_ui(args: argparse.Namespace) -> dict[str, Any]:
    summary_path = args.right_bottom_ui_run / "right-bottom-ui-summary.json"
    bounds_path = args.right_bottom_ui_run / "right-bottom-ui-bounds.json"
    failures: list[str] = []
    if not summary_path.exists():
        return {
            "passed": False,
            "run": str(args.right_bottom_ui_run),
            "summary_json": str(summary_path),
            "failures": [f"missing right-bottom UI summary: {summary_path}"],
        }
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    marker_counts = summary.get("MarkerCounts") or {}
    if not summary.get("SurfaceDumpPassed"):
        failures.append("right-bottom UI surface dump did not pass")
    if not summary.get("RbuiMarkersSeen"):
        failures.append("right-bottom UI RBUI markers were not observed")
    if int(marker_counts.get("SURFDUMP_PLAYGAME") or 0) <= 0:
        failures.append("right-bottom UI run did not reach SURFDUMP_PLAYGAME")
    if int(marker_counts.get("SURFDUMP_READY") or 0) <= 0:
        failures.append("right-bottom UI run did not reach SURFDUMP_READY")
    if summary.get("Passed") is False:
        failures.append("right-bottom UI wrapper reported failure")

    bounds_summary: dict[str, Any] | None = None
    if bounds_path.exists():
        bounds = json.loads(bounds_path.read_text(encoding="utf-8-sig"))
        images = bounds.get("images") or []
        regions = images[0].get("regions") if images else []
        bounds_summary = {
            region.get("name"): {
                "nonblack_percent": region.get("nonblack_percent"),
                "black_percent": region.get("black_percent"),
                "flags": region.get("flags"),
            }
            for region in regions
            if region.get("name")
        }

    return {
        "passed": not failures,
        "run": str(args.right_bottom_ui_run),
        "summary_json": str(summary_path),
        "bounds_json": str(bounds_path) if bounds_path.exists() else None,
        "screenshot": canonical_capture_path(summary.get("PngPath")),
        "summary": {
            "surface_dump_passed": summary.get("SurfaceDumpPassed"),
            "rbui_markers_seen": summary.get("RbuiMarkersSeen"),
            "rbui_desc_switch": marker_counts.get("RBUI_DESC_SWITCH"),
            "rbui_viewport_switch": marker_counts.get("RBUI_VIEWPORT_SWITCH"),
            "rbui_panel_draw": marker_counts.get("RBUI_PANEL_DRAW"),
            "rbui_action_box": marker_counts.get("RBUI_ACTION_BOX"),
            "surfdump_playgame": marker_counts.get("SURFDUMP_PLAYGAME"),
            "surfdump_ready": marker_counts.get("SURFDUMP_READY"),
            "bounds": bounds_summary,
        },
        "failures": failures,
    }


def evaluate_right_bottom_fixture_natural_draw(fixture_run: Path) -> tuple[dict[str, Any], list[str]]:
    """Evaluate the accepted slot5-as-slot0 fixture run as natural-draw evidence.

    user ruling 2026-07-14: slot5-as-slot0 fixture accepted as natural-draw evidence.
    Fails closed when the fixture run/log/result-summary is missing or when any
    required marker (PANEL_DRAW, GRID_DRAW, NOWNER_WRAPPER_COPYBACK_DONE) is absent
    or any access-violation indicator is present.
    """
    failures: list[str] = []
    log = fixture_run / "cdb-surface-dump.log"
    result_summary_path = fixture_run / "right-bottom-slot-fixture-result-summary.json"
    payload: dict[str, Any] = {
        "ruling": RIGHT_BOTTOM_FIXTURE_NATURAL_DRAW_RULING,
        "fixture_run": str(fixture_run),
        "log": str(log),
        "result_summary_json": str(result_summary_path),
        "marker_counts": None,
        "av_count": None,
        "proof_class": None,
        "expected_slot_match": None,
        "row_count": None,
        "stage": None,
        "candidate_sha256": None,
    }
    if not log.exists():
        failures.append(f"missing right-bottom fixture natural-draw log: {log}")
        return payload, failures

    log_text = log.read_text(encoding="utf-8", errors="replace")
    marker_counts = {
        "NOWNER_435BC0_PANEL_DRAW": log_text.count("NOWNER_435BC0_PANEL_DRAW"),
        "NOWNER_435BC0_GRID_DRAW": log_text.count("NOWNER_435BC0_GRID_DRAW"),
        "NOWNER_WRAPPER_COPYBACK_DONE": log_text.count("NOWNER_WRAPPER_COPYBACK_DONE"),
        "NOWNER_WRAPPER_PRESENT_CALL": log_text.count("NOWNER_WRAPPER_PRESENT_CALL"),
    }
    av_count = (
        log_text.lower().count("c0000005")
        + log_text.lower().count("access violation")
        + log_text.count("AV_")
    )
    payload["marker_counts"] = marker_counts
    payload["av_count"] = av_count
    if marker_counts["NOWNER_435BC0_PANEL_DRAW"] < 1:
        failures.append("right-bottom fixture natural-draw log has no NOWNER_435BC0_PANEL_DRAW rows")
    if marker_counts["NOWNER_435BC0_GRID_DRAW"] < 1:
        failures.append("right-bottom fixture natural-draw log has no NOWNER_435BC0_GRID_DRAW rows")
    if marker_counts["NOWNER_WRAPPER_COPYBACK_DONE"] < 1:
        failures.append("right-bottom fixture natural-draw log has no NOWNER_WRAPPER_COPYBACK_DONE rows")
    if av_count:
        failures.append(f"right-bottom fixture natural-draw log has AV rows: {av_count}")

    if not result_summary_path.exists():
        failures.append(
            f"missing right-bottom fixture natural-draw result summary: {result_summary_path}"
        )
        return payload, failures

    result_summary = json.loads(result_summary_path.read_text(encoding="utf-8-sig"))
    payload["proof_class"] = result_summary.get("proof_class")
    payload["expected_slot_match"] = result_summary.get("expected_slot_match")
    payload["row_count"] = result_summary.get("row_count")
    payload["stage"] = result_summary.get("stage")
    payload["candidate_sha256"] = result_summary.get("candidate_sha256")
    if result_summary.get("proof_class") != "non_natural_isolated_fixture":
        failures.append(
            "right-bottom fixture result summary proof_class is "
            f"{result_summary.get('proof_class')}, expected non_natural_isolated_fixture"
        )
    if result_summary.get("expected_slot_match") is not True:
        failures.append("right-bottom fixture result summary did not confirm expected_slot_match")
    return payload, failures


def build_right_bottom_compose_ui_probe(args: argparse.Namespace) -> dict[str, Any]:
    run = args.right_bottom_compose_ui_run
    manifest_path = args.right_bottom_compose_patch_manifest
    summary_path = run / "right-bottom-ui-summary.json"
    surface_summary_path = run / "summary.json"
    bounds_path = run / "right-bottom-ui-bounds.json"
    log = run / "cdb-surface-dump.log"
    failures: list[str] = []

    for label, path in (
        ("right-bottom compose UI summary", summary_path),
        ("right-bottom compose surface summary", surface_summary_path),
        ("right-bottom compose UI bounds", bounds_path),
        ("right-bottom compose UI log", log),
        ("right-bottom compose patch manifest", manifest_path),
    ):
        if not path.exists():
            return {
                "passed": False,
                "run": str(run),
                "summary_json": str(summary_path),
                "manifest": str(manifest_path),
                "failures": [f"missing {label}: {path}"],
            }

    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    surface_summary = json.loads(surface_summary_path.read_text(encoding="utf-8-sig"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    bounds = json.loads(bounds_path.read_text(encoding="utf-8-sig"))
    log_text = log.read_text(encoding="utf-8", errors="replace")
    marker_counts = summary.get("MarkerCounts") or {}
    patch_group = (manifest.get("groups") or {}).get("right-bottom-compose-proof") or {}
    current_gate = manifest.get("current_hd_map_gate") or {}

    images = bounds.get("images") or []
    regions = images[0].get("regions") if images else []
    bounds_summary = {
        region.get("name"): {
            "nonblack_percent": region.get("nonblack_percent"),
            "black_percent": region.get("black_percent"),
            "flags": region.get("flags"),
        }
        for region in regions
        if region.get("name")
    }

    av_count = (
        log_text.lower().count("c0000005")
        + log_text.lower().count("access violation")
        + log_text.count("AV_")
    )

    natural_owner_rows = int(marker_counts.get("RBUI_PANEL_DRAW") or 0) + int(
        marker_counts.get("RBUI_ACTION_BOX") or 0
    )
    natural_rows_present = natural_owner_rows > 0
    natural_draw_source = "bare_map_natural_rows" if natural_rows_present else "slot5_as_slot0_fixture"
    fixture_payload: dict[str, Any] | None = None

    if not summary.get("SurfaceDumpPassed"):
        failures.append("right-bottom compose UI surface dump did not pass")
    if not summary.get("RbuiMarkersSeen"):
        failures.append("right-bottom compose UI RBUI markers were not observed")
    if summary.get("Passed") is False:
        if natural_rows_present:
            failures.append("right-bottom compose UI wrapper reported failure")
        else:
            # user ruling 2026-07-14: slot5-as-slot0 fixture accepted as natural-draw evidence.
            # On the bare map the wrapper's owner/action-rows requirement is the retired
            # rows-absent expectation; accept the wrapper failure only when it is exactly
            # that condition (no error, surface dump and RBUI markers otherwise fine).
            rows_only_wrapper_failure = bool(
                summary.get("Error") in (None, "")
                and summary.get("SurfaceDumpPassed")
                and summary.get("RbuiMarkersSeen")
                and summary.get("RequiresOwnerActionRows") is True
                and summary.get("OwnerActionRowsSeen") is False
            )
            if not rows_only_wrapper_failure:
                failures.append(
                    "right-bottom compose UI wrapper reported failure beyond the retired rows-absent expectation"
                )
    if not surface_summary.get("HiddenDesktop"):
        failures.append("right-bottom compose UI run was not hidden-desktop")
    if surface_summary.get("SkipMapValidation"):
        failures.append("right-bottom compose UI run skipped map validation")
    if not surface_summary.get("NoSkipStartAnims"):
        failures.append("right-bottom compose UI run did not use full startup animation path")
    if surface_summary.get("Stage") != RIGHT_BOTTOM_COMPOSE_PATCH_STAGE:
        failures.append("right-bottom compose UI stage mismatch")
    if summary.get("Stage") != RIGHT_BOTTOM_COMPOSE_PATCH_STAGE:
        failures.append("right-bottom compose UI wrapper stage mismatch")
    if not probe_template_matches(
        summary.get("ExtraProbeTemplate"),
        "probes/cdb/ui/clash95_right_bottom_ui_extra.cdb",
    ):
        failures.append("right-bottom compose UI extra probe template was not recorded")
    if str(summary.get("CandidateSha256") or "").upper() != str(manifest.get("exe_sha256") or "").upper():
        failures.append("right-bottom compose UI candidate SHA does not match patch manifest")
    if int(marker_counts.get("SURFDUMP_PLAYGAME") or 0) <= 0:
        failures.append("right-bottom compose UI run did not reach SURFDUMP_PLAYGAME")
    if int(marker_counts.get("SURFDUMP_READY") or 0) <= 0:
        failures.append("right-bottom compose UI run did not reach SURFDUMP_READY")
    # RBUI_VIEWPORT_SWITCH is asserted UNCONDITIONALLY, on both the natural-rows and the
    # fixture path. The compose patch's dynamic viewport switch does not depend on the
    # owner/action draw rows being entered: it is emitted on the bare map and is satisfied
    # there, so there is no justification for relaxing it on the fixture path.
    if int(marker_counts.get("RBUI_VIEWPORT_SWITCH") or 0) <= 0:
        failures.append("right-bottom compose UI viewport switch row was not observed")

    rbui_desc_switch_asserted = natural_rows_present
    rbui_desc_switch_unasserted_reason: str | None = None
    if natural_rows_present:
        # Original natural-rows path: unchanged requirement when the bare-map run
        # itself enters the owner/action draw rows.
        if int(marker_counts.get("RBUI_DESC_SWITCH") or 0) <= 0:
            failures.append("right-bottom compose UI descriptor switch rows were not observed")
    else:
        # RBUI_DESC_SWITCH is deliberately NOT asserted here, and that omission is
        # disclosed in the emitted payload, the generated markdown, and the guard
        # policy text rather than left silent -- see RBUI_DESC_SWITCH_UNASSERTED_REASON.
        rbui_desc_switch_unasserted_reason = RBUI_DESC_SWITCH_UNASSERTED_REASON
        # Rows absent on the bare map is the physically-correct engine result: the
        # unmodified slot-0 save's only player-owned record has owner_flag=0x00, which
        # parks descriptor 004338E0 off-screen, and the widget poll 00419DC0 never
        # fires headlessly. Per the ruling
        # (user ruling 2026-07-14: slot5-as-slot0 fixture accepted as natural-draw evidence)
        # the accepted fixture run supplies the natural-draw proof; fail closed if it
        # is missing or incomplete.
        fixture_payload, fixture_failures = evaluate_right_bottom_fixture_natural_draw(
            args.right_bottom_compose_ui_fixture_run
        )
        failures.extend(fixture_failures)
    if av_count:
        failures.append("right-bottom compose UI AV rows were observed")
    if not current_gate.get("passed"):
        failures.append("right-bottom compose UI patch manifest did not pass the current HD map gate")
    if int(patch_group.get("patched") or 0) != 4 or int(patch_group.get("total") or 0) != 4:
        failures.append("right-bottom compose UI patch group is not fully patched")

    return {
        "passed": not failures,
        "run": str(run),
        "summary_json": str(summary_path),
        "surface_summary_json": str(surface_summary_path),
        "bounds_json": str(bounds_path),
        "manifest": str(manifest_path),
        "screenshot": canonical_capture_path(summary.get("PngPath")),
        "summary": {
            "surface_dump_passed": summary.get("SurfaceDumpPassed"),
            "hidden_desktop": surface_summary.get("HiddenDesktop"),
            "map_validation_skipped": surface_summary.get("SkipMapValidation"),
            "no_skip_start_anims": surface_summary.get("NoSkipStartAnims"),
            "stage": summary.get("Stage"),
            "candidate_sha256": summary.get("CandidateSha256"),
            "rbui_markers_seen": summary.get("RbuiMarkersSeen"),
            "rbui_desc_switch": marker_counts.get("RBUI_DESC_SWITCH"),
            "rbui_desc_switch_asserted": rbui_desc_switch_asserted,
            "rbui_desc_switch_unasserted_reason": rbui_desc_switch_unasserted_reason,
            "rbui_viewport_switch": marker_counts.get("RBUI_VIEWPORT_SWITCH"),
            "rbui_viewport_switch_asserted": True,
            "rbui_panel_draw": marker_counts.get("RBUI_PANEL_DRAW"),
            "rbui_action_box": marker_counts.get("RBUI_ACTION_BOX"),
            "surfdump_playgame": marker_counts.get("SURFDUMP_PLAYGAME"),
            "surfdump_ready": marker_counts.get("SURFDUMP_READY"),
            "av_count": av_count,
            "current_hd_map_gate": current_gate.get("passed"),
            "right_bottom_patch_group": patch_group,
            "natural_draw_source": natural_draw_source,
            "guard_policy": (
                RIGHT_BOTTOM_COMPOSE_UI_GUARD_POLICY_NATURAL
                if natural_rows_present
                else RIGHT_BOTTOM_COMPOSE_UI_GUARD_POLICY_FIXTURE
            ),
            "fixture": fixture_payload,
            "bounds": bounds_summary,
        },
        "failures": failures,
    }


def build_right_bottom_owner_route(args: argparse.Namespace) -> dict[str, Any]:
    run = args.right_bottom_owner_route_run
    summary_path = run / "summary.json"
    log = run / "cdb-surface-dump.log"
    route_json = run / "action-panel-route-summary.json"
    route_md = run / "action-panel-route-summary.md"
    composition_json = run / "action-box-composition-summary.json"
    composition_md = run / "action-box-composition-summary.md"
    bounds_path = run / "right-bottom-ui-bounds.json"
    failures: list[str] = []

    if not summary_path.exists():
        return {
            "passed": False,
            "run": str(run),
            "summary_json": str(summary_path),
            "failures": [f"missing right-bottom owner-route summary: {summary_path}"],
        }
    if not log.exists():
        return {
            "passed": False,
            "run": str(run),
            "log": str(log),
            "failures": [f"missing right-bottom owner-route log: {log}"],
        }

    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    route = action_panel_route_summary.parse_log(log)
    write_json(route_json, route)
    action_panel_route_summary.write_markdown(route_md, route)
    marker_counts = route.get("marker_counts") or {}
    png_path = Path(summary.get("PngPath") or run / "surface.png")
    composition = border_tooltip_summary.summarize(
        log,
        png_path if png_path.exists() else None,
        argparse.Namespace(logical_width=800, logical_height=600, threshold=12),
    )
    write_json(composition_json, composition)
    border_tooltip_summary.write_markdown(composition, composition_md)
    composition_counts = composition.get("row_counts") or {}
    composition_markers = composition.get("marker_counts") or {}

    if not summary.get("Passed"):
        failures.append("right-bottom owner-route surface dump did not pass")
    if not summary.get("HiddenDesktop"):
        failures.append("right-bottom owner-route run was not hidden-desktop")
    if not summary.get("SkipMapValidation"):
        failures.append("right-bottom owner-route run did not skip map validation")
    if not probe_template_matches(
        summary.get("ExtraProbeTemplate"),
        "probes/cdb/map/clash95_post_owner_action_extra.cdb",
    ):
        failures.append("right-bottom owner-route extra probe template was not recorded")
    if not route.get("ready"):
        failures.append("right-bottom owner-route did not reach SURFDUMP_READY")
    if route.get("av_count"):
        failures.append("right-bottom owner-route AV rows were observed")
    if not route.get("owner_rows"):
        failures.append("right-bottom owner-route owner/global rows were not observed")
    if not route.get("draw_rows"):
        failures.append("right-bottom owner-route draw rows were not observed")
    if not route.get("nonzero_owner_rows"):
        failures.append("right-bottom owner-route nonzero owner rows were not observed")
    for marker in (
        "APPOST_OWNER_SETUP_CALL",
        "APPOST_ACTION_CALL",
        "APPOST_PANEL_DRAW_4347A0",
        "APPOST_GRID_DRAW_434E20",
        "APPOST_STATUS_DRAW_435280",
        "APREDIR_AFTER_ACTION_BOX",
        "APREDIR_COPYBACK_AFTER_CALL",
        "APPOST_SURFDUMP_READY",
        "SURFDUMP_HOST_READY",
    ):
        if int(marker_counts.get(marker) or 0) <= 0:
            failures.append(f"right-bottom owner-route marker missing: {marker}")
    if (
        int(marker_counts.get("APPOST_ACTION_BOX_435500") or 0) <= 0
        and int(composition_markers.get("TOOLTIP_ACTION_BOX") or 0) <= 0
    ):
        failures.append("right-bottom owner-route marker missing: APPOST_ACTION_BOX_435500/TOOLTIP_ACTION_BOX")
    for marker in (
        "TOOLTIP_ACTION_BOX",
        "TOOLTIP_TEXTFMT",
        "APCOMP_ACTION_BOX_ENTRY",
        "APCOMP_COPYBACK_SAMPLES",
    ):
        if int(composition_markers.get(marker) or 0) <= 0:
            failures.append(f"right-bottom action-box composition marker missing: {marker}")
    if int(composition_counts.get("text") or 0) <= 0:
        failures.append("right-bottom action-box composition text rows were not observed")
    if int(composition_counts.get("samples") or 0) <= 0:
        failures.append("right-bottom action-box composition sample rows were not observed")
    if composition.get("av_rows"):
        failures.append("right-bottom action-box composition AV rows were observed")

    bounds_summary: dict[str, Any] | None = None
    if bounds_path.exists():
        bounds = json.loads(bounds_path.read_text(encoding="utf-8-sig"))
        images = bounds.get("images") or []
        regions = images[0].get("regions") if images else []
        bounds_summary = {
            region.get("name"): {
                "nonblack_percent": region.get("nonblack_percent"),
                "black_percent": region.get("black_percent"),
                "flags": region.get("flags"),
            }
            for region in regions
            if region.get("name")
        }

    return {
        "passed": not failures,
        "run": str(run),
        "summary_json": str(summary_path),
        "route_json": str(route_json),
        "route_markdown": str(route_md),
        "composition_json": str(composition_json),
        "composition_markdown": str(composition_md),
        "bounds_json": str(bounds_path) if bounds_path.exists() else None,
        "screenshot": canonical_capture_path(summary.get("PngPath")),
        "summary": {
            "surface_dump_passed": summary.get("Passed"),
            "hidden_desktop": summary.get("HiddenDesktop"),
            "map_validation_skipped": summary.get("SkipMapValidation"),
            "candidate_sha256": summary.get("CandidateSha256"),
            "ready": route.get("ready"),
            "av_count": route.get("av_count"),
            "owner_rows": len(route.get("owner_rows") or []),
            "panel_rows": len(route.get("panel_rows") or []),
            "draw_rows": len(route.get("draw_rows") or []),
            "nonzero_owner_rows": len(route.get("nonzero_owner_rows") or []),
            "appost_action_box": marker_counts.get("APPOST_ACTION_BOX_435500"),
            "tooltip_action_box": composition_markers.get("TOOLTIP_ACTION_BOX"),
            "apredir_after_action_box": marker_counts.get("APREDIR_AFTER_ACTION_BOX"),
            "apredir_copyback_after_call": marker_counts.get("APREDIR_COPYBACK_AFTER_CALL"),
            "composition_text_rows": composition_counts.get("text"),
            "composition_present_rows": composition_counts.get("present"),
            "composition_present_null_rows": composition_counts.get("present_null"),
            "composition_sample_rows": composition_counts.get("samples"),
            "composition_present_by_region": composition.get("present_by_region"),
            "composition_present_null_by_region": composition.get("present_null_by_region"),
            "bounds": bounds_summary,
        },
        "failures": failures,
    }


def build_bounds_compare(baseline_png: Path, compose_png: Path, output: Path) -> dict[str, Any]:
    bounds_args = argparse.Namespace(
        logical_width=800,
        logical_height=600,
        threshold=12,
        bright_threshold=96,
        mostly_black_percent=5.0,
        large_component_percent=20.0,
        black_component_min_area=128,
        max_black_components=5,
        require_region_min_nonblack=[],
    )
    regions = list(right_bottom_ui_bounds.DEFAULT_REGIONS.items())
    report = {
        "parameters": {
            "logical_width": bounds_args.logical_width,
            "logical_height": bounds_args.logical_height,
            "threshold": bounds_args.threshold,
            "bright_threshold": bounds_args.bright_threshold,
            "mostly_black_percent": bounds_args.mostly_black_percent,
            "large_component_percent": bounds_args.large_component_percent,
            "black_component_min_area": bounds_args.black_component_min_area,
            "max_black_components": bounds_args.max_black_components,
            "require_region_min_nonblack": [],
        },
        "regions": [{"name": name, "logical_rect": list(rect)} for name, rect in regions],
        "images": [
            right_bottom_ui_bounds.analyze_image(baseline_png, regions, bounds_args),
            right_bottom_ui_bounds.analyze_image(compose_png, regions, bounds_args),
        ],
    }
    write_json(output, report)
    return report


def region_summary(image: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        region.get("name"): {
            "nonblack_percent": region.get("nonblack_percent"),
            "black_percent": region.get("black_percent"),
            "flags": region.get("flags"),
        }
        for region in image.get("regions", [])
        if region.get("name")
    }


def build_right_bottom_compose_probe(args: argparse.Namespace) -> dict[str, Any]:
    baseline_run = args.right_bottom_compose_baseline_run
    run = args.right_bottom_compose_run
    summary_path = run / "summary.json"
    log = run / "cdb-surface-dump.log"
    route_json = run / "action-panel-route-summary.json"
    route_md = run / "action-panel-route-summary.md"
    composition_json = run / "action-box-compose-summary.json"
    composition_md = run / "action-box-compose-summary.md"
    bounds_json = run / "right-bottom-ui-bounds-compare.json"
    baseline_png = baseline_run / "surface.png"
    compose_png = run / "surface.png"
    failures: list[str] = []

    for label, path in (
        ("right-bottom compose summary", summary_path),
        ("right-bottom compose log", log),
        ("right-bottom compose baseline PNG", baseline_png),
        ("right-bottom compose PNG", compose_png),
    ):
        if not path.exists():
            return {
                "passed": False,
                "run": str(run),
                "baseline_run": str(baseline_run),
                "failures": [f"missing {label}: {path}"],
            }

    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    route = action_panel_route_summary.parse_log(log)
    write_json(route_json, route)
    action_panel_route_summary.write_markdown(route_md, route)
    composition = border_tooltip_summary.summarize(
        log,
        compose_png,
        argparse.Namespace(logical_width=800, logical_height=600, threshold=12),
    )
    write_json(composition_json, composition)
    border_tooltip_summary.write_markdown(composition, composition_md)
    bounds = build_bounds_compare(baseline_png, compose_png, bounds_json)
    baseline_regions = region_summary(bounds["images"][0])
    compose_regions = region_summary(bounds["images"][1])
    deltas = {
        name: round(
            float(compose_regions.get(name, {}).get("nonblack_percent") or 0.0)
            - float(baseline_regions.get(name, {}).get("nonblack_percent") or 0.0),
            3,
        )
        for name in compose_regions
    }

    marker_counts = route.get("marker_counts") or {}
    composition_counts = composition.get("row_counts") or {}
    composition_markers = composition.get("marker_counts") or {}

    if not summary.get("Passed"):
        failures.append("right-bottom compose surface dump did not pass")
    if not summary.get("HiddenDesktop"):
        failures.append("right-bottom compose run was not hidden-desktop")
    if not summary.get("SkipMapValidation"):
        failures.append("right-bottom compose run did not skip map validation")
    if not probe_template_matches(
        summary.get("ExtraProbeTemplate"),
        "probes/cdb/map/clash95_post_owner_action_compose_extra.cdb",
    ):
        failures.append("right-bottom compose extra probe template was not recorded")
    if not route.get("ready"):
        failures.append("right-bottom compose route did not reach SURFDUMP_READY")
    if route.get("av_count"):
        failures.append("right-bottom compose AV rows were observed")
    for marker in (
        "APPOST_OWNER_SETUP_CALL",
        "APPOST_ACTION_CALL",
        "APPOST_STATUS_DRAW_435280",
        "APPOST_ACTION_BOX_435500",
        "APREDIR_COPYBACK_AFTER_CALL",
        "APPOST_SURFDUMP_READY",
    ):
        if int(marker_counts.get(marker) or 0) <= 0:
            failures.append(f"right-bottom compose route marker missing: {marker}")
    for marker in (
        "APCOMPOSE_STATUS_SHIFT_CALL",
        "APCOMPOSE_STATUS_SHIFT_DONE",
        "APCOMPOSE_ACTION_SHIFT_CALL",
        "APCOMPOSE_ACTION_SHIFT_DONE",
    ):
        if int(composition_markers.get(marker) or 0) <= 0:
            failures.append(f"right-bottom compose marker missing: {marker}")
    if int(composition_counts.get("samples") or 0) < 4:
        failures.append("right-bottom compose sample rows were incomplete")
    if composition.get("av_rows"):
        failures.append("right-bottom compose composition AV rows were observed")

    if deltas.get("bottom_right_ui_corner", 0.0) < 20.0:
        failures.append("right-bottom compose did not improve bottom_right_ui_corner by at least 20% nonblack")
    if float(compose_regions.get("bottom_right_tile_r8c10", {}).get("nonblack_percent") or 0.0) < 40.0:
        failures.append("right-bottom compose did not recover r8c10 to at least 40% nonblack")
    if float(compose_regions.get("bottom_right_tile_r8c11", {}).get("nonblack_percent") or 0.0) < 40.0:
        failures.append("right-bottom compose did not recover r8c11 to at least 40% nonblack")

    return {
        "passed": not failures,
        "run": str(run),
        "baseline_run": str(baseline_run),
        "summary_json": str(summary_path),
        "route_json": str(route_json),
        "route_markdown": str(route_md),
        "composition_json": str(composition_json),
        "composition_markdown": str(composition_md),
        "bounds_json": str(bounds_json),
        "screenshot": canonical_capture_path(summary.get("PngPath")),
        "summary": {
            "surface_dump_passed": summary.get("Passed"),
            "hidden_desktop": summary.get("HiddenDesktop"),
            "map_validation_skipped": summary.get("SkipMapValidation"),
            "candidate_sha256": summary.get("CandidateSha256"),
            "ready": route.get("ready"),
            "av_count": route.get("av_count"),
            "owner_rows": len(route.get("owner_rows") or []),
            "draw_rows": len(route.get("draw_rows") or []),
            "apcompose_status_call": composition_markers.get("APCOMPOSE_STATUS_SHIFT_CALL"),
            "apcompose_status_done": composition_markers.get("APCOMPOSE_STATUS_SHIFT_DONE"),
            "apcompose_action_call": composition_markers.get("APCOMPOSE_ACTION_SHIFT_CALL"),
            "apcompose_action_done": composition_markers.get("APCOMPOSE_ACTION_SHIFT_DONE"),
            "composition_sample_rows": composition_counts.get("samples"),
            "bottom_right_ui_corner_nonblack": compose_regions.get("bottom_right_ui_corner", {}).get("nonblack_percent"),
            "bottom_right_ui_corner_delta": deltas.get("bottom_right_ui_corner"),
            "bottom_right_tile_r8c10_nonblack": compose_regions.get("bottom_right_tile_r8c10", {}).get("nonblack_percent"),
            "bottom_right_tile_r8c10_delta": deltas.get("bottom_right_tile_r8c10"),
            "bottom_right_tile_r8c11_nonblack": compose_regions.get("bottom_right_tile_r8c11", {}).get("nonblack_percent"),
            "bottom_right_tile_r8c11_delta": deltas.get("bottom_right_tile_r8c11"),
            "bottom_strip_delta": deltas.get("bottom_strip"),
        },
        "failures": failures,
    }


def build_right_bottom_compose_patch(args: argparse.Namespace) -> dict[str, Any]:
    baseline_run = args.right_bottom_compose_baseline_run
    run = args.right_bottom_compose_patch_run
    manifest_path = args.right_bottom_compose_patch_manifest
    summary_path = run / "summary.json"
    log = run / "cdb-surface-dump.log"
    route_json = run / "action-panel-route-patch-summary.json"
    route_md = run / "action-panel-route-patch-summary.md"
    composition_json = run / "action-box-compose-patch-summary.json"
    composition_md = run / "action-box-compose-patch-summary.md"
    bounds_json = run / "right-bottom-compose-patch-bounds-compare.json"
    baseline_png = baseline_run / "surface.png"
    patch_png = run / "surface.png"
    failures: list[str] = []

    for label, path in (
        ("right-bottom compose patch summary", summary_path),
        ("right-bottom compose patch log", log),
        ("right-bottom compose patch manifest", manifest_path),
        ("right-bottom compose patch baseline PNG", baseline_png),
        ("right-bottom compose patch PNG", patch_png),
    ):
        if not path.exists():
            return {
                "passed": False,
                "run": str(run),
                "baseline_run": str(baseline_run),
                "manifest": str(manifest_path),
                "failures": [f"missing {label}: {path}"],
            }

    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    route = action_panel_route_summary.parse_log(log)
    write_json(route_json, route)
    action_panel_route_summary.write_markdown(route_md, route)
    composition = border_tooltip_summary.summarize(
        log,
        patch_png,
        argparse.Namespace(logical_width=800, logical_height=600, threshold=12),
    )
    write_json(composition_json, composition)
    border_tooltip_summary.write_markdown(composition, composition_md)
    bounds = build_bounds_compare(baseline_png, patch_png, bounds_json)
    baseline_regions = region_summary(bounds["images"][0])
    patch_regions = region_summary(bounds["images"][1])
    deltas = {
        name: round(
            float(patch_regions.get(name, {}).get("nonblack_percent") or 0.0)
            - float(baseline_regions.get(name, {}).get("nonblack_percent") or 0.0),
            3,
        )
        for name in patch_regions
    }

    marker_counts = route.get("marker_counts") or {}
    composition_counts = composition.get("row_counts") or {}
    patch_group = (manifest.get("groups") or {}).get("right-bottom-compose-proof") or {}
    status_counts = manifest.get("status_counts") or {}
    current_gate = manifest.get("current_hd_map_gate") or {}

    if not summary.get("Passed"):
        failures.append("right-bottom compose patch surface dump did not pass")
    if not summary.get("HiddenDesktop"):
        failures.append("right-bottom compose patch run was not hidden-desktop")
    if not summary.get("SkipMapValidation"):
        failures.append("right-bottom compose patch run did not skip map validation")
    if not summary.get("UseDdrawProxy"):
        failures.append("right-bottom compose patch run did not use the DirectDraw proxy")
    if not summary.get("FastForwardStartAnims"):
        failures.append("right-bottom compose patch run did not use fast-forward startup")
    if summary.get("Stage") != RIGHT_BOTTOM_COMPOSE_PATCH_STAGE:
        failures.append("right-bottom compose patch stage mismatch")
    if not probe_template_matches(
        summary.get("ExtraProbeTemplate"),
        "probes/cdb/map/clash95_post_owner_action_extra.cdb",
    ):
        failures.append("right-bottom compose patch extra probe template was not recorded")
    if str(summary.get("CandidateSha256") or "").upper() != str(manifest.get("exe_sha256") or "").upper():
        failures.append("right-bottom compose patch manifest SHA does not match run candidate")
    if manifest.get("stage") != RIGHT_BOTTOM_COMPOSE_PATCH_STAGE:
        failures.append("right-bottom compose patch manifest stage mismatch")
    if not current_gate.get("passed"):
        failures.append("right-bottom compose patch manifest did not pass the current HD map gate")
    if int(status_counts.get("original") or 0) != 0 or int(status_counts.get("unexpected") or 0) != 0:
        failures.append("right-bottom compose patch manifest has original/unexpected selected bytes")
    if int(patch_group.get("patched") or 0) != 4 or int(patch_group.get("total") or 0) != 4:
        failures.append("right-bottom compose patch group is not fully patched")
    if not route.get("ready"):
        failures.append("right-bottom compose patch route did not reach SURFDUMP_READY")
    if route.get("av_count"):
        failures.append("right-bottom compose patch AV rows were observed")
    for marker in (
        "APPOST_OWNER_SETUP_CALL",
        "APPOST_ACTION_CALL",
        "APPOST_STATUS_DRAW_435280",
        "APPOST_ACTION_BOX_435500",
        "APREDIR_COPYBACK_AFTER_CALL",
        "APPOST_SURFDUMP_READY",
    ):
        if int(marker_counts.get(marker) or 0) <= 0:
            failures.append(f"right-bottom compose patch route marker missing: {marker}")
    if composition.get("av_rows"):
        failures.append("right-bottom compose patch composition AV rows were observed")
    if int(composition_counts.get("text") or 0) < 10:
        failures.append("right-bottom compose patch text rows were incomplete")
    if deltas.get("bottom_right_ui_corner", 0.0) < 20.0:
        failures.append("right-bottom compose patch did not improve bottom_right_ui_corner by at least 20% nonblack")
    if float(patch_regions.get("bottom_right_tile_r8c10", {}).get("nonblack_percent") or 0.0) < 40.0:
        failures.append("right-bottom compose patch did not recover r8c10 to at least 40% nonblack")
    if float(patch_regions.get("bottom_right_tile_r8c11", {}).get("nonblack_percent") or 0.0) < 40.0:
        failures.append("right-bottom compose patch did not recover r8c11 to at least 40% nonblack")

    return {
        "passed": not failures,
        "run": str(run),
        "baseline_run": str(baseline_run),
        "manifest": str(manifest_path),
        "summary_json": str(summary_path),
        "route_json": str(route_json),
        "route_markdown": str(route_md),
        "composition_json": str(composition_json),
        "composition_markdown": str(composition_md),
        "bounds_json": str(bounds_json),
        "screenshot": canonical_capture_path(summary.get("PngPath")),
        "summary": {
            "surface_dump_passed": summary.get("Passed"),
            "hidden_desktop": summary.get("HiddenDesktop"),
            "map_validation_skipped": summary.get("SkipMapValidation"),
            "stage": summary.get("Stage"),
            "candidate_sha256": summary.get("CandidateSha256"),
            "manifest_patched": status_counts.get("patched"),
            "right_bottom_patch_group": patch_group,
            "current_hd_map_gate": current_gate.get("passed"),
            "ready": route.get("ready"),
            "av_count": route.get("av_count"),
            "owner_rows": len(route.get("owner_rows") or []),
            "draw_rows": len(route.get("draw_rows") or []),
            "composition_text_rows": composition_counts.get("text"),
            "composition_present_rows": composition_counts.get("present"),
            "composition_present_null_rows": composition_counts.get("present_null"),
            "bottom_right_ui_corner_nonblack": patch_regions.get("bottom_right_ui_corner", {}).get("nonblack_percent"),
            "bottom_right_ui_corner_delta": deltas.get("bottom_right_ui_corner"),
            "bottom_right_tile_r8c10_nonblack": patch_regions.get("bottom_right_tile_r8c10", {}).get("nonblack_percent"),
            "bottom_right_tile_r8c10_delta": deltas.get("bottom_right_tile_r8c10"),
            "bottom_right_tile_r8c11_nonblack": patch_regions.get("bottom_right_tile_r8c11", {}).get("nonblack_percent"),
            "bottom_right_tile_r8c11_delta": deltas.get("bottom_right_tile_r8c11"),
            "bottom_strip_delta": deltas.get("bottom_strip"),
        },
        "failures": failures,
    }


def build_right_bottom_compose_fullstart_route(args: argparse.Namespace) -> dict[str, Any]:
    baseline_run = args.right_bottom_compose_baseline_run
    run = args.right_bottom_compose_fullstart_run
    manifest_path = args.right_bottom_compose_patch_manifest
    summary_path = run / "summary.json"
    log = run / "cdb-surface-dump.log"
    route_json = run / "action-panel-route-fullstart-summary.json"
    route_md = run / "action-panel-route-fullstart-summary.md"
    composition_json = run / "action-box-compose-fullstart-summary.json"
    composition_md = run / "action-box-compose-fullstart-summary.md"
    bounds_json = run / "right-bottom-compose-fullstart-bounds-compare.json"
    baseline_png = baseline_run / "surface.png"
    patch_png = run / "surface.png"
    failures: list[str] = []

    for label, path in (
        ("right-bottom compose full-start summary", summary_path),
        ("right-bottom compose full-start log", log),
        ("right-bottom compose full-start patch manifest", manifest_path),
        ("right-bottom compose full-start baseline PNG", baseline_png),
        ("right-bottom compose full-start PNG", patch_png),
    ):
        if not path.exists():
            return {
                "passed": False,
                "run": str(run),
                "baseline_run": str(baseline_run),
                "manifest": str(manifest_path),
                "failures": [f"missing {label}: {path}"],
            }

    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    route = action_panel_route_summary.parse_log(log)
    write_json(route_json, route)
    action_panel_route_summary.write_markdown(route_md, route)
    composition = border_tooltip_summary.summarize(
        log,
        patch_png,
        argparse.Namespace(logical_width=800, logical_height=600, threshold=12),
    )
    write_json(composition_json, composition)
    border_tooltip_summary.write_markdown(composition, composition_md)
    bounds = build_bounds_compare(baseline_png, patch_png, bounds_json)
    baseline_regions = region_summary(bounds["images"][0])
    patch_regions = region_summary(bounds["images"][1])
    deltas = {
        name: round(
            float(patch_regions.get(name, {}).get("nonblack_percent") or 0.0)
            - float(baseline_regions.get(name, {}).get("nonblack_percent") or 0.0),
            3,
        )
        for name in patch_regions
    }

    marker_counts = route.get("marker_counts") or {}
    composition_counts = composition.get("row_counts") or {}
    patch_group = (manifest.get("groups") or {}).get("right-bottom-compose-proof") or {}
    status_counts = manifest.get("status_counts") or {}
    current_gate = manifest.get("current_hd_map_gate") or {}

    if not summary.get("Passed"):
        failures.append("right-bottom compose full-start surface dump did not pass")
    if not summary.get("HiddenDesktop"):
        failures.append("right-bottom compose full-start run was not hidden-desktop")
    if not summary.get("SkipMapValidation"):
        failures.append("right-bottom compose full-start run did not skip map validation")
    if not summary.get("UseDdrawProxy"):
        failures.append("right-bottom compose full-start run did not use the DirectDraw proxy")
    if not summary.get("NoSkipStartAnims"):
        failures.append("right-bottom compose full-start run did not use full startup animation path")
    if summary.get("FastForwardStartAnims"):
        failures.append("right-bottom compose full-start run unexpectedly fast-forwarded startup")
    if summary.get("Stage") != RIGHT_BOTTOM_COMPOSE_PATCH_STAGE:
        failures.append("right-bottom compose full-start stage mismatch")
    if not probe_template_matches(
        summary.get("ExtraProbeTemplate"),
        "probes/cdb/map/clash95_post_owner_action_extra.cdb",
    ):
        failures.append("right-bottom compose full-start extra probe template was not recorded")
    if str(summary.get("CandidateSha256") or "").upper() != str(manifest.get("exe_sha256") or "").upper():
        failures.append("right-bottom compose full-start manifest SHA does not match run candidate")
    if manifest.get("stage") != RIGHT_BOTTOM_COMPOSE_PATCH_STAGE:
        failures.append("right-bottom compose full-start manifest stage mismatch")
    if not current_gate.get("passed"):
        failures.append("right-bottom compose full-start manifest did not pass the current HD map gate")
    if int(status_counts.get("original") or 0) != 0 or int(status_counts.get("unexpected") or 0) != 0:
        failures.append("right-bottom compose full-start manifest has original/unexpected selected bytes")
    if int(patch_group.get("patched") or 0) != 4 or int(patch_group.get("total") or 0) != 4:
        failures.append("right-bottom compose full-start patch group is not fully patched")
    if not route.get("ready"):
        failures.append("right-bottom compose full-start route did not reach SURFDUMP_READY")
    if route.get("av_count"):
        failures.append("right-bottom compose full-start AV rows were observed")
    for marker in (
        "APPOST_OWNER_SETUP_CALL",
        "APPOST_ACTION_CALL",
        "APPOST_STATUS_DRAW_435280",
        "APPOST_ACTION_BOX_435500",
        "APREDIR_COPYBACK_AFTER_CALL",
        "APPOST_SURFDUMP_READY",
    ):
        if int(marker_counts.get(marker) or 0) <= 0:
            failures.append(f"right-bottom compose full-start route marker missing: {marker}")
    if composition.get("av_rows"):
        failures.append("right-bottom compose full-start composition AV rows were observed")
    if int(composition_counts.get("text") or 0) < 10:
        failures.append("right-bottom compose full-start text rows were incomplete")
    if deltas.get("bottom_right_ui_corner", 0.0) < 20.0:
        failures.append("right-bottom compose full-start did not improve bottom_right_ui_corner by at least 20% nonblack")
    if float(patch_regions.get("bottom_right_tile_r8c10", {}).get("nonblack_percent") or 0.0) < 40.0:
        failures.append("right-bottom compose full-start did not recover r8c10 to at least 40% nonblack")
    if float(patch_regions.get("bottom_right_tile_r8c11", {}).get("nonblack_percent") or 0.0) < 40.0:
        failures.append("right-bottom compose full-start did not recover r8c11 to at least 40% nonblack")

    return {
        "passed": not failures,
        "run": str(run),
        "baseline_run": str(baseline_run),
        "manifest": str(manifest_path),
        "summary_json": str(summary_path),
        "route_json": str(route_json),
        "route_markdown": str(route_md),
        "composition_json": str(composition_json),
        "composition_markdown": str(composition_md),
        "bounds_json": str(bounds_json),
        "screenshot": canonical_capture_path(summary.get("PngPath")),
        "summary": {
            "surface_dump_passed": summary.get("Passed"),
            "hidden_desktop": summary.get("HiddenDesktop"),
            "map_validation_skipped": summary.get("SkipMapValidation"),
            "no_skip_start_anims": summary.get("NoSkipStartAnims"),
            "fast_forward_start_anims": summary.get("FastForwardStartAnims"),
            "stage": summary.get("Stage"),
            "candidate_sha256": summary.get("CandidateSha256"),
            "manifest_patched": status_counts.get("patched"),
            "right_bottom_patch_group": patch_group,
            "current_hd_map_gate": current_gate.get("passed"),
            "ready": route.get("ready"),
            "av_count": route.get("av_count"),
            "owner_rows": len(route.get("owner_rows") or []),
            "draw_rows": len(route.get("draw_rows") or []),
            "composition_text_rows": composition_counts.get("text"),
            "composition_present_rows": composition_counts.get("present"),
            "composition_present_null_rows": composition_counts.get("present_null"),
            "bottom_right_ui_corner_nonblack": patch_regions.get("bottom_right_ui_corner", {}).get("nonblack_percent"),
            "bottom_right_ui_corner_delta": deltas.get("bottom_right_ui_corner"),
            "bottom_right_tile_r8c10_nonblack": patch_regions.get("bottom_right_tile_r8c10", {}).get("nonblack_percent"),
            "bottom_right_tile_r8c10_delta": deltas.get("bottom_right_tile_r8c10"),
            "bottom_right_tile_r8c11_nonblack": patch_regions.get("bottom_right_tile_r8c11", {}).get("nonblack_percent"),
            "bottom_right_tile_r8c11_delta": deltas.get("bottom_right_tile_r8c11"),
            "bottom_strip_delta": deltas.get("bottom_strip"),
        },
        "failures": failures,
    }


def build_right_bottom_compose_normal_gate(args: argparse.Namespace) -> dict[str, Any]:
    run = args.right_bottom_compose_normal_run
    manifest_path = args.right_bottom_compose_patch_manifest
    summary_path = run / "summary.json"
    coverage_path = run / "map-tile-coverage.json"
    visibility_path = run / "visibility-coverage-summary.json"
    failures: list[str] = []

    for label, path in (
        ("right-bottom compose normal summary", summary_path),
        ("right-bottom compose normal coverage", coverage_path),
        ("right-bottom compose normal visibility", visibility_path),
        ("right-bottom compose patch manifest", manifest_path),
    ):
        if not path.exists():
            return {
                "passed": False,
                "run": str(run),
                "manifest": str(manifest_path),
                "failures": [f"missing {label}: {path}"],
            }

    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    coverage = json.loads(coverage_path.read_text(encoding="utf-8-sig"))
    visibility = json.loads(visibility_path.read_text(encoding="utf-8-sig"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))

    surface = summary.get("Surface") or {}
    coverage_image = ((coverage.get("images") or [{}])[0]) or {}
    coverage_summary = coverage_image.get("summary") or {}
    frame_check = coverage_image.get("frame_check") or {}
    blank_cells = summary.get("CoverageBlankActiveCells") or []
    status_counts = visibility.get("status_counts") or {}
    unexplained = visibility.get("unexplained_blank_cells") or []
    patch_group = (manifest.get("groups") or {}).get("right-bottom-compose-proof") or {}
    current_gate = manifest.get("current_hd_map_gate") or {}

    if not summary.get("Passed"):
        failures.append("right-bottom compose normal surface dump did not pass")
    if not summary.get("HiddenDesktop"):
        failures.append("right-bottom compose normal run was not hidden-desktop")
    if not summary.get("UseDdrawProxy"):
        failures.append("right-bottom compose normal run did not use the DirectDraw proxy")
    if not summary.get("NoSkipStartAnims"):
        failures.append("right-bottom compose normal run did not use full startup animation path")
    if summary.get("FastForwardStartAnims"):
        failures.append("right-bottom compose normal run unexpectedly fast-forwarded startup")
    if summary.get("SkipMapValidation"):
        failures.append("right-bottom compose normal run skipped map validation")
    if summary.get("Stage") != RIGHT_BOTTOM_COMPOSE_PATCH_STAGE:
        failures.append("right-bottom compose normal stage mismatch")
    if str(summary.get("CandidateSha256") or "").upper() != str(manifest.get("exe_sha256") or "").upper():
        failures.append("right-bottom compose normal candidate SHA does not match patch manifest")
    if int(surface.get("Width") or 0) != 800 or int(surface.get("Height") or 0) != 600:
        failures.append("right-bottom compose normal surface was not 800x600")
    if not frame_check.get("gameplay_frame_likely"):
        failures.append("right-bottom compose normal coverage is not gameplay-like")
    if int(coverage_summary.get("active_cells") or 0) != 108:
        failures.append("right-bottom compose normal coverage does not have 108 active cells")
    if summary.get("VisibilityRequireExplained") is not True:
        failures.append("right-bottom compose normal visibility explanation was not required")
    if not (summary.get("VisibilityExplainedGate") or {}).get("Passed"):
        failures.append("right-bottom compose normal visibility explanation gate did not pass")
    if unexplained:
        failures.append("right-bottom compose normal has unexplained blank cells")
    if int(status_counts.get("visibility_zero") or 0) != len(blank_cells):
        failures.append("right-bottom compose normal visibility_zero count does not match blank cells")
    if len(blank_cells) < 1:
        failures.append("right-bottom compose normal did not exercise any blank-cell visibility explanation")
    if not current_gate.get("passed"):
        failures.append("right-bottom compose normal patch manifest did not pass the current HD map gate")
    if int(patch_group.get("patched") or 0) != 4 or int(patch_group.get("total") or 0) != 4:
        failures.append("right-bottom compose normal patch group is not fully patched")

    return {
        "passed": not failures,
        "run": str(run),
        "manifest": str(manifest_path),
        "summary_json": str(summary_path),
        "coverage_json": str(coverage_path),
        "visibility_json": str(visibility_path),
        "screenshot": canonical_capture_path(summary.get("PngPath")),
        "summary": {
            "surface_dump_passed": summary.get("Passed"),
            "hidden_desktop": summary.get("HiddenDesktop"),
            "map_validation_skipped": summary.get("SkipMapValidation"),
            "no_skip_start_anims": summary.get("NoSkipStartAnims"),
            "fast_forward_start_anims": summary.get("FastForwardStartAnims"),
            "stage": summary.get("Stage"),
            "candidate_sha256": summary.get("CandidateSha256"),
            "surface": [surface.get("Width"), surface.get("Height")],
            "gameplay_frame_likely": frame_check.get("gameplay_frame_likely"),
            "active_cells": coverage_summary.get("active_cells"),
            "blank_active_cells": len(blank_cells),
            "visibility_require_explained": summary.get("VisibilityRequireExplained"),
            "visibility_explained_gate": (summary.get("VisibilityExplainedGate") or {}).get("Passed"),
            "visibility_unexplained_blank_cells": len(unexplained),
            "visibility_zero": status_counts.get("visibility_zero"),
            "current_hd_map_gate": current_gate.get("passed"),
            "right_bottom_patch_group": patch_group,
        },
        "failures": failures,
    }


def build_refresh(args: argparse.Namespace) -> dict[str, Any]:
    checks = {
        "hd_map_smoke": build_hd_map_smoke(args),
        "hd_layout_summary": build_hd_layout_summary(args),
        "hd_layout_summary_tests": build_hd_layout_summary_tests(args),
        "hd_layout_visible_summary": build_hd_layout_visible_summary(args),
        "hd_layout_visible_summary_tests": build_hd_layout_visible_summary_tests(args),
        "no_popup_map_evidence": build_no_popup_map_evidence(args),
        "no_popup_map_evidence_tests": build_no_popup_map_evidence_tests(args),
        "patch_manifest_compare": build_patch_compare(args),
        "barracks_success_branch": build_barracks_success(args),
        "right_bottom_ui_probe": build_right_bottom_ui(args),
        "right_bottom_owner_route": build_right_bottom_owner_route(args),
        "right_bottom_compose_probe": build_right_bottom_compose_probe(args),
        "right_bottom_compose_patch": build_right_bottom_compose_patch(args),
        "right_bottom_compose_fullstart_route": build_right_bottom_compose_fullstart_route(args),
        "right_bottom_compose_normal_gate": build_right_bottom_compose_normal_gate(args),
        "right_bottom_compose_ui_probe": build_right_bottom_compose_ui_probe(args),
        "right_bottom_grid_hit": build_right_bottom_grid_hit(args),
        "right_bottom_grid_hit_probe_guard": build_right_bottom_grid_hit_probe_guard(args),
        "right_bottom_natural_route_guard": build_right_bottom_natural_route_guard(args),
        "castle_save_owner_flag_scan": build_castle_save_owner_flag_scan(args),
        "right_bottom_natural_route_candidate_matrix": build_right_bottom_natural_route_candidate_matrix(args),
        "load_slot_route_limit_guard": build_load_slot_route_limit_guard(args),
        "right_bottom_slot_fixture_plan": build_right_bottom_slot_fixture_plan(args),
        "right_bottom_slot_fixture_script_guard": build_right_bottom_slot_fixture_script_guard(args),
        "right_bottom_slot_fixture_runtime_plan": build_right_bottom_slot_fixture_runtime_plan(args),
        "load_slot_timeout_phase": build_load_slot_timeout_phase(args),
        "load_slot_entry_gap": build_load_slot_entry_gap(args),
        "load_slot_transition_probe_guard": build_load_slot_transition_probe_guard(args),
        "load_slot_transition_run_plan": build_load_slot_transition_run_plan(args),
        "load_slot_transition_geometry_guard": build_load_slot_transition_geometry_guard(args),
        "load_slot_transition_probe_preview": build_load_slot_transition_probe_preview(args),
        "right_bottom_owner_flag_inventory": build_right_bottom_owner_flag_inventory(args),
        "right_bottom_route_timing_guard": build_right_bottom_route_timing_guard(args),
    }
    checks["right_bottom_compose_promotion_decision"] = build_right_bottom_compose_decision(
        args,
        checks,
    )
    checks["right_bottom_compose_evidence"] = build_right_bottom_compose_matrix(args, checks)
    checks["right_bottom_blocker_triage"] = build_right_bottom_blocker_triage(args)
    checks["right_bottom_visual_artifact_guard"] = build_right_bottom_visual_artifact_guard(args)
    checks["first_mission_visual_audit"] = build_first_mission_visual_audit(args)
    checks["right_bottom_compose_promotion_decision_tests"] = build_right_bottom_compose_decision_tests(args)
    checks["right_bottom_compose_evidence_matrix_tests"] = build_right_bottom_compose_matrix_tests(args)
    checks["right_bottom_blocker_triage_tests"] = build_right_bottom_blocker_triage_tests(args)
    checks["right_bottom_visual_artifact_guard_tests"] = build_right_bottom_visual_artifact_guard_tests(args)
    checks["first_mission_visual_audit_tests"] = build_first_mission_visual_audit_tests(args)
    checks["border_frame_restore_check"] = build_border_frame_restore_check(args)
    checks["border_frame_restore_check_tests"] = build_border_frame_restore_check_tests(args)
    checks["right_bottom_grid_hit_summary_tests"] = build_right_bottom_grid_hit_tests(args)
    checks["right_bottom_grid_hit_probe_guard_tests"] = build_right_bottom_grid_hit_probe_guard_tests(args)
    checks["right_bottom_natural_route_guard_tests"] = build_right_bottom_natural_route_guard_tests(args)
    checks["right_bottom_natural_route_candidate_matrix_tests"] = (
        build_right_bottom_natural_route_candidate_matrix_tests(args)
    )
    checks["right_bottom_natural_slot2_summary_tests"] = (
        build_right_bottom_natural_slot2_summary_tests(args)
    )
    checks["right_bottom_slot_fixture_plan_tests"] = build_right_bottom_slot_fixture_plan_tests(args)
    checks["right_bottom_slot_fixture_script_guard_tests"] = build_right_bottom_slot_fixture_script_guard_tests(args)
    checks["right_bottom_slot_fixture_runtime_plan_tests"] = build_right_bottom_slot_fixture_runtime_plan_tests(args)
    checks["right_bottom_slot_fixture_result_summary_tests"] = (
        build_right_bottom_slot_fixture_result_summary_tests(args)
    )
    checks["load_slot_route_limit_guard_tests"] = build_load_slot_route_limit_guard_tests(args)
    checks["load_slot_timeout_phase_tests"] = build_load_slot_timeout_phase_tests(args)
    checks["load_slot_entry_gap_tests"] = build_load_slot_entry_gap_tests(args)
    checks["load_slot_transition_probe_guard_tests"] = build_load_slot_transition_probe_guard_tests(args)
    checks["load_slot_transition_run_plan_tests"] = build_load_slot_transition_run_plan_tests(args)
    checks["load_slot_transition_geometry_guard_tests"] = build_load_slot_transition_geometry_guard_tests(args)
    checks["load_slot_transition_probe_preview_tests"] = build_load_slot_transition_probe_preview_tests(args)
    checks["load_slot_transition_summary_tests"] = build_load_slot_transition_summary_tests(args)
    checks["load_slot_transition_readiness"] = build_load_slot_transition_readiness(args)
    checks["load_slot_transition_readiness_tests"] = build_load_slot_transition_readiness_tests(args)
    checks["right_bottom_owner_flag_static_guard"] = build_right_bottom_owner_flag_static_guard(args)
    checks["right_bottom_owner_flag_static_guard_tests"] = build_right_bottom_owner_flag_static_guard_tests(args)
    checks["right_bottom_owner_flag_inventory_tests"] = build_right_bottom_owner_flag_inventory_tests(args)
    checks["right_bottom_route_timing_guard_tests"] = build_right_bottom_route_timing_guard_tests(args)
    checks["castle_overview_evidence"] = build_castle_matrix(args)
    checks["castle_owner_records_summary_tests"] = build_castle_owner_records_tests(args)
    checks["castle_save_owner_flag_scan_tests"] = build_castle_save_owner_flag_scan_tests(args)
    checks["castle_overview_evidence_matrix_tests"] = build_castle_matrix_tests(args)
    checks["castle_overview_gate_tests"] = build_castle_gate_tests(args)
    checks["castle_overview_hitbox_summary_tests"] = build_castle_hitbox_summary_tests(args)
    checks["castle_overview_hitmap_summary_tests"] = build_castle_hitmap_summary_tests(args)
    checks["castle_overview_multihit_summary_tests"] = build_castle_multihit_summary_tests(args)
    checks["castle_overview_promotion_decision"] = build_castle_decision(args)
    checks["castle_overview_promotion_decision_tests"] = build_castle_decision_tests(args)
    checks["castle_overview_baseline_recheck"] = build_castle_baseline_recheck(args)
    checks["castle_overview_baseline_recheck_tests"] = build_castle_baseline_recheck_tests(args)
    checks["castle_overview_probe_guard"] = build_castle_probe_guard(args)
    checks["castle_overview_probe_guard_tests"] = build_castle_probe_guard_tests(args)
    checks["battle_ui_summary_tests"] = build_battle_ui_summary_tests(args)
    checks["battle_ui_gate_tests"] = build_battle_ui_gate_tests(args)
    checks["battle_visible_input_summary"] = build_battle_visible_input_summary(args)
    checks["battle_visible_input_summary_tests"] = build_battle_visible_input_summary_tests(args)
    checks["battle_ui_evidence_matrix"] = build_battle_ui_evidence_matrix(args)
    checks["battle_ui_evidence_matrix_tests"] = build_battle_ui_evidence_matrix_tests(args)
    checks["battle_visible_harness_guard"] = build_battle_visible_harness_guard(args)
    checks["battle_visible_harness_guard_tests"] = build_battle_visible_harness_guard_tests(args)
    checks["patch_definition_guard"] = build_patch_definition_guard(args)
    checks["patch_definition_guard_tests"] = build_patch_definition_tests(args)
    checks["stable_stage_guard"] = build_stable_stage_guard(args)
    checks["stable_stage_guard_tests"] = build_stable_stage_guard_tests(args)
    checks["exe_artifact_guard"] = build_exe_artifact_guard(args)
    checks["surface_dump_policy_guard"] = build_surface_dump_policy_guard(args)
    checks["visible_runtime_launcher_guard"] = build_visible_runtime_launcher_guard(args)
    checks["visible_runtime_launcher_guard_tests"] = build_visible_runtime_launcher_guard_tests(args)
    checks["python_runtime_safety_guard"] = build_python_runtime_safety_guard(args)
    checks["python_runtime_safety_guard_tests"] = build_python_runtime_safety_tests(args)
    checks["no_visible_runtime_guard"] = build_no_visible_runtime_guard(args, checks)
    checks["no_visible_runtime_guard_tests"] = build_no_visible_runtime_guard_tests(args)
    checks["process_hygiene_guard"] = build_process_hygiene_guard(args)
    checks["process_hygiene_guard_tests"] = build_process_hygiene_guard_tests(args)
    checks["patch_resolution_tests"] = build_patch_resolution_tests(args)
    checks["launcher_policy_guard"] = build_launcher_policy_guard(args)
    checks["launcher_policy_guard_tests"] = build_launcher_policy_guard_tests(args)
    checks["launcher_core_tests"] = build_launcher_core_tests(args)
    checks["resolution_manifest_guard"] = build_resolution_manifest_guard(args)
    checks["resolution_manifest_guard_tests"] = build_resolution_manifest_guard_tests(args)
    checks["no_popup_guard_tests"] = build_no_popup_guard_tests(args)
    checks["manual_directinput_checklist"] = build_manual_directinput_checklist(args)
    checks["manual_directinput_checklist_tests"] = build_manual_directinput_checklist_tests(args)
    checks["hd_layout_promotion_decision"] = build_hd_layout_promotion_decision(args)
    checks["hd_layout_promotion_decision_tests"] = build_hd_layout_promotion_decision_tests(args)
    checks["manual_directinput_proof_template"] = build_manual_directinput_proof_template(args)
    checks["manual_directinput_proof_template_tests"] = build_manual_directinput_proof_template_tests(args)
    checks["manual_directinput_run_plan"] = build_manual_directinput_run_plan(args)
    checks["manual_directinput_run_plan_tests"] = build_manual_directinput_run_plan_tests(args)
    checks["promotion_override_manifest"] = build_promotion_override_manifest(args)
    checks["promotion_override_manifest_tests"] = build_promotion_override_manifest_tests(args)
    checks["promotion_override_guard"] = build_promotion_override_guard(args)
    checks["promotion_override_guard_tests"] = build_promotion_override_guard_tests(args)
    checks["handoff_freshness_guard"] = build_handoff_freshness_guard(args)
    checks["handoff_freshness_guard_tests"] = build_handoff_freshness_guard_tests(args)
    checks["current_completion_summary_tests"] = build_current_completion_summary_tests(args)
    checks["current_completion_summary"] = build_current_completion_summary(args, checks)
    checks["hd_soak_harness_guard"] = build_hd_soak_harness_guard(args)
    checks["hd_soak_harness_guard_tests"] = build_hd_soak_harness_guard_tests(args)
    checks["hd_soak_execution_boundary"] = build_hd_soak_execution_boundary(args)
    checks["hd_soak_execution_boundary_tests"] = build_hd_soak_execution_boundary_tests(args)
    checks["hd_soak_report_guard"] = build_hd_soak_report_guard(args)
    checks["hd_soak_report_guard_tests"] = build_hd_soak_report_guard_tests(args)
    checks["hd_soak_failure_triage"] = build_hd_soak_failure_triage(args)
    checks["hd_soak_failure_triage_tests"] = build_hd_soak_failure_triage_tests(args)
    checks["hd_soak_short_artifact_manifest"] = build_hd_soak_short_artifact_manifest(args)
    checks["hd_soak_short_artifact_manifest_tests"] = build_hd_soak_short_artifact_manifest_tests(args)
    checks["hd_soak_short_validation_refresh"] = build_hd_soak_short_validation_refresh(args)
    checks["hd_soak_short_validation_refresh_tests"] = build_hd_soak_short_validation_refresh_tests(args)
    checks["hd_soak_short_step_status"] = build_hd_soak_short_step_status(args)
    checks["hd_soak_short_step_status_tests"] = build_hd_soak_short_step_status_tests(args)
    checks["hd_soak_dry_run_plan"] = build_hd_soak_dry_run_plan(args)
    checks["hd_soak_dry_run_plan_tests"] = build_hd_soak_dry_run_plan_tests(args)
    checks["hd_soak_intro_skip_rerun_readiness"] = build_hd_soak_intro_skip_rerun_readiness(args)
    checks["hd_soak_intro_skip_rerun_readiness_tests"] = build_hd_soak_intro_skip_rerun_readiness_tests(args)
    checks["hd_continuity_status"] = build_hd_continuity_status(args)
    checks["hd_continuity_status_tests"] = build_hd_continuity_status_tests(args)
    checks["hd_soak_long_report_guard"] = build_hd_soak_long_report_guard(args)
    checks["hd_soak_long_report_guard_tests"] = build_hd_soak_long_report_guard_tests(args)
    checks["hd_endurance_release_checklist"] = build_hd_endurance_release_checklist(args)
    checks["hd_endurance_release_checklist_tests"] = build_hd_endurance_release_checklist_tests(args)
    checks["hd_soak_route_coverage"] = build_hd_soak_route_coverage(args)
    checks["hd_soak_route_coverage_tests"] = build_hd_soak_route_coverage_tests(args)
    checks["hd_endurance_next_actions"] = build_hd_endurance_next_actions(args)
    checks["hd_endurance_next_actions_tests"] = build_hd_endurance_next_actions_tests(args)
    checks["hd_soak_short_tier_ladder"] = build_hd_soak_short_tier_ladder(args)
    checks["hd_soak_short_tier_ladder_tests"] = build_hd_soak_short_tier_ladder_tests(args)
    checks["hd_soak_approval_preflight"] = build_hd_soak_approval_preflight(args)
    checks["hd_soak_approval_preflight_tests"] = build_hd_soak_approval_preflight_tests(args)
    checks["capture_corpus_index"] = build_capture_corpus_index(args)
    checks["capture_corpus_index_tests"] = build_capture_corpus_index_tests(args)
    checks["no_popup_boundary_guard"] = build_no_popup_boundary_guard(args, checks)
    checks["docs_consistency_guard"] = build_docs_consistency_guard(args, checks)
    checks["docs_consistency_guard_tests"] = build_docs_consistency_tests(args)
    checks["no_popup_boundary_guard"] = build_no_popup_boundary_guard(args, checks)
    checks["evidence_index_check"] = build_evidence_index_check(args)
    checks["current_completion_summary"] = build_current_completion_summary(args, checks)
    failures: list[str] = []
    for name, check in checks.items():
        if not check.get("passed"):
            check_failures = check.get("failures") or ["failed without a detailed reason"]
            failures.extend(f"{name}: {failure}" for failure in check_failures)

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "checks": checks,
        "failures": failures,
    }


def print_refresh(refresh: dict[str, Any]) -> None:
    print(f"overall: {status_text(refresh['passed'])}")
    print(f"runtime-policy: {refresh['runtime_policy']}")
    for name, check in refresh["checks"].items():
        print(f"{name}: {status_text(bool(check.get('passed')))}")
        summary = check.get("summary") or {}
        for key, value in summary.items():
            print(f"  {key}: {value}")
    if refresh["failures"]:
        print("failures:")
        for failure in refresh["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, refresh: dict[str, Any]) -> None:
    checks = refresh["checks"]
    lines = [
        "# Current Evidence Refresh",
        "",
        f"- Overall: {status_text(refresh['passed'])}",
        f"- Generated: `{refresh['generated_at']}`",
        f"- Runtime policy: {refresh['runtime_policy']}",
        "",
        "## Checks",
        "",
    ]
    for name, check in checks.items():
        lines.append(f"### {name.replace('_', ' ').title()}")
        lines.append("")
        lines.append(f"- Status: {status_text(bool(check.get('passed')))}")
        if check.get("json"):
            lines.append(f"- JSON: `{check['json']}`")
        if check.get("markdown"):
            lines.append(f"- Markdown: `{check['markdown']}`")
        if check.get("index"):
            lines.append(f"- Index: `{check['index']}`")
        summary = check.get("summary") or {}
        for key, value in summary.items():
            lines.append(f"- {key}: `{value}`")
        if summary.get("rbui_desc_switch_asserted") is False:
            # Never let a green check be read as descriptor-switch proof.
            lines.append(
                "- **UNASSERTED-CHECK DISCLOSURE:** "
                f"{summary.get('rbui_desc_switch_unasserted_reason')}"
            )
        if check.get("failures"):
            lines.append("- Failures:")
            for failure in check["failures"]:
                lines.append(f"  - {failure}")
        lines.append("")
    if refresh["failures"]:
        lines.extend(["## Failures", ""])
        lines.extend(f"- {failure}" for failure in refresh["failures"])
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captures-root", type=Path, default=Path("captures"))
    parser.add_argument("--hd-map-captures-root", type=Path, default=DEFAULT_HD_MAP_CAPTURES_ROOT)
    parser.add_argument("--normal-run", type=Path)
    parser.add_argument("--forced-run", type=Path)
    parser.add_argument("--hd-map-patch-exe", type=Path)
    parser.add_argument("--hd-map-patch-report-json", type=Path, default=DEFAULT_HD_MAP_PATCH_REPORT_JSON)
    parser.add_argument("--hd-map-stage", default=hd_map_smoke_matrix.DEFAULT_STAGE)
    parser.add_argument("--hd-map-smoke-json", type=Path, default=DEFAULT_HD_MAP_SMOKE_JSON)
    parser.add_argument("--hd-map-smoke-md", type=Path, default=DEFAULT_HD_MAP_SMOKE_MD)
    parser.add_argument("--hd-layout-log", type=Path, default=DEFAULT_HD_LAYOUT_LOG)
    parser.add_argument(
        "--hd-layout-summary-json",
        type=Path,
        default=DEFAULT_HD_LAYOUT_SUMMARY_JSON,
    )
    parser.add_argument(
        "--hd-layout-summary-md",
        type=Path,
        default=DEFAULT_HD_LAYOUT_SUMMARY_MD,
    )
    parser.add_argument(
        "--hd-layout-summary-tests-json",
        type=Path,
        default=DEFAULT_HD_LAYOUT_SUMMARY_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-layout-summary-tests-md",
        type=Path,
        default=DEFAULT_HD_LAYOUT_SUMMARY_TESTS_MD,
    )
    parser.add_argument(
        "--hd-layout-visible-run-dir",
        type=Path,
        default=DEFAULT_HD_LAYOUT_VISIBLE_RUN_DIR,
    )
    parser.add_argument(
        "--hd-layout-visible-baseline-frame",
        type=Path,
        default=DEFAULT_HD_LAYOUT_VISIBLE_BASELINE_FRAME,
    )
    parser.add_argument(
        "--hd-layout-visible-json",
        type=Path,
        default=DEFAULT_HD_LAYOUT_VISIBLE_JSON,
    )
    parser.add_argument(
        "--hd-layout-visible-md",
        type=Path,
        default=DEFAULT_HD_LAYOUT_VISIBLE_MD,
    )
    parser.add_argument(
        "--hd-layout-visible-tests-json",
        type=Path,
        default=DEFAULT_HD_LAYOUT_VISIBLE_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-layout-visible-tests-md",
        type=Path,
        default=DEFAULT_HD_LAYOUT_VISIBLE_TESTS_MD,
    )
    parser.add_argument(
        "--hd-layout-promotion-patch-json",
        type=Path,
        default=hd_layout_promotion_decision.DEFAULT_PATCH_JSON,
    )
    parser.add_argument(
        "--hd-layout-promotion-hidden-json",
        type=Path,
        default=hd_layout_promotion_decision.DEFAULT_HIDDEN_JSON,
    )
    parser.add_argument(
        "--hd-layout-promotion-hidden-run-json",
        type=Path,
        default=hd_layout_promotion_decision.DEFAULT_HIDDEN_RUN_JSON,
    )
    parser.add_argument(
        "--hd-layout-promotion-decision-json",
        type=Path,
        default=DEFAULT_HD_LAYOUT_PROMOTION_DECISION_JSON,
    )
    parser.add_argument(
        "--hd-layout-promotion-decision-md",
        type=Path,
        default=DEFAULT_HD_LAYOUT_PROMOTION_DECISION_MD,
    )
    parser.add_argument(
        "--hd-layout-promotion-decision-tests-json",
        type=Path,
        default=DEFAULT_HD_LAYOUT_PROMOTION_DECISION_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-layout-promotion-decision-tests-md",
        type=Path,
        default=DEFAULT_HD_LAYOUT_PROMOTION_DECISION_TESTS_MD,
    )
    parser.add_argument(
        "--right-bottom-natural-slot2-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_NATURAL_SLOT2_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-natural-slot2-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_NATURAL_SLOT2_TESTS_MD,
    )
    parser.add_argument("--no-popup-map-evidence-json", type=Path, default=DEFAULT_NO_POPUP_MAP_EVIDENCE_JSON)
    parser.add_argument("--no-popup-map-evidence-md", type=Path, default=DEFAULT_NO_POPUP_MAP_EVIDENCE_MD)
    parser.add_argument("--no-popup-map-evidence-tests-json", type=Path, default=DEFAULT_NO_POPUP_MAP_EVIDENCE_TESTS_JSON)
    parser.add_argument("--no-popup-map-evidence-tests-md", type=Path, default=DEFAULT_NO_POPUP_MAP_EVIDENCE_TESTS_MD)
    parser.add_argument("--no-popup-map-normal-run", type=Path, default=DEFAULT_NO_POPUP_MAP_NORMAL_RUN)
    parser.add_argument("--no-popup-map-forced-run", type=Path, default=DEFAULT_NO_POPUP_MAP_FORCED_RUN)
    parser.add_argument("--patch-compare-left", type=Path, default=DEFAULT_PATCH_COMPARE_LEFT)
    parser.add_argument("--patch-compare-right", type=Path, default=DEFAULT_PATCH_COMPARE_RIGHT)
    parser.add_argument("--patch-compare-json", type=Path, default=DEFAULT_PATCH_COMPARE_JSON)
    parser.add_argument("--patch-compare-md", type=Path, default=DEFAULT_PATCH_COMPARE_MD)
    parser.add_argument("--patch-compare-limit", type=int, default=8)
    parser.add_argument("--evidence-index", type=Path, default=DEFAULT_EVIDENCE_INDEX)
    parser.add_argument("--evidence-index-check-json", type=Path, default=DEFAULT_EVIDENCE_INDEX_CHECK_JSON)
    parser.add_argument("--castle-stage", default=castle_overview_evidence_matrix.DEFAULT_STAGE)
    parser.add_argument("--castle-patch-exe", type=Path)
    parser.add_argument("--castle-patch-report-json", type=Path, default=DEFAULT_CASTLE_PATCH_REPORT_JSON)
    parser.add_argument("--castle-overview-run", type=Path, default=castle_overview_evidence_matrix.DEFAULT_OVERVIEW_RUN)
    parser.add_argument("--castle-barracks-run", type=Path, default=castle_overview_evidence_matrix.DEFAULT_BARRACKS_RUN)
    parser.add_argument("--castle-focused-hitbox-run", type=Path, default=castle_overview_evidence_matrix.DEFAULT_FOCUSED_HITBOX_RUN)
    parser.add_argument("--castle-visible-multihit-run", type=Path, default=castle_overview_evidence_matrix.DEFAULT_VISIBLE_MULTI_RUN)
    parser.add_argument("--castle-owner-records-raw", type=Path, default=castle_overview_evidence_matrix.DEFAULT_OWNER_RECORDS_RAW)
    parser.add_argument("--castle-forced-hitmap-raw", type=Path, default=castle_overview_evidence_matrix.DEFAULT_FORCED_HITMAP_RAW)
    parser.add_argument("--castle-dormant-multihit-run", type=Path, default=castle_overview_evidence_matrix.DEFAULT_DORMANT_MULTI_RUN)
    parser.add_argument("--castle-threshold", type=int, default=12)
    parser.add_argument("--castle-max-echo-percent", type=float, default=25.0)
    parser.add_argument("--castle-matrix-json", type=Path, default=DEFAULT_CASTLE_MATRIX_JSON)
    parser.add_argument("--castle-matrix-md", type=Path, default=DEFAULT_CASTLE_MATRIX_MD)
    parser.add_argument("--castle-owner-records-tests-json", type=Path, default=DEFAULT_CASTLE_OWNER_RECORDS_TESTS_JSON)
    parser.add_argument("--castle-owner-records-tests-md", type=Path, default=DEFAULT_CASTLE_OWNER_RECORDS_TESTS_MD)
    parser.add_argument(
        "--castle-save-owner-flag-saves-root",
        type=Path,
        default=castle_save_owner_flag_scan.DEFAULT_SAVES_ROOT,
    )
    parser.add_argument(
        "--castle-save-owner-flag-known-offset",
        type=int,
        default=castle_save_owner_flag_scan.DEFAULT_KNOWN_OFFSET,
    )
    parser.add_argument(
        "--castle-save-owner-flag-record-count",
        type=int,
        default=castle_save_owner_flag_scan.DEFAULT_RECORD_COUNT,
    )
    parser.add_argument(
        "--castle-save-owner-flag-scan-json",
        type=Path,
        default=DEFAULT_CASTLE_SAVE_OWNER_FLAG_SCAN_JSON,
    )
    parser.add_argument(
        "--castle-save-owner-flag-scan-md",
        type=Path,
        default=DEFAULT_CASTLE_SAVE_OWNER_FLAG_SCAN_MD,
    )
    parser.add_argument(
        "--castle-save-owner-flag-scan-tests-json",
        type=Path,
        default=DEFAULT_CASTLE_SAVE_OWNER_FLAG_SCAN_TESTS_JSON,
    )
    parser.add_argument(
        "--castle-save-owner-flag-scan-tests-md",
        type=Path,
        default=DEFAULT_CASTLE_SAVE_OWNER_FLAG_SCAN_TESTS_MD,
    )
    parser.add_argument("--castle-matrix-tests-json", type=Path, default=DEFAULT_CASTLE_MATRIX_TESTS_JSON)
    parser.add_argument("--castle-matrix-tests-md", type=Path, default=DEFAULT_CASTLE_MATRIX_TESTS_MD)
    parser.add_argument("--castle-gate-tests-json", type=Path, default=DEFAULT_CASTLE_GATE_TESTS_JSON)
    parser.add_argument("--castle-gate-tests-md", type=Path, default=DEFAULT_CASTLE_GATE_TESTS_MD)
    parser.add_argument("--castle-hitbox-summary-tests-json", type=Path, default=DEFAULT_CASTLE_HITBOX_SUMMARY_TESTS_JSON)
    parser.add_argument("--castle-hitbox-summary-tests-md", type=Path, default=DEFAULT_CASTLE_HITBOX_SUMMARY_TESTS_MD)
    parser.add_argument("--castle-hitmap-summary-tests-json", type=Path, default=DEFAULT_CASTLE_HITMAP_SUMMARY_TESTS_JSON)
    parser.add_argument("--castle-hitmap-summary-tests-md", type=Path, default=DEFAULT_CASTLE_HITMAP_SUMMARY_TESTS_MD)
    parser.add_argument("--castle-multihit-summary-tests-json", type=Path, default=DEFAULT_CASTLE_MULTIHIT_SUMMARY_TESTS_JSON)
    parser.add_argument("--castle-multihit-summary-tests-md", type=Path, default=DEFAULT_CASTLE_MULTIHIT_SUMMARY_TESTS_MD)
    parser.add_argument(
        "--castle-baseline-overview-run",
        type=Path,
        default=castle_overview_baseline_recheck.DEFAULT_OVERVIEW_BASELINE_RUN,
    )
    parser.add_argument("--castle-baseline-recheck-json", type=Path, default=DEFAULT_CASTLE_BASELINE_RECHECK_JSON)
    parser.add_argument("--castle-baseline-recheck-md", type=Path, default=DEFAULT_CASTLE_BASELINE_RECHECK_MD)
    parser.add_argument(
        "--castle-baseline-recheck-tests-json",
        type=Path,
        default=DEFAULT_CASTLE_BASELINE_RECHECK_TESTS_JSON,
    )
    parser.add_argument("--castle-baseline-recheck-tests-md", type=Path, default=DEFAULT_CASTLE_BASELINE_RECHECK_TESTS_MD)
    parser.add_argument("--castle-probe-script", type=Path, default=castle_overview_probe_guard.DEFAULT_PROBE)
    parser.add_argument(
        "--castle-probe-summary-parser",
        type=Path,
        default=castle_overview_probe_guard.DEFAULT_SUMMARY_PARSER,
    )
    parser.add_argument("--castle-probe-patcher", type=Path, default=castle_overview_probe_guard.DEFAULT_PATCHER)
    parser.add_argument("--castle-probe-guard-json", type=Path, default=DEFAULT_CASTLE_PROBE_GUARD_JSON)
    parser.add_argument("--castle-probe-guard-md", type=Path, default=DEFAULT_CASTLE_PROBE_GUARD_MD)
    parser.add_argument(
        "--castle-probe-guard-tests-json",
        type=Path,
        default=DEFAULT_CASTLE_PROBE_GUARD_TESTS_JSON,
    )
    parser.add_argument("--castle-probe-guard-tests-md", type=Path, default=DEFAULT_CASTLE_PROBE_GUARD_TESTS_MD)
    parser.add_argument("--battle-ui-summary-tests-json", type=Path, default=DEFAULT_BATTLE_UI_SUMMARY_TESTS_JSON)
    parser.add_argument("--battle-ui-summary-tests-md", type=Path, default=DEFAULT_BATTLE_UI_SUMMARY_TESTS_MD)
    parser.add_argument("--battle-ui-gate-tests-json", type=Path, default=DEFAULT_BATTLE_UI_GATE_TESTS_JSON)
    parser.add_argument("--battle-ui-gate-tests-md", type=Path, default=DEFAULT_BATTLE_UI_GATE_TESTS_MD)
    parser.add_argument(
        "--battle-visible-input-run",
        dest="battle_visible_input_runs",
        action="append",
        type=Path,
        default=None,
    )
    parser.add_argument("--battle-visible-input-json", type=Path, default=DEFAULT_BATTLE_VISIBLE_INPUT_JSON)
    parser.add_argument("--battle-visible-input-md", type=Path, default=DEFAULT_BATTLE_VISIBLE_INPUT_MD)
    parser.add_argument(
        "--battle-visible-input-summary-tests-json",
        type=Path,
        default=DEFAULT_BATTLE_VISIBLE_INPUT_SUMMARY_TESTS_JSON,
    )
    parser.add_argument(
        "--battle-visible-input-summary-tests-md",
        type=Path,
        default=DEFAULT_BATTLE_VISIBLE_INPUT_SUMMARY_TESTS_MD,
    )
    parser.add_argument("--battle-ui-evidence-json", type=Path, default=DEFAULT_BATTLE_UI_EVIDENCE_JSON)
    parser.add_argument("--battle-ui-evidence-md", type=Path, default=DEFAULT_BATTLE_UI_EVIDENCE_MD)
    parser.add_argument(
        "--battle-ui-evidence-tests-json",
        type=Path,
        default=DEFAULT_BATTLE_UI_EVIDENCE_TESTS_JSON,
    )
    parser.add_argument("--battle-ui-evidence-tests-md", type=Path, default=DEFAULT_BATTLE_UI_EVIDENCE_TESTS_MD)
    parser.add_argument(
        "--battle-visible-harness-script",
        type=Path,
        default=battle_visible_harness_guard.DEFAULT_SCRIPT,
    )
    parser.add_argument(
        "--battle-visible-harness-guard-json",
        type=Path,
        default=DEFAULT_BATTLE_VISIBLE_HARNESS_GUARD_JSON,
    )
    parser.add_argument(
        "--battle-visible-harness-guard-md",
        type=Path,
        default=DEFAULT_BATTLE_VISIBLE_HARNESS_GUARD_MD,
    )
    parser.add_argument(
        "--battle-visible-harness-guard-tests-json",
        type=Path,
        default=DEFAULT_BATTLE_VISIBLE_HARNESS_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--battle-visible-harness-guard-tests-md",
        type=Path,
        default=DEFAULT_BATTLE_VISIBLE_HARNESS_GUARD_TESTS_MD,
    )
    parser.add_argument("--current-stable-stage", default=castle_overview_promotion_decision.DEFAULT_STABLE_STAGE)
    parser.add_argument("--manual-input-proof", type=Path)
    parser.add_argument("--allow-cdb-only-promotion", action="store_true")
    parser.add_argument("--castle-decision-json", type=Path, default=DEFAULT_CASTLE_DECISION_JSON)
    parser.add_argument("--castle-decision-md", type=Path, default=DEFAULT_CASTLE_DECISION_MD)
    parser.add_argument("--castle-decision-tests-json", type=Path, default=DEFAULT_CASTLE_DECISION_TESTS_JSON)
    parser.add_argument("--castle-decision-tests-md", type=Path, default=DEFAULT_CASTLE_DECISION_TESTS_MD)
    parser.add_argument("--barracks-success-run", type=Path, default=DEFAULT_BARRACKS_SUCCESS_RUN)
    parser.add_argument("--barracks-success-desc", default="0x005151cf")
    parser.add_argument("--barracks-success-callback", default="0x004356c0")
    parser.add_argument("--right-bottom-ui-run", type=Path, default=DEFAULT_RIGHT_BOTTOM_UI_RUN)
    parser.add_argument("--right-bottom-owner-route-run", type=Path, default=DEFAULT_RIGHT_BOTTOM_OWNER_ROUTE_RUN)
    parser.add_argument("--right-bottom-compose-baseline-run", type=Path, default=DEFAULT_RIGHT_BOTTOM_COMPOSE_BASELINE_RUN)
    parser.add_argument("--right-bottom-compose-run", type=Path, default=DEFAULT_RIGHT_BOTTOM_COMPOSE_RUN)
    parser.add_argument("--right-bottom-compose-patch-run", type=Path, default=DEFAULT_RIGHT_BOTTOM_COMPOSE_PATCH_RUN)
    parser.add_argument("--right-bottom-compose-fullstart-run", type=Path, default=DEFAULT_RIGHT_BOTTOM_COMPOSE_FULLSTART_RUN)
    parser.add_argument("--right-bottom-compose-normal-run", type=Path, default=DEFAULT_RIGHT_BOTTOM_COMPOSE_NORMAL_RUN)
    parser.add_argument("--right-bottom-compose-ui-run", type=Path, default=DEFAULT_RIGHT_BOTTOM_COMPOSE_UI_RUN)
    parser.add_argument(
        "--right-bottom-compose-ui-fixture-run",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_COMPOSE_UI_FIXTURE_RUN,
    )
    parser.add_argument("--right-bottom-grid-hit-run", type=Path, default=DEFAULT_RIGHT_BOTTOM_GRID_HIT_RUN)
    parser.add_argument("--right-bottom-grid-hit-json", type=Path, default=DEFAULT_RIGHT_BOTTOM_GRID_HIT_JSON)
    parser.add_argument("--right-bottom-grid-hit-md", type=Path, default=DEFAULT_RIGHT_BOTTOM_GRID_HIT_MD)
    parser.add_argument("--right-bottom-natural-route-run", type=Path, default=DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_RUN)
    parser.add_argument(
        "--right-bottom-natural-route-guard-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_GUARD_JSON,
    )
    parser.add_argument(
        "--right-bottom-natural-route-guard-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_GUARD_MD,
    )
    parser.add_argument(
        "--right-bottom-natural-route-guard-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-natural-route-guard-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_GUARD_TESTS_MD,
    )
    parser.add_argument(
        "--right-bottom-natural-route-candidate-save-scan-json",
        type=Path,
        default=DEFAULT_CASTLE_SAVE_OWNER_FLAG_SCAN_JSON,
    )
    parser.add_argument(
        "--right-bottom-natural-route-candidate-slot2-run",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_CANDIDATE_SLOT2_RUN,
    )
    parser.add_argument(
        "--right-bottom-natural-route-candidate-slot5-run",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_CANDIDATE_SLOT5_RUN,
    )
    parser.add_argument(
        "--right-bottom-natural-route-candidate-matrix-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_CANDIDATE_MATRIX_JSON,
    )
    parser.add_argument(
        "--right-bottom-natural-route-candidate-matrix-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_CANDIDATE_MATRIX_MD,
    )
    parser.add_argument(
        "--right-bottom-natural-route-candidate-matrix-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_CANDIDATE_MATRIX_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-natural-route-candidate-matrix-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_NATURAL_ROUTE_CANDIDATE_MATRIX_TESTS_MD,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-root",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_ROOT,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-plan-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_PLAN_JSON,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-plan-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_PLAN_MD,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-plan-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_PLAN_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-plan-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_PLAN_TESTS_MD,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-script",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_SCRIPT,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-script-guard-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_SCRIPT_GUARD_JSON,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-script-guard-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_SCRIPT_GUARD_MD,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-script-guard-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_SCRIPT_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-script-guard-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_SCRIPT_GUARD_TESTS_MD,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-runtime-surface-dump-script",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RUNTIME_SURFACE_DUMP_SCRIPT,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-runtime-extra-probe",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RUNTIME_EXTRA_PROBE,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-result-parser",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RESULT_PARSER,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-runtime-stage",
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RUNTIME_STAGE,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-runtime-plan-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RUNTIME_PLAN_JSON,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-runtime-plan-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RUNTIME_PLAN_MD,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-runtime-plan-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RUNTIME_PLAN_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-runtime-plan-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RUNTIME_PLAN_TESTS_MD,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-result-summary-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RESULT_SUMMARY_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-slot-fixture-result-summary-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_SLOT_FIXTURE_RESULT_SUMMARY_TESTS_MD,
    )
    parser.add_argument(
        "--load-slot-route-limit-decomp-c",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ROUTE_LIMIT_DECOMP_C,
    )
    parser.add_argument(
        "--load-slot-route-limit-surface-probe-script",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ROUTE_LIMIT_SURFACE_PROBE_SCRIPT,
    )
    parser.add_argument(
        "--load-slot-route-limit-slot2-run",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ROUTE_LIMIT_SLOT2_RUN,
    )
    parser.add_argument(
        "--load-slot-route-limit-slot3-run",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ROUTE_LIMIT_SLOT3_RUN,
    )
    parser.add_argument(
        "--load-slot-route-limit-slot4-run",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ROUTE_LIMIT_SLOT4_RUN,
    )
    parser.add_argument(
        "--load-slot-route-limit-slot5-run",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ROUTE_LIMIT_SLOT5_RUN,
    )
    parser.add_argument(
        "--load-slot-route-limit-recent-slot5-run",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ROUTE_LIMIT_RECENT_SLOT5_RUN,
    )
    parser.add_argument(
        "--load-slot-route-limit-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ROUTE_LIMIT_JSON,
    )
    parser.add_argument(
        "--load-slot-route-limit-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ROUTE_LIMIT_MD,
    )
    parser.add_argument(
        "--load-slot-route-limit-tests-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ROUTE_LIMIT_TESTS_JSON,
    )
    parser.add_argument(
        "--load-slot-route-limit-tests-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ROUTE_LIMIT_TESTS_MD,
    )
    parser.add_argument(
        "--load-slot-timeout-phase-slot2-run",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_SLOT2_RUN,
    )
    parser.add_argument(
        "--load-slot-timeout-phase-slot3-run",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_SLOT3_RUN,
    )
    parser.add_argument(
        "--load-slot-timeout-phase-slot4-run",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_SLOT4_RUN,
    )
    parser.add_argument(
        "--load-slot-timeout-phase-slot5-run",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_SLOT5_RUN,
    )
    parser.add_argument(
        "--load-slot-timeout-phase-recent-slot5-run",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_RECENT_SLOT5_RUN,
    )
    parser.add_argument(
        "--load-slot-timeout-phase-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_JSON,
    )
    parser.add_argument(
        "--load-slot-timeout-phase-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_MD,
    )
    parser.add_argument(
        "--load-slot-timeout-phase-tests-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_TESTS_JSON,
    )
    parser.add_argument(
        "--load-slot-timeout-phase-tests-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TIMEOUT_PHASE_TESTS_MD,
    )
    parser.add_argument(
        "--load-slot-entry-gap-decomp-c",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ENTRY_GAP_DECOMP_C,
    )
    parser.add_argument(
        "--load-slot-entry-gap-cdb-probe",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ENTRY_GAP_CDB_PROBE,
    )
    parser.add_argument(
        "--load-slot-entry-gap-timeout-phase-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ENTRY_GAP_TIMEOUT_PHASE_JSON,
    )
    parser.add_argument(
        "--load-slot-entry-gap-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ENTRY_GAP_JSON,
    )
    parser.add_argument(
        "--load-slot-entry-gap-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ENTRY_GAP_MD,
    )
    parser.add_argument(
        "--load-slot-entry-gap-tests-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ENTRY_GAP_TESTS_JSON,
    )
    parser.add_argument(
        "--load-slot-entry-gap-tests-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_ENTRY_GAP_TESTS_MD,
    )
    parser.add_argument(
        "--load-slot-transition-probe",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_PROBE,
    )
    parser.add_argument(
        "--load-slot-transition-surface-dump-script",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_SURFACE_DUMP_SCRIPT,
    )
    parser.add_argument(
        "--load-slot-transition-probe-guard-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_PROBE_GUARD_JSON,
    )
    parser.add_argument(
        "--load-slot-transition-probe-guard-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_PROBE_GUARD_MD,
    )
    parser.add_argument(
        "--load-slot-transition-probe-guard-tests-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_PROBE_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--load-slot-transition-probe-guard-tests-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_PROBE_GUARD_TESTS_MD,
    )
    parser.add_argument(
        "--load-slot-transition-result-parser",
        type=Path,
        default=load_slot_transition_run_plan.DEFAULT_RESULT_PARSER,
    )
    parser.add_argument(
        "--load-slot-transition-candidate-root",
        type=Path,
        default=load_slot_transition_run_plan.DEFAULT_CANDIDATE_ROOT,
    )
    parser.add_argument(
        "--load-slot-transition-result-root",
        type=Path,
        default=load_slot_transition_run_plan.DEFAULT_RESULT_ROOT,
    )
    parser.add_argument(
        "--load-slot-transition-run-plan-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_RUN_PLAN_JSON,
    )
    parser.add_argument(
        "--load-slot-transition-run-plan-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_RUN_PLAN_MD,
    )
    parser.add_argument(
        "--load-slot-transition-run-plan-tests-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_RUN_PLAN_TESTS_JSON,
    )
    parser.add_argument(
        "--load-slot-transition-run-plan-tests-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_RUN_PLAN_TESTS_MD,
    )
    parser.add_argument(
        "--load-slot-transition-geometry-guard-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_GEOMETRY_GUARD_JSON,
    )
    parser.add_argument(
        "--load-slot-transition-geometry-guard-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_GEOMETRY_GUARD_MD,
    )
    parser.add_argument(
        "--load-slot-transition-geometry-guard-tests-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_GEOMETRY_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--load-slot-transition-geometry-guard-tests-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_GEOMETRY_GUARD_TESTS_MD,
    )
    parser.add_argument(
        "--load-slot-transition-probe-preview-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_PROBE_PREVIEW_JSON,
    )
    parser.add_argument(
        "--load-slot-transition-probe-preview-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_PROBE_PREVIEW_MD,
    )
    parser.add_argument(
        "--load-slot-transition-probe-preview-tests-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_PROBE_PREVIEW_TESTS_JSON,
    )
    parser.add_argument(
        "--load-slot-transition-probe-preview-tests-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_PROBE_PREVIEW_TESTS_MD,
    )
    parser.add_argument(
        "--load-slot-transition-readiness-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_READINESS_JSON,
    )
    parser.add_argument(
        "--load-slot-transition-readiness-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_READINESS_MD,
    )
    parser.add_argument(
        "--load-slot-transition-readiness-tests-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_READINESS_TESTS_JSON,
    )
    parser.add_argument(
        "--load-slot-transition-readiness-tests-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_READINESS_TESTS_MD,
    )
    parser.add_argument(
        "--load-slot-transition-summary-tests-json",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_SUMMARY_TESTS_JSON,
    )
    parser.add_argument(
        "--load-slot-transition-summary-tests-md",
        type=Path,
        default=DEFAULT_LOAD_SLOT_TRANSITION_SUMMARY_TESTS_MD,
    )
    parser.add_argument(
        "--right-bottom-owner-flag-static-exe",
        type=Path,
        default=right_bottom_owner_flag_static_guard.DEFAULT_EXE,
    )
    parser.add_argument(
        "--right-bottom-owner-flag-static-guard-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_STATIC_GUARD_JSON,
    )
    parser.add_argument(
        "--right-bottom-owner-flag-static-guard-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_STATIC_GUARD_MD,
    )
    parser.add_argument(
        "--right-bottom-owner-flag-static-guard-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_STATIC_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-owner-flag-static-guard-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_STATIC_GUARD_TESTS_MD,
    )
    parser.add_argument(
        "--right-bottom-owner-flag-inventory-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_INVENTORY_JSON,
    )
    parser.add_argument(
        "--right-bottom-owner-flag-inventory-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_INVENTORY_MD,
    )
    parser.add_argument(
        "--right-bottom-owner-flag-inventory-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_INVENTORY_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-owner-flag-inventory-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_OWNER_FLAG_INVENTORY_TESTS_MD,
    )
    parser.add_argument("--right-bottom-owner-flag-inventory-max-markdown-rows", type=int, default=30)
    parser.add_argument(
        "--right-bottom-grid-hit-probe-script",
        type=Path,
        default=right_bottom_grid_hit_probe_guard.DEFAULT_PROBE,
    )
    parser.add_argument(
        "--right-bottom-grid-hit-probe-summary-parser",
        type=Path,
        default=right_bottom_grid_hit_probe_guard.DEFAULT_SUMMARY_PARSER,
    )
    parser.add_argument(
        "--right-bottom-grid-hit-probe-guard-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_GRID_HIT_PROBE_GUARD_JSON,
    )
    parser.add_argument(
        "--right-bottom-grid-hit-probe-guard-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_GRID_HIT_PROBE_GUARD_MD,
    )
    parser.add_argument(
        "--right-bottom-compose-patch-manifest",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_COMPOSE_PATCH_MANIFEST,
    )
    parser.add_argument("--right-bottom-compose-decision-json", type=Path, default=DEFAULT_RIGHT_BOTTOM_COMPOSE_DECISION_JSON)
    parser.add_argument("--right-bottom-compose-decision-md", type=Path, default=DEFAULT_RIGHT_BOTTOM_COMPOSE_DECISION_MD)
    parser.add_argument("--right-bottom-compose-manual-input-proof", type=Path)
    parser.add_argument("--allow-right-bottom-compose-cdb-only-promotion", action="store_true")
    parser.add_argument("--right-bottom-compose-matrix-json", type=Path, default=DEFAULT_RIGHT_BOTTOM_COMPOSE_MATRIX_JSON)
    parser.add_argument("--right-bottom-compose-matrix-md", type=Path, default=DEFAULT_RIGHT_BOTTOM_COMPOSE_MATRIX_MD)
    parser.add_argument(
        "--right-bottom-blocker-triage-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_BLOCKER_TRIAGE_JSON,
    )
    parser.add_argument(
        "--right-bottom-blocker-triage-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_BLOCKER_TRIAGE_MD,
    )
    parser.add_argument(
        "--right-bottom-blocker-triage-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_BLOCKER_TRIAGE_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-blocker-triage-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_BLOCKER_TRIAGE_TESTS_MD,
    )
    parser.add_argument(
        "--right-bottom-visual-artifact-guard-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_VISUAL_ARTIFACT_GUARD_JSON,
    )
    parser.add_argument(
        "--right-bottom-visual-artifact-guard-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_VISUAL_ARTIFACT_GUARD_MD,
    )
    parser.add_argument(
        "--right-bottom-visual-artifact-guard-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_VISUAL_ARTIFACT_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-visual-artifact-guard-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_VISUAL_ARTIFACT_GUARD_TESTS_MD,
    )
    parser.add_argument(
        "--first-mission-visual-audit-json",
        type=Path,
        default=DEFAULT_FIRST_MISSION_VISUAL_AUDIT_JSON,
    )
    parser.add_argument(
        "--first-mission-visual-audit-md",
        type=Path,
        default=DEFAULT_FIRST_MISSION_VISUAL_AUDIT_MD,
    )
    parser.add_argument(
        "--first-mission-visual-audit-tests-json",
        type=Path,
        default=DEFAULT_FIRST_MISSION_VISUAL_AUDIT_TESTS_JSON,
    )
    parser.add_argument(
        "--first-mission-visual-audit-tests-md",
        type=Path,
        default=DEFAULT_FIRST_MISSION_VISUAL_AUDIT_TESTS_MD,
    )
    parser.add_argument("--first-mission-visual-threshold", type=int, default=12)
    parser.add_argument("--first-mission-visual-bright-threshold", type=float, default=96.0)
    parser.add_argument("--first-mission-visual-diff-threshold", type=float, default=40.0)
    parser.add_argument("--first-mission-visual-max-stripe-high-percent", type=float, default=12.0)
    parser.add_argument("--first-mission-visual-max-stripe-excess-percent", type=float, default=8.0)
    parser.add_argument(
        "--border-frame-restore-evidence-json",
        type=Path,
        default=DEFAULT_BORDER_FRAME_RESTORE_EVIDENCE_JSON,
    )
    parser.add_argument(
        "--border-frame-restore-realruntime-json",
        type=Path,
        default=DEFAULT_BORDER_FRAME_RESTORE_REALRUNTIME_JSON,
    )
    parser.add_argument(
        "--border-frame-restore-check-json",
        type=Path,
        default=DEFAULT_BORDER_FRAME_RESTORE_CHECK_JSON,
    )
    parser.add_argument(
        "--border-frame-restore-check-md",
        type=Path,
        default=DEFAULT_BORDER_FRAME_RESTORE_CHECK_MD,
    )
    parser.add_argument(
        "--border-frame-restore-check-tests-json",
        type=Path,
        default=DEFAULT_BORDER_FRAME_RESTORE_CHECK_TESTS_JSON,
    )
    parser.add_argument(
        "--border-frame-restore-check-tests-md",
        type=Path,
        default=DEFAULT_BORDER_FRAME_RESTORE_CHECK_TESTS_MD,
    )
    parser.add_argument(
        "--right-bottom-compose-decision-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_COMPOSE_DECISION_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-compose-decision-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_COMPOSE_DECISION_TESTS_MD,
    )
    parser.add_argument(
        "--right-bottom-compose-matrix-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_COMPOSE_MATRIX_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-compose-matrix-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_COMPOSE_MATRIX_TESTS_MD,
    )
    parser.add_argument(
        "--right-bottom-grid-hit-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_GRID_HIT_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-grid-hit-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_GRID_HIT_TESTS_MD,
    )
    parser.add_argument(
        "--right-bottom-grid-hit-probe-guard-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_GRID_HIT_PROBE_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-grid-hit-probe-guard-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_GRID_HIT_PROBE_GUARD_TESTS_MD,
    )
    parser.add_argument(
        "--right-bottom-route-timing-guard-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_ROUTE_TIMING_GUARD_JSON,
    )
    parser.add_argument(
        "--right-bottom-route-timing-guard-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_ROUTE_TIMING_GUARD_MD,
    )
    parser.add_argument(
        "--right-bottom-route-timing-guard-tests-json",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_ROUTE_TIMING_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--right-bottom-route-timing-guard-tests-md",
        type=Path,
        default=DEFAULT_RIGHT_BOTTOM_ROUTE_TIMING_GUARD_TESTS_MD,
    )
    parser.add_argument("--stable-stage-guard-json", type=Path, default=DEFAULT_STABLE_STAGE_GUARD_JSON)
    parser.add_argument("--stable-stage-guard-md", type=Path, default=DEFAULT_STABLE_STAGE_GUARD_MD)
    parser.add_argument("--stable-stage-guard-tests-json", type=Path, default=DEFAULT_STABLE_STAGE_GUARD_TESTS_JSON)
    parser.add_argument("--stable-stage-guard-tests-md", type=Path, default=DEFAULT_STABLE_STAGE_GUARD_TESTS_MD)
    parser.add_argument("--patch-definition-json", type=Path, default=DEFAULT_PATCH_DEFINITION_JSON)
    parser.add_argument("--patch-definition-md", type=Path, default=DEFAULT_PATCH_DEFINITION_MD)
    parser.add_argument("--patch-definition-tests-json", type=Path, default=DEFAULT_PATCH_DEFINITION_TESTS_JSON)
    parser.add_argument("--patch-definition-tests-md", type=Path, default=DEFAULT_PATCH_DEFINITION_TESTS_MD)
    parser.add_argument("--exe-artifact-guard-json", type=Path, default=DEFAULT_EXE_ARTIFACT_GUARD_JSON)
    parser.add_argument("--exe-artifact-guard-md", type=Path, default=DEFAULT_EXE_ARTIFACT_GUARD_MD)
    parser.add_argument("--no-visible-runtime-guard-json", type=Path, default=DEFAULT_NO_VISIBLE_RUNTIME_GUARD_JSON)
    parser.add_argument("--no-visible-runtime-guard-md", type=Path, default=DEFAULT_NO_VISIBLE_RUNTIME_GUARD_MD)
    parser.add_argument(
        "--no-visible-runtime-guard-tests-json",
        type=Path,
        default=DEFAULT_NO_VISIBLE_RUNTIME_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--no-visible-runtime-guard-tests-md",
        type=Path,
        default=DEFAULT_NO_VISIBLE_RUNTIME_GUARD_TESTS_MD,
    )
    parser.add_argument("--process-hygiene-guard-json", type=Path, default=DEFAULT_PROCESS_HYGIENE_GUARD_JSON)
    parser.add_argument("--process-hygiene-guard-md", type=Path, default=DEFAULT_PROCESS_HYGIENE_GUARD_MD)
    parser.add_argument(
        "--process-hygiene-guard-tests-json",
        type=Path,
        default=DEFAULT_PROCESS_HYGIENE_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--process-hygiene-guard-tests-md",
        type=Path,
        default=DEFAULT_PROCESS_HYGIENE_GUARD_TESTS_MD,
    )
    parser.add_argument("--surface-dump-policy-guard-json", type=Path, default=DEFAULT_SURFACE_DUMP_POLICY_GUARD_JSON)
    parser.add_argument("--surface-dump-policy-guard-md", type=Path, default=DEFAULT_SURFACE_DUMP_POLICY_GUARD_MD)
    parser.add_argument("--surface-dump-policy-script", type=Path, default=surface_dump_policy_guard.DEFAULT_SCRIPT)
    parser.add_argument("--visible-runtime-launcher-guard-json", type=Path, default=DEFAULT_VISIBLE_RUNTIME_LAUNCHER_GUARD_JSON)
    parser.add_argument("--visible-runtime-launcher-guard-md", type=Path, default=DEFAULT_VISIBLE_RUNTIME_LAUNCHER_GUARD_MD)
    parser.add_argument(
        "--visible-runtime-launcher-guard-tests-json",
        type=Path,
        default=DEFAULT_VISIBLE_RUNTIME_LAUNCHER_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--visible-runtime-launcher-guard-tests-md",
        type=Path,
        default=DEFAULT_VISIBLE_RUNTIME_LAUNCHER_GUARD_TESTS_MD,
    )
    parser.add_argument(
        "--visible-runtime-launcher-script",
        type=Path,
        action="append",
        default=list(visible_runtime_launcher_guard.DEFAULT_SCRIPTS),
    )
    parser.add_argument("--python-runtime-safety-json", type=Path, default=DEFAULT_PYTHON_RUNTIME_SAFETY_JSON)
    parser.add_argument("--python-runtime-safety-md", type=Path, default=DEFAULT_PYTHON_RUNTIME_SAFETY_MD)
    parser.add_argument(
        "--patch-resolution-tests-json",
        type=Path,
        default=DEFAULT_PATCH_RESOLUTION_TESTS_JSON,
    )
    parser.add_argument(
        "--patch-resolution-tests-md",
        type=Path,
        default=DEFAULT_PATCH_RESOLUTION_TESTS_MD,
    )
    parser.add_argument("--launcher-policy-guard-json", type=Path, default=DEFAULT_LAUNCHER_POLICY_GUARD_JSON)
    parser.add_argument("--launcher-policy-guard-md", type=Path, default=DEFAULT_LAUNCHER_POLICY_GUARD_MD)
    parser.add_argument(
        "--launcher-policy-guard-tests-json",
        type=Path,
        default=DEFAULT_LAUNCHER_POLICY_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--launcher-policy-guard-tests-md",
        type=Path,
        default=DEFAULT_LAUNCHER_POLICY_GUARD_TESTS_MD,
    )
    parser.add_argument("--launcher-core-tests-json", type=Path, default=DEFAULT_LAUNCHER_CORE_TESTS_JSON)
    parser.add_argument("--launcher-core-tests-md", type=Path, default=DEFAULT_LAUNCHER_CORE_TESTS_MD)
    parser.add_argument(
        "--resolution-manifest-guard-json",
        type=Path,
        default=DEFAULT_RESOLUTION_MANIFEST_GUARD_JSON,
    )
    parser.add_argument(
        "--resolution-manifest-guard-md",
        type=Path,
        default=DEFAULT_RESOLUTION_MANIFEST_GUARD_MD,
    )
    parser.add_argument(
        "--resolution-manifest-guard-tests-json",
        type=Path,
        default=DEFAULT_RESOLUTION_MANIFEST_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--resolution-manifest-guard-tests-md",
        type=Path,
        default=DEFAULT_RESOLUTION_MANIFEST_GUARD_TESTS_MD,
    )
    parser.add_argument(
        "--python-runtime-safety-tests-json",
        type=Path,
        default=DEFAULT_PYTHON_RUNTIME_SAFETY_TESTS_JSON,
    )
    parser.add_argument(
        "--python-runtime-safety-tests-md",
        type=Path,
        default=DEFAULT_PYTHON_RUNTIME_SAFETY_TESTS_MD,
    )
    parser.add_argument("--no-popup-boundary-guard-json", type=Path, default=DEFAULT_NO_POPUP_BOUNDARY_GUARD_JSON)
    parser.add_argument("--no-popup-boundary-guard-md", type=Path, default=DEFAULT_NO_POPUP_BOUNDARY_GUARD_MD)
    parser.add_argument("--no-popup-guard-tests-json", type=Path, default=DEFAULT_NO_POPUP_GUARD_TESTS_JSON)
    parser.add_argument("--no-popup-guard-tests-md", type=Path, default=DEFAULT_NO_POPUP_GUARD_TESTS_MD)
    parser.add_argument("--handoff-next-md", type=Path, default=handoff_freshness_guard.DEFAULT_NEXT)
    parser.add_argument("--handoff-state-md", type=Path, default=handoff_freshness_guard.DEFAULT_STATE)
    parser.add_argument("--handoff-tasks-md", type=Path, default=handoff_freshness_guard.DEFAULT_TASKS)
    parser.add_argument("--handoff-progress-md", type=Path, default=handoff_freshness_guard.DEFAULT_PROGRESS)
    parser.add_argument(
        "--handoff-bottom-question-md",
        type=Path,
        default=handoff_freshness_guard.DEFAULT_BOTTOM_QUESTION,
    )
    parser.add_argument("--handoff-freshness-guard-json", type=Path, default=DEFAULT_HANDOFF_FRESHNESS_GUARD_JSON)
    parser.add_argument("--handoff-freshness-guard-md", type=Path, default=DEFAULT_HANDOFF_FRESHNESS_GUARD_MD)
    parser.add_argument(
        "--handoff-freshness-guard-tests-json",
        type=Path,
        default=DEFAULT_HANDOFF_FRESHNESS_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--handoff-freshness-guard-tests-md",
        type=Path,
        default=DEFAULT_HANDOFF_FRESHNESS_GUARD_TESTS_MD,
    )
    parser.add_argument("--manual-directinput-proof", type=Path)
    parser.add_argument("--allow-manual-directinput-cdb-only-promotion", action="store_true")
    parser.add_argument("--promotion-override-manifest", type=Path)
    parser.add_argument(
        "--manual-directinput-checklist-json",
        type=Path,
        default=DEFAULT_MANUAL_DIRECTINPUT_CHECKLIST_JSON,
    )
    parser.add_argument(
        "--manual-directinput-checklist-md",
        type=Path,
        default=DEFAULT_MANUAL_DIRECTINPUT_CHECKLIST_MD,
    )
    parser.add_argument(
        "--manual-directinput-checklist-tests-json",
        type=Path,
        default=DEFAULT_MANUAL_DIRECTINPUT_CHECKLIST_TESTS_JSON,
    )
    parser.add_argument(
        "--manual-directinput-checklist-tests-md",
        type=Path,
        default=DEFAULT_MANUAL_DIRECTINPUT_CHECKLIST_TESTS_MD,
    )
    parser.add_argument(
        "--manual-directinput-proof-template-json",
        type=Path,
        default=DEFAULT_MANUAL_DIRECTINPUT_PROOF_TEMPLATE_JSON,
    )
    parser.add_argument(
        "--manual-directinput-proof-template-report-json",
        type=Path,
        default=DEFAULT_MANUAL_DIRECTINPUT_PROOF_TEMPLATE_REPORT_JSON,
    )
    parser.add_argument(
        "--manual-directinput-proof-template-md",
        type=Path,
        default=DEFAULT_MANUAL_DIRECTINPUT_PROOF_TEMPLATE_MD,
    )
    parser.add_argument(
        "--manual-directinput-proof-template-tests-json",
        type=Path,
        default=DEFAULT_MANUAL_DIRECTINPUT_PROOF_TEMPLATE_TESTS_JSON,
    )
    parser.add_argument(
        "--manual-directinput-proof-template-tests-md",
        type=Path,
        default=DEFAULT_MANUAL_DIRECTINPUT_PROOF_TEMPLATE_TESTS_MD,
    )
    parser.add_argument(
        "--manual-directinput-run-plan-json",
        type=Path,
        default=DEFAULT_MANUAL_DIRECTINPUT_RUN_PLAN_JSON,
    )
    parser.add_argument(
        "--manual-directinput-run-plan-md",
        type=Path,
        default=DEFAULT_MANUAL_DIRECTINPUT_RUN_PLAN_MD,
    )
    parser.add_argument(
        "--manual-directinput-run-plan-tests-json",
        type=Path,
        default=DEFAULT_MANUAL_DIRECTINPUT_RUN_PLAN_TESTS_JSON,
    )
    parser.add_argument(
        "--manual-directinput-run-plan-tests-md",
        type=Path,
        default=DEFAULT_MANUAL_DIRECTINPUT_RUN_PLAN_TESTS_MD,
    )
    parser.add_argument("--promotion-override-guard-json", type=Path, default=DEFAULT_PROMOTION_OVERRIDE_GUARD_JSON)
    parser.add_argument("--promotion-override-guard-md", type=Path, default=DEFAULT_PROMOTION_OVERRIDE_GUARD_MD)
    parser.add_argument(
        "--promotion-override-guard-tests-json",
        type=Path,
        default=DEFAULT_PROMOTION_OVERRIDE_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--promotion-override-guard-tests-md",
        type=Path,
        default=DEFAULT_PROMOTION_OVERRIDE_GUARD_TESTS_MD,
    )
    parser.add_argument("--promotion-override-manifest-json", type=Path, default=DEFAULT_PROMOTION_OVERRIDE_MANIFEST_JSON)
    parser.add_argument("--promotion-override-manifest-md", type=Path, default=DEFAULT_PROMOTION_OVERRIDE_MANIFEST_MD)
    parser.add_argument(
        "--promotion-override-manifest-tests-json",
        type=Path,
        default=DEFAULT_PROMOTION_OVERRIDE_MANIFEST_TESTS_JSON,
    )
    parser.add_argument(
        "--promotion-override-manifest-tests-md",
        type=Path,
        default=DEFAULT_PROMOTION_OVERRIDE_MANIFEST_TESTS_MD,
    )
    parser.add_argument("--capture-corpus-index-json", type=Path, default=DEFAULT_CAPTURE_CORPUS_INDEX_JSON)
    parser.add_argument("--capture-corpus-index-md", type=Path, default=DEFAULT_CAPTURE_CORPUS_INDEX_MD)
    parser.add_argument(
        "--capture-corpus-index-tests-json",
        type=Path,
        default=DEFAULT_CAPTURE_CORPUS_INDEX_TESTS_JSON,
    )
    parser.add_argument(
        "--capture-corpus-index-tests-md",
        type=Path,
        default=DEFAULT_CAPTURE_CORPUS_INDEX_TESTS_MD,
    )
    parser.add_argument("--hd-soak-harness-script", type=Path, default=DEFAULT_HD_SOAK_HARNESS_SCRIPT)
    parser.add_argument("--hd-soak-harness-guard-json", type=Path, default=DEFAULT_HD_SOAK_HARNESS_GUARD_JSON)
    parser.add_argument("--hd-soak-harness-guard-md", type=Path, default=DEFAULT_HD_SOAK_HARNESS_GUARD_MD)
    parser.add_argument(
        "--hd-soak-harness-guard-tests-json",
        type=Path,
        default=DEFAULT_HD_SOAK_HARNESS_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-soak-harness-guard-tests-md",
        type=Path,
        default=DEFAULT_HD_SOAK_HARNESS_GUARD_TESTS_MD,
    )
    parser.add_argument(
        "--hd-soak-execution-boundary-json",
        type=Path,
        default=DEFAULT_HD_SOAK_EXECUTION_BOUNDARY_JSON,
    )
    parser.add_argument(
        "--hd-soak-execution-boundary-md",
        type=Path,
        default=DEFAULT_HD_SOAK_EXECUTION_BOUNDARY_MD,
    )
    parser.add_argument(
        "--hd-soak-execution-boundary-tests-json",
        type=Path,
        default=DEFAULT_HD_SOAK_EXECUTION_BOUNDARY_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-soak-execution-boundary-tests-md",
        type=Path,
        default=DEFAULT_HD_SOAK_EXECUTION_BOUNDARY_TESTS_MD,
    )
    parser.add_argument(
        "--hd-soak-execution-boundary-fixture-root",
        type=Path,
        default=hd_soak_execution_boundary.DEFAULT_FIXTURE_ROOT,
    )
    parser.add_argument("--hd-soak-dry-run-plan-json", type=Path, default=DEFAULT_HD_SOAK_DRY_RUN_PLAN_JSON)
    parser.add_argument("--hd-soak-dry-run-plan-md", type=Path, default=DEFAULT_HD_SOAK_DRY_RUN_PLAN_MD)
    parser.add_argument(
        "--hd-soak-dry-run-plan-tests-json",
        type=Path,
        default=DEFAULT_HD_SOAK_DRY_RUN_PLAN_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-soak-dry-run-plan-tests-md",
        type=Path,
        default=DEFAULT_HD_SOAK_DRY_RUN_PLAN_TESTS_MD,
    )
    parser.add_argument("--hd-soak-route-coverage-json", type=Path, default=DEFAULT_HD_SOAK_ROUTE_COVERAGE_JSON)
    parser.add_argument("--hd-soak-route-coverage-md", type=Path, default=DEFAULT_HD_SOAK_ROUTE_COVERAGE_MD)
    parser.add_argument(
        "--hd-soak-route-coverage-tests-json",
        type=Path,
        default=DEFAULT_HD_SOAK_ROUTE_COVERAGE_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-soak-route-coverage-tests-md",
        type=Path,
        default=DEFAULT_HD_SOAK_ROUTE_COVERAGE_TESTS_MD,
    )
    parser.add_argument("--hd-soak-report", type=Path, default=DEFAULT_HD_SOAK_REPORT)
    parser.add_argument("--hd-soak-first-step-report", type=Path, default=DEFAULT_HD_SOAK_FIRST_STEP_REPORT)
    parser.add_argument("--hd-soak-report-guard-json", type=Path, default=DEFAULT_HD_SOAK_REPORT_GUARD_JSON)
    parser.add_argument("--hd-soak-report-guard-md", type=Path, default=DEFAULT_HD_SOAK_REPORT_GUARD_MD)
    parser.add_argument(
        "--hd-soak-report-guard-tests-json",
        type=Path,
        default=DEFAULT_HD_SOAK_REPORT_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-soak-report-guard-tests-md",
        type=Path,
        default=DEFAULT_HD_SOAK_REPORT_GUARD_TESTS_MD,
    )
    parser.add_argument("--hd-soak-failure-triage-json", type=Path, default=DEFAULT_HD_SOAK_FAILURE_TRIAGE_JSON)
    parser.add_argument("--hd-soak-failure-triage-md", type=Path, default=DEFAULT_HD_SOAK_FAILURE_TRIAGE_MD)
    parser.add_argument(
        "--hd-soak-failure-triage-tests-json",
        type=Path,
        default=DEFAULT_HD_SOAK_FAILURE_TRIAGE_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-soak-failure-triage-tests-md",
        type=Path,
        default=DEFAULT_HD_SOAK_FAILURE_TRIAGE_TESTS_MD,
    )
    parser.add_argument(
        "--hd-endurance-release-checklist-json",
        type=Path,
        default=DEFAULT_HD_ENDURANCE_RELEASE_CHECKLIST_JSON,
    )
    parser.add_argument(
        "--hd-endurance-release-checklist-md",
        type=Path,
        default=DEFAULT_HD_ENDURANCE_RELEASE_CHECKLIST_MD,
    )
    parser.add_argument(
        "--hd-endurance-release-checklist-tests-json",
        type=Path,
        default=DEFAULT_HD_ENDURANCE_RELEASE_CHECKLIST_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-endurance-release-checklist-tests-md",
        type=Path,
        default=DEFAULT_HD_ENDURANCE_RELEASE_CHECKLIST_TESTS_MD,
    )
    parser.add_argument(
        "--hd-endurance-next-actions-json",
        type=Path,
        default=DEFAULT_HD_ENDURANCE_NEXT_ACTIONS_JSON,
    )
    parser.add_argument(
        "--hd-endurance-next-actions-md",
        type=Path,
        default=DEFAULT_HD_ENDURANCE_NEXT_ACTIONS_MD,
    )
    parser.add_argument(
        "--hd-endurance-next-actions-tests-json",
        type=Path,
        default=DEFAULT_HD_ENDURANCE_NEXT_ACTIONS_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-endurance-next-actions-tests-md",
        type=Path,
        default=DEFAULT_HD_ENDURANCE_NEXT_ACTIONS_TESTS_MD,
    )
    parser.add_argument(
        "--hd-soak-short-tier-ladder-json",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_TIER_LADDER_JSON,
    )
    parser.add_argument(
        "--hd-soak-short-tier-ladder-md",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_TIER_LADDER_MD,
    )
    parser.add_argument(
        "--hd-soak-short-tier-ladder-tests-json",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_TIER_LADDER_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-soak-short-tier-ladder-tests-md",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_TIER_LADDER_TESTS_MD,
    )
    parser.add_argument(
        "--hd-soak-short-artifact-manifest-json",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_ARTIFACT_MANIFEST_JSON,
    )
    parser.add_argument(
        "--hd-soak-short-artifact-manifest-md",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_ARTIFACT_MANIFEST_MD,
    )
    parser.add_argument(
        "--hd-soak-short-artifact-manifest-tests-json",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_ARTIFACT_MANIFEST_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-soak-short-artifact-manifest-tests-md",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_ARTIFACT_MANIFEST_TESTS_MD,
    )
    parser.add_argument(
        "--hd-soak-short-validation-refresh-json",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_VALIDATION_REFRESH_JSON,
    )
    parser.add_argument(
        "--hd-soak-short-validation-refresh-md",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_VALIDATION_REFRESH_MD,
    )
    parser.add_argument(
        "--hd-soak-short-validation-refresh-tests-json",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_VALIDATION_REFRESH_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-soak-short-validation-refresh-tests-md",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_VALIDATION_REFRESH_TESTS_MD,
    )
    parser.add_argument(
        "--hd-soak-short-step-status-json",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_STEP_STATUS_JSON,
    )
    parser.add_argument(
        "--hd-soak-short-step-status-md",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_STEP_STATUS_MD,
    )
    parser.add_argument(
        "--hd-soak-short-step-status-tests-json",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_STEP_STATUS_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-soak-short-step-status-tests-md",
        type=Path,
        default=DEFAULT_HD_SOAK_SHORT_STEP_STATUS_TESTS_MD,
    )
    parser.add_argument(
        "--hd-soak-approval-preflight-json",
        type=Path,
        default=DEFAULT_HD_SOAK_APPROVAL_PREFLIGHT_JSON,
    )
    parser.add_argument(
        "--hd-soak-approval-preflight-md",
        type=Path,
        default=DEFAULT_HD_SOAK_APPROVAL_PREFLIGHT_MD,
    )
    parser.add_argument(
        "--hd-soak-approval-preflight-tests-json",
        type=Path,
        default=DEFAULT_HD_SOAK_APPROVAL_PREFLIGHT_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-soak-approval-preflight-tests-md",
        type=Path,
        default=DEFAULT_HD_SOAK_APPROVAL_PREFLIGHT_TESTS_MD,
    )
    parser.add_argument(
        "--hd-soak-intro-skip-rerun-readiness-json",
        type=Path,
        default=DEFAULT_HD_SOAK_INTRO_SKIP_RERUN_READINESS_JSON,
    )
    parser.add_argument(
        "--hd-soak-intro-skip-rerun-readiness-md",
        type=Path,
        default=DEFAULT_HD_SOAK_INTRO_SKIP_RERUN_READINESS_MD,
    )
    parser.add_argument(
        "--hd-soak-intro-skip-rerun-readiness-tests-json",
        type=Path,
        default=DEFAULT_HD_SOAK_INTRO_SKIP_RERUN_READINESS_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-soak-intro-skip-rerun-readiness-tests-md",
        type=Path,
        default=DEFAULT_HD_SOAK_INTRO_SKIP_RERUN_READINESS_TESTS_MD,
    )
    parser.add_argument("--hd-long-soak-report-guard-json", type=Path, default=DEFAULT_HD_LONG_SOAK_REPORT_GUARD_JSON)
    parser.add_argument("--hd-long-soak-report-guard-md", type=Path, default=DEFAULT_HD_LONG_SOAK_REPORT_GUARD_MD)
    parser.add_argument("--hd-long-soak-proof-json", type=Path, default=DEFAULT_HD_LONG_SOAK_PROOF_JSON)
    parser.add_argument(
        "--hd-long-soak-report-guard-tests-json",
        type=Path,
        default=DEFAULT_HD_LONG_SOAK_REPORT_GUARD_TESTS_JSON,
    )
    parser.add_argument(
        "--hd-long-soak-report-guard-tests-md",
        type=Path,
        default=DEFAULT_HD_LONG_SOAK_REPORT_GUARD_TESTS_MD,
    )
    parser.add_argument("--hd-continuity-json", type=Path, default=DEFAULT_HD_CONTINUITY_JSON)
    parser.add_argument("--hd-continuity-md", type=Path, default=DEFAULT_HD_CONTINUITY_MD)
    parser.add_argument("--hd-continuity-proof-json", type=Path, default=DEFAULT_HD_CONTINUITY_PROOF_JSON)
    parser.add_argument("--hd-continuity-tests-json", type=Path, default=DEFAULT_HD_CONTINUITY_TESTS_JSON)
    parser.add_argument("--hd-continuity-tests-md", type=Path, default=DEFAULT_HD_CONTINUITY_TESTS_MD)
    parser.add_argument("--docs-consistency-json", type=Path, default=DEFAULT_DOCS_CONSISTENCY_JSON)
    parser.add_argument("--docs-consistency-md", type=Path, default=DEFAULT_DOCS_CONSISTENCY_MD)
    parser.add_argument("--docs-consistency-tests-json", type=Path, default=DEFAULT_DOCS_CONSISTENCY_TESTS_JSON)
    parser.add_argument("--docs-consistency-tests-md", type=Path, default=DEFAULT_DOCS_CONSISTENCY_TESTS_MD)
    parser.add_argument("--completion-battle-json", type=Path, default=DEFAULT_COMPLETION_BATTLE_JSON)
    parser.add_argument("--repo-test-sweep-json", type=Path, default=DEFAULT_REPO_TEST_SWEEP_JSON)
    parser.add_argument(
        "--current-completion-summary-json",
        type=Path,
        default=DEFAULT_CURRENT_COMPLETION_SUMMARY_JSON,
    )
    parser.add_argument(
        "--current-completion-summary-md",
        type=Path,
        default=DEFAULT_CURRENT_COMPLETION_SUMMARY_MD,
    )
    parser.add_argument(
        "--current-completion-summary-tests-json",
        type=Path,
        default=DEFAULT_CURRENT_COMPLETION_SUMMARY_TESTS_JSON,
    )
    parser.add_argument(
        "--current-completion-summary-tests-md",
        type=Path,
        default=DEFAULT_CURRENT_COMPLETION_SUMMARY_TESTS_MD,
    )
    parser.add_argument(
        "--process-guard-exact-name",
        action="append",
        default=list(process_hygiene_guard.DEFAULT_EXACT_NAMES),
    )
    parser.add_argument(
        "--process-guard-prefix",
        action="append",
        default=list(process_hygiene_guard.DEFAULT_PREFIXES),
    )
    parser.add_argument("--gitignore", type=Path, default=Path(".gitignore"))
    parser.add_argument("--write-json", type=Path, default=DEFAULT_REFRESH_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_REFRESH_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    refresh = build_refresh(args)
    print_refresh(refresh)
    if args.write_json:
        write_json(args.write_json, refresh)
    if args.write_markdown:
        write_markdown(args.write_markdown, refresh)
    if args.require_pass and not refresh["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
