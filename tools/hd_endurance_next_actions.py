#!/usr/bin/env python3
"""Build the next-action handoff for the HD endurance road.

This is repo-only triage. It reads the release checklist plus the short soak
step status and emits exact safe commands plus the approval-gated runtime
command that would prove the next milestone. It does not launch Clash95, CDB,
wrappers, PowerShell, or windows.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_CHECKLIST_JSON = Path("captures/current/hd-endurance-release-checklist-current.json")
DEFAULT_SHORT_STEP_STATUS_JSON = Path("captures/current/hd-soak-short-step-status-current.json")
DEFAULT_DRY_RUN_PLAN_JSON = Path("captures/current/hd-soak-dry-run-plan-current.json")
DEFAULT_INTRO_SKIP_READINESS_JSON = Path("captures/current/hd-soak-intro-skip-rerun-readiness-current.json")
DEFAULT_HARNESS_GUARD_JSON = Path("captures/current/hd-soak-harness-guard-current.json")
DEFAULT_JSON = Path("captures/current/hd-endurance-next-actions-current.json")
DEFAULT_MD = Path("captures/current/hd-endurance-next-actions-current.md")
RUNTIME_POLICY = (
    "repo-only endurance next-action triage; does not launch Clash95, CDB, "
    "wrappers, PowerShell harnesses, or visible windows"
)
MAX_INPUT_DRIFT_PX = 1
SAMPLE_INTERVAL_SEC = 15
MIN_NONBLACK_PERCENT = 10.0
MIN_NONBLACK_PERCENT_TEXT = "10"
MIN_UNIQUE_SAMPLE_COLORS = 8
MAX_ARTIFACT_MB = 250
MAX_WORKING_SET_GROWTH_MB = 64
MAX_PRIVATE_MEMORY_GROWTH_MB = 64
MAX_HANDLE_GROWTH = 128
INTRO_SKIP_CLICK_MODE = "postmessage"
INTRO_SKIP_CLICKS = 8
SKIP_PULSES = 4
MAX_DRY_RUN_PLAN_AGE_HOURS = 12
MIN_APPROVAL_TTL_MINUTES = 30


VISIBLE_SHORT2_COMMAND = (
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
    ".\\scripts\\smoke\\run_hd_soak.ps1 "
    "-Tier short2 -Route menu-idle "
    "-ReportJson captures\\current\\hd-soak-short2-menu-idle-current.json "
    "-ReportMarkdown captures\\current\\hd-soak-short2-menu-idle-current.md "
    f"-IntroSkipClickMode {INTRO_SKIP_CLICK_MODE} "
    f"-IntroSkipClicks {INTRO_SKIP_CLICKS} "
    f"-SkipPulses {SKIP_PULSES} "
    f"-SampleIntervalSec {SAMPLE_INTERVAL_SEC} "
    f"-MaxInputDriftPx {MAX_INPUT_DRIFT_PX} "
    f"-MinNonblackPercent {MIN_NONBLACK_PERCENT_TEXT} "
    f"-MinUniqueSampleColors {MIN_UNIQUE_SAMPLE_COLORS} "
    f"-MaxArtifactMB {MAX_ARTIFACT_MB} "
    f"-MaxWorkingSetGrowthMB {MAX_WORKING_SET_GROWTH_MB} "
    f"-MaxPrivateMemoryGrowthMB {MAX_PRIVATE_MEMORY_GROWTH_MB} "
    f"-MaxHandleGrowth {MAX_HANDLE_GROWTH} "
    "-Execute -AllowVisibleRuntime -RequirePass -Json"
)
DRY_RUN_SHORT2_COMMAND = (
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
    ".\\scripts\\smoke\\run_hd_soak.ps1 -Tier short2 -Route menu-idle "
    "-ReportJson captures\\current\\hd-soak-short2-menu-idle-current.json "
    "-ReportMarkdown captures\\current\\hd-soak-short2-menu-idle-current.md "
    f"-IntroSkipClickMode {INTRO_SKIP_CLICK_MODE} "
    f"-IntroSkipClicks {INTRO_SKIP_CLICKS} "
    f"-SkipPulses {SKIP_PULSES} "
    f"-SampleIntervalSec {SAMPLE_INTERVAL_SEC} "
    f"-MaxInputDriftPx {MAX_INPUT_DRIFT_PX} "
    f"-MinNonblackPercent {MIN_NONBLACK_PERCENT_TEXT} "
    f"-MinUniqueSampleColors {MIN_UNIQUE_SAMPLE_COLORS} "
    f"-MaxArtifactMB {MAX_ARTIFACT_MB} "
    f"-MaxWorkingSetGrowthMB {MAX_WORKING_SET_GROWTH_MB} "
    f"-MaxPrivateMemoryGrowthMB {MAX_PRIVATE_MEMORY_GROWTH_MB} "
    f"-MaxHandleGrowth {MAX_HANDLE_GROWTH} -Json"
)
PYTHON_EXE = (
    r"C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\python\python.exe"
)


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def dry_run_plan_freshness(dry_run_plan: dict[str, Any]) -> dict[str, Any]:
    generated_at = parse_datetime(dry_run_plan.get("generated_at"))
    now = datetime.now(timezone.utc)
    max_age = timedelta(hours=MAX_DRY_RUN_PLAN_AGE_HOURS)
    failures: list[str] = []
    age_seconds: float | None = None
    if generated_at is None:
        failures.append("dry-run plan generated_at is missing or invalid")
    else:
        age = now - generated_at
        age_seconds = age.total_seconds()
        if age < timedelta(minutes=-5):
            failures.append("dry-run plan generated_at is in the future")
        if age > max_age:
            failures.append(
                f"dry-run plan is older than {MAX_DRY_RUN_PLAN_AGE_HOURS} hours; regenerate before approval"
            )
    return {
        "generated_at": dry_run_plan.get("generated_at"),
        "age_seconds": age_seconds,
        "max_age_hours": MAX_DRY_RUN_PLAN_AGE_HOURS,
        "passed": not failures,
        "failures": failures,
    }


def approval_ttl_status(approval_expires_utc: Any) -> dict[str, Any]:
    expires_at = parse_datetime(approval_expires_utc)
    now = datetime.now(timezone.utc)
    failures: list[str] = []
    remaining_seconds: float | None = None
    if expires_at is None:
        failures.append("dry-run plan visible runtime approval expires_utc is missing or invalid")
    else:
        remaining = expires_at - now
        remaining_seconds = remaining.total_seconds()
        if remaining < timedelta(minutes=MIN_APPROVAL_TTL_MINUTES):
            failures.append(
                "dry-run plan visible runtime approval expires too soon; "
                f"regenerate before approval so at least {MIN_APPROVAL_TTL_MINUTES} minutes remain"
            )
    return {
        "expires_utc": approval_expires_utc,
        "remaining_seconds": remaining_seconds,
        "min_remaining_minutes": MIN_APPROVAL_TTL_MINUTES,
        "passed": not failures,
        "failures": failures,
    }


def failing_requirements(checklist: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in checklist.get("requirements", []) if not row.get("passed")]


def group_requirements(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for row in rows:
        key = str(row.get("category") or "uncategorized")
        groups.setdefault(key, []).append(str(row.get("id")))
    return groups


def short_step_record(step_status: dict[str, Any] | None) -> dict[str, Any] | None:
    current = (step_status or {}).get("current_step") or {}
    current_id = current.get("id")
    for step in (step_status or {}).get("steps") or []:
        if step.get("id") == current_id:
            return step
    return None


def normalized_path(value: Any) -> str:
    return str(value or "").replace("/", "\\").rstrip("\\").casefold()


def artifact_path_exists(value: Any) -> bool:
    if not value:
        return False
    return Path(str(value).replace("\\", "/")).exists()


def current_step_artifact_inventory(step: dict[str, Any]) -> dict[str, Any]:
    paths = step.get("paths") or {}
    report_json = paths.get("report_json")
    report_markdown = paths.get("report_markdown")
    guard_json = paths.get("guard_json")
    guard_markdown = paths.get("guard_markdown")
    triage_json = paths.get("triage_json")
    triage_markdown = paths.get("triage_markdown")
    report_exists = artifact_path_exists(report_json)
    guard_exists = artifact_path_exists(guard_json)
    triage_exists = artifact_path_exists(triage_json)
    return {
        "report_json": report_json,
        "report_json_exists": report_exists,
        "report_markdown": report_markdown,
        "report_markdown_exists": artifact_path_exists(report_markdown),
        "guard_json": guard_json,
        "guard_json_exists": guard_exists,
        "guard_markdown": guard_markdown,
        "guard_markdown_exists": artifact_path_exists(guard_markdown),
        "triage_json": triage_json,
        "triage_json_exists": triage_exists,
        "triage_markdown": triage_markdown,
        "triage_markdown_exists": artifact_path_exists(triage_markdown),
        "canonical_runtime_report_missing": bool(report_json) and not report_exists,
        "post_run_guard_missing": bool(guard_json) and not guard_exists,
        "post_run_triage_missing": bool(triage_json) and not triage_exists,
    }


def current_failure_summary(step: dict[str, Any]) -> dict[str, Any] | None:
    summary = step.get("summary") or {}
    if not summary.get("classification"):
        return None
    result = {
        "classification": summary.get("classification"),
        "next_probe": summary.get("next_probe"),
        "frame_sample_count": summary.get("frame_sample_count"),
        "final_route_marker": summary.get("final_route_marker"),
        "candidate_sha256": summary.get("candidate_sha256"),
        "visual_anomaly_passed": summary.get("visual_anomaly_passed"),
        "black_patch_risk_count": summary.get("black_patch_risk_count"),
        "palette_or_stripe_risk_count": summary.get("palette_or_stripe_risk_count"),
        "missing_nonblack_bounds_count": summary.get("missing_nonblack_bounds_count"),
    }
    for key in (
        "wer_followup_matched",
        "wer_followup_status",
        "window_health_mitigation_ready",
    ):
        if key in summary:
            result[key] = summary.get(key)
    return result


def window_health_guard_summary(harness_guard: dict[str, Any] | None) -> dict[str, Any]:
    stop_check = ((harness_guard or {}).get("checks") or {}).get("window_health_stop") or {}
    return {
        "harness_guard_passed": (harness_guard or {}).get("passed") is True,
        "window_health_stop_check_passed": stop_check.get("passed") is True,
        "ready": (
            (harness_guard or {}).get("passed") is True
            and stop_check.get("passed") is True
        ),
    }


def rejected_legacy_runtime_command(command: str, reason: str) -> dict[str, Any] | None:
    if not command:
        return None
    return {
        "command": command,
        "safe_to_run": False,
        "reason": reason,
    }


def plan_required_action(
    base: dict[str, Any],
    step: dict[str, Any],
    *,
    action_id: str,
    why: str,
    legacy_command: str = "",
    dry_run_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        **base,
        "id": action_id,
        "status": "dry_run_plan_required",
        "requires_visible_runtime": False,
        "requires_explicit_user_approval": False,
        "why": why,
        "exact_runtime_command": None,
        "exact_runtime_command_source": None,
        "legacy_step_runtime_command": None,
        "rejected_legacy_runtime_command": rejected_legacy_runtime_command(
            legacy_command,
            "visible-runtime execution now requires a current dry-run plan command with "
            "-VisibleRuntimeApprovalExpiresUtc and -VisibleRuntimeApprovalToken",
        ),
        "plan_verified_execute_command": None,
        "dry_run_plan": dry_run_plan,
        "safe_dry_run_command": step.get("safe_dry_run_command") or DRY_RUN_SHORT2_COMMAND,
        "post_run_validation": [],
        "post_run_handoff_refresh": post_run_handoff_refresh_for_step(step),
        "post_run_evidence_refresh": [],
    }


def dry_run_plan_for_step(
    dry_run_plan: dict[str, Any] | None,
    step: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    if not dry_run_plan:
        return None, []
    failures: list[str] = []
    plan = dry_run_plan.get("plan") or {}
    current = dry_run_plan.get("current_step") or {}
    execute_command = str(dry_run_plan.get("approval_gated_execute_command") or (plan.get("commands") or {}).get("execute") or "")
    freshness = dry_run_plan_freshness(dry_run_plan)
    if not dry_run_plan.get("passed"):
        failures.append("dry-run plan is not passing")
    failures.extend(freshness["failures"])
    if dry_run_plan.get("status") != "ready_for_explicit_approval":
        failures.append(f"dry-run plan status is {dry_run_plan.get('status')!r}")
    if current.get("id") != step.get("id"):
        failures.append("dry-run plan current step does not match the next short step")
    if plan.get("tier") != step.get("tier") or plan.get("route") != step.get("route"):
        failures.append("dry-run plan tier/route do not match the next short step")
    if plan.get("stable_stage_should_change") is not False:
        failures.append("dry-run plan would change the stable stage")
    if plan.get("right_bottom_promotion_blocked") is not True:
        failures.append("dry-run plan does not keep right-bottom promotion blocked")
    if normalized_path(plan.get("candidate_dir")) != normalized_path(r"C:\ClashTests\hd-soak"):
        failures.append("dry-run plan candidate_dir is not C:\\ClashTests\\hd-soak")
    if normalized_path(plan.get("output_root")) != normalized_path(r"C:\ClashCaptures\hd-soak"):
        failures.append("dry-run plan output_root is not C:\\ClashCaptures\\hd-soak")
    if plan.get("input_exists") is not True:
        failures.append("dry-run plan input_exe does not exist or was not confirmed readable")
    if str(plan.get("base_sha_status") or "") != "ok":
        failures.append(f"dry-run plan base_sha_status is {plan.get('base_sha_status')!r}, expected 'ok'")
    if int(plan.get("sample_interval_sec") or 0) != SAMPLE_INTERVAL_SEC:
        failures.append(f"dry-run plan sample_interval_sec is not {SAMPLE_INTERVAL_SEC}")
    frame_limits = plan.get("frame_limits") or {}
    if float(frame_limits.get("min_nonblack_percent") or 0.0) != MIN_NONBLACK_PERCENT:
        failures.append("dry-run plan does not pin min nonblack percent")
    if int(frame_limits.get("min_unique_sample_colors") or 0) != MIN_UNIQUE_SAMPLE_COLORS:
        failures.append("dry-run plan does not pin min unique sample colors")
    growth = plan.get("growth_limits") or {}
    expected_growth = {
        "max_artifact_mb": MAX_ARTIFACT_MB,
        "max_working_set_growth_mb": MAX_WORKING_SET_GROWTH_MB,
        "max_private_memory_growth_mb": MAX_PRIVATE_MEMORY_GROWTH_MB,
        "max_handle_growth": MAX_HANDLE_GROWTH,
    }
    for key, expected in expected_growth.items():
        if int(growth.get(key) or 0) != expected:
            failures.append(f"dry-run plan growth limit {key} is not {expected}")
    approval = plan.get("visible_runtime_approval") or {}
    approval_token = str(approval.get("token") or "")
    approval_expires_utc = str(approval.get("expires_utc") or "")
    if not approval_expires_utc:
        failures.append("dry-run plan visible runtime approval expires_utc is missing")
    token_fields = approval.get("token_fields") or []
    if approval_expires_utc and approval_expires_utc not in token_fields:
        failures.append("dry-run plan visible runtime approval expiry is not covered by token_fields")
    approval_ttl = approval_ttl_status(approval_expires_utc)
    failures.extend(approval_ttl["failures"])
    if int(approval.get("min_ttl_minutes") or 0) != MIN_APPROVAL_TTL_MINUTES:
        failures.append(f"dry-run plan visible runtime approval min_ttl_minutes is not {MIN_APPROVAL_TTL_MINUTES}")
    for fragment in (
        "-Execute",
        "-AllowVisibleRuntime",
        "-IntroSkipClickMode",
        INTRO_SKIP_CLICK_MODE,
        "-IntroSkipClicks",
        str(INTRO_SKIP_CLICKS),
        "-SkipPulses",
        str(SKIP_PULSES),
        "-VisibleRuntimeApprovalExpiresUtc",
        approval_expires_utc,
        "-VisibleRuntimeApprovalToken",
        approval_token,
        "-RequirePass",
        "-Json",
        "-MaxInputDriftPx",
        "-SampleIntervalSec",
        "-MinNonblackPercent",
        "-MinUniqueSampleColors",
        "-MaxArtifactMB",
        "-MaxWorkingSetGrowthMB",
        "-MaxPrivateMemoryGrowthMB",
        "-MaxHandleGrowth",
    ):
        if fragment not in execute_command:
            failures.append(f"dry-run plan execute command missing fragment: {fragment}")
    if failures:
        return None, failures
    return {
        "passed": bool(dry_run_plan.get("passed")),
        "status": dry_run_plan.get("status"),
        "current_step": current.get("id"),
        "candidate_path": plan.get("candidate_path"),
        "candidate_dir": plan.get("candidate_dir"),
        "output_root": plan.get("output_root"),
        "report_json": plan.get("report_json"),
        "report_markdown": plan.get("report_markdown"),
        "input_sha256": plan.get("input_sha256"),
        "base_sha_status": plan.get("base_sha_status"),
        "approval_expires_utc": approval_expires_utc,
        "approval_ttl": approval_ttl,
        "execute_command": execute_command,
        "freshness": freshness,
    }, []


def intro_skip_readiness_for_step(
    intro_skip_readiness: dict[str, Any] | None,
    step: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    if not intro_skip_readiness:
        return None, []
    failures: list[str] = []
    current_step = intro_skip_readiness.get("current_step") or {}
    if intro_skip_readiness.get("passed") is not True:
        failures.append("intro-skip rerun readiness is not passing")
    if intro_skip_readiness.get("status") != "ready_for_explicit_visible_rerun_approval":
        failures.append(f"intro-skip rerun readiness status is {intro_skip_readiness.get('status')!r}")
    if current_step.get("id") != step.get("id"):
        failures.append("intro-skip rerun readiness current step does not match the next short step")
    if failures:
        return None, failures
    triage = intro_skip_readiness.get("triage") or {}
    dry_run = intro_skip_readiness.get("dry_run_plan") or {}
    return {
        "passed": True,
        "status": intro_skip_readiness.get("status"),
        "current_step": current_step.get("id"),
        "classification": triage.get("classification"),
        "candidate_sha256": triage.get("candidate_sha256"),
        "approval_boundary": intro_skip_readiness.get("approval_boundary"),
        "approval_gated_execute_command": dry_run.get("approval_gated_execute_command"),
    }, []


def post_run_validation_for_step(step: dict[str, Any]) -> list[str]:
    return [
        (
            f"{PYTHON_EXE} tools\\hd_soak_short_validation_refresh.py "
            "--write-json captures\\current\\hd-soak-short-validation-refresh-current.json "
            "--write-markdown captures\\current\\hd-soak-short-validation-refresh-current.md "
            "--require-pass"
        ),
        (
            f"{PYTHON_EXE} tools\\hd_soak_short_step_status.py "
            "--write-json captures\\current\\hd-soak-short-step-status-current.json "
            "--write-markdown captures\\current\\hd-soak-short-step-status-current.md "
            "--require-pass"
        ),
        "git diff --check",
    ]


def post_run_handoff_refresh_for_step(_step: dict[str, Any]) -> list[str]:
    return [
        (
            f"{PYTHON_EXE} tools\\hd_soak_dry_run_plan.py "
            "--write-json captures\\current\\hd-soak-dry-run-plan-current.json "
            "--write-markdown captures\\current\\hd-soak-dry-run-plan-current.md "
            "--require-pass"
        ),
        (
            f"{PYTHON_EXE} tools\\hd_endurance_release_checklist.py "
            "--write-json captures\\current\\hd-endurance-release-checklist-current.json "
            "--write-markdown captures\\current\\hd-endurance-release-checklist-current.md"
        ),
        (
            f"{PYTHON_EXE} tools\\hd_soak_intro_skip_rerun_readiness.py "
            "--write-json captures\\current\\hd-soak-intro-skip-rerun-readiness-current.json "
            "--write-markdown captures\\current\\hd-soak-intro-skip-rerun-readiness-current.md"
        ),
        (
            f"{PYTHON_EXE} tools\\hd_endurance_next_actions.py "
            "--write-json captures\\current\\hd-endurance-next-actions-current.json "
            "--write-markdown captures\\current\\hd-endurance-next-actions-current.md "
            "--require-pass"
        ),
        (
            f"{PYTHON_EXE} tools\\hd_soak_approval_preflight.py "
            "--write-json captures\\current\\hd-soak-approval-preflight-current.json "
            "--write-markdown captures\\current\\hd-soak-approval-preflight-current.md "
            "--require-pass"
        ),
    ]


def post_run_evidence_refresh_commands() -> list[str]:
    return [
        (
            f"{PYTHON_EXE} tools\\current_evidence_refresh.py "
            "--write-json captures\\current\\current-evidence-refresh-current.json "
            "--write-markdown captures\\current\\current-evidence-refresh-current.md"
        ),
        f"{PYTHON_EXE} tools\\evidence_index_check.py captures\\current\\hd-map-evidence-current.md --require-pass",
        (
            f"{PYTHON_EXE} tools\\current_completion_summary.py "
            "--write-json captures\\current\\current-completion-summary-current.json "
            "--write-markdown captures\\current\\current-completion-summary-current.md "
            "--require-pass"
        ),
        "git diff --check",
    ]


def next_action_for_short_step(
    step_status: dict[str, Any] | None,
    dry_run_plan: dict[str, Any] | None = None,
    intro_skip_readiness: dict[str, Any] | None = None,
    harness_guard: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    current = (step_status or {}).get("current_step") or {}
    step = short_step_record(step_status)
    if not current or not step:
        return None, []
    status = str(current.get("status") or "")
    base = {
        "source": "short_soak_step_status",
        "short_step_id": current.get("id"),
        "tier": step.get("tier"),
        "route": step.get("route"),
        "writes_outside_repo": step.get("writes_outside_repo")
        or [r"C:\ClashTests\hd-soak", r"C:\ClashCaptures\hd-soak"],
        "must_not_modify": step.get("must_not_modify") or [r"C:\Clash\clash95.exe"],
        "current_step_artifacts": current_step_artifact_inventory(step),
    }
    current_failure = current_failure_summary(step)
    if current_failure:
        base["current_failure"] = current_failure

    if status in {"pending_approval_legacy_compat", "missing_pending_approval"}:
        legacy_command = str(current.get("next_command") or step.get("approval_gated_runtime_command") or "")
        plan_summary, plan_failures = dry_run_plan_for_step(dry_run_plan, step)
        plan_command = (plan_summary or {}).get("execute_command")
        if not plan_command:
            return plan_required_action(
                base,
                step,
                action_id=f"refresh_{current.get('id')}_dry_run_plan",
                why=(
                    "A visible-runtime short soak requires the current tokened dry-run packet. "
                    "Refresh the dry-run plan and approval preflight before requesting approval."
                ),
                legacy_command=legacy_command,
                dry_run_plan=plan_summary,
            ), plan_failures
        command = str(plan_command)
        return {
            **base,
            "id": f"run_{current.get('id')}_soak",
            "status": "approval_required",
            "requires_visible_runtime": True,
            "requires_explicit_user_approval": True,
            "why": (
                "The short soak ladder is not complete. Run the current protected-stage "
                f"{step.get('tier')} {step.get('route')} soak before unlocking later "
                "short, long, or future route lanes."
            ),
            "exact_runtime_command": command,
            "exact_runtime_command_source": "dry_run_plan",
            "legacy_step_runtime_command": None,
            "rejected_legacy_runtime_command": rejected_legacy_runtime_command(
                legacy_command,
                "superseded by the current dry-run plan command with visible-runtime approval token",
            ),
            "plan_verified_execute_command": plan_command,
            "dry_run_plan": plan_summary,
            "safe_dry_run_command": step.get("safe_dry_run_command"),
            "post_run_validation": post_run_validation_for_step(step),
            "post_run_handoff_refresh": post_run_handoff_refresh_for_step(step),
            "post_run_evidence_refresh": post_run_evidence_refresh_commands(),
        }, plan_failures

    summary = step.get("summary") or {}
    next_command = current.get("next_command") or summary.get("next_command")
    if status in {"needs_guard", "failed_needs_triage"}:
        command_kind = "guard" if status == "needs_guard" else "triage"
        return {
            **base,
            "id": f"run_{current.get('id')}_{command_kind}",
            "status": "repo_only_validation_required",
            "requires_visible_runtime": False,
            "requires_explicit_user_approval": False,
            "why": (
                f"The current {step.get('tier')} {step.get('route')} soak has a canonical report, "
                f"but the required {command_kind} output is missing."
            ),
            "exact_runtime_command": None,
            "safe_dry_run_command": None,
            "repo_command": next_command,
            "post_run_validation": post_run_validation_for_step(step),
            "post_run_handoff_refresh": post_run_handoff_refresh_for_step(step),
            "post_run_evidence_refresh": post_run_evidence_refresh_commands(),
        }, []

    if status.startswith("failed_classified_"):
        summary = step.get("summary") or {}
        window_health = window_health_guard_summary(harness_guard)
        application_hang_rerun_ready = (
            summary.get("classification") == "application_hang_wer_closed"
            and summary.get("wer_followup_matched") is True
            and summary.get("wer_followup_status") == "application_hang_confirmed_wer_closed"
            and summary.get("window_health_mitigation_ready") is True
            and window_health.get("ready") is True
        )
        if application_hang_rerun_ready:
            legacy_command = str(current.get("next_command") or step.get("approval_gated_runtime_command") or "")
            plan_summary, plan_failures = dry_run_plan_for_step(dry_run_plan, step)
            plan_command = (plan_summary or {}).get("execute_command")
            if not plan_command:
                return plan_required_action(
                    base,
                    step,
                    action_id=f"refresh_{current.get('id')}_dry_run_plan",
                    why=(
                        "The AppHangB1 retry mitigation is ready, but visible execution requires "
                        "a fresh tokened dry-run packet before approval can be requested."
                    ),
                    legacy_command=legacy_command,
                    dry_run_plan=plan_summary,
                ), plan_failures
            return {
                **base,
                "id": f"rerun_{current.get('id')}_soak",
                "status": "approval_required",
                "requires_visible_runtime": True,
                "requires_explicit_user_approval": True,
                "why": (
                    "Windows confirmed the previous visible result as AppHangB1 and closed the "
                    "nonresponsive candidate. The matching hidden CDB route stayed live, and the "
                    "harness guard now proves responsiveness sampling stops input and capture at "
                    "the first hung or missing live target window."
                ),
                "exact_runtime_command": str(plan_command),
                "exact_runtime_command_source": "dry_run_plan",
                "legacy_step_runtime_command": None,
                "rejected_legacy_runtime_command": rejected_legacy_runtime_command(
                    legacy_command,
                    "superseded by the current dry-run plan command with visible-runtime approval token",
                ),
                "plan_verified_execute_command": plan_command,
                "dry_run_plan": plan_summary,
                "application_hang_rerun_readiness": {
                    "wer_followup_matched": True,
                    "wer_followup_status": summary.get("wer_followup_status"),
                    "window_health_mitigation_ready": True,
                    **window_health,
                },
                "safe_dry_run_command": step.get("safe_dry_run_command"),
                "post_run_validation": post_run_validation_for_step(step),
                "post_run_handoff_refresh": post_run_handoff_refresh_for_step(step),
                "post_run_evidence_refresh": post_run_evidence_refresh_commands(),
            }, plan_failures
        window_missing_rerun_ready = (
            summary.get("classification") == "window_missing_while_process_alive"
            and summary.get("window_health_mitigation_ready") is True
            and window_health.get("ready") is True
        )
        if window_missing_rerun_ready:
            legacy_command = str(current.get("next_command") or step.get("approval_gated_runtime_command") or "")
            plan_summary, plan_failures = dry_run_plan_for_step(dry_run_plan, step)
            plan_command = (plan_summary or {}).get("execute_command")
            if not plan_command:
                return plan_required_action(
                    base,
                    step,
                    action_id=f"refresh_{current.get('id')}_dry_run_plan",
                    why=(
                        "The window-missing mitigation is ready, but visible execution requires "
                        "a fresh tokened dry-run packet before approval can be requested."
                    ),
                    legacy_command=legacy_command,
                    dry_run_plan=plan_summary,
                ), plan_failures
            return {
                **base,
                "id": f"rerun_{current.get('id')}_soak",
                "status": "approval_required",
                "requires_visible_runtime": True,
                "requires_explicit_user_approval": True,
                "why": (
                    "The previous visible run lost its application/windowed target window while "
                    "the process stayed alive. The harness now grace-retries transient window "
                    "loss, verifies the menu before route input, drives menu clicks with the "
                    "pulse-mode engine-aim mechanism, and verifies the gameplay map on screen, "
                    "while still stopping at the first persistently missing live target window."
                ),
                "exact_runtime_command": str(plan_command),
                "exact_runtime_command_source": "dry_run_plan",
                "legacy_step_runtime_command": None,
                "rejected_legacy_runtime_command": rejected_legacy_runtime_command(
                    legacy_command,
                    "superseded by the current dry-run plan command with visible-runtime approval token",
                ),
                "plan_verified_execute_command": plan_command,
                "dry_run_plan": plan_summary,
                "window_missing_rerun_readiness": {
                    "window_health_mitigation_ready": True,
                    **window_health,
                },
                "safe_dry_run_command": step.get("safe_dry_run_command"),
                "post_run_validation": post_run_validation_for_step(step),
                "post_run_handoff_refresh": post_run_handoff_refresh_for_step(step),
                "post_run_evidence_refresh": post_run_evidence_refresh_commands(),
            }, plan_failures
        if summary.get("classification") == "input_environment_permission_denied":
            legacy_command = str(current.get("next_command") or step.get("approval_gated_runtime_command") or "")
            plan_summary, plan_failures = dry_run_plan_for_step(dry_run_plan, step)
            plan_command = (plan_summary or {}).get("execute_command")
            if not plan_command:
                return plan_required_action(
                    base,
                    step,
                    action_id=f"refresh_{current.get('id')}_dry_run_plan",
                    why=(
                        "The previous route was blocked by Windows input-API permissions. "
                        "Refresh the tokened dry-run plan before requesting an unsandboxed rerun."
                    ),
                    legacy_command=legacy_command,
                    dry_run_plan=plan_summary,
                ), plan_failures
            return {
                **base,
                "id": f"rerun_{current.get('id')}_soak",
                "status": "approval_required",
                "requires_visible_runtime": True,
                "requires_explicit_user_approval": True,
                "why": (
                    "The previous route was blocked by Windows input-API permissions, not "
                    "classified as game behavior. Rerun the current tokened postmessage command "
                    "only in a fresh explicitly approved unsandboxed Windows session."
                ),
                "exact_runtime_command": str(plan_command),
                "exact_runtime_command_source": "dry_run_plan",
                "legacy_step_runtime_command": None,
                "rejected_legacy_runtime_command": rejected_legacy_runtime_command(
                    legacy_command,
                    "superseded by the current dry-run plan command with visible-runtime approval token",
                ),
                "plan_verified_execute_command": plan_command,
                "dry_run_plan": plan_summary,
                "safe_dry_run_command": step.get("safe_dry_run_command"),
                "post_run_validation": post_run_validation_for_step(step),
                "post_run_handoff_refresh": post_run_handoff_refresh_for_step(step),
                "post_run_evidence_refresh": post_run_evidence_refresh_commands(),
            }, plan_failures
        readiness_summary = None
        readiness_failures: list[str] = []
        if summary.get("classification") == "intro_skip_input_drift_exit":
            readiness_summary, readiness_failures = intro_skip_readiness_for_step(intro_skip_readiness, step)
        if summary.get("classification") == "intro_skip_input_drift_exit" and readiness_summary:
            legacy_command = str(current.get("next_command") or step.get("approval_gated_runtime_command") or "")
            plan_summary, plan_failures = dry_run_plan_for_step(dry_run_plan, step)
            plan_command = (plan_summary or {}).get("execute_command")
            if not plan_command:
                return plan_required_action(
                    base,
                    step,
                    action_id=f"refresh_{current.get('id')}_dry_run_plan",
                    why=(
                        "The intro-skip rerun is ready in principle, but the actual visible-runtime "
                        "command must come from a current tokened dry-run plan."
                    ),
                    legacy_command=str(readiness_summary.get("approval_gated_execute_command") or legacy_command),
                    dry_run_plan=plan_summary,
                ), plan_failures
            command = str(plan_command)
            return {
                **base,
                "id": f"rerun_{current.get('id')}_soak",
                "status": "approval_required",
                "requires_visible_runtime": True,
                "requires_explicit_user_approval": True,
                "why": (
                    "The previous short2 menu-idle run failed during intro-skip input, "
                    "and the repo-only rerun readiness gate now proves the harness uses "
                    "postmessage intro-skip prep. Rerun only after explicit visible-window approval."
                ),
                "exact_runtime_command": command,
                "exact_runtime_command_source": "dry_run_plan",
                "legacy_step_runtime_command": None,
                "rejected_legacy_runtime_command": rejected_legacy_runtime_command(
                    legacy_command,
                    "superseded by the current dry-run plan command with visible-runtime approval token",
                ),
                "plan_verified_execute_command": plan_command,
                "dry_run_plan": plan_summary,
                "intro_skip_rerun_readiness": readiness_summary,
                "safe_dry_run_command": step.get("safe_dry_run_command"),
                "post_run_validation": post_run_validation_for_step(step),
                "post_run_handoff_refresh": post_run_handoff_refresh_for_step(step),
                "post_run_evidence_refresh": post_run_evidence_refresh_commands(),
            }, plan_failures
        if (
            summary.get("classification") == "intro_skip_input_drift_exit"
            and summary.get("intro_skip_click_mode") == "postmessage"
        ):
            return {
                **base,
                "id": f"fix_{current.get('id')}_intro_transition",
                "status": "repo_only_harness_fix_required",
                "requires_visible_runtime": False,
                "requires_explicit_user_approval": False,
                "why": summary.get("next_probe")
                or "Stop or reacquire intro-skip postmessage repeats when the window transitions.",
                "exact_runtime_command": None,
                "safe_dry_run_command": step.get("safe_dry_run_command"),
                "repo_command": None,
                "triage": {
                    "classification": summary.get("classification"),
                    "next_probe": summary.get("next_probe"),
                    "intro_skip_click_mode": summary.get("intro_skip_click_mode"),
                    "intro_skip_click_repeat": summary.get("intro_skip_click_repeat"),
                    "intro_skip_click_path_verified": summary.get("intro_skip_click_path_verified"),
                    "final_route_marker": summary.get("final_route_marker"),
                    "candidate_sha256": summary.get("candidate_sha256"),
                },
                "post_run_validation": post_run_validation_for_step(step),
                "post_run_handoff_refresh": post_run_handoff_refresh_for_step(step),
                "post_run_evidence_refresh": post_run_evidence_refresh_commands(),
            }, []
        if readiness_failures:
            return None, readiness_failures
        return {
            **base,
            "id": f"inspect_{current.get('id')}_triage",
            "status": "triage_followup_required",
            "requires_visible_runtime": False,
            "requires_explicit_user_approval": False,
            "why": summary.get("next_probe")
            or "Inspect the classified short-soak failure before rerunning or changing patches.",
            "exact_runtime_command": None,
            "safe_dry_run_command": None,
            "repo_command": None,
            "triage": {
                "classification": summary.get("classification"),
                "next_probe": summary.get("next_probe"),
                "frame_sample_count": summary.get("frame_sample_count"),
                "final_route_marker": summary.get("final_route_marker"),
                "candidate_sha256": summary.get("candidate_sha256"),
            },
            "post_run_validation": post_run_validation_for_step(step),
            "post_run_handoff_refresh": post_run_handoff_refresh_for_step(step),
            "post_run_evidence_refresh": post_run_evidence_refresh_commands(),
        }, []

    return None, []


def next_action_for_milestone(milestone: dict[str, Any] | None) -> dict[str, Any]:
    milestone_id = (milestone or {}).get("id")
    if milestone_id == "short2_menu_idle_soak":
        step = {
            "id": "short2_menu_idle",
            "tier": "short2",
            "route": "menu-idle",
            "paths": {
                "report_json": r"captures\current\hd-soak-short2-menu-idle-current.json",
                "report_markdown": r"captures\current\hd-soak-short2-menu-idle-current.md",
                "guard_json": r"captures\current\hd-soak-short2-menu-idle-guard-current.json",
                "guard_markdown": r"captures\current\hd-soak-short2-menu-idle-guard-current.md",
                "triage_json": r"captures\current\hd-soak-short2-menu-idle-triage-current.json",
                "triage_markdown": r"captures\current\hd-soak-short2-menu-idle-triage-current.md",
            },
            "safe_dry_run_command": DRY_RUN_SHORT2_COMMAND,
        }
        base = {
            "writes_outside_repo": [
                r"C:\ClashTests\hd-soak",
                r"C:\ClashCaptures\hd-soak",
            ],
            "must_not_modify": [r"C:\Clash\clash95.exe"],
            "current_step_artifacts": current_step_artifact_inventory(step),
        }
        return plan_required_action(
            base,
            step,
            action_id="refresh_short2_menu_idle_dry_run_plan",
            why=(
                "The release checklist cannot progress until one protected-stage short2 "
                "menu-idle soak passes, but visible-runtime approval must start from a "
                "fresh tokened dry-run plan."
            ),
            legacy_command=VISIBLE_SHORT2_COMMAND,
        )
    if milestone:
        return {
            "id": f"resolve_{milestone_id}",
            "status": "needs_planning",
            "requires_visible_runtime": False,
            "requires_explicit_user_approval": False,
            "why": milestone.get("next_probe") or "Resolve the next release-checklist item.",
            "exact_runtime_command": None,
            "safe_dry_run_command": None,
            "writes_outside_repo": [],
            "must_not_modify": [r"C:\Clash\clash95.exe"],
            "post_run_validation": ["tools\\hd_endurance_release_checklist.py"],
        }
    return {
        "id": "release_audit",
        "status": "ready_for_release_audit",
        "requires_visible_runtime": False,
        "requires_explicit_user_approval": False,
        "why": "No failing release-checklist milestone was reported.",
        "exact_runtime_command": None,
        "safe_dry_run_command": None,
        "writes_outside_repo": [],
        "must_not_modify": [r"C:\Clash\clash95.exe"],
        "post_run_validation": ["tools\\hd_endurance_release_checklist.py --require-pass"],
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    checklist = load_json(args.checklist_json)
    short_step_status_path = getattr(args, "short_step_status_json", DEFAULT_SHORT_STEP_STATUS_JSON)
    dry_run_plan_path = getattr(args, "dry_run_plan_json", None)
    intro_skip_readiness_path = getattr(args, "intro_skip_readiness_json", None)
    harness_guard_path = getattr(args, "harness_guard_json", DEFAULT_HARNESS_GUARD_JSON)
    step_status = load_json(short_step_status_path)
    dry_run_plan = load_json(dry_run_plan_path) if dry_run_plan_path and dry_run_plan_path.exists() else None
    intro_skip_readiness = (
        load_json(intro_skip_readiness_path)
        if intro_skip_readiness_path and intro_skip_readiness_path.exists()
        else None
    )
    harness_guard = (
        load_json(harness_guard_path)
        if harness_guard_path and harness_guard_path.exists()
        else None
    )
    failures: list[str] = []
    if checklist is None:
        failures.append(f"missing release checklist: {args.checklist_json}")
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "passed": False,
            "runtime_policy": RUNTIME_POLICY,
            "checklist": str(args.checklist_json),
            "next_action": None,
            "failures": failures,
        }

    open_rows = failing_requirements(checklist)
    milestone = checklist.get("next_milestone")
    short_step_action, short_step_failures = next_action_for_short_step(
        step_status,
        dry_run_plan,
        intro_skip_readiness,
        harness_guard,
    )
    failures.extend(short_step_failures)
    next_action = short_step_action or next_action_for_milestone(milestone)
    if checklist.get("full_game_complete"):
        status = "release_complete_pending_audit"
    elif next_action["requires_explicit_user_approval"]:
        status = "waiting_for_explicit_visible_runtime_approval"
    else:
        status = "repo_only_followup_available"

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "checklist": str(args.checklist_json),
        "short_step_status": str(short_step_status_path),
        "dry_run_plan": str(dry_run_plan_path) if dry_run_plan_path else None,
        "intro_skip_readiness": str(intro_skip_readiness_path) if intro_skip_readiness_path else None,
        "harness_guard": str(harness_guard_path) if harness_guard_path else None,
        "short_ladder_complete": bool((step_status or {}).get("ladder_complete")),
        "current_short_step": (step_status or {}).get("current_step"),
        "full_game_complete": bool(checklist.get("full_game_complete")),
        "release_counts": checklist.get("counts"),
        "status": status,
        "next_milestone": milestone,
        "next_action": next_action,
        "open_requirement_count": len(open_rows),
        "open_requirement_groups": group_requirements(open_rows),
        "open_requirements": [
            {
                "id": row.get("id"),
                "status": row.get("status"),
                "category": row.get("category"),
                "summary": row.get("summary"),
                "next_probe": row.get("next_probe"),
            }
            for row in open_rows
        ],
        "failures": failures,
    }
    return report


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# HD Endurance Next Actions",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Status: `{report.get('status')}`",
        f"- Current short step: `{(report.get('current_short_step') or {}).get('id')}`",
        f"- Full game complete: `{report.get('full_game_complete')}`",
        f"- Open requirements: `{report.get('open_requirement_count')}`",
    ]
    action = report.get("next_action") or {}
    if action:
        lines.extend(
            [
                "",
                "## Next Action",
                "",
                f"- `{action.get('id')}`: `{action.get('status')}`",
                f"- Requires visible runtime: `{action.get('requires_visible_runtime')}`",
                f"- Requires explicit user approval: `{action.get('requires_explicit_user_approval')}`",
                f"- Why: {action.get('why')}",
            ]
        )
        artifacts = action.get("current_step_artifacts") or {}
        if artifacts:
            lines.extend(
                [
                    "",
                    "Current step artifacts:",
                    "",
                    (
                        f"- Report JSON: `{artifacts.get('report_json')}` "
                        f"exists=`{artifacts.get('report_json_exists')}`"
                    ),
                    (
                        f"- Guard JSON: `{artifacts.get('guard_json')}` "
                        f"exists=`{artifacts.get('guard_json_exists')}`"
                    ),
                    (
                        f"- Triage JSON: `{artifacts.get('triage_json')}` "
                        f"exists=`{artifacts.get('triage_json_exists')}`"
                    ),
                    f"- Canonical runtime report missing: `{artifacts.get('canonical_runtime_report_missing')}`",
                    f"- Post-run guard missing: `{artifacts.get('post_run_guard_missing')}`",
                    f"- Post-run triage missing: `{artifacts.get('post_run_triage_missing')}`",
                ]
            )
        if action.get("safe_dry_run_command"):
            lines.extend(["", "Safe dry-run command:", "", "```powershell", action["safe_dry_run_command"], "```"])
        plan_verified_command = action.get("plan_verified_execute_command")
        if plan_verified_command:
            dry_run_plan = action.get("dry_run_plan") or {}
            lines.extend(
                [
                    "",
                    "Approval-gated runtime command (plan-verified):",
                    "",
                    f"- Dry-run plan status: `{dry_run_plan.get('status')}`",
                    f"- Candidate path: `{dry_run_plan.get('candidate_path')}`",
                    f"- Output root: `{dry_run_plan.get('output_root')}`",
                    "",
                    "```powershell",
                    plan_verified_command,
                    "```",
                ]
            )
        if action.get("exact_runtime_command") and action.get("exact_runtime_command") != plan_verified_command:
            lines.extend(
                [
                    "",
                    "Approval-gated runtime command:",
                    "",
                    "```powershell",
                    action["exact_runtime_command"],
                    "```",
                ]
            )
        rejected_legacy = action.get("rejected_legacy_runtime_command") or {}
        if rejected_legacy:
            lines.extend(
                [
                    "",
                    "Rejected legacy runtime command:",
                    "",
                    f"- Safe to run: `{rejected_legacy.get('safe_to_run')}`",
                    f"- Reason: {rejected_legacy.get('reason')}",
                    "- Command body: omitted from Markdown; retained in JSON for audit.",
                ]
            )
        if action.get("repo_command"):
            lines.extend(["", "Repo-only command:", "", "```powershell", action["repo_command"], "```"])
        if action.get("triage"):
            triage = action["triage"]
            lines.extend(
                [
                    "",
                    "Triage:",
                    "",
                    f"- Classification: `{triage.get('classification')}`",
                    f"- Next probe: {triage.get('next_probe')}",
                    f"- Final route marker: `{triage.get('final_route_marker')}`",
                    f"- Candidate SHA-256: `{triage.get('candidate_sha256')}`",
                ]
            )
        current_failure = action.get("current_failure") or {}
        if current_failure:
            lines.extend(
                [
                    "",
                    "Current failure:",
                    "",
                    f"- Classification: `{current_failure.get('classification')}`",
                    f"- Next probe: {current_failure.get('next_probe')}",
                    f"- Final route marker: `{current_failure.get('final_route_marker')}`",
                    f"- Candidate SHA-256: `{current_failure.get('candidate_sha256')}`",
                    f"- Visual anomaly passed: `{current_failure.get('visual_anomaly_passed')}`",
                    f"- Black/blank patch risk count: `{current_failure.get('black_patch_risk_count')}`",
                    f"- Palette/stripe risk count: `{current_failure.get('palette_or_stripe_risk_count')}`",
                    f"- Missing nonblack bounds count: `{current_failure.get('missing_nonblack_bounds_count')}`",
                ]
            )
        if action.get("post_run_validation"):
            lines.extend(["", "Focused post-run validation:", ""])
            for command in action["post_run_validation"]:
                lines.append(f"- `{command}`")
        if action.get("post_run_handoff_refresh"):
            lines.extend(["", "Post-run handoff refresh:", ""])
            for command in action["post_run_handoff_refresh"]:
                lines.append(f"- `{command}`")
        if action.get("post_run_evidence_refresh"):
            lines.extend(["", "Broad evidence refresh:", ""])
            for command in action["post_run_evidence_refresh"]:
                lines.append(f"- `{command}`")

    groups = report.get("open_requirement_groups") or {}
    if groups:
        lines.extend(["", "## Open Requirement Groups", ""])
        for category, ids in groups.items():
            lines.append(f"- `{category}`: `{', '.join(ids)}`")

    open_requirements = report.get("open_requirements") or []
    if open_requirements:
        lines.extend(["", "## Open Requirement Details", ""])
        for row in open_requirements:
            lines.append(
                f"- `{row.get('id')}` (`{row.get('category')}`, `{row.get('status')}`): "
                f"{row.get('summary')} Next probe: {row.get('next_probe')}"
            )

    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        for failure in report["failures"]:
            lines.append(f"- {failure}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], json_path: Path | None, md_path: Path | None) -> None:
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    if md_path:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(to_markdown(report), encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checklist-json", type=Path, default=DEFAULT_CHECKLIST_JSON)
    parser.add_argument("--short-step-status-json", type=Path, default=DEFAULT_SHORT_STEP_STATUS_JSON)
    parser.add_argument("--dry-run-plan-json", type=Path, default=DEFAULT_DRY_RUN_PLAN_JSON)
    parser.add_argument("--intro-skip-readiness-json", type=Path, default=DEFAULT_INTRO_SKIP_READINESS_JSON)
    parser.add_argument("--harness-guard-json", type=Path, default=DEFAULT_HARNESS_GUARD_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    report = build_report(args)
    write_outputs(report, args.write_json, args.write_markdown)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"status: {report.get('status')}")
    action = report.get("next_action") or {}
    if action:
        print(f"next-action: {action.get('id')} ({action.get('status')})")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
