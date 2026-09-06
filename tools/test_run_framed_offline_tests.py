#!/usr/bin/env python3
"""Synthetic, repository-only tests for the framed fixture runner."""
from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import run_framed_offline_tests as runner

NAME = "test_framed_viewport"
PASS = "import unittest\nclass Fixture(unittest.TestCase):\n def test_ok(self): self.assertEqual(2 + 2, 4)\n"
SKIP = "import unittest\n@unittest.skip('needs an unavailable fixture')\nclass Fixture(unittest.TestCase):\n def test_a(self): pass\n def test_b(self): pass\n"


class OfflineRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="hd-runner-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "tools").mkdir()
        (self.root / "src").mkdir()
        shutil.copyfile(runner.__file__, self.root / "tools" / Path(runner.__file__).name)
        self.source = self.root / "src" / "source.py"
        self.minimap = self.root / "src" / "minimap.py"
        self.source.write_bytes(b"VALUE = 1\r\n")
        self.minimap.write_bytes(b"VALUE = 2\n")
        self.write_builder()
        self.write_suite(PASS)

    def write_builder(self, pins=None, extra=""):
        if pins is None:
            pins = {"src/source.py": hashlib.sha256(self.source.read_bytes()).hexdigest()}
        text = (f"PINNED_SOURCES = {pins!r}\nMINIMAP_SOURCE = 'src/minimap.py'\n"
                f"MINIMAP_SOURCE_SHA256 = {runner.digest(self.minimap.read_bytes())!r}\n" + extra)
        (self.root / runner.BUILDER).write_text(text, encoding="utf-8")

    def write_suite(self, text):
        (self.root / "tools" / f"{NAME}.py").write_text(text, encoding="utf-8")

    def run_one(self, timeout=10):
        return runner.run_suite(self.root, NAME, timeout)

    def invoke(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(self.root / "tools" / Path(runner.__file__).name), *args],
            cwd=self.root, capture_output=True, text=True, encoding="utf-8", timeout=20, check=False)

    def test_preflight_authenticates_both_optional_and_required_sources(self):
        result = runner.source_preflight(self.root)
        self.assertTrue(result["passed"])
        self.assertEqual(set(result["checks"]), {"src/source.py", "src/minimap.py"})
        self.assertEqual(len(result["builder_sha256"]), 64)

    def test_preflight_does_not_import_or_execute_builder(self):
        self.write_builder(extra="raise AssertionError('builder must not execute')\n")
        self.assertTrue(runner.source_preflight(self.root)["passed"])

    def test_preflight_detects_line_ending_changes_without_repinning(self):
        builder = (self.root / runner.BUILDER).read_bytes()
        self.source.write_bytes(b"VALUE = 1\n")
        result = runner.source_preflight(self.root)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["src/source.py"]["passed"])
        self.assertEqual((self.root / runner.BUILDER).read_bytes(), builder)

    def test_missing_minimap_is_not_silently_optional(self):
        self.minimap.unlink()
        result = runner.source_preflight(self.root)
        self.assertFalse(result["passed"])
        self.assertIn("error", result["checks"]["src/minimap.py"])

    def test_missing_builder_fails_closed(self):
        (self.root / runner.BUILDER).unlink()
        self.assertFalse(runner.source_preflight(self.root)["passed"])

    def test_bad_pin_definitions_fail_closed(self):
        for pins in ({}, {"src/source.py": "not-a-sha"}, {"src/source.py": 4}, []):
            with self.subTest(pins=pins):
                self.write_builder(pins=pins)
                self.assertFalse(runner.source_preflight(self.root)["passed"])

    def test_computed_or_duplicate_pins_fail_without_execution(self):
        for extra in ("PINNED_SOURCES = {}\n", "MINIMAP_SOURCE = str('src/minimap.py')\n"):
            with self.subTest(extra=extra):
                self.write_builder(extra=extra)
                self.assertFalse(runner.source_preflight(self.root)["passed"])
        (self.root / runner.BUILDER).write_text("PINNED_SOURCES = dict()\n", encoding="utf-8")
        self.assertFalse(runner.source_preflight(self.root)["passed"])

    def test_conflicting_minimap_pin_fails(self):
        self.write_builder(pins={"src/minimap.py": "0" * 64})
        self.assertFalse(runner.source_preflight(self.root)["passed"])

    def test_paths_reject_escape_absolute_backslash_and_noncanonical_names(self):
        for name in ("../other.py", "/tmp/other.py", "src/../source.py", "src\\source.py",
                     "./src/source.py", "src/source.json", "src//source.py", 123):
            with self.subTest(name=name), self.assertRaises(ValueError):
                runner.source_path(self.root, name)

    def test_preflight_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "source.py"
            target.write_bytes(self.source.read_bytes())
            self.source.unlink()
            try:
                self.source.symlink_to(target)
            except OSError:
                self.skipTest("symlink creation is unavailable")
            result = runner.source_preflight(self.root)
            self.assertFalse(result["passed"])
            self.assertIn("escapes", result["checks"]["src/source.py"]["error"])

    def test_worker_records_real_successes(self):
        result = self.run_one()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["discovered"], 1)
        self.assertEqual(result["tests_run"], 1)
        self.assertEqual(len(result["successful"]), 1)
        self.assertEqual(result["skipped"], [])

    def test_worker_separates_class_skips_from_success(self):
        self.write_suite(SKIP)
        result = self.run_one()
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["discovered"], 2)
        self.assertEqual(result["successful"], [])
        self.assertEqual(len(result["skipped"]), 2)
        self.assertIn("unavailable fixture", result["skipped"][0]["reason"])

    def test_worker_reports_class_setup_skip_without_inventing_success(self):
        self.write_suite("import unittest\nclass Fixture(unittest.TestCase):\n @classmethod\n"
                         " def setUpClass(cls): raise unittest.SkipTest('no original')\n"
                         " def test_a(self): pass\n def test_b(self): pass\n")
        result = self.run_one()
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["discovered"], 2)
        self.assertEqual(result["successful"], [])
        self.assertEqual(len(result["skipped"]), 1)

    def test_failure_traceback_survives_worker(self):
        self.write_suite(PASS.replace("2 + 2, 4", "2 + 2, 5"))
        result = self.run_one()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(result["failures"]), 1)
        self.assertIn("4 != 5", result["failures"][0]["traceback"])
        self.assertIn("FAILED", result["output_tail"])

    def test_import_error_is_a_failure(self):
        self.write_suite("raise ImportError('fixture dependency missing')\n")
        result = self.run_one()
        self.assertEqual(result["status"], "failed")
        self.assertIn("fixture dependency missing", result["errors"][0]["traceback"])

    def test_zero_exit_without_worker_report_fails(self):
        self.write_suite("raise SystemExit(0)\n")
        result = self.run_one()
        self.assertEqual(result["status"], "failed")
        self.assertIn("error", result)

    def test_empty_module_fails(self):
        self.write_suite("VALUE = 1\n")
        result = self.run_one()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["discovered"], 0)

    def test_timeout_is_recorded_and_not_a_pass(self):
        self.write_suite("import time\ntime.sleep(60)\n" + PASS)
        result = self.run_one(timeout=0.2)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["timed_out"])

    def test_worker_stdout_cannot_corrupt_json(self):
        self.write_suite("print('not json')\n" + PASS)
        self.assertEqual(self.run_one()["status"], "passed")

    def test_expected_failure_is_not_complete_coverage(self):
        self.write_suite(PASS.replace(" def test_ok", " @unittest.expectedFailure\n def test_ok")
                         .replace("2 + 2, 4", "2 + 2, 5"))
        row = self.run_one()
        self.assertEqual(row["status"], "incomplete")
        self.assertEqual(len(row["expected_failures"]), 1)
        self.assertFalse(runner.summarize({"passed": True}, [row], (NAME,))["offline_passed"])

    def test_unexpected_success_fails(self):
        self.write_suite(PASS.replace(" def test_ok", " @unittest.expectedFailure\n def test_ok"))
        row = self.run_one()
        self.assertEqual(row["status"], "failed")
        self.assertEqual(len(row["unexpected_successes"]), 1)

    def test_summary_distinguishes_partial_coverage_and_runtime(self):
        row = {"status": "passed", "discovered": 2, "successful": ["one"],
               "skipped": [{"test": "two", "reason": "no original"}]}
        report = runner.summarize({"passed": True}, [row], (NAME,))
        self.assertTrue(report["offline_passed"])
        for key in ("selected_coverage_complete", "full_suite_selected", "game_runtime_executed",
                    "manual_input_proof", "promotion_ready"):
            self.assertFalse(report[key])
        self.assertFalse(runner.summarize({"passed": True}, [], (NAME,))["offline_passed"])
        self.assertFalse(runner.summarize({"passed": False}, [row], (NAME,))["offline_passed"])

    def test_cli_strict_mode_rejects_skipped_cases(self):
        self.write_suite(PASS + "\n@unittest.skip('not present')\nclass Other(unittest.TestCase):\n def test_skip(self): pass\n")
        ordinary = self.invoke("--suite", NAME)
        strict = self.invoke("--suite", NAME, "--require-complete")
        self.assertEqual(ordinary.returncode, 0, ordinary.stderr)
        self.assertEqual(strict.returncode, 1, strict.stderr)
        self.assertTrue(json.loads(ordinary.stdout)["offline_passed"])
        self.assertFalse(json.loads(strict.stdout)["selected_coverage_complete"])

    def test_cli_preflight_failure_runs_no_suites(self):
        self.source.write_bytes(b"changed\n")
        with patch.object(runner, "ROOT", self.root), patch.object(runner, "run_suite") as run:
            with patch.object(sys, "argv", ["runner", "--suite", NAME]), redirect_stdout(io.StringIO()):
                self.assertEqual(runner.main(), 1)
            run.assert_not_called()

    def test_cli_report_matches_stdout_and_retains_selection(self):
        target = self.root / "reports" / "result.json"
        process = self.invoke("--suite", NAME, "--suite", NAME, "--report-json", str(target))
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(report, json.loads(process.stdout))
        self.assertEqual(report["selected_suites"], [NAME])
        self.assertTrue(report["selected_coverage_complete"])

    def test_malformed_worker_records_fail_closed(self):
        good = self.run_one()
        runner.validate_record(good, NAME)
        for changes in ({"suite": "other"}, {"discovered": True}, {"tests_run": -1},
                        {"successful": "not-a-list"}, {"status": "skipped"},
                        {"failures": [{"test": "one", "traceback": "broken"}]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                runner.validate_record(good | changes, NAME)

    def test_json_report_does_not_follow_existing_symlink(self):
        original = self.root / "original.exe"
        original.write_bytes(b"synthetic untouched bytes")
        target = self.root / "report.json"
        try:
            target.symlink_to(original)
        except OSError:
            self.skipTest("symlink creation is unavailable")
        process = self.invoke("--suite", NAME, "--report-json", str(target))
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(original.read_bytes(), b"synthetic untouched bytes")
        self.assertFalse(target.is_symlink())
        self.assertTrue(json.loads(target.read_text(encoding="utf-8"))["offline_passed"])


    def test_cli_rejects_invalid_timeout_unknown_suite_and_non_json_output(self):
        for args in (("--timeout", "0"), ("--timeout", "nan"), ("--timeout", "inf"),
                     ("--suite", "test_arbitrary"), ("--report-json", "clash95.exe")):
            with self.subTest(args=args):
                self.assertEqual(self.invoke(*args).returncode, 2)


if __name__ == "__main__":
    unittest.main()
