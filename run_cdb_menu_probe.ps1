param(
    [string]$Exe = 'C:\Clash\clash95_hddisplay_absinput.exe',
    [string]$Cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe',
    [string]$Probe = (Join-Path $PSScriptRoot 'clash95_hd_menu_state_probe.cdb'),
    [string]$Log = 'C:\Clash\hd-cdb-menu.log',
    [string]$WorkDir = 'C:\Clash',
    [int]$RunSeconds = 10,
    [int]$SkipPulses = 4,
    [int]$SkipIntervalMs = 500
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
