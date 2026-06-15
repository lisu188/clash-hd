#!/usr/bin/env python3
"""Tests for right_bottom_slot_fixture_script_guard.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import right_bottom_slot_fixture_script_guard as guard


GOOD_SCRIPT = r"""
param(
    [string]$SourceSave = 'C:\Clash\save\5.dat',
    [string]$SourceWorkDir = 'C:\Clash',
    [string]$FixtureRoot = 'C:\ClashTests\right-bottom-slot5-as-slot0-fixture',
    [ValidateRange(0,9)]
    [int]$TargetLoadSlot = 0,
    [switch]$SeedWorkDir,
    [switch]$Execute,
    [switch]$AllowRepoFixtureRoot,
    [switch]$Json
)
$Plan = [ordered]@{
    proof_class = 'non_natural_isolated_fixture'
    promotion_ready = $false
    stable_stage_should_change = $false
}
if ((Test-IsUnderPath $FixtureRootFull $RepoRoot) -and -not $AllowRepoFixtureRoot) {
    throw "repo"
}
if (Test-IsUnderPath $FixtureSaveFull $ClashSaveRootFull) {
    throw "live save"
}
if (Test-IsUnderPath $FixtureRootFull $SourceWorkDirFull) {
    throw "source workdir"
}
if ($FixtureSaveFull -eq $SourceSaveFull) {
    throw "Refusing to overwrite source save"
}
$SeedExcludedDirs = @('save')
if (-not $Execute) {
    exit 0
}
if ($SeedWorkDir) {
    Get-ChildItem -LiteralPath $SourceWorkDirFull -Force |
        Where-Object { $SeedExcludedDirs -notcontains $_.Name } |
        ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $FixtureRootFull -Recurse -Force
        }
}
Copy-Item -LiteralPath $SourceSaveFull -Destination $FixtureSaveFull
"""


def write_script(root: Path, text: str) -> Path:
    script = root / "scripts/smoke/prepare_right_bottom_slot_fixture.ps1"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(text, encoding="utf-8")
    return script


def test_passes_good_script_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = guard.build_guard(write_script(Path(tmp), GOOD_SCRIPT))
    assert report["passed"], report
    assert report["dry_run_exit_line"] < report["seed_copy_line"]
    assert report["dry_run_exit_line"] < report["copy_line"]


def test_fails_without_execute_gate() -> None:
    bad = GOOD_SCRIPT.replace("if (-not $Execute) {\n    exit 0\n}\n", "")
    with tempfile.TemporaryDirectory() as tmp:
        report = guard.build_guard(write_script(Path(tmp), bad))
    assert not report["passed"]
    assert any("dry-run exit" in failure for failure in report["failures"]), report


def test_fails_when_copy_precedes_dry_run_exit() -> None:
    bad = GOOD_SCRIPT.replace(
        "$SeedExcludedDirs = @('save')\nif (-not $Execute)",
        "$SeedExcludedDirs = @('save')\n"
        "Copy-Item -LiteralPath $SourceSaveFull -Destination $FixtureSaveFull\n"
        "if (-not $Execute)",
    )
    with tempfile.TemporaryDirectory() as tmp:
        report = guard.build_guard(write_script(Path(tmp), bad))
    assert not report["passed"]
    assert any("before the dry-run exit" in failure for failure in report["failures"]), report


def test_fails_without_live_save_guard() -> None:
    bad = GOOD_SCRIPT.replace(
        "if (Test-IsUnderPath $FixtureSaveFull $ClashSaveRootFull) {\n    throw \"live save\"\n}\n",
        "",
    )
    with tempfile.TemporaryDirectory() as tmp:
        report = guard.build_guard(write_script(Path(tmp), bad))
    assert not report["passed"]
    assert any("live_save_guard" in failure for failure in report["failures"]), report


def test_fails_without_seed_save_exclusion() -> None:
    bad = GOOD_SCRIPT.replace("$SeedExcludedDirs = @('save')\n", "")
    with tempfile.TemporaryDirectory() as tmp:
        report = guard.build_guard(write_script(Path(tmp), bad))
    assert not report["passed"]
    assert any("seed_excludes_save_dir" in failure for failure in report["failures"]), report


def test_fails_on_visible_runtime_api() -> None:
    bad = GOOD_SCRIPT + "\nStart-Process -FilePath 'C:\\Clash\\clash95.exe'\n"
    with tempfile.TemporaryDirectory() as tmp:
        report = guard.build_guard(write_script(Path(tmp), bad))
    assert not report["passed"]
    assert any("visible/runtime" in failure for failure in report["failures"]), report


def test_cli_writes_outputs_and_requires_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        script = write_script(root, GOOD_SCRIPT)
        out_json = root / "out.json"
        out_md = root / "out.md"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(guard.__file__)),
                "--script",
                str(script),
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
    test_passes_good_script_shape()
    test_fails_without_execute_gate()
    test_fails_when_copy_precedes_dry_run_exit()
    test_fails_without_live_save_guard()
    test_fails_without_seed_save_exclusion()
    test_fails_on_visible_runtime_api()
    test_cli_writes_outputs_and_requires_pass()


if __name__ == "__main__":
    run_tests()
    print("right_bottom_slot_fixture_script_guard tests passed")
