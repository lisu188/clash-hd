#!/usr/bin/env python3
"""Repo-only visible-probe contract fixtures; optional real files are read only."""
import argparse
from pathlib import Path
import re
import struct
import unittest

import battle_hd_visible_probe as probe


class VisibleProbeTests(unittest.TestCase):
    def test_debugger_setup_uses_documented_masm_and_radix_commands(self):
        # Run-01 continued past syntax errors in `expr` and `.radix`. These
        # must be actual CDB commands, before any MASM byte/geometry checks.
        self.assertEqual(probe.DEBUGGER_SETUP_COMMANDS, ("bc *", ".expr /s masm", "n 16"))

    def test_load_transition_never_retires_instrumented_worker_sleep(self):
        rows = probe.commands()
        sites = {row[0] for row in rows.values()}
        self.assertIn(probe.MAIN_STARTUP_SLEEP_VA, sites)
        self.assertTrue(sites.isdisjoint(probe.WORKER_SLEEP_VAS))
        # Absent worker IDs must not survive in the old range(10) retirement.
        retired = {int(v) for v in re.findall(r"\bbd\s+([0-9]+)\b", rows[9][1])}
        self.assertEqual(retired, {0, 4, 6, 7, 8, 9})
        self.assertTrue(retired <= rows.keys())
        self.assertNotIn("80000003", "\n".join(row[1] for row in rows.values()))
        # The main startup skip itself still executes only during phase0.
        self.assertTrue(rows[0][1].startswith(".if (@$t0 == 0)"))
        for worker_va in probe.WORKER_SLEEP_VAS:
            forged = dict(rows)
            forged[1] = (worker_va, "gc", "observer")
            with self.assertRaisesRegex(ValueError, "worker Sleep"):
                probe.validate_commands(forged)

    def test_breakpoint_lifecycle_rejects_undefined_enable_and_disable_ids(self):
        rows = probe.commands()
        for operation in ("bd", "be", "bc"):
            forged = dict(rows)
            va, body, kind = forged[9]
            forged[9] = (va, f"{operation} 1; " + body, kind)
            with self.assertRaisesRegex(ValueError, "undefined ID 1"):
                probe.validate_commands(forged)
        # Removing an observer must also fail when entry would still arm it.
        del rows[53]
        with self.assertRaisesRegex(ValueError, "undefined ID 53"):
            probe.validate_commands(rows)

    def test_rejects_wrong_candidate_original_save_and_stage(self):
        for kwargs in ({}, {"stage": "centered"}, {"resolution": "800x600"}):
            with self.assertRaises(ValueError):
                probe.build_probe(b"wrong original", b"wrong candidate", b"wrong save", **kwargs)
        # All identities are immutable reviewed constants, not CLI assertions.
        self.assertEqual(probe.CANDIDATE_SHA256, "99d92ec7c8f81debf60321dcc5c1b5872c96e3c485fa2bdd7d9332287b3c7e87")
        self.assertEqual(probe.PROTOCOL, "expanded_battle_visible_observers_v3")
        self.assertEqual(probe.SAVE_BYTES, 586414)

    def test_unique_ids_sites_lengths_and_native_acquisition(self):
        rows = probe.commands()
        probe.validate_commands(rows)
        self.assertEqual(len(rows), len({v[0] for v in rows.values()}))
        for i, (va, body, kind) in rows.items():
            self.assertLessEqual(len(probe.breakpoint(i, va, body)), 4000)
            self.assertNotIn(va, (0x47BD66, 0x47BDAE, 0x47BF30))
        by_va = {v[0]: v for v in rows.values()}
        self.assertIn("hresult=%p", by_va[0x47BD6F][1])
        self.assertIn("hresult=%p", by_va[0x47BDB7][1])
        self.assertIn("@eax", by_va[0x47C02C][1])
        self.assertIn("input_valid=%d", by_va[0x47C02C][1])
        self.assertIn("(@eax == 0)", by_va[0x47C02C][1])

    def test_observer_mutations_and_collisions_fail_closed(self):
        rows = probe.commands()
        for bad in ("r eax=1; gc", "r @eip=0042cb50; gc", "ed 0053205c 1; gc", "eb 005451c0 80; gc"):
            forged = dict(rows)
            forged[20] = (rows[20][0], bad, "observer")
            with self.assertRaises(ValueError):
                probe.validate_commands(forged)
        forged = dict(rows)
        forged[59] = (rows[20][0], "gc", "observer")
        with self.assertRaises(ValueError):
            probe.validate_commands(forged)
        forged[59] = (0x47BF30, "gc", "observer")
        with self.assertRaises(ValueError):
            probe.validate_commands(forged)
        forged[59] = (0x400000, "x" * 4001, "observer")
        with self.assertRaises(ValueError):
            probe.validate_commands(forged)

    def test_forced_setup_is_separate_from_battle_gate(self):
        rows = probe.commands()
        click = rows[5][1]
        self.assertEqual(click.count("r eax=1"), 1)
        self.assertIn("@$t0 == 0", click.split("r eax=1")[0])
        self.assertNotIn("r eax=", click.split(".elsif", 1)[1])
        self.assertIn("BHDV_FORCED_BATTLE_SETUP", rows[10][1])
        self.assertIn("(@esp == @$t2-0n36)", rows[10][1])
        self.assertIn("ed @esp @edi @esi @ebp (@esp+0n36) @ebx @edx @ecx @eax @efl", rows[10][1])
        self.assertIn("r efl=poi(@esp+0n32); r esp=@esp+0n36", rows[10][1])
        self.assertIn("ed 0051d01c @$t4", rows[10][1])
        self.assertNotIn("ed 0053205c", "\n".join(v[1] for v in rows.values()))
        self.assertNotIn("-0n80", "\n".join(v[1] for v in rows.values()))
        self.assertIn("bd 11; bd 12", rows[13][1])
        self.assertIn("input_proof=0 manual_proof=0", rows[19][1])

    def test_readiness_has_all_live_descriptors_and_bounds(self):
        rows = probe.commands()
        readiness = "\n".join(rows[i][1] for i in (14, 17, 18, 19))
        for i, desc in enumerate(probe.DESCRIPTORS):
            self.assertEqual(readiness.count(f"index={i} desc={desc:08x}"), 1)
            self.assertIn(f"== {probe.CALLBACKS[i]:08x}", readiness)
        self.assertIn("input_bounds=(%d,%d,%d,%d)", readiness)
        self.assertIn("cursor_meta=%p input_bounds=(%d,%d,%d,%d)", rows[20][1])
        self.assertIn("poi(00544d14)", rows[20][1])
        self.assertIn("arena=(%d,%d) camera=(%d,%d)", readiness)
        self.assertIn("poi(poi(00532048)+0n800) == 7", readiness)
        self.assertIn("poi(poi(00532048)+0n812) == 0", readiness)
        self.assertIn("attack_available=%d attack_enabled=%d", readiness)
        snapshot = probe.snapshot_script()
        self.assertEqual(len(snapshot.splitlines()), 3)
        self.assertTrue(all(len(line) < 4000 for line in snapshot.splitlines()))
        self.assertNotRegex(snapshot, r"(?:^|;)\s*(?:r\s|e[bdwq]\s)")
        self.assertNotIn("BHDV_READY", snapshot)

    def test_log_bounds_leave_native_action_state_untouched(self):
        rows = probe.commands()
        self.assertIn("bd 20; bd 21; bd 22", rows[20][1])
        self.assertIn("bd 23", rows[23][1])
        self.assertIn("@$t8 < 8", rows[23][1])
        self.assertIn("poi(@esp+5c) != @$t16", rows[23][1])
        self.assertIn("by(005451c0) != 0", rows[24][1])
        self.assertIn("@ebx != @$t5", rows[27][1])
        for i in (24, 26, 27, 28, 34, 49):
            self.assertIn(f"bd {i}", rows[i][1])
        # Escaping must preserve one real newline when CDB evaluates a BP.
        encoded = probe.breakpoint(1, 0x400000, probe.printf("EXAMPLE", "result=%p", "@eax"))
        self.assertIn(r'\\n\"', encoded)
        self.assertNotIn("\n", encoded)

    def test_pe_mapping_rejects_padding_truncation_and_ambiguous_sections(self):
        data = bytearray(0x500)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 0x3C, 0x80)
        data[0x80:0x84] = b"PE\0\0"
        struct.pack_into("<HH", data, 0x84, 0x14C, 1)
        struct.pack_into("<H", data, 0x94, 0xE0)
        struct.pack_into("<H", data, 0x98, 0x10B)
        struct.pack_into("<I", data, 0x98+28, 0x400000)
        table = 0x178
        struct.pack_into("<IIII", data, table+8, 0x1000, 0x1000, 0x100, 0x300)
        data[0x300:0x304] = b"ABCD"
        self.assertEqual(probe.read_va(bytes(data), 0x401000, 4), (0x300, b"ABCD"))
        for va, size in ((0x401100, 4), (0x4010FF, 2), (0x401000, 0)):
            with self.assertRaises(ValueError):
                probe.read_va(bytes(data), va, size)
        with self.assertRaises(ValueError):
            probe.read_va(bytes(data[:0x200]), 0x401000, 4)
        struct.pack_into("<H", data, 0x86, 2)
        struct.pack_into("<IIII", data, table+48, 0x1000, 0x1000, 0x100, 0x400)
        with self.assertRaises(ValueError):
            probe.read_va(bytes(data), 0x401000, 4)


