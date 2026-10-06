"""Uninstalled stack-only battle lease and normal-return checks.

This preparatory component cannot interrupt native Tile/Unit continuations,
the next frozen V2 tile, or RLE/provider work before normal return. It never
installs hooks, changes owner pages, clears pixels, or grants acceptance.
"""
from __future__ import annotations

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
SOURCE = "src/patcher/battle_profile_stack_lease.py"
FIELD = "src/patcher/battle_profile_field_v2.py"
FIELD_V1 = "src/patcher/battle_profile_field.py"
ROUTING = "src/patcher/battle_profile_routing.py"
CONTEXT = "src/patcher/battle_profile_context.py"
PINNED_SOURCES = {
    FIELD: "673a2170f77dc143a1d62745bf5879f23163e9cbcffa3f5549123c4cc81f8cbf",
    FIELD_V1: "c329460fc7289d11ac10ddc33d26eb5ad158169ca976fee41ccd32fba6d97c88",
    ROUTING: "838d371bf837ab0098420e5589abc07d446a22bd6daa25ecab683e4725e25972",
    "src/patcher/battle_profile_lifecycle.py": "dccb907b09d002691cad679219942ac5a8ffcb2798af4c96b0b1768dbd9e9f44",
    CONTEXT: "be3bbca018c415895ba7e79e64862512f330297fb56b4d8321f8f6d378c38500",
    "src/patcher/partial_tile_clip.py": "92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad",
    "src/patcher/pe_extension.py": "4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27",
    "src/patcher/framed_viewport.py": "1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42",
    "src/patcher/framed_battle_viewport.py": "8673e36bd04ded2afc8cc3b9d7ff2fed4c48dae891fe289509b44a9070c23bc6",
    "src/patcher/framed_battle_coordinates.py": "b67900d7399e0ce807d88a261c97942598beebfc28e2d78774cd109098f95142",
    "src/patcher/framed_battle_field.py": "f690865e615db65d02e8c59b5c43e0cfbaa1e371dd6502441d16e0d270a7196d",
    "src/patcher/framed_modal_canvas.py": "567b025520184a99f1f4f44b23a879ef9c729dcf2917dfa03a277c018cb20054",
    "src/patcher/framed_battle_hud.py": "3a6cb61a2ec2fcd0fa9c52c09a96e11a9a2d9f75cac6e3a2e826d5caa98a3ee3",
}
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
LEASE_BYTES, HELPER_BYTES, FIELD_BYTES = 192, 512, 1280
TAG, SCHEMA = 0x534C4231, 1
ROOT_STACK_BOUND = 0x10000
STATE_ROOT, STATE_TID = 16, 20
THREAD_IAT = 0x4EA4E8
FAMILIES = ("tile","unit","adjacent","tracking_effect","charge_effect","sprite","line")
ARG_BYTES = dict(tile=0,unit=4,adjacent=0,tracking_effect=20,charge_effect=32,sprite=28,line=8)
DESCRIPTOR = dict(tag=0,schema=4,bytes=8,source_va=12,source_end=16,root_esp=20,
    owner_tid=24,field_entry_sp=28,field_return_pc=32,lease_entry_sp=36,mode=40,
    loss=44,leaf_status=48,leaves_called=52,leaves_returned=56,
    outer_return_pc=60,outer_saved_ebp=64)
TILE_UNIT_RETURNS = (0x4303B1,0x43041C,0x430491,0x4304F5,0x430531,
    0x43059B,0x43060F,0x43067E,0x4306E8,0x430AAA)
ADJACENT_UNIT_RETURNS = (0x42FCC4,0x42FD58,0x42FDF9,0x42FEFC,
    0x42FF20,0x42FF54,0x42FF75,0x42FFA4)
TILE_SPRITE_RETURNS = (0x430038,0x4300F6,0x430251,0x43034C,
    0x430736,0x4307AD,0x43080F,0x430994)
NATIVE_RET_ABI = ((0x43084C,0),(0x430B11,0),(0x42FA94,4),(0x42FEDC,0),
    (0x42FFAA,0),(0x40555B,20),(0x4055BC,32),(0x403D0E,28),
    (0x403D67,28),(0x40403A,8))
NATIVE_CALL_ABI = (
    *(('unit',pc,'tile',76,0x42F820,None) for pc in TILE_UNIT_RETURNS),
    *(('unit',pc,'adjacent',24,0x42F820,None) for pc in ADJACENT_UNIT_RETURNS),
    ('adjacent',0x4302DC,'tile',72,0x42FC30,None),
    ('tracking_effect',0x42FA7C,'unit',88,0x405510,None),
    ('tracking_effect',0x42FBBD,'unit',88,0x405510,None),
    ('tracking_effect',0x43087D,'tile',92,0x405510,None),
    ('charge_effect',0x42F932,'unit',100,0x405560,None),
    *(('sprite',pc,'tile',100,None,0x34) for pc in TILE_SPRITE_RETURNS),
    ('sprite',0x42FC1E,'unit',96,None,0x34),
    ('sprite',0x405555,'tracking_effect',48,None,0x34),
    ('sprite',0x4055B6,'charge_effect',60,None,0x34),
    ('line',0x430AD8,'tile',80,None,0x14),
    ('line',0x430B0A,'tile',80,None,0x14),
)

