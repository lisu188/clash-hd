#!/usr/bin/env python3
"""Verify the visible battle input harness fails closed on invalid CDB logs.

This is a repo-only source guard. It reads the PowerShell harness and does not
launch Clash95, CDB, wrappers, PowerShell, or any visible window.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SCRIPT = Path("scripts/cdb/run_cdb_battle_visible_input_probe.ps1")
DEFAULT_JSON = Path("captures/current/battle-visible-harness-guard-current.json")
DEFAULT_MD = Path("captures/current/battle-visible-harness-guard-current.md")
RUNTIME_POLICY = "repo-only source inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
FATAL_CDB_PATTERNS = (
    "Unable to insert breakpoint",
    "Unable to remove breakpoint",
    "Break instruction exception - code 80000003",
)


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def line_numbers(text: str, pattern: str) -> list[int]:
    regex = re.compile(pattern, re.IGNORECASE)
    return [
        index
        for index, line in enumerate(text.splitlines(), start=1)
        if regex.search(line)
    ]


def wait_log_pattern_body(text: str) -> str:
    match = re.search(r"function\s+Wait-LogPattern\s*\{", text, re.IGNORECASE)
    if not match:
        return ""

    depth = 0
    start = match.start()
    for index in range(match.start(), len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return text[start:]


def build_guard(script: Path = DEFAULT_SCRIPT) -> dict[str, Any]:
    failures: list[str] = []
    checks: list[dict[str, Any]] = []
    if not script.exists():
        return {
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "passed": False,
            "runtime_policy": RUNTIME_POLICY,
            "script": str(script),
            "checks": [],
            "failures": [f"missing visible battle input harness: {script}"],
        }

    text = script.read_text(encoding="utf-8-sig", errors="replace")
    wait_body = wait_log_pattern_body(text)

    def add_check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            failures.append(detail or name)

    add_check(
        "visible runtime guard",
        bool(line_numbers(text, r"\[switch\]\$AllowVisibleRuntime\b"))
        and "explicit user approval" in text
        and "throw" in text
        and "AllowVisibleRuntime" in text,
        f"{script} must keep the explicit AllowVisibleRuntime approval gate",
    )
    add_check(
        "raw screen input mode",
        "raw-screen" in text and "RawScreenPoints" in text,
        f"{script} must keep the raw-screen input path for HWND-free clicks",
    )
    add_check(
        "wait log function",
        bool(wait_body),
        f"{script} must define Wait-LogPattern",
    )

    for pattern in FATAL_CDB_PATTERNS:
        add_check(
            f"fatal CDB pattern: {pattern}",
            pattern in wait_body,
            f"Wait-LogPattern must detect fatal CDB log pattern: {pattern}",
        )

    add_check(
        "post-g break exception gate",
        "$cdbHasStarted = $false" in wait_body
        and "$cdbHasStarted = $true" in wait_body
        and "$cdbHasStarted -and" in wait_body
        and re.search(r"\\s\*g\\s\*", wait_body, re.IGNORECASE) is not None,
        "Wait-LogPattern must gate 80000003 break-instruction failures behind the post-g CDB state",
    )
    add_check(
        "incremental log scan",
        "processedLineCount" in wait_body and "Select-Object -Skip" in wait_body,
        "Wait-LogPattern must process only new log lines so the initial loader break is not reclassified after g",
    )
    add_check(
        "fatal wait failure throws",
        "CDB became invalid before" in wait_body and "throw" in wait_body,
        "Wait-LogPattern must throw a clear failure when CDB becomes invalid before readiness",
    )

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "script": str(script),
        "wait_log_pattern_lines": line_numbers(text, r"function\s+Wait-LogPattern"),
        "checks": checks,
        "failures": failures,
    }


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(guard['passed']))}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"script: {guard['script']}")
    for check in guard["checks"]:
        print(f"{check['name']}: {status_text(bool(check['passed']))}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# Battle Visible Harness Guard",
        "",
        f"- Overall: {status_text(bool(guard['passed']))}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Script: `{guard['script']}`",
        f"- Wait-LogPattern lines: `{guard.get('wait_log_pattern_lines', [])}`",
        "",
        "## Checks",
        "",
    ]
    for check in guard["checks"]:
        lines.append(f"- `{check['name']}`: `{status_text(bool(check['passed']))}`")
        if check.get("detail") and not check["passed"]:
            lines.append(f"  - {check['detail']}")
    if guard["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, default=DEFAULT_SCRIPT)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    guard = build_guard(args.script)
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
