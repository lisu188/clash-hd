#!/usr/bin/env python3
"""Verify proprietary executable artifacts are absent from the repository.

This is a repo-only guard. It reads the filesystem and git metadata, but does
not launch Clash95, CDB, wrappers, or any visible GUI process.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = Path("captures/current/exe-artifact-guard-current.json")
DEFAULT_MD = Path("captures/current/exe-artifact-guard-current.md")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def repo_relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("/", "\\")


def filesystem_exes() -> list[str]:
    found: list[str] = []
    for path in REPO_ROOT.rglob("*.exe"):
        if ".git" in path.relative_to(REPO_ROOT).parts:
            continue
        found.append(repo_relative(path))
    return sorted(found)


def git_nul_lines(stdout: str) -> list[str]:
    return sorted(part for part in stdout.split("\0") if part)


def git_status_lines(stdout: str) -> list[str]:
    return [line for line in stdout.splitlines() if line.strip()]


def classify_status(lines: list[str]) -> tuple[list[str], list[str]]:
    allowed_deletions: list[str] = []
    disallowed: list[str] = []
    for line in lines:
        status = line[:2]
        path = line[3:] if len(line) > 3 else ""
        if status == "D ":
            allowed_deletions.append(path)
        else:
            disallowed.append(line)
    return sorted(allowed_deletions), disallowed


def root_exe_ignore_present(gitignore: Path) -> bool:
    if not gitignore.exists():
        return False
    for line in gitignore.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped == "/*.exe":
            return True
    return False


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    failures: list[str] = []
    filesystem = filesystem_exes()
    if filesystem:
        failures.append(f"repository contains executable files: {filesystem}")

    ls_files = run_git(["ls-files", "-z", "--", "*.exe"])
    tracked: list[str] = []
    if ls_files.returncode:
        failures.append(f"git ls-files failed: {ls_files.stderr.strip()}")
    else:
        tracked = git_nul_lines(ls_files.stdout)
        if tracked:
            failures.append(f"git index still tracks executable files: {tracked}")

    status = run_git(["status", "--porcelain=v1", "--", "*.exe"])
    status_lines: list[str] = []
    allowed_deletions: list[str] = []
    disallowed_status: list[str] = []
    if status.returncode:
        failures.append(f"git status failed: {status.stderr.strip()}")
    else:
        status_lines = git_status_lines(status.stdout)
        allowed_deletions, disallowed_status = classify_status(status_lines)
        if disallowed_status:
            failures.append(f"executable git status has disallowed records: {disallowed_status}")

    gitignore = args.gitignore
    ignore_ok = root_exe_ignore_present(gitignore)
    if not ignore_ok:
        failures.append(f"{gitignore} is missing root-level executable ignore pattern /*.exe")

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": "repo-only; does not launch Clash95, CDB, wrappers, or visible windows",
        "filesystem_exes": filesystem,
        "tracked_exes": tracked,
        "exe_status_lines": status_lines,
        "allowed_staged_deletions": allowed_deletions,
        "disallowed_status_lines": disallowed_status,
        "root_exe_ignore_present": ignore_ok,
        "gitignore": str(gitignore),
        "failures": failures,
    }


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(guard['passed'])}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"filesystem-exes: {len(guard['filesystem_exes'])}")
    print(f"tracked-exes: {len(guard['tracked_exes'])}")
    print(f"allowed-staged-deletions: {len(guard['allowed_staged_deletions'])}")
    print(f"root-exe-ignore-present: {guard['root_exe_ignore_present']}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# Executable Artifact Guard",
        "",
        f"- Overall: {status_text(guard['passed'])}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Filesystem `.exe` files: `{len(guard['filesystem_exes'])}`",
        f"- Git-index `.exe` files: `{len(guard['tracked_exes'])}`",
        f"- Allowed staged `.exe` deletions: `{len(guard['allowed_staged_deletions'])}`",
        f"- Root `.exe` ignore present: `{guard['root_exe_ignore_present']}`",
        "",
        "## Allowed Staged Deletions",
        "",
    ]
    if guard["allowed_staged_deletions"]:
        lines.extend(f"- `{path}`" for path in guard["allowed_staged_deletions"])
    else:
        lines.append("- None")
    if guard["filesystem_exes"]:
        lines.extend(["", "## Filesystem Executables", ""])
        lines.extend(f"- `{path}`" for path in guard["filesystem_exes"])
    if guard["tracked_exes"]:
        lines.extend(["", "## Tracked Executables", ""])
        lines.extend(f"- `{path}`" for path in guard["tracked_exes"])
    if guard["disallowed_status_lines"]:
        lines.extend(["", "## Disallowed Git Status Records", ""])
        lines.extend(f"- `{line}`" for line in guard["disallowed_status_lines"])
    if guard["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gitignore", type=Path, default=Path(".gitignore"))
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
