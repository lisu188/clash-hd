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

function Assert-BuildReserve {
    param([string]$Path, [long]$PendingBytes = 536870912)
    $volume = [System.IO.DriveInfo]::new([System.IO.Path]::GetPathRoot($Path))
    if (-not $volume.IsReady -or $volume.TotalSize -le 0 -or
        ($volume.AvailableFreeSpace - $PendingBytes) -le ($volume.TotalSize / 10)) {
        throw "Launcher build requires more than ten percent free space plus its 512 MiB allowance: $Path"
    }
}

$OutputDirFull = [System.IO.Path]::GetFullPath($OutputDir)
if (Test-IsUnderPath $OutputDirFull $RepoRoot) {
    throw "Refusing PyInstaller output inside the repository: $OutputDirFull. The packaging boundary forbids committed executables; build under C:\ClashTests\launcher\build."
}

$PythonFull = Find-Python -Requested $Python
$RunScript = Join-Path $RepoRoot 'src\launcher\run.py'
$BuildRoot = Join-Path $OutputDirFull ('launcher-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$WorkDir = Join-Path $BuildRoot 'work'
$DistDir = Join-Path $BuildRoot 'dist'
$SpecDir = Join-Path $BuildRoot 'spec'
$BundleDir = Join-Path $BuildRoot 'bundle'

Write-Host 'Clash95 HD launcher local build plan'
Write-Host "Dry run: $(-not [bool]$Execute)"
Write-Host "Python: $PythonFull"
Write-Host "Entry: $RunScript"
Write-Host "Output: $DistDir\ClashHDLauncher.exe"
Write-Host 'Resources: fixed public-source allowlist, exact source bytes, launcher catalog and wrapper configuration template.'
Write-Host 'The package includes no game executable, DirectDraw wrapper, game assets, saves or captures.'
Write-Host 'The build output is local-only and must never be committed; the repository .gitignore and exe artifact guard enforce this.'

if (-not $Execute) {
    Write-Host 'Re-run with -Execute to build. PyInstaller must already be installed for this Python (pip install pyinstaller).'
    exit 0
}

Assert-BuildReserve -Path $RepoRoot
Assert-BuildReserve -Path $OutputDirFull
& $PythonFull -m PyInstaller --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller is not installed for this Python. Install it with: pip install pyinstaller'
}

New-Item -ItemType Directory -Force -Path $OutputDirFull | Out-Null
$BundleRaw = & $PythonFull -B (Join-Path $RepoRoot 'tools\prepare_launcher_bundle.py') --destination $BundleDir
if ($LASTEXITCODE -ne 0) {
    throw 'Launcher resource preflight or staging failed.'
}
$Bundle = ($BundleRaw -join [Environment]::NewLine) | ConvertFrom-Json
$BuildArguments = @('-m', 'PyInstaller', '--noconfirm', '--onefile', '--windowed',
    '--name', 'ClashHDLauncher', '--distpath', $DistDir, '--workpath', $WorkDir, '--specpath', $SpecDir,
    '--paths', $RepoRoot, '--paths', (Join-Path $RepoRoot 'src\launcher'),
    '--paths', (Join-Path $RepoRoot 'tools'), '--paths', $Bundle.identity_root,
    '--add-data', ($Bundle.resource_root + ';.'))
foreach ($Module in $Bundle.hidden_imports) {
    $BuildArguments += @('--hidden-import', [string]$Module)
}
$BuildArguments += $RunScript
& $PythonFull @BuildArguments
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

$PostBuildInventory = & $PythonFull -B -c "import sys; sys.path.insert(0, sys.argv[1]); import package_resources as r; print(r.sha256(r.inventory_bytes(sys.argv[2])))" (Join-Path $RepoRoot 'src\launcher') $RepoRoot
if ($LASTEXITCODE -ne 0 -or $PostBuildInventory.Trim() -ne $Bundle.inventory_sha256) {
    throw 'Launcher sources changed during compilation; the executable is not accepted for delivery.'
}
Assert-BuildReserve -Path $OutputDirFull -PendingBytes 0
Write-Host "Built: $DistDir\ClashHDLauncher.exe"
exit 0
