#!/usr/bin/env python3
"""Fixture tests for castle_save_owner_flag_scan.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "castle_save_owner_flag_scan.py"
sys.path.insert(0, str(ROOT / "tools"))

import castle_save_owner_flag_scan as scan  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def make_record(
    *,
    x: int = 14,
    y: int = 20,
    owner: int = 0,
    byte_4: int = 2,
    flags_1a0: int = 0,
    flags_1a4: int = 0,
    byte_1a5: int = 0,
    byte_1b3: int = 0,
    byte_1bc: int = 0,
) -> bytes:
    record = bytearray(scan.RECORD_SIZE)
    record[0] = x
    record[1] = y
    record[2] = owner
    record[4] = byte_4
    record[5:14] = b"TestKeep\x00"
    record[0x1A0] = flags_1a0
    record[0x1A4] = flags_1a4
    record[0x1A5] = byte_1a5
    record[0x1B3] = byte_1b3
    record[0x1BC] = byte_1bc
    return bytes(record)


def make_save(path: Path, offset: int, records: list[bytes]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    block = bytearray(scan.RECORD_SIZE * scan.DEFAULT_RECORD_COUNT)
    for index, record in enumerate(records):
        start = index * scan.RECORD_SIZE
        block[start : start + scan.RECORD_SIZE] = record
    path.write_bytes(bytes(offset) + bytes(block) + b"\x00" * 16)
    return path


def test_scan_reports_no_eligible_block_without_failing(fixture: Path) -> None:
    saves = fixture / "save"
    offset = 128
    make_save(saves / "0.dat", offset, [make_record(x=14, y=20, owner=0, flags_1a0=0)])
    make_save(saves / "1.dat", offset, [make_record(x=90, y=7, owner=1, flags_1a0=0)])

    report = scan.build_report(saves, offset)
    assert report["passed"] is True, report
    assert report["summary"]["save_count"] == 2, report
    assert report["summary"]["candidate_block_count"] == 2, report
    assert report["summary"]["action_eligible_record_count"] == 0, report
    assert report["recommended_route_target"] is None, report
    assert "no installed save currently" in report["current_blocker"], report


def test_scan_detects_action_eligible_owner_flag(fixture: Path) -> None:
    saves = fixture / "save"
    offset = 256
    make_save(
        saves / "2.dat",
        offset,
        [
            make_record(x=14, y=20, owner=0, flags_1a0=0),
            make_record(x=90, y=7, owner=1, flags_1a0=0x02, byte_1bc=7),
        ],
    )

    report = scan.build_report(saves, offset)
    assert report["passed"] is True, report
    assert report["summary"]["action_eligible_save_count"] == 1, report
    assert report["summary"]["action_eligible_record_count"] == 1, report
    target = report["recommended_route_target"]
    assert target["save"].endswith("2.dat"), target
    assert target["record_index"] == 1, target
    assert target["flags_1a0_hex"] == "0x02", target
    assert target["action_eligible"] is True, target


def test_cli_writes_outputs_and_require_action_eligible_fails_closed(fixture: Path) -> None:
    saves = fixture / "save"
    offset = 384
    make_save(saves / "0.dat", offset, [make_record(flags_1a0=0)])
    out_json = fixture / "scan.json"
    out_md = fixture / "scan.md"

    run = run_script(
        "--saves-root",
        str(saves),
        "--known-offset",
        str(offset),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
    )
    assert run.returncode == 0, run.stdout + run.stderr
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["passed"] is True, payload
    assert payload["summary"]["action_eligible_record_count"] == 0, payload
    markdown = out_md.read_text(encoding="utf-8")
    assert "- Action-eligible records (`flags_1a0 & 0x02`): `0`" in markdown

    required = run_script(
        "--saves-root",
        str(saves),
        "--known-offset",
        str(offset),
        "--write-json",
        str(fixture / "required.json"),
        "--write-markdown",
        str(fixture / "required.md"),
        "--require-action-eligible",
    )
    assert required.returncode == 2, required.stdout + required.stderr
    assert "no action-eligible owner records found" in required.stderr


def test_missing_saves_root_fails_closed(fixture: Path) -> None:
    report = scan.build_report(fixture / "missing", 0)
    assert report["passed"] is False, report
    assert any("missing saves root" in failure for failure in report["failures"]), report

    run = run_script(
        "--saves-root",
        str(fixture / "missing"),
        "--write-json",
        str(fixture / "missing.json"),
        "--write-markdown",
        str(fixture / "missing.md"),
        "--require-pass",
    )
    assert run.returncode == 2, run.stdout + run.stderr


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "castle-save-owner-flag-scan-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True, exist_ok=True)
    try:
        test_scan_reports_no_eligible_block_without_failing(fixture / "none")
        test_scan_detects_action_eligible_owner_flag(fixture / "eligible")
        test_cli_writes_outputs_and_require_action_eligible_fails_closed(fixture / "cli")
        test_missing_saves_root_fails_closed(fixture / "missing")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("castle save owner-flag scan tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
