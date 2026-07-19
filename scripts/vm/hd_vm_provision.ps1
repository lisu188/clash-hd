# Provision the clash-hd-dedicated QEMU Win98 guest by duplicating the
# clash-disassembly rig's installed machine.
#
# Why duplicate instead of reusing: the disassembly rig (C:\clash95-vm) is the
# baseline for that repo's original-vs-recovered frame/tile comparisons. HD-mod
# experiments restage the game drive and rewrite D:\RUN.BAT, which would perturb
# that baseline. This gives clash-hd its own machine, its own game drive, and
# its own QMP port (hd_vm_launch.ps1 defaults to 4445 vs the rig's 4444).
#
# READ-ONLY with respect to the source: nothing here writes to C:\clash95-vm.
# Refuses to run while either guest is up, because copying a qcow2 that QEMU
# holds open read-write yields a corrupt copy.
#
#   hd_vm_provision.ps1              # copy hda.qcow2 + game.img
#   hd_vm_provision.ps1 -Overlay     # copy-on-write hda instead of a full copy
#   hd_vm_provision.ps1 -Force       # replace an existing HD machine
param(
  [string]$SourceVm = 'C:\clash95-vm',
  [string]$DestVm   = 'C:\clash-hd-vm',
  [switch]$Overlay,
  [switch]$Force
)

$ErrorActionPreference = 'Stop'
$qemuImg = 'C:\Program Files\qemu\qemu-img.exe'

$srcHda  = Join-Path $SourceVm 'hda.qcow2'
$srcGame = Join-Path $SourceVm 'game.img'
foreach ($required in @($srcHda, $srcGame)) {
  if (-not (Test-Path -LiteralPath $required)) { throw "Source image missing: $required" }
}

# A running QEMU on either machine means the disk is open read-write; copying it
# now would capture a torn filesystem.
if (Get-Process qemu-system-i386 -ErrorAction SilentlyContinue) {
  throw "QEMU is running. Shut the guest down cleanly (QMP powerdown, or 'quit') before provisioning - copying a live qcow2 produces a corrupt image."
}

$destHda  = Join-Path $DestVm 'hda.qcow2'
$destGame = Join-Path $DestVm 'game.img'
if ((Test-Path -LiteralPath $destHda) -and -not $Force) {
  throw "$destHda already exists. Re-run with -Force to replace the HD machine."
}

if (-not (Test-Path -LiteralPath $DestVm)) { New-Item -ItemType Directory -Path $DestVm -Force | Out-Null }

if ($Overlay) {
  # Copy-on-write: fast and space-cheap, but the HD guest breaks if the source
  # base is ever modified - i.e. if the disassembly rig boots its own hda again.
  # Full copy is the safer default for exactly that reason.
  if (-not (Test-Path -LiteralPath $qemuImg)) { throw "qemu-img not found: $qemuImg" }
  Write-Output "creating copy-on-write overlay (base stays $srcHda - do NOT boot the disassembly rig after this)"
  & $qemuImg create -f qcow2 -b $srcHda -F qcow2 $destHda | Out-Null
} else {
  Write-Output "copying $srcHda -> $destHda (2 GB, full independent copy)"
  Copy-Item -LiteralPath $srcHda -Destination $destHda -Force
}

Write-Output "copying $srcGame -> $destGame (2.5 GB game drive)"
Copy-Item -LiteralPath $srcGame -Destination $destGame -Force

$hdaSize  = (Get-Item $destHda).Length / 1GB
$gameSize = (Get-Item $destGame).Length / 1GB
Write-Output ("provisioned {0}: hda={1:N1} GB game={2:N1} GB overlay={3}" -f $DestVm, $hdaSize, $gameSize, [bool]$Overlay)
Write-Output "next: stage the HD candidate with scripts\vm\hd_vm_stage.ps1, then boot with scripts\vm\hd_vm_launch.ps1"
