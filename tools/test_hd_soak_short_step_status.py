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
        for key, value in step.items():
            if key.endswith("_command") and isinstance(value, str):
                step[key] = value.replace("captures\\current\\", str(tmp / "captures" / "current") + "\\")
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
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        report = status.build_report(args_for(tmp, manifest_fixture(tmp)))
    assert report["passed"] is True, report["failures"]
    assert report["ladder_complete"] is False
    assert report["current_step"]["id"] == "short2_menu_idle"
    assert report["current_step"]["status"] == "missing_pending_approval"
    assert report["current_step"]["preferred_environment"] == "host_visible"
    assert report["current_step"]["hidden_cdb_runtime_command"] is None
    assert "-Execute -AllowVisibleRuntime" in report["current_step"]["next_command"]
    assert all(row["status"] == "locked_by_prerequisite" for row in report["steps"][1:])
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
    current = report["current_step"]
    assert current["status"] == "missing_pending_hidden_runtime"
    assert current["preferred_environment"] == "hidden_cdb_host"
    assert current["next_command"] == current["recommended_runtime_command"] == current["hidden_cdb_runtime_command"]
    assert r"scripts\cdb\run_hidden_soak.ps1" in current["next_command"]
    assert "-Execute" in current["next_command"]
    assert "-AllowVisibleRuntime" not in current["next_command"]
    assert "-Execute -AllowVisibleRuntime" in current["visible_runtime_alternative_command"]
    for option, path_key in (("-ReportJson", "report_json"), ("-GuardJson", "guard_json")):
        expected_path = manifest_data["step_reports"][1]["paths"][path_key].replace("/", "\\")
        assert f"{option} {expected_path}" in current["next_command"].replace("/", "\\")


def test_passing_first_step_labels_host_environment() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        manifest_data = manifest_fixture(tmp)
        first = manifest_data["step_reports"][0]
        write_json(Path(first["paths"]["report_json"]), soak_report(first, passed=True))
        write_json(Path(first["paths"]["guard_json"]), guard_report(first, overall=True))
        report = status.build_report(args_for(tmp, manifest_data))
    assert report["passed"] is True, report["failures"]
    assert report["steps"][0]["summary"]["environment"] == "host_visible"


def test_hidden_step_report_counts_and_labels_environment() -> None:
    """A hidden map step follows visible-menu proof and retains its evidence binding."""
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        manifest_data = manifest_fixture(tmp)
        first = manifest_data["step_reports"][0]
        write_json(Path(first["paths"]["report_json"]), soak_report(first, passed=True))
        write_json(Path(first["paths"]["guard_json"]), guard_report(first, overall=True))
        map_step = manifest_data["step_reports"][1]
        hidden = soak_report(map_step, passed=True)
        hidden["environment"] = "hidden_cdb_host"
        hidden["evidence_class"] = "approved_hidden_cdb_host_soak"
        hidden_guard = guard_report(map_step, overall=True)
        hidden_guard.update(environment=hidden["environment"], evidence_class=hidden["evidence_class"])
        write_json(Path(map_step["paths"]["report_json"]), hidden)
        write_json(Path(map_step["paths"]["guard_json"]), hidden_guard)
        report = status.build_report(args_for(tmp, manifest_data))
    assert report["passed"] is True, report["failures"]
    assert report["counts"]["passed"] == 2
    assert report["steps"][1]["passed"] is True
    assert report["steps"][1]["summary"]["environment"] == "hidden_cdb_host"
    assert report["steps"][1]["summary"]["evidence_class"] == "approved_hidden_cdb_host_soak"
    assert report["current_step"]["id"] == "short10_map_idle"
    markdown = status.to_markdown(report)
    assert "environment=`hidden_cdb_host`" in markdown


def test_hidden_report_cannot_replace_visible_menu_evidence() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        manifest_data = manifest_fixture(tmp)
        first = manifest_data["step_reports"][0]
        hidden = dict(soak_report(first, passed=True), environment="hidden_cdb_host",
                      evidence_class="approved_hidden_cdb_host_soak")
        write_json(Path(first["paths"]["report_json"]), hidden)
        report = status.build_report(args_for(tmp, manifest_data))
    assert not report["passed"]
    assert report["counts"]["passed"] == 0
    assert report["current_step"]["status"] == "invalid_report_mismatch"


