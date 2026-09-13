"""Offline movement host boundaries; native calls are replaced by explicit fakes.

These fixtures never launch a game/debugger/desktop or claim runtime evidence.
An optional real read-only producer dry run is run separately with owned inputs.
"""
import hashlib
import ctypes
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / 'scripts/cdb/run_complete_hd_army_movement_capture.ps1'
PS = Path('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')

PRELUDE = r'''
param([string]$HostPath,[string]$FixtureRoot,[string]$Mode)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($HostPath,[ref]$tokens,[ref]$errors)
if ($errors.Count) {throw ($errors | Out-String)}
$script:RepoRoot=[IO.Path]::GetFullPath((Join-Path (Split-Path $HostPath) '..\..'))
function Import-Function {
 param([string]$Name)
 $nodes=@($ast.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $Name},$true))
 if ($nodes.Count -ne 1) {throw ('missing unique function: '+$Name)}
 . ([scriptblock]::Create($nodes[0].Extent.Text.Replace(('function '+$Name+' {'),('function global:'+$Name+' {'))))
}
function Assert-Case {param([bool]$Value);if (-not $Value) {throw 'fixture assertion failed'}}
'''

DRY_RUN = r'''
Import-Function Invoke-MovementCapture
function Start-CanvasHidden {throw 'native launch must not run'}
function New-Item {throw 'dry run must not create files'}
$result=Invoke-MovementCapture @{plan=@{out_dir=$FixtureRoot};packet=@{fixture='synthetic'}}
Assert-Case ($result.status -ceq 'dry_run' -and $result.executed -is [bool] -and -not $result.executed)
@{passed=$true} | ConvertTo-Json
'''

PATHS = r'''
Import-Function Resolve-CanvasPath
$new=Join-Path $FixtureRoot 'absent\nested'
$accepted=@(@{name='ordinary child';path=$new},@{name='dot component';path=($FixtureRoot+'\absent\.\nested')})
foreach ($case in $accepted) {
 # The contract returns .NET's canonical spelling, which need not preserve
 # the caller's short-name, separator or dot-component spelling.
 $expected=[IO.Path]::GetFullPath($case.path).TrimEnd('\')
 try {$actual=Resolve-CanvasPath $case.path -Root $FixtureRoot -Kind new}
 catch {throw ("Path validation failed for {0}: input=[{1}], expected=[{2}], root=[{3}], canonical_root=[{4}]: {5}" -f $case.name,$case.path,$expected,$FixtureRoot,[IO.Path]::GetFullPath($FixtureRoot),$_.Exception.Message)}
 if ($actual -cne $expected) {throw ("Canonical path mismatch for {0}: input=[{1}], expected=[{2}], actual=[{3}], root=[{4}]" -f $case.name,$case.path,$expected,$actual,$FixtureRoot)}
}
$bad=@(@{name='existing root';path=$FixtureRoot},@{name='parent traversal';path=(Join-Path $FixtureRoot '..\escape')},
 @{name='prefix sibling';path=($FixtureRoot+'-sibling\new')},@{name='command delimiter';path=($new+';q')},
 @{name='alternate stream';path=($new+':stream')},@{name='relative path';path='relative\new'})
foreach ($case in $bad) {
 $failed=$false;try {$null=Resolve-CanvasPath $case.path -Root $FixtureRoot -Kind new} catch {$failed=$true}
 if (-not $failed) {throw ("Unsafe path unexpectedly accepted for {0}: input=[{1}], root=[{2}]" -f $case.name,$case.path,$FixtureRoot)}
}
if (Test-Path -LiteralPath $new) {throw ('Read-only path validation created an artifact: '+$new)}
@{passed=$true;accepted=$accepted.Count;rejected=$bad.Count;mode=$Mode} | ConvertTo-Json
'''

DRIFT = r'''
foreach ($name in @('Resolve-CanvasPath','Get-CanvasHash','Get-MovementAssets','Assert-MovementFiles')) {Import-Function $name}
$work=Join-Path $FixtureRoot 'work';[void](New-Item -ItemType Directory -Path $work)
$source=Join-Path $FixtureRoot 'source.txt';$asset=Join-Path $work 'asset.txt'
[IO.File]::WriteAllText($source,'source');[IO.File]::WriteAllText($asset,'asset')
$plan=@{identities=@(@{path=$source;sha256=(Get-CanvasHash $source)});work_dir=$work;assets_before=(Get-MovementAssets $work)}
Assert-MovementFiles $plan
if ($Mode -eq 'source') {[IO.File]::WriteAllText($source,'drift')}
elseif ($Mode -eq 'asset') {[IO.File]::WriteAllText($asset,'drift')}
elseif ($Mode -eq 'added') {[IO.File]::WriteAllText((Join-Path $work 'extra.txt'),'extra')}
elseif ($Mode -eq 'missing') {[IO.File]::Delete($asset)}
else {throw 'unknown fixture'}
$failed=$false;try {Assert-MovementFiles $plan} catch {$failed=$true}
Assert-Case $failed
@{passed=$true} | ConvertTo-Json
'''

