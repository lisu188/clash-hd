"""Adversarial ordered/source-bound fixtures; no runtime or game-file output."""
from __future__ import annotations

import copy
import re
import unittest
from unittest.mock import patch

import framed_battle_initial_probe as producer
import framed_battle_initial_trace as trace
import test_framed_battle_initial_probe as command_fixture
import test_initial_map_paint_trace as initial_fixture


def small_packet(resolution='800x600'):
    return dict(stage=producer.STAGE,resolution=resolution,route=producer.ROUTE,
        protocol_revision=producer.PROTOCOL,candidate_sha256='a'*64,
        save_sha256=producer.SAVE_SHA256,canvas_state_va=command_fixture.STATE)


def log_fixture(packet,extra=None):
    resolution=packet['resolution'];w,h=map(int,resolution.split('x'))
    events=initial_fixture.initial_events(resolution,framed=True)
    for row in events:
        row['tid']=0x2345
        row['records']=[x.replace('tid=abc','tid=2345') for x in row['records']]
    initial,_=initial_fixture.fixture(events,resolution=resolution,stage=producer.STAGE,close='')
    initial=initial.replace(initial_fixture.SHA,packet['candidate_sha256'])
    if extra:
        for bp,va in re.findall(r'^bp\s*(\d+)\s+([0-9a-f]{8}) ',extra,re.M|re.I):
            initial=initial.replace(f'eip={initial_fixture.SITES[int(bp)]:08x}',f'eip={int(va,16):08x}')
    rows=initial.splitlines()
    observations=command_fixture.advance(w,h,packet['canvas_state_va'])[3]
    loaded=(f"MCANVAS_CONTRACT_PASS stage={producer.STAGE} resolution={resolution} "
        f"candidate_sha256={packet['candidate_sha256']} revision={producer.builder.REVISION} "
        f"state={packet['canvas_state_va']:08x} state_bytes=4096")
    contract=(f"BINIT_CONTRACT stage={producer.STAGE} resolution={resolution} candidate_sha256={packet['candidate_sha256']} "
              f"save_sha256={producer.SAVE_SHA256} route={producer.ROUTE} protocol={producer.PROTOCOL} runtime_acceptance=0")
    return '\n'.join([
        f"BINIT_BYTE_CONTRACT_PASS candidate_sha256={packet['candidate_sha256']} route={producer.ROUTE}",
        loaded,'MCANVAS_SCOPE owned_castle_canvas_only manual_input_proof=false promotion_ready=false',
        *rows[:2],contract,*rows[2:],
        f'SURFDUMP_READY redraw_seq=4 surface=20000000 size=({w},{h}) base=21000000 bytes={w*h}',
        *observations])+'\n'


