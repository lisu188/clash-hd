#!/usr/bin/env python3
"""Mocked initial-loader receipts only; no native adapters, I/O or outputs."""
from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import struct
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0, str(ROOT / "src" / "patcher")); sys.path.insert(0, str(ROOT))
import hidden_soak_loaded_read_session as tool
import hidden_soak_loaded_image as oracle
import pe_extension as pe
import test_hidden_soak_loaded_image as image_fixture
import test_pe_extension as pe_fixture


class MockAdapter:
    def __init__(self, bound, authority, anchor):
        self.bound, self.authority, self.anchor = bound, authority, anchor
        self.tick, self.step, self.calls = anchor.held_start_tick, 1, []
        self.owner_change = self.query_change = self.pointer_change = self.counter_change = self.read_change = None
        self.breakpoint_change = None
        self.reads = {row.address: row.raw for row in image_fixture.observations(bound, authority)}

    def counter(self):
        self.calls.append("counter"); self.tick += self.step
        row = tool.QpcSample(self.anchor.epoch_id, self.anchor.frequency_hz, self.tick, 1, 0, 1, 0)
        return self.counter_change(row) if self.counter_change else row

    def observe_owner(self):
        self.calls.append("owner"); a = self.authority
        row = tool.OwnerObservation(a.run_id, a.checkpoint_id, a.clock_epoch, a.controller, a.debugger, a.target,
                                    (258, 258, 258), (0, 0, 0), 0, 0, 0)
        return self.owner_change(row) if self.owner_change else row

    def query(self, name):
        self.calls.append(name)
        values = dict(zip(oracle.PHASE_QUERY_NAMES, (6, self.authority.target.pid, self.authority.primary_tid,
                                                    self.authority.engine_pid, self.authority.engine_tid)))
        row = oracle.NativeQuery(name, 0, values[name])
        return self.query_change(row) if self.query_change else row

    def pointer64(self):
        self.calls.append("pointer64"); row = tool.Pointer64Result(1)
        return self.pointer_change(row) if self.pointer_change else row

    def get_number_breakpoints(self):
        self.calls.append("GetNumberBreakpoints"); row = tool.BreakpointCountResult(0, 0)
        return self.breakpoint_change(row) if self.breakpoint_change else row

    def read_virtual(self, address, size):
        self.calls.append("read_virtual")
        row = tool.ReadResult(0, len(self.reads[address]), self.reads[address])
        return self.read_change(row) if self.read_change else row

    def go(self): raise AssertionError("collector must never resume")
    def probe(self): raise AssertionError("collector must never execute a probe")
    def entry_breakpoint(self): raise AssertionError("collector must never arm a breakpoint")


