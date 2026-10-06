"""Uninstalled fresh content successor; the lease dependency must be frozen.

Body helpers retain EAX value/EDX status, with no native instruction replay,
provider authority, cancellation, installation or runtime acceptance.
"""
from __future__ import annotations
import ast
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
import sys
import types
import uuid

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "src/patcher/battle_profile_content_v2.py"
TEMPLATE = "src/patcher/battle_profile_content.py"
LEASE = "src/patcher/battle_profile_stack_lease_v2.py"
FIELD = "src/patcher/battle_profile_field_v3.py"
CLIP = "src/patcher/partial_tile_clip.py"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
# Reviewed final source/model dependency; this grants no installation or runtime.
LEASE_V2_SHA256 = "f24b7c1cb0756ce1bdcbb1e4f5a24cd2fb139aacb6feb627cad8a7e636408d19"
# Root-authorized exact source for explicit synthetic reconstruction only.
MODEL_LEASE_SHA256 = "f24b7c1cb0756ce1bdcbb1e4f5a24cd2fb139aacb6feb627cad8a7e636408d19"
PINNED_SOURCES = {
    "src/patcher/battle_profile_context_v2.py": "d0a8b27ae4d07b290a449c1c875d4b574d329d2a9ac6b1397a2753f7d10ee5c9",
    "src/patcher/battle_profile_context.py": "be3bbca018c415895ba7e79e64862512f330297fb56b4d8321f8f6d378c38500",
    "src/patcher/battle_profile_lifecycle.py": "dccb907b09d002691cad679219942ac5a8ffcb2798af4c96b0b1768dbd9e9f44",
    "src/patcher/battle_profile_lifecycle_v2.py": "cbc91857e7fb914be0e27654bd59c7ed4cec145c118d9ebe3aa8163b55e78199",
    "src/patcher/battle_profile_routing.py": "838d371bf837ab0098420e5589abc07d446a22bd6daa25ecab683e4725e25972",
    "src/patcher/battle_profile_routing_v2.py": "77be6897c0cfab78237a6d85dd678e772a0b34c81787e11736950f4cb4700b1c",
    "src/patcher/battle_profile_field.py": "c329460fc7289d11ac10ddc33d26eb5ad158169ca976fee41ccd32fba6d97c88",
    "src/patcher/battle_profile_field_v2.py": "673a2170f77dc143a1d62745bf5879f23163e9cbcffa3f5549123c4cc81f8cbf",
    FIELD: "c369525f34308ab5fde48b9c334d45a90845aded3ab26abda5a08b5ff35d6d3a",
    "src/patcher/battle_profile_stack_lease.py": "47d6ad4931aef39b58919dff4b22b41cce76b0abf39267237a704471331f834c",
    TEMPLATE: "52f9ac7f8d52cb40638e91868910d6487cea083be0cc32e622d8fe4a3f8cf3d7",
    CLIP: "92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad",
    "src/patcher/pe_extension.py": "4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27",
    "src/patcher/framed_viewport.py": "1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42",
    "src/patcher/framed_battle_viewport.py": "8673e36bd04ded2afc8cc3b9d7ff2fed4c48dae891fe289509b44a9070c23bc6",
    "src/patcher/framed_battle_coordinates.py": "b67900d7399e0ce807d88a261c97942598beebfc28e2d78774cd109098f95142",
    "src/patcher/framed_battle_field.py": "f690865e615db65d02e8c59b5c43e0cfbaa1e371dd6502441d16e0d270a7196d",
    "src/patcher/framed_modal_canvas.py": "567b025520184a99f1f4f44b23a879ef9c729dcf2917dfa03a277c018cb20054",
    "src/patcher/framed_battle_hud.py": "3a6cb61a2ec2fcd0fa9c52c09a96e11a9a2d9f75cac6e3a2e826d5caa98a3ee3",
}
MODULE_ORDER = (
    "framed_viewport", "pe_extension", "partial_tile_clip", "framed_battle_viewport",
    "framed_battle_coordinates", "framed_battle_field", "framed_modal_canvas", "framed_battle_hud",
    "battle_profile_context", "battle_profile_context_v2", "battle_profile_lifecycle",
    "battle_profile_lifecycle_v2", "battle_profile_routing", "battle_profile_routing_v2",
    "battle_profile_field", "battle_profile_field_v2", "battle_profile_field_v3",
    "battle_profile_stack_lease", "battle_profile_stack_lease_v2", "battle_profile_content",
)
HELPER_BYTES, FIELD_BYTES, LEASE_BYTES = 784, 1280, 192
AUTHORITY_LOCALS = tuple(range(200, 236, 4)) + tuple(range(240, 392, 4))
INPUT_SLOTS = tuple(range(400, 436, 4))
CONTROL_SLOTS = AUTHORITY_LOCALS + INPUT_SLOTS + tuple(range(HELPER_BYTES, HELPER_BYTES+40, 4)) + (-4,)
CONTROL_SHADOW, MUTABLE_SHADOW, THREAD_RESULT = 476, 744, 768
MUTABLE_DESCRIPTOR_SLOTS = (44, 48, 52, 56, 60, 64)
FALSE_CLAIMS = (
    "installed", "battle_installed", "expanded_battle_installed", "installation_ready",
    "source_candidate_installed", "native_executed", "game_executed", "runtime_executed",
    "runtime_verified", "manual_input_proof", "manual_input_verified", "promotion_ready",
    "release_accepted", "provider_validity_verified", "provider_capacity_verified",
    "provider_lifetime_verified", "native_receiver_validity_verified", "native_argument_validity_verified",
    "native_callback_abi_verified", "native_stack_capacity_verified", "whole_chain_capacity_verified",
    "native_body_callsite_admission_installed", "native_instruction_replay", "native_continuation_cancellation",
    "count_entry_record_guard_installed", "non_draw_count_admission", "standalone_native_callsite_replacement_safe",
    "physical_only_clip_admission_verified", "arena_intersection_verified", "thread_lifetime_runtime_verified",
    "next_Tile_cancellation", "intraTile_cancellation_verified", "native_provider_rle_verified",
    "healthy_return_verified", "healthy_native_unwind_verified", "atomic_installation_verified",
    "transient_write_prevention_verified", "cross_thread_immutability_verified",
    "downstream_frozen_continuation_compatible", "downstream_frozen_primitive_compatible",
)


