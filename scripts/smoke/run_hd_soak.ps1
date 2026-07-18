param(
    [string]$InputExe = 'C:\Clash\clash95.exe',
    [string]$CandidateDir = 'C:\ClashTests\hd-soak',
    [string]$CandidateName = '',
    [string]$WorkDir = 'C:\Clash',
    [string]$Python = '',
    [string]$Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch',
    [ValidateSet('short2', 'short10', 'short30', 'custom')]
    [string]$Tier = 'short2',
    [int]$DurationSec = 0,
    [ValidateSet('menu-idle', 'map-idle', 'map-pan', 'custom')]
    [string]$Route = 'menu-idle',
    [string]$CustomPoints = '400,300',
    [int]$SampleIntervalSec = 15,
    [ValidateSet('sendinput', 'postmessage', 'both', 'none')]
    [string]$IntroSkipClickMode = 'postmessage',
    [int]$IntroSkipClicks = 8,
    [int]$SkipPulses = 4,
    [int]$RouteStepWaitMs = 1400,
    [int]$MoveWindowX = 80,
    [int]$MoveWindowY = 80,
    [ValidateSet('setcursor', 'sendinput-absolute', 'sendinput-relative', 'sendinput-client-delta', 'auto', 'none')]
    [string]$MoveMode = 'auto',
    [ValidateSet('sendinput', 'postmessage', 'both')]
    [string]$ClickMode = 'sendinput',
    [int]$ClickHoldMs = 250,
    [int]$ClickRepeat = 1,
    [int]$MaxInputDriftPx = 1,
    [double]$MinNonblackPercent = 10.0,
    [int]$MinUniqueSampleColors = 8,
    [int]$MaxArtifactMB = 250,
    [int]$MaxWorkingSetGrowthMB = 64,
    [int]$MaxPrivateMemoryGrowthMB = 64,
    [int]$MaxHandleGrowth = 128,
    [string]$OutputRoot = 'C:\ClashCaptures\hd-soak',
    [string]$ReportJson = 'captures\current\hd-soak-short-current.json',
    [string]$ReportMarkdown = 'captures\current\hd-soak-short-current.md',
    [string]$VisibleRuntimeApprovalExpiresUtc = '',
    [string]$VisibleRuntimeApprovalToken = '',
    [switch]$Execute,
    [switch]$AllowVisibleRuntime,
    [switch]$AllowRepoCandidateDir,
    [switch]$ReuseCandidate,
    [switch]$SkipPatch,
    [switch]$KeepOpen,
    [switch]$RequirePass,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'

$StableStage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch'
$ExpectedBaseSha256 = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$IntroSkipStopClickRepeatOnDrift = $true
# 2026-07-17 diagnosis: the menu consumes ONLY pulse-mode relative DirectInput
# (one MOUSEEVENTF_MOVE per ~28ms poll; engine cursor = gain*delta per poll,
# accumulator resets each poll). SetCursorPos/absolute moves/PostMessage clicks
# never reach the menu hit test, which is why earlier sendinput route clicks
# verified OS-cursor placement but never navigated. Route clicks therefore run
# through tools/menu_pulse_click.py (engine-aim + frame-transition proof).
$IntroMenuVerifyNonblackPercent = 50.0
$IntroMenuVerifyNonblackMaxPercent = 80.0
$IntroMenuVerifyMaxUniqueColors = 400
$IntroSkipMaxRounds = 12
# Rapid kill+relaunch destabilizes the GOG DirectDraw wrapper (observed
# DDERR_UNSUPPORTED dialog on fast relaunch 2026-07-17), so default to a
# single launch; the engine-cursor revival inside tools/menu_pulse_click.py
# (foreground activation cycle) handles the dead-poll case in-process without
# a relaunch. MaxLaunchAttempts stays configurable for machines whose wrapper
# tolerates relaunch.
$MaxLaunchAttempts = 1
$RelaunchSettleMs = 8000
$PulseAimTolerancePx = 10
$MapReachedNonblackPercent = 85.0
$WindowMissingGraceAttempts = 3
$WindowMissingGraceDelayMs = 800
# Stale-handle policy for the INPUT helpers (the grace retries above only cover
# health sampling). The wrapper destroys and recreates its top-level window
# across the intro->menu mode switch, so tools/mouse_path_probe.py must (a) wait
# for the same hwnd to report the same client size on consecutive samples before
# it sends anything, and (b) re-acquire the handle for the pid instead of dying
# on ERROR_INVALID_WINDOW_HANDLE the way the 2026-07-18 short2 run did.
$WindowStableSamples = 2
$WindowStablePollMs = 350
$WindowStableTimeoutSec = 8
$WindowReacquireAttempts = 12
$WindowReacquireDelayMs = 250

if (-not ([System.Management.Automation.PSTypeName]'ClashSoakWindowHealthWin32').Type) {
    Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class ClashSoakWindowHealthWin32 {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc callback, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumChildWindows(IntPtr parent, EnumWindowsProc callback, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool IsWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool IsIconic(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool GetClientRect(IntPtr hWnd, out RECT rect);

    [DllImport("user32.dll")]
    public static extern bool IsHungAppWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetClassName(IntPtr hWnd, StringBuilder buffer, int size);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder buffer, int size);

    public static string ClassNameOf(IntPtr hWnd) {
        StringBuilder buffer = new StringBuilder(256);
        GetClassName(hWnd, buffer, buffer.Capacity);
        return buffer.ToString();
    }

    public static string TextOf(IntPtr hWnd) {
        StringBuilder buffer = new StringBuilder(512);
        GetWindowText(hWnd, buffer, buffer.Capacity);
        return buffer.ToString();
    }

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

    // MEASURED 2026-07-18 (C:\ClashCaptures\hd-soak-diag\windowtimeline-*):
    // when the GOG DirectDraw wrapper fails a display-mode switch it CLEARS
    // WS_VISIBLE on its main window (style 0x95000000 -> 0x8D000000) while the
    // window stays alive with an intact 800x600 client rect, and pops a modal
    // #32770 carrying "DirectDraw Error DDERR_UNSUPPORTED". The visible-only
    // filter above reports that as "window missing", which sent two sessions
    // hunting a phantom teardown. These two probes let the harness say which of
    // the three states it is. They are DIAGNOSTIC ONLY: a hidden window is
    // still a hard failure and no input or capture is ever driven through one,
    // because a screen grab of a hidden window observes whatever is behind it.
    public static IntPtr FindAliveHiddenWindowForProcess(uint processId) {
        IntPtr found = IntPtr.Zero;
        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {
            uint windowProcessId;
            GetWindowThreadProcessId(hWnd, out windowProcessId);
            if (windowProcessId == processId && IsWindow(hWnd) && !IsWindowVisible(hWnd)) {
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

    public static IntPtr FindDialogForProcess(uint processId) {
        IntPtr found = IntPtr.Zero;
        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {
            uint windowProcessId;
            GetWindowThreadProcessId(hWnd, out windowProcessId);
            if (windowProcessId == processId && IsWindowVisible(hWnd) && ClassNameOf(hWnd) == "#32770") {
                found = hWnd;
                return false;
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }

    public static string DialogTextOf(IntPtr dialog) {
        StringBuilder collected = new StringBuilder();
        EnumChildWindows(dialog, delegate(IntPtr child, IntPtr lParam) {
            string text = TextOf(child);
            if (text.Length > 0) {
                if (collected.Length > 0) {
                    collected.Append(" | ");
                }
                collected.Append(text);
            }
            return true;
        }, IntPtr.Zero);
        return collected.ToString();
    }
}
'@
}

function Resolve-PlanPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $Path))
}

function Test-IsUnderPath {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Root
    )
    $fullPath = [System.IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
    if ($fullPath.Equals($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $true
    }
    return $fullPath.StartsWith($fullRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)
}

function Get-DxcfgWindowedStatus {
    param([Parameter(Mandatory = $true)][string]$Path)
    $failures = @()
    $settings = @{}
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        $failures += "Windowed DirectDraw config is missing: $Path"
    }
    else {
        $section = ''
        foreach ($rawLine in Get-Content -LiteralPath $Path) {
            $line = $rawLine.Trim()
            if (-not $line -or $line.StartsWith(';') -or $line.StartsWith('#')) {
                continue
            }
            if ($line -match '^\[(?<section>[^]]+)\]$') {
                $section = $Matches.section.ToLowerInvariant()
                continue
            }
            if ($section -eq 'dxcfg' -and $line -match '^(?<key>[^=]+)=(?<value>.*)$') {
                $settings[$Matches.key.Trim().ToLowerInvariant()] = $Matches.value.Trim().ToLowerInvariant()
            }
        }
    }
    $display = $settings['display']
    $presentation = $settings['presentation']
    if ($display -ne 'application') {
        $failures += "Windowed DirectDraw config display is '$display', expected 'application'"
    }
    if ($presentation -ne 'windowed') {
        $failures += "Windowed DirectDraw config presentation is '$presentation', expected 'windowed'"
    }
    [pscustomobject]@{
        Passed = (@($failures).Count -eq 0)
        Path = $Path
        Sha256 = if (Test-Path -LiteralPath $Path -PathType Leaf) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash } else { $null }
        Display = $display
        Presentation = $presentation
        Required = $true
        Failures = @($failures)
    }
}

function Get-InputStandingStatus {
    <#
      MEASURED 2026-07-18: three consecutive soak-shaped runs (21:43, 21:49,
      21:58) were destroyed by a LOCKED WORKSTATION, and none of them said so.
      With the lock screen owning the foreground (LockApp / LogonUI, class
      Windows.UI.Core.CoreWindow), tools/mouse_path_probe.py died on every
      intro round with "[WinError 5] SetCursorPos" and "[WinError 5] SendInput
      absolute move", so no intro-skip stimulus was ever delivered, the intro
      auto-played to completion, and the GOG DirectDraw wrapper then failed its
      intro->menu display-mode switch with a modal
      "DirectDraw Error DDERR_UNSUPPORTED" box.

      The run before them (21:09), on an unlocked session, skipped the intro on
      round 0 and clicked the menu successfully, so this is an environment
      precondition and not a harness or patch defect. Checking it BEFORE launch
      turns a ten-minute wrapper-destabilising false failure into an immediate,
      correctly-named refusal. OpenInputDesktop is deliberately NOT used: it
      still reported the "Default" desktop while the machine was locked on this
      machine, so the foreground owner is the signal that actually measured.
    #>
    $blockingOwners = @('LockApp', 'LogonUI')
    try {
        $foreground = [ClashSoakWindowHealthWin32]::GetForegroundWindow()
        if ($foreground -eq [IntPtr]::Zero) {
            return [pscustomobject]@{
                Passed = $false
                ForegroundProcess = $null
                ForegroundTitle = $null
                ForegroundClass = $null
                Failures = @('no foreground window exists; the interactive session cannot accept injected input')
            }
        }
        $foregroundPid = [uint32]0
        [ClashSoakWindowHealthWin32]::GetWindowThreadProcessId($foreground, [ref]$foregroundPid) | Out-Null
        $ownerProcess = $null
        try {
            $ownerProcess = (Get-Process -Id $foregroundPid -ErrorAction Stop).ProcessName
        } catch {
            $ownerProcess = $null
        }
        $title = [ClashSoakWindowHealthWin32]::TextOf($foreground)
        $class = [ClashSoakWindowHealthWin32]::ClassNameOf($foreground)
        $failures = @()
        if ($ownerProcess -and ($blockingOwners -contains $ownerProcess)) {
            $failures += (
                "the workstation is locked (foreground window '$title' is owned by $ownerProcess); " +
                'OS input injection is denied and the DirectDraw wrapper cannot complete a display-mode ' +
                'switch, so unlock the session before running the visible soak'
            )
        }
        return [pscustomobject]@{
            Passed = (@($failures).Count -eq 0)
            ForegroundProcess = $ownerProcess
            ForegroundTitle = $title
            ForegroundClass = $class
            Failures = @($failures)
        }
    } catch {
        return [pscustomobject]@{
            Passed = $false
            ForegroundProcess = $null
            ForegroundTitle = $null
            ForegroundClass = $null
            Failures = @("input standing probe failed: $($_.Exception.Message)")
        }
    }
}

function Get-WindowHealthSample {
    param(
        [Parameter(Mandatory = $true)][System.Diagnostics.Process]$Process,
        [Parameter(Mandatory = $true)][string]$Phase
    )

    $timestamp = (Get-Date).ToString('o')
    try {
        $Process.Refresh()
        if ($Process.HasExited) {
            return [pscustomobject]@{
                Timestamp = $timestamp
                Phase = $Phase
                ProcessExited = $true
                WindowFound = $false
                Hwnd = $null
                ClientWidth = $null
                ClientHeight = $null
                IsHung = $null
                HealthClass = 'process_exited'
            }
        }
        $handle = [ClashSoakWindowHealthWin32]::FindVisibleWindowForProcess([uint32]$Process.Id)
        $graceAttemptsUsed = 0
        while ($handle -eq [IntPtr]::Zero -and $graceAttemptsUsed -lt $WindowMissingGraceAttempts) {
            # Grace retry: the application/windowed wrapper can briefly hide or
            # recreate its window during display transitions; only classify the
            # window as missing after it stays missing across the grace window.
            $graceAttemptsUsed++
            Start-Sleep -Milliseconds $WindowMissingGraceDelayMs
            $Process.Refresh()
            if ($Process.HasExited) {
                return [pscustomobject]@{
                    Timestamp = $timestamp
                    Phase = $Phase
                    ProcessExited = $true
                    WindowFound = $false
                    Hwnd = $null
                    ClientWidth = $null
                    ClientHeight = $null
                    IsHung = $null
                    HealthClass = 'process_exited'
                }
            }
            $handle = [ClashSoakWindowHealthWin32]::FindVisibleWindowForProcess([uint32]$Process.Id)
        }
        if ($handle -eq [IntPtr]::Zero) {
            # Say WHICH of the three no-visible-window states this is. All three
            # stay hard failures, but "hidden with a wrapper error dialog up" and
            # "genuinely gone" call for completely different follow-ups.
            $dialog = [ClashSoakWindowHealthWin32]::FindDialogForProcess([uint32]$Process.Id)
            $hidden = [ClashSoakWindowHealthWin32]::FindAliveHiddenWindowForProcess([uint32]$Process.Id)
            $dialogText = $null
            $healthClass = 'window_missing_while_process_alive'
            if ($dialog -ne [IntPtr]::Zero) {
                $dialogText = [ClashSoakWindowHealthWin32]::DialogTextOf($dialog)
                $healthClass = 'wrapper_error_dialog'
            } elseif ($hidden -ne [IntPtr]::Zero) {
                $healthClass = 'window_hidden_while_process_alive'
            }
            $hiddenWidth = $null
            $hiddenHeight = $null
            if ($hidden -ne [IntPtr]::Zero) {
                $hiddenRect = New-Object ClashSoakWindowHealthWin32+RECT
                [ClashSoakWindowHealthWin32]::GetClientRect($hidden, [ref]$hiddenRect) | Out-Null
                $hiddenWidth = $hiddenRect.Right - $hiddenRect.Left
                $hiddenHeight = $hiddenRect.Bottom - $hiddenRect.Top
            }
            return [pscustomobject]@{
                Timestamp = $timestamp
                Phase = $Phase
                ProcessExited = $false
                WindowFound = $false
                Hwnd = $null
                ClientWidth = $null
                ClientHeight = $null
                IsHung = $null
                GraceAttempts = $graceAttemptsUsed
                HiddenWindowHwnd = if ($hidden -ne [IntPtr]::Zero) { ('0x{0:X}' -f $hidden.ToInt64()) } else { $null }
                HiddenWindowClientWidth = $hiddenWidth
                HiddenWindowClientHeight = $hiddenHeight
                HiddenWindowIconic = if ($hidden -ne [IntPtr]::Zero) { [bool][ClashSoakWindowHealthWin32]::IsIconic($hidden) } else { $null }
                DialogHwnd = if ($dialog -ne [IntPtr]::Zero) { ('0x{0:X}' -f $dialog.ToInt64()) } else { $null }
                DialogText = $dialogText
                HealthClass = $healthClass
            }
        }
        $rect = New-Object ClashSoakWindowHealthWin32+RECT
        [ClashSoakWindowHealthWin32]::GetClientRect($handle, [ref]$rect) | Out-Null
        $isHung = [ClashSoakWindowHealthWin32]::IsHungAppWindow($handle)
        return [pscustomobject]@{
            Timestamp = $timestamp
            Phase = $Phase
            ProcessExited = $false
            WindowFound = $true
            Hwnd = ('0x{0:X}' -f $handle.ToInt64())
            ClientWidth = $rect.Right - $rect.Left
            ClientHeight = $rect.Bottom - $rect.Top
            IsHung = [bool]$isHung
            HealthClass = if ($isHung) { 'application_hung' } else { 'responsive' }
        }
    } catch {
        return [pscustomobject]@{
            Timestamp = $timestamp
            Phase = $Phase
            ProcessExited = $false
            WindowFound = $false
            Hwnd = $null
            ClientWidth = $null
            ClientHeight = $null
            IsHung = $null
            HealthClass = 'health_probe_error'
            Error = $_.Exception.Message
        }
    }
}

function Find-Python {
    param([string]$Requested)
    if ($Requested) {
        if (-not (Test-Path -LiteralPath $Requested -PathType Leaf)) {
            throw "Python path does not exist: $Requested"
        }
        return (Resolve-PlanPath $Requested)
    }

    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $bundled = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundled -PathType Leaf) {
        return $bundled
    }

    throw 'Python 3 was not found on PATH and the bundled Codex runtime was not found.'
}

function Quote-Arg {
    param([Parameter(Mandatory = $true)][string]$Value)
    return "'" + ($Value -replace "'", "''") + "'"
}

function Get-VisibleRuntimeApprovalToken {
    param(
        [Parameter(Mandatory = $true)][string[]]$Fields
    )
    $payload = ($Fields -join "`n")
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha.ComputeHash($bytes)
    } finally {
        $sha.Dispose()
    }
    return ([System.BitConverter]::ToString($hash) -replace '-', '').ToLowerInvariant().Substring(0, 16)
}

function Get-TierDurationSec {
    param([string]$Name, [int]$CustomDuration)
    switch ($Name) {
        'short2' { return 120 }
        'short10' { return 600 }
        'short30' { return 1800 }
        'custom' {
            if ($CustomDuration -le 0) {
                throw 'Use -DurationSec with -Tier custom.'
            }
            return $CustomDuration
        }
        default { throw "Unknown tier: $Name" }
    }
}

function Get-RouteSteps {
    param([string]$RouteName, [string]$Points)
    switch ($RouteName) {
        'menu-idle' {
            return @()
        }
        'map-idle' {
            # Click steps carry ENGINE-space targets consumed by
            # tools/menu_pulse_click.py (centered main-menu Load ellipse center
            # measured at 302,211 on 2026-07-17; slot/confirm targets from
            # docs/hd/CLASH95_MENU_LOAD_ROUTE_NOTES.md engine hit zones).
            return @(
                [pscustomobject]@{ Name = 'load-button'; Points = '302,211'; Click = $true; WaitMs = $RouteStepWaitMs },
                [pscustomobject]@{ Name = 'load-slot0'; Points = '320,166'; Click = $true; WaitMs = $RouteStepWaitMs },
                [pscustomobject]@{ Name = 'confirm-load'; Points = '400,226'; Click = $true; WaitMs = [math]::Max($RouteStepWaitMs, 2200) }
            )
        }
        'map-pan' {
            return @(
                [pscustomobject]@{ Name = 'load-button'; Points = '302,211'; Click = $true; WaitMs = $RouteStepWaitMs },
                [pscustomobject]@{ Name = 'load-slot0'; Points = '320,166'; Click = $true; WaitMs = $RouteStepWaitMs },
                [pscustomobject]@{ Name = 'confirm-load'; Points = '400,226'; Click = $true; WaitMs = [math]::Max($RouteStepWaitMs, 2200) },
                [pscustomobject]@{ Name = 'pan-path'; Points = '400,300;680,300;680,520;120,520;120,120;400,300'; Click = $false; WaitMs = [math]::Max($RouteStepWaitMs, 2200) }
            )
        }
        'custom' {
            return @([pscustomobject]@{ Name = 'custom-points'; Points = $Points; Click = $true; WaitMs = [math]::Max($RouteStepWaitMs, 2200) })
        }
        default {
            throw "Unknown route: $RouteName"
        }
    }
}

function Invoke-MousePath {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$OutputJson,
        [string]$Points,
        [bool]$Click,
        [int]$SpacePulses = 0,
        [string]$MoveModeOverride = '',
        [string]$ClickModeOverride = '',
        [int]$ClickRepeatOverride = -1,
        [bool]$StopClickRepeatOnDrift = $false
    )

    $mouseTool = Join-Path $RepoRoot 'tools\mouse_path_probe.py'
    if (-not (Test-Path -LiteralPath $mouseTool -PathType Leaf)) {
        throw "Required mouse probe was not found: $mouseTool"
    }
    $effectiveMoveMode = if ($MoveModeOverride) { $MoveModeOverride } else { $MoveMode }
    $effectiveClickMode = if ($ClickModeOverride) { $ClickModeOverride } else { $ClickMode }
    $effectiveClickRepeat = if ($ClickRepeatOverride -ge 0) { $ClickRepeatOverride } else { $ClickRepeat }
    $args = @(
        $mouseTool,
        '--pid', "$($Process.Id)",
        '--workdir', $WorkDirFull,
        '--window-timeout', '12',
        '--settle-sec', '0.5',
        '--move-window', "$MoveWindowX", "$MoveWindowY",
        '--space-pulses', "$SpacePulses",
        '--space-interval-ms', '500',
        '--interval-ms', '300',
        '--move-mode', $effectiveMoveMode,
        '--points', $Points,
        '--window-stable-samples', "$WindowStableSamples",
        '--window-stable-poll-ms', "$WindowStablePollMs",
        '--window-stable-timeout-sec', "$WindowStableTimeoutSec",
        '--window-reacquire-attempts', "$WindowReacquireAttempts",
        '--window-reacquire-delay-ms', "$WindowReacquireDelayMs",
        '--json', $OutputJson
    )
    if ($Click) {
        $args += @('--click', '--click-mode', $effectiveClickMode, '--click-hold-ms', "$ClickHoldMs", '--click-repeat', "$effectiveClickRepeat")
    }
    if ($StopClickRepeatOnDrift) {
        $args += '--stop-click-repeat-on-drift'
    }

    $probeLog = [System.IO.Path]::ChangeExtension($OutputJson, '.log')
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $probeOutput = & $PythonFull @args 2>&1
        $exitCode = $LASTEXITCODE
    } catch {
        $probeOutput = @($_.Exception.Message)
        $exitCode = 1
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $probeOutput | Set-Content -LiteralPath $probeLog -Encoding ASCII

    if (Test-Path -LiteralPath $OutputJson -PathType Leaf) {
        $result = Get-Content -LiteralPath $OutputJson -Raw | ConvertFrom-Json
        $result | Add-Member -NotePropertyName ProbeExitCode -NotePropertyValue $exitCode -Force
        $result | Add-Member -NotePropertyName ProbeLog -NotePropertyValue $probeLog -Force
        $result | Add-Member -NotePropertyName EffectiveMoveMode -NotePropertyValue $effectiveMoveMode -Force
        $result | Add-Member -NotePropertyName EffectiveClickMode -NotePropertyValue $effectiveClickMode -Force
        $result | Add-Member -NotePropertyName EffectiveClickRepeat -NotePropertyValue $effectiveClickRepeat -Force
        $result | Add-Member -NotePropertyName WindowStable -NotePropertyValue ([bool]($result.window_stability -and $result.window_stability.stable)) -Force
        $result | Add-Member -NotePropertyName WindowLost -NotePropertyValue ([bool]$result.window_lost) -Force
        $result | Add-Member -NotePropertyName WindowReacquireCount -NotePropertyValue (Convert-NullableInt $result.window_reacquire_count) -Force
        return $result
    }

    return [pscustomobject]@{
        path_verified = $false
        click_path_verified = $false
        click_event_count = 0
        click_repeat_stop_observed = $false
        click_repeat_stop_reasons = @()
        WindowStable = $false
        WindowLost = $false
        WindowReacquireCount = $null
        ProbeExitCode = $exitCode
        ProbeLog = $probeLog
        ProbeError = "mouse_path_probe.py did not write JSON"
        EffectiveMoveMode = $effectiveMoveMode
        EffectiveClickMode = $effectiveClickMode
        EffectiveClickRepeat = $effectiveClickRepeat
    }
}

