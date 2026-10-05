"""Uninstalled, profile-aware private tactical-HUD lifetime preparation.

The public entry point privately reconstructs a fixed source parent, derives
its code/state addresses, and verifies original/candidate instruction spans.
It returns bounded helper bytes and four hook descriptions. It never installs
them, writes a candidate, or establishes battle/render/input acceptance.

Native allocation failure retains the original fatal route. Private rollback
is separate from normal retirement and the later native-return checkpoint.
Drawing, dialogs, animation and general process-quit interception are absent.
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
SOURCE = "src/patcher/battle_profile_lifecycle.py"
CONTEXT = "src/patcher/battle_profile_context.py"
PINNED_SOURCES = {
    CONTEXT: "be3bbca018c415895ba7e79e64862512f330297fb56b4d8321f8f6d378c38500",
    "src/patcher/partial_tile_clip.py": "92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad",
    "src/patcher/pe_extension.py": "4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27",
    "src/patcher/framed_viewport.py": "1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42",
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
LIVE = ("physical", "native", "saved_render", "root_esp", "owner_tid",
        "pending_header", "pending_pixels", "native_pixels", "physical_pixels",
        "battle", "saved_owner", "saved_backend")
MODAL_LIVE = (0, 4, 8, 12, 16, 20, 36, 52, 56, 60, 64)
MODAL_HISTORY = ((24, "modal_enter"), (28, "modal_mirror"),
                 (32, "modal_leave"), (40, "modal_allocs"),
                 (44, "modal_frees"), (48, "modal_mirrors"))
MAP, RENDER, PRIMARY, OWNER = 0x5202E0, 0x511230, 0x51D4C0, 0x5199D8
LOWER, POST, BATTLE = 0x526994, 0x526990, 0x532048
MAP_OWNER, BATTLE_OWNER = 0x40AD40, 0x42E8B0
MEMORY_VTABLE, PRIMARY_VTABLE = 0x50EE24, 0x50EEC4
THREAD_IAT = 0x4EA4E8
ALLOC, FREE, CTOR, DTOR = 0x473FF0, 0x4740DD, 0x401E00, 0x403E50
NATIVE_PIXELS, HEADER_BYTES, BATTLE_BYTES = 640 * 480, 0xBC, 0xF7C
# Minimal descriptions only; no disassembler/decompiler export is stored.
SITES = {
    "root_entry": (0x42E9E0, "56575581ec9c000000", 0x42E9E9),
    "bind_allocation": (0x42EC90, "833d4820530000", 0x42EC97),
    "leave_before_free": (0x42F531, "e8a74b0400", 0x42F536),
    "root_epilogue": (0x42F5B3, "81c49c000000", 0x42F5B9),
}
NATIVE_SPANS = {
    "root": (0x42E9E0, 0x42F7B6, "76d0092eb035798d0da8f1b1ed11913e7c428781784ee91c1a0337cdb19d367a"),
    "allocation_predicate": (0x42EC90, 0x42EC9D, "9f5b593ae8d812646e9e3e019adaabf10e8f77f19c6adc0eb6fffd337f57be51"),
    "allocation_fatal": (0x42F004, 0x42F037, "40bfff07dd510c323bf840f133e66c7269063d33da35a9d4f88e2afb586f0506"),
    "free_and_zero": (0x42F52C, 0x42F53D, "c06c2880ea623eaeba2eed93b5dd8a5cffc41e8ada40ebdf5b4f724fb970ad39"),
    "epilogue": (0x42F5B1, 0x42F5BF, "a66256148a3dfbff7b839cbda9059d148bb9b6d053bc5c05ad8ce2dfa2217862"),
    "allocator": (0x473FF0, 0x4740DD, "a18fd9592d3cbed9c905ca7972918df080331fa2df655b064efccb8dc081ba68"),
    "base_constructor": (0x401E00, 0x401E25, "13da14ece5cae85a50f8ccc76f6a26ae558cf3e6346f6a9bb7ec28420056e3b2"),
    "member_constructor": (0x473250, 0x4732A0, "bb259809475cdab8983e2fc8e1317f344e1637dfa72f8c8e8d86a7aa72517af4"),
    "scalar_destructor": (0x403E50, 0x403EAE, "9f2dbe6bee7edc7fb85fddcfdf444646ba5888cde136d14bf604efe9de3831e8"),
}
ROOT_PRESENT_VA, ROOT_PRESENT_OFFSET = 0x42F2F5, 0x02E6F5
ROOT_PRESENT_OLD, ROOT_PRESENT_NEW = "e8a61b0300", "e806c70e00"
ROOT_EDIT_PINS = {
    "patcher": ("src/patcher/patch_clash95_hd.py", "38021e9a4d21bc9a8bf0c2f9b66379595509446b5177d6f91bab6f677b5e8106"),
    "framed_recipe": ("src/patcher/framed_recipe.py", "559b571ce1dd83421f79a58e110cd5b6317807cd68087d7ea77f14c4f4a071b4"),
    "framed_viewport": ("src/patcher/framed_viewport.py", "1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42"),
}
ROOT_RECIPE_PATHS = {
    "framed": ("predecessor", "framed_recipe"),
    "completehd": ("predecessor", "base_candidate", "base_candidate", "framed_recipe"),
    "modalwidgets": ("predecessor",) + ("base_candidate",)*4 +
                    ("predecessor", "base_candidate", "base_candidate", "framed_recipe"),
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
class BattleProfileLifecycleBundle:
    emission: CodeEmission
    hook_sites: tuple
    removed_highlow_rvas: tuple
    metadata_json: str

    def metadata(self):
        return json.loads(self.metadata_json)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _snapshot():
    _require(Path(__file__).resolve() == ROOT / SOURCE, "noncanonical lifecycle module")
    result = {}
    for name, digest in dict(PINNED_SOURCES, **{SOURCE: None}).items():
        path = ROOT / name
        _require(path.resolve(strict=True) == path and path.is_relative_to(ROOT), "noncanonical lifecycle source")
        before = path.stat()
        data = path.read_bytes()
        after = path.stat()
        stamp = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns)
        _require(stamp(before) == stamp(after) and (digest is None or _sha(data) == digest),
                 "pinned lifecycle source differs: " + name)
        result[name] = (data, stamp(after))
    return result


def _unchanged(snapshot):
    current = _snapshot()
    _require(current == snapshot, "lifecycle source changed during emission")


@contextmanager
def _modules(snapshot):
    prefix = "_clash95_battle_lifecycle_" + uuid.uuid4().hex
    saved_path = list(sys.path)
    try:
        for suffix in ("", ".src", ".src.patcher"):
            package = types.ModuleType(prefix + suffix)
            package.__path__ = []
            sys.modules[package.__name__] = package
            if suffix:
                parent, _, leaf = package.__name__.rpartition(".")
                setattr(sys.modules[parent], leaf, package)
        result = {}
        for name in ("src/patcher/framed_viewport.py", "src/patcher/pe_extension.py",
                     "src/patcher/partial_tile_clip.py", CONTEXT, SOURCE):
            full = prefix + "." + name.removesuffix(".py").replace("/", ".")
            module = types.ModuleType(full)
            module.__file__, module.__package__ = str(ROOT / name), full.rpartition(".")[0]
            module.__loaded_source_sha256__ = _sha(snapshot[name][0])
            sys.modules[full] = module
            setattr(sys.modules[module.__package__], full.rpartition(".")[2], module)
            exec(compile(snapshot[name][0], module.__file__, "exec"), module.__dict__)
            result[name] = module
        yield result
    finally:
        for name in list(sys.modules):
            if name == prefix or name.startswith(prefix + "."):
                del sys.modules[name]
        sys.path[:] = saved_path


def _emit_code(plan, *, modal_state_va, assembler_module):
    """Pure synthetic-fixture boundary; the public API supplies all authority.

    All helper state writes are DWORDs within 0..103. Temporary immutable entry
    snapshots live in a bounded 384-byte helper stack frame, not modal padding.
    EAX is the boolean result; other GPRs, ESP and caller EFLAGS/DF are restored.
    """
    _require(type(plan) is dict and plan.get("allocation_plan_only") is True
             and plan.get("battle_installed") is False, "uninstalled allocation plan required")
    profile, resolution = plan["profile"], plan["resolution"]
    _require(type(profile) is str and profile in ("classic", "framed", "completehd", "modalwidgets"), "unknown lifecycle profile")
    _require(type(resolution) is str, "canonical lifecycle preset required")
    width, height = map(int, resolution.split("x"))
    _require(resolution == f"{width}x{height}" and (width, height) in ((800,600),(1024,768),(1280,720),(1280,960),(1366,768),
                               (1920,1080),(2560,1440),(3440,1440),(3840,2160)), "canonical lifecycle preset required")
    base, state = plan["rx"]["va"], plan["rw"]["va"]
    image_extent = plan["rx"]["rva"]
    _require(type(base) is type(state) is int and base % 4096 == 0
             and type(image_extent) is int and image_extent > 0 and base-image_extent == 0x400000
             and 0x10000 <= base <= 0x7FFE0000 and 0x10000 <= state <= 0x7FFFFF80
             and (state + STATE_SIZE <= base or state >= base + 0x20000)
             and state % 4 == 0 and type(plan["rw"]["used_bytes"]) is int
             and plan["rw"]["used_bytes"] == STATE_SIZE
             and plan["rw"]["page_bytes"] == 4096
             and plan["rw"]["page_offset"] == (0 if modal_state_va is None else 0x100)
             and plan["rx"]["characteristics"] == 0x60000020
             and plan["rw"]["characteristics"] == 0xC0000040, "owned lifecycle allocation differs")
    _require((modal_state_va is None) == (profile in ("classic", "framed")), "profile modal ownership differs")
    if modal_state_va is not None:
        _require(type(modal_state_va) is int and 0x10000 <= modal_state_va <= 0x7FFFF000 and modal_state_va % 4096 == 0
                 and state == modal_state_va + 0x100, "reserved inherited state offset differs")
    a = assembler_module._Assembler(base)
    state_page = state if modal_state_va is None else modal_state_va
    LOCAL, OWN_SNAPSHOT, MODAL_SNAPSHOT = 384, 64, 192
    LS = dict(physical=0, render=4, owner=8, backend=12, tid=16, root=20,
              header=24, pixels=28, physical_pixels=56)
    def address(value, purpose): a.absolute(value, purpose)
    def st(name): return state + STATE[name]
    def read(reg, value, purpose):
        a.emit("8b" + f"{(reg << 3) | 5:02x}"); address(value, purpose)
    def write(reg, value, purpose):
        a.emit("89" + f"{(reg << 3) | 5:02x}"); address(value, purpose)
    def load(name): read(0, st(name), "state." + name)
    def store(name): write(0, st(name), "state." + name)
    def imm(name, value):
        a.emit("c705"); address(st(name), "state." + name); a.u32(value)
    def inc(name): a.emit("ff05"); address(st(name), "state." + name)
    def cmp_abs(value, immediate, purpose):
        a.emit("813d"); address(value, purpose); a.u32(immediate)
    def cmp_address(value, immediate, purpose):
        a.emit("813d"); address(value, purpose); address(immediate, purpose + " value")
    def cmp_state(name, value): cmp_abs(st(name), value, "state." + name)
    def local_operand(op, reg, offset):
        _require(type(offset) is int and 0 <= offset <= LOCAL + 32, "helper stack extent differs")
        if offset < 128:
            a.emit(op + f"{0x44 | (reg << 3):02x}" + "24" + f"{offset:02x}")
        else:
            a.emit(op + f"{0x84 | (reg << 3):02x}" + "24"); a.u32(offset)
    def local_store(reg, offset): local_operand("89",reg,offset)
    def local_read(reg, offset): local_operand("8b",reg,offset)
    def local_cmp(reg, offset): local_operand("3b",reg,offset)
    def ne(label): a.branch("0f85", label)
    def eq(label): a.branch("0f84", label)
    def transfer(op, target, purpose):
        a.emit(op); offset = len(a.code)
        a.relocations.append(assembler_module.Relocation(offset, "rel32", target, purpose))
        a.u32(target - base - offset - 4)
    def call(target, purpose): transfer("e8", target, purpose)
    def jump(target, purpose): transfer("e9", target, purpose)
    def thread(): a.emit("ff15"); address(THREAD_IAT, "GetCurrentThreadId IAT")
    def save(): a.emit("9c60fc81ec"); a.u32(LOCAL)
    def result(value):
        a.emit("b8"); a.u32(value); local_store(0,LOCAL+28)
        a.emit("81c4"); a.u32(LOCAL); a.emit("619dc3")
    def user_pointer(reg, size, reject):
        a.emit("81" + f"{0xf8 + reg:02x}"); a.u32(0x10000); a.branch("0f82", reject)
        a.emit("81" + f"{0xf8 + reg:02x}"); a.u32(0x80000000-size); a.branch("0f87", reject)
        a.emit("f7" + f"{0xc0 + reg:02x}" + "03000000"); ne(reject)
    def memory_header(reg, w, h, reject, private=False):
        user_pointer(reg, HEADER_BYTES, reject)
        outside_state_page(reg, HEADER_BYTES, reject)
        a.emit("81" + f"{0x38 + reg:02x}"); a.u32(w | (h << 16)); ne(reject)
        a.emit("81" + f"{0xb8 + reg:02x}" + "b8000000")
        address(MEMORY_VTABLE, "memory surface vtable"); ne(reject)
        a.emit("8b" + f"{0x40 + reg:02x}" + "04")
        user_pointer(0, w*h, reject)
        outside_state_page(0, w*h, reject)
        if private:
            a.emit("83" + f"{0xb8 + reg:02x}" + "ac00000000"); ne(reject)
    def primary(reject):
        cmp_abs(PRIMARY, width | (height << 16), "physical primary dimensions"); ne(reject)
        a.emit("813d"); address(PRIMARY+0xB8, "primary vtable"); address(PRIMARY_VTABLE, "primary vtable value"); ne(reject)
        cmp_abs(PRIMARY+0xD4, 8, "primary depth"); ne(reject)
        read(6, PRIMARY+0xBC, "primary backend"); user_pointer(6, 0xA8, reject)
        outside_state_page(6, 0xA8, reject)
        a.emit("83bea400000000"); eq(reject)
    def modal(reject, snapshot=False, local=False):
        if modal_state_va is None:
            return
        for offset in MODAL_LIVE:
            cmp_abs(modal_state_va+offset, 0, "inherited inactive owner"); ne(reject)
        read(0, modal_state_va+40, "inherited allocation count")
        a.emit("3b05"); address(modal_state_va+44, "inherited free count"); ne(reject)
        for index, (offset, name) in enumerate(MODAL_HISTORY):
            read(0, modal_state_va+offset, "inherited historical status")
            if snapshot:
                local_store(0, 32+index*4)
            elif local:
                local_cmp(0, 32+index*4); ne(reject)
            else:
                a.emit("3b05"); address(st(name), "state."+name); ne(reject)
    def callbacks_idle(reject):
        cmp_abs(LOWER, 0, "lower-row callback owner"); ne(reject)
        cmp_abs(POST, 0, "post-tile callback owner"); ne(reject)
    def snapshot_records():
        for offset in range(0,STATE_SIZE,4):
            read(0,state+offset,"immutable own state snapshot")
            local_store(0,OWN_SNAPSHOT+offset)
        if modal_state_va is not None:
            for offset in range(0,128,4):
                read(0,modal_state_va+offset,"immutable inherited state snapshot")
                local_store(0,MODAL_SNAPSHOT+offset)
    def stable_records(reject):
        for offset in range(0,STATE_SIZE,4):
            read(0,state+offset,"immutable own state revalidation")
            local_cmp(0,OWN_SNAPSHOT+offset); ne(reject)
        if modal_state_va is not None:
            for offset in range(0,128,4):
                read(0,modal_state_va+offset,"immutable inherited state revalidation")
                local_cmp(0,MODAL_SNAPSHOT+offset); ne(reject)
    rollback_globals = (MAP,RENDER,OWNER,LOWER,POST,BATTLE,PRIMARY,
                        PRIMARY+0xB8,PRIMARY+0xBC,PRIMARY+0xD4)
    def rollback_snapshot():
        snapshot_records()
        for index,value in enumerate(rollback_globals):
            read(0,value,"rollback callback global snapshot"); local_store(0,320+index*4)
    def rollback_stable(reject):
        stable_records(reject)
        for index,value in enumerate(rollback_globals):
            read(0,value,"rollback callback global revalidation")
            local_cmp(0,320+index*4); ne(reject)
    def entry_globals(reject):
        for value, offset, purpose in ((MAP,LS["physical"],"map identity"),
                (RENDER,LS["render"],"render identity"),(OWNER,LS["owner"],"owner identity"),
                (PRIMARY+0xBC,LS["backend"],"backend identity")):
            read(0,value,purpose); local_cmp(0,offset); ne(reject)
        read(7,MAP,"physical map"); memory_header(7,width,height,reject)
        local_cmp(0,LS["physical_pixels"]); ne(reject)
        primary(reject); callbacks_idle(reject); modal(reject,local=True)
        cmp_abs(BATTLE,0,"inactive native battle"); ne(reject)
    def entry_snapshot(reject):
        # The native allocator restores callee GPRs, but authority lives in
        # our bounded stack snapshot, not mutable state or callback booleans.
        thread(); local_cmp(0, LS["tid"]); ne(reject)
        stable_records(reject)
        cmp_state("phase", 3); ne(reject)
        cmp_state("fault", 0); ne(reject)
        for name, offset in (("physical",LS["physical"]),("saved_render",LS["render"]),
                             ("saved_owner",LS["owner"]),("saved_backend",LS["backend"]),
                             ("owner_tid",LS["tid"]),("root_esp",LS["root"]),
                             ("physical_pixels",LS["physical_pixels"])):
            load(name); local_cmp(0, offset); ne(reject)
        entry_globals(reject)
    def disjoint(reg, size, other_reg, other_size, reject, tag):
        # Pointer ranges have already been bounded. Half-open intervals may
        # touch but must not overlap; temporary arithmetic cannot wrap.
        a.emit("89"+f"{0xc0 | (reg << 3) | 2:02x}"+"81c2"); a.u32(size)
        a.emit("39"+f"{0xc0 | (2 << 3) | other_reg:02x}"); a.branch("0f83",tag)
        a.emit("89"+f"{0xc0 | (other_reg << 3) | 2:02x}"+"81c2"); a.u32(other_size)
        a.emit("39"+f"{0xc0 | (2 << 3) | reg:02x}"); a.branch("0f82",reject)
        a.label(tag)
    def outside_state_page(reg, size, reject):
        # The complete allocation is owned even though the current record
        # uses only 128 bytes. Padding cannot become a forged heap object.
        a.emit("b9"); address(state_page,"owned lifecycle RW page extent")
        disjoint(reg,size,1,4096,reject,reject+".rwpage"+str(len(a.code)))
    def allocation_interval(reg,size,reject,label,pixels=False):
        user_pointer(reg,size,reject)
        local_read(1,LS["physical"]); disjoint(reg,size,1,HEADER_BYTES,reject,label+".map_header")
        local_read(1,LS["physical_pixels"]); disjoint(reg,size,1,width*height,reject,label+".map_pixels")
        a.emit("b9"); address(0x400000,"parent image extent")
        disjoint(reg,size,1,image_extent,reject,label+".parent_image")
        a.emit("b9"); address(state_page,"lifecycle RW page extent"); disjoint(reg,size,1,4096,reject,label+".state")
        a.emit("b9"); address(base,"lifecycle code extent"); disjoint(reg,size,1,0x20000,reject,label+".code")
        a.emit("b9"); address(PRIMARY,"physical primary extent"); disjoint(reg,size,1,0xD8,reject,label+".primary")
        local_read(1,LS["backend"]); disjoint(reg,size,1,0xA8,reject,label+".backend")
        if modal_state_va is not None:
            a.emit("b9"); address(modal_state_va,"inherited state extent")
            disjoint(reg,size,1,128,reject,label+".modal")
        if pixels:
            local_read(1,LS["header"]); disjoint(reg,size,1,HEADER_BYTES,reject,label+".private_header")
    def saved_route(reject,tag):
        cmp_address(st("saved_owner"),MAP_OWNER,"saved ordinary map owner"); ne(reject)
        load("saved_render"); a.emit("3b05"); address(st("physical"),"saved physical render identity")
        eq(tag+".saved_render_ok")
        a.emit("3d"); address(PRIMARY,"saved primary render identity"); ne(reject)
        a.label(tag+".saved_render_ok")
    def owned(phase,reject,owner):
        cmp_state("phase",phase); ne(reject); cmp_state("fault",0); ne(reject)
        cmp_state("abort_reason",0); ne(reject)
        cmp_state("enter_status",1); ne(reject)
        cmp_state("leave_status",0); ne(reject); cmp_state("return_status",0); ne(reject)
        saved_route(reject,reject)
        snapshot_records()
        thread(); a.emit("3b05"); address(st("owner_tid"),"state.owner_tid"); ne(reject)
        stable_records(reject)
        primary(reject)
        a.emit("3b35"); address(st("saved_backend"),"state.saved_backend"); ne(reject)
        callbacks_idle(reject); modal(reject)
        read(7,MAP,"physical map"); a.emit("3b3d"); address(st("physical"),"state.physical"); ne(reject)
        memory_header(7,width,height,reject)
        a.emit("3b05"); address(st("physical_pixels"),"state.physical_pixels"); ne(reject)
        local_store(7,LS["physical"]); local_store(0,LS["physical_pixels"])
        read(0,PRIMARY+0xBC,"owned backend"); local_store(0,LS["backend"])
        cmp_address(OWNER,owner,"native render owner"); ne(reject)
        if phase in (1,2):
            read(7,st("native"),"state.native"); memory_header(7,640,480,reject,private=True)
            a.emit("3b05"); address(st("native_pixels"),"state.native_pixels"); ne(reject)
            local_store(7,LS["header"]); local_store(0,LS["pixels"])
            allocation_interval(7,HEADER_BYTES,reject,reject+".owned_header")
            local_read(0,LS["pixels"])
            allocation_interval(0,NATIVE_PIXELS,reject,reject+".owned_pixels",pixels=True)
            load("allocations"); a.emit("85c0"); eq(reject)
            a.emit("48"); a.emit("3b05"); address(st("frees"),"state.frees"); ne(reject)
            cmp_state("pending_header",0); ne(reject); cmp_state("pending_pixels",0); ne(reject)
        if phase == 2:
            load("battle"); a.emit("3b05"); address(BATTLE,"current bound native battle"); ne(reject)
            allocation_interval(0,BATTLE_BYTES,reject,reject+".owned_world",pixels=True)
            local_read(1,LS["pixels"])
            disjoint(0,BATTLE_BYTES,1,NATIVE_PIXELS,reject,reject+".owned_world_pixels")
        read(0,RENDER,"render identity"); a.emit("3b05"); address(st("physical"),"state.physical"); eq(reject+".render_ok")
        a.emit("3d"); address(PRIMARY,"physical primary"); eq(reject+".render_ok")
        if phase in (1,2):
            a.emit("3b05"); address(st("native"),"state.native"); ne(reject)
        else:
            ne(reject)
        a.label(reject+".render_ok")
    def clear_live():
        for name in LIVE:
            imm(name,0)
        for _,name in MODAL_HISTORY:
            imm(name,0)
    def destroy_private(reject,tag):
        load("saved_render"); write(0,RENDER,"restore render before private destruction")
        imm("phase",3); snapshot_records(); load("native"); a.emit("ba02000000")
        call(DTOR,"owned private scalar destructor")
        thread(); a.emit("3b05"); address(st("owner_tid"),"state.owner_tid"); ne(tag+".changed")
        stable_records(tag+".changed")
        load("saved_render"); a.emit("3b05"); address(RENDER,"retirement render identity"); ne(tag+".changed")
        read(7,MAP,"retirement map identity"); a.emit("3b3d"); address(st("physical"),"state.physical"); ne(tag+".changed")
        memory_header(7,width,height,tag+".changed")
        a.emit("3b05"); address(st("physical_pixels"),"state.physical_pixels"); ne(tag+".changed")
        primary(tag+".changed"); a.emit("3b35"); address(st("saved_backend"),"state.saved_backend"); ne(tag+".changed")
        callbacks_idle(tag+".changed"); modal(tag+".changed")
        cmp_address(OWNER,BATTLE_OWNER,"retirement native owner"); ne(tag+".changed")
        load("battle"); a.emit("3b05"); address(BATTLE,"retirement native battle"); ne(tag+".changed")
        imm("native",0); imm("native_pixels",0); inc("frees")
        a.branch("e9",tag+".done")
        # The destructor was called exactly once with an admitted receipt.
        # Never retry it after mutation; retain the failed lifetime diagnosis.
        a.label(tag+".changed"); imm("native",0); imm("native_pixels",0)
        local_read(0,OWN_SNAPSHOT+STATE["frees"]); a.emit("40"); store("frees")
        imm("phase",4); imm("fault",9); a.branch("e9",reject)
        a.label(tag+".done")

    a.label("try_enter"); save(); imm("enter_status",0)
    cmp_state("phase",0); ne("enter.reentry"); cmp_state("fault",0); ne("enter.reject")
    cmp_state("abort_reason",0); ne("enter.reject")
    for name in LIVE:
        cmp_state(name,0); ne("enter.reject")
    load("allocations"); a.emit("3b05"); address(st("frees"),"state.frees"); ne("enter.reject")
    modal("enter.reject",snapshot=True); primary("enter.reject"); callbacks_idle("enter.reject")
    cmp_abs(BATTLE,0,"inactive battle allocation"); ne("enter.reject")
    cmp_address(OWNER,MAP_OWNER,"ordinary map owner"); ne("enter.reject")
    read(7,MAP,"physical map"); memory_header(7,width,height,"enter.reject")
    local_store(7,LS["physical"]); local_store(0,LS["physical_pixels"])
    read(0,RENDER,"entry render device"); a.emit("3b05"); address(MAP,"map surface"); eq("enter.render_ok")
    a.emit("3d"); address(PRIMARY,"primary surface"); ne("enter.reject")
    a.label("enter.render_ok"); local_store(0,LS["render"])
    read(0,OWNER,"entry owner"); local_store(0,LS["owner"])
    read(0,PRIMARY+0xBC,"entry backend"); local_store(0,LS["backend"])
    snapshot_records(); thread(); a.emit("85c0"); eq("enter.reject"); local_store(0,LS["tid"])
    stable_records("enter.reject")
    entry_globals("enter.reject")
    local_read(0,LOCAL+28); user_pointer(0,8,"enter.reject"); local_store(0,LS["root"])
    for name,offset in (("physical",LS["physical"]),("physical_pixels",LS["physical_pixels"]),
                        ("saved_render",LS["render"]),("saved_owner",LS["owner"]),
                        ("saved_backend",LS["backend"]),("owner_tid",LS["tid"]),("root_esp",LS["root"])):
        local_read(0,offset); store(name)
    imm("phase",3); imm("leave_status",0); imm("return_status",0)
    a.emit("c744241800000000c744241c00000000")
    snapshot_records()
    a.emit("b8bc000000"); call(ALLOC,"nonfatal private header allocation"); a.emit("85c0"); eq("enter.allocation_failed")
    allocation_interval(0,HEADER_BYTES,"enter.untrusted","header")
    local_store(0,LS["header"]); stable_records("enter.changed")
    local_read(0,LS["header"]); store("pending_header")
    local_store(0,OWN_SNAPSHOT+STATE["pending_header"]); entry_snapshot("enter.changed")
    a.emit("b8"); a.u32(NATIVE_PIXELS); call(ALLOC,"nonfatal private pixel allocation")
    a.emit("85c0"); eq("enter.allocation_failed")
    allocation_interval(0,NATIVE_PIXELS,"enter.untrusted","pixels",pixels=True)
    local_store(0,LS["pixels"]); stable_records("enter.changed")
    local_read(0,LS["pixels"]); store("pending_pixels")
    local_store(0,OWN_SNAPSHOT+STATE["pending_pixels"]); entry_snapshot("enter.changed")
    local_read(7,LS["pixels"]); a.emit("31c0b9002c0100f3ab")
    local_read(0,LS["header"]); a.emit("ba80020000bbe0010000")
    call(CTOR,"nonallocating native base constructor")
    local_cmp(0,LS["header"]); ne("enter.rollback")
    entry_snapshot("enter.changed")
    local_read(7,LS["header"]); local_read(0,LS["pixels"]); a.emit("894704c787b8000000")
    address(MEMORY_VTABLE,"private memory vtable")
    memory_header(7,640,480,"enter.rollback",private=True)
    local_cmp(0,LS["pixels"]); ne("enter.rollback")
    local_read(0,LS["header"]); store("native")
    local_read(0,LS["pixels"]); store("native_pixels")
    if modal_state_va is not None:
        for index,(_,name) in enumerate(MODAL_HISTORY):
            local_read(0,32+index*4); store(name)
    imm("pending_header",0); imm("pending_pixels",0); inc("allocations")
    imm("phase",1); imm("enter_status",1); result(1)
    a.label("enter.allocation_failed"); entry_snapshot("enter.changed"); a.branch("e9","enter.rollback")
    a.label("enter.changed"); imm("fault",4)
    a.label("enter.rollback"); thread(); local_cmp(0,LS["tid"]); ne("enter.untrusted")
    local_read(0,LS["pixels"]); a.emit("85c0"); eq("enter.rollback_header")
    rollback_snapshot(); local_read(0,LS["pixels"])
    call(FREE,"rollback uncommitted private pixels")
    thread(); local_cmp(0,LS["tid"]); ne("enter.pixels_retired_changed")
    rollback_stable("enter.pixels_retired_changed")
    imm("pending_pixels",0); a.emit("c744241c00000000")
    a.label("enter.rollback_header"); local_read(0,LS["header"]); a.emit("85c0"); eq("enter.rollback_done")
    rollback_snapshot(); local_read(0,LS["header"])
    call(FREE,"rollback uncommitted private header")
    thread(); local_cmp(0,LS["tid"]); ne("enter.header_retired_changed")
    rollback_stable("enter.header_retired_changed")
    imm("pending_header",0); a.emit("c744241800000000")
    a.label("enter.rollback_done"); clear_live(); imm("phase",0); result(0)
    a.label("enter.pixels_retired_changed"); imm("pending_pixels",0); a.branch("e9","enter.untrusted")
    a.label("enter.header_retired_changed"); imm("pending_header",0); a.branch("e9","enter.untrusted")
    # An invalid/aliased allocator result is not a receipt permitting a free.
    # Keep pending diagnostics, fault and the staging phase; never free a map
    # or caller-selected pointer to turn that inconsistency into a clean pass.
    a.label("enter.untrusted"); imm("fault",6); result(0)
    a.label("enter.reentry"); imm("fault",5)
    a.label("enter.reject"); result(0)

    a.label("bind_or_abort"); save(); owned(1,"bind.reject",BATTLE_OWNER)
    load("root_esp"); a.emit("2da8000000"); local_cmp(0,LOCAL+20); ne("bind.reject")
    local_read(0,LOCAL+28); a.emit("3b05"); address(BATTLE,"native battle allocation"); ne("bind.reject")
    a.emit("85c0"); eq("bind.abort")
    allocation_interval(0,BATTLE_BYTES,"bind.reject","bound_world",pixels=True)
    local_read(1,LS["pixels"]); disjoint(0,BATTLE_BYTES,1,NATIVE_PIXELS,"bind.reject","bound_world.private_pixels")
    store("battle"); imm("phase",2); result(1)
    a.label("bind.abort"); destroy_private("bind.destroy_reject","abort_destroy")
    clear_live(); imm("abort_reason",1); imm("phase",0); result(0)
    a.label("bind.destroy_reject"); imm("abort_reason",1); result(0)
    a.label("bind.reject"); imm("fault",7); result(0)

    a.label("try_leave"); save(); owned(2,"leave.reject",BATTLE_OWNER)
    load("root_esp"); a.emit("2dac000000"); local_cmp(0,LOCAL+28); ne("leave.reject")
    load("battle"); a.emit("3b05"); address(BATTLE,"bound native battle allocation"); ne("leave.reject")
    destroy_private("leave.destroy_reject","leave_destroy"); imm("phase",4); imm("leave_status",1); result(1)
    a.label("leave.destroy_reject"); result(0)
    a.label("leave.reject"); imm("leave_status",0); imm("fault",8); result(0)

    a.label("finish_return"); save(); cmp_state("return_status",0); ne("return.reject")
    cmp_state("phase",4); ne("return.reject"); cmp_state("fault",0); ne("return.reject")
    cmp_state("abort_reason",0); ne("return.reject"); saved_route("return.reject","return")
    cmp_state("enter_status",1); ne("return.reject"); cmp_state("leave_status",1); ne("return.reject")
    for name in ("native","native_pixels","pending_header","pending_pixels"):
        cmp_state(name,0); ne("return.reject")
    snapshot_records()
    thread(); a.emit("3b05"); address(st("owner_tid"),"state.owner_tid"); ne("return.reject")
    stable_records("return.reject")
    load("root_esp"); a.emit("2da8000000"); local_cmp(0,LOCAL+28); ne("return.reject")
    cmp_abs(BATTLE,0,"native allocation cleared after free"); ne("return.reject")
    load("saved_owner"); a.emit("3b05"); address(OWNER,"native restored owner"); ne("return.reject")
    load("saved_render"); a.emit("3b05"); address(RENDER,"restored render identity"); ne("return.reject")
    read(7,MAP,"restored map identity"); a.emit("3b3d"); address(st("physical"),"state.physical"); ne("return.reject")
    memory_header(7,width,height,"return.reject"); a.emit("3b05"); address(st("physical_pixels"),"state.physical_pixels"); ne("return.reject")
    local_store(7,LS["physical"]); local_store(0,LS["physical_pixels"])
    primary("return.reject"); a.emit("3b35"); address(st("saved_backend"),"state.saved_backend"); ne("return.reject")
    local_store(6,LS["backend"])
    callbacks_idle("return.reject"); modal("return.reject")
    load("allocations"); a.emit("85c0"); eq("return.reject")
    a.emit("3b05"); address(st("frees"),"state.frees"); ne("return.reject")
    load("battle"); allocation_interval(0,BATTLE_BYTES,"return.reject","returned_world")
    clear_live(); imm("phase",0); imm("return_status",1); result(1)
    a.label("return.reject"); result(0)

    # Adapters describe the native JMP/CALL shapes but are never installed.
    a.label("root_entry"); a.emit("9c608d442424"); a.branch("e8","try_enter")
    a.emit("619d"+SITES["root_entry"][1]); jump(0x42E9E9,"native root continuation")
    a.label("bind_allocation"); a.emit("9c608d542424"); read(0,BATTLE,"native allocation result")
    a.branch("e8","bind_or_abort"); a.emit("619d833d"); address(BATTLE,"native allocation predicate")
    a.emit("00"); jump(0x42EC97,"original null/fatal predicate continuation")
    a.label("leave_before_free"); a.emit("9c608d442424"); a.branch("e8","try_leave")
    a.emit("619d"); jump(FREE,"original battle allocation free, unchanged CALL return")
    a.label("root_epilogue"); a.emit("9c608d442424"); a.branch("e8","finish_return")
    a.emit("619d"+SITES["root_epilogue"][1]); jump(0x42F5B9,"native pops and RET4 continuation")
    code = a.finish()
    _require(0 < len(code) < plan["rx"]["virtual_reservation"] == 0x20000,
             "lifecycle code exceeds authenticated reservation")
    entries = tuple((name,base+offset) for name,offset in a.labels.items() if "." not in name)
    emission = CodeEmission(base,state,code,entries,tuple(a.relocations),width,height)
    assembler_module.absolute_relocation_offsets(emission)
    return emission


def _check_parent_root(original_root, candidate_root, *, file_offset, profile, parent_metadata, plan):
    """Exact bounded predecessor delta; public reconstruction supplies authority.

    This fixture boundary admits no generic patch window. The sole inherited
    non-Classic difference is the pinned combined-UI centered-present CALL.
    The public producer separately authenticates the whole original root.
    """
    lo,hi,_ = NATIVE_SPANS["root"]
    _require(type(original_root) is type(candidate_root) is bytes and
             len(original_root) == len(candidate_root) == hi-lo and
             type(file_offset) is int and file_offset == 0x02DDE0,
             "native root span bounds differ")
    _require(type(plan) is dict and type(parent_metadata) is dict and
             profile in ("classic","framed","completehd","modalwidgets") and
             plan.get("profile") == profile and plan.get("original_sha256") == BASE_SHA256 and
             parent_metadata.get("base_sha256") == BASE_SHA256 and
             parent_metadata.get("resolution") == plan.get("resolution") and
             parent_metadata.get("stage") == plan.get("parent_stage") and
             parent_metadata.get("recipe_revision") == plan.get("parent_revision") and
             parent_metadata.get("candidate_sha256") == plan.get("candidate_sha256"),
             "reconstructed native root parent identity differs")
    rows = parent_metadata.get("patch_records")
    _require(type(rows) is list,"native root owning record inventory missing")
    overlap = []
    for row in rows:
        _require(type(row) is dict,"native root owning record type differs")
        va,new_hex = row.get("va"),row.get("new_hex")
        if type(va) is int and type(new_hex) is str and va < hi and va+len(new_hex)//2 > lo:
            overlap.append(row)
    expected = bytearray(original_root)
    at = ROOT_PRESENT_VA-lo
    _require(original_root[at:at+5] == bytes.fromhex(ROOT_PRESENT_OLD),
             "original native present CALL differs")
    if profile == "classic":
        _require(not overlap and candidate_root == original_root,
                 "Classic native root must remain exact original")
        return dict(rule="exact_original",candidate_root_sha256=_sha(original_root),edits=[])
    expected[at:at+5] = bytes.fromhex(ROOT_PRESENT_NEW)
    _require(candidate_root == bytes(expected),"native root has an undeclared predecessor edit")
    _require(len(overlap) == 1,"native root owning record missing or duplicate")
    row = overlap[0]
    groups = dict(framed="framed-all-presets-integrated",completehd="complete-hd-all-presets-integrated",
                  modalwidgets="modal-widgets-all-presets-integrated")
    required = dict(appended=False,file_offset=ROOT_PRESENT_OFFSET+1,offset=ROOT_PRESENT_OFFSET+1,
        va=ROOT_PRESENT_VA+1,rva=ROOT_PRESENT_VA+1-0x400000,old_hex="a61b03",new_hex="06c70e",
        group=groups[profile],stage=plan["parent_stage"])
    _require(all(type(row.get(key)) is type(value) and row.get(key) == value
                 for key,value in required.items()),"native root final owning record differs")
    recipe = parent_metadata
    for key in ROOT_RECIPE_PATHS[profile]:
        _require(type(recipe) is dict and type(recipe.get(key)) is dict,
                 "native root semantic owner ancestry missing")
        recipe = recipe[key]
    _require(recipe.get("resolution") == plan["resolution"] and
             recipe.get("original_sha256") == BASE_SHA256,
             "native root semantic owner identity differs")
    semantic = recipe.get("patches")
    _require(type(semantic) is list,"native root semantic patch inventory missing")
    owned = [item for item in semantic if type(item) is dict and
             (item.get("file_offset") == ROOT_PRESENT_OFFSET or item.get("va") == ROOT_PRESENT_VA)]
    declared = dict(group="battle-ui-center-present-wrapper",file_offset=ROOT_PRESENT_OFFSET,
        va=ROOT_PRESENT_VA,rva=ROOT_PRESENT_VA-0x400000,old_hex=ROOT_PRESENT_OLD,new_hex=ROOT_PRESENT_NEW,
        rationale="0x42F2F5 battle initial Render_Present call -> 0x51BA00 battle-only native-centering present wrapper")
    _require(len(owned) == 1 and all(type(owned[0].get(key)) is type(value) and owned[0].get(key) == value
                 for key,value in declared.items()),"native root semantic CALL owner differs")
    for role,(name,digest) in ROOT_EDIT_PINS.items():
        bindings = recipe.get("source_bindings",{})
        _require(type(bindings) is dict and type(bindings.get(role)) is dict and
                 bindings[role].get("path") == str(ROOT/name) and bindings[role].get("sha256") == digest and
                 plan.get("source_hashes",{}).get(name) == digest and
                 parent_metadata.get("source_hashes",{}).get(name) == digest,
                 "native root semantic owner source differs: "+name)
    return dict(rule="one_exact_inherited_centered_present_call",candidate_root_sha256=_sha(bytes(expected)),
        edits=[declared],final_owning_record=required,source_pins=ROOT_EDIT_PINS,
        semantic_owner_path=list(ROOT_RECIPE_PATHS[profile]))


def _authenticate_native(original, candidate, pe, clip, *, profile, parent_metadata, plan):
    root_contract = None
    for name,(lo,hi,digest) in NATIVE_SPANS.items():
        for is_parent,image in ((False,original),(True,candidate)):
            view = pe.inspect_pe(image)
            offset = view.file_offset(lo-view.image_base,hi-lo)
            if name == "root" and is_parent:
                old_view = pe.inspect_pe(original)
                old_offset = old_view.file_offset(lo-old_view.image_base,hi-lo)
                _require(offset == old_offset,"native root section offset changed")
                root_contract = _check_parent_root(original[old_offset:old_offset+hi-lo],image[offset:offset+hi-lo],
                    file_offset=old_offset,profile=profile,parent_metadata=parent_metadata,plan=plan)
                continue
            _require(_sha(image[offset:offset+hi-lo]) == digest, "native lifecycle span differs: "+name)
    for va,value,_ in SITES.values():
        expected = bytes.fromhex(value)
        for image in (original,candidate):
            offset = clip.file_offset(image,va,len(expected))
            _require(image[offset:offset+len(expected)] == expected, "native lifecycle old bytes differ")
    # The whole-original identity and existing fixed parent verification bind
    # the constructor/destructor and import ABI. Check TID by its import name.
    view = pe.inspect_pe(original)
    rva,_ = struct.unpack_from("<II",original,view.optional_offset+104)
    cursor = view.file_offset(rva,20)
    threads = []
    while True:
        lookup,stamp,chain,name,iat = struct.unpack_from("<IIIII",original,cursor)
        if not any((lookup,stamp,chain,name,iat)):
            break
        index = 0
        while True:
            entry, = struct.unpack_from("<I",original,view.file_offset((lookup or iat)+index*4,4))
            if not entry:
                break
            if not entry & 0x80000000:
                start = view.file_offset(entry+2,1)
                end = original.index(0,start)
                if original[start:end] == b"GetCurrentThreadId":
                    threads.append(view.image_base+iat+index*4)
            index += 1
        cursor += 20
    _require(threads == [THREAD_IAT], "native thread identity import differs")
    return root_contract


def _emit_authenticated(original: bytes, profile: str, resolution: str) -> BattleProfileLifecycleBundle:
    _require(type(original) is bytes and _sha(original) == BASE_SHA256, "exact original required; no context override")
    snapshot = _snapshot()
    _require(globals().get("__loaded_source_sha256__") == _sha(snapshot[SOURCE][0]),
             "privately compiled lifecycle source required")
    with _modules(snapshot) as modules:
        context = modules[CONTEXT]
        parent = context.build_parent_context(original,profile,resolution)
        plan = parent.allocation_plan()
        pe,clip = modules["src/patcher/pe_extension.py"],modules["src/patcher/partial_tile_clip.py"]
        root_contract = _authenticate_native(original,parent.candidate,pe,clip,profile=profile,
                                            parent_metadata=parent.parent_metadata(),plan=plan)
        inventory = plan["inherited_state_inventory"]
        modal_state = None if inventory is None else inventory["page_va"]
        emission = _emit_code(plan,modal_state_va=modal_state,assembler_module=clip)
        entries = dict(emission.entries)
        hooks,removed = [],[]
        for name,(va,value,_) in SITES.items():
            old = bytes.fromhex(value)
            op = b"\xe8" if name == "leave_before_free" else b"\xe9"
            new = op + struct.pack("<i",entries[name]-va-5) + b"\x90"*(len(old)-5)
            hooks.append(pe.HookPatch(clip.file_offset(parent.candidate,va,len(old)),va-0x400000,va,
                         old,new,"battle_profile_lifecycle."+name,
                         (pe.CodeRelocation(1,"rel32",entries[name],name),)))
            removed.extend(va-0x400000+offset for offset in clip._original_highlow_fields(original,va,len(old)))
        metadata = dict(schema="clash95_battle_profile_lifecycle_v1",profile=profile,resolution=resolution,
            parent_stage=plan["parent_stage"],parent_revision=plan["parent_revision"],
            original_sha256=BASE_SHA256,parent_candidate_sha256=plan["candidate_sha256"],
            canonical_probe_sha256=plan["canonical_probe_sha256"],allocation_plan=plan,
            source_hashes=plan["source_hashes"] | {name:_sha(data) for name,(data,_) in snapshot.items()},
            code_sha256=_sha(emission.code),code_bytes=len(emission.code),state_va=emission.state_va,
            state_bytes=STATE_SIZE,state_offsets=STATE,modal_state_va=modal_state,
            phases=dict(empty=0,prepared=1,bound=2,cleaning=3,awaiting_native_return=4),
            native_spans={name:dict(start=lo,end_exclusive=hi,sha256=digest) for name,(lo,hi,digest) in NATIVE_SPANS.items()},
            inherited_native_root_contract=root_contract,
            native_root_body_esp_delta=-168,native_free_call_esp_delta=-172,
            native_root_return=0x42F5BC,native_root_stack_cleanup=4,
            helper_stack_snapshot_bytes=384,inherited_state_snapshot_bytes=0 if modal_state is None else 128,
            protected_state_page_va=emission.state_va if modal_state is None else modal_state,
            protected_state_page_bytes=4096,
            allocation_plan_only=False,emission_preparation_only=True,installed=False,
            **{name:False for name in context.FALSE_CLAIMS},
            required_unemitted_families=["native HUD target/draw/composition routing", "field and input admission",
                "per-animation-step presentation", "camera/saved views", "dialogs/results restoration",
                "general App_RequestQuit/App_Shutdown and CRT termination interception",
                "message-queue quit mode-switch handling", "complete atomic successor and canonical probe"],
            limitations=["Uninstalled preparation; helper truth values supply no expanded-battle or runtime acceptance.",
                "Native allocation-null rollback preserves the original fatal branch; it proves no healthy map return.",
                "Pending native return requires its separate checkpoint after private retirement.",
                "Invalid allocator receipts or foreign-thread rollback remain failed diagnostics, not invented cleanups.",
                "Source address/byte bounds do not prove dynamic heap lifetime, native callbacks or loader behavior."])
    _unchanged(snapshot)
    return BattleProfileLifecycleBundle(emission,tuple(hooks),tuple(sorted(set(removed))),
        json.dumps(metadata,sort_keys=True,separators=(",",":"),allow_nan=False))


def emit_battle_profile_lifecycle(original: bytes, profile: str, resolution: str) -> BattleProfileLifecycleBundle:
    """Use a fresh private producer, including this module's loaded constants."""
    snapshot = _snapshot()
    with _modules(snapshot) as modules:
        result = modules[SOURCE]._emit_authenticated(original,profile,resolution)
    _unchanged(snapshot)
    return result


emit_lifecycle = emit_battle_profile_lifecycle
