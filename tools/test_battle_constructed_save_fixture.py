#!/usr/bin/env python3
"""Fixture tests for the constructed battle save helper."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import battle_constructed_save_fixture as fixture  # noqa: E402
import battle_save_unit_inventory as inventory  # noqa: E402


def make_save(unit_type: int = 5) -> bytes:
    data = bytearray(inventory.SAVE_UNIT_BASE_OFFSET)
    record = bytearray(inventory.UNIT_RECORD_STRIDE)
    record[0:2] = (14).to_bytes(2, "little")
    record[2:4] = (22).to_bytes(2, "little")
    record[4] = 0
    record[inventory.TYPE_OFFSET : inventory.TYPE_OFFSET + 2] = unit_type.to_bytes(2, "little")
    data.extend(record)
    return bytes(data)


def test_patch_unit_type_changes_only_type_field() -> None:
    source = make_save(5)
    patched = fixture.patch_unit_type(source, unit_index=0, target_unit_type=8)
    offset = fixture.unit_type_offset(0)
    assert source[offset : offset + 2] == (5).to_bytes(2, "little")
    assert patched[offset : offset + 2] == (8).to_bytes(2, "little")
    assert patched[:offset] == source[:offset]
    assert patched[offset + 2 :] == source[offset + 2 :]


def test_patch_unit_type_rejects_missing_record() -> None:
    try:
        fixture.patch_unit_type(b"short", unit_index=0, target_unit_type=8)
    except ValueError as exc:
        assert "outside save data" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_repo_output_guard_blocks_default_repo_write() -> None:
    repo = ROOT
    output = ROOT / ".codex-loop" / "tmp-tests" / "constructed-save" / "0.dat"
    assert fixture.path_is_under(output, repo)


def run_tests() -> None:
    tmp = ROOT / ".codex-loop" / "tmp-tests" / "constructed-save"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    try:
        test_patch_unit_type_changes_only_type_field()
        test_patch_unit_type_rejects_missing_record()
        test_repo_output_guard_blocks_default_repo_write()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    run_tests()
    print("battle constructed save fixture tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
