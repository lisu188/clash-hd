#!/usr/bin/env python3
"""Authored fresh request/continuation CPU contracts; no retail runtime.

Effect/native frames are explicit models. No sprite/provider is dereferenced,
populated or executed. Independent scalar and clipping oracles remain separate
from source issuance and prove no native lifetime, installation or full battle.
"""
from __future__ import annotations
import ast
from dataclasses import replace
import gc
import hashlib
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/"tools")]
from src.patcher import battle_profile_primitive_request_v2 as tool
import test_battle_profile_continuation_v2 as previous

MODEL = "tools/test_battle_profile_continuation_v2.py"
MODEL_SHA = "a6339649cf0064460c559ca96359ce7c1f73ecf4b653144ed4f218c6f2ac6d5e"
ROWS,HIGHLOW = previous.ROWS,previous.HIGHLOW
CACHE = {}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def emit(profile="classic",resolution="1920x1080"):
    key = profile,resolution
    if key not in CACHE:
        values = previous.parent.emit(profile,resolution)
        out = tool._raw_emit(values[0],values[3],values[4],values[5],values[6],values[7],*values[-3:],
            continuation=previous.tool,**previous.arguments())
        CACHE[key] = values,out
    return CACHE[key]


def source_closure():
    if sha((ROOT/MODEL).read_bytes()) != MODEL_SHA:
        raise ValueError("complete reviewed scalar fixture required")
    return previous.source_closure()|{name:sha((ROOT/name).read_bytes()) for name in
        (tool.SOURCE,"tools/test_battle_profile_primitive_request_v2.py")}


def prior_machine():
    raw = (ROOT/MODEL).read_bytes()
    if sha(raw) != MODEL_SHA:
        raise ValueError("complete reviewed scalar fixture differs")
    node = next(node for node in ast.parse(raw).body if isinstance(node,ast.ClassDef) and node.name == "Machine")
    proxy = SimpleNamespace(**(vars(previous.tool)|vars(tool)))
    proxy._join_field = previous.tool._join_field
    namespace = dict(vars(previous))|dict(emit=emit,tool=proxy,ROWS=ROWS,HIGHLOW=HIGHLOW)
    exec(compile(ast.get_source_segment(raw.decode(),node),str(ROOT/MODEL)+"#fresh_request_model","exec"),namespace)
    return namespace["Machine"]


