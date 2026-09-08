<# Controlled hidden minimap scroll capture. Default prepares an offline plan.
   Fixed canonical before/continue files only; no visible fallback or manual-input proof.
#>
[CmdletBinding()]
param(
    [string]$Original='C:\Clash\clash95.exe',
    [Parameter(Mandatory=$true)][string]$InputCandidate,
    [Parameter(Mandatory=$true)][string]$ProxyBuildManifest,
    [Parameter(Mandatory=$true)][string]$WorkDir,
    [Parameter(Mandatory=$true)][string]$CandidateDir,
    [Parameter(Mandatory=$true)][string]$OutDir,
    [ValidateSet('1024x768','802x602')][string]$Resolution='1024x768',
    [Parameter(Mandatory=$true)][ValidateRange(0,99)][int]$TargetX,
    [Parameter(Mandatory=$true)][ValidateRange(0,99)][int]$TargetY,
    [switch]$Execute
)
$ErrorActionPreference='Stop'
$OutputEncoding=[Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=$OutputEncoding
$script:RepoRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$script:Stage='gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation'

function Get-ScrollHash {
    param([string]$Path)
    $stream = [IO.File]::OpenRead($Path)
    $hash = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
    finally { $stream.Dispose(); $hash.Dispose() }
}

function Get-ScrollCandidateName {
    param([string]$Directory, [string]$Route, [string]$Resolution)
    $hash=[Security.Cryptography.SHA256]::Create()
    try {
        $digest=([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($Directory.ToLowerInvariant())))).Replace('-','').ToLowerInvariant()
        return ('framed-minimap-scroll-' + $Route + '-' + $Resolution + '-' + $digest.Substring(0,16) + '.exe')
    } finally { $hash.Dispose() }
}

