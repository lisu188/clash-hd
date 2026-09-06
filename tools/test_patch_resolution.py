#!/usr/bin/env python3
"""Fixture tests for the patcher's resolution parameterization.

The backward-compatibility contract: the frozen legacy PATCHES table is the
byte-for-byte source of truth for 800x600, and the resolution generator must
reproduce it exactly at the legacy resolution before any other resolution is
trusted.
"""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPL_PATH = ROOT / "src" / "patcher" / "patch_clash95_hd.py"
SHIM_PATH = ROOT / "patch_clash95_hd.py"
sys.path.insert(0, str(ROOT / "tools"))

import hd_map_smoke_matrix  # noqa: E402
import patch_stage_report  # noqa: E402

_SPEC = importlib.util.spec_from_file_location("clash95_patch_resolution_impl", IMPL_PATH)
assert _SPEC is not None and _SPEC.loader is not None
impl = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = impl
_SPEC.loader.exec_module(impl)


# Pin of the frozen legacy table. Any edit to PATCHES must be deliberate:
# update this hash together with the archived-SHA reproduction check.
FROZEN_TABLE_SHA256 = "6683ee66851d23a28d856a8576e6b58c9b1285e0766bb592b9cdb0847bc8c55c"
FROZEN_STABLE_SELECTION_SHA256 = "1c334f12bcc3206ee98b239733689bdb6982b9ce7ab0007487e105e7d1f688f9"

# 4-byte value slots where more than one formula matches the legacy bytes at
# 800x600. Each entry records why the chosen formula is right; the audit test
# fails if a new coincidence appears without being acknowledged here.
KNOWN_COINCIDENCES = {
    ("EDGEX", "W-1"): (
        "799 is both the tile-grid right edge (32+64*12-1) and W-1 at 800x600; "
        "EDGEY=591 vs H-1=599 proves sub_418700 present rects end on the tile "
        "grid, so EDGEX is the correct X formula"
    ),
}


def canonical_table_hash() -> str:
    canon = "\n".join(
        f"{p.group}|{p.offset:06X}|{p.old_hex}|{p.new_hex}|{p.note}"
        for p in impl.PATCHES
    )
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def test_frozen_table_pin() -> None:
    assert canonical_table_hash() == FROZEN_TABLE_SHA256, (
        "legacy PATCHES table changed; update FROZEN_TABLE_SHA256 only after "
        "confirming archived candidate SHAs still reproduce"
    )


def test_dispatch_identity() -> None:
    assert impl.build_patches(impl.PROFILE_800) is impl.PATCHES


def test_golden_generation_at_legacy_resolution() -> None:
    generated = impl.generate_patches(impl.PROFILE_800)
    assert len(generated) == len(impl.PATCHES)
    for legacy, produced in zip(impl.PATCHES, generated):
        assert legacy == produced, (
            f"generator drifted at {legacy.group} 0x{legacy.offset:06X}: "
            f"{legacy.new_hex} != {produced.new_hex}"
        )


def test_profile_math() -> None:
    p800 = impl.PROFILE_800
    assert (p800.tiles_x, p800.tiles_y) == (12, 9)
    assert (p800.off_x, p800.off_y) == (80, 60)
    assert (p800.edge_x, p800.edge_y) == (799, 591)
    assert p800.edge_y != p800.max_y, "EDGEY must differ from H-1 at 800x600"
    assert (p800.partial_col_px, p800.partial_row_px) == (0, 8)

    expected = {
        "1024x768": ((15, 11), (192, 144), (991, 719), (32, 48)),
        "1280x720": ((19, 11), (320, 120), (1247, 719), (32, 0)),
        "1280x960": ((19, 14), (320, 240), (1247, 911), (32, 48)),
        "1920x1080": ((29, 16), (640, 300), (1887, 1039), (32, 40)),
    }
    for key, (tiles, off, edges, partial) in expected.items():
        profile = impl.parse_resolution(key)
        assert (profile.tiles_x, profile.tiles_y) == tiles, key
        assert (profile.off_x, profile.off_y) == off, key
        assert (profile.edge_x, profile.edge_y) == edges, key
        assert (profile.partial_col_px, profile.partial_row_px) == partial, key

    for bad in ("640x480", "800x601", "801x600", "abc", "800", "800x600x32"):
        try:
            impl.parse_resolution(bad)
        except impl.ResolutionError:
            continue
        raise AssertionError(f"parse_resolution accepted {bad!r}")