READY = r'''
Import-Function Test-MovementReady
foreach ($text in @('WMOV_HOST_READY','prefix WMOV_HOST_READY'+"`n",'SURFDUMP_HOST_READY'+"`n",' WMOV_HOST_READY'+"`n",'WMOV_HOST_READY extra'+"`n",'WMOV_BASE_HOST_READY'+"`n",'SHSEL_HOST_READY'+"`n")) {
 Assert-Case (-not (Test-MovementReady $text))
}
Assert-Case (Test-MovementReady ("prefix`r`nWMOV_HOST_READY`r`n"))
@{passed=$true} | ConvertTo-Json
'''

SURFACE = r'''
Import-Function Assert-MovementSurface
$plan=[IO.File]::ReadAllText((Join-Path $FixtureRoot 'plan.json')) | ConvertFrom-Json
$report=[IO.File]::ReadAllText((Join-Path $FixtureRoot 'report.json')) | ConvertFrom-Json
foreach ($name in @('Resolve-CanvasPath','Get-CanvasHash')) {Import-Function $name}
if ($Mode -eq 'normal') {$null=Assert-MovementSurface $report $plan}
else {
 switch ($Mode) {
  'notbound' {$report.source_authenticated=$false}
  'truthy' {$report.ready_for_host_capture='true'}
  'initial' {$report.initial_map_trace.passed=$false}
  'sequence' {$report.movement_sequence.passed=$false}
  'projected' {$report.initial_log_projected=$true}
  'source' {$report.source.source_sha256.'tools/complete_hd_army_movement_trace.py'='0'*64}
  'probe' {$report.source.probe_raw_sha256='0'*64}
  'candidate' {$report.source.candidate_sha256='0'*64}
  'width' {$report.surface.width=1920}
  'vtable' {$report.surface.vtable=0}
  'wrap' {$report.surface.base=4294967290L}
  'headerwrap' {$report.surface.surface=4294967290L}
  'static' {$report.surface.surface=0x51d4c0}
  'type' {$report.surface.base='2097152'}
  'selected' {$report.movement_sequence.ready.selected=4}
  'stop' {$report.surface.eip=0x406fa0}
  'headers-unbound' {$report.snapshot_headers_verified=$false}
  'units-unbound' {$report.snapshot_units_verified=$false}
  'commands-unbound' {$report.all_supplemental_commands_bound=$false}
  'state' {$report.movement_state.passed=$false}
  'unitwrap' {$report.movement_sequence.ready.unit=4294967290L}
  'ap' {$report.movement_sequence.ready.ap7=16}
  'occupancy' {$report.movement_sequence.ready.occ2=65535}
  'destination' {$report.movement_sequence.ready.x=16}
  'steps' {$report.movement_sequence.ready.steps=1}
  'queue' {$report.movement_sequence.ready.path_count=1}
  'thread' {$report.movement_sequence.ready.tid=99}
  'command-hash' {$report.source.supplemental_commands.'C:/ClashCaptures/synthetic/movement-checkpoint-1.cdb'.raw_sha256='0'*64}
  default {throw 'unknown fixture'}
 }
 $failed=$false;try {$null=Assert-MovementSurface $report $plan} catch {$failed=$true}
 Assert-Case $failed
}
@{passed=$true} | ConvertTo-Json
'''

