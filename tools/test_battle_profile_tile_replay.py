#!/usr/bin/env python3
"""Uninstalled Tile replay: authored scalar CPU oracles, not native runtime.

The native windows are a small independently authored instruction ledger. No
original body, game, debugger, compiler, candidate file or capture is executed.
"""
from __future__ import annotations

import ast
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
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import battle_profile_tile_replay as tool
from src.patcher import battle_profile_field_loss as loss_tool
from src.patcher import battle_profile_content_v2 as content_tool
from src.patcher import battle_profile_content as native_content
from src.patcher import partial_tile_clip as clip
import test_battle_profile_field_loss as loss_fixture
import test_battle_profile_content_v2 as content_fixture

LOSS_SOURCE_SHA256 = "3d473676828e13fc24853c3bf7f08d7e92e2a3f682bd31226e50cbf9f9258163"
LOSS_FIXTURE_SHA256 = "98edffc4cb1f2f5b95b8908e9a4928fcab9976d9152abe75cadf0d390d07419c"
LEDGER_SOURCE = "src/patcher/battle_profile_continuation.py"
LEDGER_SHA256 = "075bd62a8311f8cc761136bca21063813dfc874ce8d8a5bcf075ebdb664d811f"
SITES = tuple(row for row in native_content.SITES if row[2] == "tile")
WINDOWS = {
    0x43026f: "0fbf8441fe05000031ff", 0x430375: "0fbfbc47fc05000083ffff",
    0x4303e7: "0fbfbc42fc05000039df", 0x430459: "0fbfbc4200060000a160235100",
    0x4304b4: "0fbfbc42fe05000083ffff", 0x43055a: "0fbfbc410006000083ffff",
    0x4305da: "0fbfbc420006000039df", 0x430649: "0fbfbc41fc05000039df",
    0x4306a7: "0fbfbc42fe05000083ffff", 0x4302b4: "0fbf8401540300006bc058",
    0x43050a: "0fbf8401540300006bc058",
}
CACHE = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def arguments():
    return dict(loss_module=loss_tool, loss_kwargs=loss_fixture.arguments(),
                content_module=content_tool, assembler_module=clip,
                ledger_source=(ROOT / LEDGER_SOURCE).read_bytes())


def emit(profile="classic", resolution="800x600"):
    key = profile, resolution
    if key not in CACHE:
        prefix = loss_fixture.emit(profile, resolution)
        layout, life, route, field, lease, content, loss = prefix
        joined = loss_tool._join_field(field, loss)
        out = tool._emit_code(*prefix, joined, **arguments())
        CACHE[key] = prefix + (joined, out)
    return CACHE[key]


def source_closure():
    loss_fixture.source_closure()
    for name, digest in ((loss_tool.SOURCE, LOSS_SOURCE_SHA256),
                         ("tools/test_battle_profile_field_loss.py", LOSS_FIXTURE_SHA256),
                         (LEDGER_SOURCE, LEDGER_SHA256)):
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError("frozen Tile replay dependency differs: " + name)
    names = set(loss_fixture.source_closure()) | {
        tool.SOURCE, LEDGER_SOURCE, "tools/test_battle_profile_tile_replay.py"}
    return {name: sha((ROOT / name).read_bytes()) for name in sorted(names)}


