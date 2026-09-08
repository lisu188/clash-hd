#!/usr/bin/env python3
"""Gate that the classified intro-skip failure was rerun and the ladder advanced.

The short2 menu-idle rerun passed on 2026-07-12 (approved visible runtime), so
this gate now asserts the passing-triage state and that the ladder advanced to
the approval-gated short2 map-idle step.

This is repo-only. It reads the failed short2 menu-idle triage plus current
harness/dry-run/guard reports and does not launch Clash95, CDB, wrappers,
PowerShell harnesses, or visible windows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import hd_soak_report
import hd_soak_short_step_status
from hd_soak_short_tier_ladder import SHORT_LADDER_STEPS


DEFAULT_TRIAGE_JSON = Path("captures/current/hd-soak-short2-menu-idle-triage-current.json")
DEFAULT_STEP_STATUS_JSON = Path("captures/current/hd-soak-short-step-status-current.json")
DEFAULT_HARNESS_GUARD_JSON = Path("captures/current/hd-soak-harness-guard-current.json")
DEFAULT_DRY_RUN_PLAN_JSON = Path("captures/current/hd-soak-dry-run-plan-current.json")
DEFAULT_VISIBLE_RUNTIME_GUARD_JSON = Path("captures/current/visible-runtime-launcher-guard-current.json")
DEFAULT_PROCESS_HYGIENE_JSON = Path("captures/current/process-hygiene-guard-current.json")
DEFAULT_EXE_ARTIFACT_JSON = Path("captures/current/exe-artifact-guard-current.json")
DEFAULT_JSON = Path("captures/current/hd-soak-intro-skip-rerun-readiness-current.json")
DEFAULT_MD = Path("captures/current/hd-soak-intro-skip-rerun-readiness-current.md")

RUNTIME_POLICY = (
    "repo-only intro-skip rerun readiness gate; does not launch Clash95, CDB, "
    "wrappers, PowerShell harnesses, or visible windows"
)
EXPECTED_CLASSIFICATION = "passing_run_no_failure"
EXPECTED_STEP_ID = "short2_map_idle"
EXPECTED_STEP_STATUS = "missing_pending_approval"
# A classified environmental failure (locked session, WER hang close, hidden
# window, intro-skip drift exit) does not invalidate rerun readiness -- the
# packet stays ready for the next unlocked attempt. The enumeration mirrors
# hd_soak_approval_preflight's rerun-readiness handling; any OTHER classified
# failure (e.g. unexpected_process_exit) keeps the report valid but marks the
# packet not applicable so no rerun is authorized on top of an unexplained
# failure.
ACCEPTED_STEP_STATUSES = {EXPECTED_STEP_STATUS, "pending_approval_legacy_compat"}
CLASSIFIED_FAILURE_PREFIX = "failed_classified_"
RERUN_READY_CLASSIFIED_STATUSES = {
    "failed_classified_intro_skip_input_drift_exit",
    "failed_classified_input_environment_permission_denied",
    "failed_classified_application_hang_wer_closed",
    "failed_classified_window_missing_while_process_alive",
}
EXPECTED_STEP_STATUSES = ACCEPTED_STEP_STATUSES | RERUN_READY_CLASSIFIED_STATUSES
EXPECTED_INTRO_SKIP = {
    "click_mode": "postmessage",
    "click_repeat": 8,
    "space_pulses": 4,
    # The harness stops repeating intro-skip clicks the moment input drift is
    # detected (the contract hd_soak_approval_preflight enforces on the real
    # dry-run plan); the readiness packet documents the same contract.
    "stop_click_repeat_on_drift": True,
    "proof_class": "intro_skip_harness_prep_not_manual_directinput_release_proof",
}
ORDERED_STEP_IDS = ("short2_menu_idle", "short2_map_idle", "short10_map_idle", "short10_map_pan", "short30_map_pan")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def command_contains_intro_contract(command: str) -> list[str]:
    failures: list[str] = []
    for fragment in (
        "-IntroSkipClickMode",
        "postmessage",
        "-IntroSkipClicks",
        "8",
        "-SkipPulses",
        "4",
        "-SampleIntervalSec",
        "15",
        "-MaxInputDriftPx",
        "1",
        "-MinNonblackPercent",
        "10",
        "-MinUniqueSampleColors",
        "8",
        "-MaxArtifactMB",
        "250",
        "-MaxWorkingSetGrowthMB",
        "64",
        "-MaxPrivateMemoryGrowthMB",
        "64",
        "-MaxHandleGrowth",
        "128",
        "-VisibleRuntimeApprovalExpiresUtc",
        "-VisibleRuntimeApprovalToken",
        "-Execute",
        "-AllowVisibleRuntime",
        "-RequirePass",
        "-Json",
    ):
        if fragment not in command:
            failures.append(f"approval command missing fragment: {fragment}")
    return failures


def intro_skip_failures(plan: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    intro = plan.get("intro_skip") or {}
    for key, expected in EXPECTED_INTRO_SKIP.items():
        if intro.get(key) != expected:
            failures.append(f"dry-run intro_skip {key} is {intro.get(key)!r}, expected {expected!r}")
    return failures


def prior_step_evidence(step_status: dict[str, Any], *, completed: bool = False) -> tuple[list[dict[str, Any]], list[str]]:
    """Verify canonical executed predecessors before treating intro readiness as historical."""
    failures: list[str] = []
    evidence: list[dict[str, Any]] = []
    current = step_status.get("current_step")
    current_id = current.get("id") if isinstance(current, dict) else None
    if not completed and current_id not in ORDERED_STEP_IDS[1:]:
        return evidence, ["current step is not a known later short-ladder step"]
    if step_status.get("passed") is not True:
        failures.append("short-step status is not passing")
    records = step_status.get("steps") or []
    if (not isinstance(records, list) or not all(isinstance(row, dict) for row in records)
            or [row.get("id") for row in records] != list(ORDERED_STEP_IDS)):
        return evidence, failures + ["short-step status does not contain the exact ordered five-step ladder"]
    current_index = len(records) if completed else ORDERED_STEP_IDS.index(current_id)
    if completed:
        if step_status.get("ladder_complete") is not True or "current_step" not in step_status or current is not None:
            failures.append("completed short ladder requires ladder_complete=true and explicit current_step=null")
        if step_status.get("protected_stable_stage") != hd_soak_short_step_status.PROTECTED_STABLE_STAGE:
            failures.append("completed short ladder does not identify the protected stable stage")
        if step_status.get("failures") != []:
            failures.append("completed short ladder must have an empty failures list")
        counts = step_status.get("counts") or {}
        expected_counts = {"total": 5, "passed": 5, "pending_or_missing": 0, "locked": 0, "failed_or_invalid": 0}
        if not isinstance(counts, dict) or any(type(counts.get(key)) is not int or counts[key] != value for key, value in expected_counts.items()):
            failures.append("completed short ladder counts do not describe exactly five passing steps")
    elif records[current_index].get("prerequisites_passed") is not True:
        failures.append("current step prerequisites have not passed")
    seen_paths: set[str] = set()
    for index, row in enumerate(records[:current_index]):
        step_id = row["id"]
        if completed:
            definition = SHORT_LADDER_STEPS[index]
            for key in ("tier", "route", "duration_sec", "prerequisites"):
                if row.get(key) != definition[key]:
                    failures.append(f"completed step {step_id} {key} differs from the canonical ladder")
            if row.get("prerequisites_passed") is not True:
                failures.append(f"completed step {step_id} prerequisites have not passed")
        if row.get("passed") is not True or row.get("status") != "pass":
            failures.append(f"predecessor {step_id} is not a passing step")
        paths = row.get("paths") or {}
        if not isinstance(paths, dict):
            failures.append(f"predecessor {step_id} artifact paths are invalid")
            continue
        source_path = Path(str(paths.get("report_json") or "").replace("\\", "/"))
        guard_path = Path(str(paths.get("guard_json") or "").replace("\\", "/"))
        try:
            source_bytes = source_path.read_bytes() if paths.get("report_json") else b""
            guard_bytes = guard_path.read_bytes() if paths.get("guard_json") else b""
            source = json.loads(source_bytes.decode("utf-8-sig")) if source_bytes else None
            guard = json.loads(guard_bytes.decode("utf-8-sig")) if guard_bytes else None
        except (OSError, UnicodeError, json.JSONDecodeError):
            source, guard = None, None
        if not isinstance(source, dict) or not isinstance(guard, dict):
            failures.append(f"predecessor {step_id} canonical report/guard is missing or unreadable")
            continue
        if completed:
            for path in (source_path, guard_path):
                identity = hd_soak_short_step_status.normalized_path_text(path.resolve())
                if identity in seen_paths:
                    failures.append(f"completed step {step_id} reuses another report/guard artifact")
                seen_paths.add(identity)
            declared_source = Path(str(source.get("report_json") or "").replace("\\", "/")).resolve()
            if hd_soak_short_step_status.normalized_path_text(declared_source) != hd_soak_short_step_status.normalized_path_text(source_path.resolve()):
                # Hidden runners preserve their immutable raw-run report path
                # when publishing the byte-identical canonical current copy.
                # Authenticate that copy rather than rewriting its provenance.
                try:
                    if declared_source.read_bytes() != source_bytes:
                        failures.append(f"completed step {step_id} canonical copy differs from its declared source report_json")
                except OSError:
                    failures.append(f"completed step {step_id} declared source report_json is missing or unreadable")
            if source.get("duration_sec") != SHORT_LADDER_STEPS[index]["duration_sec"] or guard.get("duration_sec") != source.get("duration_sec"):
                failures.append(f"completed step {step_id} report/guard duration does not match the canonical tier")
            if source.get("failures") != [] or guard.get("failures") != []:
                failures.append(f"completed step {step_id} report/guard retains failures")
            # Recompute the existing environment-specific guard from actual
            # source metrics and patch evidence; cached affirmative flags alone
            # cannot establish completion or hide a subsequently changed source.
            try:
                evaluation = hd_soak_report.evaluate_report_for_environment(source)
                if evaluation.get("overall") is not True:
                    failures.extend(f"completed step {step_id} source recheck: {failure}" for failure in evaluation.get("failures") or ["not passing"])
                guard_checks = guard.get("checks")
                if not isinstance(guard_checks, dict) or any(
                    not isinstance(guard_checks.get(name), dict) or guard_checks[name].get("passed") is not True
                    for name in evaluation.get("checks") or {}
                ):
                    failures.append(f"completed step {step_id} saved guard omits or fails required source checks")
            except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
                failures.append(f"completed step {step_id} source could not be rechecked: {exc}")
        if source.get("executed") is not True or source.get("passed") is not True:
            failures.append(f"predecessor {step_id} source is not an executed passing run")
        if not hd_soak_short_step_status.matches_step(source, row):
            failures.append(f"predecessor {step_id} source stage/route/environment does not match")
        if guard.get("overall") is not True:
            failures.append(f"predecessor {step_id} guard is not passing")
        failures.extend(hd_soak_short_step_status.artifact_mismatch_failures(guard, row, source_path, "guard", source))
        checks = guard.get("checks") or {}
        if not isinstance(checks, dict) or any(not isinstance(value, dict) for value in checks.values()):
            failures.append(f"predecessor {step_id} guard checks are malformed")
            continue
        for name in ("executed", "source_status", "protected_stage", "patch_evidence", "promotion_boundary"):
            if (checks.get(name) or {}).get("passed") is not True:
                failures.append(f"predecessor {step_id} guard check {name} is not passing")
        candidate_sha = str(source.get("candidate_sha256") or "").lower()
        patch_summary = (checks.get("patch_evidence") or {}).get("summary")
        guard_sha = str((patch_summary if isinstance(patch_summary, dict) else {}).get("candidate_sha256") or "").lower()
        if not hd_soak_report.is_sha256(candidate_sha) or candidate_sha != guard_sha:
            failures.append(f"predecessor {step_id} candidate SHA does not match guard provenance")
        if step_id == ORDERED_STEP_IDS[0] and (
            source.get("environment", "host_visible") != "host_visible" or source.get("final_route_marker") != "intro-skip"
        ):
            failures.append("menu predecessor does not prove the visible-host intro-skip route")
        evidence.append({"id": step_id, "report": str(source_path), "guard": str(guard_path), "candidate_sha256": candidate_sha,
                         "declared_source_report": source.get("report_json"),
                         "environment": hd_soak_short_step_status.evidence_binding(source)[0],
                         "report_sha256": hashlib.sha256(source_bytes).hexdigest(),
                         "guard_sha256": hashlib.sha256(guard_bytes).hexdigest()})
    return evidence, failures


def short_ladder_terminal_claim(step_status: dict[str, Any]) -> bool:
    return bool(step_status.get("ladder_complete")) or ("current_step" in step_status and step_status["current_step"] is None)


def completed_short_ladder_report(step_status: dict[str, Any], source: Path, runtime_policy: str) -> dict[str, Any]:
    evidence, failures = prior_step_evidence(step_status, completed=True)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(), "passed": not failures,
        "status": "not_applicable_short_ladder_complete" if not failures else "invalid_short_ladder_completion",
        "terminal_short_ladder": True, "ladder_complete_verified": not failures,
        "runtime_policy": runtime_policy, "source_artifacts": {"step_status_json": str(source)},
        "current_step": None, "completed_predecessor_evidence": evidence,
        "runtime_authorized": False, "approval_required": False, "approved": False,
        "promotion_ready": False, "manual_input_proof": False,
        "safe_dry_run_command": None, "approval_gated_execute_command": None,
        "hidden_runtime_command": None, "recommended_runtime_command": None,
        "exact_runtime_command": None, "post_run_validation": [], "commands": {},
        "plan": {}, "dry_run_plan": {"approval_gated_execute_command": None},
        "invocation": {"command": None, "exit_code": None, "executed": False},
        "approval_boundary": "This terminal short-ladder status authorizes no runtime or approval request. Long-soak, manual-input and promotion evidence require their separate gates.",
        "remaining_requirements": ["long-soak evidence", "manual-input proof and required visible approval", "explicit promotion decision"],
        "locks": {"stable_stage_should_change": False, "right_bottom_promotion_blocked": True,
                  "long_tiers_locked": bool(failures), "future_lanes_locked": True},
        "failures": failures,
    }


def completed_short_ladder_markdown(report: dict[str, Any], title: str) -> str:
    lines = [f"# {title}", "", f"- Overall: {status_text(report['passed'])}",
             f"- Status: `{report['status']}`", f"- Evidence records reloaded: `{len(report['completed_predecessor_evidence'])}`",
             "", report["approval_boundary"], "", "## Separate Requirements", ""]
    lines.extend(f"- {item}" for item in report["remaining_requirements"])
    if report["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    return "\n".join(lines) + "\n"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    sources = {
        "triage": args.triage_json,
        "step_status": args.step_status_json,
        "harness_guard": args.harness_guard_json,
        "dry_run_plan": args.dry_run_plan_json,
        "visible_runtime_guard": args.visible_runtime_guard_json,
        "process_hygiene": args.process_hygiene_json,
        "exe_artifact": args.exe_artifact_json,
    }
    step_status_data = load_json(args.step_status_json) or {}
    if short_ladder_terminal_claim(step_status_data):
        return completed_short_ladder_report(step_status_data, args.step_status_json, RUNTIME_POLICY)
    loaded = {name: step_status_data if name == "step_status" else load_json(path) for name, path in sources.items()}
    current_data = step_status_data.get("current_step") or {}
    current_id = current_data.get("id")
    historical = current_id in ORDERED_STEP_IDS[2:] or (
        current_id == EXPECTED_STEP_ID and current_data.get("preferred_environment") == "hidden_cdb_host"
    )
    if historical:
        evidence, failures = prior_step_evidence(step_status_data)
        triage = loaded.get("triage") or {}
        if triage.get("classification") != EXPECTED_CLASSIFICATION or triage.get("executed") is not True or triage.get("final_route_marker") != "intro-skip":
            failures.append("historical intro triage does not record an executed passing intro-skip run")
        if evidence and str(triage.get("candidate_sha256") or "").lower() != evidence[0]["candidate_sha256"]:
            failures.append("historical intro triage candidate SHA does not match canonical menu proof")
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(), "passed": not failures,
            "runtime_policy": RUNTIME_POLICY, "status": "not_applicable_later_step" if not failures else "not_ready",
            "source_artifacts": {name: str(sources[name]) for name in ("triage", "step_status")},
            "current_step": current_data, "completed_predecessor_evidence": evidence,
            "triage": {"classification": triage.get("classification"), "candidate_sha256": triage.get("candidate_sha256")},
            "intro_skip_contract": EXPECTED_INTRO_SKIP,
            "dry_run_plan": {"approval_gated_execute_command": None},
            "approval_boundary": "Historical intro-skip proof is complete. This status authorizes no runtime; follow the current environment-specific preflight.",
            "failures": failures,
        }
    failures: list[str] = []
    for name, data in loaded.items():
        if data is None:
            failures.append(f"missing source report: {sources[name]}")

    triage = loaded.get("triage") or {}
    step_status = loaded.get("step_status") or {}
    harness_guard = loaded.get("harness_guard") or {}
    dry_run_plan = loaded.get("dry_run_plan") or {}
    visible_runtime_guard = loaded.get("visible_runtime_guard") or {}
    process_hygiene = loaded.get("process_hygiene") or {}
    exe_artifact = loaded.get("exe_artifact") or {}
    plan = dry_run_plan.get("plan") or {}
    current_step = step_status.get("current_step") or {}
    dry_run_step = dry_run_plan.get("current_step") or {}
    command = str(dry_run_plan.get("approval_gated_execute_command") or (plan.get("commands") or {}).get("execute") or "")
    current_step_status = str(current_step.get("status") or "")
    not_applicable_current_failure = (
        current_step.get("id") == EXPECTED_STEP_ID
        and current_step_status.startswith(CLASSIFIED_FAILURE_PREFIX)
        and current_step_status not in RERUN_READY_CLASSIFIED_STATUSES
    )

    if triage.get("classification") != EXPECTED_CLASSIFICATION:
        failures.append(f"triage classification is {triage.get('classification')!r}, expected {EXPECTED_CLASSIFICATION!r}")
    if triage.get("final_route_marker") != "intro-skip":
        failures.append("triage final route marker is not intro-skip")
    if triage.get("executed") is not True:
        failures.append("triage source report was not an executed runtime run")

    if current_step.get("id") != EXPECTED_STEP_ID:
        failures.append(f"current short step is {current_step.get('id')!r}, expected {EXPECTED_STEP_ID!r}")
    if current_step.get("status") not in EXPECTED_STEP_STATUSES and not not_applicable_current_failure:
        failures.append(
            f"current short step status is {current_step.get('status')!r}, "
            f"expected one of {sorted(EXPECTED_STEP_STATUSES)!r}"
        )

    if harness_guard.get("passed") is not True:
        failures.append("harness guard is not passing")
    checks = harness_guard.get("checks") or {}
    for check_name in (
        "intro_skip_policy",
        "visible_runtime_opt_in",
        "windowed_mode",
        "protected_stage_boundary",
    ):
        if (checks.get(check_name) or {}).get("passed") is not True:
            failures.append(f"harness guard check is not passing: {check_name}")

    if dry_run_plan.get("passed") is not True:
        failures.append("dry-run plan is not passing")
    if dry_run_plan.get("status") != "ready_for_explicit_approval":
        failures.append(f"dry-run plan status is {dry_run_plan.get('status')!r}")
    if dry_run_step.get("id") != EXPECTED_STEP_ID:
        failures.append(f"dry-run plan current step is {dry_run_step.get('id')!r}, expected {EXPECTED_STEP_ID!r}")
    if plan.get("stable_stage_should_change") is not False:
        failures.append("dry-run plan would change the stable stage")
    if plan.get("right_bottom_promotion_blocked") is not True:
        failures.append("dry-run plan does not keep right-bottom promotion blocked")
    failures.extend(intro_skip_failures(plan))
    failures.extend(command_contains_intro_contract(command))
    approval = plan.get("visible_runtime_approval") or {}
    token = str(approval.get("token") or "")
    if len(token) != 16 or not all(ch in "0123456789abcdef" for ch in token):
        failures.append("dry-run visible runtime approval token is missing or malformed")
    if token and token not in command:
        failures.append("approval command does not include the dry-run visible runtime approval token")
    approval_expires_utc = str(approval.get("expires_utc") or "")
    if not approval_expires_utc:
        failures.append("dry-run visible runtime approval expires_utc is missing")
    elif approval_expires_utc not in command:
        failures.append("approval command does not include the dry-run visible runtime approval expiry")
    token_fields = approval.get("token_fields") or []
    if approval_expires_utc and approval_expires_utc not in token_fields:
        failures.append("dry-run visible runtime approval expiry is not covered by token_fields")

    if visible_runtime_guard.get("passed") is not True:
        failures.append("visible runtime launcher guard is not passing")
    if process_hygiene.get("passed") is not True:
        failures.append("process hygiene guard is not passing")
    if process_hygiene.get("matching_process_count") not in {None, 0}:
        failures.append("process hygiene reports stale cdb/clash95 processes")
    if exe_artifact.get("passed") is not True:
        failures.append("exe artifact guard is not passing")
    if exe_artifact.get("tracked_exes"):
        failures.append("exe artifact guard reports tracked executables")

    if failures:
        status = "not_ready"
    elif not_applicable_current_failure:
        status = "not_applicable_current_failure"
    else:
        status = "ready_for_explicit_visible_rerun_approval"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "status": status,
        "source_artifacts": {name: str(path) for name, path in sources.items()},
        "triage": {
            "classification": triage.get("classification"),
            "final_route_marker": triage.get("final_route_marker"),
            "candidate_sha256": triage.get("candidate_sha256"),
            "next_probe": triage.get("next_probe"),
        },
        "current_step": {
            "id": current_step.get("id"),
            "status": current_step.get("status"),
        },
        "intro_skip_contract": EXPECTED_INTRO_SKIP,
        "dry_run_plan": {
            "passed": dry_run_plan.get("passed"),
            "status": dry_run_plan.get("status"),
            "current_step": dry_run_step.get("id"),
            "candidate_path": plan.get("candidate_path"),
            "output_root": plan.get("output_root"),
            "approval_gated_execute_command": command,
        },
        "guards": {
            "harness_guard_passed": bool(harness_guard.get("passed")),
            "visible_runtime_guard_passed": bool(visible_runtime_guard.get("passed")),
            "process_hygiene_passed": bool(process_hygiene.get("passed")),
            "exe_artifact_guard_passed": bool(exe_artifact.get("passed")),
        },
        "approval_boundary": (
            "No intro-skip rerun is authorized while the current step has an unrelated "
            "classified failure; follow its repo-only triage instead."
            if not_applicable_current_failure
            else "The next runtime run will open a visible Clash95 game window and still "
            "requires explicit user approval."
        ),
        "failures": failures,
    }


def to_markdown(report: dict[str, Any]) -> str:
    if report.get("terminal_short_ladder"):
        return completed_short_ladder_markdown(report, "HD Soak Intro-Skip Rerun Readiness")
    triage = report.get("triage") or {}
    dry_run = report.get("dry_run_plan") or {}
    lines = [
        "# HD Soak Intro-Skip Rerun Readiness",
        "",
        f"- Overall: {status_text(bool(report.get('passed')))}",
        f"- Generated: `{report.get('generated_at')}`",
        f"- Runtime policy: {report.get('runtime_policy')}",
        f"- Status: `{report.get('status')}`",
        f"- Triage classification: `{triage.get('classification')}`",
        f"- Current step: `{(report.get('current_step') or {}).get('id')}` status=`{(report.get('current_step') or {}).get('status')}`",
        f"- Approval boundary: {report.get('approval_boundary')}",
        "",
        "## Intro-Skip Contract",
        "",
    ]
    for key, value in (report.get("intro_skip_contract") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Approval-Gated Runtime Command",
            "",
            "```powershell",
            str(dry_run.get("approval_gated_execute_command") or ""),
            "```",
        ]
    )
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
    parser.add_argument("--triage-json", type=Path, default=DEFAULT_TRIAGE_JSON)
    parser.add_argument("--step-status-json", type=Path, default=DEFAULT_STEP_STATUS_JSON)
    parser.add_argument("--harness-guard-json", type=Path, default=DEFAULT_HARNESS_GUARD_JSON)
    parser.add_argument("--dry-run-plan-json", type=Path, default=DEFAULT_DRY_RUN_PLAN_JSON)
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
    print(f"status: {report['status']}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
