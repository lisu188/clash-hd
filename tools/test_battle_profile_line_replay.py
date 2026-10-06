#!/usr/bin/env python3
"""Closed-line synthetic x86 models only; no native game or file outputs."""
from __future__ import annotations

import argparse
from copy import deepcopy
from contextlib import contextmanager
from dataclasses import replace
import hashlib
from pathlib import Path
import struct
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]
from src.patcher import battle_profile_line_replay as line
from src.patcher import battle_profile_primitive_request as primitive
from src.patcher import partial_tile_clip as clip
import test_battle_profile_primitive_request as previous
import test_battle_profile_field as oracle


def emit(profile='classic', resolution='1024x768'):
    plan, field, lease, checked, old, request = previous.emit(profile, resolution)
    return plan, field, lease, checked, request, line._emit_code(plan, checked, lease, field, assembler_module=clip)


def receipt(out):
    result=vars(out).copy()
    result['relocations']=tuple((r.offset,r.kind,r.target,r.purpose) for r in out.relocations)
    return result


def expected_pixels(before, width, right, x, y, endx, endy, flags):
    # Independent destination-domain oracle, retaining absolute dash phase.
    x, y, endx, endy = (v & 65535 for v in (x, y, endx, endy))
    horizontal = y == endy; dashed = bool(flags & 256)
    first, end = (x, endx) if horizontal else (y, endy)
    if first > end: return before
    pixels = bytearray(before)
    for v in range(first, end+int(not dashed)):
        px, py = (v, y) if horizontal else (x, v)
        if 32 <= px <= right and 16 <= py <= 463 and (not dashed or v & 3 == 2):
            pixels[py*width+px] = flags & 255
    return bytes(pixels)


