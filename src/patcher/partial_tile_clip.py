"""Offline x86 clipping building blocks for a future partial-tile validation stage.

This module does not modify a binary, install a vtable, or launch a process.
The emitted adapters and edge dispatcher are executable building blocks, not an
installed patch. Caller composition ordering and runtime evidence remain open.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct

from .framed_viewport import FramedViewport


ORIGINAL_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
MAP_SURFACE_GLOBAL = 0x005202E0
GAME_DATA_GLOBAL = 0x005202E4
RENDER_DEVICE_GLOBAL = 0x00511230
TILE_CALLBACK_GLOBAL = 0x0052698C
LOWER_ROW_OWNER_GLOBAL = 0x00526994
CURSOR_VISIBLE_GLOBAL = 0x00544D10
RENDER_HOOK_GLOBAL = 0x005199D8
POST_TILE_CALLBACK_GLOBAL = 0x00526990
CURRENT_PLAYER_GLOBAL = 0x005202EC
COMMAND_SPRITES_GLOBAL = 0x0052030C
TURN_SPRITES_GLOBAL = 0x005202DC
COMMAND_DESCRIPTORS = 0x00511D40
TOOLTIP_SURFACE_GLOBAL = 0x00526EF4
TOOLTIP_BOUNDS = (0x526EF8, 0x526EFC, 0x526F00, 0x526F04)
MEMORY_VTABLE = 0x0050EE24
NATIVE_TARGETS = {"line": 0x00403F70, "outline": 0x00404040,
                  "fill": 0x004040F0, "sprite": 0x00402E80,
                  "tile": 0x00416850, "dirty": 0x00460BB0,
                  "blit": 0x004024E0, "cursor": 0x00460EA0,
                  "descriptors": 0x00419D80,
                  "turn_sprite_lookup": 0x00405EC0, "turn_select_font": 0x0040BAE0,
                  "turn_text_format": 0x0040C150, "turn_text_color": 0x0040BB60,
                  "turn_text_draw": 0x0040BE50, "minimap": 0x0040D560}
VTABLE_ENTRIES = (
    0x403E50, 0x403EB0, 0x403EF0, 0x403F30, 0x403F50,
    0x403F70, 0x404040, 0x4040F0, 0x401E90, 0x401E30,
    0x404160, 0x401FA0, 0x4020A0, 0x402E80, 0x401E60,
    0x405640, 0x405650, 0, 0, 0,
)
NATIVE_BYTES = {
    # The tile loops do not contain an extra partial-row/column branch.
    0x41876E: "83f9097cc4",
    0x41877F: "83ff067ca1",
    0x4189FD: "83f9067cc3",
    0x418AA4: "83c10939c87d4f",
    0x418AB1: "83c10739ca7d42",
    # Unbounded software write iterator: width*y + pixels + x.
    0x403F03: "5631f6668b310fafde8b4904c70094ed500001d989700801d18948045e59c3",
    # Memory sprite decoder entry; its four explicit clip args are optional.
    0x402E80: "56575589e581ec0401000083ed6a",
}


def file_offset(data: bytes, va: int, size: int) -> int:
    """Map a VA through this PE's real sections, including zero VirtualSize."""
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("invalid PE signature")
    count, optional = struct.unpack_from("<H", data, pe + 6)[0], struct.unpack_from("<H", data, pe + 20)[0]
    image_base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    rva = va - image_base
    for index in range(count):
        pos = pe + 24 + optional + 40 * index
        virtual_size, start, raw_size, raw = struct.unpack_from("<IIII", data, pos + 8)
        if start <= rva and rva + size <= start + max(virtual_size, raw_size):
            offset = raw + rva - start
            if rva - start + size > raw_size or offset + size > len(data):
                raise ValueError("VA has no file-backed bytes")
            return offset
    raise ValueError(f"VA 0x{va:08X} is outside PE sections")


def verify_original(data: bytes) -> None:
    if hashlib.sha256(data).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("unknown original executable SHA-256")
    expectations = dict(NATIVE_BYTES)
    expectations[MEMORY_VTABLE] = struct.pack("<20I", *VTABLE_ENTRIES).hex()
    for va, expected_hex in expectations.items():
        expected = bytes.fromhex(expected_hex)
        off = file_offset(data, va, len(expected))
        if data[off:off + len(expected)] != expected:
            raise ValueError(f"native ABI bytes differ at 0x{va:08X}")


@dataclass(frozen=True)
class Relocation:
    offset: int
    kind: str
    target: int
    purpose: str


@dataclass(frozen=True)
class AdapterBundle:
    base_va: int
    code: bytes
    entries: dict[str, int]
    relocations: tuple[Relocation, ...]
    width: int
    height: int
    installation_ready: bool = False


def absolute_relocation_offsets(bundle: AdapterBundle) -> tuple[int, ...]:
    """Validate declared fields and return PE HIGHLOW locations within code.

    Every image VA is emitted through _Assembler.absolute, including nonzero
    cloned-vtable entries. Native transfers are rel32 and must not be placed in
    PE base relocations. x86 immediate locations can be unaligned. This checks
    the supplied metadata against bytes; semantic completeness is additionally
    exercised by the independent rebased x86 fixtures, not inferred by scanning
    numbers that merely resemble addresses.
    """
    fields=[];absolute=[]
    for relocation in bundle.relocations:
        pos=relocation.offset
        if type(pos) is not int or pos < 0 or pos+4 > len(bundle.code):
            raise ValueError("relocation lies outside emitted code")
        if any(pos < other+4 and other < pos+4 for other in fields):
            raise ValueError("duplicate or overlapping relocation fields")
        fields.append(pos)
        if relocation.kind=="abs32":
            if not 0 < relocation.target <= 0xFFFFFFFF:
                raise ValueError("invalid nonzero image VA relocation")
            expected=relocation.target;absolute.append(pos)
        elif relocation.kind=="rel32":
            expected=(relocation.target-(bundle.base_va+pos+4)) & 0xFFFFFFFF
        else:raise ValueError("unknown relocation kind")
        if struct.unpack_from("<I",bundle.code,pos)[0] != expected:
            raise ValueError("relocation metadata does not match emitted bytes")
    return tuple(sorted(absolute))


