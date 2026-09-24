"""Source-only and native-i386 fixtures; the owner validator is a labeled stub.

The emitted guards execute on the CPU, not a Python instruction emulator.
No game, debugger, wrapper, input injection, or runtime capture is used.
"""
from dataclasses import replace
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher import framed_modal_widget_bounds as tool
from src.patcher import partial_tile_clip as clip

BASE = 0x20000000
CODE = BASE + 0xE0000
OWNER = BASE + 0xE1000
DATA = BASE + 0x100000
STATE = DATA + 0x1000
DESCRIPTOR = DATA + 0x2000
OUTPUT = DATA + 0x3000
MASK = 0xCD5
MODES = {
    'ordinary_hd': (0, 0, 0, DATA + 0x400, 1),
    'native_modal': (1, 0, DATA + 0x500, DATA + 0x500, 1),
    'primary_during_modal': (1, 0, DATA + 0x500, DATA + 0x400, 1),
    'foreign_target': (1, 0, DATA + 0x500, DATA + 0x600, 1),
    'missing_native': (1, 0, 0, 0, 1),
    'inactive_owned_target': (0, 0, DATA + 0x500, DATA + 0x500, 1),
    'faulted_owned_target': (1, 7, DATA + 0x500, DATA + 0x500, 1),
    'invalid_owned_target': (1, 0, DATA + 0x500, DATA + 0x500, 0),
}
CSHARP = r'''
using System;
using System.IO;
using System.Runtime.InteropServices;
class Fixture {
 [DllImport("kernel32")] static extern IntPtr VirtualAlloc(IntPtr p,UIntPtr n,uint a,uint b);
 [DllImport("kernel32")] static extern bool VirtualProtect(IntPtr p,UIntPtr n,uint a,out uint old);
 [DllImport("kernel32")] static extern bool VirtualFree(IntPtr p,UIntPtr n,uint a);
 [DllImport("kernel32")] static extern IntPtr GetCurrentProcess();
 [DllImport("kernel32")] static extern bool FlushInstructionCache(IntPtr p,IntPtr a,UIntPtr n);
 [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int Entry();
 static int Main(string[] args) {
  IntPtr block=VirtualAlloc((IntPtr)0x20000000,(UIntPtr)0x200000,0x3000,4);
  if(block!=(IntPtr)0x20000000) throw new Exception("Fixture allocation unavailable");
  try {
   byte[] bytes=File.ReadAllBytes(args[0]);
   if(bytes.Length!=0x100000) throw new Exception("Fixture code extent differs");
   Marshal.Copy(bytes,0,block,bytes.Length);
   uint old;
   if(!VirtualProtect(block,(UIntPtr)0x100000,0x20,out old) ||
      !FlushInstructionCache(GetCurrentProcess(),block,(UIntPtr)0x100000)) throw new Exception("Fixture RX setup failed");
   int rc=((Entry)Marshal.GetDelegateForFunctionPointer((IntPtr)0x20001000,typeof(Entry)))();
   byte[] output=new byte[int.Parse(args[1])];Marshal.Copy((IntPtr)0x20103000,output,0,output.Length);
   Console.OpenStandardOutput().Write(output,0,output.Length);return rc;
  } finally { if(!VirtualFree(block,UIntPtr.Zero,0x8000)) throw new Exception("Fixture cleanup failed"); }
 }
}
'''


def comparison_flags(left, right, direction):
    left &= 0xFFFFFFFF; right &= 0xFFFFFFFF
    value = (left - right) & 0xFFFFFFFF
    return (int(left < right) | (int((value & 255).bit_count() % 2 == 0) << 2)
            | ((left ^ right ^ value) & 16) | (int(value == 0) << 6) | ((value >> 24) & 128)
            | (int(bool((left ^ right) & (left ^ value) & 0x80000000)) << 11) | direction)


def bundle(width=1024, height=768, prefixes=(b'\x81\x38', b'\x81\x3b')):
    return tool._emit_guards(base_va=CODE, state_va=STATE, owner_va=OWNER, width=width, height=height,
        comparisons={name: prefix + struct.pack('<I', width) for name, prefix in zip(('single', 'list'), prefixes)})


