# Drive the clash-hd guest from a cold boot to the HD main menu, then optionally
# exercise a menu click, capturing frames at each step.
#
# This is the guest-side equivalent of the host visual-smoke lane. It exists
# because the host lane cannot run while the workstation is locked (Windows
# denies SetCursorPos/SendInput into a locked session) whereas QMP input is
# injected by the hypervisor and is unaffected.
#
# Sequence facts learned 2026-07-19 (do not re-derive):
#  - Win98 boots to the desktop with a "Welcome to Windows 98" dialog; alt+f4
#    closes it.
#  - The game does NOT auto-launch from StartUp despite the disassembly rig's
#    README. It is launched from the Run dialog, whose MRU already holds
#    'd:\run.bat ...'; ctrl+esc then 'r' opens Run and 'ret' runs the MRU entry.
#    hd_vm_stage.ps1 rewrites D:\RUN.BAT so that MRU entry launches the HD
#    candidate.
#  - Win98 sits at 640x480; a screendump header of 800x600 IS the HD-mode proof.
#    PPM size is a pure function of dimensions, so never gate on byte size.
#
#   hd_vm_drive_menu.ps1                      # boot -> menu, capture
#   hd_vm_drive_menu.ps1 -ClickPoint '300,208'  # also click (HD-frame coords)
#   hd_vm_drive_menu.ps1 -SkipBoot            # guest already at the desktop
param(
  [string]$Vm = 'C:\clash-hd-vm',
  [int]$Port = 4445,
  [string]$OutDir = '',
  [int]$BootWaitSec = 300,
  [int]$LaunchWaitSec = 45,
  [string]$ClickPoint = '',
  [switch]$SkipBoot,
  [switch]$KeepRunning
)

$ErrorActionPreference = 'Stop'
$qmp = Join-Path $PSScriptRoot '..\..\..\clash-disassembly\tools\vm\qmp_win.ps1'
if (-not (Test-Path -LiteralPath $qmp)) {
  $qmp = 'C:\Users\andrz\git\clash-disassembly\tools\vm\qmp_win.ps1'
}
if (-not (Test-Path -LiteralPath $qmp)) { throw "qmp client not found: $qmp" }

