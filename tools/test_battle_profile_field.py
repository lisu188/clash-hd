#!/usr/bin/env python3
"""Uninstalled field helpers on synthetic x86 and modeled native tile calls.

There is no game, renderer, debugger, screenshot or runtime input in this
fixture. The native tile callback below paints a deterministic test pattern;
its call arguments and untouched regions are checked independently. Optional
original-backed reconstruction reads the user's executable only into memory.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import importlib
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import battle_profile_context as context
from src.patcher import battle_profile_lifecycle as lifecycle
from src.patcher import battle_profile_routing as routing
from src.patcher import partial_tile_clip as clip
from src.patcher import framed_modal_canvas as native
import test_battle_profile_lifecycle as lifetime_fixture
import test_battle_profile_routing as routing_fixture

PROFILES = ("classic", "framed", "completehd", "modalwidgets")
RESOLUTIONS = ("800x600", "1024x768", "1280x720", "1280x960", "1366x768",
               "1920x1080", "2560x1440", "3440x1440", "3840x2160")
ENTRIES = ("visible_columns", "clamp_scroll_x", "screen_to_cell", "visible_cell",
           "draw_full", "draw_incremental")
TILE = 0x42FFB0
REJECT, PARTIAL = 0xFFFFFFFF, 2
RET_SPANS = {"effects": (0x4055BC, 0x4055BF, 0x20),
             "memory_sprite": (0x403D67, 0x403D6A, 0x1C),
             "memory_line": (0x40403A, 0x40403D, 8)}


def field():
    return importlib.import_module("src.patcher.battle_profile_field")


def color(x, y):
    return 1 + (29 * x + 17 * y) % 254


def expected_pixels(width, height, columns, scroll, before, cells=None):
    """Destination-to-world oracle; no producer's loop or rectangle ledger."""
    visible = min(columns, (width - 192) // 64)
    selected = None if cells is None else set(cells)
    result = bytearray(before)
    for py in range(16, 464):
        y = (py - 16) // 64
        for local_x in range(visible):
            x = scroll + local_x
            if selected is None or (x, y) in selected:
                left = py * width + 32 + local_x * 64
                result[left:left + 64] = bytes([color(x, y)]) * 64
    assert len(result) == width * height
    return bytes(result)


class Machine(routing_fixture.Machine):
    def __init__(self, tools, profile="classic", resolution="1024x768", delta=0):
        self.field_active = False
        self.tiles = []
        self.tile_mutation = None
        self.tile_clobbers = True
        super().__init__(tools, profile, resolution, delta)
        self.field_emission = field()._emit_code(self.plan, self.routing_emission,
                                                assembler_module=clip)
        self.field_entries = {name: va + delta for name, va in self.field_emission.entries}
        code = bytearray(self.field_emission.code)
        for row in self.field_emission.relocations:
            if row.kind == "abs32":
                struct.pack_into("<I", code, row.offset, row.target + delta)
        self.cpu.mem_write(self.field_emission.base_va + delta, bytes(code))

    def on_code(self, cpu, address, size, data):
        if address == TILE + self.delta:
            assert self.field_active, "native tile outside a field invocation"
            assert cpu.reg_read(self.regs["EFLAGS"]) & 0x400 == 0, "native tile DF1"
            assert self.word(native.RENDER + self.delta) == self.PHYSICAL, "tile target is not physical"
            x, y = (cpu.reg_read(self.regs[n]) for n in ("EAX", "EDX"))
            columns, scroll = self.word(self.WORLD + 804), self.word(self.WORLD + 808)
            visible = min(columns, (self.width - 192) // 64)
            assert 0 <= y < 7 and scroll <= x < scroll + visible, (x, y, columns, scroll)
            self.tiles.append((x, y))
            self.callback("tile")
            # Paint using the native projection model, rather than the helper's
            # loop counters. API writes are independent from emitted CPU writes.
            left, top = 32 + (x - scroll) * 64, 16 + y * 64
            row = bytes([color(x, y)]) * 64
            for py in range(top, top + 64):
                cpu.mem_write(self.PHYSICAL_PIXELS + py * self.width + left, row)
            if self.tile_mutation:
                self.tile_mutation(self, len(self.tiles))
            if self.tile_clobbers:
                cpu.reg_write(self.regs["EDX"], 0xBCDE2345)
                cpu.reg_write(self.regs["EFLAGS"], 0x202)
            self.ret(0xCDEF3456)
        else:
            super().on_code(cpu, address, size, data)

    def prepare(self, *, columns=20, scroll=0, bound=True):
        super().prepare(bound=bound)
        self.put(self.WORLD + 804, columns)
        self.put(self.WORLD + 808, scroll)
        return self

    def invoke_field(self, name, *, eax=0x12345678, edx=0x22334455,
                     ecx=0x11223344, flags=0xED7):
        self.field_active = True
        self.routing_active = True
        self.stops, self.native_stop = set(), None
        self.writes, self.reads, self.tiles = [], [], []
        begin = len(self.callbacks)
        registers = dict(EAX=eax, EDX=edx, ECX=ecx, EBX=0x33445566,
                         EBP=0x44556677, ESI=0x55667788, EDI=0x66778899, ESP=self.SP)
        self.put(self.SP, self.STOP)
        for key, value in registers.items():
            self.cpu.reg_write(self.regs[key], value & 0xFFFFFFFF)
        self.cpu.reg_write(self.regs["EFLAGS"], flags)
        try:
            self.cpu.emu_start(self.field_entries[name], self.STOP + 1, count=10000000)
        finally:
            self.field_active = False
            self.routing_active = False
        actual = {key: self.cpu.reg_read(reg) for key, reg in self.regs.items()}
        assert self.native_stop == self.STOP, (name, actual)
        assert actual["ESP"] == self.SP + 4, (name, actual)
        for key, value in registers.items():
            if key not in ("EAX", "ESP"):
                assert actual[key] == value & 0xFFFFFFFF, (name, key, actual[key], value)
        assert actual["EFLAGS"] & self.MASK == flags & self.MASK, (name, actual)
        self.field_callbacks = self.callbacks[begin:]
        # Emitted helpers own only their stack and the scoped render assignment.
        # Pixels are written by the explicitly modeled tile call above.
        for address, size in self.writes:
            assert (self.STACK <= address and address + size <= self.STACK + 0x10000
                    or address == native.RENDER + self.delta and size == 4), (name, address, size)
        for at in (self.state_va - 16, self.state_va + 128, self.PRIVATE - 16,
                   self.PRIVATE + 188, self.private_pixels - 16, self.private_pixels + 307200,
                   self.PHYSICAL_PIXELS - 16, self.PHYSICAL_PIXELS + self.width * self.height):
            assert bytes(self.cpu.mem_read(at, 16)) == b"\xD7" * 16, (name, hex(at))
        return actual


class SourceTests(unittest.TestCase):
    def test_exact_geometry_inventory_is_independent(self):
        self.assertEqual(context.PROFILES, PROFILES)
        self.assertEqual(context.RESOLUTIONS, RESOLUTIONS)
        self.assertEqual(len(PROFILES) * len(RESOLUTIONS), 36)

    def test_public_boundary_requires_original_and_fixed_selectors(self):
        module = field()
        for original, profile, resolution in ((b"", "classic", "800x600"),
                                              (bytearray(), "classic", "800x600"),
                                              (b"", "other", "800x600"),
                                              (b"", "classic", "802x602")):
            with self.assertRaises(ValueError):
                module.emit_battle_profile_field(original, profile, resolution)

    def test_pure_boundary_rejects_substituted_guard_and_allocation(self):
        module = field()
        plan = lifetime_fixture.synthetic_plan()
        life = lifecycle._emit_code(plan, modal_state_va=None, assembler_module=clip)
        route = routing._emit_code(plan, life, modal_state_va=None, assembler_module=clip)
        emitted = module._emit_code(plan, route, assembler_module=clip)
        self.assertEqual(tuple(name for name, _ in emitted.entries), ENTRIES)
        self.assertEqual(emitted.base_va, (route.base_va + len(route.code) + 15) & ~15)
        self.assertLessEqual(emitted.base_va + len(emitted.code), plan["rx"]["va"] + 0x20000)
        for change in ("resolution", "code", "state", "entries", "guard", "rx", "rw"):
            bad_plan = deepcopy(plan)
            # Frozen emission replacement preserves the exact type.
            from dataclasses import replace
            bad = route
            if change == "resolution": bad = replace(route, width=route.width + 1)
            elif change == "code": bad = replace(route, code=b"")
            elif change == "state": bad = replace(route, state_va=route.state_va + 4)
            elif change == "entries": bad = replace(route, entries=tuple((n, v) for n, v in route.entries if n != "check_owned_bound"))
            elif change == "guard": bad = replace(route, entries=tuple((n, route.base_va - 4 if n == "check_owned_bound" else v) for n, v in route.entries))
            elif change == "rx": bad_plan["rx"]["virtual_reservation"] = 0x40000
            else: bad_plan["rw"]["page_bytes"] = 128
            with self.subTest(change=change), self.assertRaises(ValueError):
                module._emit_code(bad_plan, bad, assembler_module=clip)

    def test_private_source_graph_ignores_public_helpers(self):
        module = field()
        snapshot = module._snapshot()
        plan = lifetime_fixture.synthetic_plan()
        life = lifecycle._emit_code(plan, modal_state_va=None, assembler_module=clip)
        route = routing._emit_code(plan, life, modal_state_va=None, assembler_module=clip)
        expected = module._emit_code(plan, route, assembler_module=clip)
        modules_before = set(sys.modules)
        with patch.object(clip, "_Assembler", side_effect=AssertionError("public assembler")), \
                patch.object(routing, "emit_battle_profile_routing", side_effect=AssertionError("public routing")), \
                patch.object(module, "_emit_code", side_effect=AssertionError("public field")):
            with module._modules(snapshot) as modules:
                private = modules[module.SOURCE]
                private_clip = modules["src/patcher/partial_tile_clip.py"]
                actual = private._emit_code(plan, route, assembler_module=private_clip)
        self.assertEqual(actual.code, expected.code)
        self.assertEqual(actual.entries, expected.entries)
        describe = lambda item: (item.offset, item.kind, item.target, item.purpose)
        self.assertEqual(tuple(map(describe, actual.relocations)), tuple(map(describe, expected.relocations)))
        self.assertFalse(any(name.startswith("_clash95_battle_field_")
                             for name in set(sys.modules) - modules_before))

    def test_native_span_pins_include_both_ret_operands(self):
        module = field()
        for name, (ret_va, end, _) in RET_SPANS.items():
            self.assertEqual(module.NATIVE_SPANS[name][1], end)
            self.assertEqual(end - ret_va, 3)
        # This models only the digest-checking boundary. The image is an
        # independently generated byte pattern, never native game instructions.
        image = bytearray(0x110000)
        pins = {}
        for name, (lo, hi, _) in module.NATIVE_SPANS.items():
            raw = bytes((index * 17 + lo) % 256 for index in range(hi - lo))
            image[lo - 0x400000:hi - 0x400000] = raw
        for name, (ret_va, _, stack_pop) in RET_SPANS.items():
            image[ret_va - 0x400000:ret_va - 0x400000 + 3] = b"\xC2" + struct.pack("<H", stack_pop)
        image[0x10EE24:0x10EE24 + 80] = struct.pack("<20I", *clip.VTABLE_ENTRIES)
        for name, (lo, hi, _) in module.NATIVE_SPANS.items():
            pins[name] = (lo, hi, module._sha(bytes(image[lo - 0x400000:hi - 0x400000])))
        reader = SimpleNamespace(file_offset=lambda data, va, size: va - 0x400000,
                                 VTABLE_ENTRIES=clip.VTABLE_ENTRIES)
        with patch.object(module, "NATIVE_SPANS", pins):
            module._authenticate_native(bytes(image), bytes(image), reader)
            for name, (ret_va, _, _) in RET_SPANS.items():
                for operand in (1, 2):
                    changed = bytearray(image)
                    changed[ret_va - 0x400000 + operand] ^= 1
                    with self.subTest(span=name, operand=operand), self.assertRaises(ValueError):
                        module._authenticate_native(bytes(image), bytes(changed), reader)


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.tools = lifetime_fixture.machine_tools()
        except ImportError as error:
            raise unittest.SkipTest(str(error))

    def test_full_field_all_36_at_two_bases_and_native_size(self):
        for profile in PROFILES:
            for resolution in RESOLUTIONS:
                for delta in (0, 0x100000):
                    with self.subTest(profile=profile, resolution=resolution, delta=delta):
                        m = Machine(self.tools, profile, resolution, delta).prepare()
                        m.thread_clobbers = True
                        before, owner = m.pixels(), m.record()
                        prior_render = m.word(native.RENDER + delta)
                        self.assertEqual(m.invoke_field("draw_full")["EAX"], 1)
                        visible = min(20, (m.width - 192) // 64)
                        self.assertEqual(len(m.tiles), visible * 7)
                        self.assertEqual(set(m.tiles), {(x, y) for x in range(visible) for y in range(7)})
                        self.assertEqual(m.pixels(), expected_pixels(m.width, m.height, 20, 0, before))
                        self.assertEqual(m.word(native.RENDER + delta), prior_render)
                        self.assertEqual(m.record(), owner)
                        self.assertTrue(all(name in ("thread", "tile") for name in m.field_callbacks))

    def test_small_arenas_origins_and_incremental_pixels(self):
        for resolution in ("800x600", "1366x768", "3440x1440", "3840x2160"):
            width, _ = map(int, resolution.split("x"))
            for columns in (1, 2, 7, 9, 13, 20):
                visible = min(columns, (width - 192) // 64)
                scroll = columns - visible
                m = Machine(self.tools, "modalwidgets", resolution).prepare(columns=columns, scroll=scroll)
                before = m.pixels()
                x, y = scroll + visible - 1, 6
                self.assertEqual(m.invoke_field("draw_incremental", eax=x, edx=y, flags=0xAD7)["EAX"], 1)
                self.assertEqual(m.tiles, [(x, y)])
                self.assertEqual(m.pixels(), expected_pixels(m.width, m.height, columns, scroll, before, [(x, y)]))

    def test_coordinate_queries_and_pixel_boundaries(self):
        for profile in PROFILES:
            for resolution in RESOLUTIONS:
                m = Machine(self.tools, profile, resolution).prepare()
                visible = min(20, (m.width - 192) // 64)
                scroll = 20 - visible
                m.put(m.WORLD + 808, scroll)
                before, owner = m.pixels(), m.record()
                self.assertEqual(m.invoke_field("visible_columns")["EAX"], visible)
                for requested in (-2147483648, -1, 0, scroll, scroll + 1, 2147483647):
                    self.assertEqual(m.invoke_field("clamp_scroll_x", edx=requested)["EAX"], min(max(requested, 0), scroll))
                for px, py in ((32, 16), (32 + visible * 64 - 1, 463), (31, 16),
                               (32, 15), (32 + visible * 64, 16), (32, 464),
                               (m.width - 160, 100), (m.width - 1, m.height - 1), (-1, 0)):
                    expected = ((scroll + (px - 32) // 64) | (((py - 16) // 64) << 16)
                                if 32 <= px < 32 + visible * 64 and 16 <= py < 464 else REJECT)
                    self.assertEqual(m.invoke_field("screen_to_cell", edx=px, ecx=py)["EAX"], expected)
                for x, y in ((scroll, 0), (scroll + visible - 1, 6), (scroll - 1, 0),
                             (scroll + visible, 0), (-1, 0), (20, 0), (scroll, -1), (scroll, 7)):
                    expected = (int(scroll <= x < scroll + visible) if 0 <= x < 20 and 0 <= y < 7 else REJECT)
                    self.assertEqual(m.invoke_field("visible_cell", eax=x, edx=y)["EAX"], expected)
                self.assertEqual(m.pixels(), before)
                self.assertEqual(m.record(), owner)
                self.assertEqual(m.tiles, [])

    def test_off_field_incremental_never_calls_tile_or_changes_target(self):
        m = Machine(self.tools, "framed", "800x600").prepare(columns=20, scroll=11)
        before, owner, render = m.pixels(), m.record(), m.word(native.RENDER)
        for x, y in ((-1, 0), (10, 0), (20, 0), (11, -1), (11, 7), (0x7FFFFFFF, 6)):
            self.assertEqual(m.invoke_field("draw_incremental", eax=x, edx=y)["EAX"], 0)
            self.assertEqual(m.tiles, [])
            self.assertEqual(m.pixels(), before)
            self.assertEqual(m.record(), owner)
            self.assertEqual(m.word(native.RENDER), render)

    def test_ownership_and_invalid_geometry_reject_without_pixels(self):
        changes = (("phase", 1), ("fault", 7), ("owner_tid", 99),
                   ("return_status", 1), ("pending_header", 0x20003000))
        for name, value in changes:
            m = Machine(self.tools, "modalwidgets").prepare()
            m.set_state(name, value)
            before, render = m.pixels(), m.word(native.RENDER)
            self.assertEqual(m.invoke_field("draw_full")["EAX"], 0)
            self.assertEqual(m.tiles, [])
            self.assertEqual(m.pixels(), before)

            self.assertEqual(m.word(native.RENDER), render)
        for offset, value in ((800, 6), (804, 0), (804, 21), (808, -1), (808, 8), (812, 1)):
            m = Machine(self.tools, "classic", "1024x768").prepare()
            m.put(m.WORLD + offset, value)
            before = m.pixels()
            self.assertEqual(m.invoke_field("draw_full")["EAX"], 0)
            self.assertEqual(m.tiles, [])
            self.assertEqual(m.pixels(), before)

    def test_partial_tile_does_not_restore_lost_ownership_or_continue(self):
        changes = ("owner_padding", "modal_padding", "balanced_counters", "valid_scroll",
                   "physical_header", "native_header", "primary_header", "backend_header",
                   "render_global", "world_global")
        for change in changes:
            with self.subTest(change=change):
                m = Machine(self.tools, "modalwidgets", "800x600").prepare()
                m.put(native.RENDER, m.PRIVATE)
                before = m.pixels()
                fired = []
                def mutate(machine, ordinal):
                    self.assertEqual(ordinal, 1)
                    fired.append(change)
                    if change == "owner_padding": machine.put(machine.state_va + 120, 9)
                    elif change == "modal_padding": machine.put(machine.modal_va + 120, 9)
                    elif change == "balanced_counters":
                        machine.set_state("allocations", machine.state("allocations") + 1)
                        machine.set_state("frees", machine.state("frees") + 1)
                    elif change == "valid_scroll": machine.put(machine.WORLD + 808, 1)
                    elif change == "physical_header": machine.put(machine.PHYSICAL + 120, 9)
                    elif change == "native_header": machine.put(machine.PRIVATE + 120, 9)
                    elif change == "primary_header": machine.put(native.PRIMARY + 120, 9)
                    elif change == "backend_header": machine.put(machine.BACKEND + 120, 9)
                    elif change == "render_global": machine.put(native.RENDER, native.PRIMARY)
                    else: machine.put(routing.BATTLE, machine.WORLD + 4)
                m.tile_mutation = mutate
                self.assertEqual(m.invoke_field("draw_full")["EAX"], PARTIAL)
                self.assertEqual(fired, [change])
                self.assertEqual(m.tiles, [(0, 0)])
                self.assertEqual(m.pixels(), expected_pixels(m.width, m.height, 20, 0, before, [(0, 0)]))
                # Ownership loss cannot authorize restoring the borrowed HUD
                # target. A changed render global itself must also be retained.
                self.assertEqual(m.word(native.RENDER), native.PRIMARY if change == "render_global" else m.PHYSICAL)

    def test_callback_rejection_precedes_poisoned_cached_heap_reads(self):
        for name, pointer, heap_name in (("physical", native.MAP, "PHYSICAL"),
                                         ("native", routing.OWNER, "PRIVATE"),
                                         ("world", routing.BATTLE, "WORLD")):
            with self.subTest(heap=name):
                m = Machine(self.tools, "modalwidgets").prepare()
                m.put(native.RENDER, m.PRIVATE)
                before, fired = m.pixels(), []
                def mutate(machine, ordinal):
                    fired.append(ordinal)
                    machine.put(pointer, 0)
                    machine.cpu.mem_protect(getattr(machine, heap_name), 4096, machine.u.UC_PROT_NONE)
                m.tile_mutation = mutate
                self.assertEqual(m.invoke_field("draw_full")["EAX"], PARTIAL)
                self.assertEqual(fired, [1])
                self.assertEqual(m.tiles, [(0, 0)])
                self.assertEqual(m.pixels(), expected_pixels(m.width, m.height, 20, 0, before, [(0, 0)]))
                self.assertEqual(m.word(native.RENDER), m.PHYSICAL)

    def test_scoped_guard_callback_loss_has_no_native_tile(self):
        m = Machine(self.tools, "classic").prepare()
        m.put(native.RENDER, m.PRIVATE)
        before, fired = m.pixels(), []
        def mutate(machine, name):
            if name == "thread":
                fired.append(name)
                if len(fired) == 2:
                    machine.put(native.MAP, 0)
                    machine.cpu.mem_protect(machine.PHYSICAL, 4096, machine.u.UC_PROT_NONE)
        m.mutation = mutate
        self.assertEqual(m.invoke_field("draw_full")["EAX"], PARTIAL)
        self.assertEqual(fired, ["thread", "thread"])
        self.assertEqual(m.tiles, [])
        self.assertEqual(m.pixels(), before)
        self.assertEqual(m.word(native.RENDER), m.PHYSICAL)

    def test_audited_effect_globals_are_not_owner_receipts(self):
        m = Machine(self.tools, "framed", "800x600").prepare()
        before, owner = m.pixels(), m.record()
        def mutate(machine, ordinal):
            for pointer in (0x532104, 0x519A14, 0x5320F4, 0x5320F8):
                machine.put(pointer, ordinal)
        m.tile_mutation = mutate
        self.assertEqual(m.invoke_field("draw_full")["EAX"], 1)
        self.assertEqual(len(m.tiles), 63)
        self.assertEqual(m.record(), owner)
        self.assertEqual(m.pixels(), expected_pixels(m.width, m.height, 20, 0, before))


def original_checks(path):
    module = field()
    original = path.read_bytes()
    for name, (ret_va, _, _) in RET_SPANS.items():
        for operand in (1, 2):
            changed = bytearray(original)
            changed[clip.file_offset(original, ret_va, 3) + operand] ^= 1
            try:
                module._authenticate_native(original, bytes(changed), clip)
            except ValueError:
                pass
            else:
                raise AssertionError(("unauthenticated RET operand", name, operand))
    print("ORIGINAL_MEMORY_RET_REJECTION_PASS", "six_operand_changes", "native_execution=false")
    for profile, resolution in (("classic", "1024x768"), ("classic", "1366x768"),
                                ("framed", "1366x768"), ("completehd", "1366x768"),
                                ("modalwidgets", "1366x768")):
        bundle = module.emit_battle_profile_field(original, profile, resolution)
        metadata = bundle.metadata()
        assert metadata["installed"] is False
        assert all(metadata[name] is False for name in context.FALSE_CLAIMS)
        assert tuple(name for name, _ in bundle.emission.entries) == ENTRIES
        assert bundle.hook_sites == () and bundle.removed_highlow_rvas == ()
        with patch.object(context, "build_parent_context", side_effect=AssertionError("public context")), \
                patch.object(lifecycle, "emit_battle_profile_lifecycle", side_effect=AssertionError("public lifetime")), \
                patch.object(routing, "emit_battle_profile_routing", side_effect=AssertionError("public routing")), \
                patch.object(clip, "_Assembler", side_effect=AssertionError("public assembler")), \
                patch.object(module, "_authenticate_native", side_effect=AssertionError("public native authority")), \
                patch.object(module, "_emit_code", side_effect=AssertionError("public field")):
            replay = module.emit_battle_profile_field(original, profile, resolution)
        assert replay.emission.code == bundle.emission.code and replay.metadata() == metadata
        assert path.read_bytes() == original
        print("ORIGINAL_MEMORY_FIELD_PASS", profile, resolution, "native_execution=false")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolchain-path", type=Path)
    parser.add_argument("--require-machine-tools", action="store_true")
    parser.add_argument("--original-backed", type=Path)
    args = parser.parse_args(argv)
    if args.toolchain_path:
        sys.path.insert(0, str(args.toolchain_path.resolve()))
    if args.require_machine_tools:
        try:
            lifetime_fixture.machine_tools()
        except ImportError as error:
            print(str(error), file=sys.stderr)
            return 2
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
                               for cls in (SourceTests, CPUTests))
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
        return 1
    if args.original_backed:
        original_checks(args.original_backed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
