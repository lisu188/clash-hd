"""Actual uninstalled x86 field clones with synthetic native ABI recorders.

The only executable launched is a no-window C# fixture. No game image, CDB,
window, input or capture is run. Native tile/cursor/copy calls are recorded;
independent field and rectangle oracles validate their coordinates and order.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import test_partial_tile_clip as runner
import test_framed_battle_coordinates as previous
from src.patcher import framed_battle_field as field
from src.patcher import partial_tile_clip as clip
from tools import build_framed_army_candidate as builder

RESOLUTIONS = ((800,600),(1024,768),(1280,720),(1280,960),(1920,1080),(802,602))
ADMISSION = runner.BASE+0x7000
DESCRIPTOR = runner.BASE+0x14000
TARGETS = {
    "battle_state_global": runner.GLOBAL+0x104,
    "battle_render_owner": runner.GLOBAL+0x100,
    "native_battle_owner": 0x42E8B0,
    "field_surface_global": runner.GLOBAL,
    "render_device_global": runner.GLOBAL+8,
    "memory_vtable": 0x50EE24,
    "cursor_descriptor_global": runner.GLOBAL+0x108,
    "mouse_shift": runner.GLOBAL+0x10C,
    "mouse_raw_x": runner.GLOBAL+0x110,
    "mouse_raw_y": runner.GLOBAL+0x114,
    "cursor_visible": runner.GLOBAL+20,
    "cursor_object": runner.BASE+0x15000,
}
NATIVE = {
    "native_battle_tile": (runner.BASE+0x6000,4,0),
    "native_cursor_hide": (runner.BASE+0x6200,15,0),
    "native_cursor_background": (runner.BASE+0x6400,16,0),
    "native_cursor_restore": (runner.BASE+0x6600,7,0),
    "native_rectangle_copy": (runner.BASE+0x6800,6,4),
    "native_cursor_dirty": (runner.BASE+0x6A00,5,1),
}


def fixture_source():
    source = previous.fixture_source()
    anchor = '    var regs=(IList)c["regs"];var args=(IList)c["args"];'
    setup = r'''
    W(Global+0x108,Get(c,"cursor_descriptor",B+0x14000));
    W(Global+0x10c,6);W(Global+0x110,Get(c,"mouse_x",900)*64);W(Global+0x114,Get(c,"mouse_y",700)*64);
    W(B+0x14000+12,Get(c,"cursor_width",16));W(B+0x14000+16,Get(c,"cursor_height",16));
    W(B+0x7001,Get(c,"admission",1));
'''
    return previous.replace_once(source, anchor, setup+anchor)


def copy_rectangles(left, top, cw, ch, right):
    """Inclusive native field-copy policy, with both-axis disjoint admission."""
    if left >= right+1 or left+cw <= 32 or top >= 464 or top+ch <= 16:
        return [(32,16,right,463)]
    l,r=max(left,32),min(left+cw,right)
    t,b=max(top,16),min(top+ch,463)
    result=[(32,16,right,t),(32,t,l,b),(l,t,r,b)]
    if r != right:
        result.append((r,t,right,b))
    if b != 463:
        result.append((32,b,right,463))
    return result


class FieldContractTests(unittest.TestCase):
    def test_installed_scope_is_explicit_and_sources_frozen(self):
        self.assertEqual(field.verify_sources(),field.PINNED_SOURCES)
        self.assertTrue(field.integration_required()[0].startswith("Do not install"))
        self.assertTrue(any("42C870" in item for item in field.integration_required()))
        self.assertEqual(len(field.FULL_CALLS),14)
        self.assertEqual(len(field.INCREMENTAL_CALLS),4)


@unittest.skipUnless(os.name=="nt" and runner.CSC.is_file() and runner.ORIGINAL.is_file(),
                     "requires user-owned original and existing x86 fixture compiler")
class EmittedBattleField(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix="clash-battle-field-x86-")
        cls.addClassCleanup(cls.temp.cleanup)
        source=Path(cls.temp.name)/"fixture.cs";cls.exe=Path(cls.temp.name)/"fixture.exe"
        source.write_text(fixture_source(),encoding="utf-8")
        compiled=subprocess.run([str(runner.CSC),"/nologo","/platform:x86","/optimize+",
            "/r:System.Web.Extensions.dll",f"/out:{cls.exe}",str(source)],capture_output=True,text=True,
            timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        if compiled.returncode:
            raise AssertionError(compiled.stdout+compiled.stderr)
        cls.original=runner.ORIGINAL.read_bytes();cls.bundles={};cls.candidates={}

    @classmethod
    def bundle(cls,width,height):
        key=width,height
        if key not in cls.bundles:
            cls.candidates[key]=builder.build_candidate(cls.original,f"{width}x{height}",minimap_viewport=True)[0]
            cls.bundles[key]=field.emit_battle_field(cls.original,cls.candidates[key],base_va=runner.BASE,
                width=width,height=height,admission_va=ADMISSION,minimap_viewport=True)
        return cls.bundles[key]

    def execute(self,width,height,cases,delta=0):
        bundle=self.bundle(width,height)
        self.assertLess(len(bundle.code),0x6000)
        self.assertFalse(bundle.installation_ready)
        self.assertFalse(bundle.source_contract["installed"])
        code=bytearray(bundle.code)
        stubs={ADMISSION+delta: "b801000000c3"}
        for _,(address,kind,argc) in NATIVE.items():
            native=runner.recorder(kind,argc,delta=delta)
            at=native.rfind(bytes.fromhex("61b8"))
            self.assertGreater(at,0)
            # Recorders do not modify DF. Replace their unused final context
            # slot with flags, independently proving native callees see DF0.
            stubs[address+delta]=(native[:at]+bytes.fromhex("9c8f473c")+native[at:]).hex()
        for reloc in bundle.relocations:
            if reloc.kind=="abs32":
                target=TARGETS[reloc.purpose]+delta
                struct.pack_into("<I",code,reloc.offset,target)
            else:
                if reloc.purpose in NATIVE:
                    target=NATIVE[reloc.purpose][0]+delta
                elif reloc.purpose=="required_battle_admission":
                    target=ADMISSION+delta
                elif reloc.purpose.startswith("native_") and reloc.purpose.endswith("_continuation"):
                    # Source-authenticated original prologues are replayed in
                    # fallback. A fixture-only matching epilogue records route.
                    which=reloc.purpose.removeprefix("native_").removesuffix("_continuation")
                    index=("full_hook","incremental_hook","visibility_hook").index(which)
                    target=runner.BASE+0x7400+0x100*index+delta
                    unwind={"full_hook":"5f5e5a595bc3", "incremental_hook":"83c4085d5e59c3", "visibility_hook":"5e595bc3"}[which]
                    recorder=runner.recorder(20+index,0,delta=delta)
                    stubs[target]=(recorder[:-3]+bytes.fromhex(unwind)).hex()
                else:
                    self.assertTrue(bundle.base_va <= reloc.target < bundle.base_va+len(code),reloc)
                    target=reloc.target+delta
                struct.pack_into("<i",code,reloc.offset,target-(runner.BASE+delta+reloc.offset+4))
        prepared=[]
        for case in cases:
            prepared.append(dict(case,entry=bundle.entries[case["entry_name"]]+delta,
                regs=[case.get("x",0),0x22334455,0x33445566,case.get("y",0)],args=[]))
        payload=dict(base=runner.BASE+delta,image_delta=delta,width=width,height=height,
                     code=code.hex(),stubs={str(k):v for k,v in stubs.items()},cases=prepared)
        ran=subprocess.run([str(self.exe)],input=json.dumps(payload),capture_output=True,text=True,
            timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(ran.returncode,0,ran.stdout+ran.stderr)
        reports=json.loads(ran.stdout);self.assertEqual(len(reports),len(cases))
        for case,report in zip(cases,reports):
            state=report["state"]
            self.assertEqual(state[1:4],[0x11223344,0x55667788,0x99AABBCC])
            self.assertEqual(state[4],state[5],"caller ESP changed")
            self.assertEqual(state[6:9],[0x22334455,0x33445566,case.get("y",0)&0xFFFFFFFF])
            self.assertEqual(state[10:12],[0xD7654321,0xC1234567])
            if not case.get("fallback"):
                self.assertEqual(state[9]&previous.FLAGS_MASK,case.get("flags",0xAD7)&previous.FLAGS_MASK)
                self.assertEqual(state[0],case.get("expected",1),str(case))
                self.assertEqual(report["render"],case.get("initial_render",0x12345000))
            self.assertEqual(report["vtable"],0x50EE74 if case.get("bad")=="vtable"
                             else case.get("initial_vtable",0x50EE24+delta))
        return reports

    def test_full_native_cells_all_resolutions_and_small_worlds(self):
        for width,height in RESOLUTIONS:
            cases=[]
            for world in (1,7,20):
                visible=min(world,(width-192)//64)
                for scroll in sorted({0,world-visible}):
                    cases.append(dict(entry_name="draw_full",columns=world,battle_scroll=scroll,
                                      mouse_x=width-20,mouse_y=height-20))
            reports=self.execute(width,height,[dict(case,flags=0xED7) for case in cases])
            for case,report in zip(cases,reports):
                visible=min(case["columns"],(width-192)//64);scroll=case["battle_scroll"]
                tiles=[r for r in report["records"] if r[0]==4]
                self.assertEqual([(r[1],r[4]) for r in tiles],
                    [(x,y) for x in range(scroll,scroll+visible) for y in range(7)])
                self.assertTrue(all(r[13]==runner.SURFACE for r in tiles))
                copies=[r for r in report["records"] if r[0]==6]
                self.assertEqual([(r[2],r[3],r[5],r[6]) for r in copies],[(32,16,31+64*visible,463)])
                self.assertTrue(all(r[4]==0 for r in copies),"native destination must resolve to primary")
                self.assertTrue(all(r[15]&0x400==0 for r in report["records"]),"DF must be clear in native callees")

    def test_full_cursor_clipping_stays_inside_exact_dynamic_field(self):
        width,height=1024,768;visible=13;right=31+64*visible
        positions=((48,32),(24,8),(right-8,450),(right+1,80),(32,700),(48,-40),(-40,80))
        cases=[dict(entry_name="draw_full",columns=20,mouse_x=x,mouse_y=y,cursor_width=16,cursor_height=16)
               for x,y in positions]
        reports=self.execute(width,height,cases,delta=0x02000000)
        for case,report in zip(cases,reports):
            copies=[r for r in report["records"] if r[0]==6]
            rects=[(r[2],r[3],r[5],r[6]) for r in copies]
            self.assertEqual(rects,copy_rectangles(case["mouse_x"],case["mouse_y"],16,16,right))
            self.assertTrue(all(32<=l<=r<=right and 16<=t<=b<=463 for l,t,r,b in rects))
            self.assertTrue(all((r[7],r[8])==(r[2],r[3]) for r in copies))

    def test_incremental_and_visibility_every_column_row_boundaries(self):
        for width,height in RESOLUTIONS:
            visible=min(20,(width-192)//64);cases=[]
            for scroll in sorted({0,20-visible}):
                for x in range(-1,21):
                    for y in (-1,0,6,7):
                        shown=scroll<=x<scroll+visible and 0<=y<7
                        for entry in ("draw_incremental","visible_cell"):
                            cases.append(dict(entry_name=entry,x=x,y=y,columns=20,battle_scroll=scroll,expected=int(shown)))
            reports=self.execute(width,height,cases)
            for case,report in zip(cases,reports):
                records=report["records"]
                if case["entry_name"]=="visible_cell" or not case["expected"]:
                    self.assertEqual(records,[])
                else:
                    self.assertEqual([r[0] for r in records],[4,5,6,7])
                    self.assertEqual((records[0][1],records[0][4]),(case["x"],case["y"]))
                    x=32+64*(case["x"]-case["battle_scroll"]);y=16+64*case["y"]
                    copy=records[2]
                    self.assertEqual((copy[2],copy[3],copy[5],copy[6],copy[7],copy[8]),(x,y,x+63,y+63,x,y))
                    dirty=records[1]
                    self.assertEqual((dirty[4],dirty[2],dirty[3],dirty[5]),(x,y,x+64,y+64))

    def test_rejected_context_calls_no_native_and_hook_fallback_is_exact(self):
        cases=[]
        for changed in ({"admission":0},{"rows":8},{"columns":0},{"columns":21},{"battle_y":1},
                        {"battle_scroll":-1},{"battle_scroll":8},{"battle_owner":0},
                        {"global_pointer":0},{"bad":"dimensions"},{"bad":"pixels"},{"bad":"vtable"}):
            for entry in ("draw_full","draw_incremental","visible_cell"):
                cases.append(dict(entry_name=entry,expected=0xFFFFFFFF if entry=="visible_cell" else 0,**changed))
        reports=self.execute(1024,768,cases)
        self.assertTrue(all(not r["records"] for r in reports))
        fallback=[dict(entry_name=entry,admission=0,fallback=True) for entry in
                  ("full_hook","incremental_hook","visibility_hook")]
        reports=self.execute(1024,768,fallback)
        self.assertEqual([[r[0] for r in report["records"]] for report in reports],[[20],[21],[22]])

    def test_candidate_hook_and_relocation_authentication(self):
        bundle=self.bundle(1024,768)
        self.assertEqual([h.va for h in bundle.hook_sites],[0x430C20,0x430B20,0x42C0F0])
        for hook in bundle.hook_sites:
            self.assertEqual(self.candidates[(1024,768)][hook.offset:hook.offset+len(hook.old)],hook.old)
            self.assertEqual(hook.new[0],0xE9)
        self.assertEqual(bundle.removed_highlow_rvas,())
        self.assertTrue(clip.absolute_relocation_offsets(bundle))
        self.assertEqual(len(bundle.source_contract["clone_instruction_edits"]),11)
        for edit in bundle.source_contract["clone_instruction_edits"]:
            old=bytes.fromhex(edit["old_hex"]);new=bytes.fromhex(edit["new_hex"])
            self.assertEqual(self.original[edit["source_offset"]:edit["source_offset"]+len(old)],old)
            offset=edit["emitted_va"]-bundle.base_va
            self.assertEqual(bundle.code[offset:offset+len(new)],new)
            self.assertEqual(len(old),len(new))
        self.assertEqual(runner.ORIGINAL.read_bytes(),self.original)
        with patch.dict(field.PINNED_SOURCES,{"src/patcher/framed_battle_coordinates.py":"0"*64}):
            with self.assertRaisesRegex(ValueError,"source differs"):
                field.verify_sources()
        with self.assertRaises(ValueError):
            field.emit_battle_field(self.original,self.candidates[(1024,768)],base_va=True,
                width=1024,height=768,admission_va=ADMISSION)
        with patch.object(builder,"build_candidate",return_value=(self.candidates[(1024,768)],{},"")):
            with self.assertRaisesRegex(ValueError,"whole current army candidate"):
                field.emit_battle_field(self.original,self.candidates[(1024,768)][:-1]+b"\xff",
                    base_va=runner.BASE,width=1024,height=768,admission_va=ADMISSION)


if __name__=="__main__":
    unittest.main()
