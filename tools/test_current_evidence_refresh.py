#!/usr/bin/env python3
"""Fixture tests for current_evidence_refresh soak report selection."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import current_evidence_refresh as refresh
import hd_soak_report


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="ascii")
    return path


def pending_report() -> dict[str, Any]:
    return {
        "executed": False,
        "passed": False,
        "runtime_policy": "opt-in visible runtime soak; use -Execute only after approval",
        "stage": hd_soak_report.PROTECTED_STABLE_STAGE,
        "stable_stage_should_change": False,
        "tier": "short2",
        "route": "menu-idle",
        "duration_sec": 120,
        "candidate": r"C:\ClashTests\hd-soak\pending.exe",
        "output_directory": r"C:\ClashCaptures\hd-soak\pending",
        "final_route_marker": "pending_approval",
        "failures": ["short2 menu-idle soak was not executed because visible-runtime escalation was not approved"],
        "execution_blocked_reason": "visible-runtime run requires explicit user approval",
    }


def args_for(tmp: Path, legacy: Path, canonical: Path) -> argparse.Namespace:
    return argparse.Namespace(
        hd_soak_report=legacy,
        hd_soak_first_step_report=canonical,
        hd_soak_report_guard_json=tmp / "guard.json",
        hd_soak_report_guard_md=tmp / "guard.md",
        hd_soak_failure_triage_json=tmp / "triage.json",
        hd_soak_failure_triage_md=tmp / "triage.md",
    )


def test_legacy_report_selected_when_canonical_missing() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        legacy = write_json(tmp / "legacy.json", pending_report())
        canonical = tmp / "canonical.json"
        args = args_for(tmp, legacy, canonical)
        selected, source = refresh.selected_hd_soak_report_path(args)
        metadata = refresh.hd_soak_report_selection_metadata(args, selected, source)
    assert selected == legacy
    assert source == "legacy_compatibility"
    assert metadata["canonical_first_step_report"] == str(canonical)
    assert metadata["canonical_first_step_present"] is False
    assert metadata["legacy_report"] == str(legacy)
    assert metadata["legacy_report_present"] is True
    assert metadata["canonical_runtime_report_missing"] is True


def test_canonical_first_step_report_selected_when_present() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        legacy = write_json(tmp / "legacy.json", pending_report())
        canonical = write_json(tmp / "canonical.json", pending_report())
        args = args_for(tmp, legacy, canonical)
        selected, source = refresh.selected_hd_soak_report_path(args)
        metadata = refresh.hd_soak_report_selection_metadata(args, selected, source)
    assert selected == canonical
    assert source == "canonical_first_short_step"
    assert metadata["canonical_first_step_report"] == str(canonical)
    assert metadata["canonical_first_step_present"] is True
    assert metadata["legacy_report"] == str(legacy)
    assert metadata["legacy_report_present"] is True
    assert metadata["canonical_runtime_report_missing"] is False


def test_report_guard_and_triage_use_canonical_first_step_when_present() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        legacy = write_json(tmp / "legacy.json", pending_report())
        canonical = write_json(tmp / "canonical.json", pending_report())
        args = args_for(tmp, legacy, canonical)
        guard = refresh.build_hd_soak_report_guard(args)
        triage = refresh.build_hd_soak_failure_triage(args)
    assert guard["summary"]["source_report"] == str(canonical)
    assert guard["summary"]["source_report_selection"] == "canonical_first_short_step"
    assert guard["summary"]["canonical_first_step_report"] == str(canonical)
    assert guard["summary"]["canonical_first_step_present"] is True
    assert guard["summary"]["canonical_runtime_report_missing"] is False
    assert triage["summary"]["source_report"] == str(canonical)
    assert triage["summary"]["source_report_selection"] == "canonical_first_short_step"
    assert triage["summary"]["canonical_first_step_report"] == str(canonical)
    assert triage["summary"]["canonical_first_step_present"] is True
    assert triage["summary"]["canonical_runtime_report_missing"] is False
    assert triage["summary"]["classification"] == "not_executed_pending_approval"


def run_tests() -> None:
    test_legacy_report_selected_when_canonical_missing()
    test_canonical_first_step_report_selected_when_present()
    test_report_guard_and_triage_use_canonical_first_step_when_present()


if __name__ == "__main__":
    run_tests()
    print("current_evidence_refresh tests passed")
