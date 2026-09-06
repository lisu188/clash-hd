#!/usr/bin/env python3
"""Execute only emitted minimap x86 in synthetic memory; no game or debugger."""
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
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher import framed_minimap as minimap
from src.patcher import partial_tile_clip as clip
import test_partial_tile_clip as runner
import test_four_sided_frame_x86 as common

RESOLUTIONS = common.RESOLUTIONS
DELTAS = (0, 0x02000000)
PRIMARY = runner.BASE + 0x15000
BACKING = runner.BASE + 0x17000
CLIPPED_TABLE = runner.BASE + 0x14000
CONTINUATION = runner.BASE + 0xA000
FALLBACK = runner.BASE + 0xA100
BRIDGE = runner.BASE + 0xA200
FLAGS = runner.GLOBAL + 144


def fixture_source() -> str:
    source = common.fixture_source()
    setup = r'''
    int width=I(root["width"]),height=I(root["height"]);
    if(Get(c,"native640",0)!=0){width=640;height=480;W(Surface,width|(height<<16));}
    int worldW=Get(c,"map_width",100),worldH=Get(c,"map_height",100),scale=Get(c,"scale",2);
    W(GameData+0x222E0,worldW);W(GameData+0x222E4,worldH);
    int boxW=worldW*scale+14,boxH=worldH*scale+14;
    W(Global+128,Get(c,"origin_x",width-32-boxW) | (Get(c,"origin_y",16)<<16));
    W(Global+132,Get(c,"box_width",boxW) | (Get(c,"box_height",boxH)<<16));
    W(Global+136,Get(c,"backing_pointer",B+0x17000));W(Global+140,scale);
    W(B+0x17000,Get(c,"backing_width",boxW) | (Get(c,"backing_height",boxH)<<16));
    W(B+0x17004,Get(c,"backing_pixels",B+0x19000));
    W(B+0x170B8,Get(c,"backing_table",0x50ee24+delta));
    W(GameData+0x23EC7,Get(c,"minimap_selector",0));
    for(int playerIndex=0;playerIndex<5;playerIndex++)W(GameData+0x2230F+playerIndex*0x58F,Get(c,"minimap_enabled",1));
    int primary=B+0x15000;
    W(primary,Get(c,"primary_width",width) | (Get(c,"primary_height",height)<<16));
    W(primary+4,0);W(primary+0xB8,Get(c,"primary_table",0x50eec4+delta));
    W(primary+0xD4,Get(c,"primary_depth",8));W(primary+0xBC,Get(c,"primary_backend",B+0x16000));
    W(B+0x16000+0xA4,Get(c,"com_surface",B+0x16100));W(B+0x16100,Get(c,"com_table",B+0x16200));
    W(B+0x16200+0x64,Get(c,"com_lock",B+0x16300));
    W(B+0x16200+0x6C,Get(c,"com_restore",B+0x16300));
    W(B+0x16200+0x80,Get(c,"com_unlock",B+0x16300));
    W(B+0x16000+0x48,Get(c,"primary_pitch",width));
    W(B+0x16000+0x5C,Get(c,"primary_pixels",B+0x18000));
    W(Global+8,Get(c,"primary",0)!=0?primary:Surface);
    if(c.ContainsKey("target_override"))W(Global+8,I(c["target_override"]));
'''
    anchor = '    var regs=(IList)c["regs"];var args=(IList)c["args"];'
    return common.replace_once(source, anchor, setup + anchor)


def draw_stub(kind: int, delta: int) -> bytes:
    record = runner.recorder(kind, 2, delta=delta)
    owner = b"\xa1" + struct.pack("<I", runner.GLOBAL + 16 + delta) + bytes.fromhex("89473c")
    observed_flags = b"\xa1" + struct.pack("<I", FLAGS + delta) + bytes.fromhex("89473c")
    if record.count(owner) != 1 or not record.endswith(bytes.fromhex("c20800")):
        raise AssertionError("shared native recorder changed")
    out = bytearray.fromhex("9c8f05") + struct.pack("<I", FLAGS + delta)
    out += record.replace(owner, observed_flags)[:-3]
    # Callee cleans its two arguments, but damages all ordinary GPR, flags and
    # render global. The emitted helper must retain its independent frame.
    for opcode in (0xB8, 0xBB, 0xB9, 0xBA, 0xBE, 0xBF, 0xBD):
        out += bytes([opcode]) + struct.pack("<I", 0xDEADBEEF)
    out += bytes.fromhex("c705") + struct.pack("<II", runner.GLOBAL + 8 + delta, 0xBAD00000)
    out += bytes.fromhex("68010200009dfdc20800")
    return bytes(out)


