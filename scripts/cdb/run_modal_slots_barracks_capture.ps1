<# Hidden, controlled owned-modal-canvas capture. Default is an offline plan only.
   This does not prove natural selection, manual input, visible composition or promotion.
   No existing harness is dot-sourced. All native code is initialized only after -Execute.
#>
[CmdletBinding()]
param(
    [string]$Original = 'C:\Clash\clash95.exe',
    [Parameter(Mandatory=$true)][string]$InputCandidate,
    [Parameter(Mandatory=$true)][string]$CandidateManifest,
    [Parameter(Mandatory=$true)][string]$ProxyBuildManifest,
    [Parameter(Mandatory=$true)][string]$WorkDir,
    [Parameter(Mandatory=$true)][string]$CandidateDir,
    [Parameter(Mandatory=$true)][string]$OutDir,
    [ValidateSet('barracks')]
    [string]$Route = 'barracks',
    [ValidateRange(0,3)][int]$CastleIndex = 0,
    [ValidateSet('existing_flags','construct_all')][string]$Availability = 'existing_flags',
    [string]$Resolution = '800x600',
    [switch]$Execute
)
$ErrorActionPreference = 'Stop'
# Only this PowerShell process is affected. Preserve Unicode packet rationale
# through redirected stdout instead of the Windows PowerShell OEM code page.
$OutputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
$script:RepoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$script:Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-modalslots-validation'

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

