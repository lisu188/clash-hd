"""Classic bounds contracts; opt-in original-bound emitted CPU models.

The optional CPU lane executes the actual emitted adapters. Native Tile,
fill/minimap/presentation and input functions are explicit modeled callbacks;
this does not execute game instructions or establish Windows gameplay proof.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import hd_multires_classic_bounded as tool
from src.patcher import classic_all_presets_candidate as classic
from src.patcher import partial_tile_clip as clip
from src.patcher import pe_extension as pe
STAGE = classic.STABLE_STAGE + "-classic-hd-multires-validation"


class AuthoringTests(unittest.TestCase):
    def test_exact_three_presets_and_original_gate(self):
        self.assertEqual(tool.RESOLUTIONS, ("1920x1080", "2560x1440", "3840x2160"))
        for raw in (b"", b"authored fixture", bytearray(32), None):
            with self.assertRaises((ValueError, TypeError)):
                tool.integrate(b"", {}, original=raw, resolution="1920x1080", selected_stage=STAGE)

    def test_no_framed_builder_native_panel_or_binary_write(self):
        tree = ast.parse(Path(tool.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, ("framed_all_presets_candidate", "four_sided_frame"))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                self.assertNotIn(node.func.attr, ("write_bytes", "write_text", "Popen", "run"))
        self.assertEqual(tool.FULL_ENTRY, bytes.fromhex("53515256575583ec18"))
        self.assertEqual(tool.INCREMENTAL_ENTRY, bytes.fromhex("535156575583ec08"))

    def test_hook_caller_inventory_retains_native_classic_panel_branches(self):
        self.assertEqual(tool.MOUSE_CALLS, ((0x4084A9, 0x40DD60, "minimap_gate"),
            (0x407F3C, 0x40DD60, "minimap_gate"), (0x408039, 0x4608F0, "click_gate")))
        self.assertNotIn(0x40855D, [row[0] for row in tool.MOUSE_CALLS])
        self.assertNotIn(0x4080AA, [row[0] for row in tool.MOUSE_CALLS])


class Machine:
    CODE = 0x700000
    STACK = 0x20000000
    GAME = 0x21000000
    SURFACE = 0x22000000
    PIXELS = 0x23000000
    STOP = 0x24000000

    def __init__(self, original, resolution, delta=0, world=(1, 1)):
        import unicorn as u
        from unicorn import x86_const as x
        self.u, self.x, self.delta = u, x, delta
        self.cpu = u.Uc(u.UC_ARCH_X86, u.UC_MODE_32)
        self.regs = {name: getattr(x, "UC_X86_REG_" + name) for name in
            ("EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP", "EIP", "EFLAGS")}
        self.width, self.height = map(int, resolution.split("x"))
        self.bundle = tool.emit(original, base_va=self.CODE, width=self.width, height=self.height)
        self.cpu.mem_map(0x400000 + delta, 0x400000)
        for address, count in ((self.STACK, 0x10000), (self.GAME, 0x30000),
                (self.SURFACE, 0x1000), (self.PIXELS, 0x1000), (self.STOP, 0x1000)):
            self.cpu.mem_map(address, count)
        code = bytearray(self.bundle.code)
        for row in self.bundle.relocations:
            if row.kind == "abs32":
                struct.pack_into("<I", code, row.offset, row.target + delta)
        self.cpu.mem_write(self.CODE + delta, bytes(code))
        self.cpu.mem_write(self.STOP, b"\x90")
        self.events = []
        self.native_body = []
        self.native_mouse = []
        self.loaded = bytes(code)
        self.world = world
        for address, value in ((clip.MAP_SURFACE_GLOBAL, self.SURFACE),
                (clip.GAME_DATA_GLOBAL, self.GAME), (clip.RENDER_DEVICE_GLOBAL, 0x12345678),
                (clip.RENDER_HOOK_GLOBAL, 0x40AD40 + delta), (clip.CURSOR_VISIBLE_GLOBAL, 0)):
            self.put(address + delta, value)
        self.put(self.SURFACE, self.width | self.height << 16)
        self.put(self.SURFACE + 4, self.PIXELS)
        self.put(self.SURFACE + 184, clip.MEMORY_VTABLE + delta)
        for offset, value in ((0x222E0, world[0]), (0x222E4, world[1]), (0x222E8, 0), (0x222EC, 0)):
            self.put(self.GAME + offset, value)
        argc = {"line": 8, "fill": 8, "sprite": 28, "tile": 0,
                "minimap": 0, "dirty": 4, "blit": 16, "cursor": 0}
        self.targets = {target + delta: name for name, target in clip.NATIVE_TARGETS.items() if name in argc}
        for target, name in self.targets.items():
            count = argc[name]
            self.cpu.mem_write(target, b"\xc2" + struct.pack("<H", count) if count else b"\xc3")
        self.cpu.mem_write(0x40DD60 + delta, bytes.fromhex("31c0c3"))
        self.cpu.mem_write(0x4608F0 + delta, bytes.fromhex("b801000000c3"))
        self.cpu.hook_add(u.UC_HOOK_CODE, self.observe)

    def put(self, address, value):
        self.cpu.mem_write(address, struct.pack("<I", value & 0xFFFFFFFF))

    def word(self, address):
        return struct.unpack("<I", self.cpu.mem_read(address, 4))[0]

    def get(self, name):
        return self.cpu.reg_read(self.regs[name])

    def observe(self, cpu, pc, size, user):
        if pc in (0x418709 + self.delta, 0x418A98 + self.delta, 0x4187A7 + self.delta):
            self.native_body.append(pc)
            cpu.emu_stop()
            return
        if pc in (0x40DD60 + self.delta, 0x4608F0 + self.delta):
            self.native_mouse.append(pc)
        name = self.targets.get(pc)
        if name is None:
            return
        if name == "tile":
            offset = self.get("EBX") - self.GAME
            column, rest = divmod(offset, 1400)
            row, tail = divmod(rest, 14)
            assert tail == 0 and 0 <= column < self.world[0] and 0 <= row < self.world[1]
            self.events.append((name, column, row, self.get("EAX"), self.get("EDX")))
        elif name == "fill":
            bottom = self.word(self.get("ESP") + 4)
            rectangle = self.get("EDX"), self.get("EBX"), self.get("ECX"), bottom
            assert 32 <= rectangle[0] <= rectangle[2] < self.width
            assert 16 <= rectangle[1] <= rectangle[3] < self.height
            self.events.append((name, *rectangle))
        else:
            self.events.append((name,))

    def invoke(self, entry, values=None):
        values = values or {}
        initial = {"EAX": 0, "EBX": 0, "ECX": 0x11223344, "EDX": 0x55667788,
            "ESI": 0, "EDI": 0xAABBCCDD, "EBP": 0x31415926,
            "ESP": self.STACK + 0xE000, "EFLAGS": 0x246}
        initial.update(values)
        self.put(initial["ESP"], self.STOP)
        for name, value in initial.items():
            self.cpu.reg_write(self.regs[name], value)
        self.events.clear(); self.native_body.clear(); self.native_mouse.clear()
        self.cpu.emu_start(self.bundle.entries[entry] + self.delta, self.STOP, count=2000000)
        actual = {name: self.get(name) for name in initial}
        if not self.native_body:
            assert actual["ESP"] == initial["ESP"] + 4
            for name in ("EBX", "ECX", "EDX", "ESI", "EDI", "EBP"):
                assert actual[name] == initial[name], (name, actual[name], initial[name])
            assert actual["EFLAGS"] & 0xCD5 == initial["EFLAGS"] & 0xCD5
        assert bytes(self.cpu.mem_read(self.CODE + self.delta, len(self.loaded))) == self.loaded
        return actual


class OriginalBoundTests(unittest.TestCase):
    original = None

    def test_three_exact_classic_parents_integrate_and_keep_native_ui_bytes(self):
        for resolution in tool.RESOLUTIONS:
            parent, metadata, _ = classic.build_candidate(self.original, resolution)
            image, report = tool.integrate(parent, metadata, original=self.original,
                resolution=resolution, selected_stage=STAGE)
            self.assertTrue(report["classic_style_preserved"])
            self.assertFalse(report["framed_builder_used"])
            self.assertEqual(report["native_hooks"], 8)
            self.assertEqual(len(pe.inspect_pe(image).sections), len(pe.inspect_pe(parent).sections))
            for va, size in ((0x511D40, 322), (0x40855D, 6), (0x4080AA, 6)):
                a = clip.file_offset(parent, va, size); b = clip.file_offset(image, va, size)
                self.assertEqual(parent[a:a + size], image[b:b + size])
            rebuilt = bytearray(parent)
            for edit in report["edits"]:
                offset, old, new = edit["offset"], bytes.fromhex(edit["old_hex"]), bytes.fromhex(edit["new_hex"])
                self.assertEqual(rebuilt[offset:offset + len(old)], old)
                rebuilt[offset:offset + len(old)] = new
            self.assertEqual(bytes(rebuilt), image)
            bad = bytearray(parent); bad[0x500] ^= 1
            with self.assertRaises(ValueError):
                tool.integrate(bytes(bad), metadata, original=self.original,
                    resolution=resolution, selected_stage=STAGE)

    def test_bounded_cells_draw_only_actual_world_and_clear_clipped_exterior(self):
        for resolution in tool.RESOLUTIONS:
            for delta in (0, 0x30000):
                m = Machine(self.original, resolution, delta=delta, world=(2, 3))
                for column, row, present in ((0, 0, 0), (1, 2, 1), (2, 0, 0), (0, 3, 1)):
                    result = m.invoke("cell", {"EAX": column, "EBX": row, "ESI": present})
                    self.assertEqual(result["EAX"], 1 if column < 2 and row < 3 else 2)
                    self.assertEqual(bool([r for r in m.events if r[0] == "tile"]), column < 2 and row < 3)
                    self.assertEqual(bool([r for r in m.events if r[0] == "fill"]), column >= 2 or row >= 3)
                    self.assertEqual(m.word(m.SURFACE + 184), clip.MEMORY_VTABLE + delta)
                    self.assertEqual(m.word(clip.RENDER_DEVICE_GLOBAL + delta), 0x12345678)
                columns, rows = (m.width - 32 + 63) // 64, (m.height - 16 + 63) // 64
                m.invoke("cell", {"EAX": columns - 1, "EBX": rows - 1})
                fill = [r for r in m.events if r[0] == "fill"]
                self.assertEqual(fill[-1][3:], (m.width - 1, m.height - 1))
                for column, row in ((-1, 0), (columns, 0), (0, rows)):
                    result = m.invoke("cell", {"EAX": column & 0xFFFFFFFF, "EBX": row})
                    self.assertEqual(result["EAX"], 0)
                    self.assertEqual(m.events, [])

    def test_camera_clamps_before_native_full_loop_and_bad_dimensions_reject(self):
        for resolution in tool.RESOLUTIONS:
            m = Machine(self.original, resolution, delta=0x30000, world=(2, 3))
            m.put(m.GAME + 0x222E8, 99); m.put(m.GAME + 0x222EC, 0xFFFFFFFF)
            m.invoke("full_entry", {"EAX": 1})
            self.assertEqual(m.native_body, [0x418709 + m.delta])
            self.assertEqual(m.word(m.GAME + 0x222E8), 0)
            self.assertEqual(m.word(m.GAME + 0x222EC), 0)
            for dimension in (0, 101, 0xFFFFFFFF):
                m.put(m.GAME + 0x222E0, dimension)
                result = m.invoke("full_entry", {"EAX": 1})
                self.assertEqual(result["EAX"], 0)
                self.assertEqual(m.native_body, [])

    def test_partial_classic_right_and_bottom_cells_are_cleared_and_presented(self):
        for resolution in tool.RESOLUTIONS:
            m = Machine(self.original, resolution, world=(1, 1))
            m.invoke("partial_tail", {"EBP": 1})
            tx, ty = (m.width - 32) // 64, (m.height - 16) // 64
            cx, cy = (m.width - 32 + 63) // 64, (m.height - 16 + 63) // 64
            self.assertEqual(len([r for r in m.events if r[0] == "fill"]), cx * cy - tx * ty)
            self.assertEqual(len([r for r in m.events if r[0] == "blit"]), cx * cy - tx * ty)
            self.assertFalse([r for r in m.events if r[0] == "tile"])
            self.assertEqual(m.native_body, [0x4187A7])
            # The native full-paint argument is truthy, not an enum 0/1.
            m.invoke("partial_tail", {"EBP": 2})
            self.assertEqual(len([r for r in m.events if r[0] == "blit"]), cx * cy - tx * ty)

    def test_native_full_call_adapter_and_incremental_paths_preserve_classic_grid(self):
        m = Machine(self.original, "3840x2160", world=(2, 3))
        for x, y in ((0, 0), (1, 2), (2, 0), (0, 3)):
            expected = 1 if x < 2 and y < 3 else 2
            result = m.invoke("full_tile", {"EAX": 32 + 64 * x, "EDX": 16 + 64 * y,
                "EBX": m.GAME + x * 1400 + y * 14})
            self.assertEqual(result["EAX"], expected)
            result = m.invoke("incremental", {"EAX": x, "EDX": y})
            self.assertEqual(result["EAX"], expected)
            self.assertEqual(len([r for r in m.events if r[0] == "blit"]), 1)

    def test_mouse_only_admits_actual_world_pixels_and_preserves_native_panel_rules(self):
        for resolution in tool.RESOLUTIONS:
            m = Machine(self.original, resolution, delta=0x30000, world=(2, 3))
            m.put(0x54512C + m.delta, 0)
            for x, y, admitted in ((32, 16, True), (159, 207, True), (160, 16, False),
                    (32, 208, False), (31, 16, False), (32, 15, False)):
                m.put(0x544CFC + m.delta, x); m.put(0x544D00 + m.delta, y)
                for entry in ("minimap_gate", "click_gate"):
                    result = m.invoke(entry, {"EAX": m.SURFACE})
                    self.assertEqual(result["EAX"], int(admitted) if entry == "click_gate" else int(not admitted))
            m.put(m.GAME + 0x222E8, 1)
            self.assertEqual(m.invoke("click_gate", {"EAX": m.SURFACE})["EAX"], 0)

    def test_invalid_context_does_not_reach_native_pointer_or_input_paths(self):
        m = Machine(self.original, "1920x1080", delta=0x30000)
        cases = ((clip.CURRENT_PLAYER_GLOBAL + m.delta, 5),
                 (m.GAME + 0x23EC7, 5), (m.GAME + 0x222E0, 0),
                 (m.SURFACE + 184, clip.MEMORY_VTABLE + m.delta + 4),
                 (clip.POST_TILE_CALLBACK_GLOBAL + m.delta, 1))
        for address, invalid in cases:
            before = m.word(address)
            m.put(address, invalid)
            for entry in ("full_entry", "incremental", "full_tile", "click_gate"):
                with self.subTest(address=address, entry=entry):
                    result = m.invoke(entry, {"EAX": 32, "EDX": 16})
                    self.assertEqual(result["EAX"], 0)
                    self.assertEqual(m.events, [])
                    self.assertEqual(m.native_body, [])
                    self.assertEqual(m.native_mouse, [])
            m.put(address, before)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AuthoringTests)
    path, original_hash = None, None
    if args.original_backed:
        path = Path(args.original_backed)
        OriginalBoundTests.original = path.read_bytes()
        clip.verify_original(OriginalBoundTests.original)
        original_hash = hashlib.sha256(OriginalBoundTests.original).hexdigest()
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(OriginalBoundTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if path is not None:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == original_hash
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
