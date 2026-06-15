param(
    [string]$InputExe = 'C:\Clash\clash95.exe',
    [string]$WorkDir = 'C:\Clash',
    [string]$Cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe',
    [string]$Python = 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [string]$Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch',
    [string]$CandidateDir = 'C:\ClashTests\cdb-right-bottom-ui',
    [int]$RunSeconds = 150,
    [switch]$ForceVisibleEdges,
    [switch]$FastForwardStartAnims,
    [switch]$AllowVisibleDesktop,
    [switch]$AllowDescriptorOnly
)

$ErrorActionPreference = 'Stop'
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

function Get-LatestRun {
    param([DateTime]$After)
    Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'captures\archive') -Directory -Filter 'cdb-surface-dump-*' |
        Where-Object { $_.LastWriteTime -ge $After.AddSeconds(-2) } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Count-Markers {
    param(
        [string]$LogPath,
        [string[]]$Markers
    )
    $text = if (Test-Path -LiteralPath $LogPath) { Get-Content -LiteralPath $LogPath -Raw } else { '' }
    $counts = [ordered]@{}
    foreach ($marker in $Markers) {
        $counts[$marker] = ([regex]::Matches($text, [regex]::Escape($marker))).Count
    }
    [pscustomobject]$counts
}

$surfaceRunner = Join-Path $RepoRoot 'scripts\cdb\run_cdb_surface_dump.ps1'
$extraProbe = Join-Path $RepoRoot 'probes\cdb\ui\clash95_right_bottom_ui_extra.cdb'
foreach ($path in @($surfaceRunner, $extraProbe, $InputExe, $WorkDir, $Cdb, $Python)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required path was not found: $path"
    }
}

if (-not (Test-Path -LiteralPath $CandidateDir)) {
    New-Item -ItemType Directory -Path $CandidateDir -Force | Out-Null
}

$start = Get-Date
$args = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $surfaceRunner,
    '-InputExe', $InputExe,
    '-WorkDir', $WorkDir,
    '-Cdb', $Cdb,
    '-Python', $Python,
    '-Stage', $Stage,
    '-CandidateDir', $CandidateDir,
    '-RunSeconds', [string]$RunSeconds,
    '-UseDdrawProxy',
    '-RequireGameplay',
    '-ExtraProbeTemplate', $extraProbe
)
if ($ForceVisibleEdges) {
    $args += '-ForceVisibleEdges'
}
if ($FastForwardStartAnims) {
    $args += '-FastForwardStartAnims'
}
else {
    $args += '-NoSkipStartAnims'
}
if ($AllowVisibleDesktop) {
    $args += '-AllowVisibleDesktop'
}

& powershell.exe @args
$surfaceExit = $LASTEXITCODE
if ($surfaceExit -ne 0) {
    throw "scripts\cdb\run_cdb_surface_dump.ps1 failed with exit code $surfaceExit"
}

$run = Get-LatestRun -After $start
if (-not $run) {
    throw 'Could not locate the new cdb-surface-dump run folder.'
}

$summaryJson = Join-Path $run.FullName 'summary.json'
if (-not (Test-Path -LiteralPath $summaryJson)) {
    throw "Surface dump summary was not found: $summaryJson"
}
$summary = Get-Content -LiteralPath $summaryJson -Raw | ConvertFrom-Json
$logPath = if ($summary.Log) { [string]$summary.Log } else { Join-Path $run.FullName 'cdb-surface-dump.log' }
$markers = @(
    'RBUI_PANEL_DRAW',
    'RBUI_GRID_DRAW',
    'RBUI_STATUS_DRAW',
    'RBUI_ACTION_BOX',
    'RBUI_GRID_HIT_ENTRY',
    'RBUI_GRID_HIT_OK',
    'RBUI_GRID_HIT_FAIL',
    'RBUI_CLICK_DISPATCH',
    'RBUI_DESC_SWITCH',
    'RBUI_VIEWPORT_SWITCH',
    'SURFDUMP_PLAYGAME',
    'SURFDUMP_READY'
)
$counts = Count-Markers -LogPath $logPath -Markers $markers
$rbuiSeen = $false
foreach ($property in $counts.PSObject.Properties) {
    if ($property.Name -like 'RBUI_*' -and [int]$property.Value -gt 0) {
        $rbuiSeen = $true
    }
}
$ownerActionMarkers = @(
    'RBUI_PANEL_DRAW',
    'RBUI_GRID_DRAW',
    'RBUI_STATUS_DRAW',
    'RBUI_ACTION_BOX',
    'RBUI_GRID_HIT_ENTRY',
    'RBUI_GRID_HIT_OK',
    'RBUI_GRID_HIT_FAIL',
    'RBUI_CLICK_DISPATCH'
)
$ownerActionRowsSeen = $false
foreach ($marker in $ownerActionMarkers) {
    if ([int]$counts.$marker -gt 0) {
        $ownerActionRowsSeen = $true
    }
}
$descriptorOrViewportSeen = ([int]$counts.RBUI_DESC_SWITCH -gt 0 -or [int]$counts.RBUI_VIEWPORT_SWITCH -gt 0)
$requiresOwnerActionRows = -not [bool]$AllowDescriptorOnly

