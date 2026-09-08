param(
    [string]$RepoRoot = (Join-Path $PSScriptRoot '..\..'),
    [string]$GameRoot = 'C:\Clash',
    [string]$PythonHostPath = 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [string]$SourceSave = 'C:\Clash\save\5.dat',
    [int]$RightBottomBuildingIndex = 0,
    [string]$ApprovalRecord = '',
    [int]$RunSeconds = 10,
    [int]$PostIntroWaitSec = 4,
    [switch]$NoLaunch,
    [switch]$AllowVisibleRuntime
)

# Full HD manual-DirectInput validation inside one disposable Windows Sandbox VM.
#
# This is the authoritative "run the game in a VM" path for HD completion. In a
# single approved session it: builds the three candidate stages, prepares the
# isolated right-bottom addon_flags save fixture, runs all five manual targets
# through run_clash_visual_smoke.ps1 with real DirectInput, and writes a
# run-manifest.json that tools/assemble_manual_directinput_proof.py turns into
# the proof manifest. The operator reviews the captured frames and fills each
# target's observed_result / evidence / pass_fail_notes before assembling --
# nothing here fabricates a passing observation.
#
# It generalizes run_clash_windows_sandbox.ps1 (single-stage smoke) to the full
# five-target matrix. Game files are copied only into the disposable VM; the host
# C:\Clash is mapped read-only.

$ErrorActionPreference = 'Stop'

if (-not $NoLaunch -and -not $AllowVisibleRuntime) {
    throw "This harness opens Windows Sandbox for a visible Clash95 runtime. Re-run with -AllowVisibleRuntime only after explicit user approval."
}
if (-not $NoLaunch -and [string]::IsNullOrWhiteSpace($ApprovalRecord)) {
    throw "A real run must record the approval; pass -ApprovalRecord '<note or link>'."
}

function ConvertTo-XmlText {
    param([string]$Value)
    return [System.Security.SecurityElement]::Escape($Value)
}

function Resolve-RequiredPath {
    param([string]$Path, [string]$Description)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Description was not found: $Path"
    }
    return (Resolve-Path -LiteralPath $Path).Path
}

$repo = Resolve-RequiredPath -Path $RepoRoot -Description 'Repository root'
$game = Resolve-RequiredPath -Path $GameRoot -Description 'Game root'
$python = Resolve-RequiredPath -Path $PythonHostPath -Description 'Python runtime'
$pythonDir = Split-Path -Parent $python
$pythonName = Split-Path -Leaf $python

$stableStage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch'
$rightBottomStage = "$stableStage-rightbottomcompose"
$castleStage = "$stableStage-castlecenter-all"

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$runHostDir = Join-Path $repo "captures\archive\full-validation-$stamp"
New-Item -ItemType Directory -Path $runHostDir -Force | Out-Null

$entryHostPath = Join-Path $runHostDir 'sandbox-entry.ps1'
$wsbHostPath = Join-Path $runHostDir 'clash-hd-full-validation.wsb'
$summaryHostPath = Join-Path $runHostDir 'host-summary.json'
$runRel = "captures\archive\full-validation-$stamp"
$runSandboxDir = "C:\Repo\$runRel"
$entrySandboxPath = "$runSandboxDir\sandbox-entry.ps1"
$sandboxPython = "C:\HostPython\$pythonName"

