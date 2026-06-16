#!/usr/bin/env python3
"""Fixture tests for repo_test_sweep.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "repo_test_sweep.py"
sys.path.insert(0, str(ROOT / "tools"))

import repo_test_sweep  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_script(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_build_report_records_pass_and_failure(fixture: Path) -> None:
    write(fixture / "tools" / "test_a_pass.py", "print('fixture pass')\n")
    write(fixture / "tools" / "test_b_fail.py", "import sys\nprint('fixture fail')\nsys.exit(3)\n")
    args = type(
        "Args",
        (),
        {
            "root": fixture,
            "tools_dir": Path("tools"),
            "pattern": "test_*.py",
            "exclude": [],
            "python": sys.executable,
            "per_test_timeout_sec": 30,
            "output_chars": 500,
        },
    )()
    report = repo_test_sweep.build_report(args)
    assert report["passed"] is False, report
    assert report["test_count"] == 2, report
    assert report["passed_count"] == 1, report
    assert report["failed_count"] == 1, report
    assert report["tests"][0]["name"] == "test_a_pass.py", report
    assert "test_b_fail.py exited 3" in report["failures"], report


def test_cli_writes_outputs_and_requires_pass(fixture: Path) -> None:
    write(fixture / "tools" / "test_fail.py", "import sys\nsys.exit(7)\n")
    out_json = fixture / "captures" / "current" / "sweep.json"
    out_md = fixture / "captures" / "current" / "sweep.md"
    result = run_script(
        fixture,
        "--root",
        str(fixture),
        "--tools-dir",
        "tools",
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert result.returncode == 2, result.stdout + result.stderr
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["passed"] is False, data
    assert data["failed_count"] == 1, data
    assert "Repo Test Sweep" in out_md.read_text(encoding="utf-8")


def test_no_tests_fails_closed(fixture: Path) -> None:
    (fixture / "tools").mkdir(parents=True)
    args = type(
        "Args",
        (),
        {
            "root": fixture,
            "tools_dir": Path("tools"),
            "pattern": "test_*.py",
            "exclude": [],
            "python": sys.executable,
            "per_test_timeout_sec": 30,
            "output_chars": 500,
        },
    )()
    report = repo_test_sweep.build_report(args)
    assert report["passed"] is False, report
    assert report["test_count"] == 0, report
    assert "no tests matched" in report["failures"][0], report


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "repo-test-sweep-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_build_report_records_pass_and_failure(fixture / "mixed")
        test_cli_writes_outputs_and_requires_pass(fixture / "cli")
        test_no_tests_fails_closed(fixture / "empty")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("repo test sweep tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
