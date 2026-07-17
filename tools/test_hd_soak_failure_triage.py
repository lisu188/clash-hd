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
        "runtime_policy": "opt-in visible runtime soak; raw frames stay outside the repository by default",
        "input_proof_class": "diagnostic_not_manual_release_proof",
        "right_bottom_promotion_blocked": True,
        "stable_stage_should_change": False,
        "tier": "short2",
        "duration_sec": 120,
        "sample_interval_sec": 15,
        "route": "menu-idle",
        "final_route_marker": "intro-skip",
        "stage": hd_soak_report.PROTECTED_STABLE_STAGE,
        "input_exe": hd_soak_report.EXPECTED_INPUT_EXE,
        "input_sha256": hd_soak_report.EXPECTED_BASE_SHA256,
        "candidate": r"C:\ClashTests\hd-soak\fixture.exe",
        "candidate_sha256": "a" * 64,
        "workdir": hd_soak_report.EXPECTED_WORKDIR,
        "output_directory": r"C:\ClashCaptures\hd-soak\fixture",
        "report_json": "captures/current/hd-soak-short-current.json",
        "frame_sample_count": 2,
        "frame_hash_unique_count": 2,
        "frame_progress_expected": False,
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
                "Name": "intro-skip",
                "Points": "400,300",
                "Click": True,
                "PathVerified": True,
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


def patch_stage_report(candidate_sha: str) -> dict[str, Any]:
    return {
        "stage": hd_soak_report.PROTECTED_STABLE_STAGE,
        "expected_base_sha256": hd_soak_report.EXPECTED_BASE_SHA256,
        "exe_sha256": candidate_sha,
        "patch_count": 2,
        "status_counts": {"patched": 2, "original": 0, "unexpected": 0},
        "current_hd_map_gate": {"passed": True},
    }


def attach_passing_guard_report(report: dict[str, Any], tmp: Path) -> None:
    patch_path = tmp / "patch-stage.json"
    patch_path.write_text(json.dumps(patch_stage_report(report["candidate_sha256"])), encoding="ascii")
    report["patch_stage_report"] = str(patch_path)


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


def test_unexpected_process_exit_classification() -> None:
    report = base_report()
    report["process_exited_unexpectedly"] = True
    report["exit_code"] = 1
    report["clean_stop"] = False
    report["failures"] = ["process exited unexpectedly with code 1"]
    result = triage.build_triage(report)
    assert result["classification"] == "unexpected_process_exit"
    assert result["exit_code"] == 1
    assert "CDB crash logging" in result["next_probe"]


def test_matching_hidden_cdb_followup_advances_unexpected_exit_probe() -> None:
    report = base_report()
    report["process_exited_unexpectedly"] = True
    report["exit_code"] = 1
    report["clean_stop"] = False
    report["failures"] = ["process exited unexpectedly with code 1"]
    followup = {
        "passed": True,
        "status": "cdb_exit_not_reproduced_hidden_memory_proxy",
        "candidate_sha256": report["candidate_sha256"],
        "stage": report["stage"],
        "route": report["route"],
        "hidden_desktop": True,
        "presentation": {"proxy_present_enabled": False},
        "route_evidence": {"gameplay_observed": True},
        "observation": {
            "post_dump_observation_completed": True,
            "post_dump_exit_observed": False,
            "access_violation_observed": False,
            "app_request_quit_observed": False,
        },
    }
    result = triage.build_triage(report, cdb_followup=followup)
    assert result["passed"] is False
    assert result["classification"] == "unexpected_process_exit"
    assert result["cdb_followup"]["matched"] is True
    assert "application/windowed wrapper" in result["next_probe"]
    followup["candidate_sha256"] = "b" * 64
    mismatch = triage.build_triage(report, cdb_followup=followup)
    assert mismatch["cdb_followup"]["matched"] is False
    assert "CDB crash logging" in mismatch["next_probe"]


