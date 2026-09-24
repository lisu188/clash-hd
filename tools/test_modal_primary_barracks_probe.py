"""Offline command execution and real image reconstruction; no native runtime.

The interpreter models only emitted CDB expressions and observations. Explicit
fixture changes stand in for separately tested native calls and never claim
that a game, debugger, cursor callback or successful screenshot was observed.
"""
from __future__ import annotations

import copy
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import modal_primary_barracks_probe as probe
import test_framed_modal_canvas_probe as canvas_fixture
from test_framed_screen_probe import Memory, run, write
from test_continuity_day_diagnostic_probe import parse_commands
from test_framed_army_selection_probe import expression_value

ORIGINAL=Path('C:/Clash/clash95.exe')
METADATA,NATIVE=canvas_fixture.METADATA,canvas_fixture.NATIVE
NAMES=('full_entry full_fallback remove_call remove_entry remove_return publish_call_direct '
       'publish_return_direct publish_call_cursor publish_return_cursor publish_entry draw_call '
       'draw_entry draw_return full_return_direct full_return_cursor cursor_rect placeholder_before placeholder_after').split()


def metadata():
    observers={name:0x680000+128*index for index,name in enumerate(NAMES)}
    observers.update(remove_entry=0x460F90,draw_entry=0x460EA0,publish_entry=0x4E9920,
                     cursor_rect=0x460BB0,placeholder_before=0x432F9E,placeholder_after=0x432FA1)
    return dict(METADATA,slots_metadata={'slot_entry_vas':{'after_dirty_copy':0x5F0100}},
                primary_observers=observers)


def execute(body,memory,registers,enabled,observations):
    # The shared interpreter models one ID per command. Splitting CDB's real
    # ID-list syntax here preserves its operations without changing production.
    body=re.sub(r'\b(be|bd) (\d+(?: \d+)+)',
                lambda match:'; '.join(match[1]+' '+part for part in match[2].split()),body)
    return run(body,memory,registers,enabled,observations)


