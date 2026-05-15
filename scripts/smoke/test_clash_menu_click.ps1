param(
    [string[]]$Exe = @('.\clash95_hddisplay_absinput.exe'),
    [string]$WorkDir = 'C:\Clash',
    [string[]]$Click = @('native-exit', 'centered-exit'),
    [string]$OutRoot = (Join-Path (Join-Path $PSScriptRoot '..\..') 'captures'),
    [int]$MenuWaitSec = 6,
    [int]$AfterClickWaitMs = 1500,
    [int]$DiffStep = 8,
    [int]$SurfaceWidth = 800,
    [int]$SurfaceHeight = 600,
    [int]$PreClickStableFrames = 2,
    [int]$PreClickStableIntervalMs = 500,
    [double]$PreClickStableMaxChangedPercent = 0.2,
    [int]$PreClickStableTimeoutSec = 8,
    [double]$PreClickMinNonblackPercent = 55.0,
    [double]$PreClickMinTargetBrightPercent = 5.0,
    [double]$PreClickMinTargetMeanLuma = 40.0,
    [int]$PreClickTargetRadius = 18,
    [int]$SkipIntroClicks = 4,
    [int]$SkipIntroIntervalMs = 500,
    [int]$SkipIntroX = 400,
    [int]$SkipIntroY = 300,
    [string[]]$SkipIntroKeys = @('Space'),
    [ValidateSet('SendInput', 'PostMessage', 'Both')]
    [string]$SkipIntroClickMode = 'Both',
    [switch]$CaptureFullClient,
    [int]$WindowX = 80,
    [int]$WindowY = 80,
    [switch]$NoMoveWindow,
    [ValidateSet('SendInput', 'PostMessage', 'Both')]
    [string]$ClickMode = 'SendInput',
    [ValidateRange(0, 5000)]
    [int]$ClickHoldMs = 0,
    [ValidateRange(1, 20)]
    [int]$ClickRepeat = 1,
    [switch]$NoInstallToWorkDir,
    [switch]$KeepExisting,
    [switch]$KeepOpenOnFailure
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class ClashWin32 {
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

    [DllImport("user32.dll")]
    public static extern bool GetClientRect(IntPtr hWnd, out RECT rect);

    [DllImport("user32.dll")]
    public static extern bool ClientToScreen(IntPtr hWnd, ref POINT point);

    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X, int Y);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool BringWindowToTop(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);

    [DllImport("user32.dll")]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);

    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();

    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [DllImport("user32.dll")]
    public static extern bool IsWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", SetLastError=true)]
    public static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);

    [DllImport("user32.dll")]
    public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);

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

$clickPoints = @{
    'native-load'       = [pscustomobject]@{ X = 220; Y = 158; Kind = 'menu'; Description = 'old 640x480 Load button center' }
    'native-campaign'   = [pscustomobject]@{ X = 215; Y = 190; Kind = 'menu'; Description = 'old 640x480 Campaign button center' }
    'native-exit'       = [pscustomobject]@{ X = 240; Y = 225; Kind = 'exit'; Description = 'old 640x480 Exit button center' }
    'centered-load'     = [pscustomobject]@{ X = 300; Y = 218; Kind = 'menu'; Description = 'native Load plus 80,60 center offset' }
    'centered-campaign' = [pscustomobject]@{ X = 295; Y = 250; Kind = 'menu'; Description = 'native Campaign plus 80,60 center offset' }
    'centered-exit'     = [pscustomobject]@{ X = 320; Y = 285; Kind = 'exit'; Description = 'native Exit plus 80,60 center offset' }
    'shifted-load'      = [pscustomobject]@{ X = 445; Y = 255; Kind = 'menu'; Description = 'observed shifted Load button center in current 800x600 menu' }
    'shifted-campaign'  = [pscustomobject]@{ X = 440; Y = 295; Kind = 'menu'; Description = 'observed shifted Campaign button center in current 800x600 menu' }
    'shifted-exit'      = [pscustomobject]@{ X = 430; Y = 335; Kind = 'exit'; Description = 'observed shifted Exit button center in current 800x600 menu' }
}

