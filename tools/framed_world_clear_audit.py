#!/usr/bin/env python3
"""Audit declared before/after clearing pixels; never infer runtime provenance.

The source-bound complete candidate supplies geometry and the exact indexed
clear value. A pair with matching bytes can pass the pixel contract only. The
current normal capture recipe rejects out-of-world ceiling cells; in particular
it cannot capture small worlds safely. No runtime/release acceptance is emitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import complete_hd_runtime_context as complete_context
from src.patcher import framed_viewport as geometry
from src.patcher import partial_tile_clip as clipping

SCHEMA='clash95_framed_world_clear_pair_v1'
CLEAR_INDEX=1
VISIBILITY_BYTES=100*13
PAIR_KEYS={'schema','candidate','geometry_sha256','world','scroll','surface_format','before','after','visibility'}
IDENTITY_KEYS={'stage','resolution','candidate_sha256','base_sha256','recipe_revision','probe_sha256','manifest_sha256'}
SURFACE_FORMAT='indexed8-packed-terrain-before-overlays'
LIMITS=[
    'A pixel-contract pass checks the supplied pair; it does not authenticate when, where or by which process the pixels or visibility bytes were captured.',
    'The current normal hidden capture recipe rejects out-of-world ceiling windows. No supported native small-world capture recipe is supplied by this helper.',
    'Complete-v1 does not admit small worlds to its native full loop. Describing their geometry or passing synthetic pixels does not change candidate support.',
    'All terrain pixels must precede overlay composition. No arbitrary masks are accepted; this surface phase is a declaration, not an observed ownership proof.',
    'Every outside-world cell needs a non-clear-to-index-1 witness. Already clear cells cannot demonstrate clearing.',
    'Visible blank detection is limited to cells containing only indexed values 0/1. It is not a terrain artwork/detail oracle.',
    'Before/after equality at the four frame bands checks write containment only, not correct frame artwork or action controls.',
    'No normal gameplay, native transition, input, cleanup, continuity, endurance or release acceptance is established.'
]


def sha(data):return hashlib.sha256(data).hexdigest()
def require(condition,message):
    if not condition:raise ValueError(message)
def reference(path):
    path=Path(path).resolve()
    return dict(path=str(path),sha256=sha(path.read_bytes()))
def read_json(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def clear_contract(context):
    """Bind palette index 1 to the reconstructed candidate's actual fill call."""
    manifest=context['manifest']
    require(manifest['stage']==complete_context.complete.STAGE,'only the exact complete candidate is supported')
    sources={}
    for module in (geometry,clipping):
        path=Path(module.__file__).resolve();name=path.relative_to(ROOT).as_posix()
        sources[name]=reference(path)
        require(manifest['source_hashes'][name]==sources[name]['sha256'],'candidate geometry/clear source differs')
    # edge.clear loads the source surface and rectangle, preserves EBP, pushes
    # the native fill color, then bottom. The following CALL reaches fill.
    prefix=bytes.fromhex('8b45fc8b55f08b4de88b5dec556a')
    suffix=bytes.fromhex('ff75e4e8')
    image=context['candidate'];positions=[];offset=0
    require(sha(image)==manifest['candidate_sha256'],'candidate bytes differ from the reconstructed identity')
    while (offset:=image.find(prefix,offset))!=-1:
        value_at=offset+len(prefix)
        if image[value_at+1:value_at+1+len(suffix)]==suffix:positions.append((offset,image[value_at]))
        offset+=1
    require(len(positions)==1 and positions[0][1]==CLEAR_INDEX,'candidate lacks one exact index-1 edge clear call')
    return dict(clear_index=CLEAR_INDEX,candidate_file_offset=positions[0][0],
                source_bytes=(prefix+bytes([CLEAR_INDEX])+suffix).hex(),sources=sources)


