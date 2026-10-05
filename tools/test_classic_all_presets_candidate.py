#!/usr/bin/env python3
"""Source and synthetic PE fixtures; no files, native processes or runtime.

--original-backed optionally reconstructs one narrow and one wide candidate
in memory from the user-owned original. It is not a runtime acceptance lane.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import re
import struct
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.patcher import classic_all_presets_candidate as tool
from src.patcher import classic_menu_candidate as menu
from src.patcher import patch_clash95_hd as scalar
from src.patcher import pe_extension as pe


def fixture(resolution="1366x768"):
    """Synthetic seven-section image, not an admitted original executable."""
    original = bytearray(0x150E00)
    original[:2] = b"MZ"
    struct.pack_into("<I", original, 0x3C, 0x70)
    original[0x70:0x74] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", original, 0x74, 0x14C, 7, 0, 0, 0, 224, 0x182)
    opt = 0x88
    struct.pack_into("<H", original, opt, 0x10B)
    struct.pack_into("<I", original, opt + 4, 0x150000)
    struct.pack_into("<III", original, opt + 28, 0x400000, 4096, 512)
    struct.pack_into("<II", original, opt + 56, 0x157000, 1024)
    struct.pack_into("<I", original, opt + 92, 16)
    struct.pack_into("<II", original, opt + 136, 0x156000, 16)
    sections = (
        (b".text", 0x1000, 0x150000, 0x400, 0x60000020),
        (b".rdata", 0x151000, 512, 0x150400, 0x40000040),
        (b".data", 0x152000, 512, 0x150600, 0xC0000040),
        (b".bss", 0x153000, 4096, 0, 0xC0000080),
        (b".one", 0x154000, 512, 0x150800, 0x40000040),
        (b".two", 0x155000, 512, 0x150A00, 0x40000040),
        (b".reloc", 0x156000, 512, 0x150C00, 0x42000040),
    )
    for index, (name, rva, size, raw, flags) in enumerate(sections):
        struct.pack_into("<8sIIIIIIHHI", original, 0x168 + index * 40,
                         name, 0, rva, size, raw, 0, 0, 0, 0, flags)
    for offset, value in ((0x501, 0x401200), (0x509, 0x402200), (0x511, 0x403200)):
        struct.pack_into("<I", original, offset, value)
    struct.pack_into("<II4H", original, 0x150C00, 0x1000, 16, 0x3101, 0x3109, 0x3111, 0)
    view = pe.inspect_pe(bytes(original))
    records, index = [], 0
    for table, count in menu.TABLES:
        offset = view.file_offset(table - view.image_base, count * 53 + 4)
        for row in range(count):
            x, y, callback = 100 + index * 5, 80 + row * 5, 0x401200 + index * 16
            struct.pack_into("<ii", original, offset + row * 53, x, y)
            struct.pack_into("<I", original, offset + row * 53 + 12, menu.MENU_SPRITES)
            struct.pack_into("<I", original, offset + row * 53 + 32, callback)
            records.append((offset + row * 53, x, y))
            index += 1
        original[offset + count * 53:offset + count * 53 + 4] = b"\xff" * 4
    for index, (_, address, size, within) in enumerate(menu.SITES):
        offset = view.file_offset(address - view.image_base, size)
        original[offset:offset + size] = b"\x90" * size
        original[offset + within:offset + within + 6] = menu.PREFIXES[index] + struct.pack("<I", 640)
    original = bytes(original)
    profile = scalar.parse_resolution(resolution)
    patches = [scalar.Patch("synthetic-width", 0x1200, "00000000", struct.pack("<I", profile.width).hex(),
                            "Synthetic scalar byte field, no game behavior claim")]
    for offset, x, y in records:
        patches.append(scalar.Patch("synthetic-menu", offset, original[offset:offset + 8].hex(),
            struct.pack("<ii", x + profile.off_x, y + profile.off_y).hex(), "Synthetic centered menu record"))
    base = bytearray(original)
    for row in patches:
        base[row.offset:row.offset + len(row.new)] = row.new
    return original, bytes(base), tuple(patches)


def wide_fixture(resolution="1366x768"):
    original, base, patches = fixture(resolution)
    view = pe.inspect_pe(base)
    native_records, tables = menu._native_records(original, base, scalar.parse_resolution(resolution))
    width, height = map(int, resolution.split("x"))
    emitted = menu.emit_guards(base_va=view.image_base + view.image_size,
                              width=width, height=height, records=native_records)
    hooks, windows = [], []
    for name, address, size, within in menu.SITES:
        offset = view.file_offset(address - view.image_base, size)
        old = original[offset + within:offset + within + 6]
        va, target = address + within, emitted.entries[name]
        hooks.append(pe.HookPatch(offset + within, va - view.image_base, va, old,
            b"\xe8" + struct.pack("<i", target - va - 5) + b"\x90", "classic_menu." + name,
            (pe.CodeRelocation(1, "rel32", target, "menu-only descriptor bound"),)))
        windows.append(dict(va=address, bytes=size, predecessor_sha256=tool.sha256(original[offset:offset + size])))
    result = pe._extend_verified_image(base, code=emitted.code, code_va=emitted.base_va,
        relocations=emitted.relocations, hooks=hooks, binding=dict(stage=menu.STAGE,
        recipe_revision=menu.REVISION, base_stage=scalar.DEFAULT_STAGE, resolution=resolution,
        original_sha256=tool.BASE_SHA256, base_candidate_sha256=tool.sha256(base)))
    metadata = dict(result.metadata, schema="clash95_classic_menu_candidate_v1",
        candidate_sha256=tool.sha256(result.image), source_hashes=dict(menu.PINNED) | {
            menu.SOURCE: tool.sha256((ROOT / menu.SOURCE).read_bytes())},
        menu_records=[dict(x=x, y=y, callback=callback) for x, y, callback in native_records],
        menu_tables=tables, dispatcher_windows=windows, entry_vas=emitted.entries,
        patch_records=[dict(group=row.group, offset=row.offset, old_hex=row.old.hex(), new_hex=row.new.hex())
                       for row in patches],
        policy="Only exact original menu/campaign/multiplayer/options/load x/y/callback records "
               "with the native menu holder use the physical bound; every other descriptor retains signed x<640.",
        runtime_executed=False, gameplay_verified=False, manual_input_proof=False, promotion_ready=False)
    spans = [(view.image_base, result.image[:view.headers_size])]
    for row in patches:
        rva = next(section.rva + row.offset - section.raw_offset for section in view.sections
                   if section.raw_offset and section.raw_offset <= row.offset < section.raw_offset + section.raw_size)
        spans.append((view.image_base + rva, result.image[row.offset:row.offset + len(row.new)]))
    for row in tables + windows:
        offset = view.file_offset(row["va"] - view.image_base, row["bytes"])
        spans.append((row["va"], result.image[offset:offset + row["bytes"]]))
    spans.append((emitted.base_va, result.image[len(base):]))
    probe = menu.loaded_probe(result.image, metadata, spans)
    metadata["probe_sha256"] = tool.sha256(probe.encode())
    return original, base, result.image, metadata, probe, patches, spans


class SourceTests(unittest.TestCase):
    def test_nine_exact_presets_and_actual_predecessor_split(self):
        self.assertEqual(len(tool.RESOLUTIONS), 9)
        self.assertEqual(len(set(tool.RESOLUTIONS)), 9)
        self.assertEqual(tool.STAGE, scalar.DEFAULT_STAGE + "-classic-allpresets-validation")
        self.assertNotIn(tool.STAGE, scalar.STAGE_GROUPS)
        self.assertEqual(tool.REVISION, "classic_all_presets_v1")
        for index, resolution in enumerate(tool.RESOLUTIONS):
            self.assertEqual(tool._selected(resolution),
                (tool.SCALAR_REVISION, scalar.DEFAULT_STAGE) if index < 2 else (menu.REVISION, menu.STAGE))
            geometry = tool._geometry(resolution)
            profile = scalar.parse_resolution(resolution)
            self.assertEqual(geometry["full_tiles"], [profile.tiles_x, profile.tiles_y])
            self.assertEqual(geometry["partial_pixels"], [profile.partial_col_px, profile.partial_row_px])
            self.assertEqual(geometry["terrain"], [32, 16, profile.edge_x, profile.edge_y])
            self.assertEqual(geometry["minimap_right_anchor"], profile.width)
            self.assertFalse(geometry["framed_map"])
            self.assertFalse(geometry["minimap_viewport"])
            self.assertFalse(geometry["small_world_renderer_installed"])

    def test_frozen_source_pins_and_private_imports_preserve_public_modules(self):
        sources = tool._sources()
        before_path, before_modules = list(sys.path), set(sys.modules)
        alias = types.ModuleType("src.patcher.classic_menu_candidate")
        alias.__file__ = "unrelated/source.py"
        public_stage, public_revision = menu.STAGE, menu.REVISION
        with patch.dict(sys.modules, {alias.__name__: alias}):
            with tool._producer(sources) as (bound_scalar, bound_menu, parser):
                self.assertIsNot(bound_menu, menu)
                self.assertIsNot(bound_scalar, scalar)
                self.assertEqual(bound_menu.REVISION, public_revision)
                self.assertEqual(bound_menu.STAGE, public_stage)
                self.assertEqual(Path(bound_menu.__file__), ROOT / menu.SOURCE)
                self.assertIs(bound_menu.scalar, bound_scalar)
                self.assertIs(bound_menu.pe, parser)
                self.assertTrue(bound_menu.build_candidate.__module__.startswith("_clash95_classic_all_presets_"))
            self.assertIs(sys.modules[alias.__name__], alias)
        self.assertEqual((menu.STAGE, menu.REVISION), (public_stage, public_revision))
        self.assertEqual(sys.path, before_path)
        self.assertFalse(any(name.startswith("_clash95_classic_all_presets_") for name in set(sys.modules) - before_modules))

    def test_snapshot_and_missing_sources_reject_before_private_execution(self):
        sources = tool._sources()
        for kind in ("changed", "missing", "extra", "mutable"):
            supplied = dict(sources)
            key = tool.MODULE_ORDER[0]
            if kind == "changed": supplied[key] += b"\n# drift\n"
            elif kind == "missing": del supplied[key]
            elif kind == "extra": supplied["unreviewed.py"] = b"pass"
            else: supplied[key] = bytearray(supplied[key])
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "snapshot identity"):
                with tool._producer(supplied): self.fail("unexpected producer")
        read = Path.read_bytes
        target = ROOT / menu.SOURCE
        with patch.object(Path, "read_bytes", lambda path: read(path) + (b"\n# drift" if path == target else b"")):
            with self.assertRaisesRegex(ValueError, "producer source differs"): tool._sources()

    def test_exception_cleans_private_import_state(self):
        before_path = list(sys.path)
        with patch("builtins.exec", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                with tool._producer(tool._sources()): self.fail("unexpected producer")
        self.assertEqual(sys.path, before_path)
        self.assertFalse(any(name.startswith("_clash95_classic_all_presets_") for name in sys.modules))

    def test_unknown_original_and_custom_or_noncanonical_dimensions_reject(self):
        for original in (b"fixture", bytearray(b"fixture"), None):
            with self.subTest(original=type(original)), self.assertRaises(ValueError):
                tool.build_candidate(original, "800x600")
        with patch.object(tool, "sha256", return_value=tool.BASE_SHA256), \
                patch.object(tool, "_sources", side_effect=AssertionError("construction must not start")):
            for resolution in ("802x602", "1144x768", "800X600", "0800x600", "3840x2162", True, None):
                with self.subTest(resolution=resolution), self.assertRaises(ValueError):
                    tool.build_candidate(b"fixture", resolution)


class ImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wide = wide_fixture()

    def audit(self, image=None, metadata=None, inherited=None):
        original, base, candidate, parent, probe, patches, _ = self.wide
        return tool._audit_wide(original, base, candidate if image is None else image,
            parent if metadata is None else metadata, probe if inherited is None else inherited,
            patches, "1366x768", menu, pe)

    def test_all_nine_geometries_frozen_bytes_and_no_new_storage(self):
        for index, resolution in enumerate(tool.RESOLUTIONS):
            with self.subTest(resolution=resolution):
                if index < 2:
                    original, candidate, patches = fixture(resolution)
                    audit = tool._audit_scalar(original, candidate, patches, resolution, pe)
                    self.assertEqual(audit["section_count"], 7)
                    self.assertEqual(audit["menu_hook_count"], 0)
                else:
                    original, base, candidate, metadata, inherited, patches, _ = wide_fixture(resolution)
                    audit, _ = tool._audit_wide(original, base, candidate, metadata, inherited,
                                               patches, resolution, menu, pe)
                    self.assertEqual(audit["section_count"], 8)
                    self.assertEqual(audit["menu_hook_count"], 2)
                self.assertEqual(audit["new_state_bytes"], 0)
                self.assertTrue(audit["only_frozen_predecessor_bytes"])
                self.assertFalse(audit["inherited_operand_completeness_proven"])
                records = tool.byte_records(original, candidate, pe.inspect_pe(candidate))
                self.assertEqual(tool.apply_records(original, records,
                    expected_base_sha256=tool.sha256(original), view=pe.inspect_pe(candidate)), candidate)

    def test_wide_full_metadata_code_hooks_and_relocations(self):
        original, base, candidate, metadata, _, _, _ = self.wide
        audit, _ = self.audit()
        self.assertEqual(audit["declared_menu_operand_count"], len(metadata["relocations"]))
        self.assertEqual([row["va"] for row in metadata["hooks"]], [0x419D63, 0x419D8C])
        self.assertEqual(metadata["base_candidate_sha256"], tool.sha256(base))
        self.assertEqual(pe.inspect_pe(candidate).sections[:7], pe.inspect_pe(original).sections)
        self.assertEqual(metadata["removed_highlow"], [])
        for name in ("installation_ready", "runtime_executed", "gameplay_verified", "manual_input_proof", "promotion_ready"):
            self.assertIs(metadata[name], False)

    def test_missing_duplicate_and_retargeted_operands_or_hooks_reject(self):
        metadata = self.wide[3]
        mutations = (
            lambda m: m["relocations"].pop(),
            lambda m: m["relocations"].append(deepcopy(m["relocations"][0])),
            lambda m: m["relocations"][0].update(target=0x401200),
            lambda m: m["relocations"][0].update(kind="rel32"),
            lambda m: m["hook_relocations"].pop(),
            lambda m: m["hooks"].pop(),
            lambda m: m["hooks"][0].update(old_hex="00" * 6),
            lambda m: m["entry_vas"].update(single=0x401200),
            lambda m: m["source_hashes"].pop(menu.SOURCE),
        )
        for index, mutate in enumerate(mutations):
            changed = deepcopy(metadata); mutate(changed)
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "wide metadata"):
                self.audit(metadata=changed)

    def test_exact_metadata_types_profile_sources_and_false_claims(self):
        for key, value in (("installation_ready", 0), ("runtime_executed", True),
                           ("new_highlow_count", True), ("stage", tool.STAGE),
                           ("resolution", "1280x720"), ("recipe_revision", tool.REVISION),
                           ("base_candidate_sha256", "0" * 64), ("unknown_claim", True)):
            changed = deepcopy(self.wide[3]); changed[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "wide metadata"):
                self.audit(metadata=changed)

    def test_code_hooks_headers_relocation_table_and_padding_tamper_reject(self):
        candidate, metadata = self.wide[2], self.wide[3]
        view = pe.inspect_pe(candidate)
        offsets = [view.pe_offset + 6, view.optional_offset + 4, view.optional_offset + 56,
                   view.sections[-1].header_offset, view.sections[-1].header_offset + 36,
                   metadata["append_offset"], metadata["append_offset"] + metadata["code_bytes"],
                   view.file_offset(view.relocation_rva, view.relocation_size),
                   metadata["hooks"][0]["offset"], len(candidate) - 1]
        for offset in offsets:
            image = bytearray(candidate); image[offset] ^= 1
            changed = deepcopy(metadata)
            changed["candidate_sha256"] = changed["output_sha256"] = tool.sha256(bytes(image))
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                self.audit(image=bytes(image), metadata=changed)

    def test_scalar_outside_patch_old_bytes_overlap_and_headers_reject(self):
        original, candidate, patches = fixture("800x600")
        changed = bytearray(candidate); changed[0x1300] ^= 1
        with self.assertRaisesRegex(ValueError, "reconstruction differs"):
            tool._audit_scalar(original, bytes(changed), patches, "800x600", pe)
        for supplied in (patches + (patches[0],), (scalar.Patch("bad", 0x1200, "01000000", "02000000", "bad"),)):
            with self.assertRaises(ValueError): tool._scalar_replay(original, supplied)
        changed = bytearray(original); changed[0x7C] ^= 1
        with self.assertRaises(ValueError): tool._audit_scalar(original, bytes(changed), (), "800x600", pe)

    def test_record_old_bytes_mapping_order_types_and_missing_final_bytes(self):
        original, _, candidate, _, _, _, _ = self.wide
        view = pe.inspect_pe(candidate)
        records = tool.byte_records(original, candidate, view)
        self.assertTrue(any(row["appended"] for row in records))
        for key, value in (("offset", True), ("va", 1), ("stage", tool.STABLE_STAGE),
                           ("appended", 1), ("old_hex", "ff"), ("group", "invented")):
            changed = deepcopy(records); changed[0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                tool.apply_records(original, changed, expected_base_sha256=tool.sha256(original), view=view)
        with self.assertRaises(ValueError):
            tool.apply_records(original, records[::-1], expected_base_sha256=tool.sha256(original), view=view)
        self.assertNotEqual(tool.apply_records(original, records[:-1],
            expected_base_sha256=tool.sha256(original), view=view), candidate)

    def test_canonical_wide_probe_and_all_parent_predicates_are_bound(self):
        _, _, candidate, _, inherited, _, spans = self.wide
        probe, contract = tool._probe(candidate, "1366x768", "a" * 64, spans, pe, inherited)
        predicates = set(re.findall(r"by\([0-9a-f]{8}\) != [0-9a-f]+", inherited))
        self.assertTrue(predicates <= set(re.findall(r"by\([0-9a-f]{8}\) != [0-9a-f]+", probe)))
        self.assertEqual(probe.count(".echo CLASSICALLPRESETS_CONTRACT_PASS "), 1)
        self.assertNotIn("CLASSICMENU_CONTRACT_PASS", probe)
        self.assertIn("predecessor_revision=classic_menu_widgets_v1", probe)
        self.assertTrue(contract["preferred_address_only"])
        self.assertFalse(contract["runtime_observation_protocol"])
        self.assertTrue(all(len(line.encode("ascii")) < 4096 for line in probe.splitlines()))
        self.assertEqual(tool._probe(candidate, "1366x768", "a" * 64, spans, pe, inherited), (probe, contract))
        for changed in (inherited + ".echo invented pass\n", inherited.replace("CLASSICMENU_CONTRACT_PASS", "FAKE_PASS"),
                        inherited.replace("by(00400000) != 4d", "by(00400000) != 0")):
            with self.subTest(probe=changed[-40:]), self.assertRaises(ValueError): self.audit(inherited=changed)

    def test_probe_missing_foreign_wrong_bytes_and_narrow_predecessor_reject(self):
        _, _, candidate, _, inherited, _, spans = self.wide
        with self.assertRaises(ValueError): tool._probe(candidate, "1366x768", "a" * 64, spans, pe)
        with self.assertRaises(ValueError): tool._probe(candidate, "1366x768", "a" * 64, spans[1:], pe, inherited)
        bad = list(spans); bad[0] = (bad[0][0], b"\0" + bad[0][1][1:])
        with self.assertRaises(ValueError): tool._probe(candidate, "1366x768", "a" * 64, bad, pe, inherited)
        with self.assertRaises(ValueError): tool._probe(candidate, "1366x768", "a" * 64, [(0x70000000, b"x")], pe, inherited)
        original, narrow, patches = fixture("800x600")
        view = pe.inspect_pe(narrow)
        narrow_spans = [(view.image_base, narrow[:view.headers_size])]
        for row in patches:
            narrow_spans.append((tool._address(view, row.offset, len(row.new))[1], row.new))
        probe, contract = tool._probe(narrow, "800x600", "a" * 64, narrow_spans, pe)
        self.assertIn("predecessor_revision=classic-frozen-800-v1", probe)
        self.assertIsNone(contract["inherited_probe_sha256"])
        with self.assertRaises(ValueError): tool._probe(narrow, "800x600", "a" * 64, narrow_spans, pe, inherited)


def original_backed():
    original = Path("C:/Clash/clash95.exe").read_bytes()
    before = tool.sha256(original)
    for resolution in ("1024x768", "1366x768"):
        candidate, metadata, probe = tool.build_candidate(original, resolution)
        if not all(metadata[name] is False for name in tool.FALSE_CLAIMS):
            raise AssertionError("source constructor granted acceptance")
        if metadata["probe_sha256"] != tool.sha256(probe.encode()):
            raise AssertionError("probe identity differs")
        print(f"CLASSIC_ORIGINAL_MEMORY_ONLY resolution={resolution} candidate_sha256={tool.sha256(candidate)} "
              f"bytes={len(candidate)} predecessor={metadata['predecessor_recipe']} "
              f"sections={metadata['structural_gate']['section_count']} runtime=false promotion=false")
    if before != tool.BASE_SHA256 or Path("C:/Clash/clash95.exe").read_bytes() != original:
        raise AssertionError("original identity changed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", action="store_true")
    args, remaining = parser.parse_known_args()
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful(): raise SystemExit(1)
    if args.original_backed: original_backed()
