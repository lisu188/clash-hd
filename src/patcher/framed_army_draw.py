"""Authenticated, uninstalled own-army portrait drawing for a framed map.

The repeated composition entry copies only the native drawing suffix. It does
not run selection/highlight logic, load resources, or write army state. Its
separate native-entry trampoline preserves the original prefix, suffix exit,
and unsupported-context fallback. No executable or hook is installed here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import struct

from . import partial_tile_clip as clip
from .framed_army_viewport import FramedArmyViewport

ROOT = Path(__file__).resolve().parents[2]
BUILDER_SHA256 = "c2da86edc7fb6bc0e7c3ca5ecca6bf4688a33ffa8d574153dab463c4653da4fb"
HOOK_VA = CLONE_VA = 0x42355A
CLONE_END = 0x423715
HOOK_OLD = bytes.fromhex("ba23000000")
FALLBACK_VA = 0x42355F
SELECTED = 0x511B58
PRIOR = 0x514194
UNIT = 0x526FA0
MASKS = 0x526F78
MARKS = 0x5202C8
INFO = 0x527C24
FONT_POINTER = 0x520724
FONT_INDEX = 0x520728
FONT7_ENTRY = 0x511F1C
FONT7_CACHE = 0x511F20
UNIT_BASE = 147174
UNIT_STRIDE = 725
NATIVE_SPANS = {
    (0x423420, 825): "a4b8ab44adfaaead900fe98302e63711b69d3859a3a064c0d15dd55474d64744",
    (0x423B00, 63): "0ed9539e5f34857a458fc8e82646741764a019180afcefe245b6948025ab3f05",
    (0x423B40, 39): "285f8a14fa55c093d373fba41419e9cce1d44cf217ea9da2f309c395b856b2f9",
    (0x423B90, 30): "7bc2f8206b622e82e68cc0d5ab92150d8829a01ad7b365806eff9c3e1572c641",
}
# Exact fields from native PE HIGHLOW records, checked against the full set.
CLONE_ABSOLUTES = {
    0x006: (MARKS, "army_marks"), 0x01C: (clip.RENDER_DEVICE_GLOBAL, "render_device_global"),
    0x049: (UNIT, "army_unit"), 0x070: (INFO, "army_info"),
    0x08A: (clip.RENDER_DEVICE_GLOBAL, "render_device_global"), 0x0A4: (UNIT, "army_unit"),
    0x0BF: (MARKS, "army_marks"), 0x0D5: (clip.RENDER_DEVICE_GLOBAL, "render_device_global"),
    0x0F9: (UNIT, "army_unit"), 0x101: (clip.CURRENT_PLAYER_GLOBAL, "current_player"),
    0x11F: (0x4EEBC4, "army_number_format"), 0x148: (MASKS, "army_masks"),
    0x156: (UNIT, "army_unit"), 0x176: (MARKS, "army_marks"),
    0x18E: (clip.RENDER_DEVICE_GLOBAL, "render_device_global"),
}
# Machine-decoded CALL instruction starts, never inferred return addresses.
CLONE_CALLS = {
    0x00A: (0x405EC0, "army_sprite_lookup"), 0x074: (0x405EC0, "army_sprite_lookup"),
    0x0C3: (0x405EC0, "army_sprite_lookup"), 0x0F3: (0x40BAE0, "army_lazy_font"),
    0x139: (0x40C150, "army_number_text"), 0x17D: (0x405EC0, "army_sprite_lookup"),
}
# instruction VA, opcode, old scalar, axis. X stride 38 stays unchanged.
COORDINATES = (
    (0x42357C, 0xB9, 400, "y"), (0x423589, 0xBB, 29, "x"),
    (0x4235DD, 0xB9, 401, "y"), (0x4235EA, 0x83, 35, "x8"),
    (0x42363D, 0xB9, 405, "y"), (0x423642, 0x83, 40, "x8"),
    (0x42367F, 0x83, 70, "x8"), (0x423682, 0x68, 450, "y"),
    (0x42368F, 0x83, 32, "x8"), (0x4236C2, 0x83, 58, "x8"),
    (0x4236EE, 0xB9, 402, "y"),
)


@dataclass(frozen=True)
class ArmyHook:
    va: int
    offset: int
    old_bytes: bytes
    new_bytes: bytes
    name: str = "own-army-native-draw-suffix"

    @property
    def rva(self):
        return self.va - 0x400000


@dataclass(frozen=True)
class ArmyDrawBundle(clip.AdapterBundle):
    hook_sites: tuple[ArmyHook, ...] = ()
    candidate_sha256: str = ""
    source_contract: dict = field(default_factory=dict)


def _verify(original, candidate, width, height, minimap_viewport):
    if type(original) is not bytes or type(candidate) is not bytes:
        raise ValueError("immutable original and prerequisite candidate bytes required")
    clip.verify_original(original)
    source = ROOT / "tools/build_framed_modal_candidate.py"
    if hashlib.sha256(source.read_bytes()).hexdigest() != BUILDER_SHA256:
        raise ValueError("reviewed modal candidate builder differs")
    if type(minimap_viewport) is not bool:
        raise ValueError("minimap variant must be a boolean")
    from tools import build_framed_modal_candidate as builder
    rebuilt, metadata, _ = builder.build_candidate(
        original, f"{width}x{height}", minimap_viewport=minimap_viewport)
    if rebuilt != candidate:
        raise ValueError("whole prerequisite candidate reconstruction differs")
    for (va, size), expected in NATIVE_SPANS.items():
        for image in (original, candidate):
            pos = clip.file_offset(image, va, size)
            if hashlib.sha256(image[pos:pos + size]).hexdigest() != expected:
                raise ValueError(f"native army bytes differ at {va:08x}")
    if hashlib.sha256(source.read_bytes()).hexdigest() != BUILDER_SHA256:
        raise ValueError("modal candidate builder changed during verification")
    return metadata


def emit_army_draw(original: bytes, candidate: bytes, *, base_va: int,
                   width: int, height: int, minimap_viewport: bool = True) -> ArmyDrawBundle:
    """Return an uninstalled draw helper and native suffix trampoline.

    ``army_guard`` and ``draw_army`` return EAX=1 on admission/draw, zero on
    rejection. All other GPRs, EFLAGS including DF and caller ESP survive.
    Neither entry takes arguments. ``draw_army`` temporarily changes/restores
    render-device and font-selection globals, uses existing resources only,
    and draws through the native memory vtable. Font glyph rendering may use
    its ordinary renderer scratch; unit/highlight/mask/resource caches are not
    changed. Native sprite and text callees keep their established ABI.

    Exact own-map context only: owner40AD40, lower-row owner1, post callback0,
    selected==prior in0..499, bound unit pointer and interactive current owner
    0..3, signed in-world unit coordinates and inactive fault-free modal state,
    two to
    ten supported32x64 squads, known387x66 backing/badges, loaded font7, and a
    physical memory surface with the canonical memory vtable. Numeric pointer
    checks are not a lifetime/mapping guarantee: the caller must own the game
    thread and readable allocations through the complete draw.

    Installers may replace ONLY the described native42355A five-byte MOV.
    The trampoline restores every entry register/flag and resumes423715 on
    successful draw. Otherwise it replays MOV EDX,35 and resumes42355F, retaining
    original foreign-army/modal/unloaded-resource behavior. This fallback is
    not used by repeated composition. No mouse globals or input hooks change.
    """
    layout = FramedArmyViewport(width, height)
    if width < 800 or type(base_va) is not int or not 0x10000 <= base_va <= 0x7FFF0000:
        raise ValueError("army dock requires width>=800 and a valid explicit x86 allocation")
    metadata = _verify(original, candidate, width, height, minimap_viewport)
    a = clip._Assembler(base_va)
    entries = {}

    def glob(address, purpose):
        a.absolute(address, purpose)

    def transfer(target, purpose, opcode="e8"):
        a.emit(opcode); pos = len(a.code)
        a.relocations.append(clip.Relocation(pos, "rel32", target, purpose))
        a.u32(target - (base_va + pos + 4))

    def reject(op="0f85"):
        a.branch(op, "guard.reject")

    def pointer_eax(limit=0x7FFF0000, *, aligned=True):
        a.emit("3d00000100"); reject("0f82")
        a.emit("3d"); a.u32(limit); reject("0f87")
        if aligned:
            a.emit("a903000000"); reject()

    def resource(address, purpose, limit=0x7FFF0000):
        a.emit("a1"); glob(address, purpose); pointer_eax(limit)

    entries["army_guard"] = base_va + len(a.code)
    a.label("army_guard"); a.emit("9c60")
    for address, purpose, value in (
        (clip.RENDER_HOOK_GLOBAL, "render_hook", 0x40AD40),
        (clip.LOWER_ROW_OWNER_GLOBAL, "lower_row_owner", 1),
        (clip.POST_TILE_CALLBACK_GLOBAL, "post_tile_callback", 0),
    ):
        a.emit("813d"); glob(address, purpose)
        if purpose == "render_hook": glob(value, "map_render_hook_target")
        else: a.u32(value)
        reject()
    for offset in (0, 8, 36, 52, 56):
        a.emit("833d"); glob(metadata["state_va"] + offset, "army_modal_state." + str(offset))
        a.emit("00"); reject()
    resource(clip.MAP_SURFACE_GLOBAL, "map_surface_global")
    a.emit("8138"); a.u32(width | height << 16); reject()
    a.emit("81b8b8000000"); glob(clip.MEMORY_VTABLE, "memory_vtable"); reject()
    a.emit("8b4004"); pointer_eax(0x7FFFFFFF - width * height)
    resource(clip.GAME_DATA_GLOBAL, "game_data_global", 0x7FF00000)
    a.emit("89c6a1"); glob(SELECTED, "army_selected")
    a.emit("3df3010000"); reject("0f87")
    a.emit("3b05"); glob(PRIOR, "army_prior"); reject()
    a.emit("69c0d502000005e63e020001f03b05"); glob(UNIT, "army_unit"); reject()
    a.emit("89c58b1d"); glob(clip.CURRENT_PLAYER_GLOBAL, "current_player")
    a.emit("83fb03"); reject("0f87")
    a.emit("0fb6450439d8"); reject()
    a.emit("69c38f05000083bc061323020000"); reject("0f84")
    for unit_offset, map_offset in ((0, 0x222E0), (2, 0x222E4)):
        a.emit("8b86"); a.u32(map_offset)
        a.emit("83f801"); reject("0f8c")
        a.emit("83f864"); reject("0f8f")
        a.emit("0fbf55" + bytes([unit_offset]).hex())
        a.emit("85d2"); reject("0f8c")
        a.emit("39c2"); reject("0f8d")
    resource(FONT7_CACHE, "army_font7_cache")
    resource(MARKS, "army_marks")
    a.emit("89c7")
    for sprite, sw, sh in ((35, 387, 66), (33, 13, 13), (4, 9, 9), (5, 9, 9)):
        a.emit("8b87"); a.u32(4 * sprite); pointer_eax(aligned=False)
        a.emit("8138"); a.u32(sw | sh << 16); reject()
        a.emit("6683780400"); reject()
    resource(INFO, "army_info"); a.emit("89c731f6")
    a.label("guard.squad")
    a.emit("6bc61f0fbf4c050683f9ff"); a.branch("0f84", "guard.squads_end")
    a.emit("83f922"); reject("0f87")
    a.emit("8b048f"); pointer_eax(aligned=False)
    a.emit("813820004000"); reject()
    a.emit("6683780400"); reject()
    a.emit("4683fe0a"); a.branch("0f8c", "guard.squad")
    a.label("guard.squads_end"); a.emit("83fe02"); reject("0f8c")
    a.emit("b801000000"); a.branch("e9", "guard.return")
    a.label("guard.reject"); a.emit("31c0")
    a.label("guard.return"); a.emit("8944241c619dc3")

    entries["draw_army"] = base_va + len(a.code)
    a.label("draw_army"); a.emit("9c60")
    a.branch("e8", "army_guard"); a.emit("85c0"); a.branch("0f84", "draw.reject")
    for address, purpose in ((clip.RENDER_DEVICE_GLOBAL, "render_device_global"),
                              (FONT_POINTER, "army_font_pointer"), (FONT_INDEX, "army_font_index")):
        a.emit("ff35"); glob(address, purpose)
    a.emit("fc83ec34a1"); glob(clip.MAP_SURFACE_GLOBAL, "map_surface_global")
    a.emit("a3"); glob(clip.RENDER_DEVICE_GLOBAL, "render_device_global")
    a.emit("c705"); glob(FONT_POINTER, "army_font_pointer"); glob(FONT7_ENTRY, "army_font7_entry")
    a.emit("c705"); glob(FONT_INDEX, "army_font_index"); a.u32(7)

    clone_start = len(a.code)
    pos = clip.file_offset(original, CLONE_VA, CLONE_END - CLONE_VA)
    body = original[pos:pos + CLONE_END - CLONE_VA]
    if hashlib.sha256(body).hexdigest() != "39228129b7d7fce30acf02249083a2e551793413fe1e98f056d995147785bf67":
        raise ValueError("native draw-only suffix differs")
    a.code.extend(body)
    for va, opcode, old, axis in COORDINATES:
        at = clone_start + va - CLONE_VA
        if a.code[at] != opcode:
            raise ValueError("native army coordinate opcode differs")
        if axis == "x8":
            if a.code[at + 1] not in (0xC0, 0xC3) or a.code[at + 2] != old:
                raise ValueError("native army ADD imm8 differs")
            a.code[at + 2] = old + layout.dx
        else:
            if struct.unpack_from("<I", a.code, at + 1)[0] != old:
                raise ValueError("native army coordinate scalar differs")
            struct.pack_into("<I", a.code, at + 1, old + (layout.dx if axis == "x" else layout.dy))
    if clip._original_highlow_fields(original, CLONE_VA, len(body)) != set(CLONE_ABSOLUTES):
        raise ValueError("native suffix HIGHLOW inventory differs")
    for at, (target, purpose) in CLONE_ABSOLUTES.items():
        if struct.unpack_from("<I", body, at)[0] != target:
            raise ValueError("native suffix absolute operand differs")
        a.relocations.append(clip.Relocation(clone_start + at, "abs32", target, purpose))
    for at, (target, purpose) in CLONE_CALLS.items():
        if body[at] != 0xE8 or CLONE_VA + at + 5 + struct.unpack_from("<i", body, at + 1)[0] != target:
            raise ValueError("native suffix CALL boundary/target differs")
        field_pos = clone_start + at + 1
        if purpose == "army_lazy_font":
            a.code[field_pos - 1:field_pos + 4] = b"\x90" * 5
        else:
            struct.pack_into("<I", a.code, field_pos, (target - (base_va + field_pos + 4)) & 0xFFFFFFFF)
            a.relocations.append(clip.Relocation(field_pos, "rel32", target, purpose))
    # Native loop exits land exactly here; local stack layout stays unchanged.
    a.emit("83c434")
    for address, purpose in ((FONT_INDEX, "army_font_index"), (FONT_POINTER, "army_font_pointer"),
                              (clip.RENDER_DEVICE_GLOBAL, "render_device_global")):
        a.emit("58a3"); glob(address, purpose)
    a.emit("b801000000"); a.branch("e9", "draw.return")
    a.label("draw.reject"); a.emit("31c0")
    a.label("draw.return"); a.emit("8944241c619dc3")

    entries["native_suffix_hook"] = base_va + len(a.code)
    a.emit("9c60"); a.branch("e8", "draw_army"); a.emit("85c0")
    a.branch("0f84", "native.fallback")
    a.emit("619d"); transfer(CLONE_END, "army_native_continue", "e9")
    a.label("native.fallback"); a.emit("619d" + HOOK_OLD.hex())
    transfer(FALLBACK_VA, "army_native_fallback", "e9")
    code = a.finish()
    hook = ArmyHook(HOOK_VA, clip.file_offset(candidate, HOOK_VA, 5), HOOK_OLD,
                   b"\xe9" + struct.pack("<i", entries["native_suffix_hook"] - HOOK_VA - 5))
    result = ArmyDrawBundle(base_va, code, entries, tuple(a.relocations), width, height,
        hook_sites=(hook,), candidate_sha256=hashlib.sha256(candidate).hexdigest(), source_contract={
            "source_sha256": metadata["source_sha256"] | {"tools/build_framed_modal_candidate.py": BUILDER_SHA256},
            "candidate_reconstructed": True, "installed": False, "native_clone_va": CLONE_VA,
            "native_clone_end": CLONE_END, "native_clone_offset": clone_start,
            "dx": layout.dx, "dy": layout.dy, "backing_rect": [layout.backing.left, layout.backing.top, layout.backing.right, layout.backing.bottom],
            "portrait_origin": [38, height - 81], "portrait_size": [32, 64], "slot_pitch": 38,
            "input_unchanged": True, "mouse_globals_written": False,
            "repeated_draw_loads_resources": False, "repeated_draw_changes_selection": False,
            "requires_readable_thread_owned_context": True, "requires_canonical_memory_vtable": True,
            "native_fallback_retained": True, "minimap_viewport": minimap_viewport,
            "caller_must_restore_overlay_after_full_and_incremental_terrain": True,
        })
    clip.absolute_relocation_offsets(result)
    return result
