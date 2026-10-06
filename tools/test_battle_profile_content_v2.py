#!/usr/bin/env python3
"""Fresh ContentV2 source and CPU models, never native/game execution.

--prototype runs only source scaffolding before the production lease freeze.
Default final lanes require the final frozen dependency and Unicorn; no skips.
"""
from __future__ import annotations
import argparse
import ast
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
import sys
import time
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from src.patcher import battle_profile_content_v2 as tool
from src.patcher import battle_profile_content as frozen
from src.patcher import battle_profile_field_v3 as field
from src.patcher import battle_profile_stack_lease_v2 as lease
from src.patcher import partial_tile_clip as clip
import test_battle_profile_stack_lease_v2 as parent_fixture
import test_battle_profile_content as old_fixture

FIELD_FIXTURE_SHA256='a5e4f26de52766513bdac5abec85a076bdaf7e96155e99fa3fa52194e1ffcbba'
LEASE_FIXTURE_SHA256='d87bfba633789609be12b0c1e7f542c16d115dc544fb00edd6a1555d8d7b3124'
CONTENT_V1_FIXTURE_SHA256='750cecfd7d8cad5f2dc4c4e80cf0f0e2111a468641a7ccbf410a4c619db749e8'
ORIGINAL=None
CACHE={}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def verify_frozen(final=True):
    pins=tool._pins() if final else tool.PINNED_SOURCES
    for name,digest in pins.items():
        if sha((ROOT/name).read_bytes())!=digest:raise ValueError('frozen content dependency differs: '+name)
    if sha((ROOT/'tools/test_battle_profile_field_v3.py').read_bytes())!=FIELD_FIXTURE_SHA256:
        raise ValueError('frozen field fixture differs')
    if sha((ROOT/'tools/test_battle_profile_content.py').read_bytes())!=CONTENT_V1_FIXTURE_SHA256:
        raise ValueError('frozen authored body-setup fixture differs')
    parent_fixture.verify_frozen()
    if final:
        if LEASE_FIXTURE_SHA256 is None:raise ValueError('final lease fixture pin unavailable')
        if sha((ROOT/'tools/test_battle_profile_stack_lease_v2.py').read_bytes())!=LEASE_FIXTURE_SHA256:
            raise ValueError('frozen lease fixture differs')


@contextmanager
def issuer():
    raw=(ROOT/tool.SOURCE).read_bytes();name='_content_v2_synthetic_'+uuid.uuid4().hex
    module=ModuleType(name);module.__file__=str(ROOT/tool.SOURCE)
    module.__loaded_source_sha256__=sha(raw);module.__canonical_content_v2_issuer__=True
    assert sys.modules.setdefault(name,module) is module
    try:
        exec(compile(raw,module.__file__,'exec'),module.__dict__);yield module
    finally:
        assert sys.modules.get(name) is module;del sys.modules[name]


def arguments(model=False):
    return dict(lease_module=lease,lease_kwargs=parent_fixture.kwargs(),field_module=field,
        template_source=(ROOT/tool.TEMPLATE).read_bytes(),template_module=frozen,assembler_module=clip,
        model_dependency=(ROOT/tool.LEASE).read_bytes() if model else None)


def inventory_arguments(model=False):
    return {k:v for k,v in arguments(model).items() if k!='lease_kwargs'}


def emit(profile='classic',resolution='1024x768',fresh=False,model=False):
    key=profile,resolution,model
    if not fresh and key in CACHE:return CACHE[key]
    layout,life,route,parent,owned=parent_fixture.emit(profile,resolution,fresh=fresh)
    out=tool._emit_code(layout,life,route,parent,owned,**arguments(model))
    result=layout,life,route,parent,owned,out
    if not fresh:CACHE[key]=result
    return result


def decode(code,address_values):
    """Independent operand oracle; authored references, never numeric VA ranges."""
    cursor=0;rows=[]
    while cursor<len(code):
        start=cursor;absolute=[];relative=[];scalars=[];op=code[cursor];cursor+=1;memory=False
        def immediate(size=4,role='immediate'):
            nonlocal cursor
            assert cursor+size<=len(code),('short independent operand',start)
            value=int.from_bytes(code[cursor:cursor+size],'little')
            if role=='memory_address' or size==4 and role=='immediate' and value in address_values:
                absolute.append(cursor)
            else:scalars.append((cursor,size,role))
            cursor+=size
        if op in (0x9c,0x9d,0x60,0x61,0xfc,0xc3,0x55,0x5d,0x4b):pass
        elif op==0xf3:assert code[cursor]==0xaf;cursor+=1
        elif 0xb8<=op<=0xbf or op==0xa9:immediate()
        elif op in (0xe8,0xe9):relative.append(cursor);cursor+=4
        elif op==0x0f:
            sub=code[cursor];cursor+=1
            if sub==0x0b:pass
            elif 0x80<=sub<=0x8f:relative.append(cursor);cursor+=4
            else:assert sub in (0xb6,0xb7,0xbf);memory=True
        elif op==0x66:assert code[cursor]==0x8b;cursor+=1;memory=True
        else:
            assert op in (0x81,0x83,0x8b,0x89,0x3b,0x39,0x85,0xf7,0xff,0x31,0x29,0x01,0xc1,0x6b,0x8d,0xd1),(start,op)
            memory=True
        if memory:
            mod=code[cursor];cursor+=1;mode=mod>>6;rm=mod&7
            if mode!=3 and rm==4:
                sib=code[cursor];immediate(1,'sib')
                if mode==0 and sib&7==5:immediate(4,'memory_address')
            if mode==0 and rm==5:immediate(4,'memory_address')
            elif mode==1:immediate(1,'displacement')
            elif mode==2:immediate(4,'displacement')
            if op==0x81 or op==0xf7 and (mod>>3)&7==0:immediate()
            elif op in (0x83,0xc1,0x6b):immediate(1)
        assert start<cursor<=len(code),(start,cursor)
        rows.append((start,cursor,absolute,relative,scalars))
    return rows


def address_values(layout,parent,owned,out):
    modal=[r.va for r in layout.protected_spans if r.role=='parent:.hdstate']
    return ({out.base_va,owned.base_va,owned.base_va+len(owned.code),layout.rw.va,
        layout.rx.va,layout.rx.va+layout.rx.size,layout.rw.va+layout.rw.size,layout.rw.va+128,
        0x51d4c0,0x5202e0,0x511230,0x5199d8,0x526994,0x526990,0x532048,0x4ea4e8,0x512360} |
        {layout.rw.va+off for off in (16,20,36)} | {dict(parent.private_entries)['check_invocation']} |
        {pc for _,pc in owned.field_return_pcs+owned.lease_return_pcs} |
        {va+5 for va,*_ in frozen.SITES} | set(frozen.TILE_UNIT_RETURNS+frozen.ADJACENT_UNIT_RETURNS+frozen.VERTICAL_RETURNS) |
        {0x42f95b,0x4302dc} | {p+off for p in modal for off in (0,128,4096)})


