"""Authenticated, uninstalled mouse gates for the prospective framed map.

Only three mouse CALLs and two obsolete panel branches are described. Keyboard,
menu, callback and descriptor bytes are not changed. Emitted code is returned
in memory; no candidate, stage, input event or manual proof is produced.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct

from . import partial_tile_clip as clip
from .framed_viewport import FramedViewport

IMAGE_BASE = 0x400000
MINIMAP_GATE = 0x40DD60
CLICK_GATE = 0x4608F0
PRIMARY_SURFACE = 0x51D4C0
MOUSE_X = 0x544CFC
MOUSE_Y = 0x544D00
MOUSE_SHIFT = 0x54512C
MINIMAP_ORIGIN = 0x523344
MINIMAP_SIZE = 0x523348
CALL_SITES = (
    ("main_mouse", 0x4084A9, "e8b2580000", MINIMAP_GATE, "minimap_gate"),
    ("after_keyboard_mouse", 0x407F3C, "e81f5e0000", MINIMAP_GATE, "minimap_gate"),
    ("selection_mouse", 0x408039, "e8b2880500", CLICK_GATE, "click_gate"),
)
PANEL_SITES = (("main_fixed_panel", 0x40855D, "0f8d86020000"),
               ("selection_fixed_panel", 0x4080AA, "0f8d86000000"))
# Complete minimap gate and the click predicate, plus the source-audited route
# prefixes. These bind native argument/result conventions and branch context;
# the known original SHA additionally binds all preceding keyboard handling.
NATIVE_CONTRACTS = (
    (0x40DD60, 126, "0e5eb8d859a898764159436fa781de9802a7c91b36450821a758b842fb392cb0"),
    (0x4084A0, 195, "bfe0c321d234c70ea348df84132c73b8d21419ee023a20d30dcaeb9c2a9a7e88"),
    (0x407F3C, 16, "5d5cc6204d55a9024e4e89d9cd7f4db9860b2c00a6d6b50e1acf093cbd878a36"),
    (0x408030, 128, "de5f44639bb87eb71cb6002ce372d3fafe179c18a99d99ede7964b699e4fade1"),
)


@dataclass(frozen=True)
class InputPatch:
    name: str
    offset: int
    va: int
    old_bytes: bytes
    new_bytes: bytes
    relocations: tuple[clip.Relocation, ...] = ()
    removed_highlow_vas: tuple[int, ...] = ()

    @property
    def rva(self) -> int:
        return self.va - IMAGE_BASE


@dataclass(frozen=True)
class FramedInputBundle(clip.AdapterBundle):
    hook_sites: tuple[InputPatch, ...] = ()
    scalar_patches: tuple[InputPatch, ...] = ()
    original_sha256: str = ""


def _native_highlow_vas(original: bytes) -> set[int]:
    pe = struct.unpack_from("<I", original, 0x3C)[0]
    rva, size = struct.unpack_from("<II", original, pe + 24 + 96 + 40)
    pos = clip.file_offset(original, IMAGE_BASE + rva, size)
    end, fields = pos + size, set()
    while pos < end:
        page, block = struct.unpack_from("<II", original, pos)
        if block < 8 or block % 2 or pos + block > end:
            raise ValueError("invalid native relocation directory")
        for entry in struct.unpack_from("<" + "H" * ((block - 8) // 2), original, pos + 8):
            if entry >> 12 == 3:
                field = IMAGE_BASE + page + (entry & 0xFFF)
                if field in fields:
                    raise ValueError("duplicate native HIGHLOW")
                fields.add(field)
            elif entry >> 12:
                raise ValueError("unsupported native relocation kind")
        pos += block
    return fields


def emit_input_bundle(original: bytes, *, base_va: int, width: int,
                      height: int) -> FramedInputBundle:
    """Return two preserving CALL wrappers and explicit uninstalled patches.

    ``minimap_gate`` returns 1 to deny and 0 to continue; ``click_gate`` returns
    0 to deny and 1 to continue. All other GPR, ESP and entry flags survive.
    Each native caller immediately TESTs EAX, so it consumes no native flags.
    Native4608F0 is called first with the original EAX button-object argument.
    Native40DD60 follows a context preflight protecting its gameData/player
    dereferences; its result precedes pixel/world admission in both wrappers.

    Current player0..4 must be interactive. The separate native minimap player
    selector is checked independently. Ordinary40AD40 owner, no lower/post
    owner, and known tile callbacks0/425120/429EC0 are supported. These callback
    identities do not change the source-audited coordinate conversion.

    The target must be the physical W/H native memory map. Enabled minimap
    backing uses actual word dimensions, must fit the framed right anchor,
    and excludes its complete footprint in addition to the native strict
    interior test. Signed shifted mouse bounds precede tile conversion. World
    dimensions1..100 and full-count scroll clamp precede world-coordinate
    checks; an outside-world partial tail cannot reach a native world pointer.

    No fallback admits an unknown owner, target or stale minimap. Other owners
    require independent integration. Future installation must bind exact
    pre-framed candidate bytes and install all five records together; removing
    either old panel branch alone is unsafe. No target memory is written.
    """
    clip.verify_original(original)
    layout = FramedViewport(width, height)
    if type(base_va) is not int or not 0x10000 <= base_va <= 0x7FFF0000:
        raise ValueError("invalid x86 allocation")
    for va, size, expected in NATIVE_CONTRACTS:
        off = clip.file_offset(original, va, size)
        if hashlib.sha256(original[off:off + size]).hexdigest() != expected:
            raise ValueError("native mouse route contract differs")
    click = bytes.fromhex("f6402c010f95c025ff000000c3")
    off = clip.file_offset(original, CLICK_GATE, len(click))
    if original[off:off + len(click)] != click:
        raise ValueError("native click predicate differs")
    fields = _native_highlow_vas(original)
    for _, va, old_hex, *_ in (*CALL_SITES, *PANEL_SITES):
        old = bytes.fromhex(old_hex)
        off = clip.file_offset(original, va, len(old))
        if original[off:off + len(old)] != old:
            raise ValueError("mouse patch old bytes differ")
        if any(field < va + len(old) and field + 4 > va for field in fields):
            raise ValueError("mouse patch displaces a native HIGHLOW")

    a = clip._Assembler(base_va)

    def glob(address: int, purpose: str) -> None:
        a.absolute(address, purpose)

    def native(target: int, purpose: str) -> None:
        a.emit("e8")
        pos = len(a.code)
        a.relocations.append(clip.Relocation(pos, "rel32", target, purpose))
        a.u32(target - (base_va + pos + 4))

    def result(value: int) -> None:
        a.emit("c744241c"); a.u32(value)
        a.emit("619dc3")  # Change saved EAX only; restore GPR/flags/stack.

    # No EBP frame is needed by the wrappers. Original argument registers
    # remain intact across context_guard, except EAX which native40DD60 ignores.
    for name, active in (("minimap_gate", False), ("click_gate", True)):
        a.label(name); a.emit("9c60")
        if active:
            native(CLICK_GATE, "native_click_gate")
            a.emit("85c0"); a.branch("0f84", name + ".deny")
        a.branch("e8", "context_guard")
        a.emit("85c0"); a.branch("0f84", name + ".deny")
        native(MINIMAP_GATE, "native_minimap_gate")
        a.emit("85c0"); a.branch("0f85", name + ".deny")
        a.branch("e8", "pixel_guard")
        a.emit("85c0"); a.branch("0f84", name + ".deny")
        result(1 if active else 0)
        a.label(name + ".deny"); result(0 if active else 1)

    a.label("context_guard"); a.emit("9c60")
    def bad(opcode: str = "0f85") -> None:
        a.branch(opcode, "context_guard.deny")
    for address, purpose, value in (
            (clip.RENDER_HOOK_GLOBAL, "render_hook", 0x40AD40),
            (clip.LOWER_ROW_OWNER_GLOBAL, "lower_row_owner", 0),
            (clip.POST_TILE_CALLBACK_GLOBAL, "post_tile_callback", 0)):
        a.emit("813d"); glob(address, purpose)
        if value: glob(value, "ordinary_map_owner")
        else: a.u32(0)
        bad()
    a.emit("a1"); glob(clip.TILE_CALLBACK_GLOBAL, "tile_callback")
    a.emit("85c0"); a.branch("0f84", "context_guard.callback")
    for target in (0x425120, 0x429EC0):
        a.emit("3d"); glob(target, "supported_tile_callback")
        a.branch("0f84", "context_guard.callback")
    a.branch("e9", "context_guard.deny")
    a.label("context_guard.callback")
    a.emit("a1"); glob(clip.MAP_SURFACE_GLOBAL, "map_surface_global")
    a.emit("85c0"); bad("0f84")
    a.emit("3d"); glob(PRIMARY_SURFACE, "primary_surface"); bad("0f84")
    a.emit("8138"); a.u32(width | (height << 16)); bad()
    a.emit("83780400"); bad("0f84")
    a.emit("81b8b8000000"); glob(clip.MEMORY_VTABLE, "memory_vtable"); bad()
    a.emit("8b35"); glob(clip.GAME_DATA_GLOBAL, "game_data_global")
    a.emit("85f6"); bad("0f84")
    a.emit("a1"); glob(clip.CURRENT_PLAYER_GLOBAL, "current_player")
    a.emit("83f805"); bad("0f83")  # unsigned rejects negative too.
    a.emit("69c08f05000083bc061323020000"); bad("0f84")
    a.emit("83bec73e020005"); bad("0f83")
    result(1)
    a.label("context_guard.deny"); result(0)

    a.label("pixel_guard"); a.emit("9c60")
    def reject(opcode: str = "0f85") -> None:
        a.branch(opcode, "pixel_guard.deny")
    a.emit("8b35"); glob(clip.GAME_DATA_GLOBAL, "game_data_global")
    a.emit("0fb60d"); glob(MOUSE_SHIFT, "mouse_shift")
    a.emit("8b1d"); glob(MOUSE_X, "mouse_x")
    a.emit("8b15"); glob(MOUSE_Y, "mouse_y")
    a.emit("d3fbd3fa83fb20"); reject("0f8c")
    a.emit("81fb"); a.u32(layout.terrain.right); reject("0f8f")
    a.emit("83fa10"); reject("0f8c")
    a.emit("81fa"); a.u32(layout.terrain.bottom); reject("0f8f")
    a.emit("81fb"); a.u32(layout.action_bar.left)
    a.branch("0f8c", "pixel_guard.command_clear")
    a.emit("81fa"); a.u32(layout.action_bar.top); reject("0f8d")
    a.label("pixel_guard.command_clear")
    # Native minimap gate has already run. Cover its strict-test border too.
    a.emit("6986c73e02008f05000083bc060f23020000")
    a.branch("0f84", "pixel_guard.minimap_clear")
    a.emit("0fb705"); glob(MINIMAP_ORIGIN, "minimap_origin")
    a.emit("0fb73d"); glob(MINIMAP_SIZE, "minimap_size")
    a.emit("85ff"); reject("0f84")
    a.emit("83f820"); reject("0f8c")
    a.emit("01c781ff"); a.u32(width - 32); reject()
    a.emit("39c3"); a.branch("0f8c", "pixel_guard.minimap_x_clear")
    a.emit("89d8")  # Remember x inside [left,right); actual x already <right.
    a.branch("e9", "pixel_guard.minimap_y")
    a.label("pixel_guard.minimap_x_clear"); a.emit("b8ffffffff")
    a.label("pixel_guard.minimap_y")
    a.emit("0fb70d"); glob(MINIMAP_ORIGIN + 2, "minimap_top")
    a.emit("83f910"); reject()
    a.emit("0fb73d"); glob(MINIMAP_SIZE + 2, "minimap_height")
    a.emit("85ff"); reject("0f84")
    a.emit("01cf81ff"); a.u32(height - 16); reject("0f8f")
    a.emit("83f8ff"); a.branch("0f84", "pixel_guard.minimap_clear")
    a.emit("39fa"); reject("0f8c")
    a.label("pixel_guard.minimap_clear")
    # Validate the full-loop world/scroll contract before forming even a tile
    # coordinate; no pointer into any world array is formed by this helper.
    for map_disp, scroll_disp, count, axis in ((0x222E0, 0x222E8, layout.full_tiles[0], "x"),
                                              (0x222E4, 0x222EC, layout.full_tiles[1], "y")):
        a.emit("8b86"); a.u32(map_disp)
        a.emit("83f801"); reject("0f8c")
        a.emit("83f864"); reject("0f8f")
        a.emit("3d"); a.u32(count); reject("0f8c")
        a.emit("2d"); a.u32(count)
        a.emit("8bbe"); a.u32(scroll_disp)
        a.emit("85ff"); reject("0f8c")
        a.emit("39c7"); reject("0f8f")
        a.emit("89d8" if axis == "x" else "89d0")
        a.emit("83e820c1f806" if axis == "x" else "83e810c1f806")
        a.emit("01f83b86"); a.u32(map_disp); reject("0f8d")
    result(1)
    a.label("pixel_guard.deny"); result(0)
    code = a.finish()
    if base_va + len(code) > 0x80000000:
        raise ValueError("input helper exceeds supported x86 allocation")
    entries = {name: base_va + pos for name, pos in a.labels.items()}
    hooks = []
    for name, va, old_hex, native_target, entry in CALL_SITES:
        old = bytes.fromhex(old_hex)
        if va + 5 + struct.unpack_from("<i", old, 1)[0] != native_target:
            raise ValueError("native mouse CALL target differs")
        target = entries[entry]
        new = b"\xe8" + struct.pack("<i", target - (va + 5))
        hooks.append(InputPatch(name, clip.file_offset(original, va, 5), va, old, new,
                                (clip.Relocation(1, "rel32", target, entry),)))
    scalar = tuple(InputPatch(name, clip.file_offset(original, va, 6), va,
                              bytes.fromhex(old_hex), b"\x90" * 6)
                   for name, va, old_hex in PANEL_SITES)
    bundle = FramedInputBundle(base_va, code, entries, tuple(a.relocations), width, height,
                                False, tuple(hooks), scalar, clip.ORIGINAL_SHA256)
    clip.absolute_relocation_offsets(bundle)
    return bundle
