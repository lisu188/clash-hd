"""Repo-only battle HD stage, PE append, and geometry boundary fixtures."""

import struct
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "patcher"))
import patch_clash95_hd as patcher
from battle_hd_layout import BATTLE_LAYOUT as layout
from battle_hd_section import (SOURCE_SIZE, SECTION_SIZE, SECTION_RVA,
                              section_records, validate_installation, validate_spans)


def raises(kind, callback):
    try:
        callback()
    except kind:
        return
    raise AssertionError(f"expected {kind.__name__}")


def test_screen_boundaries():
    for point, expected in [((32, 136), (0, 0)), ((1119, 583), (16, 6)),
                            ((544, 200), (8, 1)), ((1056, 136), (16, 0))]:
        assert layout.cell_at(*point, 20) == expected
    for point in [(31, 136), (32, 135), (1120, 136), (32, 584), (1279, 490),
                  (0, 0), (1280, 720), (-1, -1), (0x7fffffff, 200)]:
        assert layout.cell_at(*point, 20) is None, point
    assert layout.cell_at(1119, 583, 20, 3) == (19, 6)
    assert layout.cell_at(480, 136, 7) is None
    assert layout.cell_at(479, 583, 7) == (6, 6)
    for columns, right in [(7, 0), (17, 0), (20, 3)]:
        assert layout.clamp_camera(-100, columns) == 0
        assert layout.clamp_camera(100, columns) == right
        assert layout.recenter(columns - 1, columns, 0) == right
    assert layout.recenter(8, 20, 0) == 0


def test_stage_isolation():
    stage = patcher.BATTLE_HD_STAGE
    selected = patcher.select_patches_for(stage, patcher.parse_resolution("1280x720"))
    validate_spans(selected)
    groups = {patch.group for patch in selected}
    assert not groups & {"battle-ui-center-present-wrapper", "battle-grid-centered-input", "battle-ui-centered-input"}
    stable = patcher.select_patches(patcher.DEFAULT_STAGE)
    assert not any(patch.group.startswith("battle-hd-") for patch in stable)
    assert not any(patch.group.startswith("battle-hd-") for patch in patcher.PATCHES)
    for resolution in ("800x600", "1024x768", "1280x960", "1920x1080"):
        raises(patcher.ResolutionNotSupportedError, lambda: patcher.select_patches_for(stage, patcher.parse_resolution(resolution)))
    # The stage cannot silently return an incomplete legacy selection.
    raises(patcher.ResolutionNotSupportedError, lambda: patcher.select_patches(stage))
    raises(SystemExit, lambda: patcher.validate_input(bytes(SOURCE_SIZE), selected))
    raises(SystemExit, lambda: patcher.apply_patches(bytes(SOURCE_SIZE), selected))


def test_section_contract():
    records = [patcher.Patch(*record) for record in section_records(b"\xc3", b"\x90\xc3")]
    validate_spans(records)
    append = next(patch for patch in records if patch.offset == SOURCE_SIZE)
    assert append.old == b"" and len(append.new) == SECTION_SIZE
    assert append.new[0] == 0xc3 and append.new[0x4000:0x4002] == b"\x90\xc3"
    header = next(patch.new for patch in records if patch.offset == 0x280)
    name, virtual_size, rva, raw_size, raw_offset, _, _, _, _, flags = struct.unpack("<8sIIIIIIHHI", header)
    assert name.rstrip(b"\0") == b".btlhd"
    assert (virtual_size, rva, raw_size, raw_offset) == (SECTION_SIZE, SECTION_RVA, SECTION_SIZE, SOURCE_SIZE)
    assert flags & 0x60000020 == 0x60000020
    raises(ValueError, lambda: section_records(b"x" * 0x4001, b"x"))
    raises(ValueError, lambda: section_records(b"x", b"x" * 0x8001))
    raises(ValueError, lambda: validate_spans([replace(append, offset=SOURCE_SIZE + 1)]))
    raises(ValueError, lambda: validate_spans([replace(append, old_hex="00")]))
    raises(ValueError, lambda: validate_spans(records + [records[0]]))


def test_installation_requires_complete_audited_stage():
    selected = patcher.select_patches_for(patcher.BATTLE_HD_STAGE, patcher.parse_resolution("1280x720"))
    validate_installation(selected, selected)
    # Ordering and rationale text have no effect on the installed image.
    validate_installation([replace(patch, note="reviewed fixture") for patch in reversed(selected)], selected)
    hook = next(patch for patch in selected if patch.group == "battle-hd-viewport")
    append = next(patch for patch in selected if patch.offset == SOURCE_SIZE)
    headers = [patch for patch in selected if patch.group == "battle-hd-section" and patch is not append]
    base = next(patch for patch in selected if not patch.group.startswith("battle-hd-"))
    missing_base = [patch for patch in selected if patch is not base]
    invalid_selections = (
        [hook], headers, [append], missing_base, patcher.battle_hd_patches(),
        [patch for patch in selected if patch is not append],
        selected + [selected[0]],
    )
    for invalid in invalid_selections:
        raises(ValueError, lambda: validate_installation(invalid, selected))
    for original in (hook, append, headers[0], base):
        changed = bytes([original.new[0] ^ 1]) + original.new[1:]
        tampered = [replace(patch, new_hex=changed.hex()) if patch is original else patch for patch in selected]
        raises(ValueError, lambda: validate_installation(tampered, selected))


if __name__ == "__main__":
    test_screen_boundaries()
    test_stage_isolation()
    test_section_contract()
    test_installation_requires_complete_audited_stage()
    print("battle HD stage, geometry and PE section tests passed")
