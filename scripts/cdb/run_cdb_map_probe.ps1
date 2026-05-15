param(
    [string]$Exe = 'C:\Clash\clash95_hd_mousedynorigin_boundguard_20260422.exe',
    [string]$WorkDir = 'C:\Clash',
    [string]$Cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe',
    [string]$Probe = (Join-Path (Join-Path $PSScriptRoot '..\..') 'probes/cdb/map/clash95_map_runtime_probe.cdb'),
    [string]$Log = (Join-Path (Join-Path $PSScriptRoot '..\..') 'captures\cdb-map-runtime-20260422.log'),
    [string]$Python = 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [string]$MouseJson = (Join-Path (Join-Path $PSScriptRoot '..\..') 'captures\map-runtime-mouse-path-20260422.json'),
    [string]$Frame = (Join-Path (Join-Path $PSScriptRoot '..\..') 'captures\map-runtime-final-frame-20260422.png'),
    [string]$Points = '300,218;320,166;400,226',
    [ValidateSet('setcursor', 'sendinput-absolute', 'sendinput-relative', 'sendinput-client-delta', 'auto', 'none')]
    [string]$MoveMode = 'setcursor',
    [ValidateSet('sendinput', 'postmessage', 'both')]
    [string]$ClickMode = 'sendinput',
    [int]$ClickHoldMs = 300,
    [int]$ClickRepeat = 2,
    [int]$ClickIntervalMs = 900,
    [int]$RunSeconds = 10,
    [int]$WindowTimeoutSec = 12,
    [int]$SkipPulses = 4,
    [int]$SkipIntervalMs = 500,
    [int]$MoveWindowX = 80,
    [int]$MoveWindowY = 80,
    [string[]]$StopLogPatterns = @(),
    [int]$StopAfterMatchSec = 2
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class ClashMapProbeWin32 {
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
    public static extern bool ClientToScreen(IntPtr hWnd, ref POINT point);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool BringWindowToTop(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

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

function Stop-ProbeProcesses {
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ProcessName -like 'clash95*' -or
            $_.ProcessName -eq 'cdb' -or
            ($_.Path -and $_.Path -like (Join-Path $WorkDir 'clash95*.exe')) -or
            ($_.Path -and $_.Path -eq $Cdb)
        } |
        Stop-Process -Force -ErrorAction SilentlyContinue
}

function Get-ClashWindowProcess {
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ProcessName -like 'clash95*' -and
            $_.MainWindowHandle -ne [IntPtr]::Zero
        } |
        Sort-Object StartTime -Descending |
        Select-Object -First 1
}

function Wait-ClashWindowProcess {
    param([int]$TimeoutSec)

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $game = Get-ClashWindowProcess
        if ($game) {
            return $game
        }
        Start-Sleep -Milliseconds 200
    }
    throw "Timed out waiting for a visible Clash95 window"
}

function Get-WindowHandleForProcess {
    param([System.Diagnostics.Process]$Process)

    $Process.Refresh()
    if ($Process.MainWindowHandle -ne [IntPtr]::Zero) {
        return $Process.MainWindowHandle
    }
    return [ClashMapProbeWin32]::FindVisibleWindowForProcess([uint32]$Process.Id)
}

function Save-ClientFrame {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Path
    )

    $captureScript = Join-Path (Join-Path $PSScriptRoot '..\capture') 'capture_clash_client_frame.ps1'
    if (-not (Test-Path -LiteralPath $captureScript)) {
        throw "Capture helper was not found: $captureScript"
    }
    $metaPath = "$Path.json"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $captureScript -TargetProcessId $Process.Id -Path $Path -Json $metaPath | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "capture_clash_client_frame.ps1 failed with exit code $LASTEXITCODE"
    }
    Get-Content -LiteralPath $metaPath -Raw | ConvertFrom-Json
}

function Get-MatchedLogPatterns {
    param(
        [string]$Path,
        [string[]]$Patterns
    )

    if (-not $Patterns -or $Patterns.Count -eq 0) {
        return @()
    }
    if (-not (Test-Path -LiteralPath $Path)) {
        return @()
    }

    $text = Get-Content -LiteralPath $Path -Raw -ErrorAction SilentlyContinue
    if ($null -eq $text) {
        return @()
    }

    @($Patterns | Where-Object { $text.Contains($_) })
}

foreach ($path in @($Exe, $WorkDir, $Cdb, $Probe, $Python)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required path was not found: $path"
    }
}

