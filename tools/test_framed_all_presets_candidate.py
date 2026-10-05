#!/usr/bin/env python3
"""Portable Framed source/geometry/PE/probe fixtures; no loader or runtime.

Optional --original-backed constructs one 1366x768 original candidate twice in
memory and checks deterministic bytes, JSON metadata and probe. It writes no
candidate, bundle, report, capture, cache or native fixture.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import json
from pathlib import Path
import struct
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import framed_all_presets_candidate as tool
from src.patcher import pe_extension as pe
from src.patcher import framed_viewport as geometry
from test_pe_extension import independent_image, rebase


def original_fixture():
    """Independent seven-section PE32 fixture; no game-derived bytes."""
    data = bytearray(0x1000)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 60, 0x70)
    data[0x70:0x74] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", data, 0x74, 0x14C, 7, 0, 0, 0, 224, 0x182)
    opt = 0x88
    struct.pack_into("<H", data, opt, 0x10B)
    struct.pack_into("<I", data, opt + 4, 512)
    struct.pack_into("<III", data, opt + 28, 0x400000, 4096, 512)
    struct.pack_into("<II", data, opt + 56, 0x8000, 1024)
    struct.pack_into("<I", data, opt + 92, 16)
    struct.pack_into("<II", data, opt + 136, 0x7000, 16)
    for index, (name, rva, size, raw, flags) in enumerate((
        (b".text", 0x1000, 512, 0x400, pe.RX_CODE), (b".bss", 0x2000, 4096, 0, 0xC0000080),
        (b".rdata", 0x3000, 512, 0x600, 0x40000040), (b".data", 0x4000, 512, 0x800, 0xC0000040),
        (b".idata", 0x5000, 512, 0xA00, 0xC0000040), (b".debug", 0x6000, 512, 0xC00, 0x40000040),
        (b".reloc", 0x7000, 512, 0xE00, 0x42000040))):
        struct.pack_into("<8sIIIIIIHHI", data, opt + 224 + 40 * index, name, 0, rva, size, raw, 0, 0, 0, 0, flags)
    data[0x400:0x600] = b"\x90" * 512
    for offset, target in ((1, 0x402008), (9, 0x401100), (17, 0x401008)):
        struct.pack_into("<I", data, 0x400 + offset, target)
    struct.pack_into("<II4H", data, 0xE00, 0x1000, 16, 0x3001, 0x3009, 0x3011, 0)
    return bytes(data)


def fixture(resolution="1366x768"):
    original = original_fixture()
    width, height = map(int, resolution.split("x"))
    scalar = bytearray(original)
    scalar[0x500:0x504] = struct.pack("<I", width)
    patches = [dict(offset=0x500, old_hex=original[0x500:0x504].hex(), new_hex=scalar[0x500:0x504].hex(), group="synthetic-width")]
    scalar = bytes(scalar)
    code = bytearray(b"\x90" * 45)
    fields = (pe.CodeRelocation(1, "abs32", 0x402008, "synthetic BSS field"),
              pe.CodeRelocation(10, "rel32", 0x401100, "synthetic native transfer"),
              pe.CodeRelocation(21, "abs32", 0x408020, "synthetic internal pointer"))
    for row in fields:
        value = row.target if row.kind == "abs32" else (row.target - 0x408000 - row.offset - 4) & 0xFFFFFFFF
        struct.pack_into("<I", code, row.offset, value)
    view = pe.inspect_pe(scalar)
    hooks = []
    for va, size in ((0x401000, 8), (0x401040, 5)):
        offset = view.file_offset(va - view.image_base, size)
        hooks.append(pe.HookPatch(offset, va - view.image_base, va, scalar[offset:offset + size],
            b"\xe9" + struct.pack("<i", 0x408000 - va - 5) + b"\x90" * (size - 5), "synthetic branch",
            (pe.CodeRelocation(1, "rel32", 0x408000, "synthetic hook transfer"),)))
    result = pe._extend_verified_image(scalar, code=bytes(code), code_va=0x408000, relocations=fields,
        hooks=tuple(hooks), removed_highlow_rvas=(0x1001,), binding=dict(original_sha256=tool.BASE_SHA256,
            stage=tool.FROZEN_STAGE, resolution=resolution, selected_patches=patches))
    layout = geometry.FramedViewport(width, height)
    metadata = dict(result.metadata, runtime_executed=False, manual_input_proof=False, promotion_ready=False,
        generated_at="synthetic top-level generation stamp",
        source_observation={"generated_at": "retained nested source stamp",
                            "rows": [{"generated_at": "retained nested row stamp"}]},
        minimap_viewport=True, framed_validation=True, initial_paint=True,
        installed_hook_names=["synthetic-one", "synthetic-two"], extension_payload_size=len(code),
        extension_payload_sha256=tool.sha256(bytes(code)),
        layout_contract=dict(profile="native_four_border_tiles_v1", physical_surface=[0, 0, width - 1, height - 1],
            terrain=list(layout.terrain.as_tuple()), full_tiles=list(layout.full_tiles), unsupported_context_is_native_fallback=True),
        frame_presentation_contract={"frame_bands_inclusive": [row.as_tuple() for row in layout.frame_bands]},
        minimap_viewport_revision="framed_minimap_actual_terrain_v1",
        minimap_viewport_contract={"statuses": {"2": "preserved native640 fallback"}})
    return original, result.image, metadata


def trusted_context(resolution="1366x768"):
    """Fresh, untampered expected producer output, independent of incoming metadata."""
    _, expected_image, expected_metadata = fixture(resolution)
    return expected_image, expected_metadata


def corrupt(image, metadata, offset):
    data, meta = bytearray(image), deepcopy(metadata)
    data[offset] ^= 1
    for row in meta["edits"]:
        start, size = row["offset"], len(bytes.fromhex(row["new_hex"]))
        if start <= offset < start + size:
            row["new_hex"] = bytes(data[start:start + size]).hex()
    meta["output_sha256"] = tool.sha256(bytes(data))
    return bytes(data), meta


class SourceTests(unittest.TestCase):
    def test_exact_source_snapshots_and_private_namespace_cleanup(self):
        sources = tool._sources()
        self.assertEqual(len(tool.RESOLUTIONS), 9)
        self.assertNotIn("802x602", tool.RESOLUTIONS)
        self.assertEqual(set(tool.MODULE_ORDER), set(tool.PINNED_SOURCES))
        self.assertFalse(any("modal" in name or "complete_hd" in name or "army" in name for name in sources))
        before = list(sys.path)
        alias = types.ModuleType("tools.build_framed_candidate")
        alias.build_candidate = lambda *args, **kwargs: self.fail("public producer alias called")
        with patch.dict(sys.modules, {alias.__name__: alias}):
            with tool._producer(sources) as modules:
                builder = modules["tools/build_framed_candidate.py"]
                self.assertEqual(builder.STAGE, tool.FROZEN_STAGE)
                self.assertIsNot(builder, alias)
                self.assertTrue(builder.build_candidate.__module__.startswith("_clash95_framed_all_presets_"))
                for name, module in modules.items():
                    self.assertEqual(Path(module.__file__).resolve(), ROOT / name)
            self.assertIs(sys.modules[alias.__name__], alias)
        self.assertEqual(sys.path, before)
        self.assertFalse(any(name.startswith("_clash95_framed_all_presets_") for name in sys.modules))
        damaged = dict(sources)
        damaged[tool.MODULE_ORDER[-1]] = b"raise ValueError('synthetic compile failure')\n"
        with self.assertRaisesRegex(ValueError, "synthetic compile failure"), tool._producer(damaged):
            self.fail("unexpected producer")
        self.assertEqual(sys.path, before)
        self.assertFalse(any(name.startswith("_clash95_framed_all_presets_") for name in sys.modules))

    def test_original_selector_source_and_constructor_path_rejections(self):
        for original in (b"fixture", bytearray(b"fixture"), None):
            with self.subTest(original=type(original)), self.assertRaises(ValueError):
                tool.build_candidate(original, "1366x768")
        with patch.object(tool, "sha256", return_value=tool.BASE_SHA256), patch.object(tool, "_sources", side_effect=AssertionError):
            for resolution in ("802x602", "1366X768", "01366x768", "1600x900", True, None):
                with self.subTest(resolution=resolution), self.assertRaises(ValueError):
                    tool.build_candidate(b"fixture", resolution)
        read = Path.read_bytes
        def tamper(path):
            result = read(path)
            return result + b"\n# unreviewed\n" if path == ROOT / "src/patcher/framed_minimap.py" else result
        with patch.object(Path, "read_bytes", tamper), self.assertRaisesRegex(ValueError, "producer source differs"):
            tool._sources()
        with patch.object(tool, "__file__", str(ROOT / "tools/fixture.py")), self.assertRaisesRegex(ValueError, "constructor path"):
            tool._sources()

    def test_only_top_level_timestamp_is_omitted_from_metadata(self):
        original = {"generated_at": "one", "stage": "validation", "nested": {"generated_at": "two", "pass": False},
                    "records": ({"generated_at": "three", "kind": "abs32"},), "timestamp": "retained"}
        self.assertEqual(tool._deterministic(original), {"stage": "validation",
                         "nested": {"generated_at": "two", "pass": False},
                         "records": [{"generated_at": "three", "kind": "abs32"}], "timestamp": "retained"})
        self.assertIn("generated_at", original)


class FinalImageTests(unittest.TestCase):
    def test_independent_source_context_is_required_and_cannot_alias_incoming_metadata(self):
        original, image, metadata = fixture()
        for context in (None, (), [], (image,), (image, None), (bytearray(image), metadata), (image, metadata)):
            with self.subTest(context_type=type(context)), self.assertRaisesRegex(ValueError, "source context required"):
                tool._audit(original, image, metadata, "1366x768", pe, geometry, source_context=context)
        with self.assertRaisesRegex(ValueError, "source context required"):
            tool._audit(original, image, metadata, "1366x768", pe, geometry)
        expected_image, expected_metadata = trusted_context()
        changed = bytearray(expected_image); changed[-1] ^= 1
        with self.assertRaisesRegex(ValueError, "source bytes differ"):
            tool._audit(original, image, metadata, "1366x768", pe, geometry,
                        source_context=(bytes(changed), expected_metadata))

    def test_omitted_code_rel32_and_native_hook_operands_fail_source_admission(self):
        original, image, metadata = fixture()
        context = trusted_context()
        self.assertTrue(any(row["kind"] == "rel32" for row in context[1]["relocations"]))
        self.assertTrue(context[1]["hook_relocations"])
        mutations = (
            lambda m: m.update(relocations=[row for row in m["relocations"] if row["kind"] != "rel32"]),
            lambda m: m.update(hook_relocations=[]),
            lambda m: m.pop("hook_relocations"),
            lambda m: m.update(code_rva=float(m["code_rva"])),
        )
        for index, mutate in enumerate(mutations):
            incoming = deepcopy(metadata); mutate(incoming)
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "source metadata identity"):
                tool._audit(original, image, incoming, "1366x768", pe, geometry, source_context=context)
        self.assertEqual(context, trusted_context())

    def test_every_numeric_metadata_value_rejects_type_coercion(self):
        original, image, metadata = fixture()
        context = trusted_context()
        def numeric_paths(value, path=()):
            if type(value) in (int, float, bool):
                yield path, value
            elif type(value) is dict:
                for key, item in value.items(): yield from numeric_paths(item, path + (key,))
            elif type(value) in (list, tuple):
                for index, item in enumerate(value): yield from numeric_paths(item, path + (index,))
        cases = list(numeric_paths(metadata))
        self.assertGreater(len(cases), 30)
        self.assertIn(("code_rva",), [path for path, _ in cases])
        for path, value in cases:
            incoming = json.loads(json.dumps(metadata))
            cursor = incoming
            for key in path[:-1]: cursor = cursor[key]
            cursor[path[-1]] = int(value) if type(value) is bool else float(value) if type(value) is int else int(value)
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "source metadata identity"):
                tool._audit(original, image, incoming, "1366x768", pe, geometry, source_context=context)
        self.assertEqual(context, trusted_context())

    def test_only_root_generation_stamp_is_ignored_by_source_admission(self):
        original, image, metadata = fixture()
        context = trusted_context()
        incoming = deepcopy(metadata)
        incoming["generated_at"] = "different synthetic wall-clock value"
        audit = tool._audit(original, image, incoming, "1366x768", pe, geometry, source_context=context)
        self.assertEqual(audit["section_count"], 8)
        normalized = tool._deterministic(metadata)
        self.assertNotIn("generated_at", normalized)
        self.assertEqual(normalized["source_observation"]["generated_at"], "retained nested source stamp")
        self.assertEqual(normalized["source_observation"]["rows"][0]["generated_at"], "retained nested row stamp")
        for path in (("source_observation", "generated_at"), ("source_observation", "rows", 0, "generated_at")):
            for remove in (False, True):
                incoming = deepcopy(metadata)
                cursor = incoming
                for key in path[:-1]: cursor = cursor[key]
                if remove: del cursor[path[-1]]
                else: cursor[path[-1]] = "invented nested generation value"
                with self.subTest(path=path, remove=remove), self.assertRaisesRegex(ValueError, "source metadata identity"):
                    tool._audit(original, image, incoming, "1366x768", pe, geometry, source_context=context)

    def test_exact_source_owned_dgroup_fallback_has_no_general_data_target_permission(self):
        section = pe.Section(b"DGROUP\0\0", 0x258, 0, 0x110000, 0x20000, 0x10E200, 0xC0000040)
        before = types.SimpleNamespace(image_base=0x400000, sections=(section,),
                                      file_offset=lambda rva, size: section.raw_offset + rva - section.rva)
        # VA 0x51BE00 maps to file 0x11A000 within this independent fixture.
        self.assertEqual(before.file_offset(0x11BE00, 256), 0x11A000)
        row = dict(kind="rel32", target=0x51BE00, purpose="framed_gate_old_c5_fallback")
        patch_row = dict(offset=0x11A000, group="frame-restore-bands", new_hex=bytes(256).hex())
        self.assertTrue(tool._owned_target(row, before, before, [patch_row]))
        for changes in ({"target": 0x51BE01}, {"target": 0x51BF00}, {"purpose": "native_fallback"}):
            self.assertFalse(tool._owned_target(row | changes, before, before, [patch_row]))
        for changes in ({"offset": 0x11A001}, {"group": "other-cave"}, {"new_hex": bytes(255).hex()}):
            self.assertFalse(tool._owned_target(row, before, before, [patch_row | changes]))
        self.assertFalse(tool._owned_target(row, before, before, [patch_row, patch_row]))
        wrong = types.SimpleNamespace(image_base=0x400000,
            sections=(pe.Section(b".data", section.header_offset, section.virtual_size, section.rva,
                                 section.raw_size, section.raw_offset, section.characteristics),), file_offset=before.file_offset)
        self.assertFalse(tool._owned_target(row, wrong, wrong, [patch_row]))
        wrong = types.SimpleNamespace(image_base=0x400000, sections=(section,), file_offset=lambda rva, size: 0x11A001)
        self.assertFalse(tool._owned_target(row, wrong, wrong, [patch_row]))

    def test_all_nine_geometry_pe_replay_and_independent_relocation_at_two_bases(self):
        for resolution in tool.RESOLUTIONS:
            with self.subTest(resolution=resolution):
                original, image, metadata = fixture(resolution)
                audit = tool._audit(original, image, metadata, resolution, pe, geometry,
                                    source_context=trusted_context(resolution))
                self.assertEqual((audit["section_count"], audit["new_mutable_state_bytes"], audit["displaced_highlow_count"]), (8, 0, 1))
                self.assertTrue(audit["native_modal_fallback_retained"])
                width, height = map(int, resolution.split("x"))
                layout = geometry.FramedViewport(width, height)
                self.assertEqual(sum(row.area for row in layout.frame_bands) + layout.terrain.area, width * height)
                for row in layout.frame_bands:
                    self.assertTrue(layout.surface.contains(row))
                    self.assertIsNone(row.intersection(layout.terrain))
                self.assertEqual(len(layout.action_cells), 6)
                self.assertTrue(all(layout.terrain.contains(row) for row in layout.action_cells))
                self.assertEqual(layout.minimap_right_anchor, width - 32)
                for column, row in ((0, 0), (layout.ceil_tiles[0] - 1, layout.ceil_tiles[1] - 1)):
                    self.assertTrue(layout.terrain.contains(layout.cell_rect(column, row)))
                view = pe.inspect_pe(image)
                records = tool.byte_records(original, image, view)
                self.assertEqual(tool.apply_records(original, records, expected_base_sha256=tool.sha256(original), view=view), image)
                memory, _, fields, _ = independent_image(image)
                self.assertEqual(sorted(fields), [0x1009, 0x1011, 0x8001, 0x8015])
                for delta in (-0x100000, 0x2100000):
                    moved = rebase(memory, fields, delta)
                    self.assertEqual(struct.unpack_from("<I", moved, 0x8001)[0], 0x402008 + delta)
                    self.assertEqual(struct.unpack_from("<I", moved, 0x8015)[0], 0x408020 + delta)
                    self.assertEqual(moved[0x800A:0x800E], memory[0x800A:0x800E])
                    self.assertEqual(moved[0x1001:0x1005], memory[0x1001:0x1005])

    def test_final_claims_parent_scalar_geometry_hook_and_operand_tamper_fail(self):
        original, image, metadata = fixture()
        for key, value in (("stage", "stable"), ("resolution", "802x602"), ("original_sha256", "0" * 64),
                           ("input_sha256", "0" * 64), ("characteristics", 0xE0000020), ("append_bytes", 1),
                           ("minimap_viewport", False), ("selected_patches", []), ("hooks", metadata["hooks"][:1]),
                           ("removed_highlow", []), ("relocations", metadata["relocations"][1:]),
                           ("old_relocation_sha256", "0" * 64)):
            bad = deepcopy(metadata)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                tool._audit(original, image, bad, "1366x768", pe, geometry, source_context=trusted_context())
        for key in tool.FALSE_CLAIMS[:4]:
            bad = deepcopy(metadata)
            bad[key] = True
            with self.subTest(key=key), self.assertRaises(ValueError):
                tool._audit(original, image, bad, "1366x768", pe, geometry, source_context=trusted_context())
        bad = deepcopy(metadata)
        bad["selected_patches"][0]["old_hex"] = "00000000"
        with self.assertRaisesRegex(ValueError, "source metadata identity"):
            tool._audit(original, image, bad, "1366x768", pe, geometry, source_context=trusted_context())
        for name in ("terrain", "full_tiles"):
            bad = deepcopy(metadata)
            bad["layout_contract"][name][0] += 1
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "source metadata identity"):
                tool._audit(original, image, bad, "1366x768", pe, geometry, source_context=trusted_context())
        bad = deepcopy(metadata)
        bad["frame_presentation_contract"]["frame_bands_inclusive"] = bad["frame_presentation_contract"]["frame_bands_inclusive"][:3]
        with self.assertRaisesRegex(ValueError, "source metadata identity"):
            tool._audit(original, image, bad, "1366x768", pe, geometry, source_context=trusted_context())
        bad = deepcopy(metadata)
        bad["hook_relocations"][0]["target"] += 1
        with self.assertRaisesRegex(ValueError, "source metadata identity"):
            tool._audit(original, image, bad, "1366x768", pe, geometry, source_context=trusted_context())
        bad = deepcopy(metadata)
        bad["relocations"].append(deepcopy(bad["relocations"][0]))
        with self.assertRaisesRegex(ValueError, "source metadata identity"):
            tool._audit(original, image, bad, "1366x768", pe, geometry, source_context=trusted_context())
        bad = deepcopy(metadata)
        bad["relocations"][1]["target"] = 0x402008
        with self.assertRaisesRegex(ValueError, "source metadata identity"):
            tool._audit(original, image, bad, "1366x768", pe, geometry, source_context=trusted_context())

    def test_padding_code_directory_header_and_replay_rejections(self):
        original, image, metadata = fixture()
        view = pe.inspect_pe(image)
        code = view.sections[-1]
        for offset in (code.raw_offset, code.raw_offset + metadata["code_bytes"], code.raw_offset + code.virtual_size,
                       code.header_offset + 36, code.header_offset + 8, view.optional_offset + 136):
            data, bad = corrupt(image, metadata, offset)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                tool._audit(original, data, bad, "1366x768", pe, geometry, source_context=trusted_context())
        rows = tool.byte_records(original, image, view)
        index = next(i for i, row in enumerate(rows) if row["old_hex"])
        for key, value in (("old_hex", "00"), ("stage", "stable"), ("file_offset", True), ("rva", 0),
                           ("new_hex", "AA"), ("rationale", ""), ("appended", 1)):
            bad = deepcopy(rows)
            bad[index][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                tool.apply_records(original, bad, expected_base_sha256=tool.sha256(original), view=view)
        with self.assertRaises(ValueError):
            tool.apply_records(original, rows, expected_base_sha256="0" * 64, view=view)
        with self.assertRaises(ValueError):
            tool.apply_records(original, [rows[0], rows[0]] + rows[1:], expected_base_sha256=tool.sha256(original), view=view)


class ProbeTests(unittest.TestCase):
    def inherited(self, image, resolution):
        return (".if ((wo(00400000) != 5a4d)) { .echo PTILE_CONTRACT_FAIL; q }\n"
                f".echo PTILE_CONTRACT_PASS stage={tool.FROZEN_STAGE} resolution={resolution} candidate_sha256={tool.sha256(image)}\n"
                ".echo PTILE_SCOPE guarded_map_only manual_input_proof=false promotion_ready=false\n"
                ".echo PTILE_OBSERVER_UNCHANGED\n")
    def test_all_nine_candidate_bound_final_predicates_and_inherited_observer(self):
        for resolution in tool.RESOLUTIONS:
            with self.subTest(resolution=resolution):
                _, image, metadata = fixture(resolution)
                inherited = self.inherited(image, resolution)
                probe, contract = tool._probe(image, metadata, inherited, resolution, "a" * 64, pe)
                self.assertEqual(probe.count("_CONTRACT_PASS"), 1)
                self.assertIn("revision=" + tool.REVISION, probe)
                self.assertIn("producer_sha256=" + "a" * 64, probe)
                self.assertIn(".echo PTILE_OBSERVER_UNCHANGED", probe)
                self.assertTrue(contract["preferred_address_only"] and contract["initial_map_only"])
                view = pe.inspect_pe(image)
                for match in tool.PREDICATE.finditer(probe):
                    kind, address, expected = match.groups()
                    self.assertEqual(int.from_bytes(tool._loaded_bytes(image, view, int(address, 16), 2 if kind == "wo" else 1), "little"), int(expected, 16))
                self.assertEqual(tool._loaded_bytes(image, view, 0x402000, 8), bytes(8))
    def test_wrong_marker_predicate_missing_failure_and_ancestor_marker_rejected(self):
        _, image, metadata = fixture()
        inherited = self.inherited(image, "1366x768")
        for variant in (inherited.replace("5a4d", "ffff"), inherited.replace("CONTRACT_FAIL", "UNVERIFIED"),
                        inherited.replace(tool.FROZEN_STAGE, "stable"), inherited.replace("wo(00400000)", "poi(00400000)"),
                        inherited + ".echo FOREIGN_CONTRACT_PASS\n", inherited + inherited):
            with self.subTest(variant=variant[:50]), self.assertRaises(ValueError):
                tool._probe(image, metadata, variant, "1366x768", "a" * 64, pe)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", action="store_true", help="one preset twice in memory; deterministic outputs only")
    args = parser.parse_args(argv)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if not result.wasSuccessful():
        return 1
    if args.original_backed:
        original = Path("C:/Clash/clash95.exe").read_bytes()
        first = tool.build_candidate(original, "1366x768")
        second = tool.build_candidate(original, "1366x768")
        assert first[0] == second[0] and first[2] == second[2]
        assert json.dumps(first[1], sort_keys=True, allow_nan=False) == json.dumps(second[1], sort_keys=True, allow_nan=False)
        image, metadata, probe = first
        assert all(metadata[key] is False for key in tool.FALSE_CLAIMS)
        assert metadata["candidate_sha256"] == tool.sha256(image) and metadata["probe_sha256"] == tool.sha256(probe.encode())
        print("ORIGINAL_BACKED_DETERMINISTIC_CONSTRUCTION_PASS resolution=1366x768 candidate_sha256=" + tool.sha256(image)
              + " bytes=" + str(len(image)) + " runtime_executed=false promotion_ready=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
