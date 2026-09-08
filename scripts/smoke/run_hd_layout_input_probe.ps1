[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Python,
    [string]$Candidate, [string]$Stage, [string]$Wrapper, [string]$WrapperConfig,
    [string]$CandidateManifest,
    [ValidateSet('manual_directinput','win32_sendinput_relative')][string]$InputMethod = 'manual_directinput',
    [ValidateSet('proxy-present','gog')][string]$WrapperMode = 'proxy-present',
    [string]$Cdb, [string]$OutputDir, [string]$RunId,
    [ValidateRange(30,900)][int]$TimeoutSeconds = 300,
    [string]$WritePlan, [string]$Plan, [string]$Approval,
    [switch]$Execute, [switch]$AllowVisibleRuntime
)
$ErrorActionPreference = 'Stop'
# Safe by default: Python planning only reads files. Neither this adapter nor
# its dry-run path inspects processes, windows, input, or the screen.
if ($Execute -and (-not $AllowVisibleRuntime -or -not $Plan -or -not $Approval)) {
    throw 'Execution requires -Execute -AllowVisibleRuntime -Plan and fresh explicit user -Approval.'
}
if (-not $Execute -and ($AllowVisibleRuntime -or $Approval)) {
    throw 'Runtime flags require -Execute.'
}
$tool = Join-Path $PSScriptRoot '..\..\tools\hd_layout_observation_manifest.py'
$arguments = @('-B', $tool)
if ($Plan) { $arguments += @('--plan', $Plan) }
else {
    $arguments += @('--candidate', $Candidate, '--stage', $Stage, '--wrapper', $Wrapper,
        '--wrapper-config', $WrapperConfig, '--wrapper-mode', $WrapperMode,
        '--cdb', $Cdb, '--output-dir', $OutputDir, '--run-id', $RunId,
        '--timeout-seconds', [string]$TimeoutSeconds)
    if ($CandidateManifest) { $arguments += @('--candidate-manifest', $CandidateManifest, '--input-method', $InputMethod) }
    elseif ($InputMethod -ne 'manual_directinput') { throw 'Relative-input observation requires the complete candidate manifest.' }
}
if ($WritePlan) { $arguments += @('--write-plan', $WritePlan) }
if ($Execute) { $arguments += @('--execute', '--allow-visible-runtime', '--approval', $Approval) }
& $Python @arguments
exit $LASTEXITCODE
