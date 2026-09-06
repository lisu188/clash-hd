#!/usr/bin/env python3
"""Offline framed scalar/data recipe fixtures; no candidate files or runtime."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.patcher import framed_recipe as framed
from src.patcher import patch_clash95_hd as native

ORIGINAL = Path("C:/Clash/clash95.exe")
# Independent expectations from the 32/16 four-band layout, not emitted slots.
CASES = {
    (800, 600): ((11, 8), (735, 527), (576, 520), (32, 56)),
    (1024, 768): ((15, 11), (991, 719), (800, 688), (0, 32)),
    (1280, 720): ((19, 10), (1247, 655), (1056, 640), (0, 48)),
    (1280, 960): ((19, 14), (1247, 911), (1056, 880), (0, 32)),
    (1920, 1080): ((29, 16), (1887, 1039), (1696, 1000), (0, 24)),
    (802, 602): ((11, 8), (735, 527), (578, 522), (34, 58)),
}
DESCRIPTOR_OFFSETS = (0x10FF40, 0x10FF75, 0x10FFAA, 0x10FFDF, 0x110014, 0x110049)
PHYSICAL_FIELDS = {0x3A64: "H", 0x3A69: "W", 0x60EAD: "H", 0x60EB2: "W",
                   0xE4D: "H", 0xE62: "W", 0xA3BF: "H", 0xA3C4: "W",
                   0x5F826: "W-1", 0x5F82D: "H-1", 0x5F92D: "H", 0x5F93B: "W",
                   0x19165: "W", 0x1918E: "W"}


def source_selection(size):
    return tuple(native.select_patches_for(framed.SOURCE_STAGE, native.ResolutionProfile(*size)))


class RecipeTests(unittest.TestCase):
    def test_all_six_full_counts_signed_helpers_edges_and_command_anchors(self):
        for size, (counts, edges, command, _) in CASES.items():
            with self.subTest(size=size):
                result = framed.select_patches_for(native.ResolutionProfile(*size))
                self.assertIsInstance(result, tuple)
                by_offset = {p.offset: p for p in result}
                tx, ty = counts
                self.assertEqual(by_offset[0x17B70].new, bytes([tx]))
                self.assertEqual(by_offset[0x17B81].new, bytes([ty - 1]))
                self.assertEqual(by_offset[0x17DFF].new, bytes([tx]))
                for offset, value in ((0x7087, -tx), (0x70BB, -ty), (0xEF9D, -tx),
                                      (0xEF6D, -ty), (0x18087, -(ty + 1)),
                                      (0x18131, -(ty + 1)), (0x180C2, -(tx + 1)),
                                      (0x18163, -(tx + 1)), (0xEF01, tx // 2), (0xEF18, ty // 2)):
                    self.assertEqual(int.from_bytes(by_offset[offset].new, "little", signed=True), value)
                for offset in (0x17CDE, 0x17D6C, 0x17D82, 0x17E68):
                    self.assertEqual(struct.unpack("<I", by_offset[offset].new)[0], edges[0])
                for offset in (0x17D99, 0x17E5E):
                    self.assertEqual(struct.unpack("<I", by_offset[offset].new)[0], edges[1])
                for index, offset in enumerate(DESCRIPTOR_OFFSETS):
                    self.assertEqual(struct.unpack("<II", by_offset[offset].new),
                                     (command[0] + 64 * (index % 3), command[1] + 32 * (index // 3)))
                self.assertEqual(by_offset[0xC790].new, b"\xBA" + struct.pack("<I", size[0] - 32))

    def test_every_selected_scalar_source_formula_is_recomputed(self):
        for size, (counts, edges, _, _) in CASES.items():
            profile = native.ResolutionProfile(*size)
            result = {(p.group, p.offset): p for p in framed.select_patches_for(profile)}
            tx, ty = counts
            expected = {"TX": tx, "TY": ty, "TY-1": ty - 1, "-TX": -tx, "-TY": -ty,
                        "TX//2": tx // 2, "TY//2": ty // 2, "-(TY+1)": -(ty + 1),
                        "-(TX+1)": -(tx + 1), "EDGEX": edges[0], "EDGEY": edges[1]}
            seen = []
            for source in source_selection(size):
                key = source.group, source.offset
                recipe = native.RECIPES.get(key)
                if recipe and recipe.kind == "value" and recipe.value in expected:
                    value = int.from_bytes(result[key].new, "little", signed=recipe.signed)
                    self.assertEqual(value, expected[recipe.value], (size, key, recipe.value))
                    seen.append(key)
            self.assertEqual(len(seen), 52)

    def test_physical_dimensions_input_clips_and_unrelated_lanes_stay_exact(self):
        preserved_groups = {"frame-restore-bands", "right-bottom-compose-proof", "terrain-tooltip-bottom-center",
                            "menu-center-hitboxes", "mouse-dynamic-origin", "viewport-switch-dynamic-surface",
                            "castle-ui-center-present-wrapper", "castle-ui-centered-input",
                            "castle-overview-center-present-wrapper", "castle-overview-centered-input",
                            "battle-ui-center-present-wrapper", "battle-grid-centered-input", "battle-ui-centered-input"}
        for size in CASES:
            baseline = source_selection(size)
            result = framed.select_patches_for(native.ResolutionProfile(*size))
            self.assertEqual(len(result), 166)
            for old, new in zip(baseline, result):
                self.assertEqual((old.group, old.offset, old.old_hex, len(old.new)),
                                 (new.group, new.offset, new.old_hex, len(new.new)))
                if old.group in preserved_groups:
                    self.assertEqual(old, new, (size, old.group, hex(old.offset)))
                if old.offset in PHYSICAL_FIELDS:
                    self.assertEqual(old, new)
                    formula = PHYSICAL_FIELDS[old.offset]
                    w, h = size
                    self.assertEqual(int.from_bytes(new.new, "little"), {"W": w, "H": h, "W-1": w - 1, "H-1": h - 1}[formula])

    def test_scroll_cave_opcodes_physical_allocation_and_unrelated_bytes_preserved(self):
        for size, (counts, _, _, _) in CASES.items():
            baseline = {p.offset: p for p in source_selection(size)}
            result = {p.offset: p for p in framed.select_patches_for(native.ResolutionProfile(*size))}
            # These exact positions were independently decoded from native
            # upgrade-cave SUB EBX,imm8 instructions, not returned metadata.
            expected = bytearray(baseline[0xE8C80].new)
            self.assertEqual(expected[0x48:0x4A], b"\x83\xEB")
            self.assertEqual(expected[0x63:0x65], b"\x83\xEB")
            expected[0x4A], expected[0x65] = counts
            self.assertEqual(result[0xE8C80].new, bytes(expected))
            self.assertEqual(result[0xD0B0].new, bytes((0x83, 0xEE, counts[0])))
            for offset in (0xD0DA, 0xD124):
                self.assertEqual(result[offset].new, bytes((0x83, 0xEA, counts[1])))

    def test_protected_table_defaults_and_sources_are_never_mutated(self):
        before = (native.PATCHES, dict(native.STAGE_GROUPS), dict(native.RECIPES), dict(native.FORMULAS))
        source = Path(native.__file__).read_bytes()
        for size in CASES:
            framed.select_patches_for(native.ResolutionProfile(*size))
        self.assertIs(native.PATCHES, before[0])
        self.assertEqual((native.STAGE_GROUPS, native.RECIPES, native.FORMULAS), before[1:])
        self.assertEqual(Path(native.__file__).read_bytes(), source)
        self.assertNotIn(framed.FRAME_BASE_STAGE, native.STAGE_GROUPS)
        self.assertNotEqual(framed.FRAME_BASE_STAGE, framed.SOURCE_STAGE)
        self.assertEqual(hashlib.sha256(source).hexdigest(), framed.PATCHER_SHA256)

    def test_missing_wrong_or_ambiguous_source_recipes_fail_closed(self):
        profile = native.PROFILE_800
        key = ("helpers", 0x7080)
        with patch.dict(native.RECIPES, {key: replace(native.RECIPES[key], value="TY")}):
            with self.assertRaisesRegex(framed.FramedRecipeError, "formula"):
                framed.select_patches_for(profile)
        splice_key = ("helpers", 0xD0B0)
        recipe = native.RECIPES[splice_key]
        for slot in (replace(recipe.slots[0], pattern="83ee00"),
                     replace(recipe.slots[0], count=2), replace(recipe.slots[0], signed=False)):
            with patch.dict(native.RECIPES, {splice_key: replace(recipe, slots=(slot,))}):
                with self.assertRaises(framed.FramedRecipeError):
                    framed.select_patches_for(profile)
        baseline = source_selection((800, 600))
        with patch.object(native, "select_patches_for", return_value=[p for p in baseline if p.offset != 0x7080]):
            with self.assertRaisesRegex(framed.FramedRecipeError, "missing"):
                framed.select_patches_for(profile)
        with patch.object(native, "select_patches_for", return_value=[*baseline, baseline[0]]):
            with self.assertRaisesRegex(framed.FramedRecipeError, "duplicate"):
                framed.select_patches_for(profile)

    def test_source_drift_invalid_profiles_and_signed_overflow_reject(self):
        with patch.object(framed, "PATCHER_SHA256", "0" * 64):
            with self.assertRaisesRegex(framed.FramedRecipeError, "source SHA"):
                framed.select_patches_for(native.PROFILE_800)
        with patch.object(native, "PATCHES", native.PATCHES[:-1]):
            with self.assertRaisesRegex(framed.FramedRecipeError, "table identity"):
                framed.select_patches_for(native.PROFILE_800)
        for invalid in ((800, 600), None, "800x600"):
            with self.assertRaises(framed.FramedRecipeError):
                framed.select_patches_for(invalid)
        for value in (-129, 128):
            with self.assertRaisesRegex(framed.FramedRecipeError, "does not fit"):
                framed._encoded(value, 1, True, "signed native tile immediate")
        self.assertEqual(framed._encoded(-128, 1, True, "lower signed bound"), b"\x80")
        with self.assertRaises(ValueError):
            framed.select_patches_for(native.ResolutionProfile(8194, 600))
        mutated = native.ResolutionProfile(800, 600)
        object.__setattr__(mutated, "width", 800.0)
        with self.assertRaises(framed.FramedRecipeError):
            framed.select_patches_for(mutated)


@unittest.skipUnless(ORIGINAL.is_file(), "requires user-owned original for exact byte and PE proof")
class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()
        cls.results = {size: framed.canonical_candidate(cls.original, *size) for size in CASES}

    def test_original_bytes_addresses_and_binding_metadata_are_exact(self):
        for size, result in self.results.items():
            metadata = result.metadata
            self.assertFalse(result.installation_ready)
            self.assertFalse(metadata["installation_ready"])
            self.assertEqual(metadata["original_sha256"], native.EXPECTED_SHA256)
            self.assertEqual(metadata["candidate_sha256"], hashlib.sha256(result.image).hexdigest())
            self.assertEqual(metadata["base_stage"], framed.FRAME_BASE_STAGE)
            self.assertEqual(metadata["source_stage"], framed.SOURCE_STAGE)
            self.assertEqual(metadata["layout"]["full_tiles"], list(CASES[size][0]))
            self.assertEqual(metadata["layout"]["partial_pixels"], list(CASES[size][3]))
            self.assertEqual(metadata["layout"]["terrain"], [32, 16, size[0] - 33, size[1] - 17])
            self.assertEqual(metadata["original_highlow_count"], 32435)
            self.assertFalse(metadata["scalar_highlow_overlap"])
            self.assertEqual(metadata["preserved_unaccepted_owner_groups"], ["right-bottom-compose-proof"])
            for name in ("frame_drawing_installed", "input_hooks_installed", "presentation_installed"):
                self.assertFalse(metadata[name])
            for record in metadata["patches"]:
                offset = record["file_offset"]
                old, new = bytes.fromhex(record["old_hex"]), bytes.fromhex(record["new_hex"])
                self.assertEqual(self.original[offset:offset + len(old)], old)
                self.assertEqual(result.image[offset:offset + len(new)], new)
                self.assertEqual(record["va"] - record["rva"], 0x400000)
            by_offset = {record["file_offset"]: record for record in metadata["patches"]}
            self.assertEqual((by_offset[0x10FF40]["rva"], by_offset[0x10FF40]["va"]), (0x111D40, 0x511D40))
            self.assertEqual((by_offset[0xC790]["rva"], by_offset[0xC790]["va"]), (0xD390, 0x40D390))
            for binding in metadata["source_bindings"].values():
                self.assertEqual(binding["sha256"], hashlib.sha256(Path(binding["path"]).read_bytes()).hexdigest())
            json.dumps(metadata)  # The metadata contains no candidate bytes.

    def test_exact_difference_from_combined_is_only_declared_source_fields(self):
        for size, result in self.results.items():
            combined = native.apply_patches(self.original, source_selection(size))
            self.assertEqual(hashlib.sha256(combined).hexdigest(), result.metadata["source_candidate_sha256"])
            slots = result.metadata["declared_slots"]
            self.assertEqual(len(slots), 70)
            expected = bytearray(combined)
            fields = set()
            for slot in slots:
                at, width = slot["file_offset"], slot["width"]
                positions = set(range(at, at + width))
                self.assertFalse(positions & fields)
                fields |= positions
                self.assertEqual(combined[at:at + width].hex(), slot["combined_old_hex"])
                self.assertEqual(self.original[at:at + width].hex(), slot["original_hex"])
                expected[at:at + width] = bytes.fromhex(slot["new_hex"])
            self.assertEqual(result.image, bytes(expected))
            self.assertEqual(len(result.image), len(self.original))
            actual_differences = {i for i, (a, b) in enumerate(zip(combined, result.image)) if a != b}
            self.assertTrue(actual_differences)
            self.assertTrue(actual_differences <= fields)
            self.assertEqual(result.metadata["changed_slots"], [s for s in slots if s["combined_old_hex"] != s["new_hex"]])
            # DOS/PE headers and original relocation section are unchanged
            # from the combined input; no extension/hook is being installed.
            self.assertEqual(result.image[:0x400], combined[:0x400])
            pe = struct.unpack_from("<I", self.original, 0x3C)[0]
            count = struct.unpack_from("<H", self.original, pe + 6)[0]
            optional = struct.unpack_from("<H", self.original, pe + 20)[0]
            self.assertEqual(count, 7)
            for index in range(count):
                entry = pe + 24 + optional + 40 * index
                if self.original[entry:entry + 8].rstrip(b"\0") == b".reloc":
                    size_bytes, offset = struct.unpack_from("<II", self.original, entry + 16)
                    self.assertEqual(result.image[offset:offset + size_bytes], self.original[offset:offset + size_bytes])

    def test_unknown_original_and_already_patched_input_reject(self):
        wrong = bytearray(self.original)
        wrong[0x100] ^= 1
        for data in (bytes(wrong), bytes(), bytearray(self.original), self.results[(800, 600)].image):
            with self.assertRaisesRegex(framed.FramedRecipeError, "SHA-256"):
                framed.canonical_candidate(data, 800, 600)
        for size in ((True, 600), (800.0, 600), (640, 480), (801, 600), (800, 601)):
            with self.assertRaises(ValueError):
                framed.canonical_candidate(self.original, *size)
        self.assertEqual(hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(), native.EXPECTED_SHA256)

    def test_old_byte_size_overlap_and_highlow_contracts_fail_closed(self):
        selected = framed.select_patches_for(native.PROFILE_800)
        first = selected[0]
        mutations = ((replace(first, old_hex="ff" * len(first.old)), *selected[1:]),
                     (replace(first, new_hex=first.new_hex + "00"), *selected[1:]),
                     (*selected, first), (replace(first, offset=len(self.original)), *selected[1:]))
        for records in mutations:
            with self.assertRaises(framed.FramedRecipeError):
                framed._apply_verified(self.original, records)
        # A scalar touching any byte of an existing absolute field is not
        # silently accepted as a relocation-free geometry change.
        first_slot = self.results[(800, 600)].metadata["declared_slots"][0]
        with patch.object(framed, "_highlow_rvas", return_value={first_slot["rva"] - 2}):
            with self.assertRaisesRegex(framed.FramedRecipeError, "HIGHLOW"):
                framed.canonical_candidate(self.original, 800, 600)


if __name__ == "__main__":
    unittest.main()
