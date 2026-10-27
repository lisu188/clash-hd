#!/usr/bin/env python3
"""Opt-in genuine final Adjacent CALL, type-minus-one Unit, Count and Unit RET4.

Only valid record indices with type -1 use this bounded provider-free route.
It executes original Unit/Count instructions around four RAM-only overrides,
including the genuine Unit RET4 to 42FFA4. Other Unit branches/providers, outer
Field/Tile/Adjacent history and Thread lifetime are not proved. Default public
checks are stdlib-only and never open an original or import a CPU interpreter.
No candidate, native export, Windows process, input or release proof is written.
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
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
SELF = "tools/test_battle_profile_native_adjacent_unit_return_original.py"
PINS = {
    "src/patcher/battle_profile_adjacent_unit_v2.py": "b2ae87457bd2344d9e6650032dba46d03a680e2303946acb75abaf0508f5ead8",
    "tools/test_battle_profile_adjacent_unit_v2.py": "a8fbbccba6151b5f1b6e374be2935db8e8a58348228451380f883a02a685b009",
    "tools/test_battle_profile_native_count_original.py": "08f654c676a3d13a9a7e993b701ecdd711d5a8d6bc79227b62357b699368cc9e",
}
ORIGINAL_SHA = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
UNIT, UNIT_END = 0x42f820, 0x42fc30
TYPE, TYPE_RESUME, ARGUMENTS = 0x42f84a, 0x42f854, 0x42f93e
UNIT_EPILOGUE, UNIT_RET = 0x42fa8f, 0x42fa94
FINAL, FINAL_CALL, FINAL_RETURN, NO_CALL = 0x42ff7a, 0x42ff9f, 0x42ffa4, 0x42fed6
COUNT, COUNT_END, COUNT_CALL, COUNT_RETURN = 0x426ef0, 0x426f75, 0x42f956, 0x42f95b
MOTION, ACTIVE, WORLD_GLOBAL = 0x523f70, 0x512360, 0x532048
UNIT_SHA = "1927416dbe66ccbee6bf8c22a7f874f5c1ee6f08feaff551985b0ae4b93d6c0e"
CALLER_SHA = "455371cdb73867ea54a97c41442702a4bd2bd88135af9c2a2b2585c2a684c9fa"
PROFILES = ("classic", "framed", "completehd", "modalwidgets")
RESOLUTIONS = ("1920x1080", "2560x1440", "3840x2160")
GPRS = ("EAX", "ECX", "EDX", "EBX", "ESP", "EBP", "ESI", "EDI")
ACCEPTANCE = dict(original_bounded_unit_return_cpu_verified=False,
    all_unit_routes_verified=False, whole_battle_verified=False,
    native_callback_abi_verified=False, native_mapping_or_lifetime_verified=False,
    historical_motion_authority_verified=False, installed=False,
    windows_runtime_verified=False, input_verified=False,
    release_accepted=False, promotion_ready=False)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def u32(value):
    return value & 0xffffffff


def source_contract():
    for name, digest in PINS.items():
        path = ROOT/name
        require(path.resolve(strict=True) == path and sha(path.read_bytes()) == digest,
                "frozen final Unit-return source dependency differs: "+name)


@dataclass(frozen=True)
class Case:
    name: str = "central"
    identity: int = 7
    motion: int = -63
    columns: int = 3
    center: tuple = (1, 3)
    occupied: int = 255
    enemies: int = 170
    owner: int = 0
    old_esi: int = 0
    old_ebx: int = 32
    old_edi: int = 16
    flags: int = 0xed7

    def validate(self):
        require(0 <= self.identity < 22 and -0x80000000 <= self.motion < 0,
                "valid native record index and signed-negative final motion required")
        require(1 <= self.columns <= 20 and 0 <= self.center[0] < self.columns
                and 0 <= self.center[1] < 7, "bounded native Count coordinates required")
        require(all(0 <= n <= 255 for n in (self.occupied, self.enemies, self.owner)),
                "bounded native occupancy and owner bytes required")
        require(u32(self.old_ebx+64) != 0,
                "selected nonzero native stack argument must exclude unaudited Unit reaction route")
        return self


@dataclass(frozen=True, repr=False)
class Native:
    unit: bytes
    caller: bytes
    unit_highlow: tuple
    caller_highlow: tuple
    count: object


def authenticate_original(image, reader):
    require(type(image) is bytes and sha(image) == ORIGINAL_SHA, "exact original required")
    base, locate, relocs = reader.pe_layout(image)
    require(base == 0x400000, "original preferred base differs")
    get = lambda va, size: image[locate(va, size):locate(va, size)+size]
    unit, caller = get(UNIT, UNIT_END-UNIT), get(FINAL, FINAL_RETURN-FINAL)
    require(sha(unit) == UNIT_SHA and sha(caller) == CALLER_SHA,
            "whole original Unit or final caller identity differs")
    inventory = lambda low, high: tuple((va, struct.unpack("<I", get(va, 4))[0])
                                      for va in sorted(relocs) if low <= va < high)
    caller_fields = inventory(FINAL, FINAL_RETURN)
    require(caller_fields == ((0x42ff7c, MOTION), (0x42ff8a, ACTIVE)),
            "whole final caller relocation roles differ")
    for pc, target in ((FINAL_CALL, UNIT), (COUNT_CALL, COUNT)):
        raw = get(pc, 5)
        require(raw[0] == 0xe8 and pc+5+struct.unpack_from("<i", raw, 1)[0] == target,
                "genuine original Unit/Count direct CALL differs")
    branch = get(TYPE_RESUME, 6)
    require(branch[:2] == b"\x0f\x84" and TYPE_RESUME+6+struct.unpack_from("<i", branch, 2)[0] == ARGUMENTS,
            "genuine type-minus-one JE target differs")
    require(get(UNIT_RET, 3) == b"\xc2\x04\x00", "genuine original Unit RET4 differs")
    return Native(unit, caller, inventory(UNIT, UNIT_END), caller_fields,
                  reader.authenticate_original(image))


def load_runtime(image):
    source_contract()
    sys.path[:0] = [str(ROOT), str(ROOT/"tools")]
    reader = importlib.import_module("test_battle_profile_native_count_original")
    native = authenticate_original(image, reader)
    prior = importlib.import_module("test_battle_profile_adjacent_unit_v2")
    tools = prior.observer.parent_fixture.field_fixture.routing_fixture.lifetime.prior_fixture.machine_tools()
    decoder = importlib.import_module("capstone")
    require(decoder.__version__ == "5.0.6", "pinned Capstone 5.0.6 decoder required")
    md = decoder.Cs(decoder.CS_ARCH_X86, decoder.CS_MODE_32)
    unit = {i.address: bytes(i.bytes) for i in md.disasm(native.unit, UNIT)}
    caller = {i.address: bytes(i.bytes) for i in md.disasm(native.caller, FINAL)}
    require(sum(map(len, unit.values())) == len(native.unit)
            and sum(map(len, caller.values())) == len(native.caller),
            "complete independent native Unit/caller instruction boundaries required")
    count = reader.decode_native(tools, native.count)
    closure = prior.source_closure() | {name: sha((ROOT/name).read_bytes()) for name in PINS}
    closure[SELF] = sha(Path(__file__).read_bytes())
    return prior, reader, tools, native, unit | caller, count, closure


def machine_class(prior, reader):
    # Reuse the frozen original Count instruction/read observer, but construct
    # the atomic successor directly. Its original Count stub is overwritten
    # before invocation; genuine native PCs never reach inherited dispatch.
    CountMachine = reader.machine_class(SimpleNamespace(Machine=prior.Machine))

    class Machine(CountMachine):
        def __init__(self, tools, native, boundaries, decoded_count, *, joined,
                     profile="classic", resolution="1920x1080", delta=0, mode=0):
            self.invocation_active = False
            prior.Machine.__init__(self, tools, profile, resolution, delta)
            self.native_image, self.native_decoded = native.count, decoded_count
            self.joined, self.mode = joined, mode
            self.unit_boundaries = boundaries
            blocks = {UNIT: bytearray(native.unit), FINAL: bytearray(native.caller),
                      COUNT: bytearray(native.count.count)}
            for low, rows in ((UNIT, native.unit_highlow), (FINAL, native.caller_highlow),
                              (COUNT, reader.HIGHLOW)):
                for va, target in rows:
                    struct.pack_into("<I", blocks[low], va-low, target+delta)
            self.expected_call = native.count.call
            self.selected_windows = {}
            for va in (TYPE, 0x426f44, 0x426f54):
                old, target, role, removed = self.planned[va]
                require(removed == (), "selected native RAM window removes no HIGHLOW")
                low = UNIT if va == TYPE else COUNT
                require(native.unit[va-UNIT:va-UNIT+len(old)] == old if va == TYPE else
                        native.count.count[va-COUNT:va-COUNT+len(old)] == old,
                        "selected whole native old RAM window differs")
                self.selected_windows[va] = (len(old), target)
                if joined:
                    blocks[low][va-low:va-low+len(old)] = (
                        b"\xe8"+struct.pack("<i", target-va-5)+b"\x90"*(len(old)-5))
            if joined:
                target = dict(self.atomic_entry.entries)["count_entry"]
                self.expected_call = b"\xe8"+struct.pack("<i", target-COUNT_CALL-5)
                blocks[UNIT][COUNT_CALL-UNIT:COUNT_RETURN-UNIT] = self.expected_call
            self.expected_native = bytes(blocks[COUNT])
            self.native_blocks = {low: bytes(raw) for low, raw in blocks.items()}
            for low, raw in self.native_blocks.items():
                self.cpu.mem_write(low+delta, raw)
                self.cpu.ctl_remove_cache(low+delta, low+delta+len(raw))
            self.cpu.mem_write(reader.TABLE+delta, native.count.table)
            self.body_regions = {row[0]: (row[2]+delta, row[7]+delta)
                                 for row in self.atomic_adapters.body_receipts if row[0] in reader.WINDOW_SIZES}
            resumes = [r for r in self.atomic_adapters.relocations
                       if r.purpose == "native_adjacent_unit_resume" and r.target == 0x426f5e]
            require(len(resumes) == 1, "one exact Count owner CMP tail required")
            self.owner_tail = self.atomic_adapters.base_va+resumes[0].offset-4+delta
            require(bytes(self.cpu.mem_read(self.owner_tail, 3)) == b"\x3a\x57\x02",
                    "original Count owner CMP replay differs")
            body = next(row for row in self.atomic_adapters.body_receipts if row[0] == TYPE)
            self.type_region = body[2]+delta, body[7]+delta
            absolute = {r.offset for r in self.atomic_adapters.relocations if r.kind == "abs32"}
            loads = [self.atomic_adapters.base_va+start+delta
                     for start, end, *_ in prior.replay_fixture.decode(self.atomic_adapters.code, absolute)
                     if self.type_region[0] <= self.atomic_adapters.base_va+start+delta < self.type_region[1]
                     and self.atomic_adapters.code[start:end] == b"\x0f\xbf\x00"]
            require(len(loads) == 1, "one atomic first-Type payload read required")
            self.type_read_pc = loads[0]

        def setup_final(self, case):
            self.case = case.validate()
            self.prepare(columns=case.columns).begin(self.mode)
            self.setup_body(prior.SITES[0], index=case.identity, via_adjacent=True)
            self.caller_sp, self.unit_s = self.adjacent_sp-16, self.unit_sp
            require(self.unit_s == self.caller_sp-8, "modeled outer Adjacent stack extent differs")
            # Native caller/prologue/Count create every future native word.
            self.cpu.mem_write(self.unit_s-100, b"\xd7"*108)
            self.count_s = self.unit_s-68
            self.put(MOTION+self.delta, case.motion)
            self.put(ACTIVE+self.delta, case.identity)
            self.put(WORLD_GLOBAL+self.delta, self.WORLD)
            self.dataset = reader.Dataset(case.name, case.columns, case.center,
                                          case.identity, case.occupied, case.enemies, case.owner)
            self.input_record = self.WORLD+852+31*case.identity
            self.cpu.mem_write(self.WORLD+1534, b"\xe7\x7f"*400)
            for x in range(case.columns):
                for y in range(7):
                    self.cpu.mem_write(self.WORLD+1534+40*x+2*y, b"\xff\xff")
            for i in range(22):
                at = self.WORLD+852+31*i
                self.cpu.mem_write(at, struct.pack("<hB", -1, case.owner))
                self.cpu.mem_write(at+4, struct.pack("<HH", 0, 0))
            self.cpu.mem_write(self.input_record+4, struct.pack("<HH", *case.center))
            self.cpu.mem_write(self.WORLD+1534+40*case.center[0]+2*case.center[1],
                               struct.pack("<h", case.identity))
            for _, x, y, index, owner in self.dataset.cells():
                self.cpu.mem_write(self.WORLD+1534+40*x+2*y, struct.pack("<h", index))
                if index >= 0:
                    at = self.WORLD+852+31*index
                    self.cpu.mem_write(at, struct.pack("<hB", 0, owner))
                    self.cpu.mem_write(at+4, struct.pack("<HH", x, y))
            require(bytes(self.cpu.mem_read(self.input_record, 2)) == b"\xff\xff",
                    "valid-index type-minus-one must not be replaced by a normal unit")
            return self, dict(EAX=case.identity, ECX=0x11223344, EDX=0x22334455,
                              EBX=u32(case.old_ebx), ESP=self.caller_sp,
                              EBP=self.current_cell[1], ESI=u32(case.old_esi), EDI=u32(case.old_edi))

        def _unit_bytes(self, pc, size):
            low = UNIT if UNIT <= pc < UNIT_END else FINAL
            raw = self.native_blocks[low]
            require(0 <= pc-low and pc-low+size <= len(raw), "native Unit/caller span escaped")
            return raw[pc-low:pc-low+size]

        def on_code(self, cpu, address, size, data):
            if not self.invocation_active:
                return prior.Machine.on_code(self, cpu, address, size, data)
            pc = address-self.delta
            if pc == FINAL_RETURN:
                require(self.unit_ret_observations == 1 and self.ret_observations == 1
                        and self.native_returns == 1 and cpu.reg_read(self.regs["ESP"]) == self.caller_sp,
                        "natural Unit RET4 did not restore the genuine final caller stack")
                self.unit_returns += 1
                self.final_stop = address
                cpu.emu_stop()
                return
            if pc == NO_CALL:
                raise ValueError("selected signed-negative active caller unexpectedly skipped Unit")
            if UNIT <= pc < UNIT_END or FINAL <= pc < FINAL_RETURN:
                permitted = (FINAL <= pc < FINAL_RETURN or UNIT <= pc <= TYPE_RESUME
                             or ARGUMENTS <= pc <= 0x42f969 or UNIT_EPILOGUE <= pc <= UNIT_RET)
                require(permitted and pc in self.unit_boundaries,
                        "native Unit left the selected provider-free type-minus-one route")
                stolen = self.joined and pc == TYPE
                expected_size = 5 if stolen else len(self.unit_boundaries[pc])
                require(size == expected_size and bytes(cpu.mem_read(address, size)) == self._unit_bytes(pc, size),
                        "authenticated Unit/caller instruction or boundary changed")
                if pc == UNIT:
                    require(self.unit_seen[-1:] == [FINAL_CALL] and self.unit_entries == 0
                            and cpu.reg_read(self.regs["ESP"]) == self.unit_s
                            and self.word(self.unit_s) == FINAL_RETURN+self.delta,
                            "genuine final CALL did not create the Unit frame")
                    self.unit_entries += 1
                if pc == TYPE:
                    require(cpu.reg_read(self.regs["ESP"]) == self.unit_s-64
                            and cpu.reg_read(self.regs["EBP"]) == self.unit_s-12,
                            "genuine Unit prologue extent differs")
                    self.admission = "type" if self.joined else None
                if pc == TYPE_RESUME:
                    self.admission = None
                if pc == COUNT_CALL:
                    self.admission = "entry" if self.joined else None
                    self.count_arguments = {n: cpu.reg_read(self.regs[n]) for n in GPRS}
                if pc == COUNT_RETURN:
                    require(self.ret_observations == 1 and self.native_returns == 0
                            and cpu.reg_read(self.regs["ESP"]) == self.count_s+4,
                            "original Count did not return through its natural CALL word")
                    self.native_returns += 1
                    self.count_exit = {n: cpu.reg_read(self.regs[n]) for n in GPRS+("EFLAGS",)}
                    self.admission = None
                if pc == UNIT_RET:
                    require(cpu.reg_read(self.regs["ESP"]) == self.unit_s
                            and self.word(self.unit_s) == FINAL_RETURN+self.delta,
                            "genuine Unit RET4 word or frame changed")
                    self.unit_ret_observations += 1
                require(self.active_scan is None, "native Unit entered during a source scan")
                self.unit_seen.append(pc)
                return  # Actual original or explicit RAM replacement executes.
            return CountMachine.on_code(self, cpu, address, size, data)

        def on_read(self, cpu, access, address, size, value, data):
            if self.invocation_active and self.active_scan is None:
                pc = cpu.reg_read(self.regs["EIP"])-self.delta
                if UNIT <= pc < UNIT_END or FINAL <= pc < FINAL_RETURN:
                    stack = self.unit_s-64 <= address and address+size <= self.unit_s+8
                    global_read = (pc, address, size) in (
                        (FINAL, MOTION+self.delta, 4), (0x42ff88, ACTIVE+self.delta, 4),
                        (0x42f83f, WORLD_GLOBAL+self.delta, 4), (0x42f940, WORLD_GLOBAL+self.delta, 4))
                    payload = pc == TYPE and address == self.input_record and size == 2
                    require(stack or global_read or payload, "native Unit read escaped selected fields/stack")
                    self.unit_reads.append((pc, address, size))
                    if payload:
                        self.type_reads.append((address, size, int.from_bytes(cpu.mem_read(address, size), "little")))
                elif pc+self.delta == self.type_read_pc:
                    require(self.joined and address == self.input_record and size == 2,
                            "atomic first-Type payload read escaped actual self record")
                    self.type_reads.append((address, size, int.from_bytes(cpu.mem_read(address, size), "little")))
            return CountMachine.on_read(self, cpu, access, address, size, value, data)

        def on_write(self, cpu, access, address, size, value, data):
            if not self.invocation_active:
                return prior.Machine.on_write(self, cpu, access, address, size, value, data)
            pc = cpu.reg_read(self.regs["EIP"])-self.delta
            if UNIT <= pc < UNIT_END or FINAL <= pc < FINAL_RETURN:
                self.write_events.append((pc, address, size))
                if pc == FINAL_CALL:
                    require((address, size, value) == (self.unit_s, 4, FINAL_RETURN+self.delta),
                            "final Unit CALL did not create its natural word")
                elif pc == COUNT_CALL:
                    require((address, size, value) == (self.count_s, 4, COUNT_RETURN+self.delta),
                            "Unit Count CALL did not create its natural word")
                elif self.joined and pc == TYPE:
                    require((address, size, value) == (self.unit_s-68, 4, TYPE+5+self.delta),
                            "atomic Type CALL wrote outside its exact word")
                else:
                    require(self.unit_s-64 <= address and address+size <= self.unit_s+8,
                            "original Unit/caller write escaped its frame/argument")
                if not (self.joined and pc == TYPE):
                    self.original_writes.append((pc, address, size, value))
                return prior.Machine.on_write(self, cpu, access, address, size, value, data)
            if COUNT <= pc < COUNT_END:
                if not (self.joined and pc in reader.WINDOW_SIZES):
                    self.original_writes.append((pc, address, size, value))
                return CountMachine.on_write(self, cpu, access, address, size, value, data)
            self.write_events.append((pc, address, size))
            require(self.unit_s-1024 <= address and address+size <= self.unit_s-64,
                    "source helper wrote outside its own bounded lower stack")
            return prior.Machine.on_write(self, cpu, access, address, size, value, data)

        def invoke_final_original(self, regs, *, fault=None):
            self.fault, self.mutation = fault, self._thread_mutation
            self.stops = set()
            self.native_stop = self.final_stop = None
            self.unsafe = self.native_started = False
            self.native_entry_write_start = None
            self.native_returns = self.ret_observations = self.unit_entries = 0
            self.unit_returns = self.unit_ret_observations = 0
            self.count_arguments = self.count_exit = None
            self.native_seen, self.body_visits, self.semantic_reads = [], [], []
            self.unit_seen, self.unit_reads, self.type_reads, self.original_writes = [], [], [], []
            self.read_events, self.write_events, self.epochs = [], [], []
            self.admission = self.entered = None
            self.content_reads, self.content_writes, self.content_events = [], [], []
            self.content_after_thread = False
            self.active_scan = None
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
                self.cpu.emu_start(FINAL+self.delta, self.STOP+1, count=10000000)
            finally:
                self.invocation_active = self.content_active = False
            require(self.final_stop == FINAL_RETURN+self.delta and self.unit_returns == 1 and not self.unsafe,
                    "bounded native route did not close through original Unit RET4")
            require(self.active_scan is None and bytes(self.cpu.mem_read(self.WORLD, 0xf7c)) == world
                    and self.record() == owner and bytes(self.cpu.mem_read(self.lease_frame, 192)) == lease,
                    "healthy Unit/Count changed world/owner/lease or left a pending scan")
            after = bytes(self.cpu.mem_read(self.STACK, 0x10000))
            low, high = self.unit_s-1024-self.STACK, self.unit_s+8-self.STACK
            require(after[:low] == stack[:low] and after[high:] == stack[high:],
                    "native Unit/Count changed exterior stack or ancestor canaries")
            for low, raw in self.native_blocks.items():
                require(bytes(self.cpu.mem_read(low+self.delta, len(raw))) == raw,
                        "authenticated native RAM span changed")
            require(bytes(self.cpu.mem_read(reader.TABLE+self.delta, 64)) == self.native_image.table,
                    "authenticated native Count neighbor table changed")
            for va, raw in self.loaded_code:
                require(bytes(self.cpu.mem_read(va, len(raw))) == raw, "atomic source emission changed")
            return {n: self.cpu.reg_read(self.regs[n]) for n in GPRS+("EFLAGS", "EIP")}

    return Machine


class AuthoringTests(unittest.TestCase):
    def test_exact_sources_and_nonacceptance(self):
        source_contract()
        self.assertTrue(all(not value for value in ACCEPTANCE.values()))
        self.assertEqual(len(PROFILES)*len(RESOLUTIONS), 12)

    def test_valid_index_type_minus_one_is_distinct_from_sentinel(self):
        for n in (0, 7, 21):
            self.assertEqual(Case(identity=n, motion=-64).validate().identity, n)
        for case in (Case(identity=-1), Case(identity=22), Case(motion=0), Case(old_ebx=-64)):
            with self.assertRaises(ValueError):
                case.validate()

    def test_default_mode_keeps_original_and_cpu_setup_lazy(self):
        tree = ast.parse(Path(__file__).read_text())
        imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertFalse(any("unicorn" in ast.unparse(n) or "capstone" in ast.unparse(n) for n in imports))
        run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_tests")
        self.assertFalse({n.id for n in ast.walk(run) if isinstance(n, ast.Name)} & {"load_runtime", "machine_class"})

    def test_original_observation_has_no_native_eip_or_result_substitution(self):
        tree = ast.parse(Path(__file__).read_text())
        factory = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "machine_class")
        cls = next(n for n in factory.body if isinstance(n, ast.ClassDef))
        observer = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "on_code")
        self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                             and n.func.attr in ("reg_write", "mem_write") for n in ast.walk(observer)))
        self.assertIn("UNIT_RET", {n.id for n in ast.walk(observer) if isinstance(n, ast.Name)})


class OriginalTests(unittest.TestCase):
    runtime = None

    def make(self, case, *, joined=True, profile="classic", resolution="1920x1080", delta=0, mode=0):
        prior, reader, tools, native, boundaries, decoded, closure = self.runtime
        return machine_class(prior, reader)(tools, native, boundaries, decoded, joined=joined,
            profile=profile, resolution=resolution, delta=delta, mode=mode).setup_final(case)

    def pair(self, case, **options):
        baseline, left = self.make(case, joined=False, **options)
        joined, right = self.make(case, **options)
        self.assertEqual(left, right)
        before, after = baseline.invoke_final_original(left), joined.invoke_final_original(right)
        self.assertEqual(before, after, (case, options))
        expected, reads = joined.dataset.oracle()
        self.assertEqual(after["EAX"], expected)
        self.assertEqual((after["ESP"], after["EIP"]), (joined.caller_sp, FINAL_RETURN+joined.delta))
        self.assertEqual((after["EBP"], after["ESI"], after["EDI"]),
                         (u32(case.motion), u32(case.old_esi), u32(case.old_edi)))
        self.assertEqual((after["ECX"], after["EDX"], after["EBX"]),
                         (u32(case.motion+64), 31*case.identity, u32(case.old_edi)))
        self.assertEqual(tuple(baseline.semantic_reads), reads)
        self.assertEqual(tuple(joined.semantic_reads), reads)
        self.assertEqual(baseline.type_reads, joined.type_reads)
        self.assertEqual(joined.type_reads, [(joined.input_record, 2, 65535)])
        self.assertEqual(baseline.original_writes, joined.original_writes)
        self.assertEqual(baseline.count_arguments, joined.count_arguments)
        self.assertEqual(joined.count_arguments["ECX"], u32(case.motion+64))
        self.assertEqual(joined.count_arguments["EAX"], joined.input_record)
        self.assertEqual(joined.count_arguments["EDX"], 31*case.identity)
        self.assertEqual(baseline.count_exit, joined.count_exit)
        self.assertEqual(joined.word(joined.unit_s-28), 0xd7d7d7d7)
        self.assertEqual(baseline.epochs, [])
        self.assertEqual(len(joined.epochs), 2+len(joined.dataset.cells())+
                         sum(index >= 0 for _, _, _, index, _ in joined.dataset.cells()))
        self.assertIn(UNIT_RET, joined.unit_seen)
        self.assertEqual(joined.unit_returns, 1)
        return baseline, joined

    def test_genuine_unit_count_return_smoke_two_bases_and_modes(self):
        for delta in (0, 0x30000):
            for mode in (0, 1):
                self.pair(Case(), delta=delta, mode=mode)

    def test_selected_twelve_cells_two_bases_both_draw_modes(self):
        for profile in PROFILES:
            for resolution in RESOLUTIONS:
                for delta in (0, 0x30000):
                    for mode in (0, 1):
                        with self.subTest(profile=profile, resolution=resolution, delta=delta, mode=mode):
                            self.pair(Case(), profile=profile, resolution=resolution, delta=delta, mode=mode)

    def test_genuine_phase_identity_motion_owner_and_occupied_edges(self):
        cases = (Case("zero", identity=0, motion=-63), Case("zero-ecx", identity=7, motion=-64),
                 Case("negative-ecx", identity=21, motion=-65, owner=255),
                 Case("corner", center=(0, 0), enemies=255),
                 Case("right-edge", columns=20, center=(19, 3), owner=254),
                 Case("one-column", columns=1, center=(0, 3)), Case("empty", occupied=0))
        for case in cases:
            self.pair(case, profile="modalwidgets", resolution="3840x2160", delta=0x30000, mode=1)

    def test_callback_motion_identity_and_count_local_loss_are_terminal(self):
        for role, field in (("type", "motion"), ("entry", "active"),
                            ("occupant", "local"), ("owner", "motion")):
            m, regs = self.make(Case(), profile="modalwidgets", resolution="3840x2160", delta=0x30000)
            changed = []
            def corrupt(mm, number, admission):
                if admission != role or changed:
                    return
                at = MOTION+mm.delta if field == "motion" else ACTIVE+mm.delta if field == "active" else mm.count_s-28
                mm.put(at, mm.word(at)^1)
                changed.append(at)
                mm.protect_cached(mm.u.UC_PROT_NONE)
            with self.assertRaises(m.u.UcError):
                m.invoke_final_original(regs, fault=corrupt)
            self.assertEqual(len(changed), 1)
            pc = m.cpu.reg_read(m.regs["EIP"])
            self.assertIn(pc, m.unsafe_vas)
            self.assertEqual(bytes(m.cpu.mem_read(pc, 2)), b"\x0f\x0b")
            self.assertEqual(m.unit_returns, 0)
            self.assertIsNone(m.final_stop)
            self.assertEqual(m.cached_after_epoch(), [])

    def test_genuine_sentinel_branch_and_wrong_count_self_never_enter_count(self):
        for fault in ("native_identity_minus_one", "count_self"):
            m, regs = self.make(Case(), profile="completehd", resolution="2560x1440", delta=0x30000)
            if fault == "native_identity_minus_one":
                regs["EAX"] = 0xffffffff
                m.put(ACTIVE+m.delta, 0xffffffff)
            else:
                def corrupt(cpu, pc, size, data):
                    cpu.reg_write(m.regs["EAX"], m.WORLD+852+31*21)
                m.cpu.hook_add(m.u.UC_HOOK_CODE, corrupt,
                               begin=COUNT_CALL+m.delta, end=COUNT_CALL+m.delta)
            with self.assertRaises(m.u.UcError):
                m.invoke_final_original(regs)
            pc = m.cpu.reg_read(m.regs["EIP"])
            self.assertIn(pc, m.unsafe_vas)
            self.assertEqual(bytes(m.cpu.mem_read(pc, 2)), b"\x0f\x0b")
            self.assertFalse(m.native_started)
            self.assertEqual(m.unit_returns, 0)
            self.assertIsNone(m.final_stop)
            self.assertEqual(m.semantic_reads, [])
            self.assertFalse(any(at <= m.WORLD+821 < at+size for _, at, size, _ in m.read_events))

    def test_instruction_and_both_native_return_words_cannot_be_shortcut(self):
        m, regs = self.make(Case())
        raw = bytes(m.cpu.mem_read(UNIT+m.delta, 1))
        m.cpu.mem_write(UNIT+m.delta, bytes([raw[0]^1]))
        m.cpu.ctl_remove_cache(UNIT+m.delta, UNIT_END+m.delta)
        with self.assertRaisesRegex(ValueError, "instruction|boundary"):
            m.invoke_final_original(regs)
        self.assertEqual(m.unit_returns, 0)
        for target, natural in ((COUNT_END-1, COUNT_RETURN), (UNIT_RET, FINAL_RETURN)):
            m, regs = self.make(Case())
            slot = m.count_s if target != UNIT_RET else m.unit_s
            def corrupt(cpu, pc, size, data):
                m.put(slot, natural+4+m.delta)
            def verify(cpu, pc, size, data):
                require(m.word(slot) == natural+m.delta,
                        "genuine native return ownership differs")
            m.cpu.hook_add(m.u.UC_HOOK_CODE, corrupt, begin=target+m.delta, end=target+m.delta)
            m.cpu.hook_add(m.u.UC_HOOK_CODE, verify, begin=target+m.delta, end=target+m.delta)
            with self.assertRaisesRegex(ValueError, "return|RET|word|ownership"):
                m.invoke_final_original(regs)
            self.assertEqual(m.unit_returns, 0)


def authoring_suite():
    return unittest.defaultTestLoader.loadTestsFromTestCase(AuthoringTests)


def run_tests():
    source_contract()
    suite = authoring_suite()
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    source_contract()
    require(result.wasSuccessful() and result.testsRun == 4 and not result.skipped,
            "strict Unit-return authoring checks failed or skipped")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", type=Path)
    parser.add_argument("--test", action="append", choices=tuple(n for n in dir(OriginalTests) if n.startswith("test_")))
    args = parser.parse_args()
    require(not args.test or args.original_backed, "selected CPU methods require explicit --original-backed")
    source_contract()
    suite = authoring_suite()
    closure = None
    if args.original_backed:
        OriginalTests.runtime = load_runtime(args.original_backed.read_bytes())
        closure = OriginalTests.runtime[-1]
        if args.test:
            for name in args.test:
                suite.addTest(OriginalTests(name))
        else:
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(OriginalTests))
    count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    source_contract()
    if closure is not None:
        require(sha(args.original_backed.read_bytes()) == ORIGINAL_SHA, "original changed during bounded Unit-return CPU fixture")
        require(all(sha((ROOT/name).read_bytes()) == digest for name, digest in closure.items()),
                "Unit-return source closure changed during CPU fixture")
    if result.wasSuccessful() and result.testsRun == count and not result.skipped:
        print("Unit-return authoring PASS; original_bounded_unit_return_cpu_verified=False." if closure is None else
              "Original final CALL/type-minus-one Unit/Count/Unit RET4 CPU PASS; outer frames/Thread modeled; all-Unit/providers/Windows/runtime/installation/input/release/promotion false.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
