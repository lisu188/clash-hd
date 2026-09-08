"""Pure synthetic marker adversaries and read-only whole-candidate binding.

No debugger, game, input, capture, candidate write or evidence refresh runs.
Synthetic logs exist only in memory and cannot become runtime artifacts.
"""
from __future__ import annotations
import copy
import contextlib
import io
import json
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import framed_army_transition_trace as trace
import test_initial_map_paint_trace as initial_fixture

TID=0xABC
SP=0x100100
GD=0x600000
SURFACE=0x900000
BASE=0xA00000
ROUTES=[('open',3,-1,-1,0,1,16,19),('switch',1,3,3,1,1,15,22),
        ('switch',2,1,1,1,1,15,23),('close',0,2,2,1,0,14,22),
        ('open',3,0,-1,0,1,16,19),('close',-1,3,3,1,0,None,None)]


def packet_fixture():
    _,extra=initial_fixture.fixture(resolution='1024x768',stage=trace.selection.initial_trace.FRAMED_STAGE)
    extra=extra.replace('stage='+trace.selection.initial_trace.FRAMED_STAGE+' ','stage='+trace.producer.base.builder.STAGE+' ')
    directory='C:/ClashCaptures/offline-transition-fixture'
    commands={f'{directory}/transition-{n}.cdb':f'.echo synthetic-nonexecuted-step-{n}\n' for n in range(1,7)}
    sites=dict(trace.NATIVE_SITES)|{'109':0x597000,'110':0x597800,'111':0x597A00}
    return dict(schema='clash95_framed_army_transition_probe_v1',revision=trace.producer.REVISION,
        stage=trace.producer.base.builder.STAGE,resolution='1024x768',width=1024,height=768,
        steps=copy.deepcopy(list(trace.producer.STEPS)),candidate_sha256='a'*64,
        original_sha256=trace.producer.base.clip.ORIGINAL_SHA256,save_sha256=trace.producer.base.SAVE_SHA256,
        capture_dir=directory,minimap_viewport=True,controlled_input=True,native_predicate_forced=False,
        selected_value_forced=False,runtime_executed=False,manual_input_proof=False,promotion_ready=False,
        compiled_probe='synthetic nonexecuted probe\n',probe_sha256=trace.sha(b'synthetic nonexecuted probe\n'),
        initial_extra=extra,initial_extra_sha256=trace.sha(extra.encode()),supplemental_commands=commands,
        supplemental_sha256={path:trace.sha(text.encode()) for path,text in commands.items()},
        observer_vas=sites,draw_return_vas=dict(native=0x597800,composition=0x597A00),
        map_return_vas=dict(open=0x423B3C,switch=0x40A5EA,close=0x423B64,deselect=0x409DC8))


