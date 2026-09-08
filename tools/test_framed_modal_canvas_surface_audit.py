"""Synthetic artifact/protocol/pixel fixtures; no game, debugger or real candidate output."""
from __future__ import annotations

from contextlib import ExitStack
import copy
from datetime import datetime, timezone
import json
import io
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest.mock import patch

import framed_modal_canvas_surface_audit as audit
import test_framed_modal_canvas_trace as trace_fixture
import test_initial_map_paint_trace as initial_fixture
import test_frame_surface_audit as frame_fixture
from hd_layout_asset_composition import Sprite
from cdb_surface_dump_to_png import convert


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def identity(proc_id, path, when, **extra):
    instant = datetime.fromisoformat(when.replace("Z", "+00:00"))
    epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
    delta = instant - epoch
    return dict(process_id=proc_id, path=str(path), creation_utc=when,
                creation_filetime=(delta.days * 86400 + delta.seconds) * 10000000 + delta.microseconds * 10,
                handle_retained=True, **extra)


class Artifacts:
    """Mock only binary recipe/PE mapping, source assets and isolated temp roots.

    Real producer command assembly, loaded-byte checks, packet equality, initial
    and modal trace validators, process/PNG bindings and pixel oracles execute.
    Synthetic bytes cannot be launched as a PE; no proprietary candidate is saved.
    """
    def __init__(self, root, route="school", availability="existing_flags"):
        self.root = root; self.run = root / "capture"; self.run.mkdir()
        self.candidate_dir = root / "candidate"; self.candidate_dir.mkdir()
        self.original = root / "original.fixture"; self.input = root / "input.fixture"
        self.candidate = self.candidate_dir / "candidate.fixture"
        producer = audit.trace.producer
        original = bytearray(b"synthetic non-PE fixture\0" + bytes(0x180000))
        spans = dict(producer.COMMON)
        for row in producer.ROUTES.values():
            if row.name != "castle_overview": spans[row.entry_va] = row.entry_bytes
            spans.update(producer._native_spans(row))
            spans[row.present_call_va] = (b"\xe8" + struct.pack("<i", producer.PRESENT - row.stop_va)).hex()
            spans[row.stop_va] = row.return_bytes
            if row.branch_va is not None:
                spans[row.branch_va] = (b"\xb9" + struct.pack("<I", row.entry_va)).hex()
        for va, data in spans.items():
            offset = va - 0x400000; original[offset:offset + len(bytes.fromhex(data))] = bytes.fromhex(data)
        self.original_bytes = bytes(original)
        self.image = self.original_bytes + b" synthetic framed validation image"
        self.original.write_bytes(self.original_bytes); self.input.write_bytes(self.image); self.candidate.write_bytes(self.image)
        self.digest = audit.sha(self.image)
        self.extra = initial_fixture.fixture(stage=producer.STAGE, close="")[1].replace(initial_fixture.SHA, self.digest)
        self.template = audit.trace.render_probe(audit.trace.BASE_PROBE.read_text(encoding="utf-8-sig"), "800x600", producer.builder.BASE_STAGE)["template"]
        self.template = re.sub(r"(?m)^g$", lambda _: self.extra.strip() + "\ng", self.template)
        self.metadata = dict(source_sha256={"synthetic_recipe": audit.sha(self.image)}, state_va=0x596000,
            modal_observer_vas={"root_after_replayed_pushes":0x5767B0,"overview_after_native_draw":0x5767E0},
            modal_state_offsets=dict(producer.canvas.STATE), modal_entry_vas={"synthetic":0x576000})
        self.frame = frame_fixture.synthetic_frame()
        self.sprites = {i: Sprite(64, 32, tuple(20 + i * 16 + (x + 3 * y) % 13
                            for y in range(32) for x in range(64))) for i in range(12)}
        self.sprites[14] = Sprite(64, 32, tuple(None for _ in range(2048)))
        self.frame_resource = root / "frame.fixture"; self.frame_resource.write_bytes(b"synthetic frame resource")
        self.command_resource = root / "commands.fixture"; self.command_resource.write_bytes(b"synthetic command resource")
        self.source_paths = dict(audit.SOURCE_PATHS)
        for key in ("python", "cdb"):
            self.source_paths[key] = root / (key + ".fixture")
            self.source_paths[key].write_bytes(("synthetic " + key).encode())
        self.proxy_input = root / "ddraw.dll"; self.proxy_input.write_bytes(b"synthetic non-PE proxy")
        self.proxy = self.candidate_dir / "ddraw.dll"; self.proxy.write_bytes(self.proxy_input.read_bytes())
        self.proxy_manifest = root / "proxy.json"
        write_json(self.proxy_manifest, dict(generated_by="clash-hd-surface-dump-proxy",
            source=str(self.source_paths["proxy_source"]), source_sha256=audit.sha(self.source_paths["proxy_source"].read_bytes()),
            output=str(self.proxy_input), output_sha256=audit.sha(self.proxy_input.read_bytes())))
        self.palette = self.candidate_dir / "ddraw_surfdump_palette.bin"
        self.palette.write_bytes(bytes(v for i in range(256) for v in (i, (i * 3) % 256, (i * 7) % 256, 0)))
        self.log = self.run / "cdb.log"; self.probe = self.run / "framed-modal-canvas.cdb"
        self.packet_path = self.run / "packet.json"; self.plan_path = self.run / "plan.json"
        self.raw = self.run / "surface.raw"; self.png = self.run / "surface.png"
        self.meta = self.run / "surface.png.json"; self.summary_path = self.run / "summary.json"
        with self.mocks():
            self.packet = producer.build_screen_probe(self.original_bytes, self.image, candidate_sha256=self.digest,
                stage=producer.STAGE, resolution="800x600", route=route, availability=availability,
                castle_index=0, rendered_probe=self.template, minimap_viewport=False)
            self.probe.write_bytes(audit.trace.compile_probe(self.packet).encode("ascii"))
            self.log.write_bytes(trace_fixture.log_fixture(self.packet, self.extra).encode("ascii"))
            self.trace = audit.trace.evaluate_trace(self.log.read_text(), original=self.original_bytes,
                candidate=self.image, packet=self.packet, generated_probe=self.probe.read_bytes())
        self.prefix = self.run / "capture-prefix.log"; self.prefix.write_bytes(self.log.read_bytes())
        self.trace["source"]["log_raw_sha256"] = audit.sha(self.log.read_bytes())
        if not self.trace["passed"]:
            raise AssertionError(self.trace["failures"])
        self.plan = dict(schema="clash95_framed_modal_canvas_capture_plan_v1", environment="hidden_cdb_host", execute=True,
            stage=producer.STAGE, resolution="800x600", width=800, height=600, route=route, castle_index=0,
            availability=availability, minimap_viewport=False, deadline_seconds=120,
            original=str(self.original), original_sha256=audit.sha(self.original_bytes), input_candidate=str(self.input),
            candidate_sha256=self.digest, candidate_dir=str(self.candidate_dir), candidate_path=str(self.candidate),
            work_dir=str(root), out_dir=str(self.run), proxy_manifest=str(self.proxy_manifest),
            proxy_manifest_sha256=audit.sha(self.proxy_manifest.read_bytes()), proxy_input=str(self.proxy_input),
            proxy_path=str(self.proxy), proxy_sha256=audit.sha(self.proxy.read_bytes()), palette_path=str(self.palette),
            probe_sha256=audit.sha(self.probe.read_bytes()), canvas_state_va=self.packet["canvas_state_va"],
            canvas_state_offsets=self.packet["canvas_state_offsets"],stop_va=self.packet["stop_va"],
            child_environment=dict(CLASH_PROXY_PRESENT="0", parent_environment_modified=False),
            manual_input_proof=False, visible_composition_proof=False, promotion_ready=False)
        for key, path in self.source_paths.items():
            self.plan[key] = str(path); self.plan[audit.SOURCE_HASH_KEYS[key]] = audit.sha(path.read_bytes())
        cdb = identity(123, self.plan["cdb"], "2026-09-06T00:00:01Z")
        game = identity(456, self.candidate, "2026-09-06T00:00:02Z", parent_process_id=123, candidate_sha256=self.digest)
        self.summary = dict(schema="clash95_framed_modal_canvas_capture_v1", passed=True, status="bounded_hidden_modal_canvas_capture",
            executed=True, launch_attempted=True, plan=self.plan, started_at="2026-09-06T00:00:00Z", finished_at="2026-09-06T00:00:10Z",
            failures=[], trace=self.trace, cdb=cdb, candidates=[game],
            hidden_desktop="ClashCanvasScreen_" + "a" * 32,
            command_line=audit.launch_command(self.plan),
            cleanup=dict(cdb=dict(identity=cdb, absent=True, termination_requested=True, handle_closed=True),
                candidates=[dict(identity=game, absent=True, termination_requested=False, handle_closed=True)], desktop_closed=True),
            postrun_identity=dict(original_sha256=self.plan["original_sha256"], input_candidate_sha256=self.digest,
                                  candidate_sha256=self.digest, proxy_sha256=self.plan["proxy_sha256"]),
            manual_input_proof=False, visible_composition_proof=False, promotion_ready=False)
        native=bytes((1+x*3+y*7)%256 for y in range(480) for x in range(640))
        physical=bytearray(800*600)
        for y in range(480): physical[(60+y)*800+80:(60+y)*800+720]=native[y*640:(y+1)*640]
        self.raw.write_bytes(physical); (self.run/"native-surface.raw").write_bytes(native)
        self.create_snapshot()
        self.rebuild_final()
        self.regenerate(); self.save()

    def mocks(self):
        stack = ExitStack()
        def canonical(original, resolution, *, minimap_viewport=False):
            audit.require(original == self.original_bytes and resolution == "800x600" and minimap_viewport is False,
                          "synthetic canonical image identity rejected")
            return self.image, self.metadata, self.extra, self.template
        def read(image, va, size):
            audit.require(image in (self.image, self.original_bytes), "unknown synthetic input image")
            offset = va - 0x400000
            return offset, image[offset:offset + size]
        stack.enter_context(patch.object(audit.trace.producer, "canonical_template", side_effect=canonical))
        stack.enter_context(patch.object(audit.trace.producer, "_read", side_effect=read))
        stack.enter_context(patch.object(audit, "SOURCE_PATHS", self.source_paths))
        def isolated(plan, directory):
            audit.require(Path(plan["out_dir"]) == self.run and directory == self.run, "wrong synthetic capture directory")
            audit.require(Path(plan["candidate_path"]) == self.candidate, "wrong synthetic candidate path")
        stack.enter_context(patch.object(audit, "check_isolation", side_effect=isolated))
        def native(data):
            audit.require(data == b"synthetic frame resource", "frame resource identity rejected")
            return self.frame
        def sprites(data):
            audit.require(data == b"synthetic command resource", "command resource identity rejected")
            return self.sprites, audit.sha(data)
        stack.enter_context(patch.object(audit.frame, "load_native_frame", side_effect=native))
        stack.enter_context(patch.object(audit.action_bar, "load_sprites", side_effect=sprites))
        return stack

    def create_snapshot(self):
        ready=next(r['values'] for r in self.trace['modal_sequence']['raw_records']
                   if r['marker']=='MCAP_CANVAS' and r['values'].get('event')=='READY')
        state=bytearray(128)
        expected=dict(phase=1, physical=ready['physical'], native=ready['native'], saved_render=ready['physical'],
            root_esp=ready['root_esp'],owner_tid=ready['tid'],enter_status=1,mirror_status=1,leave_status=0,
            fault=0,allocations=1,frees=0,mirrors=ready['mirrors'],pending_header=0,pending_pixels=0,
            native_pixels=ready['native_pixels'],physical_pixels=ready['physical_pixels'])
        for k,v in expected.items():struct.pack_into('<I',state,self.packet['canvas_state_offsets'][k],v)
        headers={}
        for name,w,h,base in [('physical_header',800,600,ready['physical_pixels']),('native_header',640,480,ready['native_pixels'])]:
            data=bytearray(188);struct.pack_into('<HHI',data,0,w,h,base);struct.pack_into('<I',data,184,0x50EE24);headers[name]=bytes(data)
        content=dict(state=bytes(state),e0=struct.pack('<I',ready['native']),**headers)
        addresses=dict(state=self.packet['canvas_state_va'],e0=0x5202e0,physical_header=ready['physical'],native_header=ready['native'])
        reads={}
        for phase in ('before','after'):
            reads[phase]={}
            for name,data in content.items():
                path=self.run/f'surface.-{phase}-{name}.raw';path.write_bytes(data)
                reads[phase][name]=dict(path=str(path),address=addresses[name],bytes=len(data),sha256=audit.sha(data))
        (self.run/'native-surface.header.bin').write_bytes(headers['native_header'])
        self.summary['snapshot']=dict(path=str(self.raw),sha256=audit.sha(self.raw.read_bytes()),bytes=480000,width=800,height=600,pitch=800,
            pixel_reads=1,physical_header_reads=2,native_header_reads=2,state_reads=2,e0_reads=2,paused=True,
            capture='owned_physical_mirror',state_va=self.packet['canvas_state_va'],physical=ready['physical'],physical_pixels=ready['physical_pixels'],
            started_at='2026-09-06T00:00:03Z',captured_at='2026-09-06T00:00:04Z',game_identity=self.summary['candidates'][0],reads=reads,
            native=dict(path=str(self.run/'native-surface.raw'),sha256=audit.sha((self.run/'native-surface.raw').read_bytes()),bytes=307200,
                width=640,height=480,pitch=640,surface=ready['native'],base=ready['native_pixels'],pixel_reads=1,header=reads['before']['native_header']))

    def rebuild_final(self):
        with self.mocks():
            self.final=audit.trace.evaluate_trace(self.log.read_text(encoding='utf8'),original=self.original_bytes,candidate=self.image,
                packet=self.packet,generated_probe=self.probe.read_bytes())
        self.final['source']['log_raw_sha256']=audit.sha(self.log.read_bytes())
        self.summary['final_trace']=self.final
        self.summary['capture_prefix']=dict(path=str(self.prefix),sha256=audit.sha(self.prefix.read_bytes()),bytes=len(self.prefix.read_bytes()))
        self.summary['final_log']=dict(path=str(self.log),sha256=audit.sha(self.log.read_bytes()),bytes=len(self.log.read_bytes()),capture_prefix_preserved=True)

    def regenerate(self):
        self.summary["png"] = convert(self.raw, self.png, 800, 600, 800, self.meta, self.prefix, self.palette)
        self.summary['snapshot']['sha256']=audit.sha(self.raw.read_bytes())
        self.summary['snapshot']['native']['sha256']=audit.sha((self.run/'native-surface.raw').read_bytes())
        self.summary["palette"] = dict(path=str(self.palette), sha256=audit.sha(self.palette.read_bytes()), bytes=1024)

    def save(self):
        write_json(self.packet_path, self.packet); write_json(self.plan_path, self.plan)
        self.summary['packet']=dict(path=str(self.packet_path),sha256=audit.sha(self.packet_path.read_bytes()))
        self.summary['probe']=dict(path=str(self.probe),sha256=audit.sha(self.probe.read_bytes()))
        write_json(self.run / "trace.json", self.trace);write_json(self.run/'trace-final.json',self.final)
        write_json(self.summary_path, self.summary)

    def evaluate(self):
        return audit.build_report(self.summary_path, frame_resource=self.frame_resource,
                                  command_resource=self.command_resource, original_path=self.original)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.a=Artifacts(Path(self.temp.name));self.addCleanup(self.a.mocks().close)
        self.files={p:p.read_bytes() for p in self.a.root.rglob('*') if p.is_file()}
        self.objects=copy.deepcopy((self.a.summary,self.a.plan,self.a.packet,self.a.trace,self.a.final))

    def reset(self):
        for path,data in self.files.items():path.write_bytes(data)
        self.a.summary,self.a.plan,self.a.packet,self.a.trace,self.a.final=copy.deepcopy(self.objects)
        self.a.summary['plan']=self.a.plan;self.a.summary['trace']=self.a.trace;self.a.summary['final_trace']=self.a.final

    def rejected(self,contains=None):
        report=self.a.evaluate()
        self.assertTrue(report['failures'],report)
        if contains:self.assertIn(contains,'; '.join(report['failures']))
        self.assertFalse(report['visual_proof']);self.assertFalse(report['runtime_verdict_changed'])
        return report

    def receipt_mutation(self,phase,name,offset,value,*,both=False):
        for current in (('before','after') if both else (phase,)):
            receipt=self.a.summary['snapshot']['reads'][current][name];path=Path(receipt['path'])
            data=bytearray(path.read_bytes());data[offset:offset+len(value)]=value;path.write_bytes(data)
            receipt['sha256']=audit.sha(data)
        if name=='native_header' and (phase=='before' or both):
            (self.a.run/'native-surface.header.bin').write_bytes(Path(self.a.summary['snapshot']['reads']['before'][name]['path']).read_bytes())
        self.a.save()

    def test_exact_native_mirror_has_bound_pixels_but_no_modal_visual_claim(self):
        report=self.a.evaluate()
        self.assertEqual(report['failures'],[])
        self.assertTrue(report['source_authenticated']);self.assertTrue(report['capture_binding_verified'])
        self.assertTrue(report['mirror_relation_passed']);self.assertTrue(report['native_content_bearing'])
        self.assertEqual(report['mirror']['counts']['native_copy_mismatches'],0)
        self.assertEqual(report['mirror']['counts']['margin_nonzero_pixels'],0)
        self.assertTrue(report['mirror_margin_color']['all_margin_pixels_verified_rgb_black'])
        self.assertTrue(report['snapshot_binding']['before_after_state_e0_headers_equal'])
        self.assertTrue(report['trace_binding']['final_trace_passed'])
        self.assertFalse(report['frame_pixels_passed'])
        self.assertFalse(report['frame_applicability']['evaluated_as_gate'])
        self.assertEqual(report['action_bar']['matching_cell_count'],0)
        self.assertFalse(report['action_bar']['evaluated_as_gate'])
        self.assertEqual([x['anchor'] for x in report['action_bar']['cells']],
                         [[576,520],[640,520],[704,520],[576,552],[640,552],[704,552]])
        for key in ('modal_controls_accepted','visual_proof','manual_input_proof','visible_composition_proof','promotion_ready'):
            self.assertFalse(report[key])
        self.assertFalse(report['mirror']['runtime_binding_verified'])
        self.assertEqual(self.files,{p:p.read_bytes() for p in self.files})

    def test_bound_pixel_mismatches_and_blank_content_do_not_forge_artwork(self):
        for x,y,region in ((80,60,'native_copy'),(0,0,'margin'),(799,599,'margin')):
            with self.subTest(region=region,x=x):
                self.reset();data=bytearray(self.a.raw.read_bytes());data[y*800+x]^=1
                self.a.raw.write_bytes(data);self.a.regenerate();self.a.save()
                report=self.a.evaluate();self.assertEqual(report['failures'],[])
                self.assertTrue(report['capture_binding_verified']);self.assertFalse(report['mirror_relation_passed'])
                self.assertEqual(report['mirror']['counts']['total_mismatches'],1)
                self.assertEqual(report['mirror']['mismatch_coordinates'][0]['region'],region)
        self.reset();self.a.raw.write_bytes(bytes(480000));(self.a.run/'native-surface.raw').write_bytes(bytes(307200))
        self.a.regenerate();self.a.save();report=self.a.evaluate()
        self.assertTrue(report['mirror_relation_passed'],report['failures'])
        self.assertFalse(report['native_content_bearing']);self.assertFalse(report['visual_proof'])

    def test_index_zero_margin_is_not_called_black_with_a_nonblack_palette(self):
        palette=bytearray(self.a.palette.read_bytes());palette[:3]=bytes((17,23,41));self.a.palette.write_bytes(palette)
        self.a.regenerate();self.a.save();report=self.a.evaluate()
        self.assertTrue(report['mirror_relation_passed'],report['failures'])
        self.assertEqual(report['mirror_margin_color']['palette_zero_rgb'],[17,23,41])
        self.assertFalse(report['mirror_margin_color']['all_margin_pixels_verified_rgb_black'])
        self.assertFalse(report['visual_proof'])

    def test_saved_cleanup_and_late_trace_failures_remain_failed_with_coherent_pixels(self):
        self.a.summary.update(passed=False,status='failed',failures=['owned desktop close failed'])
        self.a.summary['cleanup']['desktop_closed']=False;self.a.save()
        report=self.a.evaluate();self.assertTrue(report['mirror_relation_passed'],report['failures'])
        self.assertFalse(report['input_runtime_passed']);self.assertFalse(report['process_observations']['recorded_owned_process_cleanup_verified'])
        self.reset();self.a.log.write_bytes(self.a.log.read_bytes()+b'MCAP_REJECT reason=actual_late_failure\n')
        self.a.rebuild_final();self.assertFalse(self.a.final['passed'])
        self.a.summary.update(passed=False,status='failed',failures=['final ordered trace failed']);self.a.save()
        report=self.a.evaluate();self.assertTrue(report['capture_binding_verified'],report['failures'])
        self.assertTrue(report['mirror_relation_passed']);self.assertFalse(report['trace_binding']['final_trace_passed'])
        self.assertTrue(report['trace_binding']['final_trace_failures']);self.assertFalse(report['input_runtime_passed'])
        self.a.summary.update(passed=True,status='bounded_hidden_modal_canvas_capture',failures=[]);self.a.save()
        self.rejected('failed final trace')

    def test_final_prefix_tail_and_stored_trace_must_reconstruct_exactly(self):
        self.a.log.write_bytes(self.a.log.read_bytes()+b'Debugger terminated after host snapshot.\n')
        self.a.rebuild_final();self.a.save();report=self.a.evaluate()
        self.assertTrue(report['capture_binding_verified'],report['failures'])
        self.assertLess(report['trace_binding']['paused_prefix_bytes'],report['trace_binding']['final_log_bytes'])
        changes=(lambda:self.a.log.write_bytes(self.a.log.read_bytes()+b'MCAP_REJECT reason=unreported\n'),
            lambda:self.a.prefix.write_bytes(self.a.prefix.read_bytes()+b'changed\n'),
            lambda:self.a.summary['capture_prefix'].update(bytes=True),
            lambda:self.a.summary['final_log'].update(capture_prefix_preserved=False),
            lambda:self.a.summary['final_log'].update(bytes=1),
            lambda:self.a.trace['source'].update(log_raw_sha256='0'*64),
            lambda:self.a.final['source'].update(log_raw_sha256='0'*64),
            lambda:self.a.trace['surface'].update(base=0x22000000))
        for change in changes:
            self.reset();change();self.a.save();self.rejected()
        self.reset();self.a.log.write_bytes(self.a.log.read_bytes()[1:]);self.a.rebuild_final();self.a.save()
        self.rejected('exact paused capture prefix')

    def test_every_paired_header_state_address_and_identity_is_measured(self):
        for phase in ('before','after'):
            for name in ('state','e0','physical_header','native_header'):
                for key,value in (('address',0),('bytes',True),('sha256','0'*64),('path',str(self.a.original))):
                    with self.subTest(phase=phase,name=name,field=key):
                        self.reset();self.a.summary['snapshot']['reads'][phase][name][key]=value;self.a.save();self.rejected()
        cases=[('state',audit.trace.producer.canvas.STATE[name],struct.pack('<I',value)) for name,value in
            (('phase',0),('physical',0x23000000),('native',0x20000000),('native_pixels',0x21000000),
             ('physical_pixels',0x21000004),('root_esp',1),('owner_tid',9),('frees',1),('mirrors',0),
             ('pending_header',1),('pending_pixels',1),('fault',1))]
        cases += [('e0',0,struct.pack('<I',0x20000000)),('physical_header',0,struct.pack('<H',640)),
            ('physical_header',4,struct.pack('<I',0x24000000)),('native_header',0,struct.pack('<H',800)),
            ('native_header',4,struct.pack('<I',0x21000000)),('native_header',172,struct.pack('<I',1)),
            ('native_header',184,struct.pack('<I',0x50EEC4))]
        for name,offset,value in cases:
            with self.subTest(name=name,offset=offset):
                self.reset();self.receipt_mutation('before',name,offset,value,both=True);self.rejected()
        self.reset();self.receipt_mutation('after','state',12,struct.pack('<I',0x12345678))
        self.rejected('changed across')

    def test_snapshot_geometry_counts_timestamps_and_native_copy_receipt(self):
        for key,value in (('pixel_reads',True),('physical_header_reads',1),('native_header_reads',1),('state_reads',1),
            ('e0_reads',1),('state_va',0),('physical',0x23000000),('physical_pixels',0x24000000),
            ('capture','memory_map'),('paused',False),('width',640),('pitch',640),('bytes',307200),
            ('started_at','2026-09-06T00:00:00Z'),('captured_at','2026-09-06T00:00:11Z'),('game_identity',{})):
            with self.subTest(field=key):
                self.reset();self.a.summary['snapshot'][key]=value;self.a.save();self.rejected()
        for key,value in (('surface',0x20000000),('base',0x21000000),('pitch',800),('pixel_reads',2),('bytes',480000),('header',{})):
            self.reset();self.a.summary['snapshot']['native'][key]=value;self.a.save();self.rejected()
        self.reset();(self.a.run/'native-surface.header.bin').write_bytes(bytes(188));self.rejected('header copy differs')

    def test_missing_or_mutated_sources_captures_receipts_and_claim_hashes_fail(self):
        paths=(self.a.original,self.a.input,self.a.candidate,self.a.proxy_input,self.a.proxy,self.a.proxy_manifest,
            self.a.packet_path,self.a.probe,self.a.plan_path,self.a.log,self.a.prefix,self.a.run/'trace.json',self.a.run/'trace-final.json',
            self.a.raw,self.a.run/'native-surface.raw',self.a.run/'native-surface.header.bin',self.a.png,self.a.meta,self.a.palette)
        for path in paths:
            with self.subTest(path=path.name):self.reset();path.unlink();self.rejected()
        self.reset();self.a.packet['manual_input_proof']=True;self.a.save();self.rejected('reconstruction')
        self.reset();self.a.probe.write_bytes(self.a.probe.read_bytes()+b'.echo unauthorized\n')
        self.a.plan['probe_sha256']=audit.sha(self.a.probe.read_bytes());self.a.save();self.rejected('reconstruction')
        for key,value in (('stage',audit.trace.producer.builder.BASE_STAGE),('width',1024),('resolution','1024x768'),
            ('route','battle_initial'),('availability','natural'),('castle_index',True),('minimap_viewport',None),
            ('canvas_state_va',1),('canvas_state_offsets',{}),('stop_va',0),('execute',False),('deadline_seconds',121),
            ('host_sha256','0'*64),('producer_sha256','0'*64),('trace_sha256','0'*64),
            ('child_environment',dict(CLASH_PROXY_PRESENT='1',parent_environment_modified=False))):
            self.reset();self.a.plan[key]=value;self.a.save();self.rejected()

    def test_png_palette_origin_and_retained_process_binding(self):
        for key,value in (('log_path',str(self.a.log)),('raw_path',str(self.a.original)),('palette_path',str(self.a.original)),('pitch',801)):
            self.reset();self.a.summary['png'][key]=value;write_json(self.a.meta,self.a.summary['png']);self.a.save();self.rejected()
        self.reset();self.a.png.write_bytes(b'fabricated PNG');self.a.summary['png']['png_sha256']=audit.sha(self.a.png.read_bytes())
        write_json(self.a.meta,self.a.summary['png']);self.a.save();self.rejected('does not encode')
        for change in (lambda s:s['candidates'][0].update(parent_process_id=999),
            lambda s:s['candidates'][0].update(creation_filetime=1),lambda s:s['candidates'][0].update(handle_retained=False),
            lambda s:s['cleanup']['cdb'].update(absent=False),lambda s:s.update(command_line=s['command_line']+' extra'),
            lambda s:s.update(hidden_desktop='Default'),lambda s:s.update(manual_input_proof=True),
            lambda s:s['postrun_identity'].update(candidate_sha256='0'*64)):
            self.reset();change(self.a.summary);self.a.save();self.rejected()

    def test_windows_always_quoted_command_matches_literal_host_recipe(self):
        plan=dict(cdb=r'C:\Program Files (x86)\cdb.exe',out_dir=r'C:\ClashCaptures\test',candidate_path=r'C:\ClashTests\game.exe')
        self.assertEqual(audit.launch_command(plan),
            '"C:\\Program Files (x86)\\cdb.exe" "-hd" "-logo" "C:\\ClashCaptures\\test\\cdb.log" "-c" '
            '"$$>a<\\"C:\\ClashCaptures\\test\\framed-modal-canvas.cdb\\"" "C:\\ClashTests\\game.exe"')

    def test_cli_does_not_overwrite_an_existing_report(self):
        output=self.a.root/'audit.json';output.write_bytes(b'preserve')
        argv=['audit','--summary',str(self.a.summary_path),'--frame-resource',str(self.a.frame_resource),
              '--command-resource',str(self.a.command_resource),'--output',str(output)]
        with patch('sys.argv',argv),patch('sys.stderr',new_callable=io.StringIO),self.assertRaises(SystemExit):audit.main()
        self.assertEqual(output.read_bytes(),b'preserve')


if __name__=='__main__':unittest.main()