def oracle(width, height, case):
    # Independent rational interval projection, not production viewport_rect.
    worldW, worldH = case.get("map_width", 100), case.get("map_height", 100)
    sx, sy, scale = case.get("scroll_x", 10), case.get("scroll_y", 17), case.get("scale", 2)
    origin = (width - 32 - (worldW * scale + 14), 16)
    result = []
    for length, world, scroll, anchor in zip((width - 64, height - 32), (worldW, worldH), (sx, sy), origin):
        numerator = min(length, 64 * (world - scroll)) * scale
        whole, remainder = divmod(numerator, 64)
        interior = whole + (1 if remainder else 0)
        start = anchor + 6 + scroll * scale
        result.append((start, start + 1 + interior))
    return result[0][0], result[1][0], result[0][1], result[1][1]


class GeometryTests(unittest.TestCase):
    def test_fractional_projection_native_and_world_edges(self):
        for width, height in RESOLUTIONS:
            for worldW, worldH, scale in ((100, 100, 2), (50, 50, 4), (100, 25, 4), (1, 1, 4)):
                for sx, sy in ((0, 0), (max(0, worldW - (width - 64)//64), max(0, worldH - (height - 32)//64))):
                    args = dict(width=width, height=height, world_width=worldW, world_height=worldH,
                                scroll_x=sx, scroll_y=sy, scale=scale,
                                origin_x=width-32-(worldW*scale+14), origin_y=16)
                    case = dict(map_width=worldW, map_height=worldH, scale=scale, scroll_x=sx, scroll_y=sy)
                    self.assertEqual(minimap.viewport_rect(**args), oracle(width, height, case))
        # The802px custom viewport is23.0625 mini pixels atscale2:24, not24*2.
        case = dict(scroll_x=0, scroll_y=0)
        l, t, r, b = oracle(802, 602, case)
        self.assertEqual((r-l-1, b-t-1), (24, 18))
        native = minimap.viewport_rect(width=640, height=480, world_width=100, world_height=100,
                                       scroll_x=0, scroll_y=0, scale=2, origin_x=394, origin_y=16)
        self.assertEqual(native, (400, 22, 419, 37))

    def test_invalid_geometry_and_signed_state(self):
        args = dict(width=800, height=600, world_width=100, world_height=100,
                    scroll_x=0, scroll_y=0, scale=2, origin_x=554, origin_y=16)
        for bad in ({"world_width":0}, {"world_height":101}, {"scroll_x":-1}, {"scroll_y":2**31},
                    {"scale":1}, {"scale":True}, {"origin_x":553}, {"origin_y":17}, {"width":801}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                minimap.viewport_rect(**dict(args, **bad))


@unittest.skipUnless(os.name == "nt" and runner.CSC.is_file() and runner.ORIGINAL.is_file(),
                     "requires x86 compiler and user-owned original for synthetic execution")
class EmittedMinimapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="framed-minimap-x86-")
        cls.addClassCleanup(cls.temp.cleanup)
        source = Path(cls.temp.name) / "fixture.cs"
        cls.exe = Path(cls.temp.name) / "fixture.exe"
        source.write_text(fixture_source(), encoding="utf-8")
        result = subprocess.run([str(runner.CSC), "/nologo", "/platform:x86", "/r:System.Web.Extensions.dll",
                                 "/out:" + str(cls.exe), str(source)], capture_output=True, text=True,
                                timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.original = runner.ORIGINAL.read_bytes()
        cls.bundles = {}

    def bundle(self, width, height):
        if (width, height) not in self.bundles:
            self.bundles[width, height] = minimap.emit_minimap_bundle(
                self.original, base_va=runner.BASE, width=width, height=height, clipped_vtable_va=CLIPPED_TABLE)
        return self.bundles[width, height]

    def execute(self, width, height, cases, delta=0):
        bundle = self.bundle(width, height)
        code = bytearray(bundle.code)
        self.assertLess(len(code), 0x6000)
        targets = {"map_surface_global":runner.GLOBAL, "game_data_global":runner.GLOBAL+4,
                   "replayed_game_data_global":runner.GLOBAL+4, "render_device_global":runner.GLOBAL+8,
                   "primary_surface":PRIMARY, "minimap_origin":runner.GLOBAL+128,
                   "minimap_top":runner.GLOBAL+130, "minimap_size":runner.GLOBAL+132,
                   "minimap_height":runner.GLOBAL+134, "minimap_backing":runner.GLOBAL+136,
                   "minimap_scale":runner.GLOBAL+140}
        natives = {"memory_outline":runner.STUBS["line"], "primary_outline":runner.STUBS["fill"],
                   "native_outline_continuation":CONTINUATION, "native_outline_fallback":FALLBACK}
        clip.absolute_relocation_offsets(bundle)
        for relocation in bundle.relocations:
            if relocation.kind == "abs32":
                value = targets.get(relocation.purpose, relocation.target) + delta
                struct.pack_into("<I", code, relocation.offset, value)
            else:
                self.assertIn(relocation.purpose, natives)
                struct.pack_into("<i", code, relocation.offset, natives[relocation.purpose] - (runner.BASE+relocation.offset+4))
        # A synthetic native stack: actual40D560 saves ESI/EBP then EDI before
        # its backing call and hook. The continuation pops exactly those three.
        bridge = bytes.fromhex("565557e9") + struct.pack("<i", bundle.entries["native_outline_hook"]-(BRIDGE+8))
        # Preserve entry flags around the synthetic observer so final flags
        # check the wrapper's state at the native fallback transfer. Actual
        # native geometry changes flags later and has no preserving contract.
        fallback = b"\x9c" + runner.recorder(99, 0, delta=delta)[:-3] + bytes.fromhex("9d5f5d5ec3")
        payload = dict(base=runner.BASE+delta, image_delta=delta, width=width, height=height, code=code.hex(),
                       stubs={str(runner.STUBS["line"]+delta):draw_stub(1,delta).hex(),
                              str(runner.STUBS["fill"]+delta):draw_stub(2,delta).hex(),
                              str(CONTINUATION+delta):"5f5d5ec3", str(FALLBACK+delta):fallback.hex(),
                              str(BRIDGE+delta):bridge.hex()},
                       cases=[dict(case, entry=(BRIDGE if case.get("hook") else bundle.entries["draw_viewport_outline"])+delta,
                                   regs=common.INPUT_REGS, args=[]) for case in cases])
        result = subprocess.run([str(self.exe)], input=json.dumps(payload), capture_output=True, text=True,
                                timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        reports = json.loads(result.stdout)
        for case, report in zip(cases, reports):
            state = report["state"]
            self.assertEqual(state[1:4], [0x11223344,0x55667788,0x99AABBCC])
            self.assertEqual(state[4],state[5], "native return stack differs")
            self.assertEqual(state[6:9],common.INPUT_REGS[1:])
            self.assertEqual(state[9] & (common.ARITHMETIC_FLAGS|common.DIRECTION_FLAG),
                             case.get("initial_flags",common.INITIAL_FLAGS) & (common.ARITHMETIC_FLAGS|common.DIRECTION_FLAG))
            self.assertEqual(report["render"], case.get("target_override", (PRIMARY if case.get("primary") else runner.SURFACE)+delta))
        return reports

    def check_draw(self, report, width, height, case, delta):
        self.assertEqual(report["state"][0], common.INPUT_REGS[0] if case.get("hook") else 1)
        self.assertEqual(len(report["records"]),1)
        record=report["records"][0]
        l,t,r,b=oracle(width,height,case)
        self.assertEqual(record[:7], [2 if case.get("primary") else 1,
                                     (PRIMARY if case.get("primary") else runner.SURFACE)+delta,t,r,l,b,0x4C])
        self.assertEqual(record[7:12],[0]*5)
        self.assertEqual(record[13],(PRIMARY if case.get("primary") else runner.SURFACE)+delta)
        self.assertEqual(record[15] & common.DIRECTION_FLAG,0)
        self.assertTrue(32<=l<r<width-32 and 16<=t<b<height-16)

    def test_scales_world_edges_six_sizes_targets_rebase_and_destructive_callee(self):
        for width,height in RESOLUTIONS:
            for delta in DELTAS:
                cases=[]
                for worldW,worldH,scale in ((100,100,2),(50,50,4),(100,25,4),(1,1,4)):
                    for sx,sy in ((0,0),(max(0,worldW-(width-64)//64),max(0,worldH-(height-32)//64))):
                        for primary in (0,1):
                            cases.append(dict(map_width=worldW,map_height=worldH,scale=scale,scroll_x=sx,scroll_y=sy,
                                              primary=primary,initial_flags=common.INITIAL_FLAGS|common.DIRECTION_FLAG))
                with self.subTest(size=(width,height),delta=delta):
                    for case,report in zip(cases,self.execute(width,height,cases,delta)):
                        self.check_draw(report,width,height,case,delta)

    def test_invalid_state_rejects_before_first_draw(self):
        negatives=[{"bad":"game_data"},{"bad":"pixels"},{"bad":"dimensions"},{"initial_vtable":0x12345678},
                   {"map_width":0},{"map_width":101},{"map_height":-1},{"scroll_x":-1},{"scroll_y":2**31},
                   {"scroll_x":100},{"scroll_y":93},{"minimap_selector":-1},{"minimap_selector":5},
                   {"minimap_enabled":0},{"scale":0},{"scale":1},{"scale":3},{"scale":4},
                   {"origin_x":0},{"origin_x":555},{"origin_y":17},{"box_width":213},{"box_height":215},
                   {"backing_width":213},{"backing_height":213},{"backing_pixels":0},{"backing_pointer":0},
                   {"backing_table":0x50eec4},{"target_override":0},{"target_override":runner.SURFACE+4}]
        primary=[{"primary":1,**bad} for bad in ({"primary_depth":16},{"primary_table":0x50ee24},
                    {"primary_width":799},{"primary_backend":0},{"com_surface":0},{"com_table":0},
                    {"com_lock":0},{"com_restore":0},{"com_unlock":0},{"primary_pixels":0},
                    {"primary_pitch":799},{"primary_pitch":-1},{"primary_pitch":65537},
                    {"primary_pixels":0xFFFFFF00})]
        for delta in DELTAS:
            cases=negatives+primary+[{"backing_pointer":runner.SURFACE+delta},{"backing_pointer":PRIMARY+delta}]
            for case,report in zip(cases,self.execute(800,600,cases,delta)):
                with self.subTest(case=case,delta=delta):
                    self.assertEqual(report["state"][0],0)
                    self.assertEqual(report["records"],[])

    def test_explicit_clipped_table_and_disabled_other_player(self):
        for delta in DELTAS:
            cases=[{"initial_vtable":CLIPPED_TABLE+delta}, {"minimap_selector":4},
                   {"primary":1,"primary_pitch":1024}]
            for case,report in zip(cases,self.execute(800,600,cases,delta)):
                self.check_draw(report,800,600,case,delta)
        original=bytearray(self.original);original[0]^=1
        with self.assertRaises(ValueError):
            minimap.emit_minimap_bundle(bytes(original),base_va=runner.BASE,width=800,height=600)
        for value in (True,0,-1,clip.MEMORY_VTABLE,0x80000000):
            with self.subTest(value=value),self.assertRaises(ValueError):
                minimap.emit_minimap_bundle(self.original,base_va=runner.BASE,width=800,height=600,clipped_vtable_va=value)

    def test_hook_exact_relocation_source_bytes_native_fallback_and_skip(self):
        bundle=self.bundle(800,600);hook=bundle.hook_sites[0]
        self.assertFalse(bundle.installation_ready)
        self.assertEqual(len(bundle.hook_sites),1)
        self.assertEqual((hook.va,hook.offset,hook.old_bytes,hook.removed_highlow_vas),
                         (0x40D633,0xCA33,bytes.fromhex("a1e4025200"),(0x40D634,)))
        self.assertEqual(hook.va+5+struct.unpack_from("<i",hook.new_bytes,1)[0],bundle.entries["native_outline_hook"])
        self.assertEqual(hook.relocations,(clip.Relocation(1,"rel32",hook.entry_va,"native_outline_hook"),))
        for target,entry in bundle.native_contract["observers"].items():
            self.assertEqual(bundle.code[entry-bundle.base_va],0xE8)
            expected=0x404040 if target=="memory" else 0x404560
            self.assertEqual(entry+5+struct.unpack_from("<i",bundle.code,entry-bundle.base_va+1)[0],expected)
        self.assertEqual(clip._original_highlow_fields(self.original,hook.va,5),{1})
        for delta in DELTAS:
            cases=[{"hook":1},{"hook":1,"primary":1},{"hook":1,"scale":3},{"native640":1},
                   {"hook":1,"native640":1},{"hook":1,"native640":1,"primary":1},
                   {"native640":1,"bad":"game_data"}]
            reports=self.execute(800,600,cases,delta)
            for case,report in zip(cases[:2],reports[:2]):self.check_draw(report,800,600,case,delta)
            self.assertEqual(reports[2]["records"],[])
            self.assertEqual(reports[2]["state"][0],common.INPUT_REGS[0])
            self.assertEqual(reports[3]["state"][0],2);self.assertEqual(reports[3]["records"],[])
            for report in reports[4:6]:
                self.assertEqual(report["records"][0][0],99)
                self.assertEqual(report["records"][0][1],runner.GAME_DATA+delta)
            self.assertEqual(reports[6]["state"][0],0)
        with patch.object(minimap,"NATIVE_CONTRACTS",((0x40D560,0x16A,"0"*64),)):
            with self.assertRaisesRegex(ValueError,"source contract"):
                minimap.emit_minimap_bundle(self.original,base_va=runner.BASE,width=800,height=600)


if __name__ == "__main__":
    unittest.main()
