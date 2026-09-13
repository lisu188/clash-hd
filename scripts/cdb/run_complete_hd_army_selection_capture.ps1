<# Controlled complete-HD native army selection on an owned hidden desktop.
   Dry-run preparation is read-only. Only -Execute initializes native APIs.
   The source-bound native trace, stopped pixels and cleanup are separate from
   ordinary input, visible composition, frame audits and stable promotion.
#>
[CmdletBinding()]
param(
    [string]$Original='C:\Clash\clash95.exe',
    [Parameter(Mandatory=$true)][string]$InputCandidate,
    [Parameter(Mandatory=$true)][string]$CandidateManifest,
    [Parameter(Mandatory=$true)][string]$ProxyBuildManifest,
    [Parameter(Mandatory=$true)][string]$WorkDir,
    [Parameter(Mandatory=$true)][string]$CandidateDir,
    [Parameter(Mandatory=$true)][string]$OutDir,
    [ValidateSet('800x600','1024x768','1280x720','1280x960','1920x1080','802x602')]
    [string]$Resolution='1024x768',
    [string]$Python=(Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'),
    [string]$Cdb='C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe',
    [switch]$Execute
)
$ErrorActionPreference='Stop'
$OutputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=$OutputEncoding
$script:RepoRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$script:HostPath=$PSCommandPath

# Lifecycle and bounded offline-child helpers copied from
# run_modal_slots_barracks_capture.ps1 SHA256 4365e383a4c25d8b86000ac66f6350e148bddf26bcf36232a9ae96215c61c778.
# They are part of this host identity; no other runtime harness is executed.
# Log reads additionally enforce the 16 MiB limit while reading, including
# pre-readiness polling and a concurrently growing debugger log.
function Get-CanvasHash {
    param([string]$Path)
    $stream = [IO.File]::OpenRead($Path)
    $hash = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
    finally { $stream.Dispose(); $hash.Dispose() }
}

function Get-CanvasCandidateName {
    param([string]$Directory, [string]$Route, [string]$Resolution)
    $hash=[Security.Cryptography.SHA256]::Create()
    try {
        $digest=([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($Directory.ToLowerInvariant())))).Replace('-','').ToLowerInvariant()
        return ('framed-modal-canvas-' + $Route + '-' + $Resolution + '-' + $digest.Substring(0,16) + '.exe')
    } finally { $hash.Dispose() }
}

function Resolve-CanvasPath {
    param([string]$Path, [string]$Root = '', [ValidateSet('file','directory','new')][string]$Kind)
    if ($Path -notmatch '^[A-Za-z]:[\\/]' -or $Path.Substring(2) -match '[:"\r\n;\x00]' -or $Path.StartsWith('\\')) {
        throw 'Capture paths must be absolute local paths without command delimiters.'
    }
    $full = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    if ($Root -and -not $full.StartsWith(([IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'), [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside required root $Root"
    }
    # Resolve all existing ancestors, rejecting junction/symlink escape and file ancestors.
    $walk = $full
    while ($walk) {
        if (Test-Path -LiteralPath $walk) {
            $item = Get-Item -LiteralPath $walk -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse-point capture paths are unsupported.' }
            if ($walk -ne $full -and -not $item.PSIsContainer) { throw 'A path ancestor is a file.' }
        }
        $walk = [IO.Path]::GetDirectoryName($walk)
    }
    if ($Kind -eq 'new') {
        if (Test-Path -LiteralPath $full) { throw 'CandidateDir and OutDir must be new, nonexistent directories.' }
    } elseif (-not (Test-Path -LiteralPath $full -PathType $(if ($Kind -eq 'file') {'Leaf'} else {'Container'}))) {
        throw "Required $Kind is missing: $full"
    }
    return $full
}

function Invoke-CanvasPythonJson {
    param([string]$Python, [string[]]$Arguments, [switch]$PermitFailure,
        [ValidateRange(1,120000)][int]$TimeoutMilliseconds=120000)
    $start=New-Object Diagnostics.ProcessStartInfo
    $start.FileName=$Python;$start.Arguments=((@('-B')+$Arguments | ForEach-Object {ConvertTo-CanvasArgument $_}) -join ' ')
    $start.UseShellExecute=$false;$start.CreateNoWindow=$true
    $start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
    $start.StandardOutputEncoding=[Text.UTF8Encoding]::new($false);$start.StandardErrorEncoding=[Text.UTF8Encoding]::new($false)
    $process=New-Object Diagnostics.Process;$process.StartInfo=$start
    try {
        if (-not $process.Start()) {throw 'Offline Python validator did not start.'}
        $stdout=$process.StandardOutput.ReadToEndAsync();$stderr=$process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutMilliseconds)) {
            $process.Kill()
            if (-not $process.WaitForExit(5000)) {throw 'Timed-out Python validator termination was not confirmed.'}
            throw 'Offline Python validation exceeded its bounded deadline.'
        }
        $exitCode=$process.ExitCode;$output=$stdout.GetAwaiter().GetResult();$errorText=$stderr.GetAwaiter().GetResult()
        try {$result=$output | ConvertFrom-Json}
        catch {throw "Offline Python command did not emit valid JSON (exit $exitCode). $errorText"}
        if (-not $result) {throw 'Offline Python command returned no report.'}
        if ($exitCode -ne 0 -and -not $PermitFailure) {
            $childFailures=@()
            if ($null -ne $result.PSObject.Properties['failures'] -and $null -ne $result.failures) {
                $childFailures=@($result.failures)
            }
            $detail=($childFailures | ForEach-Object {
                if ($_ -is [string]) {$_} else {$_ | ConvertTo-Json -Compress -Depth 10}
            }) -join '; '
            $exception=[InvalidOperationException]::new("Offline Python command failed with exit $exitCode. $detail $errorText")
            # Preserve the child verdict without copying unrelated, potentially
            # multi-megabyte prepared probe/packet fields into a failure receipt.
            $exception.Data['CanvasPythonFailure']=@{exit_code=$exitCode;failures=$childFailures;stderr=$errorText}
            throw $exception
        }
        return $result
    } finally {$process.Dispose()}
}

function Read-CanvasLog {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return '' }
    return [Text.Encoding]::UTF8.GetString((Read-CanvasLogBytes $Path))
}