@dataclass(frozen=True)
class CodeEmission:
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

@dataclass(frozen=True)
class BattleProfileStackLeaseBundle:
    emission: CodeEmission
    field_bundle: object
    metadata_json: str
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()

    def metadata(self):
        return json.loads(self.metadata_json)

def _require(condition,message):
    if not condition:
        raise ValueError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _snapshot():
    _require(Path(__file__).resolve() == ROOT/SOURCE,"noncanonical field source")
    result = {}
    for name,digest in dict(PINNED_SOURCES,**{SOURCE:None}).items():
        path = ROOT/name
        _require(path.resolve(strict=True) == path and path.is_relative_to(ROOT),"noncanonical field dependency")
        before = path.stat(); data = path.read_bytes(); after = path.stat()
        stamp = lambda row: (row.st_dev,row.st_ino,row.st_size,row.st_mtime_ns)
        _require(stamp(before) == stamp(after) and (digest is None or _sha(data) == digest),
                 "pinned field source differs: "+name)
        result[name] = (data,stamp(after))
    return result


def _unchanged(snapshot):
    _require(_snapshot() == snapshot,"field source changed during emission")


@contextmanager
def _modules(snapshot):
    prefix = "_clash95_battle_stack_lease_"+uuid.uuid4().hex
    saved_path = list(sys.path)
    try:
        for suffix in ("",".src",".src.patcher"):
            module = types.ModuleType(prefix+suffix); module.__path__ = []
            sys.modules[module.__name__] = module
            if suffix:
                parent,_,leaf = module.__name__.rpartition(".")
                setattr(sys.modules[parent],leaf,module)
        result = {}
        for stem in ("framed_viewport","pe_extension","partial_tile_clip","framed_battle_viewport",
                     "framed_battle_coordinates","framed_battle_field","framed_modal_canvas",
                     "framed_battle_hud","battle_profile_context","battle_profile_lifecycle",
                     "battle_profile_routing","battle_profile_field","battle_profile_field_v2","battle_profile_stack_lease"):
            name = "src/patcher/"+stem+".py"; full = prefix+".src.patcher."+stem
            module = types.ModuleType(full)
            module.__file__,module.__package__ = str(ROOT/name),full.rpartition(".")[0]
            module.__loaded_source_sha256__ = _sha(snapshot[name][0])
            sys.modules[full] = module; setattr(sys.modules[module.__package__],stem,module)
            exec(compile(snapshot[name][0],module.__file__,"exec"),module.__dict__)
            result[name] = module
        yield result
    finally:
        for name in list(sys.modules):
            if name == prefix or name.startswith(prefix+"."):
                del sys.modules[name]
        sys.path[:] = saved_path