function Invoke-MenuPulseRoute {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$OutputJson,
        [object[]]$ClickSteps
    )

    $pulseTool = Join-Path $RepoRoot 'tools\menu_pulse_click.py'
    if (-not (Test-Path -LiteralPath $pulseTool -PathType Leaf)) {
        throw "Required pulse click tool was not found: $pulseTool"
    }
    $stepSpec = (@($ClickSteps | ForEach-Object { "{0}:{1}" -f $_.Name, $_.Points }) -join ';')
    $toolArgs = @(
        $pulseTool,
        '--pid', "$($Process.Id)",
        '--steps', $stepSpec,
        '--map-nonblack', "$MapReachedNonblackPercent",
        '--aim-tolerance', "$PulseAimTolerancePx",
        '--click-hold-ms', '700',
        '--click-repeats', '3',
        '--deadline-sec', '150',
        '--json', $OutputJson
    )
    $probeLog = [System.IO.Path]::ChangeExtension($OutputJson, '.log')
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $toolOutput = & $PythonFull '-W' 'ignore' @toolArgs 2>&1
        $exitCode = $LASTEXITCODE
    } catch {
        $toolOutput = @($_.Exception.Message)
        $exitCode = 1
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $toolOutput | Set-Content -LiteralPath $probeLog -Encoding ASCII

    $result = $null
    if (Test-Path -LiteralPath $OutputJson -PathType Leaf) {
        $result = Get-Content -LiteralPath $OutputJson -Raw | ConvertFrom-Json
    }
    [pscustomobject]@{
        Result = $result
        ExitCode = $exitCode
        Json = $OutputJson
        Log = $probeLog
        StepSpec = $stepSpec
    }
}