function Read-CanvasLogBytes {
    param([string]$Path)
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    $copy=New-Object IO.MemoryStream
    try {
        if ($stream.Length -gt 16777216) { throw 'Debugger log exceeds the frozen parser bound.' }
        $buffer=New-Object byte[] 8192
        while (($read=$stream.Read($buffer,0,[Math]::Min($buffer.Length,16777217-[int]$copy.Length))) -gt 0) {
            if ($copy.Length+$read -gt 16777216) {throw 'Debugger log exceeds the frozen parser bound.'}
            $copy.Write($buffer,0,$read)
        }
        return ,$copy.ToArray()
    } finally { $copy.Dispose();$stream.Dispose() }
}

function Get-CanvasBytesHash {
    param([byte[]]$Bytes)
    $hash=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() }
    finally { $hash.Dispose() }
}

function Select-CanvasChildren {
    param($Rows, [int]$CdbProcessId, [string]$CandidatePath, [datetime]$StartedAt)
    $selected = @()
    foreach ($row in $Rows) {
        if ([int]$row.ParentProcessId -eq $CdbProcessId -and $row.ExecutablePath -and
            [IO.Path]::GetFullPath([string]$row.ExecutablePath) -ieq $CandidatePath) {
            if (([datetime]$row.CreationDate).ToUniversalTime() -lt $StartedAt.ToUniversalTime() -or [int]$row.ProcessId -le 0) { throw 'Child process identity predates this launch.' }
            $selected += $row
        }
    }
    return $selected
}

function Initialize-CanvasNative {
    if ('CanvasScreenNative' -as [type]) { return }
    Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class CanvasScreenNative {
 [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] public struct STARTUPINFO {
  public int cb; public string reserved, desktop, title; public uint x,y,xSize,ySize,xChars,yChars,fill,flags;
  public short show, reserved2; public IntPtr reservedPtr, input, output, error;
 }
 [StructLayout(LayoutKind.Sequential)] public struct PROCESS_INFORMATION { public IntPtr process, thread; public uint processId, threadId; }
 [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=true)] public static extern IntPtr CreateDesktopW(string name, IntPtr device, IntPtr mode, uint flags, uint access, IntPtr security);
 [DllImport("user32.dll", SetLastError=true)] public static extern bool CloseDesktop(IntPtr desktop);
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] public static extern bool CreateProcessW(string app, StringBuilder command, IntPtr pa, IntPtr ta, bool inherit, uint flags, IntPtr environment, string workdir, ref STARTUPINFO startup, out PROCESS_INFORMATION info);
 [DllImport("kernel32.dll", SetLastError=true)] public static extern bool CloseHandle(IntPtr handle);
 [DllImport("kernel32.dll", SetLastError=true)] public static extern IntPtr OpenProcess(uint access, bool inherit, uint id);
 [DllImport("kernel32.dll", SetLastError=true)] public static extern bool ReadProcessMemory(IntPtr process, IntPtr address, byte[] bytes, UIntPtr count, out UIntPtr read);
 [DllImport("kernel32.dll", SetLastError=true)] public static extern bool TerminateProcess(IntPtr process, uint code);
 [DllImport("kernel32.dll", SetLastError=true)] public static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);
 [DllImport("kernel32.dll", SetLastError=true)] public static extern bool GetProcessTimes(IntPtr handle, out long creation, out long exit, out long kernel, out long user);
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] public static extern bool QueryFullProcessImageNameW(IntPtr handle, uint flags, StringBuilder path, ref uint length);
}
'@
}

function Get-CanvasHandleIdentity {
    param([IntPtr]$Handle, [int]$ProcessId, [string]$ExpectedPath)
    $path = New-Object Text.StringBuilder 32768
    [uint32]$size = $path.Capacity
    [long]$created=0; [long]$ended=0; [long]$kernel=0; [long]$user=0
    if (-not [CanvasScreenNative]::QueryFullProcessImageNameW($Handle,0,$path,[ref]$size) -or
        -not [CanvasScreenNative]::GetProcessTimes($Handle,[ref]$created,[ref]$ended,[ref]$kernel,[ref]$user) -or
        [IO.Path]::GetFullPath($path.ToString()) -ine $ExpectedPath) { throw 'Retained process handle does not match the expected executable.' }
    return @{ process_id=$ProcessId; path=$path.ToString(); creation_filetime=$created; creation_utc=[datetime]::FromFileTimeUtc($created).ToString('o'); handle_retained=$true }
}

function ConvertTo-CanvasArgument {
    param([string]$Value)
    if ($Value -match '[\r\n\x00]') { throw 'Invalid native launch argument.' }
    # Windows CommandLineToArgv/CRT quoting: double slash runs before quotes
    # and the closing delimiter, retaining all other path slashes literally.
    $escaped=[regex]::Replace($Value,'(\\*)"','${1}${1}\"')
    $escaped=[regex]::Replace($escaped,'(\\+)$','${1}${1}')
    return '"'+$escaped+'"'
}

function Get-CanvasLaunchCommand {
    param($Plan,[string]$ProbePath,[string]$LogPath)
    if ($ProbePath -match '[$";\r\n]' -or $ProbePath -match '[^\x20-\x7e]') { throw 'Invalid canonical initial file path.' }
    $command='$$>a<"'+$ProbePath+'"'
    return ((@($Plan.cdb,'-hd','-logo',$LogPath,'-c',$command,$Plan.candidate_path) | ForEach-Object { ConvertTo-CanvasArgument $_ }) -join ' ')
}

