"""Offline native key-pan producer fixtures; never runs Clash95 or CDB."""
from __future__ import annotations

import ast
import operator
from pathlib import Path
import re
import struct
import subprocess
import unittest
from unittest.mock import patch

import framed_army_keypan_probe as probe

ORIGINAL = Path('C:/Clash/clash95.exe')
SAVE = Path('C:/ClashTests/hd-completion/framed-screens-20260906-034725/workdir/save/0.dat')
CANDIDATE = Path('C:/ClashTests/hd-completion/framed-army-v1-1024x768-build-20260906-085300/clash95_army_1024x768_v1.exe')
CAPTURE = 'C:/ClashCaptures/offline-keypan-probe-fixture'


def expression(text, registers, memory):
    """Independent eager MASM integer subset, retaining sign-extended reads."""
    text = re.sub(r'\b(?:0x[0-9a-f]+|0n[0-9]+|[0-9a-f]+)\b',
        lambda m:str(int(m[0][2:],10) if m[0].startswith('0n') else int(m[0],16)),text)
    text = text.replace('@$','').replace('@','')
    binary = {ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,
        ast.LShift:operator.lshift,ast.BitAnd:operator.and_,ast.BitOr:operator.or_}
    comparisons = {ast.Eq:operator.eq,ast.NotEq:operator.ne,ast.Lt:operator.lt,
        ast.Gt:operator.gt,ast.LtE:operator.le,ast.GtE:operator.ge}
    def run(n):
        if isinstance(n,ast.Constant) and type(n.value) is int:return n.value
        if isinstance(n,ast.Name):return registers[n.id]
        if isinstance(n,ast.BinOp):return binary[type(n.op)](run(n.left),run(n.right))
        if isinstance(n,ast.Compare) and len(n.ops)==1:return comparisons[type(n.ops[0])](run(n.left),run(n.comparators[0]))
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and len(n.args)==1:
            value = memory.get(run(n.args[0]),0)
            return value if n.func.id=='poi' else value&((1<<{'wo':16,'by':8}[n.func.id])-1)
        raise AssertionError(ast.dump(n))
    return bool(run(ast.parse(text,mode='eval').body))


def conditions(text):
    result = []
    for match in re.finditer(r'\.if \(',text):
        start=match.end();depth=1;end=start
        while depth:
            if text[end]=='(':depth+=1
            elif text[end]==')':depth-=1
            end+=1
        result.append(text[start:end-1])
    return result


def command(packet,n):
    rows = re.findall(r'^bp'+str(n)+r' ([0-9a-f]{8}) "(.*)"$',packet['compiled_probe'],re.M)
    assert len(rows)==1
    return int(rows[0][0],16),rows[0][1]


