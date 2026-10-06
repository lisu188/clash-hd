#!/usr/bin/env python3
"""Portable V2 allocation/relayout rejection fixtures; no native or outputs.

The explicit synthetic issuer below is test authority only. It cannot issue a
production parent or original identity. --original-backed adds one Classic and
one Modal canonical reconstruction in RAM. Neither mode installs a candidate,
publishes provider records, or establishes runtime/release acceptance.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, replace
import hashlib
from pathlib import Path
import struct
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.patcher import battle_profile_context_v2 as tool
from tools.test_battle_profile_context import fixture

ORIGINAL = None


def sha(data):
    return hashlib.sha256(data).hexdigest()


@contextmanager
def synthetic_issuer():
    """Compile an isolated canonical source; only its pure layout is callable."""
    raw = (ROOT / tool.SOURCE).read_bytes()
    name = "_context_v2_synthetic_fixture_" + uuid.uuid4().hex
    module = ModuleType(name)
    module.__file__ = str(ROOT / tool.SOURCE)
    module.__canonical_context_v2_issuer__ = True
    module.__loaded_source_sha256__ = sha(raw)
    sys.modules[name] = module
    try:
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
        yield module
    finally:
        if sys.modules.get(name) is not module:
            raise AssertionError("fixture namespace replaced")
        del sys.modules[name]


def synthetic_context(issuer, profile="modalwidgets", resolution="1366x768", values=None):
    original, parent, meta = fixture(profile, resolution) if values is None else values
    relayout, layout = issuer._layout(original, parent, profile, resolution, meta["stage"])
    return original, parent, relayout, layout


def auxiliary_fixture(profile="modalwidgets"):
    """Independent COFF/debug/security offset ledger around a synthetic parent."""
    original, parent, meta = fixture(profile, "1366x768")
    data = bytearray(parent)
    view = tool._parse(parent)
    debug = next(s for s in view.sections if s.name.rstrip(b"\0") == b".debug")
    # One mapped directory row with mapped payload and one with owned overlay.
    struct.pack_into("<II", data, view.opt + 96 + 6 * 8, debug.rva, 56)
    mapped = debug.raw + 64
    data[mapped:mapped + 8] = b"RSDSDATA"
    struct.pack_into("<IIHHIIII", data, debug.raw, 0, 0, 0, 0, 2, 8, debug.rva + 64, mapped)
    overlay = len(data)
    data.extend(b"NB10DATA")
    struct.pack_into("<IIHHIIII", data, debug.raw + 28, 0, 0, 0, 0, 2, 8, 0, overlay)
    # One symbol record without auxiliary file-offset forms, plus string table.
    symbols = len(data)
    data.extend(struct.pack("<8sIhHBB", b"fixture\0", 0, 1, 0, 2, 0))
    data.extend(struct.pack("<I", 4))
    struct.pack_into("<II", data, view.pe + 12, symbols, 1)
    rel = len(data)
    data.extend(struct.pack("<IIH", 4, 0, 6))
    line = len(data)
    data.extend(struct.pack("<IH", 0, 0))
    struct.pack_into("<IIHH", data, view.sections[0].header + 24, rel, line, 1, 1)
    data.extend(bytes((-len(data)) % 8))
    certificate = len(data)
    data.extend(struct.pack("<IHH", 16, 0x200, 2) + b"CERTDATA")
    struct.pack_into("<II", data, view.opt + 128, certificate, 16)
    data.extend(bytes((-len(data)) % 512))
    return original, bytes(data), meta


class SourceTests(unittest.TestCase):
    def test_all36_header_geometry_fresh_state_and_zero_reservations(self):
        with synthetic_issuer() as issuer:
            for profile in tool.PROFILES:
                for resolution in tool.RESOLUTIONS:
                    with self.subTest(profile=profile, resolution=resolution):
                        original, parent, relayout, layout = synthetic_context(issuer, profile, resolution)
                        self.assertEqual(layout.rx.size, 0x40000)
                        self.assertEqual(layout.rw.size, 0x10000)
                        self.assertEqual(layout.rw.va, layout.rx.va + 0x40000)
                        self.assertEqual(layout.battle_state_va, layout.rw.va)
                        self.assertEqual(layout.provider_va, layout.rw.va + 4096)
                        self.assertEqual(layout.provider_reservation_bytes, 61440)
                        self.assertEqual(layout.provider_schema, "unpopulated_provider_reservation_v1")
                        self.assertEqual(layout.rx.characteristics, 0x60000020)
                        self.assertEqual(layout.rw.characteristics, 0xC0000040)
                        self.assertEqual(layout.future_section_count, layout.parent_section_count + 2)
                        self.assertEqual(len(relayout) - len(parent), 1024 if profile == "modalwidgets" else 0)
                        self.assertEqual(layout.headers_after, 0x800 if profile == "modalwidgets" else 0x400)
                        self.assertEqual(relayout[layout.rx.header_offset:layout.rw.header_offset + 40], bytes(80))
                        self.assertEqual(layout.future_file_size, len(relayout) + 0x50000)
                        self.assertEqual(layout.highlow_rvas, issuer._parse(parent).highlow)
                        self.assertEqual(len(layout.geometry), 20)
                        width, height = map(int, resolution.split("x"))
                        for g in layout.geometry:
                            expected = min(g.world_columns, min(20, (width - 192) // 64))
                            self.assertEqual(g.visible_columns, expected)
                            self.assertEqual(g.max_scroll_x, max(0, g.world_columns - expected))
                            self.assertEqual(g.arena, (32, 16, 32 + 64 * expected - 1, 463))
                            self.assertEqual(g.gutter_before_hud, width - 160 - 32 - 64 * expected)
                            self.assertGreaterEqual(g.gutter_before_hud, 0)
                        for a, b in zip(layout.protected_spans, layout.protected_spans[1:]):
                            self.assertLessEqual(a.va + a.size, b.va)
                        self.assertEqual(issuer._parse(original).sections, issuer._parse(parent).sections[:7])
                        with self.assertRaises(FrozenInstanceError):
                            layout.rx.size = 1

    def test_modal_offset_inventory_preserves_loaded_sections_and_inherited_page(self):
        with synthetic_issuer() as issuer:
            _, parent, relayout, layout = synthetic_context(issuer)
            old, new = issuer._parse(parent), issuer._parse(relayout)
            self.assertEqual(len(layout.file_offset_edits), 1 + sum(bool(s.raw) for s in old.sections))
            self.assertEqual(old.directories, new.directories)
            for a, b in zip(old.sections, new.sections):
                self.assertEqual((a.rva, a.virtual_size, a.raw_size, a.flags), (b.rva, b.virtual_size, b.raw_size, b.flags))
                self.assertEqual(b.raw, a.raw + 1024 if a.raw else 0)
                if a.raw:
                    self.assertEqual(parent[a.raw:a.raw + a.raw_size], relayout[b.raw:b.raw + b.raw_size])
                if a.name.rstrip(b"\0") == b".hdstate":
                    self.assertEqual(relayout[b.raw:b.raw + b.raw_size], bytes(4096))
                    self.assertNotEqual(0x400000 + a.rva, layout.rw.va)
            for fixup in old.highlow:
                self.assertEqual(parent[old.file_offset(fixup, 4):old.file_offset(fixup, 4) + 4],
                                 relayout[new.file_offset(fixup, 4):new.file_offset(fixup, 4) + 4])

    def test_known_coff_security_debug_line_offsets_move_once_and_rvas_remain(self):
        with synthetic_issuer() as issuer:
            _, parent, _ = auxiliary_fixture()
            # Format-only lane: these extra schemas are not canonical parents.
            relayout, edits = issuer._relayout(parent, 0x800)
            roles = {row.role for row in edits}
            self.assertEqual(roles, {"SizeOfHeaders", "section_raw", "section_coff_relocations",
                "section_line_numbers", "coff_symbol_table", "security_directory", "debug_payload"})
            for row in edits:
                self.assertEqual(struct.unpack("<I", row.new)[0] - struct.unpack("<I", row.old)[0], 1024)
                self.assertEqual(relayout[row.offset:row.offset + 4], row.new)
            old, new = issuer._parse(parent), issuer._parse(relayout)
            self.assertEqual(old.directories[6], new.directories[6])
            self.assertEqual(new.directories[4], (old.directories[4][0] + 1024, old.directories[4][1]))
            self.assertEqual(old.highlow, new.highlow)
            issuer._verify_relayout(parent, relayout, 0x800, edits)

    def test_undeclared_extra_byte_wrong_pointer_missing_or_forged_edits_fail(self):
        with synthetic_issuer() as issuer:
            _, parent, relayout, layout = synthetic_context(issuer)
            for at in (0x20, issuer._parse(relayout).sections[0].raw + 16, len(relayout) - 1):
                mutated = bytearray(relayout); mutated[at] ^= 1
                with self.assertRaises(ValueError):
                    issuer._verify_relayout(parent, bytes(mutated), 0x800, layout.file_offset_edits)
            for edits in (layout.file_offset_edits[:-1], tuple(reversed(layout.file_offset_edits)),
                          (replace(layout.file_offset_edits[0], role="forged"),) + layout.file_offset_edits[1:]):
                with self.assertRaisesRegex(ValueError, "inventory|prefix"):
                    issuer._verify_relayout(parent, relayout, 0x800, edits)
            mutated = bytearray(relayout)
            row = layout.file_offset_edits[-1]
            mutated[row.offset:row.offset + 4] = struct.pack("<I", struct.unpack("<I", row.new)[0] + 512)
            with self.assertRaises(ValueError):
                issuer._verify_relayout(parent, bytes(mutated), 0x800, layout.file_offset_edits)

    def test_unknown_overlapping_auxiliary_directory_overlay_and_highlow_fail(self):
        _, parent, _ = auxiliary_fixture()
        pe = tool._parse(parent)
        cases = []
        data = bytearray(parent); data[-1] = 1; cases.append(data)
        data = bytearray(parent); struct.pack_into("<II", data, pe.opt + 96 + 11 * 8, 0x300, 8); cases.append(data)
        data = bytearray(parent); symbols = struct.unpack_from("<I", data, pe.pe + 12)[0]; data[symbols + 17] = 1; cases.append(data)
        data = bytearray(parent); struct.pack_into("<I", data, pe.sections[0].header + 24, pe.sections[0].raw); cases.append(data)
        data = bytearray(parent); debug = pe.file_offset(pe.directories[6][0], 56); struct.pack_into("<I", data, debug + 12, 99); cases.append(data)
        data = bytearray(parent); struct.pack_into("<I", data, debug + 24, 0x400); cases.append(data)
        data = bytearray(parent); struct.pack_into("<H", data, pe.directories[4][0] + 6, 7); cases.append(data)
        data = bytearray(parent); at = pe.file_offset(pe.directories[5][0], pe.directories[5][1]); struct.pack_into("<H", data, at + 8, 0x5004); cases.append(data)
        for index, data in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(ValueError):
                tool._parse(bytes(data))
        with self.assertRaisesRegex(ValueError, "OVERFLOW|fixed|schema"):
            tool._validate_reservations(0x40000, 0x100000000, tool.PROVIDER_SCHEMA)
        with self.assertRaisesRegex(ValueError, "schema"):
            tool._validate_reservations(0x40000, 0x10000, "unknown_provider")

    def test_header_state_profile_original_and_forged_reservation_rejections(self):
        original, parent, meta = fixture("completehd", "1366x768")
        pe = tool._parse(parent)
        state = next(s for s in pe.sections if s.name.rstrip(b"\0") == b".hdstate")
        with synthetic_issuer() as issuer:
            for at in (0x320, 0x360, state.raw + 127, state.raw + 256, state.raw + 4095):
                mutated = bytearray(parent); mutated[at] = 1
                with self.assertRaises(ValueError):
                    issuer._layout(original, bytes(mutated), "completehd", "1366x768", meta["stage"])
            for profile, resolution in (("forged", "1366x768"), ("completehd", "802x602"), ("framed", "1366x768")):
                with self.assertRaises(ValueError):
                    issuer._layout(original, parent, profile, resolution, meta["stage"])
            with patch.object(issuer, "RX_BYTES", 0x80000), self.assertRaisesRegex(ValueError, "fixed"):
                issuer._layout(original, parent, "completehd", "1366x768", meta["stage"])
            mutated = bytearray(original); struct.pack_into("<I", mutated, pe.sections[0].header + 36, 0xE0000020)
            with self.assertRaisesRegex(ValueError, "original section"):
                issuer._layout(bytes(mutated), parent, "completehd", "1366x768", meta["stage"])
            with self.assertRaises(ValueError):
                issuer.build_allocation_context(original, "completehd", "1366x768")

    def test_public_aliases_cannot_admit_synthetic_original_and_marker_is_rejecting(self):
        marker = object()
        with patch.object(tool, "_issue", return_value=marker), \
             patch.object(tool, "_sources", return_value={}), \
             patch.object(tool, "_private_predecessor", side_effect=AssertionError("public dependency alias called")), \
             patch.object(tool, "_production_factory", return_value=lambda *args: marker), \
             patch.object(tool, "_sha", return_value=tool.BASE_SHA256), \
             patch.object(tool, "ROOT", Path("C:/forged")), \
             patch.object(tool, "RX_BYTES", 1), \
             patch.object(tool, "SOURCE", "forged.py"):
            with self.assertRaisesRegex(ValueError, "exact original"):
                tool.build_allocation_context(b"invented", "classic", "1024x768")
        with synthetic_issuer() as issuer, self.assertRaisesRegex(ValueError, "captured canonical"):
            issuer.build_allocation_context(b"invented", "classic", "1024x768")

    def test_source_midread_reparse_and_snapshot_changes_fail_without_writes(self):
        path = ROOT / tool.SOURCE
        real_stat = Path.stat
        count = 0

        def changed_stat(subject, *args, **kwargs):
            nonlocal count
            row = real_stat(subject, *args, **kwargs)
            if subject == path and kwargs.get("follow_symlinks", True):
                count += 1
                if count > 1:
                    return SimpleNamespace(st_dev=row.st_dev, st_ino=row.st_ino, st_size=row.st_size,
                        st_mtime_ns=row.st_mtime_ns + 1, st_file_attributes=getattr(row, "st_file_attributes", 0))
            return row

        with patch.object(Path, "stat", changed_stat), self.assertRaisesRegex(ValueError, "during read"):
            tool._read_path(path, ROOT)
        real_lstat = Path.lstat

        def reparse(subject, *args, **kwargs):
            row = real_lstat(subject, *args, **kwargs)
            if subject == path.parent:
                return SimpleNamespace(st_file_attributes=0x400, st_mode=row.st_mode)
            return row

        with patch.object(Path, "lstat", reparse), self.assertRaisesRegex(ValueError, "reparse"):
            tool._read_path(path, ROOT)
        raw, stamp = tool._read_path(path, ROOT)
        with self.assertRaisesRegex(ValueError, "closure changed"):
            tool._check_sources({tool.SOURCE: (raw + b"\n", stamp)})
        with synthetic_issuer() as issuer:
            with patch.object(issuer, "PREDECESSOR_SHA256", "0" * 64), self.assertRaisesRegex(ValueError, "frozen context"):
                issuer._sources("classic")

    def test_private_namespace_cleanup_keeps_foreign_identity(self):
        raw = (ROOT / tool.PREDECESSOR).read_bytes()
        foreign = ModuleType("foreign")
        name = None
        try:
            with self.assertRaisesRegex(ValueError, "namespace identity"):
                with tool._private_predecessor(raw) as module:
                    name = module.__name__
                    sys.modules[name] = foreign
            self.assertIs(sys.modules[name], foreign)
        finally:
            if name and sys.modules.get(name) is foreign:
                del sys.modules[name]


class OriginalBackedTests(unittest.TestCase):
    def test_two_representatives_private_authority_header_relayout_and_original_unchanged(self):
        original = ORIGINAL.read_bytes()
        self.assertEqual(sha(original), tool.BASE_SHA256)
        for profile, resolution in (("classic", "1024x768"), ("modalwidgets", "3840x2160")):
            with self.subTest(profile=profile):
                baseline = tool.build_allocation_context(original, profile, resolution)
                with patch.object(tool, "_issue", side_effect=AssertionError("public issuer used")), \
                     patch.object(tool, "_sources", side_effect=AssertionError("public snapshot used")), \
                     patch.object(tool, "_read_path", side_effect=AssertionError("public read used")), \
                     patch.object(tool, "_sha", return_value="0" * 64), \
                     patch.object(tool, "RX_BYTES", 1), patch.object(tool, "RW_BYTES", 1), \
                     patch.object(tool, "ROOT", Path("C:/forged")), patch.object(tool, "SOURCE", "forged.py"):
                    second = tool.build_allocation_context(original, profile, resolution)
                self.assertEqual(baseline, second)
                metadata = baseline.metadata()
                self.assertTrue(metadata["canonical_parent_reconstructed"])
                self.assertTrue(metadata["allocation_plan_only"])
                for key in tool.FALSE_CLAIMS:
                    self.assertIs(metadata[key], False)
                self.assertEqual(metadata["provider_records_emitted"], 0)
                self.assertIsNone(metadata["provider_catalog_capacity"])
                self.assertNotEqual(baseline.layout.rw.va, next((s.va for s in baseline.layout.protected_spans
                    if s.role == "parent:.hdstate"), None))
                self.assertEqual(metadata["parent_sha256"], sha(baseline.parent))
                self.assertEqual(metadata["relayout_parent_sha256"], sha(baseline.relayout_parent))
                self.assertEqual(baseline.layout.insertion_bytes, 1024 if profile == "modalwidgets" else 0)
                # Production dataclasses originate in the captured private
                # issuer. Recreate values for this independent pure verifier;
                # its public class identity supplies no candidate authority.
                edits = tuple(tool.FileOffsetEdit(row.offset, row.old, row.new, row.role)
                              for row in baseline.layout.file_offset_edits)
                tool._verify_relayout(baseline.parent, baseline.relayout_parent,
                    baseline.layout.headers_after, edits)
        self.assertEqual(sha(ORIGINAL.read_bytes()), tool.BASE_SHA256)


def main():
    global ORIGINAL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", type=Path,
        help="explicit user-owned exact original; adds bounded canonical RAM-only lane")
    args, selectors = parser.parse_known_args()
    ORIGINAL = args.original_backed
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    if selectors:
        suite.addTests(loader.loadTestsFromNames(selectors, module=sys.modules[__name__]))
    else:
        suite.addTests(loader.loadTestsFromTestCase(SourceTests))
        if ORIGINAL is not None:
            suite.addTests(loader.loadTestsFromTestCase(OriginalBackedTests))
    if ORIGINAL is None and any("OriginalBackedTests" in name for name in selectors):
        parser.error("OriginalBackedTests requires --original-backed")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print("allocation_plan_only=True native_execution=False provider_capacity_verified=False")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