def _require(value, message):
    if not value:
        raise ValueError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pins():
    _require(type(LEASE_V2_SHA256) is str and len(LEASE_V2_SHA256) == 64 and
        all(c in "0123456789abcdef" for c in LEASE_V2_SHA256), "final frozen LeaseV2 source pin unavailable")
    return PINNED_SOURCES | {LEASE: LEASE_V2_SHA256}


def _read(path):
    _require(path.is_absolute() and path.is_relative_to(ROOT) and path.resolve(strict=True) == path,
        "canonical content V2 source required")
    for item in (path, *path.parents):
        row = item.lstat()
        _require(not item.is_symlink() and not getattr(row, "st_file_attributes", 0) & 0x400,
            "content V2 reparse path forbidden")
    before = path.stat(); raw = path.read_bytes(); after = path.stat()
    stamp = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, getattr(row, "st_file_attributes", 0))
    _require(stamp(before) == stamp(after) and len(raw) == after.st_size, "content V2 source changed while read")
    return raw, stamp(after)


def _snapshot():
    pins = _pins()
    result = {name: _read(ROOT/name) for name in (*pins, SOURCE)}
    _require(all(_sha(result[name][0]) == digest for name, digest in pins.items()), "content V2 dependency pin differs")
    _require(globals().get("__loaded_source_sha256__") == _sha(result[SOURCE][0]), "private content V2 issuer required")
    return result


def _unchanged(snapshot):
    _require(all(_read(ROOT/name) == receipt for name, receipt in snapshot.items()), "content V2 source graph changed")


@contextmanager
def _modules(snapshot):
    prefix = "_battle_content_v2_" + uuid.uuid4().hex
    owned, attributes, modules = {}, [], {}
    try:
        for suffix in ("", ".src", ".src.patcher"):
            module = types.ModuleType(prefix+suffix); module.__path__ = []
            _require(sys.modules.setdefault(module.__name__, module) is module, "content V2 namespace occupied")
            owned[module.__name__] = module
            if suffix:
                parent, _, leaf = module.__name__.rpartition(".")
                _require(not hasattr(sys.modules[parent], leaf), "content V2 namespace attribute occupied")
                setattr(sys.modules[parent], leaf, module); attributes.append((sys.modules[parent], leaf, module))
        for stem in MODULE_ORDER:
            name = "src/patcher/"+stem+".py"; full = prefix+".src.patcher."+stem
            module = types.ModuleType(full); module.__file__ = str(ROOT/name); module.__package__ = full.rpartition(".")[0]
            module.__loaded_source_sha256__ = _sha(snapshot[name][0])
            _require(sys.modules.setdefault(full, module) is module, "content V2 namespace occupied")
            owned[full] = module; parent = sys.modules[module.__package__]
            _require(not hasattr(parent, stem), "content V2 namespace attribute occupied")
            setattr(parent, stem, module); attributes.append((parent, stem, module))
            for source, marker in (("battle_profile_lifecycle_v2", "__canonical_lifecycle_v2_issuer__"),
                ("battle_profile_routing_v2", "__canonical_routing_v2_issuer__"),
                ("battle_profile_field_v3", "__canonical_field_v3_issuer__"),
                ("battle_profile_stack_lease_v2", "__canonical_stack_lease_v2_issuer__")):
                if stem == source: setattr(module, marker, True)
            exec(compile(snapshot[name][0], module.__file__, "exec"), module.__dict__); modules[name] = module
        yield modules
    finally:
        replaced = any(sys.modules.get(name) is not module for name, module in owned.items()) or any(
            getattr(parent, leaf, None) is not module for parent, leaf, module in attributes)
        for name, module in reversed(tuple(owned.items())):
            if sys.modules.get(name) is module: del sys.modules[name]
        _require(not replaced, "content V2 namespace identity changed")


