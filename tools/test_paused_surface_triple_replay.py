"""Synthetic RAM journals only; no current host emits the tested protocol.

Tiny temporary files exercise literal-path identity/rehash rejection separately.
No original/candidate assets, native APIs, game, debugger, captures or approvals
are used, and no passing diagnostic is treated as production evidence.
"""
from __future__ import annotations

import ast
import copy
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest.mock import patch

import paused_surface_triple_replay as replay

AUTHORITY_FLAGS = ("passed", "candidate_authenticated", "canonical_probe_verified", "source_authenticated",
    "native_provenance_verified", "release_evidence_verified", "geometry_evidence_verified", "runtime_proof",
    "manual_input_proof", "ordinary_input_proof", "visible_composition_proof", "live_cleanup_verified",
    "endurance_proof", "promotion_ready")


class RAMArtifacts:
    def __init__(self, originals):
        self.originals = originals
        self.loaded = {}
        self.total = 0
        self.at_final = None

    def reference(self, row, role):
        replay.keys(row, ("path", "bytes", "sha256"), role)
        replay.require(type(row["path"]) is str and row["path"] not in self.loaded, "synthetic original role alias")
        replay.integer(row["bytes"], 0, replay.MAX_FILE_BYTES, "synthetic size")
        replay.digest(row["sha256"], "synthetic hash")
        data = self.originals[row["path"]]
        replay.require(len(data) == row["bytes"] and replay.sha(data) == row["sha256"], "synthetic original hash/bytes differ")
        replay.require(self.total + len(data) <= replay.MAX_TOTAL_BYTES, "synthetic aggregate budget")
        self.loaded[row["path"]] = data, role
        self.total += len(data)
        return data

    def unchanged(self):
        if self.at_final:
            hook, self.at_final = self.at_final, None
            hook()
        for path, (data, _) in self.loaded.items():
            replay.require(self.originals[path] == data, "synthetic original changed at final rehash")

    def receipts(self):
        return [dict(path=path, sha256=replay.sha(data), bytes=len(data), role=role)
                for path, (data, role) in self.loaded.items()]


