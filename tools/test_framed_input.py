#!/usr/bin/env python3
"""Run uninstalled mouse gates in synthetic x86 memory, never game input.

The known original is read for byte authentication. Native predicates are
cloned into fixture memory with their explicit original HIGHLOW fields; no
keyboard, mouse, debugger, window or runnable game candidate is produced.
"""
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
from src.patcher import framed_input as gate
from src.patcher import partial_tile_clip as clip
import test_partial_tile_clip as runner

SIZES = ((640,480),(800,600),(1024,768),(1280,720),(1280,960),(1920,1080),(802,602))
FLAGS = 0xED7
FLAGS_MASK = 0xCD5
GLOBAL_MAP = dict(runner.GLOBALS)
GLOBAL_MAP.update(mouse_x=runner.GLOBAL+64, mouse_y=runner.GLOBAL+68,
                  mouse_shift=runner.GLOBAL+72, minimap_origin=runner.GLOBAL+76,
                  minimap_top=runner.GLOBAL+78, minimap_size=runner.GLOBAL+80,
                  minimap_height=runner.GLOBAL+82)
STUBS = {'native_minimap_gate':runner.BASE+0x6000,'native_click_gate':runner.BASE+0x6400}


def replace_once(text, old, new):
    if text.count(old)!=1: raise AssertionError('synthetic fixture source anchor differs')
    return text.replace(old,new)


def fixture_source():
    source=runner.CSHARP
    diagnostics=r'''
 [DllImport("kernel32")] static extern uint SetErrorMode(uint mode);
 [UnmanagedFunctionPointer(CallingConvention.Winapi)] delegate int FaultHandler(IntPtr info);
 [DllImport("kernel32")] static extern IntPtr AddVectoredExceptionHandler(uint first,FaultHandler handler);
 static FaultHandler faultHandler=OnFault;
 static int OnFault(IntPtr info){
  IntPtr record=Marshal.ReadIntPtr(info),context=Marshal.ReadIntPtr(info,4);
  uint code=unchecked((uint)Marshal.ReadInt32(record));
  if(code==0xc0000005){Console.Error.WriteLine("Synthetic x86 AV EIP="+Marshal.ReadInt32(context,184).ToString("X8")+" EAX="+Marshal.ReadInt32(context,176).ToString("X8")+" ESI="+Marshal.ReadInt32(context,160).ToString("X8"));}
  return 0;
 }
'''
    source=replace_once(source,' static int B,Surface,Sprite,Global,Record,Output,GameData;',
                        ' static int B,Surface,Sprite,Global,Record,Output,GameData;'+diagnostics)
    source=replace_once(source,'   if(IntPtr.Size!=4)throw new Exception("Fixture must execute as x86");',
                        '   SetErrorMode(3);AddVectoredExceptionHandler(1,faultHandler);\n'
                        '   if(IntPtr.Size!=4)throw new Exception("Fixture must execute as x86");')
    setup=r'''
    W(Global+64,Get(c,"raw_x",100));W(Global+68,Get(c,"raw_y",100));W(Global+72,Get(c,"shift",0));
    int mw=Get(c,"mini_width",214),mh=Get(c,"mini_height",214);
    int ml=Get(c,"mini_left",I(root["width"])-32-mw),mt=Get(c,"mini_top",16);
    W(Global+76,(ml&65535)|((mt&65535)<<16));W(Global+80,(mw&65535)|((mh&65535)<<16));
    W(Global+128+44,Get(c,"click",1));
    W(GameData+0x23ec7,Get(c,"minimap_player",0));
    for(int p=0;p<5;p++)W(GameData+1423*p+0x2230f,
     Get(c,"minimap_enabled_player",-1)<0 || Get(c,"minimap_enabled_player",-1)==p ? Get(c,"minimap_enabled",0) : 0);
    if(Get(c,"null_surface",0)!=0)W(Global,0);
    if(Get(c,"primary_surface",0)!=0)W(Global,0x51d4c0+delta);
    // All target data is read-only for this helper and the actual predicates.
    byte[] beforeGlobal=new byte[512],beforeSurface=new byte[256],beforeGame=new byte[0x25000];
    Marshal.Copy((IntPtr)Global,beforeGlobal,0,beforeGlobal.Length);
    Marshal.Copy((IntPtr)Surface,beforeSurface,0,beforeSurface.Length);
    Marshal.Copy((IntPtr)GameData,beforeGame,0,beforeGame.Length);
'''
    source=replace_once(source,'    var regs=(IList)c["regs"];var args=(IList)c["args"];',
                        setup+'    var regs=(IList)c["regs"];var args=(IList)c["args"];')
    source=replace_once(source,'    b.Add(0xE8);Imm(b,I(c["entry"])-(B+0x8000+b.Count+4));',
                        '    b.Add(0x68);Imm(b,0xED7);b.Add(0x9D);\n'
                        '    b.Add(0xE8);Imm(b,I(c["entry"])-(B+0x8000+b.Count+4));')
    source=replace_once(source,'Save(b,0x15,Output+36);',
                        'Save(b,0x15,Output+36);b.AddRange(new byte[]{0x9c,0x8f,0x05});Imm(b,Output+16);b.Add(0xFC);')
    source=replace_once(source,'new int[]{0,4,8,12,20,24,28,32,36}',
                        'new int[]{0,4,8,12,20,24,28,32,36,16}')
    check=r'''
    for(int k=0;k<beforeGlobal.Length;k++)if(Marshal.ReadByte((IntPtr)(Global+k))!=beforeGlobal[k])throw new Exception("Input helper wrote global state");
    for(int k=0;k<beforeSurface.Length;k++)if(Marshal.ReadByte((IntPtr)(Surface+k))!=beforeSurface[k])throw new Exception("Input helper wrote surface state");
    for(int k=0;k<beforeGame.Length;k++)if(Marshal.ReadByte((IntPtr)(GameData+k))!=beforeGame[k])throw new Exception("Input helper wrote game data");
'''
    return replace_once(source,'    int count=Marshal.ReadInt32((IntPtr)Record);',
                        check+'    int count=Marshal.ReadInt32((IntPtr)Record);')


