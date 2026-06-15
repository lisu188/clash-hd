#!/usr/bin/env python3
"""Fixture tests for the right-bottom compose evidence matrix helper."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "right_bottom_compose_evidence_matrix.py"
sys.path.insert(0, str(ROOT / "tools"))

import right_bottom_compose_evidence_matrix  # noqa: E402


STABLE_STAGE = right_bottom_compose_evidence_matrix.DEFAULT_STABLE_STAGE
VALIDATION_STAGE = right_bottom_compose_evidence_matrix.DEFAULT_VALIDATION_STAGE
REQUIRED_CHECKS = right_bottom_compose_evidence_matrix.REQUIRED_CHECKS
SHA = "fixture-sha"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def args_for() -> argparse.Namespace:
    return argparse.Namespace(
        current_stable_stage=STABLE_STAGE,
        validation_stage=VALIDATION_STAGE,
        refresh_json=Path("unused-refresh.json"),
    )


def check(name: str, summary: dict, *, passed: bool = True) -> dict:
    return {
        "passed": passed,
        "summary": summary,
        "failures": [] if passed else [f"intentional {name} fixture failure"],
    }


def good_checks() -> dict:
    return {
        "right_bottom_compose_patch": check(
            "right_bottom_compose_patch",
            {
                "stage": VALIDATION_STAGE,
                "candidate_sha256": SHA,
                "right_bottom_patch_group": {"patched": 4, "total": 4},
                "current_hd_map_gate": True,
            },
        ),
        "right_bottom_compose_fullstart_route": check(
            "right_bottom_compose_fullstart_route",
            {
                "stage": VALIDATION_STAGE,
                "candidate_sha256": SHA,
                "hidden_desktop": True,
                "no_skip_start_anims": True,
                "fast_forward_start_anims": False,
                "map_validation_skipped": True,
                "ready": True,
                "av_count": 0,
                "bottom_right_ui_corner_nonblack": 48.228,
                "bottom_right_tile_r8c10_nonblack": 54.102,
                "bottom_right_tile_r8c11_nonblack": 42.822,
            },
        ),
        "right_bottom_compose_normal_gate": check(
            "right_bottom_compose_normal_gate",
            {
                "stage": VALIDATION_STAGE,
                "candidate_sha256": SHA,
                "hidden_desktop": True,
                "map_validation_skipped": False,
                "surface": [800, 600],
                "visibility_explained_gate": True,
                "visibility_unexplained_blank_cells": 0,
            },
        ),
        "right_bottom_compose_ui_probe": check(
            "right_bottom_compose_ui_probe",
            {
                "stage": VALIDATION_STAGE,
                "candidate_sha256": SHA,
                "hidden_desktop": True,
                "rbui_desc_switch": 35,
                "rbui_viewport_switch": 1,
                "rbui_panel_draw": 1,
                "rbui_action_box": 1,
                "av_count": 0,
            },
        ),
        "right_bottom_grid_hit": check(
            "right_bottom_grid_hit",
            {
                "stage": VALIDATION_STAGE,
                "candidate_sha256": SHA,
                "hidden_desktop": True,
                "map_validation_skipped": True,
                "fast_forward_start_anims": True,
                "surface": [800, 600],
                "grid_hit_ok": True,
                "last_grid_entry": [450, 73],
                "last_grid_result": 0,
                "forced_gate_count": 1,
                "failure_exit_count": 0,
                "draw_row_count": 5,
                "av_count": 0,
            },
        ),
        "right_bottom_natural_route_guard": check(
            "right_bottom_natural_route_guard",
            {
                "stage": f"{STABLE_STAGE}-rightbottomaction-nativecenter",
                "candidate_sha256": "natural-route-sha",
                "hidden_desktop": True,
                "owner_entry_flag": "0x00",
                "owner_flag_test": {"owner_flag": "0x00", "bit2": 0, "bit1": 0, "bit8": 0},
                "action_descriptor": {"slot": "d1", "x": 1000, "y": 426, "callback": "004338e0"},
                "descriptor_result": {
                    "result": 0,
                    "owner": "041bc71a",
                    "owner_flag": "0x00",
                    "surface": [800, 600],
                },
                "action_route_count": 0,
                "state_gated_by_owner_flag": True,
                "av_count": 0,
            },
        ),
        "right_bottom_route_timing_guard": check(
            "right_bottom_route_timing_guard",
            {
                "candidate_sha256": SHA,
                "patch_route_ordered_markers": 29,
                "fullstart_route_ordered_markers": 29,
                "grid_route_ordered_markers": 25,
                "grid_hit_ok": True,
                "last_grid_entry": [450, 73],
                "last_grid_result": 0,
                "failure_exit_count": 0,
                "av_count": 0,
            },
        ),
        "right_bottom_compose_promotion_decision": check(
            "right_bottom_compose_promotion_decision",
            {
                "decision": "defer_stable_promotion",
                "stable_stage_should_change": False,
                "current_stable_stage": STABLE_STAGE,
                "candidate_sha256": SHA,
            },
        ),
    }


def write_refresh(path: Path, checks: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"checks": checks}, indent=2) + "\n", encoding="utf-8")
    return path


def test_matrix_passes_with_all_required_checks(fixture: Path) -> None:
    matrix = right_bottom_compose_evidence_matrix.build_matrix_from_checks(args_for(), good_checks())
    assert matrix["passed"] is True, matrix
    assert matrix["promotion_status"] == "validation_stage_only", matrix
    assert matrix["stable_stage_should_change"] is False, matrix
    assert matrix["candidate_sha256"] == SHA, matrix
    assert matrix["key_evidence"]["promotion_decision"] == "defer_stable_promotion", matrix


def test_missing_or_failed_required_checks_fail(fixture: Path) -> None:
    for name in REQUIRED_CHECKS:
        failed_checks = good_checks()
        failed_checks[name]["passed"] = False
        failed_checks[name]["failures"] = [f"intentional {name} fixture failure"]
        failed = right_bottom_compose_evidence_matrix.build_matrix_from_checks(args_for(), failed_checks)
        assert failed["passed"] is False, failed
        assert any(f"{name}: intentional {name} fixture failure" in failure for failure in failed["failures"]), failed

        missing_checks = good_checks()
        missing_checks.pop(name)
        missing = right_bottom_compose_evidence_matrix.build_matrix_from_checks(args_for(), missing_checks)
        assert missing["passed"] is False, missing
        assert any(f"{name} is missing" in failure for failure in missing["failures"]), missing


def test_matrix_rejects_route_and_safety_regressions(fixture: Path) -> None:
    cases = [
        ("patch group", ("right_bottom_compose_patch", "right_bottom_patch_group"), {"patched": 3, "total": 4}, "right-bottom patch group"),
        ("map byte gate", ("right_bottom_compose_patch", "current_hd_map_gate"), False, "current HD map byte gate"),
        ("fullstart visible", ("right_bottom_compose_fullstart_route", "hidden_desktop"), False, "full-start route did not run on hidden desktop"),
        ("fullstart startup", ("right_bottom_compose_fullstart_route", "no_skip_start_anims"), False, "full-start route did not use the full startup"),
        ("fullstart av", ("right_bottom_compose_fullstart_route", "av_count"), 1, "full-start route has AV rows"),
        ("normal skipped validation", ("right_bottom_compose_normal_gate", "map_validation_skipped"), True, "normal map gate skipped map validation"),
        ("normal surface", ("right_bottom_compose_normal_gate", "surface"), [640, 480], "normal map gate surface"),
        ("normal visibility", ("right_bottom_compose_normal_gate", "visibility_unexplained_blank_cells"), 1, "unexplained blank cells"),
        ("ui descriptor", ("right_bottom_compose_ui_probe", "rbui_desc_switch"), 0, "descriptor switch rows"),
        ("ui viewport", ("right_bottom_compose_ui_probe", "rbui_viewport_switch"), 0, "viewport switch rows"),
        ("ui owner rows", ("right_bottom_compose_ui_probe", "rbui_panel_draw"), 0, "owner/action draw rows"),
        ("ui action rows", ("right_bottom_compose_ui_probe", "rbui_action_box"), 0, "owner/action draw rows"),
        ("ui av", ("right_bottom_compose_ui_probe", "av_count"), 1, "natural UI probe has AV rows"),
        ("grid visible", ("right_bottom_grid_hit", "hidden_desktop"), False, "controlled grid-hit proof did not run on hidden desktop"),
        ("grid startup", ("right_bottom_grid_hit", "fast_forward_start_anims"), False, "controlled grid-hit proof did not fast-forward"),
        ("grid surface", ("right_bottom_grid_hit", "surface"), [640, 480], "controlled grid-hit surface"),
        ("grid ok", ("right_bottom_grid_hit", "grid_hit_ok"), False, "controlled grid-hit proof did not prove"),
        ("grid entry", ("right_bottom_grid_hit", "last_grid_entry"), [451, 73], "controlled grid-hit entry"),
        ("grid result", ("right_bottom_grid_hit", "last_grid_result"), 1, "controlled grid-hit result"),
        ("grid failure exit", ("right_bottom_grid_hit", "failure_exit_count"), 1, "controlled grid-hit proof used a failure exit"),
        ("grid av", ("right_bottom_grid_hit", "av_count"), 1, "controlled grid-hit proof has AV rows"),
        ("natural visible", ("right_bottom_natural_route_guard", "hidden_desktop"), False, "natural route guard did not run on hidden desktop"),
        ("natural state gate", ("right_bottom_natural_route_guard", "state_gated_by_owner_flag"), False, "save-state gate"),
        ("natural owner flag", ("right_bottom_natural_route_guard", "owner_entry_flag"), "0x02", "natural route owner entry flag"),
        ("natural action route", ("right_bottom_natural_route_guard", "action_route_count"), 1, "natural route unexpectedly entered"),
        ("natural av", ("right_bottom_natural_route_guard", "av_count"), 1, "natural route guard has AV"),
        ("timing patch markers", ("right_bottom_route_timing_guard", "patch_route_ordered_markers"), 0, "patch route marker ordering"),
        ("timing fullstart markers", ("right_bottom_route_timing_guard", "fullstart_route_ordered_markers"), 0, "full-start route marker ordering"),
        ("timing grid markers", ("right_bottom_route_timing_guard", "grid_route_ordered_markers"), 0, "grid route marker ordering"),
        ("timing grid ok", ("right_bottom_route_timing_guard", "grid_hit_ok"), False, "route timing guard did not preserve grid-hit proof"),
        ("timing grid entry", ("right_bottom_route_timing_guard", "last_grid_entry"), [451, 73], "route timing guard grid entry"),
        ("timing grid result", ("right_bottom_route_timing_guard", "last_grid_result"), 1, "route timing guard grid result"),
        ("timing failure exit", ("right_bottom_route_timing_guard", "failure_exit_count"), 1, "route timing guard observed failure exits"),
        ("timing av", ("right_bottom_route_timing_guard", "av_count"), 1, "route timing guard observed AV rows"),
        ("decision promote", ("right_bottom_compose_promotion_decision", "stable_stage_should_change"), True, "would change the stable"),
    ]
    for _label, (check_name, key), value, expected_failure in cases:
        checks = deepcopy(good_checks())
        if expected_failure == "owner/action draw rows":
            checks["right_bottom_compose_ui_probe"]["summary"]["rbui_panel_draw"] = 0
            checks["right_bottom_compose_ui_probe"]["summary"]["rbui_action_box"] = 0
        else:
            checks[check_name]["summary"][key] = value
        matrix = right_bottom_compose_evidence_matrix.build_matrix_from_checks(args_for(), checks)
        assert matrix["passed"] is False, matrix
        assert any(expected_failure in failure for failure in matrix["failures"]), matrix


def test_matrix_rejects_natural_route_nested_regressions(fixture: Path) -> None:
    cases = [
        (
            "owner flag bits",
            lambda checks: checks["right_bottom_natural_route_guard"]["summary"]["owner_flag_test"].update({"bit2": 2}),
            "natural route owner flag bits",
        ),
        (
            "action callback",
            lambda checks: checks["right_bottom_natural_route_guard"]["summary"]["action_descriptor"].update({"callback": "004338c0"}),
            "action descriptor callback",
        ),
        (
            "action descriptor in bounds",
            lambda checks: checks["right_bottom_natural_route_guard"]["summary"]["action_descriptor"].update({"x": 799}),
            "not off-screen",
        ),
        (
            "descriptor result",
            lambda checks: checks["right_bottom_natural_route_guard"]["summary"]["descriptor_result"].update({"result": 1}),
            "natural route descriptor result",
        ),
    ]
    for _label, mutate, expected_failure in cases:
        checks = deepcopy(good_checks())
        mutate(checks)
        matrix = right_bottom_compose_evidence_matrix.build_matrix_from_checks(args_for(), checks)
        assert matrix["passed"] is False, matrix
        assert any(expected_failure in failure for failure in matrix["failures"]), matrix


def test_matrix_rejects_candidate_sha_disagreement(fixture: Path) -> None:
    checks = good_checks()
    checks["right_bottom_compose_ui_probe"]["summary"]["candidate_sha256"] = "other-sha"
    matrix = right_bottom_compose_evidence_matrix.build_matrix_from_checks(args_for(), checks)
    assert matrix["passed"] is False, matrix
    assert any("candidate SHA values disagree" in failure for failure in matrix["failures"]), matrix


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    good_refresh = write_refresh(fixture / "good" / "refresh.json", good_checks())
    out_json = fixture / "good-output" / "matrix.json"
    out_md = fixture / "good-output" / "matrix.md"
    good_run = run_script(
        "--refresh-json",
        str(good_refresh),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good_run.returncode == 0, good_run.stdout + good_run.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

    bad_checks = good_checks()
    bad_checks["right_bottom_compose_normal_gate"]["summary"]["visibility_unexplained_blank_cells"] = 1
    bad_refresh = write_refresh(fixture / "bad" / "refresh.json", bad_checks)
    bad_json = fixture / "bad-output" / "matrix.json"
    bad_md = fixture / "bad-output" / "matrix.md"
    bad_run = run_script(
        "--refresh-json",
        str(bad_refresh),
        "--write-json",
        str(bad_json),
        "--write-markdown",
        str(bad_md),
        "--require-pass",
    )
    assert bad_run.returncode == 2, bad_run.stdout + bad_run.stderr
    assert json.loads(bad_json.read_text(encoding="utf-8"))["passed"] is False
    assert "- Overall: FAIL" in bad_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "right-bottom-compose-matrix-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_matrix_passes_with_all_required_checks(fixture / "pass")
        test_missing_or_failed_required_checks_fail(fixture / "required")
        test_matrix_rejects_route_and_safety_regressions(fixture / "regressions")
        test_matrix_rejects_natural_route_nested_regressions(fixture / "natural-route-regressions")
        test_matrix_rejects_candidate_sha_disagreement(fixture / "sha")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("right-bottom compose evidence matrix tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
