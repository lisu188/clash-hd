param(
    [string]$Exe = 'C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapright_vswitch_20260423.exe',
    [string]$WorkDir = 'C:\Clash',
    [string]$Cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe',
    [string]$Probe = (Join-Path $PSScriptRoot 'probes/cdb/render/clash95_viewport_bounds_probe.cdb'),
    [string]$Log = (Join-Path $PSScriptRoot 'captures\cdb-viewport-bounds-20260423.log'),
    [int]$RunSeconds = 10,
    [int]$WindowTimeoutSec = 8,
    [int]$SpacePulses = 4,
    [int]$SpaceIntervalMs = 500
)

$ErrorActionPreference = 'Stop'

Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class ClashViewportBoundsWin32 {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool BringWindowToTop(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);

    public static IntPtr FindVisibleWindowForProcess(uint processId) {
        IntPtr found = IntPtr.Zero;
        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {
            uint windowProcessId;
            GetWindowThreadProcessId(hWnd, out windowProcessId);
            if (windowProcessId == processId && IsWindowVisible(hWnd)) {
                found = hWnd;
                return false;
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

function Wait-ClashWindow {
    param([int]$TimeoutSec)

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $game = Get-ClashWindowProcess
        if ($game) {
            $handle = $game.MainWindowHandle
            if ($handle -eq [IntPtr]::Zero) {
                $handle = [ClashViewportBoundsWin32]::FindVisibleWindowForProcess([uint32]$game.Id)
            }
            if ($handle -ne [IntPtr]::Zero) {
                return [pscustomobject]@{ Process = $game; Hwnd = $handle }
            }
        }
        Start-Sleep -Milliseconds 200
    }
    return $null
}

function Send-SpacePulses {
    param(
        [int]$Count,
        [int]$IntervalMs
    )

    for ($i = 0; $i -lt $Count; $i++) {
        [ClashViewportBoundsWin32]::keybd_event(0x20, 0, 0, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds 50
        [ClashViewportBoundsWin32]::keybd_event(0x20, 0, 2, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds $IntervalMs
    }
}

foreach ($path in @($Exe, $WorkDir, $Cdb, $Probe)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required path was not found: $path"
    }
}

$logDir = Split-Path -Parent $Log
if ($logDir -and -not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
if (Test-Path -LiteralPath $Log) {
    Remove-Item -LiteralPath $Log -Force
}

Stop-ProbeProcesses

$cdbArgs = @('-hd', '-logo', $Log, '-cf', $Probe, $Exe)
$cdbProcess = Start-Process -FilePath $Cdb -ArgumentList $cdbArgs -WorkingDirectory $WorkDir -PassThru
$windowInfo = $null

try {
    $windowInfo = Wait-ClashWindow -TimeoutSec $WindowTimeoutSec
    if ($windowInfo -and $SpacePulses -gt 0) {
        [ClashViewportBoundsWin32]::BringWindowToTop($windowInfo.Hwnd) | Out-Null
        [ClashViewportBoundsWin32]::SetForegroundWindow($windowInfo.Hwnd) | Out-Null
        Start-Sleep -Milliseconds 300
        Send-SpacePulses -Count $SpacePulses -IntervalMs $SpaceIntervalMs
    }

    $deadline = (Get-Date).AddSeconds($RunSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($cdbProcess.HasExited) {
            break
        }
        Start-Sleep -Milliseconds 250
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
    RunSeconds = $RunSeconds
    SpacePulses = $SpacePulses
    WindowPid = if ($windowInfo) { $windowInfo.Process.Id } else { $null }
    WindowHwnd = if ($windowInfo) { ('0x{0:X}' -f $windowInfo.Hwnd.ToInt64()) } else { $null }
}

$result | Format-List
if (Test-Path -LiteralPath $Log) {
    Get-Content -LiteralPath $Log | Select-Object -Last 160
} else {
    Write-Warning "CDB log was not created: $Log"
}
