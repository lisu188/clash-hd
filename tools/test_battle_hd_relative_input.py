#!/usr/bin/env python3
"""Native x86 fixtures for battle-only relative DirectInput integration.

Reads a SHA-verified local original, never launches it. Emulates the original
460A50 update, 460AF0 recenter and 460B20 sprite-aware bounds setter. Device
polling and ClientToScreen are controlled fixtures. No calibrated automation
offset, game binary, runtime capture or Windows input is produced.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "patcher"))
import battle_hd_core as core
from test_battle_hd_cursor_bounds import test_stage_contract, verify_battle_context_routes


def machine_tests(source_exe):
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn import x86_const as r

    source = source_exe.read_bytes()
    assert hashlib.sha256(source).hexdigest() == core.EXPECTED_SOURCE_SHA256
    verify_battle_context_routes(source)
    selected, inherited = test_stage_contract()
    block = next(b for b in core.ASSEMBLY_BLOCKS if b[0] == "battle_relative_mouse")
    assembler = Ks(KS_ARCH_X86, KS_MODE_32)
    encoded = bytes.fromhex(block[3])
    assert bytes(assembler.asm(block[2], block[1])[0]) == encoded
    assert encoded[33:71] == source[0x05fe61:0x05fe87]
    hook = next(p for p in selected if p.offset == 0x05fe61)
    assert hook.old == source[0x05fe61:0x05fe87]
    assert hook.new[0] == 0xe9 and hook.new[5:] == b"\x90" * 33
    assert 0x460a66 + struct.unpack("<i",hook.new[1:5])[0] == block[1]

    obj, meta, stack, stop, api = 0x544cd8, 0x5196f0, 0x710000, 0x580000, 0x580100
    regs = (r.UC_X86_REG_EAX, r.UC_X86_REG_EBX, r.UC_X86_REG_ECX,
            r.UC_X86_REG_EDX, r.UC_X86_REG_ESI, r.UC_X86_REG_EDI,
            r.UC_X86_REG_EBP)

    def signed(value):
        return (value + 0x80000000) % 0x100000000 - 0x80000000

    class Machine:
        def __init__(self, mode, owner, shift, speed, sprite, origin=(0,0), battle=0):
            self.u = Uc(UC_ARCH_X86, UC_MODE_32)
            self.u.mem_map(0x400000,0x190000)
            self.u.mem_map(stack-0x10000,0x10000)
            self.u.mem_write(0x460a50,source[0x05fe50:0x05ffaf])
            self.u.mem_write(core.CORE_CODE_VA,core.CORE_CODE)
            rows = selected if mode == "battle" else inherited if mode == "inherited" else ()
            for patch in rows:
                if patch.offset in (0x05fe61,0x0e8c10):
                    assert source[patch.offset:patch.offset+len(patch.old)] == patch.old
                    self.u.mem_write(patch.offset+0x400c00,patch.new)
            self.put(0x5199d8,owner)
            self.put(0x532048,battle)
            self.put(obj+0x454,shift)
            self.put(obj+0x20,speed)
            self.put(obj+0x3c,meta)
            self.put(0x4ea3e0,api)
            self.put(0x5452dc,0x123456)
            for offset,value in zip((12,16,20,24),sprite):
                self.put(meta+offset,value)
            self.sample = (0,0,0)
            self.origin = origin
            self.events = []
            self.finished = False
            self.u.hook_add(UC_HOOK_CODE,self.intercept)
            self.bounds(1280,720)

        def put(self,address,value):
            self.u.mem_write(address,struct.pack("<I",value & 0xffffffff))

        def get(self,address):
            return struct.unpack("<I",self.u.mem_read(address,4))[0]

        def native_scope_fragment(self,start,end,registers):
            # Execute only the byte-verified native pointer publication/clear
            # or owner store with explicit fixture operands. No allocation,
            # game lifecycle, DirectInput or OS activity is simulated as real.
            self.u.mem_write(start,source[start-0x400c00:end-0x400c00])
            sp = stack-0x100
            self.u.reg_write(r.UC_X86_REG_ESP,sp)
            for register,value in registers:
                self.u.reg_write(register,value)
            self.u.emu_start(start,end,count=64)
            assert self.u.reg_read(r.UC_X86_REG_EIP) == end
            assert self.u.reg_read(r.UC_X86_REG_ESP) == sp

        def ret(self,cleanup=0):
            sp = self.u.reg_read(r.UC_X86_REG_ESP)
            self.u.reg_write(r.UC_X86_REG_EIP,self.get(sp))
            self.u.reg_write(r.UC_X86_REG_ESP,sp+4+cleanup)

        def intercept(self,u,address,size,user):
            if address == stop:
                self.finished = True
                u.emu_stop()
            elif address == 0x47bfd0:
                # Native input-update polling call. Supply signed device
                # deltas and button bytes without replacing the update logic.
                dx,dy,buttons = self.sample
                self.put(0x5451a8,dx)
                self.put(0x5451ac,dy)
                self.u.mem_write(0x5451c0,bytes([0x80 if buttons & 1 else 0]))
                self.u.mem_write(0x5451c8,bytes([0x80 if buttons & 2 else 0]))
                self.events.append("poll")
                self.ret()
            elif address == api:
                sp = u.reg_read(r.UC_X86_REG_ESP)
                assert self.get(sp+4) == 0x123456
                point = self.get(sp+8)
                self.put(point,self.origin[0])
                self.put(point+4,self.origin[1])
                u.reg_write(r.UC_X86_REG_EAX,1)
                # A stdcall API may clobber these caller-saved registers.
                u.reg_write(r.UC_X86_REG_ECX,0xdead)
                u.reg_write(r.UC_X86_REG_EDX,0xbad)
                self.events.append("ClientToScreen")
                self.ret(8)
            elif address == 0x4605d0:
                # The real recenter calls DD_Pump. Its device-dispatch fixture
                # immediately invokes the original 460A50 callback and lets
                # its RET return to recenter's stock continuation at 460B19.
                assert u.reg_read(r.UC_X86_REG_EAX) == obj
                self.events.append("recenter_poll")
                u.reg_write(r.UC_X86_REG_EIP,0x460a50)

        def invoke(self,entry,args=()):
            self.events.clear()
            self.finished = False
            sp = stack-4*(len(args)+1)
            for index,value in enumerate((stop,*args)):
                self.put(sp+4*index,value)
            self.u.reg_write(r.UC_X86_REG_ESP,sp)
            self.u.reg_write(r.UC_X86_REG_EFLAGS,0x202)
            self.u.emu_start(entry,0,count=1000)
            assert self.finished, hex(entry)
            assert self.u.reg_read(r.UC_X86_REG_ESP) == stack

        def bounds(self,width,height):
            self.u.reg_write(r.UC_X86_REG_EAX,obj)
            self.u.reg_write(r.UC_X86_REG_EDX,0)
            self.u.reg_write(r.UC_X86_REG_ECX,width)
            self.u.reg_write(r.UC_X86_REG_EBX,0)
            self.invoke(0x460b20,(height,))

        def result(self):
            return (tuple(self.get(obj+o) for o in (0x24,0x28,0x2c)),
                    tuple(self.u.reg_read(reg) for reg in regs),
                    self.u.reg_read(r.UC_X86_REG_EFLAGS))

        def poll(self,dx,dy,buttons=0,recenter=None):
            self.sample = (dx,dy,buttons)
            for index,reg in enumerate(regs):
                self.u.reg_write(reg,0x12340000+index)
            self.u.reg_write(r.UC_X86_REG_EAX,obj)
            if recenter is not None:
                self.u.reg_write(r.UC_X86_REG_EDX,recenter[0])
                self.u.reg_write(r.UC_X86_REG_EBX,recenter[1])
            before = tuple(self.u.reg_read(reg) for reg in regs)
            self.invoke(0x460af0 if recenter is not None else 0x460a50)
            if recenter is None:
                assert self.result()[1][1:] == before[1:]
            assert self.events.count("poll") == 1
            return self.result()

    total = 0
    samples = ((0,0,0),(-29,1,0),(-257,-5,1),(29,-1,2),(257,5,3),
               (1,0,0),(0,-1,0),(1000000,-1000000,3),(-1000000,1000000,0),
               (0x7fffffff,-0x80000000,2),(0,0,1))
    for owner,battle,shift in ((o,b,s) for o,b in ((0x42e8b0,0),(0x4617a0,0x570000)) for s in (0,6)):
        for speed in (0,1,3,64,128):
            for sprite in ((30,29,0,0),(48,48,19,20)):
                for origin in ((0,0),(880,407)):
                    m = Machine("battle",owner,shift,speed,sprite,origin,battle)
                    native = Machine("native",owner,shift,speed,sprite,origin,battle)
                    # Recenter's immediate poll must also use relative data.
                    assert m.poll(-29,1,2,(576,360)) == native.poll(-29,1,2,(576,360))
                    assert "ClientToScreen" not in m.events
                    total += 1
                    for dx,dy,buttons in samples:
                        x,y,_ = m.result()[0]
                        left,top,right,bottom = (m.get(obj+o) for o in (0x10,0x14,0x18,0x1c))
                        expected = (min(max(signed(x+dx*speed),left),right),
                                    min(max(signed(y+dy*speed),top),bottom),buttons)
                        actual = m.poll(dx,dy,buttons)
                        assert actual == native.poll(dx,dy,buttons)
                        assert actual[0] == expected, (shift,speed,dx,dy,actual[0],expected)
                        assert "ClientToScreen" not in m.events
                        total += 1
                    # Restore center with zero deltas, then prove that genuine
                    # zero motion stays at center (no absolute-origin rewrite).
                    assert m.poll(0,0,0,(576,360)) == native.poll(0,0,0,(576,360))
                    centered = m.result()[0]
                    assert m.poll(0,0)[0] == centered
                    total += 2

    # Exact scope: nonbattle owners remain byte-for-byte behaviorally equal to
    # the inherited dynamic-origin updater, including its API and stack ABI.
    for owner,battle in ((0x4617a0,0),(0,0),(0x42e8b1,0),
                         (0,0x570000),(0x42e8b1,0x570000)):
        for origin in ((0,0),(880,407)):
            m = Machine("battle",owner,6,64,(30,29,0,0),origin,battle)
            legacy = Machine("inherited",owner,6,64,(30,29,0,0),origin,battle)
            for sample in samples:
                assert m.poll(*sample,recenter=(576,360)) == legacy.poll(*sample,recenter=(576,360))
                assert m.events.count("ClientToScreen") == 1
                total += 1

    # The observed problematic sequence now has the native interpretation.
    m = Machine("battle",0x42e8b0,6,64,(30,29,0,0))
    assert m.poll(0,0,0,(576,360))[0] == (576 << 6,360 << 6,0)
    assert m.poll(-29,1)[0] == (547 << 6,361 << 6,0)
    assert m.poll(-257,-5)[0] == (290 << 6,356 << 6,0)
    total += 3

    # Native-byte fragments establish the active interval, temporary overlay
    # owners and return to the default hook. The fixture deliberately does not
    # call allocation/free: publish a controlled pointer via the real copy,
    # then execute the real post-free clear after the two overlay intervals.
    m = Machine("battle",0x4617a0,6,64,(30,29,0,0))

    def check_transition(mode,label):
        expected = Machine(mode,m.get(0x5199d8),6,64,(30,29,0,0),battle=m.get(0x532048))
        assert m.poll(-29,1,2,(576,360)) == expected.poll(-29,1,2,(576,360)), label
        assert m.events.count("ClientToScreen") == (mode == "inherited"), label
        assert m.poll(-257,-5,1) == expected.poll(-257,-5,1), label
        return 2

    total += check_transition("inherited","before battle")
    m.native_scope_fragment(0x42ec7c,0x42ec90,(
        (r.UC_X86_REG_EAX,0x570000),(r.UC_X86_REG_ECX,4),
        (r.UC_X86_REG_EDI,0x532048),(r.UC_X86_REG_ESI,stack-0x100+0x70)))
    assert m.get(0x532048) == 0x570000
    m.native_scope_fragment(0x42ea65,0x42ea6b,((r.UC_X86_REG_EDX,0x42e8b0),))
    total += check_transition("native","battle")
    m.native_scope_fragment(0x42d77c,0x42d782,((r.UC_X86_REG_EDX,0x4617a0),))
    total += check_transition("native","banner before owner restore")
    m.native_scope_fragment(0x42da62,0x42da67,((r.UC_X86_REG_EAX,0x42e8b0),))
    total += check_transition("native","banner returned")
    m.native_scope_fragment(0x4453b5,0x4453bb,((r.UC_X86_REG_ECX,0x4617a0),))
    total += check_transition("native","results wait")
    m.native_scope_fragment(0x44585f,0x445864,((r.UC_X86_REG_EAX,0x42e8b0),))
    total += check_transition("native","results returned")
    m.native_scope_fragment(0x42f536,0x42f53d,())
    assert m.get(0x532048) == 0
    total += check_transition("native","cleared pointer with original battle owner")
    m.native_scope_fragment(0x42f5a2,0x42f5a7,((r.UC_X86_REG_EAX,0x4617a0),))
    total += check_transition("inherited","default owner after battle")
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-exe",type=Path)
    parser.add_argument("--toolchain-path",type=Path)
    parser.add_argument("--require-machine-tools",action="store_true")
    args = parser.parse_args()
    test_stage_contract()
    if args.toolchain_path:
        sys.path.insert(0,str(args.toolchain_path))
    if args.source_exe is None:
        if args.require_machine_tools:
            parser.error("--require-machine-tools also requires --source-exe")
        print("battle relative-input stage isolation passed; native x86 lane skipped (no --source-exe)")
        return
    count = machine_tests(args.source_exe)
    print(f"battle relative-input isolation and {count} native x86 update/recenter scenarios passed")


if __name__ == "__main__":
    main()
