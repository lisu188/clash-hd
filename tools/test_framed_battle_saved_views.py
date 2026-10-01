#!/usr/bin/env python3
"""Portable contracts and synthetic x86 camera execution; no game or outputs.

Use --toolchain-path for retained Unicorn and --require-machine-tools to fail
closed when the CPU lane cannot run. --source-exe additionally authenticates
native source spans; it never builds or writes a candidate.
"""
import argparse
import hashlib
import importlib
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import framed_battle_saved_views as module
from src.patcher import partial_tile_clip as clip

CASES = ((800,600,9),(1024,768,13),(1280,720,17),(1280,960,17),
         (1366,768,18),(1920,1080,20),(2560,1440,20),(3440,1440,20),
         (3840,2160,20),(802,602,9),(640,480,7))
SOURCE_EXE = None


def machine_tools():
    try:
        u = importlib.import_module("unicorn")
        r = importlib.import_module("unicorn.x86_const")
        if not callable(u.Uc) or not all(type(getattr(r, "UC_X86_REG_" + n)) is int
                for n in ("EAX","EBX","ECX","EDX","ESI","EDI","EBP","ESP","EFLAGS","EIP")):
            raise ImportError("Unicorn x86 API differs")
        return u, r
    except (ImportError, AttributeError, OSError) as error:
        raise ImportError("Unicorn x86 API unavailable") from error


class SourceTests(unittest.TestCase):
    def test_reviewed_sources_and_mismatch_rejection(self):
        self.assertEqual(module.verify_sources(), module.PINNED_SOURCES | {
            module.SOURCE: hashlib.sha256((ROOT/module.SOURCE).read_bytes()).hexdigest()})
        with patch.dict(module.PINNED_SOURCES,
                        {"src/patcher/framed_battle_viewport.py": "0" * 64}):
            with self.assertRaisesRegex(ValueError, "reviewed battle saved-view"):
                module.verify_sources()

    def test_emitter_hash_is_bound_and_mid_reconstruction_edit_fails(self):
        before = module.verify_sources()
        module._verify_source_snapshot(before)
        read = Path.read_bytes
        def changed(path):
            data = read(path)
            return data + b"# concurrent edit\n" if path == ROOT/module.SOURCE else data
        with patch.object(Path, "read_bytes", changed):
            self.assertNotEqual(module.verify_sources()[module.SOURCE], before[module.SOURCE])
            with self.assertRaisesRegex(ValueError, "changed during reconstruction"):
                module._verify_source_snapshot(before)

    def test_exact_sub_jump_spans_and_continuations(self):
        self.assertEqual(module.SITES, {
            "attacker_right": (0x42F5E4, "83e807e90ffcffff", 0x42F1FB, 836),
            "defender_right": (0x42F5F7, "83e807e91ffcffff", 0x42F21E, 840)})
        for va, value, target, _ in module.SITES.values():
            old = bytes.fromhex(value)
            self.assertEqual(len(old), 8)
            self.assertEqual(old[:4], bytes.fromhex("83e807e9"))
            self.assertEqual(va + 8 + struct.unpack_from("<i", old, 4)[0], target)

    def test_strict_arguments_and_alias_rejection(self):
        args = dict(base_va=0x10000000, width=800, height=600, admission_va=0x10002000)
        for key, value in (("base_va",True),("base_va",0),("admission_va",0x80000000),
                           ("admission_va",0x10000001),("width",True),("height",479)):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                module._emit_code(**(args | {key:value}))
        with self.assertRaisesRegex(ValueError, "immutable"):
            module.emit_battle_saved_views(b"", bytearray(), **args)
        with self.assertRaisesRegex(ValueError, "unknown original"):
            module.emit_battle_saved_views(b"", b"", **args)

    def test_all_geometry_code_has_explicit_relocations_and_stays_uninstalled(self):
        for width, height, _ in CASES:
            bundle = module._emit_code(base_va=0x10000000, width=width, height=height,
                                       admission_va=0x10002000)
            self.assertFalse(bundle.installation_ready)
            self.assertEqual(set(bundle.entries), {"attacker_right", "defender_right"})
            self.assertLess(len(bundle.code), 4096)
            self.assertEqual(len(clip.absolute_relocation_offsets(bundle)), 6)
            relative = [r for r in bundle.relocations if r.kind == "rel32"]
            self.assertEqual(len(relative), 6)
            self.assertEqual(sum(r.purpose == "required_owned_battle_admission"
                                 for r in relative), 2)
            self.assertEqual({r.target for r in relative}, {0x10002000,0x42F1FB,0x42F21E})

    def test_original_spans_highlow_and_each_tampered_region(self):
        if SOURCE_EXE is None:
            self.skipTest("optional authenticated original not supplied")
        original = SOURCE_EXE.read_bytes()
        clip.verify_original(original)
        module._authenticate_native(original, original)
        for name, (lo, hi, digest) in module.NATIVE_SPANS.items():
            at = clip.file_offset(original, lo, hi-lo)
            self.assertEqual(hashlib.sha256(original[at:at+hi-lo]).hexdigest(), digest)
            changed = bytearray(original); changed[at] ^= 1
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "native saved-camera span"):
                module._authenticate_native(original, bytes(changed))
        site = module.SITES["attacker_right"]
        with patch.dict(module.SITES, {"attacker_right": (site[0],"83e808e90ffcffff",*site[2:])}):
            with self.assertRaisesRegex(ValueError, "old bytes differ"):
                module._authenticate_native(original, original)


