$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Start-Transcript -Path 'C:\Repo\captures\sandbox-20260424-091715\sandbox-run.log' -Force
try {
    $Repo = 'C:\Repo'
    $GameSource = 'C:\HostClash'
    $GameWork = 'C:\Clash'
    $Python = 'C:\HostPython\python.exe'
    $Candidate = 'C:\Clash\clash95_hd_sandbox_candidate.exe'
    $Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch'

    if (-not (Test-Path -LiteralPath $Python)) {
        throw "Mapped Python runtime not found: $Python"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $GameSource 'clash95.exe'))) {
        throw "Mapped Clash install does not contain clash95.exe: $GameSource"
    }

    if (Test-Path -LiteralPath $GameWork) {
        Remove-Item -LiteralPath $GameWork -Recurse -Force
    }
    New-Item -ItemType Directory -Path $GameWork -Force | Out-Null
    Get-ChildItem -LiteralPath $GameSource -Force |
        Where-Object { $_.Name -notmatch '^(crack|keygen)\.exe$' } |
        Copy-Item -Destination $GameWork -Recurse -Force

    $baseHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $GameWork 'clash95.exe')).Hash
    & $Python (Join-Path $Repo 'patch_clash95_hd.py') --input (Join-Path $GameWork 'clash95.exe') --output $Candidate --stage $Stage
    if ($LASTEXITCODE -ne 0) {
        throw "patch_clash95_hd.py failed with exit code $LASTEXITCODE"
    }
    $candidateHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Candidate).Hash

    New-Item -ItemType Directory -Path 'C:\Repo\captures\sandbox-20260424-091715\visual-smoke' -Force | Out-Null
    $smokeArgs = @(
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        (Join-Path $Repo 'run_clash_visual_smoke.ps1'),
        '-Exe',
        $Candidate,
        '-WorkDir',
        $GameWork,
        '-Python',
        $Python,
        '-OutRoot',
        'C:\Repo\captures\sandbox-20260424-091715\visual-smoke',
        '-Points',
        '320,245;448,245;648,49;760,201',
        '-MoveMode',
        'auto',
        '-ClickMode',
        'sendinput',
        '-RunSeconds',
        '10',
        '-PostIntroWaitSec',
        '4'
    )
    & powershell.exe @smokeArgs
    $smokeExit = $LASTEXITCODE

    $latestSmoke = Get-ChildItem -LiteralPath 'C:\Repo\captures\sandbox-20260424-091715\visual-smoke' -Directory -Filter 'visual-smoke-*' |
        Sort-Object LastWriteTime |
        Select-Object -Last 1
    $coverageExit = $null
    $coverageFrame = $null
    if ($latestSmoke) {
        $coverageFrame = Join-Path $latestSmoke.FullName 'after-map-path.png'
        if (Test-Path -LiteralPath $coverageFrame) {
            & $Python (Join-Path $Repo 'tools\map_tile_coverage.py') $coverageFrame --write-json 'C:\Repo\captures\sandbox-20260424-091715\map-tile-coverage.json'
            $coverageExit = $LASTEXITCODE
        }
    }

    [pscustomobject]@{
        Stage = $Stage
        GameWork = $GameWork
        BaseSha256 = $baseHash
        Candidate = $Candidate
        CandidateSha256 = $candidateHash
        SmokeExitCode = $smokeExit
        LatestSmokeDirectory = if ($latestSmoke) { $latestSmoke.FullName } else { $null }
        CoverageFrame = $coverageFrame
        CoverageJson = 'C:\Repo\captures\sandbox-20260424-091715\map-tile-coverage.json'
        CoverageExitCode = $coverageExit
        MoveMode = 'auto'
        ClickMode = 'sendinput'
        Note = 'Game files were copied only into the disposable sandbox; host C:\Clash was mapped read-only.'
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath 'C:\Repo\captures\sandbox-20260424-091715\sandbox-summary.json' -Encoding ASCII
}
catch {
    [pscustomobject]@{
        Error = $_.Exception.Message
        Script = 'C:\Repo\captures\sandbox-20260424-091715\sandbox-entry.ps1'
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath 'C:\Repo\captures\sandbox-20260424-091715\sandbox-error.json' -Encoding ASCII
    throw
}
finally {
    Stop-Transcript
}