def decode(code, absolute_immediates):
    """Independent decoder with exact authored address offsets, never VA guessing."""
    cursor, rows = 0, []
    while cursor < len(code):
        start = cursor
        op = code[cursor]; cursor += 1
        absolute, relative, scalar = [], [], []

        def immediate(size=4, role="immediate"):
            nonlocal cursor
            assert cursor + size <= len(code), (start, "truncated operand")
            if role == "memory_address" or size == 4 and role == "immediate" and cursor in absolute_immediates:
                absolute.append(cursor)
            else:
                scalar.append((cursor, size))
            cursor += size

        memory = False
        if op in (0x9c, 0x9d, 0x60, 0x61, 0xfc, 0xc3, 0x55, 0x5d, 0x4b):
            pass
        elif op == 0xf3:
            assert code[cursor] == 0xaf; cursor += 1
        elif op == 0xa1:
            immediate(role="memory_address")
        elif 0xb8 <= op <= 0xbf or op == 0xa9:
            immediate()
        elif op in (0xe8, 0xe9):
            relative.append(cursor); cursor += 4
        elif op == 0x0f:
            sub = code[cursor]; cursor += 1
            if sub == 0x0b:
                pass
            elif 0x80 <= sub <= 0x8f:
                relative.append(cursor); cursor += 4
            else:
                assert sub in (0xb6, 0xb7, 0xbf); memory = True
        else:
            assert op in (0x81, 0x83, 0x8b, 0x89, 0x3b, 0x39, 0x85, 0xf7,
                          0xff, 0x31, 0x29, 0x01, 0xc1, 0x6b, 0x8d, 0xd1), (start, op)
            memory = True
        if memory:
            modrm = code[cursor]; cursor += 1
            mode, rm = modrm >> 6, modrm & 7
            if mode != 3 and rm == 4:
                sib = code[cursor]; immediate(1, "sib")
                if mode == 0 and sib & 7 == 5:
                    immediate(role="memory_address")
            if mode == 0 and rm == 5:
                immediate(role="memory_address")
            elif mode == 1:
                immediate(1, "displacement")
            elif mode == 2:
                immediate(4, "displacement")
            if op == 0x81 or op == 0xf7 and (modrm >> 3) & 7 == 0:
                immediate()
            elif op in (0x83, 0xc1, 0x6b):
                immediate(1)
        assert start < cursor <= len(code), (start, cursor)
        rows.append((start, cursor, absolute, relative, scalar))
    return rows


class Machine(content_fixture.Machine):
    def __init__(self, tools, profile="classic", resolution="800x600", delta=0):
        super().__init__(tools, profile, resolution, delta)
        self.tools = tools
        *_, self.loss_emission, self.joined_field, self.replay = emit(profile, resolution)
        for out in (self.joined_field, self.loss_emission, self.replay):
            raw = bytearray(out.code)
            for row in out.relocations:
                if row.kind == "abs32":
                    struct.pack_into("<I", raw, row.offset, row.target + delta)
            self.cpu.mem_write(out.base_va + delta, bytes(raw))
            self.loaded_code = [(va, data) for va, data in self.loaded_code if va != out.base_va + delta]
            self.loaded_code.append((out.base_va + delta, bytes(raw)))
        self.planned = {va: (raw, target, role, removed)
                        for va, raw, target, role, removed in self.replay.planned_hooks}
        self.unsafe_vas = {va+delta for name, va in self.replay.private_entries if "unsafe" in name}
        self.unsafe_vas.add(dict(self.content_emission.private_entries)["unsafe_control"]+delta)
        self.instruction_mutation = None

    def on_code(self, cpu, address, size, data):
        if address in getattr(self, "unsafe_vas", ()):
            self.unsafe = True
            return  # Execute the real UD2; do not replace it with a successful stop.
        if getattr(self, "instruction_mutation", None):
            self.instruction_mutation(self, address)
        super().on_code(cpu, address, size, data)

    def invoke_replay(self, row, regs, *, flags=0xed7, call_pc=None):
        va = row[0]
        old, target, _, _ = self.planned[va]
        site = va+self.delta if call_pc is None else call_pc-5
        hook = b"\xe8" + struct.pack("<i", target+self.delta-site-5) + b"\x90"*(len(old)-5)
        self.cpu.mem_write(site, hook)
        self.cpu.ctl_remove_cache(site, site+len(hook))
        self.stops = {va+self.delta+len(old)}
        self.native_stop = None; self.unsafe = False
        self.reads = []; self.writes = []
        self.content_reads = []; self.content_writes = []; self.content_events = []
        self.content_after_thread = False; self.content_active = True
        self.before_callbacks = len(self.callbacks)
        self.minimum_sp = regs["ESP"]
        for name, value in regs.items():
            self.cpu.reg_write(self.regs[name], value & 0xffffffff)
        self.cpu.reg_write(self.regs["EFLAGS"], flags)
        try:
            self.cpu.emu_start(site, self.STOP+1, count=2000000)
        finally:
            self.content_active = False
        return {name: self.cpu.reg_read(reg) for name, reg in self.regs.items()}

    def scalar_oracle(self, row, regs, value, flags):
        """Only stolen scalar tails execute; checked MOVSX is assigned independently."""
        operand = bytes.fromhex(row[1])
        dest = ("EAX", "ECX", "EDX", "EBX", "ESP", "EBP", "ESI", "EDI")[(operand[2] >> 3) & 7]
        state = dict(regs); state[dest] = value & 0xffffffff
        tail = bytearray(bytes.fromhex(WINDOWS[row[0]])[len(operand):])
        if row[0] == 0x430459:
            assert tail[0] == 0xa1
            struct.pack_into("<I", tail, 1, 0x512360+self.delta)
        cpu = self.u.Uc(self.u.UC_ARCH_X86, self.u.UC_MODE_32)
        cpu.mem_map(0x10000, 4096)
        cpu.mem_map(0x500000+self.delta, 0x60000)
        cpu.mem_write(0x512360+self.delta, bytes(self.cpu.mem_read(0x512360+self.delta, 4)))
        cpu.mem_write(0x10000, bytes(tail))
        for name, value in state.items():
            cpu.reg_write(self.regs[name], value & 0xffffffff)
        cpu.reg_write(self.regs["EFLAGS"], flags)
        cpu.emu_start(0x10000, 0x10000+len(tail), count=20)
        return {name: cpu.reg_read(reg) for name, reg in self.regs.items()}


