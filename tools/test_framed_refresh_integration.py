"""Aggregate coverage must retain missing, skipped and failed framed checks."""
import unittest
from unittest.mock import patch

import current_evidence_refresh as refresh
import run_framed_offline_tests as framed


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


if __name__ == "__main__":
    unittest.main()
