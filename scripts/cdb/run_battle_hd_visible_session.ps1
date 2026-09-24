<# Launch/own the approved expanded-battle debugger session. No UI automation.
   All window selection, activation, input and capture belong to the external
   computer-use controller. A stop.request file or deadline closes only the
   retained debugger and its exact candidate child. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Exe,
    [Parameter(Mandatory=$true)][string]$Probe,
    [Parameter(Mandatory=$true)][string]$Packet,
    [Parameter(Mandatory=$true)][string]$Approval,
    [Parameter(Mandatory=$true)][string]$SessionDir,
    [string]$Cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe',
    [Parameter(Mandatory=$true)][string]$Python,
    [ValidateRange(60,1800)][int]$TimeoutSeconds = 900,
    [switch]$ExecuteApproved
)
$ErrorActionPreference = 'Stop'
$expected = '99D92EC7C8F81DEBF60321DCC5C1B5872C96E3C485FA2BDD7D9332287B3C7E87'
$proxySha = 'B4CF172509083066EEE011FDB866F9A07C6CC4FA1F0CE53EC1F90E28CB5A28B1'
$stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlehd'
function Assert-NoReparse([string]$Value) {
    $cursor = [IO.Path]::GetFullPath($Value)
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Reparse point is not an isolated session path: $cursor"
            }
        }
        $parent = [IO.Path]::GetDirectoryName($cursor)
        if ($parent -eq $cursor) { break }
        $cursor = $parent
    }
}
function Resolve-File([string]$Value) {
    Assert-NoReparse $Value
    $item = Get-Item -LiteralPath $Value -Force
    if ($item.PSIsContainer) { throw 'Expected a file.' }
    $item.FullName
}
function File-Ref([string]$Value) {
    $resolved = Resolve-File $Value
    @{path=$resolved; sha256=(Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash}
}
function Write-Json([string]$Path, $Value) {
    $Value | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $Path -Encoding UTF8
}
function Assert-Approval($Record, [string]$CandidateSha, [string]$WrapperSha, [string]$StageName, [DateTimeOffset]$Now) {
    if ($Record.user_response -cnotin @('Yes', 'Approve visible rerun') -or $Record.candidate_sha256 -ne $CandidateSha -or
        $Record.wrapper_sha256 -ne $WrapperSha -or $Record.wrapper_mode -cne 'proxy-present' -or
        $Record.stage -cne $StageName -or $Record.resolution -cne '1280x720' -or
        $Record.scope -cne 'visible launch, foreground/cursor control, automated input and screenshots' -or
        [string]::IsNullOrWhiteSpace($Record.approval_question) -or
        [string]::IsNullOrWhiteSpace($Record.thread_id)) { throw 'Approval scope/identity mismatch.' }
    $recordTime = [DateTimeOffset]::Parse($Record.recorded_at_utc)
    if ($recordTime -gt $Now -or ($Now - $recordTime).TotalHours -gt 12) { throw 'Approval record is not fresh.' }
}
function Assert-ChildIdentity($Process, $Discovered, $Bound, [int]$ParentId, [string]$ExpectedPath) {
    # CIM truncates the kernel timestamp to microseconds. The retained handle
    # and repeated parent/path/time observation bind this particular child.
    $sameStart = [Math]::Abs(($Process.StartTime.ToUniversalTime() - $Discovered.CreationDate.ToUniversalTime()).Ticks) -lt 10
    if ($Process.Id -ne $Discovered.ProcessId -or $Process.Path -ine $ExpectedPath -or -not $sameStart -or
        $Bound.ProcessId -ne $Process.Id -or $Bound.ParentProcessId -ne $ParentId -or
        $Discovered.ParentProcessId -ne $ParentId -or $Bound.ExecutablePath -ine $ExpectedPath -or
        $Discovered.ExecutablePath -ine $ExpectedPath -or $Bound.CreationDate -ne $Discovered.CreationDate) {
        throw 'Candidate identity changed during process discovery.'
    }
}
function Stop-OwnedProcesses($CandidateProcess, $DebuggerProcess) {
    $result = @{candidate_stopped=$false; debugger_stopped=$false; errors=@()}
    $owned = @(@{name='candidate'; process=$CandidateProcess}, @{name='debugger'; process=$DebuggerProcess})
    # Signal both before waiting: a stopped debugger can delay debuggee exit.
    foreach ($entry in $owned) {
        if ($null -ne $entry.process) {
            try { if (-not $entry.process.HasExited) { $entry.process.Kill() } }
            catch { $result.errors += $entry.name + ' terminate: ' + $_.Exception.Message }
        }
    }
    foreach ($entry in $owned) {
        if ($null -ne $entry.process) {
            try { $result[$entry.name + '_stopped'] = $entry.process.WaitForExit(10000) }
            catch { $result.errors += $entry.name + ' wait: ' + $_.Exception.Message }
        }
    }
    return $result
}
$Exe = Resolve-File $Exe; $Probe = Resolve-File $Probe
$Packet = Resolve-File $Packet; $Approval = Resolve-File $Approval
$Cdb = Resolve-File $Cdb; $Python = Resolve-File $Python
$SessionDir = [IO.Path]::GetFullPath($SessionDir)
Assert-NoReparse $SessionDir
if (-not $Exe.StartsWith('C:\ClashTests\', [StringComparison]::OrdinalIgnoreCase) -or
    -not $SessionDir.StartsWith('C:\ClashTests\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Candidate and session must be isolated under C:\ClashTests.'
}
if (Test-Path -LiteralPath $SessionDir) { throw 'Session directory must be new.' }
$candidateRef = File-Ref $Exe
$wrapperRef = File-Ref (Join-Path (Split-Path $Exe) 'ddraw.dll')
if ($candidateRef.sha256 -ne $expected -or $wrapperRef.sha256 -ne $proxySha) {
    throw 'Unreviewed candidate or presenting proxy.'
}
$record = Get-Content -LiteralPath $Approval -Raw | ConvertFrom-Json
Assert-Approval $record $expected $proxySha $stage ([DateTimeOffset]::UtcNow)
$probeText = Get-Content -LiteralPath $Probe -Raw
if ($probeText -match 'SURFDUMP_BYPASS|r eip=0047bd73|r eip=0047bdbf') { throw 'Native acquisition bypass forbidden.' }
# Reconstruct the reviewed packet in memory. No candidate, save or probe is
# written by this verification, and no process other than Python is started.
$producer = Resolve-File (Join-Path $PSScriptRoot '..\..\tools\battle_hd_visible_probe.py')
$verifyPacket = @'
import importlib.util, json, sys
from pathlib import Path
producer, packet_path, candidate_path, probe_path = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('battle_hd_visible_verified', producer)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
packet = json.loads(packet_path.read_text(encoding='utf-8-sig'))
if packet.get('schema') != 'clash95_battle_hd_visible_probe_v1':
    raise ValueError('unexpected packet schema')
if Path(packet['candidate_path']).resolve() != candidate_path.resolve() or Path(packet['probe_path']).resolve() != probe_path.resolve():
    raise ValueError('packet candidate/probe path mismatch')
original, save, snapshot = (Path(packet[key]) for key in ('original_path', 'save_path', 'snapshot_path'))
if save.resolve() != (candidate_path.parent / 'save' / '0.dat').resolve():
    raise ValueError('packet save is not the candidate-private runtime slot0')
script, rebuilt = module.build_probe(original.read_bytes(), candidate_path.read_bytes(), save.read_bytes(), stage=packet['stage'], resolution=packet['resolution'])
if any(packet.get(key) != value for key, value in rebuilt.items()):
    raise ValueError('packet differs from exact producer reconstruction')
if probe_path.read_bytes() != script.encode('ascii'):
    raise ValueError('probe differs from exact producer reconstruction')
expected_snapshot = module.snapshot_script().encode('ascii')
if snapshot.read_bytes() != expected_snapshot or packet.get('snapshot_sha256') != module.sha(expected_snapshot):
    raise ValueError('snapshot differs from exact producer reconstruction')
print('battle HD packet verified without runtime')
'@
$verificationOutput = @(& $Python -B -c $verifyPacket $producer $Packet $Exe $Probe 2>&1)
if ($LASTEXITCODE -ne 0) { throw ('Exact producer packet verification failed: ' + ($verificationOutput -join ' ')) }
$packetRecord = Get-Content -LiteralPath $Packet -Raw | ConvertFrom-Json
foreach ($path in @($packetRecord.original_path, $packetRecord.save_path, $packetRecord.snapshot_path)) { Assert-NoReparse $path }
$plan = [ordered]@{
    schema_version=1; executed=$false; stage=$stage; resolution='1280x720'
    candidate=$candidateRef; wrapper=$wrapperRef; wrapper_mode='proxy-present'
    wrapper_config=(File-Ref (Join-Path (Split-Path $Exe) 'dxcfg.ini'))
    wrapper_config_usage='retained provenance only; presenting proxy ignores dxcfg.ini'
    wrapper_build_manifest=(File-Ref (Join-Path (Split-Path $Exe) 'ddraw_surfdump_proxy.build.json'))
    probe=(File-Ref $Probe); packet=(File-Ref $Packet); approval=(File-Ref $Approval)
    original=(File-Ref $packetRecord.original_path); save=(File-Ref $packetRecord.save_path); snapshot=(File-Ref $packetRecord.snapshot_path)
    cdb=(File-Ref $Cdb); runner=(File-Ref $PSCommandPath); producer=(File-Ref $producer); python=(File-Ref $Python)
    session_dir=$SessionDir; timeout_seconds=$TimeoutSeconds
    ui_controller='SkyJS; runner performs no UI operations'
    input_classification='automated input, if subsequently performed; manual evidence unavailable'
    child_environment=@{__COMPAT_LAYER='HIGHDPIAWARE'; CLASH_PROXY_PRESENT='1'}
    debugger_launch=@{use_shell_execute=$false; create_no_window=$true; window_style='Normal'}
}
if (-not $ExecuteApproved) { $plan | ConvertTo-Json -Depth 15; exit 0 }
New-Item -ItemType Directory -Path $SessionDir | Out-Null
Write-Json (Join-Path $SessionDir 'launch-plan.json') $plan
Copy-Item -LiteralPath $Approval -Destination (Join-Path $SessionDir 'user-approval.json')
Copy-Item -LiteralPath $Probe -Destination (Join-Path $SessionDir 'probe.cdb')
Copy-Item -LiteralPath $Packet -Destination (Join-Path $SessionDir 'probe-packet.json')
$savedEnvironment = @{}
Get-ChildItem Env: | Where-Object { $_.Name -like 'CLASH_PROXY_*' -or $_.Name -eq '__COMPAT_LAYER' } | ForEach-Object {
    $savedEnvironment[$_.Name]=$_.Value
}
$debugger = $null; $candidate = $null; $candidateIdentity = $null; $failure = $null
$stopReason = 'error'
$started = [DateTime]::UtcNow
$cleanup = @{candidate_stopped=$false; debugger_stopped=$false; errors=@()}
try {
    foreach ($name in $savedEnvironment.Keys) { [Environment]::SetEnvironmentVariable($name,$null,'Process') }
    $env:__COMPAT_LAYER='HIGHDPIAWARE'; $env:CLASH_PROXY_PRESENT='1'
    foreach ($reference in @($plan.candidate, $plan.wrapper, $plan.wrapper_config, $plan.wrapper_build_manifest, $plan.cdb, $plan.producer, $plan.probe, $plan.packet, $plan.approval, $plan.original, $plan.save, $plan.snapshot)) {
        if ((File-Ref $reference.path).sha256 -ne $reference.sha256) { throw 'Launch artifact changed after verification.' }
    }
    if ((File-Ref (Join-Path $SessionDir 'probe.cdb')).sha256 -ne $plan.probe.sha256 -or
        (File-Ref (Join-Path $SessionDir 'probe-packet.json')).sha256 -ne $plan.packet.sha256 -or
        (File-Ref (Join-Path $SessionDir 'user-approval.json')).sha256 -ne $plan.approval.sha256) { throw 'Session artifact copy differs.' }
    if ((File-Ref $packetRecord.save_path).sha256 -ne $packetRecord.save_sha256) { throw 'Private runtime slot0 changed.' }
    $log = Join-Path $SessionDir 'cdb.log'
    $startup = Join-Path $SessionDir 'probe.cdb'
    $arguments = '-hd -logo "{0}" -cf "{1}" "{2}"' -f $log,$startup,$Exe
    # Hide only the debugger console. A Hidden startup show-state could affect
    # the debuggee's first ShowWindow call; that startup hypothesis is unproven.
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $Cdb
    $startInfo.Arguments = $arguments
    $startInfo.WorkingDirectory = Split-Path $Exe
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.WindowStyle = [Diagnostics.ProcessWindowStyle]::Normal
    $debugger = [Diagnostics.Process]::Start($startInfo)
    # Retain handles; process IDs alone are never used for termination.
    $null = $debugger.Handle
    if ($debugger.Path -ine $Cdb -or $debugger.StartTime.ToUniversalTime() -lt $started) { throw 'Debugger identity mismatch.' }
    $deadline = $started.AddSeconds($TimeoutSeconds)
    $stopReason = 'deadline'
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($debugger.HasExited) { $stopReason='debugger_exit'; break }
        if ($null -eq $candidate) {
            $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($debugger.Id)" | Where-Object {
                $_.ExecutablePath -ieq $Exe -and $_.CreationDate.ToUniversalTime() -ge $started
            })
            if ($children.Count -gt 1) { throw 'Ambiguous exact debugger child.' }
            if ($children.Count -eq 1) {
                $discoveredProcess = Get-Process -Id $children[0].ProcessId
                try {
                    $null = $discoveredProcess.Handle
                    $boundChild = Get-CimInstance Win32_Process -Filter "ProcessId=$($discoveredProcess.Id)"
                    Assert-ChildIdentity $discoveredProcess $children[0] $boundChild $debugger.Id $Exe
                }
                catch {
                    try { $discoveredProcess.Dispose() } catch { }
                    throw
                }
                $candidate = $discoveredProcess
                $candidateIdentity = @{pid=$candidate.Id; path=$candidate.Path; started_at=$candidate.StartTime.ToUniversalTime().ToString('o'); parent_pid=$debugger.Id}
                Write-Json (Join-Path $SessionDir 'owned-processes.json') @{
                    debugger=@{pid=$debugger.Id; path=$debugger.Path; started_at=$debugger.StartTime.ToUniversalTime().ToString('o')}
                    candidate=$candidateIdentity
                }
            }
        }
        if (Test-Path -LiteralPath (Join-Path $SessionDir 'stop.request')) { $stopReason='stop_request'; break }
        Start-Sleep -Milliseconds 500
    }
    if ($null -eq $candidateIdentity) { throw 'Exact candidate child was not discovered.' }
} catch { $stopReason='error'; $failure=$_.Exception.Message; Write-Warning $failure }
finally {
    $cleanup = Stop-OwnedProcesses $candidate $debugger
    try {
        Get-ChildItem Env: | Where-Object { $_.Name -like 'CLASH_PROXY_*' -or $_.Name -eq '__COMPAT_LAYER' } | ForEach-Object {
            [Environment]::SetEnvironmentVariable($_.Name,$null,'Process')
        }
        foreach ($name in $savedEnvironment.Keys) { [Environment]::SetEnvironmentVariable($name,$savedEnvironment[$name],'Process') }
    } catch { $cleanup.errors += 'environment: ' + $_.Exception.Message }
    Write-Json (Join-Path $SessionDir 'execution.json') @{
        executed=$true; started_at=$started.ToString('o'); ended_at=[DateTime]::UtcNow.ToString('o')
        launch_plan=(File-Ref (Join-Path $SessionDir 'launch-plan.json'))
        candidate=$candidateIdentity; cleanup=$cleanup; failure=$failure; stop_reason=$stopReason
        acceptance_passed=$false; manual_input_proven=$false
    }
}
if ($failure -or $cleanup.errors.Count -gt 0 -or -not $cleanup.candidate_stopped -or -not $cleanup.debugger_stopped) { exit 1 }