CAPTURE = r'''
foreach ($name in @('Save-MovementSnapshot','Get-CanvasHash','Get-CanvasBytesHash')) {Import-Function $name}
$script:Header=New-Object byte[] 188
[BitConverter]::GetBytes([uint16]800).CopyTo($script:Header,0);[BitConverter]::GetBytes([uint16]600).CopyTo($script:Header,2)
[BitConverter]::GetBytes([uint32]0x200000).CopyTo($script:Header,4);[BitConverter]::GetBytes([uint32]0x50ee24).CopyTo($script:Header,184)
$script:Unit=New-Object byte[] 725;$script:Unit[0]=18;$script:Unit[2]=19
$script:Reads=0
function Read-CanvasMemory {
 param($Handle,$Address,$Count)
 $script:Reads++
 $data=New-Object byte[] $Count
 if ($Count -eq 4) {
  [BitConverter]::GetBytes([uint32]0x100000).CopyTo($data,0)
  if ($Mode -eq 'e0' -and $script:Reads -gt 4) {$data[0]=1}
 }
 elseif ($Count -eq 188) {
  $script:Header.CopyTo($data,0)
  if ($Mode -eq 'header' -and $script:Reads -gt 4) {$data[20]=1}
  if ($Mode -eq 'vtable') {$data[184]=0}
 } elseif ($Count -eq 725) {
  $script:Unit.CopyTo($data,0)
  if ($Mode -eq 'unit' -and $script:Reads -gt 4) {$data[100]=1}
 } else {$data[0]=1;$data[-1]=2}
 return ,$data
}
$surface=@{surface=0x100000;base=0x200000;width=800;height=600}
$evidence=@{surface=$surface;ready=@{unit=0x300000};header_sha256=(Get-CanvasBytesHash $script:Header);unit_sha256=(Get-CanvasBytesHash $script:Unit)}
$failed=$false
try {$result=Save-MovementSnapshot @{handle=123;identity=@{fixture='synthetic'}} $evidence (Join-Path $FixtureRoot 'surface.raw') @{width=800;height=600}}
catch {$failed=$true}
Assert-Case ($failed -eq ($Mode -ne 'normal'))
if ($Mode -eq 'normal') {
 Assert-Case ($script:Reads -eq 7 -and $result.bytes -eq 480000 -and $result.reads.before.header.bytes -eq 188 -and $result.reads.before.unit.bytes -eq 725 -and $result.unit_reads -eq 2)
 foreach ($phase in @('before','after')) {foreach ($name in @('e0','header','unit')) {
  $expected=Join-Path $FixtureRoot ('surface-'+$phase+'-'+$name+'.raw')
  Assert-Case ($result.reads[$phase][$name].path -ceq $expected -and (Test-Path -LiteralPath $expected))
 }}
 Assert-Case (@(Get-ChildItem -LiteralPath $FixtureRoot -Filter 'surface.-*').Count -eq 0)
}
@{passed=$true} | ConvertTo-Json
'''

TRIPLET = r'''
Import-Function Save-MovementTriplet
$script:Count=0
function Save-MovementSnapshot {
 param($OwnedGame,$Surface,$RawPath,$Plan)
 $script:Count++;[IO.File]::WriteAllBytes($RawPath,[byte[]](1,2,3))
 $pixel=if ($Mode -eq 'pixels' -and $script:Count -eq 2) {'changed'} else {'same'}
 $header=if ($Mode -eq 'header' -and $script:Count -eq 3) {'changed'} else {'same'}
 $unit=if ($Mode -eq 'unit' -and $script:Count -eq 3) {'changed'} else {'same'}
 return @{path=$RawPath;sha256=$pixel;reads=@{before=@{e0=@{sha256='e0'};header=@{sha256=$header};unit=@{sha256=$unit}}}}
}
$result=Save-MovementTriplet @{handle=123} @{} @{out_dir=$FixtureRoot}
Assert-Case ($script:Count -eq 3 -and $result.snapshots.Count -eq 3)
Assert-Case ($result.clean_stable_pair -eq ($Mode -eq 'normal'))
foreach ($index in 1..3) {Assert-Case (Test-Path -LiteralPath (Join-Path $FixtureRoot ('capture-'+$index+'\surface.raw')))}
@{passed=$true} | ConvertTo-Json
'''

CLEANUP = r'''
foreach ($name in @('Stop-CanvasOwned','Test-MovementCleanup')) {Import-Function $name}
Add-Type @'
using System;using System.Collections.Generic;
public class CanvasScreenNative {
 public static List<string> Calls=new List<string>();public static string Mode="normal";static int count;
 public static uint WaitForSingleObject(IntPtr h,uint timeout){Calls.Add("wait:"+h+":"+timeout);count++;return Mode=="failure"?258u:(count==1&&Mode!="exited"?258u:0u);}
 public static bool TerminateProcess(IntPtr h,uint exit){Calls.Add("terminate:"+h);return true;}
 public static bool CloseHandle(IntPtr h){Calls.Add("close:"+h);return true;}
}
'@
[CanvasScreenNative]::Mode=$Mode
$result=Stop-CanvasOwned @{handle=[IntPtr]123;identity=@{process_id=77;fixture='synthetic'}}
Assert-Case ($result.absent -eq ($Mode -ne 'failure') -and $result.handle_closed)
Assert-Case ([CanvasScreenNative]::Calls[-1] -ceq 'close:123')
$cleanup=@{cdb=$result;candidates=@(@{absent=$true;handle_closed=$true});desktop_closed=$true}
Assert-Case ((Test-MovementCleanup $cleanup) -eq ($Mode -ne 'failure'))
foreach ($bad in @('true',1,$false,$null)) {
 $cleanup=@{cdb=@{absent=$true;handle_closed=$true};candidates=@(@{absent=$true;handle_closed=$true});desktop_closed=$bad}
 Assert-Case (-not (Test-MovementCleanup $cleanup))
 $cleanup.desktop_closed=$true;$cleanup.candidates[0].absent=$bad
 Assert-Case (-not (Test-MovementCleanup $cleanup))
}
@{passed=$true} | ConvertTo-Json
'''

