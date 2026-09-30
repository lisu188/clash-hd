#!/usr/bin/env python3
"""Execute the authenticated native mouse poll in 32 KiB of artificial memory.

Only GetDeviceState and Acquire are modeled; their x86 stubs use real stdcall
returns. No executable, game, Windows API, builder or output file is used.
These CPU contracts do not prove acquisition, physical input or gameplay.
"""
import argparse
from contextlib import redirect_stderr
import hashlib
import io
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

import ordinary_map_phase_host as host

PINNED_SHA256 = 'a14789c5b210ada15278f2f6bd1d08864244f7280b662eb54127383e79aa9074'
POLL, CALL, RETURN, COPY, COPY_END = 0x47BFD0, 0x47C029, 0x47C02C, 0x47C03C, 0x47C065
NOTACQUIRED, INPUTLOST = 0x8007000C, 0x8007001E
REQUIRE_MACHINE = False
REGISTERS = ('EAX', 'EBX', 'ECX', 'EDX', 'ESI', 'EDI', 'EBP', 'ESP', 'EFLAGS', 'EIP')


def authenticated_body():
    body = bytes.fromhex(host.MOUSE_NATIVE_BYTES)
    if (len(body) != 154 or hashlib.sha256(body).hexdigest() != PINNED_SHA256
            or host.MOUSE_NATIVE_SHA256 != PINNED_SHA256):
        raise ValueError('native mouse poll bytes or SHA-256 differ')
    return body


def machine_tools():
    """Validate the specific Unicorn API before accepting a required CPU lane."""
    try:
        import unicorn
        from unicorn import x86_const
        names = ('UC_ARCH_X86', 'UC_MODE_32', 'UC_HOOK_CODE', 'UC_HOOK_MEM_WRITE',
                 'UC_PROT_READ', 'UC_PROT_WRITE', 'UC_PROT_EXEC')
        if (not callable(unicorn.Uc)
                or not all(type(getattr(unicorn, name)) is int for name in names)
                or not all(type(getattr(x86_const, 'UC_X86_REG_' + name)) is int
                           for name in REGISTERS)
                or not all(callable(getattr(unicorn.Uc, name)) for name in
                           ('mem_map', 'mem_write', 'mem_read', 'mem_protect',
                            'reg_write', 'reg_read', 'hook_add', 'emu_start', 'emu_stop'))):
            raise ImportError('Unicorn x86 API differs')
    except (ImportError, AttributeError, OSError) as error:
        raise ImportError('Unicorn x86 API unavailable') from error
    return unicorn, x86_const