function Resolve-ScrollPath {
    param([string]$Path, [string]$Root = '', [ValidateSet('file','directory','new')][string]$Kind)
    if ($Path -notmatch '^[A-Za-z]:[\\/]' -or $Path.Substring(2) -match '[:"\r\n;\x00]' -or $Path.StartsWith('\\')) {
        throw 'Capture paths must be absolute local paths without command delimiters.'
    }
    $full = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    if ($Root -and -not $full.StartsWith(([IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'), [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside required root $Root"
    }
    # Resolve all existing ancestors, rejecting junction/symlink escape and file ancestors.
    $walk = $full
    while ($walk) {
        if (Test-Path -LiteralPath $walk) {
            $item = Get-Item -LiteralPath $walk -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse-point capture paths are unsupported.' }
            if ($walk -ne $full -and -not $item.PSIsContainer) { throw 'A path ancestor is a file.' }
        }
        $walk = [IO.Path]::GetDirectoryName($walk)
    }
    if ($Kind -eq 'new') {
        if (Test-Path -LiteralPath $full) { throw 'CandidateDir and OutDir must be new, nonexistent directories.' }
    } elseif (-not (Test-Path -LiteralPath $full -PathType $(if ($Kind -eq 'file') {'Leaf'} else {'Container'}))) {
        throw "Required $Kind is missing: $full"
    }
    return $full
}

function Invoke-ScrollPythonJson {
    param([string]$Python, [string[]]$Arguments, [switch]$PermitFailure)
    $output = & $Python -B @Arguments
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0 -and -not $PermitFailure) { throw "Offline Python command failed with exit $exitCode." }
    try { $result = ($output -join "`n") | ConvertFrom-Json }
    catch { throw "Offline Python command did not emit valid JSON (exit $exitCode)." }
    if (-not $result) { throw 'Offline Python command returned no report.' }
    return $result
}

function Read-ScrollLog {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return '' }
    # CDB retains a writable log handle while paused. Do not deny its writer.
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    $reader=New-Object IO.StreamReader $stream
    try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
}

function Select-ScrollChildren {
    param($Rows, [int]$CdbProcessId, [string]$CandidatePath, [datetime]$StartedAt)
    $selected = @()
    foreach ($row in $Rows) {
        if ([int]$row.ParentProcessId -eq $CdbProcessId -and $row.ExecutablePath -and
            [IO.Path]::GetFullPath([string]$row.ExecutablePath) -ieq $CandidatePath) {
            if ([datetime]$row.CreationDate -lt $StartedAt -or [int]$row.ProcessId -le 0) { throw 'Child process identity predates this launch.' }
            $selected += $row
        }
    }
    return $selected
}

function Get-ScrollHandleIdentity {
    param([IntPtr]$Handle, [int]$ProcessId, [string]$ExpectedPath)
    $path = New-Object Text.StringBuilder 32768
    [uint32]$size = $path.Capacity
    [long]$created=0; [long]$ended=0; [long]$kernel=0; [long]$user=0
    if (-not [ScrollScreenNative]::QueryFullProcessImageNameW($Handle,0,$path,[ref]$size) -or
        -not [ScrollScreenNative]::GetProcessTimes($Handle,[ref]$created,[ref]$ended,[ref]$kernel,[ref]$user) -or
        [IO.Path]::GetFullPath($path.ToString()) -ine $ExpectedPath) { throw 'Retained process handle does not match the expected executable.' }
    return @{ process_id=$ProcessId; path=$path.ToString(); creation_filetime=$created; creation_utc=[datetime]::FromFileTimeUtc($created).ToString('o'); handle_retained=$true }
}

function Find-ScrollOwnedChildren {
    param($Plan, $CdbSession, [datetime]$StartedAt, $Owned)
    $rows = @(Get-CimInstance Win32_Process -Filter ('ParentProcessId=' + $CdbSession.identity.process_id) -OperationTimeoutSec 5)
    $matches = @(Select-ScrollChildren $rows $CdbSession.identity.process_id $Plan.candidate_path $StartedAt)
    foreach ($row in $matches) {
        $key = [string]$row.ProcessId
        if ($Owned.ContainsKey($key)) { continue }
        $handle = [ScrollScreenNative]::OpenProcess(0x101011,$false,[uint32]$row.ProcessId)
        if ($handle -eq [IntPtr]::Zero) { throw 'Could not retain the owned candidate process handle.' }
        try {
            $identity = Get-ScrollHandleIdentity $handle ([int]$row.ProcessId) $Plan.candidate_path
            if ([datetime]$identity.creation_utc -lt $StartedAt -or
                [Math]::Abs((([datetime]$identity.creation_utc).ToUniversalTime() - ([datetime]$row.CreationDate).ToUniversalTime()).TotalMilliseconds) -gt 1) {
                throw 'Candidate PID creation time changed during handle acquisition.'
            }
            $identity.parent_process_id=$CdbSession.identity.process_id
            $identity.candidate_sha256=Get-ScrollHash $Plan.candidate_path
            if ($identity.candidate_sha256 -cne $Plan.candidate_sha256) { throw 'Candidate changed after launch.' }
            $Owned[$key] = @{ handle=$handle; identity=$identity }
        } catch { [void][ScrollScreenNative]::CloseHandle($handle); throw }
    }
    if ($Owned.Count -gt 1) { throw 'Ambiguous candidate PID: more than one owned candidate was observed.' }
}

function Read-ScrollMemory {
    param([IntPtr]$Handle, [long]$Address, [int]$Count)
    $bytes = New-Object byte[] $Count
    [UIntPtr]$read = [UIntPtr]::Zero
    $nativeCount = [UIntPtr]::new([uint64]$Count)
    if (-not [ScrollScreenNative]::ReadProcessMemory($Handle,[IntPtr]$Address,$bytes,$nativeCount,[ref]$read) -or $read.ToUInt64() -ne $Count) { throw 'ReadProcessMemory did not return the exact bounded snapshot.' }
    return ,$bytes
}

function Stop-ScrollOwned {
    param($OwnedProcess)
    $before = [ScrollScreenNative]::WaitForSingleObject($OwnedProcess.handle,0)
    $terminated = $false
    if ($before -ne 0) { $terminated = [ScrollScreenNative]::TerminateProcess($OwnedProcess.handle,1) }
    $absent = [ScrollScreenNative]::WaitForSingleObject($OwnedProcess.handle,5000) -eq 0
    $closed = [ScrollScreenNative]::CloseHandle($OwnedProcess.handle)
    return @{ identity=$OwnedProcess.identity; absent=$absent; termination_requested=$terminated; handle_closed=$closed }
}

function Close-ScrollDesktop {
    param($Session)
    return [ScrollScreenNative]::CloseDesktop($Session.desktop)
}

function Test-ScrollProcessExited {
    param($Session)
    return [ScrollScreenNative]::WaitForSingleObject($Session.handle,0) -eq 0
}

function Write-ScrollJson {
    param([string]$Path, $Value)
    [IO.File]::WriteAllText($Path,($Value | ConvertTo-Json -Depth 80),[Text.UTF8Encoding]::new($false))
}

# Fixed offline bridge, not a caller-supplied script. Only these operations are
# exposed. Every operation reconstructs the whole canonical packet and files.
# Single-quoted Python literals preserve Windows PowerShell5.1 -c transport.
$script:ScrollPython = @'
import hashlib,json,math,re,sys
from pathlib import Path
op,repo,original_path,candidate_path,resolution,tx,ty,out_dir,candidate_sha=sys.argv[1:10]
sys.path.insert(0,str(Path(repo)/'tools'))
import framed_minimap_scroll_probe as producer
import framed_minimap_scroll_trace as trace
original=Path(original_path).read_bytes();candidate=Path(candidate_path).read_bytes()
packet=producer.build_packet(original,candidate,candidate_sha256=candidate_sha,stage=producer.STAGE,
    resolution=resolution,requested_scroll=(int(tx),int(ty)))
packet_sha=producer.packet_hash(packet);folder=Path(out_dir)
def check(condition,message):
    if not condition: raise ValueError(message)
def read_json(name): return json.loads((folder/name).read_text(encoding='utf-8-sig'))
def equal(a,b): return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))
try:
    check(op in ('prepare','initial','before','after','erasure'),'unsupported fixed operation')
    if op=='prepare':
        result=dict(passed=True,phase='prepare',source_authenticated=True,packet=packet,packet_sha256=packet_sha)
    else:
        check(equal(read_json('packet.json'),packet),'whole saved packet differs from source/candidate reconstruction')
        initial=(folder/'initial.cdb').read_bytes();before=(folder/'before.cdb').read_bytes();continuation=(folder/'continue.cdb').read_bytes()
        for name,data in (('initial_probe',initial),('before_commands',before),('continue_commands',continuation)):
            check(data==packet[name].encode('ascii'),'whole reconstructed command file differs: '+name)
        log=(folder/'cdb.log').read_bytes()
        if op=='initial':
            rows,errors=trace.parse_records(log);check(not errors,'invalid initial log records: '+str(errors))
            count=sum(math.ceil(row['size']/48) for row in packet['native_spans'])
            check([row['marker'] for row in rows]==['BYTE_SEGMENT_PASS']*count+['BOUND'],'unexpected scroll phase before initial validation')
            bound=rows[-1]
            check((bound['stage'],bound['resolution'],bound['sha'],bound['request_x'],bound['request_y'])==
                  (packet['stage'],resolution,candidate_sha,int(tx),int(ty)),'initial loaded contract differs')
            extra=producer.builder.build_candidate(original,resolution,minimap_viewport=True)[2]
            evaluation=trace.initial.evaluate_trace(log.decode('utf-8-sig'),extra,resolution=resolution,candidate_sha256=candidate_sha,stage=packet['stage'])
            check(evaluation['passed'],'initial map trace failed: '+str(evaluation['failures']))
            text=log.decode('utf-8-sig')
            ready=list(re.finditer(rb'(?m)^SURFDUMP_HOST_READY\r?\n',log))
            surfaces=re.findall(r'(?m)^SURFDUMP_READY redraw_seq=4 surface=([0-9a-fA-F]{1,8}) size=\(([0-9]+),([0-9]+)\) base=([0-9a-fA-F]{1,8}) bytes=([0-9]+)\r?$',text)
            closes=re.findall(r'(?m)^PTILE_TRACE_CLOSED tid=([0-9a-fA-F]+) eip=00406fa0 esp=([0-9a-fA-F]+)\r?$',text)
            w,h=map(int,resolution.split('x'))
            check(len(ready)==len(surfaces)==len(closes)==1,'initial pause is not unique and complete')
            sf=surfaces[0];check((int(sf[1]),int(sf[2]),int(sf[4]))==(w,h,w*h),'initial physical geometry differs')
            check(65536<=int(sf[0],16)<0xffffff44 and 65536<=int(sf[3],16)<=0x100000000-w*h,'initial surface bounds invalid')
            check(bound['line']<evaluation['event_integrity']['events'][0]['line'],'loaded contract follows native execution')
            prefix=log[:ready[0].end()]
            result=dict(passed=True,phase=op,source_authenticated=True,packet_sha256=packet_sha,
                log_prefix_bytes=len(prefix),log_prefix_sha256=producer.sha(prefix),initial_trace=evaluation,
                candidate_sha256=candidate_sha)
        elif op in ('before','after'):
            result=trace.evaluate_trace(log,original=original,candidate=candidate,packet=packet,
                initial_probe=initial,before_commands=before,continue_commands=continuation,phase=op)
            if result['passed']:
                boundary=result['sequence']['boundaries'][op]
                result.update(log_prefix_bytes=boundary['prefix_bytes'],log_prefix_sha256=boundary['prefix_sha256'])
        else:
            receipts={phase:read_json(phase+'-receipt.json') for phase in ('before','after')}
            result=trace.audit_erasure(log,original=original,candidate=candidate,packet=packet,
                initial_probe=initial,before_commands=before,continue_commands=continuation,
                before_frame=(folder/'before-frame.raw').read_bytes(),after_frame=(folder/'after-frame.raw').read_bytes(),
                before_backing=(folder/'before-backing.raw').read_bytes(),after_backing=(folder/'after-backing.raw').read_bytes(),receipts=receipts)
            result.update(phase='erasure',packet_sha256=packet_sha)
    print(json.dumps(result,ensure_ascii=True))
    sys.exit(0 if result['passed'] else 2)
