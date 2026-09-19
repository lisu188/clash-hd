#!/usr/bin/env python3
"""Build the separate owned-modal text candidate; never launch the game."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tools'))
from src.patcher import complete_hd_candidate as complete
from src.patcher import framed_modal_primary_text as text
from src.patcher import pe_modal_primary_text_extension as extension
from src.patcher import pe_extension as pe
import build_framed_modal_primary_candidate as primary
from build_framed_modal_candidate import _checked_lines

STAGE, REVISION = text.STAGE, text.REVISION
SOURCES = ('src/patcher/framed_modal_primary_text.py', 'src/patcher/pe_modal_primary_text_extension.py',
           'tools/build_framed_modal_primary_text_candidate.py')
PREDICATE = re.compile(r'\((wo|by)\(([0-9a-f]{8})\) != ([0-9a-f]+)\)')


def sha(data): return hashlib.sha256(data).hexdigest()


def loaded_bytes(candidate, view, va, size):
    """Read a checked image predicate, including initial zero-filled BSS."""
    result = bytearray()
    for rva in range(va - view.image_base, va - view.image_base + size):
        if 0 <= rva < view.headers_size:
            result.append(candidate[rva])
            continue
        sections = [s for s in view.sections if s.rva <= rva < s.rva + s.memory_size]
        pe._require(len(sections) == 1, 'loaded predicate address is unmapped or ambiguous')
        section = sections[0]
        relative = rva - section.rva
        # The original linker describes .bss with a nonzero SizeOfRawData but
        # PointerToRawData=0. It is zero-filled, not a view of the DOS image.
        result.append(candidate[section.raw_offset + relative]
                      if section.raw_offset and relative < section.raw_size else 0)
    return bytes(result)


def make_probe(base, candidate, context, old_probe, bundle, metadata):
    """Retain every predecessor predicate; update only authenticated edit bytes."""
    pe._require(sha(old_probe.encode()) == context['probe_sha256'], 'predecessor loaded probe hash differs')
    before, after = pe.inspect_pe(base), pe.inspect_pe(candidate)
    changed = set()
    for row in metadata['edits']:
        changed.update(range(row['va'], row['va'] + len(bytes.fromhex(row['old_hex']))))
    count = 0

    def rebind(match):
        nonlocal count
        kind, address, expected = match.groups()
        va, size = int(address, 16), 2 if kind == 'wo' else 1
        old = loaded_bytes(base, before, va, size)
        new = loaded_bytes(candidate, after, va, size)
        pe._require(int.from_bytes(old, 'little') == int(expected, 16), 'inherited loaded predicate differs from predecessor')
        pe._require(all(a == b or va + index in changed for index, (a, b) in enumerate(zip(old, new))),
                    'inherited predicate changed outside declared edits')
        count += 1
        return f'({kind}({address}) != {int.from_bytes(new, "little"):x})'

    probe = PREDICATE.sub(rebind, old_probe)
    pe._require(count > 0, 'predecessor loaded predicates absent')
    old_marker = '.echo ' + context['probe_contract']['primary_marker']
    pe._require(probe.splitlines().count(old_marker) == 1, 'exact predecessor primary marker required')
    spans = [(after.image_base + after.sections[-1].rva,
              candidate[after.sections[-1].raw_offset:after.sections[-1].raw_offset + after.sections[-1].raw_size]),
             (after.image_base + after.sections[-1].header_offset,
              candidate[after.sections[-1].header_offset:after.sections[-1].header_offset + 40])]
    for va, size, _ in text.NATIVE_SPANS:
        offset = after.file_offset(va - after.image_base, size)
        spans.append((va, candidate[offset:offset + size]))
    format_offset = after.file_offset(text.TEXT_FORMAT - after.image_base, 3)
    pe._require(candidate[format_offset:format_offset + 3] == b'%d\0', 'native text format differs')
    spans.append((text.TEXT_FORMAT, candidate[format_offset:format_offset + 3]))
    spans.extend((hook.va, hook.new) for hook in bundle.hook_sites)
    checks = [line.replace('MCANVAS_CONTRACT_FAIL', 'MPRIMARYTEXT_CONTRACT_FAIL') for line in _checked_lines(spans)]
    marker = (f'MPRIMARYTEXT_CONTRACT_PASS stage={STAGE} resolution={metadata["resolution"]} '
              f'candidate_sha256={sha(candidate)} revision={REVISION}')
    probe = probe.replace(old_marker, '\n'.join([*checks, '.echo ' + marker]), 1)
    old_ptile = (f'.echo PTILE_CONTRACT_PASS stage={primary.STAGE} resolution={metadata["resolution"]} '
                 f'candidate_sha256={sha(base)}')
    pe._require(probe.splitlines().count(old_ptile) == 1, 'exact predecessor tile marker required')
    probe = probe.replace(old_ptile, old_ptile.replace(primary.STAGE, STAGE).replace(sha(base), sha(candidate)), 1)
    old_scope = ('.echo MPRIMARY_SCOPE owned_modal_primary primary_composition_proven=false '
                 'manual_input_proof=false promotion_ready=false')
    pe._require(probe.splitlines().count(old_scope) == 1, 'exact predecessor scope marker required')
    probe = probe.replace(old_scope, '.echo MPRIMARYTEXT_SCOPE owned_modal_primary_text '
                          'primary_composition_proven=false manual_input_proof=false promotion_ready=false', 1)
    pe._require(all(len(line.encode('ascii')) < 4096 for line in probe.splitlines()), 'loaded probe line exceeds CDB limit')
    return probe, marker


def build_candidate(original: bytes, resolution: str):
    pe._identity(original, pe.ORIGINAL_SHA256, 'original')
    before = {name: sha((ROOT / name).read_bytes()) for name in SOURCES}
    base, context, old_probe = primary.build_candidate(original, resolution)
    pe._require(context['stage'] == primary.STAGE and context['recipe_revision'] == primary.REVISION,
                'exact primary-v1 predecessor required')
    layout = extension.allocation_layout(base)
    width, height = map(int, resolution.split('x'))
    bundle = text.emit_modal_primary_text(original, base, base_va=layout.code_va, width=width, height=height)
    expected = dict(context['source_hashes']) | {SOURCES[0]: before[SOURCES[0]]}
    pe._require(bundle.candidate_sha256 == sha(base) and bundle.source_contract['source_hashes'] == expected,
                'text emitter and reconstructed predecessor context differ')
    pe._require(len(bundle.hook_sites) == 1 and bundle.hook_sites[0].va == text.TEXT_CALL
                and bundle.hook_sites[0].old == bytes.fromhex('e8e594fdff'), 'exact original text CALL replacement required')
    binding = dict(original_sha256=pe.ORIGINAL_SHA256, base_stage=primary.STAGE, stage=STAGE,
                   resolution=resolution, base_candidate_sha256=sha(base), recipe_revision=REVISION)
    result = extension._extend_verified_image(base, code=bundle.code, code_va=bundle.base_va,
        relocations=bundle.relocations, hooks=bundle.hook_sites, binding=binding)
    metadata = dict(result.metadata)
    probe, marker = make_probe(base, result.image, context, old_probe, bundle, metadata)
    sources = dict(context['source_hashes']) | before
    pe._require(sources == {name: sha((ROOT / name).read_bytes()) for name in sources}, 'text source changed during build')
    metadata.update(schema='clash95_framed_modal_primary_text_candidate_v1', candidate_sha256=sha(result.image),
        base_sha256=pe.ORIGINAL_SHA256, source_hashes=sources, base_candidate=context,
        text_entry_vas=bundle.entries, text_contract=bundle.source_contract,
        modal_state_va=bundle.modal_state_va, modal_entry_vas=bundle.modal_entry_vas,
        probe_sha256=sha(probe.encode()), probe_contract=dict(stage=STAGE, text_marker=marker,
            requires_new_stage_consumer=True, predecessor_stage_preserved=primary.STAGE,
            loaded_byte_checks_required=True, inherited_probe_sha256=sha(old_probe.encode())),
        validation_stage_only=True, primary_composition_proven=False,
        limitations=['The text adapter and loaded-byte checks do not prove rendered composition.',
            'Fresh source-bound runtime capture and overlay-aware pixel evaluation remain required.',
            'Ordinary input, castle routes, native exit and promotion remain separate.'])
    return result.image, metadata, probe


def checked_output_path(output: Path):
    output = Path(output)
    if not output.is_absolute():
        raise ValueError('primary-text output must be an absolute path')
    output = output.resolve()
    if (not output.is_relative_to(Path('C:/ClashTests').resolve())
            or output.is_relative_to(ROOT.resolve()) or output.suffix.lower() != '.exe'):
        raise ValueError('primary-text candidate must be a named .exe under C:/ClashTests outside the repository')
    return output


def write_candidate(original: Path, output: Path, resolution: str):
    output = checked_output_path(output)
    paths = (output, output.with_suffix('.candidate.json'), output.with_suffix('.cdb'))
    if any(path.exists() for path in paths):
        raise FileExistsError('primary-text bundle exists; choose a new name')
    image, metadata, probe = build_candidate(Path(original).read_bytes(), resolution)
    output.parent.mkdir(parents=True, exist_ok=True)
    complete._write_bundle(paths, (image, (json.dumps(metadata, indent=2) + '\n').encode(), probe.encode()))
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', required=True, type=Path)
    parser.add_argument('--resolution', required=True, choices=complete.RESOLUTIONS)
    parser.add_argument('--stage', choices=[STAGE], default=STAGE)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args(argv)
    if args.preflight:
        if args.output: parser.error('preflight accepts no output')
        _, metadata, _ = build_candidate(args.original.read_bytes(), args.resolution)
    else:
        if not args.output: parser.error('output is required unless preflight')
        try:
            path = checked_output_path(args.output)
        except ValueError as error:
            parser.error(str(error))
        metadata = write_candidate(args.original, path, args.resolution)
    print(json.dumps({key: metadata[key] for key in ('stage', 'resolution', 'candidate_sha256',
                                                   'runtime_executed', 'promotion_ready')}))
    return 0


if __name__ == '__main__': raise SystemExit(main())
