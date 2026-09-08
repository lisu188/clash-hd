<# Controlled initial tactical-battle capture. Offline plan by default.
   E0 is scratch evidence, not a final composed primary screenshot.
   Retained-handle lifecycle helpers come from one exact reviewed source.
#>
[CmdletBinding()]
param(
 [string]$Original='C:\Clash\clash95.exe',
 [Parameter(Mandatory=$true)][string]$InputCandidate,
 [Parameter(Mandatory=$true)][string]$ProxyBuildManifest,
 [Parameter(Mandatory=$true)][string]$WorkDir,
 [Parameter(Mandatory=$true)][string]$CandidateDir,
 [Parameter(Mandatory=$true)][string]$OutDir,
 [ValidateSet('constructed_slot0_unit0_vs_unit4')][string]$Route='constructed_slot0_unit0_vs_unit4',
 [string]$Resolution='1024x768',
 [switch]$MinimapViewport,
 [switch]$Execute
)
$ErrorActionPreference='Stop'
$OutputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=$OutputEncoding
$script:RepoRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$script:Stage='gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-modalcanvas-validation'
$script:LifecyclePath=Join-Path $PSScriptRoot 'run_framed_modal_canvas_capture.ps1'
$script:LifecycleSha='8873f885d7a5405a8a570e70e3b09e31081dcbd339b33b9e92b465274b58d9ba'
if ((Get-FileHash -LiteralPath $script:LifecyclePath -Algorithm SHA256).Hash.ToLowerInvariant() -cne $script:LifecycleSha) {
 throw 'Reviewed hidden lifecycle source changed.'
}
# Import definitions only. Never dot-source the old host or run its main path.
$tokens=$null;$parseErrors=$null
$lifecycleAst=[Management.Automation.Language.Parser]::ParseFile($script:LifecyclePath,[ref]$tokens,[ref]$parseErrors)
if ($parseErrors.Count) {throw 'Reviewed lifecycle source does not parse.'}
$names=@('Get-CanvasHash','Get-CanvasCandidateName','Resolve-CanvasPath','Invoke-CanvasPythonJson',
 'Read-CanvasLog','Read-CanvasLogBytes','Get-CanvasBytesHash','Select-CanvasChildren','Initialize-CanvasNative',
 'Get-CanvasHandleIdentity','ConvertTo-CanvasArgument','Get-CanvasLaunchCommand','Start-CanvasHidden',
 'Find-CanvasOwnedChildren','Read-CanvasMemory','Stop-CanvasOwned','Close-CanvasDesktop',
 'Test-CanvasProcessExited','Write-CanvasJson')
foreach ($name in $names) {
 $nodes=@($lifecycleAst.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq $name},$true))
 if ($nodes.Count -ne 1) {throw ('Missing/ambiguous lifecycle definition: '+$name)}
 . ([scriptblock]::Create($nodes[0].Extent.Text))
}

