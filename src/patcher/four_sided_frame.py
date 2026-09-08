"""Offline native-art frame draw plan and uninstalled x86 memory-surface helper.

No game assets are embedded, no executable is written and no hook is installed.
Clipped FRAME sprites supply four borders; sprite 5 supplies the footer once.
The primary/wrapper surface is deliberately not an accepted draw target.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import partial_tile_clip as clip
from .framed_viewport import FramedViewport, Rect


FRAME_SPRITES_GLOBAL = 0x5202BC
PRIMARY_SURFACE = 0x51D4C0
NATIVE_SPRITE = 0x402E80
NATIVE_LOOKUP = 0x405EC0
BASE_PIECES = (
    (0, 0, 0, 314, 237), (1, 314, 0, 326, 238),
    (2, 0, 237, 315, 243), (3, 315, 238, 325, 242),
)
SPRITE_SIZES = {index: (width, height) for index, _, _, width, height in BASE_PIECES}
SPRITE_SIZES[5] = (324, 15)
PROFILE = "native_four_border_tiles_v1"


@dataclass(frozen=True)
class FrameDraw:
    sprite: int
    x: int
    y: int
    clip: Rect
    band: str


def _segments(size: int, native_size: int, border: int):
    """Disjoint destination spans with their native source starting coordinate."""
    result = [(0, border - 1, 0)]
    repeat = native_size - 2 * border
    for dest in range(border, size - border, repeat):
        result.append((dest, min(dest + repeat - 1, size - border - 1), border))
    result.append((size - border, size - 1, native_size - border))
    return tuple(result)


def frame_draw_plan(layout: FramedViewport) -> tuple[FrameDraw, ...]:
    """Use original sprite origins and clipped repeat tails, never scale pixels.

    Base clips partition all four frame bands. Footer 5 then overlays its one
    native-centered footprint; it is not part of the repeated bottom artwork.
    Terrain and controls are outside every clip. This is a prospective layout,
    not a claim about any existing stage or screenshot.
    """
    if not isinstance(layout, FramedViewport):
        raise ValueError("frame plan requires a validated FramedViewport")
    result = []

    def append_piece(source: Rect, dx: int, dy: int, band: str):
        for index, x, y, width, height in BASE_PIECES:
            part = source.intersection(Rect(x, y, x + width - 1, y + height - 1))
            if part is not None:
                target = Rect(part.left + dx, part.top + dy, part.right + dx, part.bottom + dy)
                result.append(FrameDraw(index, x + dx, y + dy, target, band))

    for name, dest_y, source_y in (("top", 0, 0), ("bottom", layout.height - 16, 464)):
        for dest_left, dest_right, source_x in _segments(layout.width, 640, 32):
            append_piece(Rect(source_x, source_y, source_x + dest_right - dest_left, source_y + 15),
                         dest_left - source_x, dest_y - source_y, name)
    for name, dest_x, source_x in (("left", 0, 0), ("right", layout.width - 32, 608)):
        for dest_top, dest_bottom, source_y in _segments(layout.height, 480, 16)[1:-1]:
            append_piece(Rect(source_x, source_y, source_x + 31, source_y + dest_bottom - dest_top),
                         dest_x - source_x, dest_top - source_y, name)
    footer_x, footer_y = 155 + (layout.width - 640) // 2, layout.height - 15
    result.append(FrameDraw(5, footer_x, footer_y,
                            Rect(footer_x, footer_y, footer_x + 323, footer_y + 14), "footer"))
    return tuple(result)


def emit_frame_helper(original: bytes, *, base_va: int, width: int, height: int) -> clip.AdapterBundle:
    """Emit ``draw_frame`` with no arguments; return 1 after issuing all draws.

    Return 0 without any draw when admission fails. All GPR except EAX, flags,
    stack and the exact entry render-device pointer are preserved. Return 1
    means admitted calls completed, not proof of correct pixels or presentation.

    Admission checks the current nonnull memory map surface, physical W/H,
    pixels and original memory vtable. All five required FRAME entries must
    exist with native dimensions, encoding 0 and nonnull encoded streams before
    the first draw. They are cached only
    on the invocation stack. This assumes the native resource loader owns a
    live sprite table; pointer checks do not authenticate arbitrary memory or
    resource content. A runtime plan must bind the user's actual FRAME asset.

    Each native call receives explicit inclusive band clips and native modes
    (1,0,0). No primary calls, vtable changes, allocation or shared cache occur.
    A future installer must handle owner lifetime, terrain/control geometry,
    input admission, present=0/1 behavior and source-bound runtime evidence.
    """
    clip.verify_original(original)
    layout = FramedViewport(width, height)
    if type(base_va) is not int or not 0x10000 <= base_va <= 0x7FFF0000:
        raise ValueError("invalid x86 code allocation")
    for va, data in ((NATIVE_LOOKUP, bytes.fromhex("8b0490c3")),
                     (0x406740, bytes.fromhex("5351525657"))):
        offset = clip.file_offset(original, va, len(data))
        if original[offset:offset + len(data)] != data:
            raise ValueError("native frame/lookup ABI differs")
    plan = frame_draw_plan(layout)
    a = clip._Assembler(base_va)
    a.label("draw_frame")
    a.emit("9c6089e583ec1ca1")  # PUSHFD/PUSHAD; frame; seven stack locals.
    a.absolute(clip.RENDER_DEVICE_GLOBAL, "render_device_global")
    a.emit("8945f8a1")          # [EBP-8] retains the exact entry render target.
    a.absolute(clip.MAP_SURFACE_GLOBAL, "map_surface_global")
    a.emit("85c0")
    a.branch("0f84", "reject")
    a.emit("3d")
    a.absolute(PRIMARY_SURFACE, "primary_surface")
    a.branch("0f84", "reject")
    a.emit("8138"); a.u32(width | (height << 16))
    a.branch("0f85", "reject")
    a.emit("83780400")
    a.branch("0f84", "reject")
    a.emit("81b8b8000000")
    a.absolute(clip.MEMORY_VTABLE, "memory_vtable")
    a.branch("0f85", "reject")
    a.emit("8945fc8b15")        # [EBP-4]=admitted map; EDX=loaded FRAME table.
    a.absolute(FRAME_SPRITES_GLOBAL, "frame_sprites_global")
    a.emit("85d2")
    a.branch("0f84", "reject")
    slots = {}
    for slot, (index, (sprite_width, sprite_height)) in enumerate(SPRITE_SIZES.items()):
        local = -(12 + 4 * slot)
        slots[index] = local
        a.emit("8b42" + bytes([4 * index]).hex() + "85c0")
        a.branch("0f84", "reject")
        # 406260 copies the S32 header unchanged: width first, then height.
        # Decompiled GetSpriteWidth/GetSpriteHeight labels are misleading.
        a.emit("8138"); a.u32(sprite_width | (sprite_height << 16))
        a.branch("0f85", "reject")
        a.emit("6683780400")
        a.branch("0f85", "reject")
        a.emit("83780a00")
        a.branch("0f84", "reject")
        a.emit("8945" + bytes([local & 255]).hex())

    a.label("frame_admitted")
    for draw in plan:
        # EBP is explicitly saved across the callee; no native return value
        # or preserved working register is assumed. RET 1Ch pops seven args.
        a.emit("558b45fca3")
        a.absolute(clip.RENDER_DEVICE_GLOBAL, "render_device_global")
        a.emit("6a006a006a01")
        for value in (draw.clip.bottom, draw.clip.right, draw.clip.top, draw.clip.left):
            a.emit("68"); a.u32(value)
        a.emit("8b55" + bytes([slots[draw.sprite] & 255]).hex())
        a.emit("bb"); a.u32(draw.x)
        a.emit("b9"); a.u32(draw.y)
        a.emit("fc")           # Native string operations require forward DF.
        a.native_transfer("sprite")
        a.emit("5d")
    a.emit("c7451c01000000")     # Status in saved EAX; never native draw EAX.
    a.branch("e9", "restore")
    a.label("reject")
    a.emit("c7451c00000000")
    a.label("restore")
    a.emit("8b45f8a3")
    a.absolute(clip.RENDER_DEVICE_GLOBAL, "render_device_global")
    a.emit("89ec619dc3")
    code = a.finish()
    if base_va + len(code) > 0x80000000:
        raise ValueError("frame helper exceeds the supported x86 allocation")
    result = clip.AdapterBundle(base_va, code, {name: base_va + pos for name, pos in a.labels.items()},
                                tuple(a.relocations), width, height, installation_ready=False)
    clip.absolute_relocation_offsets(result)
    return result
