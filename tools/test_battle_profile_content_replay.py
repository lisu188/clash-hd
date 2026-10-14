#!/usr/bin/env python3
"""Independent CPU/operand checks for uninstalled seventeen-site replay.

Only authored scalar tails run in Unicorn. No original executable body,
native callback, debugger, game, candidate file or release lane is executed.
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
from src.patcher import battle_profile_content_replay as tool
from src.patcher import battle_profile_tile_replay as tile_tool
from src.patcher import battle_profile_content_v2 as content_tool
from src.patcher import battle_profile_content as native_content
from src.patcher import partial_tile_clip as clip
import test_battle_profile_tile_replay as tile_fixture

TILE_SOURCE_SHA256 = "2df87c637b5477ed4154a57fd69751f4a7f48712dc73ccac23c133e543a2a8c6"
TILE_FIXTURE_SHA256 = "ae4af88f86a5d574ebb80770b281c864de4f1baf78b9be16261495263b9701c7"
SITES = tuple(row for row in native_content.SITES if row[2] != "tile")
WINDOWS = {
    0x42f7cf: "0fbf8401540300006bc058", 0x42f84a: "0fbf825403000083f8ff",
    0x42f9af: "668b825803000001d86bc028", 0x42f9c3: "668b825a030000038738335100",
    0x42f9d7: "0fbf80fe05000083f8ff", 0x42f9ec: "8a99560300003a9a56030000",
    0x42fc5f: "0fbf84025403000083f81b", 0x42fc92: "0fbf8468fc05000083f8ff",
    0x42fcea: "0fbf84680006000083f8ff", 0x42fd26: "0fbf846afe05000083f8ff",
    0x42fd7f: "0fbf846afe05000083f8ff", 0x42fdc0: "0fbf846afc05000083f8ff",
    0x42fe23: "0fbf846a0006000083f8ff", 0x42fe68: "0fbf846afc05000083f8ff",
    0x42febb: "0fbf84680006000083f8ff", 0x426f44: "0fbf8c59fe05000083f9ff",
    0x426f54: "8a9411560300003a5702",
}
CACHE = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def arguments():
    return dict(tile_module=tile_tool, tile_kwargs=tile_fixture.arguments(),
                content_module=content_tool, assembler_module=clip,
                ledger_source=(ROOT / tile_fixture.LEDGER_SOURCE).read_bytes())


def emit(profile="classic", resolution="800x600"):
    key = profile, resolution
    if key not in CACHE:
        prefix = tile_fixture.emit(profile, resolution)
        CACHE[key] = prefix + (tool._emit_code(*prefix, **arguments()),)
    return CACHE[key]


def source_closure():
    previous = tile_fixture.source_closure()
    for name, digest in ((tile_tool.SOURCE, TILE_SOURCE_SHA256),
                         ("tools/test_battle_profile_tile_replay.py", TILE_FIXTURE_SHA256)):
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError("frozen content replay dependency differs: " + name)
    names = set(previous) | {tool.SOURCE, "tools/test_battle_profile_content_replay.py"}
    return {name: sha((ROOT / name).read_bytes()) for name in sorted(names)}


def decode(code, absolute_fields):
    """Decode a closed dialect; absolute fields come from authored receipts."""
    cursor, rows = 0, []
    while cursor < len(code):
        start = cursor
        op = code[cursor]; cursor += 1
        absolute, relative, scalar = [], [], []

        def immediate(size=4, role="immediate"):
            nonlocal cursor
            assert cursor + size <= len(code), (start, "truncated operand")
            if role == "memory_address" or size == 4 and cursor in absolute_fields:
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
        elif 0xb8 <= op <= 0xbf or op in (0xa9, 0x3d):
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
        elif op == 0x66:
            assert code[cursor] in (0x8b, 0x89); cursor += 1; memory = True
        else:
            assert op in (0x81, 0x83, 0x8b, 0x89, 0x88, 0x3b, 0x39, 0x3a,
                          0x03, 0x85, 0xf7, 0xff, 0x31, 0x29, 0x01, 0xc1,
                          0x6b, 0x8d, 0xd1), (start, op)
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


class Machine(tile_fixture.Machine):
    def __init__(self, tools, profile="classic", resolution="800x600", delta=0):
        super().__init__(tools, profile, resolution, delta)
        self.replay = emit(profile, resolution)[-1]
        raw = bytearray(self.replay.code)
        for row in self.replay.relocations:
            if row.kind == "abs32":
                struct.pack_into("<I", raw, row.offset, row.target + delta)
        self.cpu.mem_write(self.replay.base_va + delta, bytes(raw))
        self.loaded_code.append((self.replay.base_va + delta, bytes(raw)))
        self.planned = {va: (old, target, role, removed)
                        for va, old, target, role, removed in self.replay.planned_hooks}
        self.unsafe_vas.update(va+delta for name, va in self.replay.private_entries if "unsafe" in name)
        table = struct.pack("<16i", *(v for pair in native_content.NEIGHBORS for v in pair))
        self.cpu.mem_write(0x513334+delta, table)
        if delta:
            self.cpu.mem_write(0x513334, struct.pack("<16i", *(0x101+i for i in range(16))))

    def setup_native(self, row, *, index=21, via_adjacent=False, table_offset=8):
        regs = self.setup_body(row, index=index, via_adjacent=via_adjacent)
        if row[0] == 0x42f9c3:
            regs["EDI"] = table_offset
        if row[0] == 0x42f9ec:
            regs["EDX"] = self.WORLD + 31*index
        return regs

    def value(self, row, index=21):
        if row[3] == "occupant":
            nx, ny = self.neighbor
            if not (0 <= nx < 2 and 0 <= ny < 7):
                return 0xffffffff
            value, at = index, self.WORLD+1534+40*nx+2*ny
            self.cpu.mem_write(at, struct.pack("<h", value))
        elif row[3] in ("type", "unit_type"):
            value = 34
            self.cpu.mem_write(self.WORLD+852+31*index, struct.pack("<h", value))
        elif row[3] == "coordinate":
            value = 1 if row[4] == 4 else 6
            self.cpu.mem_write(self.WORLD+852+31*index+row[4], struct.pack("<H", value))
        else:
            value = 0xd3
            self.cpu.mem_write(self.WORLD+854+31*index, bytes([value]))
            if row[2] == "count":
                self.cpu.mem_write(self.WORLD+854, b"\x5a")
        return value

    def scalar_oracle(self, row, regs, value, flags):
        operand = bytes.fromhex(row[1])
        width = 16 if operand[0] == 0x66 else 8 if operand[0] == 0x8a else 32
        modrm = operand[1 if width == 8 else 2]
        dest = ("EAX", "ECX", "EDX", "EBX", "ESP", "EBP", "ESI", "EDI")[(modrm >> 3) & 7]
        mask = (1 << width)-1
        state = dict(regs)
        state[dest] = (state[dest] & ~mask) | (value & mask)
        tail = bytearray(bytes.fromhex(WINDOWS[row[0]])[len(operand):])
        if row[0] == 0x42f9c3:
            assert tail[:2] == b"\x03\x87"
            struct.pack_into("<I", tail, 2, 0x513338+self.delta)
        cpu = self.u.Uc(self.u.UC_ARCH_X86, self.u.UC_MODE_32)
        cpu.mem_map(0x10000, 4096)
        cpu.mem_map(0x500000+self.delta, 0x60000)
        cpu.mem_write(0x500000+self.delta, bytes(self.cpu.mem_read(0x500000+self.delta, 0x60000)))
        # Authored fixture WORLD may live outside the rebased native globals.
        if not 0x500000+self.delta <= self.WORLD < 0x560000+self.delta:
            cpu.mem_map(self.WORLD & ~4095, 8192)
            cpu.mem_write(self.WORLD, bytes(self.cpu.mem_read(self.WORLD, 4096)))
        cpu.mem_write(0x10000, bytes(tail))
        for name, item in state.items():
            cpu.reg_write(self.regs[name], item & 0xffffffff)
        cpu.reg_write(self.regs["EFLAGS"], flags)
        cpu.emu_start(0x10000, 0x10000+len(tail), count=20)
        return {name: cpu.reg_read(reg) for name, reg in self.regs.items()}


class SourceTests(unittest.TestCase):
    def test_all36_complete_prefix_windows_and_independent_operand_inventory(self):
        source_closure()
        for profile in tile_fixture.content_fixture.parent_fixture.context.PROFILES:
            for resolution in tile_fixture.content_fixture.parent_fixture.context.RESOLUTIONS:
                with self.subTest(profile=profile, resolution=resolution):
                    layout, life, route, field, lease, content, loss, joined, tile, out = emit(profile, resolution)
                    self.assertEqual(out.base_va, (tile.base_va+len(tile.code)+15)&~15)
                    self.assertLessEqual(out.base_va+len(out.code), layout.rx.va+layout.rx.size)
                    self.assertEqual(len(out.entries), 17)
                    self.assertEqual(len(out.body_receipts), 17)
                    self.assertEqual(len(out.source_blocks), 17)
                    self.assertEqual(tuple(r[0] for r in out.planned_hooks), tuple(r[0] for r in SITES))
                    for va, old, target, role, removed in out.planned_hooks:
                        self.assertEqual(old, bytes.fromhex(WINDOWS[va]))
                        self.assertEqual(target, dict(out.entries)[f"site_{va:06x}"])
                        self.assertEqual(role, "content_operand")
                        self.assertEqual(removed, (0x2f9cc,) if va == 0x42f9c3 else ())
                    absolute = set()
                    for va, old_entry, old_end, digest, entry, old_pc in out.source_blocks:
                        self.assertEqual(digest, sha(content.code[old_entry-content.base_va:old_end-content.base_va]))
                        absolute.update(entry-out.base_va+r.offset+content.base_va-old_entry
                            for r in content.relocations if r.kind == "abs32" and
                            old_entry <= content.base_va+r.offset < old_end)
                    for va, entry, payload, pc, denied, fault, valid, finish, resume in out.body_receipts:
                        absolute.add(finish-out.base_va+25)
                        absolute.add(dict(out.private_entries)[f"admit_{va:06x}"]-out.base_va+17)
                    table_at = dict(out.private_entries)["admit_42f9c3"]-out.base_va-9
                    self.assertEqual(out.code[table_at-2:table_at], b"\x03\x87")
                    absolute.add(table_at)
                    decoded = decode(out.code, absolute)
                    starts = {r[0] for r in decoded}
                    declared = {r.offset: r for r in out.relocations}
                    self.assertEqual(len(declared), len(out.relocations))
                    self.assertEqual({at for _, _, aa, rr, ss in decoded for at in aa},
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
                    records = tool._operand_inventory(out, content)
                    self.assertEqual([(r.offset, r.value) for r in records if r.role == "native_table_base_displacement"],
                                     [(table_at, 0x513338)])

    def test_every_parent_tile_field_and_source_receipt_is_checked(self):
        prefix = emit()
        tile = prefix[-2]
        for field in ("code", "relocations", "body_receipts", "source_blocks", "planned_hooks", "entries", "private_entries"):
            bad = replace(tile, **{field: getattr(tile, field)[:-1]})
            supplied = list(prefix[:-1]); supplied[-1] = bad
            with self.subTest(field=field), self.assertRaises(ValueError):
                tool._emit_code(*supplied, **arguments())
        self.assertEqual(asdict(tile), asdict(tile_fixture.emit()[-1]))
        for index in (3, 4, 5, 6, 7):
            value = prefix[index]
            for field in ("code", "relocations"):
                supplied = list(prefix[:-1])
                supplied[index] = replace(value, **{field: getattr(value, field)[:-1]})
                with self.subTest(parent_index=index, field=field), self.assertRaises(ValueError):
                    tool._emit_code(*supplied, **arguments())

    def test_exact_original_relayout_windows_and_selected_highlow(self):
        origin, length = 0x426000, 0x10000
        image = bytearray(length)
        for va, text in WINDOWS.items():
            raw = bytes.fromhex(text)
            image[va-origin:va-origin+len(raw)] = raw
        image = bytes(image)
        mapper = SimpleNamespace(file_offset=lambda image, va, count: va-origin)
        pe = SimpleNamespace(inspect_pe=lambda image: SimpleNamespace(image_base=0x400000),
                             _old_relocations=lambda image, parsed: (None, (0x2f9cc,)))
        ledger = arguments()["ledger_source"]
        tool._authenticate_windows(image, image, mapper, pe, ledger)
        for target in (0, 1):
            for va in (0x42f9af, 0x42f9c3, 0x42f9ec, 0x426f54):
                bad = bytearray(image)
                bad[va-origin+len(bytes.fromhex(WINDOWS[va]))-1] ^= 1
                supplied = [image, image]; supplied[target] = bytes(bad)
                with self.subTest(target=target, va=va), self.assertRaises(ValueError):
                    tool._authenticate_windows(*supplied, mapper, pe, ledger)
        for values in ((), (0x2f9cc, 0x2f9c4)):
            pe._old_relocations = lambda image, parsed, values=values: (None, values)
            with self.assertRaises(ValueError):
                tool._authenticate_windows(image, image, mapper, pe, ledger)

    def test_closed_bytes_roles_receipts_and_scalar_cannot_be_addresses(self):
        *_, content, loss, joined, tile, out = emit()
        forged = clip.Relocation(5, "abs32", 784, "content_replay_source_absolute:forged")
        with self.assertRaises(ValueError):
            tool._operand_inventory(replace(out, relocations=out.relocations+(forged,)), content)
        for name in ("source_blocks", "body_receipts", "planned_hooks", "private_entries"):
            with self.subTest(field=name), self.assertRaises(ValueError):
                tool._operand_inventory(replace(out, **{name: getattr(out, name)[::-1]}), content)
        row = next(r for r in out.relocations if r.purpose == "native_content_scalar_highlow")
        for bad in (replace(row, kind="rel32"), replace(row, target=row.target+4),
                    replace(row, purpose="content_replay_source_absolute:forged")):
            altered = tuple(bad if r == row else r for r in out.relocations)
            with self.assertRaises(ValueError):
                tool._operand_inventory(replace(out, relocations=altered), content)
        for at in (0, row.offset, dict(out.private_entries)["admit_42f9ec"]-out.base_va+17):
            raw = bytearray(out.code); raw[at] ^= 1
            with self.assertRaises(ValueError):
                tool._operand_inventory(replace(out, code=bytes(raw)), content)

    def test_ledger_public_aliases_and_nonacceptance_metadata(self):
        supplied = arguments(); supplied["ledger_source"] = supplied["ledger_source"][:-1]
        with self.assertRaises(ValueError):
            tool._emit_code(*emit()[:-1], **supplied)
        def poison(*args, **kwargs):
            raise AssertionError("mutable producer alias invoked")
        with patch.object(tool, "_issue", poison), patch.object(tile_tool, "_issue", poison):
            for original in (b"", b"synthetic PE", bytearray(b"synthetic PE"), None):
                with self.assertRaisesRegex(ValueError, "original"):
                    tool.emit_content_replay(original, "classic", "800x600")
        for name in ("installed", "native_executed", "runtime_verified", "manual_input_proof",
                     "release_accepted", "promotion_ready", "native_count_early_reads_adapted",
                     "count_entry_record_guard_installed", "non_draw_count_admission"):
            self.assertIn(name, tool.FALSE_CLAIMS)
        tree = ast.parse((ROOT/tool.SOURCE).read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and
                             n.func.attr in ("write_bytes", "write_text") for n in ast.walk(tree)))
        self.assertEqual(tool.HELPER_BYTES, 784)


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools = tile_fixture.content_fixture.parent_fixture.field_fixture.routing_fixture.lifetime.prior_fixture.machine_tools()
        if cls.tools is None:
            raise ImportError("required Unicorn CPU interpreter unavailable")

    def make(self, profile="classic", delta=0, mode=0):
        return Machine(self.tools, profile, delta=delta).prepare(columns=2).begin(mode)

    def assert_healthy(self, m, row, regs, value, *, flags=0xed7):
        expected = m.scalar_oracle(row, regs, value, flags)
        owner = m.record()
        actual = m.invoke_replay(row, regs, flags=flags)
        self.assertEqual(m.native_stop, row[0]+m.delta+len(bytes.fromhex(WINDOWS[row[0]])))
        for name in regs:
            self.assertEqual(actual[name], expected[name], (hex(row[0]), name))
        self.assertEqual(actual["EFLAGS"]&m.MASK, expected["EFLAGS"]&m.MASK)
        self.assertEqual(m.callbacks[m.before_callbacks:], ["thread"])
        self.assertFalse(m.unsafe)
        self.assertEqual(m.record(), owner)
        helper = regs["ESP"]-824
        for at, size in m.content_writes:
            self.assertTrue(helper-44 <= at and at+size <= helper+824, (hex(at), size))
        for at, raw in m.loaded_code:
            self.assertEqual(bytes(m.cpu.mem_read(at, len(raw))), raw)
        return actual

    def assert_terminal(self, m, row, regs, **options):
        before = m.record()
        before_tiles = list(m.tiles)
        with self.assertRaises(self.tools[0].UcError):
            m.invoke_replay(row, regs, **options)
        eip = m.cpu.reg_read(m.regs["EIP"])
        self.assertIn(eip, m.unsafe_vas)
        self.assertEqual(bytes(m.cpu.mem_read(eip, 2)), b"\x0f\x0b")
        self.assertIsNone(m.native_stop)
        self.assertEqual(m.record(), before)
        self.assertEqual(m.tiles, before_tiles)

    def test_seventeen_native_tails_partial_registers_all_profiles_two_bases_modes(self):
        for profile in tile_fixture.content_fixture.parent_fixture.context.PROFILES:
            for delta in (0, 0x30000):
                for mode in (0, 1):
                    m = self.make(profile, delta, mode)
                    for row in SITES:
                        regs = m.setup_native(row)
                        value = m.value(row)
                        self.assert_healthy(m, row, regs, value)
                    del m; gc.collect()

    def test_unit_via_adjacent_count_draw_ancestry_sentinel_and_partial_high_bits(self):
        for delta in (0, 0x30000):
            m = self.make("modalwidgets", delta)
            for row in SITES:
                if row[2] not in ("unit", "count"):
                    continue
                regs = m.setup_native(row, via_adjacent=True)
                self.assert_healthy(m, row, regs, m.value(row), flags=0x246)
            row = next(r for r in SITES if r[0] == 0x42f84a)
            regs = m.setup_native(row)
            m.cpu.mem_write(m.WORLD+852+31*21, b"\xff\xff")
            self.assert_healthy(m, row, regs, 0xffffffff)
            del m; gc.collect()

    def test_neighbor_table_rebased_offsets_and_rejection_before_tail_read(self):
        row = next(r for r in SITES if r[0] == 0x42f9c3)
        for delta in (0, 0x30000):
            m = self.make("framed", delta)
            for offset in (0, 8, 56):
                regs = m.setup_native(row, table_offset=offset)
                self.assert_healthy(m, row, regs, m.value(row))
                self.assertIn((0x513338+delta+offset, 4), m.content_reads)
                if delta:
                    self.assertNotIn((0x513338+offset, 4), m.content_reads)
            for offset in (1, 4, 63, 64, 0xffffffF8):
                regs = m.setup_native(row, table_offset=offset); m.value(row)
                self.assert_terminal(m, row, regs)
                self.assertFalse(any(0x513334+delta <= at < 0x513374+delta for at, _ in m.content_reads))
            del m; gc.collect()

    def test_owner_tail_self_is_distinct_from_neighbor_and_rejects_wrong_pointer(self):
        row = next(r for r in SITES if r[0] == 0x42f9ec)
        for delta in (0, 0x30000):
            m = self.make("completehd", delta)
            regs = m.setup_native(row, index=21)
            # Authenticated SELF remains21, while the payload neighbor is7.
            regs["EAX"] = 7; regs["ECX"] = m.WORLD+31*7
            m.cpu.mem_write(m.WORLD+854+31*21, b"\x19")
            m.cpu.mem_write(m.WORLD+854+31*7, b"\xd3")
            actual = self.assert_healthy(m, row, regs, 0xd3)
            self.assertEqual(actual["EBX"]&0xff, 0xd3)
            self.assertIn((m.WORLD+854+31*21, 1), m.content_reads)
            for bad in (m.WORLD+31*7, m.WORLD+31*21+1, 0x7f001000):
                regs = m.setup_native(row); regs["EDX"] = bad; m.value(row)
                self.assert_terminal(m, row, regs)
                self.assertNotIn((bad+854, 1), m.content_reads)
            for offset in (-31, 1, 682):
                regs = m.setup_native(row); m.value(row)
                m.put(m.unit_sp-28, offset)
                self.assert_terminal(m, row, regs)
            del m; gc.collect()

    def test_count_bad_input_or_non_draw_receipt_never_reaches_owner_tail(self):
        row = next(r for r in SITES if r[0] == 0x426f54)
        m = self.make("framed", 0x30000)
        for index in (0, 7, 21):
            regs = m.setup_native(row); value = m.value(row)
            regs["EDI"] = m.WORLD+852+31*index
            self.assert_healthy(m, row, regs, value)
        del m; gc.collect()
        for fault in ("misaligned", "sentinel", "negative", "one_past", "non_draw_one", "non_draw_two"):
            m = self.make("framed", 0x30000)
            regs = m.setup_native(row); m.value(row)
            if fault == "misaligned":
                regs["EDI"] += 1
            elif fault == "sentinel":
                regs["EDI"] = m.WORLD+821
            elif fault == "negative":
                regs["EDI"] = m.WORLD+852-1
            elif fault == "one_past":
                regs["EDI"] = m.WORLD+852+31*22
            else:
                m.put(m.native_s, (0x426f95 if fault == "non_draw_one" else 0x431d7a)+m.delta)
            self.assert_terminal(m, row, regs)
            self.assertNotIn((regs["EDI"]+2, 1), m.content_reads)
            del m; gc.collect()

    def test_actual_native_and_intrinsic_call_receipts_fail_before_callbacks(self):
        row = SITES[0]
        for fault in ("foreign_native", "intrinsic_return", "intrinsic_stack"):
            m = self.make("modalwidgets", 0x30000)
            regs = m.setup_native(row); m.value(row)
            options = {}
            if fault == "foreign_native":
                options["call_pc"] = row[0]+m.delta+5+0x20
            else:
                guard = dict(m.replay.private_entries)[f"admit_{row[0]:06x}"]+m.delta
                seen = []
                def corrupt(mm, address):
                    if address == guard:
                        sp = mm.cpu.reg_read(mm.regs["ESP"])
                        if fault == "intrinsic_return":
                            mm.put(sp, mm.word(sp)^4)
                        else:
                            mm.cpu.reg_write(mm.regs["ESP"], sp-4)
                        seen.append(sp)
                m.instruction_mutation = corrupt
            self.assert_terminal(m, row, regs, **options)
            if fault != "foreign_native":
                self.assertEqual(len(seen), 1)
            self.assertEqual(m.callbacks[m.before_callbacks:], [])
            self.assertEqual(m.cached_reads(), [])
            del m; gc.collect()

    def test_malformed_or_latched_loss_and_callback_controls_cannot_resume(self):
        for fault in ("type", "occupant", "loss", "status", "descriptor", "helper"):
            m = self.make("completehd", 0x30000)
            row = next(r for r in SITES if r[0] == (0x42f9d7 if fault == "occupant" else 0x42f84a))
            regs = m.setup_native(row); m.value(row)
            if fault == "type":
                m.cpu.mem_write(m.WORLD+852+31*21, struct.pack("<h", -2))
            elif fault == "occupant":
                m.cpu.mem_write(m.WORLD+1534, struct.pack("<h", -2))
            elif fault in ("loss", "status"):
                m.put(m.lease_frame+(44 if fault == "loss" else 48), 2)
                m.protect_cached(m.u.UC_PROT_NONE)
            else:
                seen = []
                def corrupt(mm, label):
                    if label == "thread":
                        at = mm.lease_frame+60 if fault == "descriptor" else regs["ESP"]-824+812
                        mm.put(at, mm.word(at)^4)
                        mm.protect_cached(mm.u.UC_PROT_NONE)
                        seen.append(at)
                m.mutation = corrupt
            self.assert_terminal(m, row, regs)
            self.assertFalse(any(m.lease_frame <= at < m.lease_frame+192 for at, _ in m.content_writes))
            if fault in ("loss", "status"):
                self.assertEqual(m.callbacks[m.before_callbacks:], [])
                self.assertEqual(m.cached_reads(), [])
            elif fault in ("descriptor", "helper"):
                self.assertEqual(len(seen), 1)
                self.assertEqual(m.cached_reads(post_thread=True), [])
            del m; gc.collect()


TEST_COUNT = sum(unittest.defaultTestLoader.loadTestsFromTestCase(cls).countTestCases()
                 for cls in (SourceTests, CPUTests))


def run_tests():
    before = source_closure()
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
                               for cls in (SourceTests, CPUTests))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if source_closure() != before:
        raise ValueError("content replay source closure changed during tests")
    if not result.wasSuccessful() or result.skipped or result.testsRun != TEST_COUNT:
        raise AssertionError("uninstalled content replay fixture failures")
    return result.testsRun


if __name__ == "__main__":
    if len(sys.argv) > 1:
        unittest.main()
    else:
        run_tests()