@dataclass(frozen=True)
class Operand:
    instruction_offset: int
    instruction_bytes: int
    offset: int
    kind: str
    role: str
    value: int


@dataclass(frozen=True)
class ContentV2Emission:
    base_va: int
    state_va: int
    code: bytes
    entries: tuple
    relocations: tuple
    width: int
    height: int
    private_entries: tuple
    body_receipts: tuple = ()


@dataclass(frozen=True)
class ContentV2Bundle:
    emission: ContentV2Emission
    lease_bundle: object
    operand_inventory: tuple
    metadata_json: str
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()

    def metadata(self):
        return json.loads(self.metadata_json)


def _identity(out):
    return (out.base_va, out.state_va, out.width, out.height, out.code, out.entries, out.private_entries,
        tuple((r.offset, r.kind, r.target, r.purpose) for r in out.relocations),
        tuple(getattr(out, "field_return_pcs", ())), tuple(getattr(out, "lease_return_pcs", ())),
        tuple(getattr(out, "field_tile_receipts", ())), tuple(getattr(out, "lease_field_receipts", ())))


def _model_dependency(raw, module):
    if raw is None:
        _pins()
        return
    _require(type(raw) is bytes and _sha(raw) == MODEL_LEASE_SHA256 and
        _read(ROOT/LEASE)[0] == raw and Path(module.__file__).resolve() == ROOT/LEASE,
        "explicit exact synthetic lease source required")


