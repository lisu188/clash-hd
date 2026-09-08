"""Synthetic protocol and offline whole-image/compiler fixtures; no runtime."""
from __future__ import annotations

from dataclasses import asdict
import copy
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import framed_screen_trace as trace
import framed_screen_probe as producer
import test_initial_map_paint_trace as initial_fixture
import test_framed_screen_probe as command_fixture

ORIGINAL=Path('C:/Clash/clash95.exe')


def small_packet(route='school',availability='existing_flags'):
    return dict(stage=producer.STAGE,resolution='800x600',candidate_sha256='a'*64,
                route=asdict(producer.ROUTES[route]),availability=availability,castle_index=0)


def log_fixture(packet, extra=None):
    name=packet['route']['name']
    events=initial_fixture.initial_events(framed=True)
    for row in events:
        row['tid']=0x2345
        row['records']=[text.replace('tid=abc','tid=2345') for text in row['records']]
    initial,_=initial_fixture.fixture(events,stage=producer.STAGE,close='')
    initial=initial.replace(initial_fixture.SHA,packet['candidate_sha256'])
    if extra:
        for bp,va in re.findall(r'^bp\s*(\d+)\s+([0-9a-f]{8}) ',extra,re.M|re.I):
            old=initial_fixture.SITES[int(bp)]
            initial=initial.replace(f'eip={old:08x}',f'eip={int(va,16):08x}')
    initial_lines=initial.splitlines()
    commands=command_fixture.CommandTests().advance(name,packet['availability'])
    modal=commands[3]
    byte=f"MODAL_BYTE_CONTRACT_PASS candidate_sha256={packet['candidate_sha256']} route={name}"
    contract=(f"MODAL_CONTRACT stage={packet['stage']} resolution={packet['resolution']} candidate_sha256={packet['candidate_sha256']} "
              f"route={name} availability={packet['availability']} castle_index=0 runtime_acceptance=0")
    return '\n'.join([byte,*initial_lines[:2],contract,*initial_lines[2:],
        'SURFDUMP_READY redraw_seq=4 surface=20000000 size=(800,600) base=21000000 bytes=480000',
        'SCROLL_VISDUMP player=0 screen0=(32,16) map0=(10,17) rows=9 cols=12 tile=(64,64) vis_base=10022331 dump_start=100223b5 count=145',
        *modal])+'\n'