$Exe = @($Exe | ForEach-Object { $_ -split ',' } | Where-Object { $_ })
$Click = @($Click | ForEach-Object { $_ -split ',' } | Where-Object { $_ })
$SkipIntroKeys = @($SkipIntroKeys | ForEach-Object { $_ -split ',' } | Where-Object { $_ })

function Stop-ClashProcesses {
    param([string]$Root)

    Get-Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ProcessName -like 'clash95*' -or
            $_.ProcessName -eq 'cdb' -or
            ($_.Path -and $_.Path -like (Join-Path $Root 'clash95*.exe')) -or
            ($_.Path -and $_.Path -eq 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe')
        } |
        Stop-Process -Force -ErrorAction SilentlyContinue
}

function Resolve-ExeForRun {
    param(
        [string]$ExePath,
        [string]$Root,
        [bool]$SkipInstall
    )

    $resolved = Resolve-Path -LiteralPath $ExePath -ErrorAction Stop
    $source = Get-Item -LiteralPath $resolved.Path
    if (-not $source.Exists) {
        throw "Executable was not found: $ExePath"
    }

    $rootFull = (Resolve-Path -LiteralPath $Root -ErrorAction Stop).Path.TrimEnd('\')
    $sourceDir = $source.DirectoryName.TrimEnd('\')
    if ($SkipInstall -or ($sourceDir -ieq $rootFull)) {
        return $source.FullName
    }

    if ($source.Name -ieq 'clash95.exe') {
        throw "Refusing to overwrite C:\Clash\clash95.exe with another clash95.exe. Use the original in C:\Clash directly."
    }

    $dest = Join-Path $rootFull $source.Name
    Copy-Item -LiteralPath $source.FullName -Destination $dest -Force
    return $dest
}

function Wait-ForMainWindow {
    param(
        [System.Diagnostics.Process]$Process,
        [int]$TimeoutSec
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $handle = Get-GameWindowHandle -Process $Process
        if ($null -ne $handle -and $handle -ne [IntPtr]::Zero) {
            return $handle
        }
        Start-Sleep -Milliseconds 200
    }

    throw "Timed out waiting for main window for process $($Process.Id)"
}

function Get-GameWindowHandle {
    param(
        [System.Diagnostics.Process]$Process,
        [switch]$RequireVisible
    )

    if ($Process.HasExited) {
        throw "Process exited before a visible game window was available: $($Process.Id)"
    }

    $Process.Refresh()
    $handle = $Process.MainWindowHandle
    if ($null -ne $handle -and $handle -ne [IntPtr]::Zero -and [ClashWin32]::IsWindow($handle)) {
        return $handle
    }

    $handle = [ClashWin32]::FindVisibleWindowForProcess([uint32]$Process.Id)
    if ($null -ne $handle -and $handle -ne [IntPtr]::Zero -and [ClashWin32]::IsWindow($handle)) {
        return $handle
    }

    if ($RequireVisible) {
        throw "Process has no visible game window handle: $($Process.Id)"
    }
    return [IntPtr]::Zero
}

function Get-ClientInfo {
    param([System.Diagnostics.Process]$Process)

    $handle = Get-GameWindowHandle -Process $Process -RequireVisible

    $rect = New-Object ClashWin32+RECT
    if (-not [ClashWin32]::GetClientRect($handle, [ref]$rect)) {
        throw "GetClientRect failed for process $($Process.Id), hwnd 0x$($handle.ToInt64().ToString('X'))"
    }

    $origin = New-Object ClashWin32+POINT
    $origin.X = 0
    $origin.Y = 0
    if (-not [ClashWin32]::ClientToScreen($handle, [ref]$origin)) {
        throw "ClientToScreen failed for process $($Process.Id), hwnd 0x$($handle.ToInt64().ToString('X'))"
    }

    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top
    if ($width -le 0 -or $height -le 0) {
        throw "Invalid client size for process $($Process.Id): ${width}x${height}"
    }

    $scale = 1
    $renderX = $origin.X
    $renderY = $origin.Y
    $renderWidth = $width
    $renderHeight = $height

    if ($SurfaceWidth -gt 0 -and $SurfaceHeight -gt 0) {
        $scale = [int][math]::Floor([math]::Min($width / [double]$SurfaceWidth, $height / [double]$SurfaceHeight))
        if ($scale -lt 1) {
            $scale = 1
        }
        $renderWidth = [int]($SurfaceWidth * $scale)
        $renderHeight = [int]($SurfaceHeight * $scale)
        $renderX = [int]($origin.X + [math]::Floor(($width - $renderWidth) / 2))
        $renderY = [int]($origin.Y + [math]::Floor(($height - $renderHeight) / 2))
    }

    [pscustomobject]@{
        Handle = $handle
        ClientX = $origin.X
        ClientY = $origin.Y
        Width = $width
        Height = $height
        RenderX = $renderX
        RenderY = $renderY
        RenderWidth = $renderWidth
        RenderHeight = $renderHeight
        RenderScale = $scale
    }
}

function Focus-GameWindow {
    param([System.Diagnostics.Process]$Process)

    $handle = Get-GameWindowHandle -Process $Process -RequireVisible

    [ClashWin32]::ShowWindow($handle, 5) | Out-Null
    if (-not $NoMoveWindow) {
        $rect = New-Object ClashWin32+RECT
        [ClashWin32]::GetWindowRect($handle, [ref]$rect) | Out-Null
        $windowWidth = $rect.Right - $rect.Left
        $windowHeight = $rect.Bottom - $rect.Top
        if ($windowWidth -gt 0 -and $windowHeight -gt 0) {
            [ClashWin32]::MoveWindow(
                $handle,
                $WindowX,
                $WindowY,
                $windowWidth,
                $windowHeight,
                $true
            ) | Out-Null
            Start-Sleep -Milliseconds 150
        }
    }
    [ClashWin32]::BringWindowToTop($handle) | Out-Null
    [ClashWin32]::SetForegroundWindow($handle) | Out-Null
    Start-Sleep -Milliseconds 250
}

function Save-ClientFrame {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Path
    )

    Focus-GameWindow -Process $Process
    $info = Get-ClientInfo -Process $Process

    $sourceX = if ($CaptureFullClient) { $info.ClientX } else { $info.RenderX }
    $sourceY = if ($CaptureFullClient) { $info.ClientY } else { $info.RenderY }
    if ($CaptureFullClient) {
        $captureWidth = [int]$info.Width
        $captureHeight = [int]$info.Height
    } else {
        $captureWidth = [int]$info.RenderWidth
        $captureHeight = [int]$info.RenderHeight
    }

    $bitmap = New-Object System.Drawing.Bitmap $captureWidth, $captureHeight
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen($sourceX, $sourceY, 0, 0, $bitmap.Size)
        $dir = Split-Path -Parent $Path
        if ($dir -and -not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Path $dir | Out-Null
        }
        $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }

    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
    [pscustomobject]@{
        Path = $Path
        Hash = $hash
        ClientX = $info.ClientX
        ClientY = $info.ClientY
        ClientWidth = $info.Width
        ClientHeight = $info.Height
        RenderX = $info.RenderX
        RenderY = $info.RenderY
        RenderWidth = $info.RenderWidth
        RenderHeight = $info.RenderHeight
        RenderScale = $info.RenderScale
        Width = $captureWidth
        Height = $captureHeight
    }
}

