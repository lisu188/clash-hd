"""Uninstalled shared fresh continuation/request preparation.

One rebuilt guard retains all43 post-return contracts and adds13 owning query
frames. EffectS-4/-12, actual source CALL words and native arguments are bounded
and rechecked. No V1 guard, native sprite replay, provider record or installer
is used. Requests die with their own stack frame and prove no provider lifetime.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import struct
import sys
import types
import uuid

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "src/patcher/battle_profile_primitive_request_v2.py"
PARENT = "src/patcher/battle_profile_continuation_v2.py"
PARENT_SHA = "2723321d508dd8b7775bb15d65180212a157ec356ce6f28f661bbe68fe374a9d"
BASE_SHA = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
HELPER_BYTES, CONTROL_SHADOW, THUNK_BYTES = 1616, 784, 80
ARGUMENT_SHADOW, REQUEST_S, EFFECT_S, ANCESTRY_EBP = 1488, 1520, 1524, 192
ROWS_OFFSET, ROW_CAPACITY = 512, 24
TAG, SCHEMA, REQUEST_BYTES = 0x50525132, 2, 64
PREPARED, MALFORMED, EMPTY, FAULT = 1, 2, 3, 4
REQUEST_SITES = (
    (0x430035,"sprite","tile",100,"ff5734"), (0x4300f3,"sprite","tile",100,"ff5734"),
    (0x43024e,"sprite","tile",100,"ff5734"), (0x430349,"sprite","tile",100,"ff5734"),
    (0x430733,"sprite","tile",100,"ff5734"), (0x4307aa,"sprite","tile",100,"ff5734"),
    (0x43080c,"sprite","tile",100,"ff5734"), (0x430991,"sprite","tile",100,"ff5734"),
    (0x42fc1b,"sprite","unit",96,"ff5734"), (0x405552,"sprite","tracking",48,"ff5534"),
    (0x4055b3,"sprite","charge",60,"ff5734"), (0x430ad5,"line","tile",80,"ff5714"),
    (0x430b07,"line","tile",80,"ff5714"),
)
EFFECT_SPANS = (
    (0x405510,0x40555e,"1ea056df0dc3725cfe0d9a867fc3624cd600848775f174440c40c0165b388115"),
    (0x405560,0x4055bf,"d604c56eec02334318a3c64af773c1c3298fcc4cef8a82cbba30ac70b5aea32f"),
)
ARGUMENT_WINDOWS = (
    (0x42fff9,0x430038,"7a5c4f0afa84d8f5cf475b9057593e9c16b9009df8bf951823ef17f3ae9ed62d",(196617,196642)),
    (0x4300b5,0x4300f6,"3920a15f9a3fa85ee400e24fe9d0ecff422c7a60a2bec49a7fef5a8825ee92d8",(196810,196832)),
    (0x430213,0x430251,"f3413b573911f1364ea45e9eca0d774fb1bf10de201755c0d495fd0b5059070f",(197157,197179)),
    (0x43030b,0x43034c,"daf8d990b55979654a95293efe9e448a6d86a74b314ec525a83460bf5c3c4a09",(197399,197416)),
    (0x4306f3,0x430736,"18b4c0fb8d0802c6f9c5adb03e9c4b1086f8a310966854906842a3dd60fe5a44",(198392,198399,198405,198437)),
    (0x43076c,0x4307ad,"29ec2ca0234ec4acef6196b569c34b1a4c092d8e57b27e600ceff4084b31da5b",(198516,198533)),
    (0x4307ce,0x43080f,"cf4986f568f3e45fe87bdfc3153096a7acd2b1af440e312d74f8a23c09017411",(198622,198639)),
    (0x430953,0x430994,"d8abd2877e52781af111a18059476c3e1f92055f1e9d62eb3162b215c43aa16d",(199016,199038)),
    (0x42fbdc,0x42fc1e,"6dd743e143ae74a1908c48bf43002b35e22be2a34a63763087645edf7e23f0e4",(195593,)),
    (0x405512,0x405555,"16f91a6a8e0b9b129323b02846cafeb703b97458ea9c835334638abf9bc2a2c2",(21786,21802)),
    (0x405577,0x4055b6,"4f4782f77db34ea044c48d9e96581e3703502ae5ce137242c6e7a0c02bbc9a6e",()),
    (0x430a96,0x430ad8,"2dda9b72729373ffcd8ed8d102ed253053af70a74fc0bf6771fa657ddae0620f",(199349,)),
    (0x430acc,0x430b0a,"ff64ac66854ff3b59f20790c22294bdef17e458947ce81421659e758c37300ce",(199393,)),
)
FALSE_CLAIMS = ("installed", "battle_installed", "installation_ready", "native_sprite_replay_emitted",
    "provider_validity_verified", "provider_lifetime_verified", "native_callback_abi_verified",
    "native_stack_capacity_verified", "whole_chain_capacity_verified", "historical_motion_authority_verified",
    "sprite_rle_verified", "intra_decoder_cancellation", "atomic_installation_verified", "runtime_verified",
    "input_verified", "healthy_map_return_verified", "release_accepted", "promotion_ready")


def _require(value, message):
    if not value:
        raise ValueError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path):
    _require(path.is_absolute() and path.is_relative_to(ROOT) and path.resolve(strict=True) == path,
             "canonical shared request source required")
    for part in (path, *path.parents):
        info = part.lstat()
        _require(not part.is_symlink() and not getattr(info, "st_file_attributes", 0) & 0x400,
                 "shared request source reparse forbidden")
    before = path.stat()
    _require(0 < before.st_size <= 2*1024*1024, "bounded shared request source required")
    raw = path.read_bytes()
    after = path.stat()
    stamp = lambda item: (item.st_dev,item.st_ino,item.st_size,item.st_mtime_ns,getattr(item,"st_file_attributes",0))
    _require(stamp(before) == stamp(after) and len(raw) == after.st_size, "shared request source changed")
    return raw, stamp(after)


@contextmanager
def _parent_module(raw):
    _require(type(raw) is bytes and _sha(raw) == PARENT_SHA, "complete fresh continuation V2 required")
    name = "_shared_request_parent_"+uuid.uuid4().hex
    module = types.ModuleType(name)
    module.__file__ = str(ROOT/PARENT)
    module.__loaded_source_sha256__ = PARENT_SHA
    module.__canonical_continuation_v2_issuer__ = True
    _require(sys.modules.setdefault(name, module) is module, "shared request namespace occupied")
    try:
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
        yield module
    finally:
        changed = sys.modules.get(name) is not module
        if not changed:
            del sys.modules[name]
        _require(not changed, "shared request namespace changed")


def _snapshot():
    parent = _read(ROOT/PARENT)
    with _parent_module(parent[0]) as module:
        snapshot = module._snapshot()
    own = _read(ROOT/SOURCE)
    _require(snapshot[PARENT] == parent and globals().get("__loaded_source_sha256__") == _sha(own[0]),
             "private complete shared request graph required")
    return snapshot | {SOURCE: own}


@dataclass(frozen=True)
class PrimitiveRequestV2Emission:
    base_va: int
    state_va: int
    code: bytes
    entries: tuple
    relocations: tuple
    width: int
    height: int
    private_entries: tuple
    planned_hooks: tuple
    field_call_patches: tuple
    adapter_receipts: tuple
    guard_source_sha256: str
    source_transforms: tuple
    request_sites: tuple = REQUEST_SITES
    request_returns: tuple = ()


@dataclass(frozen=True)
class PrimitiveRequestV2Bundle:
    emission: PrimitiveRequestV2Emission
    joined_field_emission: object
    continuation_bundle: object
    metadata_json: str
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()

    def metadata(self):
        return json.loads(self.metadata_json)


def _edit(source, old, new):
    _require(source.count(old) == 1, "one exact fresh shared guard boundary required: "+old[:70])
    return source.replace(old, new)


def _guard_source(continuation, atomic, content, template_source, template, rows):
    source, transforms, namespace, _ = continuation._guard_source(atomic, content, template_source, template, rows)
    edits = list(transforms)
    def edit(old, new):
        nonlocal source
        source = _edit(source, old, new)
        edits.append((old, new, 1))
    edit("ROWS,ROW_COUNT,WORLD,X,Y,INDEX,EA=240,368,372,376,380,384,388",
         "ROWS,ROW_COUNT,WORLD,X,Y,INDEX,EA=512,368,372,376,380,384,388")
    edit("cmp(1,16);a.branch('0f83','capture_stack.reject')", "cmp(1,24);a.branch('0f83','capture_stack.reject')")
    edit("extent(7,HELPER_BYTES+140,reject)", "extent(7,HELPER_BYTES+204,reject)")
    # Common intrinsic checks are hoisted, with the per-site outer CALL word
    # still checked in each row. No native/data check is dropped for size.
    common = "        a.emit('8d4c240439cd');ne(reject)\n"+\
        "        a.emit('8b0424');cmpva(0,admit_return_pc,'fixed continuation helper admission CALL return');ne(reject)\n"
    edit(common, "")
    edit("        get(7,NATIVE_S)\n", "")
    edit("    for number,(va,raw,family,op,dx,dy) in enumerate(SITES):\n",
         "    a.emit('8d4c240439cd');ne(reject)\n"
         "    a.emit('8b0424');cmpva(0,admit_return_pc,'fixed shared request helper admission CALL return');ne(reject)\n"
         "    get(7,NATIVE_S);put(7,REQUEST_S)\n"
         "    for number,(va,raw,family,op,dx,dy) in enumerate(SITES):\n")
    edit("    for number,family in enumerate(FAMILIES):\n",
         "    get(0,INPUT+8);put(0,ANCESTRY_EBP)\n"
         "    get(0,SITE);cmp(0,43);a.branch('0f83','ancestry.request')\n"
         "    for number,family in enumerate(FAMILIES):\n")
    edit("    a.label('ancestry.count')\n", _request_ancestry_source()+"    a.label('ancestry.count')\n")
    edit("    a.label('ebp.compare');get(0,INPUT+8);a.emit('39f8');ne(reject)",
         "    a.label('ebp.compare');get(0,ANCESTRY_EBP);a.emit('39f8');ne(reject)")
    early = "        get(0,SITE)\n        for early_post in early_unit_posts:cmp(0,early_post);eq(label+'.early')\n"
    edit(early,
         "        get(0,SITE);cmp(0,52);eq(label+'.effect.tracking');cmp(0,53);eq(label+'.effect.saved')\n"
         "        cmp(0,51);eq(label+'.early')\n"
         "        for early_post in early_unit_posts:cmp(0,early_post);eq(label+'.early')\n"
         "        jump(label+'.late')\n"
         "        a.label(label+'.effect.tracking');get(7,EFFECT_S);load(0,7,0)\n"
         "        cmpva(0,0x42fa7c,'late Tracking Unit source phase');eq(label+'.late')\n"
         "        a.label(label+'.effect.saved');get(7,EFFECT_S);load(0,7,-4);jump(label+'.identity')\n"
         "        a.label(label+'.late')\n")
    edit("    control_capture();mutable_capture()\n", _argument_source("capture")+"    control_capture();mutable_capture()\n")
    edit("    put(0,THREAD_RESULT);control_match()\n",
         "    put(0,THREAD_RESULT);control_match()\n"+_argument_source("match"))
    old_rows = "    for n in range(16):\n"+\
        "        get(0,ROW_COUNT);cmp(0,n);a.branch('0f86',f'rows.done.{n}')\n"+\
        "        get(7,ROWS+8*n);extent(7,4,reject);load(0,7,0);match(0,ROWS+8*n+4);ne(reject);a.label(f'rows.done.{n}')\n"
    edit(old_rows, "    get(0,ROW_COUNT);cmp(0,24);a.branch('0f87',reject)\n"
         "    imm(0,0);put(0,196);a.label('request.rows.next')\n"
         "    get(0,196);get(1,ROW_COUNT);a.emit('39c8');a.branch('0f83','request.rows.done')\n"
         "    a.emit('8dbcc5');a.u32(ROWS);load(7,7,0);extent(7,4,reject);load(0,7,0)\n"
         "    get(1,196);a.emit('8db4cd');a.u32(ROWS);mem('3b',0,6,4);ne(reject)\n"
         "    get(0,196);add(0,1);put(0,196);jump('request.rows.next');a.label('request.rows.done')\n")
    authority = tuple(range(200, 236, 4))+tuple(range(368, 392, 4))+tuple(range(ROWS_OFFSET, ROWS_OFFSET+8*ROW_CAPACITY, 4))
    extra = (ANCESTRY_EBP, REQUEST_S, EFFECT_S)+tuple(range(ARGUMENT_SHADOW, ARGUMENT_SHADOW+28, 4))
    control = authority+tuple(range(400,436,4))+tuple(range(HELPER_BYTES,HELPER_BYTES+156,4))+(-4,)+extra
    _require(CONTROL_SHADOW+4*len(control) <= ARGUMENT_SHADOW and ARGUMENT_SHADOW+28 <= REQUEST_S
             and EFFECT_S+4 <= HELPER_BYTES, "disjoint shared request private shadows required")
    namespace.update(HELPER_BYTES=HELPER_BYTES, CONTROL_SHADOW=CONTROL_SHADOW, AUTHORITY_LOCALS=authority,
        CONTROL_SLOTS=control, REQUEST_S=REQUEST_S, EFFECT_S=EFFECT_S, ANCESTRY_EBP=ANCESTRY_EBP,
        ARGUMENT_SHADOW=ARGUMENT_SHADOW, REQUEST_SITES=REQUEST_SITES,
        SITES=tuple((va,"",family,"post",0,0) for va,family,_ in rows)+
            tuple((pc,"","tile" if owner=="tile" else "unit","request",0,0) for pc,_,owner,_,_ in REQUEST_SITES))
    return source, tuple(edits), namespace, control


def _request_ancestry_source():
    return """    a.label('ancestry.request');get(7,REQUEST_S);extent(7,32,reject)
    for i,(pc,primitive,owner,delta,raw) in enumerate(REQUEST_SITES):
        get(0,SITE);cmp(0,43+i);ne('request.ancestry.next.'+str(i))
        get(7,REQUEST_S);add(7,delta)
        if owner in ('tile','unit'):jump('ancestry.'+owner)
        else:
            put(7,EFFECT_S);record(7,4,reject)
            get(7,EFFECT_S);add(7,-12);record(7,4,reject)
            get(7,EFFECT_S);add(7,-4);record(7,4,reject)
            get(7,EFFECT_S);load(0,7,-12);put(0,ANCESTRY_EBP)
            if owner=='tracking':
                get(0,INPUT+8);cmpva(0,0x50ee24,'Tracking memory vtable EBP');ne(reject)
                get(7,EFFECT_S);load(0,7,0)
                cmpva(0,0x43087d,'Tracking Tile native caller');eq('request.tracking.tile')
                returns(0,(0x42fa7c,0x42fbbd),'request.tracking.unit');jump(reject)
            else:
                get(6,REQUEST_S);load(0,6,8);match(0,INPUT+8);ne(reject)
                get(7,EFFECT_S);load(0,7,0);cmpva(0,0x42f932,'Charge Unit native caller');ne(reject)
                get(7,EFFECT_S);add(7,100);jump('ancestry.unit')
        a.label('request.ancestry.next.'+str(i))
    jump(reject)
    a.label('request.tracking.tile');imm(0,0);put(0,KIND);get(7,EFFECT_S);add(7,92);jump('ancestry.tile')
    a.label('request.tracking.unit');get(7,EFFECT_S);add(7,88);jump('ancestry.unit')
