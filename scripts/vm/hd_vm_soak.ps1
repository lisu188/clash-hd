# QEMU-Win98 guest soak scaffold for the HD mod.
#
# This is the GUEST analogue of scripts/smoke/run_hd_soak.ps1. It boots the
# headless Win98 guest, drives it to the HD (800x600) map, then samples QMP
# screendump frames and query-status liveness on a fixed interval for the soak
# duration, and writes a GUEST-LABELLED soak report in the exact schema
# tools/hd_soak_report.py:evaluate_guest_report() grades.
#
# HONESTY: the report is stamped environment=guest_win98_qemu /
# evidence_class=approved_guest_win98_directdraw so it can never be mistaken for
# a host soak. Host-process telemetry (working set / private bytes / handle
# growth, exit_code, clean_stop) is NOT obtainable from inside a headless guest,
# so every such field is written as the string "not_applicable_guest" -- never a
# faked number and never dropped. Liveness is proven by QMP query-status plus
# frame progression, and the 800x600 frame size IS the HD proof.
#
# SAFETY: dry-run by default. Without -AllowGuestRuntime it PLANS only and boots
# nothing; the plan report is written executed=false so the grader treats it as a
# non-run. A real run requires -AllowGuestRuntime. QMP port 4445 ONLY (4444 is
# the disassembly rig and is refused). Never touches C:\Clash or C:\clash95-vm.
#
#   hd_vm_soak.ps1 -Candidate C:\ClashTests\hd-soak\clash95_hd_stable.exe -Tier short2 -Route map-idle
#   hd_vm_soak.ps1 -Candidate ... -Tier short10 -Route map-pan -AllowGuestRuntime
param(
  [Parameter(Mandatory = $true)]
  [string]$Candidate,
  [string[]]$SaveFiles = @(),
  [string]$ApprovalRecord = '',
  [string]$Vm = 'C:\clash-hd-vm',
  [int]$Port = 4445,
  [ValidateSet('short2', 'short10', 'short30', 'custom')]
  [string]$Tier = 'short2',
  [int]$DurationSec = 0,
  [ValidateSet('menu-idle', 'map-idle', 'map-pan', 'custom')]
  [string]$Route = 'map-idle',
  [int]$SampleIntervalSec = 15,
  [double]$MinNonblackPercent = 10.0,
  [int]$MinUniqueSampleColors = 8,
  [int]$MaxArtifactMB = 250,
  [int]$BootWaitSec = 300,
  [string]$OutputRoot = 'C:\ClashCaptures\hd-soak-guest',
  [string]$ReportJson = 'captures\current\hd-soak-guest-current.json',
  [switch]$GradeReport,
  [switch]$AllowGuestRuntime
)

$ErrorActionPreference = 'Stop'

if ($Port -eq 4444) {
  throw 'Port 4444 is the clash-disassembly rig. The HD guest lane uses 4445 only.'
}

$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$ToolsDir = Join-Path $RepoRoot 'tools'
$StableStage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch'
$ExpectedBaseSha256 = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
$GuestExePath = 'D:\CLASHHD.EXE'
$NotApplicableGuest = 'not_applicable_guest'

# Canonical HD engine-space load route (identical to scripts/smoke/run_hd_soak.ps1
# GetRouteSteps; reused, not re-derived) and pan path.
$LoadRoutePoints = @('302,211', '320,166', '400,226')
$PanPathPoints = @('400,300', '680,300', '680,520', '120,520', '120,120', '400,300')

$qmp = Join-Path $PSScriptRoot '..\..\..\clash-disassembly\tools\vm\qmp_win.ps1'
if (-not (Test-Path -LiteralPath $qmp)) {
  $qmp = 'C:\Users\andrz\git\clash-disassembly\tools\vm\qmp_win.ps1'
}

function Get-PythonExe {
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  throw 'Python 3 was not found on PATH.'
}

function Get-TierDurationSec {
  param([string]$Name, [int]$CustomDuration)
  switch ($Name) {
    'short2' { return 120 }
    'short10' { return 600 }
    'short30' { return 1800 }
    'custom' {
      if ($CustomDuration -le 0) { throw 'Use -DurationSec with -Tier custom.' }
      return $CustomDuration
    }
    default { throw "Unknown tier: $Name" }
  }
}

function Invoke-Qmp {
  param([string]$Op, [string]$Arg = '')
  & $qmp -Port $Port -Op $Op -Arg $Arg
}