PERSISTENCE = r'''
foreach ($name in @('Invoke-MovementCapture','Test-MovementCleanup','Save-MovementFinalTrace')) {Import-Function $name}
function Assert-MovementFiles {}
function Assert-MovementCommands {}
function Resolve-CanvasPath {param($Path,$Root,$Kind);return $Path}
function Get-CanvasHash {return 'fixture-hash'}
function Get-MovementAssets {return @{}}
function Write-CanvasJson {
 param($Path,$Value)
 if ([IO.Path]::GetFileName($Path) -eq 'summary.json') {throw 'injected receipt write failure'}
 [IO.File]::WriteAllText($Path,($Value | ConvertTo-Json -Depth 20))
}
function Invoke-CanvasPythonJson {return $script:Packet}
function Start-CanvasHidden {
 param($Plan,$Probe,$Log,$Launch)
 $Launch.session=@{handle=123;identity=@{process_id=77;fixture='synthetic'};desktop_name='synthetic';command_line='synthetic'}
 throw 'injected post-launch identity failure'
}
function Find-CanvasOwnedChildren {
 param($Plan,$Session,$Started,$Owned)
 $Owned['88']=@{handle=456;identity=@{process_id=88;fixture='synthetic'}}
}
function Stop-CanvasOwned {param($Owned);return @{identity=$Owned.identity;absent=$true;handle_closed=$true;termination_requested=$true}}
function Close-CanvasDesktop {return $true}
$input=Join-Path $FixtureRoot 'input.fixture';[IO.File]::WriteAllText($input,'fixture bytes')
$directory=Join-Path $FixtureRoot 'candidate';$out=Join-Path $FixtureRoot 'out'
$script:Packet=@{compiled_probe='synthetic probe';initial_extra='synthetic initial'}
$plan=@{out_dir=$out;candidate_dir=$directory;input_candidate=$input;candidate_path=(Join-Path $directory 'candidate.fixture');candidate_sha256='fixture-hash'
 proxy_input=$input;proxy_path=(Join-Path $directory 'proxy.fixture');proxy_sha256='fixture-hash';host_path=$input;probe_sha256='fixture-hash'
 producer='synthetic';original=$input;save=$input;candidate_manifest=$input;resolution='800x600';work_dir=$FixtureRoot;python='unused'}
$result=Invoke-MovementCapture @{plan=$plan;packet=$script:Packet} -DoExecute
Assert-Case ($result.executed -is [bool] -and $result.executed -and -not $result.passed -and $result.status -ceq 'failed')
Assert-Case ($result.cleanup_verified -and $result.cdb.process_id -eq 77)
Assert-Case (@($result.failures | Where-Object {$_ -like '*Final summary persistence failed:*injected receipt write failure*'}).Count -eq 1)
Assert-Case (@($result.failures | Where-Object {$_ -eq 'injected post-launch identity failure'}).Count -eq 1)
@{passed=$true;synthetic_fixture_only=$true} | ConvertTo-Json
'''

LOG_BOUND = r'''
foreach ($name in @('Read-CanvasLog','Read-CanvasLogBytes')) {Import-Function $name}
$path=Join-Path $FixtureRoot 'synthetic.log'
[IO.File]::WriteAllText($path,"WMOV_HOST_READY`r`n")
Assert-Case ((Read-CanvasLog $path) -ceq "WMOV_HOST_READY`r`n")
$file=[IO.File]::OpenWrite($path);try {$file.SetLength(16777217)} finally {$file.Dispose()}
foreach ($name in @('Read-CanvasLog','Read-CanvasLogBytes')) {
 $failed=$false;try {$null=& $name $path} catch {$failed=$true}
 Assert-Case $failed
}
@{passed=$true} | ConvertTo-Json
'''