"""


def _argument_source(mode):
    rows = """    get(0,SITE);cmp(0,43);a.branch('0f82','request.arguments.MODE.done')
    get(7,REQUEST_S);extent(7,32,reject)
    get(0,SITE);cmp(0,54);a.branch('0f83','request.arguments.MODE.line')
    for argument in range(0,28,4):
        get(7,REQUEST_S);load(0,7,4+argument);OPERATION
    jump('request.arguments.MODE.done')
    a.label('request.arguments.MODE.line')
    for argument in (0,4):
        get(7,REQUEST_S);load(0,7,4+argument);OPERATION
    a.label('request.arguments.MODE.done')
""".replace("MODE", mode)
    operation = "put(0,ARGUMENT_SHADOW+argument)" if mode == "capture" else "match(0,ARGUMENT_SHADOW+argument);ne(reject)"
    return rows.replace("OPERATION", operation)


def _raw_guard(layout, field, lease, guard_base, admit_return_pc, thunk_returns, rows, *, continuation,
               atomic_module, content_module, template_module, template_source, assembler_module):
    source, transforms, namespace, _ = _guard_source(continuation, atomic_module, content_module,
        template_source, template_module, rows)
    modal = [span for span in layout.protected_spans if span.role == "parent:.hdstate"]
    _require(len(modal) == int(layout.profile in ("completehd", "modalwidgets")), "shared request modal identity differs")
    plan = {"profile": layout.profile}
    def captured(supplied, parent):
        _require(supplied is plan and parent is lease, "canonical fresh shared request lease required")
        return layout.rx.va,layout.rw.va,field.width,field.height,dict(field.private_entries)["check_invocation"]
    namespace.update(_layout=captured, model_base=guard_base, modal_va=None if not modal else modal[0].va,
        protected_intervals=((layout.rx.va,layout.rx.va+layout.rx.size),(layout.rw.va,layout.rw.va+layout.rw.size))+
            (() if not modal else ((modal[0].va,modal[0].va+modal[0].size),)),
        admit_return_pc=admit_return_pc, thunk_returns=thunk_returns)
    exec(compile(source, str(ROOT/SOURCE)+"#shared_guard", "exec"), namespace)
    parent = assembler_module._Assembler
    class CompleteAssembler(parent):
        def finish(self):
            code = super().finish()
            for offset,label in self.fixups:
                self.relocations.append(assembler_module.Relocation(offset,"rel32",self.base+self.labels[label],
                    "shared_request_guard_internal:"+label))
            return code
    assembler = types.SimpleNamespace(_Assembler=CompleteAssembler,Relocation=assembler_module.Relocation,
        absolute_relocation_offsets=assembler_module.absolute_relocation_offsets)
    guard = namespace["_versioned_emit_code"](plan,lease,assembler_module=assembler)
    _require(guard.base_va == guard_base and guard.entries == (), "one shared request guard extent required")
    return guard,source,transforms,()


def _append_requests(a, base, entries, calls):
    returns = []
    for index,(pc,kind,owner,delta,raw) in enumerate(REQUEST_SITES):
        name = "request_"+str(index)
        a.label(name); entries.append((name,base+len(a.code)))
        a.emit("9c60fc83ec50c7042400000000c744240400000000c7442408");a.u32(43+index)
        a.emit("c744240c");a.u32(0 if owner == "tile" else 1)
        a.branch("e8","helper");calls.append(base+len(a.code));returns.append(calls[-1])
        # The typed request is live only at ESP+16..80 at this point. The
        # query changes EDX=status, preserving caller EAX/flags/other GPRs.
        a.emit("8954246483c450619dc3")
    return tuple(returns)


def _append_payload(a, width):
    def imm(reg,value):a.emit(f"{0xb8+reg:02x}");a.u32(value)
    def mem(op,reg,base,offset):
        a.emit(op+f"{0x80|(reg<<3)|base:02x}")
        if base == 4:a.emit("24")
        a.u32(offset)
    def get(reg,offset):mem("8b",reg,5,offset)
    def put(reg,offset):mem("89",reg,5,offset)
    def load(reg,base,offset):mem("8b",reg,base,offset)
    def cmp(reg,value):a.emit(f"81{0xf8+reg:02x}");a.u32(value)
    def branch(op,label):a.branch(op,label)
    def result(status):imm(2,status);branch("e9","request.publish")
    a.label("request.payload")
    a.emit("31c08dbd80000000b910000000fcf3ab")
    for offset,value in ((128,TAG),(132,SCHEMA),(136,REQUEST_BYTES)):
        imm(0,value);put(0,offset)
    for source,destination in ((428,148),(420,144),(416,152),(424,156)):
        get(0,source);put(0,destination)
    get(0,428);get(7,220);load(1,7,1040);a.emit("39c8");branch("0f85","request.fault")
    a.emit("81f8");a.absolute(0x51d4c0,"reject literal primary request receiver")
    branch("0f84","request.fault")
    get(7,372);load(0,7,804);cmp(0,(width-192)//64);branch("0f86","request.columns")
    imm(0,(width-192)//64);a.label("request.columns");a.emit("c1e00683c01f");put(0,196)
    get(0,200);cmp(0,54);branch("0f83","request.line")
    imm(0,1);put(0,140)
    for offset in range(0,28,4):get(0,ARGUMENT_SHADOW+offset);put(0,160+offset)
    for offset in (160,164,168,172):
        get(0,offset);cmp(0,0xffffffff);branch("0f85","request.sprite.finite")
    imm(0,32);put(0,160);imm(0,16);put(0,164)
    get(0,196);put(0,168);imm(0,463);put(0,172);result(PREPARED)
    a.label("request.sprite.finite")
    for left,right in ((160,168),(164,172)):
        get(0,left);mem("3b",0,5,right);branch("0f8f","request.malformed")
    for offset,low in ((160,32),(164,16)):
        get(0,offset);cmp(0,low);branch("0f8d","request.sprite.low."+str(offset))
        imm(0,low);put(0,offset);a.label("request.sprite.low."+str(offset))
    get(0,168);mem("3b",0,5,196);branch("0f8e","request.sprite.right")
    get(0,196);put(0,168);a.label("request.sprite.right")
    get(0,172);cmp(0,463);branch("0f8e","request.sprite.bottom")
    imm(0,463);put(0,172);a.label("request.sprite.bottom")
    for left,right in ((160,168),(164,172)):
        get(0,left);mem("3b",0,5,right);branch("0f8f","request.empty")
    result(PREPARED)
    a.label("request.line");imm(0,2);put(0,140)
    for source,destination in ((420,160),(416,164),(424,168)):
        get(0,source);a.emit("25ffff0000");put(0,destination)
    get(0,ARGUMENT_SHADOW);a.emit("25ffff0000");put(0,172)
    get(0,ARGUMENT_SHADOW+4);put(0,176)
    get(0,164);mem("3b",0,5,172);branch("0f85","request.line.vertical")
    get(0,160);mem("3b",0,5,168);branch("0f87","request.malformed")
    get(0,164);cmp(0,16);branch("0f82","request.empty");cmp(0,463);branch("0f87","request.empty")
    get(0,160);cmp(0,32);branch("0f83","request.line.left")
    imm(0,32);put(0,160);a.label("request.line.left")
    get(0,196);get(1,176);a.emit("f7c100010000");branch("0f84","request.line.right.bound");a.emit("40")
    a.label("request.line.right.bound");get(1,168);a.emit("39c1");branch("0f86","request.line.right.done")
    put(0,168);a.label("request.line.right.done");branch("e9","request.line.nonempty")
    a.label("request.line.vertical")
    get(0,164);mem("3b",0,5,172);branch("0f87","request.malformed")
    get(0,160);cmp(0,32);branch("0f82","request.empty");mem("3b",0,5,196);branch("0f87","request.empty")
    get(0,164);cmp(0,16);branch("0f83","request.line.top")
    imm(0,16);put(0,164);a.label("request.line.top")
    imm(0,463);get(1,176);a.emit("f7c100010000");branch("0f84","request.line.bottom.bound");a.emit("40")
    a.label("request.line.bottom.bound");get(1,172);a.emit("39c1");branch("0f86","request.line.bottom.done")
    put(0,172);a.label("request.line.bottom.done")
    get(0,164);get(1,172);branch("e9","request.line.compare")
    a.label("request.line.nonempty");get(0,160);get(1,168)
    a.label("request.line.compare");a.emit("39c8");branch("0f87","request.empty")
    get(1,176);a.emit("f7c100010000");branch("0f84","request.line.prepared")
    get(1,416);a.emit("81e1ffff0000");get(3,ARGUMENT_SHADOW);a.emit("81e3ffff0000")
    a.emit("39d9");branch("0f85","request.line.dashed.vertical")
    get(1,168);branch("e9","request.line.dashed.compare")
    a.label("request.line.dashed.vertical");get(1,172)
    a.label("request.line.dashed.compare");a.emit("39c8");branch("0f84","request.empty")
    a.label("request.line.prepared");result(PREPARED)
    a.label("request.empty");result(EMPTY)
    a.label("request.malformed");result(MALFORMED)
    a.label("request.fault");imm(2,FAULT)
    a.label("request.publish");put(2,188)
    a.emit("8db5800000008dbd");a.u32(HELPER_BYTES+56);a.emit("b910000000fcf3a5")
    get(0,428);put(0,HELPER_BYTES+28);put(2,HELPER_BYTES+20)
    branch("e9","helper.restore")


def _raw_emit(*values, continuation, **kwargs):
    raw = _read(ROOT/PARENT)[0]
    _require(_sha(raw) == PARENT_SHA, "complete fresh continuation composition source required")
    tree = ast.parse(raw)
    node = next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name == "_raw_emit")
    source = ast.get_source_segment(raw.decode(),node)
    source = _edit(source,"83ec10c7042400000000", "83ec50c7042400000000")
    source = _edit(source,"83c410619d8d642404", "83c450619d8d642404")
    source = _edit(source,"    field_patches = []\n", "    request_returns = _append_requests(a,base,entries,calls)\n    field_patches = []\n")
    old = "    for slot in tuple(range(200, 236, 4))+tuple(range(240, 392, 4)):\n"+\
        "        a.emit(\"c785\"); a.u32(slot); a.u32(0)\n"
    source = _edit(source,old,"    for low,count in ((192,50),(512,48),(1488,10)):\n"
        "        a.emit('31c08dbd');a.u32(low);a.emit('b9');a.u32(count);a.emit('fcf3ab')\n")
    source = _edit(source,"a.u32(HELPER_BYTES+92)","a.u32(HELPER_BYTES+156)")
    source = _edit(source,"    a.emit(\"8985\"); a.u32(HELPER_BYTES+28)\n",
        "    a.emit('8b85');a.u32(200);a.emit('83f82b');branch('normal.finish','0f82');branch('request.payload')\n"
        "    a.label('normal.finish');a.emit('b801000000')\n"
        "    a.emit(\"8985\"); a.u32(HELPER_BYTES+28)\n    a.label('helper.restore')\n")
    source = _edit(source,"    guard_base = (base+len(a.code)+15)&~15\n",
        "    _append_payload(a,field.width)\n    guard_base = (base+len(a.code)+15)&~15\n")
    source = _edit(source,"    return out", "    return replace(out,request_returns=request_returns)")
    namespace = dict(continuation.__dict__)
    def guard(*args, **supplied):
        return _raw_guard(*args,continuation=continuation,**supplied)
    namespace.update(HELPER_BYTES=HELPER_BYTES,CONTROL_SHADOW=CONTROL_SHADOW,
        ContinuationV2Emission=PrimitiveRequestV2Emission,_append_requests=_append_requests,
        _append_payload=_append_payload,_raw_guard=guard,replace=replace)
    exec(compile(source,str(ROOT/SOURCE)+"#whole_shared_composition","exec"),namespace)
    out = namespace["_raw_emit"](*values,**kwargs)
    _require(len(out.request_returns) == 13 and len({pc for pc in out.request_returns}) == 13,
             "all13 live owning request returns required")
    return out


def _authenticate_native(original, relayout, clip, pe):
    for image in (original,relayout):
        parsed = pe.inspect_pe(image)
        _,relocations = pe._old_relocations(image,parsed)
        for low,high,digest in EFFECT_SPANS:
            at = clip.file_offset(image,low,high-low)
            _require(_sha(image[at:at+high-low]) == digest, "whole original effect span differs")
            expected = {0x40551a,0x40552a} if low == 0x405510 else {0x405569}
            _require({parsed.image_base+rva for rva in relocations if low <= parsed.image_base+rva < high} == expected,
                     "complete effect span HIGHLOW inventory differs")
        for low,high,digest,expected in ARGUMENT_WINDOWS:
            at = clip.file_offset(image,low,high-low)
            _require(_sha(image[at:at+high-low]) == digest, "whole native request argument window differs")
            _require(tuple(sorted(rva for rva in relocations if low <= parsed.image_base+rva < high)) == expected,
                     "complete native argument HIGHLOW inventory differs")
        for pc,_,_,_,old in REQUEST_SITES:
            at = clip.file_offset(image,pc,3)
            _require(image[at:at+3] == bytes.fromhex(old), "actual native primitive CALL differs")


def _issue(original, profile, resolution):
    _require(type(original) is bytes and _sha(original) == BASE_SHA, "exact fresh primitive request original required")
    snapshot = _snapshot()
    with _parent_module(snapshot[PARENT][0]) as continuation:
        _require(profile in continuation.PROFILES and resolution in continuation.RESOLUTIONS,
                 "selected shared request profile/preset required")
        parent = continuation._issue(original,profile,resolution)
        atomic_bundle = parent.adjacent_unit_bundle
        body = atomic_bundle.count_body_bundle
        replay = body.count_entry_bundle.content_replay_bundle
        loss_bundle = replay.tile_replay_bundle.field_loss_bundle
        content = loss_bundle.content_bundle
        lease,field = content.lease_bundle,content.lease_bundle.field_bundle
        context = field.routing_bundle.lifecycle_bundle.allocation_context
        with continuation._parent_module(snapshot[continuation.PARENT][0]) as atomic:
            with continuation._graph(atomic,snapshot) as (content_module,modules):
                _authenticate_native(original,context.relayout_parent,modules[continuation.CLIP],modules[continuation.PE])
                out = _raw_emit(context.layout,field.emission,lease.emission,content.emission,
                    loss_bundle.emission,loss_bundle.joined_field_emission,atomic_bundle.model_emission,
                    atomic_bundle.emission,atomic_bundle.count_entry_emission,continuation=continuation,
                    atomic_module=atomic,content_module=content_module,template_module=modules[continuation.TEMPLATE],
                    template_source=snapshot[continuation.TEMPLATE][0],ledger_source=snapshot[continuation.LEDGER][0],
                    loss_module=continuation._loss_module(snapshot),assembler_module=modules[continuation.CLIP])
                joined = continuation._join_field(loss_bundle.joined_field_emission,out)
        metadata = dict(schema="clash95_battle_profile_primitive_request_v2",profile=profile,resolution=resolution,
            original_sha256=BASE_SHA,source_hashes=parent.metadata()["source_hashes"]|
                {name:_sha(raw) for name,(raw,_) in snapshot.items()},
            parent_candidate_sha256=_sha(context.parent),relayout_parent_sha256=_sha(context.relayout_parent),
            validation_stage=context.layout.validation_stage,code_sha256=_sha(out.code),code_va=out.base_va,
            code_bytes=len(out.code),guard_source_sha256=out.guard_source_sha256,
            joined_field_sha256=_sha(joined.code),normal_return_windows=43,field_loss_tail_joins=2,
            request_count=13,request_frame_bytes=64,outer_thunk_bytes=80,helper_frame_bytes=HELPER_BYTES,
            ancestor_row_capacity=ROW_CAPACITY,ancestor_rows_offset=ROWS_OFFSET,control_shadow_offset=CONTROL_SHADOW,
            argument_shadow_offset=ARGUMENT_SHADOW,native_argument_bytes=dict(sprite=28,line=8),
            effect_identity=dict(early="bounded/rechecked EffectS-4 saved Unit ESI",saved_unit_ebp="EffectS-12",
                late_tracking_return=0x42fa7c,late="bounded/rechecked UnitS-28 divisible31",historical_authority=False),
            request_sites=[dict(va=pc,primitive=kind,owner=owner,original_callee_entry_delta=delta,old_call_bytes=old,
                query_entry_va=dict(out.entries)["request_"+str(index)],query_return_pc=out.request_returns[index],
                query_native_call_word=pc+5,native_hook_supplied=False)
                for index,(pc,kind,owner,delta,old) in enumerate(REQUEST_SITES)],
            query_statuses=dict(prepared=PREPARED,malformed=MALFORMED,empty=EMPTY,fault=FAULT),
            request_lifetime="own thunk ESP+16..80 only before its teardown; no retained pointer",
            shared_guard_count=1,provider_schema=context.layout.provider_schema,provider_records_emitted=0,
            prefix_rx_remaining_bytes=context.layout.rx.va+context.layout.rx.size-out.base_va-len(out.code),
            installed_hooks=[],candidate_written=False,preparation_only=True,
            limitations=["Query thunks supply no native primitive replay or complete native CALL replacement window.",
                "Copied sprite/provider scalars have no validated storage, allocation provenance or lifetime.",
                "Current motion/identity and saved-register equality are not historical authority or native mapped-stack capacity.",
                "The zero-provider fresh/inherited RW tails remain required and unchanged.",
                "Native sprite/RLE, atomic installation, presentation/input/quit and full battle remain unfinished."],
            **{name:False for name in FALSE_CLAIMS})
    _require(all(_read(ROOT/name) == row for name,row in snapshot.items()), "shared request source graph changed")
    return PrimitiveRequestV2Bundle(out,joined,parent,json.dumps(metadata,sort_keys=True,separators=(",",":")))


def _production_factory():
    from hashlib import sha256
    from pathlib import Path as SourcePath
    from types import ModuleType
    from sys import modules
    from uuid import uuid4
    path = SourcePath(__file__).absolute()
    if path != path.parents[2]/SOURCE:
        raise ValueError("canonical fresh request producer required")
    raw,stamp = _read(path)
    module = ModuleType("_fresh_request_issuer_"+uuid4().hex)
    module.__file__ = str(path)
    module.__loaded_source_sha256__ = sha256(raw).hexdigest()
    module.__canonical_primitive_request_v2_issuer__ = True
    if modules.setdefault(module.__name__,module) is not module:
        raise ValueError("fresh request issuer occupied")
    try:
        exec(compile(raw,str(path),"exec"),module.__dict__)
        issue,read = module._issue,module._read
    finally:
        if modules.get(module.__name__) is not module:
            raise ValueError("fresh request issuer changed")
        del modules[module.__name__]
    if read(path) != (raw,stamp):
        raise ValueError("fresh request source changed during capture")
    def dispatch(original,profile,resolution):
        if read(path) != (raw,stamp):
            raise ValueError("captured fresh request source differs")
        try:
            return issue(original,profile,resolution)
        finally:
            if read(path) != (raw,stamp):
                raise ValueError("captured fresh request source changed")
    return dispatch


if not globals().get("__canonical_primitive_request_v2_issuer__",False):
    emit_primitive_request_v2 = _production_factory()
