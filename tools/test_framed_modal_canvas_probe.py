"""Offline execution of emitted CDB commands; no debugger, game or EXE output."""
from __future__ import annotations

import copy
from pathlib import Path
import unittest
from unittest.mock import patch

import framed_modal_canvas_probe as probe
from test_framed_screen_probe import Memory, run, state, write

ORIGINAL=Path('C:/Clash/clash95.exe')
METADATA={'state_va':0x596000,'modal_observer_vas':{
    'root_after_replayed_pushes':0x5767B0,'overview_after_native_draw':0x5767E0}}
NATIVE=0x23000000
PIXELS=0x24000000


class CommandTests(unittest.TestCase):
    def advance(self,name='school',availability='existing_flags',width=800,height=600,index=0,metadata=None,variant=1):
        metadata=metadata or METADATA
        route=probe.ROUTES[name]
        handoff,commands=probe._commands(route,width,height,index,availability,metadata)
        memory,regs,enabled,observed=state(width,height,index)
        regs['edi']=66
        write(memory,0x51D578,0x50EEC4)
        stack=regs['esp'];sv=metadata['state_va']
        self.assertEqual(run(handoff,memory,regs,enabled,observed),'gc')
        self.assertEqual(regs['eip'],0x422180)
        self.assertFalse(enabled & set(range(70,78)))
        write(memory,regs['$t1']+4,variant,1)
        write(memory,0x5202EC,0)
        snapshots={}
        def hit(number,**changes):
            regs.update(changes);regs['eip']=commands[number][0]
            if any(x in commands[number][1] for x in ('MCAP_CANVAS','poi(@esp)')):
                for i in range(4): memory.setdefault(regs['esp']+i,0)
            snapshots[number]=(Memory(memory),regs.copy(),enabled.copy())
            return run(commands[number][1],memory,regs,enabled,observed)
        def field(name,value):write(memory,sv+probe.canvas.STATE[name],value)
        # Model the already separately x86-tested emitter's committed state.
        for i in range(128):memory[sv+i]=0
        for k,v in dict(phase=1,physical=0x20000000,native=NATIVE,saved_render=0x20000000,
                root_esp=stack-4,owner_tid=regs['$tid'],enter_status=1,allocations=1,
                native_pixels=PIXELS,physical_pixels=0x21000000).items():field(k,v)
        for a,v,n in ((NATIVE,640,2),(NATIVE+2,480,2),(NATIVE+4,PIXELS,4),
                      (NATIVE+0xB8,0x50EE24,4),(NATIVE+0xAC,0,4),
                      (0x5202E0,NATIVE,4),(0x511230,NATIVE,4)):
            write(memory,a,v,n)
        for name_reg in ('ebx','ecx','edx','esi','edi'):
            regs['esp']-=4;write(memory,regs['esp'],regs[name_reg])
        self.assertEqual(hit(81),'gc')
        write(memory,stack-136,0x422043)
        self.assertEqual(hit(98,esp=stack-136,eax=NATIVE,ecx=regs['$t1'],ebx=0,edx=0),'gc')
        def call(number,esp,caller):
            write(memory,esp,caller)
            self.assertEqual(hit(number,esp=esp,eax=NATIVE),'gc')
            snapshots[(number,caller)]=copy.deepcopy(snapshots[number])
        call(91,stack-452,0x4213C2)
        self.assertEqual(hit(92,esp=stack-448,eax=7),'gc')
        self.assertIn(91,enabled)
        call(91,stack-452,0x4214DC)
        self.assertEqual(hit(100,esp=stack-448,eax=8),'gc')
        if variant==1:
            call(91,stack-452,0x42154A)
            self.assertEqual(hit(101,esp=stack-448,eax=9),'gc')
        else:self.assertNotIn(101,enabled)
        self.assertIn(91,enabled)
        self.assertEqual(hit(99,esp=stack-132),'gc')
        call(93,stack-136,0x4220C6)
        field('mirrors',1);field('mirror_status',1)
        self.assertEqual(hit(94,esp=stack-132,eax=17),'gc')
        field('mirrors',2)
        self.assertEqual(hit(95,esp=stack-100,eax=19),'gc')
        self.assertEqual(hit(82,esp=stack-60,eax=0x544CD8),'gc')
        self.assertEqual(hit(83,esp=stack-60),None if route.name=='castle_overview' else 'gc')
        if route.name!='castle_overview':
            self.assertEqual(hit(84,esp=stack-60,esi=0,ebp=index*467),'gc')
            self.assertEqual(hit(85,esp=stack-60,eax=0,ecx=route.entry_va,esi=route.command),'gc')
            write(memory,0x5199D8,0x4617A0)
            self.assertEqual(hit(86,esp=stack-60,eax=regs['$t1'],ecx=route.entry_va),'gc')
            write(memory,stack-64,0x42262E)
            self.assertEqual(hit(87,esp=stack-64,eax=regs['$t1']),'gc')
            bottom=stack-64-route.local_stack_bytes
            call(91,bottom-4,probe.LOAD_CALLS[route.name]+3)
            self.assertEqual(hit(96,esp=bottom,eax=0x71),'gc')
            call(93,bottom-4,probe.BLIT_CALLS[route.name]+3)
            field('mirrors',3)
            self.assertEqual(hit(97,esp=bottom,eax=0x91),'gc')
            self.assertEqual(hit(88,esp=bottom,eax=0x544CD8),'gc')
            self.assertIsNone(hit(89,esp=bottom,eax=0x1234))
        return memory,regs,enabled,observed,snapshots,commands,handoff

    def test_all_seven_native_paths_both_explicit_availability_profiles(self):
        for name in probe.ROUTES:
            for availability in ('existing_flags','construct_all'):
                with self.subTest(route=name,availability=availability):
                    m,r,e,rows,s,c,h=self.advance(name,availability)
                    self.assertEqual(rows[-1],'MCAP_SURFDUMP_HOST_READY')
                    self.assertIn('surface=20000000 size=(800,600) base=21000000',rows[-2])
                    self.assertIn('capture=owned_physical_mirror',rows[-2])
                    self.assertNotIn(0x422181,[va for va,_ in c.values()])
                    self.assertFalse(e & {91,92,93,94,95,96,97,98,99,100,101})
                    self.assertFalse(any(x.startswith('MODAL_') for x in rows))

    def test_wrong_root_stack_sentinel_or_saved_register_fails_without_entry(self):
        *_,snapshots,commands,handoff=self.advance('castle_overview')
        for offset in (0,4,8,12,16,20):
            m,r,e=copy.deepcopy(snapshots[81]);rows=[]
            write(m,r['esp']+offset,0xDEADBEEF)
            self.assertEqual(run(commands[81][1],m,r,e,rows),'q')
            self.assertFalse(any(x.startswith('MCAP_CANVAS') for x in rows))
        m,r,e=copy.deepcopy(snapshots[81]);r['esp']+=4;rows=[]
        self.assertEqual(run(commands[81][1],m,r,e,rows),'q')

    def test_owned_state_fault_counters_dimensions_com_and_nulls_fail(self):
        *_,snapshots,commands,handoff=self.advance('school')
        changes=[('phase',0),('fault',1),('owner_tid',99),('root_esp',1),('allocations',2),
                 ('frees',1),('native',0),('physical',0),('native_pixels',PIXELS+4),
                 ('physical_pixels',0x21000004),('pending_header',1),('pending_pixels',1)]
        for bp in (81,92,94,95,96,97,98,99,100,101,89):
            for field,value in changes:
                with self.subTest(bp=bp,field=field):
                    m,r,e=copy.deepcopy(snapshots[bp]);rows=[]
                    write(m,METADATA['state_va']+probe.canvas.STATE[field],value)
                    self.assertEqual(run(commands[bp][1],m,r,e,rows),'q')
                    self.assertNotIn('MCAP_SURFDUMP_HOST_READY',rows)
            for address,value,n in ((NATIVE,800,2),(NATIVE+2,600,2),(NATIVE+0xAC,1,4),
                                    (NATIVE+0xB8,0x50EEC4,4),(0x20000000,640,2),(0x5202E0,0x20000000,4)):
                m,r,e=copy.deepcopy(snapshots[bp]);rows=[];write(m,address,value,n)
                self.assertEqual(run(commands[bp][1],m,r,e,rows),'q')

    def test_native_return_stack_wrong_caller_and_repeated_command_fail(self):
        *_,snapshots,commands,handoff=self.advance('school')
        for bp in (92,94,96,97,99,100,101):
            m,r,e=copy.deepcopy(snapshots[bp]);r['esp']+=4;rows=[]
            self.assertEqual(run(commands[bp][1],m,r,e,rows),'q')
        for bp in (91,93):
            m,r,e=copy.deepcopy(snapshots[bp]);rows=[];write(m,r['esp'],0x12345678)
            self.assertEqual(run(commands[bp][1],m,r,e,rows),'q')
        for bp in (81,92,94,95,96,97,98,99,100,101):
            m,r,e=copy.deepcopy(snapshots[bp]);rows=[]
            self.assertEqual(run(commands[bp][1],m,r,e,rows),'gc')
            self.assertEqual(run(commands[bp][1],m,r,e,rows),'q')

    def test_other_surface_loader_cannot_supply_owned_canvas_evidence(self):
        *_,snapshots,commands,handoff=self.advance('school')
        for bp in (91,93,98):
            m,r,e=copy.deepcopy(snapshots[bp]);r['eax']=0x22000000;rows=[]
            before=r.copy()
            self.assertEqual(run(commands[bp][1],m,r,e,rows),'gc')
            self.assertEqual(r,before);self.assertEqual(rows,[])

    def test_two_or_three_loads_follow_castle_byte4_not_owner_style(self):
        for route in probe.ROUTES:
            for availability in ('existing_flags','construct_all'):
                for variant in (0,1,2,128,255):
                    with self.subTest(route=route,availability=availability,variant=variant):
                        m,r,e,rows,s,c,h=self.advance(route,availability,variant=variant)
                        entry=next(x for x in rows if x.startswith('MCAP_ARTWORK_ENTRY'))
                        self.assertIn(f'variant_byte={variant} ',entry)
                        self.assertIn('style=1',next(x for x in rows if x.startswith('MCAP_CASTLE_STATE')))
                        loads=[x for x in rows if x.startswith('MCAP_CANVAS event=LOAD_CALL') and ' mirrors=0 ' in x]
                        expected=(0x4213C2,0x4214DC,0x42154A) if variant==1 else (0x4213C2,0x4214DC)
                        self.assertEqual(len(loads),len(expected))
                        for row,caller in zip(loads,expected):self.assertIn(f'caller={caller:08x}',row)
                        self.assertEqual(sum(x.startswith('MCAP_ARTWORK_RETURN') for x in rows),1)
                        self.assertEqual(rows[-1],'MCAP_SURFDUMP_HOST_READY')
        # Castle index and artwork selector are independent native inputs.
        *_,rows,snapshots,commands,handoff=self.advance('hospital','construct_all',index=2,variant=2)
        self.assertIn('index=2',next(x for x in rows if x.startswith('MCAP_CASTLE_STATE')))
        self.assertEqual(sum(x.startswith('MCAP_CANVAS event=LOAD_CALL') and ' mirrors=0 ' in x for x in rows),2)

    def test_native_load_pair_guards_reject_skips_repeats_wrong_callers_and_changed_selector(self):
        *_,snapshots,commands,handoff=self.advance('hospital','construct_all')
        for caller in (0x4213C2,0x4214DC,0x42154A):
            for wrong in (0x4213C2,0x4214DC,0x42154A,0x43DD37):
                if caller==wrong:continue
                m,r,e=copy.deepcopy(snapshots[(91,caller)]);rows=[];write(m,r['esp'],wrong)
                self.assertEqual(run(commands[91][1],m,r,e,rows),'q')
                self.assertFalse(any(x.startswith('MCAP_CANVAS') for x in rows))
        for bp in (92,99,100,101):
            m,r,e=copy.deepcopy(snapshots[bp]);r['$t9']-=1;rows=[]
            self.assertEqual(run(commands[bp][1],m,r,e,rows),'q')
        for bp in (99,100,101):
            m,r,e=copy.deepcopy(snapshots[bp]);write(m,r['$t1']+4,2,1);rows=[]
            self.assertEqual(run(commands[bp][1],m,r,e,rows),'q')
        m,r,e=copy.deepcopy(snapshots[98]);write(m,r['esp'],0x422043+1);rows=[]
        self.assertEqual(run(commands[98][1],m,r,e,rows),'q')
        for field,value in (('ebx',1),('edx',1),('ecx',0),('esp',snapshots[98][1]['esp']+4)):
            m,r,e=copy.deepcopy(snapshots[98]);r[field]=value;rows=[]
            self.assertEqual(run(commands[98][1],m,r,e,rows),'q')
        for folder in (5,0xFFFFFFFF):
            m,r,e=copy.deepcopy(snapshots[98]);write(m,0x5202EC,folder);rows=[]
            self.assertEqual(run(commands[98][1],m,r,e,rows),'q')
        # The observed native call has ended, but the final loader stays armed.
        # An extra owned load after its expected phase fails instead of hiding.
        m,r,e=copy.deepcopy(snapshots[99]);rows=[]
        self.assertEqual(run(commands[99][1],m,r,e,rows),'gc');self.assertIn(91,e)
        r.update(eip=0x4020A0,eax=NATIVE,esp=0x1000000-452);write(m,r['esp'],0x4213C2)
        self.assertEqual(run(commands[91][1],m,r,e,rows),'q')

    def test_artwork_observers_never_write_target_memory_or_general_registers(self):
        *_,snapshots,commands,handoff=self.advance('hospital','construct_all')
        for bp in (91,92,98,99,100,101):
            m,r,e=copy.deepcopy(snapshots[bp]);before=dict(m);gprs={k:v for k,v in r.items() if not k.startswith('$')};rows=[]
            self.assertEqual(run(commands[bp][1],m,r,e,rows),'gc')
            self.assertEqual(dict(m),before)
            self.assertEqual({k:v for k,v in r.items() if not k.startswith('$')},gprs)

    def test_six_resolutions_have_bounded_lines_and_no_state_writes(self):
        for w,h in ((800,600),(1024,768),(1280,720),(1280,960),(1920,1080),(802,602)):
            for route in probe.ROUTES.values():
                hand,c=probe._commands(route,w,h,3,'construct_all',METADATA)
                for bp,(va,body) in c.items():
                    self.assertLess(len(f'bp{bp} {va:08x} "{body}"'),4096)
                    self.assertNotIn('ed 005960',body)
                    if bp>=91:
                        self.assertNotIn('; ed ',body);self.assertNotIn('; eb ',body)
                self.assertEqual(hand.count('PTILE_TRACE_CLOSED'),1)
                self.assertNotIn('$t18',hand)
                self.assertNotIn('$t19',hand)


