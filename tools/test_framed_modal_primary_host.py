"""AST-isolated primary host fixtures; no game, debugger, input or capture.

One regression launches an owned no-window synthetic x86 CLR helper and reads
its module list from64-bit Windows PowerShell. Other native boundaries are
managed stand-ins. Neither case reads or executes a game/proxy binary.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_framed_screen_capture import PRELUDE,PS,PATHS
import test_framed_modal_canvas_capture as canvas
from test_framed_minimap_scroll_capture import QUOTING,MEMORY

ROOT=Path(__file__).resolve().parents[1]
HOST=ROOT/'scripts/cdb/run_framed_modal_primary_capture.ps1'


def lifecycle(command_error=None):
    text=canvas.orchestration().replace('MCAP_SURFDUMP_HOST_READY','MPRI_HOST_READY')
    text=text.replace("'Read-CanvasLog'", "'Read-CanvasLog','Get-CanvasDebuggerCommandFailure'")
    text=text.replace("$script:Calls.Add('parse')", """
if ($Arguments -contains '--snapshot-manifest') {
 if ($script:Calls.IndexOf('stop_200') -lt 0) {throw 'Secondary primary audit ran before owned cleanup'}
 $script:Calls.Add('audit_primary')
 return @{passed=($Mode -ne 'primary_failure');primary_snapshot=@{cached_primary_snapshot_valid=($Mode -ne 'primary_failure')}}
}
$script:Calls.Add('parse')
""")
    text=text.replace("$script:Prepared=@{packet=@{prepared=$true};probe=$probe;probe_sha256=$probeHash}",
                      "$script:Prepared=@{packet=@{prepared=$true};probe=$probe;probe_sha256=$probeHash;ready_script=$probe;ready_script_sha256=$probeHash}")
    text=text.replace('$bundle=@{plan=$plan;prepared=$script:Prepared}',"""
