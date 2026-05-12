param(
    [string]$Exe = 'C:\Clash\clash95_hd_mouseabsq_20260422.exe',
    [string]$WorkDir = 'C:\Clash',
    [string]$Cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe',
    [string]$Probe = (Join-Path $PSScriptRoot 'clash95_mouse_menu_dynamic_probe.cdb'),
    [string]$Log = (Join-Path $PSScriptRoot 'captures\cdb-python-mouse-map.log'),
    [string]$Python = 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [string]$OutJson = (Join-Path $PSScriptRoot 'captures\mouseclickmap-cdb-python.json'),
    [string]$Points = '239,196;265,264;320,285;437,196;468,264',
    [ValidateSet('sendinput', 'postmessage', 'both')]
    [string]$ClickMode = 'sendinput',
    [int]$ClickHoldMs = 250,
    [int]$ClickRepeat = 2,
    [int]$RunSeconds = 8,
    [int]$WindowTimeoutSec = 12,
    [int]$SkipPulses = 4,
    [int]$SkipIntervalMs = 500,
    [int]$MoveWindowX = 80,
    [int]$MoveWindowY = 80
)

$ErrorActionPreference = 'Stop'

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

foreach ($path in @($Exe, $WorkDir, $Cdb, $Probe, $Python)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required path was not found: $path"
    }
}

$mouseTool = Join-Path $PSScriptRoot 'tools\mouse_path_probe.py'
if (-not (Test-Path -LiteralPath $mouseTool)) {
    throw "Mouse path probe was not found: $mouseTool"
}

$logDir = Split-Path -Parent $Log
if ($logDir -and -not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$jsonDir = Split-Path -Parent $OutJson
if ($jsonDir -and -not (Test-Path -LiteralPath $jsonDir)) {
    New-Item -ItemType Directory -Path $jsonDir -Force | Out-Null
}

Stop-ProbeProcesses
if (Test-Path -LiteralPath $Log) {
    Remove-Item -LiteralPath $Log -Force
}
if (Test-Path -LiteralPath $OutJson) {
    Remove-Item -LiteralPath $OutJson -Force
}

$cdbArgs = @('-hd', '-logo', $Log, '-cf', $Probe, $Exe)
$cdbProcess = Start-Process -FilePath $Cdb -ArgumentList $cdbArgs -WorkingDirectory $WorkDir -PassThru

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
        '--interval-ms', '350',
        '--points', $Points,
        '--click',
        '--click-mode', $ClickMode,
        '--click-hold-ms', $ClickHoldMs,
        '--click-repeat', $ClickRepeat,
        '--json', $OutJson
    )

    & $Python @mouseArgs

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

[pscustomobject]@{
    Exe = $Exe
    Probe = $Probe
    Log = $Log
    MouseJson = $OutJson
    ClickMode = $ClickMode
    ClickHoldMs = $ClickHoldMs
    ClickRepeat = $ClickRepeat
    Points = $Points
}
