param(
    [string]$Exe,
    [string]$WorkDir,
    [string]$Cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe',
    [string]$Probe,
    [string]$Log,
    [string]$Python = 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [string]$OutJson,
    [string]$Points = '588,440',
    [ValidateSet('window', 'raw-screen')]
    [string]$InputMode = 'window',
    [string]$RawScreenPoints = '668,520',
    [ValidateSet('sendinput', 'postmessage', 'both')]
    [string]$ClickMode = 'sendinput',
    [ValidateSet('setcursor', 'sendinput-absolute', 'sendinput-relative', 'sendinput-client-delta', 'auto', 'none')]
    [string]$MoveMode = 'auto',
    [int]$ClickHoldMs = 180,
    [int]$ClickRepeat = 4,
    [int]$RunSeconds = 12,
    [int]$WindowTimeoutSec = 20,
    [int]$ReadyTimeoutSec = 60,
    [string]$ReadyPattern = 'BATTLE_COMMAND_INPUT_WINDOW',
    [int]$MoveWindowX = 80,
    [int]$MoveWindowY = 80,
    [switch]$AllowVisibleRuntime
)

$ErrorActionPreference = 'Stop'
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

if (-not $AllowVisibleRuntime) {
    throw "This harness launches a visible Clash95 runtime and sends mouse input. Re-run with -AllowVisibleRuntime only after explicit user approval."
}

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

if (-not ('ClashWin' -as [type])) {
    Add-Type @'
using System; using System.Runtime.InteropServices; using System.Text;
public class ClashWin {
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
  delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] static extern int GetWindowTextLength(IntPtr h);
  // A visible top-level window with a title owned by the target pid. The GOG
  // ddraw wrapper can leave Process.MainWindowHandle null even when this window
  // exists (documented in AGENTS.md), so enumerate instead of trusting .NET.
  public static bool HasVisibleWindow(uint target){
    bool found=false;
    EnumWindows((h,l)=>{ uint p; GetWindowThreadProcessId(h,out p);
      if(p==target && IsWindowVisible(h) && GetWindowTextLength(h)>0){ found=true; return false; }
      return true; }, IntPtr.Zero);
    return found;
  }
}
'@
}

function Get-ClashWindowProcess {
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ProcessName -like 'clash95*' -and
            ($_.MainWindowHandle -ne [IntPtr]::Zero -or [ClashWin]::HasVisibleWindow([uint32]$_.Id))
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

function Wait-LogPattern {
    param(
        [string]$Path,
        [string]$Pattern,
        [int]$TimeoutSec
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $processedLineCount = 0
    $cdbHasStarted = $false
    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $Path) {
            # Probe printf rows can arrive without trailing newlines, gluing the
            # ready marker onto a prompt-prefixed or still-unterminated line that
            # the per-line scan below skips. Match the pattern on raw content
            # first; keep the line scan for breakpoint-failure detection.
            try {
                $rawStream = [System.IO.File]::Open($Path, 'Open', 'Read', 'ReadWrite')
                try {
                    $rawReader = New-Object System.IO.StreamReader($rawStream)
                    $rawText = $rawReader.ReadToEnd()
                }
                finally {
                    $rawStream.Dispose()
                }
                # CDB echoes the probe script into the log, so the pattern also
                # appears inside bp definitions with %d/%p placeholders. Accept
                # only an occurrence whose following text carries real values
                # (no % format placeholders).
                $patternIndex = 0
                while (($patternIndex = $rawText.IndexOf($Pattern, $patternIndex)) -ge 0) {
                    $tailStart = $patternIndex + $Pattern.Length
                    $tailLength = [Math]::Min(160, $rawText.Length - $tailStart)
                    $tail = $rawText.Substring($tailStart, $tailLength)
                    if (-not $tail.Contains('%')) {
                        return
                    }
                    $patternIndex = $tailStart
                }
            }
            catch {
            }
            $lines = @(Get-Content -LiteralPath $Path)
            if ($lines.Count -lt $processedLineCount) {
                $processedLineCount = 0
            }
            $newLines = @($lines | Select-Object -Skip $processedLineCount)
            $processedLineCount = $lines.Count
            if ($newLines.Count -eq 0) {
                Start-Sleep -Milliseconds 250
                continue
            }
            foreach ($line in $newLines) {
                $trimmed = $line.TrimStart()
                if ($trimmed -match '^\d+:\d+>\s*g\s*$') {
                    $cdbHasStarted = $true
                    continue
                }
                if ($line.Contains('Unable to insert breakpoint') -or $line.Contains('Unable to remove breakpoint')) {
                    throw "CDB became invalid before '$Pattern': $line"
                }
                if ($cdbHasStarted -and $line.Contains('Break instruction exception - code 80000003')) {
                    throw "CDB became invalid before '$Pattern': $line"
                }
                if ($trimmed -match '^\d+:\d+>') {
                    continue
                }
                if ($line.Contains($Pattern)) {
                    return
                }
            }
        }
        Start-Sleep -Milliseconds 250
    }
    throw "Timed out waiting for log pattern '$Pattern' in $Path"
}