class Machine(prior_machine()):
    def on_code(self,cpu,address,size,data):
        out = getattr(self,"continuation",None)
        if out is not None and address in {pc+self.delta for pc in out.request_returns}:
            sp = cpu.reg_read(self.regs["ESP"])
            self.request_records.append(struct.unpack("<16I",bytes(cpu.mem_read(sp+16,64))))
        super().on_code(cpu,address,size,data)

    def setup_request(self,index,*,arguments=None,tracking="early",final=True,identity=21):
        pc,kind,owner,delta,_ = tool.REQUEST_SITES[index]
        tracking_tile = owner == "tracking" and tracking == "tile"
        family = "tile" if owner == "tile" or tracking_tile else "unit"
        row = next(row for row in previous.parent.replay_fixture.native_content.SITES if row[2] == family)
        self.setup_body(row,index=identity,via_adjacent=family == "unit")
        if family == "unit":
            self.set_atomic_ancestry(caller=previous.parent.FINAL_RETURN if final else previous.parent.ORDINARY_RETURNS[0],identity=identity)
        ts,us = self.tile_sp,self.unit_sp
        if owner == "tile":
            source,ebp = ts-delta,ts-20
        elif owner == "unit":
            source,ebp = us-delta,us-12
            self.put(us-28,0xd7d7d7d7)
        elif owner == "tracking":
            effect = ts-92 if tracking_tile else us-88
            ret = 0x43087d if tracking_tile else 0x42fa7c if tracking == "late" else 0x42fbbd
            self.put(effect,ret+self.delta)
            self.put(effect-12,ts-20 if tracking_tile else us-12)
            self.put(effect-4,identity if tracking != "late" else 99)
            if not tracking_tile:
                self.put(us-28,31*identity if tracking == "late" else 0xd7d7d7d7)
            source,ebp = effect-delta,0x50ee24+self.delta
            self.effect_s = effect
        else:
            effect = us-100
            self.put(effect,0x42f932+self.delta);self.put(effect-12,us-12);self.put(effect-4,identity)
            self.put(us-28,0xd7d7d7d7)
            source,ebp = effect-delta,0
            self.effect_s = effect
        values = tuple(arguments if arguments is not None else
            ((0xffffffff,)*4+(0x11223344,0x55667788,0x99aabbcc) if kind == "sprite" else (100,0)))
        assert len(values) == (7 if kind == "sprite" else 2)
        for number,value in enumerate(values):self.put(source+4+4*number,value)
        if owner == "charge":ebp = values[1]
        regs = dict(EAX=self.PHYSICAL,ECX=20 if kind == "sprite" else 100,
            EDX=0xdeadbeef if kind == "sprite" else 40,EBX=40 if kind == "sprite" else 20,
            EBP=ebp,ESI=identity if owner == "unit" else 0x778899aa,EDI=0x99aabbcc,ESP=source+4)
        self.request_s,self.request_args = source,values
        return regs

    def invoke_request(self,index,regs,*,wrong_pc=False):
        pc = tool.REQUEST_SITES[index][0]+self.delta if not wrong_pc else 0x401100+self.delta
        target = dict(self.continuation.entries)["request_"+str(index)]+self.delta
        self.cpu.mem_write(pc,b"\xe8"+struct.pack("<i",target-pc-5)+b"\x90")
        self.cpu.ctl_remove_cache(pc,pc+6)
        self.stops,self.native_stop,self.unsafe,self.active_scan = {pc+5},None,False,None
        self.request_records = []
        self.content_reads,self.content_writes,self.content_events = [],[],[]
        self.content_after_thread,self.content_active = False,True
        self.before_callbacks = len(self.callbacks)
        self.minimum_sp = regs["ESP"]
        for name,value in regs.items():self.cpu.reg_write(self.regs[name],value&0xffffffff)
        self.cpu.reg_write(self.regs["EFLAGS"],0xed7)
        try:self.cpu.emu_start(pc,self.STOP+1,count=3000000)
        finally:self.content_active = False
        return {name:self.cpu.reg_read(reg) for name,reg in self.regs.items()}


def sprite_oracle(arguments,right):
    signed = lambda value:value if value < 0x80000000 else value-0x100000000
    bounds = tuple(signed(value) for value in arguments[:4])
    if bounds == (-1,)*4:return tool.PREPARED,(32,16,right,463)
    left,top,end,bottom = bounds
    if left > end or top > bottom:return tool.MALFORMED,bounds
    bounds = max(32,left),max(16,top),min(right,end),min(463,bottom)
    return (tool.EMPTY if bounds[0] > bounds[2] or bounds[1] > bounds[3] else tool.PREPARED),bounds