def _versioned_template(raw, template_module):
    """One whole pinned function, exact edits, no final parent admission here."""
    _require(type(raw) is bytes and _sha(raw) == PINNED_SOURCES[TEMPLATE], "frozen whole content template differs")
    text = raw.decode("utf-8"); nodes = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "_emit_code"]
    _require(len(nodes) == 1, "one whole frozen content emitter required")
    source = [ast.get_source_segment(text, nodes[0])]; ledger = []
    def replace(old, new, count=1):
        _require(source[0].count(old) == count, "whole content edit occurrence differs: "+old[:80])
        source[0] = source[0].replace(old, new); ledger.append((old, new, count))
    replace("def _emit_code(plan,lease_emission,*,assembler_module):", "def _versioned_emit_code(plan,lease_emission,*,assembler_module):")
    replace("    def extent(reg,count,reject):", "    extent_number = [0]\n    def extent(reg,count,reject):")
    replace("        a.emit('39d0');a.branch('0f87',reject)", """        a.emit('39d0');a.branch('0f87',reject)
        for low,high in protected_intervals:
            label='content.stack.protected.'+str(extent_number[0]); extent_number[0]+=1
            cmpva(reg,high,'protected content allocation end');a.branch('0f83',label)
            cmpva(0,low,'protected content allocation start');a.branch('0f86',label)
            jump(reject);a.label(label)""")
    replace("    a.emit('39d0');a.branch('0f87','capture_stack.reject')", """    a.emit('39d0');a.branch('0f87','capture_stack.reject')
    for number,(low,high) in enumerate(protected_intervals):
        label='capture_stack.protected.'+str(number)
        cmpva(7,high,'protected captured ancestry allocation end');a.branch('0f83',label)
        cmpva(0,low,'protected captured ancestry allocation start');a.branch('0f86',label)
        jump('capture_stack.reject');a.label(label)""")
    replace("    def result(status):", """    def control_capture():
        for index,slot in enumerate(CONTROL_SLOTS):
            get(0,slot);put(0,CONTROL_SHADOW+4*index)
    def control_match():
        for index,slot in enumerate(CONTROL_SLOTS):
            get(0,slot);match(0,CONTROL_SHADOW+4*index);ne('unsafe_control')
    def mutable_capture():
        for index,slot in enumerate(MUTABLE_DESCRIPTOR_SLOTS):
            get(0,slot);put(0,MUTABLE_SHADOW+4*index)
    def mutable_match(reject):
        for index,slot in enumerate(MUTABLE_DESCRIPTOR_SLOTS):
            get(0,slot);match(0,MUTABLE_SHADOW+4*index);ne(reject)
    def protected_zero(reject):
        for pointer,count in ((state+128,16352),)+(() if modal_va is None else ((modal_va+128,992),)):
            a.emit('60fc');imm(0,0);imm(1,count);a.emit('bf');address(pointer,'fresh content protected zero tail')
            a.emit('f3af61');ne(reject)
    def result(status):""")
    first = source[0].index('    for off,value in ((0,0x534C4231),(4,1),(8,LEASE_BYTES)):')
    last = source[0].index('    for off in range(0,LEASE_BYTES,4):load(0,7,off);put(0,off)', first)
    canonical = source[0][first:last]
    _require(canonical.count('for off in range(68,LEASE_BYTES,4)') == 1, "full canonical content descriptor block required")
    canonical = canonical.replace("'lease.mode.full'", "'lease.mode.full.'+suffix").replace("'lease.mode.compare'", "'lease.mode.compare.'+suffix")
    canonical = ''.join('    '+line if line.strip() else line for line in canonical.splitlines(True))
    replace("    def result(status):", "    def canonical_descriptor(reject,suffix):\n        get(7,LEASE_EBP);get(6,FIELD_EBP)\n"+canonical+"    def result(status):")
    replace("        own('capture_inputs')", "        own('capture_inputs')\n        for slot in AUTHORITY_LOCALS:imm(0,0);put(0,slot)")
    replace("        operand(row);get(7,WORLD)", "        a.label(name+'.payload')\n        operand(row);get(7,WORLD)")
    replace("    a.emit('89ef');add(7,-16);extent(7,HELPER_BYTES+56,reject)",
        "    a.emit('89ef');add(7,-44);extent(7,HELPER_BYTES+84,reject)")
    replace("    a.emit('fcff15');address(THREAD_IAT,'fixed content owning ThreadId callback')\n    match(0,24);ne(reject)",
        "    control_capture();mutable_capture()\n    a.emit('fcff15');address(THREAD_IAT,'fixed content owning ThreadId callback')\n"+
        "    put(0,THREAD_RESULT);control_match();get(0,THREAD_RESULT)\n    match(0,24);ne(reject)\n"+
        "    mutable_match(reject);canonical_descriptor(reject,'thread')")
    replace("    if plan['profile'] not in ('classic','framed'):blocks+=((state-256,128,128),)", "    if modal_va is not None:blocks+=((modal_va,128,128),)")
    replace("    imm(0,1);a.emit('c3');a.label('fixed.reject');a.emit('31c0c3')", """    for cached,owner in ((1104,4),(1112,8),(1120,72),(1124,64)):
        load(0,6,cached);mem('3b',0,6,owner);ne('fixed.reject')
    for current,shadow in ((1132,1156),(1136,1160),(1140,1164),(1144,1168)):
        load(0,6,current);mem('3b',0,6,shadow);ne('fixed.reject')
    protected_zero('fixed.reject')
    imm(0,1);a.emit('c3');a.label('fixed.reject');a.emit('31c0c3')
    a.label('unsafe_control');a.emit('0f0b')""")
    replace("    for off,label in private_calls:a.relocations.append(assembler_module.Relocation(off,'rel32',base+a.labels[label],'private content helper '+label))", "")
    replace("rx+0x20000", "rx+0x40000")
    replace("('capture_inputs','capture_stack','admit_body','fixed_receipt')", "('capture_inputs','capture_stack','admit_body','fixed_receipt','unsafe_control','finish_rejected','finish_valid')")
    namespace = dict(template_module.__dict__)
    namespace.update(HELPER_BYTES=HELPER_BYTES, CodeEmission=ContentV2Emission, AUTHORITY_LOCALS=AUTHORITY_LOCALS,
        CONTROL_SLOTS=CONTROL_SLOTS, CONTROL_SHADOW=CONTROL_SHADOW, MUTABLE_DESCRIPTOR_SLOTS=MUTABLE_DESCRIPTOR_SLOTS,
        MUTABLE_SHADOW=MUTABLE_SHADOW, THREAD_RESULT=THREAD_RESULT)
    exec(compile(source[0], str(ROOT/SOURCE)+"#whole_pinned_content", "exec"), namespace)
    return namespace['_versioned_emit_code'], tuple(ledger), namespace


