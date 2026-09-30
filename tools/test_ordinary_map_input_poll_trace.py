"""Portable synthetic log fixtures; these are not game/runtime observations."""
from copy import deepcopy
import json
import unittest

import ordinary_map_input_poll_trace as trace


IDENTITY = dict(pid=101, tid=102, creation_filetime=133700000000000000,
                image_base=0x400000, controller_sha256="a" * 64, session_id="b" * 32)
ROOT = 0x100000
LOCAL = bytes.fromhex("feffffff030000001100000080408012").hex()


def common(kind, epoch=1, identity=None, *, action_index=None, root=ROOT):
    return dict(schema=trace.SCHEMA, kind=kind, epoch=epoch,
                action_index=epoch - 1 if action_index is None else action_index,
                **(identity or IDENTITY), root_esp=root)


def poll_records(poll=1, *, epoch=1, identity=None, caller=0x460A61, hresult=0,
                 pre="00" * 16, post=LOCAL, local=LOCAL, action_index=None, root=ROOT):
    identity = identity or IDENTITY
    delta = identity["image_base"] - 0x400000
    raw = bytes.fromhex(local)
    frame = root - 0x180
    call = dict(common("call", epoch, identity, action_index=action_index, root=root),
                poll=poll, caller=caller + delta,
                call_esp=frame - 12, frame_esp=frame, entry_esp=frame + 0x6C,
                backend=0x545198 + delta, device=0x70001000, vtable=0x70002000,
                method=0x70003001, buffer=frame + 0x50, pre_hex=pre)
    returned = dict(common("return", epoch, identity, action_index=action_index, root=root),
                    poll=poll, return_esp=frame,
                    hresult=hresult, post_hex=post)
    copied = dict(common("copy", epoch, identity, action_index=action_index, root=root),
                  poll=poll, copy_esp=frame, local_hex=local,
                  backend_x=int.from_bytes(raw[:4], "little"), backend_y=int.from_bytes(raw[4:8], "little"),
                  primary=raw[12], secondary=raw[13], middle=raw[14],
                  resolved=0, raw_x=0xFFFFFFFF, raw_y=0x80000000)
    return [call, returned, copied]


def epoch_records(epoch=1, *, polls=1, identity=None, action_index=None, root=ROOT, **kwargs):
    rows = [dict(common("start", epoch, identity, action_index=action_index, root=root),
                 startup_retired=True, deadline_tick_ms=987654321)]
    for poll in range(1, polls + 1):
        rows.extend(poll_records(poll, epoch=epoch, identity=identity,
                                 action_index=action_index, root=root, **kwargs))
    rows.append(dict(common("end", epoch, identity, action_index=action_index, root=root),
                     polls=polls, pending=False,
                     retired_before_hold=True, reason="caller_hold"))
    return rows


def log(rows):
    return "debugger unrelated output\n" + "\n".join(
        trace.MARKER + " " + json.dumps(row, separators=(",", ":")) for row in rows) + "\n"