def log_fixture(packet=None,*,native=1,compositions=1):
    packet=packet or packet_fixture()
    sites={int(n):int(va,16) for n,va in re.findall(r'(?m)^bp(7[0-7]) ([0-9a-fA-F]{8}) ',packet['initial_extra'])}
    lines=['ATX_BYTES_PASS',
        f"ARMY_CONTRACT_PASS stage={packet['stage']} resolution=1024x768 candidate_sha256={packet['candidate_sha256']} revision={trace.producer.base.builder.REVISION}",
        'ARMY_SCOPE own_player_0_to_3_native_size_panel manual_input_proof=false promotion_ready=false',
        f"PTILE_CONTRACT_PASS stage={packet['stage']} resolution=1024x768 candidate_sha256={packet['candidate_sha256']}",
        'PTILE_SCOPE guarded_map_only manual_input_proof=false promotion_ready=false']
    for n,event in enumerate(initial_fixture.initial_events('1024x768',framed=True),1):
        lines.append(f"PTILE_EVENT seq={n} bp={event['bp']} tid={TID:x} eip={sites[event['bp']]:08x} esp={event['esp']:08x}")
        lines.extend(event['records'])
    lines.append(f'PTILE_TRACE_CLOSED tid={TID:x} eip=00406fa0 esp={SP:08x}')
    for n,(branch,unit,old,prior,old_lower,lower,x,y) in enumerate(ROUTES,1):
        counts=[0,0,0,0,0];state=(old,prior,old_lower)
        def obs(kind,phase,eip,delta,*,eax=0,ecx=0,edx=0,esi=0,caller=0):
            selected,past,owner=state
            lines.append(f'ATX_OBS kind={kind} step={n} phase={phase} tid={TID:x} eip={eip:08x} esp={SP-delta:08x} '
                f'selected={selected} prior={past} lower={owner} owner=0040ad40 gd={GD:08x} eax={eax:x} ecx={ecx:x} edx={edx:x} esi={esi:x} caller={caller:08x} '
                f'draws=({counts[0]},{counts[1]},{counts[2]}) maps=({counts[3]},{counts[4]})')
        obs('begin',1,0x406FA0 if n==1 else 0x406FA1,0)
        if n<6:
            obs('occupancy',2,0x4080EF,24,esi=x,ecx=2*y,edx=unit)
            state=(unit,prior,old_lower)
            obs('selected',3,0x408131,24,eax=1)
            obs('updater',4,0x406980,4,caller=0x406FA1)
        else:
            obs('deselect-entry',2,0x409D81,8,eax=0x511D40)
            obs('deselect-write',3,0x409DA8,16,ecx=0xffffffff)
            state=(-1,prior,old_lower)
        obs('panel-update',5,0x40A500,20 if n==6 else 48,caller=0x409DB3 if n==6 else 0x40A4F2)
        obs(branch,6,dict(open=0x423B00,switch=0x423B90,close=0x423B40)[branch],36 if n==6 else 64,
            caller=dict(open=0x40A5F3,switch=0x40A5EA,close=0x40A51F)[branch])
        state=(unit,unit if lower else -1,lower)
        def draw(route,phase,depth):
            counts[0]+=1
            obs('draw-entry',phase,packet['observer_vas']['109'],depth,caller=packet['draw_return_vas'][route])
            counts[1]+=1
            if route=='composition':counts[2]+=1
            obs('draw-'+route+'-return',phase,packet['draw_return_vas'][route],depth-4,eax=native if route=='native' else 1)
        if lower:draw('native',6,192 if branch=='open' else 184)
        def map_pair(route,phase,depth):
            counts[3]+=1;obs('map-entry',phase,0x418700,depth,caller=packet['map_return_vas'][route])
            if lower:
                for _ in range(compositions):draw('composition',phase,depth+240)
            counts[4]+=1;obs('map-return',phase+1,packet['map_return_vas'][route],depth-4)
        map_pair(branch,7,48 if n==6 else 64 if branch=='switch' else 76)
        if n==6:
            obs('deselect-panel-return',8,0x409DB3,16)
            map_pair('deselect',9,20)
        obs('snapshot',10 if n==6 else 8,0x406FA1,0)
        lines.append(f'ATX_SURFACE step={n} surface={SURFACE:08x} base={BASE:08x} width=1024 height=768 vtable=0050ee24')
    lines += [f'ATX_READY tid={TID:x} eip=00406fa1 esp={SP:08x} selected=-1 prior=-1 lower=0 owner=0040ad40 surface={SURFACE:08x} base={BASE:08x} width=1024 height=768 vtable=0050ee24','ATX_HOST_READY']
    return '\n'.join(lines)+'\n'


