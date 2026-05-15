param(
    [string]$ProcessName = 'clash95_hddisplay_absinput',
    [string]$Output = 'C:\Clash\clash-window.png',
    [int]$WaitSec = 2
)

$ErrorActionPreference = 'Stop'
Start-Sleep -Seconds $WaitSec

Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class Win32Capture {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);

    [DllImport("user32.dll")]
    public static extern bool GetClientRect(IntPtr hWnd, out RECT rect);

    [DllImport("user32.dll")]
    public static extern bool ClientToScreen(IntPtr hWnd, ref POINT point);

    [StructLayout(LayoutKind.Sequential)]
    public struct POINT {
        public int X;
        public int Y;
    }
}
'@

$process = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } |
    Select-Object -First 1

if (-not $process) {
    throw "No visible window found for process name: $ProcessName"
}

$client = New-Object Win32Capture+RECT
[Win32Capture]::GetClientRect($process.MainWindowHandle, [ref]$client) | Out-Null

$origin = New-Object Win32Capture+POINT
$origin.X = 0
$origin.Y = 0
[Win32Capture]::ClientToScreen($process.MainWindowHandle, [ref]$origin) | Out-Null

$width = $client.Right - $client.Left
$height = $client.Bottom - $client.Top
if ($width -le 0 -or $height -le 0) {
    throw "Invalid client size for process $($process.Id): ${width}x${height}"
}

$bitmap = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($origin.X, $origin.Y, 0, 0, $bitmap.Size)
$graphics.Dispose()

$dir = Split-Path -Parent $Output
if ($dir -and -not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir | Out-Null
}

$bitmap.Save($Output, [System.Drawing.Imaging.ImageFormat]::Png)
$bitmap.Dispose()

[pscustomobject]@{
    ProcessId = $process.Id
    ProcessName = $process.ProcessName
    ClientX = $origin.X
    ClientY = $origin.Y
    Width = $width
    Height = $height
    Output = $Output
}
