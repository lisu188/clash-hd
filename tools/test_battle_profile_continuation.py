#!/usr/bin/env python3
"""Authored CALL/normal-RET models; no native game instruction executes."""
from __future__ import annotations
import argparse
import ast
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from src.patcher import battle_profile_continuation as continuation
from src.patcher import battle_profile_content as content
from src.patcher import partial_tile_clip as clip
import test_battle_profile_content as predecessor
import test_battle_profile_field as oracle

def emit(profile='classic',resolution='1024x768'):
    plan,field,lease=predecessor.parent_fixture.emit(profile,resolution)
    checked=content._emit_code(plan,lease,assembler_module=clip)
    return plan,field,lease,checked,continuation._emit_code(plan,checked,lease,field,assembler_module=clip)

class Machine(predecessor.Machine):
    def __init__(self,tools,profile='classic',resolution='1024x768',delta=0):
        super().__init__(tools,profile,resolution,delta)
        self.tools=tools
        self.continuation=continuation._emit_code(self.plan,self.content_emission,self.lease_emission,
            self.field_emission,assembler_module=clip)
        raw=bytearray(self.continuation.code)
        for row in self.continuation.relocations:
            if row.kind=='abs32':struct.pack_into('<I',raw,row.offset,row.target+delta)
        self.cpu.mem_write(self.continuation.base_va+delta,bytes(raw))
        self.continuation_entries={name:va+delta for name,va in self.continuation.entries}
        self.planned={va:(raw,target,role,removed) for va,raw,target,role,removed in self.continuation.planned_hooks}
        self.count_calls=0;self.normal_closures=0;self.count_model=False
        self.pending_normal=None;self.normal_mutation=None
        self.unsafe=self.continuation.unsafe_va+delta
        self.unsafe_vas={self.unsafe}|{va+delta for name,va in self.continuation.private_entries if name.endswith('_unsafe')}

    def on_code(self,cpu,address,size,data):
        if self.pending_normal and address==0x401100+self.delta:
            pop=self.pending_normal;sp=cpu.reg_read(self.regs['ESP'])
            self.normal_closures+=1
            if self.normal_mutation:self.normal_mutation(self)
            cpu.reg_write(self.regs['EAX'],0xC0FFEE11)
            cpu.reg_write(self.regs['ECX'],0xABCD0123)
            cpu.reg_write(self.regs['EDX'],0x56789ABC)
            cpu.reg_write(self.regs['EFLAGS'],0x247)
            self.ret();cpu.reg_write(self.regs['ESP'],sp+4+pop[0]);return
        if self.count_model and address==0x426EF0+self.delta:
            self.count_calls+=1
            assert self.word(cpu.reg_read(self.regs['ESP']))==0x42F95B+self.delta
        if self.count_model and address==getattr(self,'count_exit',None):self.normal_closures+=1
        super().on_code(cpu,address,size,data)

    def apply_field_calls(self):
        for va,raw,target in self.continuation.field_call_patches:
            site=va+self.delta
            assert bytes(self.cpu.mem_read(site,5))==raw # relative operands rebase unchanged
            self.cpu.mem_write(site,b'\xe8'+struct.pack('<i',target+self.delta-site-5))

    def count_native_model(self):
        # Authored callback-free ABI model, including the three early input
        # reads. This is not the original Count body or a parity fixture.
        code=bytes.fromhex('53515256575583ec0489c70fb748040fb750060fb65802b80700000083c4045d5f5e5a595bc3')
        self.cpu.mem_write(0x426EF0+self.delta,code)
        self.count_exit=0x426EF0+self.delta+len(code)-1
        self.count_model=True

    def invoke_post(self,va,family,*,loss=False):
        row=next(row for row in content.SITES if row[2]==family)
        regs=self.prepared_regs(row)
        self.source_hook(va)
        returns={r[1]:r[0] for r in predecessor.lease.NATIVE_CALL_ABI}
        callee=returns.get(va,'count' if va==0x42F95B else 'vertical')
        pop=predecessor.lease.ARG_BYTES.get(callee,0)
        self.pending_normal=(pop,);self.normal_closures=0;self.normal_mutation=None
        self.cpu.mem_write(0x401100+self.delta,b'\x90')
        call_pc=va+self.delta-5
        self.cpu.mem_write(call_pc,b'\xe8'+struct.pack('<i',0x401100+self.delta-call_pc-5))
        self.cpu.ctl_remove_cache(call_pc,va+self.delta)
        start_sp=regs['ESP']-pop
        for at in range(pop//4):self.put(start_sp+4*at,0x13570000+at)
        regs['ESP']=start_sp
        raw=bytes.fromhex(next(raw for pc,_,raw in continuation.POST_WINDOWS if pc==va))
        stops={va+self.delta+len(raw)}|self.unsafe_vas
        pos=0
        while pos<len(raw):
            if raw[pos]==0xE9:
                stops.add(va+pos+5+struct.unpack_from('<i',raw,pos+1)[0]+self.delta);pos+=5
            elif 0x70<=raw[pos]<=0x7F:
                stops.add(va+pos+2+struct.unpack_from('<b',raw,pos+1)[0]+self.delta);pos+=2
            elif raw[pos:pos+2]==b'\x0f\x85':
                stops.add(va+pos+6+struct.unpack_from('<i',raw,pos+2)[0]+self.delta);pos+=6
            else:pos+=continuation._scalar_length(raw,pos)
        if loss:
            stops={self.word(self.tile_sp if family=='tile' else self.unit_sp if family=='unit' else self.adjacent_sp)}|self.unsafe_vas
            def mutate(target):target.put(target.lease_frame+44,2);target.put(target.lease_frame+48,2)
            self.normal_mutation=mutate
        self.stops,self.native_stop=stops,None;self.reads,self.writes=[],[]
        for name,value in regs.items():self.cpu.reg_write(self.regs[name],value&0xFFFFFFFF)
        self.cpu.reg_write(self.regs['EFLAGS'],0xED7)
        self.cpu.emu_start(call_pc,self.STOP+1,count=1000000)
        return {name:self.cpu.reg_read(reg) for name,reg in self.regs.items()},regs,raw

    def post_scalar_oracle(self,va,raw,regs):
        u,r=self.tools;cpu=u.Uc(u.UC_ARCH_X86,u.UC_MODE_32)
        cpu.mem_map(0x10000,0x2000);cpu.mem_map(0x400000+self.delta,0x200000)
        cpu.mem_map(self.STACK,0x10000);cpu.mem_map(0x20000000,0x5000)
        cpu.mem_write(self.STACK,bytes(self.cpu.mem_read(self.STACK,0x10000)))
        cpu.mem_write(0x400000+self.delta,bytes(self.cpu.mem_read(0x400000+self.delta,0x200000)))
        cpu.mem_write(self.WORLD,bytes(self.cpu.mem_read(self.WORLD,0xF7C)))
        code=bytearray(raw);pos=0
        for h in continuation.NATIVE_HIGHLOW:
            if va<=h<va+len(raw):
                at=h-va;struct.pack_into('<I',code,at,struct.unpack_from('<I',code,at)[0]+self.delta)
        while pos<len(raw):
            if raw[pos]==0xE9:
                struct.pack_into('<i',code,pos+1,0x11000-(0x10000+pos+5));pos+=5
            elif 0x70<=raw[pos]<=0x7F:
                # Put a same-condition near branch into a tiny independently
                # authored oracle; preserve flags and native scalar operations.
                target=0x11000;expanded=b'\x0f'+bytes([raw[pos]+16])+struct.pack('<i',target-(0x10000+pos+6))
                code[pos:pos+2]=expanded
                # This ledger has at most one condition; remaining scalar
                # bytes contain no control flow and retain exact opcodes.
                pos+=6;break
            elif raw[pos:pos+2]==b'\x0f\x85':
                struct.pack_into('<i',code,pos+2,0x11000-(0x10000+pos+6));pos+=6
            else:pos+=continuation._scalar_length(raw,pos)
        cpu.mem_write(0x10000,bytes(code))
        state=dict(regs);state.update(EAX=0xC0FFEE11,ECX=0xABCD0123,EDX=0x56789ABC,ESP=regs['ESP']+self.pending_normal[0])
        for name,value in state.items():cpu.reg_write(self.regs[name],value&0xFFFFFFFF)
        cpu.reg_write(self.regs['EFLAGS'],0x247)
        def stop(machine,address,size,data):
            if address in (0x11000,0x10000+len(code)):machine.emu_stop()
        cpu.hook_add(u.UC_HOOK_CODE,stop);cpu.emu_start(0x10000,0x11001,count=100)
        return {name:cpu.reg_read(reg) for name,reg in self.regs.items()}

    def source_hook(self,va):
        raw,target,role,_=self.planned[va];site=va+self.delta
        self.cpu.mem_write(site,b'\xe8'+struct.pack('<i',target+self.delta-site-5)+b'\x90'*(len(raw)-5))
        self.cpu.ctl_remove_cache(site,site+len(raw))
        return raw,target,role

    def prepared_regs(self,row,**kwargs):
        regs=self.setup_body(row,**kwargs)
        index=kwargs.get('index',0)
        if row[0]==0x42F9EC:regs['EDX']=self.WORLD+31*index
        if row[0]==0x42F9C3:regs['EDI']=0
        self.put(self.WORLD+852+31*index+2,0x000000E7)
        return regs

    def invoke(self,row,**kwargs):
        if isinstance(row,str):return super().invoke(row,**kwargs)
        return self.invoke_regs(row,self.prepared_regs(row,**kwargs))

    def invoke_regs(self,row,regs,*,stop=None,flags=0xED7):
        va=row[0];raw,target,role=self.source_hook(va)
        expected=va+self.delta+len(raw)
        self.stops={expected}|self.unsafe_vas if stop is None else set(stop)|self.unsafe_vas
        self.native_stop=None;self.reads,self.writes=[],[]
        for name,value in regs.items():self.cpu.reg_write(self.regs[name],value&0xFFFFFFFF)
        self.cpu.reg_write(self.regs['EFLAGS'],flags)
        self.cpu.emu_start(va+self.delta,self.STOP+1,count=1000000)
        actual={name:self.cpu.reg_read(reg) for name,reg in self.regs.items()}
        for address,size in self.writes:
            assert self.STACK<=address and address+size<=self.STACK+0x10000,(address,size)
        return actual,regs

    def original_scalar_oracle(self,row,regs,flags):
        """Run only the same small scalar replay ledger, with no world read."""
        va=row[0];window=bytes.fromhex(dict(continuation.CONTENT_WINDOWS)[va]);operand=bytes.fromhex(row[1])
        # Derive independently the native destination after a checked read.
        value=self.checked_value(row,regs)
        modrm=operand[2] if operand[0] in (0x0F,0x66) else operand[1]
        dest=('EAX','ECX','EDX','EBX','ESP','EBP','ESI','EDI')[(modrm>>3)&7]
        state=dict(regs)
        bits=8 if operand[0]==0x8A else 16 if operand[0]==0x66 else 32
        mask=(1<<bits)-1;state[dest]=(state[dest]&~mask)|(value&mask)
        cpu=self.tools[0].Uc(self.tools[0].UC_ARCH_X86,self.tools[0].UC_MODE_32)
        cpu.mem_map(0x10000,0x1000)
        cpu.mem_map(0x20000000,0x5000)
        cpu.mem_map(0x500000+self.delta,0x60000)
        cpu.mem_write(self.WORLD,bytes(self.cpu.mem_read(self.WORLD,0xF7C)))
        cpu.mem_write(0x513334+self.delta,bytes(self.cpu.mem_read(0x513334+self.delta,64)))
        cpu.mem_write(0x512360+self.delta,bytes(self.cpu.mem_read(0x512360+self.delta,4)))
        tail=bytearray(window[len(operand):])
        for _,raw,_,_,removed in self.continuation.planned_hooks:
            if raw==window:
                for rva in removed:
                    at=0x400000+rva-va-len(operand)
                    struct.pack_into('<I',tail,at,struct.unpack_from('<I',tail,at)[0]+self.delta)
        cpu.mem_write(0x10000,bytes(tail))
        for name,value in state.items():cpu.reg_write(self.regs[name],value&0xFFFFFFFF)
        cpu.reg_write(self.regs['EFLAGS'],flags)
        cpu.emu_start(0x10000,0x10000+len(tail),count=20)
        return {name:cpu.reg_read(reg) for name,reg in self.regs.items()}

    def checked_value(self,row,regs):
        va,raw,family,op,dx,dy=row
        if op=='occupant':
            x,y=self.current_cell
            if family in ('tile','adjacent'):x+=dx;y+=dy
            if not 0<=x<self.word(self.WORLD+804) or not 0<=y<self.word(self.WORLD+800):return 0xFFFFFFFF
            return struct.unpack('<h',self.cpu.mem_read(self.WORLD+1534+40*x+2*y,2))[0]&0xFFFFFFFF
        index=(self.word(self.unit_sp-28)//31 if op=='coordinate' else regs['ESI'] if family=='unit'
               else regs['EDX'] if family=='vertical' else self.word(0x512360+self.delta) if family=='adjacent'
               else self.word(self.tile_sp-44))
        if op=='owner':index=regs['EAX'] if family=='unit' else regs['ECX']//31
        if op=='coordinate':return struct.unpack('<H',self.cpu.mem_read(self.WORLD+852+31*index+dx,2))[0]
        if op=='owner':return self.cpu.mem_read(self.WORLD+854+31*index,1)[0]
        return struct.unpack('<h',self.cpu.mem_read(self.WORLD+852+31*index,2))[0]&0xFFFFFFFF

class SourceTests(unittest.TestCase):
    def test_all36_whole_parent_payload_relocation_and_budget(self):
        for profile in oracle.PROFILES:
            for resolution in oracle.RESOLUTIONS:
                plan,field,lease,checked,out=emit(profile,resolution)
                self.assertEqual(len(out.planned_hooks),72)
                self.assertEqual(len(out.field_call_patches),2)
                self.assertEqual(len(out.reused_blocks),28)
                self.assertLessEqual(out.base_va+len(out.code),plan['rx']['va']+0x20000)
                self.assertEqual(out.code[out.unsafe_va-out.base_va:out.unsafe_va-out.base_va+2],b'\x0f\x0b')
                for name,va in out.private_entries:
                    if name.endswith('_unsafe'):
                        self.assertEqual(out.code[va-out.base_va:va-out.base_va+2],b'\x0f\x0b',name)
                offsets=set()
                for row in out.relocations:
                    self.assertNotIn(row.offset,offsets);offsets.add(row.offset)
                    if row.kind=='abs32':self.assertEqual(struct.unpack_from('<I',out.code,row.offset)[0],row.target)
                    else:self.assertEqual(out.base_va+row.offset+4+struct.unpack_from('<i',out.code,row.offset)[0],row.target)
                for va,raw,target,role,removed in out.planned_hooks:
                    self.assertGreaterEqual(len(raw),5)
                    self.assertTrue(out.base_va<=target<out.base_va+len(out.code))
                    self.assertTrue(all(va<=0x400000+r<va+len(raw) for r in removed))

    def test_rejects_changed_payload_prefix_finish_entries_relocations_plan_and_field(self):
        plan,field,lease,checked,_=emit()
        cases=[]
        for index in (0,69,len(checked.code)-1):
            code=bytearray(checked.code);code[index]^=1;cases.append(replace(checked,code=bytes(code)))
        cases.extend((replace(checked,entries=checked.entries[:-1]),replace(checked,relocations=checked.relocations[:-1]),
            replace(checked,private_entries=checked.private_entries[:-1])))
        for bad in cases:
            with self.assertRaises(ValueError):continuation._emit_code(plan,bad,lease,field,assembler_module=clip)
        for name,value in (('page_bytes',128),('used_bytes',4096)):
            bad=deepcopy(plan);bad['rw'][name]=value
            with self.assertRaises(ValueError):continuation._emit_code(bad,checked,lease,field,assembler_module=clip)
        code=bytearray(field.code);at=lease.field_return_pcs[0][1]-field.base_va;code[at]^=1
        with self.assertRaises(ValueError):continuation._emit_code(plan,checked,lease,replace(field,code=bytes(code)),assembler_module=clip)

    def test_false_claims_fixed_source_graph_and_source_hashes(self):
        snapshot=continuation._snapshot();plan,field,lease,checked,expected=emit()
        with patch.object(content,'SITES',()),patch.object(content,'_emit_code',side_effect=AssertionError('public payload')), \
             patch.object(clip,'_Assembler',side_effect=AssertionError('public assembler')):
            with continuation._modules(snapshot) as private:
                actual=private[continuation.SOURCE]._emit_code(plan,checked,lease,field,assembler_module=private['src/patcher/partial_tile_clip.py'])
        self.assertEqual(actual.code,expected.code)
        tree=ast.parse((ROOT/continuation.SOURCE).read_text(encoding='utf8'))
        producer=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='dict'
            and any(k.arg=='schema' and isinstance(k.value,ast.Constant) and k.value.value=='clash95_battle_profile_continuation_v1' for k in n.keywords))
        vals={k.arg:k.value for k in producer.keywords}
        for name in ('installed','battle_installed','expanded_battle_installed','installation_ready','runtime_executed','runtime_verified',
            'release_accepted','provider_validity_verified','arena_intersection_verified','intra_decoder_cancellation','provider_early_cancellation',
            'process_quit_closure_verified','manual_input_verified','promotion_ready','standalone_native_callsite_replacement_safe'):
            self.assertIs(vals[name].value,False)
        for raw in (b'',bytearray()):
            with self.assertRaises(ValueError):continuation.emit_battle_profile_continuation(raw,'classic','1024x768')

    def test_whole_native_window_epi_and_highlow_rejections(self):
        # Authored opcode+ModRM+disp32 length, independent of scalar oracle.
        self.assertEqual(continuation._scalar_length(bytes.fromhex("3a9a56030000"),0),6)
        raw=bytearray(0x140000)
        windows=list(continuation.CONTENT_WINDOWS)+[(va,b) for va,_,b in continuation.POST_WINDOWS]
        windows.append((0x42F956,'e8'+struct.pack('<i',0x426EF0-0x42F95B).hex()))
        for va,value in windows:
            b=bytes.fromhex(value);raw[va-0x400000:va-0x400000+len(b)]=b
        for family,(lo,hi) in continuation.EPILOGUE_SITES.items():raw[lo-0x400000:hi-0x400000]=bytes.fromhex(continuation.EPILOGUES[family])
        fixture=bytes(raw);mapper=SimpleNamespace(file_offset=lambda image,va,count:va-0x400000)
        checked=SimpleNamespace(_authenticate_native=lambda *args:())
        lease=SimpleNamespace(_authenticate_native_abi=lambda *args:())
        pe=SimpleNamespace(inspect_pe=lambda image:SimpleNamespace(image_base=0x400000),
            _old_relocations=lambda image,parsed:(b'',tuple(x-0x400000 for x in continuation.NATIVE_HIGHLOW)))
        continuation._authenticate_native(fixture,fixture,mapper,checked,lease,pe)
        for va,value in windows:
            for index in (0,len(bytes.fromhex(value))-1):
                bad=bytearray(fixture);bad[va-0x400000+index]^=1
                with self.subTest(va=va,index=index),self.assertRaises(ValueError):continuation._authenticate_native(fixture,bytes(bad),mapper,checked,lease,pe)
        bad_pe=SimpleNamespace(inspect_pe=pe.inspect_pe,_old_relocations=lambda *args:(b'',()))
        with self.assertRaises(ValueError):continuation._authenticate_native(fixture,fixture,mapper,checked,lease,bad_pe)

