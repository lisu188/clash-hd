"""Repo-only contract tests for the additive, observation-only cursor probe.

Optional binary arguments read user-owned files and verify complete SHA/bytes.
No game, debugger, wrapper, input, or capture is launched.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "probes/cdb/battle/clash95_battle_hd_cursor_diagnostic.cdb"
ORIGINAL_SHA = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
CANDIDATE_SHA = "7d04fe9005515dad4e618df507103946265d7e2a6421287281c1fc5f112d1e47"
CONTRACTS = (
    (0x460af0, "5181e2ffff00008b8854040000d3e289502431d28b88540400006689dad3e2895028", "original"),
    (0x460b14, "e8b7faffff", "original"),
    (0x460b1a, "c3", "original"),
    (0x4605d0, "535156575583ec08", "original"),
    (0x46060e, "ff5114", "original"),
    (0x460a50, "535152565789c2b898515400e86fb50100", "original"),
    (0x460a61, "e9aa8d0800", "candidate"),
    (0x47bfd0, "53515283ec6089c3", "original"),
    (0x47c01c, "8d542450528b40086a108b0850ff51243d1e00078075098b4308508b10ff521c", "original"),
    (0x47c03c, "8b4424508943108b442454894314", "original"),
    (0x4e9810, "89d76a006a0054ff35dc525400ff15e0a34e00a1a8515400", "candidate"),
    (0x50f1f8, "500a4600", "original"),
)
CALLERS = (0x42DA46, 0x42DE6E, 0x566533)
SOURCE_EXE = None
CANDIDATE_EXE = None


def guard_line(va, hex_bytes):
    raw = bytes.fromhex(hex_bytes)
    clauses = []
    offset = 0
    while offset < len(raw):
        size = 2 if len(raw) - offset >= 2 else 1
        accessor = {2: "wo", 1: "by"}[size]
        value = int.from_bytes(raw[offset:offset + size], "little")
        clauses.append(f"({accessor}({va + offset:08x}) != 0x{value:0{size * 2}x})")
        offset += size
    return f".if ({' | '.join(clauses)}) {{ .echo BATTLE_HD_CURSOR_DIAG_FAIL bytes_{va:08x}; q }}"


def read_va(raw, va, size):
    """Resolve checked VA through the actual PE section table."""
    pe = int.from_bytes(raw[0x3c:0x40], "little")
    if raw[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not PE")
    image_base = int.from_bytes(raw[pe + 52:pe + 56], "little")
    count = int.from_bytes(raw[pe + 6:pe + 8], "little")
    optional_size = int.from_bytes(raw[pe + 20:pe + 22], "little")
    table = pe + 24 + optional_size
    rva = va - image_base
    for index in range(count):
        row = table + 40 * index
        section_rva = int.from_bytes(raw[row + 12:row + 16], "little")
        raw_size = int.from_bytes(raw[row + 16:row + 20], "little")
        raw_offset = int.from_bytes(raw[row + 20:row + 24], "little")
        if section_rva <= rva and rva + size <= section_rva + raw_size:
            return raw[raw_offset + rva - section_rva:raw_offset + rva - section_rva + size]
    raise ValueError(f"VA {va:08x} not backed by section bytes")


class CursorProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PROBE.read_text(encoding="utf-8")
        cls.breakpoints = {
            int(match[1], 16): match[2]
            for line in cls.text.splitlines()
            if (match := re.fullmatch(r'bp ([0-9A-F]{8}) "(.*)"', line))
        }

    def test_all_guarded_bytes_precede_breakpoints(self):
        first_bp = self.text.index("\nbp ")
        # CDB MASM may sign-extend high-bit32 literals while poi remains
        # zero-extended. Word/byte reads preserve the exact contract safely.
        guards = self.text[:first_bp]
        self.assertNotIn("poi(", guards)
        for literal in re.findall(r"!= 0x([0-9a-f]+)", guards):
            self.assertLessEqual(int(literal, 16), 0xffff)
        for va, expected, _ in CONTRACTS:
            line = guard_line(va, expected)
            self.assertIn(line, self.text)
            self.assertLess(self.text.index(line), first_bp)

    def test_only_new_instruction_addresses(self):
        self.assertEqual(set(self.breakpoints), {0x460AF0, 0x47C029, 0x47C02C, 0x4E9823, 0x460B1A})
        for path in (
            ROOT / "probes/cdb/battle/clash95_battle_hd_lifecycle_extra.cdb",
            ROOT / "probes/cdb/render/clash95_surface_dump_probe.cdb",
        ):
            addresses = {int(x, 16) for x in re.findall(r"(?m)^bp(?:[0-9]+)? ([0-9a-fA-F]{8}) ", path.read_text())}
            self.assertFalse(set(self.breakpoints) & addresses, str(path))

    def test_observation_only_and_no_shared_scratch_writes(self):
        self.assertNotRegex(self.text, r"(?i)(?:^|[;{])\s*(?:r\s|e[bwdq]\s|\.call\b|g(?:h|n)?\s*$|ba\s|bc\s|be\s|bd\s|as\s)")
        self.assertEqual(set(re.findall(r"@\$t\d+", self.text)), {"@$t19"})
        self.assertNotRegex(self.text, r"(?i)@\$t\d+\s*=(?!=)")
        self.assertNotIn("__SURFACE_DUMP_ACTION__", self.text)
        self.assertNotIn("BATTLE_HD_LIFECYCLE_CURSOR_", self.text)

    def test_all_records_include_caller_thread_stack_identity(self):
        for body in self.breakpoints.values():
            for field in ("caller=%p", "tid=%x", "cursor_sp=%p", "eip=%p", "esp=%p"):
                self.assertIn(field, body)
            self.assertIn("(@$t19 == 1)", body)
            self.assertTrue(body.endswith("; gc"))
            self.assertIn(r'\\n', body)
            for caller in CALLERS:
                self.assertIn(f"== {caller:08X}", body)

    def test_exact_device_and_origin_observations(self):
        call = self.breakpoints[0x47C029]
        result = self.breakpoints[0x47C02C]
        origin = self.breakpoints[0x4E9823]
        self.assertIn("(poi(@esp+4) == 0n16)", call)
        self.assertIn("(poi(@esp+8) == (@esp+0x5c))", call)
        self.assertIn("before=(%p,%p,%p,%p)", call)
        self.assertIn("hresult=%p buffer=%p after=(%p,%p,%p,%p)", result)
        self.assertIn("@eax, @esp+0x50", result)
        self.assertIn("success=%p origin=(%d,%d)", origin)
        self.assertIn("@eax, poi(@esp), poi(@esp+4)", origin)

    def test_stack_filters_match_guarded_native_abi(self):
        # Construct the chain independently from the documented x86 pushes:
        # cursor ECX; DD_Pump return, five registers, eight local bytes;
        # updater return and five registers; poller return, three registers,
        # 96 local bytes; then the three stdcall GetDeviceState arguments.
        cursor_sp = 0x200000
        cursor_body = cursor_sp - 4
        pump_return = cursor_body - 4
        pump_body = pump_return - 5 * 4 - 8
        updater_return = pump_body - 4
        updater_body = updater_return - 5 * 4
        poller_return = updater_body - 4
        poller_body = poller_return - 3 * 4 - 96
        call_sp = poller_body - 3 * 4
        buffer = poller_body + 80
        origin_sp = updater_body - 2 * 4
        self.assertEqual(buffer, call_sp + 0x5c)
        observations = (
            (0x47C029, call_sp, ((poller_return, 0x460A61), (updater_return, 0x460611), (pump_return, 0x460B19))),
            (0x47C02C, poller_body, ((poller_return, 0x460A61), (updater_return, 0x460611), (pump_return, 0x460B19))),
            (0x4E9823, origin_sp, ((updater_return, 0x460611), (pump_return, 0x460B19))),
        )
        for address, esp, frames in observations:
            body = self.breakpoints[address]
            for location, expected_return in frames:
                self.assertIn(f"(poi(@esp+0x{location - esp:x}) == {expected_return:08X})", body)
            for caller in CALLERS:
                self.assertIn(f"(poi(@esp+0x{cursor_sp - esp:x}) == {caller:08X})", body)
        self.assertIn("(poi(@esp+0x0) == 0042DA46)", self.breakpoints[0x460AF0])
        self.assertIn("(poi(@esp+0x0) == 0042DA46)", self.breakpoints[0x460B1A])

    def test_no_success_or_manual_acceptance_is_inferred(self):
        self.assertIn("No register or data writes and no new input or forced outcomes", self.text)
        self.assertNotRegex(self.text, r"(?i)DIAG_PASS|approved[=:]|manual_input_proof[=:]1")

    def test_original_source_bytes_when_requested(self):
        if SOURCE_EXE is None:
            self.skipTest("optional verified original executable not supplied")
        raw = SOURCE_EXE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ORIGINAL_SHA)
        for va, expected, owner in CONTRACTS:
            if owner == "original":
                self.assertEqual(read_va(raw, va, len(bytes.fromhex(expected))).hex(), expected, f"{va:08x}")

    def test_candidate_bytes_when_requested(self):
        if CANDIDATE_EXE is None:
            self.skipTest("optional verified validation candidate not supplied")
        raw = CANDIDATE_EXE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), CANDIDATE_SHA)
        for va, expected, _ in CONTRACTS:
            self.assertEqual(read_va(raw, va, len(bytes.fromhex(expected))).hex(), expected, f"{va:08x}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-exe", type=Path)
    parser.add_argument("--candidate-exe", type=Path)
    args, remaining = parser.parse_known_args()
    SOURCE_EXE, CANDIDATE_EXE = args.source_exe, args.candidate_exe
    unittest.main(argv=[__file__, *remaining])
