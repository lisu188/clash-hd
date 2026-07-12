#!/usr/bin/env python3
"""Fixture tests for hd_soak_short_step_status.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import hd_soak_short_artifact_manifest as manifest
import hd_soak_short_step_status as status


def write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="ascii")
    return path


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
        step["safe_dry_run_command"] = step["safe_dry_run_command"].replace(
            "captures\\current\\", str(tmp / "captures" / "current") + "\\"
        )
        step["approval_gated_runtime_command"] = step["approval_gated_runtime_command"].replace(
            "captures\\current\\", str(tmp / "captures" / "current") + "\\"
        )
        step["guard_command"] = step["guard_command"].replace(
            "captures\\current\\", str(tmp / "captures" / "current") + "\\"
        )
        step["triage_command"] = step["triage_command"].replace(
            "captures\\current\\", str(tmp / "captures" / "current") + "\\"
        )
    return report


def soak_report(step: dict[str, Any], *, passed: bool, executed: bool = True) -> dict[str, Any]:
    return {
        "report_json": step["paths"]["report_json"],
        "executed": executed,
        "passed": passed,
        "stage": status.PROTECTED_STABLE_STAGE,
        "tier": step["tier"],
        "route": step["route"],
        "duration_sec": step["duration_sec"],
        "frame_sample_count": 3 if passed else 0,
        "final_route_marker": "complete" if passed else "failed",
        "candidate_sha256": "abc123" if passed else None,
        "failures": [] if passed else ["frame sample count 0 is below 2"],
    }


def guard_report(step: dict[str, Any], *, overall: bool) -> dict[str, Any]:
    return {
        "overall": overall,
        "source_report": step["paths"]["report_json"],
        "stage": status.PROTECTED_STABLE_STAGE,
        "tier": step["tier"],
        "route": step["route"],
        "failures": [] if overall else ["frame sample count 0 is below 2"],
    }


def triage_report(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "passed": False,
        "source_report": step["paths"]["report_json"],
        "classification": "hang_or_no_frame_progress",
        "next_probe": "inspect process samples",
        "visual_anomalies": {
            "passed": False,
            "black_patch_risk_count": 1,
            "palette_or_stripe_risk_count": 0,
            "missing_nonblack_bounds_count": 0,
        },
        "stage": status.PROTECTED_STABLE_STAGE,
        "tier": step["tier"],
        "route": step["route"],
    }


def args_for(tmp: Path, manifest_data: dict[str, Any], legacy_data: dict[str, Any] | None = None) -> argparse.Namespace:
    manifest_path = write_json(tmp / "manifest.json", manifest_data)
    legacy_path = tmp / "legacy.json"
    if legacy_data is not None:
        write_json(legacy_path, legacy_data)
    return argparse.Namespace(manifest_json=manifest_path, legacy_report_json=legacy_path)


def test_current_pending_status_passes() -> None:
    report = status.build_report(
        argparse.Namespace(
            manifest_json=status.DEFAULT_MANIFEST_JSON,
            legacy_report_json=status.DEFAULT_LEGACY_REPORT_JSON,
        )
    )
    assert report["passed"] is True, report["failures"]
    assert report["ladder_complete"] is False
    assert report["current_step"]["id"] == "short2_map_idle"
    current_status = report["current_step"]["status"]
    assert current_status in {
        "pending_approval_legacy_compat",
        "missing_pending_approval",
    } or current_status.startswith("failed_classified_")
    assert report["locks"]["right_bottom_promotion_blocked"] is True


def test_passing_first_step_advances_current_step() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        manifest_data = manifest_fixture(tmp)
        first = manifest_data["step_reports"][0]
        write_json(Path(first["paths"]["report_json"]), soak_report(first, passed=True))
        write_json(Path(first["paths"]["guard_json"]), guard_report(first, overall=True))
        report = status.build_report(args_for(tmp, manifest_data))
    assert report["passed"] is True, report["failures"]
    assert report["counts"]["passed"] == 1
    assert report["current_step"]["id"] == "short2_map_idle"
    assert report["current_step"]["status"] == "missing_pending_approval"


def test_canonical_report_without_guard_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        manifest_data = manifest_fixture(tmp)
        first = manifest_data["step_reports"][0]
        write_json(Path(first["paths"]["report_json"]), soak_report(first, passed=True))
        report = status.build_report(args_for(tmp, manifest_data))
    assert report["passed"] is False
    assert report["current_step"]["status"] == "needs_guard"
    assert any("no guard output" in failure for failure in report["failures"])


def test_canonical_report_with_mismatched_guard_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        manifest_data = manifest_fixture(tmp)
        first = manifest_data["step_reports"][0]
        guard = guard_report(first, overall=True)
        guard["source_report"] = str(tmp / "captures" / "current" / "wrong-report.json")
        write_json(Path(first["paths"]["report_json"]), soak_report(first, passed=True))
        write_json(Path(first["paths"]["guard_json"]), guard)
        report = status.build_report(args_for(tmp, manifest_data))
    assert report["passed"] is False
    assert report["current_step"]["status"] == "invalid_guard_mismatch"
    assert any("guard source_report does not match" in failure for failure in report["failures"])


def test_failed_report_with_triage_is_classified_status() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        manifest_data = manifest_fixture(tmp)
        first = manifest_data["step_reports"][0]
        write_json(Path(first["paths"]["report_json"]), soak_report(first, passed=False))
        write_json(Path(first["paths"]["guard_json"]), guard_report(first, overall=False))
        write_json(Path(first["paths"]["triage_json"]), triage_report(first))
        report = status.build_report(args_for(tmp, manifest_data))
    assert report["passed"] is True, report["failures"]
    assert report["current_step"]["id"] == "short2_menu_idle"
    assert report["current_step"]["status"] == "failed_classified_hang_or_no_frame_progress"
    summary = report["steps"][0]["summary"]
    assert summary["visual_anomaly_passed"] is False
    assert summary["black_patch_risk_count"] == 1
    assert summary["palette_or_stripe_risk_count"] == 0
    assert summary["missing_nonblack_bounds_count"] == 0


def test_failed_report_with_mismatched_triage_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        manifest_data = manifest_fixture(tmp)
        first = manifest_data["step_reports"][0]
        triage = triage_report(first)
        triage["route"] = "map-idle"
        write_json(Path(first["paths"]["report_json"]), soak_report(first, passed=False))
        write_json(Path(first["paths"]["guard_json"]), guard_report(first, overall=False))
        write_json(Path(first["paths"]["triage_json"]), triage)
        report = status.build_report(args_for(tmp, manifest_data))
    assert report["passed"] is False
    assert report["current_step"]["status"] == "invalid_triage_mismatch"
    assert any("triage route does not match" in failure for failure in report["failures"])


def test_cli_writes_outputs() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        json_out = tmp / "status.json"
        md_out = tmp / "status.md"
        script = Path(__file__).resolve().parent / "hd_soak_short_step_status.py"
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
    test_current_pending_status_passes()
    test_passing_first_step_advances_current_step()
    test_canonical_report_without_guard_fails_closed()
    test_canonical_report_with_mismatched_guard_fails_closed()
    test_failed_report_with_triage_is_classified_status()
    test_failed_report_with_mismatched_triage_fails_closed()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_short_step_status tests passed")