def _original_highlow_fields(original: bytes, start_va: int, size: int) -> set[int]:
    """Read authenticated PE HIGHLOW fields for a bounded native-code clone."""
    pe=struct.unpack_from("<I",original,0x3C)[0]
    image_base=struct.unpack_from("<I",original,pe+24+28)[0]
    rva,total=struct.unpack_from("<II",original,pe+24+96+5*8)
    pos=file_offset(original,image_base+rva,total);end=pos+total;result=set()
    while pos<end:
        page,block=struct.unpack_from("<II",original,pos)
        if block<8 or block%2 or pos+block>end:raise ValueError("invalid native relocation block")
        for offset in range(pos+8,pos+block,2):
            entry=struct.unpack_from("<H",original,offset)[0]
            kind=entry>>12;va=image_base+page+(entry&0xFFF)
            if start_va<=va<start_va+size:
                if kind==0:continue
                if kind!=3 or va+4>start_va+size:raise ValueError("unsupported clone relocation")
                if va-start_va in result:raise ValueError("duplicate native clone relocation")
                result.add(va-start_va)
        pos+=block
    return result


class _Assembler:
    def __init__(self, base: int):
        self.base = base
        self.code = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str]] = []
        self.relocations: list[Relocation] = []

    def emit(self, value: str) -> None:
        self.code.extend(bytes.fromhex(value))

    def u32(self, value: int) -> None:
        self.code.extend(struct.pack("<I", value & 0xFFFFFFFF))

    def label(self, name: str) -> None:
        if name in self.labels:
            raise ValueError("duplicate assembly label")
        self.labels[name] = len(self.code)

    def branch(self, opcode: str, label: str) -> None:
        self.emit(opcode)
        self.fixups.append((len(self.code), label))
        self.u32(0)

    def absolute(self, value: int, purpose: str) -> None:
        self.relocations.append(Relocation(len(self.code), "abs32", value, purpose))
        self.u32(value)

    def native_jump(self, name: str) -> None:
        self.native_transfer(name, "e9")

    def native_transfer(self, name: str, opcode: str = "e8") -> None:
        self.emit(opcode)
        pos = len(self.code)
        target = NATIVE_TARGETS[name]
        self.relocations.append(Relocation(pos, "rel32", target, name))
        self.u32(target - (self.base + pos + 4))

    def finish(self) -> bytes:
        for pos, label in self.fixups:
            struct.pack_into("<i", self.code, pos, self.labels[label] - pos - 4)
        return bytes(self.code)


def emit_adapters(original: bytes, *, base_va: int, width: int, height: int,
                  _clipped_vtable_va: int | None = None,
                  clip_origin: tuple[int, int] = (0, 0),
                  clip_end: tuple[int, int] | None = None) -> AdapterBundle:
    """Emit native-ABI adapters with a strict target/geometry guard.

    Native vtable installation is deliberately not provided. Adapters accept
    only the authenticated memory vtable and the current map surface pointer;
    they can be invoked by a future separately reviewed dispatch hook. The
    sprite path intersects existing inclusive clip bounds, preserves the three
    remaining stack arguments, and delegates decoding to the native function.
    """
    verify_original(original)
    if not (32 < width <= 8192 and 16 < height <= 8192):
        raise ValueError("unsupported clipping geometry")
    if not (0x10000 <= base_va <= 0x7FFF0000):
        raise ValueError("invalid x86 code allocation")
    if (len(clip_origin) != 2 or any(type(v) is not int for v in clip_origin)
            or not 0 <= clip_origin[0] < width or not 0 <= clip_origin[1] < height):
        raise ValueError("invalid clipping origin")
    end_x, end_y = (width - 1, height - 1) if clip_end is None else clip_end
    if (type(end_x) is not int or type(end_y) is not int
            or not clip_origin[0] <= end_x < width or not clip_origin[1] <= end_y < height):
        raise ValueError("invalid clipping end")
    a = _Assembler(base_va)

    def guard(name: str) -> None:
        a.label(name)
        a.emit("6089e58b451c3b05")  # pushad; frame; saved EAX == map surface
        a.absolute(MAP_SURFACE_GLOBAL, "map_surface_global")
        a.branch("0f85", name + ".reject")
        a.emit("85c0")
        a.branch("0f84", name + ".reject")
        a.emit("668138" + struct.pack("<H", width).hex())
        a.branch("0f85", name + ".reject")
        a.emit("66817802" + struct.pack("<H", height).hex())
        a.branch("0f85", name + ".reject")
        a.emit("83780400")
        a.branch("0f84", name + ".reject")
        a.emit("81b8b8000000")
        a.absolute(MEMORY_VTABLE, "memory_vtable")
        if _clipped_vtable_va is not None:
            a.branch("0f84", name + ".target")
            a.emit("81b8b8000000")
            a.absolute(_clipped_vtable_va, "clipped_vtable")
        a.branch("0f85", name + ".reject")
        a.label(name + ".target")

    def intersect(name: str) -> None:
        # EDX left, ECX right, EBX top, EDI bottom; all comparisons signed.
        a.emit("39ca")
        a.branch("0f8f", name + ".reject")
        a.emit("39fb")
        a.branch("0f8f", name + ".reject")
        a.emit("81fa"); a.u32(clip_origin[0])
        a.branch("0f8d", name + ".left")
        a.emit("ba"); a.u32(clip_origin[0])
        a.label(name + ".left")
        a.emit("81f9"); a.u32(end_x)
        a.branch("0f8e", name + ".right")
        a.emit("b9"); a.u32(end_x)
        a.label(name + ".right")
        a.emit("81fb"); a.u32(clip_origin[1])
        a.branch("0f8d", name + ".top")
        a.emit("bb"); a.u32(clip_origin[1])
        a.label(name + ".top")
        a.emit("81ff"); a.u32(end_y)
        a.branch("0f8e", name + ".bottom")
        a.emit("bf"); a.u32(end_y)
        a.label(name + ".bottom")
        a.emit("39ca")
        a.branch("0f8f", name + ".reject")
        a.emit("39fb")
        a.branch("0f8f", name + ".reject")

    def reject(name: str, pop: int) -> None:
        a.label(name + ".reject")
        a.emit("6131c0c2" + struct.pack("<H", pop).hex())

    for name in ("line", "fill"):
        guard(name)
        a.emit("8b55148b4d188b5d108b7d24")
        if name == "line":
            # Native line routine supports horizontal or vertical segments.
            a.emit("39ca")
            a.branch("0f84", "line.axis")
            a.emit("39fb")
            a.branch("0f85", "line.reject")
            a.label("line.axis")
        intersect(name)
        a.emit("895514894d18895d10897d2461")
        a.native_jump(name)
        reject(name, 8)

    guard("sprite")
    # Bound coordinate arithmetic, which the decoder performs as signed int32.
    for offset in (0x10, 0x18):
        a.emit("8b45" + bytes([offset]).hex() + "3d"); a.u32(-65535)
        a.branch("0f8c", "sprite.reject")
        a.emit("3d"); a.u32(65535)
        a.branch("0f8f", "sprite.reject")
    a.emit("8b451485c0")  # saved EDX = sprite pointer
    a.branch("0f84", "sprite.reject")
    a.emit("8b55248b4d2c8b5d288b7d30")
    for register_cmp in ("83faff", "83f9ff", "83fbff", "83ffff"):
        a.emit(register_cmp)
        a.branch("0f85", "sprite.explicit")
    a.emit("31d231dbb9"); a.u32(end_x)
    a.emit("bf"); a.u32(end_y)
    a.label("sprite.explicit")
    intersect("sprite")
    a.emit("895524894d2c895d28897d3061")
    a.native_jump("sprite")
    reject("sprite", 28)

    guard("outline")
    a.emit("8b55148b4d188b5d108b7d2439ca")
    a.branch("0f8f", "outline.reject")
    a.emit("39fb")
    a.branch("0f8f", "outline.reject")
    # Clip the FOUR ORIGINAL segments. Intersecting a rectangle first would
    # manufacture a new visible border where its original edge was offscreen.
    for setup in (
        "8b55148b4d188b5d1089df",  # original top
        "8b55148b4d188b5d2489df",  # original bottom
        "8b551489d18b5d108b7d24",  # original left
        "8b551889d18b5d108b7d24",  # original right
    ):
        a.emit(setup)
        a.emit("8b451c8b752881e6ff000000555657")
        a.branch("e8", "line")
        a.emit("5d")
    a.emit("89451c61c20800")
    reject("outline", 8)
    code = a.finish()
    return AdapterBundle(base_va, code, {n: base_va + a.labels[n] for n in ("line", "fill", "sprite", "outline")},
                         tuple(a.relocations), width, height)


