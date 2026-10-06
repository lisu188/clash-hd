#!/usr/bin/env python3
"""Mocked refresh collection only; no aggregate suites, runtime or outputs."""
from __future__ import annotations

import ast
from contextlib import ExitStack, contextmanager, redirect_stdout
import hashlib
import inspect
from io import StringIO
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import current_evidence_refresh as refresh


def parsed_args(*options):
    with patch.object(sys, "argv", ["current_evidence_refresh.py", *options]):
        return refresh.parse_args()


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.args = parsed_args()
        self.builders = {
            name: value for name, value in vars(refresh).items()
            if name.startswith("build_") and name != "build_refresh" and inspect.isfunction(value)
        }
        self.records = {
            name: {"passed": True, "summary": {"fixture_builder": name}, "failures": []}
            for name in self.builders
        }
        self.calls = []
        self.snapshots = []

    @contextmanager
    def mocked_builders(self, overrides=None):
        overrides = overrides or {}
        with ExitStack() as stack:
            for name in self.builders:
                def builder(*args, name=name):
                    self.calls.append((name, args))
                    if len(args) == 2:
                        self.snapshots.append((name, args[1], dict(args[1])))
                    if name in overrides:
                        return overrides[name](*args)
                    return self.records[name]
                builder.__name__ = name
                stack.enter_context(patch.object(refresh, name, builder))
            yield

    def build(self, overrides=None):
        with self.mocked_builders(overrides):
            return refresh.build_refresh(self.args)

    def assert_diagnostic(self, report, key, kind, message, attempt=1):
        check = report["checks"][key]
        self.assertIs(check["passed"], False)
        error = check["collection_errors"][attempt - 1]
        self.assertEqual(error["check_key"], key)
        self.assertEqual(error["attempt"], attempt)
        self.assertEqual(error["exception_type"], kind)
        self.assertEqual(error["exception_message"], message)
        self.assertLessEqual(len(error["traceback"]), 16384)
        self.assertIn(kind, error["traceback"])
        self.assertTrue(any(kind in failure and message in failure for failure in check["failures"]))
        self.assertNotIn("json", check)
        self.assertNotIn("markdown", check)
        self.assertNotIn("skipped", check)
        self.assertNotIn("approved", check)
        self.assertNotIn("approval_record", check)
        return error

    def test_all_original_dispatches_order_arguments_and_names_preserved(self):
        # Fixed oracle from the pre-repair coordinator: 169 calls, 167 keys.
        # It includes both repeated dependent calls and the zero-argument runner.
        tree = ast.parse(inspect.getsource(refresh.build_refresh))
        calls = sorted((n for n in ast.walk(tree) if isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Name) and n.func.id == "collect"),
                       key=lambda n: (n.lineno, n.col_offset))
        rows = [(n.args[0].value, n.args[1].id, [a.id for a in n.args[2:]]) for n in calls]
        digest = hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(digest, "f17de72de1d1a03f102a095d454b1c71fd051ddffd60887e2aa0a0dba75dfc3e")
        self.assertEqual(len(rows), 169)
        self.assertEqual(len({row[0] for row in rows}), 167)
        self.assertFalse(any(isinstance(n.func, ast.Name) and n.func.id.startswith("build_")
                             for n in ast.walk(tree) if isinstance(n, ast.Call)))
        report = self.build()
        self.assertEqual([name for name, _ in self.calls], [row[1] for row in rows])
        self.assertEqual(self.calls[0], ("build_framed_offline_refresh", ()))
        for name, args in self.calls[1:]:
            self.assertIs(args[0], self.args, name)
        self.assertEqual(len(report["checks"]), 167)
        self.assertIs(report["passed"], True)

    def test_early_missing_input_keeps_completed_and_later_results(self):
        message = "captures/current/patch-stage-current-hd-map.json is missing"
        def missing(args):
            raise FileNotFoundError(message)
        report = self.build({"build_hd_map_smoke": missing})
        error = self.assert_diagnostic(report, "hd_map_smoke", "FileNotFoundError", message)
        self.assertEqual(error["builder"], "build_hd_map_smoke")
        self.assertIs(report["checks"]["framed_offline_fixtures"], self.records["build_framed_offline_refresh"])
        self.assertIs(report["checks"]["evidence_index_check"], self.records["build_evidence_index_check"])
        self.assertEqual(len(self.calls), 169)
        self.assertIs(report["passed"], False)

    def test_actual_hd_map_builder_exception_is_collected_before_writes(self):
        original = self.builders["build_hd_map_smoke"]
        missing = FileNotFoundError("original missing patch manifest")
        with self.mocked_builders(), patch.object(refresh, "build_hd_map_smoke", original), \
             patch.object(refresh.hd_map_smoke_matrix, "build_matrix", side_effect=missing) as matrix, \
             patch.object(refresh, "write_json") as writer:
            report = refresh.build_refresh(self.args)
        self.assert_diagnostic(report, "hd_map_smoke", "FileNotFoundError", str(missing))
        smoke_args = matrix.call_args.args[0]
        self.assertEqual(smoke_args.patch_report_json, self.args.hd_map_patch_report_json)
        self.assertEqual(smoke_args.normal_run, self.args.normal_run)
        writer.assert_not_called()

    def test_malformed_original_json_keeps_original_exception(self):
        with self.assertRaises(json.JSONDecodeError) as caught:
            json.loads("{malformed")
        original_error = caught.exception
        def malformed(args):
            raise original_error
        report = self.build({"build_hd_layout_summary": malformed})
        self.assert_diagnostic(report, "hd_layout_summary", "JSONDecodeError", str(original_error))
        self.assertIs(report["checks"]["hd_layout_summary_tests"], self.records["build_hd_layout_summary_tests"])

    def test_actual_downstream_guard_malformed_read_keeps_later_checks(self):
        original = self.builders["build_no_visible_runtime_guard"]
        with self.mocked_builders(), patch.object(refresh, "build_no_visible_runtime_guard", original), \
             patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "read_text", return_value="{invalid"):
            report = refresh.build_refresh(self.args)
        check = report["checks"]["no_visible_runtime_guard"]
        self.assertEqual(check["collection_errors"][0]["exception_type"], "JSONDecodeError")
        self.assertIs(report["checks"]["process_hygiene_guard"], self.records["build_process_hygiene_guard"])
        self.assertIs(report["passed"], False)

    def test_missing_middle_and_final_inputs_do_not_abort_collection(self):
        for builder, key in (("build_first_mission_visual_audit", "first_mission_visual_audit"),
                             ("build_evidence_index_check", "evidence_index_check")):
            with self.subTest(key=key):
                self.calls.clear()
                def missing(*args):
                    raise FileNotFoundError("missing " + key)
                report = self.build({builder: missing})
                self.assert_diagnostic(report, key, "FileNotFoundError", "missing " + key)
                self.assertEqual(len(self.calls), 169)
                self.assertEqual(self.calls[-1][0], "build_current_completion_summary")

    def test_downstream_checks_receive_same_partial_dictionary_and_namespace(self):
        def missing(args):
            raise FileNotFoundError("missing raw input")
        report = self.build({"build_hd_map_smoke": missing})
        expected = {"build_right_bottom_compose_decision", "build_right_bottom_compose_matrix",
                    "build_no_visible_runtime_guard", "build_no_popup_boundary_guard",
                    "build_docs_consistency_guard", "build_current_completion_summary"}
        self.assertEqual({name for name, _, _ in self.snapshots}, expected)
        for name, checks, snapshot in self.snapshots:
            self.assertIs(checks, report["checks"], name)
            self.assertIs(snapshot["hd_map_smoke"]["passed"], False, name)
            self.assertEqual(snapshot["hd_map_smoke"]["collection_errors"][0]["exception_type"], "FileNotFoundError")

    def test_repeated_check_first_exception_stays_false_after_success(self):
        for builder, key in (("build_no_popup_boundary_guard", "no_popup_boundary_guard"),
                             ("build_current_completion_summary", "current_completion_summary")):
            with self.subTest(key=key):
                count = 0
                def retry(*args):
                    nonlocal count
                    count += 1
                    if count == 1:
                        raise ValueError("first attempt failed")
                    return self.records[builder]
                report = self.build({builder: retry})
                self.assertEqual(count, 2)
                self.assert_diagnostic(report, key, "ValueError", "first attempt failed")
                self.assertIs(report["passed"], False)
                self.assertIs(self.records[builder]["passed"], True)
                self.assertNotIn("collection_errors", self.records[builder])
                if key == "no_popup_boundary_guard":
                    final_summary = [snapshot for name, _, snapshot in self.snapshots
                                     if name == "build_current_completion_summary"][-1]
                    self.assertIs(final_summary[key]["passed"], False)

    def test_repeated_check_preserves_both_original_exceptions(self):
        count = 0
        def fail(*args):
            nonlocal count
            count += 1
            if count == 1:
                raise FileNotFoundError("first original")
            raise RuntimeError("second original")
        report = self.build({"build_no_popup_boundary_guard": fail})
        errors = report["checks"]["no_popup_boundary_guard"]["collection_errors"]
        self.assertEqual([(e["attempt"], e["exception_type"], e["exception_message"]) for e in errors],
                         [(1, "FileNotFoundError", "first original"), (2, "RuntimeError", "second original")])

    def test_normal_success_and_existing_evidence_failure_are_preserved(self):
        record = {"passed": False, "summary": {"stable_stage_should_change": False},
                  "failures": ["existing evidence rejection"], "json": "original-report.json"}
        self.records["build_stable_stage_guard"] = record
        report = self.build()
        self.assertIs(report["checks"]["stable_stage_guard"], record)
        self.assertIs(report["checks"]["hd_map_smoke"], self.records["build_hd_map_smoke"])
        self.assertEqual(report["failures"], ["stable_stage_guard: existing evidence rejection"])
        self.assertNotIn("collection_errors", record)

    def test_malformed_return_records_fail_before_summary_rendering(self):
        invalid = (None, [], {"passed": "true"}, {"passed": True, "summary": []},
                   {"passed": True, "failures": "wrong"}, {"passed": True, "failures": [1]},
                   {"passed": True, "summary": {"unwritable": object()}})
        for record in invalid:
            with self.subTest(record=record):
                report = self.build({"build_hd_map_smoke": lambda args: record})
                error = report["checks"]["hd_map_smoke"]["collection_errors"][0]
                self.assertEqual(error["exception_type"], "TypeError")
                self.assertIs(report["passed"], False)
                with redirect_stdout(StringIO()):
                    refresh.print_refresh(report)
                json.dumps(report)

    def test_traceback_is_bounded_while_original_message_is_preserved(self):
        message = "original failure " + "X" * 50000
        def fail(args):
            raise RuntimeError(message)
        report = self.build({"build_hd_map_smoke": fail})
        error = report["checks"]["hd_map_smoke"]["collection_errors"][0]
        self.assertEqual(error["exception_message"], message)
        self.assertEqual(len(error["traceback"]), 16384)
        self.assertIs(error["traceback_truncated"], True)

    def test_exception_cause_remains_in_traceback(self):
        def fail(args):
            try:
                json.loads("{original malformed JSON")
            except json.JSONDecodeError as cause:
                raise FileNotFoundError("original downstream failure") from cause
        report = self.build({"build_hd_map_smoke": fail})
        trace = report["checks"]["hd_map_smoke"]["collection_errors"][0]["traceback"]
        self.assertIn("JSONDecodeError", trace)
        self.assertIn("FileNotFoundError", trace)
        self.assertIn("original downstream failure", trace)

    def test_system_exit_and_keyboard_interrupt_are_not_swallowed(self):
        for kind in (SystemExit, KeyboardInterrupt):
            with self.subTest(kind=kind):
                def interrupted(args):
                    raise kind("stop requested")
                with self.mocked_builders({"build_hd_map_smoke": interrupted}):
                    with self.assertRaises(kind):
                        refresh.build_refresh(self.args)

    def test_cli_overrides_and_runtime_policy_are_forwarded_unchanged(self):
        self.args = parsed_args("--normal-run", "selected-normal", "--forced-run", "selected-forced",
                                "--hd-map-patch-report-json", "selected-patch.json",
                                "--manual-directinput-proof", "selected-proof.json",
                                "--promotion-override-manifest", "selected-override.json",
                                "--hd-soak-report", "selected-soak.json",
                                "--hd-soak-first-step-report", "selected-first-step.json",
                                "--write-json", "selected-refresh.json", "--write-markdown", "selected-refresh.md")
        report = self.build()
        for name, args in self.calls[1:]:
            self.assertIs(args[0], self.args, name)
        self.assertEqual(self.args.hd_map_patch_report_json, Path("selected-patch.json"))
        self.assertEqual(self.args.manual_directinput_proof, Path("selected-proof.json"))
        self.assertEqual(self.args.promotion_override_manifest, Path("selected-override.json"))
        self.assertFalse(self.args.allow_manual_directinput_cdb_only_promotion)
        self.assertFalse(self.args.allow_right_bottom_compose_cdb_only_promotion)
        self.assertEqual(report["runtime_policy"],
                         "repo/local metadata only; does not launch Clash95, CDB, wrappers, or visible windows")

    def test_main_preserves_exit_policy_and_writes_failed_summary(self):
        def missing(args):
            raise FileNotFoundError("missing source evidence")
        for required, expected in ((False, 0), (True, 2)):
            with self.subTest(required=required):
                self.args.require_pass = required
                events = []
                with self.mocked_builders({"build_hd_map_smoke": missing}), \
                     patch.object(refresh, "parse_args", return_value=self.args), \
                     patch.object(refresh, "print_refresh", side_effect=lambda r: events.append(("print", r))), \
                     patch.object(refresh, "write_json", side_effect=lambda p, r: events.append(("json", p, r))), \
                     patch.object(refresh, "write_markdown", side_effect=lambda p, r: events.append(("markdown", p, r))):
                    self.assertEqual(refresh.main(), expected)
                self.assertEqual([event[0] for event in events], ["print", "json", "markdown"])
                self.assertIs(events[0][1], events[1][2])
                self.assertIs(events[1][2], events[2][2])
                self.assertIs(events[0][1]["passed"], False)
                self.assertEqual(events[1][1], self.args.write_json)
                self.assertEqual(events[2][1], self.args.write_markdown)

    def test_real_serializers_and_print_render_diagnostics_without_files(self):
        def missing(args):
            raise FileNotFoundError("missing manifest retained")
        report = self.build({"build_hd_map_smoke": missing})
        with patch.object(Path, "mkdir"), patch.object(Path, "write_text") as write:
            refresh.write_json(Path("fixture-report.json"), report)
            json_record = json.loads(write.call_args.args[0])
            self.assertIs(json_record["checks"]["hd_map_smoke"]["passed"], False)
            refresh.write_markdown(Path("fixture-report.md"), report)
            self.assertIn("FileNotFoundError: missing manifest retained", write.call_args.args[0])
        output = StringIO()
        with redirect_stdout(output):
            refresh.print_refresh(report)
        self.assertIn("hd_map_smoke: FAIL", output.getvalue())
        self.assertIn("FileNotFoundError: missing manifest retained", output.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
