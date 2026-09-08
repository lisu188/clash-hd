param(
    [string]$InputExe = 'C:\Clash\clash95.exe',
    [string]$WorkDir = 'C:\Clash',
    [string]$Cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe',
    [string]$Python = 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [string]$Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch',
    [string]$Resolution = '800x600',
    [switch]$PartialTileValidation,
    [switch]$InitialMapPaintValidation,
    [switch]$FramedValidation,
    [switch]$MinimapViewportValidation,
    [switch]$CompleteHdValidation,
    [switch]$NoopProgressDiagnostic,
    [switch]$FullPaintProgressDiagnostic,
    [string]$CandidateName = '',
    [string]$CandidateDir = '',
    [switch]$UseDdrawProxy,
    [string]$DdrawProxyDll = '',
    [string]$DdrawProxyBuildScript = (Join-Path (Join-Path $PSScriptRoot '..\..') 'scripts\build\build_ddraw_surfdump_proxy.ps1'),
    [string]$OutRoot = (Join-Path (Join-Path $PSScriptRoot '..\..') 'captures\archive'),
    [string]$ProbeTemplate = (Join-Path (Join-Path $PSScriptRoot '..\..') 'probes\cdb\render\clash95_surface_dump_probe.cdb'),
    [string]$ExtraProbeTemplate = '',
    [int]$RunSeconds = 90,
    [ValidateRange(0,600)]
    [int]$ContinueAfterDumpSec = 0,
    [switch]$NoSkipStartAnims,
    [switch]$FastForwardStartAnims,
    [switch]$ForceVisibleEdges,
    [switch]$PostOwnerForceVisibleSeven,
    [switch]$UseCdbWriteMem,
    [switch]$AllowVisibleDesktop,
    [switch]$SkipMapValidation,
    [switch]$RequireGameplay,
    [switch]$LateLoadSlotForcingOnly,
    [ValidateRange(0,9)]
    [int]$LoadSlot = 0
)

$ErrorActionPreference = 'Stop'
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

