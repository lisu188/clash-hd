"""Aggregate coverage must retain missing, skipped and failed framed checks."""
import unittest
from unittest.mock import patch

import current_evidence_refresh as refresh
import run_framed_offline_tests as framed
from test_run_framed_offline_tests import EVIDENCE_SUITES


class AggregateTests(unittest.TestCase):
    def row(self, status="passed"):
        return {"suite": "fixture", "status": status, "successful": ["test_one"],
                "discovered": 1, "skipped": [], "expected_failures": []}

    def run_fixture(self, row, preflight=True):
        with patch.object(framed, "SUITES", ("fixture",)), \
             patch.object(framed, "source_preflight", return_value={"passed": preflight}), \
             patch.object(framed, "run_suite", return_value=row) as run:
            report = refresh.build_framed_offline_refresh()
            self.assertEqual(run.call_count, int(preflight))
            return report

    def test_only_complete_success_passes(self):
        self.assertTrue(self.run_fixture(self.row())["passed"])
        for status in ("failed", "skipped", "incomplete"):
            report = self.run_fixture(self.row(status))
            self.assertFalse(report["passed"])
            self.assertFalse(report["promotion_ready"])
            self.assertEqual(report["suites"][0]["status"], status)

    def test_source_failure_stops_execution_and_stays_failed(self):
        report = self.run_fixture(self.row(), preflight=False)
        self.assertFalse(report["passed"])
        self.assertEqual(report["suites"], [])

    def test_current_registry_forwards_each_integrated_evidence_suite_once(self):
        for name in EVIDENCE_SUITES:
            self.assertEqual(framed.SUITES.count(name), 1, name)
        def success(root, name, timeout):
            return self.row() | {"suite": name}
        with patch.object(framed, "source_preflight", return_value={"passed": True}), \
             patch.object(framed, "run_suite", side_effect=success) as run:
            report = refresh.build_framed_offline_refresh()
        self.assertEqual([call.args[1] for call in run.call_args_list], list(framed.SUITES))
        self.assertEqual([row["suite"] for row in report["suites"]], list(framed.SUITES))
        self.assertTrue(report["passed"])
        self.assertTrue(report["full_suite_selected"])
        self.assertFalse(report["game_runtime_executed"])

    def test_integrated_evidence_failure_or_missing_platform_coverage_stays_incomplete(self):
        for name in EVIDENCE_SUITES:
            for status in ("failed", "skipped"):
                def outcome(root, suite, timeout):
                    if suite != name:
                        return self.row() | {"suite": suite}
                    row = self.row(status) | {"suite": suite, "successful": []}
                    if status == "failed":
                        row["errors"] = [{"test": name + ".case", "traceback": "fixture failed"}]
                    else:
                        row["skipped"] = [{"test": name + ".case", "reason": "PowerShell unavailable"}]
                    return row
                with self.subTest(suite=name, status=status), \
                     patch.object(framed, "source_preflight", return_value={"passed": True}), \
                     patch.object(framed, "run_suite", side_effect=outcome):
                    report = refresh.build_framed_offline_refresh()
                    self.assertFalse(report["passed"])
                    self.assertFalse(report["selected_coverage_complete"])
                    retained = next(row for row in report["suites"] if row["suite"] == name)
                    self.assertEqual(retained["status"], status)
                    self.assertEqual(len(retained["errors" if status == "failed" else "skipped"]), 1)


if __name__ == "__main__":
    unittest.main()