except (ValueError,KeyError,TypeError,OSError,UnicodeError,IndexError) as error:
    print(json.dumps(dict(passed=False,phase=op,source_authenticated=False,packet_sha256=packet_sha,
        failures=[str(error)],manual_input_proof=False,promotion_ready=False),ensure_ascii=True))
    sys.exit(2)
'@

function Invoke-ScrollOperation {
    param($Plan,[ValidateSet('prepare','initial','before','after','erasure')][string]$Operation,[switch]$InputFile)
    $candidate = if ($InputFile) { $Plan.input_candidate } else { $Plan.candidate_path }
    $arguments=@('-c',$script:ScrollPython,$Operation,$script:RepoRoot,$Plan.original,$candidate,$Plan.resolution,
        [string]$Plan.target_x,[string]$Plan.target_y,$Plan.out_dir,$Plan.candidate_sha256)
    return Invoke-ScrollPythonJson $Plan.python $arguments -PermitFailure
}

function New-ScrollCapturePlan {
    param($Options)
    $originalPath=Resolve-ScrollPath $Options.Original -Kind file
    $inputPath=Resolve-ScrollPath $Options.InputCandidate -Root 'C:\ClashTests' -Kind file
    $manifestPath=Resolve-ScrollPath $Options.ProxyBuildManifest -Root 'C:\ClashTests' -Kind file
    $workingPath=Resolve-ScrollPath $Options.WorkDir -Root 'C:\ClashTests' -Kind directory
    $candidateDirectory=Resolve-ScrollPath $Options.CandidateDir -Root 'C:\ClashTests' -Kind new
    $outputDirectory=Resolve-ScrollPath $Options.OutDir -Root 'C:\ClashCaptures' -Kind new
    if ($outputDirectory -match '[^\x20-\x7e]' -or $outputDirectory -match '[$";\r\n]' -or $outputDirectory.Length -gt 3500) {
        throw 'Canonical debugger command files require bounded ASCII output paths without argument tokens.'
    }
    if ($Options.Resolution -cnotin @('1024x768','802x602') -or $Options.TargetX -lt 0 -or $Options.TargetX -gt 99 -or $Options.TargetY -lt 0 -or $Options.TargetY -gt 99) { throw 'Unsupported reviewed scroll request.' }
    $size=$Options.Resolution.Split('x')
    $python=Resolve-ScrollPath (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe') -Kind file
    $cdb=Resolve-ScrollPath 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe' -Kind file
    $producer=Join-Path $script:RepoRoot 'tools\framed_minimap_scroll_probe.py'
    $trace=Join-Path $script:RepoRoot 'tools\framed_minimap_scroll_trace.py'
    $converter=Join-Path $script:RepoRoot 'tools\cdb_surface_dump_to_png.py'
    $proxySource=Join-Path $script:RepoRoot 'src\ddraw_surfdump_proxy\ddraw_surfdump_proxy.cpp'
    $manifest=[IO.File]::ReadAllText($manifestPath) | ConvertFrom-Json
    $proxyInput=Resolve-ScrollPath ([string]$manifest.output) -Root 'C:\ClashTests' -Kind file
    $proxyHash=Get-ScrollHash $proxyInput; $proxySourceHash=Get-ScrollHash $proxySource
    if ($manifest.generated_by -cne 'clash-hd-surface-dump-proxy' -or
        [IO.Path]::GetFullPath([string]$manifest.source) -ine $proxySource -or
        $manifest.source_sha256 -inotmatch '^[a-f0-9]{64}$' -or $manifest.source_sha256 -ine $proxySourceHash -or
        $manifest.output_sha256 -inotmatch '^[a-f0-9]{64}$' -or $manifest.output_sha256 -ine $proxyHash -or
        [IO.Path]::GetFileName($proxyInput) -ine 'ddraw.dll') { throw 'Proxy manifest does not authenticate current source and binary.' }
    $name=Get-ScrollCandidateName $candidateDirectory 'scroll' $Options.Resolution
    if ($name -ieq [IO.Path]::GetFileName($inputPath)) { throw 'Fresh candidate must have a distinct basename.' }
    $plan=[ordered]@{
        schema='clash95_framed_minimap_scroll_capture_plan_v1'; environment='hidden_cdb_host'; execute=[bool]$Options.Execute
        stage=$script:Stage; resolution=$Options.Resolution; width=[int]$size[0]; height=[int]$size[1]
        target_x=[int]$Options.TargetX; target_y=[int]$Options.TargetY; minimap_viewport=$true; deadline_seconds=120
        original=$originalPath; original_sha256=(Get-ScrollHash $originalPath)
        input_candidate=$inputPath; candidate_sha256=(Get-ScrollHash $inputPath); candidate_dir=$candidateDirectory
        candidate_path=(Join-Path $candidateDirectory $name); work_dir=$workingPath; out_dir=$outputDirectory
        proxy_manifest=$manifestPath; proxy_manifest_sha256=(Get-ScrollHash $manifestPath)
        proxy_source=$proxySource; proxy_source_sha256=$proxySourceHash; proxy_input=$proxyInput; proxy_sha256=$proxyHash
        proxy_path=(Join-Path $candidateDirectory 'ddraw.dll'); palette_path=(Join-Path $candidateDirectory 'ddraw_surfdump_palette.bin')
        python=$python; python_sha256=(Get-ScrollHash $python); cdb=$cdb; cdb_sha256=(Get-ScrollHash $cdb)
        producer=$producer; producer_sha256=(Get-ScrollHash $producer); trace=$trace; trace_sha256=(Get-ScrollHash $trace)
        converter=$converter; converter_sha256=(Get-ScrollHash $converter); host_path=$PSCommandPath; host_sha256=(Get-ScrollHash $PSCommandPath)
        child_environment=@{CLASH_PROXY_PRESENT='0';parent_environment_modified=$false}
        transport='owned inherited stdin read pipe; parent write handle is noninheritable; exact before/continue file dispatch only'
        manual_input_proof=$false; visible_composition_proof=$false; promotion_ready=$false
        limits=@('Controlled native CALL, mouse globals and a disclosed one-shot query-result override; not manual input.',
            'Same paused owned process; before/after full memory map and distinct clean minimap backing.',
            'Native writes may affect the explicitly isolated work directory; no source-install writes are requested.')
    }
    $prepared=Invoke-ScrollOperation $plan prepare -InputFile
    if ($prepared.passed -isnot [bool] -or -not $prepared.passed -or $prepared.phase -cne 'prepare' -or
        $prepared.packet.candidate_sha256 -cne $plan.candidate_sha256 -or $prepared.packet.stage -cne $plan.stage -or
        $prepared.packet.resolution -cne $plan.resolution -or $prepared.packet_sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Canonical packet preparation failed.' }
    $plan.packet_sha256=$prepared.packet_sha256
    $plan.initial_probe_sha256=$prepared.packet.initial_probe_sha256
    $plan.before_commands_sha256=$prepared.packet.before_commands_sha256
    $plan.continue_commands_sha256=$prepared.packet.continue_commands_sha256
    return @{plan=$plan;packet=$prepared.packet}
}

function Initialize-ScrollNative {
    if ('ScrollScreenNative' -as [type]) { return }
    Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class ScrollScreenNative {
 [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] public struct STARTUPINFO {
  public int cb; public string reserved, desktop, title; public uint x,y,xSize,ySize,xChars,yChars,fill,flags;
  public short show,reserved2; public IntPtr reservedPtr,input,output,error;
 }
 [StructLayout(LayoutKind.Sequential)] public struct PROCESS_INFORMATION { public IntPtr process,thread; public uint processId,threadId; }
 [StructLayout(LayoutKind.Sequential)] public struct SECURITY_ATTRIBUTES { public int length; public IntPtr descriptor; public int inherit; }
 [DllImport("user32.dll",CharSet=CharSet.Unicode,SetLastError=true)] public static extern IntPtr CreateDesktopW(string name,IntPtr device,IntPtr mode,uint flags,uint access,IntPtr security);
 [DllImport("user32.dll",SetLastError=true)] public static extern bool CloseDesktop(IntPtr desktop);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] public static extern bool CreateProcessW(string app,StringBuilder command,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr environment,string workdir,ref STARTUPINFO startup,out PROCESS_INFORMATION info);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool CreatePipe(out IntPtr read,out IntPtr write,ref SECURITY_ATTRIBUTES attributes,uint size);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool SetHandleInformation(IntPtr handle,uint mask,uint flags);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] public static extern IntPtr CreateFileW(string name,uint access,uint share,ref SECURITY_ATTRIBUTES attributes,uint creation,uint flags,IntPtr template);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool WriteFile(IntPtr file,byte[] bytes,uint count,out uint written,IntPtr overlapped);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool CloseHandle(IntPtr handle);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern IntPtr OpenProcess(uint access,bool inherit,uint id);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool ReadProcessMemory(IntPtr process,IntPtr address,byte[] bytes,UIntPtr count,out UIntPtr read);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool TerminateProcess(IntPtr process,uint code);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern uint WaitForSingleObject(IntPtr handle,uint milliseconds);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool GetProcessTimes(IntPtr handle,out long creation,out long exit,out long kernel,out long user);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] public static extern bool QueryFullProcessImageNameW(IntPtr handle,uint flags,StringBuilder path,ref uint length);
}
'@
}

