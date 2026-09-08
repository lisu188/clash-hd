#!/usr/bin/env python3
"""Compare two captured index buffers; no renderer, process or file mutation.

This oracle checks a 640x480 row-major source centered in a physical buffer,
with palette index zero everywhere outside. It does not import the emitter or
derive expected pixels from its code. Matching indices do not establish RGB
palette correctness, artwork, complete modal layers, controls or promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

STAGE = ("gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
         "presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-"
         "framed-modalcanvas-validation")
RESOLUTIONS = frozenset(((800,600),(1024,768),(1280,720),(1280,960),(1920,1080),(802,602)))
NATIVE_WIDTH, NATIVE_HEIGHT = 640, 480
NATIVE_BYTES = 307200
LIMITS = [
    "This is an indexed-buffer mirror relation only; correct artwork and complete modal composition are not established.",
    "Margins require palette index zero; the palette must be separately bound before describing its final RGB color.",
    "Native content-bearing means at least two distinct indices, including a nonzero index; it is not artwork recognition.",
    "The caller must independently bind both buffers to the same paused runtime, candidate, route and source-owned state.",
    "No runtime, native exit cleanup, visible/manual input, controls or promotion proof is supplied by this pure comparison.",
]


def audit_mirror(native: bytes, physical: bytes, *, width: int, height: int,
                 stage: str, coordinate_limit: int = 16) -> dict:
    """Return exact counts and at most64 mismatch coordinates, never images.

    Invalid inputs fail with unknown comparison counts. An all-zero source
    and all-zero destination can pass the mirror relation while the separate
    native_content_bearing flag remains false and visual_proof stays false.
    """
    failures=[]
    report=dict(schema="framed_modal_mirror_audit_v1",stage=stage,width=width,height=height,
        input_valid=False,passed=False,mirror_relation_passed=False,
        native_size=[NATIVE_WIDTH,NATIVE_HEIGHT],native_rect_in_physical=None,
        native_sha256=None,physical_sha256=None,native_bytes=None,physical_bytes=None,
        counts=None,mismatch_coordinates=[],coordinate_limit=coordinate_limit,
        native_content=None,native_content_bearing=False,
        runtime_binding_verified=False,visual_proof=False,controls_proof=False,
        manual_input_proof=False,promotion_ready=False,failures=failures,limits=LIMITS)
    if stage!=STAGE:failures.append("exact framed-modalcanvas validation stage required")
    dimensions_valid=(type(width) is int and type(height) is int and (width,height) in RESOLUTIONS)
    if not dimensions_valid:failures.append("one of the six supported physical resolutions is required")
    if type(coordinate_limit) is not int or not 0<=coordinate_limit<=64:
        failures.append("coordinate_limit must be an integer from0 through64")
    for name,value in (("native",native),("physical",physical)):
        if type(value) is not bytes:
            failures.append(f"{name} must be an immutable bytes buffer")
        else:
            report[name+"_sha256"]=hashlib.sha256(value).hexdigest()
            report[name+"_bytes"]=len(value)
    if type(native) is bytes and len(native)!=NATIVE_BYTES:
        failures.append("native buffer must contain exactly640x480 one-byte indices")
    if dimensions_valid and type(physical) is bytes and len(physical)!=width*height:
        failures.append("physical buffer length must equal physical width times height")
    if failures:return report

    report["input_valid"]=True
    left,top=(width-NATIVE_WIDTH)//2,(height-NATIVE_HEIGHT)//2
    right,bottom=left+NATIVE_WIDTH-1,top+NATIVE_HEIGHT-1
    report["native_rect_in_physical"]=[left,top,right,bottom]
    distinct=len(set(native));nonzero=NATIVE_BYTES-native.count(0)
    report["native_content"]=dict(distinct_indices=distinct,nonzero_pixels=nonzero,
                                  all_zero=nonzero==0,has_variation=distinct>1)
    report["native_content_bearing"]=distinct>1 and nonzero>0
    copy_mismatches=margin_mismatches=0
    samples=report["mismatch_coordinates"]
    def sample(x,y,expected,observed,region):
        if len(samples)<coordinate_limit:
            value=dict(x=x,y=y,expected_index=expected,observed_index=observed,region=region)
            if region=="native_copy":value.update(native_x=x-left,native_y=y-top)
            samples.append(value)
    def margin(start,end,y,x):
        data=physical[start:end]
        count=len(data)-data.count(0)
        if count and len(samples)<coordinate_limit:
            for offset,value in enumerate(data):
                if value:sample(x+offset,y,0,value,"margin")
                if len(samples)>=coordinate_limit:break
        return count
    # Physical row order makes coordinate samples deterministic. Source rows
    # always use640 stride; physical rows always use the supplied width.
    for y in range(height):
        start=y*width
        if y<top or y>bottom:
            margin_mismatches+=margin(start,start+width,y,0)
            continue
        margin_mismatches+=margin(start,start+left,y,0)
        source_start=(y-top)*NATIVE_WIDTH
        expected=native[source_start:source_start+NATIVE_WIDTH]
        observed=physical[start+left:start+right+1]
        if observed!=expected:
            for x,(a,b) in enumerate(zip(expected,observed)):
                if a!=b:
                    copy_mismatches+=1
                    sample(left+x,y,a,b,"native_copy")
        margin_mismatches+=margin(start+right+1,start+width,y,right+1)
    report["counts"]=dict(native_pixels_compared=NATIVE_BYTES,
        native_pixels_matched=NATIVE_BYTES-copy_mismatches,native_copy_mismatches=copy_mismatches,
        margin_pixels_compared=width*height-NATIVE_BYTES,
        margin_pixels_zero=width*height-NATIVE_BYTES-margin_mismatches,
        margin_nonzero_pixels=margin_mismatches,total_mismatches=copy_mismatches+margin_mismatches)
    if copy_mismatches:failures.append(f"{copy_mismatches} centered native-copy indices differ")
    if margin_mismatches:failures.append(f"{margin_mismatches} margin indices are nonzero")
    report["mirror_relation_passed"]=report["passed"]=not failures
    return report


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native',type=Path,required=True)
    parser.add_argument('--physical',type=Path,required=True)
    parser.add_argument('--resolution',required=True)
    parser.add_argument('--stage',required=True)
    parser.add_argument('--coordinate-limit',type=int,default=16)
    args=parser.parse_args()
    match=re.fullmatch(r'([1-9][0-9]{2,3})x([1-9][0-9]{2,3})',args.resolution)
    try:
        if not match:raise ValueError('resolution must be canonical WIDTHxHEIGHT')
        width,height=map(int,match.groups())
        result=audit_mirror(args.native.read_bytes(),args.physical.read_bytes(),width=width,height=height,
                            stage=args.stage,coordinate_limit=args.coordinate_limit)
        result['inputs']=dict(native_path=str(args.native.resolve()),physical_path=str(args.physical.resolve()))
    except (OSError,ValueError) as exc:
        result=dict(schema='framed_modal_mirror_audit_v1',passed=False,mirror_relation_passed=False,
                    input_valid=False,counts=None,failures=[str(exc)],visual_proof=False,
                    controls_proof=False,manual_input_proof=False,promotion_ready=False,limits=LIMITS)
    print(json.dumps(result,indent=2))
    return 0 if result['passed'] else 2


if __name__=='__main__':raise SystemExit(main())
