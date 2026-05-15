param(
    [Parameter(Mandatory = $true)]
    [int]$TargetProcessId,
    [Parameter(Mandatory = $true)]
    [string]$Path,
    [string]$Json,
    [int]$WindowTimeoutSec = 5
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class ClashClientCaptureWin32 {
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
    public static extern bool SetProcessDPIAware();

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
    public static extern IntPtr WindowFromPoint(POINT point);

    [DllImport("user32.dll")]
    public static extern IntPtr GetAncestor(IntPtr hWnd, uint gaFlags);

    [DllImport("user32.dll")]
    public static extern IntPtr GetDC(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern int ReleaseDC(IntPtr hWnd, IntPtr hDC);

    [DllImport("gdi32.dll")]
    public static extern bool BitBlt(IntPtr hdcDest, int nXDest, int nYDest, int nWidth, int nHeight, IntPtr hdcSrc, int nXSrc, int nYSrc, int dwRop);

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

[ClashClientCaptureWin32]::SetProcessDPIAware() | Out-Null

function Wait-ClashWindow {
    param(
        [int]$ProcessId,
        [int]$TimeoutSec
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $handle = [ClashClientCaptureWin32]::FindVisibleWindowForProcess([uint32]$ProcessId)
        if ($handle -ne [IntPtr]::Zero) {
            return $handle
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Timed out waiting for visible window for pid $ProcessId"
}

function Get-FrameSampleStats {
    param([string]$FramePath)

    $bitmap = [System.Drawing.Bitmap]::FromFile($FramePath)
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
                $samples++
                $lumaSum += $luma
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

function Get-WindowProcessId {
    param([IntPtr]$Handle)

    if ($Handle -eq [IntPtr]::Zero) {
        return 0
    }
    [uint32]$processId = 0
    [ClashClientCaptureWin32]::GetWindowThreadProcessId($Handle, [ref]$processId) | Out-Null
    [int]$processId
}

function Get-CaptureTargetGeometry {
    param([IntPtr]$Handle)

    $rect = New-Object ClashClientCaptureWin32+RECT
    if (-not [ClashClientCaptureWin32]::GetClientRect($Handle, [ref]$rect)) {
        throw "GetClientRect failed"
    }
    $origin = New-Object ClashClientCaptureWin32+POINT
    $origin.X = 0
    $origin.Y = 0
    if (-not [ClashClientCaptureWin32]::ClientToScreen($Handle, [ref]$origin)) {
        throw "ClientToScreen failed"
    }
    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top
    if ($width -le 0 -or $height -le 0) {
        throw "Invalid client size ${width}x${height}"
    }

    $center = New-Object ClashClientCaptureWin32+POINT
    $center.X = $origin.X + [int][math]::Floor($width / 2)
    $center.Y = $origin.Y + [int][math]::Floor($height / 2)
    $centerWindow = [ClashClientCaptureWin32]::WindowFromPoint($center)
    $centerRoot = [ClashClientCaptureWin32]::GetAncestor($centerWindow, 2)

    [pscustomobject]@{
        Handle = $Handle
        Origin = $origin
        Width = $width
        Height = $height
        CenterWindow = $centerWindow
        CenterRoot = $centerRoot
        CenterMatchesTarget = ($centerRoot -eq $Handle -or $centerWindow -eq $Handle)
    }
}

$handle = Wait-ClashWindow -ProcessId $TargetProcessId -TimeoutSec $WindowTimeoutSec
$hwndTopmost = [IntPtr]::new(-1)
$hwndNotTopmost = [IntPtr]::new(-2)
$swpNoMove = 0x0002
$swpNoSize = 0x0001
$swpShowWindow = 0x0040

[ClashClientCaptureWin32]::ShowWindow($handle, 5) | Out-Null
[ClashClientCaptureWin32]::SetWindowPos($handle, $hwndTopmost, 0, 0, 0, 0, $swpNoMove -bor $swpNoSize -bor $swpShowWindow) | Out-Null
[ClashClientCaptureWin32]::BringWindowToTop($handle) | Out-Null
[ClashClientCaptureWin32]::SetForegroundWindow($handle) | Out-Null
Start-Sleep -Milliseconds 250

$geometry = Get-CaptureTargetGeometry -Handle $handle
$centerWindow = $geometry.CenterWindow
$centerRoot = $geometry.CenterRoot
$centerMatchesTarget = $geometry.CenterMatchesTarget
$reacquiredSameProcessWindow = $false
$captureMode = 'screen'
if (-not $centerMatchesTarget) {
    $centerRootProcessId = Get-WindowProcessId -Handle $centerRoot
    $centerWindowProcessId = Get-WindowProcessId -Handle $centerWindow
    if ($centerRoot -ne [IntPtr]::Zero -and $centerRootProcessId -eq $TargetProcessId) {
        $handle = $centerRoot
        $reacquiredSameProcessWindow = $true
    } elseif ($centerWindow -ne [IntPtr]::Zero -and $centerWindowProcessId -eq $TargetProcessId) {
        $handle = $centerWindow
        $reacquiredSameProcessWindow = $true
    }

    if ($reacquiredSameProcessWindow) {
        [ClashClientCaptureWin32]::ShowWindow($handle, 5) | Out-Null
        [ClashClientCaptureWin32]::SetWindowPos($handle, $hwndTopmost, 0, 0, 0, 0, $swpNoMove -bor $swpNoSize -bor $swpShowWindow) | Out-Null
        [ClashClientCaptureWin32]::BringWindowToTop($handle) | Out-Null
        [ClashClientCaptureWin32]::SetForegroundWindow($handle) | Out-Null
        Start-Sleep -Milliseconds 250

        $geometry = Get-CaptureTargetGeometry -Handle $handle
        $centerWindow = $geometry.CenterWindow
        $centerRoot = $geometry.CenterRoot
        $centerMatchesTarget = $geometry.CenterMatchesTarget
    }

    if (-not $centerMatchesTarget) {
        $captureMode = 'windowdc-contaminated-fallback'
    }
}

$origin = $geometry.Origin
$width = $geometry.Width
$height = $geometry.Height

$dir = Split-Path -Parent $Path
if ($dir -and -not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

$bitmap = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
try {
    if ($captureMode -eq 'screen') {
        $graphics.CopyFromScreen($origin.X, $origin.Y, 0, 0, $bitmap.Size)
    } else {
        $srcDc = [ClashClientCaptureWin32]::GetDC($handle)
        if ($srcDc -eq [IntPtr]::Zero) {
            throw "GetDC failed for fallback capture"
        }
        $destDc = $graphics.GetHdc()
        try {
            $srccopy = 0x00CC0020
            if (-not [ClashClientCaptureWin32]::BitBlt($destDc, 0, 0, $width, $height, $srcDc, 0, 0, $srccopy)) {
                throw "BitBlt failed for fallback capture"
            }
        } finally {
            $graphics.ReleaseHdc($destDc)
            [ClashClientCaptureWin32]::ReleaseDC($handle, $srcDc) | Out-Null
        }
    }
    $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
} finally {
    $graphics.Dispose()
    $bitmap.Dispose()
    [ClashClientCaptureWin32]::SetWindowPos($handle, $hwndNotTopmost, 0, 0, 0, 0, $swpNoMove -bor $swpNoSize -bor $swpShowWindow) | Out-Null
}

$stats = Get-FrameSampleStats -FramePath $Path
$result = [pscustomobject]@{
    Path = $Path
    Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
    Width = $width
    Height = $height
    OriginX = $origin.X
    OriginY = $origin.Y
    CenterWindowMatchesTarget = $centerMatchesTarget
    ReacquiredSameProcessWindow = $reacquiredSameProcessWindow
    CaptureMode = $captureMode
    TargetHwnd = ("0x{0}" -f $handle.ToInt64().ToString('X'))
    CenterWindowHwnd = ("0x{0}" -f $centerWindow.ToInt64().ToString('X'))
    CenterRootHwnd = ("0x{0}" -f $centerRoot.ToInt64().ToString('X'))
    NonblackPercent = $stats.NonblackPercent
    MeanLuma = $stats.MeanLuma
    NonblackBounds = $stats.NonblackBounds
}

if ($Json) {
    $jsonDir = Split-Path -Parent $Json
    if ($jsonDir -and -not (Test-Path -LiteralPath $jsonDir)) {
        New-Item -ItemType Directory -Path $jsonDir -Force | Out-Null
    }
    $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Json -Encoding ASCII
}

$result | ConvertTo-Json -Depth 6
