param(
    [string]$Exe = 'C:\Clash\clash95_hd_mousedynorigin_menusurface_scrollclamp_20260423.exe',
    [string]$WorkDir = 'C:\Clash',
    [string]$Python = 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [string]$OutRoot = (Join-Path $PSScriptRoot 'captures'),
    [string]$Points = '300,218;320,166;400,226',
    [ValidateSet('load-slot0', 'campaign-start', 'custom', 'menu-only')]
    [string]$Route = 'load-slot0',
    [int]$RunSeconds = 8,
    [int]$WindowTimeoutSec = 12,
    [int]$SkipPulses = 4,
    [int]$IntroSkipClicks = 8,
    [int]$IntroMaxRounds = 8,
    [int]$IntroRoundWaitMs = 700,
    [int]$SkipIntervalMs = 500,
    [int]$PostIntroWaitSec = 4,
    [int]$RouteStepWaitMs = 1400,
    [int]$ClickHoldMs = 300,
    [int]$ClickRepeat = 2,
    [int]$ClickIntervalMs = 900,
    [ValidateSet('setcursor', 'sendinput-absolute', 'sendinput-relative', 'auto', 'none')]
    [string]$MoveMode = 'auto',
    [ValidateSet('sendinput', 'postmessage', 'both')]
    [string]$ClickMode = 'sendinput',
    [int]$MoveWindowX = 80,
    [int]$MoveWindowY = 80,
    [switch]$NoGameplayCheck,
    [switch]$KeepOpen
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class ClashVisualSmokeWin32 {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct POINT {
        public int X;
        public int Y;
    }

    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool GetClientRect(IntPtr hWnd, out RECT rect);

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);

    [DllImport("user32.dll")]
    public static extern bool ClientToScreen(IntPtr hWnd, ref POINT point);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool BringWindowToTop(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);

    [DllImport("user32.dll")]
    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);

    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();

    [DllImport("user32.dll")]
    public static extern IntPtr WindowFromPoint(POINT point);

    [DllImport("user32.dll")]
    public static extern IntPtr GetAncestor(IntPtr hWnd, uint gaFlags);

    public static IntPtr FindVisibleWindowForProcess(uint processId) {
        IntPtr found = IntPtr.Zero;
        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {
            uint windowProcessId;
            GetWindowThreadProcessId(hWnd, out windowProcessId);
            if (windowProcessId == processId && IsWindowVisible(hWnd)) {
                RECT rect;
                if (GetClientRect(hWnd, out rect) && rect.Right > rect.Left && rect.Bottom > rect.Top) {
                    found = hWnd;
                    return false;
                }
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }
}
'@

function Stop-ClashProcesses {
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ProcessName -like 'clash95*' -or
            $_.ProcessName -eq 'cdb' -or
            ($_.Path -and $_.Path -like (Join-Path $WorkDir 'clash95*.exe'))
        } |
        Stop-Process -Force -ErrorAction SilentlyContinue
}

function Get-WindowHandleForProcess {
    param([System.Diagnostics.Process]$Process)

    $Process.Refresh()
    if ($Process.MainWindowHandle -ne [IntPtr]::Zero) {
        return $Process.MainWindowHandle
    }
    return [ClashVisualSmokeWin32]::FindVisibleWindowForProcess([uint32]$Process.Id)
}

function Wait-ClashWindow {
    param(
        [System.Diagnostics.Process]$Process,
        [int]$TimeoutSec
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ($Process.HasExited) {
            throw "Process exited before creating a window: $($Process.Id)"
        }
        $handle = Get-WindowHandleForProcess -Process $Process
        if ($handle -ne [IntPtr]::Zero) {
            return $handle
        }
        Start-Sleep -Milliseconds 200
    }
    throw "Timed out waiting for a visible Clash95 window"
}

