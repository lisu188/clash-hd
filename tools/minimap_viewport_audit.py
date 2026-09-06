#!/usr/bin/env python3
"""Audit existing framed minimap outline geometry and indexed surface pixels.

The result is separate from runtime, initial-trace, frame, action-bar, input,
and promotion verdicts. No game/debugger/image modification is performed.
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
import action_bar_surface_audit as screenshot
import build_framed_candidate as builder
import initial_map_paint_trace as initial_trace
import visibility_coverage as visibility
from src.patcher.framed_viewport import FramedViewport

STAGE=screenshot.FRAMED_STAGE
PRIMARY_SURFACE=0x51D4C0
COLOR=0x4C
HEX=r"[0-9a-fA-F]{1,8}"
READY=re.compile(rf"SURFDUMP_READY redraw_seq=(\d+) surface=({HEX}) size=\((\d+),(\d+)\) base=({HEX}) bytes=(\d+)")
REDRAW=re.compile(rf"SURFDUMP_REDRAW seq=(\d+) scroll=\((\d+),(\d+)\) endgrid=\((\d+),(\d+)\) map=\((\d+),(\d+)\) surface=({HEX}) size=\((\d+),(\d+)\)")
MINIMAP=re.compile(r"FRAMED_MINIMAP enabled=([01]) origin=\((\d+),(\d+)\) size=\((\d+),(\d+)\)")
VIEWPORT=re.compile(r"FRAMED_MINIMAP_VIEWPORT scale=(\d+) world=\((\d+),(\d+)\) scroll=\((\d+),(\d+)\)")
DRAW=re.compile(rf"FRAMED_MINIMAP_DRAW target=({HEX}) rect=\((\d+),(\d+),(\d+),(\d+)\) color=({HEX}) tid=({HEX}) scale=(\d+) world=\((\d+),(\d+)\) scroll=\((\d+),(\d+)\)")
CLOSED=re.compile(rf"PTILE_TRACE_CLOSED tid=({HEX}) eip=({HEX}) esp=({HEX})")
LIMITS=["Minimap outline geometry and exact indexed pixels only; frame/footer/action-bar pixels require their separate audits.",
        "Original runtime and initial-trace verdicts are retained independently, including failures.",
        "The surrounding source main probe is a hashed prelaunch producer input; only the candidate, installed extra and additive observer transformation are reconstructed canonically.",
        "No visible composition, manual input, cleanup, endurance, or promotion proof."]


def require(condition,message):
    if not condition:raise ValueError(message)


def sha(data):return hashlib.sha256(data).hexdigest()
def read_json(path):return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def ref(path):
    path=Path(path).resolve();return dict(path=str(path),sha256=sha(path.read_bytes()))


def source_path(value):
    path=Path(value);return path.resolve() if path.is_absolute() else (ROOT/path).resolve()


def observations(lines,prefix,pattern,*,unique=False):
    found=[]
    for i,line in enumerate(lines):
        if re.match(re.escape(prefix)+r"\b",line,re.I):
            match=pattern.fullmatch(line)
            require(match is not None,f"malformed {prefix} record")
            found.append((i,match))
    if unique:require(len(found)==1,f"expected one {prefix} record")
    return found


def expected_outline(width,height,*,scale,world,scroll,minimap_origin,minimap_size):
    """Independent native-pixel formula; never round the view to whole tiles.

    sub_40D330 backing is world*scale+14, anchored at W-32 with top16.
    sub_404040 writes top interior, sides through B-1, and inclusive bottom;
    together these are precisely the inclusive rectangle's one-pixel border.
    This arithmetic also describes world-edge clipping. It does not establish
    that the separate initial full-map route supports every such world.
    """
    values=(width,height,scale,*world,*scroll,*minimap_origin,*minimap_size)
    require(all(type(v)is int for v in values),"geometry requires exact integers")
    require(640<=width<=8192 and 480<=height<=8192 and width%2==height%2==0,"unsupported framed dimensions")
    require(scale in (2,4),"native minimap scale must be 2 or 4")
    mw,mh=world;sx,sy=scroll;mx,my=minimap_origin;bw,bh=minimap_size
    require(1<=mw<=100 and 1<=mh<=100,"world exceeds native visibility backing")
    full_x,full_y=(width-64)//64,(height-32)//64
    require(0<=sx<=max(0,mw-full_x) and 0<=sy<=max(0,mh-full_y),"scroll exceeds native full-tile clamp")
    require((bw,bh)==(mw*scale+14,mh*scale+14),"minimap backing does not match native world/scale dimensions")
    require((mx,my)==(width-32-bw,16) and mx>=32 and my+bh<=height-16,"minimap backing is not within the framed terrain")
    visible_x=min(width-64,(mw-sx)*64);visible_y=min(height-32,(mh-sy)*64)
    require(visible_x>0 and visible_y>0,"empty minimap viewport")
    left,top=mx+6+sx*scale,my+6+sy*scale
    right=left+1+(visible_x*scale+63)//64
    bottom=top+1+(visible_y*scale+63)//64
    require(mx<=left<right<mx+bw and my<=top<bottom<my+bh,"outline escapes minimap backing")
    return dict(rect=[left,top,right,bottom],visible_world_pixels=[visible_x,visible_y],
                scaled_pixel_extent=[right-left-1,bottom-top-1],native_color_index=COLOR)


def perimeter(rect):
    left,top,right,bottom=rect
    require(all(type(v)is int for v in rect) and 0<=left<right and 0<=top<bottom,"invalid native outline rectangle")
    # Match native 404040 order as well as its final inclusive pixel set.
    return ([(x,top) for x in range(left+1,right)]+
            [(x,y) for y in range(top,bottom) for x in (left,right)]+
            [(x,bottom) for x in range(left,right+1)])


def inspect_capture(log,summary,raw):
    """Bind latest actual memory draw to one paused state and its raw pixels."""
    width,height=summary["Surface"]["Width"],summary["Surface"]["Height"]
    layout=FramedViewport(width,height)
    require(summary["Stage"]==STAGE and summary["Resolution"]==layout.resolution,"summary stage/resolution mismatch")
    require(len(raw)==width*height==summary["RawBytes"]==summary["Surface"]["Bytes"],"raw surface size mismatch")
    lines=log.splitlines()
    ri,ready=observations(lines,"SURFDUMP_READY",READY,unique=True)[0]
    vi,vis=observations(lines,"SCROLL_VISDUMP",visibility.VISDUMP_RE,unique=True)[0]
    vpi,view=observations(lines,"FRAMED_MINIMAP_VIEWPORT",VIEWPORT,unique=True)[0]
    mi,mini=observations(lines,"FRAMED_MINIMAP",MINIMAP,unique=True)[0]
    ci,closed=observations(lines,"PTILE_TRACE_CLOSED",CLOSED,unique=True)[0]
    hi,_=observations(lines,"SURFDUMP_HOST_READY",re.compile("SURFDUMP_HOST_READY"),unique=True)[0]
    require(vi==ri+1 and vi<vpi and vpi+1==mi and mi+1==ci and ci+1==hi,"capture state is not one ordered paused boundary")
    require(int(closed[2],16)==0x406FA0 and int(closed[1],16)>0 and int(closed[3],16)>0,"invalid native pause identity")
    surface=summary["Surface"];surface_va=int(ready[2],16)
    require(tuple(map(int,ready.group(1,3,4,6)))==(4,width,height,width*height) and surface["RedrawSeq"]==4,"READY does not match fourth framed update")
    require(surface_va>0 and surface_va!=PRIMARY_SURFACE and int(ready[5],16)>0 and
            surface_va==int(surface["Surface"],16) and int(ready[5],16)==int(surface["Base"],16),"READY surface/pixel pointers mismatch")
    draws=observations(lines,"SURFDUMP_REDRAW",REDRAW)
    require(draws,"missing native redraw context")
    di,redraw=draws[-1]
    require(di==ri-1 and int(redraw[1])==3 and int(redraw[8],16)==surface_va and
            tuple(map(int,redraw.group(9,10)))==(width,height),"redraw does not bind captured surface")
    scale,mw,mh,sx,sy=map(int,view.groups())
    require(scale==(4 if mw*mh<=2500 else 2),"paused scale differs from native world-area selection")
    require(tuple(map(int,redraw.group(2,3,4,5,6,7)))==
            (sx,sy,sx+(width-64)//64,sy+(height-32)//64,mw,mh),"paused world/scroll differs from native redraw")
    grid=dict(player=0,x=32,y=16,mx=sx,my=sy,cols=(width-64+63)//64,rows=(height-32+63)//64,tile_x=64,tile_y=64)
    require(all(int(vis[key])==value for key,value in grid.items()),"paused visibility header differs from viewport context")
    enabled,mx,my,bw,bh=map(int,mini.groups())
    require(enabled==1,"minimap is not enabled in the captured state")
    geometry=expected_outline(width,height,scale=scale,world=(mw,mh),scroll=(sx,sy),
                              minimap_origin=(mx,my),minimap_size=(bw,bh))
    draw_rows=observations(lines,"FRAMED_MINIMAP_DRAW",DRAW)
    require(draw_rows and all(i<ri for i,_ in draw_rows),"draw observer missing or occurs after captured READY")
    require(all(int(m[1],16) in (surface_va,PRIMARY_SURFACE) for _,m in draw_rows),"draw target is not captured memory or native primary surface")
    memory=[(i,m) for i,m in draw_rows if int(m[1],16)!=PRIMARY_SURFACE]
    require(memory,"no actual memory-surface outline draw")
    draw_line,draw=memory[-1]
    require(int(draw[1],16)==surface_va and int(draw[7],16)==int(closed[1],16),"last memory draw target/thread differs from capture")
    require(tuple(map(int,draw.group(8,9,10,11,12)))==(scale,mw,mh,sx,sy),"last memory draw context differs from paused viewport")
    require(list(map(int,draw.group(2,3,4,5)))==geometry["rect"],"actual native outline differs from framed pixel geometry")
    require(int(draw[6],16)==COLOR,"actual native outline color is not 4C")
    pixels=perimeter(geometry["rect"])
    mismatches=[dict(x=x,y=y,index=raw[y*width+x]) for x,y in pixels if raw[y*width+x]!=COLOR]
    return dict(geometry=geometry,draw_line=draw_line+1,draw_count=len(draw_rows),memory_draw_count=len(memory),
                memory_target=surface_va,thread=int(draw[7],16),scale=scale,world=[mw,mh],scroll=[sx,sy],
                minimap_origin=[mx,my],minimap_size=[bw,bh],ready_line=ri+1,visibility_line=vi+1,
                viewport_line=vpi+1,minimap_line=mi+1,closed_line=ci+1,
                perimeter_pixels=len(pixels),mismatched_pixels=len(mismatches),first_mismatches=mismatches[:20],
                all_perimeter_pixels_match=not mismatches)


def bind_run_plan(summary,plan_path,metadata,candidate,run_dir):
    plan=read_json(plan_path)
    require(plan["stage"]==STAGE,"run plan stage differs")
    runs=[row for row in plan["runs"] if row.get("resolution")==summary["Resolution"] and
          source_path(row["candidate_path"])==candidate]
    require(len(runs)==1,"missing or ambiguous source-bound minimap run")
    run=runs[0]
    require(run["expected_candidate_sha256"]==summary["CandidateSha256"].lower() and
            source_path(run["output_root"])==run_dir.parent,"run plan candidate/output differs")
    command=run["command"]
    require(isinstance(command,list) and command and all(isinstance(value,str) for value in command),"invalid run command")
    require(source_path(command[0])==(ROOT/"scripts/cdb/run_cdb_surface_dump.ps1").resolve(),"unexpected run producer command")
    required_switches={"-PartialTileValidation","-InitialMapPaintValidation","-FramedValidation","-MinimapViewportValidation","-UseDdrawProxy"}
    optional_switches={"-FastForwardStartAnims","-RequireGameplay"}
    values={"-Stage","-Resolution","-WorkDir","-CandidateDir","-CandidateName","-OutRoot","-LoadSlot","-RunSeconds"}
    parsed={};i=1
    while i<len(command):
        name=command[i]
        require(name in required_switches|optional_switches|values and name not in parsed,"unknown or repeated run option")
        if name in values:
            require(i+1<len(command),"run option lacks a value")
            parsed[name]=command[i+1];i+=2
        else:parsed[name]=True;i+=1
    require(required_switches|values<=set(parsed),"missing bounded minimap run options")
    require(parsed["-Stage"]==STAGE and parsed["-Resolution"]==summary["Resolution"] and parsed["-LoadSlot"]=="0","run route/stage/resolution differs")
    require(source_path(parsed["-CandidateDir"])==source_path(run["candidate_dir"])==candidate.parent and
            parsed["-CandidateName"]==candidate.name and source_path(parsed["-WorkDir"])==source_path(run["workdir"]) and
            source_path(parsed["-OutRoot"])==run_dir.parent,"run command paths differ from packet")
    require(re.fullmatch(r"[1-9][0-9]*",parsed["-RunSeconds"]) and int(parsed["-RunSeconds"])<=240,"run exceeds bounded capture duration")
    sources=dict(metadata["source_sha256"])
    for name in ("tools/build_framed_candidate.py","tools/framed_minimap_probe.py","tools/framed_noop_progress_probe.py",
                 "scripts/cdb/run_cdb_surface_dump.ps1","tools/render_cdb_surface_probe.py","tools/initial_map_paint_trace.py",
                 "tools/action_bar_surface_audit.py","tools/cdb_surface_dump_to_png.py"):
        sources[name]=sha((ROOT/name).read_bytes())
    for name,expected in sources.items():
        require(plan["source_sha256"].get(name)==expected==sha((ROOT/name).read_bytes()),f"run source binding differs: {name}")
    return plan,run


def build_report(summary_path,*,log_path,probe_path,original_path,run_plan_path=None):
    """Read existing artifacts and emit an independent geometry verdict.

    probe_path is surface-minimap-probe.cdb, the observed main. The original
    generated main and prelaunch minimap-observer.json remain in the same run.
    """
    import framed_minimap_probe as producer
    report=dict(schema_version=1,stage=STAGE,minimap_viewport_geometry_passed=False,
        decision="minimap_viewport_geometry_rejected",input_passed=None,initial_trace_passed=None,
        runtime_verdict_changed=False,initial_trace_verdict_changed=False,frame_pixels_audited=False,
        action_bar_pixels_audited=False,manual_input_proof=False,promotion_ready=False,
        cleanup_proven=False,failures=[],limits=LIMITS,sources={})
    try:
        paths={name:Path(value).resolve() for name,value in dict(summary=summary_path,log=log_path,
                                                             observed_main=probe_path,original=original_path).items()}
        report["sources"]={name:ref(path) for name,path in paths.items()}
        summary=read_json(paths["summary"]);run_dir=paths["summary"].parent
        report.update(input_passed=summary.get("Passed"),input_error=summary.get("Error"))
        require(type(report["input_passed"])is bool,"runtime Passed must be an explicit preserved boolean")
        require(summary.get("Stage")==STAGE and summary.get("MinimapViewportValidation")is True,"exact minimap-enabled framed stage required")
        for name in ("log","observed_main"):
            require(paths[name].parent==run_dir,f"{name} belongs to a different capture")
        for key,name in (("GeneratedProbe","observed_main"),("Log","log")):
            if key in summary:require(source_path(summary[key])==paths[name],f"summary {key} path differs")
        if "SourceLog" in summary:
            require(source_path(summary["SourceLog"]["path"])==paths["log"] and
                    summary["SourceLog"]["sha256"]==report["sources"]["log"]["sha256"],"summary raw log binding differs")
        candidate=source_path(summary["CandidatePath"]);original=paths["original"].read_bytes()
        image,metadata,canonical_extra=builder.build_candidate(original,summary["Resolution"],minimap_viewport=True)
        require(metadata.get("minimap_viewport")is True and metadata.get("minimap_viewport_revision")=="framed_minimap_actual_terrain_v1","builder lacks reviewed minimap viewport revision")
        require(image==candidate.read_bytes() and sha(image)==summary["CandidateSha256"].lower(),"candidate differs from canonical minimap-enabled image")
        report.update(candidate_sha256=sha(image),resolution=summary["Resolution"])
        report["sources"]["candidate"]=ref(candidate)
        plan_ref=summary.get("RunPlan")
        plan_path=Path(run_plan_path).resolve() if run_plan_path is not None else source_path(plan_ref["path"])
        report["sources"]["run_plan"]=ref(plan_path)
        if plan_ref:
            require(source_path(plan_ref["path"])==plan_path and plan_ref["sha256"]==report["sources"]["run_plan"]["sha256"],"summary run plan binding differs")
        plan,run=bind_run_plan(summary,plan_path,metadata,candidate,run_dir)
        require(plan["original_sha256"]==sha(original),"run plan original differs")
        extra_path=run_dir/"partial-tile-installed.extra.cdb";extra_raw=extra_path.read_bytes()
        require(extra_raw in (canonical_extra.encode("ascii"),canonical_extra.replace("\n","\r\n").encode("ascii")) and
                run["expected_probe_sha256"]==sha(canonical_extra.encode("ascii")),"installed extra differs from canonical probe/plan")
        report["sources"]["canonical_extra"]=ref(extra_path)
        packet_path=source_path(summary["MinimapObserverReport"])
        require(packet_path.parent==run_dir,"observer packet belongs to a different capture")
        packet=read_json(packet_path);source_main=source_path(packet["source_main_path"])
        require(source_main.parent==run_dir and source_main!=paths["observed_main"],"invalid source main probe path")
        source_text=source_main.read_bytes().decode("ascii")
        rebuilt=producer.build_observed_probe(original,image,resolution=summary["Resolution"],rendered_probe=source_text)
        observed=rebuilt["probe"].encode("ascii")
        require(run["expected_source_main_lf_sha256"]==rebuilt["source_main_lf_sha256"] and
                run["expected_observed_main_sha256"]==sha(observed),"main probes differ from prelaunch run plan hashes")
        require(paths["observed_main"].read_bytes()==observed,"observed main differs from exact producer transformation")
        expected_packet={key:value for key,value in rebuilt.items() if key!="probe"}
        expected_packet.update(producer_source_sha256=sha(Path(producer.__file__).read_bytes()),
                               source_main_path=str(source_main),observed_main_path=str(paths["observed_main"]))
        require(packet==expected_packet,"prelaunch observer packet differs from source-bound reconstruction")
        report["sources"].update(observer_packet=ref(packet_path),source_main=ref(source_main))
        log=paths["log"].read_text(encoding="utf-8-sig");lines=log.splitlines()
        for prefix in ("PTILE_CONTRACT_PASS","FRAMED_MINIMAP_OBSERVER_BOUND"):
            pattern=re.compile(re.escape(f"{prefix} stage={STAGE} resolution={summary['Resolution']} candidate_sha256={sha(image)}"))
            observations(lines,prefix,pattern,unique=True)
        initial=initial_trace.evaluate_trace(log,canonical_extra,resolution=summary["Resolution"],candidate_sha256=sha(image),stage=STAGE)
        report.update(initial_trace_passed=initial["passed"],initial_trace_failures=initial["failures"])
        raw_path,png_path=source_path(summary["RawPath"]),source_path(summary["PngPath"])
        require(raw_path.parent==png_path.parent==run_dir,"surface artifacts belong to a different capture")
        raw=raw_path.read_bytes();width,height=summary["Surface"]["Width"],summary["Surface"]["Height"]
        png_meta=read_json(summary["PngMetadata"])
        require(source_path(png_meta["log_path"])==paths["log"],"PNG metadata belongs to another log")
        report["screenshot_binding"]=screenshot.bind_screenshot(summary,raw,raw_path,png_path,width,height)
        report["sources"].update(raw_surface=ref(raw_path),png=ref(png_path),png_metadata=ref(summary["PngMetadata"]))
        report["capture"]=inspect_capture(log,summary,raw)
        require(report["capture"]["all_perimeter_pixels_match"],"native minimap perimeter pixels are incomplete")
        report.update(minimap_viewport_geometry_passed=True,decision="minimap_viewport_geometry_verified",
                      candidate_reconstructed=True,canonical_extra_verified=True,observer_transformation_verified=True,
                      prelaunch_main_hashes_verified=True,
                      source_main_fully_reconstructed=False)
    except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError) as exc:
        report["failures"].append(str(exc))
    report["evaluator_source"]=ref(__file__)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("summary","log","probe","original","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--run-plan",type=Path)
    args=parser.parse_args()
    if args.output.exists():parser.error("output exists; refusing overwrite")
    report=build_report(args.summary,log_path=args.log,probe_path=args.probe,original_path=args.original,run_plan_path=args.run_plan)
    try:
        with args.output.open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2)
    except OSError as exc:parser.error(str(exc))
    print(json.dumps({key:report.get(key) for key in ("decision","minimap_viewport_geometry_passed","input_passed","initial_trace_passed","failures")}))
    return 0 if report["minimap_viewport_geometry_passed"] else 2


if __name__=="__main__":raise SystemExit(main())
