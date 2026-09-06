"""Execute isolated emitted x86 with synthetic state and native continuations.

No game/debugger/input/window runs. Original/candidate prerequisites are read
or reconstructed in memory. Continuations record their real register/flag ABI;
scroll writes are checked independently against scalar geometry and canaries.
"""
import hashlib
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
from src.patcher import framed_battle_input as module
from src.patcher import partial_tile_clip as clip
from tools import build_framed_army_candidate as builder

RESOLUTIONS=previous.RESOLUTIONS
ADMISSION=runner.BASE+0x7000
STATE=previous.STATE
TARGETS={
    'battle_state_global':runner.GLOBAL+0x104,'battle_render_owner':runner.GLOBAL+0x100,
    'native_battle_owner':0x42E8B0,'mouse_raw_x':runner.GLOBAL+0x110,
    'mouse_raw_y':runner.GLOBAL+0x114,'mouse_shift':runner.GLOBAL+0x10c,
    'current_player_global':runner.GLOBAL+0x118}


def fixture_source():
    source=previous.fixture_source().replace('new byte[1024]','new byte[4096]')
    source=previous.replace_once(source,'    var regs=(IList)c["regs"];var args=(IList)c["args"];',r'''
    W(Global+0x110,Get(c,"raw_x",Get(c,"pixel_x",32)*64));
    W(Global+0x114,Get(c,"raw_y",Get(c,"pixel_y",16)*64));
    W(Global+0x10c,Get(c,"shift",6));W(Global+0x118,Get(c,"player",0));
    W(B+0x7001,Get(c,"admission",1));
    for(int z=0;z<5;z++){Marshal.WriteByte((IntPtr)(battle+0xf5e+z*2),(byte)Get(c,"saved_x",13));Marshal.WriteByte((IntPtr)(battle+0xf5f+z*2),(byte)Get(c,"saved_y",4));}
    Marshal.Copy((IntPtr)battle,guarded,0,guarded.Length);
    var regs=(IList)c["regs"];var args=(IList)c["args"];
''')
    source=source.replace('if(Marshal.ReadByte((IntPtr)(battle+z))!=guarded[z])',
                          'if((z<808 || z>=816) && Marshal.ReadByte((IntPtr)(battle+z))!=guarded[z])')
    source=previous.replace_once(source,'{"render",unchecked((uint)Marshal.ReadInt32((IntPtr)(Global+8)))}});',
        '{"render",unchecked((uint)Marshal.ReadInt32((IntPtr)(Global+8)))},'+
        '{"scroll",new int[]{Marshal.ReadInt32((IntPtr)(battle+808)),Marshal.ReadInt32((IntPtr)(battle+812))}}});')
    return source


@unittest.skipUnless(os.name=='nt' and runner.CSC.is_file() and runner.ORIGINAL.is_file(),
                     'requires original bytes and existing no-window x86 fixture compiler')