def _parent_receipts(layout, field, lease, field_module, lease_module):
    plan, modal = field_module._plan(layout)
    tiles = field_module._tile_receipts(field)
    _require(tuple(lease.field_tile_receipts) == tiles and tuple(lease.field_return_pcs) == tuple((m,pc) for m,pc,_,_ in tiles),
        "actual fresh field Tile descriptors differ")
    fields = dict(field.entries); private = dict(field.private_entries); result = []
    entries = dict(lease.entries)
    for mode, name in enumerate(('leased_draw_full', 'leased_draw_incremental')):
        rows = [r for r in lease.relocations if r.kind == 'rel32' and r.target == fields['draw_full' if mode == 0 else 'draw_incremental']]
        _require(len(rows) == 1, "one actual leased field CALL per mode required")
        row = rows[0]; at = row.offset-1; pc = lease.base_va+row.offset+4
        stop = entries['leased_draw_incremental'] if mode == 0 else entries['check_tile']
        _require(entries[name] <= lease.base_va+at < pc < stop and lease.code[at] == 0xe8 and
            row.purpose == 'fixed versioned field entry' and pc+struct.unpack_from('<i',lease.code,row.offset)[0] == row.target,
            "leased field instruction/target/return differs")
        result.append((mode,pc,pc-lease.base_va,row.target))
    _require(tuple(lease.lease_return_pcs) == tuple((m,pc) for m,pc,_,_ in result), "actual lease return PCs differ")
    _require(tuple(lease_module._lease_receipts(lease,field)) == tuple(result), "source-owned lease return descriptors differ")
    _require(tuple(lease.lease_field_receipts) == tuple(result), "complete immutable lease field receipts differ")
    _require(tuple(private) == ('capture_invocation','check_invocation','same_invocation') and
        lease.state_va == field.state_va == layout.rw.va and
        lease.base_va == (field.base_va+len(field.code)+15)&~15 and lease.base_va+len(lease.code) <= layout.rx.va+layout.rx.size,
        "complete fresh content parent extent/ABI differs")
    return plan, modal, tiles, tuple(result), private['check_invocation']


def _raw_emit(layout, field, lease, *, field_module, lease_module, template_source, template_module, assembler_module, model_dependency=None):
    _model_dependency(model_dependency,lease_module)
    plan, modal, _, _, check = _parent_receipts(layout,field,lease,field_module,lease_module)
    emitter, ledger, namespace = _versioned_template(template_source,template_module)
    def captured(supplied,parent):
        _require(supplied is plan and parent is lease, "exact captured fresh content parent required")
        return layout.rx.va,layout.rw.va,field.width,field.height,check
    namespace['_layout'] = captured; namespace['modal_va'] = modal
    namespace['protected_intervals'] = ((layout.rx.va,layout.rx.va+layout.rx.size),(layout.rw.va,layout.rw.va+layout.rw.size)) + (() if modal is None else ((modal,modal+4096),))
    parent = assembler_module._Assembler; relocation = assembler_module.Relocation; label_receipts=[]
    class CompleteAssembler(parent):
        def finish(self):
            result = super().finish()
            for offset,label in self.fixups:
                self.relocations.append(relocation(offset,'rel32',self.base+self.labels[label],'content_v2_internal:'+label))
            label_receipts.append(dict(self.labels))
            return result
    isolated = types.SimpleNamespace(_Assembler=CompleteAssembler,Relocation=relocation,absolute_relocation_offsets=assembler_module.absolute_relocation_offsets)
    out = emitter(plan,lease,assembler_module=isolated)
    _require(len(label_receipts)==1,"one complete content label receipt required")
    labels=label_receipts[0]; bodies=[]
    for va,*_ in template_module.SITES:
        name=f'site_{va:06x}';entry=out.base_va+labels[name]
        payload=out.base_va+labels[name+'.payload']
        calls=[r for r in out.relocations if r.kind=='rel32' and r.purpose=='content_v2_internal:admit_body' and
            entry <= out.base_va+r.offset-1 < payload]
        _require(len(calls)==1 and out.code[calls[0].offset-1]==0xe8,"one actual body admission CALL required")
        bodies.append((va,entry,payload,out.base_va+calls[0].offset+4,
            out.base_va+labels[name+'.denied'],out.base_va+labels[name+'.fault'],out.base_va+labels[name+'.valid']))
    out=ContentV2Emission(out.base_va,out.state_va,out.code,out.entries,out.relocations,out.width,out.height,out.private_entries,tuple(bodies))
    _require(out.base_va == (lease.base_va+len(lease.code)+15)&~15 and out.base_va+len(out.code) <= layout.rx.va+layout.rx.size,
        "content V2 exceeds fresh prefix reservation")
    return out, ledger


