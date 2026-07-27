# Stage an HD candidate executable into the clash-hd guest's game drive and
# point the guest's auto-launch at it.
#
# The guest sees game.img as D:. Its StartUp runs D:\RUN.BAT, so rewriting
# RUN.BAT selects what launches on boot - no interactive guest input needed.
# The image is PARTITIONED (MBR, FAT32 at LBA 2048), so mtools needs the @@1M
# offset; without it mdir reports "non DOS media".
#
# Requires mtools inside WSL (mcopy/mdir/mtype). Never touches C:\Clash or the
# disassembly rig's C:\clash95-vm.
#
#   hd_vm_stage.ps1 -Candidate C:\ClashTests\...\clash95_hd_stable.exe
#   hd_vm_stage.ps1 -Candidate ... -GuestName CLASHHD.EXE -Args '/A5'
#   hd_vm_stage.ps1 -Candidate ... -SaveFiles C:\ClashTests\...\save\5.dat  # also copy save fixtures
#   hd_vm_stage.ps1 -Restore                      # point RUN.BAT back at the stock exe
#
# -SaveFiles copies one or more host save files into the guest's D:\clash\save
# directory (the game's save dir; RUN.BAT does `cd \clash`). It uses the same
# partitioned-image @@1M mtools offset as the candidate copy, so a per-target
# manual-DirectInput fixture (e.g. a slot5-as-slot0 right-bottom save) can be
# staged in the same pass. Host save files are never modified.
param(
  [string]$Candidate,
  [string]$GuestName = 'CLASHHD.EXE',
  [string]$Args = '',
  [string[]]$SaveFiles = @(),
  [string]$SaveDest = '::/clash/save',
  [string]$Image = 'C:\clash-hd-vm\game.img',
  [switch]$Restore
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Image)) {
  throw "Game image not found: $Image (run scripts\vm\hd_vm_provision.ps1 first)"
}
if (Get-Process qemu-system-i386 -ErrorAction SilentlyContinue) {
  throw "QEMU is running - shut the guest down before restaging its disk."
}

# Windows path -> WSL path, then append the partition offset mtools needs.
function ConvertTo-WslPath([string]$WinPath) {
  $full = [System.IO.Path]::GetFullPath($WinPath)
  $drive = $full.Substring(0,1).ToLower()
  '/mnt/' + $drive + ($full.Substring(2) -replace '\\','/')
}
$imgWsl = (ConvertTo-WslPath $Image) + '@@1M'

if ($Restore) {
  $bat = "@echo off`r`nD:`r`ncd \clash`r`nclash95.exe`r`n"
  $tmp = [System.IO.Path]::GetTempFileName()
  [System.IO.File]::WriteAllText($tmp, $bat)
  $tmpWsl = ConvertTo-WslPath $tmp
  wsl.exe -e bash -lc "mcopy -i '$imgWsl' -o '$tmpWsl' ::/RUN.BAT" | Out-Null
  Remove-Item $tmp -Force
  Write-Output "RUN.BAT restored to stock clash95.exe"
  exit 0
}

if (-not $Candidate) { throw "-Candidate is required (or pass -Restore)" }
if (-not (Test-Path -LiteralPath $Candidate)) { throw "Candidate not found: $Candidate" }

# Record what we staged: the SHA is what ties guest evidence back to a patch stage.
$sha = (Get-FileHash -LiteralPath $Candidate -Algorithm SHA256).Hash
$candWsl = ConvertTo-WslPath $Candidate

wsl.exe -e bash -lc "mcopy -i '$imgWsl' -o '$candWsl' ::/clash/$GuestName" | Out-Null

# Stage optional save fixtures into the guest save directory. mmd is allowed to
# fail (directory already exists), so it is guarded; each mcopy overwrites (-o).
if ($SaveFiles.Count -gt 0) {
  wsl.exe -e bash -lc "mmd -i '$imgWsl' $SaveDest 2>/dev/null; true" | Out-Null
  foreach ($save in $SaveFiles) {
    if (-not (Test-Path -LiteralPath $save)) { throw "Save fixture not found: $save" }
    $saveWsl = ConvertTo-WslPath $save
    $leaf = [System.IO.Path]::GetFileName($save)
    wsl.exe -e bash -lc "mcopy -i '$imgWsl' -o '$saveWsl' $SaveDest/$leaf" | Out-Null
    Write-Output "staged save fixture $leaf -> $SaveDest/$leaf"
  }
}

$argSuffix = if ($Args) { " $Args" } else { '' }
$bat = "@echo off`r`nD:`r`ncd \clash`r`n$GuestName$argSuffix`r`n"
$tmp = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($tmp, $bat)
$tmpWsl = ConvertTo-WslPath $tmp
wsl.exe -e bash -lc "mcopy -i '$imgWsl' -o '$tmpWsl' ::/RUN.BAT" | Out-Null
Remove-Item $tmp -Force

$listing = wsl.exe -e bash -lc "mdir -i '$imgWsl' ::/clash 2>/dev/null | grep -i '$($GuestName.Split('.')[0])'"
Write-Output "staged $GuestName sha256=$sha"
Write-Output "guest D:\clash listing: $listing"
Write-Output "RUN.BAT -> $GuestName$argSuffix"
