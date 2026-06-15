#!/usr/bin/env python3
"""Fixture tests for right_bottom_blocker_triage.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "right_bottom_blocker_triage.py"
sys.path.insert(0, str(ROOT / "tools"))

import right_bottom_blocker_triage  # noqa: E402


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def good_payloads() -> dict[str, dict]:
    compose = {
        "passed": False,
        "checks": {
            "right_bottom_compose_patch": {
                "passed": True,
                "summary": {"candidate_sha256": "a" * 64},
            },
            "right_bottom_compose_fullstart_route": {
                "passed": True,
                "summary": {
                    "bottom_right_ui_corner_nonblack": 48.0,
                    "bottom_right_tile_r8c10_nonblack": 54.0,
                    "bottom_right_tile_r8c11_nonblack": 42.0,
                    "av_count": 0,
                },
            },
            "right_bottom_compose_normal_gate": {
                "passed": True,
                "summary": {"visibility_unexplained_blank_cells": 0},
            },
            "right_bottom_compose_ui_probe": {
                "passed": False,
                "summary": {
                    "rbui_markers_seen": True,
                    "rbui_panel_draw": 0,
                    "rbui_action_box": 0,
                    "av_count": 0,
                },
            },
            "right_bottom_grid_hit": {
                "passed": True,
                "summary": {"grid_hit_ok": True, "last_grid_entry": [450, 73], "last_grid_result": 0},
            },
        },
    }
    natural = {
        "passed": True,
        "summary": {
            "state_gated_by_owner_flag": True,
            "owner_flag_test": {"owner_flag": "0x00", "bit2": 0, "bit1": 0, "bit8": 0},
            "action_descriptor": {"slot": "d1", "x": 1000, "y": 426, "callback": "004338e0"},
            "action_route_count": 0,
            "av_count": 0,
        },
    }
    fixture = {
        "passed": True,
        "summary": {
            "proof_class": "non_natural_isolated_fixture",
            "promotion_ready": False,
            "stable_stage_should_change": False,
            "target_load_slot": 0,
        },
    }
    entry_gap = {
        "passed": True,
        "promotion_ready": False,
        "gap_classification": "after_main_load_callback_before_load_menu_case_entry",
        "summary": {"blocked_rows": [3, 4, 5]},
    }
    manual = {
        "passed": True,
        "proof_ready": False,
        "summary": {"all_commands_have_allow_visible_runtime": True, "command_count": 5},
    }
    decision = {
        "decision": "defer_stable_promotion",
        "stable_stage_should_change": False,
    }
    return {
        "compose": compose,
        "natural": natural,
        "fixture": fixture,
        "entry_gap": entry_gap,
        "manual": manual,
        "decision": decision,
    }


def write_payloads(fixture: Path, payloads: dict[str, dict] | None = None) -> dict[str, Path]:
    payloads = payloads or good_payloads()
    paths = {
        "compose": write_json(fixture / "compose.json", payloads["compose"]),
        "natural": write_json(fixture / "natural.json", payloads["natural"]),
        "fixture": write_json(fixture / "fixture.json", payloads["fixture"]),
        "entry_gap": write_json(fixture / "entry-gap.json", payloads["entry_gap"]),
        "manual": write_json(fixture / "manual.json", payloads["manual"]),
        "decision": write_json(fixture / "decision.json", payloads["decision"]),
    }
    if "slot5" in payloads:
        paths["slot5"] = write_json(fixture / "slot5.json", payloads["slot5"])
    return paths


def build_from_paths(paths: dict[str, Path]) -> dict:
    return right_bottom_blocker_triage.build_triage(
        compose_evidence_json=paths["compose"],
        promotion_decision_json=paths["decision"],
        natural_route_json=paths["natural"],
        natural_slot5_summary_json=paths.get("slot5", paths["natural"].with_name("missing-natural-slot5.json")),
        slot_fixture_runtime_plan_json=paths["fixture"],
        load_slot_entry_gap_json=paths["entry_gap"],
        manual_run_plan_json=paths["manual"],
    )


def test_good_blocker_shape_passes(fixture: Path) -> None:
    report = build_from_paths(write_payloads(fixture))
    assert report["passed"] is True, report
    assert report["classification"] == "controlled_recovered_but_natural_route_nonpromoting", report
    assert report["promotion_ready"] is False, report
    assert report["checks"]["natural_route_blocker_documented"] is True, report


def test_missing_controlled_composition_fails(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["compose"]["checks"]["right_bottom_compose_fullstart_route"]["summary"][
        "bottom_right_tile_r8c10_nonblack"
    ] = 3.0
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is False, report
    assert any("controlled_composition_recovered" in failure for failure in report["failures"]), report


def test_obsolete_owner_flag_gate_fails(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["natural"]["summary"]["owner_flag_test"] = {
        "owner_flag": "0x02",
        "bit2": 2,
        "bit1": 0,
        "bit8": 0,
    }
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is False, report
    assert any("natural_route_blocker_documented" in failure for failure in report["failures"]), report


def test_slot5_copyback_blocker_passes(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["natural"]["summary"]["owner_flag_test"] = {
        "owner_flag": "0x02",
        "bit2": 2,
        "bit1": 0,
        "bit8": 0,
    }
    payloads["natural"]["summary"]["state_gated_by_owner_flag"] = False
    payloads["slot5"] = {
        "proof_class": "natural_slot5_right_bottom_route",
        "status": "owner_action_draw_reached",
        "expected_slot_match": True,
        "load_success": True,
        "owner_bit2_set": True,
        "owner_action_route_count": 3,
        "owner_action_draw_count": 2,
        "render_begin_exit_count": 1,
        "wrapper_copyback_count": 0,
        "av_count": 0,
    }
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is True, report
    assert report["checks"]["natural_route_blocker_documented"] is True, report
    assert report["observations"]["natural_slot5_wrapper_copyback_count"] == 0, report


def test_slot5_copyback_path_blocker_status_passes(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["natural"]["summary"]["owner_flag_test"] = {
        "owner_flag": "0x02",
        "bit2": 2,
        "bit1": 0,
        "bit8": 0,
    }
    payloads["natural"]["summary"]["state_gated_by_owner_flag"] = False
    payloads["slot5"] = {
        "proof_class": "natural_slot5_right_bottom_route",
        "status": "owner_action_copyback_not_reached",
        "expected_slot_match": True,
        "load_success": True,
        "owner_bit2_set": True,
        "owner_action_route_count": 3,
        "owner_action_draw_count": 2,
        "render_begin_exit_count": 1,
        "copyback_path_marker_count": 8,
        "owner_435bc0_loop_count": 1,
        "owner_435bc0_return_count": 1,
        "wrapper_copyback_count": 0,
        "av_count": 0,
    }
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is True, report
    assert report["checks"]["natural_route_blocker_documented"] is True, report
    assert report["observations"]["natural_slot5_copyback_path_marker_count"] == 8, report


def test_slot5_loopstate_coordinate_blocker_passes(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["natural"]["summary"]["owner_flag_test"] = {
        "owner_flag": "0x02",
        "bit2": 2,
        "bit1": 0,
        "bit8": 0,
    }
    payloads["natural"]["summary"]["state_gated_by_owner_flag"] = False
    payloads["slot5"] = {
        "proof_class": "natural_slot5_right_bottom_loopstate",
        "status": "owner_action_435bc0_loop_stalled",
        "expected_slot_match": True,
        "load_success": True,
        "owner_bit2_set": True,
        "owner_action_route_count": 3,
        "owner_action_draw_count": 2,
        "render_begin_exit_count": 1,
        "copyback_path_marker_count": 225,
        "wrapper_copyback_count": 0,
        "owner_435bc0_loop_count": 8,
        "owner_435bc0_return_count": 0,
        "owner_435bc0_poll_count": 16,
        "owner_435bc0_poll_limit_count": 1,
        "owner_435bc0_grid_route_count": 26,
        "owner_435bc0_grid_fail_count": 10,
        "owner_435bc0_selection_update_count": 0,
        "last_owner_435bc0_poll": {"mouse": [4, 440], "raw": [256, 28160]},
        "last_owner_435bc0_grid_gate": {"raw_result": 0, "mouse": [4, 440]},
        "timeout_stack_classification": "descriptor_hit_scan",
        "av_count": 0,
    }
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is True, report
    assert report["checks"]["natural_route_blocker_documented"] is True, report
    assert report["observations"]["natural_slot5_proof_class"] == "natural_slot5_right_bottom_loopstate", report
    assert report["observations"]["natural_slot5_435bc0_grid_fail_count"] == 10, report
    assert report["observations"]["natural_slot5_timeout_stack_classification"] == "descriptor_hit_scan", report


def test_slot5_input_resample_blocker_passes(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["natural"]["summary"]["owner_flag_test"] = {
        "owner_flag": "0x02",
        "bit2": 2,
        "bit1": 0,
        "bit8": 0,
    }
    payloads["natural"]["summary"]["state_gated_by_owner_flag"] = False
    payloads["slot5"] = {
        "proof_class": "natural_slot5_right_bottom_input_resample",
        "status": "owner_action_copyback_not_reached",
        "expected_slot_match": True,
        "load_success": True,
        "owner_bit2_set": True,
        "owner_action_route_count": 3,
        "owner_action_draw_count": 2,
        "render_begin_exit_count": 1,
        "copyback_path_marker_count": 240,
        "wrapper_copyback_count": 0,
        "owner_435bc0_loop_count": 8,
        "owner_435bc0_return_count": 0,
        "owner_435bc0_poll_count": 16,
        "owner_435bc0_grid_route_count": 26,
        "owner_435bc0_grid_fail_count": 10,
        "owner_435bc0_selection_update_count": 0,
        "owner_435bc0_pump_cb14_call_count": 1,
        "owner_435bc0_pump_608f0b_call_count": 1,
        "first_owner_435bc0_pump_cb14_call": {"cb14": 0x004612E0, "raw": [0x2D00, 0x6E00]},
        "first_owner_435bc0_pump_608f0b_call": {"raw": [0x0100, 0x6E00], "button0": 0x93},
        "last_owner_435bc0_pump_cb14_call": {"cb14": 0x004612E0, "raw": [0x2D00, 0x6E00]},
        "last_owner_435bc0_pump_608f0b_call": {"raw": [0x0100, 0x6E00], "button0": 0x93},
        "last_owner_435bc0_poll": {"mouse": [4, 440], "raw": [0x0100, 0x6E00]},
        "av_count": 0,
    }
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is True, report
    assert report["checks"]["natural_route_blocker_documented"] is True, report
    assert report["observations"]["natural_slot5_proof_class"] == "natural_slot5_right_bottom_input_resample", report
    assert report["observations"]["natural_slot5_first_435bc0_pump_cb14_call"]["raw"] == [0x2D00, 0x6E00], report
    assert report["observations"]["natural_slot5_last_435bc0_pump_cb14_call"]["cb14"] == 0x004612E0, report
    assert any("00519620" in item for item in report["next_proof_options"]), report


def test_slot5_sourcehold_coords_blocker_passes(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["natural"]["summary"]["owner_flag_test"] = {
        "owner_flag": "0x02",
        "bit2": 2,
        "bit1": 0,
        "bit8": 0,
    }
    payloads["natural"]["summary"]["state_gated_by_owner_flag"] = False
    payloads["slot5"] = {
        "proof_class": "natural_slot5_right_bottom_sourcehold_coords_callsite",
        "status": "owner_action_435bc0_loop_stalled",
        "expected_slot_match": True,
        "load_success": True,
        "owner_bit2_set": True,
        "owner_action_route_count": 3,
        "owner_action_draw_count": 2,
        "render_begin_exit_count": 1,
        "copyback_path_marker_count": 832,
        "wrapper_copyback_count": 0,
        "owner_435bc0_loop_count": 8,
        "owner_435bc0_return_count": 0,
        "owner_435bc0_poll_count": 16,
        "owner_435bc0_grid_route_count": 60,
        "owner_435bc0_grid_gate_count": 60,
        "owner_435bc0_grid_fail_count": 0,
        "owner_435bc0_selection_update_count": 0,
        "owner_435bc0_pump_cb14_call_count": 7,
        "owner_435bc0_pump_608f0b_call_count": 61,
        "last_sourcehold_marker": "NOWNER_SOURCEHOLD_608F0B_COORDS_PRE",
        "last_sourcehold": {"raw": [0x2D00, 0x6E00], "d544d04": 0, "button0": 0},
        "last_owner_435bc0_poll": {"mouse": [180, 440], "raw": [0x2D00, 0x6E00]},
        "last_owner_435bc0_grid_gate": {"raw_result": 0, "mouse": [180, 440]},
        "last_owner_435bc0_pump_cb14_call": {
            "cb14": 0x004612E0,
            "raw": [0x2D00, 0x6E00],
            "d544d04": 0,
        },
        "last_owner_435bc0_pump_608f0b_call": {
            "raw": [0x2D00, 0x6E00],
            "d544d04": 0,
            "button0": 0,
        },
        "timeout_stack_classification": "descriptor_hit_scan",
        "av_count": 0,
    }
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is True, report
    assert report["checks"]["natural_route_blocker_documented"] is True, report
    assert report["observations"]["natural_slot5_proof_class"] == (
        "natural_slot5_right_bottom_sourcehold_coords_callsite"
    ), report
    assert report["observations"]["natural_slot5_last_sourcehold_marker"] == (
        "NOWNER_SOURCEHOLD_608F0B_COORDS_PRE"
    ), report
    assert report["observations"]["natural_slot5_last_sourcehold"]["button0"] == 0, report
    assert any("grid route" in item for item in report["next_proof_options"]), report


def test_slot5_action_click_native_copyback_diagnostic_passes(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["natural"]["summary"]["owner_flag_test"] = {
        "owner_flag": "0x02",
        "bit2": 2,
        "bit1": 0,
        "bit8": 0,
    }
    payloads["natural"]["summary"]["state_gated_by_owner_flag"] = False
    payloads["slot5"] = {
        "proof_class": "natural_slot5_right_bottom_action_click_native",
        "status": "owner_action_copyback_reached",
        "expected_slot_match": True,
        "load_success": True,
        "owner_bit2_set": True,
        "owner_action_route_count": 4,
        "owner_action_draw_count": 4,
        "render_begin_exit_count": 2,
        "copyback_path_marker_count": 74,
        "wrapper_copyback_count": 1,
        "wrapper_stock_return_count": 1,
        "owner_435bc0_loop_count": 1,
        "owner_435bc0_return_count": 1,
        "owner_435bc0_poll_count": 16,
        "owner_435bc0_poll_limit_count": 1,
        "action_click_marker_count": 10,
        "action_click_force_count": 1,
        "action_descriptor_callback_count": 1,
        "action_click_435620_entry_count": 1,
        "action_click_exit_set_count": 1,
        "last_action_force": {
            "target": "bottom-left-action",
            "native": [81, 441],
            "raw": [0x1440, 0x6E40],
            "button0": 0x80,
        },
        "last_action_descriptor_callback": {
            "desc": 0x0051519A,
            "callback": 0x00435620,
            "mouse": [81, 441],
        },
        "last_action_click_exit_set": {"action_state": 1},
        "av_count": 0,
    }
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is True, report
    assert report["checks"]["natural_route_blocker_documented"] is True, report
    assert report["classification"] == "controlled_recovered_but_natural_route_nonpromoting", report
    assert report["observations"]["natural_slot5_proof_class"] == "natural_slot5_right_bottom_action_click_native", report
    assert report["observations"]["natural_slot5_action_click_435620_entry_count"] == 1, report
    assert report["observations"]["natural_slot5_last_action_descriptor_callback"]["callback"] == 0x00435620, report
    assert any("debugger-forced" in item for item in report["next_proof_options"]), report


def test_slot5_centered_input_copyback_diagnostic_passes(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["natural"]["summary"]["owner_flag_test"] = {
        "owner_flag": "0x02",
        "bit2": 2,
        "bit1": 0,
        "bit8": 0,
    }
    payloads["natural"]["summary"]["state_gated_by_owner_flag"] = False
    payloads["slot5"] = {
        "proof_class": "natural_slot5_right_bottom_action_click_centered_input",
        "status": "owner_action_copyback_reached",
        "expected_slot_match": True,
        "load_success": True,
        "owner_bit2_set": True,
        "owner_action_route_count": 4,
        "owner_action_draw_count": 4,
        "render_begin_exit_count": 2,
        "copyback_path_marker_count": 74,
        "wrapper_copyback_count": 1,
        "wrapper_stock_return_count": 1,
        "owner_435bc0_loop_count": 1,
        "owner_435bc0_return_count": 1,
        "owner_435bc0_poll_count": 16,
        "owner_435bc0_poll_limit_count": 1,
        "action_click_marker_count": 10,
        "action_click_force_count": 1,
        "action_click_native_force_count": 0,
        "action_click_display_force_count": 1,
        "action_descriptor_callback_count": 1,
        "action_click_435620_entry_count": 1,
        "action_click_exit_set_count": 1,
        "last_action_force_marker": "NOWNER_ACTION_FORCE_DISPLAY",
        "last_action_force": {
            "target": "bottom-left-action",
            "displayed": [161, 501],
            "expected_native": [81, 441],
            "raw": [0x2840, 0x7D40],
            "button0": 0x80,
        },
        "last_action_descriptor_callback": {
            "desc": 0x0051519A,
            "callback": 0x00435620,
            "mouse": [81, 441],
        },
        "last_action_click_exit_set": {"action_state": 1},
        "av_count": 0,
    }
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is True, report
    assert report["checks"]["natural_route_blocker_documented"] is True, report
    assert report["observations"]["natural_slot5_proof_class"] == (
        "natural_slot5_right_bottom_action_click_centered_input"
    ), report
    assert report["observations"]["natural_slot5_action_click_display_force_count"] == 1, report
    assert report["observations"]["natural_slot5_last_action_force"]["displayed"] == [161, 501], report
    assert report["observations"]["natural_slot5_last_action_descriptor_callback"]["mouse"] == [81, 441], report


def test_promoting_fixture_plan_fails(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["fixture"]["summary"]["promotion_ready"] = True
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is False, report
    assert any("hidden_fixture_plan_ready" in failure for failure in report["failures"]), report


def test_cli_writes_outputs(fixture: Path) -> None:
    paths = write_payloads(fixture)
    out_json = fixture / "out" / "triage.json"
    out_md = fixture / "out" / "triage.md"
    run = run_script(
        "--compose-evidence-json",
        str(paths["compose"]),
        "--promotion-decision-json",
        str(paths["decision"]),
        "--natural-route-json",
        str(paths["natural"]),
        "--slot-fixture-runtime-plan-json",
        str(paths["fixture"]),
        "--load-slot-entry-gap-json",
        str(paths["entry_gap"]),
        "--manual-run-plan-json",
        str(paths["manual"]),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "Right-Bottom Blocker Triage" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "right-bottom-blocker-triage-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_blocker_shape_passes(fixture / "good")
        test_missing_controlled_composition_fails(fixture / "missing-controlled")
        test_obsolete_owner_flag_gate_fails(fixture / "owner-flag-obsolete")
        test_slot5_copyback_blocker_passes(fixture / "slot5-copyback")
        test_slot5_copyback_path_blocker_status_passes(fixture / "slot5-copyback-path")
        test_slot5_loopstate_coordinate_blocker_passes(fixture / "slot5-loopstate-coordinate")
        test_slot5_input_resample_blocker_passes(fixture / "slot5-input-resample")
        test_slot5_sourcehold_coords_blocker_passes(fixture / "slot5-sourcehold-coords")
        test_slot5_action_click_native_copyback_diagnostic_passes(fixture / "slot5-action-click-native")
        test_slot5_centered_input_copyback_diagnostic_passes(fixture / "slot5-centered-input")
        test_promoting_fixture_plan_fails(fixture / "promoting-fixture")
        test_cli_writes_outputs(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("right-bottom blocker triage tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