def test_hidden_guard_and_triage_must_match_canonical_evidence_binding() -> None:
    for artifact_name in ("guard", "triage"):
        for field, mismatched_value in (("environment", "host_visible"), ("evidence_class", "manual_directinput")):
            with tempfile.TemporaryDirectory() as directory:
                tmp = Path(directory)
                manifest_data = manifest_fixture(tmp)
                step = manifest_data["step_reports"][1]
                binding = {"environment": "hidden_cdb_host", "evidence_class": "approved_hidden_cdb_host_soak"}
                source = dict(soak_report(step, passed=False), **binding)
                guard = dict(guard_report(step, overall=False), **binding)
                triage = dict(triage_report(step), **binding)
                (guard if artifact_name == "guard" else triage)[field] = mismatched_value
                write_json(Path(step["paths"]["report_json"]), source)
                write_json(Path(step["paths"]["guard_json"]), guard)
                write_json(Path(step["paths"]["triage_json"]), triage)
                report = status.build_report(args_for(tmp, manifest_data))
            assert not report["passed"], report
            assert report["steps"][1]["status"] == f"invalid_{artifact_name}_mismatch"
            assert any(f"{artifact_name} {field} does not match" in failure for failure in report["failures"])


def test_later_passing_report_stays_locked_without_prerequisites() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        manifest_data = manifest_fixture(tmp)
        step = manifest_data["step_reports"][1]
        binding = {"environment": "hidden_cdb_host", "evidence_class": "approved_hidden_cdb_host_soak"}
        write_json(Path(step["paths"]["report_json"]), dict(soak_report(step, passed=True), **binding))
        write_json(Path(step["paths"]["guard_json"]), dict(guard_report(step, overall=True), **binding))
        report = status.build_report(args_for(tmp, manifest_data))
    assert report["passed"], report
    assert report["counts"]["passed"] == 0
    assert report["steps"][1]["status"] == "locked_by_prerequisite"
    assert report["steps"][1]["summary"]["next_command"] is None
    assert report["current_step"]["id"] == "short2_menu_idle"


def test_evidence_binding_rejects_unknown_or_explicit_null_labels() -> None:
    with tempfile.TemporaryDirectory() as directory:
        step = manifest_fixture(Path(directory))["step_reports"][1]
        source = soak_report(step, passed=True)
        assert status.matches_step(source, step), "absent labels preserve legacy visible reports"
        for environment in (None, "", "unknown", [], {}):
            assert not status.matches_step(dict(source, environment=environment), step)
        for evidence_class in (None, "", "manual_directinput", "approved_hidden_cdb_host_soak"):
            assert not status.matches_step(dict(source, evidence_class=evidence_class), step)
        for environment, evidence_class in (("hidden_cdb_host", "approved_hidden_cdb_host_soak"),
                                            ("guest_win98_qemu", "approved_guest_win98_directdraw")):
            assert status.matches_step(dict(source, environment=environment, evidence_class=evidence_class), step)
            assert not status.matches_step(dict(source, environment=environment), step)


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


def test_apphang_triage_exposes_window_health_rerun_readiness() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        manifest_data = manifest_fixture(tmp)
        first = manifest_data["step_reports"][0]
        triage = triage_report(first)
        triage["classification"] = "application_hang_wer_closed"
        triage["next_probe"] = "generate a fresh tokened windowed retry packet"
        triage["wer_followup"] = {
            "matched": True,
            "status": "application_hang_confirmed_wer_closed",
            "window_health_mitigation_ready": True,
        }
        write_json(Path(first["paths"]["report_json"]), soak_report(first, passed=False))
        write_json(Path(first["paths"]["guard_json"]), guard_report(first, overall=False))
        write_json(Path(first["paths"]["triage_json"]), triage)
        report = status.build_report(args_for(tmp, manifest_data))
    summary = report["steps"][0]["summary"]
    assert report["passed"] is True, report["failures"]
    assert report["current_step"]["status"] == "failed_classified_application_hang_wer_closed"
    assert summary["wer_followup_matched"] is True
    assert summary["wer_followup_status"] == "application_hang_confirmed_wer_closed"
    assert summary["window_health_mitigation_ready"] is True


def test_cli_writes_outputs() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        args = args_for(tmp, manifest_fixture(tmp))
        json_out = tmp / "status.json"
        md_out = tmp / "status.md"
        script = Path(__file__).resolve().parent / "hd_soak_short_step_status.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--manifest-json",
                str(args.manifest_json),
                "--legacy-report-json",
                str(args.legacy_report_json),
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
    test_passing_first_step_labels_host_environment()
    test_hidden_step_report_counts_and_labels_environment()
    test_hidden_report_cannot_replace_visible_menu_evidence()
    test_hidden_guard_and_triage_must_match_canonical_evidence_binding()
    test_later_passing_report_stays_locked_without_prerequisites()
    test_evidence_binding_rejects_unknown_or_explicit_null_labels()
    test_canonical_report_without_guard_fails_closed()
    test_canonical_report_with_mismatched_guard_fails_closed()
    test_failed_report_with_triage_is_classified_status()
    test_failed_report_with_mismatched_triage_fails_closed()
    test_apphang_triage_exposes_window_health_rerun_readiness()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_short_step_status tests passed")
