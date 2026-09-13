"""Synthetic Complete-HD movement parser fixtures; never runtime evidence.

Native v3 pump pairs are part of every positive baseline. Real binding coverage
uses actual reconstructed candidates plus invented logs, without executing them.
"""
from __future__ import annotations
import copy
import contextlib
import io
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest.mock import patch

import complete_hd_army_movement_trace as trace
import test_complete_hd_army_selection_trace as base_fixture

TID=0xABC;SP=0x100100;GD=0x600000;SURFACE=0x900000;BASE=0xA00000
AP=(26,22,16,16,16,16,16,16)


def packet_fixture(resolution='1024x768'):
    base=base_fixture.packet_fixture(resolution);directory='C:/ClashCaptures/offline-complete-movement-trace'
    commands={f'{directory}/movement-checkpoint-{n}.cdb':f'$$ synthetic-not-executable-{n}\n' for n in range(3)}
    return base | dict(schema='clash95_complete_hd_army_movement_probe_v1',revision=trace.producer.REVISION,
        capture_dir=directory,unit=3,mouse_shift_max=21,source_xy=[16,19],destination_xy=[18,19],
        controlled_scroll=[10,17],controlled_mouse=[576,176],expected_initial_ap=list(AP),expected_final_ap=[v-10 for v in AP],
        expected_path_count=2,expected_path_words=list(trace.producer.PATH_WORDS),supplemental_commands=commands,
        supplemental_sha256={p:trace.sha(t.encode()) for p,t in commands.items()},
        baseline_observer_vas=base['observer_vas'],baseline_native_call_returns=base['native_call_returns'],
        movement_observer_vas={str(n):va for n,va in trace.SITES.items()},
        parent_source_sha256=trace.producer.PARENT_SOURCE_SHA256,
        max_pump_calls_per_click=1024,pump_observers=copy.deepcopy(trace.PUMPS),
        controlled_input=True,controlled_release=True,selected_value_forced=False,flag_value_forced=False,movement_state_forced=False)


def synthetic_record():
    data=bytearray(725);struct.pack_into('<hh',data,0,16,19)
    for i,kind in enumerate((16,16,1,1,1,1,1,1,-1,-1)):
        struct.pack_into('<h',data,6+31*i,kind)
        if i<8:data[14+31*i]=AP[i]
    return bytes(data)


def unit_fixture(packet,source=None):
    before=source or synthetic_record();preview=bytearray(before)
    struct.pack_into('<iII',preview,316,2,0xA1312,0x51311)
    after=bytearray(preview);struct.pack_into('<hh',after,0,18,19);struct.pack_into('<i',after,316,0)
    for i in range(8):after[14+31*i]-=10
    return {item['unit_path']:raw for item,raw in zip(trace.snapshot_paths(packet),(before,bytes(preview),bytes(after)))}


def headers_fixture(packet):
    data=bytearray(188);struct.pack_into('<HHI',data,0,packet['width'],packet['height'],BASE);struct.pack_into('<I',data,184,0x50EE24)
    return {x['header_path']:bytes(data) for x in trace.snapshot_paths(packet)}


