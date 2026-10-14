#!/usr/bin/env python3
"""Independent source/CPU models for an uninstalled draw-only Count entry.

The Count body below is an authored three-read stub, never original game
instructions or native Count parity. No original, candidate, process or capture
is read, written or launched. Complete source closure and no skips are required.
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
from src.patcher import battle_profile_count_entry as tool
from src.patcher import battle_profile_content_replay as replay_tool
from src.patcher import partial_tile_clip as clip
import test_battle_profile_content_replay as replay_fixture

COUNT_SOURCE_SHA256 = "50bf7d588bd41102ba7170f6a53ff9f65a22496b5d9ea13586496196a7cc2ac4"
REPLAY_SOURCE_SHA256 = "bafc8fd0cdd8350a85b3ca0cd0d91005d603d6db99b10359c401b50d083248f3"
REPLAY_FIXTURE_SHA256 = "f285dea2525bd2ad796391f8d53eebaf4d206e20660e9de5e862c815aa4afd86"
NATIVE_CALL, NATIVE_RET, NATIVE_COUNT = 0x42f956, 0x42f95b, 0x426ef0
OLD_CALL = b"\xe8" + struct.pack("<i", NATIVE_COUNT - NATIVE_RET)
ROW = (NATIVE_CALL, OLD_CALL.hex(), "unit", "count_entry", 0, 0)
# Preserve every input and flag while reading only the three authored fields.
COUNT_STUB = bytes.fromhex("9c6089c20fb742040fb74a060fb65202619dc3")
CACHE = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def arguments():
    return dict(content_replay_module=replay_tool,
                content_replay_kwargs=replay_fixture.arguments(),
                content_module=replay_fixture.content_tool, assembler_module=clip,
                template_source=(ROOT / tool.TEMPLATE).read_bytes())


def emit(profile="classic", resolution="800x600"):
    key = profile, resolution
    if key not in CACHE:
        prefix = replay_fixture.emit(profile, resolution)
        CACHE[key] = prefix + (tool._emit_code(*prefix, **arguments()),)
    return CACHE[key]


def source_closure():
    previous = replay_fixture.source_closure()
    for name, digest in ((tool.SOURCE, COUNT_SOURCE_SHA256),
                         (replay_tool.SOURCE, REPLAY_SOURCE_SHA256),
                         ("tools/test_battle_profile_content_replay.py", REPLAY_FIXTURE_SHA256)):
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError("frozen Count-entry dependency differs: " + name)
    names = set(previous) | {tool.SOURCE, "tools/test_battle_profile_count_entry.py"}
    return {name: sha((ROOT / name).read_bytes()) for name in sorted(names)}


def independent_contract(content, field, out):
    """Rebuild all bytes/typed fields without consulting new relocations.

    Only the actual SITE12 entry-to-payload prefix and capture_inputs-to-end
    private region are copied. Every private relative field is remapped; one
    authenticated proposed-native-return CMP changes value.
    """
    parent = dict(content.private_entries)
    site, entry, payload, pc, denied, fault, valid = content.body_receipts[12]
    assert site == 0x42f84a and entry < pc < payload < valid < fault < denied
    lo, hi = entry-content.base_va, payload-content.base_va
    prefix = content.code[lo:hi]
    private_lo, private_hi = parent["capture_inputs"], content.base_va+len(content.code)
    private_offset = private_lo-content.base_va
    private = content.code[private_offset:]
    changed = [r for r in content.relocations if private_offset <= r.offset and
               (r.kind, r.target, r.purpose) ==
               ("abs32", 0x42f84f, "fixed proposed body CALL return PC")]
    assert len(changed) == 1
    changed = changed[0].offset
    assert content.code[changed-2:changed] == b"\x81\xf8"
    code, fields, pending = bytearray(prefix), {}, []

    def mark(at, kind, target, purpose):
        assert at not in fields
        fields[at] = kind, target, purpose

    def raw(text):
        code.extend(bytes.fromhex(text))

    def word(value):
        code.extend(struct.pack("<I", value & 0xffffffff))

    def unsafe(op):
        raw(op); pending.append(len(code)); word(0)

    def absolute(value, purpose):
        mark(len(code), "abs32", value, purpose); word(value)

    def relative(value, purpose):
        mark(len(code), "rel32", value, purpose); word(0)

    suffix = out.base_va+len(code)
    raw("39ec"); unsafe("0f85")
    raw("8b95"); word(820)
    raw("81fa"); absolute(NATIVE_RET, "natural Count draw CALL return")
    unsafe("0f85")
    raw("8b85"); word(428)
    raw("8bbd"); word(372)
    raw("29f881c0"); word(-852)
    raw("81f8"); word(682); unsafe("0f83")
    raw("31d2b91f000000f7f185d2"); unsafe("0f85")
    raw("8bb5"); word(428)
    raw("0fb746048b8f"); word(804)
    raw("39c8"); unsafe("0f83")
    raw("0fb756068b8f"); word(800)
    raw("39ca"); unsafe("0f83")
    raw("81c4"); word(784); raw("619de9")
    relative(NATIVE_COUNT, "native_count_entry")
    guard = out.base_va+len(code)
    raw("8d4c240439cd"); unsafe("0f85")
    raw("8b042481f8")
    actual_pc = out.base_va+pc-entry
    absolute(actual_pc, "actual Count adapter admission CALL return")
    unsafe("0f85")
    raw("e9"); guard_target = len(code); word(0)
    terminal = out.base_va+len(code)
    raw("0f0b")
    clone = out.base_va+len(code)
    private_start = len(code)
    code.extend(private)
    prefix_roles = []
    for row in content.relocations:
        if lo <= row.offset < hi:
            assert row.kind == "rel32" and row.offset+4 <= hi
            if row.target == parent["capture_inputs"]:
                target, purpose = clone, "count_entry_internal:clone.capture_inputs"
            elif row.target == parent["admit_body"]:
                assert row.offset == pc-content.base_va-4
                target, purpose = guard, "count_entry_internal:admission_guard"
            else:
                assert row.target == denied and row.offset == hi-4
                target, purpose = terminal, "count_entry_internal:unsafe_control"
            prefix_roles.append(purpose)
            mark(row.offset-lo, "rel32", target, purpose)
        elif private_offset <= row.offset < len(content.code):
            assert row.offset+4 <= len(content.code)
            at = private_start+row.offset-private_offset
            if row.kind == "abs32":
                target = NATIVE_RET if row.offset == changed else row.target
                purpose = "count_entry_private_native_return" if row.offset == changed else (
                    "count_entry_private_absolute:"+row.purpose)
                mark(at, "abs32", target, purpose)
            else:
                assert row.kind == "rel32"
                if private_lo <= row.target < private_hi:
                    target, purpose = clone+row.target-private_lo, "count_entry_internal:private"
                else:
                    assert row.target == dict(field.private_entries)["check_invocation"]
                    assert row.purpose == "private current V2 complete content receipt"
                    assert content.code[row.offset-1] == 0xe8
                    target, purpose = row.target, "count_entry_field_receipt"
                mark(at, "rel32", target, purpose)
    assert sorted(prefix_roles) == sorted(("count_entry_internal:clone.capture_inputs",
        "count_entry_internal:admission_guard", "count_entry_internal:unsafe_control"))
    cloned_admit = clone+parent["admit_body"]-private_lo
    mark(guard_target, "rel32", cloned_admit, "count_entry_internal:clone.admit_body")
    for at in pending:
        mark(at, "rel32", terminal, "count_entry_internal:unsafe_control")
    for at, (kind, target, _) in fields.items():
        struct.pack_into("<I", code, at, target if kind == "abs32" else
                         (target-out.base_va-at-4) & 0xffffffff)
    cloned_private = tuple(("private_unsafe_control" if name == "unsafe_control" else name,
                            clone+va-private_lo) for name, va in content.private_entries
                           if private_lo <= va < private_hi)
    assert out.entries == (("count_entry", out.base_va),)
    assert out.private_entries == cloned_private+(("admission_guard", guard), ("unsafe_control", terminal))
    assert out.prefix_receipt == (NATIVE_CALL, site, entry, payload, pc, denied, sha(prefix),
                                  out.base_va, suffix, actual_pc)
    assert out.private_clone_receipt == (private_lo, private_hi, sha(private), clone,
        out.base_va+len(code), changed, private_start+changed-private_offset)
    assert out.guard_receipts == (guard, actual_pc, cloned_admit, clone, terminal)
    assert out.source_blocks == (("unit_admission_prefix", entry, payload, sha(prefix), out.base_va, suffix),
        ("private_admission", private_lo, private_hi, sha(private), clone, out.base_va+len(code)))
    assert out.planned_hooks == ((NATIVE_CALL, OLD_CALL, out.base_va, "count_entry", ()),)
    assert out.code == bytes(code)
    return fields


class Machine(replay_fixture.Machine):
    def __init__(self, tools, profile="classic", resolution="800x600", delta=0):
        # Track actual active parent code observers, not broad guessed ranges.
        hooks, deleted = [], set()
        original_add, original_delete = tools[0].Uc.hook_add, tools[0].Uc.hook_del

        def add(cpu, kind, *args, **kwargs):
            handle = original_add(cpu, kind, *args, **kwargs)
            hooks.append((kind, handle, args, kwargs))
            return handle

        def remove(cpu, handle):
            deleted.add(handle)
            return original_delete(cpu, handle)

        self.count_active = False
        with patch.object(tools[0].Uc, "hook_add", add), patch.object(tools[0].Uc, "hook_del", remove):
            super().__init__(tools, profile, resolution, delta)
        self.count_emission = emit(profile, resolution)[-1]
        raw = bytearray(self.count_emission.code)
        for row in self.count_emission.relocations:
            if row.kind == "abs32":
                struct.pack_into("<I", raw, row.offset, row.target+delta)
        self.cpu.mem_write(self.count_emission.base_va+delta, bytes(raw))
        self.loaded_code.append((self.count_emission.base_va+delta, bytes(raw)))
        self.unsafe_vas.update(va+delta for name, va in self.count_emission.private_entries if "unsafe" in name)
        content = emit(profile, resolution)[5]
        role, source_lo, source_hi, digest, clone_lo, clone_hi = self.count_emission.source_blocks[1]
        assert role == "private_admission" and source_hi-source_lo == clone_hi-clone_lo
        assert sha(content.code[source_lo-content.base_va:source_hi-content.base_va]) == digest
        excluded = []
        observer = replay_fixture.tile_fixture.content_fixture
        for start, end, _ in observer.tool._decode(content.code):
            source_va = content.base_va+start
            if not source_lo <= source_va < source_hi or content.code[start] != 0xf3:
                continue
            assert content.code[start:start+2] == b"\xf3\xaf"
            assert content.code[start-10] == 0xb9 and content.code[start-5] == 0xbf
            count = struct.unpack_from("<I", content.code, start-9)[0]
            pointer = struct.unpack_from("<I", content.code, start-4)[0]+delta
            pc = clone_lo+delta+source_va-source_lo
            self.scan_before[pc-5] = (pc+2, pointer, count)
            self.scan_after[pc+2] = (pointer, count)
            excluded.append((pc, pc+1))
        assert excluded
        replacements = []
        for kind, handle, args, kwargs in hooks:
            if kind == self.u.UC_HOOK_CODE and handle not in deleted:
                values, pieces = observer.observer_slices(args, kwargs, excluded, self.on_code)
                replacements.append((handle, values, pieces))
        self.count_hook_receipts = []
        for handle, values, pieces in replacements:
            self.cpu.hook_del(handle)
            for low, high in pieces:
                self.cpu.hook_add(self.u.UC_HOOK_CODE, values["callback"], values["user_data"],
                                  low, high, values["aux1"], values["aux2"])
            self.count_hook_receipts.append((values, pieces))
        assert replacements
        for left, right in excluded:
            assert not any(low <= left <= high or low <= right <= high
                           for _, pieces in self.count_hook_receipts for low, high in pieces)
            for pc in (left-5, right+1):
                assert any(low <= pc <= high for _, pieces in self.count_hook_receipts for low, high in pieces)
        self.cpu.mem_write(NATIVE_COUNT+delta, COUNT_STUB)
        self.cpu.ctl_remove_cache(NATIVE_COUNT+delta, NATIVE_COUNT+delta+len(COUNT_STUB))

    def on_code(self, cpu, address, size, data):
        if getattr(self, "count_active", False):
            if address == NATIVE_COUNT+self.delta:
                self.count_entries.append(({name: cpu.reg_read(reg) for name, reg in self.regs.items()},
                                           self.word(cpu.reg_read(self.regs["ESP"]))))
            if address == NATIVE_RET+self.delta:
                self.count_returns.append(address)
        super().on_code(cpu, address, size, data)

    def on_read(self, cpu, access, address, size, value, data):
        if getattr(self, "count_active", False):
            pc = cpu.reg_read(self.regs["EIP"])
            if NATIVE_COUNT+self.delta <= pc < NATIVE_COUNT+self.delta+len(COUNT_STUB):
                self.stub_reads.append((address, size))
            suffix = self.count_emission.prefix_receipt[-2]+self.delta
            guard = dict(self.count_emission.private_entries)["admission_guard"]+self.delta
            if suffix <= pc < guard:
                self.suffix_reads.append((address, size))
        super().on_read(cpu, access, address, size, value, data)

    def setup_count(self, *, record=21, via_adjacent=False, x=1, y=6):
        regs = self.setup_body(ROW, index=21, via_adjacent=via_adjacent)
        regs["EAX"] = self.WORLD+852+31*record
        self.cpu.mem_write(regs["EAX"]+2, b"\xd3")
        self.cpu.mem_write(regs["EAX"]+4, struct.pack("<HH", x, y))
        return regs

    def invoke_count(self, regs, *, flags=0xed7, call_pc=None):
        site = NATIVE_CALL+self.delta if call_pc is None else call_pc-5
        target = dict(self.count_emission.entries)["count_entry"]+self.delta
        self.cpu.mem_write(site, b"\xe8"+struct.pack("<i", target-site-5))
        self.cpu.ctl_remove_cache(site, site+5)
        self.stops = {NATIVE_RET+self.delta}
        self.native_stop = None; self.unsafe = False; self.active_scan = None
        self.reads = []; self.writes = []; self.content_reads = []; self.content_writes = []
        self.content_events = []; self.content_after_thread = False
        self.count_entries = []; self.count_returns = []; self.stub_reads = []; self.suffix_reads = []
        self.before_callbacks = len(self.callbacks); self.minimum_sp = regs["ESP"]
        for name, value in regs.items():
            self.cpu.reg_write(self.regs[name], value & 0xffffffff)
        self.cpu.reg_write(self.regs["EFLAGS"], flags)
        self.content_active = True; self.count_active = True
        try:
            self.cpu.emu_start(site, self.STOP+1, count=2000000)
        finally:
            self.count_active = False; self.content_active = False
        return {name: self.cpu.reg_read(reg) for name, reg in self.regs.items()}


class SourceTests(unittest.TestCase):
    def test_all36_independent_complete_prefix_private_bytes_operands_and_bounds(self):
        source_closure()
        context = replay_fixture.tile_fixture.content_fixture.parent_fixture.context
        for profile in context.PROFILES:
            for resolution in context.RESOLUTIONS:
                with self.subTest(profile=profile, resolution=resolution):
                    *prefix, out = emit(profile, resolution)
                    layout, field, content, parent = prefix[0], prefix[3], prefix[5], prefix[-1]
                    self.assertEqual(out.base_va, (parent.base_va+len(parent.code)+15)&~15)
                    self.assertLessEqual(out.base_va+len(out.code), layout.rx.va+layout.rx.size)
                    fields = independent_contract(content, field, out)
                    declared = {r.offset: (r.kind, r.target, r.purpose) for r in out.relocations}
                    self.assertEqual(len(declared), len(out.relocations))
                    self.assertEqual(declared, fields)
                    absolute = {at for at, row in fields.items() if row[0] == "abs32"}
                    self.assertIn(out.prefix_receipt[-2]-out.base_va+16, absolute)
                    self.assertIn(dict(out.private_entries)["admission_guard"]-out.base_va+17, absolute)
                    self.assertNotIn(5, absolute)
                    decoded = replay_fixture.decode(out.code, absolute)
                    starts = {start for start, *_ in decoded}
                    self.assertEqual({at for _, _, aa, _, _ in decoded for at in aa}, absolute)
                    self.assertEqual({at for _, _, _, rr, _ in decoded for at in rr},
                                     {at for at, row in fields.items() if row[0] == "rel32"})
                    for start, end, aa, rr, ss in decoded:
                        self.assertFalse({at for at, _ in ss} & set(declared))
                        for at in aa:
                            self.assertEqual(struct.unpack_from("<I", out.code, at)[0], declared[at][1])
                        for at in rr:
                            target = out.base_va+at+4+struct.unpack_from("<i", out.code, at)[0]
                            self.assertEqual(target, declared[at][1])
                            if out.base_va <= target < out.base_va+len(out.code):
                                self.assertIn(target-out.base_va, starts)
                    self.assertEqual(sum(r.purpose == "count_entry_private_native_return" for r in out.relocations), 1)

    def test_full_parent_and_source_receipt_substitutions_are_rejected(self):
        prefix = emit()
        for index in range(3, 10):
            value = prefix[index]
            for name in ("code", "relocations"):
                supplied = list(prefix[:-1]); supplied[index] = replace(value, **{name: getattr(value, name)[:-1]})
                with self.subTest(index=index, field=name), self.assertRaises(ValueError):
                    tool._emit_code(*supplied, **arguments())
        for name in ("body_receipts", "source_blocks", "planned_hooks", "entries", "private_entries"):
            supplied = list(prefix[:-1]); parent = supplied[-1]
            supplied[-1] = replace(parent, **{name: getattr(parent, name)[:-1]})
            with self.subTest(parent_field=name), self.assertRaises(ValueError):
                tool._emit_code(*supplied, **arguments())
        self.assertEqual(asdict(prefix[-2]), asdict(replay_fixture.emit()[-1]))

    def test_closed_receipts_native_pc_and_scalar_roles_cannot_be_forged(self):
        prefix = emit(); field, content, out = prefix[3], prefix[5], prefix[-1]
        forged = clip.Relocation(5, "abs32", 784, "count_entry_private_absolute:forged")
        with self.assertRaises(ValueError):
            tool._operand_inventory(replace(out, relocations=out.relocations+(forged,)), content, field)
        for name in ("prefix_receipt", "private_clone_receipt", "guard_receipts", "source_blocks", "planned_hooks", "private_entries"):
            value = getattr(out, name)
            altered = value[:-1] if name == "planned_hooks" else value[::-1]
            self.assertNotEqual(altered, value, "negative fixture must change its input")
            with self.subTest(field=name), self.assertRaises(ValueError):
                tool._operand_inventory(replace(out, **{name: altered}), content, field)
        for at in (0, out.private_clone_receipt[-1], out.prefix_receipt[-2]-out.base_va+16,
                   dict(out.private_entries)["admission_guard"]-out.base_va+17):
            raw = bytearray(out.code); raw[at] ^= 1
            with self.subTest(offset=at), self.assertRaises(ValueError):
                tool._operand_inventory(replace(out, code=bytes(raw)), content, field)

    def test_authored_native_call_and_span_authentication_not_original_proof(self):
        template = arguments()["template_source"]
        old, prologue = tool._native_contract(template)
        self.assertEqual(old, OLD_CALL)
        self.assertEqual(prologue, bytes.fromhex("53515256575583ec0489c7"))
        with self.assertRaises(ValueError):
            tool._native_contract(template[:-1])
        # Explicit synthetic digest adapter isolates window/span authentication.
        # It is neither a real native body nor an original-executable admission.
        span = prologue+b"\x90"*(0x85-len(prologue))
        origin = 0x426000
        image = bytearray(0x10000)
        image[NATIVE_CALL-origin:NATIVE_CALL-origin+5] = OLD_CALL
        image[NATIVE_COUNT-origin:NATIVE_COUNT-origin+len(span)] = span
        image = bytes(image)
        mapper = SimpleNamespace(file_offset=lambda image, va, count: va-origin)
        digest = lambda raw: tool.COUNT_SHA256 if raw == span else sha(raw)
        with patch.object(tool, "_sha", digest):
            tool._authenticate_native(image, image, mapper, template_source=template)
            for target in (0, 1):
                for at in (NATIVE_CALL-origin, NATIVE_COUNT-origin, NATIVE_COUNT-origin+0x84):
                    bad = bytearray(image); bad[at] ^= 1
                    supplied = [image, image]; supplied[target] = bytes(bad)
                    with self.subTest(target=target, offset=at), self.assertRaises(ValueError):
                        tool._authenticate_native(*supplied, mapper, template_source=template)

    def test_public_alias_capture_closure_and_explicit_false_claims(self):
        def poison(*args, **kwargs):
            raise AssertionError("mutable issuer alias invoked")
        with patch.object(tool, "_issue", poison), patch.object(replay_tool, "_issue", poison):
            for original in (b"", b"authored PE", bytearray(b"authored PE"), None):
                with self.assertRaisesRegex(ValueError, "original"):
                    tool.emit_count_entry(original, "classic", "800x600")
        for name in ("installed", "native_executed", "native_count_instruction_execution_verified",
                     "native_count_parity_verified", "native_count_early_reads_adapted", "non_draw_count_admission",
                     "native_sentinel_record_verified", "runtime_verified", "manual_input_proof", "promotion_ready"):
            self.assertIn(name, tool.FALSE_CLAIMS)
        tree = ast.parse((ROOT/tool.SOURCE).read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and
                             n.func.attr in ("write_bytes", "write_text") for n in ast.walk(tree)))
        self.assertEqual(tool.HELPER_BYTES, 784)
        self.assertEqual(tool.NATIVE_RETURN, 820)


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools = replay_fixture.tile_fixture.content_fixture.parent_fixture.field_fixture.routing_fixture.lifetime.prior_fixture.machine_tools()
        if cls.tools is None:
            raise ImportError("required Unicorn CPU interpreter unavailable")

    def make(self, profile="classic", delta=0, mode=0):
        return Machine(self.tools, profile, delta=delta).prepare(columns=2).begin(mode)

    def assert_healthy(self, m, regs, *, flags=0xed7):
        owner, tiles = m.record(), list(m.tiles)
        scans = m.scan_observations
        actual = m.invoke_count(regs, flags=flags)
        self.assertEqual(len(m.count_entries), 1)
        entered, ret = m.count_entries[0]
        self.assertEqual(ret, NATIVE_RET+m.delta)
        self.assertEqual(entered["ESP"], regs["ESP"]-4)
        for name in regs:
            self.assertEqual(entered[name], regs[name] if name != "ESP" else regs[name]-4, name)
            self.assertEqual(actual[name], regs[name], name)
        self.assertEqual(entered["EFLAGS"]&m.MASK, flags&m.MASK)
        self.assertEqual(actual["EFLAGS"]&m.MASK, flags&m.MASK)
        self.assertEqual(m.count_returns, [NATIVE_RET+m.delta])
        self.assertEqual(m.native_stop, NATIVE_RET+m.delta)
        self.assertEqual([r for r in m.stub_reads if m.WORLD <= r[0] < m.WORLD+0xf7c],
                         [(regs["EAX"]+4, 2), (regs["EAX"]+6, 2), (regs["EAX"]+2, 1)])
        self.assertEqual(m.callbacks[m.before_callbacks:], ["thread"])
        self.assertGreater(m.scan_observations, scans)
        self.assertIsNone(m.active_scan)
        self.assertFalse(m.unsafe)
        self.assertEqual(m.record(), owner); self.assertEqual(m.tiles, tiles)
        helper = regs["ESP"]-824
        for at, size in m.content_writes:
            self.assertTrue(helper-44 <= at and at+size <= helper+824, (hex(at), size))
        for at, raw in m.loaded_code:
            self.assertEqual(bytes(m.cpu.mem_read(at, len(raw))), raw)

    def assert_terminal(self, m, regs, **options):
        owner, tiles = m.record(), list(m.tiles)
        with self.assertRaises(self.tools[0].UcError):
            m.invoke_count(regs, **options)
        pc = m.cpu.reg_read(m.regs["EIP"])
        self.assertIn(pc, m.unsafe_vas)
        self.assertEqual(bytes(m.cpu.mem_read(pc, 2)), b"\x0f\x0b")
        self.assertEqual(m.count_entries, []); self.assertEqual(m.count_returns, [])
        self.assertEqual(m.stub_reads, []); self.assertIsNone(m.native_stop)
        self.assertEqual(m.record(), owner); self.assertEqual(m.tiles, tiles)
        self.assertFalse(any(m.lease_frame <= at < m.lease_frame+192 for at, _ in m.content_writes))

    def test_direct_count_stub_natural_return_all_profiles_bases_modes_and_ancestry(self):
        context = replay_fixture.tile_fixture.content_fixture.parent_fixture.context
        for profile in context.PROFILES:
            for delta in (0, 0x30000):
                for mode in (0, 1):
                    m = self.make(profile, delta, mode)
                    for via in (False, True):
                        for record in (0, 7, 21):
                            with self.subTest(profile=profile, delta=delta, mode=mode, via=via, record=record):
                                regs = m.setup_count(record=record, via_adjacent=via,
                                                     x=0 if record == 0 else 1,
                                                     y=0 if record == 0 else 2 if record == 7 else 6)
                                self.assert_healthy(m, regs, flags=0x246 if via else 0xed7)
                    del m; gc.collect()

    def test_invalid_record_membership_and_unsigned_coordinates_precede_count(self):
        for fault in ("misaligned", "negative", "sentinel", "one_past", "x_edge", "y_edge", "unsigned_x"):
            m = self.make("framed", 0x30000)
            regs = m.setup_count()
            if fault == "misaligned": regs["EAX"] += 1
            elif fault == "negative": regs["EAX"] = m.WORLD+852-1
            elif fault == "sentinel": regs["EAX"] = m.WORLD+821
            elif fault == "one_past": regs["EAX"] = m.WORLD+852+31*22
            elif fault == "x_edge": m.cpu.mem_write(regs["EAX"]+4, struct.pack("<H", 2))
            elif fault == "y_edge": m.cpu.mem_write(regs["EAX"]+6, struct.pack("<H", 7))
            else: m.cpu.mem_write(regs["EAX"]+4, struct.pack("<H", 0xffff))
            self.assert_terminal(m, regs)
            if fault in ("misaligned", "negative", "sentinel", "one_past"):
                self.assertNotIn((regs["EAX"]+4, 2), m.suffix_reads)
                self.assertNotIn((regs["EAX"]+6, 2), m.suffix_reads)
            del m; gc.collect()

    def test_foreign_and_non_draw_natural_call_receipts_deny_before_callback(self):
        for pc in (NATIVE_RET+0x20, 0x426f95, 0x431d7a):
            m = self.make("modalwidgets", 0x30000)
            regs = m.setup_count()
            self.assert_terminal(m, regs, call_pc=pc+m.delta)
            self.assertEqual(m.callbacks[m.before_callbacks:], [])
            self.assertEqual(m.cached_reads(), [])
            del m; gc.collect()

    def test_actual_intrinsic_return_and_stack_corruption_deny_before_callback(self):
        for fault in ("return", "stack"):
            m = self.make("completehd", 0x30000)
            regs = m.setup_count()
            guard = dict(m.count_emission.private_entries)["admission_guard"]+m.delta
            seen = []
            def corrupt(mm, address):
                if address == guard:
                    sp = mm.cpu.reg_read(mm.regs["ESP"])
                    if fault == "return": mm.put(sp, mm.word(sp)^4)
                    else: mm.cpu.reg_write(mm.regs["ESP"], sp-4)
                    seen.append(sp)
            m.instruction_mutation = corrupt
            self.assert_terminal(m, regs)
            self.assertEqual(len(seen), 1)
            self.assertEqual(m.callbacks[m.before_callbacks:], [])
            self.assertEqual(m.cached_reads(), [])
            del m; gc.collect()

    def test_latched_loss_status_and_owner_phase_precede_poisoned_cached_reads(self):
        for fault in ("loss", "status", "phase"):
            m = self.make("framed", 0x30000)
            regs = m.setup_count()
            if fault == "phase": m.put(m.state_va, 3)
            else: m.put(m.lease_frame+(44 if fault == "loss" else 48), 2)
            m.protect_cached(m.u.UC_PROT_NONE)
            self.assert_terminal(m, regs)
            self.assertEqual(m.callbacks[m.before_callbacks:], [])
            self.assertEqual(m.cached_reads(), [])
            del m; gc.collect()

    def test_callback_control_descriptor_and_current_coordinate_loss_precede_count(self):
        for fault in ("descriptor", "helper", "intrinsic_word", "ancestor", "coordinate"):
            m = self.make("completehd", 0x30000)
            regs = m.setup_count(); seen = []
            def corrupt(mm, label):
                if label == "thread":
                    helper = regs["ESP"]-824
                    if fault == "coordinate":
                        mm.cpu.mem_write(regs["EAX"]+4, struct.pack("<H", 2))
                        seen.append(regs["EAX"]+4)
                    else:
                        at = (mm.lease_frame+60 if fault == "descriptor" else helper+812 if fault == "helper"
                              else helper-4 if fault == "intrinsic_word" else mm.unit_sp-28)
                        mm.put(at, mm.word(at)^4); seen.append(at)
                        mm.protect_cached(mm.u.UC_PROT_NONE)
            m.mutation = corrupt
            self.assert_terminal(m, regs)
            self.assertEqual(len(seen), 1)
            self.assertEqual(m.callbacks[m.before_callbacks:], ["thread"])
            if fault == "coordinate":
                self.assertIn((regs["EAX"]+4, 2), m.suffix_reads)
            else:
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
        raise ValueError("Count-entry source closure changed during tests")
    if not result.wasSuccessful() or result.skipped or result.testsRun != TEST_COUNT:
        raise AssertionError("uninstalled Count-entry fixture failures")
    return result.testsRun


if __name__ == "__main__":
    if len(sys.argv) > 1:
        unittest.main()
    else:
        run_tests()
