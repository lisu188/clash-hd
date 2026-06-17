#!/usr/bin/env python3
"""Fixture tests for hd_endurance_release_checklist.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import hd_endurance_release_checklist as checklist


def write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="ascii")
    return path


def fixture_args(tmp: Path) -> argparse.Namespace:
    return argparse.Namespace(
        stable_stage_json=tmp / "stable.json",
        no_popup_json=tmp / "no-popup.json",
        short_soak_json=tmp / "short-soak.json",
        short_step_status_json=tmp / "short-step-status.json",
        long_soak_json=tmp / "long-soak.json",
        manual_json=tmp / "manual.json",
        right_bottom_json=tmp / "right-bottom.json",
        castle_json=tmp / "castle.json",
        battle_json=tmp / "battle.json",
        first_mission_visual_json=tmp / "first-mission-visual.json",
        completion_json=tmp / "completion.json",
        continuity_json=tmp / "continuity.json",
        exe_artifact_json=tmp / "exe.json",
        process_hygiene_json=tmp / "process.json",
    )


def write_complete_fixture(args: argparse.Namespace) -> None:
    write_json(
        args.stable_stage_json,
        {
            "current_stable_stage": checklist.PROTECTED_STABLE_STAGE,
            "patcher_default_stage": checklist.PROTECTED_STABLE_STAGE,
            "checks": {
                "patcher_default_stage": {"passed": True},
                "stable_stage_validation_groups_absent": {"passed": True},
            },
        },
    )
    write_json(args.no_popup_json, {"passed": True})
    write_json(args.short_soak_json, {"overall": True, "tier": "short2", "route": "menu-idle", "duration_sec": 120})
    write_json(
        args.short_step_status_json,
        {
            "passed": True,
            "steps": [
                {
                    "id": "short2_menu_idle",
                    "status": "pass",
                    "passed": True,
                    "tier": "short2",
                    "route": "menu-idle",
                    "summary": {"guard_present": True, "guard_overall": True, "executed": True},
                }
            ],
        },
    )
    write_json(args.long_soak_json, {"overall": True, "tier": "custom", "route": "map-pan", "duration_sec": 7200})
    manual_items = [
        "stable_menu_load",
        "stable_hd_map_input",
        "right_bottom_validation_input",
        "castle_barracks_centered_input",
        "castle_overview_centered_input",
    ]
    write_json(
        args.manual_json,
        {
            "passed": True,
            "manual_proof_valid": True,
            "stable_stage_should_change": False,
            "items": [{"id": item_id, "status": "accepted"} for item_id in manual_items],
        },
    )
    write_json(
        args.right_bottom_json,
        {
            "passed": True,
            "decision": "ready_for_stable_promotion",
            "manual_input_proof_valid": True,
            "stable_stage_should_change": False,
        },
    )
    write_json(
        args.castle_json,
        {
            "passed": True,
            "decision": "ready_for_stable_promotion",
            "manual_input_proof_valid": True,
            "stable_stage_should_change": False,
        },
    )
    write_json(
        args.battle_json,
        {
            "passed": True,
            "promotion_status": "release_ready",
            "stable_stage_should_change": False,
        },
    )
    write_json(
        args.first_mission_visual_json,
        {
            "passed": True,
            "current_status": "first_mission_visual_clean",
            "first_mission_visual_clean": True,
            "primary_frame": "centered_bottom_edge_panel",
            "primary_frame_path": r"captures\archive\clean\surface.png",
            "next_probe": "rerun first_mission_visual_audit.py after the next first-mission visual evidence refresh",
            "summary": {
                "primary_selected_action_bar_visible": True,
                "primary_legacy_middle_action_bar_visible": False,
                "primary_black_patch_regions": [],
                "stripe_failure_frames": [],
            },
        },
    )
    write_json(args.completion_json, {"passed": True, "full_game_complete": True})
    write_json(
        args.continuity_json,
        {
            "passed": True,
            "checks": {
                "save_load_roundtrip": True,
                "turn_advancement": {"passed": True},
                "campaign_routes": True,
            },
        },
    )
    write_json(args.exe_artifact_json, {"passed": True})
    write_json(args.process_hygiene_json, {"passed": True})


def req(report: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    for row in report["requirements"]:
        if row["id"] == requirement_id:
            return row
    raise AssertionError(f"missing requirement: {requirement_id}")


def test_complete_fixture_passes() -> None:
    with tempfile.TemporaryDirectory() as directory:
        args = fixture_args(Path(directory))
        write_complete_fixture(args)
        report = checklist.build_checklist(args)
        assert report["passed"] is True, report["failures"]
        assert report["full_game_complete"] is True
        assert report["counts"]["passed"] == report["counts"]["total"]


def test_pending_short_soak_blocks_next_milestone() -> None:
    with tempfile.TemporaryDirectory() as directory:
        args = fixture_args(Path(directory))
        write_complete_fixture(args)
        write_json(
            args.short_soak_json,
            {
                "overall": False,
                "tier": "short2",
                "duration_sec": 120,
                "source_report_selection": "legacy_compatibility",
                "canonical_first_step_report": r"captures\current\hd-soak-short2-menu-idle-current.json",
                "canonical_first_step_present": False,
                "canonical_runtime_report_missing": True,
                "failures": ["soak report was not produced by an execution run"],
            },
        )
        write_json(
            args.short_step_status_json,
            {
                "passed": True,
                "ladder_complete": False,
                "current_step": {"id": "short2_menu_idle", "status": "pending_approval_legacy_compat"},
                "steps": [
                    {
                        "id": "short2_menu_idle",
                        "status": "pending_approval_legacy_compat",
                        "passed": False,
                        "tier": "short2",
                        "route": "menu-idle",
                        "paths": {
                            "report_json": r"captures\current\hd-soak-short2-menu-idle-current.json",
                            "guard_json": r"captures\current\hd-soak-short2-menu-idle-guard-current.json",
                            "triage_json": r"captures\current\hd-soak-short2-menu-idle-triage-current.json",
                        },
                        "summary": {
                            "canonical_report_present": False,
                            "guard_present": False,
                            "triage_present": False,
                        },
                    }
                ],
            },
        )
        report = checklist.build_checklist(args)
    first_soak = req(report, "short2_menu_idle_soak")
    assert report["passed"] is False
    assert first_soak["status"] == "blocked"
    assert "canonical report is missing" in first_soak["summary"]
    assert first_soak["details"]["global_report_guard"]["canonical_runtime_report_missing"] is True
    assert first_soak["details"]["canonical_outputs"]["report_json"] == (
        r"captures\current\hd-soak-short2-menu-idle-current.json"
    )
    assert first_soak["details"]["canonical_outputs"]["guard_json"] == (
        r"captures\current\hd-soak-short2-menu-idle-guard-current.json"
    )
    assert first_soak["details"]["canonical_outputs"]["triage_json"] == (
        r"captures\current\hd-soak-short2-menu-idle-triage-current.json"
    )
    assert first_soak["details"]["short_step_status"]["current_step_status"] == "pending_approval_legacy_compat"
    assert first_soak["details"]["short_step_status"]["canonical_report_present"] is False
    assert first_soak["details"]["short_step_status"]["guard_present"] is False
    assert first_soak["details"]["short_step_status"]["triage_present"] is False
    assert report["next_milestone"]["id"] == "short2_menu_idle_soak"


def test_classified_short_step_status_overrides_stale_global_missing_summary() -> None:
    with tempfile.TemporaryDirectory() as directory:
        args = fixture_args(Path(directory))
        write_complete_fixture(args)
        write_json(
            args.short_soak_json,
            {
                "overall": False,
                "tier": "short2",
                "duration_sec": 120,
                "source_report_selection": "legacy_compatibility",
                "canonical_first_step_report": r"captures\current\hd-soak-short2-menu-idle-current.json",
                "canonical_first_step_present": False,
                "canonical_runtime_report_missing": True,
                "failures": ["soak report was not produced by an execution run"],
            },
        )
        write_json(
            args.short_step_status_json,
            {
                "passed": True,
                "ladder_complete": False,
                "current_step": {
                    "id": "short2_menu_idle",
                    "status": "failed_classified_intro_skip_input_drift_exit",
                },
                "steps": [
                    {
                        "id": "short2_menu_idle",
                        "status": "failed_classified_intro_skip_input_drift_exit",
                        "passed": False,
                        "tier": "short2",
                        "route": "menu-idle",
                        "paths": {
                            "report_json": r"captures\current\hd-soak-short2-menu-idle-current.json",
                            "guard_json": r"captures\current\hd-soak-short2-menu-idle-guard-current.json",
                            "triage_json": r"captures\current\hd-soak-short2-menu-idle-triage-current.json",
                        },
                        "summary": {
                            "canonical_report_present": True,
                            "guard_present": True,
                            "triage_present": True,
                            "guard_overall": False,
                            "classification": "intro_skip_input_drift_exit",
                        },
                    }
                ],
            },
        )
        report = checklist.build_checklist(args)
    first_soak = req(report, "short2_menu_idle_soak")
    assert report["passed"] is False
    assert "current short-step status is failed_classified_intro_skip_input_drift_exit" in first_soak["summary"]
    assert "canonical report is missing" not in first_soak["summary"]
    assert first_soak["details"]["short_step_status"]["canonical_report_present"] is True
    assert first_soak["details"]["short_step_status"]["triage_present"] is True


def test_canonical_short_step_status_satisfies_first_soak() -> None:
    with tempfile.TemporaryDirectory() as directory:
        args = fixture_args(Path(directory))
        write_complete_fixture(args)
        write_json(args.short_soak_json, {"overall": False, "tier": "short2", "duration_sec": 120})
        write_json(
            args.short_step_status_json,
            {
                "passed": True,
                "steps": [
                    {
                        "id": "short2_menu_idle",
                        "status": "pass",
                        "passed": True,
                        "tier": "short2",
                        "route": "menu-idle",
                        "summary": {
                            "guard_present": True,
                            "guard_overall": True,
                            "executed": True,
                            "candidate_sha256": "a" * 64,
                        },
                    }
                ],
            },
        )
        report = checklist.build_checklist(args)
    assert report["passed"] is True, report["failures"]
    first_soak = req(report, "short2_menu_idle_soak")
    assert first_soak["passed"] is True
    assert first_soak["summary"] == "canonical short2 menu-idle step status passes"


def test_pending_manual_input_blocks_menu_and_map() -> None:
    with tempfile.TemporaryDirectory() as directory:
        args = fixture_args(Path(directory))
        write_complete_fixture(args)
        write_json(
            args.manual_json,
            {
                "passed": True,
                "manual_proof_valid": False,
                "stable_stage_should_change": False,
                "items": [
                    {"id": "stable_menu_load", "status": "pending_manual"},
                    {"id": "stable_hd_map_input", "status": "pending_manual"},
                    {"id": "castle_barracks_centered_input", "status": "pending_manual"},
                    {"id": "castle_overview_centered_input", "status": "pending_manual"},
                ],
            },
        )
        report = checklist.build_checklist(args)
        assert report["passed"] is False
        assert req(report, "stable_menu_real_input")["passed"] is False
        assert req(report, "stable_hd_map_real_input")["passed"] is False
        assert req(report, "castle_and_barracks_centered_input")["passed"] is False


def test_validation_only_right_bottom_blocks_release() -> None:
    with tempfile.TemporaryDirectory() as directory:
        args = fixture_args(Path(directory))
        write_complete_fixture(args)
        write_json(
            args.right_bottom_json,
            {
                "passed": False,
                "decision": "defer_stable_promotion",
                "manual_input_proof_valid": False,
                "stable_stage_should_change": False,
            },
        )
        report = checklist.build_checklist(args)
        assert report["passed"] is False
        assert req(report, "right_bottom_action_menu")["status"] == "blocked"


def test_first_mission_visual_top_level_clean_flag_satisfies_requirement() -> None:
    with tempfile.TemporaryDirectory() as directory:
        args = fixture_args(Path(directory))
        write_complete_fixture(args)
        write_json(
            args.first_mission_visual_json,
            {
                "passed": True,
                "current_status": "first_mission_visual_clean",
                "first_mission_visual_clean": True,
                "primary_frame": "centered_bottom_edge_panel",
                "primary_frame_path": r"captures\archive\clean\surface.png",
                "next_probe": "rerun first_mission_visual_audit.py",
                "summary": {
                    "primary_selected_action_bar_visible": True,
                    "primary_legacy_middle_action_bar_visible": False,
                    "primary_black_patch_regions": [],
                    "stripe_failure_frames": [],
                },
            },
        )
        report = checklist.build_checklist(args)
    visual = req(report, "first_mission_visual_clean")
    assert report["passed"] is True, report["failures"]
    assert visual["passed"] is True
    assert visual["details"]["current_status"] == "first_mission_visual_clean"
    assert visual["details"]["primary_frame"] == "centered_bottom_edge_panel"
    assert visual["details"]["primary_frame_path"] == r"captures\archive\clean\surface.png"


def test_first_mission_visual_summary_clean_flag_satisfies_requirement() -> None:
    with tempfile.TemporaryDirectory() as directory:
        args = fixture_args(Path(directory))
        write_complete_fixture(args)
        write_json(
            args.first_mission_visual_json,
            {
                "passed": True,
                "summary": {
                    "current_status": "first_mission_visual_clean",
                    "first_mission_visual_clean": True,
                    "primary_frame": "centered_bottom_edge_panel",
                    "primary_frame_path": r"captures\archive\clean-summary\surface.png",
                    "primary_selected_action_bar_visible": True,
                    "primary_legacy_middle_action_bar_visible": False,
                    "primary_black_patch_regions": [],
                    "stripe_failure_frames": [],
                    "next_probe": "rerun first_mission_visual_audit.py",
                },
            },
        )
        report = checklist.build_checklist(args)
    visual = req(report, "first_mission_visual_clean")
    assert report["passed"] is True, report["failures"]
    assert visual["passed"] is True
    assert visual["details"]["current_status"] == "first_mission_visual_clean"
    assert visual["details"]["primary_frame"] == "centered_bottom_edge_panel"
    assert visual["details"]["primary_frame_path"] == r"captures\archive\clean-summary\surface.png"
    assert visual["details"]["next_probe"] == "rerun first_mission_visual_audit.py"


def test_first_mission_visual_blockers_block_release() -> None:
    with tempfile.TemporaryDirectory() as directory:
        args = fixture_args(Path(directory))
        write_complete_fixture(args)
        write_json(
            args.first_mission_visual_json,
            {
                "passed": False,
                "current_status": "selected_unit_action_bar_on_bottom_but_black_ui_patches_remain",
                "primary_frame": "centered_bottom_edge_panel",
                "primary_frame_path": r"captures\archive\blocked\surface.png",
                "next_probe": "inspect the primary frame's right-side/minimap/bottom-panel compose or present path",
                "summary": {
                    "first_mission_visual_clean": False,
                    "primary_selected_action_bar_visible": True,
                    "primary_legacy_middle_action_bar_visible": False,
                    "primary_black_patch_regions": [
                        "right_below_minimap",
                        "bottom_right_panel",
                        "minimap_interior",
                    ],
                    "primary_black_patch_details": [
                        {
                            "region": "right_below_minimap",
                            "rect": [586, 230, 799, 599],
                            "black_percent": 76.407,
                            "nonblack_percent": 23.593,
                            "mean_luma": 22.011,
                            "quantized_color_bins": 19,
                        }
                    ],
                    "stripe_failure_frames": [],
                },
                "failures": ["primary first-mission frame is not visually clean"],
            },
        )
        report = checklist.build_checklist(args)
    visual = req(report, "first_mission_visual_clean")
    assert report["passed"] is False
    assert visual["status"] == "blocked"
    assert visual["details"]["selected_action_bar_visible"] is True
    assert visual["details"]["legacy_middle_action_bar_visible"] is False
    assert visual["details"]["black_patch_regions"] == [
        "right_below_minimap",
        "bottom_right_panel",
        "minimap_interior",
    ]
    assert visual["details"]["black_patch_details"] == [
        {
            "region": "right_below_minimap",
            "rect": [586, 230, 799, 599],
            "black_percent": 76.407,
            "nonblack_percent": 23.593,
            "mean_luma": 22.011,
            "quantized_color_bins": 19,
        }
    ]
    assert visual["details"]["next_probe"].startswith("inspect the primary frame")
    assert "black patches: right_below_minimap, bottom_right_panel, minimap_interior" in visual["summary"]


def test_cli_writes_outputs_and_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        args = fixture_args(tmp)
        write_complete_fixture(args)
        args.long_soak_json.unlink()
        json_out = tmp / "report.json"
        md_out = tmp / "report.md"
        script = Path(__file__).resolve().parent / "hd_endurance_release_checklist.py"
        command = [
            sys.executable,
            str(script),
            "--stable-stage-json",
            str(args.stable_stage_json),
            "--no-popup-json",
            str(args.no_popup_json),
            "--short-soak-json",
            str(args.short_soak_json),
            "--short-step-status-json",
            str(args.short_step_status_json),
            "--long-soak-json",
            str(args.long_soak_json),
            "--manual-json",
            str(args.manual_json),
            "--right-bottom-json",
            str(args.right_bottom_json),
            "--castle-json",
            str(args.castle_json),
            "--battle-json",
            str(args.battle_json),
            "--first-mission-visual-json",
            str(args.first_mission_visual_json),
            "--completion-json",
            str(args.completion_json),
            "--continuity-json",
            str(args.continuity_json),
            "--exe-artifact-json",
            str(args.exe_artifact_json),
            "--process-hygiene-json",
            str(args.process_hygiene_json),
            "--write-json",
            str(json_out),
            "--write-markdown",
            str(md_out),
            "--require-pass",
        ]
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        assert result.returncode == 1, result.stdout
        assert json_out.exists()
        assert md_out.exists()
        report = json.loads(json_out.read_text(encoding="ascii"))
        assert req(report, "long_soak_representative_routes")["status"] == "missing"


def run_tests() -> None:
    test_complete_fixture_passes()
    test_pending_short_soak_blocks_next_milestone()
    test_classified_short_step_status_overrides_stale_global_missing_summary()
    test_canonical_short_step_status_satisfies_first_soak()
    test_pending_manual_input_blocks_menu_and_map()
    test_validation_only_right_bottom_blocks_release()
    test_first_mission_visual_top_level_clean_flag_satisfies_requirement()
    test_first_mission_visual_summary_clean_flag_satisfies_requirement()
    test_first_mission_visual_blockers_block_release()
    test_cli_writes_outputs_and_fails_closed()


if __name__ == "__main__":
    run_tests()
    print("hd_endurance_release_checklist tests passed")
