#!/usr/bin/env python3
"""Fixture tests for the castle owner records summary parser."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "castle_owner_records_summary.py"
sys.path.insert(0, str(ROOT / "tools"))

import castle_owner_records_summary  # noqa: E402


RECORD_SIZE = castle_owner_records_summary.RECORD_SIZE


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
    x: int = 0,
    y: int = 0,
    owner: int = 0,
    byte_4: int = 0,
    flags_1a0: int = 0,
    flags_1a4: int = 0,
    byte_1a5: int = 0,
    word_1ae: int = 0,
    byte_1b3: int = 0,
    dword_1b6: int = 0,
    byte_1bc: int = 0,
) -> bytes:
    record = bytearray(RECORD_SIZE)
    record[0] = x
    record[1] = y
    record[2] = owner
    record[4] = byte_4
    record[0x1A0] = flags_1a0
    record[0x1A4] = flags_1a4
    record[0x1A5] = byte_1a5
    record[0x1AE:0x1B0] = word_1ae.to_bytes(2, "little")
    record[0x1B3] = byte_1b3
    record[0x1B6:0x1BA] = dword_1b6.to_bytes(4, "little")
    record[0x1BC] = byte_1bc
    return bytes(record)


def write_records(path: Path, records: list[bytes]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(records))
    return path


def test_summarize_classifies_active_retired_and_interesting(fixture: Path) -> None:
    raw = write_records(
        fixture / "owners.raw",
        [
            make_record(x=14, y=20, owner=0, byte_4=2, byte_1bc=1),
            make_record(x=90, y=7, owner=1, byte_4=0xFF, byte_1bc=1),
            make_record(x=60, y=46, owner=2, byte_4=1, flags_1a0=0x1F, byte_1a5=3),
        ],
    )
    summary = castle_owner_records_summary.summarize(raw, 3)
    assert summary["record_count"] == 3, summary
    assert len(summary["nonempty_records"]) == 3, summary
    assert [row["index"] for row in summary["active_records"]] == [0, 2], summary
    assert [row["index"] for row in summary["interesting_records"]] == [2], summary
    assert summary["flag_1a0_values"] == [0, 31], summary
    assert summary["flag_1a4_values"] == [0], summary
    assert summary["records"][2]["word_1ae"] == 0, summary


def test_cli_required_flags_pass_and_write_outputs(fixture: Path) -> None:
    raw = write_records(
        fixture / "owners.raw",
        [
            make_record(x=14, y=20, owner=0, byte_4=2, byte_1bc=1),
            make_record(x=90, y=7, owner=1, byte_4=0xFF, byte_1bc=1),
            bytes(RECORD_SIZE),
        ],
    )
    out_json = fixture / "summary.json"
    out_md = fixture / "summary.md"
    run = run_script(
        str(raw),
        "--count",
        "3",
        "--require-active",
        "--forbid-interesting",
        "--write-json",
        str(out_json),
        "--write-md",
        str(out_md),
    )
    assert run.returncode == 0, run.stdout + run.stderr
    written = json.loads(out_json.read_text(encoding="utf-8"))
    assert len(written["active_records"]) == 1, written
    assert len(written["interesting_records"]) == 0, written
    markdown = out_md.read_text(encoding="utf-8")
    assert "- Active records: `1`" in markdown
    assert "- Interesting records: `0`" in markdown


def test_cli_required_flags_fail_closed_and_size_errors(fixture: Path) -> None:
    no_active = write_records(
        fixture / "no-active.raw",
        [make_record(x=1, y=2, owner=0, byte_4=0xFF, byte_1bc=1), bytes(RECORD_SIZE)],
    )
    no_active_run = run_script(str(no_active), "--count", "2", "--require-active")
    assert no_active_run.returncode == 2, no_active_run.stdout + no_active_run.stderr

    no_interesting_run = run_script(str(no_active), "--count", "2", "--require-interesting")
    assert no_interesting_run.returncode == 2, no_interesting_run.stdout + no_interesting_run.stderr

    interesting = write_records(
        fixture / "interesting.raw",
        [make_record(x=3, y=4, owner=1, byte_4=1, flags_1a4=0x1F)],
    )
    forbid_run = run_script(str(interesting), "--count", "1", "--forbid-interesting")
    assert forbid_run.returncode == 2, forbid_run.stdout + forbid_run.stderr

    short_raw = fixture / "short.raw"
    short_raw.write_bytes(bytes(RECORD_SIZE - 1))
    try:
        castle_owner_records_summary.summarize(short_raw, 1)
    except ValueError as exc:
        assert "expected at least" in str(exc)
    else:
        raise AssertionError("summarize should reject a truncated owner-record dump")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "castle-owner-records-summary-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_summarize_classifies_active_retired_and_interesting(fixture / "parse")
        test_cli_required_flags_pass_and_write_outputs(fixture / "cli-pass")
        test_cli_required_flags_fail_closed_and_size_errors(fixture / "cli-fail")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("castle owner records summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
