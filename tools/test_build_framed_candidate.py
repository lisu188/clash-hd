#!/usr/bin/env python3
"""Offline framed builder/binder fixtures; actual images remain in memory.

File-output boundaries reuse the legacy builder's adversarial CLI cases with
explicitly synthetic non-PE bytes and a TemporaryDirectory candidate root.
No game, debugger, screen, installed candidate or approval is produced.
"""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import build_framed_candidate as builder
import build_partial_tile_candidate as legacy
import test_build_partial_tile_candidate as legacy_fixture
from test_pe_extension import independent_image, rebase

ORIGINAL = Path("C:/Clash/clash95.exe")
RESOLUTIONS = ("800x600", "1024x768", "1280x720", "1280x960", "1920x1080", "802x602")
SITES = (("full_converge", 0x4187A0, "833d9069520000", 0xE9),
         ("full_present", 0x4187B7, "a1fc4c5400", 0xE9),
         ("incremental", 0x418A90, "535156575583ec08", 0xE9),
         ("framed_full_entry", 0x418700, "53515256575583ec18", 0xE9),
         ("framed_frame_gate", 0x4187AF, "e94c361000909090", 0xE9),
         ("initial_paint", 0x40B884, "bed84c54005f", 0xE9),
         ("native_frame", 0x406740, "5351525657", 0xE9),
         ("main_mouse", 0x4084A9, "e8b2580000", 0xE8),
         ("after_keyboard_mouse", 0x407F3C, "e81f5e0000", 0xE8),
         ("selection_mouse", 0x408039, "e8b2880500", 0xE8),
         ("main_fixed_panel", 0x40855D, "0f8d86020000", None),
         ("selection_fixed_panel", 0x4080AA, "0f8d86000000", None))