function ConvertTo-ScrollArgument {
    param([string]$Value)
    if ($Value -match '[\r\n\x00]') { throw 'Invalid native launch argument.' }
    # Windows CommandLineToArgv/CRT quoting: double slash runs before quotes
    # and the closing delimiter, retaining all other path slashes literally.
    $escaped=[regex]::Replace($Value,'(\\*)"','${1}${1}\"')
    $escaped=[regex]::Replace($escaped,'(\\+)$','${1}${1}')
    return '"'+$escaped+'"'
}

function Get-ScrollLaunchCommand {
    param($Plan,[string]$ProbePath,[string]$LogPath)
    if ($ProbePath -match '[$";\r\n]' -or $ProbePath -match '[^\x20-\x7e]') { throw 'Invalid canonical initial file path.' }
    $command='$$>a<"'+$ProbePath+'"'
    return ((@($Plan.cdb,'-hd','-logo',$LogPath,'-c',$command,$Plan.candidate_path) | ForEach-Object { ConvertTo-ScrollArgument $_ }) -join ' ')
}

function Start-ScrollHidden {
    param($Plan,[string]$ProbePath,[string]$LogPath,[hashtable]$Launch)
    Initialize-ScrollNative
    $desktopName='ClashMinimapScroll_'+[Guid]::NewGuid().ToString('N')
    $desktop=[ScrollScreenNative]::CreateDesktopW($desktopName,[IntPtr]::Zero,[IntPtr]::Zero,0,0x000F01FF,[IntPtr]::Zero)
    if ($desktop -eq [IntPtr]::Zero) { throw 'Hidden desktop creation failed; no fallback is supported.' }
    $inputRead=[IntPtr]::Zero; $inputWrite=[IntPtr]::Zero; $console=[IntPtr]::Zero; $environmentPointer=[IntPtr]::Zero
    try {
        $attributes=New-Object ScrollScreenNative+SECURITY_ATTRIBUTES
        $attributes.length=[Runtime.InteropServices.Marshal]::SizeOf($attributes); $attributes.inherit=1
        if (-not [ScrollScreenNative]::CreatePipe([ref]$inputRead,[ref]$inputWrite,[ref]$attributes,0) -or
            -not [ScrollScreenNative]::SetHandleInformation($inputWrite,1,0)) { throw 'Cannot create the isolated debugger input pipe.' }
        $console=[ScrollScreenNative]::CreateFileW((Join-Path $Plan.out_dir 'cdb-console.log'),0x40000000,1,[ref]$attributes,1,0x80,[IntPtr]::Zero)
        if ($console -eq [IntPtr]::Zero -or $console -eq [IntPtr](-1)) { throw 'Cannot create the exclusive debugger console log.' }
        $environment=New-Object 'Collections.Generic.SortedDictionary[string,string]' ([StringComparer]::OrdinalIgnoreCase)
        foreach ($pair in [Environment]::GetEnvironmentVariables().GetEnumerator()) { $environment[[string]$pair.Key]=[string]$pair.Value }
        $environment['CLASH_PROXY_PRESENT']='0'
        $block=(($environment.GetEnumerator() | ForEach-Object { $_.Key+'='+$_.Value }) -join "`0")+"`0`0"
        $environmentPointer=[Runtime.InteropServices.Marshal]::StringToHGlobalUni($block)
        $startup=New-Object ScrollScreenNative+STARTUPINFO
        $startup.cb=[Runtime.InteropServices.Marshal]::SizeOf($startup)
        $startup.desktop=$desktopName; $startup.flags=0x101; $startup.show=0
        $startup.input=$inputRead; $startup.output=$console; $startup.error=$console
        $command=Get-ScrollLaunchCommand $Plan $ProbePath $LogPath
        $info=New-Object ScrollScreenNative+PROCESS_INFORMATION
        if (-not [ScrollScreenNative]::CreateProcessW($Plan.cdb,(New-Object Text.StringBuilder $command),[IntPtr]::Zero,[IntPtr]::Zero,$true,0x410,$environmentPointer,$Plan.work_dir,[ref]$startup,[ref]$info)) {
            throw ('Hidden CreateProcessW failed: '+[Runtime.InteropServices.Marshal]::GetLastWin32Error())
        }
        # Publish all retained ownership before any identity query can throw.
        $Launch.session=@{handle=$info.process;desktop=$desktop;input_write=$inputWrite;transport_phase='initial'
            identity=@{process_id=[int]$info.processId;path=$Plan.cdb;creation_utc=$null};desktop_name=$desktopName;command_line=$command}
        [void][ScrollScreenNative]::CloseHandle($info.thread)
        $Launch.session.identity=Get-ScrollHandleIdentity $info.process ([int]$info.processId) $Plan.cdb
        return $Launch.session
    } finally {
        if ($inputRead -ne [IntPtr]::Zero) { [void][ScrollScreenNative]::CloseHandle($inputRead) }
        if ($console -ne [IntPtr]::Zero -and $console -ne [IntPtr](-1)) { [void][ScrollScreenNative]::CloseHandle($console) }
        if ($environmentPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::FreeHGlobal($environmentPointer) }
        if (-not $Launch.session) {
            if ($inputWrite -ne [IntPtr]::Zero) { [void][ScrollScreenNative]::CloseHandle($inputWrite) }
            [void][ScrollScreenNative]::CloseDesktop($desktop)
        }
    }
}

