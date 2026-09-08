#!/usr/bin/env python3
"""Fixture tests for hd_soak_dry_run_plan.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "hd_soak_dry_run_plan.py"
sys.path.insert(0, str(ROOT / "tools"))

import hd_soak_dry_run_plan as dry_run_plan  # noqa: E402
import test_hd_soak_intro_skip_rerun_readiness as intro_fixtures  # noqa: E402


STEP_ID = "short2_menu_idle"
TIER = "short2"
ROUTE = "menu-idle"
DURATION = 120
APPROVAL_EXPIRES_UTC = "2999-01-01T00:00:00.0000000+00:00"


def write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="ascii")
    return path


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def step_paths() -> dict[str, str]:
    return {
        "report_json": r"captures\current\hd-soak-short2-menu-idle-current.json",
        "report_markdown": r"captures\current\hd-soak-short2-menu-idle-current.md",
        "guard_json": r"captures\current\hd-soak-short2-menu-idle-guard-current.json",
        "guard_markdown": r"captures\current\hd-soak-short2-menu-idle-guard-current.md",
        "triage_json": r"captures\current\hd-soak-short2-menu-idle-triage-current.json",
        "triage_markdown": r"captures\current\hd-soak-short2-menu-idle-triage-current.md",
    }


def step_status() -> dict[str, Any]:
    paths = step_paths()
    return {
        "passed": True,
        "current_step": {
            "id": STEP_ID,
            "tier": TIER,
            "route": ROUTE,
            "status": "pending_approval_legacy_compat",
            "next_command": (
                r"powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 "
                rf"-Tier {TIER} -Route {ROUTE} -ReportJson {paths['report_json']} "
                rf"-ReportMarkdown {paths['report_markdown']} "
                "-IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4 "
                "-SampleIntervalSec 15 -MaxInputDriftPx 1 "
                "-MinNonblackPercent 10 -MinUniqueSampleColors 8 "
                "-MaxArtifactMB 250 -MaxWorkingSetGrowthMB 64 "
                "-MaxPrivateMemoryGrowthMB 64 -MaxHandleGrowth 128 "
                "-Execute -AllowVisibleRuntime -RequirePass -Json"
            ),
        },
        "steps": [
            {
                "id": STEP_ID,
                "tier": TIER,
                "route": ROUTE,
                "duration_sec": DURATION,
                "paths": paths,
            }
        ],
    }


def abs_report_path(key: str) -> str:
    return str(ROOT / step_paths()[key].replace("\\", "/"))


def valid_plan() -> dict[str, Any]:
    candidate = r"C:\ClashTests\hd-soak\clash95_hd_soak_fixture.exe"
    report_json = abs_report_path("report_json")
    report_md = abs_report_path("report_markdown")
    approval_token = "1234567890abcdef"
    return {
        "dry_run": True,
        "runtime_policy": "opt-in visible runtime soak; use -Execute -AllowVisibleRuntime only after explicit user approval",
        "repo_root": str(ROOT),
        "input_exe": dry_run_plan.EXPECTED_INPUT_EXE,
        "input_exists": True,
        "expected_base_sha256": dry_run_plan.EXPECTED_BASE_SHA256,
        "input_sha256": dry_run_plan.EXPECTED_BASE_SHA256,
        "base_sha_status": "ok",
        "stage": dry_run_plan.PROTECTED_STABLE_STAGE,
        "protected_stable_stage": dry_run_plan.PROTECTED_STABLE_STAGE,
        "stable_stage_should_change": False,
        "tier": TIER,
        "duration_sec": DURATION,
        "route": ROUTE,
        "route_steps": [],
        "sample_interval_sec": 15,
        "candidate_dir": dry_run_plan.EXPECTED_CANDIDATE_DIR,
        "candidate_path": candidate,
        "workdir": dry_run_plan.EXPECTED_WORKDIR,
        "output_root": dry_run_plan.EXPECTED_OUTPUT_ROOT,
        "report_json": report_json,
        "report_markdown": report_md,
        "growth_limits": {
            "max_working_set_growth_mb": 64,
            "max_private_memory_growth_mb": 64,
            "max_handle_growth": 128,
            "max_artifact_mb": 250,
        },
        "frame_limits": {
            "min_nonblack_percent": 10.0,
            "min_unique_sample_colors": 8,
        },
        "input_limits": {"max_input_drift_px": 1},
        "intro_skip": {
            "click_mode": dry_run_plan.EXPECTED_INTRO_SKIP_CLICK_MODE,
            "click_repeat": dry_run_plan.EXPECTED_INTRO_SKIP_CLICKS,
            "space_pulses": dry_run_plan.EXPECTED_SKIP_PULSES,
            "proof_class": "intro_skip_harness_prep_not_manual_directinput_release_proof",
        },
        "visible_runtime_approval": {
            "token": approval_token,
            "token_kind": "sha256-16",
            "expires_utc": APPROVAL_EXPIRES_UTC,
            "max_age_hours": dry_run_plan.APPROVAL_MAX_AGE_HOURS,
            "min_ttl_minutes": dry_run_plan.MIN_APPROVAL_TTL_MINUTES,
            "token_fields": [
                dry_run_plan.EXPECTED_INPUT_EXE,
                dry_run_plan.EXPECTED_WORKDIR,
                dry_run_plan.PROTECTED_STABLE_STAGE,
                TIER,
                ROUTE,
                str(DURATION),
                dry_run_plan.EXPECTED_CANDIDATE_DIR,
                "clash95_hd_soak_fixture.exe",
                dry_run_plan.EXPECTED_OUTPUT_ROOT,
                report_json,
                report_md,
                "postmessage",
                "8",
                "4",
                "1",
                "15",
                "10",
                "8",
                "250",
                "64",
                "64",
                "128",
                APPROVAL_EXPIRES_UTC,
            ],
            "purpose": "copy-exact dry-run approval packet; edited, stale, or hand-typed visible runtime commands fail closed",
        },
        "raw_artifacts_policy": "raw PNG frames and per-step logs stay outside the repository by default",
        "right_bottom_promotion_blocked": True,
        "commands": {
            "patch": (
                rf"& 'python' 'patch_clash95_hd.py' --input '{dry_run_plan.EXPECTED_INPUT_EXE}' "
                rf"--output '{candidate}' --stage '{dry_run_plan.PROTECTED_STABLE_STAGE}'"
            ),
            "execute": (
                rf"powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\smoke\run_hd_soak.ps1' "
                rf"-InputExe '{dry_run_plan.EXPECTED_INPUT_EXE}' -WorkDir '{dry_run_plan.EXPECTED_WORKDIR}' "
                rf"-Stage '{dry_run_plan.PROTECTED_STABLE_STAGE}' -Tier '{TIER}' -Route '{ROUTE}' "
                rf"-CandidateDir '{dry_run_plan.EXPECTED_CANDIDATE_DIR}' "
                rf"-CandidateName 'clash95_hd_soak_fixture.exe' -OutputRoot '{dry_run_plan.EXPECTED_OUTPUT_ROOT}' "
                rf"-ReportJson '{report_json}' "
                rf"-ReportMarkdown '{report_md}' "
                "-IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' "
                "-SampleIntervalSec '15' -MaxInputDriftPx '1' "
                "-MinNonblackPercent '10' -MinUniqueSampleColors '8' "
                "-MaxArtifactMB '250' -MaxWorkingSetGrowthMB '64' "
                "-MaxPrivateMemoryGrowthMB '64' -MaxHandleGrowth '128' "
                f"-VisibleRuntimeApprovalExpiresUtc '{APPROVAL_EXPIRES_UTC}' "
                f"-VisibleRuntimeApprovalToken '{approval_token}' "
                "-Execute -AllowVisibleRuntime -RequirePass -Json"
            ),
        },
    }


def hidden_step_status() -> dict[str, Any]:
    data = step_status()
    step = data["steps"][0]
    step.update(id="short10_map_idle", tier="short10", route="map-idle", duration_sec=600,
                preferred_environment="hidden_cdb_host", prerequisites_passed=True)
    step["paths"] = {name: path.replace("short2-menu-idle", "short10-map-idle") for name, path in step["paths"].items()}
    data["current_step"] = {"id": step["id"], "status": "missing_pending_hidden_runtime", "preferred_environment": "hidden_cdb_host"}
    return data


def valid_hidden_plan() -> dict[str, Any]:
    step = hidden_step_status()["steps"][0]
    options = {
        "Route": "map-idle", "DurationSec": 600, "FrameIntervalSec": 15, "PanIntervalSec": 10,
        "LoadSlot": 2, "ReadyTimeoutSec": 240, "EndGraceSec": 180, "PngEdgeCount": 3,
        "MaxArtifactMB": 250, "MaxWorkingSetGrowthMB": 64, "MaxPrivateMemoryGrowthMB": 64,
        "MaxHandleGrowth": 128, "Python": sys.executable,
        "ProbeTemplate": ROOT / "probes/cdb/render/clash95_surface_dump_probe.cdb",
        "SoakProbeTemplate": ROOT / "probes/cdb/soak/clash95_hidden_soak_route_extra.cdb",
        "DdrawProxyBuildScript": ROOT / "scripts/build/build_ddraw_surfdump_proxy.ps1",
        "ReportJson": step["paths"]["report_json"], "ReportMarkdown": step["paths"]["report_markdown"],
        "GuardJson": step["paths"]["guard_json"], "GuardMarkdown": step["paths"]["guard_markdown"],
    }
    command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File '" + str(ROOT / dry_run_plan.HIDDEN_SCRIPT) + "'"
    command += "".join(f" -{name} '{value}'" for name, value in options.items())
    command += " -Execute -RequirePass -Json"
    return {
        "executed": False, "preflight_passed": True, "environment": "hidden_cdb_host",
        "route": "map-idle", "duration_sec": 600, "input_sha256": dry_run_plan.EXPECTED_BASE_SHA256,
        "candidate_run_directory": dry_run_plan.HIDDEN_CANDIDATE_ROOT + r"\fixture",
        "output_directory": dry_run_plan.HIDDEN_OUTPUT_ROOT + r"\fixture",
        "hidden_runtime_command": command,
    }


def args_for(tmp: Path, plan: dict[str, Any], status_data: dict[str, Any] | None = None) -> argparse.Namespace:
    return argparse.Namespace(
        step_status_json=write_json(tmp / "step-status.json", status_data or step_status()),
        script=Path("scripts/smoke/run_hd_soak.ps1"),
        read_plan_json=write_json(tmp / "plan.json", plan),
    )


def build_fixture_report(plan: dict[str, Any], status_data: dict[str, Any] | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temporary:
        return dry_run_plan.build_report(args_for(Path(temporary), plan, status_data))


def test_valid_plan_passes() -> None:
    report = build_fixture_report(valid_plan())
    assert report["passed"] is True, report
    assert report["status"] == "ready_for_explicit_approval"
    assert report["approval_ttl"]["passed"] is True
    assert report["approval_ttl"]["min_remaining_minutes"] == dry_run_plan.MIN_APPROVAL_TTL_MINUTES
    assert "-RequirePass -Json" in report["approval_gated_execute_command"]
    assert report["locks"]["right_bottom_promotion_blocked"] is True


def test_rejects_executed_plan() -> None:
    plan = valid_plan()
    plan["dry_run"] = False
    report = build_fixture_report(plan)
    assert report["passed"] is False, report
    assert any("not marked as a dry run" in failure for failure in report["failures"])


def test_rejects_stage_drift() -> None:
    plan = valid_plan()
    plan["stage"] = "validation-only-stage"
    report = build_fixture_report(plan)
    assert report["passed"] is False, report
    assert any("expected protected stable stage" in failure for failure in report["failures"])


def test_rejects_execute_command_without_require_pass_or_json() -> None:
    plan = valid_plan()
    plan["commands"]["execute"] = plan["commands"]["execute"].replace(" -RequirePass -Json", "")
    report = build_fixture_report(plan)
    assert report["passed"] is False, report
    assert any("execute command missing fragment: -RequirePass" in failure for failure in report["failures"])
    assert any("execute command missing fragment: -Json" in failure for failure in report["failures"])


def test_rejects_missing_visible_runtime_token() -> None:
    plan = valid_plan()
    plan["visible_runtime_approval"]["token"] = ""
    plan["commands"]["execute"] = plan["commands"]["execute"].replace(
        "-VisibleRuntimeApprovalToken '1234567890abcdef' ",
        "",
    )
    report = build_fixture_report(plan)
    assert report["passed"] is False, report
    assert any("approval token" in failure for failure in report["failures"])
    assert any("execute command missing fragment: -VisibleRuntimeApprovalToken" in failure for failure in report["failures"])


def test_rejects_missing_visible_runtime_expiry() -> None:
    plan = valid_plan()
    plan["visible_runtime_approval"]["expires_utc"] = ""
    plan["visible_runtime_approval"]["max_age_hours"] = 0
    plan["visible_runtime_approval"]["token_fields"] = [
        field
        for field in plan["visible_runtime_approval"]["token_fields"]
        if field != APPROVAL_EXPIRES_UTC
    ]
    plan["commands"]["execute"] = plan["commands"]["execute"].replace(
        f"-VisibleRuntimeApprovalExpiresUtc '{APPROVAL_EXPIRES_UTC}' ",
        "",
    )
    report = build_fixture_report(plan)
    assert report["passed"] is False, report
    assert any("approval expires_utc" in failure for failure in report["failures"])
    assert any("approval max_age_hours" in failure for failure in report["failures"])
    assert any("expiry is not covered" in failure for failure in report["failures"])
    assert any("execute command missing fragment: -VisibleRuntimeApprovalExpiresUtc" in failure for failure in report["failures"])


def test_rejects_nearly_expired_visible_runtime_approval() -> None:
    plan = valid_plan()
    old_expiry = APPROVAL_EXPIRES_UTC
    new_expiry = (
        datetime.now(timezone.utc) + timedelta(minutes=dry_run_plan.MIN_APPROVAL_TTL_MINUTES - 1)
    ).isoformat()
    approval = plan["visible_runtime_approval"]
    approval["expires_utc"] = new_expiry
    approval["token_fields"] = [new_expiry if field == old_expiry else field for field in approval["token_fields"]]
    plan["commands"]["execute"] = plan["commands"]["execute"].replace(old_expiry, new_expiry)
    report = build_fixture_report(plan)
    assert report["passed"] is False, report
    assert report["approval_ttl"]["passed"] is False
    assert any("approval expires too soon" in failure for failure in report["failures"])


def test_rejects_missing_intro_skip_plan_fields() -> None:
    plan = valid_plan()
    plan["intro_skip"]["click_mode"] = "sendinput"
    plan["commands"]["execute"] = plan["commands"]["execute"].replace("-IntroSkipClickMode 'postmessage' ", "")
    report = build_fixture_report(plan)
    assert report["passed"] is False, report
    assert any("intro_skip click_mode" in failure for failure in report["failures"])
    assert any("execute command missing fragment: -IntroSkipClickMode" in failure for failure in report["failures"])


def test_rejects_execute_command_without_explicit_stage_or_io_roots() -> None:
    plan = valid_plan()
    for fragment in (
        rf"-InputExe '{dry_run_plan.EXPECTED_INPUT_EXE}' ",
        rf"-WorkDir '{dry_run_plan.EXPECTED_WORKDIR}' ",
        rf"-Stage '{dry_run_plan.PROTECTED_STABLE_STAGE}' ",
        rf"-OutputRoot '{dry_run_plan.EXPECTED_OUTPUT_ROOT}' ",
    ):
        plan["commands"]["execute"] = plan["commands"]["execute"].replace(fragment, "")
    report = build_fixture_report(plan)
    assert report["passed"] is False, report
    assert any("execute command missing fragment: -InputExe" in failure for failure in report["failures"])
    assert any("execute command missing fragment: -WorkDir" in failure for failure in report["failures"])
    assert any("execute command missing fragment: -Stage" in failure for failure in report["failures"])
    assert any("execute command missing fragment: -OutputRoot" in failure for failure in report["failures"])


def test_rejects_repo_candidate_path() -> None:
    plan = valid_plan()
    plan["candidate_dir"] = str(ROOT / "captures" / "hd-soak")
    plan["candidate_path"] = str(ROOT / "captures" / "hd-soak" / "candidate.exe")
    report = build_fixture_report(plan)
    assert report["passed"] is False, report
    assert any("candidate_dir is not the isolated" in failure for failure in report["failures"])
    assert any("candidate_path is inside the repository" in failure for failure in report["failures"])


def test_rejects_missing_or_unverified_base_input() -> None:
    plan = valid_plan()
    plan["input_exists"] = False
    plan["base_sha_status"] = "missing"
    report = build_fixture_report(plan)
    assert report["passed"] is False, report
    assert any("input_exe does not exist" in failure for failure in report["failures"])
    assert any("base_sha_status" in failure for failure in report["failures"])


def test_cli_writes_outputs() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        fixture = Path(temporary)
        status_path = write_json(fixture / "step-status.json", step_status())
        plan_path = write_json(fixture / "plan.json", valid_plan())
        out_json = fixture / "out.json"
        out_md = fixture / "out.md"
        result = run_script(
            "--step-status-json",
            str(status_path),
            "--read-plan-json",
            str(plan_path),
            "--write-json",
            str(out_json),
            "--write-markdown",
            str(out_md),
            "--require-pass",
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(out_json.read_text(encoding="ascii"))["passed"] is True
        markdown = out_md.read_text(encoding="ascii")
        assert "HD Soak Dry-Run Plan" in markdown
        assert "Approval TTL" in markdown


def test_hidden_plan_uses_real_schema_and_preserves_no_input_boundary() -> None:
    report = build_fixture_report(valid_hidden_plan(), hidden_step_status())
    assert report["passed"], report["failures"]
    assert report["status"] == "ready_for_hidden_runtime"
    assert report["input_responsiveness"] == "not_applicable_hidden"
    assert report["evidence_class"] == "approved_hidden_cdb_host_soak"
    assert report["approval_gated_execute_command"] is None
    assert report["runner_source"]["protected_stage"] == dry_run_plan.PROTECTED_STABLE_STAGE
    assert len(report["runner_source"]["sha256"]) == 64
    assert report["recommended_runtime_command"] == valid_hidden_plan()["hidden_runtime_command"]


def test_hidden_plan_rejects_provenance_and_command_drift() -> None:
    for field, value in (("executed", True), ("preflight_passed", False), ("environment", "host_visible"),
                         ("duration_sec", 120), ("input_sha256", "0" * 64),
                         ("candidate_run_directory", str(ROOT / "candidate")),
                         ("output_directory", dry_run_plan.HIDDEN_OUTPUT_ROOT + r"\..\escape")):
        plan = valid_hidden_plan()
        plan[field] = value
        assert not build_fixture_report(plan, hidden_step_status())["passed"], field
    for before, after in (("-RequirePass", ""), ("-Json", ""), ("run_hidden_soak.ps1", "other.ps1"),
                          ("-MaxArtifactMB '250'", "-MaxArtifactMB '999'"),
                          ("short10-map-idle-current.json", "wrong.json"),
                          ("-FrameIntervalSec '15'", "-FrameIntervalSec '1'"),
                          ("-Execute", "-Execute -AllowVisibleRuntime")):
        plan = valid_hidden_plan()
        plan["hidden_runtime_command"] = plan["hidden_runtime_command"].replace(before, after)
        assert not build_fixture_report(plan, hidden_step_status())["passed"], before


def test_hidden_default_invokes_only_hidden_dry_run() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        args = args_for(Path(temporary), valid_hidden_plan(), hidden_step_status())
        args.read_plan_json = None
        with patch.object(dry_run_plan, "run_harness_plan", return_value=(valid_hidden_plan(), {"exit_code": 0})) as run:
            report = dry_run_plan.build_report(args)
        assert report["passed"], report["failures"]
        assert run.call_args.args[0] == dry_run_plan.HIDDEN_SCRIPT
        command = dry_run_plan.dry_run_command(*run.call_args.args)
        assert "-Execute" not in command and "-AllowVisibleRuntime" not in command
        assert "-Json" in command and "-GuardJson" in command
        assert "-Tier" not in command


def test_unknown_environment_never_invokes_a_harness() -> None:
    for environment in (None, "unknown", ["hidden_cdb_host"]):
        with tempfile.TemporaryDirectory() as temporary:
            status = hidden_step_status()
            status["steps"][0]["preferred_environment"] = environment
            args = args_for(Path(temporary), valid_hidden_plan(), status)
            args.read_plan_json = None
            with patch.object(dry_run_plan, "run_harness_plan") as run:
                report = dry_run_plan.build_report(args)
            run.assert_not_called()
        assert not report["passed"], report
        assert any("unsupported" in failure for failure in report["failures"])


def test_hidden_plan_rejects_an_arbitrary_existing_interpreter() -> None:
    plan = valid_hidden_plan()
    plan["hidden_runtime_command"] = plan["hidden_runtime_command"].replace(sys.executable, str(Path(__file__).resolve()))
    report = build_fixture_report(plan, hidden_step_status())
    assert not report["passed"], report
    assert any("verified guard interpreter" in failure for failure in report["failures"])


def test_completed_ladder_never_invokes_a_harness_or_reads_a_plan() -> None:
    for fixture_plan in (False, True):
        with tempfile.TemporaryDirectory() as temporary:
            tmp = Path(temporary)
            args = args_for(tmp, {}, intro_fixtures.completed_ladder_status(tmp))
            if fixture_plan:
                args.read_plan_json.write_text("not JSON", encoding="utf-8")
            else:
                args.read_plan_json = None
            with patch.object(dry_run_plan, "run_harness_plan", side_effect=AssertionError("terminal state must not invoke a harness")) as run:
                report = dry_run_plan.build_report(args)
            run.assert_not_called()
        assert report["passed"], report["failures"]
        assert report["status"] == "not_applicable_short_ladder_complete"
        intro_fixtures.assert_terminal_no_authorization(report)
        assert "authorizes no runtime" in dry_run_plan.to_markdown(report)


def test_invalid_completion_never_falls_back_to_runtime_planning() -> None:
    for mutation in intro_fixtures.COMPLETION_MUTATIONS:
        with tempfile.TemporaryDirectory() as temporary:
            tmp = Path(temporary)
            status = intro_fixtures.completed_ladder_status(tmp)
            intro_fixtures.mutate_completed_ladder(status, mutation)
            args = args_for(tmp, {}, status)
            args.read_plan_json = None
            with patch.object(dry_run_plan, "run_harness_plan", side_effect=AssertionError("invalid completion must fail closed")) as run:
                report = dry_run_plan.build_report(args)
            run.assert_not_called()
        assert not report["passed"], (mutation, report)
        assert report["status"] == "invalid_short_ladder_completion"
        intro_fixtures.assert_terminal_no_authorization(report)


def test_completed_ladder_cli_writes_only_terminal_packet() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        tmp = Path(temporary)
        status_path = write_json(tmp / "status.json", intro_fixtures.completed_ladder_status(tmp))
        output_json, output_md = tmp / "terminal.json", tmp / "terminal.md"
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--step-status-json", str(status_path),
                                 "--write-json", str(output_json), "--write-markdown", str(output_md), "--require-pass"],
                                capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(output_json.read_text(encoding="utf-8"))
        intro_fixtures.assert_terminal_no_authorization(report)
        assert report["status"] == "not_applicable_short_ladder_complete"
        assert "Approval-Gated Execute Command" not in output_md.read_text(encoding="utf-8")


def test_missing_harness_runner_fails_closed_without_a_plan() -> None:
    for environment in (dry_run_plan.HOST_ENVIRONMENT, dry_run_plan.HIDDEN_ENVIRONMENT):
        step = {"tier": TIER, "route": ROUTE, "duration_sec": DURATION,
                "preferred_environment": environment}
        with patch.object(dry_run_plan.subprocess, "run", side_effect=FileNotFoundError("missing PowerShell")) as run:
            plan, invocation = dry_run_plan.run_harness_plan(Path("fixture.ps1"), step)
        assert plan is None
        assert invocation["exit_code"] is None
        assert "runner unavailable" in invocation["stderr"]
        assert "missing PowerShell" in invocation["stderr"]
        assert "-Execute" not in run.call_args.args[0]
        run.assert_called_once()


def run_tests() -> None:
    test_missing_harness_runner_fails_closed_without_a_plan()
    test_completed_ladder_never_invokes_a_harness_or_reads_a_plan()
    test_invalid_completion_never_falls_back_to_runtime_planning()
    test_completed_ladder_cli_writes_only_terminal_packet()
    test_unknown_environment_never_invokes_a_harness()
    test_hidden_plan_rejects_an_arbitrary_existing_interpreter()
    test_hidden_plan_uses_real_schema_and_preserves_no_input_boundary()
    test_hidden_plan_rejects_provenance_and_command_drift()
    test_hidden_default_invokes_only_hidden_dry_run()
    test_valid_plan_passes()
    test_rejects_executed_plan()
    test_rejects_stage_drift()
    test_rejects_execute_command_without_require_pass_or_json()
    test_rejects_missing_visible_runtime_token()
    test_rejects_missing_visible_runtime_expiry()
    test_rejects_nearly_expired_visible_runtime_approval()
    test_rejects_missing_intro_skip_plan_fields()
    test_rejects_execute_command_without_explicit_stage_or_io_roots()
    test_rejects_repo_candidate_path()
    test_rejects_missing_or_unverified_base_input()
    test_cli_writes_outputs()


def main() -> int:
    run_tests()
    print("hd_soak_dry_run_plan tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
