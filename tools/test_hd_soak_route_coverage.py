#!/usr/bin/env python3
"""Fixture tests for hd_soak_route_coverage.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import hd_soak_route_coverage as coverage


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
    test_missing_route_fails_closed()
    test_bad_tier_duration_fails_closed()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_route_coverage tests passed")
