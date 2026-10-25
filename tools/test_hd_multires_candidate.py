#!/usr/bin/env python3
"""Source/byte/CPU contracts; optional original-bound construction of 12 cells.

CPU checks execute authored guard instructions on synthetic memory. Neither
that mode nor original-file construction launches Clash95 or proves gameplay.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import json
import struct
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import hd_multires_candidate as candidate
from src.patcher import hd_multires_bounded as bounded
from src.patcher import framed_bounded_input as mouse
from src.patcher import framed_camera as camera
from src.patcher import pe_extension as pe
from src.patcher.framed_viewport import FramedViewport
from test_complete_small_world_candidate import _synthetic_image
from test_pe_extension import independent_image, rebase


def synthetic_parent(profile="framed", resolution="3840x2160"):
    layout = FramedViewport(*map(int, resolution.split("x")))
    raw = bytearray(_synthetic_image("completehd"))
    view = pe.inspect_pe(bytes(raw))
    section = next(s for s in view.sections if s.name.rstrip(b"\0") == b".hdcode")
    base = view.image_base + section.rva
    entries = {name: base + 0x100 + 0x10 * i for i, name in enumerate(bounded.paint.HELPERS)}
    entries.update(hook_framed_full_entry=base + 0x300, framed_full_reject=base + 0x600,
                   initial_paint_admission=base + 0x700, initial_admission_reject=base + 0xa00,
                   framed_full_fallback=base + 0xa20)
    entries[mouse.ENTRY] = base + 0xb00
    entries[mouse.DENY] = entries[mouse.ENTRY] + 179

    def put(va, data):
        off = view.file_offset(va - view.image_base, len(data))
        raw[off:off + len(data)] = data

    for kind, entry_name, deny_name in (
            ("full_redraw", "hook_framed_full_entry", "framed_full_reject"),
            ("initial_paint", "initial_paint_admission", "initial_admission_reject")):
        va = entries[entry_name]
        put(va, camera._prefix(kind, va, entries))
        guard = va + camera.GATE_OFFSETS[kind]
        put(guard, camera.old_gate(layout, guard, entries[deny_name]))
    put(entries[mouse.ENTRY], mouse.world_gate(layout, entries[mouse.ENTRY], entries[mouse.DENY]))
    framed = dict(schema="clash95_pe_extension_v1", framed_validation=True, code_va=base,
                  code_bytes=0x1000, entry_vas=entries)
    predecessor = framed
    if profile != "framed":
        army = next(s for s in view.sections if s.name.rstrip(b"\0") == b".hdarmy")
        army_va = view.image_base + army.rva
        private = {"input.private.pixel_guard.minimap_clear": army_va + 0x100,
                   "input.private.pixel_guard.deny": army_va + 0x100 + 179}
        put(private["input.private.pixel_guard.minimap_clear"],
            mouse.world_gate(layout, private["input.private.pixel_guard.minimap_clear"],
                             private["input.private.pixel_guard.deny"]))
        predecessor = dict(schema="clash95_framed_army_candidate_v1", code_va=army_va,
                           code_bytes=0x1000, army_entry_vas=private, base_candidate=framed)
    image = bytes(raw)
    metadata = dict(candidate_sha256=candidate.sha256(image), resolution=resolution,
                    predecessor=predecessor)
    return image, metadata


class SourceAndByteTests(unittest.TestCase):
    def test_exact_twelve_cells_and_legacy_default_are_separate(self):
        self.assertEqual(len(candidate.PROFILES) * len(candidate.RESOLUTIONS), 12)
        registry = json.loads((ROOT / "src/launcher/resolutions.json").read_text())
        self.assertEqual(registry["default"], "800x600")
        self.assertEqual(registry["profiles"]["classic"]["resolutions"]["800x600"]["status"], "stable")
        for profile in candidate.PROFILES:
            self.assertTrue(candidate.stage(profile).endswith("-validation"))
            self.assertNotEqual(candidate.stage(profile), candidate.STABLE_STAGE)

    def test_original_identity_rejects_before_predecessor_construction(self):
        with patch.object(candidate, "_builder", side_effect=AssertionError("must not build")):
            with self.assertRaisesRegex(ValueError, "original executable"):
                candidate.build_candidate(b"fake", "1920x1080", profile="classic")
        for value in (None, True, "other"):
            with self.assertRaises(ValueError):
                candidate.stage(value)

    def test_all_source_closures_include_constructor_and_checked_helpers(self):
        for profile in candidate.PROFILES:
            sources = candidate.source_hashes(profile)
            self.assertIn(candidate.SOURCE, sources)
            self.assertIn("src/patcher/hd_multires_bounded.py", sources)
            self.assertTrue(set(candidate.HELPER_SOURCES) <= set(sources))
            self.assertEqual(sources, {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                      for name in sources})
        original_read = Path.read_bytes
        target = ROOT / "src/patcher/framed_camera.py"
        with patch.object(Path, "read_bytes", lambda path:
                          b"changed" if path == target else original_read(path)):
            with self.assertRaisesRegex(ValueError, "frozen issuer source pin"):
                candidate.source_hashes("framed")

    def test_all_framed_cells_apply_only_declared_guards_and_tail(self):
        for profile in candidate.PROFILES[1:]:
            for resolution in candidate.RESOLUTIONS:
                with self.subTest(profile=profile, resolution=resolution):
                    parent, meta = synthetic_parent(profile, resolution)
                    before = deepcopy(meta)
                    image, report = bounded.integrate(parent, meta, profile=profile,
                        resolution=resolution, selected_stage=candidate.stage(profile))
                    rebuilt = bytearray(parent)
                    for row in report["edits"]:
                        old, new = bytes.fromhex(row["old_hex"]), bytes.fromhex(row["new_hex"])
                        at = row["offset"]
                        self.assertEqual(rebuilt[at:at + len(old)], old)
                        rebuilt[at:at + len(old)] = new
                    self.assertEqual(bytes(rebuilt), image)
                    self.assertEqual(meta, before)
                    self.assertEqual(report["guard_count"], 4 if profile == "framed" else 6)
                    self.assertEqual(pe.inspect_pe(image).sections[:-1], pe.inspect_pe(parent).sections[:-1])
                    self.assertEqual(len(report["added_highlow_rvas"]), 5)
                    self.assertFalse(report["runtime_executed"])
                    self.assertFalse(report["manual_input_proof"])
                    self.assertFalse(report["promotion_ready"])

    def test_mutated_guard_fails_even_with_updated_outer_hash(self):
        parent, meta = synthetic_parent()
        entry = meta["predecessor"]["entry_vas"][mouse.ENTRY]
        at = pe.inspect_pe(parent).file_offset(entry - 0x400000, 1)
        changed = bytearray(parent)
        changed[at] ^= 1
        changed = bytes(changed)
        with self.assertRaisesRegex(ValueError, "input gate differs"):
            bounded.integrate(changed, meta | {"candidate_sha256": candidate.sha256(changed)},
                profile="framed", resolution="3840x2160", selected_stage=candidate.stage("framed"))

    def test_relocations_rebase_added_helpers_and_retain_original_fields(self):
        parent, meta = synthetic_parent("modalwidgets")
        image, report = bounded.integrate(parent, meta, profile="modalwidgets",
            resolution="3840x2160", selected_stage=candidate.stage("modalwidgets"))
        view = pe.inspect_pe(image)
        _, fields = pe._old_relocations(image, view)
        memory, _, independent_fields, _ = independent_image(image)
        self.assertEqual(tuple(independent_fields), tuple(fields))
        for target in (0x400000, 0x17000000):
            delta = target - view.image_base
            loaded = rebase(memory, independent_fields, delta)
            for rva in fields:
                at = view.file_offset(rva, 4)
                expected = (struct.unpack_from("<I", image, at)[0] + delta) & 0xffffffff
                self.assertEqual(struct.unpack_from("<I", loaded, rva)[0], expected)

    def test_probe_is_final_candidate_bound_and_requires_ordered_chunks(self):
        parent, meta = synthetic_parent()
        image, _ = bounded.integrate(parent, meta, profile="framed", resolution="3840x2160",
                                      selected_stage=candidate.stage("framed"))
        probe, facts = candidate.render_probe(image, dict(profile="framed", resolution="3840x2160",
            stage=candidate.stage("framed")), "")
        self.assertIn(candidate.sha256(image), facts["acceptance_marker"])
        self.assertTrue(facts["relocation_aware"])
        self.assertFalse(facts["runtime_observation_protocol"])
        self.assertGreater(facts["required_chunks"], 1)
        self.assertEqual(probe.count(".echo HDMULTI_LOADED_BYTES_OK"), 1)
        self.assertNotIn("\n", probe.replace("\r\n", ""))
        self.assertTrue(all(len(line.encode()) < 3800 for line in probe.splitlines()))
        with self.assertRaisesRegex(ValueError, "inherited read"):
            candidate.render_probe(image, dict(profile="framed", resolution="3840x2160",
                stage=candidate.stage("framed")), "by(00000001)")


class GuardCPU(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import unicorn
            from unicorn import x86_const
        except ImportError as exc:
            raise unittest.SkipTest("pinned Unicorn is required for authored guard CPU tests") from exc
        cls.uc, cls.x = unicorn, x86_const

    def test_world_admission_clamps_signed_scroll_and_validates_both_dimensions(self):
        for resolution in candidate.RESOLUTIONS:
            parent, meta = synthetic_parent("framed", resolution)
            image, report = bounded.integrate(parent, meta, profile="framed", resolution=resolution,
                                              selected_stage=candidate.stage("framed"))
            helper = report["helper"]
            view = pe.inspect_pe(image)
            at = view.file_offset(helper["va"] - view.image_base, helper["byte_count"])
            code = image[at:at + helper["byte_count"]]
            for width, height, scroll_x, scroll_y in ((1,1,0x7fffffff,0xffffffff),
                    (50,50,0x7fffffff,0x80000000), (100,100,0,1), (0,50,7,9), (50,101,7,9)):
                uc = self.uc.Uc(self.uc.UC_ARCH_X86, self.uc.UC_MODE_32)
                code_base = helper["va"] & ~4095
                uc.mem_map(code_base, 4096)
                uc.mem_write(helper["va"], code)
                data, stack, stop = 0x20000000, 0x21000000, 0x22000000
                uc.mem_map(data, 0x23000)
                uc.mem_map(stack, 0x10000)
                uc.mem_map(stop, 4096)
                values = (width, height, scroll_x, scroll_y)
                for offset, value in zip((*camera.MAP_DIMENSIONS, *camera.MAP_SCROLL), values):
                    uc.mem_write(data + offset, struct.pack("<I", value))
                sp = stack + 0xf000
                uc.mem_write(sp, struct.pack("<I", stop))
                uc.reg_write(self.x.UC_X86_REG_ESP, sp)
                uc.reg_write(self.x.UC_X86_REG_EDX, data)
                uc.emu_start(helper["entries"]["admit_world"], stop, count=1000)
                result = uc.reg_read(self.x.UC_X86_REG_EAX)
                actual = [struct.unpack("<I", uc.mem_read(data + offset, 4))[0]
                          for offset in (*camera.MAP_DIMENSIONS, *camera.MAP_SCROLL)]
                if not 1 <= width <= 100 or not 1 <= height <= 100:
                    self.assertEqual(result, 0)
                    self.assertEqual(actual, list(values))
                else:
                    full = report["full_tiles"]
                    self.assertEqual(result, 2 if width < full[0] or height < full[1] else 1)
                    self.assertEqual(actual[:2], [width, height])
                    for index, raw in enumerate((scroll_x, scroll_y)):
                        signed = raw if raw < 0x80000000 else raw - 0x100000000
                        self.assertEqual(actual[2 + index], min(max(signed, 0), max(0, (width, height)[index] - full[index])))
                self.assertEqual(uc.reg_read(self.x.UC_X86_REG_ESP), sp + 4)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", type=Path)
    args, rest = parser.parse_known_args()
    if args.original_backed is None:
        unittest.main(argv=[sys.argv[0], *rest])
        return
    original = args.original_backed.read_bytes()
    rows = []
    for resolution in candidate.RESOLUTIONS:
        for profile in candidate.PROFILES:
            started = time.monotonic()
            image, meta, probe = candidate.build_candidate(original, resolution, profile=profile)
            assert meta["candidate_sha256"] == candidate.sha256(image)
            assert meta["probe_sha256"] == candidate.sha256(probe.encode())
            assert meta["source_hashes"] == candidate.source_hashes(profile)
            assert all(meta[n] is False for n in ("runtime_verified", "manual_input_proof", "promotion_ready"))
            row = dict(profile=profile, resolution=resolution, candidate_sha256=meta["candidate_sha256"],
                bytes=len(image), probe_bytes=len(probe), bounded=meta["bounded_small_world_integrated"],
                seconds=round(time.monotonic()-started, 3), construction_passed=True,
                runtime_verified=False)
            rows.append(row)
            print(json.dumps(row), flush=True)
    assert len(rows) == 12


if __name__ == "__main__":
    main()
