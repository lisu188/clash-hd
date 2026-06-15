#!/usr/bin/env python3
"""Tests for right_bottom_slot_fixture_plan.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import right_bottom_slot_fixture_plan as plan


def write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def candidate_matrix(
    *,
    passed: bool = True,
    promotion_ready: bool = False,
    route_save_slot: int = 5,
    route_record_index: int = 0,
    slot5_status: str = "timeout_before_loadsave",
    slot2_status: str = "loads_but_click_misses_castle",
) -> dict[str, object]:
    route_candidate = {
        "save": rf"C:\Clash\save\{route_save_slot}.dat",
        "save_slot": route_save_slot,
        "record_index": route_record_index,
        "position": [14, 20],
        "owner": 0,
        "flags_1a0_hex": "0x0B",
        "bit2": 2,
        "bit1": 1,
        "bit8": 8,
        "action_eligible": True,
    }
    return {
        "passed": passed,
        "promotion_ready": promotion_ready,
        "summary": {
            "baseline_route_index": 0,
            "route_compatible_candidate": route_candidate,
            "slot2_status": {"status": slot2_status},
            "slot5_status": {"status": slot5_status},
        },
        "baseline": {
            "load_slot": 0,
            "load_succeeded": True,
            "map_click_hits_building": True,
            "castle_overview_reached": True,
            "owner_flag_zero_blocker": True,
        },
    }


def load_slot_route_limit(*, passed: bool = True, recent_slot5_blocked: bool = True) -> dict[str, object]:
    return {
        "passed": passed,
        "summary": {
            "recent_slot5_blocked": recent_slot5_blocked,
        },
    }


def build(root: Path, *, matrix: dict[str, object] | None = None, route_limit: dict[str, object] | None = None) -> dict[str, object]:
    matrix_path = write_json(root / "matrix.json", matrix or candidate_matrix())
    route_limit_path = write_json(root / "route-limit.json", route_limit or load_slot_route_limit())
    return plan.build_plan(
        candidate_matrix_json=matrix_path,
        load_slot_route_limit_json=route_limit_path,
        fixture_root=Path(r"C:\ClashTests\right-bottom-slot5-as-slot0-fixture"),
        repo_root=root,
    )


def test_passes_current_fixture_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(Path(tmp))
    assert report["passed"], report
    planned = report["plan"]
    assert planned["proof_class"] == "non_natural_isolated_fixture"
    assert planned["promotion_ready"] is False
    assert planned["stable_stage_should_change"] is False
    assert planned["source_save"].endswith(r"C:\Clash\save\5.dat")
    assert planned["fixture_save"].endswith(r"save\0.dat")


def test_fails_when_candidate_is_promotion_ready() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(Path(tmp), matrix=candidate_matrix(promotion_ready=True))
    assert not report["passed"]
    assert any("promotion-ready" in failure for failure in report["failures"]), report


def test_fails_when_slot5_no_longer_blocked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(
            Path(tmp),
            matrix=candidate_matrix(slot5_status="loaded_needs_new_action_probe"),
            route_limit=load_slot_route_limit(recent_slot5_blocked=False),
        )
    assert not report["passed"]
    assert any("slot5 status" in failure for failure in report["failures"]), report
    assert any("recent slot5 blocked" in failure for failure in report["failures"]), report


def test_fails_when_fixture_would_write_inside_repo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        matrix_path = write_json(root / "matrix.json", candidate_matrix())
        route_limit_path = write_json(root / "route-limit.json", load_slot_route_limit())
        report = plan.build_plan(
            candidate_matrix_json=matrix_path,
            load_slot_route_limit_json=route_limit_path,
            fixture_root=root / "fixture",
            repo_root=root,
        )
    assert not report["passed"]
    assert any("inside the repository" in failure for failure in report["failures"]), report


def test_cli_writes_outputs_and_requires_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        matrix_path = write_json(root / "matrix.json", candidate_matrix())
        route_limit_path = write_json(root / "route-limit.json", load_slot_route_limit())
        out_json = root / "out.json"
        out_md = root / "out.md"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(plan.__file__)),
                "--candidate-matrix-json",
                str(matrix_path),
                "--load-slot-route-limit-json",
                str(route_limit_path),
                "--repo-root",
                str(root),
                "--write-json",
                str(out_json),
                "--write-markdown",
                str(out_md),
                "--require-pass",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert out_json.exists()
        assert out_md.exists()


def run_tests() -> None:
    test_passes_current_fixture_shape()
    test_fails_when_candidate_is_promotion_ready()
    test_fails_when_slot5_no_longer_blocked()
    test_fails_when_fixture_would_write_inside_repo()
    test_cli_writes_outputs_and_requires_pass()


if __name__ == "__main__":
    run_tests()
    print("right_bottom_slot_fixture_plan tests passed")
