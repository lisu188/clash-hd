#!/usr/bin/env python3
"""Execute emitted x86 in an isolated, synthetic 32-bit fixture process.

No game/debugger/window/input/capture is launched. Native draw entrypoints are
replaced only in this fixture by ABI recorders. Independent raster oracles
check the recorded operations. All compiler outputs live in a temp directory.
"""
from __future__ import annotations

import json
from dataclasses import replace
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher import partial_tile_clip as clip

BASE = 0x20000000
SURFACE = BASE + 0x10000
SPRITE = BASE + 0x11000
GLOBAL = BASE + 0x12000
RECORD = BASE + 0x20000
OUTPUT = BASE + 0x30000
GAME_DATA = BASE + 0x40000
DESCRIPTORS = BASE + 0x13000
STUBS = {name: BASE + 0x6000 + 0x200*i for i,name in enumerate(
    ("line", "fill", "sprite", "tile", "dirty", "blit", "cursor", "descriptors",
     "turn_sprite_lookup","turn_select_font","turn_text_format","turn_text_color","turn_text_draw","minimap"))}
ARGC = {"line":2,"fill":2,"sprite":7,"tile":0,"dirty":1,"blit":4,"cursor":0,"descriptors":0,
        "turn_sprite_lookup":0,"turn_select_font":0,"turn_text_format":5,"turn_text_color":0,"turn_text_draw":4,"minimap":0}
GLOBALS = {name:GLOBAL+4*i for i,name in enumerate(("map_surface_global", "game_data_global",
    "render_device_global", "tile_callback", "lower_row_owner", "cursor_visible",
    "render_hook","post_tile_callback","current_player","command_sprites","tooltip_surface",
    "tooltip_0","tooltip_1","tooltip_2","tooltip_3","turn_sprites"))}