# Size-stable screendump read (mirrors hd_vm_drive_menu.ps1 Save-Shot so the
# partial-frame 800x600->640x480 misread is not reintroduced).
function Save-GuestFrame {
  param([string]$Label, [string]$Dir)
  $ppm = Join-Path $Dir "$Label.ppm"
  Invoke-Qmp 'shot' $ppm | Out-Null
  $expected640 = 15 + 640 * 480 * 3
  $expected800 = 15 + 800 * 600 * 3
  $last = -1; $stableReads = 0
  for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 250
    if (-not (Test-Path -LiteralPath $ppm)) { continue }
    $sz = (Get-Item -LiteralPath $ppm).Length
    if ($sz -eq $last -and ($sz -ge $expected640 - 64)) { $stableReads++ } else { $stableReads = 0 }
    $last = $sz
    if ($stableReads -ge 2 -and ($sz -eq $expected640 -or $sz -ge $expected800)) { break }
  }
  return $ppm
}

function Get-FrameStats {
  param([string]$PpmPath, [string]$Python)
  $png = [System.IO.Path]::ChangeExtension($PpmPath, '.png')
  $code = @"
import json, sys
import ppm_to_png as ppm
frame = ppm.parse_ppm(open(sys.argv[1], 'rb').read())
ppm.write_png(frame, __import__('pathlib').Path(sys.argv[2]))
print(json.dumps(ppm.frame_stats(frame)))
"@
  $previous = $env:PYTHONPATH
  $env:PYTHONPATH = $ToolsDir
  try {
    $json = & $Python -c $code $PpmPath $png
    if ($LASTEXITCODE -ne 0) { return $null }
  } finally {
    $env:PYTHONPATH = $previous
  }
  return ($json | ConvertFrom-Json)
}

function Get-GuestStatusSample {
  $ts = (Get-Date).ToString('o')
  $status = 'unknown'
  $running = $false
  try {
    $obj = (Invoke-Qmp 'status') | ConvertFrom-Json
    if ($obj.return.status) { $status = [string]$obj.return.status }
    $running = [bool]$obj.return.running
  } catch {
    $status = 'query_error'
    $running = $false
  }
  return [pscustomobject]@{ Timestamp = $ts; Status = $status; Running = $running }
}

$python = Get-PythonExe
$DurationResolvedSec = Get-TierDurationSec -Name $Tier -CustomDuration $DurationSec
$CandidateFull = [System.IO.Path]::GetFullPath($Candidate)
$ReportJsonFull = if ([System.IO.Path]::IsPathRooted($ReportJson)) {
  [System.IO.Path]::GetFullPath($ReportJson)
} else {
  [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $ReportJson))
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$outDir = Join-Path ([System.IO.Path]::GetFullPath($OutputRoot)) ("guest-{0}-{1}-{2}" -f $Tier, $Route, $stamp)
$frameProgressExpected = ($Route -eq 'map-pan')
$artifactLimitBytes = [int64]$MaxArtifactMB * 1024 * 1024

function Write-GuestSoakReport {
  param([object]$Report)
  $dir = Split-Path -Parent $ReportJsonFull
  if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  $Report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $ReportJsonFull -Encoding ASCII
}

if (-not $AllowGuestRuntime) {
  # DRY RUN: plan only, executed=false so the grader treats it as a non-run.
  Write-Output "DRY RUN (no -AllowGuestRuntime): planning guest soak"
  Write-Output "  tier/route:   $Tier / $Route ($DurationResolvedSec s, sample every $SampleIntervalSec s)"
  Write-Output "  candidate:    $CandidateFull"
  Write-Output "  save fixtures:$($SaveFiles -join ', ')"
  Write-Output "  out dir:      $outDir"
  Write-Output "  report json:  $ReportJsonFull"
  $plan = [ordered]@{
    generated_at = (Get-Date).ToString('o')
    environment = 'guest_win98_qemu'
    evidence_class = 'approved_guest_win98_directdraw'
    runtime_policy = 'QEMU-Win98 guest soak driver; dry-run plans only and boots nothing without -AllowGuestRuntime'
    executed = $false
    passed = $false
    failures = @('dry_run: guest runtime not approved (-AllowGuestRuntime absent)')
    stage = $StableStage
    stable_stage_should_change = $false
    tier = $Tier
    route = $Route
    duration_sec = $DurationResolvedSec
    sample_interval_sec = $SampleIntervalSec
    candidate_build_path = $CandidateFull
    guest_exe_path = $GuestExePath
    report_json = $ReportJsonFull
    frame_sample_count = 0
    guest_status_samples = @()
    frame_samples = @()
    capture_errors = @()
  }
  Write-GuestSoakReport -Report $plan
  Write-Output "guest soak plan: $ReportJsonFull"
  exit 0
}