def log_fixture(packet=None,*,warmup=0,extra_draw=False,source_record=None,shift=6):
    packet=packet or packet_fixture();base=copy.deepcopy(packet)
    base.update(native_call_returns=packet['baseline_native_call_returns'])
    text=base_fixture.log_fixture(base,native_status=warmup).replace('SHSEL_','WMOV_BASE_')
    contract=f"WMOV_CONTRACT revision={trace.producer.REVISION} candidate_sha256={packet['candidate_sha256']} save_sha256={packet['save_sha256']} source=(16,19) target=(18,19) clicks=2"
    text=text.replace('\nPTILE_EVENT seq=1 ','\nWMOV_BYTES_PASS\n'+contract+'\nPTILE_EVENT seq=1 ',1).replace('WMOV_BASE_HOST_READY\n','')
    text=text.replace('esp=000ff000',f'esp={SP-192:08x}').replace('esp=000ff004',f'esp={SP-188:08x}')
    text=text.replace('esp=000fe000',f'esp={SP-316:08x}').replace('esp=000fe004',f'esp={SP-312:08x}')
    lines=text.splitlines()
    raw=source_record or synthetic_record();initial_path=struct.unpack_from('<II',raw,320)
    def surface(n):lines.append(f'WMOV_SURFACE checkpoint={n} tid={TID:x} eip=00406fa1 esp={SP:08x} surface={SURFACE:08x} base={BASE:08x} width={packet['width']} height={packet['height']} vtable=0050ee24')
    surface(0)
    for click in (1,2):
        counts=[0,0,0];pump_count=0;steps=0;buttons=1;accumulator=0x80;x=16;queue=0 if click==1 else 2;cost=0;occupancy=[3,65535,65535]
        path=initial_path if click==1 else (0xA1312,0x51311)
        def obs(kind,phase,eip,depth,*,caller=0,eax=0,ebx=0,ecx=0,edx=0,esi=0,edi=0,ebp=0):
            aps=','.join(str(a-cost) for a in AP);occs=','.join(f'{n:x}' for n in occupancy)
            lines.append(f'WMOV_OBS kind={kind} click={click} phase={phase} tid={TID:x} eip={eip:08x} esp={SP-depth:08x} caller={caller:08x} '
                f'eax={eax:x} ebx={ebx:x} ecx={ecx:x} edx={edx:x} esi={esi:x} edi={edi:x} ebp={ebp:x} selected=3 prior=3 lower=1 unit={GD+149349:08x} '
                f'xy=({x},19) path=({queue},{path[0]:x},{path[1]:x}) ap=({aps}) occupancy=({occs}) buttons={buttons:x} accumulator={accumulator:x} steps={steps} draws=({counts[0]},{counts[1]},{counts[2]})')
        def draw(route,phase,depth):
            ret=packet['baseline_native_call_returns']['native_draw' if route=='native' else 'composition_draw']
            counts[0]+=1;obs('draw-entry',phase,packet['baseline_observer_vas']['90'],depth,caller=ret,ebx=7,ecx=8,edx=9,esi=10,edi=11,ebp=12)
            counts[1]+=1;counts[2]+=int(route=='composition')
            obs('draw-'+route+'-return',phase,ret,depth-4,eax=1,ebx=7,ecx=8,edx=9,esi=10,edi=11,ebp=12)
        def pump(kind,phase):
            nonlocal pump_count,buttons,accumulator
            spec=next(p for p in trace.PUMPS if p['kind']==kind);pump_count+=1
            for suffix,site in (('call',spec['call']),('return',spec['returned'])):
                if suffix=='return':buttons=3;accumulator=0x90
                lines.append(f"WMOV_PUMP kind={kind}-{suffix} count={pump_count} phase={phase} tid={TID:x} eip={site:08x} esp={SP-spec['stack_depth']:08x} eax={0x544cd8 if suffix=='call' else 0:x} edx=0 raw=({576<<shift:x},{176<<shift:x}) shift={shift:x} buttons={buttons:x} accumulator={accumulator:x} secondary=0")
        phase=20 if click==1 else 40
        lines.append(f'WMOV_MOUSE click={click} tid={TID:x} eip=00406fa1 esp={SP:08x} raw=({576<<shift:x},{176<<shift:x}) shift={shift:x}')
        obs('begin',phase,0x406FA1,0)
        obs('post-push',phase+1,0x4084A1,8)
        obs('framed-admission-return',phase+2,0x4084AE,116)
        obs('left-sample-return',phase+3,0x40856D,116,eax=1)
        obs('fog-return',phase+4,0x408594,116,eax=0xffffffff)
        obs('right-return',phase+5,0x408733,116)
        obs('left-return',phase+6,0x4087E1,116,eax=1)
        obs('empty-target-return',phase+7,0x4099E3,116,ebp=18)
        if click==1:
            obs('track-call',28,0x409A6C,120,caller=19,eax=3,edx=16,ecx=18,ebx=19)
            obs('track-entry',29,0x4147A0,124,caller=0x409A71,eax=3,edx=16,ecx=18,ebx=19)
            pump('pathfinder',29)
            obs('track-return',30,0x409A71,116,eax=0xB00000)
            queue=2;path=(0xA1312,0x51311);obs('track-copied',31,0x409AB5,116)
            obs('preview-wait-call',32,0x409CA6,116)
            obs('preview-release-before',32,0x409CA6,116)
            buttons=accumulator=0;obs('preview-release-after',32,0x409CA6,116)
            obs('release-entry',33,0x4609D0,120,caller=0x409CAB,eax=0x544CD8)
            obs('release-left-return',34,0x4609E0,132)
            obs('release-right-return',35,0x4609FC,132)
            obs('release-return',36,0x409CAB,116)
            if extra_draw:draw('native',36,300)
            draw('composition',36,420)
            obs('preview-redraw-return',37,0x409CB5,116)
            obs('preview-ret',38,0x409CBE,4,caller=0x406FA1)
        else:
            obs('affordability-call',48,0x409BC5,116,eax=3)
            obs('affordability-return',49,0x409BCA,116,eax=1)
            obs('execute-call',50,0x409C0E,116,eax=3,edx=1)
            obs('execute-release-before',50,0x409C0E,116,eax=3,edx=1)
            buttons=accumulator=0;obs('execute-release-after',50,0x409C0E,116,eax=3,edx=1)
            obs('execute-entry',51,0x410330,120,caller=0x409C13,eax=3,edx=1)
            for step in (1,2):
                obs('spend-call',52,0x4108DF,328,eax=GD+149349,edx=5)
                steps=step;cost=step*5;obs('spend-return',53,0x4108E4,328)
                queue=2-step;obs('path-decrement',54,0x410747,328)
                pump('animation',54)
                x=16+step;occupancy=[65535,3,65535] if step==1 else [65535,65535,3]
                obs('xy-occupancy-commit',51,0x410AF7,328,edi=GD+149349)
                pump('delay',51)
                if extra_draw:draw('native',51,600)
            draw('composition',51,632)
            obs('execute-redraw-return',55,0x4105F7,328)
            obs('execute-ret',56,0x410615,120,caller=0x409C13)
            obs('execute-return',57,0x409C13,116)
            obs('updater-return',58,0x409C18,116)
            obs('world-ret',59,0x409C21,4,caller=0x406FA1)
        surface(click)
        if click==2:obs('ready',59,0x406FA1,0)
    lines.append('WMOV_HOST_READY')
    return '\n'.join(lines)+'\n'


