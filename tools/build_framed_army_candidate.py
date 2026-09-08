#!/usr/bin/env python3
"""Build a distinct source-bound army validation image; never start runtime.

Reconstruct the complete previous modal image, then append the reviewed army
code and install its ten explicit hooks. Shared state is unnecessary. Both
the original and every previous-stage generator remain unchanged.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tools'))
from src.patcher import pe_extension as pe
from src.patcher import pe_army_extension as extension
from src.patcher import framed_army_draw as draw
from src.patcher import framed_army_input as inputs
from src.patcher import framed_army_composition as composition
from build_partial_tile_candidate import make_probe as make_base_probe
from build_framed_modal_candidate import _checked_lines, _outputs

STAGE = extension.STAGE
REVISION = 'framed_own_army_native_size_v1'
# Exact source snapshots for the integration fixtures and candidate builder.
# A successful build is byte integrity evidence; runtime needs the independent
# emitter/loader fixtures and its own source-bound observation protocol.
PINNED_SOURCES = {
    'src/patcher/pe_army_extension.py': '8b2bf19c59351cf1b625b28e143d0ccfd000380898a81af29e28e7cf7af75161',
    'src/patcher/framed_army_viewport.py': '6f091c2655ee47392541b6d15db24346e3c26dc43158942426bc939a1e158224',
    'src/patcher/framed_army_draw.py': 'e6763ae2ebdf038d0b0b574564573fb07e2a2b68c12f7aeafc0b63ca44347cf9',
    'src/patcher/framed_army_input.py': 'c27a0feb17df909dcf9986bfde231d90a79e8c1ad8abbcf2884b52e767a70ee2',
    'src/patcher/framed_army_composition.py': '7639e0b96bfc96d0f9c39b6c17126b376cc40e7ab37407b2a86d72bc626c511c',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_sources():
    for name, expected in PINNED_SOURCES.items():
        pe._identity((ROOT/name).read_bytes(),expected,'reviewed army source '+name)
    return dict(PINNED_SOURCES)


def _initial_probe(candidate, modal_metadata, result_metadata):
    """Authenticate the actual modified image before old initial-map observers.

    The existing observer protocol is used only while no army is selected.
    Separate selection/deselection and input evidence must use the new stage.
    All old/new code, hooks, headers, zero modal state and merged relocations
    are bound here, including modifications within the old .hdcode section.
    """
    old = modal_metadata['base_candidate']
    image = pe.inspect_pe(candidate)
    width,height = map(int,old['resolution'].split('x'))
    code_offset = image.file_offset(old['code_va']-image.image_base,old['extension_payload_size'])
    code = candidate[code_offset:code_offset+old['extension_payload_size']]
    bundle = SimpleNamespace(base_va=old['code_va'],code=code,width=width,height=height,
        entries=old['entry_vas'],status_vas=old['status_vas'],initial_status_vas=old['initial_status_vas'],
        layout_contract=old['layout_contract'],hook_sites=tuple(SimpleNamespace(va=r['va'],offset=r['offset'],
        old_bytes=bytes.fromhex(r['old_hex'])) for r in old['hooks']))
    probe = make_base_probe(candidate,bundle)
    prior = f".echo PTILE_CONTRACT_PASS stage={old['stage']} resolution={width}x{height} candidate_sha256={sha(candidate)}"
    if probe.splitlines().count(prior)!=1:
        raise ValueError('initial-map observer stage contract differs')
    spans = [(image.image_base+s.header_offset,candidate[s.header_offset:s.header_offset+40]) for s in image.sections]
    for s in image.sections:
        if s.name.rstrip(b'\0') in (b'.hdmodal',b'.hdarmy'):
            spans.append((image.image_base+s.rva,candidate[s.raw_offset:s.raw_offset+s.raw_size]))
    spans.append((modal_metadata['state_va'],bytes(modal_metadata['state_bytes'])))
    for row in (*modal_metadata['hooks'],*result_metadata['hooks']):
        spans.append((row['va'],bytes.fromhex(row['new_hex'])))
    # Modal inactive fallback resumes inside these original DGROUP wrappers.
    # Their complete authenticated tails are outside every extension section.
    for row in modal_metadata['authenticated_legacy_continuations']:
        pos = image.file_offset(row['entry_va']-image.image_base,row['span_bytes'])
        spans.append((row['entry_va'],candidate[pos:pos+row['span_bytes']]))
    spans.append((image.image_base+image.optional_offset+136,
                  candidate[image.optional_offset+136:image.optional_offset+144]))
    # Bind the exact active directory independently, even though it resides
    # within the fully checked .hdarmy bytes above.
    pos = image.file_offset(image.relocation_rva,image.relocation_size)
    spans.append((image.image_base+image.relocation_rva,candidate[pos:pos+image.relocation_size]))
    lines = [line.replace('MCANVAS_CONTRACT_FAIL','ARMY_CONTRACT_FAIL') for line in _checked_lines(spans)]
    lines += [f'.echo ARMY_CONTRACT_PASS stage={STAGE} resolution={width}x{height} candidate_sha256={sha(candidate)} revision={REVISION}',
              '.echo ARMY_SCOPE own_player_0_to_3_native_size_panel manual_input_proof=false promotion_ready=false',
              prior.replace(f"stage={old['stage']} ",f'stage={STAGE} ',1)]
    return probe.replace(prior,'\n'.join(lines),1)


def build_candidate(original: bytes,resolution: str,*,minimap_viewport: bool=False):
    sources = verify_sources()
    pe._identity(original,pe.ORIGINAL_SHA256,'original')
    if type(minimap_viewport) is not bool:
        raise ValueError('minimap variant must be explicit boolean')
    base,modal_metadata,base_sources = extension._reconstruct_modal(original,resolution,minimap_viewport)
    allocation = extension.allocation_layout(base,state_bytes=0)
    width,height = map(int,resolution.split('x'))
    mouse = inputs.emit_army_input(original,base,base_va=allocation.code_va,
                                   width=width,height=height,minimap_viewport=minimap_viewport)
    portraits = draw.emit_army_draw(original,base,base_va=mouse.base_va+len(mouse.code),
                                   width=width,height=height,minimap_viewport=minimap_viewport)
    panel = composition.emit_army_composition(original,base,base_va=portraits.base_va+len(portraits.code),
        width=width,height=height,minimap_viewport=minimap_viewport,
        owner_state_va=mouse.entries['owner_state'],draw_army_va=portraits.entries['draw_army'])
    code = mouse.code+portraits.code+panel.code
    relocs = tuple(replace(r,offset=r.offset+b.base_va-allocation.code_va)
                   for b in (mouse,portraits,panel) for r in b.relocations)
    hooks = list(mouse.hook_sites)+list(panel.hook_sites)
    for site in portraits.hook_sites:
        target = site.va+5+struct.unpack_from('<i',site.new_bytes,1)[0]
        hooks.append(pe.HookPatch(site.offset,site.rva,site.va,site.old_bytes,site.new_bytes,
                                  site.name,(pe.CodeRelocation(1,'rel32',target,site.name),)))
    if len(hooks)!=10 or len({s.va for s in hooks})!=10:
        raise ValueError('army integration requires ten distinct hooks')
    removed = tuple(va-0x400000 for va in mouse.removed_highlow_vas)+panel.removed_highlow_rvas
    result = extension.extend_modal_candidate_with_army(original,base,expected_candidate_sha256=sha(base),
        resolution=resolution,minimap_viewport=minimap_viewport,validation_stage=STAGE,
        code=code,code_va=allocation.code_va,state_va=None,state_bytes=0,
        relocations=relocs,hooks=tuple(hooks),removed_highlow_rvas=removed)
    probe = _initial_probe(result.image,modal_metadata,result.metadata)
    metadata = dict(result.metadata)
    metadata.update(schema='clash95_framed_army_candidate_v1',generated_at=datetime.now(timezone.utc).isoformat(),
        source_sha256=base_sources|sources,builder_sha256=sha(Path(__file__).read_bytes()),
        base_candidate=modal_metadata,army_revision=REVISION,
        army_entry_vas={prefix+'.'+name:va for prefix,b in (('input',mouse),('draw',portraits),('composition',panel))
                        for name,va in b.entries.items()},
        army_contracts={prefix:b.source_contract for prefix,b in (('input',mouse),('draw',portraits),('composition',panel))},
        initial_probe_sha256=sha(probe.encode()),initial_probe_contract=dict(stage=STAGE,
            requires_new_stage_consumer=True,scope='unchanged initial ordinary map observer protocol only'),
        validation_stage_only=True,installation_ready=False,runtime_executed=False,
        manual_input_proof=False,promotion_ready=False)
    verify_sources()
    return result.image,metadata,probe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original',required=True,type=Path)
    parser.add_argument('--resolution',required=True)
    parser.add_argument('--minimap-viewport',action='store_true')
    parser.add_argument('--preflight',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--report-json',type=Path)
    parser.add_argument('--probe-out',type=Path)
    args = parser.parse_args()
    if args.preflight and any((args.output,args.report_json,args.probe_out)):
        parser.error('preflight accepts no output paths')
    paths = [] if args.preflight else _outputs(args,parser)
    candidate,metadata,probe = build_candidate(args.original.read_bytes(),args.resolution,
                                               minimap_viewport=args.minimap_viewport)
    if args.preflight:
        print(json.dumps(dict(stage=STAGE,candidate_sha256=sha(candidate),resolution=args.resolution,
                              preflight_passed=True,runtime_executed=False,promotion_ready=False)))
        return 0
    for path in paths:
        path.parent.mkdir(parents=True,exist_ok=True)
    with ExitStack() as stack:
        streams = [stack.enter_context(path.open('xb')) for path in paths]
        for stream,data in zip(streams,(candidate,(json.dumps(metadata,indent=2)+'\n').encode(),probe.encode())):
            stream.write(data)
    print(json.dumps(dict(stage=STAGE,candidate_sha256=sha(candidate),output=str(paths[0]),
                          runtime_executed=False,promotion_ready=False)))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
