param(
    [string]$InstallDir = "C:\Tools\x64dbg",
    [switch]$CreatePublicDesktopShortcut,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$ReleaseApi = "https://api.github.com/repos/x64dbg/x64dbg/releases/latest"
$FallbackUrl = "https://github.com/x64dbg/x64dbg/releases/download/2025.08.19/snapshot_2025-08-19_19-40.zip"
$TempZip = Join-Path $env:TEMP "x64dbg_snapshot.zip"
$TempExtract = Join-Path $env:TEMP ("x64dbg_extract_{0}" -f $PID)

function Write-Step([string]$Message) {
    Write-Host "[x64dbg-global] $Message"
}

function Assert-Administrator {
    $Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $Principal = New-Object Security.Principal.WindowsPrincipal($Identity)
    if (-not $Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this script from an elevated PowerShell window: right-click PowerShell and choose 'Run as administrator'."
    }
}

function Get-X64DbgSnapshotUrl {
    try {
        Write-Step "Querying latest x64dbg release from GitHub..."
        $Headers = @{ "User-Agent" = "clash-hd-x64dbg-global-installer" }
        $Release = Invoke-RestMethod -Uri $ReleaseApi -Headers $Headers
        $Asset = $Release.assets |
            Where-Object { $_.name -match '^snapshot_.*\.zip$' -and $_.name -notmatch '^symbols-' } |
            Select-Object -First 1

        if ($null -eq $Asset) {
            throw "No snapshot zip asset found in latest release."
        }

        return $Asset.browser_download_url
    }
    catch {
        Write-Warning "Could not resolve latest release automatically: $($_.Exception.Message)"
        Write-Warning "Falling back to known snapshot: $FallbackUrl"
        return $FallbackUrl
    }
}

function Add-MachinePath([string]$PathToAdd) {
    $CurrentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $Parts = @()
    if ($CurrentPath) {
        $Parts = $CurrentPath -split ';' | Where-Object { $_ }
    }

    $AlreadyPresent = $false
    foreach ($Part in $Parts) {
        if ($Part.TrimEnd('\') -ieq $PathToAdd.TrimEnd('\')) {
            $AlreadyPresent = $true
            break
        }
    }

    if ($AlreadyPresent) {
        Write-Step "Machine PATH already contains $PathToAdd"
        return
    }

    $NewPath = (($Parts + $PathToAdd) -join ';')
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "Machine")
    Write-Step "Added to Machine PATH: $PathToAdd"
}

function New-Shortcut([string]$ShortcutPath, [string]$TargetPath, [string]$Description) {
    $ShortcutDir = Split-Path $ShortcutPath -Parent
    New-Item -ItemType Directory -Force -Path $ShortcutDir | Out-Null

    $Shell = New-Object -ComObject WScript.Shell
    $Shortcut = $Shell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $TargetPath
    $Shortcut.WorkingDirectory = Split-Path $TargetPath -Parent
    $Shortcut.Description = $Description
    $Shortcut.Save()
    Write-Step "Created shortcut: $ShortcutPath"
}

try {
    Assert-Administrator

    $Url = Get-X64DbgSnapshotUrl

    if ((Test-Path $InstallDir) -and -not $Force) {
        $ExistingX32 = Get-ChildItem -Path $InstallDir -Recurse -Filter "x32dbg.exe" -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($ExistingX32) {
            Write-Step "x64dbg already appears installed at: $InstallDir"
            Write-Step "x32dbg: $($ExistingX32.FullName)"
            Write-Step "Use -Force to reinstall/overwrite."
            exit 0
        }
    }

    if (Test-Path $TempZip) {
        Remove-Item -LiteralPath $TempZip -Force
    }
    if (Test-Path $TempExtract) {
        Remove-Item -LiteralPath $TempExtract -Recurse -Force
    }

    New-Item -ItemType Directory -Force -Path (Split-Path $TempZip) | Out-Null
    New-Item -ItemType Directory -Force -Path $TempExtract | Out-Null
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

    Write-Step "Downloading $Url"
    Invoke-WebRequest -Uri $Url -OutFile $TempZip -UseBasicParsing

    Write-Step "Extracting archive..."
    Expand-Archive -Path $TempZip -DestinationPath $TempExtract -Force

    $ExtractedX32 = Get-ChildItem -Path $TempExtract -Recurse -Filter "x32dbg.exe" |
        Select-Object -First 1
    if ($null -eq $ExtractedX32) {
        throw "Archive did not contain x32dbg.exe."
    }

    $ReleaseRoot = Split-Path (Split-Path $ExtractedX32.FullName -Parent) -Parent
    Write-Step "Installing to $InstallDir"
    Copy-Item -Path (Join-Path $ReleaseRoot "*") -Destination $InstallDir -Recurse -Force

    Get-ChildItem -Path $InstallDir -Recurse -File -ErrorAction SilentlyContinue | Unblock-File

    $X32Dbg = Get-ChildItem -Path $InstallDir -Recurse -Filter "x32dbg.exe" |
        Select-Object -First 1
    $X64Dbg = Get-ChildItem -Path $InstallDir -Recurse -Filter "x64dbg.exe" |
        Select-Object -First 1
    $X96Dbg = Get-ChildItem -Path $InstallDir -Recurse -Filter "x96dbg.exe" |
        Select-Object -First 1

    if ($null -eq $X32Dbg) {
        throw "Install finished but x32dbg.exe was not found under $InstallDir."
    }

    Add-MachinePath (Split-Path $X32Dbg.FullName -Parent)
    if ($X64Dbg) {
        Add-MachinePath (Split-Path $X64Dbg.FullName -Parent)
    }
    if ($X96Dbg) {
        Add-MachinePath (Split-Path $X96Dbg.FullName -Parent)
    }

    $StartMenuDir = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs\x64dbg"
    New-Shortcut -ShortcutPath (Join-Path $StartMenuDir "x32dbg.lnk") -TargetPath $X32Dbg.FullName -Description "x32dbg 32-bit debugger"
    if ($X64Dbg) {
        New-Shortcut -ShortcutPath (Join-Path $StartMenuDir "x64dbg.lnk") -TargetPath $X64Dbg.FullName -Description "x64dbg 64-bit debugger"
    }
    if ($X96Dbg) {
        New-Shortcut -ShortcutPath (Join-Path $StartMenuDir "x96dbg launcher.lnk") -TargetPath $X96Dbg.FullName -Description "x64dbg architecture launcher"
    }

    if ($CreatePublicDesktopShortcut) {
        $PublicDesktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
        New-Shortcut -ShortcutPath (Join-Path $PublicDesktop "x32dbg.lnk") -TargetPath $X32Dbg.FullName -Description "x32dbg 32-bit debugger"
    }

    Write-Step "Installed successfully."
    Write-Host ""
    Write-Host "x32dbg path: $($X32Dbg.FullName)"
    if ($X64Dbg) {
        Write-Host "x64dbg path: $($X64Dbg.FullName)"
    }
    if ($X96Dbg) {
        Write-Host "launcher path: $($X96Dbg.FullName)"
    }
    Write-Host ""
    Write-Host "Open a new terminal to pick up the updated Machine PATH."
    Write-Host "For Clash95, use:"
    Write-Host "  x32dbg `"C:\Clash\clash95_hdtest.exe`""
}
finally {
    if (Test-Path $TempZip) {
        Remove-Item -LiteralPath $TempZip -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $TempExtract) {
        Remove-Item -LiteralPath $TempExtract -Recurse -Force -ErrorAction SilentlyContinue
    }
}
