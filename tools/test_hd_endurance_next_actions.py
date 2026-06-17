#!/usr/bin/env python3
"""Fixture tests for hd_endurance_next_actions.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import hd_endurance_next_actions as next_actions

APPROVAL_TOKEN = "1234567890abcdef"
APPROVAL_EXPIRES_UTC = "2999-01-01T00:00:00.0000000+00:00"


def write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="ascii")
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


def step_command(tier: str, route: str, paths: dict[str, str], *, execute: bool) -> str:
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
        "-IntroSkipClickMode",
        next_actions.INTRO_SKIP_CLICK_MODE,
        "-IntroSkipClicks",
        str(next_actions.INTRO_SKIP_CLICKS),
        "-SkipPulses",
        str(next_actions.SKIP_PULSES),
        "-SampleIntervalSec",
        str(next_actions.SAMPLE_INTERVAL_SEC),
        "-MaxInputDriftPx",
        str(next_actions.MAX_INPUT_DRIFT_PX),
        "-MinNonblackPercent",
        next_actions.MIN_NONBLACK_PERCENT_TEXT,
        "-MinUniqueSampleColors",
        str(next_actions.MIN_UNIQUE_SAMPLE_COLORS),
        "-MaxArtifactMB",
        str(next_actions.MAX_ARTIFACT_MB),
        "-MaxWorkingSetGrowthMB",
        str(next_actions.MAX_WORKING_SET_GROWTH_MB),
        "-MaxPrivateMemoryGrowthMB",
        str(next_actions.MAX_PRIVATE_MEMORY_GROWTH_MB),
        "-MaxHandleGrowth",
        str(next_actions.MAX_HANDLE_GROWTH),
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
        "safe_dry_run_command": step_command(tier, route, paths, execute=False),
        "approval_gated_runtime_command": step_command(tier, route, paths, execute=True),
        "writes_outside_repo": [r"C:\ClashTests\hd-soak", r"C:\ClashCaptures\hd-soak"],
        "must_not_modify": [r"C:\Clash\clash95.exe"],
    }


def dry_run_plan_for_step(step: dict[str, Any], *, current_step_id: str | None = None, passed: bool = True) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "status": "ready_for_explicit_approval" if passed else "dry_run_plan_invalid",
        "current_step": {
            "id": current_step_id or step["id"],
            "status": step["status"],
            "tier": step["tier"],
            "route": step["route"],
            "duration_sec": step.get("duration_sec", 120),
            "paths": step["paths"],
        },
        "plan": {
            "dry_run": True,
            "stage": "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch",
            "protected_stable_stage": "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch",
            "stable_stage_should_change": False,
            "right_bottom_promotion_blocked": True,
            "tier": step["tier"],
            "route": step["route"],
            "sample_interval_sec": next_actions.SAMPLE_INTERVAL_SEC,
            "candidate_dir": r"C:\ClashTests\hd-soak",
            "candidate_path": r"C:\ClashTests\hd-soak\clash95_hd_soak_fixture.exe",
            "output_root": r"C:\ClashCaptures\hd-soak",
            "report_json": str(Path(step["paths"]["report_json"]).resolve()),
            "report_markdown": str(Path(step["paths"]["report_markdown"]).resolve()),
            "input_exists": True,
            "input_sha256": "5" * 64,
            "base_sha_status": "ok",
            "growth_limits": {
                "max_working_set_growth_mb": next_actions.MAX_WORKING_SET_GROWTH_MB,
                "max_private_memory_growth_mb": next_actions.MAX_PRIVATE_MEMORY_GROWTH_MB,
                "max_handle_growth": next_actions.MAX_HANDLE_GROWTH,
                "max_artifact_mb": next_actions.MAX_ARTIFACT_MB,
            },
            "frame_limits": {
                "min_nonblack_percent": next_actions.MIN_NONBLACK_PERCENT,
                "min_unique_sample_colors": next_actions.MIN_UNIQUE_SAMPLE_COLORS,
            },
            "intro_skip": {
                "click_mode": next_actions.INTRO_SKIP_CLICK_MODE,
                "click_repeat": next_actions.INTRO_SKIP_CLICKS,
                "space_pulses": next_actions.SKIP_PULSES,
                "proof_class": "intro_skip_harness_prep_not_manual_directinput_release_proof",
            },
            "visible_runtime_approval": {
                "token": APPROVAL_TOKEN,
                "token_kind": "sha256-16",
                "expires_utc": APPROVAL_EXPIRES_UTC,
                "max_age_hours": 12,
                "min_ttl_minutes": next_actions.MIN_APPROVAL_TTL_MINUTES,
                "token_fields": ["fixture", APPROVAL_EXPIRES_UTC],
                "purpose": "copy-exact dry-run approval packet; edited, stale, or hand-typed visible runtime commands fail closed",
            },
            "commands": {
                "execute": (
                    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
                    r"'.\scripts\smoke\run_hd_soak.ps1' "
                    f"-Tier '{step['tier']}' -Route '{step['route']}' "
                    r"-CandidateDir 'C:\ClashTests\hd-soak' "
                    "-CandidateName 'clash95_hd_soak_fixture.exe' "
                    f"-ReportJson '{Path(step['paths']['report_json']).resolve()}' "
                    f"-ReportMarkdown '{Path(step['paths']['report_markdown']).resolve()}' "
                    "-IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' "
                    "-SampleIntervalSec '15' -MaxInputDriftPx '1' "
                    "-MinNonblackPercent '10' -MinUniqueSampleColors '8' "
                    "-MaxArtifactMB '250' -MaxWorkingSetGrowthMB '64' "
                    "-MaxPrivateMemoryGrowthMB '64' -MaxHandleGrowth '128' "
                    f"-VisibleRuntimeApprovalExpiresUtc '{APPROVAL_EXPIRES_UTC}' "
                    f"-VisibleRuntimeApprovalToken '{APPROVAL_TOKEN}' "
                    "-Execute -AllowVisibleRuntime -RequirePass -Json"
                )
            },
        },
        "approval_gated_execute_command": (
            "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
            r"'.\scripts\smoke\run_hd_soak.ps1' "
            f"-Tier '{step['tier']}' -Route '{step['route']}' "
            r"-CandidateDir 'C:\ClashTests\hd-soak' "
            "-CandidateName 'clash95_hd_soak_fixture.exe' "
            f"-ReportJson '{Path(step['paths']['report_json']).resolve()}' "
            f"-ReportMarkdown '{Path(step['paths']['report_markdown']).resolve()}' "
            "-IntroSkipClickMode 'postmessage' -IntroSkipClicks '8' -SkipPulses '4' "
            "-SampleIntervalSec '15' -MaxInputDriftPx '1' "
            "-MinNonblackPercent '10' -MinUniqueSampleColors '8' "
            "-MaxArtifactMB '250' -MaxWorkingSetGrowthMB '64' "
            "-MaxPrivateMemoryGrowthMB '64' -MaxHandleGrowth '128' "
            f"-VisibleRuntimeApprovalExpiresUtc '{APPROVAL_EXPIRES_UTC}' "
            f"-VisibleRuntimeApprovalToken '{APPROVAL_TOKEN}' "
            "-Execute -AllowVisibleRuntime -RequirePass -Json"
        ),
    }


def checklist_fixture(*, complete: bool = False) -> dict[str, Any]:
    if complete:
        return {
            "full_game_complete": True,
            "counts": {"total": 15, "passed": 15, "blocked": 0, "missing": 0},
            "next_milestone": None,
            "requirements": [],
        }
    return {
        "full_game_complete": False,
        "counts": {"total": 15, "passed": 4, "blocked": 7, "missing": 4},
        "next_milestone": {
            "id": "short2_menu_idle_soak",
            "title": "First short2 menu-idle soak passes",
            "next_probe": "run the approval-gated short2 menu-idle soak on the protected stage",
        },
        "requirements": [
            {
                "id": "short2_menu_idle_soak",
                "passed": False,
                "status": "blocked",
                "category": "endurance",
                "summary": "short2 visible-runtime soak has not produced passing frame/process evidence",
                "next_probe": "run the approval-gated short2 menu-idle soak on the protected stage",
            },
            {
                "id": "first_mission_visual_clean",
                "passed": False,
                "status": "blocked",
                "category": "render baseline",
                "summary": "first-mission visual audit is not clean; black patches remain",
                "next_probe": "fix right/bottom/minimap black patches before release",
            },
            {
                "id": "stable_menu_real_input",
                "passed": False,
                "status": "blocked",
                "category": "manual input",
                "summary": "menu-load proof remains pending manual DirectInput validation",
                "next_probe": "collect approved manual menu-load proof or keep promotion blocked",
            },
        ],
    }


def intro_skip_readiness_for_step(step: dict[str, Any], *, passed: bool = True) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "runtime_policy": (
            "repo-only intro-skip rerun readiness gate; does not launch Clash95, CDB, "
            "wrappers, PowerShell harnesses, or visible windows"
        ),
        "status": "ready_for_explicit_visible_rerun_approval" if passed else "not_ready",
        "current_step": {
            "id": step["id"],
            "status": step["status"],
        },
        "triage": {
            "classification": "intro_skip_input_drift_exit",
            "final_route_marker": "intro-skip",
            "candidate_sha256": "a" * 64,
            "next_probe": "rerun only after explicit visible-window approval",
        },
        "dry_run_plan": {
            "approval_gated_execute_command": dry_run_plan_for_step(step)["approval_gated_execute_command"],
        },
        "approval_boundary": (
            "The next runtime run will open a visible Clash95 game window and still "
            "requires explicit user approval."
        ),
        "failures": [] if passed else ["fixture failure"],
    }


def args_for(
    path: Path,
    step_status_path: Path | None = None,
    dry_run_plan_path: Path | None = None,
    intro_skip_readiness_path: Path | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        checklist_json=path,
        short_step_status_json=step_status_path or path.parent / "missing-step-status.json",
        dry_run_plan_json=dry_run_plan_path,
        intro_skip_readiness_json=intro_skip_readiness_path,
    )


def test_short2_next_action_is_visible_approval_gated() -> None:
    with tempfile.TemporaryDirectory() as directory:
        checklist_path = write_json(Path(directory) / "checklist.json", checklist_fixture())
        report = next_actions.build_report(args_for(checklist_path))
        action = report["next_action"]
        assert report["passed"] is True
        assert report["status"] == "repo_only_followup_available"
        assert action["id"] == "refresh_short2_menu_idle_dry_run_plan"
        assert action["status"] == "dry_run_plan_required"
        assert action["requires_visible_runtime"] is False
        assert action["requires_explicit_user_approval"] is False
        assert action["exact_runtime_command"] is None
        assert action["plan_verified_execute_command"] is None
        assert action["rejected_legacy_runtime_command"]["safe_to_run"] is False
        assert "-Execute -AllowVisibleRuntime" in action["rejected_legacy_runtime_command"]["command"]
        assert "-Execute" not in action["safe_dry_run_command"]
        assert "hd-soak-short2-menu-idle-current.json" in action["safe_dry_run_command"]
        assert "-MaxInputDriftPx 1" in action["safe_dry_run_command"]
        assert "-IntroSkipClickMode postmessage" in action["safe_dry_run_command"]
        artifacts = action["current_step_artifacts"]
        assert artifacts["guard_json"] == r"captures\current\hd-soak-short2-menu-idle-guard-current.json"
        assert artifacts["triage_json"] == r"captures\current\hd-soak-short2-menu-idle-triage-current.json"
        assert action["post_run_validation"] == []
        assert "hd_soak_dry_run_plan.py" in " ".join(action["post_run_handoff_refresh"])
        assert "hd_soak_approval_preflight.py" in " ".join(action["post_run_handoff_refresh"])
        assert action["post_run_evidence_refresh"] == []
        assert r"C:\Clash\clash95.exe" in action["must_not_modify"]
        markdown = next_actions.to_markdown(report)
        assert "## Open Requirement Details" in markdown
        assert "`first_mission_visual_clean` (`render baseline`, `blocked`)" in markdown
        assert "fix right/bottom/minimap black patches before release" in markdown


def test_missing_checklist_fails_closed() -> None:
    report = next_actions.build_report(args_for(Path("does-not-exist.json")))
    assert report["passed"] is False
    assert report["next_action"] is None
    assert report["failures"]


def test_complete_checklist_switches_to_release_audit() -> None:
    with tempfile.TemporaryDirectory() as directory:
        checklist_path = write_json(Path(directory) / "checklist.json", checklist_fixture(complete=True))
        report = next_actions.build_report(args_for(checklist_path))
        assert report["passed"] is True
        assert report["status"] == "release_complete_pending_audit"
        assert report["next_action"]["id"] == "release_audit"
        assert report["next_action"]["requires_visible_runtime"] is False


def test_pending_later_short_step_takes_precedence_over_manual_milestone() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        checklist = checklist_fixture()
        checklist["next_milestone"] = {
            "id": "stable_menu_real_input",
            "title": "Stable menu load has real input proof",
            "next_probe": "collect approved manual menu-load proof or keep promotion blocked",
        }
        checklist["requirements"][0]["passed"] = True
        checklist["requirements"][0]["status"] = "pass"
        checklist_path = write_json(tmp / "checklist.json", checklist)
        first = step_record("short2_menu_idle", "short2", "menu-idle", status="pass", passed=True)
        second = step_record("short2_map_idle", "short2", "map-idle", status="missing_pending_approval")
        step_status_path = write_json(
            tmp / "step-status.json",
            {
                "passed": True,
                "ladder_complete": False,
                "current_step": {
                    "id": "short2_map_idle",
                    "status": "missing_pending_approval",
                    "next_command": second["approval_gated_runtime_command"],
                },
                "steps": [first, second],
            },
        )
        report = next_actions.build_report(args_for(checklist_path, step_status_path))

    action = report["next_action"]
    assert report["passed"] is True
    assert report["status"] == "repo_only_followup_available"
    assert action["id"] == "refresh_short2_map_idle_dry_run_plan"
    assert action["source"] == "short_soak_step_status"
    assert action["requires_visible_runtime"] is False
    assert action["exact_runtime_command"] is None
    assert "-Route map-idle" in action["safe_dry_run_command"]
    assert action["rejected_legacy_runtime_command"]["safe_to_run"] is False
    assert action["current_step_artifacts"]["guard_json"] == r"captures\current\hd-soak-short2-map-idle-guard-current.json"
    assert "hd_soak_dry_run_plan.py" in " ".join(action["post_run_handoff_refresh"])
    assert action["post_run_evidence_refresh"] == []


def test_pending_short_step_includes_plan_verified_execute_command() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        checklist_path = write_json(tmp / "checklist.json", checklist_fixture())
        first = step_record("short2_menu_idle", "short2", "menu-idle", status="pending_approval_legacy_compat")
        step_status_path = write_json(
            tmp / "step-status.json",
            {
                "passed": True,
                "ladder_complete": False,
                "current_step": {
                    "id": "short2_menu_idle",
                    "status": "pending_approval_legacy_compat",
                    "next_command": first["approval_gated_runtime_command"],
                },
                "steps": [first],
            },
        )
        dry_run_plan_path = write_json(tmp / "dry-run-plan.json", dry_run_plan_for_step(first))
        report = next_actions.build_report(args_for(checklist_path, step_status_path, dry_run_plan_path))

    action = report["next_action"]
    assert report["passed"] is True, report
    assert action["exact_runtime_command"] == action["plan_verified_execute_command"]
    assert action["exact_runtime_command_source"] == "dry_run_plan"
    assert action["legacy_step_runtime_command"] is None
    assert action["rejected_legacy_runtime_command"]["command"] == first["approval_gated_runtime_command"]
    assert action["rejected_legacy_runtime_command"]["safe_to_run"] is False
    assert r"-CandidateDir 'C:\ClashTests\hd-soak'" in action["plan_verified_execute_command"]
    assert "-IntroSkipClickMode 'postmessage'" in action["plan_verified_execute_command"]
    assert f"-VisibleRuntimeApprovalExpiresUtc '{APPROVAL_EXPIRES_UTC}'" in action["plan_verified_execute_command"]
    assert "-VisibleRuntimeApprovalToken '1234567890abcdef'" in action["plan_verified_execute_command"]
    assert "-RequirePass -Json" in action["plan_verified_execute_command"]
    assert action["dry_run_plan"]["candidate_path"].endswith("clash95_hd_soak_fixture.exe")
    assert action["dry_run_plan"]["output_root"] == r"C:\ClashCaptures\hd-soak"
    assert action["dry_run_plan"]["approval_expires_utc"] == APPROVAL_EXPIRES_UTC


def test_pending_short_step_records_current_artifact_inventory() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        checklist_path = write_json(tmp / "checklist.json", checklist_fixture())
        first = step_record("short2_menu_idle", "short2", "menu-idle", status="pending_approval_legacy_compat")
        first["paths"] = {
            "report_json": str(tmp / "hd-soak-short2-menu-idle-current.json"),
            "report_markdown": str(tmp / "hd-soak-short2-menu-idle-current.md"),
            "guard_json": str(tmp / "hd-soak-short2-menu-idle-guard-current.json"),
            "guard_markdown": str(tmp / "hd-soak-short2-menu-idle-guard-current.md"),
            "triage_json": str(tmp / "hd-soak-short2-menu-idle-triage-current.json"),
            "triage_markdown": str(tmp / "hd-soak-short2-menu-idle-triage-current.md"),
        }
        Path(first["paths"]["guard_json"]).write_text("{}", encoding="ascii")
        step_status_path = write_json(
            tmp / "step-status.json",
            {
                "passed": True,
                "ladder_complete": False,
                "current_step": {
                    "id": "short2_menu_idle",
                    "status": "pending_approval_legacy_compat",
                    "next_command": first["approval_gated_runtime_command"],
                },
                "steps": [first],
            },
        )
        report = next_actions.build_report(args_for(checklist_path, step_status_path))

    artifacts = report["next_action"]["current_step_artifacts"]
    assert artifacts["report_json"] == first["paths"]["report_json"]
    assert artifacts["report_json_exists"] is False
    assert artifacts["guard_json_exists"] is True
    assert artifacts["triage_json_exists"] is False
    assert artifacts["canonical_runtime_report_missing"] is True
    assert artifacts["post_run_guard_missing"] is False
    assert artifacts["post_run_triage_missing"] is True


def test_mismatched_dry_run_plan_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        checklist_path = write_json(tmp / "checklist.json", checklist_fixture())
        first = step_record("short2_menu_idle", "short2", "menu-idle", status="pending_approval_legacy_compat")
        step_status_path = write_json(
            tmp / "step-status.json",
            {
                "passed": True,
                "ladder_complete": False,
                "current_step": {
                    "id": "short2_menu_idle",
                    "status": "pending_approval_legacy_compat",
                    "next_command": first["approval_gated_runtime_command"],
                },
                "steps": [first],
            },
        )
        dry_run_plan_path = write_json(
            tmp / "dry-run-plan.json",
            dry_run_plan_for_step(first, current_step_id="short2_map_idle"),
        )
        report = next_actions.build_report(args_for(checklist_path, step_status_path, dry_run_plan_path))

    assert report["passed"] is False, report
    assert any("dry-run plan current step" in failure for failure in report["failures"]), report


def test_stale_dry_run_plan_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        checklist_path = write_json(tmp / "checklist.json", checklist_fixture())
        first = step_record("short2_menu_idle", "short2", "menu-idle", status="pending_approval_legacy_compat")
        step_status_path = write_json(
            tmp / "step-status.json",
            {
                "passed": True,
                "ladder_complete": False,
                "current_step": {
                    "id": "short2_menu_idle",
                    "status": "pending_approval_legacy_compat",
                    "next_command": first["approval_gated_runtime_command"],
                },
                "steps": [first],
            },
        )
        plan = dry_run_plan_for_step(first)
        plan["generated_at"] = (
            datetime.now(timezone.utc) - timedelta(hours=next_actions.MAX_DRY_RUN_PLAN_AGE_HOURS + 1)
        ).isoformat()
        dry_run_plan_path = write_json(tmp / "dry-run-plan.json", plan)
        report = next_actions.build_report(args_for(checklist_path, step_status_path, dry_run_plan_path))

    assert report["passed"] is False, report
    assert any("dry-run plan is older" in failure for failure in report["failures"]), report


def test_nearly_expired_approval_token_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        checklist_path = write_json(tmp / "checklist.json", checklist_fixture())
        first = step_record("short2_menu_idle", "short2", "menu-idle", status="pending_approval_legacy_compat")
        step_status_path = write_json(
            tmp / "step-status.json",
            {
                "passed": True,
                "ladder_complete": False,
                "current_step": {
                    "id": "short2_menu_idle",
                    "status": "pending_approval_legacy_compat",
                    "next_command": first["approval_gated_runtime_command"],
                },
                "steps": [first],
            },
        )
        plan = dry_run_plan_for_step(first)
        old_expiry = APPROVAL_EXPIRES_UTC
        new_expiry = (
            datetime.now(timezone.utc) + timedelta(minutes=next_actions.MIN_APPROVAL_TTL_MINUTES - 1)
        ).isoformat()
        approval = plan["plan"]["visible_runtime_approval"]
        approval["expires_utc"] = new_expiry
        approval["token_fields"] = ["fixture", new_expiry]
        plan["plan"]["commands"]["execute"] = plan["plan"]["commands"]["execute"].replace(old_expiry, new_expiry)
        plan["approval_gated_execute_command"] = plan["approval_gated_execute_command"].replace(old_expiry, new_expiry)
        dry_run_plan_path = write_json(tmp / "dry-run-plan.json", plan)
        report = next_actions.build_report(args_for(checklist_path, step_status_path, dry_run_plan_path))

    assert report["passed"] is False, report
    assert any("approval expires too soon" in failure for failure in report["failures"]), report


def test_unverified_dry_run_base_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        checklist_path = write_json(tmp / "checklist.json", checklist_fixture())
        first = step_record("short2_menu_idle", "short2", "menu-idle", status="pending_approval_legacy_compat")
        step_status_path = write_json(
            tmp / "step-status.json",
            {
                "passed": True,
                "current_step": {
                    "id": first["id"],
                    "status": first["status"],
                    "next_command": first["approval_gated_runtime_command"],
                },
                "steps": [first],
            },
        )
        plan = dry_run_plan_for_step(first)
        plan["plan"]["input_exists"] = False
        plan["plan"]["base_sha_status"] = "missing"
        dry_run_plan_path = write_json(tmp / "dry-run-plan.json", plan)
        report = next_actions.build_report(args_for(checklist_path, step_status_path, dry_run_plan_path))

    assert report["passed"] is False, report
    assert any("input_exe does not exist" in failure for failure in report["failures"]), report
    assert any("base_sha_status" in failure for failure in report["failures"]), report


def test_failed_short_step_without_triage_requests_repo_triage_command() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        checklist_path = write_json(tmp / "checklist.json", checklist_fixture())
        first = step_record("short2_menu_idle", "short2", "menu-idle", status="failed_needs_triage")
        first["summary"] = {
            "next_command": r"python tools\hd_soak_failure_triage.py captures\current\hd-soak-short2-menu-idle-current.json",
        }
        step_status_path = write_json(
            tmp / "step-status.json",
            {
                "passed": True,
                "ladder_complete": False,
                "current_step": {
                    "id": "short2_menu_idle",
                    "status": "failed_needs_triage",
                    "next_command": first["summary"]["next_command"],
                },
                "steps": [first],
            },
        )
        report = next_actions.build_report(args_for(checklist_path, step_status_path))

    action = report["next_action"]
    assert report["passed"] is True
    assert report["status"] == "repo_only_followup_available"
    assert action["id"] == "run_short2_menu_idle_triage"
    assert action["requires_visible_runtime"] is False
    assert action["repo_command"].startswith("python tools\\hd_soak_failure_triage.py")
    assert "hd_soak_short_step_status.py" in " ".join(action["post_run_validation"])
    assert "current_evidence_refresh.py" not in " ".join(action["post_run_validation"])


def test_classified_failed_short_step_points_to_next_probe() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        checklist_path = write_json(tmp / "checklist.json", checklist_fixture())
        first = step_record("short2_menu_idle", "short2", "menu-idle", status="failed_classified_input_route_failure")
        first["summary"] = {
            "classification": "input_route_failure",
            "next_probe": "inspect route_results and rerun the same route with mouse_path_probe logging before changing patches",
            "frame_sample_count": 3,
            "final_route_marker": "route-input-failed",
            "candidate_sha256": "a" * 64,
            "visual_anomaly_passed": True,
            "black_patch_risk_count": 0,
            "palette_or_stripe_risk_count": 0,
            "missing_nonblack_bounds_count": 0,
        }
        step_status_path = write_json(
            tmp / "step-status.json",
            {
                "passed": True,
                "ladder_complete": False,
                "current_step": {
                    "id": "short2_menu_idle",
                    "status": "failed_classified_input_route_failure",
                    "next_command": None,
                },
                "steps": [first],
            },
        )
        report = next_actions.build_report(args_for(checklist_path, step_status_path))

    action = report["next_action"]
    assert report["passed"] is True
    assert report["status"] == "repo_only_followup_available"
    assert action["id"] == "inspect_short2_menu_idle_triage"
    assert action["requires_visible_runtime"] is False
    assert action["triage"]["classification"] == "input_route_failure"
    assert action["current_failure"]["classification"] == "input_route_failure"
    assert action["current_failure"]["black_patch_risk_count"] == 0
    assert action["current_failure"]["palette_or_stripe_risk_count"] == 0
    assert "mouse_path_probe" in action["why"]


def test_intro_skip_readiness_turns_classified_failure_into_rerun_approval() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        checklist_path = write_json(tmp / "checklist.json", checklist_fixture())
        first = step_record(
            "short2_menu_idle",
            "short2",
            "menu-idle",
            status="failed_classified_intro_skip_input_drift_exit",
        )
        first["summary"] = {
            "classification": "intro_skip_input_drift_exit",
            "next_probe": "rerun after repo-only intro-skip readiness passes and explicit visible-window approval",
            "frame_sample_count": 4,
            "final_route_marker": "intro-skip",
            "candidate_sha256": "a" * 64,
            "visual_anomaly_passed": False,
            "black_patch_risk_count": 1,
            "palette_or_stripe_risk_count": 0,
            "missing_nonblack_bounds_count": 0,
        }
        step_status_path = write_json(
            tmp / "step-status.json",
            {
                "passed": True,
                "ladder_complete": False,
                "current_step": {
                    "id": "short2_menu_idle",
                    "status": "failed_classified_intro_skip_input_drift_exit",
                    "next_command": first["approval_gated_runtime_command"],
                },
                "steps": [first],
            },
        )
        dry_run_plan_path = write_json(tmp / "dry-run-plan.json", dry_run_plan_for_step(first))
        readiness_path = write_json(tmp / "intro-skip-readiness.json", intro_skip_readiness_for_step(first))
        report = next_actions.build_report(
            args_for(checklist_path, step_status_path, dry_run_plan_path, readiness_path)
        )

    action = report["next_action"]
    assert report["passed"] is True, report
    assert report["status"] == "waiting_for_explicit_visible_runtime_approval"
    assert action["id"] == "rerun_short2_menu_idle_soak"
    assert action["requires_visible_runtime"] is True
    assert action["requires_explicit_user_approval"] is True
    assert action["exact_runtime_command"] == action["plan_verified_execute_command"]
    assert action["exact_runtime_command_source"] == "dry_run_plan"
    assert action["legacy_step_runtime_command"] is None
    assert action["rejected_legacy_runtime_command"]["safe_to_run"] is False
    assert action["current_failure"]["classification"] == "intro_skip_input_drift_exit"
    assert action["current_failure"]["visual_anomaly_passed"] is False
    assert action["current_failure"]["black_patch_risk_count"] == 1
    assert action["intro_skip_rerun_readiness"]["status"] == "ready_for_explicit_visible_rerun_approval"
    assert action["intro_skip_rerun_readiness"]["classification"] == "intro_skip_input_drift_exit"
    assert "visible Clash95 game window" in action["intro_skip_rerun_readiness"]["approval_boundary"]
    assert "hd_soak_intro_skip_rerun_readiness.py" in " ".join(action["post_run_handoff_refresh"])
    assert "postmessage intro-skip prep" in action["why"]


def test_cli_writes_outputs() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        checklist_path = write_json(tmp / "checklist.json", checklist_fixture())
        step_status_path = tmp / "missing-step-status.json"
        json_out = tmp / "next.json"
        md_out = tmp / "next.md"
        script = Path(__file__).resolve().parent / "hd_endurance_next_actions.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--checklist-json",
                str(checklist_path),
                "--short-step-status-json",
                str(step_status_path),
                "--dry-run-plan-json",
                str(tmp / "missing-dry-run-plan.json"),
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
        report = json.loads(json_out.read_text(encoding="ascii"))
        assert report["next_action"]["id"] == "refresh_short2_menu_idle_dry_run_plan"
        assert report["next_action"]["exact_runtime_command"] is None


def run_tests() -> None:
    test_short2_next_action_is_visible_approval_gated()
    test_missing_checklist_fails_closed()
    test_complete_checklist_switches_to_release_audit()
    test_pending_later_short_step_takes_precedence_over_manual_milestone()
    test_pending_short_step_includes_plan_verified_execute_command()
    test_pending_short_step_records_current_artifact_inventory()
    test_mismatched_dry_run_plan_fails_closed()
    test_stale_dry_run_plan_fails_closed()
    test_nearly_expired_approval_token_fails_closed()
    test_unverified_dry_run_base_fails_closed()
    test_failed_short_step_without_triage_requests_repo_triage_command()
    test_classified_failed_short_step_points_to_next_probe()
    test_intro_skip_readiness_turns_classified_failure_into_rerun_approval()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_endurance_next_actions tests passed")
