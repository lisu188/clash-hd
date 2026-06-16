#!/usr/bin/env python3
"""Fixture tests for hd_soak_harness_guard.py."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "hd_soak_harness_guard.py"
HARNESS = ROOT / "scripts" / "smoke" / "run_hd_soak.ps1"
sys.path.insert(0, str(ROOT / "tools"))

import hd_soak_harness_guard  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_fixture(fixture: Path, text: str) -> Path:
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(text, encoding="utf-8")
    return fixture


def harness_text() -> str:
    return HARNESS.read_text(encoding="utf-8-sig")


def test_current_harness_passes() -> None:
    guard = hd_soak_harness_guard.build_guard(HARNESS)
    assert guard["passed"] is True, guard
    assert guard["checks"]["visible_runtime_opt_in"]["passed"] is True
    assert guard["checks"]["promotion_boundary"]["passed"] is True


def test_guard_rejects_stage_drift(fixture: Path) -> None:
    bad = harness_text().replace(hd_soak_harness_guard.PROTECTED_STABLE_STAGE, "bad-stage", 1)
    script = write_fixture(fixture / "bad-stage.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("Stage default" in failure for failure in guard["failures"]), guard


def test_guard_rejects_repo_candidate_default(fixture: Path) -> None:
    bad = harness_text().replace(r"C:\ClashTests\hd-soak", r"captures\hd-soak", 1)
    script = write_fixture(fixture / "repo-candidate.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("CandidateDir default" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_explicit_approval(fixture: Path) -> None:
    bad = harness_text().replace("explicit user approval", "operator confirmation")
    script = write_fixture(fixture / "missing-approval.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("explicit user approval" in failure for failure in guard["failures"]), guard


def test_guard_rejects_dry_run_execute_command_without_require_pass(fixture: Path) -> None:
    bad = harness_text().replace("    '-RequirePass',\n", "")
    script = write_fixture(fixture / "missing-require-pass.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("dry-run execute command does not include -RequirePass" in failure for failure in guard["failures"]), guard


def test_guard_rejects_dry_run_execute_command_without_json(fixture: Path) -> None:
    bad = harness_text().replace("    '-Json'\n", "")
    script = write_fixture(fixture / "missing-json.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("dry-run execute command does not include -Json" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_metric(fixture: Path) -> None:
    bad = harness_text().replace("unique_sample_colors_min", "unique_sample_colors_low")
    script = write_fixture(fixture / "missing-metric.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("unique_sample_colors_min" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_render_range_and_inventory_metrics(fixture: Path) -> None:
    bad = harness_text()
    bad = bad.replace("sample_interval_sec", "sample_period_sec")
    bad = bad.replace("mean_luma_max", "mean_luma_high")
    bad = bad.replace("capture_errors", "capture_issue_rows")
    script = write_fixture(fixture / "missing-range-inventory.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("sample_interval_sec" in failure for failure in guard["failures"]), guard
    assert any("mean_luma_max" in failure for failure in guard["failures"]), guard
    assert any("capture_errors" in failure for failure in guard["failures"]), guard


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    bad = harness_text().replace("right_bottom_promotion_blocked = $true", "right_bottom_promotion_blocked = $false")
    script = write_fixture(fixture / "promotion-open.ps1", bad)
    out_json = fixture / "out.json"
    out_md = fixture / "out.md"
    result = run_script(
        "--script",
        str(script),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert out_json.exists()
    assert "HD Soak Harness Guard" in out_md.read_text(encoding="ascii")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "hd-soak-harness-guard-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_current_harness_passes()
        test_guard_rejects_stage_drift(fixture / "stage")
        test_guard_rejects_repo_candidate_default(fixture / "repo-candidate")
        test_guard_rejects_missing_explicit_approval(fixture / "approval")
        test_guard_rejects_dry_run_execute_command_without_require_pass(fixture / "require-pass")
        test_guard_rejects_dry_run_execute_command_without_json(fixture / "json")
        test_guard_rejects_missing_metric(fixture / "metric")
        test_guard_rejects_missing_render_range_and_inventory_metrics(fixture / "range-inventory")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("hd_soak_harness_guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
