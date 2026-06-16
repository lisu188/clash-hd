param(
    [string]$InputExe = 'C:\Clash\clash95.exe',
    [string]$CandidateDir = 'C:\ClashTests\hd-soak',
    [string]$CandidateName = '',
    [string]$WorkDir = 'C:\Clash',
    [string]$Python = '',
    [string]$Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch',
    [ValidateSet('short2', 'short10', 'short30', 'custom')]
    [string]$Tier = 'short2',
    [int]$DurationSec = 0,
    [ValidateSet('menu-idle', 'map-idle', 'map-pan', 'custom')]
    [string]$Route = 'menu-idle',
    [string]$CustomPoints = '400,300',
    [int]$SampleIntervalSec = 15,
    [ValidateSet('sendinput', 'postmessage', 'both', 'none')]
    [string]$IntroSkipClickMode = 'postmessage',
    [int]$IntroSkipClicks = 8,
    [int]$SkipPulses = 4,
    [int]$RouteStepWaitMs = 1400,
    [int]$MoveWindowX = 80,
    [int]$MoveWindowY = 80,
    [ValidateSet('setcursor', 'sendinput-absolute', 'sendinput-relative', 'sendinput-client-delta', 'auto', 'none')]
    [string]$MoveMode = 'auto',
    [ValidateSet('sendinput', 'postmessage', 'both')]
    [string]$ClickMode = 'sendinput',
    [int]$ClickHoldMs = 250,
    [int]$ClickRepeat = 1,
    [int]$MaxInputDriftPx = 1,
    [double]$MinNonblackPercent = 10.0,
    [int]$MinUniqueSampleColors = 8,
    [int]$MaxArtifactMB = 250,
    [int]$MaxWorkingSetGrowthMB = 64,
    [int]$MaxPrivateMemoryGrowthMB = 64,
    [int]$MaxHandleGrowth = 128,
    [string]$OutputRoot = 'C:\ClashCaptures\hd-soak',
    [string]$ReportJson = 'captures\current\hd-soak-short-current.json',
    [string]$ReportMarkdown = 'captures\current\hd-soak-short-current.md',
    [switch]$Execute,
    [switch]$AllowVisibleRuntime,
    [switch]$AllowRepoCandidateDir,
    [switch]$ReuseCandidate,
    [switch]$SkipPatch,
    [switch]$KeepOpen,
    [switch]$RequirePass,
    [switch]$Json
)

$ErrorActionPreference = 'Stop'

$StableStage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch'
$ExpectedBaseSha256 = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

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

function Get-TierDurationSec {
    param([string]$Name, [int]$CustomDuration)
    switch ($Name) {
        'short2' { return 120 }
        'short10' { return 600 }
        'short30' { return 1800 }
        'custom' {
            if ($CustomDuration -le 0) {
                throw 'Use -DurationSec with -Tier custom.'
            }
            return $CustomDuration
        }
        default { throw "Unknown tier: $Name" }
    }
}

function Get-RouteSteps {
    param([string]$RouteName, [string]$Points)
    switch ($RouteName) {
        'menu-idle' {
            return @()
        }
        'map-idle' {
            return @(
                [pscustomobject]@{ Name = 'load-button'; Points = '300,218'; Click = $true; WaitMs = $RouteStepWaitMs },
                [pscustomobject]@{ Name = 'load-slot0'; Points = '320,166'; Click = $true; WaitMs = $RouteStepWaitMs },
                [pscustomobject]@{ Name = 'confirm-load'; Points = '400,226'; Click = $true; WaitMs = [math]::Max($RouteStepWaitMs, 2200) }
            )
        }
        'map-pan' {
            return @(
                [pscustomobject]@{ Name = 'load-button'; Points = '300,218'; Click = $true; WaitMs = $RouteStepWaitMs },
                [pscustomobject]@{ Name = 'load-slot0'; Points = '320,166'; Click = $true; WaitMs = $RouteStepWaitMs },
                [pscustomobject]@{ Name = 'confirm-load'; Points = '400,226'; Click = $true; WaitMs = [math]::Max($RouteStepWaitMs, 2200) },
                [pscustomobject]@{ Name = 'pan-path'; Points = '400,300;680,300;680,520;120,520;120,120;400,300'; Click = $false; WaitMs = [math]::Max($RouteStepWaitMs, 2200) }
            )
        }
        'custom' {
            return @([pscustomobject]@{ Name = 'custom-points'; Points = $Points; Click = $true; WaitMs = [math]::Max($RouteStepWaitMs, 2200) })
        }
        default {
            throw "Unknown route: $RouteName"
        }
    }
}

