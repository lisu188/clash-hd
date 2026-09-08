#!/usr/bin/env python3
"""Offline movement-state fixtures; no game, debugger, process or capture runs."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import struct
import unittest

import framed_army_movement_state as state


ORIGINAL = Path("C:/Clash/clash95.exe")
SAVE = Path("C:/ClashTests/hd-completion/framed-screens-20260906-034725/workdir/save/0.dat")


def changed(raw, offset, value, fmt="B"):
    result = bytearray(raw)
    struct.pack_into("<"+fmt, result, offset, value)
    return bytes(result)


class RecordLayoutTests(unittest.TestCase):
    def test_signed_records_and_bounded_waypoints(self):
        raw = bytearray(725)
        struct.pack_into("<hhBB", raw, 0, -2, 99, 2, 7)
        for i in range(10):
            offset = 6+31*i
            struct.pack_into("<h", raw, offset, i if i < 8 else -1)
            raw[offset+2] = 2
            raw[offset+8:offset+12] = bytes((20+i, 100-i, i, 10+i))
        struct.pack_into("<i", raw, 316, 100)
        for i in range(100):
            struct.pack_into("<BBH", raw, 320+4*i, i, 99-i, 65535-i)
        raw[720] = 1
        decoded = state.decode_unit(bytes(raw))
        self.assertEqual((decoded["xy"], decoded["owner"], decoded["facing"], decoded["hidden"]),
                         ([-2, 99], 2, 7, 1))
        self.assertEqual(decoded["occupied_count"], 8)
        self.assertEqual(decoded["slots"][7], dict(index=7, offset=223, unit_type=7,
                         owner=2, ap=27, health=93, fatigue=7, morale=17))
        self.assertEqual(decoded["path"][-1], dict(xy=[99, 0], cumulative_cost=65436))
        for count in (-2147483648, -1, 101, 2147483647):
            with self.subTest(count=count), self.assertRaises(ValueError):
                state.decode_unit(changed(bytes(raw), 316, count, "i"))
        for bad in (None, bytearray(raw), memoryview(raw), b"", bytes(raw[:-1]), bytes(raw)+b"x"):
            with self.subTest(type=type(bad)), self.assertRaises(ValueError):
                state.decode_unit(bad)

    def test_immutable_ranges_have_exact_field_coverage(self):
        ranges = state.immutable_ranges()
        covered = [i for r in ranges for i in range(r["start"], r["end"])]
        expected = {4} | set(range(254, 316))
        for slot in range(8):
            offset = 6+31*slot
            expected.update(range(offset, offset+3))
            expected.update(range(offset+9, offset+12))
        self.assertEqual(len(covered), len(set(covered)))
        self.assertEqual(set(covered), expected)
        self.assertNotIn(5, covered)  # Facing is allowed to change during movement.
        self.assertTrue(all(6+31*i+8 not in covered for i in range(8)))


@unittest.skipUnless(ORIGINAL.is_file() and SAVE.is_file(), "requires local authenticated original/save; no runtime")
class MovementStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, cls.save = ORIGINAL.read_bytes(), SAVE.read_bytes()
        cls.unit = cls.save[147190+3*725:147190+4*725]
        cls.base = state.MovementSnapshot(cls.unit, 3, 3, 0, (0,)*10)
        preview = bytearray(cls.unit)
        struct.pack_into("<iBBHBBH", preview, 316, 2, 18, 19, 10, 17, 19, 5)
        cls.preview = replace(cls.base, record=bytes(preview))
        final = bytearray(preview)
        struct.pack_into("<hh", final, 0, 18, 19)
        struct.pack_into("<i", final, 316, 0)
        final[5] = 2
        for i in range(8):
            final[14+31*i] -= 10
        cls.settled = replace(cls.base, record=bytes(final))

    def compare(self, **changes):
        args = dict(original=self.original, save=self.save, baseline=self.base,
                    preview=self.preview, settled=self.settled, destination=(18, 19))
        args.update(changes)
        return state.compare_movement_state(**args)

    def failed(self, fragment, **changes):
        result = self.compare(**changes)
        self.assertFalse(result["passed"], result)
        self.assertFalse(result["state_deltas_passed"])
        self.assertTrue(any(fragment in f for f in result["failures"]), result["failures"])
        self.assertFalse(result["runtime_accepted"])
        return result

    def test_source_authenticated_three_phase_state_only(self):
        result = self.compare()
        self.assertTrue(result["passed"], result["failures"])
        self.assertTrue(result["original_authenticated"] and result["save_authenticated"])
        self.assertEqual(result["source"]["unit_record_sha256"],
                         "aca90ac24a1cc644145abdf6d2a40740304a684160a9c2bb93bf6847514f2c92")
        self.assertEqual(result["game_data_record_offset"], 149349)
        self.assertEqual([x["settled"] for x in result["ap_deltas"]], [16, 12, 6, 6, 6, 6, 6, 6])
        self.assertEqual(result["snapshots"]["preview"]["state"]["path"],
                         [dict(xy=[18, 19], cumulative_cost=10), dict(xy=[17, 19], cumulative_cost=5)])
        self.assertEqual(result, self.compare())
        for key in ("captured_records_bound", "native_route_proved", "runtime_accepted", "manual_input_proof",
                    "pixels_verified", "cleanup_verified", "promotion_ready"):
            self.assertIs(result[key], False)
        self.assertEqual(ORIGINAL.read_bytes(), self.original)
        self.assertEqual(SAVE.read_bytes(), self.save)

    def test_exact_source_and_save_identity_fail_closed(self):
        for raw in (None, bytearray(self.original), self.original[:-1], changed(self.original, 62483, 0)):
            self.failed("original executable", original=raw)
        for raw in (None, bytearray(self.save), self.save[:-1], changed(self.save, 0, self.save[0]^1)):
            self.failed("slot0 save", save=raw)

    def test_snapshot_context_and_immutable_input_types(self):
        for phase in state.PHASES:
            snapshot = {"baseline": self.base, "preview": self.preview, "settled": self.settled}[phase]
            for field, value in (("selected_index", 1), ("prior_index", -1), ("current_player", 1)):
                self.failed("identity differs", **{phase: replace(snapshot, **{field: value})})
            for flags in ((1,)+(0,)*9, (0,)*9, [0]*10, (False,)+(0,)*9):
                self.failed("context", **{phase: replace(snapshot, squad_flags=flags)})
            self.failed("integer", **{phase: replace(snapshot, current_player=False)})
            self.failed("MovementSnapshot", **{phase: {"record": snapshot.record}})
            self.failed("725-byte", **{phase: replace(snapshot, record=bytearray(snapshot.record))})

    def test_explicit_world_destination_and_no_queue_only_success(self):
        for target in (None, [18, 19], (True, 19), (-1, 19), (100, 19), (18, 100), (16, 19), (18,)):
            self.failed("destination required", destination=target)
        # Animation may leave path0 while XY has not reached the target.
        for xy in ((16, 19), (17, 19), (18, 20), (-1, 19), (100, 19)):
            raw = changed(changed(self.settled.record, 0, xy[0], "h"), 2, xy[1], "h")
            self.failed("destination not reached", settled=replace(self.settled, record=raw))
        self.failed("queue still active", settled=replace(self.settled,
                    record=changed(self.settled.record, 316, 1, "i")))

    def test_preview_is_nonmutating_and_has_target_queue(self):
        self.failed("coordinates changed", preview=replace(self.preview,
                    record=changed(self.preview.record, 0, 17, "h")))
        self.failed("nonempty queue", preview=replace(self.preview,
                    record=changed(self.preview.record, 316, 0, "i")))
        self.failed("stored destination", preview=replace(self.preview,
                    record=changed(self.preview.record, 320, 17)))
        self.failed("waypoint1 outside world", preview=replace(self.preview,
                    record=changed(self.preview.record, 324, 100)))
        self.failed("native capacity", preview=replace(self.preview,
                    record=changed(self.preview.record, 316, -1, "i")))
        self.failed("initial XY/empty queue", baseline=replace(self.base,
                    record=changed(self.base.record, 316, 1, "i")))
        for i in range(8):
            offset = 14+31*i
            self.failed(f"slot{i} AP changed", preview=replace(self.preview,
                        record=changed(self.preview.record, offset, self.preview.record[offset]-1)))
            self.failed(f"slot{i} AP differs from save", baseline=replace(self.base,
                        record=changed(self.unit, offset, self.unit[offset]-1)))

    def test_every_named_invariant_and_empty_byte_is_preserved(self):
        for phase, snapshot in (("baseline", self.base), ("preview", self.preview), ("settled", self.settled)):
            for span in state.immutable_ranges():
                # Every byte is exercised, including unsigned health/fatigue/morale
                # and all metadata bytes of the two empty slots, not just -1 types.
                for offset in range(span["start"], span["end"]):
                    with self.subTest(phase=phase, offset=offset):
                        self.failed("changed "+span["purpose"], **{phase: replace(snapshot,
                            record=changed(snapshot.record, offset, snapshot.record[offset]^1))})
        self.failed("hidden state", settled=replace(self.settled,
                    record=changed(self.settled.record, 720, 1)))

    def test_each_slot_ap_never_increases_without_inventing_cost(self):
        for i in range(8):
            offset = 14+31*i
            self.failed(f"slot{i} AP increased", settled=replace(self.settled,
                        record=changed(self.settled.record, offset, self.unit[offset]+1)))
        # No cost table is consulted. Equal or differing nonnegative expenditure
        # is reported honestly, rather than forced to the illustrative cost10.
        for spend in (0, 1, 16):
            raw = bytearray(self.settled.record)
            for i in range(8):
                raw[14+31*i] = max(0, self.unit[14+31*i]-spend)
            result = self.compare(settled=replace(self.settled, record=bytes(raw)))
            self.assertTrue(result["passed"], result["failures"])
            self.assertEqual([a["delta"] for a in result["ap_deltas"]], [-spend]*8)

    def test_all_changed_bytes_are_retained_without_opaque_semantics_claim(self):
        raw = bytearray(self.settled.record)
        raw[5] = 7                   # Native facing.
        raw[6+18] = 0xFE             # Occupied-slot aux runtime byte.
        raw[6+13] = 2                # Occupied-slot flags are reported.
        raw[319+4*100] = 0xAB        # Inactive tail of the cleared queue.
        raw[724] ^= 1               # Unrecovered army tail.
        final = replace(self.settled, record=bytes(raw))
        result = self.compare(settled=final)
        self.assertTrue(result["passed"], result["failures"])
        for key, before, after in (("save_to_baseline", self.unit, self.base.record),
                                  ("baseline_to_preview", self.base.record, self.preview.record),
                                  ("preview_to_settled", self.preview.record, final.record)):
            receipt = result["byte_deltas"][key]
            replay = bytearray(before)
            indices = set()
            for group in receipt["ranges"]:
                start, end = group["offset"], group["offset"]+group["size"]
                self.assertEqual(before[start:end].hex(), group["before_hex"])
                self.assertTrue(all(a != b for a, b in zip(before[start:end], after[start:end])))
                self.assertFalse(indices.intersection(range(start, end)))
                indices.update(range(start, end))
                replay[start:end] = bytes.fromhex(group["after_hex"])
            self.assertEqual(bytes(replay), after)
            self.assertEqual(receipt["changed_bytes"], len(indices))


if __name__ == "__main__":
    unittest.main()
