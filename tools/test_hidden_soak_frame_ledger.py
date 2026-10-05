#!/usr/bin/env python3
"""Mocked clock/read/storage only: no native APIs or output/scratch files."""
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path, PureWindowsPath
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hidden_soak_frame_ledger as ledger
import hidden_soak_process_lease as process

REAL_LEDGER, REAL_PROCESS = Path(ledger.__file__).resolve(), Path(process.__file__).resolve()
MOCK_LEDGER = Path("C:/fixture/tools/hidden_soak_frame_ledger.py")
MOCK_PROCESS = Path("C:/fixture/tools/hidden_soak_process_lease.py")


class MockStorage:
    """Retain segment references;242 frames share immutable raw fixture bytes."""
    def __init__(self):
        self.files, self.calls, self.clock = {}, [], 1_000_000_000
        self.sources = {process._path(str(MOCK_LEDGER)): hashlib.sha256(REAL_LEDGER.read_bytes()).hexdigest(),
                        process._path(str(MOCK_PROCESS)): hashlib.sha256(REAL_PROCESS.read_bytes()).hexdigest()}
        self.root = "c:\\clashcaptures\\ledger-fixture"
        self.root_identity = "directory-generation-1"
        self.free, self.total = 80_000_000_000, 100_000_000_000
        self.hook, self.next_id, self.closed = None, 0, set()
        self.short_write = False
        self.deny_flush, self.deny_close, self.deny_publish = False, False, False

    def step(self, name, value=None):
        self.calls.append((name, value))
        if self.hook:
            self.hook(self, name, value)

    def source_sha256(self, path):
        self.step("source", path); return self.sources[path]

    def inspect_root(self, path):
        self.step("root", path)
        return ledger.DirectoryObservation(self.root, self.root_identity,
                                           (False,) * len(PureWindowsPath(self.root).parts))

    def disk_space(self, path):
        self.step("space", path); return ledger.DiskSpace(self.total, self.free)

    def monotonic_ns(self):
        self.step("clock"); result = self.clock; self.clock += 1000; return result

    def create_exclusive(self, name):
        self.step("create", name)
        if name in self.files:
            raise FileExistsError(name)
        self.next_id += 1
        self.files[name] = {"identity": "file-" + str(self.next_id), "segments": [], "regular": True, "reparse": False, "links": 1}
        return (name, self.next_id)

    def write(self, handle, data):
        assert handle not in self.closed
        self.step("write", handle)
        count = len(data) // 2 if self.short_write else len(data)
        self.files[handle[0]]["segments"].append(data if count == len(data) else data[:count])
        self.free -= count
        return count

    def flush(self, handle):
        assert handle not in self.closed
        self.step("flush", handle)
        if self.deny_flush:
            raise OSError("flush denied")

    def close(self, handle):
        assert handle not in self.closed
        self.step("close", handle); self.closed.add(handle)
        if self.deny_close:
            raise OSError("close denied")

    def publish_exclusive(self, temporary, name):
        self.step("publish", (temporary, name))
        if self.deny_publish:
            raise OSError("publish denied")
        if name in self.files:
            raise FileExistsError(name)
        self.files[name] = self.files.pop(temporary)

    def stat(self, name):
        self.step("stat", name); row = self.files[name]
        return ledger.FileObservation(row["identity"], sum(map(len, row["segments"])),
                                      row["regular"], row["reparse"], row["links"])

    def read(self, name):
        self.step("read", name); return b"".join(self.files[name]["segments"])

    def replace_bytes(self, name, data):
        self.files[name]["segments"] = [data]


def surface(width=800, height=600):
    header = struct.pack("<HHI", width, height, 0x20000000) + b"\0" * (ledger.HEADER_BYTES - 8)
    return ledger.SurfaceAuthority(width, height, 0x10000000, 0x20000000, header)


def authority(store, geometry=None):
    geometry = geometry or surface()
    controller = process.Generation(1, 100, "C:/host/python.exe", "a" * 64)
    debugger = process.Generation(2, 200, "C:/tools/cdb.exe", "b" * 64)
    target = process.Generation(3, 300, "C:/ClashTests/candidate.exe", "c" * 64)
    run = process.RunAuthority("0123456789abcdef0123456789abcdef", "c" * 64, "d" * 64,
                              "modalwidgets", f"{geometry.width}x{geometry.height}", "fixture-validation", controller,
                              (process.ImageAuthority("candidate", target.image_path, target.image_sha256),
                               process.ImageAuthority("debugger", debugger.image_path, debugger.image_sha256)),
                              tuple(process.SourcePin(path, digest) for path, digest in store.sources.items()))
    runtime = 1024 * 1024
    return ledger.FrameAuthority(run, target, debugger, geometry, store.clock,
                                 "C:/checkout/clash-hd", store.root, store.root_identity, runtime,
                                 ledger.budget(geometry, runtime)["total_peak_bytes"])