@dataclass(frozen=True)
class EdgeCell:
    column: int
    row: int
    world_x: int
    world_y: int
    rect: tuple[int, int, int, int]
    operation: str  # draw_clipped_tile or clear_outside_world


MINIMAP_CLIP_HOOK = bytes.fromhex("e91bc40d00909090")
MINIMAP_CLIP_CAVE = bytes.fromhex(
    "56558b35e4025200668b2d4433520066032d48335200664d6639e8770d"
    "6639eb76036689ebe9be3bf2ffe9183df2ff" + "00" * 17
)


def verify_edge_prerequisites(original: bytes, candidate: bytes, *, width: int | None = None) -> None:
    """Verify the audited drawing code and mandatory minimap intersection.

    This supplements, and never replaces, the patcher's full candidate byte
    gate. The altered native full/incremental tile-loop immediates are outside
    these immutable drawing routines. No original or candidate is written.
    """
    verify_original(original)
    for start, end in (
        # Direct primitives, text/sprite wrappers, units and effect writers.
        (0x416850, 0x418700), (0x402E80, 0x403D70),
        (0x403EF0, 0x4041D0), (0x4191F0, 0x419410),
        (0x405510, 0x4055C0), (0x40BC00, 0x40BC90),
        (0x415EA0, 0x4163F0), (0x416750, 0x416850),
        (0x419000, 0x4190B0), (0x459ED0, 0x45B3C0),
        (0x45C000, 0x45D430), (0x45D430, 0x45E630),
        (0x45F190, 0x460270),
        # Callback queries and the direct minimap-copy tail must not acquire
        # a new write/present path after the original's transitive audit.
        (0x40DB80, 0x40DC10), (0x40F060, 0x40F0C0),
        (0x40D568, 0x40D6D0),
        (0x425120, 0x4254CC), (0x429EC0, 0x42A340),
        (0x4024E0, 0x402850), (0x460BB0, 0x460C70),
        (0x460EA0, 0x460F90),
    ):
        n = end - start
        source = file_offset(original, start, n)
        target = file_offset(candidate, start, n)
        if original[source:source+n] != candidate[target:target+n]:
            raise ValueError(f"audited drawing routine changed at 0x{start:08X}")
    for va, expected in ((0x40D560, MINIMAP_CLIP_HOOK), (0x4E9980, MINIMAP_CLIP_CAVE),
                         (MEMORY_VTABLE, struct.pack("<20I", *VTABLE_ENTRIES))):
        off = file_offset(candidate, va, len(expected))
        if candidate[off:off+len(expected)] != expected:
            raise ValueError(f"required memory/minimap binding differs at 0x{va:08X}")
    for descriptor in (0x5142B8, 0x5142ED, 0x514322, 0x514357):
        off = file_offset(candidate, descriptor + 28, 4)
        if struct.unpack_from("<I", candidate, off)[0] != 0x4191F0:
            raise ValueError("road overlay has an unaudited descriptor draw callback")
    # Road overlays invoke this native descriptor dispatcher. Retaining its
    # original x<640 guard would silently omit valid extra-column sprites.
    off = file_offset(candidate, 0x419D60, 17)
    expected = bytearray(original[file_offset(original,0x419D60,17):][:17])
    actual_width = struct.unpack_from("<I",candidate,off+5)[0]
    if width is not None and actual_width != width:
        raise ValueError("road descriptor redraw clip does not match the requested width")
    struct.pack_into("<I",expected,5,actual_width)
    if candidate[off:off+17] != expected:
        raise ValueError("road descriptor dispatcher contains unaudited instructions")


def _terrain_end(width: int, height: int, layout: FramedViewport | None) -> tuple[int, int]:
    if layout is None:
        return width - 1, height - 1
    if not isinstance(layout, FramedViewport) or (layout.width, layout.height) != (width, height):
        raise ValueError("framed layout does not match the physical surface")
    return layout.terrain.right, layout.terrain.bottom