def relocation_oracle(layout,parent,owned,out):
    decoded=decode(out.code,address_values(layout,parent,owned,out));starts={r[0] for r in decoded}
    declarations={r.offset:r for r in out.relocations};assert len(declarations)==len(out.relocations)
    absolute={off for row in decoded for off in row[2]};relative={off for row in decoded for off in row[3]}
    scalar={off for row in decoded for off,_,_ in row[4]}
    assert absolute=={r.offset for r in out.relocations if r.kind=='abs32'}
    assert relative=={r.offset for r in out.relocations if r.kind=='rel32'}
    assert not scalar & set(declarations)
    for row in decoded:
        for off in row[2]:assert struct.unpack_from('<I',out.code,off)[0]==declarations[off].target
        for off in row[3]:
            target=out.base_va+off+4+struct.unpack_from('<i',out.code,off)[0]
            assert target==declarations[off].target
            if declarations[off].purpose.startswith('content_v2_internal:'):assert target-out.base_va in starts
    private=dict(out.private_entries)
    for native,entry,payload,pc,denied,fault,valid in out.body_receipts:
        assert entry==dict(out.entries)[f'site_{native:06x}']
        assert all(va-out.base_va in starts for va in (entry,payload,pc,denied,fault,valid))
        call=next(row for row in decoded if out.base_va+row[1]==pc)
        assert out.code[call[0]]==0xe8 and call[3]==[call[0]+1]
        assert declarations[call[0]+1].target==private['admit_body']
        assert out.code[entry-out.base_va:entry-out.base_va+9]==bytes.fromhex('9c60fc81ec10030000')
        assert entry<pc<payload<valid<fault<denied<private['finish_rejected']
    assert private['finish_rejected']<private['finish_valid']<private['capture_inputs']
    assert tuple((mode,pc) for mode,pc,_,_ in lease._lease_receipts(owned,parent))==owned.lease_return_pcs
    return len(decoded),len(absolute),len(relative),len(scalar)


def observer_slices(args,kwargs,excluded,expected):
    """Preserve the documented hook ABI; unexpected observers fail closed."""
    names=('callback','user_data','begin','end','aux1','aux2')
    defaults=dict(user_data=None,begin=1,end=0,aux1=0,aux2=0)
    if len(args)>len(names) or set(kwargs)-set(names):raise ValueError('unexpected code observer arguments')
    if set(names[:len(args)])&set(kwargs):raise ValueError('duplicate code observer arguments')
    values=defaults|dict(zip(names,args))|kwargs
    if values.get('callback')!=expected:raise ValueError('unexpected parent code observer callback')
    if any(type(values[k]) is not int for k in ('begin','end','aux1','aux2')) or values['aux1'] or values['aux2']:
        raise ValueError('unexpected parent code observer range or auxiliary value')
    begin,end=values['begin'],values['end']
    if not 0<=begin<=0xffffffff or not 0<=end<=0xffffffff:raise ValueError('non-x86 parent observer range')
    # Unicorn documents begin > end as the all-address range. Other ranges
    # retain their exact inclusive bounds, including positional arguments.
    low,high=(0,0xffffffff) if begin>end else (begin,end)
    cursor=low;pieces=[]
    for left,right in sorted(excluded):
        if not 0<=left<=right<=0xffffffff:raise ValueError('invalid decoded exclusion')
        if right<cursor or left>high:continue
        if cursor<left:pieces.append((cursor,min(left-1,high)))
        cursor=max(cursor,right+1)
    if cursor<=high:pieces.append((cursor,high))
    return values,tuple(pieces)


