#!/usr/bin/env python3
"""Offline host contracts; no game/debugger/native APIs or real candidate files.

PowerShell parses the script, extracts named functions, and replaces every
runtime boundary. Full orchestration uses temporary synthetic .bin inputs and
the actual offline PNG converter. The production entry point is never sourced.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "scripts/cdb/run_framed_screen_capture.ps1"
PS = Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")

PRELUDE = r'''
param([string]$HostPath,[string]$FixtureRoot,[string]$Python,[string]$Converter,[string]$Mode)
$ErrorActionPreference='Stop'
$tokens=$null; $parseErrors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($HostPath,[ref]$tokens,[ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
function Import-Function {
    param([string]$Name)
    $nodes=@($ast.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $Name},$true))
    if ($nodes.Count -ne 1) { throw "Missing unique function $Name" }
    # Only named function declarations are sourced, never the host script.
    . ([scriptblock]::Create($nodes[0].Extent.Text.Replace(('function '+$Name+' {'),('function global:'+$Name+' {'))))
}
function Assert-Case { param([bool]$Condition,[string]$Message); if (-not $Condition) { throw $Message } }
function Expect-Failure {
    param([scriptblock]$Action,[string]$Name)
    $failed=$false
    try { & $Action | Out-Null } catch { $failed=$true }
    Assert-Case $failed ("Missing rejection: "+$Name)
}
'''

PURE = r'''
foreach ($name in @('Test-FramedModalReady','Assert-FramedSurface','Select-FramedChildren','Get-FramedCandidateName')) { Import-Function $name }
$first=Get-FramedCandidateName 'C:\ClashTests\new' 'hospital' '800x600'
$again=Get-FramedCandidateName 'c:\clashtests\new' 'hospital' '800x600'
$other=Get-FramedCandidateName 'C:\ClashTests\other' 'hospital' '800x600'
Assert-Case ($first -ceq $again -and $first -cne $other -and $first -match '^framed-screen-hospital-800x600-[a-f0-9]{16}\.exe$') 'Candidate plan naming is not deterministic and isolated'
$results=@()
foreach ($text in @('',"SURFDUMP_READY x=1`nSURFDUMP_HOST_READY`n",'MODAL_SURFDUMP_HOST_READY'," modal_SURFDUMP_HOST_READY`n", "xMODAL_SURFDUMP_HOST_READY`n", "MODAL_SURFDUMP_HOST_READY extra`n")) {
    Assert-Case (-not (Test-FramedModalReady $text)) 'Unrelated/incomplete readiness accepted'
    $results+='readiness_reject'
}
foreach ($text in @("MODAL_SURFDUMP_HOST_READY`n", "SURFDUMP_READY old`nMODAL_SURFDUMP_HOST_READY`r`n")) {
    Assert-Case (Test-FramedModalReady $text) 'Exact complete modal readiness rejected'
    $results+='readiness_accept'
}
$plan=@{width=800;height=600;route='hospital'}
$valid=@{passed=$true;ready_for_host_capture=$true;surface=@{surface=0x120000;width=800;height=600;base=0x4000000;bytes=480000;tid=10;eip=0x43de53;esp=0xe0000;route='hospital'}}
$s=Assert-FramedSurface $valid $plan
Assert-Case ($s.bytes -eq 480000) 'Valid native surface rejected'
foreach ($case in @(@('width',801),@('height',599),@('bytes',480001),@('base',4294967290),@('base',0),@('surface',0x51d4c0),@('surface',0),@('surface',4294967290),@('tid',0),@('eip',0),@('esp',0),@('route','smith'),@('width','800'),@('bytes',480000.0))) {
    $copy=($valid | ConvertTo-Json -Depth 8 | ConvertFrom-Json)
    $copy.surface.($case[0])=$case[1]
    Expect-Failure { Assert-FramedSurface $copy $plan } ('surface_'+$case[0])
    $results+='surface_reject'
}
foreach ($value in @($false,'true',1)) {
    $copy=($valid | ConvertTo-Json -Depth 8 | ConvertFrom-Json); $copy.passed=$value
    Expect-Failure { Assert-FramedSurface $copy $plan } 'nonaffirmative trace'
}
$start=[datetime]'2026-09-06T01:00:00Z'
$rows=@([pscustomobject]@{ParentProcessId=100;ProcessId=200;ExecutablePath='C:\ClashTests\new\candidate.bin';CreationDate=$start.AddSeconds(1)},
    [pscustomobject]@{ParentProcessId=101;ProcessId=201;ExecutablePath='C:\ClashTests\new\candidate.bin';CreationDate=$start.AddSeconds(1)},
    [pscustomobject]@{ParentProcessId=100;ProcessId=202;ExecutablePath='C:\ClashTests\other\candidate.bin';CreationDate=$start.AddSeconds(1)})
$selected=@(Select-FramedChildren $rows 100 'C:\ClashTests\new\candidate.bin' $start)
Assert-Case ($selected.Count -eq 1 -and $selected[0].ProcessId -eq 200) 'Parent/path ownership filter failed'
$rows[0].CreationDate=$start.AddSeconds(-1)
Expect-Failure { Select-FramedChildren $rows 100 'C:\ClashTests\new\candidate.bin' $start } 'stale child creation'
@{passed=$true;cases=$results.Count+5} | ConvertTo-Json
'''

PATHS = r'''
Import-Function 'Resolve-FramedPath'
$script:Existing=@{'C:\'= 'directory'; 'C:\ClashTests'='directory'; 'C:\ClashCaptures'='directory';
    'C:\ClashTests\work'='directory'; 'C:\ClashTests\old.bin'='file'; 'C:\ClashTests\junction'='reparse'}
function Test-Path {
    param([string]$LiteralPath,[string]$PathType)
    if (-not $script:Existing.ContainsKey($LiteralPath)) { return $false }
    if ($PathType -eq 'Leaf') { return $script:Existing[$LiteralPath] -eq 'file' }
    if ($PathType -eq 'Container') { return $script:Existing[$LiteralPath] -ne 'file' }
    return $true
}
function Get-Item {
    param([string]$LiteralPath,[switch]$Force)
    return [pscustomobject]@{PSIsContainer=($script:Existing[$LiteralPath] -ne 'file');Attributes=$(if ($script:Existing[$LiteralPath] -eq 'reparse') {[IO.FileAttributes]::ReparsePoint} else {[IO.FileAttributes]::Normal})}
}
Assert-Case ((Resolve-FramedPath 'C:\ClashTests\new' 'C:\ClashTests' new) -eq 'C:\ClashTests\new') 'new path rejected'
Assert-Case ((Resolve-FramedPath 'C:\ClashTests\work' 'C:\ClashTests' directory) -eq 'C:\ClashTests\work') 'workdir rejected'
$cases=@('C:\Clash\new','C:\ClashTests-evil\new','C:\ClashTests\..\Clash\new','C:\ClashTests',
    'C:\ClashTests\work','C:\ClashTests\old.bin','C:\ClashTests\old.bin\new','C:\ClashTests\junction\new',
    'C:ClashTests\new','relative','\\host\ClashTests\new','C:\ClashTests\new:stream','C:\ClashTests\new"x','C:\ClashTests\new;x')
foreach ($path in $cases) { Expect-Failure { Resolve-FramedPath $path 'C:\ClashTests' new } $path }
Expect-Failure { Resolve-FramedPath 'C:\ClashTests\absent' 'C:\ClashTests' directory } 'missing workdir'
Expect-Failure { Resolve-FramedPath 'C:\ClashTests\work' 'C:\ClashTests' file } 'wrong kind'
@{passed=$true;cases=$cases.Count+4} | ConvertTo-Json
'''

ORCHESTRATION = r'''
foreach ($name in @('Get-FramedHash','Write-FramedJson','Invoke-FramedCapture','Assert-FramedSurface','Test-FramedModalReady','Read-FramedLog')) { Import-Function $name }
$script:Calls=New-Object 'Collections.Generic.List[string]'
$script:FindCount=0
$script:GameId=200
function Initialize-FramedNative { throw 'Native initialization is forbidden in offline fixtures' }
function Resolve-FramedPath { param($Path,$Root,$Kind); return $Path }
function Invoke-FramedPythonJson {
    param($Python,[string[]]$Arguments,[switch]$PermitFailure)
    if ($Arguments -contains '--prepare') { $script:Calls.Add('prepare'); return $script:Prepared }
    $script:Calls.Add('parse')
    if ($Mode -eq 'parse_failure') { return @{passed=$false;ready_for_host_capture=$false;failures=@('strict fixture rejection')} }
    return @{passed=$true;ready_for_host_capture=$true;surface=@{surface=0x120000;width=800;height=600;base=0x4000000;bytes=480000;tid=10;eip=0x43de53;esp=0xe0000;route='hospital'}}
}
function Start-FramedHidden {
    param($Plan,$ProbePath,$LogPath,$Launch)
    $script:Calls.Add('start_hidden')
    if ($Mode -eq 'start_failure') { throw 'synthetic hidden desktop failure' }
    $palette=New-Object byte[] 1024
    for ($i=0;$i -lt 256;$i++) { $palette[$i*4]=[byte]$i }
    [IO.File]::WriteAllBytes($Plan.palette_path,$palette)
    $script:LogPath=$LogPath
    $Launch.session=@{handle=123;desktop=456;identity=@{process_id=100;path='synthetic-cdb.bin';creation_utc='2026-09-06T01:00:00Z'};desktop_name='fixture_hidden';command_line='synthetic no-launch'}
    if ($Mode -eq 'partial_start_failure') { throw 'synthetic identity query failed after process creation' }
    return $Launch.session
}
function Find-FramedOwnedChildren {
    param($Plan,$Session,$StartedAt,$Owned)
    $script:FindCount++
    $script:Calls.Add('discover')
    $Owned['200']=@{handle=201;identity=@{process_id=200;path=$Plan.candidate_path;parent_process_id=100;creation_utc='2026-09-06T01:00:01Z'}}
    if ($Mode -eq 'ambiguous') {
        $Owned['201']=@{handle=202;identity=@{process_id=201;path=$Plan.candidate_path;parent_process_id=100}}
        throw 'Ambiguous candidate PID: synthetic double child'
    }
    if ($Mode -eq 'early_map' -and $script:FindCount -eq 1) {
        [IO.File]::WriteAllText($script:LogPath,"SURFDUMP_READY map`nSURFDUMP_HOST_READY`n")
    } else { [IO.File]::WriteAllText($script:LogPath,"SURFDUMP_READY map`nMODAL_SURFDUMP_HOST_READY`n") }
}
function Test-FramedProcessExited { param($Session); $script:Calls.Add('poll_live'); return $false }
function Start-Sleep { param($Milliseconds); $script:Calls.Add('wait') }
function Save-FramedSnapshot {
    param($OwnedGame,$Surface,$RawPath)
    $script:Calls.Add('read_snapshot')
    if ($script:Calls.IndexOf('parse') -lt 0) { throw 'Read before full parser!' }
    $bytes=New-Object byte[] $Surface.bytes
    [IO.File]::WriteAllBytes($RawPath,$bytes)
    return @{path=$RawPath;sha256=(Get-FramedHash $RawPath);bytes=$Surface.bytes;width=800;height=600;pitch=800;pixel_reads=1;paused=$true}
}
function Stop-FramedOwned {
    param($OwnedProcess)
    $script:Calls.Add(('stop_'+$OwnedProcess.identity.process_id))
    return @{identity=$OwnedProcess.identity;absent=($Mode -ne 'cleanup_failure');handle_closed=$true;termination_requested=$true}
}
function Close-FramedDesktop { param($Session); $script:Calls.Add('close_desktop'); return $true }
$inputPath=Join-Path $FixtureRoot 'input.bin'; $proxyPath=Join-Path $FixtureRoot 'proxy.bin'
[IO.File]::WriteAllBytes($inputPath,[byte[]](1,2,3)); [IO.File]::WriteAllBytes($proxyPath,[byte[]](4,5,6))
$hash=Get-FramedHash $inputPath; $proxyHash=Get-FramedHash $proxyPath
$candidateDir=Join-Path $FixtureRoot 'candidate'; $outDir=Join-Path $FixtureRoot 'output'
$probe=".echo synthetic fixture`ng`n"
$algorithm=[Security.Cryptography.SHA256]::Create()
$probeHash=([BitConverter]::ToString($algorithm.ComputeHash([Text.Encoding]::UTF8.GetBytes($probe)))).Replace('-','').ToLowerInvariant()
$algorithm.Dispose()
$script:Prepared=@{packet=@{prepared=$true};probe=$probe;probe_sha256=$probeHash}
$plan=@{out_dir=$outDir;candidate_dir=$candidateDir;candidate_path=(Join-Path $candidateDir 'copied-synthetic.bin');
    input_candidate=$inputPath;original=$inputPath;original_sha256=$hash;candidate_sha256=$hash;
    proxy_manifest=$inputPath;proxy_manifest_sha256=$hash;proxy_source=$inputPath;proxy_source_sha256=$hash;
    proxy_input=$proxyPath;proxy_path=(Join-Path $candidateDir 'copied-proxy.bin');proxy_sha256=$proxyHash;
    host_path=$HostPath;host_sha256=(Get-FramedHash $HostPath);trace=$inputPath;trace_sha256=$hash;
    converter=$Converter;converter_sha256=(Get-FramedHash $Converter);python=$Python;python_sha256=(Get-FramedHash $Python);
    cdb=$inputPath;cdb_sha256=$hash;probe_sha256=$probeHash;route='hospital';width=800;height=600;resolution='800x600';stage='synthetic';
    availability='existing_flags';castle_index=0;minimap_viewport=$false;palette_path=(Join-Path $candidateDir 'ddraw_surfdump_palette.bin')}
$bundle=@{plan=$plan;prepared=$script:Prepared}
$result=Invoke-FramedCapture $bundle -DoExecute:($Mode -ne 'dry_run')
if ($Mode -eq 'dry_run') {
    Assert-Case ($result.status -eq 'dry_run' -and -not $result.executed -and $script:Calls.Count -eq 0) 'Dry-run reached a runtime boundary'
    Assert-Case (-not (Test-Path $outDir) -and -not (Test-Path $candidateDir)) 'Dry-run created artifact directories'
} else {
    Assert-Case (Test-Path (Join-Path $outDir 'summary.json')) 'Missing final failure/success summary'
    if ($Mode -eq 'start_failure') {
        Assert-Case (-not $result.executed -and -not $result.passed -and $script:Calls.Count -eq 2) 'Failed hidden launch continued'
    } else {
        $debuggerStop=$script:Calls.IndexOf('stop_100'); $gameStop=$script:Calls.IndexOf('stop_200')
        Assert-Case ($debuggerStop -ge 0 -and $gameStop -gt $debuggerStop) 'Cleanup did not stop debugger FIRST'
        if ($Mode -in @('parse_failure','ambiguous','partial_start_failure')) {
            Assert-Case (-not $result.passed -and $script:Calls.IndexOf('read_snapshot') -lt 0 -and -not $result.png) 'Failure was converted into capture proof'
        } else {
            Assert-Case ($null -ne $result.png -and (Test-Path (Join-Path $outDir 'surface.png'))) 'Raw diagnostic was not converted'
            Assert-Case ($result.passed -eq ($Mode -ne 'cleanup_failure')) 'Incorrect bounded success/cleanup failure'
        }
        if ($Mode -eq 'early_map') { Assert-Case ($script:Calls.IndexOf('wait') -lt $script:Calls.IndexOf('parse') -and $script:Calls.IndexOf('wait') -ge 0) 'Earlier map-ready incorrectly triggered parser/capture' }
        if ($Mode -eq 'ambiguous') { Assert-Case ($script:Calls.IndexOf('stop_201') -gt $debuggerStop) 'Ambiguous but owned second child was not cleaned after debugger' }
    }
    Assert-Case ((Get-FramedHash $inputPath) -eq $hash -and (Get-FramedHash $proxyPath) -eq $proxyHash) 'Inputs modified'
}
@{passed=$true;mode=$Mode;calls=@($script:Calls);result_status=$result.status} | ConvertTo-Json -Depth 5
'''


class FramedScreenCaptureTests(unittest.TestCase):
    def run_ps(self, body: str, mode: str = "pure") -> dict:
        with tempfile.TemporaryDirectory(prefix="clash-framed-host-fixture-") as directory:
            temp = Path(directory)
            fixture = temp / "fixture.ps1"
            fixture.write_text(PRELUDE + body, encoding="utf-8")
            result = subprocess.run(
                [str(PS), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(fixture),
                 "-HostPath", str(HOST), "-FixtureRoot", str(temp), "-Python", sys.executable,
                 "-Converter", str(ROOT / "tools/cdb_surface_dump_to_png.py"), "-Mode", mode],
                capture_output=True, text=True, encoding='utf-8', timeout=45, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(result.stdout)

    def test_readiness_surface_and_child_identity(self):
        self.assertTrue(self.run_ps(PURE)["passed"])

    def test_path_boundary_and_existing_artifact_rejections(self):
        self.assertTrue(self.run_ps(PATHS)["passed"])

    def test_dry_run_never_reaches_native_or_creates_outputs(self):
        self.assertEqual(self.run_ps(ORCHESTRATION, "dry_run")["calls"], [])

    def test_full_mocked_hidden_capture_and_earlier_map_ready(self):
        for mode in ("success", "early_map"):
            with self.subTest(mode=mode):
                result = self.run_ps(ORCHESTRATION, mode)
                self.assertEqual(result["calls"].count("read_snapshot"), 1)

    def test_mocked_failures_cleanup_order_and_diagnostic_conversion(self):
        for mode in ("start_failure", "partial_start_failure", "parse_failure", "ambiguous", "cleanup_failure"):
            with self.subTest(mode=mode):
                self.assertTrue(self.run_ps(ORCHESTRATION, mode)["passed"])

    def test_native_and_provenance_contracts_are_explicit(self):
        source = HOST.read_text(encoding="utf-8")
        for forbidden in ("AllowVisibleDesktop", "SendInput", "SetCursorPos", "PostMessage", "SetForegroundWindow", "Stop-Process", "Remove-Item", "-Force -", "CLASH_PROXY_PRESENT=1"):
            self.assertNotIn(forbidden, source)
        for required in (
            "[switch]$Execute", "if (-not $DoExecute)", "CreateDesktopW", "CreateProcessW", "$startup.desktop=$desktopName",
            "$startup.show=0", "$false,0x410,$environmentPointer", "$environment['CLASH_PROXY_PRESENT'] = '0'",
            "[Environment]::GetEnvironmentVariables()", "GetProcessTimes", "QueryFullProcessImageNameW",
            "ParentProcessId=", "creation_filetime", "ReadProcessMemory", "0x50ee24", "pixel_reads=1",
            "$watch.Elapsed.TotalSeconds -lt 120", "source_sha256", "output_sha256", "--candidate-sha256",
            "@($plan.host_path,$plan.host_sha256)", "@($plan.cdb,$plan.cdb_sha256)", "--prepare", "--packet",
            "[IO.File]::Copy($plan.input_candidate,$plan.candidate_path,$false)",
            "[IO.File]::Copy($plan.proxy_input,$plan.proxy_path,$false)",
            "ddraw_surfdump_palette.bin", "directdraw-palette", "finally {",
        ):
            self.assertIn(required, source)
        self.assertNotIn("SetEnvironmentVariable", source)
        self.assertNotIn("run_cdb_surface_dump.ps1", source)
        self.assertLess(source.index("$summary.trace=Invoke-FramedPythonJson"), source.index("$summary.snapshot=Save-FramedSnapshot"))
        self.assertLess(source.index("$summary.cleanup.cdb=Stop-FramedOwned"), source.index("$summary.cleanup.candidates += (Stop-FramedOwned"))

    def test_redirected_packet_unicode_is_valid_utf8_json(self):
        body = r'''
$encodingAssignments=@($ast.EndBlock.Statements | Where-Object {
    $_ -is [System.Management.Automation.Language.AssignmentStatementAst] -and
    $_.Left.Extent.Text -in @('$OutputEncoding','[Console]::OutputEncoding')
})
Assert-Case ($encodingAssignments.Count -eq 2) 'Missing explicit process-local stdout encoding'
foreach ($node in $encodingAssignments) { . ([scriptblock]::Create($node.Extent.Text)) }
# Build Unicode without depending on the fixture script file's Windows encoding.
@{packet=@{rationale=('4338E0'+[char]0x2192+'435BC0');label=([string][char]0x0142+[char]0x00f3+[char]0x017c)};passed=$true} | ConvertTo-Json -Depth 8
'''
        result = self.run_ps(body)
        self.assertEqual(result['packet']['rationale'], '4338E0\u2192435BC0')
        self.assertEqual(result['packet']['label'], '\u0142\u00f3\u017c')

    def test_live_header_checked_before_single_pixel_read(self):
        body = r'''
foreach ($name in @('Get-FramedHash','Save-FramedSnapshot')) { Import-Function $name }
$script:Reads=New-Object 'Collections.Generic.List[object]'
$script:Bad=''
function Read-FramedMemory {
    param($Handle,[long]$Address,[int]$Count)
    $script:Reads.Add(@{address=$Address;count=$Count})
    $bytes=New-Object byte[] $Count
    if ($Count -eq 188) {
        [BitConverter]::GetBytes([uint16]$(if ($script:Bad -eq 'width') {801} else {800})).CopyTo($bytes,0)
        [BitConverter]::GetBytes([uint16]$(if ($script:Bad -eq 'height') {601} else {600})).CopyTo($bytes,2)
        [BitConverter]::GetBytes([uint32]$(if ($script:Bad -eq 'pixels') {0} else {0x4000000})).CopyTo($bytes,4)
        [BitConverter]::GetBytes([uint32]$(if ($script:Bad -eq 'vtable') {0x50eec4} else {0x50ee24})).CopyTo($bytes,184)
    }
    return ,$bytes
}
$surface=@{surface=0x120000;base=0x4000000;bytes=480000;width=800;height=600}
$game=@{handle=42}; $raw=Join-Path $FixtureRoot 'synthetic.raw'
$result=Save-FramedSnapshot $game $surface $raw
Assert-Case ($script:Reads.Count -eq 2 -and $script:Reads[0].count -eq 188 -and $script:Reads[1].count -eq 480000 -and $result.pixel_reads -eq 1) 'Snapshot was not one header followed by one pixel read'
foreach ($bad in @('width','height','pixels','vtable')) {
    $script:Reads.Clear(); $script:Bad=$bad
    Expect-Failure { Save-FramedSnapshot $game $surface $raw } $bad
    Assert-Case ($script:Reads.Count -eq 1) 'Invalid header reached pixel read'
}
@{passed=$true;cases=5} | ConvertTo-Json
'''
        self.assertTrue(self.run_ps(body)['passed'])

    def test_actual_read_function_marshals_pointer_sized_count(self):
        # Exercise PowerShell 5.1 argument conversion with the real host
        # function. This managed stand-in never reads another process.
        body = r'''
Import-Function 'Read-FramedMemory'
Add-Type -TypeDefinition @'
using System;
public static class FramedScreenNative {
    public static ulong LastCount;
    public static bool ShortRead, Fail;
    public static bool ReadProcessMemory(IntPtr handle, IntPtr address, byte[] bytes, UIntPtr count, out UIntPtr read) {
        LastCount = count.ToUInt64();
        if (LastCount != (ulong)bytes.Length) throw new Exception("count and buffer differ");
        bytes[0] = 0xab;
        bytes[bytes.Length - 1] = 0xcd;
        read = new UIntPtr(LastCount - (ShortRead ? 1UL : 0UL));
        return !Fail;
    }
}
'@
foreach ($count in @(188,480000,786432)) {
    $bytes = Read-FramedMemory ([IntPtr]42) 0x120000 $count
    Assert-Case ($bytes -is [byte[]] -and $bytes.Length -eq $count) 'Snapshot byte array differs'
    Assert-Case ([FramedScreenNative]::LastCount -eq $count -and $bytes[0] -eq 0xab -and $bytes[-1] -eq 0xcd) 'Pointer-sized count or returned data differs'
}
[FramedScreenNative]::ShortRead = $true
Expect-Failure { Read-FramedMemory ([IntPtr]42) 0x120000 188 } 'short native read'
[FramedScreenNative]::ShortRead = $false
[FramedScreenNative]::Fail = $true
Expect-Failure { Read-FramedMemory ([IntPtr]42) 0x120000 188 } 'failed native read'
@{passed=$true;cases=5;native_process_read=$false} | ConvertTo-Json
'''
        self.assertTrue(self.run_ps(body)['passed'])


if __name__ == "__main__":
    unittest.main()
