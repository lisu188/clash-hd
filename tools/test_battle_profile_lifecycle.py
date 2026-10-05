#!/usr/bin/env python3
"""Portable lifecycle contracts and synthetic x86; no game or file outputs.

Allocator/constructor/destructor/thread functions are explicit ABI models.
They are not native lifetime evidence. --require-machine-tools makes a missing
Unicorn interpreter fail, and --original-backed additionally authenticates the
five representative original-backed parents entirely in memory.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import importlib
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import battle_profile_lifecycle as tool
from src.patcher import battle_profile_context as context
from src.patcher import framed_modal_canvas as native
from src.patcher import partial_tile_clip as clip
import test_battle_profile_context as parent_fixture


def machine_tools():
    try:
        return importlib.import_module("unicorn"), importlib.import_module("unicorn.x86_const")
    except (ImportError, OSError) as error:
        raise ImportError("Unicorn x86 API unavailable") from error


def synthetic_plan(profile="classic", resolution="1024x768"):
    # A deliberately synthetic planning boundary. The production API must
    # reject this PE fixture and independently authenticate the real parent.
    result = parent_fixture.plan(profile, resolution)
    result["rx"]["va"] = 0x10000000
    result["rx"]["rva"] = 0xFC00000
    if profile in ("classic", "framed"):
        result["rw"]["va"] = 0x10020000
    return result


def synthetic_root(profile="framed", resolution="1366x768"):
    """Minimal semantic-owner fixture, never a production original identity.

    The pure helper's already-authenticated context is modelled here. Its
    identity label cannot authenticate the dummy bytes through the public API.
    """
    plan = synthetic_plan(profile, resolution)
    plan["original_sha256"] = context.BASE_SHA256
    lo, hi, _ = tool.NATIVE_SPANS["root"]
    original = bytearray(b"\x90" * (hi - lo))
    at = tool.ROOT_PRESENT_VA - lo
    original[at:at + 5] = bytes.fromhex(tool.ROOT_PRESENT_OLD)
    candidate = bytearray(original)
    metadata = dict(base_sha256=context.BASE_SHA256, resolution=resolution,
                    stage=plan["parent_stage"], recipe_revision=plan["parent_revision"],
                    candidate_sha256=plan["candidate_sha256"], source_hashes=deepcopy(plan["source_hashes"]),
                    patch_records=[])
    if profile != "classic":
        candidate[at:at + 5] = bytes.fromhex(tool.ROOT_PRESENT_NEW)
        group = {"framed": "framed-all-presets-integrated", "completehd": "complete-hd-all-presets-integrated",
                 "modalwidgets": "modal-widgets-all-presets-integrated"}[profile]
        metadata["patch_records"] = [dict(appended=False, file_offset=0x02E6F6, offset=0x02E6F6,
            va=0x42F2F6, rva=0x2F2F6, old_hex="a61b03", new_hex="06c70e", group=group, stage=plan["parent_stage"])]
        recipe = metadata
        for key in tool.ROOT_RECIPE_PATHS[profile]:
            recipe[key] = {}
            recipe = recipe[key]
        recipe.update(resolution=resolution, original_sha256=context.BASE_SHA256,
            source_bindings={role: dict(path=str(ROOT / name), sha256=digest)
                             for role, (name, digest) in tool.ROOT_EDIT_PINS.items()},
            patches=[dict(group="battle-ui-center-present-wrapper", file_offset=0x02E6F5,
                va=0x42F2F5, rva=0x2F2F5, old_hex="e8a61b0300", new_hex="e806c70e00",
                rationale="0x42F2F5 battle initial Render_Present call -> 0x51BA00 battle-only native-centering present wrapper")])
    return bytes(original), bytes(candidate), metadata, plan


class Machine:
    """Emitted x86 in isolated Unicorn memory with guarded allocation models."""
    HEAP = 0x20000000
    PHYSICAL, PRIVATE, BACKEND, WORLD = HEAP + 0x1000, HEAP + 0x2000, HEAP + 0x3000, HEAP + 0x4000
    PHYSICAL_PIXELS = HEAP + 0x100000
    STACK, SP, ROOT_SP = 0x30000000, 0x30008000, 0x30008100
    THREAD, STOP = 0x18000000, 0x18000100
    MASK = 0xCD5
    NAMES = ("EAX", "ECX", "EDX", "EBX", "ESP", "EBP", "ESI", "EDI", "EFLAGS", "EIP")
    MODAL_LIVE = ("phase", "physical", "native", "saved_render", "root_esp", "owner_tid",
                  "fault", "pending_header", "pending_pixels", "native_pixels", "physical_pixels")

    def __init__(self, tools, profile="classic", resolution="1024x768", delta=0):
        u, r = tools
        self.u, self.r = u, r
        self.cpu = u.Uc(u.UC_ARCH_X86, u.UC_MODE_32)
        self.regs = {name: getattr(r, "UC_X86_REG_" + name) for name in self.NAMES}
        self.plan = synthetic_plan(profile, resolution)
        self.width, self.height = map(int, resolution.split("x"))
        self.delta = delta
        self.modal_va = None if profile in ("classic", "framed") else self.plan["inherited_state_inventory"]["page_va"]
        self.emission = tool._emit_code(self.plan, modal_state_va=self.modal_va, assembler_module=clip)
        self.entries = {name: va + delta for name, va in self.emission.entries}
        self.state_va = self.emission.state_va + delta
        self.private_pixels = (self.PHYSICAL_PIXELS + self.width * self.height + 0x1FFF) & ~0xFFF
        heap_bytes = (self.private_pixels + 307200 + 0x1000 - self.HEAP + 0xFFF) & ~0xFFF
        self.cpu.mem_map(0x400000 + delta, 0x200000)
        self.cpu.mem_map(self.emission.base_va + delta, 0x21000)
        self.cpu.mem_map(self.HEAP, heap_bytes)
        self.cpu.mem_map(self.STACK, 0x10000)
        self.cpu.mem_map(self.THREAD, 0x1000)
        code = bytearray(self.emission.code)
        for row in self.emission.relocations:
            if row.kind == "abs32":
                struct.pack_into("<I", code, row.offset, row.target + delta)
        self.cpu.mem_write(self.emission.base_va + delta, bytes(code))
        self.cpu.mem_write(self.THREAD, b"\xC3")
        self.cpu.hook_add(u.UC_HOOK_CODE, self.on_code)
        self.cpu.hook_add(u.UC_HOOK_MEM_WRITE, self.on_write)
        self.cpu.hook_add(u.UC_HOOK_MEM_READ, self.on_read)
        self.allocs, self.frees, self.destructions, self.callback_flags = [], [], [], []
        self.writes, self.reads, self.callbacks = [], [], []
        self.thread_id, self.fail_allocation, self.mutation = 123, None, None
        self.live, self.retired = {}, set()
        self.replayed_free_flags = []
        self.thread_clobbers = False
        self.allocator_returns = None
        self.native_stop = None
        self.cpu.mem_write(self.state_va - 16, b"\xD7" * 16 + bytes(128) + b"\xD7" * 16)
        self.cpu.mem_write(self.PRIVATE - 16, b"\xD7" * 16 + b"\xB9" * 188 + b"\xD7" * 16)
        self.cpu.mem_write(self.private_pixels - 16, b"\xD7" * 16 + b"\xA7" * 307200 + b"\xD7" * 16)
        self.cpu.mem_write(self.PHYSICAL_PIXELS - 16, b"\xD7" * 16)
        self.cpu.mem_write(self.PHYSICAL_PIXELS + self.width * self.height, b"\xD7" * 16)
        self.cpu.mem_write(self.PHYSICAL_PIXELS, b"\xB9" * (self.width * self.height))
        if self.modal_va is not None:
            self.cpu.mem_write(self.modal_va + delta, bytes(128))
        self.put(native.MAP + delta, self.PHYSICAL)
        self.put(native.RENDER + delta, self.PHYSICAL)
        self.put(native.HOOK_OWNER + delta, 0x40AD40 + delta)
        self.put(clip.LOWER_ROW_OWNER_GLOBAL + delta, 0)
        self.put(clip.POST_TILE_CALLBACK_GLOBAL + delta, 0)
        self.put(native.THREAD_IAT + delta, self.THREAD)
        self.put(0x532048 + delta, 0)
        self.put(self.PHYSICAL, self.width | (self.height << 16))
        self.put(self.PHYSICAL + 4, self.PHYSICAL_PIXELS)
        self.put(self.PHYSICAL + 0xB8, native.MEMORY_VTABLE + delta)
        self.put(native.PRIMARY + delta, self.width | (self.height << 16))
        self.put(native.PRIMARY + delta + 0xB8, native.PRIMARY_VTABLE + delta)
        self.put(native.PRIMARY + delta + 0xD4, 8)
        self.put(native.PRIMARY + delta + 0xBC, self.BACKEND)
        self.put(self.BACKEND + 0xA4, self.BACKEND + 0x100)
        self.inherited_snapshot = None if self.modal_va is None else bytes(self.cpu.mem_read(self.modal_va + delta, 128))

    def put(self, at, value):
        self.cpu.mem_write(at, struct.pack("<I", value & 0xFFFFFFFF))

    def word(self, at):
        return struct.unpack("<I", self.cpu.mem_read(at, 4))[0]

    def state(self, name):
        return self.word(self.state_va + tool.STATE[name])

    def set_state(self, name, value):
        self.put(self.state_va + tool.STATE[name], value)

    def ret(self, value=None):
        if value is not None:
            self.cpu.reg_write(self.regs["EAX"], value & 0xFFFFFFFF)
        sp = self.cpu.reg_read(self.regs["ESP"])
        self.cpu.reg_write(self.regs["EIP"], self.word(sp))
        self.cpu.reg_write(self.regs["ESP"], sp + 4)

    def callback(self, name):
        flags = self.cpu.reg_read(self.regs["EFLAGS"])
        self.callback_flags.append(flags)
        self.callbacks.append(name)
        assert flags & 0x400 == 0, (name, hex(flags))
        if self.mutation:
            self.mutation(self, name)

    def release(self, ptr):
        # Retire CPU access to each private allocation. API reads used for the
        # independent oracle remain possible, while generated UAF faults.
        if ptr == self.WORLD:
            assert ptr not in self.retired, "double native-world free"
            self.retired.add(ptr)
        else:
            size = self.live.pop(ptr)
            self.retired.add(ptr)
            extent = (size + 0xFFF) & ~0xFFF
            self.cpu.mem_protect(ptr, extent, self.u.UC_PROT_NONE)
        self.frees.append(ptr)

    def on_code(self, cpu, address, size, data):
        if address == self.STOP or address in self.stops:
            self.native_stop = address
            cpu.emu_stop()
        elif address == self.THREAD:
            self.callback("thread")
            if self.thread_clobbers:
                # The OS call has no arguments and promises no volatile ECX,
                # EDX or arithmetic-flag preservation. Keep DF0 at its return.
                cpu.reg_write(self.regs["ECX"], 0xDEADCAFE)
                cpu.reg_write(self.regs["EDX"], 0xCAFEDEAD)
                cpu.reg_write(self.regs["EFLAGS"], 0x202)
            self.ret(self.thread_id)
        elif address == native.ALLOC + self.delta:
            self.callback("allocate")
            size = cpu.reg_read(self.regs["EAX"])
            assert size in (188, 307200), size
            self.allocs.append(size)
            value = self.PRIVATE if size == 188 else self.private_pixels
            expected_pointer = value
            if self.allocator_returns is not None and len(self.allocs) <= len(self.allocator_returns):
                value = self.allocator_returns[len(self.allocs) - 1]
            if len(self.allocs) == self.fail_allocation:
                value = 0
            elif value == expected_pointer:
                assert value not in self.live, "duplicate private allocation"
                self.live[value] = size
                self.retired.discard(value)
                self.cpu.mem_protect(value, (size + 0xFFF) & ~0xFFF, self.u.UC_PROT_ALL)
            self.ret(value)
        elif address == native.FREE + self.delta:
            ptr = cpu.reg_read(self.regs["EAX"])
            if ptr == self.WORLD:
                # This tail transfer replaces the original native CALL. Its
                # flags come from the native caller; added helper callbacks
                # separately require DF0, even for incoming DF1.
                self.replayed_free_flags.append(cpu.reg_read(self.regs["EFLAGS"]))
            else:
                self.callback("free")
            self.release(ptr)
            self.ret()
        elif address == native.BASE_CTOR + self.delta:
            self.callback("construct")
            ptr = cpu.reg_read(self.regs["EAX"])
            assert ptr == self.PRIVATE
            w, h = (cpu.reg_read(self.regs[name]) for name in ("EDX", "EBX"))
            assert (w, h) == (640, 480), (w, h)
            self.cpu.mem_write(ptr, bytes(188))
            self.put(ptr, w | (h << 16))
            self.ret(ptr)
        elif address == native.DTOR + self.delta:
            self.callback("destroy")
            ptr, flags = (cpu.reg_read(self.regs[name]) for name in ("EAX", "EDX"))
            self.destructions.append((ptr, flags, self.word(native.RENDER + self.delta), self.state("phase")))
            assert ptr == self.PRIVATE and flags == 2
            assert self.word(self.PRIVATE + 4) == self.private_pixels
            assert self.word(self.PRIVATE + 0xB8) == native.MEMORY_VTABLE + self.delta
            assert self.word(self.PRIVATE + 0xAC) == 0
            self.release(self.private_pixels)
            self.release(self.PRIVATE)
            self.ret()

    def on_write(self, cpu, access, address, size, value, data):
        self.writes.append((address, size))

    def on_read(self, cpu, access, address, size, value, data):
        self.reads.append((address, size))

    def invoke(self, name, *, eax=0, edx=0x22334455, flags=0xED7, stops=(), sp=None):
        self.stops = {va + self.delta for va in stops}
        self.native_stop = None
        self.writes, self.reads = [], []
        registers = dict(EAX=eax, ECX=0x11223344, EDX=edx, EBX=0x33445566,
                         EBP=0x44556677, ESI=0x55667788, EDI=0x66778899, ESP=self.SP if sp is None else sp)
        self.put(registers["ESP"], self.STOP)
        for n, value in registers.items():
            self.cpu.reg_write(self.regs[n], value & 0xFFFFFFFF)
        self.cpu.reg_write(self.regs["EFLAGS"], flags)
        self.cpu.emu_start(self.entries[name], self.STOP + 1, count=1000000)
        result = {n: self.cpu.reg_read(reg) for n, reg in self.regs.items()}
        assert self.native_stop is not None, (name, result)
        if self.native_stop == self.STOP:
            expected_sp = self.ROOT_SP + 8 if name == "root_epilogue" else registers["ESP"] + 4
            assert result["ESP"] == expected_sp, (name, result)
            assert all(result[n] == v for n, v in registers.items() if n not in ("EAX", "ESP")), (name, result)
            if name != "root_epilogue":
                assert result["EFLAGS"] & self.MASK == flags & self.MASK, (name, result)
        allowed = ((self.STACK, self.STACK + 0x10000), (self.state_va, self.state_va + 104),
                   (self.PRIVATE, self.PRIVATE + 188), (self.private_pixels, self.private_pixels + 307200),
                   (native.RENDER + self.delta, native.RENDER + self.delta + 4))
        assert all(any(lo <= at and at + size <= hi for lo, hi in allowed) for at, size in self.writes), self.writes
        for address in (self.state_va - 16, self.state_va + 128, self.PRIVATE - 16, self.PRIVATE + 188,
                        self.private_pixels - 16, self.private_pixels + 307200,
                        self.PHYSICAL_PIXELS - 16, self.PHYSICAL_PIXELS + self.width * self.height):
            assert bytes(self.cpu.mem_read(address, 16)) == b"\xD7" * 16, hex(address)
        assert bytes(self.cpu.mem_read(self.state_va + 104, 24)) == bytes(24)
        if self.modal_va is not None:
            assert bytes(self.cpu.mem_read(self.modal_va + self.delta, 128)) == self.inherited_snapshot
        return result

    def enter(self, **kwargs):
        return self.invoke("try_enter", eax=self.ROOT_SP, **kwargs)

    def bind(self, **kwargs):
        self.put(native.HOOK_OWNER + self.delta, 0x42E8B0 + self.delta)
        self.put(0x532048 + self.delta, self.WORLD)
        self.put(self.WORLD + 800, 7)
        self.put(self.WORLD + 804, 20)
        return self.invoke("bind_or_abort", eax=self.WORLD, edx=self.ROOT_SP - 168, **kwargs)


class SourceTests(unittest.TestCase):
    def test_profile_root_preserves_every_byte_except_exact_authenticated_call(self):
        for profile in context.PROFILES:
            for resolution in context.RESOLUTIONS:
                old, new, metadata, plan = synthetic_root(profile, resolution)
                contract = tool._check_parent_root(old, new, file_offset=0x02DDE0, profile=profile,
                                                   parent_metadata=metadata, plan=plan)
                self.assertEqual(contract["rule"], "exact_original" if profile == "classic" else
                                 "one_exact_inherited_centered_present_call")
                altered = bytearray(new)
                altered[0] ^= 1
                with self.assertRaises(ValueError):
                    tool._check_parent_root(old, bytes(altered), file_offset=0x02DDE0, profile=profile,
                                             parent_metadata=metadata, plan=plan)

    def test_profile_root_rejects_wrong_call_source_record_and_ancestry(self):
        for profile in ("framed", "completehd", "modalwidgets"):
            old, new, metadata, plan = synthetic_root(profile)
            for change in ("missing_final", "duplicate_final", "wrong_final", "missing_ancestry", "wrong_resolution",
                           "missing_semantic", "duplicate_semantic", "wrong_semantic", "wrong_source", "wrong_call"):
                with self.subTest(profile=profile, change=change):
                    altered_meta, altered_plan, altered_new = deepcopy(metadata), deepcopy(plan), new
                    recipe = altered_meta
                    for key in tool.ROOT_RECIPE_PATHS[profile]:
                        recipe = recipe[key]
                    if change == "missing_final": altered_meta["patch_records"] = []
                    elif change == "duplicate_final": altered_meta["patch_records"] *= 2
                    elif change == "wrong_final": altered_meta["patch_records"][0]["stage"] = "other"
                    elif change == "missing_ancestry": altered_meta.pop(tool.ROOT_RECIPE_PATHS[profile][0])
                    elif change == "wrong_resolution": recipe["resolution"] = "1920x1080"
                    elif change == "missing_semantic": recipe["patches"] = []
                    elif change == "duplicate_semantic": recipe["patches"] *= 2
                    elif change == "wrong_semantic": recipe["patches"][0]["group"] = "unrelated"
                    elif change == "wrong_source":
                        name, _ = next(iter(tool.ROOT_EDIT_PINS.values()))
                        altered_plan["source_hashes"][name] = "0" * 64
                    elif change == "wrong_call":
                        data = bytearray(new)
                        data[tool.ROOT_PRESENT_VA - tool.NATIVE_SPANS["root"][0] + 1] ^= 1
                        altered_new = bytes(data)
                    with self.assertRaises(ValueError):
                        tool._check_parent_root(old, altered_new, file_offset=0x02DDE0, profile=profile,
                                                 parent_metadata=altered_meta, plan=altered_plan)

    def test_fixed_private_context_and_assembler_ignore_public_aliases(self):
        snapshot = tool._snapshot()
        modules_before = set(sys.modules)
        plan = synthetic_plan()
        expected = tool._emit_code(plan, modal_state_va=None, assembler_module=clip)
        with patch.object(context, "build_parent_context", side_effect=AssertionError("public context alias")), \
                patch.object(clip, "_Assembler", side_effect=AssertionError("public assembler alias")):
            with tool._modules(snapshot) as modules:
                owned_context = modules[tool.CONTEXT]
                self.assertIsNot(owned_context.build_parent_context, context.build_parent_context)
                private_clip = modules["src/patcher/partial_tile_clip.py"]
                actual = tool._emit_code(plan, modal_state_va=None, assembler_module=private_clip)
                self.assertEqual(actual.code, expected.code)
                self.assertEqual(actual.entries, expected.entries)
                self.assertEqual([(r.offset, r.kind, r.target, r.purpose) for r in actual.relocations],
                                 [(r.offset, r.kind, r.target, r.purpose) for r in expected.relocations])
        self.assertEqual(set(sys.modules), modules_before)
        tool._unchanged(snapshot)

    def test_pinned_and_mid_emission_source_changes_are_rejected(self):
        snapshot = tool._snapshot()
        with patch.dict(tool.PINNED_SOURCES, {tool.CONTEXT: "0" * 64}):
            with self.assertRaisesRegex(ValueError, "pinned lifecycle source"):
                tool._snapshot()
        read = Path.read_bytes
        def changed(path):
            data = read(path)
            return data + b"# concurrent edit\n" if path == ROOT / tool.SOURCE else data
        with patch.object(Path, "read_bytes", changed):
            with self.assertRaisesRegex(ValueError, "source changed during"):
                tool._unchanged(snapshot)

    def test_public_api_rejects_synthetic_original_and_bad_selectors(self):
        for original in (b"", bytearray(), memoryview(b"")):
            with self.subTest(type=type(original)), self.assertRaises(ValueError):
                tool.emit_battle_profile_lifecycle(original, "classic", "1024x768")
        for profile, resolution in (("other", "1024x768"), ("classic", "802x602"),
                                    (True, "800x600"), ("classic", "800X600")):
            with self.subTest(profile=profile, resolution=resolution), self.assertRaises(ValueError):
                tool.emit_battle_profile_lifecycle(b"", profile, resolution)

    def test_all_profile_preset_code_is_bounded_and_state_reservations_are_disjoint(self):
        for profile in context.PROFILES:
            for resolution in context.RESOLUTIONS:
                plan = synthetic_plan(profile, resolution)
                modal = None if profile in ("classic", "framed") else plan["inherited_state_inventory"]["page_va"]
                code = tool._emit_code(plan, modal_state_va=modal, assembler_module=clip)
                self.assertEqual(code.state_va, plan["rw"]["va"])
                self.assertEqual(code.base_va, plan["rx"]["va"])
                self.assertLess(len(code.code), plan["rx"]["virtual_reservation"])
                self.assertGreater(len(clip.absolute_relocation_offsets(code)), 0)
                self.assertEqual({n for n, _ in code.entries}, {"try_enter", "bind_or_abort", "try_leave", "finish_return",
                                                          "root_entry", "bind_allocation", "leave_before_free", "root_epilogue"})
                self.assertTrue(all(0 <= offset < 104 and offset % 4 == 0 for offset in tool.STATE.values()))


class CPUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.tools = machine_tools()
        except ImportError as error:
            raise unittest.SkipTest(str(error))

    def native_stack_flags(self, opcode, esp, flags):
        # Execute an independent native SUB/ADD instead of reusing the
        # emitter's arithmetic or assuming its replay keeps arithmetic flags.
        u, r = self.tools
        reference = u.Uc(u.UC_ARCH_X86, u.UC_MODE_32)
        reference.mem_map(0x1000, 4096)
        reference.mem_write(0x1000, bytes.fromhex(opcode))
        reference.reg_write(r.UC_X86_REG_ESP, esp)
        reference.reg_write(r.UC_X86_REG_EFLAGS, flags)
        reference.emu_start(0x1000, 0x1006, count=1)
        return reference.reg_read(r.UC_X86_REG_EFLAGS) & Machine.MASK

    def test_all_36_cells_two_bases_allocation_and_normal_lifetime(self):
        for profile in context.PROFILES:
            for resolution in context.RESOLUTIONS:
                for delta in (0, 0x2000000):
                    with self.subTest(profile=profile, resolution=resolution, delta=delta):
                        machine = Machine(self.tools, profile, resolution, delta)
                        self.assertEqual(machine.enter()["EAX"], 1)
                        self.assertEqual(machine.state("phase"), 1)
                        self.assertEqual(machine.allocs, [188, 307200])
                        self.assertEqual(bytes(machine.cpu.mem_read(machine.private_pixels, 307200)), bytes(307200))
                        self.assertEqual(machine.bind()["EAX"], 1)
                        self.assertEqual(machine.state("phase"), 2)
                        machine.put(native.RENDER + delta, machine.PRIVATE)
                        self.assertEqual(machine.invoke("try_leave", eax=machine.ROOT_SP - 172)["EAX"], 1)
                        self.assertEqual(machine.state("phase"), 4)
                        self.assertEqual(machine.destructions[0][2], machine.PHYSICAL)
                        self.assertEqual(machine.frees, [machine.private_pixels, machine.PRIVATE])
                        machine.put(0x532048 + delta, 0)
                        machine.put(native.HOOK_OWNER + delta, 0x40AD40 + delta)
                        self.assertEqual(machine.invoke("finish_return", eax=machine.ROOT_SP - 168)["EAX"], 1)
                        self.assertEqual(machine.state("phase"), 0)
                        self.assertEqual(machine.state("allocations"), machine.state("frees"))
                        self.assertEqual(bytes(machine.cpu.mem_read(machine.PHYSICAL_PIXELS, machine.width * machine.height)),
                                         b"\xB9" * (machine.width * machine.height))

    def test_each_allocator_failure_retains_no_published_owner(self):
        for profile in context.PROFILES:
            for failure in (1, 2):
                with self.subTest(profile=profile, allocation=failure):
                    machine = Machine(self.tools, profile)
                    machine.fail_allocation = failure
                    self.assertEqual(machine.enter()["EAX"], 0)
                    self.assertEqual(machine.state("phase"), 0)
                    self.assertEqual(machine.state("native"), 0)
                    self.assertEqual(machine.state("pending_header"), 0)
                    self.assertEqual(machine.state("pending_pixels"), 0)
                    self.assertEqual(machine.frees, [] if failure == 1 else [machine.PRIVATE])
                    self.assertEqual(machine.word(native.RENDER), machine.PHYSICAL)

    def test_invalid_or_aliased_allocator_receipts_never_authorize_a_free(self):
        for target in (0xFFFF, Machine.PRIVATE + 1, Machine.PHYSICAL, Machine.PHYSICAL_PIXELS,
                       Machine.BACKEND, 0x10000000, 0x10020000, 0x10020200, 0x10020F44):
            with self.subTest(header_receipt=hex(target)):
                machine = Machine(self.tools)
                machine.allocator_returns = [target]
                self.assertEqual(machine.enter()["EAX"], 0)
                self.assertEqual(machine.state("phase"), 3)
                self.assertEqual(machine.state("fault"), 6)
                self.assertEqual(machine.state("native"), 0)
                self.assertEqual(machine.frees, [])
                self.assertNotIn("construct", machine.callbacks)
        for target in (Machine.PRIVATE, Machine.PHYSICAL_PIXELS, 0x10000000, 0x10020000, 0x10020200):
            with self.subTest(pixel_receipt=hex(target)):
                machine = Machine(self.tools)
                machine.allocator_returns = [machine.PRIVATE, target]
                self.assertEqual(machine.enter()["EAX"], 0)
                self.assertEqual(machine.state("phase"), 3)
                self.assertEqual(machine.state("fault"), 6)
                self.assertEqual(machine.state("pending_header"), machine.PRIVATE)
                self.assertEqual(machine.frees, [])
                self.assertNotIn("construct", machine.callbacks)

    def test_unused_rw_page_cannot_become_surface_backend_or_world_owner(self):
        for profile in ("classic", "framed"):
            for role in ("physical", "backend", "world", "private"):
                with self.subTest(profile=profile, role=role):
                    machine = Machine(self.tools, profile)
                    forged = machine.state_va + 512
                    if role == "physical":
                        machine.cpu.mem_write(forged, bytes(machine.cpu.mem_read(machine.PHYSICAL, 188)))
                        machine.put(native.MAP, forged)
                        machine.put(native.RENDER, forged)
                        self.assertEqual(machine.enter()["EAX"], 0)
                        self.assertEqual(machine.allocs, [])
                    elif role == "backend":
                        machine.cpu.mem_write(forged, bytes(machine.cpu.mem_read(machine.BACKEND, 168)))
                        machine.put(native.PRIMARY + 0xBC, forged)
                        self.assertEqual(machine.enter()["EAX"], 0)
                        self.assertEqual(machine.allocs, [])
                    elif role == "world":
                        self.assertEqual(machine.enter()["EAX"], 1)
                        machine.put(native.HOOK_OWNER, 0x42E8B0)
                        machine.put(0x532048, forged)
                        self.assertEqual(machine.invoke("bind_or_abort", eax=forged, edx=machine.ROOT_SP - 168)["EAX"], 0)
                    else:
                        self.assertEqual(machine.enter()["EAX"], 1)
                        self.assertEqual(machine.bind()["EAX"], 1)
                        machine.cpu.mem_write(forged, bytes(machine.cpu.mem_read(machine.PRIVATE, 188)))
                        machine.set_state("native", forged)
                        self.assertEqual(machine.invoke("try_leave", eax=machine.ROOT_SP - 172)["EAX"], 0)
                    self.assertEqual(machine.frees, [])
                    self.assertEqual(machine.destructions, [])

    def test_native_allocation_abort_cleans_phase_one_without_healthy_return(self):
        for profile in context.PROFILES:
            machine = Machine(self.tools, profile)
            self.assertEqual(machine.enter()["EAX"], 1)
            machine.put(native.HOOK_OWNER, 0x42E8B0)
            self.assertEqual(machine.invoke("bind_or_abort", eax=0, edx=machine.ROOT_SP - 168)["EAX"], 0)
            self.assertEqual(machine.frees, [machine.private_pixels, machine.PRIVATE])
            self.assertEqual(machine.state("return_status"), 0)
            self.assertEqual(machine.state("abort_reason"), 1)

    def test_modal_live_fields_reject_even_when_phase_is_inactive(self):
        for key in Machine.MODAL_LIVE:
            for profile in ("completehd", "modalwidgets"):
                with self.subTest(profile=profile, field=key):
                    machine = Machine(self.tools, profile)
                    machine.put(machine.modal_va + native.STATE[key], 1)
                    machine.inherited_snapshot = bytes(machine.cpu.mem_read(machine.modal_va, 128))
                    self.assertEqual(machine.enter()["EAX"], 0)
                    self.assertEqual(machine.allocs, [])

    def test_completed_modal_statuses_are_preserved_and_unbalanced_counters_reject(self):
        for profile in ("completehd", "modalwidgets"):
            machine = Machine(self.tools, profile)
            for key, value in (("enter_status", 1), ("mirror_status", 1), ("leave_status", 1),
                               ("allocations", 7), ("frees", 7), ("mirrors", 123)):
                machine.put(machine.modal_va + native.STATE[key], value)
            machine.inherited_snapshot = bytes(machine.cpu.mem_read(machine.modal_va, 128))
            self.assertEqual(machine.enter()["EAX"], 1)
            bad = Machine(self.tools, profile)
            bad.put(bad.modal_va + native.STATE["allocations"], 1)
            bad.inherited_snapshot = bytes(bad.cpu.mem_read(bad.modal_va, 128))
            self.assertEqual(bad.enter()["EAX"], 0)
            self.assertEqual(bad.allocs, [])

    def test_wrong_owner_thread_stack_and_pointer_never_destroy(self):
        cases = ("thread", "root_stack", "physical_pixels", "native_pixels", "native_com", "owner", "battle")
        for name in cases:
            with self.subTest(case=name):
                machine = Machine(self.tools)
                self.assertEqual(machine.enter()["EAX"], 1)
                self.assertEqual(machine.bind()["EAX"], 1)
                if name == "thread": machine.thread_id += 1
                elif name == "root_stack": machine.set_state("root_esp", machine.ROOT_SP + 4)
                elif name == "physical_pixels": machine.put(machine.PHYSICAL + 4, machine.PHYSICAL_PIXELS + 4)
                elif name == "native_pixels": machine.put(machine.PRIVATE + 4, machine.private_pixels + 4)
                elif name == "native_com": machine.put(machine.PRIVATE + 0xAC, 1)
                elif name == "owner": machine.put(native.HOOK_OWNER, 0x40AD40)
                elif name == "battle": machine.put(0x532048, machine.WORLD + 4)
                self.assertEqual(machine.invoke("try_leave", eax=machine.ROOT_SP - 172)["EAX"], 0)
                self.assertEqual(machine.frees, [])

    def test_callbacks_cannot_substitute_entry_thread_globals_or_modal_owner(self):
        for profile in context.PROFILES:
            keys = ("thread", "map", "render", "owner", "backend", "lower", "post")
            if profile in ("completehd", "modalwidgets"):
                keys += ("modal_live", "modal_counter")
            for key in keys:
                with self.subTest(profile=profile, mutation=key):
                    machine = Machine(self.tools, profile)
                    def mutate(m, callback):
                        if callback != "allocate" or m.allocs:
                            return
                        if key == "thread": m.thread_id += 1
                        elif key == "map": m.put(native.MAP, m.PHYSICAL + 4)
                        elif key == "render": m.put(native.RENDER, native.PRIMARY)
                        elif key == "owner": m.put(native.HOOK_OWNER, 0x42E8B0)
                        elif key == "backend": m.put(native.PRIMARY + 0xBC, m.BACKEND + 4)
                        elif key == "lower": m.put(clip.LOWER_ROW_OWNER_GLOBAL, 1)
                        elif key == "post": m.put(clip.POST_TILE_CALLBACK_GLOBAL, 1)
                        elif key == "modal_live": m.put(m.modal_va + native.STATE["saved_render"], 1)
                        elif key == "modal_counter": m.put(m.modal_va + native.STATE["mirrors"], 1)
                        if m.modal_va is not None:
                            m.inherited_snapshot = bytes(m.cpu.mem_read(m.modal_va, 128))
                    machine.mutation = mutate
                    self.assertEqual(machine.enter()["EAX"], 0)
                    self.assertEqual(machine.state("phase"), 3 if key == "thread" else 0)
                    self.assertEqual(machine.state("native"), 0)
                    self.assertEqual(machine.state("pending_header"), machine.PRIVATE if key == "thread" else 0)
                    self.assertEqual(machine.state("pending_pixels"), 0)
                    self.assertEqual(len(machine.frees), 0 if key == "thread" else len(machine.allocs))
                    if key == "thread":
                        self.assertEqual(machine.state("fault"), 6)
                        self.assertEqual(machine.live, {machine.PRIVATE: 188})

    def test_actual_root_adapter_replays_native_stack_and_preserves_flags(self):
        for profile in context.PROFILES:
            for delta in (0, 0x2000000):
                for flags in (0x202, 0xED7):
                    with self.subTest(profile=profile, delta=delta, flags=flags):
                        machine = Machine(self.tools, profile, delta=delta)
                        result = machine.invoke("root_entry", sp=machine.ROOT_SP, stops=(0x42E9E9,), flags=flags)
                        self.assertEqual(result["ESP"], machine.ROOT_SP - 168)
                        self.assertEqual(machine.state("root_esp"), machine.ROOT_SP)
                        self.assertEqual(machine.state("phase"), 1)
                        self.assertEqual(result["EFLAGS"] & Machine.MASK,
                                         self.native_stack_flags("81ec9c000000", machine.ROOT_SP - 12, flags))
                        self.assertEqual(result["EBP"], 0x44556677)
                        self.assertEqual(result["ESI"], 0x55667788)
                        self.assertEqual(result["EDI"], 0x66778899)

    def test_finish_return_needs_native_owner_globals_and_allocation_retirement(self):
        for key in ("battle", "owner", "render", "thread", "backend", "stack"):
            with self.subTest(case=key):
                machine = Machine(self.tools)
                self.assertEqual(machine.enter()["EAX"], 1)
                self.assertEqual(machine.bind()["EAX"], 1)
                self.assertEqual(machine.invoke("try_leave", eax=machine.ROOT_SP - 172)["EAX"], 1)
                machine.put(0x532048, 0)
                machine.put(native.HOOK_OWNER, 0x40AD40)
                if key == "battle": machine.put(0x532048, machine.WORLD)
                elif key == "owner": machine.put(native.HOOK_OWNER, 0x42E8B0)
                elif key == "render": machine.put(native.RENDER, machine.PRIVATE)
                elif key == "thread": machine.thread_id += 1
                elif key == "backend": machine.put(native.PRIMARY + 0xBC, machine.BACKEND + 4)
                result = machine.invoke("finish_return", eax=machine.ROOT_SP - (164 if key == "stack" else 168))
                self.assertEqual(result["EAX"], 0)
                self.assertNotEqual(machine.state("phase"), 0)
                self.assertEqual(machine.state("return_status"), 0)

    def test_retired_phase_cannot_clear_poisoned_status_or_resource_receipts(self):
        for key, value in (("enter_status", 0), ("leave_status", 0), ("return_status", 1), ("native", Machine.PRIVATE),
                           ("native_pixels", 1), ("pending_header", Machine.PRIVATE),
                           ("pending_pixels", 1), ("battle", 0), ("empty_counters", 0)):
            with self.subTest(field=key):
                machine = Machine(self.tools)
                self.assertEqual(machine.enter()["EAX"], 1)
                self.assertEqual(machine.bind()["EAX"], 1)
                self.assertEqual(machine.invoke("try_leave", eax=machine.ROOT_SP - 172)["EAX"], 1)
                machine.put(0x532048, 0)
                machine.put(native.HOOK_OWNER, 0x40AD40)
                if key == "empty_counters":
                    machine.set_state("allocations", 0)
                    machine.set_state("frees", 0)
                else:
                    machine.set_state(key, value)
                self.assertEqual(machine.invoke("finish_return", eax=machine.ROOT_SP - 168)["EAX"], 0)
                self.assertNotEqual(machine.state("phase"), 0)
                self.assertEqual(machine.state("return_status"), 1 if key == "return_status" else 0)

    def test_active_phase_rejects_status_mutations_before_private_retirement(self):
        for key, value in (("enter_status", 0), ("leave_status", 1), ("return_status", 1)):
            with self.subTest(field=key):
                machine = Machine(self.tools)
                self.assertEqual(machine.enter()["EAX"], 1)
                self.assertEqual(machine.bind()["EAX"], 1)
                machine.set_state(key, value)
                self.assertEqual(machine.invoke("try_leave", eax=machine.ROOT_SP - 172)["EAX"], 0)
                self.assertEqual(machine.destructions, [])

    def test_hook_chain_bind_free_epilogue_keeps_native_ret4(self):
        for profile in context.PROFILES:
            for delta in (0, 0x2000000):
                with self.subTest(profile=profile, delta=delta):
                    machine = Machine(self.tools, profile, delta=delta)
                    machine.invoke("root_entry", sp=machine.ROOT_SP, stops=(0x42E9E9,))
                    machine.put(native.HOOK_OWNER + delta, 0x42E8B0 + delta)
                    machine.put(0x532048 + delta, machine.WORLD)
                    result = machine.invoke("bind_allocation", sp=machine.ROOT_SP - 168, stops=(0x42EC97,))
                    self.assertEqual(result["ESP"], machine.ROOT_SP - 168)
                    self.assertEqual(machine.state("phase"), 2)
                    machine.put(native.RENDER + delta, machine.PRIVATE)
                    machine.invoke("leave_before_free", eax=machine.WORLD, sp=machine.ROOT_SP - 172)
                    self.assertEqual(machine.frees, [machine.private_pixels, machine.PRIVATE, machine.WORLD])
                    self.assertEqual(machine.replayed_free_flags[0] & Machine.MASK, 0xED7 & Machine.MASK)
                    self.assertEqual(machine.state("phase"), 4)
                    machine.put(0x532048 + delta, 0)
                    machine.put(native.HOOK_OWNER + delta, 0x40AD40 + delta)
                    # Only the untouched native POP/RET4 continuation is used.
                    # The synthetic caller frame was entered through root_entry.
                    machine.cpu.mem_write(0x42F5B9 + delta, bytes.fromhex("5d5f5ec20400"))
                    machine.put(machine.ROOT_SP - 12, 0x44556677)
                    machine.put(machine.ROOT_SP - 8, 0x66778899)
                    machine.put(machine.ROOT_SP - 4, 0x55667788)
                    machine.put(machine.ROOT_SP, machine.STOP)
                    machine.put(machine.ROOT_SP + 4, 0xA5A5)
                    result = machine.invoke("root_epilogue", eax=0x44556677, sp=machine.ROOT_SP - 168)
                    self.assertEqual(result["EAX"], 0x44556677)
                    self.assertEqual(result["ESP"], machine.ROOT_SP + 8)
                    self.assertEqual(result["EFLAGS"] & Machine.MASK,
                                     self.native_stack_flags("81c49c000000", machine.ROOT_SP - 168, 0xED7))
                    self.assertEqual(machine.state("phase"), 0)

    def test_bind_hook_keeps_native_null_branch_and_fatal_cleanup_class(self):
        for profile in context.PROFILES:
            machine = Machine(self.tools, profile)
            machine.invoke("root_entry", sp=machine.ROOT_SP, stops=(0x42E9E9,))
            machine.put(native.HOOK_OWNER, 0x42E8B0)
            # Original JE following the replaced seven-byte CMP. There is no
            # fabricated nonfatal continuation or healthy map-return callback.
            machine.cpu.mem_write(0x42EC97, bytes.fromhex("0f8467030000"))
            result = machine.invoke("bind_allocation", sp=machine.ROOT_SP - 168, stops=(0x42F004,))
            self.assertEqual(machine.native_stop, 0x42F004)
            self.assertEqual(result["ESP"], machine.ROOT_SP - 168)
            self.assertEqual(machine.frees, [machine.private_pixels, machine.PRIVATE])
            self.assertEqual(machine.state("return_status"), 0)

    def test_thread_api_volatile_clobbers_and_repeated_visits_preserve_abi(self):
        for profile in context.PROFILES:
            machine = Machine(self.tools, profile)
            machine.thread_clobbers = True
            for visit in range(3):
                self.assertEqual(machine.enter()["EAX"], 1)
                self.assertEqual(machine.bind()["EAX"], 1)
                self.assertEqual(machine.invoke("try_leave", eax=machine.ROOT_SP - 172)["EAX"], 1)
                machine.put(0x532048, 0)
                machine.put(native.HOOK_OWNER, 0x40AD40)
                self.assertEqual(machine.invoke("finish_return", eax=machine.ROOT_SP - 168)["EAX"], 1)
                self.assertEqual(machine.state("allocations"), visit + 1)
                self.assertEqual(machine.state("frees"), visit + 1)
                self.assertEqual(machine.live, {})

    def test_owner_record_mutations_during_thread_callback_do_not_destroy(self):
        for key in ("phase", "fault", "native", "native_pixels", "physical", "root_esp"):
            with self.subTest(field=key):
                machine = Machine(self.tools)
                self.assertEqual(machine.enter()["EAX"], 1)
                self.assertEqual(machine.bind()["EAX"], 1)
                changed = False
                def mutate(m, name):
                    nonlocal changed
                    if name == "thread" and not changed:
                        changed = True
                        m.set_state(key, m.state(key) + 1)
                machine.mutation = mutate
                self.assertEqual(machine.invoke("try_leave", eax=machine.ROOT_SP - 172)["EAX"], 0)
                self.assertEqual(machine.destructions, [])
                self.assertEqual(machine.frees, [])

    def test_paired_header_and_receipt_aliases_cannot_free_physical_pixels(self):
        for target in (Machine.PHYSICAL_PIXELS, 0x10020000, 0x10000000, Machine.PRIVATE):
            with self.subTest(target=hex(target)):
                machine = Machine(self.tools)
                self.assertEqual(machine.enter()["EAX"], 1)
                self.assertEqual(machine.bind()["EAX"], 1)
                machine.put(machine.PRIVATE + 4, target)
                machine.set_state("native_pixels", target)
                self.assertEqual(machine.invoke("try_leave", eax=machine.ROOT_SP - 172)["EAX"], 0)
                self.assertEqual(machine.destructions, [])
                self.assertEqual(machine.frees, [])

    def test_paired_native_world_and_receipt_aliases_cannot_retire_private_owner(self):
        for target in (Machine.PRIVATE, Machine.PHYSICAL, Machine.BACKEND,
                       Machine.PHYSICAL_PIXELS, 0x10020000, 0x10000000):
            with self.subTest(target=hex(target)):
                machine = Machine(self.tools)
                self.assertEqual(machine.enter()["EAX"], 1)
                self.assertEqual(machine.bind()["EAX"], 1)
                machine.set_state("battle", target)
                machine.put(0x532048, target)
                self.assertEqual(machine.invoke("try_leave", eax=machine.ROOT_SP - 172)["EAX"], 0)
                self.assertEqual(machine.destructions, [])
                self.assertEqual(machine.frees, [])

    def test_forged_saved_render_and_owner_cannot_restore_freed_or_battle_targets(self):
        machine = Machine(self.tools)
        self.assertEqual(machine.enter()["EAX"], 1)
        self.assertEqual(machine.bind()["EAX"], 1)
        machine.set_state("saved_render", machine.PRIVATE)
        self.assertEqual(machine.invoke("try_leave", eax=machine.ROOT_SP - 172)["EAX"], 0)
        self.assertEqual(machine.destructions, [])
        valid = Machine(self.tools)
        self.assertEqual(valid.enter()["EAX"], 1)
        self.assertEqual(valid.bind()["EAX"], 1)
        self.assertEqual(valid.invoke("try_leave", eax=valid.ROOT_SP - 172)["EAX"], 1)
        valid.put(0x532048, 0)
        valid.set_state("saved_owner", 0x42E8B0)
        self.assertEqual(valid.invoke("finish_return", eax=valid.ROOT_SP - 168)["EAX"], 0)
        self.assertEqual(valid.state("return_status"), 0)
        self.assertNotEqual(valid.state("phase"), 0)

    def test_destructor_changes_never_become_a_second_free_or_clean_return(self):
        for key in ("phase", "fault", "physical", "root_esp", "modal_counter"):
            machine = Machine(self.tools, "completehd")
            self.assertEqual(machine.enter()["EAX"], 1)
            self.assertEqual(machine.bind()["EAX"], 1)
            def mutate(m, name):
                if name != "destroy": return
                if key == "modal_counter":
                    m.put(m.modal_va + native.STATE["mirrors"], 1)
                    m.inherited_snapshot = bytes(m.cpu.mem_read(m.modal_va, 128))
                else:
                    m.set_state(key, m.state(key) + 1)
            machine.mutation = mutate
            self.assertEqual(machine.invoke("try_leave", eax=machine.ROOT_SP - 172)["EAX"], 0)
            self.assertEqual(len(machine.destructions), 1)
            self.assertEqual(machine.state("phase"), 4)
            self.assertEqual(machine.state("fault"), 9)
            self.assertEqual(machine.state("native"), 0)
            self.assertEqual(machine.state("frees"), 1)
            self.assertEqual(machine.state("return_status"), 0)
            machine.mutation = None
            self.assertEqual(machine.invoke("try_leave", eax=machine.ROOT_SP - 172)["EAX"], 0)
            self.assertEqual(len(machine.destructions), 1)

    def test_second_allocation_constructor_and_thread_revalidation_keep_changes_unpublished(self):
        for callback, occurrence in (("allocate", 2), ("construct", 1), ("thread", 3)):
            with self.subTest(callback=callback, occurrence=occurrence):
                machine = Machine(self.tools, "modalwidgets")
                def mutate(m, name):
                    if name == callback and m.callbacks.count(name) == occurrence:
                        m.put(native.RENDER, native.PRIMARY)
                        m.put(m.modal_va + native.STATE["mirrors"], 1)
                        m.inherited_snapshot = bytes(m.cpu.mem_read(m.modal_va, 128))
                machine.mutation = mutate
                self.assertEqual(machine.enter()["EAX"], 0)
                self.assertEqual(machine.state("phase"), 0)
                self.assertEqual(machine.state("native"), 0)
                self.assertEqual(machine.state("enter_status"), 0)
                self.assertEqual(machine.live, {})

    def test_rollback_free_callback_changed_thread_stops_remaining_cleanup(self):
        machine = Machine(self.tools)
        changed = False
        def mutate(m, name):
            nonlocal changed
            if name == "construct":
                m.put(native.RENDER, native.PRIMARY)
            elif name == "free" and not changed:
                changed = True
                m.thread_id += 1
        machine.mutation = mutate
        self.assertEqual(machine.enter()["EAX"], 0)
        self.assertTrue(changed)
        self.assertNotEqual(machine.state("phase"), 0)
        self.assertNotEqual(machine.state("fault"), 0)
        self.assertEqual(machine.frees, [machine.private_pixels])
        self.assertEqual(machine.live, {machine.PRIVATE: 188})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolchain-path", type=Path)
    parser.add_argument("--require-machine-tools", action="store_true")
    parser.add_argument("--original-backed", type=Path)
    args = parser.parse_args(argv)
    if args.toolchain_path:
        sys.path.insert(0, str(args.toolchain_path.resolve()))
    if args.require_machine_tools:
        try:
            machine_tools()
        except ImportError as error:
            print(str(error), file=sys.stderr)
            return 2
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(
        unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in (SourceTests, CPUTests)))
    if not result.wasSuccessful():
        return 1
    if args.original_backed:
        original = args.original_backed.read_bytes()
        for profile, resolution in (("classic", "1024x768"), ("classic", "1366x768"),
                                    ("framed", "1366x768"), ("completehd", "1366x768"),
                                    ("modalwidgets", "1366x768")):
            bundle = tool.emit_battle_profile_lifecycle(original, profile, resolution)
            metadata = bundle.metadata()
            assert all(metadata[name] is False for name in context.FALSE_CLAIMS)
            assert metadata["installed"] is False
            assert metadata["emission_preparation_only"] is True
            assert len(bundle.hook_sites) == 4
            entries = dict(bundle.emission.entries)
            for name, site in zip(tool.SITES, bundle.hook_sites):
                va, old, _ = tool.SITES[name]
                assert site.va == va and site.rva == va - 0x400000
                assert site.old.hex() == old
                assert site.new[:1] == (b"\xE8" if name == "leave_before_free" else b"\xE9")
                assert va + 5 + struct.unpack_from("<i", site.new, 1)[0] == entries[name]
                assert site.offset == clip.file_offset(original, va, len(site.old))
            # Mutated public context/assembler/state aliases are deliberately
            # ignored by the production private-source reconstruction.
            with patch.object(context, "build_parent_context", side_effect=AssertionError("public context")), \
                    patch.object(clip, "_Assembler", side_effect=AssertionError("public assembler")), \
                    patch.dict(tool.STATE, {"fault": 128}):
                replay = tool.emit_battle_profile_lifecycle(original, profile, resolution)
            assert replay.emission.code == bundle.emission.code
            assert replay.metadata() == metadata
            assert args.original_backed.read_bytes() == original
            print("ORIGINAL_MEMORY_LIFECYCLE_PASS", profile, resolution, "native_execution=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
