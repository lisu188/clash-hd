"""Offline primary consumer fixtures; no target execution or native API calls.

Synthetic packets exercise each boundary independently. They are never written
as runtime evidence. The frozen reader reuses its existing synthetic corpus.
"""
import copy
from dataclasses import replace
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest.mock import patch

import modal_slots_primary_capture as tool
import modal_slots_primary_surface as primary
import test_framed_primary_surface as reader_fixtures


def sequence_fixture():
    lines=['MPRI_NATIVE_CONTRACT_PASS','entry',
        'MPRI_LOCK_CALL tid=2345 esp=00300000 backend=20000000 surface=20001000 descriptor=20000038 rect=00000000 flags=1 event=00000000',
        'MPRI_LOCK_RETURN tid=2345 esp=00300014 backend=20000000 hr=0 surface=20001000 descriptor=20000038 pixels=22000000 size=(800,600) pitch=800',
        'MCAP_SURFDUMP_HOST_READY',
        'MPRI_READY tid=2345 eip=00433e77 esp=002ffffc backend=20000000 surface=20001000 palette=20002000 pixels=22000000 size=(800,600) pitch=800',
        'MPRI_HOST_READY']
    packet={'resolution':'800x600','route':{'name':'barracks'}}
    def evaluate(log):
        current=log.splitlines()
        source={'modal_sequence':{'raw_records':[
            {'marker':'MCAP_SCREEN_ENTRY','line':current.index('entry')+1},
            {'marker':'MCAP_SURFDUMP_HOST_READY','line':current.index('MCAP_SURFDUMP_HOST_READY')+1}]},
            'surface':{'tid':0x2345,'eip':0x433e77,'esp':0x2ffffc}}
        return tool.evaluate_primary_sequence(log,packet,source)
    return '\n'.join(lines)+'\n',packet,evaluate


class FrozenReaderTests(reader_fixtures.PrimarySurfaceTests):
    def setUp(self):
        self.addCleanup(patch.stopall)
        patch.object(reader_fixtures,'primary',primary).start()

    def test_exact_byte_preserved_reader_port(self):
        self.assertEqual((tool.ROOT/'tools/modal_slots_primary_surface.py').read_bytes(),
                         (tool.ROOT/'tools/framed_primary_surface.py').read_bytes())
        tool.check_pins()