class Machine:
    BASE, ADMISSION = 0x10000000, 0x10002000
    HEAP, STACK, ESP = 0x20000000, 0x30000000, 0x30000F00
    NAMES = ("EAX","EBX","ECX","EDX","ESI","EDI","EBP","ESP")
    PRESERVED = dict(EBX=0x22334455, ECX=0x33445566, EDX=0x44556677,
                     ESI=0x55667788, EDI=0x66778899, EBP=0x778899AA, ESP=ESP)

    def __init__(self, tools, width=800, height=600, delta=0):
        self.u, r = tools
        self.uc = self.u.Uc(self.u.UC_ARCH_X86, self.u.UC_MODE_32)
        self.regs = {n: getattr(r, "UC_X86_REG_"+n) for n in (*self.NAMES,"EFLAGS","EIP")}
        self.delta = delta
        bundle = module._emit_code(base_va=self.BASE, width=width, height=height,
                                   admission_va=self.ADMISSION)
        self.entries = {n:va+delta for n,va in bundle.entries.items()}
        code = bytearray(bundle.code)
        for rel in bundle.relocations:
            if rel.kind == "abs32":
                struct.pack_into("<I", code, rel.offset, rel.target+delta)
        # Relative fields retain their displacement when every image VA moves.
        for address, size in ((self.BASE+delta,0x4000),(0x42F000+delta,0x1000),
                              (0x519000+delta,0x1000),(0x532000+delta,0x1000),
                              (self.HEAP,0x1000),(self.STACK,0x1000)):
            self.uc.mem_map(address, size)
        self.uc.mem_write(self.BASE+delta, bytes(code))
        self.uc.hook_add(self.u.UC_HOOK_CODE, self.on_code)
        self.uc.hook_add(self.u.UC_HOOK_MEM_WRITE, self.on_write)
        self.uc.hook_add(self.u.UC_HOOK_MEM_READ, self.on_read)

    def put(self, at, value):
        self.uc.mem_write(at, struct.pack("<I", value & 0xFFFFFFFF))

    def on_code(self, uc, address, size, data):
        if address == self.ADMISSION+self.delta:
            self.admission_flags.append(uc.reg_read(self.regs["EFLAGS"]))
        if address in (0x42F1FB+self.delta, 0x42F21E+self.delta):
            self.continuation = address
            uc.emu_stop()

    def on_write(self, uc, access, address, size, value, data):
        self.writes.append((address,size))

    def on_read(self, uc, access, address, size, value, data):
        if self.HEAP <= address < self.HEAP+0x1000:
            self.heap_reads.append((address,size))

    def execute(self, name, *, columns=20, eax=None, rows=7, y=0, player=0,
                admission=1, owner=None, pointer=None, flags=0x202):
        self.writes, self.heap_reads, self.admission_flags = [], [], []
        self.continuation = None
        self.uc.mem_write(self.HEAP, b"\xA5"*0x1000)
        self.put(self.HEAP+800, rows); self.put(self.HEAP+804, columns)
        self.put(self.HEAP+812, y)
        self.put(self.HEAP+module.SITES[name][3], player)
        self.put(0x532048+self.delta, self.HEAP if pointer is None else pointer)
        self.put(0x5199D8+self.delta, 0x42E8B0+self.delta if owner is None else owner)
        self.uc.mem_write(self.ADMISSION+self.delta,
                         b"\xB8"+struct.pack("<I",admission & 0xFFFFFFFF)+b"\xC3")
        snapshots = {at: bytes(self.uc.mem_read(at,size)) for at,size in
                     ((self.HEAP,0x1000),(0x519000+self.delta,0x1000),(0x532000+self.delta,0x1000))}
        registers = self.PRESERVED | {"EAX":columns if eax is None else eax}
        for n, v in registers.items(): self.uc.reg_write(self.regs[n], v & 0xFFFFFFFF)
        self.uc.reg_write(self.regs["EFLAGS"], flags)
        self.uc.emu_start(self.entries[name], self.BASE+self.delta+0x4000, count=200)
        result = {n:self.uc.reg_read(r) for n,r in self.regs.items()}
        assert self.continuation == module.SITES[name][2]+self.delta, result
        assert all(result[n] == value for n,value in self.PRESERVED.items()), result
        assert self.admission_flags and not any(v & 0x400 for v in self.admission_flags)
        assert all(self.STACK <= at < at+size <= self.STACK+0x1000 for at,size in self.writes)
        assert all(bytes(self.uc.mem_read(at,len(before))) == before for at,before in snapshots.items())
        return result


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: cls.tools = machine_tools()
        except ImportError as error: raise unittest.SkipTest(str(error))
        u, r = cls.tools
        cls.reference = u.Uc(u.UC_ARCH_X86, u.UC_MODE_32)
        cls.reference.mem_map(0x1000, 4096)
        cls.reference_regs = r

    def assert_native_sub(self, result, initial, subtract, flags):
        # Execute the independent native ISA instruction, rather than compute
        # x86 arithmetic/flags in Python or reuse the adapter's flag merge.
        r = self.reference_regs
        self.reference.mem_write(0x1000, bytes((0x83,0xE8,subtract)))
        self.reference.reg_write(r.UC_X86_REG_EAX, initial & 0xFFFFFFFF)
        self.reference.reg_write(r.UC_X86_REG_EFLAGS, flags)
        self.reference.emu_start(0x1000,0x1003,count=1)
        self.assertEqual(result["EAX"],self.reference.reg_read(r.UC_X86_REG_EAX))
        self.assertEqual(result["EFLAGS"],self.reference.reg_read(r.UC_X86_REG_EFLAGS))

    def test_all_nine_presets_boundary_native_and_all_arenas_at_two_bases(self):
        for width,height,capacity in CASES:
            for delta in (0,0x02000000):
                machine = Machine(self.tools,width,height,delta)
                for columns in range(1,21):
                    for name in ("attacker_right","defender_right"):
                        for flags in (0x202,0xED7):
                            with self.subTest(resolution=(width,height),delta=delta,
                                              columns=columns,side=name,flags=flags):
                                result=machine.execute(name,columns=columns,player=columns%5,flags=flags)
                                self.assert_native_sub(result,columns,min(columns,capacity),flags)
                                self.assertEqual(result["EAX"],max(0,columns-capacity))

    def test_exact_one_admission_precedes_every_state_read(self):
        for delta in (0,0x02000000):
            machine=Machine(self.tools,delta=delta)
            for name in module.SITES:
                for admission in (0,2,0xFFFFFFFF):
                    for eax in (0,1,20,0x80000000,0xFFFFFFFF):
                        result=machine.execute(name,admission=admission,eax=eax,pointer=0,flags=0xED7)
                        self.assert_native_sub(result,eax,7,0xED7)
                        self.assertEqual(machine.heap_reads,[])

    def test_owner_pointer_bounds_and_alignment_reject_before_state_read(self):
        for delta in (0,0x02000000):
            machine=Machine(self.tools,delta=delta)
            for name in module.SITES:
                for kwargs in (dict(owner=0),dict(pointer=0),dict(pointer=0xFFFF),
                               dict(pointer=Machine.HEAP+1),dict(pointer=0x7FFFF088)):
                    result=machine.execute(name,**kwargs,flags=0xED7)
                    self.assert_native_sub(result,20,7,0xED7)
                    self.assertEqual(machine.heap_reads,[])

    def test_invalid_dimensions_y_players_or_stale_loaded_width_replay_native(self):
        for delta in (0,0x02000000):
            machine=Machine(self.tools,delta=delta)
            for name in module.SITES:
                for kwargs in (dict(rows=6),dict(rows=8),dict(y=-1),dict(y=1),
                               dict(player=-1),dict(player=5),dict(columns=0),dict(columns=21),
                               dict(eax=19),dict(eax=0x80000000)):
                    result=machine.execute(name,**kwargs,flags=0xED7)
                    self.assert_native_sub(result,kwargs.get("eax",kwargs.get("columns",20)),7,0xED7)


def main(argv=None):
    global SOURCE_EXE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolchain-path",type=Path)
    parser.add_argument("--source-exe",type=Path)
    parser.add_argument("--require-machine-tools",action="store_true")
    args=parser.parse_args(argv)
    if args.toolchain_path: sys.path.insert(0,str(args.toolchain_path.resolve()))
    SOURCE_EXE=args.source_exe
    if args.require_machine_tools:
        try: machine_tools()
        except ImportError as error:
            print(str(error),file=sys.stderr); return 2
    result=unittest.TextTestRunner(verbosity=2).run(
        unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c)
                           for c in (SourceTests,CPUTests)))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
