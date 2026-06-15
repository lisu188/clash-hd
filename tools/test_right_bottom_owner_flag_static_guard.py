#!/usr/bin/env python3
"""Fixture tests for right_bottom_owner_flag_static_guard.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "right_bottom_owner_flag_static_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import right_bottom_owner_flag_static_guard as guard  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_fixture_exe(path: Path, *, drift_name: str | None = None) -> bytes:
    size = max(pattern.offset + len(pattern.expected) for pattern in guard.PATTERNS) + 16
    data = bytearray(b"\x00" * size)
    for pattern in guard.PATTERNS:
        data[pattern.offset : pattern.offset + len(pattern.expected)] = pattern.expected
        if pattern.name == drift_name:
            data[pattern.offset] ^= 0xFF
    digest = guard.sha256(bytes(data))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return digest


def test_static_guard_accepts_expected_patterns(fixture: Path) -> None:
    exe = fixture / "good.exe"
    digest = write_fixture_exe(exe)
    old_sha = guard.EXPECTED_SHA256
    guard.EXPECTED_SHA256 = digest
    try:
        report = guard.build_guard(exe)
    finally:
        guard.EXPECTED_SHA256 = old_sha
    assert report["passed"] is True, report
    assert report["summary"]["pattern_count"] == len(guard.PATTERNS), report
    assert report["summary"]["owner_globals_verified"] is True, report
    assert report["summary"]["action_bit2_gate_verified"] is True, report
    assert report["summary"]["owner_loop_bit_gates_verified"] is True, report


def test_static_guard_rejects_byte_drift(fixture: Path) -> None:
    exe = fixture / "drift.exe"
    digest = write_fixture_exe(exe, drift_name="action_4338e0_bit2_early_return")
    old_sha = guard.EXPECTED_SHA256
    guard.EXPECTED_SHA256 = digest
    try:
        report = guard.build_guard(exe)
    finally:
        guard.EXPECTED_SHA256 = old_sha
    assert report["passed"] is False, report
    assert any("action_4338e0_bit2_early_return" in failure for failure in report["failures"]), report


def test_static_guard_rejects_sha_drift(fixture: Path) -> None:
    exe = fixture / "sha.exe"
    write_fixture_exe(exe)
    old_sha = guard.EXPECTED_SHA256
    guard.EXPECTED_SHA256 = "0" * 64
    try:
        report = guard.build_guard(exe)
    finally:
        guard.EXPECTED_SHA256 = old_sha
    assert report["passed"] is False, report
    assert any("SHA-256" in failure for failure in report["failures"]), report


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    exe = fixture / "cli.exe"
    write_fixture_exe(exe)
    out_json = fixture / "guard.json"
    out_md = fixture / "guard.md"
    run = run_script(
        "--exe",
        str(exe),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
    )
    assert run.returncode == 0, run.stdout + run.stderr
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["passed"] is False, payload
    assert "SHA-256" in "\n".join(payload["failures"])
    assert "- Overall: FAIL" in out_md.read_text(encoding="utf-8")

    missing = run_script(
        "--exe",
        str(fixture / "missing.exe"),
        "--write-json",
        str(fixture / "missing.json"),
        "--write-markdown",
        str(fixture / "missing.md"),
        "--require-pass",
    )
    assert missing.returncode == 2, missing.stdout + missing.stderr


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "right-bottom-owner-flag-static-guard-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True, exist_ok=True)
    try:
        test_static_guard_accepts_expected_patterns(fixture / "pass")
        test_static_guard_rejects_byte_drift(fixture / "drift")
        test_static_guard_rejects_sha_drift(fixture / "sha")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("right-bottom owner-flag static guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
