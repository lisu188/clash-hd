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
    assert guard["checks"]["intro_skip_policy"]["passed"] is True
    assert guard["checks"]["windowed_mode"]["passed"] is True
    assert guard["checks"]["window_health_stop"]["passed"] is True
    assert guard["checks"]["window_handle_freshness"]["passed"] is True
    assert guard["checks"]["promotion_boundary"]["passed"] is True


def test_nonexecuting_syntax_hash_and_preflight_boundary(fixture: Path) -> None:
    """Parse the full producer; execute only its two file-reading helpers."""
    powershell = shutil.which("powershell.exe") or shutil.which("pwsh")
    if not powershell:
        print("PowerShell syntax/helper check unavailable on this platform")
        return
    fixture.mkdir(parents=True)
    sample = fixture / "hash sample.bin"
    sample.write_bytes(b"abc")
    config = fixture / "dxcfg.ini"
    config.write_text("[dxcfg]\ndisplay=application\npresentation=windowed\n", encoding="ascii")
    def quoted(path: Path) -> str:
        return "'" + str(path.resolve()).replace("'", "''") + "'"
    command = r"""
$ErrorActionPreference = 'Stop'
$tokens = $null; $parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(HARNESS_PATH, [ref]$tokens, [ref]$parseErrors)
if (@($parseErrors).Count) { throw ($parseErrors | Out-String) }
$names = @($ast.ParamBlock.Parameters | ForEach-Object { $_.Name.VariablePath.UserPath.ToLowerInvariant() })
if (@($names | Select-Object -Unique).Count -ne $names.Count) { throw 'duplicate producer parameters' }
$functions = @($ast.FindAll({ param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
    $node.Name -in @('Get-SoakFileSha256', 'Get-DxcfgWindowedStatus', 'Get-VisibleRuntimeApprovalToken')
}, $true))
if ($functions.Count -ne 3) { throw 'missing file-only helpers' }
foreach ($function in $functions) { . ([scriptblock]::Create($function.Extent.Text)) }
function Get-FileHash { throw 'Get-FileHash must not be required' }
$actual = Get-SoakFileSha256 -Path SAMPLE_PATH
if ($actual -cne 'BA7816BF8F01CFEA414140DE5DAE2223B00361A396177A9CB410FF61F20015AD') { throw 'wrong SHA-256' }
$config = Get-DxcfgWindowedStatus -Path CONFIG_PATH
if (-not $config.Passed -or $config.Sha256 -cne (Get-SoakFileSha256 -Path CONFIG_PATH)) { throw 'config hash differs' }
if ((Get-DxcfgWindowedStatus -Path MISSING_PATH).Passed) { throw 'missing config accepted' }
$configFields = @($ast.FindAll({ param($node)
    $node -is [System.Management.Automation.Language.SubExpressionAst] -and
    $node.Extent.Text.Contains("'missing-windowed-config'")
}, $true))
if ($configFields.Count -ne 1) { throw 'missing explicit absent-config token field' }
$windowedMode = [pscustomobject]@{ Sha256 = $null }
$missingField = & ([scriptblock]::Create($configFields[0].Extent.Text))
if ($missingField -cne 'missing-windowed-config') { throw 'missing config field became empty' }
$token = Get-VisibleRuntimeApprovalToken -Fields @('fixture-source', $missingField, 'fixture-stage')
if ($token -notmatch '^[0-9a-f]{16}$') { throw 'missing config blocks the approval boundary' }
$windowedMode = [pscustomobject]@{ Sha256 = $actual }
if ((& ([scriptblock]::Create($configFields[0].Extent.Text))) -cne $actual) { throw 'valid config token field changed' }
$failed = $false
try { Get-SoakFileSha256 -Path MISSING_PATH | Out-Null } catch { $failed = $true }
if (-not $failed) { throw 'missing hash source accepted' }
$standingCalls = @($ast.FindAll({ param($node)
    $node -is [System.Management.Automation.Language.CommandAst] -and $node.GetCommandName() -eq 'Get-InputStandingStatus'
}, $true))
$guard = $ast.Extent.Text.IndexOf('if ($VisibleRuntimeApprovalToken -ne $expectedVisibleRuntimeApprovalToken)')
if ($guard -lt 0 -or $standingCalls.Count -ne 1 -or $standingCalls[0].Extent.StartOffset -le $guard) {
    throw 'input-standing inspection precedes exact approval'
}
'NONEXECUTING_SOAK_PREFLIGHT_PASS'
"""
    for name, path in (("HARNESS_PATH", HARNESS), ("SAMPLE_PATH", sample), ("CONFIG_PATH", config),
                       ("MISSING_PATH", fixture / "missing.bin")):
        command = command.replace(name, quoted(path))
    result = subprocess.run([powershell, "-NoProfile", "-Command", command], capture_output=True, text=True, check=False)
    assert result.returncode == 0 and "NONEXECUTING_SOAK_PREFLIGHT_PASS" in result.stdout, result.stdout + result.stderr


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


