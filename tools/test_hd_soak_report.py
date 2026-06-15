#!/usr/bin/env python3
"""Fixture tests for hd_soak_report.py."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import hd_soak_report as soak


def patch_stage_report(candidate_sha: str) -> dict:
    return {
        "stage": soak.PROTECTED_STABLE_STAGE,
        "exe_sha256": candidate_sha,
        "expected_base_sha256": soak.EXPECTED_BASE_SHA256.upper(),
        "patch_count": 2,
        "status_counts": {"patched": 2},
        "current_hd_map_gate": {"passed": True},
    }


def passing_report(tmp: Path) -> dict:
    candidate_sha = "c" * 64
    patch_path = tmp / "patch-stage.json"
    patch_path.write_text(json.dumps(patch_stage_report(candidate_sha)), encoding="ascii")
    return {
        "executed": True,
        "runtime_policy": "opt-in visible runtime soak; raw frames stay outside the repository by default",
        "stage": soak.PROTECTED_STABLE_STAGE,
        "stable_stage_should_change": False,
        "tier": "short2",
        "route": "menu-idle",
        "duration_sec": 120,
        "candidate": r"C:\ClashTests\hd-soak\clash95_hd_soak_fixture.exe",
        "candidate_sha256": candidate_sha,
        "input_sha256": soak.EXPECTED_BASE_SHA256,
        "patch_stage_report": str(patch_path),
        "output_directory": r"C:\ClashCaptures\hd-soak\fixture",
        "report_json": "captures/current/hd-soak-short-current.json",
        "frame_sample_count": 2,
        "artifact_bytes": 123456,
        "process_exited_unexpectedly": False,
        "exit_code": None,
        "clean_stop": True,
        "input_proof_class": "automated_visible_runtime_diagnostic_not_manual_directinput_release_proof",
        "right_bottom_promotion_blocked": True,
        "route_results": [
            {
                "Name": "intro-skip",
                "PathVerified": True,
                "Click": True,
                "ClickPathVerified": True,
            }
        ],
        "frame_samples": [
            {
                "Name": "frame-0000",
                "Width": 800,
                "Height": 600,
                "Hash": "a" * 64,
                "NonblackPercent": 45.0,
                "MeanLuma": 40.0,
                "UniqueSampleColors": 32,
            },
            {
                "Name": "frame-0001",
                "Width": 800,
                "Height": 600,
                "Hash": "b" * 64,
                "NonblackPercent": 44.5,
                "MeanLuma": 41.0,
                "UniqueSampleColors": 35,
            },
        ],
    }


def test_passing_report() -> None:
    with tempfile.TemporaryDirectory() as directory:
        evaluation = soak.evaluate_report(passing_report(Path(directory)))
    assert evaluation["overall"] is True, evaluation
    assert evaluation["checks"]["protected_stage"]["passed"] is True
    assert evaluation["checks"]["patch_evidence"]["passed"] is True
    assert evaluation["checks"]["render_metrics"]["passed"] is True
    assert evaluation["checks"]["promotion_boundary"]["passed"] is True


def test_unexpected_exit_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["process_exited_unexpectedly"] = True
        report["exit_code"] = 3221225477
        report["clean_stop"] = False
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["process_liveness"]["passed"] is False
    assert any("unexpectedly" in failure for failure in evaluation["failures"])


def test_repo_artifacts_fail() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["candidate"] = str(soak.REPO_ROOT / "clash95_hd_bad.exe")
        report["output_directory"] = str(soak.REPO_ROOT / "captures" / "current" / "raw-soak")
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["artifact_locations"]["passed"] is False


def test_render_metrics_fail() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["frame_samples"][1]["NonblackPercent"] = 0.0
        report["frame_samples"][1]["UniqueSampleColors"] = 1
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["render_metrics"]["passed"] is False


def test_patch_manifest_mismatch_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        report = passing_report(tmp)
        patch_path = tmp / "patch-stage.json"
        payload = patch_stage_report(report["candidate_sha256"])
        payload["status_counts"] = {"patched": 1, "original": 1}
        payload["current_hd_map_gate"] = {"passed": False}
        patch_path.write_text(json.dumps(payload), encoding="ascii")
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["patch_evidence"]["passed"] is False
    assert any("current_hd_map_gate" in failure for failure in evaluation["failures"])


def test_missing_patch_manifest_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = passing_report(Path(directory))
        report["patch_stage_report"] = str(Path(directory) / "missing.json")
        evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["patch_evidence"]["passed"] is False
    assert any("patch_stage_report does not exist" in failure for failure in evaluation["failures"])


def run_tests() -> None:
    test_passing_report()
    test_unexpected_exit_fails()
    test_repo_artifacts_fail()
    test_render_metrics_fail()
    test_patch_manifest_mismatch_fails()
    test_missing_patch_manifest_fails()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_report tests passed")
