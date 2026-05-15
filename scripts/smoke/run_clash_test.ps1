param(
    [string]$Exe = 'C:\Clash\clash95_hddisplay_absinput.exe',
    [string]$WorkDir = 'C:\Clash',
    [switch]$Probe,
    [string]$Log,
    [int]$MenuWaitSec = 8,
    [int]$AutoCloseSec = 0,
    [switch]$KeepExisting
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Exe)) {
    throw "Executable was not found: $Exe"
}
if (-not (Test-Path -LiteralPath $WorkDir)) {
    throw "Working directory was not found: $WorkDir"
}

if (-not $KeepExisting) {
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Path -like 'C:\Clash\clash95*.exe' -or
            $_.Path -eq 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe'
        } |
        Stop-Process -Force -ErrorAction SilentlyContinue
}

if ($Probe) {
    $probeRunner = Join-Path (Join-Path $PSScriptRoot '..\cdb') 'run_cdb_mouse_probe.ps1'
    if (-not (Test-Path -LiteralPath $probeRunner)) {
        throw "Probe runner was not found: $probeRunner"
    }
    if (-not $Log) {
        $name = [IO.Path]::GetFileNameWithoutExtension($Exe)
        $Log = Join-Path $WorkDir "$name-cdb-probe.log"
    }
    & $probeRunner -Exe $Exe -Log $Log -NoWait
    Start-Sleep -Seconds $MenuWaitSec
    $game = Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $Exe } |
        Select-Object -First 1
    [pscustomobject]@{
        Mode = 'cdb'
        Exe = $Exe
        GamePid = if ($game) { $game.Id } else { $null }
        Log = $Log
    }
} else {
    $process = Start-Process -FilePath $Exe -WorkingDirectory $WorkDir -PassThru
    Start-Sleep -Seconds $MenuWaitSec
    [pscustomobject]@{
        Mode = 'direct'
        Exe = $Exe
        GamePid = $process.Id
        Log = $null
    }
}

if ($AutoCloseSec -gt 0) {
    Start-Sleep -Seconds $AutoCloseSec
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $Exe } |
        Stop-Process -Force -ErrorAction SilentlyContinue
}