class PrototypeSourceTests(unittest.TestCase):
    def setUp(self):verify_frozen(False)

    def test_whole_checked_ledger_frame_control_and_false_boundaries(self):
        _,ledger,scope=tool._versioned_template((ROOT/tool.TEMPLATE).read_bytes(),frozen)
        self.assertEqual(len(ledger),15);self.assertEqual(scope['HELPER_BYTES'],784)
        self.assertEqual(len(tool.CONTROL_SLOTS),67);self.assertIn(-4,tool.CONTROL_SLOTS)
        self.assertEqual(tool.CONTROL_SHADOW+4*len(tool.CONTROL_SLOTS),tool.MUTABLE_SHADOW)
        self.assertEqual(tool.MUTABLE_SHADOW+4*len(tool.MUTABLE_DESCRIPTOR_SLOTS),tool.THREAD_RESULT)
        self.assertLessEqual(tool.THREAD_RESULT+4,tool.HELPER_BYTES)
        self.assertEqual((tool.FIELD_BYTES,tool.LEASE_BYTES),(1280,192))
        self.assertIn('whole_chain_capacity_verified',tool.FALSE_CLAIMS)
        self.assertIn('native_provider_rle_verified',tool.FALSE_CLAIMS)
        self.assertTrue(any('unsafe_control' in new for _,new,_ in ledger))
        self.assertTrue(any('HELPER_BYTES+84' in new and '-44' in new for _,new,_ in ledger))
        self.assertTrue(any('protected_intervals' in new for _,new,_ in ledger))
        row_guard=next(new for old,new,_ in ledger if old=="    a.emit('39d0');a.branch('0f87','capture_stack.reject')")
        self.assertIn('enumerate(protected_intervals)',row_guard)
        self.assertIn("jump('capture_stack.reject')",row_guard)
        self.assertEqual(scope['SITES'],frozen.SITES)
        for raw in ((ROOT/tool.TEMPLATE).read_bytes()+b'\n',b''):
            with self.assertRaises(ValueError):tool._versioned_template(raw,frozen)

    def test_missing_production_pin_fails_without_original_or_alias_calls(self):
        captured=next(cell.cell_contents for cell in tool.emit_content_v2.__closure__ if callable(cell.cell_contents) and getattr(cell.cell_contents,'__name__','')=='_issue')
        self.assertIsNot(captured,tool._issue)
        self.assertTrue(captured.__globals__['__canonical_content_v2_issuer__'])
        with patch.dict(captured.__globals__,LEASE_V2_SHA256=None):
            with self.assertRaisesRegex(ValueError,'unavailable'):tool.emit_content_v2(b'','classic','1024x768')
        with patch.object(tool,'LEASE_V2_SHA256',None):
            with self.assertRaisesRegex(ValueError,'unavailable'):tool._snapshot()
        with patch.object(tool,'_issue',side_effect=AssertionError('public alias')):
            with self.assertRaises(ValueError):tool.emit_content_v2(b'','classic','1024x768')

    def test_structural_decoder_unknown_truncated_and_scalar_roles(self):
        code=bytes.fromhex('b8000040008b0425000040000fbf8401fe0500000fb7000fb6006bc028c1e101d1f8e9000000000f85000000000f0b')
        rows=tool._decode(code)
        self.assertEqual(rows[0][2],((1,4,'immediate'),))
        self.assertEqual(rows[1][2],((7,1,'sib'),(8,4,'memory_address')))
        for raw in (b'\x00',b'\x0f',b'\xe8\x01',b'\x8b\x04'):
            with self.assertRaises(ValueError):tool._decode(raw)
        independent=decode(code,{0x400000})
        self.assertEqual(len(rows),len(independent))
        self.assertEqual({at for _,_,fields in rows for at,_,role in fields if role=='relative'},
            {at for _,_,_,relative,_ in independent for at in relative})

    def test_namespace_occupied_roots_and_issuer_preserve_registry(self):
        token='e'*32;prefix='_battle_content_v2_'+token
        snapshot={name:(raw,stamp) for name in tool.PINNED_SOURCES for raw,stamp in (tool._read(ROOT/name),)}
        snapshot[tool.LEASE]=tool._read(ROOT/tool.LEASE)
        for name in (prefix,prefix+'.src',prefix+'.src.patcher',prefix+'.src.patcher.battle_profile_field_v3',
            '_battle_content_v2_issuer_'+token):
            before=dict(sys.modules);foreign=ModuleType(name);foreign.preserved=object();attrs=dict(foreign.__dict__)
            sys.modules[name]=foreign
            try:
                with patch.object(uuid,'uuid4',return_value=SimpleNamespace(hex=token)):
                    with self.assertRaisesRegex(ValueError,'occupied'):
                        if 'issuer_' in name:tool._production_factory()
                        else:
                            with tool._modules(snapshot):pass
                self.assertIs(sys.modules[name],foreign);self.assertEqual(foreign.__dict__,attrs)
                self.assertEqual(set(sys.modules),set(before)|{name})
                self.assertTrue(all(sys.modules[k] is v for k,v in before.items()))
            finally:del sys.modules[name]

    def test_code_observer_positional_keyword_callback_data_and_ranges_preserved(self):
        callback=lambda *args:None;data=object();excluded=((12,13),(18,19),(80,81))
        for args,kwargs in (((callback,data,10,20),{}),((callback,),dict(user_data=data,begin=10,end=20))):
            values,pieces=observer_slices(args,kwargs,excluded,callback)
            self.assertIs(values['callback'],callback);self.assertIs(values['user_data'],data)
            self.assertEqual((values['begin'],values['end']),(10,20))
            self.assertEqual(pieces,((10,11),(14,17),(20,20)))
        _,pieces=observer_slices((callback,data),{},excluded,callback)
        self.assertEqual(pieces,((0,11),(14,17),(20,79),(82,0xffffffff)))
        for args,kwargs in (((callback,data,10),dict(begin=10)),((object(),),{}),((callback,),dict(begin=-1)),
            ((callback,),dict(aux1=1)),((callback,),dict(unknown=0))):
            with self.assertRaises(ValueError):observer_slices(args,kwargs,excluded,callback)

    def test_explicit_synthetic_parent_reconstruction_and_operand_oracle(self):
        # Exact root-authorized model source only, no Original or bundle.
        for profile,resolution in (('classic','1024x768'),('modalwidgets','3840x2160')):
            layout,life,route,parent,owned,out=emit(profile,resolution,model=True)
            self.assertEqual(len(out.entries),28);self.assertEqual(len(dict(out.private_entries)),7)
            self.assertEqual(len(out.body_receipts),28)
            self.assertEqual(tuple(r[0] for r in out.body_receipts),tuple(row[0] for row in frozen.SITES))
            self.assertTrue(all(entry<pc<payload for _,entry,payload,pc,*_ in out.body_receipts))
            counts=relocation_oracle(layout,parent,owned,out);self.assertGreater(counts[2],1000)
            self.assertEqual(tool._parent_receipts(layout,parent,owned,field,lease)[3],owned.lease_field_receipts)
            scalar=next(r for r in tool._operand_inventory(out,layout,parent,owned,**inventory_arguments(True)) if r.kind=='scalar32' and r.role=='immediate')
            forged=clip.Relocation(scalar.offset,'abs32',scalar.value,'forged scalar')
            with self.assertRaises(ValueError):
                tool._operand_inventory(replace(out,relocations=out.relocations+(forged,)),layout,parent,owned,**inventory_arguments(True))
        if tool.LEASE_V2_SHA256 is not None:self.assertEqual(tool.LEASE_V2_SHA256,tool.MODEL_LEASE_SHA256)


