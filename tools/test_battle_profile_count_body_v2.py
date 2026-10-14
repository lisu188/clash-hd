#!/usr/bin/env python3
"""Independent source/scalar CPU fixture for uninstalled Count-body V2.

No original executable is opened and no original Count body executes here.
The native CALL frames, scalar tails and callbacks are authored models only.
The supported initial Adjacent -> Unit return is 42FCC4, never the separately
incompatible final 42FFA4 caller. Source/model checks are not native parity,
installation, cancellation, runtime, manual input or release acceptance.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, replace
import gc
import hashlib
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import battle_profile_count_body_v2 as tool
from src.patcher import battle_profile_count_entry as entry_tool
from src.patcher import partial_tile_clip as clip
import test_battle_profile_count_entry as entry_fixture

BODY_SHA256 = "b42d1724edb3eb6ba1a393884a8ceff0f590d61368fe438c4b003ad2997b1d8d"
ENTRY_FIXTURE_SHA256 = "b927ee3d1a0bf55f6ca46dfe4915adf9b60d783aec7c2a6d4f95cf75462da73c"
replay_fixture = entry_fixture.replay_fixture
observer = replay_fixture.tile_fixture.content_fixture
CONTEXT = observer.parent_fixture.context
SITES = tuple(row for row in replay_fixture.native_content.SITES if row[2] == "count")
WINDOWS = {0x426f44: bytes.fromhex("0fbf8c59fe05000083f9ff"),
           0x426f54: bytes.fromhex("8a9411560300003a5702")}
NEIGHBORS = ((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1))
CACHE = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def arguments():
    return dict(count_entry_module=entry_tool, count_entry_kwargs=entry_fixture.arguments(),
                content_module=replay_fixture.content_tool,
                template_module=replay_fixture.native_content, assembler_module=clip,
                template_source=(ROOT / tool.TEMPLATE).read_bytes())


def emit(profile="classic", resolution="800x600"):
    key = profile, resolution
    if key not in CACHE:
        prefix = entry_fixture.emit(profile, resolution)
        CACHE[key] = prefix + tool._emit_code(*prefix, **arguments())
    return CACHE[key]


def source_closure():
    previous = entry_fixture.source_closure()
    for name, digest in ((tool.SOURCE, BODY_SHA256),
                         ("tools/test_battle_profile_count_entry.py", ENTRY_FIXTURE_SHA256)):
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError("frozen Count-body fixture dependency differs: " + name)
    names = set(previous) | {tool.SOURCE, "tools/test_battle_profile_count_body_v2.py"}
    return {name: sha((ROOT / name).read_bytes()) for name in sorted(names)}


class Bytes:
    """Authored byte/operand oracle, independent of the producer assembler."""
    def __init__(self, base):
        self.base, self.code, self.fields = base, bytearray(), {}

    def raw(self, text):
        self.code.extend(bytes.fromhex(text))

    def word(self, value):
        self.code.extend(struct.pack("<I", value & 0xffffffff))

    def mark(self, at, kind, target, purpose):
        assert at not in self.fields
        self.fields[at] = kind, target, purpose

    def operand(self, kind, target, purpose):
        at = len(self.code)
        self.mark(at, kind, target, purpose); self.word(0)
        return at

    def finish(self):
        for at, (kind, target, _) in self.fields.items():
            struct.pack_into("<I", self.code, at, (target if kind == "abs32" else
                             target-self.base-at-4) & 0xffffffff)
        return bytes(self.code)


def independent_model(content, field, model):
    """Reconstruct from actual frozen ContentV2 bytes, not new source maps.

    Six retained source ranges surround five exact transformations; native
    return rows and first/shared EBP checks are anchored in canonical typed
    operands. Added Count-local extents, snapshot/match and DY helper are
    authored below. No new declared relocation supplies an absolute-field role.
    """
    original, parent = content.code, dict(content.private_entries)
    reloc = {r.offset: r for r in content.relocations}
    native = sorted((r for r in content.relocations if r.kind == "abs32" and
                     r.purpose == "fixed proposed body CALL return PC"), key=lambda r:r.offset)
    assert len(native) == 28 and tuple(r.target for r in native) == tuple(
        row[0]+5 for row in replay_fixture.native_content.SITES)
    ladder = [r.offset-26 for r in native]
    reject = reloc[ladder[0]+32].target
    for number, start in enumerate(ladder):
        row = original[start:start+41]
        assert row[:8] == bytes.fromhex("8b85c800000081f8")
        assert struct.unpack_from("<I", row, 8)[0] == number
        assert row[12:14] == b"\x0f\x85" and row[18:26] == bytes.fromhex("8b870000000081f8")
        assert struct.unpack_from("<I", row, 26)[0] == native[number].target
        assert row[30:32] == b"\x0f\x85" and row[36] == 0xe9
        for at, name in ((14,"site_receipt.next."+str(number)), (32,"admit.reject"),
                         (37,"site_receipt.matched")):
            assert reloc[start+at].kind == "rel32"
            assert reloc[start+at].purpose == "content_v2_internal:"+name
    assert all(right-left == 41 for left, right in zip(ladder, ladder[1:]))
    first_rows = [r for r in content.relocations if (r.kind,r.target,r.purpose) ==
                  ("abs32",0x42f95b,"draw-only native Count caller")]
    assert len(first_rows) == 1
    first = first_rows[0].offset+10
    assert original[first:first+18] == bytes.fromhex("89f981c1380000008b859801000039c80f85")
    assert reloc[first+18].target == reject
    # Find the exact shared Count fallback; no guessed numeric address scan.
    second_candidates = []
    for at in range(parent["admit_body"]-content.base_va, parent["fixed_receipt"]-content.base_va):
        if original[at:at+25] == bytes.fromhex("81f8030000000f84")+original[at+8:at+12]+bytes.fromhex(
                "8bbdd800000081c7f4ffffffe9"):
            second_candidates.append(at+12)
    assert len(second_candidates) == 1
    second = second_candidates[0]
    assert reloc[second+13].purpose == "content_v2_internal:ebp.compare"
    local_before = [r.offset-13 for r in content.relocations if r.kind == "rel32" and
        r.purpose == "content_v2_internal:ancestry.unit" and original[r.offset-13:r.offset] ==
        bytes.fromhex("8bbdd000000081c744000000e9")]
    assert len(local_before) == 1
    thread = [r for r in content.relocations if r.kind == "abs32" and
              r.purpose == "fixed content owning ThreadId callback"]
    assert len(thread) == 1
    post = [at for at in range(thread[0].offset+4,parent["fixed_receipt"]-content.base_va)
            if original[at:at+14] == bytes.fromhex("8b85000300003b85180000000f85")]
    assert len(post) == 1
    assert original[post[0]-18:post[0]-4] == bytes.fromhex("8b85fcffffff3b85e40200000f85")
    assert reloc[post[0]-4].target == parent["unsafe_control"]
    protected = []
    for r in sorted(content.relocations, key=lambda r:r.offset):
        if (r.kind,r.purpose) == ("abs32","protected content allocation end"):
            low = reloc[r.offset+12]
            assert (low.kind,low.purpose) == ("abs32","protected content allocation start")
            pair = low.target,r.target
            if pair not in protected: protected.append(pair)
    assert protected[:2] == [(content.state_va-0x40000,content.state_va),
                              (content.state_va,content.state_va+0x10000)]
    assert len(protected) in (2,3)
    edits = ((ladder[0],ladder[26],"drop_non_count_admissions"),
             (first,first+22,"first_live_dy"),
             (local_before[0],local_before[0],"count_local_snapshot"),
             (second,second+17,"shared_live_dy"),
             (post[0],post[0],"count_local_match"))
    b = Bytes(model.base_va); copied, changed, pending, next_labels = [],[],[],[]
    cursor = content.body_receipts[26][1]-content.base_va

    def branch(op, target, role="admit.reject"):
        b.raw(op); at = len(b.code); b.word(0)
        pending.append((at,target,"count_body_v2_internal:"+role))

    def local_extent(suffix):
        b.raw("8bbd"); b.word(208); b.raw("81c7"); b.word(-28)
        b.raw("f7c703000000"); branch("0f85",reject)
        b.raw("8b95"); b.word(228); b.raw("89d181c1"); b.word(-0x10000)
        b.raw("39cf"); branch("0f82",reject)
        b.raw("89f881c0"); b.word(4); branch("0f82",reject)
        b.raw("39d0"); branch("0f87",reject)
        for number,(low,high) in enumerate(protected):
            b.raw("81ff"); b.operand("abs32",high,"protected Count local allocation end")
            b.raw("0f83"); above=len(b.code); b.word(0)
            b.raw("81f8"); b.operand("abs32",low,"protected Count local allocation start")
            b.raw("0f86"); below=len(b.code); b.word(0)
            branch("e9",reject)
            name="count_body_v2_internal:count.local."+suffix+".protected."+str(number)
            next_labels.extend((at,model.base_va+len(b.code),name) for at in (above,below))

    for lo,hi,role in edits:
        start=len(b.code); b.code.extend(original[cursor:lo]); copied.append((cursor,lo,start))
        start=len(b.code)
        if role in ("count_local_snapshot","count_local_match"):
            local_extent("before" if role == "count_local_snapshot" else "after")
            b.raw("8b8700000000")
            b.raw("8985" if role == "count_local_snapshot" else "3b85"); b.word(376)
            if role == "count_local_match": branch("0f85",reject)
        elif role != "drop_non_count_admissions":
            branch("e8","dy","count_expected_dy")
            b.raw("81f8"); b.word(1); branch("0f85",reject)
            if role == "first_live_dy":
                b.raw("8b85"); b.word(408); b.raw("39f8"); branch("0f85",reject)
                b.raw("8bbd"); b.word(208)
            else: branch("e9",reloc[second+13].target,"ebp.compare")
        changed.append((lo,hi,start,len(b.code),role)); cursor=hi
    start=len(b.code); b.code.extend(original[cursor:]); copied.append((cursor,len(original),start))
    helper=model.base_va+len(b.code); helper_start=len(b.code)
    b.raw("8b85"); b.word(428); b.raw("a9070000000f85"); one=len(b.code); b.word(0)
    b.raw("81f8"); b.word(64); b.raw("0f83"); two=len(b.code); b.word(0)
    for number,(_,dy) in enumerate(NEIGHBORS):
        b.raw("81f8"); b.word(number*8); b.raw("0f85"); at=len(b.code); b.word(0)
        b.raw("bf"); b.word(dy); b.raw("b8"); b.word(1); b.raw("c3")
        next_labels.append((at,model.base_va+len(b.code),"count_body_v2_internal:count.dy.next."+str(number)))
    end=model.base_va+len(b.code); b.raw("b8"); b.word(0); b.raw("c3")
    for at in (one,two): b.mark(at,"rel32",end,"count_body_v2_internal:count.dy.reject")
    for at,target,role in next_labels: b.mark(at,"rel32",target,role)

    def mapped(va):
        old=va-content.base_va
        hits=[model.base_va+new+old-lo for lo,hi,new in copied if lo <= old < hi]
        hits += [model.base_va+new for lo,hi,new,_,role in changed if lo < hi and old == lo and
                 role != "drop_non_count_admissions"]
        assert len(hits) == 1,(hex(va),hits)
        return hits[0]

    for lo,hi,start in copied:
        for r in content.relocations:
            if not lo <= r.offset < hi: continue
            assert r.offset+4 <= hi
            target,purpose=r.target,r.purpose
            if r.kind == "rel32" and content.base_va <= target < content.base_va+len(original):
                target=mapped(target)
                assert purpose.startswith("content_v2_internal:")
                label=purpose.split(":",1)[1]
                label={"site_receipt.next.26":"site_receipt.next.0",
                       "site_receipt.next.27":"site_receipt.next.1"}.get(label,label)
                purpose="count_body_v2_internal:"+label
            elif r.kind == "rel32":
                assert target == dict(field.private_entries)["check_invocation"]
                assert purpose == "private current V2 complete content receipt" and original[r.offset-1] == 0xe8
            else: assert r.kind == "abs32"
            b.mark(start+r.offset-lo,r.kind,target,purpose)
    for at,target,role in pending: b.mark(at,"rel32",helper if target == "dy" else mapped(target),role)
    scalars=[]
    for number,row in enumerate(content.body_receipts[26:]):
        pattern=b"\xb8"+struct.pack("<I",26+number)+bytes.fromhex("8985c8000000")
        prefix=original[row[1]-content.base_va:row[3]-content.base_va]
        assert prefix.count(pattern) == 1
        body_at=row[1]-content.base_va+prefix.index(pattern)+1
        for old in (body_at,ladder[26+number]+8):
            new=mapped(content.base_va+old)-model.base_va
            assert new not in b.fields and struct.unpack_from("<I",b.code,new)[0] == 26+number
            struct.pack_into("<I",b.code,new,number); scalars.append((old,new,26+number,number))
    expected=b.finish()
    receipts=tuple((role,content.base_va+lo,content.base_va+hi,model.base_va+start,model.base_va+end,
                    sha(original[lo:hi]),sha(expected[start:end])) for lo,hi,start,end,role in changed)
    receipts += tuple(("site_scalar",content.base_va+old,content.base_va+old+4,model.base_va+new,model.base_va+new+4,
                       sha(struct.pack("<I",before)),sha(struct.pack("<I",after))) for old,new,before,after in scalars)
    receipts += (("authoritative_dy_helper",None,None,helper,model.base_va+len(expected),None,sha(expected[helper_start:])),)
    blocks=tuple(("canonical_content_block_"+str(i),content.base_va+lo,content.base_va+hi,
                  sha(original[lo:hi]),model.base_va+start,model.base_va+start+hi-lo)
                 for i,(lo,hi,start) in enumerate(copied))
    assert model.code == expected
    assert model.entries == tuple((f"site_{row[0]:06x}",mapped(row[1])) for row in content.body_receipts[26:])
    assert model.private_entries == tuple((name,mapped(va)) for name,va in content.private_entries)+(("count_expected_dy",helper),)
    assert model.body_receipts == tuple((row[0],*(mapped(va) for va in row[1:])) for row in content.body_receipts[26:])
    assert model.source_blocks == blocks and model.transform_receipts == receipts
    return b.fields


def independent_adapters(model, out, model_fields):
    """Clone full model blocks and independently author exact native tails."""
    b=Bytes(out.base_va); private=dict(model.private_entries)
    entries,guards,bodies,sources,hooks,pending=[],[],[],[],[],[]
    for number,row in enumerate(model.body_receipts):
        va,old_entry,payload,pc,denied,fault,valid=row
        end=model.body_receipts[1][1] if number == 0 else private["finish_rejected"]
        lo,hi=old_entry-model.base_va,end-model.base_va
        raw=model.code[lo:hi]; start=len(b.code); entry=out.base_va+start
        b.code.extend(raw); dispatch=out.base_va+len(b.code); admission=None; finishes=[]
        for at,(kind,target,role) in model_fields.items():
            if not lo <= at < hi: continue
            new=start+at-lo
            if kind == "abs32": b.mark(new,kind,target,"count_body_adapter_source_absolute:"+role)
            elif at == pc-model.base_va-4:
                assert target == private["admit_body"] and model.code[at-1] == 0xe8
                admission=new
            elif old_entry <= target < end:
                b.mark(new,kind,entry+target-old_entry,"count_body_adapter_internal:source_block")
            elif target in (private["finish_rejected"],private["finish_valid"]):
                assert model.code[at-1] == 0xe9; finishes.append(new)
            else:
                assert target == private["capture_inputs"] and model.code[at-1] == 0xe8
                b.mark(new,kind,target,"count_body_adapter_capture_inputs")
        def unsafe(op):
            b.raw(op); pending.append(len(b.code)); b.word(0)
        b.raw("83fa01"); unsafe("0f85"); b.raw("39ec"); unsafe("0f85")
        b.raw("8b95"); b.word(820); b.raw("81fa")
        b.operand("abs32",va+5,"natural corrected Count body CALL return"); unsafe("0f85")
        b.raw("8985" if number == 0 else "8885"); b.word(808 if number == 0 else 804)
        b.raw("81c4"); b.word(784); b.raw("619d8d642404")
        b.raw("83f9ff" if number == 0 else "3a5702")
        b.raw("e9"); b.operand("rel32",va+len(WINDOWS[va]),"native_count_body_resume")
        guard=out.base_va+len(b.code); b.raw("8d4c240439cd"); unsafe("0f85")
        b.raw("8b042481f8")
        b.operand("abs32",entry+pc-old_entry,"actual corrected Count adapter admission CALL return"); unsafe("0f85")
        b.raw("e9"); b.operand("rel32",private["admit_body"],"native_corrected_count_admission_parent")
        assert admission is not None and finishes
        b.mark(admission,"rel32",guard,f"count_body_adapter_internal:admit_{va:06x}")
        for at in finishes: b.mark(at,"rel32",dispatch,f"count_body_adapter_internal:finish_{va:06x}")
        entries.append((f"site_{va:06x}",entry)); guards.append((f"admit_{va:06x}",guard))
        bodies.append((va,entry,entry+payload-old_entry,entry+pc-old_entry,entry+denied-old_entry,
                       entry+fault-old_entry,entry+valid-old_entry,dispatch,va+len(WINDOWS[va])))
        sources.append((va,old_entry,end,sha(raw),entry,pc)); hooks.append((va,WINDOWS[va],entry,"count_body_v2_operand",()))
    terminal=out.base_va+len(b.code); b.raw("0f0b")
    for at in pending: b.mark(at,"rel32",terminal,"count_body_adapter_internal:unsafe_control")
    assert out.code == b.finish() and out.entries == tuple(entries)
    assert out.private_entries == (("unsafe_control",terminal),)+tuple(guards)
    assert out.body_receipts == tuple(bodies) and out.source_blocks == tuple(sources)
    assert out.planned_hooks == tuple(hooks)
    return b.fields


class Machine(entry_fixture.Machine):
    def __init__(self, tools, profile="classic", resolution="800x600", delta=0):
        hooks,deleted=[],set()
        original_add,original_del=tools[0].Uc.hook_add,tools[0].Uc.hook_del
        def add(cpu,kind,*args,**kwargs):
            handle=original_add(cpu,kind,*args,**kwargs); hooks.append((kind,handle,args,kwargs)); return handle
        def remove(cpu,handle):
            deleted.add(handle); return original_del(cpu,handle)
        with patch.object(tools[0].Uc,"hook_add",add),patch.object(tools[0].Uc,"hook_del",remove):
            super().__init__(tools,profile,resolution,delta)
        self.model,self.body=emit(profile,resolution)[-2:]
        for out in (self.model,self.body):
            raw=bytearray(out.code)
            for row in out.relocations:
                if row.kind == "abs32": struct.pack_into("<I",raw,row.offset,row.target+delta)
            self.cpu.mem_write(out.base_va+delta,bytes(raw)); self.loaded_code.append((out.base_va+delta,bytes(raw)))
            self.unsafe_vas.update(va+delta for name,va in out.private_entries if "unsafe" in name)
        self.planned={va:(old,target,role,removed) for va,old,target,role,removed in self.body.planned_hooks}
        # Only exact REP instruction bytes lose repeated CODE callbacks. Every
        # memory observer and strict before/after scan latch remains active.
        fields=independent_model(emit(profile,resolution)[5],emit(profile,resolution)[3],self.model)
        excluded=[]
        for start,end,_,_,_ in replay_fixture.decode(self.model.code,{at for at,r in fields.items() if r[0] == "abs32"}):
            if self.model.code[start:start+2] != b"\xf3\xaf": continue
            assert self.model.code[start-10] == 0xb9 and self.model.code[start-5] == 0xbf
            count=struct.unpack_from("<I",self.model.code,start-9)[0]
            pointer=struct.unpack_from("<I",self.model.code,start-4)[0]+delta
            pc=self.model.base_va+delta+start
            self.scan_before[pc-5]=(pc+2,pointer,count); self.scan_after[pc+2]=(pointer,count)
            excluded.append((pc,pc+1))
        assert excluded
        self.body_hook_receipts=[]
        for kind,handle,args,kwargs in hooks:
            if kind != self.u.UC_HOOK_CODE or handle in deleted: continue
            values,pieces=observer.observer_slices(args,kwargs,excluded,self.on_code)
            self.cpu.hook_del(handle)
            for low,high in pieces:
                self.cpu.hook_add(self.u.UC_HOOK_CODE,values["callback"],values["user_data"],low,high,values["aux1"],values["aux2"])
            self.body_hook_receipts.append((values,pieces))
        assert self.body_hook_receipts
        for left,right in excluded:
            assert not any(lo <= left <= hi or lo <= right <= hi for _,pieces in self.body_hook_receipts for lo,hi in pieces)
            assert all(any(lo <= pc <= hi for _,pieces in self.body_hook_receipts for lo,hi in pieces) for pc in (left-5,right+1))

    def setup_count_body(self,row,*,offset=0,via_adjacent=False,input_record=0,center=(1,3),target_record=21):
        # Tile stays00: setup_body must never silently call begin(1) and erase
        # the full-mode case. Count record coordinates are independent of Tile.
        mode=self.word(self.lease_frame+40)
        regs=self.setup_body(row,index=21,via_adjacent=via_adjacent)
        assert self.current_cell == (0,0) and self.word(self.lease_frame+40) == mode
        assert self.word(self.unit_sp) == (0x42fcc4 if via_adjacent else 0x4303b1)+self.delta
        assert self.word(self.native_s-24) == self.unit_sp-12
        dx,dy=NEIGHBORS[offset//8] if 0 <= offset < 64 and offset%8 == 0 else (0,-1)
        regs["EAX"],regs["EBP"]=offset & 0xffffffff,dy & 0xffffffff
        regs["EDI"]=self.WORLD+852+31*input_record
        self.cpu.mem_write(regs["EDI"]+2,b"\x5a")
        self.cpu.mem_write(regs["EDI"]+4,struct.pack("<HH",*center))
        # Real Count local at CountS-28 contains center input X. It is not the
        # saved EBP word at CountS-24 and must remain immutable across Thread.
        self.put(self.native_s-28,center[0])
        nx,ny=center[0]+dx,center[1]+dy
        if row[3] == "occupant":
            regs["ECX"],regs["EBX"]=self.WORLD+40*nx,ny & 0xffffffff
            self.neighbor=(nx,ny)
            if 0 <= nx < self.word(self.WORLD+804) and 0 <= ny < 7:
                self.cpu.mem_write(self.WORLD+1534+40*nx+2*ny,struct.pack("<h",target_record))
        else:
            regs["ECX"],regs["EDX"]=31*target_record,self.WORLD
            self.cpu.mem_write(self.WORLD+854+31*target_record,b"\xd3")
        self.body_regs=regs
        return regs


class SourceTests(unittest.TestCase):
    def test_all36_complete_model_adapters_independent_bytes_roles_and_bounds(self):
        source_closure()
        for profile in CONTEXT.PROFILES:
            for resolution in CONTEXT.RESOLUTIONS:
                with self.subTest(profile=profile,resolution=resolution):
                    values=emit(profile,resolution); layout,field,content=values[0],values[3],values[5]
                    model,out=values[-2:]
                    self.assertEqual(model.base_va,(values[10].base_va+len(values[10].code)+15)&~15)
                    self.assertEqual(out.base_va,(model.base_va+len(model.code)+15)&~15)
                    self.assertLessEqual(out.base_va+len(out.code),layout.rx.va+layout.rx.size)
                    fields=independent_model(content,field,model)
                    for component,expected in ((model,fields),(out,independent_adapters(model,out,fields))):
                        declared={r.offset:(r.kind,r.target,r.purpose) for r in component.relocations}
                        self.assertEqual(len(declared),len(component.relocations)); self.assertEqual(declared,expected)
                        absolute={at for at,r in expected.items() if r[0] == "abs32"}
                        decoded=replay_fixture.decode(component.code,absolute)
                        self.assertEqual({at for _,_,aa,_,_ in decoded for at in aa},absolute)
                        self.assertEqual({at for _,_,_,rr,_ in decoded for at in rr},
                                         {at for at,r in expected.items() if r[0] == "rel32"})
                        starts={start for start,*_ in decoded}
                        for _,_,aa,rr,ss in decoded:
                            self.assertFalse({at for at,_ in ss}&set(expected))
                            for at in aa: self.assertEqual(struct.unpack_from("<I",component.code,at)[0],expected[at][1])
                            for at in rr:
                                target=component.base_va+at+4+struct.unpack_from("<i",component.code,at)[0]
                                self.assertEqual(target,expected[at][1])
                                if component.base_va <= target < component.base_va+len(component.code):
                                    self.assertIn(target-component.base_va,starts)
                        self.assertNotIn(5,absolute,"784-byte frame scalar is not an address")
                    for number,row in enumerate(model.body_receipts):
                        self.assertEqual(row[0],SITES[number][0])
                    self.assertEqual(len(model.source_blocks),6)
                    self.assertEqual({r[0] for r in model.transform_receipts},
                        {"drop_non_count_admissions","first_live_dy","shared_live_dy","count_local_snapshot",
                         "count_local_match","site_scalar","authoritative_dy_helper"})
        self.assertEqual(tuple(NEIGHBORS),tool.NEIGHBORS)

    def test_complete_frozen_parent_identity_and_receipts_are_required(self):
        values=emit(); prefix=values[:-2]
        self.assertEqual(asdict(prefix[-1]),asdict(entry_fixture.emit()[-1]))
        for index in range(3,11):
            out=prefix[index]; raw=bytearray(out.code); raw[-1]^=1
            supplied=list(prefix); supplied[index]=replace(out,code=bytes(raw))
            with self.subTest(parent=index),self.assertRaises(ValueError): tool._emit_code(*supplied,**arguments())
        for name in ("prefix_receipt","private_clone_receipt","guard_receipts","source_blocks","planned_hooks"):
            value=getattr(prefix[-1],name); changed=value[:-1]
            self.assertNotEqual(value,changed)
            supplied=prefix[:-1]+(replace(prefix[-1],**{name:changed}),)
            with self.subTest(receipt=name),self.assertRaises(ValueError): tool._emit_code(*supplied,**arguments())

    def test_closed_model_adapter_bytes_receipts_and_scalar_roles(self):
        values=emit(); field,content,model,out=values[3],values[5],values[-2],values[-1]
        for component,names in ((model,("source_blocks","transform_receipts","body_receipts","private_entries")),
                                (out,("source_blocks","body_receipts","private_entries","planned_hooks"))):
            check=(lambda obj:tool._model_operand_inventory(obj,content,field)) if component is model else (
                   lambda obj:tool._operand_inventory(obj,model))
            for name in names:
                value=getattr(component,name); changed=value[:-1]
                self.assertNotEqual(value,changed)
                with self.subTest(component=type(component).__name__,field=name),self.assertRaises(ValueError):
                    check(replace(component,**{name:changed}))
            forged=clip.Relocation(5,"abs32",784,"forged frame address")
            with self.assertRaises(ValueError): check(replace(component,relocations=component.relocations+(forged,)))
            for at in (0,dict(component.private_entries)["unsafe_control"]-component.base_va):
                raw=bytearray(component.code); raw[at]^=1
                with self.subTest(offset=at),self.assertRaises(ValueError): check(replace(component,code=bytes(raw)))
            row=next(r for r in component.relocations if r.kind == "abs32")
            for bad in (replace(row,kind="rel32"),replace(row,target=row.target+4),replace(row,purpose="forged")):
                changed=tuple(bad if r == row else r for r in component.relocations)
                with self.assertRaises(ValueError): check(replace(component,relocations=changed))

    def test_authored_span_table_highlow_both_images_not_original_execution(self):
        template=arguments()["template_source"]
        with self.assertRaises(ValueError): tool._native_contract(template[:-1])
        # Synthetic digest adapter authenticates only this authored byte array.
        # It does not admit a retail executable or prove original Count parity.
        span=bytearray(b"\x90"*133); span[:11]=bytes.fromhex("53515256575583ec0489c7")
        highlow=((0x426f0d,0x514500),(0x426f19,0x532048),(0x426f29,0x514504))
        for va,target in highlow: struct.pack_into("<I",span,va-0x426ef0,target)
        for va,raw in WINDOWS.items(): span[va-0x426ef0:va-0x426ef0+len(raw)]=raw
        span=bytes(span); table=struct.pack("<16i",*(v for pair in NEIGHBORS for v in pair))
        self.assertEqual(sha(table),tool.TABLE_SHA256)
        image=span+b"\x90"*(256-len(span))+table
        def offset(image,va,count):
            if 0x426ef0 <= va and va+count <= 0x426f75: return va-0x426ef0
            if va == 0x514500 and count == 64: return 256
            raise ValueError("outside authored authentication map")
        mapper=SimpleNamespace(file_offset=offset)
        relocs=tuple(va-0x400000 for va,_ in highlow)
        pe=SimpleNamespace(inspect_pe=lambda raw:SimpleNamespace(image_base=0x400000),
                           _old_relocations=lambda raw,parsed:(None,relocs))
        digest=lambda raw:tool.COUNT_SHA256 if raw == span else sha(raw)
        with patch.object(tool,"_sha",digest):
            tool._authenticate_native(image,image,mapper,pe,template_source=template)
            for target in (0,1):
                for at in (0,132,0x426f0d-0x426ef0,0x426f19-0x426ef0,0x426f29-0x426ef0,
                           0x426f44-0x426ef0,0x426f54-0x426ef0,256,319):
                    bad=bytearray(image); bad[at]^=1; supplied=[image,image]; supplied[target]=bytes(bad)
                    with self.subTest(image=target,offset=at),self.assertRaises(ValueError):
                        tool._authenticate_native(*supplied,mapper,pe,template_source=template)
            for changed in (relocs[:-1],relocs+(0x26f45,),relocs+(0x26ef1,)):
                pe._old_relocations=lambda raw,parsed,changed=changed:(None,changed)
                with self.assertRaises(ValueError): tool._authenticate_native(image,image,mapper,pe,template_source=template)

    def test_public_alias_capture_source_pins_and_false_claims(self):
        def poison(*args,**kwargs): raise AssertionError("mutable issuer alias invoked")
        with patch.object(tool,"_issue",poison),patch.object(entry_tool,"_issue",poison):
            for original in (b"",b"authored PE",bytearray(b"authored PE"),None):
                with self.assertRaisesRegex(ValueError,"original"): tool.emit_count_body_v2(original,"classic","800x600")
        for name in ("installed","native_executed","native_count_instruction_execution_verified","native_count_parity_verified",
                     "runtime_verified","manual_input_proof","release_accepted","promotion_ready","non_draw_count_admission",
                     "native_sentinel_record_verified","native_stack_capacity_verified","whole_chain_capacity_verified",
                     "native_callback_abi_verified","provider_lifetime_verified","transient_write_prevention_verified",
                     "cross_thread_immutability_verified","healthy_native_unwind_verified","atomic_installation_verified"):
            self.assertIn(name,tool.FALSE_CLAIMS)
        tree=ast.parse((ROOT/tool.SOURCE).read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and
                             n.func.attr in ("write_bytes","write_text") for n in ast.walk(tree)))
        self.assertEqual(tool.HELPER_BYTES,784)
        self.assertEqual(tool.ENTRY_SHA256,entry_fixture.COUNT_SOURCE_SHA256)


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools=observer.parent_fixture.field_fixture.routing_fixture.lifetime.prior_fixture.machine_tools()
        if cls.tools is None: raise ImportError("required Unicorn CPU interpreter unavailable")

    def make(self,profile="classic",delta=0,mode=0):
        return Machine(self.tools,profile,delta=delta).prepare(columns=3).begin(mode)

    def assert_healthy(self,m,row,regs,value,*,flags=0xed7):
        expected=m.scalar_oracle(row,regs,value,flags)
        owner,tiles,descriptor=m.record(),list(m.tiles),bytes(m.cpu.mem_read(m.lease_frame,192))
        local,saved=m.word(m.native_s-28),m.word(m.native_s-24)
        scans=m.scan_observations
        actual=m.invoke_replay(row,regs,flags=flags)
        self.assertEqual(m.native_stop,row[0]+m.delta+len(WINDOWS[row[0]]))
        for name in regs: self.assertEqual(actual[name],expected[name],(hex(row[0]),name))
        self.assertEqual(actual["EFLAGS"]&m.MASK,expected["EFLAGS"]&m.MASK)
        self.assertEqual(m.callbacks[m.before_callbacks:],["thread"])
        self.assertFalse(m.unsafe); self.assertGreater(m.scan_observations,scans); self.assertIsNone(m.active_scan)
        self.assertEqual(m.record(),owner); self.assertEqual(m.tiles,tiles)
        self.assertEqual(bytes(m.cpu.mem_read(m.lease_frame,192)),descriptor)
        self.assertEqual(m.word(m.native_s-28),local); self.assertEqual(m.word(m.native_s-24),saved)
        helper=regs["ESP"]-824
        self.assertIn((m.native_s-28,4),m.observed_reads())
        self.assertIn((m.native_s-28,4),m.observed_reads(post_thread=True))
        for at,size in m.content_writes:
            self.assertTrue(helper-44 <= at and at+size <= helper+824,(hex(at),size))
            self.assertFalse(at < m.native_s-24 and at+size > m.native_s-28,
                             "healthy helper must not write Count local X")
        for at,raw in m.loaded_code: self.assertEqual(bytes(m.cpu.mem_read(at,len(raw))),raw)
        return actual

    def assert_terminal(self,m,row,regs,**options):
        owner,tiles=m.record(),list(m.tiles)
        with self.assertRaises(self.tools[0].UcError): m.invoke_replay(row,regs,**options)
        pc=m.cpu.reg_read(m.regs["EIP"])
        self.assertIn(pc,m.unsafe_vas); self.assertEqual(bytes(m.cpu.mem_read(pc,2)),b"\x0f\x0b")
        self.assertIsNone(m.native_stop); self.assertEqual(m.record(),owner); self.assertEqual(m.tiles,tiles)
        self.assertFalse(any(m.lease_frame <= at < m.lease_frame+192 for at,_ in m.content_writes))
        self.assertFalse(any(at < m.native_s-24 and at+size > m.native_s-28 for at,size in m.content_writes),
                         "denial must not restore or overwrite Count local X")

    def test_live_dy_saved_ebp_native_tails_profiles_bases_modes_initial_ancestry(self):
        for profile in CONTEXT.PROFILES:
            for delta in (0,0x30000):
                for mode in (0,1):
                    m=self.make(profile,delta,mode)
                    for via in (False,True):
                        for offset in (0,16,24): # three distinct signed DY values
                            for row in SITES:
                                with self.subTest(profile=profile,delta=delta,mode=mode,via=via,offset=offset,va=hex(row[0])):
                                    regs=m.setup_count_body(row,offset=offset,via_adjacent=via,input_record=7)
                                    self.assertEqual(m.word(m.lease_frame+40),mode)
                                    self.assertEqual(regs["EBP"],NEIGHBORS[offset//8][1]&0xffffffff)
                                    self.assertNotEqual(regs["EBP"],m.word(m.native_s-24))
                                    actual=self.assert_healthy(m,row,regs,21 if row[3] == "occupant" else 0xd3)
                                    if row[3] == "owner": self.assertEqual(actual["EDX"],(m.WORLD&~0xff)|0xd3)
                    del m; gc.collect()

    def test_all_eight_dy_offsets_occupied_empty_edges_and_malformed_payload(self):
        for delta in (0,0x30000):
            m=self.make("modalwidgets",delta)
            for offset in range(0,64,8):
                for row in SITES:
                    regs=m.setup_count_body(row,offset=offset,via_adjacent=True,input_record=0)
                    self.assert_healthy(m,row,regs,21 if row[3] == "occupant" else 0xd3,flags=0x246)
            occupant=SITES[0]
            regs=m.setup_count_body(occupant,offset=16)
            nx,ny=m.neighbor; at=m.WORLD+1534+40*nx+2*ny
            m.cpu.mem_write(at,b"\xff\xff")
            self.assert_healthy(m,occupant,regs,0xffffffff)
            regs=m.setup_count_body(occupant,offset=0,center=(0,0))
            self.assert_healthy(m,occupant,regs,0xffffffff)
            self.assertFalse(any(m.WORLD+1534 <= at < m.WORLD+2334 for at,_ in m.content_reads))
            del m; gc.collect()
        for bad in (-2,22,32767):
            m=self.make(); row=SITES[0]; regs=m.setup_count_body(row,offset=16)
            nx,ny=m.neighbor; m.cpu.mem_write(m.WORLD+1534+40*nx+2*ny,struct.pack("<h",bad))
            self.assert_terminal(m,row,regs); del m; gc.collect()

    def test_invalid_offset_live_dy_saved_ancestry_and_numeric_input_before_caches(self):
        for fault in ("offset1","offset4","offset64","offsetnegative","dy","inherited_live_ebp",
                      "saved_ebp","count_return","non_draw_one","non_draw_two","sentinel","input_one_past"):
            m=self.make("framed",0x30000); row=SITES[1]; regs=m.setup_count_body(row)
            if fault.startswith("offset"):
                regs["EAX"]={"offset1":1,"offset4":4,"offset64":64,"offsetnegative":0xfffffff8}[fault]
            elif fault == "dy": regs["EBP"]=0
            elif fault == "inherited_live_ebp": regs["EBP"]=m.unit_sp-12
            elif fault == "saved_ebp": m.put(m.native_s-24,m.word(m.native_s-24)+4)
            elif fault in ("count_return","non_draw_one","non_draw_two"):
                m.put(m.native_s,{"count_return":0x42f95f,"non_draw_one":0x426f95,"non_draw_two":0x431d7a}[fault]+m.delta)
            elif fault == "sentinel": regs["EDI"]=m.WORLD+821
            else: regs["EDI"]=m.WORLD+852+31*22
            # Numeric input membership occurs after the full current receipt;
            # only earlier DY/ancestry failures authorize poisoned cached pages.
            early=fault not in ("sentinel","input_one_past")
            if early: m.protect_cached(m.u.UC_PROT_NONE)
            self.assert_terminal(m,row,regs)
            if early:
                self.assertEqual(m.callbacks[m.before_callbacks:],[]); self.assertEqual(m.cached_reads(),[])
            self.assertNotIn((regs["EDI"]+2,1),m.content_reads)
            del m; gc.collect()

    def test_actual_foreign_native_and_intrinsic_return_stack_fail_before_callback(self):
        for row in SITES:
            for fault in ("foreign_native","intrinsic_return","intrinsic_stack"):
                m=self.make("completehd",0x30000); regs=m.setup_count_body(row)
                options={}; seen=[]
                if fault == "foreign_native": options["call_pc"]=row[0]+m.delta+0x25
                else:
                    guard=dict(m.body.private_entries)[f"admit_{row[0]:06x}"]+m.delta
                    def corrupt(mm,address):
                        if address == guard:
                            sp=mm.cpu.reg_read(mm.regs["ESP"])
                            if fault == "intrinsic_return": mm.put(sp,mm.word(sp)^4)
                            else: mm.cpu.reg_write(mm.regs["ESP"],sp-4)
                            seen.append(sp)
                    m.instruction_mutation=corrupt
                m.protect_cached(m.u.UC_PROT_NONE); self.assert_terminal(m,row,regs,**options)
                if fault != "foreign_native": self.assertEqual(len(seen),1)
                self.assertEqual(m.callbacks[m.before_callbacks:],[]); self.assertEqual(m.cached_reads(),[])
                del m; gc.collect()

    def test_latched_loss_and_callback_control_descriptor_precede_poisoned_caches(self):
        for fault in ("loss","status","phase","descriptor","helper","saved_ebp","unit_return"):
            m=self.make("completehd",0x30000); row=SITES[1]; regs=m.setup_count_body(row,via_adjacent=True)
            seen=[]
            if fault in ("loss","status","phase"):
                m.put(m.state_va if fault == "phase" else m.lease_frame+(44 if fault == "loss" else 48),3 if fault == "phase" else 2)
                m.protect_cached(m.u.UC_PROT_NONE)
            else:
                def corrupt(mm,label):
                    if label == "thread":
                        at={"descriptor":mm.lease_frame+60,"helper":regs["ESP"]-824+812,
                            "saved_ebp":mm.native_s-24,"unit_return":mm.unit_sp}[fault]
                        mm.put(at,mm.word(at)^4); seen.append(at); mm.protect_cached(mm.u.UC_PROT_NONE)
                m.mutation=corrupt
            self.assert_terminal(m,row,regs)
            if fault in ("loss","status","phase"):
                self.assertEqual(m.callbacks[m.before_callbacks:],[]); self.assertEqual(m.cached_reads(),[])
            else:
                self.assertEqual(len(seen),1); self.assertEqual(m.callbacks[m.before_callbacks:],["thread"])
                self.assertEqual(m.cached_reads(post_thread=True),[])
            del m; gc.collect()

    def test_count_local_x_and_paired_shadow_loss_deny_before_post_thread_caches(self):
        for row in SITES:
            for paired in (False,True):
                m=self.make("modalwidgets",0x30000); regs=m.setup_count_body(row,offset=24,via_adjacent=True)
                local=m.native_s-28; saved_ebp=m.word(m.native_s-24); seen=[]
                def corrupt(mm,label):
                    if label == "thread":
                        helper=regs["ESP"]-824
                        self.assertEqual(mm.word(helper+376),mm.word(local))
                        mm.put(local,mm.word(local)^1)
                        if paired: mm.put(helper+376,mm.word(helper+376)^1)
                        seen.append(local); mm.protect_cached(mm.u.UC_PROT_NONE)
                m.mutation=corrupt
                self.assert_terminal(m,row,regs)
                self.assertEqual(seen,[local]); self.assertEqual(m.word(m.native_s-24),saved_ebp)
                self.assertEqual(m.callbacks[m.before_callbacks:],["thread"])
                self.assertEqual(m.cached_reads(post_thread=True),[])
                local_reads=[event for event in m.content_events if event[0] == "read" and
                             event[4] and event[2:4] == (local,4)]
                # A paired native/helper mutation dies in control_match,
                # before the added post-Thread native-local reread itself.
                self.assertEqual(len(local_reads),0 if paired else 1)
                self.assertNotIn((local,4),m.content_writes,"denial must not repair native Count local")
                del m; gc.collect()


TEST_COUNT=sum(unittest.defaultTestLoader.loadTestsFromTestCase(cls).countTestCases() for cls in (SourceTests,CPUTests))


def run_tests():
    before=source_closure()
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in (SourceTests,CPUTests))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if source_closure() != before: raise ValueError("Count-body V2 source closure changed during tests")
    if not result.wasSuccessful() or result.skipped or result.testsRun != TEST_COUNT:
        raise AssertionError("uninstalled Count-body V2 fixture failures")
    return result.testsRun


if __name__ == "__main__":
    if len(sys.argv) > 1: unittest.main()
    else: run_tests()
