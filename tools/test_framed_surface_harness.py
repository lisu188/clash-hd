#!/usr/bin/env python3
"""Safe AST/expression fixtures for the framed hidden-surface harness.

Only allowlisted option, observation, parser and argument-building fragments
execute against synthetic values. No harness, native API, game, CDB, builder,
process inspection or capture runs. Temporary files contain fixture text/JSON.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

import render_cdb_surface_probe as render

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts/cdb/run_cdb_surface_dump.ps1"
POWERSHELL = Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
STAGE = render.FRAMED_STAGE
SHA = "ab"*32

FIXTURE = r'''
param([string]$Runner,[string]$RepoRoot,[string]$CasesPath)
$ErrorActionPreference='Stop'
$tokens=$null; $errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($Runner,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
$cases=Get-Content -LiteralPath $CasesPath -Raw | ConvertFrom-Json
$commands=@('Join-Path','Test-Path','Where-Object')
$methods=@('GetFullPath','StartsWith','Replace','Match','Contains','ContainsKey','Remove','ToUInt64','Floor','Ceiling','Max','ToLowerInvariant','TryParse')
function Pure($node) {
 foreach ($c in $node.FindAll({param($n) $n -is [System.Management.Automation.Language.CommandAst]},$true)) {
  if ($c.GetCommandName() -notin $commands) { throw "Unsafe extracted command: $($c.Extent.Text)" }
 }
 foreach ($m in $node.FindAll({param($n) $n -is [System.Management.Automation.Language.InvokeMemberExpressionAst]},$true)) {
  if ($m.Member.Value -notin $methods) { throw "Unsafe extracted method: $($m.Extent.Text)" }
 }
}
function Pick([string]$kind,[string]$name,[string]$needle='') {
 $nodes=@($ast.FindAll({param($n)
  if ($kind -eq 'assignment') { return $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq $name -and $n.Extent.Text.Contains($needle) }
  if ($kind -eq 'if') { return $n -is [System.Management.Automation.Language.IfStatementAst] -and $n.Clauses[0].Item1.Extent.Text -eq $name -and $n.Extent.Text.Contains($needle) }
  if ($kind -eq 'function') { return $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name }
 },$true))
 if ($nodes.Count -ne 1) { throw "Ambiguous pure fragment: $kind $name $needle count=$($nodes.Count)" }
 Pure $nodes[0]
 return $nodes[0].Extent.Text
}
$framedGate=Pick 'if' '$FramedValidation -and (-not $PartialTileValidation -or -not $InitialMapPaintValidation)'
$minimapGate=Pick 'if' '$MinimapViewportValidation -and -not $FramedValidation'
$initialGate=Pick 'if' '$InitialMapPaintValidation -and -not $PartialTileValidation'
$options=Pick 'if' '$PartialTileValidation' '$partialBase ='
$renderArgsCode=Pick 'assignment' '$renderArgs' '$probeRenderer'
$minimapActionCode=Pick 'assignment' '$framedMinimapAction'
$insertCode=Pick 'assignment' '$probeText' '$framedMinimapAction + $surfaceDumpAction'
$minimapParse=Pick 'if' '$FramedValidation' '$minimapRows ='
$coverageBase=Pick 'assignment' '$coverageArgs' '$coverageTool'
$coverageMode=Pick 'if' '$FramedValidation' '$coverageArgs +='
$gameplayMode=Pick 'if' '$RequireGameplay' '$coverageArgs +='
$validator=Pick 'function' 'Get-PartialTileValidationFailure'
. ([scriptblock]::Create($validator))
function Test-Path { param([string]$LiteralPath,[string]$PathType)
 if ($LiteralPath -ne $partialTileBuilder -or $PathType -ne 'Leaf') { throw 'Unexpected mock path access' }
 return -not $script:MissingBuilder
}
$result=[ordered]@{options=@(); minimaps=@(); coverage=@(); actions=@(); logs=@()}
foreach ($case in $cases.options) {
 $PartialTileValidation=$true; $InitialMapPaintValidation=$true; $FramedValidation=$true
 $MinimapViewportValidation=$false
 $Stage=$cases.stage; $UseDdrawProxy=$true; $AllowVisibleDesktop=$false; $ExtraProbeTemplate=''
 $ForceVisibleEdges=$false; $PostOwnerForceVisibleSeven=$false; $SkipMapValidation=$false
 $UseCdbWriteMem=$false; $LoadSlot=0; $ContinueAfterDumpSec=0; $RequireGameplay=$false
 $ProbeTemplate=Join-Path $RepoRoot 'probes\cdb\render\clash95_surface_dump_probe.cdb'
 $CandidateDir='C:\ClashTests\synthetic-framed\candidate'; $WorkDir='C:\ClashTests\synthetic-framed\work'
 $OutRoot='C:\ClashCaptures\synthetic-framed'; $Resolution='800x600'
 $partialTileBuilder=Join-Path $RepoRoot 'tools\build_partial_tile_candidate.py'
 $probeRenderer=Join-Path $RepoRoot 'tools\render_cdb_surface_probe.py'
 $recipeStage=$Stage; $partialBuilderOptions=@(); $script:MissingBuilder=$false
 foreach ($property in $case.values.PSObject.Properties) {
  if ($property.Name -eq 'MissingBuilder') { $script:MissingBuilder=$property.Value }
  else { Set-Variable -Name $property.Name -Value $property.Value }
 }
 $failure=$null
 try {
  . ([scriptblock]::Create($minimapGate)); . ([scriptblock]::Create($framedGate)); . ([scriptblock]::Create($initialGate)); . ([scriptblock]::Create($options))
  . ([scriptblock]::Create($renderArgsCode))
 } catch { $failure=$_.Exception.Message }
 $result.options += [pscustomobject]@{name=$case.name; error=$failure; recipe=$recipeStage; builder=$partialTileBuilder;
  builder_options=@($partialBuilderOptions); renderer=@($renderArgs); gameplay=$RequireGameplay}
}
foreach ($enabled in @($false,$true)) {
 $FramedValidation=$enabled; $surfaceDumpAction='.echo SYNTHETIC_CAPTURE_BOUNDARY;'; $probeText='before __SURFACE_DUMP_ACTION__ after'
 . ([scriptblock]::Create($minimapActionCode)); . ([scriptblock]::Create($insertCode))
 $result.actions += [pscustomobject]@{framed=$enabled; action=$framedMinimapAction; inserted=$probeText}
}
foreach ($case in $cases.minimaps) {
 $FramedValidation=$case.framed; $logText=$case.log; $surfaceGeometry=[pscustomobject]@{width=$case.width; height=$case.height}
 $partialValidationFailure=$case.prior_error; $framedMinimap=$null
 . ([scriptblock]::Create($minimapParse))
 $result.minimaps += [pscustomobject]@{name=$case.name; error=$partialValidationFailure; observation=$framedMinimap}
}
foreach ($case in $cases.coverage) {
 $FramedValidation=$case.framed; $Stage=$cases.stage; $RequireGameplay=$case.gameplay
 $ready=[pscustomobject]@{Width=$case.width; Height=$case.height}
 $surfaceGeometry=[pscustomobject]@{columns=$case.columns; rows=$case.rows}
 $framedMinimap=[pscustomobject]@{Enabled=$case.enabled; Width=$case.mw; Height=$case.mh}
 $coverageTool='synthetic-map-coverage.py'; $pngPath='synthetic-frame.png'; $coverageJson='synthetic-coverage.json'
 . ([scriptblock]::Create($coverageBase)); . ([scriptblock]::Create($coverageMode)); . ([scriptblock]::Create($gameplayMode))
 $result.coverage += [pscustomobject]@{name=$case.name; args=@($coverageArgs)}
}
foreach ($case in $cases.logs) {
 $failure=Get-PartialTileValidationFailure -LogText $case.log -Stage $case.stage -Resolution $case.resolution -CandidateSha256 $cases.sha
 $result.logs += [pscustomobject]@{name=$case.name; error=$failure}
}
$result | ConvertTo-Json -Depth 16 -Compress
'''


def observation(action, *, selector=0, enabled=1, game_data=0x10000000, box=(554,16,214,214)):
    """Interpret only actual emitted readonly conditions/printf, never CDB.

    Undeclared reads, writes, unknown commands and expression syntax fail.
    All values originate in the supplied synthetic dword/word maps.
    """
    source=action.replace(r'\"','"'); pos=0
    memory={0x5202E4:game_data}; words=dict(zip((0x523344,0x523346,0x523348,0x52334A),box))
    if game_data:
        memory[game_data+0x23EC7]=selector & 0xFFFFFFFF
        if 0 <= selector < 5: memory[game_data+0x2230F+selector*0x58F]=enabled & 0xFFFFFFFF
    before=dict(memory); reads=[]; events=[]; quit=False

    def skip():
        nonlocal pos
        while pos < len(source) and (source[pos].isspace() or source[pos]==';'):pos+=1

    def parse(nested=False):
        nonlocal pos
        nodes=[]
        while pos<len(source):
            skip()
            if pos==len(source):break
            if source[pos]=='}':
                if not nested:raise AssertionError('unmatched closing brace')
                pos+=1;return nodes
            if source.startswith('.if',pos):
                pos+=3;skip()
                if source[pos]!='(':raise AssertionError('missing condition')
                start=pos+1;depth=1;pos+=1
                while depth:
                    if pos>=len(source):raise AssertionError('unterminated condition')
                    depth+=(source[pos]=='(')-(source[pos]==')');pos+=1
                condition=source[start:pos-1];skip()
                if source[pos]!='{':raise AssertionError('missing conditional block')
                pos+=1;yes=parse(True);skip();no=[]
                if source.startswith('.else',pos):
                    pos+=5;skip()
                    if source[pos]!='{':raise AssertionError('missing else block')
                    pos+=1;no=parse(True)
                nodes.append(('if',condition,yes,no))
            else:
                start=pos;quoted=False
                while pos<len(source):
                    char=source[pos]
                    if char=='"':quoted=not quoted
                    if not quoted and char in ';}':break
                    pos+=1
                if quoted:raise AssertionError('unterminated printf string')
                nodes.append(('command',source[start:pos].strip()))
        if nested:raise AssertionError('unterminated block')
        return nodes

    def evaluate(text):
        tokens=re.findall(r'poi|wo|[0-9][0-9a-f]*|==|!=|>=|<=|[()+*&|<>-]|\s+',text)
        if ''.join(tokens)!=text:raise AssertionError('unsupported MASM syntax')
        text=''.join(str(int(t,16)) if re.fullmatch('[0-9a-f]+',t) else t for t in tokens)
        def visit(node):
            if isinstance(node,ast.Constant) and type(node.value)is int:return node.value
            if isinstance(node,ast.BinOp):
                left,right=visit(node.left),visit(node.right)
                if isinstance(node.op,ast.Add):return left+right
                if isinstance(node.op,ast.Mult):return left*right
                if isinstance(node.op,ast.Sub):return left-right
                if isinstance(node.op,ast.BitAnd):return left & right
                if isinstance(node.op,ast.BitOr):return left | right
            if isinstance(node,ast.Compare) and len(node.ops)==1:
                left,right=visit(node.left),visit(node.comparators[0]);op=node.ops[0]
                if isinstance(op,ast.Eq):return int(left==right)
                if isinstance(op,ast.NotEq):return int(left!=right)
                if isinstance(op,ast.GtE):return int(left>=right)
                if isinstance(op,ast.Gt):return int(left>right)
                if isinstance(op,ast.LtE):return int(left<=right)
                if isinstance(op,ast.Lt):return int(left<right)
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and len(node.args)==1:
                address=visit(node.args[0]);name=node.func.id;reads.append((name,address))
                values=memory if name=='poi' else words if name=='wo' else {}
                if address not in values:raise AssertionError(f'undeclared/null {name} read {address:08x}')
                return values[address]
            raise AssertionError('unsupported expression AST')
        return visit(ast.parse(text.strip(),mode='eval').body)

    def execute(nodes):
        nonlocal quit
        for node in nodes:
            if quit:return
            if node[0]=='if':execute(node[2] if evaluate(node[1]) else node[3]);continue
            command=node[1]
            if command=='q':quit=True
            elif command.startswith('.echo '):events.append(command[6:])
            elif command.startswith('.printf '):
                match=re.fullmatch(r'\.printf "(.*?)", (.*)',command)
                if not match:raise AssertionError('unsupported printf')
                fmt,args=match.groups();values=iter(evaluate(arg.strip()) for arg in args.split(','))
                line=re.sub('%d',lambda _:str(next(values)),fmt)
                if next(values,None)is not None or '%' in line:raise AssertionError('printf arity mismatch')
                events.append(line.removesuffix(r'\\n'))
            else:raise AssertionError('mutating or unknown debugger command: '+command)
    execute(parse())
    if memory!=before:raise AssertionError('observer wrote memory')
    return dict(events=events,reads=reads,quit=quit)


def scenarios():
    options=[dict(name='framed',values={},passed=True),
             dict(name='framed_minimap',values=dict(MinimapViewportValidation=True),passed=True),
             dict(name='minimap_without_frame',values=dict(MinimapViewportValidation=True,FramedValidation=False),passed=False),
             dict(name='minimap_without_partial',values=dict(MinimapViewportValidation=True,PartialTileValidation=False),passed=False),
             dict(name='minimap_visible',values=dict(MinimapViewportValidation=True,AllowVisibleDesktop=True),passed=False),
             dict(name='minimap_extra',values=dict(MinimapViewportValidation=True,ExtraProbeTemplate='synthetic.cdb'),passed=False)]
    for name,values in (
        ('no_partial',dict(PartialTileValidation=False)),('no_initial',dict(InitialMapPaintValidation=False)),
        ('wrong_stage',dict(Stage=render.patcher.DEFAULT_STAGE)),('no_proxy',dict(UseDdrawProxy=False)),
        ('visible',dict(AllowVisibleDesktop=True)),('extra',dict(ExtraProbeTemplate='synthetic.cdb')),
        ('force',dict(ForceVisibleEdges=True)),('postforce',dict(PostOwnerForceVisibleSeven=True)),
        ('skip',dict(SkipMapValidation=True)),('cdbwrite',dict(UseCdbWriteMem=True)),('slot',dict(LoadSlot=1)),
        ('grace',dict(ContinueAfterDumpSec=1)),('builder_missing',dict(MissingBuilder=True)),
        ('candidate_escape',dict(CandidateDir='C:\\ClashTests\\..\\Windows\\candidate')),
        ('workdir_original',dict(WorkDir='C:\\Clash')),('output_repo',dict(OutRoot=str(ROOT/'captures'))),
    ):options.append(dict(name=name,values=values,passed=False))
    options += [dict(name='legacy_initial',values=dict(FramedValidation=False,Stage=STAGE.replace('-framed','')),passed=True),
                dict(name='legacy_partial',values=dict(FramedValidation=False,InitialMapPaintValidation=False,
                     Stage=STAGE.replace('-initialpaint-framed','')),passed=True)]
    minimaps=[]
    def add(name,line,passed=False,**changes):
        minimaps.append(dict(name=name,log=line,passed=passed,width=800,height=600,framed=True,prior_error=None,**changes))
    good='FRAMED_MINIMAP enabled=1 origin=(554,16) size=(214,214)'
    add('valid',good,True); add('off','FRAMED_MINIMAP enabled=0 origin=(0,0) size=(0,0)',True)
    for name,line in (('missing',''),('duplicate',good+'\n'+good),('malformed',good+' trailing'),
             ('badflag',good.replace('enabled=1','enabled=2')),('zero_width',good.replace('(214,214)','(0,214)')),
             ('zero_height',good.replace('(214,214)','(214,0)')),('left',good.replace('(554,16)','(553,16)')),
             ('top',good.replace('(554,16)','(554,17)')),('height',good.replace('(214,214)','(214,569)')),
             ('negative',good.replace('(214,214)','(-1,214)')),('overwide',good.replace('(214,214)','(9999,214)')),
             ('rejected',good+'\nFRAMED_CAPTURE_REJECT minimap_selector')):add(name,line)
    minimaps.append(dict(name='prior',log=good,passed=False,width=800,height=600,framed=True,prior_error='prior failure'))
    minimaps.append(dict(name='legacy_ignores',log='unrelated',passed=True,width=800,height=600,framed=False,prior_error=None))
    minimaps.append(dict(name='1024',log=good.replace('(554,16)','(778,16)'),passed=True,width=1024,height=768,framed=True,prior_error=None))
    coverage=[dict(name=f'{w}_{framed}_{enabled}',framed=framed,enabled=enabled,width=w,height=h,
                   columns=(w-1)//64,rows=(h+31)//64,mw=214,mh=213,gameplay=True)
              for w,h in ((800,600),(1024,768)) for framed in (False,True) for enabled in (0,1)]
    logs=[]
    def log(name,world,status,passed,resolution='800x600',scroll=(10,17),stage=STAGE):
        width,height=map(int,resolution.split('x'));x,y=world;native_sp=0xEDC24
        prefix=[f'PTILE_CONTRACT_PASS stage={stage} resolution={resolution} candidate_sha256={SHA}',
                f'PTILE_MAP_READY owner=0040ad40 size=({width},{height})']
        for hook in ('full_converge','full_present'):
            prefix.append(f'PTILE_STATUS hook={hook} status=1 tid=3ac esp=000ed000 owner=0040ad40 tile=00000000 post=00000000 lower=00000000 player=0')
        prefix.append(f'PTILE_COMPOSITION_GUARD tid=3ac esp={native_sp-120:08x} status=1 world=({x},{y}) cell=({x-scroll[0]},{y-scroll[1]}) present=1 caller=00407125')
        def observed(kind,sp):
            return f'PTILE_{kind} tid=3ac esp={sp:08x} world=({x},{y}) caller=00407125 gd=03e60030 map=(100,100) scroll=({scroll[0]},{scroll[1]}) vtable=0050ee24'
        prefix += [observed('INCREMENTAL_INPUT',native_sp-36),f'PTILE_STATUS hook=incremental status={status} tid=3ac esp={native_sp-36:08x} owner=0040ad40 tile=00000000 post=00000000 lower=00000000 player=0']
        if status==0:prefix.append(observed('NATIVE_NOOP_EXIT',native_sp-28))
        logs.append(dict(name=name,log='\n'.join(prefix),stage=stage,resolution=resolution,passed=passed))
    log('framed800_partial', (21,25),1,True);log('framed800_partial_zero',(21,25),0,False)
    log('framed1024_last_visible',(24,28),1,True,'1024x768')
    log('framed1024_last_visible_zero',(24,28),0,False,'1024x768')
    log('framed1024_new_right_noop',(25,20),0,True,'1024x768')
    log('framed800_floor_farworld_clear',(100,20),2,True,scroll=(89,17))
    log('framed800_scroll_overflow',(14,20),1,False,scroll=(90,17))
    log('unknown_framed',(14,20),1,False,stage=STAGE+'-extra')
    return dict(stage=STAGE,sha=SHA,options=options,minimaps=minimaps,coverage=coverage,logs=logs)


@unittest.skipUnless(sys.platform=='win32' and POWERSHELL.is_file(),'requires PowerShell AST parser')
class FramedHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=scenarios()
        with tempfile.TemporaryDirectory(prefix='clash-framed-harness-fixture-') as folder:
            path=Path(folder);script=path/'fixture.ps1';cases=path/'cases.json'
            script.write_text(FIXTURE,encoding='utf-8');cases.write_text(json.dumps(cls.cases),encoding='utf-8')
            ran=subprocess.run([str(POWERSHELL),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                                '-File',str(script),str(HARNESS),str(ROOT),str(cases)],capture_output=True,text=True,timeout=60)
            if ran.returncode:raise AssertionError(ran.stdout+ran.stderr)
            cls.result=json.loads(ran.stdout)

    def test_actual_option_gates_select_final_renderer_and_framed_builder(self):
        for case,row in zip(self.cases['options'],self.result['options']):
            self.assertEqual(row['error'] is None,case['passed'],row)
            if not case['passed']:continue
            self.assertTrue(row['gameplay'])
            args=row['renderer'];self.assertEqual(args[args.index('--stage')+1],row['recipe'])
            if case['name'] in ('framed','framed_minimap'):
                self.assertEqual(row['recipe'],STAGE)
                self.assertTrue(row['builder'].endswith('tools\\build_framed_candidate.py'))
                self.assertEqual(row['builder_options'],['--minimap-viewport'] if case['name']=='framed_minimap' else [])
            else:
                self.assertEqual(row['recipe'],render.patcher.DEFAULT_STAGE+'-combinedui-validation')
                self.assertTrue(row['builder'].endswith('tools\\build_partial_tile_candidate.py'))
                self.assertEqual(row['builder_options'],['--initial-map-paint'] if case['name']=='legacy_initial' else [])

    def test_actual_observer_is_readonly_and_binds_all_five_selector_flags(self):
        disabled,enabled=self.result['actions'];self.assertEqual(disabled['action'],'')
        self.assertEqual(disabled['inserted'],'before .echo SYNTHETIC_CAPTURE_BOUNDARY; after')
        self.assertLess(enabled['inserted'].index('FRAMED_MINIMAP'),enabled['inserted'].index('SYNTHETIC_CAPTURE_BOUNDARY'))
        for selector in range(5):
            for flag in (0,1,2,0xFFFFFFFF):
                data=observation(enabled['action'],selector=selector,enabled=flag)
                self.assertFalse(data['quit'])
                self.assertEqual(data['events'],[f'FRAMED_MINIMAP enabled={int(flag!=0)} origin=(554,16) size=(214,214)'])
                self.assertIn(('poi',0x10000000+0x2230F+selector*0x58F),data['reads'])
                self.assertNotIn(('poi',0x5202EC),data['reads'],'wrong player selector')
        for selector in (5,0xFFFFFFFF):
            data=observation(enabled['action'],selector=selector)
            self.assertTrue(data['quit']);self.assertEqual(data['events'],['FRAMED_CAPTURE_REJECT minimap_selector'])
            self.assertTrue(all(address in (0x5202E4,0x10023EC7) for _,address in data['reads']))
        data=observation(enabled['action'],game_data=0)
        self.assertTrue(data['quit']);self.assertEqual(data['reads'],[('poi',0x5202E4)])
        with self.assertRaisesRegex(AssertionError,'mutating'):
            observation(enabled['action']+' ed 005202ec 1;')

    def test_actual_minimap_parser_rejects_missing_duplicate_bad_backing_and_prior_errors(self):
        for case,row in zip(self.cases['minimaps'],self.result['minimaps']):
            self.assertEqual(row['error'] is None,case['passed'],row)
            if case['name']=='prior':self.assertEqual(row['error'],'prior failure')
            if case['name']=='valid':self.assertEqual(row['observation'],dict(Enabled=1,Left=554,Top=16,Width=214,Height=214))
            if case['name']=='legacy_ignores':self.assertIsNone(row['observation'])

    def test_actual_coverage_args_use_measured_backing_and_no_framed_grid_override(self):
        for case,row in zip(self.cases['coverage'],self.result['coverage']):
            args=row['args']
            self.assertEqual(args[args.index('--logical-width')+1],case['width'])
            self.assertEqual(args[args.index('--logical-height')+1],case['height'])
            self.assertIn('--require-gameplay',args)
            if case['framed']:
                self.assertEqual(args[args.index('--stage')+1],STAGE)
                self.assertEqual(args[args.index('--minimap-enabled')+1],case['enabled'])
                self.assertFalse(set(args)&{'--columns','--rows','--bottom-row-active-cols'})
                if case['enabled']:
                    self.assertEqual(args[args.index('--minimap-width')+1],214)
                    self.assertEqual(args[args.index('--minimap-height')+1],213)
                else:self.assertNotIn('--minimap-width',args)
            else:
                self.assertNotIn('--stage',args);self.assertNotIn('--minimap-enabled',args)
                self.assertEqual(args[args.index('--columns')+1],case['columns'])

    def test_actual_partial_validator_uses_framed_floor_clamp_and_ceiling_admission(self):
        for case,row in zip(self.cases['logs'],self.result['logs']):
            self.assertEqual(row['error'] is None,case['passed'],row)


if __name__=='__main__':unittest.main()
