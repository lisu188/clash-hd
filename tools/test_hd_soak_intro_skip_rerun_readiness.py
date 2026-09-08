#!/usr/bin/env python3
"""Fixture tests for hd_soak_intro_skip_rerun_readiness.py."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import hd_soak_intro_skip_rerun_readiness as readiness
import hd_soak_report
import test_hd_soak_report as soak_fixtures

APPROVAL_TOKEN = "1234567890abcdef"
APPROVAL_EXPIRES_UTC = "2026-06-16T20:00:00.0000000+00:00"


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
        "-SampleIntervalSec '15' -MaxInputDriftPx '1' "
        "-MinNonblackPercent '10' -MinUniqueSampleColors '8' "
        "-MaxArtifactMB '250' -MaxWorkingSetGrowthMB '64' "
        "-MaxPrivateMemoryGrowthMB '64' -MaxHandleGrowth '128' "
        f"-VisibleRuntimeApprovalExpiresUtc '{APPROVAL_EXPIRES_UTC}' "
        f"-VisibleRuntimeApprovalToken '{APPROVAL_TOKEN}' "
        "-Execute -AllowVisibleRuntime -RequirePass -Json"
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
                "windowed_mode": {"passed": True},
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
                "visible_runtime_approval": {
                    "token": APPROVAL_TOKEN,
                    "token_kind": "sha256-16",
                    "expires_utc": APPROVAL_EXPIRES_UTC,
                    "max_age_hours": 12,
                    "token_fields": ["fixture", APPROVAL_EXPIRES_UTC],
                    "purpose": "copy-exact dry-run approval packet; edited, stale, or hand-typed visible runtime commands fail closed",
                },
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
    assert "-VisibleRuntimeApprovalExpiresUtc" in report["dry_run_plan"]["approval_gated_execute_command"]
    assert "-VisibleRuntimeApprovalToken" in report["dry_run_plan"]["approval_gated_execute_command"]


def test_input_environment_denied_map_attempt_preserves_readiness() -> None:
    data = reports()
    data["step_status"]["current_step"]["status"] = (
        "failed_classified_input_environment_permission_denied"
    )
    report = build_fixture_report(data)

    assert report["passed"] is True, report["failures"]
    assert report["current_step"]["status"] == (
        "failed_classified_input_environment_permission_denied"
    )


def test_intro_transition_failure_preserves_readiness_after_harness_fix() -> None:
    data = reports()
    data["step_status"]["current_step"]["status"] = (
        "failed_classified_intro_skip_input_drift_exit"
    )
    report = build_fixture_report(data)

    assert report["passed"] is True, report["failures"]
    assert report["intro_skip_contract"]["stop_click_repeat_on_drift"] is True


def test_legacy_pending_and_known_environment_failures_still_require_approval() -> None:
    for status in (
        "pending_approval_legacy_compat",
        "failed_classified_application_hang_wer_closed",
        "failed_classified_window_missing_while_process_alive",
    ):
        data = reports()
        data["step_status"]["current_step"]["status"] = status
        report = build_fixture_report(data)
        assert report["passed"] is True, (status, report["failures"])
        assert report["status"] == "ready_for_explicit_visible_rerun_approval"
        assert "requires explicit user approval" in report["approval_boundary"]
        data["dry_run_plan"]["plan"]["visible_runtime_approval"]["token"] = ""
        report = build_fixture_report(data)
        assert report["passed"] is False, (status, report)
        assert report["status"] == "not_ready"


def test_unexpected_process_exit_is_not_applicable_not_rerun_ready() -> None:
    data = reports()
    data["step_status"]["current_step"]["status"] = (
        "failed_classified_unexpected_process_exit"
    )
    report = build_fixture_report(data)

    assert report["passed"] is True, report["failures"]
    assert report["status"] == "not_applicable_current_failure"
    assert "No intro-skip rerun is authorized" in report["approval_boundary"]


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


def test_rejects_visible_runtime_token_drift() -> None:
    data = reports()
    data["dry_run_plan"]["approval_gated_execute_command"] = command().replace(
        f"-VisibleRuntimeApprovalToken '{APPROVAL_TOKEN}' ",
        "",
    )
    data["dry_run_plan"]["plan"]["visible_runtime_approval"]["token"] = ""
    report = build_fixture_report(data)
    assert report["passed"] is False
    assert any("approval token" in failure for failure in report["failures"])


def test_rejects_visible_runtime_expiry_drift() -> None:
    data = reports()
    data["dry_run_plan"]["approval_gated_execute_command"] = command().replace(
        f"-VisibleRuntimeApprovalExpiresUtc '{APPROVAL_EXPIRES_UTC}' ",
        "",
    )
    data["dry_run_plan"]["plan"]["visible_runtime_approval"]["expires_utc"] = ""
    data["dry_run_plan"]["plan"]["visible_runtime_approval"]["token_fields"] = ["fixture"]
    report = build_fixture_report(data)
    assert report["passed"] is False
    assert any("approval expires_utc" in failure or "approval expiry" in failure for failure in report["failures"])


def later_step_reports(tmp: Path, current_index: int = 2) -> dict[str, dict[str, Any]]:
    data = reports()
    rows = []
    for index, step_id in enumerate(readiness.ORDERED_STEP_IDS):
        tier, _, tail = step_id.partition("_")
        row = {"id": step_id, "tier": tier, "route": tail.replace("_", "-"),
               "duration_sec": {"short2": 120, "short10": 600, "short30": 1800}[tier],
               "passed": index < current_index, "status": "pass" if index < current_index else "missing_pending_hidden_runtime",
               "prerequisites_passed": index <= current_index,
               "preferred_environment": "host_visible" if index == 0 else "hidden_cdb_host",
               "paths": {"report_json": str(tmp / f"{step_id}.json"), "guard_json": str(tmp / f"{step_id}-guard.json")}}
        rows.append(row)
        if index < current_index:
            source = soak_fixtures.passing_report(tmp) if index == 0 else soak_fixtures.passing_hidden_report(tmp)
            source["report_json"] = row["paths"]["report_json"]
            guard = hd_soak_report.evaluate_report_for_environment(source)
            assert guard["overall"], guard["failures"]
            guard["source_report"] = row["paths"]["report_json"]
            write_json(Path(row["paths"]["report_json"]), source)
            write_json(Path(row["paths"]["guard_json"]), guard)
    data["step_status"] = {"passed": True, "steps": rows, "current_step": {
        "id": rows[current_index]["id"], "status": "missing_pending_hidden_runtime", "preferred_environment": "hidden_cdb_host"}}
    data["triage"]["candidate_sha256"] = "c" * 64
    return data


def completed_ladder_status(tmp: Path) -> dict[str, Any]:
    """Synthetic temp-only source reports, graded by the real offline evaluator."""
    rows = []
    for index, definition in enumerate(readiness.SHORT_LADDER_STEPS):
        directory = tmp / definition["id"]
        directory.mkdir()
        factory = (soak_fixtures.passing_report if index == 0 else
                   soak_fixtures.passing_hidden_pan_report if definition["route"] == "map-pan" else
                   soak_fixtures.passing_hidden_report)
        source = factory(directory)
        source.update({key: definition[key] for key in ("tier", "route", "duration_sec")})
        duration = definition["duration_sec"]
        start = datetime(2026, 6, 16, 12, tzinfo=timezone.utc)
        for samples in (source["frame_samples"], source["process_samples"]):
            samples[-1]["Timestamp"] = (start + timedelta(seconds=duration)).isoformat()
        if index:
            source["route_start_marker"]["route_ticks"] = duration * 64
            source["route_end_marker"]["tick_delta"] = duration * 64
        paths = {"report_json": str(directory / "report.json"), "guard_json": str(directory / "guard.json")}
        source["report_json"] = paths["report_json"] if index == 0 else str(directory / "raw-report.json")
        evaluation = hd_soak_report.evaluate_report_for_environment(source)
        assert evaluation["overall"], (definition["id"], evaluation["failures"])
        # Current real source reports use absolute report_json while the
        # canonical status/guard can use the equivalent repo-relative path.
        if index == 0:
            paths["report_json"] = os.path.relpath(paths["report_json"])
        evaluation["source_report"] = paths["report_json"]
        write_json(Path(paths["report_json"]), source)
        if index:
            write_json(Path(source["report_json"]), source)
        write_json(Path(paths["guard_json"]), evaluation)
        rows.append({**definition, "status": "pass", "passed": True, "prerequisites_passed": True,
                     "preferred_environment": "host_visible" if index == 0 else "hidden_cdb_host", "paths": paths})
    return {"passed": True, "ladder_complete": True, "current_step": None,
            "protected_stable_stage": hd_soak_report.PROTECTED_STABLE_STAGE, "failures": [],
            "counts": {"total": 5, "passed": 5, "pending_or_missing": 0, "locked": 0, "failed_or_invalid": 0},
            "steps": rows}


COMPLETION_MUTATIONS = (
    "flag_false", "flag_missing", "flag_string", "nonnull_current", "missing_current", "wrong_count",
    "wrong_order", "wrong_tier", "wrong_duration", "wrong_prerequisites", "failed_prerequisite", "failed_step",
    "bool_only", "missing_report", "missing_guard", "wrong_source_path", "wrong_guard_path", "wrong_guard_sha",
    "unexecuted", "failed_source", "failed_guard", "failed_check", "bool_only_guard", "bool_only_source",
    "stale_elapsed_proof", "patch_changed", "missing_input_boundary", "wrong_stage", "malformed_steps",
    "malformed_guard_summary", "unreadable_guard", "missing_declared_report", "changed_declared_report",
)


def mutate_completed_ladder(status: dict[str, Any], mutation: str) -> None:
    row = status["steps"][-1]
    if mutation == "flag_false": status["ladder_complete"] = False
    elif mutation == "flag_missing": del status["ladder_complete"]
    elif mutation == "flag_string": status["ladder_complete"] = "true"
    elif mutation == "nonnull_current": status["current_step"] = {"id": row["id"], "status": "pass"}
    elif mutation == "missing_current": del status["current_step"]
    elif mutation == "wrong_count": status["counts"]["total"] = 4
    elif mutation == "wrong_order": status["steps"].reverse()
    elif mutation == "wrong_tier": row["tier"] = "short2"
    elif mutation == "wrong_duration": row["duration_sec"] = 120
    elif mutation == "wrong_prerequisites": row["prerequisites"] = []
    elif mutation == "failed_prerequisite": row["prerequisites_passed"] = False
    elif mutation == "failed_step": row["passed"] = False
    elif mutation == "bool_only": status["steps"] = [{"id": name, "passed": True} for name in readiness.ORDERED_STEP_IDS]
    elif mutation == "malformed_steps": status["steps"] = [None]
    elif mutation in ("missing_report", "missing_guard"):
        Path(row["paths"]["report_json" if mutation == "missing_report" else "guard_json"]).unlink()
    elif mutation == "unreadable_guard":
        Path(row["paths"]["guard_json"]).write_bytes(b"\xffinvalid-utf8")
    elif mutation in ("missing_declared_report", "changed_declared_report"):
        data = json.loads(Path(row["paths"]["report_json"]).read_text(encoding="utf-8"))
        declared = Path(data["report_json"])
        if mutation == "missing_declared_report": declared.unlink()
        else: declared.write_text("{}", encoding="utf-8")
    else:
        path = Path(row["paths"]["guard_json" if mutation in ("wrong_guard_path", "wrong_guard_sha", "failed_guard", "failed_check", "bool_only_guard", "malformed_guard_summary") else "report_json"])
        data = json.loads(path.read_text(encoding="utf-8"))
        if mutation == "wrong_source_path": data["report_json"] = status["steps"][0]["paths"]["report_json"]
        elif mutation == "wrong_guard_path": data["source_report"] = status["steps"][0]["paths"]["report_json"]
        elif mutation == "wrong_guard_sha": data["checks"]["patch_evidence"]["summary"]["candidate_sha256"] = "a" * 64
        elif mutation == "unexecuted": data["executed"] = False
        elif mutation == "failed_source": data["passed"] = False
        elif mutation == "failed_guard": data["overall"] = False
        elif mutation == "failed_check": data["checks"]["elapsed_coverage"]["passed"] = False
        elif mutation == "bool_only_guard": data = {"overall": True, "checks": {}}
        elif mutation == "malformed_guard_summary": data["checks"]["patch_evidence"]["summary"] = [True]
        elif mutation == "bool_only_source": data = {"executed": True, "passed": True, "stage": data["stage"], "tier": data["tier"], "route": data["route"]}
        elif mutation == "stale_elapsed_proof": data["frame_samples"][-1]["Timestamp"] = data["frame_samples"][0]["Timestamp"]
        elif mutation == "patch_changed":
            patch_path = Path(data["patch_stage_report"])
            patch = json.loads(patch_path.read_text(encoding="utf-8"))
            patch["exe_sha256"] = "a" * 64
            write_json(patch_path, patch)
        elif mutation == "missing_input_boundary": data["input_responsiveness"] = 0
        elif mutation == "wrong_stage": data["stage"] += "-validation"
        else: raise AssertionError(mutation)
        write_json(path, data)
        if mutation in ("stale_elapsed_proof", "missing_input_boundary", "unexecuted", "failed_source", "wrong_stage"):
            # Keep the canonical copy genuine so these cases exercise source
            # regrading, not merely the independent raw-copy identity check.
            write_json(Path(data["report_json"]), data)


def assert_terminal_no_authorization(report: dict[str, Any]) -> None:
    assert report["terminal_short_ladder"] is True
    assert report["runtime_authorized"] is False and report["approved"] is False
    assert report["approval_required"] is False and report["promotion_ready"] is False
    assert report["manual_input_proof"] is False
    assert report["current_step"] is None and report["commands"] == {} and report["plan"] == {}
    assert report["invocation"]["command"] is None and report["invocation"]["executed"] is False
    for name in ("recommended_runtime_command", "safe_dry_run_command", "approval_gated_execute_command",
                 "exact_runtime_command", "hidden_runtime_command"):
        assert report[name] is None, (name, report)
    assert report["locks"]["stable_stage_should_change"] is False
    assert len(report["remaining_requirements"]) == 3


def test_completed_ladder_requires_real_bound_reports_but_no_current_approval_packet() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        data = reports()
        data["step_status"] = completed_ladder_status(tmp)
        args = args_for(tmp, data)
        # Irrelevant historical/approval files must not be consumed by a terminal no-op.
        args.triage_json.write_text("not JSON", encoding="utf-8")
        report = readiness.build_report(args)
    assert report["passed"], report["failures"]
    assert report["status"] == "not_applicable_short_ladder_complete"
    assert len(report["completed_predecessor_evidence"]) == 5
    assert_terminal_no_authorization(report)
    assert "authorizes no runtime" in readiness.to_markdown(report)


def test_completed_ladder_rejects_forged_stale_or_mismatched_evidence() -> None:
    for mutation in COMPLETION_MUTATIONS:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            data = reports()
            data["step_status"] = completed_ladder_status(tmp)
            mutate_completed_ladder(data["step_status"], mutation)
            report = readiness.build_report(args_for(tmp, data))
        assert not report["passed"], (mutation, report)
        assert report["status"] == "invalid_short_ladder_completion", (mutation, report)
        assert_terminal_no_authorization(report)


def test_real_predecessor_reports_make_intro_readiness_historical() -> None:
    for index in (1, 2):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            data = later_step_reports(tmp, index)
            # Historical proof does not depend on an expired visible approval packet.
            data["dry_run_plan"] = {"passed": False, "status": "expired_visible_plan"}
            report = readiness.build_report(args_for(tmp, data))
        assert report["passed"], report["failures"]
        assert report["status"] == "not_applicable_later_step"
        assert len(report["completed_predecessor_evidence"]) == index
        assert report["dry_run_plan"]["approval_gated_execute_command"] is None
        assert "authorizes no runtime" in report["approval_boundary"]


def test_later_step_label_cannot_replace_canonical_predecessor_proof() -> None:
    for mutation in ("missing_report", "failed_guard", "unexecuted", "sha_mismatch", "prerequisite"):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            data = later_step_reports(tmp)
            first = data["step_status"]["steps"][0]
            report_path = Path(first["paths"]["report_json"])
            guard_path = Path(first["paths"]["guard_json"])
            if mutation == "missing_report":
                report_path.unlink()
            elif mutation == "failed_guard":
                guard = json.loads(guard_path.read_text(encoding="utf-8"))
                guard["overall"] = False
                write_json(guard_path, guard)
            elif mutation == "unexecuted":
                source = json.loads(report_path.read_text(encoding="utf-8"))
                source["executed"] = False
                write_json(report_path, source)
            elif mutation == "sha_mismatch":
                data["triage"]["candidate_sha256"] = "a" * 64
            else:
                data["step_status"]["steps"][1]["passed"] = False
            report = readiness.build_report(args_for(tmp, data))
        assert not report["passed"], (mutation, report)
        assert report["status"] == "not_ready"


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
    test_completed_ladder_requires_real_bound_reports_but_no_current_approval_packet()
    test_completed_ladder_rejects_forged_stale_or_mismatched_evidence()
    test_real_predecessor_reports_make_intro_readiness_historical()
    test_later_step_label_cannot_replace_canonical_predecessor_proof()
    test_ready_packet_passes()
    test_input_environment_denied_map_attempt_preserves_readiness()
    test_intro_transition_failure_preserves_readiness_after_harness_fix()
    test_legacy_pending_and_known_environment_failures_still_require_approval()
    test_unexpected_process_exit_is_not_applicable_not_rerun_ready()
    test_rejects_wrong_triage_classification()
    test_rejects_intro_skip_command_drift()
    test_rejects_visible_runtime_token_drift()
    test_rejects_visible_runtime_expiry_drift()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_intro_skip_rerun_readiness tests passed")
