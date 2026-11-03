"""Uninstalled atomic Unit-motion/Count successor with caller-specific authority.

Frozen predecessors reject the final signed-motion Adjacent caller. This fresh
selected-seven model retains ordinary ancestry and the two Count DY/local
corrections. Current-global equality is restrictive, never historical authority.
Eight planned overrides remain uninstalled; source bytes are not native proof.
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
SOURCE = "src/patcher/battle_profile_adjacent_unit_v2.py"
PARENT = "src/patcher/battle_profile_count_body_v2.py"
PARENT_SHA256 = "b42d1724edb3eb6ba1a393884a8ceff0f590d61368fe438c4b003ad2997b1d8d"
ENTRY = "src/patcher/battle_profile_count_entry.py"
LEDGER = "src/patcher/battle_profile_continuation.py"
LEDGER_SHA256 = "075bd62a8311f8cc761136bca21063813dfc874ce8d8a5bcf075ebdb664d811f"
NATIVE_RETURN = 820
NATIVE_CALL, NATIVE_RET, NATIVE_COUNT, COUNT_END = 0x42f956, 0x42f95b, 0x426ef0, 0x426f75
PARENT_SITE, PARENT_SITE_NUMBER = 0x42f84a, 0
BODY_SP = dict(unit=-64, adjacent=-16, vertical=-8, count=-28)
BODY_SITES = (0x42f84a,0x42f9af,0x42f9c3,0x42f9d7,0x42f9ec,0x426f44,0x426f54)
SOURCE_INDICES = (12,13,14,15,16,26,27)
FINAL_RETURN, MOTION_SOURCE, ACTIVE_SOURCE = 0x42ffa4,0x523f70,0x512360
CALLER_WINDOW = (0x42ff7a,0x42ffa4,"455371cdb73867ea54a97c41442702a4bd2bd88135af9c2a2b2585c2a684c9fa")
CALLER_HIGHLOW = ((0x42ff7c,0x523f70),(0x42ff8a,0x512360))
PHASE_WINDOWS = (
    (0x42f820,0x42f84a,"82906cff5c6036c02677c48091c94687a509d949dbe4d6d6641cfd7eef73e9a0"),
    (0x42f93e,0x42f956,"0ef8e34292b19d935303cb0338bdb644d4fab7256e238b3644e7e4fd508fa8b4"),
    (0x42f95b,0x42f9af,"0a2b615b01104a697ba5b1d5f42db5619f01c7c380e98f289f5a94afe92bf5ec"),
)
PHASE_HIGHLOW = ((0x42f841,0x532048),(0x42f942,0x532048),(0x42f9a1,0x532048),(0x42f9ab,0x513334))
UNIT_SPAN = (0x42f820,0x42fc30,"1927416dbe66ccbee6bf8c22a7f874f5c1ee6f08feaff551985b0ae4b93d6c0e")
ENTRY_SHA256 = "50bf7d588bd41102ba7170f6a53ff9f65a22496b5d9ea13586496196a7cc2ac4"
REPLAY = "src/patcher/battle_profile_content_replay.py"
TILE = "src/patcher/battle_profile_tile_replay.py"
LOSS = "src/patcher/battle_profile_field_loss.py"
CONTENT = "src/patcher/battle_profile_content_v2.py"
TEMPLATE = "src/patcher/battle_profile_content.py"
TEMPLATE_SHA256 = "52f9ac7f8d52cb40638e91868910d6487cea083be0cc32e622d8fe4a3f8cf3d7"
CLIP = "src/patcher/partial_tile_clip.py"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
HELPER_BYTES = 784
COUNT_SITES = (0x426f44, 0x426f54)
COUNT_WINDOWS = (bytes.fromhex("0fbf8c59fe05000083f9ff"), bytes.fromhex("8a9411560300003a5702"))
COUNT_SHA256 = "a97ca326a029c59233d0e8881e5eed3004c8e168d24fd7248a5a78c48c65cf90"
TABLE_SHA256 = "f5c6bbbf5f45749649807f7d447f200806adb5055b4af1fcb2738ba8786dd59c"
COUNT_HIGHLOW = ((0x426f0d, 0x514500), (0x426f19, 0x532048), (0x426f29, 0x514504))
NEIGHBORS = ((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1))
FALSE_CLAIMS = (
    "source_accepted", "source_acceptance", "installed", "battle_installed", "expanded_battle_installed",
    "source_candidate_installed", "installation_ready", "standalone_native_callsite_replacement_safe",
    "native_executed", "game_executed", "runtime_executed", "runtime_verified", "manual_input_proof",
    "manual_input_verified", "promotion_ready", "release_accepted", "native_callback_abi_verified",
    "native_stack_capacity_verified", "whole_chain_capacity_verified", "native_receiver_validity_verified",
    "native_argument_validity_verified", "provider_validity_verified", "provider_capacity_verified",
    "provider_lifetime_verified", "native_provider_rle_verified", "intra_decoder_cancellation",
    "provider_early_cancellation", "native_continuation_cancellation", "healthy_return_verified",
    "healthy_native_unwind_verified", "process_quit_closure_verified", "atomic_installation_verified",
    "physical_only_clip_admission_verified", "arena_intersection_verified", "transient_write_prevention_verified",
    "cross_thread_immutability_verified", "non_draw_count_admission", "native_sentinel_record_verified",
    "native_count_instruction_execution_verified", "native_count_parity_verified",
    "count_body_hooks_installed", "unit_body_hooks_installed", "count_entry_record_guard_installed",
    "final_adjacent_native_parity_verified", "native_motion_historical_authority_verified",
    "downstream_frozen_continuation_compatible", "downstream_frozen_primitive_compatible",
)

def _require(value, message):
    if not value: raise ValueError(message)

def _sha(raw):
    return hashlib.sha256(raw).hexdigest()

def _read(path):
    _require(path.is_absolute() and path.is_relative_to(ROOT) and path.resolve(strict=True) == path,
             "canonical Count body V2 source required")
    for item in (path, *path.parents):
        row = item.lstat()
        _require(not item.is_symlink() and not getattr(row, "st_file_attributes", 0) & 0x400,
                 "Count body V2 reparse forbidden")
    before = path.stat()
    _require(0 < before.st_size <= 2*1024*1024, "bounded Count body V2 source required")
    with path.open("rb") as stream: raw = stream.read(2*1024*1024+1)
    after = path.stat()
    stamp = lambda r: (r.st_dev,r.st_ino,r.st_size,r.st_mtime_ns,getattr(r,"st_file_attributes",0))
    _require(stamp(before) == stamp(after) and len(raw) == after.st_size, "Count body V2 source changed while read")
    return raw, stamp(after)

@contextmanager
def _body_module(raw):
    _require(type(raw) is bytes and _sha(raw)==PARENT_SHA256,"frozen complete Count body V2 source required")
    name="_adjacent_unit_v2_parent_"+uuid.uuid4().hex
    module=types.ModuleType(name);module.__file__=str(ROOT/PARENT)
    module.__loaded_source_sha256__=PARENT_SHA256;module.__canonical_count_body_v2_issuer__=True
    _require(sys.modules.setdefault(name,module) is module,"private Adjacent Unit parent namespace occupied")
    try:
        exec(compile(raw,module.__file__,"exec"),module.__dict__);yield module
    finally:
        replaced=sys.modules.get(name) is not module
        if sys.modules.get(name) is module:del sys.modules[name]
        _require(not replaced,"private Adjacent Unit parent namespace changed")

def _snapshot():
    parent=_read(ROOT/PARENT)
    with _body_module(parent[0]) as producer:result=producer._snapshot()
    own=_read(ROOT/SOURCE)
    _require(result[PARENT]==parent and globals().get("__loaded_source_sha256__")==_sha(own[0]),
        "private complete unchanged Adjacent Unit source graph required")
    return result|{SOURCE:own}

def _unchanged(snapshot):
    _require(all(_read(ROOT/name) == receipt for name,receipt in snapshot.items()),"Count body V2 source graph changed")

@dataclass(frozen=True)
class Operand:
    instruction_offset:int
    instruction_bytes:int
    offset:int
    kind:str
    role:str
    value:int

@dataclass(frozen=True)
class AdjacentUnitModelEmission:
    base_va:int
    state_va:int
    code:bytes
    entries:tuple
    relocations:tuple
    width:int
    height:int
    private_entries:tuple
    body_receipts:tuple=()
    source_blocks:tuple=()
    transform_receipts:tuple=()

@dataclass(frozen=True)
class AdjacentUnitAdaptersEmission:
    base_va:int
    state_va:int
    code:bytes
    entries:tuple
    relocations:tuple
    width:int
    height:int
    private_entries:tuple
    body_receipts:tuple
    source_blocks:tuple
    planned_hooks:tuple

@dataclass(frozen=True)
class AdjacentUnitEntryEmission:
    base_va:int
    state_va:int
    code:bytes
    entries:tuple
    relocations:tuple
    width:int
    height:int
    private_entries:tuple
    prefix_receipt:tuple
    private_clone_receipt:tuple
    guard_receipts:tuple
    source_blocks:tuple
    planned_hooks:tuple

@dataclass(frozen=True)
class AdjacentUnitV2Bundle:
    emission:AdjacentUnitAdaptersEmission
    model_emission:AdjacentUnitModelEmission
    count_entry_emission:AdjacentUnitEntryEmission
    count_body_bundle:object
    operand_inventory:tuple
    model_operand_inventory:tuple
    count_entry_operand_inventory:tuple
    metadata_json:str
    hook_sites:tuple=()
    removed_highlow_rvas:tuple=()
    def metadata(self):return json.loads(self.metadata_json)


def _identity(out):
    return (out.base_va,out.state_va,out.code,out.entries,out.private_entries,
        tuple((r.offset,r.kind,r.target,r.purpose) for r in out.relocations),out.width,out.height,
        *(tuple(getattr(out,name,())) for name in ("body_receipts","source_blocks","planned_hooks",
          "field_call_patches","field_return_pcs","lease_return_pcs","field_tile_receipts",
          "lease_field_receipts","prefix_receipt","private_clone_receipt","guard_receipts","transform_receipts")))

def _literal(raw,name):
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.Assign) and
           any(isinstance(t,ast.Name) and t.id==name for t in n.targets)]
    _require(len(nodes)==1,"one whole pinned Count body field required")
    return ast.literal_eval(nodes[0].value)

def _native_contract(template_source):
    _require(type(template_source) is bytes and _sha(template_source)==TEMPLATE_SHA256,"whole pinned content template required")
    sites=_literal(template_source,"SITES")
    _require(len(sites)==28 and tuple(row[0] for row in sites[-2:])==COUNT_SITES and
        all(row[2]=='count' for row in sites[-2:]) and _literal(template_source,"NEIGHBORS")==NEIGHBORS and
        _literal(template_source,"NATIVE_SPANS")['count']==(0x426ef0,0x426f75,COUNT_SHA256),
        "complete Count native/model ledger differs")
    _require(tuple(bytes.fromhex(row[1]) for row in sites[-2:])==
        (bytes.fromhex('0fbf8c59fe050000'),bytes.fromhex('8a941156030000')),"exact native Count operands required")
    return sites

def _whole_model_source(content_module,template_source,template_module):
    sites=_native_contract(template_source)
    _,ledger,namespace=content_module._versioned_template(template_source,template_module)
    text=template_source.decode('utf-8')
    nodes=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='_emit_code']
    _require(len(nodes)==1,"one whole pinned content function required")
    source=ast.get_source_segment(text,nodes[0])
    for old,new,count in ledger:
        _require(type(count) is int and count>0 and source.count(old)==count,"complete ContentV2 edit occurrence differs")
        source=source.replace(old,new)
    edits=[]
    def edit(old,new):
        nonlocal source
        _require(source.count(old)==1,"exact Count body V2 edit occurrence differs: "+old[:70])
        source=source.replace(old,new);edits.append((old,new,1))
    edit('base=(parent.base_va+len(parent.code)+15)&~15','base=model_base')
    edit("    a.emit('89f9');add(1,56);get(0,INPUT+8);a.emit('39c8');ne(reject)",
         "    own('count_expected_dy');cmp(0,1);ne(reject)\n"
         "    get(0,INPUT+8);a.emit('39f8');ne(reject)\n    get(7,NATIVE_S)")
    edit("    get(7,UNIT_S);add(7,-12);jump('ebp.compare')\n",
         "    own('count_expected_dy');cmp(0,1);ne(reject);jump('ebp.compare')\n")
    helper="""    a.label('count_expected_dy')
    get(0,INPUT+28);a.emit('a907000000');ne('count.dy.reject')
    cmp(0,64);a.branch('0f83','count.dy.reject')
    for number,(_,dy) in enumerate(NEIGHBORS):
        cmp(0,number*8);ne('count.dy.next.'+str(number))
        imm(7,dy);imm(0,1);a.emit('c3');a.label('count.dy.next.'+str(number))
    a.label('count.dy.reject');imm(0,0);a.emit('c3')
