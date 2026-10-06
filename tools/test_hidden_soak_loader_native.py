"""Portable synthetic binary receipts; no native/COM/process/file outputs.

The private parser factory seam explicitly models request issuance only for
these synthetic PE fixtures. Public production request admission stays closed.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT))
import hidden_soak_loader_native as native
import hidden_soak_loader_native_adapter as adapter
import hidden_soak_loaded_read_session as session
import hidden_soak_loaded_image as image
import test_hidden_soak_loaded_image as image_fixture
import test_hidden_soak_loaded_read_session as session_fixture
import pe_extension as pe


def digest(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def generation(observed, parent):
    path = observed.image_path.encode("utf-16-le")
    return dict(pid=observed.pid, pid_error=0, path_return=1, path_error=0, path_chars=len(path) // 2,
        image_path_utf16le=path.hex(), times_return=1, times_error=0, creation_filetime=observed.creation_filetime,
        exit_filetime=0, kernel_filetime=1, user_filetime=2, image_sha256=observed.image_sha256, hash_status=0,
        wait_result=258, wait_error=0, parent_pid=parent.pid if parent else 77,
        parent_query_return=1, parent_query_error=0, parent_creation_filetime=parent.creation_filetime if parent else 900,
        parent_times_return=1, parent_times_error=0)


def owner(observed):
    return dict(run_id=observed.run_id, checkpoint_id=observed.checkpoint_id, clock_epoch=observed.clock_epoch,
        controller=generation(observed.controller, None), debugger=generation(observed.debugger, observed.controller),
        target=generation(observed.target, observed.debugger), probe_sequence=observed.probe_sequence,
        breakpoint_sequence=observed.breakpoint_sequence, command_sequence=observed.command_sequence)


class Recorder(session_fixture.MockAdapter):
    def __init__(self, bound, authority, anchor):
        super().__init__(bound, authority, anchor); self.rows, self.ordinal = [], 0
    def emit(self, operation, data, raw=b""):
        self.rows.append((operation, data, raw))
    def counter(self):
        original = super().counter(); self.emit("counter", asdict(original)); return original
    def observe_owner(self):
        original = super().observe_owner(); self.emit("owner", owner(original)); return original
    def query(self, name):
        original = super().query(name); self.emit("query", asdict(original)); return original
    def get_number_breakpoints(self):
        original = super().get_number_breakpoints(); self.emit("GetNumberBreakpoints", asdict(original)); return original
    def pointer64(self):
        original = super().pointer64(); self.emit("pointer64", asdict(original)); return original
    def read_virtual(self, address, size):
        original = super().read_virtual(address, size)
        self.emit("read_virtual", dict(ordinal=self.ordinal, address=address, requested_bytes=size,
            hresult=original.hresult, returned_bytes=original.returned_bytes), original.raw)
        self.ordinal += 1; return original


def encode(rows, *, finish=True):
    output, raw_bytes, metadata_bytes = bytearray(b"CLHDLR1\0"), 0, 8
    for sequence, (operation, data, raw) in enumerate(rows, 1):
        metadata = canonical(dict(sequence=sequence, operation=operation, data=data))
        output.extend(struct.pack("<II", len(metadata), len(raw))); output.extend(metadata); output.extend(raw)
        raw_bytes += len(raw); metadata_bytes += 8 + len(metadata)
    if finish:
        metadata = canonical(dict(sequence=len(rows) + 1, operation="finish", data=dict(status="complete",
            frame_count=len(rows), raw_bytes=raw_bytes, metadata_bytes=metadata_bytes, comparison_scope="asynchronous_only")))
        output.extend(struct.pack("<II", len(metadata), 0)); output.extend(metadata)
    return bytes(output)


class NativeArchiveTests(unittest.TestCase):
    def setUp(self):
        self.bound = image_fixture.contract()
        self.owned = replace(image_fixture.authority(self.bound), clock_origin_ns=1, checkpoint_start_ns=1001)
        self.anchor = session.QpcAnchor(self.owned.clock_epoch, 1000000, 1000, 1, 1001)
        self.recorder = Recorder(self.bound, self.owned, self.anchor)
        result = session._collect(self.bound, self.owned, self.anchor, self.recorder, oracle=image, pe=pe, check_sources=lambda: None)
        self.assertTrue(result.report()["supplied_receipt_collection_passed"], result.report())
        self.request = object(); request_bytes = b"private synthetic request bytes; no production admission"
        host = b"private synthetic native host source; no native execution"
        self.source_paths = (Path(native.__file__).resolve(), Path(adapter.__file__).resolve())
        self.sources = tuple(path.read_bytes() for path in self.source_paths)
        plan = self.bound.plan()
        self.metadata = dict(request_sha256=digest(request_bytes), host_source_sha256=digest(host),
            native_source_sha256=digest(self.sources[0]), adapter_source_sha256=digest(self.sources[1]),
            candidate_sha256=self.owned.candidate_sha256, profile=self.owned.profile, resolution=self.owned.resolution,
            stage=self.owned.stage, recipe_revision=self.owned.recipe_revision, probe_sha256=self.owned.probe_sha256,
            source_closure_sha256=self.owned.source_closure_sha256, run_id=self.owned.run_id,
            checkpoint_id=self.owned.checkpoint_id, epoch_id=self.owned.clock_epoch, controller_pid=self.owned.controller.pid,
            frequency_hz=1000000, origin_tick=1000, origin_ns=1, preferred_base=0x400000,
            image_size=plan["immutable_scope"]["image_size"])
        def check_sources():
            if tuple(path.read_bytes() for path in self.source_paths) != self.sources: raise ValueError("actual fixture source bytes changed")
        def collect(authority, anchor, supplied):
            return session._collect(self.bound, authority, anchor, supplied, oracle=image, pe=pe, check_sources=check_sources)
        self.facts = native.RequestFacts(canonical(self.metadata).decode("ascii"), request_bytes, host,
            tuple((row["rva"], row["size"]) for row in plan["immutable_scope"]["chunks"]), collect, check_sources)
        def inspect(request):
            if request is not self.request: raise ValueError("private synthetic issuer identity differs")
            check_sources(); return self.facts
        with patch.object(native, "inspect_request", inspect):
            self.parse, self.create, self.collect = adapter._api_factory()
        self.rows = self.startup() + self.recorder.rows + self.ending()

    def qpc(self, tick):
        return dict(epoch_id=self.owned.clock_epoch, frequency_hz=1000000, tick=tick,
            frequency_native_return=1, frequency_native_error=0, counter_native_return=1, counter_native_error=0)

    def startup(self):
        invocation = dict(request_sha256=self.metadata["request_sha256"], candidate_file_sha256=self.owned.candidate_sha256,
            host_file_sha256=self.owned.debugger.image_sha256, controller_pid=self.owned.controller.pid,
            run_id=self.owned.run_id, checkpoint_id=self.owned.checkpoint_id, epoch_id=self.owned.clock_epoch,
            comparison_scope="asynchronous_only")
        rows = [("invocation", invocation, b""), ("origin", dict(anchor={name: self.metadata[name]
            for name in ("epoch_id", "frequency_hz", "origin_tick", "origin_ns")}, sample=self.qpc(1000)), b"")]
        names = ("DebugCreate", "QueryInterface.control", "QueryInterface.memory", "QueryInterface.system",
                 "SetEventCallbacks", "SetOutputCallbacks", "AddEngineOptions", "GetEngineOptions", "CreateProcess")
        for index, name in enumerate(names):
            if name == "CreateProcess":
                rows.append(("launch", dict(target_path_utf16le=(self.owned.target.image_path.encode("utf-16-le") + b"\0\0").hex(),
                    command_hex=("\"" + self.owned.target.image_path + "\"").encode("ascii").hex() + "00", create_flags=0x08000002), b""))
            rows.append(("setup", dict(api_name=name, hresult=0, value=0x100000000 + index if index < 4 else 0x1020 if name == "GetEngineOptions" else None), b""))
        rows.append(("callback_create", dict(image_handle=50, process_handle=51, initial_thread_handle=52,
            base_offset=self.owned.image_base, module_size=self.metadata["image_size"], thread_data_offset=0, start_offset=self.owned.image_base,
            module_name_hex=b"candidate\0".hex(), image_name_hex=b"candidate.exe\0".hex(), pid=self.owned.target.pid, tid=self.owned.primary_tid,
            checksum=0, timestamp=0, pid_error=0, tid_error=0,
            duplicate_process_return=1, duplicate_process_error=0, duplicate_thread_return=1, duplicate_thread_error=0,
            owned_process_handle=61, owned_thread_handle=62), b""))
        record = bytearray(152); struct.pack_into("<IIQQI", record, 0, 0x80000003, 0, 0, 0x77001234, 0)
        exception_sequence = len(rows) + 1
        rows.append(("callback_exception", dict(record_hex=bytes(record).hex(), first_chance=1, qpc=self.qpc(1001)), b""))
        extra = bytearray(256); extra[:152] = record; struct.pack_into("<I", extra, 152, 1)
        rows.extend([("wait_event", dict(hresult=0, flags=0, timeout_ms=15000), b""),
            ("event", dict(hresult=0, type=2, engine_pid=self.owned.engine_pid, engine_tid=self.owned.engine_tid,
                extra_hex=bytes(extra).hex(), description_hex=bytes(1024).hex(), extra_used=160, description_used=1), b""),
            ("peb", dict(hresult=0, address=self.owned.peb_address), b""),
            ("held", dict(qpc=self.qpc(1002), initial_exception_sequence=exception_sequence), b""),
            ("startup_owner", owner(session.OwnerObservation(self.owned.run_id, self.owned.checkpoint_id, self.owned.clock_epoch,
                self.owned.controller, self.owned.debugger, self.owned.target, (258, 258, 258), (0, 0, 0), 0, 0, 0)), b"")])
        return rows

    def ending(self):
        cleanup = dict(target_pid=self.owned.target.pid, target_pid_error=0, target_wait=0, target_wait_error=0,
            target_creation_filetime=self.owned.target.creation_filetime, target_exit_filetime=self.owned.target.creation_filetime + 1,
            target_kernel_filetime=1, target_user_filetime=2, target_times_return=1, target_times_error=0,
            target_exit_return=1, target_exit_error=0, target_exit_code=259)
        for role in ("target", "thread", "controller", "debugger"): cleanup.update({role + "_close": 1, role + "_close_error": 0})
        cleanup.update(event_callbacks_hresult=0, output_callbacks_hresult=0)
        return [("stop", dict(end_session_hresult=0, qpc=self.qpc(self.recorder.tick + 1),
                    execution_status=dict(name=image.PHASE_QUERY_NAMES[0], hresult=0, value=7)), b""), ("cleanup", cleanup, b"")]

    def authority(self, raw, **changes):
        values = dict(request_sha256=self.metadata["request_sha256"], candidate_file_sha256=self.owned.candidate_sha256,
            host_file_sha256=self.owned.debugger.image_sha256, host_source_sha256=self.metadata["host_source_sha256"],
            native_source_sha256=self.metadata["native_source_sha256"], adapter_source_sha256=self.metadata["adapter_source_sha256"],
            archive_sha256=digest(raw), archive_size=len(raw), run_id=self.owned.run_id,
            checkpoint_id=self.owned.checkpoint_id, epoch_id=self.owned.clock_epoch, controller_pid=self.owned.controller.pid,
            observed_host_exit_code=0)
        values.update(changes); return adapter.ArchiveAuthority(**values)

    def parse_rows(self, rows=None):
        raw = encode(self.rows if rows is None else rows)
        return self.parse(raw, self.authority(raw), self.request)

    def index(self, operation):
        return next(index for index, row in enumerate(self.rows) if row[0] == operation)

    def rejected(self, raw):
        with self.assertRaises(adapter.ArchiveError) as caught: self.parse(raw, self.authority(raw), self.request)
        self.assertIs(caught.exception.original_archive, raw)
        return caught.exception

    def test_complete_original_frames_collect_asynchronous_scope_and_no_broad_claims(self):
        parsed = self.parse_rows(); result = self.collect(parsed, self.owned, self.anchor)
        self.assertTrue(result.report()["supplied_receipt_collection_passed"], result.report())
        self.assertTrue(all(result.report()[name] is False for name in session.FALSE_CLAIMS))
        self.assertEqual(tuple(row.raw for row in parsed.frames if row.operation == "read_virtual"), tuple(read.raw for read in result.oracle_reads))
        self.assertEqual(parsed.frames[0].data()["comparison_scope"], "asynchronous_only")

    def test_truncated_archive_every_boundary_retained_without_filling(self):
        raw = encode(self.rows)
        for size in (0, 1, 7, 8, 9, 15, 16, len(raw) - 1, len(raw) - 8): self.rejected(raw[:size])
        self.rejected(raw + b"\0")

    def test_frame_caps_overflow_magic_noncanonical_duplicates_and_extra_fields_fail(self):
        for bad in (b"CLHDLR2\0", b"CLHDLR1\0" + struct.pack("<II", 0xffffffff, 0),
                    b"CLHDLR1\0" + struct.pack("<II", 1, 65540) + b"0"):
            self.rejected(bad)
        for metadata in (b'{"sequence":1,"sequence":1,"operation":"invocation","data":{}}',
                         b'{"sequence": 1,"operation":"invocation","data":{}}',
                         canonical(dict(sequence=True, operation="invocation", data={})),
                         canonical(dict(sequence=1, operation="invocation", data={}, passed=True))):
            self.rejected(b"CLHDLR1\0" + struct.pack("<II", len(metadata), 0) + metadata)

    def test_missing_duplicate_reordered_startup_and_terminal_originals_fail(self):
        for index in (0, 1, *(self.index(op) for op in ("launch", "callback_create", "callback_exception", "wait_event", "event", "peb", "held", "startup_owner")), len(self.rows) - 2, len(self.rows) - 1):
            rows = deepcopy(self.rows); del rows[index]; self.rejected(encode(rows))
        rows = deepcopy(self.rows); rows[0], rows[1] = rows[1], rows[0]; self.rejected(encode(rows))
        rows = deepcopy(self.rows); index = self.index("callback_exception"); rows.insert(index, deepcopy(rows[index])); self.rejected(encode(rows))

    def test_unknown_invented_success_error_original_message_and_failed_finish_fail(self):
        rows = deepcopy(self.rows); rows.insert(12, ("error", dict(type_name="native_error", message_hex=b"whole raw native failure".hex(), retention_debt=True), b""))
        error = self.rejected(encode(rows)); self.assertTrue(error.parsed_frames)
        self.assertEqual(error.parsed_frames[12].data()["message_hex"], b"whole raw native failure".hex())
        rows = deepcopy(self.rows); rows[0][1]["passed"] = True; self.rejected(encode(rows))
        rows = deepcopy(self.rows); rows[0] = ("observer_pass", rows[0][1], b""); self.rejected(encode(rows))

    def test_external_launch_candidate_request_sources_exit_and_archive_bindings_fail(self):
        raw = encode(self.rows)
        for field in ("request_sha256", "candidate_file_sha256", "host_file_sha256", "host_source_sha256", "native_source_sha256", "adapter_source_sha256", "archive_sha256"):
            with self.assertRaises(adapter.ArchiveError): self.parse(raw, self.authority(raw, **{field: "a" * 64}), self.request)
        with self.assertRaises(adapter.ArchiveError): self.parse(raw, self.authority(raw, observed_host_exit_code=3), self.request)
        with self.assertRaises(adapter.ArchiveError): self.parse(raw, self.authority(raw), object())

    def test_owner_missing_failed_foreign_paths_hashes_and_parent_generation_fail(self):
        for field, value in (("path_return", 0), ("path_chars", 999), ("hash_status", -1), ("wait_result", 0),
                             ("creation_filetime", 9), ("parent_creation_filetime", 1), ("parent_pid", 999),
                             ("image_sha256", "a" * 64), ("image_path_utf16le", "zz")):
            rows = deepcopy(self.rows); rows[self.index("startup_owner")][1]["target"][field] = value
            parsed = self.parse_rows(rows)
            with self.assertRaises(ValueError): self.create(parsed, self.owned, self.anchor)
        rows = deepcopy(self.rows); del rows[self.index("startup_owner")][1]["target"]["parent_pid"]
        parsed = self.parse_rows(rows)
        with self.assertRaises(ValueError): self.create(parsed, self.owned, self.anchor)

    def test_held_original_clock_stop_work_and_selected_peb_IDS_fail(self):
        for operation, path, value in (("held", "initial_exception_sequence", 999), ("peb", "address", 0),
                                   ("event", "engine_pid", 999)):
            index = self.index(operation)
            rows = deepcopy(self.rows); rows[index][1][path] = value
            if operation == "event":
                parsed = self.parse_rows(rows)
                with self.assertRaises(ValueError): self.create(parsed, self.owned, self.anchor)
            else: self.rejected(encode(rows))
        rows = deepcopy(self.rows); rows[-2][1]["qpc"]["tick"] = 1001 + 20 * 1000000 + 1; self.rejected(encode(rows))
        parsed = self.parse_rows()
        with self.assertRaises(ValueError): self.create(parsed, self.owned, replace(self.anchor, held_start_tick=1002))

    def test_callback_last_event_semantics_active_params_and_padding_scope(self):
        for field in ("ExceptionCode", "ExceptionAddress", "FirstChance", "NumberParameters"):
            rows = deepcopy(self.rows); index = self.index("event"); raw = bytearray.fromhex(rows[index][1]["extra_hex"])
            struct.pack_into("<I", raw, {"ExceptionCode": 0, "ExceptionAddress": 16, "FirstChance": 152, "NumberParameters": 24}[field], 16)
            rows[index][1]["extra_hex"] = raw.hex(); self.rejected(encode(rows))
        rows = deepcopy(self.rows); index = self.index("event"); raw = bytearray.fromhex(rows[index][1]["extra_hex"]); raw[28] = 0xa5; raw[159:] = b"x" * 97
        rows[index][1]["extra_hex"] = raw.hex(); parsed = self.parse_rows(rows)
        self.assertTrue(self.collect(parsed, self.owned, self.anchor).report()["supplied_receipt_collection_passed"])

    def test_partial_failed_read_and_stale_native_HRESULTs_retained_no_next_operation(self):
        rows = deepcopy(self.rows); index = next(i for i, row in enumerate(rows) if row[0] == "read_virtual")
        rows[index][1].update(hresult=-2147467259, returned_bytes=2); rows[index] = (*rows[index][:2], b"xx")
        parsed = self.parse_rows(rows); result = self.collect(parsed, self.owned, self.anchor)
        self.assertFalse(result.report()["supplied_receipt_collection_passed"])
        self.assertEqual(result.raw_attempts[0].original_return.raw, b"xx")
        self.assertEqual(result.raw_attempts[0].original_return.hresult, -2147467259)
        self.assertIsNone(result.raw_attempts[0].phase_after)
        for operation in ("query", "GetNumberBreakpoints", "pointer64"):
            rows = deepcopy(self.rows); index = next(i for i, row in enumerate(rows) if row[0] == operation)
            rows[index][1]["hresult"] = -2147467259
            parsed = self.parse_rows(rows); result = self.collect(parsed, self.owned, self.anchor)
            self.assertFalse(result.report()["supplied_receipt_collection_passed"])

    def test_caller_archive_clones_row_mutation_source_change_and_unconsumed_rows_fail(self):
        parsed = self.parse_rows()
        for clone in (replace(parsed), adapter.ParsedArchive(parsed.original_archive, parsed.frames)):
            with self.assertRaises(ValueError): self.create(clone, self.owned, self.anchor)
        supplied = self.create(parsed, self.owned, self.anchor)
        with self.assertRaises(ValueError): supplied.require_consumed()
        row = next(row for row in parsed.frames if row.operation == "read_virtual")
        object.__setattr__(row, "raw", b"changed")
        with self.assertRaises(ValueError): self.create(parsed, self.owned, self.anchor)

    def test_public_alias_forged_request_and_generic_approval_reports_never_issue(self):
        raw = encode(self.rows)
        with patch.object(native, "inspect_request", lambda request: self.facts):
            with self.assertRaises(adapter.ArchiveError): adapter.parse_archive(raw, self.authority(raw), self.request)
        with self.assertRaises(adapter.ArchiveError): adapter.parse_archive(raw, self.authority(raw), {"passed": True})

    def test_output_callback_originals_transparent_order_and_bad_cstring_fail(self):
        rows = deepcopy(self.rows)
        for offset in (5, self.index("read_virtual"), len(self.rows) - 2):
            rows.insert(offset, ("output", dict(mask=1, text_hex=b"full original debugger output\0".hex()), b""))
        # Insertions before the initial exception shift its original ordinal.
        held = next(row[1] for row in rows if row[0] == "held")
        held["initial_exception_sequence"] = next(i + 1 for i, row in enumerate(rows) if row[0] == "callback_exception")
        parsed = self.parse_rows(rows)
        self.assertEqual(len([row for row in parsed.frames if row.operation == "output"]), 3)
        self.assertTrue(self.collect(parsed, self.owned, self.anchor).report()["supplied_receipt_collection_passed"])
        rows = deepcopy(self.rows); rows.insert(5, ("output", dict(mask=1, text_hex=b"truncated".hex()), b""))
        self.rejected(encode(rows))

    def test_callback_disable_launch_arguments_engine_options_and_bool_aliases_fail(self):
        for field in ("event_callbacks_hresult", "output_callbacks_hresult", "target_pid_error"):
            rows = deepcopy(self.rows); rows[-1][1][field] = -2147467259; self.rejected(encode(rows))
        for field, value in (("command_hex", b'"C:/other.exe"\0'.hex()), ("create_flags", 2)):
            rows = deepcopy(self.rows); rows[self.index("launch")][1][field] = value; self.rejected(encode(rows))
        rows = deepcopy(self.rows); rows[1][1]["anchor"]["origin_ns"] = True; self.rejected(encode(rows))
        for name in ("probe_sequence", "breakpoint_sequence", "command_sequence"):
            rows = deepcopy(self.rows); rows[self.index("startup_owner")][1][name] = False
            parsed = self.parse_rows(rows)
            with self.assertRaises(ValueError): self.create(parsed, self.owned, self.anchor)
        rows = deepcopy(self.rows)
        next(row[1] for row in rows if row[0] == "setup" and row[1]["api_name"] == "GetEngineOptions")["value"] = 0x120
        self.rejected(encode(rows))

    def test_callbacks_inside_CreateProcess_and_native_failed_raw_prefix_are_retained(self):
        rows = deepcopy(self.rows)
        receipt = next(i for i, row in enumerate(rows) if row[0] == "setup" and row[1]["api_name"] == "CreateProcess")
        created = next(i for i, row in enumerate(rows) if row[0] == "callback_create")
        rows[receipt], rows[created] = rows[created], rows[receipt]
        parsed = self.parse_rows(rows)
        self.assertTrue(self.collect(parsed, self.owned, self.anchor).report()["supplied_receipt_collection_passed"])
        rows = deepcopy(self.rows)
        index = self.index("read_virtual")
        rows.insert(index, ("native_failure", dict(api_name="ReadFile", native_return=0, native_error=5,
            requested_bytes=65536, returned_bytes=3, detail_hex=""), b"xyz"))
        error = self.rejected(encode(rows))
        self.assertEqual(error.parsed_frames[index].raw, b"xyz")
        rows[index] = ("native_failure", dict(api_name="ReadFile", native_return=0, native_error=5,
            requested_bytes=8, returned_bytes=3, detail_hex=""), b"xyz\0\0\0\0\0")
        error = self.rejected(encode(rows))
        self.assertEqual(error.parsed_frames[index].raw, b"xyz\0\0\0\0\0")
        self.assertEqual(error.parsed_frames[index].data()["returned_bytes"], 3)

    def test_launch_before_engine_setup_and_changed_fixed_wait_rejected(self):
        rows = deepcopy(self.rows)
        launched = rows.pop(self.index("launch")); rows.insert(2, launched)
        self.rejected(encode(rows))
        for timeout in (1, 14999, 15001, 20000):
            rows = deepcopy(self.rows); rows[self.index("wait_event")][1]["timeout_ms"] = timeout
            self.rejected(encode(rows))

    def test_original_negative_or_uncalled_stop_cleanup_and_parent_queries_retained(self):
        for field in ("end_session_hresult",):
            for failure in (-2147467259, None):
                rows = deepcopy(self.rows); rows[-2][1][field] = failure
                error = self.rejected(encode(rows))
                self.assertEqual(error.parsed_frames[-3].data()[field], failure)
        for field in ("parent_query_return", "parent_times_return"):
            rows = deepcopy(self.rows); rows[self.index("startup_owner")][1]["controller"][field] = 0
            parsed = self.parse_rows(rows)
            with self.assertRaises(ValueError): self.create(parsed, self.owned, self.anchor)

    def test_failure_tail_capacity_retained_but_cannot_be_complete(self):
        raw = encode(self.rows)
        metadata_bytes = len(raw) - sum(len(row[2]) for row in self.rows)
        with patch.object(adapter, "MAX_TOTAL_METADATA", metadata_bytes - 1), \
             patch.object(adapter, "MAX_FAILURE_METADATA", metadata_bytes + 1024):
            error = self.rejected(raw)
            self.assertEqual(len(error.parsed_frames), len(self.rows) + 1)

    def test_source_change_after_parse_and_public_parser_aliases_rejected(self):
        parsed = self.parse_rows()
        real_reader = Path.read_bytes
        def changed(path):
            original = real_reader(path)
            return original + b"changed in mocked RAM" if path == self.source_paths[1] else original
        with patch.object(Path, "read_bytes", changed):
            with self.assertRaises(ValueError): self.create(parsed, self.owned, self.anchor)
        raw = encode(self.rows)
        def forbidden(*args): raise AssertionError("poisoned public alias must not issue authority")
        with patch.object(adapter, "_frames", forbidden), patch.object(adapter, "_protocol", forbidden), \
             patch.object(adapter, "OfflineAdapter", forbidden):
            self.assertTrue(self.collect(self.parse(raw, self.authority(raw), self.request), self.owned,
                                         self.anchor).report()["supplied_receipt_collection_passed"])

    def test_initial_callback_precedes_native_origin_or_module_extent_substitution_fail(self):
        rows = deepcopy(self.rows); rows[1][1]["sample"]["tick"] = 1002
        self.rejected(encode(rows))
        rows = deepcopy(self.rows); rows[self.index("callback_create")][1]["module_size"] += 1
        parsed = self.parse_rows(rows)
        with self.assertRaises(ValueError): self.create(parsed, self.owned, self.anchor)

    def test_create_and_load_callback_names_match_exact_native_capacity_and_cstring(self):
        def changed_rows(operation, field, original):
            rows = deepcopy(self.rows)
            if operation == "callback_load":
                at = self.index("callback_create")
                create = rows[at][1]
                load = {key: create[key] for key in adapter.LOAD_FIELDS}
                rows.insert(at + 1, ("callback_load", load, b""))
                at += 1
                exception = next(i for i, row in enumerate(rows) if row[0] == "callback_exception")
                next(row for row in rows if row[0] == "held")[1]["initial_exception_sequence"] = exception + 1
            else: at = self.index(operation)
            rows[at][1][field] = original.hex()
            return rows
        for operation in ("callback_create", "callback_load"):
            for field in ("module_name_hex", "image_name_hex"):
                for original in (b"missing terminator", b"a\0b\0", b"x" * 32768 + b"\0"):
                    with self.subTest(operation=operation, field=field, original_bytes=len(original)):
                        rows = changed_rows(operation, field, original)
                        self.rejected(encode(rows))
                for original in (b"", b"x" * 32767 + b"\0"):
                    with self.subTest(operation=operation, field=field, allowed_bytes=len(original)):
                        rows = changed_rows(operation, field, original)
                        self.assertTrue(self.collect(self.parse_rows(rows), self.owned,
                                                     self.anchor).report()["supplied_receipt_collection_passed"])

    def test_resealed_current_source_cannot_replace_imported_adapter_bytes(self):
        changed = self.sources[1] + b"\n# source changed after import; resealed fixture only\n"
        self.sources = (self.sources[0], changed)
        self.metadata["adapter_source_sha256"] = digest(changed)
        self.facts = replace(self.facts, metadata_json=canonical(self.metadata).decode("ascii"))
        real_reader = Path.read_bytes
        def newer(path): return changed if path == self.source_paths[1] else real_reader(path)
        raw = encode(self.rows)
        with patch.object(Path, "read_bytes", newer):
            with self.assertRaises(adapter.ArchiveError) as caught:
                self.parse(raw, self.authority(raw), self.request)
        self.assertIs(caught.exception.original_archive, raw)
        self.assertIn("imported adapter", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
