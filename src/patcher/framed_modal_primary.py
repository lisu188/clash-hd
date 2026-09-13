"""Emit uninstalled primary-composition hooks above the exact slots candidate.

The original full-blit boundary publishes the owned, centered physical mirror.
Barracks primary-only placeholder and cursor bounds use physical coordinates;
the selected panel keeps native drawing and translates only its dirty copy.
No existing builder, stage, executable or runtime evidence is changed here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import struct

from . import framed_modal_canvas as modal
from . import framed_modal_slots as slots
from . import partial_tile_clip as clip
from . import pe_extension as pe

STAGE = slots.STAGE.removesuffix('-modalslots-validation') + '-modalprimary-validation'
REVISION = 'owned_modal_primary_v1'
FULL_BLIT = 0x401E30
HD_BLIT = 0x4E9920
PANEL_COPY = 0x433273
PLACEHOLDER = 0x432F94
CURSOR_RECTS = (0x432F5C, 0x4331D5)
CURSOR_RECT = 0x460BB0
CURSOR_REMOVE = 0x460F90
CURSOR_DRAW = 0x460EA0
CURSOR_STATE = 0x544CD8
CURSOR_VISIBLE = 0x544D10
CURSOR_DESCRIPTORS = tuple(0x519678 + 40 * index for index in range(18))
CURSOR_STARTUP_DESCRIPTOR = 0x545158
CURSOR_USER_LIMIT = 0x7FFE0000
CURSOR_CONTEXT_SPANS = (
    (0x460490, 232, 'fa888ccf02806b2a1c6f0a3b2dda3c7a1af660c62e40ff01bd23c61a7db85e6d'),
    (0x460D80, 283, 'fad4f9c8f9b8f479f79c08f64dfb0e5232dd9dbf98102953285706740e45673b'),
    (0x405EC0, 4, '198e92a89d43b3007ccc06467366a4221d39cf40d9c1feb16bb6c26efd077bf5'),
)
PANEL_X, PANEL_Y = 220, 289
NATIVE_SPANS = (
    (0x432ED0, 2032, '0aef30246bf922c0d6a60d44d227d11611128e6d43bdede53acfe9827c123b56'),
    (0x4024E0, 867, '29c70320d733412798da7d41c77f2ab310987ad58dfef89a88f3459cfcd350a8'),
    (CURSOR_RECT, 82, '1c8d3c05eca8a041549163a5b2dfd8219c59a5495bf59e3ba4dbf00fec10179e'),
    (CURSOR_REMOVE, 119, '808876643b180ccb733f829def04bda8d34cee6075f60dcd2c0cdb33376bcfd3'),
    (CURSOR_DRAW, 229, 'a8d1befe8bf0815c566d9cb272e9efad2d73c1ade9ad5b004f91eb3578a037f9'),
)


@dataclass(frozen=True)
class ModalPrimaryBundle(clip.AdapterBundle):
    hook_sites: tuple[pe.HookPatch, ...] = ()
    modal_state_va: int = 0
    modal_entry_vas: dict = field(default_factory=dict)
    candidate_sha256: str = ''
    source_contract: dict = field(default_factory=dict)


def emit_modal_primary(original: bytes, candidate: bytes, *, base_va: int,
                       width: int, height: int) -> ModalPrimaryBundle:
    from tools import build_framed_modal_slots_candidate as builder

    pe._identity(original, pe.ORIGINAL_SHA256, 'original')
    rebuilt, context, _ = builder.build_candidate(original, f'{width}x{height}')
    pe._require(candidate == rebuilt, 'exact slots candidate reconstruction required')
    pe._require(context['recipe_revision'] == slots.REVISION, 'exact slots revision required')
    view = pe.inspect_pe(candidate)
    pe._require(struct.unpack_from('<H', candidate, view.pe_offset + 22)[0] == 0x0182,
                'native non-large-address-aware executable characteristics required')
    pe._require(type(base_va) is int and base_va == view.image_base + view.image_size
                and base_va % 4096 == 0 and base_va + 4096 < 0x7FFE0000,
                'primary code requires next aligned image extent')
    for va, size, digest in NATIVE_SPANS:
        off = view.file_offset(va - view.image_base, size)
        pe._identity(candidate[off:off + size], digest, f'native primary ABI {va:08x}')
    original_view = pe.inspect_pe(original)
    for va, size, digest in CURSOR_CONTEXT_SPANS:
        off = original_view.file_offset(va - original_view.image_base, size)
        pe._identity(original[off:off + size], digest, f'native cursor initialization {va:08x}')
    descriptor_prefixes = {}
    for va in CURSOR_DESCRIPTORS:
        off = original_view.file_offset(va - original_view.image_base, 12)
        prefix = original[off:off + 12]
        installed = view.file_offset(va - view.image_base, 12)
        pe._require(candidate[installed:installed + 12] == prefix,
                    'native cursor descriptor prefix changed')
        descriptor_prefixes[va] = struct.unpack('<3I', prefix)
    # The original initializer also selects its zero-initialized BSS descriptor.
    # It has 36 used bytes, not a 40-byte record: the next DWORD is input state.
    descriptor_prefixes[CURSOR_STARTUP_DESCRIPTOR] = (0, 0, 0)
    owner = context['base_candidate']['predecessor']['base_candidate']
    state = owner['state_va']
    entries = owner['modal_entry_vas']
    pe._require(owner['modal_state_offsets'] == modal.STATE, 'modal state layout differs')
    expected_full = b'\xe9' + struct.pack('<i', entries['full_blit'] - FULL_BLIT - 5)
    sites = ((FULL_BLIT, expected_full, 'full_blit', 'e9'),
             (PLACEHOLDER, bytes.fromhex('b921010000bbdc000000'), 'placeholder', 'e9'),
             (CURSOR_RECTS[0], bytes.fromhex('e84fdc0200'), 'cursor_rect', 'e8'),
             (CURSOR_RECTS[1], bytes.fromhex('e8d6d90200'), 'cursor_rect', 'e8'),
             (PANEL_COPY, bytes.fromhex('e868f2fcff'), 'panel_copy', 'e8'))
    for va, old, _, _ in sites:
        off = view.file_offset(va - view.image_base, len(old))
        pe._require(candidate[off:off + len(old)] == old, f'primary old bytes differ at {va:08x}')
        pe._require(not clip._original_highlow_fields(original, va, len(old)),
                    'primary hook overlaps original HIGHLOW')
    a = clip._Assembler(base_va)
    dx, dy = (width - 640) // 2, (height - 480) // 2

    def transfer(op, target, purpose):
        a.emit(op); pos = len(a.code)
        a.relocations.append(clip.Relocation(pos, 'rel32', target, purpose))
        a.u32(target - base_va - pos - 4)

    def address(target, purpose): a.absolute(target, purpose)
    def st(name): address(state + modal.STATE[name], 'modal state.' + name)
    def reject_if(op, label): a.branch(op, label)

    def admitted(fallback):
        # The frozen ownership helper deliberately exposes sticky faults.
        a.emit('833d'); st('fault'); a.emit('00'); reject_if('0f85', fallback)
        transfer('e8', entries['is_active'], 'owned canvas validator')
        a.emit('85c0'); reject_if('0f84', fallback)

    def saved_equals(offset, value, fallback, absolute=False):
        a.emit('817c24' + bytes([offset]).hex())
        if absolute: address(value, 'exact native argument')
        else: a.u32(value)
        reject_if('0f85', fallback)

    def range32(offset, low, high, fallback):
        # Unsigned bounds also reject negative values and nonzero high words.
        a.emit('817c24' + bytes([offset]).hex()); a.u32(low); reject_if('0f82', fallback)
        a.emit('817c24' + bytes([offset]).hex()); a.u32(high); reject_if('0f87', fallback)

    def add_saved(offset, amount):
        a.emit('814424' + bytes([offset]).hex()); a.u32(amount)

    def register_range(reg, low, high, fallback):
        a.emit('81' + bytes([0xF8 + reg]).hex()); a.u32(low); reject_if('0f82', fallback)
        a.emit('81' + bytes([0xF8 + reg]).hex()); a.u32(high); reject_if('0f87', fallback)

    def pointer_range(reg, size, fallback):
        # This exact non-LAA target cannot own kernel-half heap pointers.
        # The bound proves user-range arithmetic, not allocation lifetime.
        register_range(reg, 0x10000, CURSOR_USER_LIMIT - size, fallback)

    def disjoint(reg, size, other, other_size, fallback, label):
        # EAX/EDX are scratch; both ranges must be nonwrapping. Other is ECX
        # or a retained pointer register, never either scratch register.
        a.emit('89' + bytes([0xC0 + reg * 8]).hex() + '05'); a.u32(size)
        reject_if('0f82', fallback)
        a.emit('89' + bytes([0xC2 + other * 8]).hex() + '81c2'); a.u32(other_size)
        reject_if('0f82', fallback)
        a.emit('39' + bytes([0xD0 + reg]).hex()); a.branch('0f83', label)
        a.emit('39' + bytes([0xC0 + other * 8]).hex()); a.branch('0f86', label)
        a.branch('e9', fallback); a.label(label)

    def cursor_context(fallback):
        # Called only for a displayed cursor, before the mirror or new native
        # callbacks. Keep the native descriptor, backing surface, and resource
        # pointers; do not manufacture replacement cursor state.
        a.emit('8b35'); address(CURSOR_STATE + 0x3C, 'native cursor descriptor')
        for index, va in enumerate(descriptor_prefixes):
            a.emit('81fe'); address(va, 'native static cursor descriptor')
            a.branch('0f84', f'cursor.descriptor.{index}')
        a.branch('e9', fallback)
        for index, prefix in enumerate(descriptor_prefixes.values()):
            a.label(f'cursor.descriptor.{index}')
            for offset, value in zip((0, 4, 8), prefix):
                a.emit('817e' + bytes([offset]).hex()); a.u32(value)
                reject_if('0f85', fallback)
            a.branch('e9', 'cursor.descriptor.valid')
        a.label('cursor.descriptor.valid')
        # Descriptor dimensions are computed by native SelectCursorDescriptor
        # across its sprite range. The allocated native backing is 64 x 64.
        a.emit('8b4e0c8b6e10')
        register_range(1, 1, 64, fallback); register_range(5, 1, 64, fallback)
        a.emit('8b56208b46042b0639c2'); reject_if('0f87', fallback)
        a.emit('03168b1d'); address(CURSOR_STATE + 0x40, 'native loaded cursor sprite set')
        pointer_range(3, 0x1010, fallback)
        a.emit('0fb78304100000')
        register_range(0, 1, 1024, fallback)
        a.emit('39c2'); reject_if('0f83', fallback)
        a.emit('8b3c93'); pointer_range(7, 4, fallback)
        # Sprite WORD+0 is pixel width, WORD+2 height; the native DLX helper
        # names are reversed. Present uses the descriptor's maximum extents.
        a.emit('0fb70783f801'); reject_if('0f82', fallback)
        a.emit('39c8'); reject_if('0f87', fallback)
        a.emit('0fb7470283f801'); reject_if('0f82', fallback)
        a.emit('39e8'); reject_if('0f87', fallback)
        a.emit('89fe8b2d'); address(CURSOR_STATE + 8, 'native cursor backing surface')
        pointer_range(5, 188, fallback)
        a.emit('817d0040004000'); reject_if('0f85', fallback)
        a.emit('81bdb8000000'); address(modal.MEMORY_VTABLE, 'native cursor memory vtable')
        reject_if('0f85', fallback)
        a.emit('8b7d04'); pointer_range(7, 4096, fallback)
        # Mirroring must not overwrite cursor metadata, its backing, or the
        # selected sprite header before the native callbacks consume them.
        # EBP=backing header, EDI=backing pixels, EBX=resource, ESI=sprite.
        for reg, size, name in ((5, 188, 'header'), (7, 4096, 'pixels'),
                                (3, 0x1010, 'resource'), (6, 4, 'sprite')):
            for field, extent in (('native', 188), ('physical', 188),
                                  ('native_pixels', 640 * 480), ('physical_pixels', width * height)):
                a.emit('8b0d'); st(field)
                disjoint(reg, size, 1, extent, fallback, f'cursor.disjoint.{name}.{field}')
        for other, extent, name in ((5, 188, 'header'), (3, 0x1010, 'resource'), (6, 4, 'sprite')):
            disjoint(7, 4096, other, extent, fallback, 'cursor.backing.disjoint.' + name)

    def publish():
        # Old helper preserves all GPRs, including the argument it receives.
        # Keep original EAX and retain the helper's actual returned flags.
        a.emit('619d50a1'); st('physical')
        transfer('e8', HD_BLIT, 'original HD blitter on physical mirror')
        a.emit('58')

    a.label('full_blit'); a.emit('9c60')
    a.emit('a1'); st('native'); a.emit('3b44241c'); reject_if('0f85', 'full.fallback')
    admitted('full.fallback')
    a.emit('833d'); address(CURSOR_VISIBLE, 'native cursor overlay state'); a.emit('01')
    reject_if('0f87', 'full.fallback')
    a.branch('0f85', 'full.cursor.context.valid')
    cursor_context('full.fallback')
    a.label('full.cursor.context.valid')
    transfer('e8', entries['mirror'], 'owned native to centered physical mirror')
    a.emit('83f801'); reject_if('0f85', 'full.fallback')
    a.emit('833d'); address(CURSOR_VISIBLE, 'native cursor overlay state'); a.emit('00')
    a.branch('0f85', 'full.cursor')
    publish(); a.emit('c3')
    a.label('full.cursor')
    # Remove OLD cursor backing before replacing primary pixels. Re-present
    # afterwards captures NEW backing. Neither cursor globals nor input state
    # are assigned by this adapter; the original routines own that lifecycle.
    a.emit('b8'); address(CURSOR_STATE, 'native cursor render state')
    transfer('e8', CURSOR_REMOVE, 'native cursor remove before full copy')
    publish()
    a.emit('9c60b8'); address(CURSOR_STATE, 'native cursor render state')
    transfer('e8', CURSOR_DRAW, 'native cursor capture and redraw after full copy')
    a.emit('619dc3')
    a.label('full.fallback'); a.emit('619d')
    transfer('e9', entries['full_blit'], 'unchanged inherited full-blit fallback')

    a.label('placeholder')
    a.emit('b921010000bbdc0000009c60')  # replay both displaced native MOVs
    admitted('placeholder.done')
    saved_equals(28, modal.PRIMARY, 'placeholder.done', absolute=True)
    saved_equals(4, modal.PRIMARY_VTABLE, 'placeholder.done', absolute=True)
    add_saved(16, dx); add_saved(24, dy)
    a.label('placeholder.done'); a.emit('619d')
    transfer('e9', PLACEHOLDER + 10, 'original primary sprite call and seven stack operands')

    a.label('cursor_rect'); a.emit('9c60')
    admitted('cursor.done')
    saved_equals(28, CURSOR_STATE, 'cursor.done', absolute=True)
    saved_equals(20, PANEL_X, 'cursor.done')  # EDX: native minimum x
    saved_equals(16, PANEL_Y, 'cursor.done')  # EBX: native minimum y
    range32(24, PANEL_X, 639, 'cursor.done')  # ECX: maximum x
    range32(40, PANEL_Y, 479, 'cursor.done')  # single stack maximum y
    add_saved(20, dx); add_saved(24, dx)
    add_saved(16, dy); add_saved(40, dy)
    a.label('cursor.done'); a.emit('619d')
    transfer('e9', CURSOR_RECT, 'native cursor rectangle keeps RET 4 and callback ordering')

    a.label('panel_copy'); a.emit('9c60')
    admitted('panel.done')
    a.emit('a1'); st('native'); a.emit('3b44241c'); reject_if('0f85', 'panel.done')
    saved_equals(20, modal.PRIMARY, 'panel.done', absolute=True)
    for off, value in ((16, PANEL_X), (24, PANEL_Y), (48, PANEL_X), (52, PANEL_Y)):
        saved_equals(off, value, 'panel.done')
    range32(40, PANEL_X, 639, 'panel.done')
    range32(44, PANEL_Y, 479, 'panel.done')
    # All readable/disjoint buffers and their separate strides were checked
    # by the inherited ownership validator. Copy only this inclusive dirty
    # rectangle; never replace later primary-only layers with a full mirror.
    a.emit('8b4424282b4424104089c38b6c242c2b6c241845')
    a.emit('8b35'); st('native_pixels')
    a.emit('8b44241869c0800200000344241001c6')
    a.emit('8b3d'); st('physical_pixels')
    a.emit('8b44241869c0'); a.u32(width)
    a.emit('0344241005'); a.u32(dy * width + dx); a.emit('01c7fc')
    a.label('panel.row'); a.emit('89d9f3a481c68002000029de81c7'); a.u32(width)
    a.emit('29df4d'); a.branch('0f85', 'panel.row')
    add_saved(48, dx); add_saved(52, dy)
    a.label('panel.done'); a.emit('619d')
    transfer('e9', slots.NATIVE_BLIT, 'native selected-panel partial blit keeps RET 16')
    code = a.finish()
    pe._require(0 < len(code) < 4096, 'primary adapter exceeds planned code page')
    hooks = []
    for va, old, entry, op in sites:
        target = base_va + a.labels[entry]
        new = bytes.fromhex(op) + struct.pack('<i', target - va - 5) + b'\x90' * (len(old) - 5)
        hooks.append(pe.HookPatch(view.file_offset(va - view.image_base, len(old)), va - view.image_base,
            va, old, new, 'modal_primary.' + entry,
            (pe.CodeRelocation(1, 'rel32', target, 'modal_primary.' + entry),)))
    hd_off = view.file_offset(HD_BLIT - view.image_base, 96)
    result = ModalPrimaryBundle(base_va, code, {k: base_va + v for k, v in a.labels.items()},
        tuple(a.relocations), width, height, False, tuple(hooks), state, dict(entries),
        pe._sha(candidate), dict(stage=STAGE, revision=REVISION,
            predecessor_stage=slots.STAGE, predecessor_revision=slots.REVISION,
            source_hashes=dict(context['source_hashes'], **{
                'src/patcher/framed_modal_primary.py': pe._sha(Path(__file__).read_bytes())}),
            native_spans=list(NATIVE_SPANS), cursor_context_spans=list(CURSOR_CONTEXT_SPANS),
            cursor_descriptor_prefixes={f'{va:08x}': list(prefix) for va, prefix in descriptor_prefixes.items()},
            cursor_backing_size=[64, 64], cursor_resource_capacity=1024,
            cursor_user_address_limit=CURSOR_USER_LIMIT,
            cursor_context_assumptions=[
                'The original initializer owns the backing surface and loaded DLX allocations; this adapter records no allocation receipt.',
                'Bounded nonnull pointers, exact backing layout, disjoint ranges and the current sprite header do not prove heap lifetime or encoded sprite payload ownership.',
                'Native Remove/Present retain cursor coordinates, clipping, palette/resource mode and sprite payload interpretation; no input polling or cursor globals are assigned by the adapter.',
                'The startup BSS descriptor is admitted through its original zero prefix and native initialization contract; its use during an active modal has no runtime proof here.'],
            hd_blit_sha256=pe._sha(candidate[hd_off:hd_off + 96]),
            centered_origin=[dx, dy], panel_origin=[PANEL_X, PANEL_Y], new_state_bytes=0,
            requires_new_rx_allocation=True, requires_new_stage_probe=True,
            runtime_executed=False, primary_composition_proven=False,
            manual_input_proof=False, promotion_ready=False))
    clip.absolute_relocation_offsets(result)
    return result
