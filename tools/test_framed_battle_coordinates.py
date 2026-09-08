"""Execute uninstalled coordinate x86 in synthetic memory, never a game image.

The original and reconstructed candidate are read only/in-memory prerequisites.
Only an isolated no-window C# fixture is compiled and run. It checks actual
return registers, stack, EFLAGS, memory canaries and rebased global operands.
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
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher import framed_battle_coordinates as coords
from src.patcher import partial_tile_clip as clip
from tools import build_framed_modal_candidate as builder
import test_partial_tile_clip as runner

RESOLUTIONS = ((800, 600), (1024, 768), (1280, 720), (1280, 960),
               (1920, 1080), (802, 602))
CAPACITIES = (9, 13, 17, 17, 27, 9)
DELTAS = (0, 0x02000000)
STATE = runner.BASE + 0x17000
OWNER_GLOBAL = runner.GLOBAL + 0x100
STATE_GLOBAL = runner.GLOBAL + 0x104
FLAGS_MASK = 0xCD5  # Arithmetic flags and DF; OS controls privileged bits.


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise AssertionError("shared synthetic harness contract changed: " + old)
    return source.replace(old, new)


def fixture_source():
    source = runner.CSHARP
    setup = r'''
    int battle=B+0x17000;
    byte[] guarded=new byte[1024];for(int z=0;z<guarded.Length;z++)guarded[z]=0xA5;
    Bytes(battle,guarded);
    W(battle+800,Get(c,"rows",7));W(battle+804,Get(c,"columns",20));
    W(battle+808,Get(c,"battle_scroll",0));W(battle+812,Get(c,"battle_y",0));
    int owner=Get(c,"battle_owner",0x42E8B0+delta);
    int pointer=Get(c,"global_pointer",battle);
    W(Global+0x100,owner);W(Global+0x104,pointer);
    Marshal.Copy((IntPtr)battle,guarded,0,guarded.Length);
'''
    source = replace_once(source, '    var regs=(IList)c["regs"];var args=(IList)c["args"];',
                          setup + '    var regs=(IList)c["regs"];var args=(IList)c["args"];')
    anchor = '    var b=new List<byte>();b.AddRange(new byte[]{0x53,0x56,0x57,0x55});'
    source = replace_once(source, anchor, anchor + r'''
    b.Add(0x68);Imm(b,unchecked((int)0xC1234567));
    b.Add(0x68);Imm(b,unchecked((int)0xD7654321));''')
    anchor = '    b.Add(0xE8);Imm(b,I(c["entry"])-(B+0x8000+b.Count+4));'
    source = replace_once(source, anchor,
                          '    b.Add(0x68);Imm(b,Get(c,"flags",0xAD7));b.Add(0x9D);\n' + anchor)
    anchor = '    b.AddRange(new byte[]{0x5D,0x5F,0x5E,0x5B,0xC3});Bytes(B+0x8000,b.ToArray());'
    source = replace_once(source, anchor, r'''
    b.AddRange(new byte[]{0x9c,0x8f,0x05});Imm(b,Output+16);b.Add(0xFC);
    b.AddRange(new byte[]{0x8b,0x04,0x24});Save(b,0x05,Output+40);
    b.AddRange(new byte[]{0x8b,0x44,0x24,0x04});Save(b,0x05,Output+44);
    b.AddRange(new byte[]{0x83,0xc4,0x08});
''' + anchor)
    anchor = '    int count=Marshal.ReadInt32((IntPtr)Record);'
    check = r'''
    for(int z=0;z<guarded.Length;z++)
     if(Marshal.ReadByte((IntPtr)(battle+z))!=guarded[z])throw new Exception("Battle state/canary mutation");
    if(Marshal.ReadInt32((IntPtr)(Global+0x100))!=owner || Marshal.ReadInt32((IntPtr)(Global+0x104))!=pointer)
     throw new Exception("Battle globals changed");
'''
    source = replace_once(source, anchor, check + anchor)
    source = replace_once(source, 'new int[]{0,4,8,12,20,24,28,32,36}',
                          'new int[]{0,4,8,12,20,24,28,32,36,16,40,44}')
    return source


@unittest.skipUnless(os.name == "nt" and runner.CSC.is_file() and runner.ORIGINAL.is_file(),
                     "requires existing x86 fixture compiler and original for authentication")
class EmittedBattleCoordinates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="clash-battle-coordinate-x86-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.exe = Path(cls.temp.name) / "fixture.exe"
        source = Path(cls.temp.name) / "fixture.cs"
        source.write_text(fixture_source(), encoding="utf-8")
        result = subprocess.run([str(runner.CSC), "/nologo", "/platform:x86", "/optimize+",
                                 "/r:System.Web.Extensions.dll", f"/out:{cls.exe}", str(source)],
                                capture_output=True, text=True, timeout=60,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.original = runner.ORIGINAL.read_bytes()
        cls.candidates = {}
        cls.bundles = {}

    @classmethod
    def candidate(cls, width, height, minimap=True):
        key = width, height, minimap
        if key not in cls.candidates:
            cls.candidates[key] = builder.build_candidate(
                cls.original, f"{width}x{height}", minimap_viewport=minimap)[0]
        return cls.candidates[key]

    @classmethod
    def bundle(cls, width, height, minimap=True):
        key = width, height, minimap
        if key not in cls.bundles:
            cls.bundles[key] = coords.emit_battle_coordinates(
                cls.original, cls.candidate(width, height, minimap), base_va=runner.BASE,
                width=width, height=height, minimap_viewport=minimap)
        return cls.bundles[key]

    def execute(self, width, height, cases, delta=0):
        bundle = self.bundle(width, height)
        self.assertFalse(bundle.installation_ready)
        self.assertLess(len(bundle.code), 0x6000)
        self.assertEqual(set(bundle.entries), {"visible_columns", "clamp_scroll_x",
                                             "visible_world_cell", "screen_to_cell"})
        code = bytearray(bundle.code)
        targets = {"battle_state_global": STATE_GLOBAL,
                   "battle_render_owner": OWNER_GLOBAL,
                   "native_battle_owner": coords.BATTLE_OWNER}
        for relocation in bundle.relocations:
            self.assertEqual(relocation.kind, "abs32")
            struct.pack_into("<I", code, relocation.offset, targets[relocation.purpose] + delta)
        prepared = []
        for case in cases:
            prepared.append(dict(case, entry=bundle.entries[case["helper"]] + delta,
                                 regs=[case.get("state_pointer", STATE + delta), 0x22334455,
                                       case.get("y", 0), case.get("x", 0)], args=[]))
        payload = dict(base=runner.BASE + delta, image_delta=delta, width=width, height=height,
                       code=code.hex(), stubs={}, cases=prepared)
        result = subprocess.run([str(self.exe)], input=json.dumps(payload), capture_output=True,
                                text=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        reports = json.loads(result.stdout)
        self.assertEqual(len(reports), len(cases))
        for case, report in zip(cases, reports):
            state = report["state"]
            self.assertEqual(report["records"], [], "coordinate helper called a native recorder")
            self.assertEqual(state[1:4], [0x11223344, 0x55667788, 0x99AABBCC])
            self.assertEqual(state[4], state[5], "caller stack differs")
            self.assertEqual(state[6:9], [0x22334455, case.get("y", 0) & 0xFFFFFFFF,
                                         case.get("x", 0) & 0xFFFFFFFF])
            self.assertEqual(state[9] & FLAGS_MASK, case.get("flags", 0xAD7) & FLAGS_MASK)
            self.assertEqual(state[10:12], [0xD7654321, 0xC1234567])
            self.assertEqual(state[0], case["expected"], str(case))
        return reports

    def test_all_resolutions_small_worlds_and_signed_clamps(self):
        for (width, height), capacity in zip(RESOLUTIONS, CAPACITIES):
            cases = []
            for world in range(1, 21):
                visible = min(world, capacity)
                cases.append(dict(helper="visible_columns", columns=world, expected=visible))
                for requested in (-0x80000000, -1, 0, 1, world - visible, world, 0x7FFFFFFF):
                    cases.append(dict(helper="clamp_scroll_x", columns=world, x=requested,
                                      battle_scroll=-123, flags=0xED7,
                                      expected=max(0, min(requested, world - visible))))
            for delta in DELTAS:
                with self.subTest(resolution=(width, height), delta=delta):
                    self.execute(width, height, cases, delta)

    def test_world_cell_visibility_and_every_cell_screen_corners(self):
        for (width, height), capacity in zip(RESOLUTIONS, CAPACITIES):
            cases = []
            for world in (1, 7, 20):
                visible = min(world, capacity)
                for scroll in sorted({0, world - visible}):
                    for column in range(world):
                        for row in range(7):
                            shown = scroll <= column < scroll + visible
                            cases.append(dict(helper="visible_world_cell", columns=world,
                                              battle_scroll=scroll, x=column, y=row, expected=int(shown)))
                            if shown:
                                for dx, dy in ((0, 0), (63, 63)):
                                    cases.append(dict(helper="screen_to_cell", columns=world,
                                                      battle_scroll=scroll,
                                                      x=32 + (column - scroll) * 64 + dx,
                                                      y=16 + row * 64 + dy,
                                                      expected=column | (row << 16), flags=0xED7))
            for delta in DELTAS:
                self.execute(width, height, cases, delta)

    def test_field_padding_hud_and_extreme_pixels_reject_before_index(self):
        for (width, height), capacity in zip(RESOLUTIONS, CAPACITIES):
            right = 32 + 64 * min(20, capacity)
            points = [(-0x80000000, 16), (-1, 16), (0, 16), (31, 16),
                      (32, -0x80000000), (32, -1), (32, 0), (32, 15),
                      (right, 16), (32, 464), (width - 160, 16), (width - 1, height - 1),
                      (0x7FFFFFFF, 16), (32, 0x7FFFFFFF)]
            if right < width - 160:
                points.append(((right + width - 160) // 2, 32))
            cases = [dict(helper="screen_to_cell", x=x, y=y, expected=coords.REJECT) for x, y in points]
            cases += [dict(helper="visible_world_cell", x=x, y=y, expected=coords.REJECT)
                      for x, y in ((-1, 0), (20, 0), (0, -1), (0, 7),
                                   (0x7FFFFFFF, 0), (0, 0x7FFFFFFF))]
            self.execute(width, height, cases, DELTAS[1])

    def test_invalid_context_null_pointer_owner_and_bounds_fail_closed(self):
        helpers = tuple(self.bundle(1024, 768).entries)
        invalid = [{"rows": 0}, {"rows": 8}, {"columns": 0}, {"columns": -1},
                   {"columns": 21}, {"columns": 0x7FFFFFFF}, {"battle_y": 1}, {"battle_y": -1},
                   {"state_pointer": 0}, {"state_pointer": 1, "global_pointer": 1},
                   {"state_pointer": 0x80000000, "global_pointer": 0x80000000},
                   {"state_pointer": 0x7FFFFCD4, "global_pointer": 0x7FFFFCD4},
                   {"state_pointer": 0x10001, "global_pointer": 0x10001},
                   {"global_pointer": 0}, {"battle_owner": 0},
                   {"battle_owner": 0x40AD40},
                   {"state_pointer": 0x12345678, "global_pointer": 0x12345678, "battle_owner": 0}]
        cases = [dict(bad, helper=helper, x=32, y=16, expected=coords.REJECT)
                 for bad in invalid for helper in helpers]
        cases += [dict(helper=helper, x=32, y=16, battle_scroll=scroll, expected=coords.REJECT)
                  for helper in ("screen_to_cell", "visible_world_cell") for scroll in (-1, 8, 0x7FFFFFFF)]
        for delta in DELTAS:
            self.execute(1024, 768, cases, delta)

    def test_whole_candidate_original_sources_and_variant_are_authenticated(self):
        candidate = self.candidate(1024, 768)
        self.assertEqual(hashlib.sha256(candidate).hexdigest(),
                         "c09940fac48e903538dd3a35688efb5ca5a65edaa6ad42cf6c804ca1c008d18d")
        bundle = self.bundle(1024, 768)
        self.assertEqual(bundle.candidate_sha256, hashlib.sha256(candidate).hexdigest())
        self.assertTrue(bundle.source_contract["candidate_reconstructed"])
        self.assertFalse(bundle.source_contract["writes_game_state"])
        self.assertFalse(bundle.source_contract["installed"])
        mutated = bytearray(candidate); mutated[-1] ^= 1
        for supplied, minimap in ((bytes(mutated), True), (candidate, False)):
            with self.assertRaises(ValueError):
                coords.emit_battle_coordinates(self.original, supplied, base_va=runner.BASE,
                                               width=1024, height=768, minimap_viewport=minimap)
        changed = bytearray(self.original); changed[0] ^= 1
        with self.assertRaises(ValueError):
            coords.emit_battle_coordinates(bytes(changed), candidate, base_va=runner.BASE,
                                           width=1024, height=768)
        with patch.dict(coords.PINNED_SOURCES, {"tools/build_framed_modal_candidate.py": "0" * 64}):
            with self.assertRaises(ValueError):
                coords.emit_battle_coordinates(self.original, candidate, base_va=runner.BASE,
                                               width=1024, height=768)
        plain = self.bundle(800, 600, False)
        self.assertFalse(plain.source_contract["minimap_viewport"])
        self.assertNotEqual(plain.candidate_sha256, self.bundle(800, 600).candidate_sha256)

    def test_invalid_api_and_declared_absolute_fields(self):
        candidate = self.candidate(800, 600)
        for base in (True, 0, -1, 0x80000000):
            with self.assertRaises(ValueError):
                coords.emit_battle_coordinates(self.original, candidate, base_va=base, width=800, height=600)
        for width, height in ((True, 600), (639, 480), (800, 479), (801, 600)):
            with self.assertRaises(ValueError):
                coords.emit_battle_coordinates(self.original, candidate, base_va=runner.BASE,
                                               width=width, height=height)
        with self.assertRaises(ValueError):
            coords.emit_battle_coordinates(self.original, candidate, base_va=runner.BASE,
                                           width=800, height=600, minimap_viewport=1)
        bundle = self.bundle(800, 600)
        self.assertEqual(len(clip.absolute_relocation_offsets(bundle)), 12)
        self.assertEqual({r.target for r in bundle.relocations},
                         {coords.BATTLE_STATE, coords.RENDER_OWNER, coords.BATTLE_OWNER})


if __name__ == "__main__":
    unittest.main()
