"""Uninstalled fresh-address tactical routing; no native/runtime acceptance.

The frozen routing template is re-emitted after canonical lifecycle V2.
Zero is only complete virgin query denial without a callback; two is unknown,
historical or owned receipt loss. Neither authorizes an adapter fallback.
Its explicit UD2 endpoint proves no cancellation or healthy restoration.
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
SOURCE = "src/patcher/battle_profile_routing_v2.py"
CONTEXT = "src/patcher/battle_profile_context_v2.py"
LIFECYCLE = "src/patcher/battle_profile_lifecycle_v2.py"
LIFE_TEMPLATE = "src/patcher/battle_profile_lifecycle.py"
TEMPLATE = "src/patcher/battle_profile_routing.py"
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
PINNED_SOURCES = {'src/patcher/battle_profile_context_v2.py': 'd0a8b27ae4d07b290a449c1c875d4b574d329d2a9ac6b1397a2753f7d10ee5c9', 'src/patcher/battle_profile_lifecycle.py': 'dccb907b09d002691cad679219942ac5a8ffcb2798af4c96b0b1768dbd9e9f44', 'src/patcher/battle_profile_context.py': 'be3bbca018c415895ba7e79e64862512f330297fb56b4d8321f8f6d378c38500', 'src/patcher/partial_tile_clip.py': '92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad', 'src/patcher/pe_extension.py': '4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27', 'src/patcher/framed_viewport.py': '1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42', 'src/patcher/framed_battle_viewport.py': '8673e36bd04ded2afc8cc3b9d7ff2fed4c48dae891fe289509b44a9070c23bc6', 'src/patcher/framed_battle_coordinates.py': 'b67900d7399e0ce807d88a261c97942598beebfc28e2d78774cd109098f95142', 'src/patcher/framed_battle_field.py': 'f690865e615db65d02e8c59b5c43e0cfbaa1e371dd6502441d16e0d270a7196d', 'src/patcher/framed_modal_canvas.py': '567b025520184a99f1f4f44b23a879ef9c729dcf2917dfa03a277c018cb20054', 'src/patcher/framed_battle_hud.py': '3a6cb61a2ec2fcd0fa9c52c09a96e11a9a2d9f75cac6e3a2e826d5caa98a3ee3', 'src/patcher/battle_profile_lifecycle_v2.py': 'cbc91857e7fb914be0e27654bd59c7ed4cec145c118d9ebe3aa8163b55e78199', 'src/patcher/battle_profile_routing.py': '838d371bf837ab0098420e5589abc07d446a22bd6daa25ecab683e4725e25972'}


def _require(condition, message):
    if not condition:
        raise ValueError(message)

def _sha(raw):
    return hashlib.sha256(raw).hexdigest()

def _read(path, root):
    _require(path.is_absolute() and path.is_relative_to(root) and path.resolve(strict=True) == path,
             "canonical routing V2 source required")
    for item in (path, *path.parents):
        row = item.lstat()
        _require(not item.is_symlink() and not getattr(row, "st_file_attributes", 0) & 0x400,
                 "routing V2 reparse path forbidden")
    before = path.stat(); data = path.read_bytes(); after = path.stat()
    stamp = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns,
                         getattr(row, "st_file_attributes", 0))
    _require(stamp(before) == stamp(after) and len(data) == after.st_size, "source changed while read")
    return data, stamp(after)

def _snapshot():
    snapshot = {name: _read(ROOT / name, ROOT) for name in (*PINNED_SOURCES, SOURCE)}
    _require(all(_sha(snapshot[name][0]) == digest for name, digest in PINNED_SOURCES.items()),
             "frozen routing V2 source pin differs")
    _require(globals().get("__loaded_source_sha256__") == _sha(snapshot[SOURCE][0]),
             "privately loaded routing V2 source required")
    return snapshot

def _unchanged(snapshot):
    _require(all(_read(ROOT / name, ROOT) == receipt for name, receipt in snapshot.items()),
             "routing V2 source closure changed")

@contextmanager
def _modules(snapshot):
    prefix = "_battle_routing_v2_" + uuid.uuid4().hex
    owned, modules = {}, {}
    try:
        for suffix in ("", ".src", ".src.patcher"):
            module = types.ModuleType(prefix + suffix)
            module.__path__ = []
            _require(sys.modules.setdefault(module.__name__, module) is module,
                     "private routing V2 namespace occupied")
            owned[module.__name__] = module
            if suffix:
                parent, _, leaf = module.__name__.rpartition(".")
                setattr(sys.modules[parent], leaf, module)
        for name in (VIEWPORT,PE,CLIP,"src/patcher/framed_battle_viewport.py",
            "src/patcher/framed_battle_coordinates.py","src/patcher/framed_battle_field.py",
            "src/patcher/framed_modal_canvas.py",HUD,V1_CONTEXT,CONTEXT,LIFE_TEMPLATE,LIFECYCLE,TEMPLATE):
            full = prefix + "." + name.removesuffix(".py").replace("/", ".")
            module = types.ModuleType(full)
            module.__file__ = str(ROOT / name)
            module.__package__ = full.rpartition(".")[0]
            module.__loaded_source_sha256__ = _sha(snapshot[name][0])
            _require(sys.modules.setdefault(full, module) is module,
                     "private routing V2 namespace occupied")
            owned[full] = module
            setattr(sys.modules[module.__package__], full.rpartition(".")[2], module)
            if name == LIFECYCLE: module.__canonical_lifecycle_v2_issuer__ = True
            exec(compile(snapshot[name][0], module.__file__, "exec"), module.__dict__)
            modules[name] = module
        yield modules
    finally:
        replaced = any(sys.modules.get(name) is not module for name, module in owned.items())
        for name, module in reversed(tuple(owned.items())):
            if sys.modules.get(name) is module:
                del sys.modules[name]
        _require(not replaced, "private routing V2 namespace identity changed")

@dataclass(frozen=True)
class Operand:
    instruction_offset: int
    instruction_bytes: int
    offset: int
    kind: str
    role: str
    value: int

@dataclass(frozen=True)
class RoutingV2Bundle:
    emission: object
    lifecycle_bundle: object
    operand_inventory: tuple
    planned_hooks: tuple
    removed_highlow_rvas: tuple
    metadata_json: str

    def metadata(self):
        return json.loads(self.metadata_json)


def _plan(layout):
    """Exact value validation for the explicitly synthetic emission boundary."""
    profile, resolution = layout.profile, layout.resolution
    _require(type(profile) is str and profile in ("classic", "framed", "completehd", "modalwidgets")
             and type(resolution) is str and resolution in ("800x600", "1024x768", "1280x720", "1280x960",
                 "1366x768", "1920x1080", "2560x1440", "3440x1440", "3840x2160"),
             "fixed routing V2 selector required")
    rx, rw = layout.rx, layout.rw
    _require(all(type(n) is int for n in (rx.va, rx.rva, rx.size, rw.va, rw.rva, rw.size))
             and rx.va % 4096 == rw.va % 4096 == 0 and rx.va - rx.rva == 0x400000
             and rx.size == 0x40000 and rw.size == 0x10000 and rw.va == rx.va + rx.size
             and rw.rva == rx.rva + rx.size and rw.va + rw.size < 0x80000000
             and rx.characteristics == 0x60000020 and rw.characteristics == 0xC0000040
             and layout.battle_state_va == rw.va and layout.battle_state_bytes == 128
             and layout.protected_state_page_bytes == 4096
             and layout.provider_va == rw.va + 4096 and layout.provider_reservation_bytes == 61440
             and layout.provider_schema == "unpopulated_provider_reservation_v1",
             "fresh routing V2 allocation contract differs")
    inherited = [row for row in layout.protected_spans if row.role == "parent:.hdstate"]
    _require(len(inherited) == (1 if profile in ("completehd", "modalwidgets") else 0),
             "inherited modal allocation count differs")
    modal = None if not inherited else inherited[0].va
    if modal is not None:
        _require(inherited[0].size == 4096 and type(modal) is int and modal % 4096 == 0
                 and 0x400000 <= modal < rx.va and modal + 4096 <= rx.va,
                 "inherited modal page must remain separate and protected")
    wanted = {"future_rx_reservation": (rx.va,rx.size),
        "future_battle_state_page": (rw.va,4096),
        "future_unpopulated_provider_reservation": (rw.va+4096,61440)}
    rows=[(r.role,r.va,r.size) for r in layout.protected_spans if r.role.startswith("future_")]
    _require(len(rows) == len(wanted) and {role:(va,size) for role,va,size in rows} == wanted,
             "complete future routing protected spans differ")
    return dict(profile=profile, resolution=resolution, allocation_plan_only=True, battle_installed=False,
        rx=dict(va=rx.va, rva=rx.rva, virtual_reservation=rx.size, characteristics=rx.characteristics),
        rw=dict(va=rw.va, used_bytes=128, page_bytes=4096, page_offset=0,
                reservation_bytes=rw.size, characteristics=rw.characteristics)), modal

def _versioned_template(raw,template_module):
    """Exact whole-function edits; never call V1 with a spoofed plan."""
    _require(type(raw) is bytes and _sha(raw) == PINNED_SOURCES[TEMPLATE],
             "frozen routing template differs")
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name == "_emit_code"]
    _require(len(nodes) == 1,"one complete routing emitter required")
    source=ast.get_source_segment(raw.decode("utf-8"),nodes[0]); ledger=[]
    def replace(old,new,count=1):
        nonlocal source
        _require(source.count(old) == count,"versioned routing edit boundary differs")
        ledger.append((old,new,count)); source=source.replace(old,new)
    replace("def _emit_code(plan,","def _versioned_emit_code(layout,")
    start=source.index('    _require(type(plan) is dict')
    end=source.index('    base = (rx+len(code)+15)&~15',start)
    replace(source[start:end],'''    plan,derived_modal = _plan(layout)
    _require(modal_state_va == derived_modal,"separate inherited routing modal differs")
    profile,resolution = layout.profile,layout.resolution
    width,height = map(int,resolution.split("x"))
    rx,state = layout.rx.va,layout.rw.va
    code = lifecycle_emission.code
    _require(type(code) is bytes and lifecycle_emission.base_va == rx and
        lifecycle_emission.state_va == state and
        (lifecycle_emission.width,lifecycle_emission.height) == (width,height),
        "fresh canonical lifecycle geometry differs")
''')
    replace('regions = [(0x400000,plan["rx"]["rva"]),(rx,0x20000),\n'
            '                   (state if modal_state_va is None else modal_state_va,4096)]',
            'regions = [(0x400000,plan["rx"]["rva"]),(rx,262144),(state,65536)]\n'
            '        if modal_state_va is not None: regions += [(modal_state_va,4096)]')
    replace('    def blocks_snapshot(check,reject):','''    def exact_zero(pointer,size,reject,purpose):
        tag = "zero." + str(len(a.code))
        a.emit("60fc31c0b9"); a.u32(size//4)
        a.emit("bf"); address(pointer,purpose); a.emit("f3af")
        ne(tag+".reject"); a.emit("61"); a.branch("e9",tag+".done")
        a.label(tag+".reject"); a.emit("61"); a.branch("e9",reject)
        a.label(tag+".done")
    def protected_zero(reject):
        exact_zero(state+128,65536-128,reject,"empty routing V2 RW tail")
        if modal_state_va is not None:
            exact_zero(modal_state_va+128,4096-128,reject,"restrictive routing V2 inherited tail")
    def forward_result():
        put(0,STACK_BYTES+28)
        a.emit("81c4"); a.u32(STACK_BYTES); a.emit("619dc3")
    def blocks_snapshot(check,reject):''')
    replace('        for name,size,slot in (("physical",188,PHYSICAL_HEADER)',
            '        protected_zero(reject)\n'
            '        for name,size,slot in (("physical",188,PHYSICAL_HEADER)')
    replace('        a.label(name); save(); reject = name+".reject"','''        a.label(name); save(); reject = name+".reject"
        protected_zero(reject)
        cmp_abs(state,0,"virgin routing phase"); ne(name+".owned")
        exact_zero(state,128,reject,"complete virgin routing record")
        if modal_state_va is not None:
            exact_zero(modal_state_va,128,reject,"complete virgin inherited record")
        result(0)
        a.label(name+".owned")''')
    replace('        result(1); a.label(reject); result(0)',
            '        result(1); a.label(reject); result(2)')
    replace('    a.label("target.reject"); result(0)',
            '    a.label("target.reject"); forward_result()')
    replace('    result(1); a.label("compose.reject"); result(0)',
            '    result(1); a.label("compose.reject"); forward_result()')
    replace('        a.emit("892d"); address(RENDER,"native target MOV fallback")',
            '        a.emit("619d"); a.branch("e9","routing_unsafe")')
    replace('    code = a.finish()',
            '    a.label("routing_unsafe"); a.emit("0f0b")\n    code = a.finish()')
    replace('rx+0x20000','rx+0x40000')
    namespace=dict(template_module.__dict__); namespace["_plan"]=_plan
    exec(compile(source,str(ROOT/SOURCE)+"#pinned_routing_template","exec"),namespace)
    return namespace["_versioned_emit_code"],tuple(ledger)

def _emission_identity(out):
    return (out.base_va,out.state_va,out.width,out.height,out.code,out.entries,
        tuple((r.offset,r.kind,r.target,r.purpose) for r in out.relocations))

def _emit_code(layout,lifecycle_emission,*,template_source,template_module,
               lifecycle_module,lifecycle_template_source,lifecycle_template_module,
               assembler_module):
    """Explicit synthetic boundary; production obtains canonical inputs privately."""
    _plan(layout)
    expected=lifecycle_module._emit_code(layout,template_source=lifecycle_template_source,
        template_module=lifecycle_template_module,assembler_module=assembler_module)
    _require(_emission_identity(lifecycle_emission) == _emission_identity(expected),
             "complete canonical lifecycle bytes/ABI required")
    emitter,_=_versioned_template(template_source,template_module)
    inherited=next((r.va for r in layout.protected_spans if r.role == "parent:.hdstate"),None)
    base=(layout.rx.va+len(expected.code)+15)&~15
    parent_assembler=assembler_module._Assembler; relocation=assembler_module.Relocation
    class CompleteAssembler(parent_assembler):
        def finish(self):
            result=super().finish()
            for offset,label in self.fixups:
                self.relocations.append(relocation(offset,"rel32",self.base+self.labels[label],
                    "routing_v2_internal:"+label))
            return result
    isolated=types.SimpleNamespace(_Assembler=CompleteAssembler,Relocation=relocation,
        absolute_relocation_offsets=assembler_module.absolute_relocation_offsets)
    out=emitter(layout,lifecycle_emission,modal_state_va=inherited,assembler_module=isolated)
    _require(out.base_va == base and out.state_va == layout.rw.va and
        out.base_va+len(out.code) <= layout.rx.va+layout.rx.size,
        "routing V2 code exceeds fresh allocation")
    _require(tuple(name for name,_ in out.entries) == template_module.ENTRIES and
        len({va for _,va in out.entries}) == 6,"six routing entries required")
    assembler_module.absolute_relocation_offsets(out); _operand_inventory(out,layout)
    return out


def _operand_inventory(out,layout):
    """Decode the bounded authored dialect, including scalar operand roles.

    Every absolute memory operand and relative transfer needs exactly one
    relocation. Fixtures independently classify immediate addresses versus
    exact scalar roles/values; numeric VA resemblance is never a classifier.
    """
    _require(tuple(name for name,_ in out.entries) == ("check_owned_prepared","check_owned_bound",
        "target_hud","compose_chrome","initial_frame_target","initial_widgets_target") and
        len({va for _,va in out.entries}) == 6,"six typed routing entries required")
    code=out.code; cursor=0; records=[]; starts=set()
    declared={r.offset:r for r in out.relocations}
    _require(len(declared) == len(out.relocations),"duplicate routing operand")
    consumed=set()
    modal=next((r.va for r in layout.protected_spans if r.role == "parent:.hdstate"),None)
    memory_addresses={0x5202e0,0x511230,0x5199d8,0x526994,0x526990,0x532048,0x4ea4e8}
    memory_addresses.update(range(0x51d4c0,0x51d4c0+216,4))
    memory_addresses.update(range(layout.rw.va,layout.rw.va+128,4))
    if modal is not None: memory_addresses.update(range(modal,modal+128,4))
    while cursor < len(code):
        start=cursor; starts.add(start); fields=[]
        opcode=code[cursor]; cursor+=1
        if opcode in (0x9c,0x9d,0x60,0x61,0xfc,0xc3,0x40,0x48,0x4a):
            pass
        elif opcode == 0xf3:
            _require(cursor < len(code) and code[cursor] in (0xaf,0xa4),"routing REP dialect differs")
            cursor+=1
        elif 0xb8 <= opcode <= 0xbf or opcode == 0x3d:
            fields.append((cursor,"immediate")); cursor+=4
        elif opcode in (0xe8,0xe9):
            fields.append((cursor,"relative")); cursor+=4
        elif opcode == 0x0f:
            sub=code[cursor]; cursor+=1
            if sub != 0x0b:
                _require(sub in (0x82,0x83,0x84,0x85,0x87,0x88),"routing branch dialect differs")
                fields.append((cursor,"relative")); cursor+=4
        elif opcode in (0x81,0x83,0x8b,0x89,0x3b,0x39,0x85,0xf7,0xff,0x31,0x29):
            modrm=code[cursor]; cursor+=1
            mode,rm=modrm>>6,modrm&7
            if mode != 3 and rm == 4:
                sib=code[cursor]; cursor+=1
                if mode == 0 and sib&7 == 5:
                    fields.append((cursor,"memory_address")); cursor+=4
            if mode == 0 and rm == 5:
                fields.append((cursor,"memory_address")); cursor+=4
            elif mode == 1:
                records.append(Operand(start,0,cursor,"scalar8","address_displacement",code[cursor]))
                cursor+=1
            elif mode == 2:
                fields.append((cursor,"displacement")); cursor+=4
            if opcode == 0x81 or opcode == 0xf7 and (modrm>>3)&7 == 0:
                fields.append((cursor,"immediate")); cursor+=4
            elif opcode == 0x83:
                records.append(Operand(start,0,cursor,"scalar8","instruction_immediate",code[cursor]))
                cursor+=1
        else:
            raise ValueError("unknown routing instruction at "+hex(start)+": "+hex(opcode))
        _require(start < cursor <= len(code),"truncated routing instruction")
        for index in range(len(records)-1,-1,-1):
            row=records[index]
            if row.instruction_offset != start: break
            records[index]=Operand(start,cursor-start,row.offset,row.kind,row.role,row.value)
        for at,role in fields:
            value=struct.unpack_from("<I",code,at)[0]; row=declared.get(at)
            immediate_addresses=None
            if role == "immediate":
                if opcode == 0xbb:
                    immediate_addresses={0x400000,layout.rx.va,layout.rw.va}
                    if modal is not None: immediate_addresses.add(modal)
                elif opcode == 0xbf:
                    immediate_addresses={layout.rw.va,layout.rw.va+128}
                    if modal is not None: immediate_addresses.update((modal,modal+128))
                elif opcode == 0x3d:
                    immediate_addresses={0x51d4c0}
                elif opcode == 0x81:
                    modrm=code[start+1]
                    if modrm == 0x3d:
                        address=struct.unpack_from("<I",code,start+2)[0]
                        if address == 0x5199d8: immediate_addresses={0x42e8b0}
                        elif address == layout.rw.va+68: immediate_addresses={0x40ad40}
                        elif address == 0x51d4c0+0xb8: immediate_addresses={0x50eec4}
                    elif modrm>>6 == 2 and struct.unpack_from("<I",code,start+2)[0] == 0xb8:
                        immediate_addresses={0x50ee24}
                _require((row is not None) == (immediate_addresses is not None),
                         "routing immediate address/scalar role differs")
                if immediate_addresses is not None:
                    _require(value in immediate_addresses,"routing address immediate value differs")
            elif role == "memory_address":
                _require(value in memory_addresses,"routing fixed memory address differs")
                if opcode == 0x89:
                    _require(value == 0x511230,"routing write escaped render target")
            if role == "relative":
                _require(row is not None and row.kind == "rel32","missing routing relative operand")
                target=out.base_va+at+4+struct.unpack_from("<i",code,at)[0]
                _require(target == row.target,"routing relative target differs")
                if out.base_va <= target < out.base_va+len(code):
                    _require(row.purpose.startswith("routing_v2_internal:"),"untyped internal routing transfer")
                    kind="rel32"; typed="internal_"+("call" if opcode == 0xe8 else "branch")
                else:
                    _require(opcode == 0xe9 and row.purpose == "native target continuation" and
                        target in (0x42eb74,0x42ef77),"unexpected external routing transfer")
                    kind="rel32"; typed="native_continuation"
            elif row is not None:
                _require(row.kind == "abs32" and row.target == value and role != "displacement",
                         "routing absolute operand differs")
                kind="abs32"; target=value
                typed="memory_address" if role == "memory_address" else "address_immediate"
            else:
                _require(role != "memory_address","missing routing memory relocation")
                kind="scalar32"; target=value
                typed="address_displacement" if role == "displacement" else "instruction_immediate"
            records.append(Operand(start,cursor-start,at,kind,typed,target))
            if row is not None: consumed.add(at)
    _require(consumed == set(declared),"routing relocation is not an instruction operand")
    for row in records:
        if row.kind == "rel32" and row.role.startswith("internal"):
            _require(row.value-out.base_va in starts,"routing branch is not an instruction boundary")
    _require(all(va-out.base_va in starts for _,va in out.entries),"routing entry boundary differs")
    return tuple(sorted(records,key=lambda row:row.offset))


def _issue(original,profile,resolution):
    _require(type(original) is bytes and _sha(original) == BASE_SHA256,"exact original required")
    snapshot=_snapshot()
    with _modules(snapshot) as modules:
        life=modules[LIFECYCLE]._issue(original,profile,resolution)
        context=life.allocation_context; layout=context.layout; contract=life.metadata()
        old=modules[TEMPLATE]; clip=modules[CLIP]
        _require(contract["state_offsets"] == old.STATE and
            contract["source_hashes"][LIFECYCLE] == PINNED_SOURCES[LIFECYCLE],
            "canonical fresh lifecycle schema differs")
        _require(old._composition_rectangles(*map(int,resolution.split("x"))) ==
            modules[HUD].composition_rectangles(*map(int,resolution.split("x"))),
            "pinned routing chrome geometry differs")
        target_contract=old._parent_target_contract(original,profile,contract,clip)
        out=_emit_code(layout,life.emission,template_source=snapshot[TEMPLATE][0],
            template_module=old,lifecycle_module=modules[LIFECYCLE],
            lifecycle_template_source=snapshot[LIFE_TEMPLATE][0],
            lifecycle_template_module=modules[LIFE_TEMPLATE],assembler_module=clip)
        operands=_operand_inventory(out,layout); view=modules[CONTEXT]._parse(context.relayout_parent)
        hooks=[]; removed=[]
        for name,(va,raw) in old.SITES.items():
            before=bytes.fromhex(raw); at=view.file_offset(va-0x400000,len(before))
            _require(context.relayout_parent[at:at+len(before)] == before,
                     "routing whole old relayout bytes differ")
            target=dict(out.entries)[name]
            after=b"\xe9"+struct.pack("<i",target-va-5)+b"\x90"
            fields=tuple(sorted(va-0x400000+field for field in
                clip._original_highlow_fields(original,va,len(before))))
            _require(all(field in layout.highlow_rvas for field in fields),
                     "routing stolen HIGHLOW inventory differs")
            hooks.append((name,at,va,before,after,target,fields)); removed.extend(fields)
        _,ledger=_versioned_template(snapshot[TEMPLATE][0],old)
        metadata=dict(schema="clash95_battle_profile_routing_v2",profile=profile,resolution=resolution,
            original_sha256=BASE_SHA256,parent_candidate_sha256=_sha(context.parent),
            relayout_parent_sha256=_sha(context.relayout_parent),
            lifecycle_metadata_sha256=_sha(life.metadata_json.encode()),
            lifecycle_code_sha256=_sha(life.emission.code),validation_stage=layout.validation_stage,
            source_hashes=contract["source_hashes"] | {name:_sha(raw) for name,(raw,_) in snapshot.items()},
            code_va=out.base_va,code_bytes=len(out.code),code_sha256=_sha(out.code),
            rx_reservation_bytes=layout.rx.size,rw_reservation_bytes=layout.rw.size,
            rx_remaining_bytes=layout.rx.va+layout.rx.size-out.base_va-len(out.code),
            state_va=out.state_va,state_bytes=128,state_offsets=old.STATE,
            helper_local_frame_bytes=1280,zero_scan_extra_stack_bytes=32,
            maximum_added_helper_chain_bytes=2712,
            guard_statuses={"0":"exact virgin query denial; no Thread or dynamic reads",
                "1":"owned admission","2":"unknown/history/owned receipt loss"},
            initial_adapter_non1="restore incoming ABI then exact UD2; no native MOV fallback",
            unsafe_va=out.base_va+len(out.code)-2,
            new_rw_tail_policy="exact zero [state+128,state+65536); no providers",
            inherited_tail_policy="nonzero [modal+128,modal+4096) explicitly unsupported",
            provider_records_emitted=0,provider_capacity=None,
            writes_state=False,writes_headers=False,clears_physical=False,
            composition_rectangles=old._composition_rectangles(out.width,out.height),
            inherited_native_target_contract=target_contract,
            template_edit_inventory=[dict(old=a,new=b,count=c) for a,b,c in ledger],
            operand_inventory=[dict(instruction_offset=r.instruction_offset,
                instruction_bytes=r.instruction_bytes,offset=r.offset,kind=r.kind,
                role=r.role,value=r.value) for r in operands],
            emission_preparation_only=True,installed_hooks=[],
            transient_write_prevention_verified=False,cross_thread_immutability_verified=False,
            limitations=["Synthetic callbacks/byte-pattern pixels prove no native game or Windows rendering.",
                "Zero tails reject persisted changes, not transient or cross-thread writes.",
                "Nonzero inherited modal tail is unsupported; dynamic writer compatibility is unproved.",
                "UD2 is unsafe, not production cancellation, fatal closure or healthy fallback.",
                "Field/content/primitive/RLE/provider/input/camera/animation/dialog/results/quit and atomic installation remain open."],
            **{key:False for key in FALSE_CLAIMS})
    _unchanged(snapshot)
    return RoutingV2Bundle(out,life,operands,tuple(hooks),tuple(sorted(set(removed))),
        json.dumps(metadata,sort_keys=True,separators=(",",":"),allow_nan=False))


def _production_factory():
    from hashlib import sha256 as digest
    from pathlib import Path as SourcePath
    from types import ModuleType as SourceModule
    from uuid import uuid4 as unique_name
    from sys import modules as registry
    exact_type, exact_bytes, rejection = type, bytes, ValueError
    compile_source, execute_source = compile, exec
    path = SourcePath(__file__).absolute(); root = path.parents[2]
    if path != root / "src/patcher/battle_profile_routing_v2.py":
        raise rejection("canonical routing V2 producer required")

    def read():
        if path.resolve(strict=True) != path:
            raise rejection("canonical routing V2 source required")
        for item in (path, *path.parents):
            row = item.lstat()
            if item.is_symlink() or getattr(row,"st_file_attributes",0) & 0x400:
                raise rejection("routing V2 source reparse forbidden")
        before=path.stat(); raw=path.read_bytes(); after=path.stat()
        def stamp(row):
            return row.st_dev,row.st_ino,row.st_size,row.st_mtime_ns,getattr(row,"st_file_attributes",0)
        if stamp(before) != stamp(after) or len(raw) != after.st_size:
            raise rejection("routing V2 source changed while read")
        return raw,stamp(after)

    raw,stamp=read(); identity=digest(raw).hexdigest()
    name="_battle_routing_v2_issuer_"+unique_name().hex
    module=SourceModule(name);module.__file__=str(path)
    module.__loaded_source_sha256__=identity;module.__canonical_routing_v2_issuer__=True
    if registry.setdefault(name,module) is not module:
        raise rejection("canonical routing V2 issuer namespace occupied")
    try:
        execute_source(compile_source(raw,str(path),"exec"),module.__dict__)
        issuer=module.__dict__["_issue"]
    finally:
        if registry.get(name) is not module:
            raise rejection("canonical routing V2 issuer replaced")
        del registry[name]
    if read() != (raw,stamp):
        raise rejection("canonical routing V2 source changed during capture")
    original_digest="500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"

    def dispatch(original,profile,resolution):
        if exact_type(original) is not exact_bytes or digest(original).hexdigest() != original_digest:
            raise rejection("exact original required")
        current,receipt=read()
        if digest(current).hexdigest() != identity:
            raise rejection("captured routing V2 source differs")
        try:
            return issuer(original,profile,resolution)
        finally:
            if read() != (current,receipt):
                raise rejection("routing V2 source changed during dispatch")
    return dispatch

if not globals().get("__canonical_routing_v2_issuer__",False):
    emit_routing_v2 = _production_factory()