function Copy-CaptureAsBefore {
    param(
        [object]$Capture,
        [string]$CaseDir
    )

    $beforePath = Join-Path $CaseDir 'before.png'
    Copy-Item -LiteralPath $Capture.Path -Destination $beforePath -Force
    [pscustomobject]@{
        Path = $beforePath
        Hash = $Capture.Hash
        ClientX = $Capture.ClientX
        ClientY = $Capture.ClientY
        ClientWidth = $Capture.ClientWidth
        ClientHeight = $Capture.ClientHeight
        RenderX = $Capture.RenderX
        RenderY = $Capture.RenderY
        RenderWidth = $Capture.RenderWidth
        RenderHeight = $Capture.RenderHeight
        RenderScale = $Capture.RenderScale
        Width = $Capture.Width
        Height = $Capture.Height
    }
}

function Compare-PngFrames {
    param(
        [string]$Before,
        [string]$After,
        [int]$Step
    )

    $bmpA = [System.Drawing.Bitmap]::FromFile($Before)
    $bmpB = [System.Drawing.Bitmap]::FromFile($After)
    try {
        if ($bmpA.Width -ne $bmpB.Width -or $bmpA.Height -ne $bmpB.Height) {
            return [pscustomobject]@{
                Samples = 0
                ChangedSamples = 0
                ChangedPercent = 100.0
                Note = "dimension change $($bmpA.Width)x$($bmpA.Height) -> $($bmpB.Width)x$($bmpB.Height)"
            }
        }

        $samples = 0
        $changed = 0
        for ($y = 0; $y -lt $bmpA.Height; $y += $Step) {
            for ($x = 0; $x -lt $bmpA.Width; $x += $Step) {
                $samples++
                if ($bmpA.GetPixel($x, $y).ToArgb() -ne $bmpB.GetPixel($x, $y).ToArgb()) {
                    $changed++
                }
            }
        }

        [pscustomobject]@{
            Samples = $samples
            ChangedSamples = $changed
            ChangedPercent = if ($samples) { [math]::Round(($changed * 100.0) / $samples, 3) } else { 0.0 }
            Note = $null
        }
    } finally {
        $bmpA.Dispose()
        $bmpB.Dispose()
    }
}

