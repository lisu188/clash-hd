# Per-target QEMU-Win98 guest run scaffold for the HD manual-DirectInput lane.
#
# This is the GUEST analogue of tools/run_hd_linux_validation.py: for ONE of the
# five required manual-DirectInput targets it stages the candidate (+ optional
# save fixtures) into the clash-hd guest, boots the headless Win98 guest, drives
# it to the HD (800x600) menu, replays the target's pulse route + follow-up click
# points over QMP, captures a screendump frame at each step, and folds the frames
# into a run-manifest.json in the exact shape
# tools/assemble_manual_directinput_proof.py consumes.
#
# HONESTY: guest evidence is a DISTINCT proof class. The manifest is stamped
# evidence_class=approved_guest_win98_directdraw / environment=guest_win98_qemu
# and runner=qemu-win98-guest, and every per-target observed_result/evidence/
# pass_fail_notes is left EMPTY with status=pending so the fail-closed host
# assembler (which hardcodes evidence_class=manual_directinput) can never
# silently promote these frames as host manual-DirectInput release proof. A guest
# assembler/validator fills the observations from the captured frames.
#
# SAFETY: dry-run by default. Without -AllowGuestRuntime it only PLANS -- it
# stages nothing, boots nothing, injects nothing -- and writes a plan manifest.
# A real run requires -AllowGuestRuntime (mirroring -AllowVisibleRuntime). It
# uses QMP port 4445 ONLY; 4444 is the clash-disassembly rig and is refused. It
# never touches C:\Clash or C:\clash95-vm.
#
#   hd_vm_run_target.ps1 -TargetId stable_hd_map_input -Candidate C:\ClashTests\...\clash95_hd_stable.exe
#   hd_vm_run_target.ps1 -TargetId right_bottom_validation_input -Candidate ... -SaveFiles C:\ClashTests\...\5.dat -AllowGuestRuntime
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet(
    'stable_menu_load',
    'stable_hd_map_input',
    'right_bottom_validation_input',
    'castle_barracks_centered_input',
    'castle_overview_centered_input'
  )]
  [string]$TargetId,
  [Parameter(Mandatory = $true)]
  [string]$Candidate,
  [string[]]$SaveFiles = @(),
  [string]$ApprovalRecord = '',
  [string]$Vm = 'C:\clash-hd-vm',
  [int]$Port = 4445,
  [string]$OutDir = '',
  [int]$BootWaitSec = 300,
  [int]$SettleSec = 3,
  [int]$ClickHoldMs = 300,
  [int]$ClickRepeat = 2,
  [switch]$AllowGuestRuntime
)

$ErrorActionPreference = 'Stop'

# 4444 is the disassembly rig's QMP port; the HD lane is 4445-only so an HD run
# can never drive that machine's guest.
if ($Port -eq 4444) {
  throw 'Port 4444 is the clash-disassembly rig. The HD guest lane uses 4445 only.'
}

$RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$ToolsDir = Join-Path $RepoRoot 'tools'
$ExpectedBaseSha256 = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
$GuestExePath = 'D:\CLASHHD.EXE'

$qmp = Join-Path $PSScriptRoot '..\..\..\clash-disassembly\tools\vm\qmp_win.ps1'
if (-not (Test-Path -LiteralPath $qmp)) {
  $qmp = 'C:\Users\andrz\git\clash-disassembly\tools\vm\qmp_win.ps1'
}

function Get-PythonExe {
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  throw 'Python 3 was not found on PATH.'
}