function New-CanvasCapturePlan {
    param($Options)
    $originalPath = Resolve-CanvasPath $Options.Original -Kind file
    $inputPath = Resolve-CanvasPath $Options.InputCandidate -Root 'C:\ClashTests' -Kind file
    $candidateManifestPath = Resolve-CanvasPath $Options.CandidateManifest -Root 'C:\ClashTests' -Kind file
    $manifestPath = Resolve-CanvasPath $Options.ProxyBuildManifest -Root 'C:\ClashTests' -Kind file
    $workingPath = Resolve-CanvasPath $Options.WorkDir -Root 'C:\ClashTests' -Kind directory
    $candidateDirectory = Resolve-CanvasPath $Options.CandidateDir -Root 'C:\ClashTests' -Kind new
    $outputDirectory = Resolve-CanvasPath $Options.OutDir -Root 'C:\ClashCaptures' -Kind new
    if ($outputDirectory -match '[^\x20-\x7e]' -or $outputDirectory -match '[$";\r\n]' -or $outputDirectory.Length -gt 3500) {
        throw 'Canonical command files require bounded ASCII paths without argument tokens.'
    }
    if ($Options.Resolution -notmatch '^([0-9]{3,4})x([0-9]{3,4})$') { throw 'Resolution must be canonical WxH.' }
    $width = [int]$Matches[1]; $height = [int]$Matches[2]
    if ($width -lt 640 -or $height -lt 480 -or $width -gt 8192 -or $height -gt 8192 -or ($width % 2) -or ($height % 2)) { throw 'Unsupported physical resolution.' }
    $python = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    $cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe'
    $python = Resolve-CanvasPath $python -Kind file
    $cdb = Resolve-CanvasPath $cdb -Kind file
    $trace = Resolve-CanvasPath (Join-Path $script:RepoRoot 'tools\modal_slots_barracks_trace.py') -Kind file
    $producer = Resolve-CanvasPath (Join-Path $script:RepoRoot 'tools\modal_slots_barracks_probe.py') -Kind file
    $converter = Resolve-CanvasPath (Join-Path $script:RepoRoot 'tools\cdb_surface_dump_to_png.py') -Kind file
    $proxySource = Resolve-CanvasPath (Join-Path $script:RepoRoot 'src\ddraw_surfdump_proxy\ddraw_surfdump_proxy.cpp') -Kind file
    $manifest = [IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json
    $proxyOutput = Resolve-CanvasPath ([string]$manifest.output) -Root 'C:\ClashTests' -Kind file
    $sourceHash = Get-CanvasHash $proxySource
    $proxyHash = Get-CanvasHash $proxyOutput
    if ($manifest.generated_by -cne 'clash-hd-surface-dump-proxy' -or
        [IO.Path]::GetFullPath([string]$manifest.source) -ine $proxySource -or
        $manifest.source_sha256 -inotmatch '^[a-f0-9]{64}$' -or $manifest.source_sha256 -ine $sourceHash -or
        $manifest.output_sha256 -inotmatch '^[a-f0-9]{64}$' -or $manifest.output_sha256 -ine $proxyHash -or
        [IO.Path]::GetFileName($proxyOutput) -ine 'ddraw.dll') { throw 'Proxy manifest does not authenticate the current source and binary.' }
    $candidateHash = Get-CanvasHash $inputPath
    $prepareArgs = @($trace,'--prepare','--original',$originalPath,'--candidate',$inputPath,
        '--candidate-manifest',$candidateManifestPath,'--candidate-sha256',$candidateHash,'--stage',$script:Stage,'--resolution',$Options.Resolution,
        '--route',$Options.Route,'--availability',$Options.Availability,'--castle-index',[string]$Options.CastleIndex)
    if ($Options.MinimapViewport) { $prepareArgs += '--minimap-viewport' }
    $prepared = Invoke-CanvasPythonJson $python $prepareArgs
    if ($prepared.packet.prepared -isnot [bool] -or -not $prepared.packet.prepared -or
        $prepared.packet.candidate_sha256 -cne $candidateHash -or $prepared.packet.stage -cne $script:Stage -or
        $prepared.packet.resolution -cne $Options.Resolution -or -not $prepared.probe -or
        $prepared.probe_sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Candidate preparation did not produce its bound packet and compiled probe.' }
    # Repeated dry-run/Execute calls with the same new directory describe the same
    # executable path. Its directory must remain nonexistent until execution.
    $candidateName = Get-CanvasCandidateName $candidateDirectory $Options.Route $Options.Resolution
    if ($candidateName -ieq [IO.Path]::GetFileName($inputPath)) { throw 'The copied executable must have a new basename.' }
    $plan = [ordered]@{
        schema='clash95_modal_slots_capture_plan_v1'; environment='hidden_cdb_host'; execute=[bool]$Options.Execute
        stage=$script:Stage; resolution=$Options.Resolution; width=$width; height=$height
        route=$Options.Route; castle_index=$Options.CastleIndex; availability=$Options.Availability
        minimap_viewport=[bool]$Options.MinimapViewport; deadline_seconds=300
        original=$originalPath; original_sha256=(Get-CanvasHash $originalPath)
        input_candidate=$inputPath; candidate_sha256=$candidateHash; candidate_dir=$candidateDirectory
        candidate_manifest=$candidateManifestPath; candidate_manifest_sha256=(Get-CanvasHash $candidateManifestPath)
        candidate_path=(Join-Path $candidateDirectory $candidateName); work_dir=$workingPath; out_dir=$outputDirectory
        proxy_manifest=$manifestPath; proxy_manifest_sha256=(Get-CanvasHash $manifestPath)
        proxy_source=$proxySource; proxy_source_sha256=$sourceHash; proxy_input=$proxyOutput; proxy_sha256=$proxyHash
        proxy_path=(Join-Path $candidateDirectory 'ddraw.dll'); palette_path=(Join-Path $candidateDirectory 'ddraw_surfdump_palette.bin')
        python=$python; cdb=$cdb; trace=$trace; converter=$converter
        host_path=$PSCommandPath; host_sha256=(Get-CanvasHash $PSCommandPath)
        producer=$producer; producer_sha256=(Get-CanvasHash $producer)
        trace_sha256=(Get-CanvasHash $trace); converter_sha256=(Get-CanvasHash $converter)
        python_sha256=(Get-CanvasHash $python); cdb_sha256=(Get-CanvasHash $cdb)
        probe_sha256=$prepared.probe_sha256
        canvas_state_va=$prepared.packet.canvas_state_va
        canvas_state_offsets=$prepared.packet.canvas_state_offsets
        stop_va=$prepared.packet.stop_va
        child_environment=@{ CLASH_PROXY_PRESENT='0'; parent_environment_modified=$false }
        manual_input_proof=$false; visible_composition_proof=$false; promotion_ready=$false
        limits=@('Controlled native dispatch and optional availability mutation; no natural-input proof.',
            'Three paused physical/native snapshots with unchanged ownership; primary-only overlays remain outside the claim.',
            'Phase1 first-present capture proves neither native exit restoration nor destructor/free execution.',
            'The provided isolated work directory may receive native game configuration/save writes.')
    }
    return @{ plan=$plan; prepared=$prepared }
}

function Test-CanvasModalReady {
    param([string]$Log)
    # Complete, exact line only. Earlier map readiness never authorizes a read.
    return [regex]::IsMatch($Log, '(?m)^MCAP_SURFDUMP_HOST_READY\r?\n')
}

function Read-CanvasLog {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return '' }
    # CDB retains a writable log handle while paused. Do not deny its writer.
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    $reader=New-Object IO.StreamReader $stream
    try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
}

function Read-CanvasLogBytes {
    param([string]$Path)
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    $copy=New-Object IO.MemoryStream
    try {
        if ($stream.Length -gt 16777216) { throw 'Debugger log exceeds the frozen parser bound.' }
        $stream.CopyTo($copy); return ,$copy.ToArray()
    } finally { $copy.Dispose();$stream.Dispose() }
}

function Get-CanvasBytesHash {
    param([byte[]]$Bytes)
    $hash=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() }
    finally { $hash.Dispose() }
}

