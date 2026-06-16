#!/usr/bin/env python3
"""Fixture tests for hd_soak_approval_preflight.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import hd_soak_approval_preflight as preflight


RUNTIME_COMMAND = (
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
    ".\\scripts\\smoke\\run_hd_soak.ps1 "
    "-Tier short2 -Route menu-idle "
    f"-ReportJson {preflight.EXPECTED_REPORT_JSON} "
    f"-ReportMarkdown {preflight.EXPECTED_REPORT_MD} "
    f"-MaxInputDriftPx {preflight.EXPECTED_MAX_INPUT_DRIFT_PX} "
    "-Execute -AllowVisibleRuntime -RequirePass -Json"
)
DRY_RUN_COMMAND = (
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
    ".\\scripts\\smoke\\run_hd_soak.ps1 "
    "-Tier short2 -Route menu-idle "
    f"-ReportJson {preflight.EXPECTED_REPORT_JSON} "
    f"-ReportMarkdown {preflight.EXPECTED_REPORT_MD} "
    f"-MaxInputDriftPx {preflight.EXPECTED_MAX_INPUT_DRIFT_PX} "
    "-Json"
)


def write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="ascii")
    return path


def step_paths(slug: str) -> dict[str, str]:
    return {
        "report_json": f"captures\\current\\hd-soak-{slug}-current.json",
        "report_markdown": f"captures\\current\\hd-soak-{slug}-current.md",
        "guard_json": f"captures\\current\\hd-soak-{slug}-guard-current.json",
        "guard_markdown": f"captures\\current\\hd-soak-{slug}-guard-current.md",
        "triage_json": f"captures\\current\\hd-soak-{slug}-triage-current.json",
        "triage_markdown": f"captures\\current\\hd-soak-{slug}-triage-current.md",
    }


def harness_command(tier: str, route: str, paths: dict[str, str], *, execute: bool) -> str:
    parts = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        r".\scripts\smoke\run_hd_soak.ps1",
        "-Tier",
        tier,
        "-Route",
        route,
        "-ReportJson",
        paths["report_json"],
        "-ReportMarkdown",
        paths["report_markdown"],
        "-MaxInputDriftPx",
        str(preflight.EXPECTED_MAX_INPUT_DRIFT_PX),
    ]
    if execute:
        parts.extend(["-Execute", "-AllowVisibleRuntime", "-RequirePass"])
    parts.append("-Json")
    return " ".join(parts)


def step_record(step_id: str, tier: str, route: str, *, status: str, passed: bool = False) -> dict[str, Any]:
    slug = f"{tier}-{route}"
    paths = step_paths(slug)
    return {
        "id": step_id,
        "tier": tier,
        "route": route,
        "status": status,
        "passed": passed,
        "paths": paths,
        "safe_dry_run_command": harness_command(tier, route, paths, execute=False),
        "approval_gated_runtime_command": harness_command(tier, route, paths, execute=True),
        "writes_outside_repo": sorted(preflight.EXPECTED_WRITES),
        "must_not_modify": [preflight.MUST_NOT_MODIFY],
    }


def dry_run_plan_for_step(step: dict[str, Any]) -> dict[str, Any]:
    paths = step["paths"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": True,
        "status": "ready_for_explicit_approval",
        "current_step": {
            "id": step["id"],
            "status": step["status"],
            "tier": step["tier"],
            "route": step["route"],
            "duration_sec": 120,
            "paths": paths,
        },
        "plan": {
            "dry_run": True,
            "runtime_policy": "opt-in visible runtime soak; use -Execute -AllowVisibleRuntime only after explicit user approval",
            "input_exists": True,
            "input_sha256": "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae",
            "base_sha_status": "ok",
            "stage": "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch",
            "protected_stable_stage": "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch",
            "stable_stage_should_change": False,
            "tier": step["tier"],
            "duration_sec": 120,
            "route": step["route"],
            "candidate_dir": r"C:\ClashTests\hd-soak",
            "candidate_path": r"C:\ClashTests\hd-soak\clash95_hd_soak_fixture.exe",
            "output_root": r"C:\ClashCaptures\hd-soak",
            "report_json": paths["report_json"],
            "report_markdown": paths["report_markdown"],
            "input_limits": {"max_input_drift_px": preflight.EXPECTED_MAX_INPUT_DRIFT_PX},
            "right_bottom_promotion_blocked": True,
        },
        "approval_gated_execute_command": (
            "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
            r".\scripts\smoke\run_hd_soak.ps1 "
            rf"-InputExe {preflight.MUST_NOT_MODIFY} "
            r"-WorkDir C:\Clash "
            "-Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch "
            f"-Tier {step['tier']} -Route {step['route']} "
            r"-CandidateDir C:\ClashTests\hd-soak "
            "-CandidateName clash95_hd_soak_fixture.exe "
            r"-OutputRoot C:\ClashCaptures\hd-soak "
            f"-ReportJson {paths['report_json']} "
            f"-ReportMarkdown {paths['report_markdown']} "
            f"-MaxInputDriftPx {preflight.EXPECTED_MAX_INPUT_DRIFT_PX} "
            "-Execute -AllowVisibleRuntime -RequirePass -Json"
        ),
    }


def source_reports() -> dict[str, dict[str, Any]]:
    first_step = step_record("short2_menu_idle", "short2", "menu-idle", status="pending_approval_legacy_compat")
    dry_run_plan = dry_run_plan_for_step(first_step)
    return {
        "next_actions": {
            "passed": True,
            "status": "waiting_for_explicit_visible_runtime_approval",
            "next_action": {
                "source": "short_soak_step_status",
                "id": "run_short2_menu_idle_soak",
                "status": "approval_required",
                "short_step_id": preflight.EXPECTED_FIRST_STEP,
                "tier": "short2",
                "route": "menu-idle",
                "requires_visible_runtime": True,
                "requires_explicit_user_approval": True,
                "exact_runtime_command": dry_run_plan["approval_gated_execute_command"],
                "legacy_step_runtime_command": RUNTIME_COMMAND,
                "plan_verified_execute_command": dry_run_plan["approval_gated_execute_command"],
                "dry_run_plan": {
                    "passed": True,
                    "status": dry_run_plan["status"],
                    "current_step": preflight.EXPECTED_FIRST_STEP,
                    "candidate_path": dry_run_plan["plan"]["candidate_path"],
                    "candidate_dir": dry_run_plan["plan"]["candidate_dir"],
                    "output_root": dry_run_plan["plan"]["output_root"],
                    "report_json": dry_run_plan["plan"]["report_json"],
                    "report_markdown": dry_run_plan["plan"]["report_markdown"],
                    "input_sha256": dry_run_plan["plan"]["input_sha256"],
                    "base_sha_status": dry_run_plan["plan"]["base_sha_status"],
                    "execute_command": dry_run_plan["approval_gated_execute_command"],
                },
                "safe_dry_run_command": DRY_RUN_COMMAND,
                "writes_outside_repo": sorted(preflight.EXPECTED_WRITES),
                "must_not_modify": [preflight.MUST_NOT_MODIFY],
                "current_step_artifacts": preflight.current_step_artifact_inventory(first_step["paths"]),
                "post_run_validation": preflight.post_run_validation_for_step(first_step),
                "post_run_handoff_refresh": preflight.post_run_handoff_refresh_for_step(first_step),
                "post_run_evidence_refresh": preflight.post_run_evidence_refresh_commands(),
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
            "steps": [first_step],
        },
        "harness_guard": {"passed": True},
        "dry_run_plan": dry_run_plan,
        "visible_runtime_guard": {"passed": True},
        "process_hygiene": {"passed": True, "matching_process_count": 0},
        "exe_artifact": {"passed": True, "tracked_exes": []},
    }


def args_for(tmp: Path, reports: dict[str, dict[str, Any]]) -> argparse.Namespace:
    paths = {
        "next_actions_json": write_json(tmp / "next-actions.json", reports["next_actions"]),
        "step_status_json": write_json(tmp / "step-status.json", reports["step_status"]),
        "hd_soak_harness_guard_json": write_json(tmp / "harness-guard.json", reports["harness_guard"]),
        "hd_soak_dry_run_plan_json": write_json(tmp / "dry-run-plan.json", reports["dry_run_plan"]),
        "visible_runtime_guard_json": write_json(tmp / "visible-runtime-guard.json", reports["visible_runtime_guard"]),
        "process_hygiene_json": write_json(tmp / "process-hygiene.json", reports["process_hygiene"]),
        "exe_artifact_json": write_json(tmp / "exe-artifact.json", reports["exe_artifact"]),
    }
    return argparse.Namespace(**paths)


def build_fixture_report(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        return preflight.build_report(args_for(Path(directory), reports))


def test_current_preflight_passes_with_generated_reports() -> None:
    reports = source_reports()
    report = build_fixture_report(reports)
    assert report["passed"] is True, report["failures"]
    assert report["status"] == "ready_for_explicit_approval"
    assert report["approval_gated_runtime_command"] == reports["dry_run_plan"]["approval_gated_execute_command"]
    assert report["legacy_step_runtime_command"] == RUNTIME_COMMAND
    assert report["safe_dry_run_command"] == DRY_RUN_COMMAND
    assert "hd_soak_short_validation_refresh.py" in report["post_run_validation"][0]
    assert "hd_soak_report.py" not in " ".join(report["post_run_validation"])
    assert report["next_action_consistency"]["approval_command_uses_dry_run_plan"] is True
    assert report["next_action_consistency"]["current_step_artifacts_match"] is True
    assert "-InputExe" in report["approval_gated_runtime_command"]
    assert r"C:\ClashTests\hd-soak" in report["approval_gated_runtime_command"]
    assert report["dry_run_plan_consistency"]["candidate_path"].endswith("clash95_hd_soak_fixture.exe")
    assert "input drift <= 1px" in report["approval_prompt"]
    assert report["locks"]["stable_stage_should_change"] is False
    assert report["locks"]["right_bottom_promotion_blocked"] is True


def test_current_preflight_records_current_step_artifact_inventory() -> None:
    reports = source_reports()
    report = build_fixture_report(reports)
    artifacts = report["current_step_artifacts"]
    assert artifacts["report_json"] == preflight.EXPECTED_REPORT_JSON
    assert artifacts["report_json_exists"] is False
    assert artifacts["guard_json"] == preflight.EXPECTED_GUARD_JSON
    assert artifacts["guard_json_exists"] is False
    assert artifacts["triage_json"] == preflight.EXPECTED_TRIAGE_JSON
    assert artifacts["triage_json_exists"] is False
    assert artifacts["canonical_runtime_report_missing"] is True
    assert artifacts["post_run_guard_missing"] is True
    assert artifacts["post_run_triage_missing"] is True


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
    reports["step_status"]["steps"][0]["safe_dry_run_command"] = DRY_RUN_COMMAND + " -Execute"
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("safe dry-run command includes execution" in failure for failure in report["failures"])


def test_step_status_command_must_match_next_actions() -> None:
    reports = source_reports()
    reports["step_status"]["current_step"]["next_command"] = "powershell.exe bad-command"
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("legacy step runtime command" in failure for failure in report["failures"])


def test_next_actions_dry_run_must_match_step_status() -> None:
    reports = source_reports()
    reports["next_actions"]["next_action"]["safe_dry_run_command"] = "powershell.exe bad-dry-run"
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("next-actions dry-run command does not match" in failure for failure in report["failures"])


def test_next_actions_post_run_validation_must_match_step_status() -> None:
    reports = source_reports()
    reports["next_actions"]["next_action"]["post_run_validation"] = ["git diff --check"]
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("next-actions post-run validation does not match" in failure for failure in report["failures"])


def test_next_actions_post_run_handoff_refresh_must_match_step_status() -> None:
    reports = source_reports()
    reports["next_actions"]["next_action"]["post_run_handoff_refresh"] = ["git diff --check"]
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("post-run handoff refresh" in failure for failure in report["failures"])


def test_next_actions_post_run_evidence_refresh_must_match_preflight() -> None:
    reports = source_reports()
    reports["next_actions"]["next_action"]["post_run_evidence_refresh"] = ["git diff --check"]
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("post-run evidence refresh" in failure for failure in report["failures"])


def test_next_actions_artifact_inventory_must_match_preflight() -> None:
    reports = source_reports()
    reports["next_actions"]["next_action"]["current_step_artifacts"]["report_json_exists"] = True
    reports["next_actions"]["next_action"]["current_step_artifacts"]["triage_json"] = r"captures\current\wrong.json"
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert report["next_action_consistency"]["current_step_artifacts_match"] is False
    assert set(report["next_action_consistency"]["current_step_artifact_mismatch_keys"]) == {
        "report_json_exists",
        "triage_json",
    }
    assert any("artifact inventory does not match" in failure for failure in report["failures"])


def test_next_actions_plan_verified_command_must_match_dry_run_plan() -> None:
    reports = source_reports()
    reports["next_actions"]["next_action"]["plan_verified_execute_command"] = reports["next_actions"]["next_action"][
        "plan_verified_execute_command"
    ].replace("-RequirePass ", "")
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("plan-verified execute command" in failure for failure in report["failures"])


def test_next_actions_dry_run_plan_summary_must_match_current_dry_run_plan() -> None:
    reports = source_reports()
    reports["next_actions"]["next_action"]["dry_run_plan"]["candidate_path"] = (
        r"C:\ClashTests\hd-soak\clash95_hd_soak_stale.exe"
    )
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert report["next_action_consistency"]["dry_run_plan_summary_matches"] is False
    assert report["next_action_consistency"]["dry_run_plan_summary_mismatch_keys"] == ["candidate_path"]
    assert any("dry-run plan summary does not match" in failure for failure in report["failures"])


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


def test_dry_run_plan_source_must_pass() -> None:
    reports = source_reports()
    reports["dry_run_plan"]["passed"] = False
    reports["dry_run_plan"]["status"] = "dry_run_plan_invalid"
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("dry-run plan report is not passing" in failure for failure in report["failures"])
    assert any("dry_run_plan is not passing" in failure for failure in report["failures"])


def test_stale_dry_run_plan_fails_closed() -> None:
    reports = source_reports()
    reports["dry_run_plan"]["generated_at"] = (
        datetime.now(timezone.utc) - timedelta(hours=preflight.MAX_DRY_RUN_PLAN_AGE_HOURS + 1)
    ).isoformat()
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("dry-run plan is older" in failure for failure in report["failures"])
    assert report["dry_run_plan_consistency"]["freshness"]["passed"] is False


def test_dry_run_plan_must_match_current_step_and_paths() -> None:
    reports = source_reports()
    reports["dry_run_plan"]["current_step"]["id"] = "short2_map_idle"
    reports["dry_run_plan"]["approval_gated_execute_command"] = reports["dry_run_plan"][
        "approval_gated_execute_command"
    ].replace(preflight.EXPECTED_REPORT_JSON, r"captures\current\wrong.json")
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("dry-run plan current step does not match" in failure for failure in report["failures"])
    assert any("canonical report JSON" in failure for failure in report["failures"])


def test_dry_run_plan_must_confirm_base_input() -> None:
    reports = source_reports()
    reports["dry_run_plan"]["plan"]["input_exists"] = False
    reports["dry_run_plan"]["plan"]["base_sha_status"] = "missing"
    reports["next_actions"]["next_action"]["dry_run_plan"]["base_sha_status"] = "missing"
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("input_exe does not exist" in failure for failure in report["failures"])
    assert any("base_sha_status" in failure for failure in report["failures"])


def test_dry_run_plan_execute_command_must_pin_stage_and_roots() -> None:
    reports = source_reports()
    bad_command = reports["dry_run_plan"]["approval_gated_execute_command"]
    for fragment in (
        rf"-InputExe {preflight.MUST_NOT_MODIFY} ",
        r"-WorkDir C:\Clash ",
        "-Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch ",
        r"-OutputRoot C:\ClashCaptures\hd-soak ",
    ):
        bad_command = bad_command.replace(fragment, "")
    reports["dry_run_plan"]["approval_gated_execute_command"] = bad_command
    reports["next_actions"]["next_action"]["plan_verified_execute_command"] = bad_command
    reports["next_actions"]["next_action"]["dry_run_plan"]["execute_command"] = bad_command
    report = build_fixture_report(reports)
    assert report["passed"] is False
    assert any("dry-run plan execute command missing fragment: -InputExe" in failure for failure in report["failures"])
    assert any("dry-run plan execute command missing fragment: -Stage" in failure for failure in report["failures"])
    assert any("dry-run plan execute command missing fragment: -OutputRoot" in failure for failure in report["failures"])


def test_later_short_step_preflight_uses_step_status_without_first_next_action() -> None:
    reports = source_reports()
    first = step_record("short2_menu_idle", "short2", "menu-idle", status="pass", passed=True)
    second = step_record("short2_map_idle", "short2", "map-idle", status="missing_pending_approval")
    reports["step_status"] = {
        "passed": True,
        "ladder_complete": False,
        "current_step": {
            "id": "short2_map_idle",
            "status": "missing_pending_approval",
            "next_command": second["approval_gated_runtime_command"],
        },
        "steps": [first, second],
    }
    reports["next_actions"] = {
        "passed": True,
        "status": "waiting_for_explicit_visible_runtime_approval",
        "next_action": {
            "source": "short_soak_step_status",
            "id": "run_short2_map_idle_soak",
            "status": "approval_required",
            "short_step_id": "short2_map_idle",
            "tier": "short2",
            "route": "map-idle",
            "requires_visible_runtime": True,
            "requires_explicit_user_approval": True,
            "exact_runtime_command": dry_run_plan_for_step(second)["approval_gated_execute_command"],
            "legacy_step_runtime_command": second["approval_gated_runtime_command"],
            "plan_verified_execute_command": dry_run_plan_for_step(second)["approval_gated_execute_command"],
            "dry_run_plan": {
                "passed": True,
                "status": "ready_for_explicit_approval",
                "current_step": "short2_map_idle",
                "candidate_path": r"C:\ClashTests\hd-soak\clash95_hd_soak_fixture.exe",
                "candidate_dir": r"C:\ClashTests\hd-soak",
                "output_root": r"C:\ClashCaptures\hd-soak",
            },
            "safe_dry_run_command": second["safe_dry_run_command"],
            "writes_outside_repo": sorted(preflight.EXPECTED_WRITES),
            "must_not_modify": [preflight.MUST_NOT_MODIFY],
            "current_step_artifacts": preflight.current_step_artifact_inventory(second["paths"]),
            "post_run_validation": preflight.post_run_validation_for_step(second),
            "post_run_handoff_refresh": preflight.post_run_handoff_refresh_for_step(second),
            "post_run_evidence_refresh": preflight.post_run_evidence_refresh_commands(),
        },
    }
    reports["dry_run_plan"] = dry_run_plan_for_step(second)
    reports["next_actions"]["next_action"]["dry_run_plan"].update(
        {
            "report_json": reports["dry_run_plan"]["plan"]["report_json"],
            "report_markdown": reports["dry_run_plan"]["plan"]["report_markdown"],
            "input_sha256": reports["dry_run_plan"]["plan"]["input_sha256"],
            "base_sha_status": reports["dry_run_plan"]["plan"]["base_sha_status"],
            "execute_command": reports["dry_run_plan"]["approval_gated_execute_command"],
        }
    )
    report = build_fixture_report(reports)
    assert report["passed"] is True, report["failures"]
    assert report["current_step"]["id"] == "short2_map_idle"
    assert "-Route map-idle" in report["approval_gated_runtime_command"]
    assert "-InputExe" in report["approval_gated_runtime_command"]
    assert report["current_step_artifacts"]["guard_json"] == r"captures\current\hd-soak-short2-map-idle-guard-current.json"
    assert "hd_soak_short_validation_refresh.py" in report["post_run_validation"][0]


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
                "--hd-soak-dry-run-plan-json",
                str(args.hd_soak_dry_run_plan_json),
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
    test_current_preflight_records_current_step_artifact_inventory()
    test_runtime_command_requires_visible_runtime_and_canonical_paths()
    test_dry_run_must_not_execute()
    test_step_status_command_must_match_next_actions()
    test_next_actions_dry_run_must_match_step_status()
    test_next_actions_post_run_validation_must_match_step_status()
    test_next_actions_post_run_handoff_refresh_must_match_step_status()
    test_next_actions_post_run_evidence_refresh_must_match_preflight()
    test_next_actions_artifact_inventory_must_match_preflight()
    test_next_actions_plan_verified_command_must_match_dry_run_plan()
    test_next_actions_dry_run_plan_summary_must_match_current_dry_run_plan()
    test_step_status_must_be_pending_first_step()
    test_guard_source_must_pass()
    test_dry_run_plan_source_must_pass()
    test_stale_dry_run_plan_fails_closed()
    test_dry_run_plan_must_match_current_step_and_paths()
    test_dry_run_plan_must_confirm_base_input()
    test_dry_run_plan_execute_command_must_pin_stage_and_roots()
    test_later_short_step_preflight_uses_step_status_without_first_next_action()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_approval_preflight tests passed")