def _field_layout(plan,field):
    """Pure test boundary; the public producer reconstructs this independently."""
    _require(type(plan) is dict and plan.get("allocation_plan_only") is True and
             plan.get("battle_installed") is False,"uninstalled lease plan required")
    profile,resolution = plan["profile"],plan["resolution"]
    _require(profile in ("classic","framed","completehd","modalwidgets") and
             type(resolution) is str,"fixed lease selectors required")
    width,height = map(int,resolution.split("x"))
    _require(resolution == f"{width}x{height}" and (width,height) in
        ((800,600),(1024,768),(1280,720),(1280,960),(1366,768),(1920,1080),
         (2560,1440),(3440,1440),(3840,2160)),"canonical lease preset required")
    rx,state = plan["rx"]["va"],plan["rw"]["va"]
    _require(type(rx) is type(state) is int and rx%4096 == 0 and state%4 == 0 and
        plan["rx"]["virtual_reservation"] == 0x20000 and plan["rw"]["used_bytes"] == 128 and
        plan["rw"]["page_bytes"] == 4096 and plan["rx"]["characteristics"] == 0x60000020 and
        plan["rw"]["characteristics"] == 0xC0000040 and
        rx-plan["rx"]["rva"] == 0x400000,"unchanged lease allocation required")
    _require((profile in ("classic","framed") and state == rx+0x20000 and
              plan["rw"]["page_offset"] == 0 and plan["rw"]["allocation"] == "fresh_zero_page") or
             (profile in ("completehd","modalwidgets") and (state-256)%4096 == 0 and
              plan["rw"]["page_offset"] == 256 and
              plan["rw"]["allocation"] == "reserved_existing_modal_page"),"lease state ownership differs")
    _require(type(field.code) is bytes and 0 < len(field.code) < 0x20000 and
        rx <= field.base_va and field.base_va%16 == 0 and
        field.base_va+len(field.code) < rx+0x20000 and field.state_va == state and
        (field.width,field.height) == (width,height) and type(field.entries) is tuple and
        type(field.private_entries) is tuple,"matching immutable field emission required")
    names = ("visible_columns","clamp_scroll_x","screen_to_cell","visible_cell","draw_full","draw_incremental")
    entries,private = dict(field.entries),dict(field.private_entries)
    _require(tuple(entries) == names and len(entries) == len(field.entries) == 6 and tuple(private) ==
        ("capture_invocation","check_invocation","same_invocation") and len(private) == len(field.private_entries) == 3 and
        all(type(v) is int and field.base_va <= v < field.base_va+len(field.code)
            for v in list(entries.values())+list(private.values())),"canonical field entry layout required")
    prefix = bytes.fromhex("9c60fc81ec0005000089e5")
    for name in names:
        offset = entries[name]-field.base_va
        _require(field.code[offset:offset+len(prefix)] == prefix,"canonical1280B field frame differs")
    returns = []
    offsets = set()
    for row in field.relocations:
        _require(row.offset not in offsets and 0 <= row.offset <= len(field.code)-4,
                 "field relocation inventory differs")
        offsets.add(row.offset)
        if row.kind == "abs32":
            _require(struct.unpack_from("<I",field.code,row.offset)[0] == row.target,
                     "field absolute relocation differs")
        else:
            _require(row.kind == "rel32" and row.offset > 0 and field.code[row.offset-1] == 0xE8 and
                field.base_va+row.offset+4+struct.unpack_from("<i",field.code,row.offset)[0] == row.target,
                "field call relocation differs")
            if row.target == 0x42FFB0:
                pc = field.base_va+row.offset+4
                mode = 0 if entries["draw_full"] < pc < entries["draw_incremental"] else 1
                _require((mode == 0 or entries["draw_incremental"] < pc < private["capture_invocation"]) and
                         row.purpose == "authenticated native tactical tile","canonical field tile CALL required")
                returns.append((mode,pc))
    _require(tuple(sorted(returns)) == tuple(returns) and tuple(mode for mode,_ in returns) == (0,1),
             "exactly two canonical field tile CALLs required")
    return rx,state,width,height,entries,private,tuple(returns)