def test_matching_wer_followup_classifies_os_closed_application_hang() -> None:
    report = base_report()
    report["process_exited_unexpectedly"] = True
    report["exit_code"] = 1
    report["clean_stop"] = False
    report["failures"] = ["process exited unexpectedly with code 1"]
    followup = {
        "passed": True,
        "status": "application_hang_confirmed_wer_closed",
        "candidate_sha256": report["candidate_sha256"],
        "stage": report["stage"],
        "route": report["route"],
        "event_evidence": {
            "event_name": "AppHangB1",
            "application_hang_1002_count": 1,
            "wer_apphang_1001_count": 2,
            "application_error_1000_count": 0,
            "windows_closed_nonresponsive_application": True,
        },
        "timeline_correlation": {
            "candidate_name_matches": True,
            "event_within_failed_run_window": True,
        },
    }
    result = triage.build_triage(report, wer_followup=followup)
    assert result["passed"] is False
    assert result["classification"] == "application_hang_wer_closed"
    assert result["wer_followup"]["matched"] is True
    assert result["wer_followup"]["window_health_mitigation_ready"] is False
    assert "window responsiveness" in result["next_probe"]
    followup["mitigation"] = {
        "window_health_instrumentation_added": True,
        "harness_guard_path": "captures/current/hd-soak-harness-guard-current.json",
        "harness_guard_passed": True,
        "window_health_stop_check_passed": True,
    }
    mitigated = triage.build_triage(report, wer_followup=followup)
    assert mitigated["wer_followup"]["window_health_mitigation_ready"] is True
    assert "fresh tokened" in mitigated["next_probe"]
    followup["event_evidence"]["event_name"] = "APPCRASH"
    mismatch = triage.build_triage(report, wer_followup=followup)
    assert mismatch["classification"] == "unexpected_process_exit"
    assert mismatch["wer_followup"]["matched"] is False


def test_runtime_window_health_classifies_hang_before_generic_exit() -> None:
    report = base_report()
    report["process_exited_unexpectedly"] = True
    report["exit_code"] = 1
    report["clean_stop"] = False
    report["window_hang_observed"] = True
    report["window_health_samples"] = [
        {"Phase": "after-load-button-wait", "HealthClass": "application_hung"}
    ]
    report["failures"] = [
        "application window became nonresponsive during the soak route",
        "process exited unexpectedly with code 1",
    ]
    result = triage.build_triage(report)
    assert result["classification"] == "application_hang_detected"
    assert "window_health_samples" in result["next_probe"]


def test_intro_skip_input_drift_exit_classification() -> None:
    report = base_report()
    report["process_exited_unexpectedly"] = True
    report["exit_code"] = 1
    report["clean_stop"] = False
    report["frame_sample_count"] = 1
    report["input_max_sample_abs_error"] = 324
    report["failures"] = [
        "process exited unexpectedly with code 1",
        "route/input probe failures: 1",
        "input drift exceeded 1px or metric missing: 1",
    ]
    report["route_results"][0]["ClickPathVerified"] = False
    report["route_results"][0]["MaxSampleAbsError"] = 324
    report["route_results"][0]["ClickMode"] = "sendinput"
    report["route_results"][0]["ClickRepeat"] = 1
    result = triage.build_triage(report)
    assert result["classification"] == "intro_skip_input_drift_exit"
    assert "postmessage" in result["next_probe"]
    assert result["last_route_marker"] == "intro-skip"
    assert result["failure_context"]["last_route_marker"] == "intro-skip"
    assert result["failure_context"]["failure_timestamp"] == "2026-06-16T12:02:00.0000000+00:00"
    assert result["failure_context"]["failure_timestamp_source"] == "last_process_sample"
    assert result["failure_context"]["crash_hang_class"] == "intro_skip_input_drift_exit"
    assert result["last_route_result"]["click_mode"] == "sendinput"