REMOVED = {0xB885, 0x187A2, 0x187B8}
INITIAL_IMAGES = {
    "800x600": "e72a57fd3bb26509179e0b4360fc9134bef804e152ac338fcd755cdfa41c548f",
    "1024x768": "5ebbaf23ad999a97209a5e0ca8883e8d42e31190fb3891f03cfc3c38001bc338",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def loaded_checks(probe):
    checks = []
    # A framed payload is deliberately chunked below the CDB line limit.
    for line in probe.splitlines():
        if "PTILE_CONTRACT_FAIL" in line:
            checks.extend(legacy_fixture.probe_checks(line))
    if not checks:
        raise AssertionError("missing loaded-byte checks")
    return checks


@unittest.skipUnless(ORIGINAL.is_file(), "requires user-owned original for in-memory byte verification")
class FramedConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()
        cls.results = {resolution: builder.build_candidate(cls.original, resolution) for resolution in RESOLUTIONS}
        cls.bases = {resolution: builder.recipe.canonical_candidate(cls.original, *map(int, resolution.split("x")))
                     for resolution in RESOLUTIONS}

    def binding_args(self, resolution="800x600"):
        return dict(expected_candidate_sha256=digest(self.bases[resolution].image),
                    expected_patcher_sha256=builder.PINNED_SOURCES["src/patcher/patch_clash95_hd.py"],
                    expected_recipe_sha256=builder.PINNED_SOURCES["src/patcher/framed_recipe.py"],
                    expected_geometry_sha256=builder.PINNED_SOURCES["src/patcher/framed_viewport.py"],
                    resolution=resolution)

    def extension_args(self):
        image, metadata, _ = self.results["800x600"]
        patches = []
        for row in metadata["hooks"]:
            relocs = tuple(builder.pe.CodeRelocation(item["offset"], item["kind"], item["target"], item["purpose"])
                           for item in metadata["hook_relocations"] if item["hook_va"] == row["va"])
            patches.append(builder.pe.HookPatch(row["offset"], row["rva"], row["va"],
                bytes.fromhex(row["old_hex"]), bytes.fromhex(row["new_hex"]), row["purpose"], relocs))
        offset = builder.clip.file_offset(image, metadata["code_va"], metadata["code_bytes"])
        return self.binding_args() | dict(validation_stage=builder.STAGE,
            code=image[offset:offset+metadata["code_bytes"]], code_va=metadata["code_va"], hooks=patches,
            relocations=tuple(builder.pe.CodeRelocation(**row) for row in metadata["relocations"]),
            removed_highlow_rvas=tuple(sorted(REMOVED)))

    def test_six_resolutions_bind_twelve_exact_sites_and_additive_rx(self):
        _, original_sections, original_fixups, _ = independent_image(self.original)
        for resolution, (image, metadata, _) in self.results.items():
            with self.subTest(resolution=resolution):
                memory, sections, fixups, _ = independent_image(image)
                base_memory, _, _, _ = independent_image(self.bases[resolution].image)
                self.assertEqual(sections[:-1], original_sections)
                self.assertEqual((sections[-1][0], sections[-1][1], sections[-1][-1]),
                                 (b".hdcode", 0x162000, 0x60000020))
                self.assertEqual(metadata["installed_hook_names"], [site[0] for site in SITES])
                self.assertEqual(len(metadata["hooks"]), 12)
                self.assertEqual(len(metadata["hook_relocations"]), 10)
                reloc_by_va = {row["hook_va"]: row for row in metadata["hook_relocations"]}
                for (name, va, old_hex, opcode), edit in zip(SITES, metadata["hooks"]):
                    old = bytes.fromhex(old_hex)
                    self.assertEqual((edit["va"], edit["rva"], edit["offset"], edit["old_hex"]),
                                     (va, va-0x400000, va-0x400C00, old_hex))
                    self.assertEqual(base_memory[va-0x400000:va-0x400000+len(old)], old)
                    new = memory[va-0x400000:va-0x400000+len(old)]
                    self.assertEqual(new.hex(), edit["new_hex"])
                    if opcode is None:
                        self.assertEqual(new, b"\x90" * 6)
                        self.assertNotIn(va, reloc_by_va)
                    else:
                        self.assertEqual(new[0], opcode)
                        target = va+5+struct.unpack_from("<i", new, 1)[0]
                        self.assertEqual(target, reloc_by_va[va]["target"])
                        self.assertEqual(new[5:], b"\x90"*(len(old)-5))
                        self.assertTrue(metadata["code_va"] <= target < metadata["code_va"]+metadata["code_bytes"])
                        self.assertIn(target, metadata["entry_vas"].values())
                declared = {metadata["code_rva"]+row["offset"] for row in metadata["relocations"] if row["kind"] == "abs32"}
                self.assertEqual(set(fixups), (set(original_fixups)-REMOVED) | declared)
                self.assertEqual(len(fixups), len(set(fixups)))
                self.assertEqual({row["rva"] for row in metadata["removed_highlow"]}, REMOVED)
                self.assertEqual(metadata["retained_highlow_count"], len(original_fixups)-3)
                self.assertEqual(metadata["new_highlow_count"], len(declared))
                self.assertEqual(metadata["stage"], builder.recipe.patcher.DEFAULT_STAGE+
                    "-combinedui-partialtiles-initialpaint-framed-validation")
                self.assertNotIn(metadata["stage"], builder.recipe.patcher.STAGE_GROUPS)
                self.assertEqual(metadata["initial_paint_contract"]["stack"]["full_status_plus_to_ready"], 148)
                self.assertEqual(metadata["layout_contract"]["full_status_to_caller_before_call"], 148)
                self.assertEqual(metadata["output_sha256"], digest(image))
                self.assertEqual(metadata["input_sha256"], digest(self.bases[resolution].image))
                for key in ("installation_ready", "runtime_executed", "promotion_ready", "manual_input_proof"):
                    self.assertFalse(metadata[key])
                self.assertTrue(metadata["validation_stage_only"])
                self.assertTrue(metadata["framed_validation"])
        self.assertEqual(ORIGINAL.read_bytes(), self.original)

    def test_metadata_reconstructs_every_byte_and_preserves_unreported_sections(self):
        for resolution, (image, metadata, _) in self.results.items():
            with self.subTest(resolution=resolution):
                rebuilt = bytearray(self.original)
                for row in (*metadata["selected_patches"], *metadata["edits"]):
                    off = row["offset"]
                    old, new = bytes.fromhex(row["old_hex"]), bytes.fromhex(row["new_hex"])
                    self.assertEqual(rebuilt[off:off+len(old)], old)
                    if not old:
                        self.assertEqual(off, len(rebuilt))
                    rebuilt[off:off+len(old)] = new
                self.assertEqual(bytes(rebuilt), image)
                memory, _, _, _ = independent_image(image)
                baseline, sections, _, _ = independent_image(self.bases[resolution].image)
                for _, va, old_hex, _ in SITES:
                    rva, size = va-0x400000, len(bytes.fromhex(old_hex))
                    memory[rva:rva+size] = baseline[rva:rva+size]
                for _, rva, size, *_ in sections:
                    self.assertEqual(memory[rva:rva+size], baseline[rva:rva+size])

    def test_independent_rebase_moves_only_declared_absolute_operands(self):
        for resolution, (image, metadata, _) in self.results.items():
            memory, _, fixups, _ = independent_image(image)
            for delta in (0x02000000, -0x100000):
                moved = rebase(memory, fixups, delta)
                for row in metadata["relocations"]:
                    at = metadata["code_rva"]+row["offset"]
                    value = struct.unpack_from("<I", moved, at)[0]
                    if row["kind"] == "abs32":
                        self.assertEqual(value, (row["target"]+delta) & 0xFFFFFFFF)
                    else:
                        self.assertEqual(moved[at:at+4], memory[at:at+4])
                        self.assertEqual((metadata["code_va"]+delta+row["offset"]+4+
                                          struct.unpack_from("<i", moved, at)[0]) & 0xFFFFFFFF,
                                         (row["target"]+delta) & 0xFFFFFFFF)
                for edit in metadata["hooks"]:
                    at, size = edit["rva"], len(bytes.fromhex(edit["new_hex"]))
                    self.assertEqual(moved[at:at+size], memory[at:at+size])

    def test_loaded_probe_covers_every_payload_byte_and_all_twelve_hook_spans(self):
        for resolution, (image, metadata, probe) in self.results.items():
            memory, _, _, _ = independent_image(image)
            checks = loaded_checks(probe)
            covered = set()
            for va, size, expected in checks:
                value = int.from_bytes(memory[va-0x400000:va-0x400000+size], "little")
                self.assertEqual(value, expected)
                for index in range(size):
                    covered.add(va+index)
                    self.assertNotEqual(value ^ (1 << (8*index)), expected,
                                        "a changed loaded byte escaped its word predicate")
            self.assertTrue(set(range(metadata["code_va"], metadata["code_va"]+metadata["code_bytes"])) <= covered)
            for _, va, old, _ in SITES:
                self.assertTrue(set(range(va, va+len(bytes.fromhex(old)))) <= covered)
            self.assertTrue(set(range(0x40B88A, 0x40B894)) <= covered)
            self.assertTrue(set(range(0x406FA0, 0x406FAF)) <= covered)
            self.assertLess(probe.rindex("PTILE_CONTRACT_FAIL"), probe.index("bp70 "))
            self.assertIn(f"stage={builder.STAGE} resolution={resolution} candidate_sha256={digest(image)}", probe)
            self.assertIn("manual_input_proof=false promotion_ready=false", probe)
            self.assertEqual(len(re.findall(r"^bp7[0-7] ", probe, re.M)), 8)
            self.assertTrue(all(len(line) < 4096 for line in probe.splitlines()))
            self.assertNotRegex(probe, r"(?:^|[;{])\s*(?:e[bdwq]|r\s+(?:eip|esp|eax))\b")

    def test_fresh_binder_ignores_poisoned_imports_and_restores_private_modules(self):
        base = self.bases["800x600"].image
        names = ["_clash95_pe_framed_binding"+tail for tail in
                 ("", ".patch_clash95_hd", ".framed_viewport", ".framed_recipe")]
        sentinels = {name: types.ModuleType(name) for name in names}
        with patch.dict(sys.modules, sentinels), patch.object(builder.recipe, "canonical_candidate",
                side_effect=AssertionError("mutable imported recipe used")):
            binding = builder.pe._bind_framed_candidate(self.original, base, **self.binding_args())
            self.assertEqual(binding["stage"], builder.recipe.FRAME_BASE_STAGE)
            self.assertTrue(all(sys.modules[name] is value for name, value in sentinels.items()))
            changed = bytearray(base); changed[0x1000] ^= 1
            with self.assertRaisesRegex(ValueError, "exact framed recipe"):
                builder.pe._bind_framed_candidate(self.original, bytes(changed),
                    **(self.binding_args() | dict(expected_candidate_sha256=digest(changed))))
            self.assertTrue(all(sys.modules[name] is value for name, value in sentinels.items()))

    def test_binder_original_source_candidate_and_resolution_fail_closed(self):
        base, args = self.bases["800x600"].image, self.binding_args()
        for key in ("expected_patcher_sha256", "expected_recipe_sha256", "expected_geometry_sha256",
                    "expected_candidate_sha256"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                builder.pe._bind_framed_candidate(self.original, base, **(args | {key: "0"*64}))
        changed = bytearray(self.original); changed[0x1000] ^= 1
        with self.assertRaises(ValueError):
            builder.pe._bind_framed_candidate(bytes(changed), base, **args)
        combined = legacy.patcher.apply_patches(self.original, legacy.patcher.select_patches_for(
            legacy.BASE_STAGE, legacy.patcher.parse_resolution("800x600")))
        for candidate in (self.original, combined, base+b"extra", self.results["800x600"][0]):
            with self.assertRaises(ValueError):
                builder.pe._bind_framed_candidate(self.original, candidate,
                    **(args | dict(expected_candidate_sha256=digest(candidate))))
        for resolution in ("0800x0600", "800X600", "1024x768", "799x600"):
            with self.assertRaises(ValueError):
                builder.pe._bind_framed_candidate(self.original, base, **(args | dict(resolution=resolution)))

    def test_extension_rejects_unreviewed_stage_bad_oldbytes_and_relocation_inventory(self):
        base, args = self.bases["800x600"].image, self.extension_args()
        result = builder.pe.extend_framed_candidate_with_hooks(self.original, base, **args)
        self.assertEqual(result.image, self.results["800x600"][0])
        for stage in ("invented-framed-validation", builder.recipe.FRAME_BASE_STAGE,
                      builder.recipe.patcher.DEFAULT_STAGE, legacy.INITIAL_STAGE, builder.STAGE+"-extra"):
            with self.subTest(stage=stage), self.assertRaises(ValueError):
                builder.pe.extend_framed_candidate_with_hooks(self.original, base, **(args | dict(validation_stage=stage)))
        bad = replace(args["hooks"][0], old=b"\x90"*7)
        cases = (dict(hooks=[]), dict(hooks=[bad, *args["hooks"][1:]]),
                 dict(removed_highlow_rvas=()), dict(removed_highlow_rvas=(*REMOVED, 0x6741)),
                 dict(hooks=[args["hooks"][0], *args["hooks"]]))
        for change in cases:
            with self.assertRaises(ValueError):
                builder.pe.extend_framed_candidate_with_hooks(self.original, base, **(args | change))

    def test_probe_requires_reviewed_framed_stack_key_and_attached_input_records(self):
        observed = {}
        generate = builder.make_probe

        def capture(image, bundle):
            observed.update(image=image, bundle=bundle)
            return generate(image, bundle)

        with patch.object(builder, "make_probe", side_effect=capture):
            builder.build_candidate(self.original, "800x600")
        bundle = observed["bundle"]
        self.assertEqual([site.name for site in bundle.hook_sites], [site[0] for site in SITES])
        self.assertEqual(bundle.layout_contract["full_status_to_caller_before_call"], 148)
        self.assertTrue(all(name in bundle.entries for name in
                            ("frame_presentation.native_frame_entry", "framed_input.minimap_gate", "framed_input.click_gate")))
        for layout in ({"full_status_to_caller_before_call": 88},
                       {"full_status_plus_to_ready": 148},
                       dict(bundle.layout_contract, full_status_to_caller_before_call=0)):
            with self.assertRaisesRegex(ValueError, "reviewed initial/full-stack contract"):
                generate(observed["image"], replace(bundle, layout_contract=layout))

    def test_builder_source_pins_original_and_resolution(self):
        self.assertTrue({"tools/build_partial_tile_candidate.py", "tools/partial_tile_trace_probe.py"}
                        <= builder.PINNED_SOURCES.keys(), "the generated probe's source dependencies must be pinned")
        with tempfile.TemporaryDirectory(prefix="framed-source-fixture-") as name:
            root = Path(name)
            for relative in builder.PINNED_SOURCES:
                path = root/relative; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((builder.ROOT/relative).read_bytes())
            for relative in builder.PINNED_SOURCES:
                path = root/relative; source = path.read_bytes(); path.write_bytes(source+b"\n# synthetic mutation\n")
                with patch.object(builder, "ROOT", root), self.assertRaisesRegex(ValueError, "reviewed framed source changed"):
                    builder.build_candidate(self.original, "800x600")
                path.write_bytes(source)
        changed = bytearray(self.original); changed[0x1000] ^= 1
        with self.assertRaises(ValueError): builder.build_candidate(bytes(changed), "800x600")
        for resolution in ("0800x0600", "800X600", "800x600 ", "799x600"):
            with self.assertRaises(ValueError): builder.build_candidate(self.original, resolution)

    def test_old_partial_and_initial_images_remain_byte_identical(self):
        for resolution, expected in legacy_fixture.KNOWN_CANDIDATES.items():
            image, _, _ = legacy.build_candidate(self.original, resolution)
            self.assertEqual(digest(image), expected)
            image, _, _ = legacy.build_candidate(self.original, resolution, initial_paint=True)
            self.assertEqual(digest(image), INITIAL_IMAGES[resolution])

    def test_actual_preflight_creates_no_files_even_with_output_arguments(self):
        with tempfile.TemporaryDirectory(prefix="framed-preflight-fixture-") as name:
            temp = Path(name)
            argv = ["build_framed_candidate.py", "--original", str(ORIGINAL), "--resolution", "800x600", "--preflight",
                    "--output", str(temp/"no.exe"), "--report-json", str(temp/"no.json"), "--probe-out", str(temp/"no.cdb")]
            output = io.StringIO()
            with patch.object(sys, "argv", argv), redirect_stdout(output), redirect_stderr(io.StringIO()):
                self.assertEqual(builder.main(), 0)
            result = json.loads(output.getvalue())
            self.assertTrue(result["preflight_passed"])
            self.assertFalse(result["runtime_executed"])
            self.assertEqual(result["candidate_sha256"], digest(self.results["800x600"][0]))
            self.assertEqual(list(temp.iterdir()), [])


class FramedCLIBoundaryTests(legacy_fixture.CLIBoundaryTests):
    """Run both full legacy adversarial CLI cases against this new entrypoint.

    The inherited fixtures substitute synthetic non-PE bytes and map the
    C:/ClashTests output root to their TemporaryDirectory. Their tested output
    protections, exclusive creation and race behavior are intentionally shared.
    """
    def setUp(self):
        self.binding = patch.object(legacy_fixture, "builder", builder)
        self.binding.start()
        self.addCleanup(self.binding.stop)

    def test_report_and_probe_races_preserve_the_preexisting_artifact(self):
        for raced_index in (1, 2):
            with self.subTest(raced_index=raced_index), tempfile.TemporaryDirectory(prefix="framed-output-race-") as name:
                temp = Path(name)
                private = temp/"synthetic-candidates"
                source = temp/"synthetic-source.bin"
                source.write_bytes(b"synthetic fixture input, not game bytes")
                outputs = (private/"synthetic.exe", temp/"report.json", temp/"probe.cdb")
                value = (b"synthetic non-PE output", {"fixture_only": True}, ".echo fixture only\n")

                def race(*_):
                    outputs[raced_index].write_bytes(b"concurrent fixture artifact")
                    return value

                def fixture_path(value):
                    return private if str(value) == "C:/ClashTests" else Path(value)

                with patch.object(builder, "Path", side_effect=fixture_path), patch.object(builder, "build_candidate", side_effect=race):
                    with self.assertRaises(FileExistsError):
                        self.invoke(source, *outputs)
                self.assertEqual(outputs[raced_index].read_bytes(), b"concurrent fixture artifact")
                self.assertEqual(source.read_bytes(), b"synthetic fixture input, not game bytes")
                self.assertEqual(outputs[0].read_bytes(), value[0])
                if raced_index == 1:
                    self.assertFalse(outputs[2].exists())
                else:
                    self.assertEqual(json.loads(outputs[1].read_text()), value[1])


if __name__ == "__main__":
    unittest.main()