# ---- Approved guest soak run -------------------------------------------------
if (-not (Test-Path -LiteralPath $CandidateFull -PathType Leaf)) { throw "Candidate not found: $CandidateFull" }
if (-not (Test-Path -LiteralPath $qmp)) { throw "qmp client not found: $qmp" }
if ([string]::IsNullOrWhiteSpace($ApprovalRecord)) {
  throw 'A real guest soak requires -ApprovalRecord (the explicit user approval note/link).'
}
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$candidateSha = (Get-FileHash -LiteralPath $CandidateFull -Algorithm SHA256).Hash.ToLowerInvariant()

$failures = @()
$captureErrors = @()

# 1. Stage candidate + optional save fixtures.
$stageScript = Join-Path $PSScriptRoot 'hd_vm_stage.ps1'
$stageArgs = @{ Candidate = $CandidateFull }
if ($SaveFiles.Count -gt 0) { $stageArgs['SaveFiles'] = $SaveFiles }
& $stageScript @stageArgs | Write-Output

# 2. Boot + drive to the HD menu (first load click if a map route).
$firstClick = if ($Route -in @('map-idle', 'map-pan')) { $LoadRoutePoints[0] } else { '' }
$driveScript = Join-Path $PSScriptRoot 'hd_vm_drive_menu.ps1'
$driveOut = & $driveScript -Vm $Vm -Port $Port -OutDir $outDir -BootWaitSec $BootWaitSec -ClickPoint $firstClick -KeepRunning
$driveOut | Write-Output
$hdConfirmed = @($driveOut | Where-Object { $_ -is [string] -and $_ -match 'HD_MODE_CONFIRMED' }).Count -gt 0
if (-not $hdConfirmed) { $failures += 'HD mode (800x600) was not confirmed by hd_vm_drive_menu.ps1' }

# 3. For map routes finish the load route to reach the map.
if ($Route -in @('map-idle', 'map-pan')) {
  foreach ($pt in $LoadRoutePoints[1..($LoadRoutePoints.Count - 1)]) {
    Invoke-Qmp 'clickrel' $pt | Out-Null
    Start-Sleep -Seconds 2
  }
}

# 4. Sample loop: screendump + query-status every interval for the duration.
$frameSamples = @()
$guestStatusSamples = @()
$panIndex = 0
$deadline = (Get-Date).AddSeconds($DurationResolvedSec)
$sampleIndex = 0
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds $SampleIntervalSec
  # map-pan drives one pan leg per interval so frames must progress.
  if ($Route -eq 'map-pan') {
    $pt = $PanPathPoints[$panIndex % $PanPathPoints.Count]
    $panIndex++
    Invoke-Qmp 'clickrel' $pt | Out-Null
    Start-Sleep -Milliseconds 500
  }
  $guestStatusSamples += (Get-GuestStatusSample)
  $label = 'sample-{0:d4}' -f $sampleIndex
  $sampleIndex++
  $ts = (Get-Date).ToString('o')
  $ppm = Save-GuestFrame -Label $label -Dir $outDir
  $stats = Get-FrameStats -PpmPath $ppm -Python $python
  if (-not $stats) {
    $captureErrors += [pscustomobject]@{ Frame = $label; Error = 'frame stats could not be computed' }
    continue
  }
  $hash = (Get-FileHash -LiteralPath $ppm -Algorithm SHA256).Hash.ToLowerInvariant()
  $frameSamples += [pscustomobject]@{
    Name = $label
    Timestamp = $ts
    Width = [int]$stats.width
    Height = [int]$stats.height
    Hash = $hash
    NonblackPercent = [double]$stats.nonblack_percent
    UniqueSampleColors = [int]$stats.color_count
    CaptureMode = 'qmp_screendump'
  }
}

