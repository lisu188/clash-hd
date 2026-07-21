param(
    [string]$Exe = 'C:\Clash\clash95_hd_mousedynorigin_menusurface_scrollclamp_20260423.exe',
    [string]$WorkDir = 'C:\Clash',
    [string]$Python = 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [string]$OutRoot = (Join-Path (Join-Path $PSScriptRoot '..\..') 'captures\archive'),
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
    # 2026-07-17 diagnosis (commit 589f5700): the menu/map read the mouse from
    # the DirectInput ACCUMULATOR, not the OS cursor. SetCursorPos and absolute
    # SendInput moves - i.e. every -MoveMode this harness offered - are
    # invisible to the engine hit test, so legacy route clicks verified OS
    # cursor placement while the engine cursor never moved. -InputMode pulse
    # routes and aims through tools/menu_pulse_click.py instead (one relative
    # MOUSEEVENTF_MOVE per ~28ms poll, frame-diff position feedback, button
    # held while pulsing). 'legacy' keeps the historic behaviour selectable.
    [ValidateSet('legacy', 'pulse')]
    [string]$InputMode = 'legacy',
    [string]$PulseRouteSteps = 'load-button:302,211;load-slot0:320,166;confirm-load:400,226',
    [string]$FollowupPoints = '',
    [switch]$FollowupAimOnly,
    [int]$PulseAimTolerancePx = 10,
    [int]$PulseClickHoldMs = 700,
    [int]$PulseClickRepeats = 3,
    [int]$PulseIntervalMs = 28,
    [double]$PulseInitialGain = 4.4,
    [int]$PulseRouteDeadlineSec = 150,
    [int]$PulsePointDeadlineSec = 90,
    [int]$PulsePointSettleMs = 1200,
    [int]$CursorProbeDeadlineSec = 45,
    [string]$CursorProbePoint = '200,150',
    [double]$MapReachedNonblackPercent = 85.0,
    [double]$IntroMenuVerifyNonblackPercent = 50.0,
    [double]$IntroMenuVerifyNonblackMaxPercent = 80.0,
    [int]$IntroMenuVerifyMaxUniqueColors = 400,
    [int]$IntroMenuStabilityWaitMs = 800,
    [int]$WindowMissingGraceAttempts = 3,
    [int]$WindowMissingGraceDelayMs = 800,
    [switch]$NoGameplayCheck,
    [switch]$KeepOpen,
    [switch]$AllowVisibleRuntime
)

$ErrorActionPreference = 'Stop'
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

if (-not $AllowVisibleRuntime) {
    throw "This legacy harness launches a visible Clash95 runtime. Re-run with -AllowVisibleRuntime only after explicit user approval."
}

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
    public static extern bool IsHungAppWindow(IntPtr hWnd);

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

function New-WindowHealthSample {
    param(
        [string]$Timestamp,
        [string]$Phase,
        [bool]$ProcessExited,
        [bool]$WindowFound,
        [object]$Hwnd,
        [object]$ClientWidth,
        [object]$ClientHeight,
        [object]$IsHung,
        [int]$GraceAttempts,
        [string]$HealthClass,
        [string]$ErrorText = $null
    )

    [pscustomobject]@{
        Timestamp = $Timestamp
        Phase = $Phase
        ProcessExited = $ProcessExited
        WindowFound = $WindowFound
        Hwnd = $Hwnd
        ClientWidth = $ClientWidth
        ClientHeight = $ClientHeight
        IsHung = $IsHung
        GraceAttempts = $GraceAttempts
        HealthClass = $HealthClass
        Error = $ErrorText
    }
}