function New-BattleCapturePlan {
    param($Options)
    $originalPath = Resolve-CanvasPath $Options.Original -Kind file
    $inputPath = Resolve-CanvasPath $Options.InputCandidate -Root 'C:\ClashTests' -Kind file
    $manifestPath = Resolve-CanvasPath $Options.ProxyBuildManifest -Root 'C:\ClashTests' -Kind file
    $workingPath = Resolve-CanvasPath $Options.WorkDir -Root 'C:\ClashTests' -Kind directory
    $candidateDirectory = Resolve-CanvasPath $Options.CandidateDir -Root 'C:\ClashTests' -Kind new
    $outputDirectory = Resolve-CanvasPath $Options.OutDir -Root 'C:\ClashCaptures' -Kind new
    if ($outputDirectory -match '[^\x20-\x7e]' -or $outputDirectory -match '[$";\r\n]' -or $outputDirectory.Length -gt 3500) {
        throw 'Canonical command files require bounded ASCII paths without argument tokens.'
    }
    if ($Options.Resolution -notmatch '^([0-9]{3,4})x([0-9]{3,4})$') { throw 'Resolution must be canonical WxH.' }
    $width = [int]$Matches[1]; $height = [int]$Matches[2]
    if ($width -lt 640 -or $height -lt 480 -or $width -gt 8192 -or $height -gt 8192 -or ($width % 2) -or ($height % 2)) { throw 'Unsupported physical resolution.' }
    $python = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    $cdb = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe'
    $python = Resolve-CanvasPath $python -Kind file
    $cdb = Resolve-CanvasPath $cdb -Kind file
    $trace = Resolve-CanvasPath (Join-Path $script:RepoRoot 'tools\framed_battle_initial_trace.py') -Kind file
    $producer = Resolve-CanvasPath (Join-Path $script:RepoRoot 'tools\framed_battle_initial_probe.py') -Kind file
    $converter = Resolve-CanvasPath (Join-Path $script:RepoRoot 'tools\cdb_surface_dump_to_png.py') -Kind file
    $proxySource = Resolve-CanvasPath (Join-Path $script:RepoRoot 'src\ddraw_surfdump_proxy\ddraw_surfdump_proxy.cpp') -Kind file
    $manifest = [IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json
    $proxyOutput = Resolve-CanvasPath ([string]$manifest.output) -Root 'C:\ClashTests' -Kind file
    $sourceHash = Get-CanvasHash $proxySource
    $proxyHash = Get-CanvasHash $proxyOutput
    if ($manifest.generated_by -cne 'clash-hd-surface-dump-proxy' -or
        [IO.Path]::GetFullPath([string]$manifest.source) -ine $proxySource -or
        $manifest.source_sha256 -inotmatch '^[a-f0-9]{64}$' -or $manifest.source_sha256 -ine $sourceHash -or
        $manifest.output_sha256 -inotmatch '^[a-f0-9]{64}$' -or $manifest.output_sha256 -ine $proxyHash -or
        [IO.Path]::GetFileName($proxyOutput) -ine 'ddraw.dll') { throw 'Proxy manifest does not authenticate the current source and binary.' }
    $savePath=Resolve-CanvasPath (Join-Path $workingPath 'save\0.dat') -Root $workingPath -Kind file
    $saveHash=Get-CanvasHash $savePath
    if ($saveHash -cne '4f2182409d209985a527f07c4116b19e44332416698d6acb0a3d35ae68db8a89') {throw 'The isolated slot0 save differs from the approved fixture.'}
    $candidateHash = Get-CanvasHash $inputPath
    $prepareArgs = @($trace,'--prepare','--original',$originalPath,'--candidate',$inputPath,
        '--candidate-sha256',$candidateHash,'--stage',$script:Stage,'--resolution',$Options.Resolution,
        '--route',$Options.Route,'--save',$savePath)
    if ($Options.MinimapViewport) { $prepareArgs += '--minimap-viewport' }
    $prepared = Invoke-CanvasPythonJson $python $prepareArgs
    if ($prepared.packet.prepared -isnot [bool] -or -not $prepared.packet.prepared -or
        $prepared.packet.candidate_sha256 -cne $candidateHash -or $prepared.packet.stage -cne $script:Stage -or
        $prepared.packet.resolution -cne $Options.Resolution -or $prepared.packet.save_sha256 -cne $saveHash -or -not $prepared.probe -or
        $prepared.probe_sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Candidate preparation did not produce its bound packet and compiled probe.' }
    # Repeated dry-run/Execute calls with the same new directory describe the same
    # executable path. Its directory must remain nonexistent until execution.
    $candidateName = (Get-CanvasCandidateName $candidateDirectory $Options.Route $Options.Resolution).Replace('framed-modal-canvas-','framed-battle-initial-')
    if ($candidateName -ieq [IO.Path]::GetFileName($inputPath)) { throw 'The copied executable must have a new basename.' }
    $plan = [ordered]@{
        schema='clash95_framed_battle_initial_capture_plan_v1'; environment='hidden_cdb_host'; execute=[bool]$Options.Execute
        stage=$script:Stage; resolution=$Options.Resolution; width=$width; height=$height
        route=$Options.Route; save_path=$savePath; save_sha256=$saveHash
        minimap_viewport=[bool]$Options.MinimapViewport; deadline_seconds=120
        original=$originalPath; original_sha256=(Get-CanvasHash $originalPath)
        input_candidate=$inputPath; candidate_sha256=$candidateHash; candidate_dir=$candidateDirectory
        candidate_path=(Join-Path $candidateDirectory $candidateName); work_dir=$workingPath; out_dir=$outputDirectory
        proxy_manifest=$manifestPath; proxy_manifest_sha256=(Get-CanvasHash $manifestPath)
        proxy_source=$proxySource; proxy_source_sha256=$sourceHash; proxy_input=$proxyOutput; proxy_sha256=$proxyHash
        proxy_path=(Join-Path $candidateDirectory 'ddraw.dll'); palette_path=(Join-Path $candidateDirectory 'ddraw_surfdump_palette.bin')
        python=$python; cdb=$cdb; trace=$trace; converter=$converter
        host_path=$PSCommandPath; host_sha256=(Get-CanvasHash $PSCommandPath)
        producer=$producer; producer_sha256=(Get-CanvasHash $producer)
        trace_sha256=(Get-CanvasHash $trace); converter_sha256=(Get-CanvasHash $converter)
        python_sha256=(Get-CanvasHash $python); cdb_sha256=(Get-CanvasHash $cdb)
        probe_sha256=$prepared.probe_sha256
        canvas_state_va=$prepared.packet.canvas_state_va
        state_bytes=$prepared.packet.state_bytes; host_read_contract=$prepared.packet.host_read_contract
        lifecycle_path=$script:LifecyclePath; lifecycle_sha256=$script:LifecycleSha
        stop_va=$prepared.packet.stop_va
        child_environment=@{ CLASH_PROXY_PRESENT='0'; parent_environment_modified=$false }
        manual_input_proof=$false; visible_composition_proof=$false; promotion_ready=$false
        limits=@('Constructed native unit0 versus unit4 entry; disclosed XY and native preference changes, no natural/manual-input proof.',
            'Paused E0 scratch pixels only; primary composition and expanded tactical layout are not accepted.',
            'First-present stop before input, battle result or return lifecycle.',
            'Native cache files may be created in the provided isolated workdir.')
    }
    return @{ plan=$plan; prepared=$prepared }
}

function Test-BattleReady {
 param([string]$Log)
 return [regex]::IsMatch($Log,'(?m)^BINIT_SURFDUMP_HOST_READY\r?\n')
}

function Assert-BattleSurface {
 param($Report,$Plan)
 if ($Report.passed -isnot [bool] -or -not $Report.passed -or
     $Report.ready_for_host_capture -isnot [bool] -or -not $Report.ready_for_host_capture -or
     $Report.schema -cne 'clash95_framed_battle_initial_trace_v1' -or $Report.stage -cne $Plan.stage -or
     $Report.resolution -cne $Plan.resolution -or $Report.route -cne $Plan.route -or
     $Report.candidate_sha256 -cne $Plan.candidate_sha256 -or
     $Report.source.original_sha256 -cne $Plan.original_sha256 -or $Report.source.save_sha256 -cne $Plan.save_sha256 -or
     $Report.source.generated_probe_sha256 -cne $Plan.probe_sha256 -or $Report.source.validator_sha256 -cne $Plan.trace_sha256 -or
     $Report.source.log_raw_sha256 -cnotmatch '^[a-f0-9]{64}$' -or
     $Report.initial_map_trace.passed -isnot [bool] -or -not $Report.initial_map_trace.passed -or
     $Report.battle_sequence.sequence_passed -isnot [bool] -or -not $Report.battle_sequence.sequence_passed) {
   throw 'Full source/save-bound battle trace did not authorize capture.'
 }
 $s=$Report.surface
 foreach ($name in @('surface','base','width','height','bytes','tid','eip','esp','state')) {
  if ($s.$name -isnot [int] -and $s.$name -isnot [long]) {throw ('Battle surface field must be an integer: '+$name)}
 }
 if ($s.width -ne $Plan.width -or $s.height -ne $Plan.height -or $s.bytes -ne ([long]$Plan.width*$Plan.height) -or
     $s.bytes -gt 67108864 -or $s.surface -lt 65536 -or $s.surface -gt 4294967108 -or $s.surface -eq 0x51d4c0 -or
     $s.base -lt 65536 -or ($s.base+$s.bytes) -gt 4294967296 -or
     $s.tid -le 0 -or $s.eip -ne 0x42f2fa -or $s.eip -ne $Plan.stop_va -or $s.esp -le 0 -or ($s.esp%4) -or
     $s.state -ne $Plan.canvas_state_va -or $s.state -lt 65536 -or ($s.state+128) -gt 4294967296 -or
     $Plan.state_bytes -ne 128) {throw 'Battle scratch/state range or first-present identity differs.'}
 $contract=$Plan.host_read_contract
 if ($contract.surface_global -ne 0x5202e0 -or $contract.state_va -ne $s.state -or $contract.state_bytes -ne 128 -or
     $contract.state_all_zero -isnot [bool] -or -not $contract.state_all_zero -or
     $contract.header_bytes -ne 188 -or $contract.header_reads -ne 2 -or $contract.state_reads -ne 2 -or
     $contract.e0_reads -ne 2 -or $contract.pixel_reads -ne 1 -or $contract.vtable -ne 0x50ee24 -or
     $contract.pause_va -ne 0x42f2fa -or $contract.deadline_seconds -ne 120) {throw 'Unreviewed battle host read contract.'}
 return $s
}

function Save-BattleSnapshot {
 param($OwnedGame,$Evidence,[string]$RawPath,$Plan)
 $s=$Evidence;$began=[datetime]::UtcNow.ToString('o');$captures=@{}
 $folder=[IO.Path]::GetDirectoryName($RawPath)
 foreach ($phase in @('before','after')) {
  $phaseRows=@{}
  foreach ($row in @(@('state',$s.state,128),@('e0',0x5202e0,4),@('scratch_header',$s.surface,188))) {
   $data=Read-CanvasMemory $OwnedGame.handle $row[1] $row[2]
   $path=Join-Path $folder ('scratch-'+$phase+'-'+$row[0]+'.raw')
   [IO.File]::WriteAllBytes($path,$data)
   $phaseRows[$row[0]]=@{path=$path;address=$row[1];bytes=$row[2];sha256=(Get-CanvasHash $path);data=$data}
  }
  if (@($phaseRows.state.data | Where-Object {$_ -ne 0}).Count) {throw 'Castle canvas became active during battle capture.'}
  $header=$phaseRows.scratch_header.data
  if ([BitConverter]::ToUInt32($phaseRows.e0.data,0) -ne $s.surface -or
      [BitConverter]::ToUInt16($header,0) -ne $s.width -or [BitConverter]::ToUInt16($header,2) -ne $s.height -or
      [BitConverter]::ToUInt32($header,4) -ne $s.base -or [BitConverter]::ToUInt32($header,184) -ne 0x50ee24 -or
      [BitConverter]::ToUInt32($header,172) -ne 0) {throw 'Battle E0 scratch header does not match the paused trace.'}
  $captures[$phase]=$phaseRows
  if ($phase -eq 'before') {
   $pixels=Read-CanvasMemory $OwnedGame.handle $s.base $s.bytes
   [IO.File]::WriteAllBytes($RawPath,$pixels)
  }
 }
 foreach ($name in @('state','e0','scratch_header')) {
  if ($captures.before[$name].sha256 -cne $captures.after[$name].sha256) {throw ('Paused battle '+$name+' changed across pixel read.')}
  $captures.before[$name].Remove('data');$captures.after[$name].Remove('data')
 }
 return @{path=$RawPath;sha256=(Get-CanvasHash $RawPath);bytes=$pixels.Length;width=$s.width;height=$s.height;pitch=$s.width;
   pixel_reads=1;header_reads=2;state_reads=2;e0_reads=2;paused=$true;capture='battle_e0_scratch_diagnostic';
   state_va=$s.state;surface=$s.surface;base=$s.base;reads=$captures;started_at=$began;
   captured_at=[datetime]::UtcNow.ToString('o');game_identity=$OwnedGame.identity;primary_capture=$false;final_composition_proven=$false}
}

function Invoke-BattleCapture {
    param($Bundle, [switch]$DoExecute)
    $plan=$Bundle.plan; $prepared=$Bundle.prepared
    if (-not $DoExecute) { return @{ status='dry_run'; executed=$false; plan=$plan; prepared=$prepared } }
    $summary = [ordered]@{ schema='clash95_framed_battle_initial_capture_v1'; passed=$false; status='failed'; executed=$false; plan=$plan
        started_at=[datetime]::UtcNow.ToString('o'); finished_at=$null; failures=@(); trace=$null; snapshot=$null; png=$null
        cdb=$null; candidates=@(); cleanup=@{ cdb=$null; candidates=@(); desktop_closed=$false }
        manual_input_proof=$false; visible_composition_proof=$false; promotion_ready=$false }
    $session=$null; $owned=@{}; $outputCreated=$false; $launch=@{session=$null}
    $logPath=Join-Path $plan.out_dir 'cdb.log'; $probePath=Join-Path $plan.out_dir 'framed-battle-initial.cdb'
    $packetPath=Join-Path $plan.out_dir 'packet.json'; $rawPath=Join-Path $plan.out_dir 'surface.raw'
    try {
        # No -Force, no reuse: never overwrite a previous artifact or candidate.
        [void](Resolve-CanvasPath $plan.out_dir -Root 'C:\ClashCaptures' -Kind new)
        [void](New-Item -ItemType Directory -Path $plan.out_dir)
        $outputCreated=$true
        [void](Resolve-CanvasPath $plan.candidate_dir -Root 'C:\ClashTests' -Kind new)
        [void](New-Item -ItemType Directory -Path $plan.candidate_dir)
        foreach ($pair in @(@($plan.original,$plan.original_sha256),@($plan.input_candidate,$plan.candidate_sha256),
            @($plan.proxy_manifest,$plan.proxy_manifest_sha256),@($plan.proxy_source,$plan.proxy_source_sha256),@($plan.proxy_input,$plan.proxy_sha256),
            @($plan.host_path,$plan.host_sha256),@($plan.producer,$plan.producer_sha256),@($plan.trace,$plan.trace_sha256),@($plan.converter,$plan.converter_sha256),
            @($plan.python,$plan.python_sha256),@($plan.cdb,$plan.cdb_sha256),
            @($plan.save_path,$plan.save_sha256),@($plan.lifecycle_path,$plan.lifecycle_sha256))) {
            if ((Get-CanvasHash $pair[0]) -cne $pair[1]) { throw 'A planned source, runtime or input file changed before execution.' }
        }
        [IO.File]::Copy($plan.input_candidate,$plan.candidate_path,$false)
        [IO.File]::Copy($plan.proxy_input,$plan.proxy_path,$false)
        if ((Get-CanvasHash $plan.candidate_path) -cne $plan.candidate_sha256 -or (Get-CanvasHash $plan.proxy_path) -cne $plan.proxy_sha256) { throw 'Fresh candidate/proxy copy identity mismatch.' }
        Write-CanvasJson $packetPath $prepared.packet
        [IO.File]::WriteAllText($probePath,$prepared.probe,[Text.UTF8Encoding]::new($false))
        if ((Get-CanvasHash $probePath) -cne $plan.probe_sha256) { throw 'Compiled probe file differs from the prepared packet.' }
        Write-CanvasJson (Join-Path $plan.out_dir 'plan.json') $plan
        $summary.packet=@{path=$packetPath;sha256=(Get-CanvasHash $packetPath)}
        $summary.probe=@{path=$probePath;sha256=(Get-CanvasHash $probePath)}
        # Reconstruct against the COPIED file before launch, not merely its input path.
        $verifyArgs=@($plan.trace,'--prepare','--original',$plan.original,'--candidate',$plan.candidate_path,
            '--candidate-sha256',$plan.candidate_sha256,'--stage',$plan.stage,'--resolution',$plan.resolution,
            '--route',$plan.route,'--save',$plan.save_path)
        if ($plan.minimap_viewport) { $verifyArgs+='--minimap-viewport' }
        $verified=Invoke-CanvasPythonJson $plan.python $verifyArgs
        if ($verified.probe_sha256 -cne $plan.probe_sha256 -or $verified.probe -cne $prepared.probe -or
            ($verified.packet | ConvertTo-Json -Depth 80 -Compress) -cne ($prepared.packet | ConvertTo-Json -Depth 80 -Compress)) { throw 'Fresh copied candidate reconstruction differs from the whole planned packet.' }
        $launchStart=[datetime]::UtcNow
        $summary.launch_attempted=$true
        $session=Start-CanvasHidden $plan $probePath $logPath $launch
        $summary.executed=$true; $summary.cdb=$session.identity
        $summary.hidden_desktop=$session.desktop_name; $summary.command_line=$session.command_line
        $watch=[Diagnostics.Stopwatch]::StartNew()
        while ($watch.Elapsed.TotalSeconds -lt 120) {
            Find-CanvasOwnedChildren $plan $session $launchStart $owned
            $text=Read-CanvasLog $logPath
            if (Test-BattleReady $text) {
                $summary.trace=Invoke-CanvasPythonJson $plan.python @($plan.trace,'--log',$logPath,'--packet',$packetPath,
                    '--original',$plan.original,'--candidate',$plan.candidate_path,'--probe',$probePath,'--save',$plan.save_path) -PermitFailure -TimeoutMilliseconds ([Math]::Max(1,120000-[int]$watch.ElapsedMilliseconds))
                Write-CanvasJson (Join-Path $plan.out_dir 'trace.json') $summary.trace
                $surface=Assert-BattleSurface $summary.trace $plan
                if ($owned.Count -ne 1) { throw 'Modal readiness lacks exactly one measured, owned candidate.' }
                if ($watch.Elapsed.TotalSeconds -ge 120) { throw 'Modal validation exceeded the capture deadline; no memory read is authorized.' }
                $prefix=Read-CanvasLogBytes $logPath
                if ((Get-CanvasBytesHash $prefix) -cne $summary.trace.source.log_raw_sha256) {throw 'Validated raw log changed before capture.'}
                $prefixPath=Join-Path $plan.out_dir 'capture-prefix.log';[IO.File]::WriteAllBytes($prefixPath,$prefix)
                $summary.capture_prefix=@{path=$prefixPath;bytes=$prefix.Length;sha256=(Get-CanvasHash $prefixPath)}
                $summary.snapshot=Save-BattleSnapshot @($owned.Values)[0] $surface $rawPath $plan
                if ((Get-CanvasBytesHash (Read-CanvasLogBytes $logPath)) -cne $summary.capture_prefix.sha256) {throw 'Debugger log changed across the paused raw capture.'}
                if ($watch.Elapsed.TotalSeconds -ge 120) {throw 'Paired capture exceeded the deadline.'}
                break
            }
            if (Test-CanvasProcessExited $session) { throw 'Debugger exited before accepted modal readiness.' }
            Start-Sleep -Milliseconds 100
        }
        if (-not $summary.snapshot) { throw 'The 120-second modal capture deadline expired without a snapshot.' }
    } catch { $summary.failures += $_.Exception.Message }
    finally {
        if (-not $session -and $launch.session) {
            $session=$launch.session; $summary.executed=$true; $summary.cdb=$session.identity
            $summary.hidden_desktop=$session.desktop_name; $summary.command_line=$session.command_line
        }
        if ($session) {
            # Attempt identity acquisition even after an early polling/parser failure.
            try { Find-CanvasOwnedChildren $plan $session $launchStart $owned } catch { $summary.failures += $_.Exception.Message }
            $summary.candidates=@($owned.Values | ForEach-Object { $_.identity })
            # Debugger FIRST. Retained kernel handles cannot target a reused PID.
            try { $summary.cleanup.cdb=Stop-CanvasOwned $session } catch { $summary.failures += $_.Exception.Message }
            foreach ($game in $owned.Values) {
                try { $summary.cleanup.candidates += (Stop-CanvasOwned $game) } catch { $summary.failures += $_.Exception.Message }
            }
            try { $summary.cleanup.desktop_closed=Close-CanvasDesktop $session } catch { $summary.failures += $_.Exception.Message }
            if (-not $summary.cleanup.cdb.absent -or -not $summary.cleanup.cdb.handle_closed -or
                $summary.cleanup.candidates.Count -ne 1 -or @($summary.cleanup.candidates | Where-Object { -not $_.absent -or -not $_.handle_closed }).Count -or
                -not $summary.cleanup.desktop_closed) { $summary.failures += 'Exact owned-process absence/handle cleanup was not fully verified.' }
        }
        if ($summary.snapshot) {
            try {
                # Preserve the earlier prefix and revalidate every later actual
                # record, including the debugger termination tail.
                $summary.final_trace=Invoke-CanvasPythonJson $plan.python @($plan.trace,'--log',$logPath,'--packet',$packetPath,
                    '--original',$plan.original,'--candidate',$plan.candidate_path,'--probe',$probePath,'--save',$plan.save_path) -PermitFailure
                Write-CanvasJson (Join-Path $plan.out_dir 'trace-final.json') $summary.final_trace
                $finalBytes=Read-CanvasLogBytes $logPath
                $finalHash=Get-CanvasBytesHash $finalBytes
                $summary.final_log=@{path=$logPath;sha256=$finalHash;bytes=$finalBytes.Length;capture_prefix_preserved=$false}
                $originalPrefix=[IO.File]::ReadAllBytes($summary.capture_prefix.path)
                if ((Get-CanvasBytesHash $originalPrefix) -cne $summary.capture_prefix.sha256 -or $finalBytes.Length -lt $originalPrefix.Length) {throw 'Immutable capture prefix was changed or truncated.'}
                $finalPrefix=New-Object byte[] $originalPrefix.Length;[Array]::Copy($finalBytes,$finalPrefix,$finalPrefix.Length)
                if ((Get-CanvasBytesHash $finalPrefix) -cne $summary.capture_prefix.sha256) {throw 'Final log no longer begins with the actual captured prefix.'}
                if ($finalHash -cne $summary.final_trace.source.log_raw_sha256) {throw 'Final raw log differs from the complete parser input.'}
                $summary.final_log.capture_prefix_preserved=$true
                [void](Assert-BattleSurface $summary.final_trace $plan)
                if ((Get-CanvasHash $packetPath) -cne $summary.packet.sha256 -or
                    (Get-CanvasHash $probePath) -cne $summary.probe.sha256) {throw 'Packet/probe changed after capture.'}
            } catch {$summary.failures+=$_.Exception.Message}
        }
        # Preserve and convert captured physical raw even when final trace or cleanup failed.
        if ($summary.snapshot) {
            try {
                if (-not (Test-Path -LiteralPath $plan.palette_path -PathType Leaf) -or (Get-Item -LiteralPath $plan.palette_path).Length -ne 1024) { throw 'Fresh proxy palette is missing or has the wrong size.' }
                $summary.palette=@{ path=$plan.palette_path; sha256=(Get-CanvasHash $plan.palette_path); bytes=1024 }
                $pngPath=Join-Path $plan.out_dir 'surface.png'; $metaPath=Join-Path $plan.out_dir 'surface.png.json'
                $convertOutput = & $plan.python -B $plan.converter $rawPath --width $plan.width --height $plan.height --pitch $plan.width --output $pngPath --metadata $metaPath --log $summary.capture_prefix.path --palette $plan.palette_path
                if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $metaPath)) { throw 'Raw-to-PNG conversion failed; raw capture is preserved.' }
                $summary.png=[IO.File]::ReadAllText($metaPath) | ConvertFrom-Json
                if ($summary.png.palette_mode -ne 'directdraw-palette' -or $summary.png.raw_sha256 -cne $summary.snapshot.sha256 -or
                    $summary.png.png_sha256 -cne (Get-CanvasHash $pngPath)) { throw 'PNG conversion metadata does not bind the fresh palette and raw capture.' }
            } catch { $summary.failures += $_.Exception.Message }
        }
        if ($summary.executed) {
            try {
                $summary.postrun_identity=@{ save_sha256=(Get-CanvasHash $plan.save_path); original_sha256=(Get-CanvasHash $plan.original); input_candidate_sha256=(Get-CanvasHash $plan.input_candidate)
                    candidate_sha256=(Get-CanvasHash $plan.candidate_path); proxy_sha256=(Get-CanvasHash $plan.proxy_path) }
                if ($summary.postrun_identity.save_sha256 -cne $plan.save_sha256 -or
                    $summary.postrun_identity.original_sha256 -cne $plan.original_sha256 -or
                    $summary.postrun_identity.input_candidate_sha256 -cne $plan.candidate_sha256 -or
                    $summary.postrun_identity.candidate_sha256 -cne $plan.candidate_sha256 -or
                    $summary.postrun_identity.proxy_sha256 -cne $plan.proxy_sha256) { throw 'Post-run executable or proxy identity changed.' }
            } catch { $summary.failures += $_.Exception.Message }
        }
        $summary.finished_at=[datetime]::UtcNow.ToString('o')
        $summary.passed=($summary.executed -and $summary.failures.Count -eq 0 -and $null -ne $summary.snapshot -and $null -ne $summary.png)
        if ($summary.passed) { $summary.status='bounded_hidden_battle_initial_scratch_capture' }
        if ($outputCreated) { Write-CanvasJson (Join-Path $plan.out_dir 'summary.json') $summary }
    }
    return $summary
}


try {
 $options=@{Original=$Original;InputCandidate=$InputCandidate;ProxyBuildManifest=$ProxyBuildManifest;WorkDir=$WorkDir;
    CandidateDir=$CandidateDir;OutDir=$OutDir;Route=$Route;Resolution=$Resolution;MinimapViewport=[bool]$MinimapViewport;Execute=[bool]$Execute}
 $bundle=New-BattleCapturePlan $options
 $result=Invoke-BattleCapture $bundle -DoExecute:$Execute
 $result | ConvertTo-Json -Depth 80
 if ($Execute -and -not $result.passed) {exit 1}
} catch {
 @{schema='clash95_framed_battle_initial_capture_v1';passed=$false;status='preparation_failed';executed=$false;
   failures=@($_.Exception.Message);manual_input_proof=$false;promotion_ready=$false} | ConvertTo-Json -Depth 10
 exit 1
}