function Assert-CanvasSurface {
    param($Report, $Plan)
    if ($Report.passed -isnot [bool] -or -not $Report.passed -or
        $Report.ready_for_host_capture -isnot [bool] -or -not $Report.ready_for_host_capture -or
        $Report.schema -cne 'clash95_modal_slots_trace_v1' -or $Report.stage -cne $Plan.stage -or
        $Report.resolution -cne $Plan.resolution -or $Report.route -cne $Plan.route -or
        $Report.candidate_sha256 -cne $Plan.candidate_sha256 -or
        $Report.source.original_sha256 -cne $Plan.original_sha256 -or
        $Report.source.generated_probe_sha256 -cne $Plan.probe_sha256 -or
        $Report.source.validator_sha256 -cne $Plan.trace_sha256 -or
        $Report.source.log_raw_sha256 -cnotmatch '^[a-f0-9]{64}$' -or
        $Report.initial_map_trace.passed -isnot [bool] -or -not $Report.initial_map_trace.passed -or
        $Report.slot_trace.passed -isnot [bool] -or -not $Report.slot_trace.passed -or
        $Report.slot_trace.raw_records.Count -ne 12 -or
        $Report.modal_sequence.sequence_passed -isnot [bool] -or -not $Report.modal_sequence.sequence_passed) {
        throw 'Full source-bound owned-canvas trace did not authorize host capture.'
    }
    $s = $Report.surface
    foreach ($name in @('surface','width','height','base','bytes','tid','eip','esp')) {
        if ($s.$name -isnot [int] -and $s.$name -isnot [long]) { throw "Surface field $name must be an integer." }
    }
    if ($s.width -ne $Plan.width -or $s.height -ne $Plan.height -or $s.bytes -ne ([long]$Plan.width * $Plan.height) -or
        $s.bytes -gt 67108864 -or $s.surface -lt 65536 -or $s.surface -ge 4294967108 -or $s.surface -eq 0x51d4c0 -or
        $s.base -lt 65536 -or ([long]$s.base + $s.bytes) -gt 4294967296 -or
        $s.tid -le 0 -or $s.eip -ne $Plan.stop_va -or $s.esp -le 0 -or ($s.esp % 4) -or $s.route -cne $Plan.route) { throw 'Validated surface is outside the bounded native memory-surface contract.' }
    $rows=@($Report.modal_sequence.raw_records | Where-Object { $_.marker -ceq 'MCAP_CANVAS' -and $_.values.event -ceq 'READY' })
    if ($rows.Count -ne 1) { throw 'The physical capture lacks one exact owned-canvas READY observation.' }
    $v=$rows[0].values
    foreach ($name in @('state','phase','tid','eip','esp','root_esp','physical','native','physical_pixels','native_pixels','allocations','frees',
        'mirrors','enter_status','mirror_status','leave_status','fault','native_width','native_height','physical_width','physical_height','native_com')) {
        if ($v.$name -isnot [int] -and $v.$name -isnot [long]) { throw ('Canvas field must be an integer: '+$name) }
    }
    if ($v.state -ne $Plan.canvas_state_va -or $v.physical -ne $s.surface -or $v.physical_pixels -ne $s.base -or
        $v.tid -ne $s.tid -or $v.eip -ne $s.eip -or $v.esp -ne $s.esp -or $v.phase -ne 1 -or
        $v.allocations -ne 1 -or $v.frees -ne 0 -or $v.fault -ne 0 -or $v.enter_status -ne 1 -or
        $v.mirror_status -ne 1 -or $v.leave_status -ne 0 -or $v.mirrors -ne $(if ($Plan.route -eq 'castle_overview') {2} else {3}) -or
        $v.native_width -ne 640 -or $v.native_height -ne 480 -or $v.native_com -ne 0 -or
        $v.physical_width -ne $Plan.width -or $v.physical_height -ne $Plan.height -or $v.native -eq $v.physical -or
        $v.native -eq 0x51d4c0 -or $v.native -lt 65536 -or $v.native -ge 4294967108 -or
        $v.native_pixels -lt 65536 -or ($v.native_pixels+307200) -gt 4294967296 -or
        -not (($v.native_pixels+307200) -le $s.base -or ($s.base+$s.bytes) -le $v.native_pixels)) {
        throw 'Owned native640 and physical HD identity/counter contract differs.'
    }
    $offsets=@{phase=0;physical=4;native=8;saved_render=12;root_esp=16;owner_tid=20;enter_status=24;mirror_status=28;leave_status=32;
        fault=36;allocations=40;frees=44;mirrors=48;pending_header=52;pending_pixels=56;native_pixels=60;physical_pixels=64}
    if ($Plan.canvas_state_va -lt 65536 -or ($Plan.canvas_state_va+128) -gt 4294967296) {throw 'Canvas state range is unbounded.'}
    foreach ($name in $offsets.Keys) {
        if ($Plan.canvas_state_offsets.$name -isnot [int] -or $Plan.canvas_state_offsets.$name -ne $offsets[$name]) {throw ('Unreviewed canvas state offset: '+$name)}
    }
    return @{surface=$s;canvas=$v}
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

function Save-CanvasSnapshot {
    param($OwnedGame, $Evidence, [string]$RawPath, $Plan)
    $s=$Evidence.surface;$v=$Evidence.canvas;$began=[datetime]::UtcNow.ToString('o')
    $captures=@{};$prefix=[IO.Path]::Combine([IO.Path]::GetDirectoryName($RawPath),[IO.Path]::GetFileNameWithoutExtension($RawPath))
    $nativePath=Join-Path ([IO.Path]::GetDirectoryName($RawPath)) 'native-surface.raw'
    foreach ($phase in @('before','after')) {
        $phaseRows=@{}
        # Exact state/E0 and both headers surround one read of each distinct
        # physical-HD/native640 pixel allocation while the debugger is paused.
        foreach ($row in @(@('state',$Plan.canvas_state_va,128),@('e0',0x5202e0,4),
            @('physical_header',$s.surface,188),@('native_header',$v.native,188))) {
            $data=Read-CanvasMemory $OwnedGame.handle $row[1] $row[2]
            $path=$prefix+'-'+$phase+'-'+$row[0]+'.raw';[IO.File]::WriteAllBytes($path,$data)
            $phaseRows[$row[0]]=@{path=$path;address=$row[1];bytes=$row[2];sha256=(Get-CanvasHash $path);data=$data}
        }
        $state=$phaseRows.state.data;$header=$phaseRows.physical_header.data;$native=$phaseRows.native_header.data
        $expected=@{phase=1;physical=$s.surface;native=$v.native;root_esp=$v.root_esp;owner_tid=$s.tid;enter_status=1;
            mirror_status=1;leave_status=0;fault=0;allocations=1;frees=0;mirrors=$v.mirrors;
            pending_header=0;pending_pixels=0;native_pixels=$v.native_pixels;physical_pixels=$s.base}
        foreach ($key in $expected.Keys) {
            if ([BitConverter]::ToUInt32($state,$Plan.canvas_state_offsets.$key) -ne $expected[$key]) {throw ('Live canvas state differs: '+$phase+' '+$key)}
        }
        if ([BitConverter]::ToUInt32($phaseRows.e0.data,0) -ne $v.native -or
            [BitConverter]::ToUInt16($header,0) -ne $s.width -or [BitConverter]::ToUInt16($header,2) -ne $s.height -or
            [BitConverter]::ToUInt32($header,4) -ne $s.base -or [BitConverter]::ToUInt32($header,184) -ne 0x50ee24 -or
            [BitConverter]::ToUInt16($native,0) -ne 640 -or [BitConverter]::ToUInt16($native,2) -ne 480 -or
            [BitConverter]::ToUInt32($native,4) -ne $v.native_pixels -or [BitConverter]::ToUInt32($native,184) -ne 0x50ee24 -or
            [BitConverter]::ToUInt32($native,172) -ne 0) {throw 'Live native640/E0/physical mirror header contract differs.'}
        $captures[$phase]=$phaseRows
        if ($phase -eq 'before') {
            $pixels=Read-CanvasMemory $OwnedGame.handle $s.base $s.bytes
            [IO.File]::WriteAllBytes($RawPath,$pixels)
            $nativePixels=Read-CanvasMemory $OwnedGame.handle $v.native_pixels 307200
            [IO.File]::WriteAllBytes($nativePath,$nativePixels)
            [IO.File]::WriteAllBytes((Join-Path ([IO.Path]::GetDirectoryName($RawPath)) 'native-surface.header.bin'),$native)
        }
    }
    foreach ($name in @('state','e0','physical_header','native_header')) {
        if ($captures.before[$name].sha256 -cne $captures.after[$name].sha256) {throw ('Paused '+$name+' changed across the paired pixel reads.')}
        $captures.before[$name].Remove('data');$captures.after[$name].Remove('data')
    }
    return @{path=$RawPath;sha256=(Get-CanvasHash $RawPath);bytes=$pixels.Length;width=$s.width;height=$s.height;pitch=$s.width;
        pixel_reads=1;physical_header_reads=2;native_header_reads=2;state_reads=2;e0_reads=2;paused=$true;
        capture='owned_physical_mirror';state_va=$Plan.canvas_state_va;physical=$s.surface;physical_pixels=$s.base;
        native=@{path=$nativePath;sha256=(Get-CanvasHash $nativePath);bytes=307200;width=640;height=480;pitch=640;
            surface=$v.native;base=$v.native_pixels;pixel_reads=1;header=$captures.before.native_header};
        reads=$captures;started_at=$began;captured_at=[datetime]::UtcNow.ToString('o');game_identity=$OwnedGame.identity}
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

function Save-CanvasTriplet {
    param($OwnedGame, $Evidence, $Plan)
    $snapshots=@()
    foreach ($captureIndex in 1..3) {
        $directory=Join-Path $Plan.out_dir ('capture-'+$captureIndex)
        [void](New-Item -ItemType Directory -Path $directory)
        $snapshots+=Save-CanvasSnapshot $OwnedGame $Evidence (Join-Path $directory 'surface.raw') $Plan
    }
    $same=$true
    foreach ($snapshot in $snapshots) {
        if ($snapshot.sha256 -cne $snapshots[0].sha256 -or $snapshot.native.sha256 -cne $snapshots[0].native.sha256) {$same=$false}
        foreach ($name in @('state','e0','physical_header','native_header')) {
            if ($snapshot.reads.before[$name].sha256 -cne $snapshots[0].reads.before[$name].sha256) {$same=$false}
        }
    }
    # Return all completed reads even on mismatch; the caller retains them in
    # the final summary before failing the stability gate.
    return @{snapshots=$snapshots;clean_stable_pair=$same}
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

function Invoke-CanvasCapture {
    param($Bundle, [switch]$DoExecute)
    $plan=$Bundle.plan; $prepared=$Bundle.prepared
    if (-not $DoExecute) { return @{ status='dry_run'; executed=$false; plan=$plan; prepared=$prepared } }
    $summary = [ordered]@{ schema='clash95_modal_slots_capture_v1'; passed=$false; status='failed'; executed=$false; plan=$plan
        started_at=[datetime]::UtcNow.ToString('o'); finished_at=$null; failures=@(); trace=$null; snapshot=$null; png=$null
        cdb=$null; candidates=@(); cleanup=@{ cdb=$null; candidates=@(); desktop_closed=$false }
        manual_input_proof=$false; visible_composition_proof=$false; promotion_ready=$false }
    $session=$null; $owned=@{}; $outputCreated=$false; $launch=@{session=$null}
    $logPath=Join-Path $plan.out_dir 'cdb.log'; $probePath=Join-Path $plan.out_dir 'modal-slots-barracks.cdb'
    $packetPath=Join-Path $plan.out_dir 'packet.json'; $rawPath=Join-Path $plan.out_dir 'surface.raw'
    try {
        # No -Force, no reuse: never overwrite a previous artifact or candidate.
        [void](Resolve-CanvasPath $plan.out_dir -Root 'C:\ClashCaptures' -Kind new)
        [void](New-Item -ItemType Directory -Path $plan.out_dir)
        $outputCreated=$true
        [void](Resolve-CanvasPath $plan.candidate_dir -Root 'C:\ClashTests' -Kind new)
        [void](New-Item -ItemType Directory -Path $plan.candidate_dir)
        foreach ($pair in @(@($plan.original,$plan.original_sha256),@($plan.input_candidate,$plan.candidate_sha256),@($plan.candidate_manifest,$plan.candidate_manifest_sha256),
            @($plan.proxy_manifest,$plan.proxy_manifest_sha256),@($plan.proxy_source,$plan.proxy_source_sha256),@($plan.proxy_input,$plan.proxy_sha256),
            @($plan.host_path,$plan.host_sha256),@($plan.producer,$plan.producer_sha256),@($plan.trace,$plan.trace_sha256),@($plan.converter,$plan.converter_sha256),
            @($plan.python,$plan.python_sha256),@($plan.cdb,$plan.cdb_sha256))) {
            if ((Get-CanvasHash $pair[0]) -cne $pair[1]) { throw 'A planned source, runtime or input file changed before execution.' }
        }
        [IO.File]::Copy($plan.input_candidate,$plan.candidate_path,$false)
        [IO.File]::Copy($plan.proxy_input,$plan.proxy_path,$false)
        if ((Get-CanvasHash $plan.candidate_path) -cne $plan.candidate_sha256 -or (Get-CanvasHash $plan.proxy_path) -cne $plan.proxy_sha256) { throw 'Fresh candidate/proxy copy identity mismatch.' }
        Write-CanvasJson $packetPath $prepared.packet
        [IO.File]::WriteAllText($probePath,$prepared.probe,[Text.UTF8Encoding]::new($false))
        if ((Get-CanvasHash $probePath) -cne $plan.probe_sha256) { throw 'Compiled probe file differs from the prepared packet.' }
        Write-CanvasJson (Join-Path $plan.out_dir 'plan.json') $plan
        $summary.packet=@{path=$packetPath;sha256=(Get-CanvasHash $packetPath)}
        $summary.probe=@{path=$probePath;sha256=(Get-CanvasHash $probePath)}
        # Reconstruct against the COPIED file before launch, not merely its input path.
        $verifyArgs=@($plan.trace,'--prepare','--original',$plan.original,'--candidate',$plan.candidate_path,
            '--candidate-manifest',$plan.candidate_manifest,'--candidate-sha256',$plan.candidate_sha256,'--stage',$plan.stage,'--resolution',$plan.resolution,
            '--route',$plan.route,'--availability',$plan.availability,'--castle-index',[string]$plan.castle_index)
        if ($plan.minimap_viewport) { $verifyArgs+='--minimap-viewport' }
        $verified=Invoke-CanvasPythonJson $plan.python $verifyArgs
        if ($verified.probe_sha256 -cne $plan.probe_sha256 -or $verified.probe -cne $prepared.probe -or
            ($verified.packet | ConvertTo-Json -Depth 80 -Compress) -cne ($prepared.packet | ConvertTo-Json -Depth 80 -Compress)) { throw 'Fresh copied candidate reconstruction differs from the whole planned packet.' }
        $launchStart=[datetime]::UtcNow
        $summary.launch_attempted=$true
        $session=Start-CanvasHidden $plan $probePath $logPath $launch
        $summary.executed=$true; $summary.cdb=$session.identity
        $summary.hidden_desktop=$session.desktop_name; $summary.command_line=$session.command_line
        $watch=[Diagnostics.Stopwatch]::StartNew()
        while ($watch.Elapsed.TotalSeconds -lt 300) {
            Find-CanvasOwnedChildren $plan $session $launchStart $owned
            $text=Read-CanvasLog $logPath
            if (Test-CanvasModalReady $text) {
                $summary.trace=Invoke-CanvasPythonJson $plan.python @($plan.trace,'--log',$logPath,'--packet',$packetPath,
                    '--original',$plan.original,'--candidate',$plan.candidate_path,'--probe',$probePath) -PermitFailure -TimeoutMilliseconds ([Math]::Max(1,[Math]::Min(120000,300000-[int]$watch.ElapsedMilliseconds)))
                Write-CanvasJson (Join-Path $plan.out_dir 'trace.json') $summary.trace
                $surface=Assert-CanvasSurface $summary.trace $plan
                if ($owned.Count -ne 1) { throw 'Modal readiness lacks exactly one measured, owned candidate.' }
                if ($watch.Elapsed.TotalSeconds -ge 300) { throw 'Modal validation exceeded the capture deadline; no memory read is authorized.' }
                $prefix=Read-CanvasLogBytes $logPath
                if ((Get-CanvasBytesHash $prefix) -cne $summary.trace.source.log_raw_sha256) {throw 'Validated raw log changed before capture.'}
                $prefixPath=Join-Path $plan.out_dir 'capture-prefix.log';[IO.File]::WriteAllBytes($prefixPath,$prefix)
                $summary.capture_prefix=@{path=$prefixPath;bytes=$prefix.Length;sha256=(Get-CanvasHash $prefixPath)}
                $triplet=Save-CanvasTriplet @($owned.Values)[0] $surface $plan
                $summary.snapshots=$triplet.snapshots
                $summary.snapshot=$summary.snapshots[0]
                $rawPath=$summary.snapshot.path
                $summary.clean_stable_pair=$triplet.clean_stable_pair
                if (-not $summary.clean_stable_pair) {throw 'Three paused physical/native captures differ; raw captures are preserved.'}
                if ((Get-CanvasBytesHash (Read-CanvasLogBytes $logPath)) -cne $summary.capture_prefix.sha256) {throw 'Debugger log changed across the paused raw capture.'}
                if ($watch.Elapsed.TotalSeconds -ge 300) {throw 'Paired capture exceeded the deadline.'}
                break
            }
            if (Test-CanvasProcessExited $session) { throw 'Debugger exited before accepted modal readiness.' }
            Start-Sleep -Milliseconds 100
        }
        if (-not $summary.snapshot) { throw 'The 300-second modal capture deadline expired without a snapshot.' }
    } catch { $summary.failures += $_.Exception.Message }
    finally {
        if (-not $session -and $launch.session) {
            $session=$launch.session; $summary.executed=$true; $summary.cdb=$session.identity
            $summary.hidden_desktop=$session.desktop_name; $summary.command_line=$session.command_line
        }
        if ($session) {
            # Attempt identity acquisition even after an early polling/parser failure.
            try { Find-CanvasOwnedChildren $plan $session $launchStart $owned } catch { $summary.failures += $_.Exception.Message }
            $summary.candidates=@($owned.Values | ForEach-Object { $_.identity })
            # Debugger FIRST. Retained kernel handles cannot target a reused PID.
            try { $summary.cleanup.cdb=Stop-CanvasOwned $session } catch { $summary.failures += $_.Exception.Message }
            foreach ($game in $owned.Values) {
                try { $summary.cleanup.candidates += (Stop-CanvasOwned $game) } catch { $summary.failures += $_.Exception.Message }
            }
            try { $summary.cleanup.desktop_closed=Close-CanvasDesktop $session } catch { $summary.failures += $_.Exception.Message }
            if (-not $summary.cleanup.cdb.absent -or -not $summary.cleanup.cdb.handle_closed -or
                $summary.cleanup.candidates.Count -ne 1 -or @($summary.cleanup.candidates | Where-Object { -not $_.absent -or -not $_.handle_closed }).Count -or
                -not $summary.cleanup.desktop_closed) { $summary.failures += 'Exact owned-process absence/handle cleanup was not fully verified.' }
        }
        if ($summary.snapshot) {
            try {
                # Preserve the earlier prefix and revalidate every later actual
                # record, including the debugger termination tail.
                $summary.final_trace=Invoke-CanvasPythonJson $plan.python @($plan.trace,'--log',$logPath,'--packet',$packetPath,
                    '--original',$plan.original,'--candidate',$plan.candidate_path,'--probe',$probePath) -PermitFailure
                Write-CanvasJson (Join-Path $plan.out_dir 'trace-final.json') $summary.final_trace
                $finalBytes=Read-CanvasLogBytes $logPath
                $finalHash=Get-CanvasBytesHash $finalBytes
                $summary.final_log=@{path=$logPath;sha256=$finalHash;bytes=$finalBytes.Length;capture_prefix_preserved=$false}
                $originalPrefix=[IO.File]::ReadAllBytes($summary.capture_prefix.path)
                if ((Get-CanvasBytesHash $originalPrefix) -cne $summary.capture_prefix.sha256 -or $finalBytes.Length -lt $originalPrefix.Length) {throw 'Immutable capture prefix was changed or truncated.'}
                $finalPrefix=New-Object byte[] $originalPrefix.Length;[Array]::Copy($finalBytes,$finalPrefix,$finalPrefix.Length)
                if ((Get-CanvasBytesHash $finalPrefix) -cne $summary.capture_prefix.sha256) {throw 'Final log no longer begins with the actual captured prefix.'}
                if ($finalHash -cne $summary.final_trace.source.log_raw_sha256) {throw 'Final raw log differs from the complete parser input.'}
                $summary.final_log.capture_prefix_preserved=$true
                [void](Assert-CanvasSurface $summary.final_trace $plan)
                if ((Get-CanvasHash $packetPath) -cne $summary.packet.sha256 -or
                    (Get-CanvasHash $probePath) -cne $summary.probe.sha256) {throw 'Packet/probe changed after capture.'}
            } catch {$summary.failures+=$_.Exception.Message}
        }
        # Preserve and convert captured physical raw even when final trace or cleanup failed.
        if ($summary.snapshot) {
            try {
                if (-not (Test-Path -LiteralPath $plan.palette_path -PathType Leaf) -or (Get-Item -LiteralPath $plan.palette_path).Length -ne 1024) { throw 'Fresh proxy palette is missing or has the wrong size.' }
                $summary.palette=@{ path=$plan.palette_path; sha256=(Get-CanvasHash $plan.palette_path); bytes=1024 }
                $pngPath=Join-Path $plan.out_dir 'surface.png'; $metaPath=Join-Path $plan.out_dir 'surface.png.json'
                $convertOutput = & $plan.python -B $plan.converter $rawPath --width $plan.width --height $plan.height --pitch $plan.width --output $pngPath --metadata $metaPath --log $summary.capture_prefix.path --palette $plan.palette_path
                if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $metaPath)) { throw 'Raw-to-PNG conversion failed; raw capture is preserved.' }
                $summary.png=[IO.File]::ReadAllText($metaPath) | ConvertFrom-Json
                if ($summary.png.palette_mode -ne 'directdraw-palette' -or $summary.png.raw_sha256 -cne $summary.snapshot.sha256 -or
                    $summary.png.png_sha256 -cne (Get-CanvasHash $pngPath)) { throw 'PNG conversion metadata does not bind the fresh palette and raw capture.' }
            } catch { $summary.failures += $_.Exception.Message }
        }
        if ($summary.executed) {
            try {
                $summary.postrun_identity=@{ original_sha256=(Get-CanvasHash $plan.original); input_candidate_sha256=(Get-CanvasHash $plan.input_candidate)
                    candidate_sha256=(Get-CanvasHash $plan.candidate_path); proxy_sha256=(Get-CanvasHash $plan.proxy_path) }
                if ($summary.postrun_identity.original_sha256 -cne $plan.original_sha256 -or
                    $summary.postrun_identity.input_candidate_sha256 -cne $plan.candidate_sha256 -or
                    $summary.postrun_identity.candidate_sha256 -cne $plan.candidate_sha256 -or
                    $summary.postrun_identity.proxy_sha256 -cne $plan.proxy_sha256) { throw 'Post-run executable or proxy identity changed.' }
            } catch { $summary.failures += $_.Exception.Message }
        }
        $summary.finished_at=[datetime]::UtcNow.ToString('o')
        $summary.passed=($summary.executed -and $summary.failures.Count -eq 0 -and $null -ne $summary.snapshot -and $null -ne $summary.png -and $summary.clean_stable_pair)
        if ($summary.passed) { $summary.status='bounded_hidden_modal_canvas_capture' }
        if ($outputCreated) { Write-CanvasJson (Join-Path $plan.out_dir 'summary.json') $summary }
    }
    return $summary
}

try {
    $options=@{ Original=$Original; InputCandidate=$InputCandidate; ProxyBuildManifest=$ProxyBuildManifest; WorkDir=$WorkDir
        CandidateDir=$CandidateDir; OutDir=$OutDir; Route=$Route; CastleIndex=$CastleIndex; Availability=$Availability; CandidateManifest=$CandidateManifest
        Resolution=$Resolution; MinimapViewport=$true; Execute=[bool]$Execute }
    $bundle=New-CanvasCapturePlan $options
    $result=Invoke-CanvasCapture $bundle -DoExecute:$Execute
    $result | ConvertTo-Json -Depth 80
    if ($Execute -and -not $result.passed) { exit 1 }
} catch {
    $failure=@{ schema='clash95_modal_slots_capture_v1'; passed=$false; status='preparation_failed'; executed=$false
        failures=@($_.Exception.Message); manual_input_proof=$false; promotion_ready=$false }
    if ($null -ne $_.Exception.Data['CanvasPythonFailure']) {
        $failure.child_failure=$_.Exception.Data['CanvasPythonFailure']
    }
    $failure | ConvertTo-Json -Depth 10
    exit 1
}
