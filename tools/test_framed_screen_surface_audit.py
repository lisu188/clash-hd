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

import framed_screen_surface_audit as audit
import test_framed_screen_trace as trace_fixture
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
        original = bytearray(b"synthetic non-PE fixture\0" + bytes(0x80000))
        spans = dict(producer.COMMON)
        for row in producer.ROUTES.values():
            spans[row.entry_va] = row.entry_bytes
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
        self.template = audit.trace.render_probe(audit.trace.BASE_PROBE.read_text(encoding="utf-8-sig"), "800x600", producer.STAGE)["template"]
        self.template = re.sub(r"(?m)^g$", lambda _: self.extra.strip() + "\ng", self.template)
        self.metadata = dict(source_sha256={"synthetic_recipe": audit.sha(self.image)})
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
        self.log = self.run / "cdb.log"; self.probe = self.run / "framed-screen.cdb"
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
        self.trace["source"]["log_raw_sha256"] = audit.sha(self.log.read_bytes())
        if not self.trace["passed"]:
            raise AssertionError(self.trace["failures"])
        self.plan = dict(schema="clash95_framed_screen_capture_plan_v1", environment="hidden_cdb_host", execute=True,
            stage=producer.STAGE, resolution="800x600", width=800, height=600, route=route, castle_index=0,
            availability=availability, minimap_viewport=False, deadline_seconds=120,
            original=str(self.original), original_sha256=audit.sha(self.original_bytes), input_candidate=str(self.input),
            candidate_sha256=self.digest, candidate_dir=str(self.candidate_dir), candidate_path=str(self.candidate),
            work_dir=str(root), out_dir=str(self.run), proxy_manifest=str(self.proxy_manifest),
            proxy_manifest_sha256=audit.sha(self.proxy_manifest.read_bytes()), proxy_input=str(self.proxy_input),
            proxy_path=str(self.proxy), proxy_sha256=audit.sha(self.proxy.read_bytes()), palette_path=str(self.palette),
            probe_sha256=audit.sha(self.probe.read_bytes()),
            child_environment=dict(CLASH_PROXY_PRESENT="0", parent_environment_modified=False),
            manual_input_proof=False, visible_composition_proof=False, promotion_ready=False)
        for key, path in self.source_paths.items():
            self.plan[key] = str(path); self.plan[audit.SOURCE_HASH_KEYS[key]] = audit.sha(path.read_bytes())
        cdb = identity(123, self.plan["cdb"], "2026-09-06T00:00:01Z")
        game = identity(456, self.candidate, "2026-09-06T00:00:02Z", parent_process_id=123, candidate_sha256=self.digest)
        self.summary = dict(schema="clash95_framed_screen_capture_v1", passed=True, status="bounded_hidden_modal_capture",
            executed=True, launch_attempted=True, plan=self.plan, started_at="2026-09-06T00:00:00Z", finished_at="2026-09-06T00:00:10Z",
            failures=[], trace=self.trace, cdb=cdb, candidates=[game],
            hidden_desktop="ClashFramedScreen_" + "a" * 32,
            command_line=f'"{self.plan["cdb"]}" -hd -logo "{self.log}" -c "$$><{self.probe}" "{self.candidate}"',
            cleanup=dict(cdb=dict(identity=cdb, absent=True, termination_requested=True, handle_closed=True),
                candidates=[dict(identity=game, absent=True, termination_requested=False, handle_closed=True)], desktop_closed=True),
            postrun_identity=dict(original_sha256=self.plan["original_sha256"], input_candidate_sha256=self.digest,
                                  candidate_sha256=self.digest, proxy_sha256=self.plan["proxy_sha256"]),
            manual_input_proof=False, visible_composition_proof=False, promotion_ready=False)
        self.raw.write_bytes(frame_fixture.surface(self.frame, audit.FramedViewport(800, 600)))
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

    def regenerate(self):
        self.summary["png"] = convert(self.raw, self.png, 800, 600, 800, self.meta, self.log, self.palette)
        self.summary["snapshot"] = dict(path=str(self.raw), sha256=audit.sha(self.raw.read_bytes()), bytes=480000,
                                       width=800, height=600, pitch=800, pixel_reads=1, paused=True)
        self.summary["palette"] = dict(path=str(self.palette), sha256=audit.sha(self.palette.read_bytes()), bytes=1024)

    def save(self):
        write_json(self.packet_path, self.packet); write_json(self.plan_path, self.plan)
        write_json(self.run / "trace.json", self.trace); write_json(self.summary_path, self.summary)

    def evaluate(self):
        return audit.build_report(self.summary_path, frame_resource=self.frame_resource,
                                  command_resource=self.command_resource, original_path=self.original)


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.a = Artifacts(Path(self.temp.name)); self.addCleanup(self.a.mocks().close)
        self.files = {p: p.read_bytes() for p in self.a.root.rglob("*") if p.is_file()}
        self.objects = copy.deepcopy((self.a.summary, self.a.plan, self.a.packet, self.a.trace))

    def reset(self):
        for path, data in self.files.items(): path.write_bytes(data)
        self.a.summary, self.a.plan, self.a.packet, self.a.trace = copy.deepcopy(self.objects)
        self.a.summary["plan"] = self.a.plan; self.a.summary["trace"] = self.a.trace

    def rejected(self, contains=None):
        result = self.a.evaluate()
        self.assertFalse(result["frame_pixels_passed"], result)
        self.assertTrue(result["failures"], result)
        if contains: self.assertIn(contains, "; ".join(result["failures"]))
        return result

    def test_complete_bindings_four_bands_footer_and_absent_bar_are_distinct(self):
        result = self.a.evaluate()
        self.assertTrue(result["frame_pixels_passed"], result["failures"])
        self.assertTrue(result["source_authenticated"]); self.assertTrue(result["screenshot_binding_verified"])
        self.assertTrue(result["structural_border_exact"]); self.assertTrue(result["footer_exact"])
        self.assertEqual([row["name"] for row in result["frame"]["bands"]], ["top", "bottom", "left", "right"])
        self.assertEqual(result["action_bar"]["matching_cell_count"], 0)
        self.assertEqual(result["action_bar"]["applicability"], "ordinary_map_bar_not_required_for_this_modal")
        self.assertFalse(result["action_bar"]["evaluated_as_gate"])
        self.assertEqual([c["anchor"] for c in result["action_bar"]["cells"]],
                         [[576, 520], [640, 520], [704, 520], [576, 552], [640, 552], [704, 552]])
        for key in ("runtime_verdict_changed", "modal_controls_accepted", "manual_input_proof", "visible_composition_proof", "promotion_ready"):
            self.assertFalse(result[key])
        self.assertEqual(self.files, {p: p.read_bytes() for p in self.files})

    def test_raw_frame_band_and_footer_mismatches_are_separate(self):
        for x, y, expected in ((0, 0, "top"), (0, 590, "bottom"), (0, 40, "left"), (799, 40, "right"), (235, 585, "footer")):
            with self.subTest(band=expected):
                self.reset(); raw = bytearray(self.a.raw.read_bytes()); raw[y * 800 + x] ^= 1
                self.a.raw.write_bytes(raw); self.a.regenerate(); self.a.save()
                result = self.a.evaluate(); self.assertFalse(result["frame_pixels_passed"])
                self.assertEqual(result["failures"], []); self.assertTrue(result["screenshot_binding_verified"])
                self.assertEqual(result["structural_border_exact"], expected == "footer")
                self.assertEqual(result["footer_exact"], expected != "footer")
                if expected != "footer":
                    self.assertEqual(next(b["mismatches"] for b in result["frame"]["bands"] if b["name"] == expected), 1)

    def test_present_bar_count_never_accepts_modal_controls(self):
        raw = bytearray(self.a.raw.read_bytes())
        for cell in range(6):
            left, top = 576 + cell % 3 * 64, 520 + cell // 3 * 32
            sprite = self.a.sprites[cell * 2]
            for y in range(32): raw[(top + y) * 800 + left:(top + y) * 800 + left + 64] = bytes(sprite.pixels[y * 64:(y + 1) * 64])
        self.a.raw.write_bytes(raw); self.a.regenerate(); self.a.save()
        result = self.a.evaluate(); self.assertTrue(result["frame_pixels_passed"], result["failures"])
        self.assertEqual(result["action_bar"]["matching_cell_count"], 6)
        self.assertFalse(result["modal_controls_accepted"])

    def test_missing_or_changed_bound_files_fail(self):
        paths = (self.a.original, self.a.input, self.a.candidate, self.a.proxy_input, self.a.proxy, self.a.proxy_manifest,
                 self.a.packet_path, self.a.probe, self.a.plan_path, self.a.log, self.a.run / "trace.json",
                 self.a.raw, self.a.png, self.a.meta, self.a.palette, self.a.frame_resource, self.a.command_resource)
        for path in paths:
            for mode in ("missing", "changed"):
                with self.subTest(file=path.name, mode=mode):
                    self.reset()
                    if mode == "missing": path.unlink()
                    elif path == self.a.log:
                        path.write_bytes(path.read_bytes().replace(b"MODAL_SURFDUMP_READY", b"MODAL_INVALID_READY", 1))
                    else: path.write_bytes(path.read_bytes() + b" changed")
                    self.rejected()

    def test_packet_probe_log_mutations_fail_even_after_claim_hash_refresh(self):
        self.a.packet["manual_input_proof"] = True; self.a.save(); self.rejected("reconstruction")
        self.reset(); self.a.probe.write_bytes(self.a.probe.read_bytes() + b".echo unauthorized\n")
        self.a.plan["probe_sha256"] = audit.sha(self.a.probe.read_bytes()); self.a.save(); self.rejected("reconstruction")
        self.reset(); self.a.log.write_bytes(self.a.log.read_bytes() + b"MODAL_REJECT reason=late_failure\n")
        self.rejected("ordered modal")
        self.reset(); line = next(row for row in self.a.log.read_text().splitlines() if row.startswith("MODAL_SURFDUMP_READY"))
        self.a.log.write_bytes(self.a.log.read_bytes() + line.encode() + b"\n"); self.rejected("ordered modal")
        self.reset(); self.a.trace["surface"]["base"] += 4; self.a.save(); self.rejected("reconstruction")
        self.reset(); self.a.trace["source"]["log_raw_sha256"] = "0" * 64; self.a.save(); self.rejected("exact prefix")

    def test_ordinary_cleanup_tail_and_honest_runtime_failure_are_preserved(self):
        self.a.log.write_bytes(self.a.log.read_bytes() + b"Debugger terminated after host snapshot.\n")
        result = self.a.evaluate(); self.assertTrue(result["frame_pixels_passed"], result["failures"])
        self.assertLess(result["trace_binding"]["paused_prefix_bytes"], result["trace_binding"]["final_log_bytes"])
        self.a.summary["passed"] = False; self.a.summary["status"] = "failed"
        self.a.summary["failures"] = ["Exact owned-process absence/handle cleanup was not fully verified."]
        self.a.summary["cleanup"]["desktop_closed"] = False; self.a.save()
        result = self.a.evaluate(); self.assertTrue(result["frame_pixels_passed"], result["failures"])
        self.assertFalse(result["input_runtime_passed"]); self.assertFalse(result["runtime_verdict_changed"])
        self.assertFalse(result["process_observations"]["recorded_owned_process_cleanup_verified"])
        self.a.summary["passed"] = True; self.a.save(); self.rejected("cleanup")

    def test_route_geometry_environment_source_and_claim_bindings_fail(self):
        for key, value in (("route", "battle_initial"), ("stage", "stable"), ("width", 1024), ("resolution", "1024x768"),
                           ("castle_index", True), ("availability", "natural"), ("minimap_viewport", None),
                           ("environment", "host_visible"), ("deadline_seconds", 121), ("execute", False),
                           ("host_sha256", "0" * 64), ("trace_sha256", "0" * 64), ("converter_sha256", "0" * 64),
                           ("proxy_source_sha256", "0" * 64), ("python_sha256", "0" * 64), ("cdb_sha256", "0" * 64),
                           ("child_environment", dict(CLASH_PROXY_PRESENT="1", parent_environment_modified=False))):
            with self.subTest(field=key):
                self.reset(); self.a.plan[key] = value; self.a.save(); self.rejected()
        for name in ("manual_input_proof", "visible_composition_proof", "promotion_ready"):
            self.reset(); self.a.summary[name] = True; self.a.save(); self.rejected("unsupported proof")

    def test_retained_identity_and_cleanup_must_bind_actual_candidate(self):
        variants = (
            lambda s: s["candidates"][0].update(parent_process_id=999),
            lambda s: s["candidates"][0].update(candidate_sha256="0" * 64),
            lambda s: s["candidates"][0].update(creation_filetime=1),
            lambda s: s["candidates"][0].update(path=str(self.a.input)),
            lambda s: s["candidates"][0].update(handle_retained=False),
            lambda s: s["cleanup"]["candidates"][0].update(identity={}),
            lambda s: s["cleanup"]["cdb"].update(absent=False),
            lambda s: s.update(command_line=s["command_line"] + " extra"),
            lambda s: s.update(hidden_desktop="Default"),
            lambda s: s.update(finished_at="2025-01-01T00:00:00Z"),
            lambda s: s["postrun_identity"].update(candidate_sha256="0" * 64),
        )
        for index, change in enumerate(variants):
            with self.subTest(change=index):
                self.reset(); change(self.a.summary); self.a.save(); self.rejected()

    def test_png_metadata_origin_palette_and_snapshot_are_not_pasted_proof(self):
        for key, value in (("log_path", str(self.a.root / "elsewhere.log")), ("raw_path", str(self.a.original)),
                           ("palette_path", str(self.a.original)), ("pitch", 801), ("width", 801)):
            with self.subTest(metadata=key):
                self.reset(); self.a.summary["png"][key] = value
                write_json(self.a.meta, self.a.summary["png"]); self.a.save(); self.rejected()
        for key, value in (("paused", False), ("pixel_reads", 2), ("pixel_reads", True), ("pitch", 801)):
            self.reset(); self.a.summary["snapshot"][key] = value; self.a.save(); self.rejected("snapshot")
        # Consistent hashes cannot turn arbitrary PNG bytes into this raw/palette.
        self.reset(); self.a.png.write_bytes(b"not an encoded screenshot")
        self.a.summary["png"]["png_sha256"] = audit.sha(self.a.png.read_bytes())
        write_json(self.a.meta, self.a.summary["png"]); self.a.save(); self.rejected("does not encode")

    def test_explicit_missing_or_different_plan_and_original_fail(self):
        for kwargs in (dict(plan_path=self.a.root / "missing.json"), dict(original_path=self.a.input)):
            result = audit.build_report(self.a.summary_path, frame_resource=self.a.frame_resource,
                                        command_resource=self.a.command_resource, **kwargs)
            self.assertFalse(result["frame_pixels_passed"]); self.assertTrue(result["failures"])

    def test_native_proxy_manifest_uppercase_hex_remains_supported(self):
        manifest = audit.read_json(self.a.proxy_manifest)
        for key in ("source_sha256", "output_sha256"): manifest[key] = manifest[key].upper()
        write_json(self.a.proxy_manifest, manifest)
        self.a.plan["proxy_manifest_sha256"] = audit.sha(self.a.proxy_manifest.read_bytes()); self.a.save()
        result = self.a.evaluate(); self.assertTrue(result["frame_pixels_passed"], result["failures"])
        manifest["source_sha256"] = "G" * 64; write_json(self.a.proxy_manifest, manifest)
        self.a.plan["proxy_manifest_sha256"] = audit.sha(self.a.proxy_manifest.read_bytes()); self.a.save()
        self.rejected("proxy manifest")

    def test_exclusive_cli_output_does_not_overwrite_existing_evidence(self):
        output = self.a.root / "audit.json"; output.write_bytes(b"preserve")
        args = ["audit", "--summary", str(self.a.summary_path), "--frame-resource", str(self.a.frame_resource),
                "--command-resource", str(self.a.command_resource), "--output", str(output)]
        with patch("sys.argv", args), patch("sys.stderr", new_callable=io.StringIO), self.assertRaises(SystemExit): audit.main()
        self.assertEqual(output.read_bytes(), b"preserve")


class RouteTests(unittest.TestCase):
    def test_all_supported_modal_routes_and_explicit_availability(self):
        for route in audit.trace.producer.ROUTES:
            for availability in ("existing_flags", "construct_all"):
                with self.subTest(route=route, availability=availability), tempfile.TemporaryDirectory() as folder:
                    artifacts = Artifacts(Path(folder), route, availability)
                    with artifacts.mocks():
                        result = artifacts.evaluate()
                    self.assertTrue(result["frame_pixels_passed"], result["failures"])
                    self.assertEqual(result["route"], route)
                    self.assertEqual(result["availability"], availability)
                    self.assertFalse(result["natural_availability_proven"])
                    self.assertFalse(result["modal_controls_accepted"])


if __name__ == "__main__":
    unittest.main()