def emit_edge_dispatch(original: bytes, candidate: bytes, *, base_va: int,
                       width: int, height: int, layout: FramedViewport | None = None) -> AdapterBundle:
    """Emit a guarded edge renderer and full/incremental entrypoints.

    edge: EAX=screen column, EBX=screen row, ESI=present (0/1).
    edge_full: EAX=present (0/1); handles all partial cells.
    edge_incremental: EAX=world x, EDX=world y; presents one partial cell.
    edge returns 1 for a drawn cell, 2 for cleared outside-world space, or 0
    when unsupported/invalid. Full returns 1 only if every edge was handled.
    All preserve caller registers except EAX and restore the exact render
    pointer and map vtable after the scoped native tile call.

    This is not installed into the candidate. Hook placement, zero-cave byte
    verification, and actual runtime evidence remain integration requirements.
    """
    verify_edge_prerequisites(original, candidate, width=width)
    right, bottom = _terrain_end(width, height, layout)
    tx, ty = (right+1-32)//64, (bottom+1-16)//64
    cx, cy = (right+1-32+63)//64, (bottom+1-16+63)//64
    if not tx or not ty or cx > 100 or cy > 100:
        raise ValueError("edge renderer requires a viewport within the 100x100 backing grid")
    trial = emit_adapters(original, base_va=base_va, width=width, height=height,
                          _clipped_vtable_va=0, clip_origin=(32, 16), clip_end=(right, bottom))
    table_offset = (len(trial.code)+15) & ~15
    table_va = base_va + table_offset
    adapters = emit_adapters(original, base_va=base_va, width=width, height=height,
                             _clipped_vtable_va=table_va, clip_origin=(32, 16), clip_end=(right, bottom))
    a = _Assembler(base_va)
    a.code.extend(adapters.code)
    a.code.extend(b"\0" * (table_offset-len(a.code)))
    table = list(VTABLE_ENTRIES)
    for slot, name in ((5,"line"),(6,"outline"),(7,"fill"),(13,"sprite")):
        table[slot] = adapters.entries[name]
    for slot,value in enumerate(table):
        if value:a.absolute(value,"vtable_entry_"+str(slot))
        else:a.u32(0)
    a.relocations.extend(adapters.relocations)
    a.labels.update({n: va-base_va for n,va in adapters.entries.items()})

    def global_address(value: int, purpose: str) -> None:
        a.absolute(value, purpose)

    def fail_if(opcode: str) -> None:
        a.branch(opcode, "edge.reject")

    # Both entries use the same bounds/ABI implementation. The public edge
    # entry admits partial cells only; cell admits every visible full/partial
    # cell so an incremental full-tile hook can retain the same composition.
    a.label("edge");a.emit("6089e583ec40c745d000000000")
    a.branch("e9","cell.common")
    a.label("cell");a.emit("6089e583ec40c745d001000000")
    a.label("cell.common")
    # Private frame: -4 map, -8 vtable, -12 render pointer, -16/-20 L/T,
    # -24/-28 R/B, -32 game data, -36/-40 world X/Y, -44 cursor, -48 result,
    # -52/-56 column/row, -60/-64 map width/height.
    a.emit("8b451c85c0"); fail_if("0f88")
    a.emit("3d"); a.u32(cx); fail_if("0f8d")
    a.emit("8945cc8b451085c0"); fail_if("0f88")
    a.emit("3d"); a.u32(cy); fail_if("0f8d")
    a.emit("8945c88b450483f801"); fail_if("0f87")
    a.emit("837dd001");a.branch("0f84","edge.partial")
    a.emit("817dcc"); a.u32(tx)
    a.branch("0f8d", "edge.partial")
    a.emit("817dc8"); a.u32(ty); fail_if("0f8c")
    a.label("edge.partial")
    # Match the native lower-row ownership restriction. Suppressed rows are
    # not silently cleared or classified as completed terrain.
    a.emit("817dc8"); a.u32(ty-1)
    a.branch("0f8c", "edge.owner_ok")
    a.emit("833d"); global_address(LOWER_ROW_OWNER_GLOBAL,"lower_row_owner"); a.emit("00")
    fail_if("0f85")
    a.label("edge.owner_ok")
    a.emit("a1"); global_address(TILE_CALLBACK_GLOBAL,"tile_callback")
    a.emit("85c0"); a.branch("0f84","edge.callback_ok")
    a.emit("3d"); a.absolute(0x425120,"road_callback"); a.branch("0f84","edge.callback_ok")
    a.emit("3d"); a.absolute(0x429EC0,"build_callback"); fail_if("0f85")
    a.label("edge.callback_ok")
    a.emit("a1"); global_address(MAP_SURFACE_GLOBAL,"map_surface_global")
    a.emit("85c0"); fail_if("0f84")
    a.emit("668138"+struct.pack("<H",width).hex()); fail_if("0f85")
    a.emit("66817802"+struct.pack("<H",height).hex()); fail_if("0f85")
    a.emit("83780400"); fail_if("0f84")
    a.emit("8945fc8b90b800000081fa"); a.absolute(MEMORY_VTABLE,"memory_vtable")
    a.branch("0f84","edge.table_ok")
    a.emit("81fa"); a.absolute(table_va,"clipped_vtable"); fail_if("0f85")
    a.label("edge.table_ok")
    a.emit("8955f88b35"); global_address(GAME_DATA_GLOBAL,"game_data_global")
    a.emit("85f6"); fail_if("0f84")
    a.emit("8975e08b86e022020083f801"); fail_if("0f8c")
    a.emit("83f864"); fail_if("0f8f")
    a.emit("8945c48b86e422020083f801"); fail_if("0f8c")
    a.emit("83f864"); fail_if("0f8f")
    a.emit("8945c0")
    for tag, dim, scroll, index, out in (("x",0xC4,0x222E8,0xCC,0xDC),("y",0xC0,0x222EC,0xC8,0xD8)):
        a.emit("8b4d"+bytes([dim]).hex()+"81e9"); a.u32(tx if tag=="x" else ty)
        a.branch("0f89","edge.max_"+tag)
        a.emit("31c9")
        a.label("edge.max_"+tag)
        a.emit("8b96"); a.u32(scroll)
        a.emit("85d2"); fail_if("0f88")
        a.emit("39ca"); fail_if("0f8f")
        a.emit("0355"+bytes([index]).hex()+"8955"+bytes([out]).hex())
    # Clip the pixel extents before either clear or presentation.
    for source, origin, limit, start, end, tag in ((0xCC,32,right+1,0xF0,0xE8,"x"),(0xC8,16,bottom+1,0xEC,0xE4,"y")):
        a.emit("8b45"+bytes([source]).hex()+"c1e00605"); a.u32(origin)
        a.emit("8945"+bytes([start]).hex()+"83c03f3d"); a.u32(limit-1)
        a.branch("0f8e","edge.end_"+tag)
        a.emit("b8"); a.u32(limit-1)
        a.label("edge.end_"+tag)
        a.emit("8945"+bytes([end]).hex())
    # Context installation is local to this call. Reentrant edge calls save
    # and restore the cloned table instead of restoring a guessed original.
    a.emit("a1"); global_address(RENDER_DEVICE_GLOBAL,"render_device_global")
    a.emit("8945f48b45fcc780b8000000"); a.absolute(table_va,"clipped_vtable")
    a.emit("a3"); global_address(RENDER_DEVICE_GLOBAL,"render_device_global")
    a.emit("8b45dc3b45c4"); a.branch("0f8d","edge.clear")
    a.emit("8b45d83b45c0"); a.branch("0f8d","edge.clear")
    # Form gameData+1400*x+14*y ONLY after both actual world-bound checks.
    a.emit("695ddc78050000035de08b55d86bd20e01d38b45f08b55ec55")
    a.native_transfer("tile")
    a.emit("5dc745d001000000")
    a.branch("e9","edge.restore")
    a.label("edge.clear")
    a.emit("8b45fc8b55f08b4de88b5dec556a01ff75e4")
    a.branch("e8","fill")
    a.emit("5d8b45f08b55ec8b4de48b5de855")
    # Match the unconditional native tile tail even for outside-world space:
    # otherwise a far-right clear would erase the moved minimap intersection.
    a.native_transfer("minimap")
    a.emit("5dc745d002000000")
    a.label("edge.restore")
    a.emit("8b45fc8b55f88990b80000008b45f4a3")
    global_address(RENDER_DEVICE_GLOBAL,"render_device_global")
    a.emit("837d0400")
    a.branch("0f84","edge.done")
    a.emit("a1"); global_address(CURSOR_VISIBLE_GLOBAL,"cursor_visible")
    # The dirty helper uses exclusive ends, matching native sub_418A90.
    a.emit("8945d4558b45e440508b55f08b4de8418b5decb8"); a.absolute(0x544CD8,"cursor_object")
    a.native_transfer("dirty")
    a.emit("5d558b45fc31d28b5df08b4decff75ecff75f0ff75e4ff75e8")
    a.native_transfer("blit")
    a.emit("5d837dd400")
    a.branch("0f84","edge.done")
    a.emit("55b8"); a.absolute(0x544CD8,"cursor_object")
    a.native_transfer("cursor")
    a.emit("5d")
    a.label("edge.done")
    a.emit("8b45d089451c83c44061c3")
    a.label("edge.reject")
    a.emit("83c4406131c0c3")

    for name,target in (("edge_incremental","edge"),("cell_incremental","cell")):
        a.label(name)
        a.emit("6089e58b35"); global_address(GAME_DATA_GLOBAL,"game_data_global")
        a.emit("85f6"); a.branch("0f84",name+".reject")
        a.emit("8b451c2b86e82202008b5d142b9eec220200be0100000055")
        a.branch("e8",target)
        a.emit("5d89451c61c3")
        a.label(name+".reject");a.emit("6131c0c3")

    a.label("edge_full")
    a.emit("6089e583ec04c745fc010000008b451c83f801")
    a.branch("0f87","full.reject")
    for row in range(cy):
        for col in range(cx):
            if col < tx and row < ty:
                continue
            a.emit("b8"); a.u32(col)
            a.emit("bb"); a.u32(row)
            a.emit("8b751c55")
            a.branch("e8","edge")
            a.emit("5d85c0")
            label=f"full.next_{col}_{row}"
            a.branch("0f85",label)
            a.emit("c745fc00000000")
            a.label(label)
    a.emit("8b45fc89451c83c40461c3")
    a.label("full.reject")
    a.emit("83c4046131c0c3")
    entries=dict(adapters.entries)
    entries.update({n:base_va+a.labels[n] for n in ("edge","cell","edge_full","edge_incremental","cell_incremental")})
    entries["clipped_vtable"] = table_va
    return AdapterBundle(base_va,a.finish(),entries,tuple(a.relocations),width,height)


