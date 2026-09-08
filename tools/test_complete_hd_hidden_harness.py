"""Offline complete candidate consumer and non-executing harness fixtures."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import complete_hd_runtime_context as context
import initial_map_paint_trace as trace
import framed_minimap_probe as minimap
from test_initial_map_paint_trace import fixture, initial_events, SHA
from test_framed_minimap_integration import synthetic_main

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts/cdb/run_cdb_surface_dump.ps1"
ORIGINAL = Path("C:/Clash/clash95.exe")
ARMY_STAGE = trace.FRAMED_STAGE.removesuffix("-validation") + "-modalcanvas-army-validation"


class ContextTests(unittest.TestCase):
    def packet(self):
        log, probe = fixture(initial_events(framed=True), stage=ARMY_STAGE)
        army = f"ARMY_CONTRACT_PASS stage={ARMY_STAGE} resolution=800x600 candidate_sha256={SHA} revision=fixture"
        complete = f"COMPLETEHD_CONTRACT_PASS stage={context.complete.STAGE} resolution=800x600 candidate_sha256={SHA} revision=complete_hd_v1"
        log = army + "\n" + complete + "\n" + log
        probe = ".echo " + army + "\n.echo " + complete + "\n" + probe
        manifest = dict(stage=context.complete.STAGE, resolution="800x600", candidate_sha256=SHA,
                        recipe_revision="complete_hd_v1", predecessor=dict(stage=ARMY_STAGE, army_revision="fixture",
                            base_candidate=dict(base_candidate=dict(stage=trace.FRAMED_STAGE))))
        return log, probe, manifest

    def test_complete_keeps_framed_stack_and_original_trace_identity(self):
        log, probe, manifest = self.packet()
        with patch.object(context.complete, "build_candidate", return_value=(b"image", manifest, probe)):
            report = trace.evaluate_trace(log, probe, resolution="800x600", candidate_sha256=SHA,
                stage=context.complete.STAGE, candidate_manifest=manifest, original=b"synthetic original")
        self.assertTrue(report["passed"], report["failures"])
        self.assertEqual(report["stage"], context.complete.STAGE)
        self.assertEqual(report["trace_contract"]["full_tiles"], [11, 8])
        self.assertEqual(report["trace_contract"]["full_status_to_ready_stack_bytes"], 148)
        self.assertFalse(report["manual_input_proof"])

    def test_complete_rejects_duplicate_mixed_missing_and_failed_contracts(self):
        log, probe, manifest = self.packet()
        complete_line = next(line for line in log.splitlines() if line.startswith("COMPLETEHD_CONTRACT_PASS"))
        bad_logs = (log + complete_line + "\n", log.replace(complete_line, ""),
                    log.replace(complete_line, complete_line.replace(SHA, "b" * 64)),
                    log + "ARMY_CONTRACT_FAIL hook_bytes\n", log.replace("ARMY_CONTRACT_PASS", "ARMY_MISSING"))
        with patch.object(context.complete, "build_candidate", return_value=(b"image", manifest, probe)):
            for value in bad_logs:
                report = trace.evaluate_trace(value, probe, resolution="800x600", candidate_sha256=SHA,
                    stage=context.complete.STAGE, candidate_manifest=manifest, original=b"synthetic original")
                self.assertFalse(report["passed"], value)
            report = trace.evaluate_trace(log, probe, resolution="800x600", candidate_sha256=SHA, stage=context.complete.STAGE)
            self.assertFalse(report["passed"])

    def test_context_rejects_changed_manifest_candidate_probe_and_resolution(self):
        _, probe, manifest = self.packet()
        builder = lambda original, resolution: (b"image", manifest, probe)
        for kwargs in (dict(candidate=b"bad"), dict(probe=probe+"\n"), dict(resolution="1024x768")):
            options = dict(resolution="800x600", builder=builder) | kwargs
            with self.assertRaises(ValueError):
                context.verify_context(manifest, b"original", **options)
        changed = copy.deepcopy(manifest); changed["predecessor"]["army_revision"] = "wrong"
        with self.assertRaises(ValueError):
            context.verify_context(changed, b"original", resolution="800x600", builder=builder)

    @unittest.skipUnless(sys.platform == "win32", "non-executing PowerShell AST needs Windows")
    def test_parse_failure_summary_preserves_failure_and_all_original_artifacts(self):
        source = r'''
$ErrorActionPreference = 'Stop'
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($args[0], [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
$definitions = @($ast.FindAll({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Write-SurfacePostprocessingFailure'}, $true))
if ($definitions.Count -ne 1) { throw 'Missing unique failure writer' }
. ([scriptblock]::Create($definitions[0].Extent.Text))
$tries = @($ast.FindAll({param($node) $node -is [System.Management.Automation.Language.TryStatementAst] -and $node.Body.Extent.Text.Contains('$coverageOutput = & $pythonExe')}, $true))
if ($tries.Count -ne 1 -or -not $tries[0].Body.Extent.Text.Contains('$summaryObject | ConvertTo-Json') -or -not $tries[0].CatchClauses[0].Body.Extent.Text.Contains('throw $postprocessingError')) { throw 'Postprocessing failure no longer encloses coverage and final summary or preserves throwing' }
$path = Join-Path $args[1] 'summary.json'
$markdown = Join-Path $args[1] 'RUN-SUMMARY.md'
$raw = Join-Path $args[1] 'surface.raw'
[System.IO.File]::WriteAllText($raw, 'fixture-only raw bytes')
$before = [System.IO.File]::ReadAllBytes($raw)
$context = @{Stage='fixture-complete'; Resolution='1920x1080'; CandidateSha256=('a'*64); CoverageExitCode=2; CoverageJson='original-failing-coverage.json'; InitialMapPaintTrace=@{passed=$true}; RawPath=$raw}
Write-SurfacePostprocessingFailure -SummaryPath $path -MarkdownPath $markdown -Context $context -FailureMessage 'map_tile_coverage.py failed with exit code 2' -FailureId 'original-id' -FailureStack 'original-stack'
$saved = [System.IO.File]::ReadAllBytes($path)
$record = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
if ($record.Passed -ne $false -or $record.CoverageExitCode -ne 2 -or $record.Error -ne 'map_tile_coverage.py failed with exit code 2' -or $record.ExceptionId -ne 'original-id' -or $record.FailurePhase -ne 'postprocessing' -or $record.PromotionReady -ne $false) { throw 'Failure summary changed failure meaning' }
Write-SurfacePostprocessingFailure -SummaryPath $path -MarkdownPath $markdown -Context @{} -FailureMessage 'replacement'
if ([Convert]::ToBase64String($saved) -ne [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($path))) { throw 'Original summary overwritten' }
if ([Convert]::ToBase64String($before) -ne [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($raw))) { throw 'Original raw changed' }
$exports = @($ast.FindAll({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Export-CompleteRuntimeProbe'}, $true))
if ($exports.Count -ne 1) { throw 'Missing unique runtime probe exporter' }
. ([scriptblock]::Create($exports[0].Extent.Text))
$inputProbe = Join-Path $args[1] 'source.cdb'
$outputProbe = Join-Path $args[1] 'runtime.cdb'
$commands = '.echo unchanged @$t0' + "`n" + 'g' + "`r`n"
[System.IO.File]::WriteAllText($inputProbe, $commands, [System.Text.Encoding]::ASCII)
Export-CompleteRuntimeProbe -SourcePath $inputProbe -OutputPath $outputProbe
if ([System.IO.File]::ReadAllText($outputProbe) -cne $commands.Replace("`r`n", "`n").Replace("`n", "`r`n")) { throw 'Runtime CRLF export changed commands' }
if ([System.IO.File]::ReadAllText($inputProbe) -cne $commands) { throw 'Canonical probe changed' }
$rejected = $false
try { Export-CompleteRuntimeProbe -SourcePath $inputProbe -OutputPath $outputProbe } catch { $rejected = $true }
if (-not $rejected) { throw 'Existing runtime probe overwritten' }
$rejected = $false
try { Export-CompleteRuntimeProbe -SourcePath $inputProbe -OutputPath $inputProbe } catch { $rejected = $true }
if (-not $rejected) { throw 'Canonical probe overwrite allowed' }
[System.IO.File]::WriteAllBytes($inputProbe, [byte[]]@(103, 0, 10))
$rejected = $false
try { Export-CompleteRuntimeProbe -SourcePath $inputProbe -OutputPath ($outputProbe + '.invalid') } catch { $rejected = $true }
if (-not $rejected) { throw 'Embedded NUL accepted' }
$runtimeTries = @($ast.FindAll({param($node) $node -is [System.Management.Automation.Language.TryStatementAst] -and $node.Body.Extent.Text.Contains('$launch = Start-CdbOnHiddenDesktop')}, $true))
if ($runtimeTries.Count -ne 1 -or $runtimeTries[0].CatchClauses.Count -ne 1) { throw 'Host exceptions can bypass final summary' }
foreach ($field in @('$runtimeError = $_.Exception.Message', '$runtimeExceptionId = $_.FullyQualifiedErrorId', '$runtimeExceptionStack = $_.ScriptStackTrace')) {
    if (-not $runtimeTries[0].CatchClauses[0].Body.Extent.Text.Contains($field)) { throw 'Runtime exception detail lost' }
}
if (-not $runtimeTries[0].Finally.Extent.Text.Contains('$cleanupResult = Test-LaunchedProcessesStopped')) { throw 'Cleanup is not verified on every runtime exit' }
$cleanupDefinitions = @($ast.FindAll({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Test-LaunchedProcessesStopped'}, $true))
if ($cleanupDefinitions.Count -ne 1) { throw 'Missing unique cleanup verifier' }
. ([scriptblock]::Create($cleanupDefinitions[0].Extent.Text))
# Synthetic process inventory only. These mocks prevent actual process access.
function Get-FullPath { param([string]$Path) $Path }
function Get-Process {
    param($Name, $Id, $ErrorAction)
    if ($Name) { $script:fixtureCandidates } else { $script:fixtureCdb }
}
$runStart = Get-Date
$script:fixtureCandidates = @()
$script:fixtureCdb = $null
$result = Test-LaunchedProcessesStopped -CdbPid 42 -CandidatePath 'C:\ClashTests\fixture.exe' -CdbPath 'C:\fixture\cdb.exe' -RunStart $runStart -WaitMilliseconds 0
if (-not $result.Passed) { throw 'Absent owned processes rejected' }
$script:fixtureCandidates = @([pscustomobject]@{Id=43; Path='C:\ClashTests\fixture.exe'; StartTime=$runStart})
$result = Test-LaunchedProcessesStopped -CdbPid 42 -CandidatePath 'C:\ClashTests\fixture.exe' -CdbPath 'C:\fixture\cdb.exe' -RunStart $runStart -WaitMilliseconds 0
if ($result.Passed -or $result.RemainingProcessIds -notcontains 43) { throw 'Surviving candidate accepted' }
$script:fixtureCandidates = @()
$script:fixtureCdb = [pscustomobject]@{Id=42; Path='C:\fixture\cdb.exe'; StartTime=$runStart}
$result = Test-LaunchedProcessesStopped -CdbPid 42 -CandidatePath 'C:\ClashTests\fixture.exe' -CdbPath 'C:\fixture\cdb.exe' -RunStart $runStart -WaitMilliseconds 0
if ($result.Passed -or $result.RemainingProcessIds -notcontains 42) { throw 'Surviving debugger accepted' }
$script:fixtureCdb.Path = 'C:\unrelated\cdb.exe'
$result = Test-LaunchedProcessesStopped -CdbPid 42 -CandidatePath 'C:\ClashTests\fixture.exe' -CdbPath 'C:\fixture\cdb.exe' -RunStart $runStart -WaitMilliseconds 0
if (-not $result.Passed) { throw 'Unrelated reused process id treated as owned' }
$script:fixtureCdb.Path = $null
$result = Test-LaunchedProcessesStopped -CdbPid 42 -CandidatePath 'C:\ClashTests\fixture.exe' -CdbPath 'C:\fixture\cdb.exe' -RunStart $runStart -WaitMilliseconds 0
if ($result.Passed -or -not $result.InspectionErrors.Count) { throw 'Unavailable identity treated as verified cleanup' }
'''
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "fixture.ps1"
            script.write_text(source, encoding="utf-8")
            result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-File", str(script), str(HARNESS), directory], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_coverage_complete_identity_requires_reconstructed_bundle(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/map_tile_coverage.py"), "absent.png", "--stage", context.complete.STAGE], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--candidate-manifest and --original", result.stderr)


@unittest.skipUnless(ORIGINAL.is_file(), "user-owned original needed; no game/debugger execution")
class BuildIntegrationTests(unittest.TestCase):
    def test_complete_minimap_observer_preserves_all_loaded_checks_at_1080p(self):
        original = ORIGINAL.read_bytes()
        image, manifest, probe = context.complete.build_candidate(original, "1920x1080")
        packet = minimap.build_observed_probe(original, image, resolution="1920x1080",
            rendered_probe=synthetic_main(probe), candidate_manifest=manifest)
        self.assertEqual(packet["stage"], context.complete.STAGE)
        self.assertEqual(packet["candidate_sha256"], context.complete.sha256(image))
        self.assertEqual(packet["probe"].count(probe.strip()), 1)
        self.assertEqual([entry["breakpoint"] for entry in packet["observer_bindings"]], [80, 81])
        self.assertFalse(packet["acceptance"])
        self.assertEqual(original, ORIGINAL.read_bytes())


if __name__ == "__main__":
    unittest.main()
