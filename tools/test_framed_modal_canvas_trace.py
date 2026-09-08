"""Ordered owned-canvas protocol and whole-image fixtures; no game/debugger."""
from dataclasses import asdict
import copy
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import framed_modal_canvas_probe as producer
import framed_modal_canvas_trace as trace
import test_framed_modal_canvas_probe as command_fixture
import test_initial_map_paint_trace as initial_fixture


def small_packet(route='school',availability='existing_flags'):
    return dict(stage=producer.STAGE,resolution='800x600',candidate_sha256='a'*64,
                protocol_revision=producer.PROTOCOL_REVISION,
                route=asdict(producer.ROUTES[route]),availability=availability,castle_index=0,
                canvas_state_va=command_fixture.METADATA['state_va'],
                canvas_observer_vas=command_fixture.METADATA['modal_observer_vas'])


def log_fixture(packet,extra=None,variant=1):
    events=initial_fixture.initial_events(framed=True)
    for row in events:
        row['tid']=0x2345
        row['records']=[text.replace('tid=abc','tid=2345') for text in row['records']]
    initial,probe=initial_fixture.fixture(events,stage=producer.STAGE,close='')
    initial=initial.replace(initial_fixture.SHA,packet['candidate_sha256'])
    if extra:
        for bp,va in re.findall(r'^bp\s*(\d+)\s+([0-9a-f]{8}) ',extra,re.M|re.I):
            old=initial_fixture.SITES[int(bp)]
            initial=initial.replace(f'eip={old:08x}',f'eip={int(va,16):08x}')
    initial_lines=initial.splitlines()
    metadata=dict(state_va=packet['canvas_state_va'],modal_observer_vas=packet['canvas_observer_vas'])
    modal=command_fixture.CommandTests().advance(packet['route']['name'],packet['availability'],metadata=metadata,variant=variant)[3]
    loaded=(f"MCANVAS_CONTRACT_PASS stage={packet['stage']} resolution={packet['resolution']} "
            f"candidate_sha256={packet['candidate_sha256']} revision={producer.builder.REVISION} "
            f"state={packet['canvas_state_va']:08x} state_bytes=4096")
    contract=(f"MCAP_CONTRACT stage={packet['stage']} resolution={packet['resolution']} "
              f"candidate_sha256={packet['candidate_sha256']} route={packet['route']['name']} "
              f"availability={packet['availability']} castle_index=0 protocol={producer.PROTOCOL_REVISION} runtime_acceptance=0")
    return '\n'.join([
        f"MCAP_BYTE_CONTRACT_PASS candidate_sha256={packet['candidate_sha256']} route={packet['route']['name']}",
        loaded,'MCANVAS_SCOPE owned_castle_canvas_only manual_input_proof=false promotion_ready=false',
        *initial_lines[:2],contract,*initial_lines[2:],
        'SURFDUMP_READY redraw_seq=4 surface=20000000 size=(800,600) base=21000000 bytes=480000',
        'SCROLL_VISDUMP player=0 screen0=(32,16) map0=(10,17) rows=9 cols=12 tile=(64,64) vis_base=10022331 dump_start=100223b5 count=145',
        *modal])+'\n'


