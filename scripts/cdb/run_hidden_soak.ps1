# run_hidden_soak.ps1 - hidden-CDB host soak runner (environment=hidden_cdb_host).
#
# APPROVED PROOF CLASS (user ruling 2026-07-27, memory no-popup-windows.md):
# a hidden-desktop CDB soak is a THIRD additive evidence variant next to the
# host visible-runtime soak and the QEMU-Win98 guest soak. Its honesty contract:
#   - input_responsiveness is ALWAYS the sentinel "not_applicable_hidden";
#     it is never faked with a number and never silently dropped.
#   - ALL host process metrics (working set, private memory, handles,
#     exit/clean-stop) STAY REQUIRED - the game is a real host process.
#   - frame/render metrics come from REAL periodic ReadProcessMemory surface
#     reads of the base printed by SOAK_SURFDUMP_READY / SURFDUMP_READY.
#   - every report is labeled environment=hidden_cdb_host.
#   - forced-entry mechanics (breakpoint-forced loader map entry, forced scroll
#     writes for map-pan) are DISCLOSED in the report, never hidden.
# Fail closed on: no ready row, surface read failures, AV rows, game or CDB
# exit before the duration, missing route end. No visible desktop fallback
# exists in this script at all.

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('map-idle', 'map-pan')]
    [string]$Route,
    [ValidateRange(60, 28800)]
    [int]$DurationSec = 7200,
    [ValidateRange(1, 600)]
    [int]$FrameIntervalSec = 30,
    [ValidateRange(1, 600)]
    [int]$PanIntervalSec = 10,
    [string]$InputExe = 'C:\Clash\clash95.exe',
    [string]$WorkDir = 'C:\Clash',
    [string]$Cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe',
    [string]$Python = 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [string]$Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch',
    [string]$CandidateDir = 'C:\ClashTests\hd-soak\hidden',
    [string]$CandidateName = '',
    [string]$OutDir = 'C:\ClashCaptures\hd-soak\hidden',
    [string]$ProbeTemplate = '',
    [string]$SoakProbeTemplate = '',
    [string]$DdrawProxyBuildScript = '',
    [ValidateRange(0, 9)]
    [int]$LoadSlot = 2,
    [ValidateRange(1, 16)]
    [int]$PngEdgeCount = 3,
    [ValidateRange(60, 900)]
    [int]$ReadyTimeoutSec = 240,
    [ValidateRange(30, 900)]
    [int]$EndGraceSec = 180,
    [int]$MaxArtifactMB = 250,
    [int]$MaxWorkingSetGrowthMB = 64,
    [int]$MaxPrivateMemoryGrowthMB = 64,
    [int]$MaxHandleGrowth = 128,
    [string]$ReportJson = '',
    [string]$ReportMarkdown = '',
    [string]$GuardJson = '',
    [string]$GuardMarkdown = '',
    # Compatibility-only: executed runs now always require both report and
    # shared guard success, whether or not this switch is supplied.
    [switch]$RequirePass,
    [switch]$Json,
    [switch]$Execute
)

$ErrorActionPreference = 'Stop'
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
if (-not $ProbeTemplate) { $ProbeTemplate = Join-Path $RepoRoot 'probes\cdb\render\clash95_surface_dump_probe.cdb' }
if (-not $SoakProbeTemplate) { $SoakProbeTemplate = Join-Path $RepoRoot 'probes\cdb\soak\clash95_hidden_soak_route_extra.cdb' }
if (-not $DdrawProxyBuildScript) { $DdrawProxyBuildScript = Join-Path $RepoRoot 'scripts\build\build_ddraw_surfdump_proxy.ps1' }
$ExpectedInputExe = 'C:\Clash\clash95.exe'
$ExpectedBaseSha256 = '500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE'
$ProtectedStableStage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch'
$ExpectedWorkDir = 'C:\Clash'
$ExpectedCdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe'
$ExpectedCandidateRoot = 'C:\ClashTests\hd-soak\hidden'
$ExpectedOutputRoot = 'C:\ClashCaptures\hd-soak\hidden'

function Get-FullPath {
    param([string]$Path)
    [System.IO.Path]::GetFullPath($Path)
}

