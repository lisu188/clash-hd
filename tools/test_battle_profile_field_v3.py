#!/usr/bin/env python3
"""Fresh field source/Unicorn models; no native game or output artifacts.

Original reconstruction is separately opt-in and RAM-only. Native Tile below
paints an independent pattern, never authentic native sprites or providers.
"""
from __future__ import annotations
import argparse
import ast
from contextlib import contextmanager
from dataclasses import asdict, replace
import gc
import hashlib
from pathlib import Path
import struct
import sys
import time
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"tools")]
from src.patcher import battle_profile_field_v3 as tool
from src.patcher import battle_profile_field_v2 as frozen
from src.patcher import battle_profile_routing_v2 as route
from src.patcher import battle_profile_routing as oldroute
from src.patcher import battle_profile_lifecycle_v2 as life
from src.patcher import battle_profile_lifecycle as oldlife
from src.patcher import battle_profile_context_v2 as context
from src.patcher import partial_tile_clip as clip
from src.patcher import framed_modal_canvas as native
import test_battle_profile_routing_v2 as routing_fixture
import test_battle_profile_field as pixel_oracle
ORIGINAL=None
CACHE={}
ENTRIES=("visible_columns","clamp_scroll_x","screen_to_cell","visible_cell","draw_full","draw_incremental")
PRIVATE=("capture_invocation","check_invocation","same_invocation")

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

@contextmanager
def issuer():
    raw=(ROOT/tool.SOURCE).read_bytes(); name="_field_v3_synthetic_"+uuid.uuid4().hex
    module=ModuleType(name); module.__file__=str(ROOT/tool.SOURCE)
    module.__loaded_source_sha256__=sha(raw); module.__canonical_field_v3_issuer__=True
    assert sys.modules.setdefault(name,module) is module
    try:
        exec(compile(raw,module.__file__,"exec"),module.__dict__)
        yield module
    finally:
        assert sys.modules.get(name) is module
        del sys.modules[name]

def kwargs():
    return dict(template_source=(ROOT/tool.TEMPLATE).read_bytes(),template_module=frozen,
        routing_module=route,routing_template_source=(ROOT/tool.ROUTE_TEMPLATE).read_bytes(),
        routing_template_module=oldroute,lifecycle_module=life,
        lifecycle_template_source=(ROOT/tool.LIFE_TEMPLATE).read_bytes(),
        lifecycle_template_module=oldlife,assembler_module=clip)

def emit(profile="classic",resolution="1024x768",fresh=False):
    key=(profile,resolution)
    if not fresh and key in CACHE: return CACHE[key]
    layout,parent,routing=routing_fixture.emit(profile,resolution)
    out=tool._emit_code(layout,parent,routing,**kwargs())
    result=layout,parent,routing,out
    if not fresh: CACHE[key]=result
    return result

def decode(code):
    """Independent field instruction boundaries, independent operand roles."""
    rows=[]; cursor=0
    while cursor<len(code):
        start=cursor; absolute=[]; relative=[]; scalars=[]
        opcode=code[cursor]; cursor+=1
        if opcode in (0x9c,0x9d,0x60,0x61,0xfc,0xc3,0x40): pass
        elif opcode==0xf3:
            assert code[cursor]==0xaf; cursor+=1
        elif 0xb8<=opcode<=0xbf:
            absolute.append((cursor,False)) if opcode==0xbf else scalars.append((cursor,4,"immediate"))
            cursor+=4
        elif opcode in (0xe8,0xe9): relative.append(cursor); cursor+=4
        elif opcode==0x0f:
            assert code[cursor] in (0x82,0x83,0x84,0x85,0x86,0x88,0x89,0x8c,0x8d)
            cursor+=1; relative.append(cursor); cursor+=4
        elif opcode in (0x81,0x83,0x8b,0x89,0x3b,0x39,0x85,0x31,0x29,0x01,0x03,0x09,0xc1):
            modrm=code[cursor]; cursor+=1; mode,rm=modrm>>6,modrm&7
            # This authored field dialect has no SIB or disp8 addressing.
            assert mode==3 or rm!=4
            if mode==0 and rm==5: absolute.append((cursor,True)); cursor+=4
            elif mode==2: scalars.append((cursor,4,"displacement")); cursor+=4
            else: assert mode in (0,3)
            if opcode==0x81: scalars.append((cursor,4,"immediate")); cursor+=4
            elif opcode in (0x83,0xc1): scalars.append((cursor,1,"immediate")); cursor+=1
        else: raise AssertionError((hex(start),hex(opcode)))
        assert start<cursor<=len(code)
        rows.append((start,cursor,tuple(absolute),tuple(relative),tuple(scalars)))
    return rows

