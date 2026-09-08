#!/usr/bin/env python3
"""Cross-checks that the HD validation drivers stay in sync with the checklist.

The Windows Sandbox driver is PowerShell (not runnable on Linux), so these are
text-level invariants: both drivers must cover all five required target IDs and
the three candidate stages, and must keep their visible-runtime approval guards.
"""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import manual_directinput_checklist as checklist  # noqa: E402

SANDBOX = ROOT / "scripts" / "smoke" / "run_clash_hd_full_validation.ps1"
LINUX_SH = ROOT / "scripts" / "smoke" / "run_clash_hd_linux_wine.sh"
LINUX_PY = ROOT / "tools" / "run_hd_linux_validation.py"
VISUAL_SMOKE = ROOT / "scripts" / "smoke" / "run_clash_visual_smoke.ps1"

STAGE_SUFFIXES = ("dynvswitch", "rightbottomcompose", "castlecenter-all")


def test_visual_smoke_single_followup_param() -> None:
    # A branch merge once duplicated the FollowupPoints parameter (parse error)
    # and left a legacy Invoke-MousePath followup block that clobbered the
    # pulse lane's rows. Keep both regressions locked out.
    text = VISUAL_SMOKE.read_text(encoding="utf-8")
    assert text.count("[string]$FollowupPoints") == 1, "duplicate FollowupPoints parameter"
    assert text.count("$followupRows = @()") == 1, "duplicate followupRows init clobbers pulse rows"



def test_powershell_driver_syntax() -> None:
    names = ("powershell.exe", "pwsh") if sys.platform == "win32" else ("pwsh", "powershell.exe")
    powershell = next((found for name in names if (found := shutil.which(name))), None)
    if powershell is None:
        if sys.platform == "win32":
            raise AssertionError("PowerShell is required for driver syntax validation on Windows")
        print("PowerShell syntax check skipped: no PowerShell executable on this platform")
        return
    parse_paths = [str(path) for path in (VISUAL_SMOKE, SANDBOX)]
    if sys.platform != "win32" and powershell.lower().endswith(".exe"):
        # WSL may expose Windows PowerShell through PATH. Its parser needs
        # Windows paths; a native POSIX pwsh (preferred above) needs POSIX paths.
        wslpath = shutil.which("wslpath")
        assert wslpath is not None, "Windows PowerShell on POSIX requires wslpath for source paths"
        converted_paths = []
        for path in parse_paths:
            converted = subprocess.run(
                [wslpath, "-w", path], capture_output=True, text=True, timeout=10, check=True,
            ).stdout.rstrip("\r\n")
            assert converted, f"wslpath returned no Windows path for {path}"
            converted_paths.append(converted)
        parse_paths = converted_paths
    paths = ", ".join("'" + path.replace("'", "''") + "'" for path in parse_paths)
    # Parse source only; do not dot-source, invoke or evaluate either harness.
    # The malformed fixture also confirms this parser catches duplicate keys.
    source = """
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$null = [System.Management.Automation.Language.Parser]::ParseInput(
    '@{ FollowupPoints = 1; FollowupPoints = 2 }', [ref]$tokens, [ref]$parseErrors)
if (-not ($parseErrors | Where-Object ErrorId -eq 'DuplicateKeyInHashLiteral')) {
    throw 'Parser failed to reject the duplicate summary-key fixture'
}
$failures = @()
foreach ($path in @(%s)) {
    $tokens = $null
    $parseErrors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile(
        $path, [ref]$tokens, [ref]$parseErrors)
    foreach ($failure in $parseErrors) {
        $failures += [pscustomobject]@{
            path = $path; line = $failure.Extent.StartLineNumber; error = $failure.ErrorId
        }
    }
}
ConvertTo-Json -InputObject @($failures) -Compress
""" % paths
    encoded = base64.b64encode(source.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    failures = json.loads(result.stdout.lstrip("\ufeff"))
    assert failures == [], failures

def test_sandbox_driver_uses_pulse_lane_and_authoritative_specs() -> None:
    text = SANDBOX.read_text(encoding="utf-8")
    assert "'-InputMode', 'pulse'" in text, "sandbox driver must drive the pulse lane"
    assert "'-PulseRouteSteps'" in text
    assert "manual_directinput_run_plan" in text, "followup specs must come from the run plan, not hardcoded copies"
    for legacy_args in ("'-MoveMode', 'auto'", "'-ClickMode', 'sendinput'"):
        assert legacy_args not in text, f"legacy engine-invisible input args resurfaced: {legacy_args}"


def test_linux_worker_strips_named_points() -> None:
    text = LINUX_SH.read_text(encoding="utf-8")
    assert 'p="${p##*:}"' in text, "worker must accept name:x,y aim points from the run plan"


def test_sandbox_driver_covers_all_targets() -> None:
    text = SANDBOX.read_text(encoding="utf-8")
    for item_id in checklist.REQUIRED_IDS:
        assert item_id in text, f"sandbox driver is missing target id {item_id}"
    for suffix in STAGE_SUFFIXES:
        assert suffix in text, f"sandbox driver is missing stage suffix {suffix}"


def test_sandbox_driver_has_guards() -> None:
    text = SANDBOX.read_text(encoding="utf-8")
    assert "AllowVisibleRuntime" in text
    assert "ApprovalRecord" in text
    assert "prepare_addon_flags_fixture.py" in text
    assert "run-manifest.json" in text
    # Never fabricates observations: statuses start pending, fields blank.
    assert "status = 'pending'" in text
    assert "run_clash_visual_smoke.ps1" in text


def test_linux_driver_covers_all_targets() -> None:
    text = LINUX_PY.read_text(encoding="utf-8")
    # The Python driver derives target ids from the checklist module, so assert
    # the wiring points exist rather than hardcoded ids.
    assert "REQUIRED_IDS" in text
    assert "run_clash_hd_linux_wine.sh" in text
    assert "prepare_addon_flags_fixture.py" in text


def test_linux_worker_has_guard() -> None:
    text = LINUX_SH.read_text(encoding="utf-8")
    assert "--allow-visible-runtime" in text
    assert "xdotool" in text
    assert "wine" in text


def run_tests() -> None:
    test_sandbox_driver_covers_all_targets()
    test_sandbox_driver_has_guards()
    test_linux_driver_covers_all_targets()
    test_linux_worker_has_guard()
    test_visual_smoke_single_followup_param()
    test_powershell_driver_syntax()
    test_sandbox_driver_uses_pulse_lane_and_authoritative_specs()
    test_linux_worker_strips_named_points()


def main() -> int:
    run_tests()
    print("HD validation driver cross-checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