def verify_actual_files(original: Path, candidate: Path, save: Path) -> None:
    values = tuple(p.read_bytes() for p in (original, candidate, save))
    script, packet = probe.build_probe(*values)
    assert packet["probe_sha256"] == probe.sha(script.encode("ascii"))
    assert packet["candidate_sha256"] == probe.CANDIDATE_SHA256
    first_bp = re.search(r"^bp\d+ ", script, re.M).start()
    assert script.index("BHDV_BYTE_CONTRACT") < first_bp
    assert script.index("loaded_bytes_") < first_bp
    lines = script.splitlines()
    assert lines[1:4] == ["bc *", ".expr /s masm", "n 16"]
    assert "expr /s masm" not in lines and ".radix 16" not in lines
    assert not packet["startup_policy"]["worker_sleep_breakpoints"]
    assert set(packet["startup_policy"]["native_worker_sleep_vas"]) == set(probe.WORKER_SLEEP_VAS)
    assert not packet["manual_input_proof"] and not packet["runtime_observed"]
    for index in range(3):
        corrupted = list(values)
        corrupted[index] = corrupted[index][:-1] + bytes([corrupted[index][-1] ^ 1])
        try:
            probe.build_probe(*corrupted)
        except ValueError:
            pass
        else:
            raise AssertionError(f"changed input{index} accepted")
    print(f"Actual-file build verified: {len(packet['byte_spans'])} exact spans; candidate={packet['candidate_sha256']}; no files written or runtime launched")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--save", type=Path)
    args = parser.parse_args()
    if any((args.original, args.candidate, args.save)) and not all((args.original, args.candidate, args.save)):
        parser.error("all three file paths required for optional actual-file checks")
    outcome = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(VisibleProbeTests))
    if not outcome.wasSuccessful():
        raise SystemExit(1)
    if args.original:
        verify_actual_files(args.original, args.candidate, args.save)