class Fixture:
    """All outputs are invented labelled synthetic packets, never provenance."""

    def __init__(self, resolution="800x600"):
        self.originals = {}
        self.serial = 0
        self.clock = 1000
        self.width, self.height = map(int, resolution.split("x"))
        commands = b"synthetic source fixture only\n.echo SHSEL_HOST_READY\n"
        binding = dict(profile="Complete HD", stage=replay.STAGE, recipe="complete_hd_v1",
            representation=replay.REPRESENTATION, phase=replay.PHASE, resolution=resolution, candidate_sha256="a" * 64,
            original_sha256="b" * 64, probe_sha256=replay.sha(commands), producer_sha256="c" * 64)
        self.identity = dict(process_id=1234, creation_filetime=134000000000000000, handle=456)
        self.state = dict(tid=17, eip=0x406FA1, esp=0x120000, selected_stack=3, panel_stack=3, lower=1,
            owner=0x40AD40, surface=0x220000, base=0x300000, width=self.width, height=self.height, vtable=0x50EE24)
        prefix = b"synthetic prior trace\n" + replay.ready_line(self.state) + b"\nSHSEL_HOST_READY\n"
        self.document = dict(schema=replay.MANIFEST_SCHEMA, evidence_class="synthetic_fixture", binding=binding,
            artifacts=dict(commands=self.ref(commands), debugger_prefix=self.ref(prefix), debugger_final=self.ref(prefix)))
        self.journal = dict(schema=replay.JOURNAL_SCHEMA, evidence_class="synthetic_fixture", host_architecture="x64", binding=copy.deepcopy(binding),
            identity=self.identity, frequency=dict(return_=None), pause=dict(epoch="synthetic_pause", state=self.state,
                prefix_sha256=replay.sha(prefix), begin=self.qpc(), end=None), cohorts=[],
            completion=dict(status="complete", failures=[], missing_originals=[]))
        self.journal["frequency"] = {"return": self.uint(1, 4), "error": self.uint(71, 4), "frequency": self.uint(10000000, 8)}
        header = bytearray(188)
        struct.pack_into("<HHI", header, 0, self.width, self.height, self.state["base"])
        struct.pack_into("<I", header, 184, self.state["vtable"])
        pixels = bytes(range(256)) * ((self.width * self.height + 255) // 256)
        pixels = pixels[:self.width * self.height]
        for index in range(1, 4):
            cohort = dict(index=index, pause_epoch="synthetic_pause", reads=[])
            for role in replay.READ_ROLES:
                if role.startswith("state_"):
                    field = role.split("_", 2)[2]
                    address = replay.STATE[field][0]
                    buffer = struct.pack("<I", replay.STATE[field][1])
                elif role.startswith("e0_"):
                    address, buffer = 0x5202E0, struct.pack("<I", self.state["surface"])
                elif role.startswith("header_"):
                    address, buffer = self.state["surface"], bytes(header)
                else:
                    address, buffer = self.state["base"], pixels
                ordinal = (index - 1) * len(replay.READ_ROLES) + len(cohort["reads"]) + 1
                read = dict(ordinal=ordinal, role=role, api="ReadProcessMemory", handle=self.identity["handle"],
                    address=address, requested=len(buffer), identity_before=self.process(), qpc_begin=self.qpc(),
                    native_return=self.uint(1, 4), native_error=self.uint(31, 4), returned_count=self.uint(len(buffer), 8),
                    buffer=self.ref(buffer), qpc_end=self.qpc(), identity_after=self.process())
                cohort["reads"].append(read)
            self.journal["cohorts"].append(cohort)
        self.journal["pause"]["end"] = self.qpc()
        self.publish()

    def ref(self, data):
        self.serial += 1
        path = str(Path(tempfile.gettempdir()) / "synthetic-paused-surface-never-written" / (str(self.serial) + ".raw"))
        self.originals[path] = data
        return dict(path=path, bytes=len(data), sha256=replay.sha(data))

    def uint(self, value, count):
        return self.ref(value.to_bytes(count, "little"))

    def qpc(self):
        self.clock += 1
        return {"return": self.uint(1, 4), "error": self.uint(71, 4), "counter": self.uint(self.clock, 8)}

    def process(self):
        stamp = self.qpc()
        return dict(handle=self.identity["handle"], pid_return=self.uint(self.identity["process_id"], 4),
            pid_error=self.uint(71, 4), times_return=self.uint(1, 4), times_error=self.uint(71, 4),
            filetimes=self.ref(struct.pack("<QQQQ", self.identity["creation_filetime"], 0, self.clock, self.clock)),
            wait_return=self.uint(258, 4), wait_error=self.uint(71, 4), qpc=stamp)

    def mutate(self, reference, data):
        self.originals[reference["path"]] = data
        reference.update(bytes=len(data), sha256=replay.sha(data))

    def set_uint(self, reference, value, count=None):
        self.mutate(reference, value.to_bytes(count or reference["bytes"], "little"))

    def publish(self):
        # Journal is itself a complete pinned original; reissue after a fixture mutation.
        self.document["artifacts"]["journal"] = self.ref(json.dumps(self.journal, separators=(",", ":")).encode())

    def read(self, index=0, role="pixels"):
        return next(row for row in self.journal["cohorts"][index]["reads"] if row["role"] == role)

    def run(self, hook=None):
        self.publish()
        store = RAMArtifacts(self.originals)
        store.at_final = hook
        return replay.replay(self.document, store)


class ReplayTests(unittest.TestCase):
    def check(self, result, consistent=False, reason=None):
        self.assertEqual(result["raw_artifact_contract_valid"], consistent, result["failures"])
        self.assertEqual(result["input_cohort_consistent"], consistent)
        for name in AUTHORITY_FLAGS:
            self.assertIs(result[name], False, name)
        self.assertTrue(result["remaining_debts"])
        if reason:
            self.assertIn(reason, "\n".join(result["failures"]))

    def rejected(self, mutate, reason):
        fixture = Fixture()
        mutate(fixture)
        result = fixture.run()
        self.check(result, reason=reason)
        return fixture, result

    def test_complete_synthetic_triple_is_consistent_and_grants_no_authority(self):
        fixture = Fixture()
        before = copy.deepcopy(fixture.document), copy.deepcopy(fixture.journal)
        result = fixture.run()
        self.check(result, True)
        self.assertEqual(len(result["observed_reads"]), 39)
        self.assertEqual(len(result["frames"]), 3)
        self.assertEqual(len({row["sha256"] for row in result["frames"]}), 1)
        self.assertEqual(before[1], fixture.journal)
        self.assertEqual(before[0]["binding"], fixture.document["binding"])
        self.assertEqual(result["evidence_class"], "synthetic_fixture")
        self.assertGreater(len(result["artifacts"]), 1000)

    def test_synthetic_dimension_bytes_include_4k_ultrawide_and_custom_without_qualification(self):
        for resolution in replay.RESOLUTIONS:
            with self.subTest(resolution=resolution):
                fixture = Fixture(resolution)
                result = fixture.run()
                self.check(result, True)
                self.assertEqual([row["bytes"] for row in result["frames"]], [fixture.width * fixture.height] * 3)
                self.assertEqual(result["evidence_class"], "synthetic_fixture")

    def test_scope_is_only_stack3_and_panel_role_never_previous_selection(self):
        self.assertEqual(replay.STATE["selected_stack"], (0x511B58, 3))
        self.assertEqual(replay.STATE["panel_stack"], (0x514194, 3))
        self.assertNotIn("previous_stack", replay.STATE)
        self.assertIn("previous_stack at0x511B5C", "\n".join(replay.DEBTS))
        native_tree = ast.parse(Path(__file__).with_name("ordinary_map_input_plan.py").read_bytes())
        native_call = next(node.value for node in native_tree.body if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "NATIVE" for target in node.targets))
        native = {keyword.arg: ast.literal_eval(keyword.value) for keyword in native_call.keywords}
        self.assertEqual((native["selected_stack"], native["panel_stack"], native["previous_stack"]),
                         (0x511B58, 0x514194, 0x511B5C))
        fixture = Fixture()
        result = fixture.run()
        self.check(result, True)
        self.assertEqual(result["diagnostic_representation"], "complete_hd_selected_stack3_physical_e0_v1")
        self.assertEqual(result["diagnostic_phase"], "controlled_selected_stack3_redraw_stopped")
        for field in ("selected_stack", "panel_stack"):
            with self.subTest(field=field):
                def changed(f):
                    f.state[field] = 2
                    for index in range(3):
                        for phase in ("before", "after"):
                            f.set_uint(f.read(index=index, role="state_" + phase + "_" + field)["buffer"], 2)
                    log = replay.ready_line(f.state) + b"\nSHSEL_HOST_READY\n"
                    for role in ("debugger_prefix", "debugger_final"):
                        f.mutate(f.document["artifacts"][role], log)
                    f.journal["pause"]["prefix_sha256"] = replay.sha(log)
                self.rejected(changed, "paused selection state differs")
        self.rejected(lambda f: f.document["binding"].update(phase="generic_map"), "representation/phase")

    def test_recorded_class_and_pass_flags_cannot_authenticate_execution(self):
        fixture = Fixture()
        fixture.document["evidence_class"] = fixture.journal["evidence_class"] = "recorded_native_diagnostic"
        self.check(fixture.run(), True)
        self.rejected(lambda f: f.document.update(passed=True), "exact object fields")
        self.rejected(lambda f: f.journal.update(native_provenance_verified=True), "exact object fields")

    def test_all_binding_and_representation_substitutions_reject(self):
        for name, value in (("profile", "Framed"), ("profile", "Modal Widgets"), ("representation", "MCAP"),
                            ("stage", "different"), ("recipe", "different"), ("resolution", "9x9")):
            with self.subTest(name=name, value=value):
                self.rejected(lambda f: f.document["binding"].update({name: value}), "supported" if name == "resolution" else "representation")
        self.rejected(lambda f: f.journal["binding"].update(candidate_sha256="d" * 64), "binding differs")
        self.rejected(lambda f: f.document["binding"].update(candidate_sha256="D" * 64), "lowercase SHA")
        self.rejected(lambda f: f.journal.update(host_architecture="x86"), "SIZE_T")

    def test_old_missing_and_duplicate_cohorts_cannot_supply_new_observations(self):
        self.rejected(lambda f: f.document.update(schema="clash95_complete_hd_army_selection_capture_v1"), "older captures")
        self.rejected(lambda f: f.journal["cohorts"].pop(), "exactly3")
        self.rejected(lambda f: f.journal["cohorts"].append(copy.deepcopy(f.journal["cohorts"][0])), "original path reused")
        self.rejected(lambda f: f.read().pop("identity_before"), "exact object fields")
        self.rejected(lambda f: f.read().pop("qpc_begin"), "exact object fields")
        self.rejected(lambda f: f.journal["pause"].pop("begin"), "exact object fields")

    def test_fixed_actual_read_order_and_native_api_roles(self):
        def reorder(f):
            reads = f.journal["cohorts"][0]["reads"]
            reads[4], reads[5] = reads[5], reads[4]
        self.rejected(reorder, "order/API/ordinal")
        self.rejected(lambda f: f.read().update(api="SendInput"), "order/API/ordinal")
        self.rejected(lambda f: f.read().update(ordinal=True), "order/API/ordinal")
        self.rejected(lambda f: f.journal["cohorts"][0].update(index=True), "index/pause")
        self.rejected(lambda f: f.journal["cohorts"][1].update(pause_epoch="lost"), "index/pause")

    def test_wrong_read_addresses_and_bool_counts_reject(self):
        for role in replay.READ_ROLES:
            with self.subTest(role=role):
                self.rejected(lambda f: f.read(role=role).update(address=0xDEAD0000), "requested range")
        self.rejected(lambda f: f.read().update(requested=True), "requested range")
        self.rejected(lambda f: f.read().update(handle=True), "retained handle differs")

    def test_failed_native_read_and_short_outputs_keep_complete_originals(self):
        for role in ("pixels", "e0_before", "header_after", "state_after_owner"):
            with self.subTest(role=role):
                _, result = self.rejected(lambda f: f.set_uint(f.read(role=role)["native_return"], 0), "ReadProcessMemory failed")
                self.assertGreater(len(result["artifacts"]), 1000)
        self.rejected(lambda f: f.set_uint(f.read()["returned_count"], 479999), "short/extra count")
        self.rejected(lambda f: f.set_uint(f.read()["returned_count"], 480001), "short/extra count")
        self.rejected(lambda f: f.mutate(f.read(role="header_before")["buffer"], b"x" * 187), "full original output")
        self.rejected(lambda f: f.mutate(f.read()["buffer"], b"x" * 479999), "full original output")
        self.rejected(lambda f: f.mutate(f.read()["native_return"], b"\x01"), "full original output")

    def test_process_identity_lifetime_and_native_outputs_are_not_summary_flags(self):
        for phase in ("identity_before", "identity_after"):
            with self.subTest(phase=phase):
                self.rejected(lambda f: f.read()[phase].update(handle=457), "retained handle differs")
                self.rejected(lambda f: f.set_uint(f.read()[phase]["pid_return"], 1235), "native PID differs")
                self.rejected(lambda f: f.set_uint(f.read()[phase]["times_return"], 0), "GetProcessTimes failed")
                self.rejected(lambda f: f.set_uint(f.read()[phase]["wait_return"], 0), "not alive")
                self.rejected(lambda f: f.mutate(f.read()[phase]["filetimes"], struct.pack("<QQQQ", f.identity["creation_filetime"] + 1, 0, 1000, 1000)), "creation lifetime")
        self.rejected(lambda f: f.journal["identity"].update(process_id=True), "bounded integer")
        self.rejected(lambda f: f.read()["identity_before"].pop("pid_error"), "exact object fields")

    def test_nonzero_native_bool_dwords_preserve_original_bits_and_no_authority(self):
        for bits in (2, 0xFFFFFFFF):
            with self.subTest(bits=bits):
                fixture = Fixture()
                statuses = [fixture.journal["frequency"]["return"], fixture.journal["pause"]["begin"]["return"],
                            fixture.journal["pause"]["end"]["return"]]
                for cohort in fixture.journal["cohorts"]:
                    for read in cohort["reads"]:
                        statuses.extend((read["native_return"], read["qpc_begin"]["return"], read["qpc_end"]["return"]))
                        for phase in ("identity_before", "identity_after"):
                            statuses.extend((read[phase]["times_return"], read[phase]["qpc"]["return"]))
                for reference in statuses:
                    fixture.set_uint(reference, bits)
                before = [fixture.originals[reference["path"]] for reference in statuses]
                result = fixture.run()
                self.check(result, True)
                self.assertTrue(all(data == struct.pack("<I", bits) for data in before))
                self.assertEqual(before, [fixture.originals[reference["path"]] for reference in statuses])

    def test_live_exit_filetime_is_undefined_full_buffer_retained_dead_wait_rejects(self):
        for undefined_exit in (1, 0xFFFFFFFFFFFFFFFF):
            with self.subTest(undefined_exit=undefined_exit):
                fixture = Fixture()
                originals = []
                for cohort in fixture.journal["cohorts"]:
                    for read in cohort["reads"]:
                        for phase in ("identity_before", "identity_after"):
                            reference = read[phase]["filetimes"]
                            created, _, kernel, user = struct.unpack("<QQQQ", fixture.originals[reference["path"]])
                            fixture.mutate(reference, struct.pack("<QQQQ", created, undefined_exit, kernel, user))
                            originals.append((reference["path"], fixture.originals[reference["path"]]))
                self.check(fixture.run(), True)
                self.assertEqual(originals, [(path, fixture.originals[path]) for path, _ in originals])
        for phase in ("identity_before", "identity_after"):
            with self.subTest(phase=phase):
                self.rejected(lambda f: f.set_uint(f.read()[phase]["wait_return"], 0), "not alive")

    def test_native_qpc_frequency_order_and_cpu_brackets(self):
        self.rejected(lambda f: f.set_uint(f.journal["frequency"]["return"], 0), "frequency failed")
        self.rejected(lambda f: f.set_uint(f.journal["frequency"]["frequency"], 0), "bounded integer")
        self.rejected(lambda f: f.set_uint(f.read()["qpc_begin"]["return"], 0), "native QPC failed")
        self.rejected(lambda f: f.set_uint(f.read()["qpc_begin"]["counter"], 1), "QPC order/bounds")
        self.rejected(lambda f: f.set_uint(f.journal["pause"]["end"]["counter"], 999), "pause clock reversed")
        self.rejected(lambda f: f.mutate(f.read()["identity_after"]["filetimes"], struct.pack("<QQQQ", f.identity["creation_filetime"], 0, 0, 0)), "CPU times reversed")

    def test_full_e0_header_and_native_state_continuity(self):
        self.rejected(lambda f: f.set_uint(f.read(role="e0_after")["buffer"], f.state["surface"] + 4), "changed within")
        def unknown_header_change(f):
            row = f.read(index=2, role="header_after")["buffer"]
            data = bytearray(f.originals[row["path"]]); data[100] ^= 1
            f.mutate(row, bytes(data))
        self.rejected(unknown_header_change, "changed within")
        self.rejected(lambda f: f.set_uint(f.read(role="state_after_selected_stack")["buffer"], 4), "state changed")
        def altered_whole_pair(f):
            for role in ("header_before", "header_after"):
                row = f.read(index=2, role=role)["buffer"]
                data = bytearray(f.originals[row["path"]]); data[100] ^= 1
                f.mutate(row, bytes(data))
        self.rejected(altered_whole_pair, "changed across")

    def test_all_three_full_raw_frames_are_required_and_different_origins(self):
        def corrupt(f):
            row = f.read(index=2)["buffer"]
            data = bytearray(f.originals[row["path"]]); data[-1] ^= 1
            f.mutate(row, bytes(data))
        self.rejected(corrupt, "full raw frames differ")
        self.rejected(lambda f: f.read(index=1).update(buffer=copy.deepcopy(f.read(index=0)["buffer"])), "original path reused")
        def missing(f):
            del f.originals[f.read(index=2)["buffer"]["path"]]
        _, result = self.rejected(missing, "native original retention failed")
        self.assertGreater(len(result["artifacts"]), 1000)

    def test_ordered_paused_markers_reject_resume_duplicates_and_native_state_mismatch(self):
        def replace_log(f, text):
            for key in ("debugger_prefix", "debugger_final"):
                f.mutate(f.document["artifacts"][key], text)
            f.journal["pause"]["prefix_sha256"] = replay.sha(text)
        for suffix in (b"SHSEL_DRAW_RETURN\n", b"SHSEL_HOST_READY\n", b"MCAP_SURFDUMP_READY\n", b"SHSEL_REJECT\n"):
            with self.subTest(suffix=suffix):
                self.rejected(lambda f: replace_log(f, f.originals[f.document["artifacts"]["debugger_prefix"]["path"]] + suffix), "ordered stopped")
        self.rejected(lambda f: f.mutate(f.document["artifacts"]["debugger_final"], b"resumed"), "log changed")
        self.rejected(lambda f: f.journal["pause"]["state"].update(tid=18), "ordered stopped")
        self.rejected(lambda f: f.journal["pause"]["state"].update(selected_stack=4), "selection state")
        self.rejected(lambda f: f.journal["pause"].update(prefix_sha256="d" * 64), "pause prefix")

    def test_failed_partial_archive_is_sticky_even_with_complete_frames(self):
        self.rejected(lambda f: f.journal["completion"].update(status="failed"), "failed/partial journal")
        self.rejected(lambda f: f.journal["completion"].update(failures=["native failure31"]), "failed/partial journal")
        self.rejected(lambda f: f.journal["completion"].update(missing_originals=["native output"]), "failed/partial journal")
        self.rejected(lambda f: f.journal["completion"].update(approved=True), "exact object fields")

    def test_probe_hash_and_unknown_parser_selectors_cannot_authorize(self):
        self.rejected(lambda f: f.document["binding"].update(probe_sha256="d" * 64), "binding differs")
        self.rejected(lambda f: f.document.update(parser="complete_hd_evidence"), "exact object fields")
        self.rejected(lambda f: f.journal["pause"].update(paused=True), "exact object fields")

    def test_final_original_rehash_drift_rejects_without_changing_flags(self):
        fixture = Fixture()
        row = fixture.read()["buffer"]
        result = fixture.run(lambda: fixture.originals.__setitem__(row["path"], b"x" * row["bytes"]))
        self.check(result, reason="changed at final rehash")
        self.assertEqual(len(result["frames"]), 3)

    def test_registration_remains_absent(self):
        source = Path(__file__).with_name("complete_hd_evidence.py").read_bytes()
        tree = ast.parse(source)
        registry = next(node.value for node in tree.body if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name) and node.target.id == "LANE_VERIFIERS")
        self.assertNotIn("geometry", [ast.literal_eval(key) for key in registry.keys])


