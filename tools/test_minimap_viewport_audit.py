#!/usr/bin/env python3
"""Offline synthetic geometry/artifact fixtures; no game, CDB or approvals."""
from __future__ import annotations

from contextlib import ExitStack
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import minimap_viewport_audit as audit
import framed_minimap_probe as producer
import test_initial_map_paint_trace as trace_fixture
from cdb_surface_dump_to_png import convert


RESOLUTIONS=((800,600),(1024,768),(1280,720),(1280,960),(1920,1080),(802,602))


def capture(width=800,height=600,*,scale=2,world=None,scroll=(10,17)):
    if world is None:world=(100,100) if scale==2 else (50,50)
    mw,mh=world;sx,sy=scroll;bw,bh=mw*scale+14,mh*scale+14;mx,my=width-32-bw,16
    geometry=audit.expected_outline(width,height,scale=scale,world=world,scroll=scroll,
                                    minimap_origin=(mx,my),minimap_size=(bw,bh))
    left,top,right,bottom=geometry["rect"]
    raw=bytearray([3])*(width*height)
    # Literal raster loops, independent from audit.perimeter implementation.
    for y in range(top,bottom+1):raw[y*width+left]=raw[y*width+right]=0x4C
    for x in range(left,right+1):raw[top*width+x]=raw[bottom*width+x]=0x4C
    surface=0x9000000;base=0xA000000;tid=0x123
    summary=dict(Passed=False,Error="synthetic runtime failure remains separate",Stage=audit.STAGE,
        Resolution=f"{width}x{height}",RawBytes=len(raw),
        Surface=dict(Width=width,Height=height,Bytes=len(raw),RedrawSeq=4,Surface=f"{surface:08x}",Base=f"{base:08x}"))
    draw=(f"FRAMED_MINIMAP_DRAW target={surface:08x} rect=({left},{top},{right},{bottom}) color=4c tid={tid:x} "
          f"scale={scale} world=({mw},{mh}) scroll=({sx},{sy})")
    log=(draw+"\n"+draw.replace(f"target={surface:08x}","target=0051d4c0")+"\n"
         f"SURFDUMP_REDRAW seq=3 scroll=({sx},{sy}) endgrid=({sx+(width-64)//64},{sy+(height-32)//64}) map=({mw},{mh}) surface={surface:08x} size=({width},{height})\n"
         f"SURFDUMP_READY redraw_seq=4 surface={surface:08x} size=({width},{height}) base={base:08x} bytes={len(raw)}\n"
         f"SCROLL_VISDUMP player=0 screen0=(32,16) map0=({sx},{sy}) rows={(height-32+63)//64} cols={(width-64+63)//64} tile=(64,64) vis_base=00622331 dump_start=006223b5 count=145\n"
         f"FRAMED_MINIMAP_VIEWPORT scale={scale} world=({mw},{mh}) scroll=({sx},{sy})\n"
         f"FRAMED_MINIMAP enabled=1 origin=({mx},{my}) size=({bw},{bh})\n"
         f"PTILE_TRACE_CLOSED tid={tid:x} eip=00406fa0 esp=00100100\nSURFDUMP_HOST_READY\n")
    return summary,log,raw,geometry


