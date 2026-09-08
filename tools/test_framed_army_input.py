#!/usr/bin/env python3
"""Source/relocation contracts and actual emitted x86 on synthetic army data.

Only a temporary synthetic fixture process runs; no game, debugger, input,
candidate executable or target data is created or changed.
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
from src.patcher import framed_army_input as army
from src.patcher import partial_tile_clip as clip
from tools import build_framed_modal_candidate as builder
import test_partial_tile_clip as runner
import test_framed_input as input_fixture

SIZES = ((800,600),(1024,768),(1280,720),(1280,960),(1920,1080),(802,602))
GLOBALS = dict(input_fixture.GLOBAL_MAP)
GLOBALS.update(army_selected=runner.GLOBAL+84, army_prior=runner.GLOBAL+88,
               army_unit=runner.GLOBAL+92)
STUBS = dict(input_fixture.STUBS)
STUBS.update(native_squad_count=runner.BASE+0x6800,
             native_portrait_hit=runner.BASE+0x6900,
             native_portrait_miss=runner.BASE+0x6A00,
             native_portrait_invalid=runner.BASE+0x6B00)


def fixture_source():
    source = input_fixture.fixture_source()
    source = input_fixture.replace_once(source, '(UIntPtr)0x80000', '(UIntPtr)0x100000')
    source = input_fixture.replace_once(source, 'beforeGame=new byte[0x25000]', 'beforeGame=new byte[0x80000]')
    setup = r'''
    int idx=Get(c,"selected",3),prior=Get(c,"prior",idx);
    W(Global+84,idx);W(Global+88,prior);
    int army=GameData+147174+725*((idx>=0&&idx<500)?idx:3);
    W(Global+92,army+Get(c,"unit_offset",0));
    Marshal.WriteInt16((IntPtr)army,unchecked((short)Get(c,"unit_x",16)));
    Marshal.WriteInt16((IntPtr)(army+2),unchecked((short)Get(c,"unit_y",19)));
    Marshal.WriteByte((IntPtr)(army+4),unchecked((byte)Get(c,"unit_owner",Get(c,"current_player",0))));
    for(int k=0;k<10;k++)Marshal.WriteInt16((IntPtr)(army+6+31*k),
       unchecked((short)(k<Get(c,"count",8)?Get(c,"type",1):-1)));
    if(c.ContainsKey("bad_slot"))Marshal.WriteInt16((IntPtr)(army+6+31*Get(c,"bad_slot",0)),
        unchecked((short)Get(c,"bad_type",35)));
    for(int k=0;k<128;k++)Marshal.WriteByte((IntPtr)(Global+256+k),0);
    W(Global+256,Get(c,"modal_phase",0));W(Global+264,Get(c,"modal_native",0));
    W(Global+292,Get(c,"modal_fault",0));W(Global+308,Get(c,"pending_header",0));
    W(Global+312,Get(c,"pending_pixels",0));
    if(Get(c,"modal_completed",0)!=0){W(Global+296,1);W(Global+300,1);W(Global+304,2);}
'''
    return input_fixture.replace_once(source,
        '    // All target data is read-only for this helper and the actual predicates.',
        setup+'    // All target data is read-only for this helper and the actual predicates.')


def expected_owner(c):
    idx=c.get('selected',3)
    return (c.get('owner',1)==1 and c.get('render_hook',0x40ad40)==0x40ad40 and
            c.get('post_tile_callback',0)==0 and c.get('current_player',0) in range(4) and
            c.get('unit_owner',c.get('current_player',0))==c.get('current_player',0) and
            c.get('interactive',1)!=0 and 0<=idx<500 and c.get('prior',idx)==idx and
            c.get('unit_offset',0)==0 and c.get('bad')!='game_data' and
            all(c.get(k,0)==0 for k in ('modal_phase','modal_native','modal_fault','pending_header','pending_pixels')) and
            1<=c.get('map_width',60)<=100 and 1<=c.get('map_height',60)<=100 and
            0<=c.get('unit_x',16)<c.get('map_width',60) and 0<=c.get('unit_y',19)<c.get('map_height',60) and
            2<=c.get('count',8)<=10 and c.get('type',1) in range(35) and
            (c.get('bad_slot',10)>=c.get('count',8) or c.get('bad_type',35) in range(35)))


def expected_context(c):
    return (expected_owner(c) and c.get('bad') not in ('global','dimensions','pixels','vtable','game_data') and
            not c.get('null_surface') and not c.get('primary_surface') and
            c.get('initial_vtable',0x50ee24)==0x50ee24 and
            c.get('callback',0) in (0,0x425120,0x429ec0) and c.get('minimap_player',0) in range(5))


def expected(width,height,c):
    name=c['name'];shift=c.get('shift',0)&31
    x=runner.signed(c.get('raw_x',100)&0xffffffff)>>shift
    y=runner.signed(c.get('raw_y',100)&0xffffffff)>>shift
    if name=='owner_state':return int(expected_owner(c))
    if name=='selected_context':return int(expected_context(c))
    slot=(x-38)//38+1 if 38<=x<=417 and height-82<=y<=height-19 else 0
    if name=='portrait_slot':return slot if expected_context(c) else 0
    if name=='portrait_hit':return 103 if not expected_context(c) else (101 if slot else 102)
    conventional=dict(c,name='click_gate',owner=0)
    return int(expected_owner(c) and input_fixture.expected_allowed(width,height,conventional) and
               not(32<=x<=418 and height-82<=y<=height-17))


@unittest.skipUnless(runner.ORIGINAL.is_file(),'requires authenticated original for read-only contracts')
class ArmyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=runner.ORIGINAL.read_bytes()
        cls.candidate,_,_=builder.build_candidate(cls.original,'800x600',minimap_viewport=True)

    def test_exact_two_hooks_displaced_highlow_and_all_relocations(self):
        before=bytes(self.candidate)
        bundle=army.emit_army_input(self.original,self.candidate,base_va=runner.BASE,
                                   width=800,height=600,minimap_viewport=True)
        self.assertFalse(bundle.installation_ready);self.assertEqual(self.candidate,before)
        self.assertEqual(bundle.removed_highlow_vas,(0x423877,))
        self.assertEqual([p.va for p in bundle.hook_sites],[0x423875,0x423984])
        self.assertEqual([p.old.hex() for p in bundle.hook_sites],['8b15fc4c5400','e867cf0300'])
        for p in bundle.hook_sites:
            self.assertEqual(p.old,self.candidate[p.offset:p.offset+len(p.old)])
            self.assertEqual(p.offset,p.rva-0xc00);self.assertEqual(len(p.old),len(p.new))
            self.assertEqual(p.va+5+struct.unpack_from('<i',p.new,1)[0],p.relocations[0].target)
            self.assertEqual(p.relocations[0].offset,1);self.assertEqual(p.relocations[0].kind,'rel32')
        self.assertEqual(len(clip.absolute_relocation_offsets(bundle)),
                         sum(r.kind=='abs32' for r in bundle.relocations))
        # Rebase independently: all declared operands retain intended targets.
        data=bytearray(bundle.code);delta=0x02000000
        for r in bundle.relocations:
            if r.kind=='abs32':struct.pack_into('<I',data,r.offset,struct.unpack_from('<I',data,r.offset)[0]+delta)
        for r in bundle.relocations:
            actual=struct.unpack_from('<I',data,r.offset)[0]
            self.assertEqual(actual,(r.target+delta if r.kind=='abs32' else r.target-bundle.base_va-r.offset-4)&0xffffffff)
        self.assertEqual(bundle.source_contract['backing'],(32,518,418,583))
        self.assertEqual(bundle.source_contract['hit'],(38,518,417,581))

    def test_whole_candidate_and_source_unknown_inputs_fail_closed(self):
        for field in ('original','candidate'):
            args=dict(original=self.original,candidate=self.candidate,base_va=runner.BASE,width=800,height=600,minimap_viewport=True)
            changed=bytearray(args[field]);changed[-1]^=1;args[field]=bytes(changed)
            with self.assertRaises(ValueError):army.emit_army_input(**args)
        for changes in ({'width':640,'height':480},{'width':True},{'height':601},
                        {'minimap_viewport':1},{'minimap_viewport':False},{'base_va':True}):
            args=dict(original=self.original,candidate=self.candidate,base_va=runner.BASE,width=800,height=600,minimap_viewport=True);args.update(changes)
            with self.assertRaises(ValueError):army.emit_army_input(**args)
        self.assertEqual(hashlib.sha256((army.ROOT/'src/patcher/framed_input.py').read_bytes()).hexdigest(),army.INPUT_SHA256)


@unittest.skipUnless(os.name=='nt' and runner.CSC.is_file() and runner.ORIGINAL.is_file(),
                     'requires x86 synthetic compiler and authenticated original')
class ArmyX86Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='clash-army-input-x86-');cls.addClassCleanup(cls.temp.cleanup)
        root=Path(cls.temp.name);cls.exe=root/'fixture.exe';source=root/'fixture.cs'
        source.write_text(fixture_source(),encoding='utf-8')
        result=subprocess.run([str(runner.CSC),'/nologo','/platform:x86','/optimize+',
              '/r:System.Web.Extensions.dll',f'/out:{cls.exe}',str(source)],capture_output=True,text=True,
              timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:raise AssertionError(result.stdout+result.stderr)
        cls.original=runner.ORIGINAL.read_bytes();cls.cache={}

    def execute(self,width,height,cases,delta=0,full_native=False):
        if (width,height) not in self.cache:
            candidate,_,_=builder.build_candidate(self.original,f'{width}x{height}',minimap_viewport=True)
            self.cache[width,height]=army.emit_army_input(self.original,candidate,base_va=runner.BASE,
                                            width=width,height=height,minimap_viewport=True)
        bundle=self.cache[width,height];code=bytearray(bundle.code)
        for r in bundle.relocations:
            if r.kind=='abs32':
                target=(runner.GLOBAL+256+int(r.purpose.split('.')[1]) if r.purpose.startswith('army_modal_state.')
                        else GLOBALS.get(r.purpose,r.target))
                struct.pack_into('<I',code,r.offset,target+delta)
            else:
                target=STUBS.get(r.purpose,r.target)
                struct.pack_into('<i',code,r.offset,target-runner.BASE-r.offset-4)
        stubs={str(STUBS[name]+delta):input_fixture.native_predicate(self.original,i+1,delta).hex()
               for i,name in enumerate(input_fixture.STUBS)}
        pos=clip.file_offset(self.original,army.COUNT,27)
        stubs[str(STUBS['native_squad_count']+delta)]=self.original[pos:pos+27].hex()
        # These record the exact native branch choice, ESI and EDI at the body
        # continuation. They preserve flags and model no game or mouse effects.
        for name,result in (('native_portrait_hit',101),('native_portrait_miss',102),('native_portrait_invalid',103)):
            stubs[str(STUBS[name]+delta)]=(b'\xb8'+struct.pack('<I',result)+b'\xc3').hex()
        if full_native:
            # Enter through the ACTUAL native PUSH/local-stack prefix, then
            # our emitted JMP. Return through the ACTUAL native epilogues.
            # The portrait body is represented by its documented EDI=1 hover
            # result only; callbacks and world writes are never executed.
            entry=runner.BASE+0x6C00;early=runner.BASE+0x6D00
            pos=clip.file_offset(self.original,0x423860,21)
            prefix=bytearray(self.original[pos:pos+21])
            self.assertEqual(clip._original_highlow_fields(self.original,0x423860,21),{6})
            self.assertEqual(prefix[11:13],bytes.fromhex('0f84'))
            struct.pack_into('<I',prefix,6,GLOBALS['army_prior']+delta)
            struct.pack_into('<i',prefix,13,early-entry-17)
            prefix+=b'\xe9'+struct.pack('<i',bundle.entries['portrait_hit']-entry-26)
            stubs[str(entry+delta)]=prefix.hex()
            pos=clip.file_offset(self.original,0x423A9A,9)
            early_bytes=self.original[pos:pos+9]
            self.assertEqual(early_bytes.hex(),'31d289d083c42c5ac3')
            stubs[str(early+delta)]=early_bytes.hex()
            pos=clip.file_offset(self.original,0x423A8D,13)
            epilogue=self.original[pos:pos+13]
            self.assertEqual(epilogue.hex(),'89fa5b595e5f89d083c42c5ac3')
            for name in ('native_portrait_hit','native_portrait_miss','native_portrait_invalid'):
                stub=(bytes.fromhex('bf01000000') if name=='native_portrait_hit' else b'')+epilogue
                stubs[str(STUBS[name]+delta)]=stub.hex()
        payload=dict(code=code.hex(),width=width,height=height,base=runner.BASE+delta,
                     image_delta=delta,stubs=stubs,cases=[])
        for case in cases:
            row=dict(case,args=[],owner=case.get('owner',1),
                     regs=[runner.GLOBAL+128+delta,0x22334455,0x33445566,0x44556677],
                     entry=(runner.BASE+0x6C00 if full_native else bundle.entries[case['name']])+delta)
            for field in ('render_hook','callback','initial_vtable'):
                if row.get(field,0):row[field]+=delta
            payload['cases'].append(row)
        result=subprocess.run([str(self.exe)],input=json.dumps(payload),capture_output=True,text=True,
                              timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        reports=json.loads(result.stdout)
        for case,report in zip(cases,reports):
            state=report['state'];want=expected(width,height,case)
            if full_native:want=int(want==101 and case.get('prior',case.get('selected',3))!=-1)
            self.assertEqual(state[0],want,case)
            if case['name']=='portrait_hit' and not full_native:
                shift=case.get('shift',0)&31;x=runner.signed(case.get('raw_x',100)&0xffffffff)>>shift
                self.assertEqual(state[1],(x-38)//38 if want==101 else 0x11223344,case)
                self.assertEqual(state[2],0,case)
            else:self.assertEqual(state[1:3],[0x11223344,0x55667788],case)
            self.assertEqual(state[3],0x99aabbcc);self.assertEqual(state[4],state[5],'ESP changed')
            self.assertEqual(state[6:9],[0x22334455,0x33445566,0x44556677],case)
            if not full_native:
                self.assertEqual(state[9]&input_fixture.FLAGS_MASK,input_fixture.FLAGS&input_fixture.FLAGS_MASK,case)
            if case['name']=='guarded_map_click':
                self.assertEqual(report['records'][0][0],2,'native click must be first')
                self.assertEqual(report['records'][0][1],runner.GLOBAL+128+delta,'native EAX argument changed')
        return reports

    def test_portrait_edges_slots_shifts_and_native_continuations(self):
        for width,height in SIZES:
            cases=[]
            points=[(x,y) for x in (0,31,32,34,35,37,38,75,76,379,380,417,418,419)
                    for y in (height-83,height-82,height-19,height-18,height-17)]
            points.extend((38+38*k+17,height-55) for k in range(10))
            for x,y in points:
                cases.append(dict(name='portrait_slot',raw_x=x,raw_y=y))
            cases.extend(dict(name='portrait_hit',raw_x=x,raw_y=y) for x,y in points[::9])
            cases.extend(dict(name='portrait_slot',raw_x=38<<s,raw_y=(height-82)<<s,shift=s) for s in (1,2,3))
            cases.extend((dict(name='portrait_hit',bad='game_data'),dict(name='portrait_hit',prior=4),
                          dict(name='portrait_slot',raw_x=-1,raw_y=height-82)))
            self.execute(width,height,cases)

    def test_owner_state_identity_asset_bounds_and_clipped_independence(self):
        bads=[dict(owner=0),dict(owner=2),dict(render_hook=0x422020),dict(post_tile_callback=1),
              dict(selected=-1),dict(selected=500),dict(prior=4),dict(unit_offset=1),
              dict(current_player=-1),dict(current_player=4),dict(unit_owner=1),dict(interactive=0),
              dict(count=0),dict(count=1),dict(type=-2),dict(type=35),dict(bad_slot=7,bad_type=40),
              dict(unit_x=-1),dict(unit_y=-1),dict(unit_x=60),dict(unit_y=60),dict(map_width=0),
              dict(map_height=101),dict(modal_phase=1),dict(modal_native=0x1234),dict(modal_fault=1),
              dict(pending_header=1),dict(pending_pixels=1),dict(bad='game_data')]
        goods=[{},dict(selected=499),dict(count=2),dict(count=10,type=34),dict(current_player=3),
               dict(modal_completed=1),dict(initial_vtable=0x570000),dict(null_surface=1)]
        self.execute(800,600,[dict(c,name='owner_state') for c in bads+goods])
        self.execute(800,600,[dict(c,name='selected_context') for c in goods+[dict(minimap_player=5),
                         dict(callback=0x425120),dict(callback=0x429ec0),dict(callback=0x422020)]])

    def test_map_click_panel_padding_old_panel_terrain_world_and_minimap(self):
        for width,height in SIZES:
            cases=[]
            # The old row/column6 area is genuine terrain after relocation;
            # every pixel of the new387x66 backing is excluded, including trim.
            for x,y in ((420,420),(416,400),(500,440),(31,100),(32,16),
                        (32,height-82),(418,height-17),(37,height-55),(419,height-55),
                        (100,height-83),(100,height-16),(width-224,height-80),
                        (width-225,height-80),(width-33,height-17)):
                cases.append(dict(name='guarded_map_click',raw_x=x,raw_y=y))
            for x,y in ((width-246,16),(width-33,229),(width-247,16),(width-33,230)):
                cases.append(dict(name='guarded_map_click',raw_x=x,raw_y=y,minimap_enabled=1))
            cases += [dict(name='guarded_map_click',click=0,bad='game_data'),
                      dict(name='guarded_map_click',bad='game_data'),
                      dict(name='guarded_map_click',modal_phase=1),
                      dict(name='guarded_map_click',scroll_x=100),
                      dict(name='guarded_map_click',scroll_y=-1),
                      dict(name='guarded_map_click',raw_x=width-33,raw_y=100,
                           scroll_x=60-(width-64)//64),
                      dict(name='guarded_map_click',raw_x=450,raw_y=height-17,
                           scroll_y=60-(height-32)//64)]
            self.execute(width,height,cases)

    def test_real_cpu_rebase_keeps_globals_native_calls_and_flags(self):
        self.execute(1024,768,[dict(name='owner_state'),dict(name='portrait_slot',raw_x=77,raw_y=700),
                              dict(name='portrait_hit',raw_x=77,raw_y=700),
                              dict(name='guarded_map_click',raw_x=450,raw_y=420),
                              dict(name='guarded_map_click',raw_x=400,raw_y=710)],delta=0x02000000)

    def test_actual_native_64_byte_body_frame_and_both_epilogues(self):
        self.execute(1024,768,[dict(name='portrait_hit',raw_x=77,raw_y=700),
                              dict(name='portrait_hit',raw_x=450,raw_y=420),
                              dict(name='portrait_hit',prior=4),
                              dict(name='portrait_hit',selected=-1,prior=-1),
                              dict(name='portrait_hit',modal_phase=1)],
                     delta=0x02000000,full_native=True)


if __name__=='__main__':unittest.main()
