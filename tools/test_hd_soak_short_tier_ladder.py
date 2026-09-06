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
    with tempfile.TemporaryDirectory() as directory:
        report = ladder.build_report(args_for(Path(directory)))
    assert report["passed"] is True, report["failures"]
    assert report["ladder_complete"] is False
    assert report["current_step"]["id"] == "short2_menu_idle"
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
        assert "-ReportJson captures\\current\\hd-soak-short2-menu-idle-current.json" in command
        assert "-ReportMarkdown captures\\current\\hd-soak-short2-menu-idle-current.md" in command
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
        assert alignment["reported_next_action"] == "inspect_short2_menu_idle_triage"
        assert alignment["reported_runtime_command"] is None
    assert report["current_step"]["hidden_cdb_runtime_command"] is None
    assert report["current_step"]["preferred_environment"] == "host_visible"
    assert report["steps"][0]["requires_visible_runtime"] is True


def test_first_pass_advances_to_short2_map_idle() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = ladder.build_report(
            args_for(Path(directory), soak=soak_report_fixture(overall=True, tier="short2", route="menu-idle"))
        )
    assert report["passed"] is True, report["failures"]
    assert report["counts"]["passed"] == 1
    assert report["current_step"]["id"] == "short2_map_idle"
    current = report["current_step"]
    assert current["status"] == "runtime_required"
    assert current["requires_explicit_user_approval"] is False
    assert current["preferred_environment"] == "hidden_cdb_host"
    assert current["recommended_runtime_command"] == current["hidden_cdb_runtime_command"]
    assert current["recommended_safe_dry_run_command"] == current["hidden_cdb_safe_dry_run_command"]
    command = current["recommended_runtime_command"]
    for fragment in (r"scripts\cdb\run_hidden_soak.ps1", "-Route map-idle", "-DurationSec 120",
                     "-FrameIntervalSec 15", "-PanIntervalSec 10", "-MaxArtifactMB 250", "-Execute"):
        assert fragment in command
    paths = ladder.canonical_report_paths(current)
    for option, key in (("-ReportJson", "report_json"), ("-ReportMarkdown", "report_markdown"),
                        ("-GuardJson", "guard_json"), ("-GuardMarkdown", "guard_markdown")):
        assert f"{option} {paths[key]}" in command
    assert "-AllowVisibleRuntime" not in command
    assert "-Execute" not in current["recommended_safe_dry_run_command"]
    assert "-MaxInputDriftPx 1" in current["approval_gated_runtime_command"]
    assert "-Execute -AllowVisibleRuntime" in current["approval_gated_runtime_command"]
    assert report["steps"][1]["visible_runtime_alternative_requires_explicit_user_approval"] is True


def test_first_pass_labels_host_environment() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = ladder.build_report(
            args_for(Path(directory), soak=soak_report_fixture(overall=True, tier="short2", route="menu-idle"))
        )
    assert report["passed"] is True, report["failures"]
    assert report["steps"][0]["environment"] == "host_visible"
    assert report["steps"][1]["environment"] is None


def test_hidden_soak_report_counts_and_labels_environment() -> None:
    """Hidden map evidence stays labeled and cannot stand in for its menu prerequisite."""
    hidden = soak_report_fixture(overall=True, tier="short2", route="map-idle")
    hidden["environment"] = "hidden_cdb_host"
    hidden["evidence_class"] = "approved_hidden_cdb_host_soak"
    with tempfile.TemporaryDirectory() as directory:
        report = ladder.build_report(args_for(Path(directory), soak=hidden))
    assert report["passed"] is True, report["failures"]
    assert report["counts"]["passed"] == 0
    assert report["steps"][1]["matched_current_soak_report"] is True
    assert report["steps"][1]["status"] == "locked_by_prerequisite"
    assert report["steps"][1]["environment"] == "hidden_cdb_host"
    assert report["steps"][1]["evidence_class"] == "approved_hidden_cdb_host_soak"
    assert report["current_step"]["id"] == "short2_menu_idle"
    markdown = ladder.to_markdown(report)
    assert "environment=`hidden_cdb_host`" in markdown


def test_hidden_report_cannot_replace_visible_menu_evidence() -> None:
    hidden = dict(soak_report_fixture(overall=True), environment="hidden_cdb_host",
                  evidence_class="approved_hidden_cdb_host_soak")
    with tempfile.TemporaryDirectory() as directory:
        report = ladder.build_report(args_for(Path(directory), soak=hidden))
    assert report["counts"]["passed"] == 0
    assert not report["steps"][0]["matched_current_soak_report"]
    assert report["current_step"]["requires_explicit_user_approval"] is True
    assert report["current_step"]["preferred_environment"] == "host_visible"


