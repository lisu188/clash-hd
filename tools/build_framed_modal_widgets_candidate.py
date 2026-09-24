"""Build a separate widget-bounds candidate above the frozen primary-text stage."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from src.patcher import framed_modal_widget_bounds as widgets
from src.patcher import complete_hd_candidate as complete
from src.patcher import pe_extension as pe
import build_framed_modal_primary_text_candidate as text
from build_framed_modal_candidate import _checked_lines

STAGE = text.STAGE.removesuffix('-modalprimarytext-validation') + '-modalwidgets-validation'
REVISION = widgets.REVISION
SOURCES = (widgets.SOURCE, 'tools/build_framed_modal_widgets_candidate.py')
RESERVATION = 0x20000


def sha(data): return hashlib.sha256(data).hexdigest()


def allocation_layout(candidate):
    image = pe.inspect_pe(candidate)
    pe._require(len(image.sections) == 14 and tuple(s.name.rstrip(b'\0') for s in image.sections[-7:]) ==
        (b'.hdcode', b'.hdmodal', b'.hdstate', b'.hdarmy', b'.hdslots', b'.hdprim', b'.hdptxt'),
        'exact fourteen-section primary-text layout required')
    pe._require(all(s.characteristics == (0xC0000040 if index == 2 else pe.RX_CODE)
                    for index, s in enumerate(image.sections[-7:])), 'inherited section protections differ')
    pe._require((image.section_alignment, image.file_alignment, image.headers_size) == (4096, 512, 1024),
                'canonical text predecessor alignment required')
    pe._require(all(a.rva + pe._align(a.memory_size, 4096) == b.rva for a, b in zip(image.sections, image.sections[1:])),
                'predecessor section adjacency differs')
    slot = image.sections[-1].header_offset + 40
    pe._require(slot == 0x398 and candidate[slot:slot + 40] == bytes(40), 'widget header slot occupied or relocated')
    pe._require(image.image_base + image.image_size + RESERVATION < 0x80000000, 'widget image exceeds native user range')
    return image.image_base + image.image_size, slot


def _extend_verified_image(candidate, *, code, code_va, relocations, hooks, binding):
    """Private format core; only build_candidate establishes source identity."""
    expected_va, slot = allocation_layout(candidate)
    before = pe.inspect_pe(candidate)
    pe._require(type(code_va) is int and code_va == expected_va and type(code) is bytes
                and 0 < len(code) < 4096, 'bounded widget code/allocation required')
    pe._require(type(binding) is dict and isinstance(relocations, (tuple, list))
                and isinstance(hooks, (tuple, list)) and len(hooks) == 2, 'two widget hooks and source binding required')
    old_table, old_fields = pe._old_relocations(candidate, before)
    normalized, operands, absolute = [], [], []
    for row in relocations:
        pe._require(all(hasattr(row, key) for key in ('offset', 'kind', 'target', 'purpose')), 'malformed widget relocation')
        pe._require(type(row.offset) is int and 0 <= row.offset <= len(code) - 4
                    and row.kind in ('abs32', 'rel32') and type(row.purpose) is str and row.purpose.strip(),
                    'invalid widget relocation field')
        pe._u32(row.target, 'widget relocation target')
        pe._require(code_va <= row.target < code_va + len(code) or any(
            s.rva <= row.target - before.image_base < s.rva + s.memory_size
            and (row.kind == 'abs32' or s.characteristics & 0x20000000) for s in before.sections),
            'widget relocation target unmapped or nonexecutable')
        expected = row.target if row.kind == 'abs32' else (row.target - code_va - row.offset - 4) & 0xFFFFFFFF
        pe._require(struct.unpack_from('<I', code, row.offset)[0] == expected, 'widget relocation operand differs')
        operands.append(row.offset)
        normalized.append(dict(offset=row.offset, kind=row.kind, target=row.target, purpose=row.purpose))
        if row.kind == 'abs32': absolute.append(code_va - before.image_base + row.offset)
    operands.sort()
    pe._require(all(a + 4 <= b for a, b in zip(operands, operands[1:])), 'overlapping widget relocation fields')
    for hook in hooks:
        pe._require(isinstance(hook, pe.HookPatch) and type(hook.old) is bytes and type(hook.new) is bytes
                    and len(hook.old) == len(hook.new) == 6 and hook.old[:2] in widgets.CMP_PREFIXES
                    and hook.new[:1] == b'\xe8' and hook.new[-1:] == b'\x90', 'widget hook must replace one complete CMP with CALL/NOP')
        pe._require(isinstance(hook.relocations, (tuple, list)) and len(hook.relocations) == 1
                    and getattr(hook.relocations[0], 'kind', None) == 'rel32'
                    and type(getattr(hook.relocations[0], 'offset', None)) is int and hook.relocations[0].offset == 1
                    and type(getattr(hook.relocations[0], 'target', None)) is int
                    and code_va <= hook.relocations[0].target < code_va + len(code), 'widget hook must target new RX code')
    edits, added, hook_rows, removed = pe._prepare_hooks(candidate, before, hooks, (), old_fields, code_va, len(code))
    pe._require(not added and not removed, 'widget hooks cannot add/remove historical absolute fields')
    expected_fields = tuple(old_fields) + tuple(absolute)
    table = pe._relocation_blocks(expected_fields)
    table_at = pe._align(len(code), 4)
    payload = code + bytes(table_at - len(code)) + table
    raw_size = pe._align(len(payload), 512)
    pe._require(raw_size <= RESERVATION, 'widget payload and relocations exceed reservation')
    rva = code_va - before.image_base
    header = struct.pack('<8sIIIIIIHHI', b'.hdwgt', RESERVATION, rva, raw_size, len(candidate), 0, 0, 0, 0, pe.RX_CODE)
    for offset, data, label in (
        (before.pe_offset + 6, struct.pack('<H', 15), 'NumberOfSections'),
        (before.optional_offset + 4, struct.pack('<I', pe._u32(before.size_of_code + raw_size, 'SizeOfCode')), 'SizeOfCode'),
        (before.optional_offset + 56, struct.pack('<I', rva + RESERVATION), 'SizeOfImage'),
        (before.optional_offset + 136, struct.pack('<II', rva + table_at, len(table)), 'complete widget HIGHLOW directory'),
        (slot, header, '.hdwgt RX header'),
    ):
        old = candidate[offset:offset + len(data)]
        pe._require(len(old) == len(data), 'widget header edit exceeds predecessor')
        edits.append(pe.ByteEdit(offset, offset, before.image_base + offset, old, data, label))
    edits.append(pe.ByteEdit(len(candidate), rva, code_va, b'', payload + bytes(raw_size - len(payload)),
                             'append widget guards and complete merged relocations'))
    intervals = sorted((e.offset, e.offset + len(e.old)) for e in edits if e.old)
    pe._require(all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:])), 'overlapping widget edits')
    output = bytearray(candidate)
    for edit in edits:
        pe._require(output[edit.offset:edit.offset + len(edit.old)] == edit.old
                    and (edit.old or edit.offset == len(output)), 'widget old-byte or append-position mismatch')
        output[edit.offset:edit.offset + len(edit.old)] = edit.new
    image = bytes(output); after = pe.inspect_pe(image)
    pe._require(after.sections[:14] == before.sections, 'historical section header changed')
    _, actual = pe._old_relocations(image, after)
    pe._require(sorted(actual) == sorted(expected_fields), 'complete widget relocation inventory differs')
    old_offset = before.file_offset(before.relocation_rva, before.relocation_size)
    pe._require(image[old_offset:old_offset + len(old_table)] == old_table, 'historical relocation directory changed')
    metadata = dict(binding, schema='clash95_pe_modal_widgets_extension_v1', input_sha256=sha(candidate), output_sha256=sha(image),
        code_va=code_va, code_rva=rva, code_bytes=len(code), code_sha256=sha(code), code_raw_bytes=raw_size,
        code_virtual_bytes=RESERVATION, code_characteristics=pe.RX_CODE, old_highlow_count=len(old_fields),
        new_highlow_count=len(absolute), removed_highlow=[], relocations=normalized, hook_relocations=hook_rows,
        relocation_rva=rva + table_at, relocation_bytes=len(table), old_relocation_sha256=sha(old_table),
        merged_relocation_sha256=sha(table), hooks=[e.metadata() for e in edits[:2]], edits=[e.metadata() for e in edits],
        installation_ready=False, runtime_executed=False, manual_input_proof=False, promotion_ready=False)
    return pe.ExtensionResult(image, tuple(edits), metadata)


def make_probe(base, candidate, context, old_probe, bundle, metadata):
    pe._require(sha(old_probe.encode()) == context['probe_sha256'], 'exact predecessor probe required')
    before, after = pe.inspect_pe(base), pe.inspect_pe(candidate)
    changed = set()
    for edit in metadata['edits']: changed.update(range(edit['va'], edit['va'] + len(bytes.fromhex(edit['old_hex']))))
    count = 0
    def rebind(match):
        nonlocal count
        kind, address, expected = match.groups(); va = int(address, 16); size = 2 if kind == 'wo' else 1
        old, new = text.loaded_bytes(base, before, va, size), text.loaded_bytes(candidate, after, va, size)
        pe._require(int.from_bytes(old, 'little') == int(expected, 16), 'predecessor loaded predicate differs')
        pe._require(all(a == b or va + i in changed for i, (a, b) in enumerate(zip(old, new))),
                    'loaded predicate changed outside declared edits')
        count += 1
        return f'({kind}({address}) != {int.from_bytes(new, "little"):x})'
    probe = text.PREDICATE.sub(rebind, old_probe)
    pe._require(count > 0, 'predecessor loaded predicates absent')
    last = after.sections[-1]
    spans = [(after.image_base + last.rva, candidate[last.raw_offset:last.raw_offset + last.raw_size]),
             (after.image_base + last.header_offset, candidate[last.header_offset:last.header_offset + 40])]
    for record in bundle.source_contract['native_spans']:
        offset = after.file_offset(record['va'] - after.image_base, record['size'])
        spans.append((record['va'], candidate[offset:offset + record['size']]))
    checks = [line.replace('MCANVAS_CONTRACT_FAIL', 'MWIDGETS_CONTRACT_FAIL') for line in _checked_lines(spans)]
    marker = f'MWIDGETS_CONTRACT_PASS stage={STAGE} resolution={metadata["resolution"]} candidate_sha256={sha(candidate)} revision={REVISION}'
    replacements = {
        '.echo ' + context['probe_contract']['text_marker']: '\n'.join([*checks, '.echo ' + marker]),
        f'.echo PTILE_CONTRACT_PASS stage={text.STAGE} resolution={metadata["resolution"]} candidate_sha256={sha(base)}':
        f'.echo PTILE_CONTRACT_PASS stage={STAGE} resolution={metadata["resolution"]} candidate_sha256={sha(candidate)}',
        '.echo MPRIMARYTEXT_SCOPE owned_modal_primary_text primary_composition_proven=false manual_input_proof=false promotion_ready=false':
        '.echo MWIDGETS_SCOPE owned_modal_widget_bounds primary_composition_proven=false manual_input_proof=false promotion_ready=false',
    }
    for old, new in replacements.items():
        pe._require(probe.splitlines().count(old) == 1, 'exact predecessor startup/scope marker required')
        probe = probe.replace(old, new, 1)
    pe._require(all(len(line.encode('ascii')) < 4096 for line in probe.splitlines()), 'widget probe line exceeds CDB limit')
    return probe, marker


def build_candidate(original: bytes, resolution: str):
    pe._require(resolution in complete.RESOLUTIONS, 'supported canonical widget resolution required')
    before_sources = {name: sha((ROOT / name).read_bytes()) for name in SOURCES}
    base, context, old_probe = widgets.predecessor(original, resolution)
    width, height = map(int, resolution.split('x'))
    code_va, _ = allocation_layout(base)
    bundle = widgets._verified_bundle(original, base, context, base_va=code_va, width=width, height=height)
    pe._require(tuple(h.va for h in bundle.hook_sites) == (0x419D63, 0x419D8C), 'exact widget hook inventory required')
    result = _extend_verified_image(base, code=bundle.code, code_va=code_va, relocations=bundle.relocations,
        hooks=bundle.hook_sites, binding=dict(original_sha256=pe.ORIGINAL_SHA256, base_stage=text.STAGE, stage=STAGE,
            resolution=resolution, base_candidate_sha256=sha(base), recipe_revision=REVISION))
    metadata = dict(result.metadata)
    probe, marker = make_probe(base, result.image, context, old_probe, bundle, metadata)
    sources = dict(context['source_hashes']) | before_sources
    pe._require(sources == {name: sha((ROOT / name).read_bytes()) for name in sources}, 'widget source changed during build')
    metadata.update(schema='clash95_framed_modal_widgets_candidate_v1', candidate_sha256=sha(result.image),
        source_hashes=sources, base_candidate=context, widget_entry_vas=bundle.entries, widget_contract=bundle.source_contract,
        modal_state_va=bundle.modal_state_va, modal_entry_vas=context['modal_entry_vas'], probe_sha256=sha(probe.encode()),
        probe_contract=dict(stage=STAGE, widgets_marker=marker, requires_new_stage_consumer=True,
            predecessor_stage_preserved=text.STAGE, inherited_probe_sha256=sha(old_probe.encode())),
        validation_stage_only=True, primary_composition_proven=False,
        limitations=['Fresh matching runtime consumer and original-artwork pixel audit are required.',
                    'Older primary/text traces are not evidence for this new candidate.',
                    'No ordinary input, modal exit, game-runtime acceptance or stable promotion is established.'])
    return result.image, metadata, probe


def write_candidate(original, output, resolution):
    output = text.checked_output_path(Path(output))
    paths = (output, output.with_suffix('.candidate.json'), output.with_suffix('.cdb'))
    if any(path.exists() for path in paths): raise FileExistsError('widget bundle exists; choose a new name')
    image, metadata, probe = build_candidate(Path(original).read_bytes(), resolution)
    output.parent.mkdir(parents=True, exist_ok=True)
    complete._write_bundle(paths, (image, (json.dumps(metadata, indent=2) + '\n').encode(), probe.encode()))
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--resolution', choices=complete.RESOLUTIONS, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    if args.preflight:
        if args.output: parser.error('preflight accepts no output')
        _, metadata, _ = build_candidate(args.original.read_bytes(), args.resolution)
    else:
        if not args.output: parser.error('output is required unless preflight')
        metadata = write_candidate(args.original, args.output, args.resolution)
    print(json.dumps({key: metadata[key] for key in ('stage', 'resolution', 'candidate_sha256', 'runtime_executed', 'promotion_ready')}))


if __name__ == '__main__': main()