class FileAndJSONTests(unittest.TestCase):
    def test_file_entrypoint_invalid_manifest_returns_only_false_authority(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-replay-") as directory:
            path = Path(directory) / "manifest.json"
            path.write_bytes(b'{"passed":false,"passed":true}')
            result = replay.replay_manifest(path)
            for name in AUTHORITY_FLAGS:
                self.assertIs(result[name], False)
            self.assertFalse(result["input_cohort_consistent"])
            self.assertIn("duplicate JSON key", "\n".join(result["failures"]))
            self.assertEqual(len(result["artifacts"]), 1)
            result = replay.replay_manifest(Path(directory) / "absent.json")
            self.assertFalse(result["passed"])
            self.assertTrue(result["failures"])

    def test_original_reads_are_bounded_and_reject_open_time_growth(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-replay-") as directory:
            path = Path(directory) / "a.bin"; path.write_bytes(b"synthetic")
            actual = Path.open
            counts = []
            class Recording:
                def __init__(self, stream):
                    self.stream = stream
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return self.stream.__exit__(*args)
                def fileno(self):
                    return self.stream.fileno()
                def read(self, size):
                    counts.append(size)
                    return self.stream.read(size)
            def opened(value, *args, **kwargs):
                return Recording(actual(value, *args, **kwargs))
            reader = replay.FileArtifacts()
            with patch.object(Path, "open", opened):
                reader.reference(self.ref(path, b"synthetic"), "raw")
                reader.unchanged()
            self.assertEqual(counts, [10, 10])
            def grown(value, *args, **kwargs):
                with actual(value, "ab") as stream:
                    stream.write(b"changed")
                return Recording(actual(value, *args, **kwargs))
            counts.clear()
            with patch.object(Path, "open", grown):
                with self.assertRaisesRegex(ValueError, "opened artifact identity"):
                    replay.FileArtifacts().reference(self.ref(path, b"synthetic"), "raw")
            self.assertEqual(counts, [])
            path.write_bytes(b"synthetic")
            reader = replay.FileArtifacts(); reader.reference(self.ref(path, b"synthetic"), "raw")
            with patch.object(Path, "open", grown):
                with self.assertRaisesRegex(ValueError, "opened artifact identity"):
                    reader.unchanged()
            self.assertEqual(counts, [])

    def test_strict_json_duplicate_numeric_and_depth_rejections(self):
        for data in (b'{"passed":false,"passed":true}', b'{"rows":[{"x":1,"x":2}]}',
                     b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e9999}',
                     b'{"x":' + b'[' * 64 + b'0' + b']' * 64 + b'}', b'[' * 10000 + b'0' + b']' * 10000):
            with self.subTest(data=data[:40]):
                with self.assertRaises(ValueError):
                    replay.parse_json(data)
        self.assertEqual(replay.parse_json(b'\xef\xbb\xbf{"x":1.25,"a":[true,false,null]}'), {"x":1.25,"a":[True,False,None]})
        replay.parse_json(b'{"x":' + b'[' * 63 + b'0' + b']' * 63 + b'}')

    @staticmethod
    def ref(path, data):
        return dict(path=str(path), bytes=len(data), sha256=replay.sha(data))

    def test_literal_files_unique_identity_and_final_rehash(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-replay-") as directory:
            path = Path(directory) / "raw.bin"; path.write_bytes(b"synthetic16bytes")
            original = path.read_bytes(); reader = replay.FileArtifacts()
            self.assertEqual(reader.reference(self.ref(path, original), "first"), original)
            with self.assertRaisesRegex(ValueError, "reused"):
                reader.reference(self.ref(path, original), "second")
            reader.unchanged()
            path.write_bytes(b"different16byte")
            with self.assertRaisesRegex(ValueError, "identity|rehash"):
                reader.unchanged()

    def test_hardlink_alias_of_an_original_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-replay-") as directory:
            first, second = Path(directory) / "a.bin", Path(directory) / "b.bin"
            first.write_bytes(b"synthetic")
            os.link(first, second)
            reader = replay.FileArtifacts(); reader.reference(self.ref(first, b"synthetic"), "first")
            with self.assertRaisesRegex(ValueError, "physical artifact alias"):
                reader.reference(self.ref(second, b"synthetic"), "second")

    def test_reparse_ancestor_and_relative_paths_reject(self):
        with self.assertRaisesRegex(ValueError, "relative"):
            replay.checked_path("relative.raw")
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-replay-") as directory:
            path = Path(directory) / "a.bin"; path.write_bytes(b"synthetic")
            actual = Path.lstat
            class Reparse:
                st_mode = stat.S_IFDIR
                st_file_attributes = 0x400
            def lstat(value, *args, **kwargs):
                return Reparse() if value == path.parent else actual(value, *args, **kwargs)
            with patch.object(Path, "lstat", lstat):
                with self.assertRaisesRegex(ValueError, "reparse"):
                    replay.checked_path(str(path))

    def test_final_reparse_substitution_is_rejected_and_original_receipt_retained(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-replay-") as directory:
            path = Path(directory) / "a.bin"; path.write_bytes(b"synthetic")
            reader = replay.FileArtifacts(); reader.reference(self.ref(path, b"synthetic"), "raw")
            actual = Path.lstat
            class Reparse:
                st_mode = stat.S_IFREG
                st_file_attributes = 0x400
            def lstat(value, *args, **kwargs):
                return Reparse() if value == path else actual(value, *args, **kwargs)
            with patch.object(Path, "lstat", lstat):
                with self.assertRaisesRegex(ValueError, "reparse"):
                    reader.unchanged()
            self.assertEqual(reader.receipts()[0]["sha256"], replay.sha(b"synthetic"))

    def test_file_type_hash_size_and_aggregate_budget_reject(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-replay-") as directory:
            path = Path(directory) / "a.bin"; path.write_bytes(b"synthetic")
            for change in ({"sha256": "d" * 64}, {"bytes": True}, {"bytes": 8}):
                with self.subTest(change=change):
                    reference = self.ref(path, b"synthetic"); reference.update(change)
                    with self.assertRaises(ValueError):
                        replay.FileArtifacts().reference(reference, "raw")
            reader = replay.FileArtifacts(); reader.total = replay.MAX_TOTAL_BYTES
            with self.assertRaisesRegex(ValueError, "aggregate artifact budget"):
                reader.reference(self.ref(path, b"synthetic"), "raw")


if __name__ == "__main__":
    unittest.main(verbosity=2)
