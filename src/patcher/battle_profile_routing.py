"""Uninstalled owned tactical-HUD targets and software chrome composition.

The public producer privately reconstructs the fixed profile lifecycle and
this source. Two target descriptions are returned, never installed. These
helpers do not draw the battlefield, present, transform input or prove pixels.
Only GetCurrentThreadId is called; copied pixels come from the private backing.
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
SOURCE = "src/patcher/battle_profile_routing.py"
LIFECYCLE = "src/patcher/battle_profile_lifecycle.py"
HUD = "src/patcher/framed_battle_hud.py"
PINNED_SOURCES = {
    LIFECYCLE: "dccb907b09d002691cad679219942ac5a8ffcb2798af4c96b0b1768dbd9e9f44",
    "src/patcher/battle_profile_context.py": "be3bbca018c415895ba7e79e64862512f330297fb56b4d8321f8f6d378c38500",
    "src/patcher/partial_tile_clip.py": "92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad",
    "src/patcher/pe_extension.py": "4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27",
    "src/patcher/framed_viewport.py": "1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42",
    "src/patcher/framed_battle_viewport.py": "8673e36bd04ded2afc8cc3b9d7ff2fed4c48dae891fe289509b44a9070c23bc6",
    "src/patcher/framed_battle_coordinates.py": "b67900d7399e0ce807d88a261c97942598beebfc28e2d78774cd109098f95142",
    "src/patcher/framed_battle_field.py": "f690865e615db65d02e8c59b5c43e0cfbaa1e371dd6502441d16e0d270a7196d",
    "src/patcher/framed_modal_canvas.py": "567b025520184a99f1f4f44b23a879ef9c729dcf2917dfa03a277c018cb20054",
    HUD: "3a6cb61a2ec2fcd0fa9c52c09a96e11a9a2d9f75cac6e3a2e826d5caa98a3ee3",
}
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
STATE_SIZE = 128
STATE = dict(phase=0, physical=4, native=8, saved_render=12, root_esp=16,
             owner_tid=20, enter_status=24, leave_status=28, return_status=32,
             fault=36, allocations=40, frees=44, pending_header=48,
             pending_pixels=52, native_pixels=56, physical_pixels=60,
             battle=64, saved_owner=68, saved_backend=72, abort_reason=76,
             modal_enter=80, modal_mirror=84, modal_leave=88, modal_allocs=92,
             modal_frees=96, modal_mirrors=100)
MODAL_LIVE = (0,4,8,12,16,20,36,52,56,60,64)
MODAL_HISTORY = ((24,"modal_enter"),(28,"modal_mirror"),(32,"modal_leave"),
                 (40,"modal_allocs"),(44,"modal_frees"),(48,"modal_mirrors"))
MAP, RENDER, PRIMARY, OWNER = 0x5202E0,0x511230,0x51D4C0,0x5199D8
LOWER, POST, BATTLE, THREAD_IAT = 0x526994,0x526990,0x532048,0x4EA4E8
MAP_OWNER, BATTLE_OWNER = 0x40AD40,0x42E8B0
MEMORY_VTABLE, PRIMARY_VTABLE = 0x50EE24,0x50EEC4
HEADER_BYTES, NATIVE_PIXELS, WORLD_BYTES = 188,307200,0xF7C
SITES = {"initial_frame_target": (0x42EB6E,"892d30125100"),
         "initial_widgets_target": (0x42EF71,"892d30125100")}
ENTRIES = ("check_owned_prepared","check_owned_bound","target_hud","compose_chrome",
           "initial_frame_target","initial_widgets_target")
STACK_BYTES = 1280


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
class BattleProfileRoutingBundle:
    emission: CodeEmission
    lifecycle_bundle: object
    hook_sites: tuple
    removed_highlow_rvas: tuple
    metadata_json: str

    def metadata(self):
        return json.loads(self.metadata_json)


def _require(condition,message):
    if not condition:
        raise ValueError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _snapshot():
    _require(Path(__file__).resolve() == ROOT/SOURCE,"noncanonical routing source")
    result = {}
    for name,digest in dict(PINNED_SOURCES,**{SOURCE:None}).items():
        path = ROOT/name
        _require(path.resolve(strict=True) == path and path.is_relative_to(ROOT),"noncanonical routing dependency")
        before = path.stat(); data = path.read_bytes(); after = path.stat()
        stamp = lambda row: (row.st_dev,row.st_ino,row.st_size,row.st_mtime_ns)
        _require(stamp(before) == stamp(after) and (digest is None or _sha(data) == digest),
                 "pinned routing source differs: "+name)
        result[name] = (data,stamp(after))
    return result


def _unchanged(snapshot):
    _require(_snapshot() == snapshot,"routing source changed during emission")


@contextmanager
def _modules(snapshot):
    prefix = "_clash95_battle_routing_"+uuid.uuid4().hex
    saved_path = list(sys.path)
    try:
        for suffix in ("",".src",".src.patcher"):
            module = types.ModuleType(prefix+suffix); module.__path__ = []
            sys.modules[module.__name__] = module
            if suffix:
                parent,_,leaf = module.__name__.rpartition(".")
                setattr(sys.modules[parent],leaf,module)
        result = {}
        order = ("framed_viewport","pe_extension","partial_tile_clip","framed_battle_viewport",
                 "framed_battle_coordinates","framed_battle_field","framed_modal_canvas",
                 "framed_battle_hud","battle_profile_context","battle_profile_lifecycle","battle_profile_routing")
        for stem in order:
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


def _composition_rectangles(width,height):
    """Independent row-copy description checked against pinned HUD geometry."""
    rows = [(0,0,31,15,0,0)]
    for y in range(16,height-16,448):
        count = min(448,height-16-y); rows.append((0,16,31,15+count,0,y))
    rows.append((0,464,31,479,0,height-16))
    for x in range(32,width-160,448):
        count = min(448,width-160-x)
        rows += [(32,0,31+count,15,x,0),(32,464,31+count,479,x,height-16)]
    for y in range(368,height-112,352):
        count = min(352,height-112-y); rows.append((624,16,639,15+count,width-16,y))
    rows += [(480,0,639,367,width-160,0),(480,368,639,479,width-160,height-112)]
    return tuple(rows)


def _parent_target_contract(original,profile,contract,clip):
    """Expose why both parent target spans remain the authenticated old MOV.

    The privately rebuilt lifecycle authenticates every parent byte. Its full
    native-root contract permits only the distinct inherited present CALL;
    neither routing target overlaps that exact five-byte exception.
    """
    expected_root = dict(start=0x42E9E0,end_exclusive=0x42F7B6,
        sha256="76d0092eb035798d0da8f1b1ed11913e7c428781784ee91c1a0337cdb19d367a")
    _require(contract.get("native_spans",{}).get("root") == expected_root,
             "authenticated routing root span differs")
    root = contract.get("inherited_native_root_contract")
    _require(type(root) is dict,"authenticated routing parent root missing")
    if profile == "classic":
        _require(root.get("rule") == "exact_original" and root.get("edits") == [] and
                 root.get("candidate_root_sha256") == expected_root["sha256"],
                 "Classic routing parent root differs")
    else:
        edits = root.get("edits")
        _require(root.get("rule") == "one_exact_inherited_centered_present_call" and
                 root.get("candidate_root_sha256") == "a1a51ff496653fb6e69803eaf1def9362e5c2ab70ff1a1dd3216743809827c42" and
                 type(edits) is list and len(edits) == 1 and type(edits[0]) is dict and
                 edits[0].get("va") == 0x42F2F5 and edits[0].get("old_hex") == "e8a61b0300" and
                 edits[0].get("new_hex") == "e806c70e00",
                 "inherited routing parent root exception differs")
    result = []
    for name,(va,value) in SITES.items():
        old = bytes.fromhex(value); offset = clip.file_offset(original,va,len(old))
        _require(expected_root["start"] <= va and va+len(old) <= expected_root["end_exclusive"] and
                 original[offset:offset+len(old)] == old,
                 "native HUD target old bytes differ")
        for edit in root["edits"]:
            lo,hi = edit["va"],edit["va"]+len(bytes.fromhex(edit["new_hex"]))
            _require(va+len(old) <= lo or hi <= va,"inherited edit overlaps routing target")
        result.append(dict(name=name,va=va,rva=va-0x400000,file_offset=offset,old_hex=value,
                           parent_bytes_exact_original=True))
    return dict(native_root=expected_root,parent_root_sha256=root["candidate_root_sha256"],
                parent_root_rule=root["rule"],sites=result)


def _emit_code(plan,lifecycle_emission,*,modal_state_va,assembler_module):
    """Synthetic boundary; production obtains both inputs privately.

    Read-only guards snapshot all state/header bytes across the thread callback.
    Composition writes only declared physical chrome rectangles. State, headers,
    native backing, arena/gutters, other GPRs, ESP and EFLAGS/DF are preserved.
    """
    _require(type(plan) is dict and plan.get("allocation_plan_only") is True and
             plan.get("battle_installed") is False,"uninstalled routing plan required")
    profile,resolution = plan["profile"],plan["resolution"]
    _require(type(profile) is str and profile in ("classic","framed","completehd","modalwidgets"),"unknown routing profile")
    _require(type(resolution) is str,"canonical routing preset required")
    width,height = map(int,resolution.split("x"))
    _require(resolution == f"{width}x{height}" and (width,height) in
             ((800,600),(1024,768),(1280,720),(1280,960),(1366,768),(1920,1080),
              (2560,1440),(3440,1440),(3840,2160)),"canonical routing preset required")
    rx,state = plan["rx"]["va"],plan["rw"]["va"]
    code = lifecycle_emission.code
    _require(type(code) is bytes and 0 < len(code) < 0x20000 and
             lifecycle_emission.base_va == rx and lifecycle_emission.state_va == state and
             lifecycle_emission.width == width and lifecycle_emission.height == height and
             type(lifecycle_emission.entries) is tuple,"immutable matching lifecycle emission required")
    _require(type(rx) is type(state) is int and rx%4096 == 0 and state%4 == 0 and
             0x400000 < rx <= 0x7FFE0000 and 0x10000 <= state <= 0x7FFFFF80 and
             type(plan["rx"]["rva"]) is int and rx-plan["rx"]["rva"] == 0x400000 and
             plan["rx"]["virtual_reservation"] == 0x20000 and plan["rw"]["used_bytes"] == 128 and
             type(plan["rw"]["page_bytes"]) is int and plan["rw"]["page_bytes"] == 4096 and
             plan["rx"]["characteristics"] == 0x60000020 and plan["rw"]["characteristics"] == 0xC0000040 and
             (state+128 <= rx or state >= rx+0x20000),"routing allocation differs")
    _require((modal_state_va is None) == (profile in ("classic","framed")),"routing modal owner differs")
    if modal_state_va is None:
        _require(plan["rw"]["allocation"] == "fresh_zero_page" and plan["rw"]["page_offset"] == 0 and
                 state == rx+0x20000,"routing fresh state page differs")
    if modal_state_va is not None:
        _require(type(modal_state_va) is int and modal_state_va%4096 == 0 and
                 0x10000 <= modal_state_va <= 0x7FFFF000 and state == modal_state_va+0x100 and
                 plan["rw"]["allocation"] == "reserved_existing_modal_page" and plan["rw"]["page_offset"] == 0x100,
                 "routing inherited state reservation differs")
    base = (rx+len(code)+15)&~15
    a = assembler_module._Assembler(base)
    # Every region is bounded by STACK_BYTES; state offsets remain untouched.
    OWN,MODAL,PHYSICAL_HEADER,PRIVATE_HEADER,PRIMARY_HEADER,BACKEND_HEADER = 0,128,256,448,640,864
    GLOBALS,WORLD_GEOMETRY = 1040,1080
    P = dict(physical=1104,physical_pixels=1108,native=1112,native_pixels=1116,backend=1120,world=1124)
    globals_ = (MAP,RENDER,OWNER,LOWER,POST,BATTLE,THREAD_IAT)
    def address(value,purpose): a.absolute(value,purpose)
    def read(reg,value,purpose):
        a.emit("8b"+f"{5|(reg<<3):02x}"); address(value,purpose)
    def write(reg,value,purpose):
        a.emit("89"+f"{5|(reg<<3):02x}"); address(value,purpose)
    def local(op,reg,offset):
        _require(0 <= offset <= STACK_BYTES+32,"routing stack extent differs")
        a.emit(op+f"{0x84|(reg<<3):02x}"+"24"); a.u32(offset)
    def put(reg,offset): local("89",reg,offset)
    def get(reg,offset): local("8b",reg,offset)
    def match(reg,offset): local("3b",reg,offset)
    def mem(reg,base_reg,offset):
        a.emit("8b"+f"{0x80|(reg<<3)|base_reg:02x}"); a.u32(offset)
    def cmp_abs(value,immediate,purpose,is_address=False):
        a.emit("813d"); address(value,purpose)
        address(immediate,purpose+" value") if is_address else a.u32(immediate)
    def cmp_mem(reg,offset,immediate,is_address=False):
        a.emit("81"+f"{0xb8|reg:02x}"); a.u32(offset)
        address(immediate,"surface vtable value") if is_address else a.u32(immediate)
    def ne(label): a.branch("0f85",label)
    def eq(label): a.branch("0f84",label)
    def state_cmp(name,value,reject,is_address=False):
        cmp_abs(state+STATE[name],value,"state."+name,is_address); ne(reject)
    def state_read(reg,name): read(reg,state+STATE[name],"state."+name)
    def reg_state(reg,name):
        a.emit("3b"+f"{5|(reg<<3):02x}"); address(state+STATE[name],"state."+name)
    def bounds(reg,size,reject,align=True):
        a.emit("81"+f"{0xf8|reg:02x}"); a.u32(0x10000); a.branch("0f82",reject)
        a.emit("81"+f"{0xf8|reg:02x}"); a.u32(0x80000000-size); a.branch("0f87",reject)
        if align:
            a.emit("f7"+f"{0xc0|reg:02x}"+"03000000"); ne(reject)
    def save(): a.emit("9c60fc81ec"); a.u32(STACK_BYTES)
    def result(value):
        a.emit("b8"); a.u32(value); put(0,STACK_BYTES+28)
        a.emit("81c4"); a.u32(STACK_BYTES); a.emit("619dc3")
    def disjoint(size,other_size,reject,tag):
        # EAX and EBX identify bounded half-open intervals, EDX is scratch.
        a.emit("89c281c2"); a.u32(size); a.emit("39d3"); a.branch("0f83",tag)
        a.emit("89da81c2"); a.u32(other_size); a.emit("39d0"); a.branch("0f82",reject)
        a.label(tag)
    def protected_interval(size,reject,tag):
        # EAX is bounded first. Reject protected image/code/state aliases
        # before following a header, backend or world pointer.
        regions = [(0x400000,plan["rx"]["rva"]),(rx,0x20000),
                   (state if modal_state_va is None else modal_state_va,4096)]
        for index,(pointer,count) in enumerate(regions):
            a.emit("bb"); address(pointer,"protected routing allocation extent")
            disjoint(size,count,reject,tag+str(index))
    def blocks_snapshot(check,reject):
        blocks = [(state,128,OWN),(PRIMARY,216,PRIMARY_HEADER)]
        if modal_state_va is not None: blocks += [(modal_state_va,128,MODAL)]
        for pointer,size,slot in blocks:
            for offset in range(0,size,4):
                read(0,pointer+offset,"complete routing record snapshot")
                if check: match(0,slot+offset); ne(reject)
                else: put(0,slot+offset)
        # Fixed records and globals must reject a callback's changed ownership
        # before a cached dynamic pointer is dereferenced again.
        for index,pointer in enumerate(globals_):
            read(0,pointer,"exact routing global snapshot")
            if check: match(0,GLOBALS+index*4); ne(reject)
            else: put(0,GLOBALS+index*4)
        for name,size,slot in (("physical",188,PHYSICAL_HEADER),("native",188,PRIVATE_HEADER),("backend",168,BACKEND_HEADER)):
            get(7,P[name])
            for offset in range(0,size,4):
                mem(0,7,offset)
                if check: match(0,slot+offset); ne(reject)
                else: put(0,slot+offset)
    def header(name,w,h,pixel_name,reject):
        state_read(7,name); bounds(7,188,reject); put(7,P[name])
        a.emit("89f8"); protected_interval(188,reject,reject+"."+name+".header")
        cmp_mem(7,0,w|(h<<16)); ne(reject)
        cmp_mem(7,0xB8,MEMORY_VTABLE,True); ne(reject)
        cmp_mem(7,0xAC,0); ne(reject)
        mem(0,7,4); bounds(0,w*h,reject); protected_interval(w*h,reject,reject+"."+name+".pixels")
        reg_state(0,pixel_name); ne(reject)
        put(0,P[pixel_name])
    def context(name,phase):
        a.label(name); save(); reject = name+".reject"
        state_cmp("phase",phase,reject)
        for key,value in (("fault",0),("abort_reason",0),("enter_status",1),("leave_status",0),
                          ("return_status",0),("pending_header",0),("pending_pixels",0)):
            state_cmp(key,value,reject)
        state_cmp("saved_owner",MAP_OWNER,reject,True)
        state_read(0,"owner_tid"); a.emit("85c0"); eq(reject)
        state_read(0,"root_esp"); bounds(0,8,reject)
        state_read(0,"allocations"); a.emit("85c0"); eq(reject)
        a.emit("48"); reg_state(0,"frees"); ne(reject)
        cmp_abs(OWNER,BATTLE_OWNER,"native battle owner",True); ne(reject)
        for pointer in (LOWER,POST): cmp_abs(pointer,0,"inactive drawing callback"); ne(reject)
        header("physical",width,height,"physical_pixels",reject)
        get(0,P["physical"]); a.emit("3b05"); address(MAP,"physical map identity"); ne(reject)
        header("native",640,480,"native_pixels",reject)
        state_read(0,"saved_render"); reg_state(0,"physical"); eq(name+".saved_render_ok")
        a.emit("3d"); address(PRIMARY,"saved physical primary"); ne(reject)
        a.label(name+".saved_render_ok")
        read(0,RENDER,"current render identity"); reg_state(0,"physical"); eq(name+".render_ok")
        reg_state(0,"native"); eq(name+".render_ok")
        a.emit("3d"); address(PRIMARY,"current physical primary"); ne(reject)
        a.label(name+".render_ok")
        cmp_abs(PRIMARY,width|(height<<16),"physical primary dimensions"); ne(reject)
        cmp_abs(PRIMARY+0xB8,PRIMARY_VTABLE,"physical primary vtable",True); ne(reject)
        cmp_abs(PRIMARY+0xD4,8,"physical primary depth"); ne(reject)
        read(7,PRIMARY+0xBC,"physical primary backend"); bounds(7,168,reject); put(7,P["backend"])
        a.emit("89f8"); protected_interval(168,reject,reject+".backend")
        reg_state(7,"saved_backend"); ne(reject)
        cmp_mem(7,0xA4,0); eq(reject)
        if modal_state_va is not None:
            for offset in MODAL_LIVE: cmp_abs(modal_state_va+offset,0,"inactive inherited owner"); ne(reject)
            read(0,modal_state_va+40,"inherited allocation count")
            a.emit("3b05"); address(modal_state_va+44,"inherited free count"); ne(reject)
            for offset,key in MODAL_HISTORY:
                read(0,modal_state_va+offset,"inherited historical receipt"); reg_state(0,key); ne(reject)
        else:
            for _,key in MODAL_HISTORY: state_cmp(key,0,reject)
        objects = [("physical",188),("physical_pixels",width*height),("native",188),
                   ("native_pixels",NATIVE_PIXELS),("backend",168)]
        if phase == 1:
            state_cmp("battle",0,reject); cmp_abs(BATTLE,0,"unbound native battle"); ne(reject)
        else:
            state_read(7,"battle"); bounds(7,WORLD_BYTES,reject); put(7,P["world"])
            a.emit("89f8"); protected_interval(WORLD_BYTES,reject,reject+".world")
            a.emit("3b3d"); address(BATTLE,"bound native battle identity"); ne(reject)
            cmp_mem(7,800,7); ne(reject); cmp_mem(7,812,0); ne(reject)
            mem(3,7,804); a.emit("83fb01"); a.branch("0f82",reject)
            a.emit("83fb14"); a.branch("0f87",reject)
            a.emit("b9"); a.u32((width-192)//64)
            a.emit("39cb"); a.branch("0f83",name+".capacity")
            a.emit("89d9"); a.label(name+".capacity")
            a.emit("29cb"); mem(0,7,808); a.emit("85c0"); a.branch("0f88",reject)
            a.emit("39d8"); a.branch("0f87",reject)
            objects += [("world",WORLD_BYTES)]
            for index,offset in enumerate((800,804,808,812)):
                mem(0,7,offset); put(0,WORLD_GEOMETRY+index*4)
        for index,(key,size) in enumerate(objects):
            get(0,P[key])
            for n,(other,count) in enumerate(objects[index+1:]):
                get(3,P[other]); disjoint(size,count,reject,name+f".pair{index}_{n}")
        read(0,THREAD_IAT,"thread identity import"); bounds(0,1,reject,False)
        blocks_snapshot(False,reject)
        a.emit("ff15"); address(THREAD_IAT,"GetCurrentThreadId IAT")
        match(0,OWN+STATE["owner_tid"]); ne(reject)
        blocks_snapshot(True,reject)
        if phase == 2:
            get(7,P["world"])
            for index,offset in enumerate((800,804,808,812)):
                mem(0,7,offset); match(0,WORLD_GEOMETRY+index*4); ne(reject)
        result(1); a.label(reject); result(0)
    context("check_owned_prepared",1)
    context("check_owned_bound",2)
    a.label("target_hud"); save()
    cmp_abs(state+STATE["phase"],1,"prepared lifetime"); eq("target.prepared")
    a.branch("e8","check_owned_bound"); a.branch("e9","target.checked")
    a.label("target.prepared"); a.branch("e8","check_owned_prepared")
    a.label("target.checked"); a.emit("83f801"); ne("target.reject")
    state_read(0,"native"); write(0,RENDER,"owned private HUD target"); result(1)
    a.label("target.reject"); result(0)
    rectangles = _composition_rectangles(width,height)
    a.label("compose_chrome"); save(); a.branch("e8","check_owned_bound")
    a.emit("83f801"); ne("compose.reject")
    for index,(l,t,r,b,x,y) in enumerate(rectangles):
        _require(0 <= l <= r < 640 and 0 <= t <= b < 480 and 0 <= x <= x+r-l < width and
                 0 <= y <= y+b-t < height,"chrome copy outside owned surface")
        _require(x+r-l < 32 or y+b-t < 16 or y >= height-16 or x >= width-160,
                 "chrome copy touches the battlefield or inert interior")
        state_read(6,"native_pixels"); a.emit("81c6"); a.u32(t*640+l)
        state_read(7,"physical_pixels"); a.emit("81c7"); a.u32(y*width+x)
        a.emit("ba"); a.u32(b-t+1); a.label("copy."+str(index))
        a.emit("b9"); a.u32(r-l+1); a.emit("fcf3a481c6"); a.u32(640-(r-l+1))
        a.emit("81c7"); a.u32(width-(r-l+1)); a.emit("4a"); ne("copy."+str(index))
    result(1); a.label("compose.reject"); result(0)
    for name,(va,_) in SITES.items():
        a.label(name); a.emit("9c60"); a.branch("e8","target_hud")
        a.emit("83f801"); eq(name+".done")
        a.emit("892d"); address(RENDER,"native target MOV fallback")
        a.label(name+".done"); a.emit("619de9")
        offset = len(a.code)
        a.relocations.append(assembler_module.Relocation(offset,"rel32",va+6,"native target continuation"))
        a.u32(va+6-base-offset-4)
    code = a.finish()
    _require(base+len(code) <= rx+0x20000,"routing code exceeds authenticated RX reservation")
    emission = CodeEmission(base,state,code,tuple((name,base+a.labels[name]) for name in ENTRIES),
                            tuple(a.relocations),width,height)
    assembler_module.absolute_relocation_offsets(emission)
    return emission


def _emit_authenticated(original,profile,resolution):
    _require(type(original) is bytes and _sha(original) == BASE_SHA256,"exact routing original required")
    snapshot = _snapshot()
    _require(globals().get("__loaded_source_sha256__") == _sha(snapshot[SOURCE][0]),"private routing producer required")
    with _modules(snapshot) as modules:
        lifecycle = modules[LIFECYCLE].emit_battle_profile_lifecycle(original,profile,resolution)
        contract = lifecycle.metadata(); plan = contract["allocation_plan"]
        _require(contract["state_offsets"] == STATE and contract["source_hashes"][LIFECYCLE] == PINNED_SOURCES[LIFECYCLE],
                 "exact lifecycle state contract required")
        width,height = lifecycle.emission.width,lifecycle.emission.height
        rectangles = _composition_rectangles(width,height)
        _require(rectangles == modules[HUD].composition_rectangles(width,height),"pinned chrome geometry differs")
        clip,pe = modules["src/patcher/partial_tile_clip.py"],modules["src/patcher/pe_extension.py"]
        target_contract = _parent_target_contract(original,profile,contract,clip)
        emission = _emit_code(plan,lifecycle.emission,modal_state_va=contract["modal_state_va"],assembler_module=clip)
        hooks,removed = [],[]
        for name,(va,value) in SITES.items():
            old = bytes.fromhex(value); offset = clip.file_offset(original,va,len(old))
            _require(original[offset:offset+len(old)] == old,"native HUD target old bytes differ")
            target = dict(emission.entries)[name]
            new = b"\xe9"+struct.pack("<i",target-va-5)+b"\x90"
            hooks.append(pe.HookPatch(offset,va-0x400000,va,old,new,"battle_profile_routing."+name,
                                     (pe.CodeRelocation(1,"rel32",target,name),)))
            removed.extend(va-0x400000+field for field in clip._original_highlow_fields(original,va,len(old)))
        metadata = dict(schema="clash95_battle_profile_routing_v1",profile=profile,resolution=resolution,
            original_sha256=BASE_SHA256,parent_stage=plan["parent_stage"],parent_revision=plan["parent_revision"],
            parent_candidate_sha256=plan["candidate_sha256"],canonical_probe_sha256=plan["canonical_probe_sha256"],
            source_hashes=contract["source_hashes"]|{name:_sha(data) for name,(data,_) in snapshot.items()},
            lifecycle_code_sha256=_sha(lifecycle.emission.code),lifecycle_metadata_sha256=_sha(lifecycle.metadata_json.encode()),
            inherited_native_target_contract=target_contract,
            allocation_plan=plan,code_sha256=_sha(emission.code),code_bytes=len(emission.code),code_va=emission.base_va,
            state_va=emission.state_va,state_bytes=128,state_offsets=STATE,helper_stack_snapshot_bytes=STACK_BYTES,
            composition_rectangles=rectangles,world_geometry_offsets=[800,804,808,812],
            native_callees=["GetCurrentThreadId"],writes_state=False,writes_headers=False,clears_physical=False,
            installed=False,emission_preparation_only=True,**{name:False for name in modules["src/patcher/battle_profile_context.py"].FALSE_CLAIMS},
            required_unemitted_families=["initial bind clear and expanded field draw","full/incremental field and visibility hooks",
                "native HUD stats and text scoped globals","full redraw owner routing","every animation-step composition/presentation",
                "physical primary presentation","field/HUD input and camera","dialogs/results restoration",
                "all normal/fatal/queue quit families","atomic successor installer and canonical probe"],
            limitations=["Uninstalled helpers and synthetic byte/geometry consistency establish no pixels or runtime correctness.",
                "The ownership predicate is not a certificate that the complete rendering/input family is installed.",
                "No native primitive, primary lock, present, field draw or input operation is called.",
                "Source bounds do not prove dynamic heap lifetime or concurrent native behavior."])
    _unchanged(snapshot)
    return BattleProfileRoutingBundle(emission,lifecycle,tuple(hooks),tuple(sorted(set(removed))),
                                     json.dumps(metadata,sort_keys=True,separators=(",",":"),allow_nan=False))


def emit_battle_profile_routing(original: bytes,profile: str,resolution: str) -> BattleProfileRoutingBundle:
    snapshot = _snapshot()
    with _modules(snapshot) as modules:
        result = modules[SOURCE]._emit_authenticated(original,profile,resolution)
    _unchanged(snapshot)
    return result