function Convert-PulseStepToRouteRow {
    param(
        [object]$PulseRun,
        [object]$StepRow,
        [object]$StepDefinition
    )

    $aim = if ($StepRow) { $StepRow.aim } else { $null }
    $skipped = [bool]($StepRow -and $StepRow.skipped_map_reached)
    $aimError = if ($aim -and $null -ne $aim.aim_error_px) { [int]$aim.aim_error_px } else { $null }
    $transitionVerified = [bool]($StepRow -and $StepRow.transition_verified)
    [pscustomobject]@{
        Name = $StepDefinition.Name
        Points = $StepDefinition.Points
        Click = $true
        InputMechanism = 'pulse-relative-engine-aim'
        PathVerified = ($skipped -or [bool]($aim -and $aim.converged))
        ClickPathVerified = ($skipped -or $transitionVerified)
        MaxAbsError = $null
        MaxSampleAbsError = $null
        AimErrorPx = $aimError
        AimTolerancePx = $PulseAimTolerancePx
        TransitionVerified = $transitionVerified
        SkippedMapReached = $skipped
        ChangedPixels = if ($StepRow -and $null -ne $StepRow.changed_pixels) { [int]$StepRow.changed_pixels } else { $null }
        PostNonblack = if ($StepRow -and $null -ne $StepRow.post_nonblack) { [double]$StepRow.post_nonblack } else { $null }
        ClickEventCount = if ($StepRow -and $null -ne $StepRow.click_count) { [int]$StepRow.click_count } else { 0 }
        ClickRepeatObserved = if ($StepRow -and $null -ne $StepRow.click_count) { [int]$StepRow.click_count } else { 0 }
        TransitionStopObserved = $false
        RepeatStopReasons = @()
        MoveMode = 'pulse-relative'
        ClickMode = 'sendinput-hold-while-pulsing'
        ClickRepeat = 3
        SpacePulses = 0
        InputProofClass = 'automated_visible_runtime_diagnostic_not_manual_directinput_release_proof'
        ProbeExitCode = $PulseRun.ExitCode
        Json = $PulseRun.Json
        Log = $PulseRun.Log
    }
}

function Save-ClientFrame {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$FramePath,
        [string]$FrameJson
    )

    $captureScript = Join-Path $RepoRoot 'scripts\capture\capture_clash_client_frame.ps1'
    if (-not (Test-Path -LiteralPath $captureScript -PathType Leaf)) {
        throw "Capture helper was not found: $captureScript"
    }

    $captureOutput = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $captureScript -AllowVisibleRuntime `
        -TargetProcessId $Process.Id `
        -Path $FramePath `
        -Json $FrameJson `
        -WindowTimeoutSec 8 2>&1
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "capture_clash_client_frame.ps1 failed with exit code $exitCode`: $captureOutput"
    }
    Get-Content -LiteralPath $FrameJson -Raw | ConvertFrom-Json
}

