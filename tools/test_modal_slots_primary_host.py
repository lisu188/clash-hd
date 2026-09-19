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

QUERY_MOCK=r'''
Add-Type -TypeDefinition @'
using System;using System.Runtime.InteropServices;
public static class ModalPrimaryQuery {
 [StructLayout(LayoutKind.Sequential)] public struct MBI {public IntPtr address,allocation;public uint allocationProtect;public UIntPtr size;public uint state,protect,type;}
 public static int mode=0,calls=0;
 public static UIntPtr VirtualQueryEx(IntPtr handle,IntPtr cursor,out MBI info,UIntPtr count) {
  if(handle.ToInt64()!=123)throw new Exception("Retained query handle changed");
  calls++;long start=cursor.ToInt64() & ~4095L;ulong size=4096;
  if(start==0x20000000)size=12288;if(start==0x22000000)size=1048576;
  info=new MBI();info.address=new IntPtr(start);info.size=new UIntPtr(size);
  info.allocation=new IntPtr(start & ~65535L);info.allocationProtect=4;
  info.state=4096;info.protect=4;info.type=0x20000;
  if(mode==1)info.protect=0x104;if(mode==2)info.state=0x2000;
  if(mode==3)info.size=UIntPtr.Zero;if(mode==4)return UIntPtr.Zero;
  if(mode==5)info.allocationProtect=2;if(mode==6)info.type=0x40000;
  if(mode==7)info.allocation=new IntPtr((start & ~65535L)-65536);
  if(mode==8)info.address=new IntPtr(start+4096);
  if(mode==9)info.size=new UIntPtr(0x100000000UL);
  if(mode==10)info.address=new IntPtr(start+1);
  return count;
 }
}
'@
function Initialize-PrimaryQuery {}
'''