# 5. Aggregate frame metrics.
$nonblackValues = @($frameSamples | ForEach-Object { $_.NonblackPercent })
$uniqueValues = @($frameSamples | ForEach-Object { $_.UniqueSampleColors })
$uniqueHashes = @($frameSamples | ForEach-Object { $_.Hash } | Sort-Object -Unique)
$frameHashUniqueCount = @($uniqueHashes).Count
$frameStabilityClass = if (@($frameSamples).Count -le 0) { 'no_frames' } elseif ($frameHashUniqueCount -le 1) { 'stable_idle' } else { 'progressing' }
if ($frameProgressExpected -and $frameHashUniqueCount -lt 2) { $failures += 'map-pan route did not progress (fewer than 2 unique frame hashes)' }

$nonblackMin = if (@($nonblackValues).Count -gt 0) { [double](($nonblackValues | Measure-Object -Minimum).Minimum) } else { 0.0 }
$nonblackMax = if (@($nonblackValues).Count -gt 0) { [double](($nonblackValues | Measure-Object -Maximum).Maximum) } else { 0.0 }
$uniqueMin = if (@($uniqueValues).Count -gt 0) { [int](($uniqueValues | Measure-Object -Minimum).Minimum) } else { 0 }
$uniqueMax = if (@($uniqueValues).Count -gt 0) { [int](($uniqueValues | Measure-Object -Maximum).Maximum) } else { 0 }

$guestRunningAtEnd = @($guestStatusSamples | Where-Object { -not $_.Running }).Count -eq 0
if (-not $guestRunningAtEnd) { $failures += 'a guest status sample reported the guest not running' }

$artifactBytes = 0L
Get-ChildItem -LiteralPath $outDir -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object { $artifactBytes += $_.Length }
if ($artifactBytes -gt $artifactLimitBytes) { $failures += "artifact bytes $artifactBytes exceeds limit $artifactLimitBytes" }

# 6. Build the GUEST-labelled soak report (schema graded by evaluate_guest_report).
$report = [ordered]@{
  generated_at = (Get-Date).ToString('o')
  environment = 'guest_win98_qemu'
  evidence_class = 'approved_guest_win98_directdraw'
  runtime_policy = 'opt-in guest QEMU-Win98 QMP soak; host-process telemetry not applicable inside a headless guest'
  executed = $true
  passed = (@($failures).Count -eq 0)
  failures = @($failures)
  stage = $StableStage
  protected_stable_stage = $StableStage
  stable_stage_should_change = $false
  tier = $Tier
  route = $Route
  duration_sec = $DurationResolvedSec
  sample_interval_sec = $SampleIntervalSec
  input_sha256 = $ExpectedBaseSha256
  candidate_sha256 = $candidateSha
  candidate_build_path = $CandidateFull
  guest_exe_path = $GuestExePath
  report_json = $ReportJsonFull
  output_directory = $outDir
  frame_sample_count = @($frameSamples).Count
  frame_hash_unique_count = $frameHashUniqueCount
  frame_progress_expected = $frameProgressExpected
  frame_stability_class = $frameStabilityClass
  nonblack_percent_min = $nonblackMin
  nonblack_percent_max = $nonblackMax
  unique_sample_colors_min = $uniqueMin
  unique_sample_colors_max = $uniqueMax
  # Host-only telemetry: NOT obtainable inside a headless guest. Never faked.
  working_set_growth_bytes = $NotApplicableGuest
  private_memory_growth_bytes = $NotApplicableGuest
  handle_growth = $NotApplicableGuest
  exit_code = $NotApplicableGuest
  clean_stop = $NotApplicableGuest
  max_artifact_mb = $MaxArtifactMB
  artifact_limit_bytes = $artifactLimitBytes
  artifact_bytes = $artifactBytes
  guest_running_at_end = $guestRunningAtEnd
  guest_status_samples = @($guestStatusSamples)
  frame_samples = @($frameSamples)
  capture_errors = @($captureErrors)
  approval_record = $ApprovalRecord
}

Write-GuestSoakReport -Report $report
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $outDir 'report.json') -Encoding ASCII
Write-Output "guest soak report: $ReportJsonFull"
Write-Output "frames: $(@($frameSamples).Count)  unique-hashes: $frameHashUniqueCount  passed: $($report.passed)"

# 7. Optionally grade with the guest report guard.
if ($GradeReport) {
  $reportTool = Join-Path $ToolsDir 'hd_soak_report.py'
  & $python $reportTool $ReportJsonFull --guest | Write-Output
}

if (@($failures).Count -gt 0) {
  Write-Output 'failures:'
  foreach ($f in $failures) { Write-Output "  - $f" }
  exit 1
}