def test_generated_hidden_next_action_aligns_with_the_map_step() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        args = args_for(tmp, soak=soak_report_fixture(overall=True))
        initial = ladder.build_report(args)
        command = initial["current_step"]["recommended_runtime_command"]
        action = {
            "passed": True,
            "next_action": {
                "id": "run_short2_map_idle_soak", "requires_visible_runtime": False,
                "requires_explicit_user_approval": False, "exact_runtime_command": command,
                "plan_verified_execute_command": command,
            },
        }
        write_json(args.next_actions_json, action)
        report = ladder.build_report(args)
    assert report["passed"], report
    alignment = report["next_action_alignment"]
    assert alignment["matches_expected_current_step"] is True
    assert alignment["plan_verified_matches_current_step"] is True
    assert alignment["expected_runtime_command"] == command


def test_plan_alignment_rejects_wrong_executables_and_tampered_hidden_commands() -> None:
    map_step = ladder.SHORT_LADDER_STEPS[1]
    hidden = ladder.hidden_cdb_command_for_step(map_step, execute=True)
    assert hidden is not None
    assert ladder.plan_command_matches_step(hidden, map_step)
    for command in (
        hidden.replace("powershell.exe", "unknown.exe", 1),
        hidden.replace("run_hidden_soak.ps1", "unrelated.ps1"),
        hidden.replace("-DurationSec 120", "-DurationSec 119"),
        hidden.replace("-Execute", ""),
        hidden + " -AllowVisibleRuntime",
        hidden + "; unknown.exe",
    ):
        assert not ladder.plan_command_matches_step(command, map_step), command
    visible = next_actions_fixture()["next_action"]["exact_runtime_command"]
    menu_step = ladder.SHORT_LADDER_STEPS[0]
    assert ladder.plan_command_matches_step(visible, menu_step)
    for command in (
        visible.replace("powershell.exe", "unknown.exe", 1),
        visible.replace("run_hd_soak.ps1", "unrelated.ps1"),
        visible + " -Command unknown.exe",
        visible + "; unknown.exe",
    ):
        assert not ladder.plan_command_matches_step(command, menu_step), command


def test_unknown_and_explicit_null_evidence_bindings_fail_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        source = soak_report_fixture(overall=True)
        assert ladder.soak_report_matches_step(source, ladder.SHORT_LADDER_STEPS[0])
        for environment in (None, "", "unknown", [], {}):
            report = ladder.build_report(args_for(tmp, soak=dict(source, environment=environment)))
            assert not report["passed"], report
            assert report["counts"]["passed"] == 0
        for evidence_class in (None, "", "manual_directinput", "approved_hidden_cdb_host_soak"):
            report = ladder.build_report(args_for(tmp, soak=dict(source, evidence_class=evidence_class)))
            assert not report["passed"], report
        guest = dict(source, route="map-idle", environment="guest_win98_qemu",
                     evidence_class="approved_guest_win98_directdraw")
        assert ladder.soak_report_matches_step(guest, ladder.SHORT_LADDER_STEPS[1])
        guest.pop("evidence_class")
        assert not ladder.soak_report_matches_step(guest, ladder.SHORT_LADDER_STEPS[1])


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
        args = args_for(tmp)
        json_out = tmp / "ladder.json"
        md_out = tmp / "ladder.md"
        script = Path(__file__).resolve().parent / "hd_soak_short_tier_ladder.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--route-coverage-json", str(args.route_coverage_json),
                "--next-actions-json", str(args.next_actions_json),
                "--soak-report-json", str(args.soak_report_json),
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
    test_first_pass_labels_host_environment()
    test_hidden_soak_report_counts_and_labels_environment()
    test_hidden_report_cannot_replace_visible_menu_evidence()
    test_generated_hidden_next_action_aligns_with_the_map_step()
    test_plan_alignment_rejects_wrong_executables_and_tampered_hidden_commands()
    test_unknown_and_explicit_null_evidence_bindings_fail_closed()
    test_missing_harness_route_fails_closed()
    test_mismatched_next_action_fails_for_first_step()
    test_repo_only_triage_next_action_can_replace_runtime_command()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_short_tier_ladder tests passed")
