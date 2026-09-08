#!/usr/bin/env python3
"""Offline host contracts. Extracted functions only; no game/CDB/process launch.

Native declarations are compiled, never invoked. Managed substitutes exercise
ReadProcessMemory/WriteFile signatures; orchestration replaces runtime boundaries.
Only temporary synthetic data and actual offline PNG conversion are used.
"""
from __future__ import annotations

import json
import contextlib
import io
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from test_framed_screen_capture import PRELUDE, PATHS, PS

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "scripts/cdb/run_framed_minimap_scroll_capture.ps1"

COMMON = r'''
function New-ValidReport {
 param([string]$Phase='before')
 $state=@{tid=123;eip=$(if ($Phase -eq 'after') {0x40b0e5} else {0x406fa0});esp=0x100000;world_x=100;world_y=100;scale=2}
 $surface=@{map=0x120000;width=1024;height=768;base=0x4000000;vtable=0x50ee24;backing=0x140000;bwidth=214;bheight=214;bbase=0x5000000;bvtable=0x50ee24}
 return @{passed=$true;source_authenticated=$true;phase=$Phase;packet_sha256=('a'*64);candidate_sha256=('b'*64);log_prefix_bytes=4;log_prefix_sha256=('c'*64);
 sequence=@{states=@{$Phase=$state};surfaces=@{$Phase=$surface}}}
}
$plan=@{width=1024;height=768;packet_sha256=('a'*64);candidate_sha256=('b'*64);out_dir=$FixtureRoot}
'''

PURE = COMMON + r'''
foreach ($name in @('Test-ScrollReady','Assert-ScrollValidation','Assert-ScrollSurfaces','Select-ScrollChildren')) { Import-Function $name }
foreach ($phase in @('initial','before','after')) {
 $marker=if ($phase -eq 'initial') {'SURFDUMP_HOST_READY'} else {'MMSC_HOST_READY phase='+$phase}
 Assert-Case (Test-ScrollReady ($marker+"`n") $phase) 'complete LF readiness rejected'
 Assert-Case (Test-ScrollReady ($marker+"`r`n") $phase) 'complete CRLF readiness rejected'
 foreach ($text in @('', $marker, ('0:000> '+$marker+"`n"),($marker+" other`n"))) {
  Assert-Case (-not (Test-ScrollReady $text $phase)) 'malformed readiness accepted'
 }
}
$valid=New-ValidReport
[void](Assert-ScrollSurfaces $valid $plan before)
foreach ($case in @(@('width',1023),@('height',769),@('width','1024'),@('base',0),@('base',4294967290),
 @('map',0),@('map',0x51d4c0),@('backing',0x120000),@('backing',0x51d4c0),@('bbase',0x4000000),
 @('bwidth',213),@('bheight',215),@('vtable',0x50eec4),@('bvtable',0))) {
 $r=New-ValidReport;$r.sequence.surfaces.before.($case[0])=$case[1]
 Expect-Failure { Assert-ScrollSurfaces $r $plan before } ('surface '+$case[0])
}
foreach ($case in @(@('tid',0),@('eip',0x40b0e5),@('esp',0),@('esp',0x100001),@('world_x',101),@('world_y',0),@('scale',1),@('tid','123'))) {
 $r=New-ValidReport;$r.sequence.states.before.($case[0])=$case[1]
 Expect-Failure { Assert-ScrollSurfaces $r $plan before } ('state '+$case[0])
}
foreach ($case in @(@('passed',$false),@('passed','true'),@('source_authenticated',1),@('phase','after'),
 @('packet_sha256',('d'*64)),@('candidate_sha256',('d'*64)),@('log_prefix_bytes',0),@('log_prefix_bytes','4'),
 @('log_prefix_bytes',16777217),@('log_prefix_sha256','bad'))) {
 $r=New-ValidReport;$r.($case[0])=$case[1]
 Expect-Failure { Assert-ScrollValidation $r $plan before } ('validation '+$case[0])
}
$start=[datetime]'2026-09-06T01:00:00Z'
$rows=@(@{ParentProcessId=100;ProcessId=200;ExecutablePath='C:\ClashTests\new\candidate.bin';CreationDate=$start.AddSeconds(1)},
 @{ParentProcessId=101;ProcessId=201;ExecutablePath='C:\ClashTests\new\candidate.bin';CreationDate=$start.AddSeconds(1)},
 @{ParentProcessId=100;ProcessId=202;ExecutablePath='C:\ClashTests\other\candidate.bin';CreationDate=$start.AddSeconds(1)})
$selected=@(Select-ScrollChildren $rows 100 'C:\ClashTests\new\candidate.bin' $start)
Assert-Case ($selected.Count -eq 1 -and $selected[0].ProcessId -eq 200) 'parent/path ownership filter'
$rows[0].CreationDate=$start.AddSeconds(-1)
Expect-Failure { Select-ScrollChildren $rows 100 'C:\ClashTests\new\candidate.bin' $start } 'stale child'
@{passed=$true} | ConvertTo-Json
'''

