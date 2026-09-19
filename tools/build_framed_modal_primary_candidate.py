#!/usr/bin/env python3
"""Build an experimental owned-modal primary bundle outside the repository.

This new stage has its own loaded-byte probe. Existing complete/slots recipes,
consumers and retained runtime receipts keep their original meaning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tools'))
from src.patcher import complete_hd_candidate as complete
from src.patcher import framed_modal_primary as primary
from src.patcher import pe_modal_primary_extension as extension
from src.patcher import pe_extension as pe
import build_framed_army_candidate as army
import build_framed_modal_slots_candidate as slots
from build_framed_modal_candidate import _checked_lines

STAGE, REVISION = primary.STAGE, primary.REVISION
SOURCES = ('src/patcher/framed_modal_primary.py', 'src/patcher/pe_modal_primary_extension.py',
           'tools/build_framed_modal_primary_candidate.py')


def sha(data): return hashlib.sha256(data).hexdigest()


def make_probe(candidate, slots_context, bundle, metadata):
    inherited = slots_context['base_candidate']['predecessor']
    # One inherited hook is deliberately replaced by this new stage. Adapt
    # its initial-image predicate in a private copy only after exact old/new
    # bytes and span have been authenticated; retain original metadata intact.
    view = pe.inspect_pe(candidate)
    modal = dict(inherited['base_candidate'])
    modal['hooks'] = [dict(row) for row in modal['hooks']]
    replaced = []
    for row in modal['hooks']:
        prior = bytes.fromhex(row['new_hex'])
        for hook in bundle.hook_sites:
            if max(row['va'], hook.va) >= min(row['va'] + len(prior), hook.va + len(hook.old)):
                continue
            if row['va'] != primary.FULL_BLIT or row['va'] != hook.va or prior != hook.old:
                raise ValueError('unsupported inherited hook overlap')
            off = view.file_offset(hook.va - view.image_base, len(hook.new))
            if candidate[off:off + len(hook.new)] != hook.new:
                raise ValueError('final inherited hook bytes differ')
            row['new_hex'] = hook.new.hex()
            replaced.append(hook.va)
    if replaced != [primary.FULL_BLIT]:
        raise ValueError('exact inherited full-blit replacement required')
    probe = army._initial_probe(candidate, modal, inherited)
    old = (f'.echo ARMY_CONTRACT_PASS stage={army.STAGE} resolution={metadata["resolution"]} '
           f'candidate_sha256={sha(candidate)} revision={army.REVISION}')
    if probe.splitlines().count(old) != 1:
        raise ValueError('inherited army contract marker differs')
    spans = [(view.image_base + s.rva, candidate[s.raw_offset:s.raw_offset + s.raw_size])
             for s in view.sections[-2:]]
    # Bind both the retained slot producer and the new primary/cursor native
    # bodies. Bytes are read from the actual final image, including our hooks.
    for va, size in ([(0x432940, 1006), (primary.HD_BLIT, 96)]
                     + [(v, n) for v, n, _ in primary.NATIVE_SPANS + primary.CURSOR_CONTEXT_SPANS]
                     + [(v, 12) for v in primary.CURSOR_DESCRIPTORS]):
        off = view.file_offset(va - view.image_base, size)
        spans.append((va, candidate[off:off + size]))
    spans.extend((h.va, h.new) for h in bundle.hook_sites)
    # Like inherited zero-state predicates, this is an initial-image check,
    # before the native cursor initializer fills its mutable BSS geometry.
    spans.append((primary.CURSOR_STARTUP_DESCRIPTOR, bytes(12)))
    checks = [line.replace('MCANVAS_CONTRACT_FAIL', 'MPRIMARY_CONTRACT_FAIL')
              for line in _checked_lines(spans)]
    marker = (f'.echo MPRIMARY_CONTRACT_PASS stage={STAGE} resolution={metadata["resolution"]} '
              f'candidate_sha256={sha(candidate)} revision={REVISION}')
    checks.extend((marker, '.echo MPRIMARY_SCOPE owned_modal_primary primary_composition_proven=false '
                   'manual_input_proof=false promotion_ready=false'))
    probe = probe.replace(old, '\n'.join(checks), 1)
    ptile = (f'.echo PTILE_CONTRACT_PASS stage={army.STAGE} resolution={metadata["resolution"]} '
             f'candidate_sha256={sha(candidate)}')
    if probe.splitlines().count(ptile) != 1:
        raise ValueError('inherited partial-tile contract marker differs')
    return probe.replace(ptile, ptile.replace(f'stage={army.STAGE} ', f'stage={STAGE} ', 1), 1)


def build_candidate(original: bytes, resolution: str):
    before = {name: sha((ROOT / name).read_bytes()) for name in SOURCES}
    base, context, _ = slots.build_candidate(original, resolution)
    if context['recipe_revision'] != slots.REVISION:
        raise ValueError('exact slots predecessor revision required')
    layout = extension.allocation_layout(base)
    width, height = map(int, resolution.split('x'))
    bundle = primary.emit_modal_primary(original, base, base_va=layout.code_va, width=width, height=height)
    expected = dict(context['source_hashes']) | {'src/patcher/framed_modal_primary.py': before['src/patcher/framed_modal_primary.py']}
    if bundle.candidate_sha256 != sha(base) or bundle.source_contract['source_hashes'] != expected:
        raise ValueError('primary emitter and reconstructed predecessor context differ')
    binding = dict(original_sha256=pe.ORIGINAL_SHA256, base_stage=slots.STAGE, stage=STAGE,
                   resolution=resolution, base_candidate_sha256=sha(base), recipe_revision=REVISION)
    result = extension._extend_verified_image(base, code=bundle.code, code_va=bundle.base_va,
        relocations=bundle.relocations, hooks=bundle.hook_sites, binding=binding)
    metadata = dict(result.metadata)
    probe = make_probe(result.image, context, bundle, metadata)
    sources = dict(context['source_hashes']) | before
    if sources != {name: sha((ROOT / name).read_bytes()) for name in sources}:
        raise ValueError('primary source changed during build')
    metadata.update(schema='clash95_framed_modal_primary_candidate_v1', candidate_sha256=sha(result.image),
        base_sha256=pe.ORIGINAL_SHA256, source_hashes=sources, base_candidate=context,
        primary_entry_vas=bundle.entries, primary_contract=bundle.source_contract,
        modal_state_va=bundle.modal_state_va, modal_entry_vas=bundle.modal_entry_vas,
        probe_sha256=sha(probe.encode()), probe_contract=dict(stage=STAGE,
            requires_new_stage_consumer=True, predecessor_stage_preserved=slots.STAGE,
            loaded_byte_checks_required=True,
            primary_marker=f'MPRIMARY_CONTRACT_PASS stage={STAGE} resolution={resolution} '
                           f'candidate_sha256={sha(result.image)} revision={REVISION}'),
        validation_stage_only=True, primary_composition_proven=False,
        limitations=['Emitted x86 and PE validation do not establish actual primary composition.',
            'A source-bound primary-stage runtime consumer and fresh captures remain required.',
            'Ordinary input, all castle routes, native exit, wider battle and promotion remain separate.'])
    return result.image, metadata, probe


def write_candidate(original: Path, output: Path, resolution: str):
    output = Path(output).resolve()
    if not output.is_relative_to(Path('C:/ClashTests').resolve()) or output.suffix.lower() != '.exe':
        raise ValueError('primary candidate must be a named .exe under C:/ClashTests')
    paths = (output, output.with_suffix('.candidate.json'), output.with_suffix('.cdb'))
    if any(p.exists() for p in paths):
        raise FileExistsError('primary bundle exists; choose a new name')
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
        path = args.output.resolve()
        if path.suffix.lower() != '.exe' or not path.is_relative_to(Path('C:/ClashTests').resolve()):
            parser.error('output must be a named .exe under C:/ClashTests')
        metadata = write_candidate(args.original, path, args.resolution)
    print(json.dumps({k: metadata[k] for k in ('stage', 'resolution', 'candidate_sha256',
                                            'runtime_executed', 'promotion_ready')}))
    return 0


if __name__ == '__main__': raise SystemExit(main())
