#!/usr/bin/env python3
"""Execute only the standalone frame helper in synthetic x86 memory.

The user-owned original is read solely for byte authentication. No game,
debugger, wrapper, window, input, image or candidate is launched or written.
Temporary compiler/fixture binaries use the existing no-window ABI harness.
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
from src.patcher import four_sided_frame as frame
from src.patcher import partial_tile_clip as clip
from src.patcher.framed_viewport import FramedViewport
import test_partial_tile_clip as runner


RESOLUTIONS = ((640, 480), (800, 600), (1024, 768), (1280, 720),
               (1280, 960), (1920, 1080), (802, 602))
DELTAS = (0, 0x02000000, 0x04000000)
FRAME_GLOBAL = runner.GLOBAL + 64
DRAW_RESULT = runner.GLOBAL + 68
DRAW_FLAGS = runner.GLOBAL + 72
ARITHMETIC_FLAGS = 0x8D5
DIRECTION_FLAG = 0x400
INITIAL_FLAGS = 0xAD7
INPUT_REGS = [0x12345678, 0x22334455, 0x33445566, 0x44556677]

# Independent literal resource dimensions: S32 encodes width first, then
# height. Native406260 copies the first10bytes unchanged into the descriptor.
# Decompiler getter names are not the header contract. Index4 is not required.
HEADERS = {0: (314, 237), 1: (326, 238), 2: (315, 243), 3: (325, 242), 5: (324, 15)}


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise AssertionError("shared synthetic harness contract changed: " + old)
    return source.replace(old, new)


def fixture_source() -> str:
    """Extend only the temporary C# harness, preserving its guard checks."""
    source = runner.CSHARP
    setup = r'''
    // Synthetic live FRAME pointer table and actual width-low/height-high headers.
    W(Global+64,Sprite);W(Global+68,Get(c,"native_result",0x13572468));
    for(int i=0;i<6;i++)W(Sprite+4*i,0);
    int[] ids=new int[]{0,1,2,3,5};
    int[] widths=new int[]{314,326,315,325,324};
    int[] heights=new int[]{237,238,243,242,15};
    for(int i=0;i<ids.Length;i++){
     int index=ids[i],header=Sprite+0x100+0x100*index;
     W(Sprite+4*index,header);W(header,widths[i] | (heights[i]<<16));
     W(header+4,0);W(header+0x0A,Sprite+0x800+32*index);
     if(Get(c,"null_sprite",-1)==index)W(Sprite+4*index,0);
     if(Get(c,"wrong_width",-1)==index)W(header,(widths[i]+1) | (heights[i]<<16));
     if(Get(c,"wrong_height",-1)==index)W(header,widths[i] | ((heights[i]+1)<<16));
     if(Get(c,"transposed_header",-1)==index)W(header,heights[i] | (widths[i]<<16));
     if(Get(c,"bad_encoding",-1)==index)W(header+4,1);
     if(Get(c,"zero_stream",-1)==index)W(header+0x0A,0);
    }
    if(Get(c,"null_table",0)!=0)W(Global+64,0);
    if(Get(c,"null_target",0)!=0)W(Global,0);
    if(Get(c,"mapped_bad_target",0)!=0)W(Global,Surface+0x400);
    if(Get(c,"primary_target",0)!=0)W(Global,0x51d4c0+delta);
'''
    anchor = '    var regs=(IList)c["regs"];var args=(IList)c["args"];'
    source = replace_once(source, anchor, setup + anchor)
    anchor = '    b.Add(0xE8);Imm(b,I(c["entry"])-(B+0x8000+b.Count+4));'
    source = replace_once(source, anchor,
                          '    b.Add(0x68);Imm(b,Get(c,"initial_flags",0xAD7));b.Add(0x9D);\n' + anchor)
    anchor = "Save(b,0x15,Output+36);"
    source = replace_once(source, anchor, anchor +
                          "b.AddRange(new byte[]{0x9c,0x8f,0x05});Imm(b,Output+16);b.Add(0xFC);")
    source = replace_once(source, "new int[]{0,4,8,12,20,24,28,32,36}",
                          "new int[]{0,4,8,12,20,24,28,32,36,16}")
    return source


