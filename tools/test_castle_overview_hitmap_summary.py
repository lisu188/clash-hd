#!/usr/bin/env python3
"""Fixture tests for the castle overview raw hitmap summary parser."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "castle_overview_hitmap_summary.py"
sys.path.insert(0, str(ROOT / "tools"))

import castle_overview_hitmap_summary  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_raw(path: Path, width: int, height: int, points: dict[tuple[int, int], int]) -> Path:
    data = bytearray(width * height)
    for (x, y), raw in points.items():
        data[y * width + x] = raw
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def all_catalog_points() -> dict[tuple[int, int], int]:
    return {
        (1, 1): 0xF8,
        (3, 2): 0xF8,
        (4, 1): 0xFA,
        (5, 1): 0xFB,
        (6, 1): 0xFC,
        (7, 1): 0xFD,
        (0, 3): 0xFE,
        (1, 3): 0xFF,
    }


def test_summarize_maps_raw_ids_and_coordinates(fixture: Path) -> None:
    raw = write_raw(fixture / "hitmap.raw", 8, 4, all_catalog_points())
    summary = castle_overview_hitmap_summary.summarize(raw, 8, 4)
    assert summary["present_raw_ids"] == ["0xF8", "0xFA", "0xFB", "0xFC", "0xFD", "0xFE", "0xFF"], summary
    assert summary["absent_catalog_raw_ids"] == [], summary
    value_f8 = summary["values"]["0xF8"]
    assert value_f8["command"] == 0x86, value_f8
    assert value_f8["count"] == 2, value_f8
    assert value_f8["bbox"] == [1, 1, 3, 2], value_f8
    assert value_f8["first_native"] == [1, 1], value_f8
    assert value_f8["first_displayed"] == [81, 61], value_f8
    assert summary["values"]["0xFA"]["command"] == 0x99, summary
    assert summary["values"]["0xF9"]["command"] is None, summary


def test_cli_required_flags_pass_and_write_outputs(fixture: Path) -> None:
    raw = write_raw(fixture / "hitmap.raw", 8, 4, all_catalog_points())
    out_json = fixture / "summary.json"
    out_md = fixture / "summary.md"
    run = run_script(
        str(raw),
        "--width",
        "8",
        "--height",
        "4",
        "--require-present",
        "0xFA",
        "--require-present",
        "0xFD",
        "--require-absent",
        "0xF9",
        "--write-json",
        str(out_json),
        "--write-md",
        str(out_md),
    )
    assert run.returncode == 0, run.stdout + run.stderr
    written = json.loads(out_json.read_text(encoding="utf-8"))
    assert "0xFA" in written["present_raw_ids"], written
    markdown = out_md.read_text(encoding="utf-8")
    assert "- Present raw IDs: 0xF8, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF" in markdown


def test_cli_required_flags_fail_closed_and_size_errors(fixture: Path) -> None:
    sparse = write_raw(fixture / "sparse.raw", 8, 4, {(1, 1): 0xF8, (0, 3): 0xFE, (1, 3): 0xFF})
    missing_present = run_script(str(sparse), "--width", "8", "--height", "4", "--require-present", "0xFA")
    assert missing_present.returncode == 2, missing_present.stdout + missing_present.stderr

    present_when_absent_required = run_script(
        str(sparse),
        "--width",
        "8",
        "--height",
        "4",
        "--require-absent",
        "0xFE",
    )
    assert present_when_absent_required.returncode == 2, (
        present_when_absent_required.stdout + present_when_absent_required.stderr
    )

    try:
        castle_overview_hitmap_summary.summarize(sparse, 7, 4)
    except ValueError as exc:
        assert "expected 28 bytes" in str(exc)
    else:
        raise AssertionError("summarize should reject a raw dump with the wrong dimensions")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "castle-overview-hitmap-summary-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_summarize_maps_raw_ids_and_coordinates(fixture / "parse")
        test_cli_required_flags_pass_and_write_outputs(fixture / "cli-pass")
        test_cli_required_flags_fail_closed_and_size_errors(fixture / "cli-fail")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("castle overview hitmap summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