function Invoke-MousePath {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$OutputJson,
        [string]$Points,
        [bool]$Click,
        [int]$SpacePulses = 0,
        [string]$MoveModeOverride = '',
        [string]$ClickModeOverride = '',
        [int]$ClickRepeatOverride = -1
    )

    $mouseTool = Join-Path $RepoRoot 'tools\mouse_path_probe.py'
    if (-not (Test-Path -LiteralPath $mouseTool -PathType Leaf)) {
        throw "Required mouse probe was not found: $mouseTool"
    }
    $effectiveMoveMode = if ($MoveModeOverride) { $MoveModeOverride } else { $MoveMode }
    $effectiveClickMode = if ($ClickModeOverride) { $ClickModeOverride } else { $ClickMode }
    $effectiveClickRepeat = if ($ClickRepeatOverride -ge 0) { $ClickRepeatOverride } else { $ClickRepeat }
    $args = @(
        $mouseTool,
        '--pid', "$($Process.Id)",
        '--workdir', $WorkDirFull,
        '--window-timeout', '12',
        '--settle-sec', '0.5',
        '--move-window', "$MoveWindowX", "$MoveWindowY",
        '--space-pulses', "$SpacePulses",
        '--space-interval-ms', '500',
        '--interval-ms', '300',
        '--move-mode', $effectiveMoveMode,
        '--points', $Points,
        '--json', $OutputJson
    )
    if ($Click) {
        $args += @('--click', '--click-mode', $effectiveClickMode, '--click-hold-ms', "$ClickHoldMs", '--click-repeat', "$effectiveClickRepeat")
    }

    $probeLog = [System.IO.Path]::ChangeExtension($OutputJson, '.log')
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $probeOutput = & $PythonFull @args 2>&1
        $exitCode = $LASTEXITCODE
    } catch {
        $probeOutput = @($_.Exception.Message)
        $exitCode = 1
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $probeOutput | Set-Content -LiteralPath $probeLog -Encoding ASCII

    if (Test-Path -LiteralPath $OutputJson -PathType Leaf) {
        $result = Get-Content -LiteralPath $OutputJson -Raw | ConvertFrom-Json
        $result | Add-Member -NotePropertyName ProbeExitCode -NotePropertyValue $exitCode -Force
        $result | Add-Member -NotePropertyName ProbeLog -NotePropertyValue $probeLog -Force
        $result | Add-Member -NotePropertyName EffectiveMoveMode -NotePropertyValue $effectiveMoveMode -Force
        $result | Add-Member -NotePropertyName EffectiveClickMode -NotePropertyValue $effectiveClickMode -Force
        $result | Add-Member -NotePropertyName EffectiveClickRepeat -NotePropertyValue $effectiveClickRepeat -Force
        return $result
    }

    return [pscustomobject]@{
        path_verified = $false
        click_path_verified = $false
        ProbeExitCode = $exitCode
        ProbeLog = $probeLog
        ProbeError = "mouse_path_probe.py did not write JSON"
        EffectiveMoveMode = $effectiveMoveMode
        EffectiveClickMode = $effectiveClickMode
        EffectiveClickRepeat = $effectiveClickRepeat
    }
}

function Save-ClientFrame {
    param(
        [System.Diagnostics.Process]$Process,
        [string]$FramePath,
        [string]$FrameJson
    )

    $captureScript = Join-Path $RepoRoot 'scripts\capture\capture_clash_client_frame.ps1'
    if (-not (Test-Path -LiteralPath $captureScript -PathType Leaf)) {
        throw "Capture helper was not found: $captureScript"
    }

    $captureOutput = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $captureScript -AllowVisibleRuntime `
        -TargetProcessId $Process.Id `
        -Path $FramePath `
        -Json $FrameJson `
        -WindowTimeoutSec 8 2>&1
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "capture_clash_client_frame.ps1 failed with exit code $exitCode`: $captureOutput"
    }
    Get-Content -LiteralPath $FrameJson -Raw | ConvertFrom-Json
}

function Get-ProcessSnapshot {
    param([System.Diagnostics.Process]$Process)
    try {
        $Process.Refresh()
        [pscustomobject]@{
            Timestamp = (Get-Date).ToString('o')
            HasExited = [bool]$Process.HasExited
            ExitCode = if ($Process.HasExited) { $Process.ExitCode } else { $null }
            WorkingSet64 = if ($Process.HasExited) { $null } else { $Process.WorkingSet64 }
            PrivateMemorySize64 = if ($Process.HasExited) { $null } else { $Process.PrivateMemorySize64 }
            HandleCount = if ($Process.HasExited) { $null } else { $Process.HandleCount }
        }
    } catch {
        [pscustomobject]@{
            Timestamp = (Get-Date).ToString('o')
            HasExited = $true
            ExitCode = $null
            WorkingSet64 = $null
            PrivateMemorySize64 = $null
            HandleCount = $null
            Error = $_.Exception.Message
        }
    }
}