class SequenceTests(unittest.TestCase):
    def assert_bad(self,log,packet):
        report=trace.evaluate_sequence(log,packet)
        self.assertFalse(report['sequence_passed'],report)
        self.assertTrue(report['failures'])
        self.assertFalse(report['ready_for_host_capture'])
        return report

    def test_seven_supported_routes_and_explicit_availability(self):
        for route in producer.ROUTES:
            for availability in ('existing_flags','construct_all'):
                with self.subTest(route=route,availability=availability):
                    packet=small_packet(route,availability)
                    result=trace.evaluate_sequence(log_fixture(packet),packet)
                    self.assertTrue(result['sequence_passed'],result['failures'])
                    self.assertFalse(result['source_authenticated'])
                    self.assertFalse(result['ready_for_host_capture'])
                    self.assertEqual(result['surface']['width'],800)
                    self.assertEqual(result['surface']['bytes'],480000)

    def test_each_missing_duplicate_or_reordered_modal_row_fails(self):
        packet=small_packet(availability='construct_all')
        lines=log_fixture(packet).splitlines()
        indices=[i for i,line in enumerate(lines) if line.startswith('MODAL_')]
        for i in indices:
            with self.subTest(missing=i): self.assert_bad('\n'.join(lines[:i]+lines[i+1:]),packet)
            with self.subTest(duplicate=i):
                bad=lines.copy();bad.insert(i,lines[i]);result=self.assert_bad('\n'.join(bad),packet)
                self.assertEqual(len(result['raw_records']),len(indices)+1)
        for left,right in zip(indices,indices[1:]):
            with self.subTest(reordered=(left,right)):
                bad=lines.copy();bad[left],bad[right]=bad[right],bad[left]
                self.assert_bad('\n'.join(bad),packet)

    def test_native_identity_surface_owner_and_contract_mutations_fail(self):
        packet=small_packet();log=log_fixture(packet)
        changes={
            'MODAL_BYTE_CONTRACT_PASS': [('a'*64,'b'*64)],
            'MODAL_CONTRACT': [('route=school','route=hospital'),('availability=existing_flags','availability=construct_all'),
                               ('resolution=800x600','resolution=1024x768'),('castle_index=0','castle_index=1')],
            'MODAL_MAP_HANDOFF': [('render_hook=0040ad40','render_hook=004617a0'),('lower=00000000','lower=00000001'),
                                  ('post=00000000','post=00000001'),('size=(800,600)','size=(640,480)')],
            'MODAL_CASTLE_STATE': [('owner=0','owner=5'),('xy=(14,20)','xy=(100,20)'),('flags=(0,0)','flags=(100,0)')],
            'MODAL_FORCE_CALL': [('entry=00422180','entry=00422181'),('return_sentinel=00406fa1','return_sentinel=00406fa0')],
            'MODAL_OVERVIEW_PROLOGUE': [('after_first_push=1','after_first_push=0'),
                                       ('return_sentinel=00406fa1','return_sentinel=00406fa0'),
                                       ('index=0','index=1')],
            'MODAL_FORCED_DISPATCH': [('branch=0042277b','branch=0042274f'),('new_render=22000000','new_render=00000000')],
            'MODAL_FLIP_GATE_FORCED': [('callback=0043d8e0','callback=0043dce0'),('command=156','command=153'),('forced=1','forced=0')],
            'MODAL_CALLBACK_CALL': [('owner=1007c6ea','owner=1007c6eb'),('render_hook=004617a0','render_hook=0040ad40')],
            'MODAL_SCREEN_ENTRY': [('owner=1007c6ea','owner=1007c6eb')],
            'MODAL_SURFDUMP_READY': [('size=(800,600)','size=(1024,768)'),('bytes=480000','bytes=480001'),
                                     ('base=21000000','base=00000000'),('base=21000000','base=ffffffff'),
                                     ('surface=20000000','surface=0051d4c0'),('capture=memory_map','capture=primary'),
                                     ('owner=1007c6ea','owner=1007c6eb'),('manual_input_proof=0','manual_input_proof=1')],
        }
        for marker,mutations in changes.items():
            original=next(line for line in log.splitlines() if line.startswith(marker+' '))
            for old,new in mutations:
                with self.subTest(marker=marker,change=(old,new)):
                    self.assertIn(old,original)
                    self.assert_bad(log.replace(original,original.replace(old,new)),packet)
        # Change one identity field in each valid native identity observation.
        for line in log.splitlines():
            if line.startswith('MODAL_') and 'tid=' in line:
                for field in ('tid','esp','eip'):
                    match=re.search(rf'\b{field}=([0-9a-f]+)',line)
                    if match:
                        with self.subTest(marker=line.split()[0],field=field):
                            replacement=line[:match.start(1)]+f'{int(match[1],16)+4:x}'+line[match.end(1):]
                            self.assert_bad(log.replace(line,replacement),packet)

    def test_closure_must_match_handoff_and_ordinary_ready_never_completes_modal(self):
        packet=small_packet();log=log_fixture(packet)
        close=next(line for line in log.splitlines() if line.startswith('PTILE_TRACE_CLOSED'))
        for bad in (log.replace(close,''),log.replace(close,close+'\n'+close),
                    log.replace(close,close.replace('00406fa0','00406fa1')),
                    log.replace(close,close.replace('tid=2345','tid=2346'))):
            self.assert_bad(bad,packet)
        self.assert_bad(log[:log.index('MODAL_MAP_HANDOFF')],packet)
        self.assert_bad(log+'SURFDUMP_HOST_READY\n',packet)
        for marker,old,new in (
            ('SURFDUMP_READY','surface=20000000','surface=20000004'),
            ('SURFDUMP_READY','redraw_seq=4','redraw_seq=5'),
            ('SCROLL_VISDUMP','count=145','count=144'),
            ('SCROLL_VISDUMP','cols=12','cols=11'),
            ('SCROLL_VISDUMP','vis_base=10022331','vis_base=10022332'),
            ('SCROLL_VISDUMP','map0=(10,17)','map0=(99,17)'),
        ):
            row=next(line for line in log.splitlines() if line.startswith(marker+' '))
            with self.subTest(snapshot=marker,mutation=new):
                self.assert_bad(log.replace(row,row.replace(old,new)),packet)
        for marker in ('SURFDUMP_READY','SCROLL_VISDUMP'):
            row=next(line for line in log.splitlines() if line.startswith(marker+' '))
            self.assert_bad(log.replace(row,''),packet)

    def test_partial_unknown_rejection_or_error_even_after_ready_is_retained(self):
        packet=small_packet();log=log_fixture(packet)
        for extra in ('MODAL_SURFDUMP_READY route=school','MODAL_REJECT reason=unexpected_native_return',
                      'MODAL_REJECT reason=unexpected_callback_return','MODAL_NEW_STATE state=1',
                      'modal_surfdump_host_ready','0:000> MODAL_SURFDUMP_HOST_READY',
                      'Syntax error at q;','AV_SURFDUMP','PTILE_REJECT status0'):
            with self.subTest(extra=extra):
                report=self.assert_bad(log+extra+'\n',packet)
                if 'modal_' in extra.lower(): self.assertEqual(report['raw_records'][-1]['text'],extra)

    def test_post_push_boundary_is_required_and_later_present_stack_is_unchanged(self):
        packet=small_packet('castle_overview');log=log_fixture(packet)
        prologue=next(row for row in log.splitlines() if row.startswith('MODAL_OVERVIEW_PROLOGUE '))
        self.assertIn('eip=00422181 esp=00fffff8',prologue)
        self.assertIn('MODAL_OVERVIEW_PRESENT_RETURN tid=2345 eip=0042239f esp=00ffffc4',log)
        for replacement in (prologue.replace('00422181','00422180'),
                            prologue.replace('00fffff8','00fffffc'),
                            prologue.replace('MODAL_OVERVIEW_PROLOGUE','MODAL_OVERVIEW_ENTRY'),
                            ''):
            self.assert_bad(log.replace(prologue,replacement),packet)
        # Preserve the first observed run's failure shape, never insert an
        # assumed entry based on a later present or otherwise infer a pass.
        failed=log[:log.index('MODAL_OVERVIEW_PROLOGUE')]+'MODAL_REJECT reason=overview_present_call\n'
        result=self.assert_bad(failed,packet)
        self.assertIsNone(result['surface'])
        self.assertEqual(result['raw_records'][-1]['text'],'MODAL_REJECT reason=overview_present_call')


