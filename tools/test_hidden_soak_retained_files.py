"""Tiny-file reader fault fixtures and RAM-only full-frame consistency tests."""

from __future__ import annotations

import copy
import hashlib
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import hidden_soak_retained_files as retained


OUTPUT = r"C:\ClashCaptures\hd-soak\hidden\retained-fixture"
FRAME = bytes(range(256)) * 1875  # Exactly 480000 bytes, in RAM only.


def payload(count: int = 3) -> dict:
    return {
        "output_directory": OUTPUT,
        "frame_samples": [
            {
                "Name": f"frame-{index:04d}",
                "RawPath": f"{OUTPUT}\\frames\\frame-{index:04d}.raw",
                "Width": 800, "Height": 600,
                "Hash": hashlib.sha256(FRAME).hexdigest(),
                "NonblackPercent": 99.609,
                "UniqueSampleColors": 256,
            }
            for index in range(1, count + 1)
        ],
    }


def fixed_reader(sample: dict, data: bytes = FRAME):
    """Only this exact RAM inventory is readable; no arbitrary path fallback."""
    inventory = {row["RawPath"].casefold(): data for row in sample["frame_samples"] if type(row.get("RawPath")) is str}

    def read(path: str, max_bytes: int) -> bytes:
        if max_bytes != 480000 or path.casefold() not in inventory:
            raise AssertionError(f"outside fixed synthetic inventory: {path}, {max_bytes}")
        return inventory[path.casefold()]

    return read


def changed_stat(info, **updates):
    fields = {name: getattr(info, name) for name in (
        "st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns",
    )}
    fields["st_file_attributes"] = getattr(info, "st_file_attributes", 0)
    if hasattr(info, "st_birthtime_ns"):
        fields["st_birthtime_ns"] = info.st_birthtime_ns
    fields.update(updates)
    return SimpleNamespace(**fields)


def creation_ns(info) -> int:
    created = getattr(info, "st_birthtime_ns", None)
    return info.st_ctime_ns if created is None else created


class RetainedFileReaderTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="hidden-retained-tiny-")
        self.addCleanup(self.scratch.cleanup)
        self.directory = Path(self.scratch.name)
        self.path = self.directory / "fixture.txt"
        self.path.write_bytes(b"retained fixture\n")

    def test_actual_read_is_bounded_readonly_and_root_first(self):
        real_lstat = os.lstat
        observations = []

        def observe(path):
            observations.append(Path(path))
            return real_lstat(path)

        before = self.path.stat()
        with mock.patch.object(retained.os, "lstat", side_effect=observe):
            self.assertEqual(retained.read_retained_file(str(self.path), 1023), b"retained fixture\n")
        chain = [*reversed(self.path.parents), self.path]
        self.assertEqual(observations, chain + chain)
        self.assertEqual(self.path.stat().st_mtime_ns, before.st_mtime_ns)

    def test_missing_unreadable_nonregular_and_invalid_requests_fail(self):
        for path, limit in (
            (str(self.path.with_name("absent.txt")), 100), (str(self.directory), 100),
            ("relative.txt", 100), (str(self.path), 0), (str(self.path), True),
            (str(self.path), 2), (" " + str(self.path), 100),
        ):
            with self.subTest(path=path, limit=limit), self.assertRaises(retained.RetainedFileError):
                retained.read_retained_file(path, limit)
        denied = PermissionError("read denied")
        with mock.patch.object(retained.os, "open", side_effect=denied), self.assertRaises(retained.RetainedFileError) as raised:
            retained.read_retained_file(str(self.path), 100)
        self.assertIs(raised.exception.errors[0], denied)

    def test_reparse_and_symlink_ancestors_are_rejected_before_open(self):
        real_lstat = os.lstat
        for update in ({"st_file_attributes": 0x400}, {"st_mode": stat.S_IFLNK | 0o777}):
            def inspect(path, update=update):
                info = real_lstat(path)
                return changed_stat(info, **update) if Path(path) == self.directory else info

            with self.subTest(update=update), mock.patch.object(retained.os, "lstat", side_effect=inspect), mock.patch.object(retained.os, "open") as opened:
                with self.assertRaises(retained.RetainedFileError):
                    retained.read_retained_file(str(self.path), 100)
                opened.assert_not_called()

    def test_unreadable_ancestor_fails_before_open(self):
        real_lstat = os.lstat
        denied = PermissionError("ancestor denied")

        def inspect(path):
            if Path(path) == self.directory:
                raise denied
            return real_lstat(path)

        with mock.patch.object(retained.os, "lstat", side_effect=inspect), mock.patch.object(retained.os, "open") as opened:
            with self.assertRaises(retained.RetainedFileError) as raised:
                retained.read_retained_file(str(self.path), 100)
            opened.assert_not_called()
        self.assertIs(raised.exception.errors[0], denied)

    def test_held_file_identity_and_metadata_drift_are_rejected(self):
        real_fstat = os.fstat
        for change_at in (1, 2):
            calls = 0

            def inspect(descriptor):
                nonlocal calls
                calls += 1
                info = real_fstat(descriptor)
                return changed_stat(info, st_ino=info.st_ino + 1) if calls == change_at else info

            with self.subTest(change_at=change_at), mock.patch.object(retained.os, "fstat", side_effect=inspect):
                with self.assertRaises(retained.RetainedFileError):
                    retained.read_retained_file(str(self.path), 100)

    def test_handle_ctime_meaning_may_differ_from_the_path_api(self):
        # Windows Python 3.12+ reports creation time as lstat st_ctime_ns but the
        # last metadata change as fstat st_ctime_ns. Emulate that handle view on
        # every interpreter; an unchanged file with the same creation time reads.
        real_fstat = os.fstat
        created = creation_ns(os.lstat(self.path))

        def handle_view(descriptor):
            info = real_fstat(descriptor)
            return changed_stat(info, st_ctime_ns=info.st_mtime_ns + 7, st_birthtime_ns=created)

        with mock.patch.object(retained.os, "fstat", side_effect=handle_view):
            self.assertEqual(retained.read_retained_file(str(self.path), 1023), b"retained fixture\n")

    def test_extension_derived_execute_bits_may_differ_from_the_handle(self):
        # Windows derives lstat execute bits from a path's extension; a nameless
        # handle never reports them, on every Python version. Read a real .exe
        # name, then emulate that handle view on every interpreter.
        executable = self.directory / "candidate.exe"
        executable.write_bytes(b"MZ retained fixture\n")
        self.assertEqual(retained.read_retained_file(str(executable), 100), b"MZ retained fixture\n")
        real_fstat = os.fstat

        def handle_view(descriptor):
            info = real_fstat(descriptor)
            return changed_stat(info, st_mode=info.st_mode & ~0o111)

        with mock.patch.object(retained.os, "fstat", side_effect=handle_view):
            self.assertEqual(retained.read_retained_file(str(executable), 100), b"MZ retained fixture\n")

    def test_handle_file_type_or_write_permission_drift_is_rejected(self):
        real_fstat = os.fstat
        for label, update in (("file type", lambda mode: (mode & ~stat.S_IFMT(mode)) | stat.S_IFDIR),
                              ("write permission", lambda mode: mode ^ stat.S_IWUSR)):
            def handle_view(descriptor, update=update):
                info = real_fstat(descriptor)
                return changed_stat(info, st_mode=update(info.st_mode))

            with self.subTest(label), mock.patch.object(retained.os, "fstat", side_effect=handle_view):
                with self.assertRaises(retained.RetainedFileError) as raised:
                    retained.read_retained_file(str(self.path), 100)
                self.assertIn("identity differs from its admitted path", str(raised.exception))

    def test_creation_time_drift_between_path_and_handle_is_rejected(self):
        real_fstat = os.fstat

        def handle_view(descriptor):
            info = real_fstat(descriptor)
            return changed_stat(info, st_birthtime_ns=creation_ns(info) + 1)

        with mock.patch.object(retained.os, "fstat", side_effect=handle_view):
            with self.assertRaises(retained.RetainedFileError) as raised:
                retained.read_retained_file(str(self.path), 100)
        self.assertIn("identity differs from its admitted path", str(raised.exception))

    def test_handle_metadata_change_during_read_is_still_rejected(self):
        real_fstat = os.fstat
        calls = 0

        def inspect(descriptor):
            nonlocal calls
            calls += 1
            info = real_fstat(descriptor)
            return changed_stat(info, st_ctime_ns=info.st_ctime_ns + 1) if calls == 2 else info

        with mock.patch.object(retained.os, "fstat", side_effect=inspect):
            with self.assertRaises(retained.RetainedFileError) as raised:
                retained.read_retained_file(str(self.path), 100)
        self.assertIn("changed during read", str(raised.exception))

    def test_after_read_path_and_ancestor_drift_are_rejected(self):
        real_lstat = os.lstat
        for changed, field in ((self.directory, "st_ino"), (self.path, "st_ino"),
                               (self.directory, "st_mtime_ns"), (self.directory, "st_ctime_ns")):
            seen = 0

            def inspect(path):
                nonlocal seen
                info = real_lstat(path)
                if Path(path) == changed:
                    seen += 1
                    if seen == 2:
                        return changed_stat(info, **{field: getattr(info, field) + 1})
                return info

            with self.subTest(changed=changed), mock.patch.object(retained.os, "lstat", side_effect=inspect):
                with self.assertRaises(retained.RetainedFileError) as raised:
                    retained.read_retained_file(str(self.path), 100)
                self.assertIn(repr(str(changed)), str(raised.exception))
                self.assertIn(f"{field}=", str(raised.exception))

    def test_actual_growth_and_truncation_are_rejected(self):
        real_read = os.read
        for replacement in (b"x", b"x" * 40):
            changed = False

            def read(descriptor, amount):
                nonlocal changed
                if not changed:
                    changed = True
                    self.path.write_bytes(replacement)
                return real_read(descriptor, amount)

            self.path.write_bytes(b"retained fixture\n")
            with self.subTest(replacement=len(replacement)), mock.patch.object(retained.os, "read", side_effect=read):
                with self.assertRaises(retained.RetainedFileError):
                    retained.read_retained_file(str(self.path), 100)

    def test_original_read_and_close_failures_are_both_preserved(self):
        read_error, close_error = OSError("read failed"), OSError("close failed")
        real_close = os.close

        def close(descriptor):
            real_close(descriptor)
            raise close_error

        with mock.patch.object(retained.os, "read", side_effect=read_error), mock.patch.object(retained.os, "close", side_effect=close):
            with self.assertRaises(retained.RetainedFileError) as raised:
                retained.read_retained_file(str(self.path), 100)
        self.assertEqual(raised.exception.errors, (read_error, close_error))

    def test_close_failure_alone_never_returns_bytes(self):
        real_close = os.close

        def close(descriptor):
            real_close(descriptor)
            raise OSError("close alone failed")

        with mock.patch.object(retained.os, "close", side_effect=close), self.assertRaises(retained.RetainedFileError):
            retained.read_retained_file(str(self.path), 100)


