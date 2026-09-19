"""Source-only lifecycle fixtures. All native reads/builds below are mocked.

No game, debugger, wrapper, host, desktop, input, executable or capture is
started or written. Synthetic records are deliberately not runtime evidence.
"""
import copy
import unittest
from unittest.mock import patch

import modal_slots_lifecycle_probe as probe


def fixture():
    entries=dict(try_leave=0x576411,is_active=0x576628,leave_before_map=0x57685F)
    observers=dict(before_restored_map_redraw=0x57686C)
    base=dict(candidate_sha256='a'*64,stage=probe.inherited.STAGE,resolution='1024x768',
              route={'name':'barracks'},availability='construct_all',castle_index=0,
              candidate_manifest={'path':'C:/synthetic/candidate.candidate.json'},
              canvas_state_va=0x596000,canvas_state_offsets=probe.canvas.STATE,
              canvas_entry_vas=entries,canvas_observer_vas=observers)
    commands={str(i):dict(va=0x600000+i*16,body='gc') for i in range(80,103)}
    commands['80']=dict(va=0x406FA1,body=probe.inherited._reject('unexpected_native_return'))
    commands['90']=dict(va=0x42262E,body=probe.inherited._guard('@eip == 0042262e',
        probe.inherited._reject('unexpected_callback_return'),'breakpoint_eip',expected_eip=0x42262E))
    base['breakpoint_commands']=commands
    initial='\n'.join(f'bp{i} {value["va"]:08x} "{value["body"]}"' for i,value in commands.items())+'\ng\n'
    native={va:bytes.fromhex(data) for va,data in probe.NATIVE.items()}
    native[0x422674]=probe._call(0x422674,0x422020)
    native[0x4224B2]=probe._call(0x4224B2,0x40AD40)
    candidate=copy.deepcopy(native)
    candidate[0x422674]=probe._call(0x422674,0x51B6D0)
    candidate[0x4224B2]=probe._call(0x4224B2,entries['leave_before_map'])
    body=bytearray(b'\x90'*(entries['is_active']-entries['try_leave']))
    call=entries['try_leave']+80
    body[75:80]=bytes.fromhex('ba02000000')
    body[80:85]=probe._call(call,probe.canvas.DTOR)
    candidate[entries['try_leave']]=bytes(body)
    candidate[entries['leave_before_map']]=(bytes.fromhex('9c608d442424')+
        probe._call(entries['leave_before_map']+6,entries['try_leave'])+bytes.fromhex('619d')+
        b'\xe9'+(0x40AD40-observers['before_restored_map_redraw']-5).to_bytes(4,'little',signed=True))
    def read(image,va,size):
        table=native if image==b'original' else candidate
        for start,data in table.items():
            if start<=va and va+size<=start+len(data): return va-0x400000,data[va-start:va-start+size]
        raise ValueError('synthetic unmapped read')
    return base,initial,native,candidate,read


def prepared_fixture():
    base,initial,native,candidate,read=fixture()
    with patch.object(probe.inherited,'build_screen_probe',return_value=base),\
         patch.object(probe.inherited_trace,'compile_probe',return_value=initial),\
         patch.object(probe.inherited,'_read',side_effect=read):
        result=probe.prepare(b'original',b'candidate',mode=probe.MODE)
    return result


