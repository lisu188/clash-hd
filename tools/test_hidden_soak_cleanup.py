#!/usr/bin/env python3
"""RAM-only AST orchestration fixtures; no native adapter or harness execution."""
from __future__ import annotations
import json
import ctypes
import os
from pathlib import Path
import subprocess
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/cdb/run_hidden_soak.ps1"
POWERSHELL = Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
FIXTURE = r'''
$ErrorActionPreference = 'Stop'
$tokens = $null; $parseErrors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile('__RUNNER__', [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$names = @('New-SoakOwnedLaunch', 'Quote-CommandLineArgument', 'Invoke-SoakOwnedChecked',
    'Start-CdbOnHiddenDesktop', 'Get-SoakOwnedCdbStatus', 'Stop-LaunchedProcesses')
$commands = $names + @('Invoke-SoakOwnedNative', 'Out-Null', 'ForEach-Object', 'Where-Object', 'Start-Sleep')
foreach ($name in $names) {
    $nodes = @($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name}, $true))
    if ($nodes.Count -ne 1) { throw "Expected one isolated helper: $name" }
    foreach ($node in $nodes[0].FindAll({param($n) $n -is [Management.Automation.Language.CommandAst]}, $true)) {
        if ($node.GetCommandName() -notin $commands) { throw "Unmocked command in $name`: $($node.GetCommandName())" }
    }
    foreach ($node in $nodes[0].FindAll({param($n) $n -is [Management.Automation.Language.InvokeMemberExpressionAst]}, $true)) {
        if ($node.Member.Value -notin @('NewGuid', 'ToString', 'StartNew', 'Stop')) { throw "Unmocked method in $name" }
    }
    # A synthetic monotonic clock avoids real timeout waits, without changing
    # the original native calls, bounds, cleanup conditions or drain count.
    $definition = $nodes[0].Extent.Text.Replace('[Diagnostics.Stopwatch]::StartNew()', '(New-MockStopwatch)')
    . ([scriptblock]::Create($definition))
}
function New-MockStopwatch {
    $script:Clock = [pscustomobject]@{ ElapsedMilliseconds = 0 }
    $script:Clock | Add-Member ScriptMethod Stop { }
    return $script:Clock
}
function Start-Sleep { param([int]$Milliseconds) $script:Clock.ElapsedMilliseconds += 1000 }
function Invoke-SoakOwnedNative {
    param([hashtable]$Ownership, [string]$Operation, [hashtable]$Arguments = @{})
    $handle = if ($Operation -like 'job_*') { $Ownership.JobHandle } elseif ($Operation -like 'thread_*') {
        $Ownership.ThreadHandle
    } elseif ($Operation -like 'desktop_*') { $Ownership.DesktopHandle } else { $Ownership.ProcessHandle }
    $result = $true; $errorCode = 0; $value = $null
    switch ($Operation) {
        'desktop_create' { $Ownership.DesktopHandle = [IntPtr]11; $handle = [IntPtr]11 }
        'job_create' { $Ownership.JobHandle = [IntPtr]12; $handle = [IntPtr]12 }
        'job_configure' { }
        'job_limits' {
            $script:LimitReads++
            $value = @{ LimitFlags = 0x2000; Capacity = 144; Returned = 144 }
            if (($script:Case -eq 'bad_initial_limits' -and $script:LimitReads -eq 1) -or
                ($script:Case -eq 'bad_admitted_limits' -and $script:LimitReads -eq 2)) { $value.LimitFlags = 0x3800 }
        }
        'process_create' {
            if ($script:Case -eq 'create_exception_before_issue') { throw 'Exception before native issuance' }
            $Ownership.ProcessCreateAttempted = $true
            $raw = @{ ProcessHandle = 13L; ThreadHandle = 14L; ProcessId = 101; ThreadId = 201 }
            $handle = [IntPtr]13; $value = @{ ProcessId = 101; ThreadId = 201; CreationFlags = 0x08000004 }
            if ($script:Case -in @('create_success_all_zero', 'create_false_all_zero')) {
                $raw = @{ ProcessHandle = 0L; ThreadHandle = 0L; ProcessId = 0; ThreadId = 0 }; $handle = [IntPtr]::Zero
            }
            if ($script:Case -in @('create_false_partial_thread_pid', 'create_exception_after_issue')) {
                $raw.ProcessHandle = 0L; $handle = [IntPtr]::Zero
            }
            $Ownership.RawProcessInformation = $raw
            if ($script:Case -eq 'create_exception_after_issue') { throw 'Exception after partial native issuance' }
            $Ownership.ProcessCreateCompleted = $true
            $Ownership.ProcessCreateSucceeded = $script:Case -notin @('fail_process_create', 'create_false_all_zero', 'create_false_partial_thread_pid', 'create_failed_receipt_then_restore_exception')
            $result = $Ownership.ProcessCreateSucceeded
            if (-not $result) { $errorCode = 5 }
            if ($result) {
                $Ownership.ProcessHandle = [IntPtr]$raw.ProcessHandle; $Ownership.ThreadHandle = [IntPtr]$raw.ThreadHandle
                $Ownership.ProcessId = $raw.ProcessId; $Ownership.ThreadId = $raw.ThreadId
            }
        }
        'process_id' { $value = if ($script:Case -eq 'wrong_created_pid' -and -not $script:InCleanup) {999} else {101} }
        'process_times' {
            $value = @{ Creation = 500L; Exit = $(if ($script:InCleanup) {900L} else {0L}); Kernel = 0L; User = 0L }
            if ($script:Case -eq 'exit_generation_changed' -and $script:InCleanup) { $value.Creation = 501L }
        }
        'job_assign' { if ($script:Case -ne 'fail_job_assign') { $Ownership.JobAssigned = $true } }
        'job_member' { $value = $script:Case -ne 'not_a_member' }
        'thread_resume' {
            if (-not $Ownership.JobAssigned) { throw 'Resume before assignment' }
            $Ownership.ResumeAttempted = $true; $Ownership.Resumed = $true; $value = 1
            if ($script:Case -eq 'unexpected_resume_count') { $value = 0; $result = $false }
        }
        'process_wait' {
            if ($Arguments.Milliseconds -notin @(0, 5000)) { throw 'Changed retained wait bound' }
            $value = if ($script:InCleanup) {0} else {258}
            if ($script:Case -eq 'wait_timeout') { $value = 258 }
            if ($script:Case -eq 'wait_failed') { $value = [uint32]::MaxValue; $result = $false; $errorCode = 6 }
            if ($script:Case -eq 'poll_exited' -and -not $script:InCleanup) { $value = 0 }
            if ($script:Case -eq 'poll_failed' -and -not $script:InCleanup) { $value = [uint32]::MaxValue; $result = $false; $errorCode = 6 }
            if ($script:Case -eq 'poll_exception' -and -not $script:InCleanup) { throw 'Original native adapter poll exception' }
        }
        'process_exit' { $value = 259 } # Valid exit code after a signalled retained wait.
        'job_terminate' { }
        'process_terminate' { if ($Ownership.JobAssigned -or $Ownership.ResumeAttempted) { throw 'Unauthorized process fallback' } }
        'job_accounting' {
            $script:AccountingReads++
            $value = @{ ActiveProcesses = 0; TotalProcesses = 3; TotalTerminatedProcesses = 3; Capacity = 48; Returned = 48 }
            if ($script:Case -eq 'drain_after_children' -and $script:AccountingReads -eq 1) { $value.ActiveProcesses = 2 }
            if ($script:Case -eq 'job_never_drains') { $value.ActiveProcesses = 1 }
            if ($script:Case -eq 'short_accounting') { $value.Returned = 47 }
        }
        { $_ -in @('thread_close', 'process_close', 'job_close', 'desktop_close') } { }
        default { throw "Unmocked operation: $Operation" }
    }
    if ($script:Case -eq "fail_$Operation" -or
        ($script:Case -eq 'thread_close_then_success' -and $Operation -eq 'thread_close' -and -not $script:InCleanup)) {
        $result = $false; $errorCode = 5
    }
    if ($result -and $Operation -like '*_close') {
        $field = @{ thread_close = 'ThreadHandle'; process_close = 'ProcessHandle'; job_close = 'JobHandle'; desktop_close = 'DesktopHandle' }[$Operation]
        $Ownership[$field] = [IntPtr]::Zero
    }
    $row = [pscustomobject]@{ Operation = $Operation; Handle = $handle.ToInt64(); Result = [bool]$result; ErrorCode = $errorCode; Value = $value }
    [void]$script:Calls.Add($row)
    if ($script:Case -in @('create_receipt_then_restore_exception', 'create_failed_receipt_then_restore_exception') -and $Operation -eq 'process_create') {
        $Ownership.Receipts += $row
        throw 'Original environment restoration exception after native create return'
    }
    return $row
}
function Get-Process { throw 'PID discovery forbidden' }
function Stop-Process { throw 'PID termination forbidden' }
function Get-LaunchedCandidateProcesses { throw 'Candidate path adoption forbidden' }
$results = @()
foreach ($name in @('success', 'drain_after_children', 'fail_desktop_create', 'fail_job_create', 'fail_job_configure',
    'bad_initial_limits', 'fail_process_create', 'wrong_created_pid', 'fail_job_assign', 'not_a_member',
    'bad_admitted_limits', 'unexpected_resume_count', 'thread_close_then_success', 'fail_job_terminate',
    'wait_timeout', 'wait_failed', 'exit_generation_changed', 'job_never_drains', 'short_accounting',
    'fail_process_close', 'fail_job_close', 'fail_desktop_close', 'poll_live', 'poll_exited', 'poll_failed', 'poll_exception',
    'create_receipt_then_restore_exception', 'create_success_all_zero', 'create_false_all_zero',
    'create_false_partial_thread_pid', 'create_exception_before_issue', 'create_exception_after_issue',
    'create_failed_receipt_then_restore_exception')) {
    $script:Case = $name; $script:InCleanup = $false; $script:LimitReads = 0; $script:AccountingReads = 0
    $script:Calls = New-Object Collections.Generic.List[object]
    $owner = New-SoakOwnedLaunch; $launchError = $null
    try { Start-CdbOnHiddenDesktop 'C:\Synthetic\cdb.exe' @('-hd', 'C:\Synthetic\candidate.exe') 'C:\Synthetic' 'MockPrivateDesktop' $owner | Out-Null }
    catch { $launchError = $_.Exception.Message }
    $poll = $null; $pollError = $null
    if ($name -like 'poll_*') {
        try { $poll = Get-SoakOwnedCdbStatus -Ownership $owner } catch { $pollError = $_.Exception.Message }
    }
    $launched = @($script:Calls.ToArray()); $script:InCleanup = $true
    $cleanup = Stop-LaunchedProcesses -Ownership $owner
    $count = $script:Calls.Count; $again = Stop-LaunchedProcesses -Ownership $owner
    $results += [pscustomobject]@{ Name = $name; LaunchError = $launchError; LaunchCalls = $launched;
        Calls = @($script:Calls.ToArray()); Cleanup = $cleanup; RepeatedCalls = $script:Calls.Count - $count
        Poll = $poll; PollError = $pollError }
}
@($results) | ConvertTo-Json -Depth 16
'''


