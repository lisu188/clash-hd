"""Pure marker adversaries and read-only whole-image binding; no runtime."""
from __future__ import annotations

import contextlib
import copy
import io
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest.mock import patch

import framed_army_portrait_trace as trace
import test_framed_army_selection_trace as baseline_fixture

TID=0xABC;SP=0x100100;GD=0x600000;SURFACE=0x900000;BASE=0xA00000


def packet_fixture():
    base=baseline_fixture.packet_fixture();directory='C:/ClashCaptures/offline-portrait-trace'
    commands={f'{directory}/portrait-checkpoint-{n}.cdb':f'.echo synthetic-not-executable-{n}\n' for n in range(3)}
    return dict(schema='clash95_framed_army_portrait_probe_v1',revision=trace.producer.REVISION,
        stage=base['stage'],resolution='1024x768',width=1024,height=768,original_sha256=base['original_sha256'],
        candidate_sha256=base['candidate_sha256'],save_sha256=base['save_sha256'],capture_dir=directory,minimap_viewport=True,
        unit=3,slot=0,unit_xy=[16,19],unit_squad_types=[16,16,1,1,1,1,1,1],controlled_scroll=[10,17],controlled_mouse=[54,719],
        flag_vectors=[[0]*10,[1]+[0]*9,[0]*10],compiled_probe='synthetic nonexecuted probe\n',
        probe_sha256=trace.sha(b'synthetic nonexecuted probe\n'),initial_extra=base['initial_extra'],initial_extra_sha256=base['initial_extra_sha256'],
        supplemental_commands=commands,supplemental_sha256={path:trace.sha(text.encode()) for path,text in commands.items()},
        baseline_observer_vas={str(n):0x400000+n for n in range(80,93)}|{'80':0x406FA1,'90':0x597000,'91':0x597800,'92':0x597A00},
        baseline_native_call_returns=base['native_call_returns'],portrait_observer_vas={str(n):va for n,va in trace.SITES.items()},
        controlled_input=True,controlled_release=True,native_predicate_forced=False,selected_value_forced=False,flag_value_forced=False,
        runtime_executed=False,manual_input_proof=False,promotion_ready=False)


def log_fixture(packet=None,*,warmup=0,shift=6):
    packet=packet or packet_fixture();base=copy.deepcopy(packet)
    base.update(revision='controlled_own_army_native_selection_v3',native_call_returns=packet['baseline_native_call_returns'])
    text=baseline_fixture.log_fixture(base,warmup=warmup).replace('SHSEL_','PTGL_BASE_')
    text=text.replace('\nPTILE_EVENT seq=1 ','\nPTGL_BYTES_PASS\nPTILE_EVENT seq=1 ',1).replace('PTGL_BASE_HOST_READY\n','')
    text=text.replace('esp=000ff000',f'esp={SP-192:08x}').replace('esp=000ff004',f'esp={SP-188:08x}')
    text=text.replace('esp=000fe000',f'esp={SP-316:08x}').replace('esp=000fe004',f'esp={SP-312:08x}')
    lines=text.splitlines()
    def surface(n):lines.append(f'PTGL_SURFACE checkpoint={n} tid={TID:x} eip=00406fa1 esp={SP:08x} surface={SURFACE:08x} base={BASE:08x} width=1024 height=768 vtable=0050ee24')
    surface(0)
    for toggle in (1,2):
        flag=toggle-1;counts=[0,0,0];buttons=1;accumulator=0x80
        def obs(kind,phase,eip,depth,*,eax=0,ecx=0,edx=0,esi=0,edi=0,caller=0):
            flags=','.join(f'{v:x}' for v in [flag]+[0]*9)
            lines.append(f'PTGL_OBS kind={kind} toggle={toggle} phase={phase} tid={TID:x} eip={eip:08x} esp={SP-depth:08x} caller={caller:08x} '
                f'eax={eax:x} ecx={ecx:x} edx={edx:x} esi={esi:x} edi={edi:x} selected=3 prior=3 lower=1 unit={GD+149349:08x} '
                f'mouse_raw=({54<<shift:x},{719<<shift:x}) shift={shift:x} buttons={buttons:x} accumulator={accumulator:x} flags=({flags}) draws=({counts[0]},{counts[1]},{counts[2]})')
        obs('begin',20,0x406FA1,0)
        obs('post-push',21,0x423861,8)
        obs('portrait-hit',22,0x4238CA,68)
        obs('right-return',23,0x4238E3,68)
        obs('left-return',24,0x423937,68,eax=1)
        obs('xor-before',25,0x423952,68,eax=16)
        flag=2-toggle
        obs('xor-after',26,0x42395A,68,eax=16)
        def draw(route,phase,depth):
            caller=packet['baseline_native_call_returns'][route+'_draw' if route=='native' else 'composition_draw']
            counts[0]+=1
            obs('draw-entry',phase,packet['baseline_observer_vas']['90'],depth,caller=caller,ecx=11,edx=18,esi=4,edi=8)
            counts[1]+=1;counts[2]+=int(route=='composition')
            obs('draw-'+route+'-return',phase,caller,depth-4,eax=1,ecx=11,edx=18,esi=4,edi=8)
        draw('native',26,188)
        obs('native-draw-return',27,0x423964,68)
        obs('map-entry',28,0x418700,72,eax=1,caller=0x423970)
        draw('composition',28,312)
        obs('map-return',29,0x423970,68)
        obs('release-before',29,0x423970,68)
        buttons=accumulator=0
        obs('release-after',29,0x423970,68)
        obs('release-entry',30,0x4609D0,72,eax=0x544CD8,caller=0x42397A)
        obs('release-left-return',31,0x4609E0,84)
        obs('release-right-return',32,0x4609FC,84)
        obs('release-return',33,0x42397A,68)
        obs('secondary-map-return',34,0x423989,68,edi=1)
        obs('portrait-return',35,0x423A99,4,eax=1,caller=0x406FA1)
        surface(toggle)
        if toggle==2:obs('ready',35,0x406FA1,0,eax=1)
    lines.append('PTGL_HOST_READY');return '\n'.join(lines)+'\n'