class CommandFixture:
    def __init__(self,cursor=0,width=800,height=600):
        self.metadata=metadata();self.width=width;self.height=height
        self.handoff,self.commands=probe._commands(probe.ROUTES['barracks'],width,height,0,'construct_all',self.metadata)
        self.observers=self.metadata['primary_observers']
        prior=canvas_fixture.CommandTests().advance('barracks',width=width,height=height)
        self.memory,self.regs,self.enabled=copy.deepcopy(prior[4][93])
        self.rows=[];self.snapshots={};self.h=self.regs['$t3'];self.s=self.h-92
        for address in range(self.h-512,self.h+8):self.memory.setdefault(address,0)
        self.regs.update({'$t18':0,'$t19':0})
        write(self.memory,0x544D10,cursor)
        self.hit(93)
        self.packet=dict(primary_observers=self.observers,checkpoints=probe.checkpoint_contract(self.observers),
                         canvas_state_va=self.metadata['state_va'],resolution=f'{width}x{height}')

    def hit(self,key,expected='gc',**registers):
        self.regs.update(registers)
        number=key if isinstance(key,int) else next(n for n,(va,_) in self.commands.items() if va==self.observers[key])
        self.regs['eip']=self.commands[number][0]
        self.snapshots[key]=(Memory(self.memory),self.regs.copy(),self.enabled.copy())
        result=execute(self.commands[number][1],self.memory,self.regs,self.enabled,self.rows)
        if result!=expected:raise AssertionError((key,result,expected,self.rows[-2:]))
        return result

    def field(self,name,value):write(self.memory,self.metadata['state_va']+probe.canvas.STATE[name],value)

    def checkpoint(self,name):
        self.snapshots['checkpoint:'+name]=(Memory(self.memory),self.regs.copy(),self.enabled.copy())
        text=probe.checkpoint_script(self.packet,name).replace(r'\n',r'\\n')
        rows=[]
        result=execute(text,self.memory,self.regs,self.enabled,rows)
        if result is not None:raise AssertionError((name,result,rows))
        assert len(rows)==2 and rows[0].startswith('MCAP_CANVAS event=CHECKPOINT '),rows
        assert rows[1].startswith('MPCAP_CHECKPOINT name='+name+' '),rows
        return rows

    def publish(self,cursor):
        self.hit('full_entry',esp=self.s,eax=NATIVE)
        self.field('mirrors',3);self.field('mirror_status',1)  # modeled native mirror
        if cursor:
            self.hit('remove_call',esp=self.s-36,eax=0x544CD8)
            write(self.memory,self.s-40,self.observers['remove_return'])
            self.hit('remove_entry',esp=self.s-40)
            write(self.memory,0x544D10,0)  # modeled native Remove
            self.hit('remove_return',esp=self.s-36)
        kind='cursor' if cursor else 'direct'
        self.hit('publish_call_'+kind,esp=self.s-4,eax=0x20000000)
        write(self.memory,self.s-8,self.observers['publish_return_'+kind])
        self.hit('publish_entry',esp=self.s-8)
        self.hit('publish_return_'+kind,expected=None,esp=self.s-4)
        self.checkpoint('full-published')
        if cursor:
            self.hit('draw_call',esp=self.s-36,eax=0x544CD8)
            write(self.memory,self.s-40,self.observers['draw_return'])
            self.hit('draw_entry',esp=self.s-40)
            write(self.memory,0x544D10,1)  # modeled native Present
            self.hit('draw_return',esp=self.s-36)
        self.hit('full_return_'+kind,esp=self.s,eax=NATIVE)
        self.hit(97,esp=self.s+4)

    def placeholder(self):
        dx,dy=(self.width-640)//2,(self.height-480)//2
        resource,sprite=0x27000000,0x28000000
        write(self.memory,0x532188,0xFFFFFFFF);write(self.memory,0x532144,resource)
        write(self.memory,0x511230,0x51D4C0)  # native432F09 selects primary
        write(self.memory,resource+100,sprite);write(self.memory,sprite,203,2);write(self.memory,sprite+2,120,2)
        write(self.memory,self.h-168,0x432F61);write(self.memory,self.h-164,289+dy+120)
        self.hit('cursor_rect',esp=self.h-168,ebp=self.h-116,eax=0x544CD8,edx=220+dx,ecx=220+dx+203,ebx=289+dy)
        write(self.memory,self.h-92,0x433E4E)
        for i in range(7):write(self.memory,self.h-188+4*i,0xFFFFFFFF if i<4 else 0)
        self.hit('placeholder_before',expected=None,esp=self.h-188,ebp=self.h-116,eax=0x51D4C0,
                 esi=0x50EEC4,edx=sprite,ebx=220+dx,ecx=289+dy)
        self.checkpoint('placeholder-before')
        self.hit('placeholder_after',expected=None,esp=self.h-160)
        self.checkpoint('placeholder-after')
        write(self.memory,0x511230,NATIVE)  # native432FA5 restores saved target
        self.hit(88,esp=self.h-88,eax=0x544CD8)
        self.hit(89,expected=None,esp=self.h-88)
        self.checkpoint('final-ready')


