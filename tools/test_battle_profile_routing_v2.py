#!/usr/bin/env python3
"""Fresh routing source/Unicorn models only; no game, capture or disk outputs.

Callbacks and byte-pattern buffers are synthetic. Default executes source and
bounded CPU paths; --source-only omits CPU. Optional --original-backed is an
explicit, separate canonical reconstruction in RAM, never native execution.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from dataclasses import asdict, replace
import gc
import hashlib
from pathlib import Path
import random
import struct
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"tools")]
from src.patcher import battle_profile_routing_v2 as tool
from src.patcher import battle_profile_routing as frozen
from src.patcher import battle_profile_lifecycle_v2 as life
from src.patcher import battle_profile_lifecycle as oldlife
from src.patcher import battle_profile_context_v2 as context
from src.patcher import partial_tile_clip as clip
from src.patcher import framed_modal_canvas as native
import test_battle_profile_lifecycle_v2 as lifetime
import test_battle_profile_routing as previous
ORIGINAL=None
CACHE={}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

@contextmanager
def issuer():
    raw=(ROOT/tool.SOURCE).read_bytes()
    name="_routing_v2_synthetic_"+uuid.uuid4().hex
    module=ModuleType(name); module.__file__=str(ROOT/tool.SOURCE)
    module.__loaded_source_sha256__=sha(raw); module.__canonical_routing_v2_issuer__=True
    assert sys.modules.setdefault(name,module) is module
    try:
        exec(compile(raw,module.__file__,"exec"),module.__dict__)
        yield module
    finally:
        assert sys.modules.get(name) is module
        del sys.modules[name]

def emit(profile="classic",resolution="1024x768",fresh=False):
    key=(profile,resolution)
    if not fresh and key in CACHE: return CACHE[key]
    layout=lifetime.synthetic_layout(profile,resolution)
    parent=lifetime.emission(layout)
    out=tool._emit_code(layout,parent,template_source=(ROOT/tool.TEMPLATE).read_bytes(),
        template_module=frozen,lifecycle_module=life,
        lifecycle_template_source=(ROOT/tool.LIFE_TEMPLATE).read_bytes(),
        lifecycle_template_module=oldlife,assembler_module=clip)
    result=layout,parent,out
    if not fresh: CACHE[key]=result
    return result

def decode(code):
    """Independent fixture decoder; not the producer's typed inventory."""
    rows=[]; cursor=0
    while cursor < len(code):
        start=cursor; absolute=[]; relative=[]; opcode=code[cursor]; cursor+=1
        if opcode in (0x9c,0x9d,0x60,0x61,0xfc,0xc3,0x40,0x48,0x4a):
            pass
        elif opcode == 0xf3:
            assert code[cursor] in (0xaf,0xa4); cursor+=1
        elif opcode in range(0xb8,0xc0) or opcode == 0x3d:
            absolute.append((cursor,False)); cursor+=4
        elif opcode in (0xe8,0xe9):
            relative.append(cursor); cursor+=4
        elif opcode == 0x0f:
            sub=code[cursor]; cursor+=1
            if sub != 0x0b:
                assert sub in (0x82,0x83,0x84,0x85,0x87,0x88)
                relative.append(cursor); cursor+=4
        elif opcode in (0x81,0x83,0x8b,0x89,0x3b,0x39,0x85,0xf7,0xff,0x31,0x29):
            modrm=code[cursor]; cursor+=1; mode,rm=modrm>>6,modrm&7
            if mode != 3 and rm == 4:
                sib=code[cursor]; cursor+=1
                if mode == 0 and sib&7 == 5:
                    absolute.append((cursor,True)); cursor+=4
            if mode == 0 and rm == 5:
                absolute.append((cursor,True)); cursor+=4
            elif mode == 1: cursor+=1
            elif mode == 2: cursor+=4
            if opcode == 0x81 or opcode == 0xf7 and (modrm>>3)&7 == 0:
                absolute.append((cursor,False)); cursor+=4
            elif opcode == 0x83: cursor+=1
        else: raise AssertionError((hex(start),hex(opcode)))
        assert start < cursor <= len(code)
        rows.append((start,cursor,tuple(absolute),tuple(relative)))
    return rows