function Get-Luma {
    param([System.Drawing.Color]$Color)

    return (0.2126 * $Color.R) + (0.7152 * $Color.G) + (0.0722 * $Color.B)
}

function Measure-PreClickReadiness {
    param(
        [string]$FramePath,
        [int]$ClickX,
        [int]$ClickY
    )

    $bitmap = [System.Drawing.Bitmap]::FromFile($FramePath)
    try {
        $totalPixels = $bitmap.Width * $bitmap.Height
        $nonblackPixels = 0
        for ($y = 0; $y -lt $bitmap.Height; $y++) {
            for ($x = 0; $x -lt $bitmap.Width; $x++) {
                $pixel = $bitmap.GetPixel($x, $y)
                if ([math]::Max($pixel.R, [math]::Max($pixel.G, $pixel.B)) -gt 12) {
                    $nonblackPixels++
                }
            }
        }

        $x0 = [math]::Max(0, $ClickX - $PreClickTargetRadius)
        $x1 = [math]::Min($bitmap.Width - 1, $ClickX + $PreClickTargetRadius)
        $y0 = [math]::Max(0, $ClickY - $PreClickTargetRadius)
        $y1 = [math]::Min($bitmap.Height - 1, $ClickY + $PreClickTargetRadius)
        $targetPixels = 0
        $targetBrightPixels = 0
        $targetLumaSum = 0.0
        for ($y = $y0; $y -le $y1; $y++) {
            for ($x = $x0; $x -le $x1; $x++) {
                $pixel = $bitmap.GetPixel($x, $y)
                $luma = Get-Luma -Color $pixel
                $targetPixels++
                $targetLumaSum += $luma
                if ($luma -ge 96.0) {
                    $targetBrightPixels++
                }
            }
        }

        $nonblackPercent = if ($totalPixels) { [math]::Round(($nonblackPixels * 100.0) / $totalPixels, 3) } else { 0.0 }
        $targetBrightPercent = if ($targetPixels) { [math]::Round(($targetBrightPixels * 100.0) / $targetPixels, 3) } else { 0.0 }
        $targetMeanLuma = if ($targetPixels) { [math]::Round($targetLumaSum / $targetPixels, 3) } else { 0.0 }
        $ready = (
            $nonblackPercent -ge $PreClickMinNonblackPercent -and
            (
                $targetBrightPercent -ge $PreClickMinTargetBrightPercent -or
                $targetMeanLuma -ge $PreClickMinTargetMeanLuma
            )
        )
        $note = if ($ready) {
            $null
        } else {
            "nonblack ${nonblackPercent}% targetBright ${targetBrightPercent}% targetMeanLuma $targetMeanLuma"
        }

        [pscustomobject]@{
            Ready = $ready
            NonblackPercent = $nonblackPercent
            TargetBrightPercent = $targetBrightPercent
            TargetMeanLuma = $targetMeanLuma
            Note = $note
        }
    } finally {
        $bitmap.Dispose()
    }
}