class PollTraceTests(unittest.TestCase):
    def parse(self, rows, identity=IDENTITY):
        return trace.parse_trace(log(rows), identity)

    def reject(self, rows, contains=None):
        report = self.parse(rows)
        self.assertFalse(report["complete"])
        self.assertTrue(report["errors"])
        if contains:
            self.assertTrue(any(contains in value for value in report["errors"]), report["errors"])
        return report

    def test_complete_sequence_has_diagnostic_coverage_only(self):
        report = self.parse(epoch_records())
        self.assertTrue(report["complete"], report["errors"])
        self.assertEqual(report["completed_epochs"], 1)
        self.assertEqual(report["completed_polls"], 1)
        self.assertEqual(report["hresults"], {"0x00000000": 1})
        self.assertTrue(report["return_observations"][0]["paired"])
        for key in ("os_input_executed", "os_input_proof", "manual_input_proof",
                    "gameplay_verified", "gameplay_proof", "promotion_ready"):
            self.assertIs(report[key], False)
        self.assertEqual(report["scope"], "native_mouse_poll_diagnostic_only")

    def test_all_rebased_native_callers_and_multiple_epochs(self):
        identity = dict(IDENTITY, image_base=0x500000)
        rows = []
        for epoch, caller in enumerate(trace.CALLERS, 1):
            rows.extend(epoch_records(epoch, identity=identity, caller=caller))
        report = self.parse(rows, identity)
        self.assertTrue(report["complete"], report["errors"])
        self.assertEqual(report["completed_epochs"], 3)

    def test_64_polls_are_allowed(self):
        report = self.parse(epoch_records(polls=64))
        self.assertTrue(report["complete"], report["errors"])
        self.assertEqual(report["completed_polls"], 64)

    def test_65th_poll_rejected(self):
        self.reject(epoch_records(polls=65), "poll")

    def test_failed_hresult_and_unchanged_buffer_retained(self):
        for value in (0x80070005, 0x8007001E, 0xFFFFFFFF):
            with self.subTest(hresult=value):
                report = self.parse(epoch_records(hresult=value, pre=LOCAL))
                self.assertTrue(report["complete"], report["errors"])
                self.assertEqual(report["failed_hresult_count"], 1)
                self.assertEqual(report["completed_failed_hresult_count"], 1)
                self.assertEqual(report["failed_hresult_with_unchanged_buffer_count"], 1)
                self.assertEqual(report["polls"][0]["returned"]["hresult"], value)
                self.assertFalse(report["gameplay_verified"])

    def test_success_hresult_high_bit_only(self):
        report = self.parse(epoch_records(hresult=0x7FFFFFFF))
        self.assertTrue(report["complete"])
        self.assertEqual(report["failed_hresult_count"], 0)

    def test_acquire_can_change_local_after_saved_hresult(self):
        report = self.parse(epoch_records(hresult=0x8007001E, post="00" * 16))
        self.assertTrue(report["complete"], report["errors"])
        self.assertEqual(report["local_changed_after_return_count"], 1)
        self.assertEqual(report["polls"][0]["returned"]["hresult"], 0x8007001E)
        self.assertTrue(report["polls"][0]["local_changed_after_return"])

    def test_failed_return_still_counted_without_copy_or_end(self):
        report = self.reject(epoch_records(hresult=0x8007001E)[:3], "unpaired")
        self.assertEqual(report["failed_hresult_count"], 1)
        self.assertEqual(report["completed_failed_hresult_count"], 0)
        self.assertEqual(report["hresults"], {"0x8007001e": 1})

    def test_unpaired_failed_return_retained_as_unpaired(self):
        report = self.reject([poll_records(hresult=0x80070005)[1]], "no active epoch")
        self.assertEqual(report["failed_hresult_count"], 1)
        self.assertFalse(report["return_observations"][0]["paired"])

    def test_missing_end_and_truncated_sequences_fail(self):
        for length in range(1, 5):
            with self.subTest(length=length):
                self.reject(epoch_records()[:length])

    def test_empty_trace_and_empty_epoch_fail(self):
        self.assertFalse(trace.parse_trace("no trace", IDENTITY)["complete"])
        self.reject(epoch_records(polls=0), "no observed mouse-poll coverage")

    def test_duplicate_and_out_of_order_events_fail(self):
        original = epoch_records()
        for index in range(5):
            with self.subTest(duplicate=index):
                rows = deepcopy(original)
                rows.insert(index + 1, rows[index])
                self.reject(rows)
        for left, right in ((0, 1), (1, 2), (2, 3), (3, 4)):
            with self.subTest(swap=(left, right)):
                rows = deepcopy(original)
                rows[left], rows[right] = rows[right], rows[left]
                self.reject(rows)

    def test_poll_index_changes_or_skips_fail(self):
        for index in (1, 2, 3):
            rows = epoch_records()
            rows[index]["poll"] = 2
            self.reject(rows, "poll")

    def test_epoch_action_and_root_must_match_owner(self):
        for index in range(5):
            for key in ("epoch", "action_index", "root_esp"):
                with self.subTest(index=index, key=key):
                    rows = epoch_records()
                    rows[index][key] += 4 if key == "root_esp" else 1
                    self.reject(rows)

    def test_stale_or_skipped_later_epochs_fail(self):
        for epoch in (1, 3):
            self.reject(epoch_records() + epoch_records(epoch), "epoch sequence")

    def test_release_and_reacquire_keep_same_action_and_can_measure_new_root(self):
        rows = (epoch_records() + epoch_records(2, action_index=0, root=ROOT+0x1000) +
                epoch_records(3, action_index=1, root=ROOT+0x1000) +
                epoch_records(4, action_index=1, root=ROOT+0x2000))
        report = self.parse(rows)
        self.assertTrue(report["complete"], report["errors"])
        self.assertEqual(report["completed_epochs"], 4)
        self.assertEqual([row["action_index"] for row in report["epochs"]], [0, 0, 1, 1])
        self.assertEqual([row["root_esp"] for row in report["epochs"]],
                         [ROOT, ROOT+0x1000, ROOT+0x1000, ROOT+0x2000])
        self.assertEqual(report["polls"][1]["call"]["frame_esp"], ROOT+0x1000-0x180)

    def test_first_action_must_be_zero_and_later_actions_cannot_skip_or_decrease(self):
        self.reject(epoch_records(action_index=1), "action sequence")
        self.reject(epoch_records() + epoch_records(2, action_index=2), "action sequence")
        self.reject(epoch_records() + epoch_records(2, action_index=1) +
                    epoch_records(3, action_index=0), "action sequence")
        self.reject(epoch_records() + epoch_records(2, action_index=0) +
                    epoch_records(3, action_index=2), "action sequence")

    def test_direct_post_action_epoch_must_retain_previous_root(self):
        self.reject(epoch_records() + epoch_records(2, action_index=1, root=ROOT+0x1000),
                    "post-action epoch changed")
        # Once a clean same-action reacquisition replaces the root, the next
        # post-action epoch must bind to that newly observed frame.
        rows = epoch_records() + epoch_records(2, action_index=0, root=ROOT+0x1000)
        self.reject(rows + epoch_records(3, action_index=1), "post-action epoch changed")

    def test_new_root_or_action_cannot_replace_active_epoch_owner(self):
        rows = epoch_records() + epoch_records(2, action_index=0, root=ROOT+0x1000)
        for key in ("root_esp", "action_index"):
            with self.subTest(key=key):
                defective = deepcopy(rows)
                defective[7][key] += 4 if key == "root_esp" else 1
                self.reject(defective, "differs from active trace owner")

    def test_reacquire_cannot_enter_before_current_epoch_end_or_pending_poll_completion(self):
        first = epoch_records()
        for length in (2, 3, 4):
            with self.subTest(prefix_length=length):
                # A new root cannot hide a pending CALL/return or an omitted
                # end record, even when the new epoch/action would be valid.
                rows = first[:length] + epoch_records(2, action_index=0, root=ROOT+0x1000)
                report = self.reject(rows, "overlapping poll epoch")
                self.assertEqual(report["completed_epochs"], 0)

    def test_all_identity_fields_bound_on_every_event(self):
        for index in range(5):
            for key in trace.IDENTITY_KEYS:
                with self.subTest(index=index, key=key):
                    rows = epoch_records()
                    value = rows[index][key]
                    rows[index][key] = "c" * len(value) if type(value) is str else value + 1
                    self.reject(rows, "identity differs")

    def test_invalid_expected_identity_fails_closed(self):
        for key, value in (("pid", True), ("tid", 0), ("creation_filetime", 1 << 64),
                           ("image_base", 0x410001), ("image_base", 0x7FFD0000),
                           ("controller_sha256", "A" * 64), ("session_id", "z" * 32)):
            identity = dict(IDENTITY, **{key: value})
            with self.subTest(key=key, value=value):
                report = trace.parse_trace(log(epoch_records()), identity)
                self.assertFalse(report["complete"])
                self.assertTrue(report["errors"])
        for identity in (None, {}, dict(IDENTITY, unknown=1)):
            self.assertFalse(trace.parse_trace("", identity)["complete"])

    def test_missing_and_unknown_keys_or_schema_fail(self):
        for index in range(5):
            rows = epoch_records()
            rows[index]["unknown"] = 1
            self.reject(rows, "keys differ")
            rows = epoch_records()
            del rows[index]["pid"]
            self.reject(rows, "keys differ")
        rows = epoch_records()
        rows[1]["schema"] = trace.SCHEMA + "_wrong"
        self.reject(rows, "schema differs")

    def test_noncanonical_json_or_malformed_marker_fail(self):
        valid = log(epoch_records())
        lines = valid.splitlines()
        cases = [valid.replace('"poll":1', '"poll":1.0', 1),
                 valid.replace('"poll":1', '"poll":true', 1),
                 valid.replace('"kind":"start"', '"kind":"\\u0073tart"', 1),
                 valid.replace(trace.MARKER + " ", trace.MARKER + "  ", 1),
                 valid.replace(trace.MARKER + " ", "prefix " + trace.MARKER + " ", 1),
                 valid.replace(trace.MARKER + " ", trace.MARKER, 1),
                 valid.replace('"kind":"start"', '"kind":"start","kind":"start"', 1),
                 valid.replace('"epoch":1', '"epoch":NaN', 1),
                 "\n".join(lines[:1] + [trace.MARKER + " {}"] + lines[2:]),
                 trace.MARKER + ' {"kind":"start"',
                 trace.MARKER + " " + "x" * 4097]
        for text in cases:
            with self.subTest(text=text[:80]):
                report = trace.parse_trace(text, IDENTITY)
                self.assertFalse(report["complete"])
                self.assertTrue(report["errors"])

    def test_integer_bounds_and_bool_aliases_fail(self):
        fields = ((0, "epoch"), (0, "action_index"), (0, "deadline_tick_ms"),
                  (1, "poll"), (2, "hresult"), (3, "backend_x"), (3, "resolved"), (4, "polls"))
        for index, key in fields:
            for value in (True, -1, 1 << 64):
                with self.subTest(index=index, key=key, value=value):
                    rows = epoch_records()
                    rows[index][key] = value
                    self.reject(rows, "integer")
        for key in ("hresult",):
            rows = epoch_records()
            rows[2][key] = 1 << 32
            self.reject(rows, "integer")

    def test_buffer_hex_must_be_exact_lowercase_16_bytes(self):
        for index, key in ((1, "pre_hex"), (2, "post_hex"), (3, "local_hex")):
            for value in (LOCAL.upper(), LOCAL[:-1], LOCAL + "00", "z" * 32, 0):
                with self.subTest(key=key, value=value):
                    rows = epoch_records()
                    rows[index][key] = value
                    self.reject(rows, "hexadecimal")

    def test_call_stack_arithmetic_and_bounds_fail(self):
        for key in ("call_esp", "frame_esp", "entry_esp", "buffer"):
            rows = epoch_records()
            rows[1][key] += 4
            self.reject(rows, "stack arithmetic")
        for frame in (ROOT - 0x4100, ROOT - 0x40):
            rows = epoch_records()
            rows[1].update(frame_esp=frame, call_esp=frame - 12,
                           entry_esp=frame + 0x6C, buffer=frame + 0x50)
            self.reject(rows, "escapes")

    def test_call_backend_caller_and_pointer_guards_fail(self):
        for key, value in (("backend", 0x54519C), ("caller", 0x460A62),
                           ("device", 0), ("vtable", 0x70002001),
                           ("vtable", trace.HIGH_PTR - 4), ("method", 0xDEADBEEF)):
            rows = epoch_records()
            rows[1][key] = value
            self.reject(rows)

    def test_device_vtable_method_cannot_change_within_epoch(self):
        for key in ("device", "vtable", "method"):
            with self.subTest(key=key):
                rows = epoch_records(polls=2)
                rows[4][key] += 4
                self.reject(rows, "changed within the epoch")

    def test_new_epoch_can_measure_new_mouse_interface(self):
        rows = epoch_records() + epoch_records(2)
        for key in ("device", "vtable", "method"):
            rows[6][key] += 4
        report = self.parse(rows)
        self.assertTrue(report["complete"], report["errors"])
        self.assertNotEqual(report["epochs"][0]["mouse_interface"], report["epochs"][1]["mouse_interface"])

    def test_return_and_copy_must_restore_exact_frame(self):
        for index, key in ((2, "return_esp"), (3, "copy_esp")):
            rows = epoch_records()
            rows[index][key] += 4
            self.reject(rows, "stack differs")

    def test_all_five_backend_copy_values_must_match_local(self):
        for key in ("backend_x", "backend_y", "primary", "middle", "secondary"):
            rows = epoch_records()
            rows[3][key] ^= 1
            self.reject(rows, "five copied backend words")

    def test_primary_middle_secondary_are_zero_extended_byte_copies(self):
        report = self.parse(epoch_records())
        copied = report["polls"][0]["copy"]
        self.assertEqual((copied["primary"], copied["middle"], copied["secondary"]), (128, 128, 64))
        rows = epoch_records()
        rows[3]["primary"] |= 0x100
        self.reject(rows, "five copied backend words")

    def test_resolved_and_raw_are_independent_uint32_snapshots(self):
        rows = epoch_records()
        rows[3].update(resolved=0xFFFFFFFF, raw_x=0, raw_y=0xFFFFFFFF)
        self.assertTrue(self.parse(rows)["complete"])

    def test_end_counts_and_retirement_disclosure_are_exact(self):
        for key, value in (("polls", 0), ("pending", True), ("pending", 0),
                           ("retired_before_hold", False), ("retired_before_hold", 1),
                           ("reason", "timeout")):
            rows = epoch_records()
            rows[4][key] = value
            self.reject(rows)
        for value in (False, 1):
            rows = epoch_records()
            rows[0]["startup_retired"] = value
            self.reject(rows, "startup retirement")

    def test_rejected_record_cannot_resynchronize_to_green(self):
        rows = epoch_records()
        rows[2]["return_esp"] += 4
        rows.extend(epoch_records(2))
        report = self.reject(rows)
        self.assertEqual(report["completed_epochs"], 0)
        self.assertTrue(any("continues after a rejected record" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
