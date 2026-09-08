#!/usr/bin/env python3
"""Run only AST-extracted cleanup helpers against fully mocked processes.

The runtime harness is parsed as text, never dot-sourced or executed. The only
child process is a hidden PowerShell interpreter for this synthetic fixture.
No game/debugger is launched, enumerated, stopped, or waited upon.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/cdb/run_hidden_soak.ps1"
POWERSHELL = Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")

FIXTURE = r'''
param([string]$Runner, [switch]$ReintroducePidSort)
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Runner, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$allowedCommands = @('Get-FullPath', 'Get-Process', 'Get-LaunchedCandidateProcesses', 'Where-Object', 'Sort-Object', 'New-Object', 'Stop-Process')
$allowedMethods = @('GetFullPath', 'AddSeconds', 'Add', 'WaitForExit')
foreach ($name in @('Get-FullPath', 'Get-LaunchedCandidateProcesses', 'Stop-LaunchedProcesses')) {
    $functions = @($ast.FindAll({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name }, $true))
    if ($functions.Count -ne 1) { throw "Expected one isolated helper: $name" }
    foreach ($command in $functions[0].FindAll({ param($node) $node -is [System.Management.Automation.Language.CommandAst] }, $true)) {
        if ($command.GetCommandName() -notin $allowedCommands) { throw 'Cleanup helper contains an unmocked command' }
    }
    foreach ($method in $functions[0].FindAll({ param($node) $node -is [System.Management.Automation.Language.InvokeMemberExpressionAst] }, $true)) {
        if ($method.Member.Value -notin $allowedMethods) { throw 'Cleanup helper contains an unmocked method' }
    }
    # Execute only these three whitelisted function definitions. The harness
    # top-level preflight, Add-Type, launch body, and finally block never run.
    $definition = $functions[0].Extent.Text
    if ($name -eq 'Stop-LaunchedProcesses' -and $ReintroducePidSort) {
        # Fault injection stays inside this temporary, mocked function. It
        # proves the fixture fails for the real prior ordering defect.
        $needle='foreach ($process in $toStop)'
        if (-not $definition.Contains($needle)) { throw 'Ordering fault injection target missing' }
        $definition=$definition.Replace($needle, 'foreach ($process in ($toStop | Sort-Object Id -Unique))')
    }
    Invoke-Expression $definition
}

function New-MockProcess {
    param([int]$ProcId, [string]$Path, [datetime]$Created, [string]$Role)
    $object = [pscustomobject]@{
        Id=$ProcId; Path=$Path; StartTime=$Created; Role=$Role; Present=$true
        Exited=$false; Stuck=$false; RaceGone=$false; StopThrows=$false; ExitOnCheck=$false
    }
    $object | Add-Member -MemberType ScriptProperty -Name HasExited -Value {
        if ($this.ExitOnCheck) { $this.Exited=$true; $this.Present=$false }
        return $this.Exited
    }
    $object | Add-Member -MemberType ScriptMethod -Name WaitForExit -Value {
        param([int]$Milliseconds)
        [void]$script:Calls.Add([pscustomobject]@{op='wait'; id=$this.Id; milliseconds=$Milliseconds})
        if ($Milliseconds -ne 5000) { throw 'Fixture rejects altered cleanup grace' }
        if ($this.Stuck) { return $false }
        # A debuggee cannot finish while its debugger still owns the session.
        # Sorting the real1336/34356 IDs recreates the old five-second failure.
        if ($this.Role -eq 'game' -and $script:ProcessTable[$script:DebuggerId].Present) { return $false }
        $this.Exited=$true
        $this.Present=$false
        return $true
    }
    return $object
}

function Get-Process {
    [CmdletBinding()]
    param([int]$Id)
    if ($PSBoundParameters.ContainsKey('Id')) {
        if ($script:ProcessTable.ContainsKey($Id) -and $script:ProcessTable[$Id].Present) {
            return $script:ProcessTable[$Id]
        }
        return
    }
    $script:Enumerations++
    if ($script:PresenceRace -and $script:Enumerations -eq 2) {
        $script:ProcessTable[50001].Present=$true
    }
    foreach ($procId in $script:ProcessOrder) {
        if ($script:ProcessTable[$procId].Present) { $script:ProcessTable[$procId] }
    }
}

function Stop-Process {
    [CmdletBinding()]
    param([int]$Id, [switch]$Force)
    [void]$script:Calls.Add([pscustomobject]@{op='stop'; id=$Id; force=[bool]$Force})
    if ($Id -notin $script:OwnedIds) { throw "Attempt to stop unrelated mock process $Id" }
    $process = $script:ProcessTable[$Id]
    if ($process.RaceGone) {
        $process.Present=$false
        $process.Exited=$true
        throw "mock process $Id disappeared during Stop-Process"
    }
    if ($process.StopThrows) { throw "mock stop denied for $Id" }
    if ($process.Role -eq 'debugger' -and -not $process.Stuck) {
        $process.Exited=$true
        $process.Present=$false
    }
}

if ((Get-Command Get-Process).CommandType -ne 'Function' -or (Get-Command Stop-Process).CommandType -ne 'Function') {
    throw 'Process cmdlets are not mocked'
}
$results = New-Object System.Collections.Generic.List[object]
$cases = @(
    @{Name='reversed_pid'; DebuggerId=34356; GameId=1336},
    @{Name='ascending_pid'; DebuggerId=1336; GameId=34356},
    @{Name='duplicates'; DebuggerId=34356; GameId=1336},
    @{Name='owned_children'; DebuggerId=34356; GameId=1336},
    @{Name='already_gone'; DebuggerId=34356; GameId=1336},
    @{Name='debugger_already_gone'; DebuggerId=34356; GameId=1336},
    @{Name='exit_after_enumeration'; DebuggerId=34356; GameId=1336},
    @{Name='race_gone'; DebuggerId=34356; GameId=1336},
    @{Name='stuck_child'; DebuggerId=34356; GameId=1336},
    @{Name='stuck_debugger'; DebuggerId=34356; GameId=1336},
    @{Name='stop_denied'; DebuggerId=34356; GameId=1336},
    @{Name='presence_race'; DebuggerId=34356; GameId=1336},
    @{Name='no_debugger_pid'; DebuggerId=34356; GameId=1336}
)
foreach ($case in $cases) {
    $script:DebuggerId=[int]$case.DebuggerId
    $gameId=[int]$case.GameId
    $runStart=[datetime]'2026-09-05T10:00:00Z'
    $candidate='C:\SyntheticClashCleanup\candidate.exe'
    $script:Calls=New-Object System.Collections.Generic.List[object]
    $script:ProcessTable=@{}
    $script:Enumerations=0
    $script:PresenceRace=$case.Name -eq 'presence_race'
    $script:OwnedIds=@($script:DebuggerId, $gameId, 50000, 50001)
    $script:ProcessTable[$script:DebuggerId]=New-MockProcess $script:DebuggerId 'C:\SyntheticClashCleanup\debugger.exe' $runStart 'debugger'
    $script:ProcessTable[$gameId]=New-MockProcess $gameId $candidate $runStart 'game'
    $script:ProcessTable[50000]=New-MockProcess 50000 $candidate ($runStart.AddSeconds(-5)) 'game'
    $script:ProcessTable[50000].Present=$case.Name -eq 'owned_children'
    $script:ProcessTable[50001]=New-MockProcess 50001 $candidate $runStart 'game'
    $script:ProcessTable[50001].Present=$false
    $script:ProcessTable[60000]=New-MockProcess 60000 'C:\SyntheticClashCleanup\unrelated.exe' $runStart 'unrelated'
    $script:ProcessTable[60001]=New-MockProcess 60001 $candidate ($runStart.AddSeconds(-6)) 'unrelated'
    $script:ProcessTable[60002]=New-MockProcess 60002 ($candidate + '.other') $runStart 'unrelated'
    $script:ProcessOrder=@($gameId,50000,60000,60001,60002,$script:DebuggerId,50001)
    if ($case.Name -eq 'duplicates') {
        $script:ProcessOrder=@($gameId,$gameId,$script:DebuggerId,60000,60001,60002)
        # Also return the debugger from the candidate query. Its first owned
        # occurrence must win even when it appears again among child results.
        $script:ProcessTable[$script:DebuggerId].Path=$candidate
    }
    if ($case.Name -in @('already_gone','debugger_already_gone','no_debugger_pid')) {
        $script:ProcessTable[$script:DebuggerId].Present=$false
    }
    if ($case.Name -eq 'already_gone') { $script:ProcessTable[$gameId].Present=$false }
    if ($case.Name -eq 'exit_after_enumeration') { $script:ProcessTable[$gameId].ExitOnCheck=$true }
    if ($case.Name -eq 'race_gone') { $script:ProcessTable[$gameId].RaceGone=$true }
    if ($case.Name -eq 'stuck_child') { $script:ProcessTable[$gameId].Stuck=$true }
    if ($case.Name -eq 'stuck_debugger') { $script:ProcessTable[$script:DebuggerId].Stuck=$true }
    if ($case.Name -eq 'stop_denied') { $script:ProcessTable[$gameId].StopThrows=$true }
    $cleanup = Stop-LaunchedProcesses -CdbPid $(if ($case.Name -eq 'no_debugger_pid') {$null} else {$script:DebuggerId}) -CandidatePath $candidate -RunStart $runStart
    [void]$results.Add([pscustomobject]@{
        Name=$case.Name; DebuggerId=$script:DebuggerId; GameId=$gameId; Cleanup=$cleanup; Calls=@($script:Calls.ToArray())
        UnrelatedRemaining=@(60000,60001,60002 | Where-Object {$script:ProcessTable[$_].Present})
    })
}
@($results.ToArray()) | ConvertTo-Json -Depth 10
'''


@unittest.skipUnless(sys.platform == "win32" and POWERSHELL.exists(), "mocked PowerShell fixture needs Windows")
class HiddenSoakCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory(prefix="clash-hidden-cleanup-fixture-") as folder:
            helper = Path(folder) / "mock-cleanup-only.ps1"
            helper.write_text(FIXTURE, encoding="ascii")
            environment = os.environ.copy()
            environment.pop("PSModulePath", None)
            # Policy is process-local for this temporary synthetic fixture;
            # no machine/user policy changes and no harness execution.
            variants = []
            for extra in ([], ["-ReintroducePidSort"]):
                result = subprocess.run(
                    [str(POWERSHELL), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                     "-File", str(helper), "-Runner", str(RUNNER), *extra],
                    capture_output=True, text=True, timeout=30, env=environment,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if result.returncode:
                    raise AssertionError(result.stdout + result.stderr)
                variants.append({case["Name"]: case for case in json.loads(result.stdout)})
        cls.results, cls.sorted_regression = variants

    def stops(self, name):
        return [row["id"] for row in self.results[name]["Calls"] if row["op"] == "stop"]

    def test_debugger_first_for_both_pid_orders_and_owned_children(self):
        for name in ("reversed_pid", "ascending_pid", "owned_children"):
            row = self.results[name]
            self.assertTrue(row["Cleanup"]["AllTerminated"], row)
            self.assertEqual(self.stops(name), [row["DebuggerId"], row["GameId"]] + ([50000] if name == "owned_children" else []))
            self.assertEqual(row["Cleanup"]["StoppedProcessIds"], self.stops(name))

    def test_deduplication_preserves_first_occurrence(self):
        row = self.results["duplicates"]
        self.assertTrue(row["Cleanup"]["AllTerminated"], row)
        self.assertEqual(self.stops("duplicates"), [34356, 1336])

    def test_oracle_reproduces_failure_when_old_pid_sort_is_restored(self):
        reversed_ids = self.sorted_regression["reversed_pid"]
        self.assertFalse(reversed_ids["Cleanup"]["AllTerminated"])
        self.assertTrue(any("process 1336 did not exit within 5 seconds" in error
                            for error in reversed_ids["Cleanup"]["Errors"]))
        self.assertEqual([call["id"] for call in reversed_ids["Calls"] if call["op"] == "stop"], [1336, 34356])
        self.assertTrue(self.sorted_regression["ascending_pid"]["Cleanup"]["AllTerminated"])

    def test_absent_and_already_exited_processes_are_honest_success(self):
        for name, expected in (("already_gone", []), ("debugger_already_gone", [1336]),
                               ("exit_after_enumeration", [34356]), ("no_debugger_pid", [1336])):
            row = self.results[name]
            self.assertTrue(row["Cleanup"]["AllTerminated"], row)
            self.assertEqual(row["Cleanup"]["Errors"], [])
            self.assertEqual(self.stops(name), expected)

    def test_true_timeouts_and_stop_errors_are_not_masked(self):
        for name in ("race_gone", "stuck_child", "stuck_debugger", "stop_denied", "presence_race"):
            row = self.results[name]
            self.assertFalse(row["Cleanup"]["AllTerminated"], row)
            self.assertTrue(row["Cleanup"]["Errors"], row)
        race = self.results["race_gone"]["Cleanup"]
        self.assertTrue(race["CdbStopped"] and race["GameStopped"])
        self.assertEqual(len(race["Errors"]), 1)
        for name in ("stuck_child", "stuck_debugger"):
            self.assertTrue(any("did not exit within 5 seconds" in error for error in self.results[name]["Cleanup"]["Errors"]))
        self.assertFalse(self.results["stuck_debugger"]["Cleanup"]["CdbStopped"])
        self.assertFalse(self.results["presence_race"]["Cleanup"]["GameStopped"])

    def test_timeouts_force_flag_and_identity_boundaries_remain_exact(self):
        for row in self.results.values():
            self.assertEqual(row["UnrelatedRemaining"], [60000, 60001, 60002])
            for call in row["Calls"]:
                self.assertNotIn(call["id"], (60000, 60001, 60002))
                if call["op"] == "wait":
                    self.assertEqual(call["milliseconds"], 5000)
                else:
                    self.assertTrue(call["force"])


if __name__ == "__main__":
    unittest.main()
