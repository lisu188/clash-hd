#!/usr/bin/env python3
"""Classify Python helpers that can launch runtime or touch Win32 input.

This is a repo-only source guard. It reads Python helper source files and does
not launch Clash95, CDB, wrappers, PowerShell, or any visible GUI process.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_JSON = Path("captures/current/python-runtime-safety-current.json")
DEFAULT_MD = Path("captures/current/python-runtime-safety-current.md")
RUNTIME_POLICY = "repo-only source inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"

RISK_PATTERNS: dict[str, re.Pattern[str]] = {
    "subprocess": re.compile(r"\bsubprocess\b"),
    "process_launch": re.compile(r"\b(?:Popen|run|call|check_call|check_output)\s*\("),
    "ctypes": re.compile(r"\bctypes\b|\bWinDLL\b|\bwindll\b"),
    "win32_user32": re.compile(r"\buser32\b|\bwin32\b", re.IGNORECASE),
    "sendinput": re.compile(r"\bSendInput\b", re.IGNORECASE),
    "postmessage": re.compile(r"\bPostMessage[AW]?\b", re.IGNORECASE),
    "cursor_window_input": re.compile(
        r"\b(?:SetCursorPos|GetCursorPos|ScreenToClient|ClientToScreen|"
        r"SetForegroundWindow|BringWindowToTop|ShowWindow|MoveWindow|keybd_event)\b",
        re.IGNORECASE,
    ),
    "shell_launch": re.compile(r"\b(?:os\.system|ShellExecute|CreateProcess)\b", re.IGNORECASE),
}

GATED_HELPERS = {
    "mouse_path_probe.py": "manual/visible-runtime evidence helper; it launches/moves/clicks only when explicitly invoked",
    "raw_sendinput_click.py": "manual/visible-runtime evidence helper; it sends OS input only when explicitly invoked by a guarded harness",
}

EXEMPT_HELPERS = {
    "battle_ui_evidence_matrix.py": "repo-only evidence matrix; process-launch text is a type annotation or fixture reference",
    "battle_visible_input_summary.py": "repo-only log parser; SendInput text appears in artifact names or evidence prose",
    "build_cloud_fixtures.py": "cloud fixture builder; risky text is source material/path filtering, not runtime window or input calls",
    "cloud_check.py": "cloud-safe validation runner; subprocess is limited to repo tests and does not launch Clash95 or CDB",
    "exe_artifact_guard.py": "uses git subprocess read-only for artifact inventory",
    "load_slot_timeout_phase.py": "repo-only CDB log parser; Win32 text appears only in timeout-stack classification labels",
    "process_hygiene_guard.py": "uses Toolhelp32 read-only process enumeration and does not launch or focus windows",
    "current_evidence_refresh.py": "repo-only evidence coordinator; risky API text appears in policy/test descriptions",
    "manual_directinput_run_plan.py": "repo-only command planner; visible-runtime and input text appears only in gated command templates",
    "visible_runtime_launcher_guard.py": "repo-only source scanner; risky API names appear as patterns, not runtime calls",
    "right_bottom_slot_fixture_script_guard.py": "repo-only source scanner; risky API names appear as patterns, not runtime calls",
    "repo_compaction_cleanup.py": "repo cleanup planner/executor; moves only classified untracked capture artifacts when --execute is supplied",
    "repo_structure.py": "repo-only structure guard; subprocess is limited to read-only git inventory",
    "right_bottom_slot_fixture_result_summary.py": "repo-only CDB log parser; Win32/input text appears in evidence markers",
    "python_runtime_safety_guard.py": "this scanner names risky APIs without calling them",
}


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def risky_lines(text: str) -> dict[str, list[int]]:
    findings: dict[str, list[int]] = {}
    for name, pattern in RISK_PATTERNS.items():
        lines = [
            index
            for index, line in enumerate(text.splitlines(), start=1)
            if pattern.search(line)
        ]
        if lines:
            findings[name] = lines
    return findings


def classify_python(path: Path, root: Path) -> dict[str, Any]:
    rel = relative_path(path, root)
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    findings = risky_lines(text)
    name = path.name
    failures: list[str] = []

    if not findings:
        classification = "safe"
        reason = "no risky runtime/input/process APIs found"
    elif name.startswith("test_"):
        classification = "test_fixture"
        reason = "fixture test may spawn Python subprocesses but is not a runtime helper"
    elif name in EXEMPT_HELPERS:
        classification = "exempt"
        reason = EXEMPT_HELPERS[name]
    elif name in GATED_HELPERS:
        classification = "manual_visible_runtime_gated"
        reason = GATED_HELPERS[name]
    else:
        classification = "unclassified_risky"
        reason = "risky Python helper is not explicitly gated or exempt"
        failures.append(f"{rel} uses risky Python runtime/input APIs but is not gated or exempt")

    return {
        "path": rel,
        "classification": classification,
        "reason": reason,
        "risk_categories": sorted(findings),
        "risk_lines": findings,
        "failures": failures,
    }


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    files = sorted((root / args.tools_dir).glob("*.py"))
    records = [classify_python(path, root) for path in files]
    failures = [failure for record in records for failure in record["failures"]]
    risky = [record for record in records if record["risk_categories"]]
    by_class: dict[str, int] = {}
    for record in records:
        by_class[record["classification"]] = by_class.get(record["classification"], 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": "Python helpers with process launch, ctypes, Win32 window/input, SendInput, or PostMessage usage must be test fixtures, explicitly gated, or explicitly exempt",
        "root": str(root),
        "file_count": len(records),
        "risky_file_count": len(risky),
        "classification_counts": by_class,
        "gated_helpers": GATED_HELPERS,
        "exempt_helpers": EXEMPT_HELPERS,
        "records": records,
        "failures": failures,
    }


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(guard['passed']))}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"risky-files: {guard['risky_file_count']}")
    for name, count in sorted(guard["classification_counts"].items()):
        print(f"{name}: {count}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# Python Runtime Safety Guard",
        "",
        f"- Overall: {status_text(bool(guard['passed']))}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        f"- Python files scanned: `{guard['file_count']}`",
        f"- Risky files: `{guard['risky_file_count']}`",
        "",
        "## Classification Counts",
        "",
    ]
    for name, count in sorted(guard["classification_counts"].items()):
        lines.append(f"- `{name}`: `{count}`")
    lines.extend(["", "## Risky Helpers", ""])
    for record in guard["records"]:
        if not record["risk_categories"]:
            continue
        lines.append(
            "- `{path}`: `{classification}` risks=`{risks}`".format(
                path=record["path"],
                classification=record["classification"],
                risks=record["risk_categories"],
            )
        )
        if record["reason"]:
            lines.append(f"  - {record['reason']}")
        for failure in record["failures"]:
            lines.append(f"  - {failure}")
    if guard["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--tools-dir", type=Path, default=Path("tools"))
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
