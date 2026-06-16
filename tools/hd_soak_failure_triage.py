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


def guard_evaluation_for(report: dict[str, Any]) -> dict[str, Any] | None:
    if report.get("executed") is not True or report.get("passed") is not True:
        return None
    return hd_soak_report.evaluate_report(report)


def classify(report: dict[str, Any], guard_evaluation: dict[str, Any] | None = None) -> tuple[str, str, bool]:
    failures = lower_failures(report)
    guard_failures = lower_guard_failures(guard_evaluation)
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
        return (
            "unexpected_process_exit",
            "collect exit code, last frame, process log, and rerun once with CDB crash logging",
            False,
        )

    if "route/input probe failures" in failures or "input drift" in failures:
        return (
            "input_route_failure",
            "inspect route_results and rerun the same route with mouse_path_probe logging before changing patches",
            False,
        )

    if "nonblack percent" in failures or "unique sampled colors" in failures:
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

    if "artifact size exceeded" in failures:
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


def route_summary(route: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(route, dict):
        return None
    return {
        "name": route.get("Name"),
        "points": route.get("Points"),
        "click": route.get("Click"),
        "path_verified": route.get("PathVerified"),
        "click_path_verified": route.get("ClickPathVerified"),
        "max_abs_error": route.get("MaxAbsError"),
        "max_sample_abs_error": route.get("MaxSampleAbsError"),
        "click_event_count": route.get("ClickEventCount"),
        "probe_exit_code": route.get("ProbeExitCode"),
        "json": route.get("Json"),
        "log": route.get("Log"),
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


def build_triage(report: dict[str, Any], source_report: Path | None = None) -> dict[str, Any]:
    guard_evaluation = guard_evaluation_for(report)
    classification, next_probe, passed = classify(report, guard_evaluation)
    last_frame = frame_summary(last_item(report.get("frame_samples")))
    last_route = route_summary(last_item(report.get("route_results")))
    last_process = process_summary(last_item(report.get("process_samples")))
    guard_failures = list((guard_evaluation or {}).get("failures") or [])
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
        "executed": report.get("executed"),
        "report_passed": report.get("passed"),
        "process_exited_unexpectedly": report.get("process_exited_unexpectedly"),
        "exit_code": report.get("exit_code"),
        "clean_stop": report.get("clean_stop"),
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
        "## Last Evidence",
        "",
        (
            f"- Last route: `{route.get('name')}` path=`{route.get('path_verified')}` "
            f"click=`{route.get('click_path_verified')}` drift=`{route.get('max_abs_error')}` "
            f"sample_drift=`{route.get('max_sample_abs_error')}`"
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
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    triage = build_triage(load_json(args.report), args.report)
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
