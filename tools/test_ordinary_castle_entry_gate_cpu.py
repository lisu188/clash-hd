#!/usr/bin/env python3
"""Synthetic x86 gate execution; no original EXE, PE builds, game or debugger.

Executes the exact-1024 and matrix gate emitters with independent caller-frame
fixtures. This tests the gate's accept/reject and preservation ABI only. It
does not execute the inherited canvas, allocation, rendering or exit lifecycle.
Use --require-machine-tools in CI; an unavailable or namespace-only Unicorn
import must not turn a required machine run into a skipped success.
"""
from __future__ import annotations

import argparse
from importlib import import_module
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]
from src.patcher import ordinary_castle_entry as exact
from src.patcher import ordinary_castle_entry_matrix as matrix

MACHINE_TOOLS = None
PASSED_CASES = 0
REGISTERS = ('EAX', 'EBX', 'ECX', 'EDX', 'ESI', 'EDI', 'EBP', 'ESP', 'EFLAGS')


def load_machine_tools(toolchain=None):
    if toolchain is not None:
        sys.path.insert(0, str(Path(toolchain).resolve()))
    try:
        module = import_module('unicorn')
        x86 = import_module('unicorn.x86_const')
        # Checking only `import unicorn` accepts a directory that the sandbox
        # cannot actually read, because Python constructs an empty namespace.
        if not callable(getattr(module, 'Uc', None)):
            raise ImportError('Unicorn Uc API is unavailable')
        for name in ('UC_ARCH_X86', 'UC_MODE_32', 'UC_HOOK_CODE', 'UC_HOOK_MEM_WRITE'):
            if type(getattr(module, name, None)) is not int:
                raise ImportError('Unicorn API constant unavailable: '+name)
        for name in REGISTERS:
            if type(getattr(x86, 'UC_X86_REG_'+name, None)) is not int:
                raise ImportError('Unicorn x86 register unavailable: '+name)
    except (ImportError, OSError, AttributeError) as error:
        raise RuntimeError('Usable Unicorn Uc/x86_const required: '+str(error)) from error
    return module, x86


def contexts():
    """Independent ABI addresses; the matrix gets two distinct caller layouts."""
    yield dict(name='exact-1024', gate=0x647B74, accept=0x57607B,
               reject=0x576230, wrapper_return=0x5767A9,
               code=exact.emit_gate()[0])
    for gate in (0x648000, 0x780000):
        for entry in (0x576000, 0x5B6000):
            admission = matrix.Admission(entry, entry+0x79E, entry+0x7A9,
                entry+0x6B, entry+0x75, entry+0x7B, entry+0x230, entry+0x20000)
            yield dict(name=f'matrix-{gate:x}-{entry:x}', gate=gate,
                       accept=entry+0x7B, reject=entry+0x230,
                       wrapper_return=entry+0x7A9,
                       code=matrix.emit_gate(gate, admission)[0])


class DependencyTests(unittest.TestCase):
    def test_empty_namespace_does_not_satisfy_required_machine_api(self):
        with patch(__name__+'.import_module', return_value=SimpleNamespace()), \
                self.assertRaisesRegex(RuntimeError, 'Unicorn Uc API'):
            load_machine_tools()

    def test_missing_register_api_is_not_a_usable_engine(self):
        module = SimpleNamespace(Uc=lambda:None, UC_ARCH_X86=1, UC_MODE_32=2,
                                 UC_HOOK_CODE=4, UC_HOOK_MEM_WRITE=8)
        with patch(__name__+'.import_module', side_effect=[module, SimpleNamespace()]), \
                self.assertRaisesRegex(RuntimeError, 'x86 register'):
            load_machine_tools()


class GateCpuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global MACHINE_TOOLS
        if MACHINE_TOOLS is None:
            try:
                MACHINE_TOOLS = load_machine_tools()
            except RuntimeError as error:
                raise unittest.SkipTest(str(error)+'; use --toolchain and --require-machine-tools') from error
        cls.uc, cls.x86 = MACHINE_TOOLS

    def execute_case(self, layout, delta, case, flags):
        global PASSED_CASES
        uc, x86 = self.uc, self.x86
        emu = uc.Uc(uc.UC_ARCH_X86, uc.UC_MODE_32)
        emu.mem_map(0x400000+delta, 0x400000)
        emu.mem_map(0x1000000, 0x3000)
        emu.mem_write(layout['gate']+delta, layout['code'])
        root_sp = 0x1001800
        gate_sp = root_sp-76
        def put(address, value):
            emu.mem_write(address, struct.pack('<I', value))
        values = [root_sp, 0x22334455, 0x33445566, 0x44556677,
                  0x55667788, 0x66778899, 0x778899AA, gate_sp, flags]
        if case == 'root_argument':
            values[0] += 4
        registers = [getattr(x86, 'UC_X86_REG_'+name) for name in REGISTERS]
        for register, value in zip(registers, values):
            emu.reg_write(register, value)
        owner = 0x40AD40 if case == 'map_compat' else 0x422020 if case == 'owner' else 0x4617A0
        put(0x5199D8+delta, owner+delta)
        # R is the native castle-root entry ESP. These offsets follow the two
        # enclosing pushfd/pushad frames, independently of emitted operands.
        put(root_sp-60, 0x12345678 if case in ('root_ebx', 'map_compat') else 0x40AD40+delta)
        put(root_sp-72, 0x87654321 if case in ('root_esi', 'map_compat') else 0x4617A0+delta)
        put(root_sp-40, 0x12340000 if case in ('wrapper_return', 'map_compat') else layout['wrapper_return']+delta)
        put(root_sp, 0x12340000 if case in ('root_return', 'map_compat') else 0x41ED6F+delta)
        owner_before = bytes(emu.mem_read(0x5199D8+delta, 4))
        caller_before = bytes(emu.mem_read(gate_sp, 256))
        registers_before = [emu.reg_read(register) for register in registers]
        visited, writes = [], []
        def reached(machine, address, size, data):
            if address in (layout['accept']+delta, layout['reject']+delta):
                visited.append(address)
                machine.emu_stop()
        def wrote(machine, access, address, size, value, data):
            writes.append((address, size))
        emu.hook_add(uc.UC_HOOK_CODE, reached)
        emu.hook_add(uc.UC_HOOK_MEM_WRITE, wrote)
        emu.emu_start(layout['gate']+delta, 0, count=100)
        expected = layout['accept'] if case in ('native', 'map_compat') else layout['reject']
        self.assertEqual(visited, [expected+delta], 'gate did not reach the correct original continuation')
        self.assertEqual([emu.reg_read(register) for register in registers], registers_before,
                         'GPR/EFLAGS/ESP preservation failure')
        self.assertEqual(bytes(emu.mem_read(gate_sp, 256)), caller_before, 'caller stack changed')
        self.assertEqual(bytes(emu.mem_read(0x5199D8+delta, 4)), owner_before, 'owner value changed')
        self.assertTrue(all(gate_sp-40 <= address and address+size <= gate_sp for address, size in writes),
                        'write escaped temporary pushfd/pushad/call stack space')
        if case == 'map_compat':
            self.assertEqual(writes, [], 'ordinary-map fast path performed a write')
        PASSED_CASES += 1

    def check_context(self, case):
        flag_patterns = (0x246, 0xED7) if case == 'map_compat' else (0x202, 0xE97)
        for layout in contexts():
            for delta in (0, 0x100000):
                for flags in flag_patterns:
                    with self.subTest(emitter=layout['name'], relocation=hex(delta), flags=hex(flags), context=case):
                        self.execute_case(layout, delta, case, flags)

    def test_authenticated_native_caller_is_accepted(self):
        self.check_context('native')

    def test_original_map_condition_accepts_without_native_frame(self):
        self.check_context('map_compat')

    def test_wrong_live_owner_rejects(self):
        self.check_context('owner')

    def test_wrong_saved_ordinary_owner_rejects(self):
        self.check_context('root_ebx')

    def test_wrong_saved_native_esi_rejects(self):
        self.check_context('root_esi')

    def test_wrong_try_enter_caller_rejects(self):
        self.check_context('wrapper_return')

    def test_wrong_root_stack_argument_rejects(self):
        self.check_context('root_argument')

    def test_wrong_native_root_return_rejects(self):
        self.check_context('root_return')


def main():
    global MACHINE_TOOLS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--toolchain', type=Path)
    parser.add_argument('--require-machine-tools', action='store_true')
    args, remaining = parser.parse_known_args()
    if args.toolchain or args.require_machine_tools:
        try:
            MACHINE_TOOLS = load_machine_tools(args.toolchain)
        except RuntimeError as error:
            if args.require_machine_tools:
                parser.error(str(error))
    result = unittest.main(argv=[sys.argv[0], *remaining], exit=False).result
    print(f'GATE_CPU cases_passed={PASSED_CASES} scope=gate_emitter_only original_backed=0 game_runtime=0 lifecycle=0')
    return int(not result.wasSuccessful())


if __name__ == '__main__':
    raise SystemExit(main())