QUOTING = r'''
foreach ($name in @('Initialize-ScrollNative','ConvertTo-ScrollArgument','Get-ScrollLaunchCommand')) { Import-Function $name }
# Compilation only: no declaration below is invoked, except shell argv parsing.
Initialize-ScrollNative
Assert-Case ($null -ne ('ScrollScreenNative' -as [type])) 'native declarations did not compile'
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class ArgvOnly {
 [DllImport("shell32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern IntPtr CommandLineToArgvW(string command,out int count);
 [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr pointer);
 public static string[] Parse(string command) {
  int count; IntPtr ptr=CommandLineToArgvW(command,out count);
  if(ptr==IntPtr.Zero) throw new Exception("argv failed");
  try { var args=new string[count];for(int i=0;i<count;i++) args[i]=Marshal.PtrToStringUni(Marshal.ReadIntPtr(ptr,i*IntPtr.Size));return args;}
  finally{LocalFree(ptr);}
 }
}
'@
$plan=@{cdb='C:\Program Files (x86)\Debuggers\cdb.exe';candidate_path='C:\ClashTests\with spaces\candidate.exe'}
$probe='C:\ClashCaptures\with spaces\initial.cdb';$log='C:\ClashCaptures\with spaces\cdb.log'
$command=Get-ScrollLaunchCommand $plan $probe $log
$args=[ArgvOnly]::Parse($command)
$expected=@($plan.cdb,'-hd','-logo',$log,'-c',('$$>a<"'+$probe+'"'),$plan.candidate_path)
Assert-Case ($args.Count -eq $expected.Count) 'wrong launch argv count'
for ($i=0;$i -lt $args.Count;$i++) { Assert-Case ($args[$i] -ceq $expected[$i]) ('wrong argv '+$i) }
foreach ($value in @('','C:\trailing\','C:\space path\','a"b','C:\slash\"quoted"')) {
 $parsed=[ArgvOnly]::Parse(('program.exe '+(ConvertTo-ScrollArgument $value)))
 Assert-Case ($parsed.Count -eq 2 -and $parsed[1] -ceq $value) 'CRT quote/slash round trip'
}
foreach ($bad in @('C:\x\$arg1.cdb','C:\x\a;b.cdb',("C:\x\a`nb.cdb"))) {
 Expect-Failure { Get-ScrollLaunchCommand $plan $bad $log } 'unsafe command file'
}
@{passed=$true;command=$command} | ConvertTo-Json
'''

TRANSPORT = r'''
foreach ($name in @('Send-ScrollCommands','Get-ScrollHash','Get-ScrollBytesHash')) { Import-Function $name }
Add-Type @'
using System;
public static class ScrollScreenNative {
 public static byte[] Sent; public static bool Fail,Short;
 public static bool WriteFile(IntPtr handle,byte[] bytes,uint count,out uint written,IntPtr overlap) {
  Sent=(byte[])bytes.Clone();written=Short?count-1:count;return !Fail;
 }
}
'@
function Get-ScrollBoundPrefix { param($Report,$Plan,$Phase); if ($Report.phase -cne $Phase) {throw 'wrong preceding phase'};return ,[byte[]](1,2) }
$packet=@{before_commands=".echo before`n";continue_commands=".echo after`n"}
$plan=@{out_dir=$FixtureRoot;packet_sha256=('a'*64)}
foreach ($phase in @('before','continue')) {
 $key=if ($phase -eq 'before') {'before_commands'} else {'continue_commands'}
 $path=Join-Path $FixtureRoot ($phase+'.cdb')
 [IO.File]::WriteAllText($path,$packet.$key,[Text.Encoding]::ASCII)
 $plan[$key+'_sha256']=Get-ScrollHash $path
}
$session=@{input_write=[IntPtr]123;transport_phase='initial'}
$r=@{phase='initial';log_prefix_sha256=('b'*64)}
$sent=Send-ScrollCommands $session $plan $packet $r before
$expected='$$>a<"'+(Join-Path $FixtureRoot 'before.cdb')+'"'+ "`r`n"
Assert-Case ([Text.Encoding]::ASCII.GetString([ScrollScreenNative]::Sent) -ceq $expected) 'script was not source-quiet exact stdin bytes'
Assert-Case ($session.transport_phase -ceq 'before' -and $sent.bytes -eq $expected.Length) 'successful dispatch not recorded'
Expect-Failure { Send-ScrollCommands $session $plan $packet $r before } 'duplicate dispatch'
$r.phase='before';[void](Send-ScrollCommands $session $plan $packet $r continue)
Assert-Case ($session.transport_phase -ceq 'after') 'continue did not advance'
foreach ($flag in @('Short','Fail')) {
 $session.transport_phase='initial';$r.phase='initial'
 if ($flag -eq 'Short') {[ScrollScreenNative]::Short=$true} else {[ScrollScreenNative]::Fail=$true}
 Expect-Failure { Send-ScrollCommands $session $plan $packet $r before } 'partial/failed pipe write'
 Assert-Case ($session.transport_phase -ceq 'initial') 'failed write advanced phase'
 [ScrollScreenNative]::Short=$false;[ScrollScreenNative]::Fail=$false
}
[IO.File]::AppendAllText((Join-Path $FixtureRoot 'before.cdb'),'changed')
Expect-Failure { Send-ScrollCommands $session $plan $packet $r before } 'modified canonical script'
@{passed=$true} | ConvertTo-Json
'''