class Machine:
    CODE, BACKEND_PAGE, BACKEND = 0x47B000, 0x545000, 0x545198
    DEPENDENCIES, DEVICE, VTABLE = 0x10000000, 0x10000100, 0x10001100
    GET_STATE, ACQUIRE, STOP = 0x10002100, 0x10002200, 0x10003100
    STACK, ENTRY = 0x20000000, 0x20000F00
    FRAME, BUFFER = ENTRY - 0x6C, ENTRY - 0x1C
    STALE = struct.pack('<iii4B', 0x11223344, -0x01020304, 0x55667788,
                        0x95, 0x97, 0x06, 0xF1)
    FRESH = struct.pack('<iii4B', -17, 23, 0x13579BDF, 0x82, 0xA4, 0x56, 0xF3)
    SAVED = dict(EBX=0x12345678, ECX=0x23456789, EDX=0x3456789A,
                 ESI=0x456789AB, EDI=0x56789ABC, EBP=0x6789ABCD)

    def __init__(self, tools, *, read_result=0, acquire_result=0, mouse=True, flags=0x202):
        unicorn, registers = tools
        self.uc = unicorn.Uc(unicorn.UC_ARCH_X86, unicorn.UC_MODE_32)
        self.regs = {name: getattr(registers, 'UC_X86_REG_' + name) for name in REGISTERS}
        self.read_result, self.acquire_result = read_result, acquire_result
        self.mouse, self.flags = mouse, flags
        self.calls, self.writes, self.samples = [], [], {}
        self.instructions, self.returned = 0, False
        for address, size in ((self.CODE, 0x2000), (self.BACKEND_PAGE, 0x1000),
                              (self.DEPENDENCIES, 0x4000), (self.STACK, 0x1000)):
            self.uc.mem_map(address, size, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
        self.uc.mem_write(self.CODE, b'\xCC' * 0x2000)
        self.uc.mem_write(POLL, authenticated_body())
        self.uc.mem_write(self.BACKEND_PAGE, b'\xA5' * 0x1000)
        self.uc.mem_write(self.STACK, b'\xB6' * 0x1000)
        self.word(self.BACKEND + 8, self.DEVICE)
        for offset, value in ((0x134, int(mouse)), (0x138, 0), (0x13C, 0)):
            self.word(self.BACKEND + offset, value)
        self.word(self.DEVICE, self.VTABLE)
        self.word(self.VTABLE + 0x24, self.GET_STATE)
        self.word(self.VTABLE + 0x1C, self.ACQUIRE)
        # Volatile COM registers change; the native function must restore its saves.
        for address, result, cleanup in ((self.GET_STATE, read_result, 12),
                                         (self.ACQUIRE, acquire_result, 4)):
            stub = (b'\xB9' + struct.pack('<I', 0x76543210)
                    + b'\xBA' + struct.pack('<I', 0x65432109)
                    + b'\xB8' + struct.pack('<I', result) + b'\xC2' + struct.pack('<H', cleanup))
            self.uc.mem_write(address, stub)
        self.uc.mem_write(self.STOP, b'\x90')
        self.word(self.ENTRY, self.STOP)
        self.uc.mem_write(self.BUFFER, self.STALE)
        for name, value in dict(self.SAVED, EAX=self.BACKEND, ESP=self.ENTRY,
                               EFLAGS=flags).items():
            self.uc.reg_write(self.regs[name], value)
        self.before = {address: bytes(self.uc.mem_read(address, size)) for address, size in
                       ((self.CODE, 0x2000), (self.BACKEND_PAGE, 0x1000),
                        (self.DEPENDENCIES, 0x4000), (self.STACK, 0x1000))}
        for address, size in ((self.CODE, 0x2000), (self.DEPENDENCIES, 0x4000)):
            self.uc.mem_protect(address, size, unicorn.UC_PROT_READ | unicorn.UC_PROT_EXEC)
        self.uc.hook_add(unicorn.UC_HOOK_CODE, self.code)
        self.uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, self.write)

    def reg(self, name):
        return self.uc.reg_read(self.regs[name])

    def word(self, address, value=None):
        if value is not None:
            self.uc.mem_write(address, struct.pack('<I', value))
        return struct.unpack('<I', self.uc.mem_read(address, 4))[0]

    def code(self, uc, address, size, _data):
        self.instructions += 1
        if address == self.STOP:
            self.returned = True
            uc.emu_stop()
            return
        if not (POLL <= address < POLL + 154 or self.GET_STATE <= address < self.GET_STATE + 18
                or self.ACQUIRE <= address < self.ACQUIRE + 18):
            raise AssertionError(f'execution escaped modeled poll: {address:08x}')
        if address == CALL:
            if (self.reg('ESP') != self.FRAME - 12
                    or tuple(self.word(self.FRAME - 12 + n) for n in (0, 4, 8))
                    != (self.DEVICE, 16, self.BUFFER)):
                raise AssertionError('native GetDeviceState call stack differs')
            self.samples['pre'] = bytes(uc.mem_read(self.BUFFER, 16))
        elif address in (self.GET_STATE, self.ACQUIRE):
            get_state = address == self.GET_STATE
            esp, count = self.reg('ESP'), 3 if get_state else 1
            return_va = RETURN if get_state else COPY
            args = tuple(self.word(esp + 4 + n * 4) for n in range(count))
            expected = (self.DEVICE, 16, self.BUFFER) if get_state else (self.DEVICE,)
            if (esp != self.FRAME - (16 if get_state else 8)
                    or self.word(esp) != return_va or args != expected):
                raise AssertionError('COM arguments or native CALL return differ')
            self.calls.append((address, esp, return_va, args))
            if get_state and self.read_result == 0:
                # Only the successful modeled dependency fills the 16-byte packet.
                uc.mem_write(self.BUFFER, self.FRESH)
        elif address == RETURN:
            self.samples['read'] = (self.reg('EAX'), self.reg('ESP'),
                                    bytes(uc.mem_read(self.BUFFER, 16)))
        elif address == COPY:
            self.samples['copy'] = (self.reg('EAX'), self.reg('ESP'))
        elif address == COPY_END:
            self.samples['copy_end_esp'] = self.reg('ESP')

    def write(self, _uc, _access, address, size, value, _data):
        pc = self.reg('EIP')
        if not (POLL <= pc < POLL + 154 and size == 4
                and (self.FRAME - 16 <= address <= self.ENTRY - 4
                     or address in {self.BACKEND + n for n in (0x10, 0x14, 0x28, 0x30, 0x2C)})):
            raise AssertionError(f'unexpected native write: {pc:08x} {address:08x}+{size}')
        self.writes.append((pc, address, size, value & 0xFFFFFFFF))

    def run(self):
        self.uc.emu_start(POLL, self.STOP + 1, count=128)
        if not self.returned:
            raise AssertionError('native poll did not return within 128 instructions')
        return self