"""
    edit("    code=bytes(a.finish())",helper+"    code=bytes(a.finish())")
    edit("('capture_inputs','capture_stack','admit_body','fixed_receipt','unsafe_control','finish_rejected','finish_valid')",
         "('capture_inputs','capture_stack','admit_body','fixed_receipt','unsafe_control','finish_rejected','finish_valid','count_expected_dy')")
    # Inline emission, not another native CALL or ancestry row. Unique labels
    # leave every inherited extent-number receipt unchanged.
    local_extent="""    def count_local_extent(suffix):
        get(7,NATIVE_S);add(7,-28)
        a.emit('f7c703000000');ne(reject)
        get(2,ROOT_ESP);a.emit('89d1');add(1,-ROOT_STACK_BOUND)
        a.emit('39cf');a.branch('0f82',reject)
        a.emit('89f8');add(0,4);a.branch('0f82',reject)
        a.emit('39d0');a.branch('0f87',reject)
        for number,(low,high) in enumerate(protected_intervals):
            label='count.local.'+suffix+'.protected.'+str(number)
            cmpva(7,high,'protected Count local allocation end');a.branch('0f83',label)
            cmpva(0,low,'protected Count local allocation start');a.branch('0f86',label)
            jump(reject);a.label(label)
"""
    edit("    def record(reg,count,reject):",local_extent+"    def record(reg,count,reject):")
    edit("    get(7,NATIVE_S);add(7,68);jump('ancestry.unit')",
         "    count_local_extent('before');load(0,7,0);put(0,X)\n"
         "    get(7,NATIVE_S);add(7,68);jump('ancestry.unit')")
    edit("    put(0,THREAD_RESULT);control_match();get(0,THREAD_RESULT)",
         "    put(0,THREAD_RESULT);control_match()\n"
         "    count_local_extent('after');load(0,7,0);match(0,X);ne(reject)\n"
         "    get(0,THREAD_RESULT)")
    motion_helpers="""    def motion_extent(family,suffix):
        get(7,NATIVE_S if family == 'count' else UNIT_S);add(7,-16 if family == 'count' else -28)
        a.emit('f7c703000000');ne(reject)
        get(2,ROOT_ESP);a.emit('89d1');add(1,-ROOT_STACK_BOUND)
        a.emit('39cf');a.branch('0f82',reject)
        a.emit('89f8');add(0,4);a.branch('0f82',reject)
        a.emit('39d0');a.branch('0f87',reject)
        for number,(low,high) in enumerate(protected_intervals):
            label='unit.motion.'+suffix+'.'+family+'.protected.'+str(number)
            cmpva(7,high,'protected Unit motion witness allocation end');a.branch('0f83',label)
            cmpva(0,low,'protected Unit motion witness allocation start');a.branch('0f86',label)
            jump(reject);a.label(label)
    def motion_witness(suffix):
        label='unit.motion.'+suffix
        get(0,KIND);cmp(0,4);eq(label+'.count')
        cmp(0,1);ne(reject)
        get(0,SITE);cmp(0,0);eq(label+'.early')
        motion_extent('unit',suffix);load(0,7,0)
        cmp(0,22*31);a.branch('0f83',reject)
        a.emit('31d2b91f000000f7f1');a.emit('85d2');ne(reject);jump(label+'.identity')
        a.label(label+'.early');get(0,INPUT+4);jump(label+'.identity')
        a.label(label+'.count');motion_extent('count',suffix);load(0,7,0)
        a.label(label+'.identity');cmp(0,22);a.branch('0f83',reject)