def headers_fixture(packet):
    raw=bytearray(188);struct.pack_into('<HHI',raw,0,1024,768,BASE);struct.pack_into('<I',raw,184,0x50EE24)
    return {item['header_path']:bytes(raw) for item in trace.snapshot_paths(packet)}


class SequenceTests(unittest.TestCase):
    def bad(self,log,packet=None):
        report=trace.evaluate_trace(log,packet or packet_fixture());self.assertFalse(report['passed'],report)
        self.assertTrue(report['failures']);self.assertFalse(report['ready_for_host_capture']);return report

    def test_true_native_two_toggle_contract_and_fallback_disclosures(self):
        for warmup in (0,1):
            for shift in (0,1,6,10):
                report=trace.evaluate_trace(log_fixture(warmup=warmup,shift=shift),packet_fixture())
                self.assertTrue(report['passed'],report['failures'])
                sequence=report['portrait_sequence']
                self.assertEqual(sequence['baseline_native_fallbacks'],int(warmup==0))
                self.assertEqual([x['final_flags'] for x in sequence['toggles']],[[1]+[0]*9,[0]*10])
                self.assertEqual([x['checkpoint'] for x in report['snapshots']],[0,1,2])
                self.assertEqual([x['composition_returns'] for x in sequence['toggles']],[1,1])
                for key in ('source_authenticated','whole_candidate_bound','all_supplemental_commands_bound','snapshot_headers_verified',
                            'ready_for_host_capture','runtime_accepted','pixels_verified','cleanup_verified','manual_input_proof','promotion_ready'):
                    self.assertFalse(report[key],key)

    def test_every_marker_missing_duplicated_or_reordered_is_rejected(self):
        lines=log_fixture().splitlines()
        for n,line in enumerate(lines):
            if not line.startswith(('PTGL_','ARMY_')):continue
            with self.subTest(missing=line):self.bad('\n'.join(lines[:n]+lines[n+1:]))
            with self.subTest(duplicate=line):self.bad('\n'.join(lines[:n]+[line]+lines[n:]))
        for a,b in (('xor-before','xor-after'),('release-before','release-after'),('release-entry','release-left-return'),('portrait-return','ready')):
            changed=lines.copy();i=next(n for n,t in enumerate(lines) if 'kind='+a+' ' in t);j=next(n for n,t in enumerate(lines) if 'kind='+b+' ' in t)
            changed[i],changed[j]=changed[j],changed[i];self.bad('\n'.join(changed))

    def test_identity_complete_flags_mouse_buttons_stack_and_counters_checked(self):
        lines=log_fixture().splitlines()
        for n,line in enumerate(lines):
            if not line.startswith('PTGL_OBS'):continue
            for key,value in (('toggle','3'),('phase','99'),('tid','def'),('eip','00400000'),('esp','00100001'),
                              ('selected','0'),('prior','0'),('lower','0'),('unit','00600000'),('shift','1'),('buttons','2'),('accumulator','ff')):
                changed=lines.copy();changed[n]=re.sub(r'\b'+key+r'=[^ ]+',key+'='+value,line)
                with self.subTest(line=n,key=key):self.bad('\n'.join(changed))
            for i in range(10):
                changed=lines.copy();flags=re.search(r'flags=\(([^)]+)\)',line).group(1).split(',');flags[i]='2'
                changed[n]=re.sub(r'flags=\([^)]+\)','flags=('+','.join(flags)+')',line);self.bad('\n'.join(changed))
            changed=lines.copy();changed[n]=line.replace('draws=(', 'draws=(99,');self.bad('\n'.join(changed))
        self.bad(log_fixture().replace('mouse_raw=(d80,b3c0)','mouse_raw=(d40,b3c0)'))

    def test_real_predicates_xor_draw_release_secondary_and_gpr_preservation(self):
        lines=log_fixture().splitlines()
        for kind,key,value in (('left-return','eax','0'),('right-return','eax','1'),('xor-before','eax','11'),
                               ('release-left-return','eax','1'),('release-right-return','eax','1'),('release-return','eax','1'),
                               ('secondary-map-return','eax','1'),('secondary-map-return','edi','0'),('portrait-return','eax','0'),
                               ('map-entry','edx','1'),('release-entry','eax','0'),('portrait-hit','esi','1')):
            n=next(n for n,t in enumerate(lines) if 'kind='+kind+' ' in t);changed=lines.copy()
            changed[n]=re.sub(r'\b'+key+r'=[^ ]+',key+'='+value,lines[n]);self.bad('\n'.join(changed))
        for kind in ('draw-native-return','draw-composition-return'):
            n=next(n for n,t in enumerate(lines) if 'kind='+kind+' ' in t)
            for key,value in (('eax','0'),('ecx','c'),('edx','13'),('esi','5'),('edi','9'),('esp','00100000')):
                changed=lines.copy();changed[n]=re.sub(r'\b'+key+r'=[^ ]+',key+'='+value,lines[n]);self.bad('\n'.join(changed))
        for old,new in (('caller=00423970','caller=0042397a'),('caller=0042397a','caller=00423970'),('caller=00406fa1','caller=00406fa0')):
            self.bad(log_fixture().replace(old,new))
        for kind in ('xor-after','release-before','release-after','portrait-return','ready'):
            n=next(n for n,t in enumerate(lines) if 'kind='+kind+' ' in t)
            for key in ('ecx','edx','esi','edi'):
                changed=lines.copy();changed[n]=re.sub(r'\b'+key+r'=[^ ]+',key+'=1234',lines[n]);self.bad('\n'.join(changed))
        n=next(n for n,t in enumerate(lines) if 'kind=post-push ' in t);changed=lines.copy()
        changed[n]=changed[n].replace('caller=00000000','caller=12345678');self.bad('\n'.join(changed))

    def test_snapshot_baseline_and_initial_failures_never_reclassified(self):
        log=log_fixture()
        for old,new in (('checkpoint=1','checkpoint=0'),('surface=00900000','surface=0051d4c0'),('width=1024','width=800'),
                        ('base=00a00000 width','base=fffffff0 width'),('vtable=0050ee24','vtable=0050ee74'),
                        ('PTGL_BASE_READY','PTGL_BASE_HOST_READY'),('PTGL_OBS kind=ready','PTGL_OBS kind=unknown'),
                        ('PTILE_EVENT seq=4','PTILE_EVENT seq=3'),('PTILE_STATUS hook=full_present status=1','PTILE_STATUS hook=full_present status=0'),
                        ('selected=1 prior=1','selected=0 prior=1')):
            self.assertIn(old,log);self.bad(log.replace(old,new))
        for tail in ('PTGL_REJECT native_contract','PTGL_OBS kind=forbidden-movement','PTGL_BASE_SELECTION_FAIL',
                     '0:000> PTGL_HOST_READY','ptgl_host_ready','PTGL_HOST_READY extra=1','SHSEL_HOST_READY',
                     'AV_SURFDUMP code=c0000005','Syntax error','timeout reached','SURFDUMP_APP_REQUEST_QUIT','PTILE_EVENT seq=999'):
            self.bad(log+tail+'\n')
        failed=log.split('PTGL_BASE_BEGIN')[0]+'PTGL_BASE_REJECT native_contract\n'
        report=self.bad(failed);self.assertTrue(report['initial_map_trace']['passed']);self.assertIsNone(report['surface'])
        projected,extra,binding=trace.selection._project(log,packet_fixture()['initial_extra'],packet_fixture())
        differences=[n for n,(a,b) in enumerate(zip(log.splitlines(),projected.splitlines())) if a!=b]
        self.assertEqual(len(differences),1);self.assertIn('a'*64,projected.splitlines()[differences[0]])
        self.assertNotIn('SHSEL_HOST_READY',projected);self.assertEqual(binding['log']['original_sha256'],trace.sha(log.encode()))

    def test_packet_malformed_or_stale_contracts_fail_closed(self):
        packet=packet_fixture()
        for key,value in (('revision','stale'),('stage','stale'),('resolution','800x600'),('slot',1),('flag_vectors',[]),
                          ('flag_value_forced',True),('controlled_release',False),('minimap_viewport',None),('candidate_sha256','x'*64),
                          ('initial_extra','changed'),('compiled_probe','changed'),('supplemental_commands',{}),('supplemental_sha256',{}),
                          ('baseline_observer_vas',{}),('portrait_observer_vas',{})):
            changed=copy.deepcopy(packet);changed[key]=value;self.bad(log_fixture(),changed)
        self.assertFalse(trace.evaluate_trace('',None)['passed'])

    def test_canonical_startup_order_and_literal_baseline_rows_are_strict(self):
        log=log_fixture();lines=log.splitlines()
        marker=lines.index('PTGL_BYTES_PASS')
        for position in (0,1,len(lines)-1):
            changed=lines.copy();changed.pop(marker);changed.insert(position,'PTGL_BYTES_PASS');self.bad('\n'.join(changed))
        names=('PTGL_BASE_BYTES_PASS','ARMY_CONTRACT_PASS','ARMY_SCOPE','PTILE_CONTRACT_PASS','PTILE_SCOPE','PTGL_BYTES_PASS')
        indices=[next(i for i,t in enumerate(lines) if t==name or t.startswith(name+' ')) for name in names]
        self.assertEqual(indices,sorted(indices))
        for i,j in zip(indices,indices[1:]):
            changed=lines.copy();changed[i],changed[j]=changed[j],changed[i];self.bad('\n'.join(changed))
        for old,new in (('screen=(448,176)','screen=(447,176)'),('world=(16,19)','world=(16,18)'),
                        ('predicate_forced=0','predicate_forced=1'),('selected_before=-1','selected_before=3'),
                        ('native_entry=00408030','native_entry=004084a0'),('unit=3 selected_before','unit=2 selected_before')):
            self.assertIn(old,log);self.bad(log.replace(old,new))


