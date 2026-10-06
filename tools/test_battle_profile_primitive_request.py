#!/usr/bin/env python3
"""Synthetic query/continuation x86 only; no native game or file outputs."""
from __future__ import annotations
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from src.patcher import battle_profile_primitive_request as request
from src.patcher import battle_profile_continuation as continuation
from src.patcher import battle_profile_content as content
from src.patcher import partial_tile_clip as clip
import test_battle_profile_continuation as previous
import test_battle_profile_field as oracle

def emit(profile='classic',resolution='1024x768'):
    plan,field,lease,checked,old=previous.emit(profile,resolution)
    return plan,field,lease,checked,old,request._emit_code(plan,checked,lease,field,assembler_module=clip)

def expected_sprite(args,right):
    left,top,r,b,*extra=args
    signed=lambda x:x if x<0x80000000 else x-0x100000000
    if all(x==0xFFFFFFFF for x in args[:4]):return 1,(32,16,right,463,*extra)
    left,top,r,b=map(signed,(left,top,r,b))
    if left>r or top>b:return 2,(left,top,r,b,*extra)
    values=(max(32,left),max(16,top),min(right,r),min(463,b),*extra)
    return (3 if values[0]>values[2] or values[1]>values[3] else 1),values

def expected_line(x,y,endx,args,right):
    x,y,endx,endy=(v&65535 for v in (x,y,endx,args[0]))
    flags=args[1];dashed=bool(flags&256)
    if y==endy:
        if x>endx:return 2,(x,y,endx,endy)
        if not 16<=y<=463:return 3,(x,y,endx,endy)
        x,endx=max(32,x),min(right+int(dashed),endx)
        return (3 if x>endx or dashed and x==endx else 1),(x,y,endx,endy)
    if y>endy:return 2,(x,y,endx,endy)
    if not 32<=x<=right:return 3,(x,y,endx,endy)
    y,endy=max(16,y),min(463+int(dashed),endy)
    return (3 if y>endy or dashed and y==endy else 1),(x,y,endx,endy)

class Machine(previous.Machine):
    def __init__(self,tools,*args,**kwargs):
        super().__init__(tools,*args,**kwargs)
        self.prior=self.continuation
        self.continuation=request._emit_code(self.plan,self.content_emission,self.lease_emission,self.field_emission,assembler_module=clip)
        raw=bytearray(self.continuation.code)
        for row in self.continuation.relocations:
            if row.kind=='abs32':struct.pack_into('<I',raw,row.offset,row.target+self.delta)
        self.cpu.mem_write(self.continuation.base_va+self.delta,bytes(raw))
        self.continuation_entries={name:va+self.delta for name,va in self.continuation.entries}
        self.planned={va:(raw,target,role,removed) for va,raw,target,role,removed in self.continuation.planned_hooks}
        self.unsafe=self.continuation.unsafe_va+self.delta
        self.unsafe_vas={self.unsafe}|{va+self.delta for name,va in self.continuation.private_entries if name.endswith('_unsafe')}
        self.request_records=[];self.helper_bp=None

    def on_code(self,cpu,address,size,data):
        if address==dict(self.continuation.private_entries).get('admit_body',0)+self.delta:
            self.helper_bp=cpu.reg_read(self.regs['EBP'])
        if address in {v+self.delta for v in self.continuation.request_returns}:
            sp=cpu.reg_read(self.regs['ESP'])
            self.request_records.append(struct.unpack('<16I',bytes(cpu.mem_read(sp+16,64))))
        super().on_code(cpu,address,size,data)

    def setup_request(self,i,*,args=None,via_adjacent=False,tracking_tile=False,x=40,y=20,endx=100):
        pc,kind,parent,delta,_=request.REQUEST_SITES[i]
        row=next(row for row in content.SITES if row[2]==('tile' if parent=='tile' or tracking_tile else 'unit'))
        self.prepared_regs(row,x=0,y=0,via_adjacent=via_adjacent)
        ts=self.tile_sp;us=self.unit_sp
        if parent=='tile':s=ts-delta;ebp=ts-20
        elif parent=='unit':s=us-delta;ebp=us-12
        elif parent=='tracking':
            es=ts-92 if tracking_tile else us-88
            self.put(es,(0x43087D if tracking_tile else 0x42FA7C)+self.delta)
            self.put(es-12,ts-20 if tracking_tile else us-12)
            s=es-delta;ebp=0x50EE24+self.delta
        else:
            es=us-100;self.put(es,0x42F932+self.delta);self.put(es-12,us-12)
            s=es-delta;ebp=16
        values=tuple(args or ((0xFFFFFFFF,)*4+(0x11223344,0x55667788,0x99AABBCC) if kind=='sprite' else (100,0)))
        for off,value in enumerate(values):self.put(s+4+off*4,value)
        if parent=='charge':ebp=values[1]
        regs=dict(EAX=self.PHYSICAL,ECX=y if kind=='sprite' else endx,
            EDX=0xDEADBEEF if kind=='sprite' else x,EBX=x if kind=='sprite' else y,
            EBP=ebp,ESI=0x778899AA,EDI=0x99AABBCC,ESP=s+4)
        self.request_s=s;self.request_args=values;return regs

    def invoke_request(self,i,regs=None,**kwargs):
        if regs is None:regs=self.setup_request(i,**kwargs)
        pc=request.REQUEST_SITES[i][0]+self.delta;target=self.continuation_entries['adapter_'+str(74+i)]
        self.cpu.mem_write(pc,b'\xe8'+struct.pack('<i',target-pc-5));self.cpu.ctl_remove_cache(pc,pc+5)
        self.stops={pc+5}|self.unsafe_vas;self.native_stop=None;self.request_records=[]
        self.reads,self.writes=[],[]
        for name,value in regs.items():self.cpu.reg_write(self.regs[name],value&0xFFFFFFFF)
        self.cpu.reg_write(self.regs['EFLAGS'],0xED7)
        self.cpu.emu_start(pc,self.STOP+1,count=1000000)
        actual={name:self.cpu.reg_read(reg) for name,reg in self.regs.items()}
        if self.native_stop not in self.unsafe_vas:
            for name,value in regs.items():
                if name!='EDX':assert actual[name]==value&0xFFFFFFFF,(i,name,actual[name],value)
            assert actual['EFLAGS']&self.MASK==0xED7&self.MASK
            assert self.word(self.request_s)==pc+5,'natural CALL return word changed'
            assert tuple(self.word(self.request_s+4+4*n) for n in range(len(self.request_args)))==self.request_args
        for at,size in self.writes:assert self.STACK<=at and at+size<=self.STACK+0x10000,(at,size)
        return actual,regs,self.request_records[-1] if self.request_records else None