def mutate(log, kind, key, value, *, occurrence=0):
    lines=log.splitlines()
    found=[i for i,line in enumerate(lines) if 'kind='+kind+' ' in line]
    i=found[occurrence]
    changed=re.sub(r'\b'+key+r'=[^ ]+',key+'='+value,lines[i])
    if changed==lines[i]:raise AssertionError('mutation did not change baseline')
    lines[i]=changed
    return '\n'.join(lines)+'\n'


class SequenceTests(unittest.TestCase):
    def bad(self, log, packet=None):
        result=trace.evaluate_trace(log,packet or packet_fixture())
        self.assertFalse(result['passed'],result['failures'])
        self.assertTrue(result['failures']);self.assertFalse(result['ready_for_host_capture'])
        return result

    def test_valid_v3_all_six_geometries_with_fallbacks_and_native_input_changes(self):
        for resolution in trace.producer.base.builder.RESOLUTIONS:
            packet=packet_fixture(resolution)
            for warmup in (0,1):
                for extra in (False,True):
                    with self.subTest(resolution=resolution,warmup=warmup,extra=extra):
                        report=trace.evaluate_trace(log_fixture(packet,warmup=warmup,extra_draw=extra),packet)
                        self.assertTrue(report['passed'],report['failures'])
                        sequence=report['movement_sequence']
                        self.assertEqual([c['steps'] for c in sequence['clicks']],[0,2])
                        self.assertEqual([p['kind'] for p in sequence['pump_calls']],['pathfinder','animation','delay','animation','delay'])
                        self.assertEqual(sequence['baseline_native_fallbacks'],1-warmup)
                        self.assertEqual(sequence['ready']['x'],18)
                        self.assertEqual(len(report['snapshots']),3)
                        self.assertIsNone(report['initial_map_trace']);self.assertTrue(report['sequence_only'])
                        for key in ('source_authenticated','whole_candidate_bound','candidate_manifest_bound','ready_for_host_capture',
                                    'snapshot_headers_verified','snapshot_units_verified','runtime_accepted','pixels_verified',
                                    'cleanup_verified','manual_input_proof','promotion_ready','initial_log_projected'):
                            self.assertFalse(report[key],key)

    def test_every_native_record_missing_duplicate_or_prefixed_fails(self):
        baseline=log_fixture();self.assertTrue(trace.evaluate_trace(baseline,packet_fixture())['passed'])
        lines=baseline.splitlines()
        for i,line in enumerate(lines):
            if not line.startswith(('WMOV_','ARMY_','COMPLETEHD_CONTRACT','PTILE_CONTRACT')):continue
            with self.subTest(record=i):
                self.bad('\n'.join(lines[:i]+lines[i+1:]))
                self.bad('\n'.join(lines[:i]+[line]+lines[i:]))
                prefixed=lines.copy();prefixed[i]='0:000> '+line;self.bad('\n'.join(prefixed))

    def test_actual_commits_ap_costs_queue_native_abi_and_returns_required(self):
        baseline=log_fixture(extra_draw=True)
        mutations=(('spend-call','edx','6'),('spend-return','ap','(26,22,16,16,16,16,16,16)'),
            ('path-decrement','path','(2,a1312,51311)'),('xy-occupancy-commit','xy','(16,19)'),
            ('xy-occupancy-commit','occupancy','(3,3,ffff)'),('xy-occupancy-commit','edi','00600000'),
            ('framed-admission-return','eax','1'),('left-sample-return','eax','0'),('fog-return','eax','0'),
            ('right-return','eax','1'),('left-return','eax','0'),('empty-target-return','ebp','11'),
            ('track-call','edx','11'),('track-entry','caller','00409a70'),('track-return','eax','1'),
            ('affordability-return','eax','0'),('execute-ret','caller','00406fa1'),('world-ret','caller','00409c13'),
            ('execute-return','eip','00409c14'),('ready','xy','(17,19)'),('ready','path','(1,a1312,51311)'))
        for kind,key,value in mutations:
            with self.subTest(kind=kind,key=key):self.bad(mutate(baseline,kind,key,value))
        for line in baseline.splitlines():
            if not line.startswith('WMOV_OBS'):continue
            for key,value in (('click','3'),('phase','90'),('tid','def'),('esp','00100001'),('selected','0'),
                              ('prior','0'),('lower','0'),('unit','00600000'),('steps','9'),('buttons','4'),('accumulator','100')):
                changed=re.sub(r'\b'+key+r'=[^ ]+',key+'='+value,line)
                with self.subTest(record=line.split()[1],key=key):self.bad(baseline.replace(line,changed,1))
        lines=baseline.splitlines()
        for first,second in (('spend-return','path-decrement'),('execute-ret','execute-return'),('world-ret','ready')):
            changed=lines.copy();a=next(i for i,v in enumerate(changed) if 'kind='+first+' ' in v);b=next(i for i,v in enumerate(changed) if 'kind='+second+' ' in v)
            changed[a],changed[b]=changed[b],changed[a];self.bad('\n'.join(changed))

    def test_bounded_pump_pairing_counts_abi_phases_and_observed_input(self):
        baseline=log_fixture()
        for kind in ('pathfinder','animation','delay'):
            for suffix in ('call','return'):
                for key,value in (('count','0'),('phase','99'),('tid','def'),('eip','00400000'),('esp','00100000'),
                                  ('buttons','4'),('accumulator','100'),('secondary','100'),('shift','100'),('eax','100000000')):
                    with self.subTest(kind=kind,suffix=suffix,key=key):self.bad(mutate(baseline,kind+'-'+suffix,key,value))
            self.bad(mutate(baseline,kind+'-call','eax','0'))
            self.bad(mutate(baseline,kind+'-call','edx','1'))
        # A native return may refresh mouse/buttons; do not invent a held-input
        # invariant or a returned HRESULT. These changed observations are valid.
        altered=mutate(baseline,'pathfinder-return','eax','ffffffff')
        altered=mutate(altered,'pathfinder-return','raw','(1,2)')
        self.assertTrue(trace.evaluate_trace(altered,packet_fixture())['passed'])
        rows=baseline.splitlines();first=next(i for i,v in enumerate(rows) if 'kind=pathfinder-call ' in v)
        self.bad('\n'.join(rows[:first]+rows[first+2:]))
        repeated=rows.copy();pair=rows[first:first+2]
        repeated[first:first+2]=[re.sub(r'count=1\b','count='+str(i),row) for i in range(1,1026) for row in pair]
        self.bad('\n'.join(repeated))

    def test_release_draw_pairs_and_all_preserved_native_registers(self):
        baseline=log_fixture(extra_draw=True)
        for kind in ('preview-release-after','execute-release-after'):
            for key,value in (('buttons','1'),('accumulator','80')):self.bad(mutate(baseline,kind,key,value))
        for kind in ('draw-native-return','draw-composition-return','preview-release-after','execute-release-after','preview-ret','world-ret','ready'):
            for register in ('ebx','ecx','edx','esi','edi','ebp'):
                self.bad(mutate(baseline,kind,register,'99'))
        self.bad(mutate(baseline,'draw-composition-return','eax','0'))
        self.bad(mutate(baseline,'draw-composition-return','draws','(1,0,1)'))
        self.bad(mutate(baseline,'draw-entry','caller','00400000'))

    def test_dynamic_surface_extent_and_signed_safe_target_mouse(self):
        for resolution in trace.producer.base.builder.RESOLUTIONS:
            packet=packet_fixture(resolution);baseline=log_fixture(packet)
            maximum=0x100000000-packet['width']*packet['height']
            self.assertTrue(trace.evaluate_trace(baseline.replace('base=00a00000',f'base={maximum:08x}'),packet)['passed'])
            self.bad(baseline.replace('base=00a00000',f'base={maximum+1:08x}'),packet)
            self.bad(baseline.replace('surface=00900000','surface=0051d4c0'),packet)
            self.bad(baseline.replace(f"width={packet['width']} height={packet['height']}",'width=640 height=480'),packet)
        for shift in (0,1,3,6,10,21):
            self.assertTrue(trace.evaluate_trace(log_fixture(shift=shift),packet_fixture())['passed'])
        for shift in (22,31):self.bad(log_fixture(shift=shift))
        self.bad(log_fixture().replace('raw=(9000,2c00)','raw=(8fc0,2c00)'))

    def test_all_contracts_failures_and_tail_are_retained(self):
        packet=packet_fixture();baseline=log_fixture(packet)
        for marker in ('ARMY_CONTRACT_PASS','COMPLETEHD_CONTRACT_PASS','PTILE_CONTRACT_PASS','WMOV_CONTRACT'):
            line=next(v for v in baseline.splitlines() if v.startswith(marker))
            self.bad(baseline.replace(line,line.replace(packet['candidate_sha256'],'f'*64)))
            self.bad(baseline.replace(line,'')+line+'\n')
        for tail in ('WMOV_UNKNOWN','WMOV_BASE_HOST_READY','WMOV_REJECT injected','Access violation','COMPLETEHD_CONTRACT_FAIL bytes',
                     'SHSEL_HOST_READY','PTILE_EVENT seq=99 bp=72 tid=abc eip=00400000 esp=00100100','SURFDUMP_REDRAW tick=999'):
            self.bad(baseline+tail+'\n')

    def test_packet_strict_types_sources_routes_and_declared_claims(self):
        packet=packet_fixture();baseline=log_fixture(packet)
        for key,value in (('width',1024.0),('unit',True),('resolution','640x480'),('mouse_shift_max',22),('max_pump_calls_per_click',1025),
            ('pump_observers',[]),('destination_xy',[17,19]),('expected_final_ap',[16]*8),('movement_state_forced',True),
            ('controlled_release',False),('minimap_viewport',None),('candidate_recipe','old'),('parent_source_sha256','f'*64),
            ('inherited_stage',packet['stage']),('candidate_manifest_canonical_sha256','bad'),('source_sha256',{}),
            ('supplemental_commands',{}),('baseline_observer_vas',{})):
            with self.subTest(key=key):self.bad(baseline,packet|{key:value})
        recursive={};recursive['self']=recursive
        self.bad(baseline,packet|{'invalid':recursive})
        class Alias(int):pass
        self.bad(baseline,packet|{'width':Alias(1024)})
        self.assertFalse(trace.evaluate_trace('',None)['passed'])