def test_intro_skip_probe_json_enriches_missing_route_mode() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        probe_path = tmp / "intro-skip.json"
        probe_path.write_text(
            json.dumps(
                {
                    "points": {
                        "move_mode": "auto",
                        "move_method": "setcursor",
                        "samples": [
                            {
                                "phase": "after_move",
                                "screen_error": [0, 0],
                                "client_error": [0, 0],
                            }
                        ],
                        "clicks": [
                            {
                                "mode": "sendinput",
                                "events": [
                                    {
                                        "phase": "after_sendinput_down",
                                        "screen_error": [-324, 133],
                                        "client_error": [-324, 133],
                                    }
                                ],
                            }
                        ],
                    }
                }
            ),
            encoding="ascii",
        )
        report = base_report()
        report["process_exited_unexpectedly"] = True
        report["exit_code"] = 1
        report["clean_stop"] = False
        report["frame_sample_count"] = 1
        report["input_max_sample_abs_error"] = 324
        report["failures"] = [
            "process exited unexpectedly with code 1",
            "route/input probe failures: 1",
            "input drift exceeded 1px or metric missing: 1",
        ]
        report["route_results"][0]["ClickPathVerified"] = False
        report["route_results"][0]["MaxSampleAbsError"] = 324
        report["route_results"][0]["Json"] = str(probe_path)
        result = triage.build_triage(report)

    route = result["last_route_result"]
    assert result["classification"] == "intro_skip_input_drift_exit"
    assert result["next_probe"].startswith("previous intro-skip click used sendinput")
    assert route["click_mode"] == "sendinput"
    assert route["click_mode_source"] == "probe_json"
    assert route["move_mode"] == "auto"
    assert route["probe_json"]["read_status"] == "ok"
    assert route["probe_json"]["max_sample_abs_error"] == 324
    assert route["probe_json"]["max_sample_phase"] == "after_sendinput_down"


def test_later_no_window_probe_preserves_intro_skip_exit_classification() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        load_log = tmp / "route-load-button.log"
        load_log.write_text(
            "TimeoutError: no visible window found for pid 24184\n",
            encoding="ascii",
        )
        report = base_report()
        report["route"] = "map-idle"
        report["final_route_marker"] = "load-button"
        report["process_exited_unexpectedly"] = True
        report["exit_code"] = 1
        report["clean_stop"] = False
        report["frame_sample_count"] = 0
        report["input_max_sample_abs_error"] = 311
        report["failures"] = [
            "process exited unexpectedly with code 1",
            "route/input probe failures: 2",
            "input drift exceeded 1px or metric missing: 2",
        ]
        report["route_results"][0]["ClickPathVerified"] = False
        report["route_results"][0]["MaxSampleAbsError"] = 311
        report["route_results"][0]["ClickMode"] = "postmessage"
        report["route_results"][0]["ClickRepeat"] = 8
        report["route_results"].append(
            {
                "Name": "load-button",
                "Points": "300,218",
                "Click": True,
                "PathVerified": False,
                "ClickPathVerified": False,
                "ProbeExitCode": 1,
                "Log": str(load_log),
            }
        )
        result = triage.build_triage(report)

    assert result["classification"] == "intro_skip_input_drift_exit"
    assert result["last_route_marker"] == "load-button"
    assert result["intro_skip_route_result"]["click_mode"] == "postmessage"
    assert "stop or reacquire" in result["next_probe"]
    load_row = result["probe_log_diagnostics"]["rows"][1]
    assert load_row["signals"] == ["no_visible_process_window"]


def test_render_regression_classification() -> None:
    report = base_report()
    report["failures"] = [
        "nonblack percent dropped below 10.0",
        "unique sampled colors dropped below 8",
    ]
    result = triage.build_triage(report)
    assert result["classification"] == "render_or_palette_regression"
    assert result["last_frame_sample"]["name"] == "frame-0001"


def test_visual_anomaly_summary_records_black_and_stripe_risk() -> None:
    report = base_report()
    report["failures"] = [
        "black/blank patch risk",
        "palette/stripe risk",
    ]
    report["frame_samples"][1]["NonblackPercent"] = 0.0
    report["frame_samples"][1]["UniqueSampleColors"] = 1
    result = triage.build_triage(report)

    visual = result["visual_anomalies"]
    assert result["classification"] == "render_or_palette_regression"
    assert visual["passed"] is False
    assert visual["black_patch_risk_count"] == 1
    assert visual["palette_or_stripe_risk_count"] == 1
    assert visual["missing_nonblack_bounds_count"] == 0
    assert visual["anomaly_rows"][0]["name"] == "frame-0001"
    assert result["failure_context"]["black_patch_risk_count"] == 1
    assert result["failure_context"]["palette_or_stripe_risk_count"] == 1


