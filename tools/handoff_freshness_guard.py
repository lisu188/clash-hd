#!/usr/bin/env python3
"""Verify current handoff docs point at the latest no-popup blockers.

This is a repo-only guard. It reads markdown handoff/evidence files and does
not launch Clash95, CDB, wrappers, PowerShell, or any visible GUI process.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_JSON = Path("captures/current/handoff-freshness-guard-current.json")
DEFAULT_MD = Path("captures/current/handoff-freshness-guard-current.md")
DEFAULT_NEXT = Path(".codex-loop/NEXT.md")
DEFAULT_STATE = Path(".codex-loop/STATE.md")
DEFAULT_TASKS = Path(".codex-loop/TASKS.md")
DEFAULT_EVIDENCE_INDEX = Path("captures/current/hd-map-evidence-current.md")
DEFAULT_PROGRESS = Path("docs/hd/HD_MOD_PROGRESS.md")
DEFAULT_BOTTOM_QUESTION = Path("wiki/questions/how-should-the-bottom-tooltip-be-recovered.md")
RUNTIME_POLICY = "repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"

FORBIDDEN_STALE_PHRASES = [
    "next no-popup target is broader route/input safety",
    "the next right-bottom target is broader route/input safety",
    "remaining blocker is broader route/input safety",
    "pending broader route/input safety",
    "validate the bounds-guarded dynamic-origin candidate outside the debugger",
    "fix frame capture/window selection for cdb map probes",
    "the current png can include the debugger console",
    "run a true clean visual/gameplay smoke pass on the v2 conditional-switch",
    "capture a fresh gameplay frame from the bottom12 candidate",
    "capture a fresh gameplay frame from the partial12 map-drawing candidate",
    "enable windows sandbox",
    "fix or route around the vm harness map-entry failure",
    "add a vm harness readiness/result guard",
    "improve the vm visual-smoke route",
    "run `probes/cdb/menu/clash95_menu_load_route_probe.cdb` against the current candidate",
    "add mouse-edge boundary visibility sampling",
    "finish the log-sentinel early-stop mode for vm cdb route probes",
]

REQUIRED_PHRASE_GROUPS = {
    "route_timing_artifacts": [
        "right-bottom-route-timing-guard-current.md",
        "right-bottom-route-timing-guard-tests-current.md",
    ],
    "owner_flag_inventory_artifacts": [
        "right-bottom-owner-flag-inventory-current.md",
        "right-bottom-owner-flag-inventory-tests-current.md",
        "zero natural owner/action routes",
    ],
    "load_slot_route_limit_artifacts": [
        "load-slot-route-limit-current.md",
        "load-slot-route-limit-tests-current.md",
        "slots 3-5",
    ],
    "load_slot_transition_readiness_artifacts": [
        "load-slot-transition-readiness-current.md",
        "load-slot-transition-readiness-tests-current.md",
        "ready_for_hidden_transition_probe",
    ],
    "manual_or_override_blocker": [
        "manual/visible DirectInput proof",
        "explicit CDB-only promotion",
    ],
    "no_visible_runtime_warning": [
        "Do not run visible/manual",
        "explicit user approval",
    ],
    "no_popup_operator_preference": [
        "Do not launch Clash95, CDB, wrappers, PowerShell harnesses",
        "visible windows unless the user explicitly approves",
    ],
    "right_bottom_safety_done": [
        "right-bottom route timing guard",
        "stable-stage promotion",
    ],
    "manual_checklist_artifact": [
        "manual-directinput-validation-checklist-current.md",
        "pending_manual_validation",
    ],
    "manual_proof_template_artifact": [
        "manual-directinput-proof-template-current.md",
        "template_valid_as_proof=False",
    ],
    "completion_summary_artifact": [
        "current-completion-summary-current.md",
        "full-game completion below 100%",
    ],
    "visible_runtime_launcher_guard": [
        "visible-runtime-launcher-guard-current.md",
        "visible-runtime-launcher-guard-tests-current.md",
        "-AllowVisibleRuntime",
    ],
}

REQUIRED_LOOP_PHRASE_GROUPS = {
    "loop_load_slot_transition_readiness_artifacts": [
        "load-slot-transition-readiness-current.md",
        "load-slot-transition-readiness-tests-current.md",
        "ready_for_hidden_transition_probe",
    ],
}


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def read_text(path: Path) -> tuple[str, list[str]]:
    if not path.exists():
        return "", [f"missing handoff file: {path}"]
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace"), []
    except OSError as exc:
        return "", [f"could not read {path}: {type(exc).__name__}: {exc}"]


def check_forbidden(path: Path, text: str) -> list[str]:
    lowered = normalize_text(text)
    failures: list[str] = []
    for phrase in FORBIDDEN_STALE_PHRASES:
        if phrase.lower() in lowered:
            failures.append(f"{path} still contains stale blocker phrase: {phrase}")
    return failures


def check_required_groups(
    combined_text: str,
    required_groups: dict[str, list[str]] = REQUIRED_PHRASE_GROUPS,
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    lowered = normalize_text(combined_text)
    groups: dict[str, Any] = {}
    for name, phrases in required_groups.items():
        missing = [phrase for phrase in phrases if normalize_text(phrase) not in lowered]
        groups[name] = {
            "passed": not missing,
            "required": phrases,
            "missing": missing,
        }
        for phrase in missing:
            failures.append(f"missing current handoff phrase for {name}: {phrase}")
    return groups, failures


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    files = [
        args.next_md,
        args.state_md,
        args.tasks_md,
        args.evidence_index,
        args.progress_md,
        args.bottom_question_md,
    ]
    failures: list[str] = []
    file_checks: list[dict[str, Any]] = []
    combined_parts: list[str] = []
    loop_parts: list[str] = []
    loop_files = {args.next_md, args.state_md, args.tasks_md}

    for path in files:
        text, read_failures = read_text(path)
        failures.extend(read_failures)
        stale_failures = check_forbidden(path, text) if text else []
        failures.extend(stale_failures)
        combined_parts.append(text)
        if path in loop_files:
            loop_parts.append(text)
        file_checks.append(
            {
                "path": str(path),
                "exists": path.exists(),
                "passed": not read_failures and not stale_failures,
                "stale_failures": stale_failures,
            }
        )

    phrase_groups, phrase_failures = check_required_groups("\n".join(combined_parts))
    failures.extend(phrase_failures)
    loop_phrase_groups, loop_phrase_failures = check_required_groups(
        "\n".join(loop_parts),
        REQUIRED_LOOP_PHRASE_GROUPS,
    )
    failures.extend(loop_phrase_failures)

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": (
            "handoff docs must mention the current route timing guard, keep the "
            "right-bottom validation stage out of stable until manual proof or "
            "explicit CDB-only override, keep the non-promoting manual proof "
            "template visible, keep the percentage completion summary visible, "
            "keep the right-bottom owner-flag inventory visible, "
            "keep the load-slot route-limit boundary visible, "
            "keep the load-slot transition readiness matrix visible, "
            "preserve the user's no-popup runtime preference, "
            "require the visible-runtime launcher approval guard, "
            "and avoid stale route/input-safety, legacy visible-capture, or "
            "VM/visual-smoke blockers"
        ),
        "files": file_checks,
        "phrase_groups": phrase_groups,
        "loop_phrase_groups": loop_phrase_groups,
        "failures": failures,
    }


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(guard['passed'])}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"guard-policy: {guard['guard_policy']}")
    for group, result in guard["phrase_groups"].items():
        print(f"{group}: {status_text(bool(result.get('passed')))}")
    for group, result in guard["loop_phrase_groups"].items():
        print(f"{group}: {status_text(bool(result.get('passed')))}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# Handoff Freshness Guard",
        "",
        f"- Overall: {status_text(guard['passed'])}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        "",
        "## Phrase Groups",
        "",
    ]
    for name, result in guard["phrase_groups"].items():
        lines.append(f"- `{name}`: `{status_text(bool(result.get('passed')))}`")
        if result.get("missing"):
            lines.append(f"  - Missing: `{result['missing']}`")
    lines.extend(["", "## Loop Phrase Groups", ""])
    for name, result in guard["loop_phrase_groups"].items():
        lines.append(f"- `{name}`: `{status_text(bool(result.get('passed')))}`")
        if result.get("missing"):
            lines.append(f"  - Missing: `{result['missing']}`")
    lines.extend(["", "## Files", ""])
    for file_check in guard["files"]:
        lines.append(
            "- `{path}`: `{status}` exists=`{exists}`".format(
                path=file_check["path"],
                status=status_text(bool(file_check.get("passed"))),
                exists=file_check.get("exists"),
            )
        )
        for failure in file_check.get("stale_failures", []):
            lines.append(f"  - {failure}")
    if guard["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--next-md", type=Path, default=DEFAULT_NEXT)
    parser.add_argument("--state-md", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--tasks-md", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--evidence-index", type=Path, default=DEFAULT_EVIDENCE_INDEX)
    parser.add_argument("--progress-md", type=Path, default=DEFAULT_PROGRESS)
    parser.add_argument("--bottom-question-md", type=Path, default=DEFAULT_BOTTOM_QUESTION)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    guard = build_guard(args)
    print_guard(guard)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(guard, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, guard)
    if args.require_pass and not guard["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