function Read-ScrollLogBytes {
    param([string]$Path)
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    $copy=New-Object IO.MemoryStream
    try {
        if ($stream.Length -gt 16777216) { throw 'Debugger log exceeds the frozen parser bound.' }
        $stream.CopyTo($copy); return ,$copy.ToArray()
    } finally { $copy.Dispose();$stream.Dispose() }
}

function Get-ScrollBytesHash {
    param([byte[]]$Bytes)
    $hash=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() }
    finally { $hash.Dispose() }
}

function Assert-ScrollValidation {
    param($Report,$Plan,[ValidateSet('initial','before','after')][string]$Phase)
    if ($Report.passed -isnot [bool] -or -not $Report.passed -or $Report.source_authenticated -isnot [bool] -or
        -not $Report.source_authenticated -or $Report.phase -cne $Phase -or $Report.packet_sha256 -cne $Plan.packet_sha256 -or
        $Report.candidate_sha256 -cne $Plan.candidate_sha256 -or
        ($Report.log_prefix_bytes -isnot [int] -and $Report.log_prefix_bytes -isnot [long]) -or
        $Report.log_prefix_bytes -le 0 -or $Report.log_prefix_bytes -gt 16777216 -or $Report.log_prefix_sha256 -cnotmatch '^[a-f0-9]{64}$') {
        throw ('Strict source-bound '+$Phase+' trace did not authorize the next action.')
    }
}

function Get-ScrollBoundPrefix {
    param($Report,$Plan,[ValidateSet('initial','before','after')][string]$Phase)
    Assert-ScrollValidation $Report $Plan $Phase
    $raw=Read-ScrollLogBytes (Join-Path $Plan.out_dir 'cdb.log')
    if ($raw.Length -lt $Report.log_prefix_bytes) { throw 'Validated log prefix was truncated.' }
    $prefix=New-Object byte[] ([int]$Report.log_prefix_bytes)
    [Array]::Copy($raw,$prefix,$prefix.Length)
    if ((Get-ScrollBytesHash $prefix) -cne $Report.log_prefix_sha256) { throw 'Validated log prefix changed.' }
    return ,$prefix
}

function Send-ScrollCommands {
    param($Session,$Plan,$Packet,$Validation,[ValidateSet('before','continue')][string]$Phase)
    $needed=if ($Phase -eq 'before') {'initial'} else {'before'}
    if ($Session.transport_phase -cne $needed -or $Session.input_write -eq [IntPtr]::Zero) { throw 'Stale or unavailable debugger command transport.' }
    [void](Get-ScrollBoundPrefix $Validation $Plan $needed)
    $key=if ($Phase -eq 'before') {'before_commands'} else {'continue_commands'}
    $path=Join-Path $Plan.out_dir ($Phase+'.cdb')
    $expected=[Text.Encoding]::ASCII.GetBytes([string]$Packet.$key)
    if ((Get-ScrollHash $path) -cne $Plan.($key+'_sha256') -or
        (Get-ScrollBytesHash $expected) -cne $Plan.($key+'_sha256')) { throw 'Continuation file differs from the exact packet and plan.' }
    # Path came from the strictly validated plan; no caller command is accepted.
    # $$>a< executes without echoing script command source. Echoed MMSC_ text
    # would correctly fail the frozen parser. This command has NO arguments.
    $command='$$>a<"'+$path+'"'+"`r`n"
    if ($path -match '[^\x20-\x7e]' -or $path -match '[$";\r\n]' -or $command.Length -ge 4096) { throw 'Only bounded ASCII command-file paths without argument tokens are supported by this transport.' }
    $bytes=[Text.Encoding]::ASCII.GetBytes($command);[uint32]$written=0
    if (-not [ScrollScreenNative]::WriteFile($Session.input_write,$bytes,[uint32]$bytes.Length,[ref]$written,[IntPtr]::Zero) -or
        $written -ne $bytes.Length) { throw 'Exact debugger command-file dispatch failed or was partial.' }
    $Session.transport_phase=if ($Phase -eq 'before') {'before'} else {'after'}
    return @{phase=$Phase;sent_at=[datetime]::UtcNow.ToString('o');path=$path;sha256=(Get-ScrollHash $path)
        command=$command;bytes=$written;validated_prefix_sha256=$Validation.log_prefix_sha256;packet_sha256=$Plan.packet_sha256}
}

