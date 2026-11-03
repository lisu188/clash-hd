"""Uninstalled two-Line successor over the pinned fresh shared request guard.

Two complete native windows replace their overlapping post-return receipts.
Only the literal memory vtable and closed callback-free memory-line target are
admitted. Sprite queries and all empty-provider/RW-zero rules remain intact.
Source emission is not native execution, mapping/lifetime or installation proof.
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
SOURCE = "src/patcher/battle_profile_line_replay_v2.py"
PARENT = "src/patcher/battle_profile_primitive_request_v2.py"
PARENT_SHA = "72e39bdcb4a047d227bf38cf40d5cb6c69d771ccb5e170e2040cfbb55ecb3be5"
BASE_SHA = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
LINE_TARGET, MEMORY_VTABLE = 0x403f70,0x50ee24
LINE_WINDOWS = ((0x430ad5,"ff5714e954fdffff",0x430831),
                (0x430b07,"ff571489ec5d5f5e595bc3",None))
REMOVED_OVERLAPS = (0x430ad8,0x430b0a)
NATIVE_SPANS = (
    ("memory_line",0x403f70,0x40403d,"74308b78ce403326e9df50c52c7c522bbc645e6b5001961e3a957e5d9b0ebf5e"),
    ("fill_adapter",0x473fd8,0x473ff0,"72d0f071ad4527d35d1d3a72d27ba6c438a17144868c4d381f451485bbcbb3ec"),
    ("fill_closure",0x487cf0,0x487d93,"0d817cb2566a6e1c69d28ad408e2c64dbe30f5718e5c9e2a0126d2bc4d8ebc03"),
    ("memory_vtable",0x50ee24,0x50ee60,"297030147e736198144db61d9839b9be6372b4d8a679a20db4586c188367fa3e"),
)
FALSE_CLAIMS = ("installed","battle_installed","installation_ready","native_line_execution_verified",
    "native_line_abi_verified","native_callback_abi_verified","native_stack_capacity_verified",
    "whole_chain_capacity_verified","provider_validity_verified","provider_lifetime_verified",
    "native_sprite_replay_emitted","sprite_rle_verified","intra_decoder_cancellation",
    "atomic_installation_verified","runtime_verified","input_verified","healthy_map_return_verified",
    "release_accepted","promotion_ready")


def _require(value,message):
    if not value:raise ValueError(message)


def _sha(raw):return hashlib.sha256(raw).hexdigest()


def _read(path):
    _require(path.is_absolute() and path.is_relative_to(ROOT) and path.resolve(strict=True) == path,
             "canonical fresh Line source required")
    for part in (path,*path.parents):
        stat = part.lstat()
        _require(not part.is_symlink() and not getattr(stat,"st_file_attributes",0)&0x400,
                 "fresh Line source reparse forbidden")
    before = path.stat();_require(0 < before.st_size <= 2*1024*1024,"bounded fresh Line source required")
    raw = path.read_bytes();after = path.stat()
    stamp = lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,getattr(s,"st_file_attributes",0))
    _require(stamp(before) == stamp(after) and len(raw) == after.st_size,"fresh Line source changed")
    return raw,stamp(after)


@contextmanager
def _parent_module(raw):
    _require(type(raw) is bytes and _sha(raw) == PARENT_SHA,"whole fresh shared request source required")
    name = "_fresh_line_request_"+uuid.uuid4().hex
    module = types.ModuleType(name);module.__file__ = str(ROOT/PARENT)
    module.__loaded_source_sha256__ = PARENT_SHA;module.__canonical_primitive_request_v2_issuer__ = True
    _require(sys.modules.setdefault(name,module) is module,"fresh Line namespace occupied")
    try:
        exec(compile(raw,module.__file__,"exec"),module.__dict__);yield module
    finally:
        changed = sys.modules.get(name) is not module
        if not changed:del sys.modules[name]
        _require(not changed,"fresh Line namespace changed")


def _snapshot():
    parent = _read(ROOT/PARENT)
    with _parent_module(parent[0]) as module:snapshot = module._snapshot()
    own = _read(ROOT/SOURCE)
    _require(snapshot[PARENT] == parent and globals().get("__loaded_source_sha256__") == _sha(own[0]),
             "private complete fresh Line graph required")
    return snapshot|{SOURCE:own}


def _function(raw,name):
    nodes = [n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name == name]
    _require(len(nodes) == 1,"one whole pinned fresh Line composition function required")
    return ast.get_source_segment(raw.decode(),nodes[0])


def _edit(source,old,new):
    _require(source.count(old) == 1,"one exact fresh Line source boundary required: "+old[:60])
    return source.replace(old,new)


@dataclass(frozen=True)
class LineReplayV2Emission:
    base_va:int
    state_va:int
    code:bytes
    entries:tuple
    relocations:tuple
    width:int
    height:int
    private_entries:tuple
    planned_hooks:tuple
    field_call_patches:tuple
    adapter_receipts:tuple
    guard_source_sha256:str
    source_transforms:tuple
    request_sites:tuple=()
    request_returns:tuple=()
    line_post_returns:tuple=()
    line_native_returns:tuple=()


@dataclass(frozen=True)
class LineReplayV2Bundle:
    emission:LineReplayV2Emission
    joined_field_emission:object
    primitive_request_bundle:object
    metadata_json:str
    hook_sites:tuple=()
    removed_highlow_rvas:tuple=()
    def metadata(self):return json.loads(self.metadata_json)


def _guard_source(request,continuation,atomic,content,template_source,template,rows,*,line_post_returns):
    source,transforms,namespace,control = request._guard_source(continuation,atomic,content,template_source,template,rows)
    _require(len(line_post_returns) == 2 and len(set(line_post_returns)) == 2,"two distinct Line post-helper returns required")
    old = "        get(0,HELPER_BYTES+36);cmpva(0,thunk_returns[number],'fixed continuation outer thunk CALL return');ne(reject)\n"
    new = """        get(0,HELPER_BYTES+36)
        if number in (54,55):
            cmpva(0,thunk_returns[number],'fixed Line pre-helper CALL return');eq('line.phase.pre.'+str(number))
            cmpva(0,line_post_returns[number-54],'fixed Line post-helper CALL return');ne(reject)
            get(0,HELPER_BYTES+40);cmp(0,1);ne(reject);jump('line.phase.done.'+str(number))
            a.label('line.phase.pre.'+str(number));get(0,HELPER_BYTES+40);a.emit('85c0');ne(reject)
            a.label('line.phase.done.'+str(number))
            get(0,INPUT);cmpva(0,MEMORY_VTABLE,'literal memory Line vtable');ne(reject)
        else:cmpva(0,thunk_returns[number],'fixed continuation outer thunk CALL return');ne(reject)
