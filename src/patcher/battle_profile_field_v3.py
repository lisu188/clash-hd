"""Fresh-address uninstalled battle field with exact invocation receipts.

All native callbacks and pixel proofs are models. No hooks, provider records,
installation, native cancellation, runtime or promotion are supplied here.
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
SOURCE = "src/patcher/battle_profile_field_v3.py"
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

def _require(condition, message):
    if not condition:
        raise ValueError(message)

def _sha(raw):
    return hashlib.sha256(raw).hexdigest()

def _read(path, root):
    _require(path.is_absolute() and path.is_relative_to(root) and path.resolve(strict=True) == path,
             "canonical field V3 source required")
    for item in (path, *path.parents):
        row = item.lstat()
        _require(not item.is_symlink() and not getattr(row, "st_file_attributes", 0) & 0x400,
                 "field V3 reparse path forbidden")
    before = path.stat(); data = path.read_bytes(); after = path.stat()
    stamp = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns,
                         getattr(row, "st_file_attributes", 0))
    _require(stamp(before) == stamp(after) and len(data) == after.st_size, "source changed while read")
    return data, stamp(after)

def _snapshot():
    snapshot = {name: _read(ROOT / name, ROOT) for name in (*PINNED_SOURCES, SOURCE)}
    _require(all(_sha(snapshot[name][0]) == digest for name, digest in PINNED_SOURCES.items()),
             "frozen field V3 source pin differs")
    _require(globals().get("__loaded_source_sha256__") == _sha(snapshot[SOURCE][0]),
             "privately loaded field V3 source required")
    return snapshot

def _unchanged(snapshot):
    _require(all(_read(ROOT / name, ROOT) == receipt for name, receipt in snapshot.items()),
             "field V3 source closure changed")

@contextmanager
def _modules(snapshot):
    prefix = "_battle_field_v3_" + uuid.uuid4().hex
    owned, modules = {}, {}
    try:
        for suffix in ("", ".src", ".src.patcher"):
            module = types.ModuleType(prefix + suffix)
            module.__path__ = []
            _require(sys.modules.setdefault(module.__name__, module) is module,
                     "private field V3 namespace occupied")
            owned[module.__name__] = module
            if suffix:
                parent, _, leaf = module.__name__.rpartition(".")
                setattr(sys.modules[parent], leaf, module)
        for name in (VIEWPORT,PE,CLIP,"src/patcher/framed_battle_viewport.py",
            "src/patcher/framed_battle_coordinates.py","src/patcher/framed_battle_field.py",
            "src/patcher/framed_modal_canvas.py",HUD,V1_CONTEXT,CONTEXT,LIFE_TEMPLATE,LIFECYCLE,ROUTE_TEMPLATE,ROUTING,FIELD_V1,TEMPLATE):
            full = prefix + "." + name.removesuffix(".py").replace("/", ".")
            module = types.ModuleType(full)
            module.__file__ = str(ROOT / name)
            module.__package__ = full.rpartition(".")[0]
            module.__loaded_source_sha256__ = _sha(snapshot[name][0])
            _require(sys.modules.setdefault(full, module) is module,
                     "private field V3 namespace occupied")
            owned[full] = module
            setattr(sys.modules[module.__package__], full.rpartition(".")[2], module)
            if name == LIFECYCLE: module.__canonical_lifecycle_v2_issuer__ = True
            if name == ROUTING: module.__canonical_routing_v2_issuer__ = True
            exec(compile(snapshot[name][0], module.__file__, "exec"), module.__dict__)
            modules[name] = module
        yield modules
    finally:
        replaced = any(sys.modules.get(name) is not module for name, module in owned.items())
        for name, module in reversed(tuple(owned.items())):
            if sys.modules.get(name) is module:
                del sys.modules[name]
        _require(not replaced, "private field V3 namespace identity changed")

@dataclass(frozen=True)
class Operand:
    instruction_offset: int
    instruction_bytes: int
    offset: int
    kind: str
    role: str
    value: int

@dataclass(frozen=True)
class FieldV3Bundle:
    emission: object
    routing_bundle: object
    operand_inventory: tuple
    tile_return_receipts: tuple
    metadata_json: str
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()

    def metadata(self):
        return json.loads(self.metadata_json)

def _plan(layout):
    """Exact value validation for the explicitly synthetic emission boundary."""
    profile, resolution = layout.profile, layout.resolution
    _require(type(profile) is str and profile in ("classic", "framed", "completehd", "modalwidgets")
             and type(resolution) is str and resolution in ("800x600", "1024x768", "1280x720", "1280x960",
                 "1366x768", "1920x1080", "2560x1440", "3440x1440", "3840x2160"),
             "fixed field V3 selector required")
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
             "fresh field V3 allocation contract differs")
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
    """Re-emit one complete frozen function through an exact edit ledger."""
    _require(type(raw) is bytes and _sha(raw) == PINNED_SOURCES[TEMPLATE],
             "frozen field V2 template differs")
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name == "_emit_code"]
    _require(len(nodes) == 1,"one complete field emitter required")
    source=ast.get_source_segment(raw.decode("utf-8"),nodes[0]); ledger=[]
    def replace(old,new,count=1):
        nonlocal source
        _require(source.count(old) == count,"versioned field edit boundary differs")
        ledger.append((old,new,count)); source=source.replace(old,new)
    replace("def _emit_code(plan,","def _versioned_emit_code(layout,")
    start=source.index('    _require(type(plan) is dict')
    end=source.index('    base = (routing_emission.base_va',start)
    replace(source[start:end],"""    plan,modal = _plan(layout)
    profile,resolution = layout.profile,layout.resolution
    width,height = map(int,resolution.split("x"))
    rx,state = layout.rx.va,layout.rw.va
    guard = dict(routing_emission.entries)["check_owned_bound"]