function Get-WindowHealthSample {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Phase
    )

    $timestamp = (Get-Date).ToString('o')
    try {
        $Process.Refresh()
        if ($Process.HasExited) {
            return New-WindowHealthSample -Timestamp $timestamp -Phase $Phase -ProcessExited $true -WindowFound $false -Hwnd $null -ClientWidth $null -ClientHeight $null -IsHung $null -GraceAttempts 0 -HealthClass 'process_exited'
        }
        $handle = [ClashVisualSmokeWin32]::FindVisibleWindowForProcess([uint32]$Process.Id)
        $graceAttemptsUsed = 0
        while ($handle -eq [IntPtr]::Zero -and $graceAttemptsUsed -lt $WindowMissingGraceAttempts) {
            # Grace retry: the GOG DirectDraw wrapper briefly hides or recreates
            # its window during display transitions, so only classify the window
            # as missing after it stays missing across the whole grace window.
            $graceAttemptsUsed++
            Start-Sleep -Milliseconds $WindowMissingGraceDelayMs
            $Process.Refresh()
            if ($Process.HasExited) {
                return New-WindowHealthSample -Timestamp $timestamp -Phase $Phase -ProcessExited $true -WindowFound $false -Hwnd $null -ClientWidth $null -ClientHeight $null -IsHung $null -GraceAttempts $graceAttemptsUsed -HealthClass 'process_exited'
            }
            $handle = [ClashVisualSmokeWin32]::FindVisibleWindowForProcess([uint32]$Process.Id)
        }
        if ($handle -eq [IntPtr]::Zero) {
            return New-WindowHealthSample -Timestamp $timestamp -Phase $Phase -ProcessExited $false -WindowFound $false -Hwnd $null -ClientWidth $null -ClientHeight $null -IsHung $null -GraceAttempts $graceAttemptsUsed -HealthClass 'window_missing_while_process_alive'
        }
        $rect = New-Object ClashVisualSmokeWin32+RECT
        [ClashVisualSmokeWin32]::GetClientRect($handle, [ref]$rect) | Out-Null
        $isHung = [ClashVisualSmokeWin32]::IsHungAppWindow($handle)
        $healthClass = if ($isHung) { 'application_hung' } else { 'responsive' }
        return New-WindowHealthSample -Timestamp $timestamp -Phase $Phase -ProcessExited $false -WindowFound $true -Hwnd ('0x{0:X}' -f $handle.ToInt64()) -ClientWidth ($rect.Right - $rect.Left) -ClientHeight ($rect.Bottom - $rect.Top) -IsHung ([bool]$isHung) -GraceAttempts $graceAttemptsUsed -HealthClass $healthClass
    } catch {
        return New-WindowHealthSample -Timestamp $timestamp -Phase $Phase -ProcessExited $false -WindowFound $false -Hwnd $null -ClientWidth $null -ClientHeight $null -IsHung $null -GraceAttempts 0 -HealthClass 'health_probe_error' -ErrorText $_.Exception.Message
    }
}

function Test-MenuFingerprint {
    param([object]$FrameMeta)

    if (-not $FrameMeta) {
        return $false
    }
    $nonblack = [double]$FrameMeta.NonblackPercent
    $colors = [int]$FrameMeta.UniqueSampleColors
    # Menu fingerprint: nonblack inside the menu band AND a small static
    # palette. Bright intro/logo/movie frames clear a plain nonblack floor but
    # fail the upper band or the palette bound; the caller additionally
    # requires a STABLE frame hash across two captures.
    return (
        $nonblack -ge $IntroMenuVerifyNonblackPercent -and
        $nonblack -le $IntroMenuVerifyNonblackMaxPercent -and
        $colors -le $IntroMenuVerifyMaxUniqueColors
    )
}

function Get-PulseRouteStepList {
    param([string]$Spec)

    $items = @()
    foreach ($raw in ($Spec -split ';')) {
        $text = $raw.Trim()
        if (-not $text) {
            continue
        }
        if ($text -notmatch '^(?<name>[^:]+):\s*(?<x>-?\d+)\s*,\s*(?<y>-?\d+)\s*$') {
            throw "Invalid -PulseRouteSteps entry (expected name:x,y): $text"
        }
        $items += [pscustomobject]@{
            Name = $Matches.name.Trim()
            Points = ('{0},{1}' -f $Matches.x, $Matches.y)
        }
    }
    return @($items)
}