class SourceTests(unittest.TestCase):
    def test_all36_complete_prefix_hooks_instruction_operands_and_bounds(self):
        source_closure()
        for profile in content_fixture.parent_fixture.context.PROFILES:
            for resolution in content_fixture.parent_fixture.context.RESOLUTIONS:
                with self.subTest(profile=profile, resolution=resolution):
                    layout, life, route, field, lease, content, loss, joined, out = emit(profile, resolution)
                    self.assertEqual(out.base_va, (loss.base_va+len(loss.code)+15)&~15)
                    self.assertLessEqual(out.base_va+len(out.code), layout.rx.va+layout.rx.size)
                    self.assertEqual(len(out.entries), 11)
                    self.assertEqual(len(out.body_receipts), 11)
                    self.assertEqual(len(out.source_blocks), 11)
                    self.assertEqual(tuple(r[0] for r in out.planned_hooks), tuple(r[0] for r in SITES))
                    for va, old, target, role, removed in out.planned_hooks:
                        self.assertEqual(old, bytes.fromhex(WINDOWS[va]))
                        self.assertEqual(target, dict(out.entries)[f"site_{va:06x}"])
                        self.assertEqual(removed, (0x30462,) if va == 0x430459 else ())
                    absolute_immediates = set()
                    for va, old_entry, old_end, digest, entry, old_pc in out.source_blocks:
                        self.assertEqual(digest, sha(content.code[old_entry-content.base_va:old_end-content.base_va]))
                        absolute_immediates.update(entry-out.base_va+r.offset+content.base_va-old_entry
                            for r in content.relocations if r.kind == "abs32" and
                            old_entry <= content.base_va+r.offset < old_end)
                    for va, entry, payload, pc, denied, fault, valid, finish, resume in out.body_receipts:
                        absolute_immediates.add(finish-out.base_va+25)
                        absolute_immediates.add(dict(out.private_entries)[f"admit_{va:06x}"]-out.base_va+17)
                    decoded = decode(out.code, absolute_immediates)
                    starts = {r[0] for r in decoded}
                    declared = {r.offset: r for r in out.relocations}
                    self.assertEqual(len(declared), len(out.relocations))
                    self.assertEqual({at for *_, aa, rr, ss in decoded for at in aa},
                                     {r.offset for r in out.relocations if r.kind == "abs32"})
                    self.assertEqual({at for _, _, aa, rr, ss in decoded for at in rr},
                                     {r.offset for r in out.relocations if r.kind == "rel32"})
                    for start, end, aa, rr, ss in decoded:
                        self.assertFalse({at for at, _ in ss} & set(declared))
                        for at in aa:
                            self.assertEqual(struct.unpack_from("<I", out.code, at)[0], declared[at].target)
                        for at in rr:
                            target = out.base_va+at+4+struct.unpack_from("<i", out.code, at)[0]
                            self.assertEqual(target, declared[at].target)
                            if out.base_va <= target < out.base_va+len(out.code):
                                self.assertIn(target-out.base_va, starts)
                    self.assertEqual(asdict(joined), asdict(loss_tool._join_field(field, loss)))

    def test_full_parent_and_joined_field_substitutions_fail(self):
        prefix = emit()
        for index in (3, 4, 5, 6, 7):
            value = prefix[index]
            for bad in (replace(value, code=value.code[:-1]),
                        replace(value, relocations=value.relocations[:-1])):
                supplied = list(prefix[:8]); supplied[index] = bad
                with self.subTest(index=index), self.assertRaises(ValueError):
                    tool._emit_code(*supplied, **arguments())
        with self.assertRaises(ValueError):
            tool._emit_code(*prefix[:7], prefix[3], **arguments())

    def test_ledger_and_mutable_public_alias_rejection(self):
        prefix = emit()
        supplied = arguments()
        supplied["ledger_source"] = supplied["ledger_source"][:-1]
        with self.assertRaises(ValueError):
            tool._emit_code(*prefix[:8], **supplied)
        def poison(*args, **kwargs):
            raise AssertionError("mutable producer alias invoked")
        with patch.object(tool, "_issue", poison), patch.object(loss_tool, "_issue", poison):
            for original in (b"", b"synthetic PE", bytearray(b"synthetic PE"), None):
                with self.assertRaisesRegex(ValueError, "original"):
                    tool.emit_tile_replay(original, "classic", "800x600")

    def test_metadata_explicitly_refuses_native_cleanup_installation_and_acceptance(self):
        self.assertEqual(tool.HELPER_BYTES, 784)
        for name in ("installed", "native_executed", "runtime_verified", "manual_input_proof",
                     "release_accepted", "promotion_ready", "healthy_native_unwind_verified"):
            self.assertIn(name, tool.FALSE_CLAIMS)
        source = (ROOT/tool.SOURCE).read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                             and n.func.attr in ("write_bytes", "write_text") for n in ast.walk(tree)))

    def test_scalar_cannot_be_reclassified_as_an_absolute_address(self):
        *_, content, loss, joined, out = emit()
        # The first SUB ESP,784 immediate is scalar even if declared as abs32.
        self.assertEqual(out.code[:5], bytes.fromhex("9c60fc81ec"))
        forged = clip.Relocation(5, "abs32", 784, "tile_replay_source_absolute:forged")
        with self.assertRaises(ValueError):
            tool._operand_inventory(replace(out, relocations=out.relocations+(forged,)), content)
        for bad in (replace(out, source_blocks=out.source_blocks[:-1]),
                    replace(out, body_receipts=out.body_receipts[::-1]),
                    replace(out, planned_hooks=out.planned_hooks[::-1])):
            with self.assertRaises(ValueError):
                tool._operand_inventory(bad, content)
        guard = dict(out.private_entries)["admit_43026f"]-out.base_va+17
        raw = bytearray(out.code)
        struct.pack_into("<I", raw, guard, struct.unpack_from("<I", raw, guard)[0]+1)
        with self.assertRaises(ValueError):
            tool._operand_inventory(replace(out, code=bytes(raw)), content)

    def test_whole_original_and_relayout_windows_and_highlow_are_checked(self):
        image = bytearray(4096)
        for va, text in WINDOWS.items():
            raw = bytes.fromhex(text)
            image[va-0x430000:va-0x430000+len(raw)] = raw
        image = bytes(image)
        mapper = SimpleNamespace(file_offset=lambda image, va, count: va-0x430000)
        pe = SimpleNamespace(inspect_pe=lambda image: SimpleNamespace(image_base=0x400000),
                             _old_relocations=lambda image, parsed: (None, (0x30462,)))
        ledger = arguments()["ledger_source"]
        tool._authenticate_windows(image, image, mapper, pe, ledger)
        for target in (0, 1):
            for va in (0x43026f, 0x430459, 0x43050a):
                bad = bytearray(image)
                bad[va-0x430000+len(bytes.fromhex(WINDOWS[va]))-1] ^= 1
                supplied = [image, image]; supplied[target] = bytes(bad)
                with self.assertRaises(ValueError):
                    tool._authenticate_windows(*supplied, mapper, pe, ledger)
        for values in ((), (0x30462, 0x30270)):
            pe._old_relocations = lambda image, parsed, values=values: (None, values)
            with self.assertRaises(ValueError):
                tool._authenticate_windows(image, image, mapper, pe, ledger)


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools = content_fixture.parent_fixture.field_fixture.routing_fixture.lifetime.prior_fixture.machine_tools()
        if cls.tools is None:
            raise ImportError("required Unicorn CPU interpreter unavailable")

    def make(self, profile="classic", resolution="800x600", delta=0, mode=0):
        return Machine(self.tools, profile, resolution, delta).prepare(columns=2).begin(mode)

    def test_eleven_native_destinations_scalar_tails_flags_and_stack_all_profiles_two_bases_modes(self):
        for profile in content_fixture.parent_fixture.context.PROFILES:
            for delta in (0, 0x30000):
                for mode in (0, 1):
                    m = self.make(profile, delta=delta, mode=mode)
                    m.put(0x512360+delta, 0x71a2c3d4)
                    if delta:
                        m.put(0x512360, 0x12345678)
                    owner = m.record()
                    for row in SITES:
                        regs = m.setup_body(row, index=21)
                        outside = row[3] == "occupant" and not (0 <= row[4] < 2 and 0 <= row[5] < 7)
                        if row[3] == "occupant":
                            value = 0xffffffff if outside else 21
                            if not outside:
                                m.cpu.mem_write(m.WORLD+1534+40*row[4]+2*row[5], struct.pack("<h", 21))
                        else:
                            value = 34
                            m.cpu.mem_write(m.WORLD+852+31*21, struct.pack("<h", value))
                        expected = m.scalar_oracle(row, regs, value, 0xed7)
                        actual = m.invoke_replay(row, regs)
                        self.assertEqual(m.native_stop, row[0]+delta+len(bytes.fromhex(WINDOWS[row[0]])))
                        for name in regs:
                            self.assertEqual(actual[name], expected[name], (profile, delta, mode, row, name))
                        self.assertEqual(actual["EFLAGS"]&m.MASK, expected["EFLAGS"]&m.MASK)
                        if row[0] == 0x430459:
                            self.assertEqual(actual["EAX"], 0x71a2c3d4)
                        self.assertEqual(m.callbacks[m.before_callbacks:], ["thread"])
                        self.assertFalse(m.unsafe)
                        self.assertEqual(m.record(), owner)
                        if outside:
                            self.assertEqual(m.payload_reads(), [])
                        for at, size in m.content_writes:
                            helper = regs["ESP"]-824
                            self.assertTrue(helper-44 <= at and at+size <= helper+824, (hex(at), size))
                        for at, raw in m.loaded_code:
                            self.assertEqual(bytes(m.cpu.mem_read(at, len(raw))), raw)
                    del m; gc.collect()

    def assert_terminal(self, m, row, regs, **options):
        before_tiles = list(m.tiles)
        with self.assertRaises(self.tools[0].UcError):
            m.invoke_replay(row, regs, **options)
        eip = m.cpu.reg_read(m.regs["EIP"])
        self.assertIn(eip, m.unsafe_vas)
        self.assertEqual(bytes(m.cpu.mem_read(eip, 2)), b"\x0f\x0b")
        self.assertIsNone(m.native_stop)
        self.assertEqual(m.tiles, before_tiles)

    def test_malformed_payload_and_latched_loss_never_fake_empty_or_native_resume(self):
        for role in ("bad_occupant", "bad_type", "loss", "leaf_status"):
            with self.subTest(role=role):
                m = self.make("modalwidgets")
                row = SITES[0] if role != "bad_type" else SITES[9]
                regs = m.setup_body(row, index=21)
                if role == "bad_occupant":
                    m.cpu.mem_write(m.WORLD+1534, struct.pack("<h", -2))
                elif role == "bad_type":
                    m.cpu.mem_write(m.WORLD+852+31*21, struct.pack("<h", -2))
                else:
                    m.put(m.lease_frame+(44 if role == "loss" else 48), 2)
                    m.protect_cached(m.u.UC_PROT_NONE)
                before = m.record()
                self.assert_terminal(m, row, regs)
                self.assertEqual(m.record(), before)
                self.assertFalse(any(m.lease_frame <= at < m.lease_frame+192 for at, _ in m.content_writes))
                if role in ("loss", "leaf_status"):
                    self.assertEqual(m.callbacks[m.before_callbacks:], [])
                    self.assertEqual(m.cached_reads(), [])
                del m; gc.collect()

    def test_foreign_native_call_receipt_denies_before_callback_or_cached_reads(self):
        m = self.make("framed")
        row = SITES[0]; regs = m.setup_body(row)
        self.assert_terminal(m, row, regs, call_pc=row[0]+5+0x20)
        self.assertEqual(m.callbacks[m.before_callbacks:], [])
        self.assertEqual(m.cached_reads(), [])
        del m; gc.collect()
        # The adapter's own admission CALL is real, and its return/stack must
        # be checked before tail-entering the parent callback guard.
        for role in ("return", "stack"):
            with self.subTest(intrinsic_control=role):
                m = self.make("framed", delta=0x30000)
                row = SITES[0]; regs = m.setup_body(row)
                guard = dict(m.replay.private_entries)["admit_43026f"]+m.delta
                seen = []
                def corrupt(mm, address):
                    if address == guard:
                        sp = mm.cpu.reg_read(mm.regs["ESP"])
                        if role == "return":
                            mm.put(sp, mm.word(sp)^4)
                        else:
                            mm.cpu.reg_write(mm.regs["ESP"], sp-4)
                        seen.append(sp)
                m.instruction_mutation = corrupt
                self.assert_terminal(m, row, regs)
                self.assertEqual(len(seen), 1)
                self.assertEqual(m.callbacks[m.before_callbacks:], [])
                self.assertEqual(m.cached_reads(), [])
                del m; gc.collect()

    def test_callback_descriptor_and_helper_control_loss_precede_poisoned_cached_reads(self):
        for role, off in (("lease", 0), ("lease", 60), ("lease", 188),
                          ("helper", 784), ("helper", 812), ("helper", -4)):
            with self.subTest(role=role, offset=off):
                m = self.make("completehd", delta=0x30000)
                row = SITES[0]; regs = m.setup_body(row)
                seen = []
                def corrupt(mm, label):
                    if label == "thread":
                        at = mm.lease_frame+off if role == "lease" else regs["ESP"]-824+off
                        mm.put(at, mm.word(at)^4)
                        mm.protect_cached(mm.u.UC_PROT_NONE)
                        seen.append(at)
                m.mutation = corrupt
                self.assert_terminal(m, row, regs)
                self.assertEqual(len(seen), 1)
                self.assertEqual(m.cached_reads(post_thread=True), [])
                self.assertEqual(m.callbacks[m.before_callbacks:], ["thread"])
                del m; gc.collect()


TEST_COUNT = sum(unittest.defaultTestLoader.loadTestsFromTestCase(cls).countTestCases()
                 for cls in (SourceTests, CPUTests))


def run_tests():
    before = source_closure()
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
                               for cls in (SourceTests, CPUTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if source_closure() != before:
        raise ValueError("Tile replay source closure changed during tests")
    if not result.wasSuccessful() or result.skipped or result.testsRun != TEST_COUNT:
        raise AssertionError("uninstalled Tile replay fixture failures")
    return result.testsRun


if __name__ == "__main__":
    if len(sys.argv) > 1:
        unittest.main()
    else:
        run_tests()