""")
    replace('    def admitted(reject):\n        transfer(guard,"genuine profile owned bound guard"); a.emit("83f801"); ne(reject)',"""    def admitted(reject,lost=None):
        transfer(guard,"genuine profile owned bound guard"); a.emit("83f801")
        if lost is None: ne(reject)
        else:
            tag = "admitted."+str(len(a.code))
            eq(tag); a.emit("85c0"); eq(reject); a.branch("e9",lost)
            a.label(tag)
""")
    replace('    def snapshot(check,reject):',"""    def exact_zero(pointer,size,reject,purpose):
        tag = "zero."+str(len(a.code))
        a.emit("60fc31c0b9"); a.u32(size//4)
        a.emit("bf"); address(pointer,purpose); a.emit("f3af")
        ne(tag+".reject"); a.emit("61"); a.branch("e9",tag+".done")
        a.label(tag+".reject"); a.emit("61"); a.branch("e9",reject)
        a.label(tag+".done")
    def protected_zero(reject):
        exact_zero(state+128,65536-128,reject,"empty field V3 RW tail")
        if modal is not None:
            exact_zero(modal+128,4096-128,reject,"restrictive field V3 inherited tail")
    def snapshot(check,reject):""")
    replace('        for key,count,slot in (("physical",188,PHYSICAL_HEADER)',"""        if check:
            for key,state_key in (("physical","physical"),("native","native"),("backend","saved_backend"),("world","battle")):
                get(0,P[key]); match(0,OWN+STATE[state_key]); ne(reject)
        protected_zero(reject)
        for key,count,slot in (("physical",188,PHYSICAL_HEADER)""")
    replace('    X,Y,V,ORIGIN,EXPECTED_RENDER = 1132,1136,1140,1144,1152',
            '    X,Y,V,ORIGIN,EXPECTED_RENDER = 1132,1136,1140,1144,1152\n    CONTROL_RECEIPT = 1156')
    replace('        if check:\n            for key,state_key',
            '        if check:\n            for index,slot in enumerate((X,Y,V,ORIGIN)):\n                get(0,slot); match(0,CONTROL_RECEIPT+index*4); ne(reject)\n            for key,state_key')
    replace('        a.label(name+".tile")',
            '        a.label(name+".tile")\n        for index,slot in enumerate((X,Y,V,ORIGIN)):\n            get(0,slot); put(0,CONTROL_RECEIPT+index*4)')
    replace('    def snapshot(check,reject):','    def snapshot(check,reject,fixed_only=False):')
    replace('        protected_zero(reject)\n        for key,count,slot',
            '        protected_zero(reject)\n        if fixed_only: return\n        for key,count,slot')
    replace('    private_call("check_invocation"); a.emit("83f801"); ne("same_invocation.reject")',
            '    snapshot(True,"same_invocation.reject",fixed_only=True)')
    replace('        admitted(reject); world()', '        admitted(reject,lost); world()')
    replace('        private_call("capture_invocation"); a.emit("83f801"); ne(reject)',
            '        private_call("capture_invocation"); a.emit("83f801"); ne(lost)')
    replace('    a.label("check_invocation")','    a.label("capture_invocation.reject"); a.emit("31c0c3")\n    a.label("check_invocation")')
    # CompleteAssembler declares every fixup; this frozen loop would duplicate
    # the private CALL rows. The new inventory types them from actual opcodes.
    replace('    for offset,name in private_calls:\n        a.relocations.append(assembler_module.Relocation(offset,"rel32",base+a.labels[name],\n            "private EBP-relative receipt helper "+name))','')
    replace('rx+0x20000','rx+0x40000')
    namespace=dict(template_module.__dict__); namespace["_plan"]=_plan
    exec(compile(source,str(ROOT/SOURCE)+"#pinned_field_template","exec"),namespace)
    return namespace["_versioned_emit_code"],tuple(ledger)

def _emission_identity(out):
    return (out.base_va,out.state_va,out.width,out.height,out.code,out.entries,
        tuple((r.offset,r.kind,r.target,r.purpose) for r in out.relocations))

def _emit_code(layout,lifecycle_emission,routing_emission,*,template_source,template_module,
               routing_module,routing_template_source,routing_template_module,
               lifecycle_module,lifecycle_template_source,lifecycle_template_module,
               assembler_module):
    """Explicit RAM fixture boundary; not production admission authority."""
    _plan(layout)
    expected=routing_module._emit_code(layout,lifecycle_emission,
        template_source=routing_template_source,template_module=routing_template_module,
        lifecycle_module=lifecycle_module,lifecycle_template_source=lifecycle_template_source,
        lifecycle_template_module=lifecycle_template_module,assembler_module=assembler_module)
    _require(_emission_identity(routing_emission) == _emission_identity(expected),
             "complete canonical routing bytes/ABI required")
    _require(template_module.STATE == routing_template_module.STATE and
        template_module.ENTRIES == ("visible_columns","clamp_scroll_x","screen_to_cell",
            "visible_cell","draw_full","draw_incremental") and template_module.STACK_BYTES == 1280,
        "frozen field ABI differs")
    emitter,_=_versioned_template(template_source,template_module)
    parent_assembler=assembler_module._Assembler; relocation=assembler_module.Relocation
    class CompleteAssembler(parent_assembler):
        def finish(self):
            result=super().finish()
            for offset,label in self.fixups:
                self.relocations.append(relocation(offset,"rel32",self.base+self.labels[label],
                    "field_v3_internal:"+label))
            return result
    isolated=types.SimpleNamespace(_Assembler=CompleteAssembler,Relocation=relocation,
        absolute_relocation_offsets=assembler_module.absolute_relocation_offsets)
    out=emitter(layout,routing_emission,assembler_module=isolated)
    _require(out.base_va == (expected.base_va+len(expected.code)+15)&~15 and
        out.state_va == layout.rw.va and out.base_va+len(out.code) <= layout.rx.va+layout.rx.size,
        "field V3 exceeds fresh prefix allocation")
    assembler_module.absolute_relocation_offsets(out); _operand_inventory(out,layout,routing_emission)
    _tile_receipts(out)
    return out

def _operand_inventory(out,layout,routing_emission):
    """Decode the bounded authored dialect, including scalar operand roles.

    Every absolute memory operand and relative transfer needs exactly one
    relocation. Fixtures independently classify immediate addresses versus
    exact scalar roles/values; numeric VA resemblance is never a classifier.
    """
    _require(tuple(name for name,_ in out.entries) == ("visible_columns","clamp_scroll_x","screen_to_cell","visible_cell","draw_full","draw_incremental") and
        len({va for _,va in out.entries}) == 6,"six typed field entries required")
    _require(tuple(name for name,_ in out.private_entries) == ("capture_invocation","check_invocation","same_invocation"),"three field receipt entries required")
    code=out.code; cursor=0; records=[]; starts=set()
    declared={r.offset:r for r in out.relocations}
    _require(len(declared) == len(out.relocations),"duplicate field operand")
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
            _require(cursor < len(code) and code[cursor] in (0xaf,0xa4),"field REP dialect differs")
            cursor+=1
        elif 0xb8 <= opcode <= 0xbf or opcode == 0x3d:
            fields.append((cursor,"immediate")); cursor+=4
        elif opcode in (0xe8,0xe9):
            fields.append((cursor,"relative")); cursor+=4
        elif opcode == 0x0f:
            sub=code[cursor]; cursor+=1
            if sub != 0x0b:
                _require(sub in (0x82,0x83,0x84,0x85,0x86,0x87,0x88,0x89,0x8c,0x8d),"field branch dialect differs")
                fields.append((cursor,"relative")); cursor+=4
        elif opcode in (0x81,0x83,0x8b,0x89,0x3b,0x39,0x85,0xf7,0xff,0x31,0x29,0x01,0x03,0x09,0xc1):
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
            elif opcode in (0x83,0xc1):
                records.append(Operand(start,0,cursor,"scalar8","instruction_immediate",code[cursor]))
                cursor+=1
        else:
            raise ValueError("unknown field instruction at "+hex(start)+": "+hex(opcode))
        _require(start < cursor <= len(code),"truncated field instruction")
        for index in range(len(records)-1,-1,-1):
            row=records[index]
            if row.instruction_offset != start: break
            records[index]=Operand(start,cursor-start,row.offset,row.kind,row.role,row.value)
        for at,role in fields:
            value=struct.unpack_from("<I",code,at)[0]; row=declared.get(at)
            immediate_addresses=None
            if role == "immediate":
                if opcode == 0xbf:
                    immediate_addresses={layout.rw.va+128}
                    if modal is not None: immediate_addresses.add(modal+128)
                _require((row is not None) == (immediate_addresses is not None),
                         "field immediate address/scalar role differs")
                if immediate_addresses is not None:
                    _require(value in immediate_addresses,"field address immediate value differs")
            elif role == "memory_address":
                _require(value in memory_addresses,"field fixed memory address differs")
                if opcode == 0x89:
                    _require(value == 0x511230,"field write escaped render target")
            if role == "relative":
                _require(row is not None and row.kind == "rel32","missing field relative operand")
                target=out.base_va+at+4+struct.unpack_from("<i",code,at)[0]
                _require(target == row.target,"field relative target differs")
                if out.base_va <= target < out.base_va+len(code):
                    _require(row.purpose.startswith("field_v3_internal:"),"untyped internal field transfer")
                    kind="rel32"; typed="internal_"+("call" if opcode == 0xe8 else "branch")
                else:
                    guard=dict(routing_emission.entries)["check_owned_bound"]
                    _require(opcode == 0xe8 and (target,row.purpose) in (
                        (guard,"genuine profile owned bound guard"),
                        (0x42ffb0,"authenticated native tactical tile")),
                        "unexpected external field transfer")
                    kind="rel32"; typed="routing_guard_call" if target == guard else "native_tile_call"
            elif row is not None:
                _require(row.kind == "abs32" and row.target == value and role != "displacement",
                         "field absolute operand differs")
                kind="abs32"; target=value
                typed="memory_address" if role == "memory_address" else "address_immediate"
            else:
                _require(role != "memory_address","missing field memory relocation")
                kind="scalar32"; target=value
                typed="address_displacement" if role == "displacement" else "instruction_immediate"
            records.append(Operand(start,cursor-start,at,kind,typed,target))
            if row is not None: consumed.add(at)
    _require(consumed == set(declared),"field relocation is not an instruction operand")
    for row in records:
        if row.kind == "rel32" and row.role.startswith("internal"):
            _require(row.value-out.base_va in starts,"field branch is not an instruction boundary")
    _require(all(va-out.base_va in starts for _,va in out.entries+out.private_entries),"field entry boundary differs")
    return tuple(sorted(records,key=lambda row:row.offset))

def _tile_receipts(out):
    """Derive two ordered Tile/post-CALL PCs from actual emitted operands."""
    entries=dict(out.entries); private=dict(out.private_entries); result=[]
    for row in sorted(out.relocations,key=lambda r:r.offset):
        if row.kind != "rel32" or row.target != 0x42ffb0: continue
        _require(row.purpose == "authenticated native tactical tile" and out.code[row.offset-1] == 0xe8,
                 "canonical native field Tile CALL required")
        pc=out.base_va+row.offset+4; at=pc-out.base_va
        mode=0 if entries["draw_full"] < pc < entries["draw_incremental"] else 1
        _require(mode == 0 or entries["draw_incremental"] < pc < private["capture_invocation"],
                 "Tile CALL outside field draw entry")
        _require(out.code[at:at+1] == b"\xe8" and len(out.code) >= at+5,
                 "post-Tile private CALL required")
        target=pc+5+struct.unpack_from("<i",out.code,at+1)[0]
        rows=[r for r in out.relocations if r.offset == at+1]
        _require(target == private["same_invocation"] and len(rows) == 1 and
            rows[0].kind == "rel32" and rows[0].target == target and
            rows[0].purpose == "field_v3_internal:same_invocation",
            "complete post-Tile private receipt CALL required")
        result.append((mode,pc,at,target))
    _require(tuple(row[0] for row in result) == (0,1),"two ordered actual Tile return receipts required")
    return tuple(result)

def _issue(original,profile,resolution):
    _require(type(original) is bytes and _sha(original) == BASE_SHA256,"exact original required")
    snapshot=_snapshot()
    with _modules(snapshot) as modules:
        route=modules[ROUTING]._issue(original,profile,resolution)
        life=route.lifecycle_bundle; context=life.allocation_context; layout=context.layout
        contract=route.metadata(); old=modules[TEMPLATE]; clip=modules[CLIP]
        _require(contract["state_offsets"] == old.STATE and
            contract["source_hashes"][ROUTING] == PINNED_SOURCES[ROUTING],
            "canonical fresh routing schema differs")
        _require(modules[FIELD_V1].NATIVE_SPANS == old.NATIVE_SPANS and
            modules[FIELD_V1].STATE == old.STATE,"frozen field native contract differs")
        native=old._authenticate_native(original,context.relayout_parent,clip)
        out=_emit_code(layout,life.emission,route.emission,template_source=snapshot[TEMPLATE][0],
            template_module=old,routing_module=modules[ROUTING],
            routing_template_source=snapshot[ROUTE_TEMPLATE][0],routing_template_module=modules[ROUTE_TEMPLATE],
            lifecycle_module=modules[LIFECYCLE],lifecycle_template_source=snapshot[LIFE_TEMPLATE][0],
            lifecycle_template_module=modules[LIFE_TEMPLATE],assembler_module=clip)
        operands=_operand_inventory(out,layout,route.emission); receipts=_tile_receipts(out)
        _,ledger=_versioned_template(snapshot[TEMPLATE][0],old)
        metadata=dict(schema="clash95_battle_profile_field_v3",profile=profile,resolution=resolution,
            original_sha256=BASE_SHA256,parent_candidate_sha256=_sha(context.parent),
            relayout_parent_sha256=_sha(context.relayout_parent),validation_stage=layout.validation_stage,
            routing_metadata_sha256=_sha(route.metadata_json.encode()),routing_code_sha256=_sha(route.emission.code),
            source_hashes=contract["source_hashes"] | {name:_sha(raw) for name,(raw,_) in snapshot.items()},
            code_va=out.base_va,code_bytes=len(out.code),code_sha256=_sha(out.code),
            rx_reservation_bytes=layout.rx.size,rw_reservation_bytes=layout.rw.size,
            prefix_extent_bytes=out.base_va+len(out.code)-layout.rx.va,
            prefix_rx_remaining_bytes=layout.rx.va+layout.rx.size-out.base_va-len(out.code),
            whole_chain_capacity_verified=False,state_va=out.state_va,state_bytes=128,state_offsets=old.STATE,
            helper_local_frame_bytes=1280,zero_scan_extra_stack_bytes=32,
            maximum_added_helper_chain_bytes=2680,
            helper_frame_base_register="EBP",private_receipt_entries=dict(out.private_entries),
            cache_slot_own_bindings={1104:4,1112:8,1120:72,1124:64},
            stack_control_receipt_offsets={1156:1132,1160:1136,1164:1140,1168:1144},
            modeled_control_receipt_rejection=True,
            field_frame_offsets=dict(owner=0,modal=128,physical_header=256,native_header=448,
                primary_header=640,backend_header=864,globals=1040,world_geometry=1080,
                physical=1104,native=1112,backend=1120,world=1124,x=1132,y=1136,
                visible=1140,origin=1144,expected_render=1152,control_receipt=1156),
            query_rejection=0xffffffff,draw_results={"0":"exact virgin denial or admitted off-field request before target publication",
                "1":"modeled complete draw","2":"unknown/history/owned/invocation loss; no fallback or unauthorized restore"},
            tile_return_receipts=[dict(mode=m,pc=pc,code_offset=at,post_call_target=target) for m,pc,at,target in receipts],
            new_rw_tail_policy="exact zero [state+128,state+65536); no providers",
            inherited_tail_policy="nonzero [modal+128,modal+4096) explicitly unsupported",
            provider_records_emitted=0,provider_capacity=None,native_spans=native,
            native_tile_va=old.NATIVE_TILE,native_tile_register_arguments=["EAX worldX","EDX worldY"],
            native_tile_checked_current_cell=False,native_local_control_integrity_verified=False,
            native_tile_disabled_clip_sprite_sites=[0x430035,0x4300f3,0x43024e,0x430349,0x4307aa,0x43080c,0x430991],
            native_tile_cell_clip_sprite_sites=[0x430733],native_unit_cell_clip_sprite_sites=[0x42fc1b],
            arena_intersection_verified=False,native_arena_clipping_verified=False,
            writes_state=False,writes_headers=False,clears_physical=False,
            emitted_direct_primary_cursor_present_calls=False,installed_hooks=[],
            native_callback_abi_verified=False,
            native_provider_rle_verified=False,native_cancellation_verified=False,
            transient_write_prevention_verified=False,cross_thread_immutability_verified=False,
            downstream_frozen_lease_compatible=False,downstream_frozen_continuation_compatible=False,
            invocation_order="fixed/globals/P/control/tails, fresh routing admission, repeated full receipt before cached reads",
            template_edit_inventory=[dict(old=a,new=b,count=c) for a,b,c in ledger],
            operand_inventory=[dict(instruction_offset=r.instruction_offset,instruction_bytes=r.instruction_bytes,
                offset=r.offset,kind=r.kind,role=r.role,value=r.value) for r in operands],
            emission_preparation_only=True,
            limitations=["Synthetic callbacks and byte-pattern pixels prove no original Tile/game/render execution.",
                "Old lease E8-only inventory, return descriptors and continuation post-CALL patches need versioned reconstruction.",
                "The bounded modeled control receipt is not full native frame/ABI integrity; Tile neighbors/unit/type/asset indices and RLE/provider lifetimes remain unproved.",
                "Zero tails reject persisted changes, not transient or cross-thread writes; inherited nonzero tail is unsupported.",
                "Receipt loss only stops helpers after return; no intra-Tile cancellation, fatal/quit closure or healthy fallback is emitted.",
                "Sprite arena clipping, clearing, composition/presentation, HUD/animation, camera/input/dialog/results and atomic installation remain open."],
            **{key:False for key in FALSE_CLAIMS})
    _unchanged(snapshot)
    return FieldV3Bundle(out,route,operands,receipts,
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
    if path != root / "src/patcher/battle_profile_field_v3.py":
        raise rejection("canonical field V3 producer required")

    def read():
        if path.resolve(strict=True) != path:
            raise rejection("canonical field V3 source required")
        for item in (path, *path.parents):
            row = item.lstat()
            if item.is_symlink() or getattr(row,"st_file_attributes",0) & 0x400:
                raise rejection("field V3 source reparse forbidden")
        before=path.stat(); raw=path.read_bytes(); after=path.stat()
        def stamp(row):
            return row.st_dev,row.st_ino,row.st_size,row.st_mtime_ns,getattr(row,"st_file_attributes",0)
        if stamp(before) != stamp(after) or len(raw) != after.st_size:
            raise rejection("field V3 source changed while read")
        return raw,stamp(after)

    raw,stamp=read(); identity=digest(raw).hexdigest()
    name="_battle_field_v3_issuer_"+unique_name().hex
    module=SourceModule(name);module.__file__=str(path)
    module.__loaded_source_sha256__=identity;module.__canonical_field_v3_issuer__=True
    if registry.setdefault(name,module) is not module:
        raise rejection("canonical field V3 issuer namespace occupied")
    try:
        execute_source(compile_source(raw,str(path),"exec"),module.__dict__)
        issuer=module.__dict__["_issue"]
    finally:
        if registry.get(name) is not module:
            raise rejection("canonical field V3 issuer replaced")
        del registry[name]
    if read() != (raw,stamp):
        raise rejection("canonical field V3 source changed during capture")
    original_digest="500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"

    def dispatch(original,profile,resolution):
        if exact_type(original) is not exact_bytes or digest(original).hexdigest() != original_digest:
            raise rejection("exact original required")
        current,receipt=read()
        if digest(current).hexdigest() != identity:
            raise rejection("captured field V3 source differs")
        try:
            return issuer(original,profile,resolution)
        finally:
            if read() != (current,receipt):
                raise rejection("field V3 source changed during dispatch")
    return dispatch

if not globals().get("__canonical_field_v3_issuer__",False):
    emit_field_v3 = _production_factory()
