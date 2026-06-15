#!/usr/bin/env python3
"""Fixture tests for battle slot scan aggregation."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import battle_slot_scan_summary as slot_scan  # noqa: E402


def test_infer_slot_prefers_summary_load_slot() -> None:
    text = "SURFDUMP_LOADSAVE selected_arg=2 selected_global=2"
    assert slot_scan.infer_slot({"LoadSlot": 4}, text) == 4


def test_infer_slot_uses_loadsave_when_summary_missing() -> None:
    text = "SURFDUMP_LOADSAVE selected_arg=2 selected_global=2"
    assert slot_scan.infer_slot({}, text) == 2


def test_classify_run_reports_enabled_units() -> None:
    result = slot_scan.classify_run({"TimedOut": False}, "", unit_count=3, natural_enabled_count=1)
    assert result == "routed-natural-enabled"


def test_classify_run_reports_timeout_before_scan() -> None:
    result = slot_scan.classify_run({"TimedOut": True}, "", unit_count=0, natural_enabled_count=0)
    assert result == "timeout-before-unit-scan"


def run_tests() -> None:
    test_infer_slot_prefers_summary_load_slot()
    test_infer_slot_uses_loadsave_when_summary_missing()
    test_classify_run_reports_enabled_units()
    test_classify_run_reports_timeout_before_scan()


def main() -> int:
    run_tests()
    print("battle slot scan summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