function Move-And-RaiseWindow {
    param([IntPtr]$Handle)

    $rect = New-Object ClashVisualSmokeWin32+RECT
    if ([ClashVisualSmokeWin32]::GetWindowRect($Handle, [ref]$rect)) {
        $windowWidth = $rect.Right - $rect.Left
        $windowHeight = $rect.Bottom - $rect.Top
        if ($windowWidth -gt 0 -and $windowHeight -gt 0) {
            [ClashVisualSmokeWin32]::MoveWindow($Handle, $MoveWindowX, $MoveWindowY, $windowWidth, $windowHeight, $true) | Out-Null
        }
    }

    $hwndTopmost = [IntPtr]::new(-1)
    $swpNoMove = 0x0002
    $swpNoSize = 0x0001
    $swpShowWindow = 0x0040
    [ClashVisualSmokeWin32]::ShowWindow($Handle, 5) | Out-Null
    [ClashVisualSmokeWin32]::SetWindowPos($Handle, $hwndTopmost, 0, 0, 0, 0, $swpNoMove -bor $swpNoSize -bor $swpShowWindow) | Out-Null
    [ClashVisualSmokeWin32]::BringWindowToTop($Handle) | Out-Null
    [ClashVisualSmokeWin32]::SetForegroundWindow($Handle) | Out-Null
    Start-Sleep -Milliseconds 350
}

function Get-ClientGeometry {
    param([IntPtr]$Handle)

    $rect = New-Object ClashVisualSmokeWin32+RECT
    if (-not [ClashVisualSmokeWin32]::GetClientRect($Handle, [ref]$rect)) {
        throw "GetClientRect failed"
    }
    $origin = New-Object ClashVisualSmokeWin32+POINT
    $origin.X = 0
    $origin.Y = 0
    if (-not [ClashVisualSmokeWin32]::ClientToScreen($Handle, [ref]$origin)) {
        throw "ClientToScreen failed"
    }
    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top
    if ($width -le 0 -or $height -le 0) {
        throw "Invalid client size ${width}x${height}"
    }

    [pscustomobject]@{
        OriginX = $origin.X
        OriginY = $origin.Y
        Width = $width
        Height = $height
    }
}

function Test-ClientCenterIsTarget {
    param(
        [IntPtr]$Handle,
        [object]$Geometry
    )

    $point = New-Object ClashVisualSmokeWin32+POINT
    $point.X = $Geometry.OriginX + [int][math]::Floor($Geometry.Width / 2)
    $point.Y = $Geometry.OriginY + [int][math]::Floor($Geometry.Height / 2)
    $window = [ClashVisualSmokeWin32]::WindowFromPoint($point)
    $root = [ClashVisualSmokeWin32]::GetAncestor($window, 2)
    [pscustomobject]@{
        MatchesTarget = ($root -eq $Handle -or $window -eq $Handle)
        WindowHwnd = ("0x{0}" -f $window.ToInt64().ToString('X'))
        RootHwnd = ("0x{0}" -f $root.ToInt64().ToString('X'))
    }
}

function Get-FrameSampleStats {
    param([string]$Path)

    $bitmap = [System.Drawing.Bitmap]::FromFile($Path)
    try {
        $step = 4
        $samples = 0
        $nonblack = 0
        $lumaSum = 0.0
        $minX = $bitmap.Width
        $minY = $bitmap.Height
        $maxX = -1
        $maxY = -1
        for ($y = 0; $y -lt $bitmap.Height; $y += $step) {
            for ($x = 0; $x -lt $bitmap.Width; $x += $step) {
                $pixel = $bitmap.GetPixel($x, $y)
                $luma = (0.2126 * $pixel.R) + (0.7152 * $pixel.G) + (0.0722 * $pixel.B)
                $lumaSum += $luma
                $samples++
                if ([math]::Max($pixel.R, [math]::Max($pixel.G, $pixel.B)) -gt 12) {
                    $nonblack++
                    $minX = [math]::Min($minX, $x)
                    $minY = [math]::Min($minY, $y)
                    $maxX = [math]::Max($maxX, $x)
                    $maxY = [math]::Max($maxY, $y)
                }
            }
        }
        [pscustomobject]@{
            Width = $bitmap.Width
            Height = $bitmap.Height
            Samples = $samples
            NonblackSamples = $nonblack
            NonblackPercent = if ($samples) { [math]::Round(($nonblack * 100.0) / $samples, 3) } else { 0.0 }
            MeanLuma = if ($samples) { [math]::Round($lumaSum / $samples, 3) } else { 0.0 }
            NonblackBounds = if ($nonblack) {
                [pscustomobject]@{
                    X = $minX
                    Y = $minY
                    Right = $maxX
                    Bottom = $maxY
                    Width = $maxX - $minX + 1
                    Height = $maxY - $minY + 1
                }
            } else {
                $null
            }
        }
    } finally {
        $bitmap.Dispose()
    }
}