COMMANDS = r'''
foreach ($name in @('Get-MovementCommands','Assert-MovementCommands','Get-CanvasBytesHash','Get-CanvasHash','Resolve-CanvasPath')) {Import-Function $name}
$commands=[ordered]@{};$hashes=[ordered]@{}
foreach ($index in 0..2) {
 $key=(Join-Path $FixtureRoot ('movement-checkpoint-'+$index+'.cdb')).Replace('\','/')
 $commands[$key]="synthetic command $index`n";$hashes[$key]=Get-CanvasBytesHash ([Text.Encoding]::ASCII.GetBytes($commands[$key]))
}
$packet=@{supplemental_commands=$commands;supplemental_sha256=$hashes} | ConvertTo-Json -Depth 10 | ConvertFrom-Json
$key=@($packet.supplemental_commands.PSObject.Properties)[1].Name
switch ($Mode) {
 'missing' {$packet.supplemental_commands.PSObject.Properties.Remove($key)}
 'extra' {$packet.supplemental_commands | Add-Member NoteProperty 'C:/outside.cdb' 'unplanned'}
 'path' {$packet.supplemental_commands.PSObject.Properties.Remove($key);$packet.supplemental_commands | Add-Member NoteProperty ($key+'.other') 'wrong path'}
 'hash' {$packet.supplemental_sha256.$key='0'*64}
 'unicode' {$packet.supplemental_commands.$key+=[char]233}
}
$failed=$false
try {
 $rows=@(Get-MovementCommands $packet $FixtureRoot)
 Assert-Case ($rows.Count -eq 3)
 foreach ($row in $rows) {
  [IO.File]::WriteAllText($row.path,$packet.supplemental_commands.($row.packet_path),[Text.UTF8Encoding]::new($false))
 }
 $plan=@{out_dir=$FixtureRoot;supplemental_commands=$rows}
 Assert-MovementCommands $plan
 if ($Mode -eq 'file-drift') {[IO.File]::WriteAllText($rows[1].path,'changed')}
 if ($Mode -eq 'file-missing') {[IO.File]::Delete($rows[1].path)}
 Assert-MovementCommands $plan
} catch {$failed=$true}
if ($failed -ne ($Mode -ne 'normal')) {throw ('Supplemental boundary expectation differs for '+$Mode)}
@{passed=$true} | ConvertTo-Json
'''

CHECKPOINTS = r'''
foreach ($name in @('Get-MovementCheckpoints','Get-CanvasHash','Resolve-CanvasPath')) {Import-Function $name}
$plan=@{out_dir=$FixtureRoot;width=800;height=600}
$report=@{snapshots=@();source=@{snapshot_headers=@();snapshot_units=@()}}
$names=@('movement-before','movement-preview','movement-after')
foreach ($index in 0..2) {
 $report.snapshots+=@{checkpoint=$index}
 foreach ($kind in @('raw','header','unit')) {
  $suffix=if ($kind -eq 'raw') {'.raw'} else {'.'+$kind+'.raw'}
  $size=if ($kind -eq 'header') {188} elseif ($kind -eq 'unit') {725} else {480000}
  $path=Join-Path $FixtureRoot ($names[$index]+$suffix)
  [IO.File]::WriteAllBytes($path,(New-Object byte[] $size))
  if ($kind -ne 'raw') {$report.source[('snapshot_'+$kind+'s')]+=@{path=$path;sha256=(Get-CanvasHash $path);bytes=$size;checkpoint=$index}}
 }
}
$baseline=@(Get-MovementCheckpoints $plan $report)
Assert-Case ($baseline.Count -eq 3 -and $baseline[2].unit.bytes -eq 725 -and $baseline[2].header.bytes -eq 188 -and $baseline[2].raw.bytes -eq 480000)
if ($Mode -match '^(raw|header|unit)-(missing|truncated)$') {
 $kind=$Matches[1];$mutation=$Matches[2];$path=$baseline[1][$kind].path
 if ($mutation -eq 'missing') {[IO.File]::Delete($path)}
 else {[IO.File]::WriteAllBytes($path,(New-Object byte[] ($baseline[1][$kind].bytes-1)))}
} elseif ($Mode -eq 'unit-hash') {$report.source.snapshot_units[1].sha256='0'*64}
elseif ($Mode -eq 'header-hash') {$report.source.snapshot_headers[1].sha256='0'*64}
elseif ($Mode -eq 'header-path') {$report.source.snapshot_headers[1].path=$report.source.snapshot_headers[0].path}
elseif ($Mode -eq 'order') {$report.snapshots[1].checkpoint=0}
$failed=$false;try {$null=Get-MovementCheckpoints $plan $report} catch {$failed=$true}
if ($failed -ne ($Mode -ne 'normal')) {throw ('Checkpoint boundary expectation differs for '+$Mode)}
@{passed=$true} | ConvertTo-Json
'''

