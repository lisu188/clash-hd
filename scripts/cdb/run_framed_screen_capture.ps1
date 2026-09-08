<# Hidden, controlled modal-route capture. Default is an offline plan only.
   This does not prove natural selection, manual input, visible composition or promotion.
   No existing harness is dot-sourced. All native code is initialized only after -Execute.
#>
[CmdletBinding()]
param(
    [string]$Original = 'C:\Clash\clash95.exe',
    [Parameter(Mandatory=$true)][string]$InputCandidate,
    [Parameter(Mandatory=$true)][string]$ProxyBuildManifest,
    [Parameter(Mandatory=$true)][string]$WorkDir,
    [Parameter(Mandatory=$true)][string]$CandidateDir,
    [Parameter(Mandatory=$true)][string]$OutDir,
    [ValidateSet('castle_overview','hospital','school','workshop','smith','barracks','peasants')]
    [string]$Route = 'castle_overview',
    [ValidateRange(0,3)][int]$CastleIndex = 0,
    [ValidateSet('existing_flags','construct_all')][string]$Availability = 'existing_flags',
    [string]$Resolution = '800x600',
    [switch]$MinimapViewport,
    [switch]$Execute
)
$ErrorActionPreference = 'Stop'
# Only this PowerShell process is affected. Preserve Unicode packet rationale
# through redirected stdout instead of the Windows PowerShell OEM code page.
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
$script:RepoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$script:Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation'

function Get-FramedHash {
    param([string]$Path)
    $stream = [IO.File]::OpenRead($Path)
    $hash = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
    finally { $stream.Dispose(); $hash.Dispose() }
}

function Get-FramedCandidateName {
    param([string]$Directory, [string]$Route, [string]$Resolution)
    $hash=[Security.Cryptography.SHA256]::Create()
    try {
        $digest=([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($Directory.ToLowerInvariant())))).Replace('-','').ToLowerInvariant()
        return ('framed-screen-' + $Route + '-' + $Resolution + '-' + $digest.Substring(0,16) + '.exe')
    } finally { $hash.Dispose() }
}

function Resolve-FramedPath {
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

function Invoke-FramedPythonJson {
    param([string]$Python, [string[]]$Arguments, [switch]$PermitFailure)
    $output = & $Python -B @Arguments
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0 -and -not $PermitFailure) { throw "Offline Python command failed with exit $exitCode." }
    try { $result = ($output -join "`n") | ConvertFrom-Json }
    catch { throw "Offline Python command did not emit valid JSON (exit $exitCode)." }
    if (-not $result) { throw 'Offline Python command returned no report.' }
    return $result
}

