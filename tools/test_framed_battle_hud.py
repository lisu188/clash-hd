"""Synthetic x86 ownership and exact native-art pixel tests; no game/CDB run."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json
import os
import struct
import subprocess
import tempfile
import unittest

import test_framed_modal_canvas as fixture
from src.patcher import framed_battle_hud as hud
from src.patcher import partial_tile_clip as clip
from tools import build_framed_army_candidate as builder

B=fixture.BASE
WORLD=B+0xE1000
BATTLE_OWNER=B+0xEE8B0
GATE=B+0x9D00
EMIT_BASE=0x700000
INTEGRATION=0x780000
RESOLUTIONS=((800,600),(802,602),(1024,768),(1280,720),(1280,960),(1920,1080))


def replace_once(source,old,new):
    if source.count(old)!=1:raise AssertionError('fixture anchor count: '+old[:70])
    return source.replace(old,new,1)


def source():
    s=fixture.CSHARP
    s=replace_once(s,'Invoke(int entry,int arg)','Invoke(int entry,int arg,int argumentEdx,bool nativeRoot)')
    s=replace_once(s,'{arg,0x11223344,0x22334455,0x33445566,0,',
                    '{arg,0x11223344,argumentEdx,0x33445566,0,')
    s=replace_once(s,'b.Add(0x9d);b.Add(0xe8);Imm(b,entry-',
                    'b.Add(0x9d);if(nativeRoot){b.Add(0x68);Imm(b,0xA5A5);}b.Add(0xe8);Imm(b,entry-')
    s=replace_once(s,'{"header_zero_com",Read(N+0xAC)==0}',
                    '{"battle",Read(S+68)},{"binds",Read(S+72)},{"header_zero_com",Read(N+0xAC)==0}')
    s=replace_once(s,'W(G+24,Get(c,"tid",123));W(R+8,Get(c,"allocation_failure",0));',
        'W(G+24,Get(c,"tid",123));W(R+8,Get(c,"allocation_failure",0));W(G+28,0);Fill(G+0x100,128,0);W(B+0x9D01,Get(c,"integration",1));')
    s=replace_once(s,'var steps=new List<object>();bool painted=false;',
                    'var steps=new List<object>();bool painted=false;bool fieldPainted=false;')
    s=replace_once(s,'if(kv.Key=="tid")W(G+24,I(kv.Value));',
        'if(kv.Key=="tid")W(G+24,I(kv.Value));else if(kv.Key=="owner")W(G+8,I(kv.Value));'
        'else if(kv.Key=="battle"){W(G+28,I(kv.Value));if(I(kv.Value)!=0){Fill(I(kv.Value),0xF7C,0);W(I(kv.Value)+800,7);W(I(kv.Value)+804,20);}}'
        'else if(kv.Key=="columns")W(B+0xE1000+804,I(kv.Value));'
        'else if(kv.Key=="rows")W(B+0xE1000+800,I(kv.Value));'
        'else if(kv.Key=="integration")W(B+0x9D01,I(kv.Value));'
        'else if(kv.Key=="castle")W(G+0x100,I(kv.Value));')
    s=replace_once(s,'    int arg=name=="try_enter"?0x30001000:name=="try_leave"?Get(c,"leave_esp",0x30000FC4):name=="full_blit"?Read(S+8):0x12345678;\n    var result=Invoke(I(entries[name]),arg);',
        '''    if(name=="paint_field"){for(int y=16;y<464;y++)Fill(F+y*width+32,64*Math.Min(20,(width-192)/64),0xA5);fieldPainted=true;continue;}
    int arg=name=="try_enter"?0x30001000:name=="try_leave"?Get(c,"leave_esp",0x30000F54):name=="try_bind"?Read(G+28):0x12345678;
    int edx=name=="try_bind"?Get(c,"bind_esp",0x30000F58):0x22334455;
    var result=Invoke(I(entries[name]),arg,edx,name=="root_entry");result["native_root"]=name=="root_entry";''')
    begin=s.index('    if((name=="mirror"')
    end=s.index('    if(painted)',begin)
    s=s[:begin]+r'''
    if(name=="try_bind" && Read(S)==2)result["clear_oracle"]=IsFill(F,width*height,0);
    if(name=="compose_chrome" && I(result["eax"])==1){
      bool ok=true;
      for(int y=0;y<height;y++)for(int x=0;x<width;x++){
        int sx=-1,sy=-1;
        if(x>=width-160 && y<368){sx=x-width+640;sy=y;}
        else if(x>=width-160 && y>=height-112){sx=x-width+640;sy=y-height+480;}
        else if(x>=width-16){sx=x-width+640;sy=16+(y-368)%352;}
        else if(x<32){sx=x;sy=y<16?y:y>=height-16?y-height+480:16+(y-16)%448;}
        else if(y<16){sx=32+(x-32)%448;sy=y;}
        else if(y>=height-16){sx=32+(x-32)%448;sy=y-height+480;}
        byte expected=0;
        if(sx>=0 && painted)expected=(byte)((sx*13+sy*7)%251);
        else if(fieldPainted && 32<=x && x<32+64*Math.Min(20,(width-192)/64) && 16<=y && y<464)expected=0xA5;
        if(Marshal.ReadByte((IntPtr)F,y*width+x)!=expected)ok=false;
      }result["pixel_oracle"]=ok;
    }
''' +s[end:]
    return s


def payload(original,bundle,cases):
    extras={hud.BATTLE:fixture.GLOBAL+28,INTEGRATION:GATE}
    extras.update({bundle.source_contract['modal_state_va']+off:fixture.GLOBAL+0x100+off
                   for off in range(0,128,4)})
    entries=dict(bundle.entries,overview_draw=bundle.entries['compose_chrome'],
                 leave_before_map=bundle.entries['leave_before_free'])
    fake=SimpleNamespace(**{k:getattr(bundle,k) for k in ('base_va','state_va','code','relocations','width','height')},
        entries=entries,source_contract=dict(bundle.source_contract,old_action_wrapper_va=0x51BC20))
    with patch.dict(fixture.GLOBALS,extras):
        result=fixture.payload(original,fake,cases)
    result['stubs'][str(GATE)]='b801000000c3'
    # Execute all five actual hook adapters in their original JMP/CALL shapes.
    # Only the remaining game body is replaced by a tiny synthetic owner that
    # writes its known allocation, initializes native dimensions and releases.
    def mapped_native(va):return B+0xE0000+(va&0xffff)
    def entry(name):return B+bundle.entries[name]-bundle.base_va
    def asm(va,build):
        a=clip._Assembler(va)
        def imm(address,value):a.emit('c705');a.u32(address);a.u32(value)
        def jump(target):a.emit('e9');a.u32(target-(va+len(a.code)+4))
        def call(target):a.emit('e8');a.u32(target-(va+len(a.code)+4))
        build(a,imm,jump,call)
        result['stubs'][str(va)]=a.finish().hex()
    def root_body(a,imm,jump,call):
        imm(fixture.GLOBAL+8,BATTLE_OWNER)
        a.emit('bd');a.u32(fixture.PRIMARY)
        jump(entry('initial_frame_target'))
    asm(mapped_native(0x42E9E9),root_body)
    def frame_done(a,imm,jump,call):
        imm(fixture.GLOBAL+28,WORLD)
        jump(entry('bind_allocation'))
    asm(mapped_native(0x42EB74),frame_done)
    def allocated(a,imm,jump,call):
        imm(WORLD+800,7);imm(WORLD+804,20)
        jump(entry('initial_widgets_target'))
    asm(mapped_native(0x42EC97),allocated)
    def widgets_done(a,imm,jump,call):
        call(entry('compose_chrome'))
        a.emit('a1');a.u32(fixture.GLOBAL+28)
        call(entry('leave_before_free'))
        imm(fixture.GLOBAL+28,0)
        imm(fixture.GLOBAL+8,fixture.STUBS[0x40AD40])
        a.emit('b80200000081c49c0000005d5f5ec20400')
    asm(mapped_native(0x42EF77),widgets_done)
    return result


class ContractTests(unittest.TestCase):
    def test_source_bound_edges_and_uninstalled_split(self):
        self.assertEqual(hud.verify_sources(),hud.PINNED_SOURCES)
        self.assertIn('15',hud.integration_required()['overlay_animation'])
        for w,h in RESOLUTIONS:
            for l,t,r,b,x,y in hud.composition_rectangles(w,h):
                self.assertTrue(0<=l<=r<640 and 0<=t<=b<480)
                self.assertTrue(0<=x and x+r-l<w and 0<=y and y+b-t<h)
                # Every frame/HUD pixel lies outside the field's reserved area.
                right=31+64*min(20,(w-192)//64)
                self.assertTrue(x+r-l<32 or x>right or y+b-t<16 or y>463)


@unittest.skipUnless(os.name=='nt' and fixture.CSC.is_file(),'requires existing no-window x86 fixture compiler')
class ExecutedHud(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='clash-battle-hud-x86-');cls.addClassCleanup(cls.temp.cleanup)
        cs=Path(cls.temp.name)/'Fixture.cs';cls.exe=Path(cls.temp.name)/'Fixture.exe';cs.write_text(source())
        compiled=subprocess.run([str(fixture.CSC),'/nologo','/platform:x86','/r:System.Web.Extensions.dll',
            '/out:'+str(cls.exe),str(cs)],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
        if compiled.returncode:raise AssertionError(compiled.stdout+compiled.stderr)
        cls.original=Path('C:/Clash/clash95.exe').read_bytes();cls.cache={}
    @classmethod
    def bundle(cls,w,h):
        if (w,h) not in cls.cache:
            c,m,p=builder.build_candidate(cls.original,f'{w}x{h}',minimap_viewport=True)
            # Candidate reconstruction itself already executed above. Reuse its
            # exact bytes within this fixture, avoiding duplicate expensive build.
            with patch.object(builder,'build_candidate',return_value=(c,m,p)):
                bundle=hud.emit_battle_hud(cls.original,c,base_va=EMIT_BASE,state_va=EMIT_BASE+0x20000,
                    width=w,height=h,integration_va=INTEGRATION)
            cls.cache[w,h]=(bundle,c,m,p)
        return cls.cache[w,h][0]
    def execute(self,cases,w=1024,h=768):
        data=payload(self.original,self.bundle(w,h),cases)
        ran=subprocess.run([str(self.exe)],input=json.dumps(data),capture_output=True,text=True,
            timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(ran.returncode,0,ran.stdout+ran.stderr)
        reports=json.loads(ran.stdout)
        for steps in reports:
            for r in steps:
                self.assertTrue(r['gprs'] and r['esp'] and r['canaries'],r)
                # The public helpers preserve flags. Root hooks replay the
                # original native body, whose ADD ESP,9C changes arithmetic
                # flags before RET4; only DF remains a caller invariant there.
                mask=0x400 if r.get('native_root') else fixture.MASK
                self.assertEqual(r['flags']&mask,fixture.FLAGS&mask)
                if 'source_intact' in r:self.assertTrue(r['source_intact'])
        return reports
    def active(self,*tail):
        return ['try_enter',dict(owner=BATTLE_OWNER,battle=WORLD),'paint','try_bind',*tail]
    def test_owned_lifecycle_and_every_native_art_pixel_all_profiles(self):
        for w,h in RESOLUTIONS:
            rows=self.execute([dict(steps=self.active('field_admission','compose_chrome','paint_field',
                'compose_chrome','try_leave'))],w,h)[0]
            self.assertTrue(all(x['eax']==1 for x in rows),rows)
            self.assertTrue(rows[1]['clear_oracle'])
            self.assertTrue(rows[3]['pixel_oracle'] and rows[4]['pixel_oracle'])
            self.assertEqual(rows[-1]['phase'],0);self.assertEqual(rows[-1]['free_calls'],2)
            self.assertEqual(rows[-1]['global_map'],fixture.PHYSICAL)
            self.assertEqual(rows[-1]['global_render'],fixture.PHYSICAL)
            self.assertEqual(rows[-1]['battle'],0)
    def test_allocator_rollback_and_preentry_rejections_do_not_publish(self):
        cases=[dict(allocation_failure=n,steps=['try_enter']) for n in (1,2)]
        cases += [dict(integration=0,steps=['try_enter']),dict(owner=0,steps=['try_enter']),
                  dict(surface_width=640,steps=['try_enter'])]
        rows=self.execute(cases)
        for case,result in zip(cases,rows):
            r=result[0];self.assertEqual((r['eax'],r['phase'],r['allocations']),(0,0,0))
            self.assertEqual(r['global_map'],fixture.PHYSICAL)
            self.assertEqual(r['global_render'],fixture.PHYSICAL)
            self.assertEqual(r['free_calls'],int(case.get('allocation_failure')==2))
    def test_actual_runner_hook_chain_replays_stack_and_native_ret4(self):
        row=self.execute([dict(steps=['root_entry'])])[0][0]
        self.assertEqual((row['eax'],row['phase'],row['enter'],row['leave']),(2,0,1,1))
        self.assertEqual((row['alloc_calls'],row['free_calls'],row['binds'],row['mirrors']),(2,3,1,1))
        self.assertEqual((row['global_map'],row['global_render']),(fixture.PHYSICAL,fixture.PHYSICAL))
    def test_wrong_thread_alias_lifetime_dimensions_and_incomplete_integration(self):
        changes=[dict(tid=124),dict(owner=0),dict(battle=WORLD+0x1000),dict(native_width=641),
                 dict(native_pixels=fixture.PHYSPIX),dict(map_pointer=0),dict(rows=8),dict(columns=0),
                 dict(columns=21),dict(integration=0),dict(castle=1)]
        rows=self.execute([dict(steps=self.active(change,'field_admission')) for change in changes])
        self.assertTrue(all(r[-1]['eax']==0 for r in rows))
        rows=self.execute([dict(bind_esp=0x30000F5C,steps=self.active()),
                           dict(leave_esp=0x30000F58,steps=self.active('try_leave'))])
        self.assertEqual(rows[0][-1]['phase'],1)
        self.assertEqual(rows[1][-1]['phase'],2)
        self.assertEqual(rows[1][-1]['free_calls'],0)
    def test_hooks_original_bytes_removed_fixups_and_candidate_mutations(self):
        bundle=self.bundle(1024,768);_,c,m,p=self.cache[1024,768]
        self.assertFalse(bundle.installation_ready)
        self.assertEqual(len(bundle.hook_sites),5)
        self.assertEqual(set(bundle.removed_highlow_rvas),{0x2EC92,0x2EB70,0x2EF73})
        for site in bundle.hook_sites:
            self.assertEqual(c[site.offset:site.offset+len(site.old)],site.old)
            self.assertEqual(site.va+5+struct.unpack_from('<i',site.new,1)[0],bundle.entries[site.purpose.removeprefix('battle HUD ')])
        bad=bytearray(c);bad[-1]^=1
        with patch.object(builder,'build_candidate',return_value=(c,m,p)):
            with self.assertRaisesRegex(ValueError,'whole current army'):
                hud.emit_battle_hud(self.original,bytes(bad),base_va=EMIT_BASE,state_va=EMIT_BASE+0x20000,
                    width=1024,height=768,integration_va=INTEGRATION)
        self.assertEqual(Path('C:/Clash/clash95.exe').read_bytes(),self.original)


if __name__=='__main__':unittest.main()