function Get-DirectorySizeBytes {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return 0
    }
    $size = 0L
    Get-ChildItem -LiteralPath $Path -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
        $size += $_.Length
    }
    return $size
}

function Select-NumberMin {
    param([object[]]$Values, [double]$Default = 0.0)
    $numbers = @($Values | Where-Object { $_ -ne $null } | ForEach-Object { [double]$_ })
    if (@($numbers).Count -eq 0) {
        return $Default
    }
    return [double](($numbers | Measure-Object -Minimum).Minimum)
}

function Select-NumberMax {
    param([object[]]$Values, [double]$Default = 0.0)
    $numbers = @($Values | Where-Object { $_ -ne $null } | ForEach-Object { [double]$_ })
    if (@($numbers).Count -eq 0) {
        return $Default
    }
    return [double](($numbers | Measure-Object -Maximum).Maximum)
}

function Convert-NullableInt {
    param([object]$Value)
    if ($null -eq $Value) {
        return $null
    }
    return [int]$Value
}

function Write-SoakMarkdown {
    param(
        [object]$Report,
        [string]$Path
    )

    $overallStatus = if ($Report.passed) { 'PASS' } else { 'FAIL' }
    function Format-NullableMetric {
        param([object]$Value)
        if ($null -eq $Value) {
            return 'n/a'
        }
        return "$Value"
    }
    $lines = @(
        '# HD Soak Short-Tier Report',
        '',
        "- Overall: $overallStatus",
        "- Generated: $($Report.generated_at)",
        "- Runtime policy: $($Report.runtime_policy)",
        "- Tier / route: $($Report.tier) / $($Report.route)",
        "- Duration seconds: $($Report.duration_sec)",
        "- Stage: $($Report.stage)",
        "- Candidate SHA-256: $($Report.candidate_sha256)",
        "- Output directory: $($Report.output_directory)",
        "- Frame samples: $($Report.frame_sample_count)",
        "- Unique frame hashes: $($Report.frame_hash_unique_count)",
        "- Frame stability class: $($Report.frame_stability_class)",
        "- Frame progress expected: $($Report.frame_progress_expected)",
        "- Nonblack min/max: $($Report.nonblack_percent_min) / $($Report.nonblack_percent_max)",
        "- Unique sampled colors min/max: $($Report.unique_sample_colors_min) / $($Report.unique_sample_colors_max)",
        "- Input max move drift px: $($Report.input_max_abs_error)",
        "- Input max sampled drift px: $($Report.input_max_sample_abs_error)",
        "- Input drift limit px: $($Report.max_input_drift_px)",
        "- Intro skip mode/repeat/pulses: $($Report.intro_skip.click_mode) / $($Report.intro_skip.click_repeat) / $($Report.intro_skip.space_pulses)",
        "- Intro skip proof class: $($Report.intro_skip.proof_class)",
        "- Working-set growth bytes: $(Format-NullableMetric $Report.working_set_growth_bytes)",
        "- Private-memory growth bytes: $(Format-NullableMetric $Report.private_memory_growth_bytes)",
        "- Handle growth: $(Format-NullableMetric $Report.handle_growth)",
        "- Artifact bytes: $($Report.artifact_bytes)",
        "- Unexpected exit: $($Report.process_exited_unexpectedly)",
        "- Clean stop: $($Report.clean_stop)",
        "- Route marker: $($Report.final_route_marker)",
        "- Input proof class: $($Report.input_proof_class)",
        "- Right-bottom promotion remains blocked: $($Report.right_bottom_promotion_blocked)",
        ''
    )
    if (@($Report.failures).Count -gt 0) {
        $lines += '## Failures'
        $lines += ''
        foreach ($failure in $Report.failures) {
            $lines += "- $failure"
        }
        $lines += ''
    }
    $lines += '## Frame Samples'
    $lines += ''
    foreach ($frame in @($Report.frame_samples)) {
        $lines += "- $($frame.Name): hash=$($frame.Hash) nonblack=$($frame.NonblackPercent) luma=$($frame.MeanLuma) colors=$($frame.UniqueSampleColors) mode=$($frame.CaptureMode)"
    }
    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    $lines | Set-Content -LiteralPath $Path -Encoding ASCII
}