def read_lease(auth, ordinal):
    due = auth.start_ns + min(ordinal, ledger.PERIODIC_COUNT - 1) * ledger.PERIOD_NS
    return ledger.ReadLease(auth.run.run_id, ordinal, f"{ordinal + 1:032x}", due,
                            auth.target, auth.debugger, auth.surface)


class MockReader:
    def __init__(self, auth, raw=None):
        self.auth = auth
        self.raw = raw if raw is not None else bytes(range(256)) * (auth.surface.width * auth.surface.height // 256) + bytes(range(auth.surface.width * auth.surface.height % 256))
        self.calls, self.transform = [], None

    def read(self, read_lease, requested_bytes):
        self.calls.append((read_lease, requested_bytes))
        observed = process.Observation(self.auth.target, self.auth.debugger.pid, 258, None, 0)
        result = ledger.ReadResult(observed, observed, self.auth.debugger, self.auth.debugger,
                                   self.auth.surface.header, self.auth.surface.header,
                                   self.auth.surface.width, self.auth.surface.width,
                                   requested_bytes, len(self.raw), 1, 0, self.raw)
        return self.transform(result) if self.transform else result


def collect(store=None, auth=None, transform=None, count=ledger.FRAME_COUNT):
    store = store or MockStorage(); auth = auth or authority(store)
    manager, reader = ledger.FrameLedger(auth, store), MockReader(auth)
    for ordinal in range(count):
        store.clock = auth.start_ns + min(ordinal, ledger.PERIODIC_COUNT - 1) * ledger.PERIOD_NS
        if ordinal == ledger.PERIODIC_COUNT:
            store.clock += 3000
        reader.transform = (lambda result, i=ordinal: transform(i, result)) if transform else None
        manager.capture(read_lease(auth, ordinal), reader)
    report, binding, error = manager.finish()
    return store, auth, manager, reader, report, binding, error


def reseal(store, auth, report):
    """Deliberately grant new external bindings to exercise semantic rejects."""
    artifacts = {}
    for row in report["attempts"]:
        if row["artifact"] is None:
            continue
        name = row["artifact"]["name"]
        metadata, raw = ledger._decode_container(store.read(name))
        segments = ledger._container({key: value for key, value in row.items() if key != "artifact"}, raw)
        store.files[name]["segments"] = list(segments)
        bound = ledger.ArtifactBinding(name, ledger._sha(store.read(name)), store.stat(name).size, store.stat(name).identity)
        row["artifact"] = ledger.asdict(bound); artifacts[bound.name] = bound
    data = ledger._canonical(report)
    store.replace_bytes("ledger.json", data)
    index = ledger.ArtifactBinding("ledger.json", ledger._sha(data), len(data), store.stat("ledger.json").identity)
    return ledger.CollectorBinding(ledger._sha(ledger._canonical(ledger._wire_authority(auth))), index, tuple(artifacts.values()))


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        patch.object(process, "SOURCE", MOCK_PROCESS).start()
        patch.object(ledger, "SOURCE", MOCK_LEDGER).start()

    def test_complete_fixed_schedule_original_bytes_and_false_claims(self):
        store, auth, manager, reader, report, binding, error = collect()
        self.assertIsNone(error)
        self.assertEqual(len(reader.calls), 242)
        self.assertEqual(len(report["attempts"]), 242)
        result = ledger.replay(auth, binding, store)
        self.assertTrue(result["raw_ledger_replay_passed"], result)
        self.assertTrue(all(result[key] is False for key in ledger.FALSE_CLAIMS))
        self.assertEqual(len({row["raw_sha256"] for row in report["attempts"]}), 1)
        self.assertEqual(report["schedule"]["duration_ns"], 7200 * 1_000_000_000)
        self.assertGreater(report["attempts"][-1]["begin_ns"], report["attempts"][-2]["end_ns"])

    def test_nine_geometry_budgets_and_complete_partial_frames(self):
        for width, height in ledger.PRESETS:
            with self.subTest(resolution=(width, height)):
                store = MockStorage(); auth = authority(store, surface(width, height))
                plan = ledger.budget(auth.surface, auth.runtime_asset_bytes)
                self.assertEqual(plan["all_raw_bytes"], 242 * width * height)
                self.assertEqual(plan["total_peak_bytes"], auth.runtime_asset_bytes + plan["all_raw_bytes"]
                                 + plan["atomic_temporary_bytes"] + 160 * 1024 * 1024)
                manager = ledger.FrameLedger(auth, store); reader = MockReader(auth)
                self.assertTrue(manager.capture(read_lease(auth, 0), reader))
                original = reader.raw
                store.clock = auth.start_ns + ledger.PERIOD_NS
                reader.transform = lambda result: replace(result, raw=original[:12345], returned_bytes=12345, native_return=0, native_error=299)
                self.assertFalse(manager.capture(read_lease(auth, 1), reader))
                metadata, retained = ledger._decode_container(store.read("frame-0001.frame"))
                self.assertEqual(retained, original[:12345])
                self.assertTrue(metadata["errors"])

    def test_custom_geometry_and_insufficient_external_budget_reject(self):
        with self.assertRaises(ValueError):
            surface(802, 602)
        store = MockStorage(); auth = authority(store)
        with self.assertRaises(ValueError):
            replace(auth, available_peak_bytes=auth.available_peak_bytes - 1)
        with self.assertRaises(ValueError):
            replace(auth, runtime_asset_bytes=True)
        with self.assertRaises(ValueError):
            replace(auth.surface, header_address=1)
        with self.assertRaises(ValueError):
            replace(auth.surface, pixels_address=0xf0000000)
        self.assertFalse(any(name == "create" for name, value in store.calls))

    def test_foreign_late_and_future_leases_denied_before_reader(self):
        for mode in ("target", "parent", "surface", "run", "late", "future", "stale"):
            store = MockStorage(); auth = authority(store); manager = ledger.FrameLedger(auth, store); reader = MockReader(auth)
            issued = read_lease(auth, 0)
            if mode == "target": issued = replace(issued, target=replace(auth.target, creation_filetime=301))
            elif mode == "parent": issued = replace(issued, debugger=replace(auth.debugger, creation_filetime=201))
            elif mode == "surface": issued = replace(issued, surface=surface(1024, 768))
            elif mode == "run": issued = replace(issued, run_id="0" * 32)
            elif mode == "late": store.clock += ledger.MAX_LATENESS_NS + 1
            elif mode == "future": issued = replace(issued, issued_ns=issued.issued_ns + 1)
            else: issued = replace(issued, issued_ns=issued.issued_ns - 1)
            self.assertFalse(manager.capture(issued, reader), mode)
            self.assertFalse(reader.calls, mode)
            metadata, raw = ledger._decode_container(store.read("frame-0000.frame"))
            self.assertIsNone(metadata["read"])
            self.assertEqual(raw, b"")
            self.assertTrue(metadata["errors"])

    def test_failed_final_readback_identifies_preserved_final_path(self):
        store = MockStorage(); auth = authority(store); manager = ledger.FrameLedger(auth, store); reader = MockReader(auth)
        def poison_final_readback(adapter, name, value):
            if name == "publish":
                adapter.root_identity = "changed-after-publication"
        store.hook = poison_final_readback
        self.assertFalse(manager.capture(read_lease(auth, 0), reader))
        self.assertIn("frame-0000.frame", store.files)
        self.assertNotIn("frame-0000.frame.partial", store.files)
        self.assertTrue(any("frame-0000.frame" in error for error in manager.rows[0]["errors"]))

    def test_reserve_checked_before_creation_and_each_write(self):
        store = MockStorage(); auth = authority(store)
        store.free = store.total // 10 + auth.available_peak_bytes
        with self.assertRaises(ValueError):
            ledger.FrameLedger(auth, store)
        self.assertFalse(store.files)
        store.free = 80_000_000_000
        manager, reader = ledger.FrameLedger(auth, store), MockReader(auth)
        def lower_after_create(adapter, name, value):
            if name == "create":
                adapter.free = adapter.total // 10
        store.hook = lower_after_create
        self.assertFalse(manager.capture(read_lease(auth, 0), reader))
        self.assertFalse(any(name == "write" for name, value in store.calls))
        self.assertIn("frame-0000.frame.partial", store.files)

    def test_reserve_remaining_allowance_tracks_actual_retained_bytes(self):
        store = MockStorage(); auth = authority(store)
        manager, reader = ledger.FrameLedger(auth, store), MockReader(auth)
        store.free = store.total // 10 + auth.available_peak_bytes + 1
        self.assertTrue(manager.capture(read_lease(auth, 0), reader))
        self.assertGreater(manager.retained_bytes, len(reader.raw))
        self.assertEqual(store.free + manager.retained_bytes, store.total // 10 + auth.available_peak_bytes + 1)
        store.clock = auth.start_ns + ledger.PERIOD_NS
        self.assertTrue(manager.capture(read_lease(auth, 1), reader))

    def test_consumed_retention_capacity_cannot_erase_peak_guard(self):
        store = MockStorage(); auth = authority(store); manager = ledger.FrameLedger(auth, store); reader = MockReader(auth)
        plan = ledger.budget(auth.surface, auth.runtime_asset_bytes)
        capacity = plan["all_raw_bytes"] + plan["atomic_temporary_bytes"] + plan["metadata_bytes"]
        manager.retained_bytes = capacity - 100
        self.assertFalse(manager.capture(read_lease(auth, 0), reader))
        self.assertFalse(any(name == "create" for name, value in store.calls))
        self.assertEqual(manager.pending_captures[0].raw, reader.raw)
        self.assertTrue(any("retention allowance" in error for error in manager.rows[0]["errors"]))
        manager.retained_bytes = capacity + 1
        with self.assertRaises(ValueError):
            manager._prewrite()

    def test_pitch_header_and_generation_failures_preserve_original_raw(self):
        transforms = (
            lambda result: replace(result, pitch_after=result.pitch_after + 1),
            lambda result: replace(result, header_after=result.header_after[:-1]),
            lambda result: replace(result, target_after=replace(result.target_after, generation=replace(result.target_after.generation, creation_filetime=301))),
            lambda result: replace(result, debugger_after=replace(result.debugger_after, creation_filetime=201)),
        )
        for transform in transforms:
            store = MockStorage(); auth = authority(store); manager = ledger.FrameLedger(auth, store); reader = MockReader(auth)
            reader.transform = transform
            self.assertFalse(manager.capture(read_lease(auth, 0), reader))
            metadata, raw = ledger._decode_container(store.read("frame-0000.frame"))
            self.assertEqual(raw, reader.raw)
            self.assertTrue(metadata["errors"])

    def test_reader_exception_carries_original_partial_bytes(self):
        store = MockStorage(); auth = authority(store); manager = ledger.FrameLedger(auth, store); reader = MockReader(auth)
        def native_partial(result):
            partial = replace(result, raw=result.raw[:4567], returned_bytes=4567, native_return=0, native_error=299)
            raise ledger.ReadFailure(partial, "native partial read")
        reader.transform = native_partial
        self.assertFalse(manager.capture(read_lease(auth, 0), reader))
        metadata, raw = ledger._decode_container(store.read("frame-0000.frame"))
        self.assertEqual(raw, reader.raw[:4567])
        self.assertEqual(metadata["read"]["returned_bytes"], 4567)
        self.assertTrue(any("ReadFailure" in error for error in metadata["errors"]))

    def test_file_generation_changes_during_readback_and_unknown_io_returns_fail(self):
        for mode in ("identity", "reparse", "flush", "close", "publish"):
            store = MockStorage(); auth = authority(store); manager = ledger.FrameLedger(auth, store); reader = MockReader(auth)
            if mode in ("identity", "reparse"):
                def mutate(adapter, name, value):
                    if name == "read":
                        if mode == "identity": adapter.files[value]["identity"] = "changed-file-generation"
                        else: adapter.files[value]["reparse"] = True
                store.hook = mutate
            elif mode == "flush": store.flush = lambda handle: False
            elif mode == "close": store.close = lambda handle: False
            else: store.publish_exclusive = lambda temporary, name: False
            self.assertFalse(manager.capture(read_lease(auth, 0), reader), mode)
            self.assertTrue(manager.rows[0]["errors"])

    def test_atomic_readback_must_match_written_original_bytes(self):
        store = MockStorage(); auth = authority(store); manager = ledger.FrameLedger(auth, store); reader = MockReader(auth)
        def corrupt_write(adapter, name, value):
            if name == "flush":
                parts = adapter.files[value[0]]["segments"]
                raw = parts[-1]
                midpoint = len(raw) // 2
                parts[-1] = raw[:midpoint] + bytes([raw[midpoint] ^ 1]) + raw[midpoint + 1:]
        store.hook = corrupt_write
        self.assertFalse(manager.capture(read_lease(auth, 0), reader))
        self.assertEqual(manager.pending_captures[0].raw, reader.raw)
        self.assertTrue(any("original write bytes" in error for error in manager.rows[0]["errors"]))
        with self.assertRaises(ValueError):
            manager._atomic("../escaped.frame", (b"not permitted",))

    def test_atomic_short_write_flush_close_publish_failures_sticky(self):
        for flag in ("short_write", "deny_flush", "deny_close", "deny_publish"):
            with self.subTest(failure=flag):
                store = MockStorage(); auth = authority(store); manager = ledger.FrameLedger(auth, store); reader = MockReader(auth)
                setattr(store, flag, True)
                self.assertFalse(manager.capture(read_lease(auth, 0), reader))
                self.assertIn("frame-0000.frame.partial", store.files)
                self.assertEqual(len(store.closed), 1)
                self.assertIsNotNone(manager.rows[0]["artifact"])
                self.assertEqual(manager.pending_captures[0].raw, reader.raw)
                setattr(store, flag, False)
                report, binding, error = manager.finish()
                self.assertIsNone(error)
                self.assertTrue(report["attempts"][0]["errors"])
                self.assertFalse(ledger.replay(auth, binding, store)["raw_ledger_replay_passed"])

    def test_collisions_reparse_escape_and_hardlinks_reject(self):
        store = MockStorage(); auth = authority(store)
        with self.assertRaises(ValueError):
            replace(auth, output_root=auth.checkout_root)
        manager, reader = ledger.FrameLedger(auth, store), MockReader(auth)
        self.assertTrue(manager.capture(read_lease(auth, 0), reader))
        another = ledger.FrameLedger(auth, store)
        self.assertFalse(another.capture(read_lease(auth, 0), reader))
        self.assertIn("frame-0000.frame.partial", store.files)
        store.files["frame-0000.frame"]["links"] = 2
        with self.assertRaises(ValueError):
            manager._bound_read("frame-0000.frame")
        def root_reparse(path):
            return ledger.DirectoryObservation(store.root, store.root_identity, (False, True, False))
        store.inspect_root = root_reparse
        with self.assertRaises(ValueError):
            ledger.FrameLedger(auth, store)

    def test_source_and_root_mutation_cannot_pass(self):
        store, auth, manager, reader, report, binding, error = collect()
        store.sources[next(iter(store.sources))] = "0" * 64
        self.assertFalse(ledger.replay(auth, binding, store)["raw_ledger_replay_passed"])
        store.sources = {pin.path: pin.sha256 for pin in auth.run.source_pins}
        store.root_identity = "different"
        self.assertFalse(ledger.replay(auth, binding, store)["raw_ledger_replay_passed"])

    def test_external_authority_and_binding_required(self):
        store, auth, manager, reader, report, binding, error = collect()
        for supplied in (report["authority"], report, None):
            self.assertFalse(ledger.replay(supplied, binding, store)["raw_ledger_replay_passed"])
        for supplied in (ledger.asdict(binding), report, None):
            self.assertFalse(ledger.replay(auth, supplied, store)["raw_ledger_replay_passed"])
        self.assertFalse(ledger.replay(replace(auth, start_ns=auth.start_ns + 1), binding, store)["raw_ledger_replay_passed"])

    def test_reused_parent_generation_chronology_rejects(self):
        store = MockStorage(); auth = authority(store)
        with self.assertRaises(ValueError):
            replace(auth, target=replace(auth.target, creation_filetime=199))
        with self.assertRaises(ValueError):
            replace(auth, debugger=replace(auth.debugger, creation_filetime=99))

    def test_interior_raw_byte_change_and_consistently_resealed_size_fail(self):
        store, auth, manager, reader, report, binding, error = collect()
        name = "frame-0123.frame"
        metadata, raw = ledger._decode_container(store.read(name))
        changed = raw[:len(raw)//2] + bytes([raw[len(raw)//2] ^ 1]) + raw[len(raw)//2 + 1:]
        store.files[name]["segments"] = list(ledger._container(metadata, changed))
        self.assertFalse(ledger.replay(auth, binding, store)["raw_ledger_replay_passed"])
        row = report["attempts"][123]
        row["raw_sha256"] = ledger._sha(changed[:-1])
        store.files[name]["segments"] = list(ledger._container(metadata, changed[:-1]))
        resealed = reseal(store, auth, report)
        self.assertFalse(ledger.replay(auth, resealed, store)["raw_ledger_replay_passed"])

    def test_missing_duplicate_reordered_and_head_tail_only_fail(self):
        for mode in ("missing", "duplicate", "reordered", "headtail"):
            store, auth, manager, reader, report, binding, error = collect()
            if mode == "missing":
                report["attempts"].pop(120)
            elif mode == "duplicate":
                report["attempts"][120] = deepcopy(report["attempts"][119])
            elif mode == "reordered":
                report["attempts"][120], report["attempts"][121] = report["attempts"][121], report["attempts"][120]
            else:
                report["attempts"] = report["attempts"][:5] + report["attempts"][-5:]
            resealed = reseal(store, auth, report)
            self.assertFalse(ledger.replay(auth, resealed, store)["raw_ledger_replay_passed"], mode)

    def test_shortened_shifted_and_drifted_schedule_fail(self):
        for mode in ("shortened", "drift", "terminal", "envelope"):
            store, auth, manager, reader, report, binding, error = collect()
            if mode == "shortened":
                report["schedule"]["duration_ns"] -= 1
            elif mode == "drift":
                report["attempts"][100]["begin_ns"] += ledger.MAX_LATENESS_NS + 1
                report["attempts"][100]["end_ns"] += ledger.MAX_LATENESS_NS + 1
            elif mode == "terminal":
                report["attempts"][-1]["begin_ns"] = report["attempts"][-2]["end_ns"]
            else:
                report["finish_ns"] = auth.start_ns + ledger.DURATION_NS - 1
            self.assertFalse(ledger.replay(auth, reseal(store, auth, report), store)["raw_ledger_replay_passed"], mode)

    def test_failed_receipt_cannot_be_deleted_or_repaired_by_boolean(self):
        transform = lambda ordinal, result: replace(result, native_return=0, native_error=299) if ordinal == 120 else result
        store, auth, manager, reader, report, binding, error = collect(transform=transform)
        self.assertFalse(ledger.replay(auth, binding, store)["raw_ledger_replay_passed"])
        report["attempts"][120]["errors"] = []
        self.assertFalse(ledger.replay(auth, reseal(store, auth, report), store)["raw_ledger_replay_passed"])
        report["passed"] = True
        self.assertFalse(ledger.replay(auth, reseal(store, auth, report), store)["raw_ledger_replay_passed"])

    def test_typed_fields_lease_reuse_missing_raw_and_unknown_fields_fail(self):
        for mode in ("bool", "lease", "missingraw", "unknown", "approval"):
            store, auth, manager, reader, report, binding, error = collect()
            if mode == "bool":
                report["attempts"][0]["read"]["native_return"] = True
            elif mode == "lease":
                report["attempts"][120]["lease"]["token"] = report["attempts"][119]["lease"]["token"]
            elif mode == "missingraw":
                del store.files["frame-0100.frame"]
                self.assertFalse(ledger.replay(auth, binding, store)["raw_ledger_replay_passed"])
                continue
            elif mode == "unknown":
                report["attempts"][120]["observer_passed"] = True
            else:
                report["claims"]["manual_input_verified"] = True
            self.assertFalse(ledger.replay(auth, reseal(store, auth, report), store)["raw_ledger_replay_passed"], mode)

    def test_capture_order_reuse_and_finish_cannot_repeat(self):
        store = MockStorage(); auth = authority(store); manager = ledger.FrameLedger(auth, store); reader = MockReader(auth)
        with self.assertRaises(ValueError):
            manager.capture(read_lease(auth, 1), reader)
        self.assertTrue(manager.capture(read_lease(auth, 0), reader))
        with self.assertRaises(ValueError):
            manager.capture(read_lease(auth, 0), reader)
        store.clock = auth.start_ns + ledger.PERIOD_NS
        with self.assertRaises(ValueError):
            manager.capture(replace(read_lease(auth, 1), token=read_lease(auth, 0).token), reader)
        manager.finish()
        with self.assertRaises(ValueError):
            manager.finish()
        with self.assertRaises(ValueError):
            manager.capture(read_lease(auth, 1), reader)


if __name__ == "__main__":
    unittest.main()