class SourceTests(unittest.TestCase):
    def setUp(self):verify_frozen()

    def test_all36_complete_geometry_reconstruction_and_typed_operands(self):
        for profile in parent_fixture.context.PROFILES:
            for resolution in parent_fixture.context.RESOLUTIONS:
                layout,_,_,parent,owned,out=emit(profile,resolution)
                self.assertEqual(len(out.entries),28)
                self.assertEqual(out.base_va,(owned.base_va+len(owned.code)+15)&~15)
                self.assertLessEqual(out.base_va+len(out.code),layout.rx.va+layout.rx.size)
                relocation_oracle(layout,parent,owned,out)

    def test_parent_layout_operand_and_return_descriptor_rejections(self):
        layout,life,route,parent,owned,out=emit()
        for bad in (replace(owned,code=owned.code[:-1]),replace(owned,entries=owned.entries[:-1]),
            replace(owned,relocations=owned.relocations[:-1]),replace(owned,field_tile_receipts=owned.field_tile_receipts[:-1]),
            replace(owned,lease_field_receipts=owned.lease_field_receipts[::-1])):
            with self.assertRaises(ValueError):tool._emit_code(layout,life,route,parent,bad,**arguments())
        for bad in (replace(layout,rx=replace(layout.rx,size=131072)),replace(layout,rw=replace(layout.rw,size=4096)),
            replace(layout,battle_state_va=layout.rw.va+256),replace(layout,resolution='802x602')):
            with self.assertRaises(ValueError):tool._emit_code(bad,life,route,parent,owned,**arguments())
        for bad in (replace(out,relocations=out.relocations[:-1]),replace(out,relocations=out.relocations+(out.relocations[0],)),
            replace(out,private_entries=out.private_entries[:-1])):
            with self.assertRaises(ValueError):tool._operand_inventory(bad,layout,parent,owned,**inventory_arguments())
        operands=tool._operand_inventory(out,layout,parent,owned,**inventory_arguments())
        scalar=next(r for r in operands if r.kind=='scalar32' and r.role=='immediate')
        forged=clip.Relocation(scalar.offset,'abs32',scalar.value,'forged scalar')
        with self.assertRaises(ValueError):tool._operand_inventory(replace(out,relocations=out.relocations+(forged,)),layout,parent,owned,**inventory_arguments())

    def test_native_whole_operand_partial_register_and_old_byte_contract(self):
        # Authored byte arrays and an isolated copy of the pinned authenticator;
        # no Original image, production hash override or native execution.
        text=(ROOT/tool.TEMPLATE).read_text(encoding='utf-8');tree=ast.parse(text)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_authenticate_native')
        scope=dict(frozen.__dict__);exec(compile(ast.get_source_segment(text,node),'<authored-content-byte-fixture>','exec'),scope)
        raw=bytearray(0x120000)
        for va,value in frozen.PROLOGUES+tuple((row[0],row[1]) for row in frozen.SITES):
            data=bytes.fromhex(value);raw[va-0x400000:va-0x400000+len(data)]=data
        for pc,target in frozen.EXTRA_CALLS:raw[pc-0x400005:pc-0x400000]=b'\xe8'+struct.pack('<i',target-pc)
        for va in (0x513334,0x514500):raw[va-0x400000:va-0x400000+64]=struct.pack('<16i',*(v for pair in frozen.NEIGHBORS for v in pair))
        fixture=bytes(raw);mapper=SimpleNamespace(file_offset=lambda image,va,count:va-0x400000)
        scope['NATIVE_SPANS']={name:(lo,hi,sha(fixture[lo-0x400000:hi-0x400000])) for name,(lo,hi,_) in frozen.NATIVE_SPANS.items()}
        auth=scope['_authenticate_native'];rows=auth(fixture,fixture,mapper)
        self.assertEqual(len(rows),28);self.assertEqual({r['native_destination_bits'] for r in rows},{8,16,32})
        for va,value,*_ in frozen.SITES:
            for off in (0,len(bytes.fromhex(value))-1):
                changed=bytearray(fixture);changed[va-0x400000+off]^=1
                with self.assertRaises(ValueError):auth(fixture,bytes(changed),mapper)
        for name,(lo,hi,_) in scope['NATIVE_SPANS'].items():
            changed=bytearray(fixture);changed[hi-0x400001]^=1
            with self.assertRaisesRegex(ValueError,'span'):auth(fixture,bytes(changed),mapper)
        for pc,_ in frozen.EXTRA_CALLS:
            changed=bytearray(fixture);changed[pc-0x400001]^=1
            with self.assertRaises(ValueError):auth(fixture,bytes(changed),mapper)
        for va in (0x513334,0x514500):
            changed=bytearray(fixture);changed[va-0x400000+63]^=1
            with self.assertRaises(ValueError):auth(fixture,bytes(changed),mapper)

    def test_private_canonical_graph_alias_capture_and_changed_sources(self):
        with issuer() as own:
            snapshot=own._snapshot();read=Path.read_bytes
            with patch.dict(own.PINNED_SOURCES,{own.FIELD:'0'*64}):
                with self.assertRaises(ValueError):own._snapshot()
            with patch.object(Path,'read_bytes',lambda path:read(path)[:-1] if path==ROOT/tool.SOURCE else read(path)):
                with self.assertRaises(ValueError):own._unchanged(snapshot)
            def poison(*args,**kwargs):raise AssertionError('public alias invoked')
            with patch.object(tool,'_raw_emit',poison),patch.object(lease,'_emit_code',poison),patch.object(field,'_emit_code',poison),patch.object(clip,'_Assembler',poison):
                with own._modules(snapshot) as modules:
                    for name in (own.LEASE,own.FIELD,own.TEMPLATE,own.CLIP):
                        self.assertEqual(modules[name].__loaded_source_sha256__,own._pins()[name])
                        self.assertNotEqual(getattr(modules[name],'_emit_code',None),poison)
        tree=ast.parse((ROOT/tool.SOURCE).read_text(encoding='utf-8'))
        metadata=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='dict' and
            any(k.arg=='schema' and isinstance(k.value,ast.Constant) and k.value.value=='clash95_battle_profile_content_v2' for k in n.keywords))
        vals={k.arg:k.value for k in metadata.keywords if k.arg}
        self.assertEqual(ast.literal_eval(vals['provider_records_emitted']),0)
        self.assertEqual(ast.literal_eval(vals['installed_hooks']),[])
        self.assertIn('downstream_frozen_continuation_compatible',tool.FALSE_CLAIMS)