def actual_snapshot_fixture():
    """Reuse identity bytes but execute the actual query, ledger and RPM writer."""
    text=legacy.CAPTURE.replace('function Read-PrimaryArtifact {','function Read-CanvasMemory {')
    text=text.replace('param($Owned,$Address,$Count,$Path,$Regions)','param($Handle,$Address,$Count)')
    text=text.replace('[IO.File]::WriteAllBytes($Path,$data)\n return @{path=$Path;address=$Address;bytes=$Count;sha256=(Get-CanvasHash $Path);data=$data}',
                      'return ,$data')
    return QUERY_MOCK+"Import-Function Read-PrimaryArtifact\n"+text


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

    def run_ps(self,body,mode='normal'):
        # Keep old query fixtures exercising historical v1 exactly. New tests
        # below execute v2 with durable ledgers and actual extracted functions.
        if '$regions=@{}' in body:body=body.replace('Read-PrimaryArtifact','Read-PrimaryArtifactV1')
        return legacy.PrimaryHostTests.run_ps(self,
            "foreach ($name in 'Get-PrimaryReadableRegions','New-PrimaryQueryLedger','Add-PrimaryQueryLedgerRow',"
            "'Get-PrimaryQueryCertificate','Get-PrimaryQueryLedgerArtifact') {Import-Function $name}\n"+body,mode)
    test_unique_complete_ready=legacy.PrimaryHostTests.test_only_unique_primary_readiness_accepts
    test_debugger_errors_classified=legacy.PrimaryHostTests.test_debugger_command_failures_are_not_native_crashes
    test_paths=legacy.PrimaryHostTests.test_original_path_restrictions_remain
    test_readable_ranges=legacy.PrimaryHostTests.test_virtual_query_covers_every_byte_before_read
    test_mock_x86_module_enumeration=legacy.PrimaryHostTests.test_x86_module_enumeration_uses_retained_handle_and_bounded_queries
    test_module_path_hash_extent=legacy.PrimaryHostTests.test_proxy_module_path_hash_uniqueness_and_range_remain_required
    test_read_only_retained_handle_rights=legacy.PrimaryHostTests.test_owned_handle_includes_query_information_without_writes

    def test_bound_current_palette_and_headers(self):
        for mode in ('normal','changed_header','changed_palette','palette_pointer','identity'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(actual_snapshot_fixture(),mode)['passed'])

    def test_region_union_preserves_flags_gaps_and_original_queries(self):
        self.assertTrue(self.run_ps(r'''
function Region {param([long]$Address,[long]$Size,[int]$Protect=4);return @{address=$Address;size=$Size;state=4096;protect=$Protect}}
# Exact query geometry retained in the failed F receipt; this synthetic fixture
# exercises the host function and does not reclassify that runtime evidence.
$actualGeometry=@((Region 0x0429e000 4096),(Region 0x0420d000 598016))
$cases=@(
 @{claims=$actualGeometry;expected=@(,@(0x0420d000,598016,4))},
 @{claims=@((Region 0x3000 0x2000),(Region 0x1000 0x3000));expected=@(,@(0x1000,0x4000,4))},
 @{claims=@((Region 0x2000 0x1000),(Region 0x1000 0x1000));expected=@(,@(0x1000,0x2000,4))},
 @{claims=@((Region 0x1000 0x3000),(Region 0x2000 0x1000),(Region 0x1000 0x3000));expected=@(,@(0x1000,0x3000,4))},
 @{claims=@((Region 0x5000 0x1000),(Region 0x2000 0x1000 2),(Region 0x1000 0x1000));expected=@(@(0x1000,0x1000,4),@(0x2000,0x1000,2),@(0x5000,0x1000,4))},
 @{claims=@((Region 4294963200 4096 0x20));expected=@(,@(4294963200,4096,0x20))}
)
foreach ($case in $cases) {
 $original=$case.claims | ConvertTo-Json -Depth 5 -Compress
 $rows=@(Get-PrimaryReadableRegions $case.claims)
 Assert-Case ($rows.Count -eq $case.expected.Count) 'Incorrect normalized region count'
 for ($i=0;$i -lt $rows.Count;$i++) {
  $r=$rows[$i];$e=$case.expected[$i]
  Assert-Case ($r.address -eq $e[0] -and $r.size -eq $e[1] -and $r.protect -eq $e[2] -and $r.state -eq 4096) 'Union changed coverage or protection'
 }
 Assert-Case (($case.claims | ConvertTo-Json -Depth 5 -Compress) -ceq $original) 'Normalization mutated query observations'
}
foreach ($claims in @(
 @((Region 0x1000 0x3000),(Region 0x2000 0x1000 2)),
 @((Region 0x2000 0x3000 0x20),(Region 0x1000 0x2000)),
 @((Region 0x1000 0x1000),(Region 0x1000 0x1000 8)))) {
 Expect-Failure {Get-PrimaryReadableRegions $claims} 'overlapping incompatible readable protection'
}
foreach ($bad in @(
 @{address=0x2000;size=0x1000;state=0x2000;protect=4},
 @{address=0x2000;size=0x1000;state=0x1000;protect=0x104},
 @{address=0;size=0x1000;state=0x1000;protect=4},
 @{address=0x1000;size=0;state=0x1000;protect=4},
 @{address=4294963200;size=8192;state=0x1000;protect=4})) {
 Expect-Failure {Get-PrimaryReadableRegions @((Region 0x1000 0x3000),$bad)} 'invalid observed region'
}
@{passed=$true} | ConvertTo-Json
''')['passed'])

    def test_query_overlap_is_checked_before_rpm_and_same_base_drift_still_fails(self):
        self.assertTrue(self.run_ps(r'''
foreach ($name in 'Read-PrimaryArtifact','Get-CanvasHash') {Import-Function $name}
Add-Type -TypeDefinition @'
using System;using System.Runtime.InteropServices;
public static class ModalPrimaryQuery {
 [StructLayout(LayoutKind.Sequential)] public struct MBI {
  public IntPtr address, allocation;public uint allocationProtect;
  public UIntPtr size;public uint state,protect,type;
 }
 public static long start=0x0420d000,length=598016;public static uint protect=4;
 public static int calls=0;
 public static UIntPtr VirtualQueryEx(IntPtr handle,IntPtr cursor,out MBI info,UIntPtr count) {
  if(handle.ToInt64()!=123)throw new Exception("Retained handle changed");
  calls++;info=new MBI();info.address=new IntPtr(start);info.size=new UIntPtr((ulong)length);
  info.state=0x1000;info.protect=protect;return count;
 }
}
'@
function Initialize-PrimaryQuery {}
$script:PixelReads=0
function Read-CanvasMemory {param($h,$a,$n);$script:PixelReads++;return ,(New-Object byte[] $n)}
$regions=@{};$owned=@{handle=[IntPtr]123};$path=Join-Path $FixtureRoot 'query.raw'
$first=Read-PrimaryArtifact $owned 0x0420d040 32 $path $regions
[ModalPrimaryQuery]::start=0x0429e000;[ModalPrimaryQuery]::length=4096
$second=Read-PrimaryArtifact $owned 0x0429e040 32 $path $regions
$third=Read-PrimaryArtifact $owned 0x0429e040 32 $path $regions
$normalized=@(Get-PrimaryReadableRegions @($regions.Values))
Assert-Case ($regions.Count -eq 2 -and $normalized.Count -eq 1 -and $normalized[0].address -eq 0x0420d000 -and $normalized[0].size -eq 598016) 'Contained suffix query lost or coverage differs'
Assert-Case ($script:PixelReads -eq 3 -and [ModalPrimaryQuery]::calls -eq 3) 'Repeated observations skipped required reads'
$original=$regions | ConvertTo-Json -Depth 5 -Compress
foreach ($spec in @(@(0x0429d000,4096,2),@(0x0420d000,593920,4),@(0x0420d000,598016,8))) {
 [ModalPrimaryQuery]::start=$spec[0];[ModalPrimaryQuery]::length=$spec[1];[ModalPrimaryQuery]::protect=$spec[2]
 $failedPath=Join-Path $FixtureRoot ('failed-'+$spec[0]+'-'+$spec[2]+'.raw')
 Expect-Failure {Read-PrimaryArtifact $owned ($spec[0]+32) 32 $failedPath $regions} 'conflict or same-base drift'
 Assert-Case (-not (Test-Path $failedPath)) 'Rejected query wrote an artifact'
 Assert-Case (($regions | ConvertTo-Json -Depth 5 -Compress) -ceq $original) 'Rejected query changed retained observations'
}
Assert-Case ($script:PixelReads -eq 3) 'Conflicting query reached RPM'
@{passed=$true} | ConvertTo-Json
''')['passed'])

    def test_snapshot_emits_disjoint_coverage_and_retains_query_provenance(self):
        body=actual_snapshot_fixture()
        body=body.replace('@{passed=$true} | ConvertTo-Json',r'''
$rows=@([IO.File]::ReadAllLines($r.query_ledger.path) | ForEach-Object {$_ | ConvertFrom-Json})
$queries=@($rows | Where-Object {$_.kind -ceq 'query'})
Assert-Case ($r.schema -ceq 'clash95_modal_primary_snapshot_receipt_v2' -and $r.region_scheme -ceq 'primary_virtual_query_ledger_v1') 'New source mislabeled v1'
Assert-Case ($r.query_ledger.records -eq 39 -and $rows.Count -eq 39 -and $queries.Count -eq 19) 'Raw query duplicates or completed reads discarded'
Assert-Case ($r.query_ledger.sha256 -ceq (Get-CanvasHash $r.query_ledger.path)) 'Ledger not hash-bound'
$outer=@($queries | Where-Object {$_.region.address -eq 0x20000000})
$inner=@($queries | Where-Object {$_.region.address -eq 0x20001000})
Assert-Case ($outer.Count -eq 2 -and $outer[0].region.size -eq 12288 -and $inner.Count -eq 4) 'Nested and repeated returned queries lost'
$ordered=@($r.regions | Sort-Object {[long]$_.address})
for ($i=1;$i -lt $ordered.Count;$i++) {Assert-Case ($ordered[$i-1].address+$ordered[$i-1].size -le $ordered[$i].address) 'Certificate still overlaps'}
Assert-Case (@($r.regions | Where-Object {$_.address -eq 0x20000000 -and $_.size -eq 12288}).Count -eq 1) 'Certificate lost nested coverage'
@{passed=$true} | ConvertTo-Json
''')
        self.assertTrue(self.run_ps(body)['passed'])

    def test_every_rejected_raw_query_is_appended_before_validation_or_rpm(self):
        body=QUERY_MOCK+r'''
foreach ($name in 'Read-PrimaryArtifact','Get-CanvasHash') {Import-Function $name}
$script:PixelReads=0
function Read-CanvasMemory {param($Handle,$Address,$Count);$script:PixelReads++;return ,(New-Object byte[] $Count)}
$owned=@{handle=[IntPtr]123;identity=@{process_id=100;creation_filetime=123;candidate_sha256=('a'*64)}}
foreach ($modeNumber in 1..10) {
 $folder=Join-Path $FixtureRoot ('bad-'+$modeNumber);[void](New-Item -ItemType Directory $folder)
 $ledger=New-PrimaryQueryLedger $owned @{out_dir=$folder;run_id='synthetic'} @{sha256=('b'*64)}
 [ModalPrimaryQuery]::mode=0
 $first=Read-PrimaryArtifact $owned 0x20000020 32 (Join-Path $folder 'first.raw') $ledger
 $prefix=[IO.File]::ReadAllText($ledger.path);$readCount=$script:PixelReads
 [ModalPrimaryQuery]::mode=$modeNumber
 $badPath=Join-Path $folder 'failed.raw'
 Expect-Failure {Read-PrimaryArtifact $owned 0x20001020 32 $badPath $ledger} 'invalid/contradictory query'
 Assert-Case ($script:PixelReads -eq $readCount -and -not (Test-Path -LiteralPath $badPath)) 'Rejected query reached RPM'
 $raw=[IO.File]::ReadAllText($ledger.path)
 Assert-Case ($raw.StartsWith($prefix) -and $raw.Length -gt $prefix.Length) 'Failure rewrote or discarded the previous ledger'
 $rows=@([IO.File]::ReadAllLines($ledger.path) | ForEach-Object {$_ | ConvertFrom-Json})
 Assert-Case ($rows.Count -eq 4 -and $rows[3].kind -ceq 'query' -and $rows[3].read_index -eq 2) 'Rejected raw query missing'
 Assert-Case ($rows[3].request.path -ceq $badPath -and $rows[3].cursor -eq 0x20001020) 'Failure lost requested read/cursor'
 Assert-Case (@($rows[3].region.PSObject.Properties).Count -eq 7) 'Failure lost full MBI region attributes'
 if ($modeNumber -eq 4) {Assert-Case ($rows[3].returned_mbi_bytes -eq 0) 'Zero query result was hidden'}
 $artifact=Get-PrimaryQueryLedgerArtifact $ledger
 Assert-Case ($artifact.records -eq 4 -and $artifact.sha256 -ceq (Get-CanvasHash $ledger.path)) 'Partial ledger cannot be hashed'
}
@{passed=$true} | ConvertTo-Json
'''
        self.assertTrue(self.run_ps(body)['passed'])

    def test_multiple_queries_cover_each_requested_byte_and_keep_read_completion(self):
        body=QUERY_MOCK+r'''
foreach ($name in 'Read-PrimaryArtifact','Get-CanvasHash') {Import-Function $name}
function Read-CanvasMemory {param($Handle,$Address,$Count);return ,(New-Object byte[] $Count)}
$owned=@{handle=[IntPtr]123;identity=@{process_id=100;creation_filetime=123}}
$ledger=New-PrimaryQueryLedger $owned @{out_dir=$FixtureRoot;run_id='synthetic'} @{sha256=('b'*64)}
$result=Read-PrimaryArtifact $owned 0x23000800 6000 (Join-Path $FixtureRoot 'pages.raw') $ledger
$rows=@([IO.File]::ReadAllLines($ledger.path) | ForEach-Object {$_ | ConvertFrom-Json})
Assert-Case ($rows.Count -eq 4 -and $rows[1].cursor -eq 0x23000800 -and $rows[2].cursor -eq 0x23001000) 'Read gap, missing raw query or wrong query order'
Assert-Case ($rows[1].query_index -eq 1 -and $rows[2].query_index -eq 2 -and $rows[3].kind -ceq 'read') 'Read completion before full coverage'
Assert-Case ($rows[3].artifact.sha256 -ceq $result.sha256 -and $rows[3].artifact.bytes -eq 6000) 'Ledger RPM artifact differs'
Expect-Failure {New-PrimaryQueryLedger $owned @{out_dir=$FixtureRoot} @{}} 'Existing ledger cannot be overwritten'
@{passed=$true} | ConvertTo-Json
'''
        self.assertTrue(self.run_ps(body)['passed'])

    def test_actual_host_certificate_matches_independent_python_reconstruction(self):
        import modal_slots_primary_capture as consumer
        body=actual_snapshot_fixture().replace('@{passed=$true} | ConvertTo-Json',r'''
$rows=@([IO.File]::ReadAllLines($r.query_ledger.path) | ForEach-Object {$_ | ConvertFrom-Json})
@{regions=$r.regions;rows=$rows} | ConvertTo-Json -Depth 20
''')
        report=self.run_ps(body)
        self.assertEqual(consumer.region_certificate([r['region'] for r in report['rows'] if r['kind']=='query'],4096),
                         report['regions'])

    def test_partial_ledger_is_hash_bound_when_snapshot_throws(self):
        body=lifecycle().replace("$script:Calls.Add('read_primary')",r'''
$script:Calls.Add('read_primary')
$ledger=Join-Path $Plan.out_dir 'primary-query-ledger.jsonl'
[IO.File]::WriteAllText($ledger,"{~BT~"kind~BT~":~BT~"query~BT~",~BT~"returned_mbi_bytes~BT~":0}~BT~n")
if ($Mode -eq 'primary_failure') {throw 'Synthetic failed query before snapshot return'}
''')
        body=body.replace("Assert-Case ($null -ne $result.png -and (Test-Path (Join-Path $outDir 'surface.png'))) 'Raw diagnostic was not converted'",
            "Assert-Case ($null -eq $result.png -and (Test-Path (Join-Path $outDir 'capture-1/surface.raw'))) 'Partial raw was lost or prematurely accepted'")
        body+=r'''
Assert-Case (-not $result.passed -and $null -eq $result.snapshot) 'Failed query returned a completed snapshot'
Assert-Case ($result.query_ledgers.Count -eq 1) 'Failed-before-return query ledger not retained'
$retained=$result.query_ledgers[0]
Assert-Case ($retained.sha256 -ceq (Get-CanvasHash $retained.path) -and $retained.bytes -eq (Get-Item $retained.path).Length) 'Partial query ledger hash/count differs'
Assert-Case ($result.failures -contains 'Synthetic failed query before snapshot return') 'Original query failure lost'
'''
        self.assertTrue(self.run_ps(body,'primary_failure')['passed'])

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
