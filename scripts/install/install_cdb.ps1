$ErrorActionPreference = 'Stop'

# Installs only "Debugging Tools for Windows" from the Windows SDK.
# Run from an elevated PowerShell prompt.

$sdkInstallerUrl = 'https://go.microsoft.com/fwlink/?linkid=2358390'
$installer = Join-Path $env:TEMP 'winsdksetup.exe'
$installRoot = 'C:\Program Files (x86)\Windows Kits\10'
$x86DebuggerDir = Join-Path $installRoot 'Debuggers\x86'
$x64DebuggerDir = Join-Path $installRoot 'Debuggers\x64'
$cdbX86 = Join-Path $x86DebuggerDir 'cdb.exe'
$cdbX64 = Join-Path $x64DebuggerDir 'cdb.exe'

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    throw 'Please run this script from an elevated PowerShell prompt.'
}

Write-Host "Downloading Windows SDK installer..."
Invoke-WebRequest -Uri $sdkInstallerUrl -OutFile $installer -UseBasicParsing

Write-Host "Installing Debugging Tools for Windows..."
$argumentLine = '/features OptionId.WindowsDesktopDebuggers /q /norestart'
$process = Start-Process -FilePath $installer -ArgumentList $argumentLine -Wait -PassThru
if ($process.ExitCode -ne 0) {
    $latestLog = Get-ChildItem -Path (Join-Path $env:TEMP 'windowssdk') -Filter *.log -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($latestLog) {
        Write-Host "Latest Windows SDK setup log: $($latestLog.FullName)"
        Get-Content -LiteralPath $latestLog.FullName -Tail 40
    }

    throw "winsdksetup.exe failed with exit code $($process.ExitCode)"
}

if (-not (Test-Path -LiteralPath $cdbX86)) {
    throw "Install completed, but x86 cdb.exe was not found at $cdbX86"
}

$machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
$pathParts = $machinePath -split ';' | Where-Object { $_ }
$newParts = @($x86DebuggerDir, $x64DebuggerDir) | Where-Object {
    (Test-Path -LiteralPath $_) -and ($pathParts -notcontains $_)
}

if ($newParts.Count -gt 0) {
    [Environment]::SetEnvironmentVariable(
        'Path',
        (($pathParts + $newParts) -join ';'),
        'Machine'
    )
    $env:Path = (($env:Path -split ';' | Where-Object { $_ }) + $newParts) -join ';'
}

Write-Host "Installed:"
Write-Host "  x86 CDB: $cdbX86"
if (Test-Path -LiteralPath $cdbX64) {
    Write-Host "  x64 CDB: $cdbX64"
}
Write-Host ''
Write-Host 'For Clash95 use the x86 debugger:'
Write-Host "  `"$cdbX86`" -version"
