#!/usr/bin/env python3
"""Synthetic offline artifact integration; never a runtime/approval fixture.

Only proprietary decoding and binary construction use explicitly synthetic
stand-ins. Trace, dump parsing, image conversion/bindings, frame/bar pixel
oracles, coverage recomputation, and final decision run their real code.
"""
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

import framed_gameplay_evidence as decision
import complete_hd_evidence as release_evidence
from cdb_surface_dump_to_png import convert
from hd_layout_asset_composition import Sprite
import test_frame_surface_audit as frame_fixture
import test_initial_map_paint_trace as trace_fixture


def write_json(path,data):path.write_text(json.dumps(data,indent=2),encoding="utf-8")


class Artifacts:
    def __init__(self,root):
        self.root=root;self.run=root/"captures"/"run";self.run.mkdir(parents=True)
        self.layout=decision.FramedViewport(800,600)
        self.original=root/"original.fixture";self.original.write_bytes(b"synthetic original; not an executable")
        self.candidate=root/"candidate.fixture";self.candidate.write_bytes(b"synthetic canonical candidate; not an executable")
        self.sha=decision.sha(self.candidate.read_bytes())
        self.frame_resource=root/"frame.fixture";self.frame_resource.write_bytes(b"synthetic frame resource")
        self.command_resource=root/"commands.fixture";self.command_resource.write_bytes(b"synthetic command resource")
        self.frame=frame_fixture.synthetic_frame()
        self.sprites={i:Sprite(64,32,tuple(20+i*16+(x+3*y)%13 for y in range(32) for x in range(64))) for i in range(12)}
        self.sprites[14]=Sprite(64,32,tuple(240 if x in (0,63) or y in (0,31) else None for y in range(32) for x in range(64)))
        self.log=self.run/"capture.log";self.probe=self.run/"partial-tile-installed.extra.cdb"
        events=trace_fixture.initial_events(framed=True)+trace_fixture.auxiliary(noop=True,world=(90,7),scroll=(10,17))
        for event in events:event["records"]=[line.replace("map=(50,50)","map=(100,100)") for line in event["records"]]
        log,probe=trace_fixture.fixture(events,stage=decision.STAGE,close="")
        log=log.replace(trace_fixture.SHA,self.sha);probe=probe.replace(trace_fixture.SHA,self.sha)
        self.canonical_probe=probe;self.probe.write_text(probe,encoding="ascii",newline="\n")
        self.vis_base=0x600000+140081;self.start=self.vis_base+10*13+(17>>3)
        last=self.vis_base+21*13+(25>>3);self.count=last-self.start+1
        log+=("SURFDUMP_REDRAW seq=3 scroll=(10,17) endgrid=(21,25) map=(100,100) surface=10000000 size=(800,600)\n"
              "SURFDUMP_READY redraw_seq=4 surface=10000000 size=(800,600) base=11000000 bytes=480000\n"
              f"SCROLL_VISDUMP player=0 screen0=(32,16) map0=(10,17) rows=9 cols=12 tile=(64,64) vis_base={self.vis_base:08x} dump_start={self.start:08x} count={self.count}\n")
        log+=self.dump_rows(bytes(self.count))
        log+=("FRAMED_MINIMAP enabled=0 origin=(0,0) size=(0,0)\n"
              "PTILE_TRACE_CLOSED tid=abc eip=00406fa0 esp=00100100\nSURFDUMP_HOST_READY\n")
        self.log.write_text(log,encoding="ascii")
        self.raw=self.run/"surface.raw";self.png=self.run/"surface.png";self.png_meta=self.run/"surface.png.json"
        raw=frame_fixture.surface(self.frame,self.layout)
        for cell in range(6):
            for y in range(32):
                for x in range(64):raw[(520+cell//3*32+y)*800+576+cell%3*64+x]=self.sprites[cell*2+1].pixels[y*64+x]
        self.raw.write_bytes(raw)
        self.coverage=self.run/"coverage.json";self.summary=self.run/"diagnostic-summary.json";self.plan=root/"run-plan.json"
        self.plan_data=dict(stage=decision.STAGE,original_sha256=decision.sha(self.original.read_bytes()),
            source_sha256={name:decision.sha((decision.ROOT/name).read_bytes()) for name in (*decision.builder.PINNED_SOURCES,*decision.PRODUCER_SOURCES)},
            runs=[dict(resolution="800x600",candidate_path=str(self.candidate),candidate_dir=str(root),workdir=str(root),
                       output_root=str(self.run.parent),expected_candidate_sha256=self.sha,
                       expected_probe_sha256=decision.sha(self.probe.read_bytes()),command=[
                "scripts/cdb/run_cdb_surface_dump.ps1","-PartialTileValidation","-InitialMapPaintValidation","-FramedValidation",
                "-Stage",decision.STAGE,"-Resolution","800x600","-WorkDir",str(root),"-CandidateDir",str(root),
                "-CandidateName",self.candidate.name,"-OutRoot",str(self.run.parent),"-UseDdrawProxy","-LoadSlot","0",
                "-FastForwardStartAnims","-RequireGameplay","-RunSeconds","180"])])
        self.summary_data=dict(Passed=False,Error="Synthetic low-coverage fixture; no game was run.",DiagnosticOnly=True,
            Stage=decision.STAGE,Resolution="800x600",CandidatePath=str(self.candidate),CandidateSha256=self.sha,
            RawPath=str(self.raw),PngPath=str(self.png),PngMetadata=str(self.png_meta),RawBytes=480000,
            Surface=dict(RedrawSeq=4,Surface="10000000",Base="11000000",Width=800,Height=600,Bytes=480000))
        self.regenerate_pixels();self.save()

    def dump_rows(self,data):
        rows=[]
        for index in range(0,len(data),16):
            values=data[index:index+16];hexes=" ".join(f"{n:02x}" for n in values)
            if len(values)>8:hexes=hexes[:23]+"-"+hexes[24:]
            rows.append(f"{self.start+index:08x}  {hexes:<47}  {'.'*len(values)}")
        return "\n".join(rows)+"\n"

    def regenerate_pixels(self):
        metadata=convert(self.raw,self.png,800,600,800,self.png_meta,self.log,None)
        self.summary_data["PngSha256"]=metadata["png_sha256"]
        write_json(self.coverage,decision.reconstruct_coverage(self.png,self.layout,dict(enabled=False,width=None,height=None)))

    def save(self):
        write_json(self.plan,self.plan_data)
        self.summary_data.update(RunPlan=decision.reference(self.plan),SourceLog=decision.reference(self.log),CoverageDiagnostic=decision.reference(self.coverage))
        write_json(self.summary,self.summary_data)

    def kwargs(self):return dict(coverage_path=self.coverage,log_path=self.log,probe_path=self.probe,
        frame_resource=self.frame_resource,command_resource=self.command_resource,original_path=self.original)

    def mocks(self):
        stack=ExitStack()
        def candidate(original,resolution):
            decision.require(original==b"synthetic original; not an executable" and resolution=="800x600","synthetic original identity rejected")
            return b"synthetic canonical candidate; not an executable",{},self.canonical_probe
        def frame(data):
            decision.require(data==b"synthetic frame resource","synthetic frame identity rejected");return self.frame
        def commands(data):
            decision.require(data==b"synthetic command resource","synthetic commands identity rejected");return self.sprites,"synthetic"
        stack.enter_context(patch.object(decision.builder,"build_candidate",side_effect=candidate))
        stack.enter_context(patch.object(decision.frame,"load_native_frame",side_effect=frame))
        stack.enter_context(patch.object(decision.bar,"load_sprites",side_effect=commands))
        return stack


class FramedGameplayEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.a=Artifacts(Path(self.temp.name));self.addCleanup(self.a.mocks().close)
        self.baseline={p:p.read_bytes() for p in self.a.root.rglob("*") if p.is_file()}
        self.plan=copy.deepcopy(self.a.plan_data);self.summary=copy.deepcopy(self.a.summary_data)

    def reset(self):
        for path,data in self.baseline.items():path.write_bytes(data)
        self.a.plan_data=copy.deepcopy(self.plan);self.a.summary_data=copy.deepcopy(self.summary)

    def evaluate(self):return decision.build_report(self.a.summary,**self.a.kwargs())
    def rejected(self,contains=None):
        result=self.evaluate();self.assertFalse(result["guarded_gameplay_evidence"],result)
        self.assertTrue(result["failures"])
        if contains:self.assertIn(contains,";".join(result["failures"]))
        return result

    def test_bound_fog_explanation_preserves_failed_inputs_and_scope(self):
        before={p:decision.sha(p.read_bytes()) for p in self.baseline}
        result=self.evaluate();self.assertTrue(result["guarded_gameplay_evidence"],result["failures"])
        self.assertFalse(result["input_passed"]);self.assertFalse(result["raw_image_gameplay_likely"])
        self.assertEqual(result["raw_image_warnings"],["low_overall_gameplay_coverage"])
        self.assertGreater(result["blank_cells"],90)
        self.assertEqual(result["blank_cells"],result["explained_blank_cells"])
        self.assertEqual(result["unexplained_blank_cells"],[])
        self.assertTrue(all(row["visibility"]==0 for row in result["visibility_zero_blank_cells"]))
        self.assertEqual(result["action_cells_verified"],6)
        for key in ("runtime_verdict_changed","manual_input_proof","promotion_ready","cleanup_proven"):self.assertFalse(result[key])
        self.assertEqual(before,{p:decision.sha(p.read_bytes()) for p in self.baseline})

    def test_canonical_candidate_probe_original_and_asset_reconstruction(self):
        for path,contains in ((self.a.original,"original identity"),(self.a.candidate,"canonical framed bytes"),
                              (self.a.probe,"loaded contract"),(self.a.frame_resource,"frame identity"),
                              (self.a.command_resource,"commands identity")):
            with self.subTest(path=path.name):
                self.reset();path.write_bytes(path.read_bytes()+b" altered")
                if path==self.a.probe:
                    self.a.plan_data["runs"][0]["expected_probe_sha256"]=decision.sha(path.read_bytes());self.a.save()
                self.rejected(contains)

    def test_probe_plan_hash_and_exact_windows_text_serialization(self):
        canonical=self.a.canonical_probe.encode("ascii")
        windows=self.a.canonical_probe.replace("\n","\r\n").encode("ascii")
        self.a.probe.write_bytes(windows)
        result=self.evaluate();self.assertTrue(result["guarded_gameplay_evidence"],result["failures"])
        self.assertEqual(result["canonical_probe_sha256"],decision.sha(canonical))
        self.assertEqual(result["sources"]["probe"]["sha256"],decision.sha(windows))
        self.a.probe.write_bytes(windows.replace(b"\r\n",b"\n",1));self.rejected("loaded contract")
        self.a.probe.write_bytes(windows)
        self.a.plan_data["runs"][0]["expected_probe_sha256"]=decision.sha(windows)
        self.a.save();self.rejected("loaded contract")

    def test_source_plan_stage_paths_commands_and_disclosures_fail_closed(self):
        mutations=[lambda a:a.summary_data.update(Stage=None),lambda a:a.summary_data.update(Stage=decision.STAGE+"-typo"),
            lambda a:a.summary_data.update(Passed=None),lambda a:a.summary_data.update(Av=True),
            lambda a:a.summary_data.update(AllowVisibleDesktop=True),lambda a:a.summary_data.update(TimedOut=True),
            lambda a:a.summary_data.update(ForceVisibleEdges=True),lambda a:a.summary_data.update(HostDumpError="failed"),
            lambda a:a.plan_data["source_sha256"].update({decision.PRODUCER_SOURCES[0]:"0"*64}),
            lambda a:a.plan_data.update(original_sha256="0"*64),
            lambda a:a.plan_data["runs"][0].update(expected_candidate_sha256="0"*64),
            lambda a:a.plan_data["runs"].append(copy.deepcopy(a.plan_data["runs"][0]))]
        for mutation in mutations:
            with self.subTest(mutation=mutations.index(mutation)):
                self.reset();mutation(self.a);self.a.save();self.rejected()
        changes=[(0,"other.ps1"),("-Stage",decision.STAGE+"-wrong"),("-Resolution","1024x768"),
                 ("-LoadSlot","1"),("-OutRoot",str(self.a.root/"elsewhere")),("-CandidateName","other.fixture"),
                 ("-WorkDir",str(self.a.root/"elsewhere")),("-RunSeconds","241")]
        for key,value in changes:
            with self.subTest(option=key):
                self.reset();command=self.a.plan_data["runs"][0]["command"]
                command[0 if key==0 else command.index(key)+1]=value;self.a.save();self.rejected()
        for extra in ("-FramedValidation","-ForceVisibleEdges","-AllowVisibleDesktop","-UseCdbWriteMem","-NotARealOption"):
            self.reset();self.a.plan_data["runs"][0]["command"].append(extra);self.a.save();self.rejected()

    def test_missing_and_foreign_artifacts_are_not_defaulted(self):
        for path in (self.a.summary,self.a.coverage,self.a.log,self.a.probe,self.a.plan,self.a.candidate):
            with self.subTest(path=path.name):
                self.reset();path.unlink();self.rejected()
        self.reset();other=self.a.root/"foreign.json";other.write_bytes(self.a.coverage.read_bytes())
        result=decision.build_report(self.a.summary,**(self.a.kwargs()|dict(coverage_path=other)))
        self.assertFalse(result["guarded_gameplay_evidence"])

    def test_snapshot_grid_player_map_surface_and_native_identity(self):
        changes=[("SCROLL_VISDUMP player=0","SCROLL_VISDUMP player=1"),("map0=(10,17)","map0=(11,17)"),
            ("rows=9 cols=12","rows=8 cols=11"),("screen0=(32,16)","screen0=(0,0)"),
            ("endgrid=(21,25)","endgrid=(22,26)"),("SURFDUMP_READY redraw_seq=4","SURFDUMP_READY redraw_seq=5"),
            ("base=11000000","base=00000000"),("bytes=480000","bytes=480001"),
            ("size=(800,600) base=","size=(800,598) base="),
            (f"vis_base={self.a.vis_base:08x}",f"vis_base={self.a.vis_base+1:08x}"),
            ("gd=00600000","gd=00600001"),("endgrid=(21,25) map=(100,100)","endgrid=(21,25) map=(100,99)"),
            ("FRAMED_MINIMAP enabled=0 origin=(0,0) size=(0,0)","FRAMED_MINIMAP enabled=1 origin=(553,16) size=(214,214)")]
        for old,new in changes:
            with self.subTest(old=old):
                self.reset();log=self.a.log.read_text();self.assertIn(old,log)
                self.a.log.write_text(log.replace(old,new));self.a.save();self.rejected()

    def test_measured_enabled_minimap_and_supported_world_sizes(self):
        log=self.a.log.read_text().replace("FRAMED_MINIMAP enabled=0 origin=(0,0) size=(0,0)",
                                         "FRAMED_MINIMAP enabled=1 origin=(554,16) size=(214,214)")
        # A source-consistent smaller world remains valid when the complete
        # ceiling window is in bounds; the decision must not hardcode 100x100.
        log=log.replace("map=(100,100)","map=(100,99)");self.a.log.write_text(log)
        write_json(self.a.coverage,decision.reconstruct_coverage(self.a.png,self.a.layout,
                    dict(enabled=True,width=214,height=214)))
        self.a.save();result=self.evaluate()
        self.assertTrue(result["guarded_gameplay_evidence"],result["failures"])
        self.assertEqual(result["snapshot"]["map_size"],[100,99])
        self.assertEqual(result["snapshot"]["minimap"],dict(enabled=True,width=214,height=214))
        for old,new in (("size=(214,214)","size=(0,214)"),("size=(214,214)","size=(800,214)"),
                        ("map=(100,99)","map=(20,99)")):
            self.a.log.write_text(log.replace(old,new));self.a.save();self.rejected()

    def test_single_complete_paused_span_and_trace_are_required(self):
        for prefix in ("SCROLL_VISDUMP","SURFDUMP_READY","FRAMED_MINIMAP","PTILE_TRACE_CLOSED","SURFDUMP_HOST_READY"):
            for mode in ("missing","duplicate"):
                with self.subTest(prefix=prefix,mode=mode):
                    self.reset();rows=self.a.log.read_text().splitlines();index=next(i for i,row in enumerate(rows) if row.startswith(prefix))
                    if mode=="missing":del rows[index]
                    else:rows.insert(index,rows[index])
                    self.a.log.write_text("\n".join(rows)+"\n");self.a.save();self.rejected()
        for mode in ("missing_bytes","duplicate_bytes","wrong_address","truncated_byte","extra_bytes","event_inside_dump","unclosed_call","av"):
            with self.subTest(mode=mode):
                self.reset();rows=self.a.log.read_text().splitlines();i=next(i for i,row in enumerate(rows) if row.startswith("SCROLL_VISDUMP"))+1
                if mode=="missing_bytes":del rows[i]
                elif mode=="duplicate_bytes":rows.insert(i,rows[i])
                elif mode=="wrong_address":rows[i]=f"{self.a.start+1:08x}"+rows[i][8:]
                elif mode=="truncated_byte":rows[i]=rows[i][:10]+"xx"+rows[i][12:]
                elif mode=="extra_bytes":rows.insert(i+1,f"{self.a.start+self.a.count:08x}"+rows[i][8:])
                elif mode=="event_inside_dump":rows.insert(i,"SURFDUMP_REDRAW unexpected")
                elif mode=="unclosed_call":rows=[row for row in rows if not row.startswith("PTILE_NATIVE_NOOP_EXIT")]
                elif mode=="av":rows.insert(0,"AV_SURFDUMP exception=c0000005")
                self.a.log.write_text("\n".join(rows)+"\n");self.a.save();self.rejected()

    def test_historical_zero_cannot_excuse_current_visible_blank(self):
        result=self.evaluate();self.assertTrue(result["guarded_gameplay_evidence"],result["failures"])
        cell=result["visibility_zero_blank_cells"][0];data=bytearray(self.a.count)
        data[cell["address"]-self.a.start]|=1<<(cell["world"][1]&7)
        log=self.a.log.read_text();log=log.replace(self.a.dump_rows(bytes(self.a.count)),self.a.dump_rows(data))
        # Historical point trace is deliberately present, but never used by the
        # current decision. Existing parser's any-zero precedence is irrelevant.
        log="SCROLL_VIS player=0 screen=(32,16) world=(10,17) value=0\n"+log
        self.a.log.write_text(log);self.a.save();self.rejected("blank cell lacks zero visibility")

    def test_optimistic_coverage_fields_cannot_replace_recomputed_pixels(self):
        original=decision.read_json(self.a.coverage)
        mutations=[lambda d:d["images"][0]["frame_check"].update(gameplay_frame_likely=True),
            lambda d:d["images"][0]["frame_check"].update(warnings=[]),
            lambda d:d["images"][0]["cells"][0].update(flags=[]),
            lambda d:d["images"][0]["summary"].update(possible_stale_or_solid_active_cells=1),
            lambda d:d["parameters"].update(min_gameplay_overall_percent=0)]
        for i,mutation in enumerate(mutations):
            with self.subTest(mutation=i):
                self.reset();data=copy.deepcopy(original);mutation(data);write_json(self.a.coverage,data);self.a.save();self.rejected("coverage report differs")

    def test_one_source_pixel_cannot_be_excused_by_visibility(self):
        for x,y,claim in ((799,300,"frame bands"),(400,599,"frame bands"),(240,587,"frame bands"),(577,521,"six complete")):
            with self.subTest(pixel=(x,y)):
                self.reset();raw=bytearray(self.a.raw.read_bytes());raw[y*800+x]^=1;self.a.raw.write_bytes(raw)
                self.a.regenerate_pixels();self.a.save();self.rejected(claim)

    def test_raw_png_metadata_and_summary_bindings_are_rechecked(self):
        for mode in ("raw","png","metadata_hash","metadata_log","summary_png_hash","coverage_hash","plan_hash"):
            with self.subTest(mode=mode):
                self.reset()
                if mode in ("raw","png"):
                    path=self.a.raw if mode=="raw" else self.a.png;data=bytearray(path.read_bytes());data[-1]^=1;path.write_bytes(data)
                elif mode.startswith("metadata"):
                    data=decision.read_json(self.a.png_meta)
                    data["log_path" if mode=="metadata_log" else "raw_sha256"]=str(self.a.root/"foreign.log") if mode=="metadata_log" else "0"*64
                    write_json(self.a.png_meta,data)
                else:
                    data=decision.read_json(self.a.summary)
                    if mode=="summary_png_hash":data["PngSha256"]="0"*64
                    else:data["CoverageDiagnostic" if mode=="coverage_hash" else "RunPlan"]["sha256"]="0"*64
                    write_json(self.a.summary,data)
                self.rejected()

    def test_existing_cli_output_is_never_overwritten(self):
        output=self.a.root/"exclusive.json";output.write_text("preserve me")
        command=[sys.executable,"-B",str(Path(decision.__file__)),"--output",str(output)]
        for name in ("summary","coverage","log","probe","frame-resource","command-resource","original"):
            command.extend(["--"+name,str(self.a.root/"missing")])
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,2);self.assertIn("refusing overwrite",result.stderr)
        self.assertEqual(output.read_text(),"preserve me")


class CompleteGameplayEvidenceTests(unittest.TestCase):
    """Exercise the real shared bundle verifier with a synthetic builder only."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.a=Artifacts(Path(self.temp.name));self.addCleanup(self.a.mocks().close)
        self.stage=decision.complete_context.complete.STAGE
        self.inherited=decision.STAGE.removesuffix('-validation')+'-modalcanvas-army-validation'
        self.a.candidate=self.a.candidate.rename(self.a.root/'candidate.exe')
        identity=f'resolution=800x600 candidate_sha256={self.a.sha}'
        army=f'ARMY_CONTRACT_PASS stage={self.inherited} {identity} revision=synthetic_army_v1'
        complete=f'COMPLETEHD_CONTRACT_PASS stage={self.stage} {identity} revision=complete_hd_v1'
        ptile=f'PTILE_CONTRACT_PASS stage={self.inherited} {identity}'
        old=f'PTILE_CONTRACT_PASS stage={decision.STAGE} {identity}'
        log=self.a.log.read_text().replace(old,army+'\n'+complete+'\n'+ptile)
        self.a.log.write_text(log,encoding='ascii')
        self.a.canonical_probe=self.a.canonical_probe.replace('.echo '+old,
            '.echo '+army+'\n.echo '+complete+'\n.echo '+ptile)
        self.a.probe.write_text(self.a.canonical_probe,encoding='ascii',newline='\n')
        self.bundle_probe=self.a.root/'candidate.cdb';self.bundle_probe.write_bytes(self.a.probe.read_bytes())
        self.manifest=self.a.root/'candidate.candidate.json'
        self.metadata=dict(schema=1,stage=self.stage,resolution='800x600',recipe_revision='complete_hd_v1',
            base_sha256=decision.sha(self.a.original.read_bytes()),candidate_sha256=self.a.sha,
            probe_sha256=decision.sha(self.bundle_probe.read_bytes()),
            source_hashes={'src/patcher/complete_hd_candidate.py':decision.sha((decision.ROOT/'src/patcher/complete_hd_candidate.py').read_bytes())},
            patch_records=[dict(synthetic_fixture=True)],
            predecessor=dict(stage=self.inherited,army_revision='synthetic_army_v1',
                base_candidate=dict(base_candidate=dict(stage=decision.STAGE))))
        write_json(self.manifest,self.metadata)
        self.a.summary_data.update(Stage=self.stage,CandidatePath=str(self.a.candidate),
            CandidateManifest=str(self.manifest),CandidateManifestSha256=decision.sha(self.manifest.read_bytes()),
            RecipeRevision='complete_hd_v1',CandidateProbeSha256=self.metadata['probe_sha256'],
            Failures=['Synthetic initial image-heuristic failure remains recorded.'])
        self.a.plan_data['stage']=self.stage
        self.a.plan_data['source_sha256'].update({name:decision.sha((decision.ROOT/name).read_bytes())
            for name in (*decision.COMPLETE_PRODUCER_SOURCES,*self.metadata['source_hashes'])})
        run=self.a.plan_data['runs'][0]
        run.update(candidate_path=str(self.a.candidate),expected_probe_sha256=self.metadata['probe_sha256'])
        command=run['command'];command[command.index('-Stage')+1]=self.stage
        command[command.index('-CandidateName')+1]=self.a.candidate.name
        command[:]=[value for value in command if value not in
                    ('-PartialTileValidation','-InitialMapPaintValidation','-FramedValidation')]
        command.append('-CompleteHdValidation')
        self.context=dict(manifest=self.metadata,candidate=self.a.candidate.read_bytes(),probe=self.a.canonical_probe,
            framed=dict(stage=decision.STAGE),inherited_stage=self.inherited,
            manifest_path=str(self.manifest.resolve()),manifest_sha256=decision.sha(self.manifest.read_bytes()))
        write_json(self.a.coverage,decision.reconstruct_coverage(self.a.png,self.a.layout,
            dict(enabled=False,width=None,height=None),context=self.context))
        self.a.save()
        stack=ExitStack();self.addCleanup(stack.close)
        stack.enter_context(patch.object(release_evidence,'BASE_SHA256',self.metadata['base_sha256']))
        stack.enter_context(patch.object(release_evidence,'CANDIDATE_ROOT',self.a.root))
        def build(original,resolution):
            decision.require(original==b'synthetic original; not an executable' and resolution=='800x600',
                             'synthetic complete original identity rejected')
            return b'synthetic canonical candidate; not an executable',copy.deepcopy(self.metadata),self.a.canonical_probe
        stack.enter_context(patch.object(decision.complete_context.complete,'build_candidate',side_effect=build))
        self.baseline={p:p.read_bytes() for p in self.a.root.rglob('*') if p.is_file()}

    def reset(self):
        for path,data in self.baseline.items():path.write_bytes(data)

    def evaluate(self):
        return decision.build_report(self.a.summary,**self.a.kwargs(),candidate_manifest_path=self.manifest)

    def rejected(self,contains=None):
        result=self.evaluate();self.assertFalse(result['guarded_gameplay_evidence'],result)
        if contains:self.assertIn(contains,';'.join(result['failures']))
        return result

    def test_complete_rebuild_preserves_stage_failed_inputs_and_framed_pixel_contract(self):
        before={p:decision.sha(p.read_bytes()) for p in self.baseline}
        result=self.evaluate();self.assertTrue(result['guarded_gameplay_evidence'],result['failures'])
        self.assertEqual(result['stage'],self.stage)
        self.assertEqual(result['candidate_context'],decision.candidate_identity(self.context))
        self.assertFalse(result['input_passed']);self.assertFalse(result['runtime_verdict_changed'])
        self.assertEqual(result['input_failures'],self.a.summary_data['Failures'])
        self.assertEqual(result['action_cells_verified'],6);self.assertFalse(result['promotion_ready'])
        self.assertEqual(before,{p:decision.sha(p.read_bytes()) for p in self.baseline})

    def test_complete_stage_requires_manifest_and_never_accepts_legacy_coverage(self):
        result=decision.build_report(self.a.summary,**self.a.kwargs())
        self.assertFalse(result['guarded_gameplay_evidence'])
        for mutation in (lambda d:d.pop('candidate_context'),
                         lambda d:d['candidate_context'].update(resolution='1024x768'),
                         lambda d:d['candidate_context'].update(candidate_sha256='0'*64),
                         lambda d:d['candidate_context'].update(recipe_revision='other'),
                         lambda d:d['framed_profile'].update(stage=self.stage)):
            self.reset();data=decision.read_json(self.a.coverage);mutation(data);write_json(self.a.coverage,data)
            summary=decision.read_json(self.a.summary);summary['CoverageDiagnostic']=decision.reference(self.a.coverage)
            write_json(self.a.summary,summary);self.rejected('coverage report differs')

    def test_bundle_and_summary_identity_mismatches_fail_even_if_claims_are_rehashed(self):
        for key,value in (('CandidateManifestSha256','0'*64),('RecipeRevision','other'),
                          ('CandidateProbeSha256','0'*64),('Stage',decision.STAGE),('Resolution','1024x768')):
            self.reset();summary=decision.read_json(self.a.summary);summary[key]=value
            write_json(self.a.summary,summary);self.rejected()
        for path in (self.a.candidate,self.bundle_probe,self.manifest):
            self.reset();path.write_bytes(path.read_bytes()+b' ')
            summary=decision.read_json(self.a.summary)
            summary['CandidateManifestSha256']=decision.sha(self.manifest.read_bytes())
            write_json(self.a.summary,summary);self.rejected()
        self.reset();manifest=decision.read_json(self.manifest);manifest['source_hashes']={}
        write_json(self.manifest,manifest);summary=decision.read_json(self.a.summary)
        summary['CandidateManifestSha256']=decision.sha(self.manifest.read_bytes());write_json(self.a.summary,summary)
        self.rejected('source reconstruction')

    def test_missing_repeated_or_mismatched_loaded_contracts_and_trace_never_pass(self):
        original=self.a.log.read_text()
        for prefix in ('COMPLETEHD_CONTRACT_PASS','ARMY_CONTRACT_PASS','PTILE_CONTRACT_PASS'):
            for mode in ('missing','duplicate','mismatched'):
                self.reset();rows=original.splitlines();index=next(i for i,line in enumerate(rows) if line.startswith(prefix))
                if mode=='missing':del rows[index]
                elif mode=='duplicate':rows.insert(index,rows[index])
                else:rows[index]=rows[index].replace(self.a.sha,'0'*64)
                self.a.log.write_text('\n'.join(rows)+'\n');self.update_log_binding();self.rejected('initial trace failed')
        self.reset();self.a.log.write_text(original.replace('PTILE_NATIVE_NOOP_EXIT','REMOVED_NATIVE_NOOP_EXIT'))
        self.update_log_binding();self.rejected('initial trace failed')

    def update_log_binding(self):
        summary=decision.read_json(self.a.summary);summary['SourceLog']=decision.reference(self.a.log)
        write_json(self.a.summary,summary)

    def test_complete_visibility_still_requires_one_matching_paused_snapshot(self):
        baseline=self.evaluate();self.assertTrue(baseline['guarded_gameplay_evidence'],baseline['failures'])
        point=baseline['visibility_zero_blank_cells'][0];data=bytearray(self.a.count)
        data[point['address']-self.a.start]|=1<<(point['world'][1]&7)
        log=self.a.log.read_text().replace(self.a.dump_rows(bytes(self.a.count)),self.a.dump_rows(data))
        self.a.log.write_text('SCROLL_VIS player=0 screen=(32,16) world=(10,17) value=0\n'+log)
        self.update_log_binding();self.rejected('blank cell lacks zero visibility')
        self.reset();log=self.a.log.read_text();line=next(row for row in log.splitlines() if row.startswith('FRAMED_MINIMAP'))
        self.a.log.write_text(log.replace(line,line+'\n'+line));self.update_log_binding()
        self.rejected('expected one FRAMED_MINIMAP')


if __name__=="__main__":unittest.main()
