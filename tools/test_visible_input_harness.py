#!/usr/bin/env python3
"""Offline visible-input fixtures; every window/capture/input operation is mocked."""
from __future__ import annotations

import argparse
import base64
from contextlib import ExitStack
import ctypes
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

import menu_pulse_click as pulse

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts/smoke/run_clash_visual_smoke.ps1"


class GeometryTests(unittest.TestCase):
    def test_requested_resolution_preserves_native_1080_pixels_and_legacy(self):
        for size in ((800, 600), (1920, 1080), (802, 602)):
            self.assertEqual(pulse.parse_resolution(f"{size[0]}x{size[1]}"), size)
            image = Image.new("RGB", size)
            image.putpixel((size[0] - 1, size[1] - 1), (30, 80, 190))
            frame = pulse.normalize_frame(image, size)
            self.assertEqual(frame.shape, (size[1], size[0], 3))
            self.assertEqual(frame[-1, -1].tolist(), [30, 80, 190])
        scaled = pulse.normalize_frame(Image.new("RGB", (1280, 720), (3, 4, 5)), (1920, 1080))
        self.assertEqual(scaled.shape, (1080, 1920, 3))
        with self.assertRaises(ValueError):
            pulse.normalize_frame(Image.new("RGB", (800, 600)), (1920, 1080))

    def test_logical_targets_map_to_measured_client_and_reject_ambiguity(self):
        self.assertEqual(pulse.logical_to_screen((1919, 1079), (-1280, 0, 1280, 720), (1920, 1080)), (-1, 719))
        self.assertEqual(pulse.logical_to_screen((400, 300), (3, 26, 800, 600), (800, 600)), (403, 326))
        for target, geometry in [((1920, 100), (0, 0, 1920, 1080)), ((-1, 0), (0, 0, 1920, 1080)),
                                 ((0, 0), (0, 0, 800, 600)), ((0, 0), (0, 0, 0, 0))]:
            with self.assertRaises(ValueError):
                pulse.logical_to_screen(target, geometry, (1920, 1080))

    def test_placement_uses_nonclient_offsets_and_negative_monitor_origins(self):
        self.assertEqual(pulse.client_placement((83, 106, 1920, 1080), (80, 80, 2006, 1186), (0, 0, 1920, 1080)), (-3, -26))
        self.assertEqual(pulse.client_placement((-1900, 40, 1920, 1080), (-1903, 14, 23, 1120), (-1920, 0, 0, 1080)), (-1923, -26))
        with self.assertRaisesRegex(ValueError, "cannot fit"):
            pulse.client_placement((0, 0, 1920, 1080), (0, 0, 1920, 1080), (0, 0, 1280, 720))

    def test_accessibility_checks_the_target_owner_not_only_window_center(self):
        with patch.object(pulse, "client_geometry", return_value=(0, 0, 1920, 1080)), \
             patch.object(pulse, "monitor_rect", return_value=(0, 0, 1920, 1080)), \
             patch.object(pulse.user32, "WindowFromPoint", return_value=42), \
             patch.object(pulse.user32, "GetAncestor", return_value=42):
            report = pulse.target_accessibility(99, (1900, 1060), (1920, 1080))
            self.assertFalse(report["accessible"])
            self.assertEqual(report["screen_target"], [1900, 1060])

    def test_centered_exit_region_moves_without_scaling_native_controls(self):
        self.assertTrue(pulse.in_menu_exit_zone((300, 280), (800, 600)))
        self.assertTrue(pulse.in_menu_exit_zone((860, 520), (1920, 1080)))
        self.assertFalse(pulse.in_menu_exit_zone((300, 280), (1920, 1080)))