$DurationResolvedSec = Get-TierDurationSec -Name $Tier -CustomDuration $DurationSec
$InputExeFull = Resolve-PlanPath $InputExe
$CandidateDirFull = Resolve-PlanPath $CandidateDir
$WorkDirFull = Resolve-PlanPath $WorkDir
$OutputRootFull = Resolve-PlanPath $OutputRoot
$ReportJsonFull = Resolve-PlanPath $ReportJson
$ReportMarkdownFull = Resolve-PlanPath $ReportMarkdown
$PythonFull = Find-Python $Python

if (-not $CandidateName) {
    $CandidateName = 'clash95_hd_soak_{0}.exe' -f (Get-Date -Format 'yyyyMMdd_HHmmss')
}
if ([System.IO.Path]::GetExtension($CandidateName) -ne '.exe') {
    throw "CandidateName must end with .exe: $CandidateName"
}
$CandidateFull = Resolve-PlanPath (Join-Path $CandidateDirFull $CandidateName)
$RouteSteps = @(Get-RouteSteps -RouteName $Route -Points $CustomPoints)

if ((Test-IsUnderPath $CandidateDirFull $RepoRoot) -and -not $AllowRepoCandidateDir) {
    throw "Refusing candidate output inside repository by default: $CandidateDirFull"
}

