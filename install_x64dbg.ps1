param(
    [string]$InstallDir = "$env:LOCALAPPDATA\Programs\x64dbg",
    [switch]$CreateDesktopShortcut,
    [switch]$AddToUserPath,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$ReleaseApi = "https://api.github.com/repos/x64dbg/x64dbg/releases/latest"
$FallbackUrl = "https://github.com/x64dbg/x64dbg/releases/download/2025.08.19/snapshot_2025-08-19_19-40.zip"
$TempZip = Join-Path $env:TEMP "x64dbg_snapshot.zip"
$TempExtract = Join-Path $env:TEMP ("x64dbg_extract_{0}" -f $PID)

function Write-Step([string]$Message) {
    Write-Host "[x64dbg] $Message"
}

function Get-X64DbgSnapshotUrl {
    try {
        Write-Step "Querying latest x64dbg release from GitHub..."
        $Headers = @{ "User-Agent" = "clash-hd-x64dbg-installer" }
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

function Add-UserPath([string]$PathToAdd) {
    $CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $Parts = @()
    if ($CurrentPath) {
        $Parts = $CurrentPath -split ';' | Where-Object { $_ }
    }

    if ($Parts -contains $PathToAdd) {
        Write-Step "User PATH already contains $PathToAdd"
        return
    }

    $NewPath = (($Parts + $PathToAdd) -join ';')
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    Write-Step "Added to user PATH: $PathToAdd"
}

try {
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
    $X96Dbg = Get-ChildItem -Path $InstallDir -Recurse -Filter "x96dbg.exe" |
        Select-Object -First 1

    if ($AddToUserPath -and $X32Dbg) {
        Add-UserPath (Split-Path $X32Dbg.FullName -Parent)
    }

    if ($CreateDesktopShortcut -and $X32Dbg) {
        $Desktop = [Environment]::GetFolderPath("Desktop")
        $ShortcutPath = Join-Path $Desktop "x32dbg.lnk"
        $Shell = New-Object -ComObject WScript.Shell
        $Shortcut = $Shell.CreateShortcut($ShortcutPath)
        $Shortcut.TargetPath = $X32Dbg.FullName
        $Shortcut.WorkingDirectory = Split-Path $X32Dbg.FullName -Parent
        $Shortcut.Description = "x32dbg debugger"
        $Shortcut.Save()
        Write-Step "Created desktop shortcut: $ShortcutPath"
    }

    Write-Step "Installed successfully."
    Write-Host ""
    Write-Host "x32dbg path: $($X32Dbg.FullName)"
    if ($X96Dbg) {
        Write-Host "launcher path: $($X96Dbg.FullName)"
    }
    Write-Host ""
    Write-Host "For Clash95, use x32dbg:"
    Write-Host "  & `"$($X32Dbg.FullName)`" `"C:\Clash\clash95_hdtest.exe`""
}
finally {
    if (Test-Path $TempZip) {
        Remove-Item -LiteralPath $TempZip -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $TempExtract) {
        Remove-Item -LiteralPath $TempExtract -Recurse -Force -ErrorAction SilentlyContinue
    }
}
