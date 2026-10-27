#!/usr/bin/env python3
"""Opt-in original final Adjacent CALL and Unit prefix, never whole Unit/runtime.

Default/public checks are stdlib authoring only. Explicit --original-backed
authenticates the user-owned original in RAM and compares the unchanged final
caller, real CALL and Unit prologue with one RAM-only first-Type adapter window.
Execution stops at 42F854 before its JE: no Unit RET, final caller continuation,
Count, Windows/game, full native ABI, installation or release proof is supplied.
Outer Field/Tile/Adjacent history and Thread remain authored models. No original
opcodes, candidate, capture or reverse-engineering export is written.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import hashlib
import importlib
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SELF = "tools/test_battle_profile_native_adjacent_prefix_original.py"
READER = "tools/test_battle_profile_native_count_original.py"
PINNED_FILES = {
    READER: "08f654c676a3d13a9a7e993b701ecdd711d5a8d6bc79227b62357b699368cc9e",
    "src/patcher/battle_profile_adjacent_unit_v2.py": "b2ae87457bd2344d9e6650032dba46d03a680e2303946acb75abaf0508f5ead8",
    "tools/test_battle_profile_adjacent_unit_v2.py": "a8fbbccba6151b5f1b6e374be2935db8e8a58348228451380f883a02a685b009",
}
ORIGINAL_SHA = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
FINAL, CALL, RETURN = 0x42ff7a, 0x42ff9f, 0x42ffa4
UNIT, TYPE, RESUME, UNIT_END = 0x42f820, 0x42f84a, 0x42f854, 0x42f85a
NO_CALL, SENTINEL = 0x42fed6, 0x42f93e
MOTION, ACTIVE, WORLD_GLOBAL = 0x523f70, 0x512360, 0x532048
SPANS = (
    (FINAL, RETURN, "455371cdb73867ea54a97c41442702a4bd2bd88135af9c2a2b2585c2a684c9fa"),
    (UNIT, UNIT_END, "bef712bfb5b35cdcdb6d8f2583b7907f85bed214da9fa244f4d2554dcd18c206"),
)
PREFIX_SHA = "82906cff5c6036c02677c48091c94687a509d949dbe4d6d6641cfd7eef73e9a0"
TYPE_SHA = "28ae5f07f0c032296977506acb7427e1ffc361b3053374eb58260d0f06cebd9c"
HIGHLOW = ((0x42ff7c, MOTION), (0x42ff8a, ACTIVE), (0x42f841, WORLD_GLOBAL))
# Authored instruction-boundary/control metadata, not proprietary opcode bytes.
CALLER_LENGTHS = (6, 2, 6, 6, 6, 3, 3, 1, 2, 2, 5)
PREFIX_LENGTHS = (1, 1, 1, 2, 3, 2, 3, 3, 3, 3, 6, 3, 6, 2, 3)
BRANCHES = ((0x42ff82, 0x8d, NO_CALL), (0x42ff8e, 0x85, NO_CALL),
            (0x42f836, 0x84, SENTINEL), (RESUME, 0x84, SENTINEL))
GPRS = ("EAX", "ECX", "EDX", "EBX", "ESP", "EBP", "ESI", "EDI")
ARITH = 0x8d5
ACCEPTANCE = dict(original_prefix_cpu_verified=False, whole_unit_verified=False,
                  genuine_final_route_verified=False, native_callback_abi_verified=False,
                  mapping_or_lifetime_verified=False, windows_runtime_verified=False,
                  installed=False, input_verified=False, release_accepted=False,
                  promotion_ready=False)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def u32(value):
    return value & 0xffffffff


def source_contract():
    for name, digest in PINNED_FILES.items():
        path = ROOT/name
        require(path.resolve(strict=True) == path, "canonical prefix fixture dependency required")
        require(sha(path.read_bytes()) == digest, "frozen prefix fixture dependency differs: "+name)


def boundaries(start, lengths):
    result = {}
    for size in lengths:
        require(1 <= size <= 15, "bounded native instruction required")
        result[start] = size
        start += size
    return result


NATIVE_LENGTHS = boundaries(FINAL, CALLER_LENGTHS) | boundaries(UNIT, PREFIX_LENGTHS) | {
    TYPE: 7, TYPE+7: 3, RESUME: 6,
}


@dataclass(frozen=True, repr=False)
class NativeImage:
    caller: bytes
    unit: bytes


def authenticate_original(image):
    require(type(image) is bytes and sha(image) == ORIGINAL_SHA, "exact original required")
    source_contract()
    sys.path[:0] = [str(ROOT), str(ROOT/"tools")]
    reader = importlib.import_module("test_battle_profile_native_count_original")
    require(Path(reader.__file__).resolve() == ROOT/READER, "pinned PE reader module required")
    base, locate, relocs = reader.pe_layout(image)
    require(base == 0x400000, "preferred original image base required")
    get = lambda va, size: image[locate(va, size):locate(va, size)+size]
    for lo, hi, digest in SPANS:
        require(sha(get(lo, hi-lo)) == digest, "complete original caller/Unit span differs")
    require(sha(get(UNIT, TYPE-UNIT)) == PREFIX_SHA and sha(get(TYPE, RESUME-TYPE)) == TYPE_SHA,
            "independently pinned prefix/type spans differ")
    selected = sorted(va for va in relocs if any(lo <= va < hi for lo, hi, _ in SPANS))
    require(selected == sorted(va for va, _ in HIGHLOW), "complete prefix HIGHLOW inventory differs")
    for va, target in HIGHLOW:
        require(get(va, 4) == struct.pack("<I", target), "prefix HIGHLOW target differs")
    for pc, condition, target in BRANCHES:
        raw = get(pc, 6)
        require(raw[:2] == bytes((0x0f, condition)) and pc+6+struct.unpack_from("<i", raw, 2)[0] == target,
                "native bounded conditional branch differs")
    call = get(CALL, 5)
    require(call[0] == 0xe8 and RETURN+struct.unpack_from("<i", call, 1)[0] == UNIT,
            "unchanged final native CALL target differs")
    source_contract()
    return NativeImage(get(FINAL, RETURN-FINAL), get(UNIT, UNIT_END-UNIT))


def cmp_flags(left, right, incoming):
    """Independent x86 SUB/CMP arithmetic flags; retain all non-arithmetic bits."""
    left, right = u32(left), u32(right)
    value = u32(left-right)
    flags = int(left < right) | (int((value & 255).bit_count() % 2 == 0) << 2)
    flags |= (left ^ right ^ value) & 0x10
    flags |= int(value == 0) << 6
    flags |= (value >> 31) << 7
    flags |= int(bool((left ^ right) & (left ^ value) & 0x80000000)) << 11
    return (incoming & ~ARITH) | flags | 2


def test_flags(value, incoming):
    # AF is architecturally undefined for TEST. Pairwise full flags still must
    # match; the independent no-call oracle excludes AF rather than inventing it.
    value = u32(value)
    flags = (int((value & 255).bit_count() % 2 == 0) << 2) | (int(value == 0) << 6)
    flags |= (value >> 31) << 7
    return (incoming & ~ARITH) | flags | 2


@dataclass(frozen=True)
class Case:
    name: str
    identity: int = 7
    motion: int = -3
    active: int | None = None
    unit_type: int = 34
    old_esi: int = 0
    old_ebx: int = 32
    old_edi: int = 16
    flags: int = 0xed7

    def active_value(self):
        return u32(self.identity if self.active is None else self.active)

    def stop(self):
        if not u32(self.motion) & 0x80000000 or u32(self.identity) != self.active_value():
            return NO_CALL
        return SENTINEL if u32(self.identity) == 0xffffffff else RESUME

    def validate(self):
        require(self.identity == -1 or 0 <= self.identity < 22, "bounded modeled identity required")
        require(-0x80000000 <= self.motion <= 0x7fffffff and -32768 <= self.unit_type <= 32767,
                "signed modeled motion/type required")
        return self


def oracle(case, incoming, world, unit_s, delta):
    """Phase-relative argument/state oracle, independent of every producer."""
    result = dict(incoming)
    result["EBP"] = u32(case.motion)
    result["EIP"] = case.stop()+delta
    mask = 0xffffffff
    if not u32(case.motion) & 0x80000000:
        result["EFLAGS"] = test_flags(case.motion, case.flags)
        return result, mask ^ 0x10
    result["EFLAGS"] = cmp_flags(case.identity, case.active_value(), case.flags)
    if case.stop() == NO_CALL:
        return result, mask
    result.update(ESP=unit_s-64, EBP=unit_s-12, ESI=u32(case.identity),
                  EBX=u32(case.old_edi), EDI=u32(case.old_edi),
                  EDX=u32(case.old_esi), ECX=u32(case.motion+64))
    if case.stop() == SENTINEL:
        result["EFLAGS"] = cmp_flags(-1, -1, case.flags)
        return result, mask
    result.update(EAX=u32(case.unit_type), ECX=world, EDX=world+31*case.identity,
                  EFLAGS=cmp_flags(case.unit_type, -1, case.flags))
    return result, mask


def native_write_oracle(case, unit_s, delta):
    if case.stop() == NO_CALL:
        return []
    return [(0x42ff9a, unit_s+4, 4, u32(case.old_ebx+64)),
            (CALL, unit_s, 4, RETURN+delta),
            (0x42f820, unit_s-4, 4, u32(case.old_esi)),
            (0x42f821, unit_s-8, 4, u32(case.old_edi)),
            (0x42f822, unit_s-12, 4, u32(case.motion)),
            (0x42f82a, unit_s-24, 4, u32(case.old_esi)),
            (0x42f82d, unit_s-20, 4, u32(case.old_edi)),
            (0x42f830, unit_s-52, 4, u32(case.motion+64))]


def native_read_oracle(case, world, delta, *, joined):
    reads = [(FINAL, MOTION+delta, 4)]
    if not u32(case.motion) & 0x80000000:
        return reads
    reads.append((0x42ff88, ACTIVE+delta, 4))
    if case.stop() != RESUME:
        return reads
    reads.append((0x42f83f, WORLD_GLOBAL+delta, 4))
    if not joined:
        reads.append((TYPE, world+852+31*case.identity, 2))
    return reads


def native_pc_oracle(case, *, joined):
    caller, prefix = list(boundaries(FINAL, CALLER_LENGTHS)), list(boundaries(UNIT, PREFIX_LENGTHS))
    if not u32(case.motion) & 0x80000000:
        return caller[:3]
    if case.stop() == NO_CALL:
        return caller[:5]
    if case.stop() == SENTINEL:
        return caller+prefix[:11]
    return caller+prefix+[TYPE]+([] if joined else [TYPE+7])


def load_runtime():
    source_contract()
    sys.path[:0] = [str(ROOT), str(ROOT/"tools")]
    prior = importlib.import_module("test_battle_profile_adjacent_unit_v2")
    closure = prior.source_closure() | {name: sha((ROOT/name).read_bytes()) for name in PINNED_FILES}
    closure[SELF] = sha(Path(__file__).read_bytes())
    tools = prior.observer.parent_fixture.field_fixture.routing_fixture.lifetime.prior_fixture.machine_tools()
    require(tools is not None, "original-backed prefix requires the real Unicorn interpreter")
    return prior, tools, closure


def machine_class(prior):
    class OriginalMachine(prior.Machine):
        def __init__(self, tools, native, *, joined, profile="classic", delta=0, mode=0):
            self.invocation_active = False
            super().__init__(tools, profile, "800x600", delta)
            self.joined, self.mode = joined, mode
            self.native_blocks = {FINAL: bytearray(native.caller), UNIT: bytearray(native.unit)}
            for va, target in HIGHLOW:
                start = FINAL if FINAL <= va < RETURN else UNIT
                struct.pack_into("<I", self.native_blocks[start], va-start, target+delta)
            old, target, role, removed = self.planned[TYPE]
            require(len(old) == RESUME-TYPE and sha(old) == TYPE_SHA and removed == (),
                    "exact Atomic first-Type window required")
            if joined:
                self.native_blocks[UNIT][TYPE-UNIT:RESUME-UNIT] = (
                    b"\xe8"+struct.pack("<i", target-TYPE-5)+b"\x90"*5)
            self.native_blocks = {va: bytes(raw) for va, raw in self.native_blocks.items()}
            for va, raw in self.native_blocks.items():
                self.cpu.mem_write(va+delta, raw)
                self.cpu.ctl_remove_cache(va+delta, va+delta+len(raw))
            body = next(row for row in self.atomic_adapters.body_receipts if row[0] == TYPE)
            self.payload_region = body[2]+delta, body[7]+delta
            absolute = {r.offset for r in self.atomic_adapters.relocations if r.kind == "abs32"}
            decoded = prior.replay_fixture.decode(self.atomic_adapters.code, absolute)
            payload_loads = [self.atomic_adapters.base_va+start+delta for start, end, *_ in decoded
                             if self.payload_region[0] <= self.atomic_adapters.base_va+start+delta < self.payload_region[1]
                             and self.atomic_adapters.code[start:end] == b"\x0f\xbf\x00"]
            require(len(payload_loads) == 1, "one exact authored first-Type WORD load required")
            self.type_read_pc = payload_loads[0]

        def setup_caller(self, case):
            self.case = case.validate()
            self.prepare(columns=3).begin(self.mode)
            row = prior.SITES[0]
            require(row[0] == TYPE, "first Unit Type source row required")
            # Obtain only modeled outer ancestry. Discard every prewritten
            # future Unit word; native PUSH/CALL/prologue must create them.
            self.setup_body(row, index=max(case.identity, 0), via_adjacent=True)
            self.caller_sp = self.adjacent_sp-16
            self.unit_s = self.caller_sp-8
            require(self.unit_s == self.unit_sp, "modeled outer stack delta differs")
            self.cpu.mem_write(self.unit_s-64, b"\xd7"*72)
            require(self.word(self.adjacent_sp-16) == self.current_cell[0] and
                    self.word(self.adjacent_sp-12) == self.tile_sp-20,
                    "future Unit clearing damaged Adjacent controls")
            self.put(MOTION+self.delta, case.motion)
            self.put(ACTIVE+self.delta, case.active_value())
            self.put(WORLD_GLOBAL+self.delta, self.WORLD)
            if case.identity >= 0:
                self.cpu.mem_write(self.WORLD+852+31*case.identity, struct.pack("<h", case.unit_type))
            regs = dict(EAX=u32(case.identity), ECX=0x11223344, EDX=0x22334455,
                        EBX=u32(case.old_ebx), ESP=self.caller_sp, EBP=self.current_cell[1],
                        ESI=u32(case.old_esi), EDI=u32(case.old_edi))
            return self, regs

        def _source_owner(self, pc, size):
            hits = [(va, raw) for va, raw in self.loaded_code if va <= pc and pc+size <= va+len(raw)]
            require(len(hits) == 1, "unexpected/ambiguous prefix surrounding source PC")
            va, raw = hits[0]
            require(bytes(self.cpu.mem_read(pc, size)) == raw[pc-va:pc-va+size],
                    "prefix surrounding source instruction changed")

        def _native_bytes(self, pc, size):
            hits = [(va, raw) for va, raw in self.native_blocks.items() if va <= pc and pc+size <= va+len(raw)]
            require(len(hits) == 1, "native prefix PC escaped bounded spans")
            va, raw = hits[0]
            return raw[pc-va:pc-va+size]

        def _check_unit_word(self):
            require(self.word(self.unit_s) == RETURN+self.delta,
                    "genuine Unit CALL return word changed")

        def _thread_mutation(self, machine, label):
            if self.invocation_active and label == "thread":
                self.epochs.append((len(self.read_events), len(self.write_events)))
                if self.fault:
                    self.fault(self, len(self.epochs))

        def on_code(self, cpu, address, size, data):
            if not self.invocation_active:
                return super().on_code(cpu, address, size, data)
            pc = address-self.delta
            if pc in (RESUME, NO_CALL, SENTINEL):
                require(pc == self.case.stop(), "unexpected native bounded stop")
                if pc == RESUME:
                    require(self.unit_entries == 1 and self.type_entries == 1 and
                            size == NATIVE_LENGTHS[RESUME] and
                            bytes(cpu.mem_read(address, size)) == self._native_bytes(pc, size),
                            "genuine first-Type resume boundary differs")
                if self.unit_entries:
                    self._check_unit_word()
                require(self.active_scan is None, "source scan pending at prefix stop")
                self.native_stop = address
                cpu.emu_stop()
                return
            if pc in NATIVE_LENGTHS or FINAL <= pc < RETURN or UNIT <= pc < UNIT_END:
                require(pc in NATIVE_LENGTHS, "native prefix instruction boundary escaped")
                expected_size = 5 if self.joined and pc == TYPE else NATIVE_LENGTHS[pc]
                require(not (self.joined and TYPE < pc < RESUME) and size == expected_size,
                        "stolen Type interior or native instruction size changed")
                require(bytes(cpu.mem_read(address, size)) == self._native_bytes(pc, size),
                        "authenticated prefix instruction changed")
                if pc == FINAL:
                    require(not self.native_seen and cpu.reg_read(self.regs["ESP"]) == self.caller_sp,
                            "final caller did not start from modeled Adjacent body SP")
                if pc == UNIT:
                    require(self.native_seen[-1:] == [CALL] and self.unit_entries == 0 and
                            cpu.reg_read(self.regs["ESP"]) == self.unit_s,
                            "genuine final CALL did not create Unit entry")
                    self._check_unit_word()
                    require(self.word(self.unit_s+4) == u32(self.case.old_ebx+64),
                            "native caller stack argument differs")
                    self.unit_entries += 1
                if self.unit_entries:
                    self._check_unit_word()
                if pc == TYPE:
                    require(self.unit_entries == 1 and self.type_entries == 0 and
                            cpu.reg_read(self.regs["ESP"]) == self.unit_s-64 and
                            cpu.reg_read(self.regs["EBP"]) == self.unit_s-12 and
                            cpu.reg_read(self.regs["ESI"]) == self.case.identity and
                            cpu.reg_read(self.regs["EAX"]) == 31*self.case.identity and
                            cpu.reg_read(self.regs["ECX"]) == self.WORLD and
                            cpu.reg_read(self.regs["EDX"]) == self.WORLD+31*self.case.identity,
                            "genuine Unit prologue/type effective-address contract differs")
                    require(self.native_writes == native_write_oracle(self.case, self.unit_s, self.delta),
                            "native prologue/argument write inventory differs")
                    self.type_entries += 1
                require(self.active_scan is None, "native prefix entered during source scan")
                self.native_seen.append(pc)
                return  # Genuine native bytes execute; never parent stub dispatch.
            if address in self.unsafe_vas:
                self._source_owner(address, 2)
                require(bytes(cpu.mem_read(address, 2)) == b"\x0f\x0b", "real authored UD2 required")
                self.unsafe = True
                return  # Execute UD2, not an observer-produced terminal result.
            if address != self.THREAD:
                self._source_owner(address, size)
            super().on_code(cpu, address, size, data)

        def on_read(self, cpu, access, address, size, value, data):
            if self.invocation_active and self.active_scan is None:
                pc = cpu.reg_read(self.regs["EIP"])-self.delta
                self.read_events.append((pc, address, size))
                if FINAL <= pc < RETURN or UNIT <= pc < UNIT_END:
                    expected = {FINAL: (MOTION+self.delta, 4), 0x42ff88: (ACTIVE+self.delta, 4),
                                0x42f83f: (WORLD_GLOBAL+self.delta, 4),
                                TYPE: (self.WORLD+852+31*self.case.identity, 2)}
                    require(expected.get(pc) == (address, size), "native prefix read escaped exact contract")
                    self.native_reads.append((pc, address, size))
                    if pc == TYPE:
                        self.type_payload_reads.append((address, size, int.from_bytes(cpu.mem_read(address, size), "little")))
                elif pc+self.delta == self.type_read_pc:
                    require(self.joined and address == self.WORLD+852+31*self.case.identity and size == 2,
                            "Atomic first-Type payload read escaped independent address")
                    self.type_payload_reads.append((address, size, int.from_bytes(cpu.mem_read(address, size), "little")))
                elif self.payload_region[0] <= pc+self.delta < self.payload_region[1]:
                    require(not (address < self.WORLD+0xf7c and address+size > self.WORLD),
                            "unexpected extra World read in first-Type payload")
            super().on_read(cpu, access, address, size, value, data)

        def on_write(self, cpu, access, address, size, value, data):
            if self.invocation_active:
                pc = cpu.reg_read(self.regs["EIP"])-self.delta
                self.write_events.append((pc, address, size, value))
                if self.joined and pc == TYPE:
                    require((address, size, value) == (self.unit_s-68, 4, TYPE+5+self.delta),
                            "first-Type CALL word escaped its exact slot")
                elif FINAL <= pc < RETURN or UNIT <= pc < TYPE:
                    event = pc, address, size, value
                    expected = native_write_oracle(self.case, self.unit_s, self.delta)
                    require(self.native_writes == expected[:len(self.native_writes)] and
                            expected[len(self.native_writes):len(self.native_writes)+1] == [event],
                            "native caller/prologue write escaped exact ordered inventory")
                    self.native_writes.append(event)
                else:
                    require(self.unit_s-932 <= address and address+size <= self.unit_s-64,
                            "source helper wrote outside own first-Type stack")
            super().on_write(cpu, access, address, size, value, data)

        def invoke_original(self, regs, *, fault=None):
            self.fault, self.mutation = fault, self._thread_mutation
            self.stops = set()
            self.native_stop, self.unsafe, self.active_scan = None, False, None
            self.unit_entries = self.type_entries = 0
            self.native_seen, self.native_writes, self.native_reads, self.type_payload_reads = [], [], [], []
            self.read_events, self.write_events, self.epochs = [], [], []
            self.content_reads, self.content_writes, self.content_events = [], [], []
            self.content_after_thread = False
            self.minimum_sp = regs["ESP"]
            self.before_callbacks = len(self.callbacks)
            world = bytes(self.cpu.mem_read(self.WORLD, 0xf7c))
            owner, lease = self.record(), bytes(self.cpu.mem_read(self.lease_frame, 192))
            stack = bytes(self.cpu.mem_read(self.STACK, 0x10000))
            for name, value in regs.items():
                self.cpu.reg_write(self.regs[name], u32(value))
            self.cpu.reg_write(self.regs["EFLAGS"], self.case.flags)
            self.invocation_active = self.content_active = True
            try:
                self.cpu.emu_start(FINAL+self.delta, self.STOP+1, count=5000000)
            finally:
                self.invocation_active = self.content_active = False
            require(self.native_stop == self.case.stop()+self.delta and not self.unsafe,
                    "bounded native prefix did not close at expected stop")
            require(self.native_writes == native_write_oracle(self.case, self.unit_s, self.delta),
                    "incomplete native caller/prologue write inventory")
            require(bytes(self.cpu.mem_read(self.WORLD, 0xf7c)) == world and self.record() == owner and
                    bytes(self.cpu.mem_read(self.lease_frame, 192)) == lease,
                    "healthy prefix changed world/owner/lease")
            after = bytes(self.cpu.mem_read(self.STACK, 0x10000))
            low, high = self.unit_s-932-self.STACK, self.unit_s+8-self.STACK
            require(after[:low] == stack[:low] and after[high:] == stack[high:],
                    "prefix/helper ancestor or stack canary changed")
            for va, raw in self.loaded_code:
                require(bytes(self.cpu.mem_read(va, len(raw))) == raw, "source emission changed")
            for va, raw in self.native_blocks.items():
                require(bytes(self.cpu.mem_read(va+self.delta, len(raw))) == raw, "native RAM span changed")
            return {name: self.cpu.reg_read(self.regs[name]) for name in GPRS+("EFLAGS", "EIP")}

        def cached_after_epoch(self):
            start = self.epochs[-1][0]
            ranges = ((self.PHYSICAL, self.PHYSICAL+188), (self.PRIVATE, self.PRIVATE+188),
                      (self.BACKEND, self.BACKEND+168), (self.WORLD, self.WORLD+0xf7c))
            return [(pc, at, size) for pc, at, size in self.read_events[start:]
                    if any(at < high and at+size > low for low, high in ranges)]

    return OriginalMachine


class AuthoringTests(unittest.TestCase):
    def test_pins_authored_boundaries_and_false_acceptance(self):
        source_contract()
        self.assertEqual(sum(CALLER_LENGTHS), 42)
        self.assertEqual(sum(PREFIX_LENGTHS), 42)
        self.assertEqual(sum(NATIVE_LENGTHS.values()), 100)
        self.assertEqual(len(HIGHLOW), 3)
        self.assertEqual(BRANCHES[0], (0x42ff82, 0x8d, NO_CALL), "authenticated original JGE role")
        self.assertTrue(all(not value for value in ACCEPTANCE.values()))

    def test_unknown_original_rejects_before_lazy_dependency(self):
        for raw in (b"", b"authored", bytearray(b"authored"), memoryview(b"authored"), None):
            with self.assertRaisesRegex(ValueError, "exact original"):
                authenticate_original(raw)

    def test_independent_flags_phase_arguments_and_domain(self):
        regs = dict(zip(GPRS, (7, 1, 2, 32, 0x30008000, 0, 0, 16)))
        for identity in (0, 7, 21):
            for value in (-1, 0, 34):
                case = Case("oracle", identity=identity, unit_type=value).validate()
                result, mask = oracle(case, regs, 0x40000000, 0x30007ff8, 0)
                self.assertEqual(mask, 0xffffffff)
                self.assertEqual(result["EAX"], u32(value))
                self.assertEqual(result["EDX"], 0x40000000+31*identity)
                self.assertEqual(result["EFLAGS"], 0x646 if value == -1 else 0x613)
                self.assertEqual(len(native_write_oracle(case, 0x30007ff8, 0)), 8)
        self.assertEqual(Case("nonnegative", motion=0).stop(), NO_CALL)
        self.assertEqual(Case("different", active=8).stop(), NO_CALL)
        self.assertEqual(Case("sentinel", identity=-1).stop(), SENTINEL)
        with self.assertRaises(ValueError):
            Case("one-past", identity=22).validate()

    def test_public_api_and_native_observers_have_no_shortcuts(self):
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        api = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_tests")
        self.assertFalse({n.id for n in ast.walk(api) if isinstance(n, ast.Name)} & {
            "load_runtime", "authenticate_original", "OriginalTests", "machine_class",
        })
        factory = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "machine_class")
        machine = next(n for n in factory.body if isinstance(n, ast.ClassDef))
        self.assertNotIn("invoke", [n.name for n in machine.body if isinstance(n, ast.FunctionDef)])
        for name in ("on_code", "on_read", "on_write"):
            method = next(n for n in machine.body if isinstance(n, ast.FunctionDef) and n.name == name)
            self.assertFalse(any(isinstance(n, ast.Attribute) and n.attr in ("reg_write", "mem_write", "ret")
                                 for n in ast.walk(method)), name)


class OriginalTests(unittest.TestCase):
    runtime = None

    def make(self, case, *, joined=True, delta=0, profile="classic", mode=0):
        prior, tools, native, cls = self.runtime
        return cls(tools, native, joined=joined, delta=delta, profile=profile, mode=mode).setup_caller(case)

    def pair(self, case, *, delta=0, profile="classic", mode=0):
        baseline, left = self.make(case, joined=False, delta=delta, profile=profile, mode=mode)
        joined, right = self.make(case, delta=delta, profile=profile, mode=mode)
        self.assertEqual(left, right)
        before, after = baseline.invoke_original(left), joined.invoke_original(right)
        self.assertEqual(before, after)
        expected, mask = oracle(case, right, joined.WORLD, joined.unit_s, delta)
        for name in GPRS+("EIP",):
            self.assertEqual(after[name], expected[name], name)
        self.assertEqual(after["EFLAGS"] & mask, expected["EFLAGS"] & mask)
        self.assertEqual(baseline.native_writes, joined.native_writes)
        self.assertEqual(baseline.native_reads, native_read_oracle(case, joined.WORLD, delta, joined=False))
        self.assertEqual(joined.native_reads, native_read_oracle(case, joined.WORLD, delta, joined=True))
        self.assertEqual(baseline.native_seen, native_pc_oracle(case, joined=False))
        self.assertEqual(joined.native_seen, native_pc_oracle(case, joined=True))
        self.assertEqual(bytes(baseline.cpu.mem_read(baseline.unit_s-64, 72)),
                         bytes(joined.cpu.mem_read(joined.unit_s-64, 72)))
        if case.stop() == RESUME:
            payload = [(joined.WORLD+852+31*case.identity, 2, case.unit_type & 65535)]
            self.assertEqual(baseline.type_payload_reads, payload)
            self.assertEqual(joined.type_payload_reads, payload)
            self.assertEqual(len(joined.epochs), 1)
            self.assertEqual(baseline.epochs, [])
        else:
            self.assertEqual(baseline.type_payload_reads, [])
            self.assertEqual(joined.type_payload_reads, [])
            self.assertEqual(baseline.epochs, [])
            self.assertEqual(joined.epochs, [])
            if case.stop() == NO_CALL:
                self.assertEqual(joined.unit_entries, 0)
                self.assertEqual(joined.native_seen[-1], 0x42ff82 if case.motion >= 0 else 0x42ff8e)
            else:
                self.assertEqual(joined.native_seen[-1], 0x42f836)
        return baseline, joined

    def test_authentic_final_call_prefix_two_bases_and_modes(self):
        for delta in (0, 0x30000):
            for mode in (0, 1):
                self.pair(Case("basic"), delta=delta, mode=mode)

    def test_identity_type_boundaries_and_separate_modal_allocation(self):
        for identity in (0, 7, 21):
            for value in (-1, 0, 34):
                self.pair(Case("identity-type", identity=identity, unit_type=value))
        for delta in (0, 0x30000):
            self.pair(Case("modal", identity=21, flags=0x246), delta=delta, profile="modalwidgets", mode=1)

    def test_genuine_no_call_and_sentinel_branches(self):
        for delta in (0, 0x30000):
            for case in (Case("motion-zero", motion=0), Case("motion-positive", motion=5),
                         Case("identity-mismatch", active=8), Case("sentinel", identity=-1)):
                self.pair(case, delta=delta)

    def test_callback_global_and_witness_loss_is_real_epoch_ud2(self):
        for fault in ("motion", "active", "saved_motion", "captured_self"):
            m, regs = self.make(Case(fault), delta=0x30000)
            changed = []
            def corrupt(mm, epoch):
                if not changed:
                    at = {"motion": MOTION+mm.delta, "active": ACTIVE+mm.delta,
                          "saved_motion": mm.unit_s-12, "captured_self": mm.unit_s-888+404}[fault]
                    mm.put(at, mm.word(at)^1)
                    changed.append(at)
                    mm.protect_cached(mm.u.UC_PROT_NONE)
            with self.assertRaises(m.u.UcError):
                m.invoke_original(regs, fault=corrupt)
            pc = m.cpu.reg_read(m.regs["EIP"])
            self.assertIn(pc, m.unsafe_vas)
            self.assertEqual(bytes(m.cpu.mem_read(pc, 2)), b"\x0f\x0b")
            self.assertEqual(len(changed), 1)
            self.assertEqual(len(m.epochs), 1)
            self.assertEqual(m.cached_after_epoch(), [])
            self.assertEqual(m.type_payload_reads, [])
            self.assertIsNone(m.native_stop)

    def test_native_instruction_and_unit_call_word_cannot_be_shortcut(self):
        m, regs = self.make(Case("instruction"))
        raw = bytes(m.cpu.mem_read(UNIT, 1))
        m.cpu.mem_write(UNIT, bytes([raw[0]^1]))
        m.cpu.ctl_remove_cache(UNIT, UNIT_END)
        with self.assertRaisesRegex(ValueError, "authenticated prefix instruction"):
            m.invoke_original(regs)
        self.assertIsNone(m.native_stop)
        m, regs = self.make(Case("native-word"))
        def corrupt(cpu, pc, size, data):
            if pc == UNIT:
                m.put(m.unit_s, RETURN+4)
        m.cpu.hook_add(m.u.UC_HOOK_CODE, corrupt, begin=UNIT, end=UNIT)
        with self.assertRaisesRegex(ValueError, "genuine Unit CALL return word"):
            m.invoke_original(regs)
        self.assertIsNone(m.native_stop)


def authoring_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(AuthoringTests)


def run_tests():
    """Public source-only API; never original lookup, CPU import or construction."""
    source_contract()
    before = sha(Path(__file__).read_bytes())
    suite = authoring_suite()
    require(suite.countTestCases() == 4, "exact four prefix authoring checks required")
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    source_contract()
    require(sha(Path(__file__).read_bytes()) == before, "prefix authoring source changed")
    require(result.wasSuccessful() and not result.skipped and result.testsRun == 4,
            "strict four-method prefix authoring checks failed or skipped")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", metavar="ORIGINAL_PATH")
    parser.add_argument("--test", action="append", choices=tuple(
        name for name in dir(OriginalTests) if name.startswith("test_")))
    args = parser.parse_args()
    require(not args.test or args.original_backed, "--test requires --original-backed")
    if not args.original_backed:
        run_tests()
        print("Prefix authoring4 PASS; original_prefix_cpu_verified=False; explicit opt-in required.")
        return 0
    source_contract()
    path = Path(args.original_backed)
    native = authenticate_original(path.read_bytes())
    prior, tools, closure = load_runtime()
    OriginalTests.runtime = prior, tools, native, machine_class(prior)
    suite = authoring_suite()
    if args.test:
        for name in args.test:
            suite.addTest(OriginalTests(name))
    else:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(OriginalTests))
    count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    source_contract()
    require(sha(path.read_bytes()) == ORIGINAL_SHA, "original changed during prefix fixture")
    require(all(sha((ROOT/name).read_bytes()) == digest for name, digest in closure.items()),
            "full named prefix source closure changed during tests")
    if result.wasSuccessful() and not result.skipped and result.testsRun == count:
        scope = "selected methods" if args.test else "complete opt-in fixture"
        print("Original final Adjacent/Unit prefix CPU PASS ("+scope+"); stops before Unit resume JE; outer history/Thread modeled; full Unit/ABI/Windows/runtime/installation/input/release/promotion false.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
