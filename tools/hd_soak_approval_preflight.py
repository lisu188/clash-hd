#!/usr/bin/env python3
"""Build the approval preflight packet for the current short HD soak step.

This report is repo-only. It does not launch the game. It verifies that the
next visible-runtime command is canonical, approval-gated, non-promoting, and
paired with post-run validation before asking for explicit approval.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


RUNTIME_POLICY = (
    "repo-only visible-runtime approval preflight; does not launch Clash95, CDB, "
    "wrappers, PowerShell harnesses, or visible windows"
)
DEFAULT_NEXT_ACTIONS_JSON = Path("captures/current/hd-endurance-next-actions-current.json")
DEFAULT_STEP_STATUS_JSON = Path("captures/current/hd-soak-short-step-status-current.json")
DEFAULT_HARNESS_GUARD_JSON = Path("captures/current/hd-soak-harness-guard-current.json")
DEFAULT_DRY_RUN_PLAN_JSON = Path("captures/current/hd-soak-dry-run-plan-current.json")
DEFAULT_INTRO_SKIP_READINESS_JSON = Path("captures/current/hd-soak-intro-skip-rerun-readiness-current.json")
DEFAULT_VISIBLE_RUNTIME_GUARD_JSON = Path("captures/current/visible-runtime-launcher-guard-current.json")
DEFAULT_PROCESS_HYGIENE_JSON = Path("captures/current/process-hygiene-guard-current.json")
DEFAULT_EXE_ARTIFACT_JSON = Path("captures/current/exe-artifact-guard-current.json")
DEFAULT_JSON = Path("captures/current/hd-soak-approval-preflight-current.json")
DEFAULT_MD = Path("captures/current/hd-soak-approval-preflight-current.md")

EXPECTED_FIRST_STEP = "short2_menu_idle"
EXPECTED_REPORT_JSON = r"captures\current\hd-soak-short2-menu-idle-current.json"
EXPECTED_REPORT_MD = r"captures\current\hd-soak-short2-menu-idle-current.md"
EXPECTED_GUARD_JSON = r"captures\current\hd-soak-short2-menu-idle-guard-current.json"
EXPECTED_TRIAGE_JSON = r"captures\current\hd-soak-short2-menu-idle-triage-current.json"
EXPECTED_WRITES = {r"C:\ClashTests\hd-soak", r"C:\ClashCaptures\hd-soak"}
MUST_NOT_MODIFY = r"C:\Clash\clash95.exe"
EXPECTED_MAX_INPUT_DRIFT_PX = 1
EXPECTED_SAMPLE_INTERVAL_SEC = 15
EXPECTED_MIN_NONBLACK_PERCENT = 10.0
EXPECTED_MIN_NONBLACK_PERCENT_TEXT = "10"
EXPECTED_MIN_UNIQUE_SAMPLE_COLORS = 8
EXPECTED_MAX_ARTIFACT_MB = 250
EXPECTED_MAX_WORKING_SET_GROWTH_MB = 64
EXPECTED_MAX_PRIVATE_MEMORY_GROWTH_MB = 64
EXPECTED_MAX_HANDLE_GROWTH = 128
EXPECTED_INTRO_SKIP_CLICK_MODE = "postmessage"
EXPECTED_INTRO_SKIP_CLICKS = 8
EXPECTED_SKIP_PULSES = 4
MAX_DRY_RUN_PLAN_AGE_HOURS = 12
MIN_APPROVAL_TTL_MINUTES = 30
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


def step_slug(step: dict[str, Any]) -> str:
    return str(step.get("id") or f"{step.get('tier')}_{step.get('route')}")


def normalized_text(value: Any) -> str:
    return str(value or "").replace("/", "\\").rstrip("\\").casefold()


def artifact_path_exists(value: Any) -> bool:
    if not value:
        return False
    return Path(str(value).replace("\\", "/")).exists()


def current_step_artifact_inventory(paths: dict[str, str]) -> dict[str, Any]:
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
    return {
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


def text_contains_path(text: str, path_text: str | None) -> bool:
    if not path_text:
        return False
    needle = normalized_text(path_text)
    haystack = normalized_text(text)
    return needle in haystack or haystack.endswith(needle)


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def dry_run_plan_freshness(
    dry_run_plan: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    generated_at = parse_datetime(dry_run_plan.get("generated_at"))
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    max_age = timedelta(hours=MAX_DRY_RUN_PLAN_AGE_HOURS)
    failures: list[str] = []
    age_seconds: float | None = None
    if generated_at is None:
        failures.append("dry-run plan generated_at is missing or invalid")
    else:
        age = current_time - generated_at
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


def approval_ttl_status(approval_expires_utc: Any, *, now: datetime | None = None) -> dict[str, Any]:
    expires_at = parse_datetime(approval_expires_utc)
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    failures: list[str] = []
    remaining_seconds: float | None = None
    if expires_at is None:
        failures.append("dry-run plan visible runtime approval expires_utc is missing or invalid")
    else:
        remaining = expires_at - current_time
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


def approval_limits_from_plan(plan: dict[str, Any], approval_ttl: dict[str, Any]) -> dict[str, Any]:
    growth = plan.get("growth_limits") or {}
    frame = plan.get("frame_limits") or {}
    input_limits = plan.get("input_limits") or {}
    approval = plan.get("visible_runtime_approval") or {}
    return {
        "sample_interval_sec": plan.get("sample_interval_sec"),
        "max_input_drift_px": input_limits.get("max_input_drift_px"),
        "min_nonblack_percent": frame.get("min_nonblack_percent"),
        "min_unique_sample_colors": frame.get("min_unique_sample_colors"),
        "max_artifact_mb": growth.get("max_artifact_mb"),
        "max_working_set_growth_mb": growth.get("max_working_set_growth_mb"),
        "max_private_memory_growth_mb": growth.get("max_private_memory_growth_mb"),
        "max_handle_growth": growth.get("max_handle_growth"),
        "approval_token_kind": approval.get("token_kind"),
        "approval_expires_utc": approval.get("expires_utc"),
        "approval_remaining_seconds": approval_ttl.get("remaining_seconds"),
        "min_approval_ttl_minutes": approval_ttl.get("min_remaining_minutes"),
    }


def command_has_required_shape(command: str, step: dict[str, Any], paths: dict[str, str]) -> list[str]:
    failures: list[str] = []
    required_fragments = [
        r".\scripts\smoke\run_hd_soak.ps1",
        f"-Tier {step.get('tier')}",
        f"-Route {step.get('route')}",
        f"-ReportJson {paths.get('report_json')}",
        f"-ReportMarkdown {paths.get('report_markdown')}",
        f"-IntroSkipClickMode {EXPECTED_INTRO_SKIP_CLICK_MODE}",
        f"-IntroSkipClicks {EXPECTED_INTRO_SKIP_CLICKS}",
        f"-SkipPulses {EXPECTED_SKIP_PULSES}",
        f"-SampleIntervalSec {EXPECTED_SAMPLE_INTERVAL_SEC}",
        f"-MaxInputDriftPx {EXPECTED_MAX_INPUT_DRIFT_PX}",
        f"-MinNonblackPercent {EXPECTED_MIN_NONBLACK_PERCENT_TEXT}",
        f"-MinUniqueSampleColors {EXPECTED_MIN_UNIQUE_SAMPLE_COLORS}",
        f"-MaxArtifactMB {EXPECTED_MAX_ARTIFACT_MB}",
        f"-MaxWorkingSetGrowthMB {EXPECTED_MAX_WORKING_SET_GROWTH_MB}",
        f"-MaxPrivateMemoryGrowthMB {EXPECTED_MAX_PRIVATE_MEMORY_GROWTH_MB}",
        f"-MaxHandleGrowth {EXPECTED_MAX_HANDLE_GROWTH}",
        "-Execute -AllowVisibleRuntime -RequirePass",
        "-Json",
    ]
    for fragment in required_fragments:
        if fragment not in command:
            failures.append(f"runtime command missing fragment: {fragment}")
    return failures


def dry_run_has_required_shape(command: str, step: dict[str, Any], paths: dict[str, str]) -> list[str]:
    failures: list[str] = []
    if "-Execute" in command or "-AllowVisibleRuntime" in command:
        failures.append("safe dry-run command includes execution/visible-runtime flags")
    for fragment in (
        r".\scripts\smoke\run_hd_soak.ps1",
        f"-Tier {step.get('tier')}",
        f"-Route {step.get('route')}",
        f"-ReportJson {paths.get('report_json')}",
        f"-ReportMarkdown {paths.get('report_markdown')}",
        f"-IntroSkipClickMode {EXPECTED_INTRO_SKIP_CLICK_MODE}",
        f"-IntroSkipClicks {EXPECTED_INTRO_SKIP_CLICKS}",
        f"-SkipPulses {EXPECTED_SKIP_PULSES}",
        f"-SampleIntervalSec {EXPECTED_SAMPLE_INTERVAL_SEC}",
        f"-MaxInputDriftPx {EXPECTED_MAX_INPUT_DRIFT_PX}",
        f"-MinNonblackPercent {EXPECTED_MIN_NONBLACK_PERCENT_TEXT}",
        f"-MinUniqueSampleColors {EXPECTED_MIN_UNIQUE_SAMPLE_COLORS}",
        f"-MaxArtifactMB {EXPECTED_MAX_ARTIFACT_MB}",
        f"-MaxWorkingSetGrowthMB {EXPECTED_MAX_WORKING_SET_GROWTH_MB}",
        f"-MaxPrivateMemoryGrowthMB {EXPECTED_MAX_PRIVATE_MEMORY_GROWTH_MB}",
        f"-MaxHandleGrowth {EXPECTED_MAX_HANDLE_GROWTH}",
        "-Json",
    ):
        if fragment not in command:
            failures.append(f"dry-run command missing fragment: {fragment}")
    return failures


def dry_run_plan_failures(
    dry_run_plan: dict[str, Any],
    current_step: dict[str, Any],
    step: dict[str, Any],
    paths: dict[str, str],
) -> list[str]:
    failures: list[str] = []
    plan = dry_run_plan.get("plan") or {}
    plan_step = dry_run_plan.get("current_step") or {}
    execute_command = str(dry_run_plan.get("approval_gated_execute_command") or (plan.get("commands") or {}).get("execute") or "")
    freshness = dry_run_plan_freshness(dry_run_plan)
    if not dry_run_plan.get("passed"):
        failures.append("dry-run plan report is not passing")
    failures.extend(freshness["failures"])
    if dry_run_plan.get("status") != "ready_for_explicit_approval":
        failures.append(f"dry-run plan status is {dry_run_plan.get('status')!r}")
    if plan_step.get("id") != current_step.get("id"):
        failures.append("dry-run plan current step does not match step-status current step")
    if plan_step.get("status") != current_step.get("status"):
        failures.append("dry-run plan current-step status does not match step-status current step")
    if plan.get("dry_run") is not True:
        failures.append("dry-run plan payload is not marked as a dry run")
    if plan.get("stage") and plan.get("stage") != plan.get("protected_stable_stage"):
        failures.append("dry-run plan stage does not match its protected stable stage")
    if plan.get("stable_stage_should_change") is not False:
        failures.append("dry-run plan would change the stable stage")
    if plan.get("right_bottom_promotion_blocked") is not True:
        failures.append("dry-run plan does not keep right-bottom promotion blocked")
    if plan.get("tier") != step.get("tier") or plan.get("route") != step.get("route"):
        failures.append("dry-run plan tier/route do not match the current step")
    if (plan.get("input_limits") or {}).get("max_input_drift_px") != EXPECTED_MAX_INPUT_DRIFT_PX:
        failures.append("dry-run plan does not pin max input drift to 1 px")
    if int(plan.get("sample_interval_sec") or 0) != EXPECTED_SAMPLE_INTERVAL_SEC:
        failures.append(f"dry-run plan sample_interval_sec is not {EXPECTED_SAMPLE_INTERVAL_SEC}")
    frame_limits = plan.get("frame_limits") or {}
    if float(frame_limits.get("min_nonblack_percent") or 0.0) != EXPECTED_MIN_NONBLACK_PERCENT:
        failures.append("dry-run plan does not pin min nonblack percent")
    if int(frame_limits.get("min_unique_sample_colors") or 0) != EXPECTED_MIN_UNIQUE_SAMPLE_COLORS:
        failures.append("dry-run plan does not pin min unique sample colors")
    growth = plan.get("growth_limits") or {}
    expected_growth = {
        "max_artifact_mb": EXPECTED_MAX_ARTIFACT_MB,
        "max_working_set_growth_mb": EXPECTED_MAX_WORKING_SET_GROWTH_MB,
        "max_private_memory_growth_mb": EXPECTED_MAX_PRIVATE_MEMORY_GROWTH_MB,
        "max_handle_growth": EXPECTED_MAX_HANDLE_GROWTH,
    }
    for key, expected in expected_growth.items():
        if int(growth.get(key) or 0) != expected:
            failures.append(f"dry-run plan growth limit {key} is not {expected}")
    intro_skip = plan.get("intro_skip") or {}
    if intro_skip.get("click_mode") != EXPECTED_INTRO_SKIP_CLICK_MODE:
        failures.append("dry-run plan intro_skip click_mode is not postmessage")
    if int(intro_skip.get("click_repeat") or 0) != EXPECTED_INTRO_SKIP_CLICKS:
        failures.append(f"dry-run plan intro_skip click_repeat is not {EXPECTED_INTRO_SKIP_CLICKS}")
    if int(intro_skip.get("space_pulses") or 0) != EXPECTED_SKIP_PULSES:
        failures.append(f"dry-run plan intro_skip space_pulses is not {EXPECTED_SKIP_PULSES}")
    if intro_skip.get("proof_class") != "intro_skip_harness_prep_not_manual_directinput_release_proof":
        failures.append("dry-run plan intro_skip proof_class is missing the non-manual proof boundary")
    approval = plan.get("visible_runtime_approval") or {}
    token = str(approval.get("token") or "")
    if len(token) != 16 or not all(ch in "0123456789abcdef" for ch in token):
        failures.append("dry-run plan visible runtime approval token is missing or malformed")
    if approval.get("token_kind") != "sha256-16":
        failures.append("dry-run plan visible runtime approval token_kind is not sha256-16")
    approval_expires_utc = str(approval.get("expires_utc") or "")
    if not approval_expires_utc:
        failures.append("dry-run plan visible runtime approval expires_utc is missing")
    if int(approval.get("min_ttl_minutes") or 0) != MIN_APPROVAL_TTL_MINUTES:
        failures.append(f"dry-run plan visible runtime approval min_ttl_minutes is not {MIN_APPROVAL_TTL_MINUTES}")
    token_fields = approval.get("token_fields") or []
    if approval_expires_utc and approval_expires_utc not in token_fields:
        failures.append("dry-run plan visible runtime approval expiry is not covered by token_fields")
    failures.extend(approval_ttl_status(approval_expires_utc)["failures"])
    if "copy-exact dry-run approval packet" not in str(approval.get("purpose") or ""):
        failures.append("dry-run plan visible runtime approval purpose is missing")
    if normalized_text(plan.get("candidate_dir")) != normalized_text(r"C:\ClashTests\hd-soak"):
        failures.append("dry-run plan candidate_dir is not C:\\ClashTests\\hd-soak")
    if normalized_text(plan.get("output_root")) != normalized_text(r"C:\ClashCaptures\hd-soak"):
        failures.append("dry-run plan output_root is not C:\\ClashCaptures\\hd-soak")
    if plan.get("input_exists") is not True:
        failures.append("dry-run plan input_exe does not exist or was not confirmed readable")
    if str(plan.get("base_sha_status") or "") != "ok":
        failures.append(f"dry-run plan base_sha_status is {plan.get('base_sha_status')!r}, expected 'ok'")
    for fragment in (
        "-InputExe",
        r"C:\Clash\clash95.exe",
        "-WorkDir",
        r"C:\Clash",
        "-Stage",
        str(plan.get("protected_stable_stage") or ""),
        "-OutputRoot",
        r"C:\ClashCaptures\hd-soak",
        "-IntroSkipClickMode",
        EXPECTED_INTRO_SKIP_CLICK_MODE,
        "-IntroSkipClicks",
        str(EXPECTED_INTRO_SKIP_CLICKS),
        "-SkipPulses",
        str(EXPECTED_SKIP_PULSES),
        "-VisibleRuntimeApprovalExpiresUtc",
        approval_expires_utc,
        "-VisibleRuntimeApprovalToken",
        token,
        "-Execute",
        "-AllowVisibleRuntime",
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
    if not text_contains_path(execute_command, paths.get("report_json")):
        failures.append("dry-run plan execute command does not include the canonical report JSON path")
    if not text_contains_path(execute_command, paths.get("report_markdown")):
        failures.append("dry-run plan execute command does not include the canonical report Markdown path")
    return failures


def current_step_record(step_status: dict[str, Any]) -> dict[str, Any] | None:
    current = step_status.get("current_step") or {}
    current_id = current.get("id")
    for step in step_status.get("steps") or []:
        if step.get("id") == current_id:
            return step
    return None


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


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    sources = {
        "next_actions": args.next_actions_json,
        "step_status": args.step_status_json,
        "harness_guard": args.hd_soak_harness_guard_json,
        "dry_run_plan": args.hd_soak_dry_run_plan_json,
        "intro_skip_readiness": args.intro_skip_readiness_json,
        "visible_runtime_guard": args.visible_runtime_guard_json,
        "process_hygiene": args.process_hygiene_json,
        "exe_artifact": args.exe_artifact_json,
    }
    loaded = {name: load_json(path) for name, path in sources.items()}
    failures: list[str] = []
    for name, data in loaded.items():
        if data is None:
            failures.append(f"missing source report: {sources[name]}")

    next_actions = loaded.get("next_actions") or {}
    step_status = loaded.get("step_status") or {}
    dry_run_plan = loaded.get("dry_run_plan") or {}
    dry_run_plan_payload = dry_run_plan.get("plan") or {}
    dry_run_approval = dry_run_plan_payload.get("visible_runtime_approval") or {}
    approval_ttl = approval_ttl_status(dry_run_approval.get("expires_utc"))
    approval_limits = approval_limits_from_plan(dry_run_plan_payload, approval_ttl)
    dry_run_plan_execute_command = str(
        dry_run_plan.get("approval_gated_execute_command")
        or (dry_run_plan_payload.get("commands") or {}).get("execute")
        or ""
    )
    action = next_actions.get("next_action") or {}
    current_step = step_status.get("current_step") or {}
    step = current_step_record(step_status) or {}
    paths = step.get("paths") or {}
    runtime_command = str(current_step.get("next_command") or step.get("approval_gated_runtime_command") or "")
    approval_command = dry_run_plan_execute_command or runtime_command
    dry_run_command = str(step.get("safe_dry_run_command") or "")
    post_run_validation = post_run_validation_for_step(step) if step else []
    post_run_handoff_refresh = post_run_handoff_refresh_for_step(step) if step else []
    post_run_evidence_refresh = post_run_evidence_refresh_commands()
    artifacts = current_step_artifact_inventory(paths)
    action_artifacts = action.get("current_step_artifacts")
    current_failure = current_failure_summary(step)
    action_current_failure = action.get("current_failure")
    artifact_mismatch_keys: list[str] = []
    action_plan_mismatch_keys: list[str] = []
    approval_step_pending = current_step.get("status") in {
        "pending_approval_legacy_compat",
        "missing_pending_approval",
    }
    intro_skip_readiness = loaded.get("intro_skip_readiness") or {}
    intro_skip_rerun_ready = (
        current_step.get("status") == "failed_classified_intro_skip_input_drift_exit"
        and intro_skip_readiness.get("passed") is True
        and intro_skip_readiness.get("status") == "ready_for_explicit_visible_rerun_approval"
    )
    approval_step_ready = approval_step_pending or intro_skip_rerun_ready

    if next_actions and not next_actions.get("passed"):
        failures.append("next-actions report is not passing")
    if not step:
        failures.append(f"current short-step record is missing for {current_step.get('id')!r}")

    first_step_next_action = current_step.get("id") == EXPECTED_FIRST_STEP and action.get("id") == "run_short2_menu_idle_soak"
    if first_step_next_action:
        if next_actions.get("status") != "waiting_for_explicit_visible_runtime_approval":
            failures.append(f"next-actions status is {next_actions.get('status')!r}")

    if approval_step_ready:
        expected_action_ids = {f"run_{current_step.get('id')}_soak"}
        if intro_skip_rerun_ready:
            expected_action_ids.add(f"rerun_{current_step.get('id')}_soak")
        if action.get("id") not in expected_action_ids:
            failures.append(
                f"next-actions id is {action.get('id')!r}, expected one of {sorted(expected_action_ids)!r}"
            )
        if action.get("status") != "approval_required":
            failures.append(f"next-action status is {action.get('status')!r}, expected 'approval_required'")
        if action.get("short_step_id") not in {None, current_step.get("id")}:
            failures.append(
                f"next-action short_step_id is {action.get('short_step_id')!r}, expected {current_step.get('id')!r}"
            )
        if action.get("tier") not in {None, step.get("tier")}:
            failures.append(f"next-action tier is {action.get('tier')!r}, expected {step.get('tier')!r}")
        if action.get("route") not in {None, step.get("route")}:
            failures.append(f"next-action route is {action.get('route')!r}, expected {step.get('route')!r}")
        if action.get("requires_explicit_user_approval") is not True:
            failures.append("next action is not marked as requiring explicit user approval")
        if action.get("requires_visible_runtime") is not True:
            failures.append("next action is not marked as visible runtime")
        if action.get("exact_runtime_command") != approval_command:
            failures.append("next-actions runtime command does not match the approval command")
        action_legacy_command = action.get("legacy_step_runtime_command")
        if action_legacy_command not in {None, runtime_command}:
            failures.append("next-actions legacy step runtime command does not match step-status runtime command")
        if action.get("safe_dry_run_command") != dry_run_command:
            failures.append("next-actions dry-run command does not match step-status dry-run command")
        if action.get("post_run_validation") and action.get("post_run_validation") != post_run_validation:
            failures.append("next-actions post-run validation does not match current-step validation")
        if action.get("post_run_handoff_refresh") != post_run_handoff_refresh:
            failures.append("next-actions post-run handoff refresh does not match current-step handoff refresh")
        if action.get("post_run_evidence_refresh") != post_run_evidence_refresh:
            failures.append("next-actions post-run evidence refresh does not match current evidence refresh")
        if action.get("plan_verified_execute_command") != dry_run_plan_execute_command:
            failures.append("next-actions plan-verified execute command does not match the dry-run plan")
        if not action_artifacts:
            failures.append("next-actions current-step artifact inventory is missing")
        else:
            artifact_mismatch_keys = [
                key
                for key, value in artifacts.items()
                if action_artifacts.get(key) != value
            ]
            if artifact_mismatch_keys:
                failures.append(
                    "next-actions current-step artifact inventory does not match approval preflight: "
                    + ", ".join(artifact_mismatch_keys)
                )
        if current_failure and action_current_failure != current_failure:
            failures.append("next-actions current failure summary does not match approval preflight")
        action_plan = action.get("dry_run_plan") or {}
        if action_plan.get("current_step") != current_step.get("id"):
            failures.append("next-actions dry-run plan summary does not match the current short step")
        if normalized_text(action_plan.get("candidate_dir")) != normalized_text(r"C:\ClashTests\hd-soak"):
            failures.append("next-actions dry-run plan summary does not pin C:\\ClashTests\\hd-soak")
        if normalized_text(action_plan.get("output_root")) != normalized_text(r"C:\ClashCaptures\hd-soak"):
            failures.append("next-actions dry-run plan summary does not pin C:\\ClashCaptures\\hd-soak")
        dry_run_plan_summary = {
            "candidate_path": dry_run_plan_payload.get("candidate_path"),
            "candidate_dir": dry_run_plan_payload.get("candidate_dir"),
            "output_root": dry_run_plan_payload.get("output_root"),
            "report_json": dry_run_plan_payload.get("report_json"),
            "report_markdown": dry_run_plan_payload.get("report_markdown"),
            "input_sha256": dry_run_plan_payload.get("input_sha256"),
            "base_sha_status": dry_run_plan_payload.get("base_sha_status"),
            "execute_command": dry_run_plan_execute_command,
        }
        for key, expected in dry_run_plan_summary.items():
            actual = action_plan.get(key)
            if key in {"candidate_path", "candidate_dir", "output_root", "report_json", "report_markdown"}:
                matches = normalized_text(actual) == normalized_text(expected)
            else:
                matches = actual == expected
            if not matches:
                action_plan_mismatch_keys.append(key)
        if action_plan_mismatch_keys:
            failures.append(
                "next-actions dry-run plan summary does not match the current dry-run plan: "
                + ", ".join(action_plan_mismatch_keys)
            )

    failures.extend(command_has_required_shape(runtime_command, step, paths))
    failures.extend(dry_run_has_required_shape(dry_run_command, step, paths))
    if dry_run_plan:
        failures.extend(dry_run_plan_failures(dry_run_plan, current_step, step, paths))
    if not approval_step_ready:
        failures.append(f"current short-step status is {current_step.get('status')!r}")
    if step_status and step_status.get("ladder_complete") is True:
        failures.append("short ladder is already complete; approval preflight should not request another short soak")

    writes = set(step.get("writes_outside_repo") or action.get("writes_outside_repo") or [])
    if writes != EXPECTED_WRITES:
        failures.append(f"writes_outside_repo is {sorted(writes)!r}, expected {sorted(EXPECTED_WRITES)!r}")
    must_not_modify = step.get("must_not_modify") or action.get("must_not_modify") or []
    if MUST_NOT_MODIFY not in set(must_not_modify):
        failures.append(f"must_not_modify does not include {MUST_NOT_MODIFY}")
    if not paths.get("guard_json"):
        failures.append("current-step artifact inventory does not identify the canonical guard output")
    if not paths.get("triage_json"):
        failures.append("current-step artifact inventory does not identify the canonical triage output")
    if not post_run_validation or "hd_soak_short_validation_refresh.py" not in post_run_validation[0]:
        failures.append("post-run validation must start with the short-soak guard/triage refresh")
    if not any("hd_soak_short_validation_refresh.py" in command for command in post_run_validation):
        failures.append("post-run validation does not refresh short-soak guard/triage outputs")
    if any("hd_soak_report.py" in command and "--require-pass" in command for command in post_run_validation):
        failures.append("post-run validation must not run a direct require-pass guard before failure triage")
    if not any("hd_soak_short_step_status.py" in command for command in post_run_validation):
        failures.append("post-run validation does not refresh short-step status")
    if "git diff --check" not in post_run_validation:
        failures.append("post-run validation does not include git diff --check")
    if not any("hd_soak_dry_run_plan.py" in command for command in post_run_handoff_refresh):
        failures.append("post-run handoff refresh does not rebuild the dry-run plan")
    if not any("hd_endurance_next_actions.py" in command for command in post_run_handoff_refresh):
        failures.append("post-run handoff refresh does not rebuild next actions")
    if not any("hd_soak_approval_preflight.py" in command for command in post_run_handoff_refresh):
        failures.append("post-run handoff refresh does not rebuild approval preflight")
    if not any("current_evidence_refresh.py" in command for command in post_run_evidence_refresh):
        failures.append("post-run evidence refresh does not refresh current evidence")
    if not any("evidence_index_check.py" in command for command in post_run_evidence_refresh):
        failures.append("post-run evidence refresh does not check evidence links")

    for guard_name in (
        "harness_guard",
        "dry_run_plan",
        "visible_runtime_guard",
        "process_hygiene",
        "exe_artifact",
    ):
        report = loaded.get(guard_name) or {}
        if report and not report.get("passed"):
            failures.append(f"{guard_name} is not passing")
    if intro_skip_rerun_ready and not intro_skip_readiness.get("passed"):
        failures.append("intro-skip rerun readiness is not passing")
    if (loaded.get("process_hygiene") or {}).get("matching_process_count") not in {None, 0}:
        failures.append("process hygiene found stale cdb/clash95 processes")
    if (loaded.get("exe_artifact") or {}).get("tracked_exes"):
        failures.append("exe artifact guard reports tracked executables")

    approval_prompt = (
        f"Approve the {step_slug(step)} visible-runtime soak using the exact "
        "approval-gated command in this report. This will open a visible Clash95 game window. "
        "It will generate a patched candidate "
        r"under C:\ClashTests\hd-soak and raw frame artifacts under C:\ClashCaptures\hd-soak; "
        rf"it must not modify C:\Clash\clash95.exe, uses postmessage intro-skip harness prep "
        rf"({EXPECTED_INTRO_SKIP_CLICKS} clicks plus {EXPECTED_SKIP_PULSES} space pulses), "
        "does not treat intro skip as manual DirectInput proof, and enforces input drift <= "
        rf"{EXPECTED_MAX_INPUT_DRIFT_PX}px, frame thresholds, artifact budget, process-growth "
        "limits, and a fresh copy-exact approval token."
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "status": "ready_for_explicit_approval" if not failures else "not_ready",
        "source_artifacts": {name: str(path) for name, path in sources.items()},
        "current_step": current_step,
        "step": {
            "id": step.get("id"),
            "tier": step.get("tier"),
            "route": step.get("route"),
            "paths": paths,
        },
        "current_step_artifacts": artifacts,
        "current_failure": current_failure,
        "approval_limits": approval_limits,
        "approval_prompt": approval_prompt,
        "safe_dry_run_command": dry_run_command,
        "approval_gated_runtime_command": approval_command,
        "legacy_step_runtime_command": runtime_command,
        "post_run_validation": post_run_validation,
        "post_run_handoff_refresh": post_run_handoff_refresh,
        "post_run_evidence_refresh": post_run_evidence_refresh,
        "dry_run_plan_consistency": {
            "path": str(args.hd_soak_dry_run_plan_json),
            "passed": bool((loaded.get("dry_run_plan") or {}).get("passed")),
            "status": (loaded.get("dry_run_plan") or {}).get("status"),
            "current_step": ((loaded.get("dry_run_plan") or {}).get("current_step") or {}).get("id"),
            "candidate_path": dry_run_plan_payload.get("candidate_path"),
            "candidate_dir": dry_run_plan_payload.get("candidate_dir"),
            "output_root": dry_run_plan_payload.get("output_root"),
            "execute_command": (loaded.get("dry_run_plan") or {}).get("approval_gated_execute_command"),
            "freshness": dry_run_plan_freshness(loaded.get("dry_run_plan") or {}),
        },
        "next_action_consistency": {
            "approval_step_pending": approval_step_pending,
            "intro_skip_rerun_ready": intro_skip_rerun_ready,
            "next_action_id": action.get("id"),
            "runtime_command_matches": action.get("exact_runtime_command") == approval_command,
            "legacy_step_runtime_command_matches": action.get("legacy_step_runtime_command") in {None, runtime_command},
            "dry_run_command_matches": action.get("safe_dry_run_command") == dry_run_command,
            "post_run_validation_matches": action.get("post_run_validation") == post_run_validation,
            "post_run_handoff_refresh_matches": action.get("post_run_handoff_refresh")
            == post_run_handoff_refresh,
            "post_run_evidence_refresh_matches": action.get("post_run_evidence_refresh")
            == post_run_evidence_refresh,
            "plan_verified_execute_command_matches": action.get("plan_verified_execute_command")
            == dry_run_plan_execute_command,
            "dry_run_plan_summary_matches": not action_plan_mismatch_keys,
            "dry_run_plan_summary_mismatch_keys": action_plan_mismatch_keys,
            "current_step_artifacts_match": bool(action_artifacts) and not artifact_mismatch_keys,
            "current_step_artifact_mismatch_keys": artifact_mismatch_keys,
            "current_failure_matches": (not current_failure) or action_current_failure == current_failure,
            "approval_command_uses_dry_run_plan": approval_command == dry_run_plan_execute_command,
        },
        "writes_outside_repo": sorted(writes),
        "must_not_modify": must_not_modify,
        "guards": {
            "harness_guard_passed": bool((loaded.get("harness_guard") or {}).get("passed")),
            "dry_run_plan_passed": bool((loaded.get("dry_run_plan") or {}).get("passed")),
            "visible_runtime_guard_passed": bool((loaded.get("visible_runtime_guard") or {}).get("passed")),
            "process_hygiene_passed": bool((loaded.get("process_hygiene") or {}).get("passed")),
            "exe_artifact_guard_passed": bool((loaded.get("exe_artifact") or {}).get("passed")),
        },
        "locks": {
            "stable_stage_should_change": False,
            "right_bottom_promotion_blocked": True,
            "long_tiers_locked": True,
            "future_lanes_locked": True,
        },
        "failures": failures,
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# HD Soak Approval Preflight",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Status: `{report['status']}`",
        f"- Current step: `{(report.get('current_step') or {}).get('id')}`",
        f"- Current step status: `{(report.get('current_step') or {}).get('status')}`",
        f"- Canonical runtime report missing: `{(report.get('current_step_artifacts') or {}).get('canonical_runtime_report_missing')}`",
        f"- Stable stage should change: `{report['locks']['stable_stage_should_change']}`",
        f"- Right-bottom promotion blocked: `{report['locks']['right_bottom_promotion_blocked']}`",
        "",
        "## Current Step Artifacts",
        "",
        f"- Report JSON: `{(report.get('current_step_artifacts') or {}).get('report_json')}` exists=`{(report.get('current_step_artifacts') or {}).get('report_json_exists')}`",
        f"- Guard JSON: `{(report.get('current_step_artifacts') or {}).get('guard_json')}` exists=`{(report.get('current_step_artifacts') or {}).get('guard_json_exists')}`",
        f"- Triage JSON: `{(report.get('current_step_artifacts') or {}).get('triage_json')}` exists=`{(report.get('current_step_artifacts') or {}).get('triage_json_exists')}`",
        "",
        "## Approval Prompt",
        "",
        report["approval_prompt"],
        "",
    ]
    current_failure = report.get("current_failure") or {}
    if current_failure:
        lines.extend(
            [
                "## Current Failure",
                "",
                f"- Classification: `{current_failure.get('classification')}`",
                f"- Next probe: {current_failure.get('next_probe')}",
                f"- Final route marker: `{current_failure.get('final_route_marker')}`",
                f"- Candidate SHA-256: `{current_failure.get('candidate_sha256')}`",
                f"- Visual anomaly passed: `{current_failure.get('visual_anomaly_passed')}`",
                f"- Black/blank patch risk count: `{current_failure.get('black_patch_risk_count')}`",
                f"- Palette/stripe risk count: `{current_failure.get('palette_or_stripe_risk_count')}`",
                f"- Missing nonblack bounds count: `{current_failure.get('missing_nonblack_bounds_count')}`",
                "",
            ]
        )
    lines.extend(["## Approval Limits", ""])
    limits = report.get("approval_limits") or {}
    for key in (
        "sample_interval_sec",
        "max_input_drift_px",
        "min_nonblack_percent",
        "min_unique_sample_colors",
        "max_artifact_mb",
        "max_working_set_growth_mb",
        "max_private_memory_growth_mb",
        "max_handle_growth",
        "approval_token_kind",
        "approval_expires_utc",
        "approval_remaining_seconds",
        "min_approval_ttl_minutes",
    ):
        lines.append(f"- {key}: `{limits.get(key)}`")
    lines.extend(
        [
            "",
            "## Safe Dry Run",
            "",
            "```powershell",
            report["safe_dry_run_command"],
            "```",
            "",
            "## Approval-Gated Runtime Command",
            "",
            "```powershell",
            report["approval_gated_runtime_command"],
            "```",
            "",
            "## Dry-Run Plan",
            "",
            f"- Plan: `{(report.get('dry_run_plan_consistency') or {}).get('path')}`",
            f"- Status: `{(report.get('dry_run_plan_consistency') or {}).get('status')}`",
            f"- Current step: `{(report.get('dry_run_plan_consistency') or {}).get('current_step')}`",
            f"- Candidate path: `{(report.get('dry_run_plan_consistency') or {}).get('candidate_path')}`",
            f"- Passing: `{(report.get('dry_run_plan_consistency') or {}).get('passed')}`",
            f"- Freshness passing: `{((report.get('dry_run_plan_consistency') or {}).get('freshness') or {}).get('passed')}`",
            f"- Max age hours: `{((report.get('dry_run_plan_consistency') or {}).get('freshness') or {}).get('max_age_hours')}`",
            "",
            "Plan-emitted execute command:",
            "",
            "```powershell",
            str((report.get("dry_run_plan_consistency") or {}).get("execute_command") or ""),
            "```",
            "",
            "## Focused Post-Run Validation",
            "",
        ]
    )
    for command in report.get("post_run_validation") or []:
        lines.append(f"- `{command}`")
    if report.get("post_run_handoff_refresh"):
        lines.extend(["", "## Post-Run Handoff Refresh", ""])
        for command in report.get("post_run_handoff_refresh") or []:
            lines.append(f"- `{command}`")
    if report.get("post_run_evidence_refresh"):
        lines.extend(["", "## Broad Evidence Refresh", ""])
        for command in report.get("post_run_evidence_refresh") or []:
            lines.append(f"- `{command}`")
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
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
    parser.add_argument("--next-actions-json", type=Path, default=DEFAULT_NEXT_ACTIONS_JSON)
    parser.add_argument("--step-status-json", type=Path, default=DEFAULT_STEP_STATUS_JSON)
    parser.add_argument("--hd-soak-harness-guard-json", type=Path, default=DEFAULT_HARNESS_GUARD_JSON)
    parser.add_argument("--hd-soak-dry-run-plan-json", type=Path, default=DEFAULT_DRY_RUN_PLAN_JSON)
    parser.add_argument("--intro-skip-readiness-json", type=Path, default=DEFAULT_INTRO_SKIP_READINESS_JSON)
    parser.add_argument("--visible-runtime-guard-json", type=Path, default=DEFAULT_VISIBLE_RUNTIME_GUARD_JSON)
    parser.add_argument("--process-hygiene-json", type=Path, default=DEFAULT_PROCESS_HYGIENE_JSON)
    parser.add_argument("--exe-artifact-json", type=Path, default=DEFAULT_EXE_ARTIFACT_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    report = build_report(args)
    write_outputs(report, args.write_json, args.write_markdown)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"status: {report.get('status')}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