$mouseTool = Join-Path (Join-Path $PSScriptRoot '..\..') 'tools\mouse_path_probe.py'
if (-not (Test-Path -LiteralPath $mouseTool)) {
    throw "Mouse path probe was not found: $mouseTool"
}

foreach ($path in @($Log, $MouseJson, $Frame)) {
    $dir = Split-Path -Parent $path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force
    }
}

Stop-ProbeProcesses

$cdbCommand = '$$><' + $Probe
$cdbArgs = @('-hd', '-logo', $Log, '-c', $cdbCommand, $Exe)
$cdbProcess = Start-Process -FilePath $Cdb -ArgumentList $cdbArgs -WorkingDirectory $WorkDir -PassThru
$frameInfo = $null
$mouseExitCode = $null
$sentinelSeenAt = $null
$sentinelMatches = @()

try {
    $game = Wait-ClashWindowProcess -TimeoutSec $WindowTimeoutSec
    $mouseArgs = @(
        $mouseTool,
        '--pid', $game.Id,
        '--workdir', $WorkDir,
        '--move-window', $MoveWindowX, $MoveWindowY,
        '--settle-sec', '1',
        '--space-pulses', $SkipPulses,
        '--space-interval-ms', $SkipIntervalMs,
        '--interval-ms', $ClickIntervalMs,
        '--points', $Points,
        '--move-mode', $MoveMode,
        '--click',
        '--click-mode', $ClickMode,
        '--click-hold-ms', $ClickHoldMs,
        '--click-repeat', $ClickRepeat,
        '--json', $MouseJson
    )

    & $Python @mouseArgs | Out-Null
    $mouseExitCode = $LASTEXITCODE
    if ($mouseExitCode -ne 0 -and $mouseExitCode -ne 2) {
        throw "mouse_path_probe.py failed with exit code $LASTEXITCODE"
    }

    $deadline = (Get-Date).AddSeconds($RunSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($cdbProcess.HasExited) {
            break
        }
        if ($StopLogPatterns -and $StopLogPatterns.Count -gt 0) {
            $matches = @(Get-MatchedLogPatterns -Path $Log -Patterns $StopLogPatterns)
            if ($matches.Count -eq $StopLogPatterns.Count) {
                if (-not $sentinelSeenAt) {
                    $sentinelSeenAt = Get-Date
                    $sentinelMatches = $matches
                }
                elseif (((Get-Date) - $sentinelSeenAt).TotalSeconds -ge $StopAfterMatchSec) {
                    break
                }
            }
            else {
                $sentinelSeenAt = $null
                $sentinelMatches = @()
            }
        }
        Start-Sleep -Milliseconds 250
    }

    $game.Refresh()
    if (-not $game.HasExited) {
        $frameInfo = Save-ClientFrame -Process $game -Path $Frame
    }
}
finally {
    if (-not $cdbProcess.HasExited) {
        Stop-ProbeProcesses
    }
}

$result = [pscustomobject]@{
    Exe = $Exe
    Probe = $Probe
    Log = $Log
    MouseJson = $MouseJson
    Frame = if ($frameInfo) { $frameInfo.Path } else { $null }
    FrameHash = if ($frameInfo) { $frameInfo.Hash } else { $null }
    FrameWidth = if ($frameInfo) { $frameInfo.Width } else { $null }
    FrameHeight = if ($frameInfo) { $frameInfo.Height } else { $null }
    FrameCenterWindowMatchesTarget = if ($frameInfo) { $frameInfo.CenterWindowMatchesTarget } else { $null }
    FrameCenterWindowHwnd = if ($frameInfo) { $frameInfo.CenterWindowHwnd } else { $null }
    FrameCenterRootHwnd = if ($frameInfo) { $frameInfo.CenterRootHwnd } else { $null }
    ClickMode = $ClickMode
    MoveMode = $MoveMode
    MouseProbeExitCode = $mouseExitCode
    ClickHoldMs = $ClickHoldMs
    ClickRepeat = $ClickRepeat
    Points = $Points
    StopLogPatterns = @($StopLogPatterns)
    StopLogMatched = ($sentinelMatches.Count -eq $StopLogPatterns.Count -and $StopLogPatterns.Count -gt 0)
    StopLogMatches = @($sentinelMatches)
    StopAfterMatchSec = $StopAfterMatchSec
}

$result | Format-List
if (Test-Path -LiteralPath $Log) {
    Get-Content -LiteralPath $Log | Select-Object -Last 160
} else {
    Write-Warning "CDB log was not created: $Log"
}