def audit_pixels(before: bytes,after: bytes,visibility: bytes,view: geometry.WorldView):
    """Pure framed geometry/pixel oracle, with no caller-authored success flags."""
    require(isinstance(view,geometry.WorldView),'world view must use the framed geometry contract')
    require(all(type(data) is bytes for data in (before,after,visibility)),'packed pixel/visibility inputs must be bytes')
    layout=view.layout;size=layout.width*layout.height
    require(len(before)==len(after)==size,'packed surface byte length differs from framed resolution')
    require(len(visibility)==VISIBILITY_BYTES,'visibility must contain the complete 100-column, 13-byte player bitmap')
    result=dict(pixel_contract_passed=False,clear_index=CLEAR_INDEX,nonclear_pixels_remaining=0,
        unchanged_nonclear_pixels=0,changed_to_clear_pixels=0,outside_world_cells=0,
        outside_world_full_cells=0,outside_world_partial_cells=0,unwitnessed_outside_world_cells=[],
        unexplained_visible_blank_cells=[],zero_visibility_blank_cells=[],
        border_changed_pixels=0,cells=[],failures=[],runtime_acceptance=False,release_eligible=False)
    for cell in view.cells():
        rect=cell.rect
        indices=[y*layout.width+x for y in range(rect.top,rect.bottom+1) for x in range(rect.left,rect.right+1)]
        actual=bytes(after[i] for i in indices)
        row=dict(id=f'r{cell.row}c{cell.column}',world=[cell.world_x,cell.world_y],
                 rectangle=list(rect.as_tuple()),in_world=cell.in_world,partial=cell.partial,pixels=rect.area)
        if cell.in_world:
            address=cell.world_x*13+(cell.world_y>>3)
            native_visible=bool(visibility[address]&(1<<(cell.world_y&7)))
            blank=all(value in (0,CLEAR_INDEX) for value in actual)
            row.update(visibility_byte_offset=address,native_visible=native_visible,blank=blank)
            if blank:
                key='unexplained_visible_blank_cells' if native_visible else 'zero_visibility_blank_cells'
                result[key].append(row['id'])
        else:
            remaining=sum(value!=CLEAR_INDEX for value in actual)
            stale=sum(before[i]==after[i] and after[i]!=CLEAR_INDEX for i in indices)
            changed=sum(before[i]!=CLEAR_INDEX and after[i]==CLEAR_INDEX for i in indices)
            result['outside_world_cells']+=1
            result['outside_world_partial_cells' if cell.partial else 'outside_world_full_cells']+=1
            result['nonclear_pixels_remaining']+=remaining
            result['unchanged_nonclear_pixels']+=stale
            result['changed_to_clear_pixels']+=changed
            row.update(nonclear_pixels_remaining=remaining,unchanged_nonclear_pixels=stale,changed_to_clear_pixels=changed)
            if not changed:result['unwitnessed_outside_world_cells'].append(row['id'])
        result['cells'].append(row)
    for band in layout.frame_bands:
        result['border_changed_pixels']+=sum(before[y*layout.width+x]!=after[y*layout.width+x]
            for y in range(band.top,band.bottom+1) for x in range(band.left,band.right+1))
    for failed,reason in (
        (not result['outside_world_cells'],'no outside-world clearing cells are present'),
        (bool(result['nonclear_pixels_remaining']),'outside-world pixels differ from source clear index 1'),
        (bool(result['unchanged_nonclear_pixels']),'outside-world stale non-clear pixels remain unchanged'),
        (bool(result['unwitnessed_outside_world_cells']),'outside-world cells lack a non-clear-to-clear witness'),
        (bool(result['unexplained_visible_blank_cells']),'in-world visible cells contain unexplained blank pixels'),
        (bool(result['border_changed_pixels']),'clearing pair changes pixels in the four frame bands')):
        if failed:result['failures'].append(reason)
    result['pixel_contract_passed']=not result['failures']
    return result


