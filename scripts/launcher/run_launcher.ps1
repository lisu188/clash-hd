param(
    [string]$Python = '',
    [switch]$DryRun,
    [switch]$GuiSelftest,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$RemainingArgs = @()
)

$ErrorActionPreference = 'Stop'

$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

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

$PythonFull = Find-Python -Requested $Python
$RunScript = Join-Path $RepoRoot 'src\launcher\run.py'
if (-not (Test-Path -LiteralPath $RunScript -PathType Leaf)) {
    throw "Launcher entry script not found: $RunScript"
}

$LauncherArgs = @()
if ($DryRun) { $LauncherArgs += '--dry-run' }
if ($GuiSelftest) { $LauncherArgs += '--gui-selftest' }
$LauncherArgs += $RemainingArgs

& $PythonFull $RunScript @LauncherArgs
exit $LASTEXITCODE
