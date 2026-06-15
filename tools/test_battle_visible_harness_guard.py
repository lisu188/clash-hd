#!/usr/bin/env python3
"""Fixture tests for the visible battle input harness guard."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "battle_visible_harness_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import battle_visible_harness_guard  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def good_harness() -> str:
    return r"""param(
    [ValidateSet('window', 'raw-screen')]
    [string]$InputMode = 'window',
    [string]$RawScreenPoints = '668,520',
    [switch]$AllowVisibleRuntime
)

if (-not $AllowVisibleRuntime) {
    throw "Re-run with -AllowVisibleRuntime only after explicit user approval."
}

function Wait-LogPattern {
    param([string]$Path, [string]$Pattern, [int]$TimeoutSec)
    $processedLineCount = 0
    $cdbHasStarted = $false
    while ($true) {
        $lines = @(Get-Content -LiteralPath $Path)
        $newLines = @($lines | Select-Object -Skip $processedLineCount)
        $processedLineCount = $lines.Count
        foreach ($line in $newLines) {
            $trimmed = $line.TrimStart()
            if ($trimmed -match '^\d+:\d+>\s*g\s*$') {
                $cdbHasStarted = $true
                continue
            }
            if ($line.Contains('Unable to insert breakpoint') -or $line.Contains('Unable to remove breakpoint')) {
                throw "CDB became invalid before '$Pattern': $line"
            }
            if ($cdbHasStarted -and $line.Contains('Break instruction exception - code 80000003')) {
                throw "CDB became invalid before '$Pattern': $line"
            }
        }
    }
}
"""


def test_guard_accepts_good_harness(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    script = fixture / "good.ps1"
    script.write_text(good_harness(), encoding="utf-8")
    guard = battle_visible_harness_guard.build_guard(script)
    assert guard["passed"] is True, guard


def test_guard_rejects_missing_fatal_pattern(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    script = fixture / "missing-fatal.ps1"
    script.write_text(good_harness().replace("Unable to remove breakpoint", "ordinary message"), encoding="utf-8")
    guard = battle_visible_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("Unable to remove breakpoint" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_post_g_gate(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    script = fixture / "missing-gate.ps1"
    script.write_text(good_harness().replace("cdbHasStarted", "cdbStarted"), encoding="utf-8")
    guard = battle_visible_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("post-g" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_incremental_scan(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    script = fixture / "missing-incremental.ps1"
    script.write_text(good_harness().replace("Select-Object -Skip $processedLineCount", "Select-Object -Last 240"), encoding="utf-8")
    guard = battle_visible_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("only new log lines" in failure for failure in guard["failures"]), guard


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    script = fixture / "good.ps1"
    out_json = fixture / "guard.json"
    out_md = fixture / "guard.md"
    script.write_text(good_harness(), encoding="utf-8")
    run = run_script(
        "--script",
        str(script),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

    bad = fixture / "bad.ps1"
    bad.write_text(good_harness().replace("[switch]$AllowVisibleRuntime", "[switch]$Visible"), encoding="utf-8")
    bad_run = run_script(
        "--script",
        str(bad),
        "--write-json",
        str(fixture / "bad.json"),
        "--write-markdown",
        str(fixture / "bad.md"),
        "--require-pass",
    )
    assert bad_run.returncode == 2, bad_run.stdout + bad_run.stderr


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "battle-visible-harness-guard-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True, exist_ok=True)
    try:
        test_guard_accepts_good_harness(fixture / "good")
        test_guard_rejects_missing_fatal_pattern(fixture / "missing-fatal")
        test_guard_rejects_missing_post_g_gate(fixture / "missing-gate")
        test_guard_rejects_missing_incremental_scan(fixture / "missing-incremental")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("battle visible harness guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