class InputBoundaryTests(unittest.TestCase):
    def test_reused_window_handle_is_not_treated_as_the_selected_process(self):
        def owner(_hwnd, value):
            ctypes.cast(value, ctypes.POINTER(pulse.wintypes.DWORD)).contents.value = 42
            return 1

        with patch.object(pulse.user32, "IsWindow", return_value=True), \
             patch.object(pulse.user32, "GetWindowThreadProcessId", side_effect=owner), \
             patch.object(pulse, "find_window", return_value=100) as find:
            self.assertEqual(pulse.live_hwnd(7, 99), 100)
        find.assert_called_once_with(7)

    def test_inaccessible_target_never_receives_a_pulse(self):
        frame = np.zeros((600, 800, 3), dtype=np.int16)
        with patch.object(pulse, "live_hwnd", return_value=99), \
             patch.object(pulse, "fit_client", return_value={}), \
             patch.object(pulse, "client_geometry", return_value=(0, 0, 800, 600)), \
             patch.object(pulse, "wake_foreground"), patch.object(pulse, "focus", return_value=True), \
             patch.object(pulse, "target_accessibility", return_value={"accessible": False}), \
             patch.object(pulse, "pulse_stream") as stream:
            report = pulse.aim(1, 99, (700, 500), 4.4, frame, None, .028, 10, time.time() + 10)
        stream.assert_not_called()
        self.assertFalse(report["converged"])
        self.assertTrue(report["target_inaccessible"])

    def test_recreated_or_occluded_window_is_checked_again_before_click(self):
        frame = np.zeros((600, 800, 3), dtype=np.int16)
        args = argparse.Namespace(aim_points="700,500", initial_gain=4.4, pid=1, aim_tolerance=10,
                                  logical_size=(800, 600), aim_only=False, json=None)
        aimed = dict(frame=frame, hwnd=99, last_pos=(700, 500), gain=4.4, converged=True,
                     aimed_pos=[700, 500], pulse_delta=[159, 114])
        with patch.object(pulse, "aim", return_value=aimed), patch.object(pulse, "live_hwnd", return_value=100), \
             patch.object(pulse, "focus", return_value=True), \
             patch.object(pulse, "target_accessibility", return_value={"accessible": False}), \
             patch.object(pulse, "click_while_pulsing") as click, patch.object(pulse, "emit"):
            report = {"steps": []}
            code = pulse.run_aim_points(args, report, 99, frame, .028, time.time() + 10)
        click.assert_not_called()
        self.assertEqual(code, 2)
        self.assertFalse(report["steps"][0]["clicked"])

    def test_manual_observation_captures_original_pair_without_input_or_focus(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            args = argparse.Namespace(json=Path(temp) / "observation.json", observe_seconds=1,
                                      observe_interval_ms=1000, pid=1, logical_size=(800, 600))
            stack.enter_context(patch.object(pulse, "live_hwnd", return_value=99))
            stack.enter_context(patch.object(pulse, "client_geometry", return_value=(3, 26, 800, 600)))
            stack.enter_context(patch.object(pulse, "grab_image", side_effect=lambda _: Image.new("RGB", (800, 600), (20, 40, 60))))
            stack.enter_context(patch.object(pulse, "target_accessibility", return_value={"accessible": True}))
            stack.enter_context(patch.object(pulse.time, "monotonic", side_effect=[0, 0, 2, 2]))
            stack.enter_context(patch.object(pulse.time, "sleep"))
            stack.enter_context(patch.object(pulse, "emit"))
            forbidden = [stack.enter_context(patch.object(pulse, name, side_effect=AssertionError(name)))
                         for name in ("focus", "wake_foreground", "fit_client", "send_rel", "send_button", "pulse_stream", "click_while_pulsing")]
            result = {}
            self.assertEqual(pulse.observe_only(args, result, 99), 0)
            self.assertTrue(result["capture_complete"])
            self.assertFalse(result["manual_input_accepted"])
            self.assertFalse(result["promotion_ready"])
            self.assertTrue(result["operator_observation_required"])
            pair = result["observations"][0]
            self.assertEqual(pair["operator_result"], "pending")
            self.assertEqual(len(pair["frames"]), 2)
            self.assertNotEqual(pair["frames"][0]["path"], pair["frames"][1]["path"])
            for item in pair["frames"]:
                with Image.open(item["path"]) as image:
                    self.assertEqual(image.size, (800, 600))
                self.assertEqual(item["client"], [3, 26, 800, 600])
            self.assertIn("tear_check", pair)
            for mock in forbidden:
                mock.assert_not_called()

    def test_manual_observer_refuses_occluded_client_before_capture(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            args = argparse.Namespace(json=Path(temp) / "observation.json", observe_seconds=1,
                                      observe_interval_ms=1000, pid=1, logical_size=(800, 600))
            stack.enter_context(patch.object(pulse, "live_hwnd", return_value=99))
            stack.enter_context(patch.object(pulse, "client_geometry", return_value=(3, 26, 800, 600)))
            stack.enter_context(patch.object(pulse, "target_accessibility", return_value={"accessible": False}))
            stack.enter_context(patch.object(pulse.time, "monotonic", side_effect=[0, 0]))
            stack.enter_context(patch.object(pulse, "emit"))
            capture = stack.enter_context(patch.object(pulse, "grab_image"))
            result = {}
            self.assertEqual(pulse.observe_only(args, result, 99), 2)
            capture.assert_not_called()
            self.assertFalse(result["capture_complete"])
            self.assertFalse(result["manual_input_accepted"])
            self.assertIn("occluded", result["observations"][0]["error"])


class PowerShellTests(unittest.TestCase):
    def powershell(self, body):
        shell = shutil.which("powershell.exe") or shutil.which("pwsh")
        if shell is None:
            self.skipTest("PowerShell unavailable; Python geometry/input fixtures still run")
        source_path = str(HARNESS)
        if sys.platform != "win32" and shell.lower().endswith(".exe"):
            translator = shutil.which("wslpath")
            self.assertIsNotNone(translator, "Windows PowerShell on POSIX requires wslpath")
            source_path = subprocess.run([translator, "-w", source_path], text=True, capture_output=True,
                                         check=True, timeout=10).stdout.rstrip("\r\n")
            self.assertTrue(source_path)
        script = ("$ErrorActionPreference='Stop';$sourcePath='" + source_path.replace("'", "''")
                  + "';$tokens=$null;$errors=$null;$ast=[System.Management.Automation.Language.Parser]::ParseFile($sourcePath,[ref]$tokens,[ref]$errors);" + body)
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        result = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_real_parser_and_parameter_uniqueness(self):
        report = self.powershell("if($errors.Count){throw ($errors|Out-String)};@{parameters=@($ast.ParamBlock.Parameters.Name.VariablePath.UserPath)}|ConvertTo-Json -Compress")
        names = [name.lower() for name in report["parameters"]]
        self.assertEqual(len(names), len(set(names)))
        for required in ("resolution", "stage", "observeprocessid"):
            self.assertIn(required, names)

    def test_cleanup_only_matches_selected_executable(self):
        report = self.powershell(r"""
if($errors.Count){throw ($errors|Out-String)}
$fn=$ast.Find({param($n)$n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Stop-ClashProcesses'},$true)
Invoke-Expression $fn.Extent.Text
$Exe='C:\ClashTests\owned\candidate.exe'
$script:stopped=@()
function Get-Process { @([pscustomobject]@{Id=1;Path=$Exe},[pscustomobject]@{Id=2;Path='C:\ClashTests\other\candidate.exe'},[pscustomobject]@{Id=3;Path='C:\Tools\cdb.exe'}) }
function Stop-Process { param([Parameter(ValueFromPipeline)]$InputObject,[switch]$Force) process {$script:stopped+=$InputObject.Id} }
Stop-ClashProcesses
@{stopped=@($script:stopped)}|ConvertTo-Json -Compress
""")
        self.assertEqual(report["stopped"], [1])

    def test_raw_capture_root_rejects_repository_and_normalized_children(self):
        report = self.powershell(r"""
if($errors.Count){throw ($errors|Out-String)}
$fn=$ast.Find({param($n)$n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Assert-ExternalCaptureRoot'},$true)
Invoke-Expression $fn.Extent.Text
$refused=@(foreach($candidate in @('C:\fixture\repo','C:\fixture\repo\captures','C:\fixture\other\..\repo\captures')) {
    try { Assert-ExternalCaptureRoot -Path $candidate -Repository 'C:\fixture\repo';$false } catch {$true}
})
Assert-ExternalCaptureRoot -Path 'C:\fixture\repo-extra\captures' -Repository 'C:\fixture\repo'
Assert-ExternalCaptureRoot -Path 'C:\ClashCaptures\visible-input' -Repository 'C:\fixture\repo'
@{refused=$refused}|ConvertTo-Json -Compress
""")
        self.assertEqual(report["refused"], [True, True, True])

    def test_sandbox_callers_map_external_outputs_and_preserve_approval(self):
        shell = shutil.which("powershell.exe") or shutil.which("pwsh")
        if sys.platform != "win32" and shell and not shell.lower().endswith(".exe"):
            self.skipTest("Sandbox output-mapping fixture requires Windows drive-path semantics")
        report = self.powershell(r"""
if($errors.Count){throw ($errors|Out-String)}
$guard=$ast.Find({param($n)$n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Assert-ExternalCaptureRoot'},$true)
Invoke-Expression $guard.Extent.Text
$rows=@()
foreach($callerName in @('run_clash_windows_sandbox.ps1','run_clash_hd_full_validation.ps1')) {
    $callerPath=Join-Path (Split-Path -Parent $sourcePath) $callerName
    $callerAst=[System.Management.Automation.Language.Parser]::ParseFile($callerPath,[ref]$tokens,[ref]$errors)
    if($errors.Count){throw ($errors|Out-String)}
    foreach($functionName in @('New-SandboxCapturePlan','ConvertTo-XmlText')) {
        $definition=$callerAst.Find({param($n)$n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $functionName},$true)
        if(-not $definition){throw "Missing function $functionName"}
        Invoke-Expression $definition.Extent.Text
    }
    $repo='C:\fixture\repo';$game='C:\fixture\game';$pythonDir='C:\fixture\python'
    $customRoot="C:\fixture\custom & team's captures"
    $capturePlan=New-SandboxCapturePlan -Path $customRoot -Repository $repo -Prefix 'fixture'
    if($capturePlan.OutputRoot -ne $customRoot){throw 'Custom external root changed'}
    $second=New-SandboxCapturePlan -Path $customRoot -Repository $repo -Prefix 'fixture'
    if($capturePlan.HostRunDirectory -eq $second.HostRunDirectory){throw 'Run directories are not unique'}
    $driveRootPlan=New-SandboxCapturePlan -Path 'C:\' -Repository $repo -Prefix 'fixture'
    if($driveRootPlan.OutputRoot -ne 'C:\'){throw 'Drive-root output lost its absolute path'}
    foreach($badRoot in @($repo, "$repo\captures", 'C:\fixture\elsewhere\..\repo\captures')) {
        $refused=$false
        try {New-SandboxCapturePlan -Path $badRoot -Repository $repo -Prefix 'fixture'|Out-Null} catch {$refused=$true}
        if(-not $refused){throw "Repository capture root accepted: $badRoot"}
    }
    $defaultExpression=$callerAst.ParamBlock.Parameters|Where-Object {$_.Name.VariablePath.UserPath -eq 'OutRoot'}
    if($defaultExpression.DefaultValue.Value -ne 'C:\ClashCaptures\windows-sandbox'){throw 'External capture default drifted'}
    foreach($variableName in @('runHostDir','runSandboxDir')) {
        $assignment=$callerAst.Find({param($n)$n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq ('$'+$variableName)},$true)
        Invoke-Expression $assignment.Extent.Text
    }
    Assert-ExternalCaptureRoot -Path $runHostDir -Repository $repo
    Assert-ExternalCaptureRoot -Path $runSandboxDir -Repository 'C:\Repo'
    $command='fixture-only command, never executed'
    $wsbAssignment=$callerAst.Find({param($n)$n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$wsb'},$true)
    $configuration=[xml](Invoke-Expression $wsbAssignment.Right.Extent.Text)
    $mappings=@($configuration.Configuration.MappedFolders.MappedFolder)
    $captureMappings=@($mappings|Where-Object {$_.SandboxFolder -eq $runSandboxDir})
    if($captureMappings.Count -ne 1 -or $captureMappings[0].HostFolder -ne $runHostDir -or $captureMappings[0].ReadOnly -ne 'false'){throw 'External capture mapping does not match the run plan'}
    $gameMappings=@($mappings|Where-Object {$_.SandboxFolder -eq 'C:\HostClash'})
    if($gameMappings.Count -ne 1 -or $gameMappings[0].ReadOnly -ne 'true'){throw 'Original game mapping changed'}
    $entryAssignment=$callerAst.Find({param($n)$n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$entryScript'},$true)
    $sandboxSmokeRoot="$runSandboxDir\visual-smoke";$entrySandboxPath="$runSandboxDir\sandbox-entry.ps1"
    $sandboxPython='C:\HostPython\python.exe';$sandboxCandidate='C:\ClashTests\fixture.exe'
    $approvedCases=@()
    foreach($AllowVisibleRuntime in @($false,$true)) {
        # Evaluate only the here-string template, then parse its guest program.
        $entryText=Invoke-Expression $entryAssignment.Right.Extent.Text
        $entryAst=[System.Management.Automation.Language.Parser]::ParseInput($entryText,[ref]$tokens,[ref]$errors)
        if($errors.Count){throw ($errors|Out-String)}
        $Repo='C:\Repo';$RunDir=$runSandboxDir;$Python=$sandboxPython;$Candidate=$sandboxCandidate;$GameWork='C:\Clash'
        $t=@{id='fixture-target';workdir=$GameWork;followup='';pulse_route_steps='load:302,211'};$exe=$Candidate
        $targetAssignment=$entryAst.Find({param($n)$n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$targetOut'},$true)
        if($targetAssignment){Invoke-Expression $targetAssignment.Extent.Text}
        $smokeAssignment=$entryAst.Find({param($n)$n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$smokeArgs'},$true)
        Invoke-Expression $smokeAssignment.Extent.Text
        if($callerName -eq 'run_clash_windows_sandbox.ps1') {
            $forwarding=$entryAst.Find({param($n)$n -is [System.Management.Automation.Language.IfStatementAst] -and $n.Clauses[0].Item1.Extent.Text -like '[[]bool]::Parse*'},$true)
            if(-not $forwarding){throw 'Conditional approval forwarding missing'}
            Invoke-Expression $forwarding.Extent.Text
            if(($smokeArgs -contains '-AllowVisibleRuntime') -ne $AllowVisibleRuntime){throw 'Approval switch was not preserved'}
        }
        $outIndex=[Array]::IndexOf($smokeArgs,'-OutRoot')
        if($outIndex -lt 0){throw 'Smoke output argument missing'}
        $guestOutput=$smokeArgs[$outIndex+1]
        Assert-ExternalCaptureRoot -Path $guestOutput -Repository 'C:\Repo'
        if(-not $guestOutput.StartsWith($runSandboxDir+'\')){throw 'Smoke output bypasses capture mapping'}
        $approvedCases+=($smokeArgs -contains '-AllowVisibleRuntime')
    }
    $rows+=@{caller=$callerName;approval_forwarded=$approvedCases;external_mapping=$true;guest_program_parsed=$true}
}
@{rows=$rows}|ConvertTo-Json -Depth 4 -Compress
""")
        self.assertEqual(len(report["rows"]), 2)
        for row in report["rows"]:
            self.assertTrue(row["external_mapping"])
            self.assertTrue(row["guest_program_parsed"])
        self.assertEqual(report["rows"][0]["approval_forwarded"], [False, True])

    def test_framed_quality_stays_incomplete_without_candidate_and_minimap_context(self):
        report = self.powershell(r"""
if($errors.Count){throw ($errors|Out-String)}
$fn=$ast.Find({param($n)$n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Invoke-GameplayFrameCheck'},$true)
Invoke-Expression $fn.Extent.Text
function Test-Path { throw 'legacy coverage must not run for framed candidates' }
$NoGameplayCheck=$false
$rows=@(foreach($Stage in @('fixture-framed-validation','fixture-completehd-validation','unknown-framed-stage')) {
    Invoke-GameplayFrameCheck -Path 'unused.png' -Json 'unused.json'
})
@{rows=$rows}|ConvertTo-Json -Depth 4 -Compress
""")
        self.assertEqual(len(report["rows"]), 3)
        for row in report["rows"]:
            self.assertEqual(row["Status"], "incomplete")
            self.assertEqual(row["ExitCode"], 2)
            self.assertFalse(row["Attempted"])
            self.assertFalse(row["GameplayFrameLikely"])
            self.assertIsNone(row["Json"])
            self.assertIn("framed-quality-requires-candidate-context-and-observed-minimap", row["Warnings"])

    def test_manual_branch_invokes_only_observer_and_keeps_acceptance_pending(self):
        report = self.powershell(r"""
if($errors.Count){throw ($errors|Out-String)}
$branch=$ast.Find({param($n)$n -is [System.Management.Automation.Language.IfStatementAst] -and $n.Clauses[0].Item1.Extent.Text -eq "$InputMode -eq 'manual'"},$true)
if(-not $branch){$branch=$ast.Find({param($n)$n -is [System.Management.Automation.Language.IfStatementAst] -and $n.Clauses[0].Item1.Extent.Text -like '*InputMode*' -and $n.Clauses[0].Item1.Extent.Text -like "*-eq 'manual'"},$true)}
if(-not $branch){throw 'manual branch missing'}
$process=[pscustomobject]@{Id=9};$outDir='C:\ClashCaptures\fixture';$Exe='C:\ClashTests\fixture.exe';$Stage='fixture-validation';$Resolution='1920x1080';$RunSeconds=30;$ObserveIntervalMs=1500;$ownsProcess=$false
function Invoke-MenuPulseTool { param($Process,$Json,$ToolArgs) if($ToolArgs[0] -ne '--observe-only'){throw 'input requested'};[pscustomobject]@{Result=[pscustomobject]@{capture_complete=$true};Json=$Json;ExitCode=0} }
function Get-FileHash { [pscustomobject]@{Hash=('a'*64)} }
$body=$branch.Clauses[0].Item2.Extent.Text
Invoke-Expression $body.Substring(1,$body.Length-2)
$result|ConvertTo-Json -Compress
""")
        self.assertEqual(report["Resolution"], "1920x1080")
        self.assertFalse(report["ProcessOwnedByHarness"])
        self.assertFalse(report["ManualInputAccepted"])
        self.assertFalse(report["PromotionReady"])
        self.assertEqual(report["InputMechanism"], "none_observation_only")


if __name__ == "__main__":
    unittest.main()