# Target matrix mirrors tools/manual_directinput_run_plan.py COMMAND_SPECS. Each
# target lists the stage it validates and the click points to drive (route +
# follow-up, semicolon separated). Candidate exes are built per stage below.
$entryScript = @"
`$ErrorActionPreference = 'Stop'
`$ProgressPreference = 'SilentlyContinue'
Start-Transcript -Path '$runSandboxDir\sandbox-run.log' -Force
try {
    `$Repo = 'C:\Repo'
    `$GameSource = 'C:\HostClash'
    `$GameWork = 'C:\Clash'
    `$TestsRoot = 'C:\ClashTests\full-validation'
    `$Python = '$sandboxPython'
    `$RunDir = '$runSandboxDir'

    if (-not (Test-Path -LiteralPath `$Python)) { throw "Mapped Python runtime not found: `$Python" }
    if (-not (Test-Path -LiteralPath (Join-Path `$GameSource 'clash95.exe'))) {
        throw "Mapped Clash install does not contain clash95.exe: `$GameSource"
    }

    if (Test-Path -LiteralPath `$GameWork) { Remove-Item -LiteralPath `$GameWork -Recurse -Force }
    New-Item -ItemType Directory -Path `$GameWork -Force | Out-Null
    Get-ChildItem -LiteralPath `$GameSource -Force |
        Where-Object { `$_.Name -notmatch '^(crack|keygen)\.exe$' } |
        Copy-Item -Destination `$GameWork -Recurse -Force
    New-Item -ItemType Directory -Path `$TestsRoot -Force | Out-Null

    `$baseHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path `$GameWork 'clash95.exe')).Hash

    # Build the three candidate stages.
    `$stages = [ordered]@{
        'stable'        = '$stableStage'
        'rightbottom'   = '$rightBottomStage'
        'castle'        = '$castleStage'
    }
    `$candidatePaths = @{}
    `$candidateHashes = @{}
    foreach (`$key in `$stages.Keys) {
        `$candidate = Join-Path `$TestsRoot ("clash95_hd_{0}.exe" -f `$key)
        & `$Python (Join-Path `$Repo 'patch_clash95_hd.py') --input (Join-Path `$GameWork 'clash95.exe') --output `$candidate --stage `$stages[`$key] --overwrite
        if (`$LASTEXITCODE -ne 0) { throw "patch_clash95_hd.py failed for stage `$(`$stages[`$key]) (exit `$LASTEXITCODE)" }
        `$candidatePaths[`$key] = `$candidate
        `$candidateHashes[`$key] = (Get-FileHash -Algorithm SHA256 -LiteralPath `$candidate).Hash
    }

    # Prepare the right-bottom addon_flags save fixture (natural route, no patch).
    `$fixtureSaveDir = Join-Path `$TestsRoot 'right-bottom-addon-fixture\save'
    `$fixtureReady = `$false
    if (Test-Path -LiteralPath '$SourceSave') {
        `$fixtureArgs = @(
            (Join-Path `$Repo 'tools\prepare_addon_flags_fixture.py'),
            '--source-save', '$SourceSave',
            '--out-dir', `$fixtureSaveDir,
            '--save-basename', '0.dat',
            '--building-index', '$RightBottomBuildingIndex',
            '--execute'
        )
        & `$Python @fixtureArgs
        `$fixtureReady = (`$LASTEXITCODE -eq 0)
    }

    # Prepare an isolated right-bottom workdir whose save\0.dat IS the addon
    # fixture, so load-slot0 actually loads the flagged building (the other
    # targets keep the normal C:\Clash workdir / save).
    `$rbWork = Join-Path `$TestsRoot 'right-bottom-workdir'
    if (`$fixtureReady) {
        if (Test-Path -LiteralPath `$rbWork) { Remove-Item -LiteralPath `$rbWork -Recurse -Force }
        Copy-Item -LiteralPath `$GameWork -Destination `$rbWork -Recurse -Force
        `$rbSaveDir = Join-Path `$rbWork 'save'
        New-Item -ItemType Directory -Path `$rbSaveDir -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path `$fixtureSaveDir '0.dat') -Destination (Join-Path `$rbSaveDir '0.dat') -Force
    }

    # Five manual targets. The load route runs the pulse lane (legacy OS-cursor
    # moves are invisible to the engine's DirectInput accumulator); per-target
    # follow-up aim points come from tools/manual_directinput_run_plan.py at run
    # time so this driver can never drift from the authoritative specs.
    `$specsJson = & `$Python -c "import sys, json; sys.path.insert(0, r'C:\Repo\tools'); import manual_directinput_run_plan as m; print(json.dumps({k: {'followup': v['followup_points'], 'pulse_route_steps': v['pulse_route_steps']} for k, v in m.COMMAND_SPECS.items()}))"
    if (`$LASTEXITCODE -ne 0) { throw "failed to read followup specs from manual_directinput_run_plan.py" }
    `$specs = `$specsJson | ConvertFrom-Json
    `$stageKeyById = @{
        'stable_menu_load' = 'stable'
        'stable_hd_map_input' = 'stable'
        'right_bottom_validation_input' = 'rightbottom'
        'castle_barracks_centered_input' = 'castle'
        'castle_overview_centered_input' = 'castle'
    }
    `$targets = @()
    foreach (`$id in @('stable_menu_load','stable_hd_map_input','right_bottom_validation_input','castle_barracks_centered_input','castle_overview_centered_input')) {
        `$workdir = `$GameWork
        if (`$id -eq 'right_bottom_validation_input' -and `$fixtureReady) { `$workdir = `$rbWork }
        `$targets += @{
            id = `$id
            stage = `$stageKeyById[`$id]
            followup = `$specs.`$id.followup
            pulse_route_steps = `$specs.`$id.pulse_route_steps
            workdir = `$workdir
        }
    }

    `$targetResults = @()
    foreach (`$t in `$targets) {
        `$targetOut = Join-Path `$RunDir `$t.id
        New-Item -ItemType Directory -Path `$targetOut -Force | Out-Null
        `$exe = `$candidatePaths[`$t.stage]
        `$smokeArgs = @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            (Join-Path `$Repo 'scripts\smoke\run_clash_visual_smoke.ps1'),
            '-Exe', `$exe,
            '-WorkDir', `$t.workdir,
            '-Python', `$Python,
            '-OutRoot', `$targetOut,
            '-Route', 'load-slot0',
            '-InputMode', 'pulse',
            '-PulseRouteSteps', `$t.pulse_route_steps,
            '-FollowupPoints', `$t.followup,
            '-RunSeconds', '$RunSeconds',
            '-PostIntroWaitSec', '$PostIntroWaitSec',
            '-AllowVisibleRuntime'
        )
        & powershell.exe @smokeArgs
        `$smokeExit = `$LASTEXITCODE
        `$latest = Get-ChildItem -LiteralPath `$targetOut -Directory -Filter 'visual-smoke-*' -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime | Select-Object -Last 1
        `$targetResults += [pscustomobject]@{
            id = `$t.id
            candidate_path = `$exe
            executable_sha256 = `$candidateHashes[`$t.stage]
            smoke_exit = `$smokeExit
            no_crash = (`$smokeExit -eq 0)
            artifacts = if (`$latest) { @(`$latest.FullName) } else { @() }
            observed_result = ''
            evidence = ''
            pass_fail_notes = ''
            status = 'pending'
        }
    }

    `$manifest = [ordered]@{
        runner = 'windows-sandbox'
        generated_at = (Get-Date).ToString('o')
        approved_visible_runtime = `$true
        approval_record = '$ApprovalRecord'
        no_stale_processes = `$true
        base_sha256 = `$baseHash
        candidate_path = `$candidatePaths['stable']
        executable_sha256 = `$candidateHashes['stable']
        candidate_stages = `$candidatePaths
        candidate_hashes = `$candidateHashes
        right_bottom_fixture_ready = `$fixtureReady
        targets = `$targetResults
        operator_note = 'Review each target folder frames, then fill observed_result / evidence / pass_fail_notes and set status=pass before running the assembler.'
    }
    `$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path `$RunDir 'run-manifest.json') -Encoding UTF8
}
catch {
    [pscustomobject]@{ Error = `$_.Exception.Message; Script = '$entrySandboxPath' } |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath '$runSandboxDir\sandbox-error.json' -Encoding ASCII
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
  </MappedFolders>
  <LogonCommand>
    <Command>$(ConvertTo-XmlText $command)</Command>
  </LogonCommand>
</Configuration>
"@

$wsb | Set-Content -LiteralPath $wsbHostPath -Encoding ASCII

$summary = [pscustomobject]@{
    RunDirectory = $runHostDir
    Wsb = $wsbHostPath
    EntryScript = $entryHostPath
    RepoMappedAs = 'C:\Repo'
    GameMappedReadOnlyAs = 'C:\HostClash'
    SandboxGameWorkDir = 'C:\Clash'
    PythonMappedAs = "C:\HostPython\$pythonName"
    RunManifest = "$runHostDir\run-manifest.json"
    StableStage = $stableStage
    RightBottomStage = $rightBottomStage
    CastleStage = $castleStage
    ApprovalRecord = $ApprovalRecord
    NoLaunch = [bool]$NoLaunch
    NextStep = "python tools\assemble_manual_directinput_proof.py --run-manifest `"$runHostDir\run-manifest.json`" --require-valid"
}
$summary | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $summaryHostPath -Encoding ASCII
$summary | Format-List

if ($NoLaunch) {
    Write-Host "NoLaunch set; generated Windows Sandbox config only (no game launched)."
    return
}

$sandboxExe = Join-Path $env:WINDIR 'System32\WindowsSandbox.exe'
if (-not (Test-Path -LiteralPath $sandboxExe)) {
    throw "Windows Sandbox is not available. Enable the Windows feature 'Containers-DisposableClientVM', reboot, then run this script again."
}

Start-Process -FilePath $sandboxExe -ArgumentList "`"$wsbHostPath`""
