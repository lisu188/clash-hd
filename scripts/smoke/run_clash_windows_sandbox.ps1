param(
    [string]$RepoRoot = (Join-Path $PSScriptRoot '..\..'),
    [string]$OutRoot = 'C:\ClashCaptures\windows-sandbox',
    [string]$GameRoot = 'C:\Clash',
    [string]$PythonHostPath = 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [string]$Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch',
    [string]$CandidateName = 'clash95_hd_sandbox_candidate.exe',
    [string]$Points = '320,245;448,245;648,49;760,201',
    [ValidateSet('setcursor', 'sendinput-absolute', 'auto', 'none')]
    [string]$MoveMode = 'auto',
    [ValidateSet('sendinput', 'postmessage', 'both')]
    [string]$ClickMode = 'sendinput',
    [int]$RunSeconds = 10,
    [int]$PostIntroWaitSec = 4,
    [switch]$NoLaunch,
    [switch]$AllowVisibleRuntime
)

$ErrorActionPreference = 'Stop'

if (-not $NoLaunch -and -not $AllowVisibleRuntime) {
    throw "This harness opens Windows Sandbox for a visible Clash95 runtime. Re-run with -AllowVisibleRuntime only after explicit user approval."
}

function ConvertTo-XmlText {
    param([string]$Value)
    return [System.Security.SecurityElement]::Escape($Value)
}

function Resolve-RequiredPath {
    param(
        [string]$Path,
        [string]$Description
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Description was not found: $Path"
    }
    return (Resolve-Path -LiteralPath $Path).Path
}

