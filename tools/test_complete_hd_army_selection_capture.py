"""Offline selection host boundaries; native calls are replaced by explicit fakes.

These fixtures never launch a game/debugger/desktop or claim runtime evidence.
An optional real read-only producer dry run is run separately with owned inputs.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / 'scripts/cdb/run_complete_hd_army_selection_capture.ps1'
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
Import-Function Invoke-SelectionCapture
function Start-CanvasHidden {throw 'native launch must not run'}
function New-Item {throw 'dry run must not create files'}
$result=Invoke-SelectionCapture @{plan=@{out_dir=$FixtureRoot};packet=@{fixture='synthetic'}}
Assert-Case ($result.status -ceq 'dry_run' -and $result.executed -is [bool] -and -not $result.executed)
@{passed=$true} | ConvertTo-Json
'''

PATHS = r'''
Import-Function Resolve-CanvasPath
$new=Join-Path $FixtureRoot 'absent\nested'
Assert-Case ((Resolve-CanvasPath $new -Root $FixtureRoot -Kind new) -ceq $new)
$bad=@($FixtureRoot,(Join-Path $FixtureRoot '..\escape'),($FixtureRoot+'-sibling\new'),($new+';q'),($new+':stream'),('relative\new'))
foreach ($path in $bad) {
 $failed=$false;try {$null=Resolve-CanvasPath $path -Root $FixtureRoot -Kind new} catch {$failed=$true}
 Assert-Case $failed
}
Assert-Case (-not (Test-Path -LiteralPath $new))
@{passed=$true;rejected=$bad.Count} | ConvertTo-Json
'''

DRIFT = r'''
foreach ($name in @('Resolve-CanvasPath','Get-CanvasHash','Get-SelectionAssets','Assert-SelectionFiles')) {Import-Function $name}
$work=Join-Path $FixtureRoot 'work';[void](New-Item -ItemType Directory -Path $work)
$source=Join-Path $FixtureRoot 'source.txt';$asset=Join-Path $work 'asset.txt'
[IO.File]::WriteAllText($source,'source');[IO.File]::WriteAllText($asset,'asset')
$plan=@{identities=@(@{path=$source;sha256=(Get-CanvasHash $source)});work_dir=$work;assets_before=(Get-SelectionAssets $work)}
Assert-SelectionFiles $plan
if ($Mode -eq 'source') {[IO.File]::WriteAllText($source,'drift')}
elseif ($Mode -eq 'asset') {[IO.File]::WriteAllText($asset,'drift')}
elseif ($Mode -eq 'added') {[IO.File]::WriteAllText((Join-Path $work 'extra.txt'),'extra')}
elseif ($Mode -eq 'missing') {[IO.File]::Delete($asset)}
else {throw 'unknown fixture'}
$failed=$false;try {Assert-SelectionFiles $plan} catch {$failed=$true}
Assert-Case $failed
@{passed=$true} | ConvertTo-Json
'''

READY = r'''
Import-Function Test-SelectionReady
foreach ($text in @('SHSEL_HOST_READY','prefix SHSEL_HOST_READY'+"`n",'SURFDUMP_HOST_READY'+"`n",' SHSEL_HOST_READY'+"`n",'SHSEL_HOST_READY extra'+"`n")) {
 Assert-Case (-not (Test-SelectionReady $text))
}
Assert-Case (Test-SelectionReady ("prefix`r`nSHSEL_HOST_READY`r`n"))
@{passed=$true} | ConvertTo-Json
'''

SURFACE = r'''
Import-Function Assert-SelectionSurface
$plan=[IO.File]::ReadAllText((Join-Path $FixtureRoot 'plan.json')) | ConvertFrom-Json
$report=[IO.File]::ReadAllText((Join-Path $FixtureRoot 'report.json')) | ConvertFrom-Json
foreach ($name in @('Resolve-CanvasPath','Get-CanvasHash')) {Import-Function $name}
if ($Mode -eq 'normal') {$null=Assert-SelectionSurface $report $plan}
else {
 switch ($Mode) {
  'notbound' {$report.source_authenticated=$false}
  'truthy' {$report.ready_for_host_capture='true'}
  'initial' {$report.initial_map_trace.passed=$false}
  'sequence' {$report.selection_sequence.passed=$false}
  'projected' {$report.initial_log_projected=$true}
  'source' {$report.source.source_sha256.'tools/complete_hd_army_selection_trace.py'='0'*64}
  'probe' {$report.source.probe_raw_sha256='0'*64}
  'candidate' {$report.source.candidate_sha256='0'*64}
  'width' {$report.surface.width=1920}
  'vtable' {$report.surface.vtable=0}
  'wrap' {$report.surface.base=4294967290L}
  'headerwrap' {$report.surface.surface=4294967290L}
  'static' {$report.surface.surface=0x51d4c0}
  'type' {$report.surface.base='2097152'}
  'selected' {$report.surface.selected=4}
  'stop' {$report.surface.eip=0x406fa0}
  default {throw 'unknown fixture'}
 }
 $failed=$false;try {$null=Assert-SelectionSurface $report $plan} catch {$failed=$true}
 Assert-Case $failed
}
@{passed=$true} | ConvertTo-Json
'''

CAPTURE = r'''
foreach ($name in @('Save-SelectionSnapshot','Get-CanvasHash')) {Import-Function $name}
$script:Reads=0
function Read-CanvasMemory {
 param($Handle,$Address,$Count)
 $script:Reads++
 $data=New-Object byte[] $Count
 if ($Count -eq 4) {[BitConverter]::GetBytes([uint32]0x100000).CopyTo($data,0)}
 elseif ($Count -eq 188) {
  [BitConverter]::GetBytes([uint16]800).CopyTo($data,0);[BitConverter]::GetBytes([uint16]600).CopyTo($data,2)
  [BitConverter]::GetBytes([uint32]0x200000).CopyTo($data,4);[BitConverter]::GetBytes([uint32]0x50ee24).CopyTo($data,184)
  if ($Mode -eq 'header' -and $script:Reads -gt 3) {$data[20]=1}
  if ($Mode -eq 'vtable') {$data[184]=0}
 } else {$data[0]=1;$data[-1]=2}
 return ,$data
}
$surface=@{surface=0x100000;base=0x200000;width=800;height=600}
$failed=$false
try {$result=Save-SelectionSnapshot @{handle=123;identity=@{fixture='synthetic'}} $surface (Join-Path $FixtureRoot 'surface.raw') @{width=800;height=600}}
catch {$failed=$true}
Assert-Case ($failed -eq ($Mode -ne 'normal'))
if ($Mode -eq 'normal') {
 Assert-Case ($script:Reads -eq 5 -and $result.bytes -eq 480000 -and $result.reads.before.header.bytes -eq 188)
 foreach ($phase in @('before','after')) {foreach ($name in @('e0','header')) {
  $expected=Join-Path $FixtureRoot ('surface-'+$phase+'-'+$name+'.raw')
  Assert-Case ($result.reads[$phase][$name].path -ceq $expected -and (Test-Path -LiteralPath $expected))
 }}
 Assert-Case (@(Get-ChildItem -LiteralPath $FixtureRoot -Filter 'surface.-*').Count -eq 0)
}
@{passed=$true} | ConvertTo-Json
'''

TRIPLET = r'''
Import-Function Save-SelectionTriplet
$script:Count=0
function Save-SelectionSnapshot {
 param($OwnedGame,$Surface,$RawPath,$Plan)
 $script:Count++;[IO.File]::WriteAllBytes($RawPath,[byte[]](1,2,3))
 $pixel=if ($Mode -eq 'pixels' -and $script:Count -eq 2) {'changed'} else {'same'}
 $header=if ($Mode -eq 'header' -and $script:Count -eq 3) {'changed'} else {'same'}
 return @{path=$RawPath;sha256=$pixel;reads=@{before=@{e0=@{sha256='e0'};header=@{sha256=$header}}}}
}
$result=Save-SelectionTriplet @{handle=123} @{} @{out_dir=$FixtureRoot}
Assert-Case ($script:Count -eq 3 -and $result.snapshots.Count -eq 3)
Assert-Case ($result.clean_stable_pair -eq ($Mode -eq 'normal'))
foreach ($index in 1..3) {Assert-Case (Test-Path -LiteralPath (Join-Path $FixtureRoot ('capture-'+$index+'\surface.raw')))}
@{passed=$true} | ConvertTo-Json
'''

CLEANUP = r'''
foreach ($name in @('Stop-CanvasOwned','Test-SelectionCleanup')) {Import-Function $name}
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
Assert-Case ((Test-SelectionCleanup $cleanup) -eq ($Mode -ne 'failure'))
foreach ($bad in @('true',1,$false,$null)) {
 $cleanup=@{cdb=@{absent=$true;handle_closed=$true};candidates=@(@{absent=$true;handle_closed=$true});desktop_closed=$bad}
 Assert-Case (-not (Test-SelectionCleanup $cleanup))
 $cleanup.desktop_closed=$true;$cleanup.candidates[0].absent=$bad
 Assert-Case (-not (Test-SelectionCleanup $cleanup))
}
@{passed=$true} | ConvertTo-Json
'''

PERSISTENCE = r'''
foreach ($name in @('Invoke-SelectionCapture','Test-SelectionCleanup')) {Import-Function $name}
function Assert-SelectionFiles {}
function Resolve-CanvasPath {param($Path,$Root,$Kind);return $Path}
function Get-CanvasHash {return 'fixture-hash'}
function Get-SelectionAssets {return @{}}
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
$result=Invoke-SelectionCapture @{plan=$plan;packet=$script:Packet} -DoExecute
Assert-Case ($result.executed -is [bool] -and $result.executed -and -not $result.passed -and $result.status -ceq 'failed')
Assert-Case ($result.cleanup_verified -and $result.cdb.process_id -eq 77)
Assert-Case (@($result.failures | Where-Object {$_ -like '*Final summary persistence failed:*injected receipt write failure*'}).Count -eq 1)
Assert-Case (@($result.failures | Where-Object {$_ -eq 'injected post-launch identity failure'}).Count -eq 1)
@{passed=$true;synthetic_fixture_only=$true} | ConvertTo-Json
'''

LOG_BOUND = r'''
foreach ($name in @('Read-CanvasLog','Read-CanvasLogBytes')) {Import-Function $name}
$path=Join-Path $FixtureRoot 'synthetic.log'
[IO.File]::WriteAllText($path,"SHSEL_HOST_READY`r`n")
Assert-Case ((Read-CanvasLog $path) -ceq "SHSEL_HOST_READY`r`n")
$file=[IO.File]::OpenWrite($path);try {$file.SetLength(16777217)} finally {$file.Dispose()}
foreach ($name in @('Read-CanvasLog','Read-CanvasLogBytes')) {
 $failed=$false;try {$null=& $name $path} catch {$failed=$true}
 Assert-Case $failed
}
@{passed=$true} | ConvertTo-Json
'''


def synthetic_surface_fixture():
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    source = 'tools/complete_hd_army_selection_trace.py'
    plan = dict(stage='synthetic-stage', resolution='800x600', width=800, height=600,
                original_sha256='1'*64, candidate_sha256='2'*64, save_sha256='3'*64,
                probe_sha256='4'*64, candidate_manifest_canonical_sha256='5'*64,
                identities=[dict(path=str(ROOT/source), sha256=sha(ROOT/source))])
    report = dict(schema='clash95_complete_hd_army_selection_trace_v1', stage=plan['stage'],
                  resolution=plan['resolution'], passed=True, ready_for_host_capture=True,
                  source_authenticated=True, whole_candidate_bound=True, candidate_manifest_bound=True,
                  sequence_only=False, initial_log_projected=False, initial_map_trace=dict(passed=True),
                  selection_sequence=dict(passed=True),
                  surface=dict(tid=123, eip=0x406fa1, esp=0x100000, selected=3, prior=3, lower=1,
                               owner=0x40ad40, surface=0x100000, base=0x200000, width=800, height=600, vtable=0x50ee24))
    report['source']={key:plan[key] for key in ('original_sha256','candidate_sha256','save_sha256','candidate_manifest_canonical_sha256')}
    report['source'].update(probe_raw_sha256=plan['probe_sha256'],log_raw_sha256='6'*64,
                            source_sha256={source:sha(ROOT/source)})
    return plan, report


@unittest.skipUnless(os.name == 'nt' and PS.is_file(), 'Windows PowerShell required')
class HostBoundaryTests(unittest.TestCase):
    def run_ps(self, body, mode='normal'):
        with tempfile.TemporaryDirectory(prefix='complete-selection-host-fixture-') as directory:
            root=Path(directory)
            plan,report=synthetic_surface_fixture()
            (root/'plan.json').write_text(json.dumps(plan),encoding='utf-8')
            (root/'report.json').write_text(json.dumps(report),encoding='utf-8')
            script=root/'fixture.ps1';script.write_text(PRELUDE+body,encoding='utf-8-sig')
            result=subprocess.run([str(PS),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),
                '-HostPath',str(HOST),'-FixtureRoot',directory,'-Mode',mode],capture_output=True,
                text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            return json.loads(result.stdout)

    def test_dry_run_invocation_creates_nothing_and_never_calls_native_launch(self):
        self.assertTrue(self.run_ps(DRY_RUN)['passed'])

    def test_paths_reject_existing_sibling_traversal_stream_and_delimiter(self):
        self.assertTrue(self.run_ps(PATHS)['passed'])

    def test_source_asset_missing_and_added_inventory_changes_fail(self):
        for mode in ('source','asset','added','missing'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(DRIFT,mode)['passed'])

    def test_only_exact_complete_ready_line_with_newline_triggers_validation(self):
        self.assertTrue(self.run_ps(READY)['passed'])

    def test_full_bound_readiness_rejects_false_truthy_stale_and_bad_memory_fields(self):
        for mode in ('normal','notbound','truthy','initial','sequence','projected','source','probe',
                     'candidate','width','vtable','wrap','headerwrap','static','type','selected','stop'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(SURFACE,mode)['passed'])

    def test_memory_capture_pair_header_contract_and_exact_artifact_names(self):
        for mode in ('normal','header','vtable'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(CAPTURE,mode)['passed'])

    def test_triplet_retains_all_reads_on_pixel_or_header_difference(self):
        for mode in ('normal','pixels','header'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(TRIPLET,mode)['passed'])

    def test_retained_handle_cleanup_and_exact_bool_evidence(self):
        for mode in ('normal','exited','failure'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(CLEANUP,mode)['passed'])

    def test_failed_summary_write_preserves_executed_truth_and_owned_cleanup(self):
        self.assertTrue(self.run_ps(PERSISTENCE)['passed'])

    def test_log_byte_limit_also_applies_before_ready_polling(self):
        self.assertTrue(self.run_ps(LOG_BOUND)['passed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