# Load the authoritative per-target coordinates from
# tools/manual_directinput_run_plan.COMMAND_SPECS (never re-derive them here) and
# the authoritative stage from tools/manual_directinput_checklist.CHECKLIST_ITEMS.
function Get-TargetSpec {
  param([string]$Id, [string]$Python)
  $code = @"
import json
import manual_directinput_run_plan as plan
import manual_directinput_checklist as checklist
spec = plan.COMMAND_SPECS['$Id']
stage = {item['id']: item['stage'] for item in checklist.CHECKLIST_ITEMS}['$Id']
print(json.dumps({
    'stage': stage,
    'route': spec['route'],
    'route_points': spec['route_points'],
    'pulse_route_steps': spec['pulse_route_steps'],
    'followup_points': spec['followup_points'],
    'notes': spec['notes'],
}))
"@
  $previous = $env:PYTHONPATH
  $env:PYTHONPATH = $ToolsDir
  try {
    $json = & $Python -c $code
    if ($LASTEXITCODE -ne 0) { throw "failed to load COMMAND_SPECS for $Id" }
  } finally {
    $env:PYTHONPATH = $previous
  }
  return ($json | ConvertFrom-Json)
}

# Parse a 'name:x,y;name:x,y' point spec into ordered {Name,X,Y} rows.
function ConvertFrom-PointSpec {
  param([string]$Spec)
  $rows = @()
  if (-not $Spec) { return $rows }
  foreach ($chunk in ($Spec -split ';')) {
    $chunk = $chunk.Trim()
    if (-not $chunk) { continue }
    $name = ''
    $coord = $chunk
    if ($chunk -match '^(?<name>[^:]+):(?<coord>.+)$') {
      $name = $Matches.name.Trim()
      $coord = $Matches.coord.Trim()
    }
    $xy = $coord -split ','
    if (@($xy).Count -lt 2) { continue }
    $rows += [pscustomobject]@{ Name = $name; X = [int]$xy[0].Trim(); Y = [int]$xy[1].Trim() }
  }
  return $rows
}

function Invoke-Qmp {
  param([string]$Op, [string]$Arg = '')
  & $qmp -Port $Port -Op $Op -Arg $Arg
}

# Size-stable screendump read (mirrors hd_vm_drive_menu.ps1 Save-Shot so the
# 2026-07-19 partial-frame 800x600->640x480 misread is not reintroduced).
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

# Fold a captured PPM into a frame-stats row using tools/ppm_to_png.py
# (parse_ppm fail-closes on a partial frame; frame_stats gives nonblack/colors).
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
  $stats = $json | ConvertFrom-Json
  $hash = (Get-FileHash -LiteralPath $PpmPath -Algorithm SHA256).Hash.ToLowerInvariant()
  return [pscustomobject]@{
    ppm = $PpmPath
    png = $png
    width = [int]$stats.width
    height = [int]$stats.height
    nonblack_percent = [double]$stats.nonblack_percent
    color_count = [int]$stats.color_count
    hd_mode = ([int]$stats.width -eq 800 -and [int]$stats.height -eq 600)
    hash = $hash
  }
}

$python = Get-PythonExe
$spec = Get-TargetSpec -Id $TargetId -Python $python
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
if (-not $OutDir) {
  $OutDir = Join-Path $RepoRoot ("captures\archive\vm-manual-di-{0}-{1}" -f $TargetId, $stamp)
}
$OutDirFull = [System.IO.Path]::GetFullPath($OutDir)
New-Item -ItemType Directory -Path $OutDirFull -Force | Out-Null

$candidateExists = Test-Path -LiteralPath $Candidate -PathType Leaf
$candidateSha = $null
if ($candidateExists) {
  $candidateSha = (Get-FileHash -LiteralPath $Candidate -Algorithm SHA256).Hash.ToLowerInvariant()
}

# Route + follow-up click points in 800x600 HD-frame coordinates (QMP clickrel
# space), taken straight from COMMAND_SPECS.
$routePoints = ConvertFrom-PointSpec $spec.pulse_route_steps
$followupPoints = ConvertFrom-PointSpec $spec.followup_points
$manifestPath = Join-Path $OutDirFull 'run-manifest.json'