$rbuiSummary = [pscustomobject]@{
    Passed = ([bool]$summary.Passed -and $rbuiSeen -and ($ownerActionRowsSeen -or $AllowDescriptorOnly))
    SurfaceDumpPassed = [bool]$summary.Passed
    RbuiMarkersSeen = $rbuiSeen
    DescriptorOrViewportSeen = $descriptorOrViewportSeen
    OwnerActionRowsSeen = $ownerActionRowsSeen
    RequiresOwnerActionRows = $requiresOwnerActionRows
    AllowDescriptorOnly = [bool]$AllowDescriptorOnly
    MarkerCounts = $counts
    RunDir = $run.FullName
    Log = $logPath
    PngPath = $summary.PngPath
    SummaryJson = $summaryJson
    Stage = $Stage
    CandidatePath = $summary.CandidatePath
    CandidateSha256 = $summary.CandidateSha256
    ExtraProbeTemplate = $extraProbe
    ForceVisibleEdges = [bool]$ForceVisibleEdges
}
$rbuiSummaryPath = Join-Path $run.FullName 'right-bottom-ui-summary.json'
$rbuiSummary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $rbuiSummaryPath -Encoding ASCII

$countText = @($counts.PSObject.Properties | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join ', '
$rbuiTextPath = Join-Path $run.FullName 'right-bottom-ui-summary.txt'
@(
    "passed=$($rbuiSummary.Passed)"
    "surface_dump_passed=$($rbuiSummary.SurfaceDumpPassed)"
    "rbui_markers_seen=$rbuiSeen"
    "descriptor_or_viewport_seen=$descriptorOrViewportSeen"
    "owner_action_rows_seen=$ownerActionRowsSeen"
    "requires_owner_action_rows=$requiresOwnerActionRows"
    "allow_descriptor_only=$([bool]$AllowDescriptorOnly)"
    "markers=$countText"
    "run_dir=$($run.FullName)"
    "png=$($summary.PngPath)"
    "log=$logPath"
) | Set-Content -LiteralPath $rbuiTextPath -Encoding ASCII

$runSummary = Join-Path $run.FullName 'RUN-SUMMARY.md'
if (Test-Path -LiteralPath $runSummary) {
    Add-Content -LiteralPath $runSummary -Encoding ASCII -Value @(
        ''
        '## Right-Bottom UI Probe'
        ''
        "- Passed: $($rbuiSummary.Passed)"
        "- RBUI markers seen: $rbuiSeen"
        "- Descriptor or viewport rows seen: $descriptorOrViewportSeen"
        "- Owner/action rows seen: $ownerActionRowsSeen"
        "- Requires owner/action rows: $requiresOwnerActionRows"
        "- Marker counts: $countText"
        "- Summary: $rbuiSummaryPath"
    )
}

if (-not $rbuiSummary.Passed) {
    if (-not $rbuiSeen) {
        throw "Right-bottom UI CDB probe did not see RBUI markers. See $rbuiSummaryPath"
    }
    if ($requiresOwnerActionRows -and -not $ownerActionRowsSeen) {
        throw "Right-bottom UI CDB probe did not see owner/action rows. See $rbuiSummaryPath"
    }
    throw "Right-bottom UI CDB probe failed. See $rbuiSummaryPath"
}

Write-Host "CDB right-bottom UI probe passed: $($run.FullName)"
Write-Host "PNG: $($summary.PngPath)"
Write-Host "Summary: $rbuiSummaryPath"
