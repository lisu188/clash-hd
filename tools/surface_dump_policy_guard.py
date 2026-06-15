#!/usr/bin/env python3
"""Verify the CDB surface-dump launcher defaults to no visible desktop.

This is a repo-only source guard. It reads `scripts/cdb/run_cdb_surface_dump.ps1` and does
not launch Clash95, CDB, wrappers, PowerShell, or any visible GUI process.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SCRIPT = Path("scripts/cdb/run_cdb_surface_dump.ps1")
DEFAULT_JSON = Path("captures/current/surface-dump-policy-guard-current.json")
DEFAULT_MD = Path("captures/current/surface-dump-policy-guard-current.md")
RUNTIME_POLICY = "repo-only source inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def check_record(name: str, passed: bool, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "summary": summary or {},
        "failures": [] if passed else [name],
    }


def line_numbers(text: str, pattern: str) -> list[int]:
    regex = re.compile(pattern)
    return [
        index
        for index, line in enumerate(text.splitlines(), start=1)
        if regex.search(line)
    ]


def visible_branch(text: str) -> str:
    match = re.search(
        r"if\s*\(\$AllowVisibleDesktop\)\s*\{(?P<branch>.*?)^\s*\}\s*else\s*\{",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group("branch") if match else ""


def hidden_branch(text: str) -> str:
    match = re.search(
        r"else\s*\{\s*\r?\n(?P<branch>\s*\$launch\s*=\s*Start-CdbOnHiddenDesktop.*?^\s*\})",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group("branch") if match else ""


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    failures: list[str] = []
    checks: dict[str, Any] = {}
    script = args.script
    if not script.exists():
        return {
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "passed": False,
            "runtime_policy": RUNTIME_POLICY,
            "script": str(script),
            "checks": {},
            "failures": [f"missing surface-dump harness script: {script}"],
        }

    text = script.read_text(encoding="utf-8-sig", errors="replace")
    visible = visible_branch(text)
    hidden = hidden_branch(text)

    check_specs = {
        "allow_visible_desktop_is_switch": (
            bool(re.search(r"\[switch\]\$AllowVisibleDesktop\b", text)),
            {"lines": line_numbers(text, r"\[switch\]\$AllowVisibleDesktop\b")},
            "surface-dump harness must expose -AllowVisibleDesktop as an explicit switch",
        ),
        "default_launch_mode_hidden": (
            "$launchMode = 'hidden-desktop'" in text,
            {"lines": line_numbers(text, r"\$launchMode\s*=\s*'hidden-desktop'")},
            "surface-dump harness must default LaunchMode to hidden-desktop",
        ),
        "createdesktop_failure_refuses_visible_fallback": (
            "Refusing visible fallback without -AllowVisibleDesktop" in text,
            {
                "lines": line_numbers(
                    text,
                    r"Refusing visible fallback without -AllowVisibleDesktop",
                )
            },
            "CreateDesktop failure must refuse visible fallback unless explicitly allowed",
        ),
        "visible_branch_requires_explicit_switch": (
            bool(visible)
            and "visible-desktop-explicit" in visible
            and "Start-Process -FilePath $Cdb" in visible,
            {
                "visible_branch_line": line_numbers(text, r"if\s*\(\$AllowVisibleDesktop\)"),
                "visible_launch_lines": line_numbers(text, r"visible-desktop-explicit"),
                "start_process_lines": line_numbers(text, r"Start-Process\s+-FilePath\s+\$Cdb\b"),
            },
            "visible desktop launch must be inside the -AllowVisibleDesktop branch",
        ),
        "hidden_branch_uses_createdesktop": (
            bool(hidden) and "Start-CdbOnHiddenDesktop" in hidden,
            {"hidden_branch_lines": line_numbers(text, r"Start-CdbOnHiddenDesktop")},
            "default branch must use Start-CdbOnHiddenDesktop",
        ),
        "summary_records_hidden_desktop": (
            text.count("HiddenDesktop = (-not $AllowVisibleDesktop)") >= 2,
            {
                "lines": line_numbers(
                    text,
                    r"HiddenDesktop\s*=\s*\(-not\s+\$AllowVisibleDesktop\)",
                )
            },
            "both failure and final summary paths must record HiddenDesktop",
        ),
        "summary_records_allow_visible_desktop": (
            text.count("AllowVisibleDesktop = [bool]$AllowVisibleDesktop") >= 2,
            {
                "lines": line_numbers(
                    text,
                    r"AllowVisibleDesktop\s*=\s*\[bool\]\$AllowVisibleDesktop",
                )
            },
            "both failure and final summary paths must record AllowVisibleDesktop",
        ),
    }

    for name, (passed, summary, failure) in check_specs.items():
        checks[name] = check_record(name, bool(passed), summary)
        if not passed:
            checks[name]["failures"] = [failure]
            failures.append(f"{name}: {failure}")

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": "surface-dump harness must default to hidden desktop and require -AllowVisibleDesktop for active-desktop fallback",
        "script": str(script),
        "checks": checks,
        "failures": failures,
    }


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(guard['passed'])}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"guard-policy: {guard['guard_policy']}")
    for name, check in guard["checks"].items():
        print(f"{name}: {status_text(bool(check.get('passed')))}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# Surface Dump Policy Guard",
        "",
        f"- Overall: {status_text(guard['passed'])}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        f"- Script: `{guard['script']}`",
        "",
        "## Checks",
        "",
    ]
    for name, check in guard["checks"].items():
        lines.append(f"- `{name}`: `{status_text(bool(check.get('passed')))}`")
        for failure in check.get("failures", []):
            lines.append(f"  - {failure}")
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