PREFIX = COMMON + r'''
foreach ($name in @('Assert-ScrollValidation','Get-ScrollBoundPrefix','Read-ScrollLogBytes','Get-ScrollBytesHash')) { Import-Function $name }
$r=New-ValidReport;$r.log_prefix_sha256=Get-ScrollBytesHash ([byte[]](1,2,3,4))
$path=Join-Path $FixtureRoot 'cdb.log'
[IO.File]::WriteAllBytes($path,[byte[]](1,2,3,4,5,6))
Assert-Case ((Get-ScrollBoundPrefix $r $plan before).Length -eq 4) 'append-only tail affected exact prefix'
[IO.File]::WriteAllBytes($path,[byte[]](1,2,3))
Expect-Failure { Get-ScrollBoundPrefix $r $plan before } 'truncated prefix'
[IO.File]::WriteAllBytes($path,[byte[]](9,2,3,4,5))
Expect-Failure { Get-ScrollBoundPrefix $r $plan before } 'changed prefix'
@{passed=$true} | ConvertTo-Json
'''

MEMORY = r'''
Import-Function 'Read-ScrollMemory'
Add-Type @'
using System;
public static class ScrollScreenNative {
 public static ulong Count; public static bool Short,Fail;
 public static bool ReadProcessMemory(IntPtr process,IntPtr address,byte[] bytes,UIntPtr count,out UIntPtr read) {
  Count=count.ToUInt64();bytes[0]=7;bytes[bytes.Length-1]=9;
  read=new UIntPtr(Short?Count-1:Count);return !Fail;
 }
}
'@
foreach ($count in @(188,45796,786432)) {
 $data=Read-ScrollMemory ([IntPtr]123) 0x4000000 $count
 Assert-Case ($data -is [byte[]] -and $data.Length -eq $count -and $data[0] -eq 7 -and $data[-1] -eq 9 -and [ScrollScreenNative]::Count -eq $count) 'pointer-sized count or returned data wrong'
}
[ScrollScreenNative]::Short=$true
Expect-Failure { Read-ScrollMemory ([IntPtr]123) 0x4000000 188 } 'short native read'
[ScrollScreenNative]::Short=$false;[ScrollScreenNative]::Fail=$true
Expect-Failure { Read-ScrollMemory ([IntPtr]123) 0x4000000 188 } 'failed native read'
@{passed=$true} | ConvertTo-Json
'''