ORIGINAL=Path('C:/Clash/clash95.exe');SAVE=Path('C:/Clash/save/0.dat')
CANDIDATE=Path('C:/ClashTests/hd-completion/framed-army-v1-1024x768-build-20260906-085300/clash95_army_1024x768_v1.exe')


@unittest.skipUnless(all(p.is_file() for p in (ORIGINAL,SAVE,CANDIDATE)),'read-only original/save/candidate required')
class BoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL.read_bytes();cls.save=SAVE.read_bytes();cls.candidate=CANDIDATE.read_bytes()
        cls.packet=trace.producer.build_portrait_probe(cls.original,cls.candidate,cls.save,capture_dir='C:/ClashCaptures/offline-portrait-trace',minimap_viewport=True)

    def evaluate(self,**updates):
        data=dict(original=self.original,candidate=self.candidate,save=self.save,generated_probe=self.packet['compiled_probe'].replace('\n','\r\n').encode('ascii'),
            supplemental_commands={p:t.replace('\n','\r\n').encode('ascii') for p,t in self.packet['supplemental_commands'].items()},snapshot_headers=headers_fixture(self.packet))
        data.update(updates)
        return trace.evaluate_bound_trace(log_fixture(self.packet),self.packet,**data)

    def test_real_whole_candidate_packet_commands_and_three_headers(self):
        report=self.evaluate();self.assertTrue(report['passed'],report['failures']);self.assertTrue(report['ready_for_host_capture'])
        self.assertTrue(report['source_authenticated']);self.assertTrue(report['snapshot_headers_verified'])
        self.assertEqual(len(report['source']['snapshot_headers']),3)
        for key in ('pixels_verified','cleanup_verified','runtime_accepted','manual_input_proof','promotion_ready'):self.assertFalse(report[key])
        changed=bytearray(self.candidate);changed[-1]^=1
        self.assertFalse(self.evaluate(candidate=bytes(changed))['passed'])
        changed=bytearray(self.save);changed[-1]^=1
        self.assertFalse(self.evaluate(save=bytes(changed))['passed'])

    def test_exact_disk_command_and_header_adversaries_after_real_reconstruction(self):
        # The real reconstruction above is separate; this records mutations at
        # the exact post-reconstruction boundary without repeating slow builds.
        with patch.object(trace.producer,'build_portrait_probe',return_value=copy.deepcopy(self.packet)):
            self.assertFalse(self.evaluate(generated_probe=b'changed')['passed'])
            for value in ({},None):self.assertFalse(self.evaluate(supplemental_commands=value)['passed'])
            commands={p:t.encode() for p,t in self.packet['supplemental_commands'].items()};path=next(iter(commands));commands[path]+=b'\n'
            self.assertFalse(self.evaluate(supplemental_commands=commands)['passed'])
            bad_header=self.evaluate(snapshot_headers={});self.assertFalse(bad_header['passed'])
            self.assertTrue(bad_header['portrait_sequence']['raw_records']);self.assertTrue(bad_header['source_authenticated'])
            for index,item in enumerate(trace.snapshot_paths(self.packet)):
                for offset,size,value in ((0,2,800),(2,2,600),(4,4,BASE+4),(184,4,0x50EE74)):
                    headers=headers_fixture(self.packet);raw=bytearray(headers[item['header_path']]);raw[offset:offset+size]=value.to_bytes(size,'little');headers[item['header_path']]=bytes(raw)
                    self.assertFalse(self.evaluate(snapshot_headers=headers)['passed'])
                headers=headers_fixture(self.packet);headers[item['header_path']]=b'\0'*187;self.assertFalse(self.evaluate(snapshot_headers=headers)['passed'])
            with patch.object(trace,'PRODUCER_SHA256','0'*64):self.assertFalse(self.evaluate()['passed'])
            with patch.dict(trace.HELPERS,{'tools/initial_map_paint_trace.py':'0'*64}):self.assertFalse(self.evaluate()['passed'])


