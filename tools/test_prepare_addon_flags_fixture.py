#!/usr/bin/env python3
"""Fixture tests for the addon_flags save-fixture editor.

These tests use a synthetic save so they run anywhere; they verify the offset
arithmetic, the single-bit edit, source immutability, and the safety guards.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "prepare_addon_flags_fixture.py"
sys.path.insert(0, str(ROOT / "tools"))

import prepare_addon_flags_fixture as fixture_tool  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def make_synthetic_save(path: Path, *, index: int, initial_addon: int = 0x00, owner: int = 0) -> int:
    """Write a synthetic save large enough to hold the flagged record.

    Returns the addon_flags file offset for ``index`` with default layout.
    """
    offset = fixture_tool.addon_flags_offset(
        index,
        header_size=fixture_tool.DEFAULT_HEADER_SIZE,
        records_base=fixture_tool.DEFAULT_RECORDS_BASE,
        record_stride=fixture_tool.DEFAULT_RECORD_STRIDE,
        addon_flags_offset_in_record=fixture_tool.DEFAULT_ADDON_FLAGS_OFFSET,
    )
    owner_offset = (
        fixture_tool.DEFAULT_HEADER_SIZE
        + fixture_tool.DEFAULT_RECORDS_BASE
        + index * fixture_tool.DEFAULT_RECORD_STRIDE
        + fixture_tool.DEFAULT_OWNER_OFFSET
    )
    size = offset + 4096
    data = bytearray(size)
    data[offset] = initial_addon
    data[owner_offset] = owner
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return offset


def test_offset_arithmetic() -> None:
    # Matches header + base + index*stride + addon offset, per the report.
    assert fixture_tool.addon_flags_offset(
        0,
        header_size=0x10,
        records_base=509674,
        record_stride=467,
        addon_flags_offset_in_record=416,
    ) == 0x10 + 509674 + 416
    assert fixture_tool.addon_flags_offset(
        7,
        header_size=0x10,
        records_base=509674,
        record_stride=467,
        addon_flags_offset_in_record=416,
    ) == 0x10 + 509674 + 7 * 467 + 416


def test_apply_sets_bit_and_preserves_source(fixture: Path) -> None:
    src = fixture / "src" / "5.dat"
    offset = make_synthetic_save(src, index=3, initial_addon=0x01, owner=0)
    src_bytes_before = src.read_bytes()
    out_dir = fixture / "out" / "save"

    run = run_script(
        "--source-save", str(src),
        "--out-dir", str(out_dir),
        "--save-basename", "0.dat",
        "--building-index", "3",
        "--allow-repo-output",
        "--execute",
        "--json",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(run.stdout)
    assert result["applied"] is True, result
    assert result["addon_flags_file_offset"] == offset, result
    assert result["byte_before"] == 0x01, result
    # 0x01 | 0x02 == 0x03 (bit set, existing bits preserved)
    assert result["byte_after"] == 0x03, result

    out_save = out_dir / "0.dat"
    out_bytes = out_save.read_bytes()
    assert out_bytes[offset] == 0x03, out_bytes[offset]
    # Only the one byte changed vs the source.
    diff = [i for i, (a, b) in enumerate(zip(src_bytes_before, out_bytes)) if a != b]
    assert diff == [offset], diff
    # Source save is untouched.
    assert src.read_bytes() == src_bytes_before


def test_idempotent_when_bit_already_set(fixture: Path) -> None:
    src = fixture / "src2" / "9.dat"
    make_synthetic_save(src, index=2, initial_addon=0x02, owner=0)
    out_dir = fixture / "out2" / "save"
    run = run_script(
        "--source-save", str(src),
        "--out-dir", str(out_dir),
        "--building-index", "2",
        "--allow-repo-output",
        "--execute",
        "--json",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(run.stdout)
    assert result["byte_before"] == 0x02 and result["byte_after"] == 0x02, result


def test_owner_mismatch_fails(fixture: Path) -> None:
    src = fixture / "src3" / "1.dat"
    make_synthetic_save(src, index=1, initial_addon=0x00, owner=2)
    out_dir = fixture / "out3" / "save"
    run = run_script(
        "--source-save", str(src),
        "--out-dir", str(out_dir),
        "--building-index", "1",
        "--require-owner", "0",
        "--allow-repo-output",
        "--execute",
        "--json",
    )
    assert run.returncode == 2, run.stdout + run.stderr
    result = json.loads(run.stdout)
    assert result["passed"] is False, result
    assert any("owner byte" in f for f in result["failures"]), result["failures"]
    # No output written on failure.
    assert not (out_dir / "0.dat").exists()


def test_rejects_repo_output_without_flag(fixture: Path) -> None:
    src = fixture / "src4" / "0.dat"
    make_synthetic_save(src, index=0, initial_addon=0x00, owner=0)
    # Target a path inside the repo without --allow-repo-output.
    repo_out = ROOT / "captures" / "current" / "_addon_fixture_should_not_write"
    run = run_script(
        "--source-save", str(src),
        "--out-dir", str(repo_out),
        "--building-index", "0",
        "--execute",
        "--json",
    )
    assert run.returncode == 2, run.stdout + run.stderr
    result = json.loads(run.stdout)
    assert any("inside the repository" in f for f in result["failures"]), result["failures"]
    assert not (repo_out / "0.dat").exists()


def test_rejects_live_save_dir(fixture: Path) -> None:
    src = fixture / "src5" / "0.dat"
    make_synthetic_save(src, index=0, initial_addon=0x00, owner=0)
    plan = fixture_tool.build_plan(
        fixture_tool.parse_args(
            [
                "--source-save", str(src),
                "--out-dir", "C:\\Clash\\save",
                "--building-index", "0",
            ]
        )
    )
    assert plan["passed"] is False, plan
    assert any("live Clash save directory" in f for f in plan["failures"]), plan["failures"]


def test_offset_beyond_save_fails(fixture: Path) -> None:
    # A too-small save makes the computed offset out of range.
    src = fixture / "src6" / "0.dat"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(bytes(1024))
    run = run_script(
        "--source-save", str(src),
        "--out-dir", str(fixture / "out6" / "save"),
        "--building-index", "0",
        "--allow-repo-output",
        "--execute",
        "--json",
    )
    assert run.returncode == 2, run.stdout + run.stderr
    result = json.loads(run.stdout)
    assert any("beyond the save size" in f for f in result["failures"]), result["failures"]


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "addon-flags-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_offset_arithmetic()
        test_apply_sets_bit_and_preserves_source(fixture)
        test_idempotent_when_bit_already_set(fixture)
        test_owner_mismatch_fails(fixture)
        test_rejects_repo_output_without_flag(fixture)
        test_rejects_live_save_dir(fixture)
        test_offset_beyond_save_fails(fixture)
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("addon_flags fixture tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
