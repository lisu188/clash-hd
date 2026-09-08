"""Offline owned-modal host fixtures; no game/debugger or native process calls."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from test_framed_screen_capture import PRELUDE, PATHS, ORCHESTRATION as OLD_ORCHESTRATION, PS
from test_framed_minimap_scroll_capture import QUOTING, MEMORY

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "scripts/cdb/run_framed_modal_canvas_capture.ps1"

COMMON = r'''
$offsets=@{phase=0;physical=4;native=8;saved_render=12;root_esp=16;owner_tid=20;enter_status=24;mirror_status=28;leave_status=32;
 fault=36;allocations=40;frees=44;mirrors=48;pending_header=52;pending_pixels=56;native_pixels=60;physical_pixels=64}
$plan=@{stage='fixture-framed-modalcanvas-validation';resolution='800x600';route='hospital';width=800;height=600;
 candidate_sha256=('a'*64);original_sha256=('b'*64);trace_sha256=('c'*64);probe_sha256=('d'*64);
 canvas_state_va=0x580000;canvas_state_offsets=$offsets;stop_va=0x43de53}
function New-Report {
 $v=@{state=0x580000;event='READY';phase=1;tid=123;eip=0x43de53;esp=0x100000;root_esp=0x100450;
 physical=0x120000;native=0x140000;physical_pixels=0x4000000;native_pixels=0x5000000;allocations=1;frees=0;
 mirrors=3;enter_status=1;mirror_status=1;leave_status=0;fault=0;native_width=640;native_height=480;
 physical_width=800;physical_height=600;native_com=0}
 return @{schema='clash95_framed_modal_canvas_trace_v1';passed=$true;ready_for_host_capture=$true;
 stage=$plan.stage;resolution=$plan.resolution;route=$plan.route;candidate_sha256=$plan.candidate_sha256;
 source=@{original_sha256=$plan.original_sha256;generated_probe_sha256=$plan.probe_sha256;validator_sha256=$plan.trace_sha256;log_raw_sha256=('e'*64)};
 initial_map_trace=@{passed=$true};modal_sequence=@{sequence_passed=$true;raw_records=@(@{marker='MCAP_CANVAS';values=$v})};
 surface=@{surface=0x120000;route='hospital';width=800;height=600;base=0x4000000;bytes=480000;tid=123;eip=0x43de53;esp=0x100000}}
}
'''

PURE = COMMON + r'''
foreach ($name in @('Test-CanvasModalReady','Assert-CanvasSurface')) {Import-Function $name}
foreach ($text in @('',"SURFDUMP_HOST_READY~BT~n","MODAL_SURFDUMP_HOST_READY~BT~n",'MCAP_SURFDUMP_HOST_READY',
 "0:000> MCAP_SURFDUMP_HOST_READY~BT~n","MCAP_SURFDUMP_HOST_READY x~BT~n")) {
 Assert-Case (-not (Test-CanvasModalReady $text)) 'legacy/invalid readiness accepted'
}
Assert-Case (Test-CanvasModalReady "MCAP_SURFDUMP_HOST_READY~BT~r~BT~n") 'new complete readiness rejected'
$r=New-Report;$result=Assert-CanvasSurface $r $plan
Assert-Case ($result.surface.surface -eq 0x120000 -and $result.canvas.native -eq 0x140000) 'physical/native distinction lost'
foreach ($case in @(@('schema','clash95_framed_screen_trace_v1'),@('stage','old'),@('passed','true'),
 @('candidate_sha256',('f'*64)),@('ready_for_host_capture',$false),@('resolution','1024x768'))) {
 $r=New-Report;$r[$case[0]]=$case[1];Expect-Failure {Assert-CanvasSurface $r $plan} ('trace '+$case[0])
}
foreach ($key in @('original_sha256','generated_probe_sha256','validator_sha256','log_raw_sha256')) {
 $r=New-Report;$r.source[$key]='bad';Expect-Failure {Assert-CanvasSurface $r $plan} ('source '+$key)
}
foreach ($case in @(@('phase',0),@('physical',0x140000),@('native',0x120000),@('native',0x51d4c0),
 @('physical_pixels',0x5000000),@('native_pixels',0x4000000),@('allocations',2),@('frees',1),@('fault',1),@('enter_status',0),
 @('mirror_status',0),@('leave_status',1),@('mirrors',2),@('native_width',800),@('native_height',600),@('native_com',1),
 @('physical_width',640),@('physical_height',480),@('state',0x580004),@('tid',124),@('eip',0x43de54),@('esp',0x100004),
 @('native_pixels',4294967290),@('phase','1'))) {
 $r=New-Report;$r.modal_sequence.raw_records[0].values[$case[0]]=$case[1]
 Expect-Failure {Assert-CanvasSurface $r $plan} ('canvas '+$case[0])
}
$r=New-Report;$r.modal_sequence.raw_records+= $r.modal_sequence.raw_records[0]
Expect-Failure {Assert-CanvasSurface $r $plan} 'duplicate READY'
$r=New-Report;$r.modal_sequence.raw_records=@()
Expect-Failure {Assert-CanvasSurface $r $plan} 'missing READY'
$r=New-Report;$plan.canvas_state_offsets.physical=8
Expect-Failure {Assert-CanvasSurface $r $plan} 'shifted source state offset'
@{passed=$true} | ConvertTo-Json
'''

CAPTURE = COMMON + r'''
foreach ($name in @('Assert-CanvasSurface','Save-CanvasSnapshot','Get-CanvasHash')) {Import-Function $name}
$script:Calls=New-Object 'Collections.Generic.List[string]'
$script:States=0
function Read-CanvasMemory {
 param($Handle,$Address,$Count)
 $script:Calls.Add(('{0}:{1}' -f $Address,$Count))
 $data=New-Object byte[] $Count
 if ($Address -eq $plan.canvas_state_va) {
  $script:States++
  $values=@{phase=1;physical=0x120000;native=0x140000;root_esp=0x100450;owner_tid=123;enter_status=1;mirror_status=1;
   leave_status=0;fault=0;allocations=1;frees=0;mirrors=3;pending_header=0;pending_pixels=0;native_pixels=0x5000000;physical_pixels=0x4000000}
  if ($Mode -eq 'bad_state') {$values.fault=1}
  if ($Mode -eq 'changed_state' -and $script:States -eq 2) {$values.saved_render=99}
  foreach ($key in $values.Keys) {[BitConverter]::GetBytes([uint32]$values[$key]).CopyTo($data,$offsets[$key])}
 } elseif ($Address -eq 0x5202e0) {
  $value=if ($Mode -eq 'e0_physical') {0x120000} else {0x140000}
  [BitConverter]::GetBytes([uint32]$value).CopyTo($data,0)
 } elseif ($Count -eq 188) {
  $native=$Address -eq 0x140000
  $width=if ($native) {640} else {800};$height=if ($native) {480} else {600}
  $pixels=if ($native) {0x5000000} else {0x4000000}
  if ($Mode -eq 'bad_header' -and -not $native) {$width=640}
  if ($Mode -eq 'native_hd' -and $native) {$width=800}
  if ($Mode -eq 'changed_header' -and $script:States -eq 2 -and -not $native) {$data[40]=7}
  [BitConverter]::GetBytes([uint16]$width).CopyTo($data,0);[BitConverter]::GetBytes([uint16]$height).CopyTo($data,2)
  [BitConverter]::GetBytes([uint32]$pixels).CopyTo($data,4);[BitConverter]::GetBytes([uint32]0x50ee24).CopyTo($data,184)
 } else {$data[0]=7;$data[-1]=9}
 return ,$data
}
$evidence=Assert-CanvasSurface (New-Report) $plan
$path=Join-Path $FixtureRoot 'surface.raw'
if ($Mode -eq 'normal') {
 $result=Save-CanvasSnapshot @{handle=[IntPtr]123;identity=@{process_id=200}} $evidence $path $plan
 $expected='5767168:128,5374688:4,1179648:188,1310720:188,67108864:480000,83886080:307200,5767168:128,5374688:4,1179648:188,1310720:188'
 Assert-Case (($script:Calls -join ',') -ceq $expected) 'state/E0/headers + physical/native pixels + repeat read order'
 Assert-Case ($result.pixel_reads -eq 1 -and $result.native.pixel_reads -eq 1 -and $result.state_reads -eq 2 -and $result.physical_header_reads -eq 2 -and $result.native_header_reads -eq 2) 'read counts differ'
 Assert-Case ($result.native.bytes -eq 307200 -and $result.native.pitch -eq 640 -and $result.pitch -eq 800 -and $result.physical -eq 0x120000 -and $result.native.surface -eq 0x140000) 'physical/native raw labels differ'
 Assert-Case ((Get-Item $path).Length -eq 480000 -and (Get-Item $result.native.path).Length -eq 307200 -and (Test-Path (Join-Path $FixtureRoot 'native-surface.header.bin'))) 'paired raw/header missing'
} else {
 Expect-Failure {Save-CanvasSnapshot @{handle=[IntPtr]123} $evidence $path $plan} 'actual read mismatch'
 if ($Mode -in @('changed_state','changed_header')) {
  Assert-Case ((Test-Path $path) -and (Test-Path (Join-Path $FixtureRoot 'native-surface.raw'))) 'failure removed captured raw'
 } else {
  Assert-Case ($script:Calls.Count -eq 4 -and -not (Test-Path $path)) 'unsafe state/header reached pixels'
 }
}
@{passed=$true;calls=@($script:Calls)} | ConvertTo-Json
'''


def orchestration():
    """Adapt existing mocked lifecycle, keeping new production entry unsourced."""
    text = OLD_ORCHESTRATION.replace("Framed", "Canvas")
    text = text.replace("'Assert-CanvasSurface',", "")
    text = text.replace("'Read-CanvasLog'", "'Read-CanvasLog','Read-CanvasLogBytes','Get-CanvasBytesHash'")
    text = text.replace("MODAL_SURFDUMP_HOST_READY", "MCAP_SURFDUMP_HOST_READY")
    text = text.replace("trace=$inputPath;trace_sha256=$hash;", "trace=$inputPath;trace_sha256=$hash;producer=$inputPath;producer_sha256=$hash;")
    text = text.replace("return @{passed=$true;ready_for_host_capture=$true;surface=", "return @{passed=$true;source=@{log_raw_sha256=(Get-CanvasHash $script:LogPath)};ready_for_host_capture=$true;surface=")
    text = text.replace("$script:Calls.Add('parse')", r"""