function Assert-ScrollSurfaces {
    param($Report,$Plan,[ValidateSet('before','after')][string]$Phase)
    Assert-ScrollValidation $Report $Plan $Phase
    $surface=$Report.sequence.surfaces.$Phase; $state=$Report.sequence.states.$Phase
    foreach ($name in @('map','width','height','base','vtable','backing','bwidth','bheight','bbase','bvtable')) {
        if ($surface.$name -isnot [int] -and $surface.$name -isnot [long]) { throw ('Surface field is not an integer: '+$name) }
    }
    foreach ($name in @('tid','eip','esp','world_x','world_y','scale')) {
        if ($state.$name -isnot [int] -and $state.$name -isnot [long]) { throw ('State field is not an integer: '+$name) }
    }
    $size=[long]$Plan.width*$Plan.height; $backingSize=[long]$surface.bwidth*$surface.bheight
    if ($surface.width -ne $Plan.width -or $surface.height -ne $Plan.height -or $surface.vtable -ne 0x50ee24 -or
        $surface.bvtable -ne 0x50ee24 -or $surface.map -eq $surface.backing -or $surface.map -eq 0x51d4c0 -or $surface.backing -eq 0x51d4c0 -or
        $surface.bwidth -ne ($state.world_x*$state.scale+14) -or $surface.bheight -ne ($state.world_y*$state.scale+14) -or
        $state.world_x -le 0 -or $state.world_x -gt 100 -or $state.world_y -le 0 -or $state.world_y -gt 100 -or
        $state.scale -notin @(2,4) -or $state.tid -le 0 -or $state.esp -lt 65536 -or $state.esp -ge 0x7ffff000 -or ($state.esp % 4) -or
        $state.eip -ne $(if ($Phase -eq 'before') {0x406fa0} else {0x40b0e5})) { throw 'Requested native map/backing/state contract differs.' }
    foreach ($range in @(@([long]$surface.map,188),@([long]$surface.backing,188),@([long]$surface.base,$size),@([long]$surface.bbase,$backingSize))) {
        if ($range[0] -lt 65536 -or $range[1] -le 0 -or $range[1] -gt 67108864 -or ($range[0]+$range[1]) -gt 4294967296) { throw 'Native read range is unbounded.' }
    }
    if (-not (($surface.base+$size) -le $surface.bbase -or ($surface.bbase+$backingSize) -le $surface.base)) { throw 'Map and minimap pixels alias.' }
    return $surface
}

function Save-ScrollPair {
    param($Game,$Report,$Plan,[ValidateSet('before','after')][string]$Phase)
    $started=[datetime]::UtcNow.ToString('o')
    $surface=Assert-ScrollSurfaces $Report $Plan $Phase
    $state=$Report.sequence.states.$Phase
    $prefix=Get-ScrollBoundPrefix $Report $Plan $Phase
    $prefixPath=Join-Path $Plan.out_dir ($Phase+'-prefix.log');[IO.File]::WriteAllBytes($prefixPath,$prefix)
    # Read and validate BOTH distinct headers before any pixel read. CDB is
    # paused and the same retained game handle is used for all four reads.
    $headers=@{}
    foreach ($kind in @('frame','backing')) {
        $address=if ($kind -eq 'frame') {$surface.map} else {$surface.backing}
        $width=if ($kind -eq 'frame') {$surface.width} else {$surface.bwidth}
        $height=if ($kind -eq 'frame') {$surface.height} else {$surface.bheight}
        $pixels=if ($kind -eq 'frame') {$surface.base} else {$surface.bbase}
        $header=Read-ScrollMemory $Game.handle $address 188
        $path=Join-Path $Plan.out_dir ($Phase+'-'+$kind+'-header.raw');[IO.File]::WriteAllBytes($path,$header)
        $headers[$kind]=@{path=$path;sha256=(Get-ScrollHash $path);address=$address;bytes=188}
        if ([BitConverter]::ToUInt16($header,0) -ne $width -or [BitConverter]::ToUInt16($header,2) -ne $height -or
            [BitConverter]::ToUInt32($header,4) -ne $pixels -or [BitConverter]::ToUInt32($header,184) -ne 0x50ee24) { throw ('Actual '+$kind+' header differs from the validated pause.') }
    }
    $frame=Read-ScrollMemory $Game.handle $surface.base ([int]($surface.width*$surface.height))
    $framePath=Join-Path $Plan.out_dir ($Phase+'-frame.raw');[IO.File]::WriteAllBytes($framePath,$frame)
    $backing=Read-ScrollMemory $Game.handle $surface.bbase ([int]($surface.bwidth*$surface.bheight))
    $backingPath=Join-Path $Plan.out_dir ($Phase+'-backing.raw');[IO.File]::WriteAllBytes($backingPath,$backing)
    [void](Get-ScrollBoundPrefix $Report $Plan $Phase)
    $receipt=[ordered]@{
        phase=$Phase;packet_sha256=$Plan.packet_sha256;candidate_sha256=$Plan.candidate_sha256
        initial_probe_sha256=$Plan.initial_probe_sha256;before_commands_sha256=$Plan.before_commands_sha256;continue_commands_sha256=$Plan.continue_commands_sha256
        log_prefix_bytes=$Report.log_prefix_bytes;log_prefix_sha256=$Report.log_prefix_sha256
        tid=$state.tid;eip=$state.eip;esp=$state.esp;map=$surface.map;base=$surface.base;backing=$surface.backing;bbase=$surface.bbase
        width=$surface.width;height=$surface.height;pitch=$surface.width;bwidth=$surface.bwidth;bheight=$surface.bheight;bpitch=$surface.bwidth
        frame_sha256=(Get-ScrollHash $framePath);backing_sha256=(Get-ScrollHash $backingPath)
    }
    $receiptPath=Join-Path $Plan.out_dir ($Phase+'-receipt.json');Write-ScrollJson $receiptPath $receipt
    $capture=@{phase=$Phase;started_at=$started;captured_at=[datetime]::UtcNow.ToString('o');paused=$true
        game_identity=$Game.identity;header_reads=2;frame_pixel_reads=1;backing_pixel_reads=1;headers=$headers
        frame=@{path=$framePath;sha256=$receipt.frame_sha256;bytes=$frame.Length}
        backing=@{path=$backingPath;sha256=$receipt.backing_sha256;bytes=$backing.Length}
        prefix=@{path=$prefixPath;sha256=$receipt.log_prefix_sha256;bytes=$prefix.Length}
        receipt=@{path=$receiptPath;sha256=(Get-ScrollHash $receiptPath);value=$receipt}
        source_hashes=@{host=$Plan.host_sha256;producer=$Plan.producer_sha256;trace=$Plan.trace_sha256;proxy=$Plan.proxy_sha256;packet=$Plan.packet_sha256}}
    Write-ScrollJson (Join-Path $Plan.out_dir ($Phase+'-capture.json')) $capture
    return $capture
}

function Test-ScrollReady {
    param([string]$Log,[ValidateSet('initial','before','after')][string]$Phase)
    $marker=if ($Phase -eq 'initial') {'SURFDUMP_HOST_READY'} else {'MMSC_HOST_READY phase='+$Phase}
    return [regex]::IsMatch($Log,('(?m)^'+[regex]::Escape($marker)+'\r?\n'))
}