FINAL_TRACE = r'''
foreach ($name in @('Save-MovementFinalTrace','Read-CanvasLogBytes','Get-CanvasBytesHash','Write-CanvasJson')) {Import-Function $name}
$log=Join-Path $FixtureRoot 'cdb.log';$script:TraceCalls=0
if ($Mode -ne 'missing-log') {[IO.File]::WriteAllText($log,"synthetic WMOV_REJECT native_contract`n")}
function Invoke-MovementTrace {
 param($Plan,$Log,$Packet,$Probe)
 $script:TraceCalls++
 if ($Mode -eq 'timeout') {throw 'injected bounded validator timeout'}
 $hash=Get-CanvasBytesHash ([IO.File]::ReadAllBytes($Log))
 if ($Mode -eq 'drift') {[IO.File]::AppendAllText($Log,'changed after parser read')}
 return @{passed=$false;ready_for_host_capture=$false;source=@{log_raw_sha256=$hash};failures=@('synthetic native rejection')}
}
if ($Mode -eq 'write-failure') {function Write-CanvasJson {throw 'injected trace persistence failure'}}
$result=Save-MovementFinalTrace @{out_dir=$FixtureRoot} $log 'unused-packet' 'unused-probe'
if ($Mode -eq 'missing-log') {
 Assert-Case (-not $result.attempted -and $script:TraceCalls -eq 0 -and $null -eq $result.trace -and $null -eq $result.log)
} else {
 Assert-Case ($result.attempted -and $script:TraceCalls -eq 1 -and $null -ne $result.log -and -not $result.log.capture_prefix_preserved)
 Assert-Case ($result.log.sha256 -ceq (Get-CanvasBytesHash ([IO.File]::ReadAllBytes($log))))
 if ($Mode -eq 'timeout') {Assert-Case ($null -eq $result.trace -and $result.log.unchanged_during_final_validation -and -not $result.log.validator_log_identity_matched)}
 else {
  Assert-Case ($result.trace.passed -is [bool] -and -not $result.trace.passed -and -not $result.trace.ready_for_host_capture)
  Assert-Case ($result.trace.failures[0] -ceq 'synthetic native rejection')
  Assert-Case ($result.log.unchanged_during_final_validation -eq ($Mode -ne 'drift'))
  Assert-Case ($result.log.validator_log_identity_matched -eq ($Mode -ne 'drift'))
 }
}
Assert-Case (($result.failures.Count -eq 0) -eq ($Mode -eq 'normal'))
if ($Mode -eq 'normal') {Assert-Case (Test-Path -LiteralPath (Join-Path $FixtureRoot 'trace-final.json'))}
@{passed=$true} | ConvertTo-Json
'''

EARLY_FAILURE_TRACE = r'''
foreach ($name in @('Invoke-MovementCapture','Test-MovementCleanup','Save-MovementFinalTrace','Read-CanvasLogBytes','Get-CanvasBytesHash','Test-MovementReady')) {Import-Function $name}
$script:Calls=New-Object 'Collections.Generic.List[string]';$script:TraceCalls=0;$script:PixelCalls=0;$script:SurfaceCalls=0
function Assert-MovementFiles {}
function Assert-MovementCommands {}
function Resolve-CanvasPath {param($Path,$Root,$Kind);return $Path}
function Get-CanvasHash {return 'fixture-hash'}
function Get-MovementAssets {return @{}}
function Write-CanvasJson {
 param($Path,$Value)
 if ($Mode -eq 'write-failure' -and [IO.Path]::GetFileName($Path) -eq 'trace-final.json') {throw 'injected trace persistence failure'}
 [IO.File]::WriteAllText($Path,($Value | ConvertTo-Json -Depth 30))
}
function Invoke-CanvasPythonJson {return $script:Packet}
function Start-CanvasHidden {
 param($Plan,$Probe,$Log,$Launch)
 $Launch.session=@{handle=123;identity=@{process_id=77;fixture='synthetic'};desktop_name='synthetic';command_line='synthetic'}
 [IO.File]::WriteAllText($Log,"synthetic WMOV_REJECT native_contract`n")
 return $Launch.session
}
function Find-CanvasOwnedChildren {param($Plan,$Session,$Started,$Owned);$Owned['88']=@{handle=456;identity=@{process_id=88;fixture='synthetic'}}}
function Read-CanvasLog {param($Path);return [IO.File]::ReadAllText($Path)}
function Test-CanvasProcessExited {return $true}
function Stop-CanvasOwned {
 param($Owned);$script:Calls.Add(('stop-'+$Owned.identity.process_id))
 return @{identity=$Owned.identity;absent=$true;handle_closed=$true;termination_requested=$true}
}
function Close-CanvasDesktop {$script:Calls.Add('desktop-closed');return $true}
function Assert-MovementSurface {$script:SurfaceCalls++;throw 'no snapshot must not authorize acceptance'}
function Save-MovementTriplet {$script:PixelCalls++;throw 'native rejection must not read pixels'}
function Invoke-MovementTrace {
 param($Plan,$Log,$Packet,$Probe)
 Assert-Case ($script:Calls[-1] -ceq 'desktop-closed')
 $script:TraceCalls++;$script:Calls.Add('final-trace')
 if ($Mode -eq 'timeout') {throw 'injected bounded validator timeout'}
 return @{passed=($Mode -eq 'optimistic-trace');ready_for_host_capture=($Mode -eq 'optimistic-trace')
  source=@{log_raw_sha256=(Get-CanvasBytesHash ([IO.File]::ReadAllBytes($Log)))};failures=@('synthetic native rejection')}
}
$input=Join-Path $FixtureRoot 'input.fixture';[IO.File]::WriteAllText($input,'fixture bytes')
$directory=Join-Path $FixtureRoot 'candidate';$out=Join-Path $FixtureRoot 'out'
$script:Packet=@{compiled_probe='synthetic probe';initial_extra='synthetic initial'}
$plan=@{out_dir=$out;candidate_dir=$directory;input_candidate=$input;candidate_path=(Join-Path $directory 'candidate.fixture');candidate_sha256='fixture-hash'
 proxy_input=$input;proxy_path=(Join-Path $directory 'proxy.fixture');proxy_sha256='fixture-hash';host_path=$input;probe_sha256='fixture-hash'
 producer='synthetic';original=$input;save=$input;candidate_manifest=$input;resolution='800x600';work_dir=$FixtureRoot;python='unused';deadline_seconds=300}
$result=Invoke-MovementCapture @{plan=$plan;packet=$script:Packet} -DoExecute
Assert-Case ($result.executed -and -not $result.passed -and $result.status -ceq 'failed' -and $result.cleanup_verified)
Assert-Case ($result.final_trace_attempted -and $script:TraceCalls -eq 1 -and $script:PixelCalls -eq 0 -and $script:SurfaceCalls -eq 0)
Assert-Case ($null -eq $result.snapshot -and $null -eq $result.png -and -not $result.final_log.capture_prefix_preserved)
Assert-Case (($script:Calls -join ',') -ceq 'stop-77,stop-88,desktop-closed,final-trace')
Assert-Case (@($result.failures | Where-Object {$_ -ceq 'Debugger exited before validated movement readiness.'}).Count -eq 1)
if ($Mode -eq 'normal') {Assert-Case ($null -ne $result.final_trace -and -not $result.final_trace.passed -and (Test-Path -LiteralPath (Join-Path $out 'trace-final.json')))}
if ($Mode -eq 'timeout') {Assert-Case ($null -eq $result.final_trace -and $result.final_log.unchanged_during_final_validation)}
if ($Mode -eq 'write-failure') {Assert-Case ($null -ne $result.final_trace -and -not (Test-Path -LiteralPath (Join-Path $out 'trace-final.json')))}
@{passed=$true;synthetic_fixture_only=$true} | ConvertTo-Json
'''


