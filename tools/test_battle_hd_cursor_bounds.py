#!/usr/bin/env python3
"""Battle-only cursor bounds: stage isolation and native x86 transition tests.

The optional machine lane reads the SHA-pinned original executable and emulates
its cursor switch, sprite-margin setter and inclusive input clamp. Asset-size
queries and device/render calls are fixtures; no game or Windows UI is launched.
Keystone/Unicorn remain external development dependencies.
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
import patch_clash95_hd as patcher
from battle_hd_section import validate_spans


def canonical(rows):
    text = "\n".join(f"{p.group}|{p.offset:06X}|{p.old_hex}|{p.new_hex}|{p.note}" for p in rows)
    return hashlib.sha256(text.encode()).hexdigest()


def verify_battle_context_routes(source):
    """Original-byte contracts for battle lifetime and temporary default hooks.

    The pointer is published by the native four-byte copy at 42EC86 and cleared
    after free at 42F538. Banner recenter precedes its owner restoration; the
    shared results wait polls while default-owned, then restores before return.
    These are source contracts, not evidence that a game session traversed them.
    """
    contracts = (
        (0x42ec43, "8db4248c000000"),
        (0x42ec63, "bf48205300"),
        (0x42ec6d, "b87c0f0000b904000000e874530400894424705789c8c1e902f2a58ac880e103f2a45f833d48205300000f8467030000"),
        (0x42ea49, "bab0e84200"),
        (0x42ea65, "8915d8995100"),
        (0x42d763, "baa0174600"),
        (0x42d77c, "8915d8995100"),
        (0x42da41, "e8aa300300"),
        (0x42da5a, "8b4424148b542418a3d8995100"),
        (0x44539c, "b9a0174600"),
        (0x4453b5, "890dd8995100"),
        (0x44543f, "e88cb10100"),
        (0x445857, "8b4424048b542418a3d8995100"),
        (0x42f52c, "a148205300e8a74b040031c0a348205300"),
        (0x42f594, "8b8424840000008b94248c000000a3d8995100"),
        # Human battle setup selects C8, sets the banner/default cursor to A0,
        # then the banner selects that A0. A0 is HD even in the inherited path.
        (0x42f2d6, "bac8965100b8d84c5400bfa0965100e8961a0300b8d84c5400893d50515400"),
        (0x42d98a, "b8d84c54008b15505154008b4c2410e8e2330300"),
    )
    for va, expected in contracts:
        raw = bytes.fromhex(expected)
        assert source[va-0x400c00:va-0x400c00+len(raw)] == raw, hex(va)
    return contracts


def test_stage_contract():
    profile = patcher.parse_resolution("1280x720")
    # Pins were measured before adding the stage-only override, including the
    # generated 1280 profile. Do not reseed them for this battle-only change.
    assert canonical(patcher.PATCHES) == "6683ee66851d23a28d856a8576e6b58c9b1285e0766bb592b9cdb0847bc8c55c"
    assert canonical(patcher.select_patches(patcher.DEFAULT_STAGE)) == "1c334f12bcc3206ee98b239733689bdb6982b9ce7ab0007487e105e7d1f688f9"
    assert canonical(patcher.select_patches_for(patcher.DEFAULT_STAGE, profile)) == "a4e202efb2d7c6dcc7cdfd05442036994585f98c1425f581adb54f652a9320a2"
    inherited = patcher.select_patches_for(patcher.DEFAULT_STAGE + "-castlecenter-all", profile)
    assert canonical(inherited) == "7ac49f2aa1fcdea8bd5b637b24489962c62e8441c86e1191d0bd2ca9ede11e2e"
    selected = patcher.select_patches_for(patcher.BATTLE_HD_STAGE, profile)
    validate_spans(selected)
    by_offset = {p.offset: p for p in selected}
    replaced = []
    for original in inherited:
        actual = by_offset[original.offset]
        if original != actual:
            replaced.append(original.offset)
            assert actual.group == "battle-hd-input"
            assert actual.old == original.old
    assert replaced == [0x05fe61, 0x060211]
    assert by_offset[0x0e8c10] == next(p for p in inherited if p.offset == 0x0e8c10)
    assert by_offset[0x0e8dc0] == next(p for p in inherited if p.offset == 0x0e8dc0)
    hook = by_offset[0x060211]
    assert hook.new[0] == 0xe9 and hook.new[5:] == b"\x90" * 33
    assert 0x460e16 + struct.unpack("<i", hook.new[1:5])[0] == 0x563400
    block = next(b for b in core.ASSEMBLY_BLOCKS if b[0] == "battle_cursor_viewport")
    assert block[1] == 0x563400
    assert core.CORE_CODE[0x1400:0x1400 + len(bytes.fromhex(block[3]))] == bytes.fromhex(block[3])
    relative = next(b for b in core.ASSEMBLY_BLOCKS if b[0] == "battle_relative_mouse")
    assert block[2].split("battle:\n")[0] == relative[2].split("battle:\n")[0]
    return selected, inherited


def machine_tests(source_exe):
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn import x86_const as r

    source = source_exe.read_bytes()
    assert hashlib.sha256(source).hexdigest() == core.EXPECTED_SOURCE_SHA256
    verify_battle_context_routes(source)
    selected, inherited = test_stage_contract()
    block = next(b for b in core.ASSEMBLY_BLOCKS if b[0] == "battle_cursor_viewport")
    assembler = Ks(KS_ARCH_X86, KS_MODE_32)
    assert bytes(assembler.asm(block[2], block[1])[0]).hex() == block[3]
    for patches in (selected, inherited):
        for patch in patches:
            if patch.offset in (0x060211, 0x0e8dc0):
                assert source[patch.offset:patch.offset + len(patch.old)] == patch.old

    regs = (r.UC_X86_REG_EAX, r.UC_X86_REG_EBX, r.UC_X86_REG_ECX,
            r.UC_X86_REG_EDX, r.UC_X86_REG_ESI, r.UC_X86_REG_EDI,
            r.UC_X86_REG_EBP)
    obj, stack, stop, table = 0x544cd8, 0x710000, 0x580000, 0x581000
    # Fixture widths/heights and hotspots. C8 reproduces the observed native
    # (1,1,609,450) bounds; F0 also exercises the native nonzero hotspot ABI.
    sprites = {0x5196a0: (16,24,0,0), 0x5196c8: (30,29,0,0),
               0x5196f0: (48,48,19,20), 0x5197b8: (38,41,5,7),
               0x519808: (24,32,0,0)}

    class Machine:
        def __init__(self, patches, owner, shift, visible, battle=0):
            self.u = Uc(UC_ARCH_X86, UC_MODE_32)
            self.u.mem_map(0x400000, 0x190000)
            self.u.mem_map(stack - 0x10000, 0x10000)
            for start, end in ((0x460d80,0x460e9a), (0x460b20,0x460baf),
                               (0x460a9d,0x460ae2)):
                self.u.mem_write(start, source[start-0x400c00:end-0x400c00])
            self.u.mem_write(core.CORE_CODE_VA, core.CORE_CODE)
            for patch in patches:
                if patch.offset in (0x060211,0x0e8dc0):
                    self.u.mem_write(patch.offset+0x400c00, patch.new)
            for meta, (_,_,hx,hy) in sprites.items():
                self.put(meta, 3)
                self.put(meta+4, 3)
                self.put(meta+20, hx)
                self.put(meta+24, hy)
                self.put(meta+28, 0x2468)
                self.put(meta+32, 0x1357)
            self.put(0x5199d8, owner)
            self.put(0x532048, battle)
            self.put(obj+0x454, shift)
            self.put(obj+0x38, visible)
            self.put(obj+0x460, table)
            self.put(table+0x14, stop+0x100)
            self.put(table+0x04, stop+0x200)
            self.put(obj+0x24, 576 << shift)
            self.put(obj+0x28, 360 << shift)
            self.events = []
            self.finished = False
            self.u.hook_add(UC_HOOK_CODE, self.intercept)

        def put(self, address, value):
            self.u.mem_write(address, struct.pack("<I", value & 0xffffffff))

        def get(self, address):
            return struct.unpack("<I", self.u.mem_read(address,4))[0]

        def snapshot(self):
            return tuple(self.u.reg_read(reg) for reg in regs)

        def ret(self):
            sp = self.u.reg_read(r.UC_X86_REG_ESP)
            self.u.reg_write(r.UC_X86_REG_EIP, self.get(sp))
            self.u.reg_write(r.UC_X86_REG_ESP, sp+4)

        def intercept(self, u, address, size, user):
            if address == stop:
                self.finished = True
                u.emu_stop()
            elif address in (0x405ef0,0x405ee0):
                self.events.append(address)
                dims = sprites[self.get(obj+0x3c)]
                u.reg_write(r.UC_X86_REG_EAX, dims[address == 0x405ee0])
                self.ret()
            elif address in (stop+0x100,stop+0x200,0x460f90,0x460ea0):
                self.events.append(address)
                self.ret()
            elif address in (0x563400,0x460b20):
                self.events.append(address)

        def run(self, address):
            self.events.clear()
            self.finished = False
            self.u.emu_start(address, 0, count=2000)
            assert self.finished, hex(address)
            assert self.u.reg_read(r.UC_X86_REG_ESP) == stack

        def switch(self, meta):
            for index, reg in enumerate(regs):
                self.u.reg_write(reg, 0x12340000+index)
            self.u.reg_write(r.UC_X86_REG_EAX, obj)
            self.u.reg_write(r.UC_X86_REG_EDX, meta)
            self.u.reg_write(r.UC_X86_REG_ESP, stack-4)
            self.put(stack-4, stop)
            before = self.snapshot()
            self.run(0x460d80)
            assert all(self.snapshot()[i] == before[i] for i in (1,2,4,5,6))
            assert self.get(obj+0x3c) == meta
            return tuple(self.get(obj+offset) for offset in (0x10,0x14,0x18,0x1c))

        def clamp(self, x, y):
            self.put(obj+0x24, x)
            self.put(obj+0x28, y)
            self.u.reg_write(r.UC_X86_REG_EDX, obj)
            # Enter the unchanged clamp with the native five-register save
            # frame from 460A50; its real epilogue must unwind that frame.
            self.u.reg_write(r.UC_X86_REG_ESP, stack-24)
            for i,value in enumerate((0x15,0x14,obj,0x12,0x11,stop)):
                self.put(stack-24+i*4, value)
            self.run(0x460a9d)
            return self.get(obj+0x24), self.get(obj+0x28)

    total = 0
    sequence = (0x5196a0,0x5196c8,0x5196f0,0x5197b8,0x5196a0,0x519808,0x5196a0)
    contexts = ((0x42e8b0,0), (0x4617a0,0), (0,0), (0x42e8b1,0),
                (0x4617a0,0x570000), (0,0x570000), (0x42e8b1,0x570000))
    for owner,battle in contexts:
        active = owner == 0x42e8b0 or (owner == 0x4617a0 and battle != 0)
        for shift in (0,6):
            for visible in (0,1):
                m = Machine(selected,owner,shift,visible,battle)
                legacy = Machine(inherited,owner,shift,visible,battle)
                for meta in sequence:
                    # Clamp probes below alter m's mouse state. Give both
                    # switch implementations identical inputs for comparison.
                    for fixture in (m,legacy):
                        fixture.put(obj+0x24,576 << shift)
                        fixture.put(obj+0x28,360 << shift)
                    bounds = m.switch(meta)
                    legacy_bounds = legacy.switch(meta)
                    width,height = ((1280,720) if active or meta == 0x5196a0 else (640,480))
                    sw,sh,hx,hy = sprites[meta]
                    pixels = (hx+1,hy+1,width-(sw-hx+1),height-(sh-hy+1))
                    assert bounds == tuple(v << shift for v in pixels), (owner,meta,shift,bounds)
                    assert m.events.count(0x563400) == m.events.count(0x460b20) == 1
                    assert m.get(meta+32) == 0 and m.get(meta+28) == 0x2468
                    if not active or meta == 0x5196a0:
                        assert bounds == legacy_bounds
                        assert bytes(m.u.mem_read(obj+0x30,8)) == bytes(legacy.u.mem_read(obj+0x30,8))
                    else:
                        assert (bounds[2]-legacy_bounds[2],bounds[3]-legacy_bounds[3]) == (640 << shift,240 << shift)
                    # Native inclusive clamp: exact endpoints survive, one raw
                    # unit outside either edge clips, and HUD centers survive
                    # when battle ownership makes the range wide enough.
                    left,top,right,bottom = bounds
                    for x,y in ((left,top),(right,bottom),(left-1,top-1),
                                (right+1,bottom+1),(1201 << shift,521 << shift)):
                        assert m.clamp(x,y) == (min(max(x,left),right),min(max(y,top),bottom))
                        total += 1
                    # Re-selecting identical metadata does not execute the
                    # helper, setter, asset queries or device/render callbacks.
                    assert m.switch(meta) == bounds and m.events == []
                    total += 1

    # The native early return is intentionally not a lifecycle refresh: a
    # changed owner alone cannot update existing bounds until metadata changes.
    m = Machine(selected,0x4617a0,6,0)
    native = m.switch(0x5196c8)
    m.put(0x5199d8,0x42e8b0)
    assert m.switch(0x5196c8) == native and m.events == []
    assert m.switch(0x5196a0)[2] > 1120 << 6
    assert m.switch(0x5196c8)[2] == 1249 << 6
    total += 3

    # Original-backed human route: nonbattle A0 -> battle C8 -> banner A0 ->
    # restored battle same A0. The final same-metadata no-op already has HD
    # bounds, so changing the generic metadata cache is unnecessary here.
    m = Machine(selected,0x4617a0,6,0)
    assert m.switch(0x5196a0)[2] == 1263 << 6
    m.put(0x532048,0x570000)
    m.put(0x5199d8,0x42e8b0)
    assert m.switch(0x5196c8)[2] == 1249 << 6
    m.put(0x5199d8,0x4617a0)
    banner_bounds = m.switch(0x5196a0)
    assert banner_bounds[2] == 1263 << 6
    m.put(0x5199d8,0x42e8b0)
    assert m.switch(0x5196a0) == banner_bounds and m.events == []
    # Live default-owned overlays also retain wide nondefault cursor bounds.
    m.put(0x5199d8,0x4617a0)
    assert m.switch(0x5196c8)[2] == 1249 << 6
    m.put(0x532048,0)
    assert m.switch(0x5196a0)[2] == 1263 << 6
    assert m.switch(0x5196c8)[2] == 609 << 6
    total += 7
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-exe", type=Path)
    parser.add_argument("--toolchain-path", type=Path)
    parser.add_argument("--require-machine-tools", action="store_true")
    args = parser.parse_args()
    test_stage_contract()
    if args.toolchain_path:
        sys.path.insert(0,str(args.toolchain_path))
    if args.source_exe is None:
        if args.require_machine_tools:
            parser.error("--require-machine-tools also requires --source-exe")
        print("battle cursor stage isolation passed; native machine checks skipped (no --source-exe)")
        return
    count = machine_tests(args.source_exe)
    print(f"battle cursor stage isolation and {count} native x86 transition/clamp scenarios passed")


if __name__ == "__main__":
    main()