class SequenceTests(unittest.TestCase):
    def bad(self,log,packet):
        result=trace.evaluate_sequence(log,packet)
        self.assertFalse(result['sequence_passed'],result)
        self.assertFalse(result['ready_for_host_capture'])
        self.assertTrue(result['failures'])
        return result

    def test_seven_routes_and_explicit_availability_capture_physical_not_native(self):
        for route in producer.ROUTES:
            for availability in ('existing_flags','construct_all'):
                packet=small_packet(route,availability)
                with self.subTest(route=route,availability=availability):
                    r=trace.evaluate_sequence(log_fixture(packet),packet)
                    self.assertTrue(r['sequence_passed'],r['failures'])
                    self.assertEqual((r['surface']['surface'],r['surface']['base']),(0x20000000,0x21000000))
                    self.assertFalse(r['ready_for_host_capture'])

    def test_both_native_mode0_load_branches_are_complete_and_style_independent(self):
        for name in ('castle_overview','hospital'):
            for availability in ('existing_flags','construct_all'):
                for variant in (0,1,2,128,255):
                    packet=small_packet(name,availability)
                    with self.subTest(route=name,availability=availability,variant=variant):
                        log=log_fixture(packet,variant=variant)
                        self.assertIn('style=1',log)
                        result=trace.evaluate_sequence(log,packet)
                        self.assertTrue(result['sequence_passed'],result['failures'])
                        calls=[r for r in result['raw_records'] if r['marker']=='MCAP_CANVAS'
                               and r['values']['event']=='LOAD_CALL' and r['values']['mirrors']==0]
                        self.assertEqual([r['values']['caller'] for r in calls],
                            [0x4213C2,0x4214DC,0x42154A] if variant==1 else [0x4213C2,0x4214DC])

    def test_exact_second_third_pairs_entry_and_return_never_disappear_or_deduplicate(self):
        packet=small_packet('hospital','construct_all');log=log_fixture(packet)
        lines=log.splitlines()
        selected=[i for i,t in enumerate(lines) if t.startswith(('MCAP_ARTWORK_ENTRY','MCAP_ARTWORK_RETURN'))
                  or (t.startswith('MCAP_CANVAS') and any(x in t for x in
                      ('caller=004214dc','caller=0042154a','event=OVERVIEW_SECOND_LOAD_RETURN','event=OVERVIEW_THIRD_LOAD_RETURN')))]
        for index in selected:
            row=lines[index]
            with self.subTest(missing=index):self.bad('\n'.join(lines[:index]+lines[index+1:]),packet)
            with self.subTest(duplicate=index):
                result=self.bad('\n'.join(lines[:index]+[row]+lines[index:]),packet)
                self.assertEqual(sum(r['text']==row for r in result['raw_records']),2)
        changes=(('caller=004214dc','caller=004213c2'),('caller=0042154a','caller=004214dc'),
            ('eip=004214dc','eip=004213c2'),('eip=0042154a','eip=004214dc'),
            ('variant_byte=1','variant_byte=0'),('mode=0 mask=0','mode=1 mask=0'),
            ('mode=0 mask=0','mode=0 mask=1'),('target=23000000','target=22000000'),
            ('folder_player=0','folder_player=5'),('caller=00422043','caller=004220db'))
        for old,new in changes:
            self.assertIn(old,log)
            with self.subTest(change=new):self.bad(log.replace(old,new,1),packet)
        for marker in ('MCAP_ARTWORK_ENTRY','MCAP_ARTWORK_RETURN'):
            row=next(t for t in lines if t.startswith(marker));esp=re.search(r'\besp=([0-9a-f]+)',row)[1]
            self.bad(log.replace(row,row.replace('esp='+esp,'esp='+f'{int(esp,16)+4:08x}')),packet)
        old=log.replace(' protocol='+producer.PROTOCOL_REVISION,'')
        self.bad(old,packet)
        changed=copy.deepcopy(packet);changed['protocol_revision']='old_single_load';self.bad(log,changed)
        # This is the original erroneous one-load observation sequence, even if
        # someone prefixes its contract with the new revision. It stays failed.
        omit=('MCAP_ARTWORK_ENTRY','MCAP_ARTWORK_RETURN','event=OVERVIEW_SECOND_LOAD_RETURN',
              'event=OVERVIEW_THIRD_LOAD_RETURN','caller=004214dc','caller=0042154a')
        self.bad('\n'.join(t for t in lines if not any(x in t for x in omit)),packet)

    def test_every_missing_duplicated_or_swapped_modal_record_fails(self):
        packet=small_packet(availability='construct_all');lines=log_fixture(packet).splitlines()
        selected=[i for i,t in enumerate(lines) if t.startswith(('MCAP_','MCANVAS_'))]
        for i in selected:
            with self.subTest(missing=i):self.bad('\n'.join(lines[:i]+lines[i+1:]),packet)
            with self.subTest(duplicate=i):
                bad=lines.copy();bad.insert(i,lines[i]);result=self.bad('\n'.join(bad),packet)
                if lines[i].startswith('MCAP_'):
                    self.assertEqual(len(result['raw_records']),sum(t.startswith('MCAP_') for t in lines)+1)
        for a,b in zip(selected,selected[1:]):
            bad=lines.copy();bad[a],bad[b]=bad[b],bad[a]
            with self.subTest(swapped=(a,b)):self.bad('\n'.join(bad),packet)

    def test_canvas_ownership_identity_stack_and_native_call_mutations_fail(self):
        packet=small_packet();log=log_fixture(packet)
        rows=[t for t in log.splitlines() if t.startswith('MCAP_CANVAS')]
        changes=[('tid=2345','tid=2346'),('phase=1','phase=0'),('state=00596000','state=00596004'),
                 ('root_esp=00fffffc','root_esp=00fffff8'),('physical=20000000','physical=20000004'),
                 ('native=23000000','native=20000000'),('physical_pixels=21000000','physical_pixels=21000004'),
                 ('native_pixels=24000000','native_pixels=21000000'),('native_pixels=24000000','native_pixels=fffffff0'),
                 ('allocations=1','allocations=2'),('frees=0','frees=1'),('enter=1','enter=0'),
                 ('leave=0','leave=1'),('fault=0','fault=3'),('native_size=(640,480)','native_size=(800,600)'),
                 ('physical_size=(800,600)','physical_size=(640,480)'),('native_com=00000000','native_com=00000001')]
        for row in rows:
            for old,new in changes:
                with self.subTest(event=row.split()[1],mutation=new):
                    self.assertIn(old,row);self.bad(log.replace(row,row.replace(old,new)),packet)
            esp=re.search(r'\besp=([0-9a-f]+)',row).group(1)
            self.bad(log.replace(row,row.replace('esp='+esp,'esp='+f'{int(esp,16)+4:08x}',1)),packet)
        for row in rows:
            if 'event=LOAD_CALL ' in row or 'event=BLIT_CALL ' in row:
                self.bad(log.replace(row,row.replace('eax=23000000','eax=20000000')),packet)
                self.bad(log.replace(row,re.sub(r'caller=[0-9a-f]+','caller=0042239f',row)),packet)

    def test_wrong_stage_candidate_availability_surface_and_rejection_are_retained(self):
        packet=small_packet();log=log_fixture(packet)
        changes=[('after_replayed_pushes=5','after_replayed_pushes=1'),
                 ('capture=owned_physical_mirror','capture=memory_map'),
                 ('primary_vtable=0050eec4','primary_vtable=0050ee24'),
                 ('surface=20000000 size=(800,600) base=21000000','surface=23000000 size=(800,600) base=24000000'),
                 ('revision='+producer.builder.REVISION,'revision=unknown'),('state_bytes=4096','state_bytes=128')]
        for old,new in changes:
            self.assertIn(old,log);self.bad(log.replace(old,new),packet)
        for text in ('MCAP_REJECT reason=failed','MCAP_UNKNOWN extra=1','mCaP_CANVAS malformed',
                     'MCANVAS_CONTRACT_FAIL','MODAL_SURFDUMP_HOST_READY','AV_SURFDUMP code=c0000005',
                     'Syntax error','MCAP_CANVAS event=READY'):
            self.bad(log+text+'\n',packet)
        for key,value in (('stage',producer.builder.BASE_STAGE),('candidate_sha256','b'*64),
                          ('availability','construct_all'),('castle_index',1)):
            changed=copy.deepcopy(packet);changed[key]=value;self.bad(log,changed)

    def test_projection_changes_one_stage_token_only_and_keeps_duplicate_failure(self):
        packet=small_packet();log=log_fixture(packet)
        contract=f"PTILE_CONTRACT_PASS stage={producer.STAGE} resolution=800x600 candidate_sha256={'a'*64}"
        extra='.echo '+contract+'\n.echo unchanged\n'
        p_log,p_extra,binding=trace._project_initial(log,extra,packet)
        self.assertEqual(p_log.replace('stage='+producer.builder.BASE_STAGE+' ','stage='+producer.STAGE+' ',1),log)
        self.assertEqual(p_extra.replace('stage='+producer.builder.BASE_STAGE+' ','stage='+producer.STAGE+' ',1),extra)
        self.assertNotEqual(binding['log_original_sha256'],binding['log_projected_sha256'])
        duplicate=next(t for t in log.splitlines() if t.startswith('PTILE_EVENT'))
        bad=log.replace(duplicate,duplicate+'\n'+duplicate,1)
        projected,_,_=trace._project_initial(bad,extra,packet)
        self.assertEqual(projected.count(duplicate),2)
        for badlog in (log.replace(contract,''),log+'\n'+contract):
            with self.assertRaises(ValueError):trace._project_initial(badlog,extra,packet)


class FullBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=command_fixture.ORIGINAL.read_bytes()
        cls.candidate,cls.metadata,cls.extra,cls.template=producer.canonical_template(cls.original,'800x600',minimap_viewport=True)
        cls.packet=producer.build_screen_probe(cls.original,cls.candidate,candidate_sha256=producer.sha(cls.candidate),
            stage=producer.STAGE,resolution='800x600',route='school',availability='existing_flags',castle_index=0,
            rendered_probe=cls.template,minimap_viewport=True)
        cls.compiled=trace.compile_probe(cls.packet)
        cls.log=log_fixture(cls.packet,cls.extra)

    def test_whole_canonical_packet_probe_candidate_and_initial_projection(self):
        result=trace.evaluate_trace(self.log,original=self.original,candidate=self.candidate,
                                    packet=self.packet,generated_probe=self.compiled.encode('ascii'))
        self.assertTrue(result['passed'],result['failures'])
        self.assertTrue(result['initial_map_trace']['passed'])
        self.assertTrue(result['initial_map_projection'])
        self.assertEqual(result['surface']['surface'],0x20000000)
        self.assertFalse(result['runtime_accepted']);self.assertFalse(result['cleanup_verified'])

    def test_canonical_source_packet_and_probe_mutations_cannot_reach_projection(self):
        mutations=[]
        bad=copy.deepcopy(self.packet);bad['canvas_state_va']+=4;mutations.append((self.candidate,bad,self.compiled.encode()))
        mutations.append((self.candidate,self.packet,self.compiled.replace('MCAP_SURFDUMP_HOST_READY','MCAP_FAKE_HOST_READY').encode()))
        mutations.append((self.candidate[:-1]+bytes([self.candidate[-1]^1]),self.packet,self.compiled.encode()))
        for candidate,packet,probe in mutations:
            with patch.object(trace,'_project_initial',side_effect=AssertionError('projection before binding')):
                result=trace.evaluate_trace(self.log,original=self.original,candidate=candidate,packet=packet,generated_probe=probe)
                self.assertFalse(result['passed']);self.assertIsNone(result['initial_map_projection'])

    def test_unchanged_initial_duplicate_still_fails_full_authenticated_trace(self):
        row=next(t for t in self.log.splitlines() if t.startswith('PTILE_EVENT'))
        log=self.log.replace(row,row+'\n'+row,1)
        result=trace.evaluate_trace(log,original=self.original,candidate=self.candidate,packet=self.packet,
                                   generated_probe=self.compiled.encode())
        self.assertFalse(result['passed'])
        self.assertFalse(result['initial_map_trace']['passed'])
        self.assertTrue(any('initial map trace:' in x for x in result['failures']))


if __name__=='__main__':unittest.main()