@contextlib.contextmanager
def synthetic_binding(packet, manifest):
    """Replace only byte reconstruction for explicit non-executable fixtures."""
    expected=copy.deepcopy(packet)
    def build(original,candidate,save,*,capture_dir,candidate_manifest,resolution):
        if (original,candidate,save,capture_dir,resolution)!=(base_fixture.ORIGINAL,base_fixture.CANDIDATE,base_fixture.SAVE,expected['capture_dir'],expected['resolution']):
            raise ValueError('synthetic original/candidate/save/options differ')
        if trace.canonical(candidate_manifest)!=trace.canonical(manifest):raise ValueError('synthetic manifest differs')
        return copy.deepcopy(expected)
    def context(candidate_manifest,original,*,resolution,candidate=None,probe=None,**kwargs):
        if original!=base_fixture.ORIGINAL or resolution!=expected['resolution'] or trace.canonical(candidate_manifest)!=trace.canonical(manifest):
            raise ValueError('synthetic complete context differs')
        if candidate is not None and candidate!=base_fixture.CANDIDATE or probe is not None and probe!=expected['initial_extra']:
            raise ValueError('synthetic candidate or canonical initial probe differs')
        return dict(manifest=copy.deepcopy(manifest),candidate=base_fixture.CANDIDATE,probe=expected['initial_extra'],
            inherited_stage=expected['inherited_stage'],framed={})
    with patch.object(trace.producer,'build_movement_probe',side_effect=build) as builder, \
         patch.object(trace.selection.runtime,'verify_context',side_effect=context) as complete:
        yield builder,complete


