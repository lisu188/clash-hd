#!/usr/bin/env python3
"""Build the approval preflight packet for the first short HD soak.

This report is repo-only. It does not launch the game. It verifies that the
next visible-runtime command is canonical, approval-gated, non-promoting, and
paired with post-run validation before asking for explicit approval.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNTIME_POLICY = (
    "repo-only visible-runtime approval preflight; does not launch Clash95, CDB, "
    "wrappers, PowerShell harnesses, or visible windows"
)
DEFAULT_NEXT_ACTIONS_JSON = Path("captures/current/hd-endurance-next-actions-current.json")
DEFAULT_STEP_STATUS_JSON = Path("captures/current/hd-soak-short-step-status-current.json")
DEFAULT_HARNESS_GUARD_JSON = Path("captures/current/hd-soak-harness-guard-current.json")
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


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def command_has_required_shape(command: str) -> list[str]:
    failures: list[str] = []
    required_fragments = [
        r".\scripts\smoke\run_hd_soak.ps1",
        "-Tier short2",
        "-Route menu-idle",
        f"-ReportJson {EXPECTED_REPORT_JSON}",
        f"-ReportMarkdown {EXPECTED_REPORT_MD}",
        "-Execute -AllowVisibleRuntime -RequirePass",
        "-Json",
    ]
    for fragment in required_fragments:
        if fragment not in command:
            failures.append(f"runtime command missing fragment: {fragment}")
    return failures


def dry_run_has_required_shape(command: str) -> list[str]:
    failures: list[str] = []
    if "-Execute" in command or "-AllowVisibleRuntime" in command:
        failures.append("safe dry-run command includes execution/visible-runtime flags")
    for fragment in (
        r".\scripts\smoke\run_hd_soak.ps1",
        "-Tier short2",
        "-Route menu-idle",
        f"-ReportJson {EXPECTED_REPORT_JSON}",
        f"-ReportMarkdown {EXPECTED_REPORT_MD}",
        "-Json",
    ):
        if fragment not in command:
            failures.append(f"dry-run command missing fragment: {fragment}")
    return failures


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    sources = {
        "next_actions": args.next_actions_json,
        "step_status": args.step_status_json,
        "harness_guard": args.hd_soak_harness_guard_json,
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
    action = next_actions.get("next_action") or {}
    current_step = step_status.get("current_step") or {}
    runtime_command = str(action.get("exact_runtime_command") or "")
    dry_run_command = str(action.get("safe_dry_run_command") or "")
    post_run_validation = [str(row) for row in action.get("post_run_validation") or []]

    if next_actions and not next_actions.get("passed"):
        failures.append("next-actions report is not passing")
    if next_actions.get("status") != "waiting_for_explicit_visible_runtime_approval":
        failures.append(f"next-actions status is {next_actions.get('status')!r}")
    if action.get("id") != "run_short2_menu_idle_soak":
        failures.append(f"next action id is {action.get('id')!r}")
    if action.get("requires_explicit_user_approval") is not True:
        failures.append("next action is not marked as requiring explicit user approval")
    if action.get("requires_visible_runtime") is not True:
        failures.append("next action is not marked as visible runtime")

    failures.extend(command_has_required_shape(runtime_command))
    failures.extend(dry_run_has_required_shape(dry_run_command))
    if current_step.get("id") != EXPECTED_FIRST_STEP:
        failures.append(f"current short-step id is {current_step.get('id')!r}")
    if current_step.get("status") not in {"pending_approval_legacy_compat", "missing_pending_approval"}:
        failures.append(f"current short-step status is {current_step.get('status')!r}")
    if current_step.get("next_command") and current_step.get("next_command") != runtime_command:
        failures.append("step-status next command does not match next-actions runtime command")
    if step_status and step_status.get("ladder_complete") is True:
        failures.append("short ladder is already complete; approval preflight should not request first soak")

    writes = set(action.get("writes_outside_repo") or [])
    if writes != EXPECTED_WRITES:
        failures.append(f"writes_outside_repo is {sorted(writes)!r}, expected {sorted(EXPECTED_WRITES)!r}")
    if MUST_NOT_MODIFY not in set(action.get("must_not_modify") or []):
        failures.append(f"must_not_modify does not include {MUST_NOT_MODIFY}")
    if not any(EXPECTED_GUARD_JSON in command for command in post_run_validation):
        failures.append("post-run validation does not write the canonical first-step guard")
    if not any(EXPECTED_TRIAGE_JSON in command for command in post_run_validation):
        failures.append("post-run validation does not write the canonical first-step triage")
    if not any("current_evidence_refresh.py" in command for command in post_run_validation):
        failures.append("post-run validation does not refresh current evidence")
    if not any("evidence_index_check.py" in command for command in post_run_validation):
        failures.append("post-run validation does not check evidence links")
    if "git diff --check" not in post_run_validation:
        failures.append("post-run validation does not include git diff --check")

    for guard_name in ("harness_guard", "visible_runtime_guard", "process_hygiene", "exe_artifact"):
        report = loaded.get(guard_name) or {}
        if report and not report.get("passed"):
            failures.append(f"{guard_name} is not passing")
    if (loaded.get("process_hygiene") or {}).get("matching_process_count") not in {None, 0}:
        failures.append("process hygiene found stale cdb/clash95 processes")
    if (loaded.get("exe_artifact") or {}).get("tracked_exes"):
        failures.append("exe artifact guard reports tracked executables")

    approval_prompt = (
        "Approve the first short2 menu-idle visible-runtime soak using the exact "
        "approval-gated command in this report. It will generate a patched candidate "
        r"under C:\ClashTests\hd-soak and raw frame artifacts under C:\ClashCaptures\hd-soak; "
        r"it must not modify C:\Clash\clash95.exe."
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "status": "ready_for_explicit_approval" if not failures else "not_ready",
        "source_artifacts": {name: str(path) for name, path in sources.items()},
        "current_step": current_step,
        "approval_prompt": approval_prompt,
        "safe_dry_run_command": dry_run_command,
        "approval_gated_runtime_command": runtime_command,
        "post_run_validation": post_run_validation,
        "writes_outside_repo": sorted(writes),
        "must_not_modify": action.get("must_not_modify") or [],
        "guards": {
            "harness_guard_passed": bool((loaded.get("harness_guard") or {}).get("passed")),
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
        f"- Stable stage should change: `{report['locks']['stable_stage_should_change']}`",
        f"- Right-bottom promotion blocked: `{report['locks']['right_bottom_promotion_blocked']}`",
        "",
        "## Approval Prompt",
        "",
        report["approval_prompt"],
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
        "## Post-Run Validation",
        "",
    ]
    for command in report.get("post_run_validation") or []:
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
