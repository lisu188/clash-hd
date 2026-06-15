#!/usr/bin/env python3
"""Fixture tests for the battle command availability helper."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import battle_command_availability as availability  # noqa: E402


def test_parse_units_from_single_cdb_line() -> None:
    rows = availability.parse_units(
        "BATTLE_FORCE_UNIT idx=0 ptr=03e43f16 owner=0 xy=(14,22) first=5 status720=0 "
        "BATTLE_FORCE_UNIT idx=1 ptr=03e441eb owner=0 xy=(15,22) first=1 status720=0"
    )
    assert [row["idx"] for row in rows] == [0, 1], rows
    assert rows[0]["unit_type"] == 5, rows
    assert rows[1]["ptr"] == 0x03E441EB, rows


def test_availability_for_type_uses_pe_section_mapping() -> None:
    image_base = 0x00400000
    sections = [{"virtual_address": 0x000EC000, "raw_size": 0x40000, "raw_pointer": 0x100}]
    data = bytearray(0x40000)
    unit_type = 5
    avail_raw = availability.va_to_raw(
        availability.AVAILABILITY_BASE_VA + unit_type * availability.UNIT_TYPE_STRIDE,
        image_base,
        sections,
    )
    enabled_raw = availability.va_to_raw(
        availability.ENABLED_BASE_VA + unit_type * availability.UNIT_TYPE_STRIDE,
        image_base,
        sections,
    )
    data[avail_raw] = 8
    data[enabled_raw] = 0
    result = availability.availability_for_type(bytes(data), image_base, sections, unit_type)
    assert result["availability"] == 8, result
    assert result["enabled"] == 0, result
    assert result["availability_va"] == "0x00512736", result


def test_scan_availability_table_reports_enabled_types() -> None:
    image_base = 0x00400000
    sections = [{"virtual_address": 0x000EC000, "raw_size": 0x40000, "raw_pointer": 0x100}]
    data = bytearray(0x40000)
    type_8_enabled = availability.va_to_raw(
        availability.ENABLED_BASE_VA + 8 * availability.UNIT_TYPE_STRIDE,
        image_base,
        sections,
    )
    data[type_8_enabled] = 3
    rows = availability.scan_availability_table(bytes(data), image_base, sections, 10)
    enabled = [row for row in rows if row["enabled"]]
    assert [row["unit_type"] for row in enabled] == [8], rows
    assert enabled[0]["enabled"] == 3, enabled


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "battle-command-availability-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_parse_units_from_single_cdb_line()
        test_availability_for_type_uses_pe_section_mapping()
        test_scan_availability_table_reports_enabled_types()
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("battle command availability tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
