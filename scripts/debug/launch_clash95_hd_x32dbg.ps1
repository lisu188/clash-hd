$ErrorActionPreference = 'Stop'

$x32dbg = 'C:\Tools\x64dbg\release\x32\x32dbg.exe'
$target = 'C:\Clash\clash95_hdtest.exe'
$script = Join-Path (Join-Path $PSScriptRoot '..\..') 'clash95_hd_x32dbg_checkpoints.xdbg'
$workDir = Split-Path -Parent $target

if (-not (Test-Path -LiteralPath $x32dbg)) {
    throw "x32dbg.exe was not found at $x32dbg"
}

if (-not (Test-Path -LiteralPath $target)) {
    throw "Patched Clash executable was not found at $target"
}

if (-not (Test-Path -LiteralPath $script)) {
    throw "x32dbg script was not found at $script"
}

$debugCommand = 'scriptexec "' + $script + '"'

Start-Process -FilePath $x32dbg -WorkingDirectory $workDir -ArgumentList @(
    "`"$target`"",
    '-workingDir',
    "`"$workDir`"",
    '-c',
    "`"$debugCommand`""
)

Write-Host "Launched x32dbg for $target"
Write-Host "Startup command: $debugCommand"
