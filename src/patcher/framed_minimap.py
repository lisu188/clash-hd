"""Uninstalled, source-bound minimap viewport outline for framed terrain.

The active hook follows native backing repair at40D633. It leaves the repair,
right-edge clamp and base recipe untouched; a final installer must verify and
apply the explicit hook separately. No binary, resource or process is written.
The unreferenced40D450 outline is intentionally not hooked.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import struct

from . import partial_tile_clip as clip
from .framed_viewport import FramedViewport

ACTIVE_SITE = 0x40D633
ACTIVE_OLD = bytes.fromhex("a1e4025200")
ACTIVE_FALLBACK = 0x40D638
ACTIVE_CONTINUATION = 0x40D6C6
PRIMARY = 0x51D4C0
PRIMARY_VTABLE = 0x50EEC4
ORIGIN = 0x523344
SIZE = 0x523348
BACKING = 0x52334C
SCALE = 0x523F54
NATIVE_MEMORY_OUTLINE = 0x404040
NATIVE_PRIMARY_OUTLINE = 0x404560
NATIVE_CONTRACTS = (
    (0x40D560, 0x16A, "a23f3e93b580fbb57849333ab89efa35c0bdde61b1809f94a48ed51a34f11733"),
    (0x40D330, 0x2D, "84acfa5753ca04592f86f3a90060505547e15c8842ba9ccb4d00fc2d2dab7173"),
    (0x404560, 0x35, "cbf28e9c50789c271ee50ac4e79d9cbdddff48b4201ab2e10e381423212ba043"),
)


@dataclass(frozen=True)
class MinimapHook:
    name: str
    offset: int
    va: int
    old_bytes: bytes
    new_bytes: bytes
    entry_va: int
    fallback_va: int
    continuation_va: int
    relocations: tuple[clip.Relocation, ...]
    removed_highlow_vas: tuple[int, ...]

    @property
    def rva(self) -> int:
        return self.va - 0x400000


@dataclass(frozen=True)
class FramedMinimapBundle(clip.AdapterBundle):
    hook_sites: tuple[MinimapHook, ...] = ()
    status_vas: dict[str, int] = field(default_factory=dict)
    native_contract: dict = field(default_factory=dict)


def viewport_rect(*, width: int, height: int, world_width: int, world_height: int,
                  scroll_x: int, scroll_y: int, scale: int,
                  origin_x: int, origin_y: int) -> tuple[int, int, int, int]:
    """Conservative projection of the visible world area, with native border.

    This pure geometry function does not assert runtime object/target validity.
    Unlike whole-tile rounding, fractional terrain contributes only its actual
    projected pixels. At the world edge, blank terrain beyond it is excluded.
    """
    layout = FramedViewport(width, height)
    values = (world_width, world_height, scroll_x, scroll_y, scale, origin_x, origin_y)
    if any(type(value) is not int for value in values):
        raise ValueError("minimap geometry requires integers")
    if not (1 <= world_width <= 100 and 1 <= world_height <= 100 and scale in (2, 4)):
        raise ValueError("unsupported world dimensions or minimap scale")
    for world, scroll, full in zip((world_width, world_height), (scroll_x, scroll_y), layout.full_tiles):
        if not 0 <= scroll <= max(0, world - full) or scroll >= world:
            raise ValueError("invalid minimap scroll")
    if (origin_x != width - 32 - (world_width * scale + 14) or origin_y != 16
            or origin_x < 32 or origin_y + world_height * scale + 14 > height - 16):
        raise ValueError("minimap footprint does not fit framed terrain")
    left, top = origin_x + 6 + scroll_x * scale, origin_y + 6 + scroll_y * scale
    dx = (min(width - 64, (world_width - scroll_x) * 64) * scale + 63) // 64
    dy = (min(height - 32, (world_height - scroll_y) * 64) * scale + 63) // 64
    return left, top, left + 1 + dx, top + 1 + dy


def emit_minimap_bundle(original: bytes, *, base_va: int, width: int, height: int,
                        clipped_vtable_va: int | None = None) -> FramedMinimapBundle:
    """Emit preserving callable and active post-repair hook, without installing.

    draw_viewport_outline returns1 after one native outline call,2 for a valid
    native640 fallback,0 for rejected state. It preserves all non-EAX GPR,
    flags, stack and g_RenderDevice. The hook restores every entry register,
    then either replays A1/gameData and resumes40D638 for status2, or skips to
    the original POP EDI/EBP/ESI/RET at40D6C6. Invalid HD state never executes
    the old small outline. Status1 describes a completed call, not pixel proof.

    Target must be the known map (native or explicitly supplied clipped vtable)
    or guarded same-sized8bpp primary. The native memory404040 call draws the
    entire bounded minimap outline even in a clipped tile scope. Primary404560
    additionally needs current backend pixels+5C/pitch+48: this primitive does
    not lock them itself. All pointers still require source-owned lifetimes.

    Before-call observation entries expose EAXtarget, EDXleft, EBXtop, ECXright,
    stack[0]bottom and stack[4]color4C. No candidate, runtime or proof is made.
    """
    clip.verify_original(original)
    layout = FramedViewport(width, height)
    if type(base_va) is not int or not 0x10000 <= base_va <= 0x7FFF0000:
        raise ValueError("invalid x86 allocation")
    if clipped_vtable_va is not None and (type(clipped_vtable_va) is not int
            or not 0x10000 <= clipped_vtable_va <= 0x7FFFFFFF or clipped_vtable_va == clip.MEMORY_VTABLE):
        raise ValueError("invalid explicit clipped vtable")
    for va, size, expected in NATIVE_CONTRACTS:
        off = clip.file_offset(original, va, size)
        if hashlib.sha256(original[off:off + size]).hexdigest() != expected:
            raise ValueError("native minimap source contract differs")
    hook_offset = clip.file_offset(original, ACTIVE_SITE, len(ACTIVE_OLD))
    if original[hook_offset:hook_offset + 5] != ACTIVE_OLD:
        raise ValueError("active post-repair hook bytes differ")
    if clip._original_highlow_fields(original, ACTIVE_SITE, 5) != {1}:
        raise ValueError("active hook HIGHLOW contract differs")
    a = clip._Assembler(base_va)
    statuses = {}

    def glob(address: int, purpose: str) -> None:
        a.absolute(address, purpose)

    def reject(op="0f85") -> None:
        a.branch(op, "outline.reject")

    def transfer(va: int, purpose: str, opcode="e8") -> None:
        a.emit(opcode)
        pos = len(a.code)
        a.relocations.append(clip.Relocation(pos, "rel32", va, purpose))
        a.u32(va - (base_va + pos + 4))

    # EBP locals: render-4, target kind-8, GD-12, scale-16, worldW/H-20/-24,
    # scrollX/Y-28/-32, L/T/R/B-36/-40/-44/-48. Saved EAX lives at EBP+28.
    a.label("draw_viewport_outline")
    a.emit("9c6089e583ec30a1"); glob(clip.RENDER_DEVICE_GLOBAL, "render_device_global")
    a.emit("8945fc85c0"); reject("0f84")
    a.emit("a1"); glob(clip.MAP_SURFACE_GLOBAL, "map_surface_global")
    a.emit("85c0"); reject("0f84")
    a.emit("3d"); glob(PRIMARY, "primary_surface"); reject("0f84")
    a.emit("83780400"); reject("0f84")
    a.emit("81b8b8000000"); glob(clip.MEMORY_VTABLE, "memory_vtable")
    if clipped_vtable_va is not None:
        a.branch("0f84", "map.table_valid")
        a.emit("81b8b8000000"); glob(clipped_vtable_va, "clipped_vtable")
    reject()
    a.label("map.table_valid")
    a.emit("8138"); a.u32(width | height << 16)
    a.branch("0f84", "map.dimensions_valid")
    a.emit("81388002e001"); reject()
    a.label("map.dimensions_valid")
    a.emit("8b55fc39c2"); a.branch("0f84", "target.memory")
    a.emit("81fa"); glob(PRIMARY, "primary_surface"); reject()
    a.emit("8b003902"); reject()  # Primary and map dimensions must agree.
    a.emit("81bab8000000"); glob(PRIMARY_VTABLE, "primary_vtable"); reject()
    a.emit("83bad400000008"); reject()
    a.emit("8b82bc00000085c0"); reject("0f84")
    a.emit("8bb0a400000085f6"); reject("0f84")
    a.emit("8b3685f6"); reject("0f84")
    for offset in (0x64, 0x6C, 0x80):
        a.emit("83be"); a.u32(offset); a.emit("00"); reject("0f84")
    # Native4739C0 writes [backend+5C + y*pitch48+x], without acquiring pixels.
    a.emit("83785c00"); reject("0f84")
    a.emit("0fb732397048"); reject("0f8c")
    a.emit("81784800000100"); reject("0f8f")
    a.emit("0fb772020faf704803705c"); reject("0f82")
    a.emit("c745f801000000"); a.branch("e9", "target.valid")
    a.label("target.memory"); a.emit("c745f800000000")
    a.label("target.valid")
    a.emit("a1"); glob(clip.GAME_DATA_GLOBAL, "game_data_global")
    a.emit("85c0"); reject("0f84")
    a.emit("8945f48b90c73e020083fa00"); reject("0f8c")
    a.emit("83fa04"); reject("0f8f")
    a.emit("69d28f05000083bc100f23020000"); reject("0f84")
    a.emit("0fb615"); glob(SCALE, "minimap_scale")
    a.emit("83fa02"); a.branch("0f84", "scale.valid")
    a.emit("83fa04"); reject()
    a.label("scale.valid"); a.emit("8955f0")
    for disp, local in ((0x222E0, 0xEC), (0x222E4, 0xE8)):
        a.emit("8b88"); a.u32(disp)
        a.emit("83f901"); reject("0f8c")
        a.emit("83f964"); reject("0f8f")
        a.emit("894d" + bytes([local]).hex())
    # Authenticate the source's scale selection as well as backing dimensions.
    a.emit("8b4dec0faf4de881f9c4090000")
    a.branch("0f8f", "scale.large_world")
    a.emit("83fa04"); reject(); a.branch("e9", "scale.matches_world")
    a.label("scale.large_world"); a.emit("83fa02"); reject()
    a.label("scale.matches_world")
    for axis, disp, world_local, scroll_local, border in ((0, 0x222E8, 0xEC, 0xE4, 64),
                                                          (2, 0x222EC, 0xE8, 0xE0, 32)):
        a.emit("8b88"); a.u32(disp)
        a.emit("85c9"); reject("0f8c")
        a.emit("3b4d" + bytes([world_local]).hex()); reject("0f8d")
        a.emit("894d" + bytes([scroll_local]).hex())
        a.emit("8b75fc0fb776" + bytes([axis]).hex() + "81ee"); a.u32(border)
        a.emit("c1ee068b5d" + bytes([world_local]).hex() + "29f3")
        label = f"scroll.{disp:x}.max"
        a.branch("0f8d", label)
        a.emit("31db"); a.label(label)
        a.emit("39d9"); reject("0f8f")
    # Native backing is world*S+14, anchored at W-32, top16; no aliasing with
    # the map/primary and no unknown surface/vtable or null pixel stream.
    a.emit("8b4dec0faf4df083c10e8b5de80faf5df083c30e0fb715")
    glob(SIZE, "minimap_size")
    a.emit("39ca"); reject()
    a.emit("0fb715"); glob(SIZE + 2, "minimap_height")
    a.emit("39da"); reject()
    a.emit("0fb715"); glob(ORIGIN, "minimap_origin")
    a.emit("83fa20"); reject("0f8c")
    a.emit("01ca8b75fc0fb73683ee2039f2"); reject()
    a.emit("66813d"); glob(ORIGIN + 2, "minimap_top"); a.emit("1000"); reject()
    a.emit("8b75fc0fb7760283ee2039f3"); reject("0f8f")
    a.emit("a1"); glob(BACKING, "minimap_backing")
    a.emit("85c0"); reject("0f84")
    a.emit("3b05"); glob(clip.MAP_SURFACE_GLOBAL, "map_surface_global"); reject("0f84")
    a.emit("3d"); glob(PRIMARY, "primary_surface"); reject("0f84")
    a.emit("0fb73039ce"); reject()
    a.emit("0fb7700239de"); reject()
    a.emit("83780400"); reject("0f84")
    a.emit("81b8b8000000"); glob(clip.MEMORY_VTABLE, "memory_vtable"); reject()
    # Preserve pre-HD behaviour only after the same world/backing checks, using
    # its native full counts/anchor above. No HD projection runs on640 surfaces.
    if (width, height) != (640, 480):
        a.emit("8b45fc81388002e001")
        a.branch("0f84", "outline.native640")
    # Project each actual visible pixel span, capping blank outside-world tails.
    for axis, world, scroll, start, end, origin, physical in (
            ("x", 0xEC, 0xE4, 0xDC, 0xD4, ORIGIN, width - 64),
            ("y", 0xE8, 0xE0, 0xD8, 0xD0, ORIGIN + 2, height - 32)):
        a.emit("8b45" + bytes([world]).hex() + "2b45" + bytes([scroll]).hex() + "c1e0063d")
        a.u32(physical); a.branch("0f8e", f"project.{axis}.bounded")
        a.emit("b8"); a.u32(physical); a.label(f"project.{axis}.bounded")
        a.emit("0faf45f083c03fc1e8068b55" + bytes([scroll]).hex() + "0faf55f00fb70d")
        glob(origin, "minimap_origin" if axis == "x" else "minimap_top")
        a.emit("01ca83c2068955" + bytes([start]).hex() + "8d4402018945" + bytes([end]).hex())
    # Preserve our frame pointer across an otherwise destructive ABI-clean
    # native primitive. Arguments remain observable immediately before CALL.
    a.emit("558b45fc8b55dc8b5dd88b4dd46a4cff75d0837df800")
    a.branch("0f85", "outline.primary_call_setup")
    a.emit("fc"); a.label("memory_outline_call")
    transfer(NATIVE_MEMORY_OUTLINE, "memory_outline")
    a.branch("e9", "outline.after_call")
    a.label("outline.primary_call_setup"); a.emit("fc"); a.label("primary_outline_call")
    transfer(NATIVE_PRIMARY_OUTLINE, "primary_outline")
    a.label("outline.after_call"); a.emit("5db80100000089451c")
    a.label("afterdraw_status")
    statuses["afterdraw_status"] = base_va + len(a.code)
    a.branch("e9", "outline.restore")
    a.label("outline.native640"); a.emit("c7451c02000000"); a.branch("e9", "outline.restore")
    a.label("outline.reject"); a.emit("c7451c00000000")
    a.label("outline.restore")
    a.emit("8b45fca3"); glob(clip.RENDER_DEVICE_GLOBAL, "render_device_global")
    a.emit("89ec619dc3")

    a.label("native_outline_hook")
    a.emit("9c60"); a.branch("e8", "draw_viewport_outline")
    statuses["native_outline_result"] = base_va + len(a.code)
    a.emit("83f802"); a.branch("0f84", "native.fallback")
    a.emit("619d"); transfer(ACTIVE_CONTINUATION, "native_outline_continuation", "e9")
    a.label("native.fallback"); a.emit("619da1")
    glob(clip.GAME_DATA_GLOBAL, "replayed_game_data_global")
    transfer(ACTIVE_FALLBACK, "native_outline_fallback", "e9")
    code = a.finish()
    if base_va + len(code) > 0x80000000:
        raise ValueError("minimap allocation exceeds x86 range")
    entries = {name: base_va + offset for name, offset in a.labels.items()}
    entry = entries["native_outline_hook"]
    hook = MinimapHook("framed_minimap_outline", hook_offset, ACTIVE_SITE, ACTIVE_OLD,
                      b"\xe9" + struct.pack("<i", entry - ACTIVE_SITE - 5), entry,
                      ACTIVE_FALLBACK, ACTIVE_CONTINUATION,
                      (clip.Relocation(1, "rel32", entry, "native_outline_hook"),), (ACTIVE_SITE + 1,))
    contract = dict(original_sha256=clip.ORIGINAL_SHA256,
                    source_spans=[dict(va=f"{va:08x}", size=size, sha256=digest) for va, size, digest in NATIVE_CONTRACTS],
                    observers={"memory": entries["memory_outline_call"], "primary": entries["primary_outline_call"]},
                    observer_abi=dict(phase="before_call", eax="target", edx="left", ebx="top", ecx="right",
                                      stack0="bottom", stack4="color4C", targets={"memory": NATIVE_MEMORY_OUTLINE,
                                                                                 "primary": NATIVE_PRIMARY_OUTLINE}),
                    afterdraw_status=entries["afterdraw_status"],
                    statuses={"0": "invalid state skipped", "1": "native outline call completed",
                              "2": "preserved native640 fallback"},
                    no_latent_hook="40D450 has no established current call/pointer reference",
                    clipped_vtable_va=clipped_vtable_va,
                    limits=["No installation or pixel/input/runtime acceptance.",
                            "Original backing repair must run before active hook; invalid backing there needs an entry-level guard separately.",
                            "Known primary backend pixels must already be available; this native primitive does not lock.",
                            "Whole minimap outline is drawn directly within its checked footprint, independent of a temporary tile clip."])
    bundle = FramedMinimapBundle(base_va, code, entries, tuple(a.relocations), width, height,
                                False, (hook,), statuses, contract)
    clip.absolute_relocation_offsets(bundle)
    return bundle