class GeometryTests(unittest.TestCase):
    def test_independent_literal_extents_at_six_resolutions_both_scales(self):
        # Inclusive differences include the native one-pixel padding. These
        # literals are calculated directly from physical viewport pixels.
        differences={2:((24,19),(31,24),(39,23),(39,30),(59,34),(25,19)),
                     4:((47,37),(61,47),(77,44),(77,59),(117,67),(48,37))}
        for scale in (2,4):
            for (width,height),(dx,dy) in zip(RESOLUTIONS,differences[scale]):
                with self.subTest(resolution=(width,height),scale=scale):
                    summary,log,raw,geometry=capture(width,height,scale=scale)
                    expected=[width-(220 if scale==2 else 200),56 if scale==2 else 90]
                    self.assertEqual(geometry["rect"],expected+[expected[0]+dx,expected[1]+dy])
                    result=audit.inspect_capture(log,summary,raw)
                    self.assertTrue(result["all_perimeter_pixels_match"])
                    self.assertEqual(result["perimeter_pixels"],2*(dx+dy))
                    self.assertEqual(result["memory_draw_count"],1)

    def test_world_edge_clips_real_pixel_extent_and_small_world_is_explicit(self):
        for width,height in RESOLUTIONS:
            for scale in (2,4):
                fullx,fully=(width-64)//64,(height-32)//64
                _,_,_,geometry=capture(width,height,scale=scale,world=(100,100),scroll=(100-fullx,100-fully))
                self.assertEqual(geometry["visible_world_pixels"],[fullx*64,fully*64])
                self.assertEqual(geometry["scaled_pixel_extent"],[fullx*scale,fully*scale])
        summary,log,raw,geometry=capture(world=(5,3),scale=4,scroll=(0,0))
        self.assertEqual(geometry["visible_world_pixels"],[320,192])
        self.assertEqual(geometry["scaled_pixel_extent"],[20,12])
        self.assertTrue(audit.inspect_capture(log,summary,raw)["all_perimeter_pixels_match"])

    def test_invalid_backing_origin_scale_world_scroll_and_physical_sizes(self):
        base=dict(width=800,height=600,scale=2,world=(100,100),scroll=(10,17),minimap_origin=(554,16),minimap_size=(214,214))
        for change in (dict(width=True),dict(width=801),dict(height=599),dict(scale=1),dict(scale=3),
                       dict(world=(0,100)),dict(world=(101,100)),dict(scroll=(-1,17)),dict(scroll=(90,17)),
                       dict(minimap_origin=(553,16)),dict(minimap_origin=(554,0)),dict(minimap_size=(213,214)),
                       dict(minimap_size=(214,0))):
            with self.subTest(change=change),self.assertRaises(ValueError):audit.expected_outline(**(base|change))

    def test_native_raster_inclusive_corners_and_no_duplicate_pixel_count(self):
        pixels=audit.perimeter([2,3,6,7])
        expected={(x,y) for y in range(3,8) for x in range(2,7) if x in (2,6) or y in (3,7)}
        self.assertEqual(set(pixels),expected);self.assertEqual(len(pixels),16)
        self.assertEqual(pixels[:3],[(3,3),(4,3),(5,3)])
        self.assertEqual(pixels[-5:],[(x,7) for x in range(2,7)])

    def test_stale_native_tile_rounded_wrong_position_and_color_fail(self):
        summary,log,raw,geometry=capture(802,602,scale=4)
        left,top,right,bottom=geometry["rect"]
        observed=f"rect=({left},{top},{right},{bottom})"
        wrong_rects=((left,top,left+1+9*4,top+1+7*4),
                     (left,top,left+1+12*4,top+1+9*4),
                     (left+1,top,right+1,bottom),(left,top+1,right,bottom+1))
        for rect in wrong_rects:
            with self.subTest(rect=rect),self.assertRaisesRegex(ValueError,"actual native outline"):
                audit.inspect_capture(log.replace(observed,"rect=("+",".join(map(str,rect))+")"),summary,raw)
        for color in ("0","4d","104c","-1"):
            with self.subTest(color=color),self.assertRaises(ValueError):
                audit.inspect_capture(log.replace("color=4c",f"color={color}"),summary,raw)

    def test_latest_memory_draw_context_target_thread_and_order(self):
        summary,log,raw,_=capture();draw=log.splitlines()[0]
        for old,new in (("target=09000000","target=09000001"),("tid=123","tid=124"),
                        ("scale=2","scale=4"),("world=(100,100)","world=(99,100)"),
                        ("scroll=(10,17)","scroll=(11,17)")):
            with self.subTest(old=old),self.assertRaises(ValueError):
                audit.inspect_capture(log.replace(draw,draw.replace(old,new),1),summary,raw)
        with self.assertRaisesRegex(ValueError,"no actual memory"):
            audit.inspect_capture(log.replace("target=09000000","target=0051d4c0"),summary,raw)
        with self.assertRaisesRegex(ValueError,"after captured READY"):
            audit.inspect_capture(log+draw+"\n",summary,raw)
        # Older same-target draws can have different positions. Acceptance
        # uses the final matching memory draw, not any historical match.
        stale=draw.replace("scroll=(10,17)","scroll=(9,17)")
        self.assertTrue(audit.inspect_capture(stale+"\n"+log,summary,raw)["all_perimeter_pixels_match"])
        with self.assertRaisesRegex(ValueError,"context differs"):
            audit.inspect_capture(log.replace(draw,draw+"\n"+stale,1),summary,raw)

    def test_unique_capture_state_and_all_native_context_bindings(self):
        summary,log,raw,_=capture()
        for prefix in ("SURFDUMP_READY","SCROLL_VISDUMP","FRAMED_MINIMAP_VIEWPORT","FRAMED_MINIMAP ","PTILE_TRACE_CLOSED","SURFDUMP_HOST_READY"):
            line=next(line for line in log.splitlines() if line.startswith(prefix))
            for replacement in ("",line+"\n"+line,line.lower()):
                with self.subTest(prefix=prefix,replacement=replacement),self.assertRaises(ValueError):
                    audit.inspect_capture(log.replace(line,replacement),summary,raw)
        changes=(("enabled=1","enabled=0"),("endgrid=(21,25)","endgrid=(22,26)"),
                 ("player=0","player=1"),("map0=(10,17)","map0=(11,17)"),
                 ("rows=9 cols=12","rows=8 cols=11"),("base=0a000000","base=00000000"),
                 ("redraw_seq=4","redraw_seq=3"),("bytes=480000","bytes=480001"),
                 ("origin=(554,16)","origin=(554,17)"),("eip=00406fa0","eip=00406fa1"))
        for old,new in changes:
            with self.subTest(old=old),self.assertRaises(ValueError):audit.inspect_capture(log.replace(old,new),summary,raw)

    def test_every_perimeter_pixel_required_but_no_unrelated_frame_claim(self):
        summary,log,raw,geometry=capture();left,top,right,bottom=geometry["rect"]
        for x,y in ((left,top),(right,top),(left,bottom),(right,bottom),(left+1,top),(left,top+1),(left+1,bottom)):
            with self.subTest(pixel=(x,y)):
                changed=raw.copy();changed[y*800+x]=3
                result=audit.inspect_capture(log,summary,changed)
                self.assertFalse(result["all_perimeter_pixels_match"]);self.assertEqual(result["mismatched_pixels"],1)
                self.assertEqual(result["first_mismatches"],[dict(x=x,y=y,index=3)])
        # Interior and unrelated frame/action-bar pixels are outside this audit.
        changed=raw.copy();changed[(top+1)*800+left+1]=76;changed[0]=0
        self.assertTrue(audit.inspect_capture(log,summary,changed)["all_perimeter_pixels_match"])


