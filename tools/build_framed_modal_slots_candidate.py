#!/usr/bin/env python3
"""Build a distinct slots-validation bundle outside the repo, without runtime.

The complete-HD v1 builder, bytes, source snapshots and probe stay unchanged.
This exact new stage needs a new-stage consumer; its probe never emits a v1
candidate pass marker for modified bytes.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
from src.patcher import complete_hd_candidate as complete
from src.patcher import framed_modal_slots as slots
from src.patcher import pe_modal_slots_extension as extension
from src.patcher import pe_extension as pe
import build_framed_army_candidate as army
from build_framed_modal_candidate import _checked_lines

STAGE=slots.STAGE
REVISION=slots.REVISION
SOURCES=('src/patcher/framed_modal_slots.py','src/patcher/pe_modal_slots_extension.py',
         'tools/build_framed_modal_slots_candidate.py')


def sha(data):return hashlib.sha256(data).hexdigest()


def make_probe(candidate,base_context,bundle,metadata):
    predecessor=base_context['predecessor']
    probe=army._initial_probe(candidate,predecessor['base_candidate'],predecessor)
    old=f'.echo ARMY_CONTRACT_PASS stage={army.STAGE} resolution={metadata["resolution"]} candidate_sha256={sha(candidate)} revision={army.REVISION}'
    if probe.splitlines().count(old)!=1:raise ValueError('army observer contract differs')
    view=pe.inspect_pe(candidate);section=view.sections[-1]
    spans=[(view.image_base+section.rva,candidate[section.raw_offset:section.raw_offset+section.raw_size])]
    for va,length in ((0x432940,1006),(0x4024E0,867)):
        offset=view.file_offset(va-view.image_base,length)
        spans.append((va,candidate[offset:offset+length]))
    checks=[line.replace('MCANVAS_CONTRACT_FAIL','SLOTS_CONTRACT_FAIL') for line in _checked_lines(spans)]
    marker=f'.echo SLOTS_CONTRACT_PASS stage={STAGE} resolution={metadata["resolution"]} candidate_sha256={sha(candidate)} revision={REVISION}'
    checks.extend((marker,'.echo SLOTS_SCOPE owned_barracks_dirty_slots primary_composition_proven=false manual_input_proof=false promotion_ready=false'))
    probe=probe.replace(old,'\n'.join(checks),1)
    ptile=f'.echo PTILE_CONTRACT_PASS stage={army.STAGE} resolution={metadata["resolution"]} candidate_sha256={sha(candidate)}'
    if probe.splitlines().count(ptile)!=1:raise ValueError('partial-tile observer contract differs')
    return probe.replace(ptile,ptile.replace(f'stage={army.STAGE} ',f'stage={STAGE} ',1),1)


def build_candidate(original: bytes,resolution: str):
    before={name:sha((ROOT/name).read_bytes()) for name in SOURCES}
    base,context,_=complete.build_candidate(original,resolution)
    if context['recipe_revision']!='complete_hd_v1':raise ValueError('frozen complete v1 predecessor required')
    layout=extension.allocation_layout(base);width,height=map(int,resolution.split('x'))
    bundle=slots.emit_modal_slots(original,base,base_va=layout.code_va,width=width,height=height)
    if bundle.candidate_sha256!=context['candidate_sha256'] or bundle.source_contract['source_hashes']!=context['source_hashes']:
        raise ValueError('slot emitter and reconstructed predecessor context differ')
    binding=dict(original_sha256=pe.ORIGINAL_SHA256,base_stage=complete.STAGE,stage=STAGE,
                 resolution=resolution,base_candidate_sha256=sha(base),recipe_revision=REVISION)
    result=extension._extend_verified_image(base,code=bundle.code,code_va=bundle.base_va,
        relocations=bundle.relocations,hooks=bundle.hook_sites,binding=binding)
    metadata=dict(result.metadata)
    probe=make_probe(result.image,context,bundle,metadata)
    sources=dict(context['source_hashes'])|before
    if sources!={name:sha((ROOT/name).read_bytes()) for name in sources}:
        raise ValueError('slots source changed during build')
    metadata.update(schema='clash95_framed_modal_slots_candidate_v1',candidate_sha256=sha(result.image),
        base_sha256=pe.ORIGINAL_SHA256,source_hashes=sources,base_candidate=context,
        slot_entry_vas=bundle.entries,slot_contract=bundle.source_contract,
        modal_state_va=bundle.modal_state_va,modal_active_va=bundle.modal_active_va,
        probe_sha256=sha(probe.encode()),probe_contract=dict(stage=STAGE,requires_new_stage_consumer=True,
            predecessor_stage_preserved=complete.STAGE,loaded_byte_checks_required=True,
            slot_marker=f'SLOTS_CONTRACT_PASS stage={STAGE} resolution={resolution} candidate_sha256={sha(result.image)} revision={REVISION}'),
        validation_stage_only=True,primary_composition_proven=False,
        limitations=['Synthetic ABI and PE admission do not establish native primary composition.',
                    'Court, recruitment, peasants, input, modal return and promotion need separate evidence.'])
    return result.image,metadata,probe


def write_candidate(original: Path,output: Path,resolution: str):
    output=Path(output).resolve()
    if not output.is_relative_to(Path('C:/ClashTests').resolve()) or output.suffix.lower()!='.exe':
        raise ValueError('slots candidate must be a named .exe under C:/ClashTests')
    paths=(output,output.with_suffix('.candidate.json'),output.with_suffix('.cdb'))
    if any(path.exists() for path in paths):raise FileExistsError('slots bundle exists; choose a new name')
    image,metadata,probe=build_candidate(Path(original).read_bytes(),resolution)
    output.parent.mkdir(parents=True,exist_ok=True)
    complete._write_bundle(paths,(image,(json.dumps(metadata,indent=2)+'\n').encode(),probe.encode()))
    return metadata


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original',required=True,type=Path)
    parser.add_argument('--resolution',required=True,choices=complete.RESOLUTIONS)
    parser.add_argument('--stage',choices=[STAGE],default=STAGE)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--preflight',action='store_true')
    args=parser.parse_args(argv)
    if args.preflight:
        if args.output:parser.error('preflight accepts no output')
        _,metadata,_=build_candidate(args.original.read_bytes(),args.resolution)
    else:
        if not args.output:parser.error('output is required unless preflight')
        # Reject protected/relative/repository destinations before building.
        path=args.output.resolve()
        if path.suffix.lower()!='.exe' or not path.is_relative_to(Path('C:/ClashTests').resolve()):
            parser.error('output must be a named .exe under C:/ClashTests')
        metadata=write_candidate(args.original,path,args.resolution)
    print(json.dumps({k:metadata[k] for k in ('stage','resolution','candidate_sha256','runtime_executed','promotion_ready')}))
    return 0


if __name__=='__main__':raise SystemExit(main())
