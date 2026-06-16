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


def test_future_lanes_stay_non_promoting() -> None:
    report = coverage.build_report()
    future = [lane for lane in report["release_lanes"] if not lane["implemented_in_harness"]]
    assert future
    assert all(lane["stable_stage_should_change"] is False for lane in future)
    assert any(lane["id"] == "right_bottom_action_menu" for lane in future)
    right_bottom = next(lane for lane in future if lane["id"] == "right_bottom_action_menu")
    assert "forced coordinates remain diagnostic" in right_bottom["promotion_scope"]


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
            },
        )
        report = coverage.build_report(release_checklist_json=path)

    assert report["passed"] is True, report["failures"]
    assert report["release_checklist"]["state"] == "present"
    assert report["counts"]["blocked_lane_count"] >= 2
    menu = next(lane for lane in report["release_lanes"] if lane["id"] == "menu_idle")
    assert menu["readiness_status"] == "implemented_blocked_by_current_requirements"
    assert menu["current_blockers"][0]["id"] == "short2_menu_idle_soak"
    right_bottom = next(lane for lane in report["release_lanes"] if lane["id"] == "right_bottom_action_menu")
    assert right_bottom["readiness_status"] == "planned_blocked_by_current_requirements"
    assert right_bottom["current_blockers"][0]["summary"] == "natural/manual action-menu proof is absent"


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
    test_release_checklist_blockers_are_annotated()
    test_missing_release_checklist_is_nonfatal()
    test_stale_release_requirement_ids_fail_closed()
    test_missing_route_fails_closed()
    test_bad_tier_duration_fails_closed()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_route_coverage tests passed")
