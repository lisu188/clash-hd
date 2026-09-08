"""Execute army composition wrappers in a synthetic no-window x86 process.

Only emitted wrapper instructions and inert ABI recorders run. Original/modal
bytes are read for exact contracts; no game, CDB, input, capture or candidate
output occurs. Native continuations are faithful synthetic frame epilogues.
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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.patcher import framed_army_composition as tool
from src.patcher import pe_army_extension as extension
from src.patcher import pe_extension as pe
from src.patcher import partial_tile_clip as clip
from src.patcher.framed_army_viewport import FramedArmyViewport
import test_partial_tile_clip as runner
import test_partial_tile_hooks as recorder
from test_initial_map_paint import flags,u32,rel32

BASE=runner.BASE
OWNER,OLD,DRAW,PIXEL,RUN,PASS,DENY,SHIM=(BASE+x for x in (0x9000,0x9400,0x9800,0x9C00,0xA000,0xA400,0xA800,0xB000))
SIZES=((800,600),(1024,768),(1280,720),(1280,960),(1920,1080),(802,602))
CACHE={}


def canonical(width,height):
    key=(width,height)
    if key not in CACHE:
        original=runner.ORIGINAL.read_bytes()
        candidate,metadata,pins=extension._reconstruct_modal(original,f'{width}x{height}',True)
        CACHE[key]=(original,candidate,metadata,pins)
    return CACHE[key]


def bundle(width=800,height=600):
    original,candidate,metadata,pins=canonical(width,height)
    layout=extension.allocation_layout(candidate,state_bytes=0)
    # Only source-authenticated reconstruction is memoized; emit/check every
    # hook against the actual candidate on every call. Negative binding test
    # below deliberately does not use this scoped cache substitution.
    with patch.object(extension,'_reconstruct_modal',return_value=(candidate,metadata,pins)):
        result=tool.emit_army_composition(original,candidate,base_va=layout.code_va+0x4000,
            width=width,height=height,minimap_viewport=True,
            owner_state_va=layout.code_va+0x1000,draw_army_va=layout.code_va+0x2000)
    return result


@unittest.skipUnless(runner.ORIGINAL.is_file(),'requires original read-only bytes')
class ContractTests(unittest.TestCase):
    def test_all_sizes_seven_hooks_exact_highlow_removals_and_destinations(self):
        for width,height in SIZES:
            with self.subTest(size=(width,height)):
                b=bundle(width,height);candidate=canonical(width,height)[1];image=pe.inspect_pe(candidate)
                _,locations=pe._old_relocations(candidate,image)
                self.assertEqual(len(b.hook_sites),7)
                self.assertEqual(len({s.va for s in b.hook_sites}),7)
                displaced=set()
                for site in b.hook_sites:
                    self.assertEqual(site.old,candidate[site.offset:site.offset+len(site.old)])
                    self.assertEqual(image.file_offset(site.rva,len(site.old)),site.offset)
                    for r in site.relocations:
                        self.assertEqual(r.kind,'rel32')
                        actual=site.va+r.offset+4+struct.unpack_from('<i',site.new,r.offset)[0]
                        self.assertEqual(actual,r.target)
                    for rva in locations:
                        if rva<site.rva+len(site.old) and site.rva<rva+4:
                            self.assertLessEqual(site.rva,rva);self.assertLessEqual(rva+4,site.rva+len(site.old));displaced.add(rva)
                self.assertEqual(set(b.removed_highlow_rvas),displaced)
                self.assertEqual(len(displaced),6)
                self.assertIn(0x18786,displaced)
                call=next(r for r in b.relocations if r.purpose=='draw_army')
                self.assertEqual(b.entries['compose.draw_return'],b.base_va+call.offset+4)
                self.assertEqual(b.code[call.offset+4:call.offset+7],bytes.fromhex('83f801'))
                self.assertEqual(b.source_contract['backing'],(32,height-82,418,height-17))
                seen=[]
                for r in b.relocations:
                    self.assertEqual(struct.unpack_from('<I',b.code,r.offset)[0],
                        (r.target if r.kind=='abs32' else r.target-b.base_va-r.offset-4)&0xFFFFFFFF)
                    seen.append(r.offset)
                self.assertEqual(len(seen),len(set(seen)))

    def test_mutated_candidate_and_overflowing_helper_are_rejected(self):
        original,candidate,metadata,pins=canonical(800,600);layout=extension.allocation_layout(candidate,state_bytes=0)
        args=dict(base_va=layout.code_va,width=800,height=600,minimap_viewport=True,
                  owner_state_va=layout.code_va+0x1000,draw_army_va=layout.code_va+0x2000)
        changed=bytearray(candidate);changed[0x1234]^=1
        with self.assertRaisesRegex(ValueError,'exact canonical'):
            tool.emit_army_composition(original,bytes(changed),**args)
        with patch.object(extension,'_reconstruct_modal',return_value=(candidate,metadata,pins)):
            for kwargs in ({'base_va':layout.code_va+layout.code_reservation-1},
                           {'owner_state_va':layout.code_va-1},{'draw_army_va':layout.code_va+layout.code_reservation}):
                with self.assertRaises(ValueError):tool.emit_army_composition(original,candidate,**(args|kwargs))


def observe(kind,delta=0):
    code=bytearray(recorder.recorder(kind,delta)[:-2])
    code+=b'\xa1'+u32(runner.SURFACE+184+delta)+bytes.fromhex('894728')
    code+=b'\xa1'+u32(runner.GLOBAL+8+delta)+bytes.fromhex('89472c619d')
    return code


def return_current(kind,offset,delta=0):
    return observe(kind,delta)+b'\xa1'+u32(runner.GLOBAL+offset+delta)+b'\xc3'


@unittest.skipUnless(os.name=='nt' and runner.CSC.is_file() and runner.ORIGINAL.is_file(),
                     'requires no-window x86 compiler and original read-only')
class X86Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=Path(tempfile.mkdtemp(prefix='clash-army-composition-x86-'))
        cls.exe=cls.directory/'fixture.exe'
        source=runner.CSHARP
        replacements={
            'Save(b,0x15,Output+36);':'Save(b,0x15,Output+36);b.AddRange(new byte[]{0x9c,0x8f,0x05});Imm(b,Output+16);b.Add(0xfc);',
            'new int[]{0,4,8,12,20,24,28,32,36}':'new int[]{0,4,8,12,20,24,28,32,36,16}',
            'W(Global+60,Get(c,"turn_sprites",Sprite));':
                'W(Global+60,Get(c,"turn_sprites",Sprite));W(Global+64,Get(c,"mouse_x",100));W(Global+68,Get(c,"mouse_y",100));'
                'W(Global+72,Get(c,"mouse_shift",0));W(Global+80,Get(c,"owner_result",1));'
                'W(Global+84,Get(c,"draw_result",1));W(Global+88,Get(c,"old_result",1));W(Global+92,Get(c,"pixel_result",1));',
        }
        for old,new in replacements.items():
            if source.count(old)!=1:raise AssertionError('shared runner contract changed')
            source=source.replace(old,new)
        path=cls.directory/'fixture.cs';path.write_text(source,encoding='utf-8')
        ran=subprocess.run([str(runner.CSC),'/nologo','/platform:x86','/optimize+',
            '/r:System.Web.Extensions.dll',f'/out:{cls.exe}',str(path)],capture_output=True,text=True,
            timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        if ran.returncode:raise AssertionError(ran.stdout+ran.stderr)

    def execute(self,name,cases,*,width=800,height=600,delta=0,df=False,hook_index=None):
        b=bundle(width,height);code=bytearray(b.code)
        addresses={'lower_row_owner':runner.GLOBAL+16,'map_surface_global':runner.GLOBAL,
                   'game_data_global':runner.GLOBAL+4,'mouse_x':runner.GLOBAL+64,
                   'mouse_y':runner.GLOBAL+68,'mouse_shift':runner.GLOBAL+72,'memory_vtable':clip.MEMORY_VTABLE}
        targets={'army_owner_state':OWNER,'draw_army':DRAW,'old compose-panel body':OLD,
                 'old framed pixel guard body':PIXEL}
        for r in b.relocations:
            if r.kind=='abs32':value=addresses.get(r.purpose,r.target)+delta
            else:
                target=targets[r.purpose]
                value=(target-BASE-r.offset-4)&0xFFFFFFFF
            struct.pack_into('<I',code,r.offset,value)
        old=observe(10,delta)
        # The original compose prologue already owns PUSHAD+12 local bytes.
        # Destroy working GPRs/flags and use its exact stack epilogue; its caller
        # must recover entry state and normalize only the returned EAX.
        for opcode,value in ((0xBB,0xABC00001),(0xB9,0xABC00002),(0xBA,0xABC00003),
                             (0xBE,0xABC00004),(0xBF,0xABC00005),(0xBD,0xABC00006)):
            old+=bytes([opcode])+u32(value)
        old+=bytes.fromhex('31c0f983c40c61a1')+u32(runner.GLOBAL+88+delta)+b'\xc3'
        pixel=observe(40,delta)+b'\xa1'+u32(runner.GLOBAL+92+delta)+bytes.fromhex('8944241c619dc3')
        stubs={OWNER:return_current(20,80,delta),DRAW:return_current(30,84,delta),OLD:old,PIXEL:pixel,
               PASS:observe(50,delta)+b'\xb8'+u32(1)+b'\xc3',DENY:observe(51,delta)+bytes.fromhex('31c0c3')}
        entry=BASE+b.entries[name]-b.base_va
        if hook_index is not None:
            site=b.hook_sites[hook_index];run=bytearray(site.new)
            for r in site.relocations:
                target=BASE+r.target-b.base_va if b.base_va<=r.target<b.base_va+len(b.code) else DENY
                struct.pack_into('<I',run,r.offset,(target-RUN-r.offset-4)&0xFFFFFFFF)
            # Each original guard's preserved fallthrough is an independent
            # native continuation, never a string-only check of the hook.
            rel32(run,RUN,PASS)
            stubs[RUN]=run;entry=RUN
        shim=bytearray(flags(recorder.INITIAL_FLAGS|(0x400 if df else 0)))
        rel32(shim,SHIM,entry);stubs[SHIM]=shim
        prepared=[]
        for case in cases:
            prepared.append(dict(regs=[0x12345678,0x23456789,0x3456789A,0x456789AB],args=[],entry=SHIM+delta,
                                 **case))
        packet=dict(base=BASE+delta,image_delta=delta,width=width,height=height,code=code.hex(),
                    stubs={str(k+delta):bytes(v).hex() for k,v in stubs.items()},cases=prepared)
        ran=subprocess.run([str(self.exe)],input=json.dumps(packet),capture_output=True,text=True,
                           timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(ran.returncode,0,ran.stdout+ran.stderr)
        rows=json.loads(ran.stdout)
        for result in rows:
            state=result['state']
            self.assertEqual(state[4],state[5],'ESP imbalance')
            self.assertEqual(state[1:4],[0x11223344,0x55667788,0x99AABBCC])
            self.assertEqual(state[6:8],[0x23456789,0x3456789A])
            self.assertEqual(result['render'],0x12345000)
            if hook_index is None:
                self.assertEqual(state[9]&0xCD5,(recorder.INITIAL_FLAGS|(0x400 if df else 0))&0xCD5)
        return rows

    def test_lower_admission_and_native_edx_override_preserve_flags_and_gprs(self):
        cases=[dict(owner=0,owner_result=0),dict(owner=1,owner_result=1),dict(owner=1,owner_result=0),
               dict(owner=1,owner_result=2),dict(owner=1,owner_result=-1),dict(owner=2,owner_result=0)]
        for delta in (0,0x2000000):
            for df in (False,True):
                rows=self.execute('lower_owner_admission',cases,delta=delta,df=df)
                self.assertEqual([r['state'][0] for r in rows],[1,1,0,0,0,0])
                self.assertEqual([len(r['records']) for r in rows],[0,1,1,1,1,1])
                rows=self.execute('native_lower_row',cases,delta=delta,df=df)
                self.assertEqual([r['state'][8] for r in rows],[0,0,1,1,1,2])
                self.assertTrue(all(r['state'][0]==0x12345678 for r in rows))

    def test_all_four_installed_guard_branches_keep_native_rejection(self):
        b=bundle();indices=[i for i,s in enumerate(b.hook_sites) if s.purpose.startswith('admit exact own-army')]
        self.assertEqual(len(indices),4)
        for index in indices:
            rows=self.execute('lower_owner_admission',[dict(owner=0),dict(owner=1,owner_result=1),
                dict(owner=1,owner_result=0),dict(owner=1,owner_result=2),dict(owner=2,owner_result=0)],hook_index=index)
            self.assertEqual([r['records'][-1][0] for r in rows],[50,50,51,51,51])

    def test_installed_native_call_preserves_flags_before_existing_test_edx(self):
        b=bundle();index=next(i for i,s in enumerate(b.hook_sites) if s.va==0x418784)
        for delta in (0,0x2000000):
            rows=self.execute('native_lower_row',[dict(owner=0,owner_result=0),dict(owner=1,owner_result=1),
                dict(owner=1,owner_result=0),dict(owner=1,owner_result=2),dict(owner=2,owner_result=0)],
                delta=delta,df=True,hook_index=index)
            expected=[0,0,1,1,2]
            for r,edx in zip(rows,expected):
                native=r['records'][-1]
                self.assertEqual(native[0],50)
                self.assertEqual(native[1],0x12345678)
                self.assertEqual(native[4],edx)
                self.assertEqual(native[8]&0xCD5,(recorder.INITIAL_FLAGS|0x400)&0xCD5)

    def test_panel_order_failure_normalization_and_exact_vtable_restoration(self):
        cases=[dict(owner=0),dict(owner=1),dict(owner=1,old_result=0),dict(owner=1,old_result=2),
               dict(owner=1,owner_result=0),dict(owner=1,owner_result=2),dict(owner=1,draw_result=0),
               dict(owner=1,draw_result=2),dict(owner=1,draw_result=-1)]
        for delta in (0,0x2000000):
            for table in (clip.MEMORY_VTABLE+delta,BASE+0x15000+delta):
                rows=self.execute('compose_army_panel',[c|{'initial_vtable':table} for c in cases],delta=delta,df=True)
                self.assertEqual([r['state'][0] for r in rows],[1,1,0,0,0,0,0,0,0])
                expected=[[10],[10,20,30],[10],[10],[10,20],[10,20],[10,20,30],[10,20,30],[10,20,30]]
                self.assertEqual([[x[0] for x in r['records']] for r in rows],expected)
                self.assertTrue(all(r['vtable']==table for r in rows))
                for r in rows:
                    self.assertEqual(r['state'][8],0x456789AB)
                    for rec in r['records']:
                        self.assertEqual(rec[10],clip.MEMORY_VTABLE+delta if rec[0]==30 else table)
                        if rec[0]==30:self.assertEqual(rec[1],runner.SURFACE+delta)

    def test_entire_backing_exclusion_scaling_and_old_pixel_continuation(self):
        for width,height in SIZES:
            rect=FramedArmyViewport(width,height).backing
            inside=[(rect.left,rect.top),(rect.right,rect.bottom),(rect.left,rect.bottom),
                    (rect.right,rect.top),(rect.left+1,rect.bottom-1)]
            outside=[(rect.left-1,rect.top),(rect.right+1,rect.bottom),(rect.left,rect.top-1),(rect.right,rect.bottom+1)]
            for shift in (0,3):
                cases=[dict(owner=1,mouse_x=x<<shift,mouse_y=y<<shift,mouse_shift=shift) for x,y in inside+outside]
                rows=self.execute('pixel_army_exclusion',cases,width=width,height=height)
                self.assertEqual([r['state'][0] for r in rows],[0]*len(inside)+[1]*len(outside))
                for r in rows[len(inside):]:
                    rec=r['records'][-1];self.assertEqual(rec[0],40)
                    self.assertEqual(rec[1],0x12345678)
                    self.assertEqual(rec[5],runner.GAME_DATA)
                    self.assertEqual(r['state'][8],0x456789AB)
        rows=self.execute('pixel_army_exclusion',[dict(owner=0,mouse_x=32,mouse_y=518,pixel_result=0),
            dict(owner=0,mouse_x=32,mouse_y=518,pixel_result=1),dict(owner=1,owner_result=2),dict(owner=2,owner_result=0)])
        self.assertEqual([r['state'][0] for r in rows],[0,1,0,0])


if __name__=='__main__':unittest.main(verbosity=2)
