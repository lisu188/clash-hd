#!/usr/bin/env python3
"""Guard the right-bottom isolated slot fixture preparation script.

This is source-only validation for ``scripts/smoke/prepare_right_bottom_slot_fixture.ps1``.
It does not run PowerShell, copy saves, launch CDB, or touch visible windows.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SCRIPT = Path("scripts/smoke/prepare_right_bottom_slot_fixture.ps1")
DEFAULT_JSON = Path("captures/current/right-bottom-slot-fixture-script-guard-current.json")
DEFAULT_MD = Path("captures/current/right-bottom-slot-fixture-script-guard-current.md")

RUNTIME_POLICY = (
    "repo-only source inspection; does not run PowerShell, copy saves, launch "
    "Clash95, CDB, wrappers, or visible windows"
)
GUARD_POLICY = (
    "the fixture preparation script must default to dry-run, copy only after "
    "-Execute, optionally seed a non-save isolated workdir, refuse repository "
    "and live C:\\Clash\\save outputs, and avoid visible-runtime APIs"
)

REQUIRED_MARKERS = {
    "default_source_slot5": "$SourceSave = 'C:\\Clash\\save\\5.dat'",
    "default_source_workdir": "$SourceWorkDir = 'C:\\Clash'",
    "default_fixture_root": "$FixtureRoot = 'C:\\ClashTests\\right-bottom-slot5-as-slot0-fixture'",
    "target_load_slot_zero": "[int]$TargetLoadSlot = 0",
    "seed_workdir_switch": "[switch]$SeedWorkDir",
    "execute_switch": "[switch]$Execute",
    "repo_escape_switch": "[switch]$AllowRepoFixtureRoot",
    "repo_guard": "Test-IsUnderPath $FixtureRootFull $RepoRoot",
    "live_save_guard": "Test-IsUnderPath $FixtureSaveFull $ClashSaveRootFull",
    "source_workdir_guard": "Test-IsUnderPath $FixtureRootFull $SourceWorkDirFull",
    "source_overwrite_guard": "Refusing to overwrite source save",
    "non_promoting_proof_class": "non_natural_isolated_fixture",
    "promotion_ready_false": "promotion_ready = $false",
    "stable_stage_false": "stable_stage_should_change = $false",
    "seed_excludes_save_dir": "$SeedExcludedDirs = @('save')",
    "seed_workdir_copy": "Copy-Item -LiteralPath $_.FullName -Destination $FixtureRootFull -Recurse -Force",
    "copy_item_literal": "Copy-Item -LiteralPath $SourceSaveFull -Destination $FixtureSaveFull",
}

RISKY_VISIBLE_RE = re.compile(
    r"\b(?:Start-Process|SendInput|PostMessage|SetCursorPos|CopyFromScreen|powershell\.exe)\b",
    re.IGNORECASE,
)


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def line_numbers(text: str, needle: str | re.Pattern[str]) -> list[int]:
    lines: list[int] = []
    for index, line in enumerate(text.splitlines(), start=1):
        if isinstance(needle, str):
            if needle in line:
                lines.append(index)
        elif needle.search(line):
            lines.append(index)
    return lines


def first_line(text: str, needle: str | re.Pattern[str]) -> int | None:
    rows = line_numbers(text, needle)
    return rows[0] if rows else None


def build_guard(script: Path = DEFAULT_SCRIPT) -> dict[str, Any]:
    failures: list[str] = []
    marker_results: dict[str, bool] = {}
    text = ""
    if not script.exists():
        failures.append(f"missing script: {script}")
    else:
        text = script.read_text(encoding="utf-8-sig", errors="replace")

    for name, marker in REQUIRED_MARKERS.items():
        present = marker in text
        marker_results[name] = present
        if not present:
            failures.append(f"missing marker {name}: {marker}")

    dry_exit_line = first_line(text, "if (-not $Execute)")
    seed_copy_line = first_line(text, "Copy-Item -LiteralPath $_.FullName -Destination $FixtureRootFull -Recurse -Force")
    copy_line = first_line(text, "Copy-Item -LiteralPath $SourceSaveFull -Destination $FixtureSaveFull")
    if dry_exit_line is None:
        failures.append("missing dry-run exit gate before fixture copy")
    if seed_copy_line is None:
        failures.append("missing optional workdir seed Copy-Item")
    if copy_line is None:
        failures.append("missing final Copy-Item fixture write")
    if dry_exit_line is not None and seed_copy_line is not None and seed_copy_line <= dry_exit_line:
        failures.append("workdir seed Copy-Item appears before the dry-run exit gate")
    if dry_exit_line is not None and copy_line is not None and copy_line <= dry_exit_line:
        failures.append("Copy-Item appears before the dry-run exit gate")

    risky_lines = line_numbers(text, RISKY_VISIBLE_RE)
    if risky_lines:
        failures.append(f"script contains visible/runtime launcher APIs on lines {risky_lines}")

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "script": str(script),
        "markers": marker_results,
        "dry_run_exit_line": dry_exit_line,
        "seed_copy_line": seed_copy_line,
        "copy_line": copy_line,
        "risky_visible_lines": risky_lines,
        "failures": failures,
    }


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# Right-Bottom Slot Fixture Script Guard",
        "",
        f"- Status: {status_text(bool(guard.get('passed')))}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        f"- Script: `{guard['script']}`",
        f"- Dry-run exit line: `{guard.get('dry_run_exit_line')}`",
        f"- Seed copy line: `{guard.get('seed_copy_line')}`",
        f"- Copy line: `{guard.get('copy_line')}`",
        f"- Risky visible/runtime lines: `{guard.get('risky_visible_lines')}`",
        "",
        "## Markers",
        "",
    ]
    for name, passed in guard.get("markers", {}).items():
        lines.append(f"- `{name}`: `{status_text(bool(passed))}`")
    if guard.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, default=DEFAULT_SCRIPT)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    guard = build_guard(args.script)
    print(f"overall: {status_text(bool(guard.get('passed')))}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"script: {guard['script']}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")
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
