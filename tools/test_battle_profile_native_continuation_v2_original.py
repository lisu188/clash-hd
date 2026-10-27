#!/usr/bin/env python3
"""Opt-in original Unit/Count RETs through two fresh continuation V2 gates.

The bounded valid-index/type-minus-one route executes genuine original final
CALL, Unit, Count, Unit RET4, and the final five-byte Adjacent scalar window.
43-window source/model coverage is separate; sprite/RLE, other Unit routes,
outer Field/Tile/Adjacent creation, Thread lifetime and Windows remain open.
Default checks are stdlib-only, lazy and never open an original executable.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SELF = "tools/test_battle_profile_native_continuation_v2_original.py"
FROZEN = "tools/test_battle_profile_native_adjacent_unit_return_original.py"
FROZEN_SHA = "722118c20e54c9f7f0fc28e8d1533834444c31f37cc83c095b1a3b3ff3aa4a12"
ORIGINAL_SHA = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
POST_COUNT, POST_UNIT, STOP = 0x42f95b, 0x42ffa4, 0x42ffa9
ACCEPTANCE = dict(original_bounded_post_return_cpu_verified=False, installed=False,
    whole_battle_verified=False, all_unit_routes_verified=False, sprite_rle_verified=False,
    native_callback_abi_verified=False, historical_motion_authority_verified=False,
    windows_runtime_verified=False, input_verified=False, release_accepted=False, promotion_ready=False)


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_contract():
    path = ROOT/FROZEN
    require(path.resolve(strict=True) == path and sha(path.read_bytes()) == FROZEN_SHA,
            "complete frozen genuine Unit-return fixture required")


def load_runtime(image):
    source_contract()
    sys.path[:0] = [str(ROOT), str(ROOT/"tools")]
    frozen = importlib.import_module("test_battle_profile_native_adjacent_unit_return_original")
    public = importlib.import_module("test_battle_profile_continuation_v2")
    runtime = frozen.load_runtime(image)
    prior, reader, tools, native, boundaries, decoded, closure = runtime
    from src.patcher import pe_extension, partial_tile_clip
    public.tool._authenticate_native(image, image, partial_tile_clip, pe_extension,
        (ROOT/public.tool.LEDGER).read_bytes())
    closure |= public.source_closure() | {FROZEN: FROZEN_SHA, SELF: sha((ROOT/SELF).read_bytes())}
    return frozen, public, runtime[:-1]+(closure,)


def machine_class(frozen, public, runtime):
    prior, reader, tools, native, boundaries, decoded, _ = runtime
    Base = frozen.machine_class(prior, reader)

    class Machine(Base):
        def __init__(self, *, joined=True, profile="classic", resolution="1920x1080", delta=0, mode=0):
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
                super().__init__(tools, native, boundaries, decoded, joined=joined,
                    profile=profile, resolution=resolution, delta=delta, mode=mode)
            _, self.continuation = public.emit(profile, resolution)
            raw = bytearray(self.continuation.code)
            for row in self.continuation.relocations:
                if row.kind == "abs32":
                    struct.pack_into("<I", raw, row.offset, row.target+delta)
            self.cpu.mem_write(self.continuation.base_va+delta, bytes(raw))
            self.loaded_code.append((self.continuation.base_va+delta, bytes(raw)))
            self.unsafe_vas.update(va+delta for name, va in self.continuation.private_entries if "unsafe" in name)
            excluded = []
            for ins in public.disassemble(self.continuation):
                if bytes(ins.bytes) != b"\xf3\xaf":
                    continue
                offset = ins.address-self.continuation.base_va
                require(self.continuation.code[offset-10] == 0xb9 and self.continuation.code[offset-5] == 0xbf,
                        "exact fresh protected-tail scan boundaries required")
                count = struct.unpack_from("<I", self.continuation.code, offset-9)[0]
                pointer = struct.unpack_from("<I", self.continuation.code, offset-4)[0]+delta
                pc = ins.address+delta
                self.scan_before[pc-5] = (pc+2, pointer, count)
                self.scan_after[pc+2] = (pointer, count)
                excluded.append((pc, pc+1))
            for kind, handle, args, kwargs in hooks:
                if kind != self.u.UC_HOOK_CODE or handle in removed:
                    continue
                values, pieces = prior.observer.observer_slices(args, kwargs, excluded, self.on_code)
                self.cpu.hook_del(handle)
                for lo, hi in pieces:
                    self.cpu.hook_add(self.u.UC_HOOK_CODE, values["callback"], values["user_data"],
                        lo, hi, values["aux1"], values["aux2"])
            self.post_windows = {}
            for va, old, target, _, removed_relocs in self.continuation.planned_hooks:
                if va not in (POST_COUNT, POST_UNIT):
                    continue
                require(not removed_relocs, "two selected continuation windows remove no HIGHLOW")
                self.post_windows[va] = old
                low = frozen.UNIT if va == POST_COUNT else frozen.FINAL
                block = bytearray(self.native_blocks[low])
                if va == POST_UNIT:
                    block.extend(old)
                require(bytes(block[va-low:va-low+len(old)]) == old,
                        "complete original selected post-return window required")
                if joined:
                    block[va-low:va-low+len(old)] = b"\xe8"+struct.pack("<i", target-va-5)+b"\x90"*(len(old)-5)
                self.native_blocks[low] = bytes(block)
                self.cpu.mem_write(low+delta, bytes(block))
                self.cpu.ctl_remove_cache(low+delta, low+delta+len(block))
            self.post_visits = []

        def on_code(self, cpu, address, size, data):
            pc = address-self.delta
            if self.invocation_active and pc == STOP:
                require(self.unit_returns == self.unit_ret_observations == self.ret_observations == 1,
                        "original Unit/Count returns must precede final scalar closure")
                self.final_stop = address
                cpu.emu_stop()
                return
            if self.invocation_active and pc in (POST_COUNT, POST_UNIT):
                if pc == POST_COUNT:
                    require(self.ret_observations == 1 and self.native_returns == 0 and
                            cpu.reg_read(self.regs["ESP"]) == self.count_s+4,
                            "genuine Count RET0 must create post-Count entry")
                    self.native_returns += 1
                    self.count_exit = {name: cpu.reg_read(self.regs[name]) for name in frozen.GPRS+("EFLAGS",)}
                else:
                    require(self.unit_ret_observations == self.native_returns == 1 and
                            cpu.reg_read(self.regs["ESP"]) == self.caller_sp,
                            "genuine Unit RET4 must create final post-Unit entry")
                    self.unit_returns += 1
                    self.unit_local_at_ret = self.word(self.unit_s-28)
                self.admission = "post_count" if pc == POST_COUNT else "post_unit"
                self.post_visits.append((pc, {name: cpu.reg_read(self.regs[name]) for name in frozen.GPRS+("EFLAGS",)}))
                expected = 5 if self.joined else (2 if pc == POST_COUNT else 3)
                require(size == expected and bytes(cpu.mem_read(address, size)) == self._unit_bytes(pc, size),
                        "authenticated post-return instruction or exact CALL changed")
                return
            if self.invocation_active and POST_UNIT < pc < STOP:
                require(not self.joined and pc in (0x42ffa7, 0x42ffa8), "baseline-only final scalar boundary required")
                require(bytes(cpu.mem_read(address, size)) == self._unit_bytes(pc, size), "baseline scalar changed")
                return
            return super().on_code(cpu, address, size, data)

        def on_write(self, cpu, access, address, size, value, data):
            pc = cpu.reg_read(self.regs["EIP"])-self.delta
            if self.invocation_active and self.joined and pc in (POST_COUNT, POST_UNIT):
                entry_sp = self.count_s+4 if pc == POST_COUNT else self.caller_sp
                require((address, size, value) == (entry_sp-4, 4, pc+5+self.delta),
                        "fresh post-return CALL must write exactly its own natural word")
                self.write_events.append((pc, address, size))
                return prior.Machine.on_write(self, cpu, access, address, size, value, data)
            source = any(va <= pc+self.delta < va+len(raw) for va, raw in self.loaded_code)
            if self.invocation_active and self.admission in ("post_count", "post_unit") and source:
                entry_sp = self.count_s+4 if self.admission == "post_count" else self.caller_sp
                require(entry_sp-public.tool.HELPER_BYTES-140 <= address and address+size <= entry_sp,
                        "fresh continuation writes escaped bounded own stack")
                self.write_events.append((pc, address, size))
                return prior.Machine.on_write(self, cpu, access, address, size, value, data)
            return super().on_write(cpu, access, address, size, value, data)

        def invoke_route(self, regs, *, fault=None):
            # Keep all native execution inside the frozen original observer.
            # This successor changes only its terminal PC and bounded private
            # stack interval; no native EIP, result or register is substituted.
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
            self.read_events, self.write_events, self.epochs, self.post_visits = [], [], [], []
            self.admission = self.entered = None
            self.content_reads, self.content_writes, self.content_events = [], [], []
            self.content_after_thread, self.active_scan = False, None
            self.minimum_sp = regs["ESP"]
            self.before_callbacks = len(self.callbacks)
            world = bytes(self.cpu.mem_read(self.WORLD, 0xf7c))
            owner, lease = self.record(), bytes(self.cpu.mem_read(self.lease_frame, 192))
            stack = bytes(self.cpu.mem_read(self.STACK, 0x10000))
            for name, value in regs.items():
                self.cpu.reg_write(self.regs[name], value & 0xffffffff)
            self.cpu.reg_write(self.regs["EFLAGS"], self.case.flags)
            self.invocation_active = self.content_active = True
            try:
                self.cpu.emu_start(frozen.FINAL+self.delta, self.STOP+1, count=10000000)
            finally:
                self.invocation_active = self.content_active = False
            require(self.final_stop == STOP+self.delta and self.unit_returns == 1 and not self.unsafe,
                    "original Unit/Count and fresh continuation did not close")
            require(self.active_scan is None and bytes(self.cpu.mem_read(self.WORLD, 0xf7c)) == world and
                    self.record() == owner and bytes(self.cpu.mem_read(self.lease_frame, 192)) == lease,
                    "fresh post-return route changed world/owner/lease or left a scan")
            after = bytes(self.cpu.mem_read(self.STACK, 0x10000))
            low, high = self.unit_s-1560-self.STACK, self.unit_s+8-self.STACK
            require(after[:low] == stack[:low] and after[high:] == stack[high:], "fresh post-return stack canary changed")
            for va, raw in self.native_blocks.items():
                require(bytes(self.cpu.mem_read(va+self.delta, len(raw))) == raw, "original RAM code changed")
            require(bytes(self.cpu.mem_read(reader.TABLE+self.delta, 64)) == self.native_image.table,
                    "authenticated original Count neighbor table changed")
            for va, raw in self.loaded_code:
                require(bytes(self.cpu.mem_read(va, len(raw))) == raw, "source continuation code changed")
            return {name: self.cpu.reg_read(self.regs[name]) for name in frozen.GPRS+("EFLAGS", "EIP")}

    return Machine


class AuthoringTests(unittest.TestCase):
    def test_frozen_source_and_explicit_nonacceptance(self):
        source_contract()
        self.assertTrue(all(value is False for value in ACCEPTANCE.values()))

    def test_default_cpu_and_original_setup_remain_lazy(self):
        tree = ast.parse((ROOT/SELF).read_bytes())
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module]
                self.assertFalse(any(name and any(token in name for token in ("unicorn", "capstone", "test_battle")) for name in names))

    def test_native_execution_has_no_eip_or_result_replacement(self):
        tree = ast.parse((ROOT/SELF).read_bytes())
        methods = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("on_")]
        self.assertTrue(methods)
        for node in methods:
            calls = [child for child in ast.walk(node) if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)]
            self.assertFalse(any(call.func.attr == "reg_write" for call in calls))


class OriginalTests(unittest.TestCase):
    runtime = None

    def pair(self, case=None, **options):
        frozen, public, runtime = self.runtime
        case = frozen.Case() if case is None else case
        Machine = machine_class(frozen, public, runtime)
        left, regs = Machine(joined=False, **options).setup_final(case)
        right, other = Machine(joined=True, **options).setup_final(case)
        self.assertEqual(regs, other)
        a, b = left.invoke_route(regs), right.invoke_route(other)
        self.assertEqual(a, b)
        self.assertEqual(tuple(left.semantic_reads), right.dataset.oracle()[1])
        self.assertEqual(left.semantic_reads, right.semantic_reads)
        self.assertEqual(left.count_arguments, right.count_arguments)
        self.assertEqual(left.count_exit, right.count_exit)
        self.assertEqual(left.type_reads, right.type_reads)
        self.assertEqual(left.original_writes, right.original_writes)
        self.assertEqual(left.post_visits, right.post_visits)
        self.assertEqual([pc for pc, _ in right.post_visits], [POST_COUNT, POST_UNIT])
        self.assertEqual(b["EIP"], STOP+right.delta)
        self.assertEqual(right.unit_ret_observations, 1)
        # The real Unit local is unassigned at RET. The following Adjacent
        # thunk legitimately reuses its dead stack; it is no later witness.
        self.assertEqual(right.unit_local_at_ret, 0xd7d7d7d7)
        return left, right

    def test_original_ret_to_post_count_and_unit_gates_bases_and_modes(self):
        for delta in (0, 0x30000):
            for mode in (0, 1):
                self.pair(delta=delta, mode=mode)

    def test_selected12_original_post_returns_bases_and_modes(self):
        frozen, public, _ = self.runtime
        for profile in frozen.PROFILES:
            for resolution in frozen.RESOLUTIONS:
                for delta in (0, 0x30000):
                    for mode in (0, 1):
                        with self.subTest(profile=profile, resolution=resolution, delta=delta, mode=mode):
                            self.pair(profile=profile, resolution=resolution, delta=delta, mode=mode)

    def test_original_post_return_callback_losses_are_terminal_before_cached_reads(self):
        frozen, public, runtime = self.runtime
        Machine = machine_class(frozen, public, runtime)
        for phase, field in (("post_count", "motion"), ("post_unit", "identity"),
                             ("post_unit", "native_return"), ("post_unit", "outer_return")):
            with self.subTest(phase=phase, field=field):
                m, regs = Machine(profile="modalwidgets", resolution="3840x2160", delta=0x30000).setup_final(frozen.Case())
                changed = []
                def corrupt(mm, number, admission):
                    if admission != phase or changed:
                        return
                    helper = mm.caller_sp-public.tool.HELPER_BYTES-96
                    address = {"motion": frozen.MOTION+mm.delta, "identity": frozen.ACTIVE+mm.delta,
                        "native_return": helper+public.tool.HELPER_BYTES+92,
                        "outer_return": helper+public.tool.HELPER_BYTES+36}[field]
                    mm.put(address, mm.word(address)^1)
                    changed.append((address, mm.word(address), len(mm.content_events)))
                    mm.protect_cached(mm.u.UC_PROT_NONE)
                with self.assertRaises(runtime[2][0].UcError):
                    m.invoke_route(regs, fault=corrupt)
                self.assertEqual(len(changed), 1)
                pc = m.cpu.reg_read(m.regs["EIP"])
                self.assertIn(pc, m.unsafe_vas)
                self.assertEqual(bytes(m.cpu.mem_read(pc, 2)), b"\x0f\x0b")
                self.assertIsNone(m.final_stop)
                self.assertEqual(m.unit_ret_observations, 0 if phase == "post_count" else 1)
                address, value, event = changed[0]
                self.assertEqual(m.word(address), value, "terminal denial must not repair corrupted control")
                cached = ((m.PHYSICAL, m.PHYSICAL+188), (m.PRIVATE, m.PRIVATE+188),
                    (m.BACKEND, m.BACKEND+168), (m.WORLD, m.WORLD+0xf7c))
                self.assertFalse(any(row[0] == "read" and any(row[2] < high and row[2]+row[3] > low
                    for low, high in cached) for row in m.content_events[event:]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", type=Path)
    parser.add_argument("--test", action="append", choices=tuple(name for name in dir(OriginalTests) if name.startswith("test_")))
    args = parser.parse_args()
    require(not args.test or args.original_backed, "selected CPU checks require explicit original")
    source_contract()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AuthoringTests)
    closure = None
    if args.original_backed:
        OriginalTests.runtime = load_runtime(args.original_backed.read_bytes())
        closure = OriginalTests.runtime[2][-1]
        for name in args.test or [name for name in dir(OriginalTests) if name.startswith("test_")]:
            suite.addTest(OriginalTests(name))
    count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    source_contract()
    if closure is not None:
        require(sha(args.original_backed.read_bytes()) == ORIGINAL_SHA, "original changed")
        require(all(sha((ROOT/name).read_bytes()) == digest for name, digest in closure.items()), "post-return source closure changed")
    require(result.wasSuccessful() and not result.skipped and result.testsRun == count, "strict fresh post-return checks failed")
    print("Fresh continuation authoring PASS; no original opened." if closure is None else
        "Original bounded post-Count/post-Unit CPU PASS; outer frames/Thread modeled; sprite/RLE, full battle, Windows, installation, input and release remain false.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
