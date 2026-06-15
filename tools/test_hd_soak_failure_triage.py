#!/usr/bin/env python3
"""Fixture tests for hd_soak_failure_triage.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import hd_soak_failure_triage as triage
import hd_soak_report


def base_report() -> dict[str, Any]:
    return {
        "generated_at": "2026-06-15T20:15:44+02:00",
        "executed": True,
        "passed": False,
        "failures": [],
        "tier": "short2",
        "duration_sec": 120,
        "route": "menu-idle",
        "final_route_marker": "intro-skip",
        "stage": hd_soak_report.PROTECTED_STABLE_STAGE,
        "candidate": r"C:\ClashTests\hd-soak\fixture.exe",
        "candidate_sha256": "a" * 64,
        "output_directory": r"C:\ClashCaptures\hd-soak\fixture",
        "report_json": "captures/current/hd-soak-short-current.json",
        "frame_sample_count": 2,
        "frame_hash_unique_count": 2,
        "nonblack_percent_min": 44.0,
        "nonblack_percent_max": 45.0,
        "mean_luma_min": 40.0,
        "mean_luma_max": 42.0,
        "unique_sample_colors_min": 32,
        "unique_sample_colors_max": 35,
        "process_sample_count": 2,
        "working_set_growth_bytes": 1024,
        "handle_growth": 1,
        "artifact_bytes": 123456,
        "process_exited_unexpectedly": False,
        "exit_code": None,
        "clean_stop": True,
        "route_results": [
            {
                "Name": "intro-skip",
                "Points": "400,300",
                "Click": True,
                "PathVerified": True,
                "ClickPathVerified": True,
                "ProbeExitCode": 0,
            }
        ],
        "process_samples": [
            {"Timestamp": "t0", "HasExited": False, "WorkingSet64": 1000, "HandleCount": 10},
            {"Timestamp": "t1", "HasExited": False, "WorkingSet64": 2024, "HandleCount": 11},
        ],
        "frame_samples": [
            {
                "Name": "frame-0000",
                "Timestamp": "t0",
                "Width": 800,
                "Height": 600,
                "Hash": "b" * 64,
                "NonblackPercent": 44.0,
                "MeanLuma": 40.0,
                "UniqueSampleColors": 32,
                "CaptureMode": "screen",
            },
            {
                "Name": "frame-0001",
                "Timestamp": "t1",
                "Width": 800,
                "Height": 600,
                "Hash": "c" * 64,
                "NonblackPercent": 45.0,
                "MeanLuma": 42.0,
                "UniqueSampleColors": 35,
                "CaptureMode": "screen",
            },
        ],
        "capture_errors": [],
    }


def test_pending_approval_classification() -> None:
    report = base_report()
    report["executed"] = False
    report["passed"] = False
    report["execution_blocked_reason"] = "visible-runtime run requires explicit user approval"
    report["failures"] = ["short2 menu-idle soak was not executed because visible-runtime escalation was not approved"]
    result = triage.build_triage(report)
    assert result["passed"] is False
    assert result["classification"] == "not_executed_pending_approval"
    assert "explicit approval" in result["next_probe"]


def test_av_crash_classification() -> None:
    report = base_report()
    report["process_exited_unexpectedly"] = True
    report["exit_code"] = 3221225477
    report["clean_stop"] = False
    report["failures"] = ["process exited unexpectedly with code 3221225477"]
    result = triage.build_triage(report)
    assert result["classification"] == "crash_av"
    assert "CDB" in result["next_probe"]


def test_render_regression_classification() -> None:
    report = base_report()
    report["failures"] = [
        "nonblack percent dropped below 10.0",
        "unique sampled colors dropped below 8",
    ]
    result = triage.build_triage(report)
    assert result["classification"] == "render_or_palette_regression"
    assert result["last_frame_sample"]["name"] == "frame-0001"


def test_input_route_failure_classification() -> None:
    report = base_report()
    report["failures"] = ["route/input probe failures: 1"]
    report["route_results"][0]["PathVerified"] = False
    result = triage.build_triage(report)
    assert result["classification"] == "input_route_failure"
    assert result["last_route_result"]["path_verified"] is False


def test_passing_run_classification() -> None:
    report = base_report()
    report["passed"] = True
    result = triage.build_triage(report)
    assert result["passed"] is True
    assert result["classification"] == "passing_run_no_failure"


def test_cli_writes_outputs_and_fails_for_failed_report() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        report_path = tmp / "report.json"
        json_out = tmp / "triage.json"
        md_out = tmp / "triage.md"
        report = base_report()
        report["failures"] = ["capture errors: 1"]
        report_path.write_text(json.dumps(report), encoding="ascii")
        script = Path(__file__).resolve().parent / "hd_soak_failure_triage.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                str(report_path),
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
        assert result.returncode == 1, result.stdout + result.stderr
        assert json_out.exists()
        assert md_out.exists()
        payload = json.loads(json_out.read_text(encoding="ascii"))
        assert payload["classification"] == "capture_harness_failure"


def run_tests() -> None:
    test_pending_approval_classification()
    test_av_crash_classification()
    test_render_regression_classification()
    test_input_route_failure_classification()
    test_passing_run_classification()
    test_cli_writes_outputs_and_fails_for_failed_report()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_failure_triage tests passed")
