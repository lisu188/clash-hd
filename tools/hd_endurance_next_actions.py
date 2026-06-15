#!/usr/bin/env python3
"""Build the next-action handoff for the HD endurance road.

This is repo-only triage. It reads the release checklist and emits exact safe
commands plus the approval-gated runtime command that would prove the next
milestone. It does not launch Clash95, CDB, wrappers, PowerShell, or windows.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CHECKLIST_JSON = Path("captures/current/hd-endurance-release-checklist-current.json")
DEFAULT_JSON = Path("captures/current/hd-endurance-next-actions-current.json")
DEFAULT_MD = Path("captures/current/hd-endurance-next-actions-current.md")
RUNTIME_POLICY = (
    "repo-only endurance next-action triage; does not launch Clash95, CDB, "
    "wrappers, PowerShell harnesses, or visible windows"
)


VISIBLE_SHORT2_COMMAND = (
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
    ".\\scripts\\smoke\\run_hd_soak.ps1 "
    "-Tier short2 -Route menu-idle "
    "-ReportJson captures\\current\\hd-soak-short2-menu-idle-current.json "
    "-ReportMarkdown captures\\current\\hd-soak-short2-menu-idle-current.md "
    "-Execute -AllowVisibleRuntime -RequirePass -Json"
)
DRY_RUN_SHORT2_COMMAND = (
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
    ".\\scripts\\smoke\\run_hd_soak.ps1 -Tier short2 -Route menu-idle "
    "-ReportJson captures\\current\\hd-soak-short2-menu-idle-current.json "
    "-ReportMarkdown captures\\current\\hd-soak-short2-menu-idle-current.md -Json"
)


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def failing_requirements(checklist: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in checklist.get("requirements", []) if not row.get("passed")]


def group_requirements(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for row in rows:
        key = str(row.get("category") or "uncategorized")
        groups.setdefault(key, []).append(str(row.get("id")))
    return groups


def next_action_for_milestone(milestone: dict[str, Any] | None) -> dict[str, Any]:
    milestone_id = (milestone or {}).get("id")
    if milestone_id == "short2_menu_idle_soak":
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
            "post_run_validation": [
                (
                    r"C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime"
                    r"\dependencies\python\python.exe tools\hd_soak_report.py "
                    r"captures\current\hd-soak-short2-menu-idle-current.json "
                    r"--write-json captures\current\hd-soak-short2-menu-idle-guard-current.json "
                    r"--write-markdown captures\current\hd-soak-short2-menu-idle-guard-current.md "
                    r"--require-pass"
                ),
                (
                    r"C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime"
                    r"\dependencies\python\python.exe tools\hd_soak_failure_triage.py "
                    r"captures\current\hd-soak-short2-menu-idle-current.json "
                    r"--write-json captures\current\hd-soak-short2-menu-idle-triage-current.json "
                    r"--write-markdown captures\current\hd-soak-short2-menu-idle-triage-current.md"
                ),
                (
                    r"C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime"
                    r"\dependencies\python\python.exe tools\current_evidence_refresh.py "
                    r"--write-json captures\current\current-evidence-refresh-current.json "
                    r"--write-markdown captures\current\current-evidence-refresh-current.md"
                ),
                (
                    r"C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime"
                    r"\dependencies\python\python.exe tools\evidence_index_check.py "
                    r"captures\current\hd-map-evidence-current.md --require-pass"
                ),
                "git diff --check",
            ],
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
    next_action = next_action_for_milestone(milestone)
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
        if action.get("safe_dry_run_command"):
            lines.extend(["", "Safe dry-run command:", "", "```powershell", action["safe_dry_run_command"], "```"])
        if action.get("exact_runtime_command"):
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
        if action.get("post_run_validation"):
            lines.extend(["", "Post-run validation:", ""])
            for command in action["post_run_validation"]:
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