def test_input_route_failure_classification() -> None:
    report = base_report()
    report["failures"] = ["route/input probe failures: 1"]
    report["route_results"][0]["PathVerified"] = False
    result = triage.build_triage(report)
    assert result["classification"] == "input_route_failure"
    assert result["last_route_result"]["path_verified"] is False


def test_input_drift_failure_classification() -> None:
    report = base_report()
    report["failures"] = ["input drift exceeded 1px or metric missing: 1"]
    report["input_max_abs_error"] = 4
    report["input_max_sample_abs_error"] = 4
    report["route_results"][0]["MaxAbsError"] = 4
    report["route_results"][0]["MaxSampleAbsError"] = 4
    result = triage.build_triage(report)
    assert result["classification"] == "input_route_failure"
    assert result["last_route_result"]["max_abs_error"] == 4
    assert result["input_metrics"]["max_input_drift_px"] == 1


def test_sendinput_permission_denial_is_environment_failure() -> None:
    with tempfile.TemporaryDirectory() as directory:
        log_path = Path(directory) / "intro-skip.log"
        log_path.write_text(
            "PermissionError: [WinError 5] SendInput absolute move\n",
            encoding="ascii",
        )
        report = base_report()
        report["failures"] = [
            "nonblack percent dropped below 10",
            "route/input probe failures: 1",
            "input drift exceeded 1px or metric missing: 1",
        ]
        report["route_results"][0]["PathVerified"] = False
        report["route_results"][0]["ClickPathVerified"] = False
        report["route_results"][0]["ProbeExitCode"] = 1
        report["route_results"][0]["Log"] = str(log_path)
        result = triage.build_triage(report)

    assert result["classification"] == "input_environment_permission_denied"
    assert "unsandboxed Windows session" in result["next_probe"]
    diagnostics = result["probe_log_diagnostics"]
    assert diagnostics["permission_denied_route_count"] == 1
    assert diagnostics["permission_denied_routes"] == ["intro-skip"]
    assert diagnostics["rows"][0]["signals"] == ["sendinput_permission_denied"]
    assert result["failure_context"]["input_permission_denied_routes"] == ["intro-skip"]


def test_cursor_query_denial_is_not_misattributed_to_sendinput() -> None:
    with tempfile.TemporaryDirectory() as directory:
        log_path = Path(directory) / "load-slot0.log"
        log_path.write_text(
            '{"sendinput_down": 1, "cursor_error": "[WinError 5] GetCursorPos"}\n',
            encoding="ascii",
        )
        report = base_report()
        report["failures"] = ["route/input probe failures: 1"]
        report["route_results"][0]["Name"] = "load-slot0"
        report["route_results"][0]["Log"] = str(log_path)
        result = triage.build_triage(report)

    row = result["probe_log_diagnostics"]["rows"][0]
    assert result["classification"] == "input_environment_permission_denied"
    assert row["signals"] == ["cursor_query_permission_denied"]


def test_frame_progression_failure_classification() -> None:
    report = base_report()
    report["route"] = "map-pan"
    report["frame_progress_expected"] = True
    report["frame_stability_class"] = "stable_idle"
    report["frame_hash_unique_count"] = 1
    report["failures"] = ["frame progression required for this route"]
    result = triage.build_triage(report)
    assert result["classification"] == "frame_progression_failure"
    assert result["frame_metrics"]["frame_stability_class"] == "stable_idle"


def test_process_growth_regression_classification() -> None:
    report = base_report()
    report["failures"] = ["private-memory growth exceeded 64MB"]
    result = triage.build_triage(report)
    assert result["classification"] == "process_growth_regression"
    assert result["process_metrics"]["private_memory_growth_bytes"] == 2048


def test_artifact_budget_classification() -> None:
    report = base_report()
    report["failures"] = ["artifact size exceeded 104857600 bytes"]
    result = triage.build_triage(report)
    assert result["classification"] == "artifact_budget_exceeded"
    assert "archive raw frames" in result["next_probe"]