function New-SandboxCapturePlan {
    param([string]$Path, [string]$Repository, [string]$Prefix)
    $captureRoot = [System.IO.Path]::GetFullPath($Path)
    $repositoryRoot = [System.IO.Path]::GetFullPath($Repository).TrimEnd('\', '/')
    if ($captureRoot.TrimEnd('\', '/').Equals($repositoryRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
        $captureRoot.StartsWith($repositoryRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Sandbox captures must be written outside the repository.'
    }
    $runName = '{0}-{1}-{2}' -f $Prefix, (Get-Date -Format 'yyyyMMdd-HHmmss'), [Guid]::NewGuid().ToString('N')
    [pscustomobject]@{
        OutputRoot = $captureRoot
        HostRunDirectory = Join-Path $captureRoot $runName
        GuestRunDirectory = 'C:\ClashCaptures\run'
    }
}

$repo = Resolve-RequiredPath -Path $RepoRoot -Description 'Repository root'
$game = Resolve-RequiredPath -Path $GameRoot -Description 'Game root'
$python = Resolve-RequiredPath -Path $PythonHostPath -Description 'Python runtime'
$pythonDir = Split-Path -Parent $python
$pythonName = Split-Path -Leaf $python

$capturePlan = New-SandboxCapturePlan -Path $OutRoot -Repository $repo -Prefix 'sandbox'
$runHostDir = $capturePlan.HostRunDirectory
New-Item -ItemType Directory -Path $runHostDir | Out-Null

$entryHostPath = Join-Path $runHostDir 'sandbox-entry.ps1'
$wsbHostPath = Join-Path $runHostDir 'clash-hd-sandbox.wsb'
$summaryHostPath = Join-Path $runHostDir 'host-summary.json'
$runSandboxDir = $capturePlan.GuestRunDirectory
$entrySandboxPath = "$runSandboxDir\sandbox-entry.ps1"
$sandboxPython = "C:\HostPython\$pythonName"
$sandboxCandidate = "C:\Clash\$CandidateName"
$sandboxSmokeRoot = "$runSandboxDir\visual-smoke"
$sandboxCoverageJson = "$runSandboxDir\map-tile-coverage.json"

$entryScript = @"
`$ErrorActionPreference = 'Stop'
`$ProgressPreference = 'SilentlyContinue'
Start-Transcript -Path '$runSandboxDir\sandbox-run.log' -Force
try {
    `$Repo = 'C:\Repo'
    `$GameSource = 'C:\HostClash'
    `$GameWork = 'C:\Clash'
    `$Python = '$sandboxPython'
    `$Candidate = '$sandboxCandidate'
    `$Stage = '$Stage'

    if (-not (Test-Path -LiteralPath `$Python)) {
        throw "Mapped Python runtime not found: `$Python"
    }
    if (-not (Test-Path -LiteralPath (Join-Path `$GameSource 'clash95.exe'))) {
        throw "Mapped Clash install does not contain clash95.exe: `$GameSource"
    }

    if (Test-Path -LiteralPath `$GameWork) {
        Remove-Item -LiteralPath `$GameWork -Recurse -Force
    }
    New-Item -ItemType Directory -Path `$GameWork -Force | Out-Null
    Get-ChildItem -LiteralPath `$GameSource -Force |
        Where-Object { `$_.Name -notmatch '^(crack|keygen)\.exe$' } |
        Copy-Item -Destination `$GameWork -Recurse -Force

    `$baseHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path `$GameWork 'clash95.exe')).Hash
    & `$Python (Join-Path `$Repo 'patch_clash95_hd.py') --input (Join-Path `$GameWork 'clash95.exe') --output `$Candidate --stage `$Stage
    if (`$LASTEXITCODE -ne 0) {
        throw "patch_clash95_hd.py failed with exit code `$LASTEXITCODE"
    }
    `$candidateHash = (Get-FileHash -Algorithm SHA256 -LiteralPath `$Candidate).Hash

    New-Item -ItemType Directory -Path '$sandboxSmokeRoot' -Force | Out-Null
    `$smokeArgs = @(
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        (Join-Path `$Repo 'scripts\smoke\run_clash_visual_smoke.ps1'),
        '-Exe',
        `$Candidate,
        '-WorkDir',
        `$GameWork,
        '-Python',
        `$Python,
        '-OutRoot',
        '$sandboxSmokeRoot',
        '-Points',
        '$Points',
        '-MoveMode',
        '$MoveMode',
        '-ClickMode',
        '$ClickMode',
        '-RunSeconds',
        '$RunSeconds',
        '-PostIntroWaitSec',
        '$PostIntroWaitSec'
    )
    if ([bool]::Parse('$([bool]$AllowVisibleRuntime)')) {
        `$smokeArgs += '-AllowVisibleRuntime'
    }
    & powershell.exe @smokeArgs
    `$smokeExit = `$LASTEXITCODE

    `$latestSmoke = Get-ChildItem -LiteralPath '$sandboxSmokeRoot' -Directory -Filter 'visual-smoke-*' |
        Sort-Object LastWriteTime |
        Select-Object -Last 1
    `$coverageExit = `$null
    `$coverageFrame = `$null
    if (`$latestSmoke) {
        `$coverageFrame = Join-Path `$latestSmoke.FullName 'after-map-path.png'
        if (Test-Path -LiteralPath `$coverageFrame) {
            & `$Python (Join-Path `$Repo 'tools\map_tile_coverage.py') `$coverageFrame --write-json '$sandboxCoverageJson'
            `$coverageExit = `$LASTEXITCODE
        }
    }

    [pscustomobject]@{
        Stage = `$Stage
        GameWork = `$GameWork
        BaseSha256 = `$baseHash
        Candidate = `$Candidate
        CandidateSha256 = `$candidateHash
        SmokeExitCode = `$smokeExit
        LatestSmokeDirectory = if (`$latestSmoke) { `$latestSmoke.FullName } else { `$null }
        CoverageFrame = `$coverageFrame
        CoverageJson = '$sandboxCoverageJson'
        CoverageExitCode = `$coverageExit
        MoveMode = '$MoveMode'
        ClickMode = '$ClickMode'
        Note = 'Game files were copied only into the disposable sandbox VM; host C:\Clash was mapped read-only.'
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath '$runSandboxDir\sandbox-summary.json' -Encoding ASCII
}
catch {
    [pscustomobject]@{
        Error = `$_.Exception.Message
        Script = '$entrySandboxPath'
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath '$runSandboxDir\sandbox-error.json' -Encoding ASCII
    throw
}
finally {
    Stop-Transcript
}
"@

$entryScript | Set-Content -LiteralPath $entryHostPath -Encoding ASCII

$command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$entrySandboxPath`""
$wsb = @"
<Configuration>
  <VGpu>Enable</VGpu>
  <Networking>Default</Networking>
  <MappedFolders>
    <MappedFolder>
      <HostFolder>$(ConvertTo-XmlText $repo)</HostFolder>
      <SandboxFolder>C:\Repo</SandboxFolder>
      <ReadOnly>false</ReadOnly>
    </MappedFolder>
    <MappedFolder>
      <HostFolder>$(ConvertTo-XmlText $game)</HostFolder>
      <SandboxFolder>C:\HostClash</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
    <MappedFolder>
      <HostFolder>$(ConvertTo-XmlText $pythonDir)</HostFolder>
      <SandboxFolder>C:\HostPython</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
    <MappedFolder>
      <HostFolder>$(ConvertTo-XmlText $runHostDir)</HostFolder>
      <SandboxFolder>$(ConvertTo-XmlText $runSandboxDir)</SandboxFolder>
      <ReadOnly>false</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  <LogonCommand>
    <Command>$(ConvertTo-XmlText $command)</Command>
  </LogonCommand>
</Configuration>
"@

$wsb | Set-Content -LiteralPath $wsbHostPath -Encoding ASCII

$summary = [pscustomobject]@{
    RunDirectory = $runHostDir
    CaptureRoot = $capturePlan.OutputRoot
    CaptureMappedAs = $runSandboxDir
    Wsb = $wsbHostPath
    EntryScript = $entryHostPath
    RepoMappedAs = 'C:\Repo'
    GameMappedReadOnlyAs = 'C:\HostClash'
    SandboxGameWorkDir = 'C:\Clash'
    PythonMappedAs = "C:\HostPython\$pythonName"
    CandidateName = $CandidateName
    Stage = $Stage
    MoveMode = $MoveMode
    ClickMode = $ClickMode
    NoLaunch = [bool]$NoLaunch
}
$summary | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $summaryHostPath -Encoding ASCII
$summary | Format-List

if ($NoLaunch) {
    Write-Host "NoLaunch set; generated Windows Sandbox config only."
    return
}

$sandboxExe = Join-Path $env:WINDIR 'System32\WindowsSandbox.exe'
if (-not (Test-Path -LiteralPath $sandboxExe)) {
    throw "Windows Sandbox is not available. Enable the Windows feature 'Containers-DisposableClientVM', reboot, then run this script again."
}

Start-Process -FilePath $sandboxExe -ArgumentList "`"$wsbHostPath`""