class SourceTests(unittest.TestCase):
    def test_selected12_whole_instruction_operands_capacity_and_no_native_primitive_target(self):
        import capstone
        for profile in previous.tool.PROFILES:
            for resolution in previous.tool.RESOLUTIONS:
                with self.subTest(profile=profile,resolution=resolution):
                    values,out = emit(profile,resolution)
                    self.assertEqual(out.base_va,(values[-1].base_va+len(values[-1].code)+15)&~15)
                    self.assertEqual(len(out.entries),58);self.assertEqual(len(out.request_returns),13)
                    self.assertEqual(tuple(row[0] for row in out.planned_hooks),tuple(row[0] for row in ROWS))
                    self.assertLessEqual(out.base_va+len(out.code),values[0].rx.va+values[0].rx.size)
                    declared = {row.offset:row for row in out.relocations}
                    self.assertEqual(len(declared),len(out.relocations))
                    instructions = previous.disassemble(out);starts = {ins.address for ins in instructions}
                    fields = set()
                    for ins in instructions:
                        for operand in ins.operands:
                            if operand.type == capstone.x86.X86_OP_MEM and operand.mem.base == operand.mem.index == 0:
                                at = ins.address-out.base_va+ins.disp_offset;fields.add(at)
                                self.assertEqual((declared[at].kind,declared[at].target),("abs32",operand.mem.disp&0xffffffff))
                        if ins.group(capstone.CS_GRP_JUMP) or ins.group(capstone.CS_GRP_CALL):
                            if ins.operands[0].type == capstone.x86.X86_OP_IMM:
                                at = ins.address-out.base_va+ins.imm_offset;fields.add(at)
                                self.assertEqual((declared[at].kind,declared[at].target),("rel32",ins.operands[0].imm&0xffffffff))
                        for at in range(ins.address-out.base_va,ins.address-out.base_va+ins.size):
                            if at not in declared or at in fields:continue
                            self.assertEqual((at,declared[at].kind),(ins.address-out.base_va+ins.imm_offset,"abs32"))
                            self.assertEqual(ins.imm_size,4);fields.add(at)
                    self.assertEqual(fields,set(declared))
                    for row in out.relocations:
                        self.assertNotIn(row.target,(0x402e80,0x403f70))
                        if row.kind == "rel32" and out.base_va <= row.target < out.base_va+len(out.code):self.assertIn(row.target,starts)
                    self.assertTrue(all(va in starts for _,va in out.entries+out.private_entries))

    def test_private_source_boundary_and_mutable_public_alias_rejection(self):
        self.assertEqual(sha((ROOT/tool.PARENT).read_bytes()),tool.PARENT_SHA)
        with patch.object(tool,"_issue",side_effect=AssertionError("mutable public issuer used")):
            for value in (b"",b"synthetic PE",bytearray(b"synthetic PE"),None):
                with self.assertRaisesRegex(ValueError,"exact fresh primitive request original"):
                    tool.emit_primitive_request_v2(value,"classic","1920x1080")


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous.CPUTests.setUpClass();cls.tools = previous.CPUTests.tools

    def make(self,profile="classic",resolution="1920x1080",delta=0,mode=0):
        return Machine(self.tools,profile,resolution,delta).prepare(columns=2).begin(mode)

    def assert_request(self,m,index,regs):
        before = bytes(m.cpu.mem_read(m.request_s+4,len(m.request_args)*4))
        actual = m.invoke_request(index,regs)
        self.assertFalse(m.unsafe);self.assertEqual(actual["EDX"],tool.PREPARED)
        for name,value in regs.items():
            if name != "EDX":self.assertEqual(actual[name],value&0xffffffff,(index,name))
        self.assertEqual(actual["EFLAGS"]&m.MASK,0xed7&m.MASK)
        self.assertEqual(bytes(m.cpu.mem_read(m.request_s+4,len(m.request_args)*4)),before)
        self.assertEqual(m.callbacks[m.before_callbacks:],["thread"])
        self.assertEqual(len(m.request_records),1)
        record = m.request_records[0]
        self.assertEqual(record[:3],(tool.TAG,tool.SCHEMA,64));self.assertEqual(record[15],tool.PREPARED)
        self.assertEqual(record[5],m.PHYSICAL)
        self.assertLessEqual(regs["ESP"]-m.minimum_sp,tool.HELPER_BYTES+204)
        for va,raw in m.loaded_code:self.assertEqual(bytes(m.cpu.mem_read(va,len(raw))),raw)
        return record

    def test_all13_effect_phases_bases_modes_and_frozen43_scalar_parity(self):
        for delta in (0,0x30000):
            for mode in (0,1):
                m = self.make(delta=delta,mode=mode)
                for va,_,_ in ROWS:
                    regs = m.setup_post(va)
                    expected,flags = m.scalar_baseline(va,regs,0xed7)
                    actual,observed = m.invoke_post(va,regs)
                    self.assertFalse(m.unsafe,hex(va));self.assertEqual(actual,expected,hex(va))
                    self.assertEqual(observed&m.MASK,flags&m.MASK)
                for index in range(13):
                    for phase in (("early","late","tile") if index == 9 else ("early",)):
                        regs = m.setup_request(index,tracking=phase)
                        self.assert_request(m,index,regs)
                del m;gc.collect()

    def test_selected12_all13_queries_and_all43_normal_returns_bases_modes(self):
        for profile in previous.tool.PROFILES:
            for resolution in previous.tool.RESOLUTIONS:
                for delta in (0,0x30000):
                    for mode in (0,1):
                        with self.subTest(profile=profile,resolution=resolution,delta=delta,mode=mode):
                            m = self.make(profile,resolution,delta,mode)
                            for va,_,_ in ROWS:
                                regs = m.setup_post(va)
                                expected,flags = m.scalar_baseline(va,regs,0xed7)
                                actual,observed = m.invoke_post(va,regs)
                                self.assertFalse(m.unsafe,hex(va));self.assertEqual(actual,expected,hex(va))
                                self.assertEqual(observed&m.MASK,flags&m.MASK)
                            for index in range(13):self.assert_request(m,index,m.setup_request(index))
                            del m;gc.collect()

    def test_sprite_bounds_and_line_uint16_statuses(self):
        m = self.make()
        right = 31+2*64
        cases = ((0xffffffff,)*4,(0,0,100,100),(32,16,32,16),(33,16,32,463),
            (0x80000000,0x80000000,0x7fffffff,0x7fffffff),(0xffffffff,16,100,463),
            (0,0,31,15),(32,464,1000,500),(2000,16,3000,463),(32,16,0xffffffff,463))
        for bounds in cases:
            values = bounds+(0x11223344,0x55667788,0x99aabbcc)
            regs = m.setup_request(0,arguments=values)
            actual = m.invoke_request(0,regs);status,expected = sprite_oracle(values,right)
            self.assertEqual(actual["EDX"],status)
            record = m.request_records[-1]
            if status in (tool.PREPARED,tool.EMPTY):self.assertEqual(record[8:12],tuple(value&0xffffffff for value in expected))
            self.assertEqual(record[12:15],values[4:]);self.assertEqual(record[15],status)
        for index in (11,12):
            regs = m.setup_request(index,arguments=(20,0x100))
            regs.update(EDX=40,EBX=20,ECX=40)
            actual = m.invoke_request(index,regs)
            self.assertEqual(actual["EDX"],tool.EMPTY)

    def test_saved_effect_identity_arguments_and_callback_control_loss_before_cached_reads(self):
        for index,field in ((9,"saved_esi"),(9,"saved_ebp"),(10,"saved_esi"),(10,"argument"),(0,"argument"),(11,"argument")):
            with self.subTest(index=index,field=field):
                m = self.make("modalwidgets",resolution="3840x2160",delta=0x30000)
                regs = m.setup_request(index)
                def corrupt(mm,name):
                    if name != "thread":return
                    address = mm.effect_s-4 if field == "saved_esi" else mm.effect_s-12 if field == "saved_ebp" else mm.request_s+4
                    mm.put(address,mm.word(address)^1)
                    mm.protect_cached(mm.u.UC_PROT_NONE)
                m.mutation = corrupt
                with self.assertRaises(self.tools[0].UcError):m.invoke_request(index,regs)
                self.assertIn(m.cpu.reg_read(m.regs["EIP"]),m.unsafe_vas)
                self.assertEqual(m.cached_reads(post_thread=True),[])
                self.assertEqual(m.request_records,[])
                del m;gc.collect()


def run_tests():
    before = source_closure()
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in (SourceTests,CPUTests))
    count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if before != source_closure():raise ValueError("fresh request source closure changed")
    if not result.wasSuccessful() or result.skipped or result.testsRun != count:raise AssertionError("fresh request contract failures")
    return count


if __name__ == "__main__":
    if len(sys.argv) > 1:unittest.main()
    else:run_tests()