function Wait-ForStableFrame {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$CaseDir
    )

    if ($PreClickStableFrames -le 0) {
        $capture = Save-ClientFrame -Process $Process -Path (Join-Path $CaseDir 'before.png')
        return [pscustomobject]@{
            Before = $capture
            Stable = $true
            Samples = 0
            Attempts = 1
            LastChangedPercent = 0.0
            Note = 'stability gate disabled'
        }
    }

    $stableSamples = 0
    $attempt = 0
    $previous = $null
    $lastChanged = $null
    $deadline = (Get-Date).AddSeconds($PreClickStableTimeoutSec)

    while ((Get-Date) -lt $deadline) {
        $path = Join-Path $CaseDir ("ready-{0:D2}.png" -f $attempt)
        $current = Save-ClientFrame -Process $Process -Path $path
        if ($previous -ne $null) {
            $comparison = Compare-PngFrames -Before $previous.Path -After $current.Path -Step $DiffStep
            $lastChanged = $comparison.ChangedPercent
            if ($comparison.ChangedPercent -le $PreClickStableMaxChangedPercent) {
                $stableSamples++
            } else {
                $stableSamples = 0
            }

            if ($stableSamples -ge $PreClickStableFrames) {
                return [pscustomobject]@{
                    Before = Copy-CaptureAsBefore -Capture $current -CaseDir $CaseDir
                    Stable = $true
                    Samples = $stableSamples
                    Attempts = $attempt + 1
                    LastChangedPercent = $lastChanged
                    Note = $comparison.Note
                }
            }
        }

        $previous = $current
        $attempt++
        Start-Sleep -Milliseconds $PreClickStableIntervalMs
    }

    if ($previous -ne $null) {
        return [pscustomobject]@{
            Before = Copy-CaptureAsBefore -Capture $previous -CaseDir $CaseDir
            Stable = $false
            Samples = $stableSamples
            Attempts = $attempt
            LastChangedPercent = $lastChanged
            Note = "timed out waiting for $PreClickStableFrames stable frame comparison(s)"
        }
    }

    throw "Unable to capture a pre-click frame for process $($Process.Id)"
}

function Invoke-ClientClick {
    param(
        [System.Diagnostics.Process]$Process,
        [int]$X,
        [int]$Y,
        [string]$Mode,
        [int]$HoldMs = 0,
        [int]$Repeat = 1
    )

    Focus-GameWindow -Process $Process
    $info = Get-ClientInfo -Process $Process

    $screenX = [int]($info.RenderX + [math]::Floor(($X + 0.5) * $info.RenderScale))
    $screenY = [int]($info.RenderY + [math]::Floor(($Y + 0.5) * $info.RenderScale))
    [ClashWin32]::SetCursorPos($screenX, $screenY) | Out-Null
    Start-Sleep -Milliseconds 150

    for ($i = 0; $i -lt $Repeat; $i++) {
        if ($Mode -eq 'SendInput' -or $Mode -eq 'Both') {
            $down = New-Object ClashWin32+INPUT
            $down.type = 0
            $down.mi.dwFlags = 0x0002

            $up = New-Object ClashWin32+INPUT
            $up.type = 0
            $up.mi.dwFlags = 0x0004

            $size = [Runtime.InteropServices.Marshal]::SizeOf([type][ClashWin32+INPUT])
            [ClashWin32]::SendInput(1, [ClashWin32+INPUT[]]@($down), $size) | Out-Null
            if ($HoldMs -gt 0) {
                Start-Sleep -Milliseconds $HoldMs
            }
            [ClashWin32]::SendInput(1, [ClashWin32+INPUT[]]@($up), $size) | Out-Null
        }

        if ($Mode -eq 'PostMessage' -or $Mode -eq 'Both') {
            $lParam = [IntPtr](($Y -shl 16) -bor ($X -band 0xffff))
            [ClashWin32]::PostMessage($info.Handle, 0x0201, [IntPtr]1, $lParam) | Out-Null
            Start-Sleep -Milliseconds ([Math]::Max(50, $HoldMs))
            [ClashWin32]::PostMessage($info.Handle, 0x0202, [IntPtr]0, $lParam) | Out-Null
        }

        if ($i -lt ($Repeat - 1)) {
            Start-Sleep -Milliseconds 75
        }
    }

    [pscustomobject]@{
        ClientX = $X
        ClientY = $Y
        ScreenX = $screenX
        ScreenY = $screenY
        HoldMs = $HoldMs
        Repeat = $Repeat
    }
}

