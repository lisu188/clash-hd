#!/usr/bin/env python3
"""Fresh 43-window authored CPU contracts, never original battle execution.

The public fixture runs authored post-return entry/scalar windows and modeled
Thread/outer helpers. It opens no original executable and installs no hooks.
Capstone independently decodes every new instruction/operand; Unicorn executes
the new adapters and a separate scalar baseline at two virtual load bases.
"""
from __future__ import annotations

from dataclasses import asdict, replace
import gc
import hashlib
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/"tools")]
from src.patcher import battle_profile_continuation_v2 as tool
import test_battle_profile_adjacent_unit_v2 as parent

CACHE = {}
ROWS, HIGHLOW = tool._ledger((ROOT/tool.LEDGER).read_bytes())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def arguments():
    supplied = parent.arguments()
    return dict(atomic_module=parent.tool, content_module=supplied["content_module"],
        template_module=supplied["template_module"], template_source=supplied["template_source"],
        ledger_source=(ROOT/tool.LEDGER).read_bytes(),
        loss_module=parent.replay_fixture.tile_fixture.loss_tool, assembler_module=parent.clip)


def emit(profile="classic", resolution="1920x1080"):
    key = profile, resolution
    if key not in CACHE:
        values = parent.emit(profile, resolution)
        out = tool._raw_emit(values[0], values[3], values[4], values[5], values[6], values[7],
            *values[-3:], **arguments())
        CACHE[key] = values, out
    return CACHE[key]


def source_closure():
    result = parent.source_closure()
    return result | {name: sha((ROOT/name).read_bytes()) for name in
        (tool.SOURCE, "tools/test_battle_profile_continuation_v2.py")}


def disassemble(out):
    import capstone
    decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    decoder.detail = True
    rows = tuple(decoder.disasm(out.code, out.base_va))
    assert sum(row.size for row in rows) == len(out.code)
    return rows