def relocation_oracle(out,layout,routing):
    instructions=decode(out.code); starts={start for start,*_ in instructions}
    absolute=set(); relative=set(); scalar=set()
    modal=next((row.va for row in layout.protected_spans if row.role=="parent:.hdstate"),None)
    allowed={0x5202e0,0x511230,0x5199d8,0x526994,0x526990,0x532048,0x4ea4e8}
    allowed.update(range(0x51d4c0,0x51d4c0+216,4)); allowed.update(range(layout.rw.va,layout.rw.va+128,4))
    if modal is not None: allowed.update(range(modal,modal+128,4))
    zeros={layout.rw.va+128} | (set() if modal is None else {modal+128})
    width=int(layout.resolution.split("x")[0]); guard=dict(routing.entries)["check_owned_bound"]
    targets=[]
    for start,end,addresses,branches,scalars in instructions:
        opcode=out.code[start]
        for at,memory in addresses:
            value=struct.unpack_from("<I",out.code,at)[0]
            assert value in (allowed if memory else zeros),(start,at,hex(value))
            if memory and opcode==0x89: assert value==0x511230
            absolute.add(at)
        for at in branches:
            target=out.base_va+at+4+struct.unpack_from("<i",out.code,at)[0]
            if out.base_va<=target<out.base_va+len(out.code): assert target-out.base_va in starts
            else: assert opcode==0xe8 and target in (guard,0x42ffb0)
            targets.append((start,at,target)); relative.add(at)
        for at,size,role in scalars:
            scalar.add(at); value=int.from_bytes(out.code[at:at+size],"little")
            if role=="displacement":
                assert value%4==0 and value in set(range(0,1280+33,4))|{800,804,808,812}
            elif opcode==0xb8: assert value in (0,1,2,0xffffffff)
            elif opcode==0xb9: assert value in ((width-192)//64,16352,992)
            elif opcode==0x81: assert value in (1280,464)
            elif opcode==0xc1: assert value in (6,16)
            else: assert value in (0,1,7,16,32)
    declared={row.offset:row for row in out.relocations}; assert len(declared)==len(out.relocations)
    assert {at for at,row in declared.items() if row.kind=="abs32"}==absolute
    assert {at for at,row in declared.items() if row.kind=="rel32"}==relative
    assert not (set(declared)&scalar)
    typed=tool._operand_inventory(out,layout,routing)
    assert {row.offset for row in typed if row.kind=="abs32"}==absolute
    assert {row.offset for row in typed if row.kind=="rel32"}==relative
    assert {row.offset for row in typed if row.kind.startswith("scalar")}==scalar
    for start,at,target in targets:
        row=declared[at]; assert row.target==target
        if out.base_va<=target<out.base_va+len(out.code): assert row.purpose.startswith("field_v3_internal:")
        elif target==guard: assert row.purpose=="genuine profile owned bound guard"
        else: assert row.purpose=="authenticated native tactical tile"
    assert all(va-out.base_va in starts for _,va in out.entries+out.private_entries)
    actual_tiles=[target for _,_,target in targets if target==0x42ffb0]
    assert len(actual_tiles)==2
    receipts=tool._tile_receipts(out)
    assert tuple(row[0] for row in receipts)==(0,1)
    for mode,pc,at,target in receipts:
        assert pc==out.base_va+at and out.code[at]==0xe8
        assert target==dict(out.private_entries)["same_invocation"]
        assert declared[at+1].target==target
    return len(instructions),len(absolute),len(relative)

class SourceTests(unittest.TestCase):
    def test_all36_deterministic_complete_inventory_receipts_and_prefix_capacity(self):
        for profile in context.PROFILES:
            for resolution in context.RESOLUTIONS:
                with self.subTest(profile=profile,resolution=resolution):
                    layout,parent,routing,out=emit(profile,resolution)
                    again=emit(profile,resolution,fresh=True)[3]
                    self.assertEqual(asdict(out),asdict(again))
                    self.assertEqual(tuple(dict(out.entries)),ENTRIES)
                    self.assertEqual(tuple(dict(out.private_entries)),PRIVATE)
                    self.assertEqual(out.base_va,(routing.base_va+len(routing.code)+15)&~15)
                    self.assertLessEqual(out.base_va+len(out.code),layout.rx.va+262144)
                    counts=relocation_oracle(out,layout,routing)
                    self.assertGreater(counts[0],1000); self.assertGreater(counts[2],300)
                    for _,va in out.entries:
                        at=va-out.base_va
                        self.assertEqual(out.code[at:at+11],bytes.fromhex("9c60fc81ec0005000089e5"))

    def test_canonical_sources_parents_layout_operands_and_returns_reject(self):
        layout,parent,routing,out=emit("modalwidgets","1920x1080")
        for bad in (replace(routing,code=routing.code[:-1]+bytes([routing.code[-1]^1])),
                    replace(routing,entries=routing.entries[:-1]),replace(routing,relocations=routing.relocations[:-1])):
            with self.assertRaisesRegex(ValueError,"canonical routing"):
                tool._emit_code(layout,parent,bad,**kwargs())
        with self.assertRaisesRegex(ValueError,"canonical lifecycle"):
            tool._emit_code(layout,replace(parent,code=parent.code[:-1]),routing,**kwargs())
        for bad in (replace(layout,rx=replace(layout.rx,size=131072)),
                    replace(layout,rw=replace(layout.rw,size=4096)),replace(layout,battle_state_va=layout.rw.va+256),
                    replace(layout,provider_schema="invented"),replace(layout,protected_spans=layout.protected_spans[:-1]),
                    replace(layout,resolution="802x602")):
            with self.assertRaises(ValueError): tool._plan(bad)
        with self.assertRaises(ValueError): tool._versioned_template(kwargs()["template_source"]+b"\n",frozen)
        for bad in (replace(out,relocations=out.relocations[:-1]),replace(out,relocations=out.relocations+(out.relocations[0],)),
                    replace(out,entries=out.entries[:-1]+(("forged",out.base_va+1),)),replace(out,private_entries=out.private_entries[:-1])):
            with self.assertRaises(ValueError): tool._operand_inventory(bad,layout,routing)
        scalar=next(row for row in tool._operand_inventory(out,layout,routing) if row.kind=="scalar32" and row.role=="instruction_immediate")
        fake=clip.Relocation(scalar.offset,"abs32",scalar.value,"forged scalar as address")
        with self.assertRaises(ValueError): tool._operand_inventory(replace(out,relocations=out.relocations+(fake,)),layout,routing)
        receipt=tool._tile_receipts(out)[0]; raw=bytearray(out.code); raw[receipt[2]]=0x90
        with self.assertRaises(ValueError): tool._tile_receipts(replace(out,code=bytes(raw)))

    def test_private_pins_capture_poisoned_aliases_and_source_read_rejections(self):
        with issuer() as own:
            snapshot=own._snapshot()
            with patch.dict(own.PINNED_SOURCES,{own.ROUTING:"0"*64}):
                with self.assertRaisesRegex(ValueError,"source pin"): own._snapshot()
            original_read=Path.read_bytes
            with patch.object(Path,"read_bytes",lambda path:b"#"+original_read(path)[1:] if path==ROOT/tool.SOURCE else original_read(path)):
                with self.assertRaisesRegex(ValueError,"closure changed"): own._unchanged(snapshot)
            with patch.object(Path,"is_symlink",lambda path:path==ROOT/tool.SOURCE):
                with self.assertRaisesRegex(ValueError,"reparse"): own._read(ROOT/tool.SOURCE,ROOT)
            with patch.object(Path,"read_bytes",lambda path:original_read(path)[:-1] if path==ROOT/tool.SOURCE else original_read(path)):
                with self.assertRaisesRegex(ValueError,"changed while read"): own._read(ROOT/tool.SOURCE,ROOT)
        captured=[cell.cell_contents for cell in tool.emit_field_v3.__closure__]
        private=next(value for value in captured if callable(value) and getattr(value,"__name__",None)=="_issue")
        self.assertIsNot(private,tool._issue); self.assertTrue(private.__globals__["__canonical_field_v3_issuer__"])
        def poison(*args,**kwargs): raise AssertionError("public producer alias called")
        with issuer() as own,patch.object(tool,"_emit_code",poison),patch.object(route,"_issue",poison), \
             patch.object(route,"_emit_code",poison),patch.object(life,"_emit_code",poison), \
             patch.object(context,"build_allocation_context",poison):
            with own._modules(own._snapshot()) as modules:
                for name in (own.ROUTING,own.LIFECYCLE,own.CONTEXT,own.TEMPLATE):
                    self.assertEqual(modules[name].__loaded_source_sha256__,own.PINNED_SOURCES[name])
                self.assertIsNot(modules[own.ROUTING]._issue,poison)
                layout=routing_fixture.lifetime.synthetic_layout("classic","1024x768")
                parent=modules[own.LIFECYCLE]._emit_code(layout,template_source=snapshot[own.LIFE_TEMPLATE][0],
                    template_module=modules[own.LIFE_TEMPLATE],assembler_module=modules[own.CLIP])
                self.assertEqual(parent.state_va,layout.rw.va)
        for value in (b"",bytearray(),memoryview(b"")):
            with self.assertRaises(ValueError): tool.emit_field_v3(value,"classic","1024x768")

    def test_foreign_namespace_collisions_replacements_and_removals_preserved(self):
        token="c"*32
        names=("_battle_field_v3_"+token,"_battle_field_v3_"+token+".src",
            "_battle_field_v3_"+token+".src.patcher",
            "_battle_field_v3_"+token+".src.patcher.battle_profile_routing_v2",
            "_battle_field_v3_"+token+".src.patcher.battle_profile_field_v2","_battle_field_v3_issuer_"+token)
        with issuer() as own:
            for name in names:
                foreign=ModuleType(name); foreign.preserved=object(); before=dict(sys.modules)
                sys.modules[name]=foreign; attrs=dict(foreign.__dict__)
                try:
                    with patch.object(uuid,"uuid4",return_value=SimpleNamespace(hex=token)):
                        with self.assertRaisesRegex(ValueError,"namespace occupied"):
                            if name.startswith("_battle_field_v3_issuer"): own._production_factory()
                            else:
                                with own._modules(own._snapshot()): pass
                    self.assertIs(sys.modules[name],foreign); self.assertEqual(foreign.__dict__,attrs)
                    self.assertEqual(set(sys.modules),set(before)|{name})
                    self.assertTrue(all(sys.modules[key] is value for key,value in before.items()))
                finally: del sys.modules[name]
            for remove in (False,True):
                before=dict(sys.modules)
                with self.assertRaisesRegex(ValueError,"identity changed"):
                    with own._modules(own._snapshot()) as modules:
                        name=modules[own.TEMPLATE].__name__
                        if remove: del sys.modules[name]
                        else: sys.modules[name]=foreign
                if not remove: self.assertIs(sys.modules.pop(name),foreign)
                self.assertEqual(set(sys.modules),set(before))

    def test_exact_owned_frame_receipts_and_false_native_installation_claims(self):
        tree=ast.parse((ROOT/tool.SOURCE).read_text(encoding="utf-8"))
        metadata=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and
            isinstance(node.func,ast.Name) and node.func.id=="dict" and any(
                field.arg=="schema" and isinstance(field.value,ast.Constant) and
                field.value.value=="clash95_battle_profile_field_v3" for field in node.keywords)]
        self.assertEqual(len(metadata),1);fields={item.arg:item.value for item in metadata[0].keywords if item.arg}
        for name,value in (("helper_local_frame_bytes",1280),("zero_scan_extra_stack_bytes",32),
            ("cache_slot_own_bindings",{1104:4,1112:8,1120:72,1124:64}),
            ("stack_control_receipt_offsets",{1156:1132,1160:1136,1164:1140,1168:1144}),
            ("provider_records_emitted",0),("query_rejection",0xffffffff)):
            self.assertEqual(ast.literal_eval(fields[name]),value,name)
        for name in ("whole_chain_capacity_verified","native_tile_checked_current_cell",
            "native_local_control_integrity_verified","arena_intersection_verified",
            "native_arena_clipping_verified","writes_state","writes_headers","clears_physical",
            "native_callback_abi_verified","native_provider_rle_verified","native_cancellation_verified",
            "downstream_frozen_lease_compatible","downstream_frozen_continuation_compatible"):
            self.assertIs(ast.literal_eval(fields[name]),False,name)
        self.assertIn("native_stack_capacity_verified",tool.FALSE_CLAIMS)
        self.assertIn("healthy_return_verified",tool.FALSE_CLAIMS)
        for profile in context.PROFILES:
            layout,_,routing,out=emit(profile)
            relocation_oracle(out,layout,routing)
            self.assertGreater(out.base_va,layout.rx.va)
            self.assertNotIn(737,[row[2] for row in tool._tile_receipts(out)])