class OwnershipSourceTests(unittest.TestCase):
    def test_actual_runner_uses_owned_job_and_retained_cdb_handle(self):
        source = RUNNER.read_text(encoding="ascii")
        for text in ("$launch = New-SoakOwnedLaunch", "-DesktopName $desktopName -Ownership $launch",
                     "$cleanup = Stop-LaunchedProcesses -Ownership $launch",
                     "$cdbProcess = Get-SoakOwnedCdbStatus -Ownership $launch", "0x08000004", "LimitFlags = 0x2000"):
            self.assertIn(text, source)
        self.assertNotIn("GetProcessById($launch.ProcessId)", source)
        cleanup = source.split("function Stop-LaunchedProcesses {", 1)[1].split("function Parse-SoakLog", 1)[0]
        for forbidden in ("Stop-Process", "Get-Process", "Get-LaunchedCandidateProcesses", "OpenProcess", "CandidatePath", "CdbPid"):
            self.assertNotIn(forbidden, cleanup)

    def test_native_outputs_and_admission_are_retained_before_resume(self):
        source = RUNNER.read_text(encoding="ascii")
        launch = source.split("function Start-CdbOnHiddenDesktop {", 1)[1].split("function Get-SoakOwnedCdbStatus", 1)[0]
        for operation in ("'process_create'", "'process_id'", "'process_times'", "'job_assign'", "'job_member'"):
            self.assertLess(launch.index(operation), launch.index("'thread_resume'"))
        self.assertEqual(launch.count("'job_limits'"), 2)
        self.assertLess(launch.rindex("'job_limits'"), launch.index("'thread_resume'"))
        adapter = source.split("function Invoke-SoakOwnedNative {", 1)[1].split("function Invoke-SoakOwnedChecked", 1)[0]
        creation = adapter.split("'process_create' {", 1)[1].split("'process_id'", 1)[0]
        for assignment in ("$Ownership.ProcessHandle = $info.hProcess", "$Ownership.ThreadHandle = $info.hThread"):
            self.assertLess(creation.index(assignment), creation.index("finally"))
            self.assertGreater(creation.index(assignment), creation.index('if ($result) {'))
        self.assertLess(creation.index("$Ownership.Receipts +="), creation.index("finally"))
        self.assertIn("$false, 0x08000004", creation)
        uncertain = creation.split('catch {', 1)[1].split('# Only a confirmed successful', 1)[0]
        self.assertIn('$Ownership.RawProcessInformation =', uncertain)
        self.assertIn('OwnershipGranted = $false; ReturnConfirmed = $false', uncertain)
        self.assertNotIn('$Ownership.ProcessHandle =', uncertain)
        self.assertNotIn('$Ownership.ThreadHandle =', uncertain)

    def test_job_struct_source_has_sdk_widths_and_explicit_bool_marshalling(self):
        source = RUNNER.read_text(encoding='ascii')
        expected_sizes = {4: (48, 48, 112, 48), 8: (64, 48, 144, 48)}
        names = ('JOB_BASIC_LIMIT_INFORMATION', 'IO_COUNTERS', 'JOB_EXTENDED_LIMIT_INFORMATION', 'JOB_BASIC_ACCOUNTING_INFORMATION')
        for pointer_width, sizes in expected_sizes.items():
            types = {'Int64': ctypes.c_int64, 'UInt32': ctypes.c_uint32, 'UInt64': ctypes.c_uint64,
                     'UIntPtr': ctypes.c_uint32 if pointer_width == 4 else ctypes.c_uint64}
            for name, expected in zip(names, sizes):
                body = source.split(f'public struct {name} {{', 1)[1].split('}', 1)[0]
                fields = []
                for field_type, declarations in re.findall(r'public (\w+) ([\w, ]+);', body):
                    fields.extend((field.strip(), types[field_type]) for field in declarations.split(','))
                struct = type(name, (ctypes.Structure,), {'_pack_': 8, '_fields_': fields})
                self.assertEqual(ctypes.sizeof(struct), expected, (pointer_width, name, fields))
                types[name] = struct
        self.assertIn('[MarshalAs(UnmanagedType.Bool)] out bool member', source)
        self.assertEqual(source.count('[return: MarshalAs(UnmanagedType.Bool)]'), 9)

    def test_samples_retain_cleanup_details_and_original_hash_check_is_finally_guarded(self):
        source = RUNNER.read_text(encoding='ascii')
        for text in ('mechanism = $cleanup.Mechanism; run_id = $cleanup.RunId',
                     'job_empty = $cleanup.JobEmpty; handles_closed = $cleanup.HandlesClosed',
                     'receipts = @($cleanup.Receipts)'):
            self.assertIn(text, source)
        stop = source.index('$cleanup = Stop-LaunchedProcesses -Ownership $launch')
        verify = source.index('original executable SHA changed during the runtime', stop)
        self.assertIn('finally {', source[stop:verify])


