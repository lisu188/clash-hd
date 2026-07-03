#!/usr/bin/env python3
"""Fixture tests for the right-bottom addon_flags save helper."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import right_bottom_addon_flags_fixture as fixture  # noqa: E402


def make_save(*, building_index: int = 0, flags: int = 0x00) -> bytes:
    """Build a minimal stock-sized save with one building record populated."""

    data = bytearray(fixture.EXPECTED_SAVE_SIZE)
    record = fixture.building_record_offset(building_index)
    data[record + fixture.OWNER_OFFSET] = 0  # player 0 owns it
    data[record + fixture.TYPE_OFFSET] = 7  # arbitrary building type
    data[fixture.addon_flags_offset(building_index)] = flags
    return bytes(data)


def test_offset_math_matches_disassembly_formula() -> None:
    # 16 + 509674 + 0*467 + 416
    assert fixture.addon_flags_offset(0) == 16 + 509674 + 416
    # 16 + 509674 + i*467 + 416 for an interior building
    assert fixture.addon_flags_offset(5) == 16 + 509674 + 5 * 467 + 416
    # Every addon_flags byte stays inside a stock-sized save.
    assert fixture.addon_flags_offset(fixture.BUILDING_RECORD_COUNT - 1) < fixture.EXPECTED_SAVE_SIZE


def test_set_production_flag_sets_only_target_byte() -> None:
    source = make_save(building_index=3, flags=0x00)
    patched = fixture.set_production_flag(source, building_index=3)
    offset = fixture.addon_flags_offset(3)
    assert not source[offset] & fixture.PRODUCTION_FLAG_BIT
    assert patched[offset] & fixture.PRODUCTION_FLAG_BIT
    assert patched[:offset] == source[:offset]
    assert patched[offset + 1 :] == source[offset + 1 :]


def test_set_production_flag_preserves_other_bits_and_is_idempotent() -> None:
    source = make_save(building_index=0, flags=0x08)  # unrelated upgrade bit set
    once = fixture.set_production_flag(source, building_index=0)
    twice = fixture.set_production_flag(once, building_index=0)
    offset = fixture.addon_flags_offset(0)
    assert once[offset] == 0x08 | fixture.PRODUCTION_FLAG_BIT
    assert twice == once  # idempotent


def test_set_production_flag_rejects_out_of_range_index() -> None:
    source = make_save()
    for bad in (-1, fixture.BUILDING_RECORD_COUNT):
        try:
            fixture.set_production_flag(source, building_index=bad)
        except ValueError as exc:
            assert "outside" in str(exc)
        else:
            raise AssertionError("expected ValueError for out-of-range index")


def test_set_production_flag_rejects_truncated_save() -> None:
    try:
        fixture.set_production_flag(b"short", building_index=0)
    except ValueError as exc:
        assert "outside save data" in str(exc)
    else:
        raise AssertionError("expected ValueError for truncated save")


def test_describe_building_reads_owner_and_type() -> None:
    source = make_save(building_index=2, flags=0x02)
    info = fixture.describe_building(source, building_index=2)
    assert info["owner_byte"] == 0
    assert info["type_byte"] == 7
    assert info["production_flag_set"] is True


def test_protected_save_dir_guard_blocks_clash_save() -> None:
    assert fixture.targets_protected_save_dir(Path(r"C:\Clash\save\0.dat"))
    assert not fixture.targets_protected_save_dir(Path(r"C:\ClashTests\rb-fixture\0.dat"))


def test_repo_output_guard_detects_repo_path() -> None:
    output = ROOT / ".codex-loop" / "tmp-tests" / "addon-flags" / "0.dat"
    assert fixture.path_is_under(output, ROOT)


def run_tests() -> None:
    tmp = ROOT / ".codex-loop" / "tmp-tests" / "addon-flags"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    try:
        test_offset_math_matches_disassembly_formula()
        test_set_production_flag_sets_only_target_byte()
        test_set_production_flag_preserves_other_bits_and_is_idempotent()
        test_set_production_flag_rejects_out_of_range_index()
        test_set_production_flag_rejects_truncated_save()
        test_describe_building_reads_owner_and_type()
        test_protected_save_dir_guard_blocks_clash_save()
        test_repo_output_guard_detects_repo_path()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    run_tests()
    print("right-bottom addon_flags fixture tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
