#!/usr/bin/env python3
"""Fixture tests for the promotion override guard."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "promotion_override_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import promotion_override_guard  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def good_decision(stage: str) -> dict:
    return {
        "passed": True,
        "decision": "defer_stable_promotion",
        "stable_stage_should_change": False,
        "validation_stage": stage,
        "manual_input_proof_supplied": False,
        "manual_input_proof_valid": False,
        "allow_cdb_only_promotion": False,
    }


def good_checklist() -> dict:
    return {
        "passed": True,
        "status": "pending_manual_validation",
        "allow_cdb_only_promotion": False,
        "promotion_ready": False,
        "manual_proof_supplied": False,
        "manual_proof_valid": False,
        "stable_stage_should_change": False,
    }


def write_fixture(
    fixture: Path,
    *,
    right_bottom: dict | None = None,
    castle: dict | None = None,
    checklist: dict | None = None,
) -> argparse.Namespace:
    fixture.mkdir(parents=True, exist_ok=True)
    right_bottom_path = fixture / "right-bottom.json"
    castle_path = fixture / "castle.json"
    checklist_path = fixture / "checklist.json"
    right_bottom_path.write_text(
        json.dumps(right_bottom or good_decision("rightbottomcompose"), indent=2) + "\n",
        encoding="utf-8",
    )
    castle_path.write_text(
        json.dumps(castle or good_decision("castlecenter-all"), indent=2) + "\n",
        encoding="utf-8",
    )
    checklist_path.write_text(
        json.dumps(checklist or good_checklist(), indent=2) + "\n",
        encoding="utf-8",
    )
    return argparse.Namespace(
        right_bottom_decision=right_bottom_path,
        castle_decision=castle_path,
        manual_checklist=checklist_path,
    )


def test_guard_passes_when_overrides_are_inactive(fixture: Path) -> None:
    guard = promotion_override_guard.build_guard(write_fixture(fixture))
    assert guard["passed"] is True, guard
    assert not guard["failures"], guard


def test_guard_rejects_right_bottom_override(fixture: Path) -> None:
    decision = good_decision("rightbottomcompose")
    decision.update(
        {
            "decision": "eligible_for_cdb_only_promotion",
            "stable_stage_should_change": True,
            "allow_cdb_only_promotion": True,
        }
    )
    guard = promotion_override_guard.build_guard(write_fixture(fixture, right_bottom=decision))
    assert guard["passed"] is False, guard
    assert any("right_bottom_compose_promotion_decision" in failure for failure in guard["failures"]), guard
    assert any("allow_cdb_only_promotion is active" in failure for failure in guard["failures"]), guard


def test_guard_allows_nonpassing_deferred_right_bottom_decision(fixture: Path) -> None:
    decision = good_decision("rightbottomcompose")
    decision.update({"passed": False, "failures": ["natural UI proof still pending"]})
    guard = promotion_override_guard.build_guard(write_fixture(fixture, right_bottom=decision))
    assert guard["passed"] is True, guard
    summary = guard["checks"]["right_bottom_compose_promotion_decision"]["summary"]
    assert summary["passed"] is False, guard
    assert summary["stable_stage_should_change"] is False, guard


def test_guard_rejects_castle_override(fixture: Path) -> None:
    decision = good_decision("castlecenter-all")
    decision["allow_cdb_only_promotion"] = True
    guard = promotion_override_guard.build_guard(write_fixture(fixture, castle=decision))
    assert guard["passed"] is False, guard
    assert any("castle_overview_promotion_decision" in failure for failure in guard["failures"]), guard


def test_guard_rejects_manual_checklist_promotion_ready(fixture: Path) -> None:
    checklist = good_checklist()
    checklist.update(
        {
            "allow_cdb_only_promotion": True,
            "promotion_ready": True,
        }
    )
    guard = promotion_override_guard.build_guard(write_fixture(fixture, checklist=checklist))
    assert guard["passed"] is False, guard
    assert any("manual_checklist: allow_cdb_only_promotion is active" in failure for failure in guard["failures"]), guard
    assert any("manual_checklist: promotion_ready is true" in failure for failure in guard["failures"]), guard


def test_guard_rejects_manual_proof_in_current_evidence(fixture: Path) -> None:
    decision = good_decision("rightbottomcompose")
    decision.update({"manual_input_proof_supplied": True, "manual_input_proof_valid": True})
    checklist = good_checklist()
    checklist.update({"manual_proof_supplied": True, "manual_proof_valid": True})
    guard = promotion_override_guard.build_guard(
        write_fixture(fixture, right_bottom=decision, checklist=checklist)
    )
    assert guard["passed"] is False, guard
    assert any("manual_input_proof_valid is true" in failure for failure in guard["failures"]), guard
    assert any("manual_checklist: manual_proof_valid is true" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_json(fixture: Path) -> None:
    args = write_fixture(fixture)
    args.castle_decision.unlink()
    guard = promotion_override_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("missing JSON" in failure for failure in guard["failures"]), guard


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    args = write_fixture(fixture / "good")
    out_json = fixture / "good" / "guard.json"
    out_md = fixture / "good" / "guard.md"
    good = run_script(
        "--right-bottom-decision",
        str(args.right_bottom_decision),
        "--castle-decision",
        str(args.castle_decision),
        "--manual-checklist",
        str(args.manual_checklist),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good.returncode == 0, good.stdout + good.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

    bad_decision = good_decision("castlecenter-all")
    bad_decision["stable_stage_should_change"] = True
    bad_args = write_fixture(fixture / "bad", castle=bad_decision)
    bad_json = fixture / "bad" / "guard.json"
    bad_md = fixture / "bad" / "guard.md"
    bad = run_script(
        "--right-bottom-decision",
        str(bad_args.right_bottom_decision),
        "--castle-decision",
        str(bad_args.castle_decision),
        "--manual-checklist",
        str(bad_args.manual_checklist),
        "--write-json",
        str(bad_json),
        "--write-markdown",
        str(bad_md),
        "--require-pass",
    )
    assert bad.returncode == 2, bad.stdout + bad.stderr
    assert json.loads(bad_json.read_text(encoding="utf-8"))["passed"] is False
    assert "- Overall: FAIL" in bad_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "promotion-override-guard-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_guard_passes_when_overrides_are_inactive(fixture / "passes")
        test_guard_rejects_right_bottom_override(fixture / "right-bottom-override")
        test_guard_allows_nonpassing_deferred_right_bottom_decision(fixture / "right-bottom-defer")
        test_guard_rejects_castle_override(fixture / "castle-override")
        test_guard_rejects_manual_checklist_promotion_ready(fixture / "checklist-ready")
        test_guard_rejects_manual_proof_in_current_evidence(fixture / "manual-proof")
        test_guard_rejects_missing_json(fixture / "missing-json")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("promotion override guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
