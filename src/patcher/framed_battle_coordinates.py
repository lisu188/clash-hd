"""Uninstalled x86 coordinate helpers for the horizontal tactical viewport.

Only bytes and metadata are returned. No hook, image, game state, surface,
process, or runtime claim is created. All four helpers are read-only apart
from their own stack and the EAX return value.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path

from . import partial_tile_clip as clip
from .framed_battle_viewport import TacticalViewport

ROOT = Path(__file__).resolve().parents[2]
BATTLE_STATE = 0x532048
RENDER_OWNER = 0x5199D8
BATTLE_OWNER = 0x42E8B0
REJECT = 0xFFFFFFFF
STATE_BYTES_READ = 816
PINNED_SOURCES = {
    "tools/build_framed_modal_candidate.py": "c2da86edc7fb6bc0e7c3ca5ecca6bf4688a33ffa8d574153dab463c4653da4fb",
    "src/patcher/framed_battle_viewport.py": "8673e36bd04ded2afc8cc3b9d7ff2fed4c48dae891fe289509b44a9070c23bc6",
}
NATIVE_SPANS = {
    0x430C39: "bf07000000",       # Native shared X/Y loop count, not changed.
    0x42C104: "83c307",          # Visibility X limit.
    0x430B33: "83c607",          # Incremental redraw X limit.
    0x42CBAA: "83fd077d0985c07c0583f8077c09",
}


@dataclass(frozen=True)
class BattleCoordinateBundle(clip.AdapterBundle):
    candidate_sha256: str = ""
    source_contract: dict = field(default_factory=dict)


def verify_sources() -> dict[str, str]:
    for name, expected in PINNED_SOURCES.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError("reviewed battle coordinate source differs: " + name)
    return dict(PINNED_SOURCES)


def _verify(original: bytes, candidate: bytes, width: int, height: int,
            minimap_viewport: bool) -> dict:
    if type(original) is not bytes or type(candidate) is not bytes:
        raise ValueError("immutable original and candidate bytes are required")
    clip.verify_original(original)
    sources = verify_sources()
    if type(minimap_viewport) is not bool:
        raise ValueError("minimap selection must be an explicit boolean")
    from tools import build_framed_modal_candidate as builder
    expected, metadata, _ = builder.build_candidate(
        original, f"{width}x{height}", minimap_viewport=minimap_viewport)
    if expected != candidate:
        raise ValueError("exact current framed modal candidate reconstruction required")
    for va, value in NATIVE_SPANS.items():
        span = bytes.fromhex(value)
        for image in (original, candidate):
            offset = clip.file_offset(image, va, len(span))
            if image[offset:offset + len(span)] != span:
                raise ValueError(f"native battle coordinate bytes differ at {va:08x}")
    verify_sources()
    return dict(source_sha256=sources | metadata["source_sha256"],
                prerequisite_stage=metadata["stage"],
                minimap_viewport=minimap_viewport,
                native_spans={f"{va:08x}": value for va, value in NATIVE_SPANS.items()})


def emit_battle_coordinates(original: bytes, candidate: bytes, *, base_va: int,
                            width: int, height: int,
                            minimap_viewport: bool = True) -> BattleCoordinateBundle:
    """Emit four ABI-preserving helpers; nothing is installed.

    Entry EAX is the caller-owned live battle-state pointer. It must equal
    [00532048], be aligned and non-null, and have a readable 816-byte lifetime.
    [005199D8] must equal native battle owner 0042E8B0. Numeric pointer checks
    cannot establish mapping or lifetime: a future owner/thread wrapper must.
    Rows at +800 must be seven, columns at +804 must be 1..20, Y scroll +812
    must be zero. All helpers return FFFFFFFF for rejected context.

    visible_columns: EAX returns min(columns, floor((W-192)/64)).
    clamp_scroll_x: signed EDX request; EAX returns 0..columns-visible.
    These two may repair/query context with an invalid stored X origin.

    visible_world_cell: signed EDX column, ECX row; EAX returns 1 if visible,
    0 for a valid world cell outside the viewport, FFFFFFFF for invalid input.
    screen_to_cell: signed physical EDX X, ECX Y; EAX returns column|(row<<16),
    or FFFFFFFF outside the exact field. Both require stored X scroll +808
    within 0..columns-visible. Bounds precede division; no array is indexed.

    All non-EAX GPRs, caller ESP and EFLAGS (including DF) are preserved. No
    globals/state/pixels are written and no native callee is invoked. Packed
    cells are coordinates, not a native occupancy-array offset. The consumer
    must check the rejection sentinel before decoding or indexing. A caller
    of visible_world_cell must compare exactly with 1, never treat any nonzero
    return (including the rejection sentinel) as visible.
    """
    layout = TacticalViewport(width, height, 20)
    if type(base_va) is not int or not 0x10000 <= base_va <= 0x7FFF0000:
        raise ValueError("invalid explicit x86 code allocation")
    contract = _verify(original, candidate, width, height, minimap_viewport)
    capacity = (width - 192) // 64
    a = clip._Assembler(base_va)
    entries = {}

    def reject(name, opcode="0f85"):
        a.branch(opcode, name + ".reject")

    def context(name, *, scroll):
        entries[name] = base_va + len(a.code)
        a.label(name)
        # PUSHFD/PUSHAD: saved EDX +20, ECX +24, EAX +28, flags +32.
        a.emit("9c60813d"); a.absolute(RENDER_OWNER, "battle_render_owner")
        a.absolute(BATTLE_OWNER, "native_battle_owner"); reject(name)
        a.emit("8b74241c85f6"); reject(name, "0f84")
        a.emit("3b35"); a.absolute(BATTLE_STATE, "battle_state_global"); reject(name)
        a.emit("81fe00000100"); reject(name, "0f82")
        a.emit("81fed0fcff7f"); reject(name, "0f87")
        a.emit("f7c603000000"); reject(name)
        a.emit("83be2003000007"); reject(name)
        a.emit("8b9e2403000083fb01"); reject(name, "0f8c")
        a.emit("83fb14"); reject(name, "0f8f")
        a.emit("83be2c03000000"); reject(name)
        a.emit("bf"); a.u32(capacity)
        a.emit("39fb"); a.branch("0f8d", name + ".capacity")
        a.emit("89df"); a.label(name + ".capacity")
        # EBX = actual world columns; EDI = visible columns. Never alter rows.
        if scroll:
            a.emit("8bae2803000085ed"); reject(name, "0f8c")
            a.emit("89d829f839c5"); reject(name, "0f8f")

    def finish(name):
        a.branch("e9", name + ".return")
        a.label(name + ".reject"); a.emit("b8ffffffff")
        a.label(name + ".return"); a.emit("8944241c619dc3")

    name = "visible_columns"
    context(name, scroll=False)
    a.emit("89f8")
    finish(name)

    name = "clamp_scroll_x"
    context(name, scroll=False)
    a.emit("8b44241429fb85c0")
    a.branch("0f89", name + ".nonnegative")
    a.emit("31c0")
    a.branch("e9", name + ".return")
    a.label(name + ".nonnegative")
    a.emit("39d8")
    a.branch("0f8e", name + ".return")
    a.emit("89d8")
    finish(name)

    name = "visible_world_cell"
    context(name, scroll=True)
    a.emit("8b5424148b4c241885d2"); reject(name, "0f8c")
    a.emit("39da"); reject(name, "0f8d")
    a.emit("85c9"); reject(name, "0f8c")
    a.emit("83f907"); reject(name, "0f8d")
    a.emit("31c039ea")
    a.branch("0f8c", name + ".return")
    a.emit("01ef39fa")
    a.branch("0f8d", name + ".return")
    a.emit("b801000000")
    finish(name)

    name = "screen_to_cell"
    context(name, scroll=True)
    a.emit("8b5424148b4c241883fa20"); reject(name, "0f8c")
    a.emit("c1e70683c72039fa"); reject(name, "0f8d")
    a.emit("83f910"); reject(name, "0f8c")
    a.emit("81f9d0010000"); reject(name, "0f8d")
    a.emit("83ea20c1ea0601ea83e910c1e906c1e11089d009c8")
    finish(name)

    code = a.finish()
    if base_va + len(code) > 0x80000000:
        raise ValueError("emitted x86 allocation wraps the supported user range")
    contract.update(
        revision="framed_battle_coordinates_v1", candidate_reconstructed=True,
        viewport_capacity=capacity, maximum_visible_columns=layout.visible_columns,
        battle_state_global=BATTLE_STATE, render_owner_global=RENDER_OWNER,
        required_owner=BATTLE_OWNER, state_bytes_read=STATE_BYTES_READ,
        rows_offset=800, columns_offset=804, scroll_x_offset=808, scroll_y_offset=812,
        reject_sentinel=REJECT, writes_game_state=False, calls_native_code=False,
        requires_caller_owned_readable_state=True, thread_or_lifetime_proof=False,
        installed=False, runtime_executed=False, input_proof=False, promotion_ready=False)
    result = BattleCoordinateBundle(base_va=base_va, code=code, entries=entries,
                                   relocations=tuple(a.relocations), width=width, height=height,
                                   candidate_sha256=hashlib.sha256(candidate).hexdigest(),
                                   source_contract=contract)
    clip.absolute_relocation_offsets(result)
    verify_sources()
    return result
