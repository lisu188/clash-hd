"""Offline primary-stage context/native-sequence fixtures; no game or debugger.

Synthetic records exercise parser boundaries only. One optional local-original
fixture reconstructs a real candidate; none of these logs is runtime evidence.
"""
from pathlib import Path
import copy
import hashlib
import json
import re
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


@unittest.skipUnless(Path('C:/Clash/clash95.exe').is_file(), 'local original required for exact candidate reconstruction')
class ActualContextTests(unittest.TestCase):
    def test_real_1024_primary_candidate_reconstructs_without_recipe_projection(self):
        original=Path('C:/Clash/clash95.exe').read_bytes()
        retained=Path('C:/ClashTests/hd-completion/modal-primary-1024x768-20260913-a/candidate.exe')
        if retained.is_file() and retained.with_suffix('.candidate.json').is_file() and retained.with_suffix('.cdb').is_file():
            # Reuse only input bytes. Both actual producer and validator below
            # independently rebuild/authenticate every byte and sidecar value.
            image=retained.read_bytes();manifest=json.loads(retained.with_suffix('.candidate.json').read_bytes())
            probe=retained.with_suffix('.cdb').read_text(encoding='utf-8')
        else:
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