def log_fixture(packet):
    base=packet['inherited_packet'];binding=packet['binding'];rows=[]
    contract=(f'LCAP_CONTRACT protocol={probe.REVISION} mode={probe.MODE} candidate_sha256={base["candidate_sha256"]} '
              f'stage={base["stage"]} resolution={base["resolution"]} acceptance=0')
    lines=[contract]
    for ordinal,spec in enumerate(probe.event_specs(binding)):
        name=spec['event'];kind=spec['ownership']
        row={field:0 for field in probe.FIELDS}
        row.update(ordinal=ordinal,tid=0x2345,eip=spec['vas'][0],esp=0x100000+spec['stack_delta'],
            root=0x100000,native=0x23000000,physical=0x24000000,native_pixels=0x25000000,
            physical_pixels=0x26000000,saved_render=0x24000000,saved_lower=0x401234,
            phase=int(kind=='active'),allocations=1,frees=int(kind=='released'),leave=int(kind=='released'),
            state_native=0x23000000 if kind=='active' else 0,state_physical=0x24000000,state_root=0x100000,
            owner_tid=0x2345,state_native_pixels=0x25000000,state_physical_pixels=0x26000000,
            state_saved_render=0x24000000,e0=0x23000000 if kind=='active' else 0x24000000,
            render=0x24000000,barracks_exit=int(ordinal>=5),overview_exit=int(ordinal>=13),
            lower=0x401234,hitmap=0x27000000)
        if kind=='released':
            for field in ('state_native','state_physical','state_root','owner_tid','state_native_pixels',
                          'state_physical_pixels','state_saved_render'): row[field]=0
        if name in ('LEAVE_ENTRY','BEFORE_MAP','MAP_ENTRY','MAP_RETURN'): row['caller']=probe.STOP
        if name=='BARRACKS_RETURN': row['caller']=0x42262E
        if name=='TRY_LEAVE_ENTRY': row.update(caller=binding['leave_va']+11,eax=row['root']-60)
        if name in ('DESTRUCTOR_CALL','DESTRUCTOR_ENTRY'): row.update(eax=row['native'],edx=2)
        if name in ('DESTRUCTOR_ENTRY','DESTRUCTOR_RETURN'): row['caller']=binding['destructor_call_va']+5
        if name in ('PIXEL_FREE_CALL','PIXEL_FREE_ENTRY'): row.update(eax=row['native_pixels'],edx=1,ecx=row['native'])
        if name=='PIXEL_FREE_ENTRY': row['caller']=0x403E72
        if name in ('PIXEL_FREE_RETURN','HEADER_FREE_CALL','HEADER_FREE_RETURN'): row['ecx']=row['native']
        if name in ('HEADER_FREE_CALL','HEADER_FREE_ENTRY','HEADER_HEAP_ENTRY'): row['eax']=row['native']
        if name in ('HEADER_FREE_ENTRY','HEADER_HEAP_ENTRY'): row['caller']=0x403EA9
        if name.endswith('_CALL') and name.startswith(('PRESENT','OVERVIEW_PRESENT')): row['eax']=0x544CD8
        if name=='FULL_MAP_CALL': row['eax']=1
        if name in ('BARRACKS_REQUEST','OVERVIEW_REQUEST'):
            target=0x532148 if name=='BARRACKS_REQUEST' else 0x526E80
            lines.append(f'LCAP_WRITE event={name} tid={row["tid"]:x} eip={row["eip"]:x} esp={row["esp"]:x} va={target:08x} old=0 new=1')
        lines.append('LCAP_EVENT event='+name+' '+' '.join(f'{field}={row[field]:x}' for field in probe.FIELDS))
        rows.append(row)
    lines.append('LCAP_SAFE_STOP')
    return '\n'.join(lines)+'\n',rows


