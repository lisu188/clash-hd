#!/usr/bin/env python3
"""Fixture tests for hd_soak_short_validation_refresh.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import hd_soak_report
import hd_soak_short_artifact_manifest as manifest
import hd_soak_short_validation_refresh as refresh


def write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="ascii")
    return path


def write_patch_stage_fixture(path: Path, candidate_sha: str) -> Path:
    return write_json(
        path,
        {
            "stage": hd_soak_report.PROTECTED_STABLE_STAGE,
            "exe_sha256": candidate_sha,
            "expected_base_sha256": hd_soak_report.EXPECTED_BASE_SHA256.upper(),
            "patch_count": 2,
            "status_counts": {"patched": 2},
            "current_hd_map_gate": {"passed": True},
        },
    )


def manifest_fixture(tmp: Path) -> dict[str, Any]:
    report = manifest.build_report(
        argparse.Namespace(
            legacy_report_json=tmp / "captures" / "current" / "hd-soak-short-current.json",
            legacy_report_md=tmp / "captures" / "current" / "hd-soak-short-current.md",
        )
    )
    for step in report["step_reports"]:
        for key, value in step["paths"].items():
            step["paths"][key] = str(tmp / value.replace("\\", "/"))
    return report


def soak_report(step: dict[str, Any], *, passed: bool) -> dict[str, Any]:
    failures = [] if passed else ["route/input probe failures: 1"]
    route_verified = bool(passed)
    candidate_sha = "a" * 64
    report_path = Path(step["paths"]["report_json"])
    patch_stage_path = write_patch_stage_fixture(report_path.parent / f"{step['id']}-patch-stage.json", candidate_sha)
    return {
        "report_json": step["paths"]["report_json"],
        "generated_at": "2026-06-15T20:15:44+02:00",
        "executed": True,
        "passed": passed,
        "failures": failures,
        "tier": step["tier"],
        "duration_sec": step["duration_sec"],
        "sample_interval_sec": 15,
        "route": step["route"],
        "final_route_marker": "menu-idle",
        "stage": hd_soak_report.PROTECTED_STABLE_STAGE,
        "stable_stage_should_change": False,
        "runtime_policy": "opt-in visible-runtime soak harness fixture",
        "input_proof_class": "diagnostic_not_manual_release_proof",
        "right_bottom_promotion_blocked": True,
        "input_exe": hd_soak_report.EXPECTED_INPUT_EXE,
        "input_sha256": hd_soak_report.EXPECTED_BASE_SHA256,
        "candidate": r"C:\ClashTests\hd-soak\fixture.exe",
        "candidate_sha256": candidate_sha,
        "patch_stage_report": str(patch_stage_path),
        "workdir": hd_soak_report.EXPECTED_WORKDIR,
        "output_directory": r"C:\ClashCaptures\hd-soak\fixture",
        "frame_sample_count": 2,
        "frame_hash_unique_count": 2,
        "frame_progress_expected": step["route"] == "map-pan",
        "frame_stability_class": "progressing",
        "nonblack_percent_min": 44.0,
        "nonblack_percent_max": 45.0,
        "mean_luma_min": 40.0,
        "mean_luma_max": 42.0,
        "unique_sample_colors_min": 32,
        "unique_sample_colors_max": 35,
        "input_max_abs_error": 1,
        "input_max_sample_abs_error": 1,
        "max_input_drift_px": 1,
        "process_sample_count": 2,
        "working_set_growth_bytes": 1024,
        "private_memory_growth_bytes": 2048,
        "handle_growth": 1,
        "max_artifact_mb": 250,
        "artifact_limit_bytes": 250 * 1024 * 1024,
        "artifact_bytes": 123456,
        "process_exited_unexpectedly": False,
        "exit_code": None,
        "clean_stop": True,
        "route_results": [
            {
                "Name": "menu-idle",
                "Points": "400,300",
                "Click": True,
                "PathVerified": route_verified,
                "ClickPathVerified": route_verified,
                "MaxAbsError": 1,
                "MaxSampleAbsError": 1,
                "ClickEventCount": 1,
                "ProbeExitCode": 0,
            }
        ],
        "process_samples": [
            {
                "Timestamp": "2026-06-16T12:00:00.0000000+00:00",
                "HasExited": False,
                "WorkingSet64": 1000,
                "PrivateMemorySize64": 2000,
                "HandleCount": 10,
            },
            {
                "Timestamp": "2026-06-16T12:02:00.0000000+00:00",
                "HasExited": False,
                "WorkingSet64": 2024,
                "PrivateMemorySize64": 4048,
                "HandleCount": 11,
            },
        ],
        "frame_samples": [
            {
                "Name": "frame-0000",
                "Timestamp": "2026-06-16T12:00:00.0000000+00:00",
                "Width": 800,
                "Height": 600,
                "Hash": "b" * 64,
                "NonblackPercent": 44.0,
                "MeanLuma": 40.0,
                "UniqueSampleColors": 32,
                "CaptureMode": "screen",
                "NonblackBounds": {"X": 0, "Y": 0, "Right": 799, "Bottom": 599, "Width": 800, "Height": 600},
            },
            {
                "Name": "frame-0001",
                "Timestamp": "2026-06-16T12:01:45.0000000+00:00",
                "Width": 800,
                "Height": 600,
                "Hash": "c" * 64,
                "NonblackPercent": 45.0,
                "MeanLuma": 42.0,
                "UniqueSampleColors": 35,
                "CaptureMode": "screen",
                "NonblackBounds": {"X": 0, "Y": 0, "Right": 799, "Bottom": 599, "Width": 800, "Height": 600},
            },
        ],
        "capture_errors": [],
    }


def args_for(tmp: Path, manifest_data: dict[str, Any]) -> argparse.Namespace:
    return argparse.Namespace(manifest_json=write_json(tmp / "manifest.json", manifest_data))


def test_no_reports_is_pending_and_passes() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        report = refresh.build_report(args_for(tmp, manifest_fixture(tmp)))
    assert report["passed"] is True, report["failures"]
    assert report["status"] == "pending_no_reports"
    assert report["counts"]["reports_found"] == 0
    assert report["counts"]["guards_written"] == 0


def test_passing_report_writes_guard_and_triage() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        manifest_data = manifest_fixture(tmp)
        first = manifest_data["step_reports"][0]
        write_json(Path(first["paths"]["report_json"]), soak_report(first, passed=True))
        report = refresh.build_report(args_for(tmp, manifest_data))
        guard = json.loads(Path(first["paths"]["guard_json"]).read_text(encoding="ascii"))
        triage = json.loads(Path(first["paths"]["triage_json"]).read_text(encoding="ascii"))
    assert report["passed"] is True, report["failures"]
    assert report["counts"]["reports_found"] == 1
    assert report["steps"][0]["status"] == "validated_pass"
    assert guard["overall"] is True
    assert triage["classification"] == "passing_run_no_failure"


def test_failed_report_writes_guard_and_classified_triage() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        manifest_data = manifest_fixture(tmp)
        first = manifest_data["step_reports"][0]
        write_json(Path(first["paths"]["report_json"]), soak_report(first, passed=False))
        report = refresh.build_report(args_for(tmp, manifest_data))
        guard = json.loads(Path(first["paths"]["guard_json"]).read_text(encoding="ascii"))
        triage = json.loads(Path(first["paths"]["triage_json"]).read_text(encoding="ascii"))
    assert report["passed"] is True, report["failures"]
    assert report["steps"][0]["status"] == "validated_failed"
    assert guard["overall"] is False
    assert triage["classification"] == "input_route_failure"


def test_mismatched_report_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        manifest_data = manifest_fixture(tmp)
        first = manifest_data["step_reports"][0]
        payload = soak_report(first, passed=True)
        payload["route"] = "map-idle"
        write_json(Path(first["paths"]["report_json"]), payload)
        report = refresh.build_report(args_for(tmp, manifest_data))
    assert report["passed"] is False
    assert report["steps"][0]["status"] == "report_mismatch"
    assert any("does not match expected" in failure for failure in report["failures"])


def test_missing_manifest_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = refresh.build_report(argparse.Namespace(manifest_json=Path(directory) / "missing.json"))
    assert report["passed"] is False
    assert report["status"] == "missing_manifest"


def test_cli_writes_outputs() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        manifest_data = manifest_fixture(tmp)
        manifest_path = write_json(tmp / "manifest.json", manifest_data)
        json_out = tmp / "refresh.json"
        md_out = tmp / "refresh.md"
        script = Path(__file__).resolve().parent / "hd_soak_short_validation_refresh.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--manifest-json",
                str(manifest_path),
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
    test_no_reports_is_pending_and_passes()
    test_passing_report_writes_guard_and_triage()
    test_failed_report_writes_guard_and_classified_triage()
    test_mismatched_report_fails_closed()
    test_missing_manifest_fails_closed()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_short_validation_refresh tests passed")
