#!/usr/bin/env python3
"""Fixture tests for hd_soak_report.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import hd_soak_report as soak


def patch_stage_report(candidate_sha: str) -> dict:
    return {
        "stage": soak.PROTECTED_STABLE_STAGE,
        "exe_sha256": candidate_sha,
        "expected_base_sha256": soak.EXPECTED_BASE_SHA256.upper(),
        "patch_count": 2,
        "status_counts": {"patched": 2},
        "current_hd_map_gate": {"passed": True},
    }


def passing_report(tmp: Path) -> dict:
    candidate_sha = "c" * 64
    patch_path = tmp / "patch-stage.json"
    patch_path.write_text(json.dumps(patch_stage_report(candidate_sha)), encoding="ascii")
    return {
        "executed": True,
        "passed": True,
        "failures": [],
        "runtime_policy": "opt-in visible runtime soak; raw frames stay outside the repository by default",
        "stage": soak.PROTECTED_STABLE_STAGE,
        "stable_stage_should_change": False,
        "tier": "short2",
        "route": "menu-idle",
        "duration_sec": 120,
        "sample_interval_sec": 15,
        "input_exe": soak.EXPECTED_INPUT_EXE,
        "candidate": r"C:\ClashTests\hd-soak\clash95_hd_soak_fixture.exe",
        "candidate_sha256": candidate_sha,
        "input_sha256": soak.EXPECTED_BASE_SHA256,
        "patch_stage_report": str(patch_path),
        "workdir": soak.EXPECTED_WORKDIR,
        "output_directory": r"C:\ClashCaptures\hd-soak\fixture",
        "report_json": "captures/current/hd-soak-short-current.json",
        "frame_sample_count": 2,
        "frame_hash_unique_count": 2,
        "frame_progress_expected": False,
        "frame_stability_class": "progressing",
        "final_route_marker": "intro-skip",
        "nonblack_percent_min": 44.5,
        "nonblack_percent_max": 45.0,
        "mean_luma_min": 40.0,
        "mean_luma_max": 41.0,
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
        "input_proof_class": "automated_visible_runtime_diagnostic_not_manual_directinput_release_proof",
        "right_bottom_promotion_blocked": True,
        "route_results": [
            {
                "Name": "intro-skip",
                "PathVerified": True,
                "Click": True,
                "ClickPathVerified": True,
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
                "Hash": "a" * 64,
                "NonblackPercent": 45.0,
                "MeanLuma": 40.0,
                "UniqueSampleColors": 32,
                "NonblackBounds": {"X": 0, "Y": 0, "Right": 799, "Bottom": 599, "Width": 800, "Height": 600},
            },
            {
                "Name": "frame-0001",
                "Timestamp": "2026-06-16T12:01:45.0000000+00:00",
                "Width": 800,
                "Height": 600,
                "Hash": "b" * 64,
                "NonblackPercent": 44.5,
                "MeanLuma": 41.0,
                "UniqueSampleColors": 35,
                "NonblackBounds": {"X": 0, "Y": 0, "Right": 799, "Bottom": 599, "Width": 800, "Height": 600},
            },
        ],
        "capture_errors": [],
    }


def pending_approval_report() -> dict:
    return {
        "executed": False,
        "passed": False,
        "failures": ["short2 menu-idle soak was not executed because visible-runtime escalation was not approved"],
        "runtime_policy": "opt-in visible runtime soak; raw frames stay outside the repository by default",
        "stage": soak.PROTECTED_STABLE_STAGE,
        "stable_stage_should_change": False,
        "tier": "short2",
        "route": "menu-idle",
        "duration_sec": 120,
        "input_exe": soak.EXPECTED_INPUT_EXE,
        "workdir": soak.EXPECTED_WORKDIR,
        "candidate": r"C:\ClashTests\hd-soak\pending-approval.exe",
        "output_directory": r"C:\ClashCaptures\hd-soak\pending-approval",
        "input_proof_class": "not_run_visible_runtime_approval_required_not_manual_directinput_release_proof",
        "right_bottom_promotion_blocked": True,
        "frame_sample_count": 0,
        "frame_hash_unique_count": 0,
        "process_sample_count": 0,
        "clean_stop": False,
    }


def passing_guest_report() -> dict:
    """A clean QEMU-Win98 guest soak report.

    Host-only telemetry is recorded as the not_applicable_guest sentinel, and
    liveness comes from QMP query-status samples plus 800x600 screendump frames.
    """
    candidate_sha = "d" * 64
    return {
        "executed": True,
        "passed": True,
        "failures": [],
        "environment": soak.GUEST_ENVIRONMENT,
        "evidence_class": soak.GUEST_EVIDENCE_CLASS,
        "runtime_policy": "opt-in guest QEMU-Win98 QMP soak; frames captured via screendump",
        "stage": soak.PROTECTED_STABLE_STAGE,
        "stable_stage_should_change": False,
        "tier": "short2",
        "route": "map-idle",
        "duration_sec": 120,
        "sample_interval_sec": 15,
        "input_sha256": soak.EXPECTED_BASE_SHA256,
        "candidate_sha256": candidate_sha,
        "candidate_build_path": r"C:\ClashTests\hd-soak\clash95_hd_guest_fixture.exe",
        "guest_exe_path": r"D:\CLASHHD.EXE",
        "report_json": "captures/current/hd-soak-guest-current.json",
        "frame_sample_count": 2,
        "frame_hash_unique_count": 2,
        "frame_progress_expected": False,
        "frame_stability_class": "progressing",
        "nonblack_percent_min": 44.5,
        "nonblack_percent_max": 45.0,
        "unique_sample_colors_min": 32,
        "unique_sample_colors_max": 35,
        # Host-process telemetry cannot be observed from inside a headless guest.
        "working_set_growth_bytes": soak.NOT_APPLICABLE_GUEST,
        "private_memory_growth_bytes": soak.NOT_APPLICABLE_GUEST,
        "handle_growth": soak.NOT_APPLICABLE_GUEST,
        "exit_code": soak.NOT_APPLICABLE_GUEST,
        "clean_stop": soak.NOT_APPLICABLE_GUEST,
        "max_artifact_mb": 250,
        "artifact_limit_bytes": 250 * 1024 * 1024,
        "artifact_bytes": 234567,
        "guest_status_samples": [
            {"Timestamp": "2026-06-16T12:00:00.0000000+00:00", "Status": "running", "Running": True},
            {"Timestamp": "2026-06-16T12:02:00.0000000+00:00", "Status": "running", "Running": True},
        ],
        "frame_samples": [
            {
                "Name": "frame-0000",
                "Timestamp": "2026-06-16T12:00:00.0000000+00:00",
                "Width": 800,
                "Height": 600,
                "Hash": "a" * 64,
                "NonblackPercent": 45.0,
                "UniqueSampleColors": 32,
                "CaptureMode": "qmp_screendump",
            },
            {
                "Name": "frame-0001",
                "Timestamp": "2026-06-16T12:01:45.0000000+00:00",
                "Width": 800,
                "Height": 600,
                "Hash": "b" * 64,
                "NonblackPercent": 44.5,
                "UniqueSampleColors": 35,
                "CaptureMode": "qmp_screendump",
            },
        ],
        "capture_errors": [],
    }


def passing_hidden_report(tmp: Path) -> dict:
    """A clean hidden-desktop CDB host soak report (environment=hidden_cdb_host).

    The game is a real host process, so all host process telemetry is present
    as real numbers; frames are host ReadProcessMemory surface reads; input
    responsiveness is the not_applicable_hidden sentinel; forced-entry
    mechanics are disclosed via entry_mechanism.
    """
    candidate_sha = "e" * 64
    patch_path = tmp / "patch-stage-hidden.json"
    patch_path.write_text(json.dumps(patch_stage_report(candidate_sha)), encoding="ascii")
    return {
        "executed": True,
        "passed": True,
        "failures": [],
        "environment": soak.HIDDEN_ENVIRONMENT,
        "evidence_class": soak.HIDDEN_EVIDENCE_CLASS,
        "schema": "hidden_cdb_host_soak_report_v1",
        "runtime_policy": "opt-in hidden-desktop CDB host soak; frames read via host ReadProcessMemory",
        "stage": soak.PROTECTED_STABLE_STAGE,
        "stable_stage_should_change": False,
        "tier": "short2",
        "route": "map-idle",
        "duration_sec": 120,
        "sample_interval_sec": 15,
        "input_exe": soak.EXPECTED_INPUT_EXE,
        "workdir": soak.EXPECTED_WORKDIR,
        "candidate": r"C:\ClashTests\hd-soak\clash95_hd_hidden_fixture.exe",
        "candidate_sha256": candidate_sha,
        "input_sha256": soak.EXPECTED_BASE_SHA256,
        "patch_stage_report": str(patch_path),
        "output_directory": r"C:\ClashCaptures\hd-soak\hidden-fixture",
        "report_json": "captures/current/hd-soak-hidden-current.json",
        "input_proof_class": "hidden_cdb_forced_route_diagnostic_not_manual_directinput_release_proof",
        "right_bottom_promotion_blocked": True,
        # Disclosed forcing + honesty sentinel + surface-read provenance.
        "entry_mechanism": soak.HIDDEN_ENTRY_MECHANISM,
        "pan_mechanism": soak.HIDDEN_NO_PAN_MECHANISM,
        "input_responsiveness": soak.NOT_APPLICABLE_HIDDEN,
        "surface_base": "0x00c80000",
        "frame_read_method": soak.HIDDEN_FRAME_READ_METHOD,
        "proxy": {
            "used": True,
            "path": r"C:\ClashTests\hd-soak\ddraw.dll",
            "sha256": "f" * 64,
            "build_manifest": r"C:\ClashTests\hd-soak\ddraw_surfdump_proxy.build.json",
            "log": r"C:\ClashTests\hd-soak\ddraw_surfdump_proxy.log",
            "present_enabled": False,
        },
        "ready_marker": {
            "source": "SOAK_SURFDUMP_READY", "base": "00c80000", "surface": "00d80000",
            "redraw_seq": 1, "width": 800, "height": 600, "bytes": 480000,
        },
        "route_start_marker": {
            "route_ticks": 7680, "pan": 0, "player": 0, "tick": 100,
            "scroll_x": 10, "scroll_y": 10, "game_data": "00600000",
        },
        "route_end_marker": {
            "hits": 128, "tick_delta": 7680, "player": 0, "scroll_x": 10, "scroll_y": 10,
        },
        "pan_events": [],
        "pan_event_count": 0,
        "heartbeat_count": 128,
        "cleanup": {"game_stopped": True, "cdb_stopped": True, "errors": []},
        "frame_sample_count": 2,
        "frame_hash_unique_count": 2,
        "frame_progress_expected": False,
        "frame_stability_class": "progressing",
        "nonblack_percent_min": 44.5,
        "nonblack_percent_max": 45.0,
        "unique_sample_colors_min": 32,
        "unique_sample_colors_max": 35,
        "process_sample_count": 2,
        "working_set_growth_bytes": 1024,
        "private_memory_growth_bytes": 2048,
        "handle_growth": 1,
        "process_exited_unexpectedly": False,
        "exit_code": None,
        "clean_stop": True,
        "max_artifact_mb": 250,
        "artifact_limit_bytes": 250 * 1024 * 1024,
        "artifact_bytes": 345678,
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
                "Hash": "a" * 64,
                "NonblackPercent": 45.0,
                "UniqueSampleColors": 32,
                "CaptureMode": "host_readprocessmemory_surface",
            },
            {
                "Name": "frame-0001",
                "Timestamp": "2026-06-16T12:01:45.0000000+00:00",
                "Width": 800,
                "Height": 600,
                "Hash": "b" * 64,
                "NonblackPercent": 44.5,
                "UniqueSampleColors": 35,
                "CaptureMode": "host_readprocessmemory_surface",
            },
        ],
        "capture_errors": [],
    }


def passing_hidden_pan_report(tmp: Path) -> dict:
    report = passing_hidden_report(tmp)
    report["route"] = "map-pan"
    report["pan_mechanism"] = soak.HIDDEN_PAN_MECHANISM
    report["frame_progress_expected"] = True
    report["route_start_marker"]["pan"] = 1
    report["pan_events"] = [
        {"phase": phase, "x": x, "y": y, "hits": phase + 1, "tick_delta": (phase + 1) * 100}
        for phase, (x, y) in enumerate(((11, 10), (11, 11), (10, 11), (10, 10)))
    ]
    report["pan_event_count"] = len(report["pan_events"])
    return report


def test_hidden_passing_report() -> None:
    with tempfile.TemporaryDirectory() as directory:
        evaluation = soak.evaluate_hidden_report(passing_hidden_report(Path(directory)))
    assert evaluation["overall"] is True, evaluation
    assert evaluation["environment"] == soak.HIDDEN_ENVIRONMENT
    assert evaluation["checks"]["environment"]["passed"] is True
    assert evaluation["checks"]["input_responsiveness"]["passed"] is True
    assert evaluation["checks"]["input_responsiveness"]["summary"]["input_responsiveness"] == soak.NOT_APPLICABLE_HIDDEN
    assert evaluation["checks"]["forced_entry_disclosure"]["passed"] is True
    assert evaluation["checks"]["capture_integrity"]["passed"] is True
    assert evaluation["checks"]["patch_evidence"]["passed"] is True
    assert evaluation["checks"]["process_liveness"]["passed"] is True
    assert evaluation["checks"]["process_growth"]["passed"] is True
    assert evaluation["checks"]["frame_inventory"]["passed"] is True
    assert evaluation["checks"]["render_metrics"]["passed"] is True
    assert evaluation["checks"]["summary_consistency"]["passed"] is True


def test_hidden_markdown_banners_environment_and_disclosures() -> None:
    with tempfile.TemporaryDirectory() as directory:
        evaluation = soak.evaluate_hidden_report(passing_hidden_report(Path(directory)))
    markdown = soak.to_markdown(evaluation)
    assert "HD Hidden-CDB Host Soak Report Guard" in markdown
    assert "ENVIRONMENT: hidden_cdb_host" in markdown
    assert soak.HIDDEN_ENTRY_MECHANISM in markdown
    assert "not_applicable_hidden" in markdown


def test_hidden_faked_input_responsiveness_number_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_hidden_report(Path(directory))
        report["input_responsiveness"] = 1  # a hidden run cannot measure this
        evaluation = soak.evaluate_hidden_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["input_responsiveness"]["passed"] is False
    assert any("fabricated" in failure for failure in evaluation["failures"])
    assert any("not_applicable_hidden" in failure for failure in evaluation["failures"])


def test_hidden_faked_input_responsiveness_true_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_hidden_report(Path(directory))
        report["input_responsiveness"] = True  # claiming responsiveness is also faking
        evaluation = soak.evaluate_hidden_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["input_responsiveness"]["passed"] is False


def test_hidden_dropped_input_responsiveness_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_hidden_report(Path(directory))
        report.pop("input_responsiveness")  # dropping hides the gap; fail closed
        evaluation = soak.evaluate_hidden_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["input_responsiveness"]["passed"] is False
    assert any("dropped" in failure for failure in evaluation["failures"])


def test_hidden_dropped_entry_mechanism_disclosure_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_hidden_report(Path(directory))
        report.pop("entry_mechanism")  # undisclosed forcing is dishonest
        evaluation = soak.evaluate_hidden_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["forced_entry_disclosure"]["passed"] is False
    assert any("entry_mechanism disclosure is missing" in failure for failure in evaluation["failures"])


def test_hidden_map_pan_requires_pan_mechanism_disclosure() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_hidden_pan_report(Path(directory))
        report.pop("pan_mechanism")
        undisclosed = soak.evaluate_hidden_report(report)
        report["pan_mechanism"] = soak.HIDDEN_PAN_MECHANISM
        disclosed = soak.evaluate_hidden_report(report)
    assert undisclosed["overall"] is False
    assert undisclosed["checks"]["forced_entry_disclosure"]["passed"] is False
    assert any("pan_mechanism disclosure is missing" in failure for failure in undisclosed["failures"])
    assert disclosed["overall"] is True, disclosed
    assert disclosed["checks"]["forced_entry_disclosure"]["passed"] is True
    assert disclosed["pan_mechanism"] == soak.HIDDEN_PAN_MECHANISM


def test_hidden_map_pan_requires_frame_progression() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_hidden_pan_report(Path(directory))
        report["frame_hash_unique_count"] = 1
        report["frame_samples"][1]["Hash"] = report["frame_samples"][0]["Hash"]
        evaluation = soak.evaluate_hidden_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["frame_progression"]["passed"] is False
    assert any("frame progression required" in failure for failure in evaluation["failures"])


def test_hidden_claimed_frame_progression_must_match_actual_hashes() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_hidden_report(Path(directory))
        report["frame_hash_unique_count"] = 5  # claimed progression the frames do not show
        evaluation = soak.evaluate_hidden_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["frame_progression"]["passed"] is False
    assert any("unique hashes in frame_samples" in failure for failure in evaluation["failures"])


def test_hidden_host_process_metrics_stay_required() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_hidden_report(Path(directory))
        report.pop("working_set_growth_bytes")
        report.pop("private_memory_growth_bytes")
        report.pop("handle_growth")
        evaluation = soak.evaluate_hidden_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["process_growth"]["passed"] is False
    assert any("working_set_growth_bytes is missing" in failure for failure in evaluation["failures"])

    with tempfile.TemporaryDirectory() as directory:
        report = passing_hidden_report(Path(directory))
        report["working_set_growth_bytes"] = 65 * 1024 * 1024
        report["process_samples"][1]["WorkingSet64"] = report["process_samples"][0]["WorkingSet64"] + 65 * 1024 * 1024
        evaluation = soak.evaluate_hidden_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["process_growth"]["passed"] is False


def test_hidden_process_liveness_stays_required() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_hidden_report(Path(directory))
        report["process_exited_unexpectedly"] = True
        report["exit_code"] = 3221225477
        report["clean_stop"] = False
        evaluation = soak.evaluate_hidden_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["process_liveness"]["passed"] is False
    assert any("unexpectedly" in failure for failure in evaluation["failures"])


def test_hidden_missing_surface_read_provenance_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_hidden_report(Path(directory))
        report.pop("surface_base")
        report["frame_read_method"] = "window_capture"
        evaluation = soak.evaluate_hidden_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["capture_integrity"]["passed"] is False
    assert any("surface_base is missing" in failure for failure in evaluation["failures"])
    assert any("host_readprocessmemory" in failure for failure in evaluation["failures"])


def test_host_report_rejected_by_hidden_grader() -> None:
    """A host visible-runtime soak report can never pass as hidden evidence."""
    with tempfile.TemporaryDirectory() as directory:
        host_report = passing_report(Path(directory))
        evaluation = soak.evaluate_hidden_report(host_report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["environment"]["passed"] is False


def test_hidden_report_rejected_by_guest_grader() -> None:
    """The hidden and guest classes must never be confused with each other."""
    with tempfile.TemporaryDirectory() as directory:
        evaluation = soak.evaluate_guest_report(passing_hidden_report(Path(directory)))
    assert evaluation["overall"] is False
    assert evaluation["checks"]["environment"]["passed"] is False


def test_guest_report_rejected_by_hidden_grader() -> None:
    evaluation = soak.evaluate_hidden_report(passing_guest_report())
    assert evaluation["overall"] is False
    assert evaluation["checks"]["environment"]["passed"] is False


def test_hidden_report_not_accepted_by_host_grader() -> None:
    """The host grader fails a hidden report closed (no route/input rows)."""
    with tempfile.TemporaryDirectory() as directory:
        evaluation = soak.evaluate_report(passing_hidden_report(Path(directory)))
    assert evaluation["overall"] is False
    assert evaluation["checks"]["input_responsiveness"]["passed"] is False


def test_hidden_cli_autodetects_and_gates() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        report_path = tmp / "hidden-report.json"
        report_path.write_text(json.dumps(passing_hidden_report(tmp)), encoding="ascii")
        script = Path(__file__).resolve().parent / "hd_soak_report.py"
        # Auto-detected as hidden via the environment stamp; no --hidden needed.
        pass_result = subprocess.run(
            [sys.executable, str(script), str(report_path), "--require-pass"],
            check=False,
            capture_output=True,
            text=True,
        )
        faked = passing_hidden_report(tmp)
        faked["input_responsiveness"] = 0  # faked numeric responsiveness
        faked_path = tmp / "hidden-faked.json"
        faked_path.write_text(json.dumps(faked), encoding="ascii")
        fail_result = subprocess.run(
            [sys.executable, str(script), str(faked_path), "--require-pass"],
            check=False,
            capture_output=True,
            text=True,
        )
    assert pass_result.returncode == 0, pass_result.stdout + pass_result.stderr
    assert fail_result.returncode == 1, fail_result.stdout + fail_result.stderr


def test_guest_passing_report() -> None:
    evaluation = soak.evaluate_guest_report(passing_guest_report())
    assert evaluation["overall"] is True, evaluation
    assert evaluation["environment"] == soak.GUEST_ENVIRONMENT
    assert evaluation["checks"]["environment"]["passed"] is True
    assert evaluation["checks"]["host_metrics_not_applicable"]["passed"] is True
    assert evaluation["checks"]["guest_liveness"]["passed"] is True
    assert evaluation["checks"]["frame_inventory"]["passed"] is True
    assert evaluation["checks"]["render_metrics"]["passed"] is True
    assert evaluation["checks"]["guest_provenance"]["passed"] is True


def test_guest_faked_working_set_fails() -> None:
    report = passing_guest_report()
    report["working_set_growth_bytes"] = 1024  # a headless guest cannot measure this
    evaluation = soak.evaluate_guest_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["host_metrics_not_applicable"]["passed"] is False
    assert any("working_set_growth_bytes" in failure for failure in evaluation["failures"])
    assert any("not_applicable_guest" in failure for failure in evaluation["failures"])


def test_guest_dropped_host_metric_fails() -> None:
    report = passing_guest_report()
    report.pop("handle_growth")  # dropping is not allowed either
    evaluation = soak.evaluate_guest_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["host_metrics_not_applicable"]["passed"] is False
    assert any("dropped" in failure and "handle_growth" in failure for failure in evaluation["failures"])


def test_guest_missing_environment_label_fails() -> None:
    report = passing_guest_report()
    report.pop("environment")
    evaluation = soak.evaluate_guest_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["environment"]["passed"] is False
    assert any("expected 'guest_win98_qemu'" in failure for failure in evaluation["failures"])


def test_guest_wrong_evidence_class_fails() -> None:
    report = passing_guest_report()
    report["evidence_class"] = "manual_directinput"  # host class must not pass as guest
    evaluation = soak.evaluate_guest_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["environment"]["passed"] is False
    assert any("evidence_class" in failure for failure in evaluation["failures"])


def test_host_report_rejected_by_guest_grader() -> None:
    """A host soak report can never be graded as guest evidence."""
    with tempfile.TemporaryDirectory() as directory:
        host_report = passing_report(Path(directory))
        evaluation = soak.evaluate_guest_report(host_report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["environment"]["passed"] is False


def test_guest_liveness_paused_fails() -> None:
    report = passing_guest_report()
    report["guest_status_samples"][1]["Status"] = "paused"
    report["guest_status_samples"][1]["Running"] = False
    evaluation = soak.evaluate_guest_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["guest_liveness"]["passed"] is False
    assert any("were not 'running'" in failure for failure in evaluation["failures"])


def test_guest_non_hd_frame_size_fails() -> None:
    report = passing_guest_report()
    report["frame_samples"][1]["Width"] = 640
    report["frame_samples"][1]["Height"] = 480
    evaluation = soak.evaluate_guest_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["frame_inventory"]["passed"] is False
    assert any("HD-mode proof size" in failure for failure in evaluation["failures"])


def test_guest_bad_provenance_path_fails() -> None:
    report = passing_guest_report()
    report["candidate_build_path"] = r"D:\CLASHHD.EXE"  # a raw guest path is not provenance
    evaluation = soak.evaluate_guest_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["guest_provenance"]["passed"] is False
    assert any("host-side build provenance" in failure for failure in evaluation["failures"])


def test_guest_render_metrics_fail() -> None:
    report = passing_guest_report()
    report["frame_samples"][1]["NonblackPercent"] = 0.0
    report["frame_samples"][1]["UniqueSampleColors"] = 1
    evaluation = soak.evaluate_guest_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["render_metrics"]["passed"] is False


def test_guest_map_pan_requires_frame_progression() -> None:
    report = passing_guest_report()
    report["route"] = "map-pan"
    report["frame_progress_expected"] = True
    report["frame_hash_unique_count"] = 1
    report["frame_stability_class"] = "stable_idle"
    report["frame_samples"][1]["Hash"] = report["frame_samples"][0]["Hash"]
    evaluation = soak.evaluate_guest_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["frame_progression"]["passed"] is False


def test_guest_cli_autodetects_and_gates() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        report_path = tmp / "guest-report.json"
        report_path.write_text(json.dumps(passing_guest_report()), encoding="ascii")
        script = Path(__file__).resolve().parent / "hd_soak_report.py"
        # Auto-detected as guest via the environment stamp; no --guest needed.
        pass_result = subprocess.run(
            [sys.executable, str(script), str(report_path), "--require-pass"],
            check=False,
            capture_output=True,
            text=True,
        )
        faked = passing_guest_report()
        faked["working_set_growth_bytes"] = 4096
        faked_path = tmp / "guest-faked.json"
        faked_path.write_text(json.dumps(faked), encoding="ascii")
        fail_result = subprocess.run(
            [sys.executable, str(script), str(faked_path), "--require-pass"],
            check=False,
            capture_output=True,
            text=True,
        )
    assert pass_result.returncode == 0, pass_result.stdout + pass_result.stderr
    assert fail_result.returncode == 1, fail_result.stdout + fail_result.stderr


def test_passing_report() -> None:
    with tempfile.TemporaryDirectory() as directory:
        evaluation = soak.evaluate_report(passing_report(Path(directory)))
    assert evaluation["overall"] is True, evaluation
    assert evaluation["checks"]["protected_stage"]["passed"] is True
    assert evaluation["checks"]["patch_evidence"]["passed"] is True
    assert evaluation["checks"]["render_metrics"]["passed"] is True
    assert evaluation["checks"]["visual_anomalies"]["passed"] is True
    assert evaluation["checks"]["route_completion_marker"]["passed"] is True
    assert evaluation["checks"]["promotion_boundary"]["passed"] is True


def test_pending_approval_report_fails_without_runtime_metric_noise() -> None:
    evaluation = soak.evaluate_report(pending_approval_report())
    assert evaluation["overall"] is False
    assert evaluation["failures"] == ["soak report was not produced by an execution run"]
    assert evaluation["checks"]["executed"]["passed"] is False
    assert evaluation["checks"]["patch_evidence"]["passed"] is True
    assert evaluation["checks"]["patch_evidence"]["summary"]["checked"] is False
    assert evaluation["checks"]["frame_inventory"]["passed"] is True
    assert evaluation["checks"]["frame_inventory"]["summary"]["checked"] is False
    assert evaluation["checks"]["render_metrics"]["passed"] is True
    assert evaluation["checks"]["render_metrics"]["summary"]["checked"] is False
    assert evaluation["checks"]["visual_anomalies"]["passed"] is True
    assert evaluation["checks"]["visual_anomalies"]["summary"]["checked"] is False
    assert evaluation["checks"]["process_liveness"]["passed"] is True
    assert evaluation["checks"]["process_liveness"]["summary"]["checked"] is False
    assert evaluation["checks"]["process_growth"]["passed"] is True
    assert evaluation["checks"]["process_growth"]["summary"]["checked"] is False
    assert not any("frame sample count" in failure for failure in evaluation["failures"])
    assert not any("working_set_growth_bytes" in failure for failure in evaluation["failures"])


def test_unexpected_exit_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["process_exited_unexpectedly"] = True
        report["exit_code"] = 3221225477
        report["clean_stop"] = False
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["process_liveness"]["passed"] is False
    assert any("unexpectedly" in failure for failure in evaluation["failures"])


def test_source_report_failures_fail_even_when_metrics_look_good() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["passed"] = False
        report["failures"] = ["script error after route sampling"]
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["source_status"]["passed"] is False
    assert any("source soak report did not mark itself passed" in failure for failure in evaluation["failures"])
    assert any("source soak report contains" in failure for failure in evaluation["failures"])


def test_repo_artifacts_fail() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["candidate"] = str(soak.REPO_ROOT / "clash95_hd_bad.exe")
        report["output_directory"] = str(soak.REPO_ROOT / "captures" / "current" / "raw-soak")
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["artifact_locations"]["passed"] is False


def test_noncanonical_soak_roots_fail() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["input_exe"] = r"C:\ClashTests\base\clash95.exe"
        report["workdir"] = r"C:\ClashTests\base"
        report["candidate"] = r"C:\ClashTests\other\clash95_hd_soak_fixture.exe"
        report["output_directory"] = r"C:\ClashDumps\hd-soak\fixture"
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["artifact_locations"]["passed"] is False
    assert any("input_exe is not" in failure for failure in evaluation["failures"])
    assert any("workdir is not" in failure for failure in evaluation["failures"])
    assert any("candidate path is not under" in failure for failure in evaluation["failures"])
    assert any("raw output directory is not under" in failure for failure in evaluation["failures"])


def test_render_metrics_fail() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["frame_samples"][1]["NonblackPercent"] = 0.0
        report["frame_samples"][1]["UniqueSampleColors"] = 1
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["render_metrics"]["passed"] is False
    assert evaluation["checks"]["visual_anomalies"]["passed"] is False
    assert any("black/blank patch risk" in failure for failure in evaluation["failures"])
    assert any("palette/stripe risk" in failure for failure in evaluation["failures"])


def test_minority_capture_mode_frame_is_not_render_evidence() -> None:
    """A black frame from a different capture path is a capture defect.

    Reproduces the 2026-07-18 short2 run: seven healthy window-DC frames plus
    one 'screen' frame that came back black. The black frame must not set the
    render minima, and the run must fail as a capture inconsistency rather than
    a render/palette regression.
    """
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        healthy = report["frame_samples"][0]
        for frame in report["frame_samples"]:
            frame["CaptureMode"] = "windowdc-contaminated-fallback"
        outlier = dict(healthy)
        outlier.update(
            {
                "Name": "frame-0002",
                "Timestamp": "2026-06-16T12:01:55.0000000+00:00",
                "Hash": "c" * 64,
                "CaptureMode": "screen",
                "NonblackPercent": 0.017,
                "MeanLuma": 0.035,
                "UniqueSampleColors": 6,
            }
        )
        report["frame_samples"].append(outlier)
        evaluation = soak.evaluate_report(report)

    render = evaluation["checks"]["render_metrics"]
    assert render["passed"] is True, render
    assert render["summary"]["min_nonblack_percent"] == 44.5
    assert render["summary"]["excluded_frame_count"] == 1
    assert evaluation["checks"]["visual_anomalies"]["passed"] is True
    capture = evaluation["checks"]["capture_consistency"]
    assert capture["passed"] is False
    assert any("capture mode changed mid-run" in failure for failure in evaluation["failures"])
    assert not any("black/blank patch risk" in failure for failure in evaluation["failures"])


def test_uniform_capture_mode_still_reports_render_regression() -> None:
    """The partition must not become a way to hide a real black-screen run."""
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        for frame in report["frame_samples"]:
            frame["CaptureMode"] = "screen"
        report["frame_samples"][1]["NonblackPercent"] = 0.0
        report["frame_samples"][1]["UniqueSampleColors"] = 1
        evaluation = soak.evaluate_report(report)
    assert evaluation["checks"]["capture_consistency"]["passed"] is True
    assert evaluation["checks"]["render_metrics"]["passed"] is False
    assert any("black/blank patch risk" in failure for failure in evaluation["failures"])


def test_harness_stamped_non_evidence_frame_is_excluded() -> None:
    """A frame the harness stamped as post-teardown is not render evidence."""
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        teardown = dict(report["frame_samples"][0])
        teardown.update(
            {
                "Name": "frame-0002",
                "Timestamp": "2026-06-16T12:02:30.0000000+00:00",
                "Hash": "d" * 64,
                "NonblackPercent": 0.0,
                "UniqueSampleColors": 1,
                "RenderEvidence": False,
                "RenderEvidenceExcludedReasons": ["captured_after_stop_signal"],
            }
        )
        report["frame_samples"].append(teardown)
        evaluation = soak.evaluate_report(report)
    assert evaluation["checks"]["render_metrics"]["passed"] is True
    assert evaluation["checks"]["render_metrics"]["summary"]["excluded_frame_count"] == 1
    assert evaluation["checks"]["visual_anomalies"]["passed"] is True


def test_missing_nonblack_bounds_fail_visual_anomaly_check() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["frame_samples"][0].pop("NonblackBounds")
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["visual_anomalies"]["passed"] is False
    assert any("NonblackBounds" in failure for failure in evaluation["failures"])


def test_capture_errors_fail() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["capture_errors"] = [{"Frame": "frame-0001", "Error": "capture failed"}]
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["capture_integrity"]["passed"] is False
    assert any("capture_errors contains" in failure for failure in evaluation["failures"])


def test_tier_route_duration_fail() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["tier"] = "short2"
        report["duration_sec"] = 30
        report["route"] = "bad-route"
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["tier_route"]["passed"] is False
    assert any("short2 duration_sec" in failure for failure in evaluation["failures"])
    assert any("unknown route" in failure for failure in evaluation["failures"])


def test_frame_hash_inventory_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["frame_samples"][1]["Hash"] = "not-a-sha"
        report["frame_hash_unique_count"] = 1
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["frame_inventory"]["passed"] is False
    assert any("invalid SHA-256 hashes" in failure for failure in evaluation["failures"])


def test_stable_idle_frames_pass_for_menu_idle() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["frame_hash_unique_count"] = 1
        report["frame_progress_expected"] = False
        report["frame_stability_class"] = "stable_idle"
        report["frame_samples"][1]["Hash"] = report["frame_samples"][0]["Hash"]
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is True, evaluation
    assert evaluation["checks"]["frame_progression"]["passed"] is True
    assert evaluation["checks"]["frame_progression"]["summary"]["frame_stability_class"] == "stable_idle"


def test_map_pan_requires_frame_progression() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["route"] = "map-pan"
        report["frame_hash_unique_count"] = 1
        report["frame_progress_expected"] = True
        report["frame_stability_class"] = "stable_idle"
        report["frame_samples"][1]["Hash"] = report["frame_samples"][0]["Hash"]
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["frame_progression"]["passed"] is False
    assert any("frame progression required" in failure for failure in evaluation["failures"])


def test_patch_manifest_mismatch_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        report = passing_report(tmp)
        patch_path = tmp / "patch-stage.json"
        payload = patch_stage_report(report["candidate_sha256"])
        payload["status_counts"] = {"patched": 1, "original": 1}
        payload["current_hd_map_gate"] = {"passed": False}
        patch_path.write_text(json.dumps(payload), encoding="ascii")
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["patch_evidence"]["passed"] is False
    assert any("current_hd_map_gate" in failure for failure in evaluation["failures"])


def test_missing_patch_manifest_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["patch_stage_report"] = str(Path(directory) / "missing.json")
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["patch_evidence"]["passed"] is False
    assert any("patch_stage_report does not exist" in failure for failure in evaluation["failures"])


def test_process_growth_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["working_set_growth_bytes"] = 65 * 1024 * 1024
        report["private_memory_growth_bytes"] = 66 * 1024 * 1024
        report["handle_growth"] = 129
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["process_growth"]["passed"] is False
    assert any("working_set_growth_bytes" in failure for failure in evaluation["failures"])
    assert any("private_memory_growth_bytes" in failure for failure in evaluation["failures"])
    assert any("handle_growth" in failure for failure in evaluation["failures"])


def test_artifact_budget_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["artifact_bytes"] = (250 * 1024 * 1024) + 1
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["artifact_budget"]["passed"] is False
    assert any("artifact bytes" in failure for failure in evaluation["failures"])

    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report.pop("max_artifact_mb")
        report.pop("artifact_limit_bytes")
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["artifact_budget"]["passed"] is False
    assert any("max_artifact_mb is missing" in failure for failure in evaluation["failures"])
    assert any("artifact_limit_bytes is missing" in failure for failure in evaluation["failures"])

    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["artifact_limit_bytes"] = 1
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["artifact_budget"]["passed"] is False
    assert any("max_artifact_mb-derived limit" in failure for failure in evaluation["failures"])


def test_process_sample_exit_state_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["process_samples"][1]["HasExited"] = True
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["process_liveness"]["passed"] is False
    assert any("HasExited=True" in failure for failure in evaluation["failures"])


def test_missing_sample_interval_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report.pop("sample_interval_sec")
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["elapsed_coverage"]["passed"] is False
    assert any("sample_interval_sec is missing" in failure for failure in evaluation["failures"])


def test_elapsed_sample_coverage_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["frame_samples"][1]["Timestamp"] = "2026-06-16T12:00:10.0000000+00:00"
        report["process_samples"][1]["Timestamp"] = "2026-06-16T12:00:10.0000000+00:00"
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["elapsed_coverage"]["passed"] is False
    assert any("frame sample elapsed coverage" in failure for failure in evaluation["failures"])
    assert any("process sample elapsed coverage" in failure for failure in evaluation["failures"])


def test_missing_process_growth_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report.pop("working_set_growth_bytes")
        report.pop("private_memory_growth_bytes")
        report.pop("handle_growth")
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["process_growth"]["passed"] is False
    assert any("working_set_growth_bytes is missing" in failure for failure in evaluation["failures"])


def test_input_drift_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["input_max_abs_error"] = 3
        report["input_max_sample_abs_error"] = 3
        report["route_results"][0]["MaxAbsError"] = 3
        report["route_results"][0]["MaxSampleAbsError"] = 3
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["input_responsiveness"]["passed"] is False
    assert any("drift limit" in failure for failure in evaluation["failures"])


def test_intro_transition_stop_accepts_only_post_click_drift() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        row = report["route_results"][0]
        row["ClickPathVerified"] = False
        row["MaxSampleAbsError"] = 298
        row["ClickRepeatObserved"] = 7
        row["TransitionStopObserved"] = True
        row["RepeatStopReasons"] = ["sample_drift_after_click"]
        report["input_max_sample_abs_error"] = 298
        evaluation = soak.evaluate_report(report)
        row["PathVerified"] = False
        rejected = soak.evaluate_report(report)
    assert evaluation["checks"]["input_responsiveness"]["passed"] is True, evaluation
    assert rejected["checks"]["input_responsiveness"]["passed"] is False, rejected


def test_probe_exit_code_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["route_results"][0]["ProbeExitCode"] = 1
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["input_responsiveness"]["passed"] is False
    assert any("bad probe exit codes" in failure for failure in evaluation["failures"])


def test_missing_input_drift_metrics_fail() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["route_results"][0].pop("MaxAbsError")
        report["route_results"][0].pop("MaxSampleAbsError")
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["input_responsiveness"]["passed"] is False
    assert any("omitted drift metrics" in failure for failure in evaluation["failures"])


def test_empty_route_inventory_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["route_results"] = []
        report["final_route_marker"] = "menu-idle"
        report["input_max_abs_error"] = None
        report["input_max_sample_abs_error"] = None
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["input_responsiveness"]["passed"] is False
    assert evaluation["checks"]["route_completion_marker"]["passed"] is False
    assert any("route/input row inventory is empty" in failure for failure in evaluation["failures"])
    assert any("without route/input rows" in failure for failure in evaluation["failures"])


def test_final_route_marker_mismatch_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["final_route_marker"] = "load-button"
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["route_completion_marker"]["passed"] is False
    assert any("final_route_marker" in failure for failure in evaluation["failures"])


def test_summary_metric_mismatch_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["frame_sample_count"] = 3
        report["frame_hash_unique_count"] = 1
        report["nonblack_percent_min"] = 0.0
        report["process_sample_count"] = 3
        report["working_set_growth_bytes"] = 999
        report["input_max_abs_error"] = 0
        report["mean_luma_min"] = 1.0
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["summary_consistency"]["passed"] is False
    assert any("frame_sample_count summary" in failure for failure in evaluation["failures"])
    assert any("working_set_growth_bytes summary" in failure for failure in evaluation["failures"])
    assert any("input_max_abs_error summary" in failure for failure in evaluation["failures"])
    assert any("mean_luma_min summary" in failure for failure in evaluation["failures"])


def test_cli_honors_max_input_drift_argument() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        report = passing_report(tmp)
        report["input_max_abs_error"] = 2
        report["input_max_sample_abs_error"] = 2
        report["route_results"][0]["MaxAbsError"] = 2
        report["route_results"][0]["MaxSampleAbsError"] = 2
        report_path = tmp / "report.json"
        report_path.write_text(json.dumps(report), encoding="ascii")
        script = Path(__file__).resolve().parent / "hd_soak_report.py"
        fail_result = subprocess.run(
            [sys.executable, str(script), str(report_path), "--max-input-drift-px", "1", "--require-pass"],
            check=False,
            capture_output=True,
            text=True,
        )
        pass_result = subprocess.run(
            [sys.executable, str(script), str(report_path), "--max-input-drift-px", "2", "--require-pass"],
            check=False,
            capture_output=True,
            text=True,
        )
    assert fail_result.returncode == 1, fail_result.stdout + fail_result.stderr
    assert pass_result.returncode == 0, pass_result.stdout + pass_result.stderr


def test_environment_dispatch_preserves_distinct_proof_classes() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        host = passing_report(tmp)
        assert "environment" not in host and "schema" not in host
        reports = (
            (host, soak.HOST_ENVIRONMENT),
            (dict(host, environment=soak.HOST_ENVIRONMENT, evidence_class=soak.HOST_EVIDENCE_CLASS), soak.HOST_ENVIRONMENT),
            (passing_guest_report(), soak.GUEST_ENVIRONMENT),
            (passing_hidden_report(tmp), soak.HIDDEN_ENVIRONMENT),
            (passing_hidden_pan_report(tmp), soak.HIDDEN_ENVIRONMENT),
        )
        for report, environment in reports:
            before = json.dumps(report)
            evaluation = soak.evaluate_report_for_environment(report)
            assert evaluation["overall"], evaluation
            assert evaluation["expected_environment"] == environment
            assert evaluation["checks"]["environment"]["passed"]
            assert json.dumps(report) == before, "dispatcher must not relabel evidence"
        hidden = reports[-1][0]
        assert not soak.evaluate_report(hidden)["checks"]["environment"]["passed"]
        assert not soak.evaluate_guest_report(hidden)["checks"]["environment"]["passed"]
        assert not soak.evaluate_report(passing_guest_report())["checks"]["environment"]["passed"]


def test_dispatch_rejects_unknown_labels_and_foreign_unlabeled_classes() -> None:
    with tempfile.TemporaryDirectory() as directory:
        host = passing_report(Path(directory))
        for environment in ("unknown", "", None, 17, [], {}):
            report = dict(host, environment=environment)
            evaluation = soak.evaluate_report_for_environment(report)
            assert not evaluation["overall"], evaluation
            assert not evaluation["checks"]["environment"]["passed"]
            assert "unsupported soak environment" in evaluation["failures"][0]
            assert not soak.evaluate_report(report)["checks"]["environment"]["passed"]
        for evidence_class in (soak.GUEST_EVIDENCE_CLASS, soak.HIDDEN_EVIDENCE_CLASS, "manual_directinput", None):
            evaluation = soak.evaluate_report_for_environment(dict(host, evidence_class=evidence_class))
            assert not evaluation["overall"], evaluation
            assert not evaluation["checks"]["environment"]["passed"]
        evaluation = soak.evaluate_report_for_environment(dict(host, schema="hidden_cdb_host_soak_report_v1"))
        assert not evaluation["checks"]["environment"]["passed"]


def test_dispatch_forwards_every_applicable_threshold() -> None:
    common = {
        "min_frames": 5, "min_nonblack_percent": 20.0, "min_unique_sample_colors": 9,
        "max_artifact_mb": 90, "expected_width": 1024, "expected_height": 768,
    }
    host_process = {
        "max_working_set_growth_mb": 21, "max_private_memory_growth_mb": 22, "max_handle_growth": 23,
    }
    supplied = dict(common, **host_process, max_input_drift_px=4, min_guest_status_samples=6)
    for environment, grader, expected in (
        (soak.HOST_ENVIRONMENT, "evaluate_report", dict(common, **host_process, max_input_drift_px=4)),
        (soak.HIDDEN_ENVIRONMENT, "evaluate_hidden_report", dict(common, **host_process)),
        (soak.GUEST_ENVIRONMENT, "evaluate_guest_report", dict(common, min_guest_status_samples=6)),
    ):
        report = {"environment": environment}
        with patch.object(soak, grader, return_value={"grader": grader}) as grading:
            result = soak.evaluate_report_for_environment(report, **supplied)
        assert result == {"grader": grader}
        grading.assert_called_once_with(report, **expected)


def test_dispatch_thresholds_change_actual_grading() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        for report in (passing_report(tmp), passing_hidden_report(tmp), passing_guest_report()):
            strict = soak.evaluate_report_for_environment(report, min_frames=3, min_nonblack_percent=46.0)
            assert not strict["checks"]["frame_inventory"]["passed"]
            assert not strict["checks"]["render_metrics"]["passed"]
        for report in (passing_report(tmp), passing_hidden_report(tmp)):
            strict = soak.evaluate_report_for_environment(report, max_handle_growth=0)
            assert not strict["checks"]["process_growth"]["passed"]
        strict_host = soak.evaluate_report_for_environment(passing_report(tmp), max_input_drift_px=0)
        assert not strict_host["checks"]["input_responsiveness"]["passed"]
        strict_guest = soak.evaluate_report_for_environment(passing_guest_report(), min_guest_status_samples=3)
        assert not strict_guest["checks"]["guest_liveness"]["passed"]


def test_hidden_missing_structured_provenance_fails_closed() -> None:
    fields = {
        "schema": "schema", "proxy": "wrapper_provenance", "ready_marker": "marker_provenance",
        "route_start_marker": "marker_provenance", "route_end_marker": "marker_provenance",
        "pan_events": "marker_provenance", "heartbeat_count": "marker_provenance",
        "cleanup": "cleanup_provenance",
    }
    with tempfile.TemporaryDirectory() as directory:
        for field, check in fields.items():
            report = passing_hidden_report(Path(directory))
            report.pop(field)
            # Legacy success booleans cannot stand in for parsed observation rows.
            report.update(ready_observed=True, soak_route_start_observed=True, soak_route_end_observed=True)
            evaluation = soak.evaluate_report_for_environment(report)
            assert not evaluation["overall"], (field, evaluation)
            assert not evaluation["checks"][check]["passed"], (field, evaluation)


def test_hidden_contradictory_provenance_fails_closed() -> None:
    mutations = (
        ("wrapper_provenance", lambda r: r["proxy"].update(present_enabled=True)),
        ("wrapper_provenance", lambda r: r["proxy"].update(sha256="invalid")),
        ("marker_provenance", lambda r: r["ready_marker"].update(base="00c90000")),
        ("marker_provenance", lambda r: r["route_end_marker"].update(tick_delta=1)),
        ("marker_provenance", lambda r: r["pan_events"][0].update(x=100)),
        ("cleanup_provenance", lambda r: r["cleanup"].update(cdb_stopped=False)),
        ("forced_entry_disclosure", lambda r: r.update(entry_mechanism="natural_input")),
        ("forced_entry_disclosure", lambda r: r.update(pan_mechanism="none")),
    )
    with tempfile.TemporaryDirectory() as directory:
        for check, mutate in mutations:
            report = passing_hidden_pan_report(Path(directory))
            mutate(report)
            evaluation = soak.evaluate_report_for_environment(report)
            assert not evaluation["overall"], (check, evaluation)
            assert not evaluation["checks"][check]["passed"], (check, evaluation)


def test_map_pan_cannot_disable_frame_progression_in_any_environment() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        for report in (passing_report(tmp), passing_guest_report(), passing_hidden_pan_report(tmp)):
            report["route"] = "map-pan"
            report["frame_progress_expected"] = False
            report["frame_stability_class"] = "stable_idle"
            report["frame_hash_unique_count"] = 1
            report["frame_samples"][1]["Hash"] = report["frame_samples"][0]["Hash"]
            evaluation = soak.evaluate_report_for_environment(report)
            assert not evaluation["checks"]["frame_progression"]["passed"], evaluation


def test_cli_rejects_unknown_and_contradictory_environment_selection() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        report_path = tmp / "report.json"
        script = Path(__file__).resolve().parent / "hd_soak_report.py"
        command = [sys.executable, str(script), str(report_path), "--require-pass"]
        hidden = passing_hidden_report(tmp)
        report_path.write_text(json.dumps(hidden), encoding="ascii")
        wrong_lane = subprocess.run(command + ["--guest"], capture_output=True, text=True, check=False)
        assert wrong_lane.returncode == 1, wrong_lane.stdout + wrong_lane.stderr
        assert "expected 'guest_win98_qemu'" in wrong_lane.stdout
        both_lanes = subprocess.run(command + ["--guest", "--hidden"], capture_output=True, text=True, check=False)
        assert both_lanes.returncode == 2, both_lanes.stdout + both_lanes.stderr
        host = dict(passing_report(tmp), environment="unsupported")
        report_path.write_text(json.dumps(host), encoding="ascii")
        unsupported = subprocess.run(command, capture_output=True, text=True, check=False)
        assert unsupported.returncode == 1, unsupported.stdout + unsupported.stderr
        assert "unsupported soak environment" in unsupported.stdout


def run_tests() -> None:
    test_environment_dispatch_preserves_distinct_proof_classes()
    test_dispatch_rejects_unknown_labels_and_foreign_unlabeled_classes()
    test_dispatch_forwards_every_applicable_threshold()
    test_dispatch_thresholds_change_actual_grading()
    test_hidden_missing_structured_provenance_fails_closed()
    test_hidden_contradictory_provenance_fails_closed()
    test_map_pan_cannot_disable_frame_progression_in_any_environment()
    test_cli_rejects_unknown_and_contradictory_environment_selection()
    test_hidden_passing_report()
    test_hidden_markdown_banners_environment_and_disclosures()
    test_hidden_faked_input_responsiveness_number_fails()
    test_hidden_faked_input_responsiveness_true_fails()
    test_hidden_dropped_input_responsiveness_fails()
    test_hidden_dropped_entry_mechanism_disclosure_fails()
    test_hidden_map_pan_requires_pan_mechanism_disclosure()
    test_hidden_map_pan_requires_frame_progression()
    test_hidden_claimed_frame_progression_must_match_actual_hashes()
    test_hidden_host_process_metrics_stay_required()
    test_hidden_process_liveness_stays_required()
    test_hidden_missing_surface_read_provenance_fails()
    test_host_report_rejected_by_hidden_grader()
    test_hidden_report_rejected_by_guest_grader()
    test_guest_report_rejected_by_hidden_grader()
    test_hidden_report_not_accepted_by_host_grader()
    test_hidden_cli_autodetects_and_gates()
    test_guest_passing_report()
    test_guest_faked_working_set_fails()
    test_guest_dropped_host_metric_fails()
    test_guest_missing_environment_label_fails()
    test_guest_wrong_evidence_class_fails()
    test_host_report_rejected_by_guest_grader()
    test_guest_liveness_paused_fails()
    test_guest_non_hd_frame_size_fails()
    test_guest_bad_provenance_path_fails()
    test_guest_render_metrics_fail()
    test_guest_map_pan_requires_frame_progression()
    test_guest_cli_autodetects_and_gates()
    test_passing_report()
    test_pending_approval_report_fails_without_runtime_metric_noise()
    test_unexpected_exit_fails()
    test_source_report_failures_fail_even_when_metrics_look_good()
    test_repo_artifacts_fail()
    test_noncanonical_soak_roots_fail()
    test_render_metrics_fail()
    test_minority_capture_mode_frame_is_not_render_evidence()
    test_uniform_capture_mode_still_reports_render_regression()
    test_harness_stamped_non_evidence_frame_is_excluded()
    test_missing_nonblack_bounds_fail_visual_anomaly_check()
    test_capture_errors_fail()
    test_tier_route_duration_fail()
    test_frame_hash_inventory_fails()
    test_stable_idle_frames_pass_for_menu_idle()
    test_map_pan_requires_frame_progression()
    test_patch_manifest_mismatch_fails()
    test_missing_patch_manifest_fails()
    test_process_growth_fails()
    test_artifact_budget_fails()
    test_process_sample_exit_state_fails()
    test_missing_sample_interval_fails()
    test_elapsed_sample_coverage_fails()
    test_missing_process_growth_fails()
    test_input_drift_fails()
    test_intro_transition_stop_accepts_only_post_click_drift()
    test_probe_exit_code_fails()
    test_missing_input_drift_metrics_fail()
    test_empty_route_inventory_fails()
    test_final_route_marker_mismatch_fails()
    test_summary_metric_mismatch_fails()
    test_cli_honors_max_input_drift_argument()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_report tests passed")