function Get-FileSha256 {
    param([string]$Path)
    # Python-launched Windows PowerShell can inherit an incompatible PS7
    # module path. Hash without relying on Get-FileHash module autoload.
    $stream = [System.IO.File]::OpenRead($Path)
    $hasher = $null
    try {
        $hasher = [System.Security.Cryptography.SHA256]::Create()
        return [System.BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-', '')
    }
    finally {
        if ($hasher) { $hasher.Dispose() }
        $stream.Dispose()
    }
}

function Test-PathEqual {
    param([string]$Left, [string]$Right)
    [string]::Equals(
        (Get-FullPath -Path $Left).TrimEnd('\'),
        (Get-FullPath -Path $Right).TrimEnd('\'),
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Get-PeMachine {
    param([string]$Path)
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
        $reader = New-Object System.IO.BinaryReader($stream)
        try {
            if ($reader.ReadUInt16() -ne 0x5A4D) {
                throw "PE file has no MZ signature: $Path"
            }
            $stream.Position = 0x3C
            $peOffset = $reader.ReadUInt32()
            if ($peOffset -gt ($stream.Length - 6)) {
                throw "PE header offset is outside the file: $Path"
            }
            $stream.Position = $peOffset
            if ($reader.ReadUInt32() -ne 0x00004550) {
                throw "PE file has no PE signature: $Path"
            }
            return $reader.ReadUInt16()
        }
        finally {
            $reader.Dispose()
        }
    }
    finally {
        $stream.Dispose()
    }
}

if ($FrameIntervalSec -ge $DurationSec) {
    throw "-FrameIntervalSec ($FrameIntervalSec) must be smaller than -DurationSec ($DurationSec)"
}
if ($Route -eq 'map-pan' -and $PanIntervalSec -ge $DurationSec) {
    throw "-PanIntervalSec ($PanIntervalSec) must be smaller than -DurationSec ($DurationSec) for map-pan"
}

# Everything through this boundary is read-only.  In particular, keep Add-Type,
# directory creation, patching, proxy compilation, probe generation, and process
# launch below the explicit -Execute gate.
foreach ($path in @($InputExe, $WorkDir, $Cdb, $ProbeTemplate, $SoakProbeTemplate, $DdrawProxyBuildScript)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required preflight path was not found: $path"
    }
}
if (-not (Test-PathEqual -Left $InputExe -Right $ExpectedInputExe)) {
    throw "-InputExe must be the canonical original path $ExpectedInputExe"
}
if (-not (Test-PathEqual -Left $WorkDir -Right $ExpectedWorkDir)) {
    throw "-WorkDir must be the canonical game work directory $ExpectedWorkDir"
}
if (-not (Test-PathEqual -Left $Cdb -Right $ExpectedCdb)) {
    throw "-Cdb must be the canonical x86 debugger $ExpectedCdb"
}
if ((Get-PeMachine -Path $Cdb) -ne 0x014C) {
    throw "The configured debugger is not an x86 PE executable: $Cdb"
}
if ($Stage -ne $ProtectedStableStage) {
    throw "-Stage must exactly match the protected stable stage: $ProtectedStableStage"
}
if (-not (Test-PathEqual -Left $CandidateDir -Right $ExpectedCandidateRoot)) {
    throw "-CandidateDir must be the canonical external root $ExpectedCandidateRoot"
}
if (-not (Test-PathEqual -Left $OutDir -Right $ExpectedOutputRoot)) {
    throw "-OutDir must be the canonical external root $ExpectedOutputRoot"
}
foreach ($externalParent in @('C:\ClashTests', 'C:\ClashCaptures')) {
    if (-not (Test-Path -LiteralPath $externalParent -PathType Container)) {
        throw "Required external evidence parent does not exist: $externalParent"
    }
}
$saveDat = Join-Path $ExpectedWorkDir ("save\{0}.dat" -f $LoadSlot)
if (-not (Test-Path -LiteralPath $saveDat -PathType Leaf)) {
    throw "Load slot $LoadSlot has no save file at $saveDat; the forced loader entry needs a real save"
}
$inputFull = Get-FullPath -Path $InputExe
$inputSha = Get-FileSha256 -Path $inputFull
if ($inputSha -ne $ExpectedBaseSha256) {
    throw "Original executable SHA-256 is $inputSha, expected $ExpectedBaseSha256"
}
$pythonExe = if (Test-Path -LiteralPath $Python -PathType Leaf) {
    (Get-Item -LiteralPath $Python).FullName
}
else {
    (Get-Command python -CommandType Application -ErrorAction Stop).Source
}
$patcher = Join-Path $RepoRoot 'patch_clash95_hd.py'
$patchStageReporter = Join-Path $RepoRoot 'tools\patch_stage_report.py'
$converter = Join-Path $RepoRoot 'tools\cdb_surface_dump_to_png.py'
$assembler = Join-Path $RepoRoot 'tools\hidden_soak_report_assembler.py'
$grader = Join-Path $RepoRoot 'tools\hd_soak_report.py'
foreach ($path in @($patcher, $patchStageReporter, $converter, $assembler, $grader)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required helper was not found: $path"
    }
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$runName = "hidden-soak-$stamp-$Route"
$candidateRunDir = Join-Path (Get-FullPath -Path $CandidateDir) $runName
$runDir = Join-Path (Get-FullPath -Path $OutDir) $runName
if (-not $CandidateName) {
    $CandidateName = "clash95_hd_hidden_soak_$($stamp -replace '-', '_').exe"
}
if ([System.IO.Path]::GetFileName($CandidateName) -ne $CandidateName) {
    throw '-CandidateName must be a file name, not a path'
}
$candidateFull = Get-FullPath -Path (Join-Path $candidateRunDir $CandidateName)
if ($candidateFull -eq $inputFull -or (Split-Path -Leaf $candidateFull).ToLowerInvariant() -eq 'clash95.exe') {
    throw "Refusing an unsafe candidate path: $candidateFull"
}
foreach ($newPath in @($candidateRunDir, $runDir, $candidateFull)) {
    if (Test-Path -LiteralPath $newPath) {
        throw "Per-run output already exists: $newPath"
    }
}
foreach ($publishSpec in @(
    @{ Name = 'ReportJson'; Value = $ReportJson; Extension = '.json' },
    @{ Name = 'ReportMarkdown'; Value = $ReportMarkdown; Extension = '.md' },
    @{ Name = 'GuardJson'; Value = $GuardJson; Extension = '.json' },
    @{ Name = 'GuardMarkdown'; Value = $GuardMarkdown; Extension = '.md' }
)) {
    if ($publishSpec.Value -and [System.IO.Path]::GetExtension($publishSpec.Value).ToLowerInvariant() -ne $publishSpec.Extension) {
        throw "-$($publishSpec.Name) must use the $($publishSpec.Extension) extension"
    }
}

if (-not $Execute) {
    $commandParts = @('powershell.exe -NoProfile -ExecutionPolicy Bypass -File')
    $commandParts += "'" + $PSCommandPath.Replace("'", "''") + "'"
    foreach ($parameter in @(
        @{ Name = 'Route'; Value = $Route },
        @{ Name = 'DurationSec'; Value = $DurationSec },
        @{ Name = 'FrameIntervalSec'; Value = $FrameIntervalSec },
        @{ Name = 'PanIntervalSec'; Value = $PanIntervalSec },
        @{ Name = 'LoadSlot'; Value = $LoadSlot },
        @{ Name = 'ReadyTimeoutSec'; Value = $ReadyTimeoutSec },
        @{ Name = 'EndGraceSec'; Value = $EndGraceSec },
        @{ Name = 'PngEdgeCount'; Value = $PngEdgeCount },
        @{ Name = 'MaxArtifactMB'; Value = $MaxArtifactMB },
        @{ Name = 'MaxWorkingSetGrowthMB'; Value = $MaxWorkingSetGrowthMB },
        @{ Name = 'MaxPrivateMemoryGrowthMB'; Value = $MaxPrivateMemoryGrowthMB },
        @{ Name = 'MaxHandleGrowth'; Value = $MaxHandleGrowth },
        @{ Name = 'Python'; Value = $pythonExe },
        @{ Name = 'ProbeTemplate'; Value = $ProbeTemplate },
        @{ Name = 'SoakProbeTemplate'; Value = $SoakProbeTemplate },
        @{ Name = 'DdrawProxyBuildScript'; Value = $DdrawProxyBuildScript },
        @{ Name = 'ReportJson'; Value = $ReportJson },
        @{ Name = 'ReportMarkdown'; Value = $ReportMarkdown },
        @{ Name = 'GuardJson'; Value = $GuardJson },
        @{ Name = 'GuardMarkdown'; Value = $GuardMarkdown }
    )) {
        if ([string]$parameter.Value -ne '') {
            $commandParts += '-{0} ''{1}''' -f $parameter.Name, ([string]$parameter.Value).Replace("'", "''")
        }
    }
    $commandParts += '-Execute -RequirePass -Json'
    $dryRun = [ordered]@{
        executed = $false
        preflight_passed = $true
        environment = 'hidden_cdb_host'
        route = $Route
        duration_sec = $DurationSec
        input_sha256 = $inputSha
        candidate_run_directory = $candidateRunDir
        output_directory = $runDir
        hidden_runtime_command = $commandParts -join ' '
    }
    if ($Json) {
        $dryRun | ConvertTo-Json -Depth 4
        return
    }
    Write-Host 'DRY RUN: preflight passed; no directories, candidates, proxies, reports, or processes were created.'
    Write-Host "Route/duration: $Route / $DurationSec sec"
    Write-Host "Protected input SHA-256: $inputSha"
    Write-Host "Candidate run directory: $candidateRunDir"
    Write-Host "Evidence run directory: $runDir"
    Write-Host $dryRun.hidden_runtime_command
    return
}

if (-not ([System.Management.Automation.PSTypeName]'ClashHiddenSoakNative').Type) {
    Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class ClashHiddenSoakNative {
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

    public static int[] Histogram(byte[] data) {
        int[] counts = new int[256];
        if (data == null) {
            return counts;
        }
        for (int i = 0; i < data.Length; i++) {
            counts[data[i]]++;
        }
        return counts;
    }
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

function Convert-CdbHexToUInt64 {
    param([string]$Value)
    $clean = ($Value -replace '`', '').Trim()
    [Convert]::ToUInt64($clean, 16)
}

function Read-TargetSurfaceBytes {
    param(
        [int]$ProcessId,
        [UInt64]$BaseAddress,
        [int]$ByteCount
    )

    if ($ByteCount -le 0) {
        throw "Invalid surface byte count: $ByteCount"
    }
    $processVmRead = 0x0010
    $processQueryInformation = 0x0400
    $handle = [ClashHiddenSoakNative]::OpenProcess($processVmRead -bor $processQueryInformation, $false, [uint32]$ProcessId)
    if ($handle -eq [IntPtr]::Zero) {
        $lastError = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        throw "OpenProcess($ProcessId) failed with Win32 error $lastError"
    }
    try {
        $buffer = New-Object byte[] $ByteCount
        $bytesRead = [UIntPtr]::Zero
        $address = [IntPtr]::new([int64]$BaseAddress)
        $ok = [ClashHiddenSoakNative]::ReadProcessMemory(
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
        return $buffer
    }
    finally {
        [ClashHiddenSoakNative]::CloseHandle($handle) | Out-Null
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
    $desktop = [ClashHiddenSoakNative]::CreateDesktop($DesktopName, [IntPtr]::Zero, [IntPtr]::Zero, 0, $desktopAllAccess, [IntPtr]::Zero)
    if ($desktop -eq [IntPtr]::Zero) {
        $lastError = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        throw "CreateDesktop failed with Win32 error $lastError. This harness never falls back to a visible desktop."
    }

    $startupInfo = New-Object ClashHiddenSoakNative+STARTUPINFO
    $startupInfo.cb = [Runtime.InteropServices.Marshal]::SizeOf([type]'ClashHiddenSoakNative+STARTUPINFO')
    $startupInfo.lpDesktop = $DesktopName
    $startupInfo.dwFlags = 0x00000001
    $startupInfo.wShowWindow = 0

    $processInfo = New-Object ClashHiddenSoakNative+PROCESS_INFORMATION
    $commandLine = New-Object System.Text.StringBuilder
    [void]$commandLine.Append((Quote-CommandLineArgument $CdbPath))
    foreach ($argument in $Arguments) {
        [void]$commandLine.Append(' ')
        [void]$commandLine.Append((Quote-CommandLineArgument $argument))
    }

    $creationFlags = 0x00000010
    # CDB inherits this process environment and the game inherits CDB's.  Make
    # presentation impossible for the entire child chain even if the caller has
    # CLASH_PROXY_PRESENT=1 set for a separate visible-runtime workflow.
    $savedProxyPresent = [Environment]::GetEnvironmentVariable('CLASH_PROXY_PRESENT', 'Process')
    [Environment]::SetEnvironmentVariable('CLASH_PROXY_PRESENT', $null, 'Process')
    try {
        $ok = [ClashHiddenSoakNative]::CreateProcess(
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
    }
    finally {
        [Environment]::SetEnvironmentVariable('CLASH_PROXY_PRESENT', $savedProxyPresent, 'Process')
    }
    if (-not $ok) {
        $lastError = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        [ClashHiddenSoakNative]::CloseDesktop($desktop) | Out-Null
        throw "CreateProcess on hidden desktop failed with Win32 error $lastError."
    }

    [ClashHiddenSoakNative]::CloseHandle($processInfo.hThread) | Out-Null
    [pscustomobject]@{
        ProcessId = [int]$processInfo.dwProcessId
        ProcessHandle = $processInfo.hProcess
        DesktopHandle = $desktop
        DesktopName = $DesktopName
        CommandLine = $commandLine.ToString()
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

function Stop-LaunchedProcesses {
    param(
        [Nullable[int]]$CdbPid,
        [string]$CandidatePath,
        [datetime]$RunStart
    )

    $toStop = @()
    $errors = @()
    $stoppedIds = @()
    if ($CdbPid) {
        $cdbProcess = Get-Process -Id $CdbPid -ErrorAction SilentlyContinue
        if ($cdbProcess) {
            $toStop += $cdbProcess
        }
    }
    $toStop += Get-LaunchedCandidateProcesses -CandidatePath $CandidatePath -RunStart $RunStart

    # Keep the debugger first: its debuggee may not finish terminating until
    # CDB exits. Deduplicate in insertion order instead of sorting numeric PIDs.
    $seenIds = New-Object 'System.Collections.Generic.HashSet[int]'
    foreach ($process in $toStop) {
        if ($null -eq $process -or -not $seenIds.Add([int]$process.Id)) {
            continue
        }
        try {
            if (-not $process.HasExited) {
                Stop-Process -Id $process.Id -Force -ErrorAction Stop
                if (-not $process.WaitForExit(5000)) {
                    throw "process $($process.Id) did not exit within 5 seconds"
                }
                $stoppedIds += [int]$process.Id
            }
        }
        catch {
            $errors += "failed to stop process $($process.Id): $($_.Exception.Message)"
        }
    }

    $cdbStillRunning = $false
    if ($CdbPid) {
        $cdbStillRunning = $null -ne (Get-Process -Id $CdbPid -ErrorAction SilentlyContinue)
    }
    $gameStillRunning = @(
        Get-LaunchedCandidateProcesses -CandidatePath $CandidatePath -RunStart $RunStart
    ).Count -gt 0
    if ($cdbStillRunning) {
        $errors += "CDB process $CdbPid is still running after cleanup"
    }
    if ($gameStillRunning) {
        $errors += 'one or more candidate game processes are still running after cleanup'
    }
    [pscustomobject]@{
        CdbStopped = -not $cdbStillRunning
        GameStopped = -not $gameStillRunning
        AllTerminated = (-not $cdbStillRunning) -and (-not $gameStillRunning) -and $errors.Count -eq 0
        StoppedProcessIds = @($stoppedIds)
        Errors = @($errors)
    }
}

function Parse-SoakLog {
    # Parse only complete structured rows.  CDB .echo prose deliberately names
    # several markers; trimming a line and anchoring both ends prevents that
    # startup text from becoming evidence.
    param([string]$LogText)

    $readyRows = New-Object System.Collections.ArrayList
    $routeStarts = New-Object System.Collections.ArrayList
    $routeEnds = New-Object System.Collections.ArrayList
    $heartbeats = New-Object System.Collections.ArrayList
    $panPlans = New-Object System.Collections.ArrayList
    $panUnsafeRows = New-Object System.Collections.ArrayList
    $panEvents = New-Object System.Collections.ArrayList
    $avObserved = $false
    $surfaceInvalidObserved = $false
    $appRequestQuitObserved = $false

    $lineNumber = 0
    foreach ($rawLine in @($LogText -split "`r?`n")) {
        $lineNumber++
        $line = $rawLine.Trim()
        if (-not $line) { continue }

        $match = [regex]::Match($line, '^(SOAK_SURFDUMP_READY|SURFDUMP_READY) redraw_seq=(\d+) surface=([0-9a-fA-F`]+) size=\((\d+),(\d+)\) base=([0-9a-fA-F`]+) bytes=(\d+)$')
        if ($match.Success) {
            [void]$readyRows.Add([pscustomobject]@{
                Source = $match.Groups[1].Value
                RedrawSeq = [int64]$match.Groups[2].Value
                Surface = $match.Groups[3].Value
                Width = [int]$match.Groups[4].Value
                Height = [int]$match.Groups[5].Value
                Base = $match.Groups[6].Value
                Bytes = [int]$match.Groups[7].Value
                LineNumber = $lineNumber
            })
            continue
        }
        $match = [regex]::Match($line, '^SOAK_ROUTE_START route_ticks=(\d+) pan=(0|1) player=(-?\d+) tick=(-?\d+) gd=([0-9a-fA-F`]+) scroll=\((-?\d+),(-?\d+)\)$')
        if ($match.Success) {
            [void]$routeStarts.Add([pscustomobject]@{
                RouteTicks = [int64]$match.Groups[1].Value
                Pan = [int]$match.Groups[2].Value
                Player = [int]$match.Groups[3].Value
                Tick = [int64]$match.Groups[4].Value
                GameData = $match.Groups[5].Value
                ScrollX = [int]$match.Groups[6].Value
                ScrollY = [int]$match.Groups[7].Value
                LineNumber = $lineNumber
            })
            continue
        }
        $match = [regex]::Match($line, '^SOAK_ROUTE_END route_ticks=(\d+) pan=(0|1) hits=(\d+) tickdelta=(\d+) player=(-?\d+) scroll=\((-?\d+),(-?\d+)\)$')
        if ($match.Success) {
            [void]$routeEnds.Add([pscustomobject]@{
                RouteTicks = [int64]$match.Groups[1].Value
                Pan = [int]$match.Groups[2].Value
                Hits = [int64]$match.Groups[3].Value
                TickDelta = [int64]$match.Groups[4].Value
                Player = [int]$match.Groups[5].Value
                ScrollX = [int]$match.Groups[6].Value
                ScrollY = [int]$match.Groups[7].Value
                LineNumber = $lineNumber
            })
            continue
        }
        $match = [regex]::Match($line, '^SOAK_HEARTBEAT hits=(\d+) tickdelta=(\d+) player=(-?\d+) scroll=\((-?\d+),(-?\d+)\)$')
        if ($match.Success) {
            [void]$heartbeats.Add([pscustomobject]@{
                Hits = [int64]$match.Groups[1].Value
                TickDelta = [int64]$match.Groups[2].Value
                Player = [int]$match.Groups[3].Value
                ScrollX = [int]$match.Groups[4].Value
                ScrollY = [int]$match.Groups[5].Value
                LineNumber = $lineNumber
            })
            continue
        }
        $match = [regex]::Match($line, '^SOAK_PAN_PLAN base=\((-?\d+),(-?\d+)\) delta=\((-?\d+),(-?\d+)\) max=\((-?\d+),(-?\d+)\) safe=1$')
        if ($match.Success) {
            [void]$panPlans.Add([pscustomobject]@{
                BaseX = [int]$match.Groups[1].Value
                BaseY = [int]$match.Groups[2].Value
                DeltaX = [int]$match.Groups[3].Value
                DeltaY = [int]$match.Groups[4].Value
                MaxX = [int]$match.Groups[5].Value
                MaxY = [int]$match.Groups[6].Value
                LineNumber = $lineNumber
            })
            continue
        }
        $match = [regex]::Match($line, '^SOAK_PAN_UNSAFE base=\((-?\d+),(-?\d+)\) max=\((-?\d+),(-?\d+)\) reason=([a-z0-9_-]+)$')
        if ($match.Success) {
            [void]$panUnsafeRows.Add([pscustomobject]@{
                BaseX = [int]$match.Groups[1].Value
                BaseY = [int]$match.Groups[2].Value
                MaxX = [int]$match.Groups[3].Value
                MaxY = [int]$match.Groups[4].Value
                Reason = $match.Groups[5].Value
                LineNumber = $lineNumber
            })
            continue
        }
        $match = [regex]::Match($line, '^SOAK_PAN_SET phase=(\d+) x=(-?\d+) y=(-?\d+) hits=(\d+) tickdelta=(\d+) delta=\((-?\d+),(-?\d+)\)$')
        if ($match.Success) {
            [void]$panEvents.Add([pscustomobject]@{
                Phase = [int]$match.Groups[1].Value
                X = [int]$match.Groups[2].Value
                Y = [int]$match.Groups[3].Value
                Hits = [int64]$match.Groups[4].Value
                TickDelta = [int64]$match.Groups[5].Value
                DeltaX = [int]$match.Groups[6].Value
                DeltaY = [int]$match.Groups[7].Value
                LineNumber = $lineNumber
            })
            continue
        }
        if ($line -eq 'AV_SURFDUMP') { $avObserved = $true; continue }
        if ($line -eq 'SURFDUMP_INVALID') { $surfaceInvalidObserved = $true; continue }
        if ($line -match '^SURFDUMP_APP_REQUEST_QUIT text_ptr=[0-9a-fA-F`]+ caption_ptr=[0-9a-fA-F`]+$') {
            $appRequestQuitObserved = $true
        }
    }

    [pscustomobject]@{
        ReadyRows = @($readyRows)
        RouteStarts = @($routeStarts)
        RouteEnds = @($routeEnds)
        Heartbeats = @($heartbeats)
        PanPlans = @($panPlans)
        PanUnsafeRows = @($panUnsafeRows)
        PanEvents = @($panEvents)
        AvObserved = $avObserved
        SurfaceInvalidObserved = $surfaceInvalidObserved
        AppRequestQuitObserved = $appRequestQuitObserved
    }
}

function Get-ProcessSnapshot {
    param([System.Diagnostics.Process]$Process)
    try {
        $Process.Refresh()
        [ordered]@{
            Timestamp = (Get-Date).ToString('o')
            HasExited = [bool]$Process.HasExited
            ExitCode = if ($Process.HasExited) { $Process.ExitCode } else { $null }
            WorkingSet64 = if ($Process.HasExited) { $null } else { $Process.WorkingSet64 }
            PrivateMemorySize64 = if ($Process.HasExited) { $null } else { $Process.PrivateMemorySize64 }
            HandleCount = if ($Process.HasExited) { $null } else { $Process.HandleCount }
        }
    } catch {
        [ordered]@{
            Timestamp = (Get-Date).ToString('o')
            HasExited = $true
            ExitCode = $null
            WorkingSet64 = $null
            PrivateMemorySize64 = $null
            HandleCount = $null
            Error = $_.Exception.Message
        }
    }
}

function Get-FrameMetrics {
    param([byte[]]$Bytes)
    $hist = [ClashHiddenSoakNative]::Histogram($Bytes)
    $total = $Bytes.Length
    $unique = 0
    for ($i = 0; $i -lt 256; $i++) {
        if ($hist[$i] -gt 0) {
            $unique++
        }
    }
    $nonblack = if ($total -gt 0) { [math]::Round((($total - $hist[0]) * 100.0) / $total, 3) } else { 0.0 }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = ([System.BitConverter]::ToString($sha.ComputeHash($Bytes)) -replace '-', '').ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
    [pscustomobject]@{
        Hash = $hash
        NonblackPercent = $nonblack
        UniqueSampleColors = $unique
    }
}

function Get-DirectorySizeBytes {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return 0
    }
    $size = 0L
    Get-ChildItem -LiteralPath $Path -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
        $size += $_.Length
    }
    return $size
}

function Get-SampleElapsedSeconds {
    param([object[]]$Samples)
    if (@($Samples).Count -lt 2) {
        return $null
    }
    try {
        $first = [datetimeoffset]::Parse([string]$Samples[0].Timestamp)
        $last = [datetimeoffset]::Parse([string]$Samples[-1].Timestamp)
        return [math]::Round(($last - $first).TotalSeconds, 3)
    }
    catch {
        return $null
    }
}

function Get-RouteValidationFailures {
    param(
        [pscustomobject]$Observations,
        [string]$ExpectedRoute,
        [int64]$ExpectedDurationTicks,
        [int64]$ExpectedPanIntervalTicks
    )

    $failures = @()
    $expectedPan = if ($ExpectedRoute -eq 'map-pan') { 1 } else { 0 }
    $soakReadyRows = @($Observations.ReadyRows | Where-Object { $_.Source -eq 'SOAK_SURFDUMP_READY' })
    if ($soakReadyRows.Count -ne 1) {
        $failures += "expected exactly one structured SOAK_SURFDUMP_READY row, observed $($soakReadyRows.Count)"
    }
    if (@($Observations.RouteStarts).Count -ne 1) {
        $failures += "expected exactly one structured SOAK_ROUTE_START row, observed $(@($Observations.RouteStarts).Count)"
    }
    if (@($Observations.RouteEnds).Count -ne 1) {
        $failures += "expected exactly one structured SOAK_ROUTE_END row, observed $(@($Observations.RouteEnds).Count)"
    }

    $start = @($Observations.RouteStarts | Select-Object -First 1)
    $end = @($Observations.RouteEnds | Select-Object -First 1)
    if ($start.Count) {
        $start = $start[0]
        if ($start.RouteTicks -ne $ExpectedDurationTicks) {
            $failures += "SOAK_ROUTE_START route_ticks=$($start.RouteTicks), expected $ExpectedDurationTicks"
        }
        if ($start.Pan -ne $expectedPan) {
            $failures += "SOAK_ROUTE_START pan=$($start.Pan), expected $expectedPan for $ExpectedRoute"
        }
    }
    else {
        $start = $null
    }
    if ($end.Count) {
        $end = $end[0]
        if ($end.RouteTicks -ne $ExpectedDurationTicks) {
            $failures += "SOAK_ROUTE_END route_ticks=$($end.RouteTicks), expected $ExpectedDurationTicks"
        }
        if ($end.Pan -ne $expectedPan) {
            $failures += "SOAK_ROUTE_END pan=$($end.Pan), expected $expectedPan for $ExpectedRoute"
        }
        if ($end.TickDelta -lt $ExpectedDurationTicks) {
            $failures += "SOAK_ROUTE_END tickdelta=$($end.TickDelta) is below requested route_ticks=$ExpectedDurationTicks"
        }
        if ($end.Hits -le 0) {
            $failures += 'SOAK_ROUTE_END did not record a positive redraw hit count'
        }
    }
    else {
        $end = $null
    }
    if ($start -and $end -and $end.LineNumber -le $start.LineNumber) {
        $failures += 'SOAK_ROUTE_END was not ordered after SOAK_ROUTE_START'
    }

    $previousHeartbeatTick = -1L
    $previousHeartbeatHits = -1L
    if (@($Observations.Heartbeats).Count -lt 1) {
        $failures += 'no structured SOAK_HEARTBEAT rows were observed'
    }
    foreach ($heartbeat in @($Observations.Heartbeats)) {
        if ($heartbeat.TickDelta -le $previousHeartbeatTick -or $heartbeat.Hits -le $previousHeartbeatHits) {
            $failures += 'SOAK_HEARTBEAT rows are not strictly ordered by tickdelta and hits'
            break
        }
        if ($start -and $heartbeat.LineNumber -le $start.LineNumber) {
            $failures += 'a SOAK_HEARTBEAT row appeared before SOAK_ROUTE_START'
            break
        }
        if ($end -and $heartbeat.LineNumber -ge $end.LineNumber) {
            $failures += 'a SOAK_HEARTBEAT row appeared at or after SOAK_ROUTE_END'
            break
        }
        $previousHeartbeatTick = $heartbeat.TickDelta
        $previousHeartbeatHits = $heartbeat.Hits
    }

    if (@($Observations.PanUnsafeRows).Count -gt 0) {
        foreach ($unsafe in @($Observations.PanUnsafeRows)) {
            $failures += "SOAK_PAN_UNSAFE reason=$($unsafe.Reason) base=($($unsafe.BaseX),$($unsafe.BaseY)) max=($($unsafe.MaxX),$($unsafe.MaxY))"
        }
    }

    if ($ExpectedRoute -eq 'map-idle') {
        if (@($Observations.PanPlans).Count -gt 0 -or @($Observations.PanEvents).Count -gt 0) {
            $failures += 'map-idle emitted structured pan-plan or pan-event rows'
        }
        return @($failures)
    }

    if (@($Observations.PanPlans).Count -ne 1) {
        $failures += "map-pan expected exactly one safe SOAK_PAN_PLAN row, observed $(@($Observations.PanPlans).Count)"
        return @($failures)
    }
    $plan = $Observations.PanPlans[0]
    if ($start -and ($plan.BaseX -ne $start.ScrollX -or $plan.BaseY -ne $start.ScrollY)) {
        $failures += 'SOAK_PAN_PLAN base does not match SOAK_ROUTE_START scroll coordinates'
    }
    if ($plan.MaxX -lt 0 -or $plan.MaxY -lt 0 -or
        $plan.BaseX -lt 0 -or $plan.BaseX -gt $plan.MaxX -or
        $plan.BaseY -lt 0 -or $plan.BaseY -gt $plan.MaxY) {
        $failures += 'SOAK_PAN_PLAN base/max bounds are invalid'
    }
    if (($plan.DeltaX -notin @(-1, 0, 1)) -or ($plan.DeltaY -notin @(-1, 0, 1)) -or
        ($plan.DeltaX -eq 0 -and $plan.DeltaY -eq 0)) {
        $failures += 'SOAK_PAN_PLAN did not select a safe inward +/-1 direction'
    }
    $targetX = $plan.BaseX + $plan.DeltaX
    $targetY = $plan.BaseY + $plan.DeltaY
    if ($targetX -lt 0 -or $targetX -gt $plan.MaxX -or $targetY -lt 0 -or $targetY -gt $plan.MaxY) {
        $failures += 'SOAK_PAN_PLAN target leaves the live scroll bounds'
    }

    $events = @($Observations.PanEvents)
    if ($events.Count -lt 1) {
        $failures += 'map-pan recorded no structured SOAK_PAN_SET events'
        return @($failures)
    }
    $previousTick = 0L
    $previousHits = -1L
    for ($index = 0; $index -lt $events.Count; $index++) {
        $event = $events[$index]
        $expectedPhase = $index % 4
        if ($event.Phase -ne $expectedPhase) {
            $failures += "SOAK_PAN_SET event $index phase=$($event.Phase), expected $expectedPhase"
            break
        }
        if ($event.DeltaX -ne $plan.DeltaX -or $event.DeltaY -ne $plan.DeltaY) {
            $failures += "SOAK_PAN_SET event $index does not match the safe pan delta"
            break
        }
        $expectedX = if ($expectedPhase -in @(1, 2)) { $targetX } else { $plan.BaseX }
        $expectedY = if ($expectedPhase -in @(2, 3)) { $targetY } else { $plan.BaseY }
        if ($event.X -ne $expectedX -or $event.Y -ne $expectedY) {
            $failures += "SOAK_PAN_SET event $index coordinates=($($event.X),$($event.Y)), expected=($expectedX,$expectedY)"
            break
        }
        if (($event.TickDelta - $previousTick) -lt $ExpectedPanIntervalTicks -or $event.Hits -le $previousHits) {
            $failures += "SOAK_PAN_SET event $index is not ordered by the requested pan interval and redraw hits"
            break
        }
        if (($start -and $event.LineNumber -le $start.LineNumber) -or ($end -and $event.LineNumber -ge $end.LineNumber)) {
            $failures += "SOAK_PAN_SET event $index is outside the route start/end interval"
            break
        }
        $previousTick = $event.TickDelta
        $previousHits = $event.Hits
    }
    return @($failures)
}

function Publish-CanonicalArtifact {
    param([string]$Source, [string]$Destination)
    if (-not $Destination) { return }
    $destinationFull = Get-FullPath -Path $Destination
    $parent = Split-Path -Parent $destinationFull
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    if (-not (Test-PathEqual -Left $Source -Right $destinationFull)) {
        Copy-Item -LiteralPath $Source -Destination $destinationFull -Force
    }
}

$publishReportJson = $ReportJson
$publishReportMarkdown = $ReportMarkdown
$publishGuardJson = $GuardJson
$publishGuardMarkdown = $GuardMarkdown

New-Item -ItemType Directory -Path $candidateRunDir -Force | Out-Null
New-Item -ItemType Directory -Path $runDir -Force | Out-Null
$framesDir = Join-Path $runDir 'frames'
New-Item -ItemType Directory -Path $framesDir -Force | Out-Null
$logPath = Join-Path $runDir 'hidden-soak-cdb.log'
$generatedProbe = Join-Path $runDir 'clash95_hidden_soak_probe.generated.cdb'
$patchStageJson = Join-Path $runDir 'patch-stage.json'
$samplesJson = Join-Path $runDir 'hidden-soak-samples.json'
$runReportJson = Join-Path $runDir 'report.json'
$runReportMarkdown = Join-Path $runDir 'RUN-SUMMARY.md'
$runGuardJson = Join-Path $runDir 'guard.json'
$runGuardMarkdown = Join-Path $runDir 'GUARD-SUMMARY.md'

& $pythonExe $patcher --input $inputFull --output $candidateFull --stage $Stage
if ($LASTEXITCODE -ne 0) {
    throw "patch_clash95_hd.py failed with exit code $LASTEXITCODE"
}
$candidateSha = Get-FileSha256 -Path $candidateFull
& $pythonExe $patchStageReporter --exe $candidateFull --stage $Stage --write-json $patchStageJson --require-current-hd-map
if ($LASTEXITCODE -ne 0) {
    throw "patch_stage_report.py failed with exit code $LASTEXITCODE"
}

# The local proxy is mandatory for the hidden lane.  It is built next to the
# candidate so Windows loads it instead of C:\Clash\ddraw.dll (the user-owned
# visible GOG wrapper), while C:\Clash remains the asset working directory.
$proxyDllPath = Join-Path $candidateRunDir 'ddraw.dll'
$proxyManifestPath = Join-Path $candidateRunDir 'ddraw_surfdump_proxy.build.json'
$proxyLogPath = Join-Path $candidateRunDir 'ddraw_surfdump_proxy.log'
& $DdrawProxyBuildScript -OutputDll $proxyDllPath -LogDir $runDir
if (-not (Test-Path -LiteralPath $proxyDllPath -PathType Leaf)) {
    throw "DirectDraw proxy build did not create $proxyDllPath"
}
if (-not (Test-Path -LiteralPath $proxyManifestPath -PathType Leaf)) {
    throw "DirectDraw proxy build manifest was not created: $proxyManifestPath"
}
$proxySha = Get-FileSha256 -Path $proxyDllPath
if ((Get-PeMachine -Path $proxyDllPath) -ne 0x014C) {
    throw "DirectDraw proxy is not an x86 PE DLL: $proxyDllPath"
}
$proxyManifest = Get-Content -LiteralPath $proxyManifestPath -Raw | ConvertFrom-Json
if ($proxyManifest.generated_by -ne 'clash-hd-surface-dump-proxy') {
    throw 'DirectDraw proxy manifest has the wrong generated_by value'
}
if (-not (Test-PathEqual -Left ([string]$proxyManifest.output) -Right $proxyDllPath)) {
    throw 'DirectDraw proxy manifest output does not match the candidate-local ddraw.dll'
}
if ([string]$proxyManifest.output_sha256 -ne $proxySha) {
    throw 'DirectDraw proxy manifest output SHA-256 does not match ddraw.dll'
}
if (-not (Test-Path -LiteralPath ([string]$proxyManifest.source) -PathType Leaf) -or
    (Get-FileSha256 -Path ([string]$proxyManifest.source)) -ne [string]$proxyManifest.source_sha256) {
    throw 'DirectDraw proxy manifest source provenance did not verify'
}
$proxyBuildLogPath = [string]$proxyManifest.build_log
if (-not (Test-Path -LiteralPath $proxyBuildLogPath -PathType Leaf)) {
    throw "DirectDraw proxy build log was not created: $proxyBuildLogPath"
}
if (Test-Path -LiteralPath $proxyLogPath) {
    throw "Fresh per-run proxy log unexpectedly already exists: $proxyLogPath"
}

# --- Probe composition (base surface-dump template + hidden soak extra) ------
$durationTicks = [int64]$DurationSec * 64
$panIntervalTicks = [int64]$PanIntervalSec * 64
$panFlag = if ($Route -eq 'map-pan') { '1' } else { '0' }

$loadMouseX = 320
$loadMouseY = 166 + (22 * $LoadSlot)
$loadMouseRawX = '{0:x8}' -f ($loadMouseX -shl 6)
$loadMouseRawY = '{0:x8}' -f ($loadMouseY -shl 6)

$extraProbeText = (Get-Content -LiteralPath $SoakProbeTemplate -Raw).Trim()
foreach ($placeholder in @('__SOAK_DURATION_TICKS__', '__SOAK_PAN__', '__PAN_INTERVAL_TICKS__')) {
    if ($extraProbeText.IndexOf($placeholder) -lt 0) {
        throw "Soak probe template is missing the required placeholder ${placeholder}: $SoakProbeTemplate"
    }
}
if ($extraProbeText -match '(?m)^\s*g\s*$') {
    throw "Soak probe template must not contain a standalone g command: $SoakProbeTemplate"
}
$extraProbeText = $extraProbeText.Replace('__SOAK_DURATION_TICKS__', ('0n{0}' -f $durationTicks))
$extraProbeText = $extraProbeText.Replace('__PAN_INTERVAL_TICKS__', ('0n{0}' -f $panIntervalTicks))
$extraProbeText = $extraProbeText.Replace('__SOAK_PAN__', $panFlag)
$extraProbeText = $extraProbeText.Replace('__LOAD_SLOT__', [string]$LoadSlot)
$extraProbeText = $extraProbeText.Replace('__LOAD_MOUSE_RAW_X__', $loadMouseRawX)
$extraProbeText = $extraProbeText.Replace('__LOAD_MOUSE_RAW_Y__', $loadMouseRawY)

$probeText = Get-Content -LiteralPath $ProbeTemplate -Raw
$preEntryLoadCoordAction = 'ed 00544cfc __LOAD_MOUSE_RAW_X__; ed 00544d00 __LOAD_MOUSE_RAW_Y__; eb 005451c0 80; ed 00544d04 1; .if (@$t1 < 0n16) { .printf \"SURFDUMP_LOAD_COORD seq=%d choice=%d entry=0x%08x ex=%d ey=%d mouse=(%d,%d) selected=%d accept=%d\\n\", @$t1, poi(00543d7c), @eax, poi(@eax), poi(@eax+4), poi(00544cfc)>>by(0054512c), poi(00544d00)>>by(0054512c), poi(005441e0), poi(00544190); r @$t1 = @$t1 + 1; };'
$probeText = $probeText.Replace('__PRE_ENTRY_LOAD_COORD_ACTION__', $preEntryLoadCoordAction)
$probeText = $probeText.Replace('__LOAD_SLOT__', [string]$LoadSlot)
$probeText = $probeText.Replace('__LOAD_MOUSE_RAW_X__', $loadMouseRawX)
$probeText = $probeText.Replace('__LOAD_MOUSE_RAW_Y__', $loadMouseRawY)

$playGamePattern = '(?m)^bp 0040B660 '
if ($probeText -notmatch $playGamePattern) {
    throw 'Could not find the PlayGame breakpoint insertion point in the CDB probe template.'
}
$probeText = [regex]::Replace($probeText, $playGamePattern, ($extraProbeText + "`r`n`r`n" + 'bp 0040B660 '), 1)

# Fast-forward start animations (the proven -FastForwardStartAnims block).
$startAnimsBreakpoint = @(
    '.echo SURFDUMP_START_ANIMS_SLEEP_FAST_FORWARD_ENABLED'
    'bp 0044789a ".printf \"SURFDUMP_SKIP_START_SLEEP ret=004478a1\\n\"; r eip=004478a1; r esp=@esp+4; gc"'
    'bp 0046e4d0 ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_AVI_SLEEP call=0046e4d0 next=0046e4d7\\n\"; r @$t12 = @$t12 + 1; }; r eip=0046e4d7; r esp=@esp+4; gc } .else { gc }"'
    'bp 0046e6df ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_AVI_SLEEP call=0046e6df next=0046e6e6\\n\"; r @$t12 = @$t12 + 1; }; r eip=0046e6e6; r esp=@esp+4; gc } .else { gc }"'
    'bp 0046fd01 ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_AVI_SLEEP call=0046fd01 next=0046fd08\\n\"; r @$t12 = @$t12 + 1; }; r eip=0046fd08; r esp=@esp+4; gc } .else { gc }"'
    'bp 0047BFD0 ".if (@$t14 == 0) { .if (@$t12 < 0n8) { .printf \"SURFDUMP_SKIP_TIME_SLEEP ret=%p\\n\", poi(@esp); r @$t12 = @$t12 + 1; }; r eax=0; r eip=poi(@esp); r esp=@esp+4; gc } .else { gc }"'
) -join "`r`n"
$probeText = $probeText.Replace('__START_ANIMS_BP__', $startAnimsBreakpoint)
$probeText = $probeText.Replace('__VISIBILITY_PLAYGAME_ACTION__', '')
$probeText = $probeText.Replace('__VISIBILITY_PATCH_ACTION__', '')
# Host-ReadProcessMemory dumping only; the game continues after the base READY.
$probeText = $probeText.Replace('__SURFACE_DUMP_ACTION__', '.echo SURFDUMP_HOST_READY; gc')
$probeText = $probeText.Replace('__RAW_PATH__', (((Get-FullPath -Path (Join-Path $framesDir 'surface.raw'))) -replace '\\', '/'))
$leftoverPlaceholders = [regex]::Matches($probeText, '__[A-Z0-9_]+__') | ForEach-Object { $_.Value } | Sort-Object -Unique
if (@($leftoverPlaceholders).Count -gt 0) {
    throw "Probe composition left unsubstituted placeholders: $($leftoverPlaceholders -join ', ')"
}
Set-Content -LiteralPath $generatedProbe -Value $probeText -Encoding ASCII

# --- Hidden-desktop launch + sampling loop -----------------------------------
$runStart = Get-Date
$desktopName = "ClashHiddenSoak_$($stamp -replace '[^0-9A-Za-z_]', '_')"
$cdbCommand = '$$><' + $generatedProbe
$cdbArgs = @('-hd', '-logo', $logPath, '-c', $cdbCommand, $candidateFull)

$launch = $null
$targetProcess = $null
$ready = $null
$readyObserved = $false
$routeStartObserved = $false
$routeEndObserved = $false
$avObserved = $false
$appRequestQuitObserved = $false
$surfInvalidObserved = $false
$cdbExitBeforeDuration = $false
$gameExitBeforeDuration = $false
$cleanStop = $false
$exitCode = $null
$processExitedUnexpectedly = $false
$runnerFailures = @()
$captureErrors = @()
$frameSamples = New-Object System.Collections.ArrayList
$processSamples = New-Object System.Collections.ArrayList
$edgeHead = @{}
$edgeTail = New-Object System.Collections.ArrayList
$frameIndex = 0
$surfaceBase = [uint64]0
$surfaceBytes = 0
$cleanup = $null
$observations = Parse-SoakLog -LogText ''

try {
    $launch = Start-CdbOnHiddenDesktop -CdbPath $Cdb -Arguments $cdbArgs -WorkingDirectory $WorkDir -DesktopName $desktopName
    $cdbProcess = [System.Diagnostics.Process]::GetProcessById($launch.ProcessId)

    $readyDeadline = $runStart.AddSeconds($ReadyTimeoutSec)
    $overallDeadline = $runStart.AddSeconds($ReadyTimeoutSec + $DurationSec + $EndGraceSec)
    $nextSampleAt = $null

    while ((Get-Date) -lt $overallDeadline) {
        Start-Sleep -Milliseconds 500
        $logText = if (Test-Path -LiteralPath $logPath) { [string](Get-Content -LiteralPath $logPath -Raw) } else { '' }
        $observations = Parse-SoakLog -LogText $logText

        if ($observations.AvObserved) {
            $avObserved = $true
            $runnerFailures += 'access violation row (AV_SURFDUMP) observed in the CDB log'
            break
        }
        if ($observations.SurfaceInvalidObserved) {
            $surfInvalidObserved = $true
            $runnerFailures += 'base template reported SURFDUMP_INVALID for the surface'
            break
        }
        if ($observations.AppRequestQuitObserved) {
            $appRequestQuitObserved = $true
            $runnerFailures += 'game requested App_RequestQuit during the soak'
            break
        }
        $routeStartObserved = @($observations.RouteStarts).Count -eq 1
        $routeEndInLog = @($observations.RouteEnds).Count -eq 1
        if (@($observations.PanUnsafeRows).Count -gt 0) {
            $runnerFailures += 'SOAK_PAN_UNSAFE was observed; the pan route cannot continue safely'
            break
        }

        $cdbProcess.Refresh()
        if ($cdbProcess.HasExited -and -not $routeEndInLog) {
            $cdbExitBeforeDuration = $true
            $runnerFailures += "CDB exited with code $($cdbProcess.ExitCode) before the soak duration completed"
            break
        }

        if (-not $readyObserved) {
            $ready = $observations.ReadyRows | Where-Object { $_.Source -eq 'SOAK_SURFDUMP_READY' } | Select-Object -First 1
            if ($ready) {
                $surfaceBase = Convert-CdbHexToUInt64 -Value $ready.Base
                $surfaceBytes = [int]$ready.Bytes
                $sane = ($surfaceBase -ne 0) -and
                    ($ready.Width -eq 800) -and ($ready.Height -eq 600) -and
                    ($surfaceBytes -eq ($ready.Width * $ready.Height))
                if (-not $sane) {
                    $runnerFailures += "surface ready row failed sanity checks: base=$($ready.Base) size=($($ready.Width),$($ready.Height)) bytes=$surfaceBytes"
                    break
                }
                $readyObserved = $true
                $nextSampleAt = Get-Date
            }
            elseif ((Get-Date) -gt $readyDeadline) {
                $runnerFailures += "no SURFDUMP_READY/SOAK_SURFDUMP_READY row within $ReadyTimeoutSec seconds"
                break
            }
        }

        if ($readyObserved) {
            if (-not $targetProcess) {
                $targetProcess = Get-LaunchedCandidateProcesses -CandidatePath $candidateFull -RunStart $runStart |
                    Sort-Object StartTime -Descending |
                    Select-Object -First 1
                if (-not $targetProcess) {
                    $runnerFailures += 'surface ready was printed but the candidate game process could not be found'
                    break
                }
            }

            $targetProcess.Refresh()
            if ($targetProcess.HasExited -and -not $routeEndInLog) {
                $gameExitBeforeDuration = $true
                $processExitedUnexpectedly = $true
                $exitCode = $targetProcess.ExitCode
                $runnerFailures += "game process exited with code $exitCode before the soak duration completed"
                break
            }

            if (((Get-Date) -ge $nextSampleAt) -and -not $targetProcess.HasExited) {
                $nextSampleAt = (Get-Date).AddSeconds($FrameIntervalSec)
                try {
                    $bytes = Read-TargetSurfaceBytes -ProcessId $targetProcess.Id -BaseAddress $surfaceBase -ByteCount $surfaceBytes
                    $metrics = Get-FrameMetrics -Bytes $bytes
                    $frameIndex++
                    $name = 'frame-{0:d4}' -f $frameIndex
                    [void]$frameSamples.Add([ordered]@{
                        Name = $name
                        Timestamp = (Get-Date).ToString('o')
                        Width = $ready.Width
                        Height = $ready.Height
                        Hash = $metrics.Hash
                        NonblackPercent = $metrics.NonblackPercent
                        UniqueSampleColors = $metrics.UniqueSampleColors
                        CaptureMode = 'hidden-cdb-host-readprocessmemory'
                        RenderEvidence = $true
                    })
                    if ($frameIndex -le $PngEdgeCount) {
                        $edgeHead[$name] = $bytes
                    }
                    [void]$edgeTail.Add(@{ Name = $name; Bytes = $bytes })
                    while ($edgeTail.Count -gt $PngEdgeCount) {
                        $edgeTail.RemoveAt(0)
                    }
                }
                catch {
                    $captureErrors += "surface read failed at frame $($frameIndex + 1): $($_.Exception.Message)"
                    $runnerFailures += 'periodic surface read failed; failing closed'
                    break
                }
                [void]$processSamples.Add((Get-ProcessSnapshot -Process $targetProcess))
            }
        }

        if ($routeEndInLog) {
            $routeEndObserved = $true
            # One final real sample pair after the in-game tick duration completed.
            try {
                $targetProcess.Refresh()
                if (-not $targetProcess.HasExited) {
                    $bytes = Read-TargetSurfaceBytes -ProcessId $targetProcess.Id -BaseAddress $surfaceBase -ByteCount $surfaceBytes
                    $metrics = Get-FrameMetrics -Bytes $bytes
                    $frameIndex++
                    $name = 'frame-{0:d4}' -f $frameIndex
                    [void]$frameSamples.Add([ordered]@{
                        Name = $name
                        Timestamp = (Get-Date).ToString('o')
                        Width = $ready.Width
                        Height = $ready.Height
                        Hash = $metrics.Hash
                        NonblackPercent = $metrics.NonblackPercent
                        UniqueSampleColors = $metrics.UniqueSampleColors
                        CaptureMode = 'hidden-cdb-host-readprocessmemory'
                        RenderEvidence = $true
                    })
                    [void]$edgeTail.Add(@{ Name = $name; Bytes = $bytes })
                    while ($edgeTail.Count -gt $PngEdgeCount) {
                        $edgeTail.RemoveAt(0)
                    }
                    [void]$processSamples.Add((Get-ProcessSnapshot -Process $targetProcess))
                }
            }
            catch {
                $captureErrors += "final surface read failed: $($_.Exception.Message)"
            }
            break
        }
    }

    if (-not $routeEndObserved -and @($runnerFailures).Count -eq 0) {
        $runnerFailures += "SOAK_ROUTE_END was not observed before the overall deadline; in-game tick duration is unproven"
    }
}
catch {
    $runnerFailures += "hidden runtime failed: $($_.Exception.Message)"
}
finally {
    $cleanup = Stop-LaunchedProcesses -CdbPid $(if ($launch) { $launch.ProcessId } else { $null }) -CandidatePath $candidateFull -RunStart $runStart
    $cleanStop = $cleanup.AllTerminated -and $routeEndObserved
    $runnerFailures += @($cleanup.Errors)
    if ($launch -and $launch.ProcessHandle -ne [IntPtr]::Zero) {
        [ClashHiddenSoakNative]::CloseHandle($launch.ProcessHandle) | Out-Null
    }
    if ($launch -and $launch.DesktopHandle -ne [IntPtr]::Zero) {
        [ClashHiddenSoakNative]::CloseDesktop($launch.DesktopHandle) | Out-Null
    }
}

# --- Persist first/last N frames as raw + PNG --------------------------------
$edgeNames = @{}
foreach ($name in $edgeHead.Keys) { $edgeNames[$name] = $edgeHead[$name] }
foreach ($entry in $edgeTail) { $edgeNames[$entry.Name] = $entry.Bytes }
$finalLogText = if (Test-Path -LiteralPath $logPath) { [string](Get-Content -LiteralPath $logPath -Raw) } else { '' }
$observations = Parse-SoakLog -LogText $finalLogText
$runnerFailures += @(Get-RouteValidationFailures -Observations $observations -ExpectedRoute $Route -ExpectedDurationTicks $durationTicks -ExpectedPanIntervalTicks $panIntervalTicks)
$avObserved = $avObserved -or $observations.AvObserved
$surfInvalidObserved = $surfInvalidObserved -or $observations.SurfaceInvalidObserved
$appRequestQuitObserved = $appRequestQuitObserved -or $observations.AppRequestQuitObserved
foreach ($name in ($edgeNames.Keys | Sort-Object)) {
    $rawPath = Join-Path $framesDir ("$name.raw")
    $pngPath = Join-Path $framesDir ("$name.png")
    $pngMetaPath = Join-Path $framesDir ("$name.png.json")
    [System.IO.File]::WriteAllBytes($rawPath, $edgeNames[$name])
    & $pythonExe $converter $rawPath --width $ready.Width --height $ready.Height --output $pngPath --metadata $pngMetaPath --log $logPath
    if ($LASTEXITCODE -ne 0) {
        $captureErrors += "cdb_surface_dump_to_png.py failed for $name with exit code $LASTEXITCODE"
    }
    else {
        foreach ($frame in $frameSamples) {
            if ($frame.Name -eq $name) {
                $frame['RawPath'] = $rawPath
                $frame['PngPath'] = $pngPath
            }
        }
    }
}

$heartbeatCount = @($observations.Heartbeats).Count
$panEventCount = @($observations.PanEvents).Count
$artifactBytes = Get-DirectorySizeBytes -Path $runDir
$proxyText = if (Test-Path -LiteralPath $proxyLogPath) { [string](Get-Content -LiteralPath $proxyLogPath -Raw) } else { '' }
$presentRows = @([regex]::Matches($proxyText, '(?m)^ddraw_surfdump_proxy loaded present_enabled=([01])\s*$'))
$proxyPresentEnabled = $null
if ($presentRows.Count -eq 1) {
    $proxyPresentEnabled = $presentRows[0].Groups[1].Value -eq '1'
}
else {
    $runnerFailures += "expected one proxy load/presentation row, observed $($presentRows.Count)"
}
if ($proxyPresentEnabled -ne $false) {
    $runnerFailures += 'loaded proxy did not prove presentation disabled'
}
if ((Get-FileSha256 -Path $inputFull) -ne $inputSha -or (Get-FileSha256 -Path $candidateFull) -ne $candidateSha -or
    (Get-FileSha256 -Path $proxyDllPath) -ne $proxySha) {
    $runnerFailures += 'original, candidate, or proxy SHA changed during the run'
}
$frameElapsed = Get-SampleElapsedSeconds -Samples @($frameSamples)
$processElapsed = Get-SampleElapsedSeconds -Samples @($processSamples)
$requiredElapsed = [math]::Max(0, $DurationSec - $FrameIntervalSec - 2)
$startMarker = $observations.RouteStarts | Select-Object -First 1
$endMarker = $observations.RouteEnds | Select-Object -First 1

# --- Samples payload for the tested pure-python assembler --------------------
# HONESTY: input_responsiveness is the sentinel and nothing else. This runner
# never measures, imports, or fabricates input metrics on a hidden desktop.
$samples = [ordered]@{
    schema = 'hidden_cdb_host_soak_samples_v1'
    generated_at = (Get-Date).ToString('o')
    executed = $true
    environment = 'hidden_cdb_host'
    route = $Route
    duration_sec = $DurationSec
    frame_interval_sec = $FrameIntervalSec
    pan_interval_sec = if ($Route -eq 'map-pan') { $PanIntervalSec } else { $null }
    duration_ticks = $durationTicks
    stage = $Stage
    protected_stable_stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch'
    input_exe = $inputFull
    input_sha256 = $inputSha
    candidate = $candidateFull
    candidate_sha256 = $candidateSha
    patch_stage_report = $patchStageJson
    workdir = (Get-FullPath -Path $WorkDir)
    output_directory = $runDir
    load_slot = $LoadSlot
    probe_template = (Get-FullPath -Path $ProbeTemplate)
    soak_probe_template = (Get-FullPath -Path $SoakProbeTemplate)
    generated_probe = $generatedProbe
    cdb_log = $logPath
    launch_mode = 'hidden-desktop'
    desktop_name = $desktopName
    frame_read_method = 'host_readprocessmemory'
    surface_base = if ($ready) { '0x{0:x8}' -f $surfaceBase } else { $null }
    ready_marker = if ($ready) {
        [ordered]@{
            source = $ready.Source; redraw_seq = $ready.RedrawSeq
            surface = $ready.Surface; base = $ready.Base
            width = $ready.Width; height = $ready.Height; bytes = $ready.Bytes
        }
    } else { $null }
    route_start_marker = if ($startMarker) {
        [ordered]@{
            route_ticks = $startMarker.RouteTicks; pan = $startMarker.Pan
            player = $startMarker.Player; tick = $startMarker.Tick; game_data = $startMarker.GameData
            scroll_x = $startMarker.ScrollX; scroll_y = $startMarker.ScrollY
        }
    } else { $null }
    route_end_marker = if ($endMarker) {
        [ordered]@{
            route_ticks = $endMarker.RouteTicks; pan = $endMarker.Pan
            hits = $endMarker.Hits; tick_delta = $endMarker.TickDelta; player = $endMarker.Player
            scroll_x = $endMarker.ScrollX; scroll_y = $endMarker.ScrollY
        }
    } else { $null }
    pan_events = @($observations.PanEvents | ForEach-Object {
        [ordered]@{
            phase = $_.Phase; x = $_.X; y = $_.Y; hits = $_.Hits; tick_delta = $_.TickDelta
            delta_x = $_.DeltaX; delta_y = $_.DeltaY
        }
    })
    proxy = [ordered]@{
        used = $presentRows.Count -eq 1
        path = $proxyDllPath; sha256 = $proxySha; build_manifest = $proxyManifestPath
        build_log = $proxyBuildLogPath; log = $proxyLogPath; present_enabled = $proxyPresentEnabled
    }
    cleanup = [ordered]@{
        game_stopped = $cleanup.GameStopped; cdb_stopped = $cleanup.CdbStopped
        errors = @($cleanup.Errors); stopped_process_ids = @($cleanup.StoppedProcessIds)
    }
    elapsed_coverage = [ordered]@{
        formula = 'duration_sec - sample_interval_sec - 2'
        required_sec = $requiredElapsed; frame_elapsed_sec = $frameElapsed; process_elapsed_sec = $processElapsed
        passed = $null -ne $frameElapsed -and $null -ne $processElapsed -and
            $frameElapsed -ge $requiredElapsed -and $processElapsed -ge $requiredElapsed
    }
    surface = if ($ready) {
        [ordered]@{
            Base = $ready.Base
            Width = $ready.Width
            Height = $ready.Height
            Bytes = $ready.Bytes
            Source = $ready.Source
        }
    } else { $null }
    ready_observed = $readyObserved
    soak_route_start_observed = $routeStartObserved
    soak_route_end_observed = $routeEndObserved
    heartbeat_count = $heartbeatCount
    pan_event_count = $panEventCount
    av_observed = $avObserved
    surface_invalid_observed = $surfInvalidObserved
    app_request_quit_observed = $appRequestQuitObserved
    cdb_exit_before_duration = $cdbExitBeforeDuration
    game_exit_before_duration = $gameExitBeforeDuration
    clean_stop = $cleanStop
    clean_stop_mechanism = 'harness_stop_after_route_end'
    exit_code = $exitCode
    process_exited_unexpectedly = $processExitedUnexpectedly
    input_responsiveness = 'not_applicable_hidden'
    runner_failures = @($runnerFailures)
    capture_errors = @($captureErrors)
    frame_samples = @($frameSamples)
    process_samples = @($processSamples)
    artifact_bytes = $artifactBytes
    max_artifact_mb = $MaxArtifactMB
    max_working_set_growth_mb = $MaxWorkingSetGrowthMB
    max_private_memory_growth_mb = $MaxPrivateMemoryGrowthMB
    max_handle_growth = $MaxHandleGrowth
    report_json = $runReportJson
    report_markdown = $runReportMarkdown
}
$samples | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $samplesJson -Encoding ASCII

& $pythonExe $assembler $samplesJson --write-json $runReportJson --write-markdown $runReportMarkdown
if ($LASTEXITCODE -ne 0) {
    throw "hidden_soak_report_assembler.py failed with exit code $LASTEXITCODE"
}

& $pythonExe $grader $runReportJson --hidden --write-json $runGuardJson --write-markdown $runGuardMarkdown
if ($LASTEXITCODE -ne 0) {
    throw "hd_soak_report.py failed with exit code $LASTEXITCODE"
}
$report = Get-Content -LiteralPath $runReportJson -Raw | ConvertFrom-Json
$guard = Get-Content -LiteralPath $runGuardJson -Raw | ConvertFrom-Json
Publish-CanonicalArtifact -Source $runReportJson -Destination $publishReportJson
Publish-CanonicalArtifact -Source $runReportMarkdown -Destination $publishReportMarkdown
Publish-CanonicalArtifact -Source $runGuardJson -Destination $publishGuardJson
Publish-CanonicalArtifact -Source $runGuardMarkdown -Destination $publishGuardMarkdown
Write-Host "Hidden soak run directory: $runDir"
Write-Host "Environment: $($report.environment)"
Write-Host "Route/duration: $Route / $DurationSec sec"
Write-Host "Passed: $($report.passed)"
if (-not $report.passed) {
    foreach ($failure in @($report.failures)) {
        Write-Host "  failure: $failure"
    }
}
Write-Host "Report: $runReportJson"
Write-Host "Summary: $runReportMarkdown"
Write-Host "Shared guard passed: $($guard.overall)"
if ($Json) {
    [ordered]@{
        environment = 'hidden_cdb_host'; executed = $true
        passed = [bool]($report.passed -and $guard.overall)
        report_json = $runReportJson; guard_json = $runGuardJson
        failures = @($report.failures) + @($guard.failures)
    } | ConvertTo-Json -Depth 6
}
if (-not $report.passed -or -not $guard.overall) {
    exit 1
}
