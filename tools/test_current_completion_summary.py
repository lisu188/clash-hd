#!/usr/bin/env python3
"""Fixture tests for the current completion summary helper."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "current_completion_summary.py"
sys.path.insert(0, str(ROOT / "tools"))

import current_completion_summary  # noqa: E402


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


def args_for(fixture: Path) -> argparse.Namespace:
    return argparse.Namespace(
        refresh_json=fixture / "refresh.json",
        battle_json=fixture / "battle.json",
        manual_checklist_json=fixture / "manual.json",
        right_bottom_decision_json=fixture / "right-bottom.json",
        repo_test_sweep_json=fixture / "repo-test-sweep.json",
    )


def write_fixture_files(fixture: Path) -> argparse.Namespace:
    write_json(
        fixture / "refresh.json",
        {
            "passed": False,
            "checks": {
                "stable_stage_guard": {"passed": True},
                "right_bottom_compose_ui_probe": {"passed": False},
                "process_hygiene_guard": {"passed": True},
                "right_bottom_compose_evidence": {"passed": False},
                "first_mission_visual_audit": {
                    "passed": False,
                    "summary": {
                        "current_status": "selected_unit_action_bar_on_bottom_but_black_ui_patches_remain",
                        "first_mission_visual_clean": False,
                        "primary_frame": "centered_bottom_edge_panel",
                        "primary_selected_action_bar_visible": True,
                        "primary_legacy_middle_action_bar_visible": False,
                        "primary_black_patch_regions": [
                            "right_below_minimap",
                            "bottom_right_panel",
                            "minimap_interior",
                        ],
                        "stripe_failure_frames": [],
                    },
                    "failures": ["primary first-mission frame is not visually clean"],
                },
                "first_mission_visual_audit_tests": {"passed": True},
            },
        },
    )
    write_json(
        fixture / "battle.json",
        {
            "passed": True,
            "completion_summary": {
                "focused_completion_percent": 99.91,
                "remaining_blocker": "real visible click-to-callback proof",
            },
            "checks": {
                "visible_input": {
                    "command_ready_run_count": 2,
                    "click_consumed_run_count": 0,
                    "invalid_run_count": 1,
                    "open_items": ["real visible click-to-callback proof remains open"],
                },
            },
            "open_items": ["real visible click-to-callback proof remains open"],
        },
    )
    write_json(
        fixture / "manual.json",
        {
            "manual_proof_valid": False,
            "promotion_ready": False,
            "summary": {
                "item_count": 5,
                "pending_count": 5,
                "pending_ids": ["stable_menu_load", "right_bottom_validation_input"],
            },
        },
    )
    write_json(
        fixture / "right-bottom.json",
        {
            "passed": False,
            "stable_stage_should_change": False,
            "required_checks": {
                "right_bottom_compose_patch": True,
                "right_bottom_compose_ui_probe": False,
                "right_bottom_natural_route_guard": True,
                "right_bottom_route_timing_guard": True,
            },
            "failures": ["right-bottom natural UI probe did not enter owner/action draw rows"],
        },
    )
    write_json(
        fixture / "repo-test-sweep.json",
        {
            "passed": True,
            "test_count": 82,
            "passed_count": 82,
            "failed_count": 0,
        },
    )
    return args_for(fixture)


def test_summary_computes_percentages(fixture: Path) -> None:
    args = write_fixture_files(fixture)
    summary = current_completion_summary.build_summary(args)
    rows = {row["id"]: row for row in summary["percentages"]}
    assert summary["passed"] is True, summary
    assert rows["current_repo_evidence_gates"]["completion_percent"] == 50.0, summary
    assert rows["repo_test_sweep"]["completion_percent"] == 100.0, summary
    assert rows["repo_test_sweep"]["passed"] is True, summary
    assert rows["focused_battle_right_bottom_lane"]["completion_percent"] == 99.91, summary
    assert rows["right_bottom_promotion_gate"]["completion_percent"] == 75.0, summary
    assert rows["manual_directinput_validation"]["completion_percent"] == 0.0, summary
    assert rows["focused_battle_right_bottom_lane"]["basis"].startswith("remaining blocker:"), summary
    assert "click-consumed runs: 0" in rows["focused_battle_right_bottom_lane"]["basis"], summary
    visual = summary["remaining_blockers"]["first_mission_visual"]
    assert visual["selected_action_bar_visible"] is True, summary
    assert visual["legacy_middle_action_bar_visible"] is False, summary
    assert visual["black_patch_regions"] == [
        "right_below_minimap",
        "bottom_right_panel",
        "minimap_interior",
    ], summary
    assert visual["stripe_failure_frames"] == [], summary
    assert summary["full_game_complete"] is False, summary
    assert "visual blockers" in summary["full_game_percent_statement"], summary


def test_summary_reports_missing_focused_completion(fixture: Path) -> None:
    args = write_fixture_files(fixture)
    battle = json.loads(args.battle_json.read_text(encoding="utf-8"))
    battle["completion_summary"].pop("focused_completion_percent")
    write_json(args.battle_json, battle)
    summary = current_completion_summary.build_summary(args)
    assert summary["passed"] is False, summary
    assert any("focused completion percent" in failure for failure in summary["failures"]), summary


def test_summary_fails_closed_when_repo_test_sweep_missing(fixture: Path) -> None:
    args = write_fixture_files(fixture)
    args.repo_test_sweep_json.unlink()
    summary = current_completion_summary.build_summary(args)
    rows = {row["id"]: row for row in summary["percentages"]}
    assert summary["passed"] is False, summary
    assert rows["repo_test_sweep"]["passed"] is False, summary
    assert any("repo test sweep artifact is missing" in failure for failure in summary["failures"]), summary


def test_summary_fails_closed_when_repo_test_sweep_failed(fixture: Path) -> None:
    args = write_fixture_files(fixture)
    write_json(
        args.repo_test_sweep_json,
        {
            "passed": False,
            "test_count": 82,
            "passed_count": 81,
            "failed_count": 1,
            "failures": ["test_probe.py exited 1"],
        },
    )
    summary = current_completion_summary.build_summary(args)
    rows = {row["id"]: row for row in summary["percentages"]}
    assert summary["passed"] is False, summary
    assert rows["repo_test_sweep"]["completion_percent"] < 100.0, summary
    assert rows["repo_test_sweep"]["passed"] is False, summary
    assert "repo test sweep is not passing" in summary["failures"], summary
    assert "test_probe.py exited 1" in summary["failures"], summary


def test_cli_writes_outputs(fixture: Path) -> None:
    args = write_fixture_files(fixture)
    out_json = fixture / "out" / "summary.json"
    out_md = fixture / "out" / "summary.md"
    run = run_script(
        "--refresh-json",
        str(args.refresh_json),
        "--battle-json",
        str(args.battle_json),
        "--manual-checklist-json",
        str(args.manual_checklist_json),
        "--right-bottom-decision-json",
        str(args.right_bottom_decision_json),
        "--repo-test-sweep-json",
        str(args.repo_test_sweep_json),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "Focused battle/right-bottom command lane" in out_md.read_text(encoding="utf-8")
    assert "First mission black patch regions" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "current-completion-summary-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_summary_computes_percentages(fixture / "percentages")
        test_summary_reports_missing_focused_completion(fixture / "missing-focused")
        test_summary_fails_closed_when_repo_test_sweep_missing(fixture / "missing-sweep")
        test_summary_fails_closed_when_repo_test_sweep_failed(fixture / "failed-sweep")
        test_cli_writes_outputs(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("current completion summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