def _emit_code(plan,field_emission,*,assembler_module):
    """Uninstalled preparation. Native continuation cancellation is NOT emitted.

    check_* uses the named native entry ABI and returns EAX0/1. The guarded
    sprite/line leaves preserve native EAX and flags after normal completion;
    leaf_status/loss in the owning stack descriptor are the separate receipt.
    Unknown ancestry returns EAX0 before calling the native primitive.
    """
    rx,state,width,height,fields,field_private,field_pcs = _field_layout(plan,field_emission)
    base = (field_emission.base_va+len(field_emission.code)+15)&~15
    a = assembler_module._Assembler(base)
    abs_fixups,private_calls = [],[]
    # Native entry S is captured from the helper's own ABI frame, not a caller VA.
    NATIVE_S,FIELD_EBP,LEASE_EBP,ROOT_ESP,MODE = 200,204,208,212,216
    KIND,ANCESTORS,ANCESTOR_ROWS = 220,224,232
    TILE_SAVED_EBP = 312
    public_names = ("leased_draw_full","leased_draw_incremental")+tuple("check_"+f for f in FAMILIES)+(
        "guarded_sprite","guarded_line")
    private_names = ("discover_and_check","check_fixed_receipt")
    def immediate(value): a.u32(value)
    def address(value,purpose): a.absolute(value,purpose)
    def movi(reg,value): a.emit(f"{0xB8+reg:02x}"); immediate(value)
    def movaddr(reg,label,purpose):
        a.emit(f"{0xB8+reg:02x}"); at=len(a.code); a.u32(0); abs_fixups.append((at,label,purpose))
    def cmpi(reg,value): a.emit(f"81{0xF8+reg:02x}"); immediate(value)
    def cmpaddr(reg,value,purpose):
        a.emit(f"81{0xF8+reg:02x}"); address(value,purpose)
    def cmplabel(reg,label,purpose):
        a.emit(f"81{0xF8+reg:02x}"); at=len(a.code); a.u32(0); abs_fixups.append((at,label,purpose))
    def memory(op,reg,base_reg,offset):
        a.emit(op+f"{0x80|(reg<<3)|base_reg:02x}")
        if base_reg == 4: a.emit("24")
        a.u32(offset)
    def get(reg,offset): memory("8b",reg,5,offset)
    def put(reg,offset): memory("89",reg,5,offset)
    def mem(reg,base_reg,offset=0): memory("8b",reg,base_reg,offset)
    def store(reg,base_reg,offset): memory("89",reg,base_reg,offset)
    def local_cmp(reg,offset): memory("3b",reg,5,offset)
    def read(reg,va,purpose):
        a.emit("8b"+f"{5|(reg<<3):02x}"); address(va,purpose)
    def branch(op,label): a.branch(op,label)
    def ne(label): branch("0f85",label)
    def eq(label): branch("0f84",label)
    def call(target,purpose):
        a.emit("e8"); at=len(a.code)
        a.relocations.append(assembler_module.Relocation(at,"rel32",target,purpose))
        a.u32(target-base-at-4)
    def own_call(label):
        a.emit("e8"); at=len(a.code); a.u32(0)
        a.fixups.append((at,label)); private_calls.append((at,label))
    def save(name,count):
        a.label(name); a.emit("9c60fc81ec"); a.u32(count); a.emit("89e5")
    def finish(count,pop_bytes=0,value=None):
        if value is not None: movi(0,value); put(0,count+28)
        a.emit("81c4"); a.u32(count); a.emit("619d")
        if pop_bytes: a.emit("c2"); a.emit(struct.pack("<H",pop_bytes).hex())
        else: a.emit("c3")
    def add(reg,value): a.emit(f"81{0xC0+reg:02x}"); a.u32(value)
    def extent(reg,count,reject,root_offset=ROOT_ESP):
        # Every ancestor interval is validated before dereferencing that interval.
        a.emit(f"f7{0xC0+reg:02x}03000000"); ne(reject)
        get(2,root_offset); a.emit("89d1"); add(1,-ROOT_STACK_BOUND)
        a.emit(f"39{0xC8+reg:02x}"); branch("0f82",reject)  # reg >= root-bound
        a.emit(f"89{0xC0|(reg<<3):02x}"); add(0,count); branch("0f82",reject)
        a.emit("39d0"); branch("0f87",reject)
    def match_returns(reg,values,label):
        for value in values: cmpaddr(reg,value,"fixed native ancestry returnPC"); eq(label)
    def capture_return(reject):
        mem(0,7,0); get(1,ANCESTORS); cmpi(1,5); branch("0f83",reject)
        # Five maximum fixed family frames; address and exact PC are retained.
        a.emit("89bccd"); a.u32(ANCESTOR_ROWS)
        a.emit("8984cd"); a.u32(ANCESTOR_ROWS+4)
        add(1,1); put(1,ANCESTORS)
    def copy_descriptor(check,reject):
        get(7,LEASE_EBP)
        for offset in range(0,LEASE_BYTES,4):
            mem(0,7,offset)
            if check: local_cmp(0,offset); ne(reject)
            else: put(0,offset)
    def field_receipt(reject):
        # The authenticated V2 frame is the receipt captured after its genuine
        # bound guard. This helper performs no Thread callback itself.
        a.emit("55"); get(5,FIELD_EBP)
        call(field_private["check_invocation"],"private authenticated V2 complete receipt")
        a.emit("5d83f801"); ne(reject)

    for mode,name in enumerate(public_names[:2]):
        save(name,LEASE_BYTES)
        # Genuine canonical V2 producer owns admission and the1280B receipt.
        # The new frame holds only a source-bound lease and separate status.
        for offset in range(0,LEASE_BYTES,4): movi(0,0); put(0,offset)
        for key,value in (("tag",TAG),("schema",SCHEMA),("bytes",LEASE_BYTES),("mode",mode)):
            movi(0,value); put(0,DESCRIPTOR[key])
        movi(0,base); a.relocations.append(assembler_module.Relocation(len(a.code)-4,"abs32",base,"lease source VA")); put(0,12)
        movaddr(0,"code_end","lease source end"); put(0,16)
        read(0,state+STATE_ROOT,"lease root stack"); put(0,20)
        a.emit("a903000000"); ne(name+".reject")
        cmpi(0,ROOT_STACK_BOUND); branch("0f86",name+".reject")
        cmpi(0,0x7FFF0000); branch("0f83",name+".reject")
        a.emit("89ef"); extent(7,LEASE_BYTES+40,name+".reject",root_offset=20)
        read(0,state+STATE_TID,"lease owning thread"); put(0,24)
        a.emit("89e8"); add(0,-4); put(0,28)
        movaddr(0,name+".field_return","fixed leased field returnPC"); put(0,32)
        a.emit("89e8"); add(0,LEASE_BYTES+36); put(0,36)
        get(0,LEASE_BYTES+36); put(0,60)
        get(0,LEASE_BYTES+8); put(0,64)
        for reg,slot in ((0,28),(1,24),(2,20),(3,16),(6,4),(7,0)):
            get(reg,LEASE_BYTES+slot)
        call(fields["draw_full" if mode == 0 else "draw_incremental"],"fixed versioned field entry")
        a.label(name+".field_return")
        put(0,LEASE_BYTES+28)
        get(1,44); a.emit("85c9"); eq(name+".done")
        movi(0,2); put(0,LEASE_BYTES+28)
        a.label(name+".done"); finish(LEASE_BYTES)
        a.label(name+".reject"); finish(LEASE_BYTES,value=0)

    for family in FAMILIES:
        name="check_"+family; save(name,HELPER_BYTES)
        a.emit("89e8"); add(0,HELPER_BYTES+36); put(0,NATIVE_S)
        movi(0,FAMILIES.index(family)); put(0,KIND)
        own_call("discover_and_check")
        put(0,HELPER_BYTES+28); finish(HELPER_BYTES,ARG_BYTES[family])

    for family,target in (("sprite",0x402E80),("line",0x403F70)):
        name="guarded_"+family; save(name,HELPER_BYTES)
        a.emit("89e8"); add(0,HELPER_BYTES+36); put(0,NATIVE_S)
        movi(0,FAMILIES.index(family)); put(0,KIND)
        own_call("discover_and_check"); a.emit("83f801"); ne(name+".reject")
        get(7,LEASE_EBP)
        mem(0,7,52); add(0,1); store(0,7,52); put(0,52)
        movi(0,0); store(0,7,48); put(0,48)
        get(7,NATIVE_S)
        for offset in range(ARG_BYTES[family],0,-4):
            a.emit("ffb7"); a.u32(offset)
        for reg,slot in ((0,28),(1,24),(2,20),(3,16),(6,4),(7,0)):
            get(reg,HELPER_BYTES+slot)
        a.emit("fc"); call(target,"unchanged native primitive normal-return call")
        # Capture actual callee outputs/flags, retaining the caller's EBP.
        a.emit("9c60")
        for slot in (0,4,16,20,24,28,32):
            mem(0,4,slot); put(0,HELPER_BYTES+slot)
        a.emit("83c424")
        get(7,LEASE_EBP)
        # Inspect the exact pre-call receipt before recording the normal return;
        # a native callback cannot have its forged counters silently repaired.
        copy_descriptor(True,name+".lost")
        mem(0,7,56); add(0,1); store(0,7,56); put(0,56)
        own_call("discover_and_check"); a.emit("83f801"); ne(name+".lost")
        get(7,LEASE_EBP); movi(0,1); store(0,7,48)
        finish(HELPER_BYTES,ARG_BYTES[family])
        a.label(name+".lost")
        get(7,LEASE_EBP); movi(0,2); store(0,7,44); store(0,7,48)
        finish(HELPER_BYTES,ARG_BYTES[family])
        a.label(name+".reject"); finish(HELPER_BYTES,ARG_BYTES[family],0)

    a.label("discover_and_check")
    reject="discover.reject"
    read(0,state,"fixed lease owner phase"); cmpi(0,2); ne(reject)
    read(0,state+36,"fixed lease owner fault"); a.emit("85c0"); ne(reject)
    read(0,state+STATE_ROOT,"fixed lease root stack"); put(0,ROOT_ESP)
    a.emit("a903000000"); ne(reject)
    cmpi(0,ROOT_STACK_BOUND); branch("0f86",reject)
    cmpi(0,0x7FFF0000); branch("0f83",reject)
    # Own512B locals, intrinsic saved registers/flags and the largest36B
    # normal-return output save all belong to this bounded live stack.
    a.emit("89ef"); add(7,-36); extent(7,HELPER_BYTES+76,reject)
    get(7,NATIVE_S); extent(7,4,reject)
    movi(0,0); put(0,ANCESTORS)
    get(0,KIND)
    for number,family in enumerate(FAMILIES): cmpi(0,number); eq("ancestry."+family)
    branch("e9",reject)
    a.label("ancestry.sprite")
    extent(7,32,reject); capture_return(reject)
    match_returns(0,TILE_SPRITE_RETURNS,"sprite.tile")
    cmpaddr(0,0x42FC1E,"fixed unit sprite returnPC"); eq("sprite.unit")
    cmpaddr(0,0x405555,"fixed tracking sprite returnPC"); eq("sprite.tracking")
    cmpaddr(0,0x4055B6,"fixed charge sprite returnPC"); eq("sprite.charge")
    branch("e9",reject)
    for label,delta,family in (("sprite.tile",100,"tile"),("sprite.unit",96,"unit"),
                              ("sprite.tracking",48,"tracking_effect"),("sprite.charge",60,"charge_effect")):
        a.label(label); add(7,delta); branch("e9","ancestry."+family)
    a.label("ancestry.line")
    extent(7,12,reject); capture_return(reject)
    match_returns(0,(0x430AD8,0x430B0A),"line.tile"); branch("e9",reject)
    a.label("line.tile"); add(7,80); branch("e9","ancestry.tile")
    a.label("ancestry.tracking_effect")
    extent(7,24,reject); capture_return(reject)
    match_returns(0,(0x42FA7C,0x42FBBD),"tracking.unit")
    cmpaddr(0,0x43087D,"fixed tile tracking returnPC"); ne(reject)
    add(7,92); branch("e9","ancestry.tile")
    a.label("tracking.unit"); add(7,88); branch("e9","ancestry.unit")
    a.label("ancestry.charge_effect")
    extent(7,36,reject); capture_return(reject)
    cmpaddr(0,0x42F932,"fixed unit charge returnPC"); ne(reject)
    add(7,100); branch("e9","ancestry.unit")
    a.label("ancestry.unit")
    extent(7,8,reject); capture_return(reject)
    match_returns(0,TILE_UNIT_RETURNS,"unit.tile")
    match_returns(0,ADJACENT_UNIT_RETURNS,"unit.adjacent"); branch("e9",reject)
    a.label("unit.tile"); add(7,76); branch("e9","ancestry.tile")
    a.label("unit.adjacent"); add(7,24); branch("e9","ancestry.adjacent")
    a.label("ancestry.adjacent")
    extent(7,4,reject); capture_return(reject)
    cmpaddr(0,0x4302DC,"fixed tile adjacent returnPC"); ne(reject)
    add(7,72); branch("e9","ancestry.tile")
    a.label("ancestry.tile")
    extent(7,4,reject); capture_return(reject)
    cmpaddr(0,field_pcs[0][1],"fixed full field tile returnPC"); eq("tile.full")
    cmpaddr(0,field_pcs[1][1],"fixed incremental field tile returnPC"); ne(reject)
    movi(0,1); branch("e9","tile.mode")
    a.label("tile.full"); movi(0,0)
    a.label("tile.mode"); put(0,MODE)
    add(7,4); put(7,FIELD_EBP); extent(7,FIELD_BYTES+40,reject)
    get(0,KIND); a.emit("85c0"); eq("tile.entry_saved_ebp")
    add(7,-24); branch("e9","tile.saved_ebp")
    a.label("tile.entry_saved_ebp")
    # Entry validation precedes native Tile's prologue. The intrinsic saved
    # caller EBP in this helper's PUSHAD frame replaces the not-yet-live native
    # TileS-20 slot, which that same PUSHAD would otherwise overwrite.
    a.emit("89ef"); add(7,HELPER_BYTES+8)
    a.label("tile.saved_ebp"); extent(7,24,reject)
    put(7,TILE_SAVED_EBP); mem(0,7,0); local_cmp(0,FIELD_EBP); ne(reject)
    get(7,FIELD_EBP)
    mem(0,7,FIELD_BYTES+8); put(0,LEASE_EBP)
    a.emit("89f9"); add(1,FIELD_BYTES+40); a.emit("39c8"); ne(reject)
    a.emit("89c7"); extent(7,LEASE_BYTES+40,reject)
    for key,value in (("tag",TAG),("schema",SCHEMA),("bytes",LEASE_BYTES)):
        mem(0,7,DESCRIPTOR[key]); cmpi(0,value); ne(reject)
    mem(0,7,12); cmpaddr(0,base,"fixed lease source VA"); ne(reject)
    mem(0,7,16); cmplabel(0,"code_end","fixed lease source end"); ne(reject)
    mem(0,7,20); local_cmp(0,ROOT_ESP); ne(reject)
    get(6,FIELD_EBP); mem(1,6,STATE_ROOT); a.emit("39c8"); ne(reject)
    mem(0,7,24); mem(1,6,STATE_TID); a.emit("39c8"); ne(reject)
    read(1,state+STATE_TID,"fixed lease owning thread"); a.emit("39c8"); ne(reject)
    a.emit("85c0"); eq(reject)
    mem(0,7,28); a.emit("89f1"); add(1,FIELD_BYTES+36); a.emit("39c8"); ne(reject)
    mem(0,7,36); a.emit("89f9"); add(1,LEASE_BYTES+36); a.emit("39c8"); ne(reject)
    mem(0,7,60); mem(1,7,LEASE_BYTES+36); a.emit("39c8"); ne(reject)
    mem(0,7,64); mem(1,7,LEASE_BYTES+8); a.emit("39c8"); ne(reject)
    mem(0,7,40); local_cmp(0,MODE); ne(reject)
    a.emit("85c0"); eq("descriptor.full")
    movaddr(1,"leased_draw_incremental.field_return","fixed incremental lease returnPC")
    branch("e9","descriptor.return")
    a.label("descriptor.full"); movaddr(1,"leased_draw_full.field_return","fixed full lease returnPC")
    a.label("descriptor.return")
    mem(0,7,32); a.emit("39c8"); ne(reject)
    mem(0,6,FIELD_BYTES+36); a.emit("39c8"); ne(reject)
    mem(0,7,44); a.emit("85c0"); ne(reject)
    mem(0,7,52); mem(1,7,56); a.emit("39c8"); ne(reject)
    cmpi(0,0x10000); branch("0f83",reject)
    mem(0,7,48); cmpi(0,1); branch("0f87",reject)
    for offset in range(68,LEASE_BYTES,4): mem(0,7,offset); a.emit("85c0"); ne(reject)
    copy_descriptor(False,reject)
    # Before asking ThreadId, compare only fixed authorities. A native callee
    # may have changed the actual thread and invalidated cached heap objects;
    # the full V2 receipt therefore belongs AFTER the thread/control checks.
    own_call("check_fixed_receipt"); a.emit("83f801"); ne(reject)
    a.emit("fcff15"); address(THREAD_IAT,"fixed native owning thread callback")
    local_cmp(0,24); ne(reject)
    # Descriptor plus fixed root/TID receipts precede all following cached reads.
    read(0,state+STATE_ROOT,"post-thread fixed lease root"); local_cmp(0,20); ne(reject)
    read(0,state+STATE_TID,"post-thread fixed lease thread"); local_cmp(0,24); ne(reject)
    copy_descriptor(True,reject)
    get(7,LEASE_EBP)
    mem(0,7,LEASE_BYTES+36); local_cmp(0,60); ne(reject)
    mem(0,7,LEASE_BYTES+8); local_cmp(0,64); ne(reject)
    get(7,FIELD_EBP)
    mem(0,7,FIELD_BYTES+36); local_cmp(0,32); ne(reject)
    mem(0,7,FIELD_BYTES+8); local_cmp(0,LEASE_EBP); ne(reject)
    get(7,TILE_SAVED_EBP); extent(7,4,reject)
    mem(0,7,0); local_cmp(0,FIELD_EBP); ne(reject)
    for number in range(5):
        get(0,ANCESTORS); cmpi(0,number); branch("0f86",f"ancestors.done.{number}")
        get(7,ANCESTOR_ROWS+8*number); extent(7,4,reject)
        mem(0,7,0); local_cmp(0,ANCESTOR_ROWS+8*number+4); ne(reject)
        a.label(f"ancestors.done.{number}")
    field_receipt(reject)
    movi(0,1); a.emit("c3")
    a.label(reject); a.emit("31c0c3")
    a.label("check_fixed_receipt")
    get(6,FIELD_EBP)
    fixed=((state,128,0),(0x51D4C0,216,640))
    if plan['profile'] not in ('classic','framed'): fixed+=((state-256,128,128),)
    for pointer,count,slot in fixed:
        for offset in range(0,count,4):
            read(0,pointer+offset,"pinned V2 fixed receipt before thread")
            memory("3b",0,6,slot+offset); ne("fixed.reject")
    for number,pointer in enumerate((0x5202E0,0x511230,0x5199D8,0x526994,0x526990,0x532048,THREAD_IAT)):
        read(0,pointer,"pinned V2 fixed global before thread")
        memory("3b",0,6,1152 if pointer == 0x511230 else 1040+4*number); ne("fixed.reject")
    movi(0,1); a.emit("c3")
    a.label("fixed.reject"); a.emit("31c0c3")
    a.label("code_end")
    code=bytearray(a.finish())
    for offset,label,purpose in abs_fixups:
        value=base+a.labels[label]; struct.pack_into("<I",code,offset,value)
        a.relocations.append(assembler_module.Relocation(offset,"abs32",value,purpose))
    for offset,label in private_calls:
        a.relocations.append(assembler_module.Relocation(offset,"rel32",base+a.labels[label],"private stack lease helper "+label))
    _require(base+len(code) <= rx+0x20000,"lease code exceeds unchanged RX reservation")
    emission=CodeEmission(base,state,bytes(code),tuple((name,base+a.labels[name]) for name in public_names),
        tuple(a.relocations),width,height,tuple((name,base+a.labels[name]) for name in private_names),
        field_pcs,tuple((mode,base+a.labels[name+".field_return"]) for mode,name in enumerate(public_names[:2])))
    assembler_module.absolute_relocation_offsets(emission)
    return emission