def program(cases, width, height, *, prefixes=(b'\x81\x38', b'\x81\x3b'), legacy=False):
    generated = bundle(width, height, prefixes)
    code = bytearray(generated.code)
    for row in generated.relocations:
        if row.target == tool.modal.RENDER:
            struct.pack_into('<I', code, row.offset, DATA)
    entries = dict(generated.entries)
    if legacy:
        code = bytearray()
        for name, prefix in zip(('single', 'list'), prefixes):
            entries[name] = CODE + len(code)
            code.extend(prefix + struct.pack('<I', width) + b'\xc3')
    body = clip._Assembler(BASE + 0x1000)
    body.emit('9c60')
    seeds = []
    for number, (name, x, mode, flags) in enumerate(cases):
        phase, fault, native, render, valid = MODES[mode]
        for address, value in ((STATE, phase), (STATE + 8, native), (STATE + 36, fault),
                               (DATA, render), (DATA + 4, valid), (DATA + 8, 0), (DESCRIPTOR, x)):
            body.emit('c705'); body.u32(address); body.u32(value)
        values = [0x11223344, 0x22334455, 0x33445566, 0x44556677, 0, 0x55667788, 0x66778899, 0x778899AA]
        values[prefixes[('single', 'list').index(name)][1] & 7] = DESCRIPTOR
        seeds.append(values)
        for register, value in enumerate(values):
            if register != 4: body.emit(f'{0xb8 + register:02x}'); body.u32(value)
        out = OUTPUT + number * 64
        body.emit('8925'); body.u32(out + 36)
        body.emit('68'); body.u32(flags); body.emit('9d')
        body.emit('e8'); body.u32(entries[name] - body.base - len(body.code) - 4); body.emit('90')
        body.emit('9c8f05'); body.u32(out + 32)
        for register in range(8):
            body.emit('89' + f'{5 + (register << 3):02x}'); body.u32(out + register * 4)
        for address, target in ((STATE + 36, out + 40), (DATA + 8, out + 44), (DESCRIPTOR, out + 48),
                                (STATE, out + 52), (DATA, out + 56), (STATE + 8, out + 60)):
            body.emit('a1'); body.u32(address); body.emit('a3'); body.u32(target)
    body.emit('619d31c0c3')
    driver = body.finish()
    if len(driver) >= CODE - body.base: raise AssertionError('fixture driver overlaps guard')
    owner = clip._Assembler(OWNER)
    owner.emit('ff05'); owner.u32(DATA + 8)
    owner.emit('a1'); owner.u32(DATA + 4)
    owner.emit('85c0'); owner.branch('0f85', 'good')
    owner.emit('c705'); owner.u32(STATE + 36); owner.u32(4)
    owner.label('good')
    for register in (1, 2, 3, 5, 6, 7): owner.emit(f'{0xb8 + register:02x}'); owner.u32(0xDEADBEEF)
    owner.emit('c3')
    result = bytearray(0x100000)
    result[0x1000:0x1000 + len(driver)] = driver
    result[CODE - BASE:CODE - BASE + len(code)] = code
    owner_code = owner.finish(); result[OWNER - BASE:OWNER - BASE + len(owner_code)] = owner_code
    return bytes(result), seeds


def elf(code, output_size):
    image = bytearray(code)
    image[:16] = b'\x7fELF\x01\x01\x01' + bytes(9)
    struct.pack_into('<HHIIIIIHHHHHH', image, 16, 2, 3, 1, BASE + 0x100, 52, 0, 0, 52, 32, 2, 0, 0, 0)
    struct.pack_into('<8I', image, 52, 1, 0, BASE, BASE, 0x100000, 0x100000, 5, 0x1000)
    struct.pack_into('<8I', image, 84, 1, 0x100000, DATA, DATA, 0, 0x100000, 6, 0x1000)
    start = clip._Assembler(BASE + 0x100)
    start.emit('e8'); start.u32(BASE + 0x1000 - start.base - len(start.code) - 4)
    start.emit('b804000000bb01000000b9'); start.u32(OUTPUT)
    start.emit('ba'); start.u32(output_size); start.emit('cd80b80100000031dbcd80')
    entry = start.finish(); image[0x100:0x100 + len(entry)] = entry
    return bytes(image)


