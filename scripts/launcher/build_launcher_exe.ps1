param(
    [string]$Python = '',
    [string]$OutputDir = 'C:\ClashTests\launcher\build',
    [switch]$Execute
)

$ErrorActionPreference = 'Stop'

$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

function Test-IsUnderPath {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Root
    )
    $fullPath = [System.IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
    $fullRoot = [System.IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
    if ($fullPath.Equals($fullRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $true
    }
    return $fullPath.StartsWith($fullRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)
}

function Find-Python {
    param([string]$Requested)
    if ($Requested) {
        if (-not (Test-Path -LiteralPath $Requested -PathType Leaf)) {
            throw "Python path does not exist: $Requested"
        }
        return [System.IO.Path]::GetFullPath($Requested)
    }

    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $bundled = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundled -PathType Leaf) {
        return $bundled
    }

    throw 'Python 3 was not found on PATH and the bundled Codex runtime was not found.'
}

$OutputDirFull = [System.IO.Path]::GetFullPath($OutputDir)
if (Test-IsUnderPath $OutputDirFull $RepoRoot) {
    throw "Refusing PyInstaller output inside the repository: $OutputDirFull. The packaging boundary forbids committed executables; build under C:\ClashTests\launcher\build."
}

$PythonFull = Find-Python -Requested $Python
$RunScript = Join-Path $RepoRoot 'src\launcher\run.py'
$WorkDir = Join-Path $OutputDirFull 'work'
$DistDir = Join-Path $OutputDirFull 'dist'
$SpecDir = Join-Path $OutputDirFull 'spec'

Write-Host 'Clash95 HD launcher local build plan'
Write-Host "Dry run: $(-not [bool]$Execute)"
Write-Host "Python: $PythonFull"
Write-Host "Entry: $RunScript"
Write-Host "Output: $DistDir\ClashHDLauncher.exe"
Write-Host 'The build output is local-only and must never be committed; the repository .gitignore and exe artifact guard enforce this.'

if (-not $Execute) {
    Write-Host 'Re-run with -Execute to build. PyInstaller must already be installed for this Python (pip install pyinstaller).'
    exit 0
}

& $PythonFull -m PyInstaller --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller is not installed for this Python. Install it with: pip install pyinstaller'
}

New-Item -ItemType Directory -Force -Path $OutputDirFull | Out-Null
& $PythonFull -m PyInstaller `
    --onefile `
    --windowed `
    --name ClashHDLauncher `
    --distpath $DistDir `
    --workpath $WorkDir `
    --specpath $SpecDir `
    --add-data ((Join-Path $RepoRoot 'src\launcher\resolutions.json') + ';.') `
    --add-data ((Join-Path $RepoRoot 'dxcfg_windowed.ini') + ';.') `
    $RunScript
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

Write-Host "Built: $DistDir\ClashHDLauncher.exe"
exit 0
