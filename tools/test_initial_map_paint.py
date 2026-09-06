#!/usr/bin/env python3
"""Execute the initial-paint x86 against synthetic memory and destructive stubs.

Reads the user's original only for exact-byte/candidate reconstruction checks.
No proprietary executable is written or run; temporary compiler output is a
no-window x86 fixture. Native UI/draw calls are fixture recorders, never game
calls. The actual emitted admission and trampoline instructions execute.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher import initial_map_paint as initial
from src.patcher import partial_tile_clip as clip
from src.patcher import partial_tile_hooks as hooks
from src.patcher import patch_clash95_hd as patcher
import test_partial_tile_clip as runner
import test_partial_tile_hooks as hook_runner

BASE = runner.BASE
SHIM = BASE + 0xB000
UI = BASE + 0x9000
PAINT = BASE + 0x9400
RESUME = BASE + 0x9800
GUARD = BASE + 0x9C00
EDGE = BASE + 0xA000
PRESENT = BASE + 0xA400
CONVERGED = BASE + 0xA800
FULL_EPILOGUE = BASE + 0xAC00
POST_UI = [0xC011CA11, 0xB0B00001, 0xC0C00002, 0xD0D00003,
           0xE0E00004, 0xF0F00005, 0xA0A00006]
CANARIES = [0xABCD0000 + i for i in range(1, 6)]
SAVED_EDI = 0xD15A0E01
RESOLUTIONS = ((800, 600), (1024, 768), (1280, 720), (1280, 960), (1920, 1080), (802, 602))


def u32(value):
    return struct.pack("<I", value & 0xFFFFFFFF)


def rel32(code: bytearray, address: int, target: int, opcode=0xE9):
    code.append(opcode)
    code.extend(u32(target - (address + len(code) + 4)))


def flags(value=hook_runner.INITIAL_FLAGS):
    return bytes.fromhex("509c5825") + u32(~hook_runner.ARITHMETIC_FLAGS) + b"\x0d" + u32(value) + bytes.fromhex("509d58")


class FixtureSource:
    @classmethod
    def setUpClass(cls):
        cls.original = runner.ORIGINAL.read_bytes()
        cls.bundles = {}

    def candidate(self, width=800, height=600):
        recipe = patcher.select_patches_for(hooks.COMBINED_STAGE, patcher.parse_resolution(f"{width}x{height}"))
        return patcher.apply_patches(self.original, recipe)

    def bundle(self, width=800, height=600):
        key = (width, height)
        if key not in self.bundles:
            self.bundles[key] = initial.emit_hook_bundle(self.original, self.candidate(*key),
                                                        base_va=BASE, width=width, height=height)
        return self.bundles[key]


@unittest.skipUnless(runner.ORIGINAL.is_file(), "requires user-owned original for byte verification")
class SourceContractTests(FixtureSource, unittest.TestCase):
    def test_all_six_resolutions_preserve_old_payload_and_add_one_exact_hook(self):
        for width, height in RESOLUTIONS:
            with self.subTest(resolution=(width, height)):
                candidate = self.candidate(width, height)
                old = hooks.emit_hook_bundle(self.original, candidate, base_va=BASE, width=width, height=height)
                new = self.bundle(width, height)
                self.assertEqual(new.code[:len(old.code)], old.code)
                self.assertEqual(new.relocations[:len(old.relocations)], old.relocations)
                self.assertEqual(new.hook_sites[:3], old.hook_sites)
                self.assertEqual(new.status_vas, old.status_vas)
                self.assertEqual({k: new.entries[k] for k in old.entries}, old.entries)
                self.assertEqual(new.candidate_sha256, hashlib.sha256(candidate).hexdigest())
                self.assertFalse(new.installation_ready)
                site = new.hook_sites[3]
                self.assertEqual((site.name, site.va, site.rva, site.offset, site.old_bytes, site.fallback_va,
                                  site.removed_highlow_vas),
                                 ("initial_paint", 0x40B884, 0xB884, 0xAC84, bytes.fromhex("bed84c54005f"),
                                  0x40B894, (0x40B885,)))
                self.assertEqual(site.entry_va, new.entries["hook_initial_paint"])
                self.assertGreater(site.entry_va, BASE + len(old.code))
                self.assertEqual(new.initial_contract["full_tiles"], [(width - 32) // 64, (height - 16) // 64])
                extra = new.relocations[len(old.relocations):]
                self.assertEqual([(r.purpose, r.target) for r in extra if r.kind == "abs32"], [
                    ("initial_info_sprites", 0x527C24), ("tile_callback", 0x52698C),
                    ("game_data_global", 0x5202E4), ("initial_cursor_object", 0x544CD8),
                    ("current_player", 0x5202EC), ("render_device_global", 0x511230),
                    ("render_device_global", 0x511230)])
                self.assertEqual(len(clip.absolute_relocation_offsets(new)), len(clip.absolute_relocation_offsets(old)) + 7)
                self.assertEqual([r.purpose for r in extra if r.kind == "rel32"], [
                    "initial_composition_guard", "initial_native_ui", "initial_admission_call",
                    "initial_native_full_paint", "initial_native_resume"])
                for relocation in extra:
                    value = struct.unpack_from("<I", new.code, relocation.offset)[0]
                    expected = relocation.target if relocation.kind == "abs32" else relocation.target - (BASE + relocation.offset + 4)
                    self.assertEqual(value, expected & 0xFFFFFFFF)

    def test_native_first_entry_shared_join_backedge_and_highlow_inventory(self):
        candidate = self.candidate()
        for data in (self.original, candidate):
            for va, size, digest in initial.NATIVE_SPANS:
                off = clip.file_offset(data, va, size)
                self.assertEqual(hashlib.sha256(data[off:off + size]).hexdigest(), digest)
            off = clip.file_offset(data, 0x40B884, 16)
            self.assertEqual(data[off:off + 16], initial.NATIVE_ENTRY_BYTES)
            # EB C0 at B8C8 goes to shared B88A, six bytes beyond the hook.
            off = clip.file_offset(data, 0x40B8C8, 2)
            self.assertEqual(data[off:off + 2], bytes.fromhex("ebc0"))
            self.assertEqual(0x40B8CA + struct.unpack("b", data[off + 1:off + 2])[0], initial.SHARED_UI_JOIN)
        self.assertEqual(clip._original_highlow_fields(self.original, 0x40B884, 16), {1, 7})
        self.assertEqual(self.bundle().initial_contract["preserved_shared_highlow_va"], 0x40B88B)

    def test_source_candidate_and_unknown_resolution_fail_closed(self):
        for va in (0x40B884, 0x40B88B, 0x40B8C8, 0x423370, 0x418700):
            candidate = bytearray(self.candidate())
            candidate[clip.file_offset(candidate, va, 1)] ^= 1
            with self.assertRaises(ValueError):
                initial.emit_hook_bundle(self.original, bytes(candidate), base_va=BASE, width=800, height=600)
        original = bytearray(self.original)
        original[0x100] ^= 1
        with self.assertRaises(ValueError):
            initial.emit_hook_bundle(bytes(original), self.candidate(), base_va=BASE, width=800, height=600)
        with self.assertRaises(ValueError):
            initial.emit_hook_bundle(self.original, self.candidate(), base_va=BASE, width=1024, height=768)

    def test_observers_authenticate_real_instruction_and_call_boundaries(self):
        bundle = self.bundle()
        spans = bundle.initial_contract["observer_spans"]
        self.assertEqual(set(spans), {"ui_return", "admission", "ready", "paint_return"})
        expected_opcodes = {"ui_return": "9c60ff35", "admission": "83f8010f85",
                            "ready": "b801000000e8", "paint_return": "908f05"}
        for name, span in spans.items():
            self.assertEqual(span["instruction_va"], bundle.initial_status_vas[name])
            self.assertEqual(span["end_va_exclusive"], span["start_va"] + span["size"])
            pos = span["start_va"] - BASE
            self.assertEqual(bundle.code[pos:pos + span["size"]].hex(), span["bytes"])
            self.assertTrue(span["bytes"].startswith(expected_opcodes[name]))
            if "preceding_call" in span:
                call = span["preceding_call"]
                self.assertEqual(call["instruction_va"] + 5, span["instruction_va"])
                encoded = bytes.fromhex(call["bytes"])
                self.assertEqual(encoded[0], 0xE8)
                self.assertEqual(call["instruction_va"] + 5 + struct.unpack_from("<i", encoded, 1)[0], call["target_va"])
        admission = bundle.initial_status_vas["admission"] - BASE
        reject_target = BASE + admission + 9 + struct.unpack_from("<i", bundle.code, admission + 5)[0]
        self.assertEqual(reject_target, bundle.initial_status_vas["paint_return"] + 1,
                         "rejected admission must skip the return-only observer")
        self.assertFalse(bundle.initial_contract["paint_return_is_success"])
        self.assertEqual(bundle.initial_contract["stack"], {
            "ui_return_minus_admission": 40, "admission_equals_ready_equals_paint_return": True,
            "full_status_plus_to_ready": 88})
        json.dumps(bundle.initial_contract)  # Consumer metadata needs no bytes encoder.


@unittest.skipUnless(os.name == "nt" and runner.CSC.is_file() and runner.ORIGINAL.is_file(),
                     "requires local x86 fixture compiler and user-owned original")
class NativeX86Tests(FixtureSource, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp = tempfile.TemporaryDirectory(prefix="clash-initial-map-paint-fixture-")
        cls.root = Path(cls.temp.name)
        cls.exe = cls.root / "fixture.exe"
        source = runner.CSHARP
        replacements = {
            "Save(b,0x15,Output+36);": "Save(b,0x15,Output+36);b.AddRange(new byte[]{0x9c,0x8f,0x05});Imm(b,Output+16);",
            "new int[]{0,4,8,12,20,24,28,32,36}": "new int[]{0,4,8,12,20,24,28,32,36,16}",
            'W(Global+60,Get(c,"turn_sprites",Sprite));':
                'W(Global+60,Get(c,"turn_sprites",Sprite));W(Global+64,Get(c,"info",Sprite));'
                'W(Global+68,Get(c,"ui_info",Sprite));'
                'W(Global+72,Get(c,"ui_render",Get(c,"initial_render",0x12345000)));'
                'W(Global+76,Get(c,"ui_result",unchecked((int)0xC011CA11)));',
        }
        for anchor, replacement in replacements.items():
            if source.count(anchor) != 1:
                raise AssertionError("shared x86 fixture source contract changed")
            source = source.replace(anchor, replacement)
        source_path = cls.root / "fixture.cs"
        source_path.write_text(source, encoding="utf-8")
        compiled = subprocess.run([str(runner.CSC), "/nologo", "/platform:x86", "/optimize+",
                                   "/r:System.Web.Extensions.dll", f"/out:{cls.exe}", str(source_path)],
                                  capture_output=True, text=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
        if compiled.returncode:
            raise AssertionError(compiled.stdout + compiled.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def execute(self, changes=None, *, width=800, height=600, delta=0, guard_status=None,
                paint_status=0x76543210, shared=False, full_pair=False):
        bundle = self.bundle(width, height)
        code = bytearray(bundle.code)
        self.assertLess(len(code), 0x8000)
        globals_map = dict(runner.GLOBALS, initial_info_sprites=runner.GLOBAL + 64)
        transfers = {"initial_native_ui": UI, "initial_native_full_paint": PAINT,
                     "initial_native_resume": RESUME}
        if guard_status is not None:
            transfers["initial_composition_guard"] = GUARD
        if full_pair:
            transfers.update(hook_helper_edge_full_composed=EDGE, hook_helper_present_map_rect=PRESENT,
                             hook_resume_full_converge=CONVERGED,
                             hook_native_full_epilogue=FULL_EPILOGUE,
                             hook_resume_full_present=FULL_EPILOGUE)
            globals_map.update(hook_post_tile_callback=runner.GLOBAL + 28,
                               hook_cursor_x=runner.GLOBAL + 20)
        for relocation in bundle.relocations:
            if relocation.kind == "abs32":
                target = globals_map.get(relocation.purpose, relocation.target)
                struct.pack_into("<I", code, relocation.offset, target + delta)
            elif relocation.purpose in transfers:
                struct.pack_into("<I", code, relocation.offset,
                                 (transfers[relocation.purpose] - (BASE + relocation.offset + 4)) & 0xFFFFFFFF)
        descriptors_off = clip.file_offset(self.candidate(width, height), clip.COMMAND_DESCRIPTORS, 322)
        descriptors = bytearray(self.candidate(width, height)[descriptors_off:descriptors_off + 322])
        for i in range(6):
            struct.pack_into("<I", descriptors, 53 * i + 12, runner.GLOBAL + 36 + delta)
            struct.pack_into("<I", descriptors, 53 * i + 28, 0x4191F0 + delta)

        ui = bytearray(hook_runner.recorder(10, delta))
        # Model resource replacement and a changed render pointer before the
        # UI result. The adapter must preserve this NEW post-call state.
        for source, destination in ((68, 64), (72, 8)):
            ui += b"\xa1" + u32(runner.GLOBAL + source + delta)
            ui += b"\xa3" + u32(runner.GLOBAL + destination + delta)
        for opcode, value in zip((0xBB, 0xB9, 0xBA, 0xBE, 0xBF, 0xBD), POST_UI[1:]):
            ui += bytes([opcode]) + u32(value)
        ui += b"\xa1" + u32(runner.GLOBAL + 76 + delta) + flags() + b"\xc3"
        paint = bytearray(hook_runner.recorder(11, delta))
        paint += bytes.fromhex("c705") + u32(runner.GLOBAL + 8 + delta) + u32(0xBAD0F00D)
        if full_pair:
            paint += bytes.fromhex("53515256575583ec18")
            rel32(paint, PAINT, bundle.entries["hook_full_converge"])
        else:
            paint += hook_runner.helper_stub(paint_status, delta, kind=12)
        resume = bytearray(hook_runner.recorder(2, delta))
        resume += bytes.fromhex("8d642414c3")  # Drop five canaries without altering flags.
        shim = bytearray()
        for value in reversed(CANARIES):
            shim += b"\x68" + u32(value)
        if shared:
            # Execute the real unchanged shared MOV/CALL, with only its
            # address/callee rebound to synthetic memory, then continue.
            shim += b"\xa1" + u32(runner.GLOBAL + 32 + delta)
            rel32(shim, SHIM, UI, 0xE8)
            rel32(shim, SHIM, RESUME)
        else:
            shim += b"\x68" + u32(SAVED_EDI)
            rel32(shim, SHIM, bundle.entries["hook_initial_paint"])
        stubs = {UI: ui, PAINT: paint, RESUME: resume, SHIM: shim,
                 GUARD: hook_runner.helper_stub(guard_status or 0, delta, kind=13)}
        if full_pair:
            stubs[EDGE] = hook_runner.helper_stub(1, delta, kind=14)
            stubs[PRESENT] = hook_runner.helper_stub(paint_status, delta, kind=15)
            converge = bytearray(hook_runner.recorder(16, delta))
            rel32(converge, CONVERGED, bundle.entries["hook_full_present"])
            stubs[CONVERGED] = converge
            stubs[FULL_EPILOGUE] = hook_runner.recorder(17, delta) + bytes.fromhex("83c4185d5f5e5a595bc3")
        case = {"regs": [23, 0x123456, 0x654321, 29], "args": [], "entry": SHIM + delta}
        case.update(changes or {})
        payload = {"code": code.hex(), "width": width, "height": height,
                   "base": BASE + delta, "image_delta": delta,
                   "descriptor_bytes": descriptors.hex(),
                   "stubs": {str(address + delta): bytes(data).hex() for address, data in stubs.items()},
                   "cases": [case]}
        ran = subprocess.run([str(self.exe)], input=json.dumps(payload), capture_output=True,
                             text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        result = json.loads(ran.stdout)[0]
        rows = result["records"]
        self.assertEqual(rows[0][0], 10)
        self.assertEqual(rows[-1][0], 2)
        self.assertEqual(rows[-1][10:15], CANARIES, "neighbor stack locals were overwritten")
        expected = list(POST_UI)
        expected[0] = case.get("ui_result", expected[0]) & 0xFFFFFFFF
        self.assertEqual(rows[-1][1:8], expected, "post-UI GPR state changed")
        self.assertEqual(rows[-1][8] & hook_runner.ARITHMETIC_FLAGS, hook_runner.INITIAL_FLAGS)
        state = result["state"]
        self.assertEqual(state[0:4], [expected[0], *expected[4:7]])
        self.assertEqual(state[4], state[5], "adapter changed native stack depth")
        self.assertEqual(state[6:9], expected[1:4])
        self.assertEqual(state[9] & hook_runner.ARITHMETIC_FLAGS, hook_runner.INITIAL_FLAGS)
        self.assertEqual(result["render"], case.get("ui_render", case.get("initial_render", 0x12345000)) & 0xFFFFFFFF)
        self.assertEqual(rows[-1][9] - rows[0][9], 4, "UI CALL return must restore the same native frame")
        if not shared:
            self.assertEqual(rows[0][5:7], [initial.CURSOR_OBJECT + delta, SAVED_EDI], "displaced MOV/POP ABI changed")
        return result

    def test_admitted_all_six_resolutions_and_rebase_preserve_post_ui_state(self):
        for width, height in RESOLUTIONS:
            for delta in (0, 0x02000000):
                with self.subTest(resolution=(width, height), delta=delta):
                    result = self.execute({"initial_render": 0x12345678, "ui_render": 0x456789AB},
                                          width=width, height=height, delta=delta)
                    self.assertEqual([r[0] for r in result["records"]], [10, 11, 12, 2])
                    self.assertEqual(result["records"][1][1], 1, "native paint must receive EAX=1")
                    self.assertEqual(result["records"][-1][9] - result["records"][1][9], 44)
                    self.assertEqual(result["vtable"], clip.MEMORY_VTABLE + delta)

    def test_resource_load_result_and_original_ui_call_are_observed_once(self):
        for delta in (0, 0x02000000):
            self.assertEqual([r[0] for r in self.execute({"info": 0}, delta=delta)["records"]], [10, 11, 12, 2])
            self.assertEqual([r[0] for r in self.execute({"ui_info": 0}, delta=delta)["records"]], [10, 2])
            for player in range(5):
                result = self.execute({"current_player": player}, delta=delta)
                self.assertEqual(result["records"][0][1], player)
                self.assertEqual([r[0] for r in result["records"]], [10, 11, 12, 2])

    def test_real_composition_rejects_before_any_native_paint(self):
        failures = [{"bad": bad} for bad in ("global", "dimensions", "pixels", "vtable", "game_data",
                                             "descriptor", "descriptor_callback", "descriptor_end")]
        failures += [{"render_hook": 0}, {"owner": 1}, {"post_tile_callback": 1}, {"command_sprites": 0},
                     {"current_player": -1}, {"current_player": 5}, {"callback": 0x416850},
                     {"interactive": 0, "turn_sprites": 0}, {"tooltip": 1, "tooltip_left": 0}]
        for changes in failures:
            with self.subTest(changes=changes):
                self.assertEqual([r[0] for r in self.execute(changes)["records"]], [10, 2])

    def test_full_loop_world_and_scroll_admission_is_checked_before_paint(self):
        for width, height in ((800, 600), (1024, 768), (1920, 1080)):
            tx, ty = (width - 32) // 64, (height - 16) // 64
            for changes in ({"map_width": 0}, {"map_height": -1}, {"map_width": 101}, {"map_height": 101},
                            {"map_width": tx - 1, "scroll_x": 0}, {"map_height": ty - 1, "scroll_y": 0},
                            {"scroll_x": -1}, {"scroll_y": -1},
                            {"scroll_x": 60 - tx + 1}, {"scroll_y": 60 - ty + 1}):
                with self.subTest(resolution=(width, height), changes=changes):
                    self.assertEqual([r[0] for r in self.execute(changes, width=width, height=height)["records"]], [10, 2])
            for changes in ({"map_width": tx, "map_height": ty, "scroll_x": 0, "scroll_y": 0},
                            {"map_width": 100, "map_height": 100, "scroll_x": 100 - tx, "scroll_y": 100 - ty}):
                self.assertEqual([r[0] for r in self.execute(changes, width=width, height=height)["records"]], [10, 11, 12, 2])

    def test_destructive_composition_guard_exact_success_and_reject(self):
        for delta in (0, 0x02000000):
            for status in (0, 1, 2, 0xFFFFFFFF):
                result = self.execute(delta=delta, guard_status=status)
                self.assertEqual([r[0] for r in result["records"]], [10, 13] + ([11, 12] if status == 1 else []) + [2])

    def test_native_shared_turn_join_has_no_paint_and_new_entry_has_one(self):
        for delta in (0, 0x02000000):
            self.assertEqual([r[0] for r in self.execute(shared=True, delta=delta)["records"]], [10, 2])
            for _ in range(2):
                self.assertEqual([r[0] for r in self.execute(delta=delta)["records"]], [10, 11, 12, 2])

    def test_full_hook_chain_executes_with_authenticated_stack_relation(self):
        for delta in (0, 0x02000000):
            for status in (0, 1, 2):
                result = self.execute(delta=delta, full_pair=True, paint_status=status)
                rows = result["records"]
                self.assertEqual([r[0] for r in rows], [10, 11, 14, 16, 15, 17, 2])
                # Native paint entry is readyESP-4. Full helper entry is
                # statusESP-4. Their difference independently proves +88.
                self.assertEqual(rows[1][9] - rows[2][9], initial.FULL_STATUS_TO_READY_STACK_BYTES)
                self.assertEqual(rows[2][9], rows[4][9], "full hooks must share one invocation frame")
                self.assertEqual(rows[4][1:5], [32, 16, 799, 599])
                # Full presentation may reject; its native return never
                # replaces the UI result or implies rendering passed.
                self.assertEqual(result["state"][0], POST_UI[0])


if __name__ == "__main__":
    unittest.main()
