#!/usr/bin/env python3
"""Source and CPU-model lease V2 fixtures; no game/native execution or artifacts.

The optional Original reconstruction lane is separate and never part of the
default suite. Modeled native callbacks cannot establish native acceptance.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from dataclasses import asdict, replace
import gc
import hashlib
from pathlib import Path
import struct
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from src.patcher import battle_profile_stack_lease_v2 as tool
from src.patcher import battle_profile_stack_lease as frozen
from src.patcher import battle_profile_field_v3 as field
from src.patcher import battle_profile_context_v2 as context
from src.patcher import partial_tile_clip as clip
from src.patcher import framed_modal_canvas as native
import test_battle_profile_field_v3 as field_fixture
import test_battle_profile_stack_lease as old_fixture

FIXTURE_PINS={
    'tools/test_battle_profile_field_v3.py':'a5e4f26de52766513bdac5abec85a076bdaf7e96155e99fa3fa52194e1ffcbba',
    'tools/test_battle_profile_stack_lease.py':'d5f5076627e809a16860b19808f929bc20ad56f88f1194c15dd2c54fd3c9b81e',
}
ORIGINAL=None
CACHE={}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def verify_frozen():
    for name,digest in FIXTURE_PINS.items()|tool.PINNED_SOURCES.items():
        if sha((ROOT/name).read_bytes())!=digest:
            raise ValueError('frozen source/fixture differs: '+name)

@contextmanager
def issuer():
    raw=(ROOT/tool.SOURCE).read_bytes(); name='_lease_v2_synthetic_'+uuid.uuid4().hex
    module=ModuleType(name);module.__file__=str(ROOT/tool.SOURCE)
    module.__loaded_source_sha256__=sha(raw);module.__canonical_stack_lease_v2_issuer__=True
    assert sys.modules.setdefault(name,module) is module
    try:
        exec(compile(raw,module.__file__,'exec'),module.__dict__);yield module
    finally:
        assert sys.modules.get(name) is module;del sys.modules[name]

def kwargs():
    return dict(field_module=field,field_kwargs=field_fixture.kwargs(),
        template_source=(ROOT/tool.LEASE_TEMPLATE).read_bytes(),template_module=frozen,assembler_module=clip)

def inventory_kwargs():
    return {key:value for key,value in kwargs().items() if key!='field_kwargs'}

def emit(profile='classic',resolution='1024x768',fresh=False):
    key=(profile,resolution)
    if not fresh and key in CACHE: return CACHE[key]
    layout,life,route,parent=field_fixture.emit(profile,resolution,fresh=fresh)
    out=tool._emit_code(layout,life,route,parent,**kwargs())
    result=layout,life,route,parent,out
    if not fresh: CACHE[key]=result
    return result

def decode(code,address_values):
    """Independent instruction/operand oracle with exact semantic address values."""
    rows=[];cursor=0
    while cursor<len(code):
        start=cursor;absolute=[];relative=[];scalar=[];op=code[cursor];cursor+=1
        def immediate(size=4,displacement=False):
            nonlocal cursor
            value=int.from_bytes(code[cursor:cursor+size],'little')
            if size==4 and not displacement and value in address_values: absolute.append(cursor)
            else: scalar.append((cursor,size))
            cursor+=size
        if op in (0x9c,0x9d,0x60,0x61,0xfc,0xc3,0x55,0x5d): pass
        elif op==0xc2: immediate(2)
        elif op==0xf3: assert code[cursor]==0xaf;cursor+=1
        elif 0xb8<=op<=0xbf or op==0xa9: immediate()
        elif op in (0xe8,0xe9): relative.append(cursor);cursor+=4
        elif op==0x0f:
            sub=code[cursor];cursor+=1
            if sub!=0x0b:
                assert 0x82<=sub<=0x87;relative.append(cursor);cursor+=4
        elif op in (0x81,0x83,0x8b,0x89,0x3b,0x39,0x85,0xf7,0xff,0x31):
            mr=code[cursor];cursor+=1;mode,rm=mr>>6,mr&7
            if mode!=3 and rm==4:
                sib=code[cursor];cursor+=1
                if mode==0 and sib&7==5: absolute.append(cursor);cursor+=4
            if mode==0 and rm==5: absolute.append(cursor);cursor+=4
            elif mode==1: immediate(1,True)
            elif mode==2: immediate(4,True)
            if op==0x81 or op==0xf7 and (mr>>3)&7==0: immediate()
            elif op==0x83: immediate(1)
        else: raise AssertionError(('unknown independent lease opcode',start,op))
        assert start<cursor<=len(code)
        rows.append((start,cursor,tuple(absolute),tuple(relative),tuple(scalar)))
    return rows

def address_values(out,layout):
    modal=next((row.va for row in layout.protected_spans if row.role=='parent:.hdstate'),None)
    return ({out.base_va,out.base_va+len(out.code),layout.rw.va,layout.rw.va+128} |
        ({modal,modal+128} if modal is not None else set()) |
        {pc for _,pc in out.field_return_pcs+out.lease_return_pcs} |
        set(frozen.TILE_UNIT_RETURNS+frozen.ADJACENT_UNIT_RETURNS+frozen.TILE_SPRITE_RETURNS) |
        {0x42fc1e,0x405555,0x4055b6,0x430ad8,0x430b0a,0x42fa7c,0x42fbbd,0x43087d,0x42f932,0x4302dc})

def relocation_oracle(out,layout,parent):
    instructions=decode(out.code,address_values(out,layout));starts={start for start,*_ in instructions}
    absolute={at for _,_,aa,_,_ in instructions for at in aa}
    relative={at for _,_,_,rr,_ in instructions for at in rr}
    scalars={at for _,_,_,_,ss in instructions for at,_ in ss}
    declarations={row.offset:row for row in out.relocations};assert len(declarations)==len(out.relocations)
    assert {at for at,row in declarations.items() if row.kind=='abs32'}==absolute
    assert {at for at,row in declarations.items() if row.kind=='rel32'}==relative
    assert not(set(declarations)&scalars)
    typed=tool._operand_inventory(out,layout,parent,**inventory_kwargs())
    assert {row.offset for row in typed if row.kind=='abs32'}==absolute
    assert {row.offset for row in typed if row.kind=='rel32'}==relative
    assert {row.offset for row in typed if row.kind.startswith('scalar')}==scalars
    for start,end,_,rr,_ in instructions:
        for at in rr:
            target=out.base_va+at+4+struct.unpack_from('<i',out.code,at)[0]
            assert declarations[at].target==target
            if declarations[at].purpose.startswith('lease_v2_internal:'):
                assert target-out.base_va in starts
            else:
                assert out.code[start]==0xe8
                assert target in set(dict(parent.entries).values())|set(dict(parent.private_entries).values())|{0x402e80,0x403f70}
    assert tuple(out.field_tile_receipts)==field._tile_receipts(parent)
    assert tuple((m,pc) for m,pc,_,_ in out.field_tile_receipts)==out.field_return_pcs
    assert tuple((m,pc) for m,pc,_,_ in out.lease_field_receipts)==out.lease_return_pcs
    for mode,pc,at,target in out.lease_field_receipts:
        assert pc==out.base_va+at and out.code[at-5]==0xe8
        assert target==dict(parent.entries)['draw_incremental' if mode else 'draw_full']
        assert declarations[at-4].target==target
    assert all(va-out.base_va in starts for _,va in out.entries+out.private_entries)
    return len(instructions),len(absolute),len(relative),len(scalars)

class SourceTests(unittest.TestCase):
    def test_all36_deterministic_geometry_full_inventory_and_actual_descriptors(self):
        verify_frozen()
        for profile in context.PROFILES:
            for resolution in context.RESOLUTIONS:
                with self.subTest(profile=profile,resolution=resolution):
                    layout,life,route,parent,out=emit(profile,resolution)
                    self.assertEqual(asdict(out),asdict(emit(profile,resolution,fresh=True)[4]))
                    self.assertEqual(tuple(dict(out.entries)),tool.PUBLIC)
                    self.assertEqual(tuple(dict(out.private_entries)),tool.PRIVATE)
                    self.assertEqual(out.base_va,(parent.base_va+len(parent.code)+15)&~15)
                    self.assertLessEqual(out.base_va+len(out.code),layout.rx.va+262144)
                    counts=relocation_oracle(out,layout,parent)
                    self.assertGreater(counts[2],600);self.assertGreater(counts[3],1200)

    def test_complete_parent_layout_template_scalar_branch_and_descriptor_rejections(self):
        layout,life,route,parent,out=emit('modalwidgets','1920x1080')
        for bad in (replace(parent,code=parent.code[:-1]),replace(parent,entries=parent.entries[:-1]),
                    replace(parent,private_entries=parent.private_entries[:-1]),replace(parent,relocations=parent.relocations[:-1])):
            with self.assertRaisesRegex(ValueError,'canonical fresh field'):
                tool._emit_code(layout,life,route,bad,**kwargs())
        for bad in (replace(layout,rx=replace(layout.rx,size=131072)),replace(layout,rw=replace(layout.rw,size=4096)),
                    replace(layout,battle_state_va=layout.rw.va+256),replace(layout,provider_schema='invented'),
                    replace(layout,protected_spans=layout.protected_spans[:-1]),replace(layout,resolution='802x602')):
            with self.assertRaises(ValueError): tool._emit_code(bad,life,route,parent,**kwargs())
        with self.assertRaises(ValueError): tool._versioned_template(kwargs()['template_source']+b'\n',frozen)
        variants=[replace(out,relocations=out.relocations[:-1]),replace(out,relocations=out.relocations+(out.relocations[0],)),
            replace(out,field_tile_receipts=out.field_tile_receipts[:-1]),replace(out,field_return_pcs=out.field_return_pcs[::-1]),
            replace(out,lease_field_receipts=out.lease_field_receipts[::-1]),
            replace(out,lease_return_pcs=((0,out.base_va+1),)+out.lease_return_pcs[1:]),replace(out,private_entries=out.private_entries[:-1])]
        operands=tool._operand_inventory(out,layout,parent,**inventory_kwargs())
        for role in ('internal_conditional_branch','internal_jump','native_normal_return_call','field_call'):
            row=next(r for r in operands if r.role==role)
            variants.append(replace(out,relocations=tuple(r for r in out.relocations if r.offset!=row.offset)))
        for row in (next(r for r in operands if r.kind=='scalar32'),next(r for r in operands if r.kind=='abs32')):
            raw=bytearray(out.code);raw[row.offset]^=1;variants.append(replace(out,code=bytes(raw)))
        scalar=next(r for r in operands if r.kind=='scalar32')
        variants.append(replace(out,relocations=out.relocations+(clip.Relocation(scalar.offset,'abs32',scalar.value,'invented scalar'),)))
        for bad in variants:
            with self.assertRaisesRegex(ValueError,'authored lease'):
                tool._operand_inventory(bad,layout,parent,**inventory_kwargs())

    def test_whole_checked_edit_ledger_and_explicit_capacity_cancellation_limits(self):
        _,ledger,_=tool._versioned_template(kwargs()['template_source'],frozen)
        self.assertEqual(len(ledger),18)
        self.assertTrue(all(count==1 for _,_,count in ledger))
        self.assertEqual((tool.LEASE_BYTES,tool.HELPER_BYTES,tool.FIELD_BYTES),(192,512,1280))
        self.assertLessEqual(tool.CONTROL_SHADOW+4*len(tool.CONTROL_SLOTS),512)
        for name in ('latched_leaf_loss_consumption_by_field','next_Tile_cancellation','native_stack_capacity_verified',
                     'healthy_native_unwind_verified','whole_chain_capacity_verified','native_provider_rle_verified'):
            self.assertIn(name,tool.FALSE_CLAIMS)
        self.assertEqual(sha((ROOT/tool.FIELD).read_bytes()),tool.PINNED_SOURCES[tool.FIELD])

    def test_private_pins_read_identity_and_public_aliases_cannot_issue(self):
        with issuer() as own:
            snapshot=own._snapshot()
            with patch.dict(own.PINNED_SOURCES,{own.FIELD:'0'*64}):
                with self.assertRaisesRegex(ValueError,'source pin'): own._snapshot()
            original=Path.read_bytes
            with patch.object(Path,'read_bytes',lambda path:b'#'+original(path)[1:] if path==ROOT/tool.SOURCE else original(path)):
                with self.assertRaisesRegex(ValueError,'closure changed'): own._unchanged(snapshot)
            with patch.object(Path,'is_symlink',lambda path:path==ROOT/tool.SOURCE):
                with self.assertRaisesRegex(ValueError,'reparse'): own._read(ROOT/tool.SOURCE,ROOT)
            with patch.object(Path,'read_bytes',lambda path:original(path)[:-1] if path==ROOT/tool.SOURCE else original(path)):
                with self.assertRaisesRegex(ValueError,'changed while read'): own._read(ROOT/tool.SOURCE,ROOT)
        private=next(cell.cell_contents for cell in tool.emit_stack_lease_v2.__closure__
            if callable(cell.cell_contents) and getattr(cell.cell_contents,'__name__',None)=='_issue')
        self.assertIsNot(private,tool._issue)
        self.assertTrue(private.__globals__['__canonical_stack_lease_v2_issuer__'])
        def poison(*args,**kwargs): raise AssertionError('public alias invoked')
        with issuer() as own,patch.object(tool,'_emit_code',poison),patch.object(field,'_issue',poison):
            with own._modules(own._snapshot()) as modules:
                for name in (own.FIELD,own.ROUTING,own.LIFECYCLE,own.CONTEXT,own.LEASE_TEMPLATE):
                    self.assertEqual(modules[name].__loaded_source_sha256__,own.PINNED_SOURCES[name])
                self.assertIsNot(modules[own.FIELD]._issue,poison)
        for value in (b'',bytearray(),memoryview(b'')):
            with self.assertRaises(ValueError): tool.emit_stack_lease_v2(value,'classic','1024x768')

    def test_foreign_registry_and_parent_attributes_are_preserved(self):
        token='d'*32;prefix='_battle_lease_v2_'+token
        with issuer() as own:
            for name in (prefix,prefix+'.src',prefix+'.src.patcher',prefix+'.src.patcher.battle_profile_field_v3'):
                foreign=ModuleType(name);foreign.marker=object();attrs=dict(foreign.__dict__);sys.modules[name]=foreign
                try:
                    with patch.object(uuid,'uuid4',return_value=SimpleNamespace(hex=token)):
                        with self.assertRaisesRegex(ValueError,'occupied'):
                            with own._modules(own._snapshot()): self.fail('collision admitted')
                    self.assertIs(sys.modules[name],foreign);self.assertEqual(foreign.__dict__,attrs)
                finally: del sys.modules[name]
            with self.assertRaisesRegex(ValueError,'identity changed'):
                with own._modules(own._snapshot()) as modules:
                    parent=sys.modules[modules[own.FIELD].__package__]
                    foreign=object();setattr(parent,'battle_profile_field_v3',foreign)
            self.assertIs(parent.battle_profile_field_v3,foreign)
            for removed in (False,True):
                foreign=ModuleType('preserved_replacement')
                with self.assertRaisesRegex(ValueError,'identity changed'):
                    with own._modules(own._snapshot()) as modules:
                        name=modules[own.FIELD].__name__
                        if removed:del sys.modules[name]
                        else:sys.modules[name]=foreign
                if removed:self.assertNotIn(name,sys.modules)
                else:
                    self.assertIs(sys.modules[name],foreign);del sys.modules[name]
            name='_battle_lease_v2_issuer_'+token;foreign=ModuleType(name);sys.modules[name]=foreign
            try:
                with patch.object(uuid,'uuid4',return_value=SimpleNamespace(hex=token)):
                    with self.assertRaisesRegex(ValueError,'occupied'):own._production_factory()
                self.assertIs(sys.modules[name],foreign)
            finally:del sys.modules[name]


class Machine(field_fixture.Machine):
    # The legacy fixture supplies independently authored ABI/ancestry setup;
    # the actual mapped parent is exclusively the fresh field V3 chain.
    begin=old_fixture.Machine.begin
    lease_word=old_fixture.Machine.lease_word
    ancestry=old_fixture.Machine.ancestry
    invoke_leaf=old_fixture.Machine.invoke_leaf

    def __init__(self,tools,profile='classic',resolution='1024x768',delta=0):
        self.pause_tile=False;self.primitive_mutation=None;self.primitives=[];self.closures=[]
        hooks=[];deleted=set();original_hook=tools[0].Uc.hook_add;original_delete=tools[0].Uc.hook_del
        def capture(cpu,kind,*args,**kwargs):
            handle=original_hook(cpu,kind,*args,**kwargs);hooks.append((kind,handle));return handle
        def remove(cpu,handle):
            deleted.add(handle);return original_delete(cpu,handle)
        with patch.object(tools[0].Uc,'hook_add',capture),patch.object(tools[0].Uc,'hook_del',remove):
            super().__init__(tools,profile,resolution,delta)
        self.lease_emission=emit(profile,resolution)[4]
        self.lease_entries={name:va+delta for name,va in self.lease_emission.entries}
        raw=bytearray(self.lease_emission.code)
        for row in self.lease_emission.relocations:
            if row.kind=='abs32':struct.pack_into('<I',raw,row.offset,row.target+delta)
        self.cpu.mem_write(self.lease_emission.base_va+delta,bytes(raw))
        self.loaded_code.append((self.lease_emission.base_va+delta,bytes(raw)))
        self.thread_clobbers=True
        # Observe every actual tail read, but suppress per-iteration code hooks
        # over genuine REP loops as the independent field fixture already does.
        exclusions=[]
        decoders=((self.emission,field_fixture.routing_fixture.lifetime.decode),
            (self.routing_emission,field_fixture.routing_fixture.decode),(self.field_emission,field_fixture.decode),
            (self.lease_emission,lambda code:decode(code,address_values(self.lease_emission,self.layout))))
        for emitted,decoder in decoders:
            for row in decoder(emitted.code):
                start,end=row[:2]
                if emitted.code[start]!=0xf3:continue
                va=emitted.base_va+delta+start;exclusions.append((va,va+end-start-1))
                if emitted is self.lease_emission:
                    assert emitted.code[start+1]==0xaf and emitted.code[start-10]==0xb9 and emitted.code[start-5]==0xbf
                    count=struct.unpack_from('<I',emitted.code,start-9)[0]
                    pointer=struct.unpack_from('<I',emitted.code,start-4)[0]+delta
                    self.scan_before[va-5]=(va+2,pointer,count);self.scan_after[va+2]=(pointer,count)
        for kind,handle in hooks:
            if kind==self.u.UC_HOOK_CODE and handle not in deleted:self.cpu.hook_del(handle)
        cursor=1
        for lo,hi in sorted(exclusions):
            if cursor<lo:self.cpu.hook_add(self.u.UC_HOOK_CODE,self.on_code,begin=cursor,end=lo-1)
            cursor=hi+1
        self.cpu.hook_add(self.u.UC_HOOK_CODE,self.on_code,begin=cursor,end=0xffffffff)

    def on_code(self,cpu,address,size,data):
        if address==0x42ffb0+self.delta and self.pause_tile:
            self.tile_context={name:cpu.reg_read(reg) for name,reg in self.regs.items()}
            self.tile_sp=self.tile_context['ESP'];self.field_frame=self.tile_sp+4
            self.lease_frame=self.word(self.field_frame+1288)
            self.pause_tile=False;self.tile_paused=True;cpu.emu_stop()
        elif address in (0x402e80+self.delta,0x403f70+self.delta):
            family='sprite' if address==0x402e80+self.delta else 'line';pop=28 if family=='sprite' else 8
            sp=cpu.reg_read(self.regs['ESP']);args=tuple(self.word(sp+at) for at in range(4,pop+1,4))
            registers={name:cpu.reg_read(self.regs[name]) for name in ('EAX','ECX','EDX','EBX','EBP','ESI','EDI','EFLAGS')}
            self.callback(family);self.primitives.append((family,args,registers));self.closures.append(family)
            if self.primitive_mutation:self.primitive_mutation(self,family)
            cpu.reg_write(self.regs['EAX'],0xc0ffee11);cpu.reg_write(self.regs['ECX'],0x1234abcd)
            cpu.reg_write(self.regs['EDX'],0x5678ef01);cpu.reg_write(self.regs['EFLAGS'],0x247)
            self.ret();cpu.reg_write(self.regs['ESP'],sp+4+pop)
        else:super().on_code(cpu,address,size,data)

    def complete(self):
        self.stops,self.native_stop=set(),None
        for name,value in self.tile_context.items():self.cpu.reg_write(self.regs[name],value)
        field_fixture.Machine.on_code(self,self.cpu,0x42ffb0+self.delta,1,None)
        self.cpu.emu_start(self.cpu.reg_read(self.regs['EIP']),self.STOP+1,count=30000000)
        actual={name:self.cpu.reg_read(reg) for name,reg in self.regs.items()}
        assert self.native_stop==self.STOP and actual['ESP']==self.SP+4
        for name,value in self.initial.items():
            if name not in ('EAX','ESP'):assert actual[name]==value,(name,actual[name],value)
        assert actual['EFLAGS']&self.MASK==self.initial_flags&self.MASK
        for va,expected in self.loaded_code:assert bytes(self.cpu.mem_read(va,len(expected)))==expected
        self.field_active=self.routing_active=False;return actual

    def invoke_outer(self,mode=0,*,eax=0,edx=0):
        self.field_active=self.routing_active=True;self.stops=set();self.native_stop=None;self.pause_tile=False
        self.writes=[];self.reads=[];self.tiles=[];self.minimum_sp=self.SP
        self.scan_observations=0;self.scan_dwords=0;before_callbacks=len(self.callbacks)
        registers=dict(EAX=eax,EDX=edx,ECX=0x10203040,EBX=0x40506070,
            EBP=0x50607080,ESI=0x60708090,EDI=0x708090a0,ESP=self.SP)
        self.put(self.SP,self.STOP)
        for name,value in registers.items():self.cpu.reg_write(self.regs[name],value&0xffffffff)
        self.cpu.reg_write(self.regs['EFLAGS'],0xed7)
        try:self.cpu.emu_start(self.lease_entries['leased_draw_incremental' if mode else 'leased_draw_full'],self.STOP+1,count=30000000)
        finally:self.field_active=self.routing_active=False
        actual={name:self.cpu.reg_read(reg) for name,reg in self.regs.items()}
        assert self.native_stop==self.STOP and actual['ESP']==self.SP+4
        for name,value in registers.items():
            if name not in ('EAX','ESP'):assert actual[name]==value&0xffffffff,(name,actual[name],value)
        assert actual['EFLAGS']&self.MASK==0xed7&self.MASK
        self.outer_callbacks=self.callbacks[before_callbacks:]
        return actual


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:cls.tools=field_fixture.routing_fixture.lifetime.prior_fixture.machine_tools()
        except ImportError as error:raise unittest.SkipTest(str(error))

    def make(self,profile='modalwidgets',resolution='800x600',delta=0,columns=1,mode=0):
        return Machine(self.tools,profile,resolution,delta).prepare(columns=columns).begin(mode,eax=0,edx=0)

    def no_cached_reads(self,m):
        ranges=((m.PHYSICAL,m.PHYSICAL+188),(m.PRIVATE,m.PRIVATE+188),(m.BACKEND,m.BACKEND+168),(m.WORLD,m.WORLD+0xf7c))
        self.assertFalse(any(at<hi and at+size>lo for at,size in m.reads for lo,hi in ranges))

    def test_all36_two_bases_full_incremental_small_arena_pixels_and_outer_abi(self):
        for profile in context.PROFILES:
            for resolution in context.RESOLUTIONS:
                for delta in (0,0x100000):
                    for mode in (0,1):
                        with self.subTest(profile=profile,resolution=resolution,delta=delta,mode=mode):
                            m=self.make(profile,resolution,delta,columns=2,mode=mode);before=m.pixels();record=m.record()
                            actual,registers,args=m.invoke_leaf('sprite_charge_adjacent',guarded=True)
                            self.assertEqual(actual['EAX'],0xc0ffee11);self.assertEqual(actual['EFLAGS']&m.MASK,0x247&m.MASK)
                            self.assertEqual(m.primitives[0][1],args);self.assertEqual(m.primitives[0][2]['ECX'],registers['ECX'])
                            self.assertEqual(m.closures,['sprite']);self.assertEqual(m.complete()['EAX'],1)
                            cells=[(0,0)] if mode else [(x,y) for x in range(2) for y in range(7)]
                            self.assertEqual(m.tiles,cells);self.assertEqual(m.record(),record)
                            self.assertEqual(m.pixels(),field_fixture.pixel_oracle.expected_pixels(m.width,m.height,2,0,before,cells))
                            del m;gc.collect()

    def test_every_native_family_and_authenticated_return_site_balances_normal_abi(self):
        m=self.make()
        for path in old_fixture.PATHS:
            with self.subTest(path=path):
                guarded=path.startswith('sprite') or path=='line';before_closures=len(m.closures)
                actual,before,args=m.invoke_leaf(path,guarded=guarded)
                self.assertEqual(actual['EAX'],0xc0ffee11 if guarded else 1)
                self.assertEqual(actual['EFLAGS']&m.MASK,(0x247 if guarded else 0xed7)&m.MASK)
                self.assertEqual(actual['EBP'],before['EBP']);self.assertEqual(actual['ESI'],before['ESI']);self.assertEqual(actual['EDI'],before['EDI'])
                self.assertEqual(len(m.closures),before_closures+guarded)
                if guarded:self.assertEqual(m.primitives[-1][1],args)
        for path,sites in (('unit',frozen.TILE_UNIT_RETURNS),('unit_adjacent',frozen.ADJACENT_UNIT_RETURNS),
                           ('sprite_tile',frozen.TILE_SPRITE_RETURNS),('line',(0x430ad8,0x430b0a))):
            for pc in sites:
                actual,_,_=m.invoke_leaf(path,guarded=path.startswith('sprite') or path=='line',return_override=pc)
                self.assertEqual(actual['EAX'],0xc0ffee11 if path.startswith('sprite') or path=='line' else 1)
        self.assertEqual(m.complete()['EAX'],1)

    def test_unknown_ancestry_alignment_and_full_descriptor_denial_before_reads(self):
        m=self.make()
        for path in old_fixture.PATHS:
            actual,_,_=m.invoke_leaf(path,guarded=path.startswith('sprite') or path=='line',return_override=m.STOP)
            self.assertEqual(actual['EAX'],0);self.no_cached_reads(m);self.assertEqual(m.primitives,[])
        for offset in range(0,192,4):
            at=m.lease_frame+offset;old=m.word(at);m.put(at,old^4)
            actual,_,_=m.invoke_leaf('sprite_tile',guarded=True)
            self.assertEqual(actual['EAX'],0);self.no_cached_reads(m);m.put(at,old)
        for sp in (m.ROOT_SP+256,m.ROOT_SP+257):
            actual,_,_=m.invoke_leaf('tile',entry_sp=sp)
            self.assertEqual(actual['EAX'],0);self.no_cached_reads(m)
        self.assertEqual(m.closures,[])

    def test_full_fixed_tail_cache_control_and_descriptor_loss_precedes_poisoned_pages(self):
        m=self.make();descriptor=bytes(m.cpu.mem_read(m.lease_frame,192))
        points=[m.state_va+at for at in range(0,128,4)]
        points += [m.modal_va+at for at in range(0,128,4)]
        points += [m.state_va+128,m.state_va+65532,m.modal_va+128,m.modal_va+4092]
        points += [m.field_frame+at for at in (1104,1112,1120,1124,1132,1136,1140,1144,1156,1160,1164,1168)]
        points += [m.lease_frame+at for at in range(0,192,4)]
        points += [native.PRIMARY+at for at in range(0,216,4)]
        points += [0x5202e0,0x511230,0x5199d8,0x526994,0x526990,0x532048,tool.THREAD_IAT]
        for boundary in ('before_thread','thread','normal_return'):
            for at in points:
                with self.subTest(boundary=boundary,address=hex(at)):
                    old=m.word(at);before=len(m.closures)
                    def corrupt(machine,label):
                        # leaf_status1 is a valid earlier normal-return receipt
                        # before a new helper starts;2 is the loss state. During
                        # callbacks every changed pre-callback value must fail.
                        mask=2 if boundary=='before_thread' and at==machine.lease_frame+48 else 1
                        machine.put(at,machine.word(at)^mask)
                        machine.cpu.mem_protect(machine.PHYSICAL,4096,machine.u.UC_PROT_NONE)
                    try:
                        if boundary=='before_thread':corrupt(m,'before')
                        elif boundary=='thread':m.mutation=lambda machine,label:corrupt(machine,label) if label=='thread' else None
                        else:m.primitive_mutation=corrupt
                        actual,_,_=m.invoke_leaf('sprite_tracking_adjacent',guarded=True)
                        self.assertEqual(actual['EAX'],0xc0ffee11 if boundary=='normal_return' else 0)
                        self.assertEqual(len(m.closures),before+(boundary=='normal_return'))
                        self.assertFalse(any(address==native.RENDER for address,_ in m.writes))
                        if boundary!='normal_return':self.no_cached_reads(m)
                        else:
                            self.assertEqual(m.lease_word('loss'),2)
                            self.assertEqual(actual['EFLAGS']&m.MASK,0x247&m.MASK)
                    finally:
                        m.mutation=m.primitive_mutation=None
                        m.cpu.mem_protect(m.PHYSICAL,4096,m.u.UC_PROT_ALL)
                        m.put(at,old);m.cpu.mem_write(m.lease_frame,descriptor)

    def test_helper_control_corruption_has_actual_unsafe_terminal_and_no_cached_read(self):
        for boundary in ('thread','normal_return'):
            for offset in tool.CONTROL_SLOTS:
                # Native normal-return output slots legitimately change.
                if boundary=='normal_return' and offset in (-4,512,516,528,532,536,540,544):continue
                with self.subTest(boundary=boundary,offset=offset):
                    m=self.make();seen=[]
                    def corrupt(machine,label):
                        helper=machine.cpu.reg_read(machine.regs['EBP'])
                        machine.put(helper+offset,machine.word(helper+offset)^4)
                        machine.cpu.mem_protect(machine.PHYSICAL,4096,machine.u.UC_PROT_NONE);seen.append(helper)
                    if boundary=='thread':m.mutation=lambda machine,label:corrupt(machine,label) if label=='thread' else None
                    else:m.primitive_mutation=corrupt
                    with self.assertRaises(self.tools[0].UcError):m.invoke_leaf('sprite_tracking_adjacent',guarded=True)
                    self.assertEqual(len(seen),1)
                    eip=m.cpu.reg_read(m.regs['EIP']);self.assertEqual(bytes(m.cpu.mem_read(eip,2)),b'\x0f\x0b')
                    self.assertIsNone(m.native_stop);self.assertFalse(any(at==native.RENDER for at,_ in m.writes))
                    if boundary=='thread':self.no_cached_reads(m)
                    self.assertEqual(len(m.closures),boundary=='normal_return')
                    del m;gc.collect()

    def test_normal_return_loss_retains_outputs_and_cleanup_once_without_retry(self):
        for family in ('sprite_tile','line'):
            m=self.make()
            def corrupt(machine,label):machine.put(machine.lease_frame+188,1)
            m.primitive_mutation=corrupt
            actual,_,_=m.invoke_leaf(family,guarded=True)
            self.assertEqual(actual['EAX'],0xc0ffee11);self.assertEqual(actual['EFLAGS']&m.MASK,0x247&m.MASK)
            self.assertEqual(m.lease_word('loss'),2);self.assertEqual(m.lease_word('leaf_status'),2)
            self.assertEqual(m.closures,['line' if family=='line' else 'sprite'])
            m.primitive_mutation=None
            self.assertEqual(m.invoke_leaf(family,guarded=True)[0]['EAX'],0)
            self.assertEqual(len(m.closures),1)

    def test_paired_descriptor_copy_corruption_regression_at_both_callbacks(self):
        # The provisional emitter admitted tag+copy mutation and called one
        # modeled primitive. This source diagnostic is deliberately retained as
        # a rejection fixture, never a historical game/native failure claim.
        for boundary in ('thread','normal_return'):
            m=self.make();descriptor=bytes(m.cpu.mem_read(m.lease_frame,192))
            for offset in range(0,192,4):
                with self.subTest(boundary=boundary,offset=offset):
                    before=len(m.closures);observed=[]
                    def corrupt(machine,label):
                        helper=machine.cpu.reg_read(machine.regs['EBP'])
                        for at in (machine.lease_frame+offset,helper+offset):
                            machine.put(at,machine.word(at)^1)
                        machine.reads.clear();machine.writes.clear()
                        machine.cpu.mem_protect(machine.PHYSICAL,4096,machine.u.UC_PROT_NONE)
                        observed.append(helper)
                    if boundary=='thread':m.mutation=lambda machine,label:corrupt(machine,label) if label=='thread' else None
                    else:m.primitive_mutation=corrupt
                    actual,_,_=m.invoke_leaf('sprite_tracking_adjacent',guarded=True)
                    self.assertEqual(len(observed),1)
                    self.assertEqual(actual['EAX'],0xc0ffee11 if boundary=='normal_return' else 0)
                    self.assertEqual(len(m.closures),before+(boundary=='normal_return'))
                    self.no_cached_reads(m)
                    self.assertFalse(any(at==native.RENDER for at,_ in m.writes))
                    if boundary=='normal_return':self.assertEqual(m.lease_word('loss'),2)
                    m.mutation=m.primitive_mutation=None
                    m.cpu.mem_protect(m.PHYSICAL,4096,m.u.UC_PROT_ALL);m.cpu.mem_write(m.lease_frame,descriptor)

    def test_lease_only_loss_does_not_fabricate_next_tile_cancellation(self):
        m=self.make(columns=2);record=m.record()
        m.put(m.lease_frame+44,2)
        self.assertEqual(m.complete()['EAX'],2)
        self.assertEqual(m.tiles,[(x,y) for x in range(2) for y in range(7)])
        self.assertEqual(m.record(),record)
        self.assertIn('next_Tile_cancellation',tool.FALSE_CLAIMS)

    def test_outer_zero_only_for_full_virgin_and_owned_history_root_losses_are_two(self):
        for profile in context.PROFILES:
            for delta in (0,0x100000):
                m=Machine(self.tools,profile,'800x600',delta)
                for mode in (0,1):
                    self.assertEqual(m.invoke_outer(mode)['EAX'],0)
                    self.assertEqual(m.outer_callbacks,[]);self.assertEqual(m.tiles,[]);self.no_cached_reads(m)
                poison=[m.state_va+at for at in range(0,128,4)] + [m.state_va+128,m.state_va+65532]
                if m.modal_va is not None:poison += [m.modal_va+delta+at for at in range(0,128,4)]+[m.modal_va+delta+128,m.modal_va+delta+4092]
                for at in poison:
                    old=m.word(at);m.put(at,1)
                    self.assertEqual(m.invoke_outer()['EAX'],2)
                    self.assertEqual(m.outer_callbacks,[]);self.assertEqual(m.tiles,[]);self.no_cached_reads(m)
                    self.assertFalse(any(address==native.RENDER+delta for address,_ in m.writes));m.put(at,old)
                m.prepare(columns=1)
                for phase in (0,2):
                    m.set_state('phase',phase)
                    for root in (0,3,0x10000,0x7fff0000,m.ROOT_SP+1,m.SP-4):
                        m.set_state('root_esp',root)
                        for mode in (0,1):
                            self.assertEqual(m.invoke_outer(mode)['EAX'],2)
                            self.assertEqual(m.outer_callbacks,[]);self.assertEqual(m.tiles,[]);self.no_cached_reads(m)
                            self.assertFalse(any(address==native.RENDER+delta for address,_ in m.writes))
                del m;gc.collect()

    def test_owned_off_field_field_zero_is_stricter_lease_denial_without_tile_or_render(self):
        m=Machine(self.tools,'modalwidgets','800x600').prepare(columns=1)
        for x,y in ((-1,0),(1,0),(0,-1),(0,7)):
            record=m.record();render=m.word(native.RENDER)
            self.assertEqual(m.invoke_outer(1,eax=x,edx=y)['EAX'],2)
            self.assertEqual(m.tiles,[]);self.assertEqual(m.primitives,[])
            self.assertEqual(m.record(),record);self.assertEqual(m.word(native.RENDER),render)
            self.assertFalse(any(at==native.RENDER for at,_ in m.writes))
            # Frozen FieldV3 performs genuine modeled Thread admission first;
            # no native Tile/primitive callback or target publication follows.
            self.assertEqual(m.outer_callbacks,['thread'])

    def test_independent_native_instruction_lengths_cover_two_bases(self):
        for profile in context.PROFILES:
            layout,_,_,parent,out=emit(profile,'3840x2160')
            expected=decode(out.code,address_values(out,layout))
            for delta in (0,0x100000):
                u,r=self.tools;cpu=u.Uc(u.UC_ARCH_X86,u.UC_MODE_32);raw=bytearray(out.code)
                for row in out.relocations:
                    if row.kind=='abs32':struct.pack_into('<I',raw,row.offset,row.target+delta)
                start=out.base_va+delta;page=start&~4095;cpu.mem_map(page,(start+len(raw)-page+4095)&~4095)
                cpu.mem_write(start,bytes(raw));lengths=[]
                def skip(machine,address,size,data):
                    lengths.append((address-start,size));machine.reg_write(r.UC_X86_REG_EIP,address+size)
                cpu.hook_add(u.UC_HOOK_CODE,skip);cpu.emu_start(start,start+len(raw),count=len(raw))
                self.assertEqual(lengths,[(at,end-at) for at,end,*_ in expected])
                self.assertEqual(sum(size for _,size in lengths),len(raw))

    def test_actual_helper_stack_low_point_includes_field_tail_scan_and_private_returns(self):
        for path in ('tile','unit','adjacent','tracking_tile','charge_unit','sprite_tracking_adjacent','line'):
            m=self.make();entry,_,_=m.ancestry(path);helper=entry-548;minimum=[entry]
            def observe(cpu,address,size,data):
                minimum[0]=min(minimum[0],cpu.reg_read(m.regs['ESP']))
            handle=m.cpu.hook_add(m.u.UC_HOOK_CODE,observe)
            try:actual,_,_=m.invoke_leaf(path,guarded=path.startswith('sprite') or path=='line')
            finally:m.cpu.hook_del(handle)
            self.assertEqual(minimum[0],helper-44)
            self.assertEqual(helper+552-minimum[0],596)
            self.assertEqual(actual['EAX'],0xc0ffee11 if path.startswith('sprite') or path=='line' else 1)
            self.assertTrue(any('add(7,-44)' in new and 'HELPER_BYTES+84' in new
                for _,new,_ in tool._versioned_template(kwargs()['template_source'],frozen)[1]))
            del m;gc.collect()


class OriginalTests(unittest.TestCase):
    def test_optional_exact_original_reconstruction_and_all_broader_flags_false(self):
        if ORIGINAL is None:self.skipTest('optional Original RAM reconstruction')
        before=ORIGINAL.read_bytes();self.assertEqual(sha(before),tool.BASE_SHA256)
        result=tool.emit_stack_lease_v2(before,'modalwidgets','1920x1080')
        self.assertEqual(ORIGINAL.read_bytes(),before)
        layout=result.field_bundle.routing_bundle.lifecycle_bundle.allocation_context.layout
        relocation_oracle(result.emission,layout,result.field_bundle.emission)
        self.assertEqual(result.hook_sites,());self.assertEqual(result.removed_highlow_rvas,())
        for name in tool.FALSE_CLAIMS:self.assertIs(result.metadata()[name],False,name)

def main(argv=None):
    global ORIGINAL
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-only',action='store_true');parser.add_argument('--require-machine-tools',action='store_true')
    parser.add_argument('--toolchain-path',type=Path);parser.add_argument('--original-backed',type=Path)
    args=parser.parse_args(argv)
    if args.toolchain_path:sys.path.insert(0,str(args.toolchain_path.resolve()))
    if args.require_machine_tools:
        try:field_fixture.routing_fixture.lifetime.prior_fixture.machine_tools()
        except ImportError as error:print(str(error),file=sys.stderr);return 2
    classes=(SourceTests,) if args.source_only else (SourceTests,CPUTests)
    if args.original_backed:ORIGINAL=args.original_backed;classes+=(OriginalTests,)
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in classes)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
