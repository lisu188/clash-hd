"""Run uninstalled army drawing x86 against synthetic ABI recorders only.

No game, candidate, debugger, window, input or capture is executed. Source
images are read/in-memory prerequisites; only the existing no-window x86
fixture compiler/runner executes. Recorded native operations are checked
against independent sprite/number geometry and all frame/action-dock bounds.
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
from src.patcher import framed_army_draw as army
from src.patcher import partial_tile_clip as clip
from tools import build_framed_modal_candidate as builder
import test_partial_tile_clip as runner

RESOLUTIONS = ((800, 600), (1024, 768), (1280, 720), (1280, 960), (1920, 1080), (802, 602))
DELTAS = (0, 0x02000000)
VTABLE = runner.BASE + 0x13000
MARKS = runner.BASE + 0x14000
INFO = runner.BASE + 0x16000
FONT = runner.BASE + 0x18000
HEADERS = runner.BASE + 0x1A000
STUBS = {name: runner.BASE + 0x6000 + 0x200 * i for i, name in enumerate(
    ("army_sprite_lookup", "sprite", "army_number_text", "army_native_continue", "army_native_fallback"))}
TARGETS = runner.GLOBALS | {
    "army_selected": runner.GLOBAL + 0x100, "army_prior": runner.GLOBAL + 0x104,
    "army_unit": runner.GLOBAL + 0x108, "army_masks": runner.GLOBAL + 0x10C,
    "army_marks": runner.GLOBAL + 0x140, "army_info": runner.GLOBAL + 0x144,
    "army_font_pointer": runner.GLOBAL + 0x148, "army_font_index": runner.GLOBAL + 0x14C,
    "army_font7_entry": FONT, "army_font7_cache": FONT + 4,
    "army_number_format": FONT + 0x100, "memory_vtable": VTABLE,
    "map_render_hook_target": 0x40AD40,
}
TARGETS.update({"army_modal_state." + str(i): runner.BASE + 0x1C000 + i for i in (0, 8, 36, 52, 56)})


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise AssertionError("synthetic fixture source anchor changed: " + old)
    return text.replace(old, new)


def fixture_source():
    source = runner.CSHARP
    source = replace_once(source, "(UIntPtr)0x80000", "(UIntPtr)0x180000")
    setup = r'''
    int marks=B+0x14000,info=B+0x16000,font=B+0x18000,headers=B+0x1A000;
    int selected=Get(c,"selected",3),prior=Get(c,"prior",selected);
    int unit=GameData+147174+725*Get(c,"unit_index",selected>=0&&selected<500?selected:3);
    byte[] unitBytes=new byte[725];for(int z=0;z<unitBytes.Length;z++)unitBytes[z]=0xA5;
    Bytes(unit,unitBytes);Marshal.WriteByte((IntPtr)(unit+4),(byte)Get(c,"unit_owner",player));
    Marshal.WriteInt16((IntPtr)unit,(short)Get(c,"unit_x",16));
    Marshal.WriteInt16((IntPtr)(unit+2),(short)Get(c,"unit_y",19));
    foreach(int offset in new int[]{0,8,36,52,56})W(B+0x1C000+offset,0);
    if(c.ContainsKey("modal_field"))W(B+0x1C000+I(c["modal_field"]),1);
    int count=Get(c,"squads",8);
    for(int j=0;j<10;j++){
      Marshal.WriteInt16((IntPtr)(unit+31*j+6),(short)(j<count?(j%2==0?16:1):-1));
      Marshal.WriteByte((IntPtr)(unit+31*j+15),(byte)(7+j));
      Marshal.WriteByte((IntPtr)(unit+31*j+19),(byte)((j%2==0)?4:0));
      Marshal.WriteByte((IntPtr)(unit+31*j+14),(byte)(j%6));
      W(Global+0x10C+4*j,Get(c,"masks",1)==0?0:(j%3==0?1:0));
    }
    W(Global+0x100,selected);W(Global+0x104,prior);W(Global+0x108,unit);
    W(Global+0x140,marks);W(Global+0x144,info);W(Global+0x148,0x12345010);W(Global+0x14C,13);
    W(font+4,B+0x19000);Bytes(font+0x100,new byte[]{37,100,0});
    W(Surface+184,B+0x13000);W(B+0x13000+0x34,B+0x6200);
    W(Global+16,Get(c,"owner",1));
    for(int j=0;j<41;j++)W(info+4*j,headers+0x81);
    W(headers+0x81,32|(64<<16));Marshal.WriteInt16((IntPtr)(headers+0x85),0);
    foreach(int j in new int[]{4,5,33,35}){
      int at=headers+(j==35?0:j==33?0x20:j==4?0x40:0x60)+1;
      int w=j==35?387:j==33?13:9,h=j==35?66:j==33?13:9;
      W(marks+4*j,at);W(at,w|(h<<16));Marshal.WriteInt16((IntPtr)(at+4),0);
    }
    if(c.ContainsKey("army_bad")){
      string bad=(string)c["army_bad"];
      if(bad=="unit_pointer")W(Global+0x108,unit+1);
      if(bad=="marks_null")W(Global+0x140,0);
      if(bad=="info_null")W(Global+0x144,0);
      if(bad=="font_null")W(font+4,0);
      if(bad=="backing_null")W(marks+35*4,0);
      if(bad=="backing_size")W(headers+1,387|(67<<16));
      if(bad=="badge_size")W(headers+0x21,14|(13<<16));
      if(bad=="portrait_size")W(headers+0x81,33|(64<<16));
      if(bad=="portrait_null")W(info+16*4,0);
      if(bad=="portrait_encoding")Marshal.WriteInt16((IntPtr)(headers+0x85),1);
      if(bad=="squad_type")Marshal.WriteInt16((IntPtr)(unit+6),35);
      if(bad=="negative_type")Marshal.WriteInt16((IntPtr)(unit+6),-2);
      if(bad=="missing_middle")Marshal.WriteInt16((IntPtr)(unit+31+6),-1);
      if(bad=="surface_null")W(Global,0);
      if(bad=="surface_size")W(Surface,640|(480<<16));
      if(bad=="surface_pixels")W(Surface+4,0);
      if(bad=="surface_vtable")W(Surface+184,B+0x13004);
      if(bad=="gd_null")W(Global+4,0);
    }
    var spans=new List<int[]>{new int[]{Global,0x160},new int[]{unit,725},new int[]{Surface,188},
      new int[]{marks,160},new int[]{info,164},new int[]{font,8},new int[]{headers,256},new int[]{B+0x1C000,128}};
    var snapshots=new List<byte[]>();
    foreach(int[] span in spans){byte[] saved=new byte[span[1]];Marshal.Copy((IntPtr)span[0],saved,0,saved.Length);snapshots.Add(saved);}
'''
    source = replace_once(source, '    var regs=(IList)c["regs"];var args=(IList)c["args"];',
                          setup + '    var regs=(IList)c["regs"];var args=(IList)c["args"];')
    anchor = '    var b=new List<byte>();b.AddRange(new byte[]{0x53,0x56,0x57,0x55});'
    source = replace_once(source, anchor, anchor + r'''
    b.Add(0x68);Imm(b,unchecked((int)0xC1234567));
    b.Add(0x68);Imm(b,unchecked((int)0xD7654321));''')
    anchor = '    b.Add(0xE8);Imm(b,I(c["entry"])-(B+0x8000+b.Count+4));'
    source = replace_once(source, anchor,
                          '    b.Add(0x68);Imm(b,Get(c,"flags",0xED7));b.Add(0x9D);\n' + anchor)
    anchor = '    b.AddRange(new byte[]{0x5D,0x5F,0x5E,0x5B,0xC3});Bytes(B+0x8000,b.ToArray());'
    source = replace_once(source, anchor, r'''
    b.AddRange(new byte[]{0x9c,0x8f,0x05});Imm(b,Output+16);b.Add(0xFC);
    b.AddRange(new byte[]{0x8b,0x04,0x24});Save(b,0x05,Output+40);
    b.AddRange(new byte[]{0x8b,0x44,0x24,0x04});Save(b,0x05,Output+44);
    b.AddRange(new byte[]{0x83,0xc4,0x08});
''' + anchor)
    anchor = '    int count=Marshal.ReadInt32((IntPtr)Record);'
    check = r'''
    for(int j=0;j<spans.Count;j++)for(int z=0;z<spans[j][1];z++)
      if(Marshal.ReadByte((IntPtr)(spans[j][0]+z))!=snapshots[j][z])throw new Exception("Native state/resource/canary mutation span="+j+" offset="+z);
'''
    # The setup's squad count has a separate name to keep the recorder count native.
    setup_count = '    int count=Get(c,"squads",8);'
    source = replace_once(source, setup_count, '    int squadCount=Get(c,"squads",8);')
    source = replace_once(source, 'j<count?(j%2==0?16:1):-1', 'j<squadCount?(j%2==0?16:1):-1')
    source = replace_once(source, anchor, check + anchor)
    source = replace_once(source, 'new int[]{0,4,8,12,20,24,28,32,36}',
                          'new int[]{0,4,8,12,20,24,28,32,36,16,40,44}')
    return source


@unittest.skipUnless(os.name == "nt" and runner.CSC.is_file() and runner.ORIGINAL.is_file(),
                     "requires existing x86 fixture compiler and user-owned original")
class NativeArmyDraw(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="clash-army-draw-x86-")
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
        cls.candidates = {}; cls.bundles = {}

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
            cls.bundles[key] = army.emit_army_draw(cls.original, cls.candidate(width, height, minimap),
                base_va=runner.BASE, width=width, height=height, minimap_viewport=minimap)
        return cls.bundles[key]

    def execute(self, width, height, cases, delta=0):
        bundle = self.bundle(width, height)
        code = bytearray(bundle.code)
        for r in bundle.relocations:
            target = (TARGETS if r.kind == "abs32" else STUBS)[r.purpose] + delta
            value = target if r.kind == "abs32" else target - (runner.BASE + delta + r.offset + 4)
            struct.pack_into("<I", code, r.offset, value & 0xFFFFFFFF)
        stubs = {}
        for name, kind, argc, cleanup in (("army_sprite_lookup", 9, 0, 0), ("sprite", 3, 7, 28),
                                          ("army_number_text", 11, 6, 0),
                                          ("army_native_continue", 90, 0, 0), ("army_native_fallback", 91, 0, 0)):
            stub = runner.recorder(kind, argc, delta=delta, cleanup=cleanup)
            if name == "army_sprite_lookup":
                tail = b"\x61\xb8" + struct.pack("<I", runner.SPRITE + delta) + b"\xc2\x00\x00"
                self.assertTrue(stub.endswith(tail))
                stub = stub[:-len(tail)] + bytes.fromhex("618b0490c3")
            elif name.startswith("army_native_"):
                self.assertEqual(stub[-9:-7], bytes.fromhex("61b8"))
                stub = b"\x9c" + stub[:-9] + bytes.fromhex("619dc3")
            stubs[str(STUBS[name] + delta)] = stub.hex()
        prepared = [dict(c, entry=bundle.entries[c.get("helper", "draw_army")] + delta,
                         regs=[0x10203040, 0x22334455, 0x12345678, 0x33445566], args=[]) for c in cases]
        payload = dict(base=runner.BASE + delta, image_delta=delta, width=width, height=height,
                       code=code.hex(), stubs=stubs, cases=prepared)
        result = subprocess.run([str(self.exe)], input=json.dumps(payload), capture_output=True, text=True,
                                timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rows = json.loads(result.stdout)
        self.assertEqual(len(rows), len(cases))
        for case, row in zip(cases, rows):
            state = row["state"]
            self.assertEqual(state[1:4], [0x11223344, 0x55667788, 0x99AABBCC])
            self.assertEqual(state[4], state[5], "caller ESP changed")
            self.assertEqual(state[6:8], [0x22334455, 0x12345678])
            self.assertEqual(state[8], 35 if case.get("fallback") else 0x33445566)
            self.assertEqual(state[9] & 0xCD5, case.get("flags", 0xED7) & 0xCD5)
            self.assertEqual(state[10:12], [0xD7654321, 0xC1234567])
            if case.get("helper") == "native_suffix_hook":
                self.assertEqual(state[0], 0x10203040)
                self.assertEqual(row["records"][-1][0], 91 if case.get("fallback") else 90)
            else:
                self.assertEqual(state[0], case.get("expected", 1), str(case))
            self.assertEqual(row["render"], 0x12345000)
            self.assertEqual(row["vtable"], VTABLE + delta if case.get("army_bad") != "surface_vtable" else VTABLE + delta + 4)
        return rows

    def assert_geometry(self, row, width, height, count, masks, delta=0):
        sprites = [r for r in row["records"] if r[0] == 3]
        text = [r for r in row["records"] if r[0] == 11]
        expected = [(32, height - 82, 387, 66)]
        for j in range(count):
            expected.append((38 + 38*j, height - 81, 32, 64))
            if j % 2 == 0:
                expected.append((43 + 38*j, height - 77, 13, 13))
            if masks and j % 3 == 0:
                expected.append((61 + 38*j, height - 80, 9, 9))
        self.assertEqual(len(sprites), len(expected))
        for record, (x, y, sw, sh) in zip(sprites, expected):
            self.assertEqual(record[1:4], [runner.SURFACE + delta, x, y])
            self.assertEqual(record[5:12], [0xFFFFFFFF] * 4 + [1, 0, 0])
            self.assertEqual(record[12:16], [VTABLE + delta, runner.SURFACE + delta, 0, 1])
            self.assertGreaterEqual(x, 32); self.assertGreaterEqual(y, 16)
            self.assertLess(x + sw - 1, width - 32)
            self.assertLess(y + sh - 1, height - 16)
            self.assertLess(x + sw - 1, width - 224, "army overlaps right command dock")
        self.assertEqual(len(text), count)
        for j, record in enumerate(text):
            self.assertEqual(record[5:11], [35 + 38*j, 73 + 38*j, height - 32, 3, FONT + 0x100 + delta, 7 + j])
        self.assertEqual({r[0] for r in row["records"]} - {3, 9, 11, 90}, set())

    def test_all_six_resolutions_squads_masks_and_rebased_real_x86(self):
        for width, height in RESOLUTIONS:
            cases = [dict(squads=count, masks=masks) for count in (2, 8, 10) for masks in (0, 1)]
            for delta in DELTAS:
                for case, report in zip(cases, self.execute(width, height, cases, delta)):
                    self.assert_geometry(report, width, height, case["squads"], case["masks"], delta)

    def test_invalid_context_resources_and_sprite_bounds_fail_closed(self):
        bad = [dict(render_hook=0), dict(owner=0), dict(owner=2), dict(post_tile_callback=1),
               dict(current_player=4), dict(unit_owner=1), dict(selected=-1), dict(selected=500),
               dict(prior=4), dict(squads=0), dict(squads=1), dict(interactive=0),
               dict(unit_x=-1), dict(unit_y=-1), dict(unit_x=60), dict(unit_y=60),
               dict(map_width=0), dict(map_height=101)]
        bad += [dict(modal_field=i) for i in (0, 8, 36, 52, 56)]
        bad += [dict(army_bad=name) for name in (
            "unit_pointer", "marks_null", "info_null", "font_null", "backing_null", "backing_size",
            "badge_size", "portrait_size", "portrait_null", "portrait_encoding", "squad_type",
            "negative_type", "missing_middle", "surface_null", "surface_size", "surface_pixels", "surface_vtable", "gd_null")]
        for helper in ("army_guard", "draw_army"):
            for delta in DELTAS:
                cases = [dict(c, helper=helper, expected=0) for c in bad]
                self.assertTrue(all(not r["records"] for r in self.execute(1024, 768, cases, delta)))

    def test_native_hook_preserves_prefix_exit_and_original_fallback(self):
        for delta in DELTAS:
            cases = [dict(helper="native_suffix_hook", squads=8)]
            cases += [dict(c, helper="native_suffix_hook", fallback=True) for c in
                      (dict(owner=0), dict(unit_owner=1), dict(army_bad="font_null"), dict(render_hook=0))]
            results = self.execute(1024, 768, cases, delta)
            self.assert_geometry(results[0], 1024, 768, 8, 1, delta)
            self.assertTrue(all([r[0] for r in row["records"]] == [91] for row in results[1:]))
        hook, = self.bundle(1024, 768).hook_sites
        self.assertEqual((hook.va, hook.old_bytes), (0x42355A, bytes.fromhex("ba23000000")))
        self.assertEqual(hook.va + 5 + struct.unpack("<i", hook.new_bytes[1:])[0],
                         self.bundle(1024, 768).entries["native_suffix_hook"])

    def test_owner_and_unit_array_boundaries_and_unaligned_sprite_headers(self):
        cases = [dict(helper="army_guard", current_player=player, unit_owner=player, selected=selected)
                 for player in range(4) for selected in (0, 499)]
        self.assertTrue(all(not r["records"] for r in self.execute(800, 600, cases)))
        # Headers deliberately end in +1 and unit3 is unaligned: native S32
        # member offsets and 725-byte records must not require dword alignment.
        self.assert_geometry(self.execute(800, 600, [dict(squads=2)])[0], 800, 600, 2, 1)

    def test_source_whole_candidate_and_native_clone_are_authenticated(self):
        candidate = self.candidate(1024, 768)
        self.assertEqual(hashlib.sha256(candidate).hexdigest(),
                         "c09940fac48e903538dd3a35688efb5ca5a65edaa6ad42cf6c804ca1c008d18d")
        changed = bytearray(candidate); changed[-1] ^= 1
        for supplied, minimap in ((bytes(changed), True), (candidate, False)):
            with self.assertRaises(ValueError):
                army.emit_army_draw(self.original, supplied, base_va=runner.BASE,
                                   width=1024, height=768, minimap_viewport=minimap)
        with patch.object(army, "BUILDER_SHA256", "0" * 64):
            with self.assertRaises(ValueError):
                army.emit_army_draw(self.original, candidate, base_va=runner.BASE, width=1024, height=768)
        bundle = self.bundle(1024, 768)
        self.assertFalse(bundle.installation_ready)
        self.assertFalse(bundle.source_contract["repeated_draw_loads_resources"])
        self.assertFalse(bundle.source_contract["repeated_draw_changes_selection"])
        self.assertTrue(bundle.source_contract["input_unchanged"])
        clone = bundle.source_contract["native_clone_offset"]
        self.assertEqual(bundle.code[clone + 0xF3:clone + 0xF8], b"\x90" * 5)
        self.assertNotIn("army_lazy_font", {r.purpose for r in bundle.relocations})
        self.assertEqual({r.target for r in bundle.relocations if r.kind == "rel32"},
                         {0x405EC0, 0x40C150, 0x423715, 0x42355F})
        clip.absolute_relocation_offsets(bundle)

    def test_api_rejects_invalid_allocations_and_dimensions(self):
        candidate = self.candidate(800, 600)
        for base in (True, 0, -1, 0x80000000):
            with self.assertRaises(ValueError):
                army.emit_army_draw(self.original, candidate, base_va=base, width=800, height=600)
        for width, height in ((640, 480), (True, 600), (801, 600), (800, 479)):
            with self.assertRaises(ValueError):
                army.emit_army_draw(self.original, candidate, base_va=runner.BASE, width=width, height=height)
        with self.assertRaises(ValueError):
            army.emit_army_draw(self.original, candidate, base_va=runner.BASE,
                               width=800, height=600, minimap_viewport=1)


if __name__ == "__main__":
    unittest.main()
