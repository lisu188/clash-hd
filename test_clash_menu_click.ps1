param(
    [string[]]$Exe = @('.\clash95_hddisplay_absinput.exe'),
    [string]$WorkDir = 'C:\Clash',
    [string[]]$Click = @('native-exit', 'centered-exit'),
    [string]$OutRoot = (Join-Path $PSScriptRoot 'captures'),
    [int]$MenuWaitSec = 6,
    [int]$AfterClickWaitMs = 1500,
    [int]$DiffStep = 8,
    [int]$SurfaceWidth = 800,
    [int]$SurfaceHeight = 600,
    [int]$SkipIntroClicks = 4,
    [int]$SkipIntroIntervalMs = 500,
    [int]$SkipIntroX = 400,
    [int]$SkipIntroY = 300,
    [string[]]$SkipIntroKeys = @('Space'),
    [ValidateSet('SendInput', 'PostMessage', 'Both')]
    [string]$SkipIntroClickMode = 'Both',
    [switch]$CaptureFullClient,
    [ValidateSet('SendInput', 'PostMessage', 'Both')]
    [string]$ClickMode = 'SendInput',
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

    [DllImport("user32.dll", SetLastError=true)]
    public static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);

    [DllImport("user32.dll")]
    public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
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
        if ($Process.HasExited) {
            throw "Process exited before its main window appeared: $($Process.Id)"
        }
        $Process.Refresh()
        if ($Process.MainWindowHandle -ne [IntPtr]::Zero) {
            return $Process.MainWindowHandle
        }
        Start-Sleep -Milliseconds 200
    }

    throw "Timed out waiting for main window for process $($Process.Id)"
}

function Get-ClientInfo {
    param([System.Diagnostics.Process]$Process)

    $Process.Refresh()
    if ($Process.MainWindowHandle -eq [IntPtr]::Zero) {
        throw "Process has no visible main window: $($Process.Id)"
    }

    $rect = New-Object ClashWin32+RECT
    [ClashWin32]::GetClientRect($Process.MainWindowHandle, [ref]$rect) | Out-Null

    $origin = New-Object ClashWin32+POINT
    $origin.X = 0
    $origin.Y = 0
    [ClashWin32]::ClientToScreen($Process.MainWindowHandle, [ref]$origin) | Out-Null

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
        Handle = $Process.MainWindowHandle
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

    [ClashWin32]::ShowWindow($Process.MainWindowHandle, 5) | Out-Null
    [ClashWin32]::BringWindowToTop($Process.MainWindowHandle) | Out-Null
    [ClashWin32]::SetForegroundWindow($Process.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds 250
}

function Save-ClientFrame {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$Path
    )

    $info = Get-ClientInfo -Process $Process
    Focus-GameWindow -Process $Process

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

function Invoke-ClientClick {
    param(
        [System.Diagnostics.Process]$Process,
        [int]$X,
        [int]$Y,
        [string]$Mode
    )

    $info = Get-ClientInfo -Process $Process
    Focus-GameWindow -Process $Process

    $screenX = [int]($info.RenderX + [math]::Floor(($X + 0.5) * $info.RenderScale))
    $screenY = [int]($info.RenderY + [math]::Floor(($Y + 0.5) * $info.RenderScale))
    [ClashWin32]::SetCursorPos($screenX, $screenY) | Out-Null
    Start-Sleep -Milliseconds 150

    if ($Mode -eq 'SendInput' -or $Mode -eq 'Both') {
        $down = New-Object ClashWin32+INPUT
        $down.type = 0
        $down.mi.dwFlags = 0x0002

        $up = New-Object ClashWin32+INPUT
        $up.type = 0
        $up.mi.dwFlags = 0x0004

        $inputs = [ClashWin32+INPUT[]]@($down, $up)
        $size = [Runtime.InteropServices.Marshal]::SizeOf([type][ClashWin32+INPUT])
        [ClashWin32]::SendInput(2, $inputs, $size) | Out-Null
    }

    if ($Mode -eq 'PostMessage' -or $Mode -eq 'Both') {
        $lParam = [IntPtr](($Y -shl 16) -bor ($X -band 0xffff))
        [ClashWin32]::PostMessage($Process.MainWindowHandle, 0x0201, [IntPtr]1, $lParam) | Out-Null
        Start-Sleep -Milliseconds 50
        [ClashWin32]::PostMessage($Process.MainWindowHandle, 0x0202, [IntPtr]0, $lParam) | Out-Null
    }

    [pscustomobject]@{
        ClientX = $X
        ClientY = $Y
        ScreenX = $screenX
        ScreenY = $screenY
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
            $before = Save-ClientFrame -Process $process -Path (Join-Path $caseDir 'before.png')
            $clickInfo = Invoke-ClientClick -Process $process -X $point.X -Y $point.Y -Mode $ClickMode
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
            ClientClickX = $point.X
            ClientClickY = $point.Y
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
    Select-Object Case,Click,ClientWidth,ClientHeight,RenderScale,CaptureWidth,CaptureHeight,ChangedPercent,ExitedAfterClick,Passed,Error |
    Format-Table -AutoSize

[pscustomobject]@{
    OutputDirectory = $outDir
    Json = $jsonPath
    Csv = $csvPath
}