def _authenticate_native_abi(original,candidate,clip):
    for image in (original,candidate):
        for va,pop in NATIVE_RET_ABI:
            count=3 if pop else 1; at=clip.file_offset(image,va,count)
            expected=b"\xC2"+struct.pack("<H",pop) if pop else b"\xC3"
            _require(image[at:at+count] == expected,"exact native RET ABI differs")
        for family,pc,parent,delta,target,slot in NATIVE_CALL_ABI:
            count=5 if target is not None else 3
            at=clip.file_offset(image,pc-count,count); raw=image[at:at+count]
            if target is not None:
                _require(len(raw) == 5 and raw[0] == 0xE8 and
                    pc+struct.unpack_from('<i',raw,1)[0] == target,"exact native direct CALL ABI differs")
            else:
                _require(len(raw) == 3 and raw[0] == 0xFF and raw[1]&0xF8 == 0x50 and raw[2] == slot,
                         "exact native virtual CALL ABI differs")
    return dict(returns=[dict(va=va,stack_pop_bytes=pop) for va,pop in NATIVE_RET_ABI],
        calls=[dict(family=family,return_pc=pc,parent_family=parent,parent_entry_sp_delta=delta,
                    direct_target_va=target,vtable_slot=slot)
               for family,pc,parent,delta,target,slot in NATIVE_CALL_ABI])