class Machine(routing_fixture.Machine):
    def __init__(self,tools,profile="classic",resolution="1024x768",delta=0):
        self.field_active=False; self.tiles=[]; self.tile_mutation=None
        admitted_hooks=[]; actual_hook_add=tools[0].Uc.hook_add
        def capture_hook(cpu,kind,*args,**kwargs):
            handle=actual_hook_add(cpu,kind,*args,**kwargs)
            admitted_hooks.append((kind,handle)); return handle
        with patch.object(tools[0].Uc,"hook_add",capture_hook):
            super().__init__(tools,profile,resolution,delta)
        self.field_emission=emit(profile,resolution)[3]
        self.field_entries={name:va+delta for name,va in self.field_emission.entries}
        raw=bytearray(self.field_emission.code)
        for row in self.field_emission.relocations:
            if row.kind=="abs32": struct.pack_into("<I",raw,row.offset,row.target+delta)
        self.cpu.mem_write(self.field_emission.base_va+delta,bytes(raw))
        self.loaded_code=[]
        for emission in (self.emission,self.routing_emission,self.field_emission):
            expected=bytearray(emission.code)
            for relocation in emission.relocations:
                if relocation.kind=="abs32": struct.pack_into("<I",expected,relocation.offset,relocation.target+delta)
            self.loaded_code.append((emission.base_va+delta,bytes(expected)))
        self.scan_before={}; self.scan_after={}; self.scan_observations=0; self.scan_dwords=0
        excluded=[]
        for emission,decoder in ((self.emission,routing_fixture.lifetime.decode),
                                 (self.routing_emission,routing_fixture.decode),(self.field_emission,decode)):
            for row in decoder(emission.code):
                start,end=row[:2]
                if emission.code[start]!=0xf3: continue
                va=emission.base_va+delta+start;excluded.append((va,va+end-start-1))
                if emission.code[start+1]==0xaf:
                    # Observe real SCAS input/output, not each REP iteration.
                    # Unicorn still executes every read and applies protection.
                    assert emission.code[start-10]==0xb9 and emission.code[start-5]==0xbf
                    count=struct.unpack_from("<I",emission.code,start-9)[0]
                    pointer=struct.unpack_from("<I",emission.code,start-4)[0]+delta
                    self.scan_before[va-5]=(va+2,pointer,count)
                    self.scan_after[va+2]=(pointer,count)
        for kind,handle in admitted_hooks:
            if kind in (self.u.UC_HOOK_CODE,self.u.UC_HOOK_MEM_READ): self.cpu.hook_del(handle)
        cursor=1
        for lo,hi in sorted(excluded):
            if cursor<lo: self.cpu.hook_add(self.u.UC_HOOK_CODE,self.on_code,begin=cursor,end=lo-1)
            cursor=hi+1
        self.cpu.hook_add(self.u.UC_HOOK_CODE,self.on_code,begin=cursor,end=0xffffffff)
        # The fixed authored inventory admits tail reads only through these
        # complete SCAS loops. All other reads retain the inherited observer;
        # writes and invalid/protected memory accesses are never suppressed.
        tails=[(self.state_va+128,self.state_va+65536-1)]
        if self.modal_va is not None: tails.append((self.modal_va+delta+128,self.modal_va+delta+4096-1))
        self.tail_ranges=tails;self.tail_handles=[];self.active_scan=None
        self.scan_next=0;self.scan_reads=0
        cursor=1
        for lo,hi in sorted(tails):
            if cursor<lo: self.cpu.hook_add(self.u.UC_HOOK_MEM_READ,self.on_read,begin=cursor,end=lo-1)
            cursor=hi+1
        self.cpu.hook_add(self.u.UC_HOOK_MEM_READ,self.on_read,begin=cursor,end=0xffffffff)
        self.restore_tail_observers()

    def observe_tail_read(self,cpu,access,address,size,value,data):
        # Every actual tail read remains observed. Only the exact decoded
        # BF/SCAS/exit window admits monotonic DWORD reads within its budget.
        if self.active_scan is None:
            raise AssertionError(("tail read outside decoded scan",cpu.reg_read(self.regs["EIP"]),address,size))
        assert size==4 and address==self.scan_next and self.scan_reads<self.active_scan[2]
        self.scan_next+=4;self.scan_reads+=1

    def on_read(self,cpu,access,address,size,value,data):
        if self.active_scan is not None:
            # The virgin first128B scans lie outside tail address ranges.
            assert size==4 and address==self.scan_next and self.scan_reads<self.active_scan[2]
            self.scan_next+=4;self.scan_reads+=1
            return
        super().on_read(cpu,access,address,size,value,data)

    def restore_tail_observers(self):
        if not self.tail_handles:
            self.tail_handles=[self.cpu.hook_add(self.u.UC_HOOK_MEM_READ,self.observe_tail_read,begin=lo,end=hi)
                for lo,hi in self.tail_ranges]

    def prepare(self,*,columns=20,scroll=0):
        super().prepare(); self.put(self.WORLD+804,columns); self.put(self.WORLD+808,scroll)
        return self

    def pixels(self):
        return bytes(self.cpu.mem_read(self.PHYSICAL_PIXELS,self.width*self.height))

    def record(self):
        return bytes(self.cpu.mem_read(self.state_va,128))

    def on_code(self,cpu,address,size,data):
        if address in self.scan_before:
            after,pointer,count=self.scan_before[address]
            assert cpu.reg_read(self.regs["ECX"])==count
            assert cpu.reg_read(self.regs["EAX"])==0 and cpu.reg_read(self.regs["EFLAGS"])&0x400==0
            assert self.active_scan is None
            self.active_scan=(after,pointer,count)
            self.scan_next=pointer;self.scan_reads=0
        if address in self.scan_after:
            pointer,count=self.scan_after[address]; remaining=cpu.reg_read(self.regs["ECX"])
            assert self.active_scan==(address,pointer,count)
            end=cpu.reg_read(self.regs["EDI"])
            assert 0<=remaining<count and end==pointer+4*(count-remaining)
            assert self.scan_next==end and self.scan_reads==count-remaining
            assert cpu.reg_read(self.regs["EFLAGS"])&0x400==0
            if cpu.reg_read(self.regs["EFLAGS"])&0x40: assert remaining==0
            else: assert self.word(end-4)!=0
            self.scan_observations+=1;self.scan_dwords+=count-remaining
            self.active_scan=None
        if address==0x42ffb0+self.delta:
            assert self.field_active and cpu.reg_read(self.regs["EFLAGS"])&0x400==0
            assert self.word(native.RENDER+self.delta)==self.PHYSICAL
            x,y=(cpu.reg_read(self.regs[name]) for name in ("EAX","EDX"))
            columns,scroll=self.word(self.WORLD+804),self.word(self.WORLD+808)
            visible=min(columns,(self.width-192)//64)
            assert 0<=y<7 and scroll<=x<scroll+visible,(x,y,columns,scroll)
            self.tiles.append((x,y)); self.callback("tile")
            row=bytes([pixel_oracle.color(x,y)])*64; left=32+(x-scroll)*64; top=16+y*64
            for py in range(top,top+64): cpu.mem_write(self.PHYSICAL_PIXELS+py*self.width+left,row)
            if self.tile_mutation: self.tile_mutation(self,len(self.tiles))
            cpu.reg_write(self.regs["ECX"],0xbadc1234);cpu.reg_write(self.regs["EDX"],0xbcde2345)
            cpu.reg_write(self.regs["EFLAGS"],0x602);self.ret(0xcdef3456)
        else: super().on_code(cpu,address,size,data)

    def invoke_field(self,name,*,eax=0x12345678,edx=0x22334455,ecx=0x11223344,flags=0xed7):
        self.field_active=True;self.routing_active=True;self.stops=set();self.native_stop=None
        self.writes=[];self.reads=[];self.tiles=[];self.minimum_sp=self.SP
        self.scan_observations=0;self.scan_dwords=0
        before_callbacks=len(self.callbacks)
        registers=dict(EAX=eax,EDX=edx,ECX=ecx,EBX=0x33445566,EBP=0x44556677,ESI=0x55667788,EDI=0x66778899,ESP=self.SP)
        self.put(self.SP,self.STOP)
        for key,value in registers.items(): self.cpu.reg_write(self.regs[key],value&0xffffffff)
        self.cpu.reg_write(self.regs["EFLAGS"],flags)
        try: self.cpu.emu_start(self.field_entries[name],self.STOP+1,count=30000000)
        finally:
            self.field_active=False;self.routing_active=False
            self.restore_tail_observers();self.active_scan=None
        actual={key:self.cpu.reg_read(reg) for key,reg in self.regs.items()}
        assert self.native_stop==self.STOP and actual["ESP"]==self.SP+4,(name,actual)
        for key,value in registers.items():
            if key not in ("EAX","ESP"): assert actual[key]==value&0xffffffff,(name,key,actual[key],value)
        assert actual["EFLAGS"]&self.MASK==flags&self.MASK,(name,actual)
        assert 4+self.SP-self.minimum_sp<=2680,(name,self.minimum_sp,self.SP)
        assert self.scan_observations>0 and self.scan_dwords>0
        for va,expected in self.loaded_code:
            assert bytes(self.cpu.mem_read(va,len(expected)))==expected,"observer changed emitted prefix"
        for address,size in self.writes:
            assert self.STACK<=address and address+size<=self.STACK+65536 or address==native.RENDER+self.delta and size==4
        self.field_callbacks=self.callbacks[before_callbacks:]
        return actual

class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: cls.tools=routing_fixture.lifetime.prior_fixture.machine_tools()
        except ImportError as error: raise unittest.SkipTest(str(error))

    def dispose(self,machine):
        del machine
        gc.collect()

    def test_all36_two_bases_queries_full_incremental_pixels_and_abi(self):
        for profile in context.PROFILES:
            for resolution in context.RESOLUTIONS:
                for delta in (0,0x100000):
                    with self.subTest(profile=profile,resolution=resolution,delta=delta):
                        width,height=map(int,resolution.split("x")); visible=min(20,(width-192)//64); scroll=20-visible
                        m=Machine(self.tools,profile,resolution,delta).prepare(scroll=scroll)
                        before,record,render=m.pixels(),m.record(),m.word(native.RENDER+delta)
                        self.assertEqual(m.invoke_field("visible_columns")["EAX"],visible)
                        for requested in (-1,0,scroll,0x7fffffff):
                            self.assertEqual(m.invoke_field("clamp_scroll_x",edx=requested)["EAX"],min(max(requested,0),scroll))
                        for px,py in ((32,16),(32+visible*64-1,463),(31,16),(32,15),(32+visible*64,16),(32,464),(width-160,100),(width-1,height-1)):
                            expected=scroll+(px-32)//64 | (((py-16)//64)<<16) if 32<=px<32+visible*64 and 16<=py<464 else 0xffffffff
                            self.assertEqual(m.invoke_field("screen_to_cell",edx=px,ecx=py)["EAX"],expected)
                        for x,y in ((scroll,0),(scroll+visible-1,6),(scroll-1,0),(20,0),(scroll,-1),(scroll,7)):
                            expected=int(scroll<=x<scroll+visible) if 0<=x<20 and 0<=y<7 else 0xffffffff
                            self.assertEqual(m.invoke_field("visible_cell",eax=x,edx=y)["EAX"],expected)
                        self.assertEqual(m.pixels(),before);self.assertEqual(m.record(),record)
                        self.assertEqual(m.invoke_field("draw_full")["EAX"],1)
                        self.assertEqual(m.tiles,[(x,y) for x in range(scroll,scroll+visible) for y in range(7)])
                        self.assertEqual(m.pixels(),pixel_oracle.expected_pixels(width,height,20,scroll,before))
                        self.assertEqual(m.record(),record);self.assertEqual(m.word(native.RENDER+delta),render)
                        full=m.pixels();x,y=scroll+visible-1,6
                        self.assertEqual(m.invoke_field("draw_incremental",eax=x,edx=y)["EAX"],1)
                        self.assertEqual(m.tiles,[(x,y)])
                        self.assertEqual(m.pixels(),pixel_oracle.expected_pixels(width,height,20,scroll,full,[(x,y)]))
                        self.assertEqual(m.word(native.RENDER+delta),render)
                        del m;gc.collect()

    def test_denial_history_aliases_and_small_arena_boundaries(self):
        for profile in context.PROFILES:
            for delta in (0,0x100000):
                virgin=Machine(self.tools,profile,"800x600",delta)
                for name in ("draw_full","draw_incremental"):
                    before,record,render=virgin.pixels(),virgin.record(),virgin.word(native.RENDER+delta)
                    self.assertEqual(virgin.invoke_field(name,eax=0,edx=0)["EAX"],0)
                    self.assertEqual(virgin.tiles,[]);self.assertEqual(virgin.pixels(),before);self.assertEqual(virgin.record(),record)
                    self.assertEqual(virgin.word(native.RENDER+delta),render)
                    self.assertFalse(any(at==native.RENDER+delta for at,_ in virgin.writes))
                del virgin;gc.collect()
                for lane in ("phase","history","tail_first","tail_last","rw_first","rw_middle","rw_last","rw_cross",
                             "rx_first","rx_middle","rx_last","rx_cross","modal_tail","modal_alias"):
                    if lane in ("modal_tail","modal_alias") and profile in ("classic","framed"): continue
                    m=Machine(self.tools,profile,"800x600",delta).prepare()
                    if lane=="phase": m.set_state("phase",0)
                    elif lane=="history": m.set_state("frees",1)
                    elif lane=="tail_first": m.put(m.state_va+128,9)
                    elif lane=="tail_last": m.put(m.state_va+65532,9)
                    elif lane=="modal_tail": m.put(m.modal_va+delta+4092,9)
                    else:
                        if lane=="modal_alias": pointer=m.modal_va+delta+4092
                        else:
                            span=m.layout.rw if lane.startswith("rw_") else m.layout.rx
                            offset={"first":0,"middle":span.size//2,"last":span.size-4,"cross":-4}[lane.split("_")[1]]
                            pointer=span.va+delta+offset
                        m.put(m.PHYSICAL+0xb0,pointer);m.set_state("physical_pixels",pointer)
                    before,render=m.pixels(),m.word(native.RENDER+delta)
                    for name in ("draw_full","draw_incremental"):
                        self.assertEqual(m.invoke_field(name,eax=0,edx=0)["EAX"],2)
                        self.assertEqual(m.tiles,[]);self.assertEqual(m.pixels(),before)
                        self.assertEqual(m.word(native.RENDER+delta),render)
                        self.assertFalse(any(at==native.RENDER+delta for at,_ in m.writes))
                    self.assertEqual(m.invoke_field("visible_columns")["EAX"],0xffffffff)
                    del m;gc.collect()
        for resolution in ("800x600","1366x768","3440x1440","3840x2160"):
            for columns in (1,2,7,9,13,20):
                width,height=map(int,resolution.split("x"));visible=min(columns,(width-192)//64);scroll=columns-visible
                m=Machine(self.tools,"modalwidgets",resolution).prepare(columns=columns,scroll=scroll)
                before=m.pixels();x,y=scroll+visible-1,6
                self.assertEqual(m.invoke_field("draw_incremental",eax=x,edx=y)["EAX"],1)
                self.assertEqual(m.pixels(),pixel_oracle.expected_pixels(width,height,columns,scroll,before,[(x,y)]))
                before=m.pixels();render=m.word(native.RENDER)
                for x,y in ((-1,0),(scroll-1,0),(columns,0),(scroll,-1),(scroll,7)):
                    self.assertEqual(m.invoke_field("draw_incremental",eax=x,edx=y)["EAX"],0)
                    self.assertEqual(m.tiles,[]);self.assertEqual(m.pixels(),before)
                    self.assertEqual(m.word(native.RENDER),render)
                del m;gc.collect()

    def test_each_tile_fixed_record_tail_cache_control_loss_precedes_poisoned_heap(self):
        cases=[("own",offset) for offset in range(0,128,4)]+[("modal",offset) for offset in range(0,128,4)]
        cases += [("tail",128),("tail",65532),("modal_tail",128),("modal_tail",4092)]
        cases += [("cache",offset) for offset in (1104,1112,1120,1124)]
        cases += [("control",offset) for offset in (1132,1136,1140,1144)]
        cases += [("global",address) for address in (0x5202e0,0x511230,0x5199d8,0x526994,0x526990,0x532048,0x4ea4e8)]
        for delta in (0,0x100000):
            for name in ("draw_full","draw_incremental"):
                for lane,offset in cases:
                    with self.subTest(delta=delta,name=name,lane=lane,offset=offset):
                        m=Machine(self.tools,"modalwidgets","800x600",delta).prepare()
                        m.put(native.RENDER+delta,m.PRIVATE); before=m.pixels();frame=m.SP-36-1280
                        def mutate(machine,ordinal):
                            self.assertEqual(ordinal,1)
                            at=machine.state_va+offset if lane in ("own","tail") else machine.modal_va+delta+offset if lane in ("modal","modal_tail") else offset+delta if lane=="global" else frame+offset
                            machine.put(at,0x17000000 if lane=="global" and offset==0x4ea4e8 else machine.word(at)^1)
                            machine.cpu.mem_protect(machine.PHYSICAL,4096,machine.u.UC_PROT_NONE)
                        m.tile_mutation=mutate
                        self.assertEqual(m.invoke_field(name,eax=0,edx=0)["EAX"],2)
                        self.assertEqual(m.tiles,[(0,0)])
                        self.assertEqual(m.pixels(),pixel_oracle.expected_pixels(800,600,20,0,before,[(0,0)]))
                        self.assertEqual(m.word(native.RENDER+delta),m.PHYSICAL^1 if lane=="global" and offset==native.RENDER else m.PHYSICAL)
                        self.assertEqual(sum(at==native.RENDER+delta for at,_ in m.writes),1)
                        self.assertEqual(m.field_callbacks,["thread","thread","tile"])
                        del m;gc.collect()

    def test_thread_loss_private_return_balance_and_actual_tile_post_pc(self):
        for delta in (0,0x100000):
            for ordinal in (1,2,3,4):
                for name in ("draw_full","draw_incremental"):
                    if ordinal==4 and name=="draw_incremental": continue
                    with self.subTest(delta=delta,ordinal=ordinal,name=name):
                        m=Machine(self.tools,"modalwidgets","1024x768",delta).prepare(columns=2)
                        m.put(native.RENDER+delta,m.PRIVATE); before=m.pixels();seen=[]
                        def mutate(machine,label):
                            if label=="thread":
                                seen.append(label)
                                if len(seen)==ordinal:
                                    machine.put(machine.state_va+65532,1)
                                    machine.cpu.mem_protect(machine.PHYSICAL,4096,machine.u.UC_PROT_NONE)
                        m.mutation=mutate
                        self.assertEqual(m.invoke_field(name,eax=0,edx=0)["EAX"],2)
                        tiles=[] if ordinal<=2 else [(0,0)]
                        self.assertEqual(m.tiles,tiles)
                        self.assertEqual(m.pixels(),pixel_oracle.expected_pixels(1024,768,2,0,before,tiles))
                        self.assertEqual(m.word(native.RENDER+delta),m.PRIVATE if ordinal==1 else m.PHYSICAL)
                        del m;gc.collect()
            m=Machine(self.tools,"modalwidgets","1366x768",delta).prepare(columns=2)
            private={va+delta:name for name,va in m.field_emission.private_entries};frame=m.SP-36-1280;observed=[]
            post={pc+delta:mode for mode,pc,_,_ in tool._tile_receipts(m.field_emission)};observed_post=[]
            def observe(cpu,address,size,data):
                if address in private:
                    helper=private[address];observed.append(helper)
                    self.assertEqual(cpu.reg_read(m.regs["EBP"]),frame)
                    self.assertEqual(cpu.reg_read(m.regs["ESP"]),frame-(8 if helper=="check_invocation" else 4))
                if address in post: observed_post.append(post[address])
            m.cpu.hook_add(m.u.UC_HOOK_CODE,observe)
            for at in (m.SP-4096,m.SP+4): m.cpu.mem_write(at,b"\xa9"*16)
            self.assertEqual(m.invoke_field("draw_full")["EAX"],1)
            self.assertEqual(observed.count("capture_invocation"),1)
            self.assertEqual(observed.count("same_invocation"),28)
            self.assertEqual(observed.count("check_invocation"),28)
            self.assertEqual(observed_post,[0]*14)
            for at in (m.SP-4096,m.SP+4): self.assertEqual(bytes(m.cpu.mem_read(at,16)),b"\xa9"*16)
            # Demonstrate that the observer still detects actual reads into
            # either protected tail outside a decoded, completed scan.
            diagnostic=m.THREAD+0x600
            for lo,_ in m.tail_ranges:
                m.cpu.mem_write(diagnostic,b"\xa1"+struct.pack("<I",lo)+b"\xc3")
                with self.assertRaisesRegex(AssertionError,"tail read outside decoded scan"):
                    m.cpu.emu_start(diagnostic,diagnostic+6,count=2)
            del m;gc.collect()

class OriginalTests(unittest.TestCase):
    def test_canonical_original_parent_native_spans_receipts_and_false_claims(self):
        if ORIGINAL is None: self.skipTest("explicit optional Original RAM lane")
        before=ORIGINAL.read_bytes(); self.assertEqual(sha(before),tool.BASE_SHA256)
        bundle=tool.emit_field_v3(before,"modalwidgets","1920x1080")
        self.assertEqual(ORIGINAL.read_bytes(),before)
        layout=bundle.routing_bundle.lifecycle_bundle.allocation_context.layout
        relocation_oracle(bundle.emission,layout,bundle.routing_bundle.emission)
        metadata=bundle.metadata()
        self.assertEqual(metadata["source_hashes"][tool.ROUTING],tool.PINNED_SOURCES[tool.ROUTING])
        self.assertEqual(bundle.tile_return_receipts,tool._tile_receipts(bundle.emission))
        self.assertEqual(bundle.hook_sites,());self.assertEqual(bundle.removed_highlow_rvas,())
        for name in tool.FALSE_CLAIMS: self.assertIs(metadata[name],False,name)
        self.assertIs(metadata["native_tile_checked_current_cell"],False)
        self.assertEqual(metadata["provider_records_emitted"],0)

def main(argv=None):
    global ORIGINAL
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolchain-path",type=Path);parser.add_argument("--require-machine-tools",action="store_true")
    parser.add_argument("--source-only",action="store_true");parser.add_argument("--original-backed",type=Path)
    args=parser.parse_args(argv)
    if args.toolchain_path: sys.path.insert(0,str(args.toolchain_path.resolve()))
    if args.require_machine_tools:
        try: routing_fixture.lifetime.prior_fixture.machine_tools()
        except ImportError as error: print(str(error),file=sys.stderr);return 2
    classes=(SourceTests,) if args.source_only else (SourceTests,CPUTests)
    if args.original_backed: ORIGINAL=args.original_backed;classes+=(OriginalTests,)
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in classes)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1

if __name__=="__main__": raise SystemExit(main())
