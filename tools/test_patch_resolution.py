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
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPL_PATH = ROOT / "src" / "patcher" / "patch_clash95_hd.py"
SHIM_PATH = ROOT / "patch_clash95_hd.py"

_SPEC = importlib.util.spec_from_file_location("clash95_patch_resolution_impl", IMPL_PATH)
assert _SPEC is not None and _SPEC.loader is not None
impl = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = impl
_SPEC.loader.exec_module(impl)


# Pin of the frozen legacy table. Any edit to PATCHES must be deliberate:
# update this hash together with the archived-SHA reproduction check.
FROZEN_TABLE_SHA256 = "7d79b84c8b04916208795fb372bb2af9c2342544b4f9a72e1b5f781182a06a85"

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


def test_recipe_coverage_and_old_bytes_invariance() -> None:
    kinds = {"value": 0, "old-plus": 0, "fixed": 0, "splice": 0, "cave-pending": 0}
    profile = impl.parse_resolution("1920x1080")
    for patch in impl.PATCHES:
        if patch.group not in impl.PARAMETERIZED_GROUPS:
            continue
        recipe = impl.RECIPES.get((patch.group, patch.offset))
        assert recipe is not None, (patch.group, hex(patch.offset))
        kinds[recipe.kind] += 1
        if recipe.kind == "cave-pending":
            continue
        produced = impl._apply_recipe(patch, recipe, profile)
        assert produced.offset == patch.offset
        assert produced.old_hex == patch.old_hex
        assert len(produced.new) == len(patch.new), (patch.group, hex(patch.offset))
    assert kinds == {
        "value": 65,
        "old-plus": 48,
        "fixed": 29,
        "splice": 15,
        "cave-pending": 7,
    }, kinds


def test_presets_generate_without_range_errors() -> None:
    for key in impl.RESOLUTION_PRESETS:
        profile = impl.parse_resolution(key)
        if key == "800x600":
            assert impl.generate_patches(profile) == impl.PATCHES
            continue
        for patch in impl.PATCHES:
            recipe = impl.RECIPES.get((patch.group, patch.offset))
            if recipe is None or recipe.kind == "cave-pending":
                continue
            impl._apply_recipe(patch, recipe, profile)


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


def test_cave_pending_refusal_and_stage_gating() -> None:
    profile = impl.parse_resolution("1024x768")
    try:
        impl.generate_patches(profile)
    except impl.ResolutionNotSupportedError:
        pass
    else:
        raise AssertionError("pending cave templates must refuse generation")

    try:
        impl.select_patches_for("display", profile)
    except impl.ResolutionNotSupportedError:
        pass
    else:
        raise AssertionError("legacy-only stages must refuse non-800 resolutions")

    for stage in impl.PARAMETERIZED_STAGES:
        assert stage in impl.STAGE_GROUPS, stage

    for stage in impl.STAGE_GROUPS:
        legacy_selection = impl.select_patches(stage)
        parameterized_selection = impl.select_patches_for(stage, impl.PROFILE_800)
        assert legacy_selection == parameterized_selection, stage


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
    completed = subprocess.run(
        [sys.executable, str(SHIM_PATH), "--resolution", "1024x768"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode != 0
    assert "not enabled yet" in completed.stderr + completed.stdout

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
    test_recipe_coverage_and_old_bytes_invariance()
    test_presets_generate_without_range_errors()
    test_range_fail_closed()
    test_cave_pending_refusal_and_stage_gating()
    test_coincidence_audit()
    test_shim_exports_resolution_api()
    test_cli_resolution_gate()


def main() -> int:
    run_tests()
    print("patch resolution tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
