"""Framed-stage full-paint clipping and C5 bypass, emitted but not installed.

The native full loop receives its original arguments and frame. An outer
invocation owns the temporary clipping vtable and restores exactly that table
after the native return. Before frame/overlay composition the convergence
hook switches back to the memory vtable. No shared latch or mutable cache is
introduced. The existing per-native-invocation stack latch controls C5 bypass.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import struct

from . import partial_tile_clip as clip
from . import partial_tile_hooks as hooks
from .framed_viewport import FramedViewport


FULL_ENTRY_VA = 0x418700
FULL_ENTRY_OLD = bytes.fromhex("53515256575583ec18")
FULL_BODY_VA = 0x418709
FRAME_GATE_VA = 0x4187AF
OLD_C5_VA = 0x51BE00
EXTRA_FULL_STACK_BYTES = 60  # flags/GPR36 + locals16 + saved EBP4 + extra CALL4
FULL_STATUS_TO_CALLER_BEFORE_CALL = 88 + EXTRA_FULL_STACK_BYTES


def append_full_entry(original: bytes, candidate: bytes, bundle: hooks.HookBundle,
                      *, layout: FramedViewport) -> hooks.HookBundle:
    """Append two exact hooks to an authenticated framed composition bundle.

    Unsupported/pre-HD composition falls back to the original full entry.
    Once composition is admitted, invalid world/full-loop bounds return zero
    before pointer formation, without calling the native loop. This is not
    support for smaller worlds: a future complete renderer must clear their
    full cells as well, and this rejection cannot be claimed as a rendered map.

    On the admitted path, EAX and flags from the native return are preserved,
    as are its original non-result GPR/stack ABI. Native render-device changes
    remain native behavior; this wrapper changes and restores only the map
    vtable. Nested admitted calls retain their exact entry table in stack locals.
    """
    hooks._verify_contract(original, candidate, layout.width, layout.height, layout)
    if ((bundle.width, bundle.height) != (layout.width, layout.height)
            or bundle.candidate_sha256 != hashlib.sha256(candidate).hexdigest()
            or any(name not in bundle.entries for name in ("composition_guard", "clipped_vtable", "draw_frame"))):
        raise ValueError("full-entry wrapper needs the matching framed composition bundle")
    clip.absolute_relocation_offsets(bundle)
    entry_offset = clip.file_offset(candidate, FULL_ENTRY_VA, len(FULL_ENTRY_OLD))
    if candidate[entry_offset:entry_offset+len(FULL_ENTRY_OLD)] != FULL_ENTRY_OLD:
        raise ValueError("native full-entry displaced bytes differ")
    gate_old = b"\xe9" + struct.pack("<i", OLD_C5_VA-(FRAME_GATE_VA+5)) + b"\x90"*3
    gate_offset = clip.file_offset(candidate, FRAME_GATE_VA, len(gate_old))
    if candidate[gate_offset:gate_offset+len(gate_old)] != gate_old:
        raise ValueError("canonical C5 entry differs")
    for va, size in ((FULL_ENTRY_VA, len(FULL_ENTRY_OLD)), (FRAME_GATE_VA, len(gate_old))):
        if clip._original_highlow_fields(original, va, size):
            raise ValueError("unexpected displaced full/frame HIGHLOW field")
    a = clip._Assembler(bundle.base_va)
    a.code.extend(bundle.code)
    a.relocations.extend(bundle.relocations)

    def transfer(opcode, target, purpose):
        a.emit(opcode)
        pos = len(a.code)
        a.relocations.append(clip.Relocation(pos, "rel32", target, purpose))
        a.u32(target-(a.base+pos+4))

    a.label("framed_native_full_trampoline")
    a.emit(FULL_ENTRY_OLD.hex())
    transfer("e9", FULL_BODY_VA, "framed_native_full_body")

    a.label("hook_framed_full_entry")
    a.emit("9c6089e583ec1055")
    transfer("e8", bundle.entries["composition_guard"], "framed_full_composition_guard")
    a.emit("5d83f801")
    a.branch("0f85", "framed_full_fallback")
    a.emit("8b15");a.absolute(clip.GAME_DATA_GLOBAL,"game_data_global")
    a.emit("85d2");a.branch("0f84","framed_full_reject")
    for dimension, scroll, count in ((0x222E0,0x222E8,layout.full_tiles[0]),
                                     (0x222E4,0x222EC,layout.full_tiles[1])):
        a.emit("8b82");a.u32(dimension)
        a.emit("83f801");a.branch("0f8c","framed_full_reject")
        a.emit("83f864");a.branch("0f8f","framed_full_reject")
        a.emit("3d");a.u32(count);a.branch("0f8c","framed_full_reject")
        a.emit("2d");a.u32(count)
        a.emit("8b8a");a.u32(scroll)
        a.emit("85c9");a.branch("0f88","framed_full_reject")
        a.emit("39c1");a.branch("0f8f","framed_full_reject")
    a.emit("a1");a.absolute(clip.MAP_SURFACE_GLOBAL,"map_surface_global")
    a.emit("8945fc8b90b80000008955f8c780b8000000")
    a.absolute(bundle.entries["clipped_vtable"],"clipped_vtable")
    a.label("framed_full_admitted")
    # Restore original native argument registers and flags before the extra
    # native CALL. Save our own EBP separately from the native caller's EBP.
    a.emit("55ff75209d8b5d108b4d188b55148b75048b7d008b451c8b6d08")
    a.branch("e8","framed_native_full_trampoline")
    a.emit("5d8945f49c8f45f0")
    a.label("framed_full_return")
    a.emit("8b45fc8b55f88990b80000008b45f489451c8b45f089452089ec619dc3")
    a.label("framed_full_reject")
    a.emit("c7451c0000000089ec619dc3")
    a.label("framed_full_fallback")
    a.emit("89ec619d")
    a.branch("e9","framed_native_full_trampoline")

    a.label("hook_framed_frame_gate")
    a.emit("9c837c240401")
    a.branch("0f85","framed_gate_fallback")
    a.emit("9d85ed")
    a.branch("0f84","framed_gate_offscreen")
    transfer("e9",0x4187B7,"framed_gate_full_present")
    a.label("framed_gate_offscreen")
    transfer("e9",0x4189A3,"framed_gate_native_epilogue")
    a.label("framed_gate_fallback")
    a.emit("9d")
    transfer("e9",OLD_C5_VA,"framed_gate_old_c5_fallback")

    entries = dict(bundle.entries)
    entries.update({name:a.base+offset for name,offset in a.labels.items()})
    sites = bundle.hook_sites + (
        hooks.HookSite("framed_full_entry",entry_offset,FULL_ENTRY_VA,FULL_ENTRY_OLD,
                       entries["hook_framed_full_entry"],FULL_BODY_VA,()),
        hooks.HookSite("framed_frame_gate",gate_offset,FRAME_GATE_VA,gate_old,
                       entries["hook_framed_frame_gate"],OLD_C5_VA,()),
    )
    contract = dict(profile="native_four_border_tiles_v1",physical_surface=[0,0,layout.width-1,layout.height-1],
                    terrain=list(layout.terrain.as_tuple()),full_tiles=list(layout.full_tiles),
                    ceil_tiles=list(layout.ceil_tiles),action_bar=list(layout.action_bar.as_tuple()),
                    full_entry_extra_stack_bytes=EXTRA_FULL_STACK_BYTES,
                    full_status_to_caller_before_call=FULL_STATUS_TO_CALLER_BEFORE_CALL,
                    full_entry_native_old_bytes=FULL_ENTRY_OLD.hex(),full_entry_va=FULL_ENTRY_VA,
                    full_native_body_va=FULL_BODY_VA,
                    full_entry_admitted_va=entries["framed_full_admitted"],
                    full_return_observer_va=entries["framed_full_return"],
                    unsupported_context_is_native_fallback=True,
                    smaller_world_is_rejection_not_rendered_proof=True)
    result = replace(bundle,code=a.finish(),entries=entries,relocations=tuple(a.relocations),
                     hook_sites=sites,layout_contract=contract)
    clip.absolute_relocation_offsets(result)
    return result
