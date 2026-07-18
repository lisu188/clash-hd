#!/usr/bin/env python3
"""Classify HD soak report failures and name the next probe.

This is repo-only triage for reports written by scripts/smoke/run_hd_soak.ps1.
It does not launch Clash95, CDB, wrappers, PowerShell harnesses, or windows.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import hd_soak_report


DEFAULT_REPORT = Path("captures/current/hd-soak-short-current.json")
DEFAULT_JSON = Path("captures/current/hd-soak-failure-triage-current.json")
DEFAULT_MD = Path("captures/current/hd-soak-failure-triage-current.md")
RUNTIME_POLICY = (
    "repo-only soak failure triage; does not launch Clash95, CDB, wrappers, "
    "PowerShell harnesses, or visible windows"
)
AV_EXIT_CODES = {3221225477, -1073741819, 0xC0000005}
MAX_PROBE_LOG_TAIL_BYTES = 256 * 1024


def cdb_followup_path_for_report(report_path: Path | None) -> Path | None:
    if report_path is None:
        return None
    name = report_path.name
    suffix = "-current.json"
    if not name.endswith(suffix):
        return None
    return report_path.with_name(f"{name[:-len(suffix)]}-cdb-followup-current.json")


def load_cdb_followup_for_report(report_path: Path | None) -> dict[str, Any] | None:
    path = cdb_followup_path_for_report(report_path)
    if path is None or not path.exists():
        return None
    return load_json(path)


def wer_followup_path_for_report(report_path: Path | None) -> Path | None:
    if report_path is None:
        return None
    name = report_path.name
    suffix = "-current.json"
    if not name.endswith(suffix):
        return None
    return report_path.with_name(f"{name[:-len(suffix)]}-wer-followup-current.json")


def load_wer_followup_for_report(report_path: Path | None) -> dict[str, Any] | None:
    path = wer_followup_path_for_report(report_path)
    if path is None or not path.exists():
        return None
    return load_json(path)


def summarize_wer_followup(
    report: dict[str, Any],
    followup: dict[str, Any] | None,
    source_report: Path | None = None,
) -> dict[str, Any] | None:
    if not isinstance(followup, dict):
        return None
    events = followup.get("event_evidence") or {}
    correlation = followup.get("timeline_correlation") or {}
    mitigation = followup.get("mitigation") or {}
    failures: list[str] = []
    if str(followup.get("candidate_sha256") or "").upper() != str(
        report.get("candidate_sha256") or ""
    ).upper():
        failures.append("candidate SHA-256 does not match the visible soak report")
    if followup.get("stage") != report.get("stage"):
        failures.append("stage does not match the visible soak report")
    if followup.get("route") != report.get("route"):
        failures.append("route does not match the visible soak report")
    if source_report is not None and Path(str(followup.get("source_visible_report") or "")) != source_report:
        failures.append("source visible report does not match the triaged report")
    if followup.get("passed") is not True:
        failures.append("WER follow-up manifest is not passing")
    if events.get("event_name") != "AppHangB1":
        failures.append("WER event is not AppHangB1")
    if int(events.get("application_hang_1002_count") or 0) < 1:
        failures.append("Application Hang event 1002 was not observed")
    if int(events.get("wer_apphang_1001_count") or 0) < 1:
        failures.append("WER AppHang event 1001 was not observed")
    if int(events.get("application_error_1000_count") or 0) != 0:
        failures.append("an Application Error 1000 crash event was also observed")
    if events.get("windows_closed_nonresponsive_application") is not True:
        failures.append("OS closure of the nonresponsive application was not established")
    if correlation.get("candidate_name_matches") is not True:
        failures.append("WER candidate name does not match the soak candidate")
    if correlation.get("event_within_failed_run_window") is not True:
        failures.append("WER event was not correlated to the failed run window")
    mitigation_ready = (
        mitigation.get("window_health_instrumentation_added") is True
        and mitigation.get("harness_guard_passed") is True
        and mitigation.get("window_health_stop_check_passed") is True
        and bool(mitigation.get("harness_guard_path"))
    )
    return {
        "path": followup.get("manifest_path"),
        "matched": not failures,
        "status": followup.get("status"),
        "candidate_sha256": followup.get("candidate_sha256"),
        "stage": followup.get("stage"),
        "route": followup.get("route"),
        "event_evidence": events,
        "timeline_correlation": correlation,
        "capture_analysis": followup.get("capture_analysis"),
        "mitigation": mitigation,
        "window_health_mitigation_ready": mitigation_ready,
        "scope_limit": followup.get("scope_limit"),
        "failures": failures,
    }


def summarize_cdb_followup(
    report: dict[str, Any],
    followup: dict[str, Any] | None,
    source_report: Path | None = None,
) -> dict[str, Any] | None:
    if not isinstance(followup, dict):
        return None
    observation = followup.get("observation") or {}
    route = followup.get("route_evidence") or {}
    presentation = followup.get("presentation") or {}
    failures: list[str] = []
    if str(followup.get("candidate_sha256") or "").upper() != str(
        report.get("candidate_sha256") or ""
    ).upper():
        failures.append("candidate SHA-256 does not match the visible soak report")
    if followup.get("stage") != report.get("stage"):
        failures.append("stage does not match the visible soak report")
    if followup.get("route") != report.get("route"):
        failures.append("route does not match the visible soak report")
    if source_report is not None and Path(str(followup.get("source_visible_report") or "")) != source_report:
        failures.append("source visible report does not match the triaged report")
    if followup.get("passed") is not True:
        failures.append("follow-up manifest is not passing")
    if followup.get("hidden_desktop") is not True:
        failures.append("follow-up was not hidden-desktop")
    if presentation.get("proxy_present_enabled") is not False:
        failures.append("memory-only proxy presentation was not explicitly disabled")
    if route.get("gameplay_observed") is not True:
        failures.append("follow-up did not observe gameplay")
    if observation.get("post_dump_observation_completed") is not True:
        failures.append("post-dump observation did not complete")
    if observation.get("post_dump_exit_observed") is not False:
        failures.append("follow-up observed a post-dump exit")
    if observation.get("access_violation_observed") is not False:
        failures.append("follow-up observed an access violation")
    if observation.get("app_request_quit_observed") is not False:
        failures.append("follow-up observed App_RequestQuit")
    return {
        "path": followup.get("manifest_path"),
        "matched": not failures,
        "status": followup.get("status"),
        "source_cdb_summary": followup.get("source_cdb_summary"),
        "candidate_sha256": followup.get("candidate_sha256"),
        "stage": followup.get("stage"),
        "route": followup.get("route"),
        "hidden_desktop": followup.get("hidden_desktop"),
        "presentation": presentation,
        "route_evidence": route,
        "observation": observation,
        "scope_limit": followup.get("scope_limit"),
        "failures": failures,
    }


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def last_item(items: list[Any] | None) -> Any:
    values = list(items or [])
    return values[-1] if values else None


def lower_failures(report: dict[str, Any]) -> str:
    return "\n".join(str(item).lower() for item in report.get("failures") or [])


def lower_guard_failures(guard_evaluation: dict[str, Any] | None) -> str:
    return "\n".join(str(item).lower() for item in (guard_evaluation or {}).get("failures") or [])


def int_value(report: dict[str, Any], key: str) -> int:
    try:
        return int(report.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def route_int_value(route: dict[str, Any] | None, key: str) -> int:
    if not isinstance(route, dict):
        return 0
    try:
        return int(route.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def guard_evaluation_for(report: dict[str, Any]) -> dict[str, Any] | None:
    if report.get("executed") is not True or report.get("passed") is not True:
        return None
    return hd_soak_report.evaluate_report(report)


def probe_log_diagnostic(route: dict[str, Any]) -> dict[str, Any]:
    """Summarize environment-level input failures without copying raw logs."""
    name = route.get("Name")
    log_value = route.get("Log")
    if not log_value:
        return {
            "name": name,
            "path": None,
            "read_status": "missing-log-path",
            "size_bytes": None,
            "signals": [],
        }

    path = Path(str(log_value))
    try:
        size_bytes = path.stat().st_size
        with path.open("rb") as handle:
            if size_bytes > MAX_PROBE_LOG_TAIL_BYTES:
                handle.seek(-MAX_PROBE_LOG_TAIL_BYTES, 2)
            text = handle.read().decode("utf-8", errors="replace").lower()
    except FileNotFoundError:
        return {
            "name": name,
            "path": str(path),
            "read_status": "missing",
            "size_bytes": None,
            "signals": [],
        }
    except OSError as exc:
        return {
            "name": name,
            "path": str(path),
            "read_status": "unreadable",
            "size_bytes": None,
            "signals": [],
            "error": str(exc),
        }

    signals: list[str] = []
    lines = text.splitlines()
    sendinput_permission_denied = any(
        "[winerror 5] sendinput" in line
        or ("sendinput" in line and "access is denied" in line)
        for line in lines
    )
    if sendinput_permission_denied:
        signals.append("sendinput_permission_denied")
    cursor_query_permission_denied = any(
        "[winerror 5] getcursorpos" in line
        or ("getcursorpos" in line and "access is denied" in line)
        for line in lines
    )
    if cursor_query_permission_denied:
        signals.append("cursor_query_permission_denied")
    if "no visible window found for pid" in text:
        signals.append("no_visible_process_window")
    return {
        "name": name,
        "path": str(path),
        "read_status": "ok",
        "size_bytes": size_bytes,
        "tail_truncated": size_bytes > MAX_PROBE_LOG_TAIL_BYTES,
        "signals": signals,
    }


def probe_log_diagnostics(report: dict[str, Any]) -> dict[str, Any]:
    rows = [
        probe_log_diagnostic(route)
        for route in report.get("route_results") or []
        if isinstance(route, dict)
    ]
    denied_routes = [
        str(row.get("name"))
        for row in rows
        if any(
            signal in {
                "sendinput_permission_denied",
                "cursor_query_permission_denied",
            }
            for signal in (row.get("signals") or [])
        )
    ]
    return {
        "checked_route_count": len(rows),
        "readable_log_count": sum(1 for row in rows if row.get("read_status") == "ok"),
        "permission_denied_route_count": len(denied_routes),
        "permission_denied_routes": denied_routes,
        "rows": rows,
    }


def cursor_probe_diagnostic(attempt: dict[str, Any]) -> dict[str, Any]:
    """Summarize one launch attempt's engine-cursor probe JSON.

    A silently denied SetForegroundWindow produces no WinError 5 anywhere: the
    call just returns false and the foreground-mode DirectInput never sees the
    injected pulses. The probe records that as ``foreground_ok: false`` on every
    aim iteration, so the probe JSON -- not the log text -- is the only place
    focus denial is observable.
    """
    name = attempt.get("Attempt")
    json_value = attempt.get("CursorProbeJson")
    base: dict[str, Any] = {
        "attempt": name,
        "path": str(json_value) if json_value else None,
        "signals": [],
    }
    if not json_value:
        base["read_status"] = "missing-json-path"
        return base

    path = Path(str(json_value))
    try:
        payload = load_json(path)
    except FileNotFoundError:
        base["read_status"] = "missing"
        return base
    except (OSError, json.JSONDecodeError) as exc:
        base["read_status"] = "unreadable"
        base["error"] = str(exc)
        return base

    iterations: list[dict[str, Any]] = []
    converged_flags: list[bool] = []
    for step in payload.get("steps") or []:
        if not isinstance(step, dict):
            continue
        aim = step.get("aim")
        if not isinstance(aim, dict):
            continue
        converged_flags.append(bool(aim.get("converged")))
        for row in aim.get("iterations") or []:
            if isinstance(row, dict):
                iterations.append(row)

    foreground_flags = [
        bool(row.get("foreground_ok"))
        for row in iterations
        if "foreground_ok" in row
    ]
    denied_count = len([flag for flag in foreground_flags if not flag])
    cursor_alive = payload.get("cursor_alive")
    converged = bool(converged_flags) and all(converged_flags)

    signals: list[str] = []
    if foreground_flags and denied_count == len(foreground_flags):
        signals.append("foreground_activation_denied")
    elif denied_count:
        signals.append("foreground_activation_intermittent")
    if cursor_alive is True and not converged:
        signals.append("cursor_responded_without_convergence")
    if cursor_alive is False:
        signals.append("cursor_never_responded")

    base.update(
        {
            "read_status": "ok",
            "iteration_count": len(iterations),
            "foreground_ok_count": len(foreground_flags) - denied_count,
            "foreground_denied_count": denied_count,
            "converged": converged,
            "cursor_alive": cursor_alive,
            "aim_error_px": (
                (payload.get("steps") or [{}])[0].get("aim", {}).get("aim_error_px")
                if payload.get("steps")
                else None
            ),
            "signals": signals,
        }
    )
    return base


def cursor_probe_diagnostics(report: dict[str, Any]) -> dict[str, Any]:
    rows = [
        cursor_probe_diagnostic(attempt)
        for attempt in report.get("launch_attempts") or []
        if isinstance(attempt, dict)
    ]
    denied_attempts = [
        row.get("attempt")
        for row in rows
        if "foreground_activation_denied" in (row.get("signals") or [])
    ]
    responded_without_convergence = [
        row.get("attempt")
        for row in rows
        if "cursor_responded_without_convergence" in (row.get("signals") or [])
    ]
    return {
        "checked_attempt_count": len(rows),
        "readable_probe_count": sum(1 for row in rows if row.get("read_status") == "ok"),
        "foreground_denied_attempt_count": len(denied_attempts),
        "foreground_denied_attempts": denied_attempts,
        "cursor_responded_without_convergence_attempts": responded_without_convergence,
        "cursor_alive_observed": any(row.get("cursor_alive") is True for row in rows),
        "rows": rows,
    }


def classify(
    report: dict[str, Any],
    guard_evaluation: dict[str, Any] | None = None,
    probe_diagnostics: dict[str, Any] | None = None,
    cursor_diagnostics: dict[str, Any] | None = None,
) -> tuple[str, str, bool]:
    failures = lower_failures(report)
    guard_failures = lower_guard_failures(guard_evaluation)
    input_permission_denied = bool(
        (probe_diagnostics or {}).get("permission_denied_route_count")
    ) or bool((cursor_diagnostics or {}).get("foreground_denied_attempt_count"))
    if report.get("executed") is not True:
        if "approval" in failures or report.get("execution_blocked_reason"):
            return (
                "not_executed_pending_approval",
                "obtain explicit approval for the exact short2 visible-runtime command, then rerun the soak",
                False,
            )
        return ("not_executed_unknown", "inspect why the soak report was written without execution", False)

    if report.get("passed") is True:
        if guard_evaluation is not None and guard_evaluation.get("overall") is not True:
            if (
                "elapsed coverage" in guard_failures
                or "sample_interval_sec" in guard_failures
                or "invalid timestamps" in guard_failures
            ):
                return (
                    "elapsed_coverage_failure",
                    "inspect frame/process sample timestamps and sample_interval_sec, then rerun with the same tier or a shorter sample interval",
                    False,
                )
            if (
                "artifact size exceeded" in guard_failures
                or "artifact bytes" in guard_failures
                or "artifact_limit_bytes" in guard_failures
            ):
                return (
                    "artifact_budget_exceeded",
                    "reduce sampling/artifact retention or archive raw frames outside the repository before rerun",
                    False,
                )
            return (
                "guard_validation_failure",
                "inspect hd_soak_report guard failures before accepting or extending the soak",
                False,
            )
        return (
            "passing_run_no_failure",
            "repeat short2 or move to short10 only after preserving the report and validation guard output",
            True,
        )

    exit_code = report.get("exit_code")
    if report.get("process_exited_unexpectedly") is True:
        if exit_code in AV_EXIT_CODES:
            return (
                "crash_av",
                "run the crash/CDB probe for the same candidate and compare the patch-stage manifest",
                False,
            )
        if report.get("window_hang_observed") is True or "application window became nonresponsive" in failures:
            return (
                "application_hang_detected",
                "inspect window_health_samples to isolate the first nonresponsive route phase before requesting any visible rerun",
                False,
            )
        if (
            report.get("window_missing_while_alive_observed") is True
            or "visible application window disappeared while the process remained alive" in failures
        ):
            return (
                "window_missing_while_process_alive",
                "inspect window_health_samples and wrapper transitions at the first missing-window phase before requesting any visible rerun",
                False,
            )
        if input_permission_denied:
            return (
                "input_environment_permission_denied",
                "rerun the exact tokenized route command in a fresh explicitly approved unsandboxed Windows session; do not change patches or lower visual thresholds",
                False,
            )
        routes = [
            route
            for route in report.get("route_results") or []
            if isinstance(route, dict)
        ]
        last_route = last_item(routes)
        intro_route = next(
            (route for route in routes if route.get("Name") == "intro-skip"),
            None,
        )
        no_visible_process_window = any(
            "no_visible_process_window" in (row.get("signals") or [])
            for row in (probe_diagnostics or {}).get("rows") or []
        )
        max_input_drift = int_value(report, "max_input_drift_px") or 1
        intro_skip_drift = (
            isinstance(intro_route, dict)
            and (
                intro_route.get("PathVerified") is not True
                or (intro_route.get("Click") is True and intro_route.get("ClickPathVerified") is not True)
                or route_int_value(intro_route, "MaxAbsError") > max_input_drift
                or route_int_value(intro_route, "MaxSampleAbsError") > max_input_drift
                or int_value(report, "input_max_sample_abs_error") > max_input_drift
                or "input drift" in failures
                or "route/input probe failures" in failures
            )
            and (
                report.get("final_route_marker") == "intro-skip"
                or no_visible_process_window
            )
        )
        if intro_skip_drift:
            return (
                "intro_skip_input_drift_exit",
                "fix or verify intro-skip harness input mode before rerunning; use postmessage/space-only harness prep, then rerun visible soak only after explicit visible-window approval",
                False,
            )
        return (
            "unexpected_process_exit",
            "collect exit code, last frame, process log, and rerun once with CDB crash logging",
            False,
        )

    if input_permission_denied:
        return (
            "input_environment_permission_denied",
            "rerun the exact tokenized route command in a fresh explicitly approved unsandboxed Windows session; do not change patches or lower visual thresholds",
            False,
        )

    if report.get("window_hang_observed") is True or "application window became nonresponsive" in failures:
        return (
            "application_hang_detected",
            "inspect window_health_samples to isolate the first nonresponsive route phase before requesting any visible rerun",
            False,
        )

    if (
        report.get("window_missing_while_alive_observed") is True
        or "visible application window disappeared while the process remained alive" in failures
    ):
        return (
            "window_missing_while_process_alive",
            "inspect window_health_samples and wrapper transitions at the first missing-window phase before requesting any visible rerun",
            False,
        )

    if "route/input probe failures" in failures or "input drift" in failures:
        return (
            "input_route_failure",
            "inspect route_results and rerun the same route with mouse_path_probe logging before changing patches",
            False,
        )

    # A capture-path change has to be ruled out BEFORE the render verdict: the
    # 'screen' and window-DC paths do not observe the same pixels for this
    # DirectDraw title, so a black outlier from a minority path is a capture
    # defect masquerading as a render regression (2026-07-18 short2).
    if "capture mode changed" in failures:
        return (
            "capture_harness_failure",
            "the run mixed capture paths, so its frames are not comparable render "
            "evidence; make capture_clash_client_frame.ps1 hold one path for the whole "
            "run before judging any render metric",
            False,
        )

    if (
        "nonblack percent" in failures
        or "unique sampled colors" in failures
        or "black/blank patch" in failures
        or "palette/stripe" in failures
        or "visual anomaly" in failures
    ):
        return (
            "render_or_palette_regression",
            "inspect the last sampled PNG/metrics and compare against no-popup/current map evidence before patching",
            False,
        )

    if "capture errors" in failures:
        return (
            "capture_harness_failure",
            "inspect capture_errors and capture_clash_client_frame output before treating this as a game failure",
            False,
        )

    if "frame progression" in failures or "unique frame hashes" in failures:
        return (
            "frame_progression_failure",
            "inspect frame hashes and route input logs before trusting longer pan or movement soaks",
            False,
        )

    if (
        "working-set growth" in failures
        or "working_set_growth" in failures
        or "private-memory growth" in failures
        or "private_memory_growth" in failures
        or "handle growth" in failures
        or "handle_growth" in failures
    ):
        return (
            "process_growth_regression",
            "inspect process_samples for working-set, private-memory, or handle growth before extending soak duration",
            False,
        )

    if (
        "artifact size exceeded" in failures
        or "artifact bytes" in failures
        or "artifact_limit_bytes" in failures
    ):
        return (
            "artifact_budget_exceeded",
            "reduce sampling/artifact retention or archive raw frames outside the repository before rerun",
            False,
        )

    if (
        "elapsed coverage" in failures
        or "sample_interval_sec" in failures
        or "invalid timestamps" in failures
    ):
        return (
            "elapsed_coverage_failure",
            "inspect frame/process sample timestamps and sample_interval_sec, then rerun with the same tier or a shorter sample interval",
            False,
        )

    frame_sample_count = int_value(report, "frame_sample_count")
    process_sample_count = int_value(report, "process_sample_count")
    if (
        "frame sample count" in failures
        or "expected at least 2 frame samples" in failures
        or "process sample count" in failures
        or "expected at least 2 process samples" in failures
        or frame_sample_count < 2
        or process_sample_count < 2
    ):
        return (
            "hang_or_no_frame_progress",
            "inspect process_samples and rerun with shorter sample interval plus crash/hang probe",
            False,
        )

    if report.get("clean_stop") is not True:
        return (
            "process_cleanup_failure",
            "verify process hygiene and stop semantics before accepting further soak output",
            False,
        )

    return (
        "soak_failed_unclassified",
        "inspect failures, last route marker, frame samples, and process samples to add a specific classifier",
        False,
    )


def frame_summary(frame: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(frame, dict):
        return None
    return {
        "name": frame.get("Name"),
        "timestamp": frame.get("Timestamp"),
        "hash": frame.get("Hash"),
        "width": frame.get("Width"),
        "height": frame.get("Height"),
        "nonblack_percent": frame.get("NonblackPercent"),
        "mean_luma": frame.get("MeanLuma"),
        "unique_sample_colors": frame.get("UniqueSampleColors"),
        "capture_mode": frame.get("CaptureMode"),
    }


def route_probe_details(route: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(route, dict):
        return {"read_status": "no-route"}
    probe_json = route.get("Json")
    if not probe_json:
        return {"read_status": "missing-json-path"}
    path = Path(str(probe_json))
    try:
        payload = load_json(path)
    except FileNotFoundError:
        return {"read_status": "missing"}
    except (OSError, json.JSONDecodeError) as exc:
        return {"read_status": "unreadable", "error": str(exc)}

    points = payload.get("points")
    if isinstance(points, dict):
        point_items = [points]
    elif isinstance(points, list):
        point_items = [point for point in points if isinstance(point, dict)]
    else:
        point_items = []
    first_point = point_items[0] if point_items else {}
    clicks = first_point.get("clicks") if isinstance(first_point, dict) else None
    click_items = [click for click in (clicks or []) if isinstance(click, dict)]
    samples = first_point.get("samples") if isinstance(first_point, dict) else None
    sample_items = [sample for sample in (samples or []) if isinstance(sample, dict)]
    click_event_items: list[dict[str, Any]] = []
    for click in click_items:
        for event in click.get("events") or []:
            if isinstance(event, dict):
                click_event_items.append(event)

    def sample_abs_error(sample: dict[str, Any]) -> int:
        values: list[int] = []
        for key in ("screen_error", "client_error"):
            error = sample.get(key)
            if isinstance(error, list):
                for value in error:
                    try:
                        values.append(abs(int(value)))
                    except (TypeError, ValueError):
                        pass
        return max(values or [0])

    all_samples = sample_items + click_event_items
    worst_sample = max(all_samples, key=sample_abs_error, default=None)
    click_methods = sorted({str(click.get("mode")) for click in click_items if click.get("mode")})
    return {
        "read_status": "ok",
        "path": str(path),
        "move_mode": first_point.get("move_mode") if isinstance(first_point, dict) else None,
        "move_method": first_point.get("move_method") if isinstance(first_point, dict) else None,
        "click_modes": click_methods,
        "click_repeat_observed": len(click_items) if click_items else None,
        "sample_count": len(sample_items),
        "click_event_sample_count": len(click_event_items),
        "max_sample_abs_error": sample_abs_error(worst_sample or {}),
        "max_sample_phase": (worst_sample or {}).get("phase"),
    }


def route_summary(route: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(route, dict):
        return None
    probe = route_probe_details(route)
    derived_click_mode = None
    click_modes = probe.get("click_modes")
    if isinstance(click_modes, list) and len(click_modes) == 1:
        derived_click_mode = click_modes[0]
    click_mode = route.get("ClickMode") or derived_click_mode
    move_mode = route.get("MoveMode") or probe.get("move_mode")
    click_repeat = route.get("ClickRepeat") or probe.get("click_repeat_observed")
    return {
        "name": route.get("Name"),
        "points": route.get("Points"),
        "click": route.get("Click"),
        "path_verified": route.get("PathVerified"),
        "click_path_verified": route.get("ClickPathVerified"),
        "max_abs_error": route.get("MaxAbsError"),
        "max_sample_abs_error": route.get("MaxSampleAbsError"),
        "click_event_count": route.get("ClickEventCount"),
        "move_mode": move_mode,
        "move_mode_source": "route_result" if route.get("MoveMode") else "probe_json" if move_mode else None,
        "click_mode": click_mode,
        "click_mode_source": "route_result" if route.get("ClickMode") else "probe_json" if click_mode else None,
        "click_repeat": click_repeat,
        "click_repeat_source": "route_result" if route.get("ClickRepeat") else "probe_json" if click_repeat else None,
        "space_pulses": route.get("SpacePulses"),
        "input_proof_class": route.get("InputProofClass"),
        "probe_exit_code": route.get("ProbeExitCode"),
        "json": route.get("Json"),
        "log": route.get("Log"),
        "probe_json": probe,
    }


def process_summary(sample: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(sample, dict):
        return None
    return {
        "timestamp": sample.get("Timestamp"),
        "has_exited": sample.get("HasExited"),
        "exit_code": sample.get("ExitCode"),
        "working_set64": sample.get("WorkingSet64"),
        "private_memory_size64": sample.get("PrivateMemorySize64"),
        "handle_count": sample.get("HandleCount"),
        "error": sample.get("Error"),
    }


def failure_timestamp_context(
    report: dict[str, Any],
    last_frame: dict[str, Any] | None,
    last_process: dict[str, Any] | None,
) -> tuple[Any, str]:
    if isinstance(last_process, dict) and last_process.get("timestamp"):
        return last_process.get("timestamp"), "last_process_sample"
    if isinstance(last_frame, dict) and last_frame.get("timestamp"):
        return last_frame.get("timestamp"), "last_frame_sample"
    return report.get("generated_at"), "report_generated_at"


def visual_anomaly_summary(report: dict[str, Any]) -> dict[str, Any]:
    evaluation = hd_soak_report.evaluate_report(report)
    check = (evaluation.get("checks") or {}).get("visual_anomalies") or {}
    summary = dict(check.get("summary") or {})
    summary["passed"] = check.get("passed")
    summary["failures"] = list(check.get("failures") or [])
    return summary


def build_triage(
    report: dict[str, Any],
    source_report: Path | None = None,
    cdb_followup: dict[str, Any] | None = None,
    wer_followup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    guard_evaluation = guard_evaluation_for(report)
    probe_diagnostics = probe_log_diagnostics(report)
    cursor_diagnostics = cursor_probe_diagnostics(report)
    classification, next_probe, passed = classify(
        report, guard_evaluation, probe_diagnostics, cursor_diagnostics
    )
    if (
        classification == "input_environment_permission_denied"
        and cursor_diagnostics.get("foreground_denied_attempt_count")
    ):
        next_probe = (
            "SetForegroundWindow was silently denied on every aim iteration, so the "
            "foreground-mode DirectInput never received the injected pulses; rerun the "
            "exact tokenized route command DIRECTLY from an interactive session with "
            "input standing (never via Start-Job or any detached/non-interactive "
            "wrapper), and do not change patches or lower visual thresholds"
        )
    cdb_followup_summary = summarize_cdb_followup(report, cdb_followup, source_report)
    wer_followup_summary = summarize_wer_followup(report, wer_followup, source_report)
    if (
        classification == "unexpected_process_exit"
        and wer_followup_summary
        and wer_followup_summary.get("matched") is True
    ):
        classification = "application_hang_wer_closed"
        if wer_followup_summary.get("window_health_mitigation_ready") is True:
            next_probe = (
                "generate a fresh tokened application/windowed retry packet and request explicit "
                "visible-runtime approval; the instrumented harness must stop at the first hung "
                "or missing live target window"
            )
        else:
            next_probe = (
                "instrument window responsiveness before and after every route step, stop further "
                "input/capture when the target becomes hung or loses its visible window, and isolate "
                "the first application/windowed wrapper transition that becomes nonresponsive"
            )
    elif (
        classification == "unexpected_process_exit"
        and cdb_followup_summary
        and cdb_followup_summary.get("matched") is True
    ):
        next_probe = (
            "the same candidate reached gameplay and stayed live in the completed hidden "
            "CDB memory-proxy observation; inspect the application/windowed wrapper, input, "
            "and capture path before requesting any visible rerun"
        )
    last_frame = frame_summary(last_item(report.get("frame_samples")))
    last_route = route_summary(last_item(report.get("route_results")))
    intro_route = route_summary(
        next(
            (
                route
                for route in report.get("route_results") or []
                if isinstance(route, dict) and route.get("Name") == "intro-skip"
            ),
            None,
        )
    )
    last_process = process_summary(last_item(report.get("process_samples")))
    failure_timestamp, failure_timestamp_source = failure_timestamp_context(report, last_frame, last_process)
    visual_anomalies = visual_anomaly_summary(report)
    guard_failures = list((guard_evaluation or {}).get("failures") or [])
    if classification == "intro_skip_input_drift_exit" and isinstance(intro_route, dict):
        click_mode = intro_route.get("click_mode")
        if click_mode == "sendinput":
            next_probe = (
                "previous intro-skip click used sendinput and drifted after button events; "
                "rerun only with the current tokenized postmessage/space-pulse intro-skip "
                "command after explicit visible-window approval"
            )
        elif not click_mode:
            next_probe = (
                "previous intro-skip report does not record the click mode; use the current "
                "tokenized postmessage/space-pulse intro-skip command, then rerun only after "
                "explicit visible-window approval"
            )
        elif click_mode == "postmessage":
            next_probe = (
                "previous intro-skip postmessage repeats crossed a window/intro transition; "
                "make the harness stop or reacquire after the transition, retain explicit "
                "windowed-mode verification, then rerun only after fresh visible-window approval"
            )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "runtime_policy": RUNTIME_POLICY,
        "source_report": str(source_report) if source_report else report.get("report_json"),
        "classification": classification,
        "next_probe": next_probe,
        "tier": report.get("tier"),
        "route": report.get("route"),
        "duration_sec": report.get("duration_sec"),
        "stage": report.get("stage"),
        "candidate": report.get("candidate"),
        "candidate_sha256": report.get("candidate_sha256"),
        "output_directory": report.get("output_directory"),
        "final_route_marker": report.get("final_route_marker"),
        "last_route_marker": (last_route or {}).get("name") if isinstance(last_route, dict) else None,
        "executed": report.get("executed"),
        "report_passed": report.get("passed"),
        "process_exited_unexpectedly": report.get("process_exited_unexpectedly"),
        "exit_code": report.get("exit_code"),
        "clean_stop": report.get("clean_stop"),
        "failure_context": {
            "classification": classification,
            "crash_hang_class": classification,
            "next_probe": next_probe,
            "failure_timestamp": failure_timestamp,
            "failure_timestamp_source": failure_timestamp_source,
            "report_generated_at": report.get("generated_at"),
            "last_frame_timestamp": (last_frame or {}).get("timestamp") if isinstance(last_frame, dict) else None,
            "last_process_timestamp": (
                (last_process or {}).get("timestamp") if isinstance(last_process, dict) else None
            ),
            "final_route_marker": report.get("final_route_marker"),
            "last_route_marker": (last_route or {}).get("name") if isinstance(last_route, dict) else None,
            "route": report.get("route"),
            "tier": report.get("tier"),
            "duration_sec": report.get("duration_sec"),
            "visual_anomaly_passed": visual_anomalies.get("passed"),
            "black_patch_risk_count": visual_anomalies.get("black_patch_risk_count"),
            "palette_or_stripe_risk_count": visual_anomalies.get("palette_or_stripe_risk_count"),
            "missing_nonblack_bounds_count": visual_anomalies.get("missing_nonblack_bounds_count"),
            "input_permission_denied_route_count": probe_diagnostics.get(
                "permission_denied_route_count"
            ),
            "input_permission_denied_routes": probe_diagnostics.get("permission_denied_routes"),
            "foreground_denied_attempt_count": cursor_diagnostics.get(
                "foreground_denied_attempt_count"
            ),
            "foreground_denied_attempts": cursor_diagnostics.get("foreground_denied_attempts"),
            "cursor_alive_observed": cursor_diagnostics.get("cursor_alive_observed"),
        },
        "frame_metrics": {
            "frame_sample_count": report.get("frame_sample_count"),
            "frame_hash_unique_count": report.get("frame_hash_unique_count"),
            "frame_progress_expected": report.get("frame_progress_expected"),
            "frame_stability_class": report.get("frame_stability_class"),
            "nonblack_percent_min": report.get("nonblack_percent_min"),
            "nonblack_percent_max": report.get("nonblack_percent_max"),
            "mean_luma_min": report.get("mean_luma_min"),
            "mean_luma_max": report.get("mean_luma_max"),
            "unique_sample_colors_min": report.get("unique_sample_colors_min"),
            "unique_sample_colors_max": report.get("unique_sample_colors_max"),
        },
        "visual_anomalies": visual_anomalies,
        "process_metrics": {
            "process_sample_count": report.get("process_sample_count"),
            "working_set_growth_bytes": report.get("working_set_growth_bytes"),
            "private_memory_growth_bytes": report.get("private_memory_growth_bytes"),
            "handle_growth": report.get("handle_growth"),
            "artifact_bytes": report.get("artifact_bytes"),
        },
        "input_metrics": {
            "input_max_abs_error": report.get("input_max_abs_error"),
            "input_max_sample_abs_error": report.get("input_max_sample_abs_error"),
            "max_input_drift_px": report.get("max_input_drift_px"),
        },
        "probe_log_diagnostics": probe_diagnostics,
        "cursor_probe_diagnostics": cursor_diagnostics,
        "cdb_followup": cdb_followup_summary,
        "wer_followup": wer_followup_summary,
        "intro_skip_route_result": intro_route,
        "last_route_result": last_route,
        "last_frame_sample": last_frame,
        "last_process_sample": last_process,
        "guard_validation": {
            "evaluated": guard_evaluation is not None,
            "overall": (guard_evaluation or {}).get("overall"),
            "failure_count": len(guard_failures),
            "failures": guard_failures,
        },
        "failures": list(report.get("failures") or []),
    }


def to_markdown(triage: dict[str, Any]) -> str:
    frame = triage.get("last_frame_sample") or {}
    route = triage.get("last_route_result") or {}
    process = triage.get("last_process_sample") or {}
    context = triage.get("failure_context") or {}
    visual = triage.get("visual_anomalies") or {}
    probe_diagnostics = triage.get("probe_log_diagnostics") or {}
    cursor_diagnostics = triage.get("cursor_probe_diagnostics") or {}
    cdb_followup = triage.get("cdb_followup") or {}
    wer_followup = triage.get("wer_followup") or {}
    lines = [
        "# HD Soak Failure Triage",
        "",
        f"- Overall: {status_text(bool(triage['passed']))}",
        f"- Generated: `{triage['generated_at']}`",
        f"- Runtime policy: {triage['runtime_policy']}",
        f"- Source report: `{triage.get('source_report')}`",
        f"- Source selection: `{triage.get('source_report_selection')}`",
        f"- Canonical first-step report: `{triage.get('canonical_first_step_report')}`",
        f"- Canonical first-step present: `{triage.get('canonical_first_step_present')}`",
        f"- Legacy report: `{triage.get('legacy_report')}`",
        f"- Canonical runtime report missing: `{triage.get('canonical_runtime_report_missing')}`",
        f"- Classification: `{triage['classification']}`",
        f"- Next probe: {triage['next_probe']}",
        f"- Tier / route: `{triage.get('tier')}` / `{triage.get('route')}`",
        f"- Stage: `{triage.get('stage')}`",
        f"- Candidate SHA-256: `{triage.get('candidate_sha256')}`",
        f"- Output directory: `{triage.get('output_directory')}`",
        f"- Final route marker: `{triage.get('final_route_marker')}`",
        "",
        "## Failure Context",
        "",
        f"- Failure timestamp: `{context.get('failure_timestamp')}` source=`{context.get('failure_timestamp_source')}`",
        f"- Crash/hang class: `{context.get('crash_hang_class')}`",
        f"- Last route marker: `{context.get('last_route_marker')}`",
        f"- Next probe: {context.get('next_probe')}",
        "",
        "## Visual Anomalies",
        "",
        f"- Overall: `{status_text(bool(visual.get('passed')))}`",
        f"- Black/blank patch risk frames: `{visual.get('black_patch_risk_count')}`",
        f"- Palette/stripe risk frames: `{visual.get('palette_or_stripe_risk_count')}`",
        f"- Missing nonblack bounds frames: `{visual.get('missing_nonblack_bounds_count')}`",
        "",
        "## Probe Environment",
        "",
        f"- Checked route logs: `{probe_diagnostics.get('checked_route_count')}`",
        f"- Readable route logs: `{probe_diagnostics.get('readable_log_count')}`",
        f"- Input-API permission-denied routes: `{probe_diagnostics.get('permission_denied_route_count')}`",
        f"- Affected routes: `{','.join(probe_diagnostics.get('permission_denied_routes') or [])}`",
        f"- Cursor probes checked: `{cursor_diagnostics.get('checked_attempt_count')}`",
        f"- Foreground-denied attempts: `{cursor_diagnostics.get('foreground_denied_attempt_count')}`",
        f"- Engine cursor responded at least once: `{cursor_diagnostics.get('cursor_alive_observed')}`",
        "",
        "## Last Evidence",
        "",
        (
            f"- Last route: `{route.get('name')}` path=`{route.get('path_verified')}` "
            f"click=`{route.get('click_path_verified')}` drift=`{route.get('max_abs_error')}` "
            f"sample_drift=`{route.get('max_sample_abs_error')}` "
            f"click_mode=`{route.get('click_mode')}` repeat=`{route.get('click_repeat')}`"
        ),
        (
            "- Last frame: "
            f"`{frame.get('name')}` size=`{frame.get('width')}x{frame.get('height')}` "
            f"nonblack=`{frame.get('nonblack_percent')}` luma=`{frame.get('mean_luma')}` "
            f"colors=`{frame.get('unique_sample_colors')}`"
        ),
        (
            "- Last process: "
            f"exited=`{process.get('has_exited')}` exit_code=`{process.get('exit_code')}` "
            f"working_set=`{process.get('working_set64')}` handles=`{process.get('handle_count')}`"
        ),
        "",
        "## Metrics",
        "",
    ]
    if cdb_followup:
        insertion = lines.index("## Last Evidence")
        lines[insertion:insertion] = [
            "## Hidden CDB Follow-up",
            "",
            f"- Matched: `{cdb_followup.get('matched')}`",
            f"- Status: `{cdb_followup.get('status')}`",
            f"- Summary: `{cdb_followup.get('source_cdb_summary')}`",
            f"- Scope limit: {cdb_followup.get('scope_limit')}",
            "",
        ]
    if wer_followup:
        insertion = lines.index("## Last Evidence")
        lines[insertion:insertion] = [
            "## Windows Error Reporting Follow-up",
            "",
            f"- Matched: `{wer_followup.get('matched')}`",
            f"- Status: `{wer_followup.get('status')}`",
            f"- Event: `{(wer_followup.get('event_evidence') or {}).get('event_name')}`",
            f"- Window-health mitigation ready: `{wer_followup.get('window_health_mitigation_ready')}`",
            f"- Scope limit: {wer_followup.get('scope_limit')}",
            "",
        ]
    metrics = triage.get("frame_metrics") or {}
    process_metrics = triage.get("process_metrics") or {}
    input_metrics = triage.get("input_metrics") or {}
    guard_validation = triage.get("guard_validation") or {}
    for key in (
        "frame_sample_count",
        "frame_hash_unique_count",
        "frame_progress_expected",
        "frame_stability_class",
        "nonblack_percent_min",
        "nonblack_percent_max",
        "mean_luma_min",
        "mean_luma_max",
        "unique_sample_colors_min",
        "unique_sample_colors_max",
    ):
        lines.append(f"- `{key}`: `{metrics.get(key)}`")
    for row in visual.get("anomaly_rows") or []:
        lines.append(
            "- `visual_anomaly`: "
            f"`{row.get('name')}` flags=`{','.join(row.get('flags') or [])}` "
            f"nonblack=`{row.get('nonblack_percent')}` colors=`{row.get('unique_sample_colors')}`"
        )
    for key in (
        "input_max_abs_error",
        "input_max_sample_abs_error",
        "max_input_drift_px",
    ):
        lines.append(f"- `{key}`: `{input_metrics.get(key)}`")
    for key in (
        "process_sample_count",
        "working_set_growth_bytes",
        "private_memory_growth_bytes",
        "handle_growth",
        "artifact_bytes",
    ):
        lines.append(f"- `{key}`: `{process_metrics.get(key)}`")
    lines.extend(
        [
            "- `guard_validation_evaluated`: "
            f"`{guard_validation.get('evaluated')}`",
            f"- `guard_validation_overall`: `{guard_validation.get('overall')}`",
            f"- `guard_validation_failure_count`: `{guard_validation.get('failure_count')}`",
        ]
    )
    if triage.get("failures"):
        lines.extend(["", "## Source Failures", ""])
        for failure in triage["failures"]:
            lines.append(f"- {failure}")
    if guard_validation.get("failures"):
        lines.extend(["", "## Guard Failures", ""])
        for failure in guard_validation["failures"]:
            lines.append(f"- {failure}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(triage: dict[str, Any], json_path: Path | None, md_path: Path | None) -> None:
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(triage, indent=2) + "\n", encoding="ascii")
    if md_path:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(to_markdown(triage), encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", nargs="?", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--cdb-followup", type=Path)
    parser.add_argument("--wer-followup", type=Path)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    followup = load_json(args.cdb_followup) if args.cdb_followup else load_cdb_followup_for_report(args.report)
    wer_followup = load_json(args.wer_followup) if args.wer_followup else load_wer_followup_for_report(args.report)
    triage = build_triage(load_json(args.report), args.report, followup, wer_followup)
    write_outputs(triage, args.write_json, args.write_markdown)
    print(f"overall: {status_text(bool(triage['passed']))}")
    print(f"runtime-policy: {triage['runtime_policy']}")
    print(f"classification: {triage['classification']}")
    print(f"next-probe: {triage['next_probe']}")
    if args.require_pass and not triage["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