"""
    source = _edit(source,old,new)
    namespace.update(line_post_returns=line_post_returns,MEMORY_VTABLE=MEMORY_VTABLE)
    return source,transforms+((old,new,1),),namespace,control


def _guard_factory(request,posts):
    raw = _read(ROOT/PARENT)[0];_require(_sha(raw) == PARENT_SHA,"whole fresh request guard source required")
    scope = dict(request.__dict__)
    def source(*args,**kwargs):
        return _guard_source(request,*args,line_post_returns=tuple(posts),**kwargs)
    scope["_guard_source"] = source
    exec(compile(_function(raw,"_raw_guard"),str(ROOT/SOURCE)+"#whole_guard_factory","exec"),scope)
    return scope["_raw_guard"]


def _append_requests(a,base,entries,calls,*,sites,posts,native_returns,relocation):
    returns = []
    for index,(pc,kind,owner,delta,raw) in enumerate(sites):
        a.label("request_"+str(index));entries.append(("request_"+str(index),base+len(a.code)))
        a.emit("9c60fc83ec50c7042400000000c744240400000000c7442408");a.u32(43+index)
        a.emit("c744240c");a.u32(0 if owner == "tile" else 1)
        a.branch("e8","helper");calls.append(base+len(a.code));returns.append(calls[-1])
        if kind != "line":
            a.emit("8954246483c450619dc3");continue
        label = "line."+str(index)
        a.emit("83fa01");a.branch("0f84",label+".prepared")
        a.emit("83fa03");a.branch("0f85","unsafe_control");a.branch("e9",label+".complete")
        a.label(label+".prepared")
        a.emit("8b4424248b5424308b5c24348b4c2438ff742440ff742440fce8")
        at = len(a.code);a.relocations.append(relocation(at,"rel32",LINE_TARGET,"closed fresh memory Line replay"))
        a.u32(LINE_TARGET-base-at-4);native_returns.append(base+len(a.code))
        # Preserve the actual native outputs in the owning PUSHAD/PUSHFD
        # receipt. EBP/EDI/ESI are also saved explicitly, not assumed inputs.
        a.emit("8944246c9c5889442470897c245089742454896c2458895c246089542464894c24688b44246c")
        a.emit("c7042401000000");a.branch("e8","helper");posts.append(base+len(a.code))
        a.emit("83f801");a.branch("0f85","unsafe_control")
        a.label(label+".complete");a.emit("83c450619d8d64240c")
        if index == 11:
            a.emit("e9");at = len(a.code)
            a.relocations.append(relocation(at,"rel32",0x430831,"exact fresh Line Tile continuation"))
            a.u32(0x430831-base-at-4)
        else:a.emit("89ec5d5f5e595bc3")
    return tuple(returns)


def _composition_source(source):
    old = "    a.emit('8b85');a.u32(200);a.emit('83f82b');branch('normal.finish','0f82');branch('request.payload')\n"
    phase = "    a.emit('8b85');a.u32(HELPER_BYTES+40);a.emit('83f801');branch('normal.finish','0f84')\n"
    _require(phase not in source,"fresh Line helper phase already composed")
    new = phase+old
    return _edit(source,old,new)


def _raw_emit(*values,request,**kwargs):
    raw = _read(ROOT/PARENT)[0];_require(_sha(raw) == PARENT_SHA,"whole fresh request composition required")
    posts,native_returns = [],[]
    scope = dict(request.__dict__)
    def compiler(source,filename,mode):
        _require(filename == str(ROOT/request.SOURCE)+"#whole_shared_composition" and mode == "exec",
                 "one complete fresh request composition compile required")
        return compile(_composition_source(source),str(ROOT/SOURCE)+"#whole_shared_line_composition",mode)
    def append(a,base,entries,calls):
        return _append_requests(a,base,entries,calls,sites=request.REQUEST_SITES,posts=posts,
            native_returns=native_returns,relocation=kwargs["assembler_module"].Relocation)
    scope.update(compile=compiler,_raw_guard=_guard_factory(request,posts),_append_requests=append,
        PrimitiveRequestV2Emission=LineReplayV2Emission)
    exec(compile(_function(raw,"_raw_emit"),str(ROOT/SOURCE)+"#whole_request_factory","exec"),scope)
    out = scope["_raw_emit"](*values,**kwargs)
    _require(len(posts) == len(native_returns) == 2,"two exact fresh native/post Line returns required")
    overlaps = tuple(row for row in out.planned_hooks if row[0] in REMOVED_OVERLAPS)
    _require(tuple(row[0] for row in overlaps) == REMOVED_OVERLAPS and all(row[4] == () for row in overlaps),
             "complete two-window Line overlap removal required")
    hooks = tuple(row for row in out.planned_hooks if row[0] not in REMOVED_OVERLAPS)
    hooks += tuple((pc,bytes.fromhex(old),dict(out.entries)["request_"+str(11+i)],"fresh_line_replay",())
                   for i,(pc,old,_) in enumerate(LINE_WINDOWS))
    spans = sorted((pc,pc+len(old)) for pc,old,*_ in hooks)
    _require(len(hooks) == 43 and len({pc for pc,*_ in hooks}) == 43 and
             all(end <= start for (_,end),(start,_) in zip(spans,spans[1:])),"whole disjoint fresh Line hook windows required")
    return replace(out,planned_hooks=hooks,request_sites=request.REQUEST_SITES,
        line_post_returns=tuple(posts),line_native_returns=tuple(native_returns))


def _authenticate_native(original,relayout,clip,pe):
    for image in (original,relayout):
        parsed = pe.inspect_pe(image);_,relocations = pe._old_relocations(image,parsed)
        for name,low,high,digest in NATIVE_SPANS:
            at = clip.file_offset(image,low,high-low)
            _require(_sha(image[at:at+high-low]) == digest,"closed fresh Line native span differs: "+name)
            expected = tuple(range(0x10ee24,0x10ee60,4)) if name == "memory_vtable" else ()
            _require(tuple(sorted(rva for rva in relocations if low <= parsed.image_base+rva < high)) == expected,
                     "complete closed fresh Line HIGHLOW inventory differs")
        for pc,old,_ in LINE_WINDOWS:
            expected = bytes.fromhex(old);at = clip.file_offset(image,pc,len(expected))
            _require(image[at:at+len(expected)] == expected and
                     not any(pc <= parsed.image_base+rva < pc+len(expected) for rva in relocations),
                     "whole fresh Line native window differs")
        at = clip.file_offset(image,MEMORY_VTABLE+0x14,4)
        _require(struct.unpack_from("<I",image,at)[0] == LINE_TARGET,"literal memory vtable Line slot differs")


def _issue(original,profile,resolution):
    _require(type(original) is bytes and _sha(original) == BASE_SHA,"exact fresh Line original required")
    snapshot = _snapshot()
    with _parent_module(snapshot[PARENT][0]) as request:
        parent = request._issue(original,profile,resolution)
        continuation_bundle = parent.continuation_bundle
        atomic_bundle = continuation_bundle.adjacent_unit_bundle
        replay = atomic_bundle.count_body_bundle.count_entry_bundle.content_replay_bundle
        loss_bundle = replay.tile_replay_bundle.field_loss_bundle
        content = loss_bundle.content_bundle;lease = content.lease_bundle;field = lease.field_bundle
        context = field.routing_bundle.lifecycle_bundle.allocation_context
        with request._parent_module(snapshot[request.PARENT][0]) as continuation:
            with continuation._parent_module(snapshot[continuation.PARENT][0]) as atomic:
                with continuation._graph(atomic,snapshot) as (content_module,modules):
                    _authenticate_native(original,context.relayout_parent,modules[continuation.CLIP],modules[continuation.PE])
                    out = _raw_emit(context.layout,field.emission,lease.emission,content.emission,loss_bundle.emission,
                        loss_bundle.joined_field_emission,atomic_bundle.model_emission,atomic_bundle.emission,
                        atomic_bundle.count_entry_emission,request=request,continuation=continuation,atomic_module=atomic,
                        content_module=content_module,template_module=modules[continuation.TEMPLATE],
                        template_source=snapshot[continuation.TEMPLATE][0],ledger_source=snapshot[continuation.LEDGER][0],
                        loss_module=continuation._loss_module(snapshot),assembler_module=modules[continuation.CLIP])
                    joined = continuation._join_field(loss_bundle.joined_field_emission,out)
        metadata = dict(schema="clash95_battle_profile_line_replay_v2",profile=profile,resolution=resolution,
            original_sha256=BASE_SHA,source_hashes=parent.metadata()["source_hashes"]|
                {name:_sha(raw) for name,(raw,_) in snapshot.items()},
            code_va=out.base_va,code_bytes=len(out.code),code_sha256=_sha(out.code),guard_source_sha256=out.guard_source_sha256,
            joined_field_sha256=_sha(joined.code),normal_post_windows_retained=41,complete_line_ports=2,
            removed_overlapping_post_windows=list(REMOVED_OVERLAPS),sprite_queries_retained=11,
            line_native_returns=out.line_native_returns,line_post_helper_returns=out.line_post_returns,
            line_target_va=LINE_TARGET,literal_memory_vtable_va=MEMORY_VTABLE,helper_frame_bytes=request.HELPER_BYTES,
            owning_thunk_bytes=80,request_bytes=64,provider_schema=context.layout.provider_schema,provider_records_emitted=0,
            prefix_rx_remaining_bytes=context.layout.rx.va+context.layout.rx.size-out.base_va-len(out.code),
            phase_policy="pre CALL return +task0, post CALL return +task1; same exact native CALL word and owning frame",
            failure_policy="UD2 for malformed/fault/unknown/lost control; no unchecked native cleanup",
            empty_line_policy="admitted own-frame cleanup without native drawing",
            native_line_replay_emitted=True,installed_hooks=[],candidate_written=False,preparation_only=True,
            limitations=["A closed native byte contract and emitted CALL do not prove execution, mapped buffers, native stack or callback ABI.",
                "Current pre/post receipts are not historical lifetime or inter-thread immutability.",
                "Sprite/RLE providers, atomic installation, complete battle, presentation/input/quit and healthy map return remain unfinished.",
                "No RX expansion or RW/provider reservation borrowing is permitted; unchanged reservation overflow rejects emission."],
            **{name:False for name in FALSE_CLAIMS})
    _require(all(_read(ROOT/name) == row for name,row in snapshot.items()),"fresh Line source graph changed")
    return LineReplayV2Bundle(out,joined,parent,json.dumps(metadata,sort_keys=True,separators=(",",":")))


def _production_factory():
    from pathlib import Path as SourcePath
    from types import ModuleType
    from sys import modules
    from uuid import uuid4
    path = SourcePath(__file__).absolute()
    if path != path.parents[2]/SOURCE:raise ValueError("canonical fresh Line producer required")
    raw,stamp = _read(path)
    module = ModuleType("_fresh_line_issuer_"+uuid4().hex);module.__file__ = str(path)
    module.__loaded_source_sha256__ = _sha(raw);module.__canonical_line_replay_v2_issuer__ = True
    if modules.setdefault(module.__name__,module) is not module:raise ValueError("fresh Line issuer occupied")
    try:
        exec(compile(raw,str(path),"exec"),module.__dict__);issue,read = module._issue,module._read
    finally:
        if modules.get(module.__name__) is not module:raise ValueError("fresh Line issuer changed")
        del modules[module.__name__]
    if read(path) != (raw,stamp):raise ValueError("fresh Line source changed during capture")
    def dispatch(original,profile,resolution):
        if read(path) != (raw,stamp):raise ValueError("captured fresh Line source differs")
        try:return issue(original,profile,resolution)
        finally:
            if read(path) != (raw,stamp):raise ValueError("captured fresh Line source changed")
    return dispatch


if not globals().get("__canonical_line_replay_v2_issuer__",False):
    emit_line_replay_v2 = _production_factory()