function Start-CanvasHidden {
    param($Plan, [string]$ProbePath, [string]$LogPath, [hashtable]$Launch)
    Initialize-CanvasNative
    $desktopName = 'ClashCanvasScreen_' + [Guid]::NewGuid().ToString('N')
    $desktop = [CanvasScreenNative]::CreateDesktopW($desktopName,[IntPtr]::Zero,[IntPtr]::Zero,0,0x000F01FF,[IntPtr]::Zero)
    if ($desktop -eq [IntPtr]::Zero) { throw 'Hidden desktop creation failed; capture cannot launch.' }
    $environmentPointer = [IntPtr]::Zero
    $info = New-Object CanvasScreenNative+PROCESS_INFORMATION
    try {
        $environment = New-Object 'Collections.Generic.SortedDictionary[string,string]' ([StringComparer]::OrdinalIgnoreCase)
        foreach ($pair in [Environment]::GetEnvironmentVariables().GetEnumerator()) { $environment[[string]$pair.Key] = [string]$pair.Value }
        $environment['CLASH_PROXY_PRESENT'] = '0'
        $block = (($environment.GetEnumerator() | ForEach-Object { $_.Key + '=' + $_.Value }) -join "`0") + "`0`0"
        $environmentPointer = [Runtime.InteropServices.Marshal]::StringToHGlobalUni($block)
        $startup = New-Object CanvasScreenNative+STARTUPINFO
        $startup.cb = [Runtime.InteropServices.Marshal]::SizeOf($startup)
        $startup.desktop=$desktopName; $startup.flags=1; $startup.show=0
        # Exact quiet command-file invocation; no caller command or arguments.
        $command = Get-CanvasLaunchCommand $Plan $ProbePath $LogPath
        $buffer = New-Object Text.StringBuilder $command
        if (-not [CanvasScreenNative]::CreateProcessW($Plan.cdb,$buffer,[IntPtr]::Zero,[IntPtr]::Zero,$false,0x410,$environmentPointer,$Plan.work_dir,[ref]$startup,[ref]$info)) { throw ('CreateProcessW on the hidden desktop failed: Win32 ' + [Runtime.InteropServices.Marshal]::GetLastWin32Error()) }
        # Publish retained ownership BEFORE further identity queries can fail.
        # The outer finally can then stop a debugger/game created by a partial launch.
        $Launch.session=@{ handle=$info.process; desktop=$desktop; identity=@{process_id=[int]$info.processId;path=$Plan.cdb;creation_utc=$null}
            desktop_name=$desktopName; command_line=$command }
        [void][CanvasScreenNative]::CloseHandle($info.thread)
        $identity = Get-CanvasHandleIdentity $info.process ([int]$info.processId) $Plan.cdb
        $Launch.session.identity=$identity
        return $Launch.session
    } catch {
        if (-not $Launch.session) { [void][CanvasScreenNative]::CloseDesktop($desktop) }
        throw
    } finally { if ($environmentPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::FreeHGlobal($environmentPointer) } }
}

function Find-CanvasOwnedChildren {
    param($Plan, $CdbSession, [datetime]$StartedAt, $Owned)
    $rows = @(Get-CimInstance Win32_Process -Filter ('ParentProcessId=' + $CdbSession.identity.process_id) -OperationTimeoutSec 5)
    $matches = @(Select-CanvasChildren $rows $CdbSession.identity.process_id $Plan.candidate_path $StartedAt)
    foreach ($row in $matches) {
        $key = [string]$row.ProcessId
        if ($Owned.ContainsKey($key)) { continue }
        $handle = [CanvasScreenNative]::OpenProcess(0x101011,$false,[uint32]$row.ProcessId)
        if ($handle -eq [IntPtr]::Zero) { throw 'Could not retain the owned candidate process handle.' }
        try {
            $identity = Get-CanvasHandleIdentity $handle ([int]$row.ProcessId) $Plan.candidate_path
            if (([datetime]$identity.creation_utc).ToUniversalTime() -lt $StartedAt.ToUniversalTime() -or
                [Math]::Abs((([datetime]$identity.creation_utc).ToUniversalTime() - ([datetime]$row.CreationDate).ToUniversalTime()).TotalMilliseconds) -gt 1) {
                throw 'Candidate PID creation time changed during handle acquisition.'
            }
            $identity.parent_process_id=$CdbSession.identity.process_id
            $identity.candidate_sha256=Get-CanvasHash $Plan.candidate_path
            if ($identity.candidate_sha256 -cne $Plan.candidate_sha256) { throw 'Candidate changed after launch.' }
            $Owned[$key] = @{ handle=$handle; identity=$identity }
        } catch { [void][CanvasScreenNative]::CloseHandle($handle); throw }
    }
    if ($Owned.Count -gt 1) { throw 'Ambiguous candidate PID: more than one owned candidate was observed.' }
}

function Read-CanvasMemory {
    param([IntPtr]$Handle, [long]$Address, [int]$Count)
    $bytes = New-Object byte[] $Count
    [UIntPtr]$read = [UIntPtr]::Zero
    $nativeCount = [UIntPtr]::new([uint64]$Count)
    if (-not [CanvasScreenNative]::ReadProcessMemory($Handle,[IntPtr]$Address,$bytes,$nativeCount,[ref]$read) -or $read.ToUInt64() -ne $Count) { throw 'ReadProcessMemory did not return the exact bounded snapshot.' }
    return ,$bytes
}

function Stop-CanvasOwned {
    param($OwnedProcess)
    $before = [CanvasScreenNative]::WaitForSingleObject($OwnedProcess.handle,0)
    $terminated = $false
    if ($before -ne 0) { $terminated = [CanvasScreenNative]::TerminateProcess($OwnedProcess.handle,1) }
    $absent = [CanvasScreenNative]::WaitForSingleObject($OwnedProcess.handle,5000) -eq 0
    $closed = [CanvasScreenNative]::CloseHandle($OwnedProcess.handle)
    return @{ identity=$OwnedProcess.identity; absent=$absent; termination_requested=$terminated; handle_closed=$closed }
}

