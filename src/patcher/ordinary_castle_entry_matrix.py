"""Versioned native-caller admission above frozen Complete HD predecessors.

No predecessor source or recipe changes. The gate is appended by extending the
last RX section; all inherited admission and lifecycle code remains intact.
Source construction does not establish rendering, input, exit, or promotion.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import struct

from . import complete_hd_candidate as complete
from . import framed_modal_canvas as canvas
from . import native_present_bounds as parent_builder
from . import pe_extension as pe

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'src/patcher/ordinary_castle_entry_matrix.py'
REVISION = 'owned_ordinary_castle_entry_matrix_v1'
SCHEMA = 'clash95_ordinary_castle_entry_matrix_v1'
RESOLUTIONS = tuple(complete.RESOLUTIONS)
PROFILES = ('completehd', 'modalwidgets')
SUFFIX = '-ordinarycastleentry-matrix-validation'
GATE_BYTES = 96
NATIVE_CALLER, NATIVE_RETURN = 0x41ED6A, 0x41ED6F
CALLER_START, CALLER_SIZE = 0x41ED28, 0x72
OWNER_CMP = bytes.fromhex('813dd899510040ad4000')
LIMITS = (
    'Six existing resolutions only; no 4K or bounded small-world composition.',
    'Native caller admission only; inherited castle body and exit remain unchanged.',
    'No runtime, campaign input, visible composition, lifecycle or promotion proof.',
    'Initial-breakpoint verifier covers final headers, executable sections and legacy wrapper spans; mutable data and imported libraries are excluded.',
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stage(profile: str) -> str:
    pe._require(profile in PROFILES, 'supported complete profile required')
    base = complete.STAGE.removesuffix('-validation')
    return base + ('-modalwidgets' if profile == 'modalwidgets' else '') + '-nativepresent' + SUFFIX


def _read(image: bytes, va: int, size: int) -> bytes:
    view = pe.inspect_pe(image)
    offset = view.file_offset(va-view.image_base, size)
    return image[offset:offset+size]


def _node(value, schema, resolution):
    pe._require(type(value) is dict and value.get('schema') == schema
                and value.get('resolution') == resolution, 'typed ancestor identity differs: '+str(schema))
    return value


def modal_ancestor(metadata: dict, profile: str, resolution: str) -> dict:
    """Follow the one known typed chain, never search arbitrary nested metadata."""
    parent = _node(metadata, 'native_map_present_bounds_v1', resolution)
    expected_base = complete.STAGE if profile == 'completehd' else complete.STAGE.removesuffix('-validation')+'-modalwidgets-validation'
    pe._require(profile in PROFILES and resolution in RESOLUTIONS
                and parent.get('profile') == profile and parent.get('base_stage') == expected_base
                and parent.get('stage') == expected_base.removesuffix('-validation')+'-nativepresent-validation'
                and parent.get('recipe_revision') == parent_builder.REVISION
                and parent.get('base_recipe_revision') == ('complete_hd_v1' if profile == 'completehd' else 'owned_modal_widget_bounds_v1')
                and parent.get('original_sha256') == pe.ORIGINAL_SHA256,
                'native-present parent identity differs')
    node = parent.get('base_candidate')
    if profile == 'modalwidgets':
        for kind in ('widgets', 'primary_text', 'primary', 'slots'):
            node = _node(node, f'clash95_framed_modal_{kind}_candidate_v1', resolution).get('base_candidate')
    node = _node(node, 1, resolution)
    pe._require(node.get('stage') == complete.STAGE and node.get('recipe_revision') == complete.REVISION
                and node.get('base_sha256') == pe.ORIGINAL_SHA256, 'complete v1 identity differs')
    army = _node(node.get('predecessor'), 'clash95_framed_army_candidate_v1', resolution)
    modal = _node(army.get('base_candidate'), 'clash95_framed_modal_candidate_v1', resolution)
    pe._require(modal.get('modal_native_canvas_revision') == 'framed_owned_native_modal_canvas_v1'
                and modal.get('modal_state_offsets') == canvas.STATE
                and modal.get('modal_state_size') == canvas.STATE_SIZE, 'inherited canvas contract differs')
    return modal


@dataclass(frozen=True)
class Admission:
    try_enter: int
    root_wrapper: int
    wrapper_return: int
    comparison: int
    hook: int
    accept: int
    reject: int
    state: int


def derive_admission(original: bytes, parent: bytes, modal: dict) -> Admission:
    """Bind known instruction boundaries relative to authenticated entrypoints."""
    view = pe.inspect_pe(parent)
    entries = modal.get('modal_entry_vas')
    pe._require(type(entries) is dict and all(type(entries.get(k)) is int for k in ('try_enter', 'root_entry')),
                'typed modal entries required')
    enter, root, state_va = entries['try_enter'], entries['root_entry'], modal.get('state_va')
    pe._require(type(state_va) is int, 'typed state address required')
    code_section = [s for s in view.sections if s.name.rstrip(b'\0') == b'.hdmodal']
    state_section = [s for s in view.sections if s.name.rstrip(b'\0') == b'.hdstate']
    pe._require(len(code_section) == len(state_section) == 1
                and code_section[0].characteristics == pe.RX_CODE
                and state_section[0].characteristics == 0xC0000040
                and enter == view.image_base+code_section[0].rva
                and view.image_base+state_section[0].rva == state_va
                and modal.get('code_va') == enter, 'owned canvas section mapping differs')
    # Geometry changes immediate values, not these frozen instruction lengths.
    comparison, hook = enter+0x6B, enter+0x75
    pe._require(_read(parent, comparison, 10) == OWNER_CMP, 'owner comparison differs')
    branch = _read(parent, hook, 6)
    pe._require(branch[:2] == b'\x0f\x85', 'original owner rejection must be JNE rel32')
    reject = hook+6+struct.unpack_from('<i', branch, 2)[0]
    pe._require(reject == enter+0x230 and _read(parent, reject, 11) == bytes.fromhex('c744241c00000000619dc3'),
                'original rejection continuation differs')
    expected = (bytes.fromhex('9c608d442424e8')+struct.pack('<i', enter-root-11)
                +bytes.fromhex('619d5351525657e9')+struct.pack('<i', 0x422185-root-23))
    pe._require(len(expected) == 23 and _read(parent, root, len(expected)) == expected,
                'inherited root wrapper ABI differs')
    pe._require(_read(parent, 0x422180, 5) == b'\xe9'+struct.pack('<i', root-0x422185),
                'native root hook does not select inherited wrapper')
    native = _read(original, CALLER_START, CALLER_SIZE)
    pe._require(_read(parent, CALLER_START, CALLER_SIZE) == native
                and _read(parent, NATIVE_CALLER, 5) == bytes.fromhex('e811340000')
                and _read(parent, 0x41ED54, 12) == bytes.fromhex('8b1dd89951008935d8995100'),
                'native Building_GetInto caller differs')
    return Admission(enter, root, root+11, comparison, hook, hook+6, reject, state_va)


def emit_gate(code_va: int, admission: Admission) -> tuple[bytes, list[dict]]:
    """PIC guard: gate entry ESP=R-76; PUSHFD/PUSHAD set S=R-112."""
    pe._require(type(code_va) is int and 0x10000 <= code_va < 0x7FFE0000-GATE_BYTES
                and isinstance(admission, Admission), 'bounded gate and typed admission required')
    code = bytearray(); labels = {}; shorts = []; operands = []
    def emit(value): code.extend(bytes.fromhex(value))
    def branch(op, label):
        emit(op); shorts.append((len(code), label)); code.append(0)
    def displacement(target, purpose):
        pe._require(type(target) is int and 0x10000 <= target < 0x7FFE0000, 'bounded gate target required')
        operands.append(dict(offset=len(code), kind='eip_relative_disp32', anchor=code_va+9, target=target, purpose=purpose))
        code.extend(struct.pack('<i', target-code_va-9))
    def relative(op, target, purpose):
        emit(op); operands.append(dict(offset=len(code), kind='rel32', target=target, purpose=purpose))
        code.extend(struct.pack('<i', target-code_va-len(code)-4))
    branch('74', 'accepted'); emit('9c60'); relative('e8', code_va+9, 'local EIP anchor'); emit('5f')
    emit('8d8f'); displacement(0x4617A0, 'native default renderer')
    emit('398f'); displacement(canvas.HOOK_OWNER, 'live render owner'); branch('75', 'reject')
    for target, offset, purpose in ((0x40AD40, '34', 'saved ordinary map owner'),
                                  (0x4617A0, '28', 'saved native caller ESI'),
                                  (admission.wrapper_return, '48', 'inherited try_enter caller')):
        emit('8d8f'); displacement(target, purpose); emit('394c24'+offset); branch('75', 'reject')
    emit('8b44241c8d4c247039c8'); branch('75', 'reject')
    emit('8d87'); displacement(NATIVE_RETURN, 'native Building_GetInto return'); emit('3901'); branch('75', 'reject')
    emit('619d'); labels['accepted'] = len(code); relative('e9', admission.accept, 'remaining admission checks')
    labels['reject'] = len(code); emit('619d'); relative('e9', admission.reject, 'original rejection')
    for offset, name in shorts:
        delta = labels[name]-offset-1
        pe._require(-128 <= delta <= 127, 'short branch range exceeded'); code[offset] = delta & 255
    pe._require(len(code) == GATE_BYTES and code[4:10] == bytes.fromhex('e8000000005f'), 'gate layout differs')
    return bytes(code), operands


def extend_tail(parent: bytes, admission: Admission, profile: str):
    """Private checked format core; public build first reconstructs the parent."""
    before = pe.inspect_pe(parent); last = before.sections[-1]
    pe._require(profile in PROFILES and len(before.sections) == (12 if profile == 'completehd' else 16)
                and before.image_base == 0x400000
                and (before.section_alignment, before.file_alignment, before.headers_size) == (4096, 512, 1024)
                and last.name.rstrip(b'\0') == b'.hdpblit' and last.characteristics == pe.RX_CODE
                and last.raw_offset+last.raw_size == len(parent), 'canonical final native-present RX section required')
    old_table, old_fields = pe._old_relocations(parent, before)
    code_va = before.image_base+before.image_size
    code, operands = emit_gate(code_va, admission)
    hook_offset = before.file_offset(admission.hook-before.image_base, 6)
    expected = b'\x0f\x85'+struct.pack('<i', admission.reject-admission.hook-6)
    pe._require(parent[hook_offset:hook_offset+6] == expected
                and _read(parent, admission.comparison, 10) == OWNER_CMP
                and admission.accept == admission.hook+6 and admission.comparison+10 == admission.hook,
                'verified original owner branch differs')
    pe._require(not any(admission.hook-before.image_base < field+4 and field < admission.hook-before.image_base+6 for field in old_fields),
                'owner branch intersects HIGHLOW field')
    # Start after the old virtual extent; do not consume undocumented padding.
    within = before.image_size-last.rva
    pe._require(within >= last.memory_size and 0 <= within-last.raw_size < 4096,
                'unexpected tail backing gap')
    raw_size = pe._align(within+len(code), before.file_alignment)
    virtual_size = pe._align(within+len(code), before.section_alignment)
    pe._require(before.image_base+last.rva+virtual_size < 0x7FFE0000, 'extended image exceeds user range')
    append = bytes(within-last.raw_size)+code+bytes(raw_size-within-len(code))
    edits = [pe.ByteEdit(hook_offset, admission.hook-before.image_base, admission.hook, expected,
                        b'\xe9'+struct.pack('<i', code_va-admission.hook-5)+b'\x90', 'dispatch native caller admission')]
    for offset, new, purpose in (
        (last.header_offset+8, struct.pack('<I', virtual_size), 'extend final RX VirtualSize'),
        (last.header_offset+16, struct.pack('<I', raw_size), 'extend final RX SizeOfRawData'),
        (before.optional_offset+4, struct.pack('<I', before.size_of_code+raw_size-last.raw_size), 'extend SizeOfCode'),
        (before.optional_offset+56, struct.pack('<I', last.rva+virtual_size), 'extend SizeOfImage'),
    ):
        edits.append(pe.ByteEdit(offset, offset, before.image_base+offset, parent[offset:offset+4], new, purpose))
    edits.append(pe.ByteEdit(len(parent), last.rva+last.raw_size, before.image_base+last.rva+last.raw_size,
                             b'', append, 'append gate after previous image extent'))
    image = bytearray(parent)
    for edit in edits:
        pe._require(image[edit.offset:edit.offset+len(edit.old)] == edit.old and (edit.old or edit.offset == len(image)),
                    'old bytes or append position differ')
        image[edit.offset:edit.offset+len(edit.old)] = edit.new
    image = bytes(image); after = pe.inspect_pe(image)
    pe._require(after.sections[:-1] == before.sections[:-1]
                and pe._old_relocations(image, after) == (old_table, old_fields), 'old sections or relocation inventory changed')
    allowed = {edit.offset+i for edit in edits if edit.old for i in range(len(edit.old))}
    pe._require(all(a == b or i in allowed for i, (a, b) in enumerate(zip(parent, image))), 'undeclared predecessor bytes changed')
    return image, dict(code_va=code_va, code_bytes=len(code), code_sha256=sha(code), relative_address_operands=operands,
                      edits=[edit.metadata() for edit in edits], preserved_relocation_sha256=sha(old_table),
                      highlow_count=len(old_fields), highlow_relocations_added=[], highlow_relocations_removed=[])


def render_probe(image: bytes, metadata: dict, legacy_spans=()):
    """Read-only initial-breakpoint gate; errors cannot advance ordered chunks."""
    pe._require(metadata.get('schema') == SCHEMA and metadata.get('profile') in PROFILES
                and metadata.get('resolution') in RESOLUTIONS
                and metadata.get('stage') == stage(metadata['profile'])
                and metadata.get('candidate_sha256') == sha(image), 'final verifier candidate identity differs')
    view = pe.inspect_pe(image); _, fields = pe._old_relocations(image, view)
    spans = [(0, view.headers_size)] + [(s.rva, s.rva+s.raw_size) for s in view.sections if s.characteristics & 0x20000000 and s.raw_offset]
    for va, size in legacy_spans:
        pe._require(type(va) is int and type(size) is int and 0 < size <= 4096, 'bounded legacy span required')
        view.file_offset(va-view.image_base, size); spans.append((va-view.image_base, va-view.image_base+size))
    ranges = []
    for start, end in sorted(spans):
        if ranges and start <= ranges[-1][1]: ranges[-1] = (ranges[-1][0], max(end, ranges[-1][1]))
        else: ranges.append((start, end))
    base_field = view.optional_offset+28
    special = set(fields) | {base_field}
    pe._require(not any(base_field < f+4 and f < base_field+4 for f in fields), 'ImageBase overlaps HIGHLOW')
    lines = ['.expr /s masm', 'r @$t18=0', 'r @$t19=0',
             '.if (@$ptrsize == 0n4) { r @$t19=dwo(@$peb+0n8) }',
             f'.if ((@$t19 < 0x10000) | ((@$t19 & 0xffff) != 0) | (@$t19 > 0x{0x7FFE0000-view.image_size:08x})) {{ r @$t19=0 }}',
             '.echo OCEM_SCOPE initial_headers_rx_and_legacy_wrappers no_runtime_route']
    pending = []; chunks = 0; count = 0
    def flush():
        nonlocal chunks
        conditions = ' & '.join(pending)
        lines.append(f'.if ((@$t19 != 0) & (@$t18 == 0n{chunks})) {{ .if ({conditions}) {{ r @$t18=0n{chunks+1} }} .else {{ .echo OCEM_MISMATCH chunk={chunks} }} }}')
        chunks += 1; pending.clear()
    for start, end in ranges:
        # Section/header boundaries must not split a HIGHLOW operand.
        pe._require(not any(start < f+4 and f < end and not(start <= f and f+4 <= end) for f in special), 'partial relocated operand in verifier')
        stops = sorted(f for f in special if start <= f < end)
        at = start
        for stop in stops+[end]:
            while at < stop:
                size = 4 if stop-at >= 4 else 2 if stop-at >= 2 else 1
                offset = at if at+size <= view.headers_size else view.file_offset(at, size)
                value = int.from_bytes(image[offset:offset+size], 'little')
                reader = {1: 'by', 2: 'wo', 4: 'dwo'}[size]
                pending.append(f'({reader}(@$t19+0x{at:x}) == 0x{value:x})')
                at += size; count += 1
                if len(pending) == 24: flush()
            if stop != end:
                offset = at if at+4 <= view.headers_size else view.file_offset(at, 4)
                value = int.from_bytes(image[offset:offset+4], 'little')
                expected = '@$t19' if at == base_field else f'((0x{value:x}+@$t19-0x{view.image_base:x}) & 0xffffffff)'
                pending.append(f'(dwo(@$t19+0x{at:x}) == {expected})'); at += 4; count += 1
                if len(pending) == 24: flush()
    if pending: flush()
    lines.append(f'.if ((@$t19 != 0) & (@$t18 == 0n{chunks})) {{ .echo OCEM_CONTRACT_PASS stage={metadata["stage"]} resolution={metadata["resolution"]} candidate_sha256={sha(image)} }} .else {{ .echo OCEM_INCOMPLETE }}')
    lines.append('.echo OCEM_STOP target remains paused no input or lifecycle proof')
    pe._require(all(len(line.encode('ascii')) < 3800 for line in lines), 'verifier command exceeds CDB limit')
    # DbgEng ExecuteCommandFile needs CRLF here; block-file execution can mask
    # the malformed line parsing observed with LF-only exported commands.
    return '\r\n'.join(lines)+'\r\n', dict(checked_ranges=[dict(rva=a, bytes=b-a) for a,b in ranges],
        checked_bytes=sum(b-a for a,b in ranges), check_count=count, required_chunks=chunks,
        initial_breakpoint_required=True, relocation_aware=True, mutable_data_included=False)


def build_candidate(original: bytes, profile: str, resolution: str):
    pe._require(profile in PROFILES and resolution in RESOLUTIONS, 'supported profile and six-resolution matrix required')
    pe._identity(original, pe.ORIGINAL_SHA256, 'original')
    source_before = sha((ROOT/SOURCE).read_bytes())
    parent, inherited, old_probe = parent_builder.build_candidate(original, profile, resolution)
    pe._require(inherited.get('candidate_sha256') == sha(parent)
                and inherited.get('probe_sha256') == sha(old_probe.encode()), 'reconstructed parent artifact identity differs')
    modal = modal_ancestor(inherited, profile, resolution)
    admission = derive_admission(original, parent, modal)
    image, report = extend_tail(parent, admission, profile)
    sources = dict(inherited['source_hashes']); sources[SOURCE] = source_before
    pe._require(sources == {name: sha((ROOT/name).read_bytes()) for name in sources}, 'source changed during matrix build')
    metadata = dict(report, schema=SCHEMA, stage=stage(profile), recipe_revision=REVISION, profile=profile,
        resolution=resolution, original_sha256=pe.ORIGINAL_SHA256, candidate_sha256=sha(image),
        base_candidate_sha256=sha(parent), base_stage=inherited['stage'], base_candidate=inherited,
        source_hashes=sources, admission=asdict(admission), native_caller_sha256=sha(_read(original, CALLER_START, CALLER_SIZE)),
        inherited_probe_sha256=sha(old_probe.encode()), predecessor_probe_reusable=False,
        validation_stage_only=True, runtime_executed=False, manual_input_proof=False, promotion_ready=False,
        bounded_small_world_integrated=False, limits=list(LIMITS))
    legacy = [(row['entry_va'], row['span_bytes']) for row in modal['authenticated_legacy_continuations']]
    probe, facts = render_probe(image, metadata, legacy)
    metadata.update(probe_sha256=sha(probe.encode()), probe_contract=facts)
    return image, metadata, probe
