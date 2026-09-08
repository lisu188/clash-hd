"""Execute emitted command branches offline; no CDB, game or binary output."""
from __future__ import annotations

import copy
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import framed_battle_initial_probe as probe
from test_framed_screen_probe import Memory, run, state, write

ORIGINAL=Path('C:/Clash/clash95.exe')
SAVE=Path('C:/Clash/save/0.dat')
STATE=0x596000
RESOLUTIONS=('800x600','1024x768','1280x720','1280x960','1920x1080','802x602')


def battle_state(width=800,height=600,state_va=STATE):
    m,r,e,rows=state(width,height)
    gd=0x10000000;att=gd+0x23ee6;defender=gd+0x24a3a
    for i in range(128):m[state_va+i]=0
    for address,value,size in ((0x5202ec,0,4),(gd+0x22313,1,4),(gd+0x228a2,0,4),
            (att,0x0016000e,4),(att+4,0,1),(att+6,5,2),(att+0x25,0xffff,2),(att+0x2d0,0,1),
            (defender,0x0009005a,4),(defender+4,1,1),(defender+6,5,2),(defender+0x25,0xffff,2),
            (defender+0x2d0,0,1),(0x51d01c,0,4)):
        write(m,address,value,size)
    r['edi']=66
    return m,r,e,rows


def advance(width=800,height=600,state_va=STATE):
    handoff,commands=probe._commands(width,height,state_va)
    m,r,e,rows=battle_state(width,height,state_va)
    before=dict(m);h=r['esp'];snapshots={}
    assert run(handoff,m,r,e,rows)=='gc'
    assert r['eip']==0x41ad20 and r['esp']==h-4
    # Execute only the independently authenticated first native opcode53.
    # Remaining native work below is explicitly modeled, never claimed run.
    assert probe.shared._read(ORIGINAL.read_bytes(),0x41ad20,1)[1]==b'\x53'
    r['esp']-=4;write(m,r['esp'],r['ebx'])
    def hit(bp,**changes):
        r.update(changes);r['eip']=commands[bp][0]
        snapshots[bp]=(Memory(m),r.copy(),e.copy())
        return run(commands[bp][1],m,r,e,rows)
    assert hit(81)=='gc'
    assert hit(82,esp=h-860,eax=1,ebp=0x10023ee6)=='gc'
    assert hit(83,ecx=1)=='gc'
    write(m,h-864,0)
    assert hit(84,esp=h-864,eax=0x10023ee6,edx=0x10024a3a,ebx=0,ecx=0)=='gc'
    write(m,h-868,0x41b14a)
    assert hit(85,esp=h-868)=='gc'
    for a,v in ((0x532048,0x22000000),(0x5199d8,0x42e8b0),(0x5202ec,0),(0x511b58,0),
                (0x53204c,0x23000000),(0x532050,0x23010000),(0x532054,0x23020000),
                (0x532058,0x23030000),(0x5202bc,0x23040000)):
        write(m,a,v)
    write(m,0x22000344,0);write(m,0x22000f68,0);write(m,0x22000354,5,2)
    assert hit(86,esp=h-1036,eax=0x544cd8)=='gc'
    write(m,h-1040,0x42f2fa)
    assert hit(87,esp=h-1040)=='gc'
    assert hit(88,esp=h-1036) is None
    return m,r,e,rows,snapshots,commands,handoff,before


