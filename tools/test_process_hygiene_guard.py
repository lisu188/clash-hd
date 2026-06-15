#!/usr/bin/env python3
"""Fixture tests for the process hygiene guard."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "process_hygiene_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import process_hygiene_guard  # noqa: E402


SnapshotFn = Callable[[], tuple[list[dict[str, str]], int, str]]


@contextmanager
def patched_snapshot(fn: SnapshotFn) -> Iterator[None]:
    original = process_hygiene_guard.process_snapshot_rows
    process_hygiene_guard.process_snapshot_rows = fn
    try:
        yield
    finally:
        process_hygiene_guard.process_snapshot_rows = original


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def row(name: str, pid: int = 100, parent: int = 1) -> dict[str, str]:
    return {
        "image_name": name,
        "pid": str(pid),
        "parent_pid": str(parent),
        "thread_count": "1",
        "session_number": "1",
    }


def args_for() -> argparse.Namespace:
    return argparse.Namespace(exact_name=["cdb.exe"], prefix=["clash95"])


def test_guard_passes_without_target_processes() -> None:
    with patched_snapshot(lambda: ([row("python.exe"), row("explorer.exe")], 0, "")):
        guard = process_hygiene_guard.build_guard(args_for())
    assert guard["passed"] is True, guard
    assert guard["matching_process_count"] == 0, guard
    assert not guard["failures"], guard


def test_guard_rejects_exact_and_prefix_targets() -> None:
    rows = [
        row("CDB.EXE", pid=10),
        row("clash95_hd_candidate.exe", pid=11),
        row("not-clash95.exe", pid=12),
    ]
    with patched_snapshot(lambda: (rows, 0, "")):
        guard = process_hygiene_guard.build_guard(args_for())
    assert guard["passed"] is False, guard
    assert guard["matching_process_count"] == 2, guard
    assert any("CDB.EXE pid=10" in failure for failure in guard["failures"]), guard
    assert any("clash95_hd_candidate.exe pid=11" in failure for failure in guard["failures"]), guard


def test_guard_rejects_snapshot_failure() -> None:
    with patched_snapshot(lambda: ([], 5, "snapshot fixture failure")):
        guard = process_hygiene_guard.build_guard(args_for())
    assert guard["passed"] is False, guard
    assert guard["inspection_returncode"] == 5, guard
    assert any("snapshot fixture failure" in failure for failure in guard["failures"]), guard


def test_target_matching_is_case_insensitive() -> None:
    assert process_hygiene_guard.is_target_process("CDB.EXE", ("cdb.exe",), ("clash95",))
    assert process_hygiene_guard.is_target_process("Clash95_HD.exe", ("cdb.exe",), ("clash95",))
    assert not process_hygiene_guard.is_target_process("notclash95.exe", ("cdb.exe",), ("clash95",))


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    out_json = fixture / "process-hygiene.json"
    out_md = fixture / "process-hygiene.md"
    good = run_script(
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good.returncode == 0, good.stdout + good.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

    python_image = Path(sys.executable).name
    bad_json = fixture / "bad-process-hygiene.json"
    bad_md = fixture / "bad-process-hygiene.md"
    bad = run_script(
        "--exact-name",
        python_image,
        "--write-json",
        str(bad_json),
        "--write-markdown",
        str(bad_md),
        "--require-pass",
    )
    assert bad.returncode == 2, bad.stdout + bad.stderr
    assert json.loads(bad_json.read_text(encoding="utf-8"))["passed"] is False
    assert "- Overall: FAIL" in bad_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "process-hygiene-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_guard_passes_without_target_processes()
        test_guard_rejects_exact_and_prefix_targets()
        test_guard_rejects_snapshot_failure()
        test_target_matching_is_case_insensitive()
        test_cli_writes_outputs_and_fails_closed(fixture)
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("process hygiene guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