CAPTURE = COMMON + r'''
foreach ($name in @('Save-ScrollPair','Assert-ScrollValidation','Assert-ScrollSurfaces','Get-ScrollHash','Write-ScrollJson')) { Import-Function $name }
$script:Calls=New-Object 'Collections.Generic.List[string]'
function Get-ScrollBoundPrefix { return ,[byte[]](1,2,3,4) }
function Read-ScrollMemory {
 param($Handle,$Address,$Count)
 $script:Calls.Add(('{0}:{1}' -f $Address,$Count))
 $bytes=New-Object byte[] $Count
 if ($Count -eq 188) {
  $width=if ($Address -eq 0x120000) {1024} else {214}
  $height=if ($Address -eq 0x120000) {768} else {214}
  $base=if ($Address -eq 0x120000) {0x4000000} else {0x5000000}
  if ($Mode -eq 'bad_header' -and $Address -eq 0x140000) {$width=213}
  [BitConverter]::GetBytes([uint16]$width).CopyTo($bytes,0)
  [BitConverter]::GetBytes([uint16]$height).CopyTo($bytes,2)
  [BitConverter]::GetBytes([uint32]$base).CopyTo($bytes,4)
  [BitConverter]::GetBytes([uint32]0x50ee24).CopyTo($bytes,184)
 }
 return ,$bytes
}
$r=New-ValidReport;$game=@{handle=[IntPtr]123;identity=@{process_id=200}}
if ($Mode -eq 'bad_header') {
 Expect-Failure { Save-ScrollPair $game $r $plan before } 'live backing header mismatch'
 Assert-Case ($script:Calls.Count -eq 2) 'pixels read before both header checks'
 Assert-Case ((Test-Path (Join-Path $FixtureRoot 'before-frame-header.raw')) -and (Test-Path (Join-Path $FixtureRoot 'before-backing-header.raw'))) 'failed header evidence lost'
} else {
 $result=Save-ScrollPair $game $r $plan before
 Assert-Case (($script:Calls -join ',') -ceq '1179648:188,1310720:188,67108864:786432,83886080:45796') 'read count/order not two headers then two pixels'
 $receipt=[IO.File]::ReadAllText($result.receipt.path) | ConvertFrom-Json
 $keys=@($receipt.PSObject.Properties.Name | Sort-Object)
 $expected=@('phase','packet_sha256','candidate_sha256','initial_probe_sha256','before_commands_sha256','continue_commands_sha256',
 'log_prefix_bytes','log_prefix_sha256','tid','eip','esp','map','base','backing','bbase','width','height','pitch','bwidth','bheight','bpitch','frame_sha256','backing_sha256') | Sort-Object
 Assert-Case (($keys -join ',') -ceq ($expected -join ',')) 'frozen parser receipt keyset changed'
 Assert-Case ($result.game_identity.process_id -eq 200 -and $result.header_reads -eq 2 -and $result.frame_pixel_reads -eq 1 -and $result.backing_pixel_reads -eq 1 -and $result.started_at -and $result.captured_at) 'host envelope missing actual capture identity'
}
@{passed=$true;calls=@($script:Calls)} | ConvertTo-Json
'''

