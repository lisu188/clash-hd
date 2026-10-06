"""Uninstalled fresh stack-only battle lease successor.

Full field V3 receipts are authenticated after normal callbacks. Field V3 does
not consume lease loss; next-Tile cancellation remains unproved. No provider,
owner-page schema, installation, hooks or native proof is emitted.
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
SOURCE = "src/patcher/battle_profile_stack_lease_v2.py"
CONTEXT = "src/patcher/battle_profile_context_v2.py"
LIFECYCLE = "src/patcher/battle_profile_lifecycle_v2.py"
LIFE_TEMPLATE = "src/patcher/battle_profile_lifecycle.py"
ROUTE_TEMPLATE = "src/patcher/battle_profile_routing.py"
ROUTING = "src/patcher/battle_profile_routing_v2.py"
FIELD_V1 = "src/patcher/battle_profile_field.py"
TEMPLATE = "src/patcher/battle_profile_field_v2.py"
V1_CONTEXT = "src/patcher/battle_profile_context.py"
VIEWPORT = "src/patcher/framed_viewport.py"
CLIP = "src/patcher/partial_tile_clip.py"
PE = "src/patcher/pe_extension.py"
HUD = "src/patcher/framed_battle_hud.py"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
FALSE_CLAIMS = ("installed","battle_installed","expanded_battle_installed",
    "installation_ready","native_executed","game_executed","runtime_executed",
    "manual_input_proof","promotion_ready","release_accepted",
    "provider_capacity_verified","provider_lifetime_verified",
    "atomic_installation_verified","native_stack_capacity_verified",
    "healthy_return_verified","native_fallback_verified")
PINNED_SOURCES = {'src/patcher/battle_profile_context_v2.py': 'd0a8b27ae4d07b290a449c1c875d4b574d329d2a9ac6b1397a2753f7d10ee5c9', 'src/patcher/battle_profile_lifecycle.py': 'dccb907b09d002691cad679219942ac5a8ffcb2798af4c96b0b1768dbd9e9f44', 'src/patcher/battle_profile_context.py': 'be3bbca018c415895ba7e79e64862512f330297fb56b4d8321f8f6d378c38500', 'src/patcher/partial_tile_clip.py': '92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad', 'src/patcher/pe_extension.py': '4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27', 'src/patcher/framed_viewport.py': '1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42', 'src/patcher/framed_battle_viewport.py': '8673e36bd04ded2afc8cc3b9d7ff2fed4c48dae891fe289509b44a9070c23bc6', 'src/patcher/framed_battle_coordinates.py': 'b67900d7399e0ce807d88a261c97942598beebfc28e2d78774cd109098f95142', 'src/patcher/framed_battle_field.py': 'f690865e615db65d02e8c59b5c43e0cfbaa1e371dd6502441d16e0d270a7196d', 'src/patcher/framed_modal_canvas.py': '567b025520184a99f1f4f44b23a879ef9c729dcf2917dfa03a277c018cb20054', 'src/patcher/framed_battle_hud.py': '3a6cb61a2ec2fcd0fa9c52c09a96e11a9a2d9f75cac6e3a2e826d5caa98a3ee3', 'src/patcher/battle_profile_lifecycle_v2.py': 'cbc91857e7fb914be0e27654bd59c7ed4cec145c118d9ebe3aa8163b55e78199', 'src/patcher/battle_profile_routing.py': '838d371bf837ab0098420e5589abc07d446a22bd6daa25ecab683e4725e25972', 'src/patcher/battle_profile_routing_v2.py': '77be6897c0cfab78237a6d85dd678e772a0b34c81787e11736950f4cb4700b1c', 'src/patcher/battle_profile_field.py': 'c329460fc7289d11ac10ddc33d26eb5ad158169ca976fee41ccd32fba6d97c88', 'src/patcher/battle_profile_field_v2.py': '673a2170f77dc143a1d62745bf5879f23163e9cbcffa3f5549123c4cc81f8cbf'}

FIELD = "src/patcher/battle_profile_field_v3.py"
LEASE_TEMPLATE = "src/patcher/battle_profile_stack_lease.py"
PINNED_SOURCES |= {
    FIELD: "c369525f34308ab5fde48b9c334d45a90845aded3ab26abda5a08b5ff35d6d3a",
    LEASE_TEMPLATE: "47d6ad4931aef39b58919dff4b22b41cce76b0abf39267237a704471331f834c",
}
FALSE_CLAIMS += (
    "latched_leaf_loss_consumption_by_field", "next_Tile_cancellation",
    "native_cancellation_verified", "intraTile_cancellation_verified",
    "native_provider_rle_verified", "native_callback_abi_verified",
    "native_receiver_validity_verified", "native_argument_validity_verified",
    "standalone_native_callsite_replacement_safe", "healthy_native_unwind_verified",
    "whole_chain_capacity_verified", "native_stack_capacity_verified",
    "atomic_installation_verified", "arena_intersection_verified",
    "installed_external_callsite_admission_verified", "physical_only_clip_admission_verified",
    "transient_write_prevention_verified", "cross_thread_immutability_verified",
)
LEASE_BYTES, HELPER_BYTES, FIELD_BYTES = 192, 512, 1280
TAG, SCHEMA, ROOT_STACK_BOUND, THREAD_IAT = 0x534C4231, 1, 0x10000, 0x4EA4E8
FAMILIES = ("tile", "unit", "adjacent", "tracking_effect", "charge_effect", "sprite", "line")
PUBLIC = ("leased_draw_full", "leased_draw_incremental") + tuple("check_"+f for f in FAMILIES) + ("guarded_sprite", "guarded_line")
PRIVATE = ("discover_and_check", "check_fixed_receipt")
CONTROL_SLOTS = (-4,) + tuple(range(200, 316, 4)) + tuple(range(512, 552, 4))
CONTROL_SHADOW = 316
MUTABLE_DESCRIPTOR_SLOTS = (44,48,52,56,60,64)
MUTABLE_SHADOW = 476

def _require(condition, message):
    if not condition:
        raise ValueError(message)

def _sha(raw):
    return hashlib.sha256(raw).hexdigest()

def _read(path, root):
    _require(path.is_absolute() and path.is_relative_to(root) and path.resolve(strict=True) == path,
             "canonical lease V2 source required")
    for item in (path, *path.parents):
        row = item.lstat()
        _require(not item.is_symlink() and not getattr(row, "st_file_attributes", 0) & 0x400,
                 "lease V2 reparse path forbidden")
    before = path.stat(); data = path.read_bytes(); after = path.stat()
    stamp = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns,
                         getattr(row, "st_file_attributes", 0))
    _require(stamp(before) == stamp(after) and len(data) == after.st_size, "source changed while read")
    return data, stamp(after)

def _snapshot():
    snapshot = {name: _read(ROOT / name, ROOT) for name in (*PINNED_SOURCES, SOURCE)}
    _require(all(_sha(snapshot[name][0]) == digest for name, digest in PINNED_SOURCES.items()),
             "frozen lease V2 source pin differs")
    _require(globals().get("__loaded_source_sha256__") == _sha(snapshot[SOURCE][0]),
             "privately loaded lease V2 source required")
    return snapshot

def _unchanged(snapshot):
    _require(all(_read(ROOT / name, ROOT) == receipt for name, receipt in snapshot.items()),
             "lease V2 source closure changed")

@contextmanager
def _modules(snapshot):
    prefix = "_battle_lease_v2_" + uuid.uuid4().hex
    owned, modules, attributes = {}, {}, []
    try:
        for suffix in ("", ".src", ".src.patcher"):
            module = types.ModuleType(prefix + suffix)
            module.__path__ = []
            _require(sys.modules.setdefault(module.__name__, module) is module,
                     "private lease V2 namespace occupied")
            owned[module.__name__] = module
            if suffix:
                parent, _, leaf = module.__name__.rpartition(".")
                _require(not hasattr(sys.modules[parent], leaf), "private lease V2 attribute occupied")
                setattr(sys.modules[parent], leaf, module)
                attributes.append((sys.modules[parent], leaf, module))
        for name in (VIEWPORT,PE,CLIP,"src/patcher/framed_battle_viewport.py",
            "src/patcher/framed_battle_coordinates.py","src/patcher/framed_battle_field.py",
            "src/patcher/framed_modal_canvas.py",HUD,V1_CONTEXT,CONTEXT,LIFE_TEMPLATE,LIFECYCLE,ROUTE_TEMPLATE,ROUTING,FIELD_V1,TEMPLATE,FIELD,LEASE_TEMPLATE):
            full = prefix + "." + name.removesuffix(".py").replace("/", ".")
            module = types.ModuleType(full)
            module.__file__ = str(ROOT / name)
            module.__package__ = full.rpartition(".")[0]
            module.__loaded_source_sha256__ = _sha(snapshot[name][0])
            _require(sys.modules.setdefault(full, module) is module,
                     "private lease V2 namespace occupied")
            owned[full] = module
            parent = sys.modules[module.__package__]; leaf = full.rpartition(".")[2]
            _require(not hasattr(parent, leaf), "private lease V2 attribute occupied")
            setattr(parent, leaf, module); attributes.append((parent, leaf, module))
            if name == LIFECYCLE: module.__canonical_lifecycle_v2_issuer__ = True
            if name == ROUTING: module.__canonical_routing_v2_issuer__ = True
            if name == FIELD: module.__canonical_field_v3_issuer__ = True
            exec(compile(snapshot[name][0], module.__file__, "exec"), module.__dict__)
            modules[name] = module
        yield modules
    finally:
        replaced = any(sys.modules.get(name) is not module for name, module in owned.items()) or any(
            getattr(parent, leaf, None) is not module for parent, leaf, module in attributes)
        for name, module in reversed(tuple(owned.items())):
            if sys.modules.get(name) is module:
                del sys.modules[name]
        _require(not replaced, "private lease V2 namespace identity changed")


@dataclass(frozen=True)
class Operand:
    instruction_offset: int
    instruction_bytes: int
    offset: int
    kind: str
    role: str
    value: int


@dataclass(frozen=True)
class LeaseV2Emission:
    base_va: int
    state_va: int
    code: bytes
    entries: tuple
    relocations: tuple
    width: int
    height: int
    private_entries: tuple
    field_return_pcs: tuple
    lease_return_pcs: tuple
    field_tile_receipts: tuple
    lease_field_receipts: tuple


@dataclass(frozen=True)
class StackLeaseV2Bundle:
    emission: LeaseV2Emission
    field_bundle: object
    operand_inventory: tuple
    metadata_json: str
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()

    def metadata(self):
        return json.loads(self.metadata_json)


def _identity(out):
    return (out.base_va, out.state_va, out.width, out.height, out.code, out.entries,
        out.private_entries, tuple((r.offset,r.kind,r.target,r.purpose) for r in out.relocations))


def _field_layout(layout, field_emission, field_module):
    plan, modal = field_module._plan(layout)
    width,height=map(int,layout.resolution.split('x')); plan=plan|dict(width=width,height=height)
    _require(field_emission.state_va == layout.rw.va and field_emission.width == width and
        field_emission.height == height and field_emission.base_va % 16 == 0 and
        layout.rx.va <= field_emission.base_va < field_emission.base_va+len(field_emission.code) <= layout.rx.va+layout.rx.size,
        'fresh field extent differs')
    fields, private = dict(field_emission.entries), dict(field_emission.private_entries)
    _require(tuple(fields) == ('visible_columns','clamp_scroll_x','screen_to_cell','visible_cell','draw_full','draw_incremental') and
        tuple(private) == ('capture_invocation','check_invocation','same_invocation'), 'fresh field entry ABI differs')
    for va in fields.values():
        at=va-field_emission.base_va
        _require(field_emission.code[at:at+11] == bytes.fromhex('9c60fc81ec0005000089e5'),
            'exact 1280-byte field frame required')
    descriptors = field_module._tile_receipts(field_emission)
    return plan,modal,fields,private,descriptors


def _lease_receipts(out,field_emission):
    entries=dict(out.entries);fields=dict(field_emission.entries);result=[]
    _require(tuple(mode for mode,_ in out.lease_return_pcs)==(0,1),'two ordered lease draw returns required')
    for mode,pc in out.lease_return_pcs:
        at=pc-out.base_va
        lo=entries['leased_draw_incremental' if mode else 'leased_draw_full']
        hi=entries['check_tile' if mode else 'leased_draw_incremental']
        _require(lo<pc<hi and at>=5 and out.code[at-5]==0xe8,'actual leased field CALL required')
        target=pc+struct.unpack_from('<i',out.code,at-4)[0]
        rows=[r for r in out.relocations if r.offset==at-4]
        _require(target==fields['draw_incremental' if mode else 'draw_full'] and len(rows)==1 and
            (rows[0].kind,rows[0].target,rows[0].purpose)==('rel32',target,'fixed versioned field entry'),
            'complete leased field call target/receipt differs')
        result.append((mode,pc,at,target))
    return tuple(result)


def _versioned_template(raw, template_module):
    _require(type(raw) is bytes and _sha(raw) == PINNED_SOURCES[LEASE_TEMPLATE], 'frozen whole lease template differs')
    text=raw.decode('utf-8'); tree=ast.parse(text)
    rows=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name == '_emit_code']
    _require(len(rows) == 1, 'one complete frozen lease emitter required')
    source=[ast.get_source_segment(text,rows[0])]; ledger=[]
    def replace(old,new,count=1):
        _require(source[0].count(old) == count, 'whole lease edit occurrence differs: '+old[:80])
        source[0]=source[0].replace(old,new); ledger.append((old,new,count))
    replace('def _emit_code(plan,field_emission,*,assembler_module):',
            'def _versioned_emit_code(plan,field_emission,*,assembler_module):')
    replace('    def field_receipt(reject):', '''    def control_capture():
        for index,slot in enumerate(CONTROL_SLOTS):
            get(0,slot); put(0,CONTROL_SHADOW+4*index)
    def control_match(include_outputs=True):
        # Own helper authority precedes every post-callback pointer dereference.
        for index,slot in enumerate(CONTROL_SLOTS):
            # -4 is a live discover RET during Thread. After discover returns,
            # native argument/output pushes legitimately reuse that word.
            if not include_outputs and slot in (-4,512,516,528,532,536,540,544): continue
            get(0,slot); local_cmp(0,CONTROL_SHADOW+4*index); ne("unsafe.control")
    def protected_zero(reject):
        for pointer,count in ((state+128,16352),)+(() if modal_va is None else ((modal_va+128,992),)):
            a.emit("60fc"); movi(0,0); movi(1,count)
            a.emit("bf"); address(pointer,"fresh lease protected zero tail")
            a.emit("f3af61"); ne(reject)
    def descriptor_shadow_capture():
        for index,slot in enumerate(MUTABLE_DESCRIPTOR_SLOTS):
            get(0,slot); put(0,MUTABLE_SHADOW+4*index)
    def descriptor_shadow_match(reject):
        for index,slot in enumerate(MUTABLE_DESCRIPTOR_SLOTS):
            get(0,slot); local_cmp(0,MUTABLE_SHADOW+4*index); ne(reject)
    def field_receipt(reject):''')
    # Revalidate all source-owned canonical descriptor words after callbacks.
    # The six mutable words also retain an independent pre-callback shadow;
    # a paired actual-descriptor/helper-copy change cannot silently be adopted.
    first=source[0].index('    for key,value in (("tag",TAG),("schema",SCHEMA),("bytes",LEASE_BYTES)):')
    last=source[0].index('    copy_descriptor(False,reject)',first)
    canonical=source[0][first:last]
    _require(canonical.count('for offset in range(68,LEASE_BYTES,4)')==1,
             'complete canonical descriptor validation block required')
    canonical=canonical.replace('"descriptor.full"','"descriptor.full."+suffix').replace(
        '"descriptor.return"','"descriptor.return."+suffix')
    balance='    mem(0,7,52); mem(1,7,56); a.emit("39c8"); ne(reject)'
    _require(canonical.count(balance)==1,'one exact descriptor counter balance required')
    canonical=canonical.replace(balance,
        '    mem(0,7,52); mem(1,7,56)\n    if inflight: add(1,1)\n    a.emit("39c8"); ne(reject)')
    canonical=''.join('    '+line if line.strip() else line for line in canonical.splitlines(True))
    replace('    def field_receipt(reject):',
        '    def canonical_descriptor(reject,suffix,inflight=False):\n        get(7,LEASE_EBP); get(6,FIELD_EBP)\n'+canonical+
        '    def field_receipt(reject):')
    replace('    def field_receipt(reject):', '''    def exact_virgin(name):
        # Same fixed-record and full-tail predicate as pinned fresh RoutingV2.
        # A phase-only/nonzero shortcut cannot classify an owner as virgin.
        spans=((state,32),(state+128,16352))
        if modal_va is not None: spans+=((modal_va,32),(modal_va+128,992))
        for pointer,count in spans:
            a.emit("60fc"); movi(0,0); movi(1,count)
            a.emit("bf"); address(pointer,"exact virgin lease fixed zero span")
            a.emit("f3af61"); ne(name+".not_virgin")
        finish(LEASE_BYTES,value=0)
        a.label(name+".not_virgin")
    def field_receipt(reject):''')
    replace('        read(0,state+STATE_ROOT,"lease root stack"); put(0,20)',
        '        exact_virgin(name)\n        read(0,state+STATE_ROOT,"lease root stack"); put(0,20)')
    replace('        put(0,LEASE_BYTES+28)\n        get(1,44);',
        '        a.emit("85c0"); ne(name+".field_nonzero"); movi(0,2)\n'+
        '        a.label(name+".field_nonzero")\n        put(0,LEASE_BYTES+28)\n        get(1,44);')
    replace('        a.label(name+".reject"); finish(LEASE_BYTES,value=0)',
        '        a.label(name+".reject"); finish(LEASE_BYTES,value=2)')
    replace('        get(7,LEASE_EBP)\n        # Inspect the exact pre-call receipt',
            '        control_match(False)\n        descriptor_shadow_match(name+".lost")\n'+
            '        canonical_descriptor(name+".lost",name,True)\n        get(7,LEASE_EBP)\n        # Inspect the exact pre-call receipt')
    replace('        movi(0,0); store(0,7,48); put(0,48)',
            '        movi(0,0); store(0,7,48); put(0,48)\n        descriptor_shadow_capture()')
    replace('    a.emit("fcff15"); address(THREAD_IAT,"fixed native owning thread callback")',
            '    control_capture(); descriptor_shadow_capture()\n'+
            '    a.emit("fcff15"); address(THREAD_IAT,"fixed native owning thread callback")')
    replace('    local_cmp(0,24); ne(reject)',
            '    put(0,500); control_match(); get(0,500)\n    local_cmp(0,24); ne(reject)\n'+
            '    descriptor_shadow_match(reject); canonical_descriptor(reject,"thread")')
    replace('    field_receipt(reject)',
            '    own_call("check_fixed_receipt"); a.emit("83f801"); ne(reject)\n    field_receipt(reject)')
    replace("    if plan['profile'] not in ('classic','framed'): fixed+=((state-256,128,128),)",
            '    if modal_va is not None: fixed+=((modal_va,128,128),)')
    replace('    movi(0,1); a.emit("c3")\n    a.label("fixed.reject")', '''    # Cache/control authority precedes field check_invocation cached reads.
    for cached,owner in ((1104,4),(1112,8),(1120,72),(1124,64)):
        memory("8b",0,6,cached); memory("3b",0,6,owner); ne("fixed.reject")
    for current,shadow in ((1132,1156),(1136,1160),(1140,1164),(1144,1168)):
        memory("8b",0,6,current); memory("3b",0,6,shadow); ne("fixed.reject")
    protected_zero("fixed.reject")
    movi(0,1); a.emit("c3")
    a.label("fixed.reject")''')
    replace('    a.label("code_end")','    a.label("unsafe.control"); a.emit("0f0b")\n    a.label("code_end")')
    replace('    for offset,label in private_calls:\n        a.relocations.append(assembler_module.Relocation(offset,"rel32",base+a.labels[label],"private stack lease helper "+label))','')
    replace('rx+0x20000','rx+0x40000')
    replace('    a.emit("89ef"); add(7,-36); extent(7,HELPER_BYTES+76,reject)',
        '    a.emit("89ef"); add(7,-44); extent(7,HELPER_BYTES+84,reject)')
    namespace=dict(template_module.__dict__)
    namespace.update(CONTROL_SLOTS=CONTROL_SLOTS,CONTROL_SHADOW=CONTROL_SHADOW,
        MUTABLE_DESCRIPTOR_SLOTS=MUTABLE_DESCRIPTOR_SLOTS,MUTABLE_SHADOW=MUTABLE_SHADOW)
    exec(compile(source[0],str(ROOT/SOURCE)+'#whole_pinned_lease','exec'),namespace)
    return namespace['_versioned_emit_code'],tuple(ledger),namespace


def _raw_emit(layout,field_emission,*,field_module,template_source,template_module,assembler_module):
    plan,modal,fields,private,descriptors=_field_layout(layout,field_emission,field_module)
    emitter,ledger,namespace=_versioned_template(template_source,template_module)
    namespace['modal_va']=modal
    def captured(supplied,out):
        _require(supplied is plan and out is field_emission,'exact captured field required')
        return (layout.rx.va,layout.rw.va,plan['width'],plan['height'],fields,private,
            tuple((mode,pc) for mode,pc,_,_ in descriptors))
    namespace['_field_layout']=captured
    parent=assembler_module._Assembler; relocation=assembler_module.Relocation
    class CompleteAssembler(parent):
        def finish(self):
            result=super().finish()
            for offset,label in self.fixups:
                self.relocations.append(relocation(offset,'rel32',self.base+self.labels[label],
                    'lease_v2_internal:'+label))
            return result
    isolated=types.SimpleNamespace(_Assembler=CompleteAssembler,Relocation=relocation,
        absolute_relocation_offsets=assembler_module.absolute_relocation_offsets)
    out=emitter(plan,field_emission,assembler_module=isolated)
    result=LeaseV2Emission(out.base_va,out.state_va,out.code,out.entries,out.relocations,
        out.width,out.height,out.private_entries,out.field_return_pcs,out.lease_return_pcs,descriptors,
        _lease_receipts(out,field_emission))
    _require(result.base_va == (field_emission.base_va+len(field_emission.code)+15)&~15 and
        result.base_va+len(result.code) <= layout.rx.va+layout.rx.size,'fresh lease prefix extent differs')
    return result,ledger


def _emit_code(layout,lifecycle_emission,routing_emission,field_emission,*,field_module,field_kwargs,
               template_source,template_module,assembler_module):
    """Explicit synthetic RAM boundary; production uses only private pinned modules."""
    expected=field_module._emit_code(layout,lifecycle_emission,routing_emission,**field_kwargs)
    _require(_identity(field_emission) == _identity(expected),'complete canonical fresh field bytes/ABI required')
    out,_=_raw_emit(layout,field_emission,field_module=field_module,template_source=template_source,
        template_module=template_module,assembler_module=assembler_module)
    _operand_inventory(out,layout,field_emission,field_module=field_module,
        template_source=template_source,template_module=template_module,assembler_module=assembler_module)
    assembler_module.absolute_relocation_offsets(out)
    return out


def _decode(code):
    """Bounded authored dialect; operands are structural, never chosen by VA ranges."""
    cursor=0; rows=[]
    while cursor<len(code):
        start=cursor; fields=[]; opcode=code[cursor];cursor+=1
        if opcode in (0x9c,0x9d,0x60,0x61,0xfc,0xc3,0x55,0x5d): pass
        elif opcode==0xc2: fields.append((cursor,2,'return_pop'));cursor+=2
        elif opcode==0xf3:
            _require(cursor<len(code) and code[cursor]==0xaf,'lease REP dialect differs');cursor+=1
        elif 0xb8<=opcode<=0xbf or opcode==0xa9:
            fields.append((cursor,4,'immediate'));cursor+=4
        elif opcode in (0xe8,0xe9): fields.append((cursor,4,'relative'));cursor+=4
        elif opcode==0x0f:
            sub=code[cursor];cursor+=1
            if sub!=0x0b:
                _require(sub in (0x82,0x83,0x84,0x85,0x86,0x87),'lease Jcc dialect differs')
                fields.append((cursor,4,'relative'));cursor+=4
        elif opcode in (0x81,0x83,0x8b,0x89,0x3b,0x39,0x85,0xf7,0xff,0x31):
            modrm=code[cursor];cursor+=1;mode,rm=modrm>>6,modrm&7
            if mode!=3 and rm==4:
                sib=code[cursor];cursor+=1
                if mode==0 and sib&7==5: fields.append((cursor,4,'memory_address'));cursor+=4
            if mode==0 and rm==5: fields.append((cursor,4,'memory_address'));cursor+=4
            elif mode==1: fields.append((cursor,1,'displacement'));cursor+=1
            elif mode==2: fields.append((cursor,4,'displacement'));cursor+=4
            if opcode==0x81 or opcode==0xf7 and (modrm>>3)&7==0:
                fields.append((cursor,4,'immediate'));cursor+=4
            elif opcode==0x83: fields.append((cursor,1,'immediate'));cursor+=1
        else: raise ValueError('unknown lease instruction at '+hex(start)+': '+hex(opcode))
        _require(start<cursor<=len(code),'truncated lease instruction')
        rows.append((start,cursor,tuple(fields)))
    return tuple(rows)


def _operand_inventory(out,layout,field_emission,*,field_module,template_source,template_module,assembler_module):
    # Whole authored reconstruction binds scalar values/roles as well as addresses.
    expected,_=_raw_emit(layout,field_emission,field_module=field_module,template_source=template_source,
        template_module=template_module,assembler_module=assembler_module)
    _require(_identity(out)==_identity(expected) and out.field_return_pcs==expected.field_return_pcs and
        out.lease_return_pcs==expected.lease_return_pcs and out.field_tile_receipts==expected.field_tile_receipts and
        out.lease_field_receipts==expected.lease_field_receipts,
        'complete authored lease operand/value/descriptor contract differs')
    _require(tuple(dict(out.entries))==PUBLIC and tuple(dict(out.private_entries))==PRIVATE,
        'lease public/private ABI inventory differs')
    rows=_decode(out.code); starts={start for start,_,_ in rows}; records=[]
    declared={r.offset:r for r in out.relocations}
    _require(len(declared)==len(out.relocations),'duplicate lease operand')
    consumed=set();fields=dict(field_emission.entries);private=dict(field_emission.private_entries)
    for start,end,operands in rows:
        opcode=out.code[start]
        for at,size,role in operands:
            value=int.from_bytes(out.code[at:at+size],'little');row=declared.get(at)
            if role=='relative':
                _require(row is not None and row.kind=='rel32','missing lease relative operand')
                target=out.base_va+at+4+struct.unpack_from('<i',out.code,at)[0]
                _require(target==row.target,'lease relative target differs')
                if row.purpose.startswith('lease_v2_internal:'):
                    _require(target-out.base_va in starts,'internal lease target is not an instruction start')
                    typed='internal_'+('call' if opcode==0xe8 else 'jump' if opcode==0xe9 else 'conditional_branch')
                else:
                    _require(opcode==0xe8 and (target,row.purpose) in (
                        (fields['draw_full'],'fixed versioned field entry'),
                        (fields['draw_incremental'],'fixed versioned field entry'),
                        (private['check_invocation'],'private authenticated V2 complete receipt'),
                        (0x402e80,'unchanged native primitive normal-return call'),
                        (0x403f70,'unchanged native primitive normal-return call')),'external lease transfer differs')
                    typed='native_normal_return_call' if target in (0x402e80,0x403f70) else 'field_call'
                kind='rel32';value=target
            elif row is not None:
                _require(size==4 and row.kind=='abs32' and row.target==value and
                    role in ('memory_address','immediate'),'absolute lease operand differs')
                kind='abs32';typed='fixed_memory_address' if role=='memory_address' else 'authored_address_immediate'
            else:
                _require(role!='memory_address','missing lease memory relocation')
                kind='scalar'+str(size*8);typed='stack_displacement' if role=='displacement' else role
            if row is not None: consumed.add(at)
            records.append(Operand(start,end-start,at,kind,typed,value))
    _require(consumed==set(declared),'lease relocation outside complete instruction inventory')
    _require(all(va-out.base_va in starts for _,va in out.entries+out.private_entries),'lease entry boundary differs')
    return tuple(sorted(records,key=lambda row:row.offset))


def _issue(original,profile,resolution):
    _require(type(original) is bytes and _sha(original)==BASE_SHA256,'exact lease V2 original required')
    snapshot=_snapshot()
    with _modules(snapshot) as modules:
        field_module=modules[FIELD];field=field_module._issue(original,profile,resolution)
        route=field.routing_bundle;life=route.lifecycle_bundle;context=life.allocation_context;layout=context.layout
        kwargs=dict(template_source=snapshot[TEMPLATE][0],template_module=modules[TEMPLATE],
            routing_module=modules[ROUTING],routing_template_source=snapshot[ROUTE_TEMPLATE][0],
            routing_template_module=modules[ROUTE_TEMPLATE],lifecycle_module=modules[LIFECYCLE],
            lifecycle_template_source=snapshot[LIFE_TEMPLATE][0],lifecycle_template_module=modules[LIFE_TEMPLATE],
            assembler_module=modules[CLIP])
        arguments=dict(field_module=field_module,field_kwargs=kwargs,template_source=snapshot[LEASE_TEMPLATE][0],
            template_module=modules[LEASE_TEMPLATE],assembler_module=modules[CLIP])
        meta=field.metadata()
        _require(meta['source_hashes'][FIELD]==PINNED_SOURCES[FIELD] and meta['helper_local_frame_bytes']==FIELD_BYTES and
            tuple(field.tile_return_receipts)==field_module._tile_receipts(field.emission) and
            tuple(field.operand_inventory)==field_module._operand_inventory(field.emission,layout,route.emission),
            'source-issued full field metadata/operands/Tile receipts required')
        native=modules[LEASE_TEMPLATE]._authenticate_native_abi(original,context.relayout_parent,modules[CLIP])
        out=_emit_code(layout,life.emission,route.emission,field.emission,**arguments)
        operands=_operand_inventory(out,layout,field.emission,**{key:arguments[key] for key in
            ('field_module','template_source','template_module','assembler_module')})
        _,ledger,_=_versioned_template(snapshot[LEASE_TEMPLATE][0],modules[LEASE_TEMPLATE])
        metadata=dict(schema='clash95_battle_profile_stack_lease_v2',profile=profile,resolution=resolution,
            original_sha256=BASE_SHA256,parent_candidate_sha256=_sha(context.parent),
            relayout_parent_sha256=_sha(context.relayout_parent),validation_stage=layout.validation_stage,
            field_code_sha256=_sha(field.emission.code),field_metadata_sha256=_sha(field.metadata_json.encode()),
            source_hashes=meta['source_hashes']|{name:_sha(raw) for name,(raw,_) in snapshot.items()},
            code_va=out.base_va,code_bytes=len(out.code),code_sha256=_sha(out.code),
            rx_reservation_bytes=layout.rx.size,rw_reservation_bytes=layout.rw.size,state_va=layout.rw.va,state_bytes=128,
            prefix_extent_bytes=out.base_va+len(out.code)-layout.rx.va,
            prefix_rx_remaining_bytes=layout.rx.va+layout.rx.size-out.base_va-len(out.code),
            field_frame_bytes=FIELD_BYTES,owning_lease_frame_bytes=LEASE_BYTES,helper_frame_bytes=HELPER_BYTES,
            helper_authority_slots=CONTROL_SLOTS,helper_authority_shadow_offset=CONTROL_SHADOW,
            live_private_discover_return_offset=-4,
            descriptor_mutable_shadow_slots=MUTABLE_DESCRIPTOR_SLOTS,descriptor_mutable_shadow_offset=MUTABLE_SHADOW,
            helper_with_private_calls_and_zero_scan_bytes=596,
            helper_lowest_authored_sp_offset=-44,helper_extent_end_offset=552,
            source_parent_plus_lease_stack_allowance_bytes=meta['maximum_added_helper_chain_bytes']+LEASE_BYTES+40,
            field_tile_return_receipts=[dict(mode=m,pc=pc,code_offset=at,post_call_target=target)
                for m,pc,at,target in out.field_tile_receipts],
            lease_field_return_receipts=[dict(mode=m,pc=pc,code_offset=at,call_target=target)
                for m,pc,at,target in out.lease_field_receipts],
            field_tile_return_pcs=dict(out.field_return_pcs),lease_field_return_pcs=dict(out.lease_return_pcs),
            private_receipt_entries=dict(out.private_entries),field_private_receipt_entries=dict(field.emission.private_entries),
            descriptor_offsets=modules[LEASE_TEMPLATE].DESCRIPTOR,
            field_frame_offsets=meta['field_frame_offsets'],
            native_return_abi=native['returns'],native_call_abi=native['calls'],
            tail_policy='exact zero: fresh RW+128..65536 and separate inherited modal+128..4096',
            provider_records_emitted=0,provider_capacity=None,writes_owner_state=False,writes_headers=False,
            heap_or_global_descriptor=False,preparation_only=True,installed_hooks=[],
            template_edit_inventory=[dict(old=a,new=b,count=c) for a,b,c in ledger],
            operand_inventory=[dict(instruction_offset=r.instruction_offset,instruction_bytes=r.instruction_bytes,
                offset=r.offset,kind=r.kind,role=r.role,value=r.value) for r in operands],
            unsafe_helper_control_closure='UD2; no healthy native unwind or fatal/quit integration proof',
            leaf_result_semantics='normal-return EAX/flags retained; stack loss is separate; no retries',
            outer_draw_statuses={'0':'exact complete virgin records and zero tails only; no Thread or cached reads',
                '1':'modeled complete draw; no native/runtime claim',
                '2':'owned/history/control loss or stricter wrapper denial of FieldV3 off-field draw0; no fallback'},
            limitations=['Uninstalled source component; mapped/native stack availability and whole-chain capacity are unproved.',
                'Field V3 same_invocation does not consume lease loss; next Tile may continue after a lease-only loss.',
                'Native local control, RLE/provider lifetime, intra-Tile cancellation, receiver/argument/clipping authority remain unproved.',
                'Normal-return observation cannot prevent transient/cross-thread writes or prove healthy native restoration.',
                'Content, continuation, primitive-request and line-replay need their own successors before integration.'],
            **{name:False for name in FALSE_CLAIMS})
    _unchanged(snapshot)
    return StackLeaseV2Bundle(out,field,operands,json.dumps(metadata,sort_keys=True,separators=(',',':'),allow_nan=False))

def _production_factory():
    from hashlib import sha256 as digest
    from pathlib import Path as SourcePath
    from types import ModuleType as SourceModule
    from uuid import uuid4 as unique_name
    from sys import modules as registry
    exact_type, exact_bytes, rejection = type, bytes, ValueError
    compile_source, execute_source = compile, exec
    path = SourcePath(__file__).absolute(); root = path.parents[2]
    if path != root / "src/patcher/battle_profile_stack_lease_v2.py":
        raise rejection("canonical lease V2 producer required")

    def read():
        if path.resolve(strict=True) != path:
            raise rejection("canonical lease V2 source required")
        for item in (path, *path.parents):
            row = item.lstat()
            if item.is_symlink() or getattr(row,"st_file_attributes",0) & 0x400:
                raise rejection("lease V2 source reparse forbidden")
        before=path.stat(); raw=path.read_bytes(); after=path.stat()
        def stamp(row):
            return row.st_dev,row.st_ino,row.st_size,row.st_mtime_ns,getattr(row,"st_file_attributes",0)
        if stamp(before) != stamp(after) or len(raw) != after.st_size:
            raise rejection("lease V2 source changed while read")
        return raw,stamp(after)

    raw,stamp=read(); identity=digest(raw).hexdigest()
    name="_battle_lease_v2_issuer_"+unique_name().hex
    module=SourceModule(name);module.__file__=str(path)
    module.__loaded_source_sha256__=identity;module.__canonical_stack_lease_v2_issuer__=True
    if registry.setdefault(name,module) is not module:
        raise rejection("canonical lease V2 issuer namespace occupied")
    try:
        execute_source(compile_source(raw,str(path),"exec"),module.__dict__)
        issuer=module.__dict__["_issue"]
    finally:
        if registry.get(name) is not module:
            raise rejection("canonical lease V2 issuer replaced")
        del registry[name]
    if read() != (raw,stamp):
        raise rejection("canonical lease V2 source changed during capture")
    original_digest="500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"

    def dispatch(original,profile,resolution):
        if exact_type(original) is not exact_bytes or digest(original).hexdigest() != original_digest:
            raise rejection("exact original required")
        current,receipt=read()
        if digest(current).hexdigest() != identity:
            raise rejection("captured lease V2 source differs")
        try:
            return issuer(original,profile,resolution)
        finally:
            if read() != (current,receipt):
                raise rejection("lease V2 source changed during dispatch")
    return dispatch

if not globals().get("__canonical_stack_lease_v2_issuer__",False):
    emit_stack_lease_v2 = _production_factory()
