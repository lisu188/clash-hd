"""Uninstalled Count-only successor with the genuine live-DY EBP contract.

The earlier content adapters retain an incompatible inherited-live-EBP Count
assumption and stay frozen. This version overrides only their two planned Count
hooks. Saved Count EBP still proves Unit ancestry; live EBP proves neighbor DY.
Source/model preparation is not native execution, installation or acceptance.
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
SOURCE = "src/patcher/battle_profile_count_body_v2.py"
ENTRY = "src/patcher/battle_profile_count_entry.py"
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
    "count_body_hooks_installed", "count_entry_record_guard_installed",
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
def _entry_module(raw):
    _require(type(raw) is bytes and _sha(raw) == ENTRY_SHA256, "frozen Count entry producer differs")
    name = "_count_body_v2_entry_"+uuid.uuid4().hex
    module = types.ModuleType(name); module.__file__ = str(ROOT/ENTRY)
    module.__loaded_source_sha256__ = ENTRY_SHA256; module.__canonical_count_entry_issuer__ = True
    _require(sys.modules.setdefault(name,module) is module,"Count body V2 namespace occupied")
    try:
        exec(compile(raw,module.__file__,"exec"),module.__dict__)
        yield module
    finally:
        replaced = sys.modules.get(name) is not module
        if sys.modules.get(name) is module: del sys.modules[name]
        _require(not replaced,"Count body V2 namespace changed")

def _snapshot():
    entry = _read(ROOT/ENTRY)
    with _entry_module(entry[0]) as producer: result = producer._snapshot()
    own = _read(ROOT/SOURCE)
    _require(result[ENTRY] == entry and globals().get("__loaded_source_sha256__") == _sha(own[0]),
             "private unchanged Count body V2 source graph required")
    return result | {SOURCE:own}

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
class CountBodyModelEmission:
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
class CountBodyV2Emission:
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
class CountBodyV2Bundle:
    emission:CountBodyV2Emission
    model_emission:CountBodyModelEmission
    count_entry_bundle:object
    operand_inventory:tuple
    model_operand_inventory:tuple
    metadata_json:str
    hook_sites:tuple=()
    removed_highlow_rvas:tuple=()
    def metadata(self): return json.loads(self.metadata_json)

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
    namespace.update(SITES=sites[-2:],NEIGHBORS=NEIGHBORS,CodeEmission=CountBodyModelEmission)
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

def _raw_model(layout,field,lease,content,count_entry,*,content_module,template_module,assembler_module,template_source):
    modal=_layout_values(layout,field,lease)
    base=(count_entry.base_va+len(count_entry.code)+15)&~15
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
                    'count_body_v2_internal:'+label))
            labels.append(dict(self.labels));return code
    isolated=types.SimpleNamespace(_Assembler=CompleteAssembler,Relocation=assembler_module.Relocation,
        absolute_relocation_offsets=assembler_module.absolute_relocation_offsets)
    out=namespace['_versioned_emit_code'](plan,lease,assembler_module=isolated)
    _require(len(labels)==1 and out.base_va==base,"one complete Count model label receipt required")
    owned=labels[0];bodies=[]
    for va in COUNT_SITES:
        entry=base+owned[f'site_{va:06x}'];payload=base+owned[f'site_{va:06x}.payload']
        rows=[r for r in out.relocations if r.purpose=='count_body_v2_internal:admit_body' and
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
    cursor=0;rows=[]
    while cursor<len(code):
        start=cursor;fields=[];opcode=code[cursor];cursor+=1;memory=False
        if opcode in (0x9c,0x9d,0x60,0x61,0xfc,0xc3,0x55,0x5d,0x4b):pass
        elif opcode==0xf3:
            _require(cursor<len(code) and code[cursor]==0xaf,"Count body REP dialect differs");cursor+=1
        elif 0xb8<=opcode<=0xbf or opcode==0xa9:fields.append((cursor,4,'immediate'));cursor+=4
        elif opcode in (0xe8,0xe9):fields.append((cursor,4,'relative'));cursor+=4
        elif opcode==0x0f:
            _require(cursor<len(code),"truncated Count body escape");sub=code[cursor];cursor+=1
            if sub==0x0b:pass
            elif 0x80<=sub<=0x8f:fields.append((cursor,4,'relative'));cursor+=4
            else:_require(sub in (0xb6,0xb7,0xbf),"Count body extended dialect differs");memory=True
        else:
            _require(opcode in (0x81,0x83,0x8b,0x89,0x88,0x3b,0x39,0x3a,0x85,0xf7,0xff,
                0x31,0x29,0x01,0xc1,0x6b,0x8d,0xd1),"unknown Count body opcode at "+hex(start));memory=True
        if memory:
            _require(cursor<len(code),"truncated Count body ModRM");modrm=code[cursor];cursor+=1;mode,rm=modrm>>6,modrm&7
            if mode!=3 and rm==4:
                _require(cursor<len(code),"truncated Count body SIB");sib=code[cursor];fields.append((cursor,1,'sib'));cursor+=1
                if mode==0 and sib&7==5:fields.append((cursor,4,'memory_address'));cursor+=4
            if mode==0 and rm==5:fields.append((cursor,4,'memory_address'));cursor+=4
            elif mode==1:fields.append((cursor,1,'displacement'));cursor+=1
            elif mode==2:fields.append((cursor,4,'displacement'));cursor+=4
            if opcode==0x81 or opcode==0xf7 and (modrm>>3)&7==0:fields.append((cursor,4,'immediate'));cursor+=4
            elif opcode in (0x83,0xc1,0x6b):fields.append((cursor,1,'immediate'));cursor+=1
        _require(start<cursor<=len(code),"truncated Count body instruction");rows.append((start,cursor,tuple(fields)))
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
    private=dict(content.private_entries);source_start=content.body_receipts[26][1]-content.base_va
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
    drop=(ladder_starts[0],ladder_starts[26])
    edits=((drop[0],drop[1],'drop_non_count_admissions'),(first,first+22,'first_live_dy'),
           (local_before,local_before,'count_local_snapshot'),(second,second+17,'shared_live_dy'),
           (local_after,local_after,'count_local_match'))
    _require(source_start<drop[0]<drop[1]<first<first+22<local_before<second<second+17<local_after<len(original),
        "ordered complete Count source transformations required")
    expected=bytearray();copied=[];replaced=[];new_fields=[];new_absolutes=[];receipts=[];cursor=source_start
    def append(raw):expected.extend(bytes.fromhex(raw))
    def u32(value):expected.extend(struct.pack('<I',value&0xffffffff))
    def new_relative(target,purpose):
        new_fields.append((len(expected),target,purpose));u32(0)
    def new_absolute(target,purpose):
        new_absolutes.append((len(expected),target,purpose));u32(target)
    def local_extent(role):
        append('8bbd');u32(208);append('81c7');u32(-28)
        append('f7c7030000000f85');new_relative(reject,'count_body_v2_internal:admit.reject')
        append('8b95');u32(228);append('89d181c1');u32(-0x10000)
        append('39cf0f82');new_relative(reject,'count_body_v2_internal:admit.reject')
        append('89f881c0');u32(4);append('0f82');new_relative(reject,'count_body_v2_internal:admit.reject')
        append('39d00f87');new_relative(reject,'count_body_v2_internal:admit.reject')
        for number,(low,high) in enumerate(protected):
            append('81ff');new_absolute(high,'protected Count local allocation end')
            append('0f83');above=len(expected);u32(0)
            append('81f8');new_absolute(low,'protected Count local allocation start')
            append('0f86');below=len(expected);u32(0)
            append('e9');new_relative(reject,'count_body_v2_internal:admit.reject')
            label='count_body_v2_internal:count.local.'+role+'.protected.'+str(number)
            target=('model',out.base_va+len(expected))
            new_fields.extend(((above,target,label),(below,target,label)))
    for lo,hi,role in edits:
        start=len(expected);expected.extend(original[cursor:lo]);copied.append((cursor,lo,start))
        replacement_start=len(expected)
        if role in ('count_local_snapshot','count_local_match'):
            local_extent('before' if role=='count_local_snapshot' else 'after')
            append('8b8700000000')
            if role=='count_local_snapshot':append('8985');u32(376)
            else:
                append('3b85');u32(376);append('0f85');new_relative(reject,'count_body_v2_internal:admit.reject')
        elif role!='drop_non_count_admissions':
            append('e8');new_relative('dy','count_body_v2_internal:count_expected_dy')
            append('81f8');u32(1);append('0f85');new_relative(reject,'count_body_v2_internal:admit.reject')
            if role=='first_live_dy':
                append('8b85');u32(408);append('39f80f85');new_relative(reject,'count_body_v2_internal:admit.reject')
                append('8bbd');u32(208)
            else:
                append('e9');new_relative(compare.target,'count_body_v2_internal:ebp.compare')
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
        helper_next.append((at,out.base_va+len(expected),'count_body_v2_internal:count.dy.next.'+str(number)))
    helper_reject=out.base_va+len(expected);append('b8');u32(0);append('c3')
    def mapped(old_va):
        old=old_va-content.base_va
        hits=[out.base_va+new+old-lo for lo,hi,new in copied if lo<=old<hi]
        hits += [out.base_va+new_lo for lo,hi,new_lo,new_hi,role in replaced if lo<hi and old==lo and role!='drop_non_count_admissions']
        _require(len(hits)==1,"source transfer escaped retained Count instruction ranges")
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
                    if label=='site_receipt.next.26':label='site_receipt.next.0'
                    if label=='site_receipt.next.27':label='site_receipt.next.1'
                    typed(at,'rel32',mapped(row.target),'count_body_v2_internal:'+label)
                else:
                    _require(row.target==dict(field.private_entries)['check_invocation'] and
                        row.purpose=='private current V2 complete content receipt' and original[row.offset-1]==0xe8,
                        "sole source external Count field CALL required")
                    typed(at,'rel32',row.target,row.purpose)
    for at,target,purpose in new_fields:
        resolved=helper if target=='dy' else target[1] if type(target) is tuple and target[0]=='model' else mapped(target)
        typed(at,'rel32',resolved,purpose)
    for at,target,purpose in new_absolutes:typed(at,'abs32',target,purpose)
    for at in (reject_one,reject_two):typed(at,'rel32',helper_reject,'count_body_v2_internal:count.dy.reject')
    for at,target,purpose in helper_next:typed(at,'rel32',target,purpose)
    # Four source-owned SITE scalar changes; they are never relocations.
    scalar_changes=[]
    for number,body in enumerate(content.body_receipts[26:]):
        lo=body[1]-content.base_va;hi=body[3]-content.base_va
        pattern=b'\xb8'+struct.pack('<I',26+number)+bytes.fromhex('8985c8000000')
        hits=[];cursor=lo
        while True:
            at=original.find(pattern,cursor,hi)
            if at<0:break
            hits.append(at+1);cursor=at+1
        _require(len(hits)==1,"one exact body SITE scalar required")
        for old in (hits[0],ladder_starts[26+number]+8):
            at=mapped(content.base_va+old)-out.base_va
            _require(at not in fields and struct.unpack_from('<I',expected,at)[0]==26+number,
                "authored Count SITE scalar differs")
            struct.pack_into('<I',expected,at,number);scalar_changes.append((old,at,26+number,number))
    for at,(kind,target,_) in fields.items():
        struct.pack_into('<I',expected,at,target if kind=='abs32' else (target-out.base_va-at-4)&0xffffffff)
    entries=tuple((f'site_{va:06x}',mapped(dict(content.entries)[f'site_{va:06x}'])) for va in COUNT_SITES)
    private_entries=tuple((name,mapped(va)) for name,va in content.private_entries)+(('count_expected_dy',helper),)
    bodies=tuple((row[0],*(mapped(va) for va in row[1:])) for row in content.body_receipts[26:])
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
    return _inventory(out,fields,internal_prefix='count_body_v2_internal:',external={
        'private current V2 complete content receipt':(0xe8,{dict(field.private_entries)['check_invocation']})})

def _model_block(model,number):
    _require(len(model.body_receipts)==2 and tuple(row[0] for row in model.body_receipts)==COUNT_SITES and
        tuple(dict(model.private_entries))==('capture_inputs','capture_stack','admit_body','fixed_receipt','unsafe_control',
            'finish_rejected','finish_valid','count_expected_dy'),"complete corrected Count model ABI required")
    va,entry,payload,pc,denied,fault,valid=model.body_receipts[number]
    end=model.body_receipts[number+1][1] if number==0 else dict(model.private_entries)['finish_rejected']
    lo,hi=entry-model.base_va,end-model.base_va;raw=model.code[lo:hi]
    _require(0<=lo<hi<=len(model.code) and entry<pc<payload<valid<fault<denied<end and
        raw[:11]==b'\x9c\x60\xfc\x81\xec'+struct.pack('<I',784)+b'\x89\xe5',"complete real Count model body receipt required")
    at=pc-model.base_va-4;rows=[r for r in model.relocations if r.offset==at]
    _require(len(rows)==1 and (rows[0].kind,rows[0].target,rows[0].purpose)==
        ('rel32',dict(model.private_entries)['admit_body'],'count_body_v2_internal:admit_body') and model.code[at-1]==0xe8,
        "actual corrected Count admission CALL required")
    return va,entry,payload,pc,denied,fault,valid,end,lo,hi,raw,at

def _raw_adapters(layout,field,model,*,assembler_module,template_source):
    _native_contract(template_source);base=(model.base_va+len(model.code)+15)&~15
    a=assembler_module._Assembler(base);parent=dict(model.private_entries);bodies=[];sources=[];hooks=[]
    def internal(at,label):struct.pack_into('<I',a.code,at,0);a.fixups.append((at,label))
    def transfer(target,purpose,opcode='e9'):
        a.emit(opcode);at=len(a.code);a.relocations.append(assembler_module.Relocation(at,'rel32',target,purpose));a.u32(target-base-at-4)
    for number,(va,window) in enumerate(zip(COUNT_SITES,COUNT_WINDOWS)):
        _,old_entry,payload,pc,denied,fault,valid,end,lo,hi,raw,admit_at=_model_block(model,number)
        start,entry=len(a.code),base+len(a.code);dispatch=f'finish_{va:06x}';guard=f'admit_{va:06x}'
        a.label(f'site_{va:06x}');a.emit(raw.hex())
        for row in model.relocations:
            if not lo<=row.offset<hi:continue
            _require(row.offset+4<=hi,"Count adapter operand crosses source block");at=start+row.offset-lo
            if row.kind=='abs32':
                a.relocations.append(assembler_module.Relocation(at,'abs32',row.target,'count_body_adapter_source_absolute:'+row.purpose))
            elif row.offset==admit_at:internal(at,guard)
            elif old_entry<=row.target<end:
                _require(row.kind=='rel32',"Count adapter internal relative required")
                target=entry+row.target-old_entry;struct.pack_into('<i',a.code,at,target-base-at-4)
                a.relocations.append(assembler_module.Relocation(at,'rel32',target,'count_body_adapter_internal:source_block'))
            elif row.target in (parent['finish_rejected'],parent['finish_valid']):
                _require(row.kind=='rel32' and a.code[at-1]==0xe9,"outer corrected Count finish JMP required");internal(at,dispatch)
            else:
                _require(row.kind=='rel32' and row.target==parent['capture_inputs'] and a.code[at-1]==0xe8,
                    "unexpected external corrected Count body transfer")
                struct.pack_into('<i',a.code,at,row.target-base-at-4)
                a.relocations.append(assembler_module.Relocation(at,'rel32',row.target,'count_body_adapter_capture_inputs'))
        a.label(dispatch)
        a.emit('83fa01');a.branch('0f85','unsafe_control');a.emit('39ec');a.branch('0f85','unsafe_control')
        a.emit('8b95');a.u32(820);a.emit('81fa');a.absolute(va+5,'natural corrected Count body CALL return')
        a.branch('0f85','unsafe_control')
        a.emit('8985' if number==0 else '8885');a.u32(808 if number==0 else 804)
        a.emit('81c4');a.u32(784);a.emit('619d8d642404')
        a.emit(('83f9ff' if number==0 else '3a5702'));transfer(va+len(window),'native_count_body_resume')
        a.label(guard);a.emit('8d4c240439cd');a.branch('0f85','unsafe_control');a.emit('8b042481f8')
        a.absolute(entry+pc-old_entry,'actual corrected Count adapter admission CALL return')
        a.branch('0f85','unsafe_control');transfer(parent['admit_body'],'native_corrected_count_admission_parent')
        bodies.append((va,entry,entry+payload-old_entry,entry+pc-old_entry,entry+denied-old_entry,
            entry+fault-old_entry,entry+valid-old_entry,base+a.labels[dispatch],va+len(window)))
        sources.append((va,old_entry,end,_sha(raw),entry,pc));hooks.append((va,window,entry,'count_body_v2_operand',()))
    a.label('unsafe_control');a.emit('0f0b');code=bytes(a.finish())
    for at,label in a.fixups:
        a.relocations.append(assembler_module.Relocation(at,'rel32',base+a.labels[label],'count_body_adapter_internal:'+label))
    _require(base+len(code)<=layout.rx.va+layout.rx.size,"Count body adapters exceed fresh RX reservation")
    out=CountBodyV2Emission(base,layout.rw.va,code,tuple((f'site_{va:06x}',base+a.labels[f'site_{va:06x}']) for va in COUNT_SITES),
        tuple(a.relocations),field.width,field.height,(('unsafe_control',base+a.labels['unsafe_control']),)+
        tuple((f'admit_{va:06x}',base+a.labels[f'admit_{va:06x}']) for va in COUNT_SITES),tuple(bodies),tuple(sources),tuple(hooks))
    assembler_module.absolute_relocation_offsets(out);_operand_inventory(out,model,template_source=template_source)
    return out

def _adapter_contract(out,model,template_source):
    _native_contract(template_source);parent=dict(model.private_entries)
    expected=bytearray();fields={};pending=[];entries=[];guards=[];bodies=[];sources=[];hooks=[]
    def typed(at,kind,target,purpose):
        _require(at not in fields,"duplicate authored corrected Count adapter operand");fields[at]=(kind,target,purpose)
    def emit(raw):expected.extend(bytes.fromhex(raw))
    def u32(value):expected.extend(struct.pack('<I',value&0xffffffff))
    def absolute(target,purpose):typed(len(expected),'abs32',target,purpose);u32(target)
    def relative(target,purpose):typed(len(expected),'rel32',target,purpose);u32(0)
    def unsafe(opcode):emit(opcode);pending.append(len(expected));u32(0)
    for number,(va,window) in enumerate(zip(COUNT_SITES,COUNT_WINDOWS)):
        _,old_entry,payload,pc,denied,fault,valid,end,lo,hi,raw,admit_at=_model_block(model,number)
        start,entry=len(expected),out.base_va+len(expected);dispatch=entry+len(raw);expected.extend(raw)
        admission=None;finishes=[]
        for row in model.relocations:
            if not lo<=row.offset<hi:continue
            _require(row.offset+4<=hi,"authored corrected Count operand crosses source boundary");at=start+row.offset-lo
            if row.kind=='abs32':typed(at,'abs32',row.target,'count_body_adapter_source_absolute:'+row.purpose)
            elif row.offset==admit_at:
                _require(row.kind=='rel32' and row.target==parent['admit_body'] and raw[row.offset-lo-1]==0xe8,
                    "authored corrected Count admission CALL differs");admission=at
            elif old_entry<=row.target<end:
                _require(row.kind=='rel32',"authored corrected Count internal relative required")
                typed(at,'rel32',entry+row.target-old_entry,'count_body_adapter_internal:source_block')
            elif row.target in (parent['finish_rejected'],parent['finish_valid']):
                _require(row.kind=='rel32' and raw[row.offset-lo-1]==0xe9,"authored corrected Count finish JMP differs");finishes.append(at)
            else:
                _require(row.kind=='rel32' and row.target==parent['capture_inputs'] and raw[row.offset-lo-1]==0xe8,
                    "authored corrected Count capture CALL differs");typed(at,'rel32',row.target,'count_body_adapter_capture_inputs')
        emit('83fa01');unsafe('0f85');emit('39ec');unsafe('0f85');emit('8b95');u32(820)
        emit('81fa');absolute(va+5,'natural corrected Count body CALL return');unsafe('0f85')
        emit('8985' if number==0 else '8885');u32(808 if number==0 else 804)
        emit('81c4');u32(784);emit('619d8d642404');emit('83f9ff' if number==0 else '3a5702')
        emit('e9');relative(va+len(window),'native_count_body_resume')
        guard=out.base_va+len(expected);emit('8d4c240439cd');unsafe('0f85');emit('8b042481f8')
        absolute(entry+pc-old_entry,'actual corrected Count adapter admission CALL return');unsafe('0f85')
        emit('e9');relative(parent['admit_body'],'native_corrected_count_admission_parent')
        _require(admission is not None and finishes,"complete corrected Count admission/finish required")
        typed(admission,'rel32',guard,f'count_body_adapter_internal:admit_{va:06x}')
        for at in finishes:typed(at,'rel32',dispatch,f'count_body_adapter_internal:finish_{va:06x}')
        entries.append((f'site_{va:06x}',entry));guards.append((f'admit_{va:06x}',guard))
        bodies.append((va,entry,entry+payload-old_entry,entry+pc-old_entry,entry+denied-old_entry,
            entry+fault-old_entry,entry+valid-old_entry,dispatch,va+len(window)))
        sources.append((va,old_entry,end,_sha(raw),entry,pc));hooks.append((va,window,entry,'count_body_v2_operand',()))
    terminal=out.base_va+len(expected);emit('0f0b')
    for at in pending:typed(at,'rel32',terminal,'count_body_adapter_internal:unsafe_control')
    for at,(kind,target,_) in fields.items():
        struct.pack_into('<I',expected,at,target if kind=='abs32' else (target-out.base_va-at-4)&0xffffffff)
    _require(out.code==bytes(expected) and out.entries==tuple(entries) and
        out.private_entries==(('unsafe_control',terminal),)+tuple(guards) and out.body_receipts==tuple(bodies) and
        out.source_blocks==tuple(sources) and out.planned_hooks==tuple(hooks),"complete independent Count adapter bytes/receipts differ")
    return fields

def _operand_inventory(out,model,*,template_source=None):
    if template_source is None:template_source=_read(ROOT/TEMPLATE)[0]
    fields=_adapter_contract(out,model,template_source);parent=dict(model.private_entries)
    return _inventory(out,fields,internal_prefix='count_body_adapter_internal:',external={
        'count_body_adapter_capture_inputs':(0xe8,{parent['capture_inputs']}),
        'native_corrected_count_admission_parent':(0xe9,{parent['admit_body']}),
        'native_count_body_resume':(0xe9,{va+len(raw) for va,raw in zip(COUNT_SITES,COUNT_WINDOWS)})})

def _emit_code(layout,life,route,field,lease,content,loss,joined_field,tile,content_replay,count_entry,*,
               count_entry_module,count_entry_kwargs,content_module,template_module,assembler_module,template_source):
    expected=count_entry_module._emit_code(layout,life,route,field,lease,content,loss,joined_field,tile,content_replay,
        **count_entry_kwargs)
    _require(_identity(count_entry)==_identity(expected),"complete canonical Count entry graph/receipts required")
    model=_raw_model(layout,field,lease,content,count_entry,content_module=content_module,template_module=template_module,
        assembler_module=assembler_module,template_source=template_source)
    adapters=_raw_adapters(layout,field,model,assembler_module=assembler_module,template_source=template_source)
    return model,adapters

def _authenticate_native(original,relayout_parent,clip,pe,*,template_source=None):
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

def _issue(original,profile,resolution):
    _require(type(original) is bytes and _sha(original)==BASE_SHA256,"exact Count body V2 original required")
    snapshot=_snapshot()
    with _entry_module(snapshot[ENTRY][0]) as producer:
        parent=producer._issue(original,profile,resolution)
        replay_bundle=parent.content_replay_bundle;tile_bundle=replay_bundle.tile_replay_bundle
        loss_bundle=tile_bundle.field_loss_bundle;content_bundle=loss_bundle.content_bundle
        lease_bundle=content_bundle.lease_bundle;field_bundle=lease_bundle.field_bundle
        context=field_bundle.routing_bundle.lifecycle_bundle.allocation_context;layout=context.layout
        with producer._replay_module(snapshot[REPLAY][0]) as replay_module:
            with replay_module._tile_module(snapshot[TILE][0]) as tile_module:
                with tile_module._loss_module(snapshot[LOSS][0]) as loss_module:
                    with loss_module._content_module(snapshot[CONTENT][0]) as content_module:
                        with content_module._modules(snapshot) as modules:
                            clip=modules[CLIP];template=modules[TEMPLATE]
                            _authenticate_native(original,context.relayout_parent,clip,modules['src/patcher/pe_extension.py'],
                                template_source=snapshot[TEMPLATE][0])
                            model=_raw_model(layout,field_bundle.emission,lease_bundle.emission,content_bundle.emission,
                                parent.emission,content_module=content_module,template_module=template,assembler_module=clip,
                                template_source=snapshot[TEMPLATE][0])
                            adapters=_raw_adapters(layout,field_bundle.emission,model,assembler_module=clip,
                                template_source=snapshot[TEMPLATE][0])
                            transformed,versioned_ledger,count_ledger,_=_whole_model_source(content_module,snapshot[TEMPLATE][0],template)
        model_inventory=_model_operand_inventory(model,content_bundle.emission,field_bundle.emission,
            template_source=snapshot[TEMPLATE][0])
        inventory=_operand_inventory(adapters,model,template_source=snapshot[TEMPLATE][0])
        previous=tuple(row for row in replay_bundle.emission.planned_hooks if row[0] in COUNT_SITES)
        _require(tuple(row[0] for row in previous)==COUNT_SITES and tuple(row[1] for row in previous)==COUNT_WINDOWS and
            all(row[4]==() for row in previous),"exact two predecessor Count-only planned overrides required")
        meta=parent.metadata()
        def operands(rows):
            return [dict(instruction_offset=r.instruction_offset,instruction_bytes=r.instruction_bytes,offset=r.offset,
                         kind=r.kind,role=r.role,value=r.value) for r in rows]
        metadata=dict(schema='clash95_battle_profile_count_body_v2',profile=profile,resolution=resolution,
            original_sha256=BASE_SHA256,parent_candidate_sha256=_sha(context.parent),
            relayout_parent_sha256=_sha(context.relayout_parent),canonical_probe_sha256=_sha(context.canonical_probe.encode()),
            validation_stage=layout.validation_stage,source_hashes=meta['source_hashes']|
                {name:_sha(raw) for name,(raw,_) in snapshot.items()},
            count_entry_code_sha256=_sha(parent.emission.code),count_entry_metadata_sha256=_sha(parent.metadata_json.encode()),
            content_replay_code_sha256=_sha(replay_bundle.emission.code),
            joined_field_code_sha256=_sha(loss_bundle.joined_field_emission.code),
            content_code_sha256=_sha(content_bundle.emission.code),
            field_tile_return_receipts=meta['field_tile_return_receipts'],
            lease_field_return_receipts=meta['lease_field_return_receipts'],
            field_loss_post_tile_call_patches=meta['field_loss_post_tile_call_patches'],
            code_va=adapters.base_va,code_bytes=len(adapters.code),code_sha256=_sha(adapters.code),
            model_va=model.base_va,model_bytes=len(model.code),model_sha256=_sha(model.code),
            helper_frame_bytes=784,helper_low_watermark=-44,helper_checked_interval_bytes=868,
            ancestor_row_capacity=16,new_ancestor_rows=0,
            model_entries=dict(model.entries),model_private_entries=dict(model.private_entries),
            model_body_return_receipts=model.body_receipts,adapter_body_return_receipts=adapters.body_receipts,
            model_source_blocks=[dict(role=role,parent_start_va=lo,parent_end_va=hi,parent_sha256=digest,
                model_start_va=start,model_end_va=end) for role,lo,hi,digest,start,end in model.source_blocks],
            model_transform_receipts=[dict(role=role,parent_start_va=lo,parent_end_va=hi,model_start_va=start,
                model_end_va=end,parent_sha256=before,model_sha256=after)
                for role,lo,hi,start,end,before,after in model.transform_receipts],
            adapter_source_blocks=[dict(native_va=va,model_start_va=lo,model_end_va=hi,model_block_sha256=digest,
                adapter_start_va=start,model_admit_return_pc=pc) for va,lo,hi,digest,start,pc in adapters.source_blocks],
            whole_model_source_sha256=_sha(transformed.encode()),
            inherited_versioned_source_edit_inventory=[dict(old=old,new=new,count=count) for old,new,count in versioned_ledger],
            count_source_edit_inventory=[dict(old=old,new=new,count=count) for old,new,count in count_ledger],
            count_only_sites=list(COUNT_SITES),count_only_site_numbers=[0,1],count_family_number=4,
            count_live_ebp_source_policy_corrected=True,count_body_adapters_emitted=True,
            live_ebp_policy='captured native EAX428 is eight-aligned unsigned<64; captured EBP408 equals pinned neighbor DY at that index',
            saved_ebp_policy='unchanged source CountS-24 equals UnitS-12; all Unit/Adjacent/Tile/Field/Lease ancestry receipts remain required',
            count_local_receipt=dict(native_offset_from_count_sp=-28,relative_to_helper_ebp=824,bytes=4,
                snapshot_slot=376,existing_control_shadow_reused=True,new_ancestor_rows=0,new_helper_bytes=0,
                pointer_authority='authenticated NATIVE_S Count entry SP minus28; never captured native ESP',
                before_read='four-byte alignment/root/carry and complete RX/RW/inherited allocation exclusion',
                after_thread='control_match, then repeated four-byte bounds and Count-local equality before Thread-result/mutable-descriptor/cached checks',
                restores_native_local=False),
            dy_helper_va=dict(model.private_entries)['count_expected_dy'],
            dy_helper_abi=dict(status='EAX0/1',expected_dy='EDI',callbacks=0,payload_reads=0,new_local_bytes=0),
            native_count_span=dict(start_va=0x426ef0,end_va=0x426f75,bytes=133,sha256=COUNT_SHA256,
                highlow=[dict(va=va,target_va=target) for va,target in COUNT_HIGHLOW]),
            native_neighbor_table=dict(va=0x514500,bytes=64,sha256=TABLE_SHA256),
            preserves_original_count_highlow=True,removed_native_highlow_rvas=[],
            predecessor_count_body_native_compatible=False,
            predecessor_count_body_blocker='frozen ContentV2 and ContentReplay Count guards require inherited live Unit EBP; genuine Count uses neighbor DY in live EBP',
            overrides_predecessor_planned_hooks=[dict(va=va,old_bytes=raw.hex(),predecessor_target_va=target,
                predecessor_role=role,removed_highlow_rvas=list(removed)) for va,raw,target,role,removed in previous],
            planned_native_windows=[dict(va=va,rva=va-0x400000,file_offset=clip.file_offset(original,va,len(raw)),
                old_bytes=raw.hex(),new_bytes=(b'\xe8'+struct.pack('<i',target-va-5)+b'\x90'*(len(raw)-5)).hex(),
                target_va=target,role=role,removed_highlow_rvas=list(removed),group='battle_profile_count_body_v2_preparation')
                for va,raw,target,role,removed in adapters.planned_hooks],
            model_operand_inventory=operands(model_inventory),operand_inventory=operands(inventory),
            unsafe_va=dict(adapters.private_entries)['unsafe_control'],model_unsafe_va=dict(model.private_entries)['unsafe_control'],
            failure_behavior='denial/status2/invalid loop DY/control stops UD2; no native epilogue, descriptor loss write or fake result',
            writes_owner_state=False,writes_descriptor=False,writes_headers=False,writes_pixels=False,
            preparation_only=True,installed_hooks=[],provider_records_emitted=0,
            prefix_rx_remaining_bytes=layout.rx.va+layout.rx.size-adapters.base_va-len(adapters.code),
            limitations=[
                'Only two Count planned body hooks are superseded; every frozen predecessor byte and fixture remains unchanged.',
                'Corrected source/model DY admission and native ECX/DL replay are uninstalled preparation, not genuine Count execution or native parity.',
                'Count local X is retained in the existing shadowed X376 authority slot across Thread; rejection never restores or writes that native local.',
                'Count remains draw-only42F95B;426F95/431D7A and WORLD+821 sentinel authority remain unsupported.',
                'Native mapping/callback ABI/receiver/arguments/lifetime and whole-chain capacity remain unproved.',
                'Live Thread RET/ESP cannot be checked before a corrupted callback return; paired pre-admission controls/locals, transient writes and cross-thread mutation remain unproved.',
                'Static neighbor-table authentication and source constants establish no live table or provider-data immutability.',
                'Post-normal-return gates, primitive/line successors, provider/RLE cancellation, clipping, camera/input/animation/presentation/dialog/results/quit and atomic installation remain required.',
            ],**{name:False for name in FALSE_CLAIMS})
    _unchanged(snapshot)
    return CountBodyV2Bundle(adapters,model,parent,inventory,model_inventory,
        json.dumps(metadata,sort_keys=True,separators=(',',':'),allow_nan=False))

def _production_factory():
    from hashlib import sha256 as digest
    from pathlib import Path as SourcePath
    from types import ModuleType as SourceModule
    from uuid import uuid4 as unique_name
    from sys import modules as registry
    rejection=ValueError;path=SourcePath(__file__).absolute();root=path.parents[2]
    if path!=root/'src/patcher/battle_profile_count_body_v2.py':raise rejection('canonical Count body V2 producer required')
    def read_source(target):
        if target!=root/'src/patcher/battle_profile_count_body_v2.py' or target.resolve(strict=True)!=target:
            raise rejection('canonical Count body V2 source required')
        for item in (target,*target.parents):
            row=item.lstat()
            if item.is_symlink() or getattr(row,'st_file_attributes',0)&0x400:raise rejection('Count body V2 source reparse forbidden')
        before=target.stat()
        if not 0<before.st_size<=2*1024*1024:raise rejection('bounded Count body V2 source required')
        with target.open('rb') as stream:raw=stream.read(2*1024*1024+1)
        after=target.stat();stamp=lambda r:(r.st_dev,r.st_ino,r.st_size,r.st_mtime_ns,getattr(r,'st_file_attributes',0))
        if stamp(before)!=stamp(after) or len(raw)!=after.st_size:raise rejection('Count body V2 source changed while read')
        return raw,stamp(after)
    raw,receipt=read_source(path);name='_battle_count_body_v2_issuer_'+unique_name().hex
    module=SourceModule(name);module.__file__=str(path);module.__loaded_source_sha256__=digest(raw).hexdigest()
    module.__canonical_count_body_v2_issuer__=True
    if registry.setdefault(name,module) is not module:raise rejection('Count body V2 issuer namespace occupied')
    try:exec(compile(raw,str(path),'exec'),module.__dict__);issuer=module.__dict__['_issue']
    finally:
        replaced=registry.get(name) is not module
        if registry.get(name) is module:del registry[name]
        if replaced:raise rejection('Count body V2 issuer namespace changed')
    if read_source(path)!=(raw,receipt):raise rejection('Count body V2 source changed during capture')
    def dispatch(original,profile,resolution):
        if read_source(path)!=(raw,receipt):raise rejection('captured Count body V2 source differs')
        try:return issuer(original,profile,resolution)
        finally:
            if read_source(path)!=(raw,receipt):raise rejection('Count body V2 source changed during dispatch')
    return dispatch

if not globals().get('__canonical_count_body_v2_issuer__',False):
    emit_count_body_v2=_production_factory()
