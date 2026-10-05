#!/usr/bin/env python3
"""Portable parent/allocation rejection fixtures; no native or file outputs.

Synthetic PE planning never satisfies production original identity. The optional
--original-backed lane reconstructs five representative plans entirely in
memory from a local user-supplied original. It supplies no runtime evidence.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import importlib
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.patcher import battle_profile_context as tool
from src.patcher import pe_extension as pe
from src.patcher import framed_battle_viewport as geometry


def fixture(profile="completehd", resolution="1366x768"):
    """Independent minimal PE fixture; not an original/game candidate."""
    width, _ = map(int, resolution.split("x"))
    suffix = [] if profile == "classic" and width < 1144 else [(b".hdcode", tool.RX)]
    if profile in ("completehd", "modalwidgets"):
        suffix = [(b".hdcode", tool.RX), (b".hdmodal", tool.RX),
                  (b".hdstate", tool.RW), (b".hdarmy", tool.RX)]
        if profile == "modalwidgets":
            suffix += [(name, tool.RX) for name in (b".hdslots", b".hdprim", b".hdptxt", b".hdwgt")]
    initial_rows = [(b".text", tool.RX), (b".rdata", 0x40000040), (b".data", tool.RW),
                    (b".bss", 0xC0000080), (b".idata", tool.RW), (b".debug", 0x40000040),
                    (b".reloc", 0x42000040)]

    def image(rows):
        data = bytearray(0x400)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 60, 0x70)
        data[0x70:0x74] = b"PE\0\0"
        struct.pack_into("<HHIIIHH", data, 0x74, 0x14C, len(rows), 0, 0, 0, 224, 0x182)
        struct.pack_into("<H", data, 0x88, 0x10B)
        struct.pack_into("<III", data, 0x88 + 28, 0x400000, 4096, 512)
        struct.pack_into("<II", data, 0x88 + 56, 0x1000 * (len(rows) + 1), 1024)
        struct.pack_into("<I", data, 0x88 + 92, 16)
        struct.pack_into("<II", data, 0x88 + 136, 0x7000, 12)
        code_size = 0
        for index, (name, flags) in enumerate(rows):
            size = 4096 if name in (b".bss", b".hdstate") else 512
            raw = 0 if name == b".bss" else len(data)
            struct.pack_into("<8sIIIIIIHHI", data, 0x168 + 40 * index,
                             name, size, 0x1000 * (index + 1), size, raw, 0, 0, 0, 0, flags)
            if raw:
                data.extend(bytes(size))
            if flags & 0x20:
                code_size += size
        struct.pack_into("<I", data, 0x88 + 4, code_size)
        view = pe.inspect_pe(bytes(data))
        struct.pack_into("<I", data, view.file_offset(0x1004, 4), 0x401008)
        struct.pack_into("<IIHH", data, view.file_offset(0x7000, 12), 0x1000, 12, 0x3004, 0)
        return bytes(data)

    original, candidate = image(initial_rows), image(initial_rows + suffix)
    _, revision, _ = tool.ENTRYPOINTS[profile]
    metadata = dict(stage=tool.STABLE_STAGE + "-" + profile + "-allpresets-validation",
                    recipe_revision=revision, resolution=resolution, probe_sha256="synthetic-probe-digest")
    if profile in ("completehd", "modalwidgets"):
        view = pe.inspect_pe(candidate)
        state = next(s for s in view.sections if s.name.rstrip(b"\0") == b".hdstate")
        page_va = view.image_base + state.rva
        modal = next(s for s in view.sections if s.name.rstrip(b"\0") == b".hdmodal")
        offsets = dict(phase=0, physical=4, native=8, saved_render=12, root_esp=16,
                      owner_tid=20, enter_status=24, mirror_status=28, leave_status=32,
                      fault=36, allocations=40, frees=44, mirrors=48, pending_header=52,
                      pending_pixels=56, native_pixels=60, physical_pixels=64)
        owner = dict(state_va=page_va, state_bytes=4096, state_raw_offset=state.raw_offset,
                     modal_state_offsets=offsets, code_va=view.image_base + modal.rva,
                     relocations=[dict(offset=8, kind="abs32", target=page_va, purpose="state.phase"),
                                  dict(offset=16, kind="abs32", target=page_va + 64, purpose="state.physical_pixels")])
        data = bytearray(candidate)
        for row in owner["relocations"]:
            struct.pack_into("<I", data, view.file_offset(modal.rva + row["offset"], 4), row["target"])
        blocks = pe._relocation_blocks((0x1004, modal.rva + 8, modal.rva + 16))
        struct.pack_into("<II", data, 0x88 + 136, 0x7000, len(blocks))
        start = view.file_offset(0x7000, len(blocks))
        data[start:start + len(blocks)] = blocks
        candidate = bytes(data)
        metadata["predecessor"] = dict(base_candidate=owner,
            retired_header_scratch=dict(start=0x300, end_exclusive=0x348, legacy_day_diagnostic_allowed=False))
        if profile == "modalwidgets":
            complete = dict(metadata, recipe_revision="complete_hd_all_presets_v1")
            context = complete
            for kind in ("slots", "primary", "text", "widgets"):
                context = dict(recipe_revision="synthetic-" + kind, layer_kind=kind, base_candidate=context)
            metadata["predecessor"] = context
    return original, candidate, metadata


def plan(profile="completehd", resolution="1366x768", values=None, snapshots=None):
    original, candidate, metadata = fixture(profile, resolution) if values is None else values
    sources = tool._source_snapshot(profile)[0] if snapshots is None else snapshots
    return tool._allocation_plan(original, candidate, metadata, profile, resolution, sources, pe, geometry)


class SourceTests(unittest.TestCase):
    def test_fixed_sources_private_namespaces_and_public_alias_independence(self):
        public_modules = {profile: importlib.import_module(entry.removesuffix(".py").replace("/", "."))
                          for profile, (entry, _, _) in tool.ENTRYPOINTS.items()}
        original, _, _ = fixture()
        before = set(sys.modules)
        for profile in tool.PROFILES:
            public = public_modules[profile]
            snapshots, stamps = tool._source_snapshot(profile)
            with patch.object(public, "build_candidate", side_effect=AssertionError("public alias called")), \
                    patch.object(public, "REVISION", "forged-public-revision"), \
                    patch.object(pe, "inspect_pe", side_effect=AssertionError("public parser called")):
                with tool._private_modules(profile, snapshots) as modules:
                    entry, revision, digest = tool.ENTRYPOINTS[profile]
                    constructor = modules[entry]
                    self.assertEqual(tool.sha256(snapshots[entry]), digest)
                    self.assertEqual(constructor.REVISION, revision)
                    self.assertEqual(constructor.RESOLUTIONS, tool.RESOLUTIONS)
                    self.assertIsNot(constructor, public)
                    self.assertIsNot(constructor.build_candidate, public.build_candidate)
                    private_parser = modules["src/patcher/pe_extension.py"]
                    self.assertIsNot(private_parser.inspect_pe, pe.inspect_pe)
                    self.assertEqual(len(private_parser.inspect_pe(original).sections), 7)
            tool._unchanged(snapshots, stamps)
        self.assertEqual(set(sys.modules), before)

    def test_pin_and_source_snapshot_mutations_fail(self):
        with patch.object(tool, "_read_source", wraps=tool._read_source) as reader:
            snapshots, stamps = tool._source_snapshot("classic")
            self.assertTrue(reader.called)
        damaged = dict(snapshots)
        damaged[next(iter(tool.FOUNDATION_PINS))] += b"\n"
        with self.assertRaisesRegex(ValueError, "pinned source differs"):
            tool._unchanged(damaged, stamps)
        changed = dict(stamps)
        name = next(iter(changed))
        changed[name] = (*changed[name][:-1], changed[name][-1] + 1)
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            tool._unchanged(snapshots, changed)

    def test_public_original_selector_and_bundle_type_boundaries(self):
        for profile, resolution in (("Classic", "800x600"), ("classic", "802x602"),
                                    ("completehd", "1280X720"), (True, "800x600")):
            with self.assertRaises(ValueError):
                tool.build_parent_context(b"synthetic", profile, resolution)
        with patch.object(tool, "_source_snapshot", side_effect=AssertionError("must reject before producers")):
            for original in (b"synthetic", bytearray(b"synthetic"), None):
                with self.assertRaisesRegex(ValueError, "exact original"):
                    tool.build_parent_context(original, "classic", "800x600")
                with self.assertRaisesRegex(ValueError, "exact original"):
                    tool.authenticate_parent(original, b"fake", {}, "fake", profile="classic", resolution="800x600")

    def test_exact_json_types_no_coercion_or_unbounded_nesting(self):
        for a, b in ((1, True), (1, 1.0), ([1], (1,))):
            if type(b) is tuple:
                with self.assertRaises(ValueError):
                    tool._canonical(b)
            else:
                self.assertNotEqual(tool._canonical(a), tool._canonical(b))
        for value in (float("nan"), {1: "bad"}, object()):
            with self.assertRaises(ValueError):
                tool._canonical(value)
        nested = 0
        for _ in range(65):
            nested = [nested]
        with self.assertRaisesRegex(ValueError, "nesting"):
            tool._canonical(nested)

    def test_typed_metadata_preserves_frozen_tuple_fields(self):
        metadata = dict(rect=(0, 1, 639, 479), other=[1, True, 1.0, None], nested={"tuple": ()})
        encoded = tool._typed_canonical(metadata)
        context = tool.BattleProfileContext(b"synthetic", encoded, "", "{}")
        restored = context.parent_metadata()
        self.assertEqual(tool._typed_canonical(restored), encoded)
        self.assertIs(type(restored["rect"]), tuple)
        self.assertIs(type(restored["other"]), list)
        changed = deepcopy(metadata)
        changed["rect"] = list(changed["rect"])
        self.assertNotEqual(tool._typed_canonical(changed), encoded)
        nested = []
        for _ in range(65):
            nested = [nested]
        for value in (float("nan"), {1: "bad"}, object(), nested):
            with self.assertRaises(ValueError):
                tool._typed_canonical(value)
        for tree in (("int", 1), ["int", True], ["tuple", {}], ["dict", [["x", ["int", 1]], ["x", ["int", 2]]]]):
            with self.assertRaises(ValueError):
                tool._restore_metadata(tree)

    def test_isolated_bundle_comparison_rejects_substitutions_and_claims(self):
        # Exercise the pure comparison boundary with an explicitly synthetic
        # identity. Neither the public API nor a constructor is invoked here.
        original, candidate, probe = b"synthetic-comparison-original", b"candidate", "canonical probe\n"
        synthetic_digest = tool.sha256(original)
        snapshots, _ = tool._source_snapshot("classic")
        metadata = dict(stage=tool.STABLE_STAGE + "-classic-allpresets-validation",
            recipe_revision="classic_all_presets_v1", profile="classic", resolution="800x600",
            base_sha256=synthetic_digest, candidate_sha256=tool.sha256(candidate), candidate_bytes=len(candidate),
            probe_sha256=tool.sha256(probe.encode()), validation_stage_only=True,
            source_hashes={name: tool.sha256(data) for name, data in snapshots.items()
                           if name not in (tool.SOURCE, "src/patcher/framed_battle_viewport.py")},
            inherited_tuple=(1, 2), **{key: False for key in tool.FALSE_CLAIMS})
        bundle = (candidate, metadata, probe)
        with patch.object(tool, "BASE_SHA256", synthetic_digest):
            tool._authenticate_bundle(original, "classic", "800x600", bundle, bundle, snapshots)
            for index, value in ((0, b"substituted candidate"), (1, {}), (2, probe + "invented pass")):
                changed = list(bundle)
                changed[index] = value
                with self.assertRaisesRegex(ValueError, "reconstruction"):
                    tool._authenticate_bundle(original, "classic", "800x600", tuple(changed), bundle, snapshots)
            changed = deepcopy(metadata)
            changed["inherited_tuple"] = [1, 2]
            with self.assertRaisesRegex(ValueError, "reconstruction"):
                tool._authenticate_bundle(original, "classic", "800x600", (candidate, changed, probe), bundle, snapshots)
            for key, value in (("candidate_bytes", float(len(candidate))), ("stage", "wrong-stage"),
                    ("recipe_revision", "old-army"), ("resolution", "1024x768"), ("profile", "framed"),
                    ("expanded_battle_installed", True), ("runtime_executed", 0)):
                changed = deepcopy(metadata)
                changed[key] = value
                forged = (candidate, changed, probe)
                with self.assertRaises(ValueError):
                    tool._authenticate_bundle(original, "classic", "800x600", forged, forged, snapshots)
            for key, value in (("source_hashes", {}), ("probe_sha256", "invented digest")):
                changed = deepcopy(metadata)
                changed[key] = value
                forged = (candidate, changed, probe)
                with self.assertRaises(ValueError):
                    tool._authenticate_bundle(original, "classic", "800x600", forged, forged, snapshots)


class AllocationTests(unittest.TestCase):
    def test_all_profiles_nine_presets_small_arenas_and_gutters(self):
        columns_at_twenty = (9, 13, 17, 17, 18, 20, 20, 20, 20)
        for profile in tool.PROFILES:
            snapshots, _ = tool._source_snapshot(profile)
            for resolution, expected_columns in zip(tool.RESOLUTIONS, columns_at_twenty):
                result = plan(profile, resolution, snapshots=snapshots)
                self.assertTrue(result["allocation_plan_only"])
                self.assertTrue(all(result[key] is False for key in tool.FALSE_CLAIMS))
                self.assertEqual(result["rx"]["characteristics"], tool.RX)
                self.assertEqual(result["rw"]["characteristics"], tool.RW)
                arenas = result["geometry"]["arenas"]
                self.assertEqual(len(arenas), 20)
                self.assertEqual(arenas[-1]["visible_columns"], expected_columns)
                for arena in arenas:
                    n = arena["world_columns"]
                    self.assertEqual(arena["visible_columns"], min(n, expected_columns))
                    self.assertEqual(arena["max_scroll_x"], n - min(n, expected_columns))
                    self.assertEqual(arena["arena"], [32, 16, 31 + min(n, expected_columns) * 64, 463])
                    self.assertGreaterEqual(arena["gutter_before_hud"], 0)
                self.assertEqual(arenas[0]["max_scroll_x"], 0)
                self.assertEqual(result["geometry"]["origin"], [32, 16])
                width, height = map(int, resolution.split("x"))
                slices = result["geometry"]["hud_slices"]
                self.assertEqual(slices[0]["destination"], [width - 160, 0, width - 1, 367])
                self.assertEqual(slices[1]["destination"], [width - 160, height - 112, width - 1, height - 1])

    def test_exact_header_slots_and_owned_state_plan(self):
        for profile, resolution, slot, count in (("classic", "1024x768", 0x280, 9),
                ("classic", "1366x768", 0x2A8, 10), ("framed", "800x600", 0x2A8, 10),
                ("completehd", "1366x768", 0x320, 12), ("modalwidgets", "1366x768", 0x3C0, 16)):
            result = plan(profile, resolution)
            self.assertEqual(result["rx"]["header_offset"], slot)
            self.assertEqual(result["future_section_count"], count)
            state = result["rw"]
            self.assertEqual(state["used_bytes"], 128)
            if profile in ("classic", "framed"):
                self.assertEqual(state["va"], result["rx"]["va"] + tool.CODE_RESERVATION)
                self.assertEqual(state["header_offset"], slot + 40)
                self.assertIsNone(state["raw_offset"])
                self.assertIsNone(result["inherited_state_inventory"])
            else:
                inherited = result["inherited_state_inventory"]
                self.assertEqual(state["va"], inherited["page_va"] + 0x100)
                self.assertIsNone(state["header_offset"])
                self.assertEqual(inherited["active_state_fixup_count"], 2)
                self.assertGreaterEqual(state["va"], inherited["inherited_extent"][1])

    def test_occupied_headers_and_changed_historical_sections_fail(self):
        for profile in tool.PROFILES:
            original, candidate, metadata = fixture(profile)
            view = pe.inspect_pe(candidate)
            offsets = (40, 80) if profile in ("classic", "framed") else (40,)
            for delta in offsets:
                damaged = bytearray(candidate)
                damaged[view.sections[-1].header_offset + delta] = 1
                with self.assertRaisesRegex(ValueError, "header slots"):
                    plan(profile, values=(original, bytes(damaged), metadata))
            damaged = bytearray(candidate)
            damaged[0x168] ^= 1
            with self.assertRaisesRegex(ValueError, "historical PE"):
                plan(profile, values=(original, bytes(damaged), metadata))

    def test_extension_permissions_names_and_scratch_retirement_fail(self):
        for profile in tool.PROFILES:
            original, candidate, metadata = fixture(profile)
            view = pe.inspect_pe(candidate)
            first = view.sections[7]
            damaged = bytearray(candidate)
            struct.pack_into("<I", damaged, first.header_offset + 36, 0xE0000020)
            with self.assertRaisesRegex(ValueError, "permissions"):
                plan(profile, values=(original, bytes(damaged), metadata))
            damaged = bytearray(candidate)
            damaged[first.header_offset] = ord("x")
            with self.assertRaisesRegex(ValueError, "sections"):
                plan(profile, values=(original, bytes(damaged), metadata))
        original, candidate, metadata = fixture()
        metadata["predecessor"]["retired_header_scratch"]["legacy_day_diagnostic_allowed"] = True
        with self.assertRaisesRegex(ValueError, "scratch retirement"):
            plan(values=(original, candidate, metadata))

    def test_zero_state_owner_fields_and_missing_operand_fail(self):
        original, candidate, metadata = fixture()
        view = pe.inspect_pe(candidate)
        state = next(s for s in view.sections if s.name.rstrip(b"\0") == b".hdstate")
        for offset in (0, 0x100, 4095):
            damaged = bytearray(candidate)
            damaged[state.raw_offset + offset] = 1
            with self.assertRaisesRegex(ValueError, "zero initialization"):
                plan(values=(original, bytes(damaged), metadata))
        for key, value in (("state_va", 1), ("state_bytes", 128), ("state_raw_offset", 0)):
            changed = deepcopy(metadata)
            changed["predecessor"]["base_candidate"][key] = value
            with self.assertRaisesRegex(ValueError, "owner|page"):
                plan(values=(original, candidate, changed))
        changed = deepcopy(metadata)
        changed["predecessor"]["base_candidate"]["modal_state_offsets"]["physical"] = 0x100
        with self.assertRaisesRegex(ValueError, "owner"):
            plan(values=(original, candidate, changed))
        changed = deepcopy(metadata)
        changed["predecessor"]["base_candidate"]["relocations"].pop()
        with self.assertRaisesRegex(ValueError, "fixup inventory"):
            plan(values=(original, candidate, changed))

    def test_state_reference_overlap_unknown_field_and_missing_fixup_fail(self):
        original, candidate, metadata = fixture()
        view = pe.inspect_pe(candidate)
        owner = metadata["predecessor"]["base_candidate"]
        for offset in (68, 0x100, 0x17C, 4092):
            changed = deepcopy(metadata)
            target = owner["state_va"] + offset
            changed["predecessor"]["base_candidate"]["relocations"][0]["target"] = target
            damaged = bytearray(candidate)
            rva = owner["code_va"] - view.image_base + 8
            struct.pack_into("<I", damaged, view.file_offset(rva, 4), target)
            with self.assertRaisesRegex(ValueError, "state reference|state fields"):
                plan(values=(original, bytes(damaged), changed))
        damaged = bytearray(candidate)
        blocks = pe._relocation_blocks((0x1004, owner["code_va"] - view.image_base + 8))
        struct.pack_into("<II", damaged, 0x88 + 136, 0x7000, len(blocks))
        start = view.file_offset(0x7000, len(blocks))
        damaged[start:start + len(blocks)] = blocks
        with self.assertRaisesRegex(ValueError, "fixup inventory"):
            plan(values=(original, bytes(damaged), metadata))


def original_backed(path):
    original = path.read_bytes()
    before = tool.sha256(original)
    for profile, resolution in (("classic", "1024x768"), ("classic", "1366x768"),
                               ("framed", "1366x768"), ("completehd", "1366x768"), ("modalwidgets", "1366x768")):
        context = tool.build_parent_context(original, profile, resolution)
        result = context.allocation_plan()
        if not result["allocation_plan_only"] or any(result[k] is not False for k in tool.FALSE_CLAIMS):
            raise AssertionError("source plan supplied an acceptance claim")
        # A substituted complete candidate, source metadata or canonical probe
        # must be rejected against the independently reconstructed real parent.
        metadata = context.parent_metadata()
        snapshots, _ = tool._source_snapshot(profile)
        expected = (context.candidate, metadata, context.canonical_probe)
        for index in range(3):
            changed = list(expected)
            if index == 0:
                changed[0] = expected[0][:-1] + bytes([expected[0][-1] ^ 1])
            elif index == 1:
                changed[1] = deepcopy(metadata)
                changed[1]["candidate_bytes"] = float(changed[1]["candidate_bytes"])
            else:
                changed[2] += "\n.echo invented_pass\n"
            try:
                tool._authenticate_bundle(original, profile, resolution, tuple(changed), expected, snapshots)
            except ValueError:
                pass
            else:
                raise AssertionError("substituted parent bundle accepted")
        print("ORIGINAL_BACKED_BATTLE_PLAN", profile, resolution, result["candidate_sha256"],
              "planned_headers=" + str(result["future_section_count"]), "battle_installed=false", flush=True)
    if tool.sha256(path.read_bytes()) != before:
        raise AssertionError("original changed during read-only audit")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", nargs="?", type=Path, const=Path("C:/Clash/clash95.exe"))
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if not result.wasSuccessful():
        return 1
    if args.original_backed:
        original_backed(args.original_backed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