$completeStage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-validation'
$framedRecipeStage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation'
if ($CompleteHdValidation) {
    if ($Stage -cne $completeStage) { throw 'CompleteHdValidation requires the exact completehd-validation stage.' }
    $PartialTileValidation = $true
    $InitialMapPaintValidation = $true
    $FramedValidation = $true
    $MinimapViewportValidation = $true
} elseif ($Stage -ceq $completeStage) {
    throw 'The complete HD stage requires -CompleteHdValidation; legacy probe geometry is forbidden.'
}
if ($NoopProgressDiagnostic -and -not $CompleteHdValidation) {
    throw 'NoopProgressDiagnostic requires the bound complete HD hidden lane.'
}
if ($FullPaintProgressDiagnostic -and -not $CompleteHdValidation) {
    throw 'FullPaintProgressDiagnostic requires the bound complete HD hidden lane.'
}
$recipeStage = $Stage
$partialTileBuilder = Join-Path $RepoRoot 'tools\build_partial_tile_candidate.py'
if ($MinimapViewportValidation -and -not $FramedValidation) {
    throw 'MinimapViewportValidation requires the exact framed validation lane.'
}
if ($FramedValidation -and (-not $PartialTileValidation -or -not $InitialMapPaintValidation)) {
    throw 'FramedValidation requires PartialTileValidation and InitialMapPaintValidation.'
}
if ($InitialMapPaintValidation -and -not $PartialTileValidation) {
    throw 'InitialMapPaintValidation requires PartialTileValidation.'
}
if ($PartialTileValidation) {
    $partialBase = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-validation'
    $partialStage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-validation'
    $partialBuilderOptions = @()
    if ($InitialMapPaintValidation) {
        $partialStage = $partialStage.Replace('-partialtiles-validation', '-partialtiles-initialpaint-validation')
        $partialBuilderOptions = @('--initial-map-paint')
        if ($ContinueAfterDumpSec -ne 0) {
            throw 'Initial paint capture pauses at a complete update boundary; ContinueAfterDumpSec must be zero.'
        }
    }
    if ($FramedValidation) {
        $partialStage = $partialStage.Replace('-initialpaint-validation', '-initialpaint-framed-validation')
        $partialTileBuilder = Join-Path $RepoRoot 'tools\build_framed_candidate.py'
        $partialBuilderOptions = @()
        if ($MinimapViewportValidation) { $partialBuilderOptions = @('--minimap-viewport') }
    }
    if ($CompleteHdValidation) {
        $partialStage = $completeStage
        $partialTileBuilder = Join-Path $RepoRoot 'patch_clash95_hd.py'
        $partialBuilderOptions = @()
    }
    if ($Stage -ne $partialStage -or -not $UseDdrawProxy -or $AllowVisibleDesktop -or
        $ExtraProbeTemplate -or $ForceVisibleEdges -or $PostOwnerForceVisibleSeven -or
        $SkipMapValidation -or $UseCdbWriteMem -or $LoadSlot -ne 0 -or
        [System.IO.Path]::GetFullPath($ProbeTemplate) -ne (Join-Path $RepoRoot 'probes\cdb\render\clash95_surface_dump_probe.cdb')) {
        throw 'PartialTileValidation requires its distinct stage, hidden proxy, canonical map probe, LoadSlot 0 and no custom/forced/skipped evidence paths.'
    }
    $recipeStage = $partialBase
    if ($FramedValidation) { $recipeStage = $framedRecipeStage }
    $RequireGameplay = $true
    if (-not (Test-Path -LiteralPath $partialTileBuilder -PathType Leaf)) {
        throw 'Partial-tile builder is missing.'
    }
    if (-not $CandidateDir -or
        -not [System.IO.Path]::GetFullPath($CandidateDir).StartsWith('C:\ClashTests\', [StringComparison]::OrdinalIgnoreCase) -or
        -not [System.IO.Path]::GetFullPath($WorkDir).StartsWith('C:\ClashTests\', [StringComparison]::OrdinalIgnoreCase) -or
        -not [System.IO.Path]::GetFullPath($OutRoot).StartsWith('C:\ClashCaptures\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Partial-tile candidates/workdirs require isolated C:\ClashTests folders and outputs under C:\ClashCaptures.'
    }
}

if ($PostOwnerForceVisibleSeven -and $SkipMapValidation) {
    throw '-PostOwnerForceVisibleSeven requires map validation; do not use -SkipMapValidation.'
}
if ($ContinueAfterDumpSec -gt 0 -and $UseCdbWriteMem) {
    throw '-ContinueAfterDumpSec requires host ReadProcessMemory dumping; do not combine it with -UseCdbWriteMem.'
}

if (-not ([System.Management.Automation.PSTypeName]'ClashSurfaceDumpNative').Type) {
    Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class ClashSurfaceDumpNative {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct STARTUPINFO {
        public UInt32 cb;
        public string lpReserved;
        public string lpDesktop;
        public string lpTitle;
        public UInt32 dwX;
        public UInt32 dwY;
        public UInt32 dwXSize;
        public UInt32 dwYSize;
        public UInt32 dwXCountChars;
        public UInt32 dwYCountChars;
        public UInt32 dwFillAttribute;
        public UInt32 dwFlags;
        public UInt16 wShowWindow;
        public UInt16 cbReserved2;
        public IntPtr lpReserved2;
        public IntPtr hStdInput;
        public IntPtr hStdOutput;
        public IntPtr hStdError;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_INFORMATION {
        public IntPtr hProcess;
        public IntPtr hThread;
        public UInt32 dwProcessId;
        public UInt32 dwThreadId;
    }

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern IntPtr CreateDesktop(string lpszDesktop, IntPtr lpszDevice, IntPtr pDevmode, UInt32 dwFlags, UInt32 dwDesiredAccess, IntPtr lpsa);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool CloseDesktop(IntPtr hDesktop);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool CreateProcess(
        string lpApplicationName,
        StringBuilder lpCommandLine,
        IntPtr lpProcessAttributes,
        IntPtr lpThreadAttributes,
        bool bInheritHandles,
        UInt32 dwCreationFlags,
        IntPtr lpEnvironment,
        string lpCurrentDirectory,
        ref STARTUPINFO lpStartupInfo,
        out PROCESS_INFORMATION lpProcessInformation);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool CloseHandle(IntPtr hObject);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern IntPtr OpenProcess(UInt32 dwDesiredAccess, bool bInheritHandle, UInt32 dwProcessId);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool ReadProcessMemory(IntPtr hProcess, IntPtr lpBaseAddress, byte[] lpBuffer, UInt32 nSize, out UIntPtr lpNumberOfBytesRead);
}
'@
}

function Quote-CommandLineArgument {
    param([string]$Value)
    if ($Value -notmatch '[\s"]') {
        return $Value
    }
    '"' + ($Value -replace '"', '\"') + '"'
}

function Get-FullPath {
    param([string]$Path)
    [System.IO.Path]::GetFullPath($Path)
}

function Get-CdbFileToken {
    param([string]$Path)
    $full = Get-FullPath -Path $Path
    ($full -replace '\\', '/')
}

function Resolve-PythonPath {
    param([string]$Requested)
    if ($Requested -and (Test-Path -LiteralPath $Requested)) {
        return (Get-Item -LiteralPath $Requested).FullName
    }
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    throw "Python was not found. Pass -Python with a valid python.exe path."
}

function Get-FileSha256 {
    param([string]$Path)
    (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
}

function Convert-CdbHexToUInt64 {
    param([string]$Value)
    $clean = ($Value -replace '`', '').Trim()
    [Convert]::ToUInt64($clean, 16)
}

function Get-SurfaceRuntimeFailure {
    param(
        [bool]$AccessViolation,
        [bool]$AppRequestQuit,
        [AllowNull()][string]$RuntimeError
    )
    if ($AccessViolation) {
        return 'access violation observed during surface capture'
    }
    if ($RuntimeError) {
        return $RuntimeError
    }
    if ($AppRequestQuit) {
        return 'game requested App_RequestQuit during surface capture'
    }
    return $null
}

function Save-ProcessMemory {
    param(
        [int]$ProcessId,
        [UInt64]$BaseAddress,
        [int]$ByteCount,
        [string]$OutputPath
    )

    if ($ByteCount -le 0) {
        throw "Invalid memory byte count: $ByteCount"
    }
    $processVmRead = 0x0010
    $processQueryInformation = 0x0400
    $handle = [ClashSurfaceDumpNative]::OpenProcess($processVmRead -bor $processQueryInformation, $false, [uint32]$ProcessId)
    if ($handle -eq [IntPtr]::Zero) {
        $lastError = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        throw "OpenProcess($ProcessId) failed with Win32 error $lastError"
    }
    try {
        $buffer = New-Object byte[] $ByteCount
        $bytesRead = [UIntPtr]::Zero
        $address = [IntPtr]::new([int64]$BaseAddress)
        $ok = [ClashSurfaceDumpNative]::ReadProcessMemory(
            $handle,
            $address,
            $buffer,
            [uint32]$ByteCount,
            [ref]$bytesRead
        )
        if (-not $ok) {
            $lastError = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
            throw "ReadProcessMemory(0x$($BaseAddress.ToString('x')), $ByteCount) failed with Win32 error $lastError"
        }
        if ($bytesRead.ToUInt64() -ne [uint64]$ByteCount) {
            throw "ReadProcessMemory read $bytesRead bytes, expected $ByteCount"
        }
        [System.IO.File]::WriteAllBytes($OutputPath, $buffer)
    }
    finally {
        [ClashSurfaceDumpNative]::CloseHandle($handle) | Out-Null
    }
}

function Start-CdbOnHiddenDesktop {
    param(
        [string]$CdbPath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [string]$DesktopName
    )

    $desktopAllAccess = 0x000F01FF
    $desktop = [ClashSurfaceDumpNative]::CreateDesktop($DesktopName, [IntPtr]::Zero, [IntPtr]::Zero, 0, $desktopAllAccess, [IntPtr]::Zero)
    if ($desktop -eq [IntPtr]::Zero) {
        $lastError = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        throw "CreateDesktop failed with Win32 error $lastError. Refusing visible fallback without -AllowVisibleDesktop."
    }

    $startupInfo = New-Object ClashSurfaceDumpNative+STARTUPINFO
    $startupInfo.cb = [Runtime.InteropServices.Marshal]::SizeOf([type]'ClashSurfaceDumpNative+STARTUPINFO')
    $startupInfo.lpDesktop = $DesktopName
    $startupInfo.dwFlags = 0x00000001
    $startupInfo.wShowWindow = 0

    $processInfo = New-Object ClashSurfaceDumpNative+PROCESS_INFORMATION
    $commandLine = New-Object System.Text.StringBuilder
    [void]$commandLine.Append((Quote-CommandLineArgument $CdbPath))
    foreach ($argument in $Arguments) {
        [void]$commandLine.Append(' ')
        [void]$commandLine.Append((Quote-CommandLineArgument $argument))
    }

    $creationFlags = 0x00000010
    $ok = [ClashSurfaceDumpNative]::CreateProcess(
        $CdbPath,
        $commandLine,
        [IntPtr]::Zero,
        [IntPtr]::Zero,
        $false,
        $creationFlags,
        [IntPtr]::Zero,
        $WorkingDirectory,
        [ref]$startupInfo,
        [ref]$processInfo
    )
    if (-not $ok) {
        $lastError = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        [ClashSurfaceDumpNative]::CloseDesktop($desktop) | Out-Null
        throw "CreateProcess on hidden desktop failed with Win32 error $lastError."
    }

    [ClashSurfaceDumpNative]::CloseHandle($processInfo.hThread) | Out-Null
    [pscustomobject]@{
        ProcessId = [int]$processInfo.dwProcessId
        ProcessHandle = $processInfo.hProcess
        DesktopHandle = $desktop
        DesktopName = $DesktopName
        CommandLine = $commandLine.ToString()
    }
}

function Stop-LaunchedProcesses {
    param(
        [Nullable[int]]$CdbPid,
        [string]$CandidatePath,
        [datetime]$RunStart,
        [string]$CdbPath
    )

    $toStop = @()
    if ($CdbPid) {
        $cdbProcess = Get-Process -Id $CdbPid -ErrorAction SilentlyContinue
        if ($cdbProcess) {
            try {
                if ($cdbProcess.Path -eq (Get-FullPath -Path $CdbPath) -and $cdbProcess.StartTime -ge $RunStart.AddSeconds(-5)) {
                    $toStop += $cdbProcess
                }
            } catch { }
        }
    }
    $candidateFull = Get-FullPath -Path $CandidatePath
    $toStop += Get-Process -ErrorAction SilentlyContinue |
        Where-Object {
            try {
                $_.Path -eq $candidateFull -and $_.StartTime -ge $RunStart.AddSeconds(-5)
            }
            catch {
                $false
            }
        }

    foreach ($process in ($toStop | Sort-Object Id -Unique)) {
        try {
            if (-not $process.HasExited) {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        }
        catch {
        }
    }
}

function Get-LaunchedCandidateProcesses {
    param(
        [string]$CandidatePath,
        [datetime]$RunStart
    )

    $candidateFull = Get-FullPath -Path $CandidatePath
    @(Get-Process -ErrorAction SilentlyContinue |
        Where-Object {
            try {
                $_.Path -eq $candidateFull -and $_.StartTime -ge $RunStart.AddSeconds(-5)
            }
            catch {
                $false
            }
        })
}

function Test-LaunchedProcessesStopped {
    param([Nullable[int]]$CdbPid, [string]$CandidatePath, [datetime]$RunStart,
          [string]$CdbPath, [ValidateRange(0,10000)][int]$WaitMilliseconds = 5000)
    $deadline = (Get-Date).AddMilliseconds($WaitMilliseconds)
    do {
        $remaining = @()
        $inspectionErrors = @()
        $candidateFull = Get-FullPath -Path $CandidatePath
        $candidateProcessName = [System.IO.Path]::GetFileNameWithoutExtension($candidateFull)
        foreach ($process in @(Get-Process -Name $candidateProcessName -ErrorAction SilentlyContinue)) {
            try {
                if ([string]::IsNullOrWhiteSpace($process.Path)) { throw 'Candidate process path is unavailable.' }
                if ($process.Path -eq $candidateFull -and $process.StartTime -ge $RunStart.AddSeconds(-5)) {
                    $remaining += $process
                }
            } catch { $inspectionErrors += "Cannot verify candidate identity: $($_.Exception.Message)" }
        }
        if ($CdbPid) {
            $process = Get-Process -Id $CdbPid -ErrorAction SilentlyContinue
            if ($process) {
                try {
                    if ([string]::IsNullOrWhiteSpace($process.Path)) { throw 'CDB process path is unavailable.' }
                    if ($process.Path -eq (Get-FullPath -Path $CdbPath) -and $process.StartTime -ge $RunStart.AddSeconds(-5)) {
                        $remaining += $process
                    }
                } catch { $inspectionErrors += "Cannot verify launched CDB identity: $($_.Exception.Message)" }
            }
        }
        if (-not $remaining.Count -and -not $inspectionErrors.Count) { break }
        if ((Get-Date) -ge $deadline) { break }
        Start-Sleep -Milliseconds 100
    } while ($true)
    [pscustomobject]@{
        Passed = (-not $remaining.Count -and -not $inspectionErrors.Count)
        RemainingProcessIds = @($remaining | Select-Object -ExpandProperty Id -Unique)
        InspectionErrors = $inspectionErrors
        Scope = 'launched CDB id/path/start and exact candidate path/start'
        WaitMilliseconds = $WaitMilliseconds
    }
}

function Save-TimeoutStack {
    param(
        [string]$CdbPath,
        [string]$CandidatePath,
        [datetime]$RunStart,
        [string]$StackLogPath
    )

    $target = Get-LaunchedCandidateProcesses -CandidatePath $CandidatePath -RunStart $RunStart |
        Sort-Object StartTime -Descending |
        Select-Object -First 1
    if (-not $target) {
        return $false
    }

    $stackCommand = '~* kb; lm; q'
    $stackArgs = @('-pv', '-p', [string]$target.Id, '-logo', $StackLogPath, '-c', $stackCommand)
    $stackArgLine = ($stackArgs | ForEach-Object { Quote-CommandLineArgument $_ }) -join ' '
    $stackProcess = Start-Process -FilePath $CdbPath -ArgumentList $stackArgLine -PassThru -WindowStyle Hidden
    if (-not $stackProcess.WaitForExit(15000)) {
        Stop-Process -Id $stackProcess.Id -Force -ErrorAction SilentlyContinue
        return (Test-Path -LiteralPath $StackLogPath)
    }
    return (Test-Path -LiteralPath $StackLogPath)
}

function Parse-SurfaceDumpReady {
    param([string]$LogPath)
    if (-not (Test-Path -LiteralPath $LogPath)) {
        return $null
    }
    $readyPattern = 'SURFDUMP_READY redraw_seq=(\d+) surface=([0-9a-fA-F`]+) size=\((\d+),(\d+)\) base=([0-9a-fA-F`]+) bytes=(\d+)'
    foreach ($line in (Get-Content -LiteralPath $LogPath)) {
        $match = [regex]::Match($line, $readyPattern)
        if ($match.Success) {
            return [pscustomobject]@{
                RedrawSeq = [int]$match.Groups[1].Value
                Surface = $match.Groups[2].Value
                Width = [int]$match.Groups[3].Value
                Height = [int]$match.Groups[4].Value
                Base = $match.Groups[5].Value
                Bytes = [int]$match.Groups[6].Value
            }
        }
    }
    $null
}

function Test-RequestedSurfaceReady {
    param($Ready, $Geometry)
    ($null -ne $Ready -and $Ready.Width -eq $Geometry.width -and
        $Ready.Height -eq $Geometry.height -and
        $Ready.Bytes -eq ($Geometry.width * $Geometry.height) -and
        (Convert-CdbHexToUInt64 -Value $Ready.Base) -ne 0 -and
        (Convert-CdbHexToUInt64 -Value $Ready.Surface) -ne 0)
}

function Set-SurfaceProxyPresentSetting {
    param([bool]$HiddenDesktop)
    $previous = [Environment]::GetEnvironmentVariable('CLASH_PROXY_PRESENT', 'Process')
    if ($HiddenDesktop) {
        [Environment]::SetEnvironmentVariable('CLASH_PROXY_PRESENT', '0', 'Process')
    }
    [pscustomobject]@{
        Previous = $previous
        Effective = [Environment]::GetEnvironmentVariable('CLASH_PROXY_PRESENT', 'Process')
    }
}

function Restore-SurfaceProxyPresentSetting {
    param($Setting)
    if ($null -ne $Setting) {
        [Environment]::SetEnvironmentVariable('CLASH_PROXY_PRESENT', $Setting.Previous, 'Process')
    }
}

foreach ($path in @($InputExe, $WorkDir, $Cdb, $ProbeTemplate)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required path was not found: $path"
    }
}
if ($ExtraProbeTemplate -and -not (Test-Path -LiteralPath $ExtraProbeTemplate)) {
    throw "Extra CDB probe template was not found: $ExtraProbeTemplate"
}

$pythonExe = Resolve-PythonPath -Requested $Python
$patcher = Join-Path $RepoRoot 'patch_clash95_hd.py'
$converter = Join-Path $RepoRoot 'tools\cdb_surface_dump_to_png.py'
$coverageTool = Join-Path $RepoRoot 'tools\map_tile_coverage.py'
$visibilityTool = Join-Path $RepoRoot 'tools\visibility_coverage.py'
$forcedVisibleTool = Join-Path $RepoRoot 'tools\forced_visible_summary.py'
$postOwnerForcedVisibleTool = Join-Path $RepoRoot 'tools\post_owner_forced_visible_summary.py'
$probeRenderer = Join-Path $RepoRoot 'tools\render_cdb_surface_probe.py'
$initialTraceTool = Join-Path $RepoRoot 'tools\initial_map_paint_trace.py'
if ($InitialMapPaintValidation -and -not (Test-Path -LiteralPath $initialTraceTool -PathType Leaf)) {
    throw 'Initial map paint trace verifier is missing; no candidate was built.'
}
foreach ($path in @($patcher, $converter, $coverageTool, $visibilityTool, $forcedVisibleTool, $postOwnerForcedVisibleTool, $probeRenderer)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required helper was not found: $path"
    }
}
if ($UseDdrawProxy -and -not (Test-Path -LiteralPath $DdrawProxyBuildScript)) {
    throw "DirectDraw proxy build script was not found: $DdrawProxyBuildScript"
}

# Pure source preflight happens before building a proxy or patching a candidate.
# The base probe is also consumed by soak runs: render a copy, never edit it.
$renderArgs = @('-B', $probeRenderer, '--template', $ProbeTemplate, '--resolution', $Resolution, '--stage', $recipeStage, '--load-slot', $LoadSlot)
if ($ForceVisibleEdges) { $renderArgs += '--force-visible-edges' }
if ($PostOwnerForceVisibleSeven) { $renderArgs += '--post-owner-force-visible-seven' }
if ($ExtraProbeTemplate) { $renderArgs += @('--extra-probe', '--extra-probe-path', $ExtraProbeTemplate) }
if ($SkipMapValidation) { $renderArgs += '--skip-map-validation' }
$probeRecipeJson = & $pythonExe @renderArgs
if ($LASTEXITCODE -ne 0) {
    throw 'Surface probe resolution preflight failed; no candidate was built.'
}
$probeRecipe = $probeRecipeJson | ConvertFrom-Json
$surfaceGeometry = $probeRecipe.geometry
$Resolution = $surfaceGeometry.resolution
if ($Resolution -ne '800x600') { $RequireGameplay = $true }
if ($PartialTileValidation) {
    if ($CompleteHdValidation) {
        $partialPreflightJson = & $pythonExe -B $partialTileBuilder --input ([System.IO.Path]::GetFullPath($InputExe)) --stage $Stage --resolution $Resolution --preflight
    } else {
        $partialPreflightJson = & $pythonExe -B $partialTileBuilder --original ([System.IO.Path]::GetFullPath($InputExe)) --resolution $Resolution --preflight @partialBuilderOptions
    }
    if ($LASTEXITCODE -ne 0) { throw 'Partial-tile source/byte preflight failed; no proxy or candidate was built.' }
    $partialPreflight = $partialPreflightJson | ConvertFrom-Json
    if ((-not $CompleteHdValidation -and -not $partialPreflight.preflight_passed) -or
        $partialPreflight.stage -cne $Stage -or $partialPreflight.resolution -cne $Resolution) {
        throw 'Partial-tile preflight identity mismatch.'
    }
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
if (-not $CandidateName) {
    $CandidateName = "clash95_hd_surfdump_$($stamp -replace '-', '_').exe"
}
if ([System.IO.Path]::GetFileName($CandidateName) -ne $CandidateName) {
    throw "-CandidateName must be a file name, not a path"
}
if (-not $CandidateDir) {
    $CandidateDir = $WorkDir
}
if (-not (Test-Path -LiteralPath $CandidateDir)) {
    New-Item -ItemType Directory -Path $CandidateDir -Force | Out-Null
}

$candidatePath = Join-Path $CandidateDir $CandidateName
$inputFull = Get-FullPath -Path $InputExe
$candidateFull = Get-FullPath -Path $candidatePath
if ($candidateFull -eq $inputFull) {
    throw "Refusing to overwrite the input executable: $inputFull"
}
if ((Split-Path -Leaf $inputFull).ToLowerInvariant() -eq 'clash95.exe' -and $candidateFull -eq (Join-Path (Split-Path -Parent $inputFull) 'clash95.exe')) {
    throw "Refusing to overwrite the original Clash95 executable"
}
if (Test-Path -LiteralPath $candidateFull) {
    throw "Candidate already exists: $candidateFull"
}

$runDir = Join-Path $OutRoot "cdb-surface-dump-$stamp"
if (Test-Path -LiteralPath $runDir) { throw "Run output already exists; preserve its evidence: $runDir" }
New-Item -ItemType Directory -Path $runDir | Out-Null
$logPath = Join-Path $runDir 'cdb-surface-dump.log'
$rawPath = Join-Path $runDir 'surface.raw'
$pngPath = Join-Path $runDir 'surface.png'
$pngMetaPath = Join-Path $runDir 'surface.png.json'
$coverageJson = Join-Path $runDir 'map-tile-coverage.json'
$coverageText = Join-Path $runDir 'map-tile-coverage.txt'
$visibilityJson = Join-Path $runDir 'visibility-coverage-summary.json'
$visibilityText = Join-Path $runDir 'visibility-coverage.txt'
$forcedVisibleJson = Join-Path $runDir 'forced-visible-summary.json'
$forcedVisibleText = Join-Path $runDir 'forced-visible-summary.txt'
$postOwnerForcedVisibleJson = Join-Path $runDir 'post-owner-forced-visible-summary.json'
$postOwnerForcedVisibleText = Join-Path $runDir 'post-owner-forced-visible-summary.txt'
$summaryJson = Join-Path $runDir 'summary.json'
$runSummary = Join-Path $runDir 'RUN-SUMMARY.md'
$timeoutStackLog = Join-Path $runDir 'timeout-stack.log'
$generatedProbe = Join-Path $runDir 'clash95_surface_dump_probe.generated.cdb'

$proxyDllPath = $null
$proxyManifestPath = $null
$proxyLogPath = $null
$proxyPalettePath = $null
$proxySha = $null
if ($UseDdrawProxy) {
    $candidateDirFull = Get-FullPath -Path $CandidateDir
    $workDirFull = Get-FullPath -Path $WorkDir
    if ($candidateDirFull -eq $workDirFull) {
        throw "Use -CandidateDir with an isolated folder when -UseDdrawProxy is set. Refusing to place ddraw.dll in $workDirFull."
    }
    if ($DdrawProxyDll) {
        $proxyDllPath = Get-FullPath -Path $DdrawProxyDll
    }
    else {
        $proxyDllPath = Join-Path $candidateDirFull 'ddraw.dll'
    }
    if ((Split-Path -Leaf $proxyDllPath).ToLowerInvariant() -ne 'ddraw.dll') {
        throw "DirectDraw proxy output must be named ddraw.dll so the target process loads it locally: $proxyDllPath"
    }
    if ((Get-FullPath -Path (Split-Path -Parent $proxyDllPath)) -ne $candidateDirFull) {
        throw "DirectDraw proxy must be placed next to the candidate executable in $candidateDirFull"
    }
    & $DdrawProxyBuildScript -OutputDll $proxyDllPath -LogDir $runDir
    $proxyBuildExit = $LASTEXITCODE
    if ($proxyBuildExit -ne 0) {
        throw "DirectDraw proxy build failed with exit code $proxyBuildExit"
    }
    $proxySha = Get-FileSha256 -Path $proxyDllPath
    $proxyManifestPath = Join-Path $candidateDirFull 'ddraw_surfdump_proxy.build.json'
    $proxyLogPath = Join-Path $candidateDirFull 'ddraw_surfdump_proxy.log'
    $proxyPalettePath = Join-Path $candidateDirFull 'ddraw_surfdump_palette.bin'
    Remove-Item -LiteralPath $proxyLogPath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $proxyPalettePath -Force -ErrorAction SilentlyContinue
}

$inputSha = Get-FileSha256 -Path $inputFull
$candidateManifestPath = $null
$candidateManifest = $null
$partialContractStage = $Stage
if ($CompleteHdValidation) {
    & $pythonExe -B $partialTileBuilder --input $inputFull --output $candidateFull --stage $Stage --resolution $Resolution
    $patchExit = $LASTEXITCODE
    if ($patchExit -ne 0) { throw "Complete candidate builder failed with exit code $patchExit" }
    $candidateManifestPath = [System.IO.Path]::ChangeExtension($candidateFull, '.candidate.json')
    $candidateManifest = Get-Content -LiteralPath $candidateManifestPath -Raw | ConvertFrom-Json
    $partialBuildReport = $candidateManifestPath
    $ExtraProbeTemplate = [System.IO.Path]::ChangeExtension($candidateFull, '.cdb')
    $partialContractStage = $candidateManifest.probe_contract.inherited_stage
    if ($candidateManifest.stage -cne $Stage -or $candidateManifest.resolution -cne $Resolution -or
        $candidateManifest.base_sha256 -cne $inputSha.ToLowerInvariant() -or
        $candidateManifest.probe_sha256 -cne (Get-FileSha256 -Path $ExtraProbeTemplate).ToLowerInvariant() -or
        -not $candidateManifest.probe_contract.requires_loaded_byte_checks -or
        -not $candidateManifest.probe_contract.all_inherited_checks_required) {
        throw 'Complete candidate bundle identity or inherited probe contract differs.'
    }
}
elseif ($PartialTileValidation) {
    $partialBuildReport = Join-Path $runDir 'partial-tile-build.json'
    $ExtraProbeTemplate = Join-Path $runDir 'partial-tile-installed.extra.cdb'
    & $pythonExe -B $partialTileBuilder --original $inputFull --output $candidateFull --resolution $Resolution --report-json $partialBuildReport --probe-out $ExtraProbeTemplate @partialBuilderOptions
}
else {
    & $pythonExe $patcher --input $inputFull --output $candidateFull --stage $Stage --resolution $Resolution
}
$patchExit = $LASTEXITCODE
if ($patchExit -ne 0) {
    throw "patch_clash95_hd.py failed with exit code $patchExit"
}
$candidateSha = Get-FileSha256 -Path $candidateFull
if ($PartialTileValidation -and $candidateSha.ToLowerInvariant() -ne $partialPreflight.candidate_sha256) {
    throw 'Partial-tile candidate differs from the preflight recipe.'
}

$probeText = $probeRecipe.template
# Preserve placeholder-based legacy/extra templates using the source-checked recipe.
$mainMouseRawX = [int]$surfaceGeometry.main_menu_mouse[0] -shl 6
$mainMouseRawY = [int]$surfaceGeometry.main_menu_mouse[1] -shl 6
$loadMouseX = $surfaceGeometry.load_mouse[0]
$loadMouseY = $surfaceGeometry.load_mouse[1]
$loadMouseRawX = $loadMouseX -shl 6
$loadMouseRawY = $loadMouseY -shl 6
$preEntryLoadCoordAction = if ($LateLoadSlotForcingOnly) {
    '.if (@$t1 < 0n16) { .printf \"SURFDUMP_PRE_ENTRY_SLOT_DEFERRED seq=%d choice=%d entry=0x%08x ex=%d ey=%d mouse=(%d,%d) selected=%d accept=%d\\n\", @$t1, poi(00543d7c), @eax, poi(@eax), poi(@eax+4), poi(00544cfc)>>by(0054512c), poi(00544d00)>>by(0054512c), poi(005441e0), poi(00544190); r @$t1 = @$t1 + 1; };'
}
else {
    'ed 00544cfc __LOAD_MOUSE_RAW_X__; ed 00544d00 __LOAD_MOUSE_RAW_Y__; eb 005451c0 80; ed 00544d04 1; .if (@$t1 < 0n16) { .printf \"SURFDUMP_LOAD_COORD seq=%d choice=%d entry=0x%08x ex=%d ey=%d mouse=(%d,%d) selected=%d accept=%d\\n\", @$t1, poi(00543d7c), @eax, poi(@eax), poi(@eax+4), poi(00544cfc)>>by(0054512c), poi(00544d00)>>by(0054512c), poi(005441e0), poi(00544190); r @$t1 = @$t1 + 1; };'
}
$probeText = $probeText.Replace('__PRE_ENTRY_LOAD_COORD_ACTION__', $preEntryLoadCoordAction)
$probeText = $probeText.Replace('__LOAD_SLOT__', [string]$LoadSlot)
$probeText = $probeText.Replace('__MAIN_MOUSE_RAW_X__', ('{0:x8}' -f $mainMouseRawX))
$probeText = $probeText.Replace('__MAIN_MOUSE_RAW_Y__', ('{0:x8}' -f $mainMouseRawY))
$probeText = $probeText.Replace('__LOAD_MOUSE_RAW_X__', ('{0:x8}' -f $loadMouseRawX))
$probeText = $probeText.Replace('__LOAD_MOUSE_RAW_Y__', ('{0:x8}' -f $loadMouseRawY))
if ($PostOwnerForceVisibleSeven -and -not $ExtraProbeTemplate) {
    throw '-PostOwnerForceVisibleSeven requires -ExtraProbeTemplate with the post-owner visibility probe.'
}
if ($ExtraProbeTemplate) {
    if ($probeRecipe.extra_probe_sha256 -and
        (Get-FileSha256 -Path $ExtraProbeTemplate).ToLowerInvariant() -cne $probeRecipe.extra_probe_sha256) {
        throw 'Extra probe changed after source preflight; refusing a mixed probe recipe.'
    }
    $extraProbeText = (Get-Content -LiteralPath $ExtraProbeTemplate -Raw).Trim()
    $extraProbeText = $extraProbeText.Replace('__LOAD_SLOT__', [string]$LoadSlot)
    $extraProbeText = $extraProbeText.Replace('__LOAD_MOUSE_RAW_X__', ('{0:x8}' -f $loadMouseRawX))
    $extraProbeText = $extraProbeText.Replace('__LOAD_MOUSE_RAW_Y__', ('{0:x8}' -f $loadMouseRawY))
    if ($extraProbeText -match '(?m)^\s*g\s*$') {
        throw "Extra CDB probe template must not contain a standalone g command: $ExtraProbeTemplate"
    }
    if ($PostOwnerForceVisibleSeven) {
        if ($extraProbeText -notmatch 'APVIS_CELL') {
            throw "-PostOwnerForceVisibleSeven requires an extra probe that logs the APVIS_CELL rows: $ExtraProbeTemplate"
        }
        $extraProbeText = ('.echo APPOST_FORCE_VISIBLE_SEVEN_GATE_ENABLED' + "`r`n" + $extraProbeText)
    }
    if ($extraProbeText -match '__BT_HOT_(BP|TEXT_BP|PRESENT_BP)_(ENABLE|DISABLE)_COMMANDS?__') {
        $startAnimsBpCount = if ($NoSkipStartAnims) {
            0
        }
        elseif ($FastForwardStartAnims) {
            6
        }
        else {
            1
        }
        # probes/cdb/ui/clash95_border_tooltip_extra.cdb declares nine cold breakpoints before
        # the three hot text/present breakpoints. Keep those hot breakpoints
        # disabled until gameplay full redraw reaches the extra probe.
        $hotStartId = 20 + $startAnimsBpCount + 9
        $hotTextIds = @($hotStartId, ($hotStartId + 1))
        $hotPresentId = $hotStartId + 2
        $hotIds = @($hotTextIds + @($hotPresentId))
        $hotReplacements = @{
            '__BT_HOT_BP_ENABLE_COMMANDS__' = (($hotIds | ForEach-Object { "be $_" }) -join '; ')
            '__BT_HOT_BP_DISABLE_COMMANDS__' = (($hotIds | ForEach-Object { "bd $_" }) -join '; ')
            '__BT_HOT_TEXT_BP_ENABLE_COMMANDS__' = (($hotTextIds | ForEach-Object { "be $_" }) -join '; ')
            '__BT_HOT_TEXT_BP_DISABLE_COMMANDS__' = (($hotTextIds | ForEach-Object { "bd $_" }) -join '; ')
            '__BT_HOT_PRESENT_BP_ENABLE_COMMAND__' = "be $hotPresentId"
            '__BT_HOT_PRESENT_BP_DISABLE_COMMAND__' = "bd $hotPresentId"
        }
        foreach ($placeholder in $hotReplacements.Keys) {
            $extraProbeText = $extraProbeText.Replace($placeholder, $hotReplacements[$placeholder])
        }
    }
    $playGamePattern = '(?m)^bp 0040B660 '
    if ($probeText -notmatch $playGamePattern) {
        throw 'Could not find the PlayGame breakpoint insertion point in the CDB probe template.'
    }
    $probeText = [regex]::Replace(
        $probeText,
        $playGamePattern,
        ($extraProbeText + "`r`n`r`n" + 'bp 0040B660 '),
        1
    )
}
if ($NoSkipStartAnims -and $FastForwardStartAnims) {
    throw 'Use only one startup-animation mode: -NoSkipStartAnims or -FastForwardStartAnims.'
}
$startAnimsBreakpoint = if ($NoSkipStartAnims) {
    '.echo SURFDUMP_START_ANIMS_SKIP_DISABLED'
}
elseif ($FastForwardStartAnims) {
    @(
        '.echo SURFDUMP_START_ANIMS_SLEEP_FAST_FORWARD_ENABLED'
        'bp 0044789a ".printf \"SURFDUMP_SKIP_START_SLEEP ret=004478a1\\n\"; r eip=004478a1; r esp=@esp+4; gc"'
        'bp 0046e4d0 ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_AVI_SLEEP call=0046e4d0 next=0046e4d7\\n\"; r @$t12 = @$t12 + 1; }; r eip=0046e4d7; r esp=@esp+4; gc } .else { gc }"'
        'bp 0046e6df ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_AVI_SLEEP call=0046e6df next=0046e6e6\\n\"; r @$t12 = @$t12 + 1; }; r eip=0046e6e6; r esp=@esp+4; gc } .else { gc }"'
        'bp 0046fd01 ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_AVI_SLEEP call=0046fd01 next=0046fd08\\n\"; r @$t12 = @$t12 + 1; }; r eip=0046fd08; r esp=@esp+4; gc } .else { gc }"'
        'bp 0047BFD0 ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_TIME_SLEEP ret=%p\\n\", poi(@esp); r @$t12 = @$t12 + 1; }; r eax=0; r eip=poi(@esp); r esp=@esp+4; gc } .else { gc }"'
    ) -join "`r`n"
}
else {
    'bp 00447840 ".printf \"SURFDUMP_SKIP_START_ANIMS ret=%p\\n\", poi(@esp); r eax=0; r eip=poi(@esp); r esp=@esp+4; gc"'
}
$probeText = $probeText.Replace('__START_ANIMS_BP__', $startAnimsBreakpoint)
$visibilityPlayGameAction = if ($ForceVisibleEdges) {
    '.if ((poi(poi(005202e4)+0n140008) == 0n10) & (poi(poi(005202e4)+0n140012) == 0n17)) { r @$t18 = poi(005202e4); eb @$t18+0n140081+(0n20*0n13)+2 f0; eb @$t18+0n140081+(0n21*0n13)+2 f0; eb @$t18+0n140081+(0n20*0n13)+3 03; eb @$t18+0n140081+(0n21*0n13)+3 03; eb @$t18+0n140081+(0n10*0n13)+3 02; be 0; be 1; be 2; be 3; be 4; be 5; be 6; .printf \"SURFDUMP_FORCE_VISIBLE_EDGES scroll=(%d,%d) bytes x20y20_23=%02x x21y20_23=%02x x20y24_25=%02x x21y24_25=%02x x10y25=%02x timing=playgame\\n\", poi(@$t18+0n140008), poi(@$t18+0n140012), by(@$t18+0n140081+(0n20*0n13)+2), by(@$t18+0n140081+(0n21*0n13)+2), by(@$t18+0n140081+(0n20*0n13)+3), by(@$t18+0n140081+(0n21*0n13)+3), by(@$t18+0n140081+(0n10*0n13)+3); } .else { .printf \"SURFDUMP_FORCE_VISIBLE_EDGES_SKIPPED scroll=(%d,%d) expected=(10,17) timing=playgame\\n\", poi(poi(005202e4)+0n140008), poi(poi(005202e4)+0n140012); };'
}
elseif ($PostOwnerForceVisibleSeven) {
    '.if ((poi(poi(005202e4)+0n140008) == 0n10) & (poi(poi(005202e4)+0n140012) == 0n17)) { r @$t10 = poi(005202e4); .printf \"APPOST_FORCE_VISIBLE_SEVEN timing=playgame scroll=(%d,%d) old_x20b2=%02x old_x21b2=%02x old_x20b3=%02x old_x21b3=%02x old_x10b3=%02x cells=r6c10,r6c11,r7c10,r7c11,r8c0,r8c10,r8c11\\n\", poi(@$t10+0n140008), poi(@$t10+0n140012), by(@$t10+0n140081+(0n20*0n13)+2), by(@$t10+0n140081+(0n21*0n13)+2), by(@$t10+0n140081+(0n20*0n13)+3), by(@$t10+0n140081+(0n21*0n13)+3), by(@$t10+0n140081+(0n10*0n13)+3); eb @$t10+0n140081+(0n20*0n13)+2 80; eb @$t10+0n140081+(0n21*0n13)+2 80; eb @$t10+0n140081+(0n20*0n13)+3 03; eb @$t10+0n140081+(0n21*0n13)+3 03; eb @$t10+0n140081+(0n10*0n13)+3 02; .printf \"APPOST_FORCE_VISIBLE_SEVEN_DONE timing=playgame new_x20b2=%02x new_x21b2=%02x new_x20b3=%02x new_x21b3=%02x new_x10b3=%02x\\n\", by(@$t10+0n140081+(0n20*0n13)+2), by(@$t10+0n140081+(0n21*0n13)+2), by(@$t10+0n140081+(0n20*0n13)+3), by(@$t10+0n140081+(0n21*0n13)+3), by(@$t10+0n140081+(0n10*0n13)+3); } .else { .printf \"APPOST_FORCE_VISIBLE_SEVEN_SKIPPED timing=playgame scroll=(%d,%d) expected=(10,17)\\n\", poi(poi(005202e4)+0n140008), poi(poi(005202e4)+0n140012); };'
}
else {
    ''
}
if ($ForceVisibleEdges -and $probeRecipe.force_playgame_action) {
    $visibilityPlayGameAction = $probeRecipe.force_playgame_action
}
$probeText = $probeText.Replace('__VISIBILITY_PLAYGAME_ACTION__', $visibilityPlayGameAction)
$visibilityRedrawAction = if ($ForceVisibleEdges) {
    'ed @$t10+0n140008 0n10; ed @$t10+0n140012 0n17; ed 00544cfc 00004b00; ed 00544d00 00003680; eb 005451c0 00; ed 00544d04 0; .if (@$t13 < 0n4) { .printf \"SURFDUMP_FORCE_VIEWPORT scroll=(%d,%d) mouse=(%d,%d) timing=redraw\\n\", poi(@$t10+0n140008), poi(@$t10+0n140012), poi(00544cfc)>>by(0054512c), poi(00544d00)>>by(0054512c); };'
}
else {
    ''
}
$probeText = $probeText.Replace('__VISIBILITY_PATCH_ACTION__', $visibilityRedrawAction)
$surfaceDumpAction = if ($InitialMapPaintValidation) {
    # This is the existing update-entry breakpoint after prior calls returned.
    # Leave CDB stopped here so the host reads a coherent surface and cannot
    # terminate a PTILE printf or an in-flight incremental invocation.
    '.printf \"PTILE_TRACE_CLOSED tid=%x eip=%p esp=%p\\n\", @$tid, @eip, @esp; .echo SURFDUMP_HOST_READY;'
}
elseif ($UseCdbWriteMem) {
    '.writemem ' + (Get-CdbFileToken -Path $rawPath) + ' @$t16 L@$t17; .echo SURFDUMP_DONE; q;'
}
else {
    '.echo SURFDUMP_HOST_READY; gc'
}
$framedMinimapAction = if ($FramedValidation) {
    # Observe the actual enabled backing at this same stopped capture boundary.
    # The selector and per-player flag mirror native40DD60; never guess a mask.
    '.if (poi(005202e4) == 0) { .echo FRAMED_CAPTURE_REJECT missing_game_data; q } .else { .if ((poi(poi(005202e4)+23ec7) != 0) & (poi(poi(005202e4)+23ec7) != 1) & (poi(poi(005202e4)+23ec7) != 2) & (poi(poi(005202e4)+23ec7) != 3) & (poi(poi(005202e4)+23ec7) != 4)) { .echo FRAMED_CAPTURE_REJECT minimap_selector; q } .else { .printf \"FRAMED_MINIMAP enabled=%d origin=(%d,%d) size=(%d,%d)\\n\", (poi(poi(005202e4)+2230f+poi(poi(005202e4)+23ec7)*58f) != 0), wo(00523344), wo(00523346), wo(00523348), wo(0052334a); }; };'
} else { '' }
$probeText = $probeText.Replace('__SURFACE_DUMP_ACTION__', ($framedMinimapAction + $surfaceDumpAction))
$probeText = $probeText.Replace('__RAW_PATH__', (Get-CdbFileToken -Path $rawPath))
Set-Content -LiteralPath $generatedProbe -Value $probeText -Encoding ASCII

$minimapObserverReport = $null
if ($MinimapViewportValidation) {
    # The canonical map probe and installed-byte extra remain preserved. The
    # additive observer reconstructs this exact candidate and records only
    # native draw arguments and state at the existing stopped capture boundary.
    $minimapObserverTool = Join-Path $RepoRoot 'tools\framed_minimap_probe.py'
    $minimapObserverReport = Join-Path $runDir 'minimap-observer.json'
    $minimapObservedProbe = Join-Path $runDir 'surface-minimap-probe.cdb'
    $minimapContextArgs = if ($CompleteHdValidation) { @('--candidate-manifest', $candidateManifestPath) } else { @() }
    & $pythonExe -B $minimapObserverTool --original $inputFull --candidate $candidateFull --resolution $Resolution --rendered-probe $generatedProbe --output $minimapObservedProbe --report $minimapObserverReport @minimapContextArgs
    if ($LASTEXITCODE -ne 0) { throw 'Minimap observer preparation failed before runtime.' }
    $generatedProbe = $minimapObservedProbe
}

$fullProgressReport = $null
if ($FullPaintProgressDiagnostic) {
    $fullProgressTool = Join-Path $RepoRoot 'tools\framed_full_progress_probe.py'
    $fullProgressReport = Join-Path $runDir 'full-paint-progress-observer.json'
    $fullObservedProbe = Join-Path $runDir 'surface-full-paint-progress-probe.cdb'
    # Reserve83..85 after minimap80/81 and before optional no-op82. The three
    # extra observers preserve all canonical PTILE declarations and records.
    $fullJson = & $pythonExe -B $fullProgressTool --original $inputFull --candidate $candidateFull --candidate-sha256 $candidateSha.ToLowerInvariant() --stage $Stage --resolution $Resolution --rendered-probe $generatedProbe --candidate-manifest $candidateManifestPath --first-breakpoint-id 83
    if ($LASTEXITCODE -ne 0) { throw 'Full-paint progress observer preparation failed before runtime.' }
    $fullPacket = $fullJson | ConvertFrom-Json
    if (-not $fullPacket.snippet -or $fullPacket.candidate_sha256 -cne $candidateSha.ToLowerInvariant() -or
        $fullPacket.stage -cne $Stage -or $fullPacket.resolution -cne $Resolution -or $fullPacket.acceptance -ne $false) {
        throw 'Full-paint progress observer identity or scope differs.'
    }
    $mainText = (Get-Content -LiteralPath $generatedProbe -Raw).Replace("`r`n", "`n")
    if ($mainText -notmatch '(?s)\ng\n*\z') { throw 'No final standalone g for full-paint observer.' }
    $finalGo = [regex]::Match($mainText, '(?s)g\n*\z')
    $composed = $mainText.Substring(0, $finalGo.Index) + $fullPacket.snippet + "g`n"
    [System.IO.File]::WriteAllText($fullObservedProbe, $composed, [System.Text.Encoding]::ASCII)
    $fullPacket | Add-Member -NotePropertyName ComposedProbeSha256 -NotePropertyValue (Get-FileSha256 -Path $fullObservedProbe)
    $fullPacket | Add-Member -NotePropertyName ComposedProbe -NotePropertyValue $fullObservedProbe
    $fullPacket | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $fullProgressReport -Encoding UTF8
    $generatedProbe = $fullObservedProbe
}

$noopProgressReport = $null
if ($NoopProgressDiagnostic) {
    $noopTool = Join-Path $RepoRoot 'tools\framed_noop_progress_probe.py'
    $noopProgressReport = Join-Path $runDir 'noop-progress-observer.json'
    $noopObservedProbe = Join-Path $runDir 'surface-noop-progress-probe.cdb'
    # Minimap owns 80/81. The diagnostic independently inventories 82 before
    # observing it and keeps every existing PTILE record unchanged.
    $noopJson = & $pythonExe -B $noopTool --original $inputFull --candidate $candidateFull --candidate-sha256 $candidateSha --stage $Stage --resolution $Resolution --rendered-probe $generatedProbe --candidate-manifest $candidateManifestPath --breakpoint-id 82 --json
    if ($LASTEXITCODE -ne 0) { throw 'Native no-op progress observer preparation failed before runtime.' }
    $noopPacket = $noopJson | ConvertFrom-Json
    if (-not $noopPacket.snippet -or $noopPacket.candidate_sha256 -cne $candidateSha.ToLowerInvariant() -or
        $noopPacket.stage -cne $Stage -or $noopPacket.resolution -cne $Resolution) {
        throw 'Native no-op progress observer identity differs.'
    }
    $mainText = (Get-Content -LiteralPath $generatedProbe -Raw).Replace("`r`n", "`n")
    if ($mainText -notmatch '(?s)\ng\n*\z') { throw 'No final standalone g for the native no-op observer.' }
    $finalGo = [regex]::Match($mainText, '(?s)g\n*\z')
    $composed = $mainText.Substring(0, $finalGo.Index) + $noopPacket.snippet + "g`n"
    # Export only this new composed run file with explicit CRLF. The canonical
    # candidate probe and prior main remain immutable, separately hashed files.
    [System.IO.File]::WriteAllText($noopObservedProbe, $composed.Replace("`r`n", "`n").Replace("`n", "`r`n"), [System.Text.Encoding]::ASCII)
    $noopPacket | Add-Member -NotePropertyName ComposedProbeSha256 -NotePropertyValue (Get-FileSha256 -Path $noopObservedProbe)
    $noopPacket | Add-Member -NotePropertyName ComposedProbe -NotePropertyValue $noopObservedProbe
    $noopPacket | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $noopProgressReport -Encoding UTF8
    $generatedProbe = $noopObservedProbe
}

function Export-CompleteRuntimeProbe {
    param([string]$SourcePath, [string]$OutputPath)
    if ([System.IO.Path]::GetFullPath($SourcePath) -eq [System.IO.Path]::GetFullPath($OutputPath)) {
        throw 'Complete runtime probe export must preserve its source.'
    }
    $sourceBytes = [System.IO.File]::ReadAllBytes($SourcePath)
    $strictAscii = [System.Text.Encoding]::GetEncoding('us-ascii', [System.Text.EncoderFallback]::ExceptionFallback, [System.Text.DecoderFallback]::ExceptionFallback)
    $text = $strictAscii.GetString($sourceBytes).Replace("`r`n", "`n")
    if ($text.Contains([char]0)) { throw 'Complete runtime probe must not contain NUL.' }
    if ($text.Contains("`r")) { throw 'Complete runtime probe contains a lone carriage return.' }
    $bytes = [System.Text.Encoding]::ASCII.GetBytes($text.Replace("`n", "`r`n"))
    $stream = [System.IO.File]::Open($OutputPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write)
    try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
}
if ($CompleteHdValidation) {
    # CDB consumes an explicit CRLF run file. The manifest-bound candidate
    # extra and LF observer intermediates remain unchanged and inspectable.
    $completeRuntimeProbe = Join-Path $runDir 'completehd-runtime-probe.cdb'
    Export-CompleteRuntimeProbe -SourcePath $generatedProbe -OutputPath $completeRuntimeProbe
    $generatedProbe = $completeRuntimeProbe
}

$runStart = Get-Date
$desktopName = "ClashSurfaceDump_$($stamp -replace '[^0-9A-Za-z_]', '_')"
$cdbCommand = '$$><' + $generatedProbe
$cdbArgs = @('-hd', '-logo', $logPath, '-c', $cdbCommand, $candidateFull)
$launch = $null
$cdbExitCode = $null
$timedOut = $false
$runtimeError = $null
$runtimeExceptionId = $null
$runtimeExceptionStack = $null
$cleanupResult = $null
$timeoutStackSaved = $false
$launchMode = 'hidden-desktop'
$stoppedAfterDump = $false
$hostDumpedMemory = $false
$surfaceCaptureSet = @()
$hostDumpError = $null
$surfaceGeometryFailure = $null
$postDumpObservationStarted = $false
$postDumpObservationCompleted = $false
$postDumpObservationStart = $null
$postDumpExitObserved = $false
$dumpMethod = if ($UseCdbWriteMem) { 'cdb-writemem' } else { 'host-readprocessmemory' }
$proxyPresentEnvironment = $null

try {
    # CreateProcess inherits this process environment. A hidden run must not
    # inherit present-on-Unlock painting from an earlier visible experiment.
    $proxyPresentEnvironment = Set-SurfaceProxyPresentSetting -HiddenDesktop (-not $AllowVisibleDesktop)
    if ($AllowVisibleDesktop) {
        $launchMode = 'visible-desktop-explicit'
        $cdbProcess = Start-Process -FilePath $Cdb -ArgumentList $cdbArgs -WorkingDirectory $WorkDir -PassThru -WindowStyle Hidden
        $launch = [pscustomobject]@{
            ProcessId = $cdbProcess.Id
            ProcessHandle = [IntPtr]::Zero
            DesktopHandle = [IntPtr]::Zero
            DesktopName = $null
            CommandLine = "$Cdb $($cdbArgs -join ' ')"
        }
    }
    else {
        $launch = Start-CdbOnHiddenDesktop -CdbPath $Cdb -Arguments $cdbArgs -WorkingDirectory $WorkDir -DesktopName $desktopName
        $cdbProcess = [System.Diagnostics.Process]::GetProcessById($launch.ProcessId)
    }

    $deadline = (Get-Date).AddSeconds($RunSeconds)
    while (-not $cdbProcess.HasExited -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 500
        $cdbProcess.Refresh()
        if ($cdbProcess.HasExited) {
            break
        }
        if (-not $UseCdbWriteMem) {
            $currentReady = Parse-SurfaceDumpReady -LogPath $logPath
            if ($currentReady -and -not (Test-RequestedSurfaceReady -Ready $currentReady -Geometry $surfaceGeometry)) {
                $surfaceGeometryFailure = "Observed surface does not match requested $Resolution or its byte count/base pointers."
                Stop-LaunchedProcesses -CdbPid $launch.ProcessId -CandidatePath $candidateFull -RunStart $runStart -CdbPath $Cdb
                break
            }
            $currentLogText = if (Test-Path -LiteralPath $logPath) { Get-Content -LiteralPath $logPath -Raw } else { '' }
            # Nonlegacy geometry/map bounds are checked by the generated probe
            # before HOST_READY; READY itself is only an observation marker.
            $probeBoundsReady = ($Resolution -eq '800x600') -or $currentLogText.Contains('SURFDUMP_HOST_READY')
            if ($InitialMapPaintValidation) {
                $probeBoundsReady = $currentLogText.Contains('SURFDUMP_HOST_READY') -and $currentLogText.Contains('PTILE_TRACE_CLOSED')
            }
            if ($currentReady -and $probeBoundsReady -and -not $currentLogText.Contains('SURFDUMP_INVALID') -and -not (Test-Path -LiteralPath $rawPath)) {
                try {
                    $target = Get-LaunchedCandidateProcesses -CandidatePath $candidateFull -RunStart $runStart |
                        Sort-Object StartTime -Descending |
                        Select-Object -First 1
                    if ($target) {
                        Save-ProcessMemory `
                            -ProcessId $target.Id `
                            -BaseAddress (Convert-CdbHexToUInt64 -Value $currentReady.Base) `
                            -ByteCount $currentReady.Bytes `
                            -OutputPath $rawPath
                        $surfaceCaptureSet = @([pscustomobject]@{ Path = $rawPath; Sha256 = (Get-FileSha256 -Path $rawPath); Bytes = $currentReady.Bytes })
                        if ($CompleteHdValidation) {
                            # The complete initial-paint lane is stopped at its
                            # trace-closed boundary. Preserve three consecutive
                            # independent reads for the visual checkpoint.
                            foreach ($captureIndex in @(2, 3)) {
                                $capturePath = Join-Path $runDir "surface-$captureIndex.raw"
                                Save-ProcessMemory -ProcessId $target.Id -BaseAddress (Convert-CdbHexToUInt64 -Value $currentReady.Base) -ByteCount $currentReady.Bytes -OutputPath $capturePath
                                $surfaceCaptureSet += [pscustomobject]@{ Path = $capturePath; Sha256 = (Get-FileSha256 -Path $capturePath); Bytes = $currentReady.Bytes }
                            }
                        }
                        $hostDumpedMemory = $true
                    }
                }
                catch {
                    $hostDumpError = $_.Exception.Message
                }
            }
        }
        $dumpObserved = $false
        if ((Test-Path -LiteralPath $rawPath) -and ((Get-Item -LiteralPath $rawPath).Length -gt 0)) {
            if ($UseCdbWriteMem) {
                $dumpObserved = (Test-Path -LiteralPath $logPath) -and ((Get-Content -LiteralPath $logPath -Raw).Contains('SURFDUMP_DONE'))
            }
            else {
                $dumpObserved = $hostDumpedMemory
            }
        }
        if ($dumpObserved) {
            if ($ContinueAfterDumpSec -le 0) {
                $stoppedAfterDump = $true
                Stop-LaunchedProcesses -CdbPid $launch.ProcessId -CandidatePath $candidateFull -RunStart $runStart -CdbPath $Cdb
                Start-Sleep -Milliseconds 500
                $cdbProcess.Refresh()
                break
            }
            if (-not $postDumpObservationStarted) {
                $postDumpObservationStarted = $true
                $postDumpObservationStart = Get-Date
            }
            elseif (((Get-Date) - $postDumpObservationStart).TotalSeconds -ge $ContinueAfterDumpSec) {
                $postDumpObservationCompleted = $true
                $stoppedAfterDump = $true
                Stop-LaunchedProcesses -CdbPid $launch.ProcessId -CandidatePath $candidateFull -RunStart $runStart -CdbPath $Cdb
                Start-Sleep -Milliseconds 500
                $cdbProcess.Refresh()
                break
            }
        }
    }

    $cdbProcess.Refresh()
    $postDumpExitObserved = $postDumpObservationStarted -and $cdbProcess.HasExited -and (-not $postDumpObservationCompleted)

    if (-not $cdbProcess.HasExited -and -not $stoppedAfterDump) {
        $timedOut = $true
        $runtimeError = "CDB surface dump timed out after $RunSeconds seconds"
        $timeoutStackSaved = Save-TimeoutStack -CdbPath $Cdb -CandidatePath $candidateFull -RunStart $runStart -StackLogPath $timeoutStackLog
    }
    else {
        $cdbProcess.Refresh()
        if ($cdbProcess.HasExited) {
            $cdbExitCode = $cdbProcess.ExitCode
        }
    }
}
catch {
    $runtimeError = $_.Exception.Message
    $runtimeExceptionId = $_.FullyQualifiedErrorId
    $runtimeExceptionStack = $_.ScriptStackTrace
}
finally {
    Restore-SurfaceProxyPresentSetting -Setting $proxyPresentEnvironment
    $launchedCdbId = if ($launch) { $launch.ProcessId } else { $null }
    Stop-LaunchedProcesses -CdbPid $launchedCdbId -CandidatePath $candidateFull -RunStart $runStart -CdbPath $Cdb
    try {
        $cleanupResult = Test-LaunchedProcessesStopped -CdbPid $launchedCdbId -CandidatePath $candidateFull -RunStart $runStart -CdbPath $Cdb
    } catch {
        $cleanupResult = [pscustomobject]@{ Passed = $false; InspectionErrors = @($_.Exception.Message); RemainingProcessIds = @() }
    }
    if (-not $cleanupResult.Passed -and -not $runtimeError) {
        $runtimeError = 'Launched process cleanup could not be verified; see CleanupResult.'
    }
    if ($launch -and $launch.ProcessHandle -ne [IntPtr]::Zero) {
        [ClashSurfaceDumpNative]::CloseHandle($launch.ProcessHandle) | Out-Null
    }
    if ($launch -and $launch.DesktopHandle -ne [IntPtr]::Zero) {
        [ClashSurfaceDumpNative]::CloseDesktop($launch.DesktopHandle) | Out-Null
    }
}

$ready = Parse-SurfaceDumpReady -LogPath $logPath
$logText = if (Test-Path -LiteralPath $logPath) { Get-Content -LiteralPath $logPath -Raw } else { '' }
function Get-PartialTileValidationFailure {
    param([string]$LogText, [string]$Stage, [string]$Resolution, [string]$CandidateSha256,
          [string]$ContractStage = $Stage)
    $contractLine = "PTILE_CONTRACT_PASS stage=$ContractStage resolution=$Resolution candidate_sha256=$($CandidateSha256.ToLowerInvariant())"
    $lines = @($LogText -split "`r?`n")
    $readyLine = "PTILE_MAP_READY owner=0040ad40 size=($($Resolution.Replace('x',',')))"
    $exactContract = @($lines | Where-Object { $_ -ceq $contractLine })
    $allContracts = @($lines | Where-Object { $_ -match '^PTILE_CONTRACT_PASS\b' })
    $allReady = @($lines | Where-Object { $_ -match '^PTILE_MAP_READY\b' })
    if ($exactContract.Count -ne 1 -or $allContracts.Count -ne 1 -or $LogText -match '(?m)^PTILE_(CONTRACT_FAIL|REJECT)\b') {
        return 'partial-tile loaded contract missing, repeated or rejected'
    }
    if ($allReady.Count -ne 1 -or $allReady[0] -cne $readyLine) { return 'native map-owner readiness missing or mismatched' }
    $geometry = [regex]::Match($Resolution, '^(\d{1,4})x(\d{1,4})$')
    if (-not $geometry.Success) { return 'invalid partial-tile resolution' }
    $width = [int]$geometry.Groups[1].Value
    $height = [int]$geometry.Groups[2].Value
    if ($width -lt 96 -or $height -lt 80 -or $width -gt 8192 -or $height -gt 8192) {
        return 'invalid partial-tile resolution'
    }
    $framedStage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation'
    $insetX = 32
    $insetY = 16
    $completeStage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-validation'
    if ($Stage -ceq $framedStage -or $Stage -ceq $completeStage) {
        if ($width -lt 640 -or $height -lt 480 -or $width % 2 -ne 0 -or $height % 2 -ne 0) {
            return 'invalid framed partial-tile resolution'
        }
        $insetX = 64
        $insetY = 32
    } elseif ($Stage -match 'framed') { return 'unknown framed partial-tile stage' }
    $floorCols = [Math]::Floor(($width - $insetX) / 64)
    $floorRows = [Math]::Floor(($height - $insetY) / 64)
    $ceilCols = [Math]::Ceiling(($width - $insetX) / 64)
    $ceilRows = [Math]::Ceiling(($height - $insetY) / 64)
    $hex = '[0-9a-fA-F]{1,8}'
    $integer = '-?\d{1,10}'
    $identityPattern = "tid=(?<tid>$hex) esp=(?<esp>$hex)"
    $worldPattern = "world=\((?<wx>$integer),(?<wy>$integer)\)"
    $inputPattern = "^PTILE_(?:INCREMENTAL_INPUT|NATIVE_NOOP_EXIT) $identityPattern $worldPattern caller=(?<caller>$hex) gd=(?<gd>$hex) map=\((?<mw>$integer),(?<mh>$integer)\) scroll=\((?<sx>$integer),(?<sy>$integer)\) vtable=(?<vtable>$hex)$"
    $guardPattern = "^PTILE_COMPOSITION_GUARD $identityPattern status=(?<status>$integer) $worldPattern cell=\((?<col>$integer),(?<row>$integer)\) present=(?<present>$integer) caller=(?<caller>$hex)$"
    $statusPattern = "^PTILE_STATUS hook=(?<hook>full_converge|full_present|incremental) status=(?<status>$integer) $identityPattern owner=(?<owner>$hex) tile=(?<tile>$hex) post=(?<post>$hex) lower=(?<lower>$hex) player=0$"
    $pending = @{}
    $incremental = @{}
    $presentCount = 0
    $contractObserved = $false
    $mapReady = $false
    foreach ($line in $lines) {
        if ($line -ceq $contractLine) { $contractObserved = $true; continue }
        if ($line -ceq $readyLine) {
            if (-not $contractObserved) { return 'map readiness precedes loaded contract' }
            $mapReady = $true
            continue
        }
        $kind = if ($line -match '^PTILE_COMPOSITION_GUARD') { 'guard' }
            elseif ($line -match '^PTILE_INCREMENTAL_INPUT') { 'input' }
            elseif ($line -match '^PTILE_NATIVE_NOOP_EXIT') { 'exit' }
            elseif ($line -match '^PTILE_STATUS') { 'status' }
            else { '' }
        if (-not $kind) { continue }
        $pattern = if ($kind -eq 'guard') { $guardPattern }
            elseif ($kind -eq 'status') { $statusPattern } else { $inputPattern }
        $match = [regex]::Match($line, $pattern)
        if (-not $mapReady -or -not $match.Success) { return 'malformed or premature partial-tile status' }
        $values = @{}
        foreach ($field in @('tid','esp','caller','gd','vtable','owner','tile','post','lower')) {
            if ($match.Groups[$field].Success) { $values[$field] = [Convert]::ToUInt64($match.Groups[$field].Value,16) }
        }
        foreach ($field in @('wx','wy','mw','mh','sx','sy','col','row','status','present')) {
            if ($match.Groups[$field].Success) {
                $number = [long]$match.Groups[$field].Value
                if ($number -lt -2147483648 -or $number -gt 2147483647) { return 'partial-tile signed value outside x86 range' }
                $values[$field] = $number
            }
        }
        if ($values.tid -eq 0 -or $values.esp -eq 0) {
            return 'invalid partial-tile thread or stack identity'
        }
        # The three observation sites have different real ESPs. Normalize to
        # the original sub_418A90 entry, which still holds the caller address:
        # guard +120, hook status/input +36, native early epilogue +28 bytes.
        $delta = if ($kind -eq 'guard') { 120 } elseif ($kind -eq 'exit') { 28 } else { 36 }
        $nativeSp = $values.esp + $delta
        if ($nativeSp -gt 4294967295) { return 'partial-tile native stack identity overflow' }
        $key = "$($values.tid):$nativeSp"
        foreach ($activeKey in $incremental.Keys) {
            $activeGuard = $incremental[$activeKey].Guard
            $activeOutside = $activeGuard.col -lt 0 -or $activeGuard.col -ge $ceilCols -or
                $activeGuard.row -lt 0 -or $activeGuard.row -ge $ceilRows
            # An offscreen helper and its native fallback have no calls: a
            # different invocation on this thread cannot occur inside them.
            # Visible calls may nest; other threads may interleave normally.
            if ($activeOutside -and $activeGuard.tid -eq $values.tid -and $activeKey -ne $key) {
                return 'offscreen incremental sequence interrupted by another invocation'
            }
        }
        if ($kind -eq 'guard') {
            if ($values.status -ne 1 -or $values.present -ne 1 -or $values.caller -eq 0) {
                return 'incremental composition guard did not approve the actual call'
            }
            if ($incremental.ContainsKey($key)) { return 'repeated or stale incremental guard' }
            $incremental[$key] = @{ Phase='guard'; Guard=$values }
            continue
        }
        if ($kind -eq 'input' -or $kind -eq 'exit') {
            if (-not $incremental.ContainsKey($key)) { return 'incremental input or native exit lacks its guard and invocation' }
            $call = $incremental[$key]
            if ($kind -eq 'exit') {
                if ($call.Phase -ne 'exit') { return 'unexpected or repeated native no-op exit' }
                foreach ($field in @('caller','wx','wy','gd','mw','mh','sx','sy','vtable')) {
                    if ($values[$field] -ne $call.Input[$field]) { return 'native no-op exit changed its input or context' }
                }
                # These are exactly the emitted exit fields. Owner/callback/
                # player were checked at status; unlogged state at exit is
                # not claimed as a separate concurrency or visual proof.
                $incremental.Remove($key)
                # An observed no-op consumes the raw zero-status call; it is
                # never a draw, world-edge clear, or complete presentation.
                continue
            }
            if ($call.Phase -ne 'guard') { return 'repeated or out-of-order incremental input' }
            if ($values.caller -ne $call.Guard.caller -or $values.wx -ne $call.Guard.wx -or $values.wy -ne $call.Guard.wy) {
                return 'incremental input differs from its actual guarded call'
            }
            if ($values.gd -eq 0 -or $values.vtable -eq 0 -or $values.mw -lt 1 -or $values.mw -gt 100 -or
                $values.mh -lt 1 -or $values.mh -gt 100 -or $values.sx -lt 0 -or $values.sy -lt 0 -or
                $values.sx -gt [Math]::Max(0, $values.mw - $floorCols) -or
                $values.sy -gt [Math]::Max(0, $values.mh - $floorRows)) {
                return 'invalid incremental map or scroll context'
            }
            if ($call.Guard.col -ne ($values.wx - $values.sx) -or $call.Guard.row -ne ($values.wy - $values.sy)) {
                return 'actual guarded cell differs from world and scroll coordinates'
            }
            $call.Input = $values
            $call.Phase = 'input'
            continue
        }
        $name = $match.Groups['hook'].Value
        $status = $values.status
        if ($name -eq 'incremental') {
            if ($status -notin @(0,1,2)) { return 'unsupported partial-tile status' }
            if (-not $incremental.ContainsKey($key) -or $incremental[$key].Phase -ne 'input') {
                return 'incremental status lacks a fresh guard and input'
            }
            $call = $incremental[$key]
            $inputRow = $call.Input
            $visible = $call.Guard.col -ge 0 -and $call.Guard.col -lt $ceilCols -and
                $call.Guard.row -ge 0 -and $call.Guard.row -lt $ceilRows
            $inWorld = $inputRow.wx -ge 0 -and $inputRow.wx -lt $inputRow.mw -and $inputRow.wy -ge 0 -and $inputRow.wy -lt $inputRow.mh
            if ($values.owner -ne 0x40AD40 -or $values.post -ne 0 -or $values.lower -ne 0 -or
                $values.tile -notin @(0,0x425120,0x429EC0)) {
                return 'incremental status has unsupported composition context'
            }
            if ($status -eq 0) {
                if ($visible -or -not $inWorld -or $values.tile -ne 0 -or $inputRow.vtable -ne 0x50EE24) {
                    return 'zero status is not a supported native offscreen no-op'
                }
                $call.Phase = 'exit'
            } else {
                if (-not $visible -or ($status -eq 1 -and -not $inWorld) -or ($status -eq 2 -and $inWorld)) {
                    return 'incremental draw or clear status contradicts actual cell bounds'
                }
                $incremental.Remove($key)
            }
            continue
        }
        if ($status -ne 1) { return 'unsupported partial-tile status' }
        $context = @($values.owner, $values.tile, $values.post, $values.lower) -join ':'
        if ($name -eq 'full_converge') { $pending[$key] = $context }
        elseif ($name -eq 'full_present') {
            if (-not $pending.ContainsKey($key) -or $pending[$key] -ne $context) {
                return 'partial presentation lacks preceding convergence on the same thread, stack and owner context'
            }
            $pending.Remove($key)
            $presentCount++
        }
    }
    if ($incremental.Count -ne 0) { return 'unfinished incremental guard, input, status or native-exit sequence' }
    # Native EBP=0 permits convergence without presentation. A successful
    # presentation must still consume a matching preceding convergence row.
    if ($presentCount -eq 0) { return 'no complete partial-tile composition/presentation pair' }
    return $null
}
$partialValidationFailure = if ($PartialTileValidation) {
    Get-PartialTileValidationFailure -LogText $logText -Stage $Stage -Resolution $Resolution -CandidateSha256 $candidateSha -ContractStage $partialContractStage
} else { $null }
$initialPaintTrace = $null
if ($InitialMapPaintValidation) {
    $traceContextArgs = if ($CompleteHdValidation) { @('--candidate-manifest', $candidateManifestPath, '--original', $inputFull) } else { @() }
    $initialTraceJson = & $pythonExe -B $initialTraceTool --log $logPath --probe $ExtraProbeTemplate --resolution $Resolution --candidate-sha256 $candidateSha --stage $Stage @traceContextArgs
    $initialTraceExit = $LASTEXITCODE
    try { $initialPaintTrace = $initialTraceJson | ConvertFrom-Json } catch { $initialPaintTrace = $null }
    if ($initialTraceExit -ne 0 -or -not $initialPaintTrace -or -not $initialPaintTrace.passed) {
        if (-not $partialValidationFailure) { $partialValidationFailure = 'Initial map paint trace failed; see InitialMapPaintTrace.' }
    }
}
$framedMinimap = $null
if ($FramedValidation) {
    $minimapRows = @($logText -split "`r?`n" | Where-Object { $_ -match '^FRAMED_MINIMAP\b' })
    $minimapMatch = if ($minimapRows.Count -eq 1) {
        [regex]::Match($minimapRows[0], '^FRAMED_MINIMAP enabled=([01]) origin=\((\d{1,4}),(\d{1,4})\) size=\((\d{1,4}),(\d{1,4})\)$')
    } else { $null }
    if (-not $minimapMatch -or -not $minimapMatch.Success -or $logText -match '(?m)^FRAMED_CAPTURE_REJECT\b') {
        if (-not $partialValidationFailure) { $partialValidationFailure = 'Framed capture lacks one valid minimap observation.' }
    } else {
        $framedMinimap = [pscustomobject]@{
            Enabled = [int]$minimapMatch.Groups[1].Value
            Left = [int]$minimapMatch.Groups[2].Value
            Top = [int]$minimapMatch.Groups[3].Value
            Width = [int]$minimapMatch.Groups[4].Value
            Height = [int]$minimapMatch.Groups[5].Value
        }
        if ($framedMinimap.Enabled -eq 1 -and
            ($framedMinimap.Width -le 0 -or $framedMinimap.Height -le 0 -or
             $framedMinimap.Left -lt 32 -or $framedMinimap.Top -ne 16 -or
             $framedMinimap.Left + $framedMinimap.Width -ne $surfaceGeometry.width - 32 -or
             $framedMinimap.Top + $framedMinimap.Height -gt $surfaceGeometry.height - 16)) {
            if (-not $partialValidationFailure) { $partialValidationFailure = 'Framed minimap backing violates the observed inner viewport.' }
        }
    }
}
$dumpDone = $logText.Contains('SURFDUMP_DONE')
if ($hostDumpedMemory) {
    $dumpDone = $true
}
$dumpInvalid = $logText.Contains('SURFDUMP_INVALID')
$av = $logText.Contains('AV_SURFDUMP')
$appRequestQuit = $logText.Contains('SURFDUMP_APP_REQUEST_QUIT')
$appRequestQuitLine = @($logText -split "`r?`n" | Where-Object { $_ -match 'SURFDUMP_APP_REQUEST_QUIT' } | Select-Object -First 1)
$rawExists = Test-Path -LiteralPath $rawPath
$rawBytes = if ($rawExists) { (Get-Item -LiteralPath $rawPath).Length } else { 0 }
if ($ready -and -not (Test-RequestedSurfaceReady -Ready $ready -Geometry $surfaceGeometry)) {
    $surfaceGeometryFailure = "Observed surface does not match requested $Resolution or its byte count/base pointers."
}

$runtimeFailure = Get-SurfaceRuntimeFailure -AccessViolation $av -AppRequestQuit $appRequestQuit -RuntimeError $(if ($runtimeError) { $runtimeError } else { $partialValidationFailure })
if (-not $ready -or -not $dumpDone -or -not $rawExists -or $surfaceGeometryFailure -or $dumpInvalid -or $runtimeFailure) {
    $failureReason = if ($runtimeFailure) {
        $runtimeFailure
    }
    elseif ($surfaceGeometryFailure) {
        $surfaceGeometryFailure
    }
    elseif ($dumpInvalid) {
        'generated probe rejected the surface or map/player bounds'
    }
    else {
        'surface dump was not completed'
    }
    $summary = [pscustomobject]@{
        Passed = $false
        PartialTileValidation = [bool]$PartialTileValidation
        InitialMapPaintValidation = [bool]$InitialMapPaintValidation
        FramedValidation = [bool]$FramedValidation
        MinimapViewportValidation = [bool]$MinimapViewportValidation
    CompleteHdValidation = [bool]$CompleteHdValidation
    NoopProgressDiagnostic = [bool]$NoopProgressDiagnostic
    NoopProgressReport = $noopProgressReport
    FullPaintProgressDiagnostic = [bool]$FullPaintProgressDiagnostic
    FullPaintProgressReport = $fullProgressReport
    SurfaceCaptureSet = $surfaceCaptureSet
    RuntimeError = $runtimeError
    RuntimeExceptionId = $runtimeExceptionId
    RuntimeExceptionStack = $runtimeExceptionStack
    CleanupResult = $cleanupResult
    CandidateManifest = $candidateManifestPath
    CandidateManifestSha256 = if ($candidateManifestPath) { Get-FileSha256 -Path $candidateManifestPath } else { $null }
    RecipeRevision = if ($candidateManifest) { $candidateManifest.recipe_revision } else { $null }
    CandidateProbeSha256 = if ($candidateManifest) { $candidateManifest.probe_sha256 } else { $null }
    GeneratedProbeSha256 = Get-FileSha256 -Path $generatedProbe
    PartialContractStage = $partialContractStage
        MinimapObserverReport = $minimapObserverReport
        FramedMinimap = $framedMinimap
        InitialMapPaintTrace = $initialPaintTrace
        PartialTileBuildReport = if ($PartialTileValidation) { $partialBuildReport } else { $null }
        Error = $failureReason
        LaunchMode = $launchMode
        HiddenDesktop = (-not $AllowVisibleDesktop)
        AllowVisibleDesktop = [bool]$AllowVisibleDesktop
        TimedOut = $timedOut
        StoppedAfterDump = $stoppedAfterDump
        ContinueAfterDumpSec = $ContinueAfterDumpSec
        PostDumpObservationStarted = $postDumpObservationStarted
        PostDumpObservationCompleted = $postDumpObservationCompleted
        PostDumpExitObserved = $postDumpExitObserved
        DumpMethod = $dumpMethod
        HostDumpedMemory = $hostDumpedMemory
        HostDumpError = $hostDumpError
        CdbExitCode = $cdbExitCode
        Av = $av
        DumpInvalid = $dumpInvalid
        AppRequestQuit = $appRequestQuit
        AppRequestQuitLine = if ($appRequestQuitLine.Count) { $appRequestQuitLine[0] } else { $null }
        RunDir = $runDir
        Log = $logPath
        CandidateDir = (Get-FullPath -Path $CandidateDir)
        CandidatePath = $candidateFull
        CandidateSha256 = $candidateSha
        LoadSlot = $LoadSlot
        UseDdrawProxy = [bool]$UseDdrawProxy
        ProxyPresentSetting = $proxyPresentEnvironment.Effective
        NoSkipStartAnims = [bool]$NoSkipStartAnims
        FastForwardStartAnims = [bool]$FastForwardStartAnims
        ForceVisibleEdges = [bool]$ForceVisibleEdges
        PostOwnerForceVisibleSeven = [bool]$PostOwnerForceVisibleSeven
        SkipMapValidation = [bool]$SkipMapValidation
        LateLoadSlotForcingOnly = [bool]$LateLoadSlotForcingOnly
        DdrawProxyDll = $proxyDllPath
        DdrawProxySha256 = $proxySha
        DdrawProxyLog = $proxyLogPath
        DdrawProxyManifest = $proxyManifestPath
        ProbeTemplate = (Get-FullPath -Path $ProbeTemplate)
        ExtraProbeTemplate = if ($ExtraProbeTemplate) { Get-FullPath -Path $ExtraProbeTemplate } else { $null }
        GeneratedProbe = $generatedProbe
        Stage = $Stage
        Resolution = $Resolution
        SurfaceGeometry = $surfaceGeometry
        SurfaceGeometryMatched = (Test-RequestedSurfaceReady -Ready $ready -Geometry $surfaceGeometry)
        BaseProbeSha256 = $probeRecipe.base_probe_sha256
        ExtraProbeSourceSha256 = $probeRecipe.extra_probe_sha256
        Ready = $ready
        RawExists = $rawExists
        RawBytes = $rawBytes
        TimeoutStackLog = if ($timeoutStackSaved) { $timeoutStackLog } else { $null }
    }
    $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryJson -Encoding ASCII
    @(
        '# CDB Surface Dump Run'
        ''
        '- Passed: false'
        "- Error: $failureReason"
        "- Resolution: $Resolution"
        "- Launch mode: $launchMode"
        "- Timed out: $timedOut"
        "- Stopped after dump: $stoppedAfterDump"
        "- Continue after dump seconds: $ContinueAfterDumpSec"
        "- Post-dump observation started: $postDumpObservationStarted"
        "- Post-dump observation completed: $postDumpObservationCompleted"
        "- Post-dump exit observed: $postDumpExitObserved"
        "- Dump method: $dumpMethod"
        "- Host dumped memory: $hostDumpedMemory"
        "- Host dump error: $(if ($hostDumpError) { $hostDumpError } else { 'not observed' })"
        "- CDB exit code: $cdbExitCode"
        "- AV: $av"
        "- Dump invalid: $dumpInvalid"
        "- App_RequestQuit: $appRequestQuit"
        "- App_RequestQuit line: $(if ($appRequestQuitLine.Count) { $appRequestQuitLine[0] } else { 'not observed' })"
        "- DirectDraw proxy: $([bool]$UseDdrawProxy)"
        "- No skip start animations: $([bool]$NoSkipStartAnims)"
        "- Fast-forward start animations: $([bool]$FastForwardStartAnims)"
    "- Force visible edges: $([bool]$ForceVisibleEdges)"
    "- Post-owner force visible seven: $([bool]$PostOwnerForceVisibleSeven)"
    "- Map validation skipped: $([bool]$SkipMapValidation)"
    "- Late load-slot forcing only: $([bool]$LateLoadSlotForcingOnly)"
    "- DirectDraw proxy DLL: $(if ($proxyDllPath) { $proxyDllPath } else { 'not used' })"
        "- DirectDraw proxy log: $(if ($proxyLogPath) { $proxyLogPath } else { 'not used' })"
        "- Generated probe: $generatedProbe"
        "- Log: $logPath"
        "- Timeout stack: $(if ($timeoutStackSaved) { $timeoutStackLog } else { 'not captured' })"
    ) | Set-Content -LiteralPath $runSummary -Encoding ASCII
    throw "Surface dump failed. See $runSummary"
}

function Write-SurfacePostprocessingFailure {
    param([string]$SummaryPath, [string]$MarkdownPath, [hashtable]$Context,
          [string]$FailureMessage, [string]$FailureId, [string]$FailureStack)
    # Preserve any earlier summary/failure verbatim. Exclusive creation also
    # refuses a racing writer; no original evidence is replaced on error.
    if (Test-Path -LiteralPath $SummaryPath) { return }
    $record = $Context.Clone()
    $record.Passed = $false
    $record.FailurePhase = 'postprocessing'
    $record.Error = $FailureMessage
    $record.ExceptionId = $FailureId
    $record.ExceptionStack = $FailureStack
    $record.ManualInputProof = $false
    $record.PromotionReady = $false
    $json = $record | ConvertTo-Json -Depth 12
    $stream = [System.IO.File]::Open($SummaryPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write)
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($json + "`n")
        $stream.Write($bytes, 0, $bytes.Length)
    } finally { $stream.Dispose() }
    if (-not (Test-Path -LiteralPath $MarkdownPath)) {
        $text = "# CDB Surface Dump Run`n`n- Passed: false`n- Failure phase: postprocessing`n- Error: $FailureMessage`n- Stage: $($record.Stage)`n- Resolution: $($record.Resolution)`n- Candidate SHA-256: $($record.CandidateSha256)`n- Summary: $SummaryPath`n"
        $stream = [System.IO.File]::Open($MarkdownPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write)
        try {
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($text)
            $stream.Write($bytes, 0, $bytes.Length)
        } finally { $stream.Dispose() }
    }
}

$convertExit = $null
$coverageExit = $null
$visibilityExit = $null
$coverageReport = $null
$visibilityReport = $null
$visibilityFailure = $null
$forceVisibleFailure = $null
$postOwnerForcedVisibleFailure = $null
try {
if ($rawBytes -lt $ready.Bytes) {
    throw "Surface dump is shorter than expected: expected $($ready.Bytes), found $rawBytes"
}

$convertArgs = @($converter, $rawPath, '--width', $ready.Width, '--height', $ready.Height, '--output', $pngPath, '--metadata', $pngMetaPath, '--log', $logPath)
if ($proxyPalettePath -and (Test-Path -LiteralPath $proxyPalettePath -PathType Leaf)) {
    $convertArgs += @('--palette', $proxyPalettePath)
}
& $pythonExe @convertArgs
$convertExit = $LASTEXITCODE
if ($convertExit -ne 0) {
    throw "cdb_surface_dump_to_png.py failed with exit code $convertExit"
}

$pngMeta = Get-Content -LiteralPath $pngMetaPath -Raw | ConvertFrom-Json
$coverageReport = $null
$coverageImage = $null
$coverageExit = $null
$blankActiveCells = @()
$visibilityRequiresExplained = $false
$visibilityExit = $null
$visibilityReport = $null
$visibilityUnexplained = @()
$visibilityFailure = $null
$forceVisibleStillBlank = @()
$forceVisibleFailure = $null
$forcedVisibleReport = $null
$forcedVisibleExit = $null
$postOwnerForcedVisibleReport = $null
$postOwnerForcedVisibleExit = $null
$postOwnerForcedVisibleFailure = $null

if ($SkipMapValidation) {
    @(
        'map_tile_coverage.py skipped by -SkipMapValidation'
        'Use this only for non-map UI surfaces where gameplay tile coverage is the wrong validator.'
    ) | Set-Content -LiteralPath $coverageText -Encoding UTF8
    @(
        'visibility_coverage.py skipped by -SkipMapValidation'
        'No gameplay tile visibility gate was run for this surface.'
    ) | Set-Content -LiteralPath $visibilityText -Encoding UTF8
}
else {
    $coverageArgs = @($coverageTool, $pngPath, '--logical-width', $ready.Width, '--logical-height', $ready.Height, '--write-json', $coverageJson)
    if ($FramedValidation) {
        $coverageArgs += @('--stage', $Stage, '--minimap-enabled', $framedMinimap.Enabled)
        if ($CompleteHdValidation) {
            $coverageArgs += @('--candidate-manifest', $candidateManifestPath, '--original', $inputFull)
        }
        if ($framedMinimap.Enabled -eq 1) {
            $coverageArgs += @('--minimap-width', $framedMinimap.Width, '--minimap-height', $framedMinimap.Height)
        }
    } else {
        $coverageArgs += @('--columns', $surfaceGeometry.columns, '--rows', $surfaceGeometry.rows, '--bottom-row-active-cols', $surfaceGeometry.columns)
    }
    if ($RequireGameplay) {
        $coverageArgs += '--require-gameplay'
    }
    $coverageOutput = & $pythonExe @coverageArgs 2>&1
    $coverageExit = $LASTEXITCODE
    $coverageOutput | Set-Content -LiteralPath $coverageText -Encoding UTF8
    if ($coverageExit -ne 0) {
        throw "map_tile_coverage.py failed with exit code $coverageExit. See $coverageText"
    }
    $coverageReport = Get-Content -LiteralPath $coverageJson -Raw | ConvertFrom-Json
    $coverageImage = @($coverageReport.images | Select-Object -First 1)
    if ($coverageImage -and $coverageImage.summary -and $coverageImage.summary.blank_active_cells) {
        $blankActiveCells = @($coverageImage.summary.blank_active_cells)
    }

    $visibilityRequiresExplained = ((-not $ForceVisibleEdges) -and ($blankActiveCells.Count -gt 0))
    $visibilityArgs = @($visibilityTool, $coverageJson, '--log', $logPath, '--write-json', $visibilityJson)
    if ($visibilityRequiresExplained) {
        $visibilityArgs += '--require-explained'
    }
    $visibilityOutput = & $pythonExe @visibilityArgs 2>&1
    $visibilityExit = $LASTEXITCODE
    $visibilityOutput | Set-Content -LiteralPath $visibilityText -Encoding UTF8
    if (($visibilityExit -ne 0) -and (-not $visibilityRequiresExplained)) {
        throw "visibility_coverage.py failed with exit code $visibilityExit. See $visibilityText"
    }
    if (-not (Test-Path -LiteralPath $visibilityJson)) {
        throw "visibility_coverage.py did not write $visibilityJson. See $visibilityText"
    }

    $visibilityReport = Get-Content -LiteralPath $visibilityJson -Raw | ConvertFrom-Json
    $visibilityUnexplained = @($visibilityReport.unexplained_blank_cells)
    if ($visibilityRequiresExplained -and (($visibilityExit -ne 0) -or ($visibilityUnexplained.Count -gt 0))) {
        $visibilityFailure = "Visibility explained gate failed: unexplained blank active cells=$($visibilityUnexplained -join ', '). See $visibilityText"
    }

    if ($ForceVisibleEdges) {
        $forcedVisibleOutput = & $pythonExe $forcedVisibleTool $coverageJson --log $logPath --write-json $forcedVisibleJson --expect-vedge-visret $surfaceGeometry.expected_vedge_count --expect-vedge-post $surfaceGeometry.expected_vedge_count --require-forced-visible 2>&1
        $forcedVisibleExit = $LASTEXITCODE
        $forcedVisibleOutput | Set-Content -LiteralPath $forcedVisibleText -Encoding UTF8
        if (Test-Path -LiteralPath $forcedVisibleJson) {
            $forcedVisibleReport = Get-Content -LiteralPath $forcedVisibleJson -Raw | ConvertFrom-Json
            if ($forcedVisibleReport.blank_active_cells) {
                $forceVisibleStillBlank = @($forcedVisibleReport.blank_active_cells)
            }
        }
        if ($forcedVisibleExit -ne 0) {
            $gateFailures = @()
            if ($forcedVisibleReport -and $forcedVisibleReport.failures) {
                $gateFailures = @($forcedVisibleReport.failures)
            }
            $forceVisibleFailure = if ($gateFailures.Count) {
                "ForceVisibleEdges proof gate failed: $($gateFailures -join '; '). See $forcedVisibleText"
            }
            else {
                "ForceVisibleEdges proof gate failed with exit code $forcedVisibleExit. See $forcedVisibleText"
            }
        }
    }
    if ($PostOwnerForceVisibleSeven) {
        $postOwnerForcedVisibleOutput = & $pythonExe $postOwnerForcedVisibleTool $coverageJson --log $logPath --write-json $postOwnerForcedVisibleJson --require-post-owner-forced-visible 2>&1
        $postOwnerForcedVisibleExit = $LASTEXITCODE
        $postOwnerForcedVisibleOutput | Set-Content -LiteralPath $postOwnerForcedVisibleText -Encoding UTF8
        if (Test-Path -LiteralPath $postOwnerForcedVisibleJson) {
            $postOwnerForcedVisibleReport = Get-Content -LiteralPath $postOwnerForcedVisibleJson -Raw | ConvertFrom-Json
        }
        if ($postOwnerForcedVisibleExit -ne 0) {
            $gateFailures = @()
            if ($postOwnerForcedVisibleReport -and $postOwnerForcedVisibleReport.failures) {
                $gateFailures = @($postOwnerForcedVisibleReport.failures)
            }
            $postOwnerForcedVisibleFailure = if ($gateFailures.Count) {
                "PostOwnerForceVisibleSeven proof gate failed: $($gateFailures -join '; '). See $postOwnerForcedVisibleText"
            }
            else {
                "PostOwnerForceVisibleSeven proof gate failed with exit code $postOwnerForcedVisibleExit. See $postOwnerForcedVisibleText"
            }
        }
    }
}
$visibilityStatusPairs = @()
if ($visibilityReport -and $visibilityReport.status_counts) {
    $visibilityStatusPairs = @(
        $visibilityReport.status_counts.PSObject.Properties |
            Sort-Object Name |
            ForEach-Object { "$($_.Name)=$($_.Value)" }
    )
}
$postDumpObservationFailure = if ($ContinueAfterDumpSec -gt 0 -and $timedOut) {
    "post-dump observation did not complete within the overall $RunSeconds-second run limit"
}
elseif ($ContinueAfterDumpSec -gt 0 -and $postDumpExitObserved) {
    "CDB or target exited during post-dump crash logging with code $cdbExitCode"
}
else {
    $null
}
$validationFailure = if ($postDumpObservationFailure) {
    $postDumpObservationFailure
}
elseif ($postOwnerForcedVisibleFailure) {
    $postOwnerForcedVisibleFailure
}
elseif ($forceVisibleFailure) {
    $forceVisibleFailure
}
elseif ($visibilityFailure) {
    $visibilityFailure
}
else {
    $null
}
$visibilityExplainedGate = [pscustomobject]@{
    Required = [bool]$visibilityRequiresExplained
    Passed = ($null -eq $visibilityFailure)
    Skipped = [bool]$SkipMapValidation
    ExitCode = $visibilityExit
    BlankActiveCells = $blankActiveCells
    UnexplainedBlankCells = $visibilityUnexplained
}
$summaryObject = [pscustomobject]@{
    Passed = ($null -eq $validationFailure)
    PartialTileValidation = [bool]$PartialTileValidation
    InitialMapPaintValidation = [bool]$InitialMapPaintValidation
    FramedValidation = [bool]$FramedValidation
    MinimapViewportValidation = [bool]$MinimapViewportValidation
    CompleteHdValidation = [bool]$CompleteHdValidation
    NoopProgressDiagnostic = [bool]$NoopProgressDiagnostic
    NoopProgressReport = $noopProgressReport
    FullPaintProgressDiagnostic = [bool]$FullPaintProgressDiagnostic
    FullPaintProgressReport = $fullProgressReport
    SurfaceCaptureSet = $surfaceCaptureSet
    RuntimeError = $runtimeError
    RuntimeExceptionId = $runtimeExceptionId
    RuntimeExceptionStack = $runtimeExceptionStack
    CleanupResult = $cleanupResult
    CandidateManifest = $candidateManifestPath
    CandidateManifestSha256 = if ($candidateManifestPath) { Get-FileSha256 -Path $candidateManifestPath } else { $null }
    RecipeRevision = if ($candidateManifest) { $candidateManifest.recipe_revision } else { $null }
    CandidateProbeSha256 = if ($candidateManifest) { $candidateManifest.probe_sha256 } else { $null }
    GeneratedProbeSha256 = Get-FileSha256 -Path $generatedProbe
    PartialContractStage = $partialContractStage
    MinimapObserverReport = $minimapObserverReport
    FramedMinimap = $framedMinimap
    InitialMapPaintTrace = $initialPaintTrace
    PartialTileBuildReport = if ($PartialTileValidation) { $partialBuildReport } else { $null }
    PartialTileStatusGatePassed = if ($PartialTileValidation) { $null -eq $partialValidationFailure } else { $null }
    Error = $validationFailure
    LaunchMode = $launchMode
    HiddenDesktop = (-not $AllowVisibleDesktop)
    AllowVisibleDesktop = [bool]$AllowVisibleDesktop
    DesktopName = $launch.DesktopName
    RunDir = $runDir
    Stage = $Stage
    Resolution = $Resolution
    SurfaceGeometry = $surfaceGeometry
    SurfaceGeometryMatched = (Test-RequestedSurfaceReady -Ready $ready -Geometry $surfaceGeometry)
    BaseProbeSha256 = $probeRecipe.base_probe_sha256
    ExtraProbeSourceSha256 = $probeRecipe.extra_probe_sha256
    InputExe = $inputFull
    InputSha256 = $inputSha
    CandidatePath = $candidateFull
    CandidateDir = (Get-FullPath -Path $CandidateDir)
    CandidateSha256 = $candidateSha
    LoadSlot = $LoadSlot
    UseDdrawProxy = [bool]$UseDdrawProxy
    ProxyPresentSetting = $proxyPresentEnvironment.Effective
    NoSkipStartAnims = [bool]$NoSkipStartAnims
    FastForwardStartAnims = [bool]$FastForwardStartAnims
    ForceVisibleEdges = [bool]$ForceVisibleEdges
    PostOwnerForceVisibleSeven = [bool]$PostOwnerForceVisibleSeven
    SkipMapValidation = [bool]$SkipMapValidation
    LateLoadSlotForcingOnly = [bool]$LateLoadSlotForcingOnly
    DdrawProxyDll = $proxyDllPath
    DdrawProxySha256 = $proxySha
    DdrawProxyLog = $proxyLogPath
    DdrawProxyPalette = $proxyPalettePath
    DdrawProxyManifest = $proxyManifestPath
    Cdb = (Get-FullPath -Path $Cdb)
    CdbExitCode = $cdbExitCode
    TimedOut = $timedOut
    StoppedAfterDump = $stoppedAfterDump
    ContinueAfterDumpSec = $ContinueAfterDumpSec
    PostDumpObservationStarted = $postDumpObservationStarted
    PostDumpObservationCompleted = $postDumpObservationCompleted
    PostDumpExitObserved = $postDumpExitObserved
    Av = $av
    AppRequestQuit = $appRequestQuit
    AppRequestQuitLine = if ($appRequestQuitLine.Count) { $appRequestQuitLine[0] } else { $null }
    DumpMethod = $dumpMethod
    HostDumpedMemory = $hostDumpedMemory
    HostDumpError = $hostDumpError
    ProbeTemplate = (Get-FullPath -Path $ProbeTemplate)
    ExtraProbeTemplate = if ($ExtraProbeTemplate) { Get-FullPath -Path $ExtraProbeTemplate } else { $null }
    GeneratedProbe = $generatedProbe
    Log = $logPath
    Surface = $ready
    RawPath = $rawPath
    RawBytes = $rawBytes
    PngPath = $pngPath
    PngSha256 = $pngMeta.png_sha256
    PngMetadata = $pngMetaPath
    PngPaletteMode = $pngMeta.palette_mode
    CoverageJson = $coverageJson
    CoverageExitCode = $coverageExit
    ConverterExitCode = $convertExit
    CoverageText = $coverageText
    CoverageBlankActiveCells = $blankActiveCells
    VisibilityJson = $visibilityJson
    VisibilityText = $visibilityText
    VisibilityExitCode = $visibilityExit
    VisibilityRequireExplained = [bool]$visibilityRequiresExplained
    VisibilityUnexplainedBlankCells = $visibilityUnexplained
    VisibilityStatusCounts = if ($visibilityReport) { $visibilityReport.status_counts } else { $null }
    VisibilityExplainedGate = $visibilityExplainedGate
    ForcedVisibleJson = if ($ForceVisibleEdges -and -not $SkipMapValidation) { $forcedVisibleJson } else { $null }
    ForcedVisibleText = if ($ForceVisibleEdges -and -not $SkipMapValidation) { $forcedVisibleText } else { $null }
    ForcedVisibleExitCode = $forcedVisibleExit
    ForcedVisibleGate = $forcedVisibleReport
    ForceVisibleStillBlankCells = $forceVisibleStillBlank
    PostOwnerForcedVisibleJson = if ($PostOwnerForceVisibleSeven -and -not $SkipMapValidation) { $postOwnerForcedVisibleJson } else { $null }
    PostOwnerForcedVisibleText = if ($PostOwnerForceVisibleSeven -and -not $SkipMapValidation) { $postOwnerForcedVisibleText } else { $null }
    PostOwnerForcedVisibleExitCode = $postOwnerForcedVisibleExit
    PostOwnerForcedVisibleGate = $postOwnerForcedVisibleReport
}
$summaryObject | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryJson -Encoding ASCII

@(
    '# CDB Surface Dump Run'
    ''
    "- Passed: $($null -eq $validationFailure)"
    "- Error: $(if ($validationFailure) { $validationFailure } else { 'not observed' })"
    "- Launch mode: $launchMode"
    "- Hidden desktop: $(-not $AllowVisibleDesktop)"
    "- Stopped after dump: $stoppedAfterDump"
    "- Continue after dump seconds: $ContinueAfterDumpSec"
    "- Post-dump observation started: $postDumpObservationStarted"
    "- Post-dump observation completed: $postDumpObservationCompleted"
    "- Post-dump exit observed: $postDumpExitObserved"
    "- AV: $av"
    "- App_RequestQuit: $appRequestQuit"
    "- Dump method: $dumpMethod"
    "- Host dumped memory: $hostDumpedMemory"
    "- Stage: $Stage"
    "- Resolution: $Resolution"
    "- Candidate: $candidateFull"
    "- Candidate SHA-256: $candidateSha"
    "- Load slot: $LoadSlot"
    "- DirectDraw proxy: $([bool]$UseDdrawProxy)"
    "- No skip start animations: $([bool]$NoSkipStartAnims)"
    "- Fast-forward start animations: $([bool]$FastForwardStartAnims)"
    "- Force visible edges: $([bool]$ForceVisibleEdges)"
    "- Post-owner force visible seven: $([bool]$PostOwnerForceVisibleSeven)"
    "- Map validation skipped: $([bool]$SkipMapValidation)"
    "- Late load-slot forcing only: $([bool]$LateLoadSlotForcingOnly)"
    "- Extra probe template: $(if ($ExtraProbeTemplate) { Get-FullPath -Path $ExtraProbeTemplate } else { 'not used' })"
    "- DirectDraw proxy DLL: $(if ($proxyDllPath) { $proxyDllPath } else { 'not used' })"
    "- DirectDraw proxy log: $(if ($proxyLogPath) { $proxyLogPath } else { 'not used' })"
    "- DirectDraw proxy palette: $(if ($proxyPalettePath -and (Test-Path -LiteralPath $proxyPalettePath -PathType Leaf)) { $proxyPalettePath } else { 'not captured' })"
    "- Surface: $($ready.Width)x$($ready.Height), base=$($ready.Base), bytes=$($ready.Bytes)"
    "- Raw: $rawPath"
    "- PNG: $pngPath"
    "- PNG palette mode: $($pngMeta.palette_mode)"
    "- Coverage JSON: $coverageJson"
    "- Coverage blank active cells: $(if ($blankActiveCells.Count) { $blankActiveCells -join ', ' } else { 'none' })"
    "- Visibility JSON: $visibilityJson"
    "- Visibility require explained: $([bool]$visibilityRequiresExplained)"
    "- Visibility explained gate: $(if ($visibilityRequiresExplained) { if ($null -eq $visibilityFailure) { 'passed' } else { "failed exit=$visibilityExit" } } else { 'not required' })"
    "- Visibility unexplained blanks: $(if ($visibilityUnexplained.Count) { $visibilityUnexplained -join ', ' } else { 'none' })"
    "- Visibility status counts: $(if ($visibilityStatusPairs.Count) { $visibilityStatusPairs -join ', ' } else { 'none' })"
    "- Forced-visible gate: $(if ($ForceVisibleEdges -and -not $SkipMapValidation) { if ($forcedVisibleExit -eq 0) { 'passed' } else { "failed exit=$forcedVisibleExit" } } elseif ($ForceVisibleEdges) { 'skipped by -SkipMapValidation' } else { 'not used' })"
    "- Forced-visible JSON: $(if ($ForceVisibleEdges -and -not $SkipMapValidation) { $forcedVisibleJson } else { 'not used' })"
    "- Post-owner forced-visible gate: $(if ($PostOwnerForceVisibleSeven -and -not $SkipMapValidation) { if ($postOwnerForcedVisibleExit -eq 0) { 'passed' } else { "failed exit=$postOwnerForcedVisibleExit" } } elseif ($PostOwnerForceVisibleSeven) { 'skipped by -SkipMapValidation' } else { 'not used' })"
    "- Post-owner forced-visible JSON: $(if ($PostOwnerForceVisibleSeven -and -not $SkipMapValidation) { $postOwnerForcedVisibleJson } else { 'not used' })"
    "- Log: $logPath"
    ''
    "![surface dump]($pngPath)"
) | Set-Content -LiteralPath $runSummary -Encoding ASCII

if ($forceVisibleFailure) {
    throw "Surface dump failed ForceVisibleEdges validation. See $runSummary"
}
if ($postOwnerForcedVisibleFailure) {
    throw "Surface dump failed PostOwnerForceVisibleSeven validation. See $runSummary"
}
if ($visibilityFailure) {
    throw "Surface dump failed visibility explanation validation. See $runSummary"
}

if ($validationFailure) {
    throw "Surface dump failed validation: $validationFailure. See $runSummary"
}
Write-Host "CDB surface dump passed: $runDir"
Write-Host "PNG: $pngPath"
Write-Host "Summary: $runSummary"

} catch {
    $postprocessingError = $_
    $failureContext = @{
        Stage = $Stage
        Resolution = $Resolution
        CandidatePath = $candidateFull
        CandidateSha256 = $candidateSha
        InputExe = $inputFull
        InputSha256 = $inputSha
        CandidateManifest = $candidateManifestPath
        RecipeRevision = if ($candidateManifest) { $candidateManifest.recipe_revision } else { $null }
        CandidateProbeSha256 = if ($candidateManifest) { $candidateManifest.probe_sha256 } else { $null }
        PartialContractStage = $partialContractStage
        CompleteHdValidation = [bool]$CompleteHdValidation
    NoopProgressDiagnostic = [bool]$NoopProgressDiagnostic
    NoopProgressReport = $noopProgressReport
    FullPaintProgressDiagnostic = [bool]$FullPaintProgressDiagnostic
    FullPaintProgressReport = $fullProgressReport
    SurfaceCaptureSet = $surfaceCaptureSet
    RuntimeError = $runtimeError
    RuntimeExceptionId = $runtimeExceptionId
    RuntimeExceptionStack = $runtimeExceptionStack
    CleanupResult = $cleanupResult
        LaunchMode = $launchMode
        HiddenDesktop = (-not $AllowVisibleDesktop)
        DumpMethod = $dumpMethod
        RunDir = $runDir
        Log = $logPath
        RawPath = $rawPath
        RawBytes = $rawBytes
        PngPath = $pngPath
        PngMetadata = $pngMetaPath
        GeneratedProbe = $generatedProbe
        ExtraProbeTemplate = $ExtraProbeTemplate
        SurfaceGeometry = $surfaceGeometry
        Ready = $ready
        InitialMapPaintTrace = $initialPaintTrace
        PartialTileValidationFailure = $partialValidationFailure
        FramedMinimap = $framedMinimap
        MinimapObserverReport = $minimapObserverReport
        ConverterExitCode = $convertExit
        CoverageExitCode = $coverageExit
        CoverageJson = $coverageJson
        CoverageText = $coverageText
        VisibilityExitCode = $visibilityExit
        VisibilityJson = $visibilityJson
        VisibilityText = $visibilityText
        VisibilityFailure = $visibilityFailure
        ForceVisibleFailure = $forceVisibleFailure
        PostOwnerForcedVisibleFailure = $postOwnerForcedVisibleFailure
        TimedOut = $timedOut
        StoppedAfterDump = $stoppedAfterDump
        CdbExitCode = $cdbExitCode
        HostDumpError = $hostDumpError
        Av = $av
        AppRequestQuit = $appRequestQuit
    }
    Write-SurfacePostprocessingFailure -SummaryPath $summaryJson -MarkdownPath $runSummary -Context $failureContext -FailureMessage $postprocessingError.Exception.Message -FailureId $postprocessingError.FullyQualifiedErrorId -FailureStack $postprocessingError.ScriptStackTrace
    throw $postprocessingError
}