class PrimaryProtocolTests(unittest.TestCase):
    def test_success_pairs_are_retained_and_tail_is_allowed(self):
        log,packet,evaluate=sequence_fixture()
        self.assertTrue(evaluate(log+'quit:\nntdll!DbgBreakPoint:\n')['passed'])
        pair='\n'.join(log.splitlines()[2:4])+'\n'
        result=evaluate(log.replace(pair,pair+pair))
        self.assertTrue(result['passed'],result['failures'])
        self.assertEqual(len(result['lock_pairs']),2)
        self.assertEqual(len(result['raw_records']),6)

    def test_missing_duplicate_malformed_and_unknown_records_fail(self):
        log,packet,evaluate=sequence_fixture();lines=log.splitlines()
        for index,line in enumerate(lines):
            if not line.startswith('MPRI_'):continue
            for mutated in (lines[:index]+lines[index+1:],lines[:index]+[line]+lines[index:],
                            lines[:index]+['0:000> '+line]+lines[index+1:]):
                with self.subTest(index=index):self.assertFalse(evaluate('\n'.join(mutated))['passed'])
        self.assertFalse(evaluate(log+'MPRI_UNKNOWN\n')['passed'])

    def test_current_native_lock_stack_dimensions_and_identity_are_required(self):
        log,packet,evaluate=sequence_fixture()
        for old,new in [('esp=00300014','esp=00300010'),('rect=00000000','rect=12340000'),('flags=1','flags=2'),
                        ('event=00000000','event=00000001'),('hr=0','hr=80004005'),('pitch=800','pitch=640'),
                        ('descriptor=20000038','descriptor=2000003c'),('pixels=22000000','pixels=fffff000'),
                        ('palette=20002000','palette=00000000'),('eip=00433e77','eip=00433e78')]:
            with self.subTest(new=new):self.assertFalse(evaluate(log.replace(old,new))['passed'])
        pair='\n'.join(log.splitlines()[2:4])+'\n'
        self.assertFalse(evaluate(log.replace(pair,'').replace('entry\n',pair+'entry\n'))['passed'])

    def test_additions_only_observe_attached_explicit_breakpoints(self):
        commands,ready,checks=tool.additions()
        self.assertEqual(re.findall(r'^bp(\d+)\s+([0-9a-f]+)',commands,re.M),[('110','0047386f'),('111','00473872')])
        for text in (commands,ready,checks):
            self.assertNotIn('.call',text);self.assertNotIn('r @',text)
            self.assertIsNone(re.search(r'(?i)(?:^|[;{}])\s*(?:ed|eb|ew|eq)\s+',text))

    def test_whole_probe_reconstruction_cannot_hide_inherited_trace_failure(self):
        log,packet,evaluate=sequence_fixture()
        packet.update(candidate_sha256='a'*64,stage='slots-validation',availability='existing_flags',
            castle_index=0,minimap_viewport=True,candidate_manifest={'path':'fixture.json'},
            primary_capture={'ready_file':'fixture.cdb','proxy_manifest':{'path':'proxy.json'}})
        prepared={'packet':copy.deepcopy(packet),'probe':'canonical\n','ready_script':'ready\n'}
        bad={'source':{},'failures':['initial trace: unmatched event 498/501'],'passed':False,'limits':[]}
        with patch.object(tool,'prepare',return_value=prepared),patch.object(tool.modal,'compile_probe',return_value='base\n'), \
             patch.object(tool.modal,'evaluate_trace',side_effect=lambda *a,**kw:copy.deepcopy(bad)), \
             patch.object(tool,'evaluate_primary_sequence',return_value={'passed':True,'failures':[]}):
            result=tool.evaluate_trace(log,original=b'original',candidate=b'candidate',packet=packet,
                generated_probe=b'canonical\n',ready_script_bytes=b'ready\n')
            self.assertFalse(result['passed']);self.assertFalse(result['ready_for_host_capture'])
            self.assertEqual(result['failures'],bad['failures'])
            for probe,ready in ((b'canonical\ng\n',b'ready\n'),(b'canonical\n',b'ready\ng\n')):
                with self.assertRaisesRegex(ValueError,'whole primary packet/probe'):
                    tool.evaluate_trace(log,original=b'original',candidate=b'candidate',packet=packet,
                        generated_probe=probe,ready_script_bytes=ready)


class FinalLogTests(unittest.TestCase):
    def test_host_failure_changed_prefix_tail_and_rehashed_failure_cannot_pass(self):
        with tempfile.TemporaryDirectory(prefix='slots-primary-final-') as directory:
            root=Path(directory).resolve()
            def artifact(name,data):
                path=root/name;path.write_bytes(data)
                return dict(path=str(path),bytes=len(data),sha256=tool.sha(data))
            prefix=artifact('capture-prefix.log',b'paused\n');final=artifact('cdb.log',b'paused\nquit:\n')
            final['capture_prefix_preserved']=True
            original=artifact('original.bin',b'original');candidate=artifact('candidate.bin',b'candidate')
            receipt=dict(plan={'out_dir':directory,'original':original['path'],'candidate_path':candidate['path']},
                failures=[],capture_prefix=prefix,final_log=final)
            def run(value):return tool.audit_final_log(value,packet={},probe=b'probe',ready_bytes=b'ready')
            with patch.object(tool,'evaluate_trace',return_value={'passed':True,'failures':[]}) as verify:
                self.assertTrue(run(receipt)['complete_final_trace_passed'])
                self.assertEqual(verify.call_args.args[0],'paused\nquit:\n')
                for key,value in [('failures',['original trace failure']),('failures',None)]:
                    changed=copy.deepcopy(receipt);changed[key]=value
                    with self.assertRaises(ValueError):run(changed)
                for field,value in [('sha256','0'*64),('bytes',1),('capture_prefix_preserved',False)]:
                    changed=copy.deepcopy(receipt);changed['final_log'][field]=value
                    with self.assertRaises(ValueError):run(changed)
                changed=copy.deepcopy(receipt);changed['final_log']=dict(artifact('cdb.log',b'changed\nquit:\n'),capture_prefix_preserved=True)
                with self.assertRaisesRegex(ValueError,'actual paused prefix'):run(changed)
            receipt['final_log']=dict(artifact('cdb.log',b'paused\nMPRI_LOCK_RETURN malformed\n'),capture_prefix_preserved=True)
            with patch.object(tool,'evaluate_trace',return_value={'passed':False,'failures':['unmatched return']}):
                with self.assertRaisesRegex(ValueError,'unmatched return'):run(receipt)


