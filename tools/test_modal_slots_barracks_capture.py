"""Offline manifest, observation, pixel and extracted PowerShell boundaries.

No game, debugger, wrapper, desktop or native process API is started. Tests of
PowerShell functions extract their AST declarations and replace native calls.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import modal_slots_barracks_probe as producer
import modal_slots_barracks_trace as trace
import modal_slots_candidate_context as context
import modal_slots_surface_audit as audit
import test_framed_modal_canvas_trace as canvas_fixture

ROOT=Path(__file__).resolve().parents[1]
HOST=ROOT/'scripts/cdb/run_modal_slots_barracks_capture.ps1'
PS=Path('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')


def slot_fixture():
    packet={'slot_entry_vas':{'after_dirty_copy':0x5F0100}}
    sequence={'raw_records':[
        {'marker':'MCAP_MAP_HANDOFF','line':1,'values':{'tid':0x2345,'esp':0x100000}},
        {'marker':'MCAP_CANVAS','line':2,'values':{'event':'FACILITY_BLIT_RETURN'}},
        {'marker':'MCAP_PRESENT_CALL','line':20,'values':{}},
        {'marker':'MCAP_CANVAS','line':21,'values':{'event':'READY','native':0x23000000}}]}
    rows=['ordinary prefix','modal blit return']
    for index in range(12):
        x=126+71*(index%6);y=75+131*(index//6)
        rows.append(f'SCAP_SLOT_COPY tid=2345 eip=005f0100 esp={0x100000-212:08x} source=23000000 x={x} y={y} right={x+32} bottom={y+64} dest_x={x} dest_y={y} return=00432c10 producer_return=00432de7')
    return '\n'.join(rows)+'\n',packet,sequence


def startup_fixture():
    """Reuse synthetic native observations, with explicit slots startup text."""
    packet=canvas_fixture.small_packet('barracks','construct_all')
    log=canvas_fixture.log_fixture(packet)
    log=log.replace(packet['stage'],producer.STAGE)
    log=log.replace(packet['protocol_revision'],producer.PROTOCOL_REVISION)
    packet.update(stage=producer.STAGE,protocol_revision=producer.PROTOCOL_REVISION)
    rows=log.splitlines()
    rows[1]=(f"SLOTS_CONTRACT_PASS stage={packet['stage']} resolution={packet['resolution']} "
             f"candidate_sha256={packet['candidate_sha256']} revision={producer.builder.REVISION}")
    rows[2]='SLOTS_SCOPE owned_barracks_dirty_slots primary_composition_proven=false manual_input_proof=false promotion_ready=false'
    return '\n'.join(rows)+'\n',packet


class StartupRecordTests(unittest.TestCase):
    def test_protocol_field_is_not_an_extra_slots_startup_record(self):
        log,packet=startup_fixture()
        self.assertIn('protocol=slots_barracks_owned_canvas_v1',log)
        result=trace.evaluate_sequence(log,packet)
        self.assertTrue(result['sequence_passed'],result['failures'])
        contracts=[row for row in result['raw_records'] if row['marker']=='MCAP_CONTRACT']
        self.assertEqual(len(contracts),1)
        self.assertEqual(contracts[0]['values']['protocol'],producer.PROTOCOL_REVISION)
        self.assertFalse(result['source_authenticated'])
        self.assertFalse(result['ready_for_host_capture'])

    def test_missing_duplicate_reordered_and_malformed_startup_records_stay_failed(self):
        log,packet=startup_fixture();rows=log.splitlines()
        for index in (1,2):
            variants=[rows[:index]+rows[index+1:],rows[:index]+[rows[index]]+rows[index:]]
            for replacement in (' '+rows[index],'\t'+rows[index],rows[index].lower(),
                                'prefix '+rows[index],rows[index]+' extra=1','SLOTS_UNKNOWN fields=1'):
                changed=rows.copy();changed[index]=replacement;variants.append(changed)
            for changed in variants:
                result=trace.evaluate_sequence('\n'.join(changed),packet)
                self.assertFalse(result['sequence_passed'],changed[index:index+1])
                self.assertIn('slots loaded contract/scope missing, repeated, malformed or mismatched',result['failures'])
        for other in (0,2,5):
            changed=rows.copy();changed[1],changed[other]=changed[other],changed[1]
            self.assertFalse(trace.evaluate_sequence('\n'.join(changed),packet)['sequence_passed'])

    def test_startup_revision_candidate_and_modal_protocol_still_require_exact_values(self):
        log,packet=startup_fixture()
        mutations=(('revision='+producer.builder.REVISION,'revision=unknown'),
                   ('candidate_sha256='+packet['candidate_sha256'],'candidate_sha256='+'b'*64),
                   ('protocol='+producer.PROTOCOL_REVISION,'protocol=slots_unknown'),
                   ('protocol='+producer.PROTOCOL_REVISION,'protocol=SLOTS_barracks_owned_canvas_v1'))
        for old,new in mutations:
            result=trace.evaluate_sequence(log.replace(old,new,1),packet)
            self.assertFalse(result['sequence_passed'],new)


class SlotObservationTests(unittest.TestCase):
    def test_twelve_source_thread_stack_and_geometry_observations(self):
        log,packet,sequence=slot_fixture();result=trace.evaluate_slots(log,packet,sequence)
        self.assertTrue(result['passed'],result);self.assertEqual(len(result['raw_records']),12)
        self.assertFalse(result['primary_composition_proven'])

    def test_missing_duplicate_malformed_wrong_geometry_identity_and_order_fail(self):
        log,packet,sequence=slot_fixture();lines=log.splitlines()
        for index in range(2,14):
            for changed in (lines[:index]+lines[index+1:],lines[:index]+[lines[index]]+lines[index:]):
                report=trace.evaluate_slots('\n'.join(changed),packet,sequence)
                self.assertFalse(report['passed']);self.assertEqual(len(report['raw_records']),len(changed)-2)
        for old,new in (('tid=2345','tid=2346'),('source=23000000','source=24000000'),('esp=000fff2c','esp=000fff30'),
                        ('x=126','x=127'),('right=158','right=157'),('return=00432c10','return=00432c14'),
                        ('producer_return=00432de7','producer_return=00432de8'),('SCAP_SLOT_COPY','SCAP_UNKNOWN')):
            self.assertIn(old,log)
            self.assertFalse(trace.evaluate_slots(log.replace(old,new,1),packet,sequence)['passed'])
        swapped=lines.copy();swapped[2],swapped[3]=swapped[3],swapped[2]
        self.assertFalse(trace.evaluate_slots('\n'.join(swapped),packet,sequence)['passed'])

    def test_old_or_broader_route_packets_are_not_accepted(self):
        for route in ('court','school','castle_overview'):
            packet={'route':{'name':route},'stage':producer.STAGE,'protocol_revision':producer.PROTOCOL_REVISION,'resolution':'800x600'}
            self.assertFalse(trace.evaluate_sequence('',packet)['sequence_passed'])


class PixelTests(unittest.TestCase):
    def fixture(self,width=1024,height=768):
        native=bytes((x*13+y*7)%251+1 for y in range(480) for x in range(640))
        physical=bytearray(width*height);ox=(width-640)//2;oy=(height-480)//2
        for y in range(480):physical[(y+oy)*width+ox:(y+oy)*width+ox+640]=native[y*640:(y+1)*640]
        return native,physical

    def test_centered_mirror_and_all_four_outer_regions(self):
        for w,h in ((800,600),(1024,768),(1920,1080),(802,602)):
            native,physical=self.fixture(w,h)
            self.assertTrue(audit.mirror_pixels(native,bytes(physical),w,h)['passed'])
            for location in (0,w-1,(h-1)*w,w*h-1):
                changed=physical.copy();changed[location]=1
                result=audit.mirror_pixels(native,bytes(changed),w,h)
                self.assertFalse(result['passed']);self.assertEqual(result['outside_nonzero_pixels'],1)

    def test_original_24576_missing_slot_failure_and_matching_blank_cannot_pass(self):
        native,physical=self.fixture();ox=192;oy=144
        for y in (75,206):
            for x in (126,197,268,339,410,481):
                for yy in range(y,y+64):physical[(yy+oy)*1024+x+ox:(yy+oy)*1024+x+ox+32]=bytes(32)
        report=audit.mirror_pixels(native,bytes(physical),1024,768)
        self.assertFalse(report['passed']);self.assertEqual(report['centered_mismatches'],24576)
        self.assertEqual([row['mirror_mismatches'] for row in report['slots']],[2048]*12)
        self.assertFalse(audit.mirror_pixels(bytes(307200),bytes(1024*768),1024,768)['passed'])
        with self.assertRaises(ValueError):audit.mirror_pixels(native,bytes(physical[:-1]),1024,768)


class ManifestTests(unittest.TestCase):
    def test_sidecars_and_rebuild_exactly_bound_no_old_stage_or_cross_resolution(self):
        metadata={'stage':context.builder.STAGE,'recipe_revision':context.builder.REVISION,'resolution':'1024x768'}
        with tempfile.TemporaryDirectory(prefix='slots-context-') as directory:
            path=Path(directory)/'candidate.candidate.json';exe=path.with_name('candidate.exe');probe=path.with_name('candidate.cdb')
            exe.write_bytes(b'image');probe.write_bytes(b'probe');path.write_text(json.dumps(metadata))
            with patch.object(context.builder,'build_candidate',return_value=(b'image',metadata,'probe')):
                value=context.load_context(b'original',b'image',path)
                self.assertEqual(value['manifest_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
                for target,content in ((exe,b'other'),(probe,b'other')):
                    old=target.read_bytes();target.write_bytes(content)
                    with self.assertRaises(ValueError):context.load_context(b'original',b'image',path)
                    target.write_bytes(old)
                with self.assertRaises(ValueError):context.load_context(b'original',b'other',path)
                path.write_text(json.dumps(dict(metadata,resolution='800x600')))
                with self.assertRaises(ValueError):context.load_context(b'original',b'image',path)
                path.write_text(json.dumps(dict(metadata,stage='old-validation')))
                with self.assertRaises(ValueError):context.load_context(b'original',b'image',path)


class AuditBindingTests(unittest.TestCase):
    def test_all_six_raw_files_state_pointers_trace_failure_and_cleanup_are_bound(self):
        with tempfile.TemporaryDirectory(prefix='slots-audit-') as directory:
            root=Path(directory);width,height=800,600
            native,physical=PixelTests().fixture(width,height)
            def artifact(path,data,**extra):
                path.write_bytes(data)
                return dict(path=str(path),sha256=hashlib.sha256(data).hexdigest(),**extra)
            identities=[dict(process_id=10,path=str(root/'cdb'),creation_filetime=100,handle_retained=True),
                        dict(process_id=11,path=str(root/'candidate'),creation_filetime=101,handle_retained=True,parent_process_id=10)]
            plan={'stage':producer.STAGE,'resolution':'800x600','width':width,'height':height,'minimap_viewport':True,'out_dir':str(root),
                  'route':'barracks','castle_index':0,'availability':'existing_flags','stop_va':0x433E77,
                  'canvas_state_va':0x596000,'canvas_state_offsets':producer.canvas.STATE}
            mapping={'original':'original_sha256','input_candidate':'candidate_sha256','candidate_path':'candidate_sha256',
                'candidate_manifest':'candidate_manifest_sha256','proxy_path':'proxy_sha256','host_path':'host_sha256',
                'producer':'producer_sha256','trace':'trace_sha256','converter':'converter_sha256',
                'proxy_source':'proxy_source_sha256','proxy_input':'proxy_sha256','proxy_manifest':'proxy_manifest_sha256',
                'python':'python_sha256','cdb':'cdb_sha256'}
            for name,key in mapping.items():
                if name in audit.SOURCE_PATHS:
                    value=ROOT/audit.SOURCE_PATHS[name]
                else:
                    value=root/('candidate' if name=='candidate_path' else name);value.write_bytes(b'fixture')
                plan[name]=str(value);plan[key]=hashlib.sha256(value.read_bytes()).hexdigest()
            identities[1]['candidate_sha256']=plan['candidate_sha256']
            ready=dict(event='READY',physical=0x20000000,native=0x23000000,physical_pixels=0x21000000,
                native_pixels=0x24000000,root_esp=0xFFFFFC,tid=0x2345)
            parsed=dict(passed=True,ready_for_host_capture=True,failures=[],modal_sequence={'raw_records':[dict(marker='MCAP_CANVAS',values=ready)]})
            state=bytearray(128)
            values=dict(phase=1,physical=ready['physical'],native=ready['native'],root_esp=ready['root_esp'],owner_tid=ready['tid'],
                enter_status=1,mirror_status=1,leave_status=0,fault=0,allocations=1,frees=0,mirrors=3,pending_header=0,
                pending_pixels=0,native_pixels=ready['native_pixels'],physical_pixels=ready['physical_pixels'])
            for key,value in values.items():state[producer.canvas.STATE[key]:producer.canvas.STATE[key]+4]=value.to_bytes(4,'little')
            def header(w,h,pixels):
                data=bytearray(188);data[:2]=w.to_bytes(2,'little');data[2:4]=h.to_bytes(2,'little')
                data[4:8]=pixels.to_bytes(4,'little');data[184:188]=(0x50EE24).to_bytes(4,'little');return bytes(data)
            header_values={'state':(0x596000,bytes(state)),'e0':(0x5202E0,ready['native'].to_bytes(4,'little')),
                'physical_header':(ready['physical'],header(width,height,ready['physical_pixels'])),
                'native_header':(ready['native'],header(640,480,ready['native_pixels']))}
            snapshots=[]
            for i in range(1,4):
                folder=root/('capture-'+str(i));folder.mkdir()
                row=artifact(folder/'surface.raw',bytes(physical),width=width,height=height,pitch=width,paused=True,capture='owned_physical_mirror',
                    physical=ready['physical'],physical_pixels=ready['physical_pixels'],game_identity=identities[1])
                row['native']=artifact(folder/'native-surface.raw',native,width=640,height=480,pitch=640,surface=ready['native'],base=ready['native_pixels'])
                row['reads']={phase:{name:artifact(folder/('surface-'+phase+'-'+name+'.raw'),data,address=address)
                    for name,(address,data) in header_values.items()} for phase in ('before','after')}
                snapshots.append(row)
            packet={key:plan[key] for key in ('stage','resolution','castle_index','availability','minimap_viewport','candidate_sha256',
                    'original_sha256','stop_va','canvas_state_va','canvas_state_offsets')}
            packet.update(route={'name':'barracks'},capture_source_hashes={relative:hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()
                for relative in audit.SOURCE_PATHS.values()},
                candidate_manifest={'path':str(Path(plan['candidate_manifest']).resolve()),'sha256':plan['candidate_manifest_sha256']})
            plan['probe_sha256']=hashlib.sha256(b'probe').hexdigest()
            summary=dict(schema='clash95_modal_slots_capture_v1',passed=True,executed=True,failures=[],plan=plan,
                packet=artifact(root/'packet.json',json.dumps(packet).encode()),probe=artifact(root/'modal-slots-barracks.cdb',b'probe'),
                final_log=artifact(root/'cdb.log',b'prefix tail'),capture_prefix=artifact(root/'capture-prefix.log',b'prefix'),
                clean_stable_pair=True,snapshots=snapshots,snapshot=snapshots[0],cdb=identities[0],candidates=[identities[1]],
                cleanup=dict(desktop_closed=True,cdb=dict(identity=identities[0],absent=True,handle_closed=True),
                    candidates=[dict(identity=identities[1],absent=True,handle_closed=True)]))
            path=root/'summary.json'
            def run(value=summary):
                path.write_text(json.dumps(value));return audit.evaluate(path)
            with patch.object(trace,'evaluate_trace',return_value=parsed):
                result=run();self.assertTrue(result['passed'],result['failures']);self.assertEqual(len(result['captures']),3)
                for mutate in ('native_size','pointer','raw_hash','cross_run','state','cleanup','identity','plan_resolution','plan_route',
                               'plan_availability','plan_source_alias','state_path_reuse','header_phase_reuse','probe_path_alias','wrong_summary_dir'):
                    bad=copy.deepcopy(summary)
                    if mutate=='native_size':bad['snapshots'][2]['native']['pitch']=800
                    elif mutate=='pointer':bad['snapshots'][2]['native']['base']+=4
                    elif mutate=='raw_hash':bad['snapshots'][1]['sha256']='0'*64
                    elif mutate=='cross_run':bad['snapshots'][2]['path']=bad['snapshots'][1]['path']
                    elif mutate=='state':bad['snapshots'][2]['reads']['before']['state']['address']+=4
                    elif mutate=='cleanup':bad['cleanup']['candidates'][0]['absent']=False
                    elif mutate=='identity':bad['snapshots'][2]['game_identity']=dict(bad['snapshots'][2]['game_identity'],process_id=99)
                    elif mutate=='plan_resolution':bad['plan']['resolution']='1920x1080'
                    elif mutate=='plan_route':bad['plan']['route']='court'
                    elif mutate=='plan_availability':bad['plan']['availability']='construct_all'
                    elif mutate=='plan_source_alias':
                        alias=root/'equal-content-host.ps1';alias.write_bytes(Path(plan['host_path']).read_bytes())
                        bad['plan']['host_path']=str(alias)
                    elif mutate=='state_path_reuse':bad['snapshots'][2]['reads']['before']['state']=copy.deepcopy(bad['snapshots'][0]['reads']['before']['state'])
                    elif mutate=='header_phase_reuse':bad['snapshots'][2]['reads']['after']['native_header']=copy.deepcopy(bad['snapshots'][2]['reads']['before']['native_header'])
                    elif mutate=='probe_path_alias':bad['probe']=artifact(root/'equal-content-probe.cdb',b'probe')
                    else:bad['plan']['out_dir']=str(root/'another-run')
                    with self.subTest(mutate=mutate):self.assertFalse(run(bad)['passed'])
            with patch.object(trace,'evaluate_trace',return_value=dict(parsed,passed=False,ready_for_host_capture=False,failures=['original incomplete trace'])):
                result=run();self.assertFalse(result['passed']);self.assertIn('re-evaluated trace: original incomplete trace',result['failures'])


PRELUDE=r'''
param([string]$HostPath,[string]$FixtureRoot,[string]$Mode)
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($HostPath,[ref]$tokens,[ref]$errors)
if ($errors.Count) {throw ($errors | Out-String)}
function Import-Function {
 param([string]$Name)
 $nodes=@($ast.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $Name},$true))
 if ($nodes.Count -ne 1) {throw 'missing unique function'}
 . ([scriptblock]::Create($nodes[0].Extent.Text.Replace(('function '+$Name+' {'),('function global:'+$Name+' {'))))
}
function Assert-Case {param([bool]$Value);if (-not $Value) {throw 'fixture assertion failed'}}
'''
TRIPLET=r'''
Import-Function Save-CanvasTriplet
$script:Count=0
function Save-CanvasSnapshot {
 param($OwnedGame,$Evidence,$RawPath,$Plan)
 $script:Count++
 [IO.File]::WriteAllBytes($RawPath,[byte[]](1,2,3))
 $pixel=if ($Mode -eq 'pixels' -and $script:Count -eq 2) {'changed'} else {'same'}
 $state=if ($Mode -eq 'state' -and $script:Count -eq 3) {'changed'} else {'same'}
 return @{path=$RawPath;sha256=$pixel;native=@{sha256='native'};reads=@{before=@{
  state=@{sha256=$state};e0=@{sha256='e0'};physical_header=@{sha256='physical'};native_header=@{sha256='nativeheader'}}}}
}
$result=Save-CanvasTriplet @{handle=123} @{} @{out_dir=$FixtureRoot}
Assert-Case ($script:Count -eq 3 -and $result.snapshots.Count -eq 3)
Assert-Case ($result.clean_stable_pair -eq ($Mode -eq 'normal'))
foreach ($i in 1..3) {Assert-Case (Test-Path -LiteralPath (Join-Path $FixtureRoot ('capture-'+$i+'\surface.raw')))}
@{passed=$true;actual_captures=$result.snapshots.Count} | ConvertTo-Json
'''
SNAPSHOT_PATHS=r'''
Import-Function Get-CanvasHash
Import-Function Save-CanvasSnapshot
Import-Function Save-CanvasTriplet
$offsets=@{phase=0;physical=4;native=8;root_esp=16;owner_tid=20;enter_status=24;mirror_status=28;
 leave_status=32;fault=36;allocations=40;frees=44;mirrors=48;pending_header=52;pending_pixels=56;native_pixels=60;physical_pixels=64}
$values=@{phase=1;physical=0x20000000;native=0x23000000;root_esp=0xfffffc;owner_tid=0x2345;enter_status=1;
 mirror_status=1;leave_status=0;fault=0;allocations=1;frees=0;mirrors=3;pending_header=0;pending_pixels=0;
 native_pixels=0x24000000;physical_pixels=0x21000000}
$script:StateBytes=New-Object byte[] 128
foreach ($name in $values.Keys) {[BitConverter]::GetBytes([uint32]$values[$name]).CopyTo($script:StateBytes,$offsets[$name])}
function New-FixtureHeader {
 param([uint16]$Width,[uint16]$Height,[uint32]$Pixels)
 $bytes=New-Object byte[] 188
 [BitConverter]::GetBytes($Width).CopyTo($bytes,0);[BitConverter]::GetBytes($Height).CopyTo($bytes,2)
 [BitConverter]::GetBytes($Pixels).CopyTo($bytes,4);[BitConverter]::GetBytes([uint32]0x50ee24).CopyTo($bytes,184)
 return ,$bytes
}
$script:PhysicalHeader=New-FixtureHeader 1024 768 0x21000000
$script:NativeHeader=New-FixtureHeader 640 480 0x24000000
$script:MemoryReads=0
function Read-CanvasMemory {
 param($Handle,[long]$Address,[int]$Count)
 Assert-Case ($Handle -eq 123)
 $script:MemoryReads++
 $data=switch ($Address) {
  0x596000 {,$script:StateBytes;break}
  0x5202e0 {,([BitConverter]::GetBytes([uint32]0x23000000));break}
  0x20000000 {,$script:PhysicalHeader;break}
  0x23000000 {,$script:NativeHeader;break}
  0x21000000 {,(New-Object byte[] 786432);break}
  0x24000000 {,(New-Object byte[] 307200);break}
  default {throw 'unreviewed synthetic memory address'}
 }
 Assert-Case ($data.Length -eq $Count)
 return ,([byte[]]$data)
}
$evidence=@{surface=@{surface=0x20000000;base=0x21000000;width=1024;height=768;bytes=786432;tid=0x2345};
 canvas=@{native=0x23000000;native_pixels=0x24000000;root_esp=0xfffffc;mirrors=3}}
$plan=@{out_dir=$FixtureRoot;canvas_state_va=0x596000;canvas_state_offsets=$offsets}
$result=Save-CanvasTriplet @{handle=123;identity=@{process_id=99}} $evidence $plan
Assert-Case ($result.clean_stable_pair -and $result.snapshots.Count -eq 3 -and $script:MemoryReads -eq 30)
$paths=@()
foreach ($index in 1..3) {
 $snapshot=$result.snapshots[$index-1];$directory=Join-Path $FixtureRoot ('capture-'+$index)
 Assert-Case ($snapshot.path -ceq (Join-Path $directory 'surface.raw'))
 Assert-Case ($snapshot.native.path -ceq (Join-Path $directory 'native-surface.raw'))
 Assert-Case ([IO.File]::ReadAllBytes($snapshot.path).Length -eq 786432)
 Assert-Case ([IO.File]::ReadAllBytes($snapshot.native.path).Length -eq 307200)
 foreach ($phase in @('before','after')) {
  foreach ($name in @('state','e0','physical_header','native_header')) {
   $row=$snapshot.reads[$phase][$name]
   $expected=Join-Path $directory ('surface-'+$phase+'-'+$name+'.raw')
   Assert-Case ($row.path -ceq $expected)
   Assert-Case ((Get-CanvasHash $expected) -ceq $row.sha256)
   $paths+=('capture-'+$index+'/'+[IO.Path]::GetFileName($row.path))
  }
 }
}
@{passed=$true;paths=$paths;memory_reads=$script:MemoryReads;captures=$result.snapshots.Count} | ConvertTo-Json
'''
CLEANUP=r'''
Import-Function Stop-CanvasOwned
Add-Type @'
using System;using System.Collections.Generic;
public class CanvasScreenNative {
 public static List<string> Calls=new List<string>();public static string Mode="normal";static int count;
 public static uint WaitForSingleObject(IntPtr h,uint timeout){Calls.Add("wait:"+h+":"+timeout);count++;return Mode=="failure"?258u:(count==1&&Mode!="exited"?258u:0u);}
 public static bool TerminateProcess(IntPtr h,uint exit){Calls.Add("terminate:"+h);return true;}
 public static bool CloseHandle(IntPtr h){Calls.Add("close:"+h);return true;}
}
'@
[CanvasScreenNative]::Mode=$Mode
$identity=@{process_id=77;creation_time=12345;image='fixture'}
$result=Stop-CanvasOwned @{handle=[IntPtr]123;identity=$identity}
Assert-Case ($result.identity -eq $identity -and $result.handle_closed)
Assert-Case ($result.absent -eq ($Mode -ne 'failure'))
Assert-Case ($result.termination_requested -eq ($Mode -ne 'exited'))
Assert-Case ([CanvasScreenNative]::Calls[-1] -ceq 'close:123')
@{passed=$true;calls=@([CanvasScreenNative]::Calls)} | ConvertTo-Json
'''
CHILD_FAILURE=r'''
Import-Function ConvertTo-CanvasArgument
Import-Function Invoke-CanvasPythonJson
$child=Join-Path $FixtureRoot 'synthetic-validator.py'
[IO.File]::WriteAllText($child, @'
import json,sys
print(json.dumps({'passed':False,'failures':['source snapshot differs','candidate recipe mismatch'],
                  'irrelevant_prepared_packet':'do-not-copy-this-packet'*50000}))
sys.exit(2)
'@)
# Execute only the real final reporting catch around the extracted offline
# helper. No preparation, game, debugger or native capture body is imported.
$outer=@($ast.EndBlock.Statements | Where-Object {$_ -is [System.Management.Automation.Language.TryStatementAst]})
Assert-Case ($outer.Count -eq 1 -and $outer[0].CatchClauses.Count -eq 1)
$body='try { $null=Invoke-CanvasPythonJson $Mode @($child) } catch '+$outer[0].CatchClauses[0].Body.Extent.Text
& ([scriptblock]::Create($body))
throw 'failed Python exit was incorrectly accepted'
'''


@unittest.skipUnless(os.name=='nt' and PS.is_file(),'Windows PowerShell parser required')
class HostBoundaryTests(unittest.TestCase):
    def run_ps(self,body,mode='normal',expected_exit=0):
        with tempfile.TemporaryDirectory(prefix='slots-host-fixture-') as directory:
            script=Path(directory)/'test.ps1';script.write_text(PRELUDE+body,encoding='utf-8-sig')
            result=subprocess.run([str(PS),'-NoProfile','-NonInteractive','-File',str(script),'-HostPath',str(HOST),
                '-FixtureRoot',directory,'-Mode',mode],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
            self.assertEqual(result.returncode,expected_exit,result.stdout+result.stderr)
            return json.loads(result.stdout)

    def test_nonexecuting_syntax_and_three_distinct_paused_capture_records(self):
        for mode in ('normal','pixels','state'):
            self.assertTrue(self.run_ps(TRIPLET,mode)['passed'])

    def test_real_snapshot_triplet_writes_all_24_exact_audit_header_paths(self):
        result=self.run_ps(SNAPSHOT_PATHS)
        expected=[f'capture-{index}/surface-{phase}-{name}.raw' for index in (1,2,3)
                  for phase in ('before','after') for name in ('state','e0','physical_header','native_header')]
        self.assertEqual(result['paths'],expected)
        self.assertEqual(result['memory_reads'],30)
        self.assertEqual(result['captures'],3)

    def test_retained_handle_cleanup_and_failed_absence_never_pass(self):
        for mode in ('normal','exited','failure'):
            self.assertTrue(self.run_ps(CLEANUP,mode)['passed'])

    def test_child_failure_json_survives_outer_preparation_failure_and_nonzero_exit(self):
        result=self.run_ps(CHILD_FAILURE,sys.executable,expected_exit=1)
        self.assertEqual(result['status'],'preparation_failed')
        self.assertFalse(result['passed']);self.assertFalse(result['executed'])
        self.assertEqual(result['child_failure'],dict(exit_code=2,
            failures=['source snapshot differs','candidate recipe mismatch'],stderr=''))
        self.assertIn('source snapshot differs',result['failures'][0])
        self.assertIn('candidate recipe mismatch',result['failures'][0])
        self.assertNotIn('do-not-copy-this-packet',json.dumps(result))


if __name__=='__main__':unittest.main(verbosity=2)
