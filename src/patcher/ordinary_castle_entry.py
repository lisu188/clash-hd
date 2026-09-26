"""Add one authenticated native-caller admission path to the exact 1024 parent.

Only a six-byte branch and unused RX padding change. The original comparison,
remaining admission checks, allocation/lifecycle code and relocation inventory
stay intact. This is validation-only source work, not runtime or input proof.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct

from . import native_present_bounds as parent_builder
from . import pe_extension as pe

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'src/patcher/ordinary_castle_entry.py'
RESOLUTION = '1024x768'
PARENT_SHA256 = '23c766f439f3f871b6a2b992f22f2efa45b51373b9629cede5235596c519d743'
PARENT_STAGE = ('gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-'
                'presentbounds-minimapright-dynvswitch-completehd-modalwidgets-nativepresent-validation')
STAGE = PARENT_STAGE.removesuffix('-validation') + '-ordinarycastleentry-validation'
REVISION = 'owned_ordinary_castle_entry_v1'
HOOK = 0x576075
OLD_BRANCH = bytes.fromhex('0f85b5010000')
ACCEPT, REJECT = 0x57607B, 0x576230
GATE, GATE_BYTES = 0x647B74, 96
STATE = 0x596000
TRY_ENTER, ROOT_WRAPPER, WRAPPER_RETURN = 0x576000, 0x57679E, 0x5767A9
NATIVE_CALLER, NATIVE_RETURN = 0x41ED6A, 0x41ED6F
# Original-backed caller contract; the full original SHA binds everything else.
CALLER_START, CALLER_SIZE = 0x41ED28, 0x72
ROOT_BYTES = bytes.fromhex('9c608d442424e857f8ffff619d5351525657e9d0b9eaff')
OWNER_CMP = bytes.fromhex('813dd899510040ad4000')
LIMITS = [
    'Validation-only 1024x768 successor; protected stable and all predecessor recipes are unchanged.',
    'Admits the authenticated native Building_GetInto call frame; no owner or canvas state is forced.',
    'Source and synthetic CPU fixtures do not prove campaign mouse input, rendering, exit lifecycle or promotion.',
    'The emitted debugger file authenticates targeted loaded spans only, not a full runtime route.',
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def emit_gate(code_va: int = GATE) -> tuple[bytes, list[dict]]:
    """Preserve comparison flags/registers, using only relative code addresses.

    On entry ESP=R-76. PUSHFD/PUSHAD establish S=R-112. The nested saved
    ESI/EBX and try_enter return are at S+28h/34h/48h; the root is S+70h.
    CALL-next/POP obtains a relocated image address without an absolute field.
    """
    pe._require(type(code_va) is int and 0x10000 <= code_va < 0x7FFE0000-GATE_BYTES,
                'bounded gate address required')
    code = bytearray()
    labels, short, operands = {}, [], []
    def emit(value): code.extend(bytes.fromhex(value))
    def branch(op, label):
        emit(op); short.append((len(code), label)); code.append(0)
    def displacement(target, purpose):
        operands.append(dict(offset=len(code), kind='eip_relative_disp32',
                             anchor=code_va+9, target=target, purpose=purpose))
        code.extend(struct.pack('<i', target-(code_va+9)))
    def relative(op, target, purpose):
        emit(op)
        operands.append(dict(offset=len(code), kind='rel32', target=target, purpose=purpose))
        code.extend(struct.pack('<i', target-code_va-len(code)-4))
    branch('74', 'accepted')  # Keep the original ordinary-map ZF path.
    emit('9c60')
    relative('e8', code_va+9, 'local EIP anchor')
    emit('5f')
    emit('8d8f'); displacement(0x4617A0, 'native default renderer')
    emit('398f'); displacement(0x5199D8, 'live render owner')
    branch('75', 'reject')
    emit('8d8f'); displacement(0x40AD40, 'saved ordinary map owner')
    emit('394c2434'); branch('75', 'reject')
    emit('8d8f'); displacement(0x4617A0, 'saved native caller ESI')
    emit('394c2428'); branch('75', 'reject')
    emit('8d8f'); displacement(WRAPPER_RETURN, 'inherited try_enter caller')
    emit('394c2448'); branch('75', 'reject')
    emit('8b44241c8d4c247039c8'); branch('75', 'reject')
    emit('8d87'); displacement(NATIVE_RETURN, 'native Building_GetInto return')
    emit('3901'); branch('75', 'reject')
    emit('619d')
    labels['accepted'] = len(code)
    relative('e9', ACCEPT, 'remaining original admission checks')
    labels['reject'] = len(code)
    emit('619d')
    relative('e9', REJECT, 'original rejection')
    for offset, label in short:
        delta = labels[label]-offset-1
        pe._require(-128 <= delta <= 127, 'short branch range exceeded')
        code[offset] = delta & 255
    pe._require(len(code) == GATE_BYTES and code[4:10] == bytes.fromhex('e8000000005f'),
                'gate instruction layout differs')
    return bytes(code), operands


def _read(image, va, size):
    view = pe.inspect_pe(image)
    offset = view.file_offset(va-view.image_base, size)
    return image[offset:offset+size]


def _layout(candidate):
    """Check the exact final section and unused directory-free padding."""
    view = pe.inspect_pe(candidate)
    pe._require(len(view.sections) == 16 and view.headers_size == 0x400
                and (view.section_alignment, view.file_alignment) == (4096, 512),
                'exact sixteen-section predecessor layout required')
    section = view.sections[-1]
    pe._require((section.name.rstrip(b'\0'), section.header_offset, section.rva,
                 section.raw_size, section.raw_offset, section.virtual_size, section.characteristics)
                == (b'.hdpblit', 0x3C0, 0x237000, 68608, 1734656, 69632, pe.RX_CODE),
                'exact final RX section required')
    pe._require(section.raw_offset+section.raw_size == len(candidate), 'overlay or raw extent differs')
    end = view.image_base+view.relocation_rva+view.relocation_size
    pe._require(end == GATE and GATE+GATE_BYTES <= view.image_base+section.rva+section.raw_size,
                'gate must fit after the complete active relocation directory')
    for index in range(16):
        address, size = struct.unpack_from('<II', candidate, view.optional_offset+96+index*8)
        if not size: continue
        # Security directory uses a file offset; this exact parent has none.
        pe._require(index != 4, 'security directory is not supported')
        pe._require(address+size <= GATE-view.image_base or
                    address >= GATE-view.image_base+GATE_BYTES,
                    'gate overlaps a PE data directory')
    pe._require(_read(candidate, GATE, GATE_BYTES) == bytes(GATE_BYTES),
                'gate padding is not zero')
    _, fields = pe._old_relocations(candidate, view)
    pe._require(all(field+4 <= GATE-view.image_base or field >= GATE-view.image_base+GATE_BYTES
                    for field in fields), 'gate overlaps a historical relocation')
    return view, fields


def _checked_edit(candidate, va, expected, replacement, purpose):
    pe._require(type(expected) is bytes and type(replacement) is bytes
                and len(expected) == len(replacement) > 0, 'fixed nonempty edit required')
    view = pe.inspect_pe(candidate)
    offset = view.file_offset(va-view.image_base, len(expected))
    pe._require(candidate[offset:offset+len(expected)] == expected, f'old bytes differ: {purpose}')
    return pe.ByteEdit(offset, va-view.image_base, va, expected, replacement, purpose)


def _probe(image, spans):
    lines = ['.echo ORDINARY_CASTLE_SCOPE targeted_loaded_bytes_only no_runtime_route', 'r @$t19=0']
    completed = 0
    for va, size in spans:
        data = _read(image, va, size)
        clauses = [f'(by({va+i:08x}) != {value:x})' for i, value in enumerate(data)]
        for start in range(0, len(clauses), 60):
            # A CDB expression/read error may abandon this line and continue
            # the file. Only the successful ordered .else advances completion.
            lines.append('.if ('+' | '.join(clauses[start:start+60])+
                ') { .echo ORDINARY_CASTLE_CONTRACT_FAIL; q } .else { '
                + f'.if (@$t19 != 0n{completed}) {{ .echo ORDINARY_CASTLE_SEQUENCE_FAIL; q }} '
                + f'.else {{ r @$t19=0n{completed+1} }} }}')
            completed += 1
    lines.append(f'.if (@$t19 == 0n{completed}) {{ .echo ORDINARY_CASTLE_CONTRACT_PASS '
                 + f'stage={STAGE} resolution={RESOLUTION} candidate_sha256={sha(image)} }} '
                 + '.else { .echo ORDINARY_CASTLE_INCOMPLETE; q }')
    return '\n'.join(lines)+'\n'


def build_candidate(original: bytes, resolution: str = RESOLUTION):
    pe._require(resolution == RESOLUTION, 'only the exact 1024x768 predecessor is supported')
    pe._identity(original, pe.ORIGINAL_SHA256, 'original')
    source_before = sha((ROOT/SOURCE).read_bytes())
    parent, inherited, old_probe = parent_builder.build_candidate(original, 'modalwidgets', resolution)
    pe._identity(parent, PARENT_SHA256, 'exact nativepresent predecessor')
    pe._require(inherited['stage'] == PARENT_STAGE and inherited['resolution'] == RESOLUTION
                and inherited['recipe_revision'] == parent_builder.REVISION, 'predecessor metadata differs')
    view, old_fields = _layout(parent)
    native = _read(original, CALLER_START, CALLER_SIZE)
    pe._require(_read(parent, CALLER_START, CALLER_SIZE) == native, 'native caller changed')
    pe._require(_read(parent, NATIVE_CALLER, 5) == bytes.fromhex('e811340000')
                and _read(parent, 0x41ED54, 12) == bytes.fromhex('8b1dd89951008935d8995100'),
                'native caller owner-save/write or CALL differs')
    pe._require(_read(parent, ROOT_WRAPPER, len(ROOT_BYTES)) == ROOT_BYTES, 'root wrapper changed')
    pe._require(_read(parent, HOOK-10, 10) == OWNER_CMP, 'original owner comparison changed')
    gate, operands = emit_gate()
    branch = b'\xe9'+struct.pack('<i', GATE-HOOK-5)+b'\x90'
    edits = (_checked_edit(parent, HOOK, OLD_BRANCH, branch, 'dispatch original owner rejection'),
             _checked_edit(parent, GATE, bytes(GATE_BYTES), gate, 'native caller gate in unused RX padding'))
    output = bytearray(parent)
    for edit in edits: output[edit.offset:edit.offset+len(edit.old)] = edit.new
    image = bytes(output)
    after = pe.inspect_pe(image)
    pe._require(after == view and len(image) == len(parent), 'PE layout changed')
    old_table, _ = pe._old_relocations(parent, view)
    table, fields = pe._old_relocations(image, after)
    pe._require(table == old_table and fields == old_fields, 'relocation inventory changed')
    changed = {i for i, (a, b) in enumerate(zip(parent, image)) if a != b}
    admitted = {edit.offset+i for edit in edits for i in range(len(edit.old))}
    pe._require(changed <= admitted and len(changed) > 0, 'unrelated candidate bytes changed')
    spans = ((HOOK-10, 16), (GATE, len(gate)), (CALLER_START, CALLER_SIZE),
             (TRY_ENTER, 0x23B), (ROOT_WRAPPER, len(ROOT_BYTES)))
    probe = _probe(image, spans)
    sources = dict(inherited['source_hashes'])
    sources[SOURCE] = source_before
    pe._require(source_before == sha((ROOT/SOURCE).read_bytes()), 'source changed during build')
    metadata = dict(schema='clash95_ordinary_castle_entry_candidate_v1', stage=STAGE,
        recipe_revision=REVISION, resolution=RESOLUTION, original_sha256=pe.ORIGINAL_SHA256,
        candidate_sha256=sha(image), base_candidate_sha256=sha(parent), base_stage=PARENT_STAGE,
        source_hashes=sources, base_candidate=inherited, inherited_probe_sha256=sha(old_probe.encode()),
        code_va=GATE, code_bytes=len(gate), code_sha256=sha(gate), entry_vas={'native_caller_gate': GATE},
        relative_address_operands=operands, highlow_relocations_added=[], highlow_relocations_removed=[],
        preserved_relocation_sha256=sha(table), edits=[edit.metadata() for edit in edits],
        native_caller_contract=dict(start=CALLER_START, bytes=CALLER_SIZE, sha256=sha(native),
            root_return=NATIVE_RETURN, try_enter_return=WRAPPER_RETURN,
            owner=0x4617A0, saved_root_ebx=0x40AD40, saved_root_esi=0x4617A0,
            root_stack_from_gate_saved_esp=0x70),
        inherited_canvas_state_va=STATE, inherited_try_enter=TRY_ENTER,
        inherited_root_wrapper=ROOT_WRAPPER, probe_sha256=sha(probe.encode()),
        runtime_executed=False, manual_input_proof=False, promotion_ready=False, limits=LIMITS)
    return image, metadata, probe