function Invoke-GameplayFrameCheck {
    param(
        [string]$Path,
        [string]$Json
    )

    $coverageTool = Join-Path $PSScriptRoot 'tools\map_tile_coverage.py'
    if ($NoGameplayCheck -or -not (Test-Path -LiteralPath $coverageTool)) {
        return [pscustomobject]@{
            Attempted = $false
            ExitCode = $null
            Json = $null
            GameplayFrameLikely = $null
            Warnings = @('gameplay-check-disabled')
            Summary = $null
        }
    }

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & $Python $coverageTool $Path --require-gameplay --write-json $Json 2>&1
        $exitCode = $LASTEXITCODE
    } catch {
        $output = @($_.ToString())
        $exitCode = 1
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $logPath = [System.IO.Path]::ChangeExtension($Json, '.log')
    $output | Set-Content -LiteralPath $logPath -Encoding ASCII

    $report = $null
    $image = $null
    if (Test-Path -LiteralPath $Json) {
        $report = Get-Content -LiteralPath $Json -Raw | ConvertFrom-Json
        if ($report -and $report.images) {
            $image = @($report.images)[0]
        }
    }

    [pscustomobject]@{
        Attempted = $true
        ExitCode = $exitCode
        Json = if (Test-Path -LiteralPath $Json) { $Json } else { $null }
        Log = $logPath
        GameplayFrameLikely = if ($image) { [bool]$image.frame_check.gameplay_frame_likely } else { $false }
        Warnings = if ($image) { @($image.frame_check.warnings) } else { @('gameplay-check-json-missing') }
        Summary = if ($image) { $image.summary } else { $null }
    }
}

function Get-FrameState {
    param(
        [string]$Path,
        [string]$Name,
        [string]$OutDir
    )

    $stats = Get-FrameSampleStats -Path $Path
    $safeName = ($Name -replace '[^0-9A-Za-z_.-]', '-')
    $gameplay = Invoke-GameplayFrameCheck -Path $Path -Json (Join-Path $OutDir "$safeName-gameplay-check.json")
    $state = 'unknown'
    $reason = 'no strong classifier matched'

    if ($stats.Width -lt 600 -or $stats.Height -lt 450) {
        $state = 'modal-or-dialog-likely'
        $reason = 'capture is smaller than the expected game client'
    } elseif ($gameplay.GameplayFrameLikely) {
        $state = 'gameplay-likely'
        $reason = 'tile coverage gameplay gate passed'
    } elseif ($stats.NonblackPercent -lt 20.0) {
        $state = 'intro-or-story-likely'
        $reason = 'low nonblack coverage'
    } elseif (
        $stats.NonblackPercent -ge 40.0 -and
        $stats.NonblackBounds -and
        $stats.NonblackBounds.Width -ge 620 -and
        $stats.NonblackBounds.Height -ge 430
    ) {
        $state = 'main-menu-or-dialog-likely'
        $reason = 'large non-gameplay frame with broad nonblack bounds'
    } else {
        $state = 'load-or-transition-likely'
        $reason = 'non-gameplay frame with intermediate coverage'
    }

    [pscustomobject]@{
        Name = $Name
        Path = $Path
        State = $state
        Reason = $reason
        Stats = $stats
        GameplayCheck = $gameplay
    }
}

function Save-StateFrame {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Name,
        [string]$Path,
        [string]$OutDir
    )

    try {
        $frame = Save-CleanClientFrame -Process $Process -Path $Path
        $state = Get-FrameState -Path $Path -Name $Name -OutDir $OutDir
    } catch {
        return [pscustomobject]@{
            Name = $Name
            Frame = $null
            State = 'capture-failed'
            Reason = $_.Exception.Message
            NonblackPercent = $null
            MeanLuma = $null
            NonblackBounds = $null
            GameplayFrameLikely = $false
            GameplayWarnings = @('capture-failed')
            GameplayCheckExitCode = $null
            GameplayCheckJson = $null
        }
    }
    [pscustomobject]@{
        Name = $Name
        Frame = $frame
        State = $state.State
        Reason = $state.Reason
        NonblackPercent = $state.Stats.NonblackPercent
        MeanLuma = $state.Stats.MeanLuma
        NonblackBounds = $state.Stats.NonblackBounds
        GameplayFrameLikely = ($state.State -eq 'gameplay-likely')
        GameplayWarnings = @($state.GameplayCheck.Warnings)
        GameplayCheckExitCode = $state.GameplayCheck.ExitCode
        GameplayCheckJson = $state.GameplayCheck.Json
    }
}

