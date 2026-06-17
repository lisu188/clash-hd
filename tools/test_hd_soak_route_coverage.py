#!/usr/bin/env python3
"""Fixture tests for hd_soak_route_coverage.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import hd_soak_route_coverage as coverage


def write_checklist(path: Path, overrides: dict[str, dict[str, object]] | None = None) -> None:
    overrides = overrides or {}
    requirement_ids = sorted(
        {requirement_id for lane in coverage.RELEASE_LANES for requirement_id in lane["release_requirement_ids"]}
    )
    requirements = []
    for requirement_id in requirement_ids:
        requirement = {
            "id": requirement_id,
            "title": requirement_id,
            "category": "fixture",
            "status": "pass",
            "passed": True,
            "evidence": [f"captures/current/{requirement_id}.json"],
            "summary": "fixture pass",
            "next_probe": "none",
        }
        requirement.update(overrides.get(requirement_id, {}))
        requirements.append(requirement)
    path.write_text(json.dumps({"passed": True, "requirements": requirements}, indent=2) + "\n", encoding="ascii")


def test_current_harness_coverage_passes() -> None:
    report = coverage.build_report()
    assert report["passed"] is True, report["failures"]
    assert report["coverage_complete"] is False
    assert report["counts"]["implemented_lane_count"] == 3
    assert report["implemented_routes"] == ["menu-idle", "map-idle", "map-pan", "custom"]
    assert report["implemented_tiers"] == ["short2", "short10", "short30", "custom"]
    assert report["tier_seconds"]["short2"] == 120
    assert report["tier_seconds"]["short10"] == 600
    assert report["tier_seconds"]["short30"] == 1800
    assert report["counts"]["locked_future_route_count"] == report["counts"]["planned_lane_count"]


def test_future_lanes_stay_non_promoting() -> None:
    report = coverage.build_report()
    future = [lane for lane in report["release_lanes"] if not lane["implemented_in_harness"]]
    assert future
    assert all(lane["stable_stage_should_change"] is False for lane in future)
    assert any(lane["id"] == "right_bottom_action_menu" for lane in future)
    right_bottom = next(lane for lane in future if lane["id"] == "right_bottom_action_menu")
    assert "forced coordinates remain diagnostic" in right_bottom["promotion_scope"]
    assert all(lane["promotion_ready"] is False for lane in future)
    assert all(lane["safe_to_execute_now"] is False for lane in future)


def test_future_route_plan_stays_locked_and_non_executable() -> None:
    report = coverage.build_report()
    future_plan = report["locked_future_route_plan"]
    assert future_plan
    implemented_routes = set(report["implemented_routes"])
    assert all(plan["route"] is None for plan in future_plan)
    assert all(plan["proposed_route"] not in implemented_routes for plan in future_plan)
    assert all(plan["route_contract_status"] == "locked_not_scripted" for plan in future_plan)
    assert all(plan["ready_to_script"] is False for plan in future_plan)
    assert all(plan["safe_to_execute_now"] is False for plan in future_plan)
    assert all(plan["stable_stage_should_change"] is False for plan in future_plan)
    castle = next(plan for plan in future_plan if plan["id"] == "castle_overview_enter_exit")
    assert castle["proposed_route"] == "castle-overview-enter-exit"
    assert "enter-castle-overview" in castle["planned_route_steps"]
    assert "castle_and_barracks_centered_input" in castle["unlock_requirement_ids"]


def test_release_checklist_blockers_are_annotated() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "checklist.json"
        write_checklist(
            path,
            {
                "short2_menu_idle_soak": {
                    "status": "blocked",
                    "passed": False,
                    "summary": "first visible short soak is approval-gated",
                    "next_probe": "run short2 menu-idle",
                },
                "right_bottom_action_menu": {
                    "status": "blocked",
                    "passed": False,
                    "summary": "natural/manual action-menu proof is absent",
                    "next_probe": "collect approved input proof",
                },
                "first_mission_visual_clean": {
                    "status": "blocked",
                    "passed": False,
                    "summary": "first-mission black patches remain",
                    "next_probe": "fix black patch regions",
                },
            },
        )
        report = coverage.build_report(release_checklist_json=path)

    assert report["passed"] is True, report["failures"]
    assert report["release_checklist"]["state"] == "present"
    assert report["counts"]["blocked_lane_count"] >= 2
    menu = next(lane for lane in report["release_lanes"] if lane["id"] == "menu_idle")
    assert menu["readiness_status"] == "implemented_blocked_by_current_requirements"
    assert menu["current_blockers"][0]["id"] == "short2_menu_idle_soak"
    map_idle = next(lane for lane in report["release_lanes"] if lane["id"] == "map_idle")
    assert any(blocker["id"] == "first_mission_visual_clean" for blocker in map_idle["current_blockers"])
    right_bottom = next(lane for lane in report["release_lanes"] if lane["id"] == "right_bottom_action_menu")
    assert right_bottom["readiness_status"] == "planned_blocked_by_current_requirements"
    assert right_bottom["current_blockers"][0]["summary"] == "natural/manual action-menu proof is absent"
    right_bottom_plan = next(
        route_plan for route_plan in report["locked_future_route_plan"] if route_plan["id"] == "right_bottom_action_menu"
    )
    assert right_bottom_plan["blocking_requirement_ids"] == ["right_bottom_action_menu"]


def test_missing_release_checklist_is_nonfatal() -> None:
    with tempfile.TemporaryDirectory() as directory:
        missing = Path(directory) / "missing.json"
        report = coverage.build_report(release_checklist_json=missing)

    assert report["passed"] is True, report["failures"]
    assert report["release_checklist"]["state"] == "missing"
    assert report["counts"]["blocked_lane_count"] == 0
    assert all(lane["readiness_status"] == "unknown_release_checklist_missing" for lane in report["release_lanes"])


def test_stale_release_requirement_ids_fail_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "checklist.json"
        path.write_text(json.dumps({"passed": True, "requirements": []}) + "\n", encoding="ascii")
        report = coverage.build_report(release_checklist_json=path)

    assert report["passed"] is False
    assert any("release checklist missing requirement" in failure for failure in report["failures"])


def test_missing_route_fails_closed() -> None:
    text = coverage.DEFAULT_SCRIPT.read_text(encoding="utf-8-sig")
    broken = text.replace("'map-pan', ", "")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "run_hd_soak.ps1"
        path.write_text(broken, encoding="ascii")
        report = coverage.build_report(path)
    assert report["passed"] is False
    assert any("map-pan" in failure for failure in report["failures"])


def test_bad_tier_duration_fails_closed() -> None:
    text = coverage.DEFAULT_SCRIPT.read_text(encoding="utf-8-sig")
    broken = text.replace("'short10' { return 600 }", "'short10' { return 601 }")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "run_hd_soak.ps1"
        path.write_text(broken, encoding="ascii")
        report = coverage.build_report(path)
    assert report["passed"] is False
    assert any("short10 duration" in failure for failure in report["failures"])


def test_cli_writes_outputs() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        json_path = tmp / "coverage.json"
        md_path = tmp / "coverage.md"
        script = Path(__file__).resolve().parent / "hd_soak_route_coverage.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--write-json",
                str(json_path),
                "--write-markdown",
                str(md_path),
                "--require-pass",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert json_path.exists()
        assert md_path.exists()


def run_tests() -> None:
    test_current_harness_coverage_passes()
    test_future_lanes_stay_non_promoting()
    test_future_route_plan_stays_locked_and_non_executable()
    test_release_checklist_blockers_are_annotated()
    test_missing_release_checklist_is_nonfatal()
    test_stale_release_requirement_ids_fail_closed()
    test_missing_route_fails_closed()
    test_bad_tier_duration_fails_closed()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_route_coverage tests passed")