class Machine(parent_fixture.Machine):
    # Frozen authored body setup; actual parent code is exclusively fresh.
    setup_body=old_fixture.Machine.setup_body
    maximum_content_stack_bytes=0
    content_stack_observations=0

    def __init__(self,tools,profile='classic',resolution='1024x768',delta=0):
        self.content_active=False;self.content_reads=[];self.content_writes=[]
        self.content_events=[];self.content_after_thread=False
        hooks=[];deleted=set();original_hook=tools[0].Uc.hook_add;original_delete=tools[0].Uc.hook_del
        def capture(cpu,kind,*args,**kwargs):
            handle=original_hook(cpu,kind,*args,**kwargs);hooks.append((kind,handle,args,kwargs));return handle
        def remove(cpu,handle):
            deleted.add(handle);return original_delete(cpu,handle)
        with patch.object(tools[0].Uc,'hook_add',capture),patch.object(tools[0].Uc,'hook_del',remove):
            super().__init__(tools,profile,resolution,delta)
        self.plan=None
        self.content_emission=emit(profile,resolution)[5]
        self.content_entries={name:va+delta for name,va in self.content_emission.entries}
        raw=bytearray(self.content_emission.code)
        for row in self.content_emission.relocations:
            if row.kind=='abs32':struct.pack_into('<I',raw,row.offset,row.target+delta)
        self.cpu.mem_write(self.content_emission.base_va+delta,bytes(raw))
        self.loaded_code.append((self.content_emission.base_va+delta,bytes(raw)))
        self.current_cell=None;self.unsafe=False
        excluded=[]
        for start,end,_ in tool._decode(self.content_emission.code):
            if self.content_emission.code[start]!=0xf3:continue
            assert self.content_emission.code[start+1]==0xaf
            assert self.content_emission.code[start-10]==0xb9 and self.content_emission.code[start-5]==0xbf
            count=struct.unpack_from('<I',self.content_emission.code,start-9)[0]
            pointer=struct.unpack_from('<I',self.content_emission.code,start-4)[0]+delta
            va=self.content_emission.base_va+delta+start
            self.scan_before[va-5]=(va+2,pointer,count);self.scan_after[va+2]=(pointer,count)
            excluded.append((va,va+1))
        # Preserve parent observer ranges; suppress only repeated code-hook
        # dispatch over exact REP bytes. Every read retains the strict latch.
        replacements=[]
        for kind,handle,args,kwargs in hooks:
            if kind!=self.u.UC_HOOK_CODE or handle in deleted:continue
            values,pieces=observer_slices(args,kwargs,excluded,self.on_code)
            replacements.append((handle,values,pieces))
        self.content_hook_receipts=[]
        for handle,values,pieces in replacements:
            self.cpu.hook_del(handle)
            for low,high in pieces:
                self.cpu.hook_add(self.u.UC_HOOK_CODE,values['callback'],values['user_data'],low,high,values['aux1'],values['aux2'])
            self.content_hook_receipts.append((values,pieces))
        assert replacements and all(any(low<=pc<=high for _,pieces in self.content_hook_receipts for low,high in pieces)
            for pc in tuple(self.scan_before)+tuple(self.scan_after))

    def begin(self,mode=0,*,eax=0,edx=0,flags=0xed7):
        result=super().begin(mode,eax=eax,edx=edx,flags=flags);self.current_cell=(eax,edx);return result

    def on_code(self,cpu,address,size,data):
        if self.content_active:self.minimum_sp=min(self.minimum_sp,cpu.reg_read(self.regs['ESP']))
        if hasattr(self,'content_entries') and address==dict(self.content_emission.private_entries)['unsafe_control']+self.delta:
            self.unsafe=True;cpu.emu_stop();return
        super().on_code(cpu,address,size,data)

    def on_read(self,cpu,access,address,size,value,data):
        # This independent log precedes parent filtering of pixel reads. The
        # separate strict SCAS observers still see every protected-tail DWORD.
        if self.content_active and self.active_scan is None:
            self.content_reads.append((address,size))
            self.content_events.append(('read',cpu.reg_read(self.regs['EIP']),address,size,self.content_after_thread))
        super().on_read(cpu,access,address,size,value,data)

    def on_write(self,cpu,access,address,size,value,data):
        if self.content_active:self.content_writes.append((address,size))
        super().on_write(cpu,access,address,size,value,data)

    def callback(self,name):
        if self.content_active:
            self.content_events.append(('callback',name,self.cpu.reg_read(self.regs['EIP']),len(self.content_reads)))
            if name=='thread':self.content_after_thread=True
        super().callback(name)

    def observed_reads(self,post_thread=False):
        if not post_thread:return self.content_reads
        return [(row[2],row[3]) for row in self.content_events if row[0]=='read' and row[4]]

    def payload_reads(self,post_thread=False):
        ranges=((self.WORLD,self.WORLD+800),(self.WORLD+852,self.WORLD+0xf7c))
        return [(at,size) for at,size in self.observed_reads(post_thread) if any(at<hi and at+size>lo for lo,hi in ranges)]

    def cached_reads(self,post_thread=False):
        ranges=((self.PHYSICAL,self.PHYSICAL+188),(self.PRIVATE,self.PRIVATE+188),
            (self.BACKEND,self.BACKEND+168),(self.WORLD,self.WORLD+0xf7c))
        return [(at,size) for at,size in self.observed_reads(post_thread) if any(at<hi and at+size>lo for lo,hi in ranges)]

    def protect_cached(self,protection):
        for page in sorted({at&~4095 for at in (self.PHYSICAL,self.PRIVATE,self.BACKEND,self.WORLD)}):
            self.cpu.mem_protect(page,4096,protection)

    def invoke_prepared(self,row,regs,call_pc=None):
        va,raw,*_=row;site=va+self.delta;target=self.content_entries[f'site_{va:06x}']
        if call_pc is not None:site=call_pc-5
        stop=site+5;self.cpu.mem_write(site,b'\xe8'+struct.pack('<i',target-site-5)+b'\x90'*(len(bytes.fromhex(raw))-5))
        self.stops={stop};self.native_stop=None;self.unsafe=False;self.reads=[];self.writes=[]
        self.active_scan=None;self.minimum_sp=regs['ESP'];self.before_callbacks=len(self.callbacks)
        self.content_reads=[];self.content_writes=[];self.content_active=True
        self.content_events=[];self.content_after_thread=False
        for name,value in regs.items():self.cpu.reg_write(self.regs[name],value&0xffffffff)
        flags=0xed7;self.cpu.reg_write(self.regs['EFLAGS'],flags)
        try:self.cpu.emu_start(site,self.STOP+1,count=2000000)
        finally:self.content_active=False
        actual={name:self.cpu.reg_read(reg) for name,reg in self.regs.items()}
        measured=regs['ESP']-self.minimum_sp
        type(self).maximum_content_stack_bytes=max(type(self).maximum_content_stack_bytes,measured)
        type(self).content_stack_observations+=1
        if not self.unsafe:
            assert self.native_stop==stop,(row,actual)
            assert actual['ESP']==regs['ESP']
            for name,value in regs.items():
                if name not in ('EAX','EDX','ESP'):assert actual[name]==value&0xffffffff,(row,name)
            assert actual['EFLAGS']&self.MASK==flags&self.MASK
            assert regs['ESP']-self.minimum_sp<=tool.HELPER_BYTES+84
        helper=regs['ESP']-4-36-tool.HELPER_BYTES
        for at,size in self.content_writes:
            assert helper-44<=at and at+size<=helper+tool.HELPER_BYTES+40,(hex(at),size,hex(helper))
        for va,expected in self.loaded_code:assert bytes(self.cpu.mem_read(va,len(expected)))==expected
        return actual,regs


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        verify_frozen()
        cls.tools=parent_fixture.field_fixture.routing_fixture.lifetime.prior_fixture.machine_tools()
        if cls.tools is None:raise RuntimeError('required Unicorn model tools unavailable')

    def test_all36_two_bases_28_body_sites_value_status_flags_and_stack(self):
        for profile in parent_fixture.context.PROFILES:
            for resolution in parent_fixture.context.RESOLUTIONS:
                for delta in (0,0x30000):
                    for mode in (0,1):
                        m=Machine(self.tools,profile,resolution,delta).prepare(columns=2).begin(mode)
                        for row in frozen.SITES:
                            regs=m.setup_body(row,index=21);expected=34
                            if row[3]=='occupant':
                                nx,ny=row[4:];outside=not(0<=nx<2 and 0<=ny<7)
                                if not outside:m.cpu.mem_write(m.WORLD+1534+40*nx+2*ny,struct.pack('<h',21))
                                expected=0xffffffff if outside else 21
                            elif row[3]=='owner':m.cpu.mem_write(m.WORLD+854+31*21,b'\xff');expected=255
                            elif row[3]=='coordinate':
                                expected=1 if row[4]==4 else 6;m.cpu.mem_write(m.WORLD+852+31*21+row[4],struct.pack('<H',expected))
                            else:m.cpu.mem_write(m.WORLD+852+31*21,struct.pack('<h',34))
                            actual,_=m.invoke_prepared(row,regs)
                            self.assertFalse(m.unsafe);self.assertEqual((actual['EAX'],actual['EDX']),(expected,1),(profile,resolution,mode,row))
                            self.assertEqual(m.callbacks[m.before_callbacks:],['thread'])
                            if row[3]=='occupant' and expected==0xffffffff:self.assertEqual(m.payload_reads(),[])
                        m.complete()

    def test_thread_receipt_pointer_tail_and_paired_descriptor_losses_before_cached_reads(self):
        for profile in parent_fixture.context.PROFILES:
            m=Machine(self.tools,profile).prepare(columns=2).begin();row=frozen.SITES[0]
            addresses=[m.state_va+at for at in range(0,128,4)]
            if m.modal_va is not None:addresses += [m.modal_va+at for at in range(0,128,4)]+[m.modal_va+128,m.modal_va+4092]
            addresses += [m.state_va+128,m.state_va+65532]
            addresses += [m.field_frame+at for at in (1104,1112,1120,1124,1132,1136,1140,1144,1156,1160,1164,1168)]
            addresses += [m.lease_frame+at for at in range(0,192,4)]
            addresses += [0x51d4c0+m.delta+at for at in range(0,216,4)]
            addresses += [pointer+m.delta for pointer in (0x5202e0,0x511230,0x5199d8,0x526994,0x526990,0x532048,frozen.THREAD_IAT)]
            for at in addresses:
                regs=m.setup_body(row);original=m.word(at);fired=[]
                def mutate(machine,label):
                    if label=='thread':
                        fired.append(label);machine.put(at,machine.word(at)^1)
                        machine.protect_cached(machine.u.UC_PROT_NONE)
                try:
                    m.mutation=mutate;actual,before=m.invoke_prepared(row,regs)
                    self.assertEqual(fired,['thread']);self.assertEqual(m.callbacks[m.before_callbacks:],['thread'])
                    self.assertFalse(m.unsafe);self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX'],0))
                    self.assertEqual(m.cached_reads(post_thread=True),[]);self.assertEqual(m.payload_reads(post_thread=True),[])
                finally:
                    m.mutation=None;m.put(at,original);m.protect_cached(m.u.UC_PROT_ALL)
            for off in range(0,192,4):
                regs=m.setup_body(row);actual_at=m.lease_frame+off;original=m.word(actual_at);fired=[]
                def paired(machine,label):
                    if label=='thread':
                        fired.append(label)
                        helper=regs['ESP']-4-36-tool.HELPER_BYTES
                        value=machine.word(actual_at)^1;machine.put(actual_at,value);machine.put(helper+off,value)
                        machine.protect_cached(machine.u.UC_PROT_NONE)
                try:
                    m.mutation=paired;actual,before=m.invoke_prepared(row,regs)
                    self.assertEqual(fired,['thread']);self.assertFalse(m.unsafe)
                    self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX'],0))
                    self.assertEqual(m.cached_reads(post_thread=True),[]);self.assertEqual(m.payload_reads(post_thread=True),[])
                finally:
                    m.mutation=None;m.put(actual_at,original);m.protect_cached(m.u.UC_PROT_ALL)

    def test_helper_control_private_return_and_input_copy_losses_use_unsafe_closure(self):
        m=Machine(self.tools,'modalwidgets').prepare(columns=2).begin();row=frozen.SITES[0]
        for slot in tool.CONTROL_SLOTS:
            regs=m.setup_body(row);seen=[]
            def mutate(machine,label):
                if label=='thread':
                    helper=regs['ESP']-4-36-tool.HELPER_BYTES;at=helper+slot
                    seen.append(at);machine.put(at,machine.word(at)^1)
                    machine.protect_cached(machine.u.UC_PROT_NONE)
            try:
                m.mutation=mutate;actual,_=m.invoke_prepared(row,regs)
                self.assertEqual(len(seen),1);self.assertTrue(m.unsafe,slot);self.assertEqual(m.payload_reads(post_thread=True),[])
                self.assertEqual(m.cached_reads(post_thread=True),[]);self.assertEqual(m.callbacks[m.before_callbacks:],['thread'])
            finally:m.mutation=None;m.protect_cached(m.u.UC_PROT_ALL)

    def test_small_arena_edges_payload_bounds_type_owner_coordinate_and_empty_values(self):
        for profile in ('classic','modalwidgets'):
            for columns in (1,3,20):
                m=Machine(self.tools,profile).prepare(columns=columns).begin()
                for row in frozen.SITES:
                    if row[3]!='occupant':continue
                    for x,y in ((0,0),(columns-1,6)):
                        regs=m.setup_body(row,x=x,y=y);nx,ny=m.neighbor
                        outside=not(0<=nx<columns and 0<=ny<7)
                        if not outside:m.cpu.mem_write(m.WORLD+1534+40*nx+2*ny,b'\xff\xff')
                        actual,_=m.invoke_prepared(row,regs)
                        self.assertEqual((actual['EAX'],actual['EDX']),(0xffffffff,1),(columns,row,x,y))
                        if outside:self.assertEqual(m.payload_reads(),[])
                    regs=m.setup_body(row);nx,ny=m.neighbor
                    if 0<=nx<columns and 0<=ny<7:
                        for malformed in (-2,22,32767):
                            m.cpu.mem_write(m.WORLD+1534+40*nx+2*ny,struct.pack('<h',malformed))
                            actual,before=m.invoke_prepared(row,regs)
                            self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX'],2))
                            self.assertEqual(m.payload_reads(),[(m.WORLD+1534+40*nx+2*ny,2)])
            m=Machine(self.tools,profile).prepare(columns=2).begin()
            for row in frozen.SITES:
                op=row[3]
                if op=='occupant':continue
                for index in (-1,22,0x10000000):
                    regs=m.setup_body(row,index=index);actual,before=m.invoke_prepared(row,regs)
                    self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX']&0xffffffff,2),row)
                    self.assertEqual(m.payload_reads(),[])
                regs=m.setup_body(row)
                if op in ('type','unit_type'):
                    for value in (-2,-1,35,32767):
                        m.cpu.mem_write(m.WORLD+852,struct.pack('<h',value));actual,before=m.invoke_prepared(row,regs)
                        expected=(0xffffffff,1) if op=='unit_type' and value==-1 else (before['EAX'],2)
                        self.assertEqual((actual['EAX'],actual['EDX']),expected)
                elif op=='coordinate':
                    for value in (2 if row[4]==4 else 7,65535):
                        m.cpu.mem_write(m.WORLD+852+row[4],struct.pack('<H',value));actual,before=m.invoke_prepared(row,regs)
                        self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX'],2))
                else:
                    for value in (0,127,255):
                        m.cpu.mem_write(m.WORLD+854,bytes([value]));actual,_=m.invoke_prepared(row,regs)
                        self.assertEqual((actual['EAX'],actual['EDX']),(value,1))

    def test_native_ancestry_count_draw_only_stack_canaries_and_thread_admission(self):
        for delta in (0,0x30000):
            m=Machine(self.tools,'modalwidgets',delta=delta).prepare(columns=2).begin()
            for family in frozen.FAMILIES:
                row=next(r for r in frozen.SITES if r[2]==family)
                for fault in ('native_pc','live_ebp','tile_return','tile_saved','thread'):
                    regs=m.setup_body(row,via_adjacent=family in ('unit','count'))
                    low=regs['ESP']-4-36-tool.HELPER_BYTES-44-16
                    m.cpu.mem_write(low,b'\xa9'*16);original=None;fired=[]
                    if fault=='live_ebp':regs['EBP']+=4
                    elif fault=='tile_return':
                        at=m.tile_sp;original=m.word(at);m.put(at,0x430000+delta)
                    elif fault=='tile_saved':
                        at=m.tile_sp-20;original=m.word(at);m.put(at,m.field_frame+4)
                    elif fault=='thread':
                        def change(machine,label):
                            if label=='thread':fired.append(label);machine.thread_id+=1
                        m.mutation=change
                    try:
                        actual,before=m.invoke_prepared(row,regs,call_pc=row[0]+delta+0x10005 if fault=='native_pc' else None)
                        self.assertFalse(m.unsafe);self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX'],0),(family,fault))
                        self.assertEqual(m.payload_reads(),[]);self.assertEqual(m.cached_reads(post_thread=True),[])
                        self.assertEqual(m.callbacks[m.before_callbacks:],['thread'] if fault=='thread' else [])
                        self.assertEqual(bytes(m.cpu.mem_read(low,16)),b'\xa9'*16)
                    finally:
                        m.mutation=None
                        if original is not None:m.put(at,original)
                        if fired:m.thread_id-=1
                if family=='count':
                    for pc in (0x426f95,0x431d7a):
                        regs=m.setup_body(row,via_adjacent=True);m.put(m.native_s,pc+delta)
                        actual,before=m.invoke_prepared(row,regs)
                        self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX'],0))
                        self.assertEqual(m.payload_reads(),[]);self.assertEqual(m.callbacks[m.before_callbacks:],[])
            # Isolated private-row entry tests its dynamic interval guard. No
            # direct native entry or ancestor capacity is established here.
            helper=m.STACK+0x6000;capture=dict(m.content_emission.private_entries)['capture_stack']+delta
            spans=((m.layout.rx.va+delta,m.layout.rx.size),(m.state_va,m.layout.rw.size))
            if m.modal_va is not None:spans+=((m.modal_va+delta,4096),)
            for low,size in spans:
                for pointer,count in ((low,4),(low+size-4,4),(low-4,8),(low+size-4,8)):
                    m.cpu.mem_write(helper,bytes(tool.HELPER_BYTES));m.put(helper+228,pointer+0x100)
                    m.put(helper-4,m.STOP);m.cpu.reg_write(m.regs['EBP'],helper)
                    m.cpu.reg_write(m.regs['ESP'],helper-4);m.cpu.reg_write(m.regs['EDI'],pointer)
                    m.cpu.reg_write(m.regs['EBX'],count);m.stops={m.STOP};m.native_stop=None
                    m.content_events=[];m.content_reads=[];m.content_writes=[];m.content_active=True
                    page=min(max(pointer,low),low+size-1)&~4095;m.cpu.mem_protect(page,4096,m.u.UC_PROT_NONE)
                    try:
                        m.cpu.emu_start(capture,m.STOP+1,count=10000)
                        self.assertEqual(m.native_stop,m.STOP)
                        self.assertEqual(m.cpu.reg_read(m.regs['EAX']),0)
                        self.assertEqual(m.cpu.reg_read(m.regs['ESP']),helper)
                        self.assertEqual(m.word(helper+368),0)
                        self.assertFalse(any(at<pointer+count and at+n>pointer for at,n in m.content_reads))
                    finally:m.content_active=False;m.cpu.mem_protect(page,4096,m.u.UC_PROT_ALL)

    def test_dynamic_header_losses_and_outside_payload_and_tail_observers_remain_visible(self):
        m=Machine(self.tools,'modalwidgets').prepare(columns=2).begin();row=frozen.SITES[0]
        points=[base+off for base,count in ((m.PHYSICAL,188),(m.PRIVATE,188),(m.BACKEND,168)) for off in range(0,count,4)]
        points += [m.WORLD+off for off in (800,804,808,812)]
        for at in points:
            regs=m.setup_body(row);original=m.word(at);fired=[]
            def mutate(machine,label):
                if label=='thread':fired.append(label);machine.put(at,machine.word(at)^1)
            try:
                m.mutation=mutate;actual,before=m.invoke_prepared(row,regs)
                self.assertEqual(fired,['thread']);self.assertFalse(m.unsafe)
                self.assertEqual((actual['EAX'],actual['EDX']),(before['EAX'],0))
                self.assertEqual(m.payload_reads(),[])
            finally:m.mutation=None;m.put(at,original)
        # Exact machine-load gadgets show neither tail nor outside-payload
        # observers disappear through inherited filtering or scan exclusions.
        for low,_ in m.tail_ranges:
            pc=0x450000;raw=b'\x8b\x05'+struct.pack('<I',low)+b'\xc3';m.cpu.mem_write(pc,raw)
            m.active_scan=None;m.put(m.SP,m.STOP);m.cpu.reg_write(m.regs['ESP'],m.SP)
            with self.assertRaisesRegex(AssertionError,'tail read outside decoded scan'):
                m.cpu.emu_start(pc,pc+len(raw),count=5)
        pc=0x450000;raw=b'\x8b\x05'+struct.pack('<I',m.WORLD+852)+b'\xc3';m.cpu.mem_write(pc,raw)
        m.content_reads=[];m.content_active=True;m.put(m.SP,m.STOP);m.cpu.reg_write(m.regs['ESP'],m.SP)
        try:m.cpu.emu_start(pc,pc+len(raw)-1,count=1)
        finally:m.content_active=False
        self.assertEqual(m.payload_reads(),[(m.WORLD+852,4)])

    def test_independent_machine_instruction_lengths_and_terminal_unsafe_endpoint(self):
        u,r=self.tools
        def lengths(raw,base):
            cpu=u.Uc(u.UC_ARCH_X86,u.UC_MODE_32)
            cpu.mem_map(base&~4095,(len(raw)+8191)&~4095);cpu.mem_write(base,raw)
            ordinary=[];traps=[]
            def step(machine,address,size,data):
                offset=address-base
                self.assertTrue(0<=offset<len(raw))
                if raw[offset:offset+2]==b'\x0f\x0b':
                    self.assertEqual(offset,len(raw)-2);return
                self.assertTrue(1<=size<=15 and offset+size<=len(raw),(offset,size))
                ordinary.append((offset,size));machine.reg_write(r.UC_X86_REG_EIP,address+size)
            def trap(machine,data):
                offset=machine.reg_read(r.UC_X86_REG_EIP)-base
                self.assertEqual(offset,len(raw)-2)
                self.assertEqual(bytes(machine.mem_read(base+offset,2)),b'\x0f\x0b')
                traps.append((offset,2));machine.emu_stop();return True
            cpu.hook_add(u.UC_HOOK_CODE,step);cpu.hook_add(u.UC_HOOK_INSN_INVALID,trap)
            cpu.emu_start(base,base+len(raw),count=len(raw))
            self.assertEqual(traps,[(len(raw)-2,2)])
            self.assertEqual(cpu.reg_read(r.UC_X86_REG_EIP),base+len(raw)-2)
            return ordinary+traps
        for bad in (b'\x0f\xff',b'\x0f\x0b\xb8\x01\x00\x00\x00'):
            with self.assertRaises((AssertionError,u.UcError)):lengths(bad,0x100000)
        for profile in parent_fixture.context.PROFILES:
            layout,_,_,parent,owned,out=emit(profile,'3840x2160')
            expected=[(lo,hi-lo) for lo,hi,*_ in decode(out.code,address_values(layout,parent,owned,out))]
            self.assertEqual(out.code[-2:],b'\x0f\x0b')
            for delta in (0,0x30000):
                raw=bytearray(out.code)
                for item in out.relocations:
                    if item.kind=='abs32':struct.pack_into('<I',raw,item.offset,item.target+delta)
                observed=lengths(bytes(raw),out.base_va+delta)
                self.assertEqual(observed,expected);self.assertEqual(sum(n for _,n in observed),len(raw))