class PacketTests(unittest.TestCase):
    def test_source_change_during_preparation_rejects_without_runtime(self):
        original_read = probe.Path.read_bytes
        target = probe.ROOT / probe.SOURCES[0]
        reads = 0

        def read(path):
            nonlocal reads
            data = original_read(path)
            if path == target:
                reads += 1
                if reads > 1:
                    return data + b'\n# synthetic concurrent edit\n'
            return data

        with patch.object(probe.Path, 'read_bytes', read):
            with self.assertRaisesRegex(ValueError, 'source changed during preparation'):
                prepared_fixture()

    def test_deterministic_two_artifacts_original_first_present_and_explicit_mode(self):
        first=prepared_fixture();second=prepared_fixture()
        self.assertEqual(first,second)
        self.assertEqual(first['initial_probe'],fixture()[1])
        packet=first['packet']
        self.assertEqual(packet['initial_probe_sha256'],probe.sha(first['initial_probe'].encode('ascii')))
        self.assertEqual(packet['continuation_probe_sha256'],probe.sha(first['continuation_probe'].encode('ascii')))
        self.assertEqual(len(packet['events']),35)
        self.assertEqual(packet['stop_va'],0x4224B7)
        for mode in ('','natural','manual','observed_only'):
            with self.assertRaisesRegex(ValueError,'explicit'): probe.prepare(b'',b'',mode=mode)
        self.assertFalse(packet['runtime_ready']);self.assertFalse(packet['evaluator_complete'])

    def test_native_changed_unknown_scalar_call_and_wrapper_are_rejected(self):
        for target in ('original','candidate'):
            for va in probe.NATIVE:
                base,initial,native,candidate,read=fixture()
                table=native if target=='original' else candidate
                table[va]=bytes([table[va][0]^1])+table[va][1:]
                with patch.object(probe.inherited,'_read',side_effect=read):
                    with self.assertRaisesRegex(ValueError,'bytes differ'):
                        probe._binding(b'original',b'candidate',base)
        for variant in ('missing','duplicate','non_scalar','wrapper'):
            base,initial,native,candidate,read=fixture()
            start=base['canvas_entry_vas']['try_leave'];body=bytearray(candidate[start])
            if variant=='missing': body[80]=0x90
            if variant=='duplicate': body[110:115]=probe._call(start+110,probe.canvas.DTOR)
            if variant=='non_scalar': body[76]=3
            if variant=='wrapper':
                va=base['canvas_entry_vas']['leave_before_map'];candidate[va]=b'\x90'+candidate[va][1:]
            candidate[start]=bytes(body)
            with patch.object(probe.inherited,'_read',side_effect=read):
                with self.assertRaises(ValueError): probe._binding(b'original',b'candidate',base)

    def test_unknown_ids_sites_callback_replacement_and_state_layout_fail(self):
        result=prepared_fixture();base=result['packet']['inherited_packet'];binding=result['packet']['binding']
        for mutation in ('id','site','callback'):
            changed=copy.deepcopy(base);initial=result['initial_probe']
            if mutation=='id':
                changed['breakpoint_commands']['103']={'va':0x650000,'body':'gc'}
                initial+='bp103 00650000 "gc"\n'
            elif mutation=='site': initial+='bp20 0040ad40 "gc"\n'
            else: changed['breakpoint_commands']['90']['body']='gc'
            with self.assertRaises(ValueError): probe._continuation(changed,binding,initial)
        changed=copy.deepcopy(base);changed['canvas_state_offsets']['owner_tid']+=4
        with self.assertRaisesRegex(ValueError,'layout'): probe._binding(b'',b'',changed)

    def test_continuation_only_two_disclosed_writes_no_stack_or_instruction_spoof(self):
        result=prepared_fixture();text=result['continuation_probe']
        self.assertNotRegex(text,r'(?i)\br\s+(?:eip|esp|eax|edx|ecx)\s*=')
        self.assertNotIn('ed @esp',text)
        self.assertEqual(text.count('ed 00532148 1'),1)
        self.assertEqual(text.count('ed 00526e80 1'),1)
        self.assertEqual(text.count('LCAP_WRITE event='),2)
        self.assertNotRegex(text,r'(?i)\b(?:ed|eb|ew)\s+(?!00532148 1|00526e80 1)')
        self.assertIn('bc 90',text)
        disabled=next(line for line in text.splitlines() if line.startswith('bd ')).split()[1:]
        self.assertNotIn('80',disabled)
        safe=next(line for line in text.splitlines() if line.startswith('bp') and '004224b7 "' in line)
        self.assertIn('LCAP_SAFE_STOP',safe);self.assertNotIn('; gc',safe)
        self.assertLess(max(map(len,text.splitlines())),4096)
        self.assertNotIn('LCAP_',result['initial_probe'])

    def test_whole_packet_and_both_probes_reconstructed_exactly(self):
        result=prepared_fixture();packet=result['packet']
        with patch.object(probe,'prepare',return_value=result):
            self.assertEqual(probe.reconstruct(b'original',b'candidate',packet,
                result['initial_probe'].encode('ascii'),result['continuation_probe'].encode('ascii')),result)
            for artifact in ('initial_probe','continuation_probe'):
                args={name:result[name].encode('ascii') for name in ('initial_probe','continuation_probe')}
                args[artifact]+=b'\ng\n'
                with self.assertRaises(ValueError): probe.reconstruct(b'',b'',packet,**args)
            for field,value in (('stop_va',0x406FA1),('runtime_ready',True),('revision','unknown'),('mode','manual')):
                changed=copy.deepcopy(packet);changed[field]=value
                with self.assertRaises(ValueError): probe.reconstruct(b'',b'',changed,
                    result['initial_probe'].encode('ascii'),result['continuation_probe'].encode('ascii'))


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.result=prepared_fixture();self.packet=self.result['packet'];self.log,self.rows=log_fixture(self.packet)

    def test_all_thirty_five_boundaries_and_both_native_return_variants(self):
        report=probe.evaluate_boundary_sequence(self.log,self.packet)
        self.assertTrue(report['boundary_sequence_passed'],report['failures'])
        self.assertEqual(len(report['raw_records']),39)
        self.assertFalse(report['source_authenticated']);self.assertFalse(report['evaluator_complete'])
        alternative=self.log.replace('event=BARRACKS_RETURN ordinal=8 tid=2345 eip=433f92',
                                     'event=BARRACKS_RETURN ordinal=8 tid=2345 eip=434101')
        self.assertTrue(probe.evaluate_boundary_sequence(alternative,self.packet)['boundary_sequence_passed'])

    def test_every_missing_and_duplicate_record_stays_failed_and_retained(self):
        rows=self.log.splitlines()
        for index in range(len(rows)):
            for changed in (rows[:index]+rows[index+1:],rows[:index]+[rows[index]]+rows[index:]):
                report=probe.evaluate_boundary_sequence('\n'.join(changed),self.packet)
                self.assertFalse(report['boundary_sequence_passed'],index)
                self.assertEqual(len(report['raw_records']),len(changed))
        for new in ('LCAP_UNKNOWN value=1','LCAP_REJECT wrong_owner','MCAP_REJECT old_failure','PTILE_TRACE_CLOSED unexpected'):
            report=probe.evaluate_boundary_sequence(self.log+new,self.packet)
            self.assertFalse(report['boundary_sequence_passed']);self.assertEqual(report['raw_records'][-1]['text'],new)

    def test_wrong_owners_stacks_free_counts_order_and_request_are_rejected(self):
        mutations=(('owner_tid=2345','owner_tid=2346'),('state_root=100000','state_root=100004'),
                   ('esp=fff9c','esp=fffa0'),('frees=1','frees=0'),('allocations=1','allocations=2'),
                   ('caller=403e72','caller=403ea9'),('eax=25000000','eax=26000000'),
                   ('old=0 new=1','old=1 new=1'),('va=00532148','va=00526e80'),
                   ('destructive_exit=0','destructive_exit=1'),('state_native=23000000','state_native=0'),
                   ('protocol='+probe.REVISION,'protocol=unknown'))
        for old,new in mutations:
            self.assertTrue(old in self.log,old)
            report=probe.evaluate_boundary_sequence(self.log.replace(old,new,1),self.packet)
            self.assertFalse(report['boundary_sequence_passed'],(old,new))
        rows=self.log.splitlines();rows[24],rows[28]=rows[28],rows[24]
        self.assertFalse(probe.evaluate_boundary_sequence('\n'.join(rows),self.packet)['boundary_sequence_passed'])

    def test_malformed_known_records_are_retained_without_normalization(self):
        rows=self.log.splitlines()
        for index in (0,1,6,len(rows)-1):
            for replacement in (' '+rows[index],'\t'+rows[index],rows[index]+' extra=1',rows[index].lower()):
                changed=rows.copy();changed[index]=replacement
                report=probe.evaluate_boundary_sequence('\n'.join(changed),self.packet)
                self.assertFalse(report['boundary_sequence_passed'])
                self.assertEqual(len(report['raw_records']),len(rows))

    def test_source_bound_report_preserves_initial_failure_and_cannot_accept(self):
        prefix='MCAP_SURFDUMP_HOST_READY\n';ready=self.rows[0]
        inherited_report=dict(failures=['initial trace incomplete 498/501'],modal_sequence={'raw_records':[
            {'marker':'MCAP_CANVAS','values':dict(event='READY',tid=ready['tid'],root_esp=ready['root'],
                native=ready['native'],physical=ready['physical'],native_pixels=ready['native_pixels'],
                physical_pixels=ready['physical_pixels'])}]})
        with patch.object(probe,'reconstruct',return_value=self.result),\
             patch.object(probe.inherited_trace,'evaluate_trace',return_value=inherited_report):
            report=probe.evaluate_trace(prefix+self.log,original=b'',candidate=b'',packet=self.packet,
                initial_probe=b'initial',continuation_probe=b'continuation')
            self.assertIn('initial trace incomplete 498/501',report['failures'])
            self.assertTrue(report['boundary_report']['boundary_sequence_passed'])
            for key in ('passed','runtime_ready','runtime_accepted','evaluator_complete','healthy_map_redraw_proven',
                        'cleanup_verified','manual_input_proof','callback_proof','continuity_proven','promotion_ready'):
                self.assertFalse(report[key],key)
            inherited_report['failures']=[]
            report=probe.evaluate_trace(prefix+self.log,original=b'',candidate=b'',packet=self.packet,
                initial_probe=b'initial',continuation_probe=b'continuation')
            self.assertFalse(report['passed']);self.assertEqual(len(report['failures']),1)
            inherited_report['modal_sequence']['raw_records'][0]['values']['native']+=4
            report=probe.evaluate_trace(prefix+self.log,original=b'',candidate=b'',packet=self.packet,
                initial_probe=b'initial',continuation_probe=b'continuation')
            self.assertFalse(report['boundary_report']['boundary_sequence_passed'])
            self.assertTrue(any('inherited owned-canvas identity' in failure for failure in report['failures']))


if __name__=='__main__':
    unittest.main()