def write_json(path,value):path.write_text(json.dumps(value,indent=2),encoding="utf-8")


class Artifacts:
    """Synthetic binary/PE mapping only; actual observer and pixel validators."""
    def __init__(self,root):
        self.root=root;self.run=root/"captures"/"run";self.run.mkdir(parents=True)
        self.original=root/"original.fixture";self.original.write_bytes(b"synthetic original, not executable")
        self.candidate=root/"candidate.fixture"
        self.image=bytes.fromhex("e800000000e800000000")+b" synthetic non-PE candidate"
        self.candidate.write_bytes(self.image);self.digest=audit.sha(self.image)
        self.metadata=dict(minimap_viewport=True,minimap_viewport_revision="framed_minimap_actual_terrain_v1",
            minimap_viewport_contract=dict(observers=dict(memory=0x701000,primary=0x701010)),
            source_sha256={"tools/build_framed_candidate.py":audit.sha(Path(audit.builder.__file__).read_bytes())})
        initial,extra=trace_fixture.fixture(stage=audit.STAGE,close="")
        self.extra=extra.replace(trace_fixture.SHA,self.digest)
        self.extra_path=self.run/"partial-tile-installed.extra.cdb";self.extra_path.write_bytes(self.extra.encode("ascii"))
        self.source=self.run/"clash95_surface_dump_probe.generated.cdb"
        capture_declaration=('bp 00406FA0 ".if (poi(005202e4) == 0) { .echo FRAMED_CAPTURE_REJECT missing_game_data; q } .else { '
            +producer.INSERTION+'%d origin=(%d,%d) size=(%d,%d)\\\\n\\\", 1, 554, 16, 214, 214; '
            +'.echo PTILE_TRACE_CLOSED; .echo SURFDUMP_HOST_READY; }; gc"')
        self.source.write_text("bc *\n"+self.extra.strip()+"\n"+capture_declaration+"\ng\n",encoding="ascii",newline="\n")
        self.observed=self.run/"surface-minimap-probe.cdb";self.packet=self.run/"minimap-observer.json"
        with self.mocks():self.rebuild_observer()
        summary,log,raw,_=capture()
        bound=f"FRAMED_MINIMAP_OBSERVER_BOUND stage={audit.STAGE} resolution=800x600 candidate_sha256={self.digest}\n"
        log=initial.replace(trace_fixture.SHA,self.digest)+bound+log.replace("tid=123","tid=abc")
        self.log=self.run/"capture.log";self.log.write_text(log,encoding="ascii")
        self.raw=self.run/"surface.raw";self.png=self.run/"surface.png";self.meta=self.run/"surface.png.json"
        self.raw.write_bytes(raw);self.summary=self.run/"diagnostic-summary.json";self.plan=root/"plan.json"
        self.summary_data=summary|dict(MinimapViewportValidation=True,MinimapObserverReport=str(self.packet),
            CandidatePath=str(self.candidate),CandidateSha256=self.digest,RawPath=str(self.raw),PngPath=str(self.png),
            PngMetadata=str(self.meta),Log=str(self.log),GeneratedProbe=str(self.observed))
        names=("tools/build_framed_candidate.py","tools/framed_minimap_probe.py","tools/framed_noop_progress_probe.py",
               "scripts/cdb/run_cdb_surface_dump.ps1","tools/render_cdb_surface_probe.py","tools/initial_map_paint_trace.py",
               "tools/action_bar_surface_audit.py","tools/cdb_surface_dump_to_png.py")
        self.plan_data=dict(stage=audit.STAGE,original_sha256=audit.sha(self.original.read_bytes()),
            source_sha256={name:audit.sha((audit.ROOT/name).read_bytes()) for name in names},
            runs=[dict(resolution="800x600",candidate_path=str(self.candidate),candidate_dir=str(root),workdir=str(root),
                output_root=str(self.run.parent),expected_candidate_sha256=self.digest,expected_probe_sha256=audit.sha(self.extra.encode("ascii")),
                expected_source_main_lf_sha256=audit.sha(self.source.read_text(encoding="ascii").encode("ascii")),
                expected_observed_main_sha256=audit.sha(self.observed.read_bytes()),
                command=["scripts/cdb/run_cdb_surface_dump.ps1","-PartialTileValidation","-InitialMapPaintValidation",
                         "-FramedValidation","-MinimapViewportValidation","-UseDdrawProxy","-RequireGameplay",
                         "-Stage",audit.STAGE,"-Resolution","800x600","-WorkDir",str(root),"-CandidateDir",str(root),
                         "-CandidateName",self.candidate.name,"-OutRoot",str(self.run.parent),"-LoadSlot","0","-RunSeconds","180"])])
        self.regenerate_png();self.save()

    def mocks(self):
        stack=ExitStack()
        def build(original,resolution,*,minimap_viewport=False):
            audit.require(original==b"synthetic original, not executable" and resolution=="800x600" and minimap_viewport is True,
                          "synthetic canonical reconstruction rejected")
            return self.image,copy.deepcopy(self.metadata),self.extra
        def file_offset(candidate,va,size):
            audit.require(candidate==self.image and va in (0x701000,0x701010) and size==5,"synthetic PE mapping rejected")
            return 0 if va==0x701000 else 5
        stack.enter_context(patch.object(audit.builder,"build_candidate",side_effect=build))
        stack.enter_context(patch.object(audit.builder.clip,"file_offset",side_effect=file_offset))
        return stack

    def rebuild_observer(self):
        packet=producer.build_observed_probe(self.original.read_bytes(),self.image,resolution="800x600",rendered_probe=self.source.read_bytes().decode("ascii"))
        self.observed.write_bytes(packet["probe"].encode("ascii"))
        value={key:item for key,item in packet.items() if key!="probe"}
        value.update(producer_source_sha256=audit.sha(Path(producer.__file__).read_bytes()),source_main_path=str(self.source),observed_main_path=str(self.observed))
        write_json(self.packet,value)

    def regenerate_png(self):
        metadata=convert(self.raw,self.png,800,600,800,self.meta,self.log,None)
        self.summary_data["PngSha256"]=metadata["png_sha256"]

    def save(self):
        write_json(self.plan,self.plan_data)
        self.summary_data.update(RunPlan=audit.ref(self.plan),SourceLog=audit.ref(self.log))
        write_json(self.summary,self.summary_data)

    def kwargs(self):return dict(log_path=self.log,probe_path=self.observed,original_path=self.original)


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.a=Artifacts(Path(self.temp.name));self.addCleanup(self.a.mocks().close)
        self.files={path:path.read_bytes() for path in self.a.root.rglob("*") if path.is_file()}
        self.summary=copy.deepcopy(self.a.summary_data);self.plan=copy.deepcopy(self.a.plan_data)

    def reset(self):
        for path,data in self.files.items():path.write_bytes(data)
        self.a.summary_data=copy.deepcopy(self.summary);self.a.plan_data=copy.deepcopy(self.plan)

    def evaluate(self):return audit.build_report(self.a.summary,**self.a.kwargs())
    def rejected(self,contains=None):
        report=self.evaluate();self.assertFalse(report["minimap_viewport_geometry_passed"],report)
        self.assertTrue(report["failures"])
        if contains:self.assertIn(contains,";".join(report["failures"]))
        return report

    def test_actual_pipeline_binds_main_extra_candidate_pixels_and_failed_runtime(self):
        hashes={path:audit.sha(data) for path,data in self.files.items()}
        report=self.evaluate();self.assertTrue(report["minimap_viewport_geometry_passed"],report["failures"])
        self.assertFalse(report["input_passed"]);self.assertEqual(report["input_error"],self.summary["Error"])
        self.assertTrue(report["initial_trace_passed"],report["initial_trace_failures"])
        for key in ("runtime_verdict_changed","initial_trace_verdict_changed","frame_pixels_audited","action_bar_pixels_audited",
                    "manual_input_proof","promotion_ready","cleanup_proven","source_main_fully_reconstructed"):
            self.assertFalse(report[key])
        self.assertEqual(hashes,{path:audit.sha(path.read_bytes()) for path in self.files})
        # A raw initial event replay remains a failed trace. Its presence does
        # not erase independently bound minimap pixels or become runtime PASS.
        log=self.a.log.read_text();self.a.log.write_text(log.replace("PTILE_EVENT seq=4","PTILE_EVENT seq=3"));self.a.save()
        report=self.evaluate();self.assertTrue(report["minimap_viewport_geometry_passed"],report["failures"])
        self.assertFalse(report["initial_trace_passed"]);self.assertTrue(report["initial_trace_failures"])
        self.assertFalse(report["input_passed"])

    def test_missing_changed_candidate_original_extra_and_observer_packets(self):
        for path in (self.a.candidate,self.a.original,self.a.extra_path,self.a.source,self.a.observed,self.a.packet,self.a.log,self.a.plan):
            for mode in ("missing","changed"):
                with self.subTest(path=path.name,mode=mode):
                    self.reset()
                    if mode=="missing":path.unlink()
                    else:path.write_bytes(path.read_bytes()+b" changed")
                    self.rejected()
        self.reset();packet=audit.read_json(self.a.packet);packet["acceptance"]=True;write_json(self.a.packet,packet)
        self.rejected("prelaunch observer packet")
        self.reset();packet=audit.read_json(self.a.packet);packet["producer_source_sha256"]="0"*64;write_json(self.a.packet,packet)
        self.rejected("prelaunch observer packet")
        self.reset();text=self.a.observed.read_text().replace("@edx, @ebx","@ebx, @edx")
        self.a.observed.write_bytes(text.encode("ascii"));packet=audit.read_json(self.a.packet)
        packet["observed_main_sha256"]=audit.sha(self.a.observed.read_bytes());write_json(self.a.packet,packet)
        self.rejected("observed main differs")

    def test_plan_stage_source_options_identity_and_capture_contract(self):
        mutations=[lambda a:a.summary_data.update(Stage=audit.STAGE+"-wrong"),lambda a:a.summary_data.update(MinimapViewportValidation=False),
            lambda a:a.summary_data.update(CandidateSha256="0"*64),lambda a:a.summary_data.update(Passed=None),
            lambda a:a.plan_data["source_sha256"].update({"tools/framed_minimap_probe.py":"0"*64}),
            lambda a:a.plan_data["runs"][0]["command"].append("-AllowVisibleDesktop"),
            lambda a:a.plan_data["runs"][0]["command"].append("-MinimapViewportValidation"),
            lambda a:a.plan_data["runs"][0]["command"].remove("-MinimapViewportValidation"),
            lambda a:a.plan_data["runs"][0].update(expected_source_main_lf_sha256="0"*64),
            lambda a:a.plan_data["runs"][0].update(expected_observed_main_sha256="0"*64),
            lambda a:a.plan_data["runs"][0].update(expected_probe_sha256="0"*64)]
        for mutation in mutations:
            self.reset();mutation(self.a);self.a.save();self.rejected()
        for prefix in ("PTILE_CONTRACT_PASS","FRAMED_MINIMAP_OBSERVER_BOUND"):
            for mode in ("wrong_candidate","missing","duplicate"):
                self.reset();log=self.a.log.read_text();line=next(line for line in log.splitlines() if line.startswith(prefix))
                replacement=line.replace(self.a.digest,"0"*64) if mode=="wrong_candidate" else "" if mode=="missing" else line+"\n"+line
                self.a.log.write_text(log.replace(line,replacement));self.a.save();self.rejected()

    def test_raw_png_palette_binding_and_deep_missing_perimeter_pixel(self):
        for mode in ("raw","png","png_hash","metadata_log","candidate"):
            with self.subTest(mode=mode):
                self.reset()
                if mode in ("raw","png","candidate"):
                    path={"raw":self.a.raw,"png":self.a.png,"candidate":self.a.candidate}[mode]
                    value=bytearray(path.read_bytes());value[-1]^=1;path.write_bytes(value)
                elif mode=="png_hash":self.a.summary_data["PngSha256"]="0"*64;self.a.save()
                else:
                    metadata=audit.read_json(self.a.meta);metadata["log_path"]=str(self.a.root/"foreign.log");write_json(self.a.meta,metadata)
                self.rejected()
        self.reset();raw=bytearray(self.a.raw.read_bytes());raw[56*800+580]=3;self.a.raw.write_bytes(raw)
        self.a.regenerate_png();self.a.save();report=self.rejected("perimeter pixels are incomplete")
        self.assertEqual(report["capture"]["mismatched_pixels"],1)

    def test_exclusive_cli_output_does_not_touch_existing_artifact(self):
        output=self.a.root/"preserved.json";output.write_text("keep")
        command=[sys.executable,"-B",str(Path(audit.__file__)),"--output",str(output)]
        for name in ("summary","log","probe","original"):command.extend(["--"+name,str(self.a.root/"absent")])
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,2);self.assertIn("refusing overwrite",result.stderr)
        self.assertEqual(output.read_text(),"keep")


if __name__=="__main__":unittest.main()