def scalar_spec(width,height,rx_rva):
    """Independent exact loop/offset values derived from visible edge mapping."""
    columns=[min(448,width-160-x) for x in range(32,width-160,448)]
    widths={32,16,160,*columns}
    heights={16,368,112}
    heights.update(min(448,height-16-y) for y in range(16,height-16,448))
    heights.update(min(352,height-112-y) for y in range(368,height-112,352))
    esi={0,16*640,464*640,32,464*640+32,16*640+624,480,368*640+480}
    esi.update(640-count for count in widths)
    edi={0,(height-16)*width,width-160,(height-112)*width+width-160}
    edi.update(y*width for y in range(16,height-16,448))
    edi.update(x for x in range(32,width-160,448))
    edi.update((height-16)*width+x for x in range(32,width-160,448))
    edi.update(y*width+width-16 for y in range(368,height-112,352))
    edi.update(width-count for count in widths)
    sizes={188,width*height,307200,168,3964,rx_rva,262144,65536,4096}
    bounds={0x10000} | {0x80000000-n for n in (8,188,width*height,307200,168,3964,1)}
    cmp_scalars={0,1,2,7,8,width|(height<<16),640|(480<<16)}
    return widths,heights,esi,edi,sizes,bounds,cmp_scalars

def relocation_oracle(out,layout):
    rows=decode(out.code); starts={a for a,_,_,_ in rows}
    declared_abs={r.offset for r in out.relocations if r.kind == "abs32"}
    declared_rel={r.offset for r in out.relocations if r.kind == "rel32"}
    assert len(declared_abs)+len(declared_rel) == len(out.relocations)
    expected_abs=set(); expected_rel=set()
    w,h=map(int,layout.resolution.split("x"))
    widths,heights,esi,edi,sizes,bounds,cmp_scalars=scalar_spec(w,h,layout.rx.rva)
    modal=next((r.va for r in layout.protected_spans if r.role == "parent:.hdstate"),None)
    pointers={0x400000,layout.rx.va,layout.rw.va} | (set() if modal is None else {modal})
    zeros={layout.rw.va,layout.rw.va+128} | (set() if modal is None else {modal,modal+128})
    for start,end,absolute,relative in rows:
        opcode=out.code[start]
        for at,memory in absolute:
            value=struct.unpack_from("<I",out.code,at)[0]
            address=memory
            if not memory:
                if opcode == 0xbb: assert value in pointers; address=True
                elif opcode == 0xbf: assert value in zeros; address=True
                elif opcode == 0x3d: assert value == 0x51d4c0; address=True
                elif opcode == 0x81:
                    modrm=out.code[start+1]
                    if modrm == 0x3d:
                        target=struct.unpack_from("<I",out.code,start+2)[0]
                        if target == 0x5199d8: assert value == 0x42e8b0; address=True
                        elif target == layout.rw.va+68: assert value == 0x40ad40; address=True
                        elif target == 0x51d4c0+0xb8: assert value == 0x50eec4; address=True
                        else: assert value in cmp_scalars
                    elif modrm>>6 == 2:
                        offset=struct.unpack_from("<I",out.code,start+2)[0]
                        if offset == 0xb8: assert value == 0x50ee24; address=True
                        else: assert value in cmp_scalars
                    elif modrm == 0xc6: assert value in esi,(start,value)
                    elif modrm == 0xc7: assert value in edi,(start,value)
                    elif modrm == 0xc2: assert value in sizes,(start,value)
                    elif modrm in (0xc4,0xec): assert value == 1280
                    else: assert value in bounds,(start,hex(value),hex(modrm))
                elif opcode == 0xf7: assert value == 3
                elif opcode == 0xb8: assert value in (0,1,2)
                elif opcode == 0xb9: assert value in widths | {32,16352,992,(w-192)//64}
                elif opcode == 0xba: assert value in heights
                else: raise AssertionError((start,opcode,value))
            if address: expected_abs.add(at)
        for at in relative:
            expected_rel.add(at)
            target=out.base_va+at+4+struct.unpack_from("<i",out.code,at)[0]
            if out.base_va <= target < out.base_va+len(out.code):
                assert target-out.base_va in starts
            else: assert target in (0x42eb74,0x42ef77)
    assert declared_abs == expected_abs,(declared_abs-expected_abs,expected_abs-declared_abs)
    assert declared_rel == expected_rel
    typed=tool._operand_inventory(out,layout)
    assert {r.offset for r in typed if r.kind == "abs32"} == expected_abs
    assert {r.offset for r in typed if r.kind == "rel32"} == expected_rel
    assert all(va-out.base_va in starts for _,va in out.entries)
    for row in out.relocations:
        value=row.target if row.kind == "abs32" else row.target-out.base_va-row.offset-4
        assert struct.unpack_from("<I",out.code,row.offset)[0] == value&0xffffffff
    return len(rows),len(expected_abs),len(expected_rel)

class SourceTests(unittest.TestCase):
    def test_all36_deterministic_full_typed_operands_and_capacity(self):
        for profile in context.PROFILES:
            for resolution in context.RESOLUTIONS:
                with self.subTest(profile=profile,resolution=resolution):
                    layout,parent,out=emit(profile,resolution)
                    again=emit(profile,resolution,fresh=True)[2]
                    self.assertEqual(asdict(out),asdict(again))
                    self.assertGreaterEqual(out.base_va,parent.base_va+len(parent.code))
                    self.assertEqual(out.base_va%16,0)
                    self.assertLessEqual(out.base_va+len(out.code),layout.rx.va+262144)
                    self.assertEqual(tuple(dict(out.entries)),frozen.ENTRIES)
                    counts=relocation_oracle(out,layout)
                    self.assertGreater(counts[0],2000)
                    if resolution == "3440x1440":
                        scalars=[r for r in tool._operand_inventory(out,layout) if r.value == 4953600]
                        self.assertTrue(scalars)
                        self.assertTrue(all(r.kind == "scalar32" for r in scalars))

    def test_canonical_parent_layout_sources_and_operand_mutations_fail(self):
        layout,parent,out=emit("modalwidgets","1920x1080")
        kwargs=dict(template_source=(ROOT/tool.TEMPLATE).read_bytes(),template_module=frozen,
            lifecycle_module=life,lifecycle_template_source=(ROOT/tool.LIFE_TEMPLATE).read_bytes(),
            lifecycle_template_module=oldlife,assembler_module=clip)
        bad_parents=(replace(parent,code=parent.code[:-1]+bytes([parent.code[-1]^1])),
            replace(parent,entries=parent.entries[:-1]),
            replace(parent,relocations=parent.relocations[:-1]))
        for bad in bad_parents:
            with self.assertRaisesRegex(ValueError,"canonical lifecycle"):
                tool._emit_code(layout,bad,**kwargs)
        bad_layouts=(replace(layout,rx=replace(layout.rx,size=131072)),
            replace(layout,rw=replace(layout.rw,size=4096)),
            replace(layout,battle_state_va=layout.rw.va+256),
            replace(layout,provider_schema="invented"),
            replace(layout,protected_spans=layout.protected_spans[:-1]),
            replace(layout,resolution="802x602"))
        for bad in bad_layouts:
            with self.assertRaises(ValueError): tool._plan(bad)
        with self.assertRaises(ValueError):
            tool._versioned_template(kwargs["template_source"]+b"\n",frozen)
        for bad in (replace(out,relocations=out.relocations[:-1]),
                    replace(out,relocations=out.relocations+(out.relocations[0],)),
                    replace(out,entries=out.entries[:-1]+(("forged",out.base_va+1),))):
            with self.assertRaises(ValueError): tool._operand_inventory(bad,layout)
        scalar=next(r for r in tool._operand_inventory(out,layout)
            if r.kind == "scalar32" and r.role == "instruction_immediate")
        fake=clip.Relocation(scalar.offset,"abs32",scalar.value,"forged scalar as address")
        with self.assertRaisesRegex(ValueError,"address/scalar"):
            tool._operand_inventory(replace(out,relocations=out.relocations+(fake,)),layout)

    def test_private_pins_capture_aliases_and_source_read_rejections(self):
        with issuer() as own:
            snapshot=own._snapshot()
            with patch.dict(own.PINNED_SOURCES,{own.LIFECYCLE:"0"*64}):
                with self.assertRaisesRegex(ValueError,"source pin"): own._snapshot()
            real=Path.read_bytes
            with patch.object(Path,"read_bytes",lambda path:
                    b"#"+real(path)[1:] if path == ROOT/tool.SOURCE else real(path)):
                with self.assertRaisesRegex(ValueError,"closure changed"): own._unchanged(snapshot)
            with patch.object(Path,"is_symlink",lambda path: path == ROOT/tool.SOURCE):
                with self.assertRaisesRegex(ValueError,"reparse"): own._read(ROOT/tool.SOURCE,ROOT)
            with patch.object(Path,"read_bytes",lambda path: real(path)[:-1] if path == ROOT/tool.SOURCE else real(path)):
                with self.assertRaisesRegex(ValueError,"changed while read"): own._read(ROOT/tool.SOURCE,ROOT)
        captured=[cell.cell_contents for cell in tool.emit_routing_v2.__closure__]
        private=next(value for value in captured if callable(value) and getattr(value,"__name__",None) == "_issue")
        self.assertIsNot(private,tool._issue)
        self.assertTrue(private.__globals__["__canonical_routing_v2_issuer__"])
        def poison(*args,**kwargs):
            raise AssertionError("public producer alias called")
        with issuer() as own, patch.object(tool,"_emit_code",poison), \
             patch.object(life,"_emit_code",poison), patch.object(life,"_issue",poison), \
             patch.object(context,"build_allocation_context",poison):
            with own._modules(own._snapshot()) as modules:
                for name in (own.LIFECYCLE,own.CONTEXT,own.TEMPLATE):
                    self.assertEqual(modules[name].__loaded_source_sha256__,own.PINNED_SOURCES[name])
                self.assertIsNot(modules[own.LIFECYCLE]._issue,poison)
                self.assertIsNot(modules[own.LIFECYCLE]._emit_code,poison)
                self.assertIsNot(modules[own.CONTEXT].build_allocation_context,poison)
                layout=lifetime.synthetic_layout("classic","1024x768")
                # Invoke the captured pure CBC graph; no Original or game reads.
                out=modules[own.LIFECYCLE]._emit_code(layout,
                    template_source=own._snapshot()[own.LIFE_TEMPLATE][0],
                    template_module=modules[own.LIFE_TEMPLATE],assembler_module=modules[own.CLIP])
                self.assertEqual(out.state_va,layout.rw.va)
        for value in (b"",bytearray(),memoryview(b"")):
            with self.assertRaises(ValueError): tool.emit_routing_v2(value,"classic","1024x768")

    def test_forced_namespace_collisions_preserve_foreign_modules_and_attributes(self):
        token="b"*32
        names=("_battle_routing_v2_"+token,"_battle_routing_v2_"+token+".src",
            "_battle_routing_v2_"+token+".src.patcher",
            "_battle_routing_v2_"+token+".src.patcher.battle_profile_lifecycle_v2",
            "_battle_routing_v2_issuer_"+token)
        with issuer() as own:
            for name in names:
                foreign=ModuleType(name); foreign.preserved=object()
                before=dict(sys.modules); sys.modules[name]=foreign
                attributes=dict(foreign.__dict__)
                try:
                    with patch.object(uuid,"uuid4",return_value=SimpleNamespace(hex=token)):
                        with self.assertRaisesRegex(ValueError,"namespace occupied"):
                            if name.startswith("_battle_routing_v2_issuer"):
                                own._production_factory()
                            else:
                                with own._modules(own._snapshot()): pass
                    self.assertIs(sys.modules[name],foreign)
                    self.assertEqual(foreign.__dict__,attributes)
                    self.assertEqual(set(sys.modules),set(before)|{name})
                    self.assertTrue(all(sys.modules[key] is value for key,value in before.items()))
                finally: del sys.modules[name]
            snapshot=own._snapshot()
            for remove in (False,True):
                before=dict(sys.modules)
                with self.assertRaisesRegex(ValueError,"identity changed"):
                    with own._modules(snapshot) as modules:
                        target=modules[own.TEMPLATE].__name__
                        if remove: del sys.modules[target]
                        else: sys.modules[target]=foreign
                if not remove: self.assertIs(sys.modules.pop(target),foreign)
                self.assertEqual(set(sys.modules),set(before))

    def test_helper_frame_and_adapter_denial_instructions(self):
        for profile in context.PROFILES:
            layout,_,out=emit(profile)
            entries=dict(out.entries)
            for name in frozen.ENTRIES[:4]:
                at=entries[name]-out.base_va
                self.assertEqual(out.code[at:at+9],bytes.fromhex("9c60fc81ec00050000"))
            self.assertEqual(out.code[-2:],b"\x0f\x0b")
            for name in frozen.ENTRIES[4:]:
                lo=entries[name]-out.base_va
                hi=entries["initial_widgets_target"]-out.base_va if name == "initial_frame_target" else len(out.code)-2
                body=out.code[lo:hi]
                self.assertNotIn(bytes.fromhex("892d30125100"),body)
                self.assertIn(bytes.fromhex("619de9"),body)
                self.assertEqual(len([r for r in out.relocations if lo <= r.offset < hi and
                    r.target == out.base_va+len(out.code)-2]),1)

class Machine(lifetime.Machine):
    def __init__(self,tools,profile="classic",resolution="1024x768",delta=0):
        self.routing_active=False
        layout,parent,out=emit(profile,resolution)
        with patch.object(lifetime,"synthetic_layout",return_value=layout),patch.object(lifetime,"emission",return_value=parent):
            super().__init__(tools,profile,resolution,delta)
        self.routing_emission=out
        self.routing_entries={name:va+delta for name,va in out.entries}
        self.routing_unsafe=out.base_va+len(out.code)-2+delta
        raw=bytearray(out.code)
        for row in out.relocations:
            if row.kind == "abs32": struct.pack_into("<I",raw,row.offset,row.target+delta)
        self.cpu.mem_write(out.base_va+delta,bytes(raw))
        self.physical_write_count=0
        self.after_thread=False
        self.post_callback_heap_reads=0
        self.minimum_sp=self.SP

    def on_code(self,cpu,address,size,data):
        if self.routing_active:
            self.minimum_sp=min(self.minimum_sp,cpu.reg_read(self.regs["ESP"]))
            if address == self.routing_unsafe:
                self.native_stop=address; cpu.emu_stop(); return
            if address == self.THREAD: self.after_thread=True
        super().on_code(cpu,address,size,data)

    def on_read(self,cpu,access,address,size,value,data):
        if self.routing_active:
            if self.state_va+128 <= address and address+size <= self.state_va+65536:
                self.tail_reads+=1; return
            if self.modal_va is not None and self.modal_va+self.delta+128 <= address and address+size <= self.modal_va+self.delta+4096:
                return
            for lo,count in ((self.private_pixels,307200),(self.PHYSICAL_PIXELS,self.width*self.height)):
                if lo <= address < lo+count:
                    assert address+size <= lo+count
                    return
            if self.after_thread and any(lo <= address < lo+count for lo,count in (
                    (self.PHYSICAL,188),(self.PRIVATE,188),(self.BACKEND,168),(self.WORLD,3964))):
                self.post_callback_heap_reads+=1
        super().on_read(cpu,access,address,size,value,data)

    def on_write(self,cpu,access,address,size,value,data):
        if self.routing_active and self.PHYSICAL_PIXELS <= address < self.PHYSICAL_PIXELS+self.width*self.height:
            assert address+size <= self.PHYSICAL_PIXELS+self.width*self.height
            self.physical_write_count+=size
            return
        super().on_write(cpu,access,address,size,value,data)

    def prepare(self,bound=True):
        assert self.enter()["EAX"] == 1
        self.put(native.HOOK_OWNER+self.delta,0x42e8b0+self.delta)
        if bound: assert self.bind()["EAX"] == 1
        return self

    def invoke_routing(self,name,*,flags=0xed7,stop=None):
        self.routing_active=True; self.stops=set() if stop is None else {stop+self.delta}
        self.native_stop=None; self.writes=[]; self.reads=[]; self.tail_reads=0
        self.physical_write_count=0; self.after_thread=False; self.post_callback_heap_reads=0
        self.minimum_sp=self.SP; begin=len(self.callbacks)
        incoming_render=self.word(native.RENDER+self.delta)
        incoming=dict(EAX=0x12345678,ECX=0x11223344,EDX=0x22334455,EBX=0x33445566,
            ESP=self.SP,EBP=0x44556677,ESI=0x55667788,EDI=0x66778899)
        self.put(self.SP,self.STOP)
        for key,value in incoming.items(): self.cpu.reg_write(self.regs[key],value)
        self.cpu.reg_write(self.regs["EFLAGS"],flags)
        try: self.cpu.emu_start(self.routing_entries[name],self.STOP+1,count=3000000)
        finally: self.routing_active=False
        actual={key:self.cpu.reg_read(value) for key,value in self.regs.items()}
        adapter=name in frozen.ENTRIES[4:]
        end=self.STOP if not adapter else (self.routing_unsafe if stop is None else stop+self.delta)
        assert self.native_stop == end,(name,actual)
        if adapter and end == self.routing_unsafe:
            assert self.word(native.RENDER+self.delta) == incoming_render,(name,"unsafe render changed")
            assert not any(at == native.RENDER+self.delta for at,_ in self.writes)
            assert self.physical_write_count == 0,(name,"unsafe pixel write")
        for key,value in incoming.items():
            if adapter or key not in ("EAX","ESP"): assert actual[key] == value,(name,key,actual,value)
        if not adapter: assert actual["ESP"] == self.SP+4
        assert actual["EFLAGS"]&self.MASK == flags&self.MASK,(name,actual,flags)
        extent=4+self.SP-self.minimum_sp
        assert extent <= 2712,(name,extent)
        for address,size in self.writes:
            assert self.STACK <= address and address+size <= self.STACK+65536 or (
                address == native.RENDER+self.delta and size == 4),(name,address,size)
        assert bytes(self.cpu.mem_read(self.state_va+128,65536-128)) == self.tail_expected
        if self.modal_va is not None:
            assert bytes(self.cpu.mem_read(self.modal_va+self.delta,4096)) == self.modal_expected
        self.routing_callbacks=self.callbacks[begin:]
        return actual

    def records(self):
        regions=[(self.state_va,65536),(self.PHYSICAL,188),(self.PRIVATE,188),
            (self.BACKEND,168),(native.PRIMARY+self.delta,216),
            (self.private_pixels,307200)]
        if self.modal_va is not None: regions.append((self.modal_va+self.delta,4096))
        return tuple(bytes(self.cpu.mem_read(lo,size)) for lo,size in regions)

    def dispose(self):
        self.mutation=None; self.writes.clear(); self.reads.clear()
        self.callbacks.clear(); self.instruction_boundaries.clear()

class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: cls.tools=lifetime.prior_fixture.machine_tools()
        except ImportError as error: raise unittest.SkipTest(str(error))

    def machine(self,*args,**kwargs):
        return Machine(self.tools,*args,**kwargs)

    def test_all36_two_bases_virgin_prepared_bound_queries_and_both_adapters(self):
        for profile in context.PROFILES:
            for resolution in context.RESOLUTIONS:
                for delta in (0,0x2000000):
                    with self.subTest(profile=profile,resolution=resolution,delta=delta):
                        m=self.machine(profile,resolution,delta)
                        before=m.records(); render=m.word(native.RENDER+delta)
                        for name in frozen.ENTRIES[:4]:
                            self.assertEqual(m.invoke_routing(name)["EAX"],0)
                            self.assertEqual(m.routing_callbacks,[])
                            self.assertEqual(m.physical_write_count,0)
                        for name in frozen.ENTRIES[4:]: m.invoke_routing(name)
                        self.assertEqual(m.records(),before)
                        self.assertEqual(m.word(native.RENDER+delta),render)
                        m.prepare(bound=False)
                        self.assertEqual(m.invoke_routing("check_owned_prepared")["EAX"],1)
                        self.assertEqual(m.invoke_routing("check_owned_bound")["EAX"],2)
                        self.assertEqual(m.invoke_routing("target_hud")["EAX"],1)
                        self.assertEqual(m.bind()["EAX"],1)
                        self.assertEqual(m.invoke_routing("check_owned_bound")["EAX"],1)
                        for name,stop in (("initial_frame_target",0x42eb74),("initial_widgets_target",0x42ef77)):
                            m.invoke_routing(name,stop=stop)
                            self.assertEqual(m.word(native.RENDER+delta),m.PRIVATE)
                        m.dispose(); del m; gc.collect()

    def test_nine_geometries_exact_chrome_edges_sidebar_and_inert_pixels(self):
        source=random.Random(0xb4771e).randbytes(640*480)
        for index,resolution in enumerate(context.RESOLUTIONS):
            m=self.machine("modalwidgets",resolution,0x2000000 if index%2 else 0).prepare()
            before=bytes(m.cpu.mem_read(m.PHYSICAL_PIXELS,m.width*m.height))
            record=m.records()
            m.cpu.mem_write(m.private_pixels,source)
            expected=previous.expected_pixels(m.width,m.height,source,before)
            self.assertEqual(m.invoke_routing("compose_chrome")["EAX"],1)
            self.assertEqual(bytes(m.cpu.mem_read(m.PHYSICAL_PIXELS,m.width*m.height)),expected)
            self.assertGreater(m.physical_write_count,0)
            # Native pixels deliberately supplied above; record/header/state remain fixed.
            self.assertEqual(m.records()[:5],record[:5])
            self.assertTrue(all(name == "thread" for name in m.routing_callbacks))
            m.dispose(); del m; gc.collect()

    def test_exact_history_padding_tails_and_whole_protected_alias_rejections(self):
        m=self.machine("modalwidgets").prepare()
        original=bytes(m.cpu.mem_read(m.state_va,128))
        pixels=bytes(m.cpu.mem_read(m.PHYSICAL_PIXELS,m.width*m.height))
        for offset in range(0,128,4):
            m.cpu.mem_write(m.state_va,original); m.put(m.state_va,0); m.put(m.state_va+offset,1)
            self.assertEqual(m.invoke_routing("target_hud")["EAX"],2)
            self.assertEqual(m.physical_write_count,0)
            for name in frozen.ENTRIES[4:]: m.invoke_routing(name)
        m.cpu.mem_write(m.state_va,original)
        for offset in (128,4092,4096,32768,65532):
            m.mutate_tail(offset)
            self.assertEqual(m.invoke_routing("check_owned_bound")["EAX"],2)
            self.assertEqual(m.routing_callbacks,[])
            m.mutate_tail(offset,0)
        for offset in (128,4092):
            m.mutate_tail(offset,inherited=True)
            self.assertEqual(m.invoke_routing("check_owned_bound")["EAX"],2)
            m.mutate_tail(offset,0,inherited=True)
        pages=(m.layout.rx.va,m.layout.rx.va+262144-4,m.state_va,m.state_va+65536-4,
            m.modal_va,m.modal_va+4096-4)
        baseline_state=bytes(m.cpu.mem_read(m.state_va,128))
        baseline_primary=bytes(m.cpu.mem_read(native.PRIMARY,216))
        for pointer in pages:
            for kind in ("physical","backend","battle"):
                m.cpu.mem_write(m.state_va,baseline_state)
                m.cpu.mem_write(native.PRIMARY,baseline_primary)
                m.put(0x532048,m.WORLD)
                if kind == "physical": m.set_state("physical",pointer)
                elif kind == "backend":
                    m.put(native.PRIMARY+0xbc,pointer); m.set_state("saved_backend",pointer)
                else: m.set_state("battle",pointer); m.put(0x532048,pointer)
                self.assertEqual(m.invoke_routing("check_owned_bound")["EAX"],2)
                self.assertEqual(m.routing_callbacks,[])
        self.assertEqual(bytes(m.cpu.mem_read(m.PHYSICAL_PIXELS,m.width*m.height)),pixels)
        m.dispose()

    def test_complete_callback_record_and_tail_loss_before_cached_heap_reads(self):
        for delta in (0,0x2000000):
            m=self.machine("modalwidgets","1024x768",delta).prepare()
            state=bytes(m.cpu.mem_read(m.state_va,128))
            modal=bytes(m.cpu.mem_read(m.modal_va+delta,4096))
            for inherited in (False,True):
                for offset in range(0,128,4):
                    m.cpu.mem_write(m.state_va,state); m.cpu.mem_write(m.modal_va+delta,modal)
                    m.modal_expected=modal
                    def mutate(current,event):
                        if event == "thread":
                            at=(current.modal_va+delta if inherited else current.state_va)+offset
                            current.put(at,current.word(at)^1)
                            current.modal_expected=bytes(current.cpu.mem_read(current.modal_va+delta,4096))
                            current.cpu.mem_protect(current.PHYSICAL&~4095,4096,current.u.UC_PROT_NONE)
                    m.mutation=mutate
                    self.assertEqual(m.invoke_routing("check_owned_bound")["EAX"],2)
                    self.assertEqual(m.post_callback_heap_reads,0)
                    m.cpu.mem_protect(m.PHYSICAL&~4095,4096,m.u.UC_PROT_ALL)
                    for adapter in frozen.ENTRIES[4:]:
                        m.cpu.mem_write(m.state_va,state)
                        m.cpu.mem_write(m.modal_va+delta,modal); m.modal_expected=modal
                        m.invoke_routing(adapter)
                        self.assertEqual(m.routing_callbacks,["thread"])
                        self.assertEqual(m.post_callback_heap_reads,0)
                        m.cpu.mem_protect(m.PHYSICAL&~4095,4096,m.u.UC_PROT_ALL)
            for inherited,offset in ((False,128),(False,65532),(True,128),(True,4092)):
                m.cpu.mem_write(m.state_va,state); m.cpu.mem_write(m.modal_va+delta,modal)
                m.cpu.mem_write(m.state_va+128,bytes(65536-128))
                m.tail_expected=bytes(65536-128); m.modal_expected=modal
                def mutate(current,event):
                    if event == "thread":
                        current.mutate_tail(offset,inherited=inherited)
                        current.cpu.mem_protect(current.PHYSICAL&~4095,4096,current.u.UC_PROT_NONE)
                m.mutation=mutate
                self.assertEqual(m.invoke_routing("target_hud")["EAX"],2)
                self.assertEqual(m.post_callback_heap_reads,0)
                self.assertEqual(m.physical_write_count,0)
                m.cpu.mem_protect(m.PHYSICAL&~4095,4096,m.u.UC_PROT_ALL)
                for adapter in frozen.ENTRIES[4:]:
                    m.cpu.mem_write(m.state_va,state)
                    m.cpu.mem_write(m.state_va+128,bytes(65536-128))
                    m.cpu.mem_write(m.modal_va+delta,modal)
                    m.tail_expected=bytes(65536-128); m.modal_expected=modal
                    m.invoke_routing(adapter)
                    self.assertEqual(m.routing_callbacks,["thread"])
                    self.assertEqual(m.post_callback_heap_reads,0)
                    m.cpu.mem_protect(m.PHYSICAL&~4095,4096,m.u.UC_PROT_ALL)
            m.dispose(); del m; gc.collect()

class OriginalTests(unittest.TestCase):
    def test_canonical_original_parent_hook_bytes_offsets_and_false_claims(self):
        if ORIGINAL is None:
            self.skipTest("explicit optional Original RAM lane")
        raw=ORIGINAL.read_bytes(); self.assertEqual(sha(raw),tool.BASE_SHA256)
        result=tool.emit_routing_v2(raw,"modalwidgets","1920x1080")
        metadata=result.metadata()
        self.assertTrue(all(metadata[name] is False for name in tool.FALSE_CLAIMS))
        self.assertEqual(metadata["installed_hooks"],[])
        self.assertEqual(len(result.planned_hooks),2)
        self.assertEqual(result.removed_highlow_rvas,(0x2eb70,0x2ef73))
        self.assertEqual(metadata["provider_records_emitted"],0)
        self.assertIsNone(metadata["provider_capacity"])
        self.assertEqual(metadata["state_offsets"],frozen.STATE)
        parent=result.lifecycle_bundle.allocation_context
        for name,offset,va,old,new,target,fields in result.planned_hooks:
            self.assertEqual(parent.relayout_parent[offset:offset+len(old)],old)
            self.assertEqual(old,bytes.fromhex("892d30125100"))
            self.assertEqual(new[0],0xe9)
            self.assertEqual(va+5+struct.unpack_from("<i",new,1)[0],target)
        relocation_oracle(result.emission,parent.layout)
        self.assertEqual(sha(ORIGINAL.read_bytes()),tool.BASE_SHA256)

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-only",action="store_true")
    parser.add_argument("--original-backed",type=Path)
    args=parser.parse_args()
    ORIGINAL=args.original_backed
    loader=unittest.defaultTestLoader
    suite=unittest.TestSuite([loader.loadTestsFromTestCase(SourceTests)])
    if not args.source_only: suite.addTests(loader.loadTestsFromTestCase(CPUTests))
    if ORIGINAL is not None: suite.addTests(loader.loadTestsFromTestCase(OriginalTests))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print("uninstalled=True callbacks=modeled native_executed=False runtime_executed=False provider_lifetime_verified=False promotion_ready=False")
    raise SystemExit(not result.wasSuccessful())