def test_menu_hitboxes_shift_by_centering_offset() -> None:
    entries = [p for p in impl.PATCHES if p.group == "menu-center-hitboxes"]
    assert len(entries) == 40, len(entries)
    for patch in entries:
        delta = int.from_bytes(patch.new, "little") - int.from_bytes(
            patch.old, "little"
        )
        assert delta in (80, 60), (hex(patch.offset), delta)
        recipe = impl.RECIPES[(patch.group, patch.offset)]
        assert recipe.kind == "old-plus"
        assert recipe.deltas == (("OFFX",) if delta == 80 else ("OFFY",))


def test_descriptor_anchor_shifts() -> None:
    entries = [
        p
        for p in impl.PATCHES
        if p.group == "right-bottom-action-descriptor-anchor" and len(p.old) == 8
    ]
    assert len(entries) == 8, len(entries)
    for patch in entries:
        for index, expected_delta in enumerate((160, 120)):
            old_value = int.from_bytes(patch.old[index * 4 : index * 4 + 4], "little")
            new_value = int.from_bytes(patch.new[index * 4 : index * 4 + 4], "little")
            assert new_value - old_value == expected_delta, hex(patch.offset)


def test_terrain_tooltip_bottom_center_recipes() -> None:
    entries = [p for p in impl.PATCHES if p.group == "terrain-tooltip-bottom-center"]
    assert len(entries) == 12, len(entries)
    assert {p.offset for p in entries} == {
        0x00A198,
        0x00A1A4,
        0x00A1A9,
        0x00AB94,
        0x00ABA0,
        0x00ABA5,
        0x01A5B3,
        0x01A5B8,
        0x01A5C2,
        0x01B022,
        0x01B027,
        0x01B031,
    }
    assert not ({0x02E055, 0x02E05A, 0x02E05F} & {p.offset for p in entries})
    for patch in entries:
        delta = int.from_bytes(patch.new, "little") - int.from_bytes(
            patch.old, "little"
        )
        recipe = impl.RECIPES[(patch.group, patch.offset)]
        assert recipe.kind == "old-plus"
        if delta == impl.PROFILE_800.off_x:
            assert recipe.deltas == ("OFFX",)
        else:
            assert delta == impl.PROFILE_800.shift_y
            assert recipe.deltas == ("SHIFTY",)

    generated = {
        p.offset: int.from_bytes(p.new, "little")
        for p in impl.generate_patches(impl.parse_resolution("1024x768"))
        if p.group == "terrain-tooltip-bottom-center"
    }
    assert generated[0x00A198] == 755
    assert generated[0x00A1A4] == 665
    assert generated[0x00A1A9] == 352


def test_selected_unit_command_panel_right_bottom_recipes() -> None:
    entries = [
        p
        for p in impl.PATCHES
        if p.group == "selected-unit-command-panel-right-bottom"
    ]
    assert len(entries) == 8, len(entries)
    clips = [p for p in entries if len(p.old) == 4]
    coords = [p for p in entries if len(p.old) == 8]
    assert {p.offset for p in clips} == {0x019165, 0x01918E}
    assert all(impl.RECIPES[(p.group, p.offset)].value == "W" for p in clips)
    assert [p.new_hex for p in coords] == [
        "6002000010020000",
        "a002000010020000",
        "e002000010020000",
        "6002000030020000",
        "a002000030020000",
        "e002000030020000",
    ]
    assert all(
        impl.RECIPES[(p.group, p.offset)].kind == "splice" for p in coords
    )

    generated = [
        p
        for p in impl.generate_patches(impl.parse_resolution("1024x768"))
        if p.group == "selected-unit-command-panel-right-bottom"
        and len(p.old) == 8
    ]
    assert [
        (
            int.from_bytes(p.new[:4], "little"),
            int.from_bytes(p.new[4:], "little"),
        )
        for p in generated
    ] == [
        (832, 696),
        (896, 696),
        (960, 696),
        (832, 728),
        (896, 728),
        (960, 728),
    ]

    stable = set(impl.STAGE_GROUPS[impl.DEFAULT_STAGE])
    assert "terrain-tooltip-bottom-center" not in stable
    assert "selected-unit-command-panel-right-bottom" not in stable
    assert set(impl.STAGE_GROUPS[impl.DEFAULT_STAGE + "-hdlayout"]) == stable | {
        "terrain-tooltip-bottom-center",
        "selected-unit-command-panel-right-bottom",
    }