class Machine(parent.Machine):
    def __init__(self, tools, profile="classic", resolution="1920x1080", delta=0):
        hooks, removed = [], set()
        add0, del0 = tools[0].Uc.hook_add, tools[0].Uc.hook_del
        def add(cpu, kind, *args, **kwargs):
            handle = add0(cpu, kind, *args, **kwargs)
            hooks.append((kind, handle, args, kwargs))
            return handle
        def remove(cpu, handle):
            removed.add(handle)
            return del0(cpu, handle)
        with patch.object(tools[0].Uc, "hook_add", add), patch.object(tools[0].Uc, "hook_del", remove):
            super().__init__(tools, profile, resolution, delta)
        _, self.continuation = emit(profile, resolution)
        raw = bytearray(self.continuation.code)
        for row in self.continuation.relocations:
            if row.kind == "abs32":
                struct.pack_into("<I", raw, row.offset, row.target+delta)
        self.cpu.mem_write(self.continuation.base_va+delta, bytes(raw))
        self.loaded_code.append((self.continuation.base_va+delta, bytes(raw)))
        self.unsafe_vas.update(va+delta for name, va in self.continuation.private_entries if "unsafe" in name)
        self.post_planned = {va: (old, target) for va, old, target, _, _ in self.continuation.planned_hooks}
        self.tail_receipts = []
        self.pending_tail = None
        self.tail_entries = {wrapper+delta: (pc+5+delta, loss_target+delta)
            for (_, pc, _, wrapper), (_, _, _, loss_target) in zip(self.continuation.field_call_patches,
                emit(profile, resolution)[0][6].field_call_patches)}
        excluded = []
        for instruction in disassemble(self.continuation):
            if bytes(instruction.bytes) != b"\xf3\xaf":
                continue
            at = instruction.address-self.continuation.base_va
            assert self.continuation.code[at-10] == 0xb9 and self.continuation.code[at-5] == 0xbf
            count = struct.unpack_from("<I", self.continuation.code, at-9)[0]
            pointer = struct.unpack_from("<I", self.continuation.code, at-4)[0]+delta
            pc = instruction.address+delta
            self.scan_before[pc-5] = (pc+2, pointer, count)
            self.scan_after[pc+2] = (pointer, count)
            excluded.append((pc, pc+1))
        assert excluded
        for kind, handle, args, kwargs in hooks:
            if kind != self.u.UC_HOOK_CODE or handle in removed:
                continue
            values, pieces = parent.observer.observer_slices(args, kwargs, excluded, self.on_code)
            self.cpu.hook_del(handle)
            for lo, hi in pieces:
                self.cpu.hook_add(self.u.UC_HOOK_CODE, values["callback"], values["user_data"],
                    lo, hi, values["aux1"], values["aux2"])

    def on_code(self, cpu, address, size, data):
        entries = getattr(self, "tail_entries", {})
        if address in entries:
            return_pc, target = entries[address]
            sp = cpu.reg_read(self.regs["ESP"])
            assert self.word(sp) == return_pc
            snapshot = {name: cpu.reg_read(reg) for name, reg in self.regs.items() if name != "EIP"}
            self.tail_receipts.append((address, target, sp, return_pc, snapshot))
            self.pending_tail = self.tail_receipts[-1]
        elif self.pending_tail is not None and address == self.pending_tail[1]:
            _, _, sp, return_pc, snapshot = self.pending_tail
            assert cpu.reg_read(self.regs["ESP"]) == sp and self.word(sp) == return_pc
            assert {name: cpu.reg_read(reg) for name, reg in self.regs.items() if name != "EIP"} == snapshot
            self.pending_tail = None
        super().on_code(cpu, address, size, data)

    def apply_tail_joins(self):
        values, _ = emit(self.layout.profile, self.layout.resolution)
        previous = values[7]
        joined = tool._join_field(previous, self.continuation)
        def rebased(out):
            raw = bytearray(out.code)
            for row in out.relocations:
                if row.kind == "abs32":
                    struct.pack_into("<I", raw, row.offset, row.target+self.delta)
            return bytes(raw)
        expected_before, expected_after = rebased(previous), rebased(joined)
        assert bytes(self.cpu.mem_read(previous.base_va+self.delta, len(expected_before))) == expected_before
        for _, pc, old, target in self.continuation.field_call_patches:
            site = pc+self.delta
            assert bytes(self.cpu.mem_read(site, 5)) == old
            self.cpu.mem_write(site, b"\xe8"+struct.pack("<i", target+self.delta-site-5))
            self.cpu.ctl_remove_cache(site, site+5)
        assert bytes(self.cpu.mem_read(joined.base_va+self.delta, len(expected_after))) == expected_after
        assert sum(va == joined.base_va+self.delta for va, _ in self.loaded_code) == 1
        self.loaded_code = [(va, expected_after if va == joined.base_va+self.delta else raw)
                            for va, raw in self.loaded_code]

    def setup_post(self, va, *, final_unit=True):
        family = next(family for pc, family, _ in ROWS if pc == va)
        row = next(row for row in parent.replay_fixture.native_content.SITES if row[2] == family)
        regs = self.setup_body(row, index=21, via_adjacent=family == "unit")
        if family == "unit":
            self.set_atomic_ancestry(caller=parent.FINAL_RETURN if final_unit else parent.ORDINARY_RETURNS[0], identity=21)
        if va == tool.FINAL_ADJACENT_POST:
            regs["EBP"] = 0xfffffffd
            self.put(tool.MOTION+self.delta, 0xfffffffd)
            self.put(tool.ACTIVE+self.delta, 21)
        return regs

    def scalar_baseline(self, va, regs, flags):
        """Execute exact scalar ledger at the native VA in a separate CPU."""
        u = self.tools[0]
        cpu = u.Uc(u.UC_ARCH_X86, u.UC_MODE_32)
        for address, size in ((0x400000+self.delta, 0x200000), (self.STACK, 0x10000), (self.WORLD, 0x5000)):
            cpu.mem_map(address, size)
            cpu.mem_write(address, bytes(self.cpu.mem_read(address, size)))
        raw = bytes.fromhex(next(raw for pc, _, raw in ROWS if pc == va))
        adjusted = bytearray(raw)
        for at in HIGHLOW:
            if va <= at < va+len(raw):
                offset = at-va
                struct.pack_into("<I", adjusted, offset, struct.unpack_from("<I", raw, offset)[0]+self.delta)
        cpu.mem_write(va+self.delta, bytes(adjusted))
        for name, value in regs.items():
            cpu.reg_write(self.regs[name], value & 0xffffffff)
        cpu.reg_write(self.regs["EFLAGS"], flags)
        stops = self.scalar_stops(va)
        def stop(machine, address, size, data):
            if address in stops:
                machine.emu_stop()
        cpu.hook_add(u.UC_HOOK_CODE, stop)
        cpu.emu_start(va+self.delta, self.STOP+1, count=100)
        return {name: cpu.reg_read(reg) for name, reg in self.regs.items()}, cpu.reg_read(self.regs["EFLAGS"])

    def scalar_stops(self, va):
        raw = bytes.fromhex(next(raw for pc, _, raw in ROWS if pc == va))
        stops, offset = {va+self.delta+len(raw)}, 0
        while offset < len(raw):
            tail = raw[offset:]
            if tail[0] == 0xe9:
                stops.add(va+offset+5+struct.unpack_from("<i", raw, offset+1)[0]+self.delta)
                offset += 5
            elif 0x70 <= tail[0] <= 0x7f:
                stops.add(va+offset+2+struct.unpack_from("<b", raw, offset+1)[0]+self.delta)
                offset += 2
            elif tail[:2] == b"\x0f\x85":
                stops.add(va+offset+6+struct.unpack_from("<i", raw, offset+2)[0]+self.delta)
                offset += 6
            else:
                offset += tool._scalar_length(raw, offset)
        return stops

    def invoke_post(self, va, regs, *, flags=0xed7, wrong_pc=None):
        old, target = self.post_planned[va]
        site = va+self.delta if wrong_pc is None else wrong_pc
        self.cpu.mem_write(site, b"\xe8"+struct.pack("<i", target+self.delta-site-5)+b"\x90"*(len(old)-5))
        self.cpu.ctl_remove_cache(site, site+len(old))
        self.stops = self.scalar_stops(va)
        self.native_stop, self.unsafe, self.active_scan = None, False, None
        self.before_callbacks = len(self.callbacks)
        self.content_reads, self.content_writes, self.content_events = [], [], []
        self.content_after_thread, self.content_active = False, True
        self.minimum_sp = regs["ESP"]
        for name, value in regs.items():
            self.cpu.reg_write(self.regs[name], value & 0xffffffff)
        self.cpu.reg_write(self.regs["EFLAGS"], flags)
        try:
            self.cpu.emu_start(site, self.STOP+1, count=2000000)
        finally:
            self.content_active = False
        return {name: self.cpu.reg_read(reg) for name, reg in self.regs.items()}, self.cpu.reg_read(self.regs["EFLAGS"])