class ReadSessionTests(unittest.TestCase):
    def setUp(self):
        self.bound = image_fixture.contract()
        self.authority = image_fixture.authority(self.bound)
        self.anchor = tool.QpcAnchor(self.authority.clock_epoch, 1_000_000, 1000,
                                    self.authority.clock_origin_ns, 1001)
        self.authority = replace(self.authority, checkpoint_start_ns=tool.project(self.anchor, self.anchor.held_start_tick).lower_ns)
        self.adapter = MockAdapter(self.bound, self.authority, self.anchor)

    def collect(self, *, authority=None, anchor=None, check_sources=lambda: None):
        result = tool._collect(self.bound, authority or self.authority, anchor or self.anchor, self.adapter,
                               oracle=oracle, pe=pe, check_sources=check_sources)
        for field in tool.FALSE_CLAIMS: self.assertIs(result.report()[field], False)
        return result

    def reject(self, **kwargs):
        result = self.collect(**kwargs)
        self.assertFalse(result.report()["supplied_receipt_collection_passed"], result.report())
        self.assertTrue(result.report()["failures"])
        return result

    def test_complete_fixed_requests_and_five_query_order_are_replayed(self):
        result = self.collect()
        self.assertTrue(result.report()["supplied_receipt_collection_passed"], result.report())
        expected = image_fixture.observations(self.bound, self.authority)
        self.assertEqual([(row.address, row.requested_bytes, row.raw) for row in result.oracle_reads],
                         [(row.address, row.requested_bytes, row.raw) for row in expected])
        self.assertEqual(len(result.raw_attempts), self.bound.plan()["immutable_scope"]["required_read_count"])
        queries = [row.argument for row in result.receipts if row.operation == "query"]
        self.assertEqual(queries, list(oracle.PHASE_QUERY_NAMES) * (2 * len(result.oracle_reads)))
        boundaries = 2 * len(result.oracle_reads)
        self.assertEqual(len([row for row in result.receipts if row.operation == "GetNumberBreakpoints"]), boundaries)
        self.assertTrue(all((row.original.hresult, row.original.count) == (0, 0) for row in result.receipts
                            if row.operation == "GetNumberBreakpoints"))
        for read in result.oracle_reads:
            for phase in (read.phase_before, read.phase_after):
                self.assertEqual((phase.probe_sequence, phase.breakpoint_sequence), (0, 0))
        self.assertEqual(result.report()["retained_raw_bytes"], sum(len(row.raw) for row in result.oracle_reads))
        self.assertEqual(result.report()["projection_count"], len([row for row in result.receipts if row.operation == "projection"]))

    def test_full_interior_bytes_and_zero_tail_never_sample_or_normalize(self):
        def mutate(row):
            if len(row.raw) > 100:
                raw = bytearray(row.raw); raw[len(raw) // 2] ^= 1
                return replace(row, raw=bytes(raw))
            return row
        self.adapter.read_change = mutate
        result = self.reject()
        self.assertEqual(len(result.oracle_reads), 3)
        self.assertIn("canonical byte replay", result.report()["failures"][0])
        self.assertNotEqual(result.raw_attempts[1].original_return.raw, self.adapter.reads[result.raw_attempts[1].address])

    def test_complete_zero_tail_raw_is_required_and_retained(self):
        candidate = bytearray(pe_fixture.synthetic_pe()); struct.pack_into("<I", candidate, 0x88 + 224 + 8, 0x600)
        self.bound = image_fixture.contract(bytes(candidate))
        self.authority = image_fixture.authority(self.bound)
        self.authority = replace(self.authority, checkpoint_start_ns=tool.project(self.anchor, self.anchor.held_start_tick).lower_ns)
        self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
        result = self.collect()
        self.assertTrue(result.report()["supplied_receipt_collection_passed"])
        self.assertEqual(result.oracle_reads[-1].raw, bytes(0x400))
        self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
        self.adapter.reads[result.oracle_reads[-1].address] = b"x" + bytes(0x3ff)
        self.reject()

    def test_partial_failed_native_read_is_original_and_immediately_stops(self):
        for code in (-2147467259, 0x80004005, 1):
            with self.subTest(code=code):
                self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
                returned = tool.ReadResult(code, 2, b"\x00\x40")
                self.adapter.read_change = lambda row: returned
                result = self.reject()
                self.assertIs(result.raw_attempts[0].original_return, returned)
                self.assertIsNone(result.raw_attempts[0].end_counter)
                self.assertIsNone(result.raw_attempts[0].phase_after)
                self.assertEqual(result.oracle_reads, ())
                self.assertEqual(self.adapter.calls[-1], "read_virtual")

    def test_count_and_raw_length_fail_without_post_failure_operations(self):
        for changes in (dict(returned_bytes=0), dict(raw=b""), dict(returned_bytes=9999)):
            with self.subTest(changes=changes):
                self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
                self.adapter.read_change = lambda row, changes=changes: replace(row, **changes)
                result = self.reject()
                self.assertEqual(self.adapter.calls[-1], "read_virtual")
                self.assertIsNotNone(result.raw_attempts[0].original_return)

    def test_each_signed_unsigned_query_failure_retains_matching_stale_value(self):
        for name in oracle.PHASE_QUERY_NAMES:
            for code in (-2147467259, 0x80004005):
                with self.subTest(name=name, code=code):
                    self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
                    self.adapter.query_change = lambda row: replace(row, hresult=code) if row.name == name else row
                    result = self.reject()
                    failed = [row.original for row in result.receipts if row.operation == "query"][-1]
                    self.assertEqual((failed.name, failed.hresult), (name, code))
                    self.assertEqual(self.adapter.calls[-1], name)
                    self.assertFalse(result.raw_attempts)

    def test_pointer_hresult_failures_remain_original(self):
        for code in (-2147467259, 0x80004005, 0):
            with self.subTest(code=code):
                self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
                self.adapter.pointer_change = lambda row: replace(row, hresult=code)
                result = self.reject()
                self.assertEqual([row.original for row in result.receipts if row.operation == "pointer64"][-1].hresult, code)
                self.assertEqual(self.adapter.calls[-1], "pointer64")

    def test_each_original_owner_sequence_nonzero_or_missing_is_retained_and_rejected(self):
        for name in ("probe_sequence", "breakpoint_sequence", "command_sequence"):
            with self.subTest(name=name):
                self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
                self.adapter.owner_change = lambda row: replace(row, **{name: 1})
                result = self.reject()
                self.assertEqual(getattr(result.receipts[-2].original, name), 1)
                self.assertEqual(self.adapter.calls[-1], "owner")
                self.assertFalse(result.raw_attempts)
        self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
        self.adapter.owner_change = lambda row: {key: value for key, value in asdict(row).items()
                                                if key != "command_sequence"}
        result = self.reject()
        observed = [row.original for row in result.receipts if row.operation == "owner"][-1]
        self.assertNotIn("command_sequence", observed)
        self.assertFalse(result.raw_attempts)

    def test_changed_owner_sequence_at_each_boundary_cannot_be_manufactured_zero(self):
        for owner_ordinal in (2, 3, 4):
            for name in ("probe_sequence", "breakpoint_sequence", "command_sequence"):
                with self.subTest(owner_ordinal=owner_ordinal, name=name):
                    self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
                    seen = [0]
                    def changed(row):
                        seen[0] += 1
                        return replace(row, **{name: 1}) if seen[0] == owner_ordinal else row
                    self.adapter.owner_change = changed
                    result = self.reject()
                    observed = [row.original for row in result.receipts if row.operation == "owner"][-1]
                    self.assertEqual(getattr(observed, name), 1)
                    self.assertEqual(self.adapter.calls[-1], "owner")
                    self.assertFalse(result.oracle_reads)
                    if owner_ordinal >= 3:
                        self.assertIsNotNone(result.raw_attempts[0].original_return)
                        self.assertIsNone(result.raw_attempts[0].phase_after)

    def test_breakpoint_native_hresult_count_missing_and_changed_receipts_fail_stop(self):
        for changes in (dict(hresult=-2147467259), dict(hresult=0x80004005), dict(hresult=1), dict(count=1)):
            with self.subTest(changes=changes):
                self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
                self.adapter.breakpoint_change = lambda row: replace(row, **changes)
                result = self.reject()
                original = [row.original for row in result.receipts if row.operation == "GetNumberBreakpoints"][-1]
                for name, value in changes.items(): self.assertEqual(getattr(original, name), value)
                self.assertEqual(self.adapter.calls[-1], "GetNumberBreakpoints")
                self.assertFalse(result.raw_attempts)
        self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
        self.adapter.breakpoint_change = lambda row: {"count": 0}
        result = self.reject()
        self.assertEqual([row.original for row in result.receipts if row.operation == "GetNumberBreakpoints"][-1], {"count": 0})
        self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
        self.adapter.get_number_breakpoints = None
        self.reject(); self.assertNotIn("read_virtual", self.adapter.calls)
        self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
        state = [False]
        def read(row): state[0] = True; return row
        self.adapter.read_change = read
        self.adapter.breakpoint_change = lambda row: replace(row, count=1) if state[0] else row
        result = self.reject()
        self.assertEqual(self.adapter.calls[-1], "GetNumberBreakpoints")
        self.assertIsNotNone(result.raw_attempts[0].original_return)
        self.assertIsNone(result.raw_attempts[0].phase_after)

    def test_owner_generation_paths_reuse_waits_errors_and_tokens_fail(self):
        for changes in (dict(target=replace(self.authority.target, creation_filetime=3001)),
                        dict(debugger=replace(self.authority.debugger, image_path="C:/other/cdb.exe")),
                        dict(wait_results=(258, 0, 258)), dict(native_errors=(0, 5, 0)),
                        dict(checkpoint_id="4" * 32), dict(clock_epoch="5" * 32)):
            with self.subTest(changes=list(changes)):
                self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
                self.adapter.owner_change = lambda row: replace(row, **changes)
                self.reject(); self.assertEqual(self.adapter.calls[-1], "owner")

    def test_foreign_selected_ids_status_and_query_reordering_fail(self):
        for name in oracle.PHASE_QUERY_NAMES:
            with self.subTest(name=name):
                self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
                self.adapter.query_change = lambda row: replace(row, value=row.value + 1) if row.name == name else row
                self.reject(); self.assertEqual(self.adapter.calls[-1], name)
        self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
        self.adapter.query_change = lambda row: replace(row, name=oracle.PHASE_QUERY_NAMES[-1])
        self.reject()

    def test_counter_failures_foreign_epoch_frequency_and_regression_preserved(self):
        for changes in (dict(counter_native_return=0, counter_native_error=5, tick=-1),
                        dict(frequency_native_return=0, frequency_native_error=5, frequency_hz=-1),
                        dict(epoch_id="4" * 32), dict(frequency_hz=self.anchor.frequency_hz + 1), dict(tick=0)):
            with self.subTest(changes=changes):
                self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
                self.adapter.counter_change = lambda row: replace(row, **changes)
                result = self.reject()
                self.assertEqual(len(self.adapter.calls), 1)
                self.assertEqual(result.receipts[0].operation, "counter")

    def test_rational_bridge_retains_remainder_and_never_extends_twenty_seconds(self):
        anchor = tool.QpcAnchor(self.anchor.epoch_id, 3, 1000, 1000, 1000)
        mapped = tool.project(anchor, 1001)
        self.assertEqual((mapped.numerator_ns, mapped.denominator_hz, mapped.remainder, mapped.lower_ns, mapped.upper_ns),
                         (1_000_000_000, 3, 1, 333334333, 333334334))
        owned = replace(self.authority, clock_origin_ns=1000, checkpoint_start_ns=1000)
        self.adapter = MockAdapter(self.bound, owned, anchor)
        self.adapter.tick = anchor.held_start_tick + 20 * anchor.frequency_hz
        result = self.reject(authority=owned, anchor=anchor)
        self.assertEqual(self.adapter.calls, ["counter"])
        self.assertIn("20s", result.report()["failures"][0])

    def test_expensive_admission_cannot_reset_old_frozen_hold_or_epoch(self):
        self.adapter.tick = self.anchor.held_start_tick + 20 * self.anchor.frequency_hz
        self.reject(); self.assertEqual(self.adapter.calls, ["counter"])
        self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
        self.reject(anchor=replace(self.anchor, held_start_tick=self.anchor.held_start_tick + 1))
        self.assertFalse(self.adapter.calls)

    def test_independent_binding_and_arbitrary_request_plan_fail_before_access(self):
        for changes in (dict(profile="framed"), dict(source_closure_sha256="0" * 64), dict(probe_sha256="0" * 64)):
            self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
            self.reject(authority=replace(self.authority, **changes)); self.assertFalse(self.adapter.calls)
        plan = self.bound.plan(); plan["immutable_scope"]["chunks"].pop()
        self.bound = replace(self.bound, plan_json=oracle._canonical(plan))
        self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
        self.reject(); self.assertFalse(self.adapter.calls)

    def test_source_change_after_read_rejects_and_keeps_exact_complete_attempt(self):
        state = [False]
        def read_change(row): state[0] = True; return row
        self.adapter.read_change = read_change
        def check():
            if state[0]: raise ValueError("source closure changed after native read")
        result = self.reject(check_sources=check)
        self.assertEqual(len(result.raw_attempts), 1)
        self.assertEqual(len(result.oracle_reads), 1)
        self.assertIsNotNone(result.raw_attempts[0].phase_after)

    def test_final_counter_source_mutation_is_rechecked_after_collection(self):
        # Discover the fixed counter inventory with a complete mock, then
        # mutate the source check state during the last adapter operation.
        healthy = self.collect()
        count = len([row for row in healthy.receipts if row.operation == "counter"])
        self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
        state = [0, False]
        def changed(row):
            state[0] += 1
            if state[0] == count: state[1] = True
            return row
        self.adapter.counter_change = changed
        def check():
            if state[1]: raise ValueError("source changed in final counter callback")
        result = self.reject(check_sources=check)
        self.assertEqual(len(result.oracle_reads), len(healthy.oracle_reads))
        self.assertEqual(self.adapter.calls[-1], "counter")

    def test_post_read_owner_mutation_retains_raw_without_fabricating_after_phase(self):
        state = [False]
        def after_read(row): state[0] = True; return row
        def changed_owner(row):
            return replace(row, target=replace(row.target, creation_filetime=3001)) if state[0] else row
        self.adapter.read_change, self.adapter.owner_change = after_read, changed_owner
        result = self.reject()
        self.assertEqual(len(result.raw_attempts), 1)
        self.assertIsNotNone(result.raw_attempts[0].original_return)
        self.assertIsNone(result.raw_attempts[0].phase_after)
        self.assertFalse(result.oracle_reads)

    def test_oversized_original_raw_capacity_is_retained_pending_without_retry(self):
        with patch.object(tool, "RAW_SCOPE_BYTES", 0), patch.object(tool, "RAW_TEMPORARY_BYTES", 0):
            result = self.reject()
        self.assertIsNotNone(result.pending)
        self.assertIs(result.pending.original, result.raw_attempts[0].original_return)
        self.assertEqual(result.report()["pending_ram_raw_bytes"], 4)
        self.assertEqual(self.adapter.calls[-1], "read_virtual")

    def test_complete_receipt_metadata_and_count_caps_keep_pending_object(self):
        for changes in (dict(MAX_RECEIPTS=2), dict(METADATA_BYTES=tool.REPORT_RESERVE_BYTES + 2)):
            self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
            with patch.multiple(tool, **changes): result = self.reject()
            self.assertIsNotNone(result.pending)
            self.assertEqual(result.pending.sequence, len(result.receipts) + 1)
            self.assertFalse(result.raw_attempts)

    def test_native_exception_partial_payload_and_long_full_error_are_retained(self):
        original = tool.ReadResult(-2147467259, 2, b"xx")
        class PartialError(RuntimeError):
            original_result = original
        def failed(row): raise PartialError("native read failed after partial transfer")
        self.adapter.read_change = failed
        result = self.reject()
        self.assertIs(result.raw_attempts[0].original_return, original)
        self.assertTrue(any(row.original is original for row in result.receipts))
        self.assertEqual(self.adapter.calls[-1], "read_virtual")
        self.adapter = MockAdapter(self.bound, self.authority, self.anchor)
        text = "x" * (tool.METADATA_BYTES + 1)
        def long_failed(row): raise ValueError(text)
        self.adapter.counter_change = long_failed
        result = self.reject()
        self.assertIsNotNone(result.pending)
        self.assertEqual(result.pending.original, text)
        self.assertEqual(result.original_failures[0].message, text)
        self.assertEqual(result.report()["pending_ram_error_bytes"], len(text))
        self.assertLess(len(result.report_json), tool.REPORT_RESERVE_BYTES)

    def test_type_coercion_and_generic_passing_observer_are_rejected(self):
        self.reject(authority=asdict(self.authority)); self.assertFalse(self.adapter.calls)
        self.adapter.counter_change = lambda row: {"passed": True, **asdict(row)}
        self.reject()
        sample = tool.QpcSample(self.anchor.epoch_id, self.anchor.frequency_hz, self.anchor.held_start_tick, 1, 0, 1, 0)
        for cls, changes, row in ((tool.ReadResult, dict(hresult=True), tool.ReadResult(0, 0, b"")),
                                 (tool.Pointer64Result, dict(hresult="1"), tool.Pointer64Result(1)),
                                 (tool.BreakpointCountResult, dict(count=True), tool.BreakpointCountResult(0, 0)),
                                 (tool.QpcSample, dict(tick=True), sample)):
            with self.subTest(cls=cls.__name__), self.assertRaises(ValueError): replace(row, **changes)

    def test_public_synthetic_or_legacy_admission_uses_no_adapter_methods(self):
        result = tool.collect_loader_reads(self.bound.candidate, self.bound, self.authority, self.anchor, self.adapter)
        self.assertFalse(result.report()["supplied_receipt_collection_passed"])
        self.assertFalse(self.adapter.calls)
        self.assertFalse(result.receipts)
        for field in tool.FALSE_CLAIMS: self.assertIs(result.report()[field], False)
        with self.assertRaises(ValueError): tool.prepare_read_plan(self.bound.candidate, self.bound)
        for forged in (tool.PreparedReadPlan("{}"), {"binding_json": "{}", "passed": True}):
            result = tool.collect_prepared_reads(forged, self.authority, self.anchor, self.adapter)
            self.assertFalse(result.report()["supplied_receipt_collection_passed"])
            self.assertFalse(self.adapter.calls)

    def test_budget_is_additive_full_raw_and_metadata_atomic_peak(self):
        expected = 16 * 1024 * 1024 + 64 * 1024 + 3 + 16 * 1024 * 1024
        self.assertEqual(tool.budget()["additional_disk_peak_bytes"], expected)
        result = self.collect()
        encoded = tool._canonical([tool._summary(row) for row in result.receipts])
        self.assertEqual(len(encoded), result.report()["metadata_bytes"])
        self.assertLess(len(encoded) + len(result.report_json), tool.METADATA_BYTES)


def original_backed():
    from src.patcher import battle_profile_context as context
    raw = image_fixture.ORIGINAL.read_bytes()
    before = hashlib.sha256(raw).hexdigest()
    source_before = (hashlib.sha256((ROOT / tool.SOURCE).read_bytes()).hexdigest(), hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    parent = context.build_parent_context(raw, "classic", "1024x768")
    bound = oracle.prepare_contract(raw, "classic", "1024x768", candidate=parent.candidate,
                                   metadata=parent.parent_metadata(), canonical_probe=parent.canonical_probe.encode())
    authority = image_fixture.authority(bound)
    anchor = tool.QpcAnchor(authority.clock_epoch, 1_000_000, 1000, authority.clock_origin_ns, 1001)
    authority = replace(authority, checkpoint_start_ns=tool.project(anchor, anchor.held_start_tick).lower_ns)
    adapter = MockAdapter(bound, authority, anchor)
    def poison(*args, **kwargs): raise AssertionError("public producer alias became authority")
    with patch.object(tool, "_collect", poison), patch.object(oracle, "_derive_plan", poison), patch.object(oracle, "_compare", poison):
        result = tool.collect_loader_reads(raw, bound, authority, anchor, adapter)
    assert result.report()["supplied_receipt_collection_passed"], result.report()
    assert all(result.report()[name] is False for name in tool.FALSE_CLAIMS)
    # Preparation is usable before a target generation/held epoch exists. A
    # capability clone or readable self-sealed binding does not inherit issuer.
    prepared = tool.prepare_read_plan(raw, bound)
    for forged in (tool.PreparedReadPlan(prepared.binding_json), replace(prepared), {"binding_json": prepared.binding_json}):
        adapter = MockAdapter(bound, authority, anchor)
        rejected = tool.collect_prepared_reads(forged, authority, anchor, adapter)
        assert not rejected.report()["supplied_receipt_collection_passed"] and not adapter.calls
    adapter = MockAdapter(bound, authority, anchor)
    with patch.object(context, "build_parent_context", poison), patch.object(context, "authenticate_parent", poison), \
         patch.object(tool, "_prepare_execution", poison), patch.object(tool, "_collect", poison):
        result = tool.collect_prepared_reads(prepared, authority, anchor, adapter)
    assert result.report()["supplied_receipt_collection_passed"], result.report()
    assert all(result.report()[name] is False for name in tool.FALSE_CLAIMS)
    actual_read = Path.read_bytes
    def changed_source(path):
        data = actual_read(path)
        return data + b"\n# changed after source issuance\n" if path == ROOT / tool.ORACLE else data
    adapter = MockAdapter(bound, authority, anchor)
    with patch.object(Path, "read_bytes", changed_source):
        rejected = tool.collect_prepared_reads(prepared, authority, anchor, adapter)
    assert not rejected.report()["supplied_receipt_collection_passed"] and not adapter.calls
    object.__setattr__(prepared, "binding_json", "{}")
    adapter = MockAdapter(bound, authority, anchor)
    assert not tool.collect_prepared_reads(prepared, authority, anchor, adapter).report()["supplied_receipt_collection_passed"]
    assert not adapter.calls
    assert hashlib.sha256(image_fixture.ORIGINAL.read_bytes()).hexdigest() == before == image_fixture.ORIGINAL_SHA
    assert source_before == (hashlib.sha256((ROOT / tool.SOURCE).read_bytes()).hexdigest(), hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    print("original-backed Classic1024 mocked collection PASS; native/source issuance and acceptance false", flush=True)


if __name__ == "__main__":
    requested = "--original-backed" in sys.argv
    if requested: sys.argv.remove("--original-backed")
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReadSessionTests))
    if not result.wasSuccessful(): raise SystemExit(1)
    if requested: original_backed()