class ProxyManifestTests(unittest.TestCase):
    def test_manifest_requires_actual_output_and_recorded_current_source(self):
        with tempfile.TemporaryDirectory(prefix='slots-proxy-context-') as directory:
            root=Path(directory).resolve();dll=root/'ddraw.dll';dll.write_bytes(b'synthetic never loaded')
            source=tool.ROOT/'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp'
            source_hash=tool.sha(source.read_bytes());digest=tool.sha(dll.read_bytes())
            path=root/'proxy.json';manifest=dict(generated_by='clash-hd-surface-dump-proxy',output=str(dll),
                source=str(source),source_sha256=source_hash,output_sha256=digest)
            with patch.multiple(primary,SUPPORTED_PROXY_SHA256=digest,SUPPORTED_PROXY_SOURCE_SHA256=source_hash), \
                 patch.object(primary,'_Proxy') as pe:
                pe.return_value.raw.return_value=tool.GET_PALETTE_BYTES
                path.write_text(json.dumps(manifest));self.assertEqual(tool.proxy_context(path)['proxy_sha256'],digest)
                for key,value in [('generated_by','self-declared'),('source_sha256','0'*64),('output_sha256','0'*64)]:
                    path.write_text(json.dumps(dict(manifest,**{key:value})))
                    with self.assertRaises(ValueError):tool.proxy_context(path)
                path.write_text(json.dumps(manifest));dll.write_bytes(b'changed even with same manifest')
                with self.assertRaises(ValueError):tool.proxy_context(path)