def test_insufficient_samples_classify_as_hang_or_no_frame_progress() -> None:
    report = base_report()
    report["failures"] = ["expected at least 2 frame samples"]
    report["frame_sample_count"] = 1
    report["frame_samples"] = report["frame_samples"][:1]
    result = triage.build_triage(report)
    assert result["classification"] == "hang_or_no_frame_progress"
    assert "shorter sample interval" in result["next_probe"]
    assert result["frame_metrics"]["frame_sample_count"] == 1
    assert result["last_frame_sample"]["name"] == "frame-0000"

    report = base_report()
    report["failures"] = ["expected at least 2 process samples"]
    report["process_sample_count"] = 1
    report["process_samples"] = report["process_samples"][:1]
    result = triage.build_triage(report)
    assert result["classification"] == "hang_or_no_frame_progress"
    assert result["process_metrics"]["process_sample_count"] == 1
    assert result["last_process_sample"]["timestamp"] == "2026-06-16T12:00:00.0000000+00:00"


def test_process_cleanup_failure_classification() -> None:
    report = base_report()
    report["clean_stop"] = False
    report["failures"] = ["process was not stopped cleanly by the harness"]
    result = triage.build_triage(report)
    assert result["classification"] == "process_cleanup_failure"
    assert "process hygiene" in result["next_probe"]


def test_passing_run_classification() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = base_report()
        report["passed"] = True
        attach_passing_guard_report(report, Path(directory))
        result = triage.build_triage(report)
    assert result["passed"] is True
    assert result["classification"] == "passing_run_no_failure"
    assert result["guard_validation"]["evaluated"] is True
    assert result["guard_validation"]["overall"] is True


def test_guard_validation_failure_overrides_raw_pass() -> None:
    report = base_report()
    report["passed"] = True
    report["candidate"] = r"C:\ClashTests\wrong-root\fixture.exe"
    result = triage.build_triage(report)
    assert result["passed"] is False
    assert result["classification"] == "guard_validation_failure"
    assert result["guard_validation"]["evaluated"] is True
    assert result["guard_validation"]["overall"] is False
    assert any("candidate path is not under" in failure for failure in result["guard_validation"]["failures"])


def test_elapsed_coverage_guard_failure_gets_specific_classification() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = base_report()
        report["passed"] = True
        attach_passing_guard_report(report, Path(directory))
        report["frame_samples"][1]["Timestamp"] = "2026-06-16T12:00:10.0000000+00:00"
        report["process_samples"][1]["Timestamp"] = "2026-06-16T12:00:10.0000000+00:00"
        result = triage.build_triage(report)
    assert result["passed"] is False
    assert result["classification"] == "elapsed_coverage_failure"
    assert "sample_interval_sec" in result["next_probe"]
    assert result["guard_validation"]["evaluated"] is True
    assert result["guard_validation"]["overall"] is False
    assert any("elapsed coverage" in failure for failure in result["guard_validation"]["failures"])


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
        markdown = md_out.read_text(encoding="ascii")
        assert payload["classification"] == "capture_harness_failure"
        assert payload["failure_context"]["last_route_marker"] == "intro-skip"
        assert "## Failure Context" in markdown
        assert "## Visual Anomalies" in markdown


def run_tests() -> None:
    test_pending_approval_classification()
    test_av_crash_classification()
    test_unexpected_process_exit_classification()
    test_matching_hidden_cdb_followup_advances_unexpected_exit_probe()
    test_matching_wer_followup_classifies_os_closed_application_hang()
    test_runtime_window_health_classifies_hang_before_generic_exit()
    test_intro_skip_input_drift_exit_classification()
    test_intro_skip_probe_json_enriches_missing_route_mode()
    test_later_no_window_probe_preserves_intro_skip_exit_classification()
    test_render_regression_classification()
    test_visual_anomaly_summary_records_black_and_stripe_risk()
    test_input_route_failure_classification()
    test_input_drift_failure_classification()
    test_sendinput_permission_denial_is_environment_failure()
    test_cursor_query_denial_is_not_misattributed_to_sendinput()
    test_frame_progression_failure_classification()
    test_process_growth_regression_classification()
    test_artifact_budget_classification()
    test_insufficient_samples_classify_as_hang_or_no_frame_progress()
    test_process_cleanup_failure_classification()
    test_passing_run_classification()
    test_guard_validation_failure_overrides_raw_pass()
    test_elapsed_coverage_guard_failure_gets_specific_classification()
    test_cli_writes_outputs_and_fails_for_failed_report()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_failure_triage tests passed")