function Close-CanvasDesktop {
    param($Session)
    return [CanvasScreenNative]::CloseDesktop($Session.desktop)
}

function Test-CanvasProcessExited {
    param($Session)
    return [CanvasScreenNative]::WaitForSingleObject($Session.handle,0) -eq 0
}

function Write-CanvasJson {
    param([string]$Path, $Value)
    [IO.File]::WriteAllText($Path,($Value | ConvertTo-Json -Depth 80),[Text.UTF8Encoding]::new($false))
}

function Get-SelectionAssets {
    param([string]$Directory)
    $rows=[ordered]@{}; $queue=New-Object 'Collections.Generic.Queue[string]'
    $queue.Enqueue($Directory)
    while ($queue.Count) {
        $current=$queue.Dequeue()
        foreach ($item in Get-ChildItem -LiteralPath $current -Force | Sort-Object Name) {
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {throw 'Work directory contains a reparse point.'}
            if ($item.PSIsContainer) {$queue.Enqueue($item.FullName)}
            else {$rows[$item.FullName.Substring($Directory.Length+1).Replace('\','/')] = Get-CanvasHash $item.FullName}
        }
    }
    return $rows
}

function Assert-SelectionFiles {
    param($Plan)
    foreach ($item in $Plan.identities) {
        [void](Resolve-CanvasPath $item.path -Kind file)
        if ((Get-CanvasHash $item.path) -cne $item.sha256) {throw ('Planned source/runtime/input changed: '+$item.path)}
    }
    $now=Get-SelectionAssets $Plan.work_dir
    if (($now | ConvertTo-Json -Compress -Depth 5) -cne ($Plan.assets_before | ConvertTo-Json -Compress -Depth 5)) {
        throw 'Isolated work directory inventory changed from the prepared plan.'
    }
}

function New-SelectionPlan {
    param($Options)
    $paths=@{}
    foreach ($key in @('Original','Python','Cdb')) {$paths[$key]=Resolve-CanvasPath $Options.$key -Kind file}
    foreach ($key in @('InputCandidate','CandidateManifest','ProxyBuildManifest')) {$paths[$key]=Resolve-CanvasPath $Options.$key -Root 'C:\ClashTests' -Kind file}
    $working=Resolve-CanvasPath $Options.WorkDir -Root 'C:\ClashTests' -Kind directory
    $candidateDirectory=Resolve-CanvasPath $Options.CandidateDir -Root 'C:\ClashTests' -Kind new
    $outputDirectory=Resolve-CanvasPath $Options.OutDir -Root 'C:\ClashCaptures' -Kind new
    if ($candidateDirectory.StartsWith($working+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Candidate directory must be outside the immutable work directory.'}
    if ($outputDirectory -match '[^A-Za-z0-9_./:\\-]') {throw 'The producer requires literal ASCII capture paths without spaces or tokens.'}
    $save=Resolve-CanvasPath (Join-Path $working 'save\0.dat') -Root $working -Kind file
    $producer=Resolve-CanvasPath (Join-Path $script:RepoRoot 'tools\complete_hd_army_selection_probe.py') -Kind file
    $trace=Resolve-CanvasPath (Join-Path $script:RepoRoot 'tools\complete_hd_army_selection_trace.py') -Kind file
    $converter=Resolve-CanvasPath (Join-Path $script:RepoRoot 'tools\cdb_surface_dump_to_png.py') -Kind file
    $proxySource=Resolve-CanvasPath (Join-Path $script:RepoRoot 'src\ddraw_surfdump_proxy\ddraw_surfdump_proxy.cpp') -Kind file
    $proxyManifest=[IO.File]::ReadAllText($paths.ProxyBuildManifest) | ConvertFrom-Json
    $proxyOutput=Resolve-CanvasPath ([string]$proxyManifest.output) -Root 'C:\ClashTests' -Kind file
    if ($proxyManifest.generated_by -cne 'clash-hd-surface-dump-proxy' -or
        [IO.Path]::GetFullPath([string]$proxyManifest.source) -ine $proxySource -or
        $proxyManifest.source_sha256 -inotmatch '^[a-f0-9]{64}$' -or $proxyManifest.source_sha256 -ine (Get-CanvasHash $proxySource) -or
        $proxyManifest.output_sha256 -inotmatch '^[a-f0-9]{64}$' -or $proxyManifest.output_sha256 -ine (Get-CanvasHash $proxyOutput) -or
        [IO.Path]::GetFileName($proxyOutput) -ine 'ddraw.dll') {throw 'Proxy manifest does not bind the current source and binary.'}
    $assets=Get-SelectionAssets $working
    $identities=@(); $seen=@{}
    foreach ($file in @($paths.Values)+@($save,$producer,$trace,$converter,$proxySource,$proxyOutput,$script:HostPath)) {
        if (-not $seen.ContainsKey($file)) {$seen[$file]=$true;$identities+=@{path=$file;sha256=(Get-CanvasHash $file)}}
    }
    # Offline producer independently rebuilds the whole candidate and manifest.
    $packet=Invoke-CanvasPythonJson $paths.Python @($producer,'--original',$paths.Original,'--candidate',$paths.InputCandidate,
        '--candidate-manifest',$paths.CandidateManifest,'--save',$save,'--resolution',$Options.Resolution,'--capture-dir',$outputDirectory)
    if ($packet.schema -cne 'clash95_complete_hd_army_selection_probe_v1' -or
        $packet.resolution -cne $Options.Resolution -or $packet.candidate_sha256 -cne (Get-CanvasHash $paths.InputCandidate) -or
        $packet.original_sha256 -cne (Get-CanvasHash $paths.Original) -or $packet.save_sha256 -cne (Get-CanvasHash $save) -or
        $packet.probe_sha256 -cne (Get-CanvasBytesHash ([Text.Encoding]::ASCII.GetBytes($packet.compiled_probe))) -or
        $packet.runtime_executed -isnot [bool] -or $packet.runtime_executed -or $packet.manual_input_proof -or $packet.promotion_ready) {
        throw 'Complete producer packet identity or disclosure differs.'
    }
    foreach ($property in $packet.source_sha256.PSObject.Properties) {
        $file=Resolve-CanvasPath (Join-Path $script:RepoRoot $property.Name) -Root $script:RepoRoot -Kind file
        if ((Get-CanvasHash $file) -cne $property.Value) {throw ('Producer source receipt differs: '+$property.Name)}
        if (-not $seen.ContainsKey($file)) {$seen[$file]=$true;$identities+=@{path=$file;sha256=$property.Value}}
    }
    foreach ($relative in @('tools/initial_map_paint_trace.py','tools/partial_tile_trace_probe.py','tools/framed_army_selection_trace.py')) {
        $file=Resolve-CanvasPath (Join-Path $script:RepoRoot $relative) -Root $script:RepoRoot -Kind file
        if (-not $seen.ContainsKey($file)) {$seen[$file]=$true;$identities+=@{path=$file;sha256=(Get-CanvasHash $file)}}
    }
    $name=Get-CanvasCandidateName $candidateDirectory 'complete-hd-army-selection' $Options.Resolution
    if ($name -ieq [IO.Path]::GetFileName($paths.InputCandidate)) {throw 'Candidate copy requires a distinct executable basename.'}
    $plan=[ordered]@{
        schema='clash95_complete_hd_army_selection_capture_plan_v1';environment='hidden_cdb_host';deadline_seconds=300
        stage=$packet.stage;resolution=$packet.resolution;width=$packet.width;height=$packet.height
        original=$paths.Original;original_sha256=$packet.original_sha256;input_candidate=$paths.InputCandidate;candidate_sha256=$packet.candidate_sha256
        candidate_manifest=$paths.CandidateManifest;candidate_manifest_canonical_sha256=$packet.candidate_manifest_canonical_sha256
        candidate_dir=$candidateDirectory;candidate_path=(Join-Path $candidateDirectory $name);work_dir=$working;out_dir=$outputDirectory
        save=$save;save_sha256=$packet.save_sha256;proxy_input=$proxyOutput;proxy_sha256=(Get-CanvasHash $proxyOutput)
        proxy_path=(Join-Path $candidateDirectory 'ddraw.dll');palette_path=(Join-Path $candidateDirectory 'ddraw_surfdump_palette.bin')
        python=$paths.Python;cdb=$paths.Cdb;producer=$producer;trace=$trace;converter=$converter;host_path=$script:HostPath
        probe_sha256=$packet.probe_sha256;identities=$identities;assets_before=$assets
        child_environment=@{CLASH_PROXY_PRESENT='0';parent_environment_modified=$false}
        input_method='controlled native calls with disclosed scroll and mouse writes'
        ordinary_input_proof=$false;manual_input_proof=$false;visible_composition_proof=$false;promotion_ready=$false
    }
    Assert-SelectionFiles $plan
    return @{plan=$plan;packet=$packet}
}

function Test-SelectionReady {
    param([string]$Log)
    return [regex]::IsMatch($Log,'(?m)^SHSEL_HOST_READY\r?\n')
}

function Assert-SelectionSurface {
    param($Report,$Plan)
    foreach ($flag in @('passed','ready_for_host_capture','source_authenticated','whole_candidate_bound','candidate_manifest_bound')) {
        if ($Report.$flag -isnot [bool] -or -not $Report.$flag) {throw ('Full bound selection trace does not authorize capture: '+$flag)}
    }
    if ($Report.schema -cne 'clash95_complete_hd_army_selection_trace_v1' -or $Report.stage -cne $Plan.stage -or
        $Report.resolution -cne $Plan.resolution -or $Report.sequence_only -isnot [bool] -or $Report.sequence_only -or
        $Report.initial_log_projected -isnot [bool] -or $Report.initial_log_projected -or
        $Report.initial_map_trace.passed -isnot [bool] -or -not $Report.initial_map_trace.passed -or
        $Report.selection_sequence.passed -isnot [bool] -or -not $Report.selection_sequence.passed -or
        $Report.source.original_sha256 -cne $Plan.original_sha256 -or $Report.source.candidate_sha256 -cne $Plan.candidate_sha256 -or
        $Report.source.save_sha256 -cne $Plan.save_sha256 -or $Report.source.probe_raw_sha256 -cne $Plan.probe_sha256 -or
        $Report.source.candidate_manifest_canonical_sha256 -cne $Plan.candidate_manifest_canonical_sha256 -or
        $Report.source.log_raw_sha256 -cnotmatch '^[a-f0-9]{64}$') {throw 'Bound trace identity or complete initial/native sequence differs.'}
    foreach ($property in $Report.source.source_sha256.PSObject.Properties) {
        $file=Resolve-CanvasPath (Join-Path $script:RepoRoot $property.Name) -Root $script:RepoRoot -Kind file
        $matches=@($Plan.identities | Where-Object {$_.path -ieq $file -and $_.sha256 -ceq $property.Value})
        if ($matches.Count -ne 1) {throw ('Trace source was not pinned by the plan: '+$property.Name)}
    }
    $s=$Report.surface
    foreach ($key in @('tid','eip','esp','selected','prior','lower','owner','surface','base','width','height','vtable')) {
        if ($s.$key -isnot [int] -and $s.$key -isnot [long]) {throw ('Surface field must be an integer: '+$key)}
    }
    $bytes=[long]$Plan.width*$Plan.height
    if ($s.width -ne $Plan.width -or $s.height -ne $Plan.height -or $bytes -gt 67108864 -or
        $s.tid -le 0 -or $s.eip -ne 0x406fa1 -or $s.esp -lt 65536 -or $s.esp -gt 4294967292 -or ($s.esp%4) -or
        $s.selected -ne 3 -or $s.prior -ne 3 -or $s.lower -ne 1 -or $s.owner -ne 0x40ad40 -or $s.vtable -ne 0x50ee24 -or
        $s.surface -lt 65536 -or $s.surface -gt 4294967108 -or $s.surface -eq 0x51d4c0 -or
        $s.base -lt 65536 -or ($s.base+$bytes) -gt 4294967296) {throw 'Selection readiness surface/state is outside the bounded contract.'}
    return $s
}

function Save-SelectionSnapshot {
    param($OwnedGame,$Surface,[string]$RawPath,$Plan)
    $began=[datetime]::UtcNow.ToString('o')
    $prefix=[IO.Path]::Combine([IO.Path]::GetDirectoryName($RawPath),[IO.Path]::GetFileNameWithoutExtension($RawPath));$reads=@{}
    foreach ($phase in @('before','after')) {
        $e0=Read-CanvasMemory $OwnedGame.handle 0x5202e0 4
        $header=Read-CanvasMemory $OwnedGame.handle $Surface.surface 188
        if ([BitConverter]::ToUInt32($e0,0) -ne $Surface.surface -or
            [BitConverter]::ToUInt16($header,0) -ne $Surface.width -or [BitConverter]::ToUInt16($header,2) -ne $Surface.height -or
            [BitConverter]::ToUInt32($header,4) -ne $Surface.base -or [BitConverter]::ToUInt32($header,184) -ne 0x50ee24) {
            throw 'Live E0/header differs from the stopped validated selection surface.'
        }
        $reads[$phase]=@{}
        foreach ($entry in @(@('e0',$e0,0x5202e0),@('header',$header,$Surface.surface))) {
            $path=$prefix+'-'+$phase+'-'+$entry[0]+'.raw';[IO.File]::WriteAllBytes($path,$entry[1])
            $reads[$phase][$entry[0]]=@{path=$path;sha256=(Get-CanvasHash $path);bytes=$entry[1].Length;address=$entry[2]}
        }
        if ($phase -eq 'before') {
            $pixels=Read-CanvasMemory $OwnedGame.handle $Surface.base ([int]($Plan.width*$Plan.height))
            [IO.File]::WriteAllBytes($RawPath,$pixels)
        }
    }
    foreach ($name in @('e0','header')) {if ($reads.before[$name].sha256 -cne $reads.after[$name].sha256) {throw ('Paused '+$name+' changed across capture.')}}
    return @{path=$RawPath;sha256=(Get-CanvasHash $RawPath);bytes=$pixels.Length;width=$Plan.width;height=$Plan.height;pitch=$Plan.width
        pixel_reads=1;header_reads=2;e0_reads=2;paused=$true;capture='e0_software_diagnostic';reads=$reads
        surface=$Surface.surface;base=$Surface.base;game_identity=$OwnedGame.identity;started_at=$began;captured_at=[datetime]::UtcNow.ToString('o')}
}

function Save-SelectionTriplet {
    param($OwnedGame,$Surface,$Plan)
    $snapshots=@();$same=$true
    foreach ($index in 1..3) {
        $directory=Join-Path $Plan.out_dir ('capture-'+$index);[void](New-Item -ItemType Directory -Path $directory)
        $snapshot=Save-SelectionSnapshot $OwnedGame $Surface (Join-Path $directory 'surface.raw') $Plan
        if ($snapshots.Count) {
            if ($snapshot.sha256 -cne $snapshots[0].sha256) {$same=$false}
            foreach ($name in @('e0','header')) {if ($snapshot.reads.before[$name].sha256 -cne $snapshots[0].reads.before[$name].sha256) {$same=$false}}
        }
        $snapshots+=$snapshot
    }
    return @{snapshots=$snapshots;clean_stable_pair=$same}
}

function Test-SelectionCleanup {
    param($Cleanup)
    if ($Cleanup.desktop_closed -isnot [bool] -or -not $Cleanup.desktop_closed -or $Cleanup.candidates.Count -ne 1) {return $false}
    foreach ($record in @($Cleanup.cdb)+@($Cleanup.candidates)) {
        foreach ($flag in @('absent','handle_closed')) {
            if ($record.$flag -isnot [bool] -or -not $record.$flag) {return $false}
        }
    }
    return $true
}

function Invoke-SelectionTrace {
    param($Plan,[string]$Log,[string]$Packet,[string]$Probe,[int]$Timeout=120000)
    return Invoke-CanvasPythonJson $Plan.python @($Plan.trace,'--log',$Log,'--packet',$Packet,'--original',$Plan.original,
        '--candidate',$Plan.candidate_path,'--save',$Plan.save,'--probe',$Probe,'--candidate-manifest',$Plan.candidate_manifest) -PermitFailure -TimeoutMilliseconds $Timeout
}

function Invoke-SelectionCapture {
    param($Bundle,[switch]$DoExecute)
    $plan=$Bundle.plan;$packet=$Bundle.packet
    if (-not $DoExecute) {return @{status='dry_run';executed=$false;plan=$plan;packet=$packet}}
    $summary=[ordered]@{schema='clash95_complete_hd_army_selection_capture_v1';passed=$false;status='failed';executed=$false
        plan=$plan;failures=@();started_at=[datetime]::UtcNow.ToString('o');trace=$null;final_trace=$null;snapshot=$null;png=$null;snapshots=@()
        cleanup=@{cdb=$null;candidates=@();desktop_closed=$false};cleanup_verified=$false;clean_stable_pair=$false
        frame_verified=$false;action_bar_verified=$false;ordinary_input_proof=$false;manual_input_proof=$false;visible_composition_proof=$false;promotion_ready=$false}
    $session=$null;$launch=@{session=$null};$owned=@{};$created=$false
    $log=Join-Path $plan.out_dir 'cdb.log';$probe=Join-Path $plan.out_dir 'complete-hd-army-selection.cdb';$packetPath=Join-Path $plan.out_dir 'packet.json'
    try {
        Assert-SelectionFiles $plan
        [void](Resolve-CanvasPath $plan.out_dir -Root 'C:\ClashCaptures' -Kind new)
        [void](Resolve-CanvasPath $plan.candidate_dir -Root 'C:\ClashTests' -Kind new)
        [void](New-Item -ItemType Directory -Path $plan.out_dir);$created=$true
        [void](New-Item -ItemType Directory -Path $plan.candidate_dir)
        [IO.File]::Copy($plan.input_candidate,$plan.candidate_path,$false);[IO.File]::Copy($plan.proxy_input,$plan.proxy_path,$false)
        if ((Get-CanvasHash $plan.candidate_path) -cne $plan.candidate_sha256 -or (Get-CanvasHash $plan.proxy_path) -cne $plan.proxy_sha256) {throw 'Copied candidate/proxy identity differs.'}
        Write-CanvasJson $packetPath $packet
        [IO.File]::WriteAllText($probe,$packet.compiled_probe,[Text.UTF8Encoding]::new($false))
        [IO.File]::WriteAllText((Join-Path $plan.out_dir 'initial-extra.cdb'),$packet.initial_extra,[Text.UTF8Encoding]::new($false))
        Write-CanvasJson (Join-Path $plan.out_dir 'plan.json') $plan
        [IO.File]::Copy($plan.host_path,(Join-Path $plan.out_dir 'host.ps1'),$false)
        $summary.packet=@{path=$packetPath;sha256=(Get-CanvasHash $packetPath)};$summary.probe=@{path=$probe;sha256=(Get-CanvasHash $probe)}
        if ($summary.probe.sha256 -cne $plan.probe_sha256) {throw 'Written canonical command differs.'}
        $rebuilt=Invoke-CanvasPythonJson $plan.python @($plan.producer,'--original',$plan.original,'--candidate',$plan.candidate_path,
            '--candidate-manifest',$plan.candidate_manifest,'--save',$plan.save,'--resolution',$plan.resolution,'--capture-dir',$plan.out_dir)
        if (($rebuilt | ConvertTo-Json -Compress -Depth 80) -cne ($packet | ConvertTo-Json -Compress -Depth 80)) {throw 'Copied candidate reconstruction differs from the full packet.'}
        Assert-SelectionFiles $plan
        $launchStart=[datetime]::UtcNow;$watch=[Diagnostics.Stopwatch]::StartNew()
        $summary.launch_attempted=$true;$session=Start-CanvasHidden $plan $probe $log $launch
        $summary.executed=$true;$summary.cdb=$session.identity;$summary.hidden_desktop=$session.desktop_name;$summary.command_line=$session.command_line
        while ($watch.Elapsed.TotalSeconds -lt $plan.deadline_seconds) {
            Find-CanvasOwnedChildren $plan $session $launchStart $owned
            if (Test-SelectionReady (Read-CanvasLog $log)) {
                Assert-SelectionFiles $plan
                $summary.trace=Invoke-SelectionTrace $plan $log $packetPath $probe ([Math]::Max(1,[Math]::Min(120000,300000-[int]$watch.ElapsedMilliseconds)))
                Write-CanvasJson (Join-Path $plan.out_dir 'trace.json') $summary.trace
                $surface=Assert-SelectionSurface $summary.trace $plan
                if ($owned.Count -ne 1) {throw 'Ready trace lacks exactly one authenticated owned candidate.'}
                if ($watch.Elapsed.TotalSeconds -ge 300) {throw 'Bound trace exceeded the runtime deadline before capture.'}
                $prefix=Read-CanvasLogBytes $log
                if ((Get-CanvasBytesHash $prefix) -cne $summary.trace.source.log_raw_sha256) {throw 'Validated raw log changed before capture.'}
                $prefixPath=Join-Path $plan.out_dir 'capture-prefix.log';[IO.File]::WriteAllBytes($prefixPath,$prefix)
                $summary.capture_prefix=@{path=$prefixPath;sha256=(Get-CanvasHash $prefixPath);bytes=$prefix.Length}
                $triplet=Save-SelectionTriplet @($owned.Values)[0] $surface $plan
                $summary.snapshots=$triplet.snapshots;$summary.snapshot=$triplet.snapshots[0];$summary.clean_stable_pair=$triplet.clean_stable_pair
                if (-not $summary.clean_stable_pair) {throw 'Paused pixel/header/E0 triplet differs; all completed captures remain available.'}
                if ((Get-CanvasBytesHash (Read-CanvasLogBytes $log)) -cne $summary.capture_prefix.sha256) {throw 'Debugger log changed during stopped capture.'}
                if ($watch.Elapsed.TotalSeconds -ge 300) {throw 'Stopped capture exceeded the runtime deadline.'}
                foreach ($name in @('before-redraw','after-redraw')) {
                    $path=Join-Path $plan.out_dir ($name+'.raw')
                    if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or (Get-Item -LiteralPath $path).Length -ne ($plan.width*$plan.height)) {throw ('Producer paired surface missing or truncated: '+$name)}
                    $summary[$name]=@{path=$path;sha256=(Get-CanvasHash $path);bytes=(Get-Item -LiteralPath $path).Length}
                }
                break
            }
            if (Test-CanvasProcessExited $session) {throw 'Debugger exited before validated selection readiness.'}
            Start-Sleep -Milliseconds 100
        }
        if (-not $summary.snapshot) {throw 'The 300-second selection deadline expired without a validated snapshot.'}
    } catch {$summary.failures+=$_.Exception.Message}
    finally {
        if (-not $session -and $launch.session) {$session=$launch.session;$summary.executed=$true;$summary.cdb=$session.identity}
        if ($session) {
            try {Find-CanvasOwnedChildren $plan $session $launchStart $owned} catch {$summary.failures+=$_.Exception.Message}
            $summary.candidates=@($owned.Values | ForEach-Object {$_.identity})
            try {$summary.cleanup.cdb=Stop-CanvasOwned $session} catch {$summary.failures+=$_.Exception.Message}
            foreach ($game in $owned.Values) {try {$summary.cleanup.candidates+=Stop-CanvasOwned $game} catch {$summary.failures+=$_.Exception.Message}}
            try {$summary.cleanup.desktop_closed=Close-CanvasDesktop $session} catch {$summary.failures+=$_.Exception.Message}
            $summary.cleanup_verified=Test-SelectionCleanup $summary.cleanup
            if (-not $summary.cleanup_verified) {$summary.failures+='Exact owned-process absence, handle closure and desktop closure were not fully verified.'}
        }
        if ($summary.snapshot) {
            try {
                $summary.final_trace=Invoke-SelectionTrace $plan $log $packetPath $probe
                Write-CanvasJson (Join-Path $plan.out_dir 'trace-final.json') $summary.final_trace
                [void](Assert-SelectionSurface $summary.final_trace $plan)
                $final=Read-CanvasLogBytes $log;$prefix=[IO.File]::ReadAllBytes($summary.capture_prefix.path)
                if ((Get-CanvasBytesHash $prefix) -cne $summary.capture_prefix.sha256 -or $final.Length -lt $prefix.Length) {throw 'Capture prefix changed or final log was truncated.'}
                $head=New-Object byte[] $prefix.Length;[Array]::Copy($final,$head,$head.Length)
                if ((Get-CanvasBytesHash $head) -cne $summary.capture_prefix.sha256 -or (Get-CanvasBytesHash $final) -cne $summary.final_trace.source.log_raw_sha256) {throw 'Final log does not retain the validated capture prefix.'}
                $summary.final_log=@{path=$log;sha256=(Get-CanvasBytesHash $final);bytes=$final.Length;capture_prefix_preserved=$true}
                if ((Get-CanvasHash $packetPath) -cne $summary.packet.sha256 -or (Get-CanvasHash $probe) -cne $summary.probe.sha256) {throw 'Packet or probe changed after capture.'}
            } catch {$summary.failures+=$_.Exception.Message}
            try {
                if (-not (Test-Path -LiteralPath $plan.palette_path -PathType Leaf) -or (Get-Item -LiteralPath $plan.palette_path).Length -ne 1024) {throw 'Fresh proxy palette is missing or truncated.'}
                $summary.palette=@{path=$plan.palette_path;sha256=(Get-CanvasHash $plan.palette_path);bytes=1024}
                $raw=Join-Path $plan.out_dir 'surface.raw';[IO.File]::Copy($summary.snapshot.path,$raw,$false)
                $png=Join-Path $plan.out_dir 'surface.png';$meta=Join-Path $plan.out_dir 'surface.png.json'
                # Converter API is offline and returns the actual metadata JSON.
                $code='import json,sys;sys.path.insert(0,sys.argv[1]);from pathlib import Path;from cdb_surface_dump_to_png import convert;print(json.dumps(convert(Path(sys.argv[2]),Path(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5]),int(sys.argv[4]),Path(sys.argv[6]),Path(sys.argv[7]),Path(sys.argv[8]))))'
                $summary.png=Invoke-CanvasPythonJson $plan.python @('-c',$code,(Split-Path $plan.converter),$raw,$png,[string]$plan.width,[string]$plan.height,$meta,$summary.capture_prefix.path,$plan.palette_path)
                if ($summary.png.palette_mode -cne 'directdraw-palette' -or $summary.png.raw_sha256 -cne $summary.snapshot.sha256 -or $summary.png.png_sha256 -cne (Get-CanvasHash $png)) {throw 'PNG does not bind the captured raw bytes and real palette.'}
            } catch {$summary.failures+=$_.Exception.Message}
        }
        try {
            Assert-SelectionFiles $plan
            $summary.assets_after=Get-SelectionAssets $plan.work_dir
            if ($summary.executed -and ((Get-CanvasHash $plan.candidate_path) -cne $plan.candidate_sha256 -or (Get-CanvasHash $plan.proxy_path) -cne $plan.proxy_sha256)) {throw 'Runtime candidate/proxy changed.'}
            $summary.source_and_input_identities_unchanged=$true
        } catch {$summary.failures+=$_.Exception.Message;$summary.source_and_input_identities_unchanged=$false}
        $summary.finished_at=[datetime]::UtcNow.ToString('o')
        $summary.passed=($summary.executed -and $summary.failures.Count -eq 0 -and $summary.cleanup_verified -and $summary.clean_stable_pair -and $null -ne $summary.png)
        if ($summary.passed) {$summary.status='bounded_hidden_complete_hd_army_selection_capture'}
        if ($created) {
            try {Write-CanvasJson (Join-Path $plan.out_dir 'summary.json') $summary}
            catch {
                # Keep real execution/cleanup truth in stdout even if receipt
                # persistence fails. The outer preparation catch must not
                # relabel an executed run as an unexecuted preparation error.
                $summary.failures+=('Final summary persistence failed: '+$_.Exception.Message)
                $summary.passed=$false;$summary.status='failed'
            }
        }
    }
    return $summary
}

try {
    $options=@{Original=$Original;InputCandidate=$InputCandidate;CandidateManifest=$CandidateManifest;ProxyBuildManifest=$ProxyBuildManifest
        WorkDir=$WorkDir;CandidateDir=$CandidateDir;OutDir=$OutDir;Resolution=$Resolution;Python=$Python;Cdb=$Cdb}
    $bundle=New-SelectionPlan $options
    $result=Invoke-SelectionCapture $bundle -DoExecute:$Execute
    $result | ConvertTo-Json -Depth 80
    if ($Execute -and -not $result.passed) {exit 1}
} catch {
    $failure=@{schema='clash95_complete_hd_army_selection_capture_v1';passed=$false;status='preparation_failed';executed=$false
        failures=@($_.Exception.Message);manual_input_proof=$false;promotion_ready=$false}
    if ($null -ne $_.Exception.Data['CanvasPythonFailure']) {$failure.child_failure=$_.Exception.Data['CanvasPythonFailure']}
    $failure | ConvertTo-Json -Depth 10
    exit 1
}
