#!/usr/bin/env python3
"""Small source/PE fixtures; no files, native loader, compiler or game launch.

The optional --original-backed lane reconstructs exactly one missing preset in
memory from the user-owned original. Default fixtures use synthetic PE bytes;
their passing result is not original-candidate or runtime acceptance.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from pathlib import Path
import struct
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from src.patcher import complete_hd_all_presets_candidate as tool
from src.patcher import framed_army_viewport as geometry
from src.patcher import pe_army_extension as army
from src.patcher import pe_extension as pe
import test_pe_army_extension as army_fixture
import test_pe_modal_extension as modal_fixture

MISSING_PRESETS = ("1366x768", "2560x1440", "3440x1440", "3840x2160")


def fixture(resolution="1366x768"):
    """Explicit synthetic ancestry, reachable only through private format helpers."""
    framed = modal_fixture.synthetic_framed()
    original = bytearray(framed[:0x1000])
    view = pe.inspect_pe(framed)
    struct.pack_into("<H", original, view.pe_offset + 6, 7)
    struct.pack_into("<I", original, view.optional_offset + 4, 0x200)
    struct.pack_into("<I", original, view.optional_offset + 56, 0x8000)
    original[view.sections[-1].header_offset:view.sections[-1].header_offset + 40] = bytes(40)
    original = bytes(original)
    modal_args = modal_fixture.ModalFormatTests().args(framed)
    modal_args["hooks"] = tuple(modal_fixture.jump_hook(framed, 0x401040 + index * 8,
                                modal_args["code_va"]) for index in range(6))
    modal_result = modal_fixture.tool._extend_verified_image(framed, **modal_args)
    modal = dict(modal_result.metadata, base_candidate_sha256=tool.sha256(framed),
                 base_candidate={"output_sha256": tool.sha256(framed)})
    args = army_fixture.arguments(modal_result.image, state_bytes=0)
    args["hooks"] = tuple(army_fixture.hook(modal_result.image, 0x401080 + index * 8,
                         args["code_va"]) for index in range(10))
    args["binding"] = dict(stage=tool.ARMY_STAGE, resolution=resolution,
                           original_sha256=tool.BASE_SHA256, minimap_viewport=True)
    result = army._extend_verified_image(modal_result.image, **args)
    width, height = map(int, resolution.split("x"))
    layout = geometry.FramedArmyViewport(width, height)
    backing, hit = list(layout.backing.as_tuple()), list(layout.hit.as_tuple())
    contracts = dict(
        input=dict(backing=backing, hit=hit, whole_candidate_reconstructed=True, native_mouse_untouched=True),
        draw=dict(backing_rect=backing, candidate_reconstructed=True, portrait_origin=[38, height - 81],
                  portrait_size=[32, 64], slot_pitch=38, minimap_viewport=True,
                  requires_readable_thread_owned_context=True, requires_canonical_memory_vtable=True,
                  native_fallback_retained=True),
        composition=dict(backing=backing, hit=hit, unsupported_owner_is_original_fallback=True,
                         original_generators_unchanged=True, runtime_executed=False))
    metadata = dict(result.metadata, army_revision=tool.ARMY_REVISION, base_candidate=modal,
                    base_candidate_sha256=tool.sha256(modal_result.image), army_contracts=contracts)
    return original, result.image, metadata


def corrupt(image, metadata, offset, replacement):
    """Update the declared final edit too, to reach independent structural checks."""
    data, meta = bytearray(image), deepcopy(metadata)
    data[offset:offset + len(replacement)] = replacement
    for row in meta["edits"]:
        start = row["offset"]
        new = bytes.fromhex(row["new_hex"])
        if start <= offset and offset + len(replacement) <= start + len(new):
            row["new_hex"] = bytes(data[start:start + len(new)]).hex()
            break
    else:
        raise AssertionError("fixture mutation must belong to a declared final edit")
    meta["output_sha256"] = tool.sha256(bytes(data))
    return bytes(data), meta


class SourceAndGeometryTests(unittest.TestCase):
    def test_all_nine_presets_and_frozen_sibling_identity(self):
        self.assertEqual(len(tool.RESOLUTIONS), 9)
        self.assertEqual(len(set(tool.RESOLUTIONS)), 9)
        self.assertTrue(set(MISSING_PRESETS).issubset(tool.RESOLUTIONS))
        self.assertNotIn("802x602", tool.RESOLUTIONS)
        sources = tool._sources()
        tree = ast.parse(sources["src/patcher/complete_hd_candidate.py"])
        literals = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
                    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id in ("REVISION", "STAGE", "RESOLUTIONS")}
        self.assertEqual(literals["REVISION"], "complete_hd_v1")
        self.assertEqual(literals["RESOLUTIONS"], ("800x600", "1024x768", "1280x720", "1280x960", "1920x1080", "802x602"))
        self.assertNotEqual(tool.STAGE, literals["STAGE"])
        self.assertTrue(tool.STAGE.endswith("-validation"))
        for resolution in tool.RESOLUTIONS:
            with self.subTest(resolution=resolution):
                width, height = map(int, resolution.split("x"))
                layout = geometry.FramedArmyViewport(width, height)
                self.assertTrue(layout.framed.terrain.contains(layout.backing))
                self.assertIsNone(layout.backing.intersection(layout.framed.action_bar))
                self.assertEqual(len(layout.framed.action_cells), 6)
                self.assertEqual(layout.portrait(0).width, 32)
                self.assertEqual(layout.portrait(0).height, 64)
                self.assertEqual(layout.pixel_to_slot(38, height - 82), 0)
                self.assertEqual(layout.pixel_to_slot(417, height - 19), 9)
                self.assertIsNone(layout.pixel_to_slot(418, height - 19))
                bands = layout.framed.frame_bands
                self.assertEqual(sum(rect.width * rect.height for rect in bands)
                                 + layout.framed.terrain.width * layout.framed.terrain.height, width * height)

    def test_private_producer_ignores_existing_module_alias_and_restores_import_state(self):
        alias = types.ModuleType("build_framed_army_candidate")
        alias.__file__ = "unrelated/fixture.py"
        alias.STAGE = "not-a-production-stage"
        before_path = list(sys.path)
        before_modules = set(sys.modules)
        with patch.dict(sys.modules, {alias.__name__: alias}):
            with tool._producer(tool._sources()) as (bound, parser, layout):
                self.assertEqual(bound.STAGE, tool.ARMY_STAGE)
                self.assertEqual(bound.REVISION, tool.ARMY_REVISION)
                self.assertTrue(bound.build_candidate.__module__.startswith("_clash95_all_presets_"))
                self.assertEqual(Path(bound.__file__), ROOT / "tools/build_framed_army_candidate.py")
                self.assertEqual(parser.ORIGINAL_SHA256, tool.BASE_SHA256)
                self.assertEqual(layout.FramedArmyViewport(3840, 2160).dy, 1678)
            self.assertIs(sys.modules[alias.__name__], alias)
        self.assertEqual(sys.path, before_path)
        self.assertFalse(any(name.startswith("_clash95_all_presets_") for name in set(sys.modules) - before_modules))

    def test_private_producer_exception_restores_import_state(self):
        sources = tool._sources()
        sources[tool.MODULE_ORDER[-1]] = b"raise ValueError('fixture failure')\n"
        before_path = list(sys.path)
        with self.assertRaisesRegex(ValueError, "fixture failure"):
            with tool._producer(sources):
                self.fail("unexpected producer")
        self.assertEqual(sys.path, before_path)
        self.assertFalse(any(name.startswith("_clash95_all_presets_") for name in sys.modules))

    def test_modified_source_is_rejected_without_writing_files(self):
        read = Path.read_bytes
        target = ROOT / "tools/build_framed_army_candidate.py"
        with patch.object(Path, "read_bytes", lambda path: read(path) + (b"\n# drift" if path == target else b"")):
            with self.assertRaisesRegex(ValueError, "producer source differs"):
                tool._sources()

    def test_unknown_original_and_noncanonical_resolution_fail_closed(self):
        for original in (b"fixture", bytearray(b"fixture"), None):
            with self.subTest(original=type(original)), self.assertRaises(ValueError):
                tool.build_candidate(original, "1366x768")
        # Selector rejection occurs before any construction. This fixture has
        # no production identity override and cannot turn synthetic bytes into proof.
        with patch.object(tool, "sha256", return_value=tool.BASE_SHA256), patch.object(tool, "_sources", side_effect=AssertionError("construction must not start")):
            for resolution in ("802x602", "1920X1080", "01366x768", "4096x2160", True, None):
                with self.subTest(resolution=resolution), self.assertRaises(ValueError):
                    tool.build_candidate(b"fixture", resolution)


class FinalImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, cls.image, cls.metadata = fixture()

    def test_full_synthetic_final_audit_and_original_byte_replay(self):
        audit = tool._audit_final(self.original, self.image, self.metadata, "1366x768", pe, geometry)
        self.assertEqual(audit["section_count"], 11)
        self.assertEqual(audit["army_hook_count"], 10)
        self.assertEqual(audit["modal_state_bytes"], 4096)
        self.assertEqual(audit["native_portrait_size"], [32, 64])
        view = pe.inspect_pe(self.image)
        records = tool.byte_records(self.original, self.image, view)
        self.assertTrue(any(row["appended"] for row in records))
        self.assertTrue(all(row["stage"] == tool.STAGE for row in records))
        self.assertEqual(tool.apply_records(self.original, records, expected_base_sha256=tool.sha256(self.original), view=view), self.image)
        self.assertEqual(tool.sha256(tool._undo_edits(self.image, self.metadata, pe)), self.metadata["input_sha256"])

    def test_all_nine_resolution_geometry_contracts_reach_final_gate(self):
        for resolution in tool.RESOLUTIONS:
            with self.subTest(resolution=resolution):
                original, image, metadata = fixture(resolution)
                self.assertEqual(tool._audit_final(original, image, metadata, resolution, pe, geometry)["army_hook_count"], 10)

    def test_replay_rejects_wrong_base_old_bytes_mapping_order_stage_and_append(self):
        view = pe.inspect_pe(self.image)
        records = tool.byte_records(self.original, self.image, view)
        def check(rows):
            with self.assertRaises(ValueError):
                tool.apply_records(self.original, rows, expected_base_sha256=tool.sha256(self.original), view=view)
        with self.assertRaisesRegex(ValueError, "base SHA"):
            tool.apply_records(self.original, records, expected_base_sha256="0" * 64, view=view)
        index = next(i for i, row in enumerate(records) if row["old_hex"])
        cases = (("file_offset", True), ("file_offset", 1.0), ("offset", -1), ("stage", "stable"),
                 ("old_hex", "00"), ("new_hex", ""), ("new_hex", "AA"), ("rva", 0),
                 ("va", 0), ("rva", float(records[index]["rva"])), ("appended", 1), ("rationale", ""))
        for key, value in cases:
            rows = deepcopy(records)
            rows[index][key] = value
            with self.subTest(key=key, value=value):
                check(rows)
        check([records[0], records[0]] + records[1:])
        index = next(i for i, row in enumerate(records) if row["appended"])
        rows = deepcopy(records)
        rows[index]["offset"] += 1
        rows[index]["file_offset"] += 1
        check(rows)

    def test_final_acceptance_and_geometry_claims_cannot_be_forged(self):
        for key in tool.FALSE_CLAIMS:
            meta = deepcopy(self.metadata)
            meta[key] = True
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "acceptance claim"):
                tool._audit_final(self.original, self.image, meta, "1366x768", pe, geometry)
        for key, value in (("stage", "stable"), ("resolution", "3840x2160"), ("minimap_viewport", 1), ("army_revision", "other")):
            meta = deepcopy(self.metadata)
            meta[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                tool._audit_final(self.original, self.image, meta, "1366x768", pe, geometry)
        meta = deepcopy(self.metadata)
        meta["army_contracts"]["draw"]["portrait_origin"][1] += 1
        with self.assertRaisesRegex(ValueError, "geometry contract"):
            tool._audit_final(self.original, self.image, meta, "1366x768", pe, geometry)

    def test_hook_count_operand_inventory_and_parent_identity_fail_closed(self):
        for key, value in (("hooks", self.metadata["hooks"][:-1]), ("relocations", self.metadata["relocations"][1:]),
                           ("input_sha256", "0" * 64), ("merged_relocation_sha256", "0" * 64),
                           ("retired_header_scratch", {"legacy_day_diagnostic_allowed": True})):
            meta = deepcopy(self.metadata)
            meta[key] = deepcopy(value)
            with self.subTest(key=key), self.assertRaises(ValueError):
                tool._audit_army(self.image, meta, pe)
        meta = deepcopy(self.metadata)
        meta["hook_relocations"][0]["target"] += 1
        with self.assertRaisesRegex(ValueError, "operand differs"):
            tool._audit_army(self.image, meta, pe)

    def test_code_protection_size_payload_directory_padding_and_state_corruption_fail(self):
        view = pe.inspect_pe(self.image)
        code = view.sections[-1]
        cases = ((code.header_offset + 36, struct.pack("<I", tool.RW)),
                 (code.header_offset + 8, struct.pack("<I", 0x21000)),
                 (code.raw_offset + 1, b"\xff"),
                 (code.raw_offset + self.metadata["code_bytes"], b"\xff"))
        for offset, value in cases:
            image, meta = corrupt(self.image, self.metadata, offset, value)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                tool._audit_army(image, meta, pe)
        state = view.sections[-2]
        image = bytearray(self.image)
        image[state.raw_offset] = 1
        meta = deepcopy(self.metadata)
        meta["output_sha256"] = tool.sha256(bytes(image))
        with self.assertRaises(ValueError):
            tool._audit_final(self.original, bytes(image), meta, "1366x768", pe, geometry)

    def test_source_declared_code_target_cannot_escape_owned_memory(self):
        view = pe.inspect_pe(self.image)
        for target in (0x1234, view.image_base + view.sections[-2].rva):
            meta = deepcopy(self.metadata)
            row = meta["relocations"][-1]
            row["kind"] = "rel32"
            row["target"] = target
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "unowned or non-executable"):
                tool._audit_army(self.image, meta, pe)

    def test_duplicate_or_partial_old_fixup_displacement_fails(self):
        meta = deepcopy(self.metadata)
        meta["relocations"].append(deepcopy(meta["relocations"][0]))
        with self.assertRaisesRegex(ValueError, "overlap"):
            tool._audit_army(self.image, meta, pe)
        meta = deepcopy(self.metadata)
        meta["removed_highlow"] = [{"rva": 0x1001, "va": 0x401001, "offset": 0x401, "old_hex": "08204000"}]
        with self.assertRaisesRegex(ValueError, "removal inventory"):
            tool._audit_army(self.image, meta, pe)


class ProbeTests(unittest.TestCase):
    def fixture(self, resolution="1366x768"):
        digest = "a" * 64
        inherited = (".if (@eax == 0) { .echo ARMY_CONTRACT_FAIL; q }\n"
            f".echo ARMY_CONTRACT_PASS stage={tool.ARMY_STAGE} resolution={resolution} candidate_sha256={digest} revision={tool.ARMY_REVISION}\n"
            f".echo PTILE_CONTRACT_PASS stage={tool.ARMY_STAGE} resolution={resolution} candidate_sha256={digest}\n"
            ".echo PTILE_OBSERVER_UNCHANGED\n")
        return digest, inherited, {"initial_probe_sha256": tool.sha256(inherited.encode())}

    def test_new_marker_preserves_every_inherited_predicate_and_observer(self):
        for resolution in tool.RESOLUTIONS:
            with self.subTest(resolution=resolution):
                digest, inherited, meta = self.fixture(resolution)
                probe, contract = tool._probe(inherited, meta, resolution, digest, "b" * 64)
                marker = ".echo " + contract["complete_marker"] + "\n"
                self.assertEqual(probe.replace(marker, "", 1), inherited)
                self.assertEqual(probe.count("COMPLETEHD_ALL_PRESETS_CONTRACT_PASS"), 1)
                self.assertNotIn("COMPLETEHD_CONTRACT_PASS", probe)
                self.assertIn(tool.STAGE, probe)
                self.assertTrue(contract["all_inherited_checks_required"])
                self.assertIn("Initial ordinary-map", contract["scope"])

    def test_missing_duplicate_foreign_or_unchecked_inherited_markers_fail(self):
        digest, inherited, meta = self.fixture()
        variants = (inherited.replace("ARMY_CONTRACT_FAIL", "unverified"), inherited + inherited,
                    inherited.replace("candidate_sha256=" + digest, "candidate_sha256=" + "c" * 64),
                    inherited.replace("PTILE_CONTRACT_PASS", "PTILE_MISSING"),
                    inherited + ".echo COMPLETEHD_CONTRACT_PASS\n")
        for variant in variants:
            meta = {"initial_probe_sha256": tool.sha256(variant.encode())}
            with self.subTest(variant=variant[:60]), self.assertRaises(ValueError):
                tool._probe(variant, meta, "1366x768", digest, "b" * 64)
        with self.assertRaises(ValueError):
            tool._probe(inherited, {"initial_probe_sha256": "0" * 64}, "1366x768", digest, "b" * 64)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", action="store_true", help="reconstruct one 1366x768 candidate in memory; no output")
    args = parser.parse_args(argv)
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        return 1
    if args.original_backed:
        original = Path("C:/Clash/clash95.exe").read_bytes()
        image, metadata, probe = tool.build_candidate(original, "1366x768")
        assert metadata["candidate_sha256"] == tool.sha256(image)
        assert metadata["probe_sha256"] == tool.sha256(probe.encode())
        assert all(metadata[key] is False for key in tool.FALSE_CLAIMS)
        assert metadata["expanded_battle_installed"] is metadata["launcher_registered"] is False
        print("ORIGINAL_BACKED_CONSTRUCTION_PASS resolution=1366x768 candidate_sha256=" + tool.sha256(image)
              + " bytes=" + str(len(image)) + " runtime_executed=false promotion_ready=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
