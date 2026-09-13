"""Extracted PowerShell function tests with mocked native boundaries.

The production script is parsed, never dot-sourced. No CDB, game, DLL, target
process, desktop, OS input or live capture API runs in this suite.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_framed_modal_primary_host as legacy
import test_framed_modal_canvas_capture as canvas
import test_modal_slots_barracks_capture as barracks
from test_framed_screen_capture import PRELUDE,PS

ROOT=Path(__file__).resolve().parents[1]
HOST=ROOT/'scripts/cdb/run_modal_slots_primary_capture.ps1'


def lifecycle(command_error=None):
    """Reuse controlled orchestration data, replacing every target boundary."""
    text=legacy.lifecycle(command_error)
    text=text.replace("'Read-CanvasLog'", "'Read-CanvasLog','Save-CanvasTriplet'")
    text=text.replace("primary_snapshot=@{cached_primary_snapshot_valid=($Mode -ne 'primary_failure')}",
        "primary_snapshot=@{cached_primary_snapshot_valid=($Mode -ne 'primary_failure');three_matched_captures=$true}")
    text=text.replace("pixel_reads=1;paused=$true}",
        "pixel_reads=1;paused=$true;native=@{sha256='synthetic-native'};reads=@{before=@{state=@{sha256='s'};e0=@{sha256='e'};physical_header=@{sha256='p'};native_header=@{sha256='n'}}}}")
    text=text.replace("palette_entries=@{path=$pal;bytes=1024;sha256=(Get-CanvasHash $pal)}}",
        "palette_entries=@{path=$pal;bytes=1024;sha256=(Get-CanvasHash $pal)};reads=@{before=@{backend=@{sha256='backend'}}}}")
    text=text.replace('$bundle=@{plan=$plan;prepared=$script:Prepared}',
        "$plan.candidate_manifest=$inputPath;$plan.candidate_manifest_sha256=$hash\n"
        "$plan.primary_source=$inputPath;$plan.primary_source_sha256=$hash\n"
        '$bundle=@{plan=$plan;prepared=$script:Prepared}')
    return text


@unittest.skipUnless(os.name=='nt' and PS.is_file(),'Windows PowerShell parser required')
class PrimaryHostTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        patch.object(legacy,'HOST',HOST).start()

    run_ps=legacy.PrimaryHostTests.run_ps
    test_unique_complete_ready=legacy.PrimaryHostTests.test_only_unique_primary_readiness_accepts
    test_debugger_errors_classified=legacy.PrimaryHostTests.test_debugger_command_failures_are_not_native_crashes
    test_paths=legacy.PrimaryHostTests.test_original_path_restrictions_remain
    test_bound_current_palette_and_headers=legacy.PrimaryHostTests.test_current_palette_and_headers_surround_read
    test_readable_ranges=legacy.PrimaryHostTests.test_virtual_query_covers_every_byte_before_read
    test_mock_x86_module_enumeration=legacy.PrimaryHostTests.test_x86_module_enumeration_uses_retained_handle_and_bounded_queries
    test_module_path_hash_extent=legacy.PrimaryHostTests.test_proxy_module_path_hash_uniqueness_and_range_remain_required
    test_read_only_retained_handle_rights=legacy.PrimaryHostTests.test_owned_handle_includes_query_information_without_writes

    def test_full_canvas_initial_slots_and_primary_guards_before_reads(self):
        text=canvas.PURE.replace('MCAP_SURFDUMP_HOST_READY','MPRI_HOST_READY')
        text=text.replace("schema='clash95_framed_modal_canvas_trace_v1';passed=$true",
            "schema='clash95_modal_slots_trace_v1';primary_sequence=@{passed=$true};slot_trace=@{passed=$true;raw_records=@(1..12)};passed=$true")
        text=text.replace('@{passed=$true;cases=70}', '@{passed=$true;cases=70}')
        text += r'''
foreach ($key in @('initial_map_trace','slot_trace','primary_sequence')) {
 $r=New-Report;$r[$key].passed=$false
 Expect-Failure {Assert-CanvasSurface $r $plan} ('failed required trace '+$key)
}
foreach ($count in 11,13) {$r=New-Report;$r.slot_trace.raw_records=@(1..$count);Expect-Failure {Assert-CanvasSurface $r $plan} 'slot count'}
'''
        # Move the sole result after the additional assertions.
        text=text.replace('@{passed=$true} | ConvertTo-Json','')+'\n@{passed=$true} | ConvertTo-Json\n'
        self.assertTrue(self.run_ps(text)['passed'])

    def test_dry_run_returns_before_native_initialization_and_output_creation(self):
        self.assertTrue(self.run_ps(r'''
Import-Function Invoke-CanvasCapture
$script:Native=0
function Start-CanvasHidden {$script:Native++;throw 'runtime forbidden'}
function Initialize-CanvasNative {$script:Native++;throw 'runtime forbidden'}
function New-Item {throw 'dry run created output'}
$plan=@{out_dir=(Join-Path $FixtureRoot 'must-not-exist')}
$r=Invoke-CanvasCapture @{plan=$plan;prepared=@{packet='synthetic'}}
Assert-Case ($r.status -ceq 'dry_run' -and -not $r.executed -and $script:Native -eq 0) 'offline default crossed boundary'
Assert-Case (-not (Test-Path $plan.out_dir)) 'offline default wrote files'
@{passed=$true} | ConvertTo-Json
''')['passed'])

    def test_three_samples_compare_all_layers_and_keep_failed_artifacts(self):
        body=r'''
Import-Function Save-CanvasTriplet
$script:Count=0
function Save-CanvasSnapshot {
 param($Owned,$Evidence,$Path,$Plan)
 $script:Count++
 [IO.File]::WriteAllBytes($Path,[byte[]](1,2,3))
 return @{path=$Path;sha256='same';native=@{sha256='native'};reads=@{before=@{
 state=@{sha256='state'};e0=@{sha256='e0'};physical_header=@{sha256='ph'};native_header=@{sha256='nh'}}}}
}
function Save-PrimarySnapshot {
 param($Owned,$Trace,$Plan,$Prefix)
 $path=Join-Path $Plan.out_dir 'primary.raw';[IO.File]::WriteAllBytes($path,[byte[]](4,5,6))
 $result=@{pixels=@{path=$path;sha256='primary'};palette_entries=@{sha256='palette'};reads=@{before=@{backend=@{sha256='backend'}}}}
 if ($script:Count -eq 2) {
  if ($Mode -eq 'pixels') {$result.pixels.sha256='changed'}
  if ($Mode -eq 'palette') {$result.palette_entries.sha256='changed'}
  if ($Mode -eq 'header') {$result.reads.before.backend.sha256='changed'}
 }
 return $result
}
$r=Save-CanvasTriplet @{handle=123} @{} @{out_dir=$FixtureRoot} @{} @{}
Assert-Case ($script:Count -eq 3 -and $r.snapshots.Count -eq 3) 'missing capture'
Assert-Case ($r.clean_stable_pair -eq ($Mode -eq 'normal')) 'changed sample accepted'
foreach ($i in 1..3) {
 foreach ($name in 'primary.raw','surface.raw') {
  Assert-Case (Test-Path (Join-Path $FixtureRoot ('capture-'+$i+'\'+$name))) 'failed raw removed'
 }
}
@{passed=$true} | ConvertTo-Json
'''
        for mode in ('normal','pixels','palette','header'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(body,mode)['passed'])

    def test_exact_retained_cleanup_never_reopens_pid(self):
        for mode in ('normal','exited','failure'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(barracks.CLEANUP,mode)['passed'])

    def test_child_nonzero_failure_details_survive_final_json(self):
        with tempfile.TemporaryDirectory(prefix='slots-primary-child-') as directory:
            script=Path(directory)/'fixture.ps1'
            script.write_text(barracks.PRELUDE+barracks.CHILD_FAILURE,encoding='utf-8-sig')
            result=subprocess.run([str(PS),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),
                '-HostPath',str(HOST),'-FixtureRoot',directory,'-Mode',sys.executable],
                capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)
            self.assertTrue(result.stdout.strip(),result.stderr)
            report=json.loads(result.stdout)
            self.assertEqual(report['child_failure']['failures'],['source snapshot differs','candidate recipe mismatch'])
            self.assertFalse(report['passed']);self.assertFalse(report['executed'])
            self.assertNotIn('do-not-copy-this-packet',json.dumps(report))

    def test_full_mocked_host_preserves_parser_final_log_and_cleanup_failures(self):
        for mode in ('normal','early_map','parse_failure','ambiguous','partial_start_failure','start_failure',
                     'cleanup_failure','final_trace','final_prefix','final_hash','primary_failure'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(lifecycle(),mode)['passed'])

    def test_debugger_command_failure_stops_before_parse_and_capture(self):
        text='Unable to insert breakpoint 27 at 00000110, Win32 error 0n299'
        self.assertTrue(self.run_ps(lifecycle(text),'command_failure')['passed'])

    def test_actual_surface_artifact_names_match_offline_auditor(self):
        body=r'''
function Assert-CanvasSurface {
 param($Report,$Plan)
 return @{surface=$Report.surface;canvas=$Report.modal_sequence.raw_records[0].values}
}
'''+canvas.CAPTURE.replace("'Assert-CanvasSurface',",'')
        body=body.replace('@{passed=$true;calls=@($script:Calls)} | ConvertTo-Json',r'''
Assert-Case ([IO.Path]::GetFileName([IO.Path]::ChangeExtension($path,$null)) -ceq 'surface.') 'Original PowerShell empty-extension defect no longer reproduced'
foreach ($phase in 'before','after') {
 foreach ($name in 'state','e0','physical_header','native_header') {
  $expected=Join-Path $FixtureRoot ('surface-'+$phase+'-'+$name+'.raw')
  Assert-Case ($result.reads[$phase][$name].path -ceq $expected -and (Test-Path -LiteralPath $expected)) 'Live producer filename differs from offline auditor'
 }
}
Assert-Case (@(Get-ChildItem $FixtureRoot -Filter 'surface.-*.raw').Count -eq 0) 'Producer retained erroneous trailing dot'
@{passed=$true} | ConvertTo-Json
''')
        self.assertTrue(self.run_ps(body)['passed'])

    def test_physical_png_uses_matching_captured_primary_palette(self):
        body=lifecycle()+r'''
$attached=$result.snapshots[0].primary.palette_entries
Assert-Case ((Get-CanvasHash $plan.palette_path) -cne $attached.sha256) 'Synthetic unrelated global palette must differ'
Assert-Case ($result.palette.path -ceq $attached.path -and $result.palette.sha256 -ceq $attached.sha256) 'Physical PNG used unrelated global palette'
Assert-Case ($result.palette.binding -ceq 'matching_paused_primary_attached_palette') 'Physical palette evidence binding missing'
Assert-Case ($result.png.palette_path -ceq $attached.path) 'Converter metadata did not retain matching captured palette'
'''
        self.assertTrue(self.run_ps(body)['passed'])


if __name__=='__main__':unittest.main(verbosity=2)