def _artifact(value,root):
    require(type(value) is dict and set(value)=={'path','sha256'},'raw artifact requires exact path/hash fields')
    path=Path(value['path'])
    require(path.is_absolute() and path.resolve().parent==root,'raw artifact must be local to the pair manifest')
    actual=reference(path)
    require(value==actual,'raw artifact path/hash differs from actual bytes')
    return path.resolve(),actual


def build_report(pair_manifest,candidate_manifest,original):
    report=dict(schema='clash95_framed_world_clear_diagnostic_v1',pixel_contract_passed=False,
        diagnostic_only=True,observation_authenticity='unverified_declared_pair',
        runtime_executed=False,runtime_acceptance=False,release_eligible=False,promotion_ready=False,
        native_capture_recipe_available=False,limits=LIMITS,sources={},failures=[])
    try:
        path=Path(pair_manifest).resolve()
        # Reconstruction can take time. Bind the input bytes before parsing or
        # rebuilding, never the replacement bytes of a manifest changed later.
        sources={'pair_manifest':reference(path),'candidate_manifest':reference(candidate_manifest),'original':reference(original)}
        report['sources']=sources
        pair=read_json(path)
        require(set(pair)==PAIR_KEYS and pair['schema']==SCHEMA,'unsupported clearing pair schema/fields')
        require(pair['surface_format']==SURFACE_FORMAT,'clearing requires packed indexed terrain before overlays')
        context=complete_context.load_context(candidate_manifest,original,resolution=read_json(candidate_manifest)['resolution'])
        manifest=context['manifest'];contract=clear_contract(context)
        identity={key:manifest[key] for key in IDENTITY_KEYS if key!='manifest_sha256'}
        identity['manifest_sha256']=sources['candidate_manifest']['sha256']
        require(pair['candidate']==identity,'pair candidate/stage/resolution/recipe/probe identity differs')
        require(pair['geometry_sha256']==sha(Path(geometry.__file__).read_bytes()),'pair framed geometry source differs')
        layout=geometry.FramedViewport(*map(int,manifest['resolution'].split('x')))
        require(all(type(pair[key]) is list and len(pair[key])==2 for key in ('world','scroll')),'world/scroll require exact coordinate pairs')
        view=layout.world_view(*pair['world'],*pair['scroll'])
        files=[]
        for key in ('before','after','visibility'):
            artifact,ref=_artifact(pair[key],path.parent);files.append(artifact);sources[key]=ref
        require(len(set(files))==3,'before/after/visibility require distinct artifact files')
        sources.update(contract['sources']);report['sources']=sources
        pixels=audit_pixels(*(item.read_bytes() for item in files),view)
        report.update(candidate_context=identity,clear_contract=contract,
            geometry=dict(terrain=list(layout.terrain.as_tuple()),world=pair['world'],scroll=pair['scroll'],
                ceiling_tiles=list(layout.ceil_tiles),full_tiles=list(layout.full_tiles),
                native_full_loop_safe=view.native_full_loop_safe),
            complete_candidate_small_world_supported=False,pixel_audit=pixels,
            pixel_contract_passed=pixels['pixel_contract_passed'],failures=pixels['failures'])
        for source in sources.values():require(reference(source['path'])==source,'input source changed during audit')
    except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError) as error:
        report['pixel_contract_passed']=False;report['failures'].append(str(error))
    report['evaluator_source']=reference(__file__)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('pair-manifest','candidate-manifest','original','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('output already exists; preserve every earlier result')
    report=build_report(args.pair_manifest,args.candidate_manifest,args.original)
    with args.output.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps({key:report[key] for key in ('pixel_contract_passed','runtime_acceptance','release_eligible','failures')}))
    # A diagnostic can complete with exit zero; its result is explicitly not a
    # release decision and is never registered as a release evidence adapter.
    return 0 if report['pixel_contract_passed'] else 2


if __name__=='__main__':raise SystemExit(main())
