#!/usr/bin/env python3
"""Opt-in original-opcode CPU emulation; no Windows/game execution or outputs.

Without --original-backed this checks authoring contracts only. With the exact
user-owned original, genuine memory-line/fill bytes execute in Unicorn against
synthetic owned surfaces. Thread queries in the surrounding source-owned guard
remain modeled. Sprite/provider/Windows/runtime/release acceptance stays false.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]
import test_battle_profile_line_replay as prior

ORIGINAL_SHA = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
PINNED_FILES = {
    'src/patcher/battle_profile_line_replay.py': '3669933ea7e24f727003160cbc198784c00c6d6745ca82039818ec4133125345',
    'tools/test_battle_profile_line_replay.py': '4f91ead9437b4ca9d90a6fef41c4909685ba23d7a45d4f55d93953bb794d77e7',
}
SPANS = (
    ('line', 0x403F70, 0x40403D, '74308b78ce403326e9df50c52c7c522bbc645e6b5001961e3a957e5d9b0ebf5e'),
    ('fill_adapter', 0x473FD8, 0x473FF0, '72d0f071ad4527d35d1d3a72d27ba6c438a17144868c4d381f451485bbcbb3ec'),
    ('fill', 0x487CF0, 0x487D93, '0d817cb2566a6e1c69d28ad408e2c64dbe30f5718e5c9e2a0126d2bc4d8ebc03'),
    ('vtable', 0x50EE24, 0x50EE60, '297030147e736198144db61d9839b9be6372b4d8a679a20db4586c188367fa3e'),
)
NATIVE_CALLS = {0x40402F:0x473FD8, 0x473FE8:0x487CF0, 0x487D07:0x487D27}
NATIVE_RETURNS = {0x40403A:8, 0x473FEF:0, 0x487D20:0, 0x487D92:0}
ACCEPTANCE = dict(original_opcode_cpu_verified=False, windows_runtime_verified=False,
    game_runtime_verified=False, installed=False, native_sprite_provider_verified=False,
    full_battle_verified=False, visual_verified=False, input_verified=False, release_accepted=False)


def require(ok, message):
    if not ok:raise ValueError(message)


def source_contract():
    for relative, expected in PINNED_FILES.items():
        path=ROOT/relative
        require(path.resolve(strict=True)==path, 'noncanonical fixture dependency')
        require(hashlib.sha256(path.read_bytes()).hexdigest()==expected, 'frozen fixture producer differs: '+relative)


def pe_layout(image):
    require(type(image) is bytes and len(image)>=64 and image[:2]==b'MZ','invalid original PE')
    pe=struct.unpack_from('<I',image,60)[0]
    require(pe+24<=len(image) and image[pe:pe+4]==b'PE\0\0','invalid PE signature')
    machine,count=struct.unpack_from('<HH',image,pe+4); optional_size=struct.unpack_from('<H',image,pe+20)[0]
    optional=pe+24
    require(machine==0x14C and optional_size>=144 and optional+optional_size+count*40<=len(image),'invalid x86 section table')
    require(struct.unpack_from('<H',image,optional)[0]==0x10B,'PE32 required')
    base=struct.unpack_from('<I',image,optional+28)[0]
    reloc_rva,reloc_size=struct.unpack_from('<II',image,optional+136)
    sections=[]
    for i in range(count):
        virtual_size,rva,raw_size,raw_offset=struct.unpack_from('<IIII',image,optional+optional_size+i*40+8)
        require(raw_offset+raw_size<=len(image),'section raw extent invalid')
        sections.append((rva,virtual_size,raw_offset,raw_size))
    def locate(va,size):
        hits=[raw+(va-base-rva) for rva,_,raw,n in sections if rva<=va-base and va-base+size<=rva+n]
        require(size>0 and len(hits)==1,'native extent has no unique raw section')
        return hits[0]
    highlow=[];at=locate(base+reloc_rva,reloc_size);end=at+reloc_size
    while at<end:
        require(at+8<=end,'truncated relocation block')
        page,n=struct.unpack_from('<II',image,at)
        require(n>=8 and n%2==0 and at+n<=end,'invalid relocation block')
        for off in range(at+8,at+n,2):
            item=struct.unpack_from('<H',image,off)[0];kind=item>>12
            require(kind in (0,3),'unexpected original relocation type')
            if kind==3:highlow.append(page+(item&4095))
        at+=n
    require(len(set(highlow))==len(highlow),'duplicate original HIGHLOW')
    return base,locate,tuple(highlow)


def authenticate_original(image):
    require(type(image) is bytes and hashlib.sha256(image).hexdigest()==ORIGINAL_SHA,'exact original required')
    base,locate,relocs=pe_layout(image);require(base==0x400000,'preferred image base differs')
    result={}
    for name,lo,hi,digest in SPANS:
        at=locate(lo,hi-lo);raw=image[at:at+hi-lo]
        require(hashlib.sha256(raw).hexdigest()==digest,'complete native span differs: '+name)
        owned=tuple(sorted(r for r in relocs if lo<=base+r<hi))
        expected=tuple(range(0x10EE24,0x10EE60,4)) if name=='vtable' else ()
        require(owned==expected,'native HIGHLOW inventory differs: '+name)
        result[name]=(lo,raw)
    require(struct.unpack_from('<I',result['vtable'][1],20)[0]==0x403F70,'native vtable line slot differs')
    return result


def decode_native(tools, spans):
    """Decode by hooks that advance EIP before instruction execution."""
    u,r=tools;decoded={}
    for name,(lo,raw) in spans.items():
        if name=='vtable':continue
        cpu=u.Uc(u.UC_ARCH_X86,u.UC_MODE_32);start=lo&~4095
        cpu.mem_map(start,((lo+len(raw)-start+4095)//4096)*4096);cpu.mem_write(lo,raw)
        rows=[]
        def skip(machine,pc,size,data):
            require(1<=size<=15 and pc+size<=lo+len(raw),'native instruction boundary exceeds authenticated span')
            rows.append((pc,bytes(machine.mem_read(pc,size))))
            machine.reg_write(r.UC_X86_REG_EIP,pc+size)
        cpu.hook_add(u.UC_HOOK_CODE,skip);cpu.emu_start(lo,lo+len(raw),count=len(raw))
        require(sum(len(b) for _,b in rows)==len(raw),'native decoder did not cover whole span')
        decoded.update(rows)
    calls={};returns={}
    for pc,raw in decoded.items():
        if raw[0]==0xE8:calls[pc]=pc+5+struct.unpack('<i',raw[1:])[0]
        if raw[0] in (0xC2,0xC3):returns[pc]=struct.unpack('<H',raw[1:])[0] if raw[0]==0xC2 else 0
        require(raw[0] not in (0x9A,0xCA,0xCB) and not (raw[0]==0xFF and (raw[1]>>3)&7 in (2,3,4,5)),
            'unexpected native indirect/far operation')
        if raw[0] in (0xE8,0xE9):target=pc+len(raw)+struct.unpack('<i',raw[-4:])[0]
        elif raw[0]==0xEB or 0x70<=raw[0]<=0x7F:target=pc+len(raw)+struct.unpack('<b',raw[-1:])[0]
        elif raw[:1]==b'\x0f' and 0x80<=raw[1]<=0x8F:target=pc+len(raw)+struct.unpack('<i',raw[-4:])[0]
        else:continue
        require(target in decoded,'native control target is not an authenticated instruction start')
    require(calls==NATIVE_CALLS and returns==NATIVE_RETURNS,'native CALL/complete RET inventory differs')
    return decoded


def pixel_oracle(before,width,right,x,y,endx,endy,flags):
    # Independent output-domain calculation. Input coordinates follow native
    # WORD semantics; native dashed ends are exclusive and phase is absolute.
    x,y,endx,endy=(v&65535 for v in (x,y,endx,endy));horizontal=y==endy;dashed=bool(flags&256)
    first,last=(x,endx) if horizontal else (y,endy)
    result=bytearray(before)
    for v in range(first,last+int(not dashed)):
        px,py=(v,y) if horizontal else (x,v)
        if 32<=px<=right and 16<=py<=463 and (not dashed or v%4==2):result[py*width+px]=flags&255
    return bytes(result)


class OriginalMachine(prior.Machine):
    def __init__(self,tools,spans,decoded,*args,**kwargs):
        self.native_active=False;self.native_frames=[];self.native_seen=[];self.native_outputs=None
        self.invocation_active=False
        self.native_returned=None;self.native_pixels=[];self.after_native_mutation=None
        self.observed_native_calls=[];self.observed_native_rets=[]
        self.native_decoded=decoded;self.native_spans=spans
        super().__init__(tools,*args,**kwargs)
        self.expected_source_closure=[]
        for emission in (self.emission,self.routing_emission,self.field_emission,self.lease_emission,
            self.content_emission,self.continuation):
            expected=bytearray(emission.code)
            for row in emission.relocations:
                if row.kind=='abs32':struct.pack_into('<I',expected,row.offset,row.target+self.delta)
            # Frozen V2 remains uninstalled in this fixture, including its
            # planned loss-aware CALL substitutions. Use its exact original
            # emitted code, rather than pretending those hooks were applied.
            self.expected_source_closure.append((emission.base_va+self.delta,bytes(expected)))
        intervals=sorted((va,va+len(raw)) for va,raw in self.expected_source_closure)
        require(all(end<=start for (_,end),(start,_) in zip(intervals,intervals[1:])),
            'source emission ownership overlaps')
        for name,(lo,raw) in spans.items():
            data=bytearray(raw)
            if name=='vtable':
                for at in range(0,len(data),4):struct.pack_into('<I',data,at,struct.unpack_from('<I',data,at)[0]+self.delta)
            self.cpu.mem_write(lo+self.delta,bytes(data))
            self.cpu.ctl_remove_cache(lo+self.delta,lo+self.delta+len(data))

    def on_write(self,cpu,access,address,size,value,data):
        if self.invocation_active and not self.native_active:
            scratch=self.request_s-1712<=address and address+size<=self.request_s+4
            loss=address in (self.owned_lease_frame+44,self.owned_lease_frame+48) and size==4 and value==2
            require(scratch or loss,
                'non-native write escaped bounded owning stack: '+
                str((hex(address),size,hex(cpu.reg_read(self.regs['EIP'])))))
        if self.native_active:
            require(size>0,'zero native write')
            if self.PHYSICAL_PIXELS<=address<self.PHYSICAL_PIXELS+self.width*self.height:
                for pixel in range(address,address+size):
                    y,x=divmod(pixel-self.PHYSICAL_PIXELS,self.width)
                    require(32<=x<=self.native_right and 16<=y<=463,'original native write escaped admitted arena')
                self.native_pixels.append((address,size));return
            require(self.native_stack_low<=address and address+size<=self.native_entry_sp+12,'native write escaped bounded own stack')
        super().on_write(cpu,access,address,size,value,data)

    def on_read(self,cpu,access,address,size,value,data):
        if self.native_active:
            allowed=(self.native_stack_low<=address and address+size<=self.native_entry_sp+12 or
                self.PHYSICAL<=address and address+size<=self.PHYSICAL+8)
            if self.PHYSICAL_PIXELS<=address and address+size<=self.PHYSICAL_PIXELS+self.width*self.height:
                # The authentic fill closure compares the destination byte
                # before filling. This is a genuine native payload read.
                allowed=all(16<=y<=463 and 32<=x<=self.native_right for y,x in
                    (divmod(at-self.PHYSICAL_PIXELS,self.width) for at in range(address,address+size)))
            require(allowed,'original native read escaped surface fields/owned stack: '+
                str((hex(address),size,hex(cpu.reg_read(self.regs['EIP'])))))
        super().on_read(cpu,access,address,size,value,data)

    def on_code(self,cpu,address,size,data):
        if address==prior.line.LINE_TARGET+self.delta:
            require(not self.native_active and not self.native_frames,'nested/unclosed native line entry')
            sp=cpu.reg_read(self.regs['ESP']);values={n:cpu.reg_read(self.regs[n]) for n in ('EAX','EDX','EBX','ECX','EBP','ESI','EDI')}
            args=tuple(self.word(sp+4+4*i) for i in range(2));ret=self.word(sp)
            genuine={self.continuation.base_va+r.offset+4+self.delta for r in self.continuation.relocations
                if r.kind=='rel32' and r.target==prior.line.LINE_TARGET}
            require(ret in genuine and values['EAX']==self.PHYSICAL,'native receiver/return authority differs')
            require(sp==self.request_s-128 and sp%4==0,'native argument copy has no exact owning thunk extent')
            require(cpu.reg_read(self.regs['EFLAGS'])&0x400==0,'native DF must be clear')
            self.native_active=True;self.native_entry_sp=sp;self.native_stack_low=sp-128
            self.native_right=32+64*min(self.word(self.WORLD+804),(self.width-192)//64)-1
            self.native_frames=[(ret,sp,8)];self.line_calls.append((sp,ret,values,args))
            self.clipped_native_args=args
        if self.native_active:
            pc=address-self.delta;raw=self.native_decoded.get(pc)
            require(raw is not None and len(raw)==size,'unexpected original native PC')
            require(bytes(cpu.mem_read(address,size))==raw,'native instruction changed after admission')
            self.native_seen.append(pc)
            if pc in NATIVE_CALLS:
                sp=cpu.reg_read(self.regs['ESP']);self.native_frames.append((address+5,sp-4,0))
                self.observed_native_calls.append(pc)
            if pc in NATIVE_RETURNS:
                ret,entry,pop=self.native_frames.pop();sp=cpu.reg_read(self.regs['ESP'])
                require(sp==entry and self.word(sp)==ret and pop==NATIVE_RETURNS[pc],'native cleanup/RET ownership differs')
                self.observed_native_rets.append(pc)
                if not self.native_frames:
                    require(pc==0x40403A,'native root returned through wrong RET')
                    self.native_outputs={n:cpu.reg_read(r) for n,r in self.regs.items()}
                    self.native_outputs['EFLAGS']=cpu.reg_read(self.regs['EFLAGS'])
                    self.native_returned=ret;self.line_closed+=1
                    self.native_active=False
            return # Original bytes execute; no native target or pixel model.
        if self.native_returned==address:
            require(cpu.reg_read(self.regs['ESP'])==self.native_entry_sp+12,'original RET8 did not consume exact args')
            for n,v in self.native_outputs.items():
                if n not in ('ESP','EIP'):require(cpu.reg_read(self.regs[n])==v,'native RET changed output '+n)
            self.native_returned=None
            if self.after_native_mutation:self.after_native_mutation(self)
        if self.invocation_active:
            sources=[(base,raw) for base,raw in self.expected_source_closure if base<=address and address+size<=base+len(raw)]
            if sources:
                require(len(sources)==1,'ambiguous source instruction ownership')
                base,raw=sources[0];at=address-base
                require(bytes(cpu.mem_read(address,size))==raw[at:at+size],
                    'source instruction differs during original-backed invocation: '+hex(address))
            else:
                require(address==self.THREAD or address in self.stops or
                    self.request_site<=address and address+size<=self.request_site_end,
                    'unexpected surrounding PC/callback in original-backed invocation: '+hex(address))
        prior.previous.Machine.on_code(self,cpu,address,size,data)

    def invoke_original(self,i=11,regs=None,**kwargs):
        if regs is None:regs=self.setup_request(i,**kwargs)
        pc=prior.primitive.REQUEST_SITES[i][0]
        raw,target,_,_=self.planned[pc];site=pc+self.delta
        self.request_site=site;self.request_site_end=site+len(raw)
        self.cpu.mem_write(site,b'\xe8'+struct.pack('<i',target+self.delta-site-5)+b'\x90'*(len(raw)-5))
        self.cpu.ctl_remove_cache(site,site+len(raw))
        self.stops={0x430831+self.delta,self.word(self.tile_sp)}|self.unsafe_vas
        require(self.lease_frame==self.field_frame+1320 and self.lease_frame%4==0 and
            self.STACK<=self.lease_frame and self.lease_frame+192<=self.STACK+0x10000,
            'separate source-owned lease descriptor extent differs')
        self.owned_lease_frame=self.lease_frame
        self.native_stop=None;self.request_records=[];self.line_calls=[];self.line_closed=0
        self.native_active=False;self.native_seen=[];self.native_outputs=None;self.native_returned=None;self.native_pixels=[]
        self.observed_native_calls=[];self.observed_native_rets=[]
        self.reads=[];self.writes=[]
        for n,v in regs.items():self.cpu.reg_write(self.regs[n],v&0xFFFFFFFF)
        self.cpu.reg_write(self.regs['EFLAGS'],0xED7)
        self.invocation_active=True
        try:self.cpu.emu_start(site,self.STOP+1,count=1000000)
        finally:self.invocation_active=False
        require(self.native_stop is not None,'bounded original call did not reach fixed continuation/UNSAFE')
        actual={n:self.cpu.reg_read(r) for n,r in self.regs.items()}
        require(not self.native_frames,'unclosed original call frames')
        return actual,regs


class AuthoringTests(unittest.TestCase):
    def test_exact_frozen_dependencies_and_complete_native_contract(self):
        source_contract()
        self.assertEqual([(n,b-a) for n,a,b,_ in SPANS],[('line',205),('fill_adapter',24),('fill',163),('vtable',60)])
        self.assertEqual(NATIVE_RETURNS[0x40403A],8)
        self.assertTrue(all(not v for v in ACCEPTANCE.values()))
    def test_unknown_original_rejects_before_machine_execution(self):
        for data in (b'fixture',bytearray(b'fixture'),memoryview(b'fixture')):
            with self.assertRaisesRegex(ValueError,'exact original required'):authenticate_original(data)
    def test_authored_pixel_domain_inclusive_exclusive_absolute_phase(self):
        before=b'\xB9'*(800*600)
        plain=pixel_oracle(before,800,95,32,20,35,20,7)
        self.assertEqual(plain[20*800+32:20*800+36],b'\x07'*4)
        dash=pixel_oracle(before,800,95,32,20,35,20,0x107)
        self.assertEqual(dash[20*800+32:20*800+36],b'\xB9\xB9\x07\xB9')


class OriginalTests(unittest.TestCase):
    tools=None;spans=None;decoded=None
    def machine(self,profile='classic',resolution='1024x768',delta=0,columns=20):
        m=OriginalMachine(self.tools,self.spans,self.decoded,profile,resolution,delta).prepare(columns=columns);m.begin();return m
    def test_representative_two_bases_genuine_pixels_outputs_flags_ret8(self):
        for delta in (0,0x100000):
            m=self.machine(delta=delta)
            for i,x,y,endx,args in ((11,0,20,65535,(20,7)),(11,0,20,65535,(20,0x107)),
                (12,40,0,123,(65535,7)),(12,40,0,123,(65535,0x107))):
                regs=m.setup_request(i,x=x,y=y,endx=endx,args=args)
                saved={n:m.word(m.tile_sp-off) for n,off in dict(EBX=4,ECX=8,ESI=12,EDI=16,EBP=20).items()}
                before=m.pixels();state=m.record();actual,regs=m.invoke_original(i,regs)
                self.assertNotIn(m.native_stop,m.unsafe_vas);self.assertEqual(m.line_closed,1)
                right=32+64*min(20,(m.width-192)//64)-1
                self.assertEqual(m.pixels(),pixel_oracle(before,m.width,right,x,y,endx,args[0],args[1]))
                self.assertEqual(m.record(),state)
                self.assertEqual(tuple(m.word(m.request_s+4+4*j) for j in range(2)),args)
                for n in ('EAX','ECX','EDX','EBX','ESI','EDI','EBP'):
                    expected=m.native_outputs[n]
                    if i==12 and n in saved:expected=saved[n]
                    self.assertEqual(actual[n],expected,(delta,i,n))
                self.assertEqual(actual['EFLAGS']&m.MASK,m.native_outputs['EFLAGS']&m.MASK)
                self.assertEqual(actual['ESP'],m.request_s+12 if i==11 else m.tile_sp+4)
                for at in (m.PHYSICAL_PIXELS-16,m.PHYSICAL_PIXELS+m.width*m.height,
                    m.private_pixels-16,m.private_pixels+307200):self.assertEqual(bytes(m.cpu.mem_read(at,16)),b'\xD7'*16)

    def test_all36_two_bases_actual_opcodes_clipped_args_outputs_and_complete_buffers(self):
        for profile in prior.oracle.PROFILES:
            for resolution in prior.oracle.RESOLUTIONS:
                for delta in (0,0x100000):
                    m=self.machine(profile,resolution,delta)
                    right=32+64*min(20,(m.width-192)//64)-1
                    for i,x,y,endx,args in ((11,0,20,65535,(20,7)),(11,31,21,65535,(21,0x107)),
                        (12,40,0,65535,(65535,7)),(12,41,0,0,(65535,0x107))):
                        regs=m.setup_request(i,x=x,y=y,endx=endx,args=args)
                        saved={n:m.word(m.tile_sp-off) for n,off in dict(EBX=4,ECX=8,ESI=12,EDI=16,EBP=20).items()}
                        before=m.pixels();record=m.record();actual,regs=m.invoke_original(i,regs)
                        self.assertNotIn(m.native_stop,m.unsafe_vas,(profile,resolution,delta,i))
                        self.assertEqual(m.line_closed,1);self.assertEqual(m.observed_native_rets[-1],0x40403A)
                        status,coords=prior.previous.expected_line(x,y,endx,args,right)
                        self.assertEqual(status,1);self.assertEqual(m.clipped_native_args,(coords[3],args[1]))
                        self.assertEqual(tuple(m.line_calls[0][2][n]&65535 for n in ('EDX','EBX','ECX')),coords[:3])
                        self.assertEqual(m.pixels(),pixel_oracle(before,m.width,right,x,y,endx,args[0],args[1]))
                        self.assertEqual(m.record(),record)
                        for n in ('EAX','ECX','EDX','EBX','ESI','EDI','EBP'):
                            expected=saved[n] if i==12 and n in saved else m.native_outputs[n]
                            self.assertEqual(actual[n],expected,(profile,resolution,delta,i,n))
                        self.assertEqual(actual['EFLAGS']&m.MASK,m.native_outputs['EFLAGS']&m.MASK)
                        self.assertEqual(actual['ESP'],m.request_s+12 if i==11 else m.tile_sp+4)
                        self.assertEqual(tuple(m.word(m.request_s+4+4*j) for j in range(2)),args)
                        if i==11 and not args[1]&256:self.assertTrue(set(NATIVE_CALLS)<=set(m.observed_native_calls))
                        else:self.assertEqual(m.observed_native_calls,[])

    def test_small_arenas_gutters_plain_inclusive_dash_exclusive_and_phase(self):
        cases=((11,31,20,32,(20,7)),(11,32,20,32,(20,7)),(11,31,20,32,(20,0x107)),
            (11,32,20,32,(20,0x107)),(11,33,20,37,(20,0x107)),(11,37,20,33,(20,7)),
            (12,40,462,0,(463,7)),(12,40,462,0,(463,0x107)),(12,40,463,0,(464,0x107)),
            (12,40,464,0,(500,7)),(11,32,464,64,(464,7)),
            (11,0x10020,0x10010,0x10040,(0x10010,0xABCD0107)))
        for delta in (0,0x100000):
            for resolution in ('800x600','1366x768','3440x1440','3840x2160'):
                for columns in (1,3,8,20):
                    m=self.machine('modalwidgets',resolution,delta,columns)
                    right=32+64*min(columns,(m.width-192)//64)-1
                    for i,x,y,endx,args in cases:
                        before=m.pixels();actual,regs=m.invoke_original(i,x=x,y=y,endx=endx,args=args)
                        status,_=prior.previous.expected_line(x,y,endx,args,right)
                        self.assertNotIn(m.native_stop,m.unsafe_vas)
                        self.assertEqual(m.line_closed,int(status==1),(resolution,columns,delta,i,status))
                        self.assertEqual(m.pixels(),before if status!=1 else pixel_oracle(before,m.width,right,x,y,endx,args[0],args[1]))
                        if status==2:self.assertEqual(m.word(m.lease_frame+44),2)
                        # A malformed request retires this owning draw. Next
                        # independent case begins a genuinely new descriptor.
                        if status==2:m.begin()

    def test_native_pc_code_stack_and_pixel_ownership_mutations_fail(self):
        for delta in (0,0x100000):
            for fault in ('instruction','return','pixel'):
                m=self.machine(delta=delta)
                if fault=='instruction':
                    old=m.native_decoded[0x403F70]
                    m.cpu.mem_write(0x403F70+delta,bytes([old[0]^1])+old[1:])
                    m.cpu.ctl_remove_cache(0x403F70+delta,0x403F70+delta+len(old))
                else:
                    # Registered hook dispatches the bound method established
                    # at construction, so add a second controlled mutation hook.
                    def mutate(cpu,pc,size,data,kind=fault,machine=m):
                        if pc==0x403F70+machine.delta:
                            if kind=='return':machine.put(machine.native_entry_sp,0xDEADC0DE)
                            else:machine.put(machine.PHYSICAL+4,machine.private_pixels)
                    m.cpu.hook_add(m.u.UC_HOOK_CODE,mutate)
                with self.assertRaises((ValueError,m.u.UcError)):
                    m.invoke_original(11,x=32,y=20,endx=64,args=(20,7))

    def test_pre_and_post_normal_loss_and_poisoned_cached_objects(self):
        for profile in prior.oracle.PROFILES:
            for delta in (0,0x100000):
                for when in ('pre','post'):
                    m=self.machine(profile,'1024x768',delta)
                    def loss(machine):
                        machine.put(machine.lease_frame+44,2);machine.put(machine.lease_frame+48,2)
                        machine.cpu.mem_protect(machine.PHYSICAL,4096,machine.u.UC_PROT_NONE)
                        machine.cpu.mem_protect(machine.WORLD,4096,machine.u.UC_PROT_NONE)
                    if when=='post':m.after_native_mutation=loss
                    else:
                        # Setup creates the exact own descriptor first; this
                        # mutation happens on its admitted Thread callback.
                        m.mutation=lambda machine,name:loss(machine) if name=='thread' else None
                    actual,regs=m.invoke_original(11,x=32,y=20,endx=64,args=(20,7))
                    self.assertIn(m.native_stop,m.unsafe_vas)
                    self.assertEqual(m.line_closed,int(when=='post'))
                    self.assertEqual(bool(m.native_pixels),when=='post')
                    self.assertFalse(any(m.PHYSICAL<=at<m.PHYSICAL+188 or m.WORLD<=at<m.WORLD+0xF7C
                        for at,n in m.reads[0:] if when=='pre'))

    def test_primary_private_receivers_and_unknown_control_never_enter_original(self):
        for delta in (0,0x100000):
            for fault in ('primary','private','return_pc','saved_ebp'):
                m=self.machine(delta=delta);regs=m.setup_request(11,x=32,y=20,endx=64,args=(20,7))
                if fault=='primary':regs['EAX']=0x51D4C0+delta
                elif fault=='private':regs['EAX']=m.PRIVATE
                elif fault=='return_pc':m.put(m.tile_sp,0xDEADC0DE)
                else:m.put(m.tile_sp-20,m.field_frame+4)
                before=m.pixels();actual,_=m.invoke_original(11,regs)
                self.assertEqual(m.line_closed,0);self.assertEqual(m.native_pixels,[]);self.assertEqual(m.pixels(),before)
                if fault in ('return_pc','saved_ebp'):self.assertIn(m.native_stop,m.unsafe_vas)
                else:self.assertEqual(m.word(m.lease_frame+44),2)

    def test_surrounding_stack_pixel_write_and_unexpected_callback_fail(self):
        for delta in (0,0x100000):
            for fault in ('pixel_write','unexpected_callback','source_instruction'):
                m=self.machine(delta=delta)
                if fault=='unexpected_callback':
                    def redirect_callback(cpu,pc,size,data,machine=m):
                        if pc==machine.THREAD:cpu.reg_write(machine.regs['EIP'],0x473FF0+machine.delta)
                    m.cpu.hook_add(m.u.UC_HOOK_CODE,redirect_callback)
                else:
                    target=m.planned[0x430AD5][1]+delta
                    if fault=='source_instruction':
                        old=bytes(m.cpu.mem_read(target,1));m.cpu.mem_write(target,bytes([old[0]^1]))
                        m.cpu.ctl_remove_cache(target,target+1)
                    else:
                        def redirect_stack(cpu,pc,size,data,machine=m,entry=target):
                            if pc==entry:cpu.reg_write(machine.regs['ESP'],machine.PHYSICAL_PIXELS+4)
                        m.cpu.hook_add(m.u.UC_HOOK_CODE,redirect_stack)
                with self.assertRaisesRegex(ValueError,'non-native write escaped|unexpected surrounding PC|source instruction differs'):
                    m.invoke_original(11,x=32,y=20,endx=64,args=(20,7))
                self.assertEqual(m.line_closed,0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-backed',metavar='ORIGINAL_PATH',help='explicitly opt into authenticated original-opcode CPU emulation')
    parser.add_argument('--test',action='append',choices=tuple(n for n in dir(OriginalTests) if n.startswith('test_')),
        help='select an original-backed fixture; authoring contracts always run')
    args,rest=parser.parse_known_args();source_contract()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(AuthoringTests)
    original_path=None
    if args.original_backed:
        original_path=Path(args.original_backed);image=original_path.read_bytes()
        OriginalTests.spans=authenticate_original(image)
        OriginalTests.tools=prior.oracle.lifetime_fixture.machine_tools()
        OriginalTests.decoded=decode_native(OriginalTests.tools,OriginalTests.spans)
        if args.test:
            for name in args.test:suite.addTest(OriginalTests(name))
        else:suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(OriginalTests))
    require(not args.test or bool(args.original_backed),'--test requires --original-backed')
    require(not rest,'unknown arguments; use explicit --original-backed only')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if original_path:
        require(hashlib.sha256(original_path.read_bytes()).hexdigest()==ORIGINAL_SHA,'original changed during CPU fixture')
    if result.wasSuccessful():
        if original_path:print('Original-opcode CPU lane PASS; genuine line/fill bytes only; original unchanged. Windows/game/runtime/release acceptance false.')
        else:print('Authoring contracts PASS; original_opcode_cpu_verified=False; --original-backed is required for original CPU proof.')
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
