#!/usr/bin/env python3
"""Source-bound framed gameplay evidence; preserve all input runtime verdicts.

Read existing artifacts and reconstruct candidate/probe/coverage in memory.
Only an exclusive new JSON output may be written. A guarded gameplay result
does not change the original runtime/coverage verdict or establish cleanup,
visible composition, manual input, endurance, or promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import action_bar_surface_audit as bar
import build_framed_candidate as builder
import frame_surface_audit as frame
import initial_map_paint_trace as trace
import map_tile_coverage as coverage
import visibility_coverage as visibility
import complete_hd_runtime_context as complete_context
import framed_minimap_probe as minimap_probe
import complete_hd_main_probe as main_probe
from src.patcher.framed_viewport import FramedViewport

STAGE=bar.FRAMED_STAGE
PRODUCER_SOURCES=("scripts/cdb/run_cdb_surface_dump.ps1","tools/render_cdb_surface_probe.py",
    "tools/initial_map_paint_trace.py","tools/map_tile_coverage.py","tools/cdb_surface_dump_to_png.py",
    "probes/cdb/render/clash95_surface_dump_probe.cdb")
COMPLETE_PRODUCER_SOURCES=("tools/complete_hd_runtime_context.py","tools/complete_hd_evidence.py",
                          "tools/framed_minimap_probe.py")
H=r"[0-9a-fA-F]{1,8}"
READY=re.compile(rf"SURFDUMP_READY redraw_seq=(\d+) surface=({H}) size=\((\d+),(\d+)\) base=({H}) bytes=(\d+)")
REDRAW=re.compile(rf"SURFDUMP_REDRAW seq=(\d+) scroll=\((\d+),(\d+)\) endgrid=\((\d+),(\d+)\) map=\((\d+),(\d+)\) surface=({H}) size=\((\d+),(\d+)\)")
MINIMAP=re.compile(r"FRAMED_MINIMAP enabled=([01]) origin=\((\d+),(\d+)\) size=\((\d+),(\d+)\)")
LIMITS=["A separate software gameplay-evidence decision; the original runtime and image-heuristic verdicts remain unchanged.",
    "Requires one in-world ceiling-window visibility snapshot at the authenticated paused capture boundary; no historical visibility merging or far-world clear proof.",
    "Masked minimap pixels remain unmeasured terrain; four frame bands/footer and all six action cells are independently source-pixel checked.",
    "No cleanup, visible composition, input, endurance, or promotion acceptance is inferred."]


def sha(data):return hashlib.sha256(data).hexdigest()
def require(condition,message):
    if not condition:raise ValueError(message)
def read_json(path):return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def reference(path):
    path=Path(path).resolve();return dict(path=str(path),sha256=sha(path.read_bytes()))
def _path(value):
    path=Path(value);return path.resolve() if path.is_absolute() else (ROOT/path).resolve()


def _one(lines,prefix,pattern):
    rows=[(i,line) for i,line in enumerate(lines) if re.match(r"^"+re.escape(prefix)+r"\b",line)]
    require(len(rows)==1,f"expected one {prefix} observation")
    i,line=rows[0];match=pattern.fullmatch(line)
    require(match is not None,f"malformed {prefix} observation")
    return i,match


def validate_command(run,layout,candidate_path,*,stage=STAGE):
    """Bind the exact supported observation lane, not merely four switch names."""
    command=run["command"]
    require(isinstance(command,list) and command and all(isinstance(v,str) for v in command),"invalid run command")
    require(_path(command[0])==(ROOT/"scripts/cdb/run_cdb_surface_dump.ps1").resolve(),"unrecognized capture producer command")
    switches={"-PartialTileValidation","-InitialMapPaintValidation","-FramedValidation","-UseDdrawProxy",
              "-FastForwardStartAnims","-RequireGameplay"}
    optional=set()
    if stage==complete_context.complete.STAGE:
        switches={"-CompleteHdValidation","-UseDdrawProxy","-FastForwardStartAnims","-RequireGameplay"}
        optional={"-PartialTileValidation","-InitialMapPaintValidation","-FramedValidation","-MinimapViewportValidation"}
    valued={"-Stage","-Resolution","-WorkDir","-CandidateDir","-CandidateName","-OutRoot","-LoadSlot","-RunSeconds"}
    options={};i=1
    while i<len(command):
        key=command[i]
        require(key in switches|optional|valued and key not in options,"unknown or repeated capture option")
        if key in switches|optional:options[key]=True;i+=1
        else:
            require(i+1<len(command),"capture option lacks value")
            options[key]=command[i+1];i+=2
    require(switches|valued<=set(options),"capture command lacks required safe options")
    require(options["-Stage"]==stage and options["-Resolution"]==layout.resolution and options["-LoadSlot"]=="0","capture route/stage/resolution differs")
    require(Path(options["-WorkDir"]).resolve()==Path(run["workdir"]).resolve() and
            Path(options["-CandidateDir"]).resolve()==Path(run["candidate_dir"]).resolve()==candidate_path.parent and
            options["-CandidateName"]==candidate_path.name and
            Path(options["-OutRoot"]).resolve()==Path(run["output_root"]).resolve(),"capture command paths differ from bound run")
    require(re.fullmatch(r"[1-9][0-9]*",options["-RunSeconds"]) and int(options["-RunSeconds"])<=240,"capture duration exceeds bounded observation lane")


def complete_minimap_contract(summary,run_dir,context,original):
    """Reconstruct the actual additive observer before consuming its extra row."""
    require(context['manifest']['stage']==complete_context.complete.STAGE,'minimap context is not complete HD')
    path=Path(summary['MinimapObserverReport']).resolve()
    require(path.parent==run_dir.resolve(),'minimap observer report is outside the capture directory')
    observed=read_json(path)
    source=Path(observed['source_main_path']).resolve();output=Path(observed['observed_main_path']).resolve()
    require(source.parent==output.parent==run_dir.resolve() and len({source,output,path})==3,
            'minimap observer source/output paths differ from capture')
    main=source.read_bytes().decode('ascii')
    raw=Path(summary['RawPath']).resolve()
    require(raw.parent==run_dir.resolve(),'raw surface is outside the capture directory')
    recipe=main_probe.verify_normal_main(main,context,raw)
    require(recipe['exact_recipe_verified'] is True,'complete source main recipe was not verified')
    rebuilt=minimap_probe.build_observed_probe(original,context['candidate'],resolution=context['manifest']['resolution'],
        rendered_probe=main,candidate_manifest=context['manifest'])
    rebuilt['producer_source_sha256']=sha(Path(minimap_probe.__file__).read_bytes())
    rebuilt['source_main_path']=str(source);rebuilt['observed_main_path']=str(output)
    require(observed=={k:v for k,v in rebuilt.items() if k!='probe'},'minimap observer report differs from source reconstruction')
    require(output.read_bytes()==rebuilt['probe'].encode('ascii'),'minimap observer probe differs from source reconstruction')
    sources={name:reference(p) for name,p in (('minimap_observer_report',path),('minimap_source_main',source),('minimap_observed_main',output))}
    for name,digest in recipe['source_hashes'].items():
        ref=reference(ROOT/name)
        require(ref['sha256']==digest,'complete main recipe source changed during evaluation')
        sources['normal_main_recipe:'+name]=ref
    return dict(stage=rebuilt['stage'],resolution=rebuilt['resolution'],candidate_sha256=rebuilt['candidate_sha256'],
                observed_main_sha256=rebuilt['observed_main_sha256'],normal_main_recipe=recipe,sources=sources)


def paused_snapshot(log,summary,layout,trace_report,*,minimap_contract=None):
    """Parse a single complete db span without deduplication or old observations."""
    lines=log.splitlines()
    require(not re.search(r"(?m)^(?:AV_SURFDUMP|SURFDUMP_INVALID|SURFDUMP_APP_REQUEST_QUIT|FRAMED_CAPTURE_REJECT|PTILE_REJECT|PTILE_CONTRACT_FAIL)\b",log),"runtime rejection marker present")
    ri,ready=_one(lines,"SURFDUMP_READY",READY)
    vi,vis=_one(lines,"SCROLL_VISDUMP",visibility.VISDUMP_RE)
    mi,minimap=_one(lines,"FRAMED_MINIMAP",MINIMAP)
    ci,close=_one(lines,"PTILE_TRACE_CLOSED",re.compile(rf"PTILE_TRACE_CLOSED tid=({H}) eip=({H}) esp=({H})"))
    hi,_=_one(lines,"SURFDUMP_HOST_READY",re.compile("SURFDUMP_HOST_READY"))
    require(vi==ri+1 and mi<ci<hi and hi==ci+1,"capture/visibility/minimap/close ordering differs")
    require(ci==mi+1,"native events occurred between minimap observation and pause")
    surface=summary["Surface"];w,h=layout.width,layout.height
    require(tuple(map(int,(ready[1],ready[3],ready[4],ready[6])))==(4,w,h,w*h),"READY dimensions/count mismatch")
    require(int(ready[2],16)>0 and int(ready[5],16)>0,"READY lacks live surface/pixels")
    require(int(ready[2],16)==int(surface["Surface"],16) and int(ready[5],16)==int(surface["Base"],16),"READY pointers differ from captured surface")
    require(surface["RedrawSeq"]==4,"summary does not bind fourth update boundary")
    redraws=[(i,REDRAW.fullmatch(line)) for i,line in enumerate(lines) if line.startswith("SURFDUMP_REDRAW ")]
    require(redraws and all(m is not None for _,m in redraws),"missing/malformed redraw map identity")
    di,draw=redraws[-1]
    require(di==ri-1 and int(draw[1])==3,"capture must follow the fourth observed redraw")
    sx,sy,ex,ey,mw,mh=map(int,draw.group(2,3,4,5,6,7))
    require(int(draw[8],16)==int(ready[2],16) and tuple(map(int,draw.group(9,10)))==(w,h),"redraw surface differs from READY")
    cols,rows=layout.ceil_tiles;fc,fr=layout.full_tiles
    require(1<=mw<=100 and 1<=mh<=100 and 0<=sx<=mw-cols and 0<=sy<=mh-rows,"visibility ceiling window leaves the world")
    require((ex,ey)==(sx+fc,sy+fr),"native full-loop endpoint differs from framed recipe")
    expected=dict(player=0,x=32,y=16,mx=sx,my=sy,cols=cols,rows=rows,tile_x=64,tile_y=64)
    require(all(int(vis[k])==v for k,v in expected.items()),"visibility grid/player/world identity mismatch")
    vb=int(vis["vis_base"].replace('`',''),16);start=int(vis["dump_start"].replace('`',''),16)
    count=int(vis["count"]);last=vb+(sx+cols-1)*13+((sy+rows-1)>>3)
    require(vb>140081 and start==vb+sx*13+(sy>>3) and count==last-start+1 and last<vb+1300,"visibility byte-span bounds mismatch")
    # The same game-data identity is observed by actual auxiliary native calls.
    inputs=[trace.PATTERNS["PTILE_INCREMENTAL_INPUT"].fullmatch(line) for line in lines if line.startswith("PTILE_INCREMENTAL_INPUT ")]
    require(inputs and all(m is not None for m in inputs),"capture lacks native game-data identity observations")
    last_input=inputs[-1]
    require(int(last_input["gd"],16)+140081==vb and tuple(int(last_input[k]) for k in ("mw","mh","sx","sy"))==(mw,mh,sx,sy),"snapshot differs from last authenticated native map context")
    require(trace_report["passed"] and trace_report["initial_sequence"]["return"]["line"]<ri+1,"capture precedes authenticated initial paint")
    memory={};expected_address=start;dump_end=mi;viewport=None
    if minimap_contract is not None:
        require(minimap_contract['stage']==complete_context.complete.STAGE and minimap_contract['resolution']==layout.resolution,
                'paused minimap observer context differs')
        pi,viewport=_one(lines,'FRAMED_MINIMAP_VIEWPORT',re.compile(r'FRAMED_MINIMAP_VIEWPORT scale=(\d+) world=\((\d+),(\d+)\) scroll=\((\d+),(\d+)\)'))
        require(vi<pi==mi-1,'paused minimap viewport must follow the full visibility dump immediately before minimap state')
        scale,vmw,vmh,vsx,vsy=map(int,viewport.groups())
        require((vmw,vmh,vsx,vsy)==(mw,mh,sx,sy) and scale==(4 if mw*mh<=2500 else 2),
                'paused minimap viewport scale/world/scroll differs from native context')
        bound=f"FRAMED_MINIMAP_OBSERVER_BOUND stage={minimap_contract['stage']} resolution={layout.resolution} candidate_sha256={minimap_contract['candidate_sha256']}"
        bi,_=_one(lines,'FRAMED_MINIMAP_OBSERVER_BOUND',re.compile(re.escape(bound)))
        require(bi<ri and bi<min(row['line'] for row in trace_report['event_integrity']['events'])-1,
                'minimap observer bound identity is late')
        dump_end=pi
    for line in lines[vi+1:dump_end]:
        match=re.fullmatch(r"([0-9a-fA-F]{8})  (.{47})  .*",line)
        require(match is not None,"malformed visibility dump row")
        address=int(match[1],16);tokens=match[2].replace('-',' ').split()
        require(address==expected_address and 1<=len(tokens)<=16 and all(re.fullmatch(r"[0-9a-fA-F]{2}",t) for t in tokens),"missing/repeated/invalid visibility bytes")
        require(len(tokens)==min(16,start+count-address),"visibility row length differs from exact span")
        for token in tokens:memory[expected_address]=int(token,16);expected_address+=1
    require(expected_address==start+count,"incomplete visibility dump")
    enabled,left,top,mwidth,mheight=map(int,minimap.groups())
    if enabled:
        box=layout.minimap_box(mwidth,mheight)
        require((left,top)==(box.left,box.top),"minimap origin differs from measured framed backing")
        if viewport is not None:
            require((mwidth,mheight)==(mw*scale+14,mh*scale+14),'paused minimap backing dimensions differ from source scale')
    points={}
    for row in range(rows):
        for col in range(cols):
            wx,wy=sx+col,sy+row;address=vb+wx*13+(wy>>3)
            points[f"r{row}c{col}"]=dict(world=[wx,wy],visibility=memory[address] & (1<<(wy&7)),address=address)
    result=dict(ready_line=ri+1,visibility_line=vi+1,minimap_line=mi+1,closed_line=ci+1,
                map_origin=[sx,sy],map_size=[mw,mh],columns=cols,rows=rows,
                dump_start=start,dump_count=count,points=points,
                minimap=dict(enabled=bool(enabled),width=mwidth if enabled else None,height=mheight if enabled else None))
    if viewport is not None:
        result['minimap_viewport']=dict(line=pi+1,scale=scale,world=[mw,mh],scroll=[sx,sy])
    return result


def candidate_identity(context):
    identity={key:context["manifest"][key] for key in
              ("stage","resolution","candidate_sha256","base_sha256","recipe_revision","probe_sha256")}
    return identity|dict(manifest_path=context["manifest_path"],manifest_sha256=context["manifest_sha256"])


def complete_failure_summary(summary):
    """Expose only measured failure-path fields; preserve the original verdict.

    This is an interface adapter, not validation. The caller still reconstructs
    the candidate/probe, paused native state and raw/palette/PNG bytes.
    """
    if 'Surface' in summary:
        if 'Ready' in summary:
            require(summary['Surface']==summary['Ready'],'Surface and Ready observations disagree')
        return summary,{}
    require(summary.get('Passed') is False and summary.get('FailurePhase')=='postprocessing'
            and summary.get('CoverageExitCode')==2,'Ready compatibility requires the recorded coverage postprocessing failure')
    require(summary.get('CompleteHdValidation') is True and summary.get('HiddenDesktop') is True
            and summary.get('LaunchMode')=='hidden-desktop','Ready compatibility requires the complete hidden-desktop lane')
    for key in ('Av','TimedOut','AppRequestQuit','FullPaintProgressDiagnostic','NoopProgressDiagnostic'):
        require(summary.get(key) is False,f'Ready compatibility rejects missing or unsupported runtime state: {key}')
    for key in ('RuntimeError','RuntimeExceptionId','HostDumpError'):
        require(key in summary and summary[key] in (None,''),f'Ready compatibility rejects runtime failure: {key}')
    ready=summary.get('Ready')
    require(isinstance(ready,dict) and set(ready)=={'RedrawSeq','Surface','Width','Height','Base','Bytes'},
            'Ready must be the exact measured surface object')
    require(all(type(ready[k]) is int for k in ('RedrawSeq','Width','Height','Bytes')),'Ready dimensions/counts must be integers')
    return dict(summary,Surface=dict(ready)),dict(Surface='original Ready observation; independently checked against native paused log')


def complete_pixels(summary,summary_path,layout,native_frame,sprites,*,fallback=False):
    """Verify exact capture bytes without rewriting a failure-path summary."""
    raw_path=Path(summary['RawPath']).resolve();png_path=Path(summary['PngPath']).resolve()
    require(raw_path.parent==png_path.parent==summary_path.parent,'surface artifacts are outside the capture directory')
    raw=raw_path.read_bytes()
    require(len(raw)==summary['RawBytes']==summary['Surface']['Bytes']==layout.width*layout.height,'raw size differs from measured surface')
    view=summary
    if 'PngSha256' not in summary:
        require(fallback,'summary PNG hash is missing outside the supported failure path')
        view=dict(summary,PngSha256=sha(png_path.read_bytes()))
    binding=bar.bind_screenshot(view,raw,raw_path,png_path,layout.width,layout.height)
    captures=[]
    if fallback or 'SurfaceCaptureSet' in summary:
        rows=summary.get('SurfaceCaptureSet')
        require(isinstance(rows,list) and len(rows)==3,'complete capture set must contain three observed raw captures')
        for row in rows:
            path=Path(row['Path']).resolve();data=path.read_bytes()
            require(path.parent==summary_path.parent and row['Bytes']==len(data)==len(raw)
                    and row['Sha256'].lower()==sha(data),'raw capture set path/size/hash differs')
            captures.append(reference(path))
        require(len({row['path'] for row in captures})==3 and captures[0]['path']==str(raw_path),
                'capture set must identify the original raw and two distinct later files')
    cells=bar.compare_cells(raw,layout.width,layout.height,sprites,stage=summary['Stage'])
    return dict(frame=frame.audit_surface(raw,layout,native_frame),cells=cells,binding=binding,
                captures=captures,stable_identical_triple=bool(captures) and len({row['sha256'] for row in captures})==1,
                sources={name:reference(path) for name,path in (('raw_surface',raw_path),('png',png_path),('png_metadata',Path(summary['PngMetadata'])) )})


def reconstruct_coverage(png_path,layout,minimap,*,context=None):
    geometry_stage=context["framed"]["stage"] if context is not None else STAGE
    geometry=coverage.framed_coverage_geometry(geometry_stage,layout.width,layout.height,
        minimap_enabled=minimap["enabled"],minimap_width=minimap["width"],minimap_height=minimap["height"])
    values=dict(logical_width=layout.width,logical_height=layout.height,origin_x=32,origin_y=16,tile_size=64,
                columns=geometry["columns"],rows=geometry["rows"],bottom_row_active_cols=geometry["columns"],
                threshold=12,black_percent=5.0,min_gameplay_border_percent=20.0,min_gameplay_overall_percent=50.0,
                low_detail_bins=0,min_unmasked_percent=20.0)
    args=argparse.Namespace(**values,framed_geometry=geometry)
    report=dict(parameters=values,masks=[dict(name=name,logical_rect=list(rect)) for name,rect in geometry["masks"]],
                images=[coverage.analyze_image(png_path,geometry["cells"],geometry["masks"],args)],
                framed_profile={k:v for k,v in geometry.items() if k not in ("cells","masks")})
    if context is not None:report["candidate_context"]=candidate_identity(context)
    return report


def build_report(summary_path,*,coverage_path,log_path,probe_path,frame_resource,command_resource,original_path,
                 run_plan_path=None,candidate_manifest_path=None):
    stage=complete_context.complete.STAGE if candidate_manifest_path is not None else STAGE
    report=dict(schema_version=1,stage=stage,input_passed=None,guarded_gameplay_evidence=False,
                decision="framed_gameplay_evidence_rejected",runtime_verdict_changed=False,manual_input_proof=False,
                promotion_ready=False,cleanup_proven=False,failures=[],limits=LIMITS,sources={})
    try:
        paths={name:Path(path).resolve() for name,path in dict(summary=summary_path,coverage=coverage_path,log=log_path,
               probe=probe_path,frame_resource=frame_resource,command_resource=command_resource,original=original_path).items()}
        report["sources"]={name:reference(path) for name,path in paths.items()}
        summary=read_json(paths["summary"]);report["input_passed"]=summary.get("Passed")
        report["input_error"]=summary.get("Error")
        if "Failures" in summary:report["input_failures"]=summary["Failures"]
        require(type(report["input_passed"])is bool,"input Passed must remain an explicit boolean")
        require(summary.get("Stage")==stage,"exact framed stage or complete stage with --candidate-manifest required")
        fallback=False
        if candidate_manifest_path is not None:
            report['input_diagnostics']={key:summary[key] for key in ('Passed','Error','Failures','ExceptionId','ExceptionStack',
                'FailurePhase','CoverageExitCode','RuntimeError','RuntimeExceptionId','RuntimeExceptionStack','CleanupResult') if key in summary}
            summary,adapter=complete_failure_summary(summary)
            report['summary_adapter']=adapter;fallback=bool(adapter)
        w,h=summary["Surface"]["Width"],summary["Surface"]["Height"];layout=FramedViewport(w,h)
        require(summary["Resolution"]==layout.resolution,"summary resolution mismatch")
        for key in ("Av","AppRequestQuit","TimedOut","AllowVisibleDesktop","ForceVisibleEdges","PostOwnerForceVisibleSeven","SkipMapValidation"):
            if key in summary:require(summary[key] is False,f"summary reports unsupported runtime state: {key}")
        if "HostDumpError" in summary:require(summary["HostDumpError"] in (None,""),"summary reports host memory capture error")
        report.update(resolution=layout.resolution,candidate_sha256=summary["CandidateSha256"].lower())
        for name in ("coverage","log","probe"):
            require(paths[name].parent==paths["summary"].parent,f"{name} is outside the same capture directory")
        for name,key in (("coverage","CoverageDiagnostic"),("log","SourceLog")):
            if key in summary:
                require(_path(summary[key]["path"])==paths[name] and summary[key]["sha256"]==report["sources"][name]["sha256"],f"summary {key} binding differs")
        if fallback:
            require(_path(summary['Log'])==paths['log'] and _path(summary['CoverageJson'])==paths['coverage']
                    and _path(summary['RunDir'])==paths['summary'].parent,'failure summary artifact paths differ')
        plan_ref=summary.get("RunPlan")
        plan_path=Path(run_plan_path).resolve() if run_plan_path is not None else _path(plan_ref["path"])
        report["sources"]["run_plan"]=reference(plan_path)
        if plan_ref:
            require(_path(plan_ref["path"])==plan_path and plan_ref["sha256"]==report["sources"]["run_plan"]["sha256"],"run plan reference mismatch")
        plan=read_json(plan_path);require(plan["stage"]==stage,"run plan stage mismatch")
        candidate_path=Path(summary["CandidatePath"]).resolve()
        runs=[r for r in plan["runs"] if r.get("resolution")==layout.resolution and Path(r["candidate_path"]).resolve()==candidate_path]
        require(len(runs)==1,"missing/ambiguous source-bound run")
        run=runs[0];require(run["expected_candidate_sha256"]==report["candidate_sha256"],"run plan candidate mismatch")
        require(paths["summary"].parent.parent==Path(run["output_root"]).resolve(),"run plan output directory mismatch")
        validate_command(run,layout,candidate_path,stage=stage)
        original=paths["original"].read_bytes()
        context=None
        sources=(*builder.PINNED_SOURCES,*PRODUCER_SOURCES)
        if candidate_manifest_path is not None:
            manifest_path=Path(candidate_manifest_path).resolve()
            report["sources"]["candidate_manifest"]=reference(manifest_path)
            require(_path(summary["CandidateManifest"])==manifest_path,"summary candidate manifest binding differs")
            if 'CandidateManifestSha256' in summary:
                require(summary['CandidateManifestSha256'].lower()==report['sources']['candidate_manifest']['sha256'],
                        'summary candidate manifest binding differs')
            else:
                require(fallback,'summary candidate manifest hash is missing outside the supported failure path')
                report['summary_adapter']['CandidateManifestSha256']='actual metadata hash; exact source reconstruction required'
            require(manifest_path.name.endswith(".candidate.json") and
                    manifest_path.with_name(manifest_path.name[:-len(".candidate.json")]+".exe")==candidate_path,
                    "candidate manifest does not belong to the summary executable")
            context=complete_context.load_context(manifest_path,paths["original"],resolution=layout.resolution,
                                                  candidate=candidate_path.read_bytes())
            image,metadata,canonical_probe=context["candidate"],context["manifest"],context["probe"]
            require(context["framed"]["stage"]==STAGE,"integrated candidate has a different framed geometry contract")
            require(summary["RecipeRevision"]==metadata["recipe_revision"] and
                    summary["CandidateProbeSha256"].lower()==metadata["probe_sha256"],"summary candidate recipe/probe differs")
            sources=(*sources,*COMPLETE_PRODUCER_SOURCES,*metadata["source_hashes"])
            report["candidate_context"]=candidate_identity(context)
        else:
            image,metadata,canonical_probe=builder.build_candidate(original,layout.resolution)
        for name in sources:
            require(plan["source_sha256"].get(name)==sha((ROOT/name).read_bytes()),f"capture producer source changed: {name}")
        require(plan["original_sha256"]==sha(original),"run plan original identity differs")
        require(image==candidate_path.read_bytes() and sha(image)==report["candidate_sha256"],"candidate differs from canonical framed bytes")
        canonical_bytes=canonical_probe.encode("ascii");probe_bytes=paths["probe"].read_bytes()
        # Run plans hash the builder's LF text. Windows text output serializes
        # it as CRLF; admit those two exact encodings, never mixed/revised text.
        require(probe_bytes in (canonical_bytes,canonical_probe.replace("\n","\r\n").encode("ascii")) and
                sha(canonical_bytes)==run["expected_probe_sha256"],"probe differs from source-bound loaded contract")
        if fallback:
            generated=_path(summary['GeneratedProbe'])
            require(generated.parent==paths['summary'].parent,'failure summary generated probe is outside capture directory')
            report['sources']['summary_generated_probe']=reference(generated)
            if 'GeneratedProbeSha256' in summary:
                require(summary['GeneratedProbeSha256'].lower()==report['sources']['summary_generated_probe']['sha256'],
                        'failure summary generated probe hash differs')
            require(summary['InputSha256'].lower()==sha(original) and _path(summary['InputExe'])==paths['original'],
                    'failure summary original identity differs')
        probe=canonical_probe
        report["canonical_probe_sha256"]=sha(canonical_bytes)
        log=paths["log"].read_text(encoding="utf-8-sig")
        trace_options=dict(candidate_manifest=context["manifest"],original=original) if context is not None else {}
        initial=trace.evaluate_trace(log,probe,resolution=layout.resolution,candidate_sha256=report["candidate_sha256"],stage=stage,
                                     **trace_options)
        require(initial["passed"],"initial trace failed: "+"; ".join(initial["failures"]))
        minimap_contract=None
        if context is not None and (context['framed'].get('minimap_viewport') is True or 'MinimapObserverReport' in summary
                                    or 'FRAMED_MINIMAP_VIEWPORT' in log):
            minimap_contract=complete_minimap_contract(summary,paths['summary'].parent,context,original)
            report['sources'].update(minimap_contract['sources'])
            report['normal_main_recipe']=minimap_contract['normal_main_recipe']
        if context is not None and 'GeneratedProbe' in summary:
            generated=_path(summary['GeneratedProbe'])
            require(generated.parent==paths['summary'].parent,'generated runtime probe is outside the capture directory')
            if minimap_contract is not None:
                source=minimap_contract['sources']['minimap_observed_main']
                runtime=Path(source['path']).read_bytes()
                require(sha(runtime)==source['sha256'],'reconstructed minimap runtime probe changed')
            else:
                runtime=canonical_bytes
            require(b'\r' not in runtime and generated.read_bytes() in (runtime,runtime.replace(b'\n',b'\r\n')),
                    'generated runtime probe differs from exact source-reconstructed composition')
            report['sources']['summary_generated_probe']=reference(generated)
            if 'GeneratedProbeSha256' in summary:
                require(summary['GeneratedProbeSha256'].lower()==report['sources']['summary_generated_probe']['sha256'],
                        'summary generated runtime probe hash differs')
            report['generated_runtime_probe_composition_verified']=True
        snapshot=paused_snapshot(log,summary,layout,initial,minimap_contract=minimap_contract)
        metadata_png=read_json(Path(summary["PngMetadata"]))
        require(Path(metadata_png["log_path"]).resolve()==paths["log"],"PNG metadata log binding differs")
        native_frame=frame.load_native_frame(paths["frame_resource"].read_bytes())
        sprites,_=bar.load_sprites(paths["command_resource"].read_bytes())
        if context is None:
            frame_result=frame.audit_summary(paths["summary"],native_frame)
            bar_result=bar.audit_summary(paths["summary"],sprites)
        else:
            pixel_result=complete_pixels(summary,paths['summary'],layout,native_frame,sprites,fallback=fallback)
            frame_result=pixel_result['frame'];bar_result=dict(all_six_cells_match_source=all(c['exact_source_match'] for c in pixel_result['cells']))
            report['pixel_audits']=pixel_result;report['sources'].update(pixel_result['sources'])
            if fallback and 'PngSha256' not in summary:
                report['summary_adapter']['PngSha256']='actual PNG digest; exact raw/palette/converter reconstruction required'
        require(frame_result["passed"] and frame_result["footer"]["exact"],"four frame bands/footer do not exactly match source pixels")
        require(bar_result["all_six_cells_match_source"],"action bar does not have all six complete source cells")
        observed=read_json(paths["coverage"])
        regenerated=reconstruct_coverage(Path(summary["PngPath"]),layout,snapshot["minimap"],context=context)
        require(observed==regenerated,"coverage report differs from exact bound PNG/default recipe")
        photo=regenerated["images"][0];check=photo["frame_check"]
        report.update(raw_image_gameplay_likely=check["gameplay_frame_likely"],raw_image_warnings=check["warnings"],
                      raw_overall_nonblack_percent=check["edge_coverage"]["overall_nonblack_percent"])
        require(check["warnings"] in ([],["low_overall_gameplay_coverage"]),"coverage has another gameplay warning")
        require(not photo["summary"]["possible_stale_or_solid_active_cells"],"stale/solid active cells remain")
        blanks=[cell for cell in photo["cells"] if cell["active"] and "blank" in cell["flags"]]
        require(check["gameplay_frame_likely"] or blanks,"low-coverage explanation has no measured blank cells")
        zero=[]
        for cell in blanks:
            point=snapshot["points"].get(cell["id"])
            require(point is not None and point["visibility"]==0,f"blank cell lacks zero visibility at paused snapshot: {cell['id']}")
            zero.append(dict(id=cell["id"],**point))
        report.update(guarded_gameplay_evidence=True,decision="guarded_gameplay_evidence",
            candidate_reconstruction_verified=True,canonical_probe_verified=True,coverage_recomputed=True,
            frame_source_pixels_verified=True,footer_source_pixels_verified=True,action_cells_verified=6,
            snapshot={k:v for k,v in snapshot.items() if k!="points"},visibility_zero_blank_cells=zero,
            blank_cells=len(blanks),explained_blank_cells=len(zero),unexplained_blank_cells=[],
            initial_trace=dict(passed=True,initial_sequence=initial["initial_sequence"],full_pairs=initial["full_pairs"]),
            original_coverage_verdict_preserved=True)
        if context is not None:
            for source in report['sources'].values():
                require(sha(Path(source['path']).read_bytes())==source['sha256'],'evidence source changed during evaluation')
    except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError) as exc:
        report["failures"].append(str(exc))
        report.update(guarded_gameplay_evidence=False,decision='framed_gameplay_evidence_rejected')
    report["evaluator_source"]=reference(__file__)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("summary","coverage","log","probe","frame-resource","command-resource","original"):
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--run-plan",type=Path)
    parser.add_argument("--candidate-manifest",type=Path,
                        help="authenticate the integrated candidate bundle; required for the exact complete HD stage")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error("output already exists; refusing overwrite")
    report=build_report(args.summary,coverage_path=args.coverage,log_path=args.log,probe_path=args.probe,
        frame_resource=args.frame_resource,command_resource=args.command_resource,original_path=args.original,run_plan_path=args.run_plan,
        candidate_manifest_path=args.candidate_manifest)
    try:
        with args.output.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2)
    except OSError as exc:parser.error(str(exc))
    print(json.dumps({k:report.get(k) for k in ("decision","guarded_gameplay_evidence","input_passed","failures")}))
    return 0 if report["guarded_gameplay_evidence"] else 2


if __name__=="__main__":raise SystemExit(main())
