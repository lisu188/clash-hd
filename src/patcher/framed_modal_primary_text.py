"""Center the barracks quantity's one native primary-only text call.

This additive recipe authenticates the complete frozen primary-v1 predecessor.
It changes only the three coordinate arguments at 00432C66, retaining the
native formatter, quantity, font, glyphs, cdecl cleanup and fallback behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import struct

from . import framed_modal_canvas as modal
from . import framed_modal_primary as primary
from . import partial_tile_clip as clip
from . import pe_extension as pe

STAGE = primary.STAGE.removesuffix('-modalprimary-validation') + '-modalprimarytext-validation'
REVISION = 'owned_modal_primary_text_v1'
TEXT_CALL = 0x432C66
TEXT_TARGET = 0x40C150
TEXT_RETURN = TEXT_CALL + 5
TEXT_FORMAT = 0x4EFC3A
TEXT_OLD = bytes.fromhex('e8e594fdff')
TEXT_LEFT, TEXT_RIGHT, TEXT_Y, TEXT_ALIGN = 545, 613, 53, 3
NATIVE_SPANS = (
    (0x432C32, 79, 'adada66ae1ed0388926fa989cac56d5b931da6d495b09816e2e978799e3ac479'),
    (TEXT_TARGET, 62, '2bd252f63a8f44dee5bacd037e14f277f551c930c7b59ed4c0062790f9a46dba'),
    (0x40BEE0, 615, '787068d6331e89ec1a8aaf02c8bbae2c3c15c209c622b5f547ee59d6e9d2532f'),
    (0x40BC00, 137, 'b33166e1bdc625988fbf8b13fbcf489572863205aadf6f2765fa6d19c34f1795'),
)


@dataclass(frozen=True)
class ModalPrimaryTextBundle(clip.AdapterBundle):
    hook_sites: tuple[pe.HookPatch, ...] = ()
    modal_state_va: int = 0
    modal_entry_vas: dict = field(default_factory=dict)
    candidate_sha256: str = ''
    source_contract: dict = field(default_factory=dict)


def emit_modal_primary_text(original: bytes, candidate: bytes, *, base_va: int,
                            width: int, height: int) -> ModalPrimaryTextBundle:
    from tools import build_framed_modal_primary_candidate as builder

    pe._identity(original, pe.ORIGINAL_SHA256, 'original')
    pe._require(type(width) is int and type(height) is int,
                'primary text geometry requires integer dimensions')
    # Cheap structural/old-byte rejection precedes the full source-bound
    # reconstruction. A successful fast check never admits a candidate.
    view = pe.inspect_pe(candidate)
    pe._require(type(base_va) is int and base_va == view.image_base + view.image_size
                and base_va % 4096 == 0 and base_va + 4096 < primary.CURSOR_USER_LIMIT,
                'primary text code requires next aligned image extent')
    pe._require(struct.unpack_from('<H', candidate, view.pe_offset + 22)[0] == 0x0182,
                'native non-large-address-aware executable characteristics required')
    for va, size, digest in NATIVE_SPANS:
        off = view.file_offset(va - view.image_base, size)
        pe._identity(candidate[off:off + size], digest, f'native primary text ABI {va:08x}')
    off = view.file_offset(TEXT_FORMAT - view.image_base, 3)
    pe._require(candidate[off:off + 3] == b'%d\0', 'native quantity format differs')
    off = view.file_offset(TEXT_CALL - view.image_base, len(TEXT_OLD))
    pe._require(candidate[off:off + len(TEXT_OLD)] == TEXT_OLD, 'primary quantity call old bytes differ')
    pe._require(not clip._original_highlow_fields(original, TEXT_CALL, len(TEXT_OLD)),
                'primary text hook overlaps original HIGHLOW')
    rebuilt, context, _ = builder.build_candidate(original, f'{width}x{height}')
    pe._require(candidate == rebuilt, 'exact primary-v1 candidate reconstruction required')
    pe._require(context['stage'] == primary.STAGE and context['recipe_revision'] == primary.REVISION,
                'exact primary-v1 stage and revision required')
    state, entries = context['modal_state_va'], context['modal_entry_vas']
    owner = context['base_candidate']['base_candidate']['predecessor']['base_candidate']
    pe._require(owner['state_va'] == state and owner['modal_entry_vas'] == entries
                and owner['modal_state_offsets'] == modal.STATE,
                'primary text inherited ownership contract differs')
    a = clip._Assembler(base_va)

    def address(value, purpose): a.absolute(value, purpose)

    def transfer(op, target, purpose):
        a.emit(op); pos = len(a.code)
        a.relocations.append(clip.Relocation(pos, 'rel32', target, purpose))
        a.u32(target - base_va - pos - 4)

    def unequal(): a.branch('0f85', 'quantity.delegate')

    def saved_equals(offset, value, *, pointer=False):
        a.emit('817c24' + bytes([offset]).hex())
        if pointer: address(value, 'exact native quantity argument')
        else: a.u32(value)
        unequal()

    a.label('quantity'); a.emit('9c60')
    a.emit('833d'); address(state + modal.STATE['fault'], 'owned canvas fault'); a.emit('00'); unequal()
    transfer('e8', entries['is_active'], 'inherited owned canvas validator')
    a.emit('85c0'); a.branch('0f84', 'quantity.delegate')
    a.emit('813d'); address(modal.RENDER, 'current native render device')
    address(modal.PRIMARY, 'native cached primary'); unequal()
    # PUSHFD/PUSHAD save 36 bytes. No incoming register or flag is changed at
    # the native callee; stack+40/44/48 are its three coordinate arguments.
    # The caller sets EBP=primary before font selection, and CALL has this one
    # exact return. Both prevent this entry becoming a general font transform.
    saved_equals(8, modal.PRIMARY, pointer=True)
    saved_equals(36, TEXT_RETURN, pointer=True)
    for offset, value in ((40, TEXT_LEFT), (44, TEXT_RIGHT), (48, TEXT_Y), (52, TEXT_ALIGN)):
        saved_equals(offset, value)
    saved_equals(56, TEXT_FORMAT, pointer=True)
    # Value is deliberately unrestricted: the original signed integer and
    # formatting remain native, including zero, negative and multi-digit values.
    # The translated fixed bounds stay inside the centered 640x480 rectangle.
    for offset, amount in ((40, (width - 640) // 2), (44, (width - 640) // 2), (48, (height - 480) // 2)):
        a.emit('814424' + bytes([offset]).hex()); a.u32(amount)
    a.label('quantity.delegate'); a.emit('619d')
    transfer('e9', TEXT_TARGET, 'native formatted text RET and caller ADD ESP,18h')
    code = a.finish()
    pe._require(0 < len(code) < 4096, 'primary text adapter exceeds planned code page')
    target = base_va + a.labels['quantity']
    hook = pe.HookPatch(off, TEXT_CALL - view.image_base, TEXT_CALL, TEXT_OLD,
                       b'\xe8' + struct.pack('<i', target - TEXT_CALL - 5), 'modal_primary_text.quantity',
                       (pe.CodeRelocation(1, 'rel32', target, 'modal_primary_text.quantity'),))
    contract = dict(
        predecessor_stage=primary.STAGE, predecessor_revision=primary.REVISION,
        source_hashes=dict(context['source_hashes'], **{
            'src/patcher/framed_modal_primary_text.py': pe._sha(Path(__file__).read_bytes())}),
        native_spans=list(NATIVE_SPANS), native_call=TEXT_CALL, native_target=TEXT_TARGET,
        native_return=TEXT_RETURN, original_args=[TEXT_LEFT, TEXT_RIGHT, TEXT_Y, TEXT_ALIGN, TEXT_FORMAT],
        coordinates='left/right x bounds and y origin; signed quantity remains unchanged',
        native_cleanup='UI_DrawTextFmt RET; original caller ADD ESP,18h consumes all six arguments',
        admitted_context='active inherited native canvas, zero fault, primary device, exact call/EBP/argument shape',
        owner_fault_behavior='inherited is_active retains its fault4 latch for invalid active ownership',
        owner_code_sha256=owner['code_sha256'], owner_state_offsets=dict(modal.STATE),
        untouched=['font selection', 'format string', 'quantity', 'glyph source', 'native render target',
                   'portrait copies', 'placeholder', 'cursor callbacks', 'primary-v1 recipe'],
        limitations=['Emitted ABI checks do not establish runtime composition or ordinary input.',
                     'Each resolution needs new candidate-bound capture and redraw evidence.'])
    bundle = ModalPrimaryTextBundle(base_va, code, {k: base_va + v for k, v in a.labels.items()},
        tuple(a.relocations), width, height, False, (hook,), state, dict(entries), pe._sha(candidate), contract)
    clip.absolute_relocation_offsets(bundle)
    return bundle