$inputExists = Test-Path -LiteralPath $InputExeFull -PathType Leaf
$inputSha256 = $null
$baseShaStatus = 'missing'
if ($inputExists) {
    $inputSha256 = (Get-FileHash -LiteralPath $InputExeFull -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($inputSha256 -ne $ExpectedBaseSha256) {
        throw "Unexpected base SHA-256 for $InputExeFull. Expected $ExpectedBaseSha256 but found $inputSha256."
    }
    $baseShaStatus = 'ok'
}

$patchCommand = @(
    '&', (Quote-Arg $PythonFull), (Quote-Arg (Join-Path $RepoRoot 'patch_clash95_hd.py')),
    '--input', (Quote-Arg $InputExeFull),
    '--output', (Quote-Arg $CandidateFull),
    '--stage', (Quote-Arg $Stage)
) -join ' '
$executeCommand = @(
    'powershell.exe -NoProfile -ExecutionPolicy Bypass -File',
    (Quote-Arg (Join-Path $RepoRoot 'scripts\smoke\run_hd_soak.ps1')),
    '-InputExe', (Quote-Arg $InputExeFull),
    '-WorkDir', (Quote-Arg $WorkDirFull),
    '-Stage', (Quote-Arg $Stage),
    '-Tier', (Quote-Arg $Tier),
    '-Route', (Quote-Arg $Route),
    '-CandidateDir', (Quote-Arg $CandidateDirFull),
    '-CandidateName', (Quote-Arg $CandidateName),
    '-OutputRoot', (Quote-Arg $OutputRootFull),
    '-ReportJson', (Quote-Arg $ReportJsonFull),
    '-ReportMarkdown', (Quote-Arg $ReportMarkdownFull),
    '-IntroSkipClickMode', (Quote-Arg $IntroSkipClickMode),
    '-IntroSkipClicks', (Quote-Arg ([string]$IntroSkipClicks)),
    '-SkipPulses', (Quote-Arg ([string]$SkipPulses)),
    '-MaxInputDriftPx', (Quote-Arg ([string]$MaxInputDriftPx)),
    '-Execute',
    '-AllowVisibleRuntime',
    '-RequirePass',
    '-Json'
) -join ' '

$plan = [ordered]@{
    dry_run = -not [bool]$Execute
    runtime_policy = 'opt-in visible runtime soak; use -Execute -AllowVisibleRuntime only after explicit user approval'
    repo_root = $RepoRoot
    input_exe = $InputExeFull
    input_exists = $inputExists
    expected_base_sha256 = $ExpectedBaseSha256
    input_sha256 = $inputSha256
    base_sha_status = $baseShaStatus
    stage = $Stage
    protected_stable_stage = $StableStage
    stable_stage_should_change = $false
    tier = $Tier
    duration_sec = $DurationResolvedSec
    route = $Route
    route_steps = $RouteSteps
    sample_interval_sec = $SampleIntervalSec
    candidate_dir = $CandidateDirFull
    candidate_path = $CandidateFull
    workdir = $WorkDirFull
    output_root = $OutputRootFull
    report_json = $ReportJsonFull
    report_markdown = $ReportMarkdownFull
    growth_limits = [ordered]@{
        max_working_set_growth_mb = $MaxWorkingSetGrowthMB
        max_private_memory_growth_mb = $MaxPrivateMemoryGrowthMB
        max_handle_growth = $MaxHandleGrowth
        max_artifact_mb = $MaxArtifactMB
    }
    input_limits = [ordered]@{
        max_input_drift_px = $MaxInputDriftPx
    }
    intro_skip = [ordered]@{
        click_mode = $IntroSkipClickMode
        click_repeat = $IntroSkipClicks
        space_pulses = $SkipPulses
        proof_class = 'intro_skip_harness_prep_not_manual_directinput_release_proof'
    }
    raw_artifacts_policy = 'raw PNG frames and per-step logs stay outside the repository by default'
    right_bottom_promotion_blocked = $true
    commands = [ordered]@{
        patch = $patchCommand
        execute = $executeCommand
    }
}

if (-not $Execute) {
    if ($Json) {
        $plan | ConvertTo-Json -Depth 8
    } else {
        Write-Host 'HD soak plan'
        Write-Host "Dry run: True"
        Write-Host "Runtime policy: $($plan.runtime_policy)"
        Write-Host "Stage: $Stage"
        Write-Host "Tier / route: $Tier / $Route"
        Write-Host "Duration seconds: $DurationResolvedSec"
        Write-Host "Candidate: $CandidateFull"
        Write-Host "Output root: $OutputRootFull"
        Write-Host "Report JSON: $ReportJsonFull"
        Write-Host "Report markdown: $ReportMarkdownFull"
        Write-Host ''
        Write-Host 'Patch command:'
        Write-Host $patchCommand
        Write-Host ''
        Write-Host 'Execute command:'
        Write-Host $executeCommand
    }
    exit 0
}

if (-not $AllowVisibleRuntime) {
    throw 'Soak execution launches and captures a visible Clash95 runtime. Re-run with -AllowVisibleRuntime only after explicit user approval.'
}
if (-not $inputExists) {
    throw "Input executable does not exist: $InputExeFull"
}
if (-not (Test-Path -LiteralPath $WorkDirFull -PathType Container)) {
    throw "Working directory does not exist: $WorkDirFull"
}
if ($SampleIntervalSec -le 0) {
    throw 'SampleIntervalSec must be positive.'
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$safeRoute = $Route -replace '[^0-9A-Za-z_.-]', '-'
$outDir = Join-Path $OutputRootFull "hd-soak-$stamp-$Tier-$safeRoute"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$process = $null
$scriptError = $null
$frameSamples = @()
$processSamples = @()
$routeResults = @()
$captureErrors = @()
$cleanStop = $false
$candidateSha256 = $null
$patchStageReport = Join-Path $outDir 'patch-stage.json'

try {
    if (-not $SkipPatch) {
        New-Item -ItemType Directory -Force -Path $CandidateDirFull | Out-Null
        if ((Test-Path -LiteralPath $CandidateFull -PathType Leaf) -and -not $ReuseCandidate) {
            throw "Candidate already exists: $CandidateFull"
        }
        if (-not (Test-Path -LiteralPath $CandidateFull -PathType Leaf)) {
            & $PythonFull (Join-Path $RepoRoot 'patch_clash95_hd.py') --input $InputExeFull --output $CandidateFull --stage $Stage
            if ($LASTEXITCODE -ne 0) {
                throw "patch_clash95_hd.py failed with exit code $LASTEXITCODE"
            }
        }
    } elseif (-not (Test-Path -LiteralPath $CandidateFull -PathType Leaf)) {
        throw "SkipPatch was set but candidate does not exist: $CandidateFull"
    }

    $candidateSha256 = (Get-FileHash -LiteralPath $CandidateFull -Algorithm SHA256).Hash
    $patchArgs = @(
        (Join-Path $RepoRoot 'tools\patch_stage_report.py'),
        '--exe', $CandidateFull,
        '--stage', $Stage,
        '--write-json', $patchStageReport
    )
    if ($Stage -eq $StableStage) {
        $patchArgs += '--require-current-hd-map'
    }
    & $PythonFull @patchArgs
    if ($LASTEXITCODE -ne 0) {
        throw "patch_stage_report.py failed with exit code $LASTEXITCODE"
    }

    $process = Start-Process -FilePath $CandidateFull -WorkingDirectory $WorkDirFull -PassThru
    Start-Sleep -Milliseconds 800

    $introJson = Join-Path $outDir 'intro-skip.json'
    $introClick = ($IntroSkipClickMode -ne 'none') -and ($IntroSkipClicks -gt 0)
    $introClickRepeat = if ($introClick) { $IntroSkipClicks } else { 0 }
    $introResult = Invoke-MousePath -Process $process -OutputJson $introJson -Points '400,300' -Click $introClick -SpacePulses $SkipPulses -ClickModeOverride $IntroSkipClickMode -ClickRepeatOverride $introClickRepeat
    $routeResults += [pscustomobject]@{
        Name = 'intro-skip'
        Points = '400,300'
        Click = $introClick
        PathVerified = [bool]$introResult.path_verified
        ClickPathVerified = [bool]$introResult.click_path_verified
        MaxAbsError = Convert-NullableInt $introResult.max_abs_error
        MaxSampleAbsError = Convert-NullableInt $introResult.max_sample_abs_error
        ClickEventCount = Convert-NullableInt $introResult.click_event_count
        MoveMode = $introResult.EffectiveMoveMode
        ClickMode = $introResult.EffectiveClickMode
        ClickRepeat = $introResult.EffectiveClickRepeat
        SpacePulses = $SkipPulses
        InputProofClass = 'intro_skip_harness_prep_not_manual_directinput_release_proof'
        ProbeExitCode = $introResult.ProbeExitCode
        Json = $introJson
        Log = $introResult.ProbeLog
    }
    Start-Sleep -Seconds 2

    foreach ($step in $RouteSteps) {
        if ($process.HasExited) {
            break
        }
        $safeStepName = $step.Name -replace '[^0-9A-Za-z_.-]', '-'
        $stepJson = Join-Path $outDir ("route-{0}.json" -f $safeStepName)
        $stepResult = Invoke-MousePath -Process $process -OutputJson $stepJson -Points $step.Points -Click ([bool]$step.Click)
        $routeResults += [pscustomobject]@{
            Name = $step.Name
            Points = $step.Points
            Click = [bool]$step.Click
            PathVerified = [bool]$stepResult.path_verified
            ClickPathVerified = [bool]$stepResult.click_path_verified
            MaxAbsError = Convert-NullableInt $stepResult.max_abs_error
            MaxSampleAbsError = Convert-NullableInt $stepResult.max_sample_abs_error
            ClickEventCount = Convert-NullableInt $stepResult.click_event_count
            MoveMode = $stepResult.EffectiveMoveMode
            ClickMode = $stepResult.EffectiveClickMode
            ClickRepeat = $stepResult.EffectiveClickRepeat
            SpacePulses = 0
            InputProofClass = 'automated_visible_runtime_diagnostic_not_manual_directinput_release_proof'
            ProbeExitCode = $stepResult.ProbeExitCode
            Json = $stepJson
            Log = $stepResult.ProbeLog
        }
        Start-Sleep -Milliseconds ([int]$step.WaitMs)
    }

    $deadline = (Get-Date).AddSeconds($DurationResolvedSec)
    $sampleIndex = 0
    do {
        $processSamples += Get-ProcessSnapshot -Process $process
        if ($process.HasExited) {
            break
        }

        $frameName = 'frame-{0:D4}' -f $sampleIndex
        $framePath = Join-Path $outDir "$frameName.png"
        $frameJson = Join-Path $outDir "$frameName.json"
        try {
            $frame = Save-ClientFrame -Process $process -FramePath $framePath -FrameJson $frameJson
            $frame | Add-Member -NotePropertyName Name -NotePropertyValue $frameName -Force
            $frame | Add-Member -NotePropertyName Timestamp -NotePropertyValue (Get-Date).ToString('o') -Force
            $frameSamples += $frame
        } catch {
            $captureErrors += [pscustomobject]@{
                Timestamp = (Get-Date).ToString('o')
                Frame = $frameName
                Error = $_.Exception.Message
            }
        }

        $sampleIndex++
        $remaining = [int][math]::Ceiling(($deadline - (Get-Date)).TotalSeconds)
        if ($remaining -le 0) {
            break
        }
        Start-Sleep -Seconds ([math]::Min($SampleIntervalSec, $remaining))
    } while ((Get-Date) -lt $deadline)

    $processSamples += Get-ProcessSnapshot -Process $process
} catch {
    $scriptError = $_
} finally {
    if ($process -and -not $process.HasExited -and -not $KeepOpen) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        $cleanStop = $true
    }
}

$artifactBytes = Get-DirectorySizeBytes -Path $outDir
$artifactLimitBytes = [int64]$MaxArtifactMB * 1024L * 1024L
$frameHashes = @($frameSamples | ForEach-Object { $_.Hash } | Where-Object { $_ })
$uniqueFrameHashes = @($frameHashes | Sort-Object -Unique)
$frameProgressExpected = ($Route -eq 'map-pan')
$frameStabilityClass = if (@($frameSamples).Count -eq 0) {
    'no_frames'
} elseif (@($uniqueFrameHashes).Count -le 1) {
    'stable_idle'
} else {
    'progressing'
}
$nonblackValues = @($frameSamples | ForEach-Object { $_.NonblackPercent })
$lumaValues = @($frameSamples | ForEach-Object { $_.MeanLuma })
$uniqueColorValues = @($frameSamples | ForEach-Object { $_.UniqueSampleColors })
$widthValues = @($frameSamples | ForEach-Object { $_.Width })
$heightValues = @($frameSamples | ForEach-Object { $_.Height })
$workingSetValues = @($processSamples | ForEach-Object { $_.WorkingSet64 } | Where-Object { $_ -ne $null })
$privateMemoryValues = @($processSamples | ForEach-Object { $_.PrivateMemorySize64 } | Where-Object { $_ -ne $null })
$handleValues = @($processSamples | ForEach-Object { $_.HandleCount } | Where-Object { $_ -ne $null })
$workingSetGrowthBytes = if (@($workingSetValues).Count -ge 2) { [int64](@($workingSetValues)[-1] - @($workingSetValues)[0]) } else { $null }
$privateMemoryGrowthBytes = if (@($privateMemoryValues).Count -ge 2) { [int64](@($privateMemoryValues)[-1] - @($privateMemoryValues)[0]) } else { $null }
$handleGrowth = if (@($handleValues).Count -ge 2) { [int](@($handleValues)[-1] - @($handleValues)[0]) } else { $null }
$workingSetLimitBytes = [int64]$MaxWorkingSetGrowthMB * 1024L * 1024L
$privateMemoryLimitBytes = [int64]$MaxPrivateMemoryGrowthMB * 1024L * 1024L
$inputMaxAbsValues = @($routeResults | ForEach-Object { $_.MaxAbsError } | Where-Object { $_ -ne $null })
$inputMaxSampleAbsValues = @($routeResults | ForEach-Object { $_.MaxSampleAbsError } | Where-Object { $_ -ne $null })
$inputMaxAbsError = if (@($inputMaxAbsValues).Count -gt 0) { [int](Select-NumberMax -Values $inputMaxAbsValues) } else { $null }
$inputMaxSampleAbsError = if (@($inputMaxSampleAbsValues).Count -gt 0) { [int](Select-NumberMax -Values $inputMaxSampleAbsValues) } else { $null }
$unexpectedExit = $false
$exitCode = $null
if ($process) {
    try {
        $process.Refresh()
        $unexpectedExit = [bool]$process.HasExited -and -not $cleanStop
        if ($process.HasExited) {
            $exitCode = $process.ExitCode
        }
    } catch {
        $unexpectedExit = $true
    }
}

$routeFailures = @($routeResults | Where-Object {
    (-not $_.PathVerified) -or ($_.Click -and -not $_.ClickPathVerified) -or ($_.ProbeExitCode -notin @(0, 2))
})
$routeDriftFailures = @($routeResults | Where-Object {
    ($null -eq $_.MaxAbsError) -or
    ([int]$_.MaxAbsError -gt $MaxInputDriftPx) -or
    ($_.Click -and (($null -eq $_.MaxSampleAbsError) -or ([int]$_.MaxSampleAbsError -gt $MaxInputDriftPx)))
})
$failures = @()
if ($scriptError) { $failures += $scriptError.Exception.Message }
if ($unexpectedExit) { $failures += "process exited unexpectedly with code $exitCode" }
if (@($captureErrors).Count -gt 0) { $failures += "capture errors: $(@($captureErrors).Count)" }
if (@($frameSamples).Count -lt 2) { $failures += "expected at least 2 frame samples" }
if ($frameProgressExpected -and @($uniqueFrameHashes).Count -lt 2) {
    $failures += 'frame progression required for map-pan route'
}
if (@($processSamples).Count -lt 2) { $failures += "expected at least 2 process samples" }
if (@($widthValues | Where-Object { $_ -ne 800 }).Count -gt 0 -or @($heightValues | Where-Object { $_ -ne 600 }).Count -gt 0) {
    $failures += 'one or more frame samples were not 800x600'
}
if ((Select-NumberMin -Values $nonblackValues) -lt $MinNonblackPercent) {
    $failures += "nonblack percent dropped below $MinNonblackPercent"
}
if ((Select-NumberMin -Values $uniqueColorValues) -lt $MinUniqueSampleColors) {
    $failures += "unique sampled colors dropped below $MinUniqueSampleColors"
}
if (@($routeFailures).Count -gt 0) {
    $failures += "route/input probe failures: $(@($routeFailures).Count)"
}
if (@($routeDriftFailures).Count -gt 0) {
    $failures += "input drift exceeded ${MaxInputDriftPx}px or metric missing: $(@($routeDriftFailures).Count)"
}
if ($null -eq $workingSetGrowthBytes) {
    $failures += 'working-set growth metric unavailable'
} elseif ($workingSetGrowthBytes -gt $workingSetLimitBytes) {
    $failures += "working-set growth exceeded ${MaxWorkingSetGrowthMB}MB"
}
if ($null -eq $privateMemoryGrowthBytes) {
    $failures += 'private-memory growth metric unavailable'
} elseif ($privateMemoryGrowthBytes -gt $privateMemoryLimitBytes) {
    $failures += "private-memory growth exceeded ${MaxPrivateMemoryGrowthMB}MB"
}
if ($null -eq $handleGrowth) {
    $failures += 'handle growth metric unavailable'
} elseif ($handleGrowth -gt $MaxHandleGrowth) {
    $failures += "handle growth exceeded $MaxHandleGrowth"
}
if ($artifactBytes -gt $artifactLimitBytes) {
    $failures += "artifact size exceeded ${MaxArtifactMB}MB"
}

$report = [ordered]@{
    generated_at = (Get-Date).ToString('o')
    runtime_policy = 'opt-in visible runtime soak; raw frames stay outside the repository by default'
    executed = $true
    passed = (@($failures).Count -eq 0)
    failures = @($failures)
    tier = $Tier
    duration_sec = $DurationResolvedSec
    sample_interval_sec = $SampleIntervalSec
    route = $Route
    final_route_marker = if (@($routeResults).Count -gt 0) { @($routeResults)[-1].Name } else { $Route }
    stage = $Stage
    protected_stable_stage = $StableStage
    stable_stage_should_change = $false
    input_exe = $InputExeFull
    input_sha256 = $inputSha256
    candidate = $CandidateFull
    candidate_sha256 = $candidateSha256
    patch_stage_report = $patchStageReport
    workdir = $WorkDirFull
    output_directory = $outDir
    report_json = $ReportJsonFull
    report_markdown = $ReportMarkdownFull
    frame_sample_count = @($frameSamples).Count
    frame_hash_unique_count = @($uniqueFrameHashes).Count
    frame_progress_expected = $frameProgressExpected
    frame_stability_class = $frameStabilityClass
    nonblack_percent_min = Select-NumberMin -Values $nonblackValues
    nonblack_percent_max = Select-NumberMax -Values $nonblackValues
    mean_luma_min = Select-NumberMin -Values $lumaValues
    mean_luma_max = Select-NumberMax -Values $lumaValues
    unique_sample_colors_min = [int](Select-NumberMin -Values $uniqueColorValues)
    unique_sample_colors_max = [int](Select-NumberMax -Values $uniqueColorValues)
    input_max_abs_error = $inputMaxAbsError
    input_max_sample_abs_error = $inputMaxSampleAbsError
    max_input_drift_px = $MaxInputDriftPx
    intro_skip = [ordered]@{
        click_mode = $IntroSkipClickMode
        click_repeat = $IntroSkipClicks
        space_pulses = $SkipPulses
        proof_class = 'intro_skip_harness_prep_not_manual_directinput_release_proof'
    }
    process_sample_count = @($processSamples).Count
    working_set_growth_bytes = $workingSetGrowthBytes
    private_memory_growth_bytes = $privateMemoryGrowthBytes
    handle_growth = $handleGrowth
    max_working_set_growth_mb = $MaxWorkingSetGrowthMB
    max_private_memory_growth_mb = $MaxPrivateMemoryGrowthMB
    max_handle_growth = $MaxHandleGrowth
    working_set_growth_limit_bytes = $workingSetLimitBytes
    private_memory_growth_limit_bytes = $privateMemoryLimitBytes
    artifact_bytes = $artifactBytes
    process_exited_unexpectedly = $unexpectedExit
    exit_code = $exitCode
    clean_stop = $cleanStop
    keep_open = [bool]$KeepOpen
    input_proof_class = 'automated_visible_runtime_diagnostic_not_manual_directinput_release_proof'
    right_bottom_promotion_blocked = $true
    route_results = @($routeResults)
    process_samples = @($processSamples)
    frame_samples = @($frameSamples)
    capture_errors = @($captureErrors)
}

$reportDir = Split-Path -Parent $ReportJsonFull
if ($reportDir -and -not (Test-Path -LiteralPath $reportDir)) {
    New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
}
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $ReportJsonFull -Encoding ASCII
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $outDir 'report.json') -Encoding ASCII
Write-SoakMarkdown -Report ([pscustomobject]$report) -Path $ReportMarkdownFull
Write-SoakMarkdown -Report ([pscustomobject]$report) -Path (Join-Path $outDir 'report.md')

if ($Json) {
    $report | ConvertTo-Json -Depth 10
} else {
    [pscustomobject]$report | Format-List
}

if ($RequirePass -and -not $report.passed) {
    exit 1
}
