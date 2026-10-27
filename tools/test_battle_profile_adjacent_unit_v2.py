#!/usr/bin/env python3
"""Independent source/scalar models for an uninstalled atomic Unit successor.

No original executable or original Unit/Adjacent/Count body is opened or run.
Final42FFA4 uses authored negative-caller frames, not genuine caller proof.
Current global equality is restrictive admission, not historical authority.
No installation, runtime, input, lifetime, release or promotion is established.
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

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"tools")]
from src.patcher import battle_profile_adjacent_unit_v2 as tool
from src.patcher import battle_profile_count_body_v2 as body_tool
from src.patcher import partial_tile_clip as clip
import test_battle_profile_count_body_v2 as body_fixture

SOURCE_SHA256="b2ae87457bd2344d9e6650032dba46d03a680e2303946acb75abaf0508f5ead8"
BODY_FIXTURE_SHA256="80ebeb87f50959890b6eb8d6df6bb2dfc398c750419137f9e51c7a4b14505ecc"
replay_fixture=body_fixture.replay_fixture
entry_fixture=body_fixture.entry_fixture
observer=body_fixture.observer
CONTEXT=body_fixture.CONTEXT
INDICES=(12,13,14,15,16,26,27)
SITES=tuple(replay_fixture.native_content.SITES[i] for i in INDICES)
WINDOWS={row[0]:bytes.fromhex(replay_fixture.WINDOWS[row[0]]) for row in SITES}
ORDINARY_RETURNS=(0x42fcc4,0x42fd58,0x42fdf9,0x42fefc,0x42ff20,0x42ff54,0x42ff75)
FINAL_RETURN=0x42ffa4
MOTION,ACTIVE=0x523f70,0x512360
NEIGHBORS=body_fixture.NEIGHBORS
CACHE={}
Bytes=body_fixture.Bytes


def sha(raw): return hashlib.sha256(raw).hexdigest()


def arguments():
    return dict(count_body_module=body_tool,count_body_kwargs=body_fixture.arguments(),
        content_module=replay_fixture.content_tool,template_module=replay_fixture.native_content,
        assembler_module=clip,template_source=(ROOT/tool.TEMPLATE).read_bytes())


def emit(profile="classic",resolution="800x600"):
    key=profile,resolution
    if key not in CACHE:
        prefix=body_fixture.emit(profile,resolution)
        CACHE[key]=prefix+tool._emit_code(*prefix,**arguments())
    return CACHE[key]


def source_closure():
    previous=body_fixture.source_closure()
    for name,digest in ((tool.SOURCE,SOURCE_SHA256),("tools/test_battle_profile_count_body_v2.py",BODY_FIXTURE_SHA256)):
        if sha((ROOT/name).read_bytes()) != digest: raise ValueError("frozen atomic dependency differs: "+name)
    names=set(previous)|{tool.SOURCE,"tools/test_battle_profile_adjacent_unit_v2.py"}
    return {name:sha((ROOT/name).read_bytes()) for name in sorted(names)}


def independent_model(content,field,out):
    """Whole canonical byte surgery with authored motion/DY/local additions.

    All source intervals and typed fields originate in frozen Content V2, not
    new source-block or relocation declarations. Scalar site IDs are explicit.
    """
    original=content.code; private=dict(content.private_entries)
    old={r.offset:r for r in content.relocations}
    native=sorted((r for r in content.relocations if (r.kind,r.purpose)==
                   ("abs32","fixed proposed body CALL return PC")),key=lambda r:r.offset)
    assert len(native)==28 and tuple(r.target for r in native)==tuple(row[0]+5 for row in replay_fixture.native_content.SITES)
    ladder=[r.offset-26 for r in native]; reject=old[ladder[0]+32].target
    for n,start in enumerate(ladder):
        raw=original[start:start+41]
        assert raw[:8]==bytes.fromhex("8b85c800000081f8") and struct.unpack_from("<I",raw,8)[0]==n
        assert raw[12:14]==b"\x0f\x85" and raw[18:26]==bytes.fromhex("8b870000000081f8")
        assert struct.unpack_from("<I",raw,26)[0]==native[n].target and raw[30:32]==b"\x0f\x85" and raw[36]==0xe9
        for at,label in ((14,"site_receipt.next."+str(n)),(32,"admit.reject"),(37,"site_receipt.matched")):
            assert old[start+at].kind=="rel32" and old[start+at].purpose=="content_v2_internal:"+label
    assert all(r-l==41 for l,r in zip(ladder,ladder[1:]))
    count=[r for r in content.relocations if (r.kind,r.target,r.purpose)==("abs32",0x42f95b,"draw-only native Count caller")]
    assert len(count)==1
    first=count[0].offset+10
    assert original[first:first+18]==bytes.fromhex("89f981c1380000008b859801000039c80f85")
    assert old[first+18].target==reject
    second=[r.offset-13 for r in content.relocations if r.kind=="rel32" and r.purpose=="content_v2_internal:ebp.compare"
            and original[r.offset-13:r.offset]==bytes.fromhex("8bbdd800000081c7f4ffffffe9")
            and original[r.offset-25:r.offset-17]==bytes.fromhex("81f8030000000f84")]
    before=[r.offset-13 for r in content.relocations if r.kind=="rel32" and r.purpose=="content_v2_internal:ancestry.unit"
            and original[r.offset-13:r.offset]==bytes.fromhex("8bbdd000000081c744000000e9")]
    motion=[r.offset-13 for r in content.relocations if r.kind=="rel32" and r.purpose=="content_v2_internal:unit.saved.compare"
            and original[r.offset-13:r.offset]==bytes.fromhex("8bb5d40000008b8ee8ffffffe9")]
    assert len(second)==len(before)==len(motion)==1
    second,before,motion=second[0],before[0],motion[0]
    thread=[r for r in content.relocations if (r.kind,r.purpose)==("abs32","fixed content owning ThreadId callback")]
    assert len(thread)==1
    post=[at for at in range(thread[0].offset+4,private["fixed_receipt"]-content.base_va)
          if original[at:at+14]==bytes.fromhex("8b85000300003b85180000000f85")]
    assert len(post)==1 and original[post[0]-18:post[0]-4]==bytes.fromhex("8b85fcffffff3b85e40200000f85")
    assert old[post[0]-4].target==private["unsafe_control"]
    protected=[]
    for r in sorted(content.relocations,key=lambda r:r.offset):
        if (r.kind,r.purpose)==("abs32","protected content allocation end"):
            low=old[r.offset+12]
            assert (low.kind,low.purpose)==("abs32","protected content allocation start")
            pair=low.target,r.target
            if pair not in protected: protected.append(pair)
    assert protected[:2]==[(content.state_va-0x40000,content.state_va),(content.state_va,content.state_va+0x10000)]
    assert len(protected) in (2,3)
    edits=((content.body_receipts[17][1]-content.base_va,content.body_receipts[26][1]-content.base_va,"drop_unselected_bodies"),
           (ladder[0],ladder[12],"drop_admissions_0_12"),(ladder[17],ladder[26],"drop_admissions_17_26"),
           (first,first+22,"first_live_dy"),(before,before,"count_local_snapshot"),
           (second,second+17,"shared_live_dy"),(motion,motion,"final_unit_motion"),
           (post[0],post[0],"motion_and_count_local_match"))
    b=Bytes(out.base_va); copied,changed,pending,labels=[],[],[],{}
    cursor=content.body_receipts[12][1]-content.base_va

    def label(name):
        assert name not in labels; labels[name]=out.base_va+len(b.code)
    def branch(op,target,name=None):
        b.raw(op); at=len(b.code); b.word(0)
        pending.append((at,target,"adjacent_unit_v2_internal:"+(name or "admit.reject")))
    def local(op,name): branch(op,("label",name),name)
    def get(reg,slot): b.raw("8b"+f"{0x85|reg<<3:02x}"); b.word(slot)
    def put(reg,slot): b.raw("89"+f"{0x85|reg<<3:02x}"); b.word(slot)
    def cmp(reg,value): b.raw("81"+f"{0xf8|reg:02x}"); b.word(value)
    def add(reg,value): b.raw("81"+f"{0xc0|reg:02x}"); b.word(value)
    def match(reg,slot): b.raw("3b"+f"{0x85|reg<<3:02x}"); b.word(slot)
    def read(reg,pointer,purpose): b.raw("8b"+f"{0x05|reg<<3:02x}"); b.operand("abs32",pointer,purpose)
    def extent(slot,offset,prefix,suffix):
        get(7,slot); add(7,offset); b.raw("f7c703000000"); branch("0f85",reject)
        get(2,228); b.raw("89d1"); add(1,-0x10000)
        b.raw("39cf"); branch("0f82",reject)
        b.raw("89f8"); add(0,4); branch("0f82",reject)
        b.raw("39d0"); branch("0f87",reject)
        for n,(lo,hi) in enumerate(protected):
            name=suffix+".protected."+str(n)
            b.raw("81ff"); b.operand("abs32",hi,"protected "+prefix+" allocation end"); local("0f83",name)
            b.raw("81f8"); b.operand("abs32",lo,"protected "+prefix+" allocation start"); local("0f86",name)
            branch("e9",reject); label(name)
    def count_local(suffix): extent(208,-28,"Count local","count.local."+suffix)
    def witness(suffix):
        name="unit.motion."+suffix
        get(0,204); cmp(0,4); local("0f84",name+".count")
        cmp(0,1); branch("0f85",reject)
        get(0,200); cmp(0,0); local("0f84",name+".early")
        extent(216,-28,"Unit motion witness",name+".unit"); b.raw("8b8700000000")
        cmp(0,682); branch("0f83",reject)
        b.raw("31d2b91f000000f7f185d2"); branch("0f85",reject); local("e9",name+".identity")
        label(name+".early"); get(0,404); local("e9",name+".identity")
        label(name+".count"); extent(208,-16,"Unit motion witness",name+".count"); b.raw("8b8700000000")
        label(name+".identity"); cmp(0,22); branch("0f83",reject)

    for lo,hi,role in edits:
        start=len(b.code); b.code.extend(original[cursor:lo]); copied.append((cursor,lo,start)); start=len(b.code)
        if role=="count_local_snapshot":
            count_local("before"); b.raw("8b8700000000"); put(0,376)
        elif role=="final_unit_motion":
            b.raw("81f8"); b.operand("abs32",FINAL_RETURN,"final signed-motion Unit caller")
            local("0f85","unit.saved.ordinary")
            read(0,MOTION,"fixed final Unit signed motion"); b.raw("85c0"); branch("0f89",reject); put(0,380)
            witness("before"); put(0,384)
            read(1,ACTIVE,"fixed final Unit active identity"); b.raw("39c8"); branch("0f85",reject)
            get(1,380); get(7,216); branch("e9",old[motion+13].target,"unit.saved.compare")
            label("unit.saved.ordinary")
        elif role=="motion_and_count_local_match":
            get(0,380); b.raw("85c0"); local("0f89","unit.motion.receipts.done")
            read(0,MOTION,"fixed final Unit signed motion recheck"); match(0,380); branch("0f85",reject)
            read(0,ACTIVE,"fixed final Unit active identity recheck"); match(0,384); branch("0f85",reject)
            witness("after"); match(0,384); branch("0f85",reject)
            label("unit.motion.receipts.done"); get(0,204); cmp(0,4); local("0f85","count.local.after.done")
            count_local("after"); b.raw("8b8700000000"); match(0,376); branch("0f85",reject)
            label("count.local.after.done")
        elif not role.startswith("drop_"):
            branch("e8","dy","count_expected_dy"); cmp(0,1); branch("0f85",reject)
            if role=="first_live_dy":
                get(0,408); b.raw("39f8"); branch("0f85",reject); get(7,208)
            else: branch("e9",old[second+13].target,"ebp.compare")
        changed.append((lo,hi,start,len(b.code),role)); cursor=hi
    start=len(b.code); b.code.extend(original[cursor:]); copied.append((cursor,len(original),start))
    helper=out.base_va+len(b.code); helper_start=len(b.code)
    get(0,428); b.raw("a907000000"); local("0f85","count.dy.reject")
    cmp(0,64); local("0f83","count.dy.reject")
    for n,(_,dy) in enumerate(NEIGHBORS):
        cmp(0,n*8); local("0f85","count.dy.next."+str(n))
        b.raw("bf"); b.word(dy); b.raw("b8"); b.word(1); b.raw("c3"); label("count.dy.next."+str(n))
    label("count.dy.reject"); b.raw("b8"); b.word(0); b.raw("c3")
    def mapped(va):
        at=va-content.base_va
        hits=[out.base_va+new+at-lo for lo,hi,new in copied if lo<=at<hi]
        hits += [out.base_va+new for lo,hi,new,_,role in changed if lo<hi and at==lo and not role.startswith("drop_")]
        for lo,hi,_,_,role in changed:
            if role.startswith("drop_admissions_") and at==lo: hits.append(mapped(content.base_va+hi))
        assert len(hits)==1,(hex(va),hits)
        return hits[0]
    for lo,hi,start in copied:
        for r in content.relocations:
            if not lo<=r.offset<hi: continue
            assert r.offset+4<=hi
            target,purpose=r.target,r.purpose
            if r.kind=="rel32" and content.base_va<=target<content.base_va+len(original):
                target=mapped(target); assert purpose.startswith("content_v2_internal:")
                name=purpose.split(":",1)[1]
                if name.startswith("site_receipt.next."): name="site_receipt.next."+str(INDICES.index(int(name.rsplit(".",1)[1])))
                purpose="adjacent_unit_v2_internal:"+name
            elif r.kind=="rel32":
                assert target==dict(field.private_entries)["check_invocation"] and purpose=="private current V2 complete content receipt"
            else: assert r.kind=="abs32"
            b.mark(start+r.offset-lo,r.kind,target,purpose)
    for at,target,purpose in pending:
        target=helper if target=="dy" else labels[target[1]] if isinstance(target,tuple) else mapped(target)
        b.mark(at,"rel32",target,purpose)
    scalars=[]
    for n,index in enumerate(INDICES):
        row=content.body_receipts[index]; pattern=b"\xb8"+struct.pack("<I",index)+bytes.fromhex("8985c8000000")
        raw=original[row[1]-content.base_va:row[3]-content.base_va]
        assert raw.count(pattern)==1
        for at in (row[1]-content.base_va+raw.index(pattern)+1,ladder[index]+8):
            new=mapped(content.base_va+at)-out.base_va
            assert new not in b.fields and struct.unpack_from("<I",b.code,new)[0]==index
            struct.pack_into("<I",b.code,new,n); scalars.append((at,new,index,n))
    expected=b.finish()
    blocks=tuple(("canonical_content_block_"+str(n),content.base_va+lo,content.base_va+hi,sha(original[lo:hi]),
                  out.base_va+start,out.base_va+start+hi-lo) for n,(lo,hi,start) in enumerate(copied))
    receipts=tuple((role,content.base_va+lo,content.base_va+hi,out.base_va+start,out.base_va+end,
                    sha(original[lo:hi]),sha(expected[start:end])) for lo,hi,start,end,role in changed)
    receipts += tuple(("site_scalar",content.base_va+at,content.base_va+at+4,out.base_va+new,out.base_va+new+4,
                       sha(struct.pack("<I",before)),sha(struct.pack("<I",after))) for at,new,before,after in scalars)
    receipts += (("authoritative_dy_helper",None,None,helper,out.base_va+len(expected),None,sha(expected[helper_start:])),)
    assert out.code==expected and out.source_blocks==blocks and out.transform_receipts==receipts
    assert out.entries==tuple((f"site_{SITES[n][0]:06x}",mapped(content.body_receipts[index][1])) for n,index in enumerate(INDICES))
    assert out.private_entries==tuple((name,mapped(va)) for name,va in content.private_entries)+(("count_expected_dy",helper),)
    assert out.body_receipts==tuple((row[0],*(mapped(va) for va in row[1:])) for row in (content.body_receipts[i] for i in INDICES))
    return b.fields


def independent_adapters(model,out,fields):
    b=Bytes(out.base_va); private=dict(model.private_entries)
    entries,guards,bodies,sources,hooks,pending=[],[],[],[],[],[]
    for n,row in enumerate(model.body_receipts):
        va,old_entry,payload,pc,denied,fault,valid=row
        end=model.body_receipts[n+1][1] if n+1<7 else private["finish_rejected"]
        lo,hi=old_entry-model.base_va,end-model.base_va
        raw=model.code[lo:hi]; start=len(b.code); entry=out.base_va+start
        b.code.extend(raw); dispatch=out.base_va+len(b.code); admission=None; finishes=[]
        for at,(kind,target,role) in fields.items():
            if not lo<=at<hi: continue
            new=start+at-lo
            if kind=="abs32": b.mark(new,kind,target,"adjacent_unit_adapter_source_absolute:"+role)
            elif at==pc-model.base_va-4: admission=new; assert target==private["admit_body"]
            elif old_entry<=target<end: b.mark(new,kind,entry+target-old_entry,"adjacent_unit_adapter_internal:source_block")
            elif target in (private["finish_rejected"],private["finish_valid"]): finishes.append(new); assert model.code[at-1]==0xe9
            else: b.mark(new,kind,target,"adjacent_unit_adapter_capture_inputs"); assert target==private["capture_inputs"]
        def unsafe(op): b.raw(op); pending.append(len(b.code)); b.word(0)
        b.raw("83fa01"); unsafe("0f85"); b.raw("39ec"); unsafe("0f85")
        b.raw("8b95"); b.word(820); b.raw("81fa"); b.operand("abs32",va+5,"natural native model body CALL return"); unsafe("0f85")
        if va==0x42f9c3:
            b.raw("89c38b85"); b.word(400); b.raw("a907000000"); unsafe("0f85"); b.raw("83f840"); unsafe("0f83"); b.raw("89d8")
        elif va==0x42f9ec:
            b.raw("89c38bb5"); b.word(216); b.raw("8b46e481f8"); b.word(682); unsafe("0f83")
            b.raw("31d2b91f000000f7f185d2"); unsafe("0f85"); b.raw("6bc01f8b8d"); b.word(372)
            b.raw("01c8"); unsafe("0f82"); b.raw("3b85"); b.word(420); unsafe("0f85"); b.raw("89d8")
        bits,destination={0x42f84a:(32,0),0x42f9af:(16,0),0x42f9c3:(16,0),0x42f9d7:(32,0),
                          0x42f9ec:(8,3),0x426f44:(32,1),0x426f54:(8,2)}[va]
        b.raw("668985" if bits==16 else "8885" if bits==8 else "8985"); b.word(784+{0:28,1:24,2:20,3:16}[destination])
        b.raw("81c4"); b.word(784); b.raw("619d8d642404")
        tail=WINDOWS[va][len(bytes.fromhex(SITES[n][1])):]
        removed=(0x2f9cc,) if va==0x42f9c3 else ()
        if removed:
            assert tail==bytes.fromhex("038738335100")
            b.mark(len(b.code)+2,"abs32",0x513338,"native_adjacent_unit_scalar_highlow")
        b.code.extend(tail); b.raw("e9"); b.operand("rel32",va+len(WINDOWS[va]),"native_adjacent_unit_resume")
        guard=out.base_va+len(b.code); b.raw("8d4c240439cd"); unsafe("0f85"); b.raw("8b042481f8")
        b.operand("abs32",entry+pc-old_entry,"actual model adapter admission CALL return"); unsafe("0f85")
        b.raw("e9"); b.operand("rel32",private["admit_body"],"native_adjacent_unit_admission_parent")
        assert admission is not None and finishes
        b.mark(admission,"rel32",guard,f"adjacent_unit_adapter_internal:admit_{va:06x}")
        for at in finishes: b.mark(at,"rel32",dispatch,f"adjacent_unit_adapter_internal:finish_{va:06x}")
        entries.append((f"site_{va:06x}",entry)); guards.append((f"admit_{va:06x}",guard))
        bodies.append((va,entry,entry+payload-old_entry,entry+pc-old_entry,entry+denied-old_entry,entry+fault-old_entry,
                       entry+valid-old_entry,dispatch,va+len(WINDOWS[va])))
        sources.append((va,old_entry,end,sha(raw),entry,pc)); hooks.append((va,WINDOWS[va],entry,"adjacent_unit_v2_operand",removed))
    terminal=out.base_va+len(b.code); b.raw("0f0b")
    for at in pending: b.mark(at,"rel32",terminal,"adjacent_unit_adapter_internal:unsafe_control")
    assert out.code==b.finish() and out.entries==tuple(entries) and out.private_entries==(("unsafe_control",terminal),)+tuple(guards)
    assert out.body_receipts==tuple(bodies) and out.source_blocks==tuple(sources) and out.planned_hooks==tuple(hooks)
    return b.fields


def independent_entry(model,field,out,model_fields):
    private=dict(model.private_entries); site,entry,payload,pc,denied,_,_=model.body_receipts[0]
    assert site==0x42f84a
    lo,hi=entry-model.base_va,payload-model.base_va
    private_lo=private["capture_inputs"]; private_hi=model.base_va+len(model.code); p=private_lo-model.base_va
    change=[at for at,row in model_fields.items() if p<=at and row==("abs32",0x42f84f,"fixed proposed body CALL return PC")]
    assert len(change)==1
    b=Bytes(out.base_va); b.code.extend(model.code[lo:hi]); pending=[]
    def unsafe(op): b.raw(op); pending.append(len(b.code)); b.word(0)
    suffix=out.base_va+len(b.code)
    b.raw("39ec"); unsafe("0f85"); b.raw("8b95"); b.word(820); b.raw("81fa")
    b.operand("abs32",0x42f95b,"natural Count draw CALL return"); unsafe("0f85")
    b.raw("8b85"); b.word(428); b.raw("8bbd"); b.word(372); b.raw("29f881c0"); b.word(-852)
    b.raw("81f8"); b.word(682); unsafe("0f83"); b.raw("31d2b91f000000f7f185d2"); unsafe("0f85")
    b.raw("8b8d"); b.word(404); b.raw("81f9"); b.word(22); unsafe("0f83")
    b.raw("39c8"); unsafe("0f85"); b.raw("6bc01f3b85"); b.word(420); unsafe("0f85")
    b.raw("8bb5"); b.word(428); b.raw("0fb746048b8f"); b.word(804); b.raw("39c8"); unsafe("0f83")
    b.raw("0fb756068b8f"); b.word(800); b.raw("39ca"); unsafe("0f83")
    b.raw("81c4"); b.word(784); b.raw("619de9"); b.operand("rel32",0x426ef0,"native_count_entry")
    guard=out.base_va+len(b.code); b.raw("8d4c240439cd"); unsafe("0f85"); b.raw("8b042481f8")
    actual_pc=out.base_va+pc-entry
    b.operand("abs32",actual_pc,"actual Count adapter admission CALL return"); unsafe("0f85")
    b.raw("e9"); guard_at=len(b.code); b.word(0)
    terminal=out.base_va+len(b.code); b.raw("0f0b"); clone=out.base_va+len(b.code); clone_at=len(b.code)
    b.code.extend(model.code[p:])
    for at,(kind,target,role) in model_fields.items():
        if lo<=at<hi:
            assert kind=="rel32"
            if target==private["capture_inputs"]: target,purpose=clone,"adjacent_unit_entry_internal:clone.capture_inputs"
            elif target==private["admit_body"]: target,purpose=guard,"adjacent_unit_entry_internal:admission_guard"
            else: assert target==denied; target,purpose=terminal,"adjacent_unit_entry_internal:unsafe_control"
            b.mark(at-lo,kind,target,purpose)
        elif p<=at<len(model.code):
            new=clone_at+at-p
            if kind=="abs32":
                target,purpose=(0x42f95b,"adjacent_unit_entry_private_native_return") if at==change[0] else (
                    target,"adjacent_unit_entry_private_absolute:"+role)
            elif private_lo<=target<private_hi:
                target,purpose=clone+target-private_lo,"adjacent_unit_entry_internal:private"
            else:
                assert target==dict(field.private_entries)["check_invocation"] and role=="private current V2 complete content receipt"
                purpose="adjacent_unit_entry_field_receipt"
            b.mark(new,kind,target,purpose)
    cloned_admit=clone+private["admit_body"]-private_lo
    b.mark(guard_at,"rel32",cloned_admit,"adjacent_unit_entry_internal:clone.admit_body")
    for at in pending: b.mark(at,"rel32",terminal,"adjacent_unit_entry_internal:unsafe_control")
    expected=b.finish(); cloned=tuple(("private_unsafe_control" if name=="unsafe_control" else name,clone+va-private_lo)
                                    for name,va in model.private_entries if private_lo<=va<private_hi)
    assert out.code==expected and out.entries==(("count_entry",out.base_va),)
    assert out.private_entries==cloned+(("admission_guard",guard),("unsafe_control",terminal))
    assert out.prefix_receipt==(0x42f956,site,entry,payload,pc,denied,sha(model.code[lo:hi]),out.base_va,suffix,actual_pc)
    assert out.private_clone_receipt==(private_lo,private_hi,sha(model.code[p:]),clone,out.base_va+len(expected),change[0],clone_at+change[0]-p)
    assert out.guard_receipts==(guard,actual_pc,cloned_admit,clone,terminal)
    assert out.source_blocks==(("unit_admission_prefix",entry,payload,sha(model.code[lo:hi]),out.base_va,suffix),
                              ("private_admission",private_lo,private_hi,sha(model.code[p:]),clone,out.base_va+len(expected)))
    assert out.planned_hooks==((0x42f956,entry_fixture.OLD_CALL,out.base_va,"count_entry",()),)
    return b.fields


class Machine(body_fixture.Machine):
    def __init__(self,tools,profile="classic",resolution="800x600",delta=0):
        hooks,deleted=[],set(); add0,del0=tools[0].Uc.hook_add,tools[0].Uc.hook_del
        def add(cpu,kind,*args,**kwargs):
            handle=add0(cpu,kind,*args,**kwargs); hooks.append((kind,handle,args,kwargs)); return handle
        def remove(cpu,handle): deleted.add(handle); return del0(cpu,handle)
        with patch.object(tools[0].Uc,"hook_add",add),patch.object(tools[0].Uc,"hook_del",remove):
            super().__init__(tools,profile,resolution,delta)
        values=emit(profile,resolution); self.atomic_model,self.atomic_adapters,self.atomic_entry=values[-3:]
        fields=independent_model(values[5],values[3],self.atomic_model)
        entry_fields=independent_entry(self.atomic_model,values[3],self.atomic_entry,fields)
        for out in values[-3:]:
            raw=bytearray(out.code)
            for r in out.relocations:
                if r.kind=="abs32": struct.pack_into("<I",raw,r.offset,r.target+delta)
            self.cpu.mem_write(out.base_va+delta,bytes(raw)); self.loaded_code.append((out.base_va+delta,bytes(raw)))
            self.unsafe_vas.update(va+delta for name,va in out.private_entries if "unsafe" in name)
        self.planned={va:(old,target,role,removed) for va,old,target,role,removed in self.atomic_adapters.planned_hooks}
        self.count_emission=self.atomic_entry  # Never silently run Entry50bf.
        excluded=[]
        for out,roles in ((self.atomic_model,fields),(self.atomic_entry,entry_fields)):
            absolute={at for at,row in roles.items() if row[0]=="abs32"}
            for start,end,_,_,_ in replay_fixture.decode(out.code,absolute):
                if out.code[start:start+2]!=b"\xf3\xaf": continue
                assert out.code[start-10]==0xb9 and out.code[start-5]==0xbf
                count=struct.unpack_from("<I",out.code,start-9)[0]
                pointer=struct.unpack_from("<I",out.code,start-4)[0]+delta
                pc=out.base_va+delta+start
                self.scan_before[pc-5]=(pc+2,pointer,count); self.scan_after[pc+2]=(pointer,count)
                excluded.append((pc,pc+1))
        assert excluded
        self.atomic_hook_receipts=[]
        for kind,handle,args,kwargs in hooks:
            if kind!=self.u.UC_HOOK_CODE or handle in deleted: continue
            values,pieces=observer.observer_slices(args,kwargs,excluded,self.on_code)
            self.cpu.hook_del(handle)
            for lo,hi in pieces:
                self.cpu.hook_add(self.u.UC_HOOK_CODE,values["callback"],values["user_data"],lo,hi,values["aux1"],values["aux2"])
            self.atomic_hook_receipts.append((values,pieces))
        assert self.atomic_hook_receipts
        for lo,hi in excluded:
            assert not any(left<=lo<=right or left<=hi<=right for _,pieces in self.atomic_hook_receipts for left,right in pieces)
            assert all(any(left<=pc<=right for _,pieces in self.atomic_hook_receipts for left,right in pieces) for pc in (lo-5,hi+1))

    def set_atomic_ancestry(self,*,caller,identity):
        assert caller in ORDINARY_RETURNS+(FINAL_RETURN,)
        self.put(self.unit_sp,caller+self.delta)
        self.put(self.unit_sp-12,0xfffffffd if caller==FINAL_RETURN else self.current_cell[1])
        self.put(MOTION+self.delta,0xfffffffd if caller==FINAL_RETURN else 5)
        self.put(ACTIVE+self.delta,identity if caller==FINAL_RETURN else 99)
        # Distinct Adjacent controls retain their ordinary authority.
        assert self.word(self.adjacent_sp-12)==self.tile_sp-20
        assert self.word(self.adjacent_sp-16)==self.current_cell[0]

    def setup_atomic(self,row,*,caller=FINAL_RETURN,identity=21,target=7,offset=16):
        self.atomic_identity=identity
        mode=self.word(self.lease_frame+40)
        if row[2]=="count":
            regs=self.setup_count_body(row,offset=offset,via_adjacent=True,input_record=identity,target_record=target)
            self.put(self.native_s-16,identity)  # Saved Unit ESI, not live Count ESI.
            self.put(self.unit_sp-28,0x12345678) # Native Unit local not assigned yet.
            regs["ESI"]=3
        else:
            regs=self.setup_native(row,index=identity,via_adjacent=True,table_offset=offset)
            regs["ESI"]=identity if row[0]==0x42f84a else 3
            self.put(self.unit_sp-28,0x12345678 if row[0]==0x42f84a else 31*identity)
            if row[3]=="owner":
                regs["EAX"],regs["ECX"],regs["EDX"]=target,self.WORLD+31*target,self.WORLD+31*identity
        self.set_atomic_ancestry(caller=caller,identity=identity)
        assert self.current_cell==(0,0) and self.word(self.lease_frame+40)==mode
        return regs

    def setup_atomic_entry(self,*,caller=FINAL_RETURN,identity=21):
        self.atomic_identity=identity
        mode=self.word(self.lease_frame+40)
        regs=self.setup_count(record=identity,via_adjacent=True,x=1,y=3)
        regs["ESI"],regs["EDX"]=identity,31*identity
        self.put(self.unit_sp-28,0x12345678)
        self.set_atomic_ancestry(caller=caller,identity=identity)
        assert regs["EBP"]==self.unit_sp-12 and self.current_cell==(0,0)
        assert self.word(self.lease_frame+40)==mode
        return regs

    def payload(self,row,target=7):
        identity=self.atomic_identity
        if row[3]=="occupant":
            nx,ny=self.neighbor
            if not (0<=nx<3 and 0<=ny<7): return 0xffffffff
            self.cpu.mem_write(self.WORLD+1534+40*nx+2*ny,struct.pack("<h",target)); return target
        if row[3]=="owner":
            self.cpu.mem_write(self.WORLD+854+31*identity,b"\x5a")
            self.cpu.mem_write(self.WORLD+854+31*target,b"\xd3"); return 0xd3
        if row[3]=="coordinate":
            value=1 if row[4]==4 else 3
            self.cpu.mem_write(self.WORLD+852+31*identity+row[4],struct.pack("<H",value)); return value
        self.cpu.mem_write(self.WORLD+852+31*identity,struct.pack("<h",34)); return 34


class SourceTests(unittest.TestCase):
    def test_all36_independent_full_model_seven_tails_entry_and_roles(self):
        source_closure()
        for profile in CONTEXT.PROFILES:
            for resolution in CONTEXT.RESOLUTIONS:
                with self.subTest(profile=profile,resolution=resolution):
                    values=emit(profile,resolution); layout,field,content=values[0],values[3],values[5]
                    model,adapters,entry=values[-3:]
                    fields=independent_model(content,field,model)
                    roles=((model,fields),(adapters,independent_adapters(model,adapters,fields)),
                           (entry,independent_entry(model,field,entry,fields)))
                    self.assertEqual(len(model.source_blocks),9); self.assertEqual(len(model.transform_receipts),23)
                    previous=values[12]
                    for out,expected in roles:
                        self.assertEqual(out.base_va,(previous.base_va+len(previous.code)+15)&~15)
                        self.assertEqual((out.state_va,out.width,out.height),(layout.rw.va,field.width,field.height))
                        self.assertLessEqual(out.base_va+len(out.code),layout.rx.va+layout.rx.size)
                        declared={r.offset:(r.kind,r.target,r.purpose) for r in out.relocations}
                        self.assertEqual(len(declared),len(out.relocations)); self.assertEqual(declared,expected)
                        absolute={at for at,row in expected.items() if row[0]=="abs32"}
                        decoded=replay_fixture.decode(out.code,absolute)
                        self.assertEqual({at for _,_,aa,_,_ in decoded for at in aa},absolute)
                        self.assertEqual({at for _,_,_,rr,_ in decoded for at in rr},{at for at,r in expected.items() if r[0]=="rel32"})
                        starts={start for start,*_ in decoded}
                        for _,_,aa,rr,ss in decoded:
                            self.assertFalse({at for at,_ in ss}&set(expected))
                            for at in aa: self.assertEqual(struct.unpack_from("<I",out.code,at)[0],expected[at][1])
                            for at in rr:
                                target=out.base_va+at+4+struct.unpack_from("<i",out.code,at)[0]
                                self.assertEqual(target,expected[at][1])
                                if out.base_va<=target<out.base_va+len(out.code): self.assertIn(target-out.base_va,starts)
                        self.assertNotIn(5,absolute); previous=out
                    self.assertEqual(tuple(r[0] for r in adapters.planned_hooks+entry.planned_hooks),tuple(r[0] for r in SITES)+(0x42f956,))
                    self.assertEqual(tuple(rva for r in adapters.planned_hooks+entry.planned_hooks for rva in r[4]),(0x2f9cc,))

    def test_complete_parent_pair_and_all_source_receipts_required(self):
        values=emit(); prefix=values[:-3]
        for n in (11,12):
            self.assertEqual(asdict(prefix[n]),asdict(body_fixture.emit()[n]))
            for name in ("code","relocations","body_receipts","source_blocks","private_entries"):
                value=getattr(prefix[n],name); changed=value[:-1]
                supplied=list(prefix); supplied[n]=replace(prefix[n],**{name:changed})
                with self.subTest(parent=n,field=name),self.assertRaises(ValueError): tool._emit_code(*supplied,**arguments())
        supplied=arguments(); supplied["template_source"]=supplied["template_source"][:-1]
        with self.assertRaises(ValueError): tool._emit_code(*prefix,**supplied)

    def test_closed_bytes_scalar_roles_private_guards_windows_and_transforms(self):
        values=emit(); content,field=values[5],values[3]; model,adapters,entry=values[-3:]
        checks=((model,lambda out:tool._model_operand_inventory(out,content,field),
                 ("source_blocks","transform_receipts","body_receipts","private_entries")),
                (adapters,lambda out:tool._adapter_operand_inventory(out,model),
                 ("source_blocks","body_receipts","private_entries","planned_hooks")),
                (entry,lambda out:tool._entry_operand_inventory(out,model,field),
                 ("prefix_receipt","private_clone_receipt","guard_receipts","source_blocks","planned_hooks")))
        for out,check,names in checks:
            for name in names:
                value=getattr(out,name); changed=value[:-1]; self.assertNotEqual(value,changed)
                with self.subTest(component=type(out).__name__,field=name),self.assertRaises(ValueError): check(replace(out,**{name:changed}))
            forged=clip.Relocation(5,"abs32",784,"forged frame address")
            with self.assertRaises(ValueError): check(replace(out,relocations=out.relocations+(forged,)))
            for at in (0,dict(out.private_entries)["unsafe_control"]-out.base_va):
                raw=bytearray(out.code); raw[at]^=1
                with self.assertRaises(ValueError): check(replace(out,code=bytes(raw)))
            row=next(r for r in out.relocations if r.kind=="abs32")
            for bad in (replace(row,kind="rel32"),replace(row,target=row.target+4),replace(row,purpose="forged")):
                changed=tuple(bad if r==row else r for r in out.relocations)
                with self.assertRaises(ValueError): check(replace(out,relocations=changed))

    def test_authored_native_authentication_adapter_not_original_proof(self):
        origin=0x426000; image=bytearray(b"\x90"*0x10100)
        def offset(raw,va,count):
            if va==0x514500 and count==64: return 0x10000
            if origin<=va and va+count<=0x430000: return va-origin
            raise ValueError("outside authored authentication map")
        def store(va,raw): image[offset(image,va,len(raw)):offset(image,va,len(raw))+len(raw)]=raw
        store(0x426ef0,bytes.fromhex("53515256575583ec0489c7"))
        for va,target in tool.COUNT_HIGHLOW+tool.CALLER_HIGHLOW+tool.PHASE_HIGHLOW: store(va,struct.pack("<I",target))
        for va,raw in WINDOWS.items(): store(va,raw)
        store(0x42f956,entry_fixture.OLD_CALL)
        table=struct.pack("<16i",*(v for pair in NEIGHBORS for v in pair)); store(0x514500,table)
        image=bytes(image)
        # Digest substitution is exact to authored buffers, never an original
        # executable admission or a genuine native instruction parity result.
        pins={image:tool.BASE_SHA256}
        for lo,hi,digest in (tool.UNIT_SPAN,tool.CALLER_WINDOW,*tool.PHASE_WINDOWS,(0x426ef0,0x426f75,tool.COUNT_SHA256)):
            raw=image[offset(image,lo,hi-lo):offset(image,lo,hi-lo)+hi-lo]; pins[raw]=digest
        mapper=SimpleNamespace(file_offset=offset)
        relocs=tuple(va-0x400000 for va,_ in tool.COUNT_HIGHLOW+tool.CALLER_HIGHLOW+tool.PHASE_HIGHLOW)
        pe=SimpleNamespace(inspect_pe=lambda raw:SimpleNamespace(image_base=0x400000),_old_relocations=lambda raw,parsed:(None,relocs))
        with patch.object(tool,"_sha",lambda raw:pins.get(raw,sha(raw))):
            tool._authenticate_native(image,image,mapper,pe,template_source=arguments()["template_source"])
            for which in (0,1):
                for va in (0x426ef0,0x426f74,0x426f0d,0x42ff7a,0x42ff7c,0x42f820,0x42f93e,0x42f95b,0x42f9ab,0x514500):
                    bad=bytearray(image); bad[offset(image,va,64 if va==0x514500 else 1)]^=1
                    supplied=[image,image]; supplied[which]=bytes(bad)
                    with self.subTest(image=which,va=hex(va)),self.assertRaises(ValueError): tool._authenticate_native(*supplied,mapper,pe)
            for changed in (relocs[:-1],relocs+(0x2ff7d,),relocs+(0x26ef1,)):
                pe._old_relocations=lambda raw,parsed,changed=changed:(None,changed)
                with self.assertRaises(ValueError): tool._authenticate_native(image,image,mapper,pe)

    def test_public_alias_capture_and_nonacceptance_metadata(self):
        def poison(*args,**kwargs): raise AssertionError("mutable issuer alias invoked")
        with patch.object(tool,"_issue",poison),patch.object(body_tool,"_issue",poison):
            for original in (b"",b"authored PE",bytearray(b"authored PE"),None):
                with self.assertRaisesRegex(ValueError,"original"): tool.emit_adjacent_unit_v2(original,"classic","800x600")
        for name in ("installed","native_executed","runtime_verified","manual_input_proof","release_accepted","promotion_ready",
                     "final_adjacent_native_parity_verified","native_motion_historical_authority_verified","native_count_parity_verified",
                     "native_callback_abi_verified","native_stack_capacity_verified","whole_chain_capacity_verified",
                     "cross_thread_immutability_verified","transient_write_prevention_verified","atomic_installation_verified"):
            self.assertIn(name,tool.FALSE_CLAIMS)
        tree=ast.parse((ROOT/tool.SOURCE).read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ("write_bytes","write_text") for n in ast.walk(tree)))
        self.assertEqual(tool.HELPER_BYTES,784); self.assertEqual(tool.PARENT_SHA256,body_fixture.BODY_SHA256)


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools=observer.parent_fixture.field_fixture.routing_fixture.lifetime.prior_fixture.machine_tools()
        if cls.tools is None: raise ImportError("required Unicorn CPU interpreter unavailable")

    def make(self,profile="classic",delta=0,mode=0):
        return Machine(self.tools,profile,delta=delta).prepare(columns=3).begin(mode)

    def assert_healthy(self,m,row,regs,value,*,flags=0xed7):
        expected=m.scalar_oracle(row,regs,value,flags)
        owner,tiles=m.record(),list(m.tiles); descriptor=bytes(m.cpu.mem_read(m.lease_frame,192))
        scans=m.scan_observations
        actual=m.invoke_replay(row,regs,flags=flags)
        self.assertEqual(m.native_stop,row[0]+m.delta+len(WINDOWS[row[0]]))
        for name in regs: self.assertEqual(actual[name],expected[name],(hex(row[0]),name))
        self.assertEqual(actual["EFLAGS"]&m.MASK,expected["EFLAGS"]&m.MASK)
        self.assertEqual(m.callbacks[m.before_callbacks:],["thread"]); self.assertFalse(m.unsafe)
        self.assertGreater(m.scan_observations,scans); self.assertIsNone(m.active_scan)
        self.assertEqual(m.record(),owner); self.assertEqual(m.tiles,tiles)
        self.assertEqual(bytes(m.cpu.mem_read(m.lease_frame,192)),descriptor)
        self.assert_helper_writes(m,regs)
        return actual

    def assert_helper_writes(self,m,regs):
        helper=regs["ESP"]-824
        for at,size in m.content_writes:
            self.assertTrue(helper-44<=at and at+size<=helper+824,(hex(at),size))
        for at,raw in m.loaded_code: self.assertEqual(bytes(m.cpu.mem_read(at,len(raw))),raw)

    def assert_entry_healthy(self,m,regs):
        # The inherited observer records actual entry to an authored 3-read
        # stub and its real RET; fresh .count_emission was explicitly selected.
        entry_fixture.CPUTests.assert_healthy(self,m,regs)
        self.assertEqual(m.count_emission,m.atomic_entry)
        self.assertEqual(m.count_entries[0][1],0x42f95b+m.delta)
        self.assert_helper_writes(m,regs)

    def assert_terminal(self,m,row,regs,*,entry=False,**options):
        owner,tiles=m.record(),list(m.tiles)
        with self.assertRaises(self.tools[0].UcError):
            (m.invoke_count(regs,**options) if entry else m.invoke_replay(row,regs,**options))
        pc=m.cpu.reg_read(m.regs["EIP"])
        self.assertIn(pc,m.unsafe_vas); self.assertEqual(bytes(m.cpu.mem_read(pc,2)),b"\x0f\x0b")
        self.assertIsNone(m.native_stop); self.assertEqual(m.record(),owner); self.assertEqual(m.tiles,tiles)
        self.assertFalse(any(m.lease_frame<=at<m.lease_frame+192 for at,_ in m.content_writes))
        self.assert_helper_writes(m,regs)
        if entry:
            self.assertEqual(m.count_entries,[]); self.assertEqual(m.count_returns,[]); self.assertEqual(m.stub_reads,[])

    def test_seven_ordinary_returns_keep_tile_y_and_ignore_final_globals(self):
        for delta in (0,0x30000):
            m=self.make("framed",delta)
            for caller in ORDINARY_RETURNS:
                for row in SITES:
                    with self.subTest(delta=delta,caller=hex(caller),site=hex(row[0])):
                        regs=m.setup_atomic(row,caller=caller)
                        self.assertEqual(m.word(m.unit_sp-12),0)
                        self.assertEqual(m.word(MOTION+delta),5); self.assertEqual(m.word(ACTIVE+delta),99)
                        self.assert_healthy(m,row,regs,m.payload(row),flags=0x246)
            del m; gc.collect()

    def test_final_authored_negative_frames_profiles_bases_modes_seven_tails(self):
        for profile in CONTEXT.PROFILES:
            for delta in (0,0x30000):
                for mode in (0,1):
                    m=self.make(profile,delta,mode)
                    for row in SITES:
                        with self.subTest(profile=profile,delta=delta,mode=mode,site=hex(row[0])):
                            regs=m.setup_atomic(row)
                            self.assertEqual(m.word(m.lease_frame+40),mode)
                            self.assertEqual(m.word(m.unit_sp-12),0xfffffffd)
                            self.assertEqual(regs["EBP"],0 if row[2]=="count" else m.unit_sp-12)
                            actual=self.assert_healthy(m,row,regs,m.payload(row))
                            if row[0]==0x42f9ec:
                                self.assertEqual(actual["EBX"]&0xff,0xd3)
                                self.assertIn((m.WORLD+854+31*21,1),m.content_reads)
                            elif row[0]==0x426f54:
                                self.assertEqual(actual["EDX"],(m.WORLD&~255)|0xd3)
                            elif row[0]==0x42f9c3:
                                self.assertIn((0x513338+delta+16,4),m.content_reads)
                                if delta: self.assertNotIn((0x513338+16,4),m.content_reads)
                    del m; gc.collect()

    def test_fresh_count_entry_coherent_self_and_natural_return_matrix(self):
        for profile in CONTEXT.PROFILES:
            for delta in (0,0x30000):
                for mode in (0,1):
                    m=self.make(profile,delta,mode)
                    for caller in (ORDINARY_RETURNS[0],FINAL_RETURN):
                        for n in (0,7,21):
                            with self.subTest(profile=profile,delta=delta,mode=mode,caller=hex(caller),n=n):
                                regs=m.setup_atomic_entry(caller=caller,identity=n)
                                self.assertEqual(m.word(m.lease_frame+40),mode)
                                self.assertEqual((regs["EAX"],regs["ESI"],regs["EDX"]),(m.WORLD+852+31*n,n,31*n))
                                self.assert_entry_healthy(m,regs)
                    del m; gc.collect()

    def test_phase_specific_invalid_witness_motion_dy_and_saved_control_before_caches(self):
        cases=((0x42f84a,"early_negative"),(0x42f84a,"early_one_past"),(0x42f9af,"later_negative"),
               (0x42f9af,"later_misaligned"),(0x42f9af,"later_one_past"),(0x426f44,"count_negative"),
               (0x426f44,"count_one_past"),(0x426f44,"dy"),(0x426f44,"offset"),
               (0x42f84a,"motion_nonnegative"),(0x42f84a,"active_mismatch"),(0x42f84a,"saved_ebp"))
        for va,fault in cases:
            m=self.make("completehd",0x30000); row=next(r for r in SITES if r[0]==va); regs=m.setup_atomic(row)
            if fault.startswith("early_"): regs["ESI"]=0xffffffff if fault.endswith("negative") else 22
            elif fault.startswith("later_"): m.put(m.unit_sp-28,{"later_negative":0xffffffe1,"later_misaligned":1,"later_one_past":682}[fault])
            elif fault.startswith("count_"): m.put(m.native_s-16,0xffffffff if fault.endswith("negative") else 22)
            elif fault=="dy": regs["EBP"]=1
            elif fault=="offset": regs["EAX"]=4
            elif fault=="motion_nonnegative": m.put(MOTION+m.delta,0); m.put(m.unit_sp-12,0)
            elif fault=="active_mismatch": m.put(ACTIVE+m.delta,7)
            else: m.put(m.unit_sp-12,0xfffffffc)
            m.protect_cached(m.u.UC_PROT_NONE); self.assert_terminal(m,row,regs)
            self.assertEqual(m.callbacks[m.before_callbacks:],[]); self.assertEqual(m.cached_reads(),[])
            del m; gc.collect()

    def test_callback_motion_active_phase_witness_local_and_paired_shadows(self):
        for row in (SITES[0],SITES[1],SITES[5]):
            faults=("motion","active","witness","paired_motion")+(("local","paired_local") if row[2]=="count" else ())
            for fault in faults:
                m=self.make("modalwidgets",0x30000); regs=m.setup_atomic(row,offset=24); m.payload(row); seen=[]
                witness=m.native_s-16 if row[2]=="count" else m.unit_sp-28
                def corrupt(mm,label):
                    if label!="thread": return
                    helper=regs["ESP"]-824
                    if fault in ("motion","paired_motion"):
                        at=MOTION+mm.delta; mm.put(at,0xfffffffc)
                        if fault=="paired_motion": mm.put(helper+380,0xfffffffc)
                    elif fault=="active": at=ACTIVE+mm.delta; mm.put(at,7)
                    elif fault in ("local","paired_local"):
                        at=mm.native_s-28; mm.put(at,mm.word(at)^1)
                        if fault=="paired_local": mm.put(helper+376,mm.word(helper+376)^1)
                    else:
                        at=helper+404 if row[0]==0x42f84a else witness
                        mm.put(at,7 if row[0]!=0x42f9af else 31*7)
                    seen.append(at); mm.protect_cached(mm.u.UC_PROT_NONE)
                m.mutation=corrupt; self.assert_terminal(m,row,regs)
                self.assertEqual(len(seen),1); self.assertEqual(m.callbacks[m.before_callbacks:],["thread"])
                self.assertEqual(m.cached_reads(post_thread=True),[])
                self.assertFalse(any(at<seen[0]+4 and at+size>seen[0] for at,size in m.content_writes)
                                 if seen[0] not in (regs["ESP"]-824+376,regs["ESP"]-824+380,regs["ESP"]-824+404) else False)
                del m; gc.collect()

    def test_entry_self_record_esi_edx_coordinates_and_nondraw_cannot_reach_stub(self):
        for fault in ("record","esi","edx","sentinel","one_past","x","y","foreign","non_draw"):
            m=self.make("classic",0x30000); regs=m.setup_atomic_entry(caller=ORDINARY_RETURNS[0]); options={}
            if fault=="record": regs["EAX"]=m.WORLD+852+31*7
            elif fault=="esi": regs["ESI"]=7
            elif fault=="edx": regs["EDX"]=31*7
            elif fault=="sentinel": regs["EAX"]=m.WORLD+821
            elif fault=="one_past": regs["EAX"]=m.WORLD+852+682
            elif fault in ("x","y"): m.cpu.mem_write(regs["EAX"]+(4 if fault=="x" else 6),struct.pack("<H",3 if fault=="x" else 7))
            else:
                options["call_pc"]=(0x42f97b if fault=="foreign" else 0x426f95)+m.delta
                m.protect_cached(m.u.UC_PROT_NONE)
            self.assert_terminal(m,None,regs,entry=True,**options)
            self.assertNotIn((regs["EAX"]+2,1),m.suffix_reads)
            if fault in ("foreign","non_draw"):
                self.assertEqual(m.callbacks[m.before_callbacks:],[]); self.assertEqual(m.cached_reads(),[])
            del m; gc.collect()

    def test_actual_body_entry_call_intrinsic_return_and_esp_corruption(self):
        for row in (SITES[0],SITES[5],None):
            for fault in ("native","intrinsic_return","intrinsic_stack"):
                m=self.make("completehd",0x30000); entry=row is None
                regs=m.setup_atomic_entry() if entry else m.setup_atomic(row)
                component=m.atomic_entry if entry else m.atomic_adapters
                guard=dict(component.private_entries)["admission_guard" if entry else f"admit_{row[0]:06x}"]+m.delta
                seen=[]; options={}
                if fault=="native": options["call_pc"]=(0x42f97b if entry else row[0]+0x25)+m.delta
                else:
                    def corrupt(mm,address):
                        if address==guard:
                            sp=mm.cpu.reg_read(mm.regs["ESP"])
                            if fault=="intrinsic_return": mm.put(sp,mm.word(sp)^4)
                            else: mm.cpu.reg_write(mm.regs["ESP"],sp-4)
                            seen.append(sp)
                    m.instruction_mutation=corrupt
                m.protect_cached(m.u.UC_PROT_NONE); self.assert_terminal(m,row,regs,entry=entry,**options)
                if fault!="native": self.assertEqual(len(seen),1)
                self.assertEqual(m.callbacks[m.before_callbacks:],[]); self.assertEqual(m.cached_reads(),[])
                del m; gc.collect()

    def test_count_local_checks_are_family_gated_and_latched_loss_is_terminal(self):
        m=self.make("modalwidgets",0x30000)
        transforms={r[0]:r for r in m.atomic_model.transform_receipts if r[0]!="site_scalar"}
        snapshot=transforms["count_local_snapshot"]; after=transforms["motion_and_count_local_match"]
        count_loads=set()
        for receipt,pattern in ((snapshot,bytes.fromhex("8b8700000000898578010000")),
                                (after,bytes.fromhex("8b87000000003b8578010000"))):
            lo,hi=receipt[3]-m.atomic_model.base_va,receipt[4]-m.atomic_model.base_va
            raw=m.atomic_model.code[lo:hi]; self.assertEqual(raw.count(pattern),1)
            count_loads.add(m.atomic_model.base_va+m.delta+lo+raw.index(pattern))
        for row in SITES[:5]:
            regs=m.setup_atomic(row); self.assert_healthy(m,row,regs,m.payload(row))
            self.assertEqual([event for event in m.content_events if event[0]=="read" and event[1] in count_loads],[])
        del m; gc.collect()
        for fault in ("loss","status","phase"):
            m=self.make("framed",0x30000); row=SITES[0]; regs=m.setup_atomic(row)
            m.put(m.state_va if fault=="phase" else m.lease_frame+(44 if fault=="loss" else 48),3 if fault=="phase" else 2)
            m.protect_cached(m.u.UC_PROT_NONE); self.assert_terminal(m,row,regs)
            self.assertEqual(m.callbacks[m.before_callbacks:],[]); self.assertEqual(m.cached_reads(),[])
            del m; gc.collect()


TEST_COUNT=sum(unittest.defaultTestLoader.loadTestsFromTestCase(cls).countTestCases() for cls in (SourceTests,CPUTests))


def run_tests():
    before=source_closure()
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in (SourceTests,CPUTests))
    result=unittest.TextTestRunner(verbosity=2,failfast=True).run(suite)
    if source_closure()!=before: raise ValueError("atomic Unit source closure changed during tests")
    if not result.wasSuccessful() or result.skipped or result.testsRun!=TEST_COUNT: raise AssertionError("atomic Unit fixture failures")
    return result.testsRun


if __name__=="__main__":
    if len(sys.argv)>1: unittest.main()
    else: run_tests()
