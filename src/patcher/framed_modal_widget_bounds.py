"""Emit two uninstalled CMP adapters for the exact primary-text predecessor.

Only the owned native modal canvas gets the original signed x<640 bound.
Other targets retain the HD bound. Invalid owned state suppresses the draw.
No descriptor, callback, primary-text recipe, or executable is modified here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import struct

from . import framed_modal_canvas as modal
from . import partial_tile_clip as clip
from . import pe_extension as pe

REVISION = 'owned_modal_widget_bounds_v1'
SOURCE = 'src/patcher/framed_modal_widget_bounds.py'
SITES = (('single', 0x419D60, 18, 3), ('list', 0x419D80, 64, 12))
CMP_PREFIXES = tuple(bytes((0x81, 0x38 + register)) for register in (0, 1, 2, 3, 6, 7))


@dataclass(frozen=True)
class WidgetBoundsBundle(clip.AdapterBundle):
    hook_sites: tuple[pe.HookPatch, ...] = ()
    modal_state_va: int = 0
    candidate_sha256: str = ''
    source_contract: dict = field(default_factory=dict)


def _emit_guards(*, base_va, state_va, owner_va, width, height, comparisons):
    """Private instruction core; source/candidate authentication is external."""
    pe._require(all(type(n) is int for n in (base_va, state_va, owner_va, width, height)),
                'integer guard addresses and dimensions required')
    clip.FramedViewport(width, height)
    pe._require(all(0x10000 <= n < 0x7FFE0000 for n in (base_va, state_va, owner_va))
                and base_va % 4096 == state_va % 4096 == 0,
                'bounded aligned code/state and owner address required')
    pe._require(type(comparisons) is dict and set(comparisons) == {'single', 'list'},
                'exact single/list comparisons required')
    for old in comparisons.values():
        pe._require(type(old) is bytes and len(old) == 6 and old[:2] in CMP_PREFIXES
                    and old[2:] == struct.pack('<I', width), 'exact six-byte widened memory CMP required')
    a = clip._Assembler(base_va)
    for name in ('single', 'list'):
        a.label(name)
        a.emit('60a1'); a.absolute(state_va + modal.STATE['native'], 'owned native header')
        a.emit('85c0'); a.branch('0f84', name + '.hd')
        a.emit('3905'); a.absolute(modal.RENDER, 'current render target')
        a.branch('0f85', name + '.hd')
        a.emit('833d'); a.absolute(state_va + modal.STATE['phase'], 'owned canvas phase'); a.emit('01')
        a.branch('0f85', name + '.reject')
        a.emit('833d'); a.absolute(state_va + modal.STATE['fault'], 'owned canvas fault'); a.emit('00')
        a.branch('0f85', name + '.reject')
        a.emit('e8')
        a.relocations.append(clip.Relocation(len(a.code), 'rel32', owner_va, 'inherited is_active ownership validator'))
        a.u32(owner_va - base_va - len(a.code) - 4)
        a.emit('85c0'); a.branch('0f84', name + '.reject')
        a.emit('61' + comparisons[name][:2].hex()); a.u32(640); a.emit('c3')
        a.label(name + '.hd'); a.emit('61' + comparisons[name].hex() + 'c3')
        a.label(name + '.reject'); a.emit('6139c0c3')
    code = a.finish()
    pe._require(len(code) < 4096, 'widget guards exceed one code page')
    bundle = WidgetBoundsBundle(base_va, code, {name: base_va + a.labels[name] for name in ('single', 'list')},
                                tuple(a.relocations), width, height)
    clip.absolute_relocation_offsets(bundle)
    return bundle


def _verified_bundle(original, candidate, context, *, base_va, width, height):
    view = pe.inspect_pe(candidate)
    pe._require(type(base_va) is int and base_va == view.image_base + view.image_size,
                'widget code must use the next image extent')
    comparisons, spans = {}, []
    for name, start, size, displacement in SITES:
        source_offset = pe.inspect_pe(original).file_offset(start - view.image_base, size)
        offset = view.file_offset(start - view.image_base, size)
        source = original[source_offset:source_offset + size]
        old = source[displacement:displacement + 6]
        pe._require(len(old) == 6 and old[:2] in CMP_PREFIXES and old[2:] == struct.pack('<I', 640),
                    'native descriptor comparison ABI differs: ' + name)
        expected = bytearray(source)
        expected[displacement + 2:displacement + 6] = struct.pack('<I', width)
        pe._require(candidate[offset:offset + size] == bytes(expected),
                    'native descriptor dispatcher changed outside its width operand: ' + name)
        comparisons[name] = bytes(expected[displacement:displacement + 6])
        spans.append(dict(name=name, va=start, offset=offset, size=size,
                          original_sha256=pe._sha(source), predecessor_sha256=pe._sha(bytes(expected)),
                          comparison_va=start + displacement, original_cmp_hex=old.hex(),
                          predecessor_cmp_hex=comparisons[name].hex()))
    state, entries = context['modal_state_va'], context['modal_entry_vas']
    code_section = next((s for s in view.sections if s.rva <= entries['is_active'] - view.image_base < s.rva + s.memory_size), None)
    state_section = next((s for s in view.sections if s.rva <= state - view.image_base < s.rva + s.memory_size), None)
    pe._require(code_section is not None and code_section.name.rstrip(b'\0') == b'.hdmodal'
                and code_section.characteristics == pe.RX_CODE and state_section is not None
                and state_section.name.rstrip(b'\0') == b'.hdstate'
                and state_section.characteristics == 0xC0000040, 'inherited owned code/state sections differ')
    core = _emit_guards(base_va=base_va, state_va=state, owner_va=entries['is_active'],
                        width=width, height=height, comparisons=comparisons)
    hooks = []
    for span in spans:
        name, va = span['name'], span['comparison_va']
        target = core.entries[name]
        old = comparisons[name]
        hooks.append(pe.HookPatch(view.file_offset(va - view.image_base, 6), va - view.image_base, va, old,
            b'\xe8' + struct.pack('<i', target - va - 5) + b'\x90', 'modal_widget_bounds.' + name,
            (pe.CodeRelocation(1, 'rel32', target, 'context-dependent descriptor CMP'),)))
    contract = dict(predecessor_stage=context['stage'], predecessor_revision=context['recipe_revision'],
        native_spans=spans, source_hashes=dict(context['source_hashes']) | {SOURCE: pe._sha(Path(__file__).read_bytes())},
        owner_va=entries['is_active'], owner_state_offsets=dict(modal.STATE),
        policy='x<640 only for the valid owned native render target; other targets retain signed x<physical_width',
        rejection='owned target with inactive/faulted/invalid ownership returns equality flags, suppressing JL',
        abi='CALL plus NOP replaces CMP; all GPRs and ESP preserved; native signed comparison flags returned',
        owner_fault_behavior='is_active may retain its existing fault4 latch on invalid active ownership',
        unchanged=['descriptors', 'callbacks', 'availability flags', 'native branch/iteration instructions', 'primary-text predecessor'],
        runtime_executed=False, installation_ready=False, manual_input_proof=False, promotion_ready=False)
    return WidgetBoundsBundle(core.base_va, core.code, core.entries, core.relocations, width, height, False,
                              tuple(hooks), state, pe._sha(candidate), contract)


def predecessor(original, resolution):
    """Build the frozen exact text stage, never accept supplied manifest claims."""
    from tools import build_framed_modal_primary_text_candidate as builder
    from tools.modal_primary_text_context import FROZEN_TEXT_SOURCES, STAGE, REVISION as TEXT_REVISION
    root = Path(__file__).resolve().parents[2]
    pe._identity(original, pe.ORIGINAL_SHA256, 'original')
    for name, digest in FROZEN_TEXT_SOURCES.items():
        pe._identity((root / name).read_bytes(), digest, 'frozen text source ' + name)
    candidate, context, probe = builder.build_candidate(original, resolution)
    pe._require(context['stage'] == STAGE and context['recipe_revision'] == TEXT_REVISION
                and context['candidate_sha256'] == pe._sha(candidate), 'exact text predecessor identity required')
    pe._require(context['source_hashes'] == {name: pe._sha((root / name).read_bytes()) for name in context['source_hashes']},
                'predecessor source changed during construction')
    return candidate, context, probe


def emit_widget_bounds(original: bytes, candidate: bytes, *, base_va: int, width: int, height: int):
    before = pe._sha(Path(__file__).read_bytes())
    pe._require(type(width) is int and type(height) is int, 'integer widget dimensions required')
    rebuilt, context, _ = predecessor(original, f'{width}x{height}')
    pe._require(candidate == rebuilt, 'exact primary-text predecessor reconstruction required')
    result = _verified_bundle(original, candidate, context, base_va=base_va, width=width, height=height)
    pe._require(before == pe._sha(Path(__file__).read_bytes()), 'widget source changed during emission')
    return result
