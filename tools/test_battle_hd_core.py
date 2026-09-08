#!/usr/bin/env python3
"""Repo-only byte, assembly and x86-emulator checks for battle HD core.

Optional development tools: keystone-engine and unicorn. Supply their external
installation with --toolchain-path; --require-machine-tools fails if absent.
No executable is launched. --source-exe only reads and checks its known SHA.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "patcher"))
import battle_hd_core as core
from battle_hd_layout import BATTLE_LAYOUT as layout


def test_patch_contract(source_exe: Path | None = None) -> None:
    intervals = []
    assert core.CORE_CODE_VA == 0x562000
    assert core.CORE_CODE_OFFSET == 0x12CE00
    assert len(core.CORE_CODE) <= 0x4000
    assert layout.battlefield == (32, 136, 1120, 584)
    source = None
    if source_exe is not None:
        source = source_exe.read_bytes()
        assert hashlib.sha256(source).hexdigest() == core.EXPECTED_SOURCE_SHA256
    for group, offset, old_hex, new_hex, note in core.build_patches():
        old, new = bytes.fromhex(old_hex), bytes.fromhex(new_hex)
        assert group in {"battle-hd-viewport", "battle-hd-camera", "battle-hd-input"}
        assert old and len(old) == len(new)
        assert old != new
        assert f"VA {offset + 0x400C00:08X}" in note and "RVA " in note
        if source is not None:
            assert source[offset:offset + len(old)] == old, hex(offset)
        intervals.append((offset, offset + len(old)))
    intervals.sort()
    assert all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:]))
    intervals = []
    for name, address, assembly, encoding in core.ASSEMBLY_BLOCKS:
        data = bytes.fromhex(encoding)
        offset = address - core.CORE_CODE_VA
        assert data and assembly.strip()
        assert core.CORE_CODE[offset:offset + len(data)] == data, name
        intervals.append((address, address + len(data)))
    assert all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:]))


def machine_tests(source_exe: Path | None = None) -> int:
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ
    from unicorn import x86_const as r

    assembler = Ks(KS_ARCH_X86, KS_MODE_32)
    for name, address, assembly, encoding in core.ASSEMBLY_BLOCKS:
        assert bytes(assembler.asm(assembly, address)[0]).hex() == encoding, name

    regs = (r.UC_X86_REG_EAX, r.UC_X86_REG_EBX, r.UC_X86_REG_ECX,
            r.UC_X86_REG_EDX, r.UC_X86_REG_ESI, r.UC_X86_REG_EDI,
            r.UC_X86_REG_EBP)
    state, stack, stop, cursor, surface = 0x600000, 0x710000, 0x580000, 0x601000, 0x602000
    total = 0

    class Machine:
        def __init__(self, columns=20, camera=0, rows=7):
            self.u = Uc(UC_ARCH_X86, UC_MODE_32)
            self.u.mem_map(0x400000, 0x180000)
            self.u.mem_map(stop, 0x1000)
            self.u.mem_map(state, 0x10000)
            self.u.mem_map(0x620000, 0x30000)
            self.u.mem_map(stack - 0x10000, 0x10000)
            self.u.mem_write(core.CORE_CODE_VA, core.CORE_CODE)
            self.put(0x532048, state)
            self.put(state + 804, columns)
            self.put(state + 800, rows)
            self.put(state + 808, camera)
            self.put(state + 812, 0)
            self.put(0x544d14, cursor)
            self.put(cursor + 12, 16)
            self.put(cursor + 16, 16)
            self.put(0x5202e0, surface)
            self.put(0x5202e4, 0x620000)
            for i, reg in enumerate(regs):
                self.u.reg_write(reg, 0x12340000 + i * 0x111)

        def put(self, address, value):
            self.u.mem_write(address, struct.pack("<I", value & 0xffffffff))

        def get(self, address):
            return struct.unpack("<i", self.u.mem_read(address, 4))[0]

        def mouse(self, x, y, shift=6):
            self.put(0x544cfc, x << shift)
            self.put(0x544d00, y << shift)
            self.u.mem_write(0x54512c, bytes([shift]))

        def snapshot(self):
            return tuple(self.u.reg_read(reg) for reg in regs)

        def run(self, entry, intercept=None):
            self.put(stack - 4, stop)
            self.u.reg_write(r.UC_X86_REG_ESP, stack - 4)
            self.u.reg_write(r.UC_X86_REG_EFLAGS, 0x202)
            reached = []

            def on_code(u, address, size, user):
                if address == stop:
                    reached.append(address)
                    u.emu_stop()
                elif intercept is not None:
                    intercept(self, address, reached)

            token = self.u.hook_add(UC_HOOK_CODE, on_code)
            try:
                self.u.emu_start(entry, 0, count=200000)
            finally:
                self.u.hook_del(token)
            assert reached, f"No bounded completion from {entry:08X}"
            return reached[-1]

        def ret(self, cleanup=0):
            sp = self.u.reg_read(r.UC_X86_REG_ESP)
            target = self.get(sp) & 0xffffffff
            self.u.reg_write(r.UC_X86_REG_ESP, sp + 4 + cleanup)
            self.u.reg_write(r.UC_X86_REG_EIP, target)

    for width in (1, 7, 16, 17, 18, 20, 0, 21):
        for camera in (-100, -1, 0, 1, 3, 50):
            m = Machine(width, camera)
            m.put(state + 812, -4)
            before = m.snapshot()
            m.run(0x562000)
            expected = layout.clamp_camera(camera, width) if 1 <= width <= 20 else 0
            assert (m.get(state + 808), m.get(state + 812)) == (expected, 0)
            assert m.snapshot() == before
            assert m.u.reg_read(r.UC_X86_REG_ESP) == stack
            total += 1

    points = [(-1,136),(31,136),(32,135),(32,136),(95,199),(96,200),
              (543,136),(544,136),(1119,583),(1120,583),(1119,584),
              (320,0),(320,719),(1279,500),(1138,490)]
    for width in (7, 17, 20):
        for camera in (0, 3, -1, 100):
            for shift in (0, 2, 6):
                for x, y in points:
                    m = Machine(width, camera)
                    m.mouse(x, y, shift)
                    before = m.snapshot()
                    raw_before = (m.get(0x544cfc), m.get(0x544d00))
                    m.run(0x562100)
                    expected = layout.cell_at(x, y, width, camera)
                    invalid = m.u.reg_read(r.UC_X86_REG_EFLAGS) & 1
                    got = (m.u.reg_read(r.UC_X86_REG_EAX), m.u.reg_read(r.UC_X86_REG_EDX))
                    if expected is None:
                        assert invalid and got == (0xffffffff, 0xffffffff), (width,camera,x,y,got)
                    else:
                        assert not invalid
                        assert got == (expected[0] - layout.clamp_camera(camera,width), expected[1])
                    after = m.snapshot()
                    assert all(after[i] == before[i] for i in (1,2,4,5,6))
                    assert (m.get(0x544cfc), m.get(0x544d00)) == raw_before
                    total += 1

    for width in (7, 17, 20):
        camera = layout.clamp_camera(3, width)
        for x in (-1, 0, 6, 7, 16, 17, 19, 20):
            for y in (-1, 0, 6, 7):
                m = Machine(width, camera)
                m.u.reg_write(r.UC_X86_REG_EAX, x & 0xffffffff)
                m.u.reg_write(r.UC_X86_REG_EDX, y & 0xffffffff)
                before = m.snapshot()
                m.run(0x562300)
                expected = 0 <= x < width and camera <= x < camera + 17 and 0 <= y < 7
                assert m.u.reg_read(r.UC_X86_REG_EAX) == int(expected), (width,x,y)
                assert m.snapshot()[1:] == before[1:]
                total += 1

    # An oversized terrain/overlay fixture at the final existing cell must
    # not paint the unused seventeenth slot (or rows below a short arena).
    # Execute the actual helper ABI; a deterministic 128x128 solid blitter
    # applies the clip supplied by the helper to an otherwise clear HD buffer.
    for width,camera,rows,col,row in ((7,0,7,6,6),(16,0,7,15,6),
                                    (17,0,7,16,6),(20,0,7,16,6),
                                    (20,3,7,19,6),(16,0,3,15,2)):
        m = Machine(width,camera,rows)
        m.u.mem_map(stack,0x1000)  # seven caller-supplied blitter arguments
        m.u.reg_write(r.UC_X86_REG_EAX,surface)
        m.u.reg_write(r.UC_X86_REG_EDX,0x604000)
        m.u.reg_write(r.UC_X86_REG_ESI,32+(col-camera)*64)
        m.u.reg_write(r.UC_X86_REG_EBP,0x605000)
        m.u.reg_write(r.UC_X86_REG_EDI,0x603000)
        m.put(0x605000-12,136+row*64)
        m.put(0x603034,0x580100)
        before = m.snapshot()
        raster = bytearray(layout.width*layout.height)
        right = 32+64*min(width-camera,17)-1
        bottom = 136+64*min(rows,7)-1
        calls = []

        def intercept(m,address,reached):
            if address == 0x580100:
                sp = m.u.reg_read(r.UC_X86_REG_ESP)
                clip = tuple(m.get(sp+i) for i in (4,8,12,16))
                assert clip == (32,136,right,bottom), (width,rows,clip)
                x,y = m.u.reg_read(r.UC_X86_REG_EBX),m.u.reg_read(r.UC_X86_REG_ECX)
                assert m.u.reg_read(r.UC_X86_REG_EAX) == surface
                assert m.u.reg_read(r.UC_X86_REG_EDX) == 0x604000
                for py in range(max(y,clip[1]),min(y+127,clip[3])+1):
                    first,last = max(x,clip[0]),min(x+127,clip[2])
                    raster[py*layout.width+first:py*layout.width+last+1] = b'\x71'*(last-first+1)
                calls.append(clip)
                m.ret(28)

        m.run(0x563200,intercept)
        assert calls == [(32,136,right,bottom)]
        assert sum(bool(value) for value in raster) == 64*64
        assert all(not any(raster[y*layout.width+right+1:(y+1)*layout.width])
                   for y in range(layout.height))
        assert not any(raster[(bottom+1)*layout.width:])
        assert all(m.snapshot()[i] == before[i] for i in (0,3,4,5,6))
        assert m.u.reg_read(r.UC_X86_REG_ESP) == stack+28
        total += 1

    for width in (7, 17, 20):
        for camera in (0, 3, -1, 100):
            for selected in (0, 6, width - 1):
                m = Machine(width, camera)
                m.u.mem_write(state + 856, struct.pack("<HH", selected, 3))
                m.u.reg_write(r.UC_X86_REG_EAX, 0)
                before = m.snapshot()
                m.run(0x562200)
                assert m.get(state + 808) == layout.recenter(selected, width, camera)
                assert m.get(state + 812) == 0
                assert m.snapshot()[1:] == before[1:]
                total += 1

    for entry, valid, invalid in ((0x562400,0x42cbc1,0x42cbb8), (0x562480,0x42c8bc,0x42c8df)):
        for width, camera, x, y in ((20,3,1119,583),(7,0,480,136),(20,0,31,136),(20,0,544,200)):
            m = Machine(width,camera)
            m.mouse(x,y)

            def intercept(m, address, reached):
                if address in (valid, invalid):
                    reached.append(address)
                    m.u.emu_stop()

            target = m.run(entry, intercept)
            cell = layout.cell_at(x,y,width,camera)
            assert target == (valid if cell is not None else invalid)
            if cell is not None:
                xr, yr = ((r.UC_X86_REG_ESI,r.UC_X86_REG_EDI) if entry == 0x562400
                          else (r.UC_X86_REG_EBX,r.UC_X86_REG_ESI))
                assert (m.u.reg_read(xr),m.u.reg_read(yr)) == cell
                assert m.u.reg_read(r.UC_X86_REG_EDX) == state
            total += 1

    # Execute the real relocated redraw, guarding its tile calls and inspecting
    # every stock copyback. No game renderer or Windows process is involved.
    for width, camera in ((7,0),(17,0),(20,3)):
        for x,y in ((0,0),(320,0),(320,120),(320,135),(320,136),(400,300),
                    (1119,583),(1120,200),(320,584),(320,700)):
            m = Machine(width,camera)
            m.mouse(x,y)
            m.put(0x544d10,1)
            before = m.snapshot()
            # Original tile entry is hooked; the tile body itself is a renderer
            # stub after the core's actual-world visibility guard succeeds.
            tile_hook = next(p for p in core.PATCH_SPECS if p[1] == 0x42ffb0 - 0x400c00)
            m.u.mem_write(0x42ffb0,bytes.fromhex(tile_hook[3]))
            seen, rects = [], []

            def intercept(m,address,reached):
                if address == 0x42ffb5:
                    seen.append((m.u.reg_read(r.UC_X86_REG_EAX),m.u.reg_read(r.UC_X86_REG_EDX)))
                    sp = m.u.reg_read(r.UC_X86_REG_ESP)
                    for reg in (r.UC_X86_REG_EBP,r.UC_X86_REG_EDI,r.UC_X86_REG_ESI,
                                r.UC_X86_REG_ECX,r.UC_X86_REG_EBX):
                        m.u.reg_write(reg,m.get(sp)&0xffffffff)
                        sp += 4
                    m.u.reg_write(r.UC_X86_REG_ESP,sp)
                    m.ret()
                elif address == 0x4024e0:
                    sp = m.u.reg_read(r.UC_X86_REG_ESP)
                    rect = (m.u.reg_read(r.UC_X86_REG_EBX),m.u.reg_read(r.UC_X86_REG_ECX),
                            m.get(sp+4),m.get(sp+8),m.get(sp+12),m.get(sp+16))
                    rects.append(rect)
                    left,top,right,bottom,dx,dy = rect
                    assert 32 <= left <= right <= 1119, (x,y,rect)
                    assert 136 <= top <= bottom <= 583, (x,y,rect)
                    assert (dx,dy) == (left,top), rect
                    m.ret(16)
                elif address in (0x460f90,0x461000,0x460ea0):
                    m.ret()

            m.run(0x562800,intercept)
            expected = [(col,row) for col in range(camera,min(width,camera+17)) for row in range(7)]
            assert seen == expected, (width,camera,seen)
            assert rects
            assert m.u.reg_read(r.UC_X86_REG_ESP) == stack
            assert m.snapshot()[1:] == before[1:]
            total += 1

    for row in (0,3,6):
        m = Machine()
        m.u.reg_write(r.UC_X86_REG_EAX,row*64)
        m.u.reg_write(r.UC_X86_REG_EBP,state+0x800)
        m.put(state+0x800-8,16)

        def intercept(m,address,reached):
            if address == 0x42ffe6:
                reached.append(address)
                m.u.emu_stop()

        m.run(0x562600,intercept)
        assert m.u.reg_read(r.UC_X86_REG_EAX) == 136+64*row
        assert m.u.reg_read(r.UC_X86_REG_ECX) == 16
        total += 1

    if source_exe is not None:
        source = source_exe.read_bytes()
        assert hashlib.sha256(source).hexdigest() == core.EXPECTED_SOURCE_SHA256

        def native_function(m,start,end):
            m.u.mem_write(start,source[start-0x400c00:end-0x400c00])
            for _group,offset,_old,new,_note in core.PATCH_SPECS:
                address = offset + 0x400c00
                if start <= address < end:
                    m.u.mem_write(address,bytes.fromhex(new))

        # Execute the patched exit call and original full-surface clear owner.
        # Only the final virtual fill and following map graphics reload are
        # stubs. Whole buffers, guard bytes and the cleanup caller ABI matter:
        # map redraw does not repaint the gutter where the battle HUD appeared.
        for back_kind in ("distinct", "primary", "null"):
            m = Machine()
            primary = 0x51d4c0
            m.put(0x5202e0, {"distinct": surface, "primary": primary, "null": 0}[back_kind])
            native_function(m,0x401e60,0x401e87)
            native_function(m,0x42f53d,0x42f542)
            m.u.mem_write(0x42f542,b'\xc3')
            count = layout.width * layout.height
            pixels = {primary: 0x800000, surface: 0x900000}
            metadata = {}
            for obj, buffer in pixels.items():
                m.u.mem_map(buffer,0x100000)
                m.u.mem_write(buffer,b'\x93' * count + b'\xa7' * 64)
                m.u.mem_write(obj,struct.pack("<HH",layout.width,layout.height))
                m.put(obj+4,buffer)
                m.put(obj+0xb8,0x603000)
                metadata[obj] = bytes(m.u.mem_read(obj,0xc0))
            m.put(0x603020,0x580300)
            before = m.snapshot()
            fills, reloads = [], []

            def intercept(m,address,reached):
                if address == 0x580300:
                    obj = m.u.reg_read(r.UC_X86_REG_EAX)
                    sp = m.u.reg_read(r.UC_X86_REG_ESP)
                    assert m.get(sp+4) == count
                    assert all(m.u.reg_read(reg) == 0 for reg in
                               (r.UC_X86_REG_EBX,r.UC_X86_REG_ECX,r.UC_X86_REG_EDX))
                    m.u.mem_write(pixels[obj],bytes(count))
                    fills.append(obj)
                    m.ret(4)
                elif address == 0x422960:
                    assert m.snapshot() == before
                    assert m.u.reg_read(r.UC_X86_REG_EFLAGS) == 0x202
                    assert m.u.reg_read(r.UC_X86_REG_ESP) == stack-8
                    reloads.append(address)
                    m.ret()

            m.run(0x42f53d,intercept)
            assert fills == ([surface,primary] if back_kind == "distinct" else [primary])
            assert reloads == [0x422960]
            assert m.snapshot() == before and m.u.reg_read(r.UC_X86_REG_ESP) == stack
            for obj,buffer in pixels.items():
                expected = bytes(count) if obj in fills else b'\x93' * count
                assert bytes(m.u.mem_read(buffer,count)) == expected
                assert bytes(m.u.mem_read(buffer+count,64)) == b'\xa7' * 64
                assert bytes(m.u.mem_read(obj,0xc0)) == metadata[obj]
            total += 1

        # Run the original terrain, neighbor composition and unit sprite owners.
        # Only asset acquisition, final blitters and unrelated effect timing are
        # stubs. In particular 0042F820 retains its real per-tile clip arguments.
        for width,camera,col,row,rows in ((7,0,0,0,7),(7,0,6,6,7),(17,0,16,6,7),
                                          (20,3,3,0,7),(20,3,19,6,7),(20,0,16,3,7),
                                          (16,0,15,6,7),(16,0,15,2,3)):
            for motion in (None,(-24,-24),(-24,24),(24,-24),(24,24)):
                m = Machine(width,camera,rows)
                native_function(m,0x42f820,0x430b12)
                m.put(0x511230,surface)
                m.put(surface+0xb8,0x603000)
                m.put(0x603034,0x580100)
                m.put(0x603014,0x580200)
                m.u.mem_write(state+0x5fe,b'\xff'*800)
                m.u.mem_write(state+0x91e,b'\xff'*800)
                m.u.mem_write(state+0x5fe+col*40+row*2,struct.pack('<h',0))
                if motion:
                    # A sentinel unit in each valid neighbor exercises every
                    # directional animation-composition branch at map edges.
                    for neighbor_x in range(max(0,col-1),min(width,col+2)):
                        for neighbor_y in range(max(0,row-1),min(rows,row+2)):
                            m.u.mem_write(state+0x5fe+neighbor_x*40+neighbor_y*2,
                                          struct.pack('<h',0))
                m.put(state+0x33c,-1)
                for address in (0x511b58,0x514e44,0x514e48,0x514e54,0x514e58):
                    m.put(address,-1)
                m.put(0x512360,0 if motion else -1)
                m.put(0x523f70,motion[0] if motion else 0)
                m.put(0x523f74,motion[1] if motion else 0)
                m.u.reg_write(r.UC_X86_REG_EAX,col)
                m.u.reg_write(r.UC_X86_REG_EDX,row)
                before = m.snapshot()
                draws = []
                def on_occupancy_read(u,access,address,size,value,user):
                    if size == 2:
                        cell_x, remainder = divmod(address-(state+0x5fe),40)
                        cell_y = remainder//2
                        assert 0 <= cell_x < width and 0 <= cell_y < rows, (
                            f"Neighbor outside arena at {u.reg_read(r.UC_X86_REG_EIP):08X}",
                            (col,row),(cell_x,cell_y),width)

                read_hook = m.u.hook_add(UC_HOOK_MEM_READ,on_occupancy_read,
                                        begin=state+0x5fe,end=state+0x91f)

                def intercept(m,address,reached):
                    if address in (0x405ec0,0x413080):
                        m.u.reg_write(r.UC_X86_REG_EAX,0x604000)
                        m.ret()
                    elif address == 0x426ef0:
                        m.u.reg_write(r.UC_X86_REG_EAX,0)
                        m.ret()
                    elif address == 0x42f7c0:
                        m.u.reg_write(r.UC_X86_REG_EAX,1)
                        m.ret()
                    elif address == 0x40bb60:
                        m.ret()
                    elif address == 0x580100:
                        sp = m.u.reg_read(r.UC_X86_REG_ESP)
                        clip = tuple(m.get(sp+offset) for offset in (4,8,12,16))
                        pixel = (m.u.reg_read(r.UC_X86_REG_EBX),m.u.reg_read(r.UC_X86_REG_ECX))
                        expected = (32+(col-camera)*64,136+row*64)
                        if clip == (32,136,32+64*min(width-camera,17)-1,136+64*rows-1):
                            assert pixel == expected, (width,col,row,pixel)
                        else:
                            assert clip == (*expected,expected[0]+63,expected[1]+63), clip
                        draws.append((pixel,clip))
                        m.ret(28)

                m.run(0x42ffb0,intercept)
                m.u.hook_del(read_hook)
                assert len(draws) >= 2, (width,col,row,draws)
                assert all(m.snapshot()[i] == before[i] for i in (1,2,4,5,6))
                assert m.u.reg_read(r.UC_X86_REG_ESP) == stack
                total += 1

        # Include the original grid-owner prologue/early-return path so rejected
        # input proves stack and saved-register restoration, not just helper math.
        for width,camera in ((7,0),(20,3)):
            for x,y in ((31,136),(32,135),(1120,136),(32,584),(1119,583),(544,200)):
                m = Machine(width,camera)
                m.mouse(x,y)
                native_function(m,0x42cb50,0x42cbc2)
                before = m.snapshot()

                def intercept(m,address,reached):
                    if address == 0x42cbc1:
                        reached.append(address)
                        m.u.emu_stop()

                target = m.run(0x42cb50,intercept)
                cell = layout.cell_at(x,y,width,camera)
                assert target == (0x42cbc1 if cell else stop)
                if cell is None:
                    assert m.u.reg_read(r.UC_X86_REG_ESP) == stack
                    assert m.snapshot()[1:] == before[1:]
                else:
                    assert (m.u.reg_read(r.UC_X86_REG_ESI),m.u.reg_read(r.UC_X86_REG_EDI)) == cell
                total += 1

        # Execute the original keyboard/drag pan owner with the exact source
        # edits, replacing only external time/input/render calls with stubs.
        for width,camera,key in ((7,100,205),(20,0,203),(20,0,205),(20,3,205),(20,3,203)):
            m = Machine(width,camera)
            m.mouse(1279,500)  # keyboard scrolling remains usable over the HUD
            native_function(m,0x42c840,0x42cb50)

            def intercept(m,address,reached):
                if address == 0x4207b0:
                    m.u.reg_write(r.UC_X86_REG_EAX,100)
                    m.u.reg_write(r.UC_X86_REG_EDX,0)
                    m.ret()
                elif address == 0x461570:
                    query = m.u.reg_read(r.UC_X86_REG_EAX)
                    m.u.reg_write(r.UC_X86_REG_EAX,int(query == key))
                    m.ret()
                elif address == 0x430c20:
                    assert 0 <= m.get(state+808) <= max(0,width-17)
                    m.ret()

            m.run(0x42c840,intercept)
            initial = layout.clamp_camera(camera,width)
            delta = -1 if key == 203 else 1
            assert m.get(state+808) == layout.clamp_camera(initial+delta,width)
            assert m.u.reg_read(r.UC_X86_REG_ESP) == stack
            total += 1

        for width,camera,delta in ((7,0,800),(20,0,800),(20,3,-800)):
            m = Machine(width,camera)
            m.mouse(64,168)
            m.put(state+1534+40*camera,-1)
            native_function(m,0x42c840,0x42cb50)
            lost_calls = [0]

            def intercept(m,address,reached):
                if address == 0x4207b0:
                    m.u.reg_write(r.UC_X86_REG_EAX,100)
                    m.u.reg_write(r.UC_X86_REG_EDX,0)
                    m.ret()
                elif address == 0x461570:
                    m.u.reg_write(r.UC_X86_REG_EAX,0)
                    m.ret()
                elif address == 0x460900:
                    lost_calls[0] += 1
                    m.u.reg_write(r.UC_X86_REG_EAX,int(lost_calls[0] <= 2))
                    m.ret()
                elif address == 0x4605d0:
                    m.mouse(64+delta,168+800)
                    m.ret()
                elif address == 0x430c20:
                    assert 0 <= m.get(state+808) <= max(0,width-17)
                    assert m.get(state+812) == 0
                    m.ret()
                elif address in (0x460f90,0x460ea0):
                    m.ret()

            m.run(0x42c840,intercept)
            assert lost_calls[0] == 3
            assert m.get(state+808) == (max(0,width-17) if delta > 0 else 0)
            assert m.get(state+812) == 0
            assert m.u.reg_read(r.UC_X86_REG_ESP) == stack
            total += 1

        for width,camera,col,row in ((7,0,6,6),(7,0,7,0),(20,3,19,6),(20,3,2,0),(20,3,3,-1)):
            m = Machine(width,camera)
            native_function(m,0x430b20,0x430c17)
            m.u.reg_write(r.UC_X86_REG_EAX,col & 0xffffffff)
            m.u.reg_write(r.UC_X86_REG_EDX,row & 0xffffffff)
            seen,rects = [],[]

            def intercept(m,address,reached):
                if address == 0x42ffb0:
                    seen.append((m.u.reg_read(r.UC_X86_REG_EAX),m.u.reg_read(r.UC_X86_REG_EDX)))
                    m.ret()
                elif address == 0x460bb0:
                    sp = m.u.reg_read(r.UC_X86_REG_ESP)
                    left,right,top = (m.u.reg_read(reg) for reg in
                                      (r.UC_X86_REG_EDX,r.UC_X86_REG_ECX,r.UC_X86_REG_EBX))
                    bottom = m.get(sp+4)
                    assert (left,top,right,bottom) == (32+64*(col-camera),136+64*row,
                                                       96+64*(col-camera),200+64*row)
                    rects.append((left,top,right,bottom))
                    m.ret(4)
                elif address == 0x4024e0:
                    sp = m.u.reg_read(r.UC_X86_REG_ESP)
                    left,top = m.u.reg_read(r.UC_X86_REG_EBX),m.u.reg_read(r.UC_X86_REG_ECX)
                    assert (left,top,m.get(sp+4),m.get(sp+8)) == (
                        32+64*(col-camera),136+64*row,95+64*(col-camera),199+64*row)
                    m.ret(16)
                elif address == 0x460ea0:
                    m.ret()

            m.run(0x430b20,intercept)
            visible = 0 <= col < width and camera <= col < camera+17 and 0 <= row < 7
            assert seen == ([(col,row)] if visible else [])
            assert bool(rects) == visible
            assert m.u.reg_read(r.UC_X86_REG_ESP) == stack
            total += 1
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolchain-path", type=Path)
    parser.add_argument("--source-exe", type=Path)
    parser.add_argument("--require-machine-tools", action="store_true")
    args = parser.parse_args()
    if args.toolchain_path:
        sys.path.insert(0,str(args.toolchain_path))
    test_patch_contract(args.source_exe)
    try:
        importlib.import_module("keystone")
        importlib.import_module("unicorn")
    except ImportError:
        if args.require_machine_tools:
            raise
        print("battle HD core byte-contract tests passed; x86 tools unavailable (emulator checks skipped)")
    else:
        count = machine_tests(args.source_exe)
        print(f"battle HD core byte/assembly tests and {count} x86 emulator scenarios passed")


if __name__ == "__main__":
    main()
