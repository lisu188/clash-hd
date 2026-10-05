"""Uninstalled profile-owned terrain loops and coordinate queries.

No executable or hook is installed. The producer privately reconstructs the
profile/routing chain and authenticates native tile dependencies. New loops
call only the owned bound guard and the original tile entry; they contain no
legacy full/incremental clone, primary, cursor or presentation operation.
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
SOURCE = "src/patcher/battle_profile_field.py"
ROUTING = "src/patcher/battle_profile_routing.py"
CONTEXT = "src/patcher/battle_profile_context.py"
PINNED_SOURCES = {
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
ENTRIES = ("visible_columns","clamp_scroll_x","screen_to_cell","visible_cell","draw_full","draw_incremental")
STATE = dict(phase=0,physical=4,native=8,saved_render=12,root_esp=16,owner_tid=20,
    enter_status=24,leave_status=28,return_status=32,fault=36,allocations=40,frees=44,
    pending_header=48,pending_pixels=52,native_pixels=56,physical_pixels=60,battle=64,
    saved_owner=68,saved_backend=72,abort_reason=76,modal_enter=80,modal_mirror=84,
    modal_leave=88,modal_allocs=92,modal_frees=96,modal_mirrors=100)
MAP,RENDER,PRIMARY,OWNER = 0x5202E0,0x511230,0x51D4C0,0x5199D8
LOWER,POST,BATTLE,THREAD_IAT = 0x526994,0x526990,0x532048,0x4EA4E8
NATIVE_TILE = 0x42FFB0
STACK_BYTES = 1280
REJECT = 0xFFFFFFFF
# Bounded original ranges; complete producer ancestry authenticates the parent.
NATIVE_SPANS = {
    "tile": (0x42FFB0,0x430B12,"d63f254e1d28a6314996b7ecc9d4b3c917351883a8e363b64d5092243d041a4f"),
    "visibility": (0x42C0F0,0x42C12B,"5412f74f7508ca12ae83e2b28d1b94b84cfacaa95524547bf11f0630b5c4f460"),
    "unit_draw": (0x42F820,0x42FC30,"1927416dbe66ccbee6bf8c22a7f874f5c1ee6f08feaff551985b0ae4b93d6c0e"),
    "adjacent_units": (0x42FC30,0x42FFB0,"fa35bb975c69093e4a0e0af71943d54edbb12af250821f4b462b0dae4052dfc8"),
    "vertical_offset": (0x42F7C0,0x42F820,"b517761a9dad348129b896a41b84ab316a4d3d929020a139bab1f00ec011a115"),
    "effects": (0x405510,0x4055BF,"f596739bbe07b4d43cdd13905bba42a20e3c9b21eb3506953301fe3a3f6cede3"),
    "memory_sprite": (0x402E80,0x403D6A,"910714afaeca20ac06b0298d622db214227bbaa1d9948a4d9845b91ab7ee4013"),
    "memory_line": (0x403F70,0x40403D,"74308b78ce403326e9df50c52c7c522bbc645e6b5001961e3a957e5d9b0ebf5e"),
    "memory_iterators": (0x403EF0,0x403F70,"4b6e21975f4bd5f82f105429e9adc13394b4effe7f91ec48de7c35561ae12812"),
}


@dataclass(frozen=True)
class CodeEmission:
    base_va: int
    state_va: int
    code: bytes
    entries: tuple
    relocations: tuple
    width: int
    height: int


@dataclass(frozen=True)
class BattleProfileFieldBundle:
    emission: CodeEmission
    routing_bundle: object
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
    prefix = "_clash95_battle_field_"+uuid.uuid4().hex
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
                     "battle_profile_routing","battle_profile_field"):
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


def _emit_code(plan,routing_emission,*,assembler_module):
    """Pure synthetic boundary, never public production authority.

    Query rejection is FFFFFFFF. visible_cell returns0/1 for valid world
    coordinates. Draw returns0 before drawing,1 complete,2 after an operation
    lost its exact invocation receipt. There is no fallback after2 and no
    unauthorized restoration. Pixel clearing/presentation are deferred.
    """
    _require(type(plan) is dict and plan.get("allocation_plan_only") is True and
             plan.get("battle_installed") is False,"uninstalled field plan required")
    profile,resolution = plan["profile"],plan["resolution"]
    _require(type(profile) is str and profile in ("classic","framed","completehd","modalwidgets") and
             type(resolution) is str,"canonical field selectors required")
    width,height = map(int,resolution.split("x"))
    _require(resolution == f"{width}x{height}" and (width,height) in
             ((800,600),(1024,768),(1280,720),(1280,960),(1366,768),(1920,1080),
              (2560,1440),(3440,1440),(3840,2160)),"canonical field preset required")
    rx,state = plan["rx"]["va"],plan["rw"]["va"]
    _require(type(rx) is type(state) is int and rx%4096 == 0 and state%4 == 0 and
             0x400000 < rx <= 0x7FFE0000 and 0x10000 <= state <= 0x7FFFFF80 and
             type(plan["rx"]["rva"]) is int and rx-plan["rx"]["rva"] == 0x400000 and
             plan["rx"]["virtual_reservation"] == 0x20000 and plan["rw"]["used_bytes"] == 128 and
             type(plan["rw"]["page_bytes"]) is int and plan["rw"]["page_bytes"] == 4096 and
             plan["rx"]["characteristics"] == 0x60000020 and plan["rw"]["characteristics"] == 0xC0000040,
             "field allocation differs")
    modal = None if profile in ("classic","framed") else state-0x100
    _require((modal is None and state == rx+0x20000 and plan["rw"]["page_offset"] == 0 and
              plan["rw"]["allocation"] == "fresh_zero_page") or
             (modal is not None and modal%4096 == 0 and plan["rw"]["page_offset"] == 0x100 and
              plan["rw"]["allocation"] == "reserved_existing_modal_page"),"field state page differs")
    _require(type(routing_emission.code) is bytes and 0 < len(routing_emission.code) < 0x20000 and
             rx <= routing_emission.base_va and routing_emission.base_va%16 == 0 and
             routing_emission.base_va+len(routing_emission.code) < rx+0x20000 and
             routing_emission.state_va == state and routing_emission.width == width and
             routing_emission.height == height and type(routing_emission.entries) is tuple,
             "immutable matching routing emission required")
    entries = dict(routing_emission.entries)
    _require(len(entries) == len(routing_emission.entries) == 6 and set(entries) ==
             {"check_owned_prepared","check_owned_bound","target_hud","compose_chrome",
              "initial_frame_target","initial_widgets_target"} and
             all(type(v) is int and routing_emission.base_va <= v < routing_emission.base_va+len(routing_emission.code)
                 for v in entries.values()),"fixed routing entries required")
    guard = entries["check_owned_bound"]
    base = (routing_emission.base_va+len(routing_emission.code)+15)&~15
    a = assembler_module._Assembler(base)
    OWN,MODAL,PHYSICAL_HEADER,PRIVATE_HEADER,PRIMARY_HEADER,BACKEND_HEADER = 0,128,256,448,640,864
    GLOBALS,WORLD_GEOMETRY = 1040,1080
    P = dict(physical=1104,native=1112,backend=1120,world=1124)
    X,Y,V,ORIGIN,EXPECTED_RENDER = 1132,1136,1140,1144,1152
    globals_ = (MAP,RENDER,OWNER,LOWER,POST,BATTLE,THREAD_IAT)
    def address(value,purpose): a.absolute(value,purpose)
    def read(reg,value,purpose):
        a.emit("8b"+f"{5|(reg<<3):02x}"); address(value,purpose)
    def write(reg,value,purpose):
        a.emit("89"+f"{5|(reg<<3):02x}"); address(value,purpose)
    def local(op,reg,offset):
        _require(0 <= offset <= STACK_BYTES+32,"field stack extent differs")
        a.emit(op+f"{0x84|(reg<<3):02x}"+"24"); a.u32(offset)
    def put(reg,offset): local("89",reg,offset)
    def get(reg,offset): local("8b",reg,offset)
    def match(reg,offset): local("3b",reg,offset)
    def mem(reg,base_reg,offset):
        a.emit("8b"+f"{0x80|(reg<<3)|base_reg:02x}"); a.u32(offset)
    def ne(label): a.branch("0f85",label)
    def eq(label): a.branch("0f84",label)
    def transfer(target,purpose):
        a.emit("e8"); at = len(a.code)
        a.relocations.append(assembler_module.Relocation(at,"rel32",target,purpose))
        a.u32(target-base-at-4)
    def save(name): a.label(name); a.emit("9c60fc81ec"); a.u32(STACK_BYTES)
    def result(value=None):
        if value is not None: a.emit("b8"); a.u32(value)
        put(0,STACK_BYTES+28); a.emit("81c4"); a.u32(STACK_BYTES); a.emit("619dc3")
    def admitted(reject):
        transfer(guard,"genuine profile owned bound guard"); a.emit("83f801"); ne(reject)
    def world(): read(7,state+STATE["battle"],"owned world")
    def visible_count(tag):
        mem(0,7,804); a.emit("b9"); a.u32((width-192)//64)
        a.emit("39c8"); a.branch("0f83",tag); a.emit("89c1"); a.label(tag)
    def snapshot(check,reject):
        fixed = [(state,128,OWN),(PRIMARY,216,PRIMARY_HEADER)]
        if modal is not None: fixed += [(modal,128,MODAL)]
        for pointer,count,slot in fixed:
            for offset in range(0,count,4):
                read(0,pointer+offset,"immutable invocation record")
                if check: match(0,slot+offset); ne(reject)
                else: put(0,slot+offset)
        # Fixed authorities precede cached dynamic pointers after any callback.
        for index,pointer in enumerate(globals_):
            read(0,pointer,"immutable invocation global")
            if check:
                match(0,EXPECTED_RENDER if pointer == RENDER else GLOBALS+index*4); ne(reject)
            else: put(0,GLOBALS+index*4)
        if not check:
            for key,state_key in (("physical","physical"),("native","native"),("world","battle"),("backend","saved_backend")):
                read(7,state+STATE[state_key],"immutable invocation pointer"); put(7,P[key])
            get(0,GLOBALS+4); put(0,EXPECTED_RENDER)
        for key,count,slot in (("physical",188,PHYSICAL_HEADER),("native",188,PRIVATE_HEADER),("backend",168,BACKEND_HEADER)):
            get(7,P[key])
            for offset in range(0,count,4):
                mem(0,7,offset)
                if check: match(0,slot+offset); ne(reject)
                else: put(0,slot+offset)
        get(7,P["world"])
        for index,offset in enumerate((800,804,808,812)):
            mem(0,7,offset)
            if check: match(0,WORLD_GEOMETRY+index*4); ne(reject)
            else: put(0,WORLD_GEOMETRY+index*4)
    def same_invocation(reject):
        snapshot(True,reject)
        admitted(reject)
        snapshot(True,reject)
    def cell(reject,outside):
        # Signed world coordinates are checked before the native terrain index.
        get(0,STACK_BYTES+28); a.emit("85c0"); a.branch("0f88",reject)
        mem(3,7,804); a.emit("39d8"); a.branch("0f83",reject)
        get(2,STACK_BYTES+20); a.emit("83fa00"); a.branch("0f8c",reject)
        a.emit("83fa07"); a.branch("0f83",reject)
        mem(3,7,808); a.emit("39d8"); a.branch("0f82",outside)
        visible_count(reject+".capacity"); a.emit("01cb")
        get(0,STACK_BYTES+28); a.emit("39d8"); a.branch("0f83",outside)

    for name in ENTRIES[:4]:
        save(name); reject = name+".reject"; admitted(reject); world()
        if name == "visible_columns":
            visible_count(name+".capacity"); a.emit("89c8"); result()
        elif name == "clamp_scroll_x":
            visible_count(name+".capacity"); a.emit("29c8"); put(0,V)
            get(0,STACK_BYTES+20); a.emit("85c0"); a.branch("0f89",name+".positive")
            a.emit("31c0"); a.branch("e9",name+".done")
            a.label(name+".positive"); match(0,V); a.branch("0f86",name+".done")
            get(0,V); a.label(name+".done"); result()
        elif name == "screen_to_cell":
            visible_count(name+".capacity"); a.emit("c1e10683c120")
            get(0,STACK_BYTES+20); a.emit("83f820"); a.branch("0f8c",reject)
            a.emit("39c8"); a.branch("0f83",reject)
            get(2,STACK_BYTES+24); a.emit("83fa10"); a.branch("0f8c",reject)
            a.emit("81fad0010000"); a.branch("0f8d",reject)
            a.emit("83e820c1e80603872803000083ea10c1ea06c1e21009d0"); result()
        else:
            cell(reject,name+".outside"); result(1)
            a.label(name+".outside"); result(0)
        a.label(reject); result(REJECT)

    for name in ENTRIES[4:]:
        save(name); reject = name+".reject"; lost = name+".lost"
        admitted(reject); world()
        if name == "draw_incremental": cell(reject,reject)
        snapshot(False,reject)
        get(7,P["world"]); visible_count(name+".capacity"); put(1,V)
        mem(0,7,808); put(0,ORIGIN)
        if name == "draw_full":
            put(0,X); a.emit("31c0"); put(0,Y)
        else:
            get(0,STACK_BYTES+28); put(0,X); get(0,STACK_BYTES+20); put(0,Y)
        # Publish the checked physical target; record the expected scoped value
        # from the immutable receipt, never from mutable post-callback globals.
        get(0,P["physical"]); put(0,EXPECTED_RENDER); write(0,RENDER,"scoped owned physical terrain target")
        a.label(name+".tile")
        same_invocation(lost)
        get(0,X); get(2,Y); a.emit("fc"); transfer(NATIVE_TILE,"authenticated native tactical tile")
        same_invocation(lost)
        if name == "draw_full":
            get(0,Y); a.emit("4083f807"); a.branch("0f82",name+".next_y")
            a.emit("31c0"); put(0,Y); get(0,X); a.emit("40"); put(0,X)
            get(2,ORIGIN); get(1,V); a.emit("01ca39d0"); a.branch("0f82",name+".tile")
            a.branch("e9",name+".complete")
            a.label(name+".next_y"); put(0,Y); a.branch("e9",name+".tile")
        a.label(name+".complete")
        # The final receipt has already passed twice around the last guard.
        get(0,GLOBALS+4); write(0,RENDER,"restore authorized invocation render target"); result(1)
        a.label(reject); result(0)
        a.label(lost); result(2)
    code = a.finish()
    _require(base+len(code) <= rx+0x20000,"field code exceeds authenticated RX reservation")
    emission = CodeEmission(base,state,code,tuple((name,base+a.labels[name]) for name in ENTRIES),tuple(a.relocations),width,height)
    assembler_module.absolute_relocation_offsets(emission)
    return emission


def _authenticate_native(original,candidate,clip):
    result = {}
    for name,(lo,hi,digest) in NATIVE_SPANS.items():
        for image in (original,candidate):
            offset = clip.file_offset(image,lo,hi-lo)
            _require(_sha(image[offset:offset+hi-lo]) == digest,"native field span differs: "+name)
        result[name] = dict(start=lo,end_exclusive=hi,sha256=digest)
    expected = struct.pack("<20I",*clip.VTABLE_ENTRIES)
    for image in (original,candidate):
        offset = clip.file_offset(image,0x50EE24,len(expected))
        _require(image[offset:offset+len(expected)] == expected,"native field memory vtable differs")
    return result


def _emit_authenticated(original,profile,resolution):
    _require(type(original) is bytes and _sha(original) == BASE_SHA256,"exact field original required")
    snapshot = _snapshot()
    _require(globals().get("__loaded_source_sha256__") == _sha(snapshot[SOURCE][0]),"private field producer required")
    with _modules(snapshot) as modules:
        routing = modules[ROUTING].emit_battle_profile_routing(original,profile,resolution)
        contract = routing.metadata(); plan = contract["allocation_plan"]
        parent = modules[CONTEXT].build_parent_context(original,profile,resolution)
        _require(parent.allocation_plan() == plan and contract["state_offsets"] == STATE and
                 contract["source_hashes"][ROUTING] == PINNED_SOURCES[ROUTING],"exact field parent/routing contract differs")
        clip = modules["src/patcher/partial_tile_clip.py"]
        native = _authenticate_native(original,parent.candidate,clip)
        emission = _emit_code(plan,routing.emission,assembler_module=clip)
        metadata = dict(schema="clash95_battle_profile_field_v1",profile=profile,resolution=resolution,
            original_sha256=BASE_SHA256,parent_stage=plan["parent_stage"],parent_revision=plan["parent_revision"],
            parent_candidate_sha256=plan["candidate_sha256"],canonical_probe_sha256=plan["canonical_probe_sha256"],
            source_hashes=contract["source_hashes"]|{name:_sha(data) for name,(data,_) in snapshot.items()},
            allocation_plan=plan,routing_code_sha256=_sha(routing.emission.code),
            routing_metadata_sha256=_sha(routing.metadata_json.encode()),code_va=emission.base_va,
            code_bytes=len(emission.code),code_sha256=_sha(emission.code),state_va=emission.state_va,
            state_bytes=128,state_offsets=STATE,helper_stack_snapshot_bytes=STACK_BYTES,native_spans=native,
            native_tile_va=NATIVE_TILE,native_tile_register_arguments=["EAX worldX","EDX worldY"],
            emitted_direct_primary_cursor_present_calls=False,clears_physical=False,writes_world_geometry=False,
            emitted_native_calls=["check_owned_bound","native42FFB0"],
            native_tile_checked_current_cell=True,native_neighbors_or_assets_verified=False,
            native_caller_sprite_clipping_enabled=False,native_arena_clipping_verified=False,
            immutable_memory_header_bytes=188,permitted_native_global_writes=[0x532104,0x519A14,0x5320F4,0x5320F8],
            writes_state=False,writes_headers=False,draw_result=dict(rejected_before_drawing=0,complete=1,receipt_lost=2),
            installed=False,emission_preparation_only=True,
            **{name:False for name in modules[CONTEXT].FALSE_CLAIMS},
            required_unemitted_families=["native unit/neighbor indices, content and provider preconditions",
                "explicit arena clipping for native terrain, overlay and unit sprite calls",
                "atomic arena/inert clearing","complete field/composition/presentation adapters",
                "HUD stats and animation transactions","camera initialization/restoration and physical input",
                "dialog/result/termination closure","complete installed-family loaded-byte admission and successor probe"],
            limitations=["Uninstalled source/CPU preparation does not establish native tile pixels or runtime acceptance.",
                "A native tile may change its audited animation/effect globals and allocate temporary drawing resources.",
                "Original neighbor paths can read X+1 past occupancy into casualty storage at20 columns; unit marks also read eight unchecked neighbors.",
                "Current-cell bounds do not validate native occupancy/unit/type/asset indices or transitive provider lifetimes.",
                "Original terrain, overlay and ordinary unit sprite calls disable caller clipping; explicit arena clipping remains required before atomic installation.",
                "No direct primary/cursor/present operation is emitted; malformed native sprites can still take original401D90 fatal shutdown.",
                "Receipt loss after drawing returns2; no subsequent tile, fallback, presentation or unauthorized global restoration occurs.",
                "The wrapper cannot preempt a native tile body or prove native heap/provider behavior.",
                "Clearing is deferred until the complete presentation transaction owns explicit arena/inert regions."])
    _unchanged(snapshot)
    return BattleProfileFieldBundle(emission,routing,json.dumps(metadata,sort_keys=True,separators=(",",":"),allow_nan=False))


def emit_battle_profile_field(original: bytes,profile: str,resolution: str) -> BattleProfileFieldBundle:
    snapshot = _snapshot()
    with _modules(snapshot) as modules:
        result = modules[SOURCE]._emit_authenticated(original,profile,resolution)
    _unchanged(snapshot)
    return result
