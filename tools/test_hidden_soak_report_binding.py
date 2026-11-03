"""Tiny actual source/copy fixtures; no game, debugger or native producer proof."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import hidden_soak_report_binding as binding
import hidden_soak_retained_files as retained


class ReportBindingTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="hidden-source-binding-tiny-")
        self.addCleanup(self.scratch.cleanup)
        self.directory = Path(self.scratch.name)
        self.source = self.directory / "external-report.json"
        self.alias = self.directory / "selected-report.json"
        self.payload = {"environment": "hidden_cdb_host", "report_json": str(self.source),
                        "executed": True, "measured_count": 1, "failures": []}
        self.raw = json.dumps(self.payload, indent=2).encode("ascii") + b"\n"
        self.source.write_bytes(self.raw)
        self.alias.write_bytes(self.raw)

    def check(self, *, payload=None, selected=None):
        return binding.validate_hidden_report_binding(
            self.payload if payload is None else payload, selected_path=selected,
        )

    def test_actual_original_and_exact_selected_copy_pass(self):
        original_payload = copy.deepcopy(self.payload)
        for selected in (None, self.source, self.alias):
            summary, failures = self.check(selected=selected)
            self.assertEqual(failures, [])
            self.assertTrue(summary["payload_matches"])
            self.assertTrue(summary["selected_bytes_match"])
            for role in ("external_source", "selected_source"):
                self.assertEqual(summary[role]["sha256"], hashlib.sha256(self.raw).hexdigest())
                self.assertEqual(summary[role]["size"], len(self.raw))
            for flag in ("immutable_files_authenticated", "native_producer_authenticated",
                         "native_execution_authenticated", "coherent_capture_authenticated", "running_time_authenticated"):
                self.assertIs(summary[flag], False)
        self.assertEqual(self.payload, original_payload)
        self.assertEqual(self.source.read_bytes(), self.raw)

    def test_missing_original_and_selected_copy_fail(self):
        self.source.unlink()
        self.assertTrue(self.check(selected=self.alias)[1])
        self.source.write_bytes(self.raw)
        self.alias.unlink()
        self.assertTrue(self.check(selected=self.alias)[1])

    def test_selected_whitespace_and_bom_drift_fail(self):
        for changed in (self.raw + b"\n", b"\xef\xbb\xbf" + self.raw, self.raw.replace(b"\n", b"\r\n")):
            self.alias.write_bytes(changed)
            summary, failures = self.check(selected=self.alias)
            self.assertTrue(failures)
            self.assertFalse(summary["selected_bytes_match"])
            self.assertEqual(json.loads(changed), self.payload)

    def test_original_whitespace_drift_against_selected_copy_fails(self):
        self.source.write_bytes(self.raw + b"\n")
        summary, failures = self.check(selected=self.alias)
        self.assertTrue(summary["payload_matches"])
        self.assertFalse(summary["selected_bytes_match"])
        self.assertTrue(failures)

    def test_semantic_and_typed_payload_drift_fail(self):
        for field, value in (("executed", 1), ("measured_count", True),
                             ("measured_count", 1.0), ("failures", ["changed"]),
                             ("measured_count", float("inf"))):
            payload = copy.deepcopy(self.payload)
            payload[field] = value
            summary, failures = self.check(payload=payload)
            self.assertTrue(failures, (field, value))
            self.assertFalse(summary["payload_matches"])

    def test_duplicate_nonfinite_and_malformed_original_json_fail(self):
        for raw in (self.raw[:-2] + b',"executed":true}\n', b'{"x":NaN}', b'{"x":Infinity}',
                    b'{"x":1e999}', b"[]", b"null", b"false", b"{", b"\xff", b""):
            self.source.write_bytes(raw)
            summary, failures = self.check()
            self.assertTrue(failures, raw)
            self.assertFalse(summary["payload_matches"])

    def test_path_policy_rejects_ambiguous_and_relative_originals(self):
        values = (None, True, [], "", " relative.json", "relative.json", "bad\0file", "bad\x7ffile")
        if os.name == "nt":
            values += (r"\\server\share\report.json", r"\\?\C:\report.json", r"C:\report.json:stream",
                       str(self.source.parent) + r"\.\external-report.json", r"C:\NUL.json")
        for value in values:
            payload = copy.deepcopy(self.payload)
            payload["report_json"] = value
            with mock.patch.object(binding, "_read_retained_file") as reader:
                self.assertTrue(self.check(payload=payload)[1], value)
            reader.assert_not_called()

    def test_oversized_source_rejected_before_read_without_large_files(self):
        with mock.patch.object(binding, "MAX_REPORT_BYTES", len(self.raw) - 1), mock.patch.object(retained.os, "open") as opener:
            self.assertTrue(self.check()[1])
            opener.assert_not_called()

    def test_source_and_selected_reparse_points_fail_before_open(self):
        real_lstat = retained.os.lstat
        for rejected in (self.source, self.alias, self.directory):
            def reparse(path, *, _rejected=rejected):
                info = real_lstat(path)
                if Path(path) != _rejected:
                    return info
                values = {field: getattr(info, field) for field in (
                    "st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns",
                )}
                values["st_file_attributes"] = getattr(info, "st_file_attributes", 0) | 0x400
                return SimpleNamespace(**values)
            with mock.patch.object(retained.os, "lstat", side_effect=reparse):
                self.assertTrue(self.check(selected=self.alias)[1], rejected)

    def test_original_read_and_close_errors_remain_diagnostics(self):
        read_error, close_error = OSError("original read failure"), OSError("original close failure")
        real_close = retained.os.close
        def close_and_fail(descriptor):
            real_close(descriptor)
            raise close_error
        with mock.patch.object(retained.os, "read", side_effect=read_error), mock.patch.object(retained.os, "close", side_effect=close_and_fail):
            failures = self.check()[1]
        self.assertTrue(any("original read failure" in failure and "original close failure" in failure for failure in failures))

    def test_observed_external_drift_during_copy_comparison_fails(self):
        actual_reader = binding._read_retained_file
        external_reads = 0
        def drifting_reader(path, maximum):
            nonlocal external_reads
            if path == str(self.source):
                external_reads += 1
                if external_reads == 2:
                    return self.raw + b"\n"
            return actual_reader(path, maximum)
        with mock.patch.object(binding, "_read_retained_file", side_effect=drifting_reader):
            failures = self.check(selected=self.alias)[1]
        self.assertTrue(any("changed during selected-copy comparison" in failure for failure in failures))
        self.assertEqual(self.source.read_bytes(), self.raw)

    def test_payload_skip_fields_cannot_bypass_actual_missing_source(self):
        self.source.unlink()
        payload = dict(self.payload, skip_source_binding=True, fixture_root=str(self.directory), source_report_binding_errors=[])
        self.assertTrue(self.check(payload=payload)[1])

    def test_public_dispatcher_folds_binding_failure_and_records_selected_path(self):
        import hd_soak_report as grader
        def data_only(*args, **kwargs):
            return {"overall": True, "checks": {}, "failures": [], "source_report": self.payload["report_json"]}
        # Unit wiring only: actual integration suites exercise the complete
        # retained-artifact grader. The binding here uses real tiny file reads.
        with mock.patch.object(grader, "evaluate_hidden_report", side_effect=data_only):
            positive = grader.evaluate_report_for_environment(self.payload, source_report_path=self.alias)
            self.assertTrue(positive["overall"], positive.get("source_report_binding_errors"))
            self.assertEqual(positive["source_report"], str(self.alias))
            self.alias.write_bytes(self.raw + b"\n")
            changed = grader.evaluate_report_for_environment(self.payload, source_report_path=self.alias)
            self.assertFalse(changed["overall"])
            self.assertFalse(changed["checks"]["source_report_binding"]["passed"])
            self.source.unlink()
            missing = grader.evaluate_report_for_environment(self.payload)
            self.assertFalse(missing["overall"])
            self.assertTrue(missing["source_report_binding_errors"])

    def test_cli_actual_grader_requires_byte_identical_selected_copy(self):
        import hd_soak_report as grader
        from test_hd_soak_report import passing_hidden_report
        from test_hidden_soak_artifact_fixtures import fixture_artifact_reads
        with fixture_artifact_reads():
            report = passing_hidden_report(self.directory)
            original = Path(report["report_json"])
            original_bytes = original.read_bytes()
            self.alias.write_bytes(original_bytes)
            guard_path, markdown_path = self.directory / "guard.json", self.directory / "guard.md"
            command = ["hd_soak_report.py", str(self.alias), "--hidden", "--require-pass",
                       "--write-json", str(guard_path), "--write-markdown", str(markdown_path)]
            with mock.patch.object(sys, "argv", command), redirect_stdout(StringIO()):
                self.assertEqual(grader.main(), 0)
            guard = json.loads(guard_path.read_bytes())
            self.assertTrue(guard["overall"])
            self.assertTrue(guard["checks"]["source_report_binding"]["passed"])
            self.assertEqual(guard["source_report"], str(self.alias))
            self.assertEqual(guard["source_report_sha256"], hashlib.sha256(original_bytes).hexdigest())
            self.alias.write_bytes(original_bytes + b"\n")
            with mock.patch.object(sys, "argv", command), redirect_stdout(StringIO()):
                self.assertEqual(grader.main(), 1)
            guard = json.loads(guard_path.read_bytes())
            self.assertFalse(guard["overall"])
            self.assertFalse(guard["checks"]["source_report_binding"]["passed"])
            for name in ("retained_binary_bytes", "retained_frame_bytes", "retained_log_bytes"):
                self.assertTrue(guard["checks"][name]["passed"], guard["checks"][name])
            self.assertEqual(original.read_bytes(), original_bytes)
            self.assertEqual(json.loads(self.alias.read_bytes())["report_json"], str(original))
            self.assertIn("source_report_binding", markdown_path.read_text(encoding="ascii"))


def run_tests():
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReportBindingTests))
    if not result.wasSuccessful():
        raise AssertionError("hidden source-report binding fixture failures")


if __name__ == "__main__":
    run_tests()