function Get-ProcessSnapshot {
    param([System.Diagnostics.Process]$Process)
    try {
        $Process.Refresh()
        [pscustomobject]@{
            Timestamp = (Get-Date).ToString('o')
            HasExited = [bool]$Process.HasExited
            ExitCode = if ($Process.HasExited) { $Process.ExitCode } else { $null }
            WorkingSet64 = if ($Process.HasExited) { $null } else { $Process.WorkingSet64 }
            PrivateMemorySize64 = if ($Process.HasExited) { $null } else { $Process.PrivateMemorySize64 }
            HandleCount = if ($Process.HasExited) { $null } else { $Process.HandleCount }
        }
    } catch {
        [pscustomobject]@{
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

function Select-NumberMin {
    param([object[]]$Values, [double]$Default = 0.0)
    $numbers = @($Values | Where-Object { $_ -ne $null } | ForEach-Object { [double]$_ })
    if (@($numbers).Count -eq 0) {
        return $Default
    }
    return [double](($numbers | Measure-Object -Minimum).Minimum)
}

function Select-NumberMax {
    param([object[]]$Values, [double]$Default = 0.0)
    $numbers = @($Values | Where-Object { $_ -ne $null } | ForEach-Object { [double]$_ })
    if (@($numbers).Count -eq 0) {
        return $Default
    }
    return [double](($numbers | Measure-Object -Maximum).Maximum)
}

function Convert-NullableInt {
    param([object]$Value)
    if ($null -eq $Value) {
        return $null
    }
    return [int]$Value
}

function Write-SoakMarkdown {
    param(
        [object]$Report,
        [string]$Path
    )

    $overallStatus = if ($Report.passed) { 'PASS' } else { 'FAIL' }
    function Format-NullableMetric {
        param([object]$Value)
        if ($null -eq $Value) {
            return 'n/a'
        }
        return "$Value"
    }
    $lines = @(
        '# HD Soak Short-Tier Report',
        '',
        "- Overall: $overallStatus",
        "- Generated: $($Report.generated_at)",
        "- Runtime policy: $($Report.runtime_policy)",
        "- Tier / route: $($Report.tier) / $($Report.route)",
        "- Duration seconds: $($Report.duration_sec)",
        "- Stage: $($Report.stage)",
        "- Candidate SHA-256: $($Report.candidate_sha256)",
        "- Output directory: $($Report.output_directory)",
        "- Frame samples: $($Report.frame_sample_count)",
        "- Unique frame hashes: $($Report.frame_hash_unique_count)",
        "- Frame stability class: $($Report.frame_stability_class)",
        "- Frame progress expected: $($Report.frame_progress_expected)",
        "- Nonblack min/max: $($Report.nonblack_percent_min) / $($Report.nonblack_percent_max)",
        "- Unique sampled colors min/max: $($Report.unique_sample_colors_min) / $($Report.unique_sample_colors_max)",
        "- Input max move drift px: $($Report.input_max_abs_error)",
        "- Input max sampled drift px: $($Report.input_max_sample_abs_error)",
        "- Input drift limit px: $($Report.max_input_drift_px)",
        "- Window mode: required=$($Report.window_mode.Required) display=$($Report.window_mode.Display) presentation=$($Report.window_mode.Presentation) config=$($Report.window_mode.Path)",
        "- Window hang observed: $($Report.window_hang_observed)",
        "- Window missing while process alive: $($Report.window_missing_while_alive_observed)",
        "- Window hidden while process alive: $($Report.window_hidden_while_alive_observed)",
        "- Wrapper error dialog: $($Report.wrapper_error_dialog_observed) $($Report.wrapper_error_dialog_text)",
        "- Input standing preflight: $($Report.input_standing.passed) (foreground owner $($Report.input_standing.foreground_process))",
        "- First window-health failure: $($Report.window_health_first_failure.Phase) / $($Report.window_health_first_failure.HealthClass)",
        "- Intro skip mode/repeat/pulses: $($Report.intro_skip.click_mode) / $($Report.intro_skip.click_repeat) / $($Report.intro_skip.space_pulses)",
        "- Intro skip proof class: $($Report.intro_skip.proof_class)",
        "- Intro menu verified: $($Report.intro_skip.menu_verified) (nonblack $($Report.intro_skip.menu_verify_nonblack_percent), rounds $($Report.intro_skip.rounds_used))",
        "- Map route reached: $($Report.map_route_reached) (final nonblack $($Report.route_final_nonblack_percent))",
        "- Working-set growth bytes: $(Format-NullableMetric $Report.working_set_growth_bytes)",
        "- Private-memory growth bytes: $(Format-NullableMetric $Report.private_memory_growth_bytes)",
        "- Handle growth: $(Format-NullableMetric $Report.handle_growth)",
        "- Artifact bytes: $($Report.artifact_bytes)",
        "- Artifact limit bytes: $(Format-NullableMetric $Report.artifact_limit_bytes)",
        "- Unexpected exit: $($Report.process_exited_unexpectedly)",
        "- Clean stop: $($Report.clean_stop)",
        "- Route marker: $($Report.final_route_marker)",
        "- Input proof class: $($Report.input_proof_class)",
        "- Right-bottom promotion remains blocked: $($Report.right_bottom_promotion_blocked)",
        ''
    )
    if (@($Report.failures).Count -gt 0) {
        $lines += '## Failures'
        $lines += ''
        foreach ($failure in $Report.failures) {
            $lines += "- $failure"
        }
        $lines += ''
    }
    $lines += '## Frame Samples'
    $lines += ''
    foreach ($frame in @($Report.frame_samples)) {
        $lines += "- $($frame.Name): hash=$($frame.Hash) nonblack=$($frame.NonblackPercent) luma=$($frame.MeanLuma) colors=$($frame.UniqueSampleColors) mode=$($frame.CaptureMode)"
    }
    $lines += ''
    $lines += '## Window Health Samples'
    $lines += ''
    foreach ($sample in @($Report.window_health_samples)) {
        $detail = ''
        if ($sample.HiddenWindowHwnd) {
            $detail += " hidden=$($sample.HiddenWindowHwnd) hiddenSize=$($sample.HiddenWindowClientWidth)x$($sample.HiddenWindowClientHeight)"
        }
        if ($sample.DialogText) {
            $detail += " dialog=$($sample.DialogText)"
        }
        $lines += "- $($sample.Phase): class=$($sample.HealthClass) hwnd=$($sample.Hwnd) size=$($sample.ClientWidth)x$($sample.ClientHeight)$detail"
    }
    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    $lines | Set-Content -LiteralPath $Path -Encoding ASCII
}

$DurationResolvedSec = Get-TierDurationSec -Name $Tier -CustomDuration $DurationSec
$InputExeFull = Resolve-PlanPath $InputExe
$CandidateDirFull = Resolve-PlanPath $CandidateDir
$WorkDirFull = Resolve-PlanPath $WorkDir
$OutputRootFull = Resolve-PlanPath $OutputRoot
$ReportJsonFull = Resolve-PlanPath $ReportJson
$ReportMarkdownFull = Resolve-PlanPath $ReportMarkdown
$PythonFull = Find-Python $Python
$windowedMode = Get-DxcfgWindowedStatus -Path (Join-Path $WorkDirFull 'dxcfg.ini')
if (-not $windowedMode.Passed) {
    throw "Windowed DirectDraw config check failed: $($windowedMode.Failures -join '; ')"
}
$inputStanding = Get-InputStandingStatus

function Test-AcceptedIntroTransition {
    param([Parameter(Mandatory = $true)][object]$Row)
    if ($Row.Name -ne 'intro-skip') {
        return $false
    }
    # Preferred acceptance: the harness verified the main menu on screen after
    # the intro-skip rounds (frame nonblack at menu levels).
    if ([bool]$Row.PSObject.Properties['MenuVerified'] -and [bool]$Row.MenuVerified) {
        return $true
    }
    return (
        [bool]$Row.Click -and
        [bool]$Row.PathVerified -and
        [bool]$Row.TransitionStopObserved -and
        ((Convert-NullableInt $Row.ClickRepeatObserved) -gt 0) -and
        (@($Row.RepeatStopReasons) -contains 'sample_drift_after_click') -and
        ($Row.ProbeExitCode -in @(0, 2))
    )
}

if (-not $CandidateName) {
    $CandidateName = 'clash95_hd_soak_{0}.exe' -f (Get-Date -Format 'yyyyMMdd_HHmmss')
}
if ([System.IO.Path]::GetExtension($CandidateName) -ne '.exe') {
    throw "CandidateName must end with .exe: $CandidateName"
}
$CandidateFull = Resolve-PlanPath (Join-Path $CandidateDirFull $CandidateName)
$RouteSteps = @(Get-RouteSteps -RouteName $Route -Points $CustomPoints)

if ((Test-IsUnderPath $CandidateDirFull $RepoRoot) -and -not $AllowRepoCandidateDir) {
    throw "Refusing candidate output inside repository by default: $CandidateDirFull"
}

$inputExists = Test-Path -LiteralPath $InputExeFull -PathType Leaf
$inputSha256 = $null
$baseShaStatus = 'missing'
if ($inputExists) {
    $inputSha256 = (Get-FileHash -LiteralPath $InputExeFull -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($inputSha256 -ne $ExpectedBaseSha256) {
        throw "Unexpected base SHA-256 for $InputExeFull. Expected $ExpectedBaseSha256 but found $inputSha256."
    }
    $baseShaStatus = 'ok'
}

$patchCommand = @(
    '&', (Quote-Arg $PythonFull), (Quote-Arg (Join-Path $RepoRoot 'patch_clash95_hd.py')),
    '--input', (Quote-Arg $InputExeFull),
    '--output', (Quote-Arg $CandidateFull),
    '--stage', (Quote-Arg $Stage)
) -join ' '
$approvalExpiryHours = 12
$minApprovalTtlMinutes = 30
$approvalExpiresUtc = if ($VisibleRuntimeApprovalExpiresUtc) {
    $VisibleRuntimeApprovalExpiresUtc
} else {
    [System.DateTimeOffset]::UtcNow.AddHours($approvalExpiryHours).ToString('o')
}
$approvalTokenFields = @(
    $InputExeFull,
    $WorkDirFull,
    $windowedMode.Sha256,
    $Stage,
    $Tier,
    $Route,
    [string]$DurationResolvedSec,
    $CandidateDirFull,
    $CandidateName,
    $OutputRootFull,
    $ReportJsonFull,
    $ReportMarkdownFull,
    $IntroSkipClickMode,
    [string]$IntroSkipClicks,
    [string]$IntroSkipStopClickRepeatOnDrift,
    [string]$SkipPulses,
    [string]$MaxInputDriftPx,
    [string]$SampleIntervalSec,
    [string]$MinNonblackPercent,
    [string]$MinUniqueSampleColors,
    [string]$MaxArtifactMB,
    [string]$MaxWorkingSetGrowthMB,
    [string]$MaxPrivateMemoryGrowthMB,
    [string]$MaxHandleGrowth,
    $approvalExpiresUtc
)
$expectedVisibleRuntimeApprovalToken = Get-VisibleRuntimeApprovalToken -Fields $approvalTokenFields
$executeCommand = @(
    'powershell.exe -NoProfile -ExecutionPolicy Bypass -File',
    (Quote-Arg (Join-Path $RepoRoot 'scripts\smoke\run_hd_soak.ps1')),
    '-InputExe', (Quote-Arg $InputExeFull),
    '-WorkDir', (Quote-Arg $WorkDirFull),
    '-Stage', (Quote-Arg $Stage),
    '-Tier', (Quote-Arg $Tier),
    '-Route', (Quote-Arg $Route),
    '-CandidateDir', (Quote-Arg $CandidateDirFull),
    '-CandidateName', (Quote-Arg $CandidateName),
    '-OutputRoot', (Quote-Arg $OutputRootFull),
    '-ReportJson', (Quote-Arg $ReportJsonFull),
    '-ReportMarkdown', (Quote-Arg $ReportMarkdownFull),
    '-IntroSkipClickMode', (Quote-Arg $IntroSkipClickMode),
    '-IntroSkipClicks', (Quote-Arg ([string]$IntroSkipClicks)),
    '-SkipPulses', (Quote-Arg ([string]$SkipPulses)),
    '-SampleIntervalSec', (Quote-Arg ([string]$SampleIntervalSec)),
    '-MaxInputDriftPx', (Quote-Arg ([string]$MaxInputDriftPx)),
    '-MinNonblackPercent', (Quote-Arg ([string]$MinNonblackPercent)),
    '-MinUniqueSampleColors', (Quote-Arg ([string]$MinUniqueSampleColors)),
    '-MaxArtifactMB', (Quote-Arg ([string]$MaxArtifactMB)),
    '-MaxWorkingSetGrowthMB', (Quote-Arg ([string]$MaxWorkingSetGrowthMB)),
    '-MaxPrivateMemoryGrowthMB', (Quote-Arg ([string]$MaxPrivateMemoryGrowthMB)),
    '-MaxHandleGrowth', (Quote-Arg ([string]$MaxHandleGrowth)),
    '-VisibleRuntimeApprovalExpiresUtc', (Quote-Arg $approvalExpiresUtc),
    '-VisibleRuntimeApprovalToken', (Quote-Arg $expectedVisibleRuntimeApprovalToken),
    '-Execute',
    '-AllowVisibleRuntime',
    '-RequirePass',
    '-Json'
) -join ' '

$plan = [ordered]@{
    dry_run = -not [bool]$Execute
    runtime_policy = 'opt-in visible runtime soak; use -Execute -AllowVisibleRuntime only after explicit user approval'
    repo_root = $RepoRoot
    input_exe = $InputExeFull
    input_exists = $inputExists
    expected_base_sha256 = $ExpectedBaseSha256
    input_sha256 = $inputSha256
    base_sha_status = $baseShaStatus
    stage = $Stage
    protected_stable_stage = $StableStage
    stable_stage_should_change = $false
    tier = $Tier
    duration_sec = $DurationResolvedSec
    route = $Route
    route_steps = $RouteSteps
    sample_interval_sec = $SampleIntervalSec
    candidate_dir = $CandidateDirFull
    candidate_path = $CandidateFull
    workdir = $WorkDirFull
    window_mode = $windowedMode
    input_standing = $inputStanding
    output_root = $OutputRootFull
    report_json = $ReportJsonFull
    report_markdown = $ReportMarkdownFull
    growth_limits = [ordered]@{
        max_working_set_growth_mb = $MaxWorkingSetGrowthMB
        max_private_memory_growth_mb = $MaxPrivateMemoryGrowthMB
        max_handle_growth = $MaxHandleGrowth
        max_artifact_mb = $MaxArtifactMB
    }
    frame_limits = [ordered]@{
        min_nonblack_percent = $MinNonblackPercent
        min_unique_sample_colors = $MinUniqueSampleColors
    }
    input_limits = [ordered]@{
        max_input_drift_px = $MaxInputDriftPx
    }
    window_health_policy = [ordered]@{
        probe = 'EnumWindows plus IsHungAppWindow; no synchronous target-window message'
        phases = 'after launch, after intro wait, before and after every route step, before every capture'
        stop_on_hung_or_missing_window = $true
        purpose = 'stop further input/capture at the first nonresponsive or missing application/windowed target'
    }
    intro_skip = [ordered]@{
        click_mode = $IntroSkipClickMode
        click_repeat = $IntroSkipClicks
        stop_click_repeat_on_drift = $IntroSkipStopClickRepeatOnDrift
        space_pulses = $SkipPulses
        proof_class = 'intro_skip_harness_prep_not_manual_directinput_release_proof'
    }
    visible_runtime_approval = [ordered]@{
        token = $expectedVisibleRuntimeApprovalToken
        token_kind = 'sha256-16'
        expires_utc = $approvalExpiresUtc
        max_age_hours = $approvalExpiryHours
        min_ttl_minutes = $minApprovalTtlMinutes
        token_fields = $approvalTokenFields
        purpose = 'copy-exact dry-run approval packet; edited, stale, or hand-typed visible runtime commands fail closed'
    }
    raw_artifacts_policy = 'raw PNG frames and per-step logs stay outside the repository by default'
    right_bottom_promotion_blocked = $true
    commands = [ordered]@{
        patch = $patchCommand
        execute = $executeCommand
    }
}

if (-not $Execute) {
    if ($Json) {
        $plan | ConvertTo-Json -Depth 8
    } else {
        Write-Host 'HD soak plan'
        Write-Host "Dry run: True"
        Write-Host "Runtime policy: $($plan.runtime_policy)"
        Write-Host "Stage: $Stage"
        Write-Host "Tier / route: $Tier / $Route"
        Write-Host "Duration seconds: $DurationResolvedSec"
        Write-Host "Candidate: $CandidateFull"
        Write-Host "Output root: $OutputRootFull"
        Write-Host "Report JSON: $ReportJsonFull"
        Write-Host "Report markdown: $ReportMarkdownFull"
        Write-Host ''
        Write-Host 'Patch command:'
        Write-Host $patchCommand
        Write-Host ''
        Write-Host 'Execute command:'
        Write-Host $executeCommand
    }
    exit 0
}

if (-not $AllowVisibleRuntime) {
    throw 'Soak execution launches and captures a visible Clash95 runtime. Re-run with -AllowVisibleRuntime only after explicit user approval.'
}
if (-not $VisibleRuntimeApprovalToken) {
    throw 'Visible runtime execution requires -VisibleRuntimeApprovalToken from a fresh dry-run approval packet.'
}
if (-not $VisibleRuntimeApprovalExpiresUtc) {
    throw 'Visible runtime execution requires -VisibleRuntimeApprovalExpiresUtc from a fresh dry-run approval packet.'
}
try {
    $approvalExpiry = [System.DateTimeOffset]::Parse(
        $VisibleRuntimeApprovalExpiresUtc,
        [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::AssumeUniversal
    ).ToUniversalTime()
} catch {
    throw "Visible runtime approval expiry is invalid: $VisibleRuntimeApprovalExpiresUtc"
}
if ([System.DateTimeOffset]::UtcNow -gt $approvalExpiry) {
    throw "Visible runtime approval expired at $($approvalExpiry.ToString('o')). Run a fresh dry-run and copy the new approval packet."
}
$approvalRemaining = $approvalExpiry - [System.DateTimeOffset]::UtcNow
if ($approvalRemaining -lt [System.TimeSpan]::FromMinutes($minApprovalTtlMinutes)) {
    throw "Visible runtime approval expires too soon at $($approvalExpiry.ToString('o')). Run a fresh dry-run so at least $minApprovalTtlMinutes minutes remain."
}
if ($VisibleRuntimeApprovalToken -ne $expectedVisibleRuntimeApprovalToken) {
    throw "Visible runtime approval token does not match this command shape. Expected $expectedVisibleRuntimeApprovalToken."
}
if (-not $inputStanding.Passed) {
    # Fail closed BEFORE launching. A run started without input standing cannot
    # deliver the intro-skip stimulus, cannot focus the game, and leaves the
    # DirectDraw wrapper in a failed display-mode state; letting it proceed
    # produces a false render/route failure instead of naming the real blocker.
    throw "Input standing preflight failed: $($inputStanding.Failures -join '; ')"
}
if (-not $inputExists) {
    throw "Input executable does not exist: $InputExeFull"
}
if (-not (Test-Path -LiteralPath $WorkDirFull -PathType Container)) {
    throw "Working directory does not exist: $WorkDirFull"
}
if ($SampleIntervalSec -le 0) {
    throw 'SampleIntervalSec must be positive.'
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$safeRoute = $Route -replace '[^0-9A-Za-z_.-]', '-'
$outDir = Join-Path $OutputRootFull "hd-soak-$stamp-$Tier-$safeRoute"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$process = $null
$scriptError = $null
$frameSamples = @()
$processSamples = @()
$routeResults = @()
$captureErrors = @()
$windowHealthSamples = @()
$cleanStop = $false
$stopSignalAt = $null
$candidateSha256 = $null
$patchStageReport = Join-Path $outDir 'patch-stage.json'
$introMenuVerified = $false
$introMenuVerifyNonblack = $null
$introRoundsUsed = 0
$mapRouteReached = $null
$routeFinalNonblack = $null
$launchAttemptRows = @()
$cursorProbeAlive = $false
$cursorProbeConverged = $false
$cursorProbeUsable = $false
$cursorProbeForegroundDenied = $false
$cursorProbeRequired = $false

try {
    if (-not $SkipPatch) {
        New-Item -ItemType Directory -Force -Path $CandidateDirFull | Out-Null
        if ((Test-Path -LiteralPath $CandidateFull -PathType Leaf) -and -not $ReuseCandidate) {
            throw "Candidate already exists: $CandidateFull"
        }
        if (-not (Test-Path -LiteralPath $CandidateFull -PathType Leaf)) {
            & $PythonFull (Join-Path $RepoRoot 'patch_clash95_hd.py') --input $InputExeFull --output $CandidateFull --stage $Stage
            if ($LASTEXITCODE -ne 0) {
                throw "patch_clash95_hd.py failed with exit code $LASTEXITCODE"
            }
        }
    } elseif (-not (Test-Path -LiteralPath $CandidateFull -PathType Leaf)) {
        throw "SkipPatch was set but candidate does not exist: $CandidateFull"
    }

    $candidateSha256 = (Get-FileHash -LiteralPath $CandidateFull -Algorithm SHA256).Hash
    $patchArgs = @(
        (Join-Path $RepoRoot 'tools\patch_stage_report.py'),
        '--exe', $CandidateFull,
        '--stage', $Stage,
        '--write-json', $patchStageReport
    )
    if ($Stage -eq $StableStage) {
        $patchArgs += '--require-current-hd-map'
    }
    & $PythonFull @patchArgs
    if ($LASTEXITCODE -ne 0) {
        throw "patch_stage_report.py failed with exit code $LASTEXITCODE"
    }

    # LAUNCH ATTEMPTS: the menu is bimodal on this machine. If the intro-skip
    # stimuli land, the interactive menu appears (engine cursor responds to
    # pulse input); if the intro instead auto-plays out, the menu comes up in
    # a dead attract-like state where no automated input reaches the engine
    # cursor and the wrapper later transitions the window (the 2026-07-14/15
    # window_missing failures). A fresh relaunch re-rolls the race, so each
    # attempt runs intro rounds and (for click routes) a no-click pulse probe
    # that verifies the engine cursor is alive before the route is trusted.
    $cursorProbeRequired = ($Route -in @('map-idle', 'map-pan'))
    $launchAttemptRows = @()
    $cursorProbeAlive = $false
    $cursorProbeConverged = $false
    $cursorProbeUsable = $false
    $cursorProbeForegroundDenied = $false
    $introClick = ($IntroSkipClickMode -ne 'none') -and ($IntroSkipClicks -gt 0)
    $introRoundCount = $IntroSkipMaxRounds
    $introClicksPerRound = if ($introClick) { $IntroSkipClicks } else { 0 }
    $introPulsesPerRound = $SkipPulses
    $process = $null
    for ($launchAttempt = 1; $launchAttempt -le $MaxLaunchAttempts; $launchAttempt++) {
        if ($null -ne $process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds $RelaunchSettleMs
        }
        $process = Start-Process -FilePath $CandidateFull -WorkingDirectory $WorkDirFull -PassThru
        Start-Sleep -Milliseconds 800
        $windowHealthSamples += Get-WindowHealthSample -Process $process -Phase 'after-launch'

        # Intro skip runs as verified ROUNDS: the intro length varies run to
        # run (single-shot skips raced it and sampled story screens on
        # 2026-07-14). Each round replays the pinned single-shot budget
        # (IntroSkipClicks postmessage clicks with drift stop, SkipPulses
        # space pulses) and ends with a menu-fingerprint frame check.
        $introMenuVerified = $false
        $introMenuVerifyNonblack = $null
        $introRoundsUsed = 0
        $introRoundRows = @()
        $introJson = $null
        $introResult = $null
        for ($introRound = 0; $introRound -lt $introRoundCount; $introRound++) {
            $process.Refresh()
            if ($process.HasExited) {
                break
            }
            $introRoundsUsed = $introRound + 1
            $introJson = Join-Path $outDir ("intro-skip-a{0}-round-{1}.json" -f $launchAttempt, $introRound)
            $introResult = Invoke-MousePath -Process $process -OutputJson $introJson -Points '400,300' -Click $introClick -SpacePulses $introPulsesPerRound -ClickModeOverride $IntroSkipClickMode -ClickRepeatOverride $introClicksPerRound -StopClickRepeatOnDrift $IntroSkipStopClickRepeatOnDrift
            $introRoundRows += $introResult
            Start-Sleep -Seconds 2
            $menuCheckPng = Join-Path $outDir ("intro-menucheck-a{0}-{1}.png" -f $launchAttempt, $introRound)
            $menuCheckJson = Join-Path $outDir ("intro-menucheck-a{0}-{1}.json" -f $launchAttempt, $introRound)
            try {
                $menuCheck = Save-ClientFrame -Process $process -FramePath $menuCheckPng -FrameJson $menuCheckJson
                $introMenuVerifyNonblack = [double]$menuCheck.NonblackPercent
                $menuCheckColors = [int]$menuCheck.UniqueSampleColors
                # Menu fingerprint: nonblack in the menu band, a small static
                # palette, and a STABLE frame (bright intro/logo/movie frames
                # can pass a plain nonblack floor but fail band+palette+
                # stability).
                $menuBandOk = (
                    $introMenuVerifyNonblack -ge $IntroMenuVerifyNonblackPercent -and
                    $introMenuVerifyNonblack -le $IntroMenuVerifyNonblackMaxPercent -and
                    $menuCheckColors -le $IntroMenuVerifyMaxUniqueColors
                )
                if ($menuBandOk) {
                    Start-Sleep -Milliseconds 800
                    $menuCheck2Png = Join-Path $outDir ("intro-menucheck-a{0}-{1}b.png" -f $launchAttempt, $introRound)
                    $menuCheck2Json = Join-Path $outDir ("intro-menucheck-a{0}-{1}b.json" -f $launchAttempt, $introRound)
                    $menuCheck2 = Save-ClientFrame -Process $process -FramePath $menuCheck2Png -FrameJson $menuCheck2Json
                    if ($menuCheck2.Hash -eq $menuCheck.Hash) {
                        $introMenuVerified = $true
                        break
                    }
                }
            } catch {
                # capture failures during intro transitions are tolerated; the
                # next round retries and window health is sampled after the loop
            }
        }

        $cursorProbeExitCode = $null
        $cursorProbeJson = $null
        if ($introMenuVerified -and $cursorProbeRequired) {
            $cursorProbeJson = Join-Path $outDir ("cursor-probe-a{0}.json" -f $launchAttempt)
            $probeArgs = @(
                (Join-Path $RepoRoot 'tools\menu_pulse_click.py'),
                '--pid', "$($process.Id)",
                '--steps', 'cursor-probe:200,150',
                '--probe-only',
                '--map-nonblack', '0',
                '--aim-tolerance', "$PulseAimTolerancePx",
                '--deadline-sec', '45',
                '--json', $cursorProbeJson
            )
            $previousEap = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            try {
                & $PythonFull '-W' 'ignore' @probeArgs 2>&1 | Set-Content -LiteralPath ([System.IO.Path]::ChangeExtension($cursorProbeJson, '.log')) -Encoding ASCII
                $cursorProbeExitCode = $LASTEXITCODE
            } finally {
                $ErrorActionPreference = $previousEap
            }
            # menu_pulse_click.py exits 0 only when the aim CONVERGED *and* the
            # engine cursor responded, so exit code alone cannot tell "the
            # cursor is dead" apart from "the cursor moved but aim did not
            # converge". Read the probe JSON for the real signals: a converge
            # failure with cursor_alive:true and a measured gain is a very
            # different defect from a cursor that never moved, and reporting
            # the wrong one sent the 2026-07-18 run chasing a phantom.
            $cursorProbeConverged = ($cursorProbeExitCode -eq 0)
            $cursorProbeAlive = $cursorProbeConverged
            $cursorProbeForegroundDenied = $false
            if ($cursorProbeJson -and (Test-Path -LiteralPath $cursorProbeJson -PathType Leaf)) {
                try {
                    $probePayload = Get-Content -LiteralPath $cursorProbeJson -Raw | ConvertFrom-Json
                    if ($null -ne $probePayload.cursor_alive) {
                        $cursorProbeAlive = [bool]$probePayload.cursor_alive
                    }
                    $aimRows = @($probePayload.steps | ForEach-Object { $_.aim } | Where-Object { $_ })
                    if (@($aimRows).Count -gt 0) {
                        $cursorProbeConverged = (@($aimRows | Where-Object { -not [bool]$_.converged }).Count -eq 0)
                    }
                    $foregroundFlags = @($aimRows | ForEach-Object { @($_.iterations) } | Where-Object { $_ -and ($null -ne $_.foreground_ok) })
                    if (@($foregroundFlags).Count -gt 0) {
                        $cursorProbeForegroundDenied = (@($foregroundFlags | Where-Object { [bool]$_.foreground_ok }).Count -eq 0)
                    }
                } catch {
                    # an unreadable probe JSON leaves the exit-code-derived
                    # values in place; the probe log is retained either way
                }
            }
            # Route gating stays on the STRICT signal: an unconverged aim must
            # never be trusted to click into the game, even if the cursor moved.
            $cursorProbeUsable = ($cursorProbeExitCode -eq 0)
        }
        $launchAttemptRows += [pscustomobject]@{
            Attempt = $launchAttempt
            MenuVerified = $introMenuVerified
            MenuVerifyNonblackPercent = $introMenuVerifyNonblack
            IntroRoundsUsed = $introRoundsUsed
            CursorProbeRequired = $cursorProbeRequired
            CursorProbeExitCode = $cursorProbeExitCode
            CursorProbeAlive = $cursorProbeAlive
            CursorProbeConverged = $cursorProbeConverged
            CursorProbeUsable = $cursorProbeUsable
            CursorProbeForegroundDenied = $cursorProbeForegroundDenied
            CursorProbeJson = $cursorProbeJson
        }
        if ($introMenuVerified -and ((-not $cursorProbeRequired) -or $cursorProbeUsable)) {
            break
        }
    }
    $introClickEvents = [int](@($introRoundRows | ForEach-Object { Convert-NullableInt $_.click_event_count } | Where-Object { $null -ne $_ }) | Measure-Object -Sum).Sum
    $introStopReasons = @($introRoundRows | ForEach-Object { @($_.click_repeat_stop_reasons) } | Where-Object { $_ })
    $routeResults += [pscustomobject]@{
        Name = 'intro-skip'
        Points = '400,300'
        Click = $introClick
        PathVerified = (@($introRoundRows | Where-Object { [bool]$_.path_verified }).Count -gt 0)
        ClickPathVerified = (@($introRoundRows | Where-Object { [bool]$_.click_path_verified }).Count -gt 0)
        MaxAbsError = if ($introResult) { Convert-NullableInt $introResult.max_abs_error } else { $null }
        MaxSampleAbsError = if ($introResult) { Convert-NullableInt $introResult.max_sample_abs_error } else { $null }
        ClickEventCount = $introClickEvents
        ClickRepeatObserved = $introClickEvents
        TransitionStopObserved = (@($introRoundRows | Where-Object { [bool]$_.click_repeat_stop_observed }).Count -gt 0)
        RepeatStopReasons = $introStopReasons
        MenuVerified = $introMenuVerified
        MenuVerifyNonblackPercent = $introMenuVerifyNonblack
        MenuVerifyThresholdPercent = $IntroMenuVerifyNonblackPercent
        IntroRoundsUsed = $introRoundsUsed
        IntroRoundBudget = $introRoundCount
        WindowStable = (@($introRoundRows | Where-Object { [bool]$_.WindowStable }).Count -gt 0)
        WindowLostObserved = (@($introRoundRows | Where-Object { [bool]$_.WindowLost }).Count -gt 0)
        WindowReacquireCount = [int](@($introRoundRows | ForEach-Object { Convert-NullableInt $_.WindowReacquireCount } | Where-Object { $null -ne $_ }) | Measure-Object -Sum).Sum
        MoveMode = if ($introResult) { $introResult.EffectiveMoveMode } else { $MoveMode }
        ClickMode = $IntroSkipClickMode
        ClickRepeat = $IntroSkipClicks
        SpacePulses = $SkipPulses
        InputProofClass = 'intro_skip_harness_prep_not_manual_directinput_release_proof'
        ProbeExitCode = if ($introResult) { $introResult.ProbeExitCode } else { 1 }
        Json = $introJson
        Log = if ($introResult) { $introResult.ProbeLog } else { $null }
    }
    $introHealth = Get-WindowHealthSample -Process $process -Phase 'after-intro-wait'
    $windowHealthSamples += $introHealth
    $routeWindowHealthStop = ($introHealth.HealthClass -ne 'responsive')

    $pulseRouteSteps = @()
    $legacyRouteSteps = @()
    foreach ($step in $RouteSteps) {
        if ([bool]$step.Click -and ($Route -in @('map-idle', 'map-pan'))) {
            $pulseRouteSteps += $step
        } else {
            $legacyRouteSteps += $step
        }
    }

    if (@($pulseRouteSteps).Count -gt 0 -and ((-not $introMenuVerified) -or ($cursorProbeRequired -and -not $cursorProbeUsable))) {
        # Fail closed: never aim/click into unverified screens (story pages,
        # transition frames, or a dead attract-state menu); the missing menu/
        # cursor verification is already a reported failure and the
        # map-reached gate will also fail.
        $pulseRouteSteps = @()
    }
    if (@($pulseRouteSteps).Count -gt 0 -and -not $process.HasExited -and -not $routeWindowHealthStop) {
        $prePulseHealth = Get-WindowHealthSample -Process $process -Phase 'before-pulse-route'
        $windowHealthSamples += $prePulseHealth
        if ($prePulseHealth.HealthClass -ne 'responsive') {
            $routeWindowHealthStop = $true
        } else {
            $pulseJson = Join-Path $outDir 'route-pulse-clicks.json'
            $pulseRun = Invoke-MenuPulseRoute -Process $process -OutputJson $pulseJson -ClickSteps $pulseRouteSteps
            $pulseSteps = @()
            if ($pulseRun.Result -and $pulseRun.Result.steps) {
                $pulseSteps = @($pulseRun.Result.steps)
            }
            foreach ($stepDefinition in $pulseRouteSteps) {
                $stepRow = $pulseSteps | Where-Object { $_.name -eq $stepDefinition.Name } | Select-Object -First 1
                $routeResults += Convert-PulseStepToRouteRow -PulseRun $pulseRun -StepRow $stepRow -StepDefinition $stepDefinition
            }
            if ($pulseRun.Result) {
                $mapRouteReached = [bool]$pulseRun.Result.map_reached
                $routeFinalNonblack = if ($null -ne $pulseRun.Result.final_nonblack) { [double]$pulseRun.Result.final_nonblack } else { $null }
            }
            Start-Sleep -Milliseconds 1200
            $postPulseHealth = Get-WindowHealthSample -Process $process -Phase 'after-pulse-route-wait'
            $windowHealthSamples += $postPulseHealth
            if ($postPulseHealth.HealthClass -ne 'responsive') {
                $routeWindowHealthStop = $true
            }
        }
    }

    foreach ($step in $legacyRouteSteps) {
        if ($process.HasExited -or $routeWindowHealthStop) {
            break
        }
        $preStepHealth = Get-WindowHealthSample -Process $process -Phase ("before-{0}" -f $step.Name)
        $windowHealthSamples += $preStepHealth
        if ($preStepHealth.HealthClass -ne 'responsive') {
            $routeWindowHealthStop = $true
            break
        }
        $safeStepName = $step.Name -replace '[^0-9A-Za-z_.-]', '-'
        $stepJson = Join-Path $outDir ("route-{0}.json" -f $safeStepName)
        $stepResult = Invoke-MousePath -Process $process -OutputJson $stepJson -Points $step.Points -Click ([bool]$step.Click)
        $routeResults += [pscustomobject]@{
            Name = $step.Name
            Points = $step.Points
            Click = [bool]$step.Click
            PathVerified = [bool]$stepResult.path_verified
            ClickPathVerified = [bool]$stepResult.click_path_verified
            MaxAbsError = Convert-NullableInt $stepResult.max_abs_error
            MaxSampleAbsError = Convert-NullableInt $stepResult.max_sample_abs_error
            ClickEventCount = Convert-NullableInt $stepResult.click_event_count
            ClickRepeatObserved = Convert-NullableInt $stepResult.click_event_count
            TransitionStopObserved = [bool]$stepResult.click_repeat_stop_observed
            RepeatStopReasons = @($stepResult.click_repeat_stop_reasons)
            WindowStable = [bool]$stepResult.WindowStable
            WindowLostObserved = [bool]$stepResult.WindowLost
            WindowReacquireCount = Convert-NullableInt $stepResult.WindowReacquireCount
            MoveMode = $stepResult.EffectiveMoveMode
            ClickMode = $stepResult.EffectiveClickMode
            ClickRepeat = $stepResult.EffectiveClickRepeat
            SpacePulses = 0
            InputProofClass = 'automated_visible_runtime_diagnostic_not_manual_directinput_release_proof'
            ProbeExitCode = $stepResult.ProbeExitCode
            Json = $stepJson
            Log = $stepResult.ProbeLog
        }
        Start-Sleep -Milliseconds ([int]$step.WaitMs)
        $postStepHealth = Get-WindowHealthSample -Process $process -Phase ("after-{0}-wait" -f $step.Name)
        $windowHealthSamples += $postStepHealth
        if ($postStepHealth.HealthClass -ne 'responsive') {
            $routeWindowHealthStop = $true
            break
        }
    }

    $deadline = (Get-Date).AddSeconds($DurationResolvedSec)
    $sampleIndex = 0
    do {
        $processSamples += Get-ProcessSnapshot -Process $process
        if ($process.HasExited) {
            break
        }

        $captureHealth = Get-WindowHealthSample -Process $process -Phase ("before-frame-{0:D4}" -f $sampleIndex)
        $windowHealthSamples += $captureHealth
        if ($captureHealth.HealthClass -ne 'responsive') {
            $captureErrors += [pscustomobject]@{
                Timestamp = (Get-Date).ToString('o')
                Frame = ('frame-{0:D4}' -f $sampleIndex)
                Error = "capture skipped because window health was $($captureHealth.HealthClass)"
            }
            break
        }

        $frameName = 'frame-{0:D4}' -f $sampleIndex
        $framePath = Join-Path $outDir "$frameName.png"
        $frameJson = Join-Path $outDir "$frameName.json"
        try {
            $frame = Save-ClientFrame -Process $process -FramePath $framePath -FrameJson $frameJson
            $frame | Add-Member -NotePropertyName Name -NotePropertyValue $frameName -Force
            $frame | Add-Member -NotePropertyName Timestamp -NotePropertyValue (Get-Date).ToString('o') -Force
            $frameSamples += $frame
        } catch {
            $captureErrors += [pscustomobject]@{
                Timestamp = (Get-Date).ToString('o')
                Frame = $frameName
                Error = $_.Exception.Message
            }
        }

        $sampleIndex++
        $remaining = [int][math]::Ceiling(($deadline - (Get-Date)).TotalSeconds)
        if ($remaining -le 0) {
            break
        }
        Start-Sleep -Seconds ([math]::Min($SampleIntervalSec, $remaining))
    } while ((Get-Date) -lt $deadline)

    $processSamples += Get-ProcessSnapshot -Process $process
} catch {
    $scriptError = $_
} finally {
    if ($process -and -not $process.HasExited -and -not $KeepOpen) {
        # Record the teardown boundary BEFORE the kill so frame evidence can be
        # partitioned against it. Anything sampled at or after this instant is
        # shutdown imagery, not render evidence.
        $stopSignalAt = (Get-Date)
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        $cleanStop = $true
    }
}

$artifactBytes = Get-DirectorySizeBytes -Path $outDir
$artifactLimitBytes = [int64]$MaxArtifactMB * 1024L * 1024L
# RENDER EVIDENCE PARTITION.
#
# Two things disqualify a captured frame as evidence of what the game rendered:
#
#  1. It was sampled at or after the teardown signal (shutdown imagery).
#  2. It came through a different capture path than the rest of the run.
#
# (2) is what broke the 2026-07-18 short2 run. capture_clash_client_frame.ps1
# picks 'screen' (CopyFromScreen) when the target owns its client-centre point
# and 'windowdc-contaminated-fallback' (BitBlt from the window DC) otherwise.
# For this DirectDraw title the two paths do NOT observe the same pixels: the
# run captured seven byte-identical windowdc frames of a healthy 60.487%-nonblack
# menu and one 'screen' frame that came back black, and the black outlier alone
# dragged nonblack_percent_min to 0.017 and produced a FALSE render regression.
# A frame captured through a minority path is not comparable to the others, so
# it is excluded from the render metrics and reported as a capture-harness
# inconsistency instead of a rendering defect.
$captureModeValues = @($frameSamples | ForEach-Object { $_.CaptureMode } | Where-Object { $_ })
$captureModeGroups = @($captureModeValues | Group-Object | Sort-Object -Property Count -Descending)
$dominantCaptureMode = if (@($captureModeGroups).Count -gt 0) { @($captureModeGroups)[0].Name } else { $null }
$captureModeCounts = [ordered]@{}
foreach ($group in $captureModeGroups) { $captureModeCounts[$group.Name] = $group.Count }
$captureModeChanged = (@($captureModeGroups).Count -gt 1)

foreach ($frame in $frameSamples) {
    $reasons = @()
    if ($null -ne $stopSignalAt -and $frame.Timestamp) {
        try {
            if ([datetime]::Parse($frame.Timestamp) -ge $stopSignalAt) { $reasons += 'captured_after_stop_signal' }
        } catch {
            # an unparsable timestamp is not grounds to discard the frame
        }
    }
    if ($dominantCaptureMode -and $frame.CaptureMode -and ($frame.CaptureMode -ne $dominantCaptureMode)) {
        $reasons += 'minority_capture_mode'
    }
    $frame | Add-Member -NotePropertyName RenderEvidence -NotePropertyValue (@($reasons).Count -eq 0) -Force
    $frame | Add-Member -NotePropertyName RenderEvidenceExcludedReasons -NotePropertyValue @($reasons) -Force
}
$renderEvidenceFrames = @($frameSamples | Where-Object { [bool]$_.RenderEvidence })
$excludedFrames = @($frameSamples | Where-Object { -not [bool]$_.RenderEvidence })

# Frame progression is render evidence too: a minority-capture-path frame hashes
# differently for reasons that have nothing to do with the game drawing a new
# scene, which would let a stalled map-pan masquerade as progressing.
$frameHashes = @($renderEvidenceFrames | ForEach-Object { $_.Hash } | Where-Object { $_ })
$uniqueFrameHashes = @($frameHashes | Sort-Object -Unique)
$frameProgressExpected = ($Route -eq 'map-pan')
$frameStabilityClass = if (@($renderEvidenceFrames).Count -eq 0) {
    'no_frames'
} elseif (@($uniqueFrameHashes).Count -le 1) {
    'stable_idle'
} else {
    'progressing'
}

$nonblackValues = @($renderEvidenceFrames | ForEach-Object { $_.NonblackPercent })
$lumaValues = @($renderEvidenceFrames | ForEach-Object { $_.MeanLuma })
$uniqueColorValues = @($renderEvidenceFrames | ForEach-Object { $_.UniqueSampleColors })
$widthValues = @($frameSamples | ForEach-Object { $_.Width })
$heightValues = @($frameSamples | ForEach-Object { $_.Height })
$workingSetValues = @($processSamples | ForEach-Object { $_.WorkingSet64 } | Where-Object { $_ -ne $null })
$privateMemoryValues = @($processSamples | ForEach-Object { $_.PrivateMemorySize64 } | Where-Object { $_ -ne $null })
$handleValues = @($processSamples | ForEach-Object { $_.HandleCount } | Where-Object { $_ -ne $null })
$workingSetGrowthBytes = if (@($workingSetValues).Count -ge 2) { [int64](@($workingSetValues)[-1] - @($workingSetValues)[0]) } else { $null }
$privateMemoryGrowthBytes = if (@($privateMemoryValues).Count -ge 2) { [int64](@($privateMemoryValues)[-1] - @($privateMemoryValues)[0]) } else { $null }
$handleGrowth = if (@($handleValues).Count -ge 2) { [int](@($handleValues)[-1] - @($handleValues)[0]) } else { $null }
$workingSetLimitBytes = [int64]$MaxWorkingSetGrowthMB * 1024L * 1024L
$privateMemoryLimitBytes = [int64]$MaxPrivateMemoryGrowthMB * 1024L * 1024L
$inputMaxAbsValues = @($routeResults | ForEach-Object { $_.MaxAbsError } | Where-Object { $_ -ne $null })
$inputMaxSampleAbsValues = @($routeResults | ForEach-Object { $_.MaxSampleAbsError } | Where-Object { $_ -ne $null })
$inputMaxAbsError = if (@($inputMaxAbsValues).Count -gt 0) { [int](Select-NumberMax -Values $inputMaxAbsValues) } else { $null }
$inputMaxSampleAbsError = if (@($inputMaxSampleAbsValues).Count -gt 0) { [int](Select-NumberMax -Values $inputMaxSampleAbsValues) } else { $null }
$windowHangSamples = @($windowHealthSamples | Where-Object { $_.HealthClass -eq 'application_hung' })
$windowHiddenWhileAliveSamples = @($windowHealthSamples | Where-Object { $_.HealthClass -eq 'window_hidden_while_process_alive' })
$wrapperErrorDialogSamples = @($windowHealthSamples | Where-Object { $_.HealthClass -eq 'wrapper_error_dialog' })
# The three no-visible-window classes are reported separately but all keep
# tripping the existing observed flag, so no gate is loosened by the split.
$windowMissingWhileAliveSamples = @($windowHealthSamples | Where-Object {
    $_.HealthClass -in @('window_missing_while_process_alive', 'window_hidden_while_process_alive', 'wrapper_error_dialog')
})
$windowHealthFailureSamples = @($windowHealthSamples | Where-Object { $_.HealthClass -ne 'responsive' -and $_.HealthClass -ne 'process_exited' })
$windowHangObserved = (@($windowHangSamples).Count -gt 0)
$windowMissingWhileAliveObserved = (@($windowMissingWhileAliveSamples).Count -gt 0)
$windowHiddenWhileAliveObserved = (@($windowHiddenWhileAliveSamples).Count -gt 0)
$wrapperErrorDialogObserved = (@($wrapperErrorDialogSamples).Count -gt 0)
$wrapperErrorDialogText = if ($wrapperErrorDialogObserved) { @($wrapperErrorDialogSamples)[0].DialogText } else { $null }
$windowHealthFirstFailure = if (@($windowHealthFailureSamples).Count -gt 0) { @($windowHealthFailureSamples)[0] } else { $null }
$unexpectedExit = $false
$exitCode = $null
if ($process) {
    try {
        $process.Refresh()
        $unexpectedExit = [bool]$process.HasExited -and -not $cleanStop
        if ($process.HasExited) {
            $exitCode = $process.ExitCode
        }
    } catch {
        $unexpectedExit = $true
    }
}

$routeFailures = @($routeResults | Where-Object {
    (-not (Test-AcceptedIntroTransition -Row $_)) -and
    ((-not $_.PathVerified) -or ($_.Click -and -not $_.ClickPathVerified) -or ($_.ProbeExitCode -notin @(0, 2)))
})
$routeDriftFailures = @($routeResults | Where-Object {
    if ([bool]$_.PSObject.Properties['InputMechanism'] -and $_.InputMechanism -eq 'pulse-relative-engine-aim') {
        # Pulse rows prove ENGINE-space aim + observed frame transition instead
        # of OS-cursor drift (the menu never reads the OS cursor).
        ($_.ProbeExitCode -ne 0) -or
        ((-not [bool]$_.SkippedMapReached) -and (
            ($null -eq $_.AimErrorPx) -or
            ([int]$_.AimErrorPx -gt [int]$_.AimTolerancePx) -or
            (-not [bool]$_.TransitionVerified)
        ))
    } else {
        ($null -eq $_.MaxAbsError) -or
        ([int]$_.MaxAbsError -gt $MaxInputDriftPx) -or
        ($_.ProbeExitCode -notin @(0, 2)) -or
        ($_.Click -and (-not (Test-AcceptedIntroTransition -Row $_)) -and (($null -eq $_.MaxSampleAbsError) -or ([int]$_.MaxSampleAbsError -gt $MaxInputDriftPx)))
    }
})
$failures = @()
if ($scriptError) { $failures += $scriptError.Exception.Message }
if ($windowHangObserved) { $failures += 'application window became nonresponsive during the soak route' }
if ($windowMissingWhileAliveObserved) { $failures += 'visible application window disappeared while the process remained alive' }
if ($wrapperErrorDialogObserved) {
    $failures += "the DirectDraw wrapper raised a modal error dialog while the application window was hidden: $wrapperErrorDialogText"
}
elseif ($windowHiddenWhileAliveObserved) {
    $failures += 'the application window was hidden (WS_VISIBLE cleared) but still alive; the wrapper failed a display transition rather than tearing the window down'
}
if ($unexpectedExit) { $failures += "process exited unexpectedly with code $exitCode" }
if (@($captureErrors).Count -gt 0) { $failures += "capture errors: $(@($captureErrors).Count)" }
if ($captureModeChanged) {
    $modeSummary = (@($captureModeGroups | ForEach-Object { "$($_.Name)=$($_.Count)" }) -join ', ')
    $failures += "capture mode changed mid-run; observed ${modeSummary}; frames from different capture paths are not comparable render evidence"
}
if (@($frameSamples).Count -lt 2) { $failures += "expected at least 2 frame samples" }
if (@($renderEvidenceFrames).Count -lt 2) { $failures += "expected at least 2 render-evidence frame samples" }
if ($frameProgressExpected -and @($uniqueFrameHashes).Count -lt 2) {
    $failures += 'frame progression required for map-pan route'
}
if (@($processSamples).Count -lt 2) { $failures += "expected at least 2 process samples" }
if (@($widthValues | Where-Object { $_ -ne 800 }).Count -gt 0 -or @($heightValues | Where-Object { $_ -ne 600 }).Count -gt 0) {
    $failures += 'one or more frame samples were not 800x600'
}
if ((Select-NumberMin -Values $nonblackValues) -lt $MinNonblackPercent) {
    $failures += "nonblack percent dropped below $MinNonblackPercent"
}
if ((Select-NumberMin -Values $uniqueColorValues) -lt $MinUniqueSampleColors) {
    $failures += "unique sampled colors dropped below $MinUniqueSampleColors"
}
if (@($routeFailures).Count -gt 0) {
    $failures += "route/input probe failures: $(@($routeFailures).Count)"
}
if (@($routeDriftFailures).Count -gt 0) {
    $failures += "input drift exceeded ${MaxInputDriftPx}px or metric missing: $(@($routeDriftFailures).Count)"
}
if ($null -ne $process -and -not $introMenuVerified) {
    $failures += 'intro skip rounds never verified the main menu on screen'
}
if ($null -ne $process -and $cursorProbeRequired -and -not $cursorProbeUsable) {
    # Report what actually happened. "Never responded" is only true when the
    # engine cursor produced no position at all; a cursor that moved but whose
    # aim did not converge, and a cursor starved of input because foreground
    # activation was denied, are three distinct defects.
    if ($cursorProbeForegroundDenied) {
        $failures += 'engine cursor input was never delivered (SetForegroundWindow denied on every aim iteration; the harness had no input standing)'
    } elseif ($cursorProbeAlive) {
        $failures += 'engine cursor responded to pulse input but aim never converged on the probe target'
    } else {
        $failures += 'no launch attempt produced an interactive menu (engine cursor never responded to pulse input)'
    }
}
if ($Route -in @('map-idle', 'map-pan') -and $mapRouteReached -ne $true) {
    $failures += 'route did not reach the gameplay map'
}
if ($null -eq $workingSetGrowthBytes) {
    $failures += 'working-set growth metric unavailable'
} elseif ($workingSetGrowthBytes -gt $workingSetLimitBytes) {
    $failures += "working-set growth exceeded ${MaxWorkingSetGrowthMB}MB"
}
if ($null -eq $privateMemoryGrowthBytes) {
    $failures += 'private-memory growth metric unavailable'
} elseif ($privateMemoryGrowthBytes -gt $privateMemoryLimitBytes) {
    $failures += "private-memory growth exceeded ${MaxPrivateMemoryGrowthMB}MB"
}
if ($null -eq $handleGrowth) {
    $failures += 'handle growth metric unavailable'
} elseif ($handleGrowth -gt $MaxHandleGrowth) {
    $failures += "handle growth exceeded $MaxHandleGrowth"
}
if ($artifactBytes -gt $artifactLimitBytes) {
    $failures += "artifact size exceeded ${MaxArtifactMB}MB"
}

$report = [ordered]@{
    generated_at = (Get-Date).ToString('o')
    runtime_policy = 'opt-in visible runtime soak; raw frames stay outside the repository by default'
    executed = $true
    passed = (@($failures).Count -eq 0)
    failures = @($failures)
    tier = $Tier
    duration_sec = $DurationResolvedSec
    sample_interval_sec = $SampleIntervalSec
    route = $Route
    final_route_marker = if (@($routeResults).Count -gt 0) { @($routeResults)[-1].Name } else { $Route }
    stage = $Stage
    protected_stable_stage = $StableStage
    stable_stage_should_change = $false
    input_exe = $InputExeFull
    input_sha256 = $inputSha256
    candidate = $CandidateFull
    candidate_sha256 = $candidateSha256
    patch_stage_report = $patchStageReport
    workdir = $WorkDirFull
    output_directory = $outDir
    report_json = $ReportJsonFull
    report_markdown = $ReportMarkdownFull
    frame_sample_count = @($frameSamples).Count
    render_evidence_frame_count = @($renderEvidenceFrames).Count
    render_evidence_excluded_count = @($excludedFrames).Count
    render_evidence_excluded_frames = @($excludedFrames | ForEach-Object {
        [ordered]@{
            name = $_.Name
            capture_mode = $_.CaptureMode
            nonblack_percent = $_.NonblackPercent
            reasons = @($_.RenderEvidenceExcludedReasons)
        }
    })
    capture_mode_dominant = $dominantCaptureMode
    capture_mode_counts = $captureModeCounts
    capture_mode_changed = $captureModeChanged
    stop_signal_at = if ($null -ne $stopSignalAt) { $stopSignalAt.ToString('o') } else { $null }
    frame_hash_unique_count = @($uniqueFrameHashes).Count
    frame_progress_expected = $frameProgressExpected
    frame_stability_class = $frameStabilityClass
    nonblack_percent_min = Select-NumberMin -Values $nonblackValues
    nonblack_percent_max = Select-NumberMax -Values $nonblackValues
    mean_luma_min = Select-NumberMin -Values $lumaValues
    mean_luma_max = Select-NumberMax -Values $lumaValues
    unique_sample_colors_min = [int](Select-NumberMin -Values $uniqueColorValues)
    unique_sample_colors_max = [int](Select-NumberMax -Values $uniqueColorValues)
    input_max_abs_error = $inputMaxAbsError
    input_max_sample_abs_error = $inputMaxSampleAbsError
    max_input_drift_px = $MaxInputDriftPx
    window_mode = $windowedMode
    input_standing = $inputStanding
    window_health_policy = $plan.window_health_policy
    window_health_sample_count = @($windowHealthSamples).Count
    window_hang_observed = $windowHangObserved
    window_missing_while_alive_observed = $windowMissingWhileAliveObserved
    window_hidden_while_alive_observed = $windowHiddenWhileAliveObserved
    wrapper_error_dialog_observed = $wrapperErrorDialogObserved
    wrapper_error_dialog_text = $wrapperErrorDialogText
    window_health_first_failure = $windowHealthFirstFailure
    intro_skip = [ordered]@{
        click_mode = $IntroSkipClickMode
        click_repeat = $IntroSkipClicks
        stop_click_repeat_on_drift = $IntroSkipStopClickRepeatOnDrift
        space_pulses = $SkipPulses
        proof_class = 'intro_skip_harness_prep_not_manual_directinput_release_proof'
        menu_verified = $introMenuVerified
        menu_verify_nonblack_percent = $introMenuVerifyNonblack
        menu_verify_threshold_percent = $IntroMenuVerifyNonblackPercent
        rounds_used = $introRoundsUsed
    }
    map_route_reached = $mapRouteReached
    route_final_nonblack_percent = $routeFinalNonblack
    map_reached_nonblack_threshold_percent = $MapReachedNonblackPercent
    launch_attempt_count = @($launchAttemptRows).Count
    launch_attempts = @($launchAttemptRows)
    cursor_probe_required = $cursorProbeRequired
    cursor_probe_alive = $cursorProbeAlive
    cursor_probe_converged = $cursorProbeConverged
    cursor_probe_usable = $cursorProbeUsable
    cursor_probe_foreground_denied = $cursorProbeForegroundDenied
    process_sample_count = @($processSamples).Count
    working_set_growth_bytes = $workingSetGrowthBytes
    private_memory_growth_bytes = $privateMemoryGrowthBytes
    handle_growth = $handleGrowth
    max_working_set_growth_mb = $MaxWorkingSetGrowthMB
    max_private_memory_growth_mb = $MaxPrivateMemoryGrowthMB
    max_handle_growth = $MaxHandleGrowth
    working_set_growth_limit_bytes = $workingSetLimitBytes
    private_memory_growth_limit_bytes = $privateMemoryLimitBytes
    max_artifact_mb = $MaxArtifactMB
    artifact_limit_bytes = $artifactLimitBytes
    artifact_bytes = $artifactBytes
    process_exited_unexpectedly = $unexpectedExit
    exit_code = $exitCode
    clean_stop = $cleanStop
    keep_open = [bool]$KeepOpen
    input_proof_class = 'automated_visible_runtime_diagnostic_not_manual_directinput_release_proof'
    right_bottom_promotion_blocked = $true
    route_results = @($routeResults)
    process_samples = @($processSamples)
    frame_samples = @($frameSamples)
    capture_errors = @($captureErrors)
    window_health_samples = @($windowHealthSamples)
}

$reportDir = Split-Path -Parent $ReportJsonFull
if ($reportDir -and -not (Test-Path -LiteralPath $reportDir)) {
    New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
}
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $ReportJsonFull -Encoding ASCII
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $outDir 'report.json') -Encoding ASCII
Write-SoakMarkdown -Report ([pscustomobject]$report) -Path $ReportMarkdownFull
Write-SoakMarkdown -Report ([pscustomobject]$report) -Path (Join-Path $outDir 'report.md')

if ($Json) {
    $report | ConvertTo-Json -Depth 10
} else {
    [pscustomobject]$report | Format-List
}

if ($RequirePass -and -not $report.passed) {
    exit 1
}