function Wait-ScrollPause {
    param($Plan,$Session,$StartedAt,$Owned,$Watch,[ValidateSet('initial','before','after')][string]$Phase)
    while ($Watch.Elapsed.TotalSeconds -lt $Plan.deadline_seconds) {
        Find-ScrollOwnedChildren $Plan $Session $StartedAt $Owned
        if (Test-ScrollReady (Read-ScrollLog (Join-Path $Plan.out_dir 'cdb.log')) $Phase) {
            if ($Owned.Count -ne 1) { throw 'Readiness lacks exactly one measured owned candidate.' }
            $report=Invoke-ScrollOperation $Plan $Phase
            Write-ScrollJson (Join-Path $Plan.out_dir ($Phase+'-trace.json')) $report
            Assert-ScrollValidation $report $Plan $Phase
            if ($Watch.Elapsed.TotalSeconds -ge $Plan.deadline_seconds) { throw 'Strict pause validation exceeded the capture deadline.' }
            return $report
        }
        if (Test-ScrollProcessExited $Session) { throw ('Debugger exited before accepted '+$Phase+' readiness.') }
        Start-Sleep -Milliseconds 100
    }
    throw ('The 120-second deadline expired before '+$Phase+' readiness.')
}

function Close-ScrollInput {
    param($Session)
    if ($Session.input_write -eq [IntPtr]::Zero) { return $true }
    $closed=[ScrollScreenNative]::CloseHandle($Session.input_write)
    if ($closed) { $Session.input_write=[IntPtr]::Zero }
    return $closed
}