class TripletTests(unittest.TestCase):
    """Actual file/hash/PE/read checks, with only final native trace mocked.

    Whole trace reconstruction is tested separately. Synthetic host identities
    and bytes below are test inputs, never affirmative runtime observations.
    """
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='slots-primary-triplet-')
        # Match canonical packet paths when Windows TEMP has a short-name alias.
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        self.addCleanup(patch.stopall)
        patch.object(reader_fixtures,'primary',primary).start()
        image=bytearray(reader_fixtures.synthetic_proxy());image[0x300:0x300+len(tool.GET_PALETTE_BYTES)]=tool.GET_PALETTE_BYTES
        self.image=bytes(image);digest=tool.sha(self.image)
        patch.multiple(primary,SUPPORTED_PROXY_SHA256=digest,SURFACE_VTABLE_RVA=0x2000,PALETTE_VTABLE_RVA=0x2100).start()
        patch.object(tool,'GET_PALETTE_RVA',0x1100).start()
        self.final=patch.object(tool,'evaluate_trace',return_value={'passed':True,'failures':[]}).start()
        def save(name,data,**fields):
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            return dict(path=str(path),bytes=len(data),sha256=tool.sha(data),**fields)
        self.save=save
        log,_,evaluate=sequence_fixture();sequence=evaluate(log)
        prefix=save('capture-prefix.log',log.encode());final=save('cdb.log',(log+'quit:\n').encode());final['capture_prefix_preserved']=True
        original=save('original.bin',b'original');candidate=save('candidate.bin',b'candidate');proxy=save('ddraw.bin',self.image)
        sidecar=save('candidate.json',b'{}');proxy_manifest=save('proxy.json',b'{}')
        probe=save('modal-slots-barracks.cdb',b'probe');ready_file=save('primary-ready.cdb',b'ready')
        self.packet=dict(stage='slots-validation',resolution='800x600',castle_index=0,availability='existing_flags',
            minimap_viewport=True,candidate_sha256=candidate['sha256'],original_sha256=original['sha256'],
            canvas_state_va=0x596000,canvas_state_offsets=tool.modal.producer.canvas.STATE,stop_va=0x433e77,
            route={'name':'barracks'},candidate_manifest={'path':sidecar['path'],'sha256':sidecar['sha256']},
            primary_capture={'ready_file':ready_file['path'],'source_hashes':{},
                'proxy_manifest':{'path':proxy_manifest['path'],'sha256':proxy_manifest['sha256']}})
        plan={k:v for k,v in self.packet.items() if k not in ('route','candidate_manifest','primary_capture')}
        plan.update(schema='clash95_modal_slots_primary_capture_plan_v1',route='barracks',width=800,height=600,out_dir=str(self.root),
            primary_ready_path=ready_file['path'],primary_ready_sha256=ready_file['sha256'],probe_sha256=probe['sha256'])
        source_paths={'host_path':'scripts/cdb/run_modal_slots_primary_capture.ps1','producer':'tools/modal_slots_primary_capture.py',
            'trace':'tools/modal_slots_primary_capture.py','primary_source':'tools/modal_slots_primary_surface.py',
            'converter':'tools/cdb_surface_dump_to_png.py','proxy_source':'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp'}
        for name,relative in source_paths.items():
            path=tool.ROOT/relative;plan[name]=str(path);plan['host_sha256' if name=='host_path' else name+'_sha256']=tool.sha(path.read_bytes())
        for name,key,record in [('original','original_sha256',original),('input_candidate','candidate_sha256',candidate),
                ('candidate_path','candidate_sha256',candidate),('candidate_manifest','candidate_manifest_sha256',sidecar),
                ('proxy_input','proxy_sha256',proxy),('proxy_path','proxy_sha256',proxy),('proxy_manifest','proxy_manifest_sha256',proxy_manifest),
                ('python','python_sha256',original),('cdb','cdb_sha256',original)]:
            plan[name]=record['path'];plan[key]=record['sha256']
        debugger=dict(process_id=10,creation_filetime=100,handle_retained=True,path=plan['cdb'])
        owner=dict(process_id=11,creation_filetime=101,creation_utc='2026-09-13T00:00:00Z',handle_retained=True,
            parent_process_id=10,path=plan['candidate_path'],candidate_sha256=candidate['sha256'])
        ready=dict(event='READY',physical=0x25000000,native=0x26000000,physical_pixels=0x27000000,
            native_pixels=0x28000000,root_esp=0x2ffffc,tid=0x2345)
        self.trace=dict(passed=True,candidate_sha256=candidate['sha256'],primary_sequence=sequence,
            modal_sequence={'raw_records':[{'marker':'MCAP_CANVAS','values':ready}]},
            source=dict(log_raw_sha256=prefix['sha256'],generated_probe_sha256=probe['sha256'],primary_ready_script_sha256=ready_file['sha256']))
        state=reader_fixtures.fixture()['before'];base=0x10000000
        surface_full=bytearray(32);struct.pack_into('<I',surface_full,0,base+0x2000);struct.pack_into('<I',surface_full,28,state.palette.address)
        reads={k:getattr(state,k) for k in state.__dataclass_fields__}
        reads.update(surface_full=primary.Read(state.surface.address,bytes(surface_full)),proxy_header=primary.Read(base,self.image[:512]),
            proxy_getpalette=primary.Read(base+tool.GET_PALETTE_RVA,tool.GET_PALETTE_BYTES))
        native=bytes((x+y)%251+1 for y in range(480) for x in range(640));physical=bytearray(800*600)
        for y in range(480):physical[(y+60)*800+80:(y+60)*800+720]=native[y*640:(y+1)*640]
        canvas=bytearray(128)
        expected=dict(phase=1,physical=ready['physical'],native=ready['native'],root_esp=ready['root_esp'],owner_tid=ready['tid'],
            enter_status=1,mirror_status=1,leave_status=0,fault=0,allocations=1,frees=0,mirrors=3,pending_header=0,
            pending_pixels=0,native_pixels=ready['native_pixels'],physical_pixels=ready['physical_pixels'])
        for key,value in expected.items():struct.pack_into('<I',canvas,plan['canvas_state_offsets'][key],value)
        def header(width,height,pointer):
            data=bytearray(188);struct.pack_into('<HHI',data,0,width,height,pointer);struct.pack_into('<I',data,184,0x50ee24);return bytes(data)
        canvas_reads={'state':primary.Read(plan['canvas_state_va'],bytes(canvas)),
            'e0':primary.Read(0x5202e0,struct.pack('<I',ready['native'])),
            'physical_header':primary.Read(ready['physical'],header(800,600,ready['physical_pixels'])),
            'native_header':primary.Read(ready['native'],header(640,480,ready['native_pixels']))}
        samples=[]
        for index in range(1,4):
            folder=f'capture-{index}'
            def records(prefix,values):
                return {phase:{name:save(f'{folder}/{prefix}-{phase}-{name}.raw',read.data,address=read.address)
                    for name,read in values.items()} for phase in ('before','after')}
            sample=dict(run_id=self.root.name,game_identity=owner,trace_sha256=prefix['sha256'],paused=True,
                proxy_module=dict(base=base,size=0x4000,path=plan['proxy_path'],sha256=digest),reads=records('primary',reads),
                pixels=save(f'{folder}/primary.raw',bytes(800*600),address=0x22000000),
                palette_entries=save(f'{folder}/primary-palette.bin',state.palette.data[12:]),
                regions=[dict(address=r.address,size=r.size,state=r.state,protect=r.protect) for r in reader_fixtures.fixture()['regions']])
            row=save(f'{folder}/surface.raw',bytes(physical),width=800,height=600,pitch=800,game_identity=owner,paused=True,
                capture='owned_physical_mirror',physical=ready['physical'],physical_pixels=ready['physical_pixels'],primary=sample,
                native=save(f'{folder}/native-surface.raw',native,width=640,height=480,pitch=640,surface=ready['native'],base=ready['native_pixels']),
                reads=records('surface',canvas_reads))
            samples.append(row)
        self.receipt=dict(schema='clash95_slots_primary_triplet_v1',plan=plan,cdb=debugger,candidates=[owner],
            cleanup=dict(desktop_closed=True,cdb={'identity':debugger,'absent':True,'handle_closed':True},
                         candidates=[{'identity':owner,'absent':True,'handle_closed':True}]),
            clean_stable_pair=True,snapshots=samples,packet=save('packet.json',json.dumps(self.packet).encode()),probe=probe,
            capture_prefix=prefix,final_log=final,failures=[])

    def evaluate(self,receipt=None):
        return tool.audit_triplet(receipt or self.receipt,proxy_image=self.image,trace=self.trace,packet=self.packet)

    def test_three_matched_native_physical_primary_samples_are_bound(self):
        result=self.evaluate()
        self.assertTrue(result['three_matched_captures']);self.assertEqual(len(result['samples']),3)
        for key in ('primary_composition_proven','visible_composition_proof','manual_input_proof','native_modal_exit_proven','promotion_ready'):
            self.assertIs(result[key],False)

    def test_mixed_capture_geometry_ownership_palette_module_and_cleanup_fail(self):
        cases=[('missing',lambda r:r['snapshots'].pop()),('unstable',lambda r:r.update(clean_stable_pair=False)),
            ('cleanup',lambda r:r['cleanup']['cdb'].update(absent=False)),('initial_failure',lambda r:r['failures'].append('initial failure')),
            ('geometry',lambda r:r['snapshots'][0].update(width=1024)),('native_pointer',lambda r:r['snapshots'][0]['native'].update(base=0)),
            ('primary_process',lambda r:r['snapshots'][0]['primary'].update(game_identity=dict(r['candidates'][0],process_id=999))),
            ('module_extent',lambda r:r['snapshots'][0]['primary']['proxy_module'].update(size=1)),
            ('source_alias',lambda r:r['plan'].update(host_path=r['plan']['original'])),
            ('palette',lambda r:r['snapshots'][0]['primary']['palette_entries'].update(sha256='0'*64)),
            ('primary_hash',lambda r:r['snapshots'][0]['primary']['pixels'].update(sha256='0'*64)),
            ('header_alias',lambda r:r['snapshots'][2]['reads']['before'].update(state=r['snapshots'][0]['reads']['before']['state'])),
            ('primary_alias',lambda r:r['snapshots'][2]['primary']['reads']['before'].update(backend=r['snapshots'][0]['primary']['reads']['before']['backend']))]
        for name,mutate in cases:
            value=copy.deepcopy(self.receipt);mutate(value)
            with self.subTest(name=name),self.assertRaises(ValueError):self.evaluate(value)
        self.trace['passed']=False
        with self.assertRaisesRegex(ValueError,'whole initial'):self.evaluate()

    def test_rehashed_changed_primary_capture_and_missing_mirrored_slot_fail(self):
        for name in ('primary','physical'):
            row=self.receipt['snapshots'][1]
            record=row['primary']['pixels'] if name=='primary' else row
            path=Path(record['path']);old=path.read_bytes();changed=bytearray(old)
            changed[0 if name=='primary' else (75+60)*800+126+80]^=1
            path.write_bytes(changed);record['sha256']=tool.sha(changed)
            with self.subTest(name=name),self.assertRaises(ValueError):self.evaluate()
            path.write_bytes(old);record['sha256']=tool.sha(old)


if __name__=='__main__':unittest.main(verbosity=2)