function Get-RouteSteps {
    param(
        [string]$RouteName,
        [string]$CustomPoints
    )

    switch ($RouteName) {
        'load-slot0' {
            return @(
                [pscustomobject]@{ Name = 'neutral-menu'; Points = '400,300'; WaitMs = $RouteStepWaitMs },
                [pscustomobject]@{ Name = 'load-button'; Points = '300,218'; WaitMs = $RouteStepWaitMs },
                [pscustomobject]@{ Name = 'load-slot0'; Points = '320,166'; WaitMs = $RouteStepWaitMs },
                [pscustomobject]@{ Name = 'confirm-load'; Points = '400,226'; WaitMs = [math]::Max($RouteStepWaitMs, 2200) }
            )
        }
        'campaign-start' {
            return @(
                [pscustomobject]@{ Name = 'campaign-button'; Points = '320,245'; WaitMs = $RouteStepWaitMs },
                [pscustomobject]@{ Name = 'campaign-select'; Points = '448,245'; WaitMs = $RouteStepWaitMs },
                [pscustomobject]@{ Name = 'campaign-confirm'; Points = '648,49;760,201'; WaitMs = [math]::Max($RouteStepWaitMs, 2200) }
            )
        }
        'custom' {
            return @([pscustomobject]@{ Name = 'custom-points'; Points = $CustomPoints; WaitMs = [math]::Max($RouteStepWaitMs, 2200) })
        }
        'menu-only' {
            return @()
        }
        default {
            throw "Unknown route: $RouteName"
        }
    }
}

function Save-CleanClientFrame {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Path
    )

    $captureScript = Join-Path $PSScriptRoot 'capture_clash_client_frame.ps1'
    if (-not (Test-Path -LiteralPath $captureScript)) {
        throw "Capture helper was not found: $captureScript"
    }
    $metaPath = "$Path.json"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $captureScript -TargetProcessId $Process.Id -Path $Path -Json $metaPath -WindowTimeoutSec $WindowTimeoutSec | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "capture_clash_client_frame.ps1 failed with exit code $LASTEXITCODE"
    }
    Get-Content -LiteralPath $metaPath -Raw | ConvertFrom-Json
}

function Invoke-MousePath {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Json,
        [string]$PathPoints,
        [switch]$Click,
        [int]$SpacePulses = 0,
        [switch]$AllowUnverified
    )

    $mouseTool = Join-Path $PSScriptRoot 'tools\mouse_path_probe.py'
    $args = @(
        $mouseTool,
        '--pid', $Process.Id,
        '--workdir', $WorkDir,
        '--move-window', $MoveWindowX, $MoveWindowY,
        '--settle-sec', '0.5',
        '--space-pulses', $SpacePulses,
        '--space-interval-ms', $SkipIntervalMs,
        '--interval-ms', $ClickIntervalMs,
        '--move-mode', $MoveMode,
        '--points', $PathPoints,
        '--json', $Json
    )
    if ($Click) {
        $args += @('--click', '--click-mode', $ClickMode, '--click-hold-ms', $ClickHoldMs, '--click-repeat', $ClickRepeat)
    }
    $probeLog = [System.IO.Path]::ChangeExtension($Json, '.log')
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $probeOutput = & $Python @args 2>&1
        $exitCode = $LASTEXITCODE
    } catch {
        $probeOutput = @($_.ToString())
        $exitCode = 1
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $probeOutput | Set-Content -LiteralPath $probeLog -Encoding ASCII
    if (-not (Test-Path -LiteralPath $Json)) {
        if ($AllowUnverified) {
            return [pscustomobject]@{
                path_verified = $false
                click_path_verified = $false
                max_abs_error = $null
                max_sample_abs_error = $null
                ProbeExitCode = $exitCode
                ProbeLog = $probeLog
                ProbeError = "mouse_path_probe.py did not write JSON"
            }
        }
        throw "mouse_path_probe.py failed with exit code $exitCode"
    }
    $result = Get-Content -LiteralPath $Json -Raw | ConvertFrom-Json
    $result | Add-Member -NotePropertyName ProbeExitCode -NotePropertyValue $exitCode -Force
    $result | Add-Member -NotePropertyName ProbeLog -NotePropertyValue $probeLog -Force
    $result
}