@unittest.skipUnless(sys.platform == "win32" and POWERSHELL.exists(), "mocked RAM PowerShell fixture needs Windows")
class HiddenSoakCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        environment = os.environ.copy(); environment.pop("PSModulePath", None)
        result = subprocess.run(
            [str(POWERSHELL), "-NoProfile", "-NonInteractive", "-Command", "& ([scriptblock]::Create([Console]::In.ReadToEnd()))"],
            input=FIXTURE.replace("__RUNNER__", str(RUNNER).replace("'", "''")), capture_output=True,
            text=True, timeout=30, env=environment, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.results = {row["Name"]: row for row in json.loads(result.stdout)}

    def operations(self, name, *, launch=False):
        return [row["Operation"] for row in self.results[name]["LaunchCalls" if launch else "Calls"]]

    def test_success_and_children_are_drained_by_job_without_pid_adoption(self):
        for name in ("success", "drain_after_children"):
            row = self.results[name]
            self.assertIsNone(row["LaunchError"], row)
            self.assertTrue(row["Cleanup"]["AllTerminated"], row)
            self.assertTrue(row["Cleanup"]["JobEmpty"] and row["Cleanup"]["HandlesClosed"], row)
            self.assertEqual(row["Cleanup"]["Errors"], [])
            self.assertNotIn("process_terminate", self.operations(name))
            self.assertGreaterEqual(self.operations(name).count("job_accounting"), 2)

    def test_setup_failures_preserve_partial_owner_and_never_resume_early(self):
        for name in ("fail_desktop_create", "fail_job_create", "fail_job_configure", "bad_initial_limits",
                     "fail_process_create", "wrong_created_pid", "fail_job_assign", "not_a_member", "bad_admitted_limits"):
            row = self.results[name]
            self.assertTrue(row["LaunchError"], row)
            self.assertFalse(row["Cleanup"]["AllTerminated"], row)
            self.assertTrue(row["Cleanup"]["Errors"], row)
            self.assertNotIn("thread_resume", self.operations(name, launch=True))
            self.assertTrue(row["Cleanup"]["HandlesClosed"], row)
        for name in ("wrong_created_pid", "fail_job_assign"):
            self.assertEqual([r["Handle"] for r in self.results[name]["Calls"] if r["Operation"] == "process_terminate"], [13])
        self.assertNotIn('process_terminate', self.operations('fail_process_create'))
        self.assertNotIn('process_close', self.operations('fail_process_create'))
        self.assertNotIn('thread_close', self.operations('fail_process_create'))
        for name in ("not_a_member", "bad_admitted_limits"):
            self.assertNotIn("process_terminate", self.operations(name))

    def test_failed_or_unexpected_resume_is_never_accepted(self):
        row = self.results["unexpected_resume_count"]
        self.assertTrue(row["LaunchError"])
        self.assertFalse(row["Cleanup"]["AllTerminated"])
        self.assertNotIn("process_terminate", self.operations("unexpected_resume_count"))

    def test_wait_generation_and_accounting_errors_fail_closed(self):
        for name in ("wait_timeout", "wait_failed", "exit_generation_changed", "job_never_drains", "short_accounting"):
            row = self.results[name]
            self.assertFalse(row["Cleanup"]["AllTerminated"], row)
            self.assertTrue(row["Cleanup"]["Errors"], row)
            self.assertTrue(row["Cleanup"]["HandlesClosed"], row)
        self.assertFalse(self.results["job_never_drains"]["Cleanup"]["GameStopped"])

    def test_original_failures_survive_later_successful_drain_or_close(self):
        for name in ("thread_close_then_success", "fail_job_terminate"):
            row = self.results[name]
            self.assertTrue(row["Cleanup"]["CdbStopped"] and row["Cleanup"]["GameStopped"], row)
            self.assertTrue(row["Cleanup"]["HandlesClosed"], row)
            self.assertFalse(row["Cleanup"]["AllTerminated"], row)
            self.assertTrue(row["Cleanup"]["Errors"], row)

    def test_each_close_is_attempted_and_failed_handles_remain_debt(self):
        for name in ("fail_process_close", "fail_job_close", "fail_desktop_close"):
            row = self.results[name]
            self.assertFalse(row["Cleanup"]["AllTerminated"], row)
            self.assertFalse(row["Cleanup"]["HandlesClosed"], row)
            for operation in ("process_close", "job_close", "desktop_close"):
                self.assertIn(operation, self.operations(name))

    def test_cleanup_is_idempotent_and_keeps_all_original_receipts(self):
        for row in self.results.values():
            self.assertEqual(row["RepeatedCalls"], 0, row)
            self.assertTrue(row["Cleanup"]["Receipts"], row)
            for receipt in row["Cleanup"]["Receipts"]:
                for field in ("ErrorCode", "Result", "Handle"):
                    self.assertIn(field, receipt)

    def test_liveness_uses_original_handle_and_poll_failures_survive_cleanup(self):
        self.assertFalse(self.results['poll_live']['Poll']['HasExited'])
        self.assertIsNone(self.results['poll_live']['Poll']['ExitCode'])
        self.assertTrue(self.results['poll_exited']['Poll']['HasExited'])
        self.assertEqual(self.results['poll_exited']['Poll']['ExitCode'], 259)
        for name in ('poll_live', 'poll_exited', 'poll_failed', 'poll_exception'):
            for receipt in self.results[name]['Calls']:
                if receipt['Operation'] == 'process_wait':
                    self.assertEqual(receipt['Handle'], 13)
        for name in ('poll_failed', 'poll_exception'):
            row = self.results[name]
            self.assertTrue(row['PollError'])
            self.assertTrue(row['Cleanup']['CdbStopped'] and row['Cleanup']['GameStopped'])
            self.assertFalse(row['Cleanup']['AllTerminated'])

    def test_original_create_failure_receipt_survives_environment_restoration_failure(self):
        row = self.results['create_failed_receipt_then_restore_exception']
        self.assertIn('restoration exception', row['LaunchError'])
        self.assertFalse(row['Cleanup']['AllTerminated'])
        original = [r for r in row['Cleanup']['Receipts'] if r['Operation'] == 'process_create']
        self.assertEqual(len(original), 1)
        self.assertFalse(original[0]['Result'])
        self.assertEqual(original[0]['ErrorCode'], 5)
        for operation in ('process_terminate', 'process_wait', 'process_id', 'process_times', 'process_exit', 'process_close', 'thread_close'):
            self.assertNotIn(operation, self.operations('create_failed_receipt_then_restore_exception'))
        self.assertFalse(row['Cleanup']['CdbStopped'] or row['Cleanup']['GameStopped'])

    def test_successful_create_remains_owned_after_environment_restoration_failure(self):
        row = self.results['create_receipt_then_restore_exception']
        self.assertIn('restoration exception', row['LaunchError'])
        self.assertTrue(row['Cleanup']['CdbStopped'] and row['Cleanup']['GameStopped'])
        self.assertFalse(row['Cleanup']['AllTerminated'])
        self.assertIn('process_terminate', self.operations('create_receipt_then_restore_exception'))
        self.assertTrue(row['Cleanup']['ProcessCreateSucceeded'])

    def test_missing_handle_is_unknown_after_success_partial_outputs_or_interrupted_issuance(self):
        for name in ('create_success_all_zero', 'create_false_partial_thread_pid', 'create_exception_after_issue'):
            row = self.results[name]
            self.assertTrue(row['LaunchError'])
            self.assertFalse(row['Cleanup']['CdbStopped'], row)
            self.assertFalse(row['Cleanup']['GameStopped'], row)
            self.assertFalse(row['Cleanup']['AllTerminated'], row)
            self.assertNotIn('process_terminate', self.operations(name))
            self.assertTrue(any('unknown/partial' in error for error in row['Cleanup']['Errors']))
        success = self.results['create_success_all_zero']['Cleanup']
        self.assertTrue(success['ProcessCreateAttempted'] and success['ProcessCreateCompleted'] and success['ProcessCreateSucceeded'])
        interrupted = self.results['create_exception_after_issue']['Cleanup']
        self.assertTrue(interrupted['ProcessCreateAttempted'])
        self.assertFalse(interrupted['ProcessCreateCompleted'])
        self.assertIsNone(interrupted['ProcessCreateSucceeded'])

    def test_true_no_issue_is_distinct_from_missing_ownership(self):
        for name in ('create_false_all_zero', 'create_exception_before_issue'):
            row = self.results[name]
            self.assertTrue(row['LaunchError'])
            self.assertTrue(row['Cleanup']['CdbStopped'] and row['Cleanup']['GameStopped'], row)
            self.assertFalse(row['Cleanup']['AllTerminated'])
            self.assertNotIn('process_terminate', self.operations(name))


def run_tests() -> None:
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if not result.wasSuccessful() or result.skipped:
        raise AssertionError("Owned cleanup fixtures failed or were unavailable")


if __name__ == "__main__":
    unittest.main()
