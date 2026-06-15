param(
    [string]$SourceSave = 'C:\Clash\save\5.dat',
    [string]$SourceWorkDir = 'C:\Clash',
    [string]$FixtureRoot = 'C:\ClashTests\right-bottom-slot5-as-slot0-fixture',
    [ValidateRange(0,9)]
    [int]$TargetLoadSlot = 0,
    [switch]$SeedWorkDir,
    [switch]$Execute,
    [switch]$AllowRepoFixtureRoot,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'

$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$ClashSaveRoot = 'C:\Clash\save'

function Resolve-PlanPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $Path))
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

function Quote-Arg {
    param([Parameter(Mandatory = $true)][string]$Value)
    return "'" + ($Value -replace "'", "''") + "'"
}

$SourceSaveFull = Resolve-PlanPath $SourceSave
$SourceWorkDirFull = Resolve-PlanPath $SourceWorkDir
$FixtureRootFull = Resolve-PlanPath $FixtureRoot
$FixtureSaveDirFull = Join-Path $FixtureRootFull 'save'
$FixtureSaveFull = Join-Path $FixtureSaveDirFull ('{0}.dat' -f $TargetLoadSlot)
$ClashSaveRootFull = Resolve-PlanPath $ClashSaveRoot

if ((Test-IsUnderPath $FixtureRootFull $RepoRoot) -and -not $AllowRepoFixtureRoot) {
    throw "Refusing fixture output inside repository by default: $FixtureRootFull. Use -AllowRepoFixtureRoot only for a deliberate local handoff."
}
if (Test-IsUnderPath $FixtureSaveFull $ClashSaveRootFull) {
    throw "Refusing to write fixture output into the live Clash save directory: $FixtureSaveFull"
}
if (Test-IsUnderPath $FixtureRootFull $SourceWorkDirFull) {
    throw "Refusing fixture output inside the source Clash workdir: $FixtureRootFull"
}
if ([System.IO.Path]::GetFullPath($FixtureSaveFull).Equals([System.IO.Path]::GetFullPath($SourceSaveFull), [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to overwrite source save: $SourceSaveFull"
}

$SourceExists = Test-Path -LiteralPath $SourceSaveFull -PathType Leaf
$SourceWorkDirExists = Test-Path -LiteralPath $SourceWorkDirFull -PathType Container
$SourceSha256 = $null
if ($SourceExists) {
    $SourceSha256 = (Get-FileHash -LiteralPath $SourceSaveFull -Algorithm SHA256).Hash.ToLowerInvariant()
}

$SeedExcludedDirs = @('save')
$SeedCommand = "Copy non-save children from $(Quote-Arg $SourceWorkDirFull) to $(Quote-Arg $FixtureRootFull)"
$CopyCommand = @(
    'Copy-Item',
    '-LiteralPath', (Quote-Arg $SourceSaveFull),
    '-Destination', (Quote-Arg $FixtureSaveFull)
) -join ' '

$Plan = [ordered]@{
    dry_run = -not [bool]$Execute
    proof_class = 'non_natural_isolated_fixture'
    promotion_ready = $false
    stable_stage_should_change = $false
    repo_root = $RepoRoot
    source_save = $SourceSaveFull
    source_exists = $SourceExists
    source_sha256 = $SourceSha256
    source_workdir = $SourceWorkDirFull
    source_workdir_exists = $SourceWorkDirExists
    seed_workdir = [bool]$SeedWorkDir
    seed_excluded_dirs = $SeedExcludedDirs
    seed_command = $SeedCommand
    fixture_root = $FixtureRootFull
    fixture_save = $FixtureSaveFull
    target_load_slot = $TargetLoadSlot
    must_not_mutate = @($ClashSaveRootFull, $RepoRoot)
    command = $CopyCommand
}

if ($Json) {
    $Plan | ConvertTo-Json -Depth 5
} else {
    Write-Host 'Right-bottom slot fixture plan'
    Write-Host "Dry run: $(-not [bool]$Execute)"
    Write-Host "Proof class: non_natural_isolated_fixture"
    Write-Host "Promotion ready: False"
    Write-Host "Seed workdir: $([bool]$SeedWorkDir)"
    Write-Host "Source workdir: $SourceWorkDirFull"
    Write-Host "Source workdir exists: $SourceWorkDirExists"
    Write-Host "Source save: $SourceSaveFull"
    Write-Host "Source exists: $SourceExists"
    Write-Host "Fixture save: $FixtureSaveFull"
    Write-Host "Target load slot: $TargetLoadSlot"
    Write-Host ''
    Write-Host 'Command:'
    if ($SeedWorkDir) {
        Write-Host $SeedCommand
    }
    Write-Host $CopyCommand
}

if (-not $Execute) {
    exit 0
}

if (-not $SourceExists) {
    throw "Source save does not exist: $SourceSaveFull"
}
if ($SeedWorkDir -and -not $SourceWorkDirExists) {
    throw "Source workdir does not exist: $SourceWorkDirFull"
}
if ($SeedWorkDir -and (Test-Path -LiteralPath $FixtureRootFull)) {
    throw "Fixture root already exists; refusing to seed over it: $FixtureRootFull"
}
if (Test-Path -LiteralPath $FixtureSaveFull) {
    throw "Fixture save already exists: $FixtureSaveFull"
}

if ($SeedWorkDir) {
    New-Item -ItemType Directory -Force -Path $FixtureRootFull | Out-Null
    Get-ChildItem -LiteralPath $SourceWorkDirFull -Force |
        Where-Object { $SeedExcludedDirs -notcontains $_.Name } |
        ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $FixtureRootFull -Recurse -Force
        }
}

New-Item -ItemType Directory -Force -Path $FixtureSaveDirFull | Out-Null
Copy-Item -LiteralPath $SourceSaveFull -Destination $FixtureSaveFull
