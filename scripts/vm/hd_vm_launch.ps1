# Launch the clash-hd-dedicated headless QEMU Win98 guest.
#
# This is a SEPARATE machine from the clash-disassembly rig (C:\clash95-vm,
# QMP 4444). It has its own disk images and its own QMP port so both can run
# without colliding, and so HD-mod experiments never disturb the disassembly
# repo's original-vs-recovered comparison baseline.
#
# Provision the machine first with hd_vm_provision.ps1 (copies the installed
# Win98 disk + game drive from the disassembly rig). Nothing here writes to
# C:\clash95-vm.
#
#   hd_vm_launch.ps1                 # boot the installed HD guest
#   hd_vm_launch.ps1 -NoGame         # boot without the game drive attached
#   hd_vm_launch.ps1 -Port 4446      # alternate QMP port
param(
  [string]$Vm   = 'C:\clash-hd-vm',
  [string]$Hda  = 'C:\clash-hd-vm\hda.qcow2',
  [string]$Game = 'C:\clash-hd-vm\game.img',
  [int]$Port    = 4445,
  [string]$Cpu  = 'pentium2',
  [string]$Vga  = 'cirrus',
  [int]$MemMb   = 256,
  [switch]$NoGame,
  [switch]$NoUsb,
  [switch]$AllowVisibleRuntime
)

$ErrorActionPreference = 'Stop'

# The guest window is headless (-display none); frames come out over QMP
# screendump. This is NOT a host visible-runtime lane, so it does not fall under
# the no-popup rule - but keep the switch so callers can be explicit.
$qemu = 'C:\Program Files\qemu\qemu-system-i386.exe'
foreach ($required in @($qemu, $Hda)) {
  if (-not (Test-Path -LiteralPath $required)) {
    throw "Missing required path: $required (run scripts\vm\hd_vm_provision.ps1 first)"
  }
}
if (-not $NoGame -and -not (Test-Path -LiteralPath $Game)) {
  throw "Missing game drive: $Game (run scripts\vm\hd_vm_provision.ps1 first)"
}

# Refuse to stomp a guest that is already up on this port.
$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
  throw "QMP port $Port is already listening - an HD guest is likely running. Stop it first (hd_vm_launch.ps1 -Port $Port then QMP quit) or pick another -Port."
}

if (-not (Test-Path -LiteralPath $Vm)) { New-Item -ItemType Directory -Path $Vm -Force | Out-Null }
if (Test-Path "$Vm\seabios.txt") { Clear-Content "$Vm\seabios.txt" }

$qargs = @(
  # acpi=off: Win98 SE's ACPI driver wedges TCG at the boot splash (disassembly
  # rig finding, 2026-07-17). cache=writethrough: a hard kill otherwise drops
  # the writeback cache and can corrupt the guest filesystem.
  '-machine','pc,acpi=off','-cpu',$Cpu,'-m',"$MemMb",'-vga',$Vga,'-display','none',
  '-qmp',"tcp:127.0.0.1:$Port,server,nowait",'-rtc','base=2000-01-01',
  '-debugcon',"file:$Vm\seabios.txt",'-global','isa-debugcon.iobase=0x402',
  '-drive',"file=$Hda,format=qcow2,if=ide,index=0,media=disk,cache=writethrough"
)
if (-not $NoGame) {
  $qargs += @('-drive',"file=$Game,format=raw,if=ide,index=1,media=disk,cache=writethrough")
}
# usb-tablet gives an ABSOLUTE pointer, so QMP clicks land on exact pixels
# instead of needing relative-delta aiming.
if (-not $NoUsb) { $qargs += @('-usb','-device','usb-tablet') }
$qargs += @('-boot','order=c,menu=off')

Start-Process -FilePath $qemu -ArgumentList $qargs -WindowStyle Hidden -RedirectStandardError "$Vm\qemu.err.txt"
Start-Sleep -Seconds 3
$proc = Get-Process qemu-system-i386 -ErrorAction SilentlyContinue
if (-not $proc) {
  $err = if (Test-Path "$Vm\qemu.err.txt") { Get-Content "$Vm\qemu.err.txt" -Tail 5 -Raw } else { '(no stderr captured)' }
  throw "QEMU failed to start:`n$err"
}
Write-Output "hd guest launched: qmp=127.0.0.1:$Port vm=$Vm game=$(-not $NoGame) tablet=$(-not $NoUsb)"
