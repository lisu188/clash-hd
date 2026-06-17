#!/usr/bin/env python3
"""Fixture tests for hd_soak_report.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

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


def run_tests() -> None:
    test_passing_report()
    test_pending_approval_report_fails_without_runtime_metric_noise()
    test_unexpected_exit_fails()
    test_source_report_failures_fail_even_when_metrics_look_good()
    test_repo_artifacts_fail()
    test_noncanonical_soak_roots_fail()
    test_render_metrics_fail()
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
    test_probe_exit_code_fails()
    test_missing_input_drift_metrics_fail()
    test_empty_route_inventory_fails()
    test_final_route_marker_mismatch_fails()
    test_summary_metric_mismatch_fails()
    test_cli_honors_max_input_drift_argument()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_report tests passed")