"""
    edit("    def record(reg,count,reject):",motion_helpers+"    def record(reg,count,reject):")
    edit("    get(6,TILE_S);load(1,6,-24);jump('unit.saved.compare')",
         "    cmpva(0,FINAL_RETURN,'final signed-motion Unit caller');ne('unit.saved.ordinary')\n"
         "    read(0,MOTION_SOURCE,'fixed final Unit signed motion');a.emit('85c0');a.branch('0f89',reject);put(0,Y)\n"
         "    motion_witness('before');put(0,INDEX)\n"
         "    read(1,ACTIVE_SOURCE,'fixed final Unit active identity');a.emit('39c8');ne(reject)\n"
         "    get(1,Y);get(7,UNIT_S);jump('unit.saved.compare')\n"
         "    a.label('unit.saved.ordinary');get(6,TILE_S);load(1,6,-24);jump('unit.saved.compare')")
    edit("    put(0,THREAD_RESULT);control_match()\n"
         "    count_local_extent('after');load(0,7,0);match(0,X);ne(reject)\n"
         "    get(0,THREAD_RESULT)",
         "    put(0,THREAD_RESULT);control_match()\n"
         "    get(0,Y);a.emit('85c0');a.branch('0f89','unit.motion.receipts.done')\n"
         "    read(0,MOTION_SOURCE,'fixed final Unit signed motion recheck');match(0,Y);ne(reject)\n"
         "    read(0,ACTIVE_SOURCE,'fixed final Unit active identity recheck');match(0,INDEX);ne(reject)\n"
         "    motion_witness('after');match(0,INDEX);ne(reject)\n"
         "    a.label('unit.motion.receipts.done')\n"
         "    get(0,KIND);cmp(0,4);ne('count.local.after.done')\n"
         "    count_local_extent('after');load(0,7,0);match(0,X);ne(reject)\n"
         "    a.label('count.local.after.done');get(0,THREAD_RESULT)")
    namespace.update(SITES=tuple(sites[i] for i in SOURCE_INDICES),NEIGHBORS=NEIGHBORS,
        FINAL_RETURN=FINAL_RETURN,MOTION_SOURCE=MOTION_SOURCE,ACTIVE_SOURCE=ACTIVE_SOURCE,
        CodeEmission=AdjacentUnitModelEmission)
    return source,tuple(ledger),tuple(edits),namespace

def _layout_values(layout,field,lease):
    _require(layout.profile in ('classic','framed','completehd','modalwidgets') and layout.rx.size==0x40000 and
        layout.rw.size==0x10000 and field.state_va==lease.state_va==layout.rw.va and
        lease.base_va==(field.base_va+len(field.code)+15)&~15,"fresh Count body layout/parent required")
    inherited=[row for row in layout.protected_spans if row.role=='parent:.hdstate']
    _require(len(inherited)==int(layout.profile in ('completehd','modalwidgets')),"separate Count modal span required")
    modal=None if not inherited else inherited[0].va
    if inherited:
        _require(inherited[0].size==4096 and modal+4096<=layout.rx.va,"complete inherited modal page required")
    return modal

def _raw_model(layout,field,lease,content,previous_adapters,*,content_module,template_module,assembler_module,template_source):
    modal=_layout_values(layout,field,lease)
    base=(previous_adapters.base_va+len(previous_adapters.code)+15)&~15
    source,ledger,edits,namespace=_whole_model_source(content_module,template_source,template_module)
    plan={'profile':layout.profile}; namespace['model_base']=base;namespace['modal_va']=modal
    namespace['protected_intervals']=((layout.rx.va,layout.rx.va+layout.rx.size),(layout.rw.va,layout.rw.va+layout.rw.size))+(
        () if modal is None else ((modal,modal+4096),))
    def captured(supplied,parent):
        _require(supplied is plan and parent is lease,"exact captured Count body lease required")
        return layout.rx.va,layout.rw.va,field.width,field.height,dict(field.private_entries)['check_invocation']
    namespace['_layout']=captured
    exec(compile(source,str(ROOT/SOURCE)+'#whole_count_model','exec'),namespace)
    labels=[];parent=assembler_module._Assembler
    class CompleteAssembler(parent):
        def finish(self):
            code=super().finish()
            for offset,label in self.fixups:
                self.relocations.append(assembler_module.Relocation(offset,'rel32',self.base+self.labels[label],
                    'adjacent_unit_v2_internal:'+label))
            labels.append(dict(self.labels));return code
    isolated=types.SimpleNamespace(_Assembler=CompleteAssembler,Relocation=assembler_module.Relocation,
        absolute_relocation_offsets=assembler_module.absolute_relocation_offsets)
    out=namespace['_versioned_emit_code'](plan,lease,assembler_module=isolated)
    _require(len(labels)==1 and out.base_va==base,"one complete Count model label receipt required")
    owned=labels[0];bodies=[]
    for va in BODY_SITES:
        entry=base+owned[f'site_{va:06x}'];payload=base+owned[f'site_{va:06x}.payload']
        rows=[r for r in out.relocations if r.purpose=='adjacent_unit_v2_internal:admit_body' and
            entry<=base+r.offset-1<payload]
        _require(len(rows)==1 and out.code[rows[0].offset-1]==0xe8,"actual Count model body admission CALL required")
        bodies.append((va,entry,payload,base+rows[0].offset+4,base+owned[f'site_{va:06x}.denied'],
            base+owned[f'site_{va:06x}.fault'],base+owned[f'site_{va:06x}.valid']))
    out=replace(out,body_receipts=tuple(bodies))
    _,blocks,receipts=_model_contract(out,content,field,template_source,check_receipts=False)
    out=replace(out,source_blocks=blocks,transform_receipts=receipts)
    _model_operand_inventory(out,content,field,template_source=template_source)
    _require(out.base_va+len(out.code)<=layout.rx.va+layout.rx.size,"Count model exceeds fresh RX reservation")
    return out

def _decode(code):
    """Closed authored source/native scalar dialect; address roles are explicit."""
    cursor, rows = 0, []
    while cursor < len(code):
        start, fields = cursor, []
        opcode = code[cursor]; cursor += 1; memory = False
        if opcode in (0x9c, 0x9d, 0x60, 0x61, 0xfc, 0xc3, 0x55, 0x5d, 0x4b):
            pass
        elif opcode == 0xf3:
            _require(cursor < len(code) and code[cursor] == 0xaf,"closed protected-tail REP dialect required")
            cursor += 1
        elif 0xb8 <= opcode <= 0xbf or opcode in (0xa9, 0x3d):
            fields.append((cursor, 4, "immediate")); cursor += 4
        elif opcode in (0xe8, 0xe9):
            fields.append((cursor, 4, "relative")); cursor += 4
        elif opcode == 0x0f:
            _require(cursor < len(code), "truncated content replay escape")
            sub = code[cursor]; cursor += 1
            if sub == 0x0b:
                pass
            elif 0x80 <= sub <= 0x8f:
                fields.append((cursor, 4, "relative")); cursor += 4
            else:
                _require(sub in (0xb6, 0xb7, 0xbf), "content replay extended load differs")
                memory = True
        elif opcode == 0x66:
            _require(cursor < len(code) and code[cursor] in (0x8b, 0x89),
                     "content replay word prefix differs")
            cursor += 1; memory = True
        else:
            _require(opcode in (0x81, 0x83, 0x8b, 0x89, 0x88, 0x3b, 0x39, 0x3a, 0x03,
                                0x85, 0xf7, 0xff, 0x31, 0x29, 0x01, 0xc1, 0x6b, 0x8d, 0xd1),
                     "unknown content replay opcode at " + hex(start))
            memory = True
        if memory:
            _require(cursor < len(code), "truncated content replay ModRM")
            modrm = code[cursor]; cursor += 1; mode, rm = modrm >> 6, modrm & 7
            if mode != 3 and rm == 4:
                _require(cursor < len(code), "truncated content replay SIB")
                sib = code[cursor]; fields.append((cursor, 1, "sib")); cursor += 1
                if mode == 0 and sib & 7 == 5:
                    fields.append((cursor, 4, "memory_address")); cursor += 4
            if mode == 0 and rm == 5:
                fields.append((cursor, 4, "memory_address")); cursor += 4
            elif mode == 1:
                fields.append((cursor, 1, "displacement")); cursor += 1
            elif mode == 2:
                fields.append((cursor, 4, "displacement")); cursor += 4
            if opcode == 0x81 or opcode == 0xf7 and (modrm >> 3) & 7 == 0:
                fields.append((cursor, 4, "immediate")); cursor += 4
            elif opcode in (0x83, 0xc1, 0x6b):
                fields.append((cursor, 1, "immediate")); cursor += 1
        _require(start < cursor <= len(code), "truncated content replay instruction")
        rows.append((start, cursor, tuple(fields)))
    return tuple(rows)

def _model_contract(out,content,field,template_source,*,check_receipts=True):
    """Independent byte surgery on the complete canonical ContentV2 emission.

    This never invokes the new model writer. Actual source relocations anchor
    the switch rows and two EBP windows; every retained byte and typed field is
    mapped, and the new helper/windows are separately authored below.
    """
    sites=_native_contract(template_source)
    _require(out.state_va==content.state_va==field.state_va and (out.width,out.height)==(content.width,content.height)==
        (field.width,field.height),"matching complete Count model state/geometry required")
    _require(len(content.body_receipts)==28 and tuple(r[0] for r in content.body_receipts)==tuple(s[0] for s in sites),
        "complete canonical ContentV2 body receipts required")
    private=dict(content.private_entries);source_start=content.body_receipts[12][1]-content.base_va
    original=content.code;declared={r.offset:r for r in content.relocations}
    _require(len(declared)==len(content.relocations),"duplicate canonical content operand")
    native_rows=sorted((r for r in content.relocations if r.kind=='abs32' and
        r.purpose=='fixed proposed body CALL return PC'),key=lambda r:r.offset)
    _require(len(native_rows)==28 and tuple(r.target for r in native_rows)==tuple(s[0]+5 for s in sites),
        "complete actual source admission ladder required")
    ladder_starts=tuple(r.offset-26 for r in native_rows)
    reject_targets=set();matched_targets=set()
    for number,start in enumerate(ladder_starts):
        row=original[start:start+41]
        _require(len(row)==41 and row[:8]==bytes.fromhex('8b85c800000081f8') and
            struct.unpack_from('<I',row,8)[0]==number and row[12:14]==b'\x0f\x85' and
            row[18:26]==bytes.fromhex('8b870000000081f8') and
            struct.unpack_from('<I',row,26)[0]==sites[number][0]+5 and row[30:32]==b'\x0f\x85' and row[36]==0xe9,
            "whole source-owned admission switch row differs")
        for relative,purpose in ((14,'site_receipt.next.'+str(number)),(32,'admit.reject'),(37,'site_receipt.matched')):
            record=declared.get(start+relative)
            _require(record is not None and record.kind=='rel32' and
                record.purpose=='content_v2_internal:'+purpose,"complete source switch transfer differs")
        reject_targets.add(declared[start+32].target);matched_targets.add(declared[start+37].target)
    _require(len(reject_targets)==len(matched_targets)==1 and all(b-a==41 for a,b in zip(ladder_starts,ladder_starts[1:])),
        "contiguous closed source ladder required")
    reject=next(iter(reject_targets))
    count_rows=[r for r in content.relocations if (r.kind,r.target,r.purpose)==
        ('abs32',0x42f95b,'draw-only native Count caller')]
    _require(len(count_rows)==1,"one actual draw-only Count return comparison required")
    first=count_rows[0].offset+10
    first_prefix=bytes.fromhex('89f981c1380000008b859801000039c8')
    _require(original[first:first+16]==first_prefix and original[first+16:first+18]==b'\x0f\x85' and
        declared[first+18].target==reject and declared[first+18].purpose=='content_v2_internal:admit.reject',
        "first whole inherited-live-EBP Count check differs")
    needles=[];needle=bytes.fromhex('81f8030000000f84')
    cursor=private['admit_body']-content.base_va
    while True:
        at=original.find(needle,cursor,private['fixed_receipt']-content.base_va)
        if at<0:break
        start=at+12
        if original[start:start+12]==bytes.fromhex('8bbdd800000081c7f4ffffff') and original[start+12:start+13]==b'\xe9':
            needles.append(start)
        cursor=at+1
    _require(len(needles)==1,"one actual shared Count EBP fallback required")
    second=needles[0];compare=declared[second+13]
    _require(compare.kind=='rel32' and compare.purpose=='content_v2_internal:ebp.compare',
        "shared Count EBP comparison target differs")
    local_before=[]
    for row in content.relocations:
        start=row.offset-13
        if (row.kind=='rel32' and row.purpose=='content_v2_internal:ancestry.unit' and start>=0 and
            original[start:row.offset]==bytes.fromhex('8bbdd000000081c744000000e9')):
            local_before.append(start)
    _require(len(local_before)==1,"one actual Count-to-Unit ancestry boundary required")
    local_before=local_before[0]
    threads=[r for r in content.relocations if r.kind=='abs32' and r.purpose=='fixed content owning ThreadId callback']
    _require(len(threads)==1,"one actual Count source owning-thread callback required")
    needle=bytes.fromhex('8b85000300003b85180000000f85');positions=[];cursor=threads[0].offset+4
    while True:
        at=original.find(needle,cursor,private['fixed_receipt']-content.base_va)
        if at<0:break
        positions.append(at);cursor=at+1
    _require(len(positions)==1,"one actual post-control-match Thread result boundary required")
    local_after=positions[0]
    _require(original[local_after-18:local_after-4]==bytes.fromhex('8b85fcffffff3b85e40200000f85') and
        declared[local_after-4].purpose=='content_v2_internal:unsafe_control' and
        declared[local_after-4].target==private['unsafe_control'],"complete last control shadow match required")
    protected=[]
    for row in sorted(content.relocations,key=lambda r:r.offset):
        if row.kind!='abs32' or row.purpose!='protected content allocation end':continue
        low=declared.get(row.offset+12)
        _require(low is not None and low.kind=='abs32' and low.purpose=='protected content allocation start',
            "actual canonical protected interval pair required")
        pair=(low.target,row.target)
        if pair not in protected:protected.append(pair)
    _require(len(protected) in (2,3) and protected[:2]==[(content.state_va-0x40000,content.state_va),
        (content.state_va,content.state_va+0x10000)] and all(lo<hi for lo,hi in protected),
        "complete canonical RX/RW/inherited protected spans required")
    ordinary_needle=bytes.fromhex('8bb5d40000008b8ee8ffffffe9')
    hits=[];cursor=private['admit_body']-content.base_va
    while True:
        at=original.find(ordinary_needle,cursor,private['fixed_receipt']-content.base_va)
        if at<0:break
        if declared.get(at+13) is not None and declared[at+13].purpose=='content_v2_internal:unit.saved.compare':
            hits.append(at)
        cursor=at+1
    _require(len(hits)==1,"one exact ordinary Unit saved-EBP source boundary required")
    motion_before=hits[0];saved_compare=declared[motion_before+13].target
    edits=(
        (content.body_receipts[17][1]-content.base_va,content.body_receipts[26][1]-content.base_va,'drop_unselected_bodies'),
        (ladder_starts[0],ladder_starts[12],'drop_admissions_0_12'),
        (ladder_starts[17],ladder_starts[26],'drop_admissions_17_26'),
        (first,first+22,'first_live_dy'),
        (local_before,local_before,'count_local_snapshot'),
        (second,second+17,'shared_live_dy'),
        (motion_before,motion_before,'final_unit_motion'),
        (local_after,local_after,'motion_and_count_local_match'),
    )
    _require(source_start<edits[0][0]<edits[0][1]<ladder_starts[0]<ladder_starts[12]<
        ladder_starts[17]<ladder_starts[26]<first<local_before<second<motion_before<local_after<len(original),
        "ordered complete selected-seven source transformations required")
    expected=bytearray();copied=[];replaced=[];new_fields=[];new_absolutes=[];receipts=[];cursor=source_start
    def append(raw):expected.extend(bytes.fromhex(raw))
    def u32(value):expected.extend(struct.pack('<I',value&0xffffffff))
    def new_relative(target,purpose):
        new_fields.append((len(expected),target,purpose));u32(0)
    def new_absolute(target,purpose):
        new_absolutes.append((len(expected),target,purpose));u32(target)
    def local_extent(role):
        append('8bbd');u32(208);append('81c7');u32(-28)
        append('f7c7030000000f85');new_relative(reject,'adjacent_unit_v2_internal:admit.reject')
        append('8b95');u32(228);append('89d181c1');u32(-0x10000)
        append('39cf0f82');new_relative(reject,'adjacent_unit_v2_internal:admit.reject')
        append('89f881c0');u32(4);append('0f82');new_relative(reject,'adjacent_unit_v2_internal:admit.reject')
        append('39d00f87');new_relative(reject,'adjacent_unit_v2_internal:admit.reject')
        for number,(low,high) in enumerate(protected):
            append('81ff');new_absolute(high,'protected Count local allocation end')
            append('0f83');above=len(expected);u32(0)
            append('81f8');new_absolute(low,'protected Count local allocation start')
            append('0f86');below=len(expected);u32(0)
            append('e9');new_relative(reject,'adjacent_unit_v2_internal:admit.reject')
            label='adjacent_unit_v2_internal:count.local.'+role+'.protected.'+str(number)
            target=('model',out.base_va+len(expected))
            new_fields.extend(((above,target,label),(below,target,label)))
    local_labels={}
    def label(name):local_labels[name]=out.base_va+len(expected)
    def branch(opcode,name):
        append(opcode);new_fields.append((len(expected),('label',name),'adjacent_unit_v2_internal:'+name));u32(0)
    def fail(opcode='0f85'):
        append(opcode);new_relative(reject,'adjacent_unit_v2_internal:admit.reject')
    def get(reg,slot):append('8b'+f'{0x85|reg<<3:02x}');u32(slot)
    def put(reg,slot):append('89'+f'{0x85|reg<<3:02x}');u32(slot)
    def cmp(reg,value):append('81'+f'{0xf8|reg:02x}');u32(value)
    def add(reg,value):append('81'+f'{0xc0|reg:02x}');u32(value)
    def read(reg,pointer,purpose):append('8b'+f'{0x05|reg<<3:02x}');new_absolute(pointer,purpose)
    def match(reg,slot):append('3b'+f'{0x85|reg<<3:02x}');u32(slot)
    def motion_extent(family,suffix):
        get(7,208 if family=='count' else 216);add(7,-16 if family=='count' else -28)
        append('f7c703000000');fail()
        get(2,228);append('89d1');add(1,-0x10000)
        append('39cf');fail('0f82')
        append('89f8');add(0,4);fail('0f82')
        append('39d0');fail('0f87')
        for number,(low,high) in enumerate(protected):
            name='unit.motion.'+suffix+'.'+family+'.protected.'+str(number)
            append('81ff');new_absolute(high,'protected Unit motion witness allocation end');branch('0f83',name)
            append('81f8');new_absolute(low,'protected Unit motion witness allocation start');branch('0f86',name)
            fail('e9');label(name)
    def motion_witness(suffix):
        name='unit.motion.'+suffix
        get(0,204);cmp(0,4);branch('0f84',name+'.count')
        cmp(0,1);fail()
        get(0,200);cmp(0,0);branch('0f84',name+'.early')
        motion_extent('unit',suffix);append('8b8700000000')
        cmp(0,682);fail('0f83')
        append('31d2b91f000000f7f185d2');fail();branch('e9',name+'.identity')
        label(name+'.early');get(0,404);branch('e9',name+'.identity')
        label(name+'.count');motion_extent('count',suffix);append('8b8700000000')
        label(name+'.identity');cmp(0,22);fail('0f83')
    for lo,hi,role in edits:
        start=len(expected);expected.extend(original[cursor:lo]);copied.append((cursor,lo,start))
        replacement_start=len(expected)
        if role=='count_local_snapshot':
            local_extent('before');append('8b87000000008985');u32(376)
        elif role=='final_unit_motion':
            append('81f8');new_absolute(FINAL_RETURN,'final signed-motion Unit caller')
            branch('0f85','unit.saved.ordinary')
            read(0,MOTION_SOURCE,'fixed final Unit signed motion');append('85c0');fail('0f89');put(0,380)
            motion_witness('before');put(0,384)
            read(1,ACTIVE_SOURCE,'fixed final Unit active identity');append('39c8');fail()
            get(1,380);get(7,216);append('e9');new_relative(saved_compare,'adjacent_unit_v2_internal:unit.saved.compare')
            label('unit.saved.ordinary')
        elif role=='motion_and_count_local_match':
            get(0,380);append('85c0');branch('0f89','unit.motion.receipts.done')
            read(0,MOTION_SOURCE,'fixed final Unit signed motion recheck');match(0,380);fail()
            read(0,ACTIVE_SOURCE,'fixed final Unit active identity recheck');match(0,384);fail()
            motion_witness('after');match(0,384);fail()
            label('unit.motion.receipts.done')
            get(0,204);cmp(0,4);branch('0f85','count.local.after.done')
            local_extent('after');append('8b8700000000');match(0,376);fail()
            label('count.local.after.done')
        elif not role.startswith('drop_'):
            append('e8');new_relative('dy','adjacent_unit_v2_internal:count_expected_dy')
            append('81f8');u32(1);append('0f85');new_relative(reject,'adjacent_unit_v2_internal:admit.reject')
            if role=='first_live_dy':
                append('8b85');u32(408);append('39f80f85');new_relative(reject,'adjacent_unit_v2_internal:admit.reject')
                append('8bbd');u32(208)
            else:
                append('e9');new_relative(compare.target,'adjacent_unit_v2_internal:ebp.compare')
        replaced.append((lo,hi,replacement_start,len(expected),role));cursor=hi
    start=len(expected);expected.extend(original[cursor:]);copied.append((cursor,len(original),start))
    helper=out.base_va+len(expected);helper_start=len(expected)
    # Closed independently authored helper: no payload/table pointer is read.
    append('8b85');u32(428);append('a9070000000f85');reject_one=len(expected);u32(0)
    append('81f8');u32(64);append('0f83');reject_two=len(expected);u32(0)
    helper_next=[]
    for number,(_,dy) in enumerate(NEIGHBORS):
        append('81f8');u32(number*8);append('0f85');at=len(expected);u32(0)
        append('bf');u32(dy);append('b8');u32(1);append('c3')
        helper_next.append((at,out.base_va+len(expected),'adjacent_unit_v2_internal:count.dy.next.'+str(number)))
    helper_reject=out.base_va+len(expected);append('b8');u32(0);append('c3')
    def mapped(old_va):
        old=old_va-content.base_va
        hits=[out.base_va+new+old-lo for lo,hi,new in copied if lo<=old<hi]
        hits += [out.base_va+new_lo for lo,hi,new_lo,new_hi,role in replaced if lo<hi and old==lo and not role.startswith('drop_')]
        for lo,hi,new_lo,new_hi,role in replaced:
            if role.startswith('drop_admissions_') and old==lo:
                hits.append(mapped(content.base_va+hi))
        _require(len(hits)==1,"source transfer escaped retained selected-seven instruction ranges")
        return hits[0]
    fields={}
    def typed(at,kind,target,purpose):
        _require(at not in fields,"duplicate authored Count model operand");fields[at]=(kind,target,purpose)
    for lo,hi,new in copied:
        for row in content.relocations:
            if not lo<=row.offset<hi:continue
            _require(row.offset+4<=hi,"retained Count model operand crosses source boundary")
            at=new+row.offset-lo
            if row.kind=='abs32':typed(at,'abs32',row.target,row.purpose)
            else:
                _require(row.kind=='rel32',"source Count relative role required")
                if content.base_va<=row.target<content.base_va+len(original):
                    _require(row.purpose.startswith('content_v2_internal:'),"source internal Count role differs")
                    label=row.purpose.split(':',1)[1]
                    if label.startswith('site_receipt.next.'):
                        old_number=int(label.rsplit('.',1)[1])
                        _require(old_number in SOURCE_INDICES,"retained native site namespace required")
                        label='site_receipt.next.'+str(SOURCE_INDICES.index(old_number))
                    typed(at,'rel32',mapped(row.target),'adjacent_unit_v2_internal:'+label)
                else:
                    _require(row.target==dict(field.private_entries)['check_invocation'] and
                        row.purpose=='private current V2 complete content receipt' and original[row.offset-1]==0xe8,
                        "sole source external Count field CALL required")
                    typed(at,'rel32',row.target,row.purpose)
    for at,target,purpose in new_fields:
        resolved=(helper if target=='dy' else target[1] if type(target) is tuple and target[0]=='model'
            else local_labels[target[1]] if type(target) is tuple and target[0]=='label' else mapped(target))
        typed(at,'rel32',resolved,purpose)
    for at,target,purpose in new_absolutes:typed(at,'abs32',target,purpose)
    for at in (reject_one,reject_two):typed(at,'rel32',helper_reject,'adjacent_unit_v2_internal:count.dy.reject')
    for at,target,purpose in helper_next:typed(at,'rel32',target,purpose)
    # Fourteen source-owned SITE scalar changes; never numeric-address guesses.
    scalar_changes=[]
    for number,old_number in enumerate(SOURCE_INDICES):
        body=content.body_receipts[old_number]
        lo=body[1]-content.base_va;hi=body[3]-content.base_va
        pattern=b'\xb8'+struct.pack('<I',old_number)+bytes.fromhex('8985c8000000')
        hits=[];cursor=lo
        while True:
            at=original.find(pattern,cursor,hi)
            if at<0:break
            hits.append(at+1);cursor=at+1
        _require(len(hits)==1,"one exact body SITE scalar required")
        for old in (hits[0],ladder_starts[old_number]+8):
            at=mapped(content.base_va+old)-out.base_va
            _require(at not in fields and struct.unpack_from('<I',expected,at)[0]==old_number,
                "authored Count SITE scalar differs")
            struct.pack_into('<I',expected,at,number);scalar_changes.append((old,at,old_number,number))
    for at,(kind,target,_) in fields.items():
        struct.pack_into('<I',expected,at,target if kind=='abs32' else (target-out.base_va-at-4)&0xffffffff)
    entries=tuple((f'site_{va:06x}',mapped(dict(content.entries)[f'site_{va:06x}'])) for va in BODY_SITES)
    private_entries=tuple((name,mapped(va)) for name,va in content.private_entries)+(('count_expected_dy',helper),)
    bodies=tuple((row[0],*(mapped(va) for va in row[1:])) for row in (content.body_receipts[i] for i in SOURCE_INDICES))
    blocks=tuple(('canonical_content_block_'+str(i),content.base_va+lo,content.base_va+hi,_sha(original[lo:hi]),
        out.base_va+new,out.base_va+new+hi-lo) for i,(lo,hi,new) in enumerate(copied))
    for lo,hi,new_lo,new_hi,role in replaced:
        receipts.append((role,content.base_va+lo,content.base_va+hi,out.base_va+new_lo,out.base_va+new_hi,
            _sha(original[lo:hi]),_sha(bytes(expected[new_lo:new_hi]))))
    for old,new,before,after in scalar_changes:
        receipts.append(('site_scalar',content.base_va+old,content.base_va+old+4,out.base_va+new,out.base_va+new+4,
            _sha(struct.pack('<I',before)),_sha(struct.pack('<I',after))))
    receipts.append(('authoritative_dy_helper',None,None,helper,out.base_va+len(expected),None,_sha(bytes(expected[helper_start:]))))
    _require(out.code==bytes(expected) and out.entries==entries and out.private_entries==private_entries and
        out.body_receipts==bodies,"complete independent Count model bytes/entries/receipts differ")
    if check_receipts:
        _require(out.source_blocks==blocks and out.transform_receipts==tuple(receipts),
            "complete Count model source mapping/transform receipts differ")
    return fields,blocks,tuple(receipts)

def _inventory(out,authored,*,internal_prefix,external):
    rows=_decode(out.code);starts={start for start,_,_ in rows};declared={r.offset:r for r in out.relocations}
    _require(len(declared)==len(out.relocations) and
        {at:(r.kind,r.target,r.purpose) for at,r in declared.items()}==authored,"exact Count typed operand roles differ")
    consumed=set();records=[]
    for start,end,fields in rows:
        for at,size,role in fields:
            row=declared.get(at);value=int.from_bytes(out.code[at:at+size],'little')
            if role=='relative':
                _require(row is not None and row.kind=='rel32',"missing Count relative operand")
                value=out.base_va+at+4+struct.unpack_from('<i',out.code,at)[0]
                _require(value==row.target,"Count relative target differs")
                if out.base_va<=value<out.base_va+len(out.code):
                    _require(value-out.base_va in starts and row.purpose.startswith(internal_prefix),"Count internal boundary differs")
                    typed='internal_transfer'
                else:
                    _require(row.purpose in external and out.code[start]==external[row.purpose][0] and
                        value in external[row.purpose][1],"unexpected Count external transfer")
                    typed=row.purpose
                kind='rel32'
            elif row is not None:
                _require(size==4 and role in ('immediate','memory_address') and row.kind=='abs32' and value==row.target,
                    "Count absolute role differs")
                kind,typed='abs32','authored_address'
            else:
                _require(role!='memory_address',"missing Count memory relocation");kind,typed='scalar'+str(size*8),role
            if row is not None:consumed.add(at)
            records.append(Operand(start,end-start,at,kind,typed,value))
    _require(consumed==set(declared) and all(va-out.base_va in starts for _,va in out.entries+out.private_entries),
        "complete Count operand/entry boundary coverage required")
    return tuple(sorted(records,key=lambda r:r.offset))

def _model_operand_inventory(out,content,field,*,template_source=None):
    if template_source is None:template_source=_read(ROOT/TEMPLATE)[0]
    fields,_,_=_model_contract(out,content,field,template_source)
    return _inventory(out,fields,internal_prefix='adjacent_unit_v2_internal:',external={
        'private current V2 complete content receipt':(0xe8,{dict(field.private_entries)['check_invocation']})})

REPLAY_BODY_SITES = (0x42f7cf,0x42f84a,0x42f9af,0x42f9c3,0x42f9d7,0x42f9ec,
    0x42fc5f,0x42fc92,0x42fcea,0x42fd26,0x42fd7f,0x42fdc0,0x42fe23,0x42fe68,0x42febb,0x426f44,0x426f54)

def _frozen_windows(ledger_source):
    _require(type(ledger_source) is bytes and _sha(ledger_source) == LEDGER_SHA256,
             "whole frozen native continuation ledger required")
    template = _read(ROOT / TEMPLATE)[0]
    _require(_sha(template) == TEMPLATE_SHA256, "whole frozen content template required")
    sites = _literal(template, "SITES")
    windows = _literal(ledger_source, "CONTENT_WINDOWS")
    highlow = _literal(ledger_source, "NATIVE_HIGHLOW")
    _require(type(sites) is type(windows) is type(highlow) is tuple and
             len(sites) == len(windows) == 28 and len(highlow) == len(set(highlow)) == 17 and
             tuple(row[0] for row in windows) == tuple(row[0] for row in sites),
             "complete frozen native content replay inventory differs")
    result = []
    for site, (va, window_hex) in zip(sites, windows):
        if site[2] == "tile":
            continue
        operand, window = bytes.fromhex(site[1]), bytes.fromhex(window_hex)
        if operand[:2] == b"\x0f\xbf":
            destination, bits = (operand[2] >> 3) & 7, 32
            _require(len(operand) in (7, 8), "whole native content MOVSX required")
        elif operand[:2] == b"\x66\x8b":
            destination, bits = (operand[2] >> 3) & 7, 16
            _require(len(operand) == 7 and destination == 0, "whole native AX operand required")
        else:
            _require(operand[0] == 0x8a and len(operand) in (6, 7), "whole native byte operand required")
            destination, bits = (operand[1] >> 3) & 7, 8
            _require(destination in (2, 3), "fixed native DL/BL destination required")
        _require(va == site[0] and site[2] in BODY_SP and destination in (0, 1, 2, 3) and
                 window.startswith(operand) and 9 <= len(window) <= 13,
                 "complete native content operand/window required")
        removed = tuple(h - 0x400000 for h in highlow if va <= h < va + len(window))
        result.append((site, window, destination, bits, removed))
    _require(tuple(row[0][0] for row in result) == REPLAY_BODY_SITES and
             tuple(rva for row in result for rva in row[4]) == (0x2f9cc,),
             "seventeen ordered native content windows/one HIGHLOW required")
    return tuple(row for row in result if row[0][0] in BODY_SITES)

def _model_block(model,number):
    _require(len(model.body_receipts)==7 and tuple(row[0] for row in model.body_receipts)==BODY_SITES and
        tuple(dict(model.private_entries))==('capture_inputs','capture_stack','admit_body','fixed_receipt','unsafe_control',
            'finish_rejected','finish_valid','count_expected_dy'),"complete corrected Count model ABI required")
    va,entry,payload,pc,denied,fault,valid=model.body_receipts[number]
    end=model.body_receipts[number+1][1] if number+1<len(model.body_receipts) else dict(model.private_entries)['finish_rejected']
    lo,hi=entry-model.base_va,end-model.base_va;raw=model.code[lo:hi]
    _require(0<=lo<hi<=len(model.code) and entry<pc<payload<valid<fault<denied<end and
        raw[:11]==b'\x9c\x60\xfc\x81\xec'+struct.pack('<I',784)+b'\x89\xe5',"complete real Count model body receipt required")
    at=pc-model.base_va-4;rows=[r for r in model.relocations if r.offset==at]
    _require(len(rows)==1 and (rows[0].kind,rows[0].target,rows[0].purpose)==
        ('rel32',dict(model.private_entries)['admit_body'],'adjacent_unit_v2_internal:admit_body') and model.code[at-1]==0xe8,
        "actual corrected Count admission CALL required")
    return va,entry,payload,pc,denied,fault,valid,end,lo,hi,raw,at

def _raw_adapters(layout, field, model, *, assembler_module, ledger_source):
    """Complete real seven-site blocks, exact native destinations and tails."""
    windows = _frozen_windows(ledger_source)
    base = (model.base_va + len(model.code) + 15) & ~15
    a = assembler_module._Assembler(base)
    parent = dict(model.private_entries)
    assembler_module.absolute_relocation_offsets(model)
    sources, hooks, bodies = [], [], []

    def transfer(target, purpose, opcode="e9"):
        a.emit(opcode)
        at = len(a.code)
        a.relocations.append(assembler_module.Relocation(at, "rel32", target, purpose))
        a.u32(target - base - at - 4)

    def internal(at, label):
        struct.pack_into("<I", a.code, at, 0)
        a.fixups.append((at, label))

    def tail_preconditions(va):
        if va == 0x42f9c3:
            # The displaced ADD addresses the eight-entry, 64-byte table by
            # native EDI. Parent admission has captured this exact register.
            a.emit("89c38b85"); a.u32(400)
            a.emit("a907000000"); a.branch("0f85", "unsafe_control")
            a.emit("83f840"); a.branch("0f83", "unsafe_control")
            a.emit("89d8")
        elif va == 0x42f9ec:
            # The compared owner belongs to SELF, not necessarily the payload
            # neighbor INDEX. UNIT_S-28 is a captured/rechecked ancestor word.
            a.emit("89c38bb5"); a.u32(216)
            a.emit("8b46e481f8"); a.u32(22 * 31)
            a.branch("0f83", "unsafe_control")
            a.emit("31d2b91f000000f7f185d2"); a.branch("0f85", "unsafe_control")
            a.emit("6bc01f8b8d"); a.u32(372)
            a.emit("01c8"); a.branch("0f82", "unsafe_control")
            a.emit("3b85"); a.u32(420)
            a.branch("0f85", "unsafe_control")
            a.emit("89d8")

    def scalar_tail(site, window, removed):
        va = site[0]
        tail = window[len(bytes.fromhex(site[1])):]
        allowed = (b"\x6b\xc0\x58", b"\x83\xf8\xff", b"\x01\xd8\x6b\xc0\x28",
                   b"\x03\x87\x38\x33\x51\x00", b"\x3a\x9a\x56\x03\x00\x00",
                   b"\x83\xf8\x1b", b"\x83\xf9\xff", b"\x3a\x57\x02")
        _require(tail in allowed, "closed exact native model scalar tail required")
        at = len(a.code)
        a.emit(tail.hex())
        if removed:
            _require(va == 0x42f9c3 and removed == (0x2f9cc,) and
                     tail == b"\x03\x87\x38\x33\x51\x00",
                     "complete stolen neighbor-table HIGHLOW operand required")
            a.relocations.append(assembler_module.Relocation(at + 2, "abs32", 0x513338,
                "native_adjacent_unit_scalar_highlow"))

    for number, (site, window, destination, bits, removed) in enumerate(windows):
        va, old_entry, old_payload, old_pc, old_denied, old_fault, old_valid, old_end, lo, hi, raw, admit_at = _model_block(model, number)
        _require(va == site[0], "ordered source-owned model body required")
        start, entry = len(a.code), base + len(a.code)
        dispatch, guard = f"finish_{va:06x}", f"admit_{va:06x}"
        a.label(f"site_{va:06x}")
        a.emit(raw.hex())
        for row in model.relocations:
            if not lo <= row.offset < hi:
                continue
            _require(row.offset + 4 <= hi, "model replay relocation crosses source boundary")
            at = start + row.offset - lo
            if row.kind == "abs32":
                a.relocations.append(assembler_module.Relocation(at, "abs32", row.target,
                    "adjacent_unit_adapter_source_absolute:" + row.purpose))
            elif row.offset == admit_at:
                internal(at, guard)
            elif old_entry <= row.target < old_end:
                _require(row.kind == "rel32", "source-owned internal model relative required")
                target = entry + row.target - old_entry
                struct.pack_into("<i", a.code, at, target - base - at - 4)
                a.relocations.append(assembler_module.Relocation(at, "rel32", target,
                    "adjacent_unit_adapter_internal:source_block"))
            elif row.target in (parent["finish_rejected"], parent["finish_valid"]):
                _require(row.kind == "rel32" and a.code[at - 1] == 0xe9,
                         "outer model replay finish JMP required")
                internal(at, dispatch)
            else:
                _require(row.kind == "rel32" and row.target == parent["capture_inputs"] and
                         a.code[at - 1] == 0xe8, "unexpected external model block transfer")
                struct.pack_into("<i", a.code, at, row.target - base - at - 4)
                a.relocations.append(assembler_module.Relocation(at, "rel32", row.target,
                    "adjacent_unit_adapter_capture_inputs"))
        a.label(dispatch)
        a.emit("83fa01"); a.branch("0f85", "unsafe_control")
        a.emit("39ec"); a.branch("0f85", "unsafe_control")
        a.emit("8b95"); a.u32(NATIVE_RETURN)
        a.emit("81fa"); a.absolute(va + 5, "natural native model body CALL return")
        a.branch("0f85", "unsafe_control")
        tail_preconditions(va)
        saved_destination = HELPER_BYTES + {0: 28, 1: 24, 2: 20, 3: 16}[destination]
        a.emit("668985" if bits == 16 else "8885" if bits == 8 else "8985")
        a.u32(saved_destination)
        a.emit("81c4"); a.u32(HELPER_BYTES)
        a.emit("619d8d642404")
        scalar_tail(site, window, removed)
        transfer(va + len(window), "native_adjacent_unit_resume")
        a.label(guard)
        a.emit("8d4c240439cd"); a.branch("0f85", "unsafe_control")
        a.emit("8b042481f8")
        a.absolute(entry + old_pc - old_entry, "actual model adapter admission CALL return")
        a.branch("0f85", "unsafe_control")
        transfer(parent["admit_body"], "native_adjacent_unit_admission_parent")
        bodies.append((va, entry, entry + old_payload - old_entry, entry + old_pc - old_entry,
                       entry + old_denied - old_entry, entry + old_fault - old_entry,
                       entry + old_valid - old_entry, base + a.labels[dispatch], va + len(window)))
        sources.append((va, old_entry, old_end, _sha(raw), entry, old_pc))
        hooks.append((va, window, entry, "adjacent_unit_v2_operand", removed))
    a.label("unsafe_control"); a.emit("0f0b")
    code = bytes(a.finish())
    for off, label in a.fixups:
        a.relocations.append(assembler_module.Relocation(off, "rel32", base + a.labels[label],
            "adjacent_unit_adapter_internal:" + label))
    _require(base + len(code) <= layout.rx.va + layout.rx.size,
             "model replay exceeds fresh RX reservation")
    out = AdjacentUnitAdaptersEmission(base, layout.rw.va, code,
        tuple((f"site_{va:06x}", base + a.labels[f"site_{va:06x}"]) for va in BODY_SITES),
        tuple(a.relocations), field.width, field.height,
        (("unsafe_control", base + a.labels["unsafe_control"]),) +
        tuple((f"admit_{va:06x}", base + a.labels[f"admit_{va:06x}"]) for va in BODY_SITES),
        tuple(bodies), tuple(sources), tuple(hooks))
    assembler_module.absolute_relocation_offsets(out)
    _adapter_operand_inventory(out, model, ledger_source=ledger_source)
    return out

def _adapter_contract(out, model, ledger_source):
    """Independently rebuild every permitted byte and operand role.

    No relocation declaration in ``out`` selects an address or changes an
    instruction's meaning. The native indexed table displacement is the sole
    explicit displacement/HIGHLOW exception, not a numeric-VA heuristic.
    """
    windows = _frozen_windows(ledger_source)
    parent = dict(model.private_entries)
    expected, fields, bodies, sources, hooks, entries, guards = bytearray(), {}, [], [], [], [], []
    pending = []

    def field(at, kind, target, purpose):
        _require(at not in fields, "duplicate authored model replay operand")
        fields[at] = (kind, target, purpose)

    def emit(raw):
        expected.extend(bytes.fromhex(raw))

    def u32(value):
        expected.extend(struct.pack("<I", value & 0xffffffff))

    def unsafe(opcode):
        emit(opcode); pending.append(len(expected)); u32(0)

    def absolute(value, purpose):
        field(len(expected), "abs32", value, purpose); u32(value)

    def relative(value, purpose):
        field(len(expected), "rel32", value, purpose); u32(0)

    for number, (site, window, destination, bits, removed) in enumerate(windows):
        va, old_entry, old_payload, old_pc, old_denied, old_fault, old_valid, old_end, lo, hi, raw, admit_at = _model_block(model, number)
        _require(va == site[0], "authored model body ordering differs")
        start, entry = len(expected), out.base_va + len(expected)
        dispatch = entry + len(raw)
        expected.extend(raw)
        source_admit = None
        source_finishes = []
        for row in model.relocations:
            if not lo <= row.offset < hi:
                continue
            _require(row.offset + 4 <= hi, "authored model relocation crosses source block")
            at = start + row.offset - lo
            if row.kind == "abs32":
                field(at, "abs32", row.target, "adjacent_unit_adapter_source_absolute:" + row.purpose)
            elif row.offset == admit_at:
                _require(row.kind == "rel32" and row.target == parent["admit_body"] and
                         row.purpose == "adjacent_unit_v2_internal:admit_body" and raw[row.offset - lo - 1] == 0xe8,
                         "whole authored model admission CALL differs")
                source_admit = at
            elif old_entry <= row.target < old_end:
                _require(row.kind == "rel32", "authored model internal relative required")
                field(at, "rel32", entry + row.target - old_entry, "adjacent_unit_adapter_internal:source_block")
            elif row.target in (parent["finish_rejected"], parent["finish_valid"]):
                _require(row.kind == "rel32" and raw[row.offset - lo - 1] == 0xe9,
                         "authored outer model finish JMP required")
                source_finishes.append(at)
            else:
                _require(row.kind == "rel32" and row.target == parent["capture_inputs"] and
                         raw[row.offset - lo - 1] == 0xe8, "authored model capture CALL differs")
                field(at, "rel32", row.target, "adjacent_unit_adapter_capture_inputs")
        emit("83fa01"); unsafe("0f85")
        emit("39ec"); unsafe("0f85")
        emit("8b95"); u32(NATIVE_RETURN)
        emit("81fa"); absolute(va + 5, "natural native model body CALL return")
        unsafe("0f85")
        if va == 0x42f9c3:
            emit("89c38b85"); u32(400)
            emit("a907000000"); unsafe("0f85")
            emit("83f840"); unsafe("0f83")
            emit("89d8")
        elif va == 0x42f9ec:
            emit("89c38bb5"); u32(216)
            emit("8b46e481f8"); u32(682)
            unsafe("0f83")
            emit("31d2b91f000000f7f185d2"); unsafe("0f85")
            emit("6bc01f8b8d"); u32(372)
            emit("01c8"); unsafe("0f82")
            emit("3b85"); u32(420)
            unsafe("0f85")
            emit("89d8")
        emit("668985" if bits == 16 else "8885" if bits == 8 else "8985")
        u32(HELPER_BYTES + {0: 28, 1: 24, 2: 20, 3: 16}[destination])
        emit("81c4"); u32(HELPER_BYTES)
        emit("619d8d642404")
        tail = window[len(bytes.fromhex(site[1])):]
        if removed:
            _require(va == 0x42f9c3 and removed == (0x2f9cc,) and
                     tail == b"\x03\x87\x38\x33\x51\x00",
                     "exact authored native neighbor-table displacement required")
            field(len(expected) + 2, "abs32", 0x513338, "native_adjacent_unit_scalar_highlow")
        expected.extend(tail)
        emit("e9"); relative(va + len(window), "native_adjacent_unit_resume")
        guard = out.base_va + len(expected)
        emit("8d4c240439cd"); unsafe("0f85")
        emit("8b042481f8")
        absolute(entry + old_pc - old_entry, "actual model adapter admission CALL return")
        unsafe("0f85")
        emit("e9"); relative(parent["admit_body"], "native_adjacent_unit_admission_parent")
        _require(source_admit is not None and source_finishes, "complete authored model CALL/finish required")
        field(source_admit, "rel32", guard, f"adjacent_unit_adapter_internal:admit_{va:06x}")
        for at in source_finishes:
            field(at, "rel32", dispatch, f"adjacent_unit_adapter_internal:finish_{va:06x}")
        bodies.append((va, entry, entry + old_payload - old_entry, entry + old_pc - old_entry,
                       entry + old_denied - old_entry, entry + old_fault - old_entry,
                       entry + old_valid - old_entry, dispatch, va + len(window)))
        sources.append((va, old_entry, old_end, _sha(raw), entry, old_pc))
        hooks.append((va, window, entry, "adjacent_unit_v2_operand", removed))
        entries.append((f"site_{va:06x}", entry))
        guards.append((f"admit_{va:06x}", guard))
    terminal = out.base_va + len(expected)
    emit("0f0b")
    for at in pending:
        field(at, "rel32", terminal, "adjacent_unit_adapter_internal:unsafe_control")
    for at, (kind, target, _) in fields.items():
        struct.pack_into("<I", expected, at,
            target if kind == "abs32" else (target - out.base_va - at - 4) & 0xffffffff)
    _require(out.entries == tuple(entries) and
             out.private_entries == (("unsafe_control", terminal),) + tuple(guards) and
             out.body_receipts == tuple(bodies) and out.source_blocks == tuple(sources) and
             out.planned_hooks == tuple(hooks), "complete authored model receipt/window inventory differs")
    _require(out.code == bytes(expected), "complete authored model source/native finish bytes differ")
    return fields

def _adapter_operand_inventory(out, model, *, ledger_source=None):
    if ledger_source is None:
        ledger_source = _read(ROOT / LEDGER)[0]
    authored = _adapter_contract(out, model, ledger_source)
    rows = _decode(out.code)
    starts = {start for start, _, _ in rows}
    declared = {r.offset: r for r in out.relocations}
    _require(len(declared) == len(out.relocations), "duplicate model replay operand")
    _require({at: (r.kind, r.target, r.purpose) for at, r in declared.items()} == authored,
             "exact authored model absolute/relative operand roles differ")
    consumed, records = set(), []
    parent = dict(model.private_entries)
    resumes = {va + len(raw) for va, raw, *_ in out.planned_hooks}
    for start, end, fields in rows:
        for at, size, role in fields:
            row = declared.get(at)
            value = int.from_bytes(out.code[at:at + size], "little")
            if role == "relative":
                _require(row is not None and row.kind == "rel32", "missing model replay relative operand")
                value = out.base_va + at + 4 + struct.unpack_from("<i", out.code, at)[0]
                _require(value == row.target, "model replay relative target differs")
                if out.base_va <= value < out.base_va + len(out.code):
                    _require(value - out.base_va in starts and row.purpose.startswith("adjacent_unit_adapter_internal:"),
                             "model replay internal instruction boundary differs")
                    typed = "internal_transfer"
                else:
                    contract = {"adjacent_unit_adapter_capture_inputs": (0xe8, {parent["capture_inputs"]}),
                                "native_adjacent_unit_admission_parent": (0xe9, {parent["admit_body"]}),
                                "native_adjacent_unit_resume": (0xe9, resumes)}
                    _require(row.purpose in contract and out.code[start] == contract[row.purpose][0] and
                             value in contract[row.purpose][1], "unexpected external model replay transfer")
                    typed = row.purpose
                kind = "rel32"
            elif row is not None:
                table = row.purpose == "native_adjacent_unit_scalar_highlow"
                _require(size == 4 and row.kind == "abs32" and value == row.target and
                         (role in ("immediate", "memory_address") or
                          table and role == "displacement" and row.target == 0x513338 and
                          out.code[start:at] == b"\x03\x87"),
                         "model replay explicit absolute operand differs")
                kind, typed = "abs32", "native_table_base_displacement" if table else "authored_address"
            else:
                _require(role != "memory_address", "missing model replay memory relocation")
                kind, typed = "scalar" + str(size * 8), role
            if row is not None:
                consumed.add(at)
            records.append(Operand(start, end - start, at, kind, typed, value))
    _require(consumed == set(declared) and all(va - out.base_va in starts for _, va in out.entries + out.private_entries),
             "model replay relocation/entry boundary differs")
    return tuple(sorted(records, key=lambda row: row.offset))

def _entry_native_contract(template_source):
    _require(type(template_source) is bytes and _sha(template_source) == TEMPLATE_SHA256,
             "whole frozen Count native/source ledger required")
    sites = _literal(template_source, "SITES")
    spans = _literal(template_source, "NATIVE_SPANS")
    prologues = _literal(template_source, "PROLOGUES")
    _require(type(sites) is tuple and len(sites) == 28 and
             sites[12] == (PARENT_SITE, "0fbf8254030000", "unit", "unit_type", 0, 0) and
             spans["count"] == (NATIVE_COUNT, COUNT_END, COUNT_SHA256),
             "whole frozen Unit admission/Count span contract differs")
    rows = [row for row in prologues if row[0] == NATIVE_COUNT]
    _require(rows == [(NATIVE_COUNT, "53515256575583ec0489c7")],
             "whole frozen Count native prologue differs")
    return b"\xe8" + struct.pack("<i", NATIVE_COUNT - NATIVE_RET), bytes.fromhex(rows[0][1])

def _source_receipts(content, field, template_source):
    _entry_native_contract(template_source)
    private = dict(content.private_entries)
    _require(tuple(private) == ("capture_inputs", "capture_stack", "admit_body", "fixed_receipt",
                               "unsafe_control", "finish_rejected", "finish_valid", "count_expected_dy") and
             len(content.body_receipts) == 7, "complete fresh Count admission parent required")
    site, entry, payload, pc, denied, fault, valid = content.body_receipts[PARENT_SITE_NUMBER]
    _require(site == PARENT_SITE and entry < pc < payload < valid < fault < denied and
             dict(content.entries)["site_42f84a"] == entry, "actual Unit admission prefix receipt differs")
    lo, hi = entry - content.base_va, payload - content.base_va
    prefix = content.code[lo:hi]
    _require(0 <= lo < hi <= len(content.code) and
             prefix[:11] == b"\x9c\x60\xfc\x81\xec" + struct.pack("<I", HELPER_BYTES) + b"\x89\xe5" and
             prefix[-12:-6] == b"\x81\xf8\x01\0\0\0" and prefix[-6:-4] == b"\x0f\x85",
             "whole actual 784-byte Unit prefix required")
    calls = [r for r in content.relocations if lo <= r.offset < hi and r.kind == "rel32"]
    capture = [r for r in calls if r.target == private["capture_inputs"] and
               r.purpose == "adjacent_unit_v2_internal:capture_inputs" and content.code[r.offset - 1] == 0xe8]
    admission = [r for r in calls if r.offset == pc - content.base_va - 4 and
                 r.target == private["admit_body"] and r.purpose == "adjacent_unit_v2_internal:admit_body" and
                 content.code[r.offset - 1] == 0xe8]
    rejection = [r for r in calls if r.offset == hi - 4 and r.target == denied and
                 r.purpose == "adjacent_unit_v2_internal:site_42f84a.denied"]
    _require(len(capture) == len(admission) == len(rejection) == 1 and len(calls) == 3,
             "whole Unit prefix capture/admission/denial transfers required")
    private_lo, private_hi = private["capture_inputs"], content.base_va + len(content.code)
    _require(payload < private["finish_rejected"] <= private["finish_valid"] < private_lo < private_hi and
             private_lo < private["capture_stack"] < private["admit_body"] < private["fixed_receipt"] <
             private["unsafe_control"] < private["count_expected_dy"] < private_hi and
             content.code[private["unsafe_control"]-content.base_va:private["unsafe_control"]-content.base_va+2] == b"\x0f\x0b" and
             content.code[-6:] == bytes.fromhex("b800000000c3"),
             "complete actual private ContentV2 region required")
    p_lo = private_lo - content.base_va
    replacements = [r for r in content.relocations if p_lo <= r.offset < len(content.code) and
                    (r.kind, r.target, r.purpose) ==
                    ("abs32", PARENT_SITE + 5, "fixed proposed body CALL return PC")]
    _require(len(replacements) == 1 and
             content.code[replacements[0].offset - 2:replacements[0].offset] == b"\x81\xf8" and
             struct.unpack_from("<I", content.code, replacements[0].offset)[0] == PARENT_SITE + 5,
             "one exact proposed Unit return CMP operand required")
    check = dict(field.private_entries)["check_invocation"]
    external = [r for r in content.relocations if p_lo <= r.offset < len(content.code) and
                r.kind == "rel32" and not private_lo <= r.target < private_hi]
    _require(len(external) == 1 and external[0].target == check and
             external[0].purpose == "private current V2 complete content receipt" and
             content.code[external[0].offset - 1] == 0xe8,
             "sole callback-free external field receipt CALL required")
    return dict(site=site, entry=entry, payload=payload, pc=pc, denied=denied,
        prefix_lo=lo, prefix_hi=hi, prefix=prefix, capture_offset=capture[0].offset,
        admission_offset=admission[0].offset, rejection_offset=rejection[0].offset,
        private_lo=private_lo, private_hi=private_hi, private_offset=p_lo,
        private=content.code[p_lo:], changed_offset=replacements[0].offset,
        private_entries=tuple((name, va) for name, va in content.private_entries if private_lo <= va < private_hi),
        field_check=check)

def _raw_count_entry(layout, field, content, previous_adapters, *, assembler_module, template_source):
    source = _source_receipts(content, field, template_source)
    base = (previous_adapters.base_va + len(previous_adapters.code) + 15) & ~15
    a = assembler_module._Assembler(base)
    assembler_module.absolute_relocation_offsets(content)

    def internal(at, label):
        struct.pack_into("<I", a.code, at, 0)
        a.fixups.append((at, label))

    def transfer(target, purpose, opcode="e9"):
        a.emit(opcode)
        at = len(a.code)
        a.relocations.append(assembler_module.Relocation(at, "rel32", target, purpose))
        a.u32(target - base - at - 4)

    def get(reg, offset):
        a.emit("8b" + f"{0x85 | reg << 3:02x}"); a.u32(offset)

    a.label("count_entry"); a.emit(source["prefix"].hex())
    for row in content.relocations:
        if not source["prefix_lo"] <= row.offset < source["prefix_hi"]:
            continue
        _require(row.offset + 4 <= source["prefix_hi"] and row.kind == "rel32",
                 "exact Unit prefix relative-only inventory required")
        at = row.offset - source["prefix_lo"]
        labels = {source["capture_offset"]: "clone.capture_inputs",
                  source["admission_offset"]: "admission_guard",
                  source["rejection_offset"]: "unsafe_control"}
        _require(row.offset in labels, "unexpected Unit prefix operand")
        internal(at, labels[row.offset])
    a.label("admitted")
    a.emit("39ec"); a.branch("0f85", "unsafe_control")
    get(2, NATIVE_RETURN)
    a.emit("81fa"); a.absolute(NATIVE_RET, "natural Count draw CALL return")
    a.branch("0f85", "unsafe_control")
    # Admission EAX=1 is not Count's input. The original input is a saved DWORD.
    get(0, 428); get(7, 372)
    a.emit("29f881c0"); a.u32(-852)
    a.emit("81f8"); a.u32(22 * 31); a.branch("0f83", "unsafe_control")
    a.emit("31d2b91f000000f7f185d2"); a.branch("0f85", "unsafe_control")
    # Native pre-CALL derives the SELF record and its byte offset from ESI.
    # Neither arbitrary valid records nor the n=-1 sentinel are admitted.
    get(1, 404); a.emit("81f9"); a.u32(22)
    a.branch("0f83", "unsafe_control")
    a.emit("39c8"); a.branch("0f85", "unsafe_control")
    a.emit("6bc01f3b85"); a.u32(420)
    a.branch("0f85", "unsafe_control")
    get(6, 428)
    a.emit("0fb746048b8f"); a.u32(804)
    a.emit("39c8"); a.branch("0f83", "unsafe_control")
    a.emit("0fb756068b8f"); a.u32(800)
    a.emit("39ca"); a.branch("0f83", "unsafe_control")
    # Keep the authentic native return word. POPAD restores Count's original
    # EAX/EDX/other inputs; neither value/status finish nor LEA ESP,+4 is used.
    a.emit("81c4"); a.u32(HELPER_BYTES); a.emit("619d")
    transfer(NATIVE_COUNT, "native_count_entry")
    a.label("admission_guard")
    a.emit("8d4c240439cd"); a.branch("0f85", "unsafe_control")
    a.emit("8b042481f8")
    a.absolute(base + source["pc"] - source["entry"], "actual Count adapter admission CALL return")
    a.branch("0f85", "unsafe_control")
    a.branch("e9", "clone.admit_body")
    a.label("unsafe_control"); a.emit("0f0b")
    clone = base + len(a.code)
    private_start = len(a.code)
    a.emit(source["private"].hex())
    for name, va in source["private_entries"]:
        a.labels["clone." + name] = private_start + va - source["private_lo"]
    for row in content.relocations:
        if not source["private_offset"] <= row.offset < len(content.code):
            continue
        _require(row.offset + 4 <= len(content.code), "private Count relocation crosses complete region")
        at = private_start + row.offset - source["private_offset"]
        if row.kind == "abs32":
            target = NATIVE_RET if row.offset == source["changed_offset"] else row.target
            purpose = "adjacent_unit_entry_private_native_return" if row.offset == source["changed_offset"] else (
                "adjacent_unit_entry_private_absolute:" + row.purpose)
            struct.pack_into("<I", a.code, at, target)
            a.relocations.append(assembler_module.Relocation(at, "abs32", target, purpose))
        else:
            _require(row.kind == "rel32", "private Count typed relative operand required")
            if source["private_lo"] <= row.target < source["private_hi"]:
                target, purpose = clone + row.target - source["private_lo"], "adjacent_unit_entry_internal:private"
            else:
                _require(row.target == source["field_check"] and a.code[at - 1] == 0xe8 and
                         row.purpose == "private current V2 complete content receipt",
                         "private Count external receipt differs")
                target, purpose = row.target, "adjacent_unit_entry_field_receipt"
            struct.pack_into("<i", a.code, at, target - base - at - 4)
            a.relocations.append(assembler_module.Relocation(at, "rel32", target, purpose))
    code = bytes(a.finish())
    for off, label in a.fixups:
        a.relocations.append(assembler_module.Relocation(off, "rel32", base + a.labels[label],
            "adjacent_unit_entry_internal:" + label))
    _require(base + len(code) <= layout.rx.va + layout.rx.size, "Count entry exceeds fresh RX reservation")
    old_call, _ = _entry_native_contract(template_source)
    changed = private_start + source["changed_offset"] - source["private_offset"]
    prefix_receipt = (NATIVE_CALL, PARENT_SITE, source["entry"], source["payload"], source["pc"],
        source["denied"], _sha(source["prefix"]), base, base + a.labels["admitted"], base + source["pc"] - source["entry"])
    private_receipt = (source["private_lo"], source["private_hi"], _sha(source["private"]),
        clone, base + len(code), source["changed_offset"], changed)
    guard = (base + a.labels["admission_guard"], prefix_receipt[-1],
        base + a.labels["clone.admit_body"], clone, base + a.labels["unsafe_control"])
    private_entries = tuple((name if name != "unsafe_control" else "private_unsafe_control",
                            base + a.labels["clone." + name]) for name, _ in source["private_entries"])
    out = AdjacentUnitEntryEmission(base, layout.rw.va, code, (("count_entry", base),), tuple(a.relocations),
        field.width, field.height, private_entries + (("admission_guard", guard[0]), ("unsafe_control", guard[-1])),
        prefix_receipt, private_receipt, guard,
        (("unit_admission_prefix", source["entry"], source["payload"], _sha(source["prefix"]), base,
          base + a.labels["admitted"]),
         ("private_admission", source["private_lo"], source["private_hi"], _sha(source["private"]), clone, base + len(code))),
        ((NATIVE_CALL, old_call, base, "count_entry", ()),))
    assembler_module.absolute_relocation_offsets(out)
    _entry_operand_inventory(out, content, field, template_source=template_source)
    return out

def _entry_contract(out, content, field_emission, template_source):
    """Independently reconstruct the exact clone and authorized substitution.

    Operand declarations in ``out`` cannot select new roles. Every private
    byte, prefix receipt, source mapping and native transfer is reconstructed.
    """
    source = _source_receipts(content, field_emission, template_source)
    expected, fields, pending = bytearray(source["prefix"]), {}, []

    def field(at, kind, target, purpose):
        _require(at not in fields, "duplicate authored Count operand")
        fields[at] = (kind, target, purpose)

    def emit(raw):
        expected.extend(bytes.fromhex(raw))

    def u32(value):
        expected.extend(struct.pack("<I", value & 0xffffffff))

    def unsafe(opcode):
        emit(opcode); pending.append(len(expected)); u32(0)

    def absolute(value, purpose):
        field(len(expected), "abs32", value, purpose); u32(value)

    def relative(value, purpose):
        field(len(expected), "rel32", value, purpose); u32(0)

    suffix = out.base_va + len(expected)
    emit("39ec"); unsafe("0f85")
    emit("8b95"); u32(820)
    emit("81fa"); absolute(NATIVE_RET, "natural Count draw CALL return")
    unsafe("0f85")
    emit("8b85"); u32(428)
    emit("8bbd"); u32(372)
    emit("29f881c0"); u32(-852)
    emit("81f8"); u32(682); unsafe("0f83")
    emit("31d2b91f000000f7f185d2"); unsafe("0f85")
    emit("8b8d"); u32(404); emit("81f9"); u32(22); unsafe("0f83")
    emit("39c8"); unsafe("0f85")
    emit("6bc01f3b85"); u32(420); unsafe("0f85")
    emit("8bb5"); u32(428)
    emit("0fb746048b8f"); u32(804)
    emit("39c8"); unsafe("0f83")
    emit("0fb756068b8f"); u32(800)
    emit("39ca"); unsafe("0f83")
    emit("81c4"); u32(784); emit("619de9"); relative(NATIVE_COUNT, "native_count_entry")
    guard = out.base_va + len(expected)
    emit("8d4c240439cd"); unsafe("0f85")
    emit("8b042481f8")
    actual_pc = out.base_va + source["pc"] - source["entry"]
    absolute(actual_pc, "actual Count adapter admission CALL return")
    unsafe("0f85")
    emit("e9"); guard_target = len(expected); u32(0)
    terminal = out.base_va + len(expected)
    emit("0f0b")
    clone = out.base_va + len(expected)
    private_start = len(expected)
    expected.extend(source["private"])
    for row in content.relocations:
        if source["prefix_lo"] <= row.offset < source["prefix_hi"]:
            _require(row.offset + 4 <= source["prefix_hi"] and row.kind == "rel32",
                     "whole authored Unit prefix relative inventory required")
            at = row.offset - source["prefix_lo"]
            if row.offset == source["capture_offset"]:
                target, purpose = clone, "adjacent_unit_entry_internal:clone.capture_inputs"
            elif row.offset == source["admission_offset"]:
                target, purpose = guard, "adjacent_unit_entry_internal:admission_guard"
            else:
                _require(row.offset == source["rejection_offset"], "unknown authored prefix operand")
                target, purpose = terminal, "adjacent_unit_entry_internal:unsafe_control"
            field(at, "rel32", target, purpose)
        elif source["private_offset"] <= row.offset < len(content.code):
            _require(row.offset + 4 <= len(content.code), "whole authored private operand required")
            at = private_start + row.offset - source["private_offset"]
            if row.kind == "abs32":
                target = NATIVE_RET if row.offset == source["changed_offset"] else row.target
                purpose = "adjacent_unit_entry_private_native_return" if row.offset == source["changed_offset"] else (
                    "adjacent_unit_entry_private_absolute:" + row.purpose)
                field(at, "abs32", target, purpose)
            else:
                _require(row.kind == "rel32", "authored private Count relative required")
                if source["private_lo"] <= row.target < source["private_hi"]:
                    target, purpose = clone + row.target - source["private_lo"], "adjacent_unit_entry_internal:private"
                else:
                    _require(row.target == source["field_check"] and
                             row.purpose == "private current V2 complete content receipt" and
                             content.code[row.offset - 1] == 0xe8,
                             "authored sole Count external field CALL differs")
                    target, purpose = row.target, "adjacent_unit_entry_field_receipt"
                field(at, "rel32", target, purpose)
    cloned_entries = tuple((name if name != "unsafe_control" else "private_unsafe_control",
                           clone + va - source["private_lo"]) for name, va in source["private_entries"])
    cloned_admit = clone + dict(source["private_entries"])["admit_body"] - source["private_lo"]
    field(guard_target, "rel32", cloned_admit, "adjacent_unit_entry_internal:clone.admit_body")
    for at in pending:
        field(at, "rel32", terminal, "adjacent_unit_entry_internal:unsafe_control")
    for at, (kind, target, _) in fields.items():
        struct.pack_into("<I", expected, at,
            target if kind == "abs32" else (target - out.base_va - at - 4) & 0xffffffff)
    changed = private_start + source["changed_offset"] - source["private_offset"]
    old_call, _ = _entry_native_contract(template_source)
    prefix_receipt = (NATIVE_CALL, PARENT_SITE, source["entry"], source["payload"], source["pc"],
        source["denied"], _sha(source["prefix"]), out.base_va, suffix, actual_pc)
    private_receipt = (source["private_lo"], source["private_hi"], _sha(source["private"]),
        clone, out.base_va + len(expected), source["changed_offset"], changed)
    blocks = (("unit_admission_prefix", source["entry"], source["payload"], _sha(source["prefix"]), out.base_va, suffix),
              ("private_admission", source["private_lo"], source["private_hi"], _sha(source["private"]), clone,
               out.base_va + len(expected)))
    _require(out.entries == (("count_entry", out.base_va),) and
             out.private_entries == cloned_entries + (("admission_guard", guard), ("unsafe_control", terminal)) and
             out.prefix_receipt == prefix_receipt and out.private_clone_receipt == private_receipt and
             out.guard_receipts == (guard, actual_pc, cloned_admit, clone, terminal) and out.source_blocks == blocks and
             out.planned_hooks == ((NATIVE_CALL, old_call, out.base_va, "count_entry", ()),),
             "complete authored Count prefix/private/window receipts differ")
    _require(out.code == bytes(expected), "complete authored Count prefix/private/suffix bytes differ")
    return fields

def _entry_operand_inventory(out, content, field, *, template_source=None):
    if template_source is None:
        template_source = _read(ROOT / TEMPLATE)[0]
    authored = _entry_contract(out, content, field, template_source)
    rows = _decode(out.code)
    starts = {start for start, _, _ in rows}
    declared = {r.offset: r for r in out.relocations}
    _require(len(declared) == len(out.relocations), "duplicate Count entry operand")
    _require({at: (r.kind, r.target, r.purpose) for at, r in declared.items()} == authored,
             "exact authored Count absolute/relative operand roles differ")
    consumed, records = set(), []
    field_check = dict(field.private_entries)["check_invocation"]
    for start, end, fields in rows:
        for at, size, role in fields:
            row = declared.get(at)
            value = int.from_bytes(out.code[at:at + size], "little")
            if role == "relative":
                _require(row is not None and row.kind == "rel32", "missing Count entry relative operand")
                value = out.base_va + at + 4 + struct.unpack_from("<i", out.code, at)[0]
                _require(value == row.target, "Count relative target differs")
                if out.base_va <= value < out.base_va + len(out.code):
                    _require(value - out.base_va in starts and row.purpose.startswith("adjacent_unit_entry_internal:"),
                             "Count internal target/instruction boundary differs")
                    typed = "internal_transfer"
                else:
                    allowed = {"adjacent_unit_entry_field_receipt": (0xe8, field_check),
                               "native_count_entry": (0xe9, NATIVE_COUNT)}
                    _require(row.purpose in allowed and (out.code[start], value) == allowed[row.purpose],
                             "Count external CALL/JMP differs")
                    typed = row.purpose
                kind = "rel32"
            elif row is not None:
                _require(size == 4 and role in ("immediate", "memory_address") and
                         row.kind == "abs32" and value == row.target, "Count explicit absolute operand differs")
                kind, typed = "abs32", "authored_address"
            else:
                _require(role != "memory_address", "missing Count memory relocation")
                kind, typed = "scalar" + str(size * 8), role
            if row is not None:
                consumed.add(at)
            records.append(Operand(start, end - start, at, kind, typed, value))
    _require(consumed == set(declared) and all(va - out.base_va in starts for _, va in out.entries + out.private_entries),
             "Count relocation/entry boundary differs")
    return tuple(sorted(records, key=lambda row: row.offset))


def _emit_code(layout,life,route,field,lease,content,loss,joined_field,tile,content_replay,count_entry,
               count_model,count_adapters,*,count_body_module,count_body_kwargs,content_module,template_module,
               assembler_module,template_source):
    """Explicit synthetic boundary; every full parent emission is canonical."""
    expected_model,expected_adapters=count_body_module._emit_code(layout,life,route,field,lease,content,loss,
        joined_field,tile,content_replay,count_entry,**count_body_kwargs)
    _require(_identity(count_model)==_identity(expected_model) and _identity(count_adapters)==_identity(expected_adapters),
        "complete canonical CountBodyV2 pair, source mappings, windows and receipts required")
    model=_raw_model(layout,field,lease,content,count_adapters,content_module=content_module,
        template_module=template_module,assembler_module=assembler_module,template_source=template_source)
    ledger_source=_read(ROOT/LEDGER)[0]
    adapters=_raw_adapters(layout,field,model,assembler_module=assembler_module,ledger_source=ledger_source)
    entry=_raw_count_entry(layout,field,model,adapters,assembler_module=assembler_module,template_source=template_source)
    _require(entry.base_va+len(entry.code)<=layout.rx.va+layout.rx.size,"atomic eight-hook prefix exceeds unchanged RX")
    return model,adapters,entry

def _authenticate_count_native(original,relayout_parent,clip,pe,*,template_source=None):
    if template_source is None:template_source=_read(ROOT/TEMPLATE)[0]
    _native_contract(template_source);table=struct.pack('<16i',*(v for pair in NEIGHBORS for v in pair))
    _require(_sha(table)==TABLE_SHA256,"complete authored Count neighbor table differs")
    for image in (original,relayout_parent):
        parsed=pe.inspect_pe(image);_,relocations=pe._old_relocations(image,parsed)
        actual={parsed.image_base+rva for rva in relocations if 0x426ef0<=parsed.image_base+rva<0x426f75}
        _require(actual=={va for va,_ in COUNT_HIGHLOW},"complete original Count HIGHLOW inventory differs")
        at=clip.file_offset(image,0x426ef0,133);raw=image[at:at+133]
        _require(len(raw)==133 and _sha(raw)==COUNT_SHA256 and raw.startswith(bytes.fromhex('53515256575583ec0489c7')),
            "whole original Count span/prologue differs")
        for va,target in COUNT_HIGHLOW:
            at=clip.file_offset(image,va,4);_require(image[at:at+4]==struct.pack('<I',target),"original Count HIGHLOW target differs")
        at=clip.file_offset(image,0x514500,64);_require(image[at:at+64]==table,"complete original Count neighbor table differs")
        for va,window in zip(COUNT_SITES,COUNT_WINDOWS):
            at=clip.file_offset(image,va,len(window));_require(image[at:at+len(window)]==window,"whole original Count operand/scalar window differs")
            _require(not any(va<=parsed.image_base+rva<va+len(window) for rva in relocations),
                "Count body windows must remove no original HIGHLOW")


def _authenticate_native(original,relayout_parent,clip,pe,*,template_source=None):
    if template_source is None:template_source=_read(ROOT/TEMPLATE)[0]
    _require(type(original) is bytes and _sha(original)==BASE_SHA256,"exact original motion contract required")
    _authenticate_count_native(original,relayout_parent,clip,pe,template_source=template_source)
    # The full Unit pin authenticates original context only. Relayout receives
    # explicit complete caller/phase hashes; no assumption of unchanged Unit.
    lo,hi,digest=UNIT_SPAN;at=clip.file_offset(original,lo,hi-lo)
    _require(_sha(original[at:at+hi-lo])==digest,"complete original Unit context differs")
    windows=(CALLER_WINDOW,)+PHASE_WINDOWS
    highlow=CALLER_HIGHLOW+PHASE_HIGHLOW
    for image in (original,relayout_parent):
        parsed=pe.inspect_pe(image);_,relocations=pe._old_relocations(image,parsed)
        expected={va for va,_ in highlow}
        actual={parsed.image_base+rva for rva in relocations
            if any(lo<=parsed.image_base+rva<hi for lo,hi,_ in windows)}
        _require(actual==expected,"exact caller/phase HIGHLOW inventory differs")
        for lo,hi,digest in windows:
            at=clip.file_offset(image,lo,hi-lo);raw=image[at:at+hi-lo]
            _require(len(raw)==hi-lo and _sha(raw)==digest,"complete original/relayout motion phase window differs")
        for va,target in highlow:
            at=clip.file_offset(image,va,4)
            _require(image[at:at+4]==struct.pack('<I',target),"exact original/relayout caller/phase relocation target differs")

def _issue(original,profile,resolution):
    _require(type(original) is bytes and _sha(original)==BASE_SHA256,"exact Adjacent Unit original required")
    snapshot=_snapshot()
    with _body_module(snapshot[PARENT][0]) as body_module:
        parent=body_module._issue(original,profile,resolution)
        entry_bundle=parent.count_entry_bundle;replay_bundle=entry_bundle.content_replay_bundle
        tile_bundle=replay_bundle.tile_replay_bundle;loss_bundle=tile_bundle.field_loss_bundle
        content_bundle=loss_bundle.content_bundle;lease_bundle=content_bundle.lease_bundle
        field_bundle=lease_bundle.field_bundle;context=field_bundle.routing_bundle.lifecycle_bundle.allocation_context
        layout=context.layout
        with body_module._entry_module(snapshot[ENTRY][0]) as entry_module:
            with entry_module._replay_module(snapshot[REPLAY][0]) as replay_module:
                with replay_module._tile_module(snapshot[TILE][0]) as tile_module:
                    with tile_module._loss_module(snapshot[LOSS][0]) as loss_module:
                        with loss_module._content_module(snapshot[CONTENT][0]) as content_module:
                            with content_module._modules(snapshot) as modules:
                                clip=modules[CLIP];template=modules[TEMPLATE];raw=snapshot[TEMPLATE][0]
                                _authenticate_native(original,context.relayout_parent,clip,modules['src/patcher/pe_extension.py'],
                                    template_source=raw)
                                model=_raw_model(layout,field_bundle.emission,lease_bundle.emission,content_bundle.emission,
                                    parent.emission,content_module=content_module,template_module=template,
                                    assembler_module=clip,template_source=raw)
                                adapters=_raw_adapters(layout,field_bundle.emission,model,assembler_module=clip,
                                    ledger_source=snapshot[LEDGER][0])
                                entry=_raw_count_entry(layout,field_bundle.emission,model,adapters,assembler_module=clip,
                                    template_source=raw)
                                source,v2_ledger,count_motion_ledger,_=_whole_model_source(content_module,raw,template)
        model_inventory=_model_operand_inventory(model,content_bundle.emission,field_bundle.emission,
            template_source=snapshot[TEMPLATE][0])
        adapter_inventory=_adapter_operand_inventory(adapters,model,ledger_source=snapshot[LEDGER][0])
        entry_inventory=_entry_operand_inventory(entry,model,field_bundle.emission,template_source=snapshot[TEMPLATE][0])
        previous=tuple(row for row in replay_bundle.emission.planned_hooks if row[0] in BODY_SITES[:5])+(
            tuple(parent.emission.planned_hooks))+tuple(entry_bundle.emission.planned_hooks)
        _require(tuple(row[0] for row in previous)==BODY_SITES+(NATIVE_CALL,),"complete eight predecessor override windows required")
        hooks=adapters.planned_hooks+entry.planned_hooks
        _require(tuple(row[0] for row in hooks)==tuple(row[0] for row in previous) and
            all(a[1]==b[1] and a[4]==b[4] for a,b in zip(hooks,previous)),
            "exact eight-window atomic replacement/provenance required")
        def operands(rows):
            return [dict(instruction_offset=r.instruction_offset,instruction_bytes=r.instruction_bytes,
                offset=r.offset,kind=r.kind,role=r.role,value=r.value) for r in rows]
        def blocks(rows):
            return [dict(role=role,parent_start_va=lo,parent_end_va=hi,parent_sha256=digest,
                clone_start_va=start,clone_end_va=end) for role,lo,hi,digest,start,end in rows]
        meta=parent.metadata()
        metadata=dict(schema='clash95_battle_profile_adjacent_unit_v2',profile=profile,resolution=resolution,
            original_sha256=BASE_SHA256,parent_candidate_sha256=_sha(context.parent),
            relayout_parent_sha256=_sha(context.relayout_parent),canonical_probe_sha256=_sha(context.canonical_probe.encode()),
            validation_stage=layout.validation_stage,source_hashes=meta['source_hashes']|
                {name:_sha(raw) for name,(raw,_) in snapshot.items()},
            parent_count_model_code_sha256=_sha(parent.model_emission.code),parent_count_adapters_code_sha256=_sha(parent.emission.code),
            parent_count_metadata_sha256=_sha(parent.metadata_json.encode()),parent_count_entry_code_sha256=_sha(entry_bundle.emission.code),
            model_va=model.base_va,model_bytes=len(model.code),model_sha256=_sha(model.code),
            code_va=adapters.base_va,code_bytes=len(adapters.code),code_sha256=_sha(adapters.code),
            count_entry_va=entry.base_va,count_entry_bytes=len(entry.code),count_entry_sha256=_sha(entry.code),
            helper_frame_bytes=784,helper_low_watermark=-44,helper_checked_interval_bytes=868,
            ancestor_row_capacity=16,new_ancestor_rows=0,new_helper_bytes=0,
            selected_body_sites=list(BODY_SITES),selected_site_numbers=list(range(7)),family_ids=dict(unit=1,count=4),
            model_entries=dict(model.entries),model_private_entries=dict(model.private_entries),
            model_body_return_receipts=model.body_receipts,adapter_body_return_receipts=adapters.body_receipts,
            model_source_blocks=blocks(model.source_blocks),
            model_transform_receipts=[dict(role=role,parent_start_va=lo,parent_end_va=hi,model_start_va=start,model_end_va=end,
                parent_sha256=before,model_sha256=after) for role,lo,hi,start,end,before,after in model.transform_receipts],
            adapter_source_blocks=[dict(native_va=va,model_start_va=lo,model_end_va=hi,model_block_sha256=digest,
                adapter_start_va=start,model_admit_return_pc=pc) for va,lo,hi,digest,start,pc in adapters.source_blocks],
            count_entry_source_blocks=blocks(entry.source_blocks),count_entry_prefix_receipt=entry.prefix_receipt,
            count_entry_private_clone_receipt=entry.private_clone_receipt,count_entry_guard_receipts=entry.guard_receipts,
            mapped_instruction_ranges=dict(model=model.source_blocks,adapters=adapters.source_blocks,count_entry=entry.source_blocks),
            whole_model_source_sha256=_sha(source.encode()),
            inherited_versioned_source_edit_inventory=[dict(old=old,new=new,count=count) for old,new,count in v2_ledger],
            count_motion_source_edit_inventory=[dict(old=old,new=new,count=count) for old,new,count in count_motion_ledger],
            final_caller=dict(start_va=CALLER_WINDOW[0],end_va=CALLER_WINDOW[1],sha256=CALLER_WINDOW[2],
                call_va=0x42ff9f,return_va=FINAL_RETURN,motion_source_va=MOTION_SOURCE,active_source_va=ACTIVE_SOURCE,
                branch_conditions='signed motion <0 and native EAX equals active moving-unit identity',highlow=CALLER_HIGHLOW),
            phase_windows=[dict(start_va=lo,end_va=hi,sha256=digest) for lo,hi,digest in PHASE_WINDOWS],
            phase_highlow=PHASE_HIGHLOW,phase_identity_policy=dict(early_unit_and_entry='captured ESI404',
                count='bounded CountS-16 saved Unit ESI',later_unit='bounded UnitS-28 unsigned<682 divisible31'),
            motion_receipts=dict(count_local_slot=376,signed_motion_slot=380,active_identity_slot=384,
                adjacent_sp_slot=388,existing_control_shadow_reused=True,
                after_thread='control_match; both current globals; phase witness; gated Count local; Thread/mutable/cached checks',
                historical_authority=False,native_words_or_globals_restored=False),
            count_live_dy_corrections_retained=True,count_saved_ebp_proof_retained=True,count_local_receipt_retained=True,
            count_local_checks_gated_family4=True,count_draw_only_return_va=NATIVE_RET,
            count_entry_natural_return_retained=True,count_entry_payload_executed=False,
            count_entry_self_record_coherence=dict(record_index='bounded captured ESI404',
                byte_offset='captured EDX420 equals31*n',record='captured EAX428 equals current WORLD+852+31*n',
                native_ecx_pop_slot_authority_verified=False,historical_callee_preservation_verified=False),
            selected_seven_model_emitted=True,seven_native_adapters_emitted=True,fresh_count_entry_emitted=True,
            predecessor_final_adjacent_native_compatible=False,
            overrides_predecessor_planned_hooks=[dict(va=va,old_bytes=raw.hex(),predecessor_target_va=target,
                predecessor_role=role,removed_highlow_rvas=list(removed)) for va,raw,target,role,removed in previous],
            prospective_atomic_override_count=8,atomic_overrides_installed=False,
            planned_native_windows=[dict(va=va,rva=va-0x400000,file_offset=clip.file_offset(original,va,len(raw)),
                old_bytes=raw.hex(),new_bytes=(b'\xe8'+struct.pack('<i',target-va-5)+b'\x90'*(len(raw)-5)).hex(),
                target_va=target,role=role,removed_highlow_rvas=list(removed),group='battle_profile_adjacent_unit_v2_preparation')
                for va,raw,target,role,removed in hooks],
            model_operand_inventory=operands(model_inventory),operand_inventory=operands(adapter_inventory),
            count_entry_operand_inventory=operands(entry_inventory),
            prefix_rx_remaining_bytes=layout.rx.va+layout.rx.size-entry.base_va-len(entry.code),
            unchanged_rx_reservation_bytes=layout.rx.size,writes_owner_state=False,writes_descriptor=False,
            writes_headers=False,writes_pixels=False,writes_native_stack=False,writes_motion_globals=False,
            preparation_only=True,installed_hooks=[],provider_records_emitted=0,
            limitations=[
                'Eight prospective overrides form one uninstalled Unit5/Count2/Count-entry successor; every predecessor source and byte remains frozen.',
                'Final42FFA4 requires the exact current signed-motion source, matching saved Unit EBP and the phase-specific active identity; ordinary Tile/Adjacent ancestry is unchanged.',
                'Current global equality restricts admission and does not prove historical call-time immutability or complete final-caller compatibility.',
                'Count remains draw-only42F95B; non-draw callers and WORLD+821 sentinel authority remain unsupported.',
                'New Count-entry self-record/EDX coherence does not establish native ECX/pop-slot authority or historical callee register preservation.',
                'The complete source model, intrinsic admission guards and scalar tails are not original-body CPU parity, native mappings or callback ABI/lifetime evidence.',
                'Live Thread RET/ESP cannot be checked before a corrupted return; paired controls/locals, transient writes and cross-thread mutation remain unproved.',
                'Numeric helper bounds, unchanged784B and16rows and RX bounds establish no native stack or whole-chain capacity.',
                'Native providers/RLE ownership, early cancellation, post-normal-return gates, primitive/line successors, clipping, camera/input/animation/presentation/dialog/results/quit and atomic installation remain required.',
                'No candidate, game/debugger runtime, visual composition, manual input, endurance, release-cell or stable promotion is supplied.',
            ],**{name:False for name in FALSE_CLAIMS})
        _require(metadata['prefix_rx_remaining_bytes']>=0,"atomic final prefix exceeds unchanged RX reservation")
    _unchanged(snapshot)
    return AdjacentUnitV2Bundle(adapters,model,entry,parent,adapter_inventory,model_inventory,entry_inventory,
        json.dumps(metadata,sort_keys=True,separators=(',',':'),allow_nan=False))

def _production_factory():
    from hashlib import sha256 as digest
    from pathlib import Path as SourcePath
    from types import ModuleType as SourceModule
    from uuid import uuid4 as unique_name
    from sys import modules as registry
    rejection=ValueError;path=SourcePath(__file__).absolute();root=path.parents[2]
    if path!=root/'src/patcher/battle_profile_adjacent_unit_v2.py':raise rejection('canonical Adjacent Unit V2 producer required')
    def read_source(target):
        if target!=root/'src/patcher/battle_profile_adjacent_unit_v2.py' or target.resolve(strict=True)!=target:
            raise rejection('canonical Adjacent Unit V2 source required')
        for item in (target,*target.parents):
            row=item.lstat()
            if item.is_symlink() or getattr(row,'st_file_attributes',0)&0x400:raise rejection('Adjacent Unit V2 source reparse forbidden')
        before=target.stat()
        if not 0<before.st_size<=2*1024*1024:raise rejection('bounded Adjacent Unit V2 source required')
        with target.open('rb') as stream:raw=stream.read(2*1024*1024+1)
        after=target.stat();stamp=lambda r:(r.st_dev,r.st_ino,r.st_size,r.st_mtime_ns,getattr(r,'st_file_attributes',0))
        if stamp(before)!=stamp(after) or len(raw)!=after.st_size:raise rejection('Adjacent Unit V2 source changed while read')
        return raw,stamp(after)
    raw,receipt=read_source(path);name='_battle_adjacent_unit_v2_issuer_'+unique_name().hex
    module=SourceModule(name);module.__file__=str(path);module.__loaded_source_sha256__=digest(raw).hexdigest()
    module.__canonical_adjacent_unit_v2_issuer__=True
    if registry.setdefault(name,module) is not module:raise rejection('Adjacent Unit V2 issuer namespace occupied')
    try:exec(compile(raw,str(path),'exec'),module.__dict__);issuer=module.__dict__['_issue']
    finally:
        replaced=registry.get(name) is not module
        if registry.get(name) is module:del registry[name]
        if replaced:raise rejection('Adjacent Unit V2 issuer namespace changed')
    if read_source(path)!=(raw,receipt):raise rejection('Adjacent Unit V2 source changed during capture')
    def dispatch(original,profile,resolution):
        if read_source(path)!=(raw,receipt):raise rejection('captured Adjacent Unit V2 source differs')
        try:return issuer(original,profile,resolution)
        finally:
            if read_source(path)!=(raw,receipt):raise rejection('Adjacent Unit V2 source changed during dispatch')
    return dispatch

if not globals().get('__canonical_adjacent_unit_v2_issuer__',False):
    emit_adjacent_unit_v2=_production_factory()
