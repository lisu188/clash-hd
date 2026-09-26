"""Repo-only fixtures for the additive 0EDEF headless cursor observer.

Optional executable arguments verify actual user-owned PE bytes, without running
the game, CDB, wrapper, input, or captures. Historical 7D04 files stay unchanged.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import struct
import unittest

import battle_hd_headless_cursor_probe as probe

SOURCE_EXE = CANDIDATE_EXE = None


def small_pe(payload=b"\x12\x34\x56\x78"):
    raw = bytearray(0x400)
    raw[:2] = b"MZ"
    struct.pack_into("<I", raw, 0x3C, 0x80)
    raw[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", raw, 0x86, 1)
    struct.pack_into("<H", raw, 0x94, 0xE0)
    struct.pack_into("<H", raw, 0x98, 0x10B)
    struct.pack_into("<I", raw, 0xB4, 0x400000)
    struct.pack_into("<III", raw, 0x178 + 12, 0x1000, 0x200, 0x200)
    raw[0x220:0x224] = payload
    return bytes(raw)


class HeadlessCursorProbeTests(unittest.TestCase):
    def setUp(self):
        self.rows = probe.observer_breakpoints()
        self.text = "\n".join(self.rows)
        self.by_va = {int(m[1], 16): m[2] for line in self.rows if (m := re.fullmatch(r'bp\d+ ([0-9A-F]{8}) "(.*)"', line))}

    def test_wrong_source_and_old_candidate_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "original SHA mismatch"):
            probe.build(b"unknown original", b"unknown candidate")
        # The strict candidate gate is not satisfied by any old protocol pin.
        self.assertEqual(probe.CANDIDATE_SHA, "0edef38dac3c5036c6012adde248bc57736273cc1bbcbb9fd05e5867a1946ca0")
        from unittest.mock import patch
        with patch.object(probe, "sha256", side_effect=[probe.ORIGINAL_SHA, "7d04fe9005515dad4e618df507103946265d7e2a6421287281c1fc5f112d1e47"]):
            with self.assertRaisesRegex(ValueError, "candidate SHA mismatch"):
                probe.build(b"source", b"old candidate")

    def test_pe_mapping_rejects_missing_truncated_and_wrong_bytes(self):
        raw = small_pe()
        self.assertEqual(probe.read_va(raw, 0x401020, 4), b"\x12\x34\x56\x78")
        probe.verify_bytes(raw, ((0x401020, "12345678"),), "fixture")
        with self.assertRaisesRegex(ValueError, "byte mismatch"):
            probe.verify_bytes(small_pe(b"\x12\x34\x56\x79"), ((0x401020, "12345678"),), "fixture")
        for address, size in ((0x400220, 4), (0x4011FF, 2), (0x401000, 0)):
            with self.assertRaises(ValueError):
                probe.read_va(raw, address, size)
        with self.assertRaises(ValueError):
            probe.read_va(raw[:0x222], 0x401020, 4)

    def test_loaded_guard_covers_every_byte_without_signed_dwords(self):
        for va, expected in probe.NATIVE + probe.PATCHED:
            raw = bytes.fromhex(expected)
            guard = probe.guard(va, expected)
            self.assertNotIn("poi(", guard)
            self.assertIn("; q }", guard)
            reads = re.findall(r"(wo|by)\(([0-9a-f]{8})\) != 0x([0-9a-f]+)", guard)
            reconstructed = bytearray()
            for accessor, address, literal in reads:
                self.assertEqual(int(address, 16), va + len(reconstructed))
                self.assertLessEqual(int(literal, 16), 0xFFFF)
                reconstructed.extend(int(literal, 16).to_bytes(2 if accessor == "wo" else 1, "little"))
            self.assertEqual(bytes(reconstructed), raw)
        patched = dict(probe.PATCHED)
        self.assertEqual(bytes.fromhex(patched[0x460A61]), bytes.fromhex("e99a2a1000") + b"\x90" * 33)
        self.assertEqual(len(bytes.fromhex(patched[0x563500])), 81)
        self.assertEqual(len(bytes.fromhex(patched[0x563400])), 53)
        self.assertIn("813dd8995100b0e84200", patched[0x563500])
        self.assertEqual(dict(probe.NATIVE)[0x4E80F0][16:24], "02000000")

    def test_observer_has_no_target_writes_input_forcing_or_shared_scratch(self):
        self.assertNotRegex(self.text, r"(?i)(?:^|[;{])\s*(?:r\s|e[bwdq]\s|\.call\b|g(?:h|n)?\s*$|ba\s|bc\s|be\s|bd\s|as\s)")
        self.assertNotRegex(self.text, r"@\$t\d+\b")
        self.assertNotIn("__SURFACE_DUMP_ACTION__", self.text)
        self.assertNotIn("BATTLE_HD_LIFECYCLE_CURSOR_", self.text)
        for body in self.by_va.values():
            for field in ("caller=%p", "tid=%x", "cursor_sp=%p", "eip=%p", "esp=%p", "owner=%p", "battle=%p"):
                self.assertIn(field, body)
            for caller in probe.CALLERS:
                self.assertIn(f"== {caller:08X}", body)
            self.assertTrue(body.endswith("; gc"))
            self.assertIn(r"\\n", body)
        self.assertEqual(set(self.by_va), {0x460AF0, 0x47C029, 0x47C02C, 0x563500, 0x563547, 0x56354C, 0x460A87, 0x460B1A})

    def test_native_stack_arithmetic_call_return_and_helper_identity(self):
        # Independently account native x86 frames, not generator constants:
        # update saves5 GPRs; wrapper call +6 GPRs; pump call +5 GPRs
        # +8 local bytes; cursor call +ECX. stdcall consumes12 argument bytes.
        update = 5 * 4
        wrapper = update + 4 + 6 * 4
        pump = wrapper + 4 + 5 * 4 + 8
        cursor = pump + 4 + 4
        self.assertEqual((update, wrapper, pump, cursor), (0x14, 0x30, 0x50, 0x58))
        frames = ((update, 0x4614DD), (wrapper, 0x460611), (pump, 0x460B19))
        for va in (0x563500, 0x563547, 0x56354C, 0x460A87):
            body = self.by_va[va]
            self.assertIn("(@edx == 00544CD8)", body)
            for offset, target in frames:
                self.assertIn(f"(poi(@esp+0x{offset:x}) == {target:08X})", body)
            self.assertIn("poi(@esp+0x58), @$tid, @esp+0x58", body)
            # Wrong owners must be recorded, so fallback cannot disappear.
            self.assertNotIn("poi(005199d8) ==", body)
        poll_frame = 3 * 4 + 0x60
        for va, extra in ((0x47C029, poll_frame + 12), (0x47C02C, poll_frame)):
            body = self.by_va[va]
            self.assertIn(f"(poi(@esp+0x{extra:x}) == 00460A61)", body)
            for offset, target in frames:
                self.assertIn(f"(poi(@esp+0x{offset + extra + 4:x}) == {target:08X})", body)
            self.assertIn(f"poi(@esp+0x{cursor + extra + 4:x}), @$tid", body)
        self.assertIn("(poi(@esp+4) == 0n16)", self.by_va[0x47C029])
        self.assertIn("(poi(@esp+8) == (@esp+0x5c))", self.by_va[0x47C029])
        self.assertIn("hresult=%p buffer=%p after=(%p,%p,%p,%p)", self.by_va[0x47C02C])
        self.assertIn("@eax, @esp+0x50", self.by_va[0x47C02C])

    def test_source_binding_and_collision_rejection(self):
        records = probe.verify_sources()
        self.assertEqual(len(records), 3)
        life, base, harness = (p.read_text(encoding="utf-8") for p in (probe.LIFECYCLE, probe.BASE, probe.HARNESS))
        inventory = probe.verify_inventory(self.rows, life, base, harness)
        self.assertLess(inventory["inherited_bp_upper_bound"], 100)
        for bad_base in (base + '\nbp 0047C02C "gc"', base + '\nbp100 00400000 "gc"', base + '\nbp 00400000 "gc"' * 100):
            with self.assertRaises(ValueError):
                probe.verify_inventory(self.rows, life, bad_base, harness)
        with self.assertRaises(ValueError):
            probe.verify_inventory(self.rows + [self.rows[0]], life, base, harness)
        with self.assertRaises(ValueError):
            probe.verify_inventory([self.rows[0].replace("bp100 ", "bp99 ")] + self.rows[1:], life, base, harness)
        from unittest.mock import patch
        with patch.object(probe, "DEPENDENCIES", ((probe.LIFECYCLE, ("0" * 64,)),)):
            with self.assertRaisesRegex(ValueError, "dependency SHA mismatch"):
                probe.verify_sources()

    def test_lifecycle_exact_checkout_forms_report_actual_raw_hash(self):
        from unittest.mock import patch
        read = Path.read_bytes
        lf = read(probe.LIFECYCLE).replace(b"\r\n", b"\n")
        for raw in (lf, lf.replace(b"\n", b"\r\n")):
            with patch.object(Path, "read_bytes", lambda path: raw if path == probe.LIFECYCLE else read(path)):
                records = probe.verify_sources()
            record = records[str(probe.LIFECYCLE.relative_to(probe.ROOT))]
            self.assertEqual(record, {"sha256": probe.sha256(raw), "bytes": len(raw)})
        for invalid in (lf + b"# changed\n", lf.replace(b"\n", b"\r\n", 1)):
            with patch.object(Path, "read_bytes", lambda path: invalid if path == probe.LIFECYCLE else read(path)):
                with self.assertRaisesRegex(ValueError, "dependency SHA mismatch"):
                    probe.verify_sources()

    def test_command_length_and_historical_protocol_unchanged(self):
        self.assertLess(max(map(len, self.rows)), 4095)
        historical = (probe.ROOT / "probes/cdb/battle/clash95_battle_hd_cursor_diagnostic.cdb").read_text(encoding="utf-8")
        self.assertIn("7d04fe9005515dad4e618df507103946265d7e2a6421287281c1fc5f112d1e47", historical)
        self.assertIn("(wo(00460a61) != 0xaae9)", historical)
        self.assertNotIn("BHDH_CURSOR_", historical)

    def test_actual_original_candidate_and_full_bundle(self):
        if not SOURCE_EXE or not CANDIDATE_EXE:
            self.skipTest("optional user-owned exact executable bytes")
        text, manifest = probe.build(SOURCE_EXE.read_bytes(), CANDIDATE_EXE.read_bytes())
        life = probe.LIFECYCLE.read_text(encoding="utf-8").rstrip()
        self.assertIn(life, text)
        first_life_bp = text.index('\nbp ')
        for va, raw in probe.NATIVE + probe.PATCHED:
            self.assertLess(text.index(probe.guard(va, raw)), first_life_bp)
        self.assertLess(max(map(len, text.splitlines())), 4095)
        self.assertEqual(manifest["status"], "prepared_not_run")
        self.assertIsNone(manifest["runtime_result"])
        for key in ("visible_acceptance", "manual_input_proof", "promotion_ready"):
            self.assertFalse(manifest[key])
        self.assertIn("bypassed", manifest["initial_acquisition"])
        self.assertEqual(manifest["input_responsiveness"], "not_applicable_hidden")
        self.assertEqual(manifest["record_identity"], ["caller", "tid", "cursor_sp"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-exe", type=Path)
    parser.add_argument("--candidate-exe", type=Path)
    args, unittest_args = parser.parse_known_args()
    if bool(args.source_exe) != bool(args.candidate_exe):
        parser.error("provide both executable arguments")
    SOURCE_EXE, CANDIDATE_EXE = args.source_exe, args.candidate_exe
    unittest.main(argv=[__file__] + unittest_args)
