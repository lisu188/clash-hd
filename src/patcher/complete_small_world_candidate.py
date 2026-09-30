"""Original-bound small-world integration above the castle-entry matrix.

Only six inherited guards change. The integrated army ownership paths, castle
gate and presentation adapters stay in place. Construction and the read-only
initial-breakpoint verifier establish no runtime, input or promotion evidence.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import stat
import struct

from . import ordinary_castle_entry_matrix as matrix
from . import framed_bounded_paint as bounded
from . import framed_bounded_input as bounded_input
from . import framed_camera as camera
from . import partial_tile_clip as clip
from . import pe_extension as pe
from .framed_viewport import FramedViewport
from .framed_army_viewport import FramedArmyViewport

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'src/patcher/complete_small_world_candidate.py'
SCHEMA = 'clash95_complete_small_world_candidate_v1'
REVISION = 'complete_small_world_v1'
PROFILES = matrix.PROFILES
RESOLUTIONS = matrix.RESOLUTIONS
AXIS_OFFSETS = (24, 108)
AXIS_BYTES = 16
# Exact reviewed LF/CRLF checkout encodings, not arbitrary normalization.
PINNED = {
    'src/patcher/framed_camera.py': (
        'f8caea185f3714a6924a4e4cb40aa049866fc7864afa41a66da1b56a93059ef8',
        '913cd88529d98a421ebc06963d2d08978d371169c4ecf287ddadedd8c3191aec'),
    'src/patcher/framed_bounded_paint.py': (
        '981d946007b0438051dba033dce9e8e442cb7863ee49c547fbaad1e35d66cf1f',
        '8dbaa3ebf5b17c4ec9941abeea283628acbe34e5200403a7aaed3c3e66faadf0'),
    'src/patcher/framed_bounded_input.py': (
        '8117232bb875b1a0f9fb179b7a77ec7325e633ce283574b7f9b8cc3d37589258',
        '6292fccb2796eaa6a2ca46920209b871f405716ac1e5a16c7bfa126bc0e90ae4'),
}
LIMITS = (
    'Both complete profiles and the six existing resolutions only; no 4K or new resolution policy.',
    'Small-world guards reuse integrated frame, panel, presentation and army ownership targets; native fitting-world continuations remain.',
    'No game execution, measured device HRESULT, hidden route, visible composition, manual input, endurance, castle lifecycle or promotion proof.',
    'The fresh CRLF verifier checks final headers and file-backed executable bytes with loader relocations; mutable data and imported libraries are excluded.',
    'Predecessor probes and evidence identify intermediate images and cannot qualify this successor.',
)
sha = matrix.sha
require = pe._require


def stage(profile: str) -> str:
    return matrix.stage(profile).removesuffix('-validation')+'-smallworld-validation'


def _read(image: bytes, va: int, size: int) -> bytes:
    view = pe.inspect_pe(image)
    offset = view.file_offset(va-view.image_base, size)
    return image[offset:offset+size]


def _source_path(name: str) -> Path:
    require(type(name) is str and name and '\\' not in name
            and not Path(name).is_absolute() and '..' not in Path(name).parts,
            'repository-relative source required')
    path = ROOT/name
    require(all(not p.is_symlink() and not getattr(p, 'is_junction', lambda: False)()
                and not(getattr(p.lstat(), 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
                for p in (path, *path.parents)), 'source path follows a link: '+name)
    require(path.resolve().is_relative_to(ROOT) and path.is_file(), 'source path escapes repository: '+name)
    return path


def source_hashes(inherited: dict) -> dict[str, str]:
    require(type(inherited) is dict and matrix.SOURCE in inherited, 'matrix source inventory missing')
    for name, expected in inherited.items():
        require(type(expected) is str and sha(_source_path(name).read_bytes()) == expected,
                'inherited source identity differs: '+str(name))
    sources = dict(inherited)
    for name, allowed in PINNED.items():
        actual = sha(_source_path(name).read_bytes())
        require(actual in allowed, 'reviewed bounded source differs: '+name)
        require(name not in sources or sources[name] == actual, 'conflicting bounded source identity')
        sources[name] = actual
    sources[SOURCE] = sha(_source_path(SOURCE).read_bytes())
    return sources


def _extent(view, node: dict, section_name: bytes) -> tuple[int, int]:
    sections = [s for s in view.sections if s.name.rstrip(b'\0') == section_name]
    start, size = node.get('code_va'), node.get('code_bytes')
    require(len(sections) == 1 and sections[0].characteristics == pe.RX_CODE
            and type(start) is int and type(size) is int and size > 0
            and start == view.image_base+sections[0].rva and size <= sections[0].raw_size,
            'typed payload extent differs: '+section_name.decode())
    view.file_offset(start-view.image_base, size)
    return start, start+size


def _entries(view, entries, names, extent):
    require(type(entries) is dict, 'typed entry inventory missing')
    for name in names:
        va = entries.get(name)
        require(type(va) is int and extent[0] <= va < extent[1], 'entry outside owned payload: '+name)
        view.file_offset(va-view.image_base, 1)


def _matrix_parent(parent: bytes, metadata: dict, admission, profile: str) -> None:
    """Replay the declared matrix edits and bind every inherited parent byte."""
    rows = metadata.get('edits')
    keys = {'offset', 'rva', 'va', 'old_hex', 'new_hex', 'purpose'}
    require(type(rows) is list and len(rows) == 6, 'six inherited matrix edits required')
    restored = bytearray(parent)
    for row in reversed(rows):
        require(type(row) is dict and set(row) == keys
                and all(type(row[k]) is int and row[k] >= 0 for k in ('offset', 'rva', 'va'))
                and all(type(row[k]) is str for k in ('old_hex', 'new_hex', 'purpose')),
                'malformed inherited matrix edit')
        offset = row['offset']; old = bytes.fromhex(row['old_hex']); new = bytes.fromhex(row['new_hex'])
        require(new and restored[offset:offset+len(new)] == new, 'inherited matrix declared bytes differ')
        if old:
            require(len(old) == len(new), 'matrix edit changes inherited span size')
            restored[offset:offset+len(new)] = old
        else:
            require(offset+len(new) == len(restored), 'matrix append is not the complete tail')
            del restored[offset:]
    native = bytes(restored)
    require(sha(native) == metadata['base_candidate_sha256'], 'native-present parent replay SHA differs')
    replay, report = matrix.extend_tail(native, admission, profile)
    require(replay == parent and all(metadata.get(key) == value for key,value in report.items()),
            'matrix construction or report differs from exact replay')


def _context(parent: bytes, metadata: dict, profile: str, resolution: str):
    require(type(parent) is bytes and type(metadata) is dict
            and profile in PROFILES and resolution in RESOLUTIONS, 'supported typed matrix parent required')
    require(metadata.get('schema') == matrix.SCHEMA and metadata.get('recipe_revision') == matrix.REVISION
            and metadata.get('stage') == matrix.stage(profile) and metadata.get('profile') == profile
            and metadata.get('resolution') == resolution and metadata.get('original_sha256') == pe.ORIGINAL_SHA256
            and metadata.get('candidate_sha256') == sha(parent), 'exact castle-entry matrix identity differs')
    require(metadata.get('validation_stage_only') is True and metadata.get('bounded_small_world_integrated') is False
            and metadata.get('predecessor_probe_reusable') is False
            and all(metadata.get(n) is False for n in ('runtime_executed', 'manual_input_proof', 'promotion_ready')),
            'matrix evidence boundary differs')
    native = metadata.get('base_candidate')
    modal = matrix.modal_ancestor(native, profile, resolution)
    require(metadata.get('base_stage') == native['stage']
            and metadata.get('base_candidate_sha256') == native.get('candidate_sha256'), 'matrix parent link differs')
    node = native['base_candidate']
    if profile == 'modalwidgets':
        for _ in range(4): node = node['base_candidate']
    require(type(node.get('schema')) is int and node['schema'] == 1, 'typed complete schema must be integer one')
    army = node['predecessor']
    framed = matrix._node(modal.get('base_candidate'), 'clash95_pe_extension_v1', resolution)
    require(army.get('army_revision') == 'framed_own_army_native_size_v1'
            and army.get('base_candidate') is modal
            and framed.get('stage') == camera.PARENT_STAGE and framed.get('framed_validation') is True
            and framed.get('minimap_viewport') is True, 'integrated army/framed recipe differs')
    view = pe.inspect_pe(parent); last = view.sections[-1]
    require(len(view.sections) == (12 if profile == 'completehd' else 16)
            and view.image_base == 0x400000
            and (view.section_alignment, view.file_alignment, view.headers_size) == (4096, 512, 1024)
            and last.name.rstrip(b'\0') == b'.hdpblit' and last.characteristics == pe.RX_CODE
            and last.raw_offset+last.raw_size == len(parent), 'canonical matrix final RX tail required')
    framed_extent = _extent(view, framed, b'.hdcode'); army_extent = _extent(view, army, b'.hdarmy')
    entries = framed.get('entry_vas'); private = army.get('army_entry_vas')
    names = (*bounded.HELPERS, 'hook_framed_full_entry', 'initial_paint_admission', 'framed_full_fallback',
             'framed_full_reject', 'initial_admission_reject', bounded_input.ENTRY, bounded_input.DENY)
    _entries(view, entries, names, framed_extent)
    _entries(view, private, ('input.private.pixel_guard.minimap_clear', 'input.private.pixel_guard.deny'), army_extent)
    layout = FramedViewport(*map(int, resolution.split('x')))
    army_layout = FramedArmyViewport(layout.width, layout.height)
    contracts = army.get('army_contracts'); composition = contracts.get('composition') if type(contracts) is dict else None
    require(type(composition) is dict and composition.get('profile') == 'framed_own_army_composition_v1'
            and tuple(composition.get('backing', ())) == army_layout.backing.as_tuple()
            and tuple(composition.get('hit', ())) == army_layout.hit.as_tuple()
            and composition.get('original_generators_unchanged') is True
            and composition.get('unsupported_owner_is_original_fallback') is True,
            'integrated army composition contract differs')
    hooks = composition.get('hooks')
    require(type(hooks) is list and len(hooks) == 7 and all(type(row) is dict for row in hooks)
            and len({row.get('va') for row in hooks}) == 7,
            'seven distinct army composition hooks required')
    for row in hooks:
        require(type(row) is dict and type(row.get('va')) is int and type(row.get('new_hex')) is str,
                'malformed army composition hook')
        old, new = bytes.fromhex(row['old_hex']), bytes.fromhex(row['new_hex'])
        require(len(old) == len(new) and 0 < len(new) <= 16 and _read(parent, row['va'], len(new)) == new,
                'integrated army hook bytes differ')
    admission_row = metadata.get('admission')
    require(type(admission_row) is dict and set(admission_row) == set(matrix.Admission.__dataclass_fields__)
            and all(type(v) is int for v in admission_row.values()), 'typed matrix admission required')
    admission = matrix.Admission(**admission_row)
    modal_entries = modal.get('modal_entry_vas', {})
    require(admission.try_enter == modal_entries.get('try_enter') and admission.root_wrapper == modal_entries.get('root_entry')
            and admission.state == modal.get('state_va') and admission.comparison == admission.try_enter+0x6b
            and admission.hook == admission.try_enter+0x75 and admission.accept == admission.hook+6
            and admission.reject == admission.try_enter+0x230 and admission.wrapper_return == admission.root_wrapper+11,
            'matrix admission ancestry differs')
    gate_va = metadata.get('code_va')
    require(type(gate_va) is int and view.image_base+last.rva <= gate_va
            and gate_va+matrix.GATE_BYTES <= view.image_base+view.image_size
            and metadata.get('code_bytes') == matrix.GATE_BYTES, 'matrix gate extent differs')
    gate, _ = matrix.emit_gate(gate_va, admission)
    require(_read(parent, gate_va, len(gate)) == gate and metadata.get('code_sha256') == sha(gate)
            and _read(parent, admission.comparison, 10) == matrix.OWNER_CMP
            and _read(parent, admission.hook, 6) == b'\xe9'+struct.pack('<i', gate_va-admission.hook-5)+b'\x90',
            'inherited matrix gate or dispatch bytes differ')
    _matrix_parent(parent, metadata, admission, profile)
    old_table, old_fields = pe._old_relocations(parent, view)
    require(not any(start < field+4 and field < end for start,end in (
                (gate_va-view.image_base, gate_va-view.image_base+matrix.GATE_BYTES),
                (admission.hook-view.image_base, admission.hook-view.image_base+6)) for field in old_fields),
            'PIC matrix gate or dispatch intersects HIGHLOW')
    require(metadata.get('preserved_relocation_sha256') == sha(old_table)
            and metadata.get('highlow_count') == len(old_fields)
            and metadata.get('highlow_relocations_added') == [] and metadata.get('highlow_relocations_removed') == [],
            'inherited matrix relocation contract differs')
    legacy = modal.get('authenticated_legacy_continuations')
    require(type(legacy) is list and all(type(row) is dict and type(row.get('entry_va')) is int
            and type(row.get('span_bytes')) is int and 0 < row['span_bytes'] <= 4096 for row in legacy),
            'typed legacy continuation inventory required')
    for row in legacy: view.file_offset(row['entry_va']-view.image_base, row['span_bytes'])
    return view, layout, entries, private, framed_extent, army_extent, modal, old_table, old_fields


def _upgrade_verified_parent(parent: bytes, metadata: dict, profile: str, resolution: str):
    """Checked format core; only build_candidate authenticates original ancestry.

    Synthetic callers can exercise this core, but synthetic metadata is never
    original-game evidence and cannot bypass the public original SHA check.
    """
    sources = source_hashes(metadata.get('source_hashes') if type(metadata) is dict else None)
    view, layout, entries, private, framed_extent, army_extent, modal, old_table, old_fields = _context(parent, metadata, profile, resolution)
    last = view.sections[-1]; helper_va = view.image_base+view.image_size
    helper = bounded.emit_helpers(layout, base_va=helper_va, entries=entries)
    require(len(helper.code) == 481, 'reviewed bounded helper length differs')
    added = tuple(helper_va-view.image_base+offset for offset in clip.absolute_relocation_offsets(helper))
    require(len(added) == 5 and len(helper.relocations) == 10, 'reviewed bounded relocation inventory differs')
    fields = []
    for r in helper.relocations:
        require(type(r.offset) is int and 0 <= r.offset <= len(helper.code)-4 and r.kind in ('abs32', 'rel32')
                and type(r.target) is int and view.contains_memory(r.target-view.image_base), 'invalid bounded helper relocation')
        expected = r.target if r.kind == 'abs32' else (r.target-helper_va-r.offset-4) & 0xffffffff
        require(struct.unpack_from('<I', helper.code, r.offset)[0] == expected, 'bounded helper operand differs')
        fields.append(asdict(r))
    spans = []; span_fields = []
    def span(name, va, old, new, extent, **details):
        require(type(va) is int and extent[0] <= va and va+len(old) <= extent[1]
                and len(old) == len(new) and _read(parent, va, len(old)) == old, 'old guard bytes differ: '+name)
        rva = va-view.image_base
        require(not any(rva < f+4 and f < rva+len(old) for f in old_fields), 'guard intersects HIGHLOW: '+name)
        edit = pe.ByteEdit(view.file_offset(rva, len(old)), rva, va, old, new, name)
        rationale = ('Retain owner admission and native fitting-world continuation; clamp bounded camera and dispatch small-world paint.'
                     if name.startswith('render.') else
                     'Admit small worlds only at scroll zero while retaining complete dimension, actual-cell, minimap and army ownership rejection.')
        spans.append(dict(edit.metadata(), name=name, group='complete-small-world', stage=stage(profile), rationale=rationale, **details))
    for kind, entry_name, reject_name in (('full_redraw', 'hook_framed_full_entry', 'framed_full_reject'),
                                         ('initial_paint', 'initial_paint_admission', 'initial_admission_reject')):
        entry = entries[entry_name]; prefix = camera._prefix(kind, entry, entries)
        require(_read(parent, entry, len(prefix)) == prefix, 'inherited render admission prefix differs: '+kind)
        va = entry+camera.GATE_OFFSETS[kind]; reject = entries[reject_name]
        replacement, relocs = bounded._gate(kind, va, reject, helper)
        span('render.'+kind, va, camera.old_gate(layout, va, reject), replacement, framed_extent,
             continuation_va=va+camera.GATE_SIZE, reject_va=reject)
        span_fields.extend(dict(asdict(r), guard_va=va) for r in relocs)
    for owner, mapping, start_name, deny_name, extent in (
        ('ordinary', entries, bounded_input.ENTRY, bounded_input.DENY, framed_extent),
        ('army', private, 'input.private.pixel_guard.minimap_clear', 'input.private.pixel_guard.deny', army_extent)):
        start, deny = mapping[start_name], mapping[deny_name]
        old = bounded_input.world_gate(layout, start, deny)
        new = bounded_input.world_gate(layout, start, deny, small_world=True)
        require(start+len(old) <= extent[1] and _read(parent, start, len(old)) == old,
                'full inherited input world gate differs: '+owner)
        for axis, offset in zip(('x', 'y'), AXIS_OFFSETS):
            span('input.'+owner+'.'+axis, start+offset, old[offset:offset+AXIS_BYTES], new[offset:offset+AXIS_BYTES],
                 extent, continuation_va=start+offset+AXIS_BYTES, reject_va=deny)
    ordered = sorted(spans, key=lambda r:r['offset'])
    require(len(spans) == 6 and all(a['offset']+len(bytes.fromhex(a['old_hex'])) <= b['offset']
                                  for a,b in zip(ordered, ordered[1:])), 'six nonoverlapping guards required')
    within = view.image_size-last.rva
    require(within >= last.memory_size and 0 <= within-last.raw_size < view.section_alignment,
            'unexpected matrix tail backing gap')
    table_offset = pe._align(within+len(helper.code), 4)
    merged_fields = tuple(sorted((*old_fields, *added)))
    table = pe._relocation_blocks(merged_fields)
    used = table_offset+len(table)
    raw_size = pe._align(used, view.file_alignment); virtual_size = pe._align(used, view.section_alignment)
    require(view.image_base+last.rva+virtual_size < 0x7ffe0000, 'small-world image exceeds user range')
    append = (bytes(within-last.raw_size)+helper.code+bytes(table_offset-within-len(helper.code))
              +table+bytes(raw_size-used))
    edits = [pe.ByteEdit(r['offset'], r['rva'], r['va'], bytes.fromhex(r['old_hex']), bytes.fromhex(r['new_hex']), r['name']) for r in ordered]
    for offset, new, purpose in (
        (last.header_offset+8, struct.pack('<I', virtual_size), 'extend final RX VirtualSize'),
        (last.header_offset+16, struct.pack('<I', raw_size), 'extend final RX SizeOfRawData'),
        (view.optional_offset+4, struct.pack('<I', view.size_of_code+raw_size-last.raw_size), 'extend SizeOfCode'),
        (view.optional_offset+56, struct.pack('<I', last.rva+virtual_size), 'extend SizeOfImage'),
        (view.optional_offset+136, struct.pack('<II', last.rva+table_offset, len(table)), 'select complete merged HIGHLOW directory')):
        edits.append(pe.ByteEdit(offset, offset, view.image_base+offset, parent[offset:offset+len(new)], new, purpose))
    edits.append(pe.ByteEdit(len(parent), last.rva+last.raw_size, view.image_base+last.rva+last.raw_size,
                             b'', append, 'append bounded helper and full merged HIGHLOW directory'))
    image = bytearray(parent)
    for edit in edits:
        require(image[edit.offset:edit.offset+len(edit.old)] == edit.old and (edit.old or edit.offset == len(image)),
                'old bytes or append position changed')
        image[edit.offset:edit.offset+len(edit.old)] = edit.new
    image = bytes(image); after = pe.inspect_pe(image)
    old_table_offset = view.file_offset(view.relocation_rva, view.relocation_size)
    require(after.sections[:-1] == view.sections[:-1]
            and pe._old_relocations(image, after) == (table, merged_fields)
            and image[old_table_offset:old_table_offset+len(old_table)] == old_table, 'inherited sections or relocation bytes changed')
    allowed = {e.offset+i for e in edits if e.old for i in range(len(e.old))}
    require(all(a == b or i in allowed for i,(a,b) in enumerate(zip(parent, image))), 'undeclared predecessor byte changed')
    require(sources == source_hashes(metadata['source_hashes']), 'source changed during small-world integration')
    report = dict(schema=SCHEMA, recipe_revision=REVISION, stage=stage(profile), profile=profile, resolution=resolution,
        original_sha256=pe.ORIGINAL_SHA256, candidate_sha256=sha(image), base_candidate_sha256=sha(parent),
        base_stage=metadata['stage'], base_candidate=metadata, source_hashes=sources, spans={r['name']:r for r in spans},
        helpers=dict(base_va=helper_va, byte_count=len(helper.code), sha256=sha(helper.code), entry_vas=helper.entries,
                     parent_entry_vas={n:entries[n] for n in bounded.HELPERS}, relocations=fields), guard_relocations=span_fields,
        relocation_contract=dict(old_rvas=list(old_fields), added_rvas=list(added), merged_rvas=list(merged_fields),
            old_directory_rva=view.relocation_rva, old_directory_size=len(old_table), old_directory_sha256=sha(old_table),
            new_directory_rva=after.relocation_rva, new_directory_size=len(table), new_directory_sha256=sha(table)),
        edits=[dict(e.metadata(), group='complete-small-world', stage=stage(profile)) for e in edits],
        inherited_castle_gate=dict(va=metadata['code_va'], bytes=matrix.GATE_BYTES, sha256=metadata['code_sha256']),
        legacy_verifier_spans=[dict(va=r['entry_va'], bytes=r['span_bytes']) for r in modal['authenticated_legacy_continuations']],
        full_tiles=list(layout.full_tiles), ceil_tiles=list(layout.ceil_tiles), camera_clamp=True,
        bounded_small_world_integrated=True, small_world_input_enabled=True, predecessor_probe_reusable=False,
        validation_stage_only=True, installation_ready=False, runtime_executed=False,
        manual_input_proof=False, promotion_ready=False, limits=list(LIMITS))
    return image, report


def render_probe(image: bytes, metadata: dict):
    """Complete final-byte verifier; ordered chunks fail closed on read errors."""
    require(type(metadata) is dict and metadata.get('schema') == SCHEMA and metadata.get('recipe_revision') == REVISION
            and metadata.get('profile') in PROFILES and metadata.get('resolution') in RESOLUTIONS
            and metadata.get('stage') == stage(metadata['profile']) and metadata.get('candidate_sha256') == sha(image),
            'final small-world verifier identity differs')
    view = pe.inspect_pe(image); _, fields = pe._old_relocations(image, view)
    spans = [(0, view.headers_size)]+[(s.rva, s.rva+s.raw_size) for s in view.sections if s.characteristics & 0x20000000 and s.raw_offset]
    legacy = metadata.get('legacy_verifier_spans')
    require(type(legacy) is list, 'legacy verifier span inventory missing')
    for row in legacy:
        va, size = row.get('va'), row.get('bytes')
        require(type(va) is int and type(size) is int and 0 < size <= 4096, 'bounded legacy verifier span required')
        view.file_offset(va-view.image_base, size); spans.append((va-view.image_base, va-view.image_base+size))
    ranges = []
    for start, end in sorted(spans):
        # Adjacent sections have distinct file mappings. Keep their boundary so
        # an unaligned DWORD after a HIGHLOW field never straddles two sections.
        if ranges and start < ranges[-1][1]: ranges[-1] = (ranges[-1][0], max(end,ranges[-1][1]))
        else: ranges.append((start,end))
    base_field = view.optional_offset+28; special = set(fields)|{base_field}
    require(not any(base_field < f+4 and f < base_field+4 for f in fields), 'ImageBase overlaps HIGHLOW')
    lines = ['.expr /s masm', 'r @$t18=0', 'r @$t19=0',
        '.if (@$ptrsize == 0n4) { r @$t19=dwo(@$peb+0n8) }',
        f'.if ((@$t19 < 0x10000) | ((@$t19 & 0xffff) != 0) | (@$t19 > 0x{0x7ffe0000-view.image_size:08x})) {{ r @$t19=0 }}',
        '.if (@$t19 == 0) { .echo CSW_BASE_INVALID }',
        '.echo CSW_SCOPE initial_headers_rx_and_legacy_wrappers no_runtime_route']
    pending = []; chunks = 0; count = 0
    # Explicit 64-bit MASM literals disable automatic sign extension. Both
    # ordinary DWORD reads and relocated values are compared as uint32.
    mask = '0x00000000`ffffffff'
    def flush():
        nonlocal chunks
        conditions = ' & '.join(pending)
        lines.append(f'.if ((@$t19 != 0) & (@$t18 == 0n{chunks})) {{ .if ({conditions}) {{ r @$t18=0n{chunks+1} }} .else {{ .echo CSW_CHUNK_{chunks}_BAD }} }}')
        chunks += 1; pending.clear()
    def check(condition):
        if pending and (len(pending) == 24 or sum(map(len,pending))+len(condition)+4*len(pending) > 3200):
            flush()
        pending.append(condition)
    for start, end in ranges:
        require(not any(start < f+4 and f < end and not(start <= f and f+4 <= end) for f in special), 'partial relocated verifier operand')
        at = start
        for stop in sorted(f for f in special if start <= f < end)+[end]:
            while at < stop:
                size = 4 if stop-at >= 4 else 2 if stop-at >= 2 else 1
                offset = at if at+size <= view.headers_size else view.file_offset(at,size)
                value = int.from_bytes(image[offset:offset+size], 'little'); reader={1:'by',2:'wo',4:'dwo'}[size]
                if size == 4:
                    check(f'(({reader}(@$t19+0x{at:x}) & {mask}) == 0x00000000`{value:08x})')
                else:
                    check(f'({reader}(@$t19+0x{at:x}) == 0x{value:x})')
                at += size; count += 1
            if stop != end:
                offset = at if at+4 <= view.headers_size else view.file_offset(at,4)
                value = int.from_bytes(image[offset:offset+4], 'little')
                expected = '@$t19' if at == base_field else f'((0x00000000`{value:08x}+@$t19-0x{view.image_base:x}) & {mask})'
                check(f'((dwo(@$t19+0x{at:x}) & {mask}) == {expected})'); at += 4; count += 1
    if pending: flush()
    marker = f'CSW_FINAL_OK stage={metadata["stage"]} resolution={metadata["resolution"]} candidate_sha256={sha(image)}'
    lines += [f'.if ((@$t19 != 0) & (@$t18 == 0n{chunks})) {{ .echo {marker} }} .else {{ .echo CSW_INCOMPLETE }}',
              '.echo CSW_STOP target remains paused no input or lifecycle proof']
    require(all(len(line.encode('ascii')) < 3800 for line in lines), 'verifier command exceeds CDB limit')
    return '\r\n'.join(lines)+'\r\n', dict(checked_ranges=[dict(rva=a,bytes=b-a) for a,b in ranges],
        checked_bytes=sum(b-a for a,b in ranges), check_count=count, required_chunks=chunks, acceptance_marker=marker,
        initial_breakpoint_required=True, relocation_aware=True, mutable_data_included=False)


def build_candidate(original: bytes, profile: str, resolution: str):
    require(profile in PROFILES and resolution in RESOLUTIONS, 'supported profile and six-resolution matrix required')
    pe._identity(original, pe.ORIGINAL_SHA256, 'original')
    before = source_hashes({matrix.SOURCE:sha(_source_path(matrix.SOURCE).read_bytes())})
    parent, inherited, old_probe = matrix.build_candidate(original, profile, resolution)
    require(inherited.get('candidate_sha256') == sha(parent) and inherited.get('probe_sha256') == sha(old_probe.encode()),
            'reconstructed matrix bundle identity differs')
    image, metadata = _upgrade_verified_parent(parent, inherited, profile, resolution)
    require(all(metadata['source_hashes'].get(name) == digest for name,digest in before.items()),
            'small-world source changed during parent reconstruction')
    probe, facts = render_probe(image, metadata)
    metadata.update(inherited_probe_sha256=sha(old_probe.encode()), probe_sha256=sha(probe.encode()), probe_contract=facts)
    require(metadata['source_hashes'] == source_hashes(inherited['source_hashes']), 'source changed during final verification')
    return image, metadata, probe