@unittest.skipUnless(ORIGINAL.is_file(),'user-owned original required for offline source/image binding')
class BoundTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL.read_bytes()
        cls.image,_,cls.extra,template=producer.canonical_template(cls.original,'800x600')
        cls.packet=producer.build_screen_probe(cls.original,cls.image,candidate_sha256=producer.sha(cls.image),
            stage=producer.STAGE,resolution='800x600',route='school',availability='existing_flags',
            castle_index=0,rendered_probe=template)
        cls.compiled=trace.compile_probe(cls.packet)
        cls.log=log_fixture(cls.packet,cls.extra)

    def evaluate(self,log=None,**changes):
        args=dict(original=self.original,candidate=self.image,packet=self.packet,generated_probe=self.compiled.encode('ascii'))
        args.update(changes)
        return trace.evaluate_trace(self.log if log is None else log,**args)

    def test_full_bound_trace_and_canonical_lf_match(self):
        for data in (self.compiled.encode('ascii'),self.compiled.replace('\n','\r\n').encode('ascii')):
            with self.subTest(crlf=b'\r' in data):
                result=self.evaluate(generated_probe=data)
                self.assertTrue(result['passed'],result['failures'])
                self.assertTrue(result['ready_for_host_capture'])
                self.assertTrue(result['initial_map_trace']['passed'])
                self.assertFalse(result['runtime_accepted']);self.assertFalse(result['cleanup_verified'])
                self.assertEqual(result['surface']['base'],0x21000000)

    def test_compiler_uses_exact_five_startup_bps_and_byte_checks_before_bps(self):
        self.assertNotRegex(self.compiled,r'__[A-Z0-9_]+__')
        self.assertEqual(self.compiled.splitlines().count('g'),1)
        self.assertEqual(self.compiled.count(self.extra.strip()),1)
        for va in ('0044789a','0046e4d0','0046e6df','0046fd01','0047BFD0'):
            self.assertIn('bp '+va+' ',self.compiled)
        self.assertLess(self.compiled.index('MODAL_BYTE_CONTRACT_PASS'),self.compiled.index('\nbp '))
        self.assertLess(self.compiled.index('PTILE_TRACE_CLOSED'),self.compiled.index('MODAL_MAP_HANDOFF'))
        self.assertIn('ed 00544cfc 00005000; ed 00544d00 00002980;',self.compiled)
        self.assertNotIn('SURFDUMP_PRE_ENTRY_SLOT_DEFERRED',self.compiled)
        self.assertNotIn('SURFDUMP_FORCE_VISIBLE_EDGES recipe',self.compiled)

    def test_whole_probe_packet_original_and_candidate_changes_cannot_pass(self):
        variants=[self.compiled+'\n.echo additional\n',self.compiled.replace('r eax=1; gc','r eax=0; gc',1),
                  self.compiled.replace('bd 70;','',1),self.compiled.replace('SCROLL_VISDUMP','IGNORED_SNAPSHOT',1),
                  self.compiled.replace('MODAL_BYTE_CONTRACT_PASS','OMITTED_BYTE_PASS',1)]
        for text in variants:
            with self.subTest(probe_difference=next((i for i,(a,b) in enumerate(zip(text,self.compiled)) if a!=b),len(text))):
                self.assertFalse(self.evaluate(generated_probe=text.encode('ascii'))['passed'])
        bad=copy.deepcopy(self.packet);bad['availability']='construct_all'
        self.assertFalse(self.evaluate(packet=bad)['passed'])
        bad=bytearray(self.image);bad[-1]^=1
        self.assertFalse(self.evaluate(candidate=bytes(bad))['passed'])
        bad=bytearray(self.original);bad[-1]^=1
        self.assertFalse(self.evaluate(original=bytes(bad))['passed'])

    def test_existing_initial_validator_failure_is_preserved(self):
        event=next(line for line in self.log.splitlines() if line.startswith('PTILE_EVENT seq=3 '))
        report=self.evaluate(self.log.replace(event,event+'\n'+event))
        self.assertFalse(report['passed'])
        self.assertFalse(report['initial_map_trace']['passed'])
        self.assertTrue(any('initial map trace:' in failure for failure in report['failures']))
        report=self.evaluate(self.log.replace('PTILE_TRACE_CLOSED tid=2345','PTILE_TRACE_CLOSED tid=1234'))
        self.assertFalse(report['passed'])

    def test_startup_source_pin_change_is_not_silently_accepted(self):
        with patch.object(trace,'HARNESS_SHA256','0'*64):
            with self.assertRaisesRegex(ValueError,'source changed'): trace.compile_probe(self.packet)


if __name__=='__main__':
    unittest.main()