function Invoke-ScrollCapture {
    param($Bundle,[switch]$DoExecute)
    $plan=$Bundle.plan;$packet=$Bundle.packet
    if (-not $DoExecute) { return @{status='dry_run';executed=$false;plan=$plan;packet=$packet} }
    $summary=[ordered]@{schema='clash95_framed_minimap_scroll_capture_v1';passed=$false;status='failed';executed=$false;plan=$plan
        started_at=[datetime]::UtcNow.ToString('o');finished_at=$null;failures=@();traces=@{};captures=@{};dispatches=@();erasure=$null
        cdb=$null;candidates=@();cleanup=@{cdb=$null;candidates=@();input_closed=$false;desktop_closed=$false}
        manual_input_proof=$false;visible_composition_proof=$false;promotion_ready=$false;host_integration_implemented=$true}
    $session=$null;$owned=@{};$launch=@{session=$null};$created=$false
    try {
        [void](Resolve-ScrollPath $plan.out_dir -Root 'C:\ClashCaptures' -Kind new)
        [void](New-Item -ItemType Directory -Path $plan.out_dir);$created=$true
        [void](Resolve-ScrollPath $plan.candidate_dir -Root 'C:\ClashTests' -Kind new)
        [void](New-Item -ItemType Directory -Path $plan.candidate_dir)
        foreach ($pair in @(@($plan.original,$plan.original_sha256),@($plan.input_candidate,$plan.candidate_sha256),
            @($plan.proxy_manifest,$plan.proxy_manifest_sha256),@($plan.proxy_source,$plan.proxy_source_sha256),@($plan.proxy_input,$plan.proxy_sha256),
            @($plan.host_path,$plan.host_sha256),@($plan.producer,$plan.producer_sha256),@($plan.trace,$plan.trace_sha256),
            @($plan.converter,$plan.converter_sha256),@($plan.python,$plan.python_sha256),@($plan.cdb,$plan.cdb_sha256))) {
            if ((Get-ScrollHash $pair[0]) -cne $pair[1]) { throw 'A planned input, source, runtime or proxy file changed.' }
        }
        if ($plan.out_dir -match '[^\x20-\x7e]') { throw 'Debugger command transport requires ASCII output paths.' }
        [IO.File]::Copy($plan.input_candidate,$plan.candidate_path,$false)
        [IO.File]::Copy($plan.proxy_input,$plan.proxy_path,$false)
        if ((Get-ScrollHash $plan.candidate_path) -cne $plan.candidate_sha256 -or (Get-ScrollHash $plan.proxy_path) -cne $plan.proxy_sha256) { throw 'Fresh candidate/proxy copy differs.' }
        foreach ($entry in @(@('initial.cdb','initial_probe'),@('before.cdb','before_commands'),@('continue.cdb','continue_commands'))) {
            $path=Join-Path $plan.out_dir $entry[0]
            [IO.File]::WriteAllText($path,[string]$packet.($entry[1]),[Text.UTF8Encoding]::new($false))
            if ((Get-ScrollHash $path) -cne $plan.($entry[1]+'_sha256')) { throw 'Serialized canonical command file differs.' }
        }
        Write-ScrollJson (Join-Path $plan.out_dir 'packet.json') $packet
        Write-ScrollJson (Join-Path $plan.out_dir 'plan.json') $plan
        $verified=Invoke-ScrollOperation $plan prepare
        if ($verified.passed -isnot [bool] -or -not $verified.passed -or $verified.packet_sha256 -cne $plan.packet_sha256) { throw 'Copied candidate packet reconstruction failed before launch.' }
        $launchStart=[datetime]::UtcNow;$summary.launch_attempted=$true
        $session=Start-ScrollHidden $plan (Join-Path $plan.out_dir 'initial.cdb') (Join-Path $plan.out_dir 'cdb.log') $launch
        $summary.executed=$true;$summary.cdb=$session.identity
        $summary.hidden_desktop=$session.desktop_name;$summary.command_line=$session.command_line
        $watch=[Diagnostics.Stopwatch]::StartNew()
        $initial=Wait-ScrollPause $plan $session $launchStart $owned $watch initial
        $summary.traces.initial=$initial
        $prefix=Get-ScrollBoundPrefix $initial $plan initial
        [IO.File]::WriteAllBytes((Join-Path $plan.out_dir 'initial-prefix.log'),$prefix)
        $summary.dispatches+=Send-ScrollCommands $session $plan $packet $initial before
        $before=Wait-ScrollPause $plan $session $launchStart $owned $watch before
        $summary.traces.before=$before
        $summary.captures.before=Save-ScrollPair @($owned.Values)[0] $before $plan before
        if ($watch.Elapsed.TotalSeconds -ge $plan.deadline_seconds) { throw 'Before capture exceeded the deadline; no continuation is authorized.' }
        $summary.dispatches+=Send-ScrollCommands $session $plan $packet $before continue
        $after=Wait-ScrollPause $plan $session $launchStart $owned $watch after
        $summary.traces.after=$after
        $summary.captures.after=Save-ScrollPair @($owned.Values)[0] $after $plan after
        if ($watch.Elapsed.TotalSeconds -ge $plan.deadline_seconds) { throw 'After capture exceeded the deadline.' }
        $summary.erasure=Invoke-ScrollOperation $plan erasure
        Write-ScrollJson (Join-Path $plan.out_dir 'erasure.json') $summary.erasure
        if ($summary.erasure.passed -isnot [bool] -or -not $summary.erasure.passed) { throw 'Source-bound scroll or old-outline erasure failed; snapshots are preserved.' }
    } catch { $summary.failures+=$_.Exception.Message }
    finally {
        if (-not $session -and $launch.session) { $session=$launch.session;$summary.executed=$true;$summary.cdb=$session.identity
            $summary.hidden_desktop=$session.desktop_name;$summary.command_line=$session.command_line }
        if ($session) {
            try { Find-ScrollOwnedChildren $plan $session $launchStart $owned } catch { $summary.failures+=$_.Exception.Message }
            $summary.candidates=@($owned.Values | ForEach-Object { $_.identity })
            # Always stop the retained debugger FIRST, then its exact children.
            try { $summary.cleanup.cdb=Stop-ScrollOwned $session } catch { $summary.failures+=$_.Exception.Message }
            foreach ($game in $owned.Values) {
                try { $summary.cleanup.candidates+=(Stop-ScrollOwned $game) } catch { $summary.failures+=$_.Exception.Message }
            }
            # Closing stdin while CDB is still alive can create a broken-pipe
            # termination unrelated to the validated capture. Keep it open
            # until the retained debugger handle has actually signaled.
            if ($summary.cleanup.cdb.absent) {
                try { $summary.cleanup.input_closed=Close-ScrollInput $session } catch { $summary.failures+=$_.Exception.Message }
            } else { $summary.failures+='Debugger termination did not signal; stdin was not closed before terminal confirmation.' }
            try { $summary.cleanup.desktop_closed=Close-ScrollDesktop $session } catch { $summary.failures+=$_.Exception.Message }
            if (-not $summary.cleanup.cdb.absent -or -not $summary.cleanup.cdb.handle_closed -or
                $summary.cleanup.candidates.Count -ne 1 -or @($summary.cleanup.candidates | Where-Object { -not $_.absent -or -not $_.handle_closed }).Count -or
                -not $summary.cleanup.input_closed -or -not $summary.cleanup.desktop_closed) { $summary.failures+='Exact owned-process/pipe/desktop cleanup was not fully verified.' }
        }
        # Convert every successful raw pair even after a later erasure/cleanup
        # failure. Raw headers/prefixes/partial reads also remain on disk.
        $summary.pngs=@{}
        foreach ($phase in @('before','after')) {
            if (-not $summary.captures.ContainsKey($phase)) { continue }
            try {
                if (-not (Test-Path -LiteralPath $plan.palette_path -PathType Leaf) -or (Get-Item -LiteralPath $plan.palette_path).Length -ne 1024) { throw 'Fresh proxy palette is missing or malformed.' }
                $summary.palette=@{path=$plan.palette_path;sha256=(Get-ScrollHash $plan.palette_path);bytes=1024}
                $s=$summary.captures[$phase].receipt.value
                $summary.pngs[$phase]=@{}
                foreach ($kind in @('frame','backing')) {
                    $w=if ($kind -eq 'frame') {$s.width} else {$s.bwidth};$h=if ($kind -eq 'frame') {$s.height} else {$s.bheight}
                    $raw=Join-Path $plan.out_dir ($phase+'-'+$kind+'.raw');$png=Join-Path $plan.out_dir ($phase+'-'+$kind+'.png')
                    $meta=$png+'.json';$prefix=Join-Path $plan.out_dir ($phase+'-prefix.log')
                    $conversion=& $plan.python -B $plan.converter $raw --width $w --height $h --pitch $w --output $png --metadata $meta --log $prefix --palette $plan.palette_path
                    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $meta)) { throw ('PNG conversion failed for '+$phase+' '+$kind) }
                    $metadata=[IO.File]::ReadAllText($meta) | ConvertFrom-Json
                    $expected=if ($kind -eq 'frame') {$s.frame_sha256} else {$s.backing_sha256}
                    if ($metadata.palette_mode -cne 'directdraw-palette' -or $metadata.raw_sha256 -cne $expected -or
                        $metadata.png_sha256 -cne (Get-ScrollHash $png)) { throw 'Converted PNG does not bind the actual raw/palette.' }
                    $summary.pngs[$phase][$kind]=$metadata
                }
            } catch { $summary.failures+=$_.Exception.Message }
        }
        if ($summary.executed) {
            try {
                $summary.postrun_identity=@{original_sha256=(Get-ScrollHash $plan.original);input_candidate_sha256=(Get-ScrollHash $plan.input_candidate)
                    candidate_sha256=(Get-ScrollHash $plan.candidate_path);proxy_sha256=(Get-ScrollHash $plan.proxy_path)}
                if ($summary.postrun_identity.original_sha256 -cne $plan.original_sha256 -or $summary.postrun_identity.input_candidate_sha256 -cne $plan.candidate_sha256 -or
                    $summary.postrun_identity.candidate_sha256 -cne $plan.candidate_sha256 -or $summary.postrun_identity.proxy_sha256 -cne $plan.proxy_sha256) { throw 'Post-run original/candidate/proxy identity changed.' }
            } catch { $summary.failures+=$_.Exception.Message }
        }
        $summary.finished_at=[datetime]::UtcNow.ToString('o')
        $summary.passed=($summary.executed -and $summary.failures.Count -eq 0 -and $summary.captures.Count -eq 2 -and $summary.erasure.passed -eq $true -and $summary.pngs.Count -eq 2)
        if ($summary.passed) { $summary.status='bounded_controlled_hidden_scroll_erasure' }
        if ($created) {
            $summary.artifacts=@()
            try {
                foreach ($artifact in @(Get-ChildItem -LiteralPath $plan.out_dir -File | Where-Object { $_.Name -ne 'summary.json' })) {
                    try { $summary.artifacts+=@{path=$artifact.FullName;sha256=(Get-ScrollHash $artifact.FullName);bytes=$artifact.Length} }
                    catch { $summary.failures+=('Preserved artifact could not be hashed: '+$artifact.FullName+': '+$_.Exception.Message) }
                }
            } catch { $summary.failures+=('Artifact inventory failed: '+$_.Exception.Message) }
            if ($summary.failures.Count) { $summary.passed=$false;$summary.status='failed' }
            Write-ScrollJson (Join-Path $plan.out_dir 'summary.json') $summary
        }
    }
    return $summary
}

try {
    $options=@{Original=$Original;InputCandidate=$InputCandidate;ProxyBuildManifest=$ProxyBuildManifest;WorkDir=$WorkDir
        CandidateDir=$CandidateDir;OutDir=$OutDir;Resolution=$Resolution;TargetX=$TargetX;TargetY=$TargetY;Execute=[bool]$Execute}
    $bundle=New-ScrollCapturePlan $options
    $result=Invoke-ScrollCapture $bundle -DoExecute:$Execute
    $result | ConvertTo-Json -Depth 90
    if ($Execute -and -not $result.passed) { exit 1 }
} catch {
    @{schema='clash95_framed_minimap_scroll_capture_v1';passed=$false;status='preparation_failed';executed=$false
        failures=@($_.Exception.Message);manual_input_proof=$false;promotion_ready=$false} | ConvertTo-Json -Depth 10
    exit 1
}