function Send-SkipKey {
    param([string]$Key)

    $vkByName = @{
        Escape = 0x1B
        Esc = 0x1B
        Space = 0x20
        Enter = 0x0D
        Return = 0x0D
    }
    if (-not $vkByName.ContainsKey($Key)) {
        throw "Unknown skip key '$Key'. Known keys: $($vkByName.Keys -join ', ')"
    }

    $vk = [byte]$vkByName[$Key]
    [ClashWin32]::keybd_event($vk, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 50
    [ClashWin32]::keybd_event($vk, 0, 0x0002, [UIntPtr]::Zero)
}

if (-not (Test-Path -LiteralPath $WorkDir)) {
    throw "Working directory was not found: $WorkDir"
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$outDir = Join-Path $OutRoot "clicktest-$stamp"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

$results = New-Object System.Collections.Generic.List[object]

foreach ($exeArg in $Exe) {
    $runExe = Resolve-ExeForRun -ExePath $exeArg -Root $WorkDir -SkipInstall:$NoInstallToWorkDir.IsPresent
    $exeStem = [IO.Path]::GetFileNameWithoutExtension($runExe)

    foreach ($clickName in $Click) {
        if (-not $clickPoints.ContainsKey($clickName)) {
            throw "Unknown click '$clickName'. Known clicks: $($clickPoints.Keys -join ', ')"
        }
        $point = $clickPoints[$clickName]
        $caseName = "$exeStem-$clickName"
        $caseDir = Join-Path $outDir $caseName
        New-Item -ItemType Directory -Path $caseDir -Force | Out-Null

        if (-not $KeepExisting) {
            Stop-ClashProcesses -Root $WorkDir
            Start-Sleep -Milliseconds 300
        }

        $process = Start-Process -FilePath $runExe -WorkingDirectory $WorkDir -PassThru
        $before = $null
        $after = $null
        $diff = $null
        $clickInfo = $null
        $errorText = $null
        $readiness = $null
        $preClickReady = $null
        $clickAttempted = $false
        $passed = $false
        $exitedAfterWait = $false

        try {
            Wait-ForMainWindow -Process $process -TimeoutSec 10 | Out-Null
            Start-Sleep -Milliseconds 800
            for ($i = 0; $i -lt $SkipIntroClicks; $i++) {
                Invoke-ClientClick -Process $process -X $SkipIntroX -Y $SkipIntroY -Mode $SkipIntroClickMode | Out-Null
                foreach ($key in $SkipIntroKeys) {
                    Send-SkipKey -Key $key
                    Start-Sleep -Milliseconds 75
                }
                Start-Sleep -Milliseconds $SkipIntroIntervalMs
            }
            Start-Sleep -Seconds $MenuWaitSec
            $readiness = Wait-ForStableFrame -Process $process -CaseDir $caseDir
            $before = $readiness.Before
            if (-not $readiness.Stable) {
                throw "Pre-click frame did not stabilize: $($readiness.Note); last changed percent: $($readiness.LastChangedPercent)"
            }
            $preClickReady = Measure-PreClickReadiness -FramePath $before.Path -ClickX $point.X -ClickY $point.Y
            if (-not $preClickReady.Ready) {
                throw "Pre-click frame is not menu-ready: $($preClickReady.Note)"
            }
            $clickInfo = Invoke-ClientClick -Process $process -X $point.X -Y $point.Y -Mode $ClickMode -HoldMs $ClickHoldMs -Repeat $ClickRepeat
            $clickAttempted = $true
            Start-Sleep -Milliseconds $AfterClickWaitMs

            $process.Refresh()
            $exitedAfterWait = $process.HasExited
            if (-not $exitedAfterWait) {
                $after = Save-ClientFrame -Process $process -Path (Join-Path $caseDir 'after.png')
                $diff = Compare-PngFrames -Before $before.Path -After $after.Path -Step $DiffStep
            }

            if ($point.Kind -eq 'exit') {
                $passed = $exitedAfterWait -or ($diff -ne $null -and $diff.ChangedPercent -ge 1.0)
            } else {
                $passed = ($diff -ne $null -and $diff.ChangedPercent -ge 1.0)
            }
        } catch {
            $errorText = $_.Exception.Message
        } finally {
            $process.Refresh()
            if (-not $process.HasExited -and (-not $KeepOpenOnFailure -or $passed)) {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        }

        $result = [pscustomobject]@{
            Exe = $runExe
            Case = $caseName
            Click = $clickName
            ClickDescription = $point.Description
            ClickMode = $ClickMode
            ClickHoldMs = $ClickHoldMs
            ClickRepeat = $ClickRepeat
            ClientClickX = $point.X
            ClientClickY = $point.Y
            PreClickStable = if ($readiness) { $readiness.Stable } else { $null }
            PreClickStableSamples = if ($readiness) { $readiness.Samples } else { $null }
            PreClickStableAttempts = if ($readiness) { $readiness.Attempts } else { $null }
            PreClickLastChangedPercent = if ($readiness) { $readiness.LastChangedPercent } else { $null }
            PreClickReady = if ($preClickReady) { $preClickReady.Ready } else { $null }
            PreClickNonblackPercent = if ($preClickReady) { $preClickReady.NonblackPercent } else { $null }
            PreClickTargetMeanLuma = if ($preClickReady) { $preClickReady.TargetMeanLuma } else { $null }
            PreClickTargetBrightPercent = if ($preClickReady) { $preClickReady.TargetBrightPercent } else { $null }
            ClickAttempted = $clickAttempted
            PreClickReadinessNote = if ($preClickReady -and $preClickReady.Note) { $preClickReady.Note } elseif ($readiness) { $readiness.Note } else { $null }
            ScreenClickX = if ($clickInfo) { $clickInfo.ScreenX } else { $null }
            ScreenClickY = if ($clickInfo) { $clickInfo.ScreenY } else { $null }
            ClientWidth = if ($before) { $before.ClientWidth } else { $null }
            ClientHeight = if ($before) { $before.ClientHeight } else { $null }
            RenderScale = if ($before) { $before.RenderScale } else { $null }
            RenderX = if ($before) { $before.RenderX } else { $null }
            RenderY = if ($before) { $before.RenderY } else { $null }
            CaptureWidth = if ($before) { $before.Width } else { $null }
            CaptureHeight = if ($before) { $before.Height } else { $null }
            Before = if ($before) { $before.Path } else { $null }
            After = if ($after) { $after.Path } else { $null }
            BeforeHash = if ($before) { $before.Hash } else { $null }
            AfterHash = if ($after) { $after.Hash } else { $null }
            ChangedPercent = if ($diff) { $diff.ChangedPercent } else { $null }
            ExitedAfterClick = $exitedAfterWait
            ExitCode = if ($exitedAfterWait) { $process.ExitCode } else { $null }
            Passed = $passed
            Error = $errorText
        }
        $results.Add($result) | Out-Null
    }
}

if (-not $KeepOpenOnFailure) {
    Stop-ClashProcesses -Root $WorkDir
}

$jsonPath = Join-Path $outDir 'results.json'
$csvPath = Join-Path $outDir 'results.csv'
$results | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $jsonPath -Encoding ASCII
$results | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding ASCII

$results |
    Select-Object Case,Click,ClientWidth,ClientHeight,RenderScale,CaptureWidth,CaptureHeight,PreClickStable,PreClickReady,PreClickNonblackPercent,PreClickTargetBrightPercent,ClickAttempted,ChangedPercent,ExitedAfterClick,Passed,Error |
    Format-Table -AutoSize

[pscustomobject]@{
    OutputDirectory = $outDir
    Json = $jsonPath
    Csv = $csvPath
}