class SourceTests(unittest.TestCase):
    def test_all36_fixed_parent_relocation_budget_and_stack_layout(self):
        for profile in oracle.PROFILES:
            for resolution in oracle.RESOLUTIONS:
                plan,field,lease,checked,old,out=emit(profile,resolution)
                self.assertEqual(out.base_va,old.base_va)
                self.assertEqual(len(out.entries),87);self.assertEqual(out.request_sites,request.REQUEST_SITES)
                self.assertEqual(len(out.request_returns),13)
                self.assertLessEqual(out.base_va+len(out.code),plan['rx']['va']+0x20000)
                self.assertEqual(len(out.planned_hooks),len(old.planned_hooks))
                self.assertEqual(tuple((r[0],r[1],r[3],r[4]) for r in out.planned_hooks),tuple((r[0],r[1],r[3],r[4]) for r in old.planned_hooks))
                self.assertEqual(len({r.offset for r in out.relocations}),len(out.relocations))
                clip.absolute_relocation_offsets(out)
                self.assertEqual(out.code.count(bytes.fromhex('81ec60030000')),1)
                self.assertEqual(out.code.count(bytes.fromhex('f3a5')),1)
                self.assertEqual(request.THUNK_BYTES,116);self.assertEqual(request.HELPER_BYTES,640)

    def test_rejects_forged_parents_state_reservation_and_source_composition(self):
        plan,field,lease,checked,old,out=emit()
        for parent,which in ((field,0),(lease,1),(checked,2)):
            for changed in (replace(parent,code=parent.code[:-1]+bytes([parent.code[-1]^1])),
                replace(parent,entries=()),replace(parent,relocations=parent.relocations[:-1])):
                values=[field,lease,checked];values[which]=changed
                with self.assertRaises(ValueError):request._emit_code(plan,values[2],values[1],values[0],assembler_module=clip)
        for section,key,value in (('rw','used_bytes',132),('rw','page_bytes',8192),('rx','virtual_reservation',0x30000)):
            poisoned=deepcopy(plan);poisoned[section][key]=value
            with self.assertRaises(ValueError):request._emit_code(poisoned,checked,lease,field,assembler_module=clip)
        with self.assertRaises(ValueError):request._replace('ab ab','ab','cd')

    def test_pinned_sources_private_aliases_and_no_production_fixture_authority(self):
        plan,field,lease,checked,old,out=emit()
        with patch.object(continuation,'_emit_code',side_effect=AssertionError('public continuation')),patch.object(content,'_emit_code',side_effect=AssertionError('public content')):
            again=request._emit_code(plan,checked,lease,field,assembler_module=clip)
        self.assertEqual(out,again)
        with self.assertRaises(ValueError):request.emit_battle_profile_primitive_request(b'fixture','classic','1024x768')
        snap=request._snapshot();self.assertEqual(hashlib.sha256(snap[request.CONTINUATION][0]).hexdigest(),request.CONTINUATION_SHA)
        with request._modules(snap) as modules:
            self.assertNotEqual(modules[request.SOURCE].__name__,request.__name__)
            self.assertEqual(modules[request.SOURCE].THUNK_BYTES,116)

class CpuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tools=oracle.lifetime_fixture.machine_tools()
    def machine(self,*args,**kwargs):return Machine(self.tools,*args,**kwargs).prepare()

    def test_all36_two_bases_baseline28_and_all13_requests(self):
        for profile in oracle.PROFILES:
            for resolution in oracle.RESOLUTIONS:
                for delta in (0,0x100000):
                    m=self.machine(profile,resolution,delta);m.begin()
                    for row in content.SITES:
                        actual,regs=m.invoke(row,index=1,x=1,y=1)
                        self.assertNotIn(m.native_stop,m.unsafe_vas,row)
                        expected=m.original_scalar_oracle(row,regs,0xED7)
                        for name in regs:self.assertEqual(actual[name],expected[name],(profile,resolution,row,name))
                    right=32+min(20,(m.width-192)//64)*64-1
                    for i,row in enumerate(request.REQUEST_SITES):
                        actual,regs,record=m.invoke_request(i)
                        self.assertEqual(actual['EDX'],1,(profile,resolution,i,hex(m.native_stop)))
                        self.assertEqual(record[:3],(request.TAG,1,64));self.assertEqual(record[4],regs['EDX'])
                        self.assertEqual(record[5],m.PHYSICAL);self.assertEqual(record[15],1)
                        if row[1]=='sprite':self.assertEqual(record[8:12],(32,16,right,463))
                        self.assertNotIn('sprite',m.callbacks);self.assertNotIn('line',m.callbacks)

    def test_signed_clip_boundaries_empty_malformed_partial_disabled_and_extras(self):
        cases=((0xFFFFFFFF,)*4,(0,0,100,100),(32,16,32,16),(33,16,32,463),
            (0x80000000,0x80000000,0x7FFFFFFF,0x7FFFFFFF),(0xFFFFFFFF,16,100,463),
            (0,0,31,15),(32,464,1000,500),(2000,16,3000,463),(32,16,0xFFFFFFFF,463))
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                m=self.machine(profile,'1366x768',delta);m.begin();right=32+18*64-1
                for i in range(11):
                    for bounds in cases:
                        args=tuple(bounds)+(0x12345678,0x81234567,0xFFFFFFFF)
                        actual,_,record=m.invoke_request(i,args=args)
                        status,expected=expected_sprite(args,right)
                        self.assertEqual(actual['EDX'],status,(i,bounds,hex(m.native_stop)))
                        self.assertEqual(record[8:15],tuple(v&0xFFFFFFFF for v in expected));self.assertEqual(record[15],status)

    def test_line_native_axis_uint16_inclusive_dashed_phase_and_ignored_xend(self):
        cases=((0,20,100,20,0),(31,20,32,20,0),(31,20,32,20,256),
            (32,20,32,20,0),(32,20,32,20,256),(100,20,32,20,0),
            (40,0,0,464,0),(40,0,0,464,256),(40,463,65535,464,256),
            (40,464,65535,500,0),(40,500,0,100,0),(0x10020,0x10010,0x10040,0x10010,0xABCD0107))
        for profile in oracle.PROFILES:
            m=self.machine(profile,'800x600');m.begin();right=32+9*64-1
            for i in (11,12):
                for x,y,endx,endy,flags in cases:
                    actual,_,record=m.invoke_request(i,x=x,y=y,endx=endx,args=(endy,flags))
                    status,coords=expected_line(x,y,endx,(endy,flags),right)
                    self.assertEqual(actual['EDX'],status,(i,(x,y,endx,endy,flags),hex(m.native_stop)))
                    self.assertEqual(record[8:12],coords);self.assertEqual(record[12],flags)

    def test_effect_saved_parent_ebp_and_adjacent_natural_paths(self):
        for profile in oracle.PROFILES:
            m=self.machine(profile);m.begin()
            for i in (8,9,10):
                for adjacent in (False,True):
                    actual,_,_=m.invoke_request(i,via_adjacent=adjacent)
                    self.assertEqual(actual['EDX'],1,(i,adjacent,hex(m.native_stop)))
            actual,_,_=m.invoke_request(9,tracking_tile=True);self.assertEqual(actual['EDX'],1)
            for i in (9,10):
                regs=m.setup_request(i);es=m.request_s+request.REQUEST_SITES[i][3]
                m.put(es-12,m.word(es-12)+4)
                actual,_,record=m.invoke_request(i,regs)
                self.assertIn(m.native_stop,m.unsafe_vas);self.assertIsNone(record)

    def test_actual_small_arena_columns_gutters_and_right_edge(self):
        for resolution in ('800x600','1366x768','3440x1440','3840x2160'):
            for columns in (1,3,8,20):
                m=Machine(self.tools,'modalwidgets',resolution).prepare(columns=columns);m.begin()
                actual,_,record=m.invoke_request(0)
                self.assertEqual(actual['EDX'],1)
                self.assertEqual(record[8:12],(32,16,32+64*min(columns,(m.width-192)//64)-1,463))

    def test_all_post_normal_closures_and_baseline_replay_once(self):
        previous.CpuTests.test_all_post_normal_return_families_close_once_then_gate(self)

    def test_count_early_domains_and_loss_reset_remain_exact(self):
        previous.CpuTests.test_count_entry_three_early_reads_and_unit_sentinel_domains(self)
        previous.CpuTests.test_loss_aware_post_tile_gate_stops_next_tile_and_new_draw_resets(self)

    def test_receiver_fault_and_control_callbacks_before_poisoned_cached_reads(self):
        roles=('native_return','thunk_return','input_eax','outer_flags','argument','ancestor_ebp','owner','global','thread')
        for delta in (0,0x100000):
            for role in roles:
                m=self.machine('modalwidgets','1024x768',delta);m.begin();regs=m.setup_request(0)
                def mutate(target,name):
                    if name!='thread':return
                    bp=target.helper_bp
                    if role=='native_return':target.put(target.request_s,target.word(target.request_s)+4)
                    elif role=='thunk_return':target.put(bp+676,target.word(bp+676)+4)
                    elif role=='input_eax':target.put(bp+428,target.PRIVATE)
                    elif role=='outer_flags':target.put(bp+792,target.word(bp+792)^1)
                    elif role=='argument':target.put(target.request_s+4,7)
                    elif role=='ancestor_ebp':target.put(target.tile_sp-20,target.field_frame+4)
                    elif role=='owner':target.put(target.plan['rw']['va']+delta+36,6)
                    elif role=='global':target.put(0x5202E0+delta,target.PRIVATE)
                    else:target.thread_id+=1
                    target.cpu.mem_protect(target.PHYSICAL,4096,target.u.UC_PROT_NONE)
                    target.cpu.mem_protect(target.WORLD,4096,target.u.UC_PROT_NONE)
                m.mutation=mutate;actual,_,record=m.invoke_request(0,regs)
                self.assertIn(m.native_stop,m.unsafe_vas,role);self.assertIsNone(record,role)
                self.assertNotIn('sprite',m.callbacks)
            m=self.machine(delta=delta);m.begin()
            for value in (0x51D4C0+delta,m.PRIVATE,m.plan['rw']['va']+delta+512):
                regs=m.setup_request(0);regs['EAX']=value
                actual,_,_=m.invoke_request(0,regs);self.assertEqual(actual['EDX'],4)

    def test_independent_decoded_relocations_calls_and_new_frame_canaries(self):
        for profile in oracle.PROFILES:
            _,_,_,_,_,out=emit(profile,'3840x2160')
            for delta in (0,0x100000):
                u,r=self.tools;cpu=u.Uc(u.UC_ARCH_X86,u.UC_MODE_32);base=out.base_va+delta;page=base&~4095
                raw=bytearray(out.code)
                for row in out.relocations:
                    if row.kind=='abs32':struct.pack_into('<I',raw,row.offset,row.target+delta)
                cpu.mem_map(page,(base+len(raw)-page+4095)&~4095);cpu.mem_write(base,bytes(raw));decoded=[]
                def skip(machine,pc,size,data):
                    if size>15 or size<1:self.assertEqual(bytes(machine.mem_read(pc,2)),b'\x0f\x0b');size=2
                    decoded.append((pc,bytes(machine.mem_read(pc,size))));machine.reg_write(r.UC_X86_REG_EIP,pc+size)
                cpu.hook_add(u.UC_HOOK_CODE,skip);cpu.emu_start(base,base+len(raw),count=len(raw))
                starts={pc-delta for pc,b in decoded};relative={};calls={};absolute=set()
                for pc,b in decoded:
                    off=pc-base
                    if b[0] in (0xE8,0xE9) or b[:1]==b'\x0f' and 0x80<=b[1]<=0x8F:
                        at=off+len(b)-4;target=pc+len(b)+struct.unpack('<i',b[-4:])[0]-delta
                        relative[at]=target
                        if b[0]==0xE8:calls[at]=target
                        if out.base_va<=target<out.base_va+len(out.code):self.assertIn(target,starts)
                    if b[:2]==b'\xff\x15':absolute.add(off+2)
                    elif b[0] in (0xA1,0xA3):absolute.add(off+1)
                    elif b[0]==0x8B and b[1]&0xC7==5:absolute.add(off+2)
                    elif b[0] in (0x03,0x3B,0x81) and len(b)==6:
                        value=struct.unpack('<I',b[2:])[0]-delta
                        if 0x400000<=value<0x20000000:absolute.add(off+2)
                    elif 0xB8<=b[0]<=0xBF and len(b)==5:
                        value=struct.unpack('<I',b[1:])[0]-delta
                        if 0x400000<=value<0x20000000:absolute.add(off+1)
                records={x.offset:x.target for x in out.relocations if x.kind=='rel32'}
                for at,target in calls.items():self.assertEqual(records.get(at),target)
                for at,target in records.items():self.assertEqual(relative.get(at),target)
                self.assertEqual({x.offset for x in out.relocations if x.kind=='abs32'},absolute)
                m=self.machine(profile,'3840x2160',delta);m.begin();regs=m.setup_request(0)
                below=regs['ESP']-2200;above=regs['ESP']+32
                m.cpu.mem_write(below,b'\xA9'*16);m.cpu.mem_write(above,b'\xA9'*16)
                actual,_,_=m.invoke_request(0,regs)
                self.assertEqual(actual['EDX'],1);self.assertEqual(bytes(m.cpu.mem_read(below,16)),b'\xA9'*16)
                self.assertEqual(bytes(m.cpu.mem_read(above,16)),b'\xA9'*16)

def original_memory(path):
    original=path.read_bytes();before=hashlib.sha256(original).hexdigest()
    out=request.emit_battle_profile_primitive_request(original,'classic','1024x768')
    with (patch.object(request,'REQUEST_SITES',()),patch.object(request,'_compose',side_effect=AssertionError('public self')),
         patch.object(continuation,'emit_battle_profile_continuation',side_effect=AssertionError('public predecessor')),
         patch.object(clip,'_Assembler',side_effect=AssertionError('public assembler'))):
        repeated=request.emit_battle_profile_primitive_request(original,'classic','1024x768')
    def receipt(emission):
        values=vars(emission).copy()
        values['relocations']=tuple((r.offset,r.kind,r.target,r.purpose) for r in emission.relocations)
        return values
    assert receipt(out.emission)==receipt(repeated.emission) and out.metadata_json==repeated.metadata_json
    assert all(out.metadata()[name] is False for name in request.FALSE_CLAIMS)
    assert out.hook_sites==out.removed_highlow_rvas==()
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before==request.BASE_SHA256
    print('Original-backed Classic1024 request twice in RAM PASS; exact producer graph/argument spans; original unchanged')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--require-machine-tools',action='store_true')
    parser.add_argument('--original',type=Path);args,remaining=parser.parse_known_args()
    if args.require_machine_tools:oracle.lifetime_fixture.machine_tools()
    if args.original:original_memory(args.original)
    unittest.main(argv=[sys.argv[0],*remaining])

if __name__=='__main__':main()