ORCHESTRATION = r'''
foreach ($name in @('Invoke-ScrollCapture','Get-ScrollHash','Get-ScrollBytesHash','Write-ScrollJson')) { Import-Function $name }
$script:Calls=New-Object 'Collections.Generic.List[string]'
function Resolve-ScrollPath { param($Path,$Root,$Kind); if (Test-Path -LiteralPath $Path) {throw 'output exists'};return $Path }
function Initialize-ScrollNative { throw 'Native initialization forbidden in offline orchestration' }
function Invoke-ScrollOperation {
 param($Plan,$Operation)
 $script:Calls.Add('operation_'+$Operation)
 if ($Operation -eq 'prepare') {return @{passed=$true;packet_sha256=$Plan.packet_sha256}}
 if ($Operation -eq 'erasure') {return @{passed=($Mode -ne 'erasure_failure');phase='erasure';packet_sha256=$Plan.packet_sha256}}
 throw 'unexpected operation'
}
function Start-ScrollHidden {
 param($Plan,$ProbePath,$LogPath,$Launch)
 $script:Calls.Add('start_hidden')
 if ($Mode -eq 'start_failure') {throw 'synthetic desktop failure'}
 $palette=New-Object byte[] 1024
 for ($i=0;$i -lt 256;$i++) {$palette[$i*4]=[byte]$i}
 [IO.File]::WriteAllBytes($Plan.palette_path,$palette)
 [IO.File]::WriteAllText($LogPath,"synthetic offline log`n")
 $Launch.session=@{handle=[IntPtr]123;desktop=[IntPtr]456;input_write=[IntPtr]789;transport_phase='initial';
 identity=@{process_id=100;path='synthetic-debugger.bin'};desktop_name='synthetic_hidden';command_line='NO LAUNCH'}
 if ($Mode -eq 'partial_start_failure') {throw 'synthetic identity query after process creation'}
 return $Launch.session
}
function Find-ScrollOwnedChildren {
 param($Plan,$Session,$StartedAt,$Owned)
 $script:Calls.Add('discover')
 $Owned['200']=@{handle=[IntPtr]201;identity=@{process_id=200;parent_process_id=100;path=$Plan.candidate_path}}
}
function Wait-ScrollPause {
 param($Plan,$Session,$StartedAt,$Owned,$Watch,$Phase)
 $script:Calls.Add('validate_'+$Phase)
 Find-ScrollOwnedChildren $Plan $Session $StartedAt $Owned
 if ($Mode -eq ($Phase+'_failure')) {throw ('strict '+$Phase+' fixture rejection')}
 return @{passed=$true;phase=$Phase}
}
function Get-ScrollBoundPrefix { return ,[Text.Encoding]::ASCII.GetBytes("synthetic offline prefix`n") }
function Send-ScrollCommands {
 param($Session,$Plan,$Packet,$Validation,$Phase)
 $script:Calls.Add('send_'+$Phase)
 if ($Validation.phase -cne $(if ($Phase -eq 'before') {'initial'} else {'before'})) {throw 'incorrect validated phase'}
 return @{phase=$Phase;synthetic_no_write=$true}
}
function Save-ScrollPair {
 param($Game,$Report,$Plan,$Phase)
 $script:Calls.Add('capture_'+$Phase)
 if ($Report.phase -cne $Phase -or $script:Calls.IndexOf('validate_'+$Phase) -lt 0) {throw 'capture before validation'}
 [IO.File]::WriteAllText((Join-Path $Plan.out_dir ($Phase+'-prefix.log')),"synthetic prefix`n")
 $frame=Join-Path $Plan.out_dir ($Phase+'-frame.raw');$back=Join-Path $Plan.out_dir ($Phase+'-backing.raw')
 [IO.File]::WriteAllBytes($frame,(New-Object byte[] (1024*768)))
 [IO.File]::WriteAllBytes($back,(New-Object byte[] (214*214)))
 return @{receipt=@{value=@{width=1024;height=768;bwidth=214;bheight=214;frame_sha256=(Get-ScrollHash $frame);backing_sha256=(Get-ScrollHash $back)}}}
}
function Stop-ScrollOwned {
 param($Session)
 $script:Calls.Add('stop_'+$Session.identity.process_id)
 return @{identity=$Session.identity;absent=($Mode -ne 'cleanup_failure');handle_closed=$true}
}
function Close-ScrollInput { $script:Calls.Add('close_input');return $true }
function Close-ScrollDesktop { $script:Calls.Add('close_desktop');return $true }
$input=Join-Path $FixtureRoot 'input.bin';$proxy=Join-Path $FixtureRoot 'proxy.bin'
[IO.File]::WriteAllBytes($input,[byte[]](1,2,3));[IO.File]::WriteAllBytes($proxy,[byte[]](4,5,6))
$hash=Get-ScrollHash $input;$phash=Get-ScrollHash $proxy
$out=Join-Path $FixtureRoot 'output';$dir=Join-Path $FixtureRoot 'candidate'
$plan=@{out_dir=$out;candidate_dir=$dir;candidate_path=(Join-Path $dir 'synthetic-candidate.bin');
 original=$input;original_sha256=$hash;input_candidate=$input;candidate_sha256=$hash;
 proxy_manifest=$input;proxy_manifest_sha256=$hash;proxy_source=$input;proxy_source_sha256=$hash;
 proxy_input=$proxy;proxy_sha256=$phash;proxy_path=(Join-Path $dir 'synthetic-proxy.bin');palette_path=(Join-Path $dir 'ddraw_surfdump_palette.bin');
 host_path=$HostPath;host_sha256=(Get-ScrollHash $HostPath);producer=$input;producer_sha256=$hash;trace=$input;trace_sha256=$hash;
 converter=$Converter;converter_sha256=(Get-ScrollHash $Converter);python=$Python;python_sha256=(Get-ScrollHash $Python);cdb=$input;cdb_sha256=$hash;
 packet_sha256=('a'*64);deadline_seconds=120;width=1024;height=768}
$packet=@{initial_probe=".echo synthetic initial`n";before_commands=".echo synthetic before`n";continue_commands=".echo synthetic after`n"}
foreach ($key in @('initial_probe','before_commands','continue_commands')) {$plan[$key+'_sha256']=Get-ScrollBytesHash ([Text.Encoding]::ASCII.GetBytes($packet[$key]))}
if ($Mode -eq 'changed_source') {$plan.producer_sha256='b'*64}
$result=Invoke-ScrollCapture @{plan=$plan;packet=$packet} -DoExecute:($Mode -ne 'dry_run')
if ($Mode -eq 'dry_run') {
 Assert-Case ($script:Calls.Count -eq 0 -and $result.status -eq 'dry_run' -and -not $result.executed) 'dry-run touched runtime'
 Assert-Case (-not (Test-Path $dir) -and -not (Test-Path $out)) 'dry-run created artifact directories'
} else {
 Assert-Case (Test-Path (Join-Path $out 'summary.json')) 'missing durable final summary'
 Assert-Case ($result.passed -eq ($Mode -eq 'normal')) 'wrong runtime/cleanup verdict'
 if ($Mode -eq 'changed_source') {
  Assert-Case ($script:Calls.Count -eq 0 -and -not $result.executed) 'changed source reached launch'
 } elseif ($Mode -eq 'start_failure') {
  Assert-Case (-not $result.executed -and $script:Calls.Count -eq 2) 'failed launch continued'
 } else {
  $stop=$script:Calls.IndexOf('stop_100');$child=$script:Calls.IndexOf('stop_200')
  Assert-Case ($stop -ge 0 -and $child -gt $stop -and $script:Calls.IndexOf('close_desktop') -gt $child) 'cleanup order'
  if ($Mode -eq 'cleanup_failure') {
   Assert-Case ($script:Calls.IndexOf('close_input') -lt 0 -and -not $result.cleanup.input_closed) 'stdin closed before debugger terminal'
  } else { Assert-Case ($script:Calls.IndexOf('close_input') -gt $child) 'stdin close order' }
  if ($Mode -in @('partial_start_failure','initial_failure')) {
   Assert-Case ($result.captures.Count -eq 0 -and $result.dispatches.Count -eq 0) 'initial failure dispatched or captured'
  } elseif ($Mode -eq 'before_failure') {
   Assert-Case ($result.captures.Count -eq 0 -and $result.dispatches.Count -eq 1 -and $script:Calls.IndexOf('send_continue') -lt 0) 'before failure continued'
  } elseif ($Mode -eq 'after_failure') {
   Assert-Case ($result.captures.Count -eq 1 -and $result.pngs.Count -eq 1 -and (Test-Path (Join-Path $out 'before-frame.png'))) 'after failure lost before raw/PNG'
  } else {
   Assert-Case ($result.captures.Count -eq 2 -and $result.dispatches.Count -eq 2 -and $result.pngs.Count -eq 2) 'paired evidence was lost'
   foreach ($phase in @('before','after')) {foreach ($kind in @('frame','backing')) {
    Assert-Case (Test-Path (Join-Path $out ($phase+'-'+$kind+'.png'))) 'raw diagnostic PNG missing'
   }}
  }
 }
 Assert-Case ((Get-ScrollHash $input) -ceq $hash -and (Get-ScrollHash $proxy) -ceq $phash) 'input bytes changed'
}
@{passed=$true;mode=$Mode;calls=@($script:Calls);failures=$result.failures} | ConvertTo-Json -Depth 5
'''