def synthetic_surface_fixture():
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    source = 'tools/complete_hd_army_movement_trace.py'
    plan = dict(stage='synthetic-stage', resolution='800x600', width=800, height=600,
                original_sha256='1'*64, candidate_sha256='2'*64, save_sha256='3'*64,
                probe_sha256='4'*64, candidate_manifest_canonical_sha256='5'*64,
                identities=[dict(path=str(ROOT/source), sha256=sha(ROOT/source))])
    report = dict(schema='clash95_complete_hd_army_movement_trace_v1', stage=plan['stage'],
                  resolution=plan['resolution'], passed=True, ready_for_host_capture=True,
                  source_authenticated=True, whole_candidate_bound=True, candidate_manifest_bound=True,
                  all_supplemental_commands_bound=True,snapshot_headers_verified=True,snapshot_units_verified=True,
                  sequence_only=False, initial_log_projected=False, initial_map_trace=dict(passed=True),
                  movement_sequence=dict(passed=True,ready=dict(kind='ready',click=2,phase=59,tid=123,eip=0x406fa1,esp=0x100000,
                      selected=3,prior=3,lower=1,unit=0x300000,x=18,y=19,steps=2,path_count=0,occ0=65535,occ1=65535,occ2=3,
                      **{'ap'+str(i):v for i,v in enumerate((16,12,6,6,6,6,6,6))})),movement_state=dict(passed=True),
                  surface=dict(checkpoint=2,tid=123,eip=0x406fa1,esp=0x100000,surface=0x100000,
                               base=0x200000,width=800,height=600,vtable=0x50ee24))
    report['source']={key:plan[key] for key in ('original_sha256','candidate_sha256','save_sha256','candidate_manifest_canonical_sha256')}
    report['source'].update(probe_raw_sha256=plan['probe_sha256'],log_raw_sha256='6'*64,
                            source_sha256={source:sha(ROOT/source)})
    plan['supplemental_commands']=[dict(path=f'C:/ClashCaptures/synthetic/movement-checkpoint-{i}.cdb',
        packet_path=f'C:/ClashCaptures/synthetic/movement-checkpoint-{i}.cdb',sha256='7'*64,bytes=10,checkpoint=i) for i in range(3)]
    report['source']['supplemental_commands']={row['packet_path']:dict(raw_sha256=row['sha256'],
        canonical_lf_sha256=row['sha256'],bytes=row['bytes']) for row in plan['supplemental_commands']}
    report['snapshots']=[dict(checkpoint=i) for i in range(3)]
    report['source']['snapshot_headers']=[dict(checkpoint=i,surface=0x100000,bytes=188,sha256='8'*64) for i in range(3)]
    report['source']['snapshot_units']=[dict(checkpoint=i,unit=0x300000,bytes=725,sha256='9'*64) for i in range(3)]
    return plan, report


