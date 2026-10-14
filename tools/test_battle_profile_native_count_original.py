#!/usr/bin/env python3
"""Opt-in original Count opcodes on synthetic outer frames, never Windows/runtime.

Default authoring checks do not open a game file, import a CPU interpreter or
construct a machine. --original-backed explicitly authenticates the user-owned
original in RAM, then compares untouched Count with Entry50bf/CountBodyV2 RAM-only
CALL windows. Original Count instructions, including its prologue and RET0,
execute without a Count stub, result callback or native-read shortcut. Thread
and the surrounding Unit/Tile/Field ancestry remain authored models. The final
Adjacent caller42FFA4 is excluded. No candidate, capture or proprietary export
is written, and no Windows/game/runtime/full-ABI/installation proof is supplied.
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
ORIGINAL_SHA = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
PINNED_FILES = {
    "src/patcher/battle_profile_count_entry.py": "50bf7d588bd41102ba7170f6a53ff9f65a22496b5d9ea13586496196a7cc2ac4",
    "src/patcher/battle_profile_count_body_v2.py": "b42d1724edb3eb6ba1a393884a8ceff0f590d61368fe438c4b003ad2997b1d8d",
    "tools/test_battle_profile_count_entry.py": "b927ee3d1a0bf55f6ca46dfe4915adf9b60d783aec7c2a6d4f95cf75462da73c",
    "tools/test_battle_profile_count_body_v2.py": "80ebeb87f50959890b6eb8d6df6bb2dfc398c750419137f9e51c7a4b14505ecc",
}
COUNT, COUNT_END, COUNT_RET = 0x426ef0, 0x426f75, 0x426f74
CALL, RETURN, TABLE, WORLD_GLOBAL = 0x42f956, 0x42f95b, 0x514500, 0x532048
COUNT_SHA = "a97ca326a029c59233d0e8881e5eed3004c8e168d24fd7248a5a78c48c65cf90"
TABLE_SHA = "f5c6bbbf5f45749649807f7d447f200806adb5055b4af1fcb2738ba8786dd59c"
HIGHLOW = ((0x426f0d, TABLE), (0x426f19, WORLD_GLOBAL), (0x426f29, TABLE+4))
BRANCHES = {0x426f15: 0x426f61, 0x426f23: 0x426f61,
            0x426f35: 0x426f61, 0x426f3d: 0x426f61,
            0x426f4f: 0x426f61, 0x426f5e: 0x426f61, 0x426f67: 0x426f08}
# Independently authored directional/domain metadata, not a native-byte export.
NEIGHBORS = ((0, -1), (1, -1), (1, 0), (1, 1),
             (0, 1), (-1, 1), (-1, 0), (-1, -1))
WINDOW_SIZES = {0x426f44: 11, 0x426f54: 10}
GPRS = ("EAX", "ECX", "EDX", "EBX", "ESP", "EBP", "ESI", "EDI")
ACCEPTANCE = dict(original_opcode_cpu_verified=False, windows_runtime_verified=False,
                  game_runtime_verified=False, native_callback_abi_verified=False,
                  whole_chain_native_abi_verified=False, installed=False,
                  full_battle_verified=False, input_verified=False,
                  release_accepted=False, promotion_ready=False)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_contract():
    for name, digest in PINNED_FILES.items():
        path = ROOT/name
        require(path.resolve(strict=True) == path, "canonical Count fixture source required")
        require(sha(path.read_bytes()) == digest, "frozen Count fixture dependency differs: "+name)


def pe_layout(image):
    """Strict file-backed PE32 spans and the complete original HIGHLOW list."""
    require(type(image) is bytes and len(image) >= 64 and image[:2] == b"MZ", "invalid original PE")
    pe = struct.unpack_from("<I", image, 60)[0]
    require(pe+24 <= len(image) and image[pe:pe+4] == b"PE\0\0", "invalid PE signature")
    machine, count = struct.unpack_from("<HH", image, pe+4)
    size = struct.unpack_from("<H", image, pe+20)[0]
    optional = pe+24
    require(machine == 0x14c and size >= 144 and optional+size+40*count <= len(image),
            "bounded x86 optional/section headers required")
    require(struct.unpack_from("<H", image, optional)[0] == 0x10b, "PE32 required")
    base = struct.unpack_from("<I", image, optional+28)[0]
    reloc_rva, reloc_size = struct.unpack_from("<II", image, optional+136)
    sections = []
    for i in range(count):
        _, rva, raw_size, raw = struct.unpack_from("<IIII", image, optional+size+i*40+8)
        require(raw+raw_size <= len(image), "section file extent invalid")
        sections.append((rva, raw_size, raw))

    def locate(va, length):
        hits = [raw+va-base-rva for rva, length_on_disk, raw in sections
                if rva <= va-base and va-base+length <= rva+length_on_disk]
        require(length > 0 and len(hits) == 1, "native span lacks unique file-backed extent")
        return hits[0]

    at = locate(base+reloc_rva, reloc_size)
    end, relocs = at+reloc_size, []
    while at < end:
        require(at+8 <= end, "truncated native relocation block")
        page, length = struct.unpack_from("<II", image, at)
        require(length >= 8 and length % 2 == 0 and at+length <= end, "invalid native relocation block")
        for p in range(at+8, at+length, 2):
            item = struct.unpack_from("<H", image, p)[0]
            require(item >> 12 in (0, 3), "unsupported native relocation type")
            if item >> 12 == 3:
                relocs.append(base+page+(item & 4095))
        at += length
    require(len(set(relocs)) == len(relocs), "duplicate native HIGHLOW")
    return base, locate, tuple(relocs)


@dataclass(frozen=True)
class NativeImage:
    count: bytes
    table: bytes
    call: bytes


def authenticate_original(image):
    require(type(image) is bytes and sha(image) == ORIGINAL_SHA, "exact original required")
    base, locate, relocs = pe_layout(image)
    require(base == 0x400000, "native preferred base differs")
    get = lambda va, size: image[locate(va, size):locate(va, size)+size]
    count, table, call = get(COUNT, 133), get(TABLE, 64), get(CALL, 5)
    require(sha(count) == COUNT_SHA and sha(table) == TABLE_SHA, "whole Count/table identity differs")
    require(table == struct.pack("<16i", *(v for pair in NEIGHBORS for v in pair)),
            "complete authored neighbor table differs")
    require(tuple(sorted(va for va in relocs if COUNT <= va < COUNT_END)) == tuple(va for va, _ in HIGHLOW),
            "complete native Count HIGHLOW inventory differs")
    for va, target in HIGHLOW:
        require(get(va, 4) == struct.pack("<I", target), "native Count HIGHLOW target differs")
    require(call[:1] == b"\xe8" and RETURN+struct.unpack_from("<i", call, 1)[0] == COUNT,
            "original Count draw CALL differs")
    require(not any(CALL <= va < RETURN or TABLE <= va < TABLE+64 for va in relocs),
            "unexpected CALL/table HIGHLOW")
    return NativeImage(count, table, call)


def decode_native(tools, native):
    """Discover boundaries by advancing EIP before any original instruction runs."""
    u, regs = tools
    cpu = u.Uc(u.UC_ARCH_X86, u.UC_MODE_32)
    cpu.mem_map(COUNT & ~4095, 4096)
    cpu.mem_write(COUNT, native.count)
    rows = {}

    def skip(machine, pc, size, data):
        require(1 <= size <= 15 and pc+size <= COUNT_END, "native instruction exceeds authenticated Count")
        rows[pc] = bytes(machine.mem_read(pc, size))
        machine.reg_write(regs.UC_X86_REG_EIP, pc+size)

    cpu.hook_add(u.UC_HOOK_CODE, skip)
    cpu.emu_start(COUNT, COUNT_END, count=133)
    require(len(rows) == 51 and sum(map(len, rows.values())) == 133, "complete native Count decode differs")
    branches, returns = {}, {}
    for pc, raw in rows.items():
        require(raw[0] not in (0xe8, 0x9a, 0xca, 0xcb) and not
                (raw[0] == 0xff and (raw[1] >> 3) & 7 in (2, 3, 4, 5)),
                "unexpected original Count CALL/indirect/far transfer")
        if raw[0] in (0xc2, 0xc3):
            returns[pc] = struct.unpack_from("<H", raw, 1)[0] if raw[0] == 0xc2 else 0
        if raw[0] == 0xeb or 0x70 <= raw[0] <= 0x7f:
            branches[pc] = pc+len(raw)+struct.unpack_from("<b", raw, len(raw)-1)[0]
        elif raw[:1] == b"\x0f" and 0x80 <= raw[1] <= 0x8f:
            branches[pc] = pc+len(raw)+struct.unpack_from("<i", raw, len(raw)-4)[0]
        elif raw[0] == 0xe9:
            raise ValueError("unexpected original Count unconditional transfer")
    require(branches == BRANCHES and returns == {COUNT_RET: 0} and
            all(target in rows for target in branches.values()), "native Count control/RET closure differs")
    return rows


@dataclass(frozen=True)
class Dataset:
    name: str
    columns: int = 3
    center: tuple = (1, 3)
    self_index: int = 21
    occupied: int = 255
    enemies: int = 170
    self_owner: int = 0

    def cells(self):
        require(1 <= self.columns <= 20 and 0 <= self.center[0] < self.columns and
                0 <= self.center[1] < 7 and 0 <= self.self_index < 22 and
                0 <= self.occupied <= 255 and 0 <= self.enemies <= 255 and 0 <= self.self_owner <= 255,
                "bounded authored Count dataset required")
        records = [i for i in range(22) if i != self.self_index]
        result = []
        for i, (dx, dy) in enumerate(NEIGHBORS):
            x, y = self.center[0]+dx, self.center[1]+dy
            if 0 <= x < self.columns and 0 <= y < 7:
                index = records[i] if self.occupied & (1 << i) else -1
                owner = self.self_owner ^ int(bool(self.enemies & (1 << i)))
                result.append((i, x, y, index, owner))
        return tuple(result)

    def oracle(self):
        """Independent semantic reads and enemy count, not an emitter ledger."""
        reads, total = [], 0
        for _, x, y, index, owner in self.cells():
            reads.append(("occupant", 1534+40*x+2*y, 2, index & 65535))
            if index != -1:
                reads.append(("owner", 854+31*index, 1, owner))
                reads.append(("input_owner", 854+31*self.self_index, 1, self.self_owner))
                total += owner != self.self_owner
        return total, tuple(reads)


def load_runtime(native):
    # Deliberately lazy: no CPU or source-emission constructor in default mode.
    source_contract()
    sys.path[:0] = [str(ROOT), str(ROOT/"tools")]
    prior = importlib.import_module("test_battle_profile_count_body_v2")
    closure = prior.source_closure()
    closure["tools/test_battle_profile_native_count_original.py"] = sha(Path(__file__).read_bytes())
    tools = prior.replay_fixture.tile_fixture.content_fixture.parent_fixture.field_fixture.routing_fixture.lifetime.prior_fixture.machine_tools()
    require(tools is not None, "original-backed Count requires the real Unicorn interpreter")
    return prior, tools, decode_native(tools, native), closure


def machine_class(prior):
    class OriginalMachine(prior.Machine):
        """Only Count executes originally; every outer authority stays modeled."""
        def __init__(self, tools, native, decoded, *, joined, profile="classic", delta=0, mode=0):
            self.invocation_active = False
            self.native_started = False
            self.joined, self.native_image, self.native_decoded = joined, native, decoded
            super().__init__(tools, profile, "800x600", delta)
            self.mode = mode
            self.expected_native = bytearray(native.count)
            for va, target in HIGHLOW:
                struct.pack_into("<I", self.expected_native, va-COUNT, target+delta)
            self.expected_call = native.call
            if joined:
                target = dict(self.count_emission.entries)["count_entry"]+delta
                self.expected_call = b"\xe8"+struct.pack("<i", target-CALL-delta-5)
                for va, old, target, role, removed in self.body.planned_hooks:
                    require(va in WINDOW_SIZES and len(old) == WINDOW_SIZES[va] and removed == (),
                            "exact two corrected RAM-only Count windows required")
                    require(native.count[va-COUNT:va-COUNT+len(old)] == old, "Count window differs from original")
                    hook = b"\xe8"+struct.pack("<i", target-va-5)+b"\x90"*(len(old)-5)
                    self.expected_native[va-COUNT:va-COUNT+len(old)] = hook
            self.expected_native = bytes(self.expected_native)
            self.cpu.mem_write(COUNT+delta, self.expected_native)
            self.cpu.mem_write(TABLE+delta, native.table)
            self.cpu.mem_write(CALL+delta, self.expected_call)
            self.cpu.ctl_remove_cache(COUNT+delta, COUNT_END+delta)
            self.cpu.ctl_remove_cache(CALL+delta, RETURN+delta)
            self.body_regions = {}
            for row in self.body.body_receipts:
                va, entry, payload, pc, denied, fault, valid, finish, resume = row
                self.body_regions[va] = payload+delta, finish+delta
            resumes = [r for r in self.body.relocations if r.purpose == "native_count_body_resume" and
                       r.target == 0x426f54+WINDOW_SIZES[0x426f54]]
            require(len(resumes) == 1, "one independently located owner CMP tail required")
            self.owner_tail = self.body.base_va+resumes[0].offset-4+delta
            require(bytes(self.cpu.mem_read(self.owner_tail, 3)) == bytes.fromhex("3a5702"),
                    "exact authored owner CMP tail required")

        def setup(self, dataset, *, via_adjacent=False):
            self.dataset = dataset
            self.prepare(columns=dataset.columns).begin(self.mode)
            # The parent supplies only modeled Unit/Tile frames. Count's own
            # saved registers, local X and live DY will be created by Count.
            regs = prior.entry_fixture.Machine.setup_count(
                self, record=dataset.self_index, via_adjacent=via_adjacent,
                x=dataset.center[0], y=dataset.center[1])
            require(self.word(self.unit_sp) == (0x42fcc4 if via_adjacent else 0x4303b1)+self.delta,
                    "only modeled initial Unit ancestry is supported")
            # Actual Unit93E..951 computes EDX=31*current_ESI and EAX=record;
            # its ECX comes from UnitS-52. This is a phase-shaped model, not
            # proof of genuine Unit entry identity or intervening callees.
            self.put(self.unit_sp-52, 0)
            self.put(self.unit_sp-28, 31*dataset.self_index)
            regs.update(ESI=dataset.self_index, EDX=31*dataset.self_index,
                        ECX=self.word(self.unit_sp-52))
            self.count_s = regs["ESP"]-4
            self.input_record = regs["EAX"]
            require(self.input_record == self.WORLD+852+31*regs["ESI"], "modeled Unit argument phase differs")
            self.cpu.mem_write(self.WORLD+1534, b"\xe7\x7f"*400)
            for x in range(dataset.columns):
                for y in range(7):
                    self.cpu.mem_write(self.WORLD+1534+40*x+2*y, b"\xff\xff")
            for i in range(22):
                at = self.WORLD+852+31*i
                self.cpu.mem_write(at, struct.pack("<hB", -1, dataset.self_owner))
                self.cpu.mem_write(at+4, struct.pack("<HH", 0, 0))
            self.cpu.mem_write(self.input_record, struct.pack("<hB", 0, dataset.self_owner))
            self.cpu.mem_write(self.input_record+4, struct.pack("<HH", *dataset.center))
            self.cpu.mem_write(self.WORLD+1534+40*dataset.center[0]+2*dataset.center[1],
                               struct.pack("<h", dataset.self_index))
            for _, x, y, index, owner in dataset.cells():
                self.cpu.mem_write(self.WORLD+1534+40*x+2*y, struct.pack("<h", index))
                if index >= 0:
                    at = self.WORLD+852+31*index
                    self.cpu.mem_write(at, struct.pack("<hB", 0, owner))
                    self.cpu.mem_write(at+4, struct.pack("<HH", x, y))
            self.cpu.mem_write(self.count_s-912, b"\xd7"*16)
            self.original_regs = dict(regs)
            return self, regs

        def _source_owner(self, pc, size):
            hits = [(va, raw) for va, raw in self.loaded_code if va <= pc and pc+size <= va+len(raw)]
            require(len(hits) == 1, "unexpected/ambiguous surrounding source instruction")
            va, raw = hits[0]
            require(bytes(self.cpu.mem_read(pc, size)) == raw[pc-va:pc-va+size],
                    "surrounding source instruction changed")

        def _thread_mutation(self, machine, label):
            if not self.invocation_active or label != "thread":
                return
            self.epochs.append((self.admission, len(self.read_events)))
            if self.fault:
                self.fault(self, len(self.epochs), self.admission)

        def _semantic(self, role, address, size):
            self.semantic_reads.append((role, address-self.WORLD, size,
                                        int.from_bytes(self.cpu.mem_read(address, size), "little")))

        def on_code(self, cpu, address, size, data):
            if not self.invocation_active:
                return super().on_code(cpu, address, size, data)
            pc = address-self.delta
            if address == CALL+self.delta:
                require(size == 5 and bytes(cpu.mem_read(address, size)) == self.expected_call,
                        "authentic draw CALL/RAM Entry window differs")
                return  # Execute the actual original or authored replacement CALL.
            if address == RETURN+self.delta:
                require(self.ret_observations == 1 and self.native_returns == 0 and
                        cpu.reg_read(self.regs["ESP"]) == self.count_s+4,
                        "genuine RET0 did not consume the natural CALL word")
                self.native_returns += 1
                self.native_stop = address
                cpu.emu_stop()
                return
            if COUNT <= pc < COUNT_END:
                require(pc in self.native_decoded, "native Count PC lacks authenticated boundary")
                if pc == COUNT:
                    require(not self.native_started and cpu.reg_read(self.regs["ESP"]) == self.count_s and
                            self.word(self.count_s) == RETURN+self.delta, "native Count entry/return ownership differs")
                    self.native_started = True
                    self.admission = None
                    self.entered = {n: cpu.reg_read(self.regs[n]) for n in GPRS+("EFLAGS",)}
                require(self.native_started, "Count interior entered before genuine prologue")
                require(self.active_scan is None, "native Count entered during a pending source scan")
                stolen = next((va for va, length in WINDOW_SIZES.items() if va <= pc < va+length), None)
                if self.joined and stolen is not None:
                    require(pc == stolen and size == 5, "execution entered a stolen native window interior")
                    expected = self.expected_native[pc-COUNT:pc-COUNT+5]
                else:
                    expected = self.expected_native[pc-COUNT:pc-COUNT+len(self.native_decoded[pc])]
                    require(size == len(self.native_decoded[pc]), "native instruction boundary changed")
                require(bytes(cpu.mem_read(address, size)) == expected, "authenticated Count instruction changed")
                if pc == COUNT:
                    self.native_entry_write_start = len(self.write_events)
                self.native_seen.append(pc)
                if pc in WINDOW_SIZES:
                    offset = cpu.reg_read(self.regs["EAX"])
                    require(offset % 8 == 0 and offset < 64, "native Count loop offset escaped table")
                    require(cpu.reg_read(self.regs["EBP"]) == NEIGHBORS[offset//8][1] & 0xffffffff,
                            "genuine Count live EBP does not equal authenticated DY")
                    require(self.word(self.count_s-24) == self.unit_sp-12,
                            "genuine Count saved Unit EBP differs")
                    self.body_visits.append((pc, offset))
                    if self.joined:
                        self.admission = "occupant" if pc == 0x426f44 else "owner"
                        self.body_inputs = {n: cpu.reg_read(self.regs[n]) for n in GPRS}
                if pc in (va+length for va, length in WINDOW_SIZES.items()):
                    self.admission = None
                if pc == COUNT_RET:
                    require(cpu.reg_read(self.regs["ESP"]) == self.count_s and
                            self.word(self.count_s) == RETURN+self.delta,
                            "original Count RET0 frame/word differs")
                    self.ret_observations += 1
                return  # Never forward genuine Count PCs to inherited stub dispatch.
            if address in self.unsafe_vas:
                # Some Unicorn versions report a sentinel CODE size for UD2.
                # Validate its exact two bytes separately and let UD2 execute.
                self._source_owner(address, 2)
                require(bytes(cpu.mem_read(address, 2)) == b"\x0f\x0b", "unsafe endpoint is not real UD2")
                self.unsafe = True
                return  # Execute the real UD2, never an emu_stop success substitute.
            if address != self.THREAD:
                self._source_owner(address, size)
            return super().on_code(cpu, address, size, data)

        def on_read(self, cpu, access, address, size, value, data):
            if self.invocation_active and self.active_scan is None:
                # Exact REP reads retain the inherited strict scan observer;
                # do not duplicate its full zero-tail journal in this fixture.
                pc = cpu.reg_read(self.regs["EIP"])
                self.read_events.append((pc, address, size, self.admission))
                native_pc = pc-self.delta
                if COUNT <= native_pc < COUNT_END:
                    stack = self.count_s-28 <= address and address+size <= self.count_s+4
                    fixed = address == WORLD_GLOBAL+self.delta and size == 4
                    table = TABLE+self.delta <= address and address+size <= TABLE+self.delta+64 and size == 4
                    header = address in (self.WORLD+800, self.WORLD+804) and size == 4
                    record = ((native_pc == 0x426efd and address == self.input_record+4 and size == 2) or
                              (native_pc == 0x426f2d and address == self.input_record+6 and size == 2) or
                              (native_pc == 0x426f5b and address == self.input_record+2 and size == 1))
                    payload = native_pc in WINDOW_SIZES
                    require(stack or fixed or table or header or record or payload,
                            "original Count read escaped declared fields/stack")
                    if table:
                        offset = cpu.reg_read(self.regs["EAX"])
                        require(offset % 8 == 0 and offset < 64 and
                                address in (TABLE+self.delta+offset, TABLE+self.delta+offset+4),
                                "native table read escaped the current neighbor")
                    if native_pc == 0x426f44:
                        self._occupant_read(address, size, {n: cpu.reg_read(self.regs[n]) for n in GPRS})
                    elif native_pc == 0x426f54:
                        self._owner_read(address, size, {n: cpu.reg_read(self.regs[n]) for n in GPRS})
                    elif native_pc == 0x426f5b:
                        self._semantic("input_owner", address, size)
                elif self.joined and self.admission in ("occupant", "owner"):
                    va = 0x426f44 if self.admission == "occupant" else 0x426f54
                    low, high = self.body_regions[va]
                    if low <= pc < high:
                        if self.admission == "occupant" and self.WORLD+1534 <= address < self.WORLD+2334:
                            self._occupant_read(address, size, self.body_inputs)
                        elif self.admission == "owner" and size == 1 and self.WORLD+852 <= address < self.WORLD+1534:
                            self._owner_read(address, size, self.body_inputs)
                    if pc == self.owner_tail:
                        require(address == self.input_record+2 and size == 1, "replayed input-owner CMP read differs")
                        self._semantic("input_owner", address, size)
            super().on_read(cpu, access, address, size, value, data)

        def _occupant_read(self, address, size, regs):
            displacement = regs["ECX"]-self.WORLD
            require(displacement >= 0 and displacement % 40 == 0, "native column pointer is not a current column")
            x, y = displacement//40, regs["EBX"]
            require(0 <= x < self.dataset.columns and 0 <= y < 7 and size == 2 and
                    address == self.WORLD+1534+40*x+2*y, "native occupancy read escaped admitted coordinates")
            self._semantic("occupant", address, size)

        def _owner_read(self, address, size, regs):
            require(regs["EDX"] == self.WORLD and regs["ECX"] % 31 == 0 and
                    regs["ECX"]//31 < 22 and size == 1 and
                    address == self.WORLD+854+regs["ECX"], "native owner read escaped valid unit records")
            self._semantic("owner", address, size)

        def on_write(self, cpu, access, address, size, value, data):
            if self.invocation_active:
                pc = cpu.reg_read(self.regs["EIP"])-self.delta
                self.write_events.append((pc, address, size))
                if pc == CALL:
                    require(address == self.count_s and size == 4 and value == RETURN+self.delta,
                            "Count CALL did not create the authentic native word")
                elif COUNT <= pc < COUNT_END:
                    if self.joined and pc in WINDOW_SIZES:
                        require(address == self.count_s-32 and size == 4 and value == pc+self.delta+5,
                                "body adapter CALL escaped its exact native word")
                    else:
                        require(self.count_s-28 <= address and address+size <= self.count_s,
                                "original Count wrote outside its saved registers/local")
                else:
                    low, high = (self.count_s-896, self.count_s-28) if self.native_started else (
                        self.count_s-864, self.count_s)
                    require(low <= address and address+size <= high,
                            "source helper wrote outside its bounded own stack")
            super().on_write(cpu, access, address, size, value, data)

        def invoke_original(self, regs, *, flags=0xed7, fault=None):
            self.fault, self.mutation = fault, self._thread_mutation
            self.stops = {RETURN+self.delta}
            self.native_stop = None
            self.unsafe = False
            self.native_started = False
            self.native_entry_write_start = None
            self.native_returns = 0
            self.ret_observations = 0
            self.native_seen, self.body_visits, self.semantic_reads = [], [], []
            self.read_events, self.write_events, self.epochs = [], [], []
            self.admission, self.entered = "entry" if self.joined else None, None
            self.content_reads, self.content_writes, self.content_events = [], [], []
            self.content_after_thread = False
            self.active_scan = None
            self.minimum_sp = regs["ESP"]
            self.before_callbacks = len(self.callbacks)
            self.world_before = bytes(self.cpu.mem_read(self.WORLD, 0xf7c))
            self.stack_before = bytes(self.cpu.mem_read(self.STACK, 0x10000))
            self.owner_before = self.record()
            self.lease_before = bytes(self.cpu.mem_read(self.lease_frame, 192))
            for name, value in regs.items():
                self.cpu.reg_write(self.regs[name], value & 0xffffffff)
            self.cpu.reg_write(self.regs["EFLAGS"], flags)
            self.invocation_active = self.content_active = True
            try:
                self.cpu.emu_start(CALL+self.delta, self.STOP+1, count=10000000)
            finally:
                self.invocation_active = self.content_active = False
            require(self.native_returns == 1 and self.native_stop == RETURN+self.delta and not self.unsafe,
                    "Count invocation did not close through genuine RET0")
            require(self.active_scan is None, "source scan observer remained pending")
            require(bytes(self.cpu.mem_read(self.WORLD, 0xf7c)) == self.world_before and
                    self.record() == self.owner_before and
                    bytes(self.cpu.mem_read(self.lease_frame, 192)) == self.lease_before,
                    "healthy Count changed world/owner/lease bytes")
            stack = bytes(self.cpu.mem_read(self.STACK, 0x10000))
            lo, hi = self.count_s-896-self.STACK, self.count_s+4-self.STACK
            require(stack[:lo] == self.stack_before[:lo] and stack[hi:] == self.stack_before[hi:],
                    "Count/helper stack canary or ancestor changed")
            require(bytes(self.cpu.mem_read(TABLE+self.delta, 64)) == self.native_image.table and
                    bytes(self.cpu.mem_read(COUNT+self.delta, 133)) == self.expected_native and
                    bytes(self.cpu.mem_read(CALL+self.delta, 5)) == self.expected_call,
                    "native Count/table/CALL changed during invocation")
            for va, raw in self.loaded_code:
                require(bytes(self.cpu.mem_read(va, len(raw))) == raw, "source emission changed during invocation")
            return {n: self.cpu.reg_read(self.regs[n]) for n in GPRS+("EFLAGS", "EIP")}

        def cached_after_epoch(self, index=-1):
            start = self.epochs[index][1]
            ranges = ((self.PHYSICAL, self.PHYSICAL+188), (self.PRIVATE, self.PRIVATE+188),
                      (self.BACKEND, self.BACKEND+168), (self.WORLD, self.WORLD+0xf7c))
            return [(pc, at, size) for pc, at, size, _ in self.read_events[start:]
                    if any(at < high and at+size > low for low, high in ranges)]

    return OriginalMachine


class AuthoringTests(unittest.TestCase):
    def test_count_invocation_does_not_shadow_inherited_lifecycle_dispatch(self):
        # Inspect source only: default mode must not import parents/Unicorn or
        # construct a machine merely to protect the setup dispatch contract.
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        factory = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "machine_class")
        machine = next(n for n in factory.body if isinstance(n, ast.ClassDef) and n.name == "OriginalMachine")
        methods = [n.name for n in machine.body if isinstance(n, ast.FunctionDef)]
        self.assertNotIn("invoke", methods)
        self.assertEqual(methods.count("invoke_original"), 1)
        originals = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "OriginalTests")
        calls = {n.name: [call.func.attr for call in ast.walk(n)
                         if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                         and call.func.attr in ("invoke", "invoke_original")]
                 for n in originals.body if isinstance(n, ast.FunctionDef)}
        self.assertFalse(any("invoke" in names for names in calls.values()))
        self.assertEqual({name: len(names) for name, names in calls.items() if names}, {
            "pair": 2, "terminal": 1,
            "test_authentic_instruction_and_ret_word_ownership_are_not_stubbed": 2,
        })
        public = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_tests")
        self.assertFalse(any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(public)))
        self.assertFalse({n.id for n in ast.walk(public) if isinstance(n, ast.Name)} & {
            "load_runtime", "authenticate_original", "OriginalTests", "machine_class",
        })
        self.assertEqual(sum(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                             and n.func.id == "source_contract" for n in ast.walk(public)), 2)

    def test_frozen_sources_native_metadata_and_false_acceptance(self):
        source_contract()
        self.assertEqual(COUNT_END-COUNT, 133)
        self.assertEqual(len(HIGHLOW), 3)
        self.assertEqual(len(BRANCHES), 7)
        self.assertEqual(COUNT_RET, COUNT_END-1)
        self.assertEqual(len(struct.pack("<16i", *(v for p in NEIGHBORS for v in p))), 64)
        self.assertTrue(all(not value for value in ACCEPTANCE.values()))

    def test_unknown_original_rejected_before_cpu_or_file_dependency(self):
        for image in (b"", b"authored fixture", bytearray(b"authored fixture"), memoryview(b"fixture"), None):
            with self.assertRaisesRegex(ValueError, "exact original"):
                authenticate_original(image)

    def test_independent_neighbor_oracle_empty_owners_edges_and_all_offsets(self):
        self.assertEqual(Dataset("empty", occupied=0).oracle()[0], 0)
        self.assertEqual(Dataset("same", enemies=0).oracle()[0], 0)
        self.assertEqual(Dataset("different", enemies=255).oracle()[0], 8)
        same_high = Dataset("same-owner-high", self_owner=255, enemies=0)
        opposite_high = Dataset("opposite-owner-high", self_owner=255, enemies=255)
        self.assertEqual(same_high.oracle()[0], 0)
        self.assertEqual(opposite_high.oracle()[0], 8)
        self.assertEqual({owner for _, _, _, _, owner in same_high.cells()}, {255})
        self.assertEqual({owner for _, _, _, _, owner in opposite_high.cells()}, {254})
        self.assertEqual(Dataset("corner", center=(0, 0), enemies=255).oracle()[0], 3)
        self.assertEqual(Dataset("edge", center=(1, 0), enemies=255).oracle()[0], 5)
        self.assertEqual(Dataset("column", columns=1, center=(0, 3), enemies=255).oracle()[0], 2)
        for bit in range(8):
            case = Dataset("single", occupied=1 << bit, enemies=1 << bit)
            self.assertEqual(case.oracle()[0], 1)
            self.assertEqual([i for i, _, _, index, _ in case.cells() if index >= 0], [bit])
        self.assertTrue(all(isinstance(test, AuthoringTests) for test in authoring_suite()))


class OriginalTests(unittest.TestCase):
    runtime = None

    def make(self, case, *, joined=True, delta=0, profile="classic", mode=0, via=False):
        prior, tools, native, decoded, cls = self.runtime
        return cls(tools, native, decoded, joined=joined, profile=profile, delta=delta, mode=mode).setup(
            case, via_adjacent=via)

    def pair(self, case, *, delta=0, profile="classic", mode=0, via=False, flags=0xed7):
        baseline, left = self.make(case, joined=False, delta=delta, profile=profile, mode=mode, via=via)
        joined, right = self.make(case, delta=delta, profile=profile, mode=mode, via=via)
        self.assertEqual(left, right)
        expected, reads = case.oracle()
        before, after = baseline.invoke_original(left, flags=flags), joined.invoke_original(right, flags=flags)
        self.assertEqual(before, after, (case.name, delta, profile, mode, via))
        self.assertEqual(after["EAX"], expected)
        self.assertEqual(after["ESP"], right["ESP"])
        for name in GPRS:
            if name != "EAX":
                self.assertEqual(after[name], right[name], name)
        self.assertEqual(tuple(baseline.semantic_reads), reads)
        self.assertEqual(tuple(joined.semantic_reads), reads)
        self.assertEqual(baseline.body_visits, joined.body_visits)
        self.assertEqual(baseline.epochs, [])
        occupied = sum(index >= 0 for _, _, _, index, _ in case.cells())
        self.assertEqual(len(joined.epochs), 1+len(case.cells())+occupied)
        self.assertEqual(baseline.entered, joined.entered)
        self.assertEqual(bytes(baseline.cpu.mem_read(baseline.count_s-28, 32)),
                         bytes(joined.cpu.mem_read(joined.count_s-28, 32)))
        return baseline, joined

    def test_true_count_two_bases_modes_and_modeled_initial_ancestry(self):
        for delta in (0, 0x30000):
            for mode in (0, 1):
                for via in (False, True):
                    case = Dataset("central-mixed", self_index=7 if via else 21)
                    _, joined = self.pair(case, delta=delta, mode=mode, via=via,
                                          flags=0x246 if via else 0xed7)
                    self.assertEqual({offset for va, offset in joined.body_visits if va == 0x426f54}, set(range(0, 64, 8)))

    def test_empty_owner_extremes_and_occupied_edges_with_genuine_access_bounds(self):
        cases = (Dataset("empty", occupied=0), Dataset("same-owner", enemies=0),
                 Dataset("same-owner-high", self_owner=255, enemies=0),
                 Dataset("opposite-owner-high", self_owner=255, enemies=255),
                 Dataset("all-enemies", enemies=255), Dataset("corner-top", center=(0, 0), enemies=255),
                 Dataset("corner-bottom", center=(2, 6), enemies=255),
                 Dataset("edge-top", center=(1, 0), self_index=0),
                 Dataset("edge-right", center=(2, 3)),
                 Dataset("wide-edge", columns=20, center=(19, 3)),
                 Dataset("one-column", columns=1, center=(0, 3)))
        for delta in (0, 0x30000):
            for case in cases:
                with self.subTest(case=case.name, delta=delta):
                    self.pair(case, delta=delta)

    def test_all_eight_sparse_owner_offsets_and_separate_modal_allocation(self):
        for bit in range(8):
            self.pair(Dataset("single-"+str(bit), occupied=1 << bit, enemies=1 << bit))
        for delta in (0, 0x30000):
            self.pair(Dataset("modal-central"), delta=delta, profile="modalwidgets", mode=1, via=True)

    def terminal(self, machine, regs, *, fault=None):
        with self.assertRaises(machine.u.UcError):
            machine.invoke_original(regs, fault=fault)
        pc = machine.cpu.reg_read(machine.regs["EIP"])
        self.assertIn(pc, machine.unsafe_vas)
        self.assertEqual(bytes(machine.cpu.mem_read(pc, 2)), b"\x0f\x0b")
        self.assertEqual(machine.native_returns, 0)
        self.assertIsNone(machine.native_stop)

    def test_pre_entry_loss_status_phase_never_enters_original_count(self):
        for fault in ("loss", "status", "phase"):
            m, regs = self.make(Dataset(fault), delta=0x30000)
            m.put(m.state_va if fault == "phase" else m.lease_frame+(44 if fault == "loss" else 48),
                  3 if fault == "phase" else 2)
            m.protect_cached(m.u.UC_PROT_NONE)
            self.terminal(m, regs)
            self.assertFalse(m.native_started)
            self.assertEqual(m.epochs, [])
            self.assertEqual(m.semantic_reads, [])

    def test_body_callback_loss_is_epoch_specific_before_new_payload_or_ret(self):
        for admission in ("occupant", "owner"):
            m, regs = self.make(Dataset(admission), delta=0x30000)
            changed = []
            def loss(mm, number, role):
                if role == admission and not changed:
                    mm.put(mm.lease_frame+44, 2)
                    mm.put(mm.lease_frame+48, 2)
                    changed.append(number)
                    mm.protect_cached(mm.u.UC_PROT_NONE)
            self.terminal(m, regs, fault=loss)
            self.assertTrue(m.native_started)
            self.assertEqual(len(changed), 1)
            self.assertEqual(m.cached_after_epoch(), [])
            self.assertEqual(len(m.semantic_reads), 0 if admission == "occupant" else 1)

    def test_genuine_count_local_and_paired_helper_loss_precede_epoch_caches(self):
        for admission in ("occupant", "owner"):
            for paired in (False, True):
                m, regs = self.make(Dataset("local"), delta=0x30000, profile="modalwidgets", via=True)
                changed = []
                fault_write_start = []
                def corrupt(mm, number, role):
                    if role == admission and not changed:
                        local = mm.count_s-28
                        helper = mm.count_s-852
                        self.assertEqual(mm.word(local), mm.dataset.center[0])
                        self.assertEqual(mm.word(helper+376), mm.word(local))
                        self.assertEqual(mm.word(helper+648), mm.word(local))
                        fault_write_start.append(len(mm.write_events))
                        mm.put(local, mm.word(local)^1)
                        if paired:
                            mm.put(helper+376, mm.word(helper+376)^1)
                        changed.append(local)
                        mm.protect_cached(mm.u.UC_PROT_NONE)
                self.terminal(m, regs, fault=corrupt)
                self.assertEqual(changed, [m.count_s-28])
                self.assertEqual(m.word(m.count_s-24), m.unit_sp-12)
                self.assertEqual(m.cached_after_epoch(), [])
                start = m.epochs[-1][1]
                rereads = [(pc, at, size) for pc, at, size, _ in m.read_events[start:]
                           if at == m.count_s-28 and size == 4]
                self.assertEqual(len(rereads), 0 if paired else 1)
                self.assertEqual(len(fault_write_start), 1)
                self.assertIsNotNone(m.native_entry_write_start)
                self.assertLessEqual(m.native_entry_write_start, fault_write_start[0])
                local_writes = [(pc, at, size) for pc, at, size in m.write_events[m.native_entry_write_start:]
                                if at < m.count_s-24 and at+size > m.count_s-28]
                self.assertEqual(local_writes, [(0x426f03, m.count_s-28, 4)])
                self.assertFalse(any(at < m.count_s-24 and at+size > m.count_s-28
                                     for _, at, size in m.write_events[fault_write_start[0]:]))
                self.assertEqual(m.word(m.count_s-28), m.dataset.center[0]^1)

    def test_authentic_instruction_and_ret_word_ownership_are_not_stubbed(self):
        m, regs = self.make(Dataset("instruction"))
        original = bytes(m.cpu.mem_read(COUNT, 1))
        m.cpu.mem_write(COUNT, bytes([original[0]^1]))
        m.cpu.ctl_remove_cache(COUNT, COUNT_END)
        with self.assertRaisesRegex(ValueError, "instruction|boundary"):
            m.invoke_original(regs)
        self.assertEqual(m.native_returns, 0)
        m, regs = self.make(Dataset("return"))
        def corrupt(cpu, pc, size, data):
            if pc == COUNT_RET:
                m.put(m.count_s, RETURN+4)
        # The mutation precedes a separately registered ownership observer.
        m.cpu.hook_add(m.u.UC_HOOK_CODE, corrupt, begin=COUNT_RET, end=COUNT_RET)
        # Check the word before the RET executes even if hook delivery order
        # places the fixture's first code observer before this mutation hook.
        def second(cpu, pc, size, data):
            if pc == COUNT_RET:
                require(m.word(m.count_s) == RETURN, "original Count RET0 frame/word differs")
        m.cpu.hook_add(m.u.UC_HOOK_CODE, second, begin=COUNT_RET, end=COUNT_RET)
        with self.assertRaisesRegex(ValueError, "RET0 frame/word"):
            m.invoke_original(regs)


def authoring_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(AuthoringTests)


def run_tests():
    """Public aggregate API: exactly four authoring checks, never original/CPU."""
    source_contract()
    before = sha(Path(__file__).read_bytes())
    suite = authoring_suite()
    require(suite.countTestCases() == 4, "exact four Count authoring checks required")
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    source_contract()
    require(sha(Path(__file__).read_bytes()) == before, "Count authoring source changed during tests")
    require(result.wasSuccessful() and not result.skipped and result.testsRun == 4,
            "strict four-method Count authoring checks failed or skipped")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", metavar="ORIGINAL_PATH",
                        help="explicit opt-in to authenticated original Count CPU execution in RAM")
    parser.add_argument("--test", action="append", choices=tuple(
        n for n in dir(OriginalTests) if n.startswith("test_")))
    args = parser.parse_args()
    require(not args.test or bool(args.original_backed), "--test requires --original-backed")
    source_contract()
    suite = authoring_suite()
    path, closure = None, None
    if args.original_backed:
        path = Path(args.original_backed)
        native = authenticate_original(path.read_bytes())
        prior, tools, decoded, closure = load_runtime(native)
        OriginalTests.runtime = prior, tools, native, decoded, machine_class(prior)
        if args.test:
            for name in args.test:
                suite.addTest(OriginalTests(name))
        else:
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(OriginalTests))
    count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    source_contract()
    if path is not None:
        require(sha(path.read_bytes()) == ORIGINAL_SHA, "original changed during Count CPU fixture")
        require(all(sha((ROOT/name).read_bytes()) == digest for name, digest in closure.items()),
                "original-backed Count fixture source closure changed")
    if result.wasSuccessful() and not result.skipped and result.testsRun == count:
        if path is None:
            print("Count authoring contracts PASS; original_opcode_cpu_verified=False; --original-backed required.")
        else:
            scope = "selected methods" if args.test else "complete opt-in fixture"
            print("Original Count CPU lane PASS ("+scope+"); modeled outer frames/Thread only; original unchanged; Windows/game/full-ABI/installation/runtime/release/promotion false.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