class GuardSourceTests(unittest.TestCase):
    def test_deterministic_entries_and_checked_relocations(self):
        first = bundle(); second = bundle()
        self.assertEqual(first, second)
        self.assertEqual(set(first.entries), {'single', 'list'})
        self.assertFalse(first.installation_ready)
        self.assertEqual(sum(row.kind == 'rel32' for row in first.relocations), 2)
        self.assertEqual(len(clip.absolute_relocation_offsets(first)), 8)
        self.assertLess(len(first.code), 4096)
        self.assertTrue(first.code.startswith(b'\x60'))
        self.assertNotIn(b'\xfa', first.code)

    def test_unknown_instruction_shapes_addresses_and_types_are_rejected(self):
        good = dict(base_va=CODE, state_va=STATE, owner_va=OWNER, width=1024, height=768,
                    comparisons={'single': b'\x81\x38\x00\x04\x00\x00', 'list': b'\x81\x3b\x00\x04\x00\x00'})
        for changes in ({'width': True}, {'base_va': CODE + 1}, {'state_va': 0}, {'owner_va': -1},
                        {'comparisons': {}}, {'comparisons': {'single': b'\x81\x3c\x00\x04\x00\x00', 'list': good['comparisons']['list']}},
                        {'comparisons': {'single': b'\x81\x38\x80\x02\x00\x00', 'list': good['comparisons']['list']}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): tool._emit_guards(**(good | changes))

    def test_unknown_original_rejected_before_builder(self):
        from tools import build_framed_modal_primary_text_candidate as parent
        with patch.object(parent, 'build_candidate') as build, self.assertRaises(ValueError):
            tool.emit_widget_bounds(b'not the game', b'candidate', base_va=CODE, width=1024, height=768)
        build.assert_not_called()


class NativeGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='clash-widget-cpu-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.folder = Path(cls.temporary.name)
        cls.runner = None
        if os.name == 'nt':
            compiler = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Microsoft.NET/Framework/v4.0.30319/csc.exe'
            if not compiler.is_file(): raise unittest.SkipTest('x86 .NET compiler required')
            source = cls.folder / 'Fixture.cs'; source.write_text(CSHARP)
            cls.runner = cls.folder / 'Fixture.exe'
            result = subprocess.run([str(compiler), '/nologo', '/platform:x86', '/out:' + str(cls.runner), str(source)],
                                    capture_output=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode: raise AssertionError(result.stdout + result.stderr)
        elif sys.platform != 'linux' or platform.machine().lower() not in ('x86_64', 'amd64', 'i386', 'i686'):
            raise unittest.SkipTest('native i386 CPU fixture requires x86 Linux or Windows')

    def execute(self, cases, width=1024, height=768, **options):
        code, seeds = program(cases, width, height, **options)
        path = self.folder / 'fixture-input.bin'
        if self.runner:
            path.write_bytes(code)
            command = [str(self.runner), str(path), str(len(cases) * 64)]
            flags = {'creationflags': subprocess.CREATE_NO_WINDOW}
        else:
            path.write_bytes(elf(code, len(cases) * 64)); path.chmod(0o700)
            command = [str(path)]; flags = {}
        result = subprocess.run(command, capture_output=True, timeout=20, **flags)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout), len(cases) * 64)
        return list(struct.iter_unpack('<16I', result.stdout)), seeds

    def test_context_bounds_cpu_flags_all_registers_stack_and_fault_contract(self):
        for width, height in ((800, 600), (1024, 768), (1280, 720), (1280, 960), (1920, 1080), (802, 602)):
            cases = [(name, x, mode, flags) for name in ('single', 'list')
                     for x in (-2147483648, -1, 0, 639, 640, 999, 1000, width - 1, width, 2147483647)
                     for mode in MODES for flags in (0x202, 0xED7)]
            outputs, seeds = self.execute(cases, width, height)
            for case, row, seed in zip(cases, outputs, seeds):
                name, x, mode, flags = case
                phase, fault, native, render, valid = MODES[mode]
                owned = native != 0 and native == render
                rejected = owned and (phase != 1 or fault != 0 or not valid)
                expected = comparison_flags(x, x if rejected else 640 if owned else width, flags & 0x400)
                calls = int(owned and phase == 1 and fault == 0)
                seed[4] = row[9]
                with self.subTest(resolution=(width, height), case=case):
                    self.assertEqual(list(row[:8]), seed)
                    self.assertEqual(row[8] & MASK, expected)
                    self.assertEqual(row[10], 4 if calls and not valid else fault)
                    self.assertEqual(row[11], calls)
                    self.assertEqual(row[12:], (x & 0xFFFFFFFF, phase, render, native))

    def test_old_wide_comparison_admits_disabled_modal_sentinel_fixed_guard_does_not(self):
        cases = [(name, 1000, 'native_modal', 0x202) for name in ('single', 'list')]
        old, _ = self.execute(cases, legacy=True)
        new, _ = self.execute(cases)
        for previous, current in zip(old, new):
            self.assertEqual(((previous[8] >> 7) ^ (previous[8] >> 11)) & 1, 1)
            self.assertEqual(((current[8] >> 7) ^ (current[8] >> 11)) & 1, 0)

    def test_every_supported_native_memory_operand_register(self):
        for prefix in tool.CMP_PREFIXES:
            cases = [(name, x, mode, 0xED7) for name in ('single', 'list') for x in (639, 640, 1000)
                     for mode in ('ordinary_hd', 'native_modal')]
            outputs, seeds = self.execute(cases, prefixes=(prefix, prefix))
            for case, row, seed in zip(cases, outputs, seeds):
                seed[4] = row[9]
                with self.subTest(prefix=prefix.hex(), case=case):
                    self.assertEqual(list(row[:8]), seed)
                    self.assertEqual(row[8] & MASK, comparison_flags(case[1], 640 if case[2] == 'native_modal' else 1024, 0x400))


if __name__ == '__main__': unittest.main(verbosity=2)