class BattleInputX86(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='clash-battle-input-x86-')
        cls.addClassCleanup(cls.temp.cleanup)
        source=Path(cls.temp.name)/'fixture.cs';cls.exe=Path(cls.temp.name)/'fixture.exe'
        source.write_text(fixture_source(),encoding='utf-8')
        r=subprocess.run([str(runner.CSC),'/nologo','/platform:x86','/optimize+',
            '/r:System.Web.Extensions.dll',f'/out:{cls.exe}',str(source)],capture_output=True,text=True,
            timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        if r.returncode:raise AssertionError(r.stdout+r.stderr)
        cls.original=runner.ORIGINAL.read_bytes();cls.bundles={};cls.candidates={}

    @classmethod
    def bundle(cls,w,h,minimap=True):
        key=w,h,minimap
        if key not in cls.bundles:
            cls.candidates[key]=builder.build_candidate(cls.original,f'{w}x{h}',minimap_viewport=minimap)[0]
            cls.bundles[key]=module.emit_battle_input(cls.original,cls.candidates[key],base_va=runner.BASE,
                width=w,height=h,admission_va=ADMISSION,minimap_viewport=minimap)
        return cls.bundles[key]

    def execute(self,w,h,cases,delta=0,native_frame=None):
        bundle=self.bundle(w,h);code=bytearray(bundle.code)
        stubs={ADMISSION+delta:'b801000000c3'};continuations={};kinds={}
        for rel in bundle.relocations:
            if rel.kind=='abs32':
                struct.pack_into('<I',code,rel.offset,TARGETS[rel.purpose]+delta)
            else:
                if rel.purpose=='required_battle_admission':target=ADMISSION+delta
                elif bundle.base_va <= rel.target < bundle.base_va+len(code):target=rel.target+delta
                else:
                    # Each native continuation is a synthetic no-op recorder.
                    # It observes the hook's exact outgoing register ABI before
                    # any subsequent native code can alter those registers.
                    if rel.purpose not in continuations:
                        target=runner.BASE+0x9000+len(continuations)*0x100+delta
                        kind=40+len(continuations);continuations[rel.purpose]=target;kinds[kind]=rel.purpose
                        raw=runner.recorder(kind,0,delta=delta)
                        at=raw.rfind(bytes.fromhex('61b8'))
                        flags_address=runner.OUTPUT+60+delta
                        # Capture flags BEFORE recorder arithmetic, independently
                        # of the CMP-under-test and its later bookkeeping.
                        raw=(bytes.fromhex('9c8f05')+struct.pack('<I',flags_address)+raw[:at]+
                             b'\xa1'+struct.pack('<I',flags_address)+bytes.fromhex('89473c')+raw[at:])
                        if native_frame:
                            epilogue={'pan_pixel':'5d5f5e5a595bc3','hit_pixel':'83c40c5d5f5e5a59c3'}[native_frame]
                            raw=raw[:-3]+bytes.fromhex(epilogue)
                        stubs[target]=raw.hex()
                    target=continuations[rel.purpose]
                struct.pack_into('<i',code,rel.offset,target-(runner.BASE+delta+rel.offset+4))
        prepared=[]
        if native_frame:
            lo,old={'pan_pixel':(0x42C840,'535152565755'),
                    'hit_pixel':(0x42CB50,'515256575583ec0c')}[native_frame]
            off=clip.file_offset(self.original,lo,len(bytes.fromhex(old)))
            self.assertEqual(self.original[off:off+len(bytes.fromhex(old))],bytes.fromhex(old))
            bridge=runner.BASE+0x6000+delta;raw=bytes.fromhex(old)
            raw+=b'\xe9'+struct.pack('<i',bundle.entries[native_frame]+delta-(bridge+len(raw)+5))
            stubs[bridge]=raw.hex()
        for case in cases:
            regs=case.get('regs',[STATE+delta,0x22334455,0x33445566,case.get('x',0)])
            prepared.append(dict(case,entry=bridge if native_frame else bundle.entries[case['helper']]+delta,regs=regs,args=[]))
        payload=dict(base=runner.BASE+delta,image_delta=delta,width=w,height=h,code=code.hex(),
                     stubs={str(k):v for k,v in stubs.items()},cases=prepared)
        r=subprocess.run([str(self.exe)],input=json.dumps(payload),capture_output=True,text=True,
            timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        reports=json.loads(r.stdout);self.assertEqual(len(reports),len(cases))
        for case,result in zip(cases,reports):
            state=result['state'];self.assertEqual(state[4],state[5],'caller ESP changed')
            self.assertEqual(state[-2:],[0xD7654321,0xC1234567],'neighbor stack canaries changed')
            if 'expected' in case:self.assertEqual(state[0],case['expected']&0xffffffff,case)
            if 'scroll' in case:self.assertEqual(result['scroll'],case['scroll'],case)
            if 'route' in case:
                self.assertEqual(len(result['records']),1,(case,result))
                self.assertEqual(kinds[result['records'][0][0]],case['route'],case)
            if 'registers' in case:
                self.assertEqual(result['records'][0][1:5],case['registers'],case)
            if case['helper'] in ('clamp_requested_x','center_requested_x','mouse_cell'):
                self.assertEqual(state[1:4],[case.get('esi',0x11223344),0x55667788,0x99AABBCC])
                self.assertEqual(state[6:9],[v&0xffffffff for v in prepared[cases.index(case)]['regs'][1:]])
                self.assertEqual(state[9]&previous.FLAGS_MASK,case.get('flags',0xAD7)&previous.FLAGS_MASK)
                self.assertEqual(result['records'],[])
        return reports

    def test_six_resolutions_signed_clamps_and_native_centering(self):
        for (w,h),delta in [(res,d) for res in RESOLUTIONS for d in (0,0x02000000)]:
            capacity=(w-192)//64;cases=[]
            for columns in (1,6,7,9,13,20):
                visible=min(columns,capacity);maximum=columns-visible
                for request in (-2147483648,-1,0,1,maximum,maximum+1,2147483647):
                    cases.append(dict(helper='clamp_requested_x',columns=columns,battle_scroll=99,battle_y=5,
                        x=request,expected=max(0,min(request,maximum)),scroll=[99,5]))
                for point in range(columns):
                    cases.append(dict(helper='center_requested_x',columns=columns,x=point,
                        expected=max(0,min(point-visible//2,maximum)),scroll=[0,0]))
            self.execute(w,h,cases,delta)

    def test_physical_mouse_bounds_before_array_and_shift_negatives(self):
        for w,h in RESOLUTIONS:
            visible=min(20,(w-192)//64);scroll=20-visible;right=32+visible*64
            cases=[]
            for x,y in ((32,16),(right-1,463),(31,16),(32,15),(right,16),(32,464),(-1,0),(w-1,h-1)):
                valid=32<=x<right and 16<=y<464
                cases.append(dict(helper='mouse_cell',pixel_x=x,pixel_y=y,battle_scroll=scroll,
                    expected=(scroll+(x-32)//64)|(((y-16)//64)<<16) if valid else -1))
            cases += [dict(helper='mouse_cell',shift=bad,expected=-1) for bad in (32,255)]
            self.execute(w,h,cases)

    def test_context_rejections_and_admission_exact_one(self):
        bads=[dict(admission=0),dict(admission=2),dict(admission=-1),dict(battle_owner=0x40ad40),
              dict(rows=6),dict(rows=8),dict(columns=0),dict(columns=21),dict(global_pointer=0)]
        self.execute(1024,768,[dict(helper=helper,expected=-1,**bad)
            for bad in bads for helper in ('clamp_requested_x','center_requested_x','mouse_cell')])
        self.execute(1024,768,[dict(helper='center_requested_x',x=x,expected=-1) for x in (-1,20,0x7fffffff)])

    def test_pan_and_hit_continuation_coordinates_and_rejected_edges(self):
        for delta in (0,0x02000000):
            for helper in ('pan_pixel','hit_pixel'):
                cases=[]
                for x,y in ((32,16),(863,463),(31,16),(32,15),(864,16),(500,464)):
                    valid=32<=x<864 and 16<=y<464
                    c=dict(helper=helper,pixel_x=x,pixel_y=y,battle_scroll=7,
                        route='native_'+helper+('_admitted' if valid else '_reject'),scroll=[7,0])
                    cases.append(c)
                reports=self.execute(1024,768,cases,delta)
                for x,y,report in [(32,16,reports[0]),(863,463,reports[1])]:
                    row=report['records'][0]
                    self.assertEqual(row[4],STATE+delta)
                    if helper=='pan_pixel':self.assertEqual(row[2],7+(x-32)//64)
                    else:self.assertEqual(row[1],(y-16)//64)
                    state=report['state']
                    if helper=='pan_pixel':self.assertEqual(state[1],(y-16)//64)
                    else:self.assertEqual(state[1:4],[7+(x-32)//64,(y-16)//64,(x-32)//64])
                self.execute(1024,768,[dict(helper=helper,admission=2,
                    route='native_'+helper+'_fallback',scroll=[0,0])],delta)

    def test_native_key_cmp_flags_and_drag_signed_quantization(self):
        for delta in (0,0x02000000):
            reports=self.execute(1024,768,[dict(helper='key_right',battle_scroll=x,
                regs=[STATE+delta,20,0x33445566,x],route='native_key_right_compare') for x in (0,6,7)],delta)
            for x,report in zip((0,6,7),reports):
                row=report['records'][0];self.assertEqual(row[4],x+13)
                self.assertEqual(bool(row[15]&0x40),x==7)
                self.assertEqual(bool(row[15]&0x80),x<7)
            cases=[]
            for initial in (0,3,7):
                for diff in (-400,-9,-8,-7,0,7,8,9,400):
                    requested=initial+int(diff/8)
                    cases.append(dict(helper='drag',pixel_x=500+diff,esi=500,battle_scroll=initial,
                        route='native_drag_redraw',scroll=[max(0,min(requested,7)),0]))
            cases.append(dict(helper='drag',pixel_x=-1,esi=500,battle_scroll=3,route='native_drag_exit',scroll=[3,0]))
            self.execute(1024,768,cases,delta)

    def test_center_hooks_and_obsolete_x_limit_bypass(self):
        for delta in (0,0x02000000):
            cases=[]
            for helper in ('unit_center','shot_center'):
                for x in (0,6,13,19):
                    regs=[0xabcdef,0x22334455,STATE+delta,x] if helper=='unit_center' else [x,0x22334455,0x33445566,STATE+delta]
                    cases.append(dict(helper=helper,regs=regs,route='native_'+helper+'_y',scroll=[max(0,min(x-6,7)),0]))
            self.execute(1024,768,cases,delta)
            for helper in ('unit_limit','shot_limit'):
                self.execute(1024,768,[dict(helper=helper,battle_scroll=x,battle_y=3,
                    route='native_'+helper+('_y_clamp' if 0<=x<=7 else '_fallback'),scroll=[x,3])
                    for x in (-1,0,7,8,13)],delta)

    def test_saved_turn_restore_normalizes_before_draw_and_checks_player(self):
        for delta in (0,0x02000000):
            cases=[dict(helper='restore',player=p,saved_x=x,saved_y=255,battle_y=99,
                        route='native_restore_redraw',scroll=[min(x,7),0]) for p in range(5) for x in (0,7,13,255)]
            cases += [dict(helper='restore',player=p,route='native_restore_reject',scroll=[0,0]) for p in (-1,5)]
            reports=self.execute(1024,768,cases,delta)
            for report in reports[:-2]:
                self.assertEqual(report['state'][2],report['state'][4]-4,'native EDI=ESP poststate changed')

    def test_authentic_native_pan_and_hit_frames_unwind_on_both_paths(self):
        for delta in (0,0x02000000):
            for helper in ('pan_pixel','hit_pixel'):
                reports=self.execute(1024,768,[dict(helper=helper,pixel_x=x,pixel_y=16,battle_scroll=7,
                    route='native_'+helper+suffix) for x,suffix in ((32,'_admitted'),(31,'_reject'))],
                    delta,native_frame=helper)
                for report in reports:
                    self.assertEqual(report['state'][1:4],[0x11223344,0x55667788,0x99AABBCC])

    def test_hook_byte_integrity_relocations_and_fallbacks(self):
        bundle=self.bundle(1024,768)
        self.assertFalse(bundle.installation_ready);self.assertFalse(bundle.source_contract['installed'])
        self.assertEqual(len(bundle.hook_sites),9);self.assertEqual(len(bundle.removed_highlow_rvas),6)
        self.assertEqual(len(clip.absolute_relocation_offsets(bundle)),len([r for r in bundle.relocations if r.kind=='abs32']))
        for hook in bundle.hook_sites:
            self.assertEqual(hook.va+5+struct.unpack_from('<i',hook.new,1)[0],hook.relocations[0].target)
            self.assertEqual(self.original[hook.offset:hook.offset+len(hook.old)],hook.old)
        self.execute(1024,768,[dict(helper=name,admission=0,route='native_'+name+'_fallback',
            regs=[6,20,STATE,STATE if name=='shot_center' else 6]) for name in module.HOOKS])
        with self.assertRaises(ValueError):module.emit_battle_input(self.original,self.candidates[(1024,768,True)][:-1]+b'X',
            base_va=runner.BASE,width=1024,height=768,admission_va=ADMISSION)
        with self.assertRaises(ValueError):module.emit_battle_input(self.original,self.candidates[(1024,768,True)],
            base_va=runner.BASE,width=1024,height=768,admission_va=runner.BASE+100)


if __name__=='__main__':unittest.main(verbosity=2)
