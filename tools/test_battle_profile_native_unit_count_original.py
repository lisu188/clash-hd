#!/usr/bin/env python3
"""Opt-in genuine final caller/Unit type-minus-one/Count CPU composition.

Default/public checks are stdlib authoring only. --original-backed reads the
exact user-owned original and reconstructs selected canonical relayout parents
in RAM. Their complete executing caller, Unit prefix/JE, argument preparation,
Count and table spans are authenticated independently before CPU use. The fresh
Atomic V2 helpers retain their explicit synthetic allocations/outer ancestry;
this is not execution of an installed candidate or a production allocation.

The original final CALL, Unit local writes, JE, Count preparation, CALL, body
and RET execute. The self record has a valid index and type -1; identity -1 is
excluded. No source callback substitutes native results. Stop BEFORE 42F95B:
later Unit bodies, Unit RET, final-caller continuation and provider paths remain
outside scope. Thread/outer history remain modeled; no legal live-game record
state, Windows/runtime/input/lifetime/release/promotion proof is supplied.
Healthy saved-ECX push/pop observations do not establish callback-time native
ECX/pop-slot authority; that integrity guarantee remains explicitly unproved.
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
SELF = "tools/test_battle_profile_native_unit_count_original.py"
PREFIX = "tools/test_battle_profile_native_adjacent_prefix_original.py"
READER = "tools/test_battle_profile_native_count_original.py"
ATOMIC = "tools/test_battle_profile_adjacent_unit_v2.py"
CONTEXT = "src/patcher/battle_profile_context_v2.py"
PINNED_FILES = {
    PREFIX: "d77ff1f61c8454ab4026ac7d0470443fb198c43298f834c99996060169f42b17",
    READER: "08f654c676a3d13a9a7e993b701ecdd711d5a8d6bc79227b62357b699368cc9e",
    ATOMIC: "a8fbbccba6151b5f1b6e374be2935db8e8a58348228451380f883a02a685b009",
    "src/patcher/battle_profile_adjacent_unit_v2.py": "b2ae87457bd2344d9e6650032dba46d03a680e2303946acb75abaf0508f5ead8",
    CONTEXT: "d0a8b27ae4d07b290a449c1c875d4b574d329d2a9ac6b1397a2753f7d10ee5c9",
}
ORIGINAL_SHA = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
FINAL, UNIT_CALL, UNIT_RETURN = 0x42ff7a, 0x42ff9f, 0x42ffa4
UNIT, TYPE, JE, UNIT_END = 0x42f820, 0x42f84a, 0x42f854, 0x42f85a
PREP, CALL, STOP = 0x42f93e, 0x42f956, 0x42f95b
COUNT, COUNT_END, COUNT_RET, TABLE = 0x426ef0, 0x426f75, 0x426f74, 0x514500
MOTION, ACTIVE, WORLD_GLOBAL = 0x523f70, 0x512360, 0x532048
SPANS = (
    (FINAL, UNIT_RETURN, "455371cdb73867ea54a97c41442702a4bd2bd88135af9c2a2b2585c2a684c9fa"),
    (UNIT, UNIT_END, "bef712bfb5b35cdcdb6d8f2583b7907f85bed214da9fa244f4d2554dcd18c206"),
    (PREP, STOP, "3a3b97dfaed542b0a2b07474630563d70ce41239ea9af3f6ac3111bdcc902d22"),
    (STOP, STOP+2, "750468e50b8500dfb8f128039880db2804b753a3ffcba500cbba0621b06a948c"),
    (COUNT, COUNT_END, "a97ca326a029c59233d0e8881e5eed3004c8e168d24fd7248a5a78c48c65cf90"),
)
TABLE_SHA = "f5c6bbbf5f45749649807f7d447f200806adb5055b4af1fcb2738ba8786dd59c"
HIGHLOW = ((0x42ff7c, MOTION), (0x42ff8a, ACTIVE), (0x42f841, WORLD_GLOBAL),
           (0x42f942, WORLD_GLOBAL), (0x426f0d, TABLE),
           (0x426f19, WORLD_GLOBAL), (0x426f29, TABLE+4))
PREP_LENGTHS = (2, 6, 3, 6, 2, 2, 3, 5)
WINDOWS = {TYPE: 10, 0x426f44: 11, 0x426f54: 10}
GPRS = ("EAX", "ECX", "EDX", "EBX", "ESP", "EBP", "ESI", "EDI")
ARITH = 0x8d5
ACCEPTANCE = dict(original_unit_count_cpu_verified=False, whole_unit_verified=False,
    all_eight_overrides_verified=False, production_allocation_executed=False,
    native_ecx_pop_slot_authority_verified=False,
    legal_live_game_record_verified=False, mapping_or_lifetime_verified=False,
    native_callback_abi_verified=False, windows_runtime_verified=False, installed=False,
    input_verified=False, release_accepted=False, promotion_ready=False)


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
        require(path.resolve(strict=True) == path and sha(path.read_bytes()) == digest,
                "frozen Unit/Count fixture dependency differs: "+name)


def load_readers():
    """Only pinned stdlib authoring modules; no machine/producer construction."""
    source_contract()
    sys.path[:0] = [str(ROOT), str(ROOT/"tools")]
    result = []
    for name in (PREFIX, READER):
        module = importlib.import_module(Path(name).stem)
        require(Path(module.__file__).resolve() == ROOT/name, "canonical native reader required")
        result.append(module)
    return tuple(result)


@dataclass(frozen=True, repr=False)
class NativeImage:
    blocks: tuple
    table: bytes
    count_image: object
    parent_sha256: str | None = None


def selected_bytes(image, reader):
    """Authenticate all actual selected bytes, including the formerly omitted JE."""
    base, locate, relocs = reader.pe_layout(image)
    require(base == 0x400000, "selected parent preferred base differs")
    get = lambda va, size: image[locate(va, size):locate(va, size)+size]
    blocks = []
    for lo, hi, digest in SPANS:
        raw = get(lo, hi-lo)
        require(len(raw) == hi-lo and sha(raw) == digest,
                "selected executing parent span differs at "+hex(lo))
        blocks.append((lo, raw))
    selected = sorted(va for va in relocs if any(lo <= va < hi for lo, hi, _ in SPANS)
                      or TABLE <= va < TABLE+64)
    require(selected == sorted(va for va, _ in HIGHLOW), "complete selected parent HIGHLOW inventory differs")
    for va, target in HIGHLOW:
        require(get(va, 4) == struct.pack("<I", target), "selected parent HIGHLOW operand differs")
    table = get(TABLE, 64)
    require(sha(table) == TABLE_SHA and table == struct.pack("<16i", *(v for p in reader.NEIGHBORS for v in p)),
            "complete selected parent neighbor table differs")
    require(get(JE, 2) == b"\x0f\x84" and JE+6+struct.unpack("<i", get(JE+2, 4))[0] == PREP,
            "genuine fast type-minus-one JE differs")
    for pc, end, target in ((UNIT_CALL, UNIT_RETURN, UNIT), (CALL, STOP, COUNT)):
        raw = get(pc, 5)
        require(raw[0] == 0xe8 and end+struct.unpack_from("<i", raw, 1)[0] == target,
                "genuine selected native CALL target differs")
    return tuple(blocks), table


def authenticate_original(image):
    require(type(image) is bytes and sha(image) == ORIGINAL_SHA, "exact original required")
    prefix, reader = load_readers()
    prefix.authenticate_original(image)
    count = reader.authenticate_original(image)
    blocks, table = selected_bytes(image, reader)
    return NativeImage(blocks, table, count)


def authenticate_parent(image, native, reader):
    blocks, table = selected_bytes(image, reader)
    require(blocks == native.blocks and table == native.table, "selected parent/original instructions differ")
    return NativeImage(blocks, table, native.count_image, sha(image))


@dataclass(frozen=True)
class Case:
    name: str
    identity: int = 7
    motion: int = -63
    columns: int = 3
    center: tuple = (1, 3)
    occupied: int = 255
    enemies: int = 170
    self_owner: int = 0
    old_esi: int = 0
    old_ebx: int = 32
    old_edi: int = 16
    flags: int = 0xed7

    def validate(self):
        require(0 <= self.identity < 22 and -0x80000000 <= self.motion < 0,
                "fast route needs valid identity 0..21 and signed-negative motion")
        require(1 <= self.columns <= 20 and len(self.center) == 2 and
                0 <= self.center[0] < self.columns and 0 <= self.center[1] < 7 and
                all(0 <= value <= 255 for value in (self.occupied, self.enemies, self.self_owner)),
                "bounded synthetic Count dataset required")
        return self


def add_flags(left, right, incoming):
    left, right = u32(left), u32(right)
    full, result = left+right, u32(left+right)
    flags = int(full > 0xffffffff) | (int((result & 255).bit_count() % 2 == 0) << 2)
    flags |= (left ^ right ^ result) & 0x10
    flags |= int(result == 0) << 6 | (result >> 31) << 7
    flags |= int(bool((~(left ^ right) & (left ^ result)) & 0x80000000)) << 11
    return (incoming & ~ARITH) | flags | 2


def load_runtime(native, original):
    prefix, reader = load_readers()
    prior, tools, closure = prefix.load_runtime()
    decoded = reader.decode_native(tools, native.count_image)
    context = importlib.import_module("src.patcher.battle_profile_context_v2")
    require(Path(context.__file__).resolve() == ROOT/CONTEXT, "canonical parent constructor required")
    parents = {}
    for profile in ("classic", "modalwidgets"):
        value = context.build_allocation_context(original, profile, "800x600")
        require(sha(value.relayout_parent) == value.metadata()["relayout_parent_sha256"],
                "canonical relayout parent receipt differs")
        parents[profile] = (value.relayout_parent, authenticate_parent(value.relayout_parent, native, reader))
    closure |= {name: sha((ROOT/name).read_bytes()) for name in PINNED_FILES}
    closure[SELF] = sha(Path(__file__).read_bytes())
    return prefix, reader, prior, tools, decoded, parents, closure


def machine_class(prefix, reader, prior):
    class OriginalMachine(prior.Machine):
        def __init__(self, tools, native, decoded, *, joined, profile="classic", delta=0, mode=0):
            self.invocation_active = False
            super().__init__(tools, profile, "800x600", delta)
            self.joined, self.mode, self.native_image = joined, mode, native
            self.native_decoded = decoded
            self.native_lengths = dict(prefix.NATIVE_LENGTHS) | prefix.boundaries(PREP, PREP_LENGTHS)
            self.native_lengths |= {pc: len(raw) for pc, raw in decoded.items()} | {STOP: 2}
            self.native_blocks = {va: bytearray(raw) for va, raw in native.blocks}
            for va, target in HIGHLOW:
                hits = [start for start, raw in self.native_blocks.items() if start <= va and va+4 <= start+len(raw)]
                require(len(hits) == 1, "one native HIGHLOW owning span required")
                struct.pack_into("<I", self.native_blocks[hits[0]], va-hits[0], target+delta)
            selected_hooks = {va: self.planned[va] for va in WINDOWS}
            require(len(self.atomic_entry.planned_hooks) == 1 and self.atomic_entry.planned_hooks[0][0] == CALL,
                    "fresh atomic Count entry required")
            _, old, target, role, removed = self.atomic_entry.planned_hooks[0]
            selected_hooks[CALL] = old, target, role, removed
            self.selected_hooks = selected_hooks
            for va, (old, target, _, removed) in selected_hooks.items():
                size = 5 if va == CALL else WINDOWS[va]
                require(len(old) == size and removed == (), "exact selected override window required")
                start = next(start for start, raw in self.native_blocks.items() if start <= va and va+size <= start+len(raw))
                require(bytes(self.native_blocks[start][va-start:va-start+size]) == old,
                        "selected override old bytes differ from executing parent")
                if joined:
                    self.native_blocks[start][va-start:va-start+size] = (
                        b"\xe8"+struct.pack("<i", target-va-5)+b"\x90"*(size-5))
            self.native_blocks = {va: bytes(raw) for va, raw in self.native_blocks.items()}
            for va, raw in self.native_blocks.items():
                self.cpu.mem_write(va+delta, raw)
                self.cpu.ctl_remove_cache(va+delta, va+delta+len(raw))
            self.cpu.mem_write(TABLE+delta, native.table)
            self.body_regions = {row[0]: (row[2]+delta, row[7]+delta)
                                 for row in self.atomic_adapters.body_receipts if row[0] in WINDOWS}
            absolute = {r.offset for r in self.atomic_adapters.relocations if r.kind == "abs32"}
            low, high = self.body_regions[TYPE]
            loads = [self.atomic_adapters.base_va+start+delta
                     for start, end, *_ in prior.replay_fixture.decode(self.atomic_adapters.code, absolute)
                     if low <= self.atomic_adapters.base_va+start+delta < high and
                     self.atomic_adapters.code[start:end] == b"\x0f\xbf\x00"]
            require(len(loads) == 1, "one independently located Type WORD load required")
            self.type_read_pc = loads[0]
            tails = [r for r in self.atomic_adapters.relocations if r.purpose == "native_adjacent_unit_resume"
                     and r.target == 0x426f54+WINDOWS[0x426f54]]
            require(len(tails) == 1, "one independently located owner-CMP tail required")
            self.owner_tail = self.atomic_adapters.base_va+tails[0].offset-4+delta
            require(bytes(self.cpu.mem_read(self.owner_tail, 3)) == b"\x3a\x57\x02", "owner-CMP scalar tail differs")

        def setup_caller(self, case):
            self.case = case.validate()
            self.prefix_case = prefix.Case(case.name, identity=case.identity, motion=case.motion,
                unit_type=-1, old_esi=case.old_esi, old_ebx=case.old_ebx,
                old_edi=case.old_edi, flags=case.flags)
            self.dataset = reader.Dataset(case.name, columns=case.columns, center=case.center,
                self_index=case.identity, occupied=case.occupied, enemies=case.enemies, self_owner=case.self_owner)
            self.prepare(columns=case.columns).begin(self.mode)
            self.setup_body(prior.SITES[0], index=case.identity, via_adjacent=True)
            self.caller_sp = self.adjacent_sp-16
            self.unit_s = self.caller_sp-8
            self.count_s = self.unit_s-68
            require(self.unit_s == self.unit_sp, "modeled outer ancestry stack delta differs")
            # Clear every future Unit/Count native slot. Native instructions,
            # not authored setup, must establish local52 and all saved GPRs.
            self.cpu.mem_write(self.count_s-28, b"\xd7"*(self.unit_s+8-(self.count_s-28)))
            require(self.word(self.adjacent_sp-16) == self.current_cell[0] and
                    self.word(self.adjacent_sp-12) == self.tile_sp-20, "future-stack clear damaged outer controls")
            self.put(MOTION+self.delta, case.motion)
            self.put(ACTIVE+self.delta, case.identity)
            self.put(WORLD_GLOBAL+self.delta, self.WORLD)
            self.input_record = self.WORLD+852+31*case.identity
            self.cpu.mem_write(self.WORLD+1534, b"\xe7\x7f"*400)
            for x in range(case.columns):
                for y in range(7):
                    self.cpu.mem_write(self.WORLD+1534+40*x+2*y, b"\xff\xff")
            for i in range(22):
                at = self.WORLD+852+31*i
                self.cpu.mem_write(at, struct.pack("<hB", -1, case.self_owner))
                self.cpu.mem_write(at+4, struct.pack("<HH", 0, 0))
            # In particular, do NOT reuse Count's old setup that writes type 0.
            self.cpu.mem_write(self.input_record+4, struct.pack("<HH", *case.center))
            self.cpu.mem_write(self.WORLD+1534+40*case.center[0]+2*case.center[1], struct.pack("<h", case.identity))
            for _, x, y, index, owner in self.dataset.cells():
                self.cpu.mem_write(self.WORLD+1534+40*x+2*y, struct.pack("<h", index))
                if index >= 0:
                    at = self.WORLD+852+31*index
                    self.cpu.mem_write(at, struct.pack("<hB", 0, owner))
                    self.cpu.mem_write(at+4, struct.pack("<HH", x, y))
            require(bytes(self.cpu.mem_read(self.input_record, 2)) == b"\xff\xff" and
                    self.word(self.unit_s-28) == 0xd7d7d7d7 and self.word(self.unit_s-52) == 0xd7d7d7d7,
                    "future Unit history was preauthored")
            regs = dict(EAX=case.identity, ECX=0x11223344, EDX=0x22334455,
                        EBX=u32(case.old_ebx), ESP=self.caller_sp, EBP=self.current_cell[1],
                        ESI=u32(case.old_esi), EDI=u32(case.old_edi))
            return self, regs

        def _source_owner(self, pc, size):
            hits = [(va, raw) for va, raw in self.loaded_code if va <= pc and pc+size <= va+len(raw)]
            require(len(hits) == 1, "unexpected or ambiguous surrounding source PC")
            va, raw = hits[0]
            require(bytes(self.cpu.mem_read(pc, size)) == raw[pc-va:pc-va+size], "surrounding source instruction changed")

        def _native_bytes(self, pc, size):
            hits = [(va, raw) for va, raw in self.native_blocks.items() if va <= pc and pc+size <= va+len(raw)]
            require(len(hits) == 1, "native PC escaped selected authenticated spans")
            va, raw = hits[0]
            return raw[pc-va:pc-va+size]

        def _check_unit_word(self):
            require(self.word(self.unit_s) == UNIT_RETURN+self.delta, "genuine Unit CALL return word changed")

        def _thread_mutation(self, machine, label):
            if self.invocation_active and label == "thread":
                self.epochs.append((self.admission, len(self.read_events), len(self.write_events)))
                if self.fault:
                    self.fault(self, len(self.epochs), self.admission)

        def _semantic(self, role, address, size):
            self.semantic_reads.append((role, address-self.WORLD, size,
                                        int.from_bytes(self.cpu.mem_read(address, size), "little")))

        def on_code(self, cpu, address, size, data):
            if not self.invocation_active:
                return super().on_code(cpu, address, size, data)
            pc = address-self.delta
            if pc == STOP:
                require(size == 2 and bytes(cpu.mem_read(address, size)) == self._native_bytes(pc, size) and
                        self.ret_observations == 1 and self.native_returns == 0 and
                        cpu.reg_read(self.regs["ESP"]) == self.unit_s-64 and self.active_scan is None,
                        "genuine Count RET did not reach the exact pre-Unit stop")
                self._check_unit_word()
                self.native_returns += 1
                self.native_stop = address
                cpu.emu_stop()
                return
            if pc in self.native_lengths:
                stolen = next((va for va, width in WINDOWS.items() if va <= pc < va+width), None)
                expected_size = 5 if self.joined and stolen is not None else self.native_lengths[pc]
                require(not self.joined or stolen is None or pc == stolen, "entered stolen native window interior")
                require(size == expected_size and bytes(cpu.mem_read(address, size)) == self._native_bytes(pc, size),
                        "authenticated native instruction or boundary changed")
                require(self.active_scan is None, "native instruction entered during source scan")
                if pc == FINAL:
                    require(not self.native_seen and cpu.reg_read(self.regs["ESP"]) == self.caller_sp,
                            "genuine final caller start differs")
                if pc == UNIT:
                    require(self.native_seen[-1:] == [UNIT_CALL] and self.unit_entries == 0 and
                            cpu.reg_read(self.regs["ESP"]) == self.unit_s, "genuine final CALL did not enter Unit")
                    self._check_unit_word()
                    require(self.word(self.unit_s+4) == u32(self.case.old_ebx+64), "native caller argument differs")
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
                            "genuine first-Type argument phase differs")
                    require(self.native_writes == prefix.native_write_oracle(self.prefix_case, self.unit_s, self.delta),
                            "genuine caller/Unit write history differs")
                    self.type_entries += 1
                    self.admission = "type" if self.joined else None
                if pc == JE:
                    require(self.type_entries == 1 and cpu.reg_read(self.regs["EAX"]) == 0xffffffff and
                            cpu.reg_read(self.regs["EFLAGS"]) & 0x40, "type-minus-one JE precondition differs")
                    self.admission = None
                if pc == PREP:
                    require(self.native_seen[-1:] == [JE] and self.type_entries == 1,
                            "only the valid-index Type JE may enter this Count slice")
                if pc == CALL:
                    expected = dict(EAX=self.input_record, ESI=self.case.identity, EDX=31*self.case.identity,
                                    ECX=u32(self.case.motion+64), EBP=self.unit_s-12, ESP=self.unit_s-64)
                    require(all(cpu.reg_read(self.regs[name]) == value for name, value in expected.items()) and
                            self.word(self.unit_s-52) == u32(self.case.motion+64) and
                            self.word(self.unit_s-28) == 0xd7d7d7d7, "genuine Count preparation/local history differs")
                    self.count_call_regs = {name: cpu.reg_read(self.regs[name]) for name in GPRS+("EFLAGS",)}
                    self.admission = "entry" if self.joined else None
                if COUNT <= pc < COUNT_END:
                    if pc == COUNT:
                        require(not self.native_started and self.native_seen[-1:] == [CALL] and
                                cpu.reg_read(self.regs["ESP"]) == self.count_s and
                                self.word(self.count_s) == STOP+self.delta, "genuine Count CALL/entry differs")
                        self.native_started = True
                        self.native_entry_write_start = len(self.write_events)
                        self.entered = {name: cpu.reg_read(self.regs[name]) for name in GPRS+("EFLAGS",)}
                        expected = dict(self.count_call_regs, ESP=self.count_s)
                        require(self.entered == expected, "Count entry helper changed genuine native inputs")
                        self.admission = None
                    require(self.native_started, "Count interior preceded native prologue")
                    if pc in reader.WINDOW_SIZES:
                        offset = cpu.reg_read(self.regs["EAX"])
                        require(offset % 8 == 0 and offset < 64 and
                                cpu.reg_read(self.regs["EBP"]) == u32(reader.NEIGHBORS[offset//8][1]) and
                                self.word(self.count_s-24) == self.unit_s-12 and
                                self.word(self.count_s-16) == self.case.identity and
                                self.word(self.count_s-8) == u32(self.case.motion+64),
                                "genuine Count saved/live register authority differs")
                        self.body_visits.append((pc, offset))
                        if self.joined:
                            self.admission = "occupant" if pc == 0x426f44 else "owner"
                            self.body_inputs = {name: cpu.reg_read(self.regs[name]) for name in GPRS}
                    if pc in (va+width for va, width in reader.WINDOW_SIZES.items()):
                        self.admission = None
                    if pc == COUNT_RET:
                        require(cpu.reg_read(self.regs["ESP"]) == self.count_s and
                                self.word(self.count_s) == STOP+self.delta, "native Count RET word differs")
                        self.ret_observations += 1
                self.native_seen.append(pc)
                return  # No inherited native stub or callback may dispatch here.
            if address in self.unsafe_vas:
                self._source_owner(address, 2)
                require(bytes(cpu.mem_read(address, 2)) == b"\x0f\x0b", "real UD2 required")
                self.unsafe = True
                return
            if address != self.THREAD:
                self._source_owner(address, size)
            super().on_code(cpu, address, size, data)

        def _occupant_read(self, address, size, regs):
            displacement = regs["ECX"]-self.WORLD
            require(displacement >= 0 and displacement % 40 == 0, "native column pointer differs")
            x, y = displacement//40, regs["EBX"]
            require(0 <= x < self.case.columns and 0 <= y < 7 and size == 2 and
                    address == self.WORLD+1534+40*x+2*y, "occupancy read escaped current arena")
            self._semantic("occupant", address, size)

        def _owner_read(self, address, size, regs):
            require(regs["EDX"] == self.WORLD and regs["ECX"] % 31 == 0 and
                    regs["ECX"]//31 < 22 and size == 1 and address == self.WORLD+854+regs["ECX"],
                    "owner read escaped bounded unit records")
            self._semantic("owner", address, size)

        def on_read(self, cpu, access, address, size, value, data):
            if self.invocation_active and self.active_scan is None:
                actual_pc = cpu.reg_read(self.regs["EIP"])
                pc = actual_pc-self.delta
                self.read_events.append((pc, address, size, self.admission))
                if COUNT <= pc < COUNT_END:
                    stack = self.count_s-28 <= address and address+size <= self.count_s+4
                    fixed = address == WORLD_GLOBAL+self.delta and size == 4
                    table = TABLE+self.delta <= address and address+size <= TABLE+self.delta+64 and size == 4
                    header = address in (self.WORLD+800, self.WORLD+804) and size == 4
                    record = ((pc == 0x426efd and address == self.input_record+4 and size == 2) or
                              (pc == 0x426f2d and address == self.input_record+6 and size == 2) or
                              (pc == 0x426f5b and address == self.input_record+2 and size == 1))
                    require(stack or fixed or table or header or record or pc in reader.WINDOW_SIZES,
                            "native Count read escaped declared fields/stack")
                    if table:
                        offset = cpu.reg_read(self.regs["EAX"])
                        require(offset % 8 == 0 and offset < 64 and
                                address in (TABLE+self.delta+offset, TABLE+self.delta+offset+4),
                                "native neighbor table read differs")
                    if pc == 0x426f44:
                        self._occupant_read(address, size, {n: cpu.reg_read(self.regs[n]) for n in GPRS})
                    elif pc == 0x426f54:
                        self._owner_read(address, size, {n: cpu.reg_read(self.regs[n]) for n in GPRS})
                    elif pc == 0x426f5b:
                        self._semantic("input_owner", address, size)
                elif pc in self.native_lengths:
                    expected = {FINAL: (MOTION+self.delta, 4), 0x42ff88: (ACTIVE+self.delta, 4),
                        0x42f83f: (WORLD_GLOBAL+self.delta, 4), TYPE: (self.input_record, 2),
                        0x42f940: (WORLD_GLOBAL+self.delta, 4), 0x42f953: (self.unit_s-52, 4)}
                    require(expected.get(pc) == (address, size), "native Unit/caller read escaped exact contract")
                    self.unit_reads.append((pc, address, size))
                    if pc == TYPE:
                        self.type_reads.append((address, size, int.from_bytes(cpu.mem_read(address, size), "little")))
                elif actual_pc == self.type_read_pc:
                    require(self.joined and address == self.input_record and size == 2, "joined Type payload read differs")
                    self.type_reads.append((address, size, int.from_bytes(cpu.mem_read(address, size), "little")))
                elif self.joined and self.admission in ("occupant", "owner"):
                    va = 0x426f44 if self.admission == "occupant" else 0x426f54
                    low, high = self.body_regions[va]
                    if low <= actual_pc < high:
                        if self.admission == "occupant" and self.WORLD+1534 <= address < self.WORLD+2334:
                            self._occupant_read(address, size, self.body_inputs)
                        elif self.admission == "owner" and size == 1 and self.WORLD+852 <= address < self.WORLD+1534:
                            self._owner_read(address, size, self.body_inputs)
                    if actual_pc == self.owner_tail:
                        require(address == self.input_record+2 and size == 1, "replayed owner-CMP read differs")
                        self._semantic("input_owner", address, size)
            super().on_read(cpu, access, address, size, value, data)

        def on_write(self, cpu, access, address, size, value, data):
            if self.invocation_active:
                pc = cpu.reg_read(self.regs["EIP"])-self.delta
                event = pc, address, size, value
                self.write_events.append(event)
                if FINAL <= pc < UNIT_RETURN or UNIT <= pc < TYPE:
                    expected = prefix.native_write_oracle(self.prefix_case, self.unit_s, self.delta)
                    require(self.native_writes == expected[:len(self.native_writes)] and
                            expected[len(self.native_writes):len(self.native_writes)+1] == [event],
                            "native caller/Unit write escaped exact ordered inventory")
                    self.native_writes.append(event)
                elif pc == CALL:
                    require((address, size, value) == (self.count_s, 4, STOP+self.delta), "Count CALL word differs")
                    self.native_writes.append(event)
                elif self.joined and pc in WINDOWS:
                    slot = self.unit_s-68 if pc == TYPE else self.count_s-32
                    require((address, size, value) == (slot, 4, pc+self.delta+5), "body adapter CALL slot differs")
                elif COUNT <= pc < COUNT_END:
                    pushes = {COUNT+i: (self.count_s-4*(i+1), self.entered[name])
                              for i, name in enumerate(("EBX", "ECX", "EDX", "ESI", "EDI", "EBP"))}
                    expected = pushes | {0x426f03: (self.count_s-28, self.case.center[0])}
                    require(pc in expected and (address, value) == expected[pc] and size == 4,
                            "native Count write escaped genuine saved registers/local")
                    self.native_writes.append(event)
                else:
                    if self.admission == "type":
                        low, high = self.unit_s-932, self.unit_s-64
                    elif self.admission == "entry":
                        low, high = self.count_s-864, self.count_s
                    else:
                        require(self.admission in ("occupant", "owner"), "unexpected source write outside admission")
                        low, high = self.count_s-896, self.count_s-28
                    require(low <= address and address+size <= high, "source helper wrote outside its own stack lifetime")
            super().on_write(cpu, access, address, size, value, data)

        def invoke_original(self, regs, *, fault=None):
            self.fault, self.mutation = fault, self._thread_mutation
            self.stops = set()
            self.native_stop, self.unsafe, self.active_scan = None, False, None
            self.unit_entries = self.type_entries = self.native_returns = self.ret_observations = 0
            self.native_started, self.native_entry_write_start = False, None
            self.native_seen, self.native_writes, self.unit_reads, self.type_reads = [], [], [], []
            self.body_visits, self.semantic_reads, self.read_events, self.write_events, self.epochs = [], [], [], [], []
            self.admission, self.entered, self.count_call_regs = None, None, None
            self.content_reads, self.content_writes, self.content_events = [], [], []
            self.content_after_thread = False
            self.minimum_sp, self.before_callbacks = regs["ESP"], len(self.callbacks)
            self.world_before = bytes(self.cpu.mem_read(self.WORLD, 0xf7c))
            self.owner_before, self.lease_before = self.record(), bytes(self.cpu.mem_read(self.lease_frame, 192))
            self.stack_before = bytes(self.cpu.mem_read(self.STACK, 0x10000))
            for name, value in regs.items():
                self.cpu.reg_write(self.regs[name], u32(value))
            self.cpu.reg_write(self.regs["EFLAGS"], self.case.flags)
            self.invocation_active = self.content_active = True
            try:
                self.cpu.emu_start(FINAL+self.delta, self.STOP+1, count=12000000)
            finally:
                self.invocation_active = self.content_active = False
            require(self.native_stop == STOP+self.delta and self.native_returns == 1 and not self.unsafe,
                    "genuine caller/Unit/Count composition did not return at bounded stop")
            require(bytes(self.cpu.mem_read(self.WORLD, 0xf7c)) == self.world_before and self.record() == self.owner_before and
                    bytes(self.cpu.mem_read(self.lease_frame, 192)) == self.lease_before,
                    "healthy native composition changed world/owner/lease")
            after = bytes(self.cpu.mem_read(self.STACK, 0x10000))
            low, high = self.count_s-896-self.STACK, self.unit_s+8-self.STACK
            require(after[:low] == self.stack_before[:low] and after[high:] == self.stack_before[high:],
                    "native/helper stack canary or ancestor changed")
            require(self.word(self.unit_s-28) == 0xd7d7d7d7 and
                    self.word(self.unit_s-52) == u32(self.case.motion+64), "native Unit local history changed")
            for va, raw in self.loaded_code:
                require(bytes(self.cpu.mem_read(va, len(raw))) == raw, "source emission changed")
            for va, raw in self.native_blocks.items():
                require(bytes(self.cpu.mem_read(va+self.delta, len(raw))) == raw, "selected native span changed")
            require(bytes(self.cpu.mem_read(TABLE+self.delta, 64)) == self.native_image.table, "native neighbor table changed")
            return {n: self.cpu.reg_read(self.regs[n]) for n in GPRS+("EFLAGS", "EIP")}

        def cached_after_epoch(self):
            start = self.epochs[-1][1]
            ranges = ((self.PHYSICAL, self.PHYSICAL+188), (self.PRIVATE, self.PRIVATE+188),
                      (self.BACKEND, self.BACKEND+168), (self.WORLD, self.WORLD+0xf7c))
            return [(pc, at, size) for pc, at, size, _ in self.read_events[start:]
                    if any(at < high and at+size > low for low, high in ranges)]

    return OriginalMachine


class AuthoringTests(unittest.TestCase):
    def test_frozen_dependencies_complete_parent_windows_and_false_claims(self):
        source_contract()
        prefix, reader = load_readers()
        self.assertEqual(sum(PREP_LENGTHS), STOP-PREP)
        self.assertEqual(set(WINDOWS), {TYPE, 0x426f44, 0x426f54})
        self.assertEqual(dict((lo, digest) for lo, _, digest in SPANS)[COUNT], reader.COUNT_SHA)
        self.assertEqual(prefix.RESUME, JE)
        self.assertFalse(any(ACCEPTANCE.values()))

    def test_unknown_original_rejects_before_lazy_reader(self):
        from unittest.mock import patch
        with patch(__name__+".load_readers", side_effect=AssertionError("reader opened")):
            for raw in (b"", b"authored PE", bytearray(b"x"), None):
                with self.assertRaisesRegex(ValueError, "exact original"):
                    authenticate_original(raw)

    def test_valid_identity_type_sentinel_distinction_and_motion_domain(self):
        for n in (0, 7, 21):
            for motion in (-63, -64, -65):
                self.assertEqual(Case("scope", identity=n, motion=motion).validate().identity, n)
        for n in (-1, 22):
            with self.assertRaises(ValueError):
                Case("excluded", identity=n).validate()
        for motion in (0, 1, -0x80000001):
            with self.assertRaises(ValueError):
                Case("excluded", motion=motion).validate()

    def test_independent_arithmetic_and_neighbor_oracle(self):
        self.assertEqual(add_flags(0xffffffff, 1, 0x202) & ARITH, 0x55)
        self.assertEqual(add_flags(0x7fffffff, 1, 0x202) & ARITH, 0x894)
        _, reader = load_readers()
        total, rows = reader.Dataset("full", enemies=255).oracle()
        self.assertEqual(total, 8)
        self.assertEqual(len(rows), 24)
        self.assertEqual(reader.Dataset("empty", occupied=0).oracle()[0], 0)

    def test_public_default_and_observers_cannot_fabricate_native_state(self):
        tree = ast.parse(Path(__file__).read_bytes())
        factory = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "machine_class")
        cls = next(n for n in factory.body if isinstance(n, ast.ClassDef))
        self.assertNotIn("invoke", [n.name for n in cls.body if isinstance(n, ast.FunctionDef)])
        for name in ("on_code", "on_read", "on_write"):
            method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
            self.assertFalse(any(isinstance(n, ast.Attribute) and n.attr in ("reg_write", "mem_write", "ret")
                                 for n in ast.walk(method)), name)
        public = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_tests")
        self.assertFalse(any(isinstance(n, ast.Name) and n.id in ("load_runtime", "machine_class", "authenticate_original")
                             for n in ast.walk(public)))


class OriginalTests(unittest.TestCase):
    runtime = None

    def make(self, case, *, joined=True, delta=0, profile="classic", mode=0):
        prefix, reader, prior, tools, decoded, parents, cls = self.runtime
        return cls(tools, parents[profile][1], decoded, joined=joined, delta=delta, profile=profile, mode=mode).setup_caller(case)

    def pair(self, case, **options):
        baseline, left = self.make(case, joined=False, **options)
        joined, right = self.make(case, **options)
        self.assertEqual(left, right)
        before, after = baseline.invoke_original(left), joined.invoke_original(right)
        self.assertEqual(before, after)
        count, semantic = joined.dataset.oracle()
        expected = dict(EAX=count, ESI=case.identity, EDX=31*case.identity, ECX=u32(case.motion+64),
                        EBX=u32(case.old_edi), EDI=u32(case.old_edi), EBP=joined.unit_s-12,
                        ESP=joined.unit_s-64, EIP=STOP+joined.delta)
        for name, value in expected.items():
            self.assertEqual(after[name], value, name)
        self.assertEqual(after["EFLAGS"] & ARITH, add_flags(joined.count_s-28, 4, case.flags) & ARITH)
        self.assertEqual(baseline.native_writes, joined.native_writes)
        self.assertEqual(baseline.entered, joined.entered)
        self.assertEqual(baseline.body_visits, joined.body_visits)
        self.assertEqual(tuple(baseline.semantic_reads), semantic)
        self.assertEqual(tuple(joined.semantic_reads), semantic)
        self.assertEqual(baseline.type_reads, [(joined.input_record, 2, 65535)])
        self.assertEqual(joined.type_reads, baseline.type_reads)
        self.assertEqual(baseline.epochs, [])
        occupied = sum(index >= 0 for _, _, _, index, _ in joined.dataset.cells())
        self.assertEqual(len(joined.epochs), 2+len(joined.dataset.cells())+occupied)
        self.assertEqual([row[0] for row in joined.epochs[:2]], ["type", "entry"])
        self.assertTrue(all(name == "thread" for name in joined.callbacks[joined.before_callbacks:]))
        # Compare the actual native stack frame, not source helper scratch.
        self.assertEqual(bytes(baseline.cpu.mem_read(baseline.count_s-28, joined.unit_s+8-(joined.count_s-28))),
                         bytes(joined.cpu.mem_read(joined.count_s-28, joined.unit_s+8-(joined.count_s-28))))
        return baseline, joined

    def test_genuine_continuation_smoke(self):
        self.pair(Case("smoke"))

    def test_two_bases_modes_and_all_eight_count_neighbors(self):
        for delta in (0, 0x30000):
            for mode in (0, 1):
                _, joined = self.pair(Case("central", identity=7), delta=delta, mode=mode)
                self.assertEqual({offset for va, offset in joined.body_visits if va == 0x426f54}, set(range(0, 64, 8)))

    def test_identity_motion_ecx_domains_and_separate_modal_allocation(self):
        for identity in (0, 7, 21):
            for motion in (-63, -64, -65):
                self.pair(Case("phase", identity=identity, motion=motion))
        for delta in (0, 0x30000):
            self.pair(Case("modal", identity=21, motion=-65, flags=0x246), delta=delta, profile="modalwidgets", mode=1)

    def test_empty_edges_sparse_records_and_owner_extremes(self):
        for case in (Case("empty", occupied=0), Case("same", enemies=0, self_owner=255),
                     Case("top", center=(0, 0), enemies=255), Case("bottom", center=(2, 6)),
                     Case("narrow", columns=1, center=(0, 3)),
                     Case("wide", columns=20, center=(19, 3), self_owner=254)):
            self.pair(case, delta=0x30000)
        for bit in range(8):
            self.pair(Case("sparse", occupied=1 << bit, enemies=1 << bit))

    def terminal(self, machine, regs, fault):
        with self.assertRaises(machine.u.UcError):
            machine.invoke_original(regs, fault=fault)
        pc = machine.cpu.reg_read(machine.regs["EIP"])
        self.assertIn(pc, machine.unsafe_vas)
        self.assertEqual(bytes(machine.cpu.mem_read(pc, 2)), b"\x0f\x0b")
        self.assertTrue(machine.unsafe)
        self.assertIsNone(machine.native_stop)
        self.assertEqual(machine.native_returns, 0)
        self.assertEqual(machine.cached_after_epoch(), [])

    def test_callback_motion_identity_count_ancestry_loss(self):
        for role, fault in (("type", "motion"), ("entry", "active"),
                            ("occupant", "saved_ebp"), ("owner", "saved_identity")):
            m, regs = self.make(Case("control"), delta=0x30000, profile="modalwidgets")
            changed = []
            def corrupt(mm, epoch, admission):
                if admission == role and not changed:
                    at = {"motion": MOTION+mm.delta, "active": ACTIVE+mm.delta,
                          "saved_ebp": mm.count_s-24, "saved_identity": mm.count_s-16}[fault]
                    mm.put(at, mm.word(at)^1)
                    changed.append(at)
                    mm.protect_cached(mm.u.UC_PROT_NONE)
            self.terminal(m, regs, corrupt)
            self.assertEqual(len(changed), 1)
            self.assertEqual(m.epochs[-1][0], role)

    def test_genuine_count_local_and_paired_shadow_loss_are_not_repaired(self):
        for role in ("occupant", "owner"):
            for paired in (False, True):
                m, regs = self.make(Case("local"), delta=0x30000)
                changed = []
                def corrupt(mm, epoch, admission):
                    if admission == role and not changed:
                        at, helper = mm.count_s-28, mm.count_s-852
                        self.assertEqual(mm.word(at), mm.case.center[0])
                        self.assertEqual(mm.word(helper+376), mm.word(at))
                        self.assertEqual(mm.word(helper+648), mm.word(at))
                        mm.put(at, mm.word(at)^1)
                        if paired:
                            mm.put(helper+376, mm.word(helper+376)^1)
                        changed.append(len(mm.write_events))
                        mm.protect_cached(mm.u.UC_PROT_NONE)
                self.terminal(m, regs, corrupt)
                self.assertEqual(len(changed), 1)
                self.assertEqual(m.word(m.count_s-28), m.case.center[0]^1)
                self.assertFalse(any(at < m.count_s-24 and at+size > m.count_s-28
                                     for _, at, size, _ in m.write_events[changed[0]:]))
                writes = [(pc, at, size) for pc, at, size, _ in m.write_events[m.native_entry_write_start:]
                          if at < m.count_s-24 and at+size > m.count_s-28]
                self.assertEqual(writes, [(0x426f03, m.count_s-28, 4)])

    def test_selected_parent_je_preparation_and_call_tampering_rejects(self):
        _, reader, _, _, _, parents, _ = self.runtime
        for profile, (image, native) in parents.items():
            _, locate, _ = reader.pe_layout(image)
            for va in (JE, PREP, 0x42f953, CALL, COUNT, TABLE):
                changed = bytearray(image)
                changed[locate(va, 1)] ^= 1
                with self.assertRaises(ValueError):
                    authenticate_parent(bytes(changed), native, reader)

    def test_native_instruction_call_return_and_identity_scope_cannot_be_shortcut(self):
        for va in (JE, PREP, CALL, COUNT):
            m, regs = self.make(Case("code"))
            old = bytes(m.cpu.mem_read(va, 1))
            m.cpu.mem_write(va, bytes([old[0]^1]))
            m.cpu.ctl_remove_cache(va, va+16)
            with self.assertRaises((ValueError, m.u.UcError)):
                m.invoke_original(regs)
            self.assertIsNone(m.native_stop)
        for pc, slot in ((UNIT, "unit_s"), (COUNT_RET-1, "count_s")):
            m, regs = self.make(Case("return"))
            def corrupt(cpu, address, size, data):
                m.put(getattr(m, slot), m.word(getattr(m, slot))^4)
            m.cpu.hook_add(m.u.UC_HOOK_CODE, corrupt, begin=pc, end=pc)
            with self.assertRaisesRegex(ValueError, "return.word|RET word"):
                m.invoke_original(regs)
            self.assertIsNone(m.native_stop)
        m, regs = self.make(Case("identity-sentinel"))
        regs["EAX"] = 0xffffffff
        m.put(ACTIVE, 0xffffffff)
        with self.assertRaisesRegex(ValueError, "valid-index Type JE"):
            m.invoke_original(regs)
        self.assertFalse(m.native_started)


def authoring_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(AuthoringTests)


def run_tests():
    """Public source-only API: no original, parent construction or CPU import."""
    source_contract()
    before = sha(Path(__file__).read_bytes())
    suite = authoring_suite()
    require(suite.countTestCases() == 5, "exact five authoring checks required")
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    source_contract()
    require(sha(Path(__file__).read_bytes()) == before, "authoring source changed")
    require(result.wasSuccessful() and not result.skipped and result.testsRun == 5,
            "strict Unit/Count authoring checks failed or skipped")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", metavar="ORIGINAL_PATH")
    parser.add_argument("--test", action="append", choices=tuple(n for n in dir(OriginalTests) if n.startswith("test_")))
    args = parser.parse_args()
    require(not args.test or args.original_backed, "--test requires --original-backed")
    if not args.original_backed:
        run_tests()
        print("Unit/Count authoring5 PASS; original_unit_count_cpu_verified=False; explicit opt-in required.")
        return 0
    path = Path(args.original_backed)
    original = path.read_bytes()
    native = authenticate_original(original)
    prefix, reader, prior, tools, decoded, parents, closure = load_runtime(native, original)
    OriginalTests.runtime = prefix, reader, prior, tools, decoded, parents, machine_class(prefix, reader, prior)
    suite = authoring_suite()
    if args.test:
        for name in args.test:
            suite.addTest(OriginalTests(name))
    else:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(OriginalTests))
    count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    source_contract()
    require(sha(path.read_bytes()) == ORIGINAL_SHA, "original changed during Unit/Count fixture")
    require(all(sha((ROOT/name).read_bytes()) == digest for name, digest in closure.items()),
            "named Unit/Count source closure changed during tests")
    if result.wasSuccessful() and not result.skipped and result.testsRun == count:
        scope = "selected methods" if args.test else "complete opt-in fixture"
        print("Genuine final caller/Unit type-1/Count CPU PASS ("+scope+"); stop before42F95B; four adapter locations only; canonical parent slices, synthetic helper allocation/outer history/Thread; legal live record/full Unit/ABI/Windows/installation/input/release/promotion false.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
