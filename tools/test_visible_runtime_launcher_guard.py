#!/usr/bin/env python3
"""Fixture tests for visible runtime launcher guard."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "visible_runtime_launcher_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import visible_runtime_launcher_guard  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def good_launcher() -> str:
    return """param(
    [string]$Exe = 'C:\\Clash\\candidate.exe',
    [switch]$AllowVisibleRuntime
)

$ErrorActionPreference = 'Stop'

if (-not $AllowVisibleRuntime) {
    throw "This legacy harness launches a visible Clash95 runtime. Re-run with -AllowVisibleRuntime only after explicit user approval."
}

$process = Start-Process -FilePath $Exe -PassThru
"""


def good_foreground_helper() -> str:
    return """param(
    [int]$TargetProcessId,
    [switch]$AllowVisibleRuntime
)

$ErrorActionPreference = 'Stop'

if (-not $AllowVisibleRuntime) {
    throw "This helper touches a visible Clash95 window. Re-run with -AllowVisibleRuntime only after explicit user approval."
}

[ClashCaptureWin32]::SetWindowPos($handle, [IntPtr]::Zero, 0, 0, 0, 0, 0) | Out-Null
"""


def good_screen_capture_helper() -> str:
    return """param(
    [string]$ProcessName = 'clash95',
    [switch]$AllowVisibleRuntime
)

$ErrorActionPreference = 'Stop'

if (-not $AllowVisibleRuntime) {
    throw "This helper reads a visible Clash95 window. Re-run with -AllowVisibleRuntime only after explicit user approval."
}

$graphics.CopyFromScreen(0, 0, 0, 0, $bitmap.Size)
"""


def parent_capture_helper_call(extra_args: str = " -AllowVisibleRuntime") -> str:
    return f"""param(
    [int]$TargetProcessId,
    [switch]$AllowVisibleRuntime
)

$ErrorActionPreference = 'Stop'

if (-not $AllowVisibleRuntime) {{
    throw "This legacy harness launches a visible Clash95 runtime. Re-run with -AllowVisibleRuntime only after explicit user approval."
}}

$captureScript = Join-Path $PSScriptRoot 'scripts/capture/capture_clash_client_frame.ps1'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $captureScript -TargetProcessId $TargetProcessId -Path 'frame.png' -Json 'frame.json'{extra_args} | Out-Null
"""


def test_guard_passes_for_gated_launchers(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    script = fixture / "good.ps1"
    script.write_text(good_launcher(), encoding="utf-8")
    guard = visible_runtime_launcher_guard.build_guard(argparse.Namespace(script=[script]))
    assert guard["passed"] is True, guard
    assert guard["passing_script_count"] == 1, guard


def test_guard_passes_for_gated_foreground_helpers(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    script = fixture / "good-helper.ps1"
    script.write_text(good_foreground_helper(), encoding="utf-8")
    guard = visible_runtime_launcher_guard.build_guard(argparse.Namespace(script=[script]))
    assert guard["passed"] is True, guard
    assert guard["scripts"][0]["first_risky_line"] is not None, guard


def test_guard_passes_for_gated_screen_capture_helpers(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    script = fixture / "good-capture.ps1"
    script.write_text(good_screen_capture_helper(), encoding="utf-8")
    guard = visible_runtime_launcher_guard.build_guard(argparse.Namespace(script=[script]))
    assert guard["passed"] is True, guard
    assert guard["scripts"][0]["first_risky_line"] is not None, guard


def test_guard_requires_visible_runtime_forwarding_to_child_helpers(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    good = fixture / "parent-good.ps1"
    bad = fixture / "parent-bad.ps1"
    good.write_text(parent_capture_helper_call(), encoding="utf-8")
    bad.write_text(parent_capture_helper_call(extra_args=""), encoding="utf-8")

    good_guard = visible_runtime_launcher_guard.build_guard(argparse.Namespace(script=[good]))
    bad_guard = visible_runtime_launcher_guard.build_guard(argparse.Namespace(script=[bad]))

    assert good_guard["passed"] is True, good_guard
    assert good_guard["scripts"][0]["child_visible_runtime_invocation_lines"], good_guard
    assert bad_guard["passed"] is False, bad_guard
    assert any("without forwarding -AllowVisibleRuntime" in failure for failure in bad_guard["failures"]), bad_guard


def test_guard_rejects_missing_switch(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    script = fixture / "missing-switch.ps1"
    script.write_text(good_launcher().replace("    [switch]$AllowVisibleRuntime\n", ""), encoding="utf-8")
    guard = visible_runtime_launcher_guard.build_guard(argparse.Namespace(script=[script]))
    assert guard["passed"] is False, guard
    assert any("missing [switch]$AllowVisibleRuntime" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_approval_text(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    script = fixture / "missing-approval.ps1"
    script.write_text(good_launcher().replace("explicit user approval", "operator says yes"), encoding="utf-8")
    guard = visible_runtime_launcher_guard.build_guard(argparse.Namespace(script=[script]))
    assert guard["passed"] is False, guard
    assert any("explicit user approval" in failure for failure in guard["failures"]), guard


def test_guard_rejects_late_guard(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    script = fixture / "late-guard.ps1"
    script.write_text(
        """param(
    [string]$Exe = 'C:\\Clash\\candidate.exe',
    [switch]$AllowVisibleRuntime
)

