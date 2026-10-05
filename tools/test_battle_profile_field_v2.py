#!/usr/bin/env python3
"""Versioned field receipt fixtures; synthetic CPU work and optional RAM audit.

The frozen v1 fixture supplies the independent destination-to-world oracle,
native callback model, ownership mutations and read/write canaries. Its source
identity is checked before reuse. No game, native renderer or output is created.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import hashlib
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import battle_profile_field as v1
from src.patcher import battle_profile_field_v2 as v2
from src.patcher import battle_profile_lifecycle as lifecycle
from src.patcher import battle_profile_routing as routing
from src.patcher import partial_tile_clip as clip
from src.patcher import framed_modal_canvas as native
import test_battle_profile_field as oracle

V1_SOURCE_SHA256 = "c329460fc7289d11ac10ddc33d26eb5ad158169ca976fee41ccd32fba6d97c88"
V1_FIXTURE_SHA256 = "d5776f1850e7f6c085fbfb08016f2eb17f4aa0f9889acd0807ad2dabe04979c6"
PRIVATE = ("capture_invocation", "check_invocation", "same_invocation")


def verify_frozen_sources():
    for name, expected in ((v1.SOURCE, V1_SOURCE_SHA256),
                           ("tools/test_battle_profile_field.py", V1_FIXTURE_SHA256)):
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("frozen field fixture/source differs: " + name)


class VersionedOracleMixin:
    def setUp(self):
        verify_frozen_sources()
        self.selector = patch.object(oracle, "field", return_value=v2)
        self.selector.start()
        self.addCleanup(self.selector.stop)
        super().setUp()


class SourceTests(VersionedOracleMixin, oracle.SourceTests):
    def test_native_caller_clip_classification(self):
        # Exact original-backed call-site ledger, independent of synthetic
        # pixel callbacks. Whole native bodies remain bound by NATIVE_SPANS.
        tree = ast.parse((ROOT / v2.SOURCE).read_text(encoding="utf-8"))
        producers = [node for node in ast.walk(tree)
                     if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                     and node.func.id == "dict" and any(
                         item.arg == "schema" and isinstance(item.value, ast.Constant)
                         and item.value.value == "clash95_battle_profile_field_v2"
                         for item in node.keywords)]
        self.assertEqual(len(producers), 1)
        fields = {item.arg: item.value for item in producers[0].keywords if item.arg}
        self.assertNotIn("native_caller_sprite_clipping_enabled", fields)
        expected = {
            "native_tile_disabled_clip_sprite_sites":
                [0x430035, 0x4300F3, 0x43024E, 0x430349, 0x4307AA, 0x43080C, 0x430991],
            "native_tile_cell_clip_sprite_sites": [0x430733],
            "native_unit_cell_clipping_present": True,
            "native_unit_cell_clip_sprite_sites": [0x42FC1B],
            "arena_intersection_verified": False,
            "native_arena_clipping_verified": False,
        }
        for name, value in expected.items():
            self.assertEqual(ast.literal_eval(fields[name]), value, name)
        for lane, span in (("native_tile_disabled_clip_sprite_sites", "tile"),
                           ("native_tile_cell_clip_sprite_sites", "tile"),
                           ("native_unit_cell_clip_sprite_sites", "unit_draw")):
            lo, hi, _ = v2.NATIVE_SPANS[span]
            self.assertTrue(all(lo <= site < hi for site in expected[lane]))
        self.assertEqual(len(set(expected["native_tile_disabled_clip_sprite_sites"]
                                 + expected["native_tile_cell_clip_sprite_sites"])), 8)

    def test_shared_layout_and_relocation_inventory(self):
        self.assertEqual(v2.PINNED_SOURCES[v1.SOURCE], V1_SOURCE_SHA256)
        self.assertEqual(v2.NATIVE_SPANS, v1.NATIVE_SPANS)
        self.assertEqual(v2.STATE, v1.STATE)
        self.assertEqual(v2.ENTRIES, v1.ENTRIES)
        for profile in oracle.PROFILES:
            for resolution in oracle.RESOLUTIONS:
                plan = oracle.lifetime_fixture.synthetic_plan(profile, resolution)
                modal = None if profile in ("classic", "framed") else plan["rw"]["va"] - 256
                life = lifecycle._emit_code(plan, modal_state_va=modal, assembler_module=clip)
                route = routing._emit_code(plan, life, modal_state_va=modal, assembler_module=clip)
                old = v1._emit_code(plan, route, assembler_module=clip)
                new = v2._emit_code(plan, route, assembler_module=clip)
                self.assertEqual(tuple(name for name, _ in new.private_entries), PRIVATE)
                self.assertEqual(len(set(value for _, value in new.private_entries)), 3)
                self.assertLess(len(new.code), len(old.code) // 3)
                self.assertEqual(new.base_va, old.base_va)
                self.assertEqual(new.state_va, old.state_va)
                self.assertEqual(new.width, old.width)
                self.assertEqual(new.height, old.height)
                self.assertLessEqual(new.base_va + len(new.code), plan["rx"]["va"] + 0x20000)
                offsets = set()
                private_calls = 0
                for row in new.relocations:
                    self.assertNotIn(row.offset, offsets)
                    offsets.add(row.offset)
                    self.assertTrue(0 <= row.offset <= len(new.code) - 4)
                    if row.kind == "abs32":
                        self.assertEqual(struct.unpack_from("<I", new.code, row.offset)[0], row.target)
                    elif row.kind == "rel32":
                        self.assertEqual(new.code[row.offset - 1], 0xE8)
                        displacement = struct.unpack_from("<i", new.code, row.offset)[0]
                        self.assertEqual(new.base_va + row.offset + 4 + displacement, row.target)
                        if row.target in dict(new.private_entries).values():
                            private_calls += 1
                    else:
                        self.fail("unknown field relocation kind")
                self.assertEqual(private_calls, 8)


class CPUTests(VersionedOracleMixin, oracle.CPUTests):
    # The paired all-cell test below includes the full original pixel oracle,
    # two image bases, every preset and both implementations.
    test_full_field_all_36_at_two_bases_and_native_size = None

    def make(self, module, profile="classic", resolution="1024x768", delta=0,
             *, columns=20, scroll=0):
        with patch.object(oracle, "field", return_value=module):
            machine = oracle.Machine(self.tools, profile, resolution, delta).prepare(
                columns=columns, scroll=scroll)
        machine.thread_clobbers = True
        return machine

    def test_all_36_two_bases_v1_v2_pixels_queries_callbacks_and_abi(self):
        for profile in oracle.PROFILES:
            for resolution in oracle.RESOLUTIONS:
                width, _ = map(int, resolution.split("x"))
                visible = min(20, (width - 192) // 64)
                scroll = 20 - visible
                for delta in (0, 0x100000):
                    with self.subTest(profile=profile, resolution=resolution, delta=delta):
                        old = self.make(v1, profile, resolution, delta, scroll=scroll)
                        new = self.make(v2, profile, resolution, delta, scroll=scroll)
                        before = new.pixels()
                        operations = (("visible_columns", {}),
                            ("clamp_scroll_x", dict(edx=-1)),
                            ("clamp_scroll_x", dict(edx=0x7FFFFFFF)),
                            ("screen_to_cell", dict(edx=32 + visible * 64 - 1, ecx=463)),
                            ("screen_to_cell", dict(edx=31, ecx=16)),
                            ("visible_cell", dict(eax=scroll, edx=6)),
                            ("visible_cell", dict(eax=20, edx=6)),
                            ("draw_full", {}),
                            ("draw_incremental", dict(eax=scroll + visible - 1, edx=6)))
                        for name, arguments in operations:
                            left = old.invoke_field(name, **arguments)
                            right = new.invoke_field(name, **arguments)
                            self.assertEqual(left, right, name)
                            self.assertEqual(old.field_callbacks, new.field_callbacks, name)
                            self.assertEqual(old.tiles, new.tiles, name)
                            self.assertEqual(old.record(), new.record(), name)
                            self.assertEqual(old.pixels(), new.pixels(), name)
                            self.assertEqual(old.word(native.RENDER + delta), new.word(native.RENDER + delta), name)
                        expected = oracle.expected_pixels(new.width, new.height, 20, scroll, before)
                        self.assertEqual(new.pixels(), expected)

    def test_private_calls_have_explicit_outer_frame_and_balanced_returns(self):
        for profile in oracle.PROFILES:
            for delta in (0, 0x100000):
                with self.subTest(profile=profile, delta=delta):
                    m = self.make(v2, profile, "1366x768", delta, columns=2)
                    frame = m.SP - 36 - v2.STACK_BYTES
                    names = {va + delta: name for name, va in m.field_emission.private_entries}
                    trace = []
                    def observe(cpu, address, size, data):
                        if address in names:
                            name = names[address]
                            trace.append(name)
                            self.assertEqual(cpu.reg_read(m.regs["EBP"]), frame)
                            expected_sp = frame - (8 if name == "check_invocation" else 4)
                            self.assertEqual(cpu.reg_read(m.regs["ESP"]), expected_sp)
                    m.cpu.hook_add(m.u.UC_HOOK_CODE, observe)
                    for address in (m.SP - 0x1800, m.SP + 4):
                        m.cpu.mem_write(address, b"\xA9" * 16)
                    self.assertEqual(m.invoke_field("draw_full")["EAX"], 1)
                    self.assertEqual(trace.count("capture_invocation"), 1)
                    self.assertEqual(trace.count("same_invocation"), 28)
                    self.assertEqual(trace.count("check_invocation"), 56)
                    for address in (m.SP - 0x1800, m.SP + 4):
                        self.assertEqual(bytes(m.cpu.mem_read(address, 16)), b"\xA9" * 16)

    def test_each_nested_check_failure_returns_before_outer_lost(self):
        for profile in oracle.PROFILES:
            for ordinal in (1, 2, 3, 4):
                with self.subTest(profile=profile, ordinal=ordinal):
                    m = self.make(v2, profile, columns=2)
                    m.put(native.RENDER, m.PRIVATE)
                    before = m.pixels()
                    frame = m.SP - 36 - v2.STACK_BYTES
                    check = dict(m.field_emission.private_entries)["check_invocation"]
                    seen = []
                    def corrupt(cpu, address, size, data):
                        if address == check:
                            seen.append(address)
                            self.assertEqual(cpu.reg_read(m.regs["EBP"]), frame)
                            self.assertEqual(cpu.reg_read(m.regs["ESP"]), frame - 8)
                            if len(seen) == ordinal:
                                # Fixed authority changes before poisoning its
                                # cached header. No helper may dereference it.
                                m.put(native.MAP, 0)
                                m.cpu.mem_protect(m.PHYSICAL, 4096, m.u.UC_PROT_NONE)
                    m.cpu.hook_add(m.u.UC_HOOK_CODE, corrupt)
                    for address in (m.SP - 0x1800, m.SP + 4):
                        m.cpu.mem_write(address, b"\xB7" * 16)
                    self.assertEqual(m.invoke_field("draw_full")["EAX"], 2)
                    self.assertEqual(len(seen), ordinal)
                    tiles = [] if ordinal <= 2 else [(0, 0)]
                    self.assertEqual(m.tiles, tiles)
                    self.assertEqual(m.pixels(), oracle.expected_pixels(m.width, m.height, 2, 0, before, tiles))
                    self.assertEqual(m.word(native.RENDER), m.PHYSICAL)
                    for address in (m.SP - 0x1800, m.SP + 4):
                        self.assertEqual(bytes(m.cpu.mem_read(address, 16)), b"\xB7" * 16)

    def test_second_thread_callback_loss_at_both_bases_consumes_nested_calls(self):
        for profile in oracle.PROFILES:
            for delta in (0, 0x100000):
                with self.subTest(profile=profile, delta=delta):
                    m = self.make(v2, profile, "1366x768", delta, columns=2)
                    m.put(native.RENDER + delta, m.PRIVATE)
                    before, fired = m.pixels(), []
                    def mutate(machine, name):
                        if name == "thread":
                            fired.append(name)
                            if len(fired) == 2:
                                machine.put(native.MAP + delta, 0)
                                machine.cpu.mem_protect(machine.PHYSICAL, 4096, machine.u.UC_PROT_NONE)
                    m.mutation = mutate
                    for address in (m.SP - 0x1800, m.SP + 4):
                        m.cpu.mem_write(address, b"\xC9" * 16)
                    self.assertEqual(m.invoke_field("draw_full")["EAX"], 2)
                    self.assertEqual(fired, ["thread", "thread"])
                    self.assertEqual(m.tiles, [])
                    self.assertEqual(m.pixels(), before)
                    self.assertEqual(m.word(native.RENDER + delta), m.PHYSICAL)
                    for address in (m.SP - 0x1800, m.SP + 4):
                        self.assertEqual(bytes(m.cpu.mem_read(address, 16)), b"\xC9" * 16)


def report_budget():
    for profile in oracle.PROFILES:
        plan = oracle.lifetime_fixture.synthetic_plan(profile, "3840x2160")
        modal = None if profile in ("classic", "framed") else plan["rw"]["va"] - 256
        life = lifecycle._emit_code(plan, modal_state_va=modal, assembler_module=clip)
        route = routing._emit_code(plan, life, modal_state_va=modal, assembler_module=clip)
        first = v1._emit_code(plan, route, assembler_module=clip)
        second = v2._emit_code(plan, route, assembler_module=clip)
        occupied = second.base_va + len(second.code) - plan["rx"]["va"]
        print("SOURCE_RX_BUDGET", profile, "3840x2160", "v1_field", len(first.code),
              "v2_field", len(second.code), "remaining", 0x20000 - occupied,
              "installed=false", "native_execution=false")


def original_checks(path):
    with patch.object(oracle, "field", return_value=v2), \
            patch.object(v1, "emit_battle_profile_field", side_effect=AssertionError("public v1 producer")), \
            patch.dict(v1.STATE, {"fault": 128}), \
            patch.object(v1, "_emit_code", side_effect=AssertionError("public v1 emitter")):
        oracle.original_checks(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolchain-path", type=Path)
    parser.add_argument("--require-machine-tools", action="store_true")
    parser.add_argument("--original-backed", type=Path)
    args = parser.parse_args(argv)
    verify_frozen_sources()
    if args.toolchain_path:
        sys.path.insert(0, str(args.toolchain_path.resolve()))
    if args.require_machine_tools:
        try:
            oracle.lifetime_fixture.machine_tools()
        except ImportError as error:
            print(str(error), file=sys.stderr)
            return 2
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
                               for cls in (SourceTests, CPUTests))
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
        return 1
    report_budget()
    if args.original_backed:
        original_checks(args.original_backed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