def native_predicate(original, kind, delta):
    # This recorder preserves every register/flag and never reads the target
    # surface, allowing null-map preflight and click-first negatives safely.
    b=bytearray.fromhex('9c6089e5bf')+struct.pack('<I',runner.RECORD+delta)
    b+=bytes.fromhex('8b376bf640ff078d7c3704c707')+struct.pack('<I',kind)
    for dest,source in ((4,28),(8,16),(12,24),(16,20),(20,32),(24,36)):
        b+=bytes((0x8b,0x45,source,0x89,0x47,dest))
    b+=bytes.fromhex('619d')
    va,size=(gate.MINIMAP_GATE,126) if kind==1 else (gate.CLICK_GATE,13)
    off=clip.file_offset(original,va,size);native=bytearray(original[off:off+size])
    mapping={clip.GAME_DATA_GLOBAL:GLOBAL_MAP['game_data_global'],gate.MOUSE_X:GLOBAL_MAP['mouse_x'],
             gate.MOUSE_Y:GLOBAL_MAP['mouse_y'],gate.MOUSE_SHIFT:GLOBAL_MAP['mouse_shift'],
             gate.MINIMAP_ORIGIN:GLOBAL_MAP['minimap_origin'],gate.MINIMAP_ORIGIN+2:GLOBAL_MAP['minimap_top'],
             gate.MINIMAP_SIZE:GLOBAL_MAP['minimap_size'],gate.MINIMAP_SIZE+2:GLOBAL_MAP['minimap_height']}
    fields=clip._original_highlow_fields(original,va,size)
    found=set()
    for pos in fields:
        value=struct.unpack_from('<I',native,pos)[0]
        if value not in mapping:raise AssertionError('unreviewed native predicate absolute operand')
        found.add(value);struct.pack_into('<I',native,pos,mapping[value]+delta)
    if kind==1 and found!=set(mapping):raise AssertionError('native minimap operand inventory differs')
    if kind==2 and fields:raise AssertionError('click predicate unexpectedly relocated')
    return bytes(b+native)


