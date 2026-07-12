#!/usr/bin/env python3
"""Fixture tests for the right-bottom constructed save helper."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import right_bottom_constructed_save_fixture as fixture  # noqa: E402


def make_building_record(
    *,
    x: int = 10,
    y: int = 12,
    owner: int = 0,
    kind: int = 1,
    addon_flags: int = 0x00,
) -> bytes:
    record = bytearray(fixture.BUILDING_RECORD_STRIDE)
    record[0] = x
    record[1] = y
    record[2] = owner
    record[4] = kind
    record[fixture.ADDON_FLAGS_OFFSET] = addon_flags
    return bytes(record)


def make_save(records: list[bytes]) -> bytes:
    data = bytearray(fixture.BUILDING_BLOCK_FILE_OFFSET)
    for record in records:
        data.extend(record)
    remaining = fixture.BUILDING_RECORD_COUNT - len(records)
    data.extend(bytes(remaining * fixture.BUILDING_RECORD_STRIDE))
    return bytes(data)


def test_offset_formula_matches_disassembly_recipe() -> None:
    # Gate 1 recipe: 0x10 header + gameData 509674 + i*467 + 0x1A0.
    assert fixture.BUILDING_BLOCK_FILE_OFFSET == 0x10 + 509674
    assert fixture.BUILDING_RECORD_STRIDE == 467
    assert fixture.addon_flags_file_offset(0) == 0x10 + 509674 + 0x1A0
    assert fixture.addon_flags_file_offset(3) == 0x10 + 509674 + 3 * 467 + 0x1A0


def test_patch_addon_flags_sets_only_bit_0x02() -> None:
    source = make_save([make_building_record(addon_flags=0x08)])
    patched = fixture.patch_addon_flags(source, building_index=0)
    offset = fixture.addon_flags_file_offset(0)
    assert source[offset] == 0x08
    assert patched[offset] == 0x0A
    assert patched[:offset] == source[:offset]
    assert patched[offset + 1 :] == source[offset + 1 :]


def test_patch_addon_flags_rejects_out_of_range() -> None:
    source = make_save([make_building_record()])
    for bad_index in (-1, fixture.BUILDING_RECORD_COUNT):
        try:
            fixture.patch_addon_flags(source, building_index=bad_index)
        except ValueError as exc:
            assert "outside record table" in str(exc)
        else:
            raise AssertionError("expected ValueError")
    try:
        fixture.patch_addon_flags(b"short", building_index=0)
    except ValueError as exc:
        assert "outside save data" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_auto_selection_picks_first_player_owned_without_bit() -> None:
    records = [
        make_building_record(owner=2),  # enemy-owned, skipped
        make_building_record(owner=0, addon_flags=0x02),  # already eligible, skipped
        make_building_record(owner=0, x=20, y=21),  # selected
    ]
    buildings = fixture.parse_buildings(make_save(records))
    assert fixture.select_building_index(buildings, player_index=0) == 2
    assert fixture.select_building_index(buildings, player_index=5) is None


def test_build_summary_dry_run(tmp_dir: Path) -> None:
    source = tmp_dir / "0.dat"
    source.write_bytes(make_save([make_building_record(owner=0, addon_flags=0x00)]))
    summary = fixture.build_summary(source, building_index=None, player_index=0)
    assert summary["dry_run"] is True
    assert summary["wrote_output"] is False
    assert summary["building_index"] == 0
    assert summary["selection_mode"] == "auto"
    assert summary["old_addon_flags"] == "0x00"
    assert summary["new_addon_flags"] == "0x02"
    assert summary["action_eligible_after"] is True
    assert source.read_bytes()[fixture.addon_flags_file_offset(0)] == 0x00


def test_build_summary_writes_isolated_output(tmp_dir: Path) -> None:
    source = tmp_dir / "0.dat"
    source.write_bytes(make_save([make_building_record(owner=0)]))
    output = tmp_dir / "isolated" / "0.dat"
    summary = fixture.build_summary(
        source,
        building_index=0,
        player_index=0,
        output_save=output,
        repo_root=tmp_dir / "pretend-repo-root",
    )
    assert summary["wrote_output"] is True
    assert output.read_bytes()[fixture.addon_flags_file_offset(0)] == 0x02


def test_repo_output_guard_blocks_repo_write(tmp_dir: Path) -> None:
    source = tmp_dir / "0.dat"
    source.write_bytes(make_save([make_building_record(owner=0)]))
    output = ROOT / ".codex-loop" / "tmp-tests" / "right-bottom-save" / "guarded.dat"
    try:
        fixture.build_summary(
            source,
            building_index=0,
            player_index=0,
            output_save=output,
            repo_root=ROOT,
        )
    except ValueError as exc:
        assert "inside repository" in str(exc)
    else:
        raise AssertionError("expected ValueError")
    try:
        fixture.build_summary(
            source,
            building_index=0,
            player_index=0,
            output_save=source,
            allow_repo_output=True,
            repo_root=tmp_dir,
        )
    except ValueError as exc:
        assert "overwrite source save" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def run_tests() -> None:
    tmp = ROOT / ".codex-loop" / "tmp-tests" / "right-bottom-save"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    try:
        test_offset_formula_matches_disassembly_recipe()
        test_patch_addon_flags_sets_only_bit_0x02()
        test_patch_addon_flags_rejects_out_of_range()
        test_auto_selection_picks_first_player_owned_without_bit()
        test_build_summary_dry_run(tmp)
        test_build_summary_writes_isolated_output(tmp)
        test_repo_output_guard_blocks_repo_write(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    run_tests()
    print("right-bottom constructed save fixture tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