def test_guard_rejects_missing_visible_runtime_token(fixture: Path) -> None:
    bad = harness_text()
    bad = bad.replace("    [string]$VisibleRuntimeApprovalToken = '',\n", "")
    bad = bad.replace("    '-VisibleRuntimeApprovalToken', (Quote-Arg $expectedVisibleRuntimeApprovalToken),\n", "")
    bad = bad.replace(
        "if (-not $VisibleRuntimeApprovalToken) {\n"
        "    throw 'Visible runtime execution requires -VisibleRuntimeApprovalToken from a fresh dry-run approval packet.'\n"
        "}\n"
        "if ($VisibleRuntimeApprovalToken -ne $expectedVisibleRuntimeApprovalToken) {\n"
        "    throw \"Visible runtime approval token does not match this command shape. Expected $expectedVisibleRuntimeApprovalToken.\"\n"
        "}\n",
        "",
    )
    script = write_fixture(fixture / "missing-token.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("visibleruntimeapprovaltoken" in failure.lower() for failure in guard["failures"]), guard


def test_guard_rejects_missing_visible_runtime_expiry(fixture: Path) -> None:
    bad = harness_text()
    bad = bad.replace("    [string]$VisibleRuntimeApprovalExpiresUtc = '',\n", "")
    bad = bad.replace("    '-VisibleRuntimeApprovalExpiresUtc', (Quote-Arg $approvalExpiresUtc),\n", "")
    bad = bad.replace(
        "if (-not $VisibleRuntimeApprovalExpiresUtc) {\n"
        "    throw 'Visible runtime execution requires -VisibleRuntimeApprovalExpiresUtc from a fresh dry-run approval packet.'\n"
        "}\n"
        "try {\n"
        "    $approvalExpiry = [System.DateTimeOffset]::Parse(\n"
        "        $VisibleRuntimeApprovalExpiresUtc,\n"
        "        [System.Globalization.CultureInfo]::InvariantCulture,\n"
        "        [System.Globalization.DateTimeStyles]::AssumeUniversal\n"
        "    ).ToUniversalTime()\n"
        "} catch {\n"
        "    throw \"Visible runtime approval expiry is invalid: $VisibleRuntimeApprovalExpiresUtc\"\n"
        "}\n"
        "if ([System.DateTimeOffset]::UtcNow -gt $approvalExpiry) {\n"
        "    throw \"Visible runtime approval expired at $($approvalExpiry.ToString('o')). Run a fresh dry-run and copy the new approval packet.\"\n"
        "}\n",
        "",
    )
    script = write_fixture(fixture / "missing-expiry.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("approval expiry" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_visible_runtime_minimum_ttl(fixture: Path) -> None:
    bad = harness_text()
    bad = bad.replace("$minApprovalTtlMinutes = 30\n", "")
    bad = bad.replace("        min_ttl_minutes = $minApprovalTtlMinutes\n", "")
    bad = bad.replace(
        "$approvalRemaining = $approvalExpiry - [System.DateTimeOffset]::UtcNow\n"
        "if ($approvalRemaining -lt [System.TimeSpan]::FromMinutes($minApprovalTtlMinutes)) {\n"
        "    throw \"Visible runtime approval expires too soon at $($approvalExpiry.ToString('o')). Run a fresh dry-run so at least $minApprovalTtlMinutes minutes remain.\"\n"
        "}\n",
        "",
    )
    script = write_fixture(fixture / "missing-min-ttl.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("minimum TTL" in failure or "30-minute" in failure for failure in guard["failures"]), guard


def test_guard_rejects_launch_before_approval_boundary(fixture: Path) -> None:
    bad = harness_text().replace(
        "if (-not $VisibleRuntimeApprovalToken) {\n",
        "Start-Process -FilePath $CandidateFull -WorkingDirectory $WorkDirFull -PassThru\n"
        "if (-not $VisibleRuntimeApprovalToken) {\n",
        1,
    )
    script = write_fixture(fixture / "launch-before-approval.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("must appear before visible process launch" in failure for failure in guard["failures"]), guard


def test_guard_rejects_intro_skip_default_drift(fixture: Path) -> None:
    bad = harness_text().replace("[string]$IntroSkipClickMode = 'postmessage'", "[string]$IntroSkipClickMode = 'sendinput'")
    script = write_fixture(fixture / "intro-mode.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("IntroSkipClickMode default" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_transition_safe_intro_stop(fixture: Path) -> None:
    bad = harness_text().replace("        $args += '--stop-click-repeat-on-drift'\n", "")
    script = write_fixture(fixture / "intro-transition-stop.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("--stop-click-repeat-on-drift" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_windowed_contract(fixture: Path) -> None:
    bad = harness_text().replace("$presentation -ne 'windowed'", "$presentation -ne 'fullscreen'", 1)
    script = write_fixture(fixture / "window-mode.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("windowed-mode contract" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_window_health_stop(fixture: Path) -> None:
    bad = harness_text().replace("IsHungAppWindow", "WindowLooksHung")
    script = write_fixture(fixture / "window-health.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("window-health marker" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_window_handle_freshness(fixture: Path) -> None:
    bad = harness_text().replace("    '--window-reacquire-attempts', \"$WindowReacquireAttempts\",\n", "")
    script = write_fixture(fixture / "window-freshness.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert guard["checks"]["window_handle_freshness"]["passed"] is False, guard
    assert any("--window-reacquire-attempts" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_window_stable_gate(fixture: Path) -> None:
    bad = harness_text().replace("$WindowStableSamples", "$WindowSettleSamples")
    script = write_fixture(fixture / "window-stable.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("$WindowStableSamples" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_wrapper_transition_classification(fixture: Path) -> None:
    bad = harness_text().replace("FindAliveHiddenWindowForProcess", "FindSomeWindow")
    script = write_fixture(fixture / "wrapper-transition.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert guard["checks"]["wrapper_transition_classification"]["passed"] is False, guard
    assert any(
        "FindAliveHiddenWindowForProcess" in failure for failure in guard["failures"]
    ), guard


def test_guard_rejects_missing_wrapper_error_dialog_report_field(fixture: Path) -> None:
    bad = harness_text().replace("wrapper_error_dialog_observed", "dialog_seen")
    script = write_fixture(fixture / "wrapper-dialog-field.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert guard["checks"]["wrapper_transition_classification"]["passed"] is False, guard


def test_guard_rejects_missing_input_standing_preflight(fixture: Path) -> None:
    bad = harness_text().replace("Get-InputStandingStatus", "Get-SomeStatus")
    script = write_fixture(fixture / "input-standing.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert guard["checks"]["input_standing_preflight"]["passed"] is False, guard
    assert any("Get-InputStandingStatus" in failure for failure in guard["failures"]), guard


def test_guard_rejects_input_standing_preflight_that_does_not_fail_closed(fixture: Path) -> None:
    bad = harness_text().replace(
        'throw "Input standing preflight failed',
        'Write-Host "Input standing preflight failed',
    )
    script = write_fixture(fixture / "input-standing-soft.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any(
        "does not fail closed before launch" in failure for failure in guard["failures"]
    ), guard


def test_guard_rejects_missing_intro_execute_fragment(fixture: Path) -> None:
    bad = harness_text().replace("    '-IntroSkipClickMode', (Quote-Arg $IntroSkipClickMode),\n", "")
    script = write_fixture(fixture / "intro-execute.ps1", bad)
    guard = hd_soak_harness_guard.build_guard(script)
    assert guard["passed"] is False, guard
    assert any("dry-run execute command does not include -IntroSkipClickMode" in failure for failure in guard["failures"]), guard


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
        test_nonexecuting_syntax_hash_and_preflight_boundary(fixture / "nonexecuting-preflight")
        test_guard_rejects_stage_drift(fixture / "stage")
        test_guard_rejects_repo_candidate_default(fixture / "repo-candidate")
        test_guard_rejects_missing_explicit_approval(fixture / "approval")
        test_guard_rejects_dry_run_execute_command_without_require_pass(fixture / "require-pass")
        test_guard_rejects_dry_run_execute_command_without_json(fixture / "json")
        test_guard_rejects_missing_visible_runtime_token(fixture / "token")
        test_guard_rejects_missing_visible_runtime_expiry(fixture / "expiry")
        test_guard_rejects_missing_visible_runtime_minimum_ttl(fixture / "minimum-ttl")
        test_guard_rejects_launch_before_approval_boundary(fixture / "launch-order")
        test_guard_rejects_intro_skip_default_drift(fixture / "intro-mode")
        test_guard_rejects_missing_transition_safe_intro_stop(fixture / "intro-transition-stop")
        test_guard_rejects_missing_windowed_contract(fixture / "window-mode")
        test_guard_rejects_missing_window_health_stop(fixture / "window-health")
        test_guard_rejects_missing_window_handle_freshness(fixture / "window-freshness")
        test_guard_rejects_missing_window_stable_gate(fixture / "window-stable")
        test_guard_rejects_missing_intro_execute_fragment(fixture / "intro-execute")
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