function New-FramedCapturePlan {
    param($Options)
    $originalPath = Resolve-FramedPath $Options.Original -Kind file
    $inputPath = Resolve-FramedPath $Options.InputCandidate -Root 'C:\ClashTests' -Kind file
    $manifestPath = Resolve-FramedPath $Options.ProxyBuildManifest -Root 'C:\ClashTests' -Kind file
    $workingPath = Resolve-FramedPath $Options.WorkDir -Root 'C:\ClashTests' -Kind directory
    $candidateDirectory = Resolve-FramedPath $Options.CandidateDir -Root 'C:\ClashTests' -Kind new
    $outputDirectory = Resolve-FramedPath $Options.OutDir -Root 'C:\ClashCaptures' -Kind new
    if ($Options.Resolution -notmatch '^([0-9]{3,4})x([0-9]{3,4})$') { throw 'Resolution must be canonical WxH.' }
    $width = [int]$Matches[1]; $height = [int]$Matches[2]
    if ($width -lt 640 -or $height -lt 480 -or $width -gt 8192 -or $height -gt 8192 -or ($width % 2) -or ($height % 2)) { throw 'Unsupported physical resolution.' }
    $python = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    $cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe'
    $python = Resolve-FramedPath $python -Kind file
    $cdb = Resolve-FramedPath $cdb -Kind file
    $trace = Resolve-FramedPath (Join-Path $script:RepoRoot 'tools\framed_screen_trace.py') -Kind file
    $converter = Resolve-FramedPath (Join-Path $script:RepoRoot 'tools\cdb_surface_dump_to_png.py') -Kind file
    $proxySource = Resolve-FramedPath (Join-Path $script:RepoRoot 'src\ddraw_surfdump_proxy\ddraw_surfdump_proxy.cpp') -Kind file
    $manifest = [IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json
    $proxyOutput = Resolve-FramedPath ([string]$manifest.output) -Root 'C:\ClashTests' -Kind file
    $sourceHash = Get-FramedHash $proxySource
    $proxyHash = Get-FramedHash $proxyOutput
    if ($manifest.generated_by -cne 'clash-hd-surface-dump-proxy' -or
        [IO.Path]::GetFullPath([string]$manifest.source) -ine $proxySource -or
        $manifest.source_sha256 -inotmatch '^[a-f0-9]{64}$' -or $manifest.source_sha256 -ine $sourceHash -or
        $manifest.output_sha256 -inotmatch '^[a-f0-9]{64}$' -or $manifest.output_sha256 -ine $proxyHash -or
        [IO.Path]::GetFileName($proxyOutput) -ine 'ddraw.dll') { throw 'Proxy manifest does not authenticate the current source and binary.' }
    $candidateHash = Get-FramedHash $inputPath
    $prepareArgs = @($trace,'--prepare','--original',$originalPath,'--candidate',$inputPath,
        '--candidate-sha256',$candidateHash,'--stage',$script:Stage,'--resolution',$Options.Resolution,
        '--route',$Options.Route,'--availability',$Options.Availability,'--castle-index',[string]$Options.CastleIndex)
    if ($Options.MinimapViewport) { $prepareArgs += '--minimap-viewport' }
    $prepared = Invoke-FramedPythonJson $python $prepareArgs
    if ($prepared.packet.prepared -isnot [bool] -or -not $prepared.packet.prepared -or
        $prepared.packet.candidate_sha256 -cne $candidateHash -or $prepared.packet.stage -cne $script:Stage -or
        $prepared.packet.resolution -cne $Options.Resolution -or -not $prepared.probe -or
        $prepared.probe_sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Candidate preparation did not produce its bound packet and compiled probe.' }
    # Repeated dry-run/Execute calls with the same new directory describe the same
    # executable path. Its directory must remain nonexistent until execution.
    $candidateName = Get-FramedCandidateName $candidateDirectory $Options.Route $Options.Resolution
    if ($candidateName -ieq [IO.Path]::GetFileName($inputPath)) { throw 'The copied executable must have a new basename.' }
    $plan = [ordered]@{
        schema='clash95_framed_screen_capture_plan_v1'; environment='hidden_cdb_host'; execute=[bool]$Options.Execute
        stage=$script:Stage; resolution=$Options.Resolution; width=$width; height=$height
        route=$Options.Route; castle_index=$Options.CastleIndex; availability=$Options.Availability
        minimap_viewport=[bool]$Options.MinimapViewport; deadline_seconds=120
        original=$originalPath; original_sha256=(Get-FramedHash $originalPath)
        input_candidate=$inputPath; candidate_sha256=$candidateHash; candidate_dir=$candidateDirectory
        candidate_path=(Join-Path $candidateDirectory $candidateName); work_dir=$workingPath; out_dir=$outputDirectory
        proxy_manifest=$manifestPath; proxy_manifest_sha256=(Get-FramedHash $manifestPath)
        proxy_source=$proxySource; proxy_source_sha256=$sourceHash; proxy_input=$proxyOutput; proxy_sha256=$proxyHash
        proxy_path=(Join-Path $candidateDirectory 'ddraw.dll'); palette_path=(Join-Path $candidateDirectory 'ddraw_surfdump_palette.bin')
        python=$python; cdb=$cdb; trace=$trace; converter=$converter
        host_path=$PSCommandPath; host_sha256=(Get-FramedHash $PSCommandPath)
        trace_sha256=(Get-FramedHash $trace); converter_sha256=(Get-FramedHash $converter)
        python_sha256=(Get-FramedHash $python); cdb_sha256=(Get-FramedHash $cdb)
        probe_sha256=$prepared.probe_sha256
        child_environment=@{ CLASH_PROXY_PRESENT='0'; parent_environment_modified=$false }
        manual_input_proof=$false; visible_composition_proof=$false; promotion_ready=$false
        limits=@('Controlled native dispatch and optional availability mutation; no natural-input proof.',
            'One paused 8-bit memory-surface snapshot; separate primary overlays may be absent.',
            'The provided isolated work directory may receive native game configuration/save writes.')
    }
    return @{ plan=$plan; prepared=$prepared }
}

function Test-FramedModalReady {
    param([string]$Log)
    # Complete, exact line only. Earlier map readiness never authorizes a read.
    return [regex]::IsMatch($Log, '(?m)^MODAL_SURFDUMP_HOST_READY\r?\n')
}

function Read-FramedLog {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return '' }
    # CDB retains a writable log handle while paused. Do not deny its writer.
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    $reader=New-Object IO.StreamReader $stream
    try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
}

function Assert-FramedSurface {
    param($Report, $Plan)
    if ($Report.passed -isnot [bool] -or -not $Report.passed -or
        $Report.ready_for_host_capture -isnot [bool] -or -not $Report.ready_for_host_capture) { throw 'Full modal trace did not authorize host capture.' }
    $s = $Report.surface
    foreach ($name in @('surface','width','height','base','bytes','tid','eip','esp')) {
        if ($s.$name -isnot [int] -and $s.$name -isnot [long]) { throw "Surface field $name must be an integer." }
    }
    if ($s.width -ne $Plan.width -or $s.height -ne $Plan.height -or $s.bytes -ne ([long]$Plan.width * $Plan.height) -or
        $s.bytes -gt 67108864 -or $s.surface -lt 65536 -or $s.surface -ge 4294967108 -or $s.surface -eq 0x51d4c0 -or
        $s.base -lt 65536 -or ([long]$s.base + $s.bytes) -gt 4294967296 -or
        $s.tid -le 0 -or $s.eip -le 0 -or $s.esp -le 0 -or $s.route -cne $Plan.route) { throw 'Validated surface is outside the bounded native memory-surface contract.' }
    return $s
}

function Select-FramedChildren {
    param($Rows, [int]$CdbProcessId, [string]$CandidatePath, [datetime]$StartedAt)
    $selected = @()
    foreach ($row in $Rows) {
        if ([int]$row.ParentProcessId -eq $CdbProcessId -and $row.ExecutablePath -and
            [IO.Path]::GetFullPath([string]$row.ExecutablePath) -ieq $CandidatePath) {
            if ([datetime]$row.CreationDate -lt $StartedAt -or [int]$row.ProcessId -le 0) { throw 'Child process identity predates this launch.' }
            $selected += $row
        }
    }
    return $selected
}

function Initialize-FramedNative {
    if ('FramedScreenNative' -as [type]) { return }
    Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class FramedScreenNative {
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

function Get-FramedHandleIdentity {
    param([IntPtr]$Handle, [int]$ProcessId, [string]$ExpectedPath)
    $path = New-Object Text.StringBuilder 32768
    [uint32]$size = $path.Capacity
    [long]$created=0; [long]$ended=0; [long]$kernel=0; [long]$user=0
    if (-not [FramedScreenNative]::QueryFullProcessImageNameW($Handle,0,$path,[ref]$size) -or
        -not [FramedScreenNative]::GetProcessTimes($Handle,[ref]$created,[ref]$ended,[ref]$kernel,[ref]$user) -or
        [IO.Path]::GetFullPath($path.ToString()) -ine $ExpectedPath) { throw 'Retained process handle does not match the expected executable.' }
    return @{ process_id=$ProcessId; path=$path.ToString(); creation_filetime=$created; creation_utc=[datetime]::FromFileTimeUtc($created).ToString('o'); handle_retained=$true }
}

function Start-FramedHidden {
    param($Plan, [string]$ProbePath, [string]$LogPath, [hashtable]$Launch)
    Initialize-FramedNative
    $desktopName = 'ClashFramedScreen_' + [Guid]::NewGuid().ToString('N')
    $desktop = [FramedScreenNative]::CreateDesktopW($desktopName,[IntPtr]::Zero,[IntPtr]::Zero,0,0x000F01FF,[IntPtr]::Zero)
    if ($desktop -eq [IntPtr]::Zero) { throw 'Hidden desktop creation failed; capture cannot launch.' }
    $environmentPointer = [IntPtr]::Zero
    $info = New-Object FramedScreenNative+PROCESS_INFORMATION
    try {
        $environment = New-Object 'Collections.Generic.SortedDictionary[string,string]' ([StringComparer]::OrdinalIgnoreCase)
        foreach ($pair in [Environment]::GetEnvironmentVariables().GetEnumerator()) { $environment[[string]$pair.Key] = [string]$pair.Value }
        $environment['CLASH_PROXY_PRESENT'] = '0'
        $block = (($environment.GetEnumerator() | ForEach-Object { $_.Key + '=' + $_.Value }) -join "`0") + "`0`0"
        $environmentPointer = [Runtime.InteropServices.Marshal]::StringToHGlobalUni($block)
        $startup = New-Object FramedScreenNative+STARTUPINFO
        $startup.cb = [Runtime.InteropServices.Marshal]::SizeOf($startup)
        $startup.desktop=$desktopName; $startup.flags=1; $startup.show=0
        # Paths were validated to exclude quotes/newlines/semicolons. $$>< accepts the remainder as its filename.
        $command = '"' + $Plan.cdb + '" -hd -logo "' + $LogPath + '" -c "$$><' + $ProbePath + '" "' + $Plan.candidate_path + '"'
        $buffer = New-Object Text.StringBuilder $command
        if (-not [FramedScreenNative]::CreateProcessW($Plan.cdb,$buffer,[IntPtr]::Zero,[IntPtr]::Zero,$false,0x410,$environmentPointer,$Plan.work_dir,[ref]$startup,[ref]$info)) { throw ('CreateProcessW on the hidden desktop failed: Win32 ' + [Runtime.InteropServices.Marshal]::GetLastWin32Error()) }
        # Publish retained ownership BEFORE further identity queries can fail.
        # The outer finally can then stop a debugger/game created by a partial launch.
        $Launch.session=@{ handle=$info.process; desktop=$desktop; identity=@{process_id=[int]$info.processId;path=$Plan.cdb;creation_utc=$null}
            desktop_name=$desktopName; command_line=$command }
        [void][FramedScreenNative]::CloseHandle($info.thread)
        $identity = Get-FramedHandleIdentity $info.process ([int]$info.processId) $Plan.cdb
        $Launch.session.identity=$identity
        return $Launch.session
    } catch {
        if (-not $Launch.session) { [void][FramedScreenNative]::CloseDesktop($desktop) }
        throw
    } finally { if ($environmentPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::FreeHGlobal($environmentPointer) } }
}

function Find-FramedOwnedChildren {
    param($Plan, $CdbSession, [datetime]$StartedAt, $Owned)
    $rows = @(Get-CimInstance Win32_Process -Filter ('ParentProcessId=' + $CdbSession.identity.process_id) -OperationTimeoutSec 5)
    $matches = @(Select-FramedChildren $rows $CdbSession.identity.process_id $Plan.candidate_path $StartedAt)
    foreach ($row in $matches) {
        $key = [string]$row.ProcessId
        if ($Owned.ContainsKey($key)) { continue }
        $handle = [FramedScreenNative]::OpenProcess(0x101011,$false,[uint32]$row.ProcessId)
        if ($handle -eq [IntPtr]::Zero) { throw 'Could not retain the owned candidate process handle.' }
        try {
            $identity = Get-FramedHandleIdentity $handle ([int]$row.ProcessId) $Plan.candidate_path
            if ([datetime]$identity.creation_utc -lt $StartedAt -or
                [Math]::Abs((([datetime]$identity.creation_utc).ToUniversalTime() - ([datetime]$row.CreationDate).ToUniversalTime()).TotalMilliseconds) -gt 1) {
                throw 'Candidate PID creation time changed during handle acquisition.'
            }
            $identity.parent_process_id=$CdbSession.identity.process_id
            $identity.candidate_sha256=Get-FramedHash $Plan.candidate_path
            if ($identity.candidate_sha256 -cne $Plan.candidate_sha256) { throw 'Candidate changed after launch.' }
            $Owned[$key] = @{ handle=$handle; identity=$identity }
        } catch { [void][FramedScreenNative]::CloseHandle($handle); throw }
    }
    if ($Owned.Count -gt 1) { throw 'Ambiguous candidate PID: more than one owned candidate was observed.' }
}

function Read-FramedMemory {
    param([IntPtr]$Handle, [long]$Address, [int]$Count)
    $bytes = New-Object byte[] $Count
    [UIntPtr]$read = [UIntPtr]::Zero
    $nativeCount = [UIntPtr]::new([uint64]$Count)
    if (-not [FramedScreenNative]::ReadProcessMemory($Handle,[IntPtr]$Address,$bytes,$nativeCount,[ref]$read) -or $read.ToUInt64() -ne $Count) { throw 'ReadProcessMemory did not return the exact bounded snapshot.' }
    return ,$bytes
}

function Save-FramedSnapshot {
    param($OwnedGame, $Surface, [string]$RawPath)
    # The debugger remains paused: independently authenticate the native memory header,
    # then one pixel read. Width is the native 8-bit memory surface pitch.
    $header = Read-FramedMemory $OwnedGame.handle $Surface.surface 188
    if ([BitConverter]::ToUInt16($header,0) -ne $Surface.width -or [BitConverter]::ToUInt16($header,2) -ne $Surface.height -or
        [BitConverter]::ToUInt32($header,4) -ne $Surface.base -or [BitConverter]::ToUInt32($header,184) -ne 0x50ee24) { throw 'Live surface header differs from the accepted native memory surface.' }
    $pixels = Read-FramedMemory $OwnedGame.handle $Surface.base $Surface.bytes
    [IO.File]::WriteAllBytes($RawPath,$pixels)
    return @{ path=$RawPath; sha256=(Get-FramedHash $RawPath); bytes=$pixels.Length; width=$Surface.width; height=$Surface.height; pitch=$Surface.width; pixel_reads=1; paused=$true }
}

function Stop-FramedOwned {
    param($OwnedProcess)
    $before = [FramedScreenNative]::WaitForSingleObject($OwnedProcess.handle,0)
    $terminated = $false
    if ($before -ne 0) { $terminated = [FramedScreenNative]::TerminateProcess($OwnedProcess.handle,1) }
    $absent = [FramedScreenNative]::WaitForSingleObject($OwnedProcess.handle,5000) -eq 0
    $closed = [FramedScreenNative]::CloseHandle($OwnedProcess.handle)
    return @{ identity=$OwnedProcess.identity; absent=$absent; termination_requested=$terminated; handle_closed=$closed }
}

function Close-FramedDesktop {
    param($Session)
    return [FramedScreenNative]::CloseDesktop($Session.desktop)
}

function Test-FramedProcessExited {
    param($Session)
    return [FramedScreenNative]::WaitForSingleObject($Session.handle,0) -eq 0
}

function Write-FramedJson {
    param([string]$Path, $Value)
    [IO.File]::WriteAllText($Path,($Value | ConvertTo-Json -Depth 80),[Text.UTF8Encoding]::new($false))
}

function Invoke-FramedCapture {
    param($Bundle, [switch]$DoExecute)
    $plan=$Bundle.plan; $prepared=$Bundle.prepared
    if (-not $DoExecute) { return @{ status='dry_run'; executed=$false; plan=$plan; prepared=$prepared } }
    $summary = [ordered]@{ schema='clash95_framed_screen_capture_v1'; passed=$false; status='failed'; executed=$false; plan=$plan
        started_at=[datetime]::UtcNow.ToString('o'); finished_at=$null; failures=@(); trace=$null; snapshot=$null; png=$null
        cdb=$null; candidates=@(); cleanup=@{ cdb=$null; candidates=@(); desktop_closed=$false }
        manual_input_proof=$false; visible_composition_proof=$false; promotion_ready=$false }
    $session=$null; $owned=@{}; $outputCreated=$false; $launch=@{session=$null}
    $logPath=Join-Path $plan.out_dir 'cdb.log'; $probePath=Join-Path $plan.out_dir 'framed-screen.cdb'
    $packetPath=Join-Path $plan.out_dir 'packet.json'; $rawPath=Join-Path $plan.out_dir 'surface.raw'
    try {
        # No -Force, no reuse: never overwrite a previous artifact or candidate.
        [void](Resolve-FramedPath $plan.out_dir -Root 'C:\ClashCaptures' -Kind new)
        [void](New-Item -ItemType Directory -Path $plan.out_dir)
        $outputCreated=$true
        [void](Resolve-FramedPath $plan.candidate_dir -Root 'C:\ClashTests' -Kind new)
        [void](New-Item -ItemType Directory -Path $plan.candidate_dir)
        foreach ($pair in @(@($plan.original,$plan.original_sha256),@($plan.input_candidate,$plan.candidate_sha256),
            @($plan.proxy_manifest,$plan.proxy_manifest_sha256),@($plan.proxy_source,$plan.proxy_source_sha256),@($plan.proxy_input,$plan.proxy_sha256),
            @($plan.host_path,$plan.host_sha256),@($plan.trace,$plan.trace_sha256),@($plan.converter,$plan.converter_sha256),
            @($plan.python,$plan.python_sha256),@($plan.cdb,$plan.cdb_sha256))) {
            if ((Get-FramedHash $pair[0]) -cne $pair[1]) { throw 'A planned source, runtime or input file changed before execution.' }
        }
        [IO.File]::Copy($plan.input_candidate,$plan.candidate_path,$false)
        [IO.File]::Copy($plan.proxy_input,$plan.proxy_path,$false)
        if ((Get-FramedHash $plan.candidate_path) -cne $plan.candidate_sha256 -or (Get-FramedHash $plan.proxy_path) -cne $plan.proxy_sha256) { throw 'Fresh candidate/proxy copy identity mismatch.' }
        Write-FramedJson $packetPath $prepared.packet
        [IO.File]::WriteAllText($probePath,$prepared.probe,[Text.UTF8Encoding]::new($false))
        if ((Get-FramedHash $probePath) -cne $plan.probe_sha256) { throw 'Compiled probe file differs from the prepared packet.' }
        Write-FramedJson (Join-Path $plan.out_dir 'plan.json') $plan
        # Reconstruct against the COPIED file before launch, not merely its input path.
        $verifyArgs=@($plan.trace,'--prepare','--original',$plan.original,'--candidate',$plan.candidate_path,
            '--candidate-sha256',$plan.candidate_sha256,'--stage',$plan.stage,'--resolution',$plan.resolution,
            '--route',$plan.route,'--availability',$plan.availability,'--castle-index',[string]$plan.castle_index)
        if ($plan.minimap_viewport) { $verifyArgs+='--minimap-viewport' }
        $verified=Invoke-FramedPythonJson $plan.python $verifyArgs
        if ($verified.probe_sha256 -cne $plan.probe_sha256 -or $verified.probe -cne $prepared.probe) { throw 'Fresh copied candidate reconstruction differs from the plan.' }
        $launchStart=[datetime]::UtcNow
        $summary.launch_attempted=$true
        $session=Start-FramedHidden $plan $probePath $logPath $launch
        $summary.executed=$true; $summary.cdb=$session.identity
        $summary.hidden_desktop=$session.desktop_name; $summary.command_line=$session.command_line
        $watch=[Diagnostics.Stopwatch]::StartNew()
        while ($watch.Elapsed.TotalSeconds -lt 120) {
            Find-FramedOwnedChildren $plan $session $launchStart $owned
            $text=Read-FramedLog $logPath
            if (Test-FramedModalReady $text) {
                $summary.trace=Invoke-FramedPythonJson $plan.python @($plan.trace,'--log',$logPath,'--packet',$packetPath,
                    '--original',$plan.original,'--candidate',$plan.candidate_path,'--probe',$probePath) -PermitFailure
                Write-FramedJson (Join-Path $plan.out_dir 'trace.json') $summary.trace
                $surface=Assert-FramedSurface $summary.trace $plan
                if ($owned.Count -ne 1) { throw 'Modal readiness lacks exactly one measured, owned candidate.' }
                if ($watch.Elapsed.TotalSeconds -ge 120) { throw 'Modal validation exceeded the capture deadline; no memory read is authorized.' }
                $summary.snapshot=Save-FramedSnapshot @($owned.Values)[0] $surface $rawPath
                break
            }
            if (Test-FramedProcessExited $session) { throw 'Debugger exited before accepted modal readiness.' }
            Start-Sleep -Milliseconds 100
        }
        if (-not $summary.snapshot) { throw 'The 120-second modal capture deadline expired without a snapshot.' }
    } catch { $summary.failures += $_.Exception.Message }
    finally {
        if (-not $session -and $launch.session) {
            $session=$launch.session; $summary.executed=$true; $summary.cdb=$session.identity
            $summary.hidden_desktop=$session.desktop_name; $summary.command_line=$session.command_line
        }
        if ($session) {
            # Attempt identity acquisition even after an early polling/parser failure.
            try { Find-FramedOwnedChildren $plan $session $launchStart $owned } catch { $summary.failures += $_.Exception.Message }
            $summary.candidates=@($owned.Values | ForEach-Object { $_.identity })
            # Debugger FIRST. Retained kernel handles cannot target a reused PID.
            try { $summary.cleanup.cdb=Stop-FramedOwned $session } catch { $summary.failures += $_.Exception.Message }
            foreach ($game in $owned.Values) {
                try { $summary.cleanup.candidates += (Stop-FramedOwned $game) } catch { $summary.failures += $_.Exception.Message }
            }
            try { $summary.cleanup.desktop_closed=Close-FramedDesktop $session } catch { $summary.failures += $_.Exception.Message }
            if (-not $summary.cleanup.cdb.absent -or -not $summary.cleanup.cdb.handle_closed -or
                $summary.cleanup.candidates.Count -ne 1 -or @($summary.cleanup.candidates | Where-Object { -not $_.absent -or -not $_.handle_closed }).Count -or
                -not $summary.cleanup.desktop_closed) { $summary.failures += 'Exact owned-process absence/handle cleanup was not fully verified.' }
        }
        # Preserve and convert any captured raw data even when a later cleanup gate failed.
        if ($summary.snapshot) {
            try {
                if (-not (Test-Path -LiteralPath $plan.palette_path -PathType Leaf) -or (Get-Item -LiteralPath $plan.palette_path).Length -ne 1024) { throw 'Fresh proxy palette is missing or has the wrong size.' }
                $summary.palette=@{ path=$plan.palette_path; sha256=(Get-FramedHash $plan.palette_path); bytes=1024 }
                $pngPath=Join-Path $plan.out_dir 'surface.png'; $metaPath=Join-Path $plan.out_dir 'surface.png.json'
                $convertOutput = & $plan.python -B $plan.converter $rawPath --width $plan.width --height $plan.height --pitch $plan.width --output $pngPath --metadata $metaPath --log $logPath --palette $plan.palette_path
                if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $metaPath)) { throw 'Raw-to-PNG conversion failed; raw capture is preserved.' }
                $summary.png=[IO.File]::ReadAllText($metaPath) | ConvertFrom-Json
                if ($summary.png.palette_mode -ne 'directdraw-palette' -or $summary.png.raw_sha256 -cne $summary.snapshot.sha256 -or
                    $summary.png.png_sha256 -cne (Get-FramedHash $pngPath)) { throw 'PNG conversion metadata does not bind the fresh palette and raw capture.' }
            } catch { $summary.failures += $_.Exception.Message }
        }
        if ($summary.executed) {
            try {
                $summary.postrun_identity=@{ original_sha256=(Get-FramedHash $plan.original); input_candidate_sha256=(Get-FramedHash $plan.input_candidate)
                    candidate_sha256=(Get-FramedHash $plan.candidate_path); proxy_sha256=(Get-FramedHash $plan.proxy_path) }
                if ($summary.postrun_identity.original_sha256 -cne $plan.original_sha256 -or
                    $summary.postrun_identity.input_candidate_sha256 -cne $plan.candidate_sha256 -or
                    $summary.postrun_identity.candidate_sha256 -cne $plan.candidate_sha256 -or
                    $summary.postrun_identity.proxy_sha256 -cne $plan.proxy_sha256) { throw 'Post-run executable or proxy identity changed.' }
            } catch { $summary.failures += $_.Exception.Message }
        }
        $summary.finished_at=[datetime]::UtcNow.ToString('o')
        $summary.passed=($summary.executed -and $summary.failures.Count -eq 0 -and $null -ne $summary.snapshot -and $null -ne $summary.png)
        if ($summary.passed) { $summary.status='bounded_hidden_modal_capture' }
        if ($outputCreated) { Write-FramedJson (Join-Path $plan.out_dir 'summary.json') $summary }
    }
    return $summary
}

try {
    $options=@{ Original=$Original; InputCandidate=$InputCandidate; ProxyBuildManifest=$ProxyBuildManifest; WorkDir=$WorkDir
        CandidateDir=$CandidateDir; OutDir=$OutDir; Route=$Route; CastleIndex=$CastleIndex; Availability=$Availability
        Resolution=$Resolution; MinimapViewport=[bool]$MinimapViewport; Execute=[bool]$Execute }
    $bundle=New-FramedCapturePlan $options
    $result=Invoke-FramedCapture $bundle -DoExecute:$Execute
    $result | ConvertTo-Json -Depth 80
    if ($Execute -and -not $result.passed) { exit 1 }
} catch {
    @{ schema='clash95_framed_screen_capture_v1'; passed=$false; status='preparation_failed'; executed=$false
        failures=@($_.Exception.Message); manual_input_proof=$false; promotion_ready=$false } | ConvertTo-Json -Depth 10
    exit 1
}
