#!/usr/bin/env python3
"""Stack-only preparation on synthetic x86, never native game execution.

The frozen field fixture models Tile pixels. Native sprite/line callbacks here
model only a normal RET and exactly-once closure; they prove no intra-decoder
cancellation or native resource behavior. Optional original audit is RAM-only.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT / "tools")]
from src.patcher import battle_profile_stack_lease as lease
from src.patcher import battle_profile_field_v2 as field
from src.patcher import battle_profile_lifecycle as life
from src.patcher import battle_profile_routing as route
from src.patcher import battle_profile_context as context
from src.patcher import partial_tile_clip as clip
from src.patcher import framed_modal_canvas as native
import test_battle_profile_field as oracle

FIELD_FIXTURE_SHA = "d5776f1850e7f6c085fbfb08016f2eb17f4aa0f9889acd0807ad2dabe04979c6"
PUBLIC = ("leased_draw_full","leased_draw_incremental","check_tile","check_unit",
          "check_adjacent","check_tracking_effect","check_charge_effect",
          "check_sprite","check_line","guarded_sprite","guarded_line")
PATHS = {
    "tile": (),
    "unit": ((76,0x4303B1),),
    "adjacent": ((72,0x4302DC),),
    "unit_adjacent": ((72,0x4302DC),(24,0x42FCC4)),
    "tracking_tile": ((92,0x43087D),),
    "tracking_unit": ((76,0x4303B1),(88,0x42FA7C)),
    "tracking_adjacent": ((72,0x4302DC),(24,0x42FCC4),(88,0x42FBBD)),
    "charge_unit": ((76,0x4303B1),(100,0x42F932)),
    "charge_adjacent": ((72,0x4302DC),(24,0x42FCC4),(100,0x42F932)),
    "sprite_tile": ((100,0x430038),),
    "sprite_unit": ((76,0x4303B1),(96,0x42FC1E)),
    "sprite_adjacent": ((72,0x4302DC),(24,0x42FCC4),(96,0x42FC1E)),
    "sprite_tracking_tile": ((92,0x43087D),(48,0x405555)),
    "sprite_tracking_unit": ((76,0x4303B1),(88,0x42FA7C),(48,0x405555)),
    "sprite_tracking_adjacent": ((72,0x4302DC),(24,0x42FCC4),(88,0x42FBBD),(48,0x405555)),
    "sprite_charge_unit": ((76,0x4303B1),(100,0x42F932),(60,0x4055B6)),
    "sprite_charge_adjacent": ((72,0x4302DC),(24,0x42FCC4),(100,0x42F932),(60,0x4055B6)),
    "line": ((80,0x430AD8),),
}


def verify_frozen():
    if hashlib.sha256((ROOT / "tools/test_battle_profile_field.py").read_bytes()).hexdigest() != FIELD_FIXTURE_SHA:
        raise ValueError("frozen independent field fixture differs")
    for name,digest in lease.PINNED_SOURCES.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError("frozen lease dependency differs: " + name)


def emit(profile="classic",resolution="1024x768"):
    plan = oracle.lifetime_fixture.synthetic_plan(profile,resolution)
    modal = None if profile in ("classic","framed") else plan["rw"]["va"]-256
    first = life._emit_code(plan,modal_state_va=modal,assembler_module=clip)
    second = route._emit_code(plan,first,modal_state_va=modal,assembler_module=clip)
    parent = field._emit_code(plan,second,assembler_module=clip)
    return plan,parent,lease._emit_code(plan,parent,assembler_module=clip)


class Machine(oracle.Machine):
    def __init__(self,tools,profile="classic",resolution="1024x768",delta=0):
        self.pause_tile = False
        self.primitive_mutation = None
        self.primitives = []
        self.closures = []
        with patch.object(oracle,"field",return_value=field):
            super().__init__(tools,profile,resolution,delta)
        self.lease_emission = lease._emit_code(self.plan,self.field_emission,assembler_module=clip)
        self.lease_entries = {name:va+delta for name,va in self.lease_emission.entries}
        code = bytearray(self.lease_emission.code)
        for row in self.lease_emission.relocations:
            if row.kind == "abs32": struct.pack_into("<I",code,row.offset,row.target+delta)
        self.cpu.mem_write(self.lease_emission.base_va+delta,bytes(code))
        self.thread_clobbers = True

    def on_code(self,cpu,address,size,data):
        if address == oracle.TILE+self.delta and self.pause_tile:
            self.tile_context = {name:cpu.reg_read(reg) for name,reg in self.regs.items()}
            self.tile_sp = self.tile_context["ESP"]
            self.field_frame = self.tile_sp+4
            self.lease_frame = self.word(self.field_frame+1288)
            self.pause_tile = False
            self.tile_paused = True
            cpu.emu_stop()
        elif address in (0x402E80+self.delta,0x403F70+self.delta):
            family = "sprite" if address == 0x402E80+self.delta else "line"
            pop = 28 if family == "sprite" else 8
            sp = cpu.reg_read(self.regs["ESP"])
            arguments = tuple(self.word(sp+at) for at in range(4,pop+1,4))
            registers = {name:cpu.reg_read(self.regs[name]) for name in ("EAX","ECX","EDX","EBX","EBP","ESI","EDI","EFLAGS")}
            self.callback(family)
            self.primitives.append((family,arguments,registers))
            # Model unchanged native normal RET cleanup exactly once. A later
            # ownership mutation deliberately occurs only at that safe return.
            self.closures.append(family)
            if self.primitive_mutation: self.primitive_mutation(self,family)
            cpu.reg_write(self.regs["EAX"],0xC0FFEE11)
            cpu.reg_write(self.regs["ECX"],0x1234ABCD)
            cpu.reg_write(self.regs["EDX"],0x5678EF01)
            cpu.reg_write(self.regs["EFLAGS"],0x247)
            self.ret()
            cpu.reg_write(self.regs["ESP"],sp+4+pop)
        else:
            super().on_code(cpu,address,size,data)

    def begin(self,mode=0,*,eax=0,edx=0,flags=0xED7):
        self.field_active = self.routing_active = True
        self.stops,self.native_stop = set(),None
        self.writes,self.reads,self.tiles = [],[],[]
        self.initial = dict(EAX=eax,ECX=0x10203040,EDX=edx,EBX=0x40506070,
                            EBP=0x50607080,ESI=0x60708090,EDI=0x708090A0,ESP=self.SP)
        self.initial_flags = flags
        self.put(self.SP,self.STOP)
        for name,value in self.initial.items(): self.cpu.reg_write(self.regs[name],value)
        self.cpu.reg_write(self.regs["EFLAGS"],flags)
        self.pause_tile,self.tile_paused = True,False
        self.cpu.emu_start(self.lease_entries["leased_draw_incremental" if mode else "leased_draw_full"],
                           self.STOP+1,count=10000000)
        assert self.tile_paused,(self.native_stop,self.callbacks)
        assert self.lease_frame == self.field_frame+1320
        assert self.lease_word("outer_return_pc") == self.STOP
        assert self.lease_word("outer_saved_ebp") == self.initial["EBP"]
        return self

    def lease_word(self,name): return self.word(self.lease_frame+lease.DESCRIPTOR[name])

    def ancestry(self,path,*,arguments=None,return_override=None,tile_saved_ebp=None):
        at = self.tile_sp
        # Model the authenticated original Tile PUSH frame for its nested
        # families; no original instruction is executed by this fixture.
        self.put(self.tile_sp-20,self.field_frame if tile_saved_ebp is None else tile_saved_ebp)
        for distance,pc in PATHS[path]:
            at -= distance
            self.put(at,pc+self.delta)
        if return_override is not None: self.put(at,return_override)
        family = "sprite" if path.startswith("sprite") else (
            "tracking_effect" if path.startswith("tracking") else
            "charge_effect" if path.startswith("charge") else
            "unit" if path.startswith("unit") else path)
        values = arguments if arguments is not None else tuple(
            0x89100000+number*0x10101 for number in range(lease.ARG_BYTES[family]//4))
        for number,value in enumerate(values): self.put(at+4+number*4,value)
        return at,family,tuple(values)

    def invoke_leaf(self,path,*,guarded=False,arguments=None,return_override=None,
                    tile_saved_ebp=None,entry_sp=None,caller_ebp=None):
        sp,family,args = self.ancestry(path,arguments=arguments,return_override=return_override,
                                     tile_saved_ebp=tile_saved_ebp)
        if entry_sp is not None:
            sp=entry_sp; self.put(sp,self.STOP)
        ra = self.word(sp)
        self.stops,self.native_stop = {ra},None
        self.reads,self.writes = [],[]
        before = dict(EAX=self.PHYSICAL,ECX=0xFFEEDDCC,EDX=0x11223344,EBX=0x22334455,
                      EBP=0x33445566,ESI=0x44556677,EDI=0x55667788,ESP=sp)
        if path == "tile": before["EBP"]=self.field_frame
        if caller_ebp is not None: before["EBP"]=caller_ebp
        for name,value in before.items(): self.cpu.reg_write(self.regs[name],value)
        self.cpu.reg_write(self.regs["EFLAGS"],0xED7)
        helper = ("guarded_" if guarded else "check_")+family
        self.cpu.emu_start(self.lease_entries[helper],self.STOP+1,count=1000000)
        actual = {name:self.cpu.reg_read(reg) for name,reg in self.regs.items()}
        assert self.native_stop == ra,(helper,actual)
        assert actual["ESP"] == sp+4+lease.ARG_BYTES[family],(helper,actual)
        assert self.word(sp) == ra,"helper repaired/changed native return PC"
        for address,size in self.writes:
            assert self.STACK <= address and address+size <= self.STACK+0x10000,(helper,address,size)
        return actual,before,args

    def complete(self):
        self.stops,self.native_stop = set(),None
        for name,value in self.tile_context.items(): self.cpu.reg_write(self.regs[name],value)
        # Invoke the independent modeled Tile at the genuine captured frame;
        # subsequent frozen V2 Tiles deliberately remain unadapted.
        oracle.Machine.on_code(self,self.cpu,oracle.TILE+self.delta,1,None)
        self.cpu.emu_start(self.cpu.reg_read(self.regs["EIP"]),self.STOP+1,count=10000000)
        actual = {name:self.cpu.reg_read(reg) for name,reg in self.regs.items()}
        assert self.native_stop == self.STOP
        assert actual["ESP"] == self.SP+4
        for name,value in self.initial.items():
            if name not in ("EAX","ESP"): assert actual[name] == value,(name,actual[name],value)
        assert actual["EFLAGS"] & self.MASK == self.initial_flags & self.MASK
        self.field_active = self.routing_active = False
        return actual


class SourceTests(unittest.TestCase):
    def setUp(self): verify_frozen()

    def test_metadata_excludes_receiver_arguments_clipping_and_standalone_installation(self):
        tree=ast.parse((ROOT/lease.SOURCE).read_text(encoding='utf-8'))
        producers=[node for node in ast.walk(tree) if isinstance(node,ast.Call)
                   and isinstance(node.func,ast.Name) and node.func.id=='dict'
                   and any(item.arg=='schema' and isinstance(item.value,ast.Constant)
                           and item.value.value=='clash95_battle_profile_stack_lease_v1' for item in node.keywords)]
        self.assertEqual(len(producers),1)
        values={item.arg:item.value for item in producers[0].keywords if item.arg}
        for name in ('installed','arena_intersection_verified','installed_external_callsite_admission_verified',
                     'native_receiver_validity_verified','native_argument_validity_verified',
                     'standalone_native_callsite_replacement_safe','physical_only_clip_admission_verified'):
            self.assertIs(ast.literal_eval(values[name]),False,name)
        limitations=ast.literal_eval(values['limitations'])
        self.assertTrue(any('does not stop frozen V2' in item for item in limitations))
        self.assertTrue(any('cannot replace native callsites on their own' in item for item in limitations))
        self.assertTrue(any('before normal return' in item for item in limitations))

    def test_fixed_private_sources_ignore_loaded_public_aliases(self):
        plan,parent,expected = emit()
        snapshot = lease._snapshot()
        before = set(sys.modules)
        with patch.object(field,"_emit_code",side_effect=AssertionError("public field alias")), \
             patch.object(clip,"_Assembler",side_effect=AssertionError("public assembler")), \
             patch.dict(lease.DESCRIPTOR,{"loss":4096}):
            with lease._modules(snapshot) as private:
                tool = private[lease.SOURCE]
                actual = tool._emit_code(plan,parent,assembler_module=private["src/patcher/partial_tile_clip.py"])
        for name in expected.__dict__:
            left,right=getattr(actual,name),getattr(expected,name)
            if name == "relocations":
                left,right=([row.__dict__ for row in left],[row.__dict__ for row in right])
            self.assertEqual(left,right,name)
        self.assertEqual(set(sys.modules),before)

    def test_pure_admission_rejects_changed_field_frames_calls_and_pages(self):
        plan,parent,_ = emit()
        for change in ("code","prologue","calls","private","state","page","reservation","resolution"):
            bad_plan,bad = deepcopy(plan),parent
            if change == "code": bad = replace(parent,code=b"")
            elif change == "prologue":
                raw=bytearray(parent.code); raw[dict(parent.entries)["draw_full"]-parent.base_va+5] ^= 1
                bad=replace(parent,code=bytes(raw))
            elif change == "calls": bad=replace(parent,relocations=tuple(row for row in parent.relocations if row.target != oracle.TILE))
            elif change == "private": bad=replace(parent,private_entries=parent.private_entries[:2])
            elif change == "state": bad=replace(parent,state_va=parent.state_va+4)
            elif change == "page": bad_plan["rw"]["page_bytes"]=128
            elif change == "reservation": bad_plan["rx"]["virtual_reservation"]*=2
            else: bad_plan["resolution"]="802x602"
            with self.subTest(change=change),self.assertRaises(ValueError):
                lease._emit_code(bad_plan,bad,assembler_module=clip)
        for original in (b"",bytearray()):
            with self.assertRaises(ValueError): lease.emit_battle_profile_stack_lease(original,"classic","1024x768")

    def test_all36_layout_budget_and_actual_call_operand_inventory(self):
        for profile in oracle.PROFILES:
            for resolution in oracle.RESOLUTIONS:
                with self.subTest(profile=profile,resolution=resolution):
                    plan,parent,emitted=emit(profile,resolution)
                    self.assertEqual(tuple(dict(emitted.entries)),PUBLIC)
                    self.assertEqual(emitted.base_va,(parent.base_va+len(parent.code)+15)&~15)
                    self.assertEqual(emitted.field_return_pcs,tuple(
                        (0 if row.offset+parent.base_va < dict(parent.entries)["draw_incremental"] else 1,
                         parent.base_va+row.offset+4) for row in parent.relocations if row.target == oracle.TILE))
                    self.assertLessEqual(emitted.base_va+len(emitted.code),plan["rx"]["va"]+0x20000)
                    offsets=set()
                    for row in emitted.relocations:
                        self.assertNotIn(row.offset,offsets); offsets.add(row.offset)
                        if row.kind == "abs32": self.assertEqual(struct.unpack_from("<I",emitted.code,row.offset)[0],row.target)
                        else:
                            self.assertEqual(row.kind,"rel32"); self.assertEqual(emitted.code[row.offset-1],0xE8)
                            self.assertEqual(emitted.base_va+row.offset+4+struct.unpack_from("<i",emitted.code,row.offset)[0],row.target)

    def test_complete_native_ret_operands_and_call_ledgers_reject_changed_final_bytes(self):
        # Authored minimal ABI fixture contains no original native body.
        raw=bytearray(0x40000)
        for va,pop in lease.NATIVE_RET_ABI:
            value=b"\xC2"+struct.pack("<H",pop) if pop else b"\xC3"
            raw[va-0x400000:va-0x400000+len(value)]=value
        for _,pc,_,_,target,slot in lease.NATIVE_CALL_ABI:
            value=(b"\xE8"+struct.pack("<i",target-pc)) if target is not None else bytes((0xFF,0x50,slot))
            raw[pc-len(value)-0x400000:pc-0x400000]=value
        fixture=bytes(raw)
        mapper=SimpleNamespace(file_offset=lambda image,va,count:va-0x400000)
        contract=lease._authenticate_native_abi(fixture,fixture,mapper)
        self.assertEqual(len(contract["calls"]),36)
        self.assertEqual(len(contract["returns"]),10)
        positions=[va-0x400000+(2 if pop else 0) for va,pop in lease.NATIVE_RET_ABI]
        positions += [pc-0x400001 for _,pc,_,_,_,_ in lease.NATIVE_CALL_ABI]
        for at in positions:
            bad=bytearray(fixture); bad[at]^=1
            with self.subTest(offset=at),self.assertRaises(ValueError):
                lease._authenticate_native_abi(fixture,bytes(bad),mapper)


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools=oracle.lifetime_fixture.machine_tools()
        if cls.tools is None: raise unittest.SkipTest("Unicorn unavailable; --require-machine-tools fails closed")

    def make(self,profile="classic",resolution="1024x768",delta=0,*,columns=1,scroll=0,mode=0):
        verify_frozen()
        return Machine(self.tools,profile,resolution,delta).prepare(columns=columns,scroll=scroll).begin(
            mode,eax=scroll,edx=0)

    def decode_without_execution(self,emission,delta=0):
        # Unicorn supplies decoded lengths; the hook advances EIP before every
        # instruction executes. Only newly authored emitted code is mapped.
        u,r=self.tools; cpu=u.Uc(u.UC_ARCH_X86,u.UC_MODE_32)
        code=bytearray(emission.code)
        for row in emission.relocations:
            if row.kind == "abs32": struct.pack_into("<I",code,row.offset,row.target+delta)
        start=emission.base_va+delta; page=start&~0xFFF
        cpu.mem_map(page,(start+len(code)-page+0xFFF)&~0xFFF)
        cpu.mem_write(start,bytes(code)); records=[]
        def skip(machine,address,size,data):
            records.append((address,bytes(machine.mem_read(address,size))))
            machine.reg_write(r.UC_X86_REG_EIP,address+size)
        cpu.hook_add(u.UC_HOOK_CODE,skip)
        cpu.emu_start(start,start+len(code),count=len(code))
        self.assertEqual(sum(len(raw) for _,raw in records),len(code))
        return records

    def test_independent_decode_accounts_for_every_absolute_and_direct_call_and_private_target(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                plan,parent,emitted=emit(profile,"3840x2160")
                instructions=self.decode_without_execution(emitted,delta)
                starts={at for at,_ in instructions}
                absolute=set(); calls={}; internal=[]
                for at,raw in instructions:
                    offset=at-emitted.base_va-delta
                    if raw[0] in (0xE8,0xE9) and len(raw) == 5:
                        target=at+5+struct.unpack_from("<i",raw,1)[0]
                        if raw[0] == 0xE8: calls[offset+1]=target-delta
                        if emitted.base_va+delta <= target < emitted.base_va+delta+len(emitted.code): internal.append(target)
                    elif len(raw) == 6 and raw[:1] == b"\x0F" and 0x80 <= raw[1] <= 0x8F:
                        internal.append(at+6+struct.unpack_from("<i",raw,2)[0])
                    position=None
                    if 0xB8 <= raw[0] <= 0xBF and len(raw) == 5: position=1
                    elif raw[0] == 0x81 and len(raw) == 6 and raw[1]>=0xF8: position=2
                    elif raw[0] == 0x8B and len(raw) == 6 and raw[1]&0xC7 == 5: position=2
                    elif raw[:2] == b"\xFF\x15" and len(raw) == 6: position=2
                    if position is not None:
                        value=struct.unpack_from("<I",raw,position)[0]-delta
                        if 0x400000 <= value < 0x600000 or plan["rx"]["va"] <= value <= plan["rx"]["va"]+0x21000:
                            absolute.add(offset+position)
                self.assertEqual(absolute,{row.offset for row in emitted.relocations if row.kind == "abs32"})
                self.assertEqual(calls,{row.offset:row.target for row in emitted.relocations if row.kind == "rel32"})
                self.assertTrue(all(target in starts for target in internal))
                parent_instructions=self.decode_without_execution(parent,delta)
                tile_pcs=tuple(at+5-delta for at,raw in parent_instructions if raw[0] == 0xE8
                    and len(raw) == 5 and at+5+struct.unpack_from("<i",raw,1)[0] == oracle.TILE+delta)
                self.assertEqual(tile_pcs,tuple(pc for _,pc in emitted.field_return_pcs))
                for _,entry in parent.entries:
                    prefix=[len(raw) for at,raw in parent_instructions if entry+delta <= at < entry+delta+11]
                    self.assertEqual(prefix,[1,1,1,6,2])

    def test_incremental_entry_and_root_bounds_reject_without_unbalanced_returns(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                m=self.make(profile,delta=delta,columns=2,mode=1)
                self.assertEqual(m.lease_word("mode"),1)
                result,_,_=m.invoke_leaf("sprite_charge_adjacent",guarded=True)
                self.assertEqual(result["EAX"],0xC0FFEE11)
                self.assertEqual(m.complete()["EAX"],1)
                self.assertEqual(m.tiles,[(0,0)])
                m=self.make(profile,delta=delta)
                for root in (0,3,0x10000,0x7FFF0000,m.ROOT_SP+1,m.field_frame+4,m.ROOT_SP-4):
                    m.set_state("root_esp",root)
                    result,_,_=m.invoke_leaf("sprite_tile",guarded=True)
                    self.assertEqual(result["EAX"],0)
                    self.assert_no_dynamic_reads(m)
                    self.assertEqual(m.closures,[])
                    m.set_state("root_esp",m.ROOT_SP)

    def test_all36_two_bases_native_size_pixels_and_outer_abi(self):
        for profile in oracle.PROFILES:
            for resolution in oracle.RESOLUTIONS:
                width,_=map(int,resolution.split("x")); visible=min(20,(width-192)//64); scroll=20-visible
                for delta in (0,0x100000):
                    with self.subTest(profile=profile,resolution=resolution,delta=delta):
                        m=self.make(profile,resolution,delta,columns=20,scroll=scroll)
                        before=m.pixels(); state=m.record()
                        result,registers,_=m.invoke_leaf("tile")
                        self.assertEqual(result["EAX"],1)
                        self.assertEqual(result["EFLAGS"] & m.MASK,0xED7 & m.MASK)
                        for name,value in registers.items():
                            if name not in ("EAX","ESP"): self.assertEqual(result[name],value)
                        self.assertEqual(m.complete()["EAX"],1)
                        self.assertEqual(m.record(),state)
                        self.assertEqual(m.pixels(),oracle.expected_pixels(m.width,m.height,20,scroll,before))

    def test_every_family_ancestry_argument_copy_native_eax_flags_and_closure_once(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                for path in PATHS:
                    with self.subTest(profile=profile,delta=delta,path=path):
                        m=self.make(profile,delta=delta)
                        guarded=path.startswith("sprite") or path == "line"
                        actual,before,args=m.invoke_leaf(path,guarded=guarded)
                        self.assertEqual(actual["EAX"],0xC0FFEE11 if guarded else 1)
                        self.assertEqual(actual["EBP"],before["EBP"])
                        self.assertEqual(actual["ESI"],before["ESI"])
                        self.assertEqual(actual["EDI"],before["EDI"])
                        self.assertEqual(actual["EFLAGS"] & m.MASK,(0x247 if guarded else 0xED7) & m.MASK)
                        if guarded:
                            family="line" if path == "line" else "sprite"
                            self.assertEqual(m.closures,[family]); self.assertEqual(len(m.primitives),1)
                            self.assertEqual(m.primitives[0][1],args)
                            # Original ECX input, including Unit's x-offset,
                            # survives validation and is passed byte-for-byte.
                            self.assertEqual(m.primitives[0][2]["ECX"],before["ECX"])
                            self.assertEqual(m.lease_word("leaf_status"),1)
                            self.assertEqual(m.lease_word("leaves_called"),1)
                            self.assertEqual(m.lease_word("leaves_returned"),1)
                        else: self.assertEqual(m.closures,[])

    def test_every_fixed_native_return_site_and_nested_private_calls_has_balanced_abi(self):
        variants=(('unit',lease.TILE_UNIT_RETURNS),('unit_adjacent',lease.ADJACENT_UNIT_RETURNS),
                  ('sprite_tile',lease.TILE_SPRITE_RETURNS),('line',(0x430AD8,0x430B0A)))
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                m=self.make(profile,delta=delta)
                for path,sites in variants:
                    for pc in sites:
                        with self.subTest(profile=profile,delta=delta,path=path,pc=hex(pc)):
                            actual,_,_=m.invoke_leaf(path,guarded=path.startswith('sprite') or path=='line',
                                                     return_override=pc+delta)
                            self.assertEqual(actual['EAX'],0xC0FFEE11 if path.startswith('sprite') or path=='line' else 1)
                            self.assertEqual(m.lease_word('loss'),0)

    def test_every_callback_receipt_dword_rejects_instead_of_adopting_a_new_invocation(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                m=self.make(profile,delta=delta)
                points=[m.state_va+offset for offset in range(0,128,4)]
                points += [native.PRIMARY+delta+offset for offset in range(0,216,4)]
                if m.modal_va is not None: points += [m.modal_va+delta+offset for offset in range(0,128,4)]
                for pointer,count in ((m.PHYSICAL,188),(m.PRIVATE,188),(m.BACKEND,168)):
                    points += [pointer+offset for offset in range(0,count,4)]
                points += [m.WORLD+offset for offset in (800,804,808,812)]
                points += [pointer+delta for pointer in (0x5202E0,0x511230,0x5199D8,0x526994,0x526990,0x532048,lease.THREAD_IAT)]
                points += [m.lease_frame+offset for offset in range(0,192,4)]
                descriptor=bytes(m.cpu.mem_read(m.lease_frame,192))
                for boundary in ('thread','native_normal_return'):
                    for at in points:
                        with self.subTest(profile=profile,delta=delta,boundary=boundary,address=hex(at)):
                            old=m.word(at); begin=len(m.closures)
                            if boundary == 'thread':
                                m.mutation=lambda target,name: target.put(at,target.word(at)^1) if name=='thread' else None
                            else: m.primitive_mutation=lambda target,name: target.put(at,target.word(at)^1)
                            result,_,_=m.invoke_leaf('sprite_tracking_adjacent',guarded=True)
                            self.assertEqual(result['EAX'],0 if boundary=='thread' else 0xC0FFEE11)
                            self.assertEqual(len(m.closures),begin+(boundary!='thread'))
                            if boundary!='thread': self.assertEqual(m.lease_word('loss'),2)
                            m.mutation=m.primitive_mutation=None
                            m.put(at,old); m.cpu.mem_write(m.lease_frame,descriptor)

    def test_all_cached_pointer_pages_are_avoided_after_fixed_authority_loss(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                for boundary in ('thread','native_normal_return'):
                    for role in ('physical','native','backend','world'):
                        with self.subTest(profile=profile,delta=delta,boundary=boundary,role=role):
                            m=self.make(profile,delta=delta)
                            ptr=dict(physical=m.PHYSICAL,native=m.PRIVATE,backend=m.BACKEND,world=m.WORLD)[role]
                            def corrupt(target,name):
                                target.put(native.MAP+delta,0)
                                target.cpu.mem_protect(ptr,4096,target.u.UC_PROT_NONE)
                            if boundary=='thread':
                                m.mutation=lambda target,name: corrupt(target,name) if name=='thread' else None
                            else: m.primitive_mutation=corrupt
                            result,_,_=m.invoke_leaf('sprite_charge_adjacent',guarded=True)
                            self.assertEqual(result['EAX'],0 if boundary=='thread' else 0xC0FFEE11)
                            self.assertEqual(len(m.closures),boundary!='thread')

    def assert_no_dynamic_reads(self,m):
        protected=((m.PHYSICAL,m.PHYSICAL+188),(m.PRIVATE,m.PRIVATE+188),
                   (m.BACKEND,m.BACKEND+168),(m.WORLD,m.WORLD+0xF7C))
        self.assertFalse(any(at < end and at+size > start for at,size in m.reads
                             for start,end in protected),m.reads)

    def test_unknown_ancestry_and_misaligned_or_outside_frames_reject_before_cached_reads(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                m=self.make(profile,delta=delta)
                for path in PATHS:
                    with self.subTest(profile=profile,delta=delta,path=path):
                        actual,_,_=m.invoke_leaf(path,guarded=path.startswith("sprite") or path == "line",
                                                 return_override=m.STOP)
                        self.assertEqual(actual["EAX"],0)
                        self.assert_no_dynamic_reads(m)
                        self.assertEqual(m.closures,[])
                for sp in (m.ROOT_SP+0x100,m.ROOT_SP+0x101):
                    actual,_,_=m.invoke_leaf("tile",entry_sp=sp)
                    self.assertEqual(actual["EAX"],0)
                    self.assert_no_dynamic_reads(m)
                actual,_,_=m.invoke_leaf("tile",caller_ebp=m.field_frame+4)
                self.assertEqual(actual["EAX"],0)
                self.assert_no_dynamic_reads(m)
                actual,_,_=m.invoke_leaf("sprite_tracking_adjacent",guarded=True,
                                         tile_saved_ebp=m.field_frame+4)
                self.assertEqual(actual["EAX"],0)
                self.assert_no_dynamic_reads(m)

    def test_every_descriptor_field_and_live_return_slot_is_bound_before_native_call(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                m=self.make(profile,delta=delta)
                addresses=[m.lease_frame+offset for offset in lease.DESCRIPTOR.values()]
                addresses += [m.lease_frame+68,m.lease_frame+128,m.lease_frame+188,
                              m.field_frame+1288,m.field_frame+1316,m.lease_frame+200,m.lease_frame+228]
                for at in addresses:
                    with self.subTest(profile=profile,delta=delta,address=hex(at)):
                        old=m.word(at); m.put(at,old^4)
                        actual,_,_=m.invoke_leaf("sprite_tile",guarded=True)
                        self.assertEqual(actual["EAX"],0)
                        self.assert_no_dynamic_reads(m)
                        self.assertEqual(m.closures,[])
                        m.put(at,old)

    def test_thread_changed_descriptor_ancestors_and_globals_precede_poisoned_heap_reads(self):
        roles=("descriptor","outer_pc","outer_ebp","field_pc","field_ebp","tile_pc","tile_ebp",
               "owner","root","tid","map","render","primary","modal")
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                for role in roles:
                    if role == "modal" and profile in ("classic","framed"): continue
                    with self.subTest(profile=profile,delta=delta,role=role):
                        m=self.make(profile,delta=delta)
                        baseline=len(m.callbacks)
                        def mutate(target,name):
                            if name != "thread": return
                            if role == "descriptor": target.put(target.lease_frame+188,1)
                            elif role == "outer_pc": target.put(target.lease_frame+228,target.STOP+4)
                            elif role == "outer_ebp": target.put(target.lease_frame+200,0)
                            elif role == "field_pc": target.put(target.field_frame+1316,0)
                            elif role == "field_ebp": target.put(target.field_frame+1288,0)
                            elif role == "tile_pc": target.put(target.tile_sp,0)
                            elif role == "tile_ebp": target.put(target.tile_sp-20,0)
                            elif role == "owner": target.set_state("allocations",target.state("allocations")+1)
                            elif role == "root": target.set_state("root_esp",target.ROOT_SP+4)
                            elif role == "tid": target.thread_id+=1
                            elif role == "map": target.put(native.MAP+delta,0)
                            elif role == "render": target.put(native.RENDER+delta,target.PRIVATE)
                            elif role == "primary": target.put(native.PRIMARY+delta+0xBC,0)
                            else: target.put(target.modal_va+delta+68,1)
                            target.cpu.mem_protect(target.PHYSICAL,4096,target.u.UC_PROT_NONE)
                        m.mutation=mutate
                        actual,_,_=m.invoke_leaf("sprite_tracking_adjacent",guarded=True)
                        self.assertEqual(actual["EAX"],0)
                        self.assertEqual(m.callbacks[baseline:],["thread"])
                        self.assertEqual(m.primitives,[])
                        self.assertEqual(m.lease_word("leaves_called"),0)

    def test_native_normal_return_loss_preserves_actual_eax_and_never_retries_cleanup(self):
        roles=("descriptor","counter","outer_pc","outer_ebp","field_pc","tile_ebp","map","owner","tid")
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                for family in ("sprite_tile","line"):
                    for role in roles:
                        with self.subTest(profile=profile,delta=delta,family=family,role=role):
                            m=self.make(profile,delta=delta)
                            def mutate(target,name):
                                if role == "descriptor": target.put(target.lease_frame+68,7)
                                elif role == "counter": target.put(target.lease_frame+56,999)
                                elif role == "outer_pc": target.put(target.lease_frame+228,target.STOP+4)
                                elif role == "outer_ebp": target.put(target.lease_frame+200,0)
                                elif role == "field_pc": target.put(target.field_frame+1316,0)
                                elif role == "tile_ebp": target.put(target.tile_sp-20,0)
                                elif role == "map": target.put(native.MAP+delta,0)
                                elif role == "owner": target.set_state("allocations",target.state("allocations")+1)
                                else: target.thread_id+=1
                                target.cpu.mem_protect(target.PHYSICAL,4096,target.u.UC_PROT_NONE)
                            m.primitive_mutation=mutate
                            result,_,_=m.invoke_leaf(family,guarded=True)
                            self.assertEqual(result["EAX"],0xC0FFEE11)
                            self.assertEqual(result["EFLAGS"] & m.MASK,0x247 & m.MASK)
                            self.assertEqual(m.lease_word("loss"),2)
                            self.assertEqual(m.lease_word("leaf_status"),2)
                            expected="line" if family == "line" else "sprite"
                            self.assertEqual(m.closures,[expected])
                            if role == "counter": self.assertEqual(m.lease_word("leaves_returned"),999)
                            # A second pre-call denial cannot retry normal closure.
                            m.primitive_mutation=None
                            result,_,_=m.invoke_leaf(family,guarded=True)
                            self.assertEqual(result["EAX"],0)
                            self.assertEqual(m.closures,[expected])

    def test_repeated_leaf_success_and_explicit_unadapted_continuation_gap(self):
        for profile in oracle.PROFILES:
            for delta in (0,0x100000):
                m=self.make(profile,delta=delta,columns=2)
                state=m.record(); reserved=bytes(m.cpu.mem_read(m.lease_frame+68,124))
                for path in ("sprite_tracking_adjacent","line"):
                    native_s=m.tile_sp-sum(distance for distance,_ in PATHS[path])
                    # The wrapper also saves actual post-callee PUSHFD/PUSHAD
                    # outputs36B below its512B locals; leave that ABI scratch live.
                    below=native_s-548-64; above=native_s+4+lease.ARG_BYTES["line" if path == "line" else "sprite"]
                    m.cpu.mem_write(below,b"\xA9"*16); m.cpu.mem_write(above,b"\xA9"*16)
                    result,_,_=m.invoke_leaf(path,guarded=True)
                    self.assertEqual(result["EAX"],0xC0FFEE11)
                    self.assertEqual(bytes(m.cpu.mem_read(below,16)),b"\xA9"*16)
                    self.assertEqual(bytes(m.cpu.mem_read(above,16)),b"\xA9"*16)
                self.assertEqual(m.lease_word("leaves_called"),2)
                self.assertEqual(m.lease_word("leaves_returned"),2)
                self.assertEqual(bytes(m.cpu.mem_read(m.lease_frame+68,124)),reserved)
                self.assertEqual(m.record(),state)
                # Loss is visible only to the newly owning draw wrapper after
                # V2 returns. Frozen V2 has no lease-loss read: all14 Tiles run.
                m.put(m.lease_frame+44,2)
                self.assertEqual(m.complete()["EAX"],2)
                self.assertEqual(len(m.tiles),14)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-machine-tools",action="store_true")
    parser.add_argument("--original",type=Path)
    args,remaining=parser.parse_known_args()
    if args.require_machine_tools and oracle.lifetime_fixture.machine_tools() is None:
        parser.error("pinned Unicorn is required")
    if args.original:
        original=args.original.read_bytes(); before=hashlib.sha256(original).hexdigest()
        bundle=lease.emit_battle_profile_stack_lease(original,"classic","1024x768")
        assert bundle.hook_sites == () and bundle.removed_highlow_rvas == ()
        assert all(bundle.metadata()[claim] is False for claim in context.FALSE_CLAIMS)
        assert hashlib.sha256(args.original.read_bytes()).hexdigest() == before == lease.BASE_SHA256
        print("Original-backed uninstalled lease reconstruction PASS; original unchanged")
    unittest.main(argv=[sys.argv[0],*remaining])


if __name__ == "__main__": main()
