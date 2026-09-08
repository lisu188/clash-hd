"""Uninstalled own-army integration for the exact frozen framed/modal image.

All old generators remain unchanged. Seven explicit old-byte-checked hooks
extend their lower-row admission, repaint portraits after terrain/commands,
and exclude the complete native backing from ordinary map input. The original
full loop renders its last row underneath the relocated portrait overlay.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct

from . import partial_tile_clip as clip
from . import pe_extension as pe
from . import pe_army_extension as extension
from . import framed_input as mouse
from .framed_army_viewport import FramedArmyViewport


@dataclass(frozen=True)
class ArmyCompositionBundle:
    base_va: int
    code: bytes
    entries: dict[str, int]
    relocations: tuple
    hook_sites: tuple
    removed_highlow_rvas: tuple[int, ...]
    candidate_sha256: str
    source_contract: dict


def emit_army_composition(original: bytes, candidate: bytes, *, base_va: int,
                          width: int, height: int, minimap_viewport: bool,
                          owner_state_va: int, draw_army_va: int) -> ArmyCompositionBundle:
    layout = FramedArmyViewport(width, height)
    expected, metadata, _ = extension._reconstruct_modal(original, f"{width}x{height}", minimap_viewport)
    if candidate != expected:
        raise ValueError("army composition requires exact canonical modal image")
    allocation = extension.allocation_layout(candidate, state_bytes=0)
    for va in (base_va, owner_state_va, draw_army_va):
        if type(va) is not int or not allocation.code_va <= va < allocation.code_va + allocation.code_reservation:
            raise ValueError("army helper lies outside the new RX reservation")
    old_entries = metadata['base_candidate']['entry_vas']
    image = pe.inspect_pe(candidate)
    a = clip._Assembler(base_va)
    hooks, removed, contracts = [], [], []

    def transfer(opcode, target, purpose):
        a.emit(opcode)
        offset = len(a.code)
        a.relocations.append(clip.Relocation(offset, 'rel32', target, purpose))
        a.u32(target - (base_va + offset + 4))

    def value(result):
        a.emit('c744241c'); a.u32(result); a.emit('619dc3')

    def read(va, size):
        offset = image.file_offset(va - image.image_base, size)
        return candidate[offset:offset + size]

    def install(va, old, new, purpose, relocs=()):
        if read(va, len(old)) != old or len(old) != len(new):
            raise ValueError('army old bytes/span differ: ' + purpose)
        hooks.append(pe.HookPatch(image.file_offset(va-image.image_base,len(old)),
                                  va-image.image_base,va,old,new,purpose,tuple(relocs)))
        contracts.append(dict(va=va, old_hex=old.hex(), new_hex=new.hex(), purpose=purpose))

    def jump(va, old, label, purpose):
        target = base_va + a.labels[label]
        install(va, old, b'\xe9'+struct.pack('<i',target-va-5)+b'\x90'*(len(old)-5),
                purpose,(pe.CodeRelocation(1,'rel32',target,purpose),))

    # Shared admission does not inspect a surface while the caller owns a
    # temporary clipped vtable. Every old caller retains its own surface checks.
    a.label('lower_owner_admission'); a.emit('9c60833d')
    a.absolute(clip.LOWER_ROW_OWNER_GLOBAL,'lower_row_owner'); a.emit('00')
    a.branch('0f84','lower.accept')
    transfer('e8',owner_state_va,'army_owner_state')
    a.emit('83f801'); a.branch('0f85','lower.reject')
    a.label('lower.accept'); value(1)
    a.label('lower.reject'); value(0)

    # Replace only the original MOV EDX,[lower], keeping its TEST/JZ and full
    # last-row body intact. All registers/flags except the native EDX survive.
    a.label('native_lower_row'); a.emit('9c608b15')
    a.absolute(clip.LOWER_ROW_OWNER_GLOBAL,'lower_row_owner')
    a.emit('89542414')
    transfer('e8',owner_state_va,'army_owner_state')
    a.emit('83f801'); a.branch('0f85','native_lower.return')
    a.emit('c744241400000000')
    a.label('native_lower.return'); a.emit('619dc3')
    target = base_va + a.labels['native_lower_row']
    native_old = bytes.fromhex('8b1594695200')
    install(0x418784,native_old,b'\xe8'+struct.pack('<i',target-0x418789)+b'\x90',
            'render complete terrain underneath admitted own-army overlay',
            (pe.CodeRelocation(1,'rel32',target,'army lower-row read'),))
    if read(0x41878A,8) != bytes.fromhex('85d20f841b020000'):
        raise ValueError('native last-row TEST/JZ boundary changed')
    removed.append(0x418786-image.image_base)

    # Symbolically located generated guards have fixed, machine-sized CMP/JNE
    # spans. Their original rejection destination and all later checks survive.
    specs = [('composition_guard',16),('framed_input.context_guard',16),
             ('frame_presentation.frame_presentation_admission',16),('edge',13)]
    for name, size in specs:
        entry = old_entries[name]
        prefix = bytes.fromhex('813d94695200000000000f85' if size==16 else '833d94695200000f85')
        region = read(entry, 128 if name!='edge' else 256)
        positions = [i for i in range(len(region)-size+1) if region[i:i+len(prefix)]==prefix]
        if len(positions)!=1:
            raise ValueError('unique source-owned lower-row guard missing: '+name)
        va = entry + positions[0]; old = read(va,size)
        reject = va + size + struct.unpack_from('<i',old,size-4)[0]
        helper = base_va + a.labels['lower_owner_admission']
        new = b'\xe8'+struct.pack('<i',helper-va-5)+b'\x85\xc0\x0f\x84'+struct.pack('<i',reject-va-13)
        install(va,old,new+b'\x90'*(size-13),'admit exact own-army in '+name,
                (pe.CodeRelocation(1,'rel32',helper,'army lower admission'),
                 pe.CodeRelocation(9,'rel32',reject,'preserved rejection')))
        removed.append(va+2-image.image_base)

    compose = old_entries['compose_panel']
    compose_old = bytes.fromhex('6089e583ec0c')
    if read(compose,6)!=compose_old:
        raise ValueError('compose-panel prologue differs')
    a.label('old_compose_panel'); a.emit(compose_old.hex())
    transfer('e9',compose+6,'old compose-panel body')
    a.label('compose_army_panel'); a.emit('9c6089e583ec08')
    a.branch('e8','old_compose_panel'); a.emit('83f801')
    a.branch('0f85','compose.deny')
    a.emit('833d'); a.absolute(clip.LOWER_ROW_OWNER_GLOBAL,'lower_row_owner'); a.emit('00')
    a.branch('0f84','compose.accept')
    transfer('e8',owner_state_va,'army_owner_state'); a.emit('83f801')
    a.branch('0f85','compose.deny')
    a.emit('a1'); a.absolute(clip.MAP_SURFACE_GLOBAL,'map_surface_global')
    a.emit('8945fc8b90b80000008955f8c780b8000000')
    a.absolute(clip.MEMORY_VTABLE,'memory_vtable')
    transfer('e8',draw_army_va,'draw_army')
    a.label('compose.draw_return')
    a.emit('83f8010f94c00fb6c089451c8b45fc8b55f88990b800000089ec619dc3')
    a.label('compose.accept'); a.emit('c7451c0100000089ec619dc3')
    a.label('compose.deny'); a.emit('c7451c0000000089ec619dc3')
    jump(compose,compose_old,'compose_army_panel','recompose native-size portraits after terrain and command dock')

    # The ordinary map gate remains responsible for terrain/minimap/world
    # bounds. Its new prefix excludes the entire387x66 backing while active.
    pixel = old_entries['framed_input.pixel_guard']
    pixel_old = bytes.fromhex('9c608b35e4025200')
    a.label('pixel_army_exclusion'); a.emit('9c60')
    a.emit('833d'); a.absolute(clip.LOWER_ROW_OWNER_GLOBAL,'lower_row_owner'); a.emit('00')
    a.branch('0f84','pixel.continue')
    transfer('e8',owner_state_va,'army_owner_state'); a.emit('83f801')
    a.branch('0f85','pixel.deny')
    a.emit('0fb60d'); a.absolute(mouse.MOUSE_SHIFT,'mouse_shift')
    a.emit('8b1d'); a.absolute(mouse.MOUSE_X,'mouse_x')
    a.emit('8b15'); a.absolute(mouse.MOUSE_Y,'mouse_y')
    a.emit('d3fbd3fa')
    for opcode,limit,branch in (('81fb',layout.backing.left,'0f8c'),
                               ('81fb',layout.backing.right,'0f8f'),
                               ('81fa',layout.backing.top,'0f8c'),
                               ('81fa',layout.backing.bottom,'0f8f')):
        a.emit(opcode); a.u32(limit); a.branch(branch,'pixel.continue')
    a.label('pixel.deny'); value(0)
    a.label('pixel.continue'); a.emit('619d9c608b35')
    a.absolute(clip.GAME_DATA_GLOBAL,'game_data_global')
    transfer('e9',pixel+8,'old framed pixel guard body')
    jump(pixel,pixel_old,'pixel_army_exclusion','exclude full army backing from ordinary map input')
    removed.append(pixel+4-image.image_base)

    code = a.finish()
    if base_va + len(code) > allocation.code_va + allocation.code_reservation:
        raise ValueError('army composition exceeds new RX reservation')
    return ArmyCompositionBundle(base_va,code,{k:base_va+v for k,v in a.labels.items()},
        tuple(a.relocations),tuple(hooks),tuple(removed),hashlib.sha256(candidate).hexdigest(),
        dict(profile='framed_own_army_composition_v1',hooks=contracts,
             native_last_row_read_va=0x418784, backing=layout.backing.as_tuple(),
             hit=layout.hit.as_tuple(),original_generators_unchanged=True,
             unsupported_owner_is_original_fallback=True,runtime_executed=False))
