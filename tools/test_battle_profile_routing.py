#!/usr/bin/env python3
"""Guarded synthetic routing and independent pixel oracles; no live capture.

The inherited lifecycle fixture supplies explicit allocator/constructor/thread
models only. Byte-pattern buffers below are synthetic and supply no screenshot,
native lifetime, input, healthy return or release evidence.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import importlib
from pathlib import Path
import random
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import battle_profile_lifecycle as lifecycle
from src.patcher import battle_profile_context as context
from src.patcher import partial_tile_clip as clip
from src.patcher import framed_modal_canvas as native
import test_battle_profile_lifecycle as lifetime_fixture


def routing():
    return importlib.import_module("src.patcher.battle_profile_routing")


def expected_pixels(width, height, source, before):
    """Independent destination-to-native coordinates, without emitted rows.

    Inclusive source rectangles and loop counts from the producer are never
    used. This covers each edge and both HUD slices, with the physical field
    and decorative interior retaining their input bytes.
    """
    result = bytearray(before)
    def row(y, left, right, sy, sx):
        result[y * width + left:y * width + right] = source[sy * 640 + sx:sy * 640 + sx + right - left]
    for y in range(height):
        if y < 16:
            sy = y
        elif y >= height - 16:
            sy = 464 + y - (height - 16)
        else:
            sy = 16 + (y - 16) % 448
        row(y, 0, 32, sy, 0)
    for y in (*range(16), *range(height - 16, height)):
        sy = y if y < 16 else 464 + y - (height - 16)
        for left in range(32, width - 160, 448):
            row(y, left, min(left + 448, width - 160), sy, 32)
    for y in range(368, height - 112):
        row(y, width - 16, width, 16 + (y - 368) % 352, 624)
    for y in range(368):
        row(y, width - 160, width, y, 480)
    for y in range(height - 112, height):
        row(y, width - 160, width, 368 + y - (height - 112), 480)
    return bytes(result)


class Machine(lifetime_fixture.Machine):
    def __init__(self, tools, profile="classic", resolution="1024x768", delta=0):
        self.routing_active = False
        self.physical_write_count = 0
        super().__init__(tools, profile, resolution, delta)
        module = routing()
        self.routing_emission = module._emit_code(self.plan, self.emission,
            modal_state_va=self.modal_va, assembler_module=clip)
        self.routing_entries = {name: va + delta for name, va in self.routing_emission.entries}
        code = bytearray(self.routing_emission.code)
        for item in self.routing_emission.relocations:
            if item.kind == "abs32":
                struct.pack_into("<I", code, item.offset, item.target + delta)
        self.cpu.mem_write(self.routing_emission.base_va + delta, bytes(code))

    def on_write(self, cpu, access, address, size, value, data):
        if self.routing_active and self.PHYSICAL_PIXELS <= address < self.PHYSICAL_PIXELS + self.width * self.height:
            assert address + size <= self.PHYSICAL_PIXELS + self.width * self.height, "physical pixel overflow"
            self.physical_write_count += size
        else:
            super().on_write(cpu, access, address, size, value, data)

    def on_read(self, cpu, access, address, size, value, data):
        # Avoid retaining one tuple per REP byte. The independent full-buffer
        # oracle plus read/write canaries checks all destination pixels.
        if self.routing_active:
            for start in (self.state_va - 16, self.state_va + 128,
                          self.PRIVATE - 16, self.PRIVATE + 188,
                          self.private_pixels - 16, self.private_pixels + 307200,
                          self.PHYSICAL_PIXELS - 16, self.PHYSICAL_PIXELS + self.width * self.height):
                assert address + size <= start or address >= start + 16, "routing read entered an unowned canary"
            if self.modal_va is not None:
                assert address + size <= self.modal_va + self.delta + 128 or address >= self.modal_va + self.delta + 144, "modal snapshot overread"
            for base, extent in ((self.private_pixels, 307200), (self.PHYSICAL_PIXELS, self.width * self.height)):
                if base <= address < base + extent:
                    assert address + size <= base + extent, "pixel read crossed its allocation"
                    return
        super().on_read(cpu, access, address, size, value, data)

    def prepare(self, *, bound=True):
        assert self.enter()["EAX"] == 1
        self.put(native.HOOK_OWNER + self.delta, 0x42E8B0 + self.delta)
        if bound:
            assert self.bind()["EAX"] == 1
        return self

    def pixels(self):
        return bytes(self.cpu.mem_read(self.PHYSICAL_PIXELS, self.width * self.height))

    def record(self):
        modal = None if self.modal_va is None else bytes(self.cpu.mem_read(self.modal_va + self.delta, 128))
        return (bytes(self.cpu.mem_read(self.state_va, 128)), modal,
                bytes(self.cpu.mem_read(self.PRIVATE, 188)), bytes(self.cpu.mem_read(self.PHYSICAL, 188)))

    def invoke_routing(self, name, *, flags=0xED7, expected_stop=None, ebp=0x44556677):
        self.routing_active = True
        self.stops = set() if expected_stop is None else {expected_stop + self.delta}
        self.native_stop = None
        self.writes, self.reads = [], []
        self.physical_write_count = 0
        callback_begin = len(self.callbacks)
        registers = dict(EAX=0x12345678, ECX=0x11223344, EDX=0x22334455, EBX=0x33445566,
                         ESP=self.SP, EBP=ebp, ESI=0x55667788, EDI=0x66778899)
        self.put(self.SP, self.STOP)
        for name_, value in registers.items():
            self.cpu.reg_write(self.regs[name_], value)
        self.cpu.reg_write(self.regs["EFLAGS"], flags)
        try:
            self.cpu.emu_start(self.routing_entries[name], self.STOP + 1, count=3000000)
        finally:
            self.routing_active = False
        self.routing_callbacks = self.callbacks[callback_begin:]
        actual = {key: self.cpu.reg_read(reg) for key, reg in self.regs.items()}
        expected_end = self.STOP if expected_stop is None else expected_stop + self.delta
        assert self.native_stop == expected_end, (name, actual)
        for key, value in registers.items():
            if expected_stop is not None or key not in ("EAX", "ESP"):
                assert actual[key] == value, (name, key, actual[key], value)
        if expected_stop is None:
            assert actual["ESP"] == self.SP + 4, (name, actual)
        assert actual["EFLAGS"] & self.MASK == flags & self.MASK, (name, actual)
        # Routing owns only a bounded stack and one scoped render assignment.
        for address, size in self.writes:
            assert (self.STACK <= address and address + size <= self.STACK + 0x10000
                    or address == native.RENDER + self.delta and size == 4), (name, address, size)
        for at in (self.state_va - 16, self.state_va + 128, self.PRIVATE - 16, self.PRIVATE + 188,
                   self.private_pixels - 16, self.private_pixels + 307200,
                   self.PHYSICAL_PIXELS - 16, self.PHYSICAL_PIXELS + self.width * self.height):
            assert bytes(self.cpu.mem_read(at, 16)) == b"\xD7" * 16, (name, hex(at))
        return actual


class SourceTests(unittest.TestCase):
    def test_parent_target_proof_rejects_changed_root_exception_and_target_bytes(self):
        module = routing()
        original = bytearray(0x30000)
        for va in (0x42EB6E, 0x42EF71):
            original[va - 0x400000:va - 0x400000 + 6] = bytes.fromhex("892d30125100")
        reader = SimpleNamespace(file_offset=lambda data, va, size: va - 0x400000)
        native_root = dict(start=0x42E9E0, end_exclusive=0x42F7B6,
            sha256="76d0092eb035798d0da8f1b1ed11913e7c428781784ee91c1a0337cdb19d367a")
        for profile in context.PROFILES:
            if profile == "classic":
                parent_root = dict(rule="exact_original", edits=[], candidate_root_sha256=native_root["sha256"])
            else:
                parent_root = dict(rule="one_exact_inherited_centered_present_call",
                    candidate_root_sha256="a1a51ff496653fb6e69803eaf1def9362e5c2ab70ff1a1dd3216743809827c42",
                    edits=[dict(va=0x42F2F5, old_hex="e8a61b0300", new_hex="e806c70e00")])
            contract = dict(native_spans=dict(root=native_root), inherited_native_root_contract=parent_root)
            proof = module._parent_target_contract(bytes(original), profile, contract, reader)
            self.assertEqual([row["va"] for row in proof["sites"]], [0x42EB6E, 0x42EF71])
            self.assertTrue(all(row["parent_bytes_exact_original"] is True for row in proof["sites"]))
            for change in ("span", "root_digest", "rule", "candidate_digest", "extra_edit", "target_byte"):
                bad = deepcopy(contract)
                image = bytearray(original)
                root = bad["inherited_native_root_contract"]
                if change == "span": bad["native_spans"]["root"]["end_exclusive"] += 1
                elif change == "root_digest": bad["native_spans"]["root"]["sha256"] = "0" * 64
                elif change == "rule": root["rule"] = "generic_patch_window"
                elif change == "candidate_digest": root["candidate_root_sha256"] = "0" * 64
                elif change == "extra_edit": root["edits"].append(dict(va=0x42EB6E, old_hex="892d30125100", new_hex="909090909090"))
                else: image[0x2EB6F] ^= 1
                with self.subTest(profile=profile, change=change), self.assertRaises(ValueError):
                    module._parent_target_contract(bytes(image), profile, bad, reader)

    def test_required_matrix_is_independent_of_producer_selector_changes(self):
        self.assertEqual(tuple(context.PROFILES), ("classic", "framed", "completehd", "modalwidgets"))
        self.assertEqual(tuple(context.RESOLUTIONS), ("800x600", "1024x768", "1280x720", "1280x960",
            "1366x768", "1920x1080", "2560x1440", "3440x1440", "3840x2160"))
        self.assertEqual(len(context.PROFILES) * len(context.RESOLUTIONS), 36)

    def test_production_rejects_nonoriginal_and_noncanonical_selectors(self):
        module = routing()
        for profile, resolution in (("other", "1024x768"), ("classic", "802x602"),
                                    (True, "800x600"), ("framed", "800X600")):
            with self.subTest(profile=profile, resolution=resolution), self.assertRaises(ValueError):
                module.emit_battle_profile_routing(b"", profile, resolution)
        for original in (bytearray(), memoryview(b""), b""):
            with self.subTest(type=type(original)), self.assertRaises(ValueError):
                module.emit_battle_profile_routing(original, "classic", "1024x768")

    def test_all_geometries_code_is_disjoint_and_has_relocations(self):
        module = routing()
        for profile in context.PROFILES:
            for resolution in context.RESOLUTIONS:
                with self.subTest(profile=profile, resolution=resolution):
                    plan = lifetime_fixture.synthetic_plan(profile, resolution)
                    modal = None if profile in ("classic", "framed") else plan["inherited_state_inventory"]["page_va"]
                    previous = lifecycle._emit_code(plan, modal_state_va=modal, assembler_module=clip)
                    result = module._emit_code(plan, previous, modal_state_va=modal, assembler_module=clip)
                    self.assertGreaterEqual(result.base_va, previous.base_va + len(previous.code))
                    self.assertEqual(result.base_va % 16, 0)
                    self.assertLessEqual(result.base_va + len(result.code), plan["rx"]["va"] + plan["rx"]["virtual_reservation"])
                    self.assertEqual(result.state_va, plan["rw"]["va"])
                    self.assertEqual({name for name, _ in result.entries}, {
                        "check_owned_prepared", "check_owned_bound", "target_hud", "compose_chrome",
                        "initial_frame_target", "initial_widgets_target"})
                    self.assertGreater(len(clip.absolute_relocation_offsets(result)), 0)

    def test_pins_and_mid_emission_edits_fail(self):
        module = routing()
        snapshot = module._snapshot()
        with patch.dict(module.PINNED_SOURCES, {module.LIFECYCLE: "0" * 64}):
            with self.assertRaises(ValueError):
                module._snapshot()
        read = Path.read_bytes
        def changed(path):
            result = read(path)
            return result + b"# concurrent routing edit\n" if path == ROOT / module.SOURCE else result
        with patch.object(Path, "read_bytes", changed), self.assertRaisesRegex(ValueError, "changed during"):
            module._unchanged(snapshot)


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.tools = lifetime_fixture.machine_tools()
        except ImportError as error:
            raise unittest.SkipTest(str(error))

    def test_all_36_cells_two_bases_exact_chrome_and_inert_pixels(self):
        # Seeded nonperiodic bytes distinguish native rows 464 and 208, as
        # well as adjacent columns and corner slices. Linear modulo patterns
        # alone repeat every 256 rows and can hide an incorrect source row.
        source = random.Random(0xB4771E).randbytes(640 * 480)
        for profile in context.PROFILES:
            for resolution in context.RESOLUTIONS:
                for delta in (0, 0x2000000):
                    with self.subTest(profile=profile, resolution=resolution, delta=delta):
                        m = Machine(self.tools, profile, resolution, delta).prepare()
                        m.cpu.mem_write(m.private_pixels, source)
                        before, record = m.pixels(), m.record()
                        expected = expected_pixels(m.width, m.height, source, before)
                        self.assertEqual(m.invoke_routing("check_owned_bound")["EAX"], 1)
                        self.assertEqual(m.invoke_routing("compose_chrome")["EAX"], 1)
                        self.assertEqual(m.routing_callbacks, ["thread"])
                        self.assertGreater(m.physical_write_count, 0)
                        self.assertEqual(m.pixels(), expected)
                        self.assertEqual(m.record(), record)
                        self.assertEqual(m.word(native.RENDER + delta), m.PHYSICAL)
                        # A repeated composition may refresh the chrome only;
                        # an independent field marker must survive exactly.
                        for y in (16, 200, 463):
                            m.cpu.mem_write(m.PHYSICAL_PIXELS + y * m.width + 32, b"\xEE" * 64)
                        updated = m.pixels()
                        self.assertEqual(m.invoke_routing("compose_chrome", flags=0x202)["EAX"], 1)
                        self.assertEqual(m.pixels(), expected_pixels(m.width, m.height, source, updated))
                        self.assertEqual(m.record(), record)

    def test_prepared_and_bound_target_hooks_replay_and_preserve_abi(self):
        for profile in context.PROFILES:
            for bound in (False, True):
                for flags in (0x202, 0xED7):
                    with self.subTest(profile=profile, bound=bound, flags=flags):
                        m = Machine(self.tools, profile, "1366x768", 0x2000000).prepare(bound=bound)
                        for name, continuation in (("initial_frame_target", 0x42EB74), ("initial_widgets_target", 0x42EF77)):
                            before, record = m.pixels(), m.record()
                            m.invoke_routing(name, flags=flags, expected_stop=continuation, ebp=native.PRIMARY + m.delta)
                            self.assertEqual(m.word(native.RENDER + m.delta), m.PRIVATE)
                            self.assertEqual(m.pixels(), before)
                            self.assertEqual(m.record(), record)
                        m.put(native.RENDER + m.delta, m.PHYSICAL)
                        self.assertEqual(m.invoke_routing("target_hud", flags=flags)["EAX"], 1)
                        self.assertEqual(m.word(native.RENDER + m.delta), m.PRIVATE)
                        if not bound:
                            before = m.pixels()
                            self.assertEqual(m.invoke_routing("check_owned_bound")["EAX"], 0)
                            self.assertEqual(m.invoke_routing("compose_chrome")["EAX"], 0)
                            self.assertEqual(m.physical_write_count, 0)
                            self.assertEqual(m.pixels(), before)

    def test_rejected_target_hook_replays_original_mov_ebp(self):
        for profile in context.PROFILES:
            m = Machine(self.tools, profile).prepare()
            m.thread_id += 1
            m.put(native.RENDER, m.PHYSICAL)
            record, before = m.record(), m.pixels()
            for name, continuation in (("initial_frame_target", 0x42EB74), ("initial_widgets_target", 0x42EF77)):
                m.invoke_routing(name, expected_stop=continuation, ebp=0x44556677)
                self.assertEqual(m.word(native.RENDER), 0x44556677)
                self.assertEqual(m.record(), record)
                self.assertEqual(m.pixels(), before)

    def test_state_global_header_and_world_rejections_write_no_pixels(self):
        cases = (
            ("state", "phase", 0), ("state", "phase", 3), ("state", "fault", 1),
            ("state", "enter_status", 0), ("state", "leave_status", 1),
            ("state", "return_status", 1), ("state", "abort_reason", 1),
            ("state", "allocations", 0), ("state", "frees", 1),
            ("state", "pending_header", lifetime_fixture.Machine.PRIVATE),
            ("state", "pending_pixels", lifetime_fixture.Machine.PRIVATE),
            ("state", "physical", lifetime_fixture.Machine.PRIVATE),
            ("state", "native", lifetime_fixture.Machine.PHYSICAL),
            ("state", "native_pixels", lifetime_fixture.Machine.PHYSICAL_PIXELS),
            ("state", "physical_pixels", lifetime_fixture.Machine.PRIVATE),
            ("state", "battle", 0), ("state", "saved_owner", 0x42E8B0),
            ("state", "saved_render", lifetime_fixture.Machine.PRIVATE),
            ("state", "owner_tid", 124), ("state", "saved_backend", 0),
            ("global", native.MAP, lifetime_fixture.Machine.PRIVATE),
            ("global", native.RENDER, 0x44556677), ("global", native.HOOK_OWNER, 0x40AD40),
            ("global", 0x532048, 0), ("global", clip.LOWER_ROW_OWNER_GLOBAL, 1),
            ("global", clip.POST_TILE_CALLBACK_GLOBAL, 1),
            ("physical", 0, 640 | (480 << 16)), ("physical", 4, lifetime_fixture.Machine.PRIVATE),
            ("physical", 0xB8, 0), ("private", 0, 800 | (600 << 16)),
            ("private", 4, lifetime_fixture.Machine.PHYSICAL_PIXELS), ("private", 0xAC, 1),
            ("private", 0xB8, 0), ("world", 800, 6), ("world", 804, 0),
            ("world", 804, 21), ("world", 808, 100), ("world", 812, 1),
            ("primary", 0xD4, 16), ("primary", 0xBC, 0),
        )
        for kind, field, value in cases:
            with self.subTest(kind=kind, field=field):
                m = Machine(self.tools, "modalwidgets").prepare()
                if kind == "state":
                    m.set_state(field, value)
                else:
                    base = {"global": 0, "physical": m.PHYSICAL, "private": m.PRIVATE,
                            "world": m.WORLD, "primary": native.PRIMARY}[kind]
                    m.put(base + field, value)
                record, before = m.record(), m.pixels()
                self.assertEqual(m.invoke_routing("check_owned_bound")["EAX"], 0)
                self.assertEqual(m.invoke_routing("compose_chrome")["EAX"], 0)
                self.assertEqual(m.physical_write_count, 0)
                self.assertEqual(m.pixels(), before)
                self.assertEqual(m.record(), record)

    def test_every_modal_live_field_and_unbalanced_history_rejects(self):
        for field in lifetime_fixture.Machine.MODAL_LIVE:
            m = Machine(self.tools, "completehd").prepare()
            m.put(m.modal_va + native.STATE[field], 1)
            before, record = m.pixels(), m.record()
            self.assertEqual(m.invoke_routing("compose_chrome")["EAX"], 0)
            self.assertEqual(m.pixels(), before)
            self.assertEqual(m.record(), record)
        for field in ("allocations", "frees", "mirrors", "enter_status", "mirror_status", "leave_status"):
            m = Machine(self.tools, "modalwidgets").prepare()
            m.put(m.modal_va + native.STATE[field], 1)
            before, record = m.pixels(), m.record()
            self.assertEqual(m.invoke_routing("compose_chrome")["EAX"], 0)
            self.assertEqual(m.pixels(), before)
            self.assertEqual(m.record(), record)

    def test_thread_callback_changes_state_globals_headers_or_history_never_copy(self):
        def balanced_modal_history(m):
            m.put(m.modal_va + native.STATE["allocations"], 1)
            m.put(m.modal_va + native.STATE["frees"], 1)
        def paired_private_pixels(m):
            m.set_state("native_pixels", m.PHYSICAL_PIXELS)
            m.put(m.PRIVATE + 4, m.PHYSICAL_PIXELS)
        def paired_physical_pixels(m):
            m.set_state("physical_pixels", m.private_pixels)
            m.put(m.PHYSICAL + 4, m.private_pixels)
        def paired_world_owner(m):
            m.set_state("battle", m.PHYSICAL)
            m.put(0x532048, m.PHYSICAL)
        changes = (
            lambda m: m.set_state("owner_tid", m.thread_id + 1),
            lambda m: m.set_state("native_pixels", m.PHYSICAL_PIXELS),
            lambda m: m.set_state("allocations", m.state("allocations") + 1),
            lambda m: m.put(native.RENDER, native.PRIMARY),
            lambda m: m.put(native.PRIMARY + 0xBC, m.BACKEND + 4),
            lambda m: m.put(m.PHYSICAL + 4, m.private_pixels),
            lambda m: m.put(m.PRIVATE + 4, m.PHYSICAL_PIXELS),
            lambda m: m.put(m.WORLD + 804, 19),
            lambda m: m.put(m.modal_va + native.STATE["mirrors"], 1),
            lambda m: m.put(m.modal_va + native.STATE["enter_status"], 1),
            lambda m: m.put(m.state_va + 120, 1),
            lambda m: m.put(m.modal_va + 120, 1),
            balanced_modal_history, paired_private_pixels, paired_physical_pixels, paired_world_owner,
        )
        for i, change in enumerate(changes):
            with self.subTest(change=i):
                m = Machine(self.tools, "modalwidgets").prepare()
                before = m.pixels()
                hits = []
                def mutate(machine, name):
                    if name == "thread":
                        hits.append(name)
                        change(machine)
                m.mutation = mutate
                self.assertEqual(m.invoke_routing("compose_chrome")["EAX"], 0)
                self.assertEqual(m.physical_write_count, 0)
                self.assertEqual(m.pixels(), before)
                self.assertEqual(m.frees, [])
                self.assertEqual(m.destructions, [])
                self.assertEqual(m.routing_callbacks, ["thread"])
                self.assertEqual(hits, ["thread"])

    def test_thread_volatile_clobbers_and_small_arenas_preserve_abi(self):
        for columns in (1, 2, 7, 9, 13, 20):
            for resolution in ("800x600", "1366x768", "3440x1440", "3840x2160"):
                with self.subTest(columns=columns, resolution=resolution):
                    m = Machine(self.tools, "framed", resolution).prepare()
                    m.put(m.WORLD + 804, columns)
                    m.put(m.WORLD + 808, max(0, columns - (m.width - 192) // 64))
                    m.thread_clobbers = True
                    record = m.record()
                    self.assertEqual(m.invoke_routing("check_owned_bound")["EAX"], 1)
                    self.assertEqual(m.invoke_routing("target_hud")["EAX"], 1)
                    self.assertEqual(m.word(native.RENDER), m.PRIVATE)
                    self.assertEqual(m.record(), record)
                    self.assertTrue(all(flags & 0x400 == 0 for flags in m.callback_flags))

    def test_full_fresh_rw_page_excludes_coherently_forged_heap_objects(self):
        for profile in ("classic", "framed"):
            for role in ("physical", "backend", "world"):
                with self.subTest(profile=profile, role=role):
                    m = Machine(self.tools, profile).prepare()
                    forged = m.state_va + 512
                    if role == "physical":
                        m.cpu.mem_write(forged, bytes(m.cpu.mem_read(m.PHYSICAL, 188)))
                        m.set_state("physical", forged)
                        m.set_state("saved_render", forged)
                        m.put(native.MAP, forged)
                        m.put(native.RENDER, forged)
                    elif role == "backend":
                        m.cpu.mem_write(forged, bytes(m.cpu.mem_read(m.BACKEND, 168)))
                        m.set_state("saved_backend", forged)
                        m.put(native.PRIMARY + 0xBC, forged)
                    else:
                        m.cpu.mem_write(forged, bytes(m.cpu.mem_read(m.WORLD, 816)))
                        m.set_state("battle", forged)
                        m.put(0x532048, forged)
                    record, before = m.record(), m.pixels()
                    self.assertEqual(m.invoke_routing("compose_chrome")["EAX"], 0)
                    self.assertEqual(m.routing_callbacks, [])
                    self.assertEqual(m.physical_write_count, 0)
                    self.assertEqual(m.pixels(), before)
                    self.assertEqual(m.record(), record)

    def test_single_column_arena_composition_keeps_all_interior_pixels(self):
        m = Machine(self.tools, "modalwidgets", "1366x768").prepare()
        m.put(m.WORLD + 804, 1)
        m.put(m.WORLD + 808, 0)
        source = random.Random(0x51DEBA7).randbytes(640 * 480)
        m.cpu.mem_write(m.private_pixels, source)
        before = m.pixels()
        self.assertEqual(m.invoke_routing("compose_chrome")["EAX"], 1)
        self.assertEqual(m.pixels(), expected_pixels(m.width, m.height, source, before))
        self.assertEqual(m.routing_callbacks, ["thread"])

    def test_changed_authority_rejects_before_rereading_retired_heap(self):
        for pointer, value, heap_name in ((native.MAP, lifetime_fixture.Machine.PRIVATE, "PHYSICAL"),
                                         (native.HOOK_OWNER, 0x40AD40, "PRIVATE"),
                                         (0x532048, 0, "WORLD")):
            with self.subTest(global_pointer=hex(pointer), poisoned=heap_name):
                m = Machine(self.tools, "modalwidgets").prepare()
                before = m.pixels()
                hits = []
                def mutate(machine, name):
                    if name == "thread":
                        hits.append(name)
                        machine.put(pointer, value)
                        machine.cpu.mem_protect(getattr(machine, heap_name), 4096, machine.u.UC_PROT_NONE)
                m.mutation = mutate
                # Unicorn page protection catches cached pointer reads even
                # when they would not modify any canary or destination byte.
                self.assertEqual(m.invoke_routing("compose_chrome")["EAX"], 0)
                self.assertEqual(m.pixels(), before)
                self.assertEqual(m.physical_write_count, 0)
                self.assertEqual(hits, ["thread"])
                self.assertEqual(m.routing_callbacks, ["thread"])


def original_checks(path):
    module = routing()
    original = path.read_bytes()
    for profile, resolution in (("classic", "1024x768"), ("classic", "1366x768"),
                                ("framed", "1366x768"), ("completehd", "1366x768"),
                                ("modalwidgets", "1366x768")):
        bundle = module.emit_battle_profile_routing(original, profile, resolution)
        metadata = bundle.metadata()
        assert metadata["installed"] is False and metadata["emission_preparation_only"] is True
        assert all(metadata[name] is False for name in context.FALSE_CLAIMS)
        assert len(bundle.hook_sites) == 2
        assert set(bundle.removed_highlow_rvas) == {0x2EB70, 0x2EF73}
        entries = dict(bundle.emission.entries)
        for name, hook in zip(("initial_frame_target", "initial_widgets_target"), bundle.hook_sites):
            va = 0x42EB6E if name == "initial_frame_target" else 0x42EF71
            assert (hook.va, hook.rva, hook.offset) == (va, va - 0x400000, clip.file_offset(original, va, 6))
            assert hook.old == bytes.fromhex("892d30125100")
            assert hook.new[0] == 0xE9 and hook.new[-1] == 0x90
            assert len(hook.new) == len(hook.old) == 6
            assert va + 5 + struct.unpack_from("<i", hook.new, 1)[0] == entries[name]
            assert len(hook.relocations) == 1
            relocation = hook.relocations[0]
            assert (relocation.offset, relocation.kind, relocation.target) == (1, "rel32", entries[name])
        with patch.object(context, "build_parent_context", side_effect=AssertionError("public context")), \
                patch.object(lifecycle, "emit_battle_profile_lifecycle", side_effect=AssertionError("public lifecycle")), \
                patch.object(clip, "_Assembler", side_effect=AssertionError("public assembler")), \
                patch.object(module, "_emit_code", side_effect=AssertionError("public routing")):
            replay = module.emit_battle_profile_routing(original, profile, resolution)
        assert replay.emission.code == bundle.emission.code and replay.metadata() == metadata
        assert path.read_bytes() == original
        print("ORIGINAL_MEMORY_ROUTING_PASS", profile, resolution, "native_execution=false")


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
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(
        unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in (SourceTests, CPUTests)))
    if not result.wasSuccessful():
        return 1
    if args.original_backed:
        original_checks(args.original_backed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