class SourceTests(unittest.TestCase):
    def test_exact_native_source_call_boundaries_for_every_supported_route(self):
        original=ORIGINAL.read_bytes()
        for route in probe.ROUTES.values():
            for va,old in probe._native_spans(route).items():
                self.assertEqual(probe._read(original,va,len(bytes.fromhex(old)))[1].hex(),old)
        # Independent source literals for the stack derivation used by the
        # trace validator: native draw saves20+8;421240 saves12+300.
        self.assertEqual(probe._read(original,0x422020,8)[1].hex(),'535152565783ec08')
        self.assertEqual(probe._read(original,0x421240,9)[1].hex(),'56575581ec2c010000')
        for va,offset in ((0x4213BF,0x207BF),(0x4214D9,0x208D9),(0x421547,0x20947)):
            self.assertEqual(probe._read(original,va,3),(offset,b'\xff\x56\x30'))
        self.assertEqual(probe._read(original,0x4214DC,14)[1].hex(),'a1646a52000fbe400483f8017560')
        self.assertEqual(probe._read(original,0x421737,1)[1],b'\xc3')

    def test_actual_1024_candidate_packets_compile_all_routes_and_fail_closed(self):
        import framed_modal_canvas_trace as trace
        original=ORIGINAL.read_bytes()
        canonical=probe.canonical_template(original,'1024x768',minimap_viewport=True)
        candidate,metadata,extra,template=canonical
        self.assertEqual(probe.sha(candidate),'c09940fac48e903538dd3a35688efb5ca5a65edaa6ad42cf6c804ca1c008d18d')
        # Cache only this already verified real reconstruction. Per-route
        # original/candidate span checks and compilation remain actual code.
        with patch.object(probe,'canonical_template',return_value=canonical):
            args=dict(candidate_sha256=probe.sha(candidate),stage=probe.STAGE,resolution='1024x768',
                      route='school',availability='existing_flags',castle_index=0,
                      rendered_probe=template,minimap_viewport=True)
            for route in probe.ROUTES:
                for availability in ('existing_flags','construct_all'):
                    packet=probe.build_screen_probe(original,candidate,**(args|{'route':route,'availability':availability}))
                    compiled=trace.compile_probe(packet)
                    self.assertLess(max(map(len,compiled.splitlines())),4096)
                    self.assertIn('MCAP_SURFDUMP_HOST_READY',compiled)
                    self.assertNotIn('bp81 00422181',compiled)
                    self.assertLess(compiled.index('.echo MCAP_BYTE_CONTRACT_PASS'),compiled.index('bp '))
                    self.assertEqual(packet['expected_capture_surface'],
                                     'borrowed physical HD mirror at owned canvas state.physical; E0 remains native640')
            changes=[{'stage':probe.builder.BASE_STAGE},{'candidate_sha256':'b'*64},
                     {'route':'court'},{'availability':'natural'},{'castle_index':True},
                     {'minimap_viewport':1},{'rendered_probe':template+'\n.echo ignored'}]
            for change in changes:
                with self.assertRaises(ValueError):probe.build_screen_probe(original,candidate,**(args|change))
            wrong=bytearray(candidate);wrong[0x300]=1
            with self.assertRaises(ValueError):
                probe.build_screen_probe(original,bytes(wrong),**(args|{'candidate_sha256':probe.sha(wrong)}))


if __name__=='__main__':unittest.main()
