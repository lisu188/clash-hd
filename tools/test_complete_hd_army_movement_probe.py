"""Offline Complete-HD movement-v3 port, candidate and guard fixtures.

Each resolution is reconstructed once from authenticated user-owned bytes. The
real context verifier reuses only those exact cached reconstruction results;
all native guards are evaluated offline. No runtime, input or capture is run.
"""
from __future__ import annotations
import ast
import copy
import json
import os
import operator
from pathlib import Path
import re
import struct
import unittest
from unittest.mock import patch

import complete_hd_army_movement_probe as probe
import framed_army_movement_probe as frozen

def local_path(value):
    # Authenticated fixtures can run with Windows Python or WSL Python.
    if os.name != 'nt' and re.match(r'^[A-Za-z]:[/\\]', value):
        value = '/mnt/' + value[0].lower() + '/' + value[3:].replace('\\', '/')
    return Path(value)


ORIGINAL=local_path(os.environ.get('CLASH95_ORIGINAL','C:/Clash/clash95.exe'))
SAVE=local_path(os.environ.get('CLASH95_SELECTION_SAVE',
    'C:/ClashTests/hd-completion/framed-screens-20260906-034725/workdir/save/0.dat'))
CAPTURE='C:/ClashCaptures/offline-complete-movement-probe-fixture'



def expression(text,registers,memory):
    """Independent eager MASM integer subset; preserves64-bit sign extension."""
    text=re.sub(r'\b(?:0x[0-9a-f]+|0n[0-9]+|[0-9a-f]+)\b',
        lambda m:str(int(m[0][2:],10) if m[0].startswith('0n') else int(m[0],16)),text)
    text=text.replace('@$','').replace('@','')
    binary={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,
            ast.LShift:operator.lshift,ast.BitAnd:operator.and_,ast.BitOr:operator.or_}
    comparisons={ast.Eq:operator.eq,ast.NotEq:operator.ne,ast.Lt:operator.lt,
                 ast.Gt:operator.gt,ast.LtE:operator.le,ast.GtE:operator.ge}
    def run(n):
        if isinstance(n,ast.Constant) and type(n.value) is int:return n.value
        if isinstance(n,ast.Name):return registers[n.id]
        if isinstance(n,ast.BinOp):return binary[type(n.op)](run(n.left),run(n.right))
        if isinstance(n,ast.Compare) and len(n.ops)==1:return comparisons[type(n.ops[0])](run(n.left),run(n.comparators[0]))
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and len(n.args)==1:
            value=memory.get(run(n.args[0]),0)
            return value if n.func.id=='poi' else value&((1<<{'wo':16,'by':8}[n.func.id])-1)
        raise AssertionError(ast.dump(n))
    return bool(run(ast.parse(text,mode='eval').body))


def conditions(text):
    result=[]
    for match in re.finditer(r'\.if \(',text):
        start=match.end();depth=1;end=start
        while depth:
            if text[end]=='(':depth+=1
            elif text[end]==')':depth-=1
            end+=1
        result.append(text[start:end-1])
    return result


def command(packet,n):
    rows=re.findall(r'^bp'+str(n)+r' ([0-9a-f]{8}) "(.*)"$',packet['compiled_probe'],re.M)
    assert len(rows)==1
    return int(rows[0][0],16),rows[0][1]


class MovementProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not all(p.is_file() for p in (ORIGINAL,SAVE)):
            raise unittest.SkipTest('authenticated local original/save required; set CLASH95_ORIGINAL and CLASH95_SELECTION_SAVE')
        cls.original=ORIGINAL.read_bytes();cls.save=SAVE.read_bytes()
        if probe.sha(cls.original)!=probe.base.builder.BASE_SHA256 or probe.sha(cls.save)!=probe.base.SAVE_SHA256:
            raise AssertionError('local original/save differs; authentic fixtures cannot substitute other bytes')
        cls.existed=local_path(CAPTURE).exists()
        cls.cases={};cls.reconstructions={}
        actual_builder=probe.base.builder.build_candidate
        def reconstruct(original,resolution):
            if original!=cls.original:
                raise ValueError('cached fixture cannot reconstruct a different original')
            if resolution not in cls.reconstructions:
                cls.reconstructions[resolution]=actual_builder(original,resolution)
            return cls.reconstructions[resolution]
        cls.cached_builder=staticmethod(reconstruct)
        for resolution in probe.base.builder.RESOLUTIONS:
            print('authenticate Complete-HD movement '+resolution,flush=True)
            candidate,metadata,canonical=reconstruct(cls.original,resolution)
            manifest=json.loads(json.dumps(metadata))
            baseline_builder=probe.base.build_selection_probe
            baseline=[]
            def remember(*args,**kwargs):
                result=baseline_builder(*args,**kwargs);baseline.append(result);return result
            # Keep the real context verifier and all manifest/byte comparisons.
            # Only deterministic reconstruction is cached after one real build.
            with patch.object(probe.base.builder,'build_candidate',side_effect=reconstruct), \
                 patch.object(probe.base.runtime,'verify_context',wraps=probe.base.runtime.verify_context) as verify, \
                 patch.object(probe.base,'build_selection_probe',side_effect=remember):
                packet=probe.build_movement_probe(cls.original,candidate,cls.save,capture_dir=CAPTURE,
                    candidate_manifest=manifest,resolution=resolution)
            if verify.call_count!=1 or len(baseline)!=1:
                raise AssertionError('movement preparation must authenticate one complete selection context')
            cls.cases[resolution]=dict(candidate=candidate,manifest=manifest,packet=packet,
                baseline=baseline[0],canonical=canonical)
        cls.candidate=cls.cases['1024x768']['candidate']
        cls.packet=cls.cases['1024x768']['packet']
        cls.baseline=cls.cases['1024x768']['baseline']

    def setUp(self):
        cached=patch.object(probe.base.builder,'build_candidate',side_effect=self.cached_builder)
        cached.start();self.addCleanup(cached.stop)

    def build(self,resolution='1024x768',**overrides):
        case=self.cases[resolution]
        args=dict(original=self.original,candidate=case['candidate'],save=self.save,
            capture_dir=CAPTURE,candidate_manifest=case['manifest'],resolution=resolution)
        args.update(overrides)
        return probe.build_movement_probe(**args)

    def test_exact_complete_identity_and_preparation_limits_at_all_six_resolutions(self):
        self.assertEqual(set(self.cases),{'800x600','1024x768','1280x720','1280x960','1920x1080','802x602'})
        for resolution,case in self.cases.items():
            with self.subTest(resolution=resolution):
                packet,manifest=case['packet'],case['manifest']
                width,height=map(int,resolution.split('x'))
                self.assertEqual(packet['schema'],'clash95_complete_hd_army_movement_probe_v1')
                self.assertEqual(packet['revision'],'complete_hd_controlled_native_whole_army_outward_move_v1')
                self.assertEqual((packet['resolution'],packet['width'],packet['height']),(resolution,width,height))
                self.assertEqual(packet['stage'],probe.base.builder.STAGE)
                self.assertEqual(packet['candidate_recipe'],probe.base.builder.REVISION)
                self.assertEqual(packet['candidate_sha256'],probe.sha(case['candidate']))
                self.assertEqual(packet['candidate_manifest_canonical_sha256'],probe.sha(
                    json.dumps(manifest,sort_keys=True,separators=(',',':'),allow_nan=False).encode()))
                for key in ('inherited_stage','inherited_revision','startup_recipe'):
                    self.assertEqual(packet[key],case['baseline'][key])
                self.assertEqual(packet['parent_source_sha256'],probe.PARENT_SOURCE_SHA256)
                self.assertEqual(packet['capture_class'],'e0_software_diagnostic')
                self.assertIs(packet['minimap_viewport'],True)
                for key in ('runtime_executed','manual_input_proof','promotion_ready','native_predicate_forced',
                            'selected_value_forced','flag_value_forced','movement_state_forced'):
                    self.assertIs(packet[key],False)
                for path,digest in packet['source_sha256'].items():
                    self.assertEqual(probe.sha((probe.ROOT/path).read_bytes()),digest,path)
                self.assertEqual(packet['probe_sha256'],probe.sha(packet['compiled_probe'].encode('ascii')))
                self.assertEqual(packet['controlled_mouse'],[576,176])
                self.assertLess(576,width-16);self.assertLess(176,height-80)
                all_text=packet['compiled_probe']+'\n'+'\n'.join(packet['supplemental_commands'].values())
                self.assertLessEqual(max(len(line.encode('ascii')) for line in all_text.splitlines()),4095)
                self.assertEqual(all_text.count('WMOV_HOST_READY'),1)
                numbers=re.findall(r'^bp([0-9]+) ',packet['compiled_probe'],re.M)
                self.assertEqual(len(numbers),len(set(numbers)))
                self.assertTrue(any('independent full-protocol' in item for item in packet['limits']))

    def test_frozen_v3_commands_are_identical_for_the_authenticated_1024_baseline(self):
        # Isolate the historical startup boundary only. Native movement source,
        # source pins, save corridor, calls, byte checks and guards remain real.
        with patch.object(frozen.base,'build_selection_probe',return_value=self.baseline):
            expected=frozen.build_movement_probe(self.original,self.candidate,self.save,capture_dir=CAPTURE)
        self.assertEqual(self.packet['compiled_probe'],expected['compiled_probe'].replace(frozen.REVISION,probe.REVISION))
        for key in ('supplemental_commands','supplemental_sha256','initial_extra','initial_extra_sha256',
                    'movement_observer_vas','movement_native_call_returns','pump_observers',
                    'loaded_native_spans','stack_offsets_from_sentinel','expected_path_words','expected_final_ap'):
            self.assertEqual(self.packet[key],expected[key],key)

    def test_complete_army_and_partial_tile_loaded_checks_remain_exact(self):
        for resolution,case in self.cases.items():
            packet=case['packet'];baseline=case['baseline']
            with self.subTest(resolution=resolution):
                self.assertEqual(packet['initial_extra'],case['canonical'])
                self.assertEqual(packet['initial_extra'],baseline['initial_extra'])
                # The frozen movement protocol inserts its own loaded-byte
                # block before the first numbered PTILE breakpoint. Remove
                # only that additive block to compare all inherited text.
                inherited='\n'.join(line for line in packet['compiled_probe'].splitlines()
                    if not (line.endswith('{ .echo WMOV_REJECT loaded_bytes; q }')
                            or line=='.echo WMOV_BYTES_PASS' or line.startswith('.echo WMOV_CONTRACT ')))
                self.assertTrue(packet['initial_extra'].strip() in inherited,
                    'canonical inherited loaded checks/observers differ at '+resolution)
                self.assertEqual(packet['initial_extra_sha256'],probe.sha(case['canonical'].encode('ascii')))
                contracts=[line for line in case['canonical'].splitlines()
                    if line.startswith(('.echo ARMY_CONTRACT_PASS ','.echo COMPLETEHD_CONTRACT_PASS ','.echo PTILE_CONTRACT_PASS '))]
                self.assertEqual([line.split()[1] for line in contracts],
                    ['ARMY_CONTRACT_PASS','COMPLETEHD_CONTRACT_PASS','PTILE_CONTRACT_PASS'])
                for line in contracts:
                    self.assertEqual(packet['compiled_probe'].splitlines().count(line),1)
                    self.assertIn('resolution='+resolution+' ',line)
                    self.assertIn('candidate_sha256='+packet['candidate_sha256'],line)
                # Both inherited selection and new movement loaded-byte checks
                # occur before the first numbered breakpoint is installed.
                first=re.search(r'^bp[0-9]+ ',packet['compiled_probe'],re.M).start()
                for marker in ('WMOV_BASE_BYTES_PASS','WMOV_BYTES_PASS'):
                    self.assertLess(packet['compiled_probe'].index(marker),first)

    def test_three_quiet_checkpoints_bind_resolution_and_nonwrapping_surface_extent(self):
        for resolution,case in self.cases.items():
            width,height=map(int,resolution.split('x'));size=width*height;maximum=0x100000000-size
            for index,name in enumerate(('movement-before','movement-preview','movement-after')):
                with self.subTest(resolution=resolution,checkpoint=index):
                    text=case['packet']['supplemental_commands'][f'{CAPTURE}/movement-checkpoint-{index}.cdb']
                    guard=conditions(text)[0]
                    r,m=self.state(130 if index==2 else 110)
                    r['esp']=r['t3'];r['t13']=0
                    m.update({0x900000:width,0x900002:height,0x900004:maximum,
                              r['t1']+140008:10,r['t1']+140012:17})
                    if index==0:m[r['t1']+149349+316]=0
                    self.assertTrue(expression(guard,r,m))
                    for address,value in ((0x900000,width+2),(0x900002,height+2),(0x900004,maximum+1),
                                          (0x900004,0xFFFF),(0x9000B8,0),(r['t1']+140008,11)):
                        self.assertFalse(expression(guard,r,m|{address:value}),(index,address,value))
                    if index:
                        self.assertFalse(expression(guard,r|{'t13':1},m))
                    self.assertIn(f'{name}.raw poi(poi(005202e0)+4) L0n{size}',text)
                    self.assertIn(f'{name}.header.raw poi(005202e0) L0n188',text)
                    self.assertIn(f'{name}.unit.raw @$t1+0n149349 L0n725',text)

    def test_complete_manifest_mismatches_are_rejected_by_the_real_verifier(self):
        original_manifest=self.cases['1024x768']['manifest']
        mutations={
            'stage':lambda d:d.update(stage=d['predecessor']['stage']),
            'recipe':lambda d:d.update(recipe_revision='wrong'),
            'schema-bool':lambda d:d.update(schema=True),
            'schema-float':lambda d:d.update(schema=1.0),
            'candidate':lambda d:d.update(candidate_sha256='a'*64),
            'source':lambda d:d['source_hashes'].update({next(iter(d['source_hashes'])):'0'*64}),
        }
        for label,change in mutations.items():
            manifest=copy.deepcopy(original_manifest);change(manifest)
            with self.subTest(mutation=label),self.assertRaises(ValueError):
                self.build(candidate_manifest=manifest)
        for value in (None,[],True):
            with self.subTest(manifest=value),self.assertRaises(ValueError):
                self.build(candidate_manifest=value)
        for resolution in ('640x480','1600x900',None):
            with self.subTest(resolution=resolution),self.assertRaises(ValueError):
                probe.build_movement_probe(self.original,self.candidate,self.save,capture_dir=CAPTURE,
                    candidate_manifest=original_manifest,resolution=resolution)
        with self.assertRaises(ValueError):
            self.build(candidate=self.cases['1920x1080']['candidate'])
        with self.assertRaises(ValueError):
            self.build(candidate_manifest=self.cases['1920x1080']['manifest'])
        with self.assertRaises(ValueError):
            self.build(original=self.original[:-1]+bytes([self.original[-1]^1]))

    def test_both_native_occupancy_commits_and_pathfinder_pump_completion_are_required(self):
        for step in (1,2):
            r,m=self.state(125,step=step);guard=conditions(command(self.packet,125)[1])[0]
            self.assertTrue(expression(guard,r,m))
            gd=r['t1'];unit=gd+149349
            for address,value in ((unit,16+step-1),(unit+2,20),
                (gd+556374+200*(16+step)+38,65535),(gd+556374+200*(15+step)+38,3)):
                self.assertFalse(expression(guard,r,m|{address:value}),(step,address))
            for slot,initial in enumerate((26,22,16,16,16,16,16,16)):
                self.assertFalse(expression(guard,r,m|{unit+14+31*slot:initial-5*step+1}),(step,slot))
        r,m=self.state(109);guards=conditions(command(self.packet,109)[1])
        # The v3 positive includes a completed real pathfinder pump before
        # rejecting absent/pending pump state. This is never a v2 baseline.
        for guard in guards:self.assertTrue(expression(guard,r,m))
        self.assertEqual((r['t12'],r['t13']),(1,0))
        for mutation in ({'t12':0},{'t13':1}):
            self.assertFalse(expression(guards[0],r|mutation,m))

    def test_source_drift_baseline_transport_and_oversized_commands_fail_closed(self):
        sources=probe.verify_sources()
        with patch.object(probe,'verify_sources',side_effect=[sources,sources|{'fixture-change':'0'*64}]):
            with self.assertRaisesRegex(ValueError,'sources changed'):
                self.build()
        compiled=self.baseline['compiled_probe']
        for changed in (re.sub(r'^bp80 .*\n','',compiled,flags=re.M),
                        compiled+re.search(r'^bp80 .*$',compiled,re.M)[0]+'\n',
                        compiled[:-2],compiled.replace('SHSEL_HOST_READY','SHSEL_HOST_READY SHSEL_HOST_READY')):
            with patch.object(probe.base,'build_selection_probe',return_value=self.baseline|{'compiled_probe':changed}):
                with self.assertRaises(ValueError):
                    self.build()
        with patch.object(probe.base,'_printf',return_value='x'*4096):
            with self.assertRaisesRegex(ValueError,'4095-byte line limit|line exceeds4096'):
                self.build()

    def test_source_candidate_save_and_no_side_effects(self):
        p=self.packet
        self.assertEqual(p['candidate_sha256'],probe.sha(self.candidate));self.assertEqual(p['save_sha256'],probe.sha(self.save))
        self.assertEqual(p['base_compiled_probe_sha256'],self.baseline['probe_sha256'])
        self.assertEqual((ORIGINAL.read_bytes(),SAVE.read_bytes()),(self.original,self.save))
        self.assertEqual(local_path(CAPTURE).exists(),self.existed)
        for key in ('native_predicate_forced','selected_value_forced','flag_value_forced','movement_state_forced',
                    'runtime_executed','manual_input_proof','promotion_ready'):self.assertIs(p[key],False)
        for key in ('candidate','save'):
            args=dict(original=self.original,candidate=self.candidate,save=self.save)
            args[key]=args[key][:-1]+bytes([args[key][-1]^1])
            with self.assertRaises(ValueError):self.build(**args)
        with patch.object(probe,'PARENT_SOURCE_SHA256','0'*64),self.assertRaises(ValueError):
            self.build()

    def test_native_metadata_and_unique_corridor_path_derivation(self):
        # Independent literal save offsets and original cost bytes; no producer
        # geometry/path helper computes the expected fixture values.
        data=self.save[16:]
        expected=[(17,13),(18,15)]
        for x,terrain in expected:
            self.assertEqual(struct.unpack_from('<H',data,556374+200*x+2*19)[0],65535)
            self.assertEqual(struct.unpack_from('<H',data,1400*x+14*19)[0],terrain)
            self.assertEqual(struct.unpack_from('<H',data,1400*x+14*19+4)[0],65535)
            self.assertTrue(data[140081+x*13+2]&8);self.assertEqual(data[576374+100*x+19],0)
        for unit_type in (1,16):
            table=probe.base._read(self.original,0x512568+88*unit_type+29,9)
            self.assertEqual(table[3],5)
        # The native first relaxation rectangle X16..18/Y19 has exactly one
        # interior tile. Cardinal destination cost5 yields cumulative5,10.
        encoded=[struct.unpack('<I',struct.pack('<BBH',x,19,cost))[0] for x,cost in ((18,10),(17,5))]
        self.assertEqual(self.packet['expected_path_words'],encoded)
        self.assertEqual(self.packet['expected_final_ap'],[16,12,6,6,6,6,6,6])
        self.assertEqual(self.packet['controlled_mouse'],[576,176])
        self.assertEqual(self.packet['destination_xy'],[18,19])

    def test_complete_loaded_native_spans_calls_and_nonoverlapping_observers(self):
        checked={int(va,16):int(value,16) for va,value in re.findall(r'\(by\(([0-9a-f]{8})\) != 0x([0-9a-f]{2})\)',self.packet['compiled_probe'])}
        for va,size in probe.NATIVE_SPANS:
            self.assertEqual(bytes(checked[va+i] for i in range(size)),probe.base._read(self.candidate,va,size))
        for va,target in probe.NATIVE_CALLS.items():
            self.assertEqual(self.packet['movement_native_call_returns'][f'{va:08x}'],probe.base._call_return(self.candidate,va,target))
        prior={int(va,16) for va in re.findall(r'^bp[0-9]+ ([0-9a-f]{8}) ',self.baseline['compiled_probe'],re.M)}
        self.assertFalse(prior.intersection(self.packet['movement_observer_vas'].values()))
        self.assertEqual(set(self.packet['movement_observer_vas']),{str(n) for n in range(100,139)})
        self.assertEqual(probe.base._read(self.candidate,0x409AB3,2),b'\xf3\xa5')
        self.assertEqual(probe.base._read(self.candidate,0x410AF3,4),b'\x66\x89\x5f\x02')

    def state(self,n,click=1,step=1):
        phases={107:27,108:28,109:29,110:30,111:31,112:32,113:33,114:34,115:35,116:36,117:37,
                118:47,119:48,120:49,121:50,122:51,123:52,124:53,125:54,126:51,127:55,128:56,129:57,130:58}
        depths={107:120,108:124,109:116,110:116,111:116,112:120,113:132,114:132,115:116,116:116,117:4,
                118:116,119:116,120:116,121:120,122:328,123:328,124:328,125:328,126:328,127:120,128:116,129:116,130:4}
        phase=phases.get(n,(20 if click==1 else 40)+n-100)
        depth=depths.get(n,8 if n==100 else 116)
        s=0x800000;gd=0x600000;u=gd+149349
        if n>=118:click=2
        r=dict(tid=7,t2=7,t1=gd,t3=s,t10=click,t0=phase,esp=s-depth,eip=self.packet['movement_observer_vas'][str(n)],
               eax=0,ebx=19,ecx=18,edx=16,esi=0,edi=0,ebp=18,t5=0,t6=0,t7=0,t11=0,t12=1,t13=0)
        m={0x5202E4:gd,0x5199D8:0x40AD40,0x526990:0,0x5202EC:0,0x511B58:3,0x514194:3,0x526994:1,0x526FA0:u,
           u:16,u+2:19,u+4:0,u+316:2,u+320:0xA1312,u+324:0x51311,
           0x544CFC:576<<2,0x544D00:176<<2,0x54512C:2,0x544D04:1,0x5451C0:128,
           0x5202E0:0x900000,0x900000:1024,0x900002:768,0x900004:0xA00000,0x9000B8:0x50EE24,
           gd+559612:3,gd+559812:65535,gd+560012:65535,0x523F70:0,0x523F74:0,0x512360:0xFFFFFFFFFFFFFFFF}
        m.update({0x526F78+4*i:0 for i in range(10)})
        m.update({u+14+31*i:ap for i,ap in enumerate((26,22,16,16,16,16,16,16))})
        if n==100:m[r['esp']+4]=0x406FA1
        if n in (102,105,119):r['eax']=1
        if n==103:r['eax']=0xFFFFFFFFFFFFFFFF
        if n==106:m[r['esp']+0x54]=19
        if n in (107,108):r['eax']=3;m[r['esp']]=19 if n==107 else 0x409A71;m[r['esp']+4]=19
        if n==109:
            r['eax']=0xA00000;m.update({0xA00000:2,0xA00004:0xA1312,0xA00008:0x51311})
        if n==112:r['eax']=0x544CD8;r['edx']=0;m[r['esp']]=0x409CAB
        if 112<=n<=117 or n>=121:m[0x544D04]=m[0x5451C0]=0
        if n in (116,117) or n>=126:r.update(t5=3,t6=3,t7=1)
        if n in (117,130):m[r['esp']]=0x406FA1
        if n in (118,120,121):r['eax']=3
        if n in (120,121):r['edx']=1
        if n==121:m[r['esp']]=0x409C13
        if 122<=n<=125:
            r['t11']=step-1 if n==122 else step
            m[u]=16+step-(0 if n==125 else 1)
            cost=5*(step-1 if n==122 else step)
            m.update({u+14+31*i:ap-cost for i,ap in enumerate((26,22,16,16,16,16,16,16))})
            if n==122:r['eax']=u;r['edx']=5
            if n in (124,125):m[u+316]=2-step
            if n==125:
                r['edi']=u;m[gd+556374+200*(16+step)+38]=3;m[gd+556374+200*(15+step)+38]=65535
        if n>=126:
            r['t11']=2;m[u]=18;m[u+316]=0
            m.update({u+14+31*i:ap-10 for i,ap in enumerate((26,22,16,16,16,16,16,16))})
            m.update({gd+559612:65535,gd+559812:65535,gd+560012:3})
        if n==127:m[r['esp']]=0x409C13
        for num,reg in enumerate(('ebx','ecx','edx','esi','edi','ebp'),14):r[f't{num}']=r[reg]
        return r,m

    def test_every_phase_binds_actual_thread_stack_owner_and_all_flags(self):
        for n in range(100,131):
            for click in ((1,2) if n<=106 else (1,)):
                for step in ((1,2) if 122<=n<=125 else (1,)):
                    r,m=self.state(n,click,step);guards=conditions(command(self.packet,n)[1])
                    for guard in guards:self.assertTrue(expression(guard,r,m),(n,click,step,guard))
                    for field,value in (('tid',8),('t0',99),('esp',r['esp']+4)):
                        self.assertFalse(expression(guards[0],r|{field:value},m),(n,field))
                    for address,value in ((0x5199D8,0),(0x526990,1),(0x5202EC,1),(0x511B58,2),(0x514194,1),(0x526994,0)):
                        self.assertFalse(expression(guards[0],r,m|{address:value}),(n,address))
                    for slot in range(10):
                        self.assertFalse(expression(guards[0],r,m|{0x526F78+4*slot:1}),(n,slot))

    def test_path_confirmation_fails_closed_and_ap_xy_are_observed(self):
        for n in (110,111,118,120):
            r,m=self.state(n);u=r['t1']+149349;guard=conditions(command(self.packet,n)[1])[0]
            for offset,value in ((316,1),(316,3),(320,0xA1311),(324,0x61311),(0,17),(14,25)):
                self.assertFalse(expression(guard,r,m|{u+offset:value}),(n,offset,value))
        for n,field,value in ((103,'eax',0),(104,'eax',1),(105,'eax',0),(119,'eax',0),(122,'edx',6)):
            r,m=self.state(n);self.assertFalse(expression(conditions(command(self.packet,n)[1])[0],r|{field:value},m),(n,field))
        r,m=self.state(109);guard=conditions(command(self.packet,109)[1])
        for ptr in (0,0xFFFF,0xFFFFFFFF):self.assertFalse(expression(guard[0],r|{'eax':ptr},m))
        for n in (126,127,128,129,130):
            r,m=self.state(n);u=r['t1']+149349;guard=conditions(command(self.packet,n)[1])[0]
            for address,value in ((u,17),(u+316,1),(u+14,17),(0x523F70,1),(0x512360,3),(r['t1']+560012,65535)):
                self.assertFalse(expression(guard,r,m|{address:value}),(n,address))
        for n in (131,132):self.assertIn('WMOV_REJECT unexpected_route; q',command(self.packet,n)[1])

    def test_release_draw_pair_and_register_preservation_contracts(self):
        for n in (111,120):
            cmd=command(self.packet,n)[1]
            self.assertLess(cmd.index('-release-before'),cmd.index('eb 005451c0 00'))
            self.assertLess(cmd.index('ed 00544d04 0'),cmd.index('-release-after'))
        for n in (113,114,115):
            r,m=self.state(n);self.assertFalse(expression(conditions(command(self.packet,n)[1])[0],r|{'eax':1},m))
        for n in (117,130):
            r,m=self.state(n);guard=conditions(command(self.packet,n)[1])[0]
            for reg in ('ebx','ecx','edx','esi','edi','ebp'):
                self.assertFalse(expression(guard,r|{reg:r[reg]^1},m),(n,reg))
        for n,key in ((91,'native_draw'),(92,'composition_draw')):
            r,m=self.state(126);r.update(t8=r['t3']-400,t9=self.packet['baseline_native_call_returns'][key],t5=2,t6=1,eax=1)
            r['esp']=r['t8']+4;guard=conditions(command(self.packet,n)[1])[-1]
            self.assertTrue(expression(guard,r,m))
            for field,value in (('eax',0),('t6',2),('esp',r['esp']+4),('t9',0)):
                self.assertFalse(expression(guard,r|{field:value},m),(n,field))

    def test_native_pump_pairs_preserve_observed_input_without_result_override(self):
        # Independent source-derived identities and stack depths. Each pump
        # occurs before the next native observation, with no forced result.
        sites=((133,134,0x414B3F,0x414B44,'pathfinder',29,388,1),
               (135,136,0x410DAE,0x410DB3,'animation',54,328,2),
               (137,138,0x410C91,0x410C96,'delay',51,328,3))
        self.assertEqual(self.packet['max_pump_calls_per_click'],1024)
        for call_n,return_n,call_va,return_va,kind,phase,depth,identity in sites:
            metadata=self.packet['pump_observers'][identity-1]
            self.assertEqual(metadata,dict(kind=kind,call=call_va,returned=return_va,
                phase=phase,stack_depth=depth,pending_identity=identity))
            self.assertEqual(probe.base._call_return(self.original,call_va,0x4605D0),return_va)
            for step in ((0,) if identity==1 else (1,2)):
                r,m=self.state(108 if identity==1 else 124,step=step or 1)
                r.update(t0=phase,esp=r['t3']-depth,eax=0x544CD8,edx=0,t11=step,t12=0,t13=0,t4=0)
                u=r['t1']+149349
                m[0x545138]=0x50F1E4;m[0x50F1F8]=0x460A50
                if identity==1:
                    m[u+316]=0
                    # Pathfinder temporarily clears occupancy; this is not a
                    # unit movement commit and must not falsely reject a poll.
                    m[r['t1']+559612]=65535
                else:
                    m[u]=16+step-(1 if identity==2 else 0)
                call=command(self.packet,call_n)[1];cg=conditions(call)
                for guard in cg:self.assertTrue(expression(guard,r,m),(call_n,step,guard))
                for field,value in (('tid',8),('esp',r['esp']+4),('t0',99),('eax',0),('edx',1),('t12',1024),('t13',identity)):
                    self.assertFalse(expression(cg[0],r|{field:value},m),(call_n,field))
                for value in (0,0x3FFFFF,0x7FFFFFFF):
                    self.assertFalse(expression(cg[0],r,m|{0x545138:value}),value)
                self.assertFalse(expression(cg[1],r,m|{0x50F1F8:0x4605D0}))
                returned=command(self.packet,return_n)[1];rg=conditions(returned)[0]
                # The full native method may return any EAX. Changed raw
                # coordinates and both accumulator bytes remain observations.
                rr=r|dict(t12=1,t13=identity,t4=0x50F1E4,eax=0xFFFFFFFF)
                for buttons in range(4):
                    mm=m|{0x544D04:buttons,0x5451C0:0x90,0x5451C8:0xED,
                          0x544CFC:0x2600,0x544D00:0x2C00,0x54512C:6}
                    self.assertTrue(expression(rg,rr,mm),(return_n,step,buttons))
                for field,value in (('tid',8),('esp',r['esp']+4),('t0',99),('t12',0),('t12',1025),('t13',0),('t13',identity+1)):
                    self.assertFalse(expression(rg,rr|{field:value},m),(return_n,field))
                for address,value in ((0x545138,0x50F204),(0x544D04,4),(0x544D04,0xFFFFFFFF)):
                    self.assertFalse(expression(rg,rr,m|{address:value}),(return_n,address))
                self.assertIn('WMOV_PUMP kind='+kind+'-call count=%d phase=%d',call)
                self.assertIn('WMOV_PUMP kind='+kind+'-return count=%d phase=%d',returned)
                self.assertIn('r @$t13=0; .printf',returned)
                self.assertNotRegex(call+'; '+returned,r'\b(?:eb|ed|ew|eq)\s|\br\s+(?:eax|ebx|ecx|edx|esi|edi|esp|eip)=')
        # This report does not claim all native input polling was observed.
        self.assertTrue(any('do not establish complete input-backend tracing' in x for x in self.packet['limits']))

    def test_preview_release_after_verified_path_allows_native_button_refresh(self):
        r,m=self.state(111);guard=conditions(command(self.packet,111)[1])[0]
        for buttons in range(4):
            for accumulator in (0,0x80,0x90,0xFF):
                self.assertTrue(expression(guard,r,m|{0x544D04:buttons,0x5451C0:accumulator}),
                    (buttons,accumulator))
        self.assertFalse(expression(guard,r,m|{0x544D04:4}))
        self.assertFalse(expression(guard,r|{'t13':1},m))
        # Confirmation still requires its own held diagnostic input before
        # the separately logged release; this is not a blanket gate removal.
        r,m=self.state(120);guard=conditions(command(self.packet,120)[1])[0]
        for address,value in ((0x544D04,3),(0x5451C0,0x90)):
            self.assertFalse(expression(guard,r,m|{address:value}))

    def test_native_fixed_point_shift6_and_signed_dword_bound_before_writes(self):
        for shift in (0,2,3,6,16,21):
            raw_x,raw_y=576<<shift,176<<shift
            self.assertLess(raw_x,1<<31);self.assertEqual((raw_x>>shift,raw_y>>shift),(576,176))
            for n in range(100,107):
                r,m=self.state(n);m.update({0x54512C:shift,0x544CFC:raw_x,0x544D00:raw_y})
                self.assertTrue(expression(conditions(command(self.packet,n)[1])[0],r,m),(n,shift))
                for address in (0x544CFC,0x544D00):
                    self.assertFalse(expression(conditions(command(self.packet,n)[1])[0],r,m|{address:m[address]+1}),(n,shift,address))
        for shift in (22,31,32,255):
            r,m=self.state(100);m.update({0x54512C:shift,0x544CFC:576<<shift,0x544D00:176<<shift})
            self.assertFalse(expression(conditions(command(self.packet,100)[1])[0],r,m),shift)
        for index in (0,1):
            text=self.packet['supplemental_commands'][f'{CAPTURE}/movement-checkpoint-{index}.cdb']
            self.assertIn('(by(0054512c) <= 0n21)',conditions(text)[0])
            self.assertLess(text.index('(by(0054512c) <= 0n21)'),text.index('ed 00544cfc'))
            self.assertLess(text.index('ed 00544d04 1'),text.index('WMOV_MOUSE'))
            self.assertLess(text.index('WMOV_MOUSE'),text.index('kind=begin'))
        for n in range(100,131):
            text=command(self.packet,n)[1]
            self.assertIn('WMOV_REJECT_CONTEXT phase=%d tid=%x eip=%p esp=%p shift=%x raw=(%x,%x)',text)
            self.assertLess(text.index('WMOV_REJECT_CONTEXT'),text.index('.echo WMOV_REJECT native_contract; q'))
        self.assertEqual(self.packet['mouse_shift_max'],21)

    def test_transport_namespace_dump_lengths_and_write_allowlist(self):
        p=self.packet;all_text=p['compiled_probe']+'\n'+'\n'.join(p['supplemental_commands'].values())
        self.assertEqual(all_text.count('WMOV_HOST_READY'),1);self.assertNotIn('WMOV_BASE_HOST_READY',all_text)
        self.assertNotIn('SHSEL_',all_text);self.assertLess(max(map(len,all_text.splitlines())),4096)
        for n in range(81,90):self.assertEqual(command(p,n)[1],command(self.baseline,n)[1].replace('SHSEL_','WMOV_BASE_'))
        self.assertEqual(p['initial_extra'],self.baseline['initial_extra'])
        for i,name in enumerate(('movement-before','movement-preview','movement-after')):
            path=f'{CAPTURE}/movement-checkpoint-{i}.cdb';text=p['supplemental_commands'][path]
            self.assertEqual(p['supplemental_sha256'][path],probe.sha(text.encode('ascii')))
            self.assertNotIn(r'\"',text);self.assertNotIn(r'\\n',text)
            self.assertIn('$$>a<\\"'+path+'\\";',command(p,80)[1])
            self.assertIn(f'{name}.header.raw poi(005202e0) L0n188',text)
            self.assertIn(f'{name}.raw poi(poi(005202e0)+4) L0n786432',text)
            self.assertIn(f'{name}.unit.raw @$t1+0n149349 L0n725',text)
        # Restrict the NEW route, after removing the exact inherited source.
        new_commands='\n'.join(command(p,n)[1] for n in range(100,139))+'\n'+'\n'.join(p['supplemental_commands'].values())
        writes=re.findall(r'\b(?:eb|ed|ew|eq)\s+([^ ;]+)',new_commands)
        self.assertEqual(set(writes),{'00544cfc','00544d00','005451c0','00544d04','@esp'})
        regwrites=re.findall(r'\br\s+([^ =;]+)=',new_commands)
        self.assertTrue(all(name.startswith('@$t') or name in ('esp','eip') for name in regwrites),regwrites)
        self.assertNotRegex(new_commands,r'\b(?:r|ed)\s+(?:eax|00511b58|00514194|00526f78)\b')
        for line in all_text.splitlines():
            if '.printf ' in line:
                # Transport and supplemental forms are intentionally distinct.
                normalized=line.replace(r'\"','"').replace(r'\\n',r'\n')
                for fmt,args in re.findall(r'\.printf "([^"\n]+)"([^;}]*)',normalized):
                    count=len(re.findall(r'%(?:I64)?(?:0?[0-9]+)?[dxXpsu]',fmt))
                    self.assertEqual(count,len([a for a in args.split(',') if a.strip()]),fmt)


if __name__=='__main__':unittest.main()