def _emit_code(layout, life, route, field, lease, *, lease_module, lease_kwargs, field_module,
    template_source, template_module, assembler_module, model_dependency=None):
    """Explicit final-source synthetic boundary, not a production capability."""
    _model_dependency(model_dependency,lease_module)
    expected = lease_module._emit_code(layout,life,route,field,**lease_kwargs)
    _require(_identity(lease) == _identity(expected), "complete canonical fresh lease bytes/ABI required")
    out,_ = _raw_emit(layout,field,lease,field_module=field_module,lease_module=lease_module,
        template_source=template_source,template_module=template_module,assembler_module=assembler_module,model_dependency=model_dependency)
    _operand_inventory(out,layout,field,lease,field_module=field_module,lease_module=lease_module,
        template_source=template_source,template_module=template_module,assembler_module=assembler_module,model_dependency=model_dependency)
    assembler_module.absolute_relocation_offsets(out)
    return out


def _decode(code):
    """Structural authored x86 dialect, including scalar8/16/32 operands."""
    cursor=0; rows=[]
    while cursor < len(code):
        start=cursor; fields=[]; opcode=code[cursor];cursor+=1; modrm_needed=False
        if opcode in (0x9c,0x9d,0x60,0x61,0xfc,0xc3,0x55,0x5d,0x4b): pass
        elif opcode == 0xf3:
            _require(cursor<len(code) and code[cursor]==0xaf,"content REP dialect differs");cursor+=1
        elif 0xb8 <= opcode <= 0xbf or opcode == 0xa9:
            fields.append((cursor,4,'immediate'));cursor+=4
        elif opcode in (0xe8,0xe9): fields.append((cursor,4,'relative'));cursor+=4
        elif opcode == 0x0f:
            _require(cursor<len(code),"truncated content escape");sub=code[cursor];cursor+=1
            if sub == 0x0b: pass
            elif 0x80 <= sub <= 0x8f:
                fields.append((cursor,4,'relative'));cursor+=4
            else:
                _require(sub in (0xb6,0xb7,0xbf),"content extended load dialect differs");modrm_needed=True
        elif opcode == 0x66:
            _require(cursor<len(code) and code[cursor]==0x8b,"content word prefix dialect differs");cursor+=1;modrm_needed=True
        else:
            _require(opcode in (0x81,0x83,0x8b,0x89,0x3b,0x39,0x85,0xf7,0xff,0x31,0x29,0x01,0xc1,0x6b,0x8d,0xd1),
                "unknown content opcode at "+hex(start)+": "+hex(opcode));modrm_needed=True
        if modrm_needed:
            _require(cursor<len(code),"truncated content modrm");modrm=code[cursor];cursor+=1;mode,rm=modrm>>6,modrm&7
            if mode != 3 and rm == 4:
                _require(cursor<len(code),"truncated content sib");sib=code[cursor];fields.append((cursor,1,'sib'));cursor+=1
                if mode == 0 and sib&7 == 5:fields.append((cursor,4,'memory_address'));cursor+=4
            if mode == 0 and rm == 5:fields.append((cursor,4,'memory_address'));cursor+=4
            elif mode == 1:fields.append((cursor,1,'displacement'));cursor+=1
            elif mode == 2:fields.append((cursor,4,'displacement'));cursor+=4
            if opcode == 0x81 or opcode == 0xf7 and (modrm>>3)&7 == 0:
                fields.append((cursor,4,'immediate'));cursor+=4
            elif opcode in (0x83,0xc1,0x6b):fields.append((cursor,1,'immediate'));cursor+=1
        _require(start<cursor<=len(code),"truncated content instruction")
        rows.append((start,cursor,tuple(fields)))
    return tuple(rows)


def _operand_inventory(out,layout,field,lease,**kwargs):
    expected,_ = _raw_emit(layout,field,lease,**kwargs)
    _require(_identity(out) == _identity(expected) and out.body_receipts==expected.body_receipts,
        "complete authored content operand/value/return contract differs")
    code=out.code; rows=_decode(code); starts={start for start,_,_ in rows}; records=[]
    declared={r.offset:r for r in out.relocations}; consumed=set()
    _require(len(declared)==len(out.relocations),"duplicate content operand")
    for start,end,fields in rows:
        for at,size,role in fields:
            row=declared.get(at); value=int.from_bytes(code[at:at+size],'little')
            if role=='relative':
                _require(row is not None and row.kind=='rel32',"missing content relative operand")
                value=out.base_va+at+4+struct.unpack_from('<i',code,at)[0]
                _require(value==row.target,"content relative target differs")
                if row.purpose.startswith('content_v2_internal:'):
                    _require(value-out.base_va in starts,"content internal target is not an instruction start")
                    typed='internal_'+('call' if code[start]==0xe8 else 'jump' if code[start]==0xe9 else 'conditional_branch')
                else:
                    _require(code[start]==0xe8 and value==dict(field.private_entries)['check_invocation'] and
                        row.purpose=='private current V2 complete content receipt',"external content CALL differs")
                    typed='callback_free_field_receipt_call'
                kind='rel32'
            elif row is not None:
                _require(size==4 and role in ('immediate','memory_address') and row.kind=='abs32' and value==row.target,
                    "content absolute operand differs")
                kind='abs32';typed='fixed_memory_address' if role=='memory_address' else 'authored_address_immediate'
            else:
                _require(role!='memory_address',"missing content memory relocation")
                kind='scalar'+str(size*8);typed='stack_displacement' if role=='displacement' else role
            if row is not None:consumed.add(at)
            records.append(Operand(start,end-start,at,kind,typed,value))
    _require(consumed==set(declared),"content relocation outside instruction operands")
    _require(all(va-out.base_va in starts for _,va in out.entries+out.private_entries),"content entry boundary differs")
    return tuple(sorted(records,key=lambda r:r.offset))


