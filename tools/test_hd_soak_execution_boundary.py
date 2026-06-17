#!/usr/bin/env python3
"""Fixture tests for hd_soak_execution_boundary.py."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import hd_soak_execution_boundary as boundary


ROOT = Path(__file__).resolve().parents[1]


def completed(command: list[str], returncode: int, text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, returncode, stdout="", stderr=text)


def args_for(tmp: Path) -> argparse.Namespace:
    return argparse.Namespace(
        script=Path("scripts/smoke/run_hd_soak.ps1"),
        fixture_root=tmp / "fixture",
        clean_fixture=True,
    )


def fake_runner(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
    text = " ".join(command)
    if "-VisibleRuntimeApprovalToken" not in command:
        return completed(command, 1, "Visible runtime execution requires -VisibleRuntimeApprovalToken from a fresh dry-run approval packet.")
    if "-VisibleRuntimeApprovalExpiresUtc" not in command:
        return completed(command, 1, "Visible runtime execution requires -VisibleRuntimeApprovalExpiresUtc from a fresh dry-run approval packet.")
    if "2000-01-01T00:00:00+00:00" in text:
        return completed(command, 1, "Visible runtime approval expired at 2000-01-01T00:00:00.0000000+00:00.")
    return completed(command, 1, "Visible runtime approval token does not match this command shape. Expected abcdef0123456789.")


def side_effect_runner(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
    candidate_dir = Path(command[command.index("-CandidateDir") + 1])
    candidate_dir.mkdir(parents=True, exist_ok=True)
    return fake_runner(command, **_)


def test_fake_boundary_report_passes() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "hd-soak-execution-boundary-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        report = boundary.build_report(args_for(fixture), runner=fake_runner)
    finally:
        shutil.rmtree(fixture, ignore_errors=True)
    assert report["passed"] is True, report
    assert report["case_count"] == 4
    assert all(case["expected_phrase_seen"] for case in report["cases"])
    assert all(not any(case["side_effects"].values()) for case in report["cases"])
    command = report["cases"][0]["command"]
    assert "-SampleIntervalSec 15" in command
    assert "-MinNonblackPercent 10" in command
    assert "-MaxArtifactMB 250" in command
    assert "-MaxWorkingSetGrowthMB 64" in command


def test_boundary_report_rejects_side_effects() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "hd-soak-execution-boundary-side-effect"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        args = args_for(fixture)
        args.clean_fixture = False
        report = boundary.build_report(args, runner=side_effect_runner)
    finally:
        shutil.rmtree(fixture, ignore_errors=True)
    assert report["passed"] is False
    assert any("did not fail closed" in failure for failure in report["failures"])
    assert any(case["side_effects"]["candidate_dir"] for case in report["cases"])


def test_markdown_contains_case_rows() -> None:
    report = {
        "passed": True,
        "generated_at": "2026-06-16T00:00:00+00:00",
        "runtime_policy": boundary.RUNTIME_POLICY,
        "guard_policy": "fixture",
        "script": "scripts/smoke/run_hd_soak.ps1",
        "case_count": 1,
        "cases": [
            {
                "name": "missing_token",
                "passed": True,
                "exit_code": 1,
                "expected_phrase_seen": True,
                "side_effects": {},
            }
        ],
        "failures": [],
    }
    markdown = boundary.to_markdown(report)
    assert "HD Soak Execution Boundary" in markdown
    assert "`missing_token`" in markdown


def test_cli_writes_outputs() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "hd-soak-execution-boundary-cli"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        out_json = fixture / "boundary.json"
        out_md = fixture / "boundary.md"
        report = boundary.build_report(args_for(fixture), runner=fake_runner)
        boundary.write_outputs(report, out_json, out_md)
        assert json.loads(out_json.read_text(encoding="ascii"))["passed"] is True
        assert "HD Soak Execution Boundary" in out_md.read_text(encoding="ascii")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def run_tests() -> None:
    test_fake_boundary_report_passes()
    test_boundary_report_rejects_side_effects()
    test_markdown_contains_case_rows()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_execution_boundary tests passed")
