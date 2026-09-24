"""New primary host boundaries, extracted without sourcing its entry point.

One fixture starts an owned synthetic x86 console helper on a hidden desktop
to verify the actual private stdin transport. It never starts a game/debugger
or reads another process's pixels. Other native boundaries are stand-ins.
"""
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_modal_slots_primary_host as inherited

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / 'scripts/cdb/run_modal_primary_capture.ps1'


@unittest.skipUnless(os.name == 'nt' and inherited.PS.is_file(), 'Windows PowerShell required')
class PrimaryHostTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        patch.object(inherited.legacy, 'HOST', HOST).start()

    def run_ps(self, body, mode='normal'):
        # This host retains the v1 reader; avoid the slots host's v2 imports
        # and reader renaming while exercising the same extracted functions.
        return inherited.legacy.PrimaryHostTests.run_ps(
            self, 'Import-Function Get-PrimaryReadableRegions\n' + body, mode)

    test_paths = inherited.PrimaryHostTests.test_paths
    test_debugger_errors = inherited.PrimaryHostTests.test_debugger_errors_classified
    test_readable_ranges = inherited.PrimaryHostTests.test_readable_ranges
    test_region_union = inherited.PrimaryHostTests.test_region_union_preserves_flags_gaps_and_original_queries
    test_overlapping_queries = inherited.PrimaryHostTests.test_query_overlap_is_checked_before_rpm_and_same_base_drift_still_fails
    test_module_enumeration = inherited.PrimaryHostTests.test_mock_x86_module_enumeration
    test_module_identity = inherited.PrimaryHostTests.test_module_path_hash_extent
    test_read_rights = inherited.PrimaryHostTests.test_read_only_retained_handle_rights

    def test_final_report_write_failure_preserves_actual_execution_and_cleanup(self):
        self.assertTrue(self.run_ps(r'''
Import-Function Save-CanvasCaptureSummary
Import-Function Write-CanvasJson
$plan=@{out_dir=$FixtureRoot}
$summary=@{passed=$true;status='bounded_hidden_modal_primary_capture';executed=$true;
 failures=@();cdb=@{process_id=77};cleanup=@{cdb=@{absent=$true;handle_closed=$true;input_closed=$true};desktop_closed=$true}}
Save-CanvasCaptureSummary $plan $summary
$saved=Get-Content -LiteralPath (Join-Path $FixtureRoot 'summary.json') -Raw | ConvertFrom-Json
Assert-Case ($saved.executed -and $saved.passed -and $saved.cleanup.desktop_closed) 'Successful persistence changed execution evidence'
# An actual directory at the file destination causes a real storage failure.
$blocked=Join-Path $FixtureRoot 'blocked'
[void](New-Item -ItemType Directory -Path (Join-Path $blocked 'summary.json'))
Save-CanvasCaptureSummary @{out_dir=$blocked} $summary
Assert-Case (-not $summary.passed -and $summary.status -ceq 'failed') 'Unwritten final report was accepted'
Assert-Case ($summary.executed -and $summary.cdb.process_id -eq 77 -and $summary.cleanup.cdb.absent -and $summary.cleanup.cdb.input_closed -and $summary.cleanup.desktop_closed) 'Storage failure erased actual execution or cleanup'
Assert-Case ($summary.failures.Count -eq 1 -and $summary.failures[0] -like 'Final summary could not be saved:*') 'Storage failure was not reported'
$stdout=$summary | ConvertTo-Json -Depth 10 | ConvertFrom-Json
Assert-Case ($stdout.executed -and -not $stdout.passed -and $stdout.cleanup.cdb.handle_closed) 'Failure summary cannot reach stdout intact'
@{passed=$true} | ConvertTo-Json
''')['passed'])

    def test_checkpoint_visualization_binds_empty_and_populated_actual_palettes(self):
        self.assertTrue(self.run_ps(r'''
foreach ($name in @('Convert-PrimaryCheckpointScreens','Get-PrimaryPaletteVisualizationMode','Get-CanvasHash')) {Import-Function $name}
$plan=@{converter=$Converter;converter_sha256=(Get-CanvasHash $Converter);python=$Python;width=2;height=2}
$prefix=Join-Path $FixtureRoot 'prefix.log';[IO.File]::WriteAllText($prefix,"fixture`n")
foreach ($mode in @('empty','color')) {
 $folder=Join-Path $FixtureRoot $mode;[void](New-Item -ItemType Directory -Path $folder)
 $palette=New-Object byte[] 1024
 # Flags alone are not RGB color. The color case sets the last RGB component.
 $palette[3]=1
 if ($mode -ceq 'color') {$palette[1022]=255}
 $palPath=Join-Path $folder 'palette.bin';[IO.File]::WriteAllBytes($palPath,$palette)
 $pixels=Join-Path $folder 'pixels.raw';[IO.File]::WriteAllBytes($pixels,[byte[]]@(0,1,128,255))
 $native=Join-Path $folder 'native.raw';[IO.File]::WriteAllBytes($native,(New-Object byte[] (640*480)))
 $palRecord=@{path=$palPath;sha256=(Get-CanvasHash $palPath);bytes=1024}
 $sample=@{path=$pixels;sha256=(Get-CanvasHash $pixels);native=@{path=$native;sha256=(Get-CanvasHash $native)};
  primary=@{pixels=@{path=$pixels;sha256=(Get-CanvasHash $pixels)};palette_entries=$palRecord}}
 $checkpoint=@{name='full-published';prefix=@{path=$prefix};snapshots=@($sample)}
 Convert-PrimaryCheckpointScreens $plan @($checkpoint)
 $expected=$(if($mode -ceq 'empty'){'grayscale-index-empty-palette'}else{'directdraw-palette'})
 foreach ($kind in @('primary','physical','native')) {
  $receipt=$sample[($kind+'_png')];$metadata=Get-Content -LiteralPath $receipt.metadata_path -Raw | ConvertFrom-Json
  Assert-Case ($receipt.palette_mode -ceq $expected -and $metadata.palette_mode -ceq $expected) 'Palette visualization mode was misclassified'
  Assert-Case ($receipt.palette_colors_available -eq ($mode -ceq 'color')) 'Grayscale indices claimed palette colors'
  Assert-Case ($receipt.color_scope -ceq $(if($mode -ceq 'empty'){'grayscale_index_preview_empty_attached_palette'}else{'matched_current_attached_proxy_palette'})) 'Wrong visualization color scope'
  Assert-Case ($receipt.sha256 -ceq (Get-CanvasHash $receipt.path) -and $receipt.palette_sha256 -ceq $palRecord.sha256) 'PNG or actual palette binding lost'
 }
 $palRecord.sha256='0'*64
 Expect-Failure {Convert-PrimaryCheckpointScreens $plan @($checkpoint)} 'Changed palette must not authorize a visualization'
 $palRecord.sha256=(Get-CanvasHash $palPath);[IO.File]::WriteAllBytes($palPath,(New-Object byte[] 1023));$palRecord.sha256=(Get-CanvasHash $palPath)
 Expect-Failure {Get-PrimaryPaletteVisualizationMode $palRecord} 'Short palette must fail even with matching new hash'
}
@{passed=$true} | ConvertTo-Json
''')['passed'])

    def test_ordered_checkpoint_plan_and_ready_records(self):
        self.assertTrue(self.run_ps(r'''
Import-Function Assert-PrimaryCheckpointPlan
Import-Function Get-PrimaryCheckpointReady
$rows=@(
 @{name='full-published';index=0;eips=@(0x610100,0x610200)},
 @{name='placeholder-before';index=1;eips=@(0x432f9e)},
 @{name='placeholder-after';index=2;eips=@(0x432fa1)},
 @{name='final-ready';index=3;eips=@(0x433e77)})
Assert-PrimaryCheckpointPlan $rows
$log=''
for ($i=0;$i -lt 4;$i++) {
 Assert-Case ($null -eq (Get-PrimaryCheckpointReady $log $i)) 'Old checkpoint became a new pause'
 $log+='MPCAP_HOST_READY name='+$rows[$i].name+"`r`n"
 Assert-Case ((Get-PrimaryCheckpointReady $log $i) -ceq $rows[$i].name) 'Exact next checkpoint rejected'
}
Assert-Case ($null -eq (Get-PrimaryCheckpointReady $log 4)) 'Final checkpoint became resumable'
foreach ($bad in @('MPCAP_HOST_READY name=full-published',"xMPCAP_HOST_READY name=full-published`n", "MPRI_HOST_READY`n")) {
 Assert-Case ($null -eq (Get-PrimaryCheckpointReady $bad 0)) 'Partial or unrelated marker authorized capture'
}
foreach ($bad in @("MPCAP_HOST_READY name=placeholder-before`n", "MPCAP_HOST_READY name=unknown`n", "MPCAP_HOST_READY name=full-published`nMPCAP_HOST_READY name=full-published`n")) {
 Expect-Failure {Get-PrimaryCheckpointReady $bad 0} 'Out of order or duplicate checkpoint'
}
foreach ($change in @(@(0,'index',1),@(1,'name','final-ready'),@(2,'eips',@(0x432fa2)),@(0,'eips',@(0x610100,0x610100)),@(0,'eips',@(0x610100,0x80000000)))) {
 $copy=$rows | ConvertTo-Json -Depth 8 | ConvertFrom-Json
 $copy[$change[0]].($change[1])=$change[2]
 Expect-Failure {Assert-PrimaryCheckpointPlan $copy} 'Malformed checkpoint plan'
}
Expect-Failure {Assert-PrimaryCheckpointPlan $rows[0..2]} 'Missing final checkpoint'
@{passed=$true} | ConvertTo-Json
''')['passed'])

    def test_only_captured_unchanged_nonfinal_checkpoint_can_resume(self):
        self.assertTrue(self.run_ps(r'''
foreach ($name in @('Resume-PrimaryCheckpoint','Get-CanvasHash','Get-CanvasBytesHash','Read-CanvasLogBytes')) {Import-Function $name}
Add-Type -TypeDefinition @'
using System;
public static class CanvasScreenNative {
 public static int calls=0;
 public static void ContinueOwnedDebugger(IntPtr handle) {
  if(handle.ToInt64()!=123)throw new Exception("Wrong private handle"); calls++;
 }
}
'@
function Test-CanvasProcessExited {param($Session);return [bool]$Session.exited}
$path=Join-Path $FixtureRoot 'prefix.log';[IO.File]::WriteAllText($path,"checkpoint`n")
$plan=@{host_path=$HostPath;host_sha256=(Get-CanvasHash $HostPath)}
$session=@{handle=[IntPtr]456;input_write=[IntPtr]123;input_closed=$false;exited=$false;identity=@{process_id=77}}
function Fresh {
 return @{name='full-published';index=0;snapshots=@(@{sha256='actual-fixture'});resumed=$false;
  prefix=@{path=$path;sha256=(Get-CanvasHash $path)}}
}
$checkpoint=Fresh
$receipt=Resume-PrimaryCheckpoint $session $checkpoint $path $plan
Assert-Case ($checkpoint.resumed -and $receipt.written -and $receipt.command -ceq 'g' -and $receipt.bytes -eq 3) 'Continuation receipt differs'
Assert-Case ($receipt.command_sha256 -ceq (Get-CanvasBytesHash ([byte[]]@(103,13,10)))) 'Exact debugger command bytes differ'
Expect-Failure {Resume-PrimaryCheckpoint $session $checkpoint $path $plan} 'Duplicate continuation'
foreach ($change in @(@('name','final-ready'),@('index',1),@('snapshots',@()),@('snapshots',@(@{},@{})))) {
 $bad=Fresh;$bad[$change[0]]=$change[1]
 Expect-Failure {Resume-PrimaryCheckpoint $session $bad $path $plan} 'Invalid pause'
}
foreach ($key in @('input_closed','exited')) {
 $session[$key]=$true
 Expect-Failure {Resume-PrimaryCheckpoint $session (Fresh) $path $plan} 'Unavailable owned debugger'
 $session[$key]=$false
}
$bad=Fresh;$bad.prefix.sha256='0'*64
Expect-Failure {Resume-PrimaryCheckpoint $session $bad $path $plan} 'Changed prefix'
Assert-Case ([CanvasScreenNative]::calls -eq 1) 'Rejected checkpoint wrote debugger input'
@{passed=$true} | ConvertTo-Json
''')['passed'])

    def test_actual_private_pipe_sends_only_g_and_hidden_helper_exits(self):
        self.assertTrue(self.run_ps(r'''
foreach ($name in @('Initialize-CanvasNative','ConvertTo-CanvasArgument')) {Import-Function $name}
Initialize-CanvasNative
$exe=Join-Path $FixtureRoot 'synthetic-stdin.exe'
$result=Join-Path $FixtureRoot 'received.txt'
$helperSource=Join-Path $FixtureRoot 'synthetic-stdin.cs'
[IO.File]::WriteAllText($helperSource,@'
using System;using System.IO;
public static class SyntheticInput {
 public static int Main(string[] args) {
  string value=Console.ReadLine();File.WriteAllText(args[0],value??"<eof>");
  return value=="g"?0:3;
 }
}
'@)
& 'C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe' /nologo /platform:x86 ('/out:'+$exe) $helperSource | Out-Null
Assert-Case ($LASTEXITCODE -eq 0) 'Synthetic x86 stdin helper compile failed'
$name='ClashPrimaryFixture_'+[Guid]::NewGuid().ToString('N')
$desktop=[CanvasScreenNative]::CreateDesktopW($name,[IntPtr]::Zero,[IntPtr]::Zero,0,0x000F01FF,[IntPtr]::Zero)
if ($desktop -eq [IntPtr]::Zero) {throw 'Synthetic hidden desktop creation failed'}
[IntPtr]$fixtureInput=[IntPtr]::Zero;$process=$null
try {
 $command=(ConvertTo-CanvasArgument $exe)+' '+(ConvertTo-CanvasArgument $result)
 $process=[CanvasScreenNative]::StartWithInput($exe,$command,$name,[IntPtr]::Zero,$FixtureRoot,[ref]$fixtureInput)
 [void][CanvasScreenNative]::CloseHandle($process.thread)
 Assert-Case ([CanvasScreenNative]::WaitForSingleObject($process.process,0) -eq 258) 'Synthetic reader was not waiting on private stdin'
 [CanvasScreenNative]::ContinueOwnedDebugger($fixtureInput)
 Assert-Case ([CanvasScreenNative]::WaitForSingleObject($process.process,15000) -eq 0) 'Synthetic reader failed to terminate'
 Assert-Case ([IO.File]::ReadAllText($result) -ceq 'g') 'Native private pipe wrote other than exact g'
} finally {
 if ($fixtureInput -ne [IntPtr]::Zero) {[void][CanvasScreenNative]::CloseHandle($fixtureInput)}
 if ($null -ne $process) {
  if ([CanvasScreenNative]::WaitForSingleObject($process.process,0) -ne 0) {[void][CanvasScreenNative]::TerminateProcess($process.process,1);[void][CanvasScreenNative]::WaitForSingleObject($process.process,5000)}
  [void][CanvasScreenNative]::CloseHandle($process.process)
 }
 [void][CanvasScreenNative]::CloseDesktop($desktop)
}
@{passed=$true;game_executed=$false;debugger_executed=$false} | ConvertTo-Json
''')['passed'])

    def test_cursor_auxiliary_reads_are_bounded_before_pointer_dereference(self):
        self.assertTrue(self.run_ps(r'''
Import-Function Read-PrimaryCursorState
Import-Function Get-CanvasHash
$script:Addresses=New-Object 'Collections.Generic.List[long]'
$script:AuxMode='normal'
function Read-PrimaryArtifact {
 param($Owned,[long]$Address,[int]$Count,$Path,$Regions)
 $script:Addresses.Add($Address);$bytes=New-Object byte[] $Count
 if ($Address -eq 0x544cd8) {
  [BitConverter]::GetBytes([uint32]0x30000000).CopyTo($bytes,8)
  [BitConverter]::GetBytes([uint32]1).CopyTo($bytes,56)
  [BitConverter]::GetBytes([uint32]$(if($script:AuxMode -eq 'descriptor'){0x519679}else{0x519678})).CopyTo($bytes,60)
  [BitConverter]::GetBytes([uint32]0x31000000).CopyTo($bytes,64)
 } elseif ($Address -eq 0x519678) {
  [BitConverter]::GetBytes([uint32]1).CopyTo($bytes,4)
  [BitConverter]::GetBytes([uint32]$(if($script:AuxMode -eq 'frame'){18}else{0})).CopyTo($bytes,32)
 } elseif ($Address -eq 0x31000000) {
  [BitConverter]::GetBytes([uint32]0x32000000).CopyTo($bytes,0)
  [BitConverter]::GetBytes([uint16]18).CopyTo($bytes,0x1004)
  [BitConverter]::GetBytes([uint16]32).CopyTo($bytes,0x1006)
 } elseif ($Address -eq 0x30000000) {
  [BitConverter]::GetBytes([uint16]$(if($script:AuxMode -eq 'backing'){65}else{64})).CopyTo($bytes,0)
  [BitConverter]::GetBytes([uint16]64).CopyTo($bytes,2)
  [BitConverter]::GetBytes([uint32]$(if($script:AuxMode -eq 'high_pointer'){0x80000000}else{0x33000000})).CopyTo($bytes,4)
  [BitConverter]::GetBytes([uint32]0x50ee24).CopyTo($bytes,184)
 } elseif ($Address -eq 0x532144) {
  [BitConverter]::GetBytes([uint32]0x34000000).CopyTo($bytes,0)
 } elseif ($Address -eq 0x34000000) {
  [BitConverter]::GetBytes([uint32]0x35000000).CopyTo($bytes,100)
  [BitConverter]::GetBytes([uint16]$(if($script:AuxMode -eq 'placeholder'){25}else{26})).CopyTo($bytes,0x1004)
  [BitConverter]::GetBytes([uint16]203).CopyTo($bytes,0x1006)
 }
 [IO.File]::WriteAllBytes($Path,$bytes)
 return @{address=$Address;bytes=$Count;path=$Path;sha256=(Get-CanvasHash $Path);data=$bytes}
}
$plan=@{out_dir=$FixtureRoot};$owned=@{handle=123}
$records=Read-PrimaryCursorState $owned $plan before @{}
Assert-Case ($records.Count -eq 9 -and $script:Addresses.Count -eq 9) 'Missing actual cursor/barracks artifact'
Assert-Case ($records.backing_pixels.bytes -eq 4096 -and $records.barracks_pointer.address -eq 0x532144) 'Wrong auxiliary byte bounds'
foreach ($record in $records.Values) {Assert-Case (-not $record.ContainsKey('data')) 'Raw arrays leaked into JSON receipt'}
foreach ($case in @(@('descriptor',1),@('frame',3),@('backing',5),@('high_pointer',5),@('placeholder',8))) {
 $script:AuxMode=$case[0];$script:Addresses.Clear()
 Expect-Failure {Read-PrimaryCursorState $owned $plan after @{}} 'Unbounded auxiliary pointer or descriptor'
 Assert-Case ($script:Addresses.Count -eq $case[1]) 'Rejected context reached a dependent memory read'
}
@{passed=$true} | ConvertTo-Json
''')['passed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