function Start-ClashProcessWithRetry {
    param(
        [string]$Path,
        [string]$Directory,
        [int]$Attempts = 5,
        [int]$DelayMs = 700
    )

    $errors = @()
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            if (-not (Test-Path -LiteralPath $Path)) {
                throw "Executable is not visible yet: $Path"
            }
            $process = Start-Process -FilePath $Path -WorkingDirectory $Directory -PassThru
            return [pscustomobject]@{
                Process = $process
                Attempts = $attempt
                Errors = $errors
            }
        } catch {
            $errors += [pscustomobject]@{
                Attempt = $attempt
                Error = $_.Exception.Message
            }
            if ($attempt -eq $Attempts) {
                throw
            }
            Start-Sleep -Milliseconds $DelayMs
        }
    }
}

foreach ($path in @($Exe, $WorkDir, $Python)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required path was not found: $path"
    }
}
$mousePath = Join-Path $PSScriptRoot 'tools\mouse_path_probe.py'
if (-not (Test-Path -LiteralPath $mousePath)) {
    throw "Required path was not found: $mousePath"
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$outDir = Join-Path $OutRoot "visual-smoke-$stamp"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$introSkipPoints = @(for ($i = 0; $i -lt $IntroSkipClicks; $i++) { '400,300' }) -join ';'

$process = $null
$result = $null
$launchInfo = $null
$scriptError = $null
Stop-ClashProcesses
try {
    $launchInfo = Start-ClashProcessWithRetry -Path $Exe -Directory $WorkDir
    $process = $launchInfo.Process
    Wait-ClashWindow -Process $process -TimeoutSec $WindowTimeoutSec | Out-Null

    $readinessFrames = @()
    $introProbeRows = @()
    $menuPath = $null
    $menuMouseJson = $null
    $mainMenuReady = $false
    for ($round = 0; $round -lt $IntroMaxRounds; $round++) {
        $menuMouseJson = Join-Path $outDir ("intro-skip-{0:D2}.json" -f $round)
        $menuPath = Invoke-MousePath -Process $process -Json $menuMouseJson -PathPoints $introSkipPoints -Click -SpacePulses $SkipPulses -AllowUnverified
        Start-Sleep -Milliseconds $IntroRoundWaitMs
        $readiness = Save-StateFrame `
            -Process $process `
            -Name ("readiness-{0:D2}" -f $round) `
            -Path (Join-Path $outDir ("readiness-{0:D2}.png" -f $round)) `
            -OutDir $outDir
        $readinessFrames += $readiness
        $introProbeRows += [pscustomobject]@{
            Round = $round
            Json = $menuMouseJson
            PathVerified = $menuPath.path_verified
            ClickPathVerified = $menuPath.click_path_verified
            ProbeExitCode = $menuPath.ProbeExitCode
            FrameState = $readiness.State
            GameplayFrameLikely = $readiness.GameplayFrameLikely
        }
        if ($readiness.State -eq 'main-menu-or-dialog-likely' -or $readiness.State -eq 'gameplay-likely') {
            $mainMenuReady = $true
            break
        }
    }

    Start-Sleep -Seconds $PostIntroWaitSec
    $menuFrameState = Save-StateFrame -Process $process -Name 'menu-ready' -Path (Join-Path $outDir 'menu.png') -OutDir $outDir

    $routeSteps = Get-RouteSteps -RouteName $Route -CustomPoints $Points
    $routeRows = @()
    $lastRoutePath = $null
    $lastRouteJson = $null
    foreach ($step in $routeSteps) {
        if ($menuFrameState.State -eq 'gameplay-likely') {
            break
        }
        $index = @($routeRows).Count
        $safeStepName = ($step.Name -replace '[^0-9A-Za-z_.-]', '-')
        $lastRouteJson = Join-Path $outDir ("route-{0:D2}-{1}-path.json" -f $index, $safeStepName)
        $lastRoutePath = Invoke-MousePath -Process $process -Json $lastRouteJson -PathPoints $step.Points -Click -AllowUnverified
        Start-Sleep -Milliseconds ([int]$step.WaitMs)
        $stepFrame = Save-StateFrame `
            -Process $process `
            -Name ("route-{0:D2}-{1}" -f $index, $safeStepName) `
            -Path (Join-Path $outDir ("route-{0:D2}-{1}.png" -f $index, $safeStepName)) `
            -OutDir $outDir
        $routeRows += [pscustomobject]@{
            Index = $index
            Name = $step.Name
            Points = $step.Points
            WaitMs = [int]$step.WaitMs
            Json = $lastRouteJson
            PathVerified = $lastRoutePath.path_verified
            ClickPathVerified = $lastRoutePath.click_path_verified
            ProbeExitCode = $lastRoutePath.ProbeExitCode
            Frame = $stepFrame.Frame
            FrameState = $stepFrame.State
            GameplayFrameLikely = $stepFrame.GameplayFrameLikely
            GameplayWarnings = @($stepFrame.GameplayWarnings)
        }
        if ($stepFrame.GameplayFrameLikely) {
            break
        }
    }

    Start-Sleep -Seconds $RunSeconds
    $mapFrameState = Save-StateFrame -Process $process -Name 'after-route' -Path (Join-Path $outDir 'after-map-path.png') -OutDir $outDir

    $routePointText = if (@($routeSteps).Count -gt 0) {
        (@($routeSteps) | ForEach-Object { $_.Points }) -join ';'
    } else {
        ''
    }
    $routePathVerified = (@($routeRows).Count -gt 0 -and @($routeRows | Where-Object { -not $_.PathVerified }).Count -eq 0)
    $routeClickPathVerified = (@($routeRows).Count -gt 0 -and @($routeRows | Where-Object { -not $_.ClickPathVerified }).Count -eq 0)
    $lastRouteRow = @($routeRows | Select-Object -Last 1)

    $process.Refresh()
    $result = [pscustomobject]@{
        Exe = $Exe
        ExeSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Exe).Hash
        ProcessId = $process.Id
        LaunchAttempts = $launchInfo.Attempts
        LaunchErrors = @($launchInfo.Errors)
        OutputDirectory = $outDir
        MenuMouseJson = $menuMouseJson
        MapMouseJson = $lastRouteJson
        MenuFrame = $menuFrameState.Frame
        MapFrame = $mapFrameState.Frame
        MenuPathVerified = $mainMenuReady
        MenuClickPathVerified = (@($introProbeRows).Count -gt 0 -and @($introProbeRows | Where-Object { -not $_.ClickPathVerified }).Count -eq 0)
        MenuProbeExitCode = if ($menuPath) { $menuPath.ProbeExitCode } else { $null }
        MapPathVerified = $routePathVerified
        MapClickPathVerified = $routeClickPathVerified
        MapProbeExitCode = if (@($lastRouteRow).Count -gt 0) { $lastRouteRow[0].ProbeExitCode } else { $null }
        Points = $routePointText
        Route = $Route
        RouteSteps = $routeRows
        ReadinessFrames = $readinessFrames
        IntroProbeRows = $introProbeRows
        MainMenuReady = $mainMenuReady
        MenuFrameState = $menuFrameState.State
        FinalFrameState = $mapFrameState.State
        GameplayFrameLikely = $mapFrameState.GameplayFrameLikely
        GameplayWarnings = @($mapFrameState.GameplayWarnings)
        MoveMode = $MoveMode
        ClickMode = $ClickMode
        IntroSkipClicks = $IntroSkipClicks
        IntroMaxRounds = $IntroMaxRounds
        PostIntroWaitSec = $PostIntroWaitSec
        RunSeconds = $RunSeconds
        ProcessExitedBeforeCleanup = $process.HasExited
        ExitCode = if ($process.HasExited) { $process.ExitCode } else { $null }
    }
} catch {
    $scriptError = $_
} finally {
    if ($process -and -not $process.HasExited -and -not $KeepOpen) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
    if (-not $KeepOpen) {
        Stop-ClashProcesses
    }
}

$resultPath = Join-Path $outDir 'results.json'
if ($result) {
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultPath -Encoding ASCII
    $result | Format-List
} else {
    [pscustomobject]@{
        Exe = $Exe
        OutputDirectory = $outDir
        LaunchAttempts = if ($launchInfo) { $launchInfo.Attempts } else { 0 }
        LaunchErrors = if ($launchInfo) { @($launchInfo.Errors) } else { @() }
        Error = if ($scriptError) { $scriptError.Exception.Message } else { 'visual smoke did not reach result creation' }
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outDir 'error.json') -Encoding ASCII
}
[pscustomobject]@{
    OutputDirectory = $outDir
    ResultsJson = $resultPath
}
if ($scriptError) {
    throw $scriptError
}