$targetRow = [ordered]@{
  id = $TargetId
  stage = $spec.stage
  route = $spec.route
  pulse_route_steps = $spec.pulse_route_steps
  followup_points = $spec.followup_points
  candidate_path = $Candidate
  guest_exe_path = $GuestExePath
  executable_sha256 = $candidateSha
  notes = $spec.notes
  # Fail-closed observation fields: a guest validator fills these from the frames.
  observed_result = ''
  evidence = ''
  pass_fail_notes = ''
  no_crash = $false
  status = 'pending'
  artifacts = @()
}

$manifest = [ordered]@{
  generated_at = (Get-Date).ToString('o')
  runner = 'qemu-win98-guest'
  environment = 'guest_win98_qemu'
  evidence_class = 'approved_guest_win98_directdraw'
  guest_proof_note = 'DISTINCT guest proof class; never record as host manual_directinput evidence'
  runtime_policy = 'QEMU-Win98 guest driver; dry-run plans only and stages/boots/injects nothing without -AllowGuestRuntime'
  target_id = $TargetId
  qmp_port = $Port
  dry_run = (-not $AllowGuestRuntime)
  approved_visible_runtime = [bool]$AllowGuestRuntime
  approval_record = $ApprovalRecord
  no_stale_processes = $true
  expected_base_sha256 = $ExpectedBaseSha256
  candidate_path = $Candidate
  candidate_present = $candidateExists
  executable_sha256 = $candidateSha
  guest_exe_path = $GuestExePath
  save_files = @($SaveFiles)
  out_dir = $OutDirFull
  targets = @($targetRow)
  failures = @()
}

if (-not $AllowGuestRuntime) {
  # DRY RUN: plan only. Never stages, boots, or injects.
  Write-Output "DRY RUN (no -AllowGuestRuntime): planning guest run for $TargetId"
  Write-Output "  stage:            $($spec.stage)"
  Write-Output "  route:            $($spec.route)"
  Write-Output "  pulse route:      $($spec.pulse_route_steps)"
  Write-Output "  follow-up points: $($spec.followup_points)"
  Write-Output "  candidate:        $Candidate (present=$candidateExists)"
  Write-Output "  save fixtures:    $($SaveFiles -join ', ')"
  Write-Output "  out dir:          $OutDirFull"
  Write-Output '  would stage:      scripts\vm\hd_vm_stage.ps1 -Candidate <candidate> [-SaveFiles ...]'
  Write-Output "  would boot+drive: scripts\vm\hd_vm_drive_menu.ps1 -Port $Port -ClickPoint '<first route point>'"
  Write-Output '  would inject:     remaining route + follow-up points via qmp_win.ps1 clickrel'
  $manifest.failures = @('dry_run: guest runtime not approved (-AllowGuestRuntime absent)')
  $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding ASCII
  Write-Output "run-manifest (plan): $manifestPath"
  exit 0
}

# ---- Approved guest run ------------------------------------------------------
if (-not $candidateExists) { throw "Candidate not found: $Candidate" }
if (-not (Test-Path -LiteralPath $qmp)) { throw "qmp client not found: $qmp" }
if ($candidateSha -ne $ExpectedBaseSha256) {
  # Informational: the candidate is a PATCHED build, so a differing SHA is
  # expected. The SHA is recorded for provenance, not gated here.
  Write-Output "candidate sha256=$candidateSha (patched build; base=$ExpectedBaseSha256)"
}
if ([string]::IsNullOrWhiteSpace($ApprovalRecord)) {
  throw 'A real guest run requires -ApprovalRecord (the explicit user approval note/link).'
}

$runFailures = @()

# 1. Stage candidate + optional save fixtures.
$stageScript = Join-Path $PSScriptRoot 'hd_vm_stage.ps1'
$stageArgs = @{ Candidate = $Candidate }
if ($SaveFiles.Count -gt 0) { $stageArgs['SaveFiles'] = $SaveFiles }
& $stageScript @stageArgs | Write-Output

