#!/usr/bin/env python3
"""Fixture tests for hd_soak_short_artifact_manifest.py."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import hd_soak_short_artifact_manifest as manifest


def args_for(tmp: Path) -> argparse.Namespace:
    legacy_json = tmp / "captures" / "current" / "hd-soak-short-current.json"
    legacy_md = tmp / "captures" / "current" / "hd-soak-short-current.md"
    legacy_json.parent.mkdir(parents=True, exist_ok=True)
    legacy_json.write_text("{}\n", encoding="ascii")
    legacy_md.write_text("# legacy\n", encoding="ascii")
    return argparse.Namespace(legacy_report_json=legacy_json, legacy_report_md=legacy_md)


def test_current_manifest_passes_with_unique_step_paths() -> None:
    report = manifest.build_report(
        argparse.Namespace(
            legacy_report_json=manifest.DEFAULT_LEGACY_REPORT_JSON,
            legacy_report_md=manifest.DEFAULT_LEGACY_REPORT_MD,
        )
    )
    assert report["passed"] is True, report["failures"]
    assert report["step_count"] == 5
    paths = []
    for record in report["step_reports"]:
        paths.extend(record["paths"].values())
    assert len(paths) == len(set(path.lower() for path in paths))
    assert any("short2-menu-idle" in record["paths"]["report_json"] for record in report["step_reports"])


def test_commands_pin_outputs_and_require_approval_for_execution() -> None:
    with tempfile.TemporaryDirectory() as directory:
        report = manifest.build_report(args_for(Path(directory)))
    for record in report["step_reports"]:
        runtime = record["approval_gated_runtime_command"]
        dry_run = record["safe_dry_run_command"]
        assert "-ReportJson" in runtime
        assert "-ReportMarkdown" in runtime
        assert "-MaxInputDriftPx 1" in runtime
        assert "-MaxInputDriftPx 1" in dry_run
        assert "-IntroSkipClickMode postmessage" in runtime
        assert "-IntroSkipClicks 8" in runtime
        assert "-SkipPulses 4" in runtime
        assert "-IntroSkipClickMode postmessage" in dry_run
        assert "--max-input-drift-px 1" in record["guard_command"]
        assert "-Execute -AllowVisibleRuntime -RequirePass" in runtime
        assert "-Execute" not in dry_run
        assert record["stable_stage_should_change"] is False
        assert record["right_bottom_promotion_blocked"] is True


def test_duplicate_paths_fail_closed() -> None:
    records = manifest.build_step_records(manifest.hd_soak_short_tier_ladder.SHORT_LADDER_STEPS)
    records[1]["paths"]["report_json"] = records[0]["paths"]["report_json"]
    failures = manifest.validate_records(records)
    assert any("duplicate canonical artifact path" in failure for failure in failures)


def test_bad_output_path_fails_closed() -> None:
    records = manifest.build_step_records(manifest.hd_soak_short_tier_ladder.SHORT_LADDER_STEPS)
    records[0]["paths"]["report_json"] = r"C:\ClashCaptures\bad.json"
    failures = manifest.validate_records(records)
    assert any("outside captures/current" in failure for failure in failures)


def test_cli_writes_outputs() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        json_out = tmp / "manifest.json"
        md_out = tmp / "manifest.md"
        script = Path(__file__).resolve().parent / "hd_soak_short_artifact_manifest.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--write-json",
                str(json_out),
                "--write-markdown",
                str(md_out),
                "--require-pass",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert json_out.exists()
        assert md_out.exists()


def run_tests() -> None:
    test_current_manifest_passes_with_unique_step_paths()
    test_commands_pin_outputs_and_require_approval_for_execution()
    test_duplicate_paths_fail_closed()
    test_bad_output_path_fails_closed()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_soak_short_artifact_manifest tests passed")