class CommandTests(unittest.TestCase):
    def test_both_actual_command_paths_pause_in_native_order_and_preserve_gprs(self):
        for cursor in (0,1):
            for width,height in ((800,600),(1024,768),(1920,1080)):
                with self.subTest(cursor=cursor,resolution=(width,height)):
                    fixture=CommandFixture(cursor,width,height)
                    fixture.publish(cursor);fixture.placeholder()
                    checkpoints=[row.split('name=')[1] for row in fixture.rows if row.startswith('MPCAP_HOST_READY ')]
                    self.assertEqual(checkpoints,[item['name'] for item in fixture.packet['checkpoints']])
                    self.assertEqual(fixture.regs['$t19'],4)
                    for key,(memory,registers,enabled) in fixture.snapshots.items():
                        if key==93 or isinstance(key,str) and key.startswith('checkpoint:'):continue
                        number=key if isinstance(key,int) else next(n for n,(va,_) in fixture.commands.items() if va==fixture.observers[key])
                        old_memory=dict(memory);gprs={k:v for k,v in registers.items() if not k.startswith('$')}
                        execute(fixture.commands[number][1],memory,registers,enabled,[])
                        self.assertEqual(dict(memory),old_memory,key)
                        self.assertEqual({k:v for k,v in registers.items() if not k.startswith('$')},gprs,key)

    def test_call_return_thread_stack_phase_and_cursor_drift_fail_closed(self):
        fixture=CommandFixture(1);fixture.publish(1);fixture.placeholder()
        keys=('full_entry','remove_call','remove_entry','remove_return','publish_call_cursor','publish_entry',
              'publish_return_cursor','draw_call','draw_entry','draw_return','full_return_cursor',
              'cursor_rect','placeholder_before','placeholder_after')
        for key in keys:
            number=next(n for n,(va,_) in fixture.commands.items() if va==fixture.observers[key])
            for register in ('$tid','$t18','eip','esp'):
                with self.subTest(event=key,register=register):
                    memory,registers,enabled=copy.deepcopy(fixture.snapshots[key]);rows=[]
                    registers[register]+=4
                    # Shared native entry is selected by its authenticated
                    # return word; retain it while testing the wrong stack.
                    if key.endswith('_entry') and key!='full_entry' and register=='esp':
                        write(memory,registers['esp'],fixture.observers[{'remove_entry':'remove_return','draw_entry':'draw_return','publish_entry':'publish_return_cursor'}[key]])
                    if key=='cursor_rect' and register=='esp':write(memory,registers['esp'],0x432F61)
                    self.assertEqual(execute(fixture.commands[number][1],memory,registers,enabled,rows),'q')
                    self.assertFalse(any(row.startswith('MPCAP_HOST_READY') for row in rows))
        for key,bad_flag in (('remove_call',0),('remove_return',1),('publish_call_cursor',1),('publish_return_cursor',1),('draw_call',1),('draw_return',0)):
            memory,registers,enabled=copy.deepcopy(fixture.snapshots[key]);write(memory,0x544D10,bad_flag)
            number=next(n for n,(va,_) in fixture.commands.items() if va==fixture.observers[key])
            self.assertEqual(execute(fixture.commands[number][1],memory,registers,enabled,[]),'q',key)

    def test_checkpoint_scripts_require_current_owner_phase_objects_and_exact_stop(self):
        fixture=CommandFixture(0);fixture.publish(0);fixture.placeholder()
        for checkpoint in fixture.packet['checkpoints']:
            name=checkpoint['name'];body=probe.checkpoint_script(fixture.packet,name).replace(r'\n',r'\\n')
            for register in ('eip','$t19','$tid'):
                memory,registers,enabled=copy.deepcopy(fixture.snapshots['checkpoint:'+name]);registers[register]+=4
                self.assertEqual(execute(body,memory,registers,enabled,[]),'q',(name,register))
            for field,value in (('phase',0),('fault',1),('owner_tid',0),('root_esp',0),('allocations',2),
                                ('frees',1),('mirrors',2),('native',0),('physical',0),('native_pixels',0),('physical_pixels',0)):
                memory,registers,enabled=copy.deepcopy(fixture.snapshots['checkpoint:'+name])
                write(memory,fixture.metadata['state_va']+probe.canvas.STATE[field],value)
                rows=[];self.assertEqual(execute(body,memory,registers,enabled,rows),'q',(name,field))
                self.assertFalse(any(row.startswith('MPCAP_CHECKPOINT name=') for row in rows))

    def test_placeholder_and_rect_reject_old_destination_selection_arguments_and_aliases(self):
        fixture=CommandFixture(0);fixture.publish(0);fixture.placeholder()
        for key,changes in (('placeholder_before',(('ebx',220),('ecx',289),('eax',NATIVE),('esi',0x50EE24),('edx',0))),
                            ('cursor_rect',(('edx',220),('ebx',289),('ecx',1)))):
            number=next(n for n,(va,_) in fixture.commands.items() if va==fixture.observers[key])
            for register,value in changes:
                memory,registers,enabled=copy.deepcopy(fixture.snapshots[key]);registers[register]=value
                self.assertEqual(execute(fixture.commands[number][1],memory,registers,enabled,[]),'q',(key,register))
        number=next(n for n,(va,_) in fixture.commands.items() if va==fixture.observers['placeholder_before'])
        for address,value in ((0x532188,0),(0x532144,0),(0x27000064,0),*( (fixture.h-188+4*i,1) for i in range(7))):
            memory,registers,enabled=copy.deepcopy(fixture.snapshots['placeholder_before']);write(memory,address,value)
            self.assertEqual(execute(fixture.commands[number][1],memory,registers,enabled,[]),'q',hex(address))

    def test_owned_fallback_fails_but_unrelated_source_does_not_claim_publication(self):
        fixture=CommandFixture(0)
        number=next(n for n,(va,_) in fixture.commands.items() if va==fixture.observers['full_fallback'])
        for source,expected in ((NATIVE,'q'),(0x22000000,'gc')):
            memory,registers,enabled=copy.deepcopy(fixture.snapshots[93]);rows=[]
            registers.update(eip=fixture.observers['full_fallback'],esp=fixture.s-36,**{'$t18':0})
            for address in range(registers['esp'],registers['esp']+40):memory.setdefault(address,0)
            write(memory,registers['esp']+28,source)
            self.assertEqual(execute(fixture.commands[number][1],memory,registers,enabled,rows),expected)
            self.assertFalse(any(row.startswith('MPCAP_EVENT') for row in rows))

    def test_native_minus_one_guards_accept_both_cdb_read_forms_and_reject_other_dwords(self):
        # The command interpreter above reads unsigned byte-backed DWORDs.
        # This independent oracle preserves observed CDB poi sign extension
        # while evaluating the actual emitted admission and argument guards.
        fixture=CommandFixture(0,1024,768);fixture.publish(0);fixture.placeholder()
        def conditions(nodes):
            for node in nodes:
                if node[0]=='if':
                    yield node[1]
                    yield from conditions(node[2]);yield from conditions(node[3])
        for key in ('cursor_rect','placeholder_before'):
            number=next(n for n,(va,_) in fixture.commands.items() if va==fixture.observers[key])
            guards=[text for text in conditions(parse_commands(fixture.commands[number][1]))
                    if 'poi(00532188)' in text]
            self.assertEqual(len(guards),1,key)
            guard=guards[0]
            stored,registers,_=fixture.snapshots[key]
            registers={name.removeprefix('$'):value for name,value in registers.items()}
            sentinel_addresses=[0x532188]
            read_addresses=[0x532188]
            if key=='placeholder_before':
                sentinel_addresses.extend(registers['esp']+4*i for i in range(4))
                read_addresses.extend([registers['ebp']+0x18,*(registers['esp']+4*i for i in range(7))])
            for sentinel in (0xFFFFFFFF,0xFFFFFFFFFFFFFFFF):
                memory={address:sum(stored[address+i]<<(8*i) for i in range(4)) for address in read_addresses}
                memory.update(dict.fromkeys(sentinel_addresses,sentinel))
                self.assertTrue(expression_value(guard,registers,memory),(key,sentinel))
                for address in sentinel_addresses:
                    for value in (0,3,0xFFFFFFFE,0xFFFFFFFFFFFFFFFE,0x7FFFFFFF):
                        with self.subTest(event=key,read_form=hex(sentinel),address=hex(address),value=hex(value)):
                            self.assertFalse(expression_value(guard,registers,memory|{address:value}))
            # Preserve the diagnosed old failure rather than normalizing poi
            # inside the oracle and accidentally making either version pass.
            self.assertFalse(expression_value('poi(00532188) == 0xffffffff',registers,
                                              {0x532188:0xFFFFFFFFFFFFFFFF}))

    def test_cursor_diagnostic_precedes_unchanged_rejection_and_never_writes_target(self):
        fixture=CommandFixture(0,1024,768);fixture.publish(0);fixture.placeholder()
        number=next(n for n,(va,_) in fixture.commands.items() if va==fixture.observers['cursor_rect'])
        cases=(('edx',220),('esp',fixture.h-172),('$t9',14),('$t18',1),('$t19',0))
        for key,value in cases:
            memory,registers,enabled=copy.deepcopy(fixture.snapshots['cursor_rect'])
            registers[key]=value
            if key=='esp':
                write(memory,value,0x432F61);write(memory,value+4,553)
            before=dict(memory);gprs={k:v for k,v in registers.items() if not k.startswith('$')};rows=[]
            self.assertEqual(execute(fixture.commands[number][1],memory,registers,enabled,rows),'q',key)
            self.assertEqual(len(rows),2,rows)
            self.assertTrue(rows[0].startswith('MPCAP_CURSOR_RECT_CONTEXT '),rows)
            self.assertEqual(rows[1],'MPCAP_REJECT reason=cursor_rect')
            self.assertEqual(dict(memory),before)
            self.assertEqual({k:v for k,v in registers.items() if not k.startswith('$')},gprs)
            self.assertNotIn('MPCAP_CURSOR_RECT tid=', '\n'.join(rows))

    def test_reserved_ids_arming_seams_transport_bound_and_inherited_route_are_preserved(self):
        for width,height in ((800,600),(1024,768),(1280,720),(1280,960),(1920,1080),(802,602)):
            meta=metadata();handoff,commands=probe._commands(probe.ROUTES['barracks'],width,height,3,'construct_all',meta)
            old_handoff,old=probe.inherited._commands(probe.ROUTES['barracks'],width,height,3,'construct_all',meta)
            self.assertEqual(handoff,old_handoff)
            self.assertNotIn(110,commands);self.assertNotIn(111,commands)
            self.assertEqual(len({va for va,_ in commands.values()}),len(commands))
            for key in set(old)-{81,87,89}:self.assertEqual(commands[key],old[key],key)
            self.assertEqual(commands[87][1].count('MPCAP_PRIMARY_OBSERVERS_ARM'),1)
            for number,(va,body) in commands.items():
                self.assertLess(len(f'bp{number} {va:08x} "{body}"'),4096)
                if number>=103:
                    self.assertNotRegex(body,r'\b(?:eb|ed|ew|eza|ezu)\s')
                    self.assertNotRegex(body,r'\br\s+@?(?:e[a-z]{2}|[abcd][lh])=')
            text='\n'.join(body for _,body in commands.values())
            for name,count in (('full-published',2),('placeholder-before',1),('placeholder-after',1),('final-ready',1)):
                self.assertEqual(text.count('MPCAP_HOST_READY name='+name),count)

    def test_checkpoint_names_shape_and_helper_drift_fail(self):
        fixture=CommandFixture()
        for change in ('name','index','eips'):
            packet=copy.deepcopy(fixture.packet);packet['checkpoints'][0][change]=None
            with self.assertRaises(ValueError):probe.checkpoint_script(packet,'full-published')
        packet=copy.deepcopy(fixture.packet);packet['checkpoints'][0]['index']=False
        with self.assertRaises(ValueError):probe.checkpoint_script(packet,'full-published')
        with self.assertRaises(ValueError):probe.checkpoint_script(fixture.packet,'unknown')
        with patch.object(probe,'HELPER_SHA256','0'*64):
            with self.assertRaisesRegex(ValueError,'frozen native route helper'):probe.check_helpers()


class ActualSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ORIGINAL.is_file():raise unittest.SkipTest('user-owned original executable is not available')
        cls.original=ORIGINAL.read_bytes()
        cls.candidate,cls.manifest,cls.extra=probe.builder.build_candidate(cls.original,'1024x768')

    def test_actual_relocation_contract_matches_exact_native_instruction_boundaries(self):
        observers=probe.primary_observers(self.manifest,self.candidate)
        for key in ('remove_call','draw_call','publish_call_direct','publish_call_cursor'):
            target=observers[{'remove_call':'remove_entry','draw_call':'draw_entry',
                             'publish_call_direct':'publish_entry','publish_call_cursor':'publish_entry'}[key]]
            installed=probe._read(self.candidate,observers[key],5)[1]
            self.assertEqual(installed[0],0xE8)
            self.assertEqual(observers[key]+5+int.from_bytes(installed[1:],'little',signed=True),target)
        for va,old in ((0x432ED0,'53515256575589e583ec2c'),(0x432F9E,'ff563485ff'),
                       (0x433E3F,'e87cefffffe877f8ffffe882f0ffff'),(0x460BB0,'565789d689df8b583c')):
            self.assertEqual(probe._read(self.original,va,len(bytes.fromhex(old)))[1].hex(),old)
        for key in ('relocations','primary_entry_vas'):
            bad=copy.deepcopy(self.manifest)
            if key=='relocations':bad[key][next(i for i,row in enumerate(bad[key]) if row['purpose']=='native cursor remove before full copy')]['target']+=1
            else:bad[key].pop('full_blit')
            with self.assertRaises((ValueError,KeyError)):probe.primary_observers(bad,self.candidate)

    def test_genuine_new_stage_bundle_compiles_and_legacy_or_tampered_inputs_fail(self):
        import modal_primary_barracks_trace as trace
        with tempfile.TemporaryDirectory(prefix='modal-primary-producer-') as directory:
            path=Path(directory)/'candidate.candidate.json'
            path.write_text(__import__('json').dumps(self.manifest),encoding='utf-8')
            path.with_name('candidate.exe').write_bytes(self.candidate)
            path.with_name('candidate.cdb').write_bytes(self.extra.encode('utf-8'))
            # Manifest/image/probe are real bytes. Reuse only the independently
            # completed rebuild to avoid a second expensive assembler pass.
            import modal_primary_candidate_context as context
            with patch.object(context.builder,'build_candidate',return_value=(self.candidate,self.manifest,self.extra)):
                canonical=probe.canonical_template(self.original,'1024x768',candidate=self.candidate,candidate_manifest=path)
            args=dict(candidate_sha256=probe.sha(self.candidate),stage=probe.STAGE,resolution='1024x768',
                      route='barracks',availability='construct_all',castle_index=0,candidate_manifest=path)
            with patch.object(probe,'canonical_template',return_value=canonical):
                packet=probe.build_screen_probe(self.original,self.candidate,**args)
                compiled=trace.compile_probe(packet)
                self.assertFalse(packet['runtime_ready']);self.assertFalse(packet['manual_input_proof'])
                self.assertFalse(packet['promotion_ready'])
                self.assertIn('MPRIMARY_CONTRACT_PASS stage='+probe.STAGE,compiled)
                self.assertNotIn('SLOTS_CONTRACT_PASS',compiled)
                self.assertLess(max(map(len,compiled.splitlines())),4096)
                for item in packet['checkpoints']:
                    self.assertLess(max(map(len,probe.checkpoint_script(packet,item['name']).splitlines())),4096)
                self.assertEqual(packet['slot_entry_vas'],self.manifest['base_candidate']['slot_entry_vas'])
                self.assertEqual(packet['source_sha256'],self.manifest['source_hashes'])
                for changes in ({'stage':probe.inherited.STAGE},{'route':'school'},{'candidate_sha256':'0'*64},
                                {'castle_index':True},{'availability':'natural'},{'minimap_viewport':False},
                                {'rendered_probe':canonical[3]+'\n.echo forged'}):
                    with self.assertRaises(ValueError):probe.build_screen_probe(self.original,self.candidate,**(args|changes))
                changed=bytearray(self.candidate);changed[probe._read(self.candidate,0x433E3F,1)[0]]^=1
                with self.assertRaises(ValueError):probe.build_screen_probe(self.original,bytes(changed),**(args|{'candidate_sha256':probe.sha(changed)}))


if __name__=='__main__':unittest.main()