GLOBALS["command_descriptors"]=DESCRIPTORS
CSC = Path(r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe")
ORIGINAL = Path(r"C:\Clash\clash95.exe")

CSHARP = r'''
using System;
using System.Collections;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
class Fixture {
 static int B,Surface,Sprite,Global,Record,Output,GameData;
 [DllImport("kernel32",SetLastError=true)] static extern IntPtr VirtualAlloc(IntPtr p,UIntPtr n,uint a,uint prot);
 [DllImport("kernel32")] static extern bool VirtualFree(IntPtr p,UIntPtr n,uint a);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int Entry();
 static int I(object x){return unchecked((int)Convert.ToInt64(x));}
 static int Get(Dictionary<string,object> c,string k,int value){return c.ContainsKey(k)?I(c[k]):value;}
 static byte[] Hex(string s){byte[] b=new byte[s.Length/2];for(int i=0;i<b.Length;i++)b[i]=Convert.ToByte(s.Substring(2*i,2),16);return b;}
 static void W(int p,int n){Marshal.WriteInt32((IntPtr)p,n);}
 static void Bytes(int p,byte[] b){Marshal.Copy(b,0,(IntPtr)p,b.Length);}
 static void Imm(List<byte> b,int n){b.AddRange(BitConverter.GetBytes(n));}
 static void Save(List<byte> b,byte reg,int dest){b.Add(0x89);b.Add(reg);Imm(b,dest);}
 static int Main(){
  IntPtr mem=IntPtr.Zero;
  try {
   if(IntPtr.Size!=4)throw new Exception("Fixture must execute as x86");
   var serializer=new JavaScriptSerializer();serializer.MaxJsonLength=16000000;
   var root=serializer.Deserialize<Dictionary<string,object>>(Console.In.ReadToEnd());
   B=Get(root,"base",0x20000000);Surface=B+0x10000;Sprite=B+0x11000;Global=B+0x12000;
   Record=B+0x20000;Output=B+0x30000;GameData=B+0x40000;int delta=Get(root,"image_delta",0);
   mem=VirtualAlloc((IntPtr)B,(UIntPtr)0x80000,0x3000,0x40);
   if(mem!=(IntPtr)B)throw new Exception("Synthetic address reservation failed");
   Bytes(B,Hex((string)root["code"]));
   var stubs=(Dictionary<string,object>)root["stubs"];
   foreach(var kv in stubs)Bytes(int.Parse(kv.Key),Hex((string)kv.Value));
   var results=new List<object>();
   foreach(object item in (IEnumerable)root["cases"]){
    var c=(Dictionary<string,object>)item;
    byte[] blank=new byte[0x11000];for(int k=0;k<blank.Length;k++)blank[k]=0xA5;
    Bytes(Record,blank);W(Record,0);
    W(Surface,I(root["width"]) | (I(root["height"])<<16));W(Surface+4,B+0x18000);W(Surface+184,Get(c,"initial_vtable",0x50ee24+delta));W(Global,Surface);
    W(Global+4,GameData);W(Global+8,Get(c,"initial_render",0x12345000));W(Global+12,Get(c,"callback",0));W(Global+16,Get(c,"owner",0));W(Global+20,Get(c,"cursor",1));
    W(GameData+0x222e0,Get(c,"map_width",60));W(GameData+0x222e4,Get(c,"map_height",60));
    W(GameData+0x222e8,Get(c,"scroll_x",10));W(GameData+0x222ec,Get(c,"scroll_y",17));
    W(Global+24,Get(c,"render_hook",0x40ad40+delta));W(Global+28,Get(c,"post_tile_callback",0));
    int player=Get(c,"current_player",0);W(Global+32,player);W(Global+36,Get(c,"command_sprites",Sprite));
    for(int p=0;p<5;p++)W(GameData+1423*p+0x22313,Get(c,"interactive",1));
    W(Global+40,Get(c,"tooltip",0));
    W(Global+44,Get(c,"tooltip_left",160+(I(root["width"])-640)/2));W(Global+48,I(root["height"])-14);
    W(Global+52,473+(I(root["width"])-640)/2);W(Global+56,I(root["height"])-1);
    W(Global+60,Get(c,"turn_sprites",Sprite));
    W(GameData+0x23ed3,Get(c,"turn_number",0));W(GameData+0x222f6,7);
    if(root.ContainsKey("descriptor_bytes"))Bytes(B+0x13000,Hex((string)root["descriptor_bytes"]));
    if(c.ContainsKey("bad")){
     string bad=(string)c["bad"];
     if(bad=="global")W(Global,Surface+4);
     if(bad=="dimensions")W(Surface,1);
     if(bad=="pixels")W(Surface+4,0);
     if(bad=="vtable")W(Surface+184,0x50ee74);
     if(bad=="game_data")W(Global+4,0);
     if(bad=="descriptor")W(B+0x13000,1);
     if(bad=="descriptor_callback")W(B+0x13000+28,0x12345678);
     if(bad=="descriptor_end")W(B+0x13000+318,0);
    }
    var regs=(IList)c["regs"];var args=(IList)c["args"];
    var b=new List<byte>();b.AddRange(new byte[]{0x53,0x56,0x57,0x55});
    // CLR nonvolatiles saved; establish canaries and record exact pre-call ESP.
    b.Add(0xBE);Imm(b,Get(c,"esi",0x11223344));b.Add(0xBF);Imm(b,0x55667788);b.Add(0xBD);Imm(b,unchecked((int)0x99AABBCC));
    Save(b,0x25,Output+20);
    for(int k=args.Count-1;k>=0;k--){b.Add(0x68);Imm(b,I(args[k]));}
    foreach(int k in new int[]{0,1,2,3}){b.Add(new byte[]{0xB8,0xBB,0xB9,0xBA}[k]);Imm(b,I(regs[k]));}
    b.Add(0xE8);Imm(b,I(c["entry"])-(B+0x8000+b.Count+4));
    Save(b,0x05,Output);Save(b,0x35,Output+4);Save(b,0x3D,Output+8);Save(b,0x2D,Output+12);Save(b,0x25,Output+24);
    Save(b,0x1D,Output+28);Save(b,0x0D,Output+32);Save(b,0x15,Output+36);
    b.AddRange(new byte[]{0x5D,0x5F,0x5E,0x5B,0xC3});Bytes(B+0x8000,b.ToArray());
    ((Entry)Marshal.GetDelegateForFunctionPointer((IntPtr)(B+0x8000),typeof(Entry)))();
    int count=Marshal.ReadInt32((IntPtr)Record);if(count<0||count>512)throw new Exception("Invalid native call count");
    var records=new List<object>();
    for(int i=0;i<count;i++){var row=new List<uint>();for(int j=0;j<16;j++)row.Add(unchecked((uint)Marshal.ReadInt32((IntPtr)(Record+4+64*i+4*j))));records.Add(row);}
    // Recorders may write only the active records, never the guard region.
    for(int i=0;i<0x10000;i++){
     bool allowed=i<4+64*count;
     if(!allowed&&Marshal.ReadByte((IntPtr)(Record+i))!=0xA5)throw new Exception("Recorder guard damaged");
    }
    var state=new List<uint>();foreach(int o in new int[]{0,4,8,12,20,24,28,32,36})state.Add(unchecked((uint)Marshal.ReadInt32((IntPtr)(Output+o))));
    results.Add(new Dictionary<string,object>{{"records",records},{"state",state},
     {"vtable",unchecked((uint)Marshal.ReadInt32((IntPtr)(Surface+184)))},
     {"render",unchecked((uint)Marshal.ReadInt32((IntPtr)(Global+8)))}});
   }
   Console.Write(serializer.Serialize(results));return 0;
  }catch(Exception e){Console.Error.WriteLine(e);return 1;}
  finally{if(mem!=IntPtr.Zero)VirtualFree(mem,UIntPtr.Zero,0x8000);}
 }
}
'''


def recorder(kind: int, argc: int, *, delta: int = 0, cleanup: int | None = None) -> bytes:
    """Native-register ABI observation stub; intentionally does no rendering."""
    b = bytearray.fromhex("6089e5bf") + struct.pack("<I", RECORD+delta)
    b += bytes.fromhex("8b376bf640ff078d7c3704c707") + struct.pack("<I", kind)
    for dest, source in ((4, 28), (8, 16), (12, 24), (16, 20)):
        b += bytes((0x8B, 0x45, source, 0x89, 0x47, dest))
    for i in range(7):
        if i < argc:
            b += bytes((0x8B, 0x45, 36 + 4*i))
        else:
            b += bytes.fromhex("31c0")
        b += bytes((0x89, 0x47, 20 + 4*i))
    # Observe context at the actual native call, independently of return state.
    b += bytes.fromhex("a1") + struct.pack("<I",GLOBAL+delta)
    b += bytes.fromhex("8b80b8000000894730")
    for dest,address in ((52,GLOBAL+8),(56,GLOBAL+12),(60,GLOBAL+16)):
        b += b"\xa1" + struct.pack("<I",address+delta) + bytes((0x89,0x47,dest))
    b += bytes.fromhex("61b8") + struct.pack("<I",SPRITE+delta if kind==9 else 0x13572468)
    b += b"\xc2" + struct.pack("<H",argc*4 if cleanup is None else cleanup)
    return bytes(b)


def signed(n: int) -> int:
    return n if n < 0x80000000 else n - 0x100000000


def inside_pixels(rect: tuple[int, int, int, int], width: int, height: int) -> set[tuple[int, int]]:
    l, t, r, b = rect
    return {(x, y) for y in range(max(t, 0), min(b, height-1)+1)
            for x in range(max(l, 0), min(r, width-1)+1)}


class GeometryTests(unittest.TestCase):
    def test_exact_partial_cells_and_world_edge(self):
        cells = clip.edge_cells(width=1024, height=768, map_width=60, map_height=60, scroll_x=10, scroll_y=17)
        self.assertEqual(len(cells), 27)
        self.assertEqual({c.operation for c in cells}, {"draw_clipped_tile"})
        self.assertEqual(cells[-1].rect, (992, 720, 1023, 767))
        pixels = set().union(*(inside_pixels(c.rect,1024,768) for c in cells))
        expected = {(x,y) for y in range(16,768) for x in range(32,1024) if x>=992 or y>=720}
        self.assertEqual(pixels, expected)
        far = clip.edge_cells(width=1024,height=768,map_width=60,map_height=60,scroll_x=45,scroll_y=49)
        self.assertEqual({c.operation for c in far}, {"clear_outside_world"})
        right = clip.edge_cells(width=1024,height=768,map_width=60,map_height=60,scroll_x=45,scroll_y=17)
        self.assertTrue(all(c.operation == ("clear_outside_world" if c.column==15 else "draw_clipped_tile") for c in right))

    def test_800_tail_and_bad_bounds(self):
        cells=clip.edge_cells(width=800,height=600,map_width=100,map_height=100,scroll_x=0,scroll_y=0)
        self.assertEqual(len(cells),12)
        self.assertTrue(all(c.rect[1:4:2]==(592,599) for c in cells))
        for changed in ({"map_width":101},{"scroll_x":89},{"scroll_y":-1},{"width":True}):
            args=dict(width=800,height=600,map_width=100,map_height=100,scroll_x=0,scroll_y=0);args.update(changed)
            with self.assertRaises(ValueError):clip.edge_cells(**args)

    def test_unfinished_installation_is_explicit(self):
        self.assertIn("Do not install",clip.integration_requirements()[0])


@unittest.skipUnless(os.name=="nt" and CSC.is_file() and ORIGINAL.is_file(), "requires local x86 compiler and user-owned original for byte verification")
class NativeX86Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix="clash-partial-x86-fixture-")
        cls.path=Path(cls.temp.name);cls.exe=cls.path/"fixture.exe"
        source=cls.path/"fixture.cs";source.write_text(CSHARP,encoding="utf-8")
        result=subprocess.run([str(CSC),"/nologo","/platform:x86","/optimize+","/r:System.Web.Extensions.dll",f"/out:{cls.exe}",str(source)],capture_output=True,text=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:raise AssertionError(result.stdout+result.stderr)
        cls.original=ORIGINAL.read_bytes()
        clip.verify_original(cls.original)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def prerequisite_candidate(self, width=1024, height=768):
        # In-memory ABI fixture, deliberately not a runnable candidate or gate.
        candidate=bytearray(self.original)
        for va,value in ((0x40D560,clip.MINIMAP_CLIP_HOOK),(0x4E9980,clip.MINIMAP_CLIP_CAVE)):
            off=clip.file_offset(candidate,va,len(value));candidate[off:off+len(value)]=value
        struct.pack_into("<I",candidate,clip.file_offset(candidate,0x419D65,4),width)
        struct.pack_into("<I",candidate,clip.file_offset(candidate,0x419D8E,4),width)
        for i in range(6):
            struct.pack_into("<ii",candidate,clip.file_offset(candidate,clip.COMMAND_DESCRIPTORS+53*i,8),
                             width-192+64*(i%3),height-72+32*(i//3))
        return bytes(candidate)

    def run_cases(self, width, height, cases, *, edges=False, origin=(0,0), composition=False, rebase_delta=0):
        candidate=self.prerequisite_candidate(width,height)
        if composition:bundle=clip.emit_map_composition(self.original,candidate,base_va=BASE,width=width,height=height)
        elif edges:bundle=clip.emit_edge_dispatch(self.original,candidate,base_va=BASE,width=width,height=height)
        else:bundle=clip.emit_adapters(self.original,base_va=BASE,width=width,height=height,clip_origin=origin)
        self.assertFalse(bundle.installation_ready)
        self.assertLess(len(bundle.code),0x6000,"fixture code overlaps native stubs")
        code=bytearray(bundle.code)
        offsets=clip.absolute_relocation_offsets(bundle)
        for offset in offsets:
            value=struct.unpack_from("<I",code,offset)[0]
            struct.pack_into("<I",code,offset,value+rebase_delta)
        for relocation in bundle.relocations:
            if relocation.purpose in GLOBALS:
                struct.pack_into("<I",code,relocation.offset,GLOBALS[relocation.purpose]+rebase_delta)
            elif relocation.kind=="rel32":
                struct.pack_into("<i",code,relocation.offset,STUBS[relocation.purpose]-(BASE+relocation.offset+4))
        payload={"code":code.hex(),"width":width,"height":height,"base":BASE+rebase_delta,"image_delta":rebase_delta,
                 "stubs":{str(STUBS[n]+rebase_delta):recorder(i,ARGC[n],delta=rebase_delta,
                    cleanup=0 if n in ("turn_text_format","turn_text_draw") else None).hex() for i,n in enumerate(STUBS,1)},"cases":[]}
        if composition:
            off=clip.file_offset(candidate,clip.COMMAND_DESCRIPTORS,322)
            desc=bytearray(candidate[off:off+322])
            for i in range(6):
                struct.pack_into("<I",desc,53*i+12,GLOBALS["command_sprites"]+rebase_delta)
                struct.pack_into("<I",desc,53*i+28,0x4191F0+rebase_delta)
            payload["descriptor_bytes"]=desc.hex()
        for case in cases:
            payload["cases"].append(dict(case,entry=bundle.entries[case["name"]]+rebase_delta))
        result=subprocess.run([str(self.exe)],input=json.dumps(payload),capture_output=True,text=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        reports=json.loads(result.stdout)
        self.assertEqual(len(reports),len(cases))
        for case,report in zip(cases,reports):
            state=report["state"]
            self.assertEqual(state[1:4],[case.get("esi",0x11223344),0x55667788,0x99AABBCC])
            self.assertEqual(state[4],state[5],"native callee-cleanup ABI corrupted ESP")
            if edges or composition:self.assertEqual(state[6:9],[v & 0xFFFFFFFF for v in case["regs"][1:4]])
        return reports

    def test_real_original_bytes_and_changed_input_reject(self):
        wrong=bytearray(self.original);wrong[0x17B70]^=1
        with self.assertRaisesRegex(ValueError,"SHA-256"):
            clip.emit_adapters(bytes(wrong),base_va=BASE,width=1024,height=768)

    def test_native_fill_line_and_original_outline_segments(self):
        width,height=113,91
        rng=random.Random(8173)
        rects=[(-10,-10,120,100),(-2,20,50,60),(20,20,150,110),(0,0,112,90),(113,0,150,90),(-50,0,-1,90),(3,4,3,4),(9,9,8,8)]
        rects += [tuple(rng.randint(-40,150) for _ in range(4)) for _ in range(60)]
        cases=[]
        for name in ("fill","outline","line"):
            for l,t,r,b in rects:
                if name=="line" and rng.randrange(2):b=t
                cases.append({"name":name,"regs":[SURFACE,t,r,l],"args":[b,0x17]})
        reports=self.run_cases(width,height,cases)
        for case,report in zip(cases,reports):
            _,t,r,l=case["regs"];b,color=case["args"];name=case["name"]
            expected=set()
            if l<=r and t<=b:
                if name=="fill":expected=inside_pixels((l,t,r,b),width,height)
                if name=="outline":expected={(x,y) for x,y in inside_pixels((l,t,r,b),width,height) if x in(l,r) or y in(t,b)}
                if name=="line" and (l==r or t==b):expected=inside_pixels((l,t,r,b),width,height)
            observed=set()
            for row in report["records"]:
                kind,surf,rr,rright,ll,bottom,flags,*_=map(signed,row)
                self.assertEqual(surf,SURFACE)
                self.assertEqual(flags,color)
                # Native registers: EBX top, ECX right, EDX left.
                self.assertTrue(0<=ll<=rright<width and 0<=rr<=bottom<height,(case,row))
                if kind==1:self.assertTrue(ll==rright or rr==bottom)
                observed |= inside_pixels((ll,rr,rright,bottom),width,height)
            self.assertEqual(observed,expected,case)

    def test_sprite_inclusive_intersection_and_untouched_mode(self):
        cases=[]
        for rect in ((-1,-1,-1,-1),(-10,10,1100,900),(100,80,200,90),(1024,0,1090,10),(100,20,99,30),(-1,-1,-1,20)):
            cases.append({"name":"sprite","regs":[SURFACE,992,720,SPRITE],"args":[*rect,1,2,0x12345678]})
        reports=self.run_cases(1024,768,cases)
        for case,report in zip(cases,reports):
            rect=tuple(case["args"][:4]);expected=inside_pixels((0,0,1023,767) if rect==(-1,)*4 else rect,1024,768)
            if not expected:self.assertEqual(report["records"],[]);continue
            self.assertEqual(len(report["records"]),1)
            row=report["records"][0];self.assertEqual(row[:5],[3,SURFACE,992,720,SPRITE]);self.assertEqual(row[9:12],case["args"][4:])
            got=tuple(map(signed,row[5:9]))
            self.assertEqual(got,(min(x for x,y in expected),min(y for x,y in expected),max(x for x,y in expected),max(y for x,y in expected)))

    def test_target_guards_and_unsupported_sprite_coordinates(self):
        cases=[]
        for name in ("line","fill","outline","sprite"):
            args=[-1]*4+[1,0,0] if name=="sprite" else [60,1]
            regs=[SURFACE,10,10,SPRITE] if name=="sprite" else [SURFACE,10,60,10]
            for bad in ("global","dimensions","pixels","vtable"):
                cases.append({"name":name,"regs":regs,"args":args,"bad":bad})
        cases.append({"name":"sprite","regs":[SURFACE,0x7FFFFFFF,0,SPRITE],"args":[-1]*4+[1,0,0]})
        for report in self.run_cases(800,600,cases):self.assertEqual(report["records"],[])

    def test_gameplay_clips_protect_gutters_without_inventing_outline(self):
        cases=[{"name":"fill","regs":[SURFACE,-10,100,-10],"args":[80,9]},
               {"name":"outline","regs":[SURFACE,-10,100,-10],"args":[80,9]},
               {"name":"sprite","regs":[SURFACE,0,0,SPRITE],"args":[-1]*4+[0,0,0]},
               {"name":"line","regs":[SURFACE,15,100,0],"args":[15,9]}]
        reports=self.run_cases(800,600,cases,origin=(32,16))
        self.assertEqual(reports[0]["records"][0][2:6],[16,100,32,80])
        outlines=[row[2:6] for row in reports[1]["records"]]
        self.assertEqual(outlines,[[80,100,32,80],[16,100,100,80]])
        self.assertEqual(reports[2]["records"][0][5:9],[32,16,799,599])
        self.assertEqual(reports[3]["records"],[])

    def test_edge_prerequisites_reject_changed_callbacks_and_missing_minimap(self):
        with self.assertRaisesRegex(ValueError,"minimap"):
            clip.emit_edge_dispatch(self.original,self.original,base_va=BASE,width=1024,height=768)
        for va in (0x416850,0x425120,0x429EC0,0x5142D4,0x4E9980,0x40D568,0x419D60,0x405510,0x460BB0):
            candidate=bytearray(self.prerequisite_candidate())
            candidate[clip.file_offset(candidate,va,1)]^=1
            with self.assertRaises(ValueError):
                clip.emit_edge_dispatch(self.original,bytes(candidate),base_va=BASE,width=1024,height=768)
        with self.assertRaisesRegex(ValueError,"requested width"):
            clip.emit_edge_dispatch(self.original,self.prerequisite_candidate(800),base_va=BASE,width=1024,height=768)

    def test_edge_x86_world_bounds_scope_and_native_present_order(self):
        cases=[]
        for scroll_x,scroll_y in ((10,17),(45,17),(10,49),(45,49)):
            for column,row in ((15,0),(0,11),(15,11)):
                for present in (0,1):
                    cases.append({"name":"edge","regs":[column,row,0,0],"args":[],"esi":present,
                                  "scroll_x":scroll_x,"scroll_y":scroll_y})
        reports=self.run_cases(1024,768,cases,edges=True)
        bundle=clip.emit_edge_dispatch(self.original,self.prerequisite_candidate(),base_va=BASE,width=1024,height=768)
        for case,report in zip(cases,reports):
            col,row=case["regs"][:2]
            wx,wy=case["scroll_x"]+col,case["scroll_y"]+row
            clear=wx>=60 or wy>=60
            l,t,r,b=32+64*col,16+64*row,min(1023,95+64*col),min(767,79+64*row)
            records=report["records"]
            self.assertEqual(report["state"][0],2 if clear else 1,case)
            self.assertEqual([x[0] for x in records],([2,14] if clear else [4])+([5,6,7] if case["esi"] else []),case)
            self.assertEqual(records[0][12:14],[bundle.entries["clipped_vtable"],SURFACE])
            if clear:
                self.assertEqual(records[0][1:7],[SURFACE,t,r,l,b,1])
                self.assertEqual(records[1][1:5],[l,r,b,t])
                self.assertEqual(records[1][12:14],[bundle.entries["clipped_vtable"],SURFACE])
            else:
                self.assertEqual(records[0][1:3],[l,GAME_DATA+1400*wx+14*wy])
                self.assertEqual(records[0][4],t)
            self.assertEqual(report["vtable"],clip.MEMORY_VTABLE)
            self.assertEqual(report["render"],0x12345000)
            if case["esi"]:
                dirty,blit,cursor=records[2 if clear else 1:]
                self.assertEqual(dirty[1:6],[0x544CD8,t,r+1,l,b+1])
                self.assertEqual(blit[1:9],[SURFACE,l,t,0,r,b,l,t])
                self.assertEqual(cursor[1],0x544CD8)
                for call in (dirty,blit,cursor):
                    self.assertEqual(call[12:14],[clip.MEMORY_VTABLE,0x12345000])

    def test_edge_full_and_incremental_refresh_actual_partial_cells(self):
        cases=[{"name":"edge_full","regs":[0,0,0,0],"args":[]},
               {"name":"edge_full","regs":[1,0,0,0],"args":[],"scroll_x":45,"scroll_y":49,"cursor":0},
               {"name":"edge_incremental","regs":[25,0,0,28],"args":[]},
               {"name":"edge_incremental","regs":[24,0,0,27],"args":[]}]
        reports=self.run_cases(1024,768,cases,edges=True)
        self.assertEqual(reports[0]["state"][0],1)
        self.assertEqual(len(reports[0]["records"]),27)
        expected=clip.edge_cells(width=1024,height=768,map_width=60,map_height=60,scroll_x=10,scroll_y=17)
        self.assertEqual([(r[1],r[4]) for r in reports[0]["records"]],[(c.rect[0],c.rect[1]) for c in expected])
        self.assertEqual(reports[1]["state"][0],1)
        self.assertEqual([r[0] for r in reports[1]["records"]],[2,14,5,6]*27)
        self.assertEqual([r[0] for r in reports[2]["records"]],[4,5,6,7])
        self.assertEqual(reports[2]["records"][0][1:3],[992,GAME_DATA+1400*25+14*28])
        self.assertEqual(reports[3]["state"][0],0)
        self.assertEqual(reports[3]["records"],[])
        small=self.run_cases(800,600,[{"name":"edge_full","regs":[0,0,0,0],"args":[]}],edges=True)[0]
        self.assertEqual(len(small["records"]),12)
        self.assertEqual({r[4] for r in small["records"]},{592})

    def test_edge_rejects_unsupported_context_without_touching_native(self):
        base={"name":"edge","regs":[15,11,0,0],"args":[],"esi":0}
        changes=[{"callback":0x12345678},{"owner":1},{"map_width":101},{"map_height":0},
                 {"scroll_x":46},{"scroll_y":-1},{"esi":2},
                 {"regs":[-1,11,0,0]},{"regs":[16,11,0,0]},
                 {"regs":[15,12,0,0]},{"regs":[14,10,0,0]}]
        changes += [{"bad":bad} for bad in ("global","dimensions","pixels","vtable","game_data")]
        for report in self.run_cases(1024,768,[dict(base,**c) for c in changes],edges=True):
            self.assertEqual(report["state"][0],0)
            self.assertEqual(report["records"],[])
            self.assertEqual(report["render"],0x12345000)
        allowed=[dict(base,callback=value,regs=[15,0,0,0],owner=1) for value in (0,0x425120,0x429EC0)]
        for report in self.run_cases(1024,768,allowed,edges=True):
            self.assertEqual(report["state"][0],1)

    def test_edge_restores_existing_scoped_context_and_dash_flags(self):
        bundle=clip.emit_edge_dispatch(self.original,self.prerequisite_candidate(),base_va=BASE,width=1024,height=768)
        clone=bundle.entries["clipped_vtable"]
        case={"name":"edge","regs":[15,0,0xDEAD,0xBEEF],"args":[],"esi":0,
              "initial_vtable":clone,"initial_render":SURFACE}
        report=self.run_cases(1024,768,[case],edges=True)[0]
        self.assertEqual(report["state"][0],1)
        self.assertEqual(report["vtable"],clone)
        self.assertEqual(report["render"],SURFACE)
        # Native dashed lines use the absolute screen coordinate for phase;
        # retain the flag and original visible coordinates at the clip edge.
        report=self.run_cases(800,600,[{"name":"line","regs":[SURFACE,17,850,19],"args":[17,0x101]}],origin=(32,16))[0]
        self.assertEqual(report["records"][0][2:7],[17,799,32,17,0x101])

    def test_map_composition_native_order_and_context_restoration(self):
        cases=[{"name":"edge_composed","regs":[15,11,0,0],"args":[],"esi":1},
               {"name":"edge_composed","regs":[15,11,0,0],"args":[],"esi":0},
               {"name":"edge_full_composed","regs":[1,0,0,0],"args":[],"tooltip":1}]
        reports=self.run_cases(1024,768,cases,composition=True)
        self.assertEqual([r[0] for r in reports[0]["records"]],[4,8,5,6,7])
        self.assertEqual([r[0] for r in reports[1]["records"]],[4,8])
        self.assertEqual([r[0] for r in reports[2]["records"]],[4]*27+[8,5,6,5,6,5,6,7])
        for report in reports:
            self.assertEqual(report["state"][0],1)
            panel=next(r for r in report["records"] if r[0]==8)
            self.assertEqual(panel[1],DESCRIPTORS)
            self.assertEqual(panel[4],0,"descriptor draw must not present or poll input")
            self.assertEqual(panel[13],SURFACE)
            self.assertEqual(report["render"],0x12345000)
            self.assertEqual(report["vtable"],clip.MEMORY_VTABLE)

    def test_primary_tooltip_exclusion_is_exact_and_map_pixels_not_dropped(self):
        rng=random.Random(592)
        rects=[(32,16,799,599),(200,590,580,599),(240,586,553,599),(32,16,60,100),
               (240,585,240,586),(554,586,554,599)]
        rects += [(l,t,r,b) for l,t,r,b in
                  ((rng.randrange(32,800),rng.randrange(16,600),rng.randrange(32,800),rng.randrange(16,600)) for _ in range(60)) if l<=r and t<=b]
        cases=[{"name":"present_map_rect","regs":[l,t,r,b],"args":[],"tooltip":1,"cursor":0} for l,t,r,b in rects]
        reports=self.run_cases(800,600,cases,composition=True)
        tooltip=inside_pixels((240,586,553,599),800,600)
        for rect,report in zip(rects,reports):
            self.assertEqual(report["state"][0],1,rect)
            observed=set()
            for dirty,copy in zip(report["records"][::2],report["records"][1::2]):
                self.assertEqual((dirty[0],copy[0]),(5,6))
                l,t=copy[2:4];r,b=copy[5:7]
                pixels=inside_pixels((l,t,r,b),800,600)
                self.assertFalse(pixels & tooltip)
                self.assertFalse(pixels & observed)
                observed |= pixels
                self.assertEqual(dirty[2:6],[t,r+1,l,b+1])
            self.assertEqual(observed,inside_pixels(rect,800,600)-tooltip,rect)

    def test_composition_rejects_unproven_owners_before_drawing(self):
        base={"name":"edge_composed","regs":[15,11,0,0],"args":[],"esi":1}
        changes=[{"render_hook":0x4617A0},{"owner":1},{"post_tile_callback":0x425120},
                 {"command_sprites":0},{"current_player":5},{"current_player":-1},{"interactive":0,"turn_sprites":0},
                 {"tooltip":1,"tooltip_left":160},{"bad":"descriptor"},{"bad":"descriptor_callback"},
                 {"bad":"descriptor_end"},{"esi":2},{"bad":"game_data"},{"bad":"vtable"}]
        for report in self.run_cases(1024,768,[dict(base,**change) for change in changes],composition=True):
            self.assertEqual(report["state"][0],0)
            self.assertEqual(report["records"],[])
            self.assertEqual(report["render"],0x12345000)

    def test_composition_candidate_contract_is_strict(self):
        for va in (clip.COMMAND_DESCRIPTORS,clip.COMMAND_DESCRIPTORS+28,0x419D8E,0x422880):
            candidate=bytearray(self.prerequisite_candidate())
            candidate[clip.file_offset(candidate,va,1)]^=1
            with self.assertRaises(ValueError):
                clip.emit_map_composition(self.original,bytes(candidate),base_va=BASE,width=1024,height=768)

    def test_general_cell_incremental_route_and_nonanimated_turn_owner(self):
        cases=[{"name":"cell_incremental_composed","regs":[24,0,0,27],"args":[]},
               {"name":"cell_composed","regs":[3,2,0,0],"args":[],"esi":1,"interactive":0,"command_sprites":0},
               {"name":"edge_full_composed","regs":[0,0,0,0],"args":[],"interactive":0}]
        reports=self.run_cases(1024,768,cases,composition=True)
        self.assertEqual([r[0] for r in reports[0]["records"]],[4,8,5,6,7])
        self.assertEqual(reports[0]["records"][0][1:3],[928,GAME_DATA+1400*24+14*27])
        self.assertEqual([r[0] for r in reports[1]["records"]],[4,9,3,9,3,10,11,5,6,7])
        self.assertEqual([r[0] for r in reports[2]["records"]],[4]*27+[9,3,9,3,10,11])
        for report in reports[1:]:
            banner_sprites=[r for r in report["records"] if r[0]==3]
            self.assertEqual(len(banner_sprites),2)
            self.assertTrue(all(r[1]==SURFACE and r[13]==SURFACE for r in banner_sprites))
        for report in reports:
            self.assertEqual(report["state"][0],1)
            self.assertEqual(report["render"],0x12345000)
            self.assertEqual(report["vtable"],clip.MEMORY_VTABLE)

    def test_offscreen_turn_prefix_has_no_primary_copy_and_cleans_cdecl_args(self):
        cases=[{"name":"edge_full_composed","regs":[0,0,0,0],"args":[],"interactive":0,"turn_number":1},
               {"name":"turn_banner_offscreen","regs":[1,0,0,0],"args":[]}]
        reports=self.run_cases(1024,768,cases,composition=True)
        self.assertEqual([r[0] for r in reports[0]["records"]],[4]*27+[9,3,9,3,10,11,12,13])
        self.assertFalse(any(r[0] in (5,6,7) for r in reports[0]["records"]),"offscreen draw reached dirty/copy/cursor")
        self.assertEqual(reports[0]["state"][0],1)
        text=reports[0]["records"][-1]
        self.assertEqual(text[5:9],[837,701,0x4EC7C5,7])
        self.assertEqual(reports[1]["state"][0],0)
        self.assertEqual(reports[1]["records"],[])

    def test_native_turn_banner_uses_the_exact_relocated_dock_delta(self):
        # Independent native instruction expectations, then actual generated
        # x86 at six geometries. Coordinates are layout values, not HIGHLOW VAs.
        for va,expected in ((0x40A637,"b990010000"),(0x40A644,"bba0010000"),
                            (0x40A686,"bb38020000"),(0x40A693,"b994010000"),
                            (0x40A6CD,"68b4010000"),(0x40A6D2,"6860020000"),
                            (0x40A6D7,"68a0010000"),(0x40A719,"6895010000"),
                            (0x40A71E,"68a5010000")):
            off=clip.file_offset(self.original,va,5)
            self.assertEqual(self.original[off:off+5],bytes.fromhex(expected))
        self.assertEqual(struct.unpack_from("<ii",self.original,
            clip.file_offset(self.original,clip.COMMAND_DESCRIPTORS,8)),(416,400))
        for width,height in ((800,600),(1024,768),(1280,720),(1280,960),(1920,1080),(802,602)):
            report=self.run_cases(width,height,[{"name":"compose_panel","regs":[0,0,0,0],
                "args":[],"interactive":0,"turn_number":1}],composition=True)[0]
            rows=report["records"]
            self.assertEqual([r[0] for r in rows],[9,3,9,3,10,11,12,13])
            sprites=[r for r in rows if r[0]==3]
            self.assertEqual([r[2:4] for r in sprites],[[width-192,height-72],[width-40,height-68]])
            self.assertTrue(all(r[5:9]==[32,16,width-1,height-1] for r in sprites))
            self.assertEqual(rows[5][5:9],[width-192,width,height-36,3])
            self.assertEqual(rows[-1][5:9],[width-187,height-67,0x4EC7C5,7])
            self.assertEqual(report["state"][0],1)
            self.assertEqual(report["render"],0x12345000)
            self.assertEqual(report["vtable"],clip.MEMORY_VTABLE)

    def test_complete_absolute_metadata_and_real_cpu_image_rebase(self):
        delta=0x02000000
        bundle=clip.emit_map_composition(self.original,self.prerequisite_candidate(),base_va=BASE,width=1024,height=768)
        offsets=clip.absolute_relocation_offsets(bundle)
        self.assertTrue(any(offset%4 for offset in offsets),"x86 absolute fields need not be aligned")
        relocated=bytearray(bundle.code)
        for offset in offsets:
            struct.pack_into("<I",relocated,offset,struct.unpack_from("<I",relocated,offset)[0]+delta)
        rebased=replace(bundle,base_va=BASE+delta,code=bytes(relocated),
                        entries={k:v+delta for k,v in bundle.entries.items()},
                        relocations=tuple(replace(r,target=r.target+delta) for r in bundle.relocations))
        self.assertEqual(clip.absolute_relocation_offsets(rebased),offsets)
        expected=list(clip.VTABLE_ENTRIES)
        for slot,name in ((5,"line"),(6,"outline"),(7,"fill"),(13,"sprite")):expected[slot]=bundle.entries[name]
        table_offset=bundle.entries["clipped_vtable"]-BASE
        self.assertEqual(struct.unpack_from("<20I",relocated,table_offset),tuple(v+delta if v else 0 for v in expected))
        for slot,value in enumerate(expected):
            self.assertEqual(table_offset+4*slot in offsets,bool(value))
        for r in bundle.relocations:
            if r.kind=="rel32":self.assertEqual(relocated[r.offset:r.offset+4],bundle.code[r.offset:r.offset+4])
        cases=[{"name":"cell_incremental_composed","regs":[25,0,0,28],"args":[],"callback":0x425120+delta},
               {"name":"edge","regs":[15,0,0,0],"args":[],"esi":1,"callback":0x429EC0+delta},
               {"name":"edge_composed","regs":[15,0,0,0],"args":[],"esi":1,"scroll_x":45},
               {"name":"edge_full_composed","regs":[0,0,0,0],"args":[],"interactive":0,"turn_number":1},
               {"name":"present_map_rect","regs":[32,16,1023,767],"args":[],"tooltip":1}]
        reports=self.run_cases(1024,768,cases,composition=True,rebase_delta=delta)
        self.assertEqual([r[0] for r in reports[2]["records"]],[2,14,8,5,6,7])
        self.assertEqual(reports[2]["state"][0],2)
        for case,report in zip(cases,reports):
            self.assertGreater(report["state"][0],0,case)
            self.assertEqual(report["vtable"],clip.MEMORY_VTABLE+delta)
            self.assertEqual(report["render"],0x12345000)
            for row in report["records"]:
                if row[0] in (5,7):self.assertEqual(row[1],0x544CD8+delta)
                if row[0]==8:self.assertEqual(row[1],DESCRIPTORS+delta)
                if row[0]==13:self.assertEqual(row[7],0x4EC7C5+delta)
        # Exercise the physical adapter independently at the moved allocation.
        reports=self.run_cases(800,600,[{"name":"sprite","regs":[SURFACE+delta,799,599,SPRITE+delta],
                                      "args":[-1]*4+[1,0,0]}],rebase_delta=delta)
        self.assertEqual(reports[0]["records"][0][1],SURFACE+delta)

    def test_relocation_contract_rejects_bad_metadata(self):
        bundle=clip.emit_map_composition(self.original,self.prerequisite_candidate(),base_va=BASE,width=1024,height=768)
        first=bundle.relocations[0]
        for bad in (replace(first,kind="guess"),replace(first,offset=-1),replace(first,target=0),replace(first,target=first.target+1)):
            with self.assertRaises(ValueError):
                clip.absolute_relocation_offsets(replace(bundle,relocations=(bad,)+bundle.relocations[1:]))
        with self.assertRaises(ValueError):
            clip.absolute_relocation_offsets(replace(bundle,relocations=bundle.relocations+(first,)))


if __name__=="__main__":unittest.main()