@unittest.skipUnless(all(p.is_file() for p in (ORIGINAL,SAVE,CANDIDATE)),'exact user-owned source/save/candidate required')
class KeypanProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL.read_bytes();cls.candidate=CANDIDATE.read_bytes();cls.save=SAVE.read_bytes()
        cls.existed=Path(CAPTURE).exists();builder=probe.base.build_selection_probe
        def remember(*args,**kwargs):cls.baseline=builder(*args,**kwargs);return cls.baseline
        with patch.object(probe.base,'build_selection_probe',side_effect=remember):
            cls.packet=probe.build_keypan_probe(cls.original,cls.candidate,cls.save,capture_dir=CAPTURE)

    def test_source_binding_and_no_side_effects(self):
        p=self.packet
        self.assertEqual(p['candidate_sha256'],probe.sha(self.candidate));self.assertEqual(p['save_sha256'],probe.sha(self.save))
        self.assertEqual(p['base_compiled_probe_sha256'],self.baseline['probe_sha256'])
        self.assertEqual((ORIGINAL.read_bytes(),CANDIDATE.read_bytes(),SAVE.read_bytes()),(self.original,self.candidate,self.save))
        self.assertEqual(Path(CAPTURE).exists(),self.existed)
        for key in ('native_predicate_forced','camera_value_forced','unit_value_forced','runtime_executed','manual_input_proof','promotion_ready'):
            self.assertIs(p[key],False)
        for key in ('candidate','save','original'):
            args=dict(original=self.original,candidate=self.candidate,save=self.save)
            args[key]=args[key][:-1]+bytes([args[key][-1]^1])
            with self.assertRaises(ValueError):probe.build_keypan_probe(**args,capture_dir=CAPTURE)
        with patch.object(probe,'BASE_SHA256','0'*64),self.assertRaises(ValueError):
            probe.build_keypan_probe(self.original,self.candidate,self.save,capture_dir=CAPTURE)

    def test_loaded_byte_coverage_and_decoder_boundaries(self):
        checked={int(va,16):int(value,16) for va,value in re.findall(r'\(by\(([0-9a-f]{8})\) != 0x([0-9a-f]{2})\)',self.packet['compiled_probe'])}
        for va,size in probe.NATIVE_SPANS:
            self.assertEqual(bytes(checked[va+i] for i in range(size)),probe.base._read(self.candidate,va,size))
        for va,target in probe.NATIVE_CALLS.items():
            raw=probe.base._read(self.candidate,va,5)
            self.assertEqual(raw[0],0xE8)
            self.assertEqual(va+5+struct.unpack('<i',raw[1:])[0],target)
            self.assertEqual(self.packet['keypan_native_call_returns'][f'{va:08x}'],va+5)
        # Actual independent decoder walks contiguous native bodies. A byte
        # equal to C3 inside a CALL operand cannot masquerade as a RET boundary.
        decoded=set()
        for start,end in ((0x407D20,0x408022),(0x461570,0x461580),(0x418700,0x418719)):
            result=subprocess.run(['wsl.exe','--exec','/usr/bin/objdump','-d','-M','intel','--insn-width=16',
                f'--start-address={start:#x}',f'--stop-address={end:#x}',
                '/mnt/c/ClashTests/hd-completion/framed-army-v1-1024x768-build-20260906-085300/clash95_army_1024x768_v1.exe'],
                check=True,capture_output=True,text=True,timeout=30)
            decoded.update(int(x,16) for x in re.findall(r'^\s*([0-9a-f]+):\s',result.stdout,re.M))
        self.assertTrue(set(self.packet['keypan_observer_vas'].values())<=decoded)
        self.assertNotIn(0x407DE2,decoded)
        prior={int(va,16) for va in re.findall(r'^bp[0-9]+ ([0-9a-f]{8}) ',self.baseline['compiled_probe'],re.M)}
        observers=list(self.packet['keypan_observer_vas'].values())
        self.assertFalse(prior.intersection(observers));self.assertEqual(len(observers),len(set(observers)))
        self.assertEqual(probe.base._read(self.candidate,0x407DDD,6),bytes.fromhex('8990e8220200'))
        self.assertEqual(probe.base._read(self.candidate,0x407DD3,3),bytes.fromhex('83ea0f'))

    def state(self,n):
        s=0x800000;gd=0x600000;u=gd+149349
        phase=20+n-100 if n<=117 else 39
        depth=8 if n==100 else 32 if n==108 else 4 if n in (117,118) else 28
        r=dict(tid=7,t2=7,t1=gd,t3=s,t0=phase,esp=s-depth,eip=self.packet['keypan_observer_vas'][str(n)],
            eax=0,ebx=101,ecx=102,edx=103,esi=104,edi=105,ebp=106,t5=0,t6=0,t7=0,t10=0)
        m={0x5202E4:gd,0x5199D8:0x40AD40,0x526990:0,0x5202EC:0,0x511B58:3,0x514194:3,0x526994:1,0x526FA0:u,
            u:16,u+2:19,u+4:0,u+316:0,gd+140008:10 if n<=105 else 11,gd+140012:17,gd+147171:8,
            0x545299:128 if n<=106 else 0,0x5202A0:1000,0x545140:0,0x544D04:0,0x5451C0:0,
            0x5202E0:0x900000,0x900000:1024,0x900002:768,0x900004:0xA00000,0x9000B8:0x50EE24}
        m.update({0x526F78+4*i:0 for i in range(10)})
        m.update({u+14+31*i:ap for i,ap in enumerate((26,22,16,16,16,16,16,16))})
        if n==100:m[r['esp']]=r['ebx'];m[r['esp']+4]=0x406FA1
        if n==101:r['eax']=1009;r['edx']=1008
        if n==104:r['eax']=1
        if n in (105,106):r.update(eax=gd,edx=11,ebp=10)
        if n in (107,108):r.update(eax=1,ecx=1)
        if n==108:m[r['esp']]=0x407DFC
        if n>=107:r['t10']=1
        if n>=109:r.update(t5=1,t6=1,t7=1)
        if n==109:r['ecx']=1
        if n in (117,118):m[r['esp']]=0x406FA1
        for num,reg in enumerate(('ebx','ecx','edx','esi','edi','ebp'),14):r[f't{num}']=r[reg]
        return r,m

    def test_every_phase_thread_stack_owner_camera_and_flags(self):
        for n in range(100,119):
            r,m=self.state(n);guard=conditions(command(self.packet,n)[1])[0]
            self.assertTrue(expression(guard,r,m),(n,guard))
            for field,value in (('tid',8),('t0',99),('esp',r['esp']+4)):
                self.assertFalse(expression(guard,r|{field:value},m),(n,field))
            for address,value in ((0x5199D8,0),(0x526990,1),(0x5202EC,1),(0x511B58,2),(0x514194,2),(0x526994,0),(0x526FA0,0),
                (r['t1']+140008,12),(r['t1']+140012,18)):
                self.assertFalse(expression(guard,r,m|{address:value}),(n,address))
            for slot in range(10):
                self.assertFalse(expression(guard,r,m|{0x526F78+4*slot:1}),(n,slot))
            self.assertIn('KPAN_REJECT_CONTEXT phase=%d tid=%x eip=%p esp=%p',command(self.packet,n)[1])

    def test_native_time_and_key_results_are_never_forced(self):
        r,m=self.state(101);guard=conditions(command(self.packet,101)[1])[0]
        for now,threshold,last,expected in ((1009,1008,1000,True),(1008,1008,1000,False),(1007,1008,1000,False),
            (0xFFFFFFFFFFFFFFFF,0xFFFFFFFFFFFFFFFE,0xFFFFFFFFFFFFFFF6,True),
            (1,0,0xFFFFFFFFFFFFFFF8,True),(0,0,0xFFFFFFFFFFFFFFF8,False),(1,0xFFFFFFFF,0xFFFFFFF7,False)):
            self.assertEqual(expression(guard,r|{'eax':now,'edx':threshold},m|{0x5202A0:last}),expected)
        self.assertLess(command(self.packet,101)[1].index('kind=time-sample'),command(self.packet,101)[1].index('.if ('))
        for n in (102,103,104,110,111,112,113,114,115,116,118):
            r,m=self.state(n);guard=conditions(command(self.packet,n)[1])[0]
            self.assertFalse(expression(guard,r|{'eax':1-r['eax']},m),n)
        new='\n'.join(command(self.packet,n)[1] for n in range(100,119))
        self.assertNotRegex(new,r'\b(?:r eax|ed 005202a0|ed @\$t1)')

    def test_store_release_single_redraw_and_abi(self):
        for n in (105,106):
            r,m=self.state(n);guard=conditions(command(self.packet,n)[1])[0]
            for field,value in (('eax',r['eax']+4),('edx',12),('ebp',11),('t10',1)):
                self.assertFalse(expression(guard,r|{field:value},m),(n,field))
        text=command(self.packet,106)[1]
        self.assertLess(text.index('kind=store-after'),text.index('r @$t10=1'))
        self.assertLess(text.index('kind=release-before'),text.index('eb 00545299 00'))
        self.assertLess(text.index('eb 00545299 00'),text.index('kind=release-after'))
        for n in (117,118):
            r,m=self.state(n);guard=conditions(command(self.packet,n)[1])[0]
            for reg in ('ebx','ecx','edx','esi','edi','ebp'):
                self.assertFalse(expression(guard,r|{reg:r[reg]^1},m),(n,reg))
        r,m=self.state(109);r.update(t0=29,esp=r['t3']-272,t5=0,t6=0,t7=0)
        ret=self.packet['baseline_native_call_returns']['composition_draw'];m[r['esp']]=ret
        guard=conditions(command(self.packet,90)[1])[-1]
        self.assertTrue(expression(guard,r,m))
        for field,value in (('esp',r['esp']-4),('t5',1),('t0',30)):
            self.assertFalse(expression(guard,r|{field:value},m),(90,field))
        r.update(t5=1,t8=r['esp'],t9=ret,eax=1);r['esp']+=4
        guard=conditions(command(self.packet,92)[1])[-1]
        self.assertTrue(expression(guard,r,m))
        for field,value in (('eax',0),('t6',1),('t7',1),('esp',r['esp']+4)):
            self.assertFalse(expression(guard,r|{field:value},m),(92,field))
        self.assertIn('KPAN_REJECT unexpected_native_draw; q',command(self.packet,91)[1])

    def test_checkpoint_all256_keys_and_unit_guards(self):
        for index in (0,1):
            text=self.packet['supplemental_commands'][f'{CAPTURE}/keypan-checkpoint-{index}.cdb']
            guards=conditions(text)
            r,m=self.state(118);r.update(esp=r['t3'],eip=0x406FA1,t0=40 if index else 10)
            m[r['t1']+140008]=10+index
            self.assertTrue(all(expression(g,r,m) for g in guards))
            for byte in range(256):
                address=0x5451CC+(byte//4)*4
                mutated=m|{address:0x80<<((byte%4)*8)}
                results=[expression(g,r,mutated) for g in guards[2:6]]
                self.assertEqual(results.count(False),1,(index,byte))
            for address,value in ((r['t1']+149349,17),(r['t1']+149349+2,20),(r['t1']+149349+316,1),
                (r['t1']+149349+14,25),(0x544D04,1),(0x5451C0,128),(0x545140,1)):
                self.assertFalse(expression(guards[0],r,m|{address:value}),(index,address))
            self.assertLess(text.index('block=3'),text.index('KPAN_SURFACE'))
            self.assertIn(f'keypan-{("before","after")[index]}.keyboard.raw 005451cc L0n256',text)
        text=self.packet['supplemental_commands'][f'{CAPTURE}/keypan-checkpoint-0.cdb']
        self.assertNotIn('be 118',text)
        self.assertLess(command(self.packet,80)[1].index('kind=pan-return'),command(self.packet,80)[1].index('be 118'))

    def test_transport_baseline_integrity_and_write_allowlist(self):
        p=self.packet;all_text=p['compiled_probe']+'\n'+'\n'.join(p['supplemental_commands'].values())
        self.assertEqual(all_text.count('KPAN_HOST_READY'),1);self.assertNotIn('KPAN_BASE_HOST_READY',all_text)
        self.assertNotIn('SHSEL_',all_text);self.assertLess(max(map(len,all_text.splitlines())),4096)
        for n in range(81,90):self.assertEqual(command(p,n)[1],command(self.baseline,n)[1].replace('SHSEL_','KPAN_BASE_'))
        self.assertEqual(p['initial_extra'],self.baseline['initial_extra'])
        for i,name in enumerate(('keypan-before','keypan-after')):
            path=f'{CAPTURE}/keypan-checkpoint-{i}.cdb';text=p['supplemental_commands'][path]
            self.assertEqual(p['supplemental_sha256'][path],probe.sha(text.encode('ascii')))
            self.assertNotIn(r'\"',text);self.assertNotIn(r'\\n',text);self.assertNotIn('$$ ',text)
            self.assertIn('$$>a<\\"'+path+'\\";',command(p,80)[1])
            self.assertIn(f'{name}.header.raw poi(005202e0) L0n188',text)
            self.assertIn(f'{name}.raw poi(poi(005202e0)+4) L0n786432',text)
            self.assertIn(f'{name}.unit.raw @$t1+0n149349 L0n725',text)
        # Check only newly authored controls; inherited baseline's camera/mouse
        # writes stay byte-identical and explicitly documented separately.
        new='\n'.join(command(p,n)[1] for n in range(100,119))+'\n'+'\n'.join(p['supplemental_commands'].values())
        self.assertEqual(set(re.findall(r'\b(?:eb|ed|ew|eq)\s+([^ ;]+)',new)),{'00545299','@esp'})
        regwrites=re.findall(r'\br\s+([^ =;]+)=',new)
        self.assertTrue(all(name.startswith('@$t') or name in ('esp','eip') for name in regwrites),regwrites)
        stop=command(p,80)[1];self.assertEqual(stop.count('r eax=0n205'),1)
        self.assertIn('r eip=00461570',stop);self.assertNotIn('r eax=0;',stop)
        for line in all_text.splitlines():
            if '.printf ' in line:
                normalized=line.replace(r'\"','"').replace(r'\\n',r'\n')
                for fmt,args in re.findall(r'\.printf "([^"\n]+)"([^;}]*)',normalized):
                    self.assertEqual(len(re.findall(r'%(?:I64)?(?:0?[0-9]+)?[dxXpsu]',fmt)),len([a for a in args.split(',') if a.strip()]),fmt)


if __name__ == '__main__':unittest.main()
