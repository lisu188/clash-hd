<# Hidden, controlled primary-stage native/physical/cached-primary capture. Default is an offline plan only.
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
$script:Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-modalprimary-validation'

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
        return ('modal-primary-' + $Route + '-' + $Resolution + '-' + $digest.Substring(0,16) + '.exe')
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
    $trace = Resolve-CanvasPath (Join-Path $script:RepoRoot 'tools\modal_primary_capture.py') -Kind file
    $producer = Resolve-CanvasPath (Join-Path $script:RepoRoot 'tools\modal_primary_capture.py') -Kind file
    $converter = Resolve-CanvasPath (Join-Path $script:RepoRoot 'tools\cdb_surface_dump_to_png.py') -Kind file
    $proxySource = Resolve-CanvasPath (Join-Path $script:RepoRoot 'src\ddraw_surfdump_proxy\ddraw_surfdump_proxy.cpp') -Kind file
    $manifest = [IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json
    $proxyOutput = Resolve-CanvasPath ([string]$manifest.output) -Root 'C:\ClashTests' -Kind file
    $sourceHash = Get-CanvasHash $proxySource
    $proxyHash = Get-CanvasHash $proxyOutput
    if ($manifest.generated_by -cne 'clash-hd-surface-dump-proxy' -or
        (Get-CanvasHash (Resolve-CanvasPath ([string]$manifest.source) -Kind file)) -cne $sourceHash -or
        $proxyHash -cne 'b173a9dd4ce772eb5b56f341acdf4b329ed4ffdd638c1fce5cc37dd332804b70' -or
        $manifest.source_sha256 -inotmatch '^[a-f0-9]{64}$' -or $manifest.source_sha256 -ine $sourceHash -or
        $manifest.output_sha256 -inotmatch '^[a-f0-9]{64}$' -or $manifest.output_sha256 -ine $proxyHash -or
        [IO.Path]::GetFileName($proxyOutput) -ine 'ddraw.dll') { throw 'Proxy manifest does not authenticate the current source and binary.' }
    $candidateHash = Get-CanvasHash $inputPath
    $prepareArgs = @($trace,'--prepare','--original',$originalPath,'--candidate',$inputPath,
        '--candidate-manifest',$candidateManifestPath,'--candidate-sha256',$candidateHash,'--stage',$script:Stage,'--resolution',$Options.Resolution,
        '--route',$Options.Route,'--availability',$Options.Availability,'--castle-index',[string]$Options.CastleIndex,
        '--out-dir',$outputDirectory,'--proxy-manifest',$manifestPath)
    if ($Options.MinimapViewport) { $prepareArgs += '--minimap-viewport' }
    $prepared = Invoke-CanvasPythonJson $python $prepareArgs
    if ($prepared.packet.prepared -isnot [bool] -or -not $prepared.packet.prepared -or
        $prepared.packet.candidate_sha256 -cne $candidateHash -or $prepared.packet.stage -cne $script:Stage -or
        $prepared.packet.resolution -cne $Options.Resolution -or -not $prepared.probe -or
        $prepared.probe_sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Candidate preparation did not produce its bound packet and compiled probe.' }
    Assert-PrimaryCheckpointPlan $prepared.packet.checkpoints
    $readyScripts=Get-PrimaryReadyScriptPlan $prepared.ready_scripts $outputDirectory
    # Repeated dry-run/Execute calls with the same new directory describe the same
    # executable path. Its directory must remain nonexistent until execution.
    $candidateName = Get-CanvasCandidateName $candidateDirectory $Options.Route $Options.Resolution
    if ($candidateName -ieq [IO.Path]::GetFileName($inputPath)) { throw 'The copied executable must have a new basename.' }
    $plan = [ordered]@{
        schema='clash95_modal_primary_capture_plan_v1'; environment='hidden_cdb_host'; execute=[bool]$Options.Execute
        stage=$script:Stage; resolution=$Options.Resolution; width=$width; height=$height
        route=$Options.Route; castle_index=$Options.CastleIndex; availability=$Options.Availability
        minimap_viewport=[bool]$Options.MinimapViewport; deadline_seconds=600
        checkpoints=$prepared.packet.checkpoints; run_id=[IO.Path]::GetFileName($outputDirectory)
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
        primary_ready_scripts=$readyScripts
        primary_source=(Join-Path $script:RepoRoot 'tools\modal_slots_primary_surface.py');primary_source_sha256=(Get-CanvasHash (Join-Path $script:RepoRoot 'tools\modal_slots_primary_surface.py'))
        canvas_state_va=$prepared.packet.canvas_state_va
        canvas_state_offsets=$prepared.packet.canvas_state_offsets
        stop_va=$prepared.packet.stop_va
        child_environment=@{ CLASH_PROXY_PRESENT='0'; parent_environment_modified=$false }
        manual_input_proof=$false; visible_composition_proof=$false; promotion_ready=$false
        limits=@('Controlled native dispatch and optional availability mutation; no natural-input proof.',
            'Four ordered paused primary checkpoints; final native/physical/primary triplet with source-backed overlay audit.',
            'Phase1 first-present capture proves neither native exit restoration nor destructor/free execution.',
            'The provided isolated work directory may receive native game configuration/save writes.')
    }
    return @{ plan=$plan; prepared=$prepared }
}

function Assert-PrimaryCheckpointPlan {
    param($Rows)
    $names=@('full-published','placeholder-before','placeholder-after','final-ready')
    $nativeSites=@(0,0x432f9e,0x432fa1,0x433e77)
    if ($Rows.Count -ne 4) {throw 'The primary plan requires exactly four native checkpoints.'}
    for ($i=0;$i -lt 4;$i++) {
        if ($Rows[$i].name -cne $names[$i] -or $Rows[$i].index -isnot [int] -or $Rows[$i].index -ne $i -or
            $Rows[$i].eips.Count -ne $(if ($i -eq 0) {2} else {1}) -or
            ($i -gt 0 -and $Rows[$i].eips[0] -ne $nativeSites[$i])) {throw 'Primary checkpoint plan site, order or type differs.'}
        foreach ($site in $Rows[$i].eips) {
            if (($site -isnot [int] -and $site -isnot [long]) -or $site -lt 0x400000 -or $site -ge 0x7ffe0000) {throw 'Primary checkpoint code site is outside the supported image range.'}
        }
        if (@($Rows[$i].eips | Select-Object -Unique).Count -ne $Rows[$i].eips.Count) {throw 'Repeated primary checkpoint code site.'}
    }
}

function Get-PrimaryReadyScriptPlan {
    param($Scripts,[string]$OutputDirectory)
    $names=@('full-published','placeholder-before','placeholder-after','final-ready')
    $properties=@($Scripts.PSObject.Properties.Name | Sort-Object)
    if (($properties -join ',') -cne (($names | Sort-Object) -join ',')) {throw 'Exactly four named primary scripts are required.'}
    $records=[ordered]@{}
    foreach ($name in $names) {
        $row=$Scripts.$name;$path=Join-Path $OutputDirectory ('primary-'+$name+'.cdb')
        if ($row.path -cne $path -or $row.text -isnot [string] -or -not $row.text -or
            $row.text -match '[^\x00-\x7f]' -or $row.sha256 -cnotmatch '^[a-f0-9]{64}$' -or
            (Get-CanvasBytesHash ([Text.Encoding]::ASCII.GetBytes($row.text))) -cne $row.sha256) {throw 'Primary checkpoint script path, text or hash differs.'}
        $records[$name]=@{path=$path;sha256=$row.sha256;bytes=[Text.Encoding]::ASCII.GetByteCount($row.text)}
    }
    return $records
}

function Test-CanvasModalReady {
    param([string]$Log)
    # Complete, exact line only. Earlier map readiness never authorizes a read.
    return [regex]::IsMatch($Log, '(?m)^MPRI_HOST_READY\r?\n')
}

function Get-PrimaryCheckpointReady {
    param([string]$Log,[ValidateRange(0,4)][int]$NextIndex)
    $names=@('full-published','placeholder-before','placeholder-after','final-ready')
    $matches=[regex]::Matches($Log,'(?m)^MPCAP_HOST_READY name=([^\r\n]+)\r?\n')
    if ($matches.Count -gt 4 -or $matches.Count -gt $NextIndex+1) {throw 'Unexpected duplicate or skipped primary checkpoint.'}
    for ($i=0;$i -lt $matches.Count;$i++) {
        if ($matches[$i].Groups[1].Value -cne $names[$i]) {throw 'Primary checkpoints are out of order.'}
    }
    if ($NextIndex -lt 4 -and $matches.Count -eq $NextIndex+1) {return $names[$NextIndex]}
    return $null
}

function Get-CanvasDebuggerCommandFailure {
    param([string]$Log)
    # These are debugger command diagnostics, not native exception evidence.
    # Anchor actual output lines so echoed command source cannot match.
    $lineNumber=0
    foreach ($line in ($Log -split "`n")) {
        $lineNumber++
        if ($line -match '(?i)^\s*(?:[0-9]+:[0-9]+>\s*)?(?:Unable to insert breakpoint\b|bp[0-9]+\s+at\s+[^\r\n]*\bfailed\b|(?:\^\s*)?Syntax error\b|Command file execution failed\b)') {
            return @{classification='debugger_command_failure';line=$lineNumber;text=$line.TrimEnd("`r")}
        }
    }
    return $null
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
    $checkpoint=$Report.capture_checkpoint
    $names=@('full-published','placeholder-before','placeholder-after','final-ready')
    if ($null -eq $checkpoint -or $checkpoint.index -isnot [int] -or $checkpoint.index -lt 0 -or $checkpoint.index -gt 3 -or
        $checkpoint.name -cne $names[$checkpoint.index] -or $Plan.checkpoints.Count -ne 4 -or
        $Plan.checkpoints[$checkpoint.index].name -cne $checkpoint.name -or
        $Plan.checkpoints[$checkpoint.index].index -ne $checkpoint.index) {throw 'Capture lacks one exact declared primary checkpoint.'}
    if ($Report.passed -isnot [bool] -or -not $Report.passed -or
        $Report.ready_for_host_capture -isnot [bool] -or -not $Report.ready_for_host_capture -or
        $Report.schema -cne 'clash95_modal_primary_trace_v1' -or $Report.stage -cne $Plan.stage -or
        $Report.resolution -cne $Plan.resolution -or $Report.route -cne $Plan.route -or
        $Report.candidate_sha256 -cne $Plan.candidate_sha256 -or
        $Report.source.original_sha256 -cne $Plan.original_sha256 -or
        $Report.source.generated_probe_sha256 -cne $Plan.probe_sha256 -or
        $Report.source.validator_sha256 -cne $Plan.trace_sha256 -or
        $Report.source.log_raw_sha256 -cnotmatch '^[a-f0-9]{64}$' -or
        $Report.initial_map_trace.passed -isnot [bool] -or -not $Report.initial_map_trace.passed -or
        $Report.slot_trace.passed -isnot [bool] -or -not $Report.slot_trace.passed -or
        $Report.slot_trace.raw_records.Count -ne $(if ($checkpoint.index -eq 0) {0} else {12}) -or
        $Report.primary_sequence.passed -isnot [bool] -or -not $Report.primary_sequence.passed -or
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
        $s.tid -le 0 -or $s.eip -notin $Plan.checkpoints[$checkpoint.index].eips -or $s.esp -le 0 -or ($s.esp % 4) -or $s.route -cne $Plan.route) { throw 'Validated surface is outside the bounded native memory-surface contract.' }
    $v=$checkpoint.canvas
    if ($null -eq $v) {throw 'The physical capture lacks its current owned-canvas checkpoint observation.'}
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
 [StructLayout(LayoutKind.Sequential)] public struct SECURITY_ATTRIBUTES { public int length; public IntPtr descriptor; [MarshalAs(UnmanagedType.Bool)] public bool inherit; }
 [StructLayout(LayoutKind.Sequential)] public struct STARTUPINFOEX { public STARTUPINFO startup; public IntPtr attributes; }
 [DllImport("kernel32.dll", SetLastError=true)] static extern bool CreatePipe(out IntPtr read, out IntPtr write, ref SECURITY_ATTRIBUTES security, uint size);
 [DllImport("kernel32.dll", SetLastError=true)] static extern bool SetHandleInformation(IntPtr handle, uint mask, uint flags);
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr CreateFileW(string path, uint access, uint share, ref SECURITY_ATTRIBUTES security, uint disposition, uint flags, IntPtr template);
 [DllImport("kernel32.dll", SetLastError=true)] static extern bool InitializeProcThreadAttributeList(IntPtr list, int count, uint flags, ref IntPtr bytes);
 [DllImport("kernel32.dll")] static extern void DeleteProcThreadAttributeList(IntPtr list);
 [DllImport("kernel32.dll", SetLastError=true)] static extern bool UpdateProcThreadAttribute(IntPtr list, uint flags, IntPtr attribute, IntPtr value, IntPtr bytes, IntPtr previous, IntPtr returned);
 [DllImport("kernel32.dll", EntryPoint="CreateProcessW", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool CreateProcessWithAttributes(string app, StringBuilder command, IntPtr pa, IntPtr ta, bool inherit, uint flags, IntPtr environment, string workdir, ref STARTUPINFOEX startup, out PROCESS_INFORMATION info);
 [DllImport("kernel32.dll", SetLastError=true)] static extern bool WriteFile(IntPtr handle, byte[] bytes, uint count, out uint written, IntPtr overlapped);
 public static PROCESS_INFORMATION StartWithInput(string app, string command, string desktop, IntPtr environment, string workdir, out IntPtr inputWrite) {
  IntPtr read=IntPtr.Zero, write=IntPtr.Zero, sink=IntPtr.Zero, list=IntPtr.Zero, handles=IntPtr.Zero;
  bool initialized=false, transferred=false; inputWrite=IntPtr.Zero;
  try {
   var security=new SECURITY_ATTRIBUTES { length=Marshal.SizeOf(typeof(SECURITY_ATTRIBUTES)), inherit=true };
   if (!CreatePipe(out read,out write,ref security,0)) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
   if (!SetHandleInformation(write,1,0)) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
   sink=CreateFileW("NUL",0x40000000,3,ref security,3,0,IntPtr.Zero);
   if (sink==new IntPtr(-1)) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
   IntPtr count=IntPtr.Zero;
   InitializeProcThreadAttributeList(IntPtr.Zero,1,0,ref count);
   if (count.ToInt64()<=0 || count.ToInt64()>65536) throw new InvalidOperationException("Invalid process attribute allocation size.");
   list=Marshal.AllocHGlobal(count);
   if (!InitializeProcThreadAttributeList(list,1,0,ref count)) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
   initialized=true; handles=Marshal.AllocHGlobal(IntPtr.Size*2);
   Marshal.WriteIntPtr(handles,0,read); Marshal.WriteIntPtr(handles,IntPtr.Size,sink);
   if (!UpdateProcThreadAttribute(list,0,new IntPtr(0x20002),handles,new IntPtr(IntPtr.Size*2),IntPtr.Zero,IntPtr.Zero)) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
   var startup=new STARTUPINFOEX(); startup.startup.cb=Marshal.SizeOf(typeof(STARTUPINFOEX));
   startup.startup.desktop=desktop; startup.startup.flags=0x101; startup.startup.show=0;
   startup.startup.input=read; startup.startup.output=sink; startup.startup.error=sink; startup.attributes=list;
   PROCESS_INFORMATION info;
   if (!CreateProcessWithAttributes(app,new StringBuilder(command),IntPtr.Zero,IntPtr.Zero,true,0x80410,environment,workdir,ref startup,out info)) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
   inputWrite=write; transferred=true; return info;
  } finally {
   if (initialized) DeleteProcThreadAttributeList(list);
   if (list!=IntPtr.Zero) Marshal.FreeHGlobal(list);
   if (handles!=IntPtr.Zero) Marshal.FreeHGlobal(handles);
   if (read!=IntPtr.Zero) CloseHandle(read);
   if (sink!=IntPtr.Zero && sink!=new IntPtr(-1)) CloseHandle(sink);
   if (!transferred && write!=IntPtr.Zero) CloseHandle(write);
  }
 }
 public static void ContinueOwnedDebugger(IntPtr inputWrite) {
  // Deliberately no caller-supplied debugger command or target memory write.
  byte[] command=new byte[] {103,13,10}; uint written;
  if (inputWrite==IntPtr.Zero || !WriteFile(inputWrite,command,3,out written,IntPtr.Zero) || written!=3)
   throw new InvalidOperationException("Owned debugger continuation was not written exactly.");
 }
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
        # Exact quiet command-file invocation; no caller command or arguments.
        $command = Get-CanvasLaunchCommand $Plan $ProbePath $LogPath
        [IntPtr]$inputWrite=[IntPtr]::Zero
        $info=[CanvasScreenNative]::StartWithInput($Plan.cdb,$command,$desktopName,$environmentPointer,$Plan.work_dir,[ref]$inputWrite)
        # Publish retained ownership BEFORE further identity queries can fail.
        # The outer finally can then stop a debugger/game created by a partial launch.
        $Launch.session=@{ handle=$info.process; desktop=$desktop; identity=@{process_id=[int]$info.processId;path=$Plan.cdb;creation_utc=$null}
            desktop_name=$desktopName; command_line=$command; input_write=$inputWrite; input_closed=$false }
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
        # VirtualQueryEx needs PROCESS_QUERY_INFORMATION (0x400), in addition
        # to the inherited read, synchronization and exact-owned cleanup rights.
        $handle = [CanvasScreenNative]::OpenProcess(0x101411,$false,[uint32]$row.ProcessId)
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
    # PowerShell binds $null to String.Empty for ChangeExtension, leaving
    # "surface." and producing names rejected by the exact artifact auditor.
    $captures=@{};$prefix=Join-Path ([IO.Path]::GetDirectoryName($RawPath)) ([IO.Path]::GetFileNameWithoutExtension($RawPath))
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

function Initialize-PrimaryQuery {
    if ('ModalPrimaryQuery' -as [type]) {return}
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ModalPrimaryQuery {
 [StructLayout(LayoutKind.Sequential)] public struct MBI {
  public IntPtr address, allocation; public uint allocationProtect;
  public UIntPtr size; public uint state, protect, type;
 }
 [DllImport("kernel32.dll",SetLastError=true)] public static extern UIntPtr VirtualQueryEx(IntPtr process, IntPtr address, out MBI info, UIntPtr count);
}
'@
}

function Get-PrimaryReadableRegions {
    param([object[]]$Observations)
    # VirtualQueryEx can describe a suffix when queried from a later page.
    # Preserve the queried records separately; the reader needs their disjoint
    # union. Merge only identical committed/readable flags, never across a gap.
    $result=New-Object 'Collections.Generic.List[object]'
    $current=$null
    foreach ($record in @($Observations | Sort-Object {[long]$_.address},{[long]$_.size})) {
        [long]$start=$record.address;[long]$length=$record.size
        if ($start -le 0 -or $length -le 0 -or $start -ge 4294967296 -or $length -gt 4294967296-$start -or
            $record.state -ne 0x1000 -or $record.protect -notin @(2,4,8,0x20,0x40,0x80)) {throw 'Primary memory-region observation is not committed readable memory.'}
        $same=$null -ne $current -and $current.state -eq $record.state -and $current.protect -eq $record.protect
        if ($null -ne $current -and $start -lt $current.address+$current.size -and -not $same) {throw 'Primary overlapping memory-region state changed.'}
        if ($same -and $start -le $current.address+$current.size) {
            $current.size=[Math]::Max($current.address+$current.size,$start+$length)-$current.address
        } else {
            $current=@{address=$start;size=$length;state=[int]$record.state;protect=[int]$record.protect}
            $result.Add($current)
        }
    }
    return $result.ToArray()
}

function Read-PrimaryArtifact {
    param($OwnedGame,[long]$Address,[int]$Count,[string]$Path,$Regions)
    if ($Address -le 0 -or $Count -le 0 -or $Count -gt 67108864 -or $Address+$Count -gt 4294967296) {throw 'Primary read range is invalid.'}
    Initialize-PrimaryQuery
    [long]$cursor=$Address
    while ($cursor -lt $Address+$Count) {
        $info=New-Object ModalPrimaryQuery+MBI
        $size=[Runtime.InteropServices.Marshal]::SizeOf($info)
        $returned=[ModalPrimaryQuery]::VirtualQueryEx($OwnedGame.handle,[IntPtr]$cursor,[ref]$info,[UIntPtr]::new([uint64]$size))
        $start=$info.address.ToInt64();$length=$info.size.ToUInt64()
        if ($returned.ToUInt64() -ne $size -or $info.state -ne 0x1000 -or $info.protect -notin @(2,4,8,0x20,0x40,0x80) -or
            $start -gt $cursor -or $length -le 0 -or $start+$length -le $cursor -or $start+$length -gt 4294967296) {throw 'Primary read is not fully committed readable memory.'}
        $record=@{address=$start;size=$length;state=[int]$info.state;protect=[int]$info.protect}
        $key=[string]$start
        if ($Regions.ContainsKey($key) -and ($Regions[$key] | ConvertTo-Json -Compress) -cne ($record | ConvertTo-Json -Compress)) {throw 'Primary memory-region state changed.'}
        # Detect conflicting cross-base observations before performing RPM.
        # Keep same-base size/state drift rejection above, including repeats.
        [void](Get-PrimaryReadableRegions (@($Regions.Values)+@($record)))
        $Regions[$key]=$record;$cursor=[Math]::Min($Address+$Count,$start+$length)
    }
    $data=Read-CanvasMemory $OwnedGame.handle $Address $Count
    [IO.File]::WriteAllBytes($Path,$data)
    return @{path=$Path;address=$Address;bytes=$Count;sha256=(Get-CanvasHash $Path);data=$data}
}

function Initialize-PrimaryModules {
    if ('ModalPrimaryModules' -as [type]) {return}
    Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class ModalPrimaryModules {
 [StructLayout(LayoutKind.Sequential)] public struct MODULEINFO {
  public IntPtr baseAddress; public uint imageSize; public IntPtr entryPoint;
 }
 [DllImport("psapi.dll",SetLastError=true)] public static extern bool EnumProcessModulesEx(IntPtr process,[Out] IntPtr[] modules,uint bytes,out uint needed,uint filter);
 [DllImport("psapi.dll",CharSet=CharSet.Unicode,SetLastError=true)] public static extern uint GetModuleFileNameExW(IntPtr process,IntPtr module,StringBuilder path,uint capacity);
 [DllImport("psapi.dll",SetLastError=true)] public static extern bool GetModuleInformation(IntPtr process,IntPtr module,out MODULEINFO info,uint bytes);
}
'@
}

function Get-PrimaryLoadedModules {
    param([IntPtr]$Handle)
    if ($Handle -eq [IntPtr]::Zero -or $Handle -eq [IntPtr](-1)) {throw 'A retained owned process handle is required for module enumeration.'}
    Initialize-PrimaryModules
    # .NET Framework Process.Modules from a64-bit host omits WoW64 DLLs.
    # LIST_MODULES_32BIT explicitly selects our x86 target, using its retained
    # handle rather than reopening a potentially reused PID. Returned module
    # addresses are snapshot values, not kernel handles to close.
    $capacity=128; $complete=$false
    for ($attempt=0; $attempt -lt 4; $attempt++) {
        $moduleAddresses=New-Object IntPtr[] $capacity
        $needed=[uint32]0; $bufferBytes=[uint32]($capacity*[IntPtr]::Size)
        if (-not [ModalPrimaryModules]::EnumProcessModulesEx($Handle,$moduleAddresses,$bufferBytes,[ref]$needed,1)) {throw 'Read-only x86 module enumeration failed.'}
        if ($needed -eq 0 -or $needed%[IntPtr]::Size -ne 0 -or $needed -gt 4096*[IntPtr]::Size) {throw 'The x86 module list has an invalid or excessive byte count.'}
        if ($needed -le $bufferBytes) {$complete=$true;break}
        $capacity=[int]($needed/[IntPtr]::Size)
    }
    if (-not $complete) {throw 'The x86 module list changed beyond the bounded enumeration attempts.'}
    $records=@();$seen=@{}
    for ($index=0; $index -lt $needed/[IntPtr]::Size; $index++) {
        $address=$moduleAddresses[$index];$number=$address.ToInt64()
        if ($number -le 0 -or $number -ge 4294967296 -or $seen.ContainsKey([string]$number)) {throw 'The x86 module list contains an invalid or duplicate module address.'}
        $seen[[string]$number]=$true
        $path=New-Object Text.StringBuilder 32768
        $length=[ModalPrimaryModules]::GetModuleFileNameExW($Handle,$address,$path,32768)
        if ($length -eq 0 -or $length -ge 32768) {throw 'A loaded x86 module path is missing or truncated.'}
        $info=New-Object ModalPrimaryModules+MODULEINFO
        if (-not [ModalPrimaryModules]::GetModuleInformation($Handle,$address,[ref]$info,[Runtime.InteropServices.Marshal]::SizeOf($info))) {throw 'A loaded x86 module header could not be queried.'}
        if ($info.baseAddress -ne $address -or $info.imageSize -eq 0 -or $number+[long]$info.imageSize -gt 4294967296) {throw 'A loaded x86 module image range is invalid.'}
        $records += [pscustomobject]@{FileName=$path.ToString();BaseAddress=$address;ModuleMemorySize=$info.imageSize}
    }
    return $records
}

function Get-PrimaryModule {
    param($OwnedGame,$Plan)
    # The held process identity is checked again after paired live reads.
    $expectedPath=[IO.Path]::GetFullPath($Plan.proxy_path)
    $modules=@(Get-PrimaryLoadedModules $OwnedGame.handle | Where-Object {[IO.Path]::GetFullPath($_.FileName) -ieq $expectedPath})
    if ($modules.Count -ne 1 -or (Get-CanvasHash $modules[0].FileName) -cne $Plan.proxy_sha256 -or
        $Plan.proxy_sha256 -cne 'b173a9dd4ce772eb5b56f341acdf4b329ed4ffdd638c1fce5cc37dd332804b70') {throw 'Owned process does not contain the pinned local proxy module.'}
    $base=$modules[0].BaseAddress.ToInt64();$size=$modules[0].ModuleMemorySize
    if ($base -le 0 -or $size -le 0 -or $base+$size -gt 4294967296) {throw 'Proxy module address is invalid.'}
    return @{base=$base;size=$size;path=$Plan.proxy_path;sha256=$Plan.proxy_sha256}
}

function Save-PrimarySnapshot {
    param($OwnedGame,$Trace,$Plan,$Prefix)
    $began=[datetime]::UtcNow.ToString('o');$v=$Trace.capture_checkpoint.values
    if (-not $Trace.passed -or -not $Trace.primary_sequence.passed -or $Trace.source.log_raw_sha256 -cne $Prefix.sha256) {throw 'Primary read requires the exact validated paused prefix.'}
    $module=Get-PrimaryModule $OwnedGame $Plan;$base=$module.base
    $regions=@{};$reads=@{}
    foreach ($phase in @('before','after')) {
        $rows=@{}
        foreach ($row in @(@('primary',0x51d4c0,220),@('backend',$v.backend,176),@('surface_full',$v.surface,32),
            @('palette',$v.palette,1036),@('proxy_header',$base,512),@('proxy_getpalette',($base+0x2070),83))) {
            $rows[$row[0]]=Read-PrimaryArtifact $OwnedGame $row[1] $row[2] (Join-Path $Plan.out_dir ('primary-'+$phase+'-'+$row[0]+'.raw')) $regions
        }
        $surfaceTable=[BitConverter]::ToUInt32($rows.surface_full.data,0);$paletteTable=[BitConverter]::ToUInt32($rows.palette.data,0)
        if ($surfaceTable -ne $base+0x1939c -or $paletteTable -ne $base+0x19340 -or
            [BitConverter]::ToUInt32($rows.surface_full.data,28) -ne $v.palette) {throw 'Current primary surface/palette interface differs from the pinned proxy.'}
        $rows.surface=Read-PrimaryArtifact $OwnedGame $v.surface 4 (Join-Path $Plan.out_dir ('primary-'+$phase+'-surface.raw')) $regions
        $rows.surface_vtable=Read-PrimaryArtifact $OwnedGame $surfaceTable 144 (Join-Path $Plan.out_dir ('primary-'+$phase+'-surface_vtable.raw')) $regions
        $rows.palette_vtable=Read-PrimaryArtifact $OwnedGame $paletteTable 28 (Join-Path $Plan.out_dir ('primary-'+$phase+'-palette_vtable.raw')) $regions
        $reads[$phase]=$rows
        if ($phase -eq 'before') {
            $pixels=Read-PrimaryArtifact $OwnedGame $v.pixels ($Plan.width*$Plan.height) (Join-Path $Plan.out_dir 'primary.raw') $regions
            $pixels.Remove('data')
            $paletteEntries=New-Object byte[] 1024;[Array]::Copy($rows.palette.data,12,$paletteEntries,0,1024)
            $palettePath=Join-Path $Plan.out_dir 'primary-palette.bin';[IO.File]::WriteAllBytes($palettePath,$paletteEntries)
        }
    }
    foreach ($key in $reads.before.Keys) {
        if ($reads.before[$key].sha256 -cne $reads.after[$key].sha256) {throw ('Paused primary read changed: '+$key)}
        $reads.before[$key].Remove('data');$reads.after[$key].Remove('data')
    }
    $identity=Get-CanvasHandleIdentity $OwnedGame.handle $OwnedGame.identity.process_id $Plan.candidate_path
    if ($identity.creation_filetime -ne $OwnedGame.identity.creation_filetime -or (Get-CanvasHash $Plan.proxy_path) -cne $Plan.proxy_sha256) {throw 'Owned identity changed across primary capture.'}
    return @{schema='clash95_modal_primary_snapshot_receipt_v1';run_id=$Plan.run_id;
        game_identity=$OwnedGame.identity;trace_sha256=$Prefix.sha256;reads=$reads;regions=@(Get-PrimaryReadableRegions @($regions.Values));pixels=$pixels;
        region_observations=@($regions.Values | Sort-Object {[long]$_.address},{[long]$_.size});
        palette_entries=@{path=$palettePath;bytes=1024;sha256=(Get-CanvasHash $palettePath)};
        proxy_module=$module;
        started_at=$began;captured_at=[datetime]::UtcNow.ToString('o');paused=$true;manual_input_proof=$false;promotion_ready=$false}
}

function Stop-CanvasOwned {
    param($OwnedProcess)
    $inputClosed=$null
    if ($OwnedProcess.ContainsKey('input_write')) {
        $inputClosed=($OwnedProcess.input_write -eq [IntPtr]::Zero -or $OwnedProcess.input_closed)
        if (-not $inputClosed) {
            $inputClosed=[CanvasScreenNative]::CloseHandle($OwnedProcess.input_write)
            $OwnedProcess.input_closed=$inputClosed
            if ($inputClosed) {$OwnedProcess.input_write=[IntPtr]::Zero}
        }
    }
    $before = [CanvasScreenNative]::WaitForSingleObject($OwnedProcess.handle,0)
    $terminated = $false
    if ($before -ne 0) { $terminated = [CanvasScreenNative]::TerminateProcess($OwnedProcess.handle,1) }
    $absent = [CanvasScreenNative]::WaitForSingleObject($OwnedProcess.handle,5000) -eq 0
    $closed = [CanvasScreenNative]::CloseHandle($OwnedProcess.handle)
    return @{ identity=$OwnedProcess.identity; absent=$absent; termination_requested=$terminated; handle_closed=$closed; input_closed=$inputClosed }
}

function Resume-PrimaryCheckpoint {
    param($Session,$Checkpoint,[string]$LogPath,$Plan)
    if ($Checkpoint.name -notin @('full-published','placeholder-before','placeholder-after') -or
        $Checkpoint.index -isnot [int] -or $Checkpoint.index -lt 0 -or $Checkpoint.index -gt 2 -or
        $Checkpoint.name -cne @('full-published','placeholder-before','placeholder-after')[$Checkpoint.index] -or
        $Checkpoint.resumed -or $Checkpoint.snapshots.Count -ne 1 -or
        $Session.input_closed -or $Session.input_write -eq [IntPtr]::Zero -or
        (Test-CanvasProcessExited $Session)) {throw 'Only the next captured checkpoint may resume the owned debugger.'}
    if ((Get-CanvasBytesHash (Read-CanvasLogBytes $LogPath)) -cne $Checkpoint.prefix.sha256 -or
        (Get-CanvasHash $Checkpoint.prefix.path) -cne $Checkpoint.prefix.sha256 -or
        (Get-CanvasHash $Plan.host_path) -cne $Plan.host_sha256) {throw 'Captured checkpoint or host changed before continuation.'}
    [CanvasScreenNative]::ContinueOwnedDebugger($Session.input_write)
    $Checkpoint.resumed=$true
    return @{checkpoint=$Checkpoint.name;index=$Checkpoint.index;command='g';written=$true;bytes=3;
        command_sha256=(Get-CanvasBytesHash ([byte[]]@(103,13,10)));prefix_sha256=$Checkpoint.prefix.sha256;
        debugger_identity=$Session.identity;sent_at=[datetime]::UtcNow.ToString('o');input_method='private_debugger_stdin'}
}

function Save-CanvasTriplet {
    param($OwnedGame, $Evidence, $Plan, $Trace, $Prefix, [ValidateRange(1,3)][int]$Count=3)
    $snapshots=@()
    foreach ($captureIndex in 1..$Count) {
        $directory=Join-Path $Plan.out_dir ('capture-'+$captureIndex)
        [void](New-Item -ItemType Directory -Path $directory)
        $capturePlan=@{};foreach ($key in $Plan.Keys) {$capturePlan[$key]=$Plan[$key]}
        $capturePlan.out_dir=$directory;$capturePlan.run_id=$Plan.run_id
        $cursorRegions=@{}
        $cursorBefore=Read-PrimaryCursorState $OwnedGame $capturePlan 'before' $cursorRegions
        $snapshot=Save-CanvasSnapshot $OwnedGame $Evidence (Join-Path $directory 'surface.raw') $Plan
        $snapshot.primary=Save-PrimarySnapshot $OwnedGame $Trace $capturePlan $Prefix
        $cursorAfter=Read-PrimaryCursorState $OwnedGame $capturePlan 'after' $cursorRegions
        foreach ($name in $cursorBefore.Keys) {
            if ($cursorBefore[$name].sha256 -cne $cursorAfter[$name].sha256 -or
                $cursorBefore[$name].address -ne $cursorAfter[$name].address) {throw ('Cursor context changed across paused pixel reads: '+$name)}
        }
        $snapshot.cursor=@{reads=@{before=$cursorBefore;after=$cursorAfter};regions=@(Get-PrimaryReadableRegions @($cursorRegions.Values));
            region_observations=@($cursorRegions.Values | Sort-Object {[long]$_.address},{[long]$_.size})}
        $snapshots+=$snapshot
    }
    $same=$true
    foreach ($snapshot in $snapshots) {
        if ($snapshot.sha256 -cne $snapshots[0].sha256 -or $snapshot.native.sha256 -cne $snapshots[0].native.sha256 -or
            $snapshot.primary.pixels.sha256 -cne $snapshots[0].primary.pixels.sha256 -or
            $snapshot.primary.palette_entries.sha256 -cne $snapshots[0].primary.palette_entries.sha256) {$same=$false}
        foreach ($name in @('state','e0','physical_header','native_header')) {
            if ($snapshot.reads.before[$name].sha256 -cne $snapshots[0].reads.before[$name].sha256) {$same=$false}
        }
        foreach ($name in $snapshot.primary.reads.before.Keys) {
            if ($snapshot.primary.reads.before[$name].sha256 -cne $snapshots[0].primary.reads.before[$name].sha256) {$same=$false}
        }
    }
    return @{snapshots=$snapshots;snapshot_count=$snapshots.Count;paired_identity_reads_valid=$same;
        clean_stable_pair=($snapshots.Count -ge 2 -and $same)}
}

function Read-PrimaryCursorState {
    param($OwnedGame,$Plan,[ValidateSet('before','after')][string]$Phase,[hashtable]$Regions)
    $rows=@{}
    function Read-Auxiliary {
        param([string]$Name,[long]$Address,[int]$Count)
        if ($Address -lt 65536 -or $Count -le 0 -or $Address+$Count -gt 0x7ffe0000) {throw 'Cursor artifact exceeds the supported native user address range.'}
        $rows[$Name]=Read-PrimaryArtifact $OwnedGame $Address $Count (Join-Path $Plan.out_dir ('cursor-'+$Phase+'-'+$Name+'.raw')) $Regions
        return ,$rows[$Name].data
    }
    $state=Read-Auxiliary 'state' 0x544cd8 68
    $descriptorAddress=[BitConverter]::ToUInt32($state,60)
    if ($descriptorAddress -ne 0x545158 -and
        ($descriptorAddress -lt 0x519678 -or $descriptorAddress -gt 0x519920 -or (($descriptorAddress-0x519678)%40))) {
        throw 'Cursor descriptor is outside the authenticated native inventory.'
    }
    if ([BitConverter]::ToUInt32($state,56) -gt 1) {throw 'Cursor visibility state is unsupported.'}
    $descriptor=Read-Auxiliary 'descriptor' $descriptorAddress 40
    $resource=Read-Auxiliary 'resource' ([BitConverter]::ToUInt32($state,64)) 0x1010
    $first=[BitConverter]::ToUInt32($descriptor,0);$last=[BitConverter]::ToUInt32($descriptor,4)
    # The native DLX sprite count is WORD-sized (MOVZX ... WORD+1004).
    # Adjacent WORDs hold other metadata and are not part of this count.
    $frame=[BitConverter]::ToUInt32($descriptor,32);$count=[BitConverter]::ToUInt16($resource,0x1004)
    if ($count -lt 1 -or $count -gt 1024 -or $last -lt $first -or $frame -gt $last-$first -or $first+$frame -ge $count) {throw 'Cursor resource index is not bounded by its native descriptor and loaded inventory.'}
    $sprite=Read-Auxiliary 'sprite_header' ([BitConverter]::ToUInt32($resource,[int](4*($first+$frame)))) 10
    $backing=Read-Auxiliary 'backing_header' ([BitConverter]::ToUInt32($state,8)) 188
    if ([BitConverter]::ToUInt16($backing,0) -ne 64 -or [BitConverter]::ToUInt16($backing,2) -ne 64 -or
        [BitConverter]::ToUInt32($backing,184) -ne 0x50ee24) {throw 'Cursor backing is not the native 64x64 memory surface.'}
    $pixels=Read-Auxiliary 'backing_pixels' ([BitConverter]::ToUInt32($backing,4)) 4096
    $barracksPointer=Read-PrimaryArtifact $OwnedGame 0x532144 4 (Join-Path $Plan.out_dir ('cursor-'+$Phase+'-barracks-pointer.raw')) $Regions
    $barracks=Read-Auxiliary 'barracks_resource' ([BitConverter]::ToUInt32($barracksPointer.data,0)) 0x1010
    $barracksCount=[BitConverter]::ToUInt16($barracks,0x1004)
    if ($barracksCount -le 25 -or $barracksCount -gt 1024) {throw 'Barracks placeholder index is outside the loaded resource.'}
    $placeholder=Read-Auxiliary 'placeholder_sprite_header' ([BitConverter]::ToUInt32($barracks,100)) 10
    # Retain the pointer read as well as its target; both are actual observations.
    $barracksPointer.Remove('data');$rows.barracks_pointer=$barracksPointer
    foreach ($name in @($rows.Keys)) {$rows[$name].Remove('data')}
    return $rows
}

function Get-PrimaryPaletteVisualizationMode {
    param($Palette)
    $bytes=[IO.File]::ReadAllBytes($Palette.path)
    if ($Palette.bytes -ne 1024 -or $bytes.Length -ne 1024 -or
        (Get-CanvasHash $Palette.path) -cne $Palette.sha256) {throw 'Captured attached palette changed before visualization.'}
    for ($index=0;$index -lt 1024;$index+=4) {
        if ($bytes[$index] -ne 0 -or $bytes[$index+1] -ne 0 -or $bytes[$index+2] -ne 0) {return 'directdraw-palette'}
    }
    # The native fade can leave the actual attached RGB palette empty at an
    # early draw boundary. The unchanged converter then shows indices in gray;
    # retain that explicit visualization mode, never claim captured colors.
    return 'grayscale-index-empty-palette'
}

function Convert-PrimaryCheckpointScreens {
    param($Plan,$Checkpoints)
    if ((Get-CanvasHash $Plan.converter) -cne $Plan.converter_sha256) {throw 'The planned indexed-pixel converter changed.'}
    foreach ($checkpoint in $Checkpoints) {
        foreach ($sample in $checkpoint.snapshots) {
            $palette=$sample.primary.palette_entries
            $paletteMode=Get-PrimaryPaletteVisualizationMode $palette
            foreach ($kind in @('primary','physical','native')) {
                if ($kind -ceq 'primary') {$raw=$sample.primary.pixels;$frameWidth=$Plan.width;$frameHeight=$Plan.height}
                elseif ($kind -ceq 'physical') {$raw=$sample;$frameWidth=$Plan.width;$frameHeight=$Plan.height}
                else {$raw=$sample.native;$frameWidth=640;$frameHeight=480}
                if ((Get-CanvasHash $raw.path) -cne $raw.sha256) {throw 'Captured indexed pixels changed before visualization.'}
                $directory=Split-Path -Parent $sample.path
                $png=Join-Path $directory ($kind+'.png');$metadataPath=Join-Path $directory ($kind+'-png.json')
                $output=& $Plan.python -B $Plan.converter $raw.path --width $frameWidth --height $frameHeight --pitch $frameWidth `
                    --output $png --metadata $metadataPath --log $checkpoint.prefix.path --palette $palette.path
                if ($LASTEXITCODE -ne 0) {throw 'Checkpoint PNG conversion failed; actual raw captures remain retained.'}
                $metadata=[IO.File]::ReadAllText($metadataPath) | ConvertFrom-Json
                if ($metadata.raw_sha256 -cne $raw.sha256 -or $metadata.png_sha256 -cne (Get-CanvasHash $png) -or
                    $metadata.palette_mode -cne $paletteMode -or $metadata.palette_path -cne $palette.path) {throw 'Checkpoint PNG does not bind its captured indices and attached palette.'}
                $sample[($kind+'_png')]=@{path=$png;sha256=(Get-CanvasHash $png);metadata_path=$metadataPath;
                    metadata_sha256=(Get-CanvasHash $metadataPath);raw_sha256=$raw.sha256;palette_sha256=$palette.sha256;
                    width=$frameWidth;height=$frameHeight;checkpoint=$checkpoint.name;capture_method='hidden_cached_primary_and_owned_surfaces';
                    palette_mode=$paletteMode;palette_colors_available=($paletteMode -ceq 'directdraw-palette');
                    color_scope=$(if($paletteMode -ceq 'directdraw-palette'){'matched_current_attached_proxy_palette'}else{'grayscale_index_preview_empty_attached_palette'})}
            }
        }
    }
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

function Save-CanvasCaptureSummary {
    param($Plan,$Summary)
    try {
        Write-CanvasJson (Join-Path $Plan.out_dir 'summary.json') $Summary
    } catch {
        # A storage failure after execution must preserve the measured run and
        # cleanup on stdout, never escape into the preparation-only catch.
        $Summary.passed=$false
        $Summary.status='failed'
        $Summary.failures += ('Final summary could not be saved: '+$_.Exception.Message)
    }
}

function Invoke-CanvasCapture {
    param($Bundle, [switch]$DoExecute)
    $plan=$Bundle.plan; $prepared=$Bundle.prepared
    if (-not $DoExecute) { return @{ status='dry_run'; executed=$false; plan=$plan; prepared=$prepared } }
    $summary = [ordered]@{ schema='clash95_modal_primary_capture_v1'; passed=$false; status='failed'; executed=$false; plan=$plan
        started_at=[datetime]::UtcNow.ToString('o'); finished_at=$null; failures=@(); trace=$null; snapshot=$null; png=$null
        cdb=$null; candidates=@(); checkpoints=@(); cleanup=@{ cdb=$null; candidates=@(); desktop_closed=$false }
        manual_input_proof=$false; visible_composition_proof=$false; promotion_ready=$false }
    $session=$null; $owned=@{}; $outputCreated=$false; $launch=@{session=$null}
    $logPath=Join-Path $plan.out_dir 'cdb.log'; $probePath=Join-Path $plan.out_dir 'modal-primary-barracks.cdb'
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
            @($plan.python,$plan.python_sha256),@($plan.cdb,$plan.cdb_sha256),@($plan.primary_source,$plan.primary_source_sha256))) {
            if ((Get-CanvasHash $pair[0]) -cne $pair[1]) { throw 'A planned source, runtime or input file changed before execution.' }
        }
        [IO.File]::Copy($plan.input_candidate,$plan.candidate_path,$false)
        [IO.File]::Copy($plan.proxy_input,$plan.proxy_path,$false)
        if ((Get-CanvasHash $plan.candidate_path) -cne $plan.candidate_sha256 -or (Get-CanvasHash $plan.proxy_path) -cne $plan.proxy_sha256) { throw 'Fresh candidate/proxy copy identity mismatch.' }
        Write-CanvasJson $packetPath $prepared.packet
        [IO.File]::WriteAllText($probePath,$prepared.probe,[Text.UTF8Encoding]::new($false))
        if ((Get-CanvasHash $probePath) -cne $plan.probe_sha256) { throw 'Compiled probe file differs from the prepared packet.' }
        foreach ($name in $plan.primary_ready_scripts.Keys) {
            $row=$plan.primary_ready_scripts[$name]
            [IO.File]::WriteAllText($row.path,$prepared.ready_scripts.$name.text,[Text.UTF8Encoding]::new($false))
            if ((Get-CanvasHash $row.path) -cne $row.sha256) {throw 'Primary checkpoint script differs from exact prepared recipe.'}
        }
        Write-CanvasJson (Join-Path $plan.out_dir 'plan.json') $plan
        $summary.packet=@{path=$packetPath;sha256=(Get-CanvasHash $packetPath)}
        $summary.probe=@{path=$probePath;sha256=(Get-CanvasHash $probePath)}
        # Reconstruct against the COPIED file before launch, not merely its input path.
        $verifyArgs=@($plan.trace,'--prepare','--original',$plan.original,'--candidate',$plan.candidate_path,
            '--candidate-manifest',$plan.candidate_manifest,'--candidate-sha256',$plan.candidate_sha256,'--stage',$plan.stage,'--resolution',$plan.resolution,
            '--route',$plan.route,'--availability',$plan.availability,'--castle-index',[string]$plan.castle_index,
            '--out-dir',$plan.out_dir,'--proxy-manifest',$plan.proxy_manifest)
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
        while ($watch.Elapsed.TotalSeconds -lt $plan.deadline_seconds) {
            Find-CanvasOwnedChildren $plan $session $launchStart $owned
            $text=Read-CanvasLog $logPath
            $commandFailure=Get-CanvasDebuggerCommandFailure $text
            if ($null -ne $commandFailure) {
                $prefix=Read-CanvasLogBytes $logPath
                $failurePath=Join-Path $plan.out_dir 'debugger-command-failure-prefix.log'
                [IO.File]::WriteAllBytes($failurePath,$prefix)
                $commandFailure.log_prefix=@{path=$failurePath;bytes=$prefix.Length;sha256=(Get-CanvasHash $failurePath)}
                $summary.debugger_command_failure=$commandFailure
                throw ('Debugger command failed before capture: '+$commandFailure.text)
            }
            $checkpointName=Get-PrimaryCheckpointReady $text $summary.checkpoints.Count
            if ($null -ne $checkpointName) {
                $checkpointTrace=Invoke-CanvasPythonJson $plan.python @($plan.trace,'--log',$logPath,'--packet',$packetPath,
                    '--original',$plan.original,'--candidate',$plan.candidate_path,'--probe',$probePath,'--checkpoint',$checkpointName) -PermitFailure -TimeoutMilliseconds ([Math]::Max(1,[Math]::Min(120000,($plan.deadline_seconds*1000)-[int]$watch.ElapsedMilliseconds)))
                $checkpointDirectory=Join-Path (Join-Path $plan.out_dir 'checkpoints') $checkpointName
                [void](New-Item -ItemType Directory -Path $checkpointDirectory)
                $checkpointTracePath=Join-Path $checkpointDirectory 'trace.json'
                Write-CanvasJson $checkpointTracePath $checkpointTrace
                $surface=Assert-CanvasSurface $checkpointTrace $plan
                if ($checkpointTrace.capture_checkpoint.name -cne $checkpointName -or
                    $checkpointTrace.capture_checkpoint.index -ne $summary.checkpoints.Count) {throw 'Validated checkpoint differs from the next observed pause.'}
                if ($owned.Count -ne 1) { throw 'Modal readiness lacks exactly one measured, owned candidate.' }
                if ($watch.Elapsed.TotalSeconds -ge $plan.deadline_seconds) { throw 'Modal validation exceeded the capture deadline; no memory read is authorized.' }
                $prefix=Read-CanvasLogBytes $logPath
                if ((Get-CanvasBytesHash $prefix) -cne $checkpointTrace.source.log_raw_sha256) {throw 'Validated raw log changed before capture.'}
                $prefixPath=Join-Path $checkpointDirectory 'capture-prefix.log';[IO.File]::WriteAllBytes($prefixPath,$prefix)
                $prefixRecord=@{path=$prefixPath;bytes=$prefix.Length;sha256=(Get-CanvasHash $prefixPath)}
                $checkpointPlan=@{};foreach ($key in $plan.Keys) {$checkpointPlan[$key]=$plan[$key]}
                $checkpointPlan.out_dir=$checkpointDirectory
                $captureCount=$(if ($checkpointName -ceq 'final-ready') {3} else {1})
                $triplet=Save-CanvasTriplet @($owned.Values)[0] $surface $checkpointPlan $checkpointTrace $prefixRecord -Count $captureCount
                $checkpointRecord=@{name=$checkpointName;index=$summary.checkpoints.Count;prefix=$prefixRecord;
                    trace=@{path=$checkpointTracePath;sha256=(Get-CanvasHash $checkpointTracePath);bytes=(Get-Item -LiteralPath $checkpointTracePath).Length};
                    snapshots=$triplet.snapshots;paired_identity_reads_valid=$triplet.paired_identity_reads_valid;
                    clean_stable_pair=$triplet.clean_stable_pair;resume=$null;resumed=$false}
                $summary.checkpoints+=,$checkpointRecord
                if (-not $triplet.paired_identity_reads_valid -or ($captureCount -ge 2 -and -not $triplet.clean_stable_pair)) {throw 'Paused native/physical/primary captures differ; raw captures are preserved.'}
                if ((Get-CanvasBytesHash (Read-CanvasLogBytes $logPath)) -cne $prefixRecord.sha256) {throw 'Debugger log changed across the paused raw capture.'}
                if ($watch.Elapsed.TotalSeconds -ge $plan.deadline_seconds) {throw 'Paired capture exceeded the deadline.'}
                if ($checkpointName -ceq 'final-ready') {
                    $summary.trace=$checkpointTrace;$summary.capture_prefix=$prefixRecord
                    $summary.snapshots=$triplet.snapshots;$summary.snapshot=$summary.snapshots[0]
                    $rawPath=$summary.snapshot.path;$summary.clean_stable_pair=$triplet.clean_stable_pair
                    break
                }
                $checkpointRecord.resume=Resume-PrimaryCheckpoint $session $checkpointRecord $logPath $plan
                Write-CanvasJson (Join-Path $checkpointDirectory 'checkpoint.json') $checkpointRecord
            }
            if (Test-CanvasProcessExited $session) { throw 'Debugger exited before accepted modal readiness.' }
            Start-Sleep -Milliseconds 100
        }
        if (-not $summary.snapshot) { throw 'The bounded primary capture deadline expired without the final triplet.' }
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
            if (-not $summary.cleanup.cdb.absent -or -not $summary.cleanup.cdb.handle_closed -or -not $summary.cleanup.cdb.input_closed -or
                $summary.cleanup.candidates.Count -ne 1 -or @($summary.cleanup.candidates | Where-Object { -not $_.absent -or -not $_.handle_closed }).Count -or
                -not $summary.cleanup.desktop_closed) { $summary.failures += 'Exact owned-process absence/handle cleanup was not fully verified.' }
        }
        if ($summary.snapshot) {
            try {
                # Preserve the earlier prefix and revalidate every later actual
                # record, including the debugger termination tail.
                $summary.final_trace=Invoke-CanvasPythonJson $plan.python @($plan.trace,'--log',$logPath,'--packet',$packetPath,
                    '--original',$plan.original,'--candidate',$plan.candidate_path,'--probe',$probePath,'--checkpoint','final-ready') -PermitFailure
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
                foreach ($row in $plan.primary_ready_scripts.Values) {
                    if ((Get-CanvasHash $row.path) -cne $row.sha256) {throw 'Primary checkpoint script changed after capture.'}
                }
            } catch {$summary.failures+=$_.Exception.Message}
        } elseif ($session -and (Test-Path -LiteralPath $logPath -PathType Leaf)) {
            # Keep an authoritative terminal trace even when no pause passed
            # validation. A failed early run must not disappear from evidence.
            try {
                $requested=$(if ($summary.checkpoints.Count) {$summary.checkpoints[-1].name} else {'full-published'})
                $summary.final_trace=Invoke-CanvasPythonJson $plan.python @($plan.trace,'--log',$logPath,'--packet',$packetPath,
                    '--original',$plan.original,'--candidate',$plan.candidate_path,'--probe',$probePath,'--checkpoint',$requested) -PermitFailure
                Write-CanvasJson (Join-Path $plan.out_dir 'trace-final.json') $summary.final_trace
                $finalBytes=Read-CanvasLogBytes $logPath
                $summary.final_log=@{path=$logPath;sha256=(Get-CanvasBytesHash $finalBytes);bytes=$finalBytes.Length;capture_prefix_preserved=$false}
            } catch {$summary.failures+=$_.Exception.Message}
        }
        if ($summary.checkpoints.Count) {
            try {Convert-PrimaryCheckpointScreens $plan $summary.checkpoints}
            catch {$summary.failures+=$_.Exception.Message}
        }
        # Preserve and convert captured physical raw even when final trace or cleanup failed.
        if ($summary.snapshot) {
            try {
                # The physical mirror contains indices destined for this same
                # paused primary. Visualize them with its captured attached
                # palette, not the proxy's independently written global file.
                $matchedPalette=$summary.snapshots[0].primary.palette_entries
                if ($matchedPalette.bytes -ne 1024 -or
                    -not (Test-Path -LiteralPath $matchedPalette.path -PathType Leaf) -or
                    (Get-Item -LiteralPath $matchedPalette.path).Length -ne 1024 -or
                    (Get-CanvasHash $matchedPalette.path) -cne $matchedPalette.sha256) {
                    throw 'Matching captured primary palette is missing, changed or has the wrong size.'
                }
                $summary.palette=@{path=$matchedPalette.path;sha256=$matchedPalette.sha256;bytes=1024;
                    binding='matching_paused_primary_attached_palette';sample_index=1;
                    primary_pixels_sha256=$summary.snapshots[0].primary.pixels.sha256}
                $pngPath=Join-Path $plan.out_dir 'surface.png'; $metaPath=Join-Path $plan.out_dir 'surface.png.json'
                $convertOutput = & $plan.python -B $plan.converter $rawPath --width $plan.width --height $plan.height --pitch $plan.width --output $pngPath --metadata $metaPath --log $summary.capture_prefix.path --palette $matchedPalette.path
                if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $metaPath)) { throw 'Raw-to-PNG conversion failed; raw capture is preserved.' }
                $summary.png=[IO.File]::ReadAllText($metaPath) | ConvertFrom-Json
                if ($summary.png.palette_mode -cne (Get-PrimaryPaletteVisualizationMode $matchedPalette) -or $summary.png.palette_path -cne $matchedPalette.path -or
                    $summary.png.raw_sha256 -cne $summary.snapshot.sha256 -or
                    $summary.png.png_sha256 -cne (Get-CanvasHash $pngPath)) { throw 'PNG conversion metadata does not bind the fresh palette and raw capture.' }
            } catch { $summary.failures += $_.Exception.Message }
        }
        if ($summary.snapshot) {
            try {
                $primaryReceipt=[ordered]@{schema='clash95_modal_primary_triplet_v1';plan=$plan;snapshots=$summary.snapshots;checkpoints=$summary.checkpoints;
                    clean_stable_pair=$summary.clean_stable_pair;cdb=$summary.cdb;candidates=$summary.candidates;cleanup=$summary.cleanup;
                    packet=$summary.packet;probe=$summary.probe;capture_prefix=$summary.capture_prefix;final_log=$summary.final_log;
                    failures=$summary.failures;manual_input_proof=$false;promotion_ready=$false}
                $primaryReceiptPath=Join-Path $plan.out_dir 'primary-triplet.json';Write-CanvasJson $primaryReceiptPath $primaryReceipt
                $summary.primary_triplet=@{path=$primaryReceiptPath;sha256=(Get-CanvasHash $primaryReceiptPath)}
                if ($summary.cleanup.cdb.absent -and $summary.cleanup.cdb.handle_closed -and
                    $summary.cleanup.candidates.Count -eq 1 -and $summary.cleanup.candidates[0].absent -and
                    $summary.cleanup.candidates[0].handle_closed -and $summary.cleanup.desktop_closed) {
                    $summary.primary_audit=Invoke-CanvasPythonJson $plan.python @($plan.trace,'--log',$summary.capture_prefix.path,'--packet',$packetPath,
                        '--probe',$probePath,'--original',$plan.original,'--candidate',$plan.candidate_path,'--checkpoint','final-ready',
                        '--snapshot-manifest',$primaryReceiptPath,'--proxy',$plan.proxy_path) -PermitFailure
                    Write-CanvasJson (Join-Path $plan.out_dir 'primary-audit.json') $summary.primary_audit
                    if ($summary.primary_audit.passed -isnot [bool] -or -not $summary.primary_audit.passed -or
                        $summary.primary_audit.primary_snapshot.three_matched_captures -isnot [bool] -or
                        -not $summary.primary_audit.primary_snapshot.three_matched_captures -or
                        -not $summary.primary_audit.primary_snapshot.cached_primary_snapshot_valid) {
                        $summary.failures+='Three matched primary/native/physical snapshots failed source-bound validation.'
                    }
                }
                $summary.primary_pngs=@($summary.snapshots | ForEach-Object {$_.primary_png})
            } catch {$summary.failures+=$_.Exception.Message}
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
        $summary.passed=($summary.executed -and $summary.failures.Count -eq 0 -and $null -ne $summary.snapshot -and $null -ne $summary.png -and
            $summary.clean_stable_pair -and $summary.primary_audit.passed -and $summary.primary_audit.primary_snapshot.cached_primary_snapshot_valid -and
            $summary.primary_audit.primary_snapshot.three_matched_captures -and $summary.primary_pngs.Count -eq 3)
        if ($summary.passed) { $summary.status='bounded_hidden_modal_primary_capture' }
        if ($outputCreated) { Save-CanvasCaptureSummary $plan $summary }
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
    $failure=@{ schema='clash95_modal_primary_capture_v1'; passed=$false; status='preparation_failed'; executed=$false
        failures=@($_.Exception.Message); manual_input_proof=$false; promotion_ready=$false }
    if ($null -ne $_.Exception.Data['CanvasPythonFailure']) {
        $failure.child_failure=$_.Exception.Data['CanvasPythonFailure']
    }
    $failure | ConvertTo-Json -Depth 10
    exit 1
}