def _issue(original,profile,resolution):
    _pins()
    _require(type(original) is bytes and _sha(original)==BASE_SHA256,"exact content V2 original required")
    snapshot=_snapshot()
    with _modules(snapshot) as modules:
        lease_module=modules[LEASE]; parent=lease_module._issue(original,profile,resolution)
        field=parent.field_bundle;route=field.routing_bundle;life=route.lifecycle_bundle;context=life.allocation_context;layout=context.layout
        clip=modules[CLIP];field_module=modules[FIELD]
        field_kwargs=dict(template_source=snapshot['src/patcher/battle_profile_field_v2.py'][0],template_module=modules['src/patcher/battle_profile_field_v2.py'],
            routing_module=modules['src/patcher/battle_profile_routing_v2.py'],routing_template_source=snapshot['src/patcher/battle_profile_routing.py'][0],
            routing_template_module=modules['src/patcher/battle_profile_routing.py'],lifecycle_module=modules['src/patcher/battle_profile_lifecycle_v2.py'],
            lifecycle_template_source=snapshot['src/patcher/battle_profile_lifecycle.py'][0],lifecycle_template_module=modules['src/patcher/battle_profile_lifecycle.py'],assembler_module=clip)
        lease_kwargs=dict(field_module=field_module,field_kwargs=field_kwargs,template_source=snapshot['src/patcher/battle_profile_stack_lease.py'][0],
            template_module=modules['src/patcher/battle_profile_stack_lease.py'],assembler_module=clip)
        arguments=dict(lease_module=lease_module,lease_kwargs=lease_kwargs,field_module=field_module,
            template_source=snapshot[TEMPLATE][0],template_module=modules[TEMPLATE],assembler_module=clip)
        meta=parent.metadata()
        _require(meta['source_hashes'][LEASE]==LEASE_V2_SHA256 and meta['field_frame_bytes']==FIELD_BYTES and meta['owning_lease_frame_bytes']==LEASE_BYTES,
            "source-issued final lease interface required")
        native=modules[TEMPLATE]._authenticate_native(original,context.relayout_parent,clip)
        out=_emit_code(layout,life.emission,route.emission,field.emission,parent.emission,**arguments)
        raw_args={key:arguments[key] for key in ('field_module','lease_module','template_source','template_module','assembler_module')}
        inventory=_operand_inventory(out,layout,field.emission,parent.emission,**raw_args)
        _,ledger=_raw_emit(layout,field.emission,parent.emission,**raw_args)
        _,_,tiles,returns,_=_parent_receipts(layout,field.emission,parent.emission,field_module,lease_module)
        metadata=dict(schema='clash95_battle_profile_content_v2',profile=profile,resolution=resolution,
            original_sha256=BASE_SHA256,parent_candidate_sha256=_sha(context.parent),relayout_parent_sha256=_sha(context.relayout_parent),
            validation_stage=layout.validation_stage,source_hashes=meta['source_hashes']|{name:_sha(raw) for name,(raw,_) in snapshot.items()},
            lease_code_sha256=_sha(parent.emission.code),lease_metadata_sha256=_sha(parent.metadata_json.encode()),
            code_va=out.base_va,code_bytes=len(out.code),code_sha256=_sha(out.code),rx_reservation_bytes=layout.rx.size,rw_reservation_bytes=layout.rw.size,
            prefix_extent_bytes=out.base_va+len(out.code)-layout.rx.va,prefix_rx_remaining_bytes=layout.rx.va+layout.rx.size-out.base_va-len(out.code),
            helper_frame_bytes=HELPER_BYTES,helper_checked_interval_bytes=HELPER_BYTES+84,helper_low_watermark=-44,
            helper_authority_slots=CONTROL_SLOTS,helper_authority_shadow_offset=CONTROL_SHADOW,
            descriptor_mutable_shadow_slots=MUTABLE_DESCRIPTOR_SLOTS,descriptor_mutable_shadow_offset=MUTABLE_SHADOW,
            thread_result_offset=THREAD_RESULT,field_frame_bytes=FIELD_BYTES,owning_lease_frame_bytes=LEASE_BYTES,
            field_tile_return_receipts=tiles,lease_field_return_receipts=returns,native_operands=native,
            body_return_receipts=out.body_receipts,
            body_return_receipt_fields=('native_site_va','entry_va','payload_va','admit_return_pc','denied_va','fault_va','valid_va'),
            finish_receipts={name:va for name,va in out.private_entries if name in ('finish_rejected','finish_valid')},
            helper_abi=dict(value='EAX',status='EDX',denied=0,valid=1,fault=2,reject_value='incoming EAX retained on ordinary rejection'),
            tail_policy='exact zero: fresh RW+128..65536 and separate inherited modal+128..4096',
            provider_records_emitted=0,provider_capacity=None,writes_owner_state=False,writes_headers=False,writes_pixels=False,
            preparation_only=True,installed_hooks=[],entries=dict(out.entries),private_entries=dict(out.private_entries),
            template_edit_inventory=[dict(old=a,new=b,count=c) for a,b,c in ledger],
            operand_inventory=[dict(instruction_offset=r.instruction_offset,instruction_bytes=r.instruction_bytes,offset=r.offset,kind=r.kind,role=r.role,value=r.value) for r in inventory],
            unsafe_control_closure='UD2; changed helper controls/RET are never used for native unwind',
            limitations=['Value/status preparation is not native MOV/MOVSX replay; no adapter, hook or candidate is installed.',
                'Count admission is draw-only42F95B;426F95 and431D7A, earlier Count input and later owner reads remain unsupported.',
                'Status2 does not cancel FieldV3 next Tile, native continuations or provider/RLE work.',
                'Callback/frame/stack observations use models, not native capacity, mapping, cross-thread or transient-write authority.',
                'Content continuation, receiver/argument authority, clipping and atomic installation require separate successors.'],
            **{name:False for name in FALSE_CLAIMS})
    _unchanged(snapshot)
    return ContentV2Bundle(out,parent,inventory,json.dumps(metadata,sort_keys=True,separators=(',',':'),allow_nan=False))