function Get-FollowupPointList {
    param([string]$Spec)

    $items = @()
    foreach ($raw in ($Spec -split ';')) {
        $text = $raw.Trim()
        if (-not $text) {
            continue
        }
        $name = ''
        $coords = $text
        if ($text -match '^(?<name>[^:]+):(?<coords>.+)$') {
            $name = $Matches.name.Trim()
            $coords = $Matches.coords.Trim()
        }
        if ($coords -notmatch '^\s*(?<x>-?\d+)\s*,\s*(?<y>-?\d+)\s*$') {
            throw "Invalid -FollowupPoints entry (expected x,y or name:x,y): $text"
        }
        $index = @($items).Count
        if (-not $name) {
            $name = 'followup-{0:D2}' -f $index
        }
        $items += [pscustomobject]@{
            Index = $index
            Name = $name
            Points = ('{0},{1}' -f $Matches.x, $Matches.y)
        }
    }
    return @($items)
}

function Invoke-MenuPulseTool {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Json,
        [string[]]$ToolArgs
    )

    $pulseTool = Join-Path $RepoRoot 'tools\menu_pulse_click.py'
    if (-not (Test-Path -LiteralPath $pulseTool -PathType Leaf)) {
        throw "Required pulse click tool was not found: $pulseTool"
    }
    $allArgs = @($pulseTool, '--pid', "$($Process.Id)") + $ToolArgs + @('--json', $Json)
    $log = [System.IO.Path]::ChangeExtension($Json, '.log')
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & $Python '-W' 'ignore' @allArgs 2>&1
        $exitCode = $LASTEXITCODE
    } catch {
        $output = @($_.Exception.Message)
        $exitCode = 1
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $output | Set-Content -LiteralPath $log -Encoding ASCII

    $result = $null
    if (Test-Path -LiteralPath $Json -PathType Leaf) {
        $result = Get-Content -LiteralPath $Json -Raw | ConvertFrom-Json
    }
    [pscustomobject]@{
        Result = $result
        ExitCode = $exitCode
        Json = $Json
        Log = $log
        ToolArgs = ($ToolArgs -join ' ')
    }
}

function Invoke-PulseCursorProbe {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Json
    )

    # No-click liveness probe: aims the ENGINE cursor at one point and exits 0
    # only if the frame diff shows it responded and converged. This separates
    # "the menu is on screen" from "the menu is interactive": the intro can
    # auto-play into a dead attract-like menu whose input poll never wakes.
    Invoke-MenuPulseTool -Process $Process -Json $Json -ToolArgs @(
        '--steps', ("cursor-probe:{0}" -f $CursorProbePoint),
        '--probe-only',
        '--map-nonblack', '0',
        '--aim-tolerance', "$PulseAimTolerancePx",
        '--pulse-interval-ms', "$PulseIntervalMs",
        '--initial-gain', "$PulseInitialGain",
        '--deadline-sec', "$CursorProbeDeadlineSec"
    )
}

function Invoke-MenuPulseRoute {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Json,
        [string]$StepSpec
    )

    Invoke-MenuPulseTool -Process $Process -Json $Json -ToolArgs @(
        '--steps', $StepSpec,
        '--map-nonblack', "$MapReachedNonblackPercent",
        '--aim-tolerance', "$PulseAimTolerancePx",
        '--click-hold-ms', "$PulseClickHoldMs",
        '--click-repeats', "$PulseClickRepeats",
        '--pulse-interval-ms', "$PulseIntervalMs",
        '--initial-gain', "$PulseInitialGain",
        '--deadline-sec', "$PulseRouteDeadlineSec"
    )
}

function Invoke-PulseAimPoint {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Json,
        [string]$PointSpec
    )

    $toolArgs = @(
        '--aim-points', $PointSpec,
        '--aim-tolerance', "$PulseAimTolerancePx",
        '--click-hold-ms', "$PulseClickHoldMs",
        '--click-repeats', "$PulseClickRepeats",
        '--pulse-interval-ms', "$PulseIntervalMs",
        '--initial-gain', "$PulseInitialGain",
        '--point-settle-ms', "$PulsePointSettleMs",
        '--deadline-sec', "$PulsePointDeadlineSec"
    )
    if ($FollowupAimOnly) {
        $toolArgs += '--aim-only'
    }
    Invoke-MenuPulseTool -Process $Process -Json $Json -ToolArgs $toolArgs
}