class Commands(unittest.TestCase):
    def test_six_geometries_real_emitted_order_and_exact_mutations(self):
        for res in RESOLUTIONS:
            w,h=map(int,res.split('x'))
            m,r,e,rows,s,c,hand,before=advance(w,h)
            self.assertEqual(rows[-1],'BINIT_SURFDUMP_HOST_READY')
            self.assertIn(f'size=({w},{h}) bytes={w*h}',rows[-2])
            self.assertFalse(e & set(range(70,90)))
            self.assertNotIn(0x41ad20,[x[0] for x in c.values()])
            self.assertEqual(c[81][0],0x41ad21)
            # Emitted commands, separately from explicitly modeled native
            # progression, write only the return stack, packedXY and UI flag.
            actor=s[81][0];reg=s[81][1];en=s[81][2];original=dict(actor)
            self.assertEqual(run(c[81][1],actor,reg,en,[]),'gc')
            changed={a for a in original if original[a]!=actor[a]}
            self.assertEqual(changed,{0x10023ee6,0x10023ee8,0x51d01c})
            self.assertEqual(actor[0x10024a3a],0x5a)

    def test_handoff_null_ownership_geometry_state_fail_before_target_writes(self):
        hand,_=probe._commands(800,600,STATE)
        changes=[(0x5202e4,0),(0x5202e0,0),(0x5202ec,1),(0x5199d8,0x42e8b0),
                 (0x526990,1),(0x526994,1),(0x20000000,640),(0x20000004,0),
                 (0x200000b8,0x50eec4)]
        changes += [(STATE+i,1) for i in range(0,128,4)]
        for address,value in changes:
            m,r,e,rows=battle_state();write(m,address,value);before=dict(m)
            self.assertEqual(run(hand,m,r,e,rows),'q',(address,value,rows))
            self.assertEqual(m,before)
            self.assertFalse(any('FORCE_CALL' in x for x in rows))
        for field,value in (('eip',0x406fa1),('$t13',5),('$t7',0),('$t14',0)):
            m,r,e,rows=battle_state();r[field]=value;before=dict(m)
            self.assertEqual(run(hand,m,r,e,rows),'q');self.assertEqual(m,before)

    def test_post_push_exact_actor_fields_and_stack_fail_before_actor_writes(self):
        _,_,_,_,snap,c,_,_=advance()
        changes=[(0x10023ee6,0x0016000f,4),(0x10024a3a,0x00090059,4),
                 (0x10023eea,1,1),(0x10024a3e,0,1),(0x10023eec,8,2),
                 (0x10023f0b,5,2),(0x100241b6,1,1),(0x10024a40,0xffff,2),
                 (0x100222e0,99,4),(0x100222e4,99,4),(0x10022313,0,4),
                 (0x100228a2,1,4),(0x5202ec,1,4),(0x00fffff8,99,4),(0x00fffffc,0x406fa0,4)]
        for address,value,size in changes:
            m,r,e=copy.deepcopy(snap[81]);write(m,address,value,size);before=dict(m);rows=[]
            self.assertEqual(run(c[81][1],m,r,e,rows),'q',(hex(address),rows))
            self.assertEqual(m,before);self.assertFalse(any('MUTATION' in x for x in rows))

    def test_every_native_observer_rejects_wrong_phase_thread_eip_stack_and_repeat(self):
        *_,snap,c,hand,before=advance()
        for bp in range(81,89):
            for key,delta in (('$tid',1),('esp',4),('eip',1),('$t0',100)):
                m,r,e=copy.deepcopy(snap[bp]);r[key]+=delta;rows=[]
                self.assertEqual(run(c[bp][1],m,r,e,rows),'q',(bp,key,rows))
            m,r,e=copy.deepcopy(snap[bp]);rows=[]
            self.assertIn(run(c[bp][1],m,r,e,rows),('gc',None))
            self.assertEqual(run(c[bp][1],m,r,e,rows),'q',bp)
        for bp in (80,89):
            m,r,e,_=battle_state();r['eip']=c[bp][0];rows=[]
            self.assertEqual(run(c[bp][1],m,r,e,rows),'q')
            self.assertNotIn('BINIT_SURFDUMP_HOST_READY',rows)

    def test_native_gates_and_runner_arguments_are_observed_never_forced(self):
        *_,snap,c,hand,before=advance()
        for bp,key,value in ((82,'eax',0),(82,'ebp',0x10024a3a),(83,'ecx',0),
                             (84,'eax',0),(84,'edx',0),(84,'ebx',1),(84,'ecx',1),
                             (85,'eax',0),(86,'eax',0),(87,'eax',0)):
            m,r,e=copy.deepcopy(snap[bp]);r[key]=value;prior=r.copy();rows=[]
            self.assertEqual(run(c[bp][1],m,r,e,rows),'q',(bp,key,rows))
            self.assertEqual(r,prior)
        for bp,off,value in ((84,0,1),(85,0,0x41b145),(85,4,1),(87,0,0x42f2f5)):
            m,r,e=copy.deepcopy(snap[bp]);write(m,r['esp']+off,value)
            self.assertEqual(run(c[bp][1],m,r,e,[]),'q')
        self.assertFalse(any(re.search(r'\br (?:eax|ecx|edx|ebx|esp|eip)=',body) for _,body in c.values()))

    def test_ready_rejects_changed_all_zero_state_surface_resources_and_overflow(self):
        *_,snap,c,hand,before=advance()
        for address,value in [(STATE+i,1) for i in range(0,128,4)]+[
            (0x5202e0,0),(0x20000004,0x21000004),(0x20000000,640),(0x200000b8,0x50eec4),
            (0x5199d8,0x40ad40),(0x532048,0),(0x532048,0xfffff000),(0x53204c,0),
            (0x532050,0),(0x532054,0),(0x532058,0),(0x5202bc,0),(0x5202ec,5),(0x511b58,22),
            (0x22000344,1),(0x22000f68,1),(0x22000354,0xffff)]:
            m,r,e=copy.deepcopy(snap[88]);write(m,address,value);rows=[]
            self.assertEqual(run(c[88][1],m,r,e,rows),'q',(hex(address),rows))
            self.assertNotIn('BINIT_SURFDUMP_HOST_READY',rows)