def edge_cells(*, width: int, height: int, map_width: int, map_height: int,
               scroll_x: int, scroll_y: int, layout: FramedViewport | None = None) -> tuple[EdgeCell, ...]:
    """Exact work for partial cells only; never construct an invalid tile pointer.

    Keep floor-based scrolling so the final world tile can be shown completely.
    The extra partial cell becomes known outside-world space at the far edge.
    The same cells must be refreshed during full and incremental repaint.
    """
    if any(type(v) is not int for v in (width, height, map_width, map_height, scroll_x, scroll_y)):
        raise ValueError("geometry must use integers")
    if not (32 < width <= 8192 and 16 < height <= 8192 and 1 <= map_width <= 100 and 1 <= map_height <= 100):
        raise ValueError("unsupported surface or map bounds")
    right, bottom = _terrain_end(width, height, layout)
    tx, ty = (right + 1 - 32) // 64, (bottom + 1 - 16) // 64
    if not tx or not ty:
        raise ValueError("at least one full map tile is required")
    if not (0 <= scroll_x <= max(0, map_width - tx) and 0 <= scroll_y <= max(0, map_height - ty)):
        raise ValueError("scroll is outside the full-tile clamp")
    cols, rows = (right + 1 - 32 + 63) // 64, (bottom + 1 - 16 + 63) // 64
    result = []
    for row in range(rows):
        for col in range(cols):
            if col < tx and row < ty:
                continue
            x, y = scroll_x + col, scroll_y + row
            rect = (32 + col * 64, 16 + row * 64, min(right, 95 + col * 64), min(bottom, 79 + row * 64))
            valid = x < map_width and y < map_height
            result.append(EdgeCell(col, row, x, y, rect,
                                   "draw_clipped_tile" if valid else "clear_outside_world"))
    return tuple(result)


