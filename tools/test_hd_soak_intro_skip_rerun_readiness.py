#!/usr/bin/env python3
"""Fixture tests for hd_soak_intro_skip_rerun_readiness.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import hd_soak_intro_skip_rerun_readiness as readiness


def write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="ascii")
    return path


def command() -> str:
    return (
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
        r"'scripts\smoke\run_hd_soak.ps1' "
        "-Tier 'short2' -Route 'menu-idle' "
        "-IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' "
        "-MaxInputDriftPx '1' -Execute -AllowVisibleRuntime -RequirePass -Json"
    )


def reports() -> dict[str, dict[str, Any]]:
    return {
        "triage": {
            "passed": False,
            "classification": readiness.EXPECTED_CLASSIFICATION,
            "final_route_marker": "intro-skip",
            "executed": True,
            "candidate_sha256": "a" * 64,
            "next_probe": "fix or verify intro-skip harness input mode before rerunning",
        },
        "step_status": {
            "passed": True,
            "current_step": {
                "id": readiness.EXPECTED_STEP_ID,
                "status": readiness.EXPECTED_STEP_STATUS,
            },
        },
        "harness_guard": {
            "passed": True,
            "checks": {
                "intro_skip_policy": {"passed": True},
                "visible_runtime_opt_in": {"passed": True},
                "protected_stage_boundary": {"passed": True},
            },
        },
        "dry_run_plan": {
            "passed": True,
            "status": "ready_for_explicit_approval",
            "current_step": {"id": readiness.EXPECTED_STEP_ID},
            "approval_gated_execute_command": command(),
            "plan": {
                "stable_stage_should_change": False,
                "right_bottom_promotion_blocked": True,
                "candidate_path": r"C:\ClashTests\hd-soak\candidate.exe",
                "output_root": r"C:\ClashCaptures\hd-soak",
                "intro_skip": dict(readiness.EXPECTED_INTRO_SKIP),
            },
        },
        "visible_runtime_guard": {"passed": True},
        "process_hygiene": {"passed": True, "matching_process_count": 0},
        "exe_artifact": {"passed": True, "tracked_exes": []},
    }


def args_for(tmp: Path, data: dict[str, dict[str, Any]]) -> argparse.Namespace:
    return argparse.Namespace(
        triage_json=write_json(tmp / "triage.json", data["triage"]),
        step_status_json=write_json(tmp / "step-status.json", data["step_status"]),
        harness_guard_json=write_json(tmp / "harness-guard.json", data["harness_guard"]),
        dry_run_plan_json=write_json(tmp / "dry-run-plan.json", data["dry_run_plan"]),
        visible_runtime_guard_json=write_json(tmp / "visible-runtime-guard.json", data["visible_runtime_guard"]),
        process_hygiene_json=write_json(tmp / "process-hygiene.json", data["process_hygiene"]),
        exe_artifact_json=write_json(tmp / "exe-artifact.json", data["exe_artifact"]),
    )


def build_fixture_report(data: dict[str, dict[str, Any]]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        return readiness.build_report(args_for(Path(directory), data))


def test_ready_packet_passes() -> None:
    report = build_fixture_report(reports())
    assert report["passed"] is True, report["failures"]
    assert report["status"] == "ready_for_explicit_visible_rerun_approval"
    assert report["intro_skip_contract"]["click_mode"] == "postmessage"
    assert "visible Clash95 game window" in report["approval_boundary"]
    assert "-AllowVisibleRuntime" in report["dry_run_plan"]["approval_gated_execute_command"]


def test_rejects_wrong_triage_classification() -> None:
    data = reports()
    data["triage"]["classification"] = "unexpected_process_exit"
    report = build_fixture_report(data)
    assert report["passed"] is False
    assert any("triage classification" in failure for failure in report["failures"])


def test_rejects_intro_skip_command_drift() -> None:
    data = reports()
    data["dry_run_plan"]["approval_gated_execute_command"] = command().replace(
        "-IntroSkipClickMode 'postmessage' ",
        "",
    )
    data["dry_run_plan"]["plan"]["intro_skip"]["click_mode"] = "sendinput"
    report = build_fixture_report(data)
    assert report["passed"] is False
    assert any("approval command missing fragment: -IntroSkipClickMode" in failure for failure in report["failures"])
    assert any("dry-run intro_skip click_mode" in failure for failure in report["failures"])


def test_cli_writes_outputs() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        data = reports()
        args = args_for(tmp, data)
        out_json = tmp / "readiness.json"
        out_md = tmp / "readiness.md"
        script = Path(__file__).resolve().parent / "hd_soak_intro_skip_rerun_readiness.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--triage-json",
                str(args.triage_json),
                "--step-status-json",
                str(args.step_status_json),
                "--harness-guard-json",
                str(args.harness_guard_json),
                "--dry-run-plan-json",
                str(args.dry_run_plan_json),
                "--visible-runtime-guard-json",
                str(args.visible_runtime_guard_json),
                "--process-hygiene-json",
                str(args.process_hygiene_json),
                "--exe-artifact-json",
                str(args.exe_artifact_json),
                "--write-json",
                str(out_json),
                "--write-markdown",
                str(out_md),
                "--require-pass",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(out_json.read_text(encoding="ascii"))["passed"] is True
        assert "Intro-Skip Rerun Readiness" in out_md.read_text(encoding="ascii")


def run_tests() -> None:
    test_ready_packet_passes()
    test_rejects_wrong_triage_classification()
    test_rejects_intro_skip_command_drift()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_intro_skip_rerun_readiness tests passed")