class CliTests(unittest.TestCase):
    def test_bom_cli_reads_all_three_actual_commands_and_headers(self):
        packet=packet_fixture();log=log_fixture(packet);disk={p:t.encode() for p,t in packet['supplemental_commands'].items()}|headers_fixture(packet)
        real=Path.read_bytes
        def read(path):return disk[str(path).replace('\\','/')] if str(path).replace('\\','/') in disk else real(path)
        with tempfile.TemporaryDirectory(prefix='clash-portrait-cli-') as directory:
            files={name:Path(directory)/(name+'.txt') for name in ('log','packet','original','candidate','save','probe')}
            files['log'].write_bytes(b'\xef\xbb\xbf'+log.encode());files['packet'].write_bytes(b'\xef\xbb\xbf'+json.dumps(packet).encode())
            for name in ('original','candidate','save','probe'):files[name].write_bytes(name.encode())
            argv=['portrait-trace']+[x for name,path in files.items() for x in ('--'+name,str(path))]
            with patch('sys.argv',argv),patch.object(Path,'read_bytes',read),patch.object(trace,'evaluate_bound_trace',return_value=trace._result(packet,passed=True)) as evaluate,contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(trace.main(),0)
            args,kwargs=evaluate.call_args;self.assertEqual(args,(log,packet))
            self.assertEqual(kwargs['snapshot_headers'],headers_fixture(packet));self.assertEqual(set(kwargs['supplemental_commands']),set(packet['supplemental_commands']))
            self.assertEqual(json.loads(out.getvalue())['source']['log_raw_sha256'],trace.sha(files['log'].read_bytes()))


if __name__=='__main__':unittest.main(verbosity=2)