class OriginalTests(unittest.TestCase):
    def test_optional_original_native_operands_relayout_and_source_capture_in_ram(self):
        verify_frozen()
        if ORIGINAL is None:raise ValueError('explicit --original-backed path required for the optional RAM lane')
        before=ORIGINAL.read_bytes();self.assertEqual(sha(before),tool.BASE_SHA256)
        result=tool.emit_content_v2(before,'modalwidgets','1920x1080')
        field_bundle=result.lease_bundle.field_bundle
        layout=field_bundle.routing_bundle.lifecycle_bundle.allocation_context.layout
        relocation_oracle(layout,field_bundle.emission,result.lease_bundle.emission,result.emission)
        metadata=result.metadata();self.assertEqual(len(metadata['native_operands']),28)
        self.assertEqual(tuple(row['va'] for row in metadata['native_operands']),tuple(row[0] for row in frozen.SITES))
        self.assertEqual({row['native_destination_bits'] for row in metadata['native_operands']},{8,16,32})
        self.assertEqual(result.hook_sites,());self.assertEqual(result.removed_highlow_rvas,())
        for name in tool.FALSE_CLAIMS:self.assertIs(metadata[name],False,name)
        def poison(*args,**kwargs):raise AssertionError('public producer alias called')
        with patch.object(tool,'_issue',poison),patch.object(lease,'_emit_code',poison),patch.object(field,'_emit_code',poison):
            repeated=tool.emit_content_v2(before,'modalwidgets','1920x1080')
        # The private parent graph gives each reconstruction distinct relocation
        # dataclass types. Compare every authored field, including complete
        # relocation records and body receipts, without class-identity equality.
        def emission_record(out):
            self.assertEqual(tuple(out.__dataclass_fields__),('base_va','state_va','code','entries',
                'relocations','width','height','private_entries','body_receipts'))
            self.assertTrue(all(tuple(r.__dataclass_fields__)==('offset','kind','target','purpose')
                for r in out.relocations))
            return (out.base_va,out.state_va,out.code,out.entries,
                tuple((r.offset,r.kind,r.target,r.purpose) for r in out.relocations),
                out.width,out.height,out.private_entries,out.body_receipts)
        self.assertEqual(emission_record(repeated.emission),emission_record(result.emission))
        self.assertEqual(repeated.metadata_json,result.metadata_json)
        self.assertEqual(ORIGINAL.read_bytes(),before)
        verify_frozen()


