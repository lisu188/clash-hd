"""Portable artificial activation logs; none are game or device evidence."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from unittest import mock
import unittest

import ordinary_map_activation_trace as trace


IDENTITY = dict(pid=101, tid=102, creation_filetime=133700000000000000,
                image_base=0x400000, controller_sha256="a" * 64, session_id="b" * 32)
FRAME = 0x100000
START_TICK, DEADLINE = 1000, 101000


def common(kind, tx=0, *, tick=START_TICK, identity=None, retired=False):
    return dict(schema=trace.SCHEMA, kind=kind, tx=tx, **(identity or IDENTITY),
                tick_ms=tick, startup_retired=retired)


def transaction_records(tx=1, *, tick=1001, identity=None, frame=FRAME,
                        wparam=1, mouse_ready=1, keyboard_ready=1, retired=False,
                        mouse_hresult=0x80070005, keyboard_hresult=1):
    identity = identity or IDENTITY
    delta = identity["image_base"] - trace.NATIVE_BASE
    args = dict(hwnd=0x10024, message=0x1C, wparam=wparam, wparam_low16=wparam & 0xFFFF,
                lparam=0xF00DCAFE, entry_esp=frame + 16, wndproc_return=0x70004003)
    rows = [dict(common("activation", tx, tick=tick, identity=identity, retired=retired),
                 **args, branch_esp=frame, deadline_tick_ms=min(DEADLINE, tick + trace.TRANSACTION_MS))]

    def row(kind, **values):
        rows.append(dict(common(kind, tx, tick=tick + len(rows), identity=identity, retired=retired), **values))

    operation = {0: "unacquire", 1: "acquire"}.get(wparam & 0xFFFF)
    if operation:
        outer_pair = trace.OUTER[operation]
        row("outer_call", operation=operation, call_va=outer_pair[0] + delta,
            return_va=outer_pair[1] + delta, call_esp=frame, backend=trace.BACKEND + delta,
            mouse_ready=mouse_ready, keyboard_ready=keyboard_ready, joystick_ready=0)
        final_eax = trace.BACKEND + delta
        for name, ready, hresult, offset in (("mouse", mouse_ready, mouse_hresult, 0),
                                            ("keyboard", keyboard_ready, keyboard_hresult, 0x10000)):
            if ready:
                pair = trace.DEVICE[operation][name]
                row("device_call", device_kind=name, call_va=pair[0] + delta,
                    return_va=pair[1] + delta, call_esp=frame - 20,
                    device=0x70001000 + offset, vtable=0x70002000 + offset, method=0x70003001 + offset)
                row("device_return", device_kind=name, return_va=pair[1] + delta,
                    return_esp=frame - 16, hresult=hresult)
                final_eax = hresult
        row("outer_return", return_va=outer_pair[1] + delta, return_esp=frame, eax=final_eax)
    row("end", **args, epilogue_va=trace.EPILOGUE + delta, epilogue_esp=frame + 16)
    return rows


def records(transactions=1, *, identity=None, **kwargs):
    identity = identity or IDENTITY
    rows = [dict(common("start", identity=identity), initial_stop_armed=True,
                 host_start_tick_ms=START_TICK, deadline_tick_ms=DEADLINE,
                 max_transactions=trace.MAX_TRANSACTIONS)]
    for tx in range(1, transactions + 1):
        rows.extend(transaction_records(tx, tick=1001 + (tx - 1) * 20, identity=identity, **kwargs))
    rows.append(dict(common("finish", tick=rows[-1]["tick_ms"] + 1, identity=identity,
                            retired=kwargs.get("retired", False)),
                     transactions=transactions, pending=False,
                     reason="transaction_cap" if transactions == trace.MAX_TRANSACTIONS else "host_interval"))
    return rows


def log(rows):
    return "unrelated debugger output\n" + "\n".join(
        trace.MARKER + " " + json.dumps(row, separators=(",", ":")) for row in rows) + "\n"


class ActivationTraceTests(unittest.TestCase):
    def parse(self, rows, identity=IDENTITY):
        return trace.parse_trace(log(rows), identity)

    def reject(self, rows, contains=None):
        result = self.parse(rows)
        self.assertFalse(result["complete"])
        self.assertTrue(result["errors"])
        if contains:
            self.assertTrue(any(contains in error for error in result["errors"]), result["errors"])
        return result

    def test_paired_results_are_diagnostic_only_and_not_callback_return(self):
        result = self.parse(records())
        self.assertTrue(result["complete"], result["errors"])
        self.assertEqual(result["scope"], "native_activation_diagnostic_only")
        self.assertEqual(result["completed_transactions"], 1)
        self.assertEqual(result["observed_device_returns"], 2)
        self.assertEqual(result["paired_device_returns"], 2)
        self.assertEqual(result["completed_device_returns"], 2)
        self.assertTrue(result["device_hresult_coverage"])
        self.assertTrue(result["initial_stop_armed"])
        self.assertTrue(result["clean_finish"])
        self.assertTrue(result["transactions"][0]["epilogue_observed"])
        for key in ("all_activation_events_observed", "callback_return_observed", "startup_acquisition_executed",
                    "os_input_executed", "os_input_proof", "manual_input_proof", "gameplay_verified",
                    "gameplay_proof", "promotion_ready"):
            self.assertIs(result[key], False)
        self.assertIs(result["transactions"][0]["callback_return_observed"], False)

    def test_pre_retirement_acquire_and_post_retirement_unacquire(self):
        rows = records()[:-1]
        rows.extend(transaction_records(2, tick=1020, wparam=0, retired=True))
        rows.append(dict(common("finish", tick=1030, retired=True), transactions=2,
                         pending=False, reason="host_interval"))
        result = self.parse(rows)
        self.assertTrue(result["complete"], result["errors"])
        self.assertEqual([item["operation"] for item in result["transactions"]], ["acquire", "unacquire"])
        self.assertFalse(result["transactions"][0]["activation"]["startup_retired"])
        self.assertTrue(result["transactions"][1]["activation"]["startup_retired"])

    def test_retirement_can_occur_during_transaction_but_never_revert(self):
        rows = records()
        for row in rows[4:]:
            row["startup_retired"] = True
        self.assertTrue(self.parse(rows)["complete"])
        rows[7]["startup_retired"] = False
        self.reject(rows, "retirement flag reverted")

    def test_acquire_and_unacquire_rebase_all_native_pairs(self):
        identity = dict(IDENTITY, image_base=0x600000)
        for wparam in (0, 1):
            with self.subTest(wparam=wparam):
                result = self.parse(records(identity=identity, wparam=wparam), identity)
                self.assertTrue(result["complete"], result["errors"])

    def test_actual_mouse_then_keyboard_order_and_independent_hresult(self):
        result = self.parse(records(mouse_hresult=0x8007000C, keyboard_hresult=0x7FFFFFFF))
        self.assertTrue(result["complete"], result["errors"])
        devices = result["transactions"][0]["devices"]
        self.assertEqual([item["call"]["device_kind"] for item in devices], ["mouse", "keyboard"])
        self.assertEqual([item["returned"]["hresult"] for item in devices], [0x8007000C, 0x7FFFFFFF])
        self.assertEqual(result["failed_hresult_count"], 1)
        self.assertEqual(result["completed_failed_hresult_count"], 1)
        self.assertEqual(result["transactions"][0]["outer_return"]["eax"], 0x7FFFFFFF)

    def test_failed_hresult_is_unsigned_and_preserved_for_each_device(self):
        for value in (0x80070005, 0x8007001E, 0xFFFFFFFF):
            with self.subTest(hresult=value):
                result = self.parse(records(mouse_hresult=value, keyboard_hresult=value))
                self.assertTrue(result["complete"], result["errors"])
                self.assertEqual(result["failed_hresult_count"], 2)
                self.assertEqual(result["paired_failed_hresult_count"], 2)
                self.assertEqual(result["hresults"], {f"0x{value:08x}": 2})

    def test_ready_flags_skip_disabled_devices_without_inferring_acquisition(self):
        for mouse, keyboard in ((0, 0), (1, 0), (0, 1), (0xFFFFFFFF, 2)):
            with self.subTest(mouse=mouse, keyboard=keyboard):
                result = self.parse(records(mouse_ready=mouse, keyboard_ready=keyboard))
                self.assertTrue(result["complete"], result["errors"])
                self.assertEqual(result["completed_device_returns"], int(bool(mouse)) + int(bool(keyboard)))
                self.assertEqual(result["device_hresult_coverage"], bool(mouse or keyboard))
                self.assertFalse(result["os_input_proof"])
        result = self.parse(records(mouse_ready=0, keyboard_ready=0))
        self.assertEqual(result["transactions"][0]["skipped_devices"], ["mouse", "keyboard"])
        self.assertEqual(result["transactions"][0]["outer_return"]["eax"], trace.BACKEND)

    def test_lowword_controls_native_operation_and_other_values_skip_backend(self):
        for wparam, operation in ((0xABCD0000, "unacquire"), (0xF00D0001, "acquire"),
                                  (2, None), (0xFFFFFFFF, None)):
            with self.subTest(wparam=wparam):
                result = self.parse(records(wparam=wparam))
                self.assertTrue(result["complete"], result["errors"])
                item = result["transactions"][0]
                self.assertEqual(item["operation"], operation)
                self.assertEqual(item["activation"]["wparam"], wparam)
                if operation is None:
                    self.assertNotIn("outer_call", item)
                    self.assertEqual(result["completed_device_returns"], 0)

    def test_zero_events_and_empty_log_never_complete(self):
        result = self.reject(records(transactions=0), "no complete observed")
        self.assertTrue(result["clean_finish"])
        self.assertFalse(result["device_hresult_coverage"])
        result = trace.parse_trace("no activation trace", IDENTITY)
        self.assertFalse(result["complete"])
        self.assertIn("no native activation trace records", result["errors"])

    def test_missing_finish_and_each_truncated_stage_are_incomplete(self):
        rows = records()
        for length in range(1, len(rows)):
            with self.subTest(length=length):
                self.reject(rows[:length], "without a clean observer finish")
        for index in range(1, len(rows) - 1):
            with self.subTest(missing=index):
                self.reject(rows[:index] + rows[index + 1:])

    def test_saved_hresult_retained_when_later_epilogue_or_finish_missing(self):
        for length in (5, 8, 9):
            with self.subTest(length=length):
                result = self.reject(records()[:length])
                self.assertEqual(result["return_observations"][0]["record"]["hresult"], 0x80070005)
                self.assertTrue(result["return_observations"][0]["paired"])
                self.assertEqual(result["completed_device_returns"], 2 if length == 9 else 0)
                self.assertEqual(result["return_observations"][0]["transaction_complete"], length == 9)

    def test_unpaired_authenticated_raw_return_remains_unpaired(self):
        result = self.reject([records()[4]], "no observer start")
        self.assertEqual(result["failed_hresult_count"], 1)
        self.assertEqual(result["paired_device_returns"], 0)
        self.assertFalse(result["return_observations"][0]["paired"])
        for return_va in (0x70005003, trace.DEVICE["acquire"]["keyboard"][1]):
            with self.subTest(return_va=return_va):
                row = deepcopy(records()[4])
                row["return_va"] = return_va
                result = self.reject([row], "rebased whitelist")
                self.assertEqual(result["failed_hresult_count"], 0)
                self.assertEqual(result["observed_device_returns"], 0)
                self.assertEqual(result["return_observations"], [])

    def test_wrong_identity_return_is_not_counted_as_authenticated(self):
        rows = records()
        rows[4]["pid"] += 1
        result = self.reject(rows, "identity differs")
        self.assertEqual(result["failed_hresult_count"], 0)

    def test_duplicate_records_and_reordered_legs_rejected(self):
        original = records()
        for index in range(len(original)):
            with self.subTest(duplicate=index):
                rows = deepcopy(original)
                rows.insert(index + 1, deepcopy(rows[index]))
                self.reject(rows)
        for index in range(len(original) - 1):
            with self.subTest(swap=index):
                rows = deepcopy(original)
                rows[index], rows[index + 1] = rows[index + 1], rows[index]
                self.reject(rows)

    def test_second_activation_cannot_hide_a_pending_transaction(self):
        for length in (2, 3, 4, 5, 8):
            with self.subTest(length=length):
                self.reject(records()[:length] + transaction_records(2, tick=1020), "overlapping")

    def test_skipped_stale_or_mismatched_transaction_numbers_rejected(self):
        for index in range(1, 9):
            with self.subTest(index=index):
                rows = records()
                rows[index]["tx"] = 2
                self.reject(rows)
        self.reject(records()[:-1] + transaction_records(1, tick=1020), "sequence")
        for index in (0, 9):
            rows = records()
            rows[index]["tx"] = 1
            self.reject(rows, "lifecycle")

    def test_sixteen_transactions_close_at_cap_and_seventeenth_rejected(self):
        rows = records(transactions=16)
        result = self.parse(rows)
        self.assertTrue(result["complete"], result["errors"])
        self.assertEqual(result["completed_transactions"], 16)
        self.assertEqual(result["completed_device_returns"], 32)
        self.reject(rows[:-1] + transaction_records(17, tick=1500), "cap")

    def test_clean_finish_reasons_counts_pending_and_postfinish_events(self):
        for key, value in (("transactions", 0), ("pending", True), ("reason", "timeout"),
                           ("reason", "transaction_cap"), ("reason", "host_deadline")):
            with self.subTest(key=key, value=value):
                rows = records()
                rows[-1][key] = value
                self.reject(rows)
        self.reject(records() + transaction_records(2, tick=1020), "after observer finish")
        self.reject(records()[:5] + [records()[-1]], "pending activation")

    def test_late_idle_host_deadline_finish_is_valid(self):
        rows = records()
        rows[-1].update(tick_ms=DEADLINE + 1000, reason="host_deadline")
        self.assertTrue(self.parse(rows)["complete"])
        rows[-1]["reason"] = "host_interval"
        self.reject(rows, "expired")

    def test_host_interval_is_bounded_and_transaction_deadline_exact(self):
        for duration in (9999, 180001, -1):
            rows = records()
            rows[0]["deadline_tick_ms"] = START_TICK + duration
            self.reject(rows, "interval")
        rows = records()
        rows[1]["deadline_tick_ms"] += 1
        self.reject(rows, "activation deadline")
        rows = records()
        for row in rows[1:]:
            row["tick_ms"] += trace.UINT64 - 10000 - 1001
        rows[0].update(tick_ms=trace.UINT64 - 30000, host_start_tick_ms=trace.UINT64 - 30000,
                       deadline_tick_ms=trace.UINT64)
        rows[1]["deadline_tick_ms"] = trace.UINT64
        self.reject(rows, "overflows")

    def test_transaction_deadline_clips_to_host_deadline(self):
        rows = records()[:1] + transaction_records(tick=DEADLINE - 10)
        rows.append(dict(common("finish", tick=DEADLINE, retired=False), transactions=1,
                         pending=False, reason="host_deadline"))
        self.assertEqual(rows[1]["deadline_tick_ms"], DEADLINE)
        self.assertTrue(self.parse(rows)["complete"])

    def test_actual_arm_delay_preserves_exact_ten_second_host_interval(self):
        rows = records()
        for row in rows:
            row["tick_ms"] += 4
        rows[0]["deadline_tick_ms"] = START_TICK + 10000
        rows[1]["deadline_tick_ms"] = START_TICK + 10000
        self.assertTrue(self.parse(rows)["complete"])
        for start_tick, reason in ((rows[0]["tick_ms"] + 1, "interval"), (START_TICK - 180000, "integer")):
            broken = deepcopy(rows)
            broken[0]["host_start_tick_ms"] = start_tick
            self.reject(broken, reason)

    def test_observed_events_at_or_after_deadline_and_decreasing_ticks_rejected(self):
        for index in range(1, 9):
            for tick in (DEADLINE, records()[1]["deadline_tick_ms"], START_TICK - 1):
                with self.subTest(index=index, tick=tick):
                    rows = records()
                    rows[index]["tick_ms"] = tick
                    self.reject(rows)

    def test_initial_arm_is_real_pre_go_not_bypassed_startup_calls(self):
        for key, value in (("initial_stop_armed", False), ("startup_retired", True),
                           ("max_transactions", 15), ("max_transactions", 17)):
            rows = records()
            rows[0][key] = value
            self.reject(rows)

    def test_all_identity_fields_bind_every_kind(self):
        for index in range(10):
            for key in trace.IDENTITY_KEYS:
                with self.subTest(index=index, key=key):
                    rows = records()
                    value = rows[index][key]
                    rows[index][key] = "c" * len(value) if type(value) is str else value + 1
                    self.reject(rows, "identity differs")

    def test_expected_identity_types_ranges_and_exact_keys(self):
        invalid = [None, dict(IDENTITY, extra=1), {key: value for key, value in IDENTITY.items() if key != "tid"}]
        for key, value in (("pid", True), ("tid", 0), ("creation_filetime", 1 << 64),
                           ("image_base", 0x400004), ("image_base", 0x7FFE0000),
                           ("controller_sha256", "A" * 64), ("session_id", "b" * 31)):
            invalid.append(dict(IDENTITY, **{key: value}))
        for identity in invalid:
            with self.subTest(identity=identity):
                result = trace.parse_trace(log(records()), identity)
                self.assertFalse(result["complete"])
                self.assertTrue(result["errors"])

    def test_schema_and_exact_keys_required_on_every_kind(self):
        for index in range(10):
            for mutation in ("schema", "extra", "missing"):
                with self.subTest(index=index, mutation=mutation):
                    rows = records()
                    if mutation == "schema":
                        rows[index]["schema"] = "wrong_schema"
                    elif mutation == "extra":
                        rows[index]["extra"] = 1
                    else:
                        del rows[index]["tick_ms"]
                    self.reject(rows)

    def test_scalar_types_are_exact_not_bool_float_or_negative(self):
        for index, field in ((0, "tick_ms"), (1, "wparam"), (2, "mouse_ready"),
                              (3, "call_esp"), (4, "hresult"), (7, "eax"), (9, "transactions")):
            for value in (True, 1.0, -1, 1 << 64):
                with self.subTest(index=index, field=field, value=value):
                    rows = records()
                    rows[index][field] = value
                    self.reject(rows, "integer")
        for value in (0, 1, "false", None):
            rows = records()
            rows[1]["startup_retired"] = value
            self.reject(rows, "boolean")

    def test_raw_wparam_lowword_and_message_must_match(self):
        for index in (1, 8):
            for key, value in (("message", 0x1D), ("wparam_low16", 2)):
                rows = records()
                rows[index][key] = value
                self.reject(rows, "LOWORD")

    def test_every_native_call_and_return_address_is_exact(self):
        for index, keys in ((2, ("call_va", "return_va")), (3, ("call_va", "return_va")),
                            (4, ("return_va",)), (5, ("call_va", "return_va")),
                            (6, ("return_va",)), (7, ("return_va",)), (8, ("epilogue_va",))):
            for key in keys:
                rows = records()
                rows[index][key] += 1
                self.reject(rows)
        rows = records()
        rows[2]["operation"] = "unacquire"
        self.reject(rows, "operation")

    def test_stack_pairs_arguments_and_return_owner_are_pinned(self):
        for index, key in ((1, "entry_esp"), (2, "call_esp"), (3, "call_esp"),
                            (4, "return_esp"), (5, "call_esp"), (6, "return_esp"),
                            (7, "return_esp"), (8, "epilogue_esp")):
            rows = records()
            rows[index][key] += 4
            self.reject(rows, "stack")
        for key in trace.ARGUMENT_KEYS:
            rows = records()
            rows[8][key] += 4 if key in ("entry_esp", "wndproc_return") else 1
            self.reject(rows)

    def test_bounded_wndproc_stack_and_native_backend(self):
        self.assertTrue(self.parse(records(frame=trace.LOW_PTR + 0x20))["complete"])
        for frame in (trace.LOW_PTR, trace.LOW_PTR + 20, trace.HIGH_PTR - 32):
            self.reject(records(frame=frame), "stack")
        rows = records()
        rows[2]["backend"] += 4
        self.reject(rows, "backend")

    def test_device_pointer_alignment_method_span_and_enabled_null_rejected(self):
        for key in ("device", "vtable", "method"):
            for value in (0, trace.LOW_PTR - 1, trace.HIGH_PTR):
                rows = records()
                rows[3][key] = value
                self.reject(rows, "pointer")
        for key in ("device", "vtable"):
            rows = records()
            rows[3][key] += 1
            self.reject(rows, "pointer")
        for wparam in (0, 1):
            rows = records(wparam=wparam)
            rows[3]["vtable"] = trace.HIGH_PTR - 4
            self.reject(rows, "span")

    def test_unsupported_joystick_and_wrong_native_device_order_rejected(self):
        rows = records()
        rows[2]["joystick_ready"] = 1
        self.reject(rows, "joystick")
        rows = records()
        rows[3]["device_kind"] = "keyboard"
        self.reject(rows, "device order")
        rows = records()
        rows[4]["device_kind"] = "keyboard"
        rows[4]["return_va"] = trace.DEVICE["acquire"]["keyboard"][1]
        self.reject(rows, "return identity")
        rows = records()
        rows[2]["mouse_ready"] = 0
        self.reject(rows, "device order")

    def test_outer_eax_cannot_replace_individual_device_results(self):
        rows = records()
        rows[7]["eax"] = rows[4]["hresult"]
        self.reject(rows, "outer EAX")
        rows = records(mouse_ready=0, keyboard_ready=0)
        rows[3]["eax"] = 0
        self.reject(rows, "outer EAX")

    def test_marker_canonical_encoding_duplicate_keys_and_malformed_json_rejected(self):
        original = log(records())
        cases = [original.replace(trace.MARKER + " ", "prefix " + trace.MARKER + " ", 1),
                 original.replace(trace.MARKER + " ", trace.MARKER + "\t", 1),
                 original.replace('"tx":0', '"tx":0,"tx":0', 1),
                 original.replace('"tx":0', '"tx": 0', 1),
                 original.replace('"tick_ms":1000', '"tick_ms":NaN', 1),
                 trace.MARKER + " {invalid}", trace.MARKER + " []",
                 trace.MARKER + " " + "[" * 1100 + "]" * 1100,
                 trace.MARKER + " " + "x" * 4097,
                 trace.MARKER + ' {"kind":"st\u00e4rt"}']
        for value in cases:
            with self.subTest(value=value[:100]):
                result = trace.parse_trace(value, IDENTITY)
                self.assertFalse(result["complete"])
                self.assertTrue(result["errors"])

    def test_finite_record_cap_and_nontext_log_fail_closed(self):
        result = trace.parse_trace(log(records()) * 14, IDENTITY)
        self.assertFalse(result["complete"])
        self.assertTrue(any("record cap" in error for error in result["errors"]))
        result = trace.parse_trace(b"not text", IDENTITY)
        self.assertFalse(result["complete"])
        self.assertIn("trace log must be text", result["errors"])

    def test_cli_reads_only_supplied_documents_and_returns_structural_status(self):
        for rows, status in ((records(), 0), (records(transactions=0), 1)):
            contents = {"identity.json": json.dumps(IDENTITY), "trace.log": log(rows)}
            output = io.StringIO()
            with mock.patch.object(trace.Path, "read_text", lambda path, **kwargs: contents[str(path)]), redirect_stdout(output):
                self.assertEqual(trace.main(["trace.log", "--expected-identity", "identity.json"]), status)
            result = json.loads(output.getvalue())
            self.assertEqual(result["complete"], status == 0)
            self.assertFalse(result["promotion_ready"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