class Machine(previous.Machine):
    def __init__(self, tools, *args, **kwargs):
        super().__init__(tools, *args, **kwargs)
        out = line._emit_code(self.plan, self.content_emission, self.lease_emission,
            self.field_emission, assembler_module=clip)
        self.continuation = out
        raw = bytearray(out.code)
        for row in out.relocations:
            if row.kind == 'abs32': struct.pack_into('<I', raw, row.offset, row.target+self.delta)
        self.cpu.mem_write(out.base_va+self.delta, bytes(raw))
        self.continuation_entries = {n:v+self.delta for n,v in out.entries}
        self.planned = {va:(raw,target,role,rs) for va,raw,target,role,rs in out.planned_hooks}
        self.unsafe = out.unsafe_va+self.delta
        self.unsafe_vas = {self.unsafe} | {v+self.delta for n,v in out.private_entries if n.endswith('_unsafe')}
        self.line_calls = []; self.line_closed = 0; self.line_mutation = None
        self.output_flags = 0xA47
        self.output_regs = dict(EAX=0xC0FFEE11, ECX=0xFEDCBA98, EDX=0xABCD0123, EBX=0x1234FEDC)
        self.line_pixel_writes = []

    def on_code(self, cpu, address, size, data):
        if address == line.LINE_TARGET+self.delta:
            sp = cpu.reg_read(self.regs['ESP'])
            args = tuple(self.word(sp+4+4*i) for i in range(2))
            values = {n:cpu.reg_read(self.regs[n]) for n in ('EAX','EDX','EBX','ECX','EBP','ESI','EDI')}
            self.line_calls.append((sp, self.word(sp), values, args))
            assert values['EAX'] == self.PHYSICAL
            assert cpu.reg_read(self.regs['EFLAGS']) & 0x400 == 0
            x, y, endx, endy = (v & 65535 for v in (values['EDX'], values['EBX'], values['ECX'], args[0]))
            flags = args[1]; horizontal = y == endy; dashed = bool(flags & 256)
            first, end = (x, endx) if horizontal else (y, endy)
            assert first <= end
            for v in range(first, end+int(not dashed)):
                px, py = (v, y) if horizontal else (x, v)
                assert 32 <= px < 32+64*min(self.word(self.WORLD+804),(self.width-192)//64)
                assert 16 <= py <= 463
                if not dashed or v & 3 == 2:
                    at = self.PHYSICAL_PIXELS+py*self.width+px
                    cpu.mem_write(at, bytes([flags & 255])); self.line_pixel_writes.append(at)
            # This model reaches the native normal RET8 exactly once before
            # any injected ownership mutation. It is not original execution.
            self.line_closed += 1
            if self.line_mutation: self.line_mutation(self)
            for n,v in self.output_regs.items(): cpu.reg_write(self.regs[n], v)
            cpu.reg_write(self.regs['EFLAGS'], self.output_flags)
            self.ret(); cpu.reg_write(self.regs['ESP'], sp+12)
            return
        super().on_code(cpu, address, size, data)

    def invoke_line(self, i=11, regs=None, **kwargs):
        if regs is None: regs = self.setup_request(i, **kwargs)
        pc = primitive.REQUEST_SITES[i][0]
        raw, target, role, removed = self.planned[pc]
        site = pc+self.delta
        self.cpu.mem_write(site, b'\xe8'+struct.pack('<i',target+self.delta-site-5)+b'\x90'*(len(raw)-5))
        self.cpu.ctl_remove_cache(site, site+len(raw))
        self.stops = {0x430831+self.delta, self.word(self.tile_sp)} | self.unsafe_vas
        self.native_stop = None; self.request_records=[]; self.line_calls=[]; self.line_closed=0
        self.line_pixel_writes=[]; self.reads=[]; self.writes=[]
        for n,v in regs.items(): self.cpu.reg_write(self.regs[n],v & 0xFFFFFFFF)
        self.cpu.reg_write(self.regs['EFLAGS'],0xED7)
        self.cpu.emu_start(site, self.STOP+1, count=1000000)
        actual = {n:self.cpu.reg_read(r) for n,r in self.regs.items()}
        # No task writes outside owned stack and explicitly modeled pixels.
        for at,size in self.writes:
            assert self.STACK <= at and at+size <= self.STACK+0x10000, (at,size)
        if self.native_stop not in self.unsafe_vas:
            assert tuple(self.word(self.request_s+4+4*j) for j in range(2)) == self.request_args
        return actual, regs


class SourceTests(unittest.TestCase):
    def test_line_owned_namespace_cleanup_preserves_foreign_replacements(self):
        replacements = {}
        def replace_namespace(code, scope):
            name = scope['__name__']; foreign = ModuleType(name)
            replacements[name] = foreign; sys.modules[name] = foreign
        raw = (ROOT/line.PRIMITIVE).read_bytes()
        try:
            with patch.object(line,'exec',replace_namespace,create=True):
                with self.assertRaisesRegex(ValueError,'frozen primitive namespace identity changed'):
                    line._load_primitive(raw)
                with self.assertRaisesRegex(ValueError,'canonical line issuer module identity changed'):
                    line._production_factory()
            package_name = '_line_owned_namespace_fixture'
            package = ModuleType(package_name); sys.modules[package_name] = package
            old = SimpleNamespace(__package__=package_name)
            @contextmanager
            def private_modules(snapshot):
                yield {line.PRIMITIVE:old}
            stub = SimpleNamespace(_modules=private_modules)
            snap = {line.PRIMITIVE:(raw,()),line.SOURCE:(Path(line.__file__).read_bytes(),())}
            try:
                with patch.object(line,'_load_primitive',return_value=stub), \
                    patch.object(line,'exec',replace_namespace,create=True):
                    with self.assertRaisesRegex(ValueError,'private line namespace identity changed'):
                        with line._modules(snap):pass
            finally:
                if sys.modules.get(package_name) is package:del sys.modules[package_name]
            self.assertEqual(len(replacements),3)
            for name,foreign in replacements.items():self.assertIs(sys.modules.get(name),foreign)
        finally:
            for name,foreign in replacements.items():
                if sys.modules.get(name) is foreign:del sys.modules[name]

    def test_captured_factory_hostile_public_aliases_cannot_bypass_original(self):
        marker = object(); calls = []
        @contextmanager
        def forged_modules(*args):
            calls.append('public modules')
            yield {line.SOURCE:SimpleNamespace(_emit_authenticated=lambda *args:marker)}
        # Exact retained reproduction: this yielded an arbitrary marker with
        # the old dispatcher despite unchanged canonical files.
        with patch.object(line,'_modules',forged_modules):
            with self.assertRaisesRegex(ValueError,'exact original required'):
                line.emit_battle_profile_line_replay(b'not-the-known-original','classic','1024x768')
        self.assertEqual(calls,[])
        aliases = ('_snapshot','_load_primitive','_emit_authenticated','_production_factory','_sha','_require')
        hostile = {n:lambda *a,**k: (_ for _ in ()).throw(AssertionError('public helper invoked')) for n in aliases}
        hostile.update(_modules=forged_modules,ROOT=Path('wrong'),SOURCE='wrong',BASE_SHA256='wrong',
            LINE_TARGET=0,__canonical_line_issuer__=True)
        with patch.dict(line.__dict__,hostile):
            for original in (b'fixture',bytearray(b'fixture'),memoryview(b'fixture')):
                with self.assertRaisesRegex(ValueError,'exact original required'):
                    line.emit_battle_profile_line_replay(original,'classic','1024x768')
        self.assertEqual(calls,[])
        closed = dict(zip(line.emit_battle_profile_line_replay.__code__.co_freevars,
            (cell.cell_contents for cell in line.emit_battle_profile_line_replay.__closure__)))
        self.assertIsNot(closed['issuer'],line._emit_authenticated)
        self.assertEqual(closed['issuer'].__globals__['__loaded_source_sha256__'],
            hashlib.sha256(Path(line.__file__).read_bytes()).hexdigest())
        self.assertTrue(closed['issuer'].__globals__['__canonical_line_issuer__'])
        with self.assertRaisesRegex(ValueError,'captured canonical line production factory required'):
            closed['issuer'].__globals__['emit_battle_profile_line_replay'](b'fixture','classic','1024x768')

    def test_all36_canonical_budget_overlap_and_relocations(self):
        budgets = {}
        for profile in oracle.PROFILES:
            for resolution in oracle.RESOLUTIONS:
                plan, field, lease, checked, prior, out = emit(profile,resolution)
                self.assertEqual(out.base_va,prior.base_va)
                self.assertEqual(len(out.entries),87)
                self.assertEqual(len(out.request_returns),13)
                self.assertEqual(len(out.line_post_returns),2)
                self.assertEqual(len(set(out.line_post_returns)),2)
                self.assertEqual(len({r.offset for r in out.relocations}),len(out.relocations))
                clip.absolute_relocation_offsets(out)
                hooks = {h[0]:h for h in out.planned_hooks}
                self.assertFalse(set(line.REMOVED_OVERLAPS) & hooks.keys())
                for pc,raw,_ in line.LINE_WINDOWS:
                    self.assertEqual(hooks[pc][1],bytes.fromhex(raw)); self.assertEqual(hooks[pc][3:5],('line_replay',()))
                intervals=sorted((pc,pc+len(raw)) for pc,raw,*_ in out.planned_hooks)
                self.assertTrue(all(e<=s for (_,e),(s,_) in zip(intervals,intervals[1:])))
                remaining=plan['rx']['va']+131072-out.base_va-len(out.code)
                self.assertGreaterEqual(remaining,0)
                self.assertEqual(out.code.count(bytes.fromhex('81ec60030000')),1)
                self.assertEqual(len([r for r in out.relocations if r.target==line.LINE_TARGET]),2)
                if resolution=='3840x2160':budgets[profile]=(len(out.code),len(out.relocations),remaining)
        self.assertEqual(set(budgets),set(oracle.PROFILES))

    def test_forged_parent_alias_reservation_and_source_authority_rejected(self):
        plan,field,lease,checked,prior,out=emit()
        for original,which in ((field,0),(lease,1),(checked,2)):
            for mutation in (replace(original,code=original.code[:-1]+bytes([original.code[-1]^1])),
                replace(original,entries=()),replace(original,relocations=original.relocations[:-1])):
                values=[field,lease,checked];values[which]=mutation
                with self.assertRaises(ValueError):line._emit_code(plan,values[2],values[1],values[0],assembler_module=clip)
        for section,key,value in (('rw','page_bytes',8192),('rw','used_bytes',132),('rx','virtual_reservation',0x30000)):
            changed=deepcopy(plan);changed[section][key]=value
            with self.assertRaises(ValueError):line._emit_code(changed,checked,lease,field,assembler_module=clip)
        with patch.object(primitive,'_compose',side_effect=AssertionError('public producer')):
            self.assertEqual(receipt(out),receipt(line._emit_code(plan,checked,lease,field,assembler_module=clip)))
        with self.assertRaises(ValueError):line.emit_battle_profile_line_replay(b'fixture','classic','1024x768')
        with self.assertRaises(ValueError):line._replace('a a','a','b')

    def test_complete_closed_native_ledger_and_private_namespace(self):
        self.assertEqual([(n,hi-lo) for n,lo,hi,_ in line.NATIVE_SPANS],
            [('memory_line',205),('fill_adapter',24),('fill_closure',163),('memory_vtable',60)])
        self.assertEqual(tuple((pc,len(bytes.fromhex(raw))) for pc,raw,_ in line.LINE_WINDOWS),((0x430AD5,8),(0x430B07,11)))
        snap=line._snapshot();self.assertEqual(hashlib.sha256(snap[line.PRIMITIVE][0]).hexdigest(),line.PRIMITIVE_SHA)
        with line._modules(snap) as modules:
            self.assertNotEqual(modules[line.SOURCE].__name__,line.__name__)
            self.assertNotEqual(modules[line.PRIMITIVE].__name__,primitive.__name__)


class CpuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tools=oracle.lifetime_fixture.machine_tools()
    def machine(self,*args,**kwargs):return Machine(self.tools,*args,**kwargs).prepare()

    def test_all36_two_bases_modeled_pixels_outputs_args_and_ret8(self):
        for profile in oracle.PROFILES:
            for resolution in oracle.RESOLUTIONS:
                for delta in (0,0x100000):
                    m=self.machine(profile,resolution,delta);m.begin()
                    right=32+64*min(20,(m.width-192)//64)-1
                    for i,args,x,y,endx in ((11,(20,0x107),0,20,65535),(12,(65535,7),40,0,1)):
                        before=m.pixels();record=m.record()
                        actual,regs=m.invoke_line(i,args=args,x=x,y=y,endx=endx)
                        self.assertEqual(m.line_closed,1);self.assertEqual(len(m.line_calls),1)
                        self.assertNotIn(m.native_stop,m.unsafe_vas)
                        self.assertEqual(m.pixels(),expected_pixels(before,m.width,right,x,y,endx,args[0],args[1]))
                        self.assertEqual(m.record(),record)
                        expected=dict(m.output_regs)
                        if i==12:expected.update(EBX=m.word(m.tile_sp-4),ECX=m.word(m.tile_sp-8))
                        for n,v in expected.items():self.assertEqual(actual[n],v,(profile,resolution,i,n))
                        self.assertEqual(actual['EFLAGS']&m.MASK,m.output_flags&m.MASK)
                        self.assertEqual(actual['ESP'],m.request_s+12 if i==11 else m.tile_sp+4)
                        self.assertEqual(m.word(m.request_s),primitive.REQUEST_SITES[i][0]+delta+5)
                        self.assertEqual(m.line_calls[0][0],m.request_s-116-12)
                        self.assertTrue(m.continuation.base_va+delta<=m.line_calls[0][1]<m.continuation.base_va+delta+len(m.continuation.code))
                        for at in (m.PHYSICAL_PIXELS-16,m.PHYSICAL_PIXELS+m.width*m.height,
                            m.private_pixels-16,m.private_pixels+307200):
                            self.assertEqual(bytes(m.cpu.mem_read(at,16)),b'\xD7'*16)

    def test_small_arenas_gutters_empty_malformed_and_receiver_fault(self):
        cases=((11,31,20,32,(20,0x107)),(11,32,20,32,(20,0x107)),
            (11,32,20,32,(20,7)),(12,40,463,65535,(464,0x107)),
            (12,40,464,0,(500,7)),(11,100,20,32,(20,7)))
        for resolution in ('800x600','1366x768','3440x1440','3840x2160'):
            for columns in (1,3,8,20):
                for i,x,y,endx,args in cases:
                    m=Machine(self.tools,'modalwidgets',resolution).prepare(columns=columns);m.begin()
                    before=m.pixels();actual,regs=m.invoke_line(i,x=x,y=y,endx=endx,args=args)
                    status,_=previous.expected_line(x,y,endx,args,32+64*min(columns,(m.width-192)//64)-1)
                    self.assertEqual(m.line_closed,int(status==1),(resolution,columns,i,status,hex(m.native_stop)))
                    self.assertNotIn(m.native_stop,m.unsafe_vas)
                    if status==3:
                        self.assertEqual(m.pixels(),before)
                        values={n:regs[n] for n in ('EAX','ECX','EDX','EBX')}
                        if i==12:values.update(EBX=m.word(m.tile_sp-4),ECX=m.word(m.tile_sp-8))
                        for n,v in values.items():self.assertEqual(actual[n],v,(resolution,columns,i,n))
                    elif status==2:
                        self.assertEqual(m.word(m.lease_frame+44),2);self.assertEqual(m.word(m.lease_frame+48),2)
                        self.assertEqual(m.pixels(),before)
        for receiver in ('primary','private'):
            m=self.machine();m.begin();regs=m.setup_request(11,args=(20,7));regs['EAX']=0x51D4C0 if receiver=='primary' else m.PRIVATE
            before=m.pixels();actual,_=m.invoke_line(11,regs)
            self.assertEqual(m.line_closed,0);self.assertEqual(m.pixels(),before)
            self.assertEqual(m.word(m.lease_frame+44),2);self.assertNotIn(m.native_stop,m.unsafe_vas)

    def test_pre_thread_and_post_normal_loss_reject_before_cached_reads(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                for when in ('pre_thread','native','post_thread'):
                    m=self.machine(profile,'1024x768',delta);m.begin();fired=[]
                    def lose(target):
                        fired.append(1);target.put(0x5202E0+delta,target.PRIVATE)
                        target.cpu.mem_protect(target.PHYSICAL,0x1000,target.u.UC_PROT_NONE)
                    if when=='native':m.line_mutation=lose
                    else:
                        count=[]
                        def mutate(target,name):
                            if name=='thread':
                                count.append(1)
                                if len(count)==(1 if when=='pre_thread' else 2):lose(target)
                        m.mutation=mutate
                    actual,_=m.invoke_line(11,args=(20,7),x=32,y=20,endx=60)
                    self.assertTrue(fired);self.assertIn(m.native_stop,m.unsafe_vas)
                    self.assertEqual(m.line_closed,int(when!='pre_thread'))

    def test_current_control_request_and_native_output_callback_snapshots(self):
        for delta in (0,0x100000):
            for mutation in ('outer_return','tile_ebp','outer_flags','request','tid','paired_record'):
                m=self.machine('completehd','1024x768',delta);m.begin();regs=m.setup_request(12,args=(80,7),x=40,y=16)
                def mutate(target,name):
                    if name!='thread' or not target.line_closed:return
                    target.mutation=None
                    if mutation=='outer_return':target.put(target.request_s,target.word(target.request_s)+1)
                    elif mutation=='tile_ebp':target.put(target.tile_sp-20,target.word(target.tile_sp-20)+4)
                    elif mutation=='outer_flags':
                        # Native result flags live in its owned116B snapshot.
                        target.put(target.request_s-116+112,target.word(target.request_s-116+112)^1)
                    elif mutation=='request':target.put(target.request_s-116+16,0)
                    elif mutation=='tid':target.thread_id+=1
                    else:target.set_state('allocations',target.state('allocations')+1);target.set_state('frees',target.state('frees')+1)
                m.mutation=mutate;actual,_=m.invoke_line(12,regs)
                self.assertEqual(m.line_closed,1);self.assertIn(m.native_stop,m.unsafe_vas,mutation)
                self.assertEqual(m.line_calls[0][2]['EAX'],m.PHYSICAL)

    def test_unknown_ancestry_and_pre_receipt_fault_never_call(self):
        for profile in oracle.PROFILES:
            for mutation in ('return','root','phase','primary','world','physical_pixels'):
                m=self.machine(profile);m.begin();regs=m.setup_request(11,args=(20,7))
                if mutation=='return':m.put(m.tile_sp,m.word(m.tile_sp)+1)
                elif mutation=='root':m.set_state('root_esp',m.state('root_esp')+4)
                elif mutation=='phase':m.set_state('phase',1)
                elif mutation=='primary':m.put(0x51D4C0,0)
                elif mutation=='world':m.put(m.WORLD+804,21)
                else:m.put(m.PHYSICAL+4,m.private_pixels)
                before=m.pixels();actual,_=m.invoke_line(11,regs)
                self.assertEqual(m.line_closed,0);self.assertEqual(m.pixels(),before)
                self.assertIn(m.native_stop,m.unsafe_vas,mutation)

    def test_pre_latched_and_post_normal_coherent_loss_before_poisoned_cached_objects(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                for when in ('pre_latched','native_return'):
                    m=self.machine(profile,'1024x768',delta);m.begin()
                    def lose(target):
                        target.put(target.lease_frame+44,2);target.put(target.lease_frame+48,2)
                        target.cpu.mem_protect(target.PHYSICAL,0x1000,target.u.UC_PROT_NONE)
                        target.cpu.mem_protect(target.WORLD,0x1000,target.u.UC_PROT_NONE)
                    if when=='pre_latched':lose(m)
                    else:m.line_mutation=lose
                    actual,_=m.invoke_line(11,args=(20,7),x=32,y=20,endx=60)
                    self.assertIn(m.native_stop,m.unsafe_vas,(profile,delta,when))
                    self.assertEqual(m.line_closed,int(when=='native_return'))
                    self.assertFalse(any(m.PHYSICAL<=at<m.PHYSICAL+188 or m.WORLD<=at<m.WORLD+0xF7C
                        for at,size in m.reads if when=='pre_latched'))

    def test_independently_decoded_calls_relocations_and_nested_stack_canaries(self):
        u,r=self.tools
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                _,_,_,_,_,out=emit(profile,'3840x2160')
                cpu=u.Uc(u.UC_ARCH_X86,u.UC_MODE_32);base=out.base_va+delta
                cpu.mem_map(base&~4095,((len(out.code)+(base&4095)+4095)//4096)*4096)
                raw=bytearray(out.code)
                for row in out.relocations:
                    if row.kind=='abs32':struct.pack_into('<I',raw,row.offset,row.target+delta)
                cpu.mem_write(base,bytes(raw));decoded=[]
                def skip(machine,address,size,data):
                    if bytes(machine.mem_read(address,2))==b'\x0f\x0b':size=2
                    self.assertTrue(1<=size<=15,(hex(address),size))
                    decoded.append((address,bytes(machine.mem_read(address,size))))
                    machine.reg_write(r.UC_X86_REG_EIP,address+size)
                cpu.hook_add(u.UC_HOOK_CODE,skip);cpu.emu_start(base,base+len(raw),count=len(raw))
                starts={pc-delta for pc,_ in decoded};relative={};calls={};absolute=set()
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
                        v=struct.unpack('<I',b[2:])[0]-delta
                        if 0x400000<=v<0x20000000:absolute.add(off+2)
                    elif 0xB8<=b[0]<=0xBF and len(b)==5:
                        v=struct.unpack('<I',b[1:])[0]-delta
                        if 0x400000<=v<0x20000000:absolute.add(off+1)
                records={r.offset:r.target for r in out.relocations if r.kind=='rel32'}
                for at,target in calls.items():self.assertEqual(records.get(at),target)
                for at,target in records.items():self.assertEqual(relative.get(at),target)
                self.assertEqual({r.offset for r in out.relocations if r.kind=='abs32'},absolute)
                native_pcs={out.base_va+at+4 for at,target in calls.items() if target==line.LINE_TARGET}
                self.assertEqual(len(native_pcs),2)
                for i in (11,12):
                    m=self.machine(profile,'1024x768',delta);m.begin();regs=m.setup_request(i,args=(20,7),x=32,y=20,endx=64)
                    below=m.request_s-1800;above=m.request_s+16
                    m.cpu.mem_write(below,b'\xA9'*16);m.cpu.mem_write(above,b'\xA9'*16)
                    actual,_=m.invoke_line(i,regs)
                    self.assertEqual(m.line_closed,1);self.assertNotIn(m.native_stop,m.unsafe_vas)
                    self.assertEqual(bytes(m.cpu.mem_read(below,16)),b'\xA9'*16)
                    self.assertEqual(bytes(m.cpu.mem_read(above,16)),b'\xA9'*16)


def original_lane(path):
    original=Path(path).read_bytes();before=hashlib.sha256(original).hexdigest()
    source_path = Path(line.__file__).resolve(); saved_read = Path.read_bytes
    def changed_source(target):
        raw = saved_read(target)
        return raw+b'\n' if target.resolve()==source_path else raw
    with patch.object(Path,'read_bytes',changed_source):
        try:line.emit_battle_profile_line_replay(original,'classic','1024x768')
        except ValueError as exc:assert 'captured canonical line source differs' in str(exc)
        else:raise AssertionError('changed canonical source reached production issuer')
    bundle=line.emit_battle_profile_line_replay(original,'classic','1024x768')
    @contextmanager
    def forged_modules(*args):
        raise AssertionError('public modules invoked')
        yield {}
    hostile = {n:lambda *a,**k: (_ for _ in ()).throw(AssertionError('public helper invoked'))
        for n in ('_snapshot','_load_primitive','_emit_authenticated','_production_factory','_sha','_require','_compose')}
    hostile.update(_modules=forged_modules,ROOT=Path('wrong'),SOURCE='wrong',BASE_SHA256='wrong',
        PRIMITIVE='wrong',PRIMITIVE_SHA='wrong',LINE_TARGET=0,__canonical_line_issuer__=True)
    with patch.dict(line.__dict__,hostile), \
        patch.object(primitive,'emit_battle_profile_primitive_request',side_effect=AssertionError('public primitive')):
        again=line.emit_battle_profile_line_replay(original,'classic','1024x768')
    assert receipt(bundle.emission)==receipt(again.emission) and bundle.metadata_json==again.metadata_json
    metadata=bundle.metadata();assert all(metadata[n] is False for n in line.FALSE_CLAIMS)
    snap=line._snapshot()
    with line._modules(snap) as modules:
        context=modules['src/patcher/battle_profile_context.py'].build_parent_context(original,'classic','1024x768')
        for va in (0x40403C,0x473FEF,0x487D92,0x430AD8,0x430B11,0x50EE38):
            bad=bytearray(original);at=modules['src/patcher/partial_tile_clip.py'].file_offset(original,va,1);bad[at]^=1
            try:line._authenticate_native(bytes(bad),context.candidate,modules)
            except ValueError:pass
            else:raise AssertionError(hex(va)+' mutated native closure accepted')
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==before
    print('Original RAM lane PASS; original unchanged; no native execution or candidate artifact.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--require-machine-tools',action='store_true')
    parser.add_argument('--original');args,rest=parser.parse_known_args()
    if args.require_machine_tools:oracle.lifetime_fixture.machine_tools()
    result=unittest.main(argv=[sys.argv[0]]+rest,exit=False).result
    if result.wasSuccessful() and args.original:original_lane(args.original)
    raise SystemExit(0 if result.wasSuccessful() else 1)
