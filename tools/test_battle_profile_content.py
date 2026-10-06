#!/usr/bin/env python3
"""Synthetic body CALL preparation; no original instructions are executed.

The native frames and CALL+NOP adapters here are authored CPU fixtures only.
Their status ABI is not installed in a candidate and does not cancel native
continuations, provider work, RLE or the next frozen field tile.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from src.patcher import battle_profile_content as content
from src.patcher import battle_profile_stack_lease as lease
from src.patcher import partial_tile_clip as clip
import test_battle_profile_stack_lease as parent_fixture
import test_battle_profile_field as oracle

def emit(profile='classic',resolution='1024x768'):
    plan,field,parent=parent_fixture.emit(profile,resolution)
    return plan,parent,content._emit_code(plan,parent,assembler_module=clip)

def verify_frozen():
    for name,digest in content.PINNED_SOURCES.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
            raise ValueError('frozen content dependency differs: '+name)

class Machine(parent_fixture.Machine):
    def __init__(self,tools,profile='classic',resolution='1024x768',delta=0):
        super().__init__(tools,profile,resolution,delta)
        self.content_emission=content._emit_code(self.plan,self.lease_emission,assembler_module=clip)
        self.content_entries={name:va+delta for name,va in self.content_emission.entries}
        raw=bytearray(self.content_emission.code)
        for row in self.content_emission.relocations:
            if row.kind == 'abs32':struct.pack_into('<I',raw,row.offset,row.target+delta)
        self.cpu.mem_write(self.content_emission.base_va+delta,bytes(raw))

    def begin(self,mode=0,*,eax=0,edx=0,flags=0xED7):
        result=super().begin(mode,eax=eax,edx=edx,flags=flags)
        self.current_cell=(eax,edx)
        return result

    def setup_body(self,row,*,x=0,y=0,index=0,via_adjacent=False):
        if self.current_cell != (x,y):
            # Obtain a real new V2 incremental CALL frame for this cell. This
            # never rewrites its captured X/Y receipt or runs original Tile.
            columns=self.word(self.WORLD+804);capacity=min(columns,(self.width-192)//64)
            self.put(self.WORLD+808,min(x,columns-capacity))
            self.begin(1,eax=x,edx=y)
        va,raw,family,op,dx,dy=row;ts=self.tile_sp
        self.put(ts-20,self.field_frame);self.put(ts-28,x);self.put(ts-24,y)
        self.put(ts-44,index)
        self.adjacent_sp=ts-72
        self.put(self.adjacent_sp,0x4302DC+self.delta);self.put(self.adjacent_sp-12,ts-20)
        self.put(self.adjacent_sp-16,x)
        us=self.adjacent_sp-24 if via_adjacent else ts-76
        self.unit_sp=us
        if family in ('unit','count'):
            self.put(us,(0x42FCC4 if via_adjacent else 0x4303B1)+self.delta)
            self.put(us-12,y if via_adjacent else ts-20);self.put(us-28,31*index)
        s=ts
        if family == 'unit':s=us
        elif family == 'adjacent':s=self.adjacent_sp
        elif family == 'vertical':
            s=ts-72;self.put(s,content.VERTICAL_RETURNS[0]+self.delta)
        elif family == 'count':
            s=us-68;self.put(s,0x42F95B+self.delta);self.put(s-24,us-12)
        ebp=ts-20 if family in ('tile','vertical') else us-12 if family in ('unit','count') else y
        regs=dict(EAX=0xA0B0C0D0,ECX=0x10203040,EDX=0x20304050,EBX=0x30405060,
                  EBP=ebp,ESI=index,EDI=0x50607080,ESP=s+content.BODY_SP[family])
        world=self.WORLD
        if op == 'occupant':
            nx,ny=x+dx,y+dy
            if family in ('tile','adjacent'):
                value=bytes.fromhex(raw);modrm=value[2];sib=value[3];bas=sib&7;ix=(sib>>3)&7
                disp=struct.unpack_from('<i',value,4)[0]
                names=('EAX','ECX','EDX','EBX','ESP','EBP','ESI','EDI')
                regs[names[ix]]=y
                regs[names[bas]]=world+40*nx+2*(ny-y)+1534-disp
            elif family == 'unit':
                nx,ny=x,y;self.put(us-64,nx);regs['EAX']=world+40*nx+2*ny
            else:
                nx,ny=x,y;regs['ECX']=world+40*nx;regs['EBX']=ny
            self.neighbor=(nx,ny)
        elif op == 'owner':
            if family == 'unit':regs['EAX']=index;regs['ECX']=world+31*index
            else:regs['ECX']=31*index;regs['EDX']=world
        elif op == 'coordinate':regs['EDX']=world+31*index
        elif family == 'unit':regs['EDX']=world+31*index
        elif family == 'vertical':regs['EAX']=31*index;regs['ECX']=world;regs['EDX']=index
        elif family == 'adjacent':
            regs['EAX']=31*index;regs['EDX']=world;self.put(0x512360+self.delta,index)
        else:regs['EAX']=31*index;regs['ECX']=world
        if family == 'count':regs['EDI']=world+852 # independent valid input record
        self.native_s=s;self.body_regs=regs
        return regs

    def invoke_site(self,row,**kwargs):
        regs=self.setup_body(row,**kwargs)
        return self.invoke_prepared(row,regs)

    def invoke_prepared(self,row,regs,*,call_pc=None):
        va,raw,*_=row;site=va+self.delta;target=self.content_entries[f'site_{va:06x}']
        # Execute an authored five-byte CALL at the exact proposed native site.
        # No original instruction is mapped or run by this fixture.
        self.cpu.mem_write(site,b'\xe8'+struct.pack('<i',target-site-5)+b'\x90'*(len(bytes.fromhex(raw))-5))
        stop=site+5 if call_pc is None else call_pc
        if call_pc is not None:
            site=call_pc-5
            self.cpu.mem_write(site,b'\xe8'+struct.pack('<i',target-site-5))
        self.stops,self.native_stop={stop},None
        self.reads,self.writes=[],[]
        for name,value in regs.items():self.cpu.reg_write(self.regs[name],value&0xFFFFFFFF)
        flags=0xED7;self.cpu.reg_write(self.regs['EFLAGS'],flags)
        self.cpu.emu_start(site,self.STOP+1,count=1000000)
        actual={name:self.cpu.reg_read(reg) for name,reg in self.regs.items()}
        assert self.native_stop == stop,(row,actual,self.callbacks)
        assert actual['ESP'] == regs['ESP'],(row,actual)
        for name,value in regs.items():
            if name not in ('EAX','EDX','ESP'):assert actual[name] == value&0xFFFFFFFF,(row,name,actual[name],value)
        assert actual['EFLAGS']&self.MASK == flags&self.MASK,(row,actual['EFLAGS'])
        for address,size in self.writes:
            assert self.STACK <= address and address+size <= self.STACK+0x10000,(row,address,size)
        return actual,regs

    def payload_reads(self):
        ranges=((self.WORLD,self.WORLD+800),(self.WORLD+852,self.WORLD+0xF7C))
        return [(a,n) for a,n in self.reads if any(a < hi and lo < a+n for lo,hi in ranges)]

class SourceTests(unittest.TestCase):
    def setUp(self):verify_frozen()

    def test_all36_code_relocation_budget_and_private_alias_independence(self):
        for profile in oracle.PROFILES:
            for resolution in oracle.RESOLUTIONS:
                plan,parent,out=emit(profile,resolution)
                self.assertEqual(len(out.entries),28)
                self.assertEqual(out.base_va,(parent.base_va+len(parent.code)+15)&~15)
                self.assertLessEqual(out.base_va+len(out.code),plan['rx']['va']+0x20000)
                seen=set()
                for row in out.relocations:
                    self.assertNotIn(row.offset,seen);seen.add(row.offset)
                    if row.kind == 'abs32':self.assertEqual(struct.unpack_from('<I',out.code,row.offset)[0],row.target)
                    else:
                        self.assertEqual(out.code[row.offset-1],0xE8)
                        self.assertEqual(out.base_va+row.offset+4+struct.unpack_from('<i',out.code,row.offset)[0],row.target)
        plan,parent,expected=emit()
        snapshot=content._snapshot();before=set(sys.modules)
        with patch.object(lease,'_emit_code',side_effect=AssertionError('public lease')), \
             patch.object(clip,'_Assembler',side_effect=AssertionError('public assembler')), \
             patch.object(content,'SITES',()):
            with content._modules(snapshot) as private:
                actual=private[content.SOURCE]._emit_code(plan,parent,assembler_module=private['src/patcher/partial_tile_clip.py'])
        self.assertEqual(actual.code,expected.code)
        self.assertEqual([r.__dict__ for r in actual.relocations],[r.__dict__ for r in expected.relocations])
        self.assertEqual(set(sys.modules),before)

    def test_pure_parent_and_original_rejections(self):
        plan,parent,_=emit()
        for name in ('empty','calls','state','fieldpc','leasepc','page','reservation','resolution'):
            bad_plan,bad=deepcopy(plan),parent
            if name == 'empty':bad=replace(parent,code=b'')
            elif name == 'calls':bad=replace(parent,relocations=tuple(r for r in parent.relocations if r.purpose != 'private authenticated V2 complete receipt'))
            elif name == 'state':bad=replace(parent,state_va=parent.state_va+4)
            elif name == 'fieldpc':bad=replace(parent,field_return_pcs=((0,0),(1,0)))
            elif name == 'leasepc':bad=replace(parent,lease_return_pcs=((0,0),(1,0)))
            elif name == 'page':bad_plan['rw']['page_bytes']=128
            elif name == 'reservation':bad_plan['rx']['virtual_reservation']*=2
            else:bad_plan['resolution']='802x602'
            with self.subTest(name=name),self.assertRaises(ValueError):content._emit_code(bad_plan,bad,assembler_module=clip)
        for original in (b'',bytearray()):
            with self.assertRaises(ValueError):content.emit_battle_profile_content(original,'classic','1024x768')

    def test_exact_native_operands_calls_prologues_neighbors_and_false_claims(self):
        # Authored small instruction receipts only; complete native functions
        # are privately authenticated separately on original-backed admission.
        raw=bytearray(0x120000)
        for va,value in content.PROLOGUES:
            b=bytes.fromhex(value);raw[va-0x400000:va-0x400000+len(b)]=b
        for va,value,*_ in content.SITES:
            b=bytes.fromhex(value);raw[va-0x400000:va-0x400000+len(b)]=b
        for pc,target in content.EXTRA_CALLS:raw[pc-0x400005:pc-0x400000]=b'\xe8'+struct.pack('<i',target-pc)
        for va in (0x513334,0x514500):raw[va-0x400000:va-0x400000+64]=struct.pack('<16i',*(v for pair in content.NEIGHBORS for v in pair))
        fixture=bytes(raw);mapper=SimpleNamespace(file_offset=lambda image,va,count:va-0x400000)
        with patch.object(content,'NATIVE_SPANS',{}):
            rows=content._authenticate_native(fixture,fixture,mapper)
            self.assertEqual(len(rows),28)
            for va,value,*_ in content.SITES:
                for off in (0,len(bytes.fromhex(value))-1):
                    bad=bytearray(fixture);bad[va-0x400000+off]^=1
                    with self.subTest(va=va,off=off),self.assertRaises(ValueError):content._authenticate_native(fixture,bytes(bad),mapper)
            for va,_ in content.PROLOGUES:
                bad=bytearray(fixture);bad[va-0x400000]^=1
                with self.assertRaises(ValueError):content._authenticate_native(fixture,bytes(bad),mapper)
            for pc,_ in content.EXTRA_CALLS:
                bad=bytearray(fixture);bad[pc-0x400001]^=1
                with self.assertRaises(ValueError):content._authenticate_native(fixture,bytes(bad),mapper)
            for va in (0x513334,0x514500):
                bad=bytearray(fixture);bad[va-0x400000+63]^=1
                with self.assertRaises(ValueError):content._authenticate_native(fixture,bytes(bad),mapper)
        tree=ast.parse((ROOT/content.SOURCE).read_text(encoding='utf-8'))
        producer=next(node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)
                      and node.func.id=='dict' and any(k.arg=='schema' and isinstance(k.value,ast.Constant)
                      and k.value.value=='clash95_battle_profile_content_v1' for k in node.keywords))
        vals={k.arg:k.value for k in producer.keywords if k.arg}
        for name in ('installed','battle_installed','expanded_battle_installed','runtime_executed','manual_input_proof','installation_ready','native_body_callsite_admission_installed',
                     'native_continuation_cancellation','count_entry_record_guard_installed','non_draw_count_admission',
                     'provider_validity_verified','arena_intersection_verified','runtime_verified','manual_input_verified',
                     'promotion_ready','release_accepted','thread_lifetime_runtime_verified','native_receiver_validity_verified',
                     'native_argument_validity_verified','standalone_native_callsite_replacement_safe','physical_only_clip_admission_verified'):
            self.assertIs(ast.literal_eval(vals[name]),False,name)
        self.assertTrue(any('does not stop' in text for text in ast.literal_eval(vals['limitations'])))

class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools=oracle.lifetime_fixture.machine_tools()
        if cls.tools is None:raise unittest.SkipTest('Unicorn unavailable; --require-machine-tools fails closed')

    def make(self,profile='classic',resolution='1024x768',delta=0,columns=20):
        return Machine(self.tools,profile,resolution,delta).prepare(columns=columns).begin()

    def test_all36_two_bases_all_body_sites_native_value_and_status_abi(self):
        for profile in oracle.PROFILES:
            for resolution in oracle.RESOLUTIONS:
                for delta in (0,0x30000):
                    m=self.make(profile,resolution,delta)
                    for row in content.SITES:
                        va,raw,family,op,dx,dy=row
                        x,y,index=3,3,21
                        if op == 'occupant':
                            nx,ny=x+dx,y+dy;m.cpu.mem_write(m.WORLD+1534+40*nx+2*ny,struct.pack('<h',21));expected=21
                        elif op in ('type','unit_type'):
                            m.cpu.mem_write(m.WORLD+852+31*index,struct.pack('<h',34));expected=34
                        elif op == 'coordinate':
                            expected=19 if dx == 4 else 6
                            m.cpu.mem_write(m.WORLD+852+31*index+dx,struct.pack('<H',expected))
                        else:m.cpu.mem_write(m.WORLD+854+31*index,b'\xff');expected=255
                        with self.subTest(profile=profile,resolution=resolution,delta=delta,va=va):
                            actual,_=m.invoke_site(row,x=x,y=y,index=index)
                            self.assertEqual((actual['EAX'],actual['EDX']),(expected,1))
                    m.complete()

    def test_edges_small_arenas_empty_and_malformed_are_distinct(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x30000):
                for columns in (1,3,20):
                    m=self.make(profile,delta=delta,columns=columns)
                    for row in content.SITES:
                        if row[3] != 'occupant':continue
                        for x,y in ((0,0),(columns-1,6)):
                            nx,ny=x+row[4],y+row[5]
                            outside=not(0<=nx<columns and 0<=ny<7)
                            if not outside:m.cpu.mem_write(m.WORLD+1534+40*nx+2*ny,b'\xff\xff')
                            actual,_=m.invoke_site(row,x=x,y=y)
                            self.assertEqual((actual['EAX'],actual['EDX']),(0xFFFFFFFF,1),(profile,columns,row,x,y))
                            if outside:self.assertEqual(m.payload_reads(),[],(row,m.payload_reads()))
                        actual,_=m.invoke_site(row,x=0,y=0)
                        nx,ny=m.neighbor
                        if 0<=nx<columns and 0<=ny<7:
                            for bad in (-2,22,32767):
                                m.cpu.mem_write(m.WORLD+1534+40*nx+2*ny,struct.pack('<h',bad))
                                actual,before=m.invoke_site(row,x=0,y=0)
                                self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX']&0xFFFFFFFF,2))

    def test_type_index_owner_and_coordinates_bounds_and_sentinel(self):
        for profile in oracle.PROFILES:
            m=self.make(profile)
            for row in content.SITES:
                if row[3] == 'occupant':continue
                for bad in (-1,22,0x10000000):
                    actual,before=m.invoke_site(row,index=bad)
                    self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX']&0xFFFFFFFF,2),row)
                    self.assertEqual(m.payload_reads(),[],row)
                if row[3] in ('type','unit_type'):
                    for value in (-2,-1,35,32767):
                        m.cpu.mem_write(m.WORLD+852,struct.pack('<h',value))
                        actual,before=m.invoke_site(row)
                        if value == -1 and row[3] == 'unit_type':self.assertEqual((actual['EAX'],actual['EDX']),(0xFFFFFFFF,1))
                        else:self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX']&0xFFFFFFFF,2))
                elif row[3] == 'coordinate':
                    for value in (20 if row[4] == 4 else 7,65535):
                        m.cpu.mem_write(m.WORLD+852+row[4],struct.pack('<H',value))
                        actual,before=m.invoke_site(row)
                        self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX']&0xFFFFFFFF,2))

    def test_unknown_ancestry_saved_current_ebp_and_thread_control_poison(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x30000):
                for family in content.FAMILIES:
                    row=next(r for r in content.SITES if r[2] == family)
                    for fault in ('unknown_call','live_ebp','tile_saved_ebp','tile_return','root','tid','map','render','descriptor','native_pc'):
                        m=self.make(profile,delta=delta);regs=m.setup_body(row,x=0,y=0)
                        if fault == 'unknown_call':
                            actual,before=m.invoke_prepared(row,regs,call_pc=row[0]+delta+0x10005)
                        else:
                            if fault == 'live_ebp':regs['EBP']+=4
                            elif fault == 'tile_saved_ebp':m.put(m.tile_sp-20,m.field_frame+4)
                            elif fault == 'tile_return':m.put(m.tile_sp,0x430000+delta)
                            else:
                                def mutate(machine,name,role=fault):
                                    if name != 'thread':return
                                    if role == 'root':machine.set_state('root_esp',machine.state('root_esp')+4)
                                    elif role == 'tid':machine.thread_id+=1
                                    elif role == 'map':machine.put(0x5202E0+delta,m.PRIVATE)
                                    elif role == 'render':machine.put(0x511230+delta,m.PRIVATE)
                                    elif role == 'descriptor':machine.put(m.lease_frame+60,m.STOP+4)
                                    else:machine.put(m.tile_sp,0x430000+delta)
                                    machine.cpu.mem_protect(m.PHYSICAL&~4095,4096,m.u.UC_PROT_NONE)
                                m.mutation=mutate
                            actual,before=m.invoke_prepared(row,regs)
                        self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX']&0xFFFFFFFF,0),(profile,family,fault))
                        self.assertEqual(m.payload_reads(),[],(profile,family,fault))

    def test_unit_via_adjacent_count_vertical_roles_and_stack_canaries(self):
        for delta in (0,0x30000):
            m=self.make(delta=delta)
            for row in content.SITES:
                if row[2] not in ('unit','count','vertical','adjacent'):continue
                if row[3] == 'occupant':m.cpu.mem_write(m.WORLD+1534,b'\xff\xff')
                elif row[3] in ('type','unit_type'):m.cpu.mem_write(m.WORLD+852,b'\x00\x00')
                elif row[3] == 'owner':m.cpu.mem_write(m.WORLD+854,b'\x80')
                else:m.cpu.mem_write(m.WORLD+852+row[4],b'\x00\x00')
                regs=m.setup_body(row,x=0,y=0,index=0,via_adjacent=True)
                low=regs['ESP']-4-content.HELPER_BYTES-36-32
                m.cpu.mem_write(low,b'\xa9'*16)
                actual,_=m.invoke_prepared(row,regs)
                self.assertEqual(actual['EDX'],1,row)
                self.assertEqual(bytes(m.cpu.mem_read(low,16)),b'\xa9'*16,row)
                if row[2] == 'count':
                    m.put(m.native_s,0x426F95+delta)
                    actual,before=m.invoke_prepared(row,regs)
                    self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX']&0xFFFFFFFF,0))

    def test_thread_word_receipts_and_body_input_losses_precede_payload(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x30000):
                m=self.make(profile,delta=delta)
                cases=[]
                for pointer,count in ((m.state_va,128),(m.PHYSICAL,188),(m.PRIVATE,188),
                                      (0x51D4C0+delta,216),(m.BACKEND,168)):
                    cases.extend((pointer+off,) for off in range(0,count,4))
                if m.modal_va is not None:cases.extend((m.modal_va+delta+off,) for off in range(0,128,4))
                cases.extend((pointer+delta,) for pointer in (0x5202E0,0x511230,0x5199D8,0x526994,0x526990,0x532048,content.THREAD_IAT))
                cases.extend((m.WORLD+off,) for off in (800,804,808,812))
                cases.append((m.state_va+40,m.state_va+44)) # coherently balanced counters still differ
                row=content.SITES[0]
                for addresses in cases:
                    regs=m.setup_body(row)
                    before_words=tuple(m.word(address) for address in addresses)
                    fired=[]
                    def mutate(machine,name):
                        if name == 'thread':
                            fired.append(name)
                            for address in addresses:machine.put(address,machine.word(address)^1)
                    m.mutation=mutate
                    with self.subTest(profile=profile,delta=delta,addresses=addresses):
                        actual,before=m.invoke_prepared(row,regs)
                        self.assertEqual(fired,['thread'])
                        self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX']&0xFFFFFFFF,0))
                        self.assertEqual(m.payload_reads(),[])
                    m.mutation=None
                    for address,value in zip(addresses,before_words):m.put(address,value)
                # Live native scalars and owned save slots are captured too;
                # changing them cannot manufacture a valid outside neighbor.
                for family in content.FAMILIES:
                    row=next(r for r in content.SITES if r[2] == family)
                    regs=m.setup_body(row)
                    helper_ebp=regs['ESP']-4-36-content.HELPER_BYTES
                    addresses=(m.tile_sp-28,m.tile_sp-24,m.field_frame+1132,m.field_frame+1136)
                    if family in ('unit','count'):addresses+=(m.unit_sp-64,m.unit_sp-28)
                    if family == 'adjacent':addresses+=(m.adjacent_sp-16,m.adjacent_sp-12)
                    addresses+=tuple(helper_ebp+content.HELPER_BYTES+off for off in range(0,36,4))
                    for address in addresses:
                        regs=m.setup_body(row)
                        # The save-frame word does not exist until the helper
                        # executes; mutate its actual live value at ThreadId.
                        stored=[]
                        def change(machine,name):
                            if name == 'thread':
                                stored.append(machine.word(address));machine.put(address,stored[-1]^1)
                        m.mutation=change
                        actual,before=m.invoke_prepared(row,regs)
                        self.assertEqual(len(stored),1,(profile,delta,family,hex(address),actual))
                        self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX']&0xFFFFFFFF,0))
                        self.assertEqual(m.payload_reads(),[])
                        m.mutation=None;m.put(address,stored[0])

    def test_outside_neighbor_payload_read_canary_and_current_geometry_rejection(self):
        for profile in oracle.PROFILES:
            m=self.make(profile)
            row=next(r for r in content.SITES if r[2] == 'tile' and r[4:]==(1,0))
            regs=m.setup_body(row,x=19,y=6)
            def forbid_payload(cpu,access,address,size,value,data):
                if m.WORLD<=address<m.WORLD+800 or m.WORLD+852<=address<m.WORLD+0xF7C:
                    raise AssertionError(('outside neighbor read payload',hex(address),size))
            handle=m.cpu.hook_add(m.u.UC_HOOK_MEM_READ,forbid_payload)
            actual,_=m.invoke_prepared(row,regs)
            self.assertEqual((actual['EAX'],actual['EDX']),(0xFFFFFFFF,1))
            m.cpu.hook_del(handle)
            old=m.word(m.WORLD+804);m.put(m.WORLD+804,old-1)
            actual,before=m.invoke_prepared(row,regs)
            self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX']&0xFFFFFFFF,0))
            self.assertEqual(m.payload_reads(),[])

    def test_independent_decode_accounts_for_calls_absolute_operands_and_branches(self):
        for profile in oracle.PROFILES:
            _,_,emitted=emit(profile)
            for delta in (0,0x30000):
                u,r=self.tools;machine=u.Uc(u.UC_ARCH_X86,u.UC_MODE_32)
                base=emitted.base_va+delta;size=(len(emitted.code)+4095)&~4095
                code=bytearray(emitted.code)
                for row in emitted.relocations:
                    if row.kind == 'abs32':struct.pack_into('<I',code,row.offset,row.target+delta)
                machine.mem_map(base&~4095,size+8192);machine.mem_write(base,bytes(code))
                instructions=[]
                def skip(cpu,address,count,data):
                    if address>=base+len(emitted.code):cpu.emu_stop();return
                    instructions.append((address,bytes(cpu.mem_read(address,count))))
                    cpu.reg_write(r.UC_X86_REG_EIP,address+count)
                machine.hook_add(u.UC_HOOK_CODE,skip)
                machine.emu_start(base,base+len(emitted.code),count=100000)
                starts={address-delta for address,_ in instructions};calls={};absolute=set();internal=[]
                for address,raw in instructions:
                    off=address-base
                    if raw[0] == 0xE8:calls[off+1]=address+len(raw)+struct.unpack('<i',raw[-4:])[0]-delta
                    elif raw[:2] == b'\xff\x15':absolute.add(off+2)
                    elif raw[0] == 0x8B and raw[1]&0xC7 == 5:absolute.add(off+2)
                    elif raw[:1] == b'\x81' and raw[1]&0xF8 == 0xF8:
                        value=struct.unpack('<I',raw[2:])[0]-delta
                        if 0x400000<=value<0x20000000:absolute.add(off+2)
                    elif 0xB8<=raw[0]<=0xBF and len(raw) == 5:
                        value=struct.unpack('<I',raw[1:])[0]-delta
                        if 0x400000<=value<0x20000000:absolute.add(off+1)
                    if raw[0] == 0xE9 or raw[:1] == b'\x0f' and 0x80<=raw[1]<=0x8F:
                        target=address+len(raw)+struct.unpack('<i',raw[-4:])[0]
                        internal.append(target-delta)
                self.assertTrue(all(target in starts for target in internal))
                self.assertEqual(calls,{r.offset:r.target for r in emitted.relocations if r.kind == 'rel32'})
                self.assertEqual(absolute,{r.offset for r in emitted.relocations if r.kind == 'abs32'})

def original_memory(path):
    original=path.read_bytes();before=hashlib.sha256(original).hexdigest()
    result=content.emit_battle_profile_content(original,'classic','1024x768')
    with patch.object(content,'_emit_code',side_effect=AssertionError('public own alias')), \
         patch.object(lease,'emit_battle_profile_stack_lease',side_effect=AssertionError('public lease alias')), \
         patch.object(clip,'_Assembler',side_effect=AssertionError('public assembler')), \
         patch.object(content,'SITES',()):
        repeated=content.emit_battle_profile_content(original,'classic','1024x768')
    assert result.emission.code == repeated.emission.code and result.metadata_json == repeated.metadata_json
    assert result.hook_sites == result.removed_highlow_rvas == ()
    assert not result.metadata()['installed'] and not result.metadata()['release_accepted']
    assert all(result.metadata()[name] is False for name in oracle.lifetime_fixture.context.FALSE_CLAIMS)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before == content.BASE_SHA256
    print('original-backed Classic1024 public API/hostile aliases PASS; original unchanged; no native execution')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--require-machine-tools',action='store_true')
    parser.add_argument('--original-memory-audit',type=Path)
    args,rest=parser.parse_known_args()
    if args.require_machine_tools and oracle.lifetime_fixture.machine_tools() is None:
        print('required Unicorn machine tools unavailable',file=sys.stderr);return 2
    suite=unittest.defaultTestLoader.loadTestsFromNames(rest or ['SourceTests','CPUTests'],sys.modules[__name__])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():return 1
    if args.original_memory_audit:original_memory(args.original_memory_audit)
    return 0

if __name__ == '__main__':raise SystemExit(main())
