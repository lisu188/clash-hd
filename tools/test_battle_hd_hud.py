"""Repo-only HUD integrity and isolated x86 helper fixtures; never launches Clash.

Supply optional development tools with --toolchain-path. Use --source-exe for
read-only byte and native-routine checks and --require-machine-tools to fail
when Keystone or Unicorn is unavailable. No local installation is discovered.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "patcher"))
import battle_hd_hud as hud
from battle_hd_layout import BATTLE_LAYOUT

SOURCE_EXE: Path | None = None


class HudIntegrityTests(unittest.TestCase):
    def test_patch_records_are_exact_nonoverlapping_and_auditable(self):
        previous_end = 0
        groups = set()
        for group, offset, old, new, note in sorted(hud.build_patches(), key=lambda p: p[1]):
            self.assertGreaterEqual(offset, previous_end)
            self.assertEqual(len(bytes.fromhex(old)), len(bytes.fromhex(new)))
            self.assertIn("VA 0x", note)
            self.assertIn("RVA 0x", note)
            previous_end = offset + len(bytes.fromhex(old))
            groups.add(group)
        self.assertEqual(groups, set(hud.HUD_GROUPS))
        self.assertLess(hud.HUD_CODE_VA + len(hud.HUD_CODE), hud.HUD_CODE_LIMIT)

    def test_frame_never_copies_native_pixels_into_battlefield(self):
        coverage = set()
        for sx, sy, width, height, dx, dy in hud.FRAME_BLITS:
            self.assertTrue(0 <= sx < sx + width <= 640)
            self.assertTrue(0 <= sy < sy + height <= 480)
            for y in range(dy, dy + height):
                for x in range(dx, dx + width):
                    self.assertFalse(32 <= x < 1120 and 136 <= y < 584)
                    self.assertNotIn((x, y), coverage)
                    coverage.add((x, y))
        expected = {(x, y) for y in range(120, 600) for x in range(1280)
                    if not (32 <= x < 1120 and 136 <= y < 584)}
        self.assertEqual(coverage, expected)

    def test_descriptors_shift_only_coordinates(self):
        native = [(498, 370), (561, 370), (498, 401), (498, 432), (561, 401), (505, 0)]
        by_offset = {p[1]: p for p in hud.build_patches()}
        for index, (x, y) in enumerate(native):
            record = by_offset[0x514B78 + index * 53 - 0x401E00]
            self.assertEqual(bytes.fromhex(record[2]), struct.pack("<ii", x, y))
            self.assertEqual(bytes.fromhex(record[3]), struct.pack("<ii", x + 640, y + 120))

    def test_layout_is_deliberately_fixed_to_audited_geometry(self):
        self.assertEqual(BATTLE_LAYOUT.sidebar_offset, (640, 120))
        self.assertEqual(BATTLE_LAYOUT.battlefield, (32, 136, 1120, 584))
        self.assertNotIn("battle-ui-center-present-wrapper", hud.HUD_GROUPS)

    def test_explicit_source_hash_and_every_old_byte(self):
        if SOURCE_EXE is None:
            self.skipTest("no --source-exe supplied")
        data = SOURCE_EXE.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), hud.HUD_SOURCE_SHA256)
        for group, offset, old, _, note in hud.build_patches():
            expected = bytes.fromhex(old)
            self.assertEqual(data[offset:offset + len(expected)], expected, note)

    def test_assembly_reproduces_each_helper_when_assembler_available(self):
        if not importlib.util.find_spec("keystone"):
            self.skipTest("optional Keystone assembler is not installed")
        from keystone import Ks, KS_ARCH_X86, KS_MODE_32
        assembler = Ks(KS_ARCH_X86, KS_MODE_32)
        for name, va, assembly, encoded in hud.HUD_CODE_FRAGMENTS:
            self.assertEqual(bytes(assembler.asm(assembly, addr=va)[0]), bytes.fromhex(encoded), name)


class HudMachineTests(unittest.TestCase):
    def setUp(self):
        if not importlib.util.find_spec("unicorn"):
            self.skipTest("optional Unicorn x86 emulator is not installed")

    def native_machine(self, start, end):
        """Load only the explicitly supplied, hash-checked native routine slice."""
        if SOURCE_EXE is None:
            self.skipTest("no --source-exe supplied")
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
        from unicorn import x86_const as r
        data = SOURCE_EXE.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), hud.HUD_SOURCE_SHA256)
        emu = Uc(UC_ARCH_X86, UC_MODE_32)
        emu.mem_map(0x400000, 0x200000)
        emu.mem_map(0x600000, 0x10000)
        emu.mem_map(0x700000, 0x10000)
        emu.mem_write(start, data[start - 0x400C00:end - 0x400C00])
        emu.mem_write(hud.HUD_CODE_VA, hud.HUD_CODE)
        for _, offset, old, replacement, _ in hud.build_patches():
            va = offset + 0x400C00
            if start <= va < end:
                self.assertEqual(data[offset:offset + len(bytes.fromhex(old))], bytes.fromhex(old))
                emu.mem_write(va, bytes.fromhex(replacement))
        emu.reg_write(r.UC_X86_REG_ESP, 0x708000)
        return emu, data

    def test_native_modals_share_geometry_for_art_hitboxes_and_background_restore(self):
        from unicorn import UC_HOOK_CODE
        from unicorn import x86_const as r
        stack, scratch, default_surface, vtable, sprite = 0x708000, 0x600000, 0x51D4C0, 0x601000, 0x602000
        variants = (
            (0x42D7C9, 0x42D8F3, 0x42D9F1, 0x42DA2E, 0x42DA32, 0x42DA46,
             0xC, 0x34, 0x28, 0x20, 0x1C),
            (0x42DB2A, 0x42DCEB, 0x42DE07, 0x42DE56, 0x42DE5A, 0x42DE6E,
             0xAC, 0xBC, 0xC0, 0xB4, 0xC4),
        )
        for variant in variants:
            begin, drawn, restore, restored, cursor_begin, cursor_end, library_local, lx, ty, rx, by = variant
            for width, height in ((336, 152), (335, 151), (448, 320)):
                with self.subTest(modal=hex(begin), dimensions=(width, height)):
                    emu, source = self.native_machine(0x42D7C9, 0x42DEB3)
                    def put(address, value):
                        emu.mem_write(address, struct.pack("<I", value))
                    def get(address):
                        return struct.unpack("<I", emu.mem_read(address, 4))[0]
                    put(stack + library_local, 0x604000)
                    put(0x511230, 0x605000)
                    put(default_surface + 184, vtable)
                    put(vtable + 52, sprite)
                    emu.reg_write(r.UC_X86_REG_ECX, default_surface)
                    descriptor_source = source[0x514CF8 - 0x401E00:0x514CF8 - 0x401E00 + 159]
                    emu.mem_write(0x514CF8, descriptor_source)
                    calls = []
                    def ret(extra=0, result=None):
                        sp = emu.reg_read(r.UC_X86_REG_ESP)
                        ip = get(sp)
                        if result is not None:
                            emu.reg_write(r.UC_X86_REG_EAX, result)
                        emu.reg_write(r.UC_X86_REG_ESP, sp + 4 + extra)
                        emu.reg_write(r.UC_X86_REG_EIP, ip)
                    def hook(_emu, address, _size, _user):
                        eax, ebx, ecx, edx = (emu.reg_read(reg) for reg in
                            (r.UC_X86_REG_EAX, r.UC_X86_REG_EBX, r.UC_X86_REG_ECX, r.UC_X86_REG_EDX))
                        if address in (0x405EF0, 0x405EE0):
                            ret(result=width if address == 0x405EF0 else height)
                        elif address == 0x461C00:
                            self.assertEqual(eax, 188)
                            ret(result=scratch)
                        elif address == 0x403D70:
                            self.assertEqual((edx, ebx), (width, height))
                            ret(result=scratch)
                        elif address == 0x4024E0:
                            sp = emu.reg_read(r.UC_X86_REG_ESP)
                            calls.append(("copy", eax, edx, ebx, ecx, *struct.unpack("<4I", emu.mem_read(sp + 4, 16))))
                            ret(16)
                        elif address == 0x405EC0:
                            ret(result=0x606000)
                        elif address == sprite:
                            calls.append(("sprite", eax, ebx, ecx))
                            ret(28)
                        elif address == 0x460AF0:
                            calls.append(("cursor", edx, ebx))
                            ret()
                    emu.hook_add(UC_HOOK_CODE, hook)
                    emu.emu_start(begin, drawn, count=5000)
                    self.assertEqual(emu.reg_read(r.UC_X86_REG_EIP), drawn)
                    self.assertEqual(emu.reg_read(r.UC_X86_REG_ESP), stack)
                    left, top = 32 + (1088 - width) // 2, (720 - height) // 2
                    right, bottom = left + width - 1, top + height - 1
                    self.assertEqual(tuple(get(stack + offset) for offset in (lx, ty, rx, by)),
                                     (left, top, right, bottom))
                    self.assertEqual(calls, [("copy", 0, scratch, left, top, right, bottom, 0, 0),
                                             ("sprite", default_surface, left, top)])
                    if begin == 0x42DB2A:
                        self.assertEqual((get(stack), get(stack + 4)), (left + 232, top + 108))
                        self.assertEqual((get(stack + 53), get(stack + 57)), (left + 27, top + 108))
                        for offset in (0, 53):
                            self.assertEqual(emu.mem_read(stack + offset + 16, 37),
                                             descriptor_source[offset + 16:offset + 53])
                    emu.emu_start(restore, restored, count=5000)
                    self.assertEqual(calls[-1], ("copy", scratch, 0, 0, 0, width - 1, height - 1, left, top))
                    self.assertEqual(emu.reg_read(r.UC_X86_REG_ESP), stack)
                    emu.emu_start(cursor_begin, cursor_end, count=5000)
                    self.assertEqual(calls[-1], ("cursor", 576, 360))

    def test_native_morale_animation_uses_sidebar_coordinates(self):
        from unicorn import UC_HOOK_CODE
        from unicorn import x86_const as r
        for morale in (0, 50, 99, 100):
            emu, _ = self.native_machine(0x430E90, 0x430F7B)
            def put(address, value):
                emu.mem_write(address, struct.pack("<I", value))
            def get(address):
                return struct.unpack("<I", emu.mem_read(address, 4))[0]
            stack, stop, scratch, device = 0x708000, 0x56D000, 0x600000, 0x605000
            put(stack, stop)
            put(0x53210C, morale)
            put(0x511230, device)
            put(scratch + 184, 0x601000)
            put(0x601000, 0x602100)
            put(0x601000 + 52, 0x602000)
            calls = []
            def ret(extra=0, result=None):
                sp = emu.reg_read(r.UC_X86_REG_ESP)
                ip = get(sp)
                if result is not None:
                    emu.reg_write(r.UC_X86_REG_EAX, result)
                emu.reg_write(r.UC_X86_REG_ESP, sp + 4 + extra)
                emu.reg_write(r.UC_X86_REG_EIP, ip)
            def hook(_emu, address, _size, _user):
                eax, ebx, ecx, edx = (emu.reg_read(reg) for reg in
                    (r.UC_X86_REG_EAX, r.UC_X86_REG_EBX, r.UC_X86_REG_ECX, r.UC_X86_REG_EDX))
                if address == 0x461C00:
                    self.assertEqual(eax, 188)
                    ret(result=scratch)
                elif address in (0x405EF0, 0x405EE0):
                    ret(result=87 if address == 0x405EF0 else 55)
                elif address == 0x403D70:
                    self.assertEqual((edx, ebx), (88, 56))
                    ret(result=scratch)
                elif address == 0x405EC0:
                    ret(result=0x606000)
                elif address == 0x602000:
                    ret(28)
                elif address == 0x602100:
                    calls.append(("free", eax, edx))
                    ret()
                elif address == 0x4024E0:
                    sp = emu.reg_read(r.UC_X86_REG_ESP)
                    calls.append(("copy", eax, edx, ebx, ecx, *struct.unpack("<4I", emu.mem_read(sp + 4, 16))))
                    ret(16)
            emu.hook_add(UC_HOOK_CODE, hook)
            emu.emu_start(0x430E90, stop, count=5000)
            self.assertEqual(emu.reg_read(r.UC_X86_REG_EIP), stop)
            self.assertEqual(emu.reg_read(r.UC_X86_REG_ESP), stack + 4)
            self.assertEqual(get(0x511230), device)
            expected = [] if morale >= 100 else [
                ("copy", scratch, device, 0, 0, (100 - morale) * 88 // 100, 56, 1174, 146),
                ("free", scratch, 2)]
            self.assertEqual(calls, expected, morale)

    def test_native_stats_present_stops_above_command_controls(self):
        from unicorn import UC_HOOK_CODE
        from unicorn import x86_const as r
        for present in (0, 1):
            emu, _ = self.native_machine(0x4317CC, 0x43181E)
            stack, scene = 0x708000, 0x604000
            emu.mem_write(stack + 0x70, struct.pack("<I", present))
            emu.mem_write(0x5202E0, struct.pack("<I", scene))
            copies = []
            def ret(extra=0):
                sp = emu.reg_read(r.UC_X86_REG_ESP)
                ip = struct.unpack("<I", emu.mem_read(sp, 4))[0]
                emu.reg_write(r.UC_X86_REG_ESP, sp + 4 + extra)
                emu.reg_write(r.UC_X86_REG_EIP, ip)
            def hook(_emu, address, _size, _user):
                if address == 0x405920:
                    ret()
                elif address == 0x460BB0:
                    ret(4)
                elif address == 0x4024E0:
                    sp = emu.reg_read(r.UC_X86_REG_ESP)
                    copies.append(tuple(emu.reg_read(reg) for reg in
                        (r.UC_X86_REG_EAX, r.UC_X86_REG_EDX, r.UC_X86_REG_EBX, r.UC_X86_REG_ECX))
                        + struct.unpack("<4I", emu.mem_read(sp + 4, 16)))
                    ret(16)
            emu.hook_add(UC_HOOK_CODE, hook)
            emu.emu_start(0x4317CC, 0x43181E, count=1000)
            self.assertEqual(emu.reg_read(r.UC_X86_REG_EIP), 0x43181E)
            self.assertEqual(emu.reg_read(r.UC_X86_REG_ESP), stack)
            self.assertEqual(copies, [(scene, 0, 1138, 130, 1264, 474, 1138, 130)] if present else [])

    def test_shared_results_art_text_and_restore_center_only_in_battle_scope(self):
        from unicorn import UC_HOOK_CODE
        from unicorn import x86_const as r
        stack, scratch, screen, vtable, sprite = 0x708000, 0x600000, 0x51D4C0, 0x601000, 0x602000
        for active in (0, 1):
            for first_height, second_height in ((180, 160), (179, 160), (160, 180)):
                emu, _ = self.native_machine(0x44546A, 0x4458D1)
                def put(address, value):
                    emu.mem_write(address, struct.pack("<I", value))
                def get(address):
                    return struct.unpack("<I", emu.mem_read(address, 4))[0]
                put(0x566800, active)
                put(screen + 184, vtable)
                put(vtable + 52, sprite)
                put(stack + 8, 0x606000)
                emu.reg_write(r.UC_X86_REG_EAX, 0x604000)
                height = max(first_height, second_height + 6)
                calls = []
                def ret(extra=0, result=None):
                    sp = emu.reg_read(r.UC_X86_REG_ESP)
                    ip = get(sp)
                    if result is not None:
                        emu.reg_write(r.UC_X86_REG_EAX, result)
                    emu.reg_write(r.UC_X86_REG_ESP, sp + 4 + extra)
                    emu.reg_write(r.UC_X86_REG_EIP, ip)
                def hook(_emu, address, _size, _user):
                    eax, ebx, ecx, edx = (emu.reg_read(reg) for reg in
                        (r.UC_X86_REG_EAX, r.UC_X86_REG_EBX, r.UC_X86_REG_ECX, r.UC_X86_REG_EDX))
                    if address == 0x405EE0:
                        ret(result=first_height if edx == 22 else second_height)
                    elif address == 0x405EF0:
                        ret(result=335)
                    elif address == 0x461C00:
                        self.assertEqual(eax, 188)
                        ret(result=scratch)
                    elif address == 0x403D70:
                        self.assertEqual((edx, ebx), (640, height))
                        ret(result=scratch)
                    elif address == 0x4024E0:
                        sp = emu.reg_read(r.UC_X86_REG_ESP)
                        calls.append(("copy", eax, edx, ebx, ecx, *struct.unpack("<4I", emu.mem_read(sp + 4, 16))))
                        ret(16)
                    elif address == 0x405EC0:
                        ret(result=0x607000 + edx)
                    elif address == sprite:
                        calls.append(("sprite", eax, edx, ebx, ecx))
                        ret(28)
                    elif address == 0x40C150:
                        sp = emu.reg_read(r.UC_X86_REG_ESP)
                        calls.append(("text", *struct.unpack("<5I", emu.mem_read(sp + 4, 20))))
                        ret()
                emu.hook_add(UC_HOOK_CODE, hook)
                emu.emu_start(0x44546A, 0x4453F9, count=5000)
                self.assertEqual(emu.reg_read(r.UC_X86_REG_EIP), 0x4453F9)
                self.assertEqual(emu.reg_read(r.UC_X86_REG_ESP), stack)
                left, top = (256, (720 - height) // 2) if active else (0, 150)
                self.assertEqual(calls, [
                    ("copy", 0, scratch, left, top, left + 639, top + height - 1, 0, 0),
                    ("sprite", screen, 0x607000 + 22, left, top),
                    ("sprite", screen, 0x607000 + 23, left + 335, top + 6),
                    ("text", left + 70, left + 569, top + 60, 6, 0x606000),
                ], (active, first_height, second_height))
                emu.emu_start(0x44586E, 0x44589F, count=5000)
                self.assertEqual(calls[-1], ("copy", scratch, 0, 0, 0, 639, height - 1, left, top))
                self.assertEqual(emu.reg_read(r.UC_X86_REG_ESP), stack)

    def test_results_scope_keeps_native_return_and_preserves_bypass_teardown(self):
        from unicorn import UC_HOOK_CODE
        from unicorn import x86_const as r
        for called in (False, True):
            emu, _ = self.native_machine(0x42F4DC, 0x42F4E6)
            def put(address, value):
                emu.mem_write(address, struct.pack("<I", value))
            def get(address):
                return struct.unpack("<I", emu.mem_read(address, 4))[0]
            stack, device = 0x708000, 0x605000
            put(0x511230, device)
            regs = (r.UC_X86_REG_EAX, r.UC_X86_REG_EBX, r.UC_X86_REG_ECX,
                    r.UC_X86_REG_EDX, r.UC_X86_REG_ESI, r.UC_X86_REG_EDI, r.UC_X86_REG_EBP)
            values = [0x606000, 0x2222, 0x3333, 0, 0x5555, 0x6666, 0x7777]
            for reg, value in zip(regs, values):
                emu.reg_write(reg, value)
            flags = 0x2D7
            emu.reg_write(r.UC_X86_REG_EFLAGS, flags)
            if called:
                emu.emu_start(0x42F4DC, 0x445360, count=1000)
                self.assertEqual(emu.reg_read(r.UC_X86_REG_EIP), 0x445360)
                self.assertEqual(emu.reg_read(r.UC_X86_REG_ESP), stack - 4)
                self.assertEqual(get(stack - 4), 0x42F4E1)
                self.assertEqual([emu.reg_read(reg) for reg in regs], values)
                self.assertEqual(emu.reg_read(r.UC_X86_REG_EFLAGS), flags)
                self.assertEqual((get(0x566800), get(0x566804)), (1, device))
                # Model the native message returning after changing its render device.
                put(0x511230, 0x51D4C0)
                emu.reg_write(r.UC_X86_REG_ESP, stack)
            calls = []
            def hook(_emu, address, _size, _user):
                if address == 0x460AF0:
                    calls.append((emu.reg_read(r.UC_X86_REG_EDX), emu.reg_read(r.UC_X86_REG_EBX)))
                    sp = emu.reg_read(r.UC_X86_REG_ESP)
                    ip = get(sp)
                    for reg in regs:
                        emu.reg_write(reg, 0xBAD)
                    emu.reg_write(r.UC_X86_REG_EFLAGS, 0x202)
                    emu.reg_write(r.UC_X86_REG_ESP, sp + 4)
                    emu.reg_write(r.UC_X86_REG_EIP, ip)
            emu.hook_add(UC_HOOK_CODE, hook)
            emu.emu_start(0x42F4E1, 0x42F4E6, count=1000)
            self.assertEqual(emu.reg_read(r.UC_X86_REG_EIP), 0x42F4E6)
            self.assertEqual(emu.reg_read(r.UC_X86_REG_ESP), stack)
            self.assertEqual([emu.reg_read(reg) for reg in regs], [0x544CD8, *values[1:]])
            self.assertEqual(emu.reg_read(r.UC_X86_REG_EFLAGS), flags)
            self.assertEqual(get(0x511230), device)
            self.assertEqual(get(0x566800), 0)
            self.assertEqual(calls, [(576, 360)] if called else [])

    def execute(self, fragment_name, fail_allocation=False, scene_surface=0x604000):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
        from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
            UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP,
            UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EFLAGS)
        emu = Uc(UC_ARCH_X86, UC_MODE_32)
        emu.mem_map(0x400000, 0x200000)
        emu.mem_map(0x600000, 0x10000)
        emu.mem_map(0x700000, 0x10000)
        emu.mem_write(hud.HUD_CODE_VA, hud.HUD_CODE)
        emu.mem_write(0x5202E0, struct.pack("<I", scene_surface))
        device_before = 0x605000
        emu.mem_write(0x511230, struct.pack("<I", device_before))
        emu.mem_write(0x600000 + 184, struct.pack("<I", 0x601000))
        emu.mem_write(0x601000, struct.pack("<I", 0x603100))
        emu.mem_write(0x601000 + 52, struct.pack("<I", 0x603000))
        stop = {"frame entry 0x42e8c4": 0x42E9A0,
                "frame entry 0x42eb6c": 0x42EC4D,
                "stats background entry": 0x431051}.get(fragment_name, 0x56D000)
        stack = 0x708000
        emu.mem_write(stack, struct.pack("<I", stop))
        regs = [UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX,
                UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP]
        values = [0x1111, 0x2222, 0x3333, 0x4444, 0x5555, 0x6666, 0x7777]
        if fragment_name == "frame entry 0x42eb6c":
            values[-1] = 0x51D4C0
        if fragment_name == "stats background entry":
            values[0] = scene_surface
        for reg, value in zip(regs, values):
            emu.reg_write(reg, value)
        emu.reg_write(UC_X86_REG_ESP, stack)
        flags_before = 0x2D7  # Set all arithmetic status flags, plus IF and reserved bit 1.
        emu.reg_write(UC_X86_REG_EFLAGS, flags_before)
        calls = []
        def ret(extra=0, result=0xAAAA):
            sp = emu.reg_read(UC_X86_REG_ESP)
            ip = struct.unpack("<I", emu.mem_read(sp, 4))[0]
            # Game calls may clobber volatile registers and arithmetic flags.
            for reg, value in ((UC_X86_REG_EAX, result), (UC_X86_REG_EBX, 0xBBBB),
                               (UC_X86_REG_ECX, 0xCCCC), (UC_X86_REG_EDX, 0xDDDD)):
                emu.reg_write(reg, value)
            emu.reg_write(UC_X86_REG_EFLAGS, 0x202)
            emu.reg_write(UC_X86_REG_ESP, sp + 4 + extra)
            emu.reg_write(UC_X86_REG_EIP, ip)
        def hook(_emu, address, _size, _user):
            eax = emu.reg_read(UC_X86_REG_EAX)
            ebx = emu.reg_read(UC_X86_REG_EBX)
            ecx = emu.reg_read(UC_X86_REG_ECX)
            edx = emu.reg_read(UC_X86_REG_EDX)
            if address == 0x461C00:
                self.assertEqual(eax, 188)
                ret(result=0 if fail_allocation else 0x600000)
            elif address == 0x403D70:
                self.assertEqual((edx, ebx), (640, 480))
                ret(result=eax)
            elif address == 0x401E60:
                calls.append(("clear", eax))
                ret()
            elif address == 0x405EC0:
                ret(result=0x602000 + edx * 0x20)
            elif address == 0x603000:
                calls.append(("sprite", eax, edx, ebx, ecx))
                ret(28)
            elif address == 0x4024E0:
                sp = emu.reg_read(UC_X86_REG_ESP)
                right, bottom, dx, dy = struct.unpack("<4I", emu.mem_read(sp + 4, 16))
                calls.append(("copy", eax, edx, ebx, ecx, right, bottom, dx, dy))
                ret(16)
            elif address == 0x603100:
                calls.append(("free", eax, edx))
                ret()
        emu.hook_add(UC_HOOK_CODE, hook)
        va = next(va for name, va, _, _ in hud.HUD_CODE_FRAGMENTS if name == fragment_name)
        emu.emu_start(va, stop, count=10000)
        self.assertEqual(emu.reg_read(UC_X86_REG_EIP), stop)
        self.assertEqual(emu.reg_read(UC_X86_REG_ESP), stack + (4 if stop == 0x56D000 else 0))
        if fragment_name == "frame entry 0x42eb6c":
            values[4] = stack + 0x70
        self.assertEqual([emu.reg_read(reg) for reg in regs], values)
        self.assertEqual(emu.reg_read(UC_X86_REG_EFLAGS), flags_before)
        device_after = struct.unpack("<I", emu.mem_read(0x511230, 4))[0]
        expected_device = {"frame entry 0x42e8c4": 0x51D4C0,
                           "frame entry 0x42eb6c": 0x51D4C0,
                           "stats background entry": scene_surface}.get(fragment_name, device_before)
        self.assertEqual(device_after, expected_device)
        return calls

    def test_frame_composition_machine_code(self):
        calls = self.execute("HD frame before terrain")
        self.assertEqual([c for c in calls if c[0] == "clear"], [("clear", 0x600000), ("clear", 0x51D4C0)])
        self.assertEqual(len([c for c in calls if c[0] == "sprite"]), 4)
        copies = [c for c in calls if c[0] == "copy"]
        expected = [("copy", 0x600000, 0x51D4C0, sx, sy, sx+w-1, sy+h-1, dx, dy)
                    for sx, sy, w, h, dx, dy in hud.FRAME_BLITS]
        expected.append(("copy", 0x51D4C0, 0x604000, 0, 0, 1279, 719, 0, 0))
        self.assertEqual(copies, expected)
        self.assertEqual(calls[-1], ("free", 0x600000, 2))

    def test_stats_background_machine_code_never_copies_over_terrain(self):
        calls = self.execute("stats sidebar background only")
        self.assertEqual([c for c in calls if c[0] == "copy"],
                         [("copy", 0x600000, 0x604000, 480, 0, 639, 479, 1120, 120)])
        self.assertEqual(calls[-1], ("free", 0x600000, 2))

    def test_native_entry_trampolines_keep_continuation_state(self):
        for name in ("frame entry 0x42e8c4", "frame entry 0x42eb6c", "stats background entry"):
            with self.subTest(entry=name):
                self.assertEqual(self.execute(name)[-1], ("free", 0x600000, 2))

    def test_frame_before_scene_allocation_does_not_copy_to_null_surface(self):
        calls = self.execute("HD frame before terrain", scene_surface=0)
        self.assertEqual(len([c for c in calls if c[0] == "copy"]), len(hud.FRAME_BLITS))
        self.assertEqual(calls[-1], ("free", 0x600000, 2))

    def test_actual_patched_hover_routine_uses_displayed_sidebar_coordinates(self):
        if SOURCE_EXE is None:
            self.skipTest("no --source-exe supplied")
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
        from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP)
        data = SOURCE_EXE.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), hud.HUD_SOURCE_SHA256)
        original = data[0x42E160 - 0x400C00:0x42E3B7 - 0x400C00]
        cases = [(535, 30, 0), (623, 83, 0), (499, 91, 1), (623, 137, 1),
                 (499, 145, 2), (623, 179, 2), (499, 180, 3), (623, 213, 3),
                 (499, 214, 4), (623, 247, 4), (499, 248, 5), (623, 281, 5),
                 (499, 282, 6), (623, 315, 6), (499, 316, 7), (623, 349, 7),
                 (534, 30, -1), (624, 83, -1), (499, 90, -1), (498, 91, -1),
                 (499, 350, -1), (-608, 16, -1), (479, 200, -1)]
        for x, y, expected in cases:
            for scale in (0, 2):
                emu = Uc(UC_ARCH_X86, UC_MODE_32)
                emu.mem_map(0x400000, 0x200000)
                emu.mem_map(0x700000, 0x10000)
                emu.mem_write(0x42E160, original)
                emu.mem_write(hud.HUD_CODE_VA, hud.HUD_CODE)
                for _, offset, _, replacement, _ in hud.build_patches():
                    va = offset + 0x400C00
                    if 0x42E160 <= va < 0x42E3B7:
                        emu.mem_write(va, bytes.fromhex(replacement))
                emu.mem_write(0x544CFC, struct.pack("<ii", (x + 640) << scale, (y + 120) << scale))
                emu.mem_write(0x54512C, bytes([scale]))
                emu.reg_write(UC_X86_REG_ESP, 0x708000)
                emu.emu_start(0x42E160, 0x42E197, count=1000)
                self.assertEqual(emu.reg_read(UC_X86_REG_EIP), 0x42E197)
                result = emu.reg_read(UC_X86_REG_EAX)
                self.assertEqual(result, expected & 0xFFFFFFFF, (x + 640, y + 120, scale))

    def test_failed_frame_allocation_performs_no_surface_access(self):
        self.assertEqual(self.execute("HD frame before terrain", fail_allocation=True), [])
        self.assertEqual(self.execute("stats sidebar background only", fail_allocation=True), [])


def main() -> None:
    global SOURCE_EXE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolchain-path", type=Path)
    parser.add_argument("--source-exe", type=Path)
    parser.add_argument("--require-machine-tools", action="store_true")
    args, remaining = parser.parse_known_args()
    if args.toolchain_path:
        sys.path.insert(0, str(args.toolchain_path))
    SOURCE_EXE = args.source_exe
    if args.require_machine_tools:
        for module in ("keystone", "unicorn"):
            importlib.import_module(module)
    unittest.main(argv=[sys.argv[0], *remaining])


if __name__ == "__main__":
    main()