def destructive_sprite_stub(delta: int) -> bytes:
    # Record the actual incoming registers,7arguments and render/vtable state.
    # Then damage every GPR except ESP, arithmetic flags and the render global.
    result = runner.recorder(3, 7, delta=delta)
    # Capture flags without changing the incoming argument stack, then use the
    # recorder's last context field for these flags rather than lower-row owner.
    load_owner = b"\xa1" + struct.pack("<I", runner.GLOBAL + 16 + delta) + bytes.fromhex("89473c")
    load_flags = b"\xa1" + struct.pack("<I", DRAW_FLAGS + delta) + bytes.fromhex("89473c")
    if result.count(load_owner) != 1:
        raise AssertionError("shared recorder context field changed")
    result = bytes.fromhex("9c8f05") + struct.pack("<I", DRAW_FLAGS + delta) + result.replace(load_owner, load_flags)
    if not result.endswith(bytes.fromhex("c21c00")):
        raise AssertionError("shared sprite recorder cleanup changed")
    out = bytearray(result[:-3])
    for opcode, value in ((0xBB, 0xB0B0B0B0), (0xB9, 0xC0C0C0C0), (0xBA, 0xD0D0D0D0),
                          (0xBE, 0xE0E0E0E0), (0xBF, 0xF0F0F0F0), (0xBD, 0xA0A0A0A0)):
        out += bytes([opcode]) + struct.pack("<I", value)
    out += bytes.fromhex("c705") + struct.pack("<II", runner.GLOBAL + 8 + delta, 0xDEADF00D)
    out += bytes.fromhex("31c0f9fda1") + struct.pack("<I", DRAW_RESULT + delta)
    out += bytes.fromhex("c21c00")
    return bytes(out)


@unittest.skipUnless(os.name == "nt" and runner.CSC.is_file() and runner.ORIGINAL.is_file(),
                     "requires local x86 fixture compiler and original for byte authentication")
