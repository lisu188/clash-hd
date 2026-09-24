"""Offline primary-stage context/native-sequence fixtures; no game or debugger.

Synthetic records exercise parser boundaries only. One optional local-original
fixture reconstructs a real candidate; none of these logs is runtime evidence.
"""
from pathlib import Path
import copy
from contextlib import redirect_stdout
import hashlib
import io
import json
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

import modal_primary_candidate_context as context
import modal_primary_initial_trace as initial
import test_initial_map_paint_trace as initial_fixture


class ContextTests(unittest.TestCase):
    def test_exact_schema_stage_revision_and_all_siblings(self):
        manifest = dict(schema='clash95_framed_modal_primary_candidate_v1', stage=context.builder.STAGE,
                        recipe_revision=context.builder.REVISION, resolution='1024x768', tuple_span=(1,2,'source'))
        with tempfile.TemporaryDirectory(prefix='primary-context-') as folder:
            path = Path(folder)/'candidate.candidate.json'
            exe, probe = path.with_name('candidate.exe'), path.with_name('candidate.cdb')
            path.write_text(json.dumps(manifest)); exe.write_bytes(b'image'); probe.write_bytes(b'probe')
            with patch.object(context.builder, 'build_candidate', return_value=(b'image',manifest,'probe')):
                report = context.load_context(b'original',b'image',path)
                self.assertEqual(report['manifest_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
                self.assertEqual(report['probe_path'],str(probe.resolve()))
                for target in (exe,probe):
                    before=target.read_bytes();target.write_bytes(b'changed')
                    with self.assertRaises(ValueError):context.load_context(b'original',b'image',path)
                    target.write_bytes(before)
                    target.unlink()
                    with self.assertRaises(OSError):context.load_context(b'original',b'image',path)
                    target.write_bytes(before)
                with self.assertRaises(ValueError):context.load_context(b'original',b'changed',path)
                for key,value in (('schema','clash95_framed_modal_slots_candidate_v1'),('stage','slots-validation'),
                                  ('recipe_revision','owned_modal_slots_v1'),('resolution','800x600'),('tuple_span',[True,2,'source'])):
                    path.write_text(json.dumps(dict(manifest,**{key:value})))
                    with self.subTest(key=key),self.assertRaises(ValueError):context.load_context(b'original',b'image',path)
                path.write_text(json.dumps(manifest));path.unlink()
                with self.assertRaises(OSError):context.load_context(b'original',b'image',path)

    def test_manifest_drift_during_rebuild_fails(self):
        manifest=dict(schema='clash95_framed_modal_primary_candidate_v1',stage=context.builder.STAGE,
                      recipe_revision=context.builder.REVISION,resolution='1024x768')
        with tempfile.TemporaryDirectory(prefix='primary-context-') as folder:
            path=Path(folder)/'candidate.candidate.json';path.write_text(json.dumps(manifest))
            path.with_name('candidate.exe').write_bytes(b'image');path.with_name('candidate.cdb').write_bytes(b'probe')
            def changed(*args):
                path.write_text(json.dumps(manifest)+' ')
                return b'image',manifest,'probe'
            with patch.object(context.builder,'build_candidate',side_effect=changed),self.assertRaisesRegex(ValueError,'changed during'):
                context.load_context(b'original',b'image',path)


class InitialTests(unittest.TestCase):
    def fixture(self,resolution='1024x768'):
        return initial_fixture.fixture(initial_fixture.initial_events(resolution,framed=True),
                                       resolution=resolution,stage=context.builder.STAGE)

    def evaluate(self,log,probe,resolution='1024x768'):
        return initial.evaluate_trace(log,probe,resolution=resolution,candidate_sha256=initial_fixture.SHA,
                                      stage=context.builder.STAGE)

    def test_authentic_primary_stage_all_geometry_and_uninterpreted_eax(self):
        for resolution in ('800x600','1024x768','1280x720','1280x960','1920x1080','802x602'):
            log,probe=self.fixture(resolution);before=(log,probe)
            r=self.evaluate(log,probe,resolution)
            self.assertTrue(r['passed'],r['failures']);self.assertEqual((log,probe),before)
            self.assertEqual(r['initial_sequence']['return_eax'],0xdeadbeef)
            self.assertEqual(r['trace_contract']['full_status_to_ready_stack_bytes'],148)
            self.assertFalse(r['source_authenticated']);self.assertFalse(r['ready_for_host_capture'])
            self.assertFalse(r['manual_input_proof']);self.assertFalse(r['promotion_ready'])

    def test_stale_stage_wrong_stack_event_duplicate_and_incomplete_fail(self):
        log,probe=self.fixture()
        variants=[log.replace(context.builder.STAGE,initial_fixture.trace.FRAMED_STAGE),
                  log.replace('status=1','status=0',1),log.replace('owner=0040ad40','owner=004617a0',1),
                  log.replace('esp=000fff6c','esp=000fff70',1),
                  log.replace('PTILE_INITIAL_RETURN','PTILE_UNKNOWN',1)]
        event=next(x for x in log.splitlines() if x.startswith('PTILE_EVENT'))
        variants.append(log.replace(event,event+'\n'+event,1))
        variants.append('\n'.join(x for x in log.splitlines() if not x.startswith('PTILE_TRACE_CLOSED')))
        for value in variants:
            self.assertNotEqual(value,log)
            r=self.evaluate(value,probe);self.assertFalse(r['passed'],value)
        r=initial.evaluate_trace(log,probe,resolution='1024x768',candidate_sha256=initial_fixture.SHA,
                                 stage=initial_fixture.trace.FRAMED_STAGE)
        self.assertFalse(r['passed'])

    def test_integrity_dependency_drift_refused(self):
        with patch.object(initial,'INTEGRITY_SHA256','0'*64),self.assertRaisesRegex(ValueError,'helper source changed'):
            self.evaluate(*self.fixture())



def native_fixture(*, overview_cursor=1,barracks_cursor=1,checkpoint=None, packet=None):
    """Declared synthetic events; never presented as measured runtime output."""
    import modal_primary_barracks_trace as trace
    import test_framed_modal_canvas_probe as native
    from dataclasses import asdict
    packet=copy.deepcopy(packet) if packet else dict(stage=trace.producer.STAGE,resolution='800x600',candidate_sha256='a'*64,
        protocol_revision=trace.producer.PROTOCOL_REVISION,route=asdict(trace.producer.ROUTES['barracks']),
        availability='construct_all',castle_index=0,canvas_state_va=native.METADATA['state_va'],
        canvas_observer_vas=native.METADATA['modal_observer_vas'],slot_entry_vas={'after_dirty_copy':0x5f0100})
    keys=('full_entry','full_fallback','remove_call','remove_entry','remove_return','publish_call_direct','publish_return_direct',
          'publish_call_cursor','publish_return_cursor','publish_entry','draw_call','draw_entry','draw_return',
          'full_return_direct','full_return_cursor','cursor_rect','placeholder_before','placeholder_after')
    obs=packet.setdefault('primary_observers',{key:0x610000+i*0x100 for i,key in enumerate(keys)})
    obs.update(remove_entry=0x460F90,publish_entry=0x4E9920,draw_entry=0x460EA0,cursor_rect=0x460BB0,
               placeholder_before=0x432F9E,placeholder_after=0x432FA1)
    packet['checkpoints']=trace.producer.checkpoint_contract(obs)
    w,h=map(int,packet['resolution'].split('x'));ox,oy=(w-640)//2,(h-480)//2
    metadata=dict(state_va=packet['canvas_state_va'],modal_observer_vas=packet['canvas_observer_vas'])
    native_rows=native.CommandTests().advance('barracks',packet['availability'],width=w,height=h,metadata=metadata)[3]
    enter=next(row for row in native_rows if row.startswith('MCAP_CANVAS event=ENTER '))
    H=0x1000000;tid=0x2345;native_pointer=0x23000000;physical=0x20000000
    owner=0x1007c6ea
    def cp(index,eip,cursor):
        name=trace.CHECKPOINT_NAMES[index];depth=(96,188,160,88)[index];sp=H-depth
        row=re.sub(r'event=ENTER','event=CHECKPOINT',enter)
        row=re.sub(r'eip=[0-9a-f]+',f'eip={eip:08x}',row)
        row=re.sub(r'esp=[0-9a-f]+',f'esp={sp:08x}',row,count=1)
        row=row.replace('mirrors=0','mirrors=3').replace('mirror=0','mirror=1')
        return [f'MPCAP_CHECKPOINT_REQUEST name={name}',row,f'MPCAP_CHECKPOINT name={name} index={index} tid={tid:x} eip={eip:08x} esp={sp:08x} surface={physical:08x} size=({w},{h}) base=21000000 bytes={w*h} owner={owner:08x} render={(0x51D4C0 if index in (1,2) else native_pointer):08x} cursor={cursor}',
                f'MPCAP_HOST_READY name={name}']
    def full(route,active):
        state=2 if route=='overview' else 8;sp=H-(136 if state==2 else 92);parent=0x4220C6 if state==2 else trace.producer.BLIT_CALLS['barracks']+3
        branch='cursor' if active else 'direct';names=['full-entry']
        if active:names+=['remove-call','remove-entry','remove-return']
        names+=['publish-call','publish-entry','publish-return']
        if active:names+=['draw-call','draw-entry','draw-return']
        names+=['full-return'];result=[]
        depths={'full-entry':0,'remove-call':36,'remove-entry':40,'remove-return':36,'publish-call':4,'publish-entry':8,
                'publish-return':4,'draw-call':36,'draw-entry':40,'draw-return':36,'full-return':0}
        for name in names:
            key=name.replace('-','_')+('_'+branch if name in ('publish-call','publish-return','full-return') else '')
            cursor=active if name in ('full-entry','full-return') else 1 if name in ('remove-call','remove-entry','draw-return') else 0
            eax=native_pointer if name in ('full-entry','full-return') else physical if name.startswith('publish') else 0x544CD8
            caller=parent if name in ('full-entry','full-return') else obs[name.replace('-entry','_return')+('_'+branch if name=='publish-entry' else '')] if name.endswith('-entry') else 0xdecafbad
            result.append(f'MPCAP_EVENT event={name} tid={tid:x} eip={obs[key]:08x} esp={sp-depths[name]:08x} full_esp={sp:08x} route_state={state} cursor={cursor} eax={eax:08x} caller={caller:08x} parent={parent:08x}')
            if route=='barracks' and name=='publish-return':result+=cp(0,obs[key],0)
        return result
    rows=[];blit=0
    for line in native_rows:
        if line.startswith('MCAP_SURFDUMP_READY '):
            # Model the actual original432FA5 render-device restoration. The
            # inherited command-only emulator does not execute that function.
            line=line.replace('render=22000000','render=23000000')
        rows.append(line)
        if line.startswith('MCAP_SCREEN_ENTRY '):rows.append('MPCAP_PRIMARY_OBSERVERS_ARM')
        if line.startswith('MCAP_CANVAS event=BLIT_CALL '):
            rows+=full('overview' if blit==0 else 'barracks',overview_cursor if blit==0 else barracks_cursor);blit+=1
        if line.startswith('MCAP_CANVAS event=FACILITY_BLIT_RETURN '):
            for i in range(12):
                x=126+71*(i%6);y=75+131*(i//6)
                rows.append(f'SCAP_SLOT_COPY tid={tid:x} eip={packet["slot_entry_vas"]["after_dirty_copy"]:08x} esp={H-212:08x} source={native_pointer:08x} x={x} y={y} right={x+32} bottom={y+64} dest_x={x} dest_y={y} return=00432c10 producer_return=00432de7')
            rows.append(f'MPCAP_CURSOR_RECT tid={tid:x} eip=00460bb0 esp={H-168:08x} eax=00544cd8 x={220+ox} right={423+ox} y={289+oy} bottom={409+oy} caller=00432f61 cursor={barracks_cursor}')
            rows.append(f'MPCAP_PLACEHOLDER tid={tid:x} eip=00432f9e esp={H-188:08x} primary=0051d4c0 vtable=0050eec4 sprite=26000000 resource=25000000 index=25 x={220+ox} y={289+oy} size=(203,120) parent=00433e4e args=(ffffffff,ffffffff,ffffffff,ffffffff,0,0,0)')
            rows+=cp(1,0x432F9E,barracks_cursor)+cp(2,0x432FA1,barracks_cursor)
        if line=='MCAP_SURFDUMP_HOST_READY':rows+=cp(3,0x433E77,1)
    events=initial_fixture.initial_events(packet['resolution'],framed=True)
    for row in events:
        row['tid']=tid;row['records']=[t.replace('tid=abc',f'tid={tid:x}') for t in row['records']]
    ilog,extra=initial_fixture.fixture(events,resolution=packet['resolution'],stage=trace.producer.STAGE,close='')
    ilog=ilog.replace(initial_fixture.SHA,packet['candidate_sha256'])
    extra=extra.replace(initial_fixture.SHA,packet['candidate_sha256'])
    if packet.get('candidate_extra'):
        for bp,va in re.findall(r'^bp\s*(\d+)\s+([0-9a-f]{8}) ',packet['candidate_extra'],re.M|re.I):
            ilog=ilog.replace(f'eip={initial_fixture.SITES[int(bp)]:08x}',f'eip={int(va,16):08x}')
        extra=packet['candidate_extra']
    ir=ilog.splitlines();cols,heights=(w-64+63)//64,(h-32+63)//64
    count=(cols-1)*13+((17+heights-1)>>3)-(17>>3)+1
    head=[f'MCAP_BYTE_CONTRACT_PASS candidate_sha256={packet["candidate_sha256"]} route=barracks',
          f'MPRIMARY_CONTRACT_PASS stage={packet["stage"]} resolution={packet["resolution"]} candidate_sha256={packet["candidate_sha256"]} revision={context.builder.REVISION}',
          'MPRIMARY_SCOPE owned_modal_primary primary_composition_proven=false manual_input_proof=false promotion_ready=false',*ir[:2],
          f'MCAP_CONTRACT stage={packet["stage"]} resolution={packet["resolution"]} candidate_sha256={packet["candidate_sha256"]} route=barracks availability={packet["availability"]} castle_index=0 protocol={trace.producer.PROTOCOL_REVISION} runtime_acceptance=0',*ir[2:],
          f'SURFDUMP_READY redraw_seq=4 surface=20000000 size=({w},{h}) base=21000000 bytes={w*h}',
          f'SCROLL_VISDUMP player=0 screen0=(32,16) map0=(10,17) rows={heights} cols={cols} tile=(64,64) vis_base=10022331 dump_start=100223b5 count={count}']
    lines=head+rows
    if checkpoint is not None:
        marker='MPCAP_HOST_READY name='+checkpoint;lines=lines[:lines.index(marker)+1]
    return '\n'.join(lines)+'\n',packet,extra


class NativeSequenceTests(unittest.TestCase):
    def evaluate(self,log,packet,checkpoint=None):
        import modal_primary_barracks_trace as trace
        seq=trace.evaluate_sequence(log,packet,checkpoint=checkpoint)
        slots=trace.evaluate_slots(log,packet,seq,checkpoint=checkpoint)
        primary=trace.evaluate_primary_route(log,packet,seq,checkpoint=checkpoint)
        return seq,slots,primary

    def test_all_four_prefixes_and_both_cursor_branches(self):
        for first in (0,1):
            for second in (0,1):
                for checkpoint in (None,'full-published','placeholder-before','placeholder-after','final-ready'):
                    log,packet,extra=native_fixture(overview_cursor=first,barracks_cursor=second,checkpoint=checkpoint)
                    seq,slots,primary=self.evaluate(log,packet,checkpoint)
                    with self.subTest(first=first,second=second,checkpoint=checkpoint):
                        self.assertTrue(seq['sequence_passed'],seq['failures'])
                        self.assertTrue(slots['passed'],slots['failures']);self.assertTrue(primary['passed'],primary['failures'])
                        self.assertFalse(seq['ready_for_host_capture']);self.assertFalse(primary['primary_composition_proven'])
                        self.assertEqual(primary['coverage']['selected_panel'],'unexercised')
                        self.assertEqual(len(slots['raw_records']),0 if checkpoint=='full-published' else 12)

    def test_native_call_pair_stack_parent_mode_and_alias_mutations_fail(self):
        log,packet,_=native_fixture()
        for old,new in (('event=remove-entry','event=remove-call'),('event=publish-entry','event=publish-return'),
                        ('full_esp=00ffffa4','full_esp=00ffffa8'),('parent=004220c6','parent=004220ca'),
                        ('route_state=2','route_state=8'),('cursor=1','cursor=2'),('caller=00610400','caller=00610404'),
                        ('right=503','right=502'),('index=25','index=24'),('args=(ffffffff','args=(fffffffe'),
                        ('owner=1007c6ea render=23000000','owner=1007c6ea render=22000000'),('event=CHECKPOINT','event=READY')):
            self.assertIn(old,log,old);bad=log.replace(old,new,1)
            seq,slots,primary=self.evaluate(bad,packet)
            self.assertFalse(seq['sequence_passed'] and slots['passed'] and primary['passed'],new)

    def test_missing_repeated_and_reordered_primary_events_or_checkpoints_fail(self):
        log,packet,_=native_fixture();lines=log.splitlines()
        selected=[i for i,t in enumerate(lines) if t.startswith('MPCAP_') or 'event=CHECKPOINT ' in t]
        for i in selected:
            for value in (lines[:i]+lines[i+1:],lines[:i]+[lines[i]]+lines[i:]):
                seq,slots,primary=self.evaluate('\n'.join(value),packet)
                self.assertFalse(seq['sequence_passed'] and slots['passed'] and primary['passed'],lines[i])
        for a,b in zip(selected,selected[1:]):
            changed=lines.copy();changed[a],changed[b]=changed[b],changed[a]
            seq,slots,primary=self.evaluate('\n'.join(changed),packet)
            self.assertFalse(seq['sequence_passed'] and slots['passed'] and primary['passed'],lines[a])

    def test_prefix_cannot_hide_future_records_or_claim_later_completion(self):
        for name in ('full-published','placeholder-before','placeholder-after'):
            log,packet,_=native_fixture(checkpoint=name)
            seq,slots,primary=self.evaluate(log,packet,None)
            self.assertFalse(seq['sequence_passed'] and slots['passed'] and primary['passed'])
            complete,_,_=native_fixture()
            seq,slots,primary=self.evaluate(complete,packet,name)
            self.assertFalse(seq['sequence_passed'] and slots['passed'] and primary['passed'])
        log,packet,_=native_fixture()
        for marker in ('MPCAP_UNKNOWN marker=1','MPCAP_REJECT reason=fault',' MPCAP_HOST_READY name=final-ready',
                       'SLOTS_CONTRACT_PASS stage=old'):
            seq,slots,primary=self.evaluate(log+marker+'\n',packet)
            self.assertFalse(seq['sequence_passed'] and slots['passed'] and primary['passed'])

    def test_cursor_rejection_diagnostic_preserves_operands_and_never_establishes_acceptance(self):
        log,packet,_=native_fixture()
        line=('MPCAP_CURSOR_RECT_CONTEXT tid=2345 eip=00460bb0 esp=00ffff58 ebp=00ffff8c eax=00544cd8 '
              'x=220 right=503 y=349 bottom=469 caller=00432f61 expected_tid=2345 root_esp=01000000 '
              'route_state=8 canvas_phase=15 publish_phase=0 checkpoint_index=1 selected=ffffffff '
              'cursor=0 resource=25000000 render=0051d4c0 state_phase=1 state_fault=0')
        # A real rejection stops before the accepted CURSOR_RECT and subsequent
        # checkpoints. Its scalar observation remains readable, never a pass.
        prefix=log[:log.index('MPCAP_CURSOR_RECT tid=')]
        rejected=prefix+line+'\nMPCAP_REJECT reason=cursor_rect\n'
        _,_,primary=self.evaluate(rejected,packet)
        self.assertFalse(primary['passed'])
        self.assertEqual(primary['cursor_rectangle_context']['values']['x'],220)
        self.assertIsNone(primary['cursor_rectangle'])
        self.assertTrue(any('producer rejected native observation: cursor_rect' in failure for failure in primary['failures']))
        for value in (line,line.replace('x=220 ','x=300 '),line+'\n'+line,' '+line,line.upper()):
            _,_,primary=self.evaluate(log+value+'\n',packet)
            self.assertFalse(primary['passed'])



class BindingBoundaryTests(unittest.TestCase):
    def fixture(self):
        import modal_primary_barracks_trace as trace
        log,packet,extra=native_fixture()
        packet.update(candidate_manifest={'path':'synthetic.candidate.json'},candidate_extra=extra)
        return trace,log,packet

    def test_canonical_comparison_precedes_any_sequence_acceptance(self):
        trace,log,packet=self.fixture()
        for field,value in (('stage','old-stage'),('candidate_sha256','b'*64),('canvas_state_va',0x1234),
                            ('recipe_revision','old-recipe'),('primary_observers',{}),('castle_index',False)):
            supplied=copy.deepcopy(packet);supplied[field]=value
            with patch.object(trace.producer,'build_screen_probe',return_value=packet),patch.object(trace,'compile_probe',return_value='canonical'), \
                 patch.object(trace,'evaluate_sequence',side_effect=AssertionError('unbound input reached semantics')):
                result=trace.evaluate_trace(log,original=b'original',candidate=b'candidate',packet=supplied,generated_probe=b'canonical')
            self.assertFalse(result['passed']);self.assertFalse(result['source_authenticated'])
        with patch.object(trace.producer,'build_screen_probe',return_value=packet),patch.object(trace,'compile_probe',return_value='canonical'), \
             patch.object(trace,'evaluate_sequence',side_effect=AssertionError('unbound command reached semantics')):
            result=trace.evaluate_trace(log,original=b'original',candidate=b'candidate',packet=packet,generated_probe=b'changed')
        self.assertFalse(result['passed']);self.assertFalse(result['source_authenticated'])

    def test_separate_sequence_only_and_structural_bound_prefix_verdicts(self):
        # Explicit mocks isolate this orchestration test. The actual-original
        # test below exercises the real reconstruction and command compiler.
        trace,_,base=self.fixture()
        for name in (None,'full-published','placeholder-before','placeholder-after','final-ready'):
            log,packet,extra=native_fixture(checkpoint=name)
            packet.update(candidate_manifest={'path':'synthetic.candidate.json'},candidate_extra=extra)
            with patch.object(trace.producer,'build_screen_probe',return_value=packet),patch.object(trace,'compile_probe',return_value='canonical'):
                result=trace.evaluate_trace(log,original=b'original',candidate=b'candidate',packet=packet,generated_probe=b'canonical',checkpoint=name)
            self.assertTrue(result['passed'],result['failures']);self.assertTrue(result['source_authenticated'])
            self.assertEqual(result['complete'],name in (None,'final-ready'))
            self.assertFalse(result['runtime_accepted']);self.assertFalse(result['cleanup_verified'])
            self.assertFalse(result['manual_input_proof']);self.assertFalse(result['promotion_ready'])
            self.assertFalse(result['modal_sequence']['ready_for_host_capture'])
            self.assertEqual(result['surface']['eip'],result['capture_checkpoint']['values']['eip'])
            self.assertNotIn('initial_map_projection',result)


def admission_trace_mutations(log):
    """Synthetic rejected rows; retain the unchanged baseline and appended row."""
    for namespace in ('MCAP_', 'MPCAP_'):
        duplicate=next(line for line in log.splitlines() if line.startswith(namespace))
        for prefix in ('x_', '7', 'prefix', '0:000> '):
            yield namespace+prefix, namespace, prefix+duplicate
        yield namespace+'lowercase', namespace, 'x_'+duplicate.lower()
        yield namespace+'unknown', namespace, 'x_'+namespace+'UNKNOWN reason=fault'
        yield namespace+'reject', namespace, 'x_'+namespace+'REJECT reason=fault'


DEBUGGER_FAILURE_ROWS=(
    'Unable to insert breakpoint 89 at 00432f9e, Win32 error 0n5',
    '0:000> Unable to insert breakpoint 89 at 00432f9e, Win32 error 0n5',
    'bp89 at 00432f9e failed',
    '0:000> bp110 at 00600000 failed',
    'Syntax error in breakpoint command',
    '0:000> ^ Syntax error',
    'Command file execution failed',
    '0:000> Command file execution failed',
)

CORE_REJECTION_ROWS=(
    'Unable to insert breakpoint 7 at 00432c66','x_MPRIMARY_REJECT example',
    'x_SLOTS_CONTRACT_PASS example','x_MCAP_REJECT example','x_MPCAP_REJECT example',
    'x_MPRI_REJECT invalid_primary','x_MPRI_REJECT invalid_primary',
)


def startup_admission_mutations(log):
    for row in (line for line in log.splitlines() if line.startswith('MPRIMARY_')):
        for prefix in ('x_','7','0:000> '):
            yield 'primary_startup_records',prefix+row
    yield 'primary_startup_records','x_mprimary_unknown value=1'
    for namespace in ('SLOTS','ARMY','COMPLETEHD','MCANVAS'):
        for prefix in ('x_','7','0:000> '):
            yield 'forbidden_stage_records',prefix+namespace+'_CONTRACT_PASS stage=old'


def primary_admission_mutations(log):
    duplicate=next(line for line in log.splitlines() if line.startswith('MPRI_CHECKPOINT '))
    for prefix in ('x_', '7', 'prefix', '0:000> '):
        yield prefix, prefix+duplicate
    yield 'lowercase', 'x_'+duplicate.lower()
    yield 'unknown', 'x_MPRI_UNKNOWN reason=fault'
    yield 'reject', 'x_MPRI_REJECT invalid_primary'
    yield 'contract', 'x_MPRI_NATIVE_CONTRACT_PASS'
    yield 'multiple', 'x_MPRI_REJECT invalid_primary\nx_MPRI_REJECT invalid_primary'


class AdmissionRegressionTests(unittest.TestCase):
    BAD_JSON=(b'{"stage":"wrong","stage":"right"}',
              b'{"nested":{"span":false,"span":1}}',
              b'{"stage":1,"st\\u0061ge":2}',
              b'{"x":NaN}',b'{"x":Infinity}',b'{"x":-Infinity}',
              b'{"x":1e999}',b'{"nested":[-1e999]}',b'[]',b'null',b'true',b'1',
              b'{"nested":'*10000+b'0'+b'}'*10000)

    def test_strict_json_preserves_types_and_rejects_ambiguous_objects(self):
        raw=b'\xef\xbb\xbf{"integer":1,"boolean":true,"fraction":1.0,"text":"\\u00e9","nested":[{"a":1}]}'
        result=context.strict_json_object(raw)
        self.assertIs(type(result['integer']),int);self.assertIs(type(result['boolean']),bool)
        self.assertIs(type(result['fraction']),float);self.assertEqual(result['text'],'\u00e9')
        self.assertEqual(result['nested'],[{'a':1}])
        for bad in self.BAD_JSON:
            with self.subTest(raw=bad),self.assertRaises(ValueError):context.strict_json_object(bad)

    def test_conflicting_duplicate_manifest_fails_before_reconstruction(self):
        manifest=dict(schema='clash95_framed_modal_primary_candidate_v1',stage=context.builder.STAGE,
                      recipe_revision=context.builder.REVISION,resolution='800x600',nested={'span':1})
        normal=json.dumps(manifest)
        variants=['{"stage":"wrong",'+normal[1:],
                  normal.replace('"span": 1','"span": false, "span": 1')]
        with tempfile.TemporaryDirectory(prefix='primary-json-') as folder:
            path=Path(folder)/'candidate.candidate.json'
            path.with_name('candidate.exe').write_bytes(b'image');path.with_name('candidate.cdb').write_bytes(b'probe')
            for bad in variants:
                path.write_text(bad,encoding='utf-8')
                with patch.object(context.builder,'build_candidate',side_effect=AssertionError('ambiguous JSON reached rebuild')) as rebuild:
                    with self.assertRaisesRegex(ValueError,'duplicate'):context.load_context(b'original',b'image',path)
                    rebuild.assert_not_called()
                self.assertEqual(path.read_text(encoding='utf-8'),bad)

    def test_packet_clis_reject_malformed_json_before_evaluation(self):
        import modal_primary_barracks_trace as trace
        import modal_primary_capture as capture
        with tempfile.TemporaryDirectory(prefix='primary-packet-') as folder:
            paths={name:Path(folder)/(name+'.txt') for name in ('original','candidate','log','packet','probe')}
            for name,path in paths.items():path.write_bytes(name.encode('ascii'))
            args=[arg for name,path in paths.items() for arg in ('--'+name,str(path))]
            for bad in self.BAD_JSON:
                paths['packet'].write_bytes(bad)
                for module in (trace,capture):
                    with self.subTest(raw=bad,module=module.__name__),redirect_stdout(io.StringIO()) as output, \
                         patch.object(module,'evaluate_trace',side_effect=AssertionError('ambiguous packet reached evaluation')) as evaluate, \
                         patch.object(sys,'argv',['tool',*args]):
                        code=module.main() if module is trace else module.main(args)
                    self.assertEqual(code,2);report=json.loads(output.getvalue())
                    self.assertFalse(report['passed']);self.assertFalse(report['ready_for_host_capture'])
                    self.assertTrue(report['failures']);evaluate.assert_not_called()
                self.assertEqual(paths['packet'].read_bytes(),bad)

    def test_artifact_and_proxy_json_use_the_same_admission(self):
        import modal_primary_capture as capture
        with tempfile.TemporaryDirectory(prefix='primary-artifact-') as folder:
            path=Path(folder)/'artifact.json'
            for bad in self.BAD_JSON:
                path.write_bytes(bad)
                for load in (capture.Artifacts().json,capture.proxy_context):
                    with self.subTest(raw=bad,load=load.__name__),self.assertRaises(ValueError):load(path)
                self.assertEqual(path.read_bytes(),bad)

    def test_every_prefixed_namespace_row_is_retained_and_rejected(self):
        log,packet,_=native_fixture()
        for name,namespace,row in admission_trace_mutations(log):
            changed=log+row+'\n';before=changed
            seq,_,primary=NativeSequenceTests().evaluate(changed,packet)
            report=seq if namespace=='MCAP_' else primary
            with self.subTest(name=name):
                self.assertFalse(report['sequence_passed'] if namespace=='MCAP_' else report['passed'])
                self.assertTrue(report['failures'])
                self.assertEqual(report['raw_records'][-1]['text'],row)
                self.assertEqual(report['raw_records'][-1]['line'],len(changed.splitlines()))
                self.assertEqual(changed,before)

    def test_debugger_failure_vocabulary_matches_host_and_retains_every_failure(self):
        import modal_primary_barracks_trace as trace
        host=(trace.producer.builder.ROOT/'scripts/cdb/run_modal_primary_capture.ps1').read_text(encoding='utf-8')
        function=host.split('function Get-CanvasDebuggerCommandFailure',1)[1].split('\nfunction ',1)[0]
        self.assertIn(trace.DEBUGGER_COMMAND_FAILURE.pattern,function)
        log,packet,_=native_fixture()
        changed=log+'\n'.join(DEBUGGER_FAILURE_ROWS)+'\n'
        report=trace.evaluate_sequence(changed,packet)
        self.assertFalse(report['sequence_passed'])
        self.assertEqual([r['text'] for r in report['debugger_failure_records']],list(DEBUGGER_FAILURE_ROWS))
        self.assertEqual([r['line'] for r in report['debugger_failure_records']],
                         list(range(len(log.splitlines())+1,len(changed.splitlines())+1)))
        for row in DEBUGGER_FAILURE_ROWS:
            self.assertRegex(row,trace.DEBUGGER_COMMAND_FAILURE)
        self.assertIsNone(trace.DEBUGGER_COMMAND_FAILURE.search('echo "Unable to insert breakpoint"'))
        self.assertIsNone(trace.DEBUGGER_COMMAND_FAILURE.search('echo "Command file execution failed"'))

    def test_startup_and_inherited_markers_cannot_hide_in_prefixed_rows(self):
        import modal_primary_barracks_trace as trace
        log,packet,_=native_fixture()
        baseline=trace.evaluate_sequence(log,packet)
        self.assertTrue(baseline['sequence_passed'],baseline['failures'])
        self.assertIn('protocol=primary_barracks_owned_canvas_v1',log)
        for field,row in startup_admission_mutations(log):
            changed=log+row+'\n'
            with self.subTest(row=row):
                report=trace.evaluate_sequence(changed,packet)
                self.assertFalse(report['sequence_passed']);self.assertTrue(report['failures'])
                self.assertEqual(report[field][-1],dict(line=len(changed.splitlines()),text=row))

    def test_rejected_rows_cannot_keep_an_authenticated_trace_passing(self):
        trace,log,packet=BindingBoundaryTests().fixture()
        rows=([row for _,_,row in admission_trace_mutations(log)]+list(DEBUGGER_FAILURE_ROWS)
              +[row for _,row in startup_admission_mutations(log)])
        for row in rows:
            with self.subTest(row=row),patch.object(trace.producer,'build_screen_probe',return_value=packet), \
                 patch.object(trace,'compile_probe',return_value='canonical'):
                report=trace.evaluate_trace(log+row+'\n',original=b'original',candidate=b'candidate',
                    packet=packet,generated_probe=b'canonical')
            self.assertTrue(report['source_authenticated']) # Synthetic identity seam only.
            self.assertFalse(report['passed']);self.assertFalse(report['ready_for_host_capture'])
            self.assertFalse(report['runtime_accepted']);self.assertTrue(report['failures'])

    def test_actual_primary_parser_rejects_prefixed_duplicate_and_failure_rows(self):
        import test_modal_primary_capture as capture_fixture
        for checkpoint in capture_fixture.tool.CHECKPOINTS:
            log,packet=capture_fixture.sequence_fixture(checkpoint)
            baseline=capture_fixture.SequenceTests().evaluate(log,packet,checkpoint)
            self.assertTrue(baseline['passed'])
            for name,row in primary_admission_mutations(log):
                changed=log+row+'\n';before=changed
                with self.subTest(checkpoint=checkpoint,name=name),self.assertRaisesRegex(ValueError,'primary observation') as caught:
                    capture_fixture.SequenceTests().evaluate(changed,packet,checkpoint)
                self.assertEqual(changed,before)
                self.assertIsInstance(caught.exception,capture_fixture.tool.PrimaryObservationError)
                expected=[dict(line=n,marker=line.split(' ',1)[0],text=line)
                          for n,line in enumerate(changed.splitlines(),1) if re.search(r'MPRI_',line,re.I)]
                self.assertEqual(caught.exception.raw_records,expected)

    def surface_fixture(self,root,bad,boundary):
        """Mock only prior file/identity gates to reach each actual JSON callsite."""
        root=root.resolve()
        import modal_primary_surface_audit as audit
        import modal_primary_capture as capture
        roles={'original':'original_sha256','input_candidate':'candidate_sha256','candidate_path':'candidate_sha256',
            'candidate_manifest':'candidate_manifest_sha256','proxy_input':'proxy_sha256','proxy_path':'proxy_sha256',
            'proxy_manifest':'proxy_manifest_sha256','python':'python_sha256','cdb':'cdb_sha256',
            **{role:('host_sha256' if role=='host_path' else role+'_sha256') for role in audit.SOURCE_PATHS}}
        plan=dict(schema='clash95_modal_primary_capture_plan_v1',out_dir=str(root),run_id=root.name,
            child_environment=dict(CLASH_PROXY_PRESENT='0',parent_environment_modified=False),
            manual_input_proof=False,visible_composition_proof=False,promotion_ready=False)
        for role,digest in roles.items():plan[role]=str(root/role);plan[digest]='a'*64
        for role,relative in audit.SOURCE_PATHS.items():plan[role]=str(audit.ROOT/relative)
        plan['candidate_manifest']=str(root/'candidate.candidate.json')
        proxy=json.dumps(dict(output=plan['proxy_input'],source=str(root/'proxy.cpp'))).encode()
        if boundary=='proxy':proxy=bad
        ready={name:str(root/('primary-'+name+'.cdb')) for name in capture.CHECKPOINTS}
        packet=dict(capture_source_hashes={},primary_capture=dict(source_hashes={},ready_files=ready,
            proxy_manifest=dict(path=plan['proxy_manifest'],sha256=capture.sha(proxy))),
            candidate_manifest=dict(path=plan['candidate_manifest'],sha256=plan['candidate_manifest_sha256']),
            stage='synthetic',resolution='800x600',castle_index=0,availability='construct_all',minimap_viewport=True,
            candidate_sha256='a'*64,original_sha256='a'*64,canvas_state_va=1,canvas_state_offsets={},stop_va=2,
            checkpoints=[],route={'name':'barracks'})
        for key in ('stage','resolution','castle_index','availability','minimap_viewport','candidate_sha256','original_sha256',
                    'canvas_state_va','canvas_state_offsets','stop_va','checkpoints'):plan[key]=packet[key]
        plan.update(route='barracks',probe_sha256=capture.sha(b'probe'),width=800,height=600,
                    primary_ready_scripts={n:{} for n in ready},work_dir=str(root))
        payload={'packet':bad if boundary=='packet' else json.dumps(packet).encode(),
                 'probe':b'probe','final':b'prefix','prefix':b'prefix','trace':bad}
        receipt=dict(schema='clash95_modal_primary_triplet_v1',failures=[],manual_input_proof=False,promotion_ready=False,
            plan=plan,packet={'role':'packet'},probe={'role':'probe'},final_log={'role':'final','capture_prefix_preserved':True},
            checkpoints=[dict(name=n,index=i,prefix={'role':'prefix'},trace={'role':'trace'})
                         for i,n in enumerate(capture.CHECKPOINTS)])
        class Reader:
            def read(self,path,**kwargs):return proxy if str(path)==plan['proxy_manifest'] else b'file'
            def artifact(self,record,**kwargs):return payload[record['role']] if 'role' in record else b'file'
        return audit,receipt,Reader()

    def test_surface_packet_proxy_and_retained_trace_consume_strict_raw_json(self):
        import modal_primary_capture as capture
        strict=capture.route.strict_json_object
        with tempfile.TemporaryDirectory(prefix='primary-surface-json-') as folder:
            for boundary in ('packet','proxy','trace'):
                for bad in self.BAD_JSON:
                    audit,receipt,reader=self.surface_fixture(Path(folder),bad,boundary)
                    with self.subTest(boundary=boundary,bad=bad), \
                         patch.object(capture.route,'strict_json_object',wraps=strict) as observed, \
                         patch.object(capture,'evaluate_trace',return_value={}), \
                         patch.object(audit,'owned_cleanup',return_value={}),patch.object(audit,'source_assets',return_value={}):
                        with self.assertRaises(ValueError):audit.bind_triplet(receipt,reader=reader)
                    self.assertEqual(observed.call_args.args,(bad,))
                    self.assertTrue(all(type(call.args[0]) is bytes for call in observed.call_args_list))

    def test_surface_summary_triplet_uses_strict_hashed_artifact_bytes(self):
        import modal_primary_surface_audit as audit
        import modal_primary_capture as capture
        strict=capture.route.strict_json_object
        with tempfile.TemporaryDirectory(prefix='primary-summary-json-') as folder:
            root=Path(folder);triplet=root/'primary-triplet.json';summary=root/'summary.json'
            for bad in self.BAD_JSON:
                triplet.write_bytes(bad)
                row=dict(schema='clash95_modal_primary_capture_v1',passed=True,executed=True,failures=[],
                    manual_input_proof=False,visible_composition_proof=False,promotion_ready=False,plan={'out_dir':str(root)},
                    primary_triplet=dict(path=str(triplet),sha256=capture.sha(bad),bytes=len(bad)))
                summary.write_text(json.dumps(row),encoding='utf-8')
                with self.subTest(bad=bad),patch.object(capture.route,'strict_json_object',wraps=strict) as observed, \
                     patch.object(audit,'bind_triplet',side_effect=AssertionError('ambiguous triplet reached binding')) as bind:
                    report=audit.evaluate(summary)
                self.assertFalse(report['passed']);self.assertFalse(report['source_authenticated'])
                self.assertTrue(report['failures']);bind.assert_not_called()
                self.assertEqual(observed.call_args.args,(bad,));self.assertEqual(triplet.read_bytes(),bad)

    def test_primary_failure_diagnostics_survive_cli_and_surface_report_boundaries(self):
        import test_modal_primary_capture as capture_fixture
        import modal_primary_surface_audit as audit
        capture=capture_fixture.tool
        log,packet=capture_fixture.sequence_fixture()
        changed=log+'x_MPRI_REJECT invalid_primary\nx_MPRI_REJECT invalid_primary\n'
        with self.assertRaises(capture.PrimaryObservationError) as caught:
            capture_fixture.SequenceTests().evaluate(changed,packet)
        failure=caught.exception
        with tempfile.TemporaryDirectory(prefix='primary-error-records-') as folder:
            root=Path(folder);paths={name:root/(name+'.txt') for name in ('original','candidate','log','packet','probe')}
            for name,path in paths.items():path.write_bytes(name.encode())
            paths['packet'].write_text(json.dumps({'primary_capture':{'ready_files':{}}}))
            args=[arg for name,path in paths.items() for arg in ('--'+name,str(path))]
            with patch.object(capture,'evaluate_trace',side_effect=failure),redirect_stdout(io.StringIO()) as output:
                self.assertEqual(capture.main(args),2)
            report=json.loads(output.getvalue());self.assertFalse(report['passed'])
            self.assertEqual(report['primary_observation_records'],failure.raw_records)
            self.assertEqual(report['primary_route_diagnostics'],failure.route_report)
            triplet=root/'primary-triplet.json';summary=root/'summary.json'
            same={key:None for key in ('checkpoints','snapshots','clean_stable_pair','cdb','candidates','cleanup',
                                      'packet','probe','capture_prefix','final_log')}
            same['plan']={'out_dir':str(root)};raw=json.dumps(same).encode();triplet.write_bytes(raw)
            row=dict(same,schema='clash95_modal_primary_capture_v1',passed=True,executed=True,failures=[],
                manual_input_proof=False,visible_composition_proof=False,promotion_ready=False,
                primary_triplet=dict(path=str(triplet),sha256=capture.sha(raw),bytes=len(raw)))
            summary.write_text(json.dumps(row))
            with patch.object(audit,'bind_triplet',side_effect=failure):report=audit.evaluate(summary)
            self.assertFalse(report['passed']);self.assertEqual(report['primary_observation_records'],failure.raw_records)
            self.assertEqual(report['primary_route_diagnostics'],failure.route_report)

    def test_core_rejections_retain_every_route_and_primary_record_at_both_consumers(self):
        import test_modal_primary_capture as capture_fixture
        import modal_primary_surface_audit as audit
        capture=capture_fixture.tool
        for checkpoint in capture.CHECKPOINTS:
            log,packet=capture_fixture.sequence_fixture(checkpoint)
            changed=log+'\n'.join(CORE_REJECTION_ROWS)+'\n'
            sequence=capture.route.evaluate_sequence(changed,packet,checkpoint=checkpoint)
            slots=capture.route.evaluate_slots(changed,packet,sequence,checkpoint=checkpoint)
            primary=capture.route.evaluate_primary_route(changed,packet,sequence,checkpoint=checkpoint)
            reports=dict(modal_sequence=sequence,slot_trace=slots,primary_route_sequence=primary)
            failure=dict(reports,passed=False,failures=sequence['failures']+slots['failures']+primary['failures'])
            self.assertFalse(sequence['sequence_passed']);self.assertTrue(failure['failures'])
            for key in ('raw_records','debugger_failure_records','forbidden_stage_records','primary_startup_records'):
                self.assertTrue(sequence[key])
            expected=[dict(line=n,marker=line.split(' ',1)[0],text=line)
                      for n,line in enumerate(changed.splitlines(),1) if re.search(r'MPRI_',line,re.I)]
            with self.subTest(checkpoint=checkpoint,consumer='bound prefix'),self.assertRaises(capture.PrimaryObservationError) as caught:
                audit.bound_capture_report(changed.encode(),packet,{'candidate_sha256':packet['candidate_sha256']},checkpoint)
            self.assertEqual(caught.exception.raw_records,expected);self.assertEqual(caught.exception.route_report,reports)
            with tempfile.TemporaryDirectory(prefix='primary-core-reject-') as folder:
                root=Path(folder);paths={name:root/(name+'.txt') for name in ('original','candidate','log','packet','probe')}
                for name,path in paths.items():path.write_bytes(name.encode())
                scripts={name:root/('primary-'+name+'.cdb') for name in capture.CHECKPOINTS}
                packet['primary_capture']['ready_files']={name:str(path) for name,path in scripts.items()}
                for name,path in scripts.items():path.write_bytes(capture.ready_script(name,packet).encode('ascii'))
                paths['packet'].write_text(json.dumps(packet));paths['log'].write_bytes(changed.encode());paths['probe'].write_bytes(b'canonical\n')
                args=[arg for name,path in paths.items() for arg in ('--'+name,str(path))]+['--checkpoint',checkpoint]
                before=copy.deepcopy(failure)
                with patch.object(capture,'compile_probe',return_value='canonical\n'), \
                     patch.object(capture.route,'compile_probe',return_value='native\n'), \
                     patch.object(capture.route,'evaluate_trace',return_value=failure),redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(capture.main(args),2)
                report=json.loads(output.getvalue())
                self.assertFalse(report['passed']);self.assertFalse(report['ready_for_host_capture'])
                self.assertEqual(report['primary_observation_records'],expected)
                self.assertEqual(report['primary_route_diagnostics'],before)
                self.assertEqual(failure,before);self.assertEqual(paths['log'].read_bytes(),changed.encode())


@unittest.skipUnless(Path('C:/Clash/clash95.exe').is_file(), 'local original required for exact candidate reconstruction')
class ActualContextTests(unittest.TestCase):
    def test_real_1024_primary_candidate_reconstructs_without_recipe_projection(self):
        original=Path('C:/Clash/clash95.exe').read_bytes()
        # A historical sidecar binds the producer sources from its own run.
        # Build fresh inputs so current source authentication is exercised
        # without treating preserved historical bundles as fixture caches.
        image,manifest,probe=context.builder.build_candidate(original,'1024x768')
        with tempfile.TemporaryDirectory(prefix='primary-real-context-') as folder:
            path=Path(folder)/'candidate.candidate.json';path.write_text(json.dumps(manifest))
            path.with_name('candidate.exe').write_bytes(image);path.with_name('candidate.cdb').write_bytes(probe.encode())
            import modal_primary_barracks_trace as trace
            packet=trace.producer.build_screen_probe(original,image,candidate_sha256=hashlib.sha256(image).hexdigest(),
                stage=context.builder.STAGE,resolution='1024x768',route='barracks',availability='construct_all',castle_index=0,
                candidate_manifest=path,minimap_viewport=True)
            self.assertEqual(packet['candidate_manifest']['sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(packet['candidate_sha256'],hashlib.sha256(image).hexdigest())
            compiled=trace.compile_probe(packet)
            log,synthetic_packet,extra=native_fixture(packet=packet)
            self.assertEqual(synthetic_packet,packet)
            result=trace.evaluate_trace(log,original=original,candidate=image,packet=packet,generated_probe=compiled.encode('ascii'))
            self.assertTrue(result['passed'],result['failures']);self.assertTrue(result['source_authenticated'])
            self.assertTrue(result['initial_map_trace']['passed']);self.assertTrue(result['primary_route_sequence']['passed'])
            self.assertFalse(result['runtime_accepted']);self.assertFalse(result['cleanup_verified'])
            self.assertFalse(result['manual_input_proof']);self.assertFalse(result['promotion_ready'])
            self.assertNotIn('initial_map_projection',result)
            self.assertEqual(manifest['recipe_revision'],'owned_modal_primary_v1')
            self.assertNotEqual(manifest['stage'],manifest['base_candidate']['stage'])
            self.assertIn('MPRIMARY_CONTRACT_PASS stage='+manifest['stage'],probe)
            self.assertIn('PTILE_CONTRACT_PASS stage='+manifest['stage'],probe)
            self.assertNotIn('.echo SLOTS_CONTRACT_PASS',probe)
            self.assertFalse(manifest['primary_composition_proven'])


if __name__=='__main__':unittest.main()
