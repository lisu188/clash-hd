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
DEFAULT_JSON = Path("captures/current/hd-endurance-next-actions-current.json")
DEFAULT_MD = Path("captures/current/hd-endurance-next-actions-current.md")
RUNTIME_POLICY = (
    "repo-only endurance next-action triage; does not launch Clash95, CDB, "
    "wrappers, PowerShell harnesses, or visible windows"
)
MAX_INPUT_DRIFT_PX = 1
MAX_DRY_RUN_PLAN_AGE_HOURS = 12


VISIBLE_SHORT2_COMMAND = (
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
    ".\\scripts\\smoke\\run_hd_soak.ps1 "
    "-Tier short2 -Route menu-idle "
    "-ReportJson captures\\current\\hd-soak-short2-menu-idle-current.json "
    "-ReportMarkdown captures\\current\\hd-soak-short2-menu-idle-current.md "
    f"-MaxInputDriftPx {MAX_INPUT_DRIFT_PX} "
    "-Execute -AllowVisibleRuntime -RequirePass -Json"
)
DRY_RUN_SHORT2_COMMAND = (
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
    ".\\scripts\\smoke\\run_hd_soak.ps1 -Tier short2 -Route menu-idle "
    "-ReportJson captures\\current\\hd-soak-short2-menu-idle-current.json "
    "-ReportMarkdown captures\\current\\hd-soak-short2-menu-idle-current.md "
    f"-MaxInputDriftPx {MAX_INPUT_DRIFT_PX} -Json"
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
    for fragment in ("-Execute", "-AllowVisibleRuntime", "-RequirePass", "-Json", "-MaxInputDriftPx"):
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
        "execute_command": execute_command,
        "freshness": freshness,
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

    if status in {"pending_approval_legacy_compat", "missing_pending_approval"}:
        legacy_command = str(current.get("next_command") or step.get("approval_gated_runtime_command") or "")
        plan_summary, plan_failures = dry_run_plan_for_step(dry_run_plan, step)
        plan_command = (plan_summary or {}).get("execute_command")
        command = str(plan_command or legacy_command)
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
            "exact_runtime_command_source": "dry_run_plan" if plan_command else "step_status",
            "legacy_step_runtime_command": legacy_command if command != legacy_command else None,
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
        }
        return {
            "id": "run_short2_menu_idle_soak",
            "status": "approval_required",
            "requires_visible_runtime": True,
            "requires_explicit_user_approval": True,
            "why": (
                "The release checklist cannot progress until one protected-stage "
                "short2 menu-idle soak produces frame/process evidence."
            ),
            "exact_runtime_command": VISIBLE_SHORT2_COMMAND,
            "safe_dry_run_command": DRY_RUN_SHORT2_COMMAND,
            "writes_outside_repo": [
                r"C:\ClashTests\hd-soak",
                r"C:\ClashCaptures\hd-soak",
            ],
            "must_not_modify": [r"C:\Clash\clash95.exe"],
            "current_step_artifacts": current_step_artifact_inventory(step),
            "post_run_validation": post_run_validation_for_step(step),
            "post_run_handoff_refresh": post_run_handoff_refresh_for_step(step),
            "post_run_evidence_refresh": post_run_evidence_refresh_commands(),
        }
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
    step_status = load_json(short_step_status_path)
    dry_run_plan = load_json(dry_run_plan_path) if dry_run_plan_path and dry_run_plan_path.exists() else None
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
    short_step_action, short_step_failures = next_action_for_short_step(step_status, dry_run_plan)
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
        if action.get("legacy_step_runtime_command"):
            lines.extend(
                [
                    "",
                    "Legacy step-status runtime command:",
                    "",
                    "```powershell",
                    action["legacy_step_runtime_command"],
                    "```",
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
