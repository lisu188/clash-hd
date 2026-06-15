#!/usr/bin/env python3
"""Fixture tests for hd_soak_report.py."""

from __future__ import annotations

import hd_soak_report as soak


def passing_report() -> dict:
    return {
        "executed": True,
        "runtime_policy": "opt-in visible runtime soak; raw frames stay outside the repository by default",
        "stage": soak.PROTECTED_STABLE_STAGE,
        "stable_stage_should_change": False,
        "tier": "short2",
        "route": "menu-idle",
        "duration_sec": 120,
        "candidate": r"C:\ClashTests\hd-soak\clash95_hd_soak_fixture.exe",
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
    evaluation = soak.evaluate_report(passing_report())
    assert evaluation["overall"] is True, evaluation
    assert evaluation["checks"]["protected_stage"]["passed"] is True
    assert evaluation["checks"]["render_metrics"]["passed"] is True
    assert evaluation["checks"]["promotion_boundary"]["passed"] is True


def test_unexpected_exit_fails() -> None:
    report = passing_report()
    report["process_exited_unexpectedly"] = True
    report["exit_code"] = 3221225477
    report["clean_stop"] = False
    evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["process_liveness"]["passed"] is False
    assert any("unexpectedly" in failure for failure in evaluation["failures"])


def test_repo_artifacts_fail() -> None:
    report = passing_report()
    report["candidate"] = str(soak.REPO_ROOT / "clash95_hd_bad.exe")
    report["output_directory"] = str(soak.REPO_ROOT / "captures" / "current" / "raw-soak")
    evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["artifact_locations"]["passed"] is False


def test_render_metrics_fail() -> None:
    report = passing_report()
    report["frame_samples"][1]["NonblackPercent"] = 0.0
    report["frame_samples"][1]["UniqueSampleColors"] = 1
    evaluation = soak.evaluate_report(report)
    assert evaluation["overall"] is False
    assert evaluation["checks"]["render_metrics"]["passed"] is False


def run_all() -> None:
    test_passing_report()
    test_unexpected_exit_fails()
    test_repo_artifacts_fail()
    test_render_metrics_fail()


if __name__ == "__main__":
    run_all()
    print("hd_soak_report tests passed")
