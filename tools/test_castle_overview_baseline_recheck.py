#!/usr/bin/env python3
"""Fixture tests for the castle overview baseline recheck."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import castle_overview_baseline_recheck  # noqa: E402


def good_args(fixture: Path) -> argparse.Namespace:
    return argparse.Namespace(
        overview_run=fixture / "overview",
        barracks_run=fixture / "barracks",
        stage="castlecenter-all",
        patch_exe=None,
        latest_overview_run=fixture / "latest-overview",
        focused_hitbox_run=fixture / "focused-hitbox",
        visible_multihit_run=fixture / "visible-multihit",
        owner_records_raw=fixture / "owner.raw",
        forced_hitmap_raw=fixture / "hitmap.raw",
        dormant_multihit_run=fixture / "dormant-multihit",
        threshold=12,
        max_echo_percent=25.0,
    )


def overview_gate_payload(*, passed: bool = True) -> dict[str, Any]:
    failures = [] if passed else ["intentional overview fixture failure"]
    return {
        "passed": passed,
        "run_dir": "fixture-overview",
        "screenshot": "fixture-overview/surface.png",
        "catalog": {
            "commands": ["0x63", "0x86", "0x87", "0x99", "0x9C", "0x9F", "0xA6"],
            "last_surface": {"size": [800, 600]},
            "last_overview_post_draw": {"main_size": [800, 600]},
        },
        "geometry": {"gate": {"passed": passed}},
        "barracks_baseline": {"passed": passed},
        "failures": failures,
    }


def barracks_payload(*, passed: bool = True) -> dict[str, Any]:
    failures = [] if passed else ["intentional barracks fixture failure"]
    return {
        "passed": passed,
        "run": "fixture-barracks",
        "log": "fixture-barracks/cdb-surface-dump.log",
        "ready": passed,
        "descriptor_click_ok": passed,
        "controlled_4356c0_ok": passed,
        "failure_exit_count": 0,
        "av_count": 0,
        "classification": [],
        "failures": failures,
    }


def matrix_target(
    index: int,
    raw: int,
    command: int,
    callback: int,
    *,
    completion_ok: bool = True,
) -> dict[str, Any]:
    return {
        "index": index,
        "raw": raw,
        "command": command,
        "callback": callback,
        "raw_ok": True,
        "descriptor_ok": True,
        "gate_ok": True,
        "completion_ok": completion_ok,
        "ok": completion_ok,
    }


def matrix_payload(*, passed: bool = True, completion_ok: bool = True) -> dict[str, Any]:
    failures = [] if passed else ["intentional matrix fixture failure"]
    return {
        "passed": passed,
        "stage": "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all",
        "promotion_status": "validation_stage_only" if passed else "regressed",
        "candidate_sha256": "fixture",
        "patches": {"patched": 134, "original": 0, "unexpected": 0, "total": 134},
        "visible_multihit_targets": [
            matrix_target(0, 0xF8, 0x86, 0x0044FE70, completion_ok=completion_ok),
            matrix_target(1, 0xFE, 0x63, 0x00433C20, completion_ok=completion_ok),
        ],
        "dormant_multihit_targets": [
            matrix_target(0, 0xFA, 0x99, 0x0043DCE0, completion_ok=completion_ok),
            matrix_target(1, 0xFB, 0x9C, 0x0043D8E0, completion_ok=completion_ok),
        ],
        "failures": failures,
    }


def with_patched_inputs(
    *,
    overview_passed: bool = True,
    barracks_passed: bool = True,
    matrix_passed: bool = True,
    matrix_completion_ok: bool = True,
    callback: Callable[[], None],
) -> None:
    original_gate = castle_overview_baseline_recheck.castle_overview_gate.build_gate
    original_barracks = castle_overview_baseline_recheck.build_barracks_controlled_stop
    original_matrix = castle_overview_baseline_recheck.build_latest_matrix
    castle_overview_baseline_recheck.castle_overview_gate.build_gate = (
        lambda **_kwargs: overview_gate_payload(passed=overview_passed)
    )
    castle_overview_baseline_recheck.build_barracks_controlled_stop = (
        lambda _run: barracks_payload(passed=barracks_passed)
    )
    castle_overview_baseline_recheck.build_latest_matrix = (
        lambda _args: matrix_payload(passed=matrix_passed, completion_ok=matrix_completion_ok)
    )
    try:
        callback()
    finally:
        castle_overview_baseline_recheck.castle_overview_gate.build_gate = original_gate
        castle_overview_baseline_recheck.build_barracks_controlled_stop = original_barracks
        castle_overview_baseline_recheck.build_latest_matrix = original_matrix


def test_good_fixture(fixture: Path) -> None:
    args = good_args(fixture)

    def check() -> None:
        recheck = castle_overview_baseline_recheck.build_recheck(args)
        assert recheck["passed"] is True, recheck

    with_patched_inputs(callback=check)


def test_overview_failure_fails(fixture: Path) -> None:
    args = good_args(fixture)

    def check() -> None:
        recheck = castle_overview_baseline_recheck.build_recheck(args)
        assert recheck["passed"] is False, recheck
        assert any("overview_visual_baseline" in failure for failure in recheck["failures"]), recheck

    with_patched_inputs(overview_passed=False, callback=check)


def test_barracks_failure_fails(fixture: Path) -> None:
    args = good_args(fixture)

    def check() -> None:
        recheck = castle_overview_baseline_recheck.build_recheck(args)
        assert recheck["passed"] is False, recheck
        assert any("barracks_controlled_stop" in failure for failure in recheck["failures"]), recheck

    with_patched_inputs(barracks_passed=False, callback=check)


def test_matrix_failure_fails(fixture: Path) -> None:
    args = good_args(fixture)

    def check() -> None:
        recheck = castle_overview_baseline_recheck.build_recheck(args)
        assert recheck["passed"] is False, recheck
        assert any("latest_castle_overview_matrix" in failure for failure in recheck["failures"]), recheck

    with_patched_inputs(matrix_passed=False, callback=check)


def test_matrix_completion_failure_fails(fixture: Path) -> None:
    args = good_args(fixture)

    def check() -> None:
        recheck = castle_overview_baseline_recheck.build_recheck(args)
        assert recheck["passed"] is False, recheck
        assert any("target-done completion proof" in failure for failure in recheck["failures"]), recheck

    with_patched_inputs(matrix_completion_ok=False, callback=check)


def test_writes_json_and_markdown(fixture: Path) -> None:
    args = good_args(fixture)
    out_json = fixture / "output" / "recheck.json"
    out_md = fixture / "output" / "recheck.md"

    def check() -> None:
        recheck = castle_overview_baseline_recheck.build_recheck(args)
        castle_overview_baseline_recheck.write_json(out_json, recheck)
        castle_overview_baseline_recheck.write_markdown(out_md, recheck)
        assert out_json.read_text(encoding="utf-8").lstrip().startswith("{")
        markdown = out_md.read_text(encoding="utf-8")
        assert "- Overall: PASS" in markdown
        assert "- Visible target completion: index 0 0x86/0xF8 completion=True" in markdown
        assert "- Dormant target completion: index 0 0x99/0xFA completion=True" in markdown

    with_patched_inputs(callback=check)


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "castle-overview-baseline-recheck-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_fixture(fixture / "good")
        test_overview_failure_fails(fixture / "overview-failure")
        test_barracks_failure_fails(fixture / "barracks-failure")
        test_matrix_failure_fails(fixture / "matrix-failure")
        test_matrix_completion_failure_fails(fixture / "matrix-completion-failure")
        test_writes_json_and_markdown(fixture / "output")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("castle overview baseline recheck tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