def _emit_authenticated(original,profile,resolution):
    _require(type(original) is bytes and _sha(original) == BASE_SHA256,"exact lease original required")
    snapshot=_snapshot()
    _require(globals().get("__loaded_source_sha256__") == _sha(snapshot[SOURCE][0]),"private lease producer required")
    with _modules(snapshot) as modules:
        field=modules[FIELD].emit_battle_profile_field_v2(original,profile,resolution)
        metadata=field.metadata(); plan=metadata["allocation_plan"]
        context=modules[CONTEXT].build_parent_context(original,profile,resolution)
        _require(context.allocation_plan() == plan and metadata["helper_stack_snapshot_bytes"] == FIELD_BYTES and
            metadata["source_hashes"][FIELD] == PINNED_SOURCES[FIELD],"exact canonical field producer required")
        clip=modules["src/patcher/partial_tile_clip.py"]
        native=_authenticate_native_abi(original,context.candidate,clip)
        emission=_emit_code(plan,field.emission,assembler_module=clip)
        result=dict(schema="clash95_battle_profile_stack_lease_v1",profile=profile,resolution=resolution,
            original_sha256=BASE_SHA256,parent_candidate_sha256=plan["candidate_sha256"],
            parent_stage=plan["parent_stage"],parent_revision=plan["parent_revision"],
            canonical_probe_sha256=plan["canonical_probe_sha256"],allocation_plan=plan,
            source_hashes=metadata["source_hashes"]|{name:_sha(data) for name,(data,_) in snapshot.items()},
            field_code_sha256=_sha(field.emission.code),field_metadata_sha256=_sha(field.metadata_json.encode()),
            code_va=emission.base_va,code_bytes=len(emission.code),code_sha256=_sha(emission.code),
            field_frame_bytes=FIELD_BYTES,owning_lease_frame_bytes=LEASE_BYTES,helper_frame_bytes=HELPER_BYTES,
            helper_maximum_intrinsic_stack_bytes=HELPER_BYTES+72,
            field_fixed_receipt_layout=dict(owner=0,modal=128,primary=640,globals=1040,expected_render=1152),
            descriptor_offsets=DESCRIPTOR,descriptor_location="authenticated owning stack only",
            root_stack_bound_bytes=ROOT_STACK_BOUND,native_return_abi=native['returns'],native_call_abi=native['calls'],
            field_tile_return_pcs=dict(emission.field_return_pcs),lease_field_return_pcs=dict(emission.lease_return_pcs),
            installed=False,preparation_only=True,writes_owner_state=False,writes_headers=False,
            heap_or_global_descriptor=False,arena_intersection_verified=False,
            installed_external_callsite_admission_verified=False,
            native_receiver_validity_verified=False,native_argument_validity_verified=False,
            standalone_native_callsite_replacement_safe=False,physical_only_clip_admission_verified=False,
            **{name:False for name in modules[CONTEXT].FALSE_CLAIMS},
            leaf_result_semantics="success preserves native EAX/flags; stack leaf_status/loss is separate",
            limitations=["No hook, native continuation abort or immediate cancellation is installed.",
                "A latched leaf loss does not stop frozen V2's next Tile or unadapted Unit/Tile reads or continuations.",
                "Leaf wrappers can check only after unchanged native normal RET and resource cleanup.",
                "RLE/provider receipt loss before normal return and termination closure remain unresolved.",
                "Observed outer return PC/EBP binds this stack lifetime; an installed external-callsite whitelist is not provided.",
                "Receiver/argument authority and physical-only clipping require future installed adapters; these helpers cannot replace native callsites on their own.",
                "Outer draw status2 is a retained diagnostic, not proof of immediate cancellation or healthy restoration."])
    _unchanged(snapshot)
    return BattleProfileStackLeaseBundle(emission,field,json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False))


def emit_battle_profile_stack_lease(original:bytes,profile:str,resolution:str)->BattleProfileStackLeaseBundle:
    snapshot=_snapshot()
    with _modules(snapshot) as modules:
        result=modules[SOURCE]._emit_authenticated(original,profile,resolution)
    _unchanged(snapshot)
    return result