class SourceTests(unittest.TestCase):
    def test_selected12_complete_windows_operands_two_tail_joins_and_capacity(self):
        import capstone
        for profile in tool.PROFILES:
            for resolution in tool.RESOLUTIONS:
                with self.subTest(profile=profile, resolution=resolution):
                    values, out = emit(profile, resolution)
                    self.assertEqual(out.base_va, (values[-1].base_va+len(values[-1].code)+15)&~15)
                    self.assertEqual(tuple(row[0] for row in out.planned_hooks), tuple(row[0] for row in ROWS))
                    self.assertLessEqual(out.base_va+len(out.code), values[0].rx.va+values[0].rx.size)
                    declarations = {row.offset: row for row in out.relocations}
                    self.assertEqual(len(declarations), len(out.relocations))
                    seen = set()
                    instructions = disassemble(out)
                    starts = {row.address for row in instructions}
                    for ins in instructions:
                        fields = []
                        for operand in ins.operands:
                            if operand.type == capstone.x86.X86_OP_MEM and operand.mem.base == operand.mem.index == 0:
                                fields.append((ins.disp_offset, ins.disp_size, "abs32", operand.mem.disp & 0xffffffff))
                        if ins.group(capstone.CS_GRP_JUMP) or ins.group(capstone.CS_GRP_CALL):
                            if ins.operands[0].type == capstone.x86.X86_OP_IMM:
                                fields.append((ins.imm_offset, ins.imm_size, "rel32", ins.operands[0].imm & 0xffffffff))
                        for offset, size, kind, target in fields:
                            at = ins.address-out.base_va+offset
                            self.assertEqual(size, 4)
                            self.assertIn(at, declarations)
                            self.assertEqual((declarations[at].kind, declarations[at].target), (kind, target))
                            seen.add(at)
                        for row in out.relocations:
                            if not ins.address-out.base_va <= row.offset < ins.address-out.base_va+ins.size:
                                continue
                            if row.offset in seen:
                                continue
                            self.assertEqual((row.offset, row.kind), (ins.address-out.base_va+ins.imm_offset, "abs32"))
                            self.assertEqual(ins.imm_size, 4)
                            self.assertEqual(struct.unpack_from("<I", out.code, row.offset)[0], row.target)
                            seen.add(row.offset)
                    self.assertEqual(seen, set(declarations))
                    for row in out.relocations:
                        if row.kind == "rel32" and out.base_va <= row.target < out.base_va+len(out.code):
                            self.assertIn(row.target, starts)
                    self.assertTrue(all(va in starts for _, va in out.entries+out.private_entries))
                    joined = tool._join_field(values[7], out)
                    changed = {i for i, (old, new) in enumerate(zip(values[7].code, joined.code)) if old != new}
                    allowed = {at for _, pc, _, _ in out.field_call_patches for at in range(pc-values[7].base_va+1, pc-values[7].base_va+5)}
                    self.assertLessEqual(changed, allowed)
                    self.assertEqual(len(out.field_call_patches), 2)

    def test_public_boundary_rejects_synthetic_input_and_mutable_aliases(self):
        def poison(*args, **kwargs):
            raise AssertionError("mutable alias used")
        with patch.object(tool, "_issue", poison), patch.object(tool, "_snapshot", poison):
            for original in (b"", b"authored executable", bytearray(b"authored executable"), None):
                with self.assertRaisesRegex(ValueError, "exact continuation V2 original"):
                    tool.emit_continuation_v2(original, "classic", "1920x1080")

    def test_complete_frozen_sources_and_empty_provider_boundary(self):
        self.assertEqual(sha((ROOT/tool.PARENT).read_bytes()), tool.PARENT_SHA)
        self.assertEqual(sha((ROOT/tool.LEDGER).read_bytes()), tool.LEDGER_SHA)
        values, _ = emit()
        args = (values[0], values[3], values[4], values[5], values[6], values[7], *values[-3:])
        bad = list(args)
        bad[0] = replace(values[0], provider_schema="populated provider")
        with self.assertRaises(ValueError):
            tool._raw_emit(*bad, **arguments())
        for at in (6, 7, 8):
            bad = list(args)
            bad[at] = replace(bad[at], code=bad[at].code[:-1])
            with self.assertRaises(ValueError):
                tool._raw_emit(*bad, **arguments())

    def test_authored_window_authentication_and_field_tail_metadata_cannot_be_partial(self):
        # This small authored buffer exercises rejection mechanics. It is not
        # an original PE, native function, candidate or native-byte proof.
        low, high = min(row[0] for row in ROWS), max(row[0]+len(bytes.fromhex(row[2])) for row in ROWS)
        image = bytearray(high-low)
        for va, _, raw in ROWS:
            image[va-low:va-low+len(bytes.fromhex(raw))] = bytes.fromhex(raw)
        image = bytes(image)
        mapper = SimpleNamespace(file_offset=lambda raw, va, count: va-low)
        relocations = tuple(va-0x400000 for va in HIGHLOW if any(pc <= va < pc+len(bytes.fromhex(raw)) for pc, _, raw in ROWS))
        pe = SimpleNamespace(inspect_pe=lambda raw: SimpleNamespace(image_base=0x400000),
            _old_relocations=lambda raw, parsed: (None, relocations))
        ledger = (ROOT/tool.LEDGER).read_bytes()
        tool._authenticate_native(image, image, mapper, pe, ledger)
        for va, _, _ in ROWS:
            bad = bytearray(image)
            bad[va-low] ^= 1
            for original, relayout in ((bytes(bad), image), (image, bytes(bad))):
                with self.assertRaises(ValueError):
                    tool._authenticate_native(original, relayout, mapper, pe, ledger)
        for rows in (relocations[:-1], relocations+(ROWS[0][0]-0x400000,)):
            broken = SimpleNamespace(inspect_pe=pe.inspect_pe, _old_relocations=lambda raw, parsed: (None, rows))
            with self.assertRaises(ValueError):
                tool._authenticate_native(image, image, mapper, broken, ledger)
        values, out = emit()
        first, second = out.field_call_patches
        for bad in (out.field_call_patches[::-1], (first, first),
                    ((first[0], first[1], first[2], first[3]+1), second)):
            with self.assertRaises(ValueError):
                tool._join_field(values[7], replace(out, field_call_patches=bad))
        with self.assertRaises(ValueError):
            tool._join_field(tool._join_field(values[7], out), out)


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools = parent.replay_fixture.tile_fixture.loss_fixture.lease_fixture.field_fixture.routing_fixture.lifetime.prior_fixture.machine_tools()
        if cls.tools is None:
            raise RuntimeError("required Unicorn unavailable")

    def make(self, profile="classic", resolution="1920x1080", delta=0, mode=0):
        return Machine(self.tools, profile, resolution, delta).prepare(columns=2).begin(mode)

    def assert_parity(self, m, va, *, final_unit=True, flags=0xed7):
        regs = m.setup_post(va, final_unit=final_unit)
        expected, expected_flags = m.scalar_baseline(va, regs, flags)
        actual, actual_flags = m.invoke_post(va, regs, flags=flags)
        self.assertFalse(m.unsafe, (hex(va), hex(m.cpu.reg_read(m.regs["EIP"]))))
        self.assertEqual(actual, expected, hex(va))
        self.assertEqual(actual_flags & m.MASK, expected_flags & m.MASK, hex(va))
        self.assertEqual(m.callbacks[m.before_callbacks:], ["thread"])
        self.assertLessEqual(regs["ESP"]-m.minimum_sp, tool.HELPER_BYTES+140)

    def test_all43_scalar_windows_flags_registers_and_bases(self):
        for delta in (0, 0x30000):
            for mode in (0, 1):
                m = self.make(delta=delta, mode=mode)
                for va, _, _ in ROWS:
                    with self.subTest(va=hex(va), delta=delta, mode=mode):
                        self.assert_parity(m, va)
                del m
                gc.collect()

    def test_selected12_profiles_preserve_both_field_modes_and_rebased_final_receipts(self):
        for profile in tool.PROFILES:
            for resolution in tool.RESOLUTIONS:
                for delta in (0, 0x30000):
                    for mode in (0, 1):
                        with self.subTest(profile=profile, resolution=resolution, delta=delta, mode=mode):
                            m = self.make(profile, resolution, delta, mode)
                            for va, _, _ in ROWS:
                                self.assert_parity(m, va)
                            del m
                            gc.collect()

    def test_wrong_call_motion_unknown_index_and_provider_tail_stop_without_repair(self):
        for fault in ("wrong_pc", "motion", "identity", "provider", "owner", "ancestor"):
            with self.subTest(fault=fault):
                m = self.make()
                regs = m.setup_post(0x42ffa4)
                if fault == "motion":
                    m.put(tool.MOTION, 0)
                elif fault == "identity":
                    m.put(tool.ACTIVE, 22)
                elif fault == "provider":
                    m.put(m.state_va+128, 1)
                elif fault == "owner":
                    m.put(m.state_va+36, 1)
                elif fault == "ancestor":
                    m.put(m.tile_sp, 0x430000)
                before = bytes(m.cpu.mem_read(m.state_va, 65536))
                with self.assertRaises(self.tools[0].UcError):
                    m.invoke_post(0x42ffa4, regs, wrong_pc=0x401100 if fault == "wrong_pc" else None)
                self.assertTrue(m.unsafe)
                pc = m.cpu.reg_read(m.regs["EIP"])
                self.assertIn(pc, m.unsafe_vas)
                self.assertEqual(bytes(m.cpu.mem_read(pc, 2)), b"\x0f\x0b")
                self.assertIsNone(m.native_stop)
                self.assertEqual(bytes(m.cpu.mem_read(m.state_va, 65536)), before)
                del m
                gc.collect()

    def test_callback_control_native_receipt_and_final_motion_losses_stop_before_cached_reads(self):
        for fault in ("outer_return", "helper_return", "native_return", "saved_eax", "tile_return", "motion", "identity"):
            with self.subTest(fault=fault):
                m = self.make("modalwidgets", delta=0x30000)
                regs = m.setup_post(0x42ffa4)
                helper = regs["ESP"]-tool.HELPER_BYTES-96
                def corrupt(mm, name):
                    if name != "thread":
                        return
                    address = {"outer_return": helper+tool.HELPER_BYTES+36,
                        "helper_return": helper-4, "native_return": helper+tool.HELPER_BYTES+92,
                        "saved_eax": helper+tool.HELPER_BYTES+28,
                        "tile_return": mm.tile_sp, "motion": tool.MOTION+mm.delta,
                        "identity": tool.ACTIVE+mm.delta}[fault]
                    mm.put(address, mm.word(address)^1)
                    mm.protect_cached(mm.u.UC_PROT_NONE)
                m.mutation = corrupt
                with self.assertRaises(self.tools[0].UcError):
                    m.invoke_post(0x42ffa4, regs)
                pc = m.cpu.reg_read(m.regs["EIP"])
                self.assertIn(pc, m.unsafe_vas)
                self.assertEqual(bytes(m.cpu.mem_read(pc, 2)), b"\x0f\x0b")
                self.assertEqual(m.cached_reads(post_thread=True), [])
                self.assertEqual(m.callbacks[m.before_callbacks:], ["thread"])
                del m
                gc.collect()

    def test_field_tail_joins_preserve_natural_call_frame_and_loss_consumption(self):
        for delta in (0, 0x30000):
            for mode in (0, 1):
                for loss in (False, True):
                    with self.subTest(delta=delta, mode=mode, loss=loss):
                        m = self.make("framed", delta=delta, mode=mode)
                        m.apply_tail_joins()
                        if loss:
                            m.put(m.lease_frame+44, 2)
                            m.put(m.lease_frame+48, 2)
                        self.assertEqual(m.complete()["EAX"], 2 if loss else 1)
                        self.assertTrue(m.tail_receipts)
                        self.assertIsNone(m.pending_tail)
                        self.assertEqual(len(m.tail_receipts), 1 if loss or mode else 14)
                        self.assertEqual(m.tiles, [(0, 0)] if loss or mode else [(x, y) for x in range(2) for y in range(7)])
                        del m
                        gc.collect()


def run_tests():
    before = source_closure()
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in (SourceTests, CPUTests))
    count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if source_closure() != before:
        raise ValueError("fresh continuation fixture source closure changed")
    if not result.wasSuccessful() or result.skipped or result.testsRun != count:
        raise AssertionError("fresh continuation contract failures")
    return count


if __name__ == "__main__":
    if len(sys.argv) > 1:
        unittest.main()
    else:
        run_tests()