# 2. Boot + drive to the HD menu, clicking the first route point.
$firstPoint = if (@($routePoints).Count -gt 0) { '{0},{1}' -f $routePoints[0].X, $routePoints[0].Y } else { '' }
$driveScript = Join-Path $PSScriptRoot 'hd_vm_drive_menu.ps1'
$driveOut = & $driveScript -Vm $Vm -Port $Port -OutDir $OutDirFull -BootWaitSec $BootWaitSec -ClickPoint $firstPoint -KeepRunning
$driveOut | Write-Output
$hdConfirmed = @($driveOut | Where-Object { $_ -is [string] -and $_ -match 'HD_MODE_CONFIRMED' }).Count -gt 0
if (-not $hdConfirmed) { $runFailures += 'HD mode (800x600) was not confirmed by hd_vm_drive_menu.ps1' }

# 3. Replay the remaining route points, then the follow-up points, capturing a
# frame after each click.
$frameStats = @()
$remaining = @()
if (@($routePoints).Count -gt 1) { $remaining = $routePoints[1..($routePoints.Count - 1)] }
$allSteps = @()
foreach ($p in $remaining) { $allSteps += [pscustomobject]@{ Phase = 'route'; Row = $p } }
foreach ($p in $followupPoints) { $allSteps += [pscustomobject]@{ Phase = 'followup'; Row = $p } }

$stepIndex = 0
foreach ($step in $allSteps) {
  $stepIndex++
  $row = $step.Row
  $label = '{0}-{1:d2}-{2}' -f $step.Phase, $stepIndex, ($(if ($row.Name) { $row.Name } else { 'point' }))
  for ($r = 0; $r -lt [Math]::Max(1, $ClickRepeat); $r++) {
    Invoke-Qmp 'clickrel' ('{0},{1}' -f $row.X, $row.Y) | Out-Null
    Start-Sleep -Milliseconds $ClickHoldMs
  }
  Start-Sleep -Seconds $SettleSec
  $ppm = Save-GuestFrame -Label $label -Dir $OutDirFull
  $stats = Get-FrameStats -PpmPath $ppm -Python $python
  if ($stats) {
    $frameStats += $stats
  } else {
    $runFailures += "frame stats could not be computed for $label"
  }
}

# 4. Final liveness: is the guest still running?
$statusJson = Invoke-Qmp 'status'
$guestRunning = $false
try {
  $statusObj = $statusJson | ConvertFrom-Json
  $guestRunning = [bool]$statusObj.return.running
} catch {
  $runFailures += "guest query-status could not be parsed: $($_.Exception.Message)"
}
if (-not $guestRunning) { $runFailures += 'guest was not running at end of route (query-status)' }

# 5. Fold frames into the target row. no_crash requires the guest alive, an HD
# frame captured, and no step error.
$hdFrames = @($frameStats | Where-Object { $_.hd_mode })
$targetRow.artifacts = @($frameStats | ForEach-Object { $_.png })
$targetRow.no_crash = ($guestRunning -and @($hdFrames).Count -gt 0 -and @($runFailures).Count -eq 0)

$artifactBytes = 0L
Get-ChildItem -LiteralPath $OutDirFull -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object { $artifactBytes += $_.Length }

$manifest.dry_run = $false
$manifest.targets = @($targetRow)
$manifest.frame_stats = @($frameStats)
$manifest.hd_frame_count = @($hdFrames).Count
$manifest.guest_running_at_end = $guestRunning
$manifest.artifact_bytes = $artifactBytes
$manifest.failures = @($runFailures)
$manifest.passed = (@($runFailures).Count -eq 0)

$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding ASCII
Write-Output "run-manifest: $manifestPath"
Write-Output "hd-frames: $(@($hdFrames).Count)  guest-running: $guestRunning  passed: $($manifest.passed)"
if (@($runFailures).Count -gt 0) {
  Write-Output 'failures:'
  foreach ($f in $runFailures) { Write-Output "  - $f" }
}
Write-Output 'NOTE: observed_result/evidence/pass_fail_notes are left empty (status=pending);'
Write-Output '      a guest validator fills them. These frames are approved_guest_win98_directdraw,'
Write-Output '      NOT host manual_directinput release proof.'