foreach ($required in @($Exe, $WorkDir, $Cdb, $Probe, $Python)) {
    if (-not $required) {
        throw "A required path parameter was empty."
    }
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required path was not found: $required"
    }
}

if (-not $Log) {
    throw "Log path was not provided."
}
if (-not $OutJson) {
    throw "OutJson path was not provided."
}

$mouseTool = Join-Path $RepoRoot 'tools\mouse_path_probe.py'
if (-not (Test-Path -LiteralPath $mouseTool)) {
    throw "Mouse path probe was not found: $mouseTool"
}
$rawClickTool = Join-Path $RepoRoot 'tools\raw_sendinput_click.py'
if (-not (Test-Path -LiteralPath $rawClickTool)) {
    throw "Raw SendInput click helper was not found: $rawClickTool"
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
Remove-Item -LiteralPath $Log -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $OutJson -Force -ErrorAction SilentlyContinue

$cdbArgs = @('-hd', '-logo', $Log, '-cf', $Probe, $Exe)
$cdbProcess = Start-Process -FilePath $Cdb -ArgumentList $cdbArgs -WorkingDirectory $WorkDir -PassThru -WindowStyle Hidden

try {
    if ($InputMode -eq 'raw-screen') {
        Wait-LogPattern -Path $Log -Pattern $ReadyPattern -TimeoutSec $ReadyTimeoutSec
        $rawClickArgs = @(
            $rawClickTool,
            '--screen-points', $RawScreenPoints,
            '--settle-sec', '0.25',
            '--interval-ms', '120',
            '--click-hold-ms', $ClickHoldMs,
            '--click-repeat', $ClickRepeat,
            '--json', $OutJson
        )
        & $Python @rawClickArgs
    } else {
        $game = Wait-ClashWindowProcess -TimeoutSec $WindowTimeoutSec
        Wait-LogPattern -Path $Log -Pattern $ReadyPattern -TimeoutSec $ReadyTimeoutSec
        $mouseArgs = @(
            $mouseTool,
            '--pid', $game.Id,
            '--workdir', $WorkDir,
            '--move-window', $MoveWindowX, $MoveWindowY,
            '--settle-sec', '0.25',
            '--interval-ms', '250',
            '--points', $Points,
            '--click',
            '--click-mode', $ClickMode,
            '--move-mode', $MoveMode,
            '--click-hold-ms', $ClickHoldMs,
            '--click-repeat', $ClickRepeat,
            '--json', $OutJson
        )
        & $Python @mouseArgs
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
    Get-Content -LiteralPath $Log | Select-Object -Last 160
} else {
    Write-Warning "CDB log was not created: $Log"
}

[pscustomobject]@{
    Exe = $Exe
    WorkDir = $WorkDir
    Probe = $Probe
    Log = $Log
    MouseJson = $OutJson
    ReadyPattern = $ReadyPattern
    InputMode = $InputMode
    ClickMode = $ClickMode
    MoveMode = $MoveMode
    ClickHoldMs = $ClickHoldMs
    ClickRepeat = $ClickRepeat
    Points = $Points
    RawScreenPoints = $RawScreenPoints
}
