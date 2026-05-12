param(
    [string]$InputExe = 'C:\Clash\clash95.exe',
    [string]$CandidateDir = 'C:\ClashTests\hd-map-smoke',
    [string]$CandidateName = '',
    [string]$Python = '',
    [string]$Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch',
    [string]$NormalRun = (Join-Path $PSScriptRoot 'captures\cdb-surface-dump-20260506-190037'),
    [string]$ForcedRun = (Join-Path $PSScriptRoot 'captures\cdb-surface-dump-20260506-201114'),
    [string]$PatchManifest = (Join-Path $PSScriptRoot 'captures\patch-stage-current-hd-map.json'),
    [string]$MatrixJson = (Join-Path $PSScriptRoot 'captures\hd-map-smoke-current.json'),
    [string]$MatrixMarkdown = (Join-Path $PSScriptRoot 'captures\hd-map-smoke-current.md'),
    [switch]$Execute,
    [switch]$AllowRepoCandidateDir,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'

$ExpectedBaseSha256 = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
$RepoRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)

function Resolve-PlanPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot $Path))
}

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
        return (Resolve-PlanPath $Requested)
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

function Quote-Arg {
    param([Parameter(Mandatory = $true)][string]$Value)
    return "'" + ($Value -replace "'", "''") + "'"
}

$InputExeFull = Resolve-PlanPath $InputExe
$CandidateDirFull = Resolve-PlanPath $CandidateDir
if (-not $CandidateName) {
    $CandidateName = 'clash95_hd_smoke_{0}.exe' -f (Get-Date -Format 'yyyyMMdd_HHmmss')
}
if ([System.IO.Path]::GetExtension($CandidateName) -ne '.exe') {
    throw "CandidateName must end with .exe: $CandidateName"
}
$CandidateFull = Resolve-PlanPath (Join-Path $CandidateDirFull $CandidateName)
$PatchManifestFull = Resolve-PlanPath $PatchManifest
$MatrixJsonFull = Resolve-PlanPath $MatrixJson
$MatrixMarkdownFull = Resolve-PlanPath $MatrixMarkdown
$NormalRunFull = Resolve-PlanPath $NormalRun
$ForcedRunFull = Resolve-PlanPath $ForcedRun
$PythonFull = Find-Python $Python

if ((Test-IsUnderPath $CandidateDirFull $RepoRoot) -and -not $AllowRepoCandidateDir) {
    throw "Refusing candidate output inside repository by default: $CandidateDirFull. Use -AllowRepoCandidateDir only for a deliberate local handoff."
}

$InputExists = Test-Path -LiteralPath $InputExeFull -PathType Leaf
$InputSha256 = $null
$BaseShaStatus = 'missing'
if ($InputExists) {
    $InputSha256 = (Get-FileHash -LiteralPath $InputExeFull -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($InputSha256 -ne $ExpectedBaseSha256) {
        throw "Unexpected base SHA-256 for $InputExeFull. Expected $ExpectedBaseSha256 but found $InputSha256."
    }
    $BaseShaStatus = 'ok'
}

$Plan = [ordered]@{
    dry_run = -not [bool]$Execute
    repo_root = $RepoRoot
    input_exe = $InputExeFull
    input_exists = $InputExists
    expected_base_sha256 = $ExpectedBaseSha256
    input_sha256 = $InputSha256
    base_sha_status = $BaseShaStatus
    stage = $Stage
    python = $PythonFull
    candidate_dir = $CandidateDirFull
    candidate_path = $CandidateFull
    patch_manifest = $PatchManifestFull
    normal_run = $NormalRunFull
    forced_run = $ForcedRunFull
    matrix_json = $MatrixJsonFull
    matrix_markdown = $MatrixMarkdownFull
}

$PatchCommand = @(
    '&', (Quote-Arg $PythonFull), (Quote-Arg (Join-Path $RepoRoot 'patch_clash95_hd.py')),
    '--input', (Quote-Arg $InputExeFull),
    '--output', (Quote-Arg $CandidateFull),
    '--stage', (Quote-Arg $Stage)
) -join ' '
$ManifestCommand = @(
    '&', (Quote-Arg $PythonFull), (Quote-Arg (Join-Path $RepoRoot 'tools\patch_stage_report.py')),
    '--exe', (Quote-Arg $CandidateFull),
    '--stage', (Quote-Arg $Stage),
    '--require-current-hd-map',
    '--write-json', (Quote-Arg $PatchManifestFull)
) -join ' '
$MatrixCommand = @(
    '&', (Quote-Arg $PythonFull), (Quote-Arg (Join-Path $RepoRoot 'tools\hd_map_smoke_matrix.py')),
    '--patch-exe', (Quote-Arg $CandidateFull),
    '--stage', (Quote-Arg $Stage),
    '--normal-run', (Quote-Arg $NormalRunFull),
    '--forced-run', (Quote-Arg $ForcedRunFull),
    '--require-pass',
    '--write-json', (Quote-Arg $MatrixJsonFull),
    '--write-markdown', (Quote-Arg $MatrixMarkdownFull)
) -join ' '

$Plan.commands = [ordered]@{
    patch = $PatchCommand
    manifest = $ManifestCommand
    matrix = $MatrixCommand
}

if ($Json) {
    $Plan | ConvertTo-Json -Depth 6
} else {
    Write-Host 'HD map smoke candidate plan'
    Write-Host "Dry run: $(-not [bool]$Execute)"
    Write-Host "Base exe: $InputExeFull"
    Write-Host "Base SHA status: $BaseShaStatus"
    if (-not $InputExists) {
        Write-Warning "Base executable is not accessible from this shell; -Execute will fail until it exists."
    }
    Write-Host "Candidate: $CandidateFull"
    Write-Host "Patch manifest: $PatchManifestFull"
    Write-Host "Matrix JSON: $MatrixJsonFull"
    Write-Host "Matrix markdown: $MatrixMarkdownFull"
    Write-Host ''
    Write-Host 'Commands:'
    Write-Host $PatchCommand
    Write-Host $ManifestCommand
    Write-Host $MatrixCommand
}

if (-not $Execute) {
    exit 0
}

if (-not $InputExists) {
    throw "Input executable does not exist: $InputExeFull"
}
if (Test-Path -LiteralPath $CandidateFull) {
    throw "Candidate already exists: $CandidateFull"
}

New-Item -ItemType Directory -Force -Path $CandidateDirFull | Out-Null
& $PythonFull (Join-Path $RepoRoot 'patch_clash95_hd.py') --input $InputExeFull --output $CandidateFull --stage $Stage
& $PythonFull (Join-Path $RepoRoot 'tools\patch_stage_report.py') --exe $CandidateFull --stage $Stage --require-current-hd-map --write-json $PatchManifestFull
& $PythonFull (Join-Path $RepoRoot 'tools\hd_map_smoke_matrix.py') --patch-exe $CandidateFull --stage $Stage --normal-run $NormalRunFull --forced-run $ForcedRunFull --require-pass --write-json $MatrixJsonFull --write-markdown $MatrixMarkdownFull