function Convert-PulseStepToRouteRow {
    param(
        [object]$PulseRun,
        [object]$StepRow,
        [string]$Name,
        [string]$Points,
        [int]$Index
    )

    $aim = if ($StepRow) { $StepRow.aim } else { $null }
    $skipped = [bool]($StepRow -and $StepRow.skipped_map_reached)
    [pscustomobject]@{
        Index = $Index
        Name = $Name
        Points = $Points
        InputMechanism = 'pulse-relative-engine-aim'
        MoveMode = 'pulse-relative'
        ClickMode = 'sendinput-hold-while-pulsing'
        AimConverged = ($skipped -or [bool]($aim -and $aim.converged))
        AimErrorPx = if ($aim -and $null -ne $aim.aim_error_px) { [int]$aim.aim_error_px } else { $null }
        AimTolerancePx = $PulseAimTolerancePx
        AimedPos = if ($aim) { $aim.aimed_pos } else { $null }
        EngineGain = if ($aim) { $aim.gain } else { $null }
        TransitionVerified = [bool]($StepRow -and $StepRow.transition_verified)
        SkippedMapReached = $skipped
        ChangedPixels = if ($StepRow -and $null -ne $StepRow.changed_pixels) { [int]$StepRow.changed_pixels } else { $null }
        PostNonblack = if ($StepRow -and $null -ne $StepRow.post_nonblack) { [double]$StepRow.post_nonblack } else { $null }
        ClickCount = if ($StepRow -and $null -ne $StepRow.click_count) { [int]$StepRow.click_count } else { 0 }
        RefusedExitZone = [bool]($StepRow -and $StepRow.refused_exit_zone)
        ForegroundDenied = [bool]($StepRow -and $StepRow.foreground_denied)
        WindowLostAfterClick = [bool]($StepRow -and $StepRow.window_lost_after_click)
        InputProofClass = 'automated_visible_runtime_engine_aim_evidence_not_manual_directinput_release_proof'
        ProbeExitCode = $PulseRun.ExitCode
        Json = $PulseRun.Json
        Log = $PulseRun.Log
    }
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

    $coverageTool = Join-Path $RepoRoot 'tools\map_tile_coverage.py'
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

    $captureScript = Join-Path $RepoRoot 'scripts\capture\capture_clash_client_frame.ps1'
    if (-not (Test-Path -LiteralPath $captureScript)) {
        throw "Capture helper was not found: $captureScript"
    }
    $metaPath = "$Path.json"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $captureScript -TargetProcessId $Process.Id -Path $Path -Json $metaPath -WindowTimeoutSec $WindowTimeoutSec -AllowVisibleRuntime | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "scripts\capture\capture_clash_client_frame.ps1 failed with exit code $LASTEXITCODE"
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

    $mouseTool = Join-Path $RepoRoot 'tools\mouse_path_probe.py'
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
$mousePath = Join-Path $RepoRoot 'tools\mouse_path_probe.py'
if (-not (Test-Path -LiteralPath $mousePath)) {
    throw "Required path was not found: $mousePath"
}
$pulseToolPath = Join-Path $RepoRoot 'tools\menu_pulse_click.py'
$pulseRouteStepList = @()
$followupPointList = @()
if ($InputMode -eq 'pulse') {
    if (-not (Test-Path -LiteralPath $pulseToolPath)) {
        throw "Required path was not found: $pulseToolPath"
    }
    if ($Route -ne 'menu-only') {
        $pulseRouteStepList = Get-PulseRouteStepList -Spec $PulseRouteSteps
        if (@($pulseRouteStepList).Count -eq 0) {
            throw "-InputMode pulse with -Route $Route requires at least one -PulseRouteSteps entry"
        }
    }
}
if ($FollowupPoints) {
    if ($InputMode -ne 'pulse') {
        throw "-FollowupPoints requires -InputMode pulse (the legacy move modes are invisible to the engine's DirectInput hit test)"
    }
    $followupPointList = Get-FollowupPointList -Spec $FollowupPoints
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
    $windowHealthSamples = @()
    $menuPath = $null
    $menuMouseJson = $null
    $mainMenuReady = $false
    $introMenuVerified = $false
    $introMenuVerifyNonblack = $null
    $introMenuVerifyColors = $null
    $introRoundsUsed = 0
    $windowHealthSamples += Get-WindowHealthSample -Process $process -Phase 'after-launch'
    for ($round = 0; $round -lt $IntroMaxRounds; $round++) {
        $introRoundsUsed = $round + 1
        $menuMouseJson = Join-Path $outDir ("intro-skip-{0:D2}.json" -f $round)
        $menuPath = Invoke-MousePath -Process $process -Json $menuMouseJson -PathPoints $introSkipPoints -Click -SpacePulses $SkipPulses -AllowUnverified
        Start-Sleep -Milliseconds $IntroRoundWaitMs
        $readiness = Save-StateFrame `
            -Process $process `
            -Name ("readiness-{0:D2}" -f $round) `
            -Path (Join-Path $outDir ("readiness-{0:D2}.png" -f $round)) `
            -OutDir $outDir
        $readinessFrames += $readiness
        $roundMenuVerified = $false
        if ($InputMode -eq 'pulse' -and -not $introMenuVerified) {
            # Verified intro-skip round: the frame-state classifier alone also
            # accepts bright story pages, so pulse mode additionally requires
            # the menu fingerprint (nonblack band + small palette) AND a stable
            # frame hash across two captures before any route click is trusted.
            if (Test-MenuFingerprint -FrameMeta $readiness.Frame) {
                Start-Sleep -Milliseconds $IntroMenuStabilityWaitMs
                try {
                    $stabilityMeta = Save-CleanClientFrame -Process $process -Path (Join-Path $outDir ("menucheck-{0:D2}b.png" -f $round))
                    if ($stabilityMeta -and $readiness.Frame -and $stabilityMeta.Hash -eq $readiness.Frame.Hash) {
                        $roundMenuVerified = $true
                        $introMenuVerified = $true
                        $introMenuVerifyNonblack = [double]$readiness.Frame.NonblackPercent
                        $introMenuVerifyColors = [int]$readiness.Frame.UniqueSampleColors
                    }
                } catch {
                    # Capture failures during intro/display transitions are
                    # tolerated; the next round retries and window health is
                    # sampled after the loop.
                }
            }
        }
        $introProbeRows += [pscustomobject]@{
            Round = $round
            Json = $menuMouseJson
            PathVerified = $menuPath.path_verified
            ClickPathVerified = $menuPath.click_path_verified
            ProbeExitCode = $menuPath.ProbeExitCode
            FrameState = $readiness.State
            GameplayFrameLikely = $readiness.GameplayFrameLikely
            MenuFingerprintVerified = $roundMenuVerified
            NonblackPercent = if ($readiness.Frame) { $readiness.Frame.NonblackPercent } else { $null }
            UniqueSampleColors = if ($readiness.Frame) { $readiness.Frame.UniqueSampleColors } else { $null }
        }
        if ($readiness.State -eq 'main-menu-or-dialog-likely' -or $readiness.State -eq 'gameplay-likely') {
            $mainMenuReady = $true
            if ($InputMode -ne 'pulse') {
                break
            }
        }
        if ($InputMode -eq 'pulse' -and $introMenuVerified) {
            break
        }
    }

    Start-Sleep -Seconds $PostIntroWaitSec
    $menuFrameState = Save-StateFrame -Process $process -Name 'menu-ready' -Path (Join-Path $outDir 'menu.png') -OutDir $outDir

    $windowHealthSamples += Get-WindowHealthSample -Process $process -Phase 'after-intro-wait'

    $cursorProbeRun = $null
    $cursorProbeAlive = $false
    $cursorProbeRequired = ($InputMode -eq 'pulse' -and $Route -ne 'menu-only')
    if ($cursorProbeRequired -and $introMenuVerified) {
        $cursorProbeRun = Invoke-PulseCursorProbe -Process $process -Json (Join-Path $outDir 'cursor-probe.json')
        $cursorProbeAlive = ($cursorProbeRun.ExitCode -eq 0)
    }

    $routeSteps = Get-RouteSteps -RouteName $Route -CustomPoints $Points
    $routeRows = @()
    $pulseRouteRows = @()
    $followupRows = @()
    $pulseRouteRun = $null
    $mapRouteReached = $null
    $routeFinalNonblack = $null
    $routeBlockedReason = $null
    $lastRoutePath = $null
    $lastRouteJson = $null

    if ($InputMode -eq 'pulse') {
        # Pulse lane: the DirectInput-visible route replaces the legacy
        # mouse_path_probe click steps entirely. Fail closed - never aim or
        # click into an unverified screen (story page, transition frame, or a
        # dead attract-state menu whose input poll never woke).
        if ($Route -eq 'menu-only') {
            $routeBlockedReason = 'menu-only route has no click steps'
        } elseif ($menuFrameState.State -eq 'gameplay-likely') {
            $routeBlockedReason = 'gameplay frame already reached before the route'
        } elseif (-not $introMenuVerified) {
            $routeBlockedReason = 'intro-skip rounds never verified the main-menu fingerprint'
        } elseif (-not $cursorProbeAlive) {
            $routeBlockedReason = 'engine-cursor liveness probe did not converge'
        } else {
            $prePulseHealth = Get-WindowHealthSample -Process $process -Phase 'before-pulse-route'
            $windowHealthSamples += $prePulseHealth
            if ($prePulseHealth.HealthClass -ne 'responsive') {
                $routeBlockedReason = "window health before the route was $($prePulseHealth.HealthClass)"
            } else {
                $pulseStepSpec = (@($pulseRouteStepList | ForEach-Object { '{0}:{1}' -f $_.Name, $_.Points }) -join ';')
                $pulseRouteRun = Invoke-MenuPulseRoute -Process $process -Json (Join-Path $outDir 'route-pulse-clicks.json') -StepSpec $pulseStepSpec
                $pulseSteps = @()
                if ($pulseRouteRun.Result -and $pulseRouteRun.Result.steps) {
                    $pulseSteps = @($pulseRouteRun.Result.steps)
                }
                $pulseIndex = 0
                foreach ($stepDefinition in $pulseRouteStepList) {
                    $stepRow = $pulseSteps | Where-Object { $_.name -eq $stepDefinition.Name } | Select-Object -First 1
                    $pulseRouteRows += Convert-PulseStepToRouteRow -PulseRun $pulseRouteRun -StepRow $stepRow -Name $stepDefinition.Name -Points $stepDefinition.Points -Index $pulseIndex
                    $pulseIndex++
                }
                if ($pulseRouteRun.Result) {
                    $mapRouteReached = [bool]$pulseRouteRun.Result.map_reached
                    $routeFinalNonblack = if ($null -ne $pulseRouteRun.Result.final_nonblack) { [double]$pulseRouteRun.Result.final_nonblack } else { $null }
                }
                Start-Sleep -Milliseconds 1200
                $postPulseHealth = Get-WindowHealthSample -Process $process -Phase 'after-pulse-route'
                $windowHealthSamples += $postPulseHealth
                $routePulseFrame = Save-StateFrame -Process $process -Name 'route-pulse' -Path (Join-Path $outDir 'route-pulse.png') -OutDir $outDir
                $readinessFrames += $routePulseFrame
            }
        }

        # Per-target FOLLOW-UP validation points: one menu_pulse_click
        # --aim-points invocation per point so each carries its own JSON, log,
        # and post-click PNG. Gated on the map actually having been reached -
        # aiming validation points at a menu would prove nothing.
        if (@($followupPointList).Count -gt 0) {
            if (-not $mapRouteReached) {
                $routeBlockedReason = if ($routeBlockedReason) { $routeBlockedReason } else { 'pulse route did not reach the gameplay map' }
            } else {
                foreach ($point in $followupPointList) {
                    $process.Refresh()
                    if ($process.HasExited) {
                        break
                    }
                    $preHealth = Get-WindowHealthSample -Process $process -Phase ('before-followup-{0}' -f $point.Name)
                    $windowHealthSamples += $preHealth
                    if ($preHealth.HealthClass -ne 'responsive') {
                        break
                    }
                    $safePointName = ($point.Name -replace '[^0-9A-Za-z_.-]', '-')
                    $pointJson = Join-Path $outDir ("followup-{0:D2}-{1}.json" -f $point.Index, $safePointName)
                    $pointRun = Invoke-PulseAimPoint -Process $process -Json $pointJson -PointSpec ('{0}:{1}' -f $point.Name, $point.Points)
                    $pointStepRow = $null
                    if ($pointRun.Result -and $pointRun.Result.steps) {
                        $pointStepRow = @($pointRun.Result.steps) | Select-Object -First 1
                    }
                    $pointFrame = Save-StateFrame `
                        -Process $process `
                        -Name ("followup-{0:D2}-{1}" -f $point.Index, $safePointName) `
                        -Path (Join-Path $outDir ("followup-{0:D2}-{1}.png" -f $point.Index, $safePointName)) `
                        -OutDir $outDir
                    $followupRow = Convert-PulseStepToRouteRow -PulseRun $pointRun -StepRow $pointStepRow -Name $point.Name -Points $point.Points -Index $point.Index
                    $followupRow | Add-Member -NotePropertyName AimOnly -NotePropertyValue ([bool]$FollowupAimOnly) -Force
                    $followupRow | Add-Member -NotePropertyName Frame -NotePropertyValue $pointFrame.Frame -Force
                    $followupRow | Add-Member -NotePropertyName FrameState -NotePropertyValue $pointFrame.State -Force
                    $followupRow | Add-Member -NotePropertyName GameplayFrameLikely -NotePropertyValue $pointFrame.GameplayFrameLikely -Force
                    $followupRows += $followupRow
                }
            }
        }
    }

    foreach ($step in $routeSteps) {
        if ($InputMode -eq 'pulse') {
            break
        }
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
    $windowHealthSamples += Get-WindowHealthSample -Process $process -Phase 'before-final-capture'
    $mapFrameState = Save-StateFrame -Process $process -Name 'after-route' -Path (Join-Path $outDir 'after-map-path.png') -OutDir $outDir

    # Per-target follow-up validation clicks run ONLY in the pulse lane (see the
    # setup guard: legacy move modes are invisible to the engine's DirectInput
    # accumulator). The pulse route section above already populated
    # $followupRows; nothing to drive here.

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
        FollowupPoints = $FollowupPoints
        FollowupSteps = $followupRows
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
        InputMode = $InputMode
        InputMechanism = if ($InputMode -eq 'pulse') { 'pulse-relative-engine-aim' } else { "$MoveMode/$ClickMode" }
        InputProofClass = if ($InputMode -eq 'pulse') {
            'automated_visible_runtime_engine_aim_evidence_not_manual_directinput_release_proof'
        } else {
            'legacy_os_cursor_path_evidence_not_engine_verified'
        }
        IntroMenuVerified = $introMenuVerified
        IntroMenuVerifyNonblackPercent = $introMenuVerifyNonblack
        IntroMenuVerifyUniqueColors = $introMenuVerifyColors
        IntroMenuVerifyBand = @($IntroMenuVerifyNonblackPercent, $IntroMenuVerifyNonblackMaxPercent)
        IntroMenuVerifyMaxUniqueColors = $IntroMenuVerifyMaxUniqueColors
        IntroRoundsUsed = $introRoundsUsed
        CursorProbeRequired = $cursorProbeRequired
        CursorProbeAlive = $cursorProbeAlive
        CursorProbeExitCode = if ($cursorProbeRun) { $cursorProbeRun.ExitCode } else { $null }
        CursorProbeJson = if ($cursorProbeRun) { $cursorProbeRun.Json } else { $null }
        PulseRouteSteps = $PulseRouteSteps
        PulseRouteRows = $pulseRouteRows
        PulseRouteJson = if ($pulseRouteRun) { $pulseRouteRun.Json } else { $null }
        PulseRouteExitCode = if ($pulseRouteRun) { $pulseRouteRun.ExitCode } else { $null }
        MapRouteReached = $mapRouteReached
        RouteFinalNonblackPercent = $routeFinalNonblack
        RouteBlockedReason = $routeBlockedReason
        FollowupPoints = $FollowupPoints
        FollowupAimOnly = [bool]$FollowupAimOnly
        FollowupRows = $followupRows
        FollowupPointCount = @($followupPointList).Count
        FollowupConvergedCount = @($followupRows | Where-Object { $_.AimConverged }).Count
        PulseAimTolerancePx = $PulseAimTolerancePx
        WindowHealthSamples = $windowHealthSamples
        WindowHangObserved = (@($windowHealthSamples | Where-Object { $_.HealthClass -eq 'application_hung' }).Count -gt 0)
        WindowMissingWhileAliveObserved = (@($windowHealthSamples | Where-Object { $_.HealthClass -eq 'window_missing_while_process_alive' }).Count -gt 0)
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