class CpuTests(unittest.TestCase):
    tools=None
    @classmethod
    def setUpClass(cls):cls.tools=oracle.lifetime_fixture.machine_tools()
    def machine(self,*args,**kwargs):
        if self.tools is None:self.skipTest('Unicorn unavailable')
        return Machine(self.tools,*args,**kwargs).prepare()

    def test_all36_two_bases_all28_native_destinations_flags_and_stack(self):
        for profile in oracle.PROFILES:
            for resolution in oracle.RESOLUTIONS:
                for delta in (0,0x100000):
                    m=self.machine(profile,resolution,delta);m.begin()
                    for row in content.SITES:
                        regs=m.prepared_regs(row,index=0)
                        m.put(m.WORLD+852,34);m.cpu.mem_write(m.WORLD+856,struct.pack('<HH',0,0))
                        m.cpu.mem_write(m.WORLD+1534,struct.pack('<h',0))
                        expected=m.original_scalar_oracle(row,regs,0xED7)
                        actual,_=m.invoke_regs(row,regs)
                        self.assertNotIn(m.native_stop,m.unsafe_vas,(profile,resolution,delta,row,m.callbacks))
                        self.assertEqual(actual['ESP'],regs['ESP'])
                        for name in regs:self.assertEqual(actual[name],expected[name],(row,name,actual[name],expected[name]))
                        self.assertEqual(actual['EFLAGS']&m.MASK,expected['EFLAGS']&m.MASK,(row,actual['EFLAGS'],expected['EFLAGS']))

    def test_malformed_content_fault_epilogue_and_distinct_unsafe_control(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                m=self.machine(profile,'1920x1080',delta);m.begin();row=content.SITES[0]
                regs=m.prepared_regs(row);m.cpu.mem_write(m.WORLD+1534,struct.pack('<h',22))
                actual,_=m.invoke_regs(row,regs,stop=(m.lease_emission.field_return_pcs[0][1]+delta,))
                self.assertNotIn(m.native_stop,m.unsafe_vas)
                self.assertEqual(m.word(m.lease_frame+44),2)
                self.assertEqual(m.word(m.lease_frame+48),2)
                self.assertEqual(actual['ESP'],m.tile_sp+4)
                m=self.machine(profile,'1920x1080',delta);m.begin();regs=m.prepared_regs(row)
                m.put(m.tile_sp-20,m.field_frame+4)
                actual,_=m.invoke_regs(row,regs)
                self.assertIn(m.native_stop,m.unsafe_vas)
                self.assertEqual(m.payload_reads(),[])

    def test_last_valid_cells_index21_partial_registers_and_owner255(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                m=self.machine(profile,'1920x1080',delta);m.begin()
                for row in content.SITES:
                    x,y=19,6
                    regs=m.prepared_regs(row,x=x,y=y,index=21)
                    m.cpu.mem_write(m.WORLD+852+31*21,struct.pack('<h',34))
                    m.cpu.mem_write(m.WORLD+854+31*21,b'\xff')
                    m.cpu.mem_write(m.WORLD+856+31*21,struct.pack('<HH',x,y))
                    m.cpu.mem_write(m.WORLD+1534+40*x+2*y,struct.pack('<h',21))
                    # Nonempty neighbors remain index21; true outside cells
                    # use the source-owned empty mapping without payload reads.
                    for nx in range(18,20):
                        for ny in range(5,7):m.cpu.mem_write(m.WORLD+1534+40*nx+2*ny,struct.pack('<h',21))
                    expected=m.original_scalar_oracle(row,regs,0xED7)
                    actual,_=m.invoke_regs(row,regs)
                    self.assertNotIn(m.native_stop,m.unsafe_vas,(profile,row))
                    for name in regs:self.assertEqual(actual[name],expected[name],(row,name))
                    self.assertEqual(actual['EFLAGS']&m.MASK,expected['EFLAGS']&m.MASK,row)
                # A coherently formed neighboring owner pointer does not
                # authorize a current unit index outside its22-record storage.
                m.begin();row=content.SITES[16];regs=m.prepared_regs(row,index=0)
                m.put(m.unit_sp-28,31*23);regs['EDX']=m.WORLD+31*23
                actual,_=m.invoke_regs(row,regs,stop=(m.word(m.unit_sp),))
                self.assertNotIn(m.native_stop,m.unsafe_vas)
                self.assertEqual(m.word(m.lease_frame+44),2)
                self.assertEqual(m.payload_reads(),[])

    def test_count_entry_three_early_reads_and_unit_sentinel_domains(self):
        row=content.SITES[12]
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                for index,typ,x,y,accepted in ((21,-1,19,6,True),(0,34,0,0,True),(-1,-1,0,0,False),
                    (22,0,0,0,False),(0,0,20,0,False),(0,0,0,7,False)):
                    m=self.machine(profile,'1920x1080',delta);m.begin();regs=m.prepared_regs(row,index=max(index,0))
                    regs['EAX']=m.WORLD+852+31*index
                    if 0<=index<22:
                        m.cpu.mem_write(m.WORLD+852+31*index,struct.pack('<hBHH',typ,231,x,y))
                        # Native coords begin+4/+6; record byte3 is opaque.
                        m.cpu.mem_write(m.WORLD+856+31*index,struct.pack('<HH',x,y))
                    m.count_native_model()
                    call=(0x42F956,'','unit','count_entry',0,0)
                    if accepted:
                        actual,_=m.invoke_regs(call,regs,stop=(0x42F95B+delta,))
                        self.assertEqual(m.count_calls,1)
                        self.assertEqual(m.normal_closures,1)
                        self.assertEqual(actual['EAX'],7)
                        self.assertEqual(actual['ESP'],regs['ESP'])
                        reads=m.payload_reads()
                        for off,size in ((4,2),(6,2),(2,1)):
                            self.assertTrue(any(a==regs['EAX']+off and n==size for a,n in reads),(profile,index,off,reads))
                    else:
                        actual,_=m.invoke_regs(call,regs,stop=(m.word(m.unit_sp),))
                        self.assertEqual(m.count_calls,0)
                        self.assertEqual(m.normal_closures,0)
                        self.assertNotIn(m.native_stop,m.unsafe_vas)
                        self.assertEqual(m.word(m.lease_frame+44),2)
                        if index in (-1,22):self.assertEqual(m.payload_reads(),[])

    def test_loss_aware_post_tile_gate_stops_next_tile_and_new_draw_resets(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                m=self.machine(profile,'1920x1080',delta);m.apply_field_calls();m.begin();row=content.SITES[0]
                regs=m.prepared_regs(row);m.cpu.mem_write(m.WORLD+1534,struct.pack('<h',22))
                actual,_=m.invoke_regs(row,regs,stop=(m.STOP,))
                self.assertEqual(m.native_stop,m.STOP)
                self.assertEqual(actual['EAX'],2)
                self.assertEqual(m.tiles,[])
                # The owning wrapper creates a fresh descriptor for a genuine
                # new invocation. A prior loss is never caller-reset in place.
                m.begin();self.assertEqual(m.word(m.lease_frame+44),0)
                m.pause_tile=False
                self.assertEqual(m.complete()['EAX'],1)
                self.assertGreater(len(m.tiles),1)

    def test_thread_local_control_receipt_rejects_before_poisoned_cached_pages(self):
        for delta in (0,0x100000):
            for role in ('site','field','world','helper_ret','outer_ret','outer_ebp','guard_ret','input_eax','descriptor','tile_ebp','global'):
                m=self.machine('modalwidgets','1024x768',delta);m.begin();row=content.SITES[0];regs=m.prepared_regs(row)
                fired=[];helper_frames=[]
                def mutate(target,name):
                    if name!='thread':return
                    fired.append(name);bp=target.cpu.reg_read(target.regs['EBP']);helper_frames.append(bp)
                    if role=='site':target.put(bp+200,27)
                    elif role=='field':target.put(bp+220,target.PHYSICAL)
                    elif role=='world':target.put(bp+372,target.PRIVATE)
                    elif role=='helper_ret':target.put(bp+676,0)
                    elif role=='outer_ret':target.put(bp+732,0)
                    elif role=='outer_ebp':target.put(bp+704,0)
                    elif role=='guard_ret':target.put(bp-4,0)
                    elif role=='input_eax':target.put(bp+428,0xDEADBEEF)
                    elif role=='descriptor':target.put(target.lease_frame+188,9)
                    elif role=='tile_ebp':target.put(target.tile_sp-20,0)
                    else:target.put(0x5202E0+delta,0)
                    target.cpu.mem_protect(target.PHYSICAL,4096,target.u.UC_PROT_NONE)
                m.mutation=mutate
                actual,_=m.invoke_regs(row,regs)
                self.assertEqual(fired,['thread'],role)
                self.assertIn(m.native_stop,m.unsafe_vas,role)
                self.assertEqual(bytes(m.cpu.mem_read(m.native_stop,2)),b'\x0f\x0b',role)
                self.assertEqual(actual['EAX'],regs['EAX'],role)
                self.assertEqual(actual['EDX'],0,role)
                self.assertEqual(actual['EBP'],helper_frames[0],role)
                self.assertEqual(actual['ESP'],helper_frames[0]-4,role)
                self.assertEqual(m.payload_reads(),[],role)
                self.assertFalse(any(m.PHYSICAL<=a<m.PHYSICAL+188 for a,n in m.reads),role)

    def test_all_post_normal_return_families_close_once_then_gate(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                m=self.machine(profile,'1024x768',delta)
                for va,family,raw in continuation.POST_WINDOWS:
                    m.begin()
                    actual,regs,_=m.invoke_post(va,family)
                    self.assertNotIn(m.native_stop,m.unsafe_vas,(profile,hex(va),family))
                    self.assertEqual(m.normal_closures,1,(hex(va),family))
                    self.assertEqual(m.word(m.lease_frame+44),0)
                    expected=m.post_scalar_oracle(va,bytes.fromhex(raw),regs)
                    for name in regs:self.assertEqual(actual[name],expected[name],(hex(va),name,actual[name],expected[name]))
                    self.assertEqual(actual['EFLAGS']&m.MASK,expected['EFLAGS']&m.MASK,(hex(va),actual['EFLAGS'],expected['EFLAGS']))
                    m.begin()
                    actual,regs,_=m.invoke_post(va,family,loss=True)
                    self.assertNotIn(m.native_stop,m.unsafe_vas,(profile,hex(va),family))
                    self.assertEqual(m.normal_closures,1)
                    self.assertEqual(m.word(m.lease_frame+44),2)
                    self.assertEqual(m.word(m.lease_frame+48),2)

    def test_post_normal_closure_control_loss_has_no_cached_read_or_replay(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                for role in ('field_ret','tile_ret','descriptor','thread','global'):
                    m=self.machine(profile,'1024x768',delta);m.begin()
                    def mutate(target):
                        if role=='field_ret':target.put(target.field_frame+1316,0)
                        elif role=='tile_ret':target.put(target.tile_sp,0)
                        elif role=='descriptor':target.put(target.lease_frame+188,7)
                        elif role=='thread':target.thread_id+=1
                        else:target.put(0x5202E0+delta,0)
                        target.cpu.mem_protect(target.PHYSICAL,4096,target.u.UC_PROT_NONE)
                    # Keep the mutation after modeled normal resource closure.
                    row=content.SITES[0];regs=m.prepared_regs(row)
                    va=0x430038;m.source_hook(va)
                    m.cpu.mem_write(va+delta-5,b'\xe8'+struct.pack('<i',0x401100+delta-(va+delta)))
                    m.cpu.ctl_remove_cache(va+delta-5,va+delta)
                    m.pending_normal=(28,);m.normal_mutation=mutate;m.normal_closures=0
                    m.stops=m.unsafe_vas;m.native_stop=None;m.reads,m.writes=[],[]
                    for name,value in regs.items():m.cpu.reg_write(m.regs[name],value)
                    m.cpu.reg_write(m.regs['ESP'],regs['ESP']-28)
                    m.cpu.reg_write(m.regs['EFLAGS'],0xED7)
                    m.cpu.emu_start(va+delta-5,m.STOP+1,count=1000000)
                    self.assertIn(m.native_stop,m.unsafe_vas,role)
                    self.assertEqual(m.normal_closures,1,role)
                    self.assertEqual(m.payload_reads(),[],role)
                    self.assertFalse(any(m.PHYSICAL<=a<m.PHYSICAL+188 for a,n in m.reads),role)
                    self.assertFalse(any(a==0x532104+delta for a,n in m.writes),role)

    def test_independent_decode_every_call_external_branch_abs_operand_and_stack_canary(self):
        for profile in oracle.PROFILES:
            _,_,_,_,out=emit(profile,'3840x2160')
            for delta in (0,0x100000):
                u,r=self.tools;cpu=u.Uc(u.UC_ARCH_X86,u.UC_MODE_32)
                base=out.base_va+delta;page=base&~4095
                code=bytearray(out.code)
                for row in out.relocations:
                    if row.kind=='abs32':struct.pack_into('<I',code,row.offset,row.target+delta)
                cpu.mem_map(page,(base+len(code)-page+4095)&~4095);cpu.mem_write(base,bytes(code))
                records=[]
                def skip(machine,address,size,data):
                    if size<1 or size>15:
                        self.assertEqual(bytes(machine.mem_read(address,2)),b'\x0f\x0b');size=2
                    records.append((address,bytes(machine.mem_read(address,size))));machine.reg_write(r.UC_X86_REG_EIP,address+size)
                cpu.hook_add(u.UC_HOOK_CODE,skip);cpu.emu_start(base,base+len(code),count=len(code))
                owner_tails=[b for pc,b in records if b[:2]==b"\x3a\x9a"]
                self.assertEqual(owner_tails,[bytes.fromhex("3a9a56030000")])
                starts={a-delta for a,b in records};calls={};absolute=set();branches={}
                for pc,b in records:
                    off=pc-base
                    if b[0] in (0xE8,0xE9) or b[:1]==b'\x0f' and 0x80<=b[1]<=0x8F:
                        at=off+len(b)-4;target=pc+len(b)+struct.unpack('<i',b[-4:])[0]-delta
                        if b[0]==0xE8:calls[at]=target
                        else:branches[at]=target
                        if out.base_va<=target<out.base_va+len(out.code):self.assertIn(target,starts)
                    if b[:2]==b'\xff\x15':absolute.add(off+2)
                    elif b[0] in (0xA1,0xA3):absolute.add(off+1)
                    elif b[0]==0x8B and b[1]&0xC7==5:absolute.add(off+2)
                    elif b[0] in (0x03,0x3B) and len(b)==6:
                        value=struct.unpack('<I',b[2:])[0]-delta
                        if 0x400000<=value<0x20000000:absolute.add(off+2)
                    elif b[0]==0x81 and b[1]&0xF8==0xF8:
                        value=struct.unpack('<I',b[2:])[0]-delta
                        if 0x400000<=value<0x20000000:absolute.add(off+2)
                    elif 0xB8<=b[0]<=0xBF and len(b)==5:
                        value=struct.unpack('<I',b[1:])[0]-delta
                        if 0x400000<=value<0x20000000:absolute.add(off+1)
                rel={row.offset:row.target for row in out.relocations if row.kind=='rel32'}
                for at,target in calls.items():self.assertEqual(rel.get(at),target)
                for at,target in rel.items():self.assertEqual((calls|branches).get(at),target)
                self.assertEqual(absolute,{row.offset for row in out.relocations if row.kind=='abs32'})
                m=self.machine(profile,'3840x2160',delta);m.begin();row=content.SITES[0];regs=m.prepared_regs(row)
                below=regs['ESP']-1536;above=regs['ESP']+16
                m.cpu.mem_write(below,b'\xA9'*16);m.cpu.mem_write(above,b'\xA9'*16)
                actual,_=m.invoke_regs(row,regs)
                self.assertNotIn(m.native_stop,m.unsafe_vas)
                self.assertEqual(bytes(m.cpu.mem_read(below,16)),b'\xA9'*16)
                self.assertEqual(bytes(m.cpu.mem_read(above,16)),b'\xA9'*16)

def original_memory(path):
    original=path.read_bytes();before=hashlib.sha256(original).hexdigest()
    result=continuation.emit_battle_profile_continuation(original,'classic','1024x768')
    with patch.object(continuation,'CONTENT_WINDOWS',()),patch.object(continuation,'_emit_code',side_effect=AssertionError('public own alias')), \
         patch.object(content,'emit_battle_profile_content',side_effect=AssertionError('public parent alias')), \
         patch.object(clip,'_Assembler',side_effect=AssertionError('public assembler')):
        repeated=continuation.emit_battle_profile_continuation(original,'classic','1024x768')
    assert result.emission.code==repeated.emission.code and result.metadata_json==repeated.metadata_json
    assert result.hook_sites==result.removed_highlow_rvas==()
    assert all(result.metadata()[name] is False for name in oracle.lifetime_fixture.context.FALSE_CLAIMS)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before==continuation.BASE_SHA256
    print('Original-backed Classic1024 continuation twice in RAM PASS; exact sources/whole windows/relocations; original unchanged')
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--require-machine-tools',action='store_true')
    parser.add_argument('--original',type=Path);args,remaining=parser.parse_known_args()
    tools=oracle.lifetime_fixture.machine_tools()
    if args.require_machine_tools and tools is None:raise SystemExit('Unicorn required')
    if args.original:original_memory(args.original)
    unittest.main(argv=[sys.argv[0],*remaining])

if __name__=='__main__':main()