class RetainedFrameTests(unittest.TestCase):
    def check(self, sample, data=FRAME):
        with mock.patch.object(retained, "_read_retained_file", side_effect=fixed_reader(sample, data)) as reader:
            summary, failures = retained.validate_retained_frames(sample)
            return summary, failures, reader.call_count

    def test_every_periodic_and_terminal_frame_is_read_from_fixed_ram_inventory(self):
        sample = payload(5)
        summary, failures, reads = self.check(sample)
        self.assertEqual(failures, [])
        self.assertEqual(reads, 5)
        self.assertEqual(summary["consistent_frame_count"], 5)
        self.assertTrue(summary["retained_frame_bytes_consistent"])
        for field in ("immutable_files_authenticated", "native_producer_authenticated", "coherent_capture_authenticated", "original_file_authenticated"):
            self.assertIs(summary[field], False)

    def test_default_reader_missing_retained_files_fails_without_optout(self):
        sample = payload(1)
        sample["output_directory"] += "-missing-12a6a9e41d044ddb92bfb7464c82e139"
        sample["frame_samples"][0]["RawPath"] = sample["output_directory"] + r"\frames\frame-0001.raw"
        sample["skip_retained_files"] = True
        sample["fixture_root"] = "unused"
        summary, failures = retained.validate_retained_frames(sample)
        self.assertTrue(failures)
        self.assertFalse(summary["retained_frame_bytes_consistent"])
        self.assertEqual(summary["read_frame_count"], 0)

    def test_byte_mutation_size_mismatch_and_middle_frame_corruption_fail(self):
        sample = payload(3)
        changed = bytes([1]) + FRAME[1:]
        for data in (changed, FRAME[:-1], FRAME + b"x"):
            with self.subTest(size=len(data)):
                self.assertTrue(self.check(sample, data)[1])
        read = fixed_reader(sample)

        def corrupt_middle(path, limit):
            return changed if path.endswith("frame-0002.raw") else read(path, limit)

        with mock.patch.object(retained, "_read_retained_file", side_effect=corrupt_middle):
            summary, failures = retained.validate_retained_frames(sample)
        self.assertEqual(summary["consistent_frame_count"], 2)
        self.assertTrue(any("retained frame 1.Hash" in failure for failure in failures))

    def test_canonical_unique_same_run_name_raw_bindings_are_required(self):
        mutations = (
            lambda sample: sample.update(output_directory=r"C:\ClashCaptures\elsewhere\run"),
            lambda sample: sample["frame_samples"][0].update(RawPath=OUTPUT + r"\frame-0001.raw"),
            lambda sample: sample["frame_samples"][0].update(RawPath=OUTPUT + r"\frames\..\frames\frame-0001.raw"),
            lambda sample: sample["frame_samples"][0].update(RawPath=OUTPUT + r"\frames\frame-0001.raw:stream"),
            lambda sample: sample["frame_samples"][0].update(Name="frame-00001"),
            lambda sample: sample["frame_samples"][0].update(Name="frame-0000"),
            lambda sample: sample["frame_samples"].append(copy.deepcopy(sample["frame_samples"][0])),
        )
        for mutate in mutations:
            sample = payload(1)
            mutate(sample)
            with self.subTest(sample=sample):
                self.assertTrue(self.check(sample)[1])

    def test_bad_shapes_metrics_dimensions_and_missing_raw_paths_fail(self):
        for field, value in (
            ("Width", True), ("Height", 599), ("Width", 600), ("Hash", "a" * 64),
            ("NonblackPercent", 1), ("NonblackPercent", True), ("NonblackPercent", float("nan")),
            ("NonblackPercent", 10 ** 1000), ("UniqueSampleColors", 42), ("UniqueSampleColors", True),
            ("RawPath", None), ("Name", "frame-" + "0" * 5000),
        ):
            sample = payload(1)
            sample["frame_samples"][0][field] = value
            with self.subTest(field=field, value_type=type(value).__name__):
                self.assertTrue(self.check(sample)[1])
        for sample in ({}, {"frame_samples": []}, {"frame_samples": [None]}, None):
            with self.subTest(sample=sample):
                self.assertTrue(retained.validate_retained_frames(sample)[1])

    def test_reader_errors_are_reported_without_suppressing_other_frames(self):
        sample = payload(3)
        read = fixed_reader(sample)

        def missing_middle(path, limit):
            if path.endswith("frame-0002.raw"):
                raise retained.RetainedFileError("missing middle", (FileNotFoundError("missing"),))
            return read(path, limit)

        with mock.patch.object(retained, "_read_retained_file", side_effect=missing_middle) as reader:
            summary, failures = retained.validate_retained_frames(sample)
        self.assertEqual(reader.call_count, 3)
        self.assertEqual(summary["consistent_frame_count"], 2)
        self.assertIn("missing middle", " ".join(failures))

    def test_midpoint_metric_matches_actual_powershell_rounding(self):
        sample = payload(1)
        data = b"\x01" * 12 + b"\x00" * (480000 - 12)
        sample["frame_samples"][0].update(Hash=hashlib.sha256(data).hexdigest(), NonblackPercent=0.002, UniqueSampleColors=2)
        self.assertEqual(self.check(sample, data)[1], [])

    def test_unfiltered_inventory_and_no_reader_parameter(self):
        sample = payload(1)
        sample["evidence_frames"] = []
        self.assertTrue(self.check(sample)[1])
        with self.assertRaises(TypeError):
            retained.validate_retained_frames(payload(1), reader=lambda *_: FRAME)


def run_tests() -> None:
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__)))
    if not result.wasSuccessful() or result.skipped:
        raise RuntimeError("retained-file source fixtures did not pass completely")


if __name__ == "__main__":
    run_tests()
