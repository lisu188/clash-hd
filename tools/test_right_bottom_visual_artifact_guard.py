#!/usr/bin/env python3
"""Fixture tests for right_bottom_visual_artifact_guard.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
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
        "passed": False,
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
                "passed": False,
                "summary": {
                    "rbui_markers_seen": True,
                    "rbui_desc_switch": 35,
                    "rbui_viewport_switch": 1,
                    "rbui_panel_draw": 0,
                    "rbui_action_box": 0,
                    "av_count": 0,
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


def test_good_visual_blocker_passes(fixture: Path) -> None:
    report = build_from_paths(write_payloads(fixture))
    assert report["passed"] is True, report
    assert report["visual_status"] == "natural_ui_visual_artifact_blocked", report
    assert report["promotion_ready"] is False, report


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


def test_natural_owner_rows_make_guard_stale(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["compose"]["checks"]["right_bottom_compose_ui_probe"]["summary"]["rbui_action_box"] = 1
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is False, report
    assert any("natural_owner_action_rows_absent" in failure for failure in report["failures"]), report


def test_visual_no_longer_black_fails_closed(fixture: Path) -> None:
    payloads = good_payloads()
    bounds = payloads["compose"]["checks"]["right_bottom_compose_ui_probe"]["summary"]["bounds"]
    bounds["bottom_right_tile_r8c10"]["black_percent"] = 20.0
    bounds["bottom_right_tile_r8c10"]["nonblack_percent"] = 80.0
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is False, report
    assert any("natural_visual_artifact_present" in failure for failure in report["failures"]), report


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
        test_good_visual_blocker_passes(fixture / "good")
        test_missing_triage_fails(fixture / "missing-triage")
        test_legacy_blocked_classification_is_still_accepted(fixture / "legacy-classification")
        test_natural_owner_rows_make_guard_stale(fixture / "owner-rows")
        test_visual_no_longer_black_fails_closed(fixture / "visual-fixed")
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
