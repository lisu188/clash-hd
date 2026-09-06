#!/usr/bin/env python3
"""Synthetic x86 frame entry/presentation ABI tests; never a game or debugger."""
from __future__ import annotations

import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher import framed_presentation as presentation
from src.patcher import four_sided_frame as frame
from src.patcher import partial_tile_clip as clip
from src.patcher.framed_viewport import FramedViewport
import test_partial_tile_clip as runner
import test_four_sided_frame_x86 as frame_fixture


PRIMARY = runner.BASE + 0x15000
FALLBACK = runner.BASE + 0xA000
BLIT_RESULT = runner.GLOBAL + 76
BLIT_FLAGS = runner.GLOBAL + 80
RESOLUTIONS = frame_fixture.RESOLUTIONS
DELTAS = frame_fixture.DELTAS
NATIVE_RESULT = 0xFACE0005  # Synthetic fallback only; not a game result.


def fixture_source() -> str:
    source = frame_fixture.fixture_source()
    setup = r'''
    int primary=B+0x15000;
    W(primary,I(root["width"]) | (I(root["height"])<<16));
    W(primary+4,0); // Primary is not a memory surface; zero here is valid.
    W(primary+0xB8,0x50eec4+delta);W(primary+0xBC,B+0x16000);W(primary+0xD4,8);
    W(B+0x16000+0xA4,B+0x16100);W(B+0x16100,B+0x16200);
    W(B+0x16200+0x64,B+0x16300);W(B+0x16200+0x6C,B+0x16300);W(B+0x16200+0x80,B+0x16300);
    W(B+0x16000+0x5C,0); // Lock establishes pixels; do not require them before it.
    W(Global+76,Get(c,"blit_result",0x24681357));
    if(Get(c,"primary_dimensions",0)!=0)W(primary,640 | (480<<16));
    if(Get(c,"primary_zero_dimensions",0)!=0)W(primary,0);
    if(Get(c,"primary_vtable",0)!=0)W(primary+0xB8,0x50ee24+delta);
    if(Get(c,"primary_backend",0)!=0)W(primary+0xBC,0);
    if(Get(c,"primary_com",0)!=0)W(B+0x16000+0xA4,0);
    if(Get(c,"primary_com_vtable",0)!=0)W(B+0x16100,0);
    if(Get(c,"primary_com_method",0)!=0)W(B+0x16200+Get(c,"primary_com_method",0),0);
    if(Get(c,"primary_depth",0)!=0)W(primary+0xD4,16);
    if(Get(c,"map_is_primary",0)!=0)W(Global,primary);
    if(Get(c,"change_primary_pixels",0)!=0)W(primary+4,unchecked((int)0xABCDEF01));
'''
    anchor = '    var regs=(IList)c["regs"];var args=(IList)c["args"];'
    return frame_fixture.replace_once(source, anchor, setup + anchor)


def blit_stub(delta: int) -> bytes:
    result = runner.recorder(2, 4, delta=delta)
    load_owner = b"\xa1" + struct.pack("<I", runner.GLOBAL + 16 + delta) + bytes.fromhex("89473c")
    load_flags = b"\xa1" + struct.pack("<I", BLIT_FLAGS + delta) + bytes.fromhex("89473c")
    if result.count(load_owner) != 1 or not result.endswith(bytes.fromhex("c21000")):
        raise AssertionError("shared four-argument recorder changed")
    result = bytes.fromhex("9c8f05") + struct.pack("<I", BLIT_FLAGS + delta) + result.replace(load_owner, load_flags)
    out = bytearray(result[:-3])
    for opcode, value in ((0xBB, 0xB0B0B0B0), (0xB9, 0xC0C0C0C0), (0xBA, 0xD0D0D0D0),
                          (0xBE, 0xE0E0E0E0), (0xBF, 0xF0F0F0F0), (0xBD, 0xA0A0A0A0)):
        out += bytes([opcode]) + struct.pack("<I", value)
    out += bytes.fromhex("c705") + struct.pack("<II", runner.GLOBAL + 8 + delta, 0xDEAD2222)
    out += bytes.fromhex("31c0f9fda1") + struct.pack("<I", BLIT_RESULT + delta) + bytes.fromhex("c21000")
    return bytes(out)


