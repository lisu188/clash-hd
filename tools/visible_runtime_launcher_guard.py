#!/usr/bin/env python3
"""Verify legacy visible-runtime launchers/helpers require explicit approval.

This is a repo-only source guard. It reads PowerShell harness scripts and does
not launch Clash95, CDB, wrappers, PowerShell, or any visible GUI process.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_JSON = Path("captures/current/visible-runtime-launcher-guard-current.json")
DEFAULT_MD = Path("captures/current/visible-runtime-launcher-guard-current.md")
RUNTIME_POLICY = "repo-only source inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
APPROVAL_PHRASE = "explicit user approval"

DEFAULT_SCRIPTS = [
    Path("scripts/smoke/run_clash_visual_smoke.ps1"),
    Path("scripts/smoke/run_hd_soak.ps1"),
    Path("scripts/cdb/run_cdb_map_probe.ps1"),
    Path("scripts/cdb/run_cdb_python_mouse_map.ps1"),
    Path("scripts/cdb/run_cdb_viewport_bounds_probe.ps1"),
    Path("scripts/cdb/run_cdb_battle_visible_input_probe.ps1"),
    Path("scripts/smoke/run_clash_windows_sandbox.ps1"),
    Path("scripts/capture/capture_clash_client_frame.ps1"),
]
VISIBLE_CHILD_SCRIPT_NAMES = {path.name.lower() for path in DEFAULT_SCRIPTS}

EXEMPT_RISKY_SCRIPTS = {
    Path("install_cdb.ps1"): "installer workflow, not a Clash95 runtime harness",
    Path("scripts/cdb/run_cdb_surface_dump.ps1"): "hidden-desktop CDB harness covered by surface_dump_policy_guard",
    Path("scripts/cdb/run_cdb_right_bottom_ui_probe.ps1"): "delegates to scripts/cdb/run_cdb_surface_dump.ps1 and inherits its visible-desktop gate",
}

RISKY_API_RE = (
    "SetForegroundWindow|BringWindowToTop|ShowWindow|SetWindowPos|"
    "SetCursorPos|SendInput|PostMessage|keybd_event"
)

RISKY_RE = re.compile(
    r"^\s*(?:\$[A-Za-z_][A-Za-z0-9_]*\s*=\s*)?"
    rf"(?:Start-Process\b|\[[^\]]+\]::(?:{RISKY_API_RE})\b|\$[A-Za-z_][A-Za-z0-9_]*\.CopyFromScreen\b)",
    re.IGNORECASE,
)

INVENTORY_RISKY_RE = re.compile(
    RISKY_RE.pattern + r"|^\s*&\s*powershell\.exe\b",
    re.IGNORECASE,
)

CHILD_SCRIPT_ASSIGN_RE = re.compile(
    r"\$(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*Join-Path\s+\$PSScriptRoot\s+['\"](?P<script>[^'\"]+\.ps1)['\"]",
    re.IGNORECASE,
)

POWERSHELL_FILE_RE = re.compile(r"^\s*&\s*powershell\.exe\b.*\s-File\s+", re.IGNORECASE)
ALLOW_VISIBLE_ARG_RE = re.compile(r"\s-AllowVisibleRuntime\b", re.IGNORECASE)


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def line_numbers(text: str, pattern: str) -> list[int]:
    regex = re.compile(pattern, re.IGNORECASE)
    return [
        index
        for index, line in enumerate(text.splitlines(), start=1)
        if regex.search(line)
    ]


def first_match_line(text: str, pattern: re.Pattern[str]) -> int | None:
    for index, line in enumerate(text.splitlines(), start=1):
        if pattern.search(line):
            return index
    return None


def relative_path(path: Path, root: Path) -> Path:
    try:
        return path.resolve().relative_to(root.resolve())
    except ValueError:
        return path


def normalize_path(path: Path) -> str:
    return path.as_posix().lower()


def child_visible_runtime_forwarding_failures(text: str, path: Path) -> tuple[list[str], list[int]]:
    variable_targets: dict[str, str] = {}
    failures: list[str] = []
    invocation_lines: list[int] = []

    for line in text.splitlines():
        match = CHILD_SCRIPT_ASSIGN_RE.search(line)
        if match:
            variable_targets[f"${match.group('var').lower()}"] = Path(match.group("script")).name.lower()

    for index, line in enumerate(text.splitlines(), start=1):
        if not POWERSHELL_FILE_RE.search(line):
            continue

        lower_line = line.lower()
        helper_name = ""
        for variable, target in variable_targets.items():
            if variable in lower_line:
                helper_name = target
                break
        if not helper_name:
            for script_name in VISIBLE_CHILD_SCRIPT_NAMES:
                if script_name in lower_line:
                    helper_name = script_name
                    break

        if helper_name not in VISIBLE_CHILD_SCRIPT_NAMES:
            continue

        invocation_lines.append(index)
        if not ALLOW_VISIBLE_ARG_RE.search(line):
            failures.append(
                f"{path} invokes guarded helper {helper_name} without forwarding -AllowVisibleRuntime at line {index}"
            )

    return failures, invocation_lines


def build_inventory(root: Path, guarded_scripts: list[Path]) -> dict[str, Any]:
    root = root.resolve()
    guarded = {normalize_path(relative_path(path, root)) for path in guarded_scripts}
    exempt = {normalize_path(path): reason for path, reason in EXEMPT_RISKY_SCRIPTS.items()}
    scripts: list[dict[str, Any]] = []
    failures: list[str] = []

    for path in sorted(root.glob("*.ps1")):
        relative = relative_path(path, root)
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        first_risky_line = first_match_line(text, INVENTORY_RISKY_RE)
        if first_risky_line is None:
            continue

        key = normalize_path(relative)
        classification = "unclassified"
        reason = ""
        if key in guarded:
            classification = "guarded"
        elif key in exempt:
            classification = "exempt"
            reason = exempt[key]
        else:
            failures.append(f"{relative} has risky runtime/window/input/capture calls but is not guarded or exempt")

        scripts.append(
            {
                "script": str(relative),
                "classification": classification,
                "reason": reason,
                "first_risky_line": first_risky_line,
            }
        )

    return {
        "checked": True,
        "root": str(root),
        "risky_script_count": len(scripts),
        "guarded_risky_script_count": sum(1 for script in scripts if script["classification"] == "guarded"),
        "exempt_risky_script_count": sum(1 for script in scripts if script["classification"] == "exempt"),
        "unclassified_risky_script_count": sum(
            1 for script in scripts if script["classification"] == "unclassified"
        ),
        "scripts": scripts,
        "failures": failures,
    }


def summarize_script(path: Path) -> dict[str, Any]:
    failures: list[str] = []
    if not path.exists():
        return {
            "script": str(path),
            "passed": False,
            "exists": False,
            "failures": [f"missing visible-runtime launcher script: {path}"],
        }

    text = path.read_text(encoding="utf-8-sig", errors="replace")
    allow_switch_lines = line_numbers(text, r"\[switch\]\$AllowVisibleRuntime\b")
    guard_lines = line_numbers(text, r"if\s*\([^\r\n]*\$AllowVisibleRuntime[^\r\n]*\)\s*\{")
    approval_lines = line_numbers(text, re.escape(APPROVAL_PHRASE))
    throw_lines = line_numbers(text, r"throw\s+.*AllowVisibleRuntime")
    first_guard_line = guard_lines[0] if guard_lines else None
    first_risky_line = first_match_line(text, RISKY_RE)
    child_failures, child_invocation_lines = child_visible_runtime_forwarding_failures(text, path)

    if not allow_switch_lines:
        failures.append(f"{path} is missing [switch]$AllowVisibleRuntime")
    if not guard_lines:
        failures.append(f"{path} is missing an early AllowVisibleRuntime guard")
    if not approval_lines:
        failures.append(f"{path} guard does not mention explicit user approval")
    if not throw_lines:
        failures.append(f"{path} guard does not throw with an AllowVisibleRuntime hint")
    if first_guard_line and first_risky_line and first_guard_line > first_risky_line:
        failures.append(
            f"{path} AllowVisibleRuntime guard appears after risky runtime call line {first_risky_line}"
        )
    failures.extend(child_failures)

    return {
        "script": str(path),
        "passed": not failures,
        "exists": True,
        "allow_visible_runtime_lines": allow_switch_lines,
        "guard_lines": guard_lines,
        "approval_phrase_lines": approval_lines,
        "throw_lines": throw_lines,
        "first_risky_line": first_risky_line,
        "child_visible_runtime_invocation_lines": child_invocation_lines,
        "failures": failures,
    }


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    scripts = args.script or DEFAULT_SCRIPTS
    script_summaries = [summarize_script(path) for path in scripts]
    check_inventory = getattr(args, "check_inventory", not bool(args.script))
    inventory = {"checked": False, "failures": []}
    if check_inventory:
        inventory = build_inventory(getattr(args, "root", Path(".")), list(scripts))
    failures = [
        failure
        for script in script_summaries
        for failure in script.get("failures", [])
    ]
    failures.extend(inventory.get("failures", []))
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": "legacy visible-runtime launchers/helpers must fail closed unless -AllowVisibleRuntime is explicitly supplied after user approval; guarded child helpers must receive the same switch; root PowerShell risky-call inventory must be guarded or explicitly exempt",
        "script_count": len(script_summaries),
        "passing_script_count": sum(1 for script in script_summaries if script.get("passed")),
        "inventory": inventory,
        "scripts": script_summaries,
        "failures": failures,
    }


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(guard['passed']))}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"guard-policy: {guard['guard_policy']}")
    print(f"script-count: {guard['script_count']}")
    print(f"passing-script-count: {guard['passing_script_count']}")
    inventory = guard.get("inventory", {})
    if inventory.get("checked"):
        print(f"inventory-risky-script-count: {inventory['risky_script_count']}")
        print(f"inventory-unclassified-risky-script-count: {inventory['unclassified_risky_script_count']}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# Visible Runtime Launcher Guard",
        "",
        f"- Overall: {status_text(bool(guard['passed']))}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        f"- Scripts checked: `{guard['script_count']}`",
        f"- Passing scripts: `{guard['passing_script_count']}`",
        "",
        "## Scripts",
        "",
    ]
    for script in guard["scripts"]:
        lines.append(
            "- `{script}`: `{status}` guard_lines=`{guard_lines}` first_risky_line=`{risky}` child_helper_lines=`{child}`".format(
                script=script.get("script"),
                status=status_text(bool(script.get("passed"))),
                guard_lines=script.get("guard_lines"),
                risky=script.get("first_risky_line"),
                child=script.get("child_visible_runtime_invocation_lines"),
            )
        )
        for failure in script.get("failures", []):
            lines.append(f"  - {failure}")
    inventory = guard.get("inventory", {})
    if inventory.get("checked"):
        lines.extend(
            [
                "",
                "## Root PowerShell Risky-Call Inventory",
                "",
                f"- Root: `{inventory['root']}`",
                f"- Risky scripts: `{inventory['risky_script_count']}`",
                f"- Guarded risky scripts: `{inventory['guarded_risky_script_count']}`",
                f"- Exempt risky scripts: `{inventory['exempt_risky_script_count']}`",
                f"- Unclassified risky scripts: `{inventory['unclassified_risky_script_count']}`",
            ]
        )
        if inventory["scripts"]:
            lines.append("")
        for script in inventory["scripts"]:
            suffix = f" reason=`{script['reason']}`" if script.get("reason") else ""
            lines.append(
                f"- `{script['script']}`: `{script['classification']}` first_risky_line=`{script['first_risky_line']}`{suffix}"
            )
    if guard["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, action="append", default=[])
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--skip-inventory", action="store_true")
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.check_inventory = not args.skip_inventory and not bool(args.script)
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