class Binding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL.read_bytes();cls.save=SAVE.read_bytes()
        cls.candidate,cls.metadata,cls.extra,cls.template=probe.canonical_template(cls.original,'1024x768',minimap_viewport=True)

    def packet(self,**changes):
        args=dict(candidate_sha256=probe.sha(self.candidate),stage=probe.STAGE,resolution='1024x768',route=probe.ROUTE,minimap_viewport=True)
        args.update(changes)
        return probe.build_probe(self.original,self.candidate,self.save,**args)

    def test_real_candidate_c099_native_bytes_all_compiled_collisions_and_lengths(self):
        self.assertEqual(probe.sha(self.candidate),'c09940fac48e903538dd3a35688efb5ca5a65edaa6ad42cf6c804ca1c008d18d')
        packet=self.packet();compiled=probe.compiler.compile_probe(packet)
        self.assertLess(max(map(len,compiled.splitlines())),4096)
        self.assertEqual(compiled.count('BINIT_SURFDUMP_HOST_READY'),1)
        self.assertNotIn('MCAP_SURFDUMP_HOST_READY',compiled)
        self.assertLess(compiled.index('BINIT_BYTE_CONTRACT_PASS'),compiled.index('bp 004'))
        self.assertEqual(packet['host_read_contract']['state_bytes'],128)
        self.assertFalse(packet['host_read_contract']['primary_capture'])
        for row in packet['byte_spans']:
            va=row['va'];new=bytes.fromhex(row['candidate_hex'])
            self.assertEqual(probe.shared._read(self.candidate,va,len(new))[1],new)
            if va==probe.RUNNER:
                old=bytearray.fromhex(row['old_hex']);i=probe.PRESENT_CALL-va
                old[i:i+5]=bytes.fromhex('e806c70e00');self.assertEqual(bytes(old),new)
        for resolution in RESOLUTIONS:
            w,h=map(int,resolution.split('x'));hand,commands=probe._commands(w,h,STATE)
            self.assertLess(max(map(len,[hand]+[body for _,body in commands.values()])),4096)

    def test_unknown_stage_route_save_sha_profile_or_candidate_refused(self):
        for changes in ({'stage':probe.builder.BASE_STAGE},{'route':'battle_results'},
                        {'candidate_sha256':'a'*64},{'minimap_viewport':1}):
            with self.assertRaises(ValueError):self.packet(**changes)
        for original,candidate,save in ((self.original,self.candidate,self.save[:-1]+b'X'),
            (self.original,self.candidate[:-1]+b'X',self.save),(self.original[:-1]+b'X',self.candidate,self.save)):
            with self.assertRaises(ValueError):probe.build_probe(original,candidate,save,
                candidate_sha256=probe.sha(candidate),stage=probe.STAGE,resolution='1024x768',route=probe.ROUTE,minimap_viewport=True)
        with patch.object(probe,'COMPILER_SHA256','0'*64):
            with self.assertRaisesRegex(ValueError,'dependency'):self.packet()


if __name__=='__main__':unittest.main()
