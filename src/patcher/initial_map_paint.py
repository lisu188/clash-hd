"""Offline, validation-only first-PlayGame map-paint trampoline.

Appends to the authenticated partial-tile hook bundle; does not install hooks,
write an executable, or claim runtime success. Initial owner installation runs
the displaced MOV/POP and UI resource load once, then conditionally performs a
bounded full paint. The untouched nextPlayer join bypasses this trampoline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib

from . import partial_tile_clip as clip
from . import partial_tile_hooks as hooks
from .framed_viewport import FramedViewport


HOOK_VA = 0x40B884
HOOK_OLD = bytes.fromhex("bed84c54005f")
SHARED_UI_JOIN = 0x40B88A
NATIVE_RESUME = 0x40B894
NATIVE_UI = 0x423370
NATIVE_FULL_PAINT = 0x418700
CURSOR_OBJECT = 0x544CD8
INFO_SPRITES_GLOBAL = 0x527C24
SHARED_UI_HIGHLOW_VA = 0x40B88B
NATIVE_ENTRY_BYTES = bytes.fromhex("bed84c54005fa1ec025200e8dc7a0100")
# These ranges authenticate first-entry vs nextPlayer control flow and the UI
# allocation whose post-call resource/global/register state must be preserved.
NATIVE_SPANS = (
    (HOOK_VA, 0x10, "2d2761525178e3d45a287ffcc84466c53a9a18258fd781f24746113e2371a6a4"),
    (0x40B81C, 0xAE, "01d971241d5479517040471de1646467d483af15387b87558cc50c6eb1799a3c"),
    (NATIVE_UI, 0x61, "ff5fa4bd24e5fafeb907f51330801f5d28bba9f892008479deced3d721ee878b"),
)
# Let S be native ESP after UI_SetCurrentPlayer returns. The added PUSHFD,
# PUSHAD and exact render-device pointer consume 40 bytes. CALL418700, its
# authenticated 6-register/24-local frame, and the full hook's PUSHFD/PUSHAD
# consume another 88. These are observation relationships, not pass markers.
UI_TO_ADMISSION_STACK_BYTES = 40
FULL_STATUS_TO_READY_STACK_BYTES = 88


@dataclass(frozen=True)
class InitialMapPaintBundle(hooks.HookBundle):
    initial_status_vas: dict[str, int] = field(default_factory=dict)
    initial_contract: dict = field(default_factory=dict)


def _verify_initial_contract(original: bytes, candidate: bytes) -> None:
    for va, size, expected_hash in NATIVE_SPANS:
        for data in (original, candidate):
            pos = clip.file_offset(data, va, size)
            if hashlib.sha256(data[pos:pos + size]).hexdigest() != expected_hash:
                raise ValueError(f"initial map-paint native span differs at 0x{va:08X}")
    if clip._original_highlow_fields(original, HOOK_VA, len(NATIVE_ENTRY_BYTES)) != {1, 7}:
        raise ValueError("initial/shared UI HIGHLOW inventory differs")
    if clip._original_highlow_fields(original, HOOK_VA, len(HOOK_OLD)) != {1}:
        raise ValueError("initial map-paint displaced HIGHLOW inventory differs")
    pos = clip.file_offset(original, NATIVE_FULL_PAINT, 9)
    if original[pos:pos + 9] != bytes.fromhex("53515256575583ec18"):
        raise ValueError("native full-paint stack frame differs")


def emit_hook_bundle(original: bytes, combined_candidate: bytes, *, base_va: int,
                     width: int, height: int, layout: FramedViewport | None = None) -> InitialMapPaintBundle:
    """Return the unchanged three-hook payload plus a first-entry trampoline.

    Admission requires loaded INFO resources, the existing composition guard,
    callback zero, map dimensions 1..100, a complete native full-tile window,
    and nonnegative bounded scroll. This runs BEFORE native pointer formation.
    Reject preserves the original post-UI continuation and exposes EAX=0 at
    ``admission``. An admitted CALL418700 uses EAX=1. Its return EAX has no
    success meaning: require the matching existing full status pair instead.

    All post-UI GPR/flags and the exact render-device pointer are restored.
    No once flag, new mutable storage, or native shared-join patch is needed.
    ``installation_ready`` remains false: installing and validating this new
    stage belongs to a separate caller with its own byte and runtime gates.
    """
    bundle = hooks.emit_hook_bundle(original, combined_candidate, base_va=base_va,
                                    width=width, height=height, layout=layout)
    full_tiles = ((width - 32) // 64, (height - 16) // 64) if layout is None else layout.full_tiles
    _verify_initial_contract(original, combined_candidate)
    a = clip._Assembler(base_va)
    a.code.extend(bundle.code)
    a.relocations.extend(bundle.relocations)
    initial_status_vas: dict[str, int] = {}
    calls: dict[str, tuple[int, int]] = {}

    def transfer(opcode: str, target: int, purpose: str) -> int:
        start = len(a.code)
        a.emit(opcode)
        pos = len(a.code)
        a.relocations.append(clip.Relocation(pos, "rel32", target, purpose))
        a.u32(target - (base_va + pos + 4))
        return base_va + start

    def mark(name: str) -> None:
        a.label("initial_" + name)
        initial_status_vas[name] = base_va + len(a.code)

    # Emit admission first so its CALL has explicit rel32 target metadata.
    a.label("initial_paint_admission")
    a.emit("60833d")                         # PUSHAD; CMP [info],0
    a.absolute(INFO_SPRITES_GLOBAL, "initial_info_sprites")
    a.emit("00")
    a.branch("0f84", "initial_admission_reject")
    transfer("e8", bundle.entries["composition_guard"], "initial_composition_guard")
    a.emit("83f801")
    a.branch("0f85", "initial_admission_reject")
    a.emit("833d")
    a.absolute(clip.TILE_CALLBACK_GLOBAL, "tile_callback")
    a.emit("00")
    a.branch("0f85", "initial_admission_reject")
    a.emit("8b15")                          # MOV EDX,[game data]
    a.absolute(clip.GAME_DATA_GLOBAL, "game_data_global")
    a.emit("85d2")
    a.branch("0f84", "initial_admission_reject")
    for dimension, scroll, count in ((0x222E0, 0x222E8, full_tiles[0]),
                                     (0x222E4, 0x222EC, full_tiles[1])):
        a.emit("8b82"); a.u32(dimension)     # MOV EAX,[EDX+dimension]
        a.emit("83f801")
        a.branch("0f8c", "initial_admission_reject")
        a.emit("83f864")
        a.branch("0f8f", "initial_admission_reject")
        a.emit("3d"); a.u32(count)
        a.branch("0f8c", "initial_admission_reject")
        a.emit("2d"); a.u32(count)           # EAX=max legal scroll
        a.emit("8b8a"); a.u32(scroll)
        a.emit("85c9")
        a.branch("0f88", "initial_admission_reject")
        a.emit("39c1")                      # CMP ECX,EAX (signed)
        a.branch("0f8f", "initial_admission_reject")
    a.emit("c744241c0100000061c3")           # saved EAX=1; POPAD; RET
    a.label("initial_admission_reject")
    a.emit("c744241c0000000061c3")

    a.label("hook_initial_paint")
    a.emit("be")                            # Replay MOV ESI,object; POP EDI.
    a.absolute(CURSOR_OBJECT, "initial_cursor_object")
    a.emit("5fa1")
    a.absolute(clip.CURRENT_PLAYER_GLOBAL, "current_player")
    calls["ui_return"] = (transfer("e8", NATIVE_UI, "initial_native_ui"), NATIVE_UI)
    mark("ui_return")
    a.emit("9c60ff35")                      # Preserve actual post-UI state.
    a.absolute(clip.RENDER_DEVICE_GLOBAL, "render_device_global")
    admission_va = base_va + a.labels["initial_paint_admission"]
    calls["admission"] = (transfer("e8", admission_va, "initial_admission_call"), admission_va)
    mark("admission")
    a.emit("83f801")
    a.branch("0f85", "initial_paint_restore")
    mark("ready")
    a.emit("b801000000")
    calls["paint_return"] = (transfer("e8", NATIVE_FULL_PAINT, "initial_native_full_paint"), NATIVE_FULL_PAINT)
    mark("paint_return")
    a.emit("90")                            # Reject skips this return-only point.
    a.label("initial_paint_restore")
    a.emit("8f05")                          # Restore pointer even on reject.
    a.absolute(clip.RENDER_DEVICE_GLOBAL, "render_device_global")
    a.emit("619d")
    transfer("e9", NATIVE_RESUME, "initial_native_resume")

    code = a.finish()
    entries = dict(bundle.entries)
    entries.update({name: base_va + pos for name, pos in a.labels.items()})
    site = hooks.HookSite("initial_paint", clip.file_offset(combined_candidate, HOOK_VA, len(HOOK_OLD)),
                          HOOK_VA, HOOK_OLD, entries["hook_initial_paint"], NATIVE_RESUME,
                          (HOOK_VA + 1,))
    observers = {}
    for name, size in (("ui_return", 8), ("admission", 9), ("ready", 10), ("paint_return", 14)):
        va = initial_status_vas[name]
        observers[name] = {"instruction_va": va, "start_va": va, "size": size,
                           "end_va_exclusive": va + size,
                           "bytes": code[va - base_va:va - base_va + size].hex()}
        if name in calls:
            call_va, target = calls[name]
            observers[name]["preceding_call"] = {
                "instruction_va": call_va, "size": 5, "target_va": target,
                "bytes": code[call_va - base_va:call_va - base_va + 5].hex()}
    contract = {
        "schema_version": 1,
        "proof_class": "uninstalled_validation_only_emitted_x86",
        "native_site": {"va": HOOK_VA, "rva": HOOK_VA - hooks.IMAGE_BASE,
                        "offset": site.offset, "size": len(HOOK_OLD), "old_bytes": HOOK_OLD.hex(),
                        "entry_va": site.entry_va, "resume_va": NATIVE_RESUME,
                        "removed_highlow_vas": [HOOK_VA + 1]},
        "native_entry_span": {"va": HOOK_VA, "size": len(NATIVE_ENTRY_BYTES),
                              "bytes": NATIVE_ENTRY_BYTES.hex()},
        "preserved_shared_join_va": SHARED_UI_JOIN,
        "preserved_shared_highlow_va": SHARED_UI_HIGHLOW_VA,
        "native_spans": [{"va": va, "size": size, "sha256": sha} for va, size, sha in NATIVE_SPANS],
        "observer_spans": observers,
        "stack": {"ui_return_minus_admission": UI_TO_ADMISSION_STACK_BYTES,
                  "admission_equals_ready_equals_paint_return": True,
                  "full_status_plus_to_ready": bundle.layout_contract.get(
                      "full_status_to_caller_before_call", FULL_STATUS_TO_READY_STACK_BYTES)},
        "full_tiles": list(full_tiles),
        "paint_return_is_success": False,
    }
    result = InitialMapPaintBundle(
        base_va=base_va, code=code, entries=entries, relocations=tuple(a.relocations),
        width=width, height=height, installation_ready=False,
        hook_sites=bundle.hook_sites + (site,), status_vas=dict(bundle.status_vas),
        candidate_sha256=bundle.candidate_sha256, layout_contract=bundle.layout_contract,
        initial_status_vas=initial_status_vas,
        initial_contract=contract)
    clip.absolute_relocation_offsets(result)
    return result