if (-not $OutDir) {
  $OutDir = Join-Path $Vm ("drive-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
}
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

function Invoke-Qmp([string]$Op, [string]$Arg = '') {
  & $qmp -Port $Port -Op $Op -Arg $Arg 2>&1 | Out-Null
}

# Read the PPM header without loading the whole frame: 'P6 <w> <h> 255'.
function Get-ShotDims([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { return $null }
  $fs = [IO.File]::OpenRead($Path)
  try {
    $buf = New-Object byte[] 32
    $n = $fs.Read($buf, 0, 32)
    $txt = [Text.Encoding]::ASCII.GetString($buf, 0, $n)
  } finally { $fs.Close() }
  if ($txt -match 'P6\s+(\d+)\s+(\d+)') { return @([int]$Matches[1], [int]$Matches[2]) }
  return $null
}

function Save-Shot([string]$Label) {
  $ppm = Join-Path $OutDir "$Label.ppm"
  Invoke-Qmp 'shot' $ppm
  # BUG FOUND 2026-07-19: an 800x600 PPM is 1.4 MB and QEMU's screendump is not
  # atomic - reading the header ~800ms after requesting it caught a stale/partial
  # file and misreported an HD frame as 640x480. Wait for the file SIZE to stop
  # growing (a settled, fully-written frame) before trusting its header.
  $expected640 = 15 + 640 * 480 * 3
  $expected800 = 15 + 800 * 600 * 3
  $last = -1; $stableReads = 0
  for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 250
    if (-not (Test-Path -LiteralPath $ppm)) { continue }
    $sz = (Get-Item -LiteralPath $ppm).Length
    if ($sz -eq $last -and ($sz -ge $expected640 - 64)) { $stableReads++ } else { $stableReads = 0 }
    $last = $sz
    if ($stableReads -ge 2 -and ($sz -eq $expected640 -or $sz -eq $expected800 -or $sz -ge $expected800)) { break }
  }
  $dims = Get-ShotDims $ppm
  if ($dims) { Write-Output ("{0}: {1}x{2} ({3} bytes)" -f $Label, $dims[0], $dims[1], $last) }
  else { Write-Output "${Label}: <no frame>" }
  return $dims
}

if (-not $SkipBoot) {
  if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    Write-Output "guest already listening on $Port; skipping launch"
  } else {
    & (Join-Path $PSScriptRoot 'hd_vm_launch.ps1') -Vm $Vm -Port $Port | Write-Output
  }
  # Dimensions are USELESS as a boot signal: the framebuffer is 640x480 for the
  # whole boot, so "two 640x480 frames" fires while Win98 is still starting and
  # the keystrokes below land nowhere (observed 2026-07-19). Use frame CONTENT
  # instead - the screen changes constantly while booting and goes static once
  # the desktop is idle. Require several consecutive identical frames, and a
  # minimum elapsed time so an early static splash cannot satisfy it.
  Write-Output "waiting up to ${BootWaitSec}s for a STABLE Win98 desktop..."
  $deadline = (Get-Date).AddSeconds($BootWaitSec)
  $minElapsed = (Get-Date).AddSeconds([Math]::Min(150, $BootWaitSec / 2))
  $lastHash = ''
  $stable = 0
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 15
    $ppm = Join-Path $OutDir 'boot-probe.ppm'
    Invoke-Qmp 'shot' $ppm
    Start-Sleep -Milliseconds 800
    if (-not (Test-Path -LiteralPath $ppm)) { continue }
    $h = (Get-FileHash -LiteralPath $ppm -Algorithm SHA256).Hash
    if ($h -eq $lastHash) { $stable++ } else { $stable = 0 }
    $lastHash = $h
    $d = Get-ShotDims $ppm
    Write-Output ("  boot probe: {0}x{1} stable={2}" -f $d[0], $d[1], $stable)
    if ($stable -ge 2 -and (Get-Date) -gt $minElapsed) { break }
  }
  Copy-Item (Join-Path $OutDir 'boot-probe.ppm') (Join-Path $OutDir 'desktop-settled.ppm') -Force -ErrorAction SilentlyContinue
}

# If the game is already up (800x600), a stray earlier launch is running; do NOT
# alt+F4 (that only BACKGROUNDS it - taskbar keeps "Clash" - and a re-launch then
# starts a SECOND instance; observed 2026-07-19). Only run the launch sequence
# from a clean 640x480 desktop.
$pre = Save-Shot 'pre-launch'
if ($pre -and $pre[0] -eq 800) {
  Write-Output "guest is ALREADY at 800x600 (game running) - skipping launch to avoid a second instance"
  $hd = $true
} else {
  Write-Output "closing the Welcome dialog and opening Run..."
  Invoke-Qmp 'chord' 'alt,f4'; Start-Sleep -Seconds 2
  Invoke-Qmp 'chord' 'ctrl,esc'; Start-Sleep -Seconds 2
  Invoke-Qmp 'key' 'r'; Start-Sleep -Seconds 3
  Save-Shot 'run-dialog' | Out-Null

  Write-Output "launching the staged HD candidate via the Run MRU..."
  Invoke-Qmp 'key' 'ret'

  $deadline = (Get-Date).AddSeconds($LaunchWaitSec)
  $hd = $false
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 10
    $d = Save-Shot 'launch-probe'
    if ($d -and $d[0] -eq 800 -and $d[1] -eq 600) { $hd = $true; break }
  }
}

if ($hd) {
  Save-Shot 'hd-menu' | Out-Null
  Write-Output "HD_MODE_CONFIRMED 800x600"
} else {
  Write-Output "HD_MODE_NOT_REACHED (still 640x480) - inspect $OutDir"
}

if ($ClickPoint -and $hd) {
  Write-Output "clicking $ClickPoint (HD-frame coords) via PS/2 relative saturation..."
  Save-Shot 'before-click' | Out-Null
  Invoke-Qmp 'clickrel' $ClickPoint
  Start-Sleep -Seconds 3
  Save-Shot 'after-click' | Out-Null
}

Write-Output "frames in $OutDir"
if (-not $KeepRunning) {
  Write-Output "leaving the guest RUNNING (pass -KeepRunning:\$false semantics not implemented; stop with qmp quit)"
}
