param(
    [string]$InputExe = 'C:\Clash\clash95.exe',
    [string]$WorkDir = 'C:\Clash',
    [string]$Cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe',
    [string]$Python = 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [string]$Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch',
    [string]$CandidateName = '',
    [string]$CandidateDir = '',
    [switch]$UseDdrawProxy,
    [string]$DdrawProxyDll = '',
    [string]$DdrawProxyBuildScript = (Join-Path (Join-Path $PSScriptRoot '..\build') 'build_ddraw_surfdump_proxy.ps1'),
    [string]$OutRoot = (Join-Path (Join-Path $PSScriptRoot '..\..') 'captures'),
    [string]$ProbeTemplate = (Join-Path (Join-Path $PSScriptRoot '..\..') 'probes/cdb/render/clash95_surface_dump_probe.cdb'),
    [string]$ExtraProbeTemplate = '',
    [int]$RunSeconds = 90,
    [switch]$NoSkipStartAnims,
    [switch]$FastForwardStartAnims,
    [switch]$ForceVisibleEdges,
    [switch]$PostOwnerForceVisibleSeven,
    [switch]$UseCdbWriteMem,
    [switch]$AllowVisibleDesktop,
    [switch]$SkipMapValidation,
    [switch]$RequireGameplay
)

$ErrorActionPreference = 'Stop'

if ($PostOwnerForceVisibleSeven -and $SkipMapValidation) {
    throw '-PostOwnerForceVisibleSeven requires map validation; do not use -SkipMapValidation.'
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
        [datetime]$RunStart
    )

    $toStop = @()
    if ($CdbPid) {
        $cdbProcess = Get-Process -Id $CdbPid -ErrorAction SilentlyContinue
        if ($cdbProcess) {
            $toStop += $cdbProcess
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

foreach ($path in @($InputExe, $WorkDir, $Cdb, $ProbeTemplate)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required path was not found: $path"
    }
}
if ($ExtraProbeTemplate -and -not (Test-Path -LiteralPath $ExtraProbeTemplate)) {
    throw "Extra CDB probe template was not found: $ExtraProbeTemplate"
}

$pythonExe = Resolve-PythonPath -Requested $Python
$patcher = Join-Path (Join-Path $PSScriptRoot '..\..') 'patch_clash95_hd.py'
$converter = Join-Path (Join-Path $PSScriptRoot '..\..') 'tools\cdb_surface_dump_to_png.py'
$coverageTool = Join-Path (Join-Path $PSScriptRoot '..\..') 'tools\map_tile_coverage.py'
$visibilityTool = Join-Path (Join-Path $PSScriptRoot '..\..') 'tools\visibility_coverage.py'
$forcedVisibleTool = Join-Path (Join-Path $PSScriptRoot '..\..') 'tools\forced_visible_summary.py'
$postOwnerForcedVisibleTool = Join-Path (Join-Path $PSScriptRoot '..\..') 'tools\post_owner_forced_visible_summary.py'
foreach ($path in @($patcher, $converter, $coverageTool, $visibilityTool, $forcedVisibleTool, $postOwnerForcedVisibleTool)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required helper was not found: $path"
    }
}
if ($UseDdrawProxy -and -not (Test-Path -LiteralPath $DdrawProxyBuildScript)) {
    throw "DirectDraw proxy build script was not found: $DdrawProxyBuildScript"
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
New-Item -ItemType Directory -Path $runDir -Force | Out-Null
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
    Remove-Item -LiteralPath $proxyLogPath -Force -ErrorAction SilentlyContinue
}

$inputSha = Get-FileSha256 -Path $inputFull
& $pythonExe $patcher --input $inputFull --output $candidateFull --stage $Stage
$patchExit = $LASTEXITCODE
if ($patchExit -ne 0) {
    throw "patch_clash95_hd.py failed with exit code $patchExit"
}
$candidateSha = Get-FileSha256 -Path $candidateFull