def expected_allowed(width,height,c):
    """Independent scalar input expectation; never calls producer geometry."""
    if c.get('click',1)&1==0 and c['name']=='click_gate':return False
    if (c.get('bad') or c.get('null_surface') or c.get('primary_surface') or
        c.get('current_player',0) not in range(5) or not c.get('interactive',1) or
        c.get('minimap_player',0) not in range(5) or c.get('render_hook',0x40ad40)!=0x40ad40 or
        c.get('owner',0)!=0 or c.get('post_tile_callback',0)!=0 or
        c.get('callback',0) not in (0,0x425120,0x429ec0) or
        c.get('initial_vtable',0x50ee24)!=0x50ee24):return False
    shift=c.get('shift',0)&31
    x=runner.signed(c.get('raw_x',100)&0xffffffff)>>shift
    y=runner.signed(c.get('raw_y',100)&0xffffffff)>>shift
    if not (32<=x<width-32 and 16<=y<height-16):return False
    if x>=width-224 and y>=height-80:return False
    enabled=(c.get('minimap_enabled',0) and
             c.get('minimap_enabled_player',c.get('minimap_player',0))==c.get('minimap_player',0))
    if enabled:
        mw,mh=c.get('mini_width',214),c.get('mini_height',214)
        ml,mt=c.get('mini_left',width-32-mw),c.get('mini_top',16)
        if not (mw>0 and mh>0 and ml>=32 and ml+mw==width-32 and mt==16 and mt+mh<=height-16):return False
        if ml<=x<ml+mw and mt<=y<mt+mh:return False
    fw,fh=(width-64)//64,(height-32)//64
    mw,mh=c.get('map_width',60),c.get('map_height',60)
    sx,sy=c.get('scroll_x',10),c.get('scroll_y',17)
    return (1<=mw<=100 and 1<=mh<=100 and mw>=fw and mh>=fh and
            0<=sx<=mw-fw and 0<=sy<=mh-fh and sx+(x-32)//64<mw and sy+(y-16)//64<mh)


@unittest.skipUnless(runner.ORIGINAL.is_file(),'requires known original for byte authentication')
class ContractTests(unittest.TestCase):
    def test_exact_five_spans_no_highlow_and_call_targets(self):
        original=runner.ORIGINAL.read_bytes();before=bytes(original)
        bundle=gate.emit_input_bundle(original,base_va=runner.BASE,width=800,height=600)
        self.assertFalse(bundle.installation_ready)
        self.assertEqual(original,before)
        self.assertEqual([p.va for p in bundle.hook_sites],[0x4084a9,0x407f3c,0x408039])
        self.assertEqual([p.va for p in bundle.scalar_patches],[0x40855d,0x4080aa])
        fields=gate._native_highlow_vas(original)
        for p in (*bundle.hook_sites,*bundle.scalar_patches):
            self.assertEqual(original[p.offset:p.offset+len(p.old_bytes)],p.old_bytes)
            self.assertEqual(p.offset,p.rva-0xc00)
            self.assertEqual(len(p.new_bytes),len(p.old_bytes))
            self.assertFalse(p.removed_highlow_vas)
            self.assertFalse(any(f<p.va+len(p.old_bytes) and f+4>p.va for f in fields))
        for p in bundle.hook_sites:
            self.assertEqual(p.new_bytes[0],0xe8)
            self.assertEqual(p.va+5+struct.unpack_from('<i',p.new_bytes,1)[0],p.relocations[0].target)
            self.assertEqual((p.relocations[0].offset,p.relocations[0].kind),(1,'rel32'))
        for p in bundle.scalar_patches:
            self.assertEqual(p.new_bytes,b'\x90'*6);self.assertFalse(p.relocations)
        for r in bundle.relocations:
            actual=struct.unpack_from('<I',bundle.code,r.offset)[0]
            self.assertEqual(actual,(r.target if r.kind=='abs32' else r.target-bundle.base_va-r.offset-4)&0xffffffff)
        self.assertEqual(len(clip.absolute_relocation_offsets(bundle)),sum(r.kind=='abs32' for r in bundle.relocations))

    def test_unknown_original_or_dimensions_allocation_fail_closed(self):
        original=runner.ORIGINAL.read_bytes();changed=bytearray(original);changed[0x100]^=1
        with self.assertRaisesRegex(ValueError,'SHA-256'):
            gate.emit_input_bundle(bytes(changed),base_va=runner.BASE,width=800,height=600)
        for width,height in ((639,480),(800,601),(True,600),(8194,600)):
            with self.assertRaises(ValueError):gate.emit_input_bundle(original,base_va=runner.BASE,width=width,height=height)
        for base in (True,-1,0x80000000):
            with self.assertRaises(ValueError):gate.emit_input_bundle(original,base_va=base,width=800,height=600)


@unittest.skipUnless(os.name=='nt' and runner.CSC.is_file() and runner.ORIGINAL.is_file(),
                     'requires x86 fixture compiler and authenticated original')
class InputX86Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='clash-framed-input-fixture-');cls.addClassCleanup(cls.temp.cleanup)
        root=Path(cls.temp.name);cls.exe=root/'fixture.exe';source=root/'fixture.cs'
        source.write_text(fixture_source(),encoding='utf-8')
        result=subprocess.run([str(runner.CSC),'/nologo','/platform:x86','/optimize+',
                               '/r:System.Web.Extensions.dll',f'/out:{cls.exe}',str(source)],
                              capture_output=True,text=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:raise AssertionError(result.stdout+result.stderr)
        cls.original=runner.ORIGINAL.read_bytes();cls.cache={}

    def execute(self,width,height,cases,delta=0):
        if (width,height) not in self.cache:
            self.cache[width,height]=gate.emit_input_bundle(self.original,base_va=runner.BASE,width=width,height=height)
        bundle=self.cache[width,height];code=bytearray(bundle.code)
        self.assertLess(len(code),0x6000)
        for r in bundle.relocations:
            if r.kind=='abs32':
                struct.pack_into('<I',code,r.offset,GLOBAL_MAP.get(r.purpose,r.target)+delta)
            else:struct.pack_into('<i',code,r.offset,STUBS[r.purpose]-runner.BASE-r.offset-4)
        payload=dict(code=code.hex(),width=width,height=height,base=runner.BASE+delta,image_delta=delta,
                     stubs={str(STUBS[name]+delta):native_predicate(self.original,i+1,delta).hex()
                            for i,name in enumerate(STUBS)},cases=[])
        for case in cases:
            row=dict(case,args=[],regs=[runner.GLOBAL+128+delta,0x22334455,0x33445566,0x44556677],
                     entry=bundle.entries[case['name']]+delta)
            for field in ('render_hook','callback','initial_vtable'):
                if row.get(field,0):row[field]+=delta
            payload['cases'].append(row)
        result=subprocess.run([str(self.exe)],input=json.dumps(payload),capture_output=True,text=True,
                              timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        reports=json.loads(result.stdout)
        for case,report in zip(cases,reports):
            allowed=expected_allowed(width,height,case)
            self.assertEqual(report['state'][0],int(allowed if case['name']=='click_gate' else not allowed),case)
            state=report['state'];self.assertEqual(state[1:4],[0x11223344,0x55667788,0x99aabbcc])
            self.assertEqual(state[4],state[5],'ESP must return exactly')
            self.assertEqual(state[6:9],[0x22334455,0x33445566,0x44556677])
            self.assertEqual(state[9]&FLAGS_MASK,FLAGS&FLAGS_MASK,'entry flags/DF must survive')
            if case['name']=='click_gate':
                self.assertEqual(report['records'][0][0],2,'native click must precede extra checks')
                self.assertEqual(report['records'][0][1],runner.GLOBAL+128+delta,'native EAX argument changed')
        return reports

    @staticmethod
    def both(rows):return [dict(row,name=name) for row in rows for name in ('minimap_gate','click_gate')]

    def test_all_edges_partial_pixels_and_old_panel_terrain(self):
        for w,h in SIZES:
            points=[(32,16),(31,16),(32,15),(w-33,250),(w-32,250),(80,h-17),(80,h-16),
                    (w-225,h-17),(w-224,h-80),(w-33,h-17),(w-225,h-80),
                    (32+6*64,16+6*64),(32+7*64,16+6*64),(w-1,h-1),(-1,100),(100,-1)]
            cases=self.both([dict(raw_x=x,raw_y=y,scroll_x=0,scroll_y=0) for x,y in points])
            self.execute(w,h,cases)
            if w>=800:
                self.assertTrue(expected_allowed(w,h,dict(name='click_gate',raw_x=416,raw_y=400,scroll_x=0,scroll_y=0)))

    def test_native_enabled_minimap_interior_edges_disabled_and_dynamic_backing(self):
        w,h=1024,768
        for mw,mh in ((214,214),(134,94),(254,174)):
            left=w-32-mw
            points=[(left-1,16),(left,16),(left,17),(left+1,17),(w-33,16),(w-33,16+mh-1),
                    (left,16+mh),(left+1,16+mh)]
            rows=[dict(raw_x=x,raw_y=y,mini_width=mw,mini_height=mh,minimap_enabled=enabled)
                  for x,y in points for enabled in (0,1)]
            self.execute(w,h,self.both(rows))
        for wrong in ({'mini_left':700},{'mini_top':15},{'mini_width':0},{'mini_height':0},
                      {'mini_height':1000},{'mini_left':0}):
            self.execute(w,h,self.both([dict(wrong,minimap_enabled=1,raw_x=40,raw_y=300)]))

    def test_context_players_callbacks_flags_and_native_gate_order(self):
        rows=[dict(current_player=p,minimap_player=m) for p in range(5) for m in range(5)]
        rows += [dict(callback=c) for c in (0,0x425120,0x429ec0,0x1234)]
        rows += [dict(current_player=p) for p in (-1,5,0x7fffffff)]
        rows += [dict(minimap_player=p) for p in (-1,5,0x7fffffff)]
        rows += [dict(interactive=0),dict(owner=1),dict(post_tile_callback=1),dict(render_hook=0x406740),
                 dict(null_surface=1),dict(primary_surface=1)]
        rows += [dict(bad=b) for b in ('dimensions','pixels','vtable','game_data')]
        rows += [dict(current_player=1,minimap_player=selector,minimap_enabled=1,
                      minimap_enabled_player=enabled,raw_x=600,raw_y=100)
                 for selector,enabled in ((3,3),(3,1),(1,3),(1,1))]
        self.execute(800,600,self.both(rows))
        cases=[dict(name='click_gate',click=0,bad='game_data'),dict(name='minimap_gate',bad='game_data'),
               dict(name='click_gate',click=1,bad='game_data'),dict(name='click_gate',click=2),
               dict(name='click_gate',click=3),dict(name='minimap_gate',raw_x=31)]
        reports=self.execute(800,600,cases)
        self.assertEqual([[r[0] for r in x['records']] for x in reports],[[2],[],[2],[2],[2,1],[1]])

    def test_world_scroll_bounds_and_partial_outside_world(self):
        rows=[]
        for field in ('map_width','map_height'):
            rows += [dict({field:n},scroll_x=0,scroll_y=0) for n in (-1,0,1,7,8,10,11,100,101,0x7fffffff)]
        for field in ('scroll_x','scroll_y'):
            rows += [{field:n} for n in (-1,0,49,50,52,53,0x7fffffff)]
        # Right partial column11 is outside a world at max floor-clamped X.
        rows += [dict(raw_x=736,raw_y=300,scroll_x=s) for s in (48,49)]
        # Bottom partial row8 likewise; use x outside the command footprint.
        rows += [dict(raw_x=100,raw_y=528,scroll_y=s) for s in (51,52)]
        self.execute(800,600,self.both(rows))

    def test_actual_arithmetic_shift_and_rebased_code(self):
        rows=[]
        for shift in (0,1,2,3,7,31,32,33,255):
            for x,y in ((100,100),(31,100),(576,520),(-1,100),(767,300)):
                rawx=(x<<(shift&31))&0xffffffff;rawy=(y<<(shift&31))&0xffffffff
                rows.append(dict(raw_x=rawx,raw_y=rawy,shift=shift))
        rows += [dict(current_player=4,minimap_player=3,callback=c,minimap_enabled=1,raw_x=554,raw_y=16)
                 for c in (0,0x425120,0x429ec0)]
        for delta in (0,0x02000000,0x04000000):self.execute(800,600,self.both(rows),delta=delta)


if __name__=='__main__':unittest.main()