$plan.primary_ready_path=Join-Path $outDir 'primary-ready.cdb';$plan.primary_ready_sha256=$probeHash
$bundle=@{plan=$plan;prepared=$script:Prepared}
""")
    text=text.replace("'cleanup_failure','final_trace','final_prefix','final_hash'", "'cleanup_failure','final_trace','final_prefix','final_hash','primary_failure','empty_palette'")
    text=text.replace("absent=($Mode -notin @('cleanup_failure','final_trace','final_prefix','final_hash','primary_failure','empty_palette'))",
                      "absent=($Mode -ne 'cleanup_failure')")
    stub=r'''
function Save-PrimarySnapshot {
 param($Owned,$Trace,$Plan,$Prefix)
 $script:Calls.Add('read_primary')
 $path=Join-Path $Plan.out_dir 'primary.raw';[IO.File]::WriteAllBytes($path,(New-Object byte[] 480000))
 $pal=Join-Path $Plan.out_dir 'primary-palette.bin';$colors=New-Object byte[] 1024
 if ($Mode -ne 'empty_palette') {$colors[4]=17}
 [IO.File]::WriteAllBytes($pal,$colors)
 return @{pixels=@{path=$path;bytes=480000;sha256=(Get-CanvasHash $path)};palette_entries=@{path=$pal;bytes=1024;sha256=(Get-CanvasHash $pal)}}
}
'''
    if command_error is not None:
        text=text.replace('"SURFDUMP_READY map`nMPRI_HOST_READY`n"',
                          '"'+command_error+'`nMPRI_HOST_READY`n"')
        text=text.replace("@('parse_failure','ambiguous','partial_start_failure')",
                          "@('parse_failure','ambiguous','partial_start_failure','command_failure')")
        text=text.replace("$debuggerStop=$script:Calls.IndexOf('stop_100');",r'''
Assert-Case ($result.debugger_command_failure.classification -ceq 'debugger_command_failure') 'Command error classified as game evidence'
Assert-Case ($result.debugger_command_failure.line -eq 1 -and (Test-Path $result.debugger_command_failure.log_prefix.path)) 'Actual failed log prefix not retained'
Assert-Case ($script:Calls.IndexOf('parse') -lt 0 -and $script:Calls.IndexOf('read_primary') -lt 0 -and $script:Calls.IndexOf('wait') -lt 0) 'Known debugger error waited or reached capture'
$debuggerStop=$script:Calls.IndexOf('stop_100');''')
    return stub+text


CAPTURE=r'''
foreach ($name in @('Save-PrimarySnapshot','Get-CanvasHash')) {Import-Function $name}
$script:Reads=New-Object 'Collections.Generic.List[string]';$script:Phase=0
$plan=@{out_dir=$FixtureRoot;width=800;height=600;candidate_path='synthetic-candidate.bin';proxy_path=$HostPath;proxy_sha256=(Get-CanvasHash $HostPath)}
$owned=@{handle=[IntPtr]123;identity=@{process_id=100;creation_filetime=123;candidate_sha256=('a'*64)}}
$trace=@{passed=$true;source=@{log_raw_sha256=('b'*64)};primary_sequence=@{passed=$true;ready=@{values=@{
 backend=0x20000000;surface=0x20001000;palette=0x20002000;pixels=0x22000000}}}}
function Get-PrimaryModule {param($Owned,$Plan);return @{base=0x10000000;size=0x30000;path=$HostPath;sha256=$Plan.proxy_sha256}}
function Get-CanvasHandleIdentity {param($Handle,$Id,$Path);return @{creation_filetime=$(if ($Mode -eq 'identity') {124} else {123})}}
function Read-PrimaryArtifact {
 param($Owned,$Address,$Count,$Path,$Regions)
 $script:Reads.Add(('{0}:{1}' -f $Address,$Count));$data=New-Object byte[] $Count
 if ($Address -eq 0x51d4c0) {$script:Phase++}
 if ($Address -eq 0x20001000) {
  [BitConverter]::GetBytes([uint32]0x1001939c).CopyTo($data,0)
  if ($Count -eq 32) {[BitConverter]::GetBytes([uint32]$(if ($Mode -eq 'palette_pointer') {0x20003000} else {0x20002000})).CopyTo($data,28)}
 }
 if ($Address -eq 0x20002000) {
  [BitConverter]::GetBytes([uint32]0x10019340).CopyTo($data,0)
  for ($i=12;$i -lt $Count;$i++) {$data[$i]=[byte]($i%256)}
 }
 if ($Mode -eq 'changed_palette' -and $script:Phase -eq 2 -and $Address -eq 0x20002000) {$data[12]=77}
 if ($Mode -eq 'changed_header' -and $script:Phase -eq 2 -and $Address -eq 0x20000000) {$data[0]=77}
 [IO.File]::WriteAllBytes($Path,$data)
 return @{path=$Path;address=$Address;bytes=$Count;sha256=(Get-CanvasHash $Path);data=$data}
}
if ($Mode -eq 'normal') {
 $r=Save-PrimarySnapshot $owned $trace $plan @{sha256=('b'*64)}
 Assert-Case ($script:Reads.Count -eq 19) 'Expected nine before reads, pixels, nine after reads'
 Assert-Case ($script:Reads[6] -eq '536875008:4' -and $script:Reads[9] -eq '570425344:480000') 'Pointer/count or pixel ordering differs'
 Assert-Case ($r.reads.before.proxy_getpalette.bytes -eq 83 -and $r.reads.after.proxy_getpalette.bytes -eq 83) 'Source getter byte span differs'
 Assert-Case ((Get-Item $r.palette_entries.path).Length -eq 1024 -and [IO.File]::ReadAllBytes($r.palette_entries.path)[0] -eq 12) 'Current attached palette not retained'
 Assert-Case ($r.pixels.bytes -eq 480000 -and $r.game_identity.process_id -eq 100 -and -not $r.manual_input_proof) 'Primary receipt labeling differs'
} else {
 Expect-Failure {Save-PrimarySnapshot $owned $trace $plan @{sha256=('b'*64)}} 'changed primary identities'
 if ($Mode -in @('changed_header','changed_palette','identity')) {Assert-Case (Test-Path (Join-Path $FixtureRoot 'primary.raw')) 'Failed capture raw removed'}
 if ($Mode -eq 'palette_pointer') {Assert-Case (-not (Test-Path (Join-Path $FixtureRoot 'primary.raw'))) 'Unsafe palette reached pixels'}
}
@{passed=$true} | ConvertTo-Json
'''


class PrimaryHostTests(unittest.TestCase):
    def run_ps(self,body,mode='normal'):
        with tempfile.TemporaryDirectory(prefix='clash-primary-host-offline-') as directory:
            root=Path(directory);script=root/'fixture.ps1'
            script.write_text(PRELUDE+body.replace('~BT~',chr(96)),encoding='utf-8-sig')
            r=subprocess.run([str(PS),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),
                '-HostPath',str(HOST),'-FixtureRoot',str(root),'-Python',sys.executable,
                '-Converter',str(ROOT/'tools/cdb_surface_dump_to_png.py'),'-Mode',mode],
                capture_output=True,text=True,encoding='utf-8',timeout=65,creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            return json.loads(r.stdout)

    def test_only_unique_primary_readiness_accepts(self):
        self.assertTrue(self.run_ps(r'''
Import-Function 'Test-CanvasModalReady'
foreach ($line in @('MPRI_HOST_READY',"MCAP_SURFDUMP_HOST_READY~BT~n","SURFDUMP_HOST_READY~BT~n","0:000> MPRI_HOST_READY~BT~n","MPRI_HOST_READY x~BT~n")) {
 Assert-Case (-not (Test-CanvasModalReady $line)) 'unrelated readiness accepted'
}
Assert-Case (Test-CanvasModalReady "MPRI_HOST_READY~BT~r~BT~n") 'exact primary readiness rejected'
@{passed=$true} | ConvertTo-Json
''')['passed'])

    def test_debugger_command_failures_are_not_native_crashes(self):
        self.assertTrue(self.run_ps(r'''
Import-Function 'Get-CanvasDebuggerCommandFailure'
foreach ($line in @('Unable to insert breakpoint 27 at 00000110, Win32 error 0n299',
 'bp27 at 00000110 failed','    ^ Syntax error in command','0:000> Syntax error at expression',
 'Command file execution failed, Win32 error 0n2')) {
 $r=Get-CanvasDebuggerCommandFailure ("prefix~BT~n"+$line+"~BT~n")
 Assert-Case ($r.classification -ceq 'debugger_command_failure' -and $r.line -eq 2 -and $r.text -ceq $line) 'Actual debugger failure not detected'
}
foreach ($line in @('Access violation - code c0000005 (first chance)','MPRI_HOST_READY',
 '0:000> .echo Syntax error','bp110 0047386f ".echo Syntax error; gc"','no syntax error observed')) {
 Assert-Case ($null -eq (Get-CanvasDebuggerCommandFailure $line)) 'Native/normal/echoed line misclassified'
}
@{passed=$true} | ConvertTo-Json
''')['passed'])

    def test_command_errors_fail_before_ready_and_keep_exact_cleanup(self):
        for error in ('Unable to insert breakpoint 27 at 00000110, Win32 error 0n299',
                      'bp27 at 00000110 failed','    ^ Syntax error in command',
                      'Command file execution failed, Win32 error 0n2'):
            with self.subTest(error=error):
                self.assertTrue(self.run_ps(lifecycle(error),'command_failure')['passed'])

    def test_original_path_restrictions_remain(self):
        self.assertTrue(self.run_ps(PATHS.replace('Framed','Canvas'))['passed'])

    def test_current_palette_and_headers_surround_read(self):
        for mode in ('normal','changed_header','changed_palette','palette_pointer','identity'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(CAPTURE,mode)['passed'])

    def test_original_canvas_identity_guard_still_applies(self):
        pure=canvas.PURE.replace('MCAP_SURFDUMP_HOST_READY','MPRI_HOST_READY')
        pure=pure.replace("schema='clash95_framed_modal_canvas_trace_v1';passed=$true", "schema='clash95_framed_modal_canvas_trace_v1';primary_sequence=@{passed=$true};passed=$true")
        self.assertTrue(self.run_ps(pure)['passed'])

    def test_native_types_compile_and_memory_count_is_pointer_sized(self):
        self.assertTrue(self.run_ps(QUOTING.replace('Scroll','Canvas'))['passed'])
        self.assertTrue(self.run_ps(MEMORY.replace('Scroll','Canvas'))['passed'])
        self.assertTrue(self.run_ps(r'''
Import-Function 'Initialize-PrimaryQuery';Initialize-PrimaryQuery
$m=New-Object ModalPrimaryQuery+MBI
Assert-Case ([Runtime.InteropServices.Marshal]::SizeOf($m) -eq $(if ([IntPtr]::Size -eq 8) {48} else {28})) 'VirtualQueryEx layout wrong'
@{passed=$true} | ConvertTo-Json
''')['passed'])

    def test_virtual_query_covers_every_byte_before_read(self):
        self.assertTrue(self.run_ps(r'''
foreach ($name in @('Read-PrimaryArtifact','Get-CanvasHash')) {Import-Function $name}
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ModalPrimaryQuery {
 [StructLayout(LayoutKind.Sequential)] public struct MBI {public IntPtr address,allocation;public uint allocationProtect;public UIntPtr size;public uint state,protect,type;}
 public static int mode=0;
 public static UIntPtr VirtualQueryEx(IntPtr handle,IntPtr address,out MBI info,UIntPtr count) {
  info=new MBI(); info.address=new IntPtr(address.ToInt64() & ~4095L);info.size=new UIntPtr(4096);info.state=0x1000;info.protect=4;
  if(mode==1)info.protect=0x104;if(mode==2)info.state=0x2000;if(mode==3)info.size=UIntPtr.Zero;
  return mode==4?UIntPtr.Zero:count;
 }
}
'@
function Initialize-PrimaryQuery {}
$script:PixelReads=0
function Read-CanvasMemory {param($h,$a,$n);$script:PixelReads++;return ,(New-Object byte[] $n)}
$regions=@{};$p=Join-Path $FixtureRoot 'bounded.raw'
$r=Read-PrimaryArtifact @{handle=[IntPtr]123} 0x20000800 6000 $p $regions
Assert-Case ($regions.Count -eq 2 -and $script:PixelReads -eq 1 -and $r.bytes -eq 6000) 'Full region coverage was not read exactly once'
foreach ($bad in 1..4) {
 [ModalPrimaryQuery]::mode=$bad
 Expect-Failure {Read-PrimaryArtifact @{handle=[IntPtr]123} 0x20000800 6000 $p @{}} 'bad VirtualQueryEx'
}
foreach ($spec in @(@(0,1),@(4294967290,16),@(0x20000000,0))) {
 Expect-Failure {Read-PrimaryArtifact @{handle=[IntPtr]123} $spec[0] $spec[1] $p @{}} 'invalid address/count'
}
Assert-Case ($script:PixelReads -eq 1) 'Invalid regions reached memory read'
@{passed=$true} | ConvertTo-Json
''')['passed'])

    def test_x86_module_enumeration_uses_retained_handle_and_bounded_queries(self):
        self.assertTrue(self.run_ps(r'''
Import-Function 'Get-PrimaryLoadedModules'
Add-Type -TypeDefinition @'
using System;using System.Text;using System.Runtime.InteropServices;
public static class ModalPrimaryModules {
 [StructLayout(LayoutKind.Sequential)] public struct MODULEINFO {public IntPtr baseAddress;public uint imageSize;public IntPtr entryPoint;}
 public static int mode=0,calls=0;
 public static bool EnumProcessModulesEx(IntPtr handle,IntPtr[] modules,uint bytes,out uint needed,uint filter) {
  if(handle.ToInt64()!=123||filter!=1||bytes!=modules.Length*IntPtr.Size)throw new Exception("Retained x86 module query ABI differs");
  calls++;needed=(uint)(2*IntPtr.Size);modules[0]=new IntPtr(0x10000000);modules[1]=new IntPtr(0x20000000);
  if(mode==1&&calls==1)needed=(uint)(129*IntPtr.Size);
  if(mode==2)needed=(uint)(modules.Length*IntPtr.Size+IntPtr.Size);
  if(mode==3)needed=0;if(mode==4)needed=3;if(mode==5)needed=(uint)(5000*IntPtr.Size);
  if(mode==7)modules[1]=modules[0];if(mode==8)modules[0]=IntPtr.Zero;
  return mode!=6;
 }
 public static uint GetModuleFileNameExW(IntPtr handle,IntPtr address,StringBuilder path,uint capacity) {
  if(handle.ToInt64()!=123||capacity!=32768)throw new Exception("Path query ABI differs");
  path.Append(@"C:\ClashTests\synthetic-"+address.ToInt64()+".dll");
  return mode==9?0:mode==10?capacity:(uint)path.Length;
 }
 public static bool GetModuleInformation(IntPtr handle,IntPtr address,out MODULEINFO info,uint bytes) {
  info=new MODULEINFO();info.baseAddress=address;info.imageSize=0x26000;
  if(bytes!=Marshal.SizeOf(info)||handle.ToInt64()!=123)throw new Exception("Module info ABI differs");
  if(mode==12)info.baseAddress=new IntPtr(123);if(mode==13)info.imageSize=0;if(mode==14)info.imageSize=uint.MaxValue;
  return mode!=11;
 }
}
'@
function Initialize-PrimaryModules {}
foreach ($modeNumber in @(0,1)) {
 [ModalPrimaryModules]::mode=$modeNumber;[ModalPrimaryModules]::calls=0
 $rows=@(Get-PrimaryLoadedModules ([IntPtr]123))
 Assert-Case ($rows.Count -eq 2 -and $rows[0].BaseAddress.ToInt64() -eq 0x10000000 -and $rows[1].ModuleMemorySize -eq 0x26000) 'Read-only module metadata differs'
 Assert-Case ([ModalPrimaryModules]::calls -eq ($modeNumber+1)) 'Module list growth was not bounded/retried'
}
foreach ($modeNumber in 2..14) {
 [ModalPrimaryModules]::mode=$modeNumber;[ModalPrimaryModules]::calls=0
 Expect-Failure {Get-PrimaryLoadedModules ([IntPtr]123)} 'invalid enumeration record'
 Assert-Case ([ModalPrimaryModules]::calls -le 4) 'Unbounded module retry'
}
foreach ($bad in @([IntPtr]::Zero,[IntPtr](-1))) {Expect-Failure {Get-PrimaryLoadedModules $bad} 'invalid retained handle'}
@{passed=$true} | ConvertTo-Json
''')['passed'])

    def test_proxy_module_path_hash_uniqueness_and_range_remain_required(self):
        self.assertTrue(self.run_ps(r'''
Import-Function 'Get-PrimaryModule'
$script:hash='b173a9dd4ce772eb5b56f341acdf4b329ed4ffdd638c1fce5cc37dd332804b70'
$script:rows=@([pscustomobject]@{FileName='C:\ClashTests\fixture\DDRAW.dll';BaseAddress=[IntPtr]0x6cdb0000;ModuleMemorySize=0x26000})
function Get-PrimaryLoadedModules {param([IntPtr]$Handle);Assert-Case ($Handle -eq [IntPtr]123) 'Reopened or replaced owned handle';return $script:rows}
function Get-CanvasHash {param($Path);return $script:hash}
$plan=@{proxy_path='C:/ClashTests/fixture/ddraw.dll';proxy_sha256=$script:hash};$owned=@{handle=[IntPtr]123}
$r=Get-PrimaryModule $owned $plan
Assert-Case ($r.base -eq 0x6cdb0000 -and $r.size -eq 0x26000 -and $r.sha256 -ceq $script:hash) 'Exact local proxy was not identified'
$original=$script:rows
$script:rows=@();Expect-Failure {Get-PrimaryModule $owned $plan} 'missing proxy'
$script:rows=@($original[0],$original[0]);Expect-Failure {Get-PrimaryModule $owned $plan} 'duplicate proxy'
$script:rows=@([pscustomobject]@{FileName='C:\ClashTests\other\ddraw.dll';BaseAddress=[IntPtr]0x6cdb0000;ModuleMemorySize=0x26000})
Expect-Failure {Get-PrimaryModule $owned $plan} 'unrelated path'
$script:rows=$original;$script:hash='a'*64;Expect-Failure {Get-PrimaryModule $owned $plan} 'changed disk hash'
$plan.proxy_sha256=$script:hash;Expect-Failure {Get-PrimaryModule $owned $plan} 'arbitrary matching proxy hash'
$script:hash=$r.sha256;$plan.proxy_sha256=$r.sha256
foreach ($range in @(@(0,0x26000),@(0x6cdb0000,0),@(4294963200,8192))) {
 $script:rows=@([pscustomobject]@{FileName=$plan.proxy_path;BaseAddress=[IntPtr]([long]$range[0]);ModuleMemorySize=$range[1]})
 Expect-Failure {Get-PrimaryModule $owned $plan} 'invalid proxy image bounds'
}
@{passed=$true} | ConvertTo-Json
''')['passed'])

    def test_actual_owned_x86_module_is_visible_to_reviewed_64bit_host(self):
        self.assertTrue(self.run_ps(r'''
foreach ($name in @('Initialize-PrimaryModules','Get-PrimaryLoadedModules','ConvertTo-CanvasArgument')) {Import-Function $name}
Assert-Case ([IntPtr]::Size -eq 8) 'This regression requires the actual reviewed64-bit Windows PowerShell host'
$dll=Join-Path $FixtureRoot 'synthetic-module.dll';$library=Join-Path $FixtureRoot 'library.cs'
$exe=Join-Path $FixtureRoot 'synthetic-child.exe';$source=Join-Path $FixtureRoot 'child.cs'
[IO.File]::WriteAllText($library,'public class EmptySyntheticModule {}')
[IO.File]::WriteAllText($source,@'
using System;using System.Runtime.InteropServices;
class Child {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern IntPtr LoadLibraryW(string path);
 static int Main(string[] args){if(IntPtr.Size!=4)return 2;IntPtr module=LoadLibraryW(args[0]);if(module==IntPtr.Zero)return 3;Console.WriteLine(module.ToInt64());Console.ReadLine();return 0;}
}
'@)
$compiler='C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe'
& $compiler /nologo /target:library /platform:x86 ('/out:'+$dll) $library | Out-Null
Assert-Case ($LASTEXITCODE -eq 0) 'Synthetic x86 DLL compile failed'
& $compiler /nologo /platform:x86 ('/out:'+$exe) $source | Out-Null
Assert-Case ($LASTEXITCODE -eq 0) 'Synthetic x86 child compile failed'
$info=New-Object Diagnostics.ProcessStartInfo;$info.FileName=$exe;$info.Arguments=ConvertTo-CanvasArgument $dll
$info.UseShellExecute=$false;$info.CreateNoWindow=$true;$info.WindowStyle='Hidden'
$info.RedirectStandardInput=$true;$info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
$process=New-Object Diagnostics.Process;$process.StartInfo=$info;$started=$false;$terminated=$false;$code=$null
try {
 $started=$process.Start();Assert-Case $started 'Synthetic process did not start'
 $line=$process.StandardOutput.ReadLineAsync();Assert-Case ($line.Wait(5000)) 'Synthetic module load deadline'
 $expectedBase=[long]$line.GetAwaiter().GetResult();Assert-Case ($expectedBase -gt 0) 'Synthetic module did not load'
 $legacy=@($process.Modules | Where-Object {$_.FileName -ieq $dll})
 Assert-Case ($legacy.Count -eq 0) 'Cross-bitness defect no longer reproduced by legacy Process.Modules'
 $actual=@(Get-PrimaryLoadedModules $process.Handle | Where-Object {$_.FileName -ieq $dll})
 Assert-Case ($actual.Count -eq 1 -and $actual[0].BaseAddress.ToInt64() -eq $expectedBase -and $actual[0].ModuleMemorySize -gt 0) 'Explicit x86 query omitted or misidentified the actual owned module'
} finally {
 if ($started) {
  if (-not $process.HasExited) {$process.StandardInput.WriteLine('done');$process.StandardInput.Flush();if (-not $process.WaitForExit(5000)) {$process.Kill();[void]$process.WaitForExit(5000)}}
  $terminated=$process.HasExited;if ($terminated) {$code=$process.ExitCode}
 }
 $process.Dispose()
}
Assert-Case ($terminated -and $code -eq 0) 'Owned synthetic process did not exit cleanly'
@{passed=$true;synthetic_exited=$terminated;handle_disposed=$true;old_module_count=$legacy.Count;new_module_count=$actual.Count} | ConvertTo-Json
''')['passed'])

    def test_owned_handle_includes_query_information_without_writes(self):
        self.assertTrue(self.run_ps(r'''
foreach ($name in @('Find-CanvasOwnedChildren','Select-CanvasChildren')) {Import-Function $name}
Add-Type -TypeDefinition @'
using System;
public static class CanvasScreenNative {
 public static uint requested;
 public static IntPtr OpenProcess(uint access,bool inherit,uint id) {requested=access;return new IntPtr(123);}
 public static bool CloseHandle(IntPtr handle) {return true;}
}
'@
$script:stamp=[datetime]'2026-09-06T01:00:00Z';$script:path='C:\ClashTests\fixture\synthetic.bin'
function Get-CimInstance {param($Class,$Filter,$OperationTimeoutSec);return [pscustomobject]@{ProcessId=200;ParentProcessId=100;ExecutablePath=$script:path;CreationDate=$script:stamp}}
function Get-CanvasHandleIdentity {param($Handle,$Number,$Path);return @{process_id=$Number;path=$Path;creation_utc=$script:stamp.ToString('o')}}
function Get-CanvasHash {param($Path);return ('a'*64)}
$owned=@{}
Find-CanvasOwnedChildren @{candidate_path=$script:path;candidate_sha256=('a'*64)} @{identity=@{process_id=100}} ($script:stamp.AddSeconds(-1)) $owned
Assert-Case ($owned.Count -eq 1 -and [CanvasScreenNative]::requested -eq 0x101411) 'Retained child lacks required VirtualQueryEx access'
Assert-Case (([CanvasScreenNative]::requested -band (0x20 -bor 0x8)) -eq 0) 'Unexpected process memory-write/operation rights'
@{passed=$true} | ConvertTo-Json
''')['passed'])

    def test_dry_run_no_runtime_or_output(self):
        self.assertTrue(self.run_ps(lifecycle(),'dry_run')['passed'])

    def test_mocked_full_capture_and_cleanup_failures_keep_raw(self):
        for mode in ('normal','early_map','parse_failure','ambiguous','partial_start_failure','start_failure',
                     'cleanup_failure','final_trace','final_prefix','final_hash','primary_failure','empty_palette'):
            with self.subTest(mode=mode):self.assertTrue(self.run_ps(lifecycle(),mode)['passed'])

    def test_preserved_native_lifecycle_function_bodies(self):
        # AST comparison, not a code-string surrogate for behavior. The other
        # tests execute these actual functions with native boundaries replaced.
        self.assertTrue(self.run_ps(r'''
$oldPath=Join-Path ([IO.Path]::GetDirectoryName($HostPath)) 'run_framed_modal_canvas_capture.ps1'
$e=$null;$t=$null;$old=[Management.Automation.Language.Parser]::ParseFile($oldPath,[ref]$t,[ref]$e)
foreach ($name in @('Start-CanvasHidden','Stop-CanvasOwned','Close-CanvasDesktop','Read-CanvasMemory','Save-CanvasSnapshot','Get-CanvasHandleIdentity','Resolve-CanvasPath')) {
 $a=$ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true)
 $b=$old.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true)
 Assert-Case ($a.Count -eq 1 -and $b.Count -eq 1 -and $a[0].Extent.Text.Replace("~BT~r~BT~n","~BT~n") -ceq $b[0].Extent.Text.Replace("~BT~r~BT~n","~BT~n")) ('frozen lifecycle changed '+$name)
}
@{passed=$true} | ConvertTo-Json
''')['passed'])


if __name__=='__main__':unittest.main(verbosity=2)
