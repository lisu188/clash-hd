"""Focused synthetic recorder dispatch/retention fixtures; never native APIs.

Full model journals stay in RAM. Tiny literal temporary files test publication
identity separately. No Original, candidate, game, owner, approval or capture is
used. Every model diagnostic keeps all fourteen authority flags false.
"""
from __future__ import annotations

import ast
from collections import Counter
import contextlib
from dataclasses import FrozenInstanceError, replace
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import complete_hd_paused_surface_recorder_v2 as recorder


def uint(value, size=4):
    return value.to_bytes(size, "little")


class Model(recorder.SyntheticAdapter):
    """Every packet here is explicitly invented; no real process exists."""
    def __init__(self, *, resolution="800x600", bool_bits=1):
        self.events, self.outputs = [], []
        self.clock, self.bool_bits = 1000, bool_bits
        self.transform = None
        self.width, self.height = map(int, resolution.split("x"))
        self.identity = dict(process_id=1234, creation_filetime=134000000000000000, handle=456)
        self.state = dict(tid=17, eip=0x406FA1, esp=0x120000, selected_stack=3, panel_stack=3, lower=1,
            owner=0x40AD40, surface=0x220000, base=0x300000, width=self.width, height=self.height, vtable=0x50EE24)
        self.commands = b"synthetic fixture only\n.echo SHSEL_HOST_READY\n"
        self.binding = dict(profile="Complete HD", stage="gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-validation",
            recipe="complete_hd_v1", representation="complete_hd_selected_stack3_physical_e0_v1",
            phase="controlled_selected_stack3_redraw_stopped", resolution=resolution, candidate_sha256="a" * 64,
            original_sha256="b" * 64, probe_sha256=recorder.sha(self.commands), producer_sha256="c" * 64)
        self.prefix = (b"synthetic source trace\nSHSEL_READY tid=11 eip=00406fa1 esp=00120000 selected=3 prior=3 "
            b"lower=1 owner=0040ad40 surface=00220000 base=00300000 width=" + str(self.width).encode() +
            b" height=" + str(self.height).encode() + b" vtable=0050ee24\nSHSEL_HOST_READY\n")
        self.header = bytearray(188)
        struct.pack_into("<HHI", self.header, 0, self.width, self.height, self.state["base"])
        struct.pack_into("<I", self.header, 184, 0x50EE24)
        self.pixels = (bytes(range(256)) * ((self.width * self.height + 255) // 256))[:self.width * self.height]

    def plan(self, **changes):
        values = dict(binding=self.binding, identity=self.identity, state=self.state,
                      commands=self.commands, prefix=self.prefix, final=self.prefix)
        values.update(changes)
        return recorder.prepare_synthetic_plan(**values)

    def invoke(self, operation, arguments):
        self.events.append((operation, arguments))
        error = uint(71)  # Successful calls may leave an unrelated stale error.
        if operation == "QueryPerformanceCounter":
            self.clock += 1
            output = recorder.Output(uint(self.bool_bits), error, (uint(self.clock, 8),))
        elif operation == "QueryPerformanceFrequency":
            output = recorder.Output(uint(self.bool_bits), error, (uint(10000000, 8),))
        elif operation == "GetProcessId":
            output = recorder.Output(uint(self.identity["process_id"]), error)
        elif operation == "GetProcessTimes":
            output = recorder.Output(uint(self.bool_bits), error, (
                struct.pack("<QQQQ", self.identity["creation_filetime"], 0xFFFFFFFFFFFFFFFF, self.clock, self.clock),))
        elif operation == "WaitForSingleObject":
            output = recorder.Output(uint(258), error)
        elif operation == "ReadProcessMemory":
            handle, address, count = arguments
            if address == 0x5202E0:
                data = uint(self.state["surface"])
            elif address == self.state["surface"]:
                data = bytes(self.header)
            elif address == self.state["base"]:
                data = self.pixels
            else:
                data = next(uint(expected) for _, native_address, expected in recorder.STATE if address == native_address)
            assert handle == self.identity["handle"] and len(data) == count
            output = recorder.Output(uint(self.bool_bits), error, (uint(count, 8), data))
        else:
            raise AssertionError("unknown source-selected operation " + operation)
        if self.transform:
            output = self.transform(operation, arguments, output, len(self.events))
        self.outputs.append(output)
        return output

    def collect(self):
        return recorder.Recorder(self.plan(), self).collect()


class RecorderTests(unittest.TestCase):
    def assert_false(self, result):
        for name in recorder.AUTHORITY_FLAGS:
            self.assertIs(result.diagnostic[name], False, name)
        self.assertEqual(json.loads(result.retention_bytes)["evidence_class"], "synthetic_fixture")
        self.assertTrue(all(value is False for value in json.loads(result.retention_bytes)["authority"].values()))

    def test_fixed_dispatch_builds_replayable_three_cohort_protocol(self):
        model = Model()
        result = model.collect()
        self.assert_false(result)
        self.assertTrue(result.diagnostic["input_cohort_consistent"])
        self.assertFalse(result.failures)
        self.assertFalse(result.missing)
        journal = json.loads(result.journal_bytes)
        self.assertEqual(journal["evidence_class"], "synthetic_fixture")
        self.assertEqual(journal["completion"], {"status": "complete", "failures": [], "missing_originals": []})
        self.assertEqual(len(model.events), 432)
        self.assertEqual(Counter(name for name, _ in model.events), {
            "QueryPerformanceFrequency": 1, "QueryPerformanceCounter": 158,
            "GetProcessId": 78, "GetProcessTimes": 78, "WaitForSingleObject": 78, "ReadProcessMemory": 39})
        expected_pattern = ("GetProcessId", "GetProcessTimes", "WaitForSingleObject", "QueryPerformanceCounter",
            "QueryPerformanceCounter", "ReadProcessMemory", "QueryPerformanceCounter",
            "GetProcessId", "GetProcessTimes", "WaitForSingleObject", "QueryPerformanceCounter")
        self.assertEqual([row[0] for row in model.events[:2]], ["QueryPerformanceFrequency", "QueryPerformanceCounter"])
        for index in range(39):
            self.assertEqual(tuple(row[0] for row in model.events[2 + index * 11:2 + (index + 1) * 11]), expected_pattern)
        reads = [read for cohort in journal["cohorts"] for read in cohort["reads"]]
        self.assertEqual([read["ordinal"] for read in reads], list(range(1, 40)))
        self.assertEqual([read["role"] for read in reads], list(recorder.READ_ROLES) * 3)
        expected = [(0x511B58, 4), (0x514194, 4), (0x526994, 4), (0x5199D8, 4),
            (0x5202E0, 4), (model.state["surface"], 188), (model.state["base"], 800 * 600),
            (0x5202E0, 4), (model.state["surface"], 188),
            (0x511B58, 4), (0x514194, 4), (0x526994, 4), (0x5199D8, 4)]
        self.assertEqual([(read["address"], read["requested"]) for read in reads], expected * 3)
        self.assertEqual(len(result.originals), 1183)
        self.assertEqual(sum(len(row.data) for row in result.originals if row.role not in
            ("commands", "debugger_prefix", "debugger_final", "journal")), 3 * 800 * 600 + 8784)
        sidecar = json.loads(result.retention_bytes)
        self.assertEqual(len(sidecar["calls"]), 432)
        self.assertEqual(sidecar["originals"], [dict(row.reference(), role=row.role) for row in result.originals])
        self.assertEqual([call.ordinal for call in result.calls], list(range(1, 433)))
        self.assertTrue(all(call.output is output for call, output in zip(result.calls, model.outputs)))

    def test_nonzero_bool_original_bits_and_undefined_live_exit_are_retained(self):
        for value in (2, 0xFFFFFFFF):
            with self.subTest(value=value):
                result = Model(bool_bits=value).collect()
                self.assertTrue(result.diagnostic["input_cohort_consistent"])
                self.assert_false(result)
                bool_calls = [call for call in result.calls if call.operation not in ("GetProcessId", "WaitForSingleObject")]
                self.assertTrue(all(call.output.result == uint(value) for call in bool_calls))
                times = [call.output.buffers[0] for call in result.calls if call.operation == "GetProcessTimes"]
                self.assertEqual(len(times), 78)
                self.assertTrue(all(struct.unpack("<QQQQ", row)[1] == 0xFFFFFFFFFFFFFFFF for row in times))

    def test_zero_bool_apis_fail_without_invented_later_observations(self):
        for api in ("QueryPerformanceFrequency", "QueryPerformanceCounter", "GetProcessTimes", "ReadProcessMemory"):
            with self.subTest(api=api):
                model = Model()
                def transform(name, args, packet, sequence):
                    return replace(packet, result=uint(0)) if name == api else packet
                model.transform = transform
                result = model.collect()
                self.assert_false(result)
                self.assertFalse(result.diagnostic["input_cohort_consistent"])
                self.assertTrue(result.failures)
                self.assertTrue(result.missing)
                self.assertLess(len(result.calls), 432)
                self.assertTrue(any(call.operation == api and call.output.result == uint(0) for call in result.calls))
                self.assertEqual(json.loads(result.journal_bytes)["completion"]["status"], "failed")

    def test_pid_creation_and_dead_or_failed_wait_reject_before_rpm(self):
        variants = (("GetProcessId", lambda packet: replace(packet, result=uint(999))),
            ("GetProcessTimes", lambda packet: replace(packet, buffers=(struct.pack("<QQQQ", 1, 0, 0, 0),))),
            ("WaitForSingleObject", lambda packet: replace(packet, result=uint(0))),
            ("WaitForSingleObject", lambda packet: replace(packet, result=uint(0xFFFFFFFF))))
        for api, mutation in variants:
            with self.subTest(api=api):
                model = Model()
                model.transform = lambda name, args, packet, seq: mutation(packet) if name == api else packet
                result = model.collect()
                self.assert_false(result)
                self.assertTrue(result.failures)
                self.assertNotIn("ReadProcessMemory", [name for name, _ in model.events])
                self.assertTrue(any(call.operation == api for call in result.calls))

    def test_partial_rpm_keeps_entire_capacity_and_actual_count_before_failure(self):
        model = Model()
        def transform(name, args, packet, sequence):
            if name == "ReadProcessMemory" and args[1] == model.state["base"]:
                data = b"\xA5" * 17 + b"\xCC" * (args[2] - 17)
                return recorder.Output(uint(0), uint(299), (uint(17, 8), data))
            return packet
        model.transform = transform
        result = model.collect()
        self.assert_false(result)
        call = next(call for call in result.calls if call.operation == "ReadProcessMemory" and call.arguments[1] == model.state["base"])
        self.assertEqual(len(call.output.buffers[1]), 800 * 600)
        self.assertEqual(call.output.buffers[1][-32:], b"\xCC" * 32)
        refs = next(row["originals"] for row in json.loads(result.retention_bytes)["calls"] if row["ordinal"] == call.ordinal)
        originals = {row.path: row.data for row in result.originals}
        self.assertEqual(originals[refs["buffer1"]["path"]], call.output.buffers[1])
        self.assertEqual(originals[refs["buffer0"]["path"]], uint(17, 8))
        self.assertTrue(result.failures)
        # Post-read identity is actual model dispatch, but no next read is invented.
        self.assertEqual([name for name, _ in model.events][-5:],
            ["QueryPerformanceCounter", "GetProcessId", "GetProcessTimes", "WaitForSingleObject", "QueryPerformanceCounter"])

    def test_short_or_extra_count_and_wrong_buffer_capacity_retain_originals(self):
        for count, length in ((3, 4), (5, 4), (4, 3), (4, 5)):
            with self.subTest(count=count, length=length):
                model = Model()
                model.transform = lambda name, args, packet, seq: recorder.Output(uint(1), uint(0),
                    (uint(count, 8), b"\xAA" * length)) if name == "ReadProcessMemory" else packet
                result = model.collect()
                self.assert_false(result)
                self.assertTrue(result.failures)
                packet = next(call.output for call in result.calls if call.operation == "ReadProcessMemory")
                self.assertEqual(packet.buffers, (uint(count, 8), b"\xAA" * length))
                self.assertTrue(any(row.data == b"\xAA" * length for row in result.originals))

    def test_exception_with_partial_packet_is_retained_and_original_cause_survives(self):
        model = Model()
        packet = recorder.Output(uint(0), uint(5), (uint(0, 8), b"\xFE" * 4))
        def transform(name, args, output, sequence):
            if name == "ReadProcessMemory":
                raise recorder.SyntheticCallFailure("modeled native call raised", packet)
            return output
        model.transform = transform
        result = model.collect()
        self.assert_false(result)
        self.assertIs(result.calls[-1].output, packet)
        self.assertEqual(result.calls[-1].original_exception.args, ("modeled native call raised",))
        self.assertIn("exception text unavailable", result.calls[-1].exception)
        self.assertTrue(any(row.data == b"\xFE" * 4 for row in result.originals))
        self.assertTrue(any(error is result.calls[-1].original_exception for error in result.exceptions))

    def test_absent_outputs_are_explicit_debt_and_never_zero_filled(self):
        for packet in (None, recorder.Output(None, uint(5), (None,)), recorder.Output(b"\x01", uint(0), (uint(1, 8),))):
            with self.subTest(packet=packet):
                model = Model()
                model.transform = lambda name, args, output, seq: packet if name == "QueryPerformanceFrequency" else output
                result = model.collect()
                self.assert_false(result)
                self.assertTrue(result.failures)
                self.assertTrue(result.missing)
                self.assertIs(result.calls[0].output, packet)
                self.assertEqual(len(result.calls), 1)
                self.assertFalse(any(row.role == "frequency.buffer0" and row.data == b"\0" * 8 for row in result.originals))

    def test_qpc_and_cpu_reversals_fail_original_replay(self):
        for target in ("clock", "cpu"):
            with self.subTest(target=target):
                model = Model()
                def transform(name, args, packet, sequence):
                    if target == "clock" and name == "QueryPerformanceCounter" and sequence > 20:
                        return replace(packet, buffers=(uint(1, 8),))
                    if target == "cpu" and name == "GetProcessTimes" and sequence > 20:
                        return replace(packet, buffers=(struct.pack("<QQQQ", model.identity["creation_filetime"], 7, 0, 0),))
                    return packet
                model.transform = transform
                result = model.collect()
                self.assert_false(result)
                self.assertFalse(result.diagnostic["input_cohort_consistent"])
                self.assertTrue(result.diagnostic["failures"])
                self.assertEqual(len(result.calls), 432)

    def test_e0_all_header_bytes_and_three_full_frames_are_checked(self):
        for kind in ("e0", "header_unused_byte", "frame"):
            with self.subTest(kind=kind):
                model = Model()
                seen = 0
                def transform(name, args, packet, sequence):
                    nonlocal seen
                    if name == "ReadProcessMemory":
                        if (kind == "e0" and args[1] == 0x5202E0) or (kind == "header_unused_byte" and args[1] == model.state["surface"]) or (kind == "frame" and args[1] == model.state["base"]):
                            seen += 1
                            if seen == 2:
                                data = bytearray(packet.buffers[1])
                                data[100 if kind == "header_unused_byte" else 0] ^= 1
                                return replace(packet, buffers=(packet.buffers[0], bytes(data)))
                    return packet
                model.transform = transform
                result = model.collect()
                self.assert_false(result)
                self.assertEqual(len(result.calls), 432)
                self.assertFalse(result.diagnostic["input_cohort_consistent"])
                self.assertTrue(result.diagnostic["failures"])

    def test_supplied_state_mutation_cannot_change_fixed_read_addresses(self):
        model = Model()
        plan = model.plan()
        model.state["base"] += 0x100000
        # Adapter no longer provides the prepared address: failure remains honest.
        result = recorder.Recorder(plan, model).collect()
        self.assert_false(result)
        rpm = [call for call in result.calls if call.operation == "ReadProcessMemory"]
        self.assertEqual(rpm[-1].arguments[1], 0x300000)
        self.assertTrue(result.failures)

    def test_plan_is_immutable_and_forged_plan_rejects_before_dispatch(self):
        model = Model()
        plan = model.plan()
        with self.assertRaises(FrozenInstanceError):
            plan.wire = b"{}"
        model.binding["candidate_sha256"] = "d" * 64
        self.assertEqual(json.loads(plan.wire)["binding"]["candidate_sha256"], "a" * 64)
        with self.assertRaises(ValueError):
            recorder.Recorder(replace(plan, wire=b'{"binding": {}}'), model)
        self.assertFalse(model.events)

    def test_scope_parser_flags_and_old_packets_cannot_select_execution(self):
        model = Model()
        for field, value in (("profile", "Modal Widgets"), ("recipe", "framed_v1"),
                             ("representation", "MCAP"), ("phase", "ordinary_map"), ("passed", True), ("parser", "arbitrary")):
            with self.subTest(field=field):
                binding = dict(model.binding, **{field: value})
                with self.assertRaises(ValueError):
                    model.plan(binding=binding)
        for name, value in (("selected_stack", 2), ("panel_stack", 0), ("eip", 1), ("width", 99999), ("previous_stack", 3)):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    model.plan(state=dict(model.state, **{name: value}))
        self.assertFalse(model.events)

    def test_stopped_log_cleanup_tail_changed_probe_and_marker_order_reject(self):
        model = Model()
        for changes in (dict(final=model.prefix + b"actual cleanup tail\n"), dict(prefix=model.prefix + b"resume\n"),
                        dict(commands=b"different commands"), dict(prefix=model.prefix.replace(b"SHSEL_HOST_READY", b"HOST_READY")),
                        dict(prefix=model.prefix.replace(b"selected=3 prior=3", b"selected=3 prior=2"))):
            with self.subTest(changes=tuple(changes)):
                with self.assertRaises(ValueError):
                    model.plan(**changes)
        self.assertFalse(model.events)

    def test_report_public_alias_and_source_substitution_do_not_choose_helper(self):
        class Poison:
            def __getattr__(self, name):
                raise AssertionError("public module alias used")
        with patch.dict(sys.modules, {"paused_surface_triple_replay": Poison()}):
            result = Model().collect()
        self.assertTrue(result.diagnostic["input_cohort_consistent"])
        self.assert_false(result)
        model = Model()
        with patch.object(recorder, "HELPER_SHA256", "0" * 64):
            with self.assertRaisesRegex(ValueError, "frozen"):
                model.plan()
        self.assertFalse(model.events)

    def test_single_use_and_output_abi_call_capacity_are_fail_closed(self):
        model = Model()
        instance = recorder.Recorder(model.plan(), model)
        self.assertTrue(instance.collect().diagnostic["input_cohort_consistent"])
        with self.assertRaisesRegex(ValueError, "single-use"):
            instance.collect()
        model = Model()
        instance = recorder.Recorder(model.plan(), model)
        with self.assertRaises(ValueError):
            instance._call("arbitrary API", (), "bad", ())
        with self.assertRaises(ValueError):
            instance._call("GetProcessId", (456,), "bad", (8,))
        self.assertFalse(model.events)
        with patch.object(recorder, "MAX_CALLS", 1):
            result = model.collect()
        self.assertEqual(len(result.calls), 1)
        self.assertTrue(result.failures)
        self.assert_false(result)

    def test_original_namespace_immutable_unique_references_and_capacity(self):
        store = recorder.RAMOriginals()
        first, second = store.put("first", b"same"), store.put("second", b"same")
        self.assertNotEqual(first["path"], second["path"])
        frozen = store.freeze()
        self.assertEqual(frozen.reference(first, "a"), b"same")
        self.assertEqual(frozen.reference(second, "b"), b"same")
        with self.assertRaises(ValueError):
            frozen.reference(first, "duplicate")
        with self.assertRaises(TypeError):
            frozen.values[first["path"]] = None
        with self.assertRaises(ValueError):
            store.put("first", b"replacement")
        with patch.object(recorder, "MAX_RAM", 8):
            with self.assertRaises(ValueError):
                store.put("third", b"x")
        frozen.unchanged()

    def test_retention_failure_adopts_packet_before_any_semantic_check(self):
        model = Model()
        instance = recorder.Recorder(model.plan(), model)
        original_put = instance.originals.put
        def fail(role, data):
            if role == "frequency.buffer0":
                raise ValueError("modeled retention failure")
            return original_put(role, data)
        with patch.object(instance.originals, "put", side_effect=fail):
            result = instance.collect()
        self.assert_false(result)
        self.assertIs(result.calls[0].output, model.outputs[0])
        self.assertEqual(result.calls[0].output.buffers[0], uint(10000000, 8))
        self.assertTrue(any("originals retention failed" in row for row in result.failures))
        self.assertTrue(any(type(error) is ValueError and error.args == ("modeled retention failure",) for error in result.exceptions))
        self.assertTrue(any("pending packet" in row for row in result.missing))

    def test_final_serialization_failure_retains_exact_packets_and_original_cause(self):
        model = Model()
        instance = recorder.Recorder(model.plan(), model)
        original_canonical = recorder.canonical
        cause = ValueError("modeled final serialization failure")
        def serialization(value):
            if value.get("schema") == "clash95_paused_surface_triple_native_journal_v1":
                raise cause
            return original_canonical(value)
        with patch.object(recorder, "canonical", side_effect=serialization):
            with self.assertRaises(recorder.RecordingFailure) as caught:
                instance.collect()
        self.assertIs(caught.exception.original_cause, cause)
        self.assertEqual(len(caught.exception.calls), 432)
        self.assertEqual(len(caught.exception.originals), 1182)
        self.assertTrue(all(call.output is output for call, output in zip(caught.exception.calls, model.outputs)))
        self.assertEqual(len(caught.exception.packet_references), 432)

    def test_malformed_buffer_tuple_or_iterable_is_bounded_and_full_packet_retained(self):
        class UntrustedIterable:
            def __iter__(self):
                raise AssertionError("untrusted iterable must not be traversed")
            def __len__(self):
                raise AssertionError("untrusted iterable must not be counted")
        third = b"unexpected original remains owned"
        buffers = (uint(10000000, 8), b"second raw original", third)
        for supplied in (buffers, UntrustedIterable()):
            with self.subTest(tuple_shape=type(supplied) is tuple):
                model = Model()
                packet = recorder.Output(uint(1), uint(71), supplied)
                model.transform = lambda name, args, output, seq: packet if name == "QueryPerformanceFrequency" else output
                result = model.collect()
                self.assert_false(result)
                self.assertEqual(len(result.calls), 1)
                self.assertIs(result.calls[0].output, packet)
                self.assertIs(result.calls[0].output.buffers, supplied)
                self.assertTrue(result.failures)
                self.assertTrue(any("complete original packet retained" in row for row in result.missing))
                self.assertEqual(json.loads(result.journal_bytes)["completion"]["status"], "failed")
                refs = json.loads(result.retention_bytes)["calls"][0]["originals"]
                self.assertNotIn("buffer2", refs)
                self.assertIn("return", refs)
                self.assertIn("error", refs)
                if type(supplied) is tuple:
                    self.assertIn("buffer0", refs)
                    self.assertIn("buffer1", refs)
                    self.assertIs(result.calls[0].output.buffers[2], third)
                else:
                    self.assertEqual(set(refs), {"return", "error"})

    def test_helper_final_source_drift_stays_failed_with_all_outputs_retained(self):
        model = Model()
        instance = recorder.Recorder(model.plan(), model)
        with patch.object(recorder, "_helper", side_effect=ValueError("modeled source drift")):
            result = instance.collect()
        self.assert_false(result)
        self.assertEqual(len(result.calls), 432)
        self.assertEqual(len(result.originals), 1183)
        self.assertFalse(result.diagnostic["input_cohort_consistent"])
        self.assertTrue(any("helper final rehash" in row for row in result.failures))
        self.assertTrue(any(type(error) is ValueError and error.args == ("modeled source drift",) for error in result.exceptions))

    def test_hostile_exception_string_methods_never_run_and_partial_output_survives(self):
        model = Model()
        packet = recorder.Output(uint(0), uint(299), (uint(0, 8), b"\xFE" * 4))
        error = recorder.SyntheticCallFailure("unrendered original message", packet)
        def transform(name, args, output, sequence):
            if name == "ReadProcessMemory":
                raise error
            return output
        model.transform = transform
        with patch.object(recorder.SyntheticCallFailure, "__str__", side_effect=AssertionError("custom str invoked")) as custom_str, \
             patch.object(recorder.SyntheticCallFailure, "__repr__", side_effect=AssertionError("custom repr invoked")) as custom_repr:
            result = model.collect()
            self.assertIs(result.calls[-1].original_exception, error)
            self.assertIs(result.calls[-1].output, packet)
            self.assertTrue(any(item is error for item in result.exceptions))
            self.assertTrue(any(row.data == b"\xFE" * 4 for row in result.originals))
            self.assertTrue(any("exception text unavailable" in debt for debt in result.missing))
            self.assertEqual(json.loads(result.journal_bytes)["completion"]["status"], "failed")
            custom_str.assert_not_called()
            custom_repr.assert_not_called()
            self.assert_false(result)

    def test_manifest_hard_cap_failure_retains_all_originals_and_exact_cause(self):
        model = Model()
        instance = recorder.Recorder(model.plan(), model)
        with patch.object(recorder, "MAX_MANIFEST", 1):
            with self.assertRaises(recorder.RecordingFailure) as caught:
                instance.collect()
        self.assertEqual(len(caught.exception.calls), 432)
        self.assertEqual(len(caught.exception.originals), 1183)
        self.assertIsInstance(caught.exception.original_cause, ValueError)
        self.assertIn("manifest hard capacity", str(caught.exception.original_cause))
        self.assertEqual(len(caught.exception.packet_references), 432)
        self.assertTrue(all(call.output is output for call, output in zip(caught.exception.calls, model.outputs)))


class BudgetPublicationTests(unittest.TestCase):
    def test_all_geometry_budgets_are_arithmetic_only_and_no_runtime_admission(self):
        resolutions = ("800x600", "1024x768", "1280x720", "1280x960", "1366x768", "1920x1080",
                       "2560x1440", "3440x1440", "3840x2160", "802x602")
        for resolution in resolutions:
            budget = recorder.retention_budget(resolution, external_bytes=1234)
            width, height = map(int, resolution.split("x"))
            self.assertEqual(budget["native_bytes"], 3 * width * height + 8784)
            self.assertEqual(budget["native_originals"], 1179)
            self.assertEqual(budget["total_originals"], 1183)
            self.assertEqual(budget["total_archive_files"], 1185)
            self.assertEqual(budget["manifest_cap"], 64 * 1024)
            self.assertEqual(budget["allocation_slack"], 1185 * (4096 - 1))
            self.assertEqual(budget["content_cap"], budget["native_bytes"] + recorder.MAX_COMMAND +
                2 * recorder.MAX_LOG + recorder.MAX_JOURNAL + recorder.MAX_RETENTION + recorder.MAX_MANIFEST)
            self.assertEqual(budget["required_peak"], budget["content_cap"] + budget["atomic_temporary"] + budget["allocation_slack"] + 1234)
            self.assertFalse(budget["runtime_budget_complete"])
            self.assertFalse(budget["runtime_assets_counted"])
            self.assertFalse(budget["native_provenance_verified"])
        for changes in (dict(allocation_unit=True), dict(allocation_unit=0), dict(external_bytes=-1)):
            with self.assertRaises(ValueError):
                recorder.retention_budget("800x600", **changes)
        self.assertEqual(recorder.retention_budget("1920x1080")["native_bytes"], 6229584)
        self.assertEqual(recorder.retention_budget("3840x2160")["native_bytes"], 24891984)

    def test_strict_reserve_rejects_equality_shortfall_invalid_and_next_write_debt(self):
        recorder.require_reserve(101, 1000, 0)
        recorder.require_reserve(201, 1000, 100)
        for values in ((100, 1000, 0), (200, 1000, 100), (99, 1000, 0), (201, 1000, 101),
                       (True, 1000, 0), (1001, 1000, 0), (101, 0, 0), (101, 1000, -1)):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    recorder.require_reserve(*values)

    def test_tiny_publication_is_atomic_unique_bounded_and_finally_rehashed(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-recorder-") as parent:
            publisher = recorder.TinySyntheticPublisher(Path(parent) / "owned", free=10**9, total=2 * 10**9)
            first, second = publisher.put(b"same"), publisher.put(b"same")
            self.assertNotEqual(first["path"], second["path"])
            self.assertNotEqual(Path(first["path"]).stat().st_ino, Path(second["path"]).stat().st_ino)
            self.assertFalse(list(publisher.directory.glob("*.pending")))
            self.assertEqual(publisher.pending, [b"same", b"same"])
            publisher.unchanged()
            Path(first["path"]).write_bytes(b"evil")
            with self.assertRaises(ValueError):
                publisher.unchanged()

    def test_existing_destination_or_atomic_failure_keeps_pending_and_is_sticky(self):
        for mode in ("existing", "link_failure"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix="synthetic-paused-recorder-") as parent:
                publisher = recorder.TinySyntheticPublisher(Path(parent) / "owned", free=10**9, total=2 * 10**9)
                target = publisher.directory / "0001.bin"
                if mode == "existing":
                    target.write_bytes(b"foreign")
                    with self.assertRaises(OSError):
                        publisher.put(b"ours")
                    self.assertEqual(target.read_bytes(), b"foreign")
                else:
                    with patch.object(recorder.os, "link", side_effect=OSError("modeled publication failure")):
                        with self.assertRaises(OSError):
                            publisher.put(b"ours")
                self.assertEqual((publisher.directory / "0001.bin.pending").read_bytes(), b"ours")
                self.assertEqual(publisher.pending, [b"ours"])
                self.assertTrue(publisher.failures)
                with self.assertRaises(ValueError):
                    publisher.put(b"retry cannot clear failure")
                with self.assertRaises(ValueError):
                    publisher.unchanged()

    def test_publication_growth_reparse_identity_and_count_limits_reject(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-recorder-") as parent:
            publisher = recorder.TinySyntheticPublisher(Path(parent) / "owned", free=10**9, total=2 * 10**9)
            reference = publisher.put(b"tiny")
            path = Path(reference["path"])
            # Replacing the original with a new file of identical bytes still rejects.
            renamed = path.with_suffix(".retained")
            path.rename(renamed)
            path.write_bytes(b"tiny")
            with self.assertRaises(ValueError):
                publisher.unchanged()
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-recorder-") as parent:
            publisher = recorder.TinySyntheticPublisher(Path(parent) / "owned", free=10**9, total=2 * 10**9, allowance=8)
            with self.assertRaises(ValueError):
                publisher.put(b"123456789")
            self.assertEqual(publisher.pending, [b"123456789"])
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-recorder-") as parent:
            publisher = recorder.TinySyntheticPublisher(Path(parent) / "owned", free=10**9, total=2 * 10**9)
            with patch.object(recorder, "MAX_TINY_FILES", 1):
                publisher.put(b"")
                with self.assertRaises(ValueError):
                    publisher.put(b"")
            self.assertEqual(len(publisher.rows), 1)
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-recorder-") as parent:
            publisher = recorder.TinySyntheticPublisher(Path(parent) / "owned", free=10**9, total=2 * 10**9)
            reference = publisher.put(b"tiny")
            target = Path(reference["path"])
            original_open = Path.open
            def grow(path, mode="r", *args, **kwargs):
                if path == target and mode == "rb":
                    with original_open(path, "ab") as output:
                        output.write(b"growth")
                return original_open(path, mode, *args, **kwargs)
            with patch.object(Path, "open", grow), self.assertRaises(ValueError):
                publisher.unchanged()
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-recorder-") as parent:
            publisher = recorder.TinySyntheticPublisher(Path(parent) / "owned", free=10**9, total=2 * 10**9)
            original_lstat = Path.lstat
            def reparse(path, *args, **kwargs):
                info = original_lstat(path, *args, **kwargs)
                if path == publisher.directory:
                    return SimpleNamespace(st_file_attributes=0x400, st_mode=info.st_mode)
                return info
            with patch.object(Path, "lstat", reparse), self.assertRaises(ValueError):
                publisher.put(b"preserve before path rejection")
            self.assertEqual(publisher.pending, [b"preserve before path rejection"])
            self.assertFalse(publisher.rows)

    def test_final_hardlink_alias_and_new_directory_collision_reject(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-recorder-") as parent:
            directory = Path(parent) / "owned"
            publisher = recorder.TinySyntheticPublisher(directory, free=10**9, total=2 * 10**9)
            reference = publisher.put(b"tiny")
            os.link(reference["path"], directory / "foreign-alias")
            with self.assertRaises(ValueError):
                publisher.unchanged()
            with self.assertRaises(ValueError):
                recorder.TinySyntheticPublisher(directory, free=10**9, total=2 * 10**9)

    def test_created_identity_binds_ordinary_and_normalized_publication_paths(self):
        for normalized in (False, True):
            with self.subTest(normalized=normalized), tempfile.TemporaryDirectory(prefix="synthetic-paused-recorder-") as parent:
                helper, source, stamp = recorder._helper()
                checked = helper.checked_path
                ordinary = Path(parent) / "owned"
                expected = Path(parent).resolve(strict=True) / "owned"
                directory = ordinary
                modeled = []
                normalization_class = "ordinary_literal_path"
                if normalized and os.name == "posix":
                    directory = Path("//" + str(Path(parent)).lstrip("/")) / "owned"
                    self.assertNotEqual(directory, expected)
                    normalization_class = "posix_double_leading_slash"
                elif normalized:
                    # This is a synthetic spelling model, not a Windows alias
                    # observation: move only the just-created tiny directory,
                    # retaining its actual identity under the new spelling.
                    expected = Path(parent).resolve(strict=True) / "normalized-owned"
                    normalization_class = "synthetic_created_directory_spelling_model"
                    def normalize(value):
                        canonical = checked(value)
                        if Path(value) == ordinary:
                            resolved_root = Path(parent).resolve(strict=True)
                            original_target = ordinary.resolve(strict=True)
                            expected_parent = expected.parent.resolve(strict=True)
                            expected_target = expected_parent / expected.name
                            self.assertTrue(resolved_root.is_absolute())
                            self.assertEqual(canonical, original_target)
                            self.assertTrue(original_target.is_absolute())
                            self.assertTrue(original_target.is_relative_to(resolved_root))
                            self.assertTrue(expected_target.is_absolute())
                            self.assertTrue(expected_target.is_relative_to(resolved_root))
                            self.assertEqual(original_target.parent, expected_parent)
                            self.assertEqual(original_target, resolved_root / "owned")
                            self.assertEqual(expected_target, resolved_root / "normalized-owned")
                            self.assertEqual(expected, expected_target)
                            self.assertFalse(expected_target.exists())
                            self.assertTrue(original_target.is_dir())
                            self.assertFalse(list(original_target.iterdir()))
                            before = ordinary.lstat()
                            ordinary.rename(expected)
                            modeled.append((before.st_dev, before.st_ino))
                            return checked(str(expected))
                        return canonical
                    helper.checked_path = normalize
                with patch.object(recorder, "_helper", return_value=(helper, source, stamp)):
                    publisher = recorder.TinySyntheticPublisher(directory, free=10**9, total=2 * 10**9)
                    self.assertEqual(publisher.directory, expected)
                    info = expected.lstat()
                    self.assertEqual(publisher.directory_identity, (info.st_dev, info.st_ino))
                    if modeled:
                        self.assertEqual(modeled, [publisher.directory_identity])
                    else:
                        self.assertTrue(os.path.samefile(directory, publisher.directory))
                    reference = publisher.put(b"canonical tiny original")
                    target = Path(reference["path"])
                    self.assertEqual(target.parent, publisher.directory)
                    self.assertEqual(target, checked(str(target)))
                    self.assertEqual(target.read_bytes(), b"canonical tiny original")
                    self.assertEqual(publisher.pending, [b"canonical tiny original"])
                    publisher.unchanged()
                    self.assertFalse(publisher.failures)
                    self.assertFalse(publisher.original_exceptions)
                print(json.dumps(dict(publication_path_case=normalization_class,
                    synthetic_only=True, windows_alias_observed=False,
                    native_provenance_verified=False, runtime_acceptance=False)), flush=True)

    def test_canonical_directory_substitution_and_post_admission_failure_retain_originals(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-recorder-") as parent:
            helper, source, stamp = recorder._helper()
            checked = helper.checked_path
            foreign = Path(parent) / "foreign"
            foreign.mkdir()
            directory = Path(parent) / "owned"
            def substitute(value):
                canonical = checked(value)
                return checked(str(foreign)) if Path(value) == directory else canonical
            helper.checked_path = substitute
            with patch.object(recorder, "_helper", return_value=(helper, source, stamp)):
                with self.assertRaisesRegex(ValueError, "canonical directory identity"):
                    recorder.TinySyntheticPublisher(directory, free=10**9, total=2 * 10**9)
            self.assertTrue(directory.is_dir())
            self.assertFalse(os.path.samefile(directory, foreign))
        with tempfile.TemporaryDirectory(prefix="synthetic-paused-recorder-") as parent:
            publisher = recorder.TinySyntheticPublisher(Path(parent) / "owned", free=10**9, total=2 * 10**9)
            foreign = Path(parent) / "foreign"
            foreign.mkdir()
            actual_lstat = Path.lstat
            def replace_identity(value, *args, **kwargs):
                return actual_lstat(foreign) if value == publisher.directory else actual_lstat(value, *args, **kwargs)
            original = b"preserve before directory identity rejection"
            with patch.object(Path, "lstat", replace_identity), self.assertRaisesRegex(ValueError, "directory identity changed") as caught:
                publisher.put(original)
            self.assertEqual(publisher.pending, [original])
            self.assertIs(publisher.original_exceptions[-1], caught.exception)
            self.assertFalse(publisher.rows)
            self.assertTrue(publisher.failures)
            self.assertFalse(list(publisher.directory.iterdir()))
            with self.assertRaisesRegex(ValueError, "sticky"):
                publisher.unchanged()

    def test_real_owner_execute_cli_and_registry_stay_unavailable_without_side_effects(self):
        for call in (recorder.native_owner_factory, recorder.execute):
            with self.assertRaises(recorder.SourceOnlyError):
                call(approved=True, report={"passed": True, "handle": 456})
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            recorder.main(["--execute"])
        self.assertEqual(caught.exception.code, 2)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(recorder.main([]), 0)
        value = json.loads(output.getvalue())
        self.assertTrue(value["synthetic_only"])
        self.assertFalse(value["native_execution_available"])
        self.assertFalse(value["native_owner_factory_available"])
        self.assertFalse(value["production_verifier_registered"])
        self.assertTrue(all(value[name] is False for name in recorder.AUTHORITY_FLAGS))
        source = Path(recorder.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        self.assertFalse(any(name in ("ctypes", "subprocess", "owned_hidden_process", "hidden_soak_job_native") for name in imports))
        self.assertEqual(recorder.HELPER_SHA256, "60fbb1b8392b302b4366e0acaec7bd659705daf8c856df6a2818a5e5b0690dcb")


if __name__ == "__main__":
    unittest.main(verbosity=2)