def emit_map_composition(original: bytes, candidate: bytes, *, base_va: int,
                         width: int, height: int, layout: FramedViewport | None = None) -> AdapterBundle:
    """Add a draw-only command-panel tail and tooltip-preserving presentation.

    This policy supports the native map render hook 0040AD40 only, including
    its interactive command-list and non-animated AI-turn banner branches.
    Other/modal owners, including army rows, fail closed.
    The command list is drawn in its existing state, without input or callback
    activation. The initialized primary-only tooltip rectangle is excluded
    from map copies. Its pixels are not erased, synthesized or reinterpreted
    as map terrain; software-surface coverage remains independent.

    compose_panel: no inputs, redraw list offscreen, return 1/0.
    present_map_rect: EAX=L, EBX=T, ECX=R, EDX=B (inclusive), return 1/0.
    edge_composed: EAX=column, EBX=row, ESI=present 0/1, return edge status.
    edge_full_composed: EAX=present 0/1, return full-edge status.
    Native full-tile drawing and frame restoration still belong to the caller.
    """
    bundle = emit_edge_dispatch(original,candidate,base_va=base_va,width=width,height=height,layout=layout)
    right, bottom = _terrain_end(width, height, layout)
    dock_x, dock_y = ((width - 192, height - 72) if layout is None
                      else (layout.action_bar.left, layout.action_bar.top))
    if width < 800 or height < 600:
        raise ValueError("map composition requires the authenticated HD layout geometry")
    # Authenticate the complete list and the list dispatcher's single changed
    # width operand. No callback addresses or unknown list terminator accepted.
    source = file_offset(original,COMMAND_DESCRIPTORS,322)
    expected = bytearray(original[source:source+322])
    for i in range(6):
        struct.pack_into("<ii",expected,53*i,dock_x+64*(i%3),dock_y+32*(i//3))
    off = file_offset(candidate,COMMAND_DESCRIPTORS,len(expected))
    if candidate[off:off+len(expected)] != expected:
        raise ValueError("command list is not the authenticated relocated map layout")
    source=file_offset(original,0x419D80,64)
    expected=bytearray(original[source:source+64]);struct.pack_into("<I",expected,14,width)
    off=file_offset(candidate,0x419D80,64)
    if candidate[off:off+64] != expected:
        raise ValueError("command list dispatcher has unaudited bytes or width")
    # The primary-only tooltip initialization/draw/clear contract is immutable.
    for start,end in ((0x422880,0x422B80),(0x40A400,0x40A450),(0x40A600,0x40A7F0)):
        n=end-start;s=file_offset(original,start,n);t=file_offset(candidate,start,n)
        if original[s:s+n] != candidate[t:t+n]:
            raise ValueError("native map composition contract changed")
    a=_Assembler(base_va);a.code.extend(bundle.code);a.relocations.extend(bundle.relocations)
    a.labels.update({n:va-base_va for n,va in bundle.entries.items()})
    table=bundle.entries["clipped_vtable"]
    frame_entry = None
    if layout is not None:
        from .four_sided_frame import emit_frame_helper
        offset = len(a.code)
        frame = emit_frame_helper(original, base_va=base_va+offset, width=width, height=height)
        a.code.extend(frame.code)
        a.relocations.extend(Relocation(r.offset+offset, r.kind, r.target, r.purpose) for r in frame.relocations)
        frame_entry = frame.entries["draw_frame"]
        a.labels["draw_frame"] = frame_entry-base_va

    def glob(value: int,purpose: str) -> None:a.absolute(value,purpose)
    def reject(opcode="0f85"):a.branch(opcode,"composition_guard.reject")
    a.label("composition_guard");a.emit("6089e5")
    for address,purpose,value in ((RENDER_HOOK_GLOBAL,"render_hook",0x40AD40),
                                   (LOWER_ROW_OWNER_GLOBAL,"lower_row_owner",0),
                                   (POST_TILE_CALLBACK_GLOBAL,"post_tile_callback",0)):
        a.emit("813d");glob(address,purpose)
        if purpose=="render_hook":glob(value,"map_render_hook_target")
        else:a.u32(value)
        reject()
    a.emit("a1");glob(MAP_SURFACE_GLOBAL,"map_surface_global")
    a.emit("85c0");reject("0f84")
    a.emit("668138"+struct.pack("<H",width).hex());reject()
    a.emit("66817802"+struct.pack("<H",height).hex());reject()
    a.emit("83780400");reject("0f84")
    a.emit("81b8b8000000");glob(MEMORY_VTABLE,"memory_vtable")
    a.branch("0f84","composition_guard.surface")
    a.emit("81b8b8000000");glob(table,"clipped_vtable");reject()
    a.label("composition_guard.surface")
    a.emit("a1");glob(CURRENT_PLAYER_GLOBAL,"current_player")
    a.emit("83f805");reject("0f83")
    a.emit("69c08f0500008b15");glob(GAME_DATA_GLOBAL,"game_data_global")
    a.emit("85d2");reject("0f84")
    a.emit("83bc021323020000")  # native interactive command-list flag
    a.branch("0f84","composition_guard.banner")
    a.emit("833d");glob(COMMAND_SPRITES_GLOBAL,"command_sprites");a.emit("00");reject("0f84")
    a.emit("be");glob(COMMAND_DESCRIPTORS,"command_descriptors")
    for i in range(6):
        for member,value in ((0,dock_x+64*(i%3)),(4,dock_y+32*(i//3)),
                             (12,COMMAND_SPRITES_GLOBAL),(28,0x4191F0)):
            a.emit("81be");a.u32(53*i+member)
            if member==12:glob(value,"command_sprites")
            elif member==28:glob(value,"command_draw_callback")
            else:a.u32(value)
            reject()
    a.emit("83be3e010000ff");reject()  # exact six-entry terminator
    a.branch("e9","composition_guard.tooltip")
    a.label("composition_guard.banner")
    a.emit("833d");glob(TURN_SPRITES_GLOBAL,"turn_sprites");a.emit("00");reject("0f84")
    # Initialized map tooltip occupies a known bottom-docked primary region.
    # Null means pre-initialization; a stale modal rectangle is rejected.
    a.label("composition_guard.tooltip")
    a.emit("a1");glob(TOOLTIP_SURFACE_GLOBAL,"tooltip_surface")
    a.emit("85c0");a.branch("0f84","composition_guard.good")
    tooltip=(160+(width-640)//2,height-14,473+(width-640)//2,height-1)
    for i,(address,value) in enumerate(zip(TOOLTIP_BOUNDS,tooltip)):
        a.emit("813d");glob(address,"tooltip_"+str(i));a.u32(value);reject()
    a.label("composition_guard.good");a.emit("61b801000000c3")
    a.label("composition_guard.reject");a.emit("6131c0c3")

    # Clone only the authenticated drawing prefix, ending at native0040A72B.
    # The omitted suffix contains Time_Now, an animation loop, and an
    # unconditional primary blit even when EAX=0. Copying that suffix would
    # violate the offscreen contract. These six E8 sites are from the native
    # instruction audit; compiler PE HIGHLOW fields independently verify all
    # absolute operands in the prefix (not address-looking byte scanning).
    a.label("turn_banner_offscreen")
    a.emit("85c0");a.branch("0f85","turn_banner_offscreen.reject")
    clone_start=len(a.code);native_va=0x40A600;clone_size=0x12B
    offset=file_offset(original,native_va,clone_size)
    a.code.extend(original[offset:offset+clone_size])
    # Native banner origin (416,400) is exactly descriptor 0, not the physical
    # 640x480 corner. Translate every sprite/text coordinate by the same delta
    # as the authenticated command dock; preserve all internal spacing and the
    # text layout's right extent (608 becomes width, not width-1).
    native_dock=struct.unpack_from("<ii",original,file_offset(original,COMMAND_DESCRIPTORS,8))
    if native_dock != (416,400):raise ValueError("native command dock origin differs")
    dock_delta=(dock_x-native_dock[0],dock_y-native_dock[1])
    for field,opcode,value,axis in ((0x38,0xB9,400,1),(0x45,0xBB,416,0),
                                    (0x87,0xBB,568,0),(0x94,0xB9,404,1),
                                    (0xCE,0x68,436,1),(0xD3,0x68,608,0),
                                    (0xD8,0x68,416,0),(0x11A,0x68,405,1),
                                    (0x11F,0x68,421,0)):
        pos=clone_start+field
        if a.code[pos-1]!=opcode or struct.unpack_from("<I",a.code,pos)[0]!=value:
            raise ValueError("native turn prefix coordinate operand differs")
        struct.pack_into("<I",a.code,pos,value+dock_delta[axis])
    fields={0x0C:RENDER_DEVICE_GLOBAL,0x14:MAP_SURFACE_GLOBAL,0x1A:CURRENT_PLAYER_GLOBAL,
            0x1F:RENDER_DEVICE_GLOBAL,0x24:TURN_SPRITES_GLOBAL,0x3E:RENDER_DEVICE_GLOBAL,
            0x5A:CURRENT_PLAYER_GLOBAL,0x64:GAME_DATA_GLOBAL,0x70:TURN_SPRITES_GLOBAL,
            0x8D:RENDER_DEVICE_GLOBAL,0xB3:CURRENT_PLAYER_GLOBAL,0xBC:GAME_DATA_GLOBAL,
            0xE2:GAME_DATA_GLOBAL,0x103:GAME_DATA_GLOBAL,0x115:0x4EC7C5}
    if _original_highlow_fields(original,native_va,clone_size) != set(fields):
        raise ValueError("native turn prefix relocation inventory differs")
    purposes={RENDER_DEVICE_GLOBAL:"render_device_global",MAP_SURFACE_GLOBAL:"map_surface_global",
              CURRENT_PLAYER_GLOBAL:"current_player",TURN_SPRITES_GLOBAL:"turn_sprites",
              GAME_DATA_GLOBAL:"game_data_global",0x4EC7C5:"turn_text_literal"}
    for field,target in fields.items():
        if struct.unpack_from("<I",a.code,clone_start+field)[0]!=target:
            raise ValueError("native turn prefix absolute operand differs")
        a.relocations.append(Relocation(clone_start+field,"abs32",target,purposes[target]))
    for field,name in ((0x28,"turn_sprite_lookup"),(0x77,"turn_sprite_lookup"),
                       (0xAC,"turn_select_font"),(0xDC,"turn_text_format"),
                       (0xFD,"turn_text_color"),(0x123,"turn_text_draw")):
        if a.code[clone_start+field]!=0xE8:raise ValueError("native turn prefix call opcode differs")
        old_target=native_va+field+5+struct.unpack_from("<i",a.code,clone_start+field+1)[0]
        target=NATIVE_TARGETS[name]
        if old_target!=target:raise ValueError("native turn prefix call target differs")
        pos=clone_start+field+1
        struct.pack_into("<i",a.code,pos,target-(base_va+pos+4))
        a.relocations.append(Relocation(pos,"rel32",target,name))
    # Same saved render pointer and register frame as native0040A600, followed
    # by success. The optional turn-number branch naturally lands here.
    a.emit("8b0424a3");glob(RENDER_DEVICE_GLOBAL,"render_device_global")
    a.emit("83c4045d5f5e5a595bb801000000c3")
    a.label("turn_banner_offscreen.reject");a.emit("31c0c3")

    a.label("compose_panel");a.emit("6089e583ec0c55")
    a.branch("e8","composition_guard");a.emit("5d85c0")
    a.branch("0f84","compose_panel.reject")
    a.emit("a1");glob(MAP_SURFACE_GLOBAL,"map_surface_global")
    a.emit("8945fc8b90b80000008955f8c780b8000000");glob(table,"clipped_vtable")
    a.emit("8b15");glob(RENDER_DEVICE_GLOBAL,"render_device_global")
    a.emit("8955f4a3");glob(RENDER_DEVICE_GLOBAL,"render_device_global")
    a.emit("a1");glob(CURRENT_PLAYER_GLOBAL,"current_player")
    a.emit("69c08f0500008b15");glob(GAME_DATA_GLOBAL,"game_data_global")
    a.emit("83bc021323020000");a.branch("0f84","compose_panel.banner")
    a.emit("55b8");glob(COMMAND_DESCRIPTORS,"command_descriptors")
    a.emit("31d2");a.native_transfer("descriptors");a.emit("5d")
    a.branch("e9","compose_panel.restore")
    a.label("compose_panel.banner")
    # Source-derived alternative with both animation AND native primary-copy
    # suffix removed; no input/selection/update owner is invoked.
    a.emit("5531c0");a.branch("e8","turn_banner_offscreen");a.emit("5d")
    a.label("compose_panel.restore")
    a.emit("8b45fc8b55f88990b80000008b45f4a3");glob(RENDER_DEVICE_GLOBAL,"render_device_global")
    a.emit("83c40c61b801000000c3")
    a.label("compose_panel.reject");a.emit("83c40c6131c0c3")

    # A bounded copy primitive used only by the partitioned presenter.
    # EAX=L,EBX=T,ECX=R,EDX=B; original values preserved except EAX.
    a.label("present_piece");a.emit("6089e583ec0455")
    a.emit("39c1");a.branch("0f8c","present_piece.empty")
    a.emit("39da");a.branch("0f8c","present_piece.empty")
    a.emit("8b451440508b551c8b4d18418b5d10b8");glob(0x544CD8,"cursor_object")
    a.native_transfer("dirty");a.emit("5d55")
    a.emit("ff7510ff751cff7514ff7518a1");glob(MAP_SURFACE_GLOBAL,"map_surface_global")
    a.emit("8b5d1c8b4d1031d2");a.native_transfer("blit")
    a.emit("5d83c40461b801000000c3")
    a.label("present_piece.empty");a.emit("5d83c40461b801000000c3")

    a.label("present_map_rect");a.emit("6089e583ec1455")
    a.branch("e8","composition_guard");a.emit("5d85c0")
    a.branch("0f84","present_map_rect.reject")
    # Inputs must already be clipped to gameplay bounds. No negative/end
    # wraparound is silently reinterpreted as a valid presentation region.
    # Framed full paints present the physical surface, including all borders,
    # through this same tooltip-preserving partition. Incremental callers still
    # submit only their terrain-clipped cell. Legacy bounds remain unchanged.
    present_left, present_top = (32, 16) if layout is None else (0, 0)
    for offset,limit,condition in ((28,present_left,"0f8c"),(16,present_top,"0f8c"),(24,width,"0f8d"),(20,height,"0f8d")):
        a.emit("817d"+bytes([offset]).hex());a.u32(limit);a.branch(condition,"present_map_rect.reject")
    a.emit("8b451c394518");a.branch("0f8c","present_map_rect.reject")
    a.emit("8b4510394514");a.branch("0f8c","present_map_rect.reject")
    a.emit("a1");glob(CURSOR_VISIBLE_GLOBAL,"cursor_visible");a.emit("8945ec")
    a.emit("a1");glob(TOOLTIP_SURFACE_GLOBAL,"tooltip_surface")
    a.emit("85c0");a.branch("0f84","present_map_rect.single")
    # I = requested rectangle intersected with the primary tooltip rectangle.
    for i,(offset,opcode) in enumerate(((28,"0f8d"),(16,"0f8d"),(24,"0f8e"),(20,"0f8e"))):
        a.emit("8b45"+bytes([offset]).hex()+"3b05");glob(TOOLTIP_BOUNDS[i],"tooltip_"+str(i))
        a.branch(opcode,"present_map_rect.bound"+str(i))
        a.emit("a1");glob(TOOLTIP_BOUNDS[i],"tooltip_"+str(i))
        a.label("present_map_rect.bound"+str(i));a.emit("8945"+bytes([0xFC-4*i]).hex())
    a.emit("8b45fc3945f4");a.branch("0f8c","present_map_rect.single")
    a.emit("8b45f83945f0");a.branch("0f8c","present_map_rect.single")
    # Partition R\I into disjoint top/bottom/left/right strips. Never copy a
    # tooltip pixel or duplicate a map pixel, including one-pixel intersections.
    for setup in ("8b451c8b5d108b4d188b55f84a",  # top
                  "8b451c8b5df0438b4d188b5514",  # bottom
                  "8b451c8b5df88b4dfc498b55f0",  # middle left
                  "8b45f4408b5df88b4d188b55f0"):
        a.emit(setup+"55");a.branch("e8","present_piece");a.emit("5d")
    a.branch("e9","present_map_rect.cursor")
    a.label("present_map_rect.single")
    a.emit("8b451c8b5d108b4d188b551455");a.branch("e8","present_piece");a.emit("5d")
    a.label("present_map_rect.cursor")
    a.emit("837dec00");a.branch("0f84","present_map_rect.done")
    a.emit("55b8");glob(0x544CD8,"cursor_object");a.native_transfer("cursor");a.emit("5d")
    a.label("present_map_rect.done");a.emit("83c41461b801000000c3")
    a.label("present_map_rect.reject");a.emit("83c4146131c0c3")

    for name,target,full in (("edge_composed","edge",False),("cell_composed","cell",False),
                             ("edge_full_composed","edge_full",True)):
        a.label(name);a.emit("6089e583ec0455")
        a.branch("e8","composition_guard");a.emit("5d85c0")
        a.branch("0f84",name+".reject")
        a.emit("837d"+("1c" if full else "04")+"01")
        a.branch("0f87",name+".reject")
        if full:
            a.emit("31c055");a.branch("e8",target)
        else:
            a.emit("8b451c8b5d1031f655");a.branch("e8",target)
        a.emit("5d8945fc85c0");a.branch("0f84",name+".reject")
        if full and frame_entry is not None:
            # Native full cells have already painted; fill partials, then build
            # the frame before overlays. The primary-only tooltip is preserved
            # by the later presenter, not overwritten with footer background.
            a.emit("55");a.branch("e8","draw_frame");a.emit("5d83f801")
            a.branch("0f85",name+".reject")
        a.emit("55");a.branch("e8","compose_panel");a.emit("5d85c0")
        a.branch("0f84",name+".reject")
        a.emit("837d"+("1c" if full else "04")+"00")
        a.branch("0f84",name+".done")
        if full:
            a.emit("b8");a.u32(present_left);a.emit("bb");a.u32(present_top)
            a.emit("b9");a.u32(width-1);a.emit("ba");a.u32(height-1)
        else:
            a.emit("8b451cc1e00683c0208b5d10c1e30683c3108d483f8d533f")
            for reg,opcode,limit,tag in (("81f9","b9",right,"right"),("81fa","ba",bottom,"bottom")):
                a.emit(reg);a.u32(limit);a.branch("0f8e",name+"."+tag)
                a.emit(opcode);a.u32(limit);a.label(name+"."+tag)
        a.emit("55");a.branch("e8","present_map_rect");a.emit("5d85c0")
        a.branch("0f84",name+".reject")
        a.label(name+".done");a.emit("8b45fc89451c83c40461c3")
        a.label(name+".reject");a.emit("83c4046131c0c3")
    a.label("cell_incremental_composed")
    a.emit("6089e58b35");glob(GAME_DATA_GLOBAL,"game_data_global")
    a.emit("85f6");a.branch("0f84","cell_incremental_composed.reject")
    a.emit("8b451c2b86e82202008b5d142b9eec220200be0100000055")
    a.branch("e8","cell_composed");a.emit("5d89451c61c3")
    a.label("cell_incremental_composed.reject");a.emit("6131c0c3")
    entries=dict(bundle.entries)
    entries.update({name:base_va+a.labels[name] for name in
                    ("composition_guard","compose_panel","present_map_rect","edge_composed","edge_full_composed",
                     "cell_composed","cell_incremental_composed","turn_banner_offscreen")})
    if frame_entry is not None:
        entries["draw_frame"] = frame_entry
    return AdapterBundle(base_va,a.finish(),entries,tuple(a.relocations),width,height)


def integration_requirements() -> tuple[str, ...]:
    return (
        "Do not install: emitted helpers are not a byte-gated patch stage; caller hooks, allocation and runtime evidence remain required.",
        "Keep the native drawing graph unchanged under the full candidate byte gate and require the authenticated minimap intersection hook.",
        "Use edge_full_composed before 004187A0, retain frame restoration, then use tooltip-preserving present_map_rect; route full and partial incremental cells through cell_incremental_composed.",
        "The executable composition tail supports exact map ownership, including the command list and a docked offscreen-only AI banner; modal and army-row policies remain unsupported and reject before drawing.",
        "Hook both sub_418700 full and sub_418A90 incremental paths, including out-of-world edge refresh after scrolling; an incremental tile notification alone cannot clear absent world cells.",
        "Keep map-memory primitive clips at [32,16,W-1,H-1], distinct from the physical surface [0,0,W-1,H-1]; retain native present ordering.",
        "Keep existing full-tile scroll clamps; update coverage to require every valid partial cell without treating world-border clear as terrain proof.",
        "Use a new validation stage, authenticated PE code allocation and exact old bytes; no stable promotion without runtime evidence.",
    )