class Sequence(unittest.TestCase):
    def bad(self,log,packet):
        result=trace.evaluate_sequence(log,packet)
        self.assertFalse(result['sequence_passed'],result)
        self.assertFalse(result['ready_for_host_capture'])
        self.assertTrue(result['failures'])
        return result

    def test_six_literal_frame_geometries_and_disclosed_mutation(self):
        for resolution in command_fixture.RESOLUTIONS:
            packet=small_packet(resolution);result=trace.evaluate_sequence(log_fixture(packet),packet)
            self.assertTrue(result['sequence_passed'],result['failures'])
            self.assertEqual(result['surface']['surface'],0x20000000)
            self.assertEqual(result['surface']['base'],0x21000000)
            self.assertEqual(result['surface']['eip'],0x42f2fa)
            self.assertEqual(result['mutation']['old_xy'],0x0016000e)
            self.assertEqual(result['mutation']['old_flag'],0)
            self.assertFalse(result['ready_for_host_capture'])

    def test_every_battle_row_missing_repeated_wrong_order_and_truncation_fails(self):
        packet=small_packet();log=log_fixture(packet)
        rows=[x for x in log.splitlines() if x.startswith('BINIT_')]
        for row in rows:
            for replacement in ('',row+'\n'+row,row[:-1]):
                with self.subTest(row=row.split()[0],replacement=replacement[:50]):
                    result=self.bad(log.replace(row,replacement,1),packet)
                    if replacement==row+'\n'+row:
                        self.assertGreaterEqual(sum(x['text']==row for x in result['raw_records']),2)
        for left,right in zip(rows,rows[1:]):
            mutated=log.replace(left,'TEMP_TOKEN',1).replace(right,left,1).replace('TEMP_TOKEN',right)
            self.bad(mutated,packet)

    def test_every_observer_native_identity_and_inactive_state_fails_if_changed(self):
        packet=small_packet();log=log_fixture(packet)
        for row in log.splitlines():
            if row.startswith('BINIT_') and ' tid=' in row:
                for key in ('tid','eip','esp'):
                    old=re.search(key+r'=([a-f0-9]+)',row).group(1)
                    self.bad(log.replace(row,row.replace(key+'='+old,key+'='+f'{int(old,16)+4:08x}',1),1),packet)
                if 'state=' in row:
                    self.bad(log.replace(row,row.replace('state=00596000','state=00596004'),1),packet)
        self.bad(log.replace('checked_bytes=128','checked_bytes=124'),packet)
        self.bad(log.replace('all_zero=1','all_zero=0'),packet)

    def test_actor_write_call_gate_and_resource_bindings_are_required(self):
        packet=small_packet();log=log_fixture(packet)
        replacements=[('old_attacker_xy=(14,22)','old_attacker_xy=(89,9)'),
            ('first_types=(5,5)','first_types=(8,5)'),('squad_counts=(1,1)','squad_counts=(0,1)'),
            ('attacker=10023ee6','attacker=10023eea'),('defender=10024a3a','defender=10024a3e'),
            ('old_xy=16000e','old_xy=90059'),('new_xy=00090059','new_xy=0009005a'),
            ('xy=90059 flag=1','xy=90059 flag=0'),('eax=1 attacker=','eax=0 attacker='),
            ('ecx=1 flag=1','ecx=0 flag=1'),('ebx=0 ecx=0 argument=0','ebx=1 ecx=0 argument=0'),
            ('caller=0041b14a','caller=0041b145'),('argument=0','argument=1'),
            ('battle=22000000','battle=00000000'),('owner=0042e8b0','owner=0040ad40'),
            ('player=0 selected=0','player=5 selected=0'),('selected=0 selected_type=','selected=22 selected_type='),
            ('selected_type=5','selected_type=41'),
            ('resources=(23000000,','resources=(00000000,'),('caller=0042f2fa cursor=00544cd8','caller=0042f2f5 cursor=00544cd8')]
        for old,new in replacements:
            with self.subTest(old=old):
                self.assertIn(old,log);self.bad(log.replace(old,new),packet)

    def test_capture_mismatch_overflow_wrong_stage_save_and_any_late_rejection(self):
        packet=small_packet();log=log_fixture(packet)
        row=next(x for x in log.splitlines() if x.startswith('BINIT_SURFDUMP_READY'))
        for old,new in [('surface=20000000','surface=0051d4c0'),('base=21000000','base=fffffff0'),
                        ('base=21000000','base=21000004'),('size=(800,600)','size=(1024,768)'),
                        ('bytes=480000','bytes=307200'),('vtable=0050ee24','vtable=0050eec4'),
                        ('capture=physical_battle_e0','capture=owned_physical_mirror')]:
            self.bad(log.replace(row,row.replace(old,new)),packet)
        for key,value in [('stage',producer.builder.BASE_STAGE),('route','battle_results'),
                          ('candidate_sha256','b'*64),('save_sha256','c'*64),('protocol_revision','unknown')]:
            bad=copy.deepcopy(packet);bad[key]=value;self.bad(log,bad)
        for tail in ('BINIT_REJECT reason=unexpected_attack_return','BINIT_NEW_OBSERVATION x=1',
                     'bInIt_SURFDUMP_HOST_READY','prefix BINIT_SURFDUMP_HOST_READY',
                     'MCAP_SURFDUMP_HOST_READY','SURFDUMP_HOST_READY','Syntax error',
                     'AV_SURFDUMP code=c0000005','SURFDUMP_APP_REQUEST_QUIT x=1',
                     'SURFDUMP_REDRAW seq=5','MCANVAS_CONTRACT_FAIL'):
            self.bad(log+tail+'\n',packet)

    def test_initial_closure_and_loaded_byte_contract_order_cannot_be_bypassed(self):
        packet=small_packet();log=log_fixture(packet)
        for row in log.splitlines():
            if row.startswith(('MCANVAS_','PTILE_TRACE_CLOSED')):
                self.bad(log.replace(row,''),packet)
                self.bad(log+row+'\n',packet)
        self.bad(log.replace('PTILE_TRACE_CLOSED tid=2345','PTILE_TRACE_CLOSED tid=2346'),packet)
        contract=next(x for x in log.splitlines() if x.startswith('BINIT_CONTRACT'))
        self.bad(log.replace(contract,'')+contract+'\n',packet)


class FullBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=command_fixture.ORIGINAL.read_bytes();cls.save=command_fixture.SAVE.read_bytes()
        cls.candidate,cls.metadata,cls.extra,_=producer.canonical_template(cls.original,'1024x768',minimap_viewport=True)
        cls.packet=producer.build_probe(cls.original,cls.candidate,cls.save,candidate_sha256=producer.sha(cls.candidate),
            stage=producer.STAGE,resolution='1024x768',route=producer.ROUTE,minimap_viewport=True)
        cls.compiled=trace.compile_probe(cls.packet);cls.log=log_fixture(cls.packet,cls.extra)

    def evaluate(self,**changes):
        args=dict(log=self.log,original=self.original,candidate=self.candidate,save=self.save,
            packet=self.packet,generated_probe=self.compiled.encode('ascii'));args.update(changes)
        return trace.evaluate_trace(**args)

    def test_exact_actual_candidate_complete_source_binding_and_projection(self):
        result=self.evaluate();self.assertTrue(result['passed'],result['failures'])
        self.assertTrue(result['ready_for_host_capture'])
        self.assertTrue(result['initial_map_trace']['passed'])
        self.assertEqual(result['source']['save_sha256'],producer.SAVE_SHA256)
        self.assertFalse(result['runtime_accepted']);self.assertFalse(result['cleanup_verified'])
        self.assertFalse(result['manual_input_proof']);self.assertFalse(result['promotion_ready'])
        crlf=self.evaluate(generated_probe=self.compiled.replace('\n','\r\n').encode('ascii'))
        self.assertTrue(crlf['passed'],crlf['failures'])
        self.assertNotEqual(crlf['source']['generated_probe_sha256'],result['source']['generated_probe_sha256'])
        self.assertEqual(crlf['source']['generated_probe_canonical_lf_sha256'],result['source']['generated_probe_canonical_lf_sha256'])

    def test_mutated_packet_probe_save_and_candidate_never_reach_projection(self):
        bad=copy.deepcopy(self.packet);bad['host_read_contract']['state_all_zero']=False
        mutations=[dict(packet=bad),dict(generated_probe=self.compiled.replace('BINIT_SURFDUMP_HOST_READY','BINIT_FAKE').encode()),
            dict(candidate=self.candidate[:-1]+b'X'),dict(save=self.save[:-1]+b'X'),dict(packet={})]
        for kwargs in mutations:
            with patch.object(producer.compiler,'_project_initial',side_effect=AssertionError('projection before whole binding')):
                result=self.evaluate(**kwargs)
                self.assertFalse(result['passed']);self.assertIsNone(result['initial_map_projection'])

    def test_duplicate_initial_event_and_late_failed_marker_remain_failed(self):
        row=next(x for x in self.log.splitlines() if x.startswith('PTILE_EVENT'))
        result=self.evaluate(log=self.log.replace(row,row+'\n'+row,1))
        self.assertFalse(result['passed']);self.assertFalse(result['initial_map_trace']['passed'])
        result=self.evaluate(log=self.log+'BINIT_REJECT reason=late_failure\n')
        self.assertFalse(result['passed'])
        self.assertTrue(any('BINIT_REJECT' in r['text'] for r in result['battle_sequence']['raw_records']))


if __name__=='__main__':unittest.main()