class TimedResult(unittest.TextTestResult):
    def startTest(self,test):
        self.started=time.perf_counter();super().startTest(test)

    def stopTest(self,test):
        elapsed=time.perf_counter()-self.started
        super().stopTest(test);self.stream.writeln(f'method_elapsed {test.id()} {elapsed:.3f}s')


def source_closure():
    names=set(tool._pins())|{tool.SOURCE,'tools/test_battle_profile_content_v2.py',
        'tools/test_battle_profile_field_v3.py','tools/test_battle_profile_stack_lease_v2.py',
        'tools/test_battle_profile_content.py'}|set(parent_fixture.FIXTURE_PINS)
    return {name:sha((ROOT/name).read_bytes()) for name in sorted(names)}


def main(argv=None):
    global ORIGINAL
    parser=argparse.ArgumentParser();parser.add_argument('--prototype',action='store_true')
    parser.add_argument('--original-backed',type=Path)
    args,rest=parser.parse_known_args(argv)
    if args.prototype and args.original_backed:parser.error('the Original RAM lane requires final dependency pins')
    ORIGINAL=args.original_backed
    if not args.prototype:
        try:
            verify_frozen()
            if parent_fixture.field_fixture.routing_fixture.lifetime.prior_fixture.machine_tools() is None:
                raise ImportError('required Unicorn model tools unavailable')
        except (ValueError,ImportError) as error:print(str(error),file=sys.stderr);return 2
    names=rest or (['PrototypeSourceTests'] if args.prototype else ['PrototypeSourceTests','SourceTests','CPUTests']+
        (['OriginalTests'] if ORIGINAL is not None else []))
    before=None if args.prototype else source_closure()
    if before is not None:print('source_closure_before '+json.dumps(before,sort_keys=True),flush=True)
    result=unittest.TextTestRunner(verbosity=2,resultclass=TimedResult).run(unittest.defaultTestLoader.loadTestsFromNames(names,sys.modules[__name__]))
    if before is not None:
        after=source_closure();print('source_closure_after '+json.dumps(after,sort_keys=True),flush=True)
        if before!=after:raise ValueError('Content source closure changed during fixture run')
    print('content_model_stack '+json.dumps(dict(observations=Machine.content_stack_observations,
        maximum_native_site_sp_to_low_point_bytes=Machine.maximum_content_stack_bytes,
        checked_helper_interval_bytes=tool.HELPER_BYTES+84,native_stack_capacity_verified=False,
        whole_chain_capacity_verified=False,runtime_verified=False)),flush=True)
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__=='__main__':raise SystemExit(main())