def _production_factory():
    # Capture dispatch rather than consulting mutable public producer aliases.
    from hashlib import sha256 as digest
    from pathlib import Path as SourcePath
    from types import ModuleType as SourceModule
    from uuid import uuid4 as unique_name
    from sys import modules as registry
    rejection=ValueError;execute_source=exec;compile_source=compile
    path=SourcePath(__file__).absolute();root=path.parents[2]
    if path != root/'src/patcher/battle_profile_content_v2.py':
        raise rejection('canonical content V2 producer required')
    def read():
        if path.resolve(strict=True) != path:
            raise rejection('canonical content V2 source required')
        for item in (path,*path.parents):
            row=item.lstat()
            if item.is_symlink() or getattr(row,'st_file_attributes',0)&0x400:
                raise rejection('content V2 source reparse forbidden')
        before=path.stat();raw=path.read_bytes();after=path.stat()
        stamp=lambda row:(row.st_dev,row.st_ino,row.st_size,row.st_mtime_ns,getattr(row,'st_file_attributes',0))
        if stamp(before)!=stamp(after) or len(raw)!=after.st_size:
            raise rejection('content V2 source changed while read')
        return raw,stamp(after)
    raw,stamp=read();identity=digest(raw).hexdigest()
    name='_battle_content_v2_issuer_'+unique_name().hex;module=SourceModule(name)
    module.__file__=str(path);module.__loaded_source_sha256__=identity;module.__canonical_content_v2_issuer__=True
    if registry.setdefault(name,module) is not module:
        raise rejection('canonical content V2 issuer namespace occupied')
    try:
        execute_source(compile_source(raw,str(path),'exec'),module.__dict__);issuer=module.__dict__['_issue']
    finally:
        replaced=registry.get(name) is not module
        if registry.get(name) is module:del registry[name]
        if replaced:raise rejection('canonical content V2 issuer replaced')
    if read()!=(raw,stamp):raise rejection('content V2 source changed during capture')
    def dispatch(original,profile,resolution):
        if read()!=(raw,stamp):raise rejection('captured content V2 source differs')
        try:return issuer(original,profile,resolution)
        finally:
            if read()!=(raw,stamp):raise rejection('content V2 source changed during dispatch')
    return dispatch


if not globals().get('__canonical_content_v2_issuer__',False):
    emit_content_v2=_production_factory()
