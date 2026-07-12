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
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
EXPECTED_INTRO_SKIP = {
    "click_mode": "postmessage",
    "click_repeat": 8,
    "space_pulses": 4,
    "proof_class": "intro_skip_harness_prep_not_manual_directinput_release_proof",
}


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
    loaded = {name: load_json(path) for name, path in sources.items()}
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

    if triage.get("classification") != EXPECTED_CLASSIFICATION:
        failures.append(f"triage classification is {triage.get('classification')!r}, expected {EXPECTED_CLASSIFICATION!r}")
    if triage.get("final_route_marker") != "intro-skip":
        failures.append("triage final route marker is not intro-skip")
    if triage.get("executed") is not True:
        failures.append("triage source report was not an executed runtime run")

    if current_step.get("id") != EXPECTED_STEP_ID:
        failures.append(f"current short step is {current_step.get('id')!r}, expected {EXPECTED_STEP_ID!r}")
    if current_step.get("status") != EXPECTED_STEP_STATUS:
        failures.append(f"current short step status is {current_step.get('status')!r}, expected {EXPECTED_STEP_STATUS!r}")

    if harness_guard.get("passed") is not True:
        failures.append("harness guard is not passing")
    checks = harness_guard.get("checks") or {}
    for check_name in ("intro_skip_policy", "visible_runtime_opt_in", "protected_stage_boundary"):
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

    status = "ready_for_explicit_visible_rerun_approval" if not failures else "not_ready"
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
            "The next runtime run will open a visible Clash95 game window and still "
            "requires explicit user approval."
        ),
        "failures": failures,
    }


def to_markdown(report: dict[str, Any]) -> str:
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