class SequenceTests(unittest.TestCase):
    def bad(self,log,packet=None):
        report=trace.evaluate_trace(log,packet or packet_fixture())
        self.assertFalse(report['passed'],report);self.assertTrue(report['failures'])
        self.assertFalse(report['ready_for_host_capture']);return report

    def test_all_six_branches_and_native_fallback_are_separate_from_pixels(self):
        for native in (0,1):
            for count in (1,3):
                report=trace.evaluate_trace(log_fixture(native=native,compositions=count),packet_fixture())
                self.assertTrue(report['passed'],report['failures'])
                sequence=report['transition_sequence']
                self.assertEqual(len(sequence['steps']),6);self.assertEqual(len(sequence['surfaces']),6)
                self.assertEqual(len(sequence['map_calls']),7);self.assertEqual(len(sequence['draw_calls']),4*(count+1))
                self.assertEqual(sequence['native_fallbacks'],4 if native==0 else 0)
                self.assertEqual([s['final_state'] for s in sequence['steps']],
                    [dict(selected=v,prior=p,lower=l) for v,p,l in ((3,3,1),(1,1,1),(2,2,1),(0,-1,0),(3,3,1),(-1,-1,0))])
                for key in ('source_authenticated','whole_candidate_bound','all_supplemental_commands_bound',
                            'ready_for_host_capture','runtime_accepted','pixels_verified','cleanup_verified','manual_input_proof','promotion_ready'):
                    self.assertFalse(report[key],key)

    def test_every_transition_marker_missing_or_duplicated_fails(self):
        lines=log_fixture().splitlines()
        for n,line in enumerate(lines):
            if not line.startswith(('ATX_','ARMY_')):continue
            with self.subTest(missing=line):self.bad('\n'.join(lines[:n]+lines[n+1:]))
            with self.subTest(duplicate=line):self.bad('\n'.join(lines[:n]+[line]+lines[n:]))

    def test_every_observer_identity_state_register_counter_and_stack_is_checked(self):
        lines=log_fixture().splitlines()
        for n,line in enumerate(lines):
            if not line.startswith('ATX_OBS'):continue
            for field,value in (('step','7'),('phase','12'),('tid','def'),('eip','00400000'),
                                ('selected','99'),('prior','99'),('lower','9'),('owner','00422020'),('gd','00601000')):
                changed=lines.copy();changed[n]=re.sub(r'\b'+field+r'=[^ ]+',field+'='+value,line)
                with self.subTest(line=n,field=field):self.bad('\n'.join(changed))
            changed=lines.copy();changed[n]=line.replace('draws=(', 'draws=(99,')
            self.bad('\n'.join(changed))
        for old,new in (('ecx=26 edx=3 esi=10','ecx=24 edx=3 esi=10'),
                        ('eax=1 ecx=0','eax=0 ecx=0'),('caller=00406fa1','caller=00406fa0'),
                        ('ecx=ffffffff','ecx=0'),('eax=511d40','eax=511d75'),
                        ('caller=0040a5ea','caller=00423bae')):
            self.bad(log_fixture().replace(old,new))

    def test_draw_map_pair_order_status_and_exact_native_stacks(self):
        log=log_fixture()
        for old,new in (('esp=00100040','esp=00100044'),('esp=00100044','esp=00100048'),
                        ('esp=001000c0','esp=001000c4'),('esp=001000b4','esp=001000b0'),
                        ('caller=00597800','caller=00597a00'),('maps=(2,2)','maps=(1,1)'),
                        ('draws=(2,2,1)','draws=(2,2,0)')):
            self.assertIn(old,log);self.bad(log.replace(old,new))
        lines=log.splitlines()
        i=next(i for i,l in enumerate(lines) if 'kind=draw-composition-return' in l)
        for status in (0,2,0xffffffff):
            changed=lines.copy();changed[i]=changed[i].replace('eax=1 ',f'eax={status:x} ');self.bad('\n'.join(changed))
        for marker in ('draw-native-return','draw-composition-return','map-return'):
            i=next(i for i,l in enumerate(lines) if 'kind='+marker+' ' in l)
            for field in ('ecx','edx','esi'):
                changed=lines.copy();changed[i]=changed[i].replace(field+'=0 ',field+'=1234 ');self.bad('\n'.join(changed))
        self.bad(log_fixture(compositions=0))
        # Swap the two genuine deselect map-return addresses, retaining all rows.
        lines=[line.replace('eip=00423b64','eip=00409dc8') if 'step=6 ' in line else line for line in lines]
        self.bad('\n'.join(lines))

    def test_surfaces_errors_unknown_records_and_failed_prefix_remain_failed(self):
        log=log_fixture()
        for old,new in (('surface=00900000','surface=0051d4c0'),('width=1024','width=800'),
                        ('vtable=0050ee24','vtable=0050ee74'),('ATX_SURFACE step=3','ATX_SURFACE step=2'),
                        ('ATX_READY','atx_ready'),('base=00a00000 width','base=fffffff0 width')):
            self.bad(log.replace(old,new))
        for tail in ('ATX_REJECT native_contract','ATX_OBS kind=unknown','0:000> ATX_HOST_READY',
                     'AV_SURFDUMP code=c0000005','Syntax error','timeout reached','SURFDUMP_APP_REQUEST_QUIT',
                     'PTILE_EVENT seq=999','SHSEL_HOST_READY','ATX_HOST_READY extra=1'):
            self.bad(log+tail+'\n')
        report=self.bad(log.split('ATX_OBS kind=begin')[0]+'ATX_REJECT native_contract\n')
        self.assertTrue(report['initial_map_trace']['passed']);self.assertIsNone(report['surface'])

    def test_exact_projection_preserves_old_trace_failures_and_other_lines(self):
        packet=packet_fixture();log=log_fixture(packet)
        projected,extra,binding=trace.selection._project(log,packet['initial_extra'],packet)
        self.assertEqual([i for i,(a,b) in enumerate(zip(log.splitlines(),projected.splitlines())) if a!=b],[3])
        self.assertIn(packet['candidate_sha256'],projected.splitlines()[3])
        self.assertEqual(binding['log']['original_sha256'],trace.sha(log.encode()))
        for old,new in (('PTILE_EVENT seq=4','PTILE_EVENT seq=3'),('PTILE_INITIAL_RETURN','PTILE_UNKNOWN'),
                        ('PTILE_STATUS hook=full_present status=1','PTILE_STATUS hook=full_present status=0')):
            self.bad(log.replace(old,new))

    def test_packet_embedded_supplemental_inventory_and_bindings_are_strict(self):
        p=packet_fixture();log=log_fixture(p)
        for field,value in (('revision','stale'),('stage','stale'),('steps',list(reversed(p['steps']))),
                            ('selected_value_forced',True),('minimap_viewport',None),('candidate_sha256','x'*64),
                            ('initial_extra','modified'),('compiled_probe','modified'),('observer_vas',{}),
                            ('supplemental_commands',{}),('supplemental_sha256',{}),('map_return_vas',{})):
            changed=copy.deepcopy(p);changed[field]=value;self.bad(log,changed)
        self.assertFalse(trace.evaluate_trace(log,None)['passed'])

    def test_cli_decodes_real_bom_files_and_passes_every_actual_command_byte(self):
        # Exercise real stdlib UTF-8 BOM decoding. The expensive bound API is
        # covered independently below; only its call boundary is recorded here.
        packet=packet_fixture();log=log_fixture(packet)
        command_bytes={path:text.replace('\n','\r\n').encode('ascii')
                       for path,text in packet['supplemental_commands'].items()}
        real_read_bytes=Path.read_bytes
        def read_bytes(path):
            return command_bytes[str(path).replace('\\','/')] if str(path).replace('\\','/') in command_bytes else real_read_bytes(path)
        with tempfile.TemporaryDirectory(prefix='clash-transition-cli-') as directory:
            root=Path(directory)
            files={name:root/(name+'.txt') for name in ('log','packet','original','candidate','save','probe')}
            files['log'].write_bytes(b'\xef\xbb\xbf'+log.encode('utf-8'))
            files['packet'].write_bytes(b'\xef\xbb\xbf'+json.dumps(packet).encode('utf-8'))
            for name in ('original','candidate','save','probe'):files[name].write_bytes(('fixture-'+name).encode())
            argv=['transition-trace']+[item for name,path in files.items() for item in ('--'+name,str(path))]
            expected=trace._result(packet,passed=True,source={})
            output=io.StringIO()
            with patch('sys.argv',argv),patch.object(Path,'read_bytes',read_bytes),\
                    patch.object(trace,'evaluate_bound_trace',return_value=expected) as evaluate,contextlib.redirect_stdout(output):
                self.assertEqual(trace.main(),0)
            args,kwargs=evaluate.call_args
            self.assertEqual(args,(log,packet))
            self.assertEqual(kwargs['supplemental_commands'],command_bytes)
            for name in ('original','candidate','save'):self.assertEqual(kwargs[name],('fixture-'+name).encode())
            self.assertEqual(kwargs['generated_probe'],b'fixture-probe')
            self.assertEqual(json.loads(output.getvalue())['source']['log_raw_sha256'],trace.sha(files['log'].read_bytes()))