$script:Calls.Add('parse')
$count=@($script:Calls | Where-Object {$_ -eq 'parse'}).Count
if ($count -eq 2 -and $Mode -eq 'final_prefix') {[IO.File]::WriteAllText($script:LogPath,"replacement synthetic log~BT~n")}
""")
    text = text.replace("if ($Mode -eq 'parse_failure')", "if ($Mode -eq 'parse_failure' -or ($count -eq 2 -and $Mode -eq 'final_trace'))")
    text = text.replace("log_raw_sha256=(Get-CanvasHash $script:LogPath)", "log_raw_sha256=$(if ($count -eq 2 -and $Mode -eq 'final_hash') {'f'*64} else {Get-CanvasHash $script:LogPath})")
    text = text.replace("($Mode -ne 'cleanup_failure')", "($Mode -notin @('cleanup_failure','final_trace','final_prefix','final_hash'))")
    # Schema and live-read safety have independent actual-function cases above.
    boundary = r'''
function Assert-CanvasSurface {
 param($Report,$Plan)
 if (-not $Report.passed) {throw 'strict fixture trace rejection'}
 return $Report.surface
}
'''
    return boundary + text


class ModalCanvasHostTests(unittest.TestCase):
    def run_ps(self, body, mode="normal"):
        with tempfile.TemporaryDirectory(prefix="clash-modal-canvas-host-") as directory:
            folder = Path(directory); script = folder / "fixture.ps1"
            script.write_text(PRELUDE + body.replace("~BT~", chr(96)), encoding="utf-8-sig")
            result = subprocess.run(
                [str(PS), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script),
                 "-HostPath", str(HOST), "-FixtureRoot", str(folder), "-Python", sys.executable,
                 "-Converter", str(ROOT / "tools/cdb_surface_dump_to_png.py"), "-Mode", mode],
                capture_output=True, text=True, encoding="utf-8", timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(result.stdout)

    def test_paths_keep_new_isolated_outputs(self):
        self.assertTrue(self.run_ps(PATHS.replace("Framed", "Canvas"))["passed"])

    def test_strict_canvas_readiness_source_and_physical_identity(self):
        self.assertTrue(self.run_ps(PURE)["passed"])

    def test_paired_capture_and_changed_state_header_rejection(self):
        for mode in ("normal", "bad_state", "e0_physical", "bad_header", "native_hd", "changed_state", "changed_header"):
            with self.subTest(mode=mode):
                self.assertTrue(self.run_ps(CAPTURE, mode)["passed"])

    def test_native_declarations_compile_and_quiet_argv(self):
        self.assertTrue(self.run_ps(QUOTING.replace("Scroll", "Canvas"))["passed"])

    def test_readprocessmemory_exact_pointer_sized_count(self):
        self.assertTrue(self.run_ps(MEMORY.replace("Scroll", "Canvas"))["passed"])

    def test_dry_run_no_runtime_or_files(self):
        self.assertTrue(self.run_ps(orchestration(), "dry_run")["passed"])

    def test_full_mocked_lifecycle_and_original_map_readiness_ignored(self):
        for mode in ("normal", "early_map"):
            with self.subTest(mode=mode):
                self.assertTrue(self.run_ps(orchestration(), mode)["passed"])

    def test_mocked_failures_keep_exact_cleanup_and_diagnostic_png(self):
        for mode in ("parse_failure", "ambiguous", "partial_start_failure", "start_failure", "cleanup_failure",
                     "final_trace", "final_prefix", "final_hash"):
            with self.subTest(mode=mode):
                self.assertTrue(self.run_ps(orchestration(), mode)["passed"])

    def test_python_validator_deadline_is_enforced_and_json_arguments_preserved(self):
        body = r'''
foreach ($name in @('Invoke-CanvasPythonJson','ConvertTo-CanvasArgument')) {Import-Function $name}
$args=@('-c',"import json,sys;print(json.dumps({'value':sys.argv[1]}))",'a"quoted"\trailing\')
$r=Invoke-CanvasPythonJson $Python $args -TimeoutMilliseconds 5000
Assert-Case ($r.value -ceq 'a"quoted"\trailing\') 'Python argv JSON round trip'
$watch=[Diagnostics.Stopwatch]::StartNew()
Expect-Failure {Invoke-CanvasPythonJson $Python @('-c','import time;time.sleep(30)') -TimeoutMilliseconds 100} 'validator timeout'
Assert-Case ($watch.Elapsed.TotalSeconds -lt 7) 'stuck validator exceeded bounded kill wait'
$r=Invoke-CanvasPythonJson $Python @('-c',"import json,sys;print(json.dumps({'passed':False}));sys.exit(2)") -PermitFailure
Assert-Case ($r.passed -is [bool] -and -not $r.passed) 'honest failed report lost'
@{passed=$true} | ConvertTo-Json
'''
        self.assertTrue(self.run_ps(body)["passed"])

    @unittest.skipUnless(Path("C:/Clash/clash95.exe").is_file(), "read-only original unavailable")
    def test_actual_canonical_trace_schema_reaches_only_physical_canvas(self):
        import test_framed_modal_canvas_trace as fixture
        fixture.FullBindingTests.setUpClass()
        item = fixture.FullBindingTests
        report = fixture.trace.evaluate_trace(item.log, original=item.original, candidate=item.candidate,
                                             packet=item.packet, generated_probe=item.compiled.encode("ascii"))
        self.assertTrue(report["passed"], report["failures"])
        report["source"]["log_raw_sha256"] = hashlib.sha256(item.log.encode()).hexdigest()
        packet = item.packet
        plan = dict(stage=packet["stage"], resolution=packet["resolution"], route=packet["route"]["name"],
                    width=800, height=600, candidate_sha256=packet["candidate_sha256"],
                    original_sha256=packet["original_sha256"], trace_sha256=report["source"]["validator_sha256"],
                    probe_sha256=report["source"]["generated_probe_sha256"], canvas_state_va=packet["canvas_state_va"],
                    canvas_state_offsets=packet["canvas_state_offsets"], stop_va=packet["stop_va"])
        with tempfile.TemporaryDirectory(prefix="clash-canvas-real-schema-") as directory:
            folder = Path(directory)
            (folder / "trace.json").write_text(json.dumps(report))
            (folder / "plan.json").write_text(json.dumps(plan))
            body = r'''
Import-Function 'Assert-CanvasSurface'
$r=[IO.File]::ReadAllText('~PATH~/trace.json') | ConvertFrom-Json
$p=[IO.File]::ReadAllText('~PATH~/plan.json') | ConvertFrom-Json
$result=Assert-CanvasSurface $r $p
Assert-Case ($result.surface.surface -eq $result.canvas.physical -and $result.surface.surface -ne $result.canvas.native -and $result.surface.width -eq 800) 'actual producer fields selected native instead of physical'
$r.stage=$r.stage.Replace('-framed-modalcanvas-validation','-framed-validation')
Expect-Failure {Assert-CanvasSurface $r $p} 'legacy stage confusion'
@{passed=$true} | ConvertTo-Json
'''
            self.assertTrue(self.run_ps(body.replace("~PATH~", folder.as_posix()))["passed"])


if __name__ == "__main__":
    unittest.main()