@unittest.skipUnless(os.name == 'nt' and PS.is_file(), 'Windows PowerShell required')
class HostBoundaryTests(unittest.TestCase):
    def run_ps(self, body, mode='normal'):
        with tempfile.TemporaryDirectory(prefix='complete-movement-host-fixture-') as directory:
            root=Path(directory).resolve(strict=True);directory=str(root)
            plan,report=synthetic_surface_fixture()
            (root/'plan.json').write_text(json.dumps(plan),encoding='utf-8')
            (root/'report.json').write_text(json.dumps(report),encoding='utf-8')
            script=root/'fixture.ps1';script.write_text(PRELUDE+body,encoding='utf-8-sig')
            fixture_root=directory
            if mode == 'canonicalized-short-root':
                # Production roots are fixed long paths. Resolve an existing
                # temporary short alias back to its long spelling before using
                # it as the containment root: mixed alias acceptance is not a
                # production promise, and must not be added by this fixture.
                kernel=ctypes.WinDLL('kernel32',use_last_error=True)
                short_path=kernel.GetShortPathNameW
                short_path.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint32]
                short_path.restype=ctypes.c_uint32
                size=short_path(directory,None,0)
                if not size:
                    raise ctypes.WinError(ctypes.get_last_error())
                buffer=ctypes.create_unicode_buffer(size)
                written=short_path(directory,buffer,size)
                if not written or written >= size:
                    raise OSError('Could not obtain a complete short fixture-root path')
                fixture_root=str(Path(buffer.value).resolve(strict=True))
                self.assertTrue(os.path.samefile(fixture_root,directory),
                                'Canonical fixture root must identify the original existing directory')
            result=subprocess.run([str(PS),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),
                '-HostPath',str(HOST),'-FixtureRoot',fixture_root,'-Mode',mode],capture_output=True,
                text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            return json.loads(result.stdout)

    def test_dry_run_invocation_creates_nothing_and_never_calls_native_launch(self):
        self.assertTrue(self.run_ps(DRY_RUN)['passed'])

    def test_paths_reject_existing_sibling_traversal_stream_and_delimiter(self):
        for mode in ('normal','canonicalized-short-root'):
            with self.subTest(mode=mode):
                result=self.run_ps(PATHS,mode)
                self.assertTrue(result['passed'])
                self.assertEqual(result['accepted'],2)
                self.assertEqual(result['rejected'],6)

    def test_source_asset_missing_and_added_inventory_changes_fail(self):
        for mode in ('source','asset','added','missing'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(DRIFT,mode)['passed'])

    def test_only_exact_complete_ready_line_with_newline_triggers_validation(self):
        self.assertTrue(self.run_ps(READY)['passed'])

    def test_full_bound_readiness_rejects_false_truthy_stale_and_bad_memory_fields(self):
        for mode in ('normal','notbound','truthy','initial','sequence','projected','source','probe',
                     'candidate','width','vtable','wrap','headerwrap','static','type','selected','stop',
                     'headers-unbound','units-unbound','commands-unbound','state','unitwrap','ap',
                     'occupancy','destination','steps','queue','thread','command-hash'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(SURFACE,mode)['passed'])

    def test_memory_capture_pair_header_contract_and_exact_artifact_names(self):
        for mode in ('normal','header','vtable','unit','e0'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(CAPTURE,mode)['passed'])

    def test_triplet_retains_all_reads_on_pixel_or_header_difference(self):
        for mode in ('normal','pixels','header','unit'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(TRIPLET,mode)['passed'])

    def test_retained_handle_cleanup_and_exact_bool_evidence(self):
        for mode in ('normal','exited','failure'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(CLEANUP,mode)['passed'])

    def test_failed_summary_write_preserves_executed_truth_and_owned_cleanup(self):
        self.assertTrue(self.run_ps(PERSISTENCE)['passed'])

    def test_log_byte_limit_also_applies_before_ready_polling(self):
        self.assertTrue(self.run_ps(LOG_BOUND)['passed'])

    def test_all_three_exact_supplemental_commands_and_actual_file_drift(self):
        for mode in ('normal','missing','extra','path','hash','unicode','file-drift','file-missing'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(COMMANDS,mode)['passed'])

    def test_all_native_checkpoint_raw_header_and_unit_files_are_required_and_bound(self):
        for mode in ('normal','raw-missing','header-missing','unit-missing','raw-truncated',
                     'header-truncated','unit-truncated','unit-hash','header-hash','header-path','order'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(CHECKPOINTS,mode)['passed'])

    def test_final_strict_failure_trace_retains_log_identity_on_timeout_write_failure_and_drift(self):
        for mode in ('normal','missing-log','timeout','write-failure','drift'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(FINAL_TRACE,mode)['passed'])

    def test_early_native_failure_parses_once_after_cleanup_and_cannot_authorize_capture(self):
        for mode in ('normal','timeout','write-failure','optimistic-trace'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(EARLY_FAILURE_TRACE,mode)['passed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