class BoundTests(unittest.TestCase):
    def setUp(self):
        original_pin=patch.object(trace.producer.base.clip,'ORIGINAL_SHA256',trace.sha(base_fixture.ORIGINAL))
        save_pin=patch.object(trace.producer.base,'SAVE_SHA256',trace.sha(base_fixture.SAVE))
        original_pin.start();save_pin.start();self.addCleanup(original_pin.stop);self.addCleanup(save_pin.stop)
        self.packet=packet_fixture();self.manifest=base_fixture.manifest_fixture('1024x768')

    def evaluate(self, packet=None, log=None, **changes):
        p=packet or self.packet
        args=dict(original=base_fixture.ORIGINAL,candidate=base_fixture.CANDIDATE,save=base_fixture.SAVE,
            candidate_manifest=self.manifest,generated_probe=p['compiled_probe'].encode(),
            supplemental_commands={path:text.encode() for path,text in p['supplemental_commands'].items()})
        args.update(changes)
        return trace.evaluate_bound_trace(log if log is not None else log_fixture(p),p,**args)

    def test_six_bound_geometries_unchanged_initial_log_and_three_quiet_commands(self):
        for resolution in trace.producer.base.builder.RESOLUTIONS:
            p=packet_fixture(resolution);manifest=base_fixture.manifest_fixture(resolution);log=log_fixture(p)
            with synthetic_binding(p,manifest),patch.object(trace.selection.initial_trace,'evaluate_trace',wraps=trace.selection.initial_trace.evaluate_trace) as initial:
                report=self.evaluate(p,log,candidate_manifest=manifest,
                    generated_probe=p['compiled_probe'].replace('\n','\r\n').encode(),
                    supplemental_commands={path:text.replace('\n','\r\n').encode() for path,text in p['supplemental_commands'].items()})
                self.assertTrue(report['passed'],report['failures']);self.assertTrue(report['ready_for_host_capture'])
                self.assertTrue(report['source_authenticated']);self.assertTrue(report['whole_candidate_bound'])
                self.assertTrue(report['candidate_manifest_bound']);self.assertTrue(report['all_supplemental_commands_bound'])
                self.assertEqual(len(report['source']['supplemental_commands']),3)
                self.assertEqual(initial.call_args.args,(log,p['initial_extra']))
                self.assertEqual(initial.call_args.kwargs,dict(resolution=resolution,candidate_sha256=p['candidate_sha256'],
                    stage=p['stage'],candidate_manifest=manifest,original=base_fixture.ORIGINAL))
                for key in ('sequence_only','initial_log_projected','snapshot_headers_verified','snapshot_units_verified',
                            'runtime_accepted','pixels_verified','cleanup_verified','manual_input_proof','promotion_ready'):
                    self.assertFalse(report[key],key)

    def test_input_identity_types_and_recursive_structures_fail_before_rebuild(self):
        recursive={};recursive['self']=recursive
        class Alias(int):pass
        with synthetic_binding(self.packet,self.manifest) as (builder,context):
            for key,value in (('original',base_fixture.ORIGINAL+b'x'),('candidate',base_fixture.CANDIDATE+b'x'),
                ('save',base_fixture.SAVE+b'x'),('original',bytearray(base_fixture.ORIGINAL)),('candidate','text'),
                ('generated_probe',bytearray(b'x')),('candidate_manifest',self.manifest|{'invalid':recursive}),
                ('candidate_manifest',self.manifest|{'invalid':Alias(1)})):
                result=self.evaluate(**{key:value})
                self.assertFalse(result['passed']);self.assertFalse(result['source_authenticated'])
            builder.assert_not_called();context.assert_not_called()

    def test_exact_main_and_every_supplemental_command_missing_changed_and_extra_reject(self):
        p=self.packet
        with synthetic_binding(p,self.manifest):
            for extra in (b'\n',b'\r',b'gc\n',b'\xef\xbb\xbf'):
                self.assertFalse(self.evaluate(generated_probe=p['compiled_probe'].encode()+extra)['passed'])
                for path in p['supplemental_commands']:
                    commands={k:v.encode() for k,v in p['supplemental_commands'].items()};commands[path]+=extra
                    self.assertFalse(self.evaluate(supplemental_commands=commands)['passed'])
            for path in p['supplemental_commands']:
                commands={k:v.encode() for k,v in p['supplemental_commands'].items()};del commands[path]
                self.assertFalse(self.evaluate(supplemental_commands=commands)['passed'])
            commands={k:v.encode() for k,v in p['supplemental_commands'].items()};commands['C:/extra.cdb']=b'gc\n'
            self.assertFalse(self.evaluate(supplemental_commands=commands)['passed'])
            changed=copy.deepcopy(p);changed['source_sha256']['unexpected']='f'*64
            self.assertFalse(self.evaluate(changed)['passed'])
            for value in (1024.0,True):
                manifest=copy.deepcopy(self.manifest);manifest['geometry']['width']=value
                changed=p|{'candidate_manifest_canonical_sha256':trace.sha(trace.canonical(manifest).encode())}
                self.assertFalse(self.evaluate(changed,candidate_manifest=manifest)['passed'])

    def test_initial_failures_are_retained_without_stage_or_namespace_projection(self):
        p=self.packet;baseline=log_fixture(p)
        with synthetic_binding(p,self.manifest):
            for old,new in (('PTILE_EVENT seq=4','PTILE_EVENT seq=3'),
                ('PTILE_STATUS hook=full_present status=1','PTILE_STATUS hook=full_present status=0'),
                ('PTILE_INITIAL_RETURN','PTILE_UNKNOWN')):
                self.assertIn(old,baseline);report=self.evaluate(log=baseline.replace(old,new))
                self.assertTrue(report['movement_sequence']['passed'])
                self.assertFalse(report['initial_map_trace']['passed']);self.assertFalse(report['ready_for_host_capture'])
            failed=self.evaluate(log=mutate(baseline,'xy-occupancy-commit','xy','(16,19)'))
            self.assertFalse(failed['movement_sequence']['passed']);self.assertTrue(failed['initial_map_trace']['passed'])
            for marker in ('ARMY_CONTRACT_PASS','COMPLETEHD_CONTRACT_PASS','PTILE_CONTRACT_PASS'):
                line=next(line for line in baseline.splitlines() if line.startswith(marker))
                report=self.evaluate(log=baseline.replace(line,''))
                self.assertFalse(report['passed']);self.assertFalse(report['initial_map_trace']['passed'])

    def test_producer_helper_and_mid_verification_source_drift_reject(self):
        with synthetic_binding(self.packet,self.manifest):
            with patch.object(trace,'PRODUCER_SHA256','0'*64):
                self.assertFalse(self.evaluate()['source_authenticated'])
            with patch.dict(trace.HELPERS,{'tools/framed_army_movement_state.py':'0'*64}):
                self.assertFalse(self.evaluate()['passed'])
            real=trace.source_receipts()
            with patch.object(trace,'source_receipts',side_effect=[real,real|{'changed':'0'*64}]):
                report=self.evaluate();self.assertFalse(report['passed']);self.assertFalse(report['source_authenticated'])


