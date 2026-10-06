#!/usr/bin/env python3
"""Pure QPC/DbgEng receipt mocks; no process APIs, capture, output or game."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hidden_soak_process_lease as process
import hidden_soak_running_time as timeproof

MOCK_ROOT = "C:/ClashSource"
MOCK_SOURCE = MOCK_ROOT + "/tools/hidden_soak_running_time.py"
MOCK_LEASE = MOCK_ROOT + "/tools/hidden_soak_process_lease.py"
MOCK_LEDGER = MOCK_ROOT + "/tools/hidden_soak_frame_ledger.py"
MOCK_HOST = MOCK_ROOT + "/tools/ordinary_map_pause_host.py"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def token(value):
    return uuid.UUID(int=value).hex


class RunningTimeTests(unittest.TestCase):
    def setUp(self):
        # Explicit modeled Windows paths; actual source bytes stay at real
        # module paths. Scope patches to this fixture and restore every case.
        for module, path in ((timeproof, MOCK_SOURCE), (process, MOCK_LEASE)):
            scoped = patch.object(module, "SOURCE", path)
            scoped.start(); self.addCleanup(scoped.stop)
        self.sources = {process._path(path): (ROOT / "tools" / name).read_bytes()
                        for path, name in ((MOCK_SOURCE, "hidden_soak_running_time.py"),
                            (MOCK_LEASE, "hidden_soak_process_lease.py"),
                            (MOCK_LEDGER, "hidden_soak_frame_ledger.py"),
                            (MOCK_HOST, "ordinary_map_pause_host.py"))}
        self.assertEqual(digest(self.sources[process._path(MOCK_LEASE)]), timeproof.FROZEN_PROCESS_LEASE_SHA256)
        self.assertEqual(digest(self.sources[process._path(MOCK_LEDGER)]), timeproof.FROZEN_WALL_LEDGER_SHA256)
        controller = process.Generation(100, 10, "C:/ClashTools/controller.exe", "1" * 64)
        debugger = process.Generation(200, 20, "C:/ClashTools/host.exe", "2" * 64)
        target = process.Generation(300, 30, "C:/ClashTests/candidate.exe", "3" * 64)
        pins = tuple(process.SourcePin(path, digest(raw)) for path, raw in self.sources.items())
        run = process.RunAuthority(token(1), target.image_sha256, "4" * 64, "modalwidgets", "1920x1080",
                    "test-validation", controller,
                    (process.ImageAuthority("debugger", debugger.image_path, debugger.image_sha256),
                     process.ImageAuthority("candidate", target.image_path, target.image_sha256)), pins)
        self.authority = timeproof.TimeAuthority(run, target, debugger, 400, 0x77001000,
            timeproof.ArtifactBinding("C:/ClashTests/readiness.json", "5" * 64, 100),
            timeproof.ClockAuthority(token(2), 1000, 100000),
            next(pin for pin in pins if pin.path == process._path(MOCK_HOST)),
            tuple(timeproof.CaptureBinding(ordinal, token(1000 + ordinal),
                # Identical static raw pixels are valid at distinct retained
                # paths; neither uniqueness nor nonblack pixels is acceptance.
                timeproof.ArtifactBinding(f"C:/ClashTests/frames/frame-{ordinal:04d}.raw", "6" * 64, 100))
                for ordinal in range(timeproof.CAPTURE_COUNT)))

    def clock(self, tick, authority=None):
        authority = authority or self.authority
        return timeproof.ClockSample(authority.clock.epoch_id, authority.clock.frequency_hz, tick, 1, 0)

    def events(self, authority=None, held_seconds=0):
        authority = authority or self.authority
        observed_target = process.Observation(authority.target, authority.debugger.pid, 258, None, 0)
        observed_debugger = process.Observation(authority.debugger, authority.run.controller.pid, 258, None, 0)
        rows, tick = [], authority.clock.origin_tick
        snapshot = timeproof.source_snapshot_sha256(authority)
        def event(kind, begin=None, end=None, **fields):
            nonlocal tick
            begin = tick if begin is None else begin
            end = begin + 1 if end is None else end
            row = timeproof.NativeEvent(len(rows) + 1, kind, authority.run.run_id, snapshot,
                    self.clock(begin, authority), self.clock(end, authority),
                    observed_target, observed_target, observed_debugger, observed_debugger, **fields)
            rows.append(row); tick = end + 1
            return row
        event("ready", artifact=authority.readiness, get_hresult=0, execution_status=timeproof.BREAK)
        go = event("go", set_hresult=0, get_hresult=0, requested_status=timeproof.GO, execution_status=timeproof.GO)
        credited = 0
        for capture in authority.captures:
            wanted = min(capture.ordinal, timeproof.PERIODIC_COUNT - 1) * timeproof.PERIOD_SECONDS * authority.clock.frequency_hz
            begin = go.end.tick + wanted - credited + 2 * timeproof.ENDPOINT_DEBIT_TICKS
            event("break_request", begin=begin, pause_token=capture.pause_token, native_return=1, native_error=0)
            credited = wanted
            event("break_ack", pause_token=capture.pause_token, get_hresult=0,
                execution_status=timeproof.BREAK, event_hresult=0,
                native_break=timeproof.NativeBreak(2, 0x80000003, 1, authority.target.pid,
                    authority.primary_tid + 1, authority.native_break_address))
            tick += held_seconds * authority.clock.frequency_hz
            event("read_begin", end=tick, pause_token=capture.pause_token, ordinal=capture.ordinal,
                  artifact=capture.artifact, get_hresult=0, execution_status=timeproof.BREAK)
            event("read_end", pause_token=capture.pause_token, ordinal=capture.ordinal,
                  artifact=capture.artifact, get_hresult=0, execution_status=timeproof.BREAK)
            if capture.ordinal != timeproof.CAPTURE_COUNT - 1:
                go = event("go", pause_token=capture.pause_token, set_hresult=0, get_hresult=0,
                           requested_status=timeproof.GO, execution_status=timeproof.GO)
        event("finish", pause_token=authority.captures[-1].pause_token, get_hresult=0,
              execution_status=timeproof.BREAK)
        return rows

    def encode(self, rows=None, authority=None):
        authority = authority or self.authority
        collector = timeproof.TranscriptCollector(authority, self.sources)
        for row in rows if rows is not None else self.events(authority):
            collector.record(row)
        data = collector.encode()
        self.assertEqual(len(data), collector.receipt_bytes)
        return data

    def binding(self, data, authority=None):
        authority = authority or self.authority
        return timeproof.TranscriptBinding(timeproof.authority_sha256(authority),
                timeproof.source_snapshot_sha256(authority), digest(data), len(data))

    def replay(self, data, authority=None, binding=None, sources=None):
        authority = authority or self.authority
        return timeproof.replay(data, authority, binding or self.binding(data, authority),
                                self.sources if sources is None else sources)

    def rejected(self, report):
        result = self.replay(timeproof._canonical(report))
        self.assertFalse(result["raw_running_transcript_replay_passed"], result)
        self.assertTrue(result["failures"])
        return result

    def test_complete_242_schedule_credits_only_7200_GO_receipt_seconds(self):
        rows = self.events(held_seconds=10)
        data = self.encode(rows)
        result = self.replay(data)
        self.assertTrue(result["raw_running_transcript_replay_passed"], result)
        self.assertEqual(result["observed_GO_lower_bound_ns"], 7200 * timeproof.SECOND)
        self.assertEqual(result["bound_capture_count"], 242)
        self.assertGreater(rows[-1].end.tick - self.authority.clock.origin_tick,
                           9600 * self.authority.clock.frequency_hz)
        self.assertTrue(all(result[name] is False for name in timeproof.FALSE_CLAIMS))
        self.assertLess(len(data), timeproof.MAX_JSON_BYTES)

    def test_quantization_is_fixed_source_policy_at_frequency_limits(self):
        for frequency in (1, 1_000_000_000):
            authority = replace(self.authority, clock=replace(self.authority.clock, frequency_hz=frequency))
            result = self.replay(self.encode(authority=authority), authority)
            self.assertTrue(result["raw_running_transcript_replay_passed"], result)
            self.assertEqual(result["observed_GO_lower_bound_ns"], 7200 * timeproof.SECOND)
        report = json.loads(self.encode())
        report["policy"]["endpoint_debit_ticks"] = 0
        self.rejected(report)

    def test_wall_7200_seconds_with_pauses_does_not_satisfy_counter_schedule(self):
        rows = self.events()
        scale = (7200 * self.authority.clock.frequency_hz) / (rows[-1].end.tick - self.authority.clock.origin_tick)
        changed = [replace(row, begin=replace(row.begin, tick=self.authority.clock.origin_tick +
                            int((row.begin.tick - self.authority.clock.origin_tick) * scale)),
                       end=replace(row.end, tick=self.authority.clock.origin_tick +
                            int((row.end.tick - self.authority.clock.origin_tick) * scale))) for row in rows]
        result = self.replay(self.encode(changed))
        self.assertFalse(result["raw_running_transcript_replay_passed"])
        self.assertLess(result["observed_GO_lower_bound_ns"], 7200 * timeproof.SECOND)

    def test_missing_duplicate_reordered_events_and_orphan_finish_fail(self):
        base = json.loads(self.encode())
        for operation in ("remove", "duplicate", "reorder", "finish"):
            with self.subTest(operation=operation):
                report = deepcopy(base)
                if operation == "remove": del report["events"][3]
                elif operation == "duplicate": report["events"].insert(3, deepcopy(report["events"][3]))
                elif operation == "reorder": report["events"][3:5] = reversed(report["events"][3:5])
                else: report["events"] = report["events"][:-1]
                self.rejected(report)

    def test_failed_GO_status_native_break_and_foreign_break_fail(self):
        base = json.loads(self.encode())
        for index, field, value in ((1, "set_hresult", 0x80004005), (1, "execution_status", timeproof.BREAK),
                                    (2, "native_return", 0), (3, "event_hresult", 0x80004005)):
            report = deepcopy(base); report["events"][index][field] = value
            self.rejected(report)
        for field, value in (("thread_tid", self.authority.primary_tid), ("exception_code", 0xc0000005),
                             ("first_chance", 0), ("process_pid", 301), ("address", 0x77002000)):
            report = deepcopy(base); report["events"][3]["native_break"][field] = value
            self.rejected(report)

    def test_resealed_sequence_cannot_hide_missing_native_transition(self):
        base = json.loads(self.encode())
        for index in (1, 2, 3, 4, 5, 6):
            with self.subTest(removed_native_kind=base["events"][index]["kind"]):
                report = deepcopy(base)
                del report["events"][index]
                for sequence, row in enumerate(report["events"], 1):
                    row["sequence"] = sequence
                self.rejected(report)

    def test_removed_failure_cannot_reuse_original_external_artifact_binding(self):
        rows = self.events()
        error = replace(rows[7], kind="unknown", error="source-host native failure", native_error=5)
        rows.insert(7, error)
        rows = [replace(row, sequence=index) for index, row in enumerate(rows, 1)]
        original = self.encode(rows)
        report = json.loads(original)
        del report["events"][7]
        for sequence, row in enumerate(report["events"], 1): row["sequence"] = sequence
        changed = timeproof._canonical(report)
        result = self.replay(changed, binding=self.binding(original))
        self.assertFalse(result["raw_running_transcript_replay_passed"])
        self.assertIn("independently retained transcript binding", result["failures"][0])

    def test_generation_parent_liveness_and_source_aliases_fail(self):
        base = json.loads(self.encode())
        for lane in ("target_before", "target_after", "debugger_before", "debugger_after"):
            for field in ("creation_filetime", "image_sha256"):
                report = deepcopy(base)
                report["events"][7][lane]["generation"][field] = 99 if field == "creation_filetime" else "a" * 64
                self.rejected(report)
        report = deepcopy(base); report["events"][7]["target_before"]["parent_pid"] = 999
        self.rejected(report)
        report = deepcopy(base)
        report["events"][7]["target_before"].update(wait_result=0, exit_code=0, exit_filetime=99)
        self.rejected(report)
        report = deepcopy(base); report["events"][7]["source_snapshot_sha256"] = "a" * 64
        self.rejected(report)

    def test_QPC_epoch_frequency_failure_and_regression_fail(self):
        base = json.loads(self.encode())
        for field, value in (("epoch_id", token(999)), ("frequency_hz", 1001), ("native_return", 0),
                             ("native_error", 5), ("tick", self.authority.clock.origin_tick - 1)):
            report = deepcopy(base); report["events"][7]["begin"][field] = value
            self.rejected(report)
        other = replace(self.authority, clock=replace(self.authority.clock, origin_tick=self.authority.clock.origin_tick + 1))
        self.assertFalse(self.replay(self.encode(), other)["raw_running_transcript_replay_passed"])

    def test_failed_counter_values_are_preserved_before_replay_rejection(self):
        rows = self.events()
        original = timeproof.ClockSample(self.authority.clock.epoch_id, 0, -1, -1, 123)
        rows[7] = replace(rows[7], begin=original, error="native counter failure")
        data = self.encode(rows)
        self.assertEqual(json.loads(data)["events"][7]["begin"], asdict(original))
        result = self.replay(data)
        self.assertFalse(result["raw_running_transcript_replay_passed"])
        self.assertEqual(json.loads(data)["events"][7]["error"], "native counter failure")

    def test_signed_HRESULT_failures_remain_original_before_replay_rejection(self):
        original = self.events()
        signed_E_FAIL = -2147467259
        for index, field in ((1, "set_hresult"), (0, "get_hresult"), (3, "event_hresult")):
            with self.subTest(field=field):
                rows = list(original)
                rows[index] = replace(rows[index], **{field: signed_E_FAIL}, error="original signed E_FAIL")
                data = self.encode(rows)
                retained = json.loads(data)["events"][index]
                self.assertEqual(retained[field], signed_E_FAIL)
                self.assertEqual(retained["error"], "original signed E_FAIL")
                result = self.replay(data)
                self.assertFalse(result["raw_running_transcript_replay_passed"])
                self.assertTrue(all(result[name] is False for name in timeproof.FALSE_CLAIMS))
                self.assertEqual(json.loads(data)["events"][index][field], signed_E_FAIL)
        for field in ("set_hresult", "get_hresult", "event_hresult"):
            for value in (-(1 << 31) - 1, (1 << 32), True):
                with self.subTest(field=field, invalid=value), self.assertRaises(ValueError):
                    replace(original[0], **{field: value})
        # Ordinary DWORD statuses/errors keep their original unsigned bounds.
        for field in ("requested_status", "execution_status", "native_error"):
            with self.subTest(unsigned_field=field), self.assertRaises(ValueError):
                replace(original[0], **{field: -1})

    def test_read_pause_token_ordinal_and_raw_reference_substitution_fail(self):
        base = json.loads(self.encode())
        for index, field, value in ((4, "pause_token", token(999)), (5, "ordinal", 1),
                                    (6, "pause_token", token(999)), (4, "execution_status", timeproof.GO)):
            report = deepcopy(base); report["events"][index][field] = value
            self.rejected(report)
        report = deepcopy(base); report["events"][4]["artifact"]["sha256"] = "a" * 64
        self.rejected(report)
        report = deepcopy(base); report["events"][5]["artifact"]["path"] = report["events"][9]["artifact"]["path"]
        self.rejected(report)

    def test_failed_native_read_end_is_not_counted_as_verified_epoch(self):
        rows = self.events()
        rows[5] = replace(rows[5], get_hresult=0x80004005, error="native held-status check failed")
        result = self.replay(self.encode(rows))
        self.assertFalse(result["raw_running_transcript_replay_passed"])
        self.assertEqual(result["bound_capture_count"], 0)

    def test_all_242_original_pause_epochs_and_artifact_paths_required(self):
        with self.assertRaises(ValueError): replace(self.authority, captures=self.authority.captures[:-1])
        for field, value in (("ordinal", 0), ("pause_token", self.authority.captures[0].pause_token),
                             ("artifact", self.authority.captures[0].artifact)):
            captures = list(self.authority.captures)
            captures[1] = replace(captures[1], **{field: value})
            with self.assertRaises(ValueError): replace(self.authority, captures=tuple(captures))
        # The two final captures have the same GO-duration due point, but must
        # retain distinct pauses and raw artifact references.
        report = json.loads(self.encode())
        terminal = next(row for row in report["events"] if row["kind"] == "read_begin" and row["ordinal"] == 241)
        terminal["ordinal"] = 240
        self.rejected(report)

    def test_read_and_held_deadlines_fail_without_retiming_original_clocks(self):
        for seconds in (21,):
            result = self.replay(self.encode(self.events(held_seconds=seconds)))
            self.assertFalse(result["raw_running_transcript_replay_passed"])
            self.assertIn("expired", result["failures"][0])
        report = json.loads(self.encode())
        # Shift every event from first read_end by three seconds, preserving
        # native chronology while violating the original held-read bound.
        for row in report["events"][5:]:
            row["begin"]["tick"] += 3000; row["end"]["tick"] += 3000
        self.rejected(report)

    def test_slot_shortening_lateness_and_unsupported_policy_fail(self):
        base = json.loads(self.encode())
        for delta in (-1000, 3000):
            report = deepcopy(base)
            for row in report["events"][7:]:
                row["begin"]["tick"] += delta; row["end"]["tick"] += delta
            self.rejected(report)
        for field, value in (("required_seconds", 7199), ("periodic_count", 240), ("capture_count", 241),
                             ("scope", "native_soak_pass"), ("clock", "ambient_wall_time")):
            report = deepcopy(base); report["policy"][field] = value
            self.rejected(report)

    def test_full_original_failure_receipts_stay_retained_and_sticky(self):
        rows = self.events()
        message = "native error detail " + "x" * 3900
        rows[7] = replace(rows[7], kind="unknown", error=message, native_return=0, native_error=123,
                          set_hresult=0x80004005)
        data = self.encode(rows)
        result = self.replay(data)
        self.assertFalse(result["raw_running_transcript_replay_passed"])
        retained = json.loads(data)["events"][7]
        self.assertEqual(retained["error"], message)
        self.assertEqual(retained["native_error"], 123)
        self.assertEqual(retained["set_hresult"], 0x80004005)
        self.assertEqual(len(json.loads(data)["events"]), len(rows))

    def test_external_candidate_probe_source_binding_changes_fail(self):
        data = self.encode()
        other_run = replace(self.authority.run, probe_sha256="a" * 64)
        self.assertFalse(self.replay(data, replace(self.authority, run=other_run))["raw_running_transcript_replay_passed"])
        sources = dict(self.sources); sources[process._path(MOCK_HOST)] += b"\nchanged"
        self.assertFalse(self.replay(data, sources=sources)["raw_running_transcript_replay_passed"])
        wrong = replace(self.binding(data), artifact_sha256="a" * 64)
        self.assertFalse(self.replay(data, binding=wrong)["raw_running_transcript_replay_passed"])
        report = json.loads(data); report["events"][7]["run_id"] = token(999)
        self.rejected(report)

    def test_claims_extra_fields_bool_integers_and_noncanonical_JSON_fail(self):
        base = json.loads(self.encode())
        for name in timeproof.FALSE_CLAIMS:
            report = deepcopy(base); report["claims"][name] = True
            self.rejected(report)
        for name, value in (("running_duration_verified", True), ("elapsed_seconds", 7200)):
            report = deepcopy(base); report[name] = value
            self.rejected(report)
        report = deepcopy(base); report["events"][7]["begin"]["native_return"] = True
        self.rejected(report)
        report = deepcopy(base); report["policy"]["endpoint_debit_ticks"] = True
        self.rejected(report)
        data = json.dumps(base, indent=2).encode("utf-8")
        self.assertFalse(self.replay(data)["raw_running_transcript_replay_passed"])
        data = timeproof._canonical(base).replace(b'{"authority_sha256":', b'{"schema":"invented","authority_sha256":', 1)
        self.assertFalse(self.replay(data)["raw_running_transcript_replay_passed"])

    def test_transcript_capacity_retains_original_attempt_without_truncation(self):
        collector = timeproof.TranscriptCollector(self.authority, self.sources)
        row = self.events()[0]
        collector.record(row)
        original = collector.encode()
        with patch.object(timeproof, "MAX_JSON_BYTES", len(original)):
            with self.assertRaises(timeproof.TranscriptLimitError) as failure:
                collector.record(replace(row, sequence=2, kind="unknown", error="original failure"))
        self.assertEqual(collector.encode(), original)
        self.assertEqual(failure.exception.event.error, "original failure")
        self.assertEqual(failure.exception.report["events"], [asdict(row)])
        with patch.object(timeproof, "MAX_EVENTS", 1):
            with self.assertRaises(timeproof.TranscriptLimitError): collector.record(replace(row, sequence=1))
        self.assertEqual(collector.encode(), original)

    def test_budget_is_explicit_additional_owned_serialized_bytes_only(self):
        allowance = timeproof.retention_allowance()
        self.assertEqual(allowance["transcript_bytes"], 4 * 1024 * 1024)
        self.assertEqual(allowance["additional_peak_bytes"], 8 * 1024 * 1024)
        self.assertFalse(allowance["included_in_frozen_wall_ledger_budget"])
        self.assertEqual(timeproof.MAX_EVENTS, 4096)
        self.assertEqual(timeproof.MAX_ERROR_BYTES, 4096)


if __name__ == "__main__":
    unittest.main(verbosity=2)