class FourSidedFrameX86Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="clash-four-frame-x86-fixture-")
        cls.addClassCleanup(cls.temp.cleanup)
        root = Path(cls.temp.name)
        cls.exe = root / "fixture.exe"
        source = root / "fixture.cs"
        source.write_text(fixture_source(), encoding="utf-8")
        compiled = subprocess.run([str(runner.CSC), "/nologo", "/platform:x86", "/optimize+",
                                   "/r:System.Web.Extensions.dll", f"/out:{cls.exe}", str(source)],
                                  capture_output=True, text=True, timeout=60,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        if compiled.returncode:
            raise AssertionError(compiled.stdout + compiled.stderr)
        cls.original = runner.ORIGINAL.read_bytes()
        clip.verify_original(cls.original)
        cls.bundles = {}

    def execute(self, width: int, height: int, cases: list[dict], *, delta: int):
        key = width, height
        if key not in self.bundles:
            self.bundles[key] = frame.emit_frame_helper(self.original, base_va=runner.BASE,
                                                       width=width, height=height)
        bundle = self.bundles[key]
        self.assertFalse(bundle.installation_ready)
        self.assertLess(len(bundle.code), 0x6000, "helper overlaps synthetic native stubs")
        code = bytearray(bundle.code)
        for offset in clip.absolute_relocation_offsets(bundle):
            value = struct.unpack_from("<I", code, offset)[0]
            struct.pack_into("<I", code, offset, value + delta)
        globals_by_purpose = {"map_surface_global": runner.GLOBAL,
                              "render_device_global": runner.GLOBAL + 8,
                              "frame_sprites_global": FRAME_GLOBAL}
        for relocation in bundle.relocations:
            if relocation.purpose in globals_by_purpose:
                self.assertEqual(relocation.kind, "abs32")
                struct.pack_into("<I", code, relocation.offset,
                                 globals_by_purpose[relocation.purpose] + delta)
            elif relocation.kind == "rel32":
                self.assertEqual(relocation.purpose, "sprite", "unrecorded native transfer")
                struct.pack_into("<i", code, relocation.offset,
                                 runner.STUBS["sprite"] - (runner.BASE + relocation.offset + 4))
            else:
                self.assertIn(relocation.purpose, ("memory_vtable", "primary_surface"))
        payload = dict(code=code.hex(), width=width, height=height, base=runner.BASE + delta,
                       image_delta=delta, stubs={str(runner.STUBS["sprite"] + delta): destructive_sprite_stub(delta).hex()},
                       cases=[dict(case, regs=INPUT_REGS, args=[],
                                   entry=bundle.entries["draw_frame"] + delta) for case in cases])
        execution = subprocess.run([str(self.exe)], input=json.dumps(payload), capture_output=True,
                                   text=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(execution.returncode, 0, execution.stdout + execution.stderr)
        reports = json.loads(execution.stdout)
        self.assertEqual(len(reports), len(cases))
        for case, report in zip(cases, reports):
            state = report["state"]
            self.assertEqual(state[1:4], [0x11223344, 0x55667788, 0x99AABBCC])
            self.assertEqual(state[6:9], INPUT_REGS[1:])
            self.assertEqual(state[4], state[5], "helper changed caller ESP")
            mask = ARITHMETIC_FLAGS | DIRECTION_FLAG
            self.assertEqual(state[9] & mask, case.get("initial_flags", INITIAL_FLAGS) & mask)
            self.assertEqual(report["render"], case.get("initial_render", 0x12345000))
            expected_vtable = (0x50EE74 if case.get("bad") == "vtable"
                               else case.get("initial_vtable", clip.MEMORY_VTABLE + delta))
            self.assertEqual(report["vtable"], expected_vtable)
        return reports

    def test_actual_native_call_abi_and_state_at_three_addresses(self):
        for width, height in RESOLUTIONS:
            for delta in DELTAS:
                with self.subTest(resolution=(width, height), delta=delta):
                    cases = [{"initial_render": saved, "native_result": returned, "initial_flags": flags}
                             for saved, returned, flags in ((0x12345000, 0, INITIAL_FLAGS),
                                                             (0, -1, 0x202),
                                                             (runner.SURFACE + delta, 0x13572468, 0x246),
                                                             (0x12345000, 0, INITIAL_FLAGS | DIRECTION_FLAG))]
                    reports = self.execute(width, height, cases, delta=delta)
                    plan = frame.frame_draw_plan(FramedViewport(width, height))
                    for report in reports:
                        self.assertEqual(report["state"][0], 1, "native draw EAX became helper success")
                        self.assertEqual(len(report["records"]), len(plan))
                        for record, draw in zip(report["records"], plan):
                            self.assertEqual(record[0], 3)
                            self.assertEqual(record[1:5], [runner.SURFACE + delta,
                                draw.x & 0xFFFFFFFF, draw.y & 0xFFFFFFFF,
                                runner.SPRITE + delta + 0x100 + 0x100 * draw.sprite])
                            self.assertEqual(record[5:12], [*draw.clip.as_tuple(), 1, 0, 0])
                            self.assertEqual(record[12:14], [clip.MEMORY_VTABLE + delta, runner.SURFACE + delta],
                                             "callee damage was not repaired before the next draw")
                            self.assertEqual(record[15] & DIRECTION_FLAG, 0, "native sprite called with DF set")
                        self.assertEqual(plan[-1].sprite, 5)
                        self.assertEqual(sum(draw.sprite == 5 for draw in plan), 1)

    def test_all_resource_rejections_happen_before_first_draw(self):
        cases = [{field: index} for index in HEADERS
                 for field in ("null_sprite", "wrong_width", "wrong_height", "transposed_header", "bad_encoding", "zero_stream")]
        cases.append({"null_table": 1})
        for width, height in RESOLUTIONS:
            for delta in DELTAS:
                with self.subTest(resolution=(width, height), delta=delta):
                    for case, report in zip(cases, self.execute(width, height, cases, delta=delta)):
                        self.assertEqual(report["state"][0], 0, case)
                        self.assertEqual(report["records"], [], case)

    def test_map_admission_rejections_preserve_entry_state_without_draw(self):
        cases = [{"null_target": 1}, {"mapped_bad_target": 1}, {"primary_target": 1},
                 {"bad": "global"}, {"bad": "dimensions"}, {"bad": "pixels"},
                 {"bad": "vtable"}, {"initial_vtable": 0}]
        for width, height in RESOLUTIONS:
            for delta in DELTAS:
                with self.subTest(resolution=(width, height), delta=delta):
                    for case, report in zip(cases, self.execute(width, height, cases, delta=delta)):
                        self.assertEqual(report["state"][0], 0, case)
                        self.assertEqual(report["records"], [], case)

    def test_original_and_admission_byte_contracts_remain_authenticated(self):
        self.assertEqual(hashlib.sha256(runner.ORIGINAL.read_bytes()).hexdigest(), clip.ORIGINAL_SHA256)
        changed = bytearray(self.original)
        changed[clip.file_offset(changed, 0x406260, 1)] ^= 1
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            frame.emit_frame_helper(bytes(changed), base_va=runner.BASE, width=800, height=600)
        self.assertEqual(hashlib.sha256(self.original).hexdigest(), clip.ORIGINAL_SHA256)


if __name__ == "__main__":
    unittest.main()
