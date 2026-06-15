#!/usr/bin/env python3
"""Fixture tests for hd_soak_approval_preflight.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import hd_soak_approval_preflight as preflight


RUNTIME_COMMAND = (
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
    ".\\scripts\\smoke\\run_hd_soak.ps1 "
    "-Tier short2 -Route menu-idle "
    f"-ReportJson {preflight.EXPECTED_REPORT_JSON} "
    f"-ReportMarkdown {preflight.EXPECTED_REPORT_MD} "
    "-Execute -AllowVisibleRuntime -RequirePass -Json"
)
DRY_RUN_COMMAND = (
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
    ".\\scripts\\smoke\\run_hd_soak.ps1 "
    "-Tier short2 -Route menu-idle "
    f"-ReportJson {preflight.EXPECTED_REPORT_JSON} "
    f"-ReportMarkdown {preflight.EXPECTED_REPORT_MD} "
    "-Json"
)


def write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="ascii")
    return path


def source_reports() -> dict[str, dict[str, Any]]:
    return {
        "next_actions": {
            "passed": True,
            "status": "waiting_for_explicit_visible_runtime_approval",
            "next_action": {
                "id": "run_short2_menu_idle_soak",
                "requires_visible_runtime": True,
                "requires_explicit_user_approval": True,
                "exact_runtime_command": RUNTIME_COMMAND,
                "safe_dry_run_command": DRY_RUN_COMMAND,
                "writes_outside_repo": sorted(preflight.EXPECTED_WRITES),
                "must_not_modify": [preflight.MUST_NOT_MODIFY],
                "post_run_validation": [
                    f"python tools\\hd_soak_report.py {preflight.EXPECTED_REPORT_JSON} "
                    f"--write-json {preflight.EXPECTED_GUARD_JSON} --require-pass",
                    f"python tools\\hd_soak_failure_triage.py {preflight.EXPECTED_REPORT_JSON} "
                    f"--write-json {preflight.EXPECTED_TRIAGE_JSON}",
                    "python tools\\current_evidence_refresh.py",
                    "python tools\\evidence_index_check.py captures\\current\\hd-map-evidence-current.md --require-pass",
                    "git diff --check",
                ],
            },
        },
        "step_status": {
            "passed": True,
            "ladder_complete": False,
            "current_step": {
                "id": preflight.EXPECTED_FIRST_STEP,
                "status": "pending_approval_legacy_compat",
                "next_command": RUNTIME_COMMAND,
            },
        },
        "harness_guard": {"passed": True},
        "visible_runtime_guard": {"passed": True},
        "process_hygiene": {"passed": True, "matching_process_count": 0},
        "exe_artifact": {"passed": True, "tracked_exes": []},
    }


def args_for(tmp: Path, reports: dict[str, dict[str, Any]]) -> argparse.Namespace:
    paths = {
        "next_actions_json": write_json(tmp / "next-actions.json", reports["next_actions"]),
        "step_status_json": write_json(tmp / "step-status.json", reports["step_status"]),
        "hd_soak_harness_guard_json": write_json(tmp / "harness-guard.json", reports["harness_guard"]),
        "visible_runtime_guard_json": write_json(tmp / "visible-runtime-guard.json", reports["visible_runtime_guard"]),
        "process_hygiene_json": write_json(tmp / "process-hygiene.json", reports["process_hygiene"]),
        "exe_artifact_json": write_json(tmp / "exe-artifact.json", reports["exe_artifact"]),
    }
    return argparse.Namespace(**paths)


def build_fixture_report(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        return preflight.build_report(args_for(Path(directory), reports))


def test_current_preflight_passes_with_generated_reports() -> None:
    report = build_fixture_report(source_reports())
    assert report["passed"] is True, report["failures"]
    assert report["status"] == "ready_for_explicit_approval"
    assert report["approval_gated_runtime_command"] == RUNTIME_COMMAND
    assert report["safe_dry_run_command"] == DRY_RUN_COMMAND
    assert report["locks"]["stable_stage_should_change"] is False
    assert report["locks"]["right_bottom_promotion_blocked"] is True


def test_runtime_command_requires_visible_runtime_and_canonical_paths() -> None:
    reports = source_reports()
    action = reports["next_actions"]["next_action"]
    action["exact_runtime_command"] = RUNTIME_COMMAND.replace(" -AllowVisibleRuntime", "")
    action["exact_runtime_command"] = action["exact_runtime_command"].replace(
        preflight.EXPECTED_REPORT_JSON,
        r"captures\current\hd-soak-short-current.json",
    )
    reports["step_status"]["current_step"]["next_command"] = action["exact_runtime_command"]
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("runtime command missing fragment" in failure for failure in report["failures"])


def test_dry_run_must_not_execute() -> None:
    reports = source_reports()
    reports["next_actions"]["next_action"]["safe_dry_run_command"] = DRY_RUN_COMMAND + " -Execute"
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("safe dry-run command includes execution" in failure for failure in report["failures"])


def test_step_status_command_must_match_next_actions() -> None:
    reports = source_reports()
    reports["step_status"]["current_step"]["next_command"] = "powershell.exe bad-command"
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("step-status next command does not match" in failure for failure in report["failures"])


def test_step_status_must_be_pending_first_step() -> None:
    reports = source_reports()
    reports["step_status"]["current_step"]["status"] = "passed"
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("current short-step status" in failure for failure in report["failures"])


def test_guard_source_must_pass() -> None:
    reports = source_reports()
    reports["process_hygiene"] = {
        "passed": False,
        "matching_process_count": 1,
    }
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("process_hygiene is not passing" in failure for failure in report["failures"])
    assert any("stale cdb/clash95 processes" in failure for failure in report["failures"])


def test_cli_writes_outputs() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        reports = source_reports()
        args = args_for(tmp, reports)
        json_out = tmp / "preflight.json"
        md_out = tmp / "preflight.md"
        script = Path(__file__).resolve().parent / "hd_soak_approval_preflight.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--next-actions-json",
                str(args.next_actions_json),
                "--step-status-json",
                str(args.step_status_json),
                "--hd-soak-harness-guard-json",
                str(args.hd_soak_harness_guard_json),
                "--visible-runtime-guard-json",
                str(args.visible_runtime_guard_json),
                "--process-hygiene-json",
                str(args.process_hygiene_json),
                "--exe-artifact-json",
                str(args.exe_artifact_json),
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
    test_current_preflight_passes_with_generated_reports()
    test_runtime_command_requires_visible_runtime_and_canonical_paths()
    test_dry_run_must_not_execute()
    test_step_status_command_must_match_next_actions()
    test_step_status_must_be_pending_first_step()
    test_guard_source_must_pass()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_approval_preflight tests passed")