$ErrorActionPreference = 'Stop'

Start-Process -FilePath $Exe -PassThru

if (-not $AllowVisibleRuntime) {
    throw "Re-run with -AllowVisibleRuntime only after explicit user approval."
}
""",
        encoding="utf-8",
    )
    guard = visible_runtime_launcher_guard.build_guard(argparse.Namespace(script=[script]))
    assert guard["passed"] is False, guard
    assert any("appears after risky runtime call" in failure for failure in guard["failures"]), guard


def test_inventory_rejects_unclassified_risky_root_scripts(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    good = fixture / "good.ps1"
    unknown = fixture / "unknown.ps1"
    good.write_text(good_launcher(), encoding="utf-8")
    unknown.write_text(
        """param()

$process = Start-Process -FilePath 'C:\\Clash\\candidate.exe' -PassThru
""",
        encoding="utf-8",
    )
    guard = visible_runtime_launcher_guard.build_guard(
        argparse.Namespace(script=[good], root=fixture, check_inventory=True)
    )
    assert guard["passed"] is False, guard
    assert guard["inventory"]["unclassified_risky_script_count"] == 1, guard
    assert any("unknown.ps1" in failure for failure in guard["failures"]), guard


def test_inventory_allows_documented_exempt_risky_scripts(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    good = fixture / "good.ps1"
    exempt = fixture / "install_cdb.ps1"
    good.write_text(good_launcher(), encoding="utf-8")
    exempt.write_text(
        """param()

$process = Start-Process -FilePath 'installer.exe' -Wait -PassThru
""",
        encoding="utf-8",
    )
    guard = visible_runtime_launcher_guard.build_guard(
        argparse.Namespace(script=[good], root=fixture, check_inventory=True)
    )
    assert guard["passed"] is True, guard
    assert guard["inventory"]["exempt_risky_script_count"] == 1, guard


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    good = fixture / "good.ps1"
    bad = fixture / "bad.ps1"
    out_json = fixture / "guard.json"
    out_md = fixture / "guard.md"
    good.write_text(good_launcher(), encoding="utf-8")
    bad.write_text(good_launcher().replace("[switch]$AllowVisibleRuntime", "[switch]$Visible"), encoding="utf-8")

    good_run = run_script(
        "--script",
        str(good),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good_run.returncode == 0, good_run.stdout + good_run.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

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
    assert json.loads((fixture / "bad.json").read_text(encoding="utf-8"))["passed"] is False


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "visible-runtime-launcher-guard-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_guard_passes_for_gated_launchers(fixture / "passes")
        test_guard_passes_for_gated_foreground_helpers(fixture / "passes-helper")
        test_guard_passes_for_gated_screen_capture_helpers(fixture / "passes-capture-helper")
        test_guard_requires_visible_runtime_forwarding_to_child_helpers(fixture / "child-forwarding")
        test_guard_rejects_missing_switch(fixture / "missing-switch")
        test_guard_rejects_missing_approval_text(fixture / "missing-approval")
        test_guard_rejects_late_guard(fixture / "late-guard")
        test_inventory_rejects_unclassified_risky_root_scripts(fixture / "inventory-unclassified")
        test_inventory_allows_documented_exempt_risky_scripts(fixture / "inventory-exempt")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("visible runtime launcher guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
