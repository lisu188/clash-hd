"""Offline portrait producer/source/guard contracts; no runtime or artifact writes."""
from __future__ import annotations
import ast
import operator
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import framed_army_portrait_probe as probe

ORIGINAL=Path('C:/Clash/clash95.exe')
SAVE=Path('C:/Clash/save/0.dat')
CANDIDATE=Path('C:/ClashTests/hd-completion/framed-army-v1-1024x768-build-20260906-085300/clash95_army_1024x768_v1.exe')
CAPTURE='C:/ClashCaptures/offline-portrait-probe-fixture'


def expression(text,registers,memory):
    """Independent bounded MASM integer predicate oracle; preserves raw DWORDs."""
    text=re.sub(r'\b(?:0x[0-9a-f]+|0n[0-9]+|[0-9a-f]+)\b',
                lambda m:str(int(m[0][2:],10) if m[0].startswith('0n') else int(m[0],16)),text)
    text=text.replace('@$','').replace('@','')
    binary={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.LShift:operator.lshift,
            ast.BitAnd:operator.and_,ast.BitOr:operator.or_}
    comparisons={ast.Eq:operator.eq,ast.NotEq:operator.ne,ast.Lt:operator.lt,ast.Gt:operator.gt,
                 ast.LtE:operator.le,ast.GtE:operator.ge}
    def run(node):
        if isinstance(node,ast.Constant) and type(node.value) is int:return node.value
        if isinstance(node,ast.Name):return registers[node.id]
        if isinstance(node,ast.BinOp) and type(node.op) in binary:return binary[type(node.op)](run(node.left),run(node.right))
        if isinstance(node,ast.Compare) and len(node.ops)==1 and type(node.ops[0]) in comparisons:
            return comparisons[type(node.ops[0])](run(node.left),run(node.comparators[0]))
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and len(node.args)==1:
            # Unseeded fixture stack/data locations are zero-filled. In
            # particular a deliberately wrong ESP must reject its equality,
            # not abort the eager bitwise predicate oracle with KeyError.
            value=memory.get(run(node.args[0]),0)
            return value if node.func.id=='poi' else value&((1<<{'wo':16,'by':8}[node.func.id])-1)
        raise AssertionError(ast.dump(node))
    return bool(run(ast.parse(text,mode='eval').body))


def command(packet,number):
    rows=re.findall(r'^bp'+str(number)+r' ([0-9a-f]{8}) "(.*)"$',packet['compiled_probe'],re.M)
    assert len(rows)==1
    return int(rows[0][0],16),rows[0][1]


def conditions(text):
    results=[]
    for match in re.finditer(r'\.if \(',text):
        start=match.end();depth=1;end=start
        while depth:
            if text[end]=='(':depth+=1
            elif text[end]==')':depth-=1
            end+=1
        results.append(text[start:end-1])
    return results