def test_recipe_coverage_and_old_bytes_invariance() -> None:
    kinds = {
        "value": 0,
        "old-plus": 0,
        "fixed": 0,
        "splice": 0,
        "cave-template": 0,
        "cave-hook": 0,
    }
    profile = impl.parse_resolution("1920x1080")
    for patch in impl.PATCHES:
        if patch.group not in impl.PARAMETERIZED_GROUPS:
            continue
        recipe = impl.RECIPES.get((patch.group, patch.offset))
        assert recipe is not None, (patch.group, hex(patch.offset))
        kinds[recipe.kind] += 1
        produced = impl._apply_recipe(patch, recipe, profile)
        if recipe.kind == "cave-template":
            template = impl._CAVE_TEMPLATES[(patch.group, patch.offset)]
            if template.new_offset is not None:
                assert produced.offset == template.new_offset
                assert produced.old_hex == "00" * (len(template.template_hex) // 2)
            else:
                assert produced.offset == patch.offset
                assert len(produced.new) == len(patch.new)
            continue
        assert produced.offset == patch.offset
        assert produced.old_hex == patch.old_hex
        assert len(produced.new) == len(patch.new), (patch.group, hex(patch.offset))
    assert kinds == {
        "value": 67,
        "old-plus": 60,
        "fixed": 27,
        "splice": 21,
        "cave-template": 8,
        "cave-hook": 3,
    }, kinds


def decode_branch(data: bytes, offset: int, kind: str, base_va: int) -> int:
    if kind == "call":
        assert data[offset] == 0xE8, hex(offset)
        disp = int.from_bytes(data[offset + 1 : offset + 5], "little", signed=True)
        return base_va + offset + 5 + disp
    if kind == "jmp32":
        assert data[offset] == 0xE9, hex(offset)
        disp = int.from_bytes(data[offset + 1 : offset + 5], "little", signed=True)
        return base_va + offset + 5 + disp
    if kind == "jz32":
        assert data[offset : offset + 2] == b"\x0f\x84", hex(offset)
        disp = int.from_bytes(data[offset + 2 : offset + 6], "little", signed=True)
        return base_va + offset + 6 + disp
    if kind == "jcc8":
        assert data[offset] in (0x74, 0x75, 0x76, 0x77, 0xEB), hex(offset)
        disp = int.from_bytes(data[offset + 1 : offset + 2], "little", signed=True)
        return base_va + offset + 2 + disp
    raise AssertionError(kind)


def test_cave_templates() -> None:
    for key, template in impl._CAVE_TEMPLATES.items():
        legacy_patch = next(
            p for p in impl.PATCHES if (p.group, p.offset) == key
        )
        template_bytes = bytes.fromhex(template.template_hex)
        if template.new_offset is None:
            assert len(template_bytes) == len(legacy_patch.new), key
        else:
            assert len(template_bytes) == 96, key
            assert template.param_va == 0x51BC20, key

        # Branch tables verify against both static byte encodings.
        for offset, kind, target in template.legacy_branches:
            actual = decode_branch(legacy_patch.new, offset, kind, template.legacy_va)
            assert actual == target, (key, "legacy", hex(offset), hex(actual))
        for offset, kind, target in template.param_branches:
            actual = decode_branch(template_bytes, offset, kind, template.param_va)
            assert actual == target, (key, "param", hex(offset), hex(actual))

        # External targets (outside the cave span) must agree across variants.
        legacy_span = range(
            template.legacy_va, template.legacy_va + len(legacy_patch.new)
        )
        param_span = range(template.param_va, template.param_va + len(template_bytes))
        # Tiling introduces internal loop branches, but it must keep every
        # external call/return target and its multiplicity exactly unchanged.
        assert Counter(
            (kind, target) for _, kind, target in template.legacy_branches
            if target not in legacy_span
        ) == Counter(
            (kind, target) for _, kind, target in template.param_branches
            if target not in param_span
        ), key

        # Slots carry the 800x600 values in the template.
        for slot in template.slots:
            current = int.from_bytes(
                template_bytes[slot.at : slot.at + slot.width],
                "little",
                signed=slot.signed,
            )
            assert current == impl.FORMULAS[slot.value](impl.PROFILE_800), (
                key,
                slot.value,
            )

    # Relocated hooks aim at the relocated cave VA.
    hook = bytes.fromhex(impl._CAVE_HOOKS[("castle-ui-center-present", 0x0351A5)])
    target = decode_branch(hook, 0, "jmp32", 0x0351A5 + 0x400C00)
    assert target == 0x51BC20, hex(target)
    hook = bytes.fromhex(
        impl._CAVE_HOOKS[("castle-ui-center-present-wrapper", 0x0351AA)]
    )
    assert hook[0] == 0xBB and int.from_bytes(hook[1:5], "little") == 0x51BC20
    hook = bytes.fromhex(
        impl._CAVE_HOOKS[("castle-ui-center-present-wrapper", 0x0351DE)]
    )
    target = decode_branch(hook, 0, "call", 0x0351DE + 0x400C00)
    assert target == 0x51BC20, hex(target)


def test_presets_generate_full_tables() -> None:
    for key in impl.RESOLUTION_PRESETS:
        profile = impl.parse_resolution(key)
        table = impl.generate_patches(profile)
        assert len(table) == len(impl.PATCHES), key
        if key == "800x600":
            assert table == impl.PATCHES
            continue
        relocated = [p for p in table if p.offset == 0x119E20]
        assert len(relocated) == 2 and all(
            p.old_hex == "00" * 96 for p in relocated
        ), key
        for stage in impl.PARAMETERIZED_STAGES:
            spans = sorted(
                (p.offset, p.offset + len(p.new))
                for p in impl.select_patches_for(stage, profile)
            )
            for (s1, e1), (s2, e2) in zip(spans, spans[1:]):
                assert e1 <= s2, (key, stage, hex(s1), hex(s2))


def test_range_fail_closed() -> None:
    # TX=128 overflows the single-byte tile immediates: W = 32 + 64*128 + 0.
    wide = impl.ResolutionProfile(32 + 64 * 128, 600)
    tile_patch = next(
        p
        for p in impl.PATCHES
        if p.group == "main-loops"
        and impl.RECIPES[(p.group, p.offset)].value == "TX"
    )
    recipe = impl.RECIPES[(tile_patch.group, tile_patch.offset)]
    try:
        impl._apply_recipe(tile_patch, recipe, wide)
    except impl.ResolutionError:
        pass
    else:
        raise AssertionError("imm8 TX=128 must fail closed")


def test_stage_gating() -> None:
    profile = impl.parse_resolution("1024x768")
    try:
        impl.select_patches_for("display", profile)
    except impl.ResolutionNotSupportedError:
        pass
    else:
        raise AssertionError("legacy-only stages must refuse non-800 resolutions")

    for stage in impl.STAGE_GROUPS:
        assert not __import__("re").search(r"\d+x\d+", stage), (
            "resolution tokens must never enter stage-name space",
            stage,
        )

    for stage in impl.PARAMETERIZED_STAGES:
        assert stage in impl.STAGE_GROUPS, stage

    for stage in impl.STAGE_GROUPS:
        legacy_selection = impl.select_patches(stage)
        parameterized_selection = impl.select_patches_for(stage, impl.PROFILE_800)
        assert legacy_selection == parameterized_selection, stage


def test_combined_ui_validation_is_exact_frozen_union() -> None:
    stable_stage = "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch"
    assert impl.DEFAULT_STAGE == stable_stage
    stable_selection = impl.select_patches(stable_stage)
    stable_text = "\n".join(
        f"{p.group}|{p.offset:06X}|{p.old_hex}|{p.new_hex}|{p.note}" for p in stable_selection
    )
    assert hashlib.sha256(stable_text.encode("utf-8")).hexdigest() == FROZEN_STABLE_SELECTION_SHA256
    stage = stable_stage + "-combinedui-validation"
    expected_groups = set().union(*(
        set(impl.STAGE_GROUPS[stable_stage + suffix])
        for suffix in ("", "-hdlayout-framerestore", "-rightbottomcompose", "-castlecenter-all-battlecenter-inputprobe")
    ))
    expected_patches = [patch for patch in impl.PATCHES if patch.group in expected_groups]
    assert len(expected_groups) == 27
    assert len(expected_patches) == 166
    assert impl.STAGE_GROUPS[stage] == tuple(dict.fromkeys(p.group for p in expected_patches))
    selected = impl.select_patches_for(stage, impl.PROFILE_800)
    assert selected == expected_patches
    assert all(actual is expected for actual, expected in zip(selected, expected_patches))
    spans = sorted((patch.offset, patch.offset + len(patch.old)) for patch in selected)
    assert all(left_end <= right_start for (_, left_end), (right_start, _) in zip(spans, spans[1:]))
    assert stage in impl.PARAMETERIZED_STAGES
    for resolution in (*impl.RESOLUTION_PRESETS[1:], "800x604", "1600x900"):
        selected = impl.select_patches_for(stage, impl.parse_resolution(resolution))
        assert len(selected) == 166, resolution
        assert {p.group for p in selected} == expected_groups, resolution
        assert all((p.group, p.offset) in impl.RECIPES for p in expected_patches)


def trace_frame_restore_machine_code(data: bytes, present: int) -> dict:
    """Interpret only the x86 instructions used by the tiling cave.

    No native code or game runs. Render_FillRect is a callee-cleaned recording
    stub that deliberately clobbers every non-ESP register and both modeled
    flags. This tests the actual emitted stack/control-flow bytes, independently
    of the recipe's slot and branch metadata. Unknown instructions fail closed.
    """
    base = 0x51BE00
    eax, ecx, edx, ebx, esp, ebp, esi, edi = range(8)
    initial = [0x12340000 + index for index in range(8)]
    initial[esp], initial[ebp] = 0x900000, present
    regs = initial.copy()
    memory = {0x5202E0: 0x700000, initial[esp]: 0xBADCAFE}
    zf, cf = False, False
    pc = base
    calls, branches = [], set()

    def push(value: int) -> None:
        regs[esp] -= 4
        memory[regs[esp]] = value & 0xFFFFFFFF

    def pop() -> int:
        value = memory[regs[esp]]
        regs[esp] += 4
        return value

    def imm(at: int, size: int, signed: bool = False) -> int:
        return int.from_bytes(data[at:at + size], "little", signed=signed)

    for _ in range(100000):
        if pc in (0x4189A3, 0x4187B7):
            assert regs == initial, (regs, initial)
            assert memory[initial[esp]] == 0xBADCAFE
            assert zf == (present == 0)
            assert pc == (0x4189A3 if present == 0 else 0x4187B7)
            return {"calls": calls, "branches": branches}
        at = pc - base
        assert 0 <= at < len(data), hex(pc)
        op = data[at]
        if op == 0x60:  # PUSHAD saves the pre-instruction ESP in its fifth slot.
            before = regs.copy()
            for value in before:
                push(value)
            pc += 1
        elif op == 0x61:
            for index in reversed(range(8)):
                value = pop()
                if index != esp:
                    regs[index] = value
            pc += 1
        elif data[at:at + 4] == bytes.fromhex("8b7c2408"):
            regs[edi] = memory[regs[esp] + 8]
            pc += 4
        elif 0xB8 <= op <= 0xBF:
            regs[op - 0xB8] = imm(at + 1, 4)
            pc += 5
        elif 0x50 <= op <= 0x57:
            push(regs[op - 0x50])
            pc += 1
        elif op == 0x6A:
            push(imm(at + 1, 1, signed=True))
            pc += 2
        elif data[at:at + 2] == bytes.fromhex("8d80"):
            regs[eax] = (regs[eax] + imm(at + 2, 4, signed=True)) & 0xFFFFFFFF
            pc += 6
        elif op == 0xA1:
            regs[eax] = memory[imm(at + 1, 4)]
            pc += 5
        elif op in (0x89, 0x31, 0x85, 0x01, 0x29):
            modrm = data[at + 1]
            assert modrm >= 0xC0, (hex(pc), hex(modrm))
            src, dst = (modrm >> 3) & 7, modrm & 7
            left, right = regs[dst], regs[src]
            if op == 0x89:
                regs[dst] = right
            else:
                value = {0x31: left ^ right, 0x85: left & right,
                         0x01: left + right, 0x29: left - right}[op]
                zf = (value & 0xFFFFFFFF) == 0
                cf = left < right if op == 0x29 else value > 0xFFFFFFFF if op == 0x01 else False
                if op != 0x85:
                    regs[dst] = value & 0xFFFFFFFF
            pc += 2
        elif op == 0x3D or data[at:at + 2] == bytes.fromhex("83f8"):
            size = 5 if op == 0x3D else 3
            value = imm(at + 1, 4) if op == 0x3D else imm(at + 2, 1, signed=True) & 0xFFFFFFFF
            zf, cf = regs[eax] == value, regs[eax] < value
            pc += size
        elif op in (0x74, 0x75, 0x76):
            branches.add(at)
            take = {0x74: zf, 0x75: not zf, 0x76: cf or zf}[op]
            pc += 2 + (imm(at + 1, 1, signed=True) if take else 0)
        elif op == 0xE8:
            branches.add(at)
            assert pc + 5 + imm(at + 1, 4, signed=True) == 0x4024E0
            assert regs[eax] == 0x700000
            calls.append((regs[edx], regs[ebx], regs[ecx],
                          memory[regs[esp]], memory[regs[esp] + 4],
                          memory[regs[esp] + 8], memory[regs[esp] + 12]))
            regs[esp] += 16  # CALL/RET cancel, RET 16 consumes four arguments.
            for index in range(8):
                if index != esp:
                    regs[index] = 0xDEAD0000 + index
            zf, cf = True, True
            pc += 5
        elif data[at:at + 2] == bytes.fromhex("0f84"):
            branches.add(at)
            pc += 6 + (imm(at + 2, 4, signed=True) if zf else 0)
        elif op == 0xE9:
            branches.add(at)
            pc += 5 + imm(at + 1, 4, signed=True)
        else:
            raise AssertionError(f"unsupported frame-cave instruction at {pc:08X}: {data[at:at + 8].hex()}")
    raise AssertionError("frame-band loop did not terminate")


def assert_frame_restore_rectangles(data: bytes, width: int, height: int, present: int) -> set[int]:
    trace = trace_frame_restore_machine_code(data, present)
    expected = []
    targets = (0x700000, 0) if present else (0x700000,)
    # Independent geometry oracle: tile authentic source pixels, clip the
    # final tile, and cover exactly each HD gutter without touching terrain.
    for y in range(480, height, 120):
        bottom = 359 + min(120, height - y)
        expected.extend((target, 0, 360, 31, bottom, 0, y) for target in targets)
    for x in range(640, width, 160):
        right = 479 + min(160, width - x)
        expected.extend((target, 480, 0, right, 15, x, 0) for target in targets)
    assert trace["calls"] == expected, (width, height, present, trace["calls"], expected)
    for target, left, top, right, bottom, x, y in trace["calls"]:
        assert target in targets
        assert 0 <= left <= right < 640 and 0 <= top <= bottom < 480
        assert 0 <= x <= x + right - left < width
        assert 0 <= y <= y + bottom - top < height
        assert x + right - left < 32 or y + bottom - top < 16
    return trace["branches"]


def test_frame_restore_tiling_machine_code() -> None:
    key = ("frame-restore-bands", 0x11A000)
    legacy = next(p for p in impl.PATCHES if (p.group, p.offset) == key)
    template = impl._CAVE_TEMPLATES[key]
    assert len(legacy.old) == len(legacy.new) == 256
    assert legacy.old == bytes(256)
    assert bytes.fromhex(template.template_hex)[217:] == bytes(39)
    profiles = {impl.parse_resolution(key) for key in impl.RESOLUTION_PRESETS}
    profiles.update(impl.ResolutionProfile(width, 600) for width in range(800, 1122, 2))
    profiles.update(impl.ResolutionProfile(800, height) for height in range(600, 842, 2))
    profiles.update((impl.ResolutionProfile(3840, 2160), impl.ResolutionProfile(8222, 8206)))
    visited = set()
    for profile in profiles:
        # Exercise the new loop's minimum too, although production 800x600
        # deliberately dispatches to the frozen legacy bytes instead.
        patch = impl._apply_cave_template(legacy, profile)
        assert patch.old == legacy.old and patch.offset == legacy.offset
        assert len(patch.new) == 256
        for present in (0, 1, 0xFFFFFFFF):
            visited.update(assert_frame_restore_rectangles(patch.new, profile.width, profile.height, present))
    assert visited == {at for at, _, _ in template.param_branches}
    hook = next(p for p in impl.PATCHES if p.group == key[0] and p.offset == 0x17BAF)
    assert decode_branch(hook.new, 0, "jmp32", 0x4187AF) == template.param_va

    # The entire original 256-byte cave, including unused padding, must still
    # be verified as zero before writing any generated variant.
    generated = impl._apply_cave_template(legacy, impl.parse_resolution("1024x768"))
    original_region = bytes(legacy.offset + len(legacy.old))
    impl.validate_input(original_region, (generated,))
    corrupt_region = bytearray(original_region)
    corrupt_region[-1] = 1
    try:
        impl.validate_input(bytes(corrupt_region), (generated,))
    except SystemExit as exc:
        assert "byte validation failure" in str(exc)
    else:
        raise AssertionError("generated frame cave bypassed old-byte verification")

    # A wrong extension or reversed screen-present condition is detected by
    # the semantic oracle, not just by the frozen-template byte assertions.
    correct = impl._apply_cave_template(legacy, impl.parse_resolution("1024x768")).new
    for at, replacement in ((11, (289).to_bytes(4, "little")), (62, b"\x75")):
        bad = bytearray(correct)
        bad[at:at + len(replacement)] = replacement
        try:
            assert_frame_restore_rectangles(bytes(bad), 1024, 768, 1)
        except AssertionError:
            pass
        else:
            raise AssertionError("corrupt frame tiling escaped semantic checks")


def test_combined_custom_resolution_limits() -> None:
    stage = impl.DEFAULT_STAGE + "-combinedui-validation"
    for resolution in ("800x604", "802x602", "1600x900", "3840x2160", "8222x8206"):
        selected = impl.select_patches_for(stage, impl.parse_resolution(resolution))
        spans = sorted((p.offset, p.offset + len(p.new)) for p in selected)
        assert len(selected) == 166
        assert all(end <= following for (_, end), (following, _) in zip(spans, spans[1:])), resolution
    for resolution in ("8224x8206", "8222x8208", "32768x600", "800x601", "640x480"):
        try:
            impl.select_patches_for(stage, impl.parse_resolution(resolution))
        except impl.ResolutionError:
            pass
        else:
            raise AssertionError(f"combined validation bypassed existing resolution limits: {resolution}")


def test_coincidence_audit() -> None:
    """Every 4-byte value slot whose legacy bytes match >1 formula must be
    acknowledged in KNOWN_COINCIDENCES with a justification."""
    p800 = impl.PROFILE_800
    for (group, offset), formula in impl._VALUE_RECIPES.items():
        patch = next(
            p for p in impl.PATCHES if p.group == group and p.offset == offset
        )
        width = len(patch.new)
        legacy_value = int.from_bytes(patch.new, "little")
        matches = sorted(
            name
            for name, function in impl.FORMULAS.items()
            if function(p800) == legacy_value
        )
        assert formula in matches, (group, hex(offset))
        if len(matches) > 1:
            key = tuple(matches)
            assert key in KNOWN_COINCIDENCES, (
                f"{group} @ 0x{offset:06X}: formulas {matches} coincide at "
                "800x600; acknowledge the ambiguity in KNOWN_COINCIDENCES "
                "with a justification"
            )


def test_gate_checks_pin_and_parameterization() -> None:
    assert (
        patch_stage_report.current_hd_map_gate_checks()
        == patch_stage_report.CURRENT_HD_MAP_GATE_CHECKS
    )
    frozen = patch_stage_report.CURRENT_HD_MAP_GATE_CHECKS
    assert frozen["visible_tiles_12x9"] == ("visible_tiles", {"x": 12, "y": 9})
    profile = impl.parse_resolution("1920x1080")
    parameterized = patch_stage_report.current_hd_map_gate_checks(profile)
    assert parameterized["visible_tiles_12x9"] == (
        "visible_tiles",
        {"x": 29, "y": 16},
    )
    # Only the tile expectation parameterizes; every other key/value is frozen.
    for name, value in frozen.items():
        if name != "visible_tiles_12x9":
            assert parameterized[name] == value, name


def test_archived_report_still_passes_smoke_gate() -> None:
    fixture = ROOT / "cloud" / "fixtures" / "evidence" / "hd-map" / "patch-stage-report.json"
    report = __import__("json").loads(fixture.read_text(encoding="utf-8"))
    gate = hd_map_smoke_matrix.patch_stage_gate_from_report(
        report, impl.DEFAULT_STAGE, fixture
    )
    assert gate["passed"], gate["failures"]


def test_build_report_on_synthetic_candidates() -> None:
    import shutil
    import tempfile

    workdir = ROOT / ".codex-loop" / "tmp-tests" / "patch-resolution-report-fixture"
    shutil.rmtree(workdir, ignore_errors=True)
    workdir.mkdir(parents=True)
    try:
        base_patches = impl.select_patches(impl.DEFAULT_STAGE)
        size = max(p.offset + len(p.old) for p in impl.PATCHES) + 0x400
        base = bytearray(size)
        # Minimal MZ header so PE parsing degrades gracefully.
        base[:2] = b"MZ"
        for patch in impl.PATCHES:
            base[patch.offset : patch.offset + len(patch.old)] = patch.old
        # Relocation region must be zero; PATCHES old bytes never cover it.
        assert bytes(base[0x119E20 : 0x119E20 + 96]) == b"\x00" * 96

        for resolution, expected_tiles in (
            ("800x600", {"x": 12, "y": 9}),
            ("1920x1080", {"x": 29, "y": 16}),
        ):
            profile = impl.parse_resolution(resolution)
            patches = impl.select_patches_for(impl.DEFAULT_STAGE, profile)
            candidate = impl.apply_patches(bytes(base), patches)
            exe = workdir / f"candidate-{resolution}.bin"
            exe.write_bytes(candidate)
            report = patch_stage_report.build_report(
                exe, impl.DEFAULT_STAGE, resolution
            )
            assert report["resolution"] == resolution
            assert report["current_hd_map_gate"]["passed"], (
                resolution,
                report["current_hd_map_gate"]["failures"],
            )
            assert report["map"]["visible_tiles"] == expected_tiles, resolution
            assert report["status_counts"].get("unexpected", 0) == 0
            assert report["status_counts"].get("original", 0) == 0

        # A 1920x1080 candidate must NOT pass the 800x600 gate (and vice
        # versa): the selected tables differ.
        report = patch_stage_report.build_report(
            workdir / "candidate-1920x1080.bin", impl.DEFAULT_STAGE, "800x600"
        )
        assert not report["current_hd_map_gate"]["passed"]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_shim_exports_resolution_api() -> None:
    spec = importlib.util.spec_from_file_location(
        "clash95_patch_resolution_shim", SHIM_PATH
    )
    assert spec is not None and spec.loader is not None
    shim = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = shim
    spec.loader.exec_module(shim)
    for name in (
        "ResolutionProfile",
        "parse_resolution",
        "RESOLUTION_PRESETS",
        "PARAMETERIZED_STAGES",
        "generate_patches",
        "build_patches",
        "select_patches_for",
        "RECIPES",
        "FORMULAS",
    ):
        assert hasattr(shim, name), name


def test_cli_resolution_gate() -> None:
    # Non-800 resolutions pass the resolution gate now; without an input exe
    # in the working directory the run stops at the input-file check.
    completed = subprocess.run(
        [sys.executable, str(SHIM_PATH), "--resolution", "1024x768"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(ROOT / "tools"),
        check=False,
    )
    assert completed.returncode != 0
    assert "Input file does not exist" in completed.stderr + completed.stdout

    completed = subprocess.run(
        [sys.executable, str(SHIM_PATH), "--resolution", "640x480"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode != 0
    assert "below the 800x600 minimum" in completed.stderr + completed.stdout


def run_tests() -> None:
    test_frozen_table_pin()
    test_dispatch_identity()
    test_golden_generation_at_legacy_resolution()
    test_profile_math()
    test_menu_hitboxes_shift_by_centering_offset()
    test_descriptor_anchor_shifts()
    test_terrain_tooltip_bottom_center_recipes()
    test_selected_unit_command_panel_right_bottom_recipes()
    test_recipe_coverage_and_old_bytes_invariance()
    test_cave_templates()
    test_presets_generate_full_tables()
    test_range_fail_closed()
    test_stage_gating()
    test_combined_ui_validation_is_exact_frozen_union()
    test_frame_restore_tiling_machine_code()
    test_combined_custom_resolution_limits()
    test_coincidence_audit()
    test_gate_checks_pin_and_parameterization()
    test_archived_report_still_passes_smoke_gate()
    test_build_report_on_synthetic_candidates()
    test_shim_exports_resolution_api()
    test_cli_resolution_gate()


def main() -> int:
    run_tests()
    print("patch resolution tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
