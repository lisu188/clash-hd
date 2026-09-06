#!/usr/bin/env python3
"""Synthetic x86 trampoline fixtures; no game, debugger, window or hook install.

Uses the existing temporary no-window x86 runner. Only our emitted trampolines
execute: renderer calls target deliberately destructive fixture stubs and native
continuations target recorders followed by authenticated native epilogues.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher import partial_tile_clip as clip
from src.patcher import partial_tile_hooks as hooks
from src.patcher import patch_clash95_hd as patcher
import test_partial_tile_clip as runner

BASE = runner.BASE
SHIM = BASE + 0xB000
HELPER = BASE + 0x9000
CONTINUATIONS = {"hook_resume_full_converge": (BASE + 0x9200, 2, "83c4185d5f5e5a595bc3"),
                 "hook_native_full_epilogue": (BASE + 0x9400, 3, "83c4185d5f5e5a595bc3"),
                 "hook_resume_full_present": (BASE + 0x9600, 4, "83c4185d5f5e5a595bc3"),
                 "hook_resume_incremental": (BASE + 0x9800, 5, "83c4085d5f5e595bc3")}
ARITHMETIC_FLAGS = 0x8D5
INITIAL_FLAGS = 0x895


def recorder(kind: int, delta: int = 0) -> bytes:
    """Record GPR, flags and exact incoming ESP without altering guest state."""
    out = bytearray.fromhex("9c6089e5bf") + struct.pack("<I", runner.RECORD + delta)
    out += bytes.fromhex("8b376bf640ff078d7c3704c707") + struct.pack("<I", kind)
    for index, offset in enumerate((28, 16, 24, 20, 4, 0, 8, 32), 1):
        out += bytes((0x8B, 0x45, offset, 0x89, 0x47, 4 * index))
    out += bytes.fromhex("8d4524894724")
    for offset in range(40, 64, 4):
        out += bytes.fromhex("c747") + bytes([offset]) + bytes(4)
    if kind in (2, 3, 4):
        # Full native var_30 and the five adjacent locals at entry ESP.
        for index in range(6):
            out += bytes((0x8B, 0x45, 36 + 4 * index, 0x89, 0x47, 40 + 4 * index))
    return bytes(out) + bytes.fromhex("619d")


def helper_stub(status: int, delta: int, kind: int = 1) -> bytes:
    out = bytearray(recorder(kind, delta))
    # Unlike an optimistic recorder, smash every GPR except ESP and change
    # arithmetic flags. The trampoline must recover its own saved state.
    for opcode, value in ((0xBB, 0xB0B0B0B0), (0xB9, 0xC0C0C0C0), (0xBA, 0xD0D0D0D0),
                          (0xBE, 0xE0E0E0E0), (0xBF, 0xF0F0F0F0), (0xBD, 0xA0A0A0A0)):
        out += bytes([opcode]) + struct.pack("<I", value)
    out += bytes.fromhex("31c0f9b8") + struct.pack("<I", status & 0xFFFFFFFF) + b"\xc3"
    return bytes(out)


@unittest.skipUnless(os.name == "nt" and runner.CSC.is_file() and runner.ORIGINAL.is_file(),
                     "requires local x86 fixture compiler and user-owned original")
class HookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="clash-partial-hooks-fixture-")
        cls.root = Path(cls.temp.name)
        cls.exe = cls.root / "fixture.exe"
        source = cls.root / "fixture.cs"
        # Extend the shared runner only in this fixture's temporary source to
        # record flags immediately after RET, before native/CLR teardown.
        runner_source = runner.CSHARP
        anchor = "Save(b,0x15,Output+36);"
        if runner_source.count(anchor) != 1:
            raise AssertionError("shared fixture return-state recording changed")
        runner_source = runner_source.replace(anchor, anchor +
            "b.AddRange(new byte[]{0x9c,0x8f,0x05});Imm(b,Output+16);")
        anchor = "new int[]{0,4,8,12,20,24,28,32,36}"
        if runner_source.count(anchor) != 1:
            raise AssertionError("shared fixture state schema changed")
        runner_source = runner_source.replace(anchor, "new int[]{0,4,8,12,20,24,28,32,36,16}")
        source.write_text(runner_source, encoding="utf-8")
        compiled = subprocess.run([str(runner.CSC), "/nologo", "/platform:x86", "/optimize+",
                                   "/r:System.Web.Extensions.dll", f"/out:{cls.exe}", str(source)],
                                  capture_output=True, text=True, timeout=60,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
        if compiled.returncode:
            raise AssertionError(compiled.stdout + compiled.stderr)
        cls.original = runner.ORIGINAL.read_bytes()
        cls.bundles = {}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def candidate(self, width=800, height=600):
        recipe = patcher.select_patches_for(hooks.COMBINED_STAGE, patcher.parse_resolution(f"{width}x{height}"))
        return patcher.apply_patches(self.original, recipe)

    def bundle(self, width=800, height=600):
        key = (width, height)
        if key not in self.bundles:
            self.bundles[key] = hooks.emit_hook_bundle(self.original, self.candidate(*key),
                                                       base_va=BASE, width=width, height=height)
        return self.bundles[key]

    def execute(self, name, status, *, width=800, height=600, delta=0, callback=0, edge_status=1):
        bundle = self.bundle(width, height)
        code = bytearray(bundle.code)
        self.assertLess(len(code), 0x8000)
        for offset in clip.absolute_relocation_offsets(bundle):
            value = struct.unpack_from("<I", code, offset)[0]
            struct.pack_into("<I", code, offset, value + delta)
        for relocation in bundle.relocations:
            if relocation.purpose.startswith("hook_helper_"):
                target = HELPER + (0xA00 if name == "full_pair" and relocation.purpose == "hook_helper_present_map_rect" else 0)
                struct.pack_into("<I", code, relocation.offset,
                                 (target - (BASE + relocation.offset + 4)) & 0xFFFFFFFF)
            elif relocation.purpose in CONTINUATIONS:
                target = CONTINUATIONS[relocation.purpose][0]
                struct.pack_into("<I", code, relocation.offset,
                                 (target - (BASE + relocation.offset + 4)) & 0xFFFFFFFF)
            elif relocation.purpose in ("hook_post_tile_callback", "hook_cursor_x"):
                target = runner.GLOBAL + (28 if relocation.purpose == "hook_post_tile_callback" else 20)
                struct.pack_into("<I", code, relocation.offset, target + delta)
        shim = bytearray()
        if name != "incremental":
            shim += bytes.fromhex("53515256575583ec18")  # Actual full-redraw native frame.
            shim += bytes.fromhex("c70424") + struct.pack("<I", edge_status & 0xFFFFFFFF)
            for index in range(1, 6):
                shim += bytes.fromhex("c74424") + bytes([4 * index]) + struct.pack("<I", 0xABCD0000 + index)
        # Define flags after the native prologue without changing its GPRs.
        shim += bytes.fromhex("509c5825") + struct.pack("<I", ~ARITHMETIC_FLAGS & 0xFFFFFFFF)
        shim += b"\x0d" + struct.pack("<I", INITIAL_FLAGS) + bytes.fromhex("509d58e9")
        entry = "full_converge" if name == "full_pair" else name
        shim += struct.pack("<i", bundle.entries["hook_" + entry] - (SHIM + len(shim) + 4))
        stubs = {str(HELPER + delta): helper_stub(edge_status if name == "full_pair" else status, delta).hex(),
                 str(HELPER + 0xA00 + delta): helper_stub(status, delta, kind=6).hex(),
                 str(SHIM + delta): shim.hex()}
        for address, kind, epilogue in CONTINUATIONS.values():
            code_tail = bytearray(recorder(kind, delta))
            if name == "full_pair" and kind == 2:
                # Continue in the SAME native frame, after the existing owner
                # and frame gate. Their candidate bytes are authenticated.
                code_tail += b"\xe9" + struct.pack("<i", bundle.entries["hook_full_present"] - (address + len(code_tail) + 5))
            else:
                code_tail += bytes.fromhex(epilogue)
            stubs[str(address + delta)] = code_tail.hex()
        case = {"regs": [23, 0x123456, 0x654321, 29], "args": [], "entry": SHIM + delta,
                "post_tile_callback": callback, "cursor": 0x12345678}
        payload = {"code": code.hex(), "width": width, "height": height,
                   "base": BASE + delta, "image_delta": delta, "stubs": stubs, "cases": [case]}
        ran = subprocess.run([str(self.exe)], input=json.dumps(payload), capture_output=True,
                             text=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        result = json.loads(ran.stdout)[0]
        self.assertEqual(result["state"][1:4], [0x11223344, 0x55667788, 0x99AABBCC])
        self.assertEqual(result["state"][4], result["state"][5], "unbalanced native/trampoline stack")
        self.assertEqual(result["state"][6:9], case["regs"][1:])
        for row in result["records"]:
            if row[0] in (2, 3, 4):
                self.assertEqual(row[11:16], [0xABCD0000 + index for index in range(1, 6)])
        return result

    def test_exact_candidate_and_native_surroundings_fail_closed(self):
        for va in (0x4187A0, 0x4187A7, 0x4187AF, 0x4187B7, 0x4187BC, 0x4189A3,
                   0x418A90, 0x418A98, 0x418AFA, 0x51BE00):
            candidate = bytearray(self.candidate())
            candidate[clip.file_offset(candidate, va, 1)] ^= 1
            with self.assertRaises(ValueError):
                hooks.emit_hook_bundle(self.original, bytes(candidate), base_va=BASE, width=800, height=600)
        changed = bytearray(self.original); changed[0x1000] ^= 1
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            hooks.emit_hook_bundle(bytes(changed), self.candidate(), base_va=BASE, width=800, height=600)
        with self.assertRaises(ValueError):
            hooks.emit_hook_bundle(self.original, self.candidate(), base_va=BASE, width=1024, height=768)

    def test_bundle_prefix_identity_site_and_relocation_metadata(self):
        for width, height in ((800, 600), (1024, 768), (1920, 1080)):
            result = self.bundle(width, height)
            candidate = self.candidate(width, height)
            guarded = clip.emit_map_composition(self.original, candidate, base_va=BASE, width=width, height=height)
            self.assertEqual(result.code[:len(guarded.code)], guarded.code)
            self.assertEqual(result.relocations[:len(guarded.relocations)], guarded.relocations)
            self.assertFalse(result.installation_ready)
            self.assertEqual(result.candidate_sha256, hashlib.sha256(candidate).hexdigest())
            self.assertEqual(tuple(site.removed_highlow_vas for site in result.hook_sites),
                             ((0x4187A2,), (0x4187B8,), ()))
            for site, spec in zip(result.hook_sites, hooks.SITES):
                self.assertEqual((site.name, site.va, site.old_bytes, site.fallback_va), spec[:4])
                self.assertEqual(candidate[site.offset:site.offset + len(site.old_bytes)], site.old_bytes)
                self.assertEqual(site.rva, site.va - hooks.IMAGE_BASE)
                self.assertGreaterEqual(site.entry_va, BASE + len(guarded.code))
                status = result.status_vas[site.name]
                pos = status - BASE
                self.assertEqual(result.code[pos - 5], 0xE8)
                self.assertTrue(any(r.offset == pos - 4 and r.kind == "rel32" and r.purpose.startswith("hook_helper_")
                                    for r in result.relocations))
            extra = result.relocations[len(guarded.relocations):]
            self.assertEqual([(r.purpose, r.target) for r in extra if r.kind == "abs32"],
                             [("hook_post_tile_callback", 0x526990), ("hook_cursor_x", 0x544CFC)])
            self.assertEqual(len(clip.absolute_relocation_offsets(result)), len(clip.absolute_relocation_offsets(guarded)) + 2)

    def test_full_convergence_restores_state_and_replays_native_cmp(self):
        for status in (0, 1, 2, 0xFFFFFFFF):
            for callback in (0, 0x12345678):
                result = self.execute("full_converge", status, callback=callback)
                helper, continuation = result["records"]
                self.assertEqual([r[0] for r in result["records"]], [1, 2])
                self.assertEqual(helper[1], 0)
                self.assertEqual(continuation[1:8], [23, 0x123456, 0x654321, 29, 0x11223344, 0x55667788, 0x99AABBCC])
                expected_flags = (0x40 if callback == 0 else 0) | (0x4 if (callback & 255).bit_count() % 2 == 0 else 0)
                self.assertEqual(continuation[8] & ARITHMETIC_FLAGS, expected_flags)
                self.assertEqual(continuation[9] - helper[9], 40)
                self.assertEqual(continuation[10], status & 0xFFFFFFFF)
                self.assertEqual(result["state"][0], 23)

    def test_full_present_exact_success_and_fallback_restore_flags_and_gpr(self):
        for width, height in ((800, 600), (1024, 768)):
            for status in (0, 1, 2, 0xFFFFFFFF):
                result = self.execute("full_present", status, width=width, height=height)
                helper, continuation = result["records"]
                self.assertEqual(helper[1:5], [32, 16, width - 1, height - 1])
                self.assertEqual(continuation[0], 3 if status == 1 else 4)
                self.assertEqual(continuation[1], 23 if status == 1 else 0x12345678)
                self.assertEqual(continuation[2:8], [0x123456, 0x654321, 29, 0x11223344, 0x55667788, 0x99AABBCC])
                self.assertEqual(continuation[8] & ARITHMETIC_FLAGS, INITIAL_FLAGS)
                self.assertEqual(continuation[9] - helper[9], 40)
                self.assertEqual(result["state"][0], continuation[1])

    def test_incremental_preserves_inputs_and_replays_native_fallback_frame(self):
        for status in (0, 1, 2, 3, 0xFFFFFFFF):
            result = self.execute("incremental", status)
            helper = result["records"][0]
            self.assertEqual(helper[1:5], [23, 0x123456, 0x654321, 29])
            self.assertEqual(helper[8] & ARITHMETIC_FLAGS, INITIAL_FLAGS)
            self.assertEqual(result["state"][0], 23)
            if status in (1, 2):
                self.assertEqual(len(result["records"]), 1)
                self.assertEqual(result["state"][9] & ARITHMETIC_FLAGS, INITIAL_FLAGS)
            else:
                continuation = result["records"][1]
                self.assertEqual(continuation[0], 5)
                self.assertEqual(continuation[1:8], [23, 0x123456, 0x654321, 29, 0x11223344, 0x55667788, 0x99AABBCC])
                self.assertEqual(continuation[9] - helper[9], 12)
                # Original SUB ESP,8 determines fallback arithmetic flags.
                before = continuation[9] + 8
                after = continuation[9]
                expected_flags = (0x10 if (before ^ 8 ^ after) & 0x10 else 0) | (0x4 if (after & 255).bit_count() % 2 == 0 else 0)
                self.assertEqual(continuation[8] & ARITHMETIC_FLAGS, expected_flags)

    def test_paired_full_status_blocks_presentation_after_rejected_edge_work(self):
        for delta in (0, 0x02000000):
            for edge_status in (0, 1, 2, 0xFFFFFFFF):
                for present_status in (0, 1, 2):
                    result = self.execute("full_pair", present_status, edge_status=edge_status, delta=delta)
                    records = result["records"]
                    expected = [1, 2] + ([6] if edge_status == 1 else [])
                    expected += [3 if edge_status == present_status == 1 else 4]
                    self.assertEqual([row[0] for row in records], expected, (edge_status, present_status))
                    self.assertEqual(records[1][10], edge_status & 0xFFFFFFFF)
                    self.assertEqual(records[-1][10], edge_status & 0xFFFFFFFF)
                    self.assertEqual(records[-1][9], records[1][9], "paired hooks changed native frame depth")
                    self.assertEqual(records[-1][8] & ARITHMETIC_FLAGS, records[1][8] & ARITHMETIC_FLAGS)
                    self.assertEqual(result["state"][0], 23 if edge_status == present_status == 1 else 0x12345678)
        # A direct presentation entry with an old/uninitialized non-success
        # stack value cannot manufacture a fresh full-edge pass.
        for edge_status in (0, 2, 0xFFFFFFFF):
            result = self.execute("full_present", 1, edge_status=edge_status)
            self.assertEqual([row[0] for row in result["records"]], [4])
            self.assertEqual(result["records"][0][8] & ARITHMETIC_FLAGS, INITIAL_FLAGS)

    def test_native_status_local_is_initialized_before_original_fallback_reads(self):
        off = clip.file_offset(self.original, 0x418700, 0x390)
        original = self.original[off:off + 0x390]
        self.assertEqual(hashlib.sha256(original).hexdigest(), hooks.FULL_REDRAW_ORIGINAL_SHA256)
        # Exactly the audited later write/read instructions, not an accidental
        # similarly encoded write to another local at an earlier stack depth.
        expected = {0x4188E2: "89442410", 0x4188F0: "8b0424", 0x4188FE: "8b4c240c"}
        for va, encoded in expected.items():
            data = bytes.fromhex(encoded)
            self.assertEqual(original[va - 0x418700:va - 0x418700 + len(data)], data)
        self.assertEqual(hooks.FULL_STATUS_SAVED_FRAME_OFFSET, 32 + 4)

    def test_trampolines_rebase_with_the_image(self):
        for name, status in (("full_converge", 0), ("full_present", 0), ("full_present", 1),
                             ("incremental", 0), ("incremental", 1), ("incremental", 2)):
            result = self.execute(name, status, delta=0x02000000, callback=0x12345678)
            self.assertTrue(result["records"])


if __name__ == "__main__":
    unittest.main()
