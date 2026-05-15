param(
    [string]$Exe = 'C:\Clash\clash95_hdcentered_hitboxes.exe',
    [string]$Cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe',
    [string]$Log = 'C:\Clash\hd-cdb-mouse-probe.log',
    [switch]$NoWait
)

$ErrorActionPreference = 'Stop'
$Probe = Join-Path (Join-Path $PSScriptRoot '..\..') 'probes/cdb/mouse/clash95_mouse_probe.cdb'

if (-not (Test-Path -LiteralPath $Cdb)) {
    throw "cdb.exe was not found at: $Cdb"
}
if (-not (Test-Path -LiteralPath $Exe)) {
    throw "Target executable was not found at: $Exe"
}
if (-not (Test-Path -LiteralPath $Probe)) {
    throw "Probe script was not found at: $Probe"
}

if (Test-Path -LiteralPath $Log) {
    Remove-Item -LiteralPath $Log -Force
}

$argsList = @('-hd', '-logo', $Log, '-cf', $Probe, $Exe)
$workDir = Split-Path -Parent $Exe

if ($NoWait) {
    $process = Start-Process -FilePath $Cdb -ArgumentList $argsList -WorkingDirectory $workDir -PassThru
    Write-Host "Started CDB mouse probe. PID: $($process.Id)"
    Write-Host "Log: $Log"
    Write-Host "Move/click in the game, close it, then inspect the log."
} else {
    & $Cdb @argsList
    Write-Host "Probe finished. Log: $Log"
}
