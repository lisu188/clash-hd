param(
    [string]$Exe = 'C:\Clash\clash95_hddisplay_absinput.exe',
    [string]$Cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe',
    [string]$Probe = (Join-Path $PSScriptRoot 'probes/cdb/menu/clash95_hd_menu_state_probe.cdb'),
    [string]$Log = 'C:\Clash\hd-cdb-menu.log',
    [string]$WorkDir = 'C:\Clash',
    [int]$RunSeconds = 10,
    [int]$SkipPulses = 4,
    [int]$SkipIntervalMs = 500,
    [switch]$MouseSweep,
    [switch]$SweepClick,
    [int]$SweepIntervalMs = 400,
    [int]$WindowX = 80,
    [int]$WindowY = 80,
    [switch]$NoMoveWindow
)

$ErrorActionPreference = 'Stop'

Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class ClashProbeWin32 {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool BringWindowToTop(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

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

    [DllImport("user32.dll")]
    public static extern bool GetClientRect(IntPtr hWnd, out RECT rect);

    [DllImport("user32.dll")]
    public static extern bool ClientToScreen(IntPtr hWnd, ref POINT point);

    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X, int Y);

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);

    [DllImport("user32.dll")]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);

    [StructLayout(LayoutKind.Sequential)]
    public struct INPUT {
        public int type;
        public MOUSEINPUT mi;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct MOUSEINPUT {
        public int dx;
        public int dy;
        public uint mouseData;
        public uint dwFlags;
        public uint time;
        public IntPtr dwExtraInfo;
    }

    [DllImport("user32.dll", SetLastError=true)]
    public static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);

    [DllImport("user32.dll")]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
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
        Select-Object -First 1
}

function Move-MouseSweep {
    param([System.Diagnostics.Process]$Game)

    if (-not $Game -or $Game.MainWindowHandle -eq [IntPtr]::Zero) {
        return
    }

    [ClashProbeWin32]::ShowWindow($Game.MainWindowHandle, 5) | Out-Null
    if (-not $NoMoveWindow) {
        $windowRect = New-Object ClashProbeWin32+RECT
        [ClashProbeWin32]::GetWindowRect($Game.MainWindowHandle, [ref]$windowRect) | Out-Null
        $windowWidth = $windowRect.Right - $windowRect.Left
        $windowHeight = $windowRect.Bottom - $windowRect.Top
        if ($windowWidth -gt 0 -and $windowHeight -gt 0) {
            [ClashProbeWin32]::MoveWindow(
                $Game.MainWindowHandle,
                $WindowX,
                $WindowY,
                $windowWidth,
                $windowHeight,
                $true
            ) | Out-Null
            Start-Sleep -Milliseconds 150
        }
    }
    [ClashProbeWin32]::BringWindowToTop($Game.MainWindowHandle) | Out-Null
    [ClashProbeWin32]::SetForegroundWindow($Game.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds 200

    $rect = New-Object ClashProbeWin32+RECT
    [ClashProbeWin32]::GetClientRect($Game.MainWindowHandle, [ref]$rect) | Out-Null
    $origin = New-Object ClashProbeWin32+POINT
    $origin.X = 0
    $origin.Y = 0
    [ClashProbeWin32]::ClientToScreen($Game.MainWindowHandle, [ref]$origin) | Out-Null

    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top
    if ($width -le 0 -or $height -le 0) {
        return
    }

    $points = @(
        @{ X = [int]($width / 2); Y = [int]($height / 2) },
        @{ X = 120; Y = 120 },
        @{ X = 320; Y = 285 },
        @{ X = 480; Y = 260 },
        @{ X = [int]($width - 80); Y = [int]($height - 80) },
        @{ X = [int]($width / 2); Y = [int]($height / 2) }
    )

    foreach ($point in $points) {
        $screenX = $origin.X + $point.X
        $screenY = $origin.Y + $point.Y
        Write-Host "Sweep client=($($point.X),$($point.Y)) screen=($screenX,$screenY)"
        [ClashProbeWin32]::SetCursorPos($screenX, $screenY) | Out-Null
        if ($SweepClick) {
            Start-Sleep -Milliseconds 120
            $down = New-Object ClashProbeWin32+INPUT
            $down.type = 0
            $down.mi.dwFlags = 0x0002

            $up = New-Object ClashProbeWin32+INPUT
            $up.type = 0
            $up.mi.dwFlags = 0x0004

            $inputs = [ClashProbeWin32+INPUT[]]@($down, $up)
            $size = [Runtime.InteropServices.Marshal]::SizeOf([type][ClashProbeWin32+INPUT])
            [ClashProbeWin32]::SendInput(2, $inputs, $size) | Out-Null
        }
        Start-Sleep -Milliseconds $SweepIntervalMs
    }
}

if (-not (Test-Path -LiteralPath $Cdb)) {
    throw "cdb.exe was not found at: $Cdb"
}
if (-not (Test-Path -LiteralPath $Exe)) {
    throw "Target executable was not found: $Exe"
}
if (-not (Test-Path -LiteralPath $Probe)) {
    throw "Probe script was not found: $Probe"
}

Stop-ProbeProcesses

if (Test-Path -LiteralPath $Log) {
    Remove-Item -LiteralPath $Log -Force
}

$argsList = @('-hd', '-logo', $Log, '-cf', $Probe, $Exe)
$cdbProcess = Start-Process -FilePath $Cdb -ArgumentList $argsList -WorkingDirectory $WorkDir -PassThru

try {
    for ($i = 0; $i -lt $SkipPulses; $i++) {
        Start-Sleep -Milliseconds $SkipIntervalMs
        $game = Get-ClashWindowProcess
        if ($game) {
            [ClashProbeWin32]::ShowWindow($game.MainWindowHandle, 5) | Out-Null
            [ClashProbeWin32]::BringWindowToTop($game.MainWindowHandle) | Out-Null
            [ClashProbeWin32]::SetForegroundWindow($game.MainWindowHandle) | Out-Null
            [ClashProbeWin32]::keybd_event(0x20, 0, 0, [UIntPtr]::Zero)
            Start-Sleep -Milliseconds 60
            [ClashProbeWin32]::keybd_event(0x20, 0, 2, [UIntPtr]::Zero)
        }
    }

    if ($MouseSweep) {
        $game = Get-ClashWindowProcess
        Move-MouseSweep -Game $game
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

if (Test-Path -LiteralPath $Log) {
    Get-Content -LiteralPath $Log | Select-Object -Last 120
} else {
    Write-Warning "CDB log was not created: $Log"
}