REAL_ORIGINAL=Path('C:/Clash/clash95.exe')
REAL_SAVE=Path('C:/Clash/save/0.dat')


@unittest.skipUnless(REAL_ORIGINAL.is_file() and REAL_SAVE.is_file(),'read-only original/save unavailable')
class RealBoundTests(unittest.TestCase):
    def test_actual_1024_reconstruction_and_native_state_with_synthetic_observations(self):
        original,save=REAL_ORIGINAL.read_bytes(),REAL_SAVE.read_bytes()
        candidate,manifest,_=trace.producer.base.builder.build_candidate(original,'1024x768')
        manifest=json.loads(json.dumps(manifest))
        packet=trace.producer.build_movement_probe(original,candidate,save,
            capture_dir='C:/ClashCaptures/offline-complete-movement-bound-fixture',candidate_manifest=manifest,resolution='1024x768')
        record=save[16+149349:16+149349+725];log=log_fixture(packet,source_record=record)
        args=dict(original=original,candidate=candidate,save=save,candidate_manifest=manifest,
            generated_probe=packet['compiled_probe'].replace('\n','\r\n').encode(),
            supplemental_commands={p:t.replace('\n','\r\n').encode() for p,t in packet['supplemental_commands'].items()})
        readiness=trace.evaluate_bound_trace(log,packet,**args)
        self.assertTrue(readiness['passed'],readiness['failures']);self.assertTrue(readiness['initial_map_trace']['passed'])
        self.assertTrue(readiness['source_authenticated']);self.assertTrue(readiness['ready_for_host_capture'])
        headers=headers_fixture(packet);units=unit_fixture(packet,record)
        # Reuse this exact successful binding only for focused artifact tests.
        # Header/unit decoders and the real original/save state comparator stay
        # active; these synthetic records are never written as runtime evidence.
        with patch.object(trace,'evaluate_bound_trace',side_effect=lambda *a,**k:copy.deepcopy(readiness)):
            def capture(**changes):
                return trace.evaluate_bound_capture(log,packet,**args,**(dict(snapshot_headers=headers,snapshot_units=units)|changes))
            report=capture();self.assertTrue(report['passed'],report['failures'])
            self.assertTrue(report['snapshot_headers_verified']);self.assertTrue(report['snapshot_units_verified'])
            self.assertTrue(report['movement_state']['passed']);self.assertEqual(len(report['source']['snapshot_units']),3)
            for key in ('runtime_accepted','pixels_verified','cleanup_verified','manual_input_proof','promotion_ready'):
                self.assertFalse(report[key],key)
            for field in ('snapshot_headers','snapshot_units'):
                for value in ({},None):self.assertFalse(capture(**{field:value})['passed'])
            class MappingAlias(dict):pass
            class KeyAlias(str):pass
            for field,values in (('snapshot_headers',headers),('snapshot_units',units)):
                self.assertFalse(capture(**{field:MappingAlias(values)})['passed'])
                self.assertFalse(capture(**{field:{KeyAlias(k):v for k,v in values.items()}})['passed'])
            for path,raw in headers.items():
                for offset,value,fmt in ((0,800,'H'),(2,600,'H'),(4,BASE+4,'I'),(184,0x50EE74,'I')):
                    changed=bytearray(raw);struct.pack_into('<'+fmt,changed,offset,value)
                    self.assertFalse(capture(snapshot_headers=headers|{path:bytes(changed)})['passed'])
                self.assertFalse(capture(snapshot_headers=headers|{path:raw[:-1]})['passed'])
            for path,raw in units.items():
                for offset in (0,4,6,14,15,316,320):
                    changed=bytearray(raw);changed[offset]^=1
                    self.assertFalse(capture(snapshot_units=units|{path:bytes(changed)})['passed'])
                self.assertFalse(capture(snapshot_units=units|{path:raw[:-1]})['passed'])
            receipts=trace.source_receipts()
            with patch.object(trace,'source_receipts',return_value=receipts|{'changed':'0'*64}):
                drifted=capture();self.assertFalse(drifted['passed']);self.assertFalse(drifted['source_authenticated'])
        for key in ('original','candidate','save'):
            changed=dict(args);data=bytearray(changed[key]);data[-1]^=1;changed[key]=bytes(data)
            self.assertFalse(trace.evaluate_bound_trace(log,packet,**changed)['source_authenticated'])


if __name__=='__main__':
    unittest.main(verbosity=2)
