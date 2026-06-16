#!/usr/bin/env python3
"""Run the repo-only Python test sweep and write compact evidence.

The sweep is intentionally opt-in and repo-local. It launches Python child
processes for tools/test_*.py files, records pass/fail output, and does not
launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_JSON = Path("captures/current/repo-test-sweep-current.json")
DEFAULT_MD = Path("captures/current/repo-test-sweep-current.md")
RUNTIME_POLICY = (
    "repo-only Python test sweep; launches only Python child processes for "
    "tools/test_*.py and does not launch Clash95, CDB, wrappers, PowerShell "
    "harnesses, or visible windows"
)


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def resolve_under_root(root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return root / path


def discover_tests(tools_dir: Path, pattern: str, excludes: set[str]) -> list[Path]:
    if not tools_dir.exists():
        return []
    return [
        path
        for path in sorted(tools_dir.glob(pattern), key=lambda item: item.name.lower())
        if path.name not in excludes
    ]


def clipped(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def run_test(
    test_path: Path,
    *,
    root: Path,
    python_exe: str,
    timeout_sec: int,
    output_chars: int,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [python_exe, str(test_path)],
            cwd=str(root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_sec,
            check=False,
        )
        duration = time.monotonic() - started
        return {
            "name": test_path.name,
            "path": str(test_path.relative_to(root)).replace("/", "\\")
            if test_path.is_relative_to(root)
            else str(test_path),
            "passed": completed.returncode == 0,
            "exit_code": completed.returncode,
            "duration_sec": round(duration, 3),
            "stdout": clipped(completed.stdout, output_chars),
            "stderr": clipped(completed.stderr, output_chars),
        }
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        return {
            "name": test_path.name,
            "path": str(test_path.relative_to(root)).replace("/", "\\")
            if test_path.is_relative_to(root)
            else str(test_path),
            "passed": False,
            "exit_code": None,
            "duration_sec": round(duration, 3),
            "timed_out": True,
            "timeout_sec": timeout_sec,
            "stdout": clipped(exc.stdout or "", output_chars),
            "stderr": clipped(exc.stderr or "", output_chars),
        }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    tools_dir = resolve_under_root(root, args.tools_dir).resolve()
    excludes = {str(value) for value in args.exclude}
    tests = discover_tests(tools_dir, args.pattern, excludes)
    started = time.monotonic()
    rows = [
        run_test(
            test_path,
            root=root,
            python_exe=args.python,
            timeout_sec=args.per_test_timeout_sec,
            output_chars=args.output_chars,
        )
        for test_path in tests
    ]
    duration = time.monotonic() - started
    failures = [
        f"{row['name']} exited {row.get('exit_code')}"
        for row in rows
        if not row.get("passed")
    ]
    if not rows:
        failures.append(f"no tests matched {args.pattern} under {tools_dir}")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "root": str(root),
        "tools_dir": str(tools_dir),
        "pattern": args.pattern,
        "python": args.python,
        "per_test_timeout_sec": args.per_test_timeout_sec,
        "test_count": len(rows),
        "passed_count": sum(1 for row in rows if row.get("passed")),
        "failed_count": sum(1 for row in rows if not row.get("passed")),
        "duration_sec": round(duration, 3),
        "excluded_tests": sorted(excludes),
        "tests": rows,
        "failures": failures,
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Repo Test Sweep",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Python: `{report['python']}`",
        f"- Tests: `{report['passed_count']}/{report['test_count']}` passed",
        f"- Duration seconds: `{report['duration_sec']}`",
        "",
        "## Tests",
        "",
    ]
    for row in report["tests"]:
        status = status_text(bool(row["passed"]))
        lines.append(f"- {status} `{row['name']}` ({row['duration_sec']}s)")
    if report["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
        for row in report["tests"]:
            if row.get("passed"):
                continue
            lines.extend(["", f"### {row['name']}", ""])
            if row.get("stdout"):
                lines.extend(["```text", str(row["stdout"]).rstrip(), "```", ""])
            if row.get("stderr"):
                lines.extend(["```text", str(row["stderr"]).rstrip(), "```", ""])
    lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], json_path: Path | None, md_path: Path | None) -> None:
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    if md_path:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(to_markdown(report), encoding="ascii")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tools-dir", type=Path, default=Path("tools"))
    parser.add_argument("--pattern", default="test_*.py")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--per-test-timeout-sec", type=int, default=120)
    parser.add_argument("--output-chars", type=int, default=4000)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-markdown", type=Path)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    write_outputs(report, args.write_json, args.write_markdown)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"tests: {report['passed_count']}/{report['test_count']} passed")
    print(f"duration-sec: {report['duration_sec']}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
