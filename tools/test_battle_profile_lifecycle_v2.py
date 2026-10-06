#!/usr/bin/env python3
"""Fresh lifecycle source and synthetic CPU fixtures; no native or outputs.

Canonical production authority is not the explicit synthetic layout below.
Allocator/constructor/destructor/thread callbacks are models, not Windows/game
execution. --original-backed adds one bounded canonical parent/emission in RAM.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, replace
import hashlib
import importlib
from pathlib import Path
import struct
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import battle_profile_lifecycle_v2 as tool
from src.patcher import battle_profile_context_v2 as context
from src.patcher import battle_profile_lifecycle as frozen
from src.patcher import partial_tile_clip as clip
from src.patcher import framed_modal_canvas as native
import test_battle_profile_context_v2 as allocation_fixture
import test_battle_profile_lifecycle as prior_fixture

ORIGINAL = None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@contextmanager
def issuer():
    raw = (ROOT / tool.SOURCE).read_bytes()
    name = "_lifecycle_v2_synthetic_" + uuid.uuid4().hex
    module = ModuleType(name)
    module.__file__ = str(ROOT / tool.SOURCE)
    module.__loaded_source_sha256__ = sha(raw)
    module.__canonical_lifecycle_v2_issuer__ = True
    sys.modules[name] = module
    try:
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
        yield module
    finally:
        if sys.modules.get(name) is not module:
            raise AssertionError("synthetic issuer replaced")
        del sys.modules[name]


def synthetic_layout(profile="classic", resolution="1024x768"):
    with allocation_fixture.synthetic_issuer() as source:
        _, _, _, layout = allocation_fixture.synthetic_context(source, profile, resolution)
    rx = replace(layout.rx, va=0x10000000, rva=0xFC00000)
    rw = replace(layout.rw, va=0x10040000, rva=0xFC40000)
    spans = tuple(row for row in layout.protected_spans if row.role.startswith("parent:"))
    spans += tuple(replace(row, va=0x10000000 if row.role == "future_rx_reservation" else
        0x10040000 if row.role == "future_battle_state_page" else 0x10041000)
        for row in layout.protected_spans if not row.role.startswith("parent:"))
    return replace(layout, rx=rx, rw=rw, battle_state_va=rw.va, provider_va=rw.va + 4096,
        future_image_size=0xFC50000, protected_spans=spans)


def emission(layout, source=None):
    own = tool if source is None else source
    return own._emit_code(layout, template_source=(ROOT / tool.TEMPLATE).read_bytes(),
        template_module=frozen, assembler_module=clip)


def decode(code):
    """Independent bounded decoder for this authored x86 instruction dialect."""
    rows = []
    cursor = 0
    while cursor < len(code):
        start, abs_fields, rel_fields = cursor, [], []
        opcode = code[cursor]; cursor += 1
        if opcode in (0x9C, 0x9D, 0x60, 0x61, 0xFC, 0xC3, 0x40, 0x48, 0x55, 0x56, 0x57):
            pass
        elif opcode == 0xF3:
            assert code[cursor] in (0xAB, 0xAF); cursor += 1
        elif 0xB8 <= opcode <= 0xBF:
            abs_fields.append((cursor, False)); cursor += 4
        elif opcode in (0xE8, 0xE9):
            rel_fields.append(cursor); cursor += 4
        elif opcode == 0x0F:
            assert code[cursor] in (0x82, 0x83, 0x84, 0x85, 0x87); cursor += 1
            rel_fields.append(cursor); cursor += 4
        elif opcode in (0x2D, 0x3D):
            abs_fields.append((cursor, False)); cursor += 4
        elif opcode in (0x81, 0x83, 0x8B, 0x89, 0x8D, 0x3B, 0x39, 0x85, 0xF7, 0xFF, 0xC7, 0x31):
            modrm = code[cursor]; cursor += 1
            mode, rm = modrm >> 6, modrm & 7
            if mode != 3 and rm == 4:
                sib = code[cursor]; cursor += 1
                if mode == 0 and sib & 7 == 5:
                    abs_fields.append((cursor, True)); cursor += 4
            if mode == 0 and rm == 5:
                abs_fields.append((cursor, True)); cursor += 4
            elif mode == 1:
                cursor += 1
            elif mode == 2:
                cursor += 4
            if opcode in (0x81, 0xC7) or opcode == 0xF7 and (modrm >> 3) & 7 == 0:
                abs_fields.append((cursor, False)); cursor += 4
            elif opcode == 0x83:
                cursor += 1
        else:
            raise AssertionError((hex(start), hex(opcode)))
        assert start < cursor <= len(code), (start, cursor)
        rows.append((start, cursor, tuple(abs_fields), tuple(rel_fields)))
    return rows


def relocation_oracle(out, layout):
    rows = decode(out.code)
    starts = {row[0] for row in rows}
    declared_abs = {row.offset for row in out.relocations if row.kind == "abs32"}
    declared_rel = {row.offset for row in out.relocations if row.kind == "rel32"}
    recognized_abs, decoded_rel = set(), set()
    # Classify exact instruction/operand roles, never numeric VA resemblance.
    # A numeric pixel count may coincide with an address (3440*1440 does).
    modal = [row for row in layout.protected_spans if row.role == "parent:.hdstate"]
    w,h=map(int,layout.resolution.split("x"))
    scalar_values=set(range(10)) | {128,156,168,172,188,216,384,640,480,3964,4096,
        65536,262144,307200,76800,16352,992,0x10000,layout.rx.rva,w*h,
        w|(h<<16),640|(480<<16)}
    scalar_values |= {0x80000000-size for size in (8,188,w*h,168,307200,3964)}
    pointer_values={0x400000,0x51D4C0,layout.rx.va,layout.rw.va}
    pointer_values |= {row.va for row in modal}
    for start,end,absolute,relative in rows:
        opcode=out.code[start]
        for at, memory_operand in absolute:
            value = struct.unpack_from("<I", out.code, at)[0]
            is_address=memory_operand
            if not memory_operand:
                if opcode == 0xBF:
                    assert value in {layout.rw.va+128} | {row.va+128 for row in modal}
                    is_address=True
                elif opcode == 0xB9 and out.code[end:end+1] not in (b"\xbf",b"\xf3"):
                    assert value in pointer_values
                    is_address=True
                elif opcode == 0x3D:
                    assert value == 0x51D4C0
                    is_address=True
                elif opcode in (0x81,0xC7):
                    modrm=out.code[start+1]
                    if modrm >> 6 == 2 and struct.unpack_from("<I",out.code,start+2)[0] == 0xB8:
                        assert value == 0x50EE24
                        is_address=True
                    elif modrm == 0x3D:
                        target=struct.unpack_from("<I",out.code,start+2)[0]
                        if target == 0x5199D8 or target == layout.rw.va+68 and value != 0:
                            assert value in (0x40AD40,0x42E8B0)
                            is_address=True
                        elif target == 0x51D4C0+0xB8:
                            assert value == 0x50EEC4
                            is_address=True
                if not is_address:
                    assert value in scalar_values,(hex(start),hex(value),hex(opcode))
            if is_address:
                recognized_abs.add(at)
        for at in relative:
            decoded_rel.add(at)
            target = out.base_va + at + 4 + struct.unpack_from("<i", out.code, at)[0]
            if out.base_va <= target < out.base_va + len(out.code):
                assert target - out.base_va in starts, (at, target)
    assert declared_abs == recognized_abs, (declared_abs - recognized_abs, recognized_abs - declared_abs)
    assert declared_rel == decoded_rel, (declared_rel - decoded_rel, decoded_rel - declared_rel)
    assert all(va - out.base_va in starts for _, va in out.entries)
    native_transfers = {
        "owned private scalar destructor": (0x403E50,0xE8),
        "nonfatal private header allocation": (0x473FF0,0xE8),
        "nonfatal private pixel allocation": (0x473FF0,0xE8),
        "nonallocating native base constructor": (0x401E00,0xE8),
        "rollback uncommitted private pixels": (0x4740DD,0xE8),
        "rollback uncommitted private header": (0x4740DD,0xE8),
        "native root continuation": (0x42E9E9,0xE9),
        "original null/fatal predicate continuation": (0x42EC97,0xE9),
        "original battle allocation free, unchanged CALL return": (0x4740DD,0xE9),
        "native pops and RET4 continuation": (0x42F5B9,0xE9),
    }
    seen_native = set()
    for row in out.relocations:
        expected = row.target if row.kind == "abs32" else row.target - out.base_va - row.offset - 4
        assert struct.unpack_from("<I", out.code, row.offset)[0] == expected & 0xFFFFFFFF
        if row.kind == "rel32":
            if out.base_va <= row.target < out.base_va + len(out.code):
                assert row.purpose.startswith("v2_owned_branch:")
            else:
                assert row.purpose in native_transfers
                target, opcode = native_transfers[row.purpose]
                assert row.target == target and out.code[row.offset-1] == opcode
                seen_native.add(row.purpose)
    assert seen_native == set(native_transfers)
    return len(rows), len(declared_abs), len(declared_rel)


class SourceTests(unittest.TestCase):
    def test_registration_only_repair_preserves_all36_complete_emissions(self):
        # Reconstruct the exact observed pre-admission producer in RAM. The
        # digest prevents this regression from masking another source change.
        current = (ROOT / tool.SOURCE).read_bytes().decode("utf-8")
        replacements = (
            ('            _require(sys.modules.setdefault(module.__name__, module) is module,\n'
             '                     "private lifecycle V2 namespace occupied")\n', ''),
            ('            owned[module.__name__] = module\n',
             '            owned[module.__name__] = module\n            sys.modules[module.__name__] = module\n'),
            ('            _require(sys.modules.setdefault(full, module) is module,\n'
             '                     "private lifecycle V2 namespace occupied")\n'
             '            owned[full] = module\n',
             '            owned[full] = module; sys.modules[full] = module\n'),
            ('    if registry.setdefault(name,module) is not module:\n'
             '        raise rejection("canonical lifecycle V2 issuer namespace occupied")\n',
             '    registry[name]=module\n'),
        )
        for after,before in replacements:
            self.assertEqual(current.count(after),1)
            current = current.replace(after,before)
        baseline = current.encode("utf-8")
        self.assertEqual(sha(baseline),"8721592d064d1eaaa4fcf35774c9e0ba3c069e57c3e7ee9b20aa5c56dd8516ad")
        name = "_lifecycle_v2_exact_baseline_" + uuid.uuid4().hex
        before = ModuleType(name)
        before.__file__ = str(ROOT / tool.SOURCE)
        before.__loaded_source_sha256__ = sha(baseline)
        before.__canonical_lifecycle_v2_issuer__ = True
        self.assertIs(sys.modules.setdefault(name,before),before)
        try:
            exec(compile(baseline,before.__file__,"exec"),before.__dict__)
            for profile in context.PROFILES:
                for resolution in context.RESOLUTIONS:
                    with self.subTest(profile=profile,resolution=resolution):
                        layout=synthetic_layout(profile,resolution)
                        old,new=emission(layout,before),emission(layout)
                        self.assertEqual(asdict(old),asdict(new))
                        self.assertEqual(relocation_oracle(old,layout),relocation_oracle(new,layout))
        finally:
            self.assertIs(sys.modules.get(name),before)
            del sys.modules[name]

    def test_all36_deterministic_fresh_addresses_complete_decoded_relocations_and_budget(self):
        for profile in context.PROFILES:
            for resolution in context.RESOLUTIONS:
                with self.subTest(profile=profile, resolution=resolution):
                    layout = synthetic_layout(profile, resolution)
                    first, second = emission(layout), emission(layout)
                    self.assertEqual(first, second)
                    self.assertEqual(first.state_va, 0x10040000)
                    self.assertEqual(first.base_va, 0x10000000)
                    self.assertLess(len(first.code), 0x40000)
                    relocation_oracle(first, layout)
                    for row in first.relocations:
                        if row.purpose.startswith("state.") or "own state" in row.purpose:
                            self.assertTrue(0x10040000 <= row.target < 0x10040080)
                        if row.purpose == "restrictive zero inherited modal tail":
                            self.assertEqual(row.target, next(s.va + 128 for s in layout.protected_spans if s.role == "parent:.hdstate"))

    def test_bad_allocation_caps_layout_aliases_templates_and_relocations_reject(self):
        layout = synthetic_layout("modalwidgets")
        mutations = [replace(layout, rw=replace(layout.rw, va=layout.rx.va + 0x20000)),
            replace(layout, rx=replace(layout.rx, size=0x80000)), replace(layout, provider_schema="forged"),
            replace(layout, provider_reservation_bytes=61441), replace(layout, battle_state_bytes=4096),
            replace(layout, protected_spans=tuple(s for s in layout.protected_spans if s.role != "parent:.hdstate"))]
        for forged in mutations:
            with self.assertRaises(ValueError):
                emission(forged)
        with self.assertRaisesRegex(ValueError, "template differs"):
            tool._emit_code(layout, template_source=(ROOT / tool.TEMPLATE).read_bytes() + b"\n",
                template_module=frozen, assembler_module=clip)
        out = emission(layout)
        bad = replace(out, relocations=out.relocations[1:])
        with self.assertRaises(AssertionError):
            relocation_oracle(bad, layout)
        bad = replace(out, relocations=(replace(out.relocations[0], target=out.relocations[0].target + 4),) + out.relocations[1:])
        with self.assertRaises(ValueError):
            tool._validate_emission(bad, layout, clip)
        native_row = next(row for row in out.relocations if row.purpose == "nonfatal private header allocation")
        code = bytearray(out.code)
        substituted = replace(native_row, target=native_row.target + 4)
        struct.pack_into("<i",code,native_row.offset,substituted.target-out.base_va-native_row.offset-4)
        substituted_rows = tuple(substituted if row is native_row else row for row in out.relocations)
        # Resealed byte/metadata agreement cannot choose another native target.
        with self.assertRaises(AssertionError):
            relocation_oracle(replace(out,code=bytes(code),relocations=substituted_rows),layout)

    def test_captured_production_rejects_fake_original_and_private_marker(self):
        with patch.object(tool, "_issue", return_value=object()), \
             patch.object(tool, "_modules", side_effect=AssertionError("public module alias")), \
             patch.object(tool, "_snapshot", return_value={}), \
             patch.object(tool, "_sha", return_value=tool.BASE_SHA256), \
             patch.object(tool, "ROOT", Path("C:/forged")), \
             patch.object(tool, "SOURCE", "forged.py"):
            with self.assertRaisesRegex(ValueError, "exact original"):
                tool.emit_lifecycle_v2(b"fake", "classic", "1024x768")
        with issuer() as private, self.assertRaisesRegex(ValueError, "captured canonical"):
            private.emit_lifecycle_v2(b"fake", "classic", "1024x768")

    def test_pinned_private_sources_and_namespaces_ignore_public_producers(self):
        with issuer() as own:
            snapshot = own._snapshot()
            before = set(sys.modules)
            with patch.object(context, "build_allocation_context", side_effect=AssertionError("public context")), \
                 patch.object(frozen, "_emit_code", side_effect=AssertionError("public template")), \
                 patch.object(clip, "_Assembler", side_effect=AssertionError("public assembler")):
                with own._modules(snapshot) as modules:
                    layout = synthetic_layout()
                    out = own._emit_code(layout, template_source=snapshot[tool.TEMPLATE][0],
                        template_module=modules[tool.TEMPLATE], assembler_module=modules[tool.CLIP])
                    self.assertGreater(len(out.code), 0)
            self.assertEqual(set(sys.modules), before)
            own._unchanged(snapshot)
            damaged = dict(snapshot); name = next(iter(damaged)); raw, stamp = damaged[name]
            damaged[name] = raw + b"\n", stamp
            with self.assertRaisesRegex(ValueError, "closure changed"):
                own._unchanged(damaged)

    def test_private_namespace_replacement_and_removal_reject_without_deleting_foreign_module(self):
        for replacement in (None, ModuleType("foreign_lifecycle_v2_test")):
            with self.subTest(replacement=replacement), issuer() as own:
                snapshot = own._snapshot()
                before = set(sys.modules)
                target = None
                try:
                    with self.assertRaisesRegex(ValueError, "namespace identity changed"):
                        with own._modules(snapshot) as modules:
                            target = modules[tool.TEMPLATE].__name__
                            if replacement is None:
                                del sys.modules[target]
                            else:
                                sys.modules[target] = replacement
                    self.assertIs(sys.modules.get(target), replacement)
                    self.assertEqual(set(sys.modules) - before,
                                     set() if replacement is None else {target})
                finally:
                    if target is not None and sys.modules.get(target) is replacement:
                        sys.modules.pop(target, None)

    def test_occupied_uuid_names_reject_and_preserve_foreign_modules_and_attributes(self):
        fixed=SimpleNamespace(hex="lifecycle_v2_collision_fixture")
        prefix="_battle_lifecycle_v2_" + fixed.hex
        candidates=(prefix,prefix+".src",prefix+".src.patcher",
                    prefix+".src.patcher.battle_profile_lifecycle",
                    "_battle_lifecycle_v2_issuer_" + fixed.hex)
        for name in candidates:
            with self.subTest(name=name), issuer() as own:
                snapshot=own._snapshot()
                self.assertNotIn(name,sys.modules)
                foreign=ModuleType(name)
                foreign.__path__=["foreign/retained/path"]
                foreign.retained_marker=object()
                sys.modules[name]=foreign
                attributes=dict(foreign.__dict__)
                registry=dict(sys.modules)
                try:
                    with patch.object(own.uuid,"uuid4",return_value=fixed):
                        with self.assertRaisesRegex(ValueError,"namespace occupied"):
                            if name.startswith("_battle_lifecycle_v2_issuer_"):
                                own._production_factory()
                            else:
                                with own._modules(snapshot):
                                    self.fail("occupied namespace admitted")
                    self.assertEqual(set(sys.modules),set(registry))
                    self.assertTrue(all(sys.modules[key] is value for key,value in registry.items()))
                    self.assertEqual(set(foreign.__dict__),set(attributes))
                    self.assertTrue(all(foreign.__dict__[key] is value for key,value in attributes.items()))
                finally:
                    if sys.modules.get(name) is foreign:
                        del sys.modules[name]

    def test_source_reader_rejects_reparse_and_changed_bytes_without_mutating_files(self):
        with issuer() as own:
            path = ROOT / tool.SOURCE
            expected = path.read_bytes()
            with patch.object(Path, "is_symlink", return_value=True):
                with self.assertRaisesRegex(ValueError, "reparse"):
                    own._read(path, ROOT)
            real_read = Path.read_bytes
            def short_read(selected):
                value = real_read(selected)
                return value[:-1] if selected == path else value
            with patch.object(Path, "read_bytes", new=short_read):
                with self.assertRaisesRegex(ValueError, "changed while read"):
                    own._read(path, ROOT)
            self.assertEqual(path.read_bytes(), expected)


class Machine(prior_fixture.Machine):
    """Independent V2 layout/mapping; retained callback ABI models only."""
    def __init__(self, tools, profile="classic", resolution="1024x768", delta=0):
        layout = synthetic_layout(profile, resolution)
        out = emission(layout)
        plan, modal = tool._plan(layout)
        plan["inherited_state_inventory"] = None if modal is None else {"page_va": modal}
        unicorn, registers = tools
        real_uc = unicorn.Uc

        class Mapping:
            def __init__(self, *args, **kwargs):
                self.cpu = real_uc(*args, **kwargs)
            def __getattr__(self, name):
                return getattr(self.cpu, name)
            def mem_map(self, at, size, *args):
                return self.cpu.mem_map(at, 0x51000 if at == out.base_va + delta else size, *args)

        proxy = SimpleNamespace(**{name:getattr(unicorn,name) for name in dir(unicorn) if not name.startswith("__")})
        proxy.Uc = Mapping
        with patch.object(prior_fixture, "synthetic_plan", return_value=plan), \
             patch.object(prior_fixture.tool, "_emit_code", return_value=out):
            super().__init__((proxy, registers), profile, resolution, delta)
        self.layout = layout
        self.cpu.mem_write(self.state_va + 128, bytes(65536 - 128))
        self.cpu.mem_write(self.state_va + 65536, b"\xD7" * 16)
        self.tail_expected = bytes(65536 - 128)
        self.padding_expected = bytes(24)
        self.modal_expected = None if modal is None else bytes(self.cpu.mem_read(modal + delta, 4096))
        self.tail_reads = 0
        self.instruction_boundaries = {}

    def on_code(self, cpu, address, size, data):
        if hasattr(self, "instruction_boundaries") and self.emission.base_va + self.delta <= address < self.emission.base_va + self.delta + len(self.emission.code):
            self.instruction_boundaries[address - self.emission.base_va - self.delta] = size
        super().on_code(cpu, address, size, data)

    def on_read(self, cpu, access, address, size, value, data):
        if hasattr(self, "tail_reads") and self.state_va + 128 <= address and address + size <= self.state_va + 65536:
            self.tail_reads += 1
            return
        super().on_read(cpu, access, address, size, value, data)

    def invoke(self, name, *, eax=0, edx=0x22334455, flags=0xED7, stops=(), sp=None):
        self.stops = {va + self.delta for va in stops}; self.native_stop = None
        self.writes, self.reads, self.tail_reads = [], [], 0
        incoming = dict(EAX=eax, ECX=0x11223344, EDX=edx, EBX=0x33445566,
            EBP=0x44556677, ESI=0x55667788, EDI=0x66778899, ESP=self.SP if sp is None else sp)
        self.put(incoming["ESP"], self.STOP)
        for name_, value in incoming.items():
            self.cpu.reg_write(self.regs[name_], value)
        self.cpu.reg_write(self.regs["EFLAGS"], flags)
        self.cpu.emu_start(self.entries[name], self.STOP + 1, count=4000000)
        output = {name_:self.cpu.reg_read(register) for name_,register in self.regs.items()}
        assert self.native_stop is not None, (name, output)
        if self.native_stop == self.STOP:
            expected_sp = self.ROOT_SP + 8 if name == "root_epilogue" else incoming["ESP"] + 4
            assert output["ESP"] == expected_sp, output
            assert all(output[name_] == value for name_,value in incoming.items() if name_ not in ("EAX","ESP")), output
            if name != "root_epilogue":
                assert output["EFLAGS"] & self.MASK == flags & self.MASK, output
        allowed = ((self.STACK,self.STACK+0x10000),(self.state_va,self.state_va+104),
            (self.PRIVATE,self.PRIVATE+188),(self.private_pixels,self.private_pixels+307200),
            (native.RENDER+self.delta,native.RENDER+self.delta+4))
        assert all(any(lo <= at and at + size <= hi for lo,hi in allowed) for at,size in self.writes), self.writes
        # The protected tails are scanned in place, never copied into a large
        # stack snapshot. Include the return slot in the declared456-byte core
        # allowance and the native adapter's own40 bytes when present.
        stack_writes = [at for at,_ in self.writes if self.STACK <= at < self.STACK+0x10000]
        outer = name in ("root_entry","bind_allocation","leave_before_free","root_epilogue")
        extent = 4 + incoming["ESP"] - min(stack_writes,default=incoming["ESP"])
        assert extent <= 456 + (40 if outer else 0), (name,extent)
        assert bytes(self.cpu.mem_read(self.state_va + 104,24)) == self.padding_expected
        assert bytes(self.cpu.mem_read(self.state_va + 128,65536-128)) == self.tail_expected
        assert bytes(self.cpu.mem_read(self.state_va-16,16)) == b"\xD7"*16
        assert bytes(self.cpu.mem_read(self.state_va+65536,16)) == b"\xD7"*16
        if self.modal_va is not None:
            assert bytes(self.cpu.mem_read(self.modal_va+self.delta,4096)) == self.modal_expected
        return output

    def mutate_tail(self, offset, value=1, inherited=False):
        at = (self.modal_va+self.delta if inherited else self.state_va) + offset
        self.put(at,value)
        if inherited:
            self.modal_expected = bytes(self.cpu.mem_read(self.modal_va+self.delta,4096))
        else:
            self.tail_expected = bytes(self.cpu.mem_read(self.state_va+128,65536-128))


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.tools = prior_fixture.machine_tools()
        except ImportError as error:
            raise unittest.SkipTest(str(error))

    def test_all36_two_bases_modeled_allocation_admission_retirement_and_return(self):
        for profile in context.PROFILES:
            for resolution in context.RESOLUTIONS:
                for delta in (0,0x2000000):
                    with self.subTest(profile=profile,resolution=resolution,delta=delta):
                        m = Machine(self.tools,profile,resolution,delta)
                        self.assertEqual(m.enter()["EAX"],1)
                        self.assertEqual(m.allocs,[188,307200])
                        self.assertEqual(m.bind()["EAX"],1)
                        m.put(native.RENDER+delta,m.PRIVATE)
                        self.assertEqual(m.invoke("try_leave",eax=m.ROOT_SP-172)["EAX"],1)
                        self.assertEqual(m.frees,[m.private_pixels,m.PRIVATE])
                        self.assertEqual(len(m.destructions),1)
                        m.put(0x532048+delta,0);m.put(native.HOOK_OWNER+delta,0x40AD40+delta)
                        self.assertEqual(m.invoke("finish_return",eax=m.ROOT_SP-168)["EAX"],1)
                        self.assertEqual(m.state("phase"),0)
                        self.assertEqual(m.state("allocations"),m.state("frees"))
                        self.assertEqual(bytes(m.cpu.mem_read(m.PHYSICAL_PIXELS,m.width*m.height)),b"\xB9"*(m.width*m.height))
                        self.assertGreater(m.tail_reads,0)

    def test_zero_policy_rejects_new_and_inherited_tails_before_callbacks(self):
        for profile in context.PROFILES:
            for inherited, offset in ((False,128),(False,4092),(False,4096),(False,65532)) + \
                (((True,128),(True,4092)) if profile in ("completehd","modalwidgets") else ()):
                with self.subTest(profile=profile,inherited=inherited,offset=offset):
                    m = Machine(self.tools,profile);m.mutate_tail(offset,inherited=inherited)
                    self.assertEqual(m.enter()["EAX"],0)
                    self.assertEqual(m.callbacks,[])
                    self.assertEqual(m.frees,[])

    def test_every_modeled_callback_tail_mutation_never_becomes_clean_lifetime(self):
        for callback in ("thread","allocate","construct","destroy","free"):
            for inherited in (False,True):
                with self.subTest(callback=callback,inherited=inherited):
                    m = Machine(self.tools,"modalwidgets")
                    if callback == "destroy":
                        self.assertEqual(m.enter()["EAX"],1);self.assertEqual(m.bind()["EAX"],1)
                    trigger = False
                    def mutation(machine,name):
                        nonlocal trigger
                        if name == callback and not trigger:
                            trigger = True;machine.mutate_tail(4096 if not inherited else 2048,inherited=inherited)
                        if callback == "free" and name == "construct":
                            machine.cpu.reg_write(machine.regs["EAX"],machine.PRIVATE+4)
                    m.mutation = mutation
                    if callback == "destroy":
                        result=m.invoke("try_leave",eax=m.ROOT_SP-172)
                        self.assertEqual(len(m.destructions),1)
                    elif callback == "free":
                        # Native allocation2 failure induces a legitimate
                        # rollback FREE, then mutation must stop subsequent work.
                        m.fail_allocation=2;result=m.enter()
                    else:
                        result=m.enter()
                    self.assertTrue(trigger)
                    self.assertEqual(result["EAX"],0)
                    self.assertEqual(m.state("return_status"),0)
                    if callback != "thread":
                        self.assertNotEqual(m.state("fault"),0)
                    self.assertLessEqual(len(m.destructions),1)

    def test_allocator_failure_phase_one_abort_and_foreign_thread_retain_diagnosis(self):
        for profile in context.PROFILES:
            for failure in (1,2):
                m=Machine(self.tools,profile);m.fail_allocation=failure
                self.assertEqual(m.enter()["EAX"],0);self.assertEqual(m.state("phase"),0)
                self.assertEqual(m.live,{})
            m=Machine(self.tools,profile);self.assertEqual(m.enter()["EAX"],1)
            m.put(native.HOOK_OWNER,0x42E8B0)
            self.assertEqual(m.invoke("bind_or_abort",eax=0,edx=m.ROOT_SP-168)["EAX"],0)
            self.assertEqual(m.state("abort_reason"),1)
            self.assertEqual(len(m.destructions),1)
            m=Machine(self.tools,profile)
            def change(machine,name):
                if name == "allocate":machine.thread_id += 1
            m.mutation=change
            self.assertEqual(m.enter()["EAX"],0)
            self.assertEqual(m.frees,[])
            self.assertEqual(m.state("phase"),3)
            self.assertEqual(m.state("fault"),6)

    def test_full_rx_rw_and_inherited_pages_cannot_be_allocator_header_backend_or_world(self):
        for profile in context.PROFILES:
            m=Machine(self.tools,profile)
            points=[m.emission.base_va+0x30000,m.state_va+512,m.state_va+60000]
            if m.modal_va is not None:points += [m.modal_va+512]
            for pointer in points:
                with self.subTest(profile=profile,pointer=pointer):
                    test=Machine(self.tools,profile);test.allocator_returns=[pointer]
                    self.assertEqual(test.enter()["EAX"],0)
                    self.assertEqual(test.frees,[])
                    test=Machine(self.tools,profile);test.put(native.MAP,pointer);test.put(native.RENDER,pointer)
                    self.assertEqual(test.enter()["EAX"],0);self.assertEqual(test.allocs,[])
                    test=Machine(self.tools,profile);test.put(native.PRIMARY+0xBC,pointer)
                    self.assertEqual(test.enter()["EAX"],0);self.assertEqual(test.allocs,[])
                    test=Machine(self.tools,profile);self.assertEqual(test.enter()["EAX"],1)
                    test.put(native.HOOK_OWNER,0x42E8B0);test.put(0x532048,pointer)
                    self.assertEqual(test.invoke("bind_or_abort",eax=pointer,edx=test.ROOT_SP-168)["EAX"],0)
                    self.assertEqual(test.destructions,[])

    def test_thread_callback_losses_reject_before_poisoned_cached_headers(self):
        for delta in (0,0x2000000):
            m=Machine(self.tools,"modalwidgets",delta=delta)
            self.assertEqual(m.enter()["EAX"],1);self.assertEqual(m.bind()["EAX"],1)
            def mutation(machine,name):
                if name == "thread":
                    machine.mutate_tail(65532)
                    machine.cpu.mem_protect(machine.PHYSICAL,4096,machine.u.UC_PROT_NONE)
            m.mutation=mutation
            self.assertEqual(m.invoke("try_leave",eax=m.ROOT_SP-172)["EAX"],0)
            self.assertEqual(m.destructions,[])

    def test_complete_first128_record_snapshots_reject_callback_loss_before_cached_headers(self):
        for delta in (0,0x2000000):
            for inherited in (False,True):
                for offset in (0,124):
                    with self.subTest(delta=delta,inherited=inherited,offset=offset):
                        m=Machine(self.tools,"modalwidgets",delta=delta)
                        self.assertEqual(m.enter()["EAX"],1);self.assertEqual(m.bind()["EAX"],1)
                        changed=False
                        def mutation(machine,name):
                            nonlocal changed
                            if name == "thread" and not changed:
                                changed=True
                                at=(machine.modal_va+machine.delta if inherited else machine.state_va)+offset
                                machine.put(at,machine.word(at)+1)
                                if inherited:
                                    machine.modal_expected=bytes(machine.cpu.mem_read(machine.modal_va+machine.delta,4096))
                                elif offset >= 104:
                                    machine.padding_expected=bytes(machine.cpu.mem_read(machine.state_va+104,24))
                                machine.cpu.mem_protect(machine.PHYSICAL,4096,machine.u.UC_PROT_NONE)
                        m.mutation=mutation
                        self.assertEqual(m.invoke("try_leave",eax=m.ROOT_SP-172)["EAX"],0)
                        self.assertTrue(changed)
                        self.assertEqual(m.destructions,[])
                        self.assertEqual(m.frees,[])

    def test_outer_hook_chain_preserves_native_stack_ret4_and_null_fatal_branch(self):
        for profile in context.PROFILES:
            for delta in (0,0x2000000):
                with self.subTest(profile=profile,delta=delta):
                    m=Machine(self.tools,profile,delta=delta)
                    m.thread_clobbers=True
                    result=m.invoke("root_entry",sp=m.ROOT_SP,stops=(0x42E9E9,))
                    self.assertEqual(result["ESP"],m.ROOT_SP-168)
                    self.assertEqual(m.state("root_esp"),m.ROOT_SP)
                    self.assertEqual(m.state("phase"),1)
                    self.assertEqual(result["EFLAGS"] & m.MASK,
                        prior_fixture.CPUTests.native_stack_flags(self,"81ec9c000000",m.ROOT_SP-12,0xED7))
                    m.put(native.HOOK_OWNER+delta,0x42E8B0+delta)
                    m.put(0x532048+delta,m.WORLD)
                    result=m.invoke("bind_allocation",sp=m.ROOT_SP-168,stops=(0x42EC97,))
                    self.assertEqual(result["ESP"],m.ROOT_SP-168)
                    self.assertEqual(m.state("phase"),2)
                    m.put(native.RENDER+delta,m.PRIVATE)
                    m.invoke("leave_before_free",eax=m.WORLD,sp=m.ROOT_SP-172)
                    self.assertEqual(m.frees,[m.private_pixels,m.PRIVATE,m.WORLD])
                    self.assertEqual(m.replayed_free_flags[0] & m.MASK,0xED7 & m.MASK)
                    self.assertEqual(m.state("phase"),4)
                    m.put(0x532048+delta,0);m.put(native.HOOK_OWNER+delta,0x40AD40+delta)
                    m.cpu.mem_write(0x42F5B9+delta,bytes.fromhex("5d5f5ec20400"))
                    m.put(m.ROOT_SP-12,0x44556677);m.put(m.ROOT_SP-8,0x66778899)
                    m.put(m.ROOT_SP-4,0x55667788);m.put(m.ROOT_SP,m.STOP);m.put(m.ROOT_SP+4,0xA5A5)
                    result=m.invoke("root_epilogue",eax=0x44556677,sp=m.ROOT_SP-168)
                    self.assertEqual(result["EAX"],0x44556677)
                    self.assertEqual(result["ESP"],m.ROOT_SP+8)
                    self.assertEqual(result["EFLAGS"] & m.MASK,
                        prior_fixture.CPUTests.native_stack_flags(self,"81c49c000000",m.ROOT_SP-168,0xED7))
                    self.assertEqual(m.state("return_status"),1)
                    self.assertEqual(m.state("phase"),0)
                    rejected=Machine(self.tools,profile,delta=delta)
                    rejected.invoke("root_entry",sp=rejected.ROOT_SP,stops=(0x42E9E9,))
                    rejected.put(native.HOOK_OWNER+delta,0x42E8B0+delta)
                    rejected.cpu.mem_write(0x42EC97+delta,bytes.fromhex("0f8467030000"))
                    result=rejected.invoke("bind_allocation",sp=rejected.ROOT_SP-168,stops=(0x42F004,))
                    self.assertEqual(rejected.native_stop,0x42F004+delta)
                    self.assertEqual(result["ESP"],rejected.ROOT_SP-168)
                    self.assertEqual(rejected.frees,[rejected.private_pixels,rejected.PRIVATE])
                    self.assertEqual(rejected.state("return_status"),0)


class OriginalBackedTests(unittest.TestCase):
    def test_modal4k_canonical_fresh_reemission_old_windows_and_hostile_alias_identity(self):
        original=ORIGINAL.read_bytes();self.assertEqual(sha(original),tool.BASE_SHA256)
        first=tool.emit_lifecycle_v2(original,"modalwidgets","3840x2160")
        with patch.object(tool,"_modules",side_effect=AssertionError("public modules")), \
             patch.object(tool,"_snapshot",return_value={}),patch.object(tool,"_issue",return_value=object()), \
             patch.object(tool,"_versioned_template",side_effect=AssertionError("public template")), \
             patch.object(context,"build_allocation_context",side_effect=AssertionError("public context")):
            second=tool.emit_lifecycle_v2(original,"modalwidgets","3840x2160")
        # Each dispatch independently compiles its private dependency classes.
        # Compare every immutable field, including bytes and metadata, without
        # mistaking unrelated Python class identities for candidate changes.
        self.assertEqual(asdict(first),asdict(second))
        out,layout=first.emission,first.allocation_context.layout
        relocation_oracle(out,layout)
        self.assertEqual(first.removed_highlow_rvas,(0x2EC92,))
        self.assertEqual(len(first.planned_hooks),4)
        for _,at,va,before,after,target,fields in first.planned_hooks:
            self.assertEqual(first.allocation_context.relayout_parent[at:at+len(before)],before)
            self.assertEqual(len(after),len(before))
            self.assertEqual(va+5+struct.unpack_from("<i",after,1)[0],target)
        meta=first.metadata()
        for key in tool.FALSE_CLAIMS:self.assertIs(meta[key],False)
        self.assertEqual(meta["provider_records_emitted"],0)
        self.assertIsNone(meta["provider_capacity"])
        self.assertEqual(meta["helper_stack_snapshot_bytes"],384)
        self.assertEqual(meta["maximum_added_helper_stack_bytes"],456)
        self.assertEqual(sha(ORIGINAL.read_bytes()),tool.BASE_SHA256)


def main():
    global ORIGINAL
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolchain-path",type=Path)
    parser.add_argument("--require-machine-tools",action="store_true")
    parser.add_argument("--original-backed",type=Path)
    args,names=parser.parse_known_args()
    if args.toolchain_path:sys.path.insert(0,str(args.toolchain_path.resolve()))
    if args.require_machine_tools:
        try:prior_fixture.machine_tools()
        except ImportError as error:parser.error(str(error))
    ORIGINAL=args.original_backed
    if ORIGINAL is None and any("OriginalBackedTests" in name for name in names):parser.error("explicit --original-backed required")
    loader=unittest.TestLoader()
    suite=unittest.TestSuite()
    if names:suite.addTests(loader.loadTestsFromNames(names,module=sys.modules[__name__]))
    else:
        for cls in (SourceTests,CPUTests):suite.addTests(loader.loadTestsFromTestCase(cls))
        if ORIGINAL is not None:suite.addTests(loader.loadTestsFromTestCase(OriginalBackedTests))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print("uninstalled=True native_callbacks=modeled provider_capacity_verified=False runtime_executed=False")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":raise SystemExit(main())
