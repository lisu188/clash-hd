"""Offline synthetic trace adversaries and one exact real-schema binding.

Synthetic markers are fixtures, never saved as runtime evidence. Game/CDB,
input, screenshots and report-writing harnesses are not executed.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import framed_army_selection_trace as trace
import test_initial_map_paint_trace as initial_fixture

TID=0xABC
SP=0x100100
SURFACE=0x900000
BASE=0xA00000
SHA='a'*64


def packet_fixture():
    _,extra=initial_fixture.fixture(resolution='1024x768',stage=trace.initial_trace.FRAMED_STAGE)
    extra=extra.replace('stage='+trace.initial_trace.FRAMED_STAGE+' ','stage='+trace.producer.builder.STAGE+' ')
    packet=dict(schema='clash95_framed_army_selection_probe_v1',revision=trace.producer.REVISION,
        stage=trace.producer.builder.STAGE,resolution='1024x768',width=1024,height=768,unit=3,
        unit_xy=[16,19],unit_squad_types=[16,16,1,1,1,1,1,1],save_sha256=trace.producer.SAVE_SHA256,
        original_sha256=trace.producer.clip.ORIGINAL_SHA256,candidate_sha256=SHA,
        controlled_scroll=[10,17],controlled_mouse=[448,176],native_predicate_forced=False,
        capture_dir='C:/ClashCaptures/offline-army-parser-fixture',minimap_viewport=True,
        native_call_returns=dict(portraits=0x423B32,redraw=0x423B3C,native_draw=0x597800,composition_draw=0x597A00),
        observer_vas={'91':0x597800,'92':0x597A00},initial_extra=extra,
        initial_extra_sha256=trace.sha(extra.encode()),compiled_probe='synthetic nonexecuted fixture\n',
        probe_sha256=trace.sha(b'synthetic nonexecuted fixture\n'),
        manual_input_proof=False,promotion_ready=False,runtime_executed=False)
    return packet


def log_fixture(packet=None,*,warmup=0,compositions=1):
    p=packet or packet_fixture()
    sites={int(n):int(va,16) for n,va in re.findall(r'(?m)^bp(7[0-7]) ([0-9a-fA-F]{8}) ',p['initial_extra'])}
    events=initial_fixture.initial_events('1024x768',framed=True)
    lines=['SHSEL_BYTES_PASS',
        f"ARMY_CONTRACT_PASS stage={p['stage']} resolution=1024x768 candidate_sha256={p['candidate_sha256']} revision={trace.producer.builder.REVISION}",
        'ARMY_SCOPE own_player_0_to_3_native_size_panel manual_input_proof=false promotion_ready=false',
        f"PTILE_CONTRACT_PASS stage={p['stage']} resolution=1024x768 candidate_sha256={p['candidate_sha256']}",
        'PTILE_SCOPE guarded_map_only manual_input_proof=false promotion_ready=false']
    for i,e in enumerate(events,1):
        lines.append(f"PTILE_EVENT seq={i} bp={e['bp']} tid={TID:x} eip={sites[e['bp']]:08x} esp={e['esp']:08x}")
        lines.extend(e['records'])
    lines += [f'PTILE_TRACE_CLOSED tid={TID:x} eip=00406fa0 esp={SP:08x}']
    if not p['revision'].endswith('_v1'):
        lines += ['SHSEL_HANDOFF eip=00406fa0 t14=1 t13=4 gd=00600000 owner=0040ad40 lower=0 post=0 player=(0,0) selected=(ffffffffffffffff,-1) prior=(ffffffffffffffff,-1)',
                  'SHSEL_HANDOFF_CHECKS eip=1 t14=1 t13=1 owner=1 lower=1 post=1 player=1 selected=1 prior=1',
                  'SHSEL_WORLD_CHECKS width=1 height=1 scroll_y=1 unit_xy=1 unit_owner=1']
    lines += [f'SHSEL_BEGIN tid={TID:x} eip=00406fa0 esp={SP:08x} old_scroll=(10,17) selected=-1 prior=-1',
        'SHSEL_CONTROLLED scroll=(10,17) screen=(448,176) unit=3 world=(16,19) predicate_forced=0 native_entry=00408030 updater=00406980',
        'SHSEL_OCCUPANCY world=(16,19) unit=3 selected_before=-1 player=0',
        f'SHSEL_SELECTION_WRITE selected=3 eax=1 tid={TID:x} esp={SP-24:08x}',
        'SHSEL_UPDATER selected=3 prior=-1 lower=0 caller=00406fa1',
        'SHSEL_PANEL_UPDATE selected=3 prior=-1 lower=0',
        'SHSEL_ARMY_OPEN selected=3 prior=-1 lower=0',
        'SHSEL_ARMY_DRAW selected=3 prior=3 lower=1',
        f"SHSEL_DRAW_ENTRY tid={TID:x} esp=000ff000 caller={p['native_call_returns']['native_draw']:08x} count=1 font7_cache=00000000",
        f'SHSEL_DRAW_RETURN route=native tid={TID:x} esp=000ff004 status={warmup} count=1',
        f'SHSEL_PAIRED event=before-redraw selected=3 prior=3 lower=1 surface={SURFACE:08x} base={BASE:08x} size=(1024,768)']
    for i in range(compositions):
        lines += [f"SHSEL_DRAW_ENTRY tid={TID:x} esp=000fe000 caller={p['native_call_returns']['composition_draw']:08x} count={i+2} font7_cache=00b00000",
                  f'SHSEL_DRAW_RETURN route=composition tid={TID:x} esp=000fe004 status=1 count={i+2}']
    lines += [f'SHSEL_PAIRED event=after-redraw selected=3 prior=3 lower=1 surface={SURFACE:08x} base={BASE:08x} size=(1024,768)',
        f'SHSEL_READY tid={TID:x} eip=00406fa1 esp={SP:08x} selected=3 prior=3 lower=1 owner=0040ad40 surface={SURFACE:08x} base={BASE:08x} width=1024 height=768 vtable=0050ee24',
        'SHSEL_HOST_READY']
    return '\n'.join(lines)+'\n'


class SequenceTests(unittest.TestCase):
    def bad(self,log,packet=None):
        result=trace.evaluate_trace(log,packet or packet_fixture())
        self.assertFalse(result['passed'],result)
        self.assertFalse(result['ready_for_host_capture']);self.assertTrue(result['failures'])
        return result

    def test_native_zero_is_disclosed_only_composition_one_proves_logged_draw(self):
        for native in (0,1):
            for count in (1,3):
                report=trace.evaluate_trace(log_fixture(warmup=native,compositions=count),packet_fixture())
                self.assertTrue(report['passed'],report['failures'])
                seq=report['selection_sequence']
                self.assertEqual(seq['native_warmup_fallbacks'],int(native==0))
                self.assertEqual(seq['native_relocated_draw_observed'],native==1)
                self.assertTrue(seq['composition_draw_observed'])
                self.assertEqual(seq['counters'],dict(entries=count+1,returns=count+1,native=1,composition=count))
                for key in ('source_authenticated','whole_candidate_bound','ready_for_host_capture','pixels_verified','cleanup_verified','manual_input_proof','promotion_ready'):
                    self.assertFalse(report[key],key)

    def test_every_required_record_missing_repeated_or_reordered_fails(self):
        lines=log_fixture().splitlines()
        for i,line in enumerate(lines):
            if not line.startswith(('SHSEL_','ARMY_')):continue
            with self.subTest(missing=line):self.bad('\n'.join(lines[:i]+lines[i+1:]))
            with self.subTest(duplicate=line):self.bad('\n'.join(lines[:i]+[line]+lines[i:]))
        for a,b in (('SHSEL_ARMY_OPEN','SHSEL_ARMY_DRAW'),('SHSEL_DRAW_RETURN route=native','SHSEL_PAIRED event=before-redraw'),
                    ('SHSEL_PAIRED event=after-redraw','SHSEL_READY')):
            changed=lines.copy();i=next(n for n,t in enumerate(changed) if t.startswith(a));j=next(n for n,t in enumerate(changed) if t.startswith(b))
            changed[i],changed[j]=changed[j],changed[i];self.bad('\n'.join(changed))

    def test_native_pairs_counters_stack_status_and_thread_are_strict(self):
        log=log_fixture()
        for old,new in (('count=1','count=0'),('count=2','count=3'),('esp=000fe004','esp=000fe000'),
                        ('esp=000ff004','esp=000ff008'),('route=composition tid=abc','route=composition tid=abd'),
                        ('esp=000fe000','esp=000fe001'),('caller=00597a00','caller=00597800'),
                        ('status=0 count=1','status=2 count=1'),('status=1 count=2','status=0 count=2')):
            with self.subTest(change=(old,new)):self.bad(log.replace(old,new))
        self.bad(log_fixture(compositions=0))
        rows=log.splitlines();entry=next(t for t in rows if t.startswith('SHSEL_DRAW_ENTRY') and 'count=2' in t)
        self.bad(log.replace(entry,entry+'\n'+entry.replace('count=2','count=3')))

    def test_state_geometry_stale_marker_and_runtime_failures_preserved(self):
        log=log_fixture()
        for old,new in (('world=(16,19)','world=(16,18)'),('selected_before=-1','selected_before=3'),
                        ('eax=1','eax=0'),('caller=00406fa1','caller=00406fa0'),
                        ('eip=00406fa1','eip=00406fa0'),('vtable=0050ee24','vtable=0050ee74'),
                        ('owner=0040ad40','owner=00422020'),('width=1024','width=800'),
                        ('base=00a00000 width','base=00a01000 width'),('surface=00900000','surface=0051d4c0'),
                        ('prior=3 lower=1','prior=2 lower=1'),('SHSEL_BEGIN','shsel_begin'),
                        ('status=0 count=1','status=0 count=1 extra=1')):
            with self.subTest(change=(old,new)):self.bad(log.replace(old,new))
        for tail in ('SHSEL_REJECT native_contract','SHSEL_SELECTION_FAIL selected=-1 eax=0',
                     'AV_SURFDUMP c0000005','access violation','Syntax error','timeout reached',
                     'SURFDUMP_APP_REQUEST_QUIT','SURFDUMP_REDRAW tick=999','PTILE_REJECT offscreen',
                     'SHSEL_UNKNOWN value=1','0:000> SHSEL_HOST_READY'):
            self.bad(log+tail+'\n')
        failed=log.split('SHSEL_BEGIN')[0]+'SHSEL_REJECT native_contract\n'
        report=self.bad(failed)
        self.assertTrue(report['initial_map_trace']['passed'])
        self.assertIsNone(report['surface'])

    def test_exact_stage_projection_keeps_sha_and_every_other_raw_line(self):
        packet=packet_fixture();log=log_fixture(packet)
        report=trace.evaluate_trace(log,packet);self.assertTrue(report['passed'],report['failures'])
        projected,extra,binding=trace._project(log,packet['initial_extra'],packet)
        before=log.splitlines();after=projected.splitlines()
        self.assertEqual([i for i,(a,b) in enumerate(zip(before,after)) if a!=b],[3])
        self.assertIn(packet['candidate_sha256'],after[3])
        self.assertEqual(binding['log']['original_sha256'],trace.sha(log.encode()))
        self.bad(log.replace('PTILE_EVENT seq=4','PTILE_EVENT seq=3'))
        self.bad(log.replace('PTILE_STATUS hook=full_present status=1','PTILE_STATUS hook=full_present status=0'))
        self.bad(log.replace('PTILE_INITIAL_RETURN','PTILE_UNKNOWN'))
        self.bad(log.replace('stage='+packet['stage'],'stage='+trace.initial_trace.FRAMED_STAGE))
        self.bad(log.replace(packet['candidate_sha256'],'b'*64))

    def test_packet_hashes_profiles_malformed_and_partial_inputs_fail(self):
        log=log_fixture();packet=packet_fixture()
        for field,value in (('stage','stale'),('revision','unknown'),('resolution','800x600'),
                            ('unit',1),('unit_xy',[15,22]),('native_predicate_forced',True),
                            ('manual_input_proof',True),('compiled_probe','mutated'),('initial_extra','mutated'),
                            ('save_sha256','b'*64),('minimap_viewport',None),('native_call_returns',[]),('observer_vas',None)):
            changed=copy.deepcopy(packet);changed[field]=value;self.bad(log,changed)
        self.assertFalse(trace.evaluate_trace(log,None)['passed'])

    def test_diagnostic_checks_never_replace_sequence_and_v1_failure_is_retained(self):
        p=packet_fixture();log=log_fixture(p)
        for old,new in (('selected=1 prior=1','selected=0 prior=1'),('unit_xy=1','unit_xy=0'),
                        ('t14=1 t13=4','t14=0 t13=4'),('gd=00600000','gd=00000000'),
                        ('selected=(ffffffffffffffff,-1)','selected=(ffffffffffffffff,3)')):
            self.bad(log.replace(old,new),p)
        failed=log.split('SHSEL_WORLD_CHECKS')[0]+'SHSEL_REJECT native_contract\n'
        report=self.bad(failed,p)
        self.assertEqual(len(report['selection_sequence']['handoff_diagnostics']),2)
        old=copy.deepcopy(p);old['revision']='controlled_own_army_native_selection_v1'
        oldlog=log_fixture(old)
        self.assertTrue(trace.evaluate_trace(oldlog,old)['passed'])
        oldfailure=oldlog.split('SHSEL_BEGIN')[0]+'SHSEL_REJECT native_contract\n'
        report=self.bad(oldfailure,old)
        self.assertTrue(report['initial_map_trace']['passed'])
        self.assertEqual(report['selection_sequence']['handoff_diagnostics'],[])


ORIGINAL=Path('C:/Clash/clash95.exe')
SAVE=Path('C:/Clash/save/0.dat')
CANDIDATE=Path('C:/ClashTests/hd-completion/framed-army-v1-1024x768-build-20260906-085300/clash95_army_1024x768_v1.exe')


@unittest.skipUnless(all(p.is_file() for p in (ORIGINAL,SAVE,CANDIDATE)),'requires original/save/candidate for read-only reconstruction')
class BoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL.read_bytes();cls.save=SAVE.read_bytes();cls.candidate=CANDIDATE.read_bytes()
        cls.packet=trace.producer.build_selection_probe(cls.original,cls.candidate,cls.save,
                       capture_dir='C:/ClashCaptures/offline-army-parser-fixture',minimap_viewport=True)
        cls.log=log_fixture(cls.packet)

    def test_full_reconstruction_real_schema_and_canonical_crlf_probe(self):
        report=trace.evaluate_bound_trace(self.log,self.packet,original=self.original,candidate=self.candidate,save=self.save,
                         generated_probe=self.packet['compiled_probe'].replace('\n','\r\n').encode('ascii'))
        self.assertTrue(report['passed'],report['failures'])
        self.assertTrue(report['source_authenticated']);self.assertTrue(report['whole_candidate_bound'])
        self.assertTrue(report['ready_for_host_capture'])
        self.assertFalse(report['pixels_verified']);self.assertFalse(report['cleanup_verified'])

    def test_full_binding_rejects_changed_probe_packet_candidate_save_and_producer(self):
        args=dict(original=self.original,candidate=self.candidate,save=self.save,
                  generated_probe=self.packet['compiled_probe'].encode('ascii'))
        # Mutated game/save bytes fail the authentic producer, not a fixture stub.
        for key in ('candidate','save'):
            changed=dict(args);data=bytearray(changed[key]);data[-1]^=1;changed[key]=bytes(data)
            report=trace.evaluate_bound_trace(self.log,self.packet,**changed)
            self.assertFalse(report['passed']);self.assertFalse(report['whole_candidate_bound'])
        # Memoize only an already fully reconstructed packet while checking the
        # separate exact packet/probe equality boundary; do not alter parsers.
        with patch.object(trace.producer,'build_selection_probe',return_value=self.packet):
            bad=copy.deepcopy(self.packet);bad['capture_dir']='C:/ClashCaptures/stale-packet'
            for packet,kwargs in ((bad,args),(self.packet,args|{'generated_probe':args['generated_probe']+b'gc\n'})):
                report=trace.evaluate_bound_trace(self.log,packet,**kwargs)
                self.assertFalse(report['passed']);self.assertIsNone(report['initial_projection'])
        with patch.object(trace,'PRODUCER_SHA256','0'*64):
            report=trace.evaluate_bound_trace(self.log,self.packet,**args)
            self.assertFalse(report['passed']);self.assertIn('producer source',report['failures'][0])


if __name__=='__main__':unittest.main()