@unittest.skipUnless(all(p.is_file() for p in (ORIGINAL,SAVE,CANDIDATE)),'exact user-owned source/save/candidate required')
class PortraitProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL.read_bytes();cls.save=SAVE.read_bytes();cls.candidate=CANDIDATE.read_bytes()
        cls.existed=Path(CAPTURE).exists();build=probe.base.build_selection_probe
        def remember(*args,**kwargs):cls.baseline=build(*args,**kwargs);return cls.baseline
        with patch.object(probe.base,'build_selection_probe',side_effect=remember):
            cls.packet=probe.build_portrait_probe(cls.original,cls.candidate,cls.save,capture_dir=CAPTURE)

    def test_complete_unchanged_candidate_save_and_source_binding(self):
        p=self.packet
        self.assertEqual(p['candidate_sha256'],probe.sha(self.candidate));self.assertEqual(p['save_sha256'],probe.sha(self.save))
        self.assertEqual(p['base_compiled_probe_sha256'],self.baseline['probe_sha256'])
        self.assertEqual(p['flag_vectors'],[[0]*10,[1]+[0]*9,[0]*10]);self.assertEqual(p['controlled_mouse'],[54,719])
        self.assertEqual((ORIGINAL.read_bytes(),SAVE.read_bytes(),CANDIDATE.read_bytes()),(self.original,self.save,self.candidate))
        self.assertEqual(Path(CAPTURE).exists(),self.existed)
        for name in ('runtime_executed','manual_input_proof','promotion_ready','native_predicate_forced','selected_value_forced','flag_value_forced'):
            self.assertIs(p[name],False)
        for key in ('candidate','save'):
            args=dict(original=self.original,candidate=self.candidate,save=self.save);data=bytearray(args[key]);data[-1]^=1;args[key]=bytes(data)
            with self.assertRaises(ValueError):probe.build_portrait_probe(**args,capture_dir=CAPTURE)
        with patch.object(probe,'BASE_SHA256','0'*64),self.assertRaises(ValueError):
            probe.build_portrait_probe(self.original,self.candidate,self.save,capture_dir=CAPTURE)

    def test_actual_native_call_old_bytes_and_complete_loaded_spans(self):
        checked={int(va,16):int(value,16) for va,value in re.findall(r'\(by\(([0-9a-f]{8})\) != 0x([0-9a-f]{2})\)',self.packet['compiled_probe'])}
        for va,size in probe.NATIVE_SPANS:
            for i,value in enumerate(probe.base._read(self.candidate,va,size)):self.assertEqual(checked[va+i],value)
        for va,target in probe.NATIVE_CALLS.items():
            self.assertEqual(self.packet['portrait_native_call_returns'][f'{va:08x}'],probe.base._call_return(self.candidate,va,target))
        self.assertEqual(probe.base._read(self.candidate,0x423952,8).hex(),'8034b5786f520001')
        # New observers do not collide with any inherited observer address.
        prior_addresses={int(va,16) for va in re.findall(r'^bp[0-9]+ ([0-9a-f]{8}) ',self.baseline['compiled_probe'],re.M)}
        self.assertFalse(prior_addresses.intersection(self.packet['portrait_observer_vas'].values()))
        self.assertEqual(set(self.packet['portrait_observer_vas']),{str(n) for n in range(100,117)})

    def test_baseline_is_retained_without_a_false_host_ready_or_duplicate_draw_bp(self):
        p=self.packet
        for n in range(81,90):
            old=command(self.baseline,n);new=command(p,n)
            self.assertEqual(new,(old[0],old[1].replace('SHSEL_','PTGL_BASE_')))
        for n in (90,91,92):
            self.assertIn(command(self.baseline,n)[1].replace('SHSEL_','PTGL_BASE_'),command(p,n)[1])
        all_text=p['compiled_probe']+'\n'+'\n'.join(p['supplemental_commands'].values())
        self.assertNotIn('SHSEL_',all_text);self.assertNotIn('PTGL_BASE_HOST_READY',all_text)
        self.assertEqual(all_text.count('PTGL_HOST_READY'),1)
        self.assertEqual(p['initial_extra'],self.baseline['initial_extra'])
        self.assertIn('r @$t10=0;',p['supplemental_commands'][CAPTURE+'/portrait-checkpoint-0.cdb'])

    def state(self,number,toggle=1):
        phase={100:20,101:21,102:22,103:23,104:24,105:25,106:26,107:27,108:28,109:29,110:30,111:31,112:32,113:33,114:34}[number]
        depth={100:8,101:68,102:68,103:68,104:68,105:68,106:68,107:72,108:68,109:72,110:84,111:84,112:68,113:68,114:4}[number]
        r=dict(tid=7,t2=7,t1=0x600000,t3=0x800000,t10=toggle,t0=phase,esp=0x800000-depth,
               eax=0,ecx=0,edx=0,esi=0,edi=0,t5=0,t6=0,t7=0)
        m={0x5202E4:0x600000,0x5199D8:0x40AD40,0x526990:0,0x5202EC:0,
           0x511B58:3,0x514194:3,0x526994:1,0x526FA0:0x600000+149349,
           0x600000+149349+6:16,0x544CFC:54<<2,0x544D00:719<<2,0x54512C:2,
           0x544D04:0 if number>=109 else 1,0x5451C0:0 if number>=109 else 0x80,
           0x5202E0:0x900000,0x900000:1024,0x900002:768,0x900004:0xA00000,0x9000B8:0x50EE24}
        m.update({0x526F78+4*i:0 for i in range(10)})
        m[0x526F78]=toggle-1 if number<=104 else 2-toggle
        if number==100:m[r['esp']+4]=0x406FA1
        if number==103:r['eax']=1
        if number==104:r['eax']=16
        if number==106:r.update(t5=1,t6=1)
        if number==107:r['eax']=1;m[r['esp']]=0x423970
        if number>=108:r.update(t5=2,t6=2,t7=1)
        if number==109:r['eax']=0x544CD8;m[r['esp']]=0x42397A
        if number==113:r['edi']=1
        if number==114:r['eax']=1;m[r['esp']]=0x406FA1
        return r,m

    def test_every_native_guard_binds_both_toggle_vectors_thread_phase_stack_and_owner(self):
        for toggle in (1,2):
            for number in range(100,115):
                guard=conditions(command(self.packet,number)[1])[0];r,m=self.state(number,toggle)
                self.assertTrue(expression(guard,r,m),(number,toggle))
                for field,value in (('tid',8),('t0',99),('t10',3),('esp',r['esp']-4)):
                    self.assertFalse(expression(guard,r|{field:value},m),(number,toggle,field))
                for address,value in ((0x5199D8,0),(0x526990,1),(0x5202EC,1),(0x511B58,1),(0x514194,2),(0x526994,0),(0x526FA0,0x600000+149350)):
                    self.assertFalse(expression(guard,r,m|{address:value}),(number,toggle,address))
                for slot in range(10):
                    addr=0x526F78+4*slot;self.assertFalse(expression(guard,r,m|{addr:m[addr]^1}),(number,toggle,slot))

    def test_actual_predicates_xor_release_and_movement_are_not_faked(self):
        for number,field,wrong in ((102,'eax',1),(103,'eax',0),(104,'eax',-1),(101,'esi',1),(101,'edi',1),
                                   (109,'eax',0),(110,'eax',1),(111,'eax',1),(112,'eax',1),(113,'eax',1),(114,'eax',0)):
            r,m=self.state(number);guard=conditions(command(self.packet,number)[1])[0]
            self.assertFalse(expression(guard,r|{field:wrong},m),(number,field))
        for number in (109,110,111,112,113):
            r,m=self.state(number);self.assertFalse(expression(conditions(command(self.packet,number)[1])[0],r,m|{0x544D04:1}),number)
        release=command(self.packet,108)[1]
        self.assertLess(release.index('kind=release-before'),release.index('eb 005451c0 00'))
        self.assertLess(release.index('ed 00544d04 0'),release.index('kind=release-after'))
        for number in (115,116):
            self.assertIn('PTGL_REJECT movement_route; q',command(self.packet,number)[1]);self.assertNotIn('; gc',command(self.packet,number)[1])

    def test_extended_draw_observers_require_actual_success_and_return_pairs(self):
        for toggle in (1,2):
            for number,phase,route,count in ((90,26,'native',0),(90,28,'composition',1),(91,26,'native',1),(92,28,'composition',2)):
                guard=conditions(command(self.packet,number)[1])[-1]
                r,m=self.state(106,toggle);va=self.packet['baseline_native_call_returns']['native_draw' if route=='native' else 'composition_draw']
                entry=r['t3']-(188 if route=='native' else 312)
                r.update(t0=phase,t5=count,t6=count if number==90 else count-1,t8=entry,t9=va,eax=1)
                r['esp']=entry if number==90 else entry+4;m[r['esp']]=va
                self.assertTrue(expression(guard,r,m),(number,phase))
                for field,value in (('t5',99),('t0',25),('t10',3)):
                    self.assertFalse(expression(guard,r|{field:value},m),(number,field))
                if number!=90:
                    self.assertFalse(expression(guard,r|{'eax':0},m));self.assertFalse(expression(guard,r|{'esp':r['esp']+4},m))
                else:
                    self.assertFalse(expression(guard,r,m|{r['esp']:0x400000}))
                    self.assertFalse(expression(guard,r|{'esp':r['esp']-4},m|{r['esp']-4:va}))

    def test_supplemental_paths_transport_printf_and_target_write_allowlist(self):
        p=self.packet;files=p['supplemental_commands']
        self.assertEqual(set(files),{CAPTURE+f'/portrait-checkpoint-{n}.cdb' for n in range(3)})
        all_text=p['compiled_probe']+'\n'+'\n'.join(files.values())
        self.assertLess(max(map(len,all_text.splitlines())),4096)
        for path,text in files.items():
            self.assertEqual(p['supplemental_sha256'][path],probe.sha(text.encode('ascii')))
            self.assertNotIn(r'\"',text);self.assertNotIn(r'\\n',text)
            self.assertIn('$$>a<\\"'+path+'\\";',command(p,80)[1])
        final=files[CAPTURE+'/portrait-checkpoint-2.cdb']
        self.assertNotRegex(final,r'(?:^|;\s*)(?:g|gc|gh|gn)\b')
        text='\n'.join(command(p,n)[1] for n in range(100,117))+'\n'+'\n'.join(files.values())
        writes=re.findall(r'\b(?:ed|ew|eb)\s+([^ ;]+)',text)
        self.assertEqual(set(writes),{'00544cfc','00544d00','005451c0','00544d04','@esp'})
        self.assertNotRegex(text,r'\br eax=|\b(?:ed|ew|eb) 00526f')
        # Check every newly generated printf conversion against its argument list.
        for line in text.splitlines():
            plain=line.replace(r'\"','"')
            for match in re.finditer(r'\.printf "([^"\n]*)", ([^;\n}]+)',plain):
                formats=re.findall(r'%(?:I64)?[dxp]',match[1]);args=[v.strip() for v in match[2].split(',')]
                self.assertEqual(len(formats),len(args),match[0])


if __name__=='__main__':unittest.main()
