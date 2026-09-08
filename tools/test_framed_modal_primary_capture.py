"""Offline primary protocol fixtures; no game, debugger, COM or target process."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest.mock import patch

import framed_modal_primary_capture as tool
import framed_primary_surface as primary
import test_framed_modal_canvas_trace as fixture
import test_framed_primary_surface as snapshots


def log_fixture(route='barracks'):
    packet=fixture.small_packet(route,'construct_all');log=fixture.log_fixture(packet)
    return packet,add_primary(packet,log)


def add_primary(packet,log):
    route=packet['route']['name']
    modal=tool.modal.evaluate_sequence(log,packet);s=modal['surface']
    pair=(f"MPRI_LOCK_CALL tid={s['tid']:x} esp=00300000 backend=20000000 surface=20001000 descriptor=20000038 rect=00000000 flags=1 event=00000000\n"
          f"MPRI_LOCK_RETURN tid={s['tid']:x} esp=00300014 backend=20000000 hr=0 surface=20001000 descriptor=20000038 pixels=22000000 size=(800,600) pitch=800\n")
    ready=(f"MPRI_READY tid={s['tid']:x} eip={s['eip']:08x} esp={s['esp']:08x} backend=20000000 surface=20001000 palette=20002000 pixels=22000000 size=(800,600) pitch=800\nMPRI_HOST_READY\n")
    marker='MCAP_OVERVIEW_PRESENT_CALL' if route=='castle_overview' else 'MCAP_PRESENT_CALL'
    log='MPRI_NATIVE_CONTRACT_PASS\n'+log.replace(marker,pair+marker,1)+ready
    return log


def sequence(packet,log):
    modal=tool.modal.evaluate_sequence(log,packet)
    return tool.evaluate_primary_sequence(log,packet,dict(modal_sequence=modal,surface=modal['surface']))


class ProtocolTests(unittest.TestCase):
    def test_explicit_cdb_breakpoint_ids_are_attached_to_bp(self):
        # CDB bp[ID] Address grammar, independently reproduce the actual
        # failed run: spaced110/111 are addresses, not the requested IDs.
        def parse_declaration(line):
            match=re.match(r'^bp(?P<id>[0-9]*)\s+(?P<address>[0-9a-fA-F]+)\b',line)
            self.assertIsNotNone(match)
            return (int(match['id'],10) if match['id'] else None,int(match['address'],16))
        self.assertEqual(parse_declaration('bp 110 0047386f "gc"'),(None,0x110))
        self.assertEqual(parse_declaration('bp 111 00473872 "gc"'),(None,0x111))
        declarations=[line for line in tool.additions()[0].splitlines() if line.startswith('bp')]
        self.assertEqual([parse_declaration(line) for line in declarations],[(110,0x47386F),(111,0x473872)])
        self.assertEqual(tool.additions()[0].splitlines()[-1],'bd 110 111')

    def test_all_seven_routes_and_debugger_tail(self):
        for route in tool.modal.producer.ROUTES:
            packet,log=log_fixture(route)
            result=sequence(packet,log+'quit:\nntdll!DbgBreakPoint:\n')
            self.assertTrue(result['passed'],result['failures'])
            self.assertEqual(len(result['lock_pairs']),1)

    def test_missing_duplicate_and_malformed_every_primary_record(self):
        packet,log=log_fixture();lines=log.splitlines()
        for n,line in enumerate(lines):
            if not line.startswith('MPRI_'):continue
            for changed in (lines[:n]+lines[n+1:],lines[:n]+[line]+lines[n:],lines[:n]+['0:000> '+line]+lines[n+1:]):
                with self.subTest(line=line,mutation=len(changed)):
                    self.assertFalse(sequence(packet,'\n'.join(changed))['passed'])
        self.assertFalse(sequence(packet,log+'MPRI_UNKNOWN\n')['passed'])

    def test_lock_stack_full_rectangle_and_descriptor_negatives(self):
        packet,log=log_fixture()
        for old,new in [('esp=00300014','esp=00300010'),('rect=00000000','rect=12340000'),('flags=1','flags=2'),
                        ('event=00000000','event=00000001'),('hr=0','hr=80004005'),('pitch=800','pitch=640'),
                        ('descriptor=20000038','descriptor=2000003c'),('pixels=22000000','pixels=fffff000')]:
            with self.subTest(new=new):self.assertFalse(sequence(packet,log.replace(old,new))['passed'])

    def test_stale_lock_and_ready_identity_rejected(self):
        packet,log=log_fixture()
        pair=re.search(r'MPRI_LOCK_CALL.*\nMPRI_LOCK_RETURN.*\n',log)[0]
        stale=log.replace(pair,'').replace('MCAP_MAP_HANDOFF',pair+'MCAP_MAP_HANDOFF',1)
        self.assertFalse(sequence(packet,stale)['passed'])
        for old,new in [('surface=20001000','surface=20003000'),('palette=20002000','palette=00000000'),
                        ('pixels=22000000','pixels=22001000'),('tid=2345','tid=2346')]:
            lines=log.splitlines();n=next(i for i,s in enumerate(lines) if s.startswith('MPRI_READY'))
            lines[n]=lines[n].replace(old,new)
            self.assertFalse(sequence(packet,'\n'.join(lines))['passed'])

    def test_multiple_real_lock_pairs_preserved_and_unfinished_pair_rejected(self):
        packet,log=log_fixture();pair=re.search(r'MPRI_LOCK_CALL.*\nMPRI_LOCK_RETURN.*\n',log)[0]
        result=sequence(packet,log.replace(pair,pair+pair))
        self.assertTrue(result['passed'],result['failures']);self.assertEqual(len(result['lock_pairs']),2)
        self.assertFalse(sequence(packet,log.replace(pair,pair.splitlines()[0]+'\n'+pair))['passed'])

    def test_read_only_additions_and_pinned_native_proxy_method(self):
        commands,ready,checks=tool.additions()
        for text in (commands,ready,checks):
            self.assertIsNone(re.search(r'(?i)(?:^|[;{}])\s*(?:ed|eb|ew|eq)\s+|\br\s+@(?:eip|eax)\s*=',text))
            self.assertNotIn('r @',text)
            self.assertNotIn('.call',text)
        original=Path('C:/Clash/clash95.exe')
        proxy=Path('C:/ClashTests/hd-completion/framed-minimap-v1-1024x768-20260906-031649/candidate/ddraw.dll')
        if not original.is_file() or not proxy.is_file():self.skipTest('user-owned byte inputs unavailable')
        self.assertEqual(tool.modal.producer._read(original.read_bytes(),tool.LOCK_START,len(tool.LOCK_BYTES))[1],tool.LOCK_BYTES)
        pe=primary._Proxy(proxy.read_bytes(),primary.SUPPORTED_PROXY_SHA256,0x10000000)
        self.assertEqual(pe.raw(tool.GET_PALETTE_RVA,len(tool.GET_PALETTE_BYTES)),tool.GET_PALETTE_BYTES)
        self.assertIn(bytes.fromhex('8b421c8901'),tool.GET_PALETTE_BYTES)


class WholeBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path('C:/ClashCaptures/hd-completion/framed-modal-canvas-v2-barracks-1024x768-castle0-20260906-062843/plan.json')
        if not path.is_file():raise unittest.SkipTest('canonical existing candidate unavailable')
        cls.plan=json.loads(path.read_text(encoding='utf-8-sig'));p=cls.plan
        cls.original=Path(p['original']).read_bytes();cls.candidate=Path(p['input_candidate']).read_bytes()
        cls.kw=dict(candidate_sha256=p['candidate_sha256'],stage=p['stage'],resolution=p['resolution'],route=p['route'],
                    availability=p['availability'],castle_index=p['castle_index'],minimap_viewport=p['minimap_viewport'],
                    ready_file='C:/ClashCaptures/offline-primary-fixture/primary-ready.cdb')
        cls.prepared=tool.prepare(cls.original,cls.candidate,**cls.kw)

    def test_complete_canonical_compilation_and_dependency_pins(self):
        p=self.prepared;self.assertTrue(p['prepared']);self.assertFalse(p['runtime_ready'])
        self.assertTrue(all(len(line)<4096 for line in p['probe'].splitlines()))
        self.assertEqual(p['probe'].count('$$>a<\\"'+self.kw['ready_file']+'\\"'),1)
        # Nested BP quiet-file invocation must terminate before its .if brace.
        # The captured second failure had an existing, matching file but no
        # semicolon between its closing quote and the outer conditional body.
        self.assertEqual(p['probe'].count('$$>a<\\"'+self.kw['ready_file']+'\\"; }'),1)
        self.assertEqual(p['ready_script'],tool.ready_script())
        self.assertEqual(p['probe_sha256'],tool.sha(p['probe'].encode('ascii')))
        tool.check_pins()
        for unsafe in ('relative.cdb','C:/x/$arg1.cdb','C:/x/../y.cdb','C:/x/evil;g.cdb'):
            packet=copy.deepcopy(p['packet']);packet['primary_capture']['ready_file']=unsafe
            with self.assertRaises(ValueError):tool.compile_probe(packet)

    def test_attached_explicit_breakpoint_collision_fails(self):
        for declaration in ('bp110 12345678 "gc"','bp111 12345678 "gc"',
                            '  BP0110 12345678 "gc"'):
            with self.subTest(declaration=declaration),patch.object(tool.modal,'compile_probe',return_value=declaration+'\n'):
                with self.assertRaisesRegex(ValueError,'breakpoint IDs collide'):
                    tool.compile_probe(self.prepared['packet'])

    def test_actual_windows_outdir_is_normalized_only_in_cdb_serialization(self):
        packet=copy.deepcopy(self.prepared['packet'])
        windows_path=r'C:\ClashCaptures\hd-completion\primary-fixture-20260906-102300\primary-ready.cdb'
        packet['primary_capture']['ready_file']=windows_path
        saved=copy.deepcopy(packet)
        compiled=tool.compile_probe(packet)
        self.assertEqual(packet,saved,'Compiling CDB text mutated the bound host path')
        self.assertEqual(compiled.count('$$>a<\\"'+windows_path.replace('\\','/')+'\\"; }'),1)
        self.assertNotIn('$$>a<\\"'+windows_path,compiled)
        slash_packet=copy.deepcopy(packet)
        slash_packet['primary_capture']['ready_file']=windows_path.replace('\\','/')
        self.assertEqual(compiled,tool.compile_probe(slash_packet),'Equivalent actual host paths emitted different CDB command bytes')

    def test_altered_canonical_probe_and_candidate_fail(self):
        p=self.prepared
        with self.assertRaises(ValueError):tool.evaluate_trace('',original=self.original,candidate=self.candidate,
            packet=p['packet'],generated_probe=(p['probe']+'g\n').encode('ascii'),ready_script_bytes=tool.ready_script().encode('ascii'))
        changed=self.candidate[:-1]+bytes([self.candidate[-1]^1])
        with self.assertRaises(ValueError):tool.prepare(self.original,changed,**self.kw)

    def test_full_source_bound_positive_keeps_modal_and_initial_gates(self):
        fixture.FullBindingTests.setUpClass();f=fixture.FullBindingTests
        kw=dict(self.kw,resolution='800x600',route='school',availability='existing_flags',candidate_sha256=tool.sha(f.candidate))
        prepared=tool.prepare(f.original,f.candidate,**kw);log=add_primary(f.packet,f.log)
        result=tool.evaluate_trace(log,original=f.original,candidate=f.candidate,packet=prepared['packet'],
            generated_probe=prepared['probe'].encode('ascii'),ready_script_bytes=prepared['ready_script'].encode('ascii'))
        self.assertTrue(result['passed'],result['failures']);self.assertTrue(result['initial_map_trace']['passed'])
        self.assertTrue(result['modal_sequence']['sequence_passed']);self.assertFalse(result['runtime_accepted'])
        with self.assertRaises(ValueError):tool.evaluate_trace(log,original=f.original,candidate=f.candidate,packet=prepared['packet'],
            generated_probe=prepared['probe'].encode('ascii'),ready_script_bytes=(prepared['ready_script']+'g\n').encode('ascii'))


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='clash-primary-offline-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        proxy=Path('C:/ClashTests/hd-completion/framed-minimap-v1-1024x768-20260906-031649/candidate/ddraw.dll')
        if not proxy.is_file():self.skipTest('pinned proxy unavailable')
        self.proxy=proxy.read_bytes();base=0x10000000;pe=primary._Proxy(self.proxy,primary.SUPPORTED_PROXY_SHA256,base)
        p=snapshots.fixture();state=p['before']
        palette=bytearray(state.palette.data);struct.pack_into('<I',palette,0,base+primary.PALETTE_VTABLE_RVA)
        state=replace(state,surface=primary.Read(0x20001000,struct.pack('<I',base+primary.SURFACE_VTABLE_RVA)),
            surface_vtable=primary.Read(base+primary.SURFACE_VTABLE_RVA,pe.raw(primary.SURFACE_VTABLE_RVA,144)),
            palette=replace(state.palette,data=bytes(palette)),palette_vtable=primary.Read(base+primary.PALETTE_VTABLE_RVA,pe.raw(primary.PALETTE_VTABLE_RVA,28)))
        full=bytearray(32);struct.pack_into('<I',full,0,base+primary.SURFACE_VTABLE_RVA);struct.pack_into('<I',full,28,state.palette.address)
        reads={k:getattr(state,k) for k in state.__dataclass_fields__}
        reads.update(surface_full=primary.Read(state.surface.address,bytes(full)),proxy_header=primary.Read(base,self.proxy[:512]),
                     proxy_getpalette=primary.Read(base+tool.GET_PALETTE_RVA,tool.GET_PALETTE_BYTES))
        self.manifest=dict(reads={phase:{k:self.save(phase+'-'+k,r) for k,r in reads.items()} for phase in ('before','after')},
            pixels=self.save('pixels',p['pixels']),palette_entries=self.save('entries',primary.Read(state.palette.address+12,bytes(palette[12:]))),
            regions=[dict(address=r.address,size=r.size,state=r.state,protect=r.protect) for r in p['regions'][:-1]]+
                    [dict(address=base,size=pe.size,state=0x1000,protect=0x20)],
            run_id='synthetic-only',game_identity=dict(process_id=101,creation_utc='2026-09-06T00:00:00Z',candidate_sha256='a'*64),
            trace_sha256='b'*64,proxy_module=dict(base=base,sha256=primary.SUPPORTED_PROXY_SHA256))
        packet,log=log_fixture();self.trace=dict(passed=True,candidate_sha256='a'*64,source=dict(log_raw_sha256='b'*64),primary_sequence=sequence(packet,log))

    def save(self,name,r):
        path=self.root/name;path.write_bytes(r.data)
        return dict(path=str(path),address=r.address,bytes=len(r.data),sha256=tool.sha(r.data))

    def test_primary_snapshot_binds_current_palette_and_all_bytes(self):
        result=tool.audit_snapshot(self.manifest,proxy_image=self.proxy,trace=self.trace)
        self.assertTrue(result['source_authenticated']);self.assertTrue(result['cached_primary_snapshot_valid'])
        for key in ('runtime_passed','visual_passed','manual_input_proof','promotion_ready'):self.assertFalse(result[key])

    def test_changed_short_stale_or_substituted_host_reads_fail(self):
        for name in self.manifest['reads']['before']:
            m=copy.deepcopy(self.manifest);m['reads']['after'][name]['sha256']='0'*64
            with self.subTest(name=name),self.assertRaises(ValueError):tool.audit_snapshot(m,proxy_image=self.proxy,trace=self.trace)
        for name in ('pixels','palette_entries'):
            m=copy.deepcopy(self.manifest);m[name]['bytes']-=1
            with self.assertRaises(ValueError):tool.audit_snapshot(m,proxy_image=self.proxy,trace=self.trace)
        for key in ('trace_sha256','run_id'):
            m=copy.deepcopy(self.manifest);m[key]=''
            with self.assertRaises(ValueError):tool.audit_snapshot(m,proxy_image=self.proxy,trace=self.trace)


if __name__=='__main__':unittest.main(verbosity=2)
