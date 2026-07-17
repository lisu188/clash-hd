#!/usr/bin/env python3
"""Fixture tests for right_bottom_visual_artifact_guard.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "right_bottom_visual_artifact_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import right_bottom_visual_artifact_guard  # noqa: E402


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def good_payloads() -> dict[str, dict]:
    compose = {
        "passed": True,
        "promotion_status": "validation_stage_only",
        "stable_stage_should_change": False,
        "checks": {
            "right_bottom_compose_fullstart_route": {
                "passed": True,
                "summary": {
                    "bottom_right_ui_corner_nonblack": 48.0,
                    "bottom_right_tile_r8c10_nonblack": 54.0,
                    "bottom_right_tile_r8c11_nonblack": 42.0,
                    "av_count": 0,
                },
            },
            "right_bottom_compose_ui_probe": {
                "passed": True,
                "summary": {
                    "rbui_markers_seen": True,
                    "rbui_desc_switch": 0,
                    "rbui_viewport_switch": 1,
                    "rbui_panel_draw": 0,
                    "rbui_action_box": 0,
                    "av_count": 0,
                    "natural_draw_source": "slot5_as_slot0_fixture",
                    "fixture": {
                        "ruling": right_bottom_visual_artifact_guard.FIXTURE_NATURAL_DRAW_RULING,
                        "fixture_run": "captures/archive/cdb-surface-dump-20260712-155528",
                        "marker_counts": {
                            "NOWNER_435BC0_PANEL_DRAW": 1,
                            "NOWNER_435BC0_GRID_DRAW": 10,
                            "NOWNER_WRAPPER_COPYBACK_DONE": 1,
                            "NOWNER_WRAPPER_PRESENT_CALL": 1,
                        },
                        "av_count": 0,
                        "proof_class": "non_natural_isolated_fixture",
                        "expected_slot_match": True,
                    },
                    "bounds": {
                        "bottom_right_ui_corner": {
                            "nonblack_percent": 21.43,
                            "black_percent": 78.57,
                            "flags": ["large_black_component", "black_touches_bottom_right"],
                        },
                        "bottom_right_tile_r8c10": {
                            "nonblack_percent": 0.0,
                            "black_percent": 100.0,
                            "flags": ["mostly_black", "large_black_component", "black_touches_bottom_right"],
                        },
                        "bottom_right_tile_r8c11": {
                            "nonblack_percent": 0.0,
                            "black_percent": 100.0,
                            "flags": ["mostly_black", "large_black_component", "black_touches_bottom_right"],
                        },
                        "right_side_below_minimap": {
                            "nonblack_percent": 23.593,
                            "black_percent": 76.407,
                            "flags": ["large_black_component", "black_touches_bottom_right"],
                        },
                    },
                },
            },
        },
    }
    triage = {
        "passed": True,
        "classification": "controlled_recovered_but_natural_route_nonpromoting",
        "promotion_ready": False,
        "stable_stage_should_change": False,
    }
    return {"compose": compose, "triage": triage}


def write_payloads(fixture: Path, payloads: dict[str, dict] | None = None) -> dict[str, Path]:
    payloads = payloads or good_payloads()
    return {
        "compose": write_json(fixture / "compose.json", payloads["compose"]),
        "triage": write_json(fixture / "triage.json", payloads["triage"]),
    }


def build_from_paths(paths: dict[str, Path]) -> dict:
    return right_bottom_visual_artifact_guard.build_guard(
        compose_evidence_json=paths["compose"],
        blocker_triage_json=paths["triage"],
    )


def ui_summary(payloads: dict[str, dict]) -> dict:
    return payloads["compose"]["checks"]["right_bottom_compose_ui_probe"]["summary"]


def test_good_resolved_state_passes(fixture: Path) -> None:
    report = build_from_paths(write_payloads(fixture))
    assert report["passed"] is True, report
    assert report["visual_status"] == "fixture_natural_draw_accepted", report
    assert report["promotion_ready"] is False, report
    assert report["stable_stage_should_change"] is False, report
    assert "user ruling 2026-07-14" in report["fixture_ruling"], report


def test_missing_triage_fails(fixture: Path) -> None:
    paths = write_payloads(fixture)
    paths["triage"].unlink()
    report = build_from_paths(paths)
    assert report["passed"] is False, report
    assert any("missing right-bottom blocker triage" in failure for failure in report["failures"]), report


def test_legacy_blocked_classification_is_still_accepted(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["triage"]["classification"] = "controlled_recovered_but_natural_route_blocked"
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is True, report
    assert report["promotion_ready"] is False, report


def test_fixture_evidence_missing_fails_closed(fixture: Path) -> None:
    payloads = good_payloads()
    summary = ui_summary(payloads)
    summary.pop("natural_draw_source")
    summary.pop("fixture")
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is False, report
    assert any("fixture_natural_draw_accepted" in failure for failure in report["failures"]), report


def test_fixture_marker_regression_fails_closed(fixture: Path) -> None:
    for marker in (
        "NOWNER_435BC0_PANEL_DRAW",
        "NOWNER_435BC0_GRID_DRAW",
        "NOWNER_WRAPPER_COPYBACK_DONE",
    ):
        payloads = deepcopy(good_payloads())
        ui_summary(payloads)["fixture"]["marker_counts"][marker] = 0
        report = build_from_paths(write_payloads(fixture / marker.lower(), payloads))
        assert report["passed"] is False, report
        assert any("fixture_natural_draw_accepted" in failure for failure in report["failures"]), report


def test_fixture_av_rows_fail_closed(fixture: Path) -> None:
    payloads = good_payloads()
    ui_summary(payloads)["fixture"]["av_count"] = 1
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is False, report
    assert any("fixture_natural_draw_accepted" in failure for failure in report["failures"]), report


def test_compose_matrix_not_passing_fails(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["compose"]["passed"] = False
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is False, report
    assert any(
        "compose_matrix_passing_promotion_deferred" in failure for failure in report["failures"]
    ), report


def test_promotion_flip_fails_closed(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["compose"]["stable_stage_should_change"] = True
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is False, report
    assert any(
        "compose_matrix_passing_promotion_deferred" in failure for failure in report["failures"]
    ), report


def test_controlled_recovery_regression_fails(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["compose"]["checks"]["right_bottom_compose_fullstart_route"]["summary"][
        "bottom_right_tile_r8c11_nonblack"
    ] = 5.0
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is False, report
    assert any("controlled_composition_recovered" in failure for failure in report["failures"]), report


def test_cli_writes_outputs(fixture: Path) -> None:
    paths = write_payloads(fixture)
    out_json = fixture / "out" / "guard.json"
    out_md = fixture / "out" / "guard.md"
    run = run_script(
        "--compose-evidence-json",
        str(paths["compose"]),
        "--blocker-triage-json",
        str(paths["triage"]),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "Right-Bottom Visual Artifact Guard" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "right-bottom-visual-artifact-guard-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_resolved_state_passes(fixture / "good")
        test_missing_triage_fails(fixture / "missing-triage")
        test_legacy_blocked_classification_is_still_accepted(fixture / "legacy-classification")
        test_fixture_evidence_missing_fails_closed(fixture / "fixture-missing")
        test_fixture_marker_regression_fails_closed(fixture / "fixture-markers")
        test_fixture_av_rows_fail_closed(fixture / "fixture-av")
        test_compose_matrix_not_passing_fails(fixture / "compose-failing")
        test_promotion_flip_fails_closed(fixture / "promotion-flip")
        test_controlled_recovery_regression_fails(fixture / "controlled-regression")
        test_cli_writes_outputs(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("right-bottom visual artifact guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