class ScrollHostTests(unittest.TestCase):
    def run_ps(self, body: str, mode: str = "normal") -> dict:
        with tempfile.TemporaryDirectory(prefix="clash-scroll-host-fixture-") as directory:
            temp = Path(directory)
            script = temp / "fixture.ps1"
            script.write_text(PRELUDE + body, encoding="utf-8-sig")
            result = subprocess.run(
                [str(PS), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script),
                 "-HostPath", str(HOST), "-FixtureRoot", str(temp), "-Python", sys.executable,
                 "-Converter", str(ROOT / "tools/cdb_surface_dump_to_png.py"), "-Mode", mode],
                capture_output=True, text=True, encoding="utf-8", timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(result.stdout)

    def test_paths_preserve_isolation_and_existing_artifacts(self):
        self.assertTrue(self.run_ps(PATHS.replace("Framed", "Scroll"))["passed"])

    def test_readiness_source_identity_surface_bounds_and_child_ownership(self):
        self.assertTrue(self.run_ps(PURE)["passed"])

    def test_native_declarations_compile_and_windows_launch_argv_round_trip(self):
        self.assertTrue(self.run_ps(QUOTING)["passed"])

    def test_exact_quiet_stdin_transport_and_partial_write_rejection(self):
        self.assertTrue(self.run_ps(TRANSPORT)["passed"])

    def test_validated_log_prefix_rejects_changes_and_truncation(self):
        self.assertTrue(self.run_ps(PREFIX)["passed"])

    def test_actual_read_function_uses_pointer_sized_count(self):
        self.assertTrue(self.run_ps(MEMORY)["passed"])

    def test_real_capture_function_checks_headers_and_exact_receipt(self):
        self.assertTrue(self.run_ps(CAPTURE)["passed"])
        self.assertTrue(self.run_ps(CAPTURE, "bad_header")["passed"])

    def test_fixed_python_bridge_compiles_and_transport_has_no_double_quotes(self):
        source = HOST.read_text(encoding="utf-8")
        bridge = re.search(r"\$script:ScrollPython = @'\n(.*?)\n'@", source, re.S)
        self.assertIsNotNone(bridge)
        compile(bridge[1], str(HOST) + ":ScrollPython", "exec")
        self.assertNotIn('"', bridge[1])

    def test_actual_wait_validates_before_return_and_obeys_deadline(self):
        body = COMMON + r'''
foreach ($name in @('Wait-ScrollPause','Test-ScrollReady','Assert-ScrollValidation','Write-ScrollJson')) { Import-Function $name }
$script:Calls=0
function Find-ScrollOwnedChildren {param($Plan,$Session,$Started,$Owned);$Owned['200']=@{identity=@{process_id=200}}}
function Read-ScrollLog {return "MMSC_HOST_READY phase=before~BT~n"}
function Test-ScrollProcessExited {return $false}
function Invoke-ScrollOperation {
 param($Plan,$Phase)
 $script:Calls++
 $r=New-ValidReport
 if ($Mode -eq 'failed') {$r.passed=$false}
 if ($Mode -eq 'late') {$watch.Elapsed.TotalSeconds=121}
 return $r
}
$plan.deadline_seconds=120;$owned=@{};$watch=@{Elapsed=@{TotalSeconds=0}}
if ($Mode -eq 'timeout') {$watch.Elapsed.TotalSeconds=120}
if ($Mode -eq 'normal') {
 $result=Wait-ScrollPause $plan @{} ([datetime]::UtcNow) $owned $watch before
 Assert-Case ($result.passed -and $script:Calls -eq 1 -and $owned.Count -eq 1) 'valid pause failed'
} else {
 Expect-Failure {Wait-ScrollPause $plan @{} ([datetime]::UtcNow) $owned $watch before} 'unsafe pause'
 Assert-Case ($script:Calls -eq $(if ($Mode -eq 'timeout') {0} else {1})) 'deadline did not limit validator'
}
@{passed=$true} | ConvertTo-Json
'''
        body = body.replace("~BT~", chr(96))
        for mode in ("normal", "failed", "late", "timeout"):
            with self.subTest(mode=mode):
                self.assertTrue(self.run_ps(body, mode)["passed"])

    def test_dry_run_has_no_files_or_runtime_boundaries(self):
        self.assertTrue(self.run_ps(ORCHESTRATION, "dry_run")["passed"])

    def test_full_mocked_capture_with_actual_four_png_conversions(self):
        self.assertTrue(self.run_ps(ORCHESTRATION)["passed"])

    def test_trace_and_cleanup_failures_preserve_evidence_without_passing(self):
        for mode in ("changed_source", "start_failure", "partial_start_failure", "initial_failure",
                     "before_failure", "after_failure", "erasure_failure", "cleanup_failure"):
            with self.subTest(mode=mode):
                self.assertTrue(self.run_ps(ORCHESTRATION, mode)["passed"])

    def test_fixed_bridge_executes_through_actual_powershell_c_transport(self):
        # Only the canonical producer's computation is replaced in this test;
        # the host's real Python -c transport and entire bridge execute.
        with tempfile.TemporaryDirectory(prefix="clash-scroll-bridge-transport-") as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            producer = """import hashlib,json
STAGE='synthetic_test_only'
def build_packet(original,candidate,**kwargs):
 assert original==bytes([1,2,3]) and candidate==bytes([4,5,6])
 return dict(kwargs, prepared=True, marker='unicode café', manual_input_proof=False)
def packet_hash(packet):
 return hashlib.sha256(json.dumps(packet,sort_keys=True).encode()).hexdigest()
"""
            (root / "tools/framed_minimap_scroll_probe.py").write_text(producer, encoding="utf-8")
            (root / "tools/framed_minimap_scroll_trace.py").write_text("# synthetic transport stand-in\n")
            (root / "original.bin").write_bytes(bytes([1, 2, 3]))
            (root / "candidate.bin").write_bytes(bytes([4, 5, 6]))
            body = r'''
foreach ($name in @('Invoke-ScrollOperation','Invoke-ScrollPythonJson')) { Import-Function $name }
$raw=[IO.File]::ReadAllText($HostPath)
$match=[regex]::Match($raw,"(?s)\~DOLLAR~script:ScrollPython = @'\r?\n(.*?)\r?\n'@")
Assert-Case $match.Success 'fixed bridge missing'
$script:ScrollPython=$match.Groups[1].Value
$script:RepoRoot='~ROOT~'
$plan=@{python=$Python;original=(Join-Path $script:RepoRoot 'original.bin');candidate_path=(Join-Path $script:RepoRoot 'candidate.bin');
 resolution='1024x768';target_x=11;target_y=17;out_dir=$FixtureRoot;candidate_sha256=('a'*64)}
$result=Invoke-ScrollOperation $plan prepare
Assert-Case ($result.passed -and $result.packet.marker -ceq 'unicode caf~E~' -and $result.packet.requested_scroll[0] -eq 11) 'real -c JSON/Unicode/arguments transport failed'
@{passed=$true} | ConvertTo-Json
'''
            body = body.replace("~ROOT~", str(root).replace("'", "''")).replace("~DOLLAR~", "$").replace("~E~", "é")
            self.assertTrue(self.run_ps(body)["passed"])

    @unittest.skipUnless(Path("C:/Clash/clash95.exe").is_file(), "read-only user original unavailable")
    def test_fixed_bridge_with_real_packet_trace_and_synthetic_buffers(self):
        # Reconstruct actual candidates only in memory. Never write game bytes.
        import test_framed_minimap_scroll_probe as fixtures
        fixtures.ScrollProbeTests.setUpClass()
        factory = fixtures.ScrollProbeTests()
        bridge = re.search(r"\$script:ScrollPython = @'\n(.*?)\n'@", HOST.read_text(), re.S)[1]
        compiled = compile(bridge, str(HOST) + ":ScrollPython", "exec")
        real_read = Path.read_bytes
        for resolution in ("1024x768", "802x602"):
            packet = factory.packets[resolution]
            candidate = factory.candidates[resolution]
            log, buffers = factory.pixel_fixture(resolution)
            with tempfile.TemporaryDirectory(prefix="clash-scroll-bridge-fixture-") as directory:
                folder = Path(directory)
                sentinel = folder / "in-memory-candidate.bin"
                def read_bytes(path):
                    return candidate if path == sentinel else real_read(path)
                for key, filename in (("initial_probe", "initial.cdb"), ("before_commands", "before.cdb"),
                                      ("continue_commands", "continue.cdb")):
                    (folder / filename).write_bytes(packet[key].encode("ascii"))
                saved = json.dumps(packet)
                (folder / "packet.json").write_text(saved)
                for phase in ("before", "after"):
                    (folder / f"{phase}-receipt.json").write_text(json.dumps(buffers["receipts"][phase]))
                    for kind in ("frame", "backing"):
                        (folder / f"{phase}-{kind}.raw").write_bytes(buffers[f"{phase}_{kind}"])
                def invoke(operation, raw_log):
                    (folder / "cdb.log").write_bytes(raw_log)
                    argv = ["bridge", operation, str(ROOT), str(fixtures.ORIGINAL), str(sentinel), resolution,
                            *map(str, packet["requested_scroll"]), str(folder), packet["candidate_sha256"]]
                    output = io.StringIO()
                    with mock.patch.object(Path, "read_bytes", read_bytes), mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(output):
                        with self.assertRaises(SystemExit) as stopped:
                            exec(compiled, {"__name__": "__main__"})
                    result = json.loads(output.getvalue())
                    self.assertEqual(stopped.exception.code, 0 if result["passed"] else 2)
                    return result
                initial = log.split(b"SURFDUMP_HOST_READY\n")[0] + b"SURFDUMP_HOST_READY\n"
                for operation, raw in (("prepare", b""), ("initial", initial),
                                       ("before", fixtures.complete_log(packet, stop_before=True)),
                                       ("after", log), ("erasure", log)):
                    with self.subTest(resolution=resolution, operation=operation):
                        result = invoke(operation, raw)
                        self.assertTrue(result["passed"], result.get("failures"))
                bad = initial.replace(b"PTILE_STATUS hook=full_converge status=1", b"PTILE_STATUS hook=full_converge status=0", 1)
                self.assertNotEqual(initial, bad)
                self.assertFalse(invoke("initial", bad)["passed"])
                self.assertFalse(invoke("initial", initial + b"MMSC_BEGIN tid=abc eip=00406fa0 esp=00100100\n")["passed"])
                for filename in ("initial.cdb", "before.cdb", "continue.cdb"):
                    path = folder / filename
                    good = path.read_bytes()
                    path.write_bytes(good + b".echo unauthorized\n")
                    self.assertFalse(invoke("before", fixtures.complete_log(packet, stop_before=True))["passed"])
                    path.write_bytes(good)
                modified = json.loads(saved)
                modified["manual_input_proof"] = True
                (folder / "packet.json").write_text(json.dumps(modified))
                self.assertFalse(invoke("before", fixtures.complete_log(packet, stop_before=True))["passed"])


if __name__ == "__main__":
    unittest.main()