$probeText = Get-Content -LiteralPath $ProbeTemplate -Raw
if ($PostOwnerForceVisibleSeven -and -not $ExtraProbeTemplate) {
    throw '-PostOwnerForceVisibleSeven requires -ExtraProbeTemplate with the post-owner visibility probe.'
}
if ($ExtraProbeTemplate) {
    $extraProbeText = (Get-Content -LiteralPath $ExtraProbeTemplate -Raw).Trim()
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
$probeText = $probeText.Replace('__VISIBILITY_PLAYGAME_ACTION__', $visibilityPlayGameAction)
$visibilityRedrawAction = if ($ForceVisibleEdges) {
    'ed @$t10+0n140008 0n10; ed @$t10+0n140012 0n17; ed 00544cfc 00004b00; ed 00544d00 00003680; eb 005451c0 00; ed 00544d04 0; .if (@$t13 < 0n4) { .printf \"SURFDUMP_FORCE_VIEWPORT scroll=(%d,%d) mouse=(%d,%d) timing=redraw\\n\", poi(@$t10+0n140008), poi(@$t10+0n140012), poi(00544cfc)>>by(0054512c), poi(00544d00)>>by(0054512c); };'
}
else {
    ''
}
$probeText = $probeText.Replace('__VISIBILITY_PATCH_ACTION__', $visibilityRedrawAction)
$surfaceDumpAction = if ($UseCdbWriteMem) {
    '.writemem ' + (Get-CdbFileToken -Path $rawPath) + ' @$t16 L@$t17; .echo SURFDUMP_DONE; q;'
}
else {
    '.echo SURFDUMP_HOST_READY; gc'
}
$probeText = $probeText.Replace('__SURFACE_DUMP_ACTION__', $surfaceDumpAction)
$probeText = $probeText.Replace('__RAW_PATH__', (Get-CdbFileToken -Path $rawPath))
Set-Content -LiteralPath $generatedProbe -Value $probeText -Encoding ASCII

$runStart = Get-Date
$desktopName = "ClashSurfaceDump_$($stamp -replace '[^0-9A-Za-z_]', '_')"
$cdbCommand = '$$><' + $generatedProbe
$cdbArgs = @('-hd', '-logo', $logPath, '-c', $cdbCommand, $candidateFull)
$launch = $null
$cdbExitCode = $null
$timedOut = $false
$runtimeError = $null
$timeoutStackSaved = $false
$launchMode = 'hidden-desktop'
$stoppedAfterDump = $false
$hostDumpedMemory = $false
$hostDumpError = $null
$dumpMethod = if ($UseCdbWriteMem) { 'cdb-writemem' } else { 'host-readprocessmemory' }

try {
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
            if ($currentReady -and -not (Test-Path -LiteralPath $rawPath)) {
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
            $stoppedAfterDump = $true
            Stop-LaunchedProcesses -CdbPid $launch.ProcessId -CandidatePath $candidateFull -RunStart $runStart
            Start-Sleep -Milliseconds 500
            $cdbProcess.Refresh()
            break
        }
    }

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
finally {
    Stop-LaunchedProcesses -CdbPid $(if ($launch) { $launch.ProcessId } else { $null }) -CandidatePath $candidateFull -RunStart $runStart
    if ($launch -and $launch.ProcessHandle -ne [IntPtr]::Zero) {
        [ClashSurfaceDumpNative]::CloseHandle($launch.ProcessHandle) | Out-Null
    }
    if ($launch -and $launch.DesktopHandle -ne [IntPtr]::Zero) {
        [ClashSurfaceDumpNative]::CloseDesktop($launch.DesktopHandle) | Out-Null
    }
}

$ready = Parse-SurfaceDumpReady -LogPath $logPath
$logText = if (Test-Path -LiteralPath $logPath) { Get-Content -LiteralPath $logPath -Raw } else { '' }
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

if (-not $ready -or -not $dumpDone -or -not $rawExists) {
    $failureReason = if ($runtimeError) {
        $runtimeError
    }
    elseif ($appRequestQuit) {
        'game requested App_RequestQuit before surface dump'
    }
    else {
        'surface dump was not completed'
    }
    $summary = [pscustomobject]@{
        Passed = $false
        Error = $failureReason
        LaunchMode = $launchMode
        TimedOut = $timedOut
        StoppedAfterDump = $stoppedAfterDump
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
        UseDdrawProxy = [bool]$UseDdrawProxy
        NoSkipStartAnims = [bool]$NoSkipStartAnims
        FastForwardStartAnims = [bool]$FastForwardStartAnims
        ForceVisibleEdges = [bool]$ForceVisibleEdges
        PostOwnerForceVisibleSeven = [bool]$PostOwnerForceVisibleSeven
        SkipMapValidation = [bool]$SkipMapValidation
        DdrawProxyDll = $proxyDllPath
        DdrawProxySha256 = $proxySha
        DdrawProxyLog = $proxyLogPath
        DdrawProxyManifest = $proxyManifestPath
        ProbeTemplate = (Get-FullPath -Path $ProbeTemplate)
        ExtraProbeTemplate = if ($ExtraProbeTemplate) { Get-FullPath -Path $ExtraProbeTemplate } else { $null }
        GeneratedProbe = $generatedProbe
        Stage = $Stage
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
        "- Launch mode: $launchMode"
        "- Timed out: $timedOut"
        "- Stopped after dump: $stoppedAfterDump"
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
        "- DirectDraw proxy DLL: $(if ($proxyDllPath) { $proxyDllPath } else { 'not used' })"
        "- DirectDraw proxy log: $(if ($proxyLogPath) { $proxyLogPath } else { 'not used' })"
        "- Generated probe: $generatedProbe"
        "- Log: $logPath"
        "- Timeout stack: $(if ($timeoutStackSaved) { $timeoutStackLog } else { 'not captured' })"
    ) | Set-Content -LiteralPath $runSummary -Encoding ASCII
    throw "Surface dump failed. See $runSummary"
}

if ($rawBytes -lt $ready.Bytes) {
    throw "Surface dump is shorter than expected: expected $($ready.Bytes), found $rawBytes"
}

& $pythonExe $converter $rawPath --width $ready.Width --height $ready.Height --output $pngPath --metadata $pngMetaPath --log $logPath
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
        $forcedVisibleOutput = & $pythonExe $forcedVisibleTool $coverageJson --log $logPath --write-json $forcedVisibleJson --require-forced-visible 2>&1
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
$validationFailure = if ($postOwnerForcedVisibleFailure) {
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
    Error = $validationFailure
    LaunchMode = $launchMode
    HiddenDesktop = (-not $AllowVisibleDesktop)
    DesktopName = $launch.DesktopName
    RunDir = $runDir
    Stage = $Stage
    InputExe = $inputFull
    InputSha256 = $inputSha
    CandidatePath = $candidateFull
    CandidateDir = (Get-FullPath -Path $CandidateDir)
    CandidateSha256 = $candidateSha
    UseDdrawProxy = [bool]$UseDdrawProxy
    NoSkipStartAnims = [bool]$NoSkipStartAnims
    FastForwardStartAnims = [bool]$FastForwardStartAnims
    ForceVisibleEdges = [bool]$ForceVisibleEdges
    PostOwnerForceVisibleSeven = [bool]$PostOwnerForceVisibleSeven
    SkipMapValidation = [bool]$SkipMapValidation
    DdrawProxyDll = $proxyDllPath
    DdrawProxySha256 = $proxySha
    DdrawProxyLog = $proxyLogPath
    DdrawProxyManifest = $proxyManifestPath
    Cdb = (Get-FullPath -Path $Cdb)
    CdbExitCode = $cdbExitCode
    TimedOut = $timedOut
    StoppedAfterDump = $stoppedAfterDump
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
    CoverageJson = $coverageJson
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
    "- Dump method: $dumpMethod"
    "- Host dumped memory: $hostDumpedMemory"
    "- Stage: $Stage"
    "- Candidate: $candidateFull"
    "- Candidate SHA-256: $candidateSha"
    "- DirectDraw proxy: $([bool]$UseDdrawProxy)"
    "- No skip start animations: $([bool]$NoSkipStartAnims)"
    "- Fast-forward start animations: $([bool]$FastForwardStartAnims)"
    "- Force visible edges: $([bool]$ForceVisibleEdges)"
    "- Post-owner force visible seven: $([bool]$PostOwnerForceVisibleSeven)"
    "- Map validation skipped: $([bool]$SkipMapValidation)"
    "- Extra probe template: $(if ($ExtraProbeTemplate) { Get-FullPath -Path $ExtraProbeTemplate } else { 'not used' })"
    "- DirectDraw proxy DLL: $(if ($proxyDllPath) { $proxyDllPath } else { 'not used' })"
    "- DirectDraw proxy log: $(if ($proxyLogPath) { $proxyLogPath } else { 'not used' })"
    "- Surface: $($ready.Width)x$($ready.Height), base=$($ready.Base), bytes=$($ready.Bytes)"
    "- Raw: $rawPath"
    "- PNG: $pngPath"
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

Write-Host "CDB surface dump passed: $runDir"
Write-Host "PNG: $pngPath"
Write-Host "Summary: $runSummary"
