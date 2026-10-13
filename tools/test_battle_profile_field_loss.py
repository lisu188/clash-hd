#!/usr/bin/env python3
"""Source/Unicorn regressions for an uninstalled fresh post-Tile loss join.

All native callbacks and pixels are models. No original/game/native compiler,
debugger, candidate file, screen capture or runtime acceptance is involved.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, replace
import gc
import hashlib
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import battle_profile_field_loss as tool
from src.patcher import battle_profile_content_v2 as content_tool
from src.patcher import battle_profile_stack_lease_v2 as lease_tool
from src.patcher import battle_profile_field_v3 as field_tool
from src.patcher import partial_tile_clip as clip
from src.patcher import framed_modal_canvas as native
import test_battle_profile_content_v2 as content_fixture
import test_battle_profile_stack_lease_v2 as lease_fixture

CACHE = {}
CONTENT_FIXTURE_SHA256 = "4ba3ae488509da4600cb3e94fab3523f1684beffed0bfc07797dca828b6e242f"
CONTENT_PRODUCER_SHA256 = "681fbf96f79e9c1fa9c64ab70f27057ade97bc4a109f79562c65a383067372c6"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def arguments():
    return dict(content_module=content_tool, content_kwargs=content_fixture.arguments(),
                lease_module=lease_tool, field_module=field_tool, assembler_module=clip)


def emit(profile="classic", resolution="800x600", fresh=False):
    key = profile, resolution
    if not fresh and key in CACHE:
        return CACHE[key]
    layout, life, route, field, lease, content = content_fixture.emit(profile, resolution, fresh=fresh)
    out = tool._emit_code(layout, life, route, field, lease, content, **arguments())
    result = layout, life, route, field, lease, content, out
    if not fresh:
        CACHE[key] = result
    return result


def source_closure():
    content_fixture.verify_frozen()
    if (sha((ROOT / tool.CONTENT).read_bytes()) != CONTENT_PRODUCER_SHA256 or
            tool.CONTENT_SHA256 != CONTENT_PRODUCER_SHA256):
        raise ValueError("frozen ContentV2 producer differs")
    if sha((ROOT / "tools/test_battle_profile_content_v2.py").read_bytes()) != CONTENT_FIXTURE_SHA256:
        raise ValueError("frozen ContentV2 fixture differs")
    names = set(content_fixture.source_closure()) | {tool.SOURCE, "tools/test_battle_profile_field_loss.py"}
    return {name: sha((ROOT / name).read_bytes()) for name in sorted(names)}


class Machine(lease_fixture.Machine):
    def __init__(self, tools, profile="classic", resolution="800x600", delta=0):
        super().__init__(tools, profile, resolution, delta)
        self.loss_emission = emit(profile, resolution)[6]
        joined = tool._join_field(self.field_emission, self.loss_emission)
        self.joined_field = joined
        for out in (joined, self.loss_emission):
            raw = bytearray(out.code)
            for row in out.relocations:
                if row.kind == "abs32":
                    struct.pack_into("<I", raw, row.offset, row.target + delta)
            self.cpu.mem_write(out.base_va + delta, bytes(raw))
            self.loaded_code = [(va, data) for va, data in self.loaded_code if va != out.base_va + delta]
            self.loaded_code.append((out.base_va + delta, bytes(raw)))


class SourceTests(unittest.TestCase):
    def test_all36_deterministic_fresh_prefix_and_two_exact_call_patches(self):
        source_closure()
        for profile in content_fixture.parent_fixture.context.PROFILES:
            for resolution in content_fixture.parent_fixture.context.RESOLUTIONS:
                with self.subTest(profile=profile, resolution=resolution):
                    layout, life, route, field, lease, content, out = emit(profile, resolution)
                    self.assertEqual(asdict(out), asdict(emit(profile, resolution, fresh=True)[6]))
                    self.assertEqual(out.base_va, (content.base_va + len(content.code) + 15) & ~15)
                    self.assertLessEqual(out.base_va + len(out.code), layout.rx.va + layout.rx.size)
                    joined = tool._join_field(field, out)
                    self.assertEqual(len(joined.code), len(field.code))
                    allowed = set()
                    for mode, pc, old, target in out.field_call_patches:
                        at = pc - field.base_va
                        self.assertEqual(old, field.code[at:at+5])
                        self.assertEqual(joined.code[at:at+1], b"\xe8")
                        self.assertEqual(pc + 5 + struct.unpack_from("<i", joined.code, at+1)[0], target)
                        allowed.update(range(at+1, at+5))
                    self.assertTrue(all(i in allowed for i, (a, b) in enumerate(zip(field.code, joined.code)) if a != b))
                    self.assertEqual(joined.entries, field.entries)
                    self.assertEqual(joined.private_entries, field.private_entries)
                    # Native Tile calls/return PCs remain exactly at their old locations.
                    for _, pc, at, _ in field_tool._tile_receipts(field):
                        self.assertEqual(joined.code[at-5:at], field.code[at-5:at])
                    clip.absolute_relocation_offsets(joined)
                    rows = lease_fixture.decode(out.code, self.address_values(out, lease, field))
                    declarations = {r.offset: r for r in out.relocations}
                    absolute = {at for _, _, aa, _, _ in rows for at in aa}
                    relative = {at for _, _, _, rr, _ in rows for at in rr}
                    scalars = {at for _, _, _, _, ss in rows for at, _ in ss}
                    self.assertEqual(len(declarations), len(out.relocations))
                    self.assertEqual({at for at, row in declarations.items() if row.kind == "abs32"}, absolute)
                    self.assertEqual({at for at, row in declarations.items() if row.kind == "rel32"}, relative)
                    self.assertFalse(set(declarations) & scalars)
                    starts = {start for start, *_ in rows}
                    for _, _, _, rr, _ in rows:
                        for at in rr:
                            target = out.base_va + at + 4 + struct.unpack_from("<i", out.code, at)[0]
                            self.assertEqual(declarations[at].target, target)
                            if declarations[at].purpose.startswith("field_loss_internal:"):
                                self.assertIn(target-out.base_va, starts)

    @staticmethod
    def address_values(out, lease, field):
        return ({lease.base_va, lease.base_va+len(lease.code), out.state_va, out.state_va+16,
                 out.state_va+20, out.state_va+36, 0x4ea4e8} |
                {pc for _, pc in lease.lease_return_pcs} |
                {pc+5 for _, pc, *_ in field_tool._tile_receipts(field)})

    def test_entire_parent_bytes_receipts_and_geometry_are_reauthenticated(self):
        layout, life, route, field, lease, content, out = emit()
        for bad in (replace(content, code=content.code[:-1]), replace(content, entries=content.entries[:-1]),
                    replace(content, private_entries=content.private_entries[:-1]),
                    replace(content, body_receipts=content.body_receipts[:-1]),
                    replace(content, relocations=content.relocations[:-1])):
            with self.assertRaisesRegex(ValueError, "canonical fresh ContentV2"):
                tool._emit_code(layout, life, route, field, lease, bad, **arguments())
        for bad in (replace(field, code=field.code[:-1]), replace(field, entries=field.entries[:-1])):
            with self.assertRaises(ValueError):
                tool._emit_code(layout, life, route, bad, lease, content, **arguments())
        for bad in (replace(layout, rx=replace(layout.rx, size=131072)),
                    replace(layout, provider_schema="populated_provider")):
            with self.assertRaises(ValueError):
                tool._emit_code(bad, life, route, field, lease, content, **arguments())

    def test_exact_old_bytes_relocation_order_and_duplicate_join_reject(self):
        *_, field, lease, content, out = emit()
        mode, pc, old, target = out.field_call_patches[0]
        for patches in (out.field_call_patches[::-1], (out.field_call_patches[0],)*2,
                        ((mode, pc, b"\xe8\0\0\0\0", target), out.field_call_patches[1]),
                        ((mode, pc, old, target+1), out.field_call_patches[1])):
            with self.assertRaises(ValueError):
                tool._join_field(field, replace(out, field_call_patches=patches))
        with self.assertRaisesRegex(ValueError, "old CALL"):
            tool._join_field(tool._join_field(field, out), out)
        at = pc-field.base_va+1
        with self.assertRaisesRegex(ValueError, "relocation"):
            tool._join_field(replace(field, relocations=tuple(r for r in field.relocations if r.offset != at)), out)

    def test_public_rejects_synthetic_original_and_mutable_producer_aliases(self):
        def poison(*args, **kwargs):
            raise AssertionError("mutable producer alias used")
        with patch.object(tool, "_issue", poison), patch.object(tool, "_snapshot", poison), patch.object(content_tool, "_issue", poison):
            for original in (b"", b"synthetic PE", bytearray(b"synthetic PE"), None):
                with self.assertRaisesRegex(ValueError, "exact field loss original"):
                    tool.emit_field_loss(original, "classic", "800x600")

    def test_metadata_keeps_runtime_native_installation_and_promotion_false(self):
        tree = ast.parse((ROOT/tool.SOURCE).read_text(encoding="utf-8"))
        nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "dict" and
                 any(k.arg == "schema" and isinstance(k.value, ast.Constant) and k.value.value == "clash95_battle_profile_field_loss_v1" for k in n.keywords)]
        self.assertEqual(len(nodes), 1)
        fields = {k.arg: k.value for k in nodes[0].keywords if k.arg}
        for name in ("writes_owner_state", "writes_descriptor", "writes_headers", "writes_pixels"):
            self.assertIs(ast.literal_eval(fields[name]), False)
        self.assertIn("next_Tile_cancellation", tool.FALSE_CLAIMS)
        self.assertIn("native_stack_capacity_verified", tool.FALSE_CLAIMS)
        self.assertIn("atomic_installation_verified", tool.FALSE_CLAIMS)
        self.assertTrue(ast.literal_eval(fields["modeled_next_tile_cancellation"]))


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools = lease_fixture.field_fixture.routing_fixture.lifetime.prior_fixture.machine_tools()

    def make(self, profile="classic", resolution="800x600", delta=0, mode=0, columns=2):
        machine = Machine(self.tools, profile, resolution, delta).prepare(columns=columns)
        machine.expected_original_render = machine.word(native.RENDER+delta)
        return machine.begin(mode, eax=0, edx=0)

    def test_healthy_full_incremental_two_bases_and_outer_abi(self):
        for profile in content_fixture.parent_fixture.context.PROFILES:
            for delta in (0, 0x100000):
                for mode in (0, 1):
                    with self.subTest(profile=profile, delta=delta, mode=mode):
                        m = self.make(profile, delta=delta, mode=mode)
                        record = m.record()
                        self.assertEqual(m.complete()["EAX"], 1)
                        self.assertEqual(m.tiles, [(0, 0)] if mode else [(x,y) for x in range(2) for y in range(7)])
                        self.assertEqual(m.record(), record)
                        self.assertEqual(m.word(native.RENDER+delta), m.expected_original_render)
                        del m; gc.collect()

    def test_loss_and_leaf_status_cancel_after_first_tile_without_restore_or_retry(self):
        for mode in (0, 1):
            for loss, status in ((2,2), (2,0), (0,2), (1,1)):
                with self.subTest(mode=mode, loss=loss, status=status):
                    m = self.make("modalwidgets", mode=mode)
                    record = m.record()
                    m.put(m.lease_frame+44, loss); m.put(m.lease_frame+48, status)
                    callbacks = len(m.callbacks)
                    self.assertEqual(m.complete()["EAX"], 2)
                    self.assertEqual(m.tiles, [(0,0)])
                    self.assertEqual(m.callbacks[callbacks:], ["tile"])
                    self.assertEqual(m.word(native.RENDER), m.PHYSICAL)
                    self.assertEqual(m.record(), record)
                    self.assertEqual(m.lease_word("loss"), loss)
                    self.assertEqual(m.lease_word("leaf_status"), status)
                    del m; gc.collect()

    def test_real_modeled_leaf_failure_is_consumed_by_the_join(self):
        m = self.make("framed")
        m.primitive_mutation = lambda mm, _: mm.put(mm.lease_frame+188, 1)
        actual, _, _ = m.invoke_leaf("sprite_tile", guarded=True)
        self.assertEqual(actual["EAX"], 0xc0ffee11)
        self.assertEqual(m.lease_word("loss"), 2)
        self.assertEqual(m.lease_word("leaf_status"), 2)
        m.primitive_mutation = None
        self.assertEqual(m.complete()["EAX"], 2)
        self.assertEqual(m.tiles, [(0,0)])
        self.assertEqual(m.closures, ["sprite"])
        self.assertEqual(m.word(native.RENDER), m.PHYSICAL)

    def no_cached_reads(self, machine):
        ranges = ((machine.PHYSICAL, 188), (machine.PRIVATE, 188),
                  (machine.BACKEND, 168), (machine.WORLD, 0xf7c))
        self.assertFalse(any(at < lo+length and at+size > lo
                             for at, size in machine.reads for lo, length in ranges))

    def poison_caches(self, machine):
        machine.reads.clear(); machine.writes.clear()
        for address in (machine.PHYSICAL, machine.PRIVATE, machine.BACKEND, machine.WORLD):
            machine.cpu.mem_protect(address, 4096, machine.u.UC_PROT_NONE)

    def assert_unsafe(self, machine):
        with self.assertRaises(self.tools[0].UcError):
            machine.complete()
        eip = machine.cpu.reg_read(machine.regs["EIP"])
        self.assertEqual(eip, dict(machine.loss_emission.private_entries)["unsafe_control"]+machine.delta)
        self.assertEqual(bytes(machine.cpu.mem_read(eip, 2)), b"\x0f\x0b")
        self.assertIsNone(machine.native_stop)
        self.assertEqual(machine.tiles, [(0,0)])
        self.assertEqual(machine.word(native.RENDER+machine.delta), machine.PHYSICAL)
        self.no_cached_reads(machine)

    def test_all36_presets_incremental_pixels_and_unchanged_owner(self):
        for profile in content_fixture.parent_fixture.context.PROFILES:
            for resolution in content_fixture.parent_fixture.context.RESOLUTIONS:
                with self.subTest(profile=profile, resolution=resolution):
                    m = self.make(profile, resolution, mode=1)
                    before = m.pixels(); record = m.record()
                    self.assertEqual(m.complete()["EAX"], 1)
                    self.assertEqual(m.tiles, [(0,0)])
                    self.assertEqual(m.record(), record)
                    oracle = lease_fixture.field_fixture.pixel_oracle
                    self.assertEqual(m.pixels(), oracle.expected_pixels(m.width, m.height, 2, 0, before, [(0,0)]))
                    self.assertEqual(m.word(native.RENDER), m.expected_original_render)
                    del m; gc.collect()

    def test_all_descriptor_words_deny_before_callbacks_or_cached_reads(self):
        for offset in range(0, 192, 4):
            with self.subTest(offset=offset):
                m = self.make("modalwidgets")
                def corrupt(mm, _, off=offset):
                    mm.put(mm.lease_frame+off, mm.word(mm.lease_frame+off) ^ (2 if off == 48 else 1))
                    self.poison_caches(mm)
                m.tile_mutation = corrupt
                callbacks = len(m.callbacks)
                if offset in (60,64):
                    self.assert_unsafe(m)
                else:
                    self.assertEqual(m.complete()["EAX"], 2)
                    self.assertEqual(m.tiles, [(0,0)])
                    self.no_cached_reads(m)
                    self.assertEqual(m.word(native.RENDER), m.PHYSICAL)
                self.assertEqual(m.callbacks[callbacks:], ["tile"])
                self.assertFalse(any(at == native.RENDER or m.lease_frame <= at < m.lease_frame+192 for at, _ in m.writes))
                del m; gc.collect()

    def test_thread_descriptor_loss_shadow_precedes_every_poisoned_cache_read(self):
        for offset in range(0, 192, 4):
            with self.subTest(offset=offset):
                m = self.make("framed")
                seen = []
                def corrupt(mm, label, off=offset):
                    if label == "thread":
                        mm.put(mm.lease_frame+off, mm.word(mm.lease_frame+off)^1)
                        self.poison_caches(mm); seen.append(label)
                m.mutation = corrupt
                self.assertEqual(m.complete()["EAX"], 2)
                self.assertEqual(seen, ["thread"])
                self.assertEqual(m.tiles, [(0,0)])
                self.assertEqual(m.word(native.RENDER), m.PHYSICAL)
                self.no_cached_reads(m)
                self.assertFalse(any(at == native.RENDER or m.lease_frame <= at < m.lease_frame+192 for at, _ in m.writes))
                del m; gc.collect()

    def test_thread_helper_control_and_paired_ancestor_mutations_stop_at_declared_unsafe(self):
        cases = [("helper", off) for off in tool.CONTROL_SLOTS] + [
            ("field_ebp", 1288), ("field_ret", 1316), ("outer_ret", 228), ("outer_ebp", 200),
            ("paired_ret", 228), ("paired_ebp", 200)]
        for role, offset in cases:
            with self.subTest(role=role, offset=offset):
                m = self.make("completehd", delta=0x100000)
                seen = []
                def corrupt(mm, label):
                    if label != "thread": return
                    helper = mm.field_frame-tool.HELPER_BYTES-40
                    at = helper+offset if role == "helper" else (
                        mm.field_frame+offset if role.startswith("field") else mm.lease_frame+offset)
                    mm.put(at, mm.word(at)^4)
                    if role.startswith("paired"):
                        shadow = mm.lease_frame+(60 if role == "paired_ret" else 64)
                        mm.put(shadow, mm.word(shadow)^4)
                    self.poison_caches(mm); seen.append(label)
                m.mutation = corrupt
                self.assert_unsafe(m)
                self.assertEqual(seen, ["thread"])
                del m; gc.collect()

    def test_fixed_tail_iat_and_actual_thread_mismatch_deny_without_cached_reads(self):
        for role in ("new_tail", "modal_tail", "iat", "thread", "cache", "control"):
            with self.subTest(role=role):
                m = self.make("modalwidgets")
                seen = []
                def corrupt(mm, label):
                    if label != "thread": return
                    at = {"new_tail": mm.state_va+65532, "modal_tail": mm.modal_va+4092,
                          "iat": 0x4ea4e8, "cache": mm.field_frame+1104,
                          "control": mm.field_frame+1156}.get(role)
                    if at is not None: mm.put(at, mm.word(at)^4)
                    else: mm.thread_id += 1
                    self.poison_caches(mm); seen.append(label)
                m.mutation = corrupt
                self.assertEqual(m.complete()["EAX"], 2)
                self.assertEqual(seen, ["thread"])
                self.assertEqual(m.tiles, [(0,0)])
                self.assertEqual(m.word(native.RENDER), m.PHYSICAL)
                self.no_cached_reads(m)
                del m; gc.collect()


TEST_COUNT = sum(unittest.defaultTestLoader.loadTestsFromTestCase(cls).countTestCases() for cls in (SourceTests, CPUTests))


def run_tests():
    before = source_closure()
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in (SourceTests, CPUTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if source_closure() != before:
        raise ValueError("field loss source closure changed during tests")
    if not result.wasSuccessful() or result.skipped or result.testsRun != TEST_COUNT:
        raise AssertionError("uninstalled field loss fixture failures")
    return result.testsRun


if __name__ == "__main__":
    if len(sys.argv) > 1:
        unittest.main()
    else:
        run_tests()