def fallback_stub(delta: int) -> bytes:
    """Observe the replayed five-PUSH entry, then model only its native epilogue.

    It does not execute native fallback drawing or imply that fallback is safe
    under invalid game state. Exact saved registers/return stack are the claim.
    """
    out = bytearray.fromhex("9c6089e5bf") + struct.pack("<I", runner.RECORD + delta)
    out += bytes.fromhex("8b376bf640ff078d7c3704c707") + struct.pack("<I", 9)
    for index, offset in enumerate((28, 16, 24, 20, 4, 0, 8, 32), 1):
        out += bytes((0x8B, 0x45, offset, 0x89, 0x47, 4 * index))
    out += bytes.fromhex("8d4524894724")
    for index in range(6):
        out += bytes((0x8B, 0x45, 36 + 4 * index, 0x89, 0x47, 40 + 4 * index))
    out += bytes.fromhex("619dc705") + struct.pack("<II", runner.GLOBAL + 8 + delta, PRIMARY + delta)
    out += b"\xb8" + struct.pack("<I", NATIVE_RESULT) + bytes.fromhex("5f5e5a595bc3")
    return bytes(out)


@unittest.skipUnless(os.name == "nt" and runner.CSC.is_file() and runner.ORIGINAL.is_file(),
                     "requires local x86 fixture compiler and original for byte authentication")
class FramedPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="clash-framed-present-x86-")
        cls.addClassCleanup(cls.temp.cleanup)
        root = Path(cls.temp.name)
        cls.exe = root / "fixture.exe"
        source = root / "fixture.cs"
        source.write_text(fixture_source(), encoding="utf-8")
        result = subprocess.run([str(runner.CSC), "/nologo", "/platform:x86", "/optimize+",
                                 "/r:System.Web.Extensions.dll", f"/out:{cls.exe}", str(source)],
                                capture_output=True, text=True, timeout=60,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.original = runner.ORIGINAL.read_bytes()
        cls.bundles = {}

    def bundle(self, width: int, height: int):
        if (width, height) not in self.bundles:
            self.bundles[width, height] = presentation.emit_framed_presentation(
                self.original, base_va=runner.BASE, width=width, height=height)
        return self.bundles[width, height]

    def execute(self, width: int, height: int, cases: list[dict], *, delta: int = 0):
        bundle = self.bundle(width, height)
        code = bytearray(bundle.code)
        self.assertLess(len(code), 0x6000)
        self.assertFalse(bundle.installation_ready)
        for offset in clip.absolute_relocation_offsets(bundle):
            old = struct.unpack_from("<I", code, offset)[0]
            struct.pack_into("<I", code, offset, old + delta)
        absolute_targets = {"map_surface_global": runner.GLOBAL, "render_device_global": runner.GLOBAL + 8,
                            "frame_sprites_global": frame_fixture.FRAME_GLOBAL,
                            "primary_surface": PRIMARY, "render_hook": runner.GLOBAL + 24,
                            "post_tile_callback": runner.GLOBAL + 28, "lower_row_owner": runner.GLOBAL + 16}
        native_targets = {"sprite": runner.STUBS["sprite"], "blit": runner.STUBS["blit"],
                          "native_frame_fallback": FALLBACK}
        for relocation in bundle.relocations:
            if relocation.purpose in absolute_targets:
                self.assertEqual(relocation.kind, "abs32")
                struct.pack_into("<I", code, relocation.offset, absolute_targets[relocation.purpose] + delta)
            elif relocation.kind == "rel32":
                self.assertIn(relocation.purpose, native_targets)
                struct.pack_into("<i", code, relocation.offset,
                                 native_targets[relocation.purpose] - (runner.BASE + relocation.offset + 4))
            else:
                self.assertIn(relocation.purpose, ("memory_vtable", "primary_vtable", "ordinary_map_owner"))
        payload = dict(code=code.hex(), width=width, height=height, base=runner.BASE + delta, image_delta=delta,
            stubs={str(runner.STUBS["sprite"] + delta): frame_fixture.destructive_sprite_stub(delta).hex(),
                   str(runner.STUBS["blit"] + delta): blit_stub(delta).hex(),
                   str(FALLBACK + delta): fallback_stub(delta).hex()},
            cases=[dict(case, regs=[case.get("eax", 1), *frame_fixture.INPUT_REGS[1:]], args=[],
                        entry=bundle.entries[case.get("entry_name", "present_frame_bands")] + delta) for case in cases])
        result = subprocess.run([str(self.exe)], input=json.dumps(payload), capture_output=True, text=True,
                                timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        reports = json.loads(result.stdout)
        self.assertEqual(len(reports), len(cases))
        for case, report in zip(cases, reports):
            state = report["state"]
            self.assertEqual(state[1:4], [0x11223344, 0x55667788, 0x99AABBCC])
            self.assertEqual(state[6:9], frame_fixture.INPUT_REGS[1:])
            self.assertEqual(state[4], state[5], "callee-cleaned blit or native fallback corrupted ESP")
            mask = frame_fixture.ARITHMETIC_FLAGS | frame_fixture.DIRECTION_FLAG
            self.assertEqual(state[9] & mask, case.get("initial_flags", frame_fixture.INITIAL_FLAGS) & mask)
            self.assertEqual(report["render"], PRIMARY + delta if case.get("entry_name") == "native_frame_entry"
                             else case.get("initial_render", 0x12345000))
        return reports

    def assert_blits(self, records, layout, delta):
        self.assertEqual(len(records), 4)
        for record, band in zip(records, layout.frame_bands):
            self.assertEqual(record[0], 2)
            self.assertEqual(record[1:5], [runner.SURFACE + delta, band.left, band.top, 0])
            self.assertEqual(record[5:9], [band.right, band.bottom, band.left, band.top])
            self.assertEqual(record[9:12], [0, 0, 0])
            self.assertEqual(record[12:14], [clip.MEMORY_VTABLE + delta, PRIMARY + delta])
            self.assertEqual(record[15] & frame_fixture.DIRECTION_FLAG, 0)
        self.assertEqual(sum(band.area for band in layout.frame_bands),
                         layout.surface.area - layout.terrain.area)
        # Fixed disjoint bands include the entire footer once and no terrain.
        footer = frame.frame_draw_plan(layout)[-1].clip
        self.assertEqual(sum(band.intersection(footer).area if band.intersection(footer) else 0
                             for band in layout.frame_bands), footer.area)

    def test_presenter_exact_native_blit_abi_flags_and_rebase(self):
        for width, height in RESOLUTIONS:
            for delta in DELTAS:
                cases = [{"eax": 1, "blit_result": 0}, {"eax": 1, "blit_result": -1, "initial_render": 0},
                         {"eax": 1, "change_primary_pixels": 1,
                          "initial_flags": frame_fixture.INITIAL_FLAGS | frame_fixture.DIRECTION_FLAG}]
                with self.subTest(resolution=(width, height), delta=delta):
                    for report in self.execute(width, height, cases, delta=delta):
                        self.assertEqual(report["state"][0], 1)
                        self.assert_blits(report["records"], FramedViewport(width, height), delta)

    def test_zero_present_is_unconditional_no_primary_call_and_invalid_flags_reject(self):
        for delta in DELTAS:
            cases = [{"eax": 0, "null_target": 1, "primary_backend": 1, "null_table": 1,
                      "render_hook": 0, "initial_render": 0, "initial_flags": 0xED7},
                     {"eax": -1}, {"eax": 2}, {"eax": 0x7FFFFFFF}]
            reports = self.execute(800, 600, cases, delta=delta)
            self.assertEqual([r["state"][0] for r in reports], [1, 0, 0, 0])
            self.assertTrue(all(not report["records"] for report in reports))

    def test_all_admission_failures_before_primary_calls(self):
        cases = [{"null_target": 1}, {"mapped_bad_target": 1}, {"map_is_primary": 1},
                 {"bad": "dimensions"}, {"bad": "pixels"}, {"bad": "vtable"},
                 {"primary_zero_dimensions": 1}, {"primary_vtable": 1}, {"primary_backend": 1},
                 {"primary_depth": 1}, {"render_hook": 0}, {"render_hook": 0x4352B3},
                 {"owner": 1}, {"post_tile_callback": 0x40AD40},
                 {"primary_com": 1}, {"primary_com_vtable": 1},
                 *[{"primary_com_method": offset} for offset in (0x64, 0x6C, 0x80)]]
        for width, height in RESOLUTIONS:
            for delta in DELTAS:
                selected = cases + ([{"primary_dimensions": 1}] if (width, height) != (640, 480) else [])
                with self.subTest(resolution=(width, height), delta=delta):
                    reports = self.execute(width, height, selected, delta=delta)
                    self.assertTrue(all(r["state"][0] == 0 and not r["records"] for r in reports))

    def test_native_wrapper_draws_map_then_four_bands_and_retains_native_poststate(self):
        for width, height in RESOLUTIONS:
            for delta in DELTAS:
                case = {"entry_name": "native_frame_entry", "eax": 0x12345678,
                        "native_result": -1, "blit_result": 0, "initial_flags": 0xED7}
                with self.subTest(resolution=(width, height), delta=delta):
                    report = self.execute(width, height, [case], delta=delta)[0]
                    self.assertEqual(report["state"][0], case["eax"], "wrapper invented a native EAX success result")
                    plan = frame.frame_draw_plan(FramedViewport(width, height))
                    self.assertEqual(len(report["records"]), len(plan) + 4)
                    for record, draw in zip(report["records"][:-4], plan):
                        self.assertEqual(record[0], 3)
                        self.assertEqual(record[1], runner.SURFACE + delta, "direct primary sprite call")
                        self.assertEqual(record[5:12], [*draw.clip.as_tuple(), 1, 0, 0])
                    self.assert_blits(report["records"][-4:], FramedViewport(width, height), delta)

    def test_native_fallback_replays_exact_five_pushes_and_entry_state(self):
        failures = [{"bad": "dimensions"}, {"render_hook": 0}, {"render_hook": 0x4352B3}, {"owner": 1},
                    {"post_tile_callback": 1}, {"primary_backend": 1}, {"primary_depth": 1}, {"null_table": 1},
                    {"primary_com": 1}, {"primary_com_vtable": 1},
                    *[{"primary_com_method": offset} for offset in (0x64, 0x6C, 0x80)]]
        failures += [{field: index} for index in frame_fixture.HEADERS
                     for field in ("null_sprite", "wrong_width", "wrong_height", "transposed_header", "bad_encoding", "zero_stream")]
        for delta in DELTAS:
            cases = [dict(failure, entry_name="native_frame_entry", eax=0x12345678) for failure in failures]
            reports = self.execute(800, 600, cases, delta=delta)
            for report in reports:
                self.assertEqual(report["state"][0], NATIVE_RESULT)
                self.assertEqual(len(report["records"]), 1, "HD drawing occurred before fallback")
                row = report["records"][0]
                self.assertEqual(row[0], 9)
                self.assertEqual(row[1:8], [0x12345678, *frame_fixture.INPUT_REGS[1:],
                                           0x11223344, 0x55667788, 0x99AABBCC])
                self.assertEqual(row[10:15], [0x55667788, 0x11223344, *reversed(frame_fixture.INPUT_REGS[1:])])
                self.assertEqual(row[9], report["state"][4] - 24)
                self.assertEqual(row[8] & frame_fixture.ARITHMETIC_FLAGS,
                                 frame_fixture.INITIAL_FLAGS & frame_fixture.ARITHMETIC_FLAGS)

    def test_hook_metadata_native_hash_and_standalone_boundaries(self):
        bundle = self.bundle(800, 600)
        self.assertEqual(len(bundle.hook_sites), 1)
        hook = bundle.hook_sites[0]
        self.assertEqual((hook.va, hook.rva, hook.offset, hook.old_bytes, hook.fallback_va, hook.removed_highlow_vas),
                         (0x406740, 0x6740, 0x5B40, bytes.fromhex("5351525657"), 0x406745, ()))
        self.assertEqual(hook.entry_va, bundle.entries["native_frame_entry"])
        self.assertTrue(set(bundle.status_vas) >= {"native_admission", "native_draw", "native_present"})
        self.assertFalse(bundle.native_contract["return_eax_is_native_success"])
        self.assertFalse(bundle.native_contract["primary_pixels_offset_4_required"])
        self.assertFalse(bundle.native_contract["backend_pixels_before_lock_required"])
        self.assertEqual(bundle.native_contract["com_methods_required"], [0x64, 0x6C, 0x80])
        self.assertTrue(bundle.native_contract["full_render_tail_must_preserve_primary_tooltip"])
        changed = bytearray(self.original)
        changed[hook.offset] ^= 1
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            presentation.emit_framed_presentation(bytes(changed), base_va=runner.BASE, width=800, height=600)


if __name__ == "__main__":
    unittest.main()
