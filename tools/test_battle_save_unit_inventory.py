#!/usr/bin/env python3
"""Fixture tests for read-only battle save unit inventory."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import battle_save_unit_inventory as inventory  # noqa: E402


def make_record(x: int, y: int, owner: int, unit_type: int) -> bytes:
    record = bytearray(inventory.UNIT_RECORD_STRIDE)
    record[0:2] = x.to_bytes(2, "little")
    record[2:4] = y.to_bytes(2, "little")
    record[4] = owner
    record[inventory.TYPE_OFFSET : inventory.TYPE_OFFSET + 2] = unit_type.to_bytes(2, "little")
    return bytes(record)


def test_parse_save_units_uses_shifted_save_offset() -> None:
    data = bytearray(inventory.SAVE_UNIT_BASE_OFFSET)
    data.extend(make_record(14, 22, 0, 5))
    data.extend(make_record(15, 22, 0, 1))
    rows = inventory.parse_save_units(bytes(data))
    assert [row["idx"] for row in rows] == [0, 1], rows
    assert rows[0]["save_offset"] == f"0x{inventory.SAVE_UNIT_BASE_OFFSET:08X}", rows
    assert rows[0]["unit_type"] == 5, rows


def test_parse_save_units_rejects_out_of_range_owner() -> None:
    data = bytearray(inventory.SAVE_UNIT_BASE_OFFSET)
    data.extend(make_record(14, 22, 9, 5))
    assert inventory.parse_save_units(bytes(data)) == []


def run_tests() -> None:
    test_parse_save_units_uses_shifted_save_offset()
    test_parse_save_units_rejects_out_of_range_owner()


def main() -> int:
    run_tests()
    print("battle save unit inventory tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
