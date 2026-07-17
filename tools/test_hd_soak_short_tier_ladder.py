#!/usr/bin/env python3
"""Fixture tests for hd_soak_short_tier_ladder.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import hd_soak_short_tier_ladder as ladder


def write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="ascii")
    return path


def route_coverage_fixture(*, missing_route: str | None = None) -> dict[str, Any]:
    routes = ["menu-idle", "map-idle", "map-pan", "custom"]
    if missing_route:
        routes.remove(missing_route)
    lanes = [
        {
            "id": "menu_idle",
            "route": "menu-idle",
            "status": "implemented_pending_first_soak",
            "promotion_scope": "non_promoting_short_soak",
            "implemented_in_harness": "menu-idle" in routes,
            "route_steps": [],
            "stable_stage_should_change": False,
        },
        {
            "id": "map_idle",
            "route": "map-idle",
            "status": "implemented_waiting_on_short2_menu",
            "promotion_scope": "non_promoting_short_soak",
            "implemented_in_harness": "map-idle" in routes,
            "route_steps": ["load-button", "load-slot0", "confirm-load"],
            "stable_stage_should_change": False,
        },
        {
            "id": "map_pan",
            "route": "map-pan",
            "status": "implemented_waiting_on_map_idle",
            "promotion_scope": "non_promoting_short_soak",
            "implemented_in_harness": "map-pan" in routes,
            "route_steps": ["load-button", "load-slot0", "confirm-load", "pan-path"],
            "stable_stage_should_change": False,
        },
        {
            "id": "right_bottom_action_menu",
            "route": None,
            "status": "planned_blocked_by_manual_or_natural_proof",
            "promotion_scope": "blocked; forced coordinates remain diagnostic only",
            "implemented_in_harness": False,
            "route_steps": [],
            "stable_stage_should_change": False,
        },
    ]
    return {
        "passed": True,
        "implemented_routes": routes,
        "implemented_tiers": ["short2", "short10", "short30", "custom"],
        "tier_seconds": {"short2": 120, "short10": 600, "short30": 1800},
        "release_lanes": lanes,
    }


def next_actions_fixture(command: str | None = None) -> dict[str, Any]:
    runtime_command = command or (
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
        r"'.\scripts\smoke\run_hd_soak.ps1' "
        "-Tier 'short2' -Route 'menu-idle' "
        r"-CandidateDir 'C:\ClashTests\hd-soak' "
        "-CandidateName 'clash95_hd_soak_fixture.exe' "
        "-ReportJson 'captures/current/hd-soak-short2-menu-idle-current.json' "
        "-ReportMarkdown 'captures/current/hd-soak-short2-menu-idle-current.md' "
        "-IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' "
        "-SampleIntervalSec '15' -MaxInputDriftPx '1' "
        "-MinNonblackPercent '10' -MinUniqueSampleColors '8' "
        "-MaxArtifactMB '250' -MaxWorkingSetGrowthMB '64' "
        "-MaxPrivateMemoryGrowthMB '64' -MaxHandleGrowth '128' "
        "-VisibleRuntimeApprovalExpiresUtc '2999-01-01T00:00:00+00:00' "
        "-VisibleRuntimeApprovalToken '1234567890abcdef' "
        "-Execute -AllowVisibleRuntime -RequirePass -Json"
    )
    return {
        "passed": True,
        "status": "waiting_for_explicit_visible_runtime_approval",
        "next_action": {
            "id": "run_short2_menu_idle_soak",
            "requires_explicit_user_approval": True,
            "exact_runtime_command": runtime_command,
            "exact_runtime_command_source": "dry_run_plan",
            "plan_verified_execute_command": runtime_command,
            "legacy_step_runtime_command": None,
        },
    }


def triage_next_actions_fixture() -> dict[str, Any]:
    return {
        "passed": True,
        "status": "repo_only_followup_available",
        "next_action": {
            "id": "inspect_short2_menu_idle_triage",
            "status": "triage_followup_required",
            "requires_visible_runtime": False,
            "requires_explicit_user_approval": False,
            "exact_runtime_command": None,
        },
    }


def soak_report_fixture(*, overall: bool, tier: str = "short2", route: str = "menu-idle") -> dict[str, Any]:
    return {
        "overall": overall,
        "stage": ladder.PROTECTED_STABLE_STAGE,
        "tier": tier,
        "route": route,
        "checks": {"executed": {"summary": {"executed": overall}}},
        "failures": [] if overall else ["soak report was not produced by an execution run"],
    }


def args_for(tmp: Path, *, missing_route: str | None = None, soak: dict[str, Any] | None = None) -> argparse.Namespace:
    return argparse.Namespace(
        route_coverage_json=write_json(tmp / "route.json", route_coverage_fixture(missing_route=missing_route)),
        next_actions_json=write_json(tmp / "next.json", next_actions_fixture()),
        soak_report_json=write_json(tmp / "soak.json", soak or soak_report_fixture(overall=False)),
    )


def test_current_pending_approval_ladder_passes_as_plan() -> None:
    report = ladder.build_report(
        argparse.Namespace(
            route_coverage_json=ladder.DEFAULT_ROUTE_COVERAGE_JSON,
            next_actions_json=ladder.DEFAULT_NEXT_ACTIONS_JSON,
            soak_report_json=ladder.DEFAULT_SOAK_REPORT_JSON,
        )
    )
    assert report["passed"] is True, report["failures"]
    assert report["ladder_complete"] is False
    assert report["current_step"]["id"] == "short2_map_idle"
    assert report["locks"]["stable_stage_should_change"] is False
    assert report["locks"]["right_bottom_promotion_blocked"] is True
    assert report["locks"]["long_tiers_locked"] is True
    assert report["locks"]["future_lanes_locked"] is True
    alignment = report["next_action_alignment"]
    assert (
        alignment["plan_verified_matches_current_step"]
        or alignment["repo_only_triage_matches_current_step"]
    ) is True
    if alignment["plan_verified_matches_current_step"]:
        assert report["current_step"]["requires_explicit_user_approval"] is True
        command = report["current_step"]["approval_gated_runtime_command"]
        assert "-Execute -AllowVisibleRuntime" in command
        assert "-ReportJson captures\\current\\hd-soak-short2-map-idle-current.json" in command
        assert "-ReportMarkdown captures\\current\\hd-soak-short2-map-idle-current.md" in command
        for fragment in (
            "-MaxInputDriftPx 1",
            "-IntroSkipClickMode postmessage",
            "-IntroSkipClicks 8",
            "-SkipPulses 4",
            "-SampleIntervalSec 15",
            "-MinNonblackPercent 10",
            "-MinUniqueSampleColors 8",
            "-MaxArtifactMB 250",
            "-MaxWorkingSetGrowthMB 64",
            "-MaxPrivateMemoryGrowthMB 64",
            "-MaxHandleGrowth 128",
        ):
            assert fragment in command
    else:
        assert alignment["reported_next_action"] == "inspect_short2_map_idle_triage"
        assert alignment["reported_runtime_command"] is None


def test_first_pass_advances_to_short2_map_idle() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = ladder.build_report(
            args_for(Path(directory), soak=soak_report_fixture(overall=True, tier="short2", route="menu-idle"))
        )
    assert report["passed"] is True, report["failures"]
    assert report["counts"]["passed"] == 1
    assert report["current_step"]["id"] == "short2_map_idle"
    assert report["current_step"]["status"] == "approval_required"
    assert "-Route map-idle" in report["current_step"]["approval_gated_runtime_command"]
    assert "hd-soak-short2-map-idle-current.json" in report["current_step"]["approval_gated_runtime_command"]
    assert "-MaxInputDriftPx 1" in report["current_step"]["approval_gated_runtime_command"]
    assert "-IntroSkipClickMode postmessage" in report["current_step"]["approval_gated_runtime_command"]
    assert "-MaxArtifactMB 250" in report["current_step"]["approval_gated_runtime_command"]


def test_missing_harness_route_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = ladder.build_report(args_for(Path(directory), missing_route="map-pan"))
    assert report["passed"] is False
    assert any("map-pan" in failure for failure in report["failures"])
    assert any(step["status"] == "missing_harness_contract" for step in report["steps"])


def test_mismatched_next_action_fails_for_first_step() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        args = argparse.Namespace(
            route_coverage_json=write_json(tmp / "route.json", route_coverage_fixture()),
            next_actions_json=write_json(tmp / "next.json", next_actions_fixture(command="wrong command")),
            soak_report_json=write_json(tmp / "soak.json", soak_report_fixture(overall=False)),
        )
        report = ladder.build_report(args)
    assert report["passed"] is False
    assert any("next-action command" in failure for failure in report["failures"])


def test_repo_only_triage_next_action_can_replace_runtime_command() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        args = argparse.Namespace(
            route_coverage_json=write_json(tmp / "route.json", route_coverage_fixture()),
            next_actions_json=write_json(tmp / "next.json", triage_next_actions_fixture()),
            soak_report_json=write_json(tmp / "soak.json", soak_report_fixture(overall=False)),
        )
        report = ladder.build_report(args)
    assert report["passed"] is True, report["failures"]
    assert report["next_action_alignment"]["repo_only_triage_matches_current_step"] is True


def test_cli_writes_outputs() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        json_out = tmp / "ladder.json"
        md_out = tmp / "ladder.md"
        script = Path(__file__).resolve().parent / "hd_soak_short_tier_ladder.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--write-json",
                str(json_out),
                "--write-markdown",
                str(md_out),
                "--require-pass",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert json_out.exists()
        assert md_out.exists()


def run_tests() -> None:
    test_current_pending_approval_ladder_passes_as_plan()
    test_first_pass_advances_to_short2_map_idle()
    test_missing_harness_route_fails_closed()
    test_mismatched_next_action_fails_for_first_step()
    test_repo_only_triage_next_action_can_replace_runtime_command()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_short_tier_ladder tests passed")