ORIGINAL=Path('C:/Clash/clash95.exe')
SAVE=Path('C:/Clash/save/0.dat')
CANDIDATE=Path('C:/ClashTests/hd-completion/framed-army-v1-1024x768-build-20260906-085300/clash95_army_1024x768_v1.exe')


@unittest.skipUnless(all(p.is_file() for p in (ORIGINAL,SAVE,CANDIDATE)),'requires original/save/candidate for read-only reconstruction')
class BoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL.read_bytes();cls.save=SAVE.read_bytes();cls.candidate=CANDIDATE.read_bytes()
        cls.packet=trace.producer.build_transition_probe(cls.original,cls.candidate,cls.save,
                       capture_dir='C:/ClashCaptures/offline-transition-fixture',minimap_viewport=True)
        cls.log=log_fixture(cls.packet)
        cls.args=dict(original=cls.original,candidate=cls.candidate,save=cls.save,
            generated_probe=cls.packet['compiled_probe'].replace('\n','\r\n').encode('ascii'),
            supplemental_commands={p:t.replace('\n','\r\n').encode('ascii') for p,t in cls.packet['supplemental_commands'].items()})

    def test_real_schema_whole_reconstruction_and_all_six_actual_command_bytes(self):
        report=trace.evaluate_bound_trace(self.log,self.packet,**self.args)
        self.assertTrue(report['passed'],report['failures'])
        for key in ('source_authenticated','whole_candidate_bound','all_supplemental_commands_bound','ready_for_host_capture'):
            self.assertTrue(report[key],key)
        self.assertEqual(len(report['source']['supplemental_commands']),6)
        self.assertFalse(report['runtime_accepted']);self.assertFalse(report['pixels_verified']);self.assertFalse(report['cleanup_verified'])

    def test_each_supplemental_missing_changed_extra_and_source_candidate_boundaries(self):
        # Genuine reconstruction remains covered above. Memoize that exact result
        # only for adversarial comparisons at the independent file boundary.
        with patch.object(trace.producer,'build_transition_probe',return_value=self.packet):
            for path in self.args['supplemental_commands']:
                for kind in ('missing','changed'):
                    cmds=dict(self.args['supplemental_commands'])
                    if kind=='missing':del cmds[path]
                    else:cmds[path]+=b'gc\n'
                    report=trace.evaluate_bound_trace(self.log,self.packet,**(self.args|{'supplemental_commands':cmds}))
                    self.assertFalse(report['passed']);self.assertIsNone(report['initial_projection'])
            for field,value in (('generated_probe',self.args['generated_probe']+b'gc\n'),
                    ('supplemental_commands',self.args['supplemental_commands']|{'C:/ClashCaptures/extra.cdb':b'q\n'})):
                self.assertFalse(trace.evaluate_bound_trace(self.log,self.packet,**(self.args|{field:value}))['passed'])
            bad=copy.deepcopy(self.packet);bad['source_sha256']['unreviewed.py']='a'*64
            self.assertFalse(trace.evaluate_bound_trace(self.log,bad,**self.args)['passed'])
        for key in ('candidate','save'):
            data=bytearray(self.args[key]);data[-1]^=1
            report=trace.evaluate_bound_trace(self.log,self.packet,**(self.args|{key:bytes(data)}))
            self.assertFalse(report['passed']);self.assertFalse(report['whole_candidate_bound'])
        with patch.object(trace,'PRODUCER_SHA256','0'*64):
            self.assertFalse(trace.evaluate_bound_trace(self.log,self.packet,**self.args)['passed'])


if __name__=='__main__':unittest.main()
