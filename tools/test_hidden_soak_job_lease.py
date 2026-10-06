"""Portable supplied-receipt mocks only; no Windows/native/process adapters."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hidden_soak_job_lease as job
import hidden_soak_process_lease as process
import hidden_soak_running_time as clock

MOCK_SOURCE = "C:/fixture/tools/hidden_soak_job_lease.py"
MOCK_PROCESS = "C:/fixture/tools/hidden_soak_process_lease.py"
MOCK_CLOCK = "C:/fixture/tools/hidden_soak_running_time.py"
MOCK_OWNED = "C:/fixture/tools/owned_hidden_process.py"
MOCK_HOST = "C:/fixture/instrumented_job_host.cpp"
ROLES = ("desktop", "job", "stdin", "stdout_duplicate", "debugger_process", "debugger_thread", "candidate_process")
APIS = dict(desktop="CreateDesktopW", job="CreateJobObjectW", limit_set="SetInformationJobObject",
    limit_query="QueryInformationJobObject", stdin="CreateFileW", stdout="DuplicateHandle", launch="CreateProcessW",
    identity="GetProcessId/QueryFullProcessImageNameW/GetProcessTimes/WaitForSingleObject/GetExitCodeProcess",
    assign="AssignProcessToJobObject", membership="IsProcessInJob", resume="ResumeThread", target_open="OpenProcess",
    pids="QueryInformationJobObject", accounting="QueryInformationJobObject", terminate="TerminateJobObject",
    wait="WaitForSingleObject/GetProcessId/QueryFullProcessImageNameW/GetProcessTimes/GetExitCodeProcess", finish="")


def digest(data): return hashlib.sha256(data).hexdigest()
def token(value): return f"{value:032x}"


def limits():
    raw = bytearray(144)
    struct.pack_into("<I", raw, 16, 0x2000)
    return bytes(raw)


def pids(values):
    raw = bytearray(b"\xa5" * 520)  # Unused original capacity is retained.
    struct.pack_into("<II", raw, 0, len(values), len(values))
    for index, value in enumerate(values): struct.pack_into("<Q", raw, 8 + index * 8, value)
    return bytes(raw)


def accounting(active, *, total=2, times=(0, 1, 2, 3)):
    return struct.pack("<4q4I", *times, 7, total, active, 0)


class JobTests(unittest.TestCase):
    def setUp(self):
        # Modeled Windows locations only; actual module bytes remain real and
        # the two SOURCE attributes are restored after every portable case.
        for module, name, value in ((job, "SOURCE", MOCK_SOURCE), (process, "SOURCE", MOCK_PROCESS)):
            owner = patch.object(module, name, value); owner.start(); self.addCleanup(owner.stop)
        self.sources = {process._path(MOCK_SOURCE): job.MODULE_PATH.read_bytes(),
            process._path(MOCK_PROCESS): Path(process.__file__).read_bytes(),
            process._path(MOCK_CLOCK): Path(clock.__file__).read_bytes(),
            process._path(MOCK_OWNED): (job.MODULE_PATH.parent / "owned_hidden_process.py").read_bytes(),
            process._path(MOCK_HOST): b"mock future native host source; no adapter exists\n"}
        controller = process.Generation(100, 1000, "C:/controller/controller.exe", digest(b"controller"))
        debugger = process.Generation(200, 2000, "C:/host/observer.exe", digest(b"debugger"))
        target = process.Generation(300, 3000, "C:/candidate/game.exe", digest(b"candidate"))
        run = process.RunAuthority(token(1), target.image_sha256, digest(b"canonical probe"), "modalwidgets", "1920x1080", "validation-fixture",
            controller, (process.ImageAuthority("debugger", debugger.image_path, debugger.image_sha256),
                         process.ImageAuthority("candidate", target.image_path, target.image_sha256)),
            tuple(process.SourcePin(path, digest(data)) for path, data in self.sources.items()))
        self.authority = job.JobAuthority(run, debugger, target, 400, clock.ClockAuthority(token(2), 1000, 1000),
            process.SourcePin(MOCK_HOST, digest(self.sources[process._path(MOCK_HOST)])),
            tuple(job.HandleToken(role, token(10 + index)) for index, role in enumerate(ROLES)),
            0x900, "ClashOwnedHost_" + token(3))
        self.tokens = {row.role: row.token for row in self.authority.handles}
        self.handles = {role: 0x100 + index for index, role in enumerate(ROLES)}

    def identity(self, role, *, live=True, code=259):
        generation = self.authority.debugger if role == "debugger_process" else self.authority.target
        parent = self.authority.run.controller.pid if role == "debugger_process" else self.authority.debugger.pid
        # Stale errors on successful native calls are not success predicates.
        return job.RawIdentity(generation.pid, 123, generation.image_path, generation.image_sha256,
            2, 456, generation.creation_filetime, 0 if live else generation.creation_filetime + 1,
            -1, 789, parent, 258 if live else 0, 1, 999, code)

    def events(self, *, parent_exited=False, drain_active=(), stale_error=183):
        rows = []
        epoch, frequency = self.authority.clock.epoch_id, self.authority.clock.frequency_hz
        snapshot = job.source_snapshot_sha256(self.authority)
        def event(kind, role="", phase="", **values):
            tick = self.authority.clock.origin_tick + 3 * len(rows)
            api = ("CloseDesktop" if role == "desktop" else "CloseHandle") if kind == "close" else APIS[kind]
            values.setdefault("api_name", api)
            values.setdefault("native_error", stale_error)
            if role: values.setdefault("handle_value", self.handles[role])
            row = job.RawJobEvent(len(rows) + 1, kind, self.authority.run.run_id, snapshot,
                clock.ClockSample(epoch, frequency, tick, 2, 123), clock.ClockSample(epoch, frequency, tick + 1, -1, 456),
                token=self.tokens.get(role, ""), phase=phase, **values)
            rows.append(row); return row
        def query(kind, phase, live_pids=None, active=None):
            size, info = {"limit_query": (144, 9), "pids": (520, 3), "accounting": (48, 1)}[kind]
            output = limits() if kind == "limit_query" else pids(live_pids) if kind == "pids" else accounting(active)
            returned = 8 + 8 * len(live_pids) if kind == "pids" else size
            return event(kind, "job", phase, native_return=2, information_class=info, requested_bytes=size,
                         returned_bytes=returned, output_buffer=output)
        def membership(role, phase, *, live=True):
            witness = self.identity(role, live=live)
            event("membership", role, phase, related_token=self.tokens["job"], related_handle_value=self.handles["job"],
                  native_return=-1, membership_result=2 if live else 0, identity_before=witness, identity_after=witness)
        event("desktop", "desktop", object_name=self.authority.desktop_name)
        event("job", "job")
        event("limit_set", "job", native_return=2, information_class=9, requested_bytes=144, input_buffer=limits())
        query("limit_query", "setup")
        event("stdin", "stdin", object_name="NUL", flags=0x80000000, inherit_handles=1)
        event("stdout", "stdout_duplicate", native_return=1, borrowed_handle_value=self.authority.caller_stdout_handle, flags=2, inherit_handles=1)
        event("launch", "debugger_process", native_return=1, related_token=self.tokens["debugger_thread"],
            related_handle_value=self.handles["debugger_thread"], value=self.authority.debugger_primary_tid,
            object_name=self.authority.desktop_name,
            process_pid=self.authority.debugger.pid, flags=0x08080404, inherit_handles=1,
            inherited_tokens=(self.tokens["stdin"], self.tokens["stdout_duplicate"]))
        event("close", "stdout_duplicate", native_return=1)
        event("close", "stdin", native_return=1)
        event("identity", "debugger_process", "startup", identity_before=self.identity("debugger_process"))
        event("assign", "debugger_process", related_token=self.tokens["job"], related_handle_value=self.handles["job"], native_return=1)
        membership("debugger_process", "startup")
        event("resume", "debugger_thread", value=1)
        event("close", "debugger_thread", native_return=1)
        event("target_open", "candidate_process", flags=0x00101001, process_pid=self.authority.target.pid, inherit_handles=0)
        event("identity", "candidate_process", "startup", identity_before=self.identity("candidate_process"))
        membership("candidate_process", "startup")
        query("limit_query", "startup"); query("pids", "startup", [300, 200]); query("accounting", "startup", active=2)
        event("identity", "debugger_process", "precleanup", identity_before=self.identity("debugger_process", live=not parent_exited))
        event("identity", "candidate_process", "precleanup", identity_before=self.identity("candidate_process"))
        membership("debugger_process", "precleanup", live=not parent_exited); membership("candidate_process", "precleanup")
        live_pids = [300] if parent_exited else [200, 300]
        query("limit_query", "precleanup"); query("pids", "precleanup", live_pids); query("accounting", "precleanup", active=len(live_pids))
        event("terminate", "job", native_return=1, value=1)
        for role in ("debugger_process", "candidate_process"):
            event("wait", role, value=0, timeout_milliseconds=5000, identity_before=self.identity(role, live=False))
        for active in (*drain_active, 0):
            query("accounting", "drain", active=active); query("pids", "drain", [200, 300][:active])
        for role in ("candidate_process", "debugger_process", "job", "desktop"):
            event("close", role, native_return=1)
        event("finish", native_error=0)
        return rows

    def encode(self, rows=None):
        collector = job.TranscriptCollector(self.authority, self.sources)
        for row in self.events() if rows is None else rows: collector.record(row)
        data = collector.encode(); self.assertEqual(len(data), collector.receipt_bytes)
        return data

    def binding(self, data, authority=None):
        authority = authority or self.authority
        return job.TranscriptBinding(job.authority_sha256(authority), job.source_snapshot_sha256(authority), digest(data), len(data))

    def replay(self, data, *, authority=None, binding=None, sources=None):
        authority = authority or self.authority
        return job.replay(data, authority, binding or self.binding(data, authority), self.sources if sources is None else sources)

    def rejected(self, report):
        data = job._canonical(report) if type(report) is dict else report
        result = self.replay(data)
        self.assertFalse(result.report()["raw_job_receipt_replay_passed"], result.report())
        self.assertTrue(result.report()["failures"])
        self.assertIs(result.original_transcript, data)
        return result.report()

    def test_complete_protocol_stale_errors_raw_bool_forms_and_parent_exit(self):
        for parent_exited in (False, True):
            with self.subTest(parent_exited=parent_exited):
                data = self.encode(self.events(parent_exited=parent_exited))
                result = self.replay(data).report()
                self.assertTrue(result["raw_job_receipt_replay_passed"], result)
                self.assertEqual(result["remaining_handle_debt"], [])
                self.assertEqual(set(result["acquired_roles"]), set(ROLES))
                self.assertTrue(all(result[name] is False for name in job.FALSE_CLAIMS))
        self.assertEqual(job.policy()["controller_abi"], "WIN64_only")

    def test_original_PID_capacity_tail_and_documented_used_length_are_retained(self):
        data = self.encode(); original = json.loads(data)
        row = next(row for row in original["events"] if row["kind"] == "pids" and row["phase"] == "startup")
        self.assertEqual(row["returned_bytes"], 24)
        self.assertEqual(len(bytes.fromhex(row["output_buffer"])), 520)
        self.assertEqual(bytes.fromhex(row["output_buffer"])[24:], b"\xa5" * 496)
        for length in (0, 23, 25, 520, 0xffffffff):
            changed = deepcopy(original); changed["events"][row["sequence"] - 1]["returned_bytes"] = length
            self.rejected(changed)

    def test_missing_duplicate_reordered_operations_and_assignmentless_empty_job_fail(self):
        original = json.loads(self.encode())
        for index in (0, 1, 2, 3, 6, 10, 11, 12, 14, 16, 27, 28, 29, 30, 31, 32, 35, 36):
            with self.subTest(missing=index):
                changed = deepcopy(original); del changed["events"][index]
                for number, row in enumerate(changed["events"], 1): row["sequence"] = number
                self.rejected(changed)
        for operation in ("duplicate", "resume_first", "drain_before_wait"):
            changed = deepcopy(original)
            if operation == "duplicate": changed["events"].insert(10, deepcopy(changed["events"][10]))
            elif operation == "resume_first": changed["events"][10], changed["events"][12] = changed["events"][12], changed["events"][10]
            else: changed["events"][28:32] = changed["events"][30:32] + changed["events"][28:30]
            for number, row in enumerate(changed["events"], 1): row["sequence"] = number
            self.rejected(changed)

    def test_job_flags_input_readback_raw_extents_and_other_controller_ABI_fail(self):
        original = json.loads(self.encode())
        for index in (2, 3, 17, 24):
            field = "input_buffer" if index == 2 else "output_buffer"
            for flags in (0, 0x2800, 0x3000, 0x2001):
                changed = deepcopy(original); raw = bytearray.fromhex(changed["events"][index][field]); struct.pack_into("<I", raw, 16, flags)
                changed["events"][index][field] = raw.hex(); self.rejected(changed)
            for size in (112, 143, 145):
                changed = deepcopy(original); raw = bytes.fromhex(changed["events"][index][field])
                changed["events"][index][field] = (raw[:size] if size < 144 else raw + b"x").hex(); self.rejected(changed)
        changed = deepcopy(original); changed["policy"]["controller_abi"] = "WIN32"; self.rejected(changed)

    def test_failed_short_overflow_queries_and_matching_stale_buffers_fail_retained(self):
        rows = self.events()
        for index in (3, 18, 19, 30, 31):
            for values in (dict(native_return=0, native_error=234), dict(returned_bytes=0xffffffff),
                           dict(output_buffer=rows[index].output_buffer[:-1])):
                bad = list(rows); bad[index] = replace(bad[index], **values)
                data = self.encode(bad); result = self.rejected(data)
                self.assertEqual(json.loads(data)["events"][index], json.loads(job._canonical(job._wire(bad[index]))))
                self.assertTrue(all(result[name] is False for name in job.FALSE_CLAIMS))

    def test_PID_count_slots_duplicates_and_unknown_late_descendants_fail(self):
        original = json.loads(self.encode())
        for assigned, count in ((3, 2), (65, 65), (0xffffffff, 0xffffffff)):
            changed = deepcopy(original); raw = bytearray.fromhex(changed["events"][18]["output_buffer"])
            struct.pack_into("<II", raw, 0, assigned, count); changed["events"][18]["output_buffer"] = raw.hex(); self.rejected(changed)
        for values in ((200, 200), (100, 300), (200, 301), (0x1000000c8, 300), (0, 300)):
            changed = deepcopy(original); changed["events"][18]["output_buffer"] = pids(values).hex(); self.rejected(changed)
        rows = self.events(drain_active=(1,))
        rows[31] = replace(rows[31], output_buffer=pids((999,)))
        self.rejected(self.encode(rows))

    def test_generation_parent_liveness_query_failure_and_handle_reuse_fail(self):
        original = json.loads(self.encode())
        for index, side in ((9, "identity_before"), (11, "identity_after"), (15, "identity_before"), (16, "identity_before")):
            for field, value in (("pid", 999), ("creation_filetime", 1), ("parent_pid", 999), ("path_return", 0),
                                 ("times_return", 0), ("exit_return", 0), ("wait_result", 0xffffffff),
                                 ("image_sha256", "a" * 64), ("image_path", "C:/other.exe")):
                changed = deepcopy(original); changed["events"][index][side][field] = value; self.rejected(changed)
        for index, field, value in ((6, "related_handle_value", self.handles["job"]), (6, "process_pid", 999),
                                    (10, "related_handle_value", 999), (11, "membership_result", 0),
                                    (12, "value", 0xffffffff), (14, "inherit_handles", 1)):
            changed = deepcopy(original); changed["events"][index][field] = value; self.rejected(changed)

    def test_inherited_job_protected_stdout_wrong_API_and_unexpected_fields_fail(self):
        original = json.loads(self.encode())
        for index, field, value in ((6, "inherited_tokens", [self.tokens["job"], self.tokens["stdin"]]),
                                    (6, "flags", 0x09080404), (6, "inherit_handles", 0),
                                    (5, "borrowed_handle_value", 999), (5, "handle_value", self.authority.caller_stdout_handle),
                                    (1, "object_name", "existing_named_job"), (35, "api_name", "CloseHandle"),
                                    (6, "object_name", None), (6, "object_name", "default"), (6, "value", 401),
                                    (36, "native_error", 183)):
            changed = deepcopy(original); changed["events"][index][field] = value; self.rejected(changed)
        changed = deepcopy(original); changed["events"][3]["force_success"] = True; self.rejected(changed)

    def test_original_failures_and_failed_close_retries_never_erase_first_error(self):
        rows = self.events(); first = next(index for index, row in enumerate(rows) if row.kind == "close" and row.token == self.tokens["candidate_process"])
        message = "native close failure detail " + "x" * 3900
        failed = replace(rows[first], native_return=0, native_error=6, error=message)
        rows.insert(first, failed)
        rows = [replace(row, sequence=index + 1,
            begin=replace(row.begin, tick=1000 + 3 * index), end=replace(row.end, tick=1001 + 3 * index)) for index, row in enumerate(rows)]
        data = self.encode(rows); result = self.rejected(data)
        self.assertEqual(json.loads(data)["events"][first]["error"], message)
        self.assertEqual(len(json.loads(data)["events"]), len(rows))
        self.assertIn("original native error retained", result["failures"][0])
        changed = json.loads(data); del changed["events"][first]
        for number, row in enumerate(changed["events"], 1): row["sequence"] = number
        altered = job._canonical(changed)
        self.assertFalse(self.replay(altered, binding=self.binding(data)).report()["raw_job_receipt_replay_passed"])

    def test_retained_waits_then_final_empty_pair_and_every_close_required(self):
        original = json.loads(self.encode())
        for index in (28, 29):
            changed = deepcopy(original); changed["events"][index]["value"] = 258; self.rejected(changed)
            changed = deepcopy(original); changed["events"][index]["identity_before"]["wait_result"] = 258; self.rejected(changed)
        for active in (1, 2):
            changed = deepcopy(original); changed["events"][30]["output_buffer"] = accounting(active).hex(); self.rejected(changed)
        for index in range(32, 36):
            changed = deepcopy(original); changed["events"][index]["native_return"] = 0; self.rejected(changed)

    def test_clock_origin_epoch_order_failed_QPC_and_drain_deadline_fail(self):
        original = json.loads(self.encode())
        for field, value in (("epoch_id", token(999)), ("frequency_hz", 999), ("native_return", 0), ("tick", -1)):
            changed = deepcopy(original); changed["events"][10]["begin"][field] = value; self.rejected(changed)
        changed = deepcopy(original); changed["events"][31]["end"]["tick"] += 5001; self.rejected(changed)
        altered = replace(self.authority, clock=replace(self.authority.clock, origin_tick=1001))
        self.assertFalse(self.replay(self.encode(), authority=altered).report()["raw_job_receipt_replay_passed"])

    def test_accounting_original_counters_not_booleans_and_invalid_lengths_fail(self):
        original = json.loads(self.encode())
        for raw in (accounting(3), accounting(2, total=1), accounting(2, times=(-1, 1, 2, 3)), b"x" * 47):
            changed = deepcopy(original); changed["events"][19]["output_buffer"] = raw.hex(); self.rejected(changed)
        changed = deepcopy(original); changed["events"][19]["returned_bytes"] = 47; self.rejected(changed)

    def test_external_candidate_probe_source_artifact_and_canonical_schema_fail(self):
        data = self.encode()
        other = replace(self.authority, run=replace(self.authority.run, probe_sha256="a" * 64))
        self.assertFalse(self.replay(data, authority=other).report()["raw_job_receipt_replay_passed"])
        wrong = replace(self.binding(data), artifact_sha256="a" * 64)
        self.assertFalse(self.replay(data, binding=wrong).report()["raw_job_receipt_replay_passed"])
        sources = dict(self.sources); sources[process._path(MOCK_HOST)] += b"changed"
        self.assertFalse(self.replay(data, sources=sources).report()["raw_job_receipt_replay_passed"])
        original = json.loads(data)
        for field, value in (("accepted", True), ("cleanup", {"job_empty": True, "handles_closed": True})):
            changed = deepcopy(original); changed[field] = value; self.rejected(changed)
        changed = deepcopy(original); changed["claims"]["no_breakaway_job_verified"] = True; self.rejected(changed)
        self.rejected(data + b"\n")
        self.rejected(b'{"schema":"x","schema":"y"}')

    def test_bool_integer_coercion_and_full_raw_buffer_overflow_diagnostics(self):
        rows = self.events()
        for field, value in (("native_return", True), ("value", True), ("handle_value", "256"), ("output_buffer", bytearray(b"x"))):
            with self.subTest(field=field), self.assertRaises(ValueError): replace(rows[3], **{field: value})
        bad = list(rows); bad[18] = replace(rows[18], output_buffer=b"q" * 600, returned_bytes=600, native_return=0, native_error=234)
        data = self.encode(bad); self.rejected(data)
        self.assertEqual(bytes.fromhex(json.loads(data)["events"][18]["output_buffer"]), b"q" * 600)
        for field, value in (("output_buffer", b"q" * 4097), ("error", "q" * 4097)):
            with self.assertRaises(ValueError): replace(rows[18], **{field: value})
        gaps = self.replay(self.encode()).report()["mandatory_future_gaps"]
        self.assertIn("oversized original native buffers/errors retained before bounded record construction", gaps)
        self.assertIn("public Python aliases are not privately reconstructed native producer authority", gaps)

    def test_capacity_preserves_entire_original_attempt_and_budget_is_additional(self):
        collector = job.TranscriptCollector(self.authority, self.sources)
        rows = self.events(); collector.record(rows[0]); before = collector.report()
        with patch.object(job, "MAX_EVENTS", 1):
            with self.assertRaises(job.TranscriptLimitError) as caught: collector.record(rows[1])
        self.assertIs(caught.exception.event, rows[1])
        self.assertEqual(caught.exception.report["events"], before["events"])
        self.assertEqual(job.retention_allowance()["additional_peak_bytes"], 8 * 1024 * 1024)
        self.assertFalse(job.retention_allowance()["included_in_frozen_frame_budget"])

    def test_source_guard_failure_retains_prior_and_entire_attempt(self):
        collector = job.TranscriptCollector(self.authority, self.sources)
        rows = self.events(); collector.record(rows[0]); before = collector.report()
        collector.source_bytes[process._path(MOCK_HOST)] += b"changed"
        with self.assertRaises(job.TranscriptLimitError) as caught: collector.record(rows[1])
        self.assertIs(caught.exception.event, rows[1])
        self.assertEqual(caught.exception.report["events"], before["events"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
