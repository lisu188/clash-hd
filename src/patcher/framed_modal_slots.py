"""Uninstalled barracks dirty-slot adapter above the exact complete-HD v1 image.

Only CALL 00432C0B is replaced. This is neither a generic partial-blit hook nor
a new complete recipe. The existing ownership validator authenticates every
pointer before the adapter copies the inclusive 33x65 native dirty rectangle.
Only this call's primary destination is translated; source and native ABI stay
unchanged. Allocation/installation and a bound runtime probe remain separate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import struct

from . import complete_hd_candidate as complete
from . import framed_modal_canvas as modal
from . import partial_tile_clip as clip
from . import pe_extension as pe

STAGE = complete.STAGE.removesuffix('-completehd-validation') + '-completehd-modalslots-validation'
REVISION = 'owned_barracks_dirty_slots_v1'
SITE = 0x432C0B
NATIVE_BLIT = 0x4024E0
EXPECTED_CALL = bytes.fromhex('e8d0f8fcff')
XS = (126, 197, 268, 339, 410, 481)
YS = (75, 206)


@dataclass(frozen=True)
class ModalSlotsBundle(clip.AdapterBundle):
    hook_sites: tuple[pe.HookPatch, ...] = ()
    modal_state_va: int = 0
    modal_active_va: int = 0
    candidate_sha256: str = ''
    source_contract: dict = field(default_factory=dict)


def emit_modal_slots(original: bytes, candidate: bytes, *, base_va: int,
                     width: int, height: int) -> ModalSlotsBundle:
    """Authenticate v1, then emit bytes only at the next aligned image extent.

    Entry has native register arguments EAX=source, EDX=destination, EBX=x,
    ECX=y and stack [return, right, bottom, dest_x, dest_y]. Native 4024E0
    consumes the four stack arguments. Tail delegation preserves its return,
    register clobbers and flags exactly; our extra work preserves incoming
    GPRs/flags. Inactive, failed ownership, latched fault or unexpected arguments
    delegate unchanged, without a copy or destination translation.
    """
    pe._identity(original, pe.ORIGINAL_SHA256, 'original')
    rebuilt, context, _ = complete.build_candidate(original, f'{width}x{height}')
    pe._require(candidate == rebuilt, 'exact complete-HD v1 candidate reconstruction required')
    pe._require(context['recipe_revision'] == 'complete_hd_v1', 'explicit v1 predecessor required')
    view = pe.inspect_pe(candidate)
    pe._require(type(base_va) is int and base_va == view.image_base + view.image_size
                and base_va % 4096 == 0 and base_va + 4096 < 0x7FFE0000,
                'uninstalled slot code requires next aligned image extent')
    offset = view.file_offset(SITE - view.image_base, len(EXPECTED_CALL))
    pe._require(candidate[offset:offset + 5] == EXPECTED_CALL, 'barracks slot call old bytes differ')
    # This caller supplies the precise slot rectangle. Bind the full native
    # producer as well as the call; matching five bytes alone is insufficient.
    for va, length, digest in (
        (0x432940, 1006, '902659a45a8deaaa964920344e24023670f60424778d9a468006e9ab05f469ae'),
        (0x4024E0, 867, '29c70320d733412798da7d41c77f2ab310987ad58dfef89a88f3459cfcd350a8'),
    ):
        pos = view.file_offset(va - view.image_base, length)
        pe._identity(candidate[pos:pos + length], digest, f'native slot ABI {va:08x}')
    pe._require(not clip._original_highlow_fields(original, SITE, 5), 'slot call overlaps old HIGHLOW')
    owner = context['predecessor']['base_candidate']
    state = owner['state_va']
    active = owner['modal_entry_vas']['is_active']
    pe._require(owner['modal_state_offsets'] == modal.STATE, 'owned canvas state layout differs')
    a = clip._Assembler(base_va)

    def transfer(opcode, va, purpose):
        a.emit(opcode)
        a.relocations.append(clip.Relocation(len(a.code), 'rel32', va, purpose))
        a.u32(va - base_va - len(a.code) - 4)

    def state_address(name):
        a.absolute(state + modal.STATE[name], 'owned modal state.' + name)

    a.label('slot_blit')
    a.emit('9c60')
    # Keep a prior lifecycle/ownership failure sticky, even though the frozen
    # is_active helper intentionally allows its caller to inspect that state.
    a.emit('833d'); state_address('fault'); a.emit('00'); a.branch('0f85', 'fallback')
    transfer('e8', active, 'authenticated modal ownership validator')
    a.emit('85c0'); a.branch('0f84', 'fallback')
    a.emit('a1'); state_address('native')
    a.emit('3b44241c'); a.branch('0f85', 'fallback')
    a.emit('837c241400'); a.branch('0f85', 'fallback')  # exact primary sentinel
    a.emit('8b442410')  # saved source x
    for x in XS:
        a.emit('3d'); a.u32(x); a.branch('0f84', 'x_ok')
    a.branch('e9', 'fallback')
    a.label('x_ok')
    a.emit('8b4c241881f94b000000'); a.branch('0f84', 'y_ok')
    a.emit('81f9ce000000'); a.branch('0f85', 'fallback')
    a.label('y_ok')
    a.emit('3b442430'); a.branch('0f85', 'fallback')
    a.emit('3b4c2434'); a.branch('0f85', 'fallback')
    a.emit('8d50203b542428'); a.branch('0f85', 'fallback')
    a.emit('8d51403b54242c'); a.branch('0f85', 'fallback')
    # is_active checked object identity, dimensions, stride, pixel pointers,
    # nonwrapping allocation extents, disjoint buffers and owner OS thread.
    a.emit('8b35'); state_address('native_pixels')
    a.emit('69d18002000001c201d6')  # source y*640 + x
    a.emit('8b3d'); state_address('physical_pixels')
    a.emit('69d1'); a.u32(width)
    a.emit('01c201d781c7'); a.u32(((height - 480) // 2) * width + (width - 640) // 2)
    a.emit('ba41000000fc')
    a.label('copy_row')
    a.emit('b921000000f3a481c65f02000081c7'); a.u32(width - 33)
    a.emit('4a'); a.branch('0f85', 'copy_row')
    a.label('after_dirty_copy')
    # Stack operands belong to this native call and are consumed by RET 16.
    # No primary text/cursor pixels are recopied or cleared by this adapter.
    a.emit('81442430'); a.u32((width - 640) // 2)
    a.emit('81442434'); a.u32((height - 480) // 2)
    a.label('fallback')
    a.emit('619d')
    transfer('e9', NATIVE_BLIT, 'native partial blit preserves return and callee clobbers')
    code = a.finish()
    pe._require(0 < len(code) < 4096, 'slot code exceeds planned page')
    hook = pe.HookPatch(offset, SITE - view.image_base, SITE, EXPECTED_CALL,
                        b'\xe8' + struct.pack('<i', base_va - SITE - 5),
                        'modal_slots.barracks_dirty_copy',
                        (pe.CodeRelocation(1, 'rel32', base_va, 'modal_slots.slot_blit'),))
    result = ModalSlotsBundle(base_va, code, {k: base_va + v for k, v in a.labels.items()},
        tuple(a.relocations), width, height, False, (hook,), state, active,
        hashlib.sha256(candidate).hexdigest(), dict(stage=STAGE, revision=REVISION,
            predecessor_stage=context['stage'], predecessor_revision=context['recipe_revision'],
            source_hashes=context['source_hashes'], slot_x=list(XS), slot_y=list(YS),
            inclusive_copy_size=[33, 65], observed_missing_art_size=[32, 64],
            modal_state_bytes=owner['state_bytes'], new_state_bytes=0,
            requires_new_rx_allocation=True, requires_new_stage_probe=True,
            runtime_executed=False, primary_composition_proven=False,
            manual_input_proof=False, promotion_ready=False))
    clip.absolute_relocation_offsets(result)
    return result