class PortableTests(unittest.TestCase):
    def test_independent_sha_and_instruction_pins_fail_closed(self):
        body = authenticated_body()
        pins = {POLL: '53515283ec6089c383', CALL: 'ff5124',
                RETURN: '3d1e00078075098b4308508b10ff521c',
                COPY: '8b4424508943108b44245489431431c08a44245c89432831c08a44245d89433031c08a44245e89432c',
                COPY_END: 'e977ffffff'}
        for va, expected in pins.items():
            self.assertEqual(body[va - POLL:va - POLL + len(expected) // 2].hex(), expected)
        for changed in ((b'\x90' + body[1:]).hex(), body[:-1].hex()):
            with self.subTest(changed=changed[:20]), patch.object(host, 'MOUSE_NATIVE_BYTES', changed):
                with self.assertRaisesRegex(ValueError, 'bytes or SHA-256'): authenticated_body()
        with patch.object(host, 'MOUSE_NATIVE_SHA256', '0' * 64):
            with self.assertRaisesRegex(ValueError, 'bytes or SHA-256'): authenticated_body()

    def test_required_missing_machine_tools_fail_before_running_suite(self):
        errors = io.StringIO()
        with patch(__name__ + '.machine_tools', side_effect=ImportError('missing')) as dependency, \
                patch.object(unittest, 'TextTestRunner') as runner, redirect_stderr(errors):
            with self.assertRaises(SystemExit) as failure: main(['--require-machine-tools', '-v'])
        self.assertEqual(failure.exception.code, 2)
        self.assertIn('--require-machine-tools requires the Unicorn x86 API', errors.getvalue())
        dependency.assert_called_once_with()
        runner.assert_not_called()

    def test_missing_toolchain_fails_before_import_or_running_suite(self):
        with patch.object(Path, 'is_dir', return_value=False), \
                patch(__name__ + '.machine_tools') as dependency, \
                patch.object(unittest, 'TextTestRunner') as runner, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as failure: main(['--toolchain', 'missing-toolchain'])
        self.assertEqual(failure.exception.code, 2)
        dependency.assert_not_called()
        runner.assert_not_called()


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.tools = machine_tools()
        except ImportError as error:
            if REQUIRE_MACHINE: raise AssertionError('required Unicorn unavailable') from error
            raise unittest.SkipTest('Unicorn unavailable; use --toolchain or --require-machine-tools')

    def check_poll(self, *, read_result=0, acquire_result=0, mouse=True):
        for flags in (0x202, 0x602):
            with self.subTest(flags=hex(flags)):
                m = Machine(self.tools, read_result=read_result, acquire_result=acquire_result,
                            mouse=mouse, flags=flags).run()
                acquire = mouse and read_result == INPUTLOST
                packet = m.FRESH if mouse and read_result == 0 else m.STALE
                self.assertEqual([row[0] for row in m.calls],
                                 ([m.GET_STATE] + ([m.ACQUIRE] if acquire else [])) if mouse else [])
                self.assertEqual(bytes(m.uc.mem_read(m.BUFFER, 16)), packet)
                if mouse:
                    self.assertEqual(m.samples['pre'], m.STALE)
                    self.assertEqual(m.samples['read'], (read_result, m.FRAME, packet))
                    self.assertEqual(m.samples['copy'],
                                     (acquire_result if acquire else read_result, m.FRAME))
                    self.assertEqual(m.samples['copy_end_esp'], m.FRAME)
                else:
                    self.assertEqual(m.samples, {})
                # Native stores are DWORDs: x/y, then primary/secondary/middle.
                words = (int.from_bytes(packet[:4], 'little'), int.from_bytes(packet[4:8], 'little'),
                         packet[12], packet[13], packet[14])
                copies = [(pc, m.BACKEND + offset, 4, value) for pc, offset, value in zip(
                    (0x47C040, 0x47C047, 0x47C050, 0x47C059, 0x47C062),
                    (0x10, 0x14, 0x28, 0x30, 0x2C), words)] if mouse else []
                self.assertEqual([row for row in m.writes if row[1] >= m.BACKEND_PAGE
                                  and row[1] < m.BACKEND_PAGE + 0x1000], copies)
                stack = [(POLL, m.ENTRY - 4, 4, m.SAVED['EBX']),
                         (POLL + 1, m.ENTRY - 8, 4, m.SAVED['ECX']),
                         (POLL + 2, m.ENTRY - 12, 4, m.SAVED['EDX'])]
                if mouse:
                    stack += [(0x47C020, m.FRAME - 4, 4, m.BUFFER),
                              (0x47C024, m.FRAME - 8, 4, 16),
                              (0x47C028, m.FRAME - 12, 4, m.DEVICE),
                              (CALL, m.FRAME - 16, 4, RETURN)]
                if acquire:
                    stack += [(0x47C036, m.FRAME - 4, 4, m.DEVICE),
                              (0x47C039, m.FRAME - 8, 4, COPY)]
                self.assertEqual([row for row in m.writes if m.STACK <= row[1] < m.STACK + 0x1000], stack)
                # Compare every mapped byte, accounting separately for the modeled fill.
                for address, before in m.before.items():
                    expected = bytearray(before)
                    for _pc, target, size, value in m.writes:
                        if address <= target < address + len(before):
                            expected[target - address:target - address + size] = value.to_bytes(size, 'little')
                    if address == m.STACK:
                        expected[m.BUFFER - address:m.BUFFER - address + 16] = packet
                    self.assertEqual(bytes(m.uc.mem_read(address, len(before))), bytes(expected))
                for name, value in m.SAVED.items(): self.assertEqual(m.reg(name), value, name)
                self.assertEqual(m.reg('ESP'), m.ENTRY + 4)
                self.assertEqual(m.reg('EIP'), m.STOP)
                self.assertEqual(m.reg('EFLAGS') & 0x400, flags & 0x400)
                self.assertEqual(m.reg('EAX'), packet[14] if mouse else m.BACKEND)
                self.assertLessEqual(m.instructions, 128)

    def test_success_reads_once_and_copies_packet(self):
        self.check_poll()

    def test_notacquired_copies_unchanged_nonzero_packet_without_acquire(self):
        self.check_poll(read_result=NOTACQUIRED)

    def test_inputlost_acquire_success_still_copies_without_read_retry(self):
        self.check_poll(read_result=INPUTLOST, acquire_result=0)

    def test_inputlost_acquire_failure_still_copies_without_read_retry(self):
        self.check_poll(read_result=INPUTLOST, acquire_result=0x80070005)

    def test_disabled_mouse_keeps_backend_and_packet_without_com_calls(self):
        self.check_poll(mouse=False)


def main(argv=None):
    global REQUIRE_MACHINE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--toolchain', type=Path)
    parser.add_argument('--require-machine-tools', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args(argv)
    if args.toolchain is not None:
        toolchain = args.toolchain.resolve()
        if not toolchain.is_dir(): parser.error('--toolchain must be an existing directory')
        sys.path.insert(0, str(toolchain))
    if args.require_machine_tools:
        try: machine_tools()
        except ImportError: parser.error('--require-machine-tools requires the Unicorn x86 API')
    REQUIRE_MACHINE = args.require_machine_tools
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
                               for cls in (PortableTests, CPUTests))
    result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
    return 0 if result.wasSuccessful() and not (args.require_machine_tools and result.skipped) else 1


if __name__ == '__main__':
    raise SystemExit(main())
