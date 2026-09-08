"""Pure selection-probe authentication, boundary and debugger-contract fixtures.

No game, debugger, candidate process or output capture is created. The positive
case reconstructs the actual candidate in memory. The small expression oracle
evaluates emitted guards independently, including native warm-up fallback.
"""
from __future__ import annotations

import ast
import operator
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import framed_army_selection_probe as probe

ORIGINAL = Path("C:/Clash/clash95.exe")
SAVE = Path("C:/ClashTests/hd-completion/framed-screens-20260906-034725/workdir/save/0.dat")
CANDIDATE = Path("C:/ClashTests/hd-completion/framed-army-v1-1024x768-build-20260906-085300/clash95_army_1024x768_v1.exe")
CAPTURE = "C:/ClashCaptures/army-selection-pure-fixture"


def expression_value(text, registers, memory):
    """Independent subset of the emitted MASM integer/read-only expressions."""
    text = re.sub(r"\b(?:0x[0-9a-f]+|0n[0-9]+|[0-9a-f]+)\b",
                  lambda m: str(int(m[0][2:], 10) if m[0].startswith("0n") else int(m[0], 16)), text)
    text = text.replace("@$", "").replace("@", "")
    binary = {ast.Add: operator.add, ast.Sub: operator.sub, ast.BitAnd: operator.and_, ast.BitOr: operator.or_}
    compare = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.GtE: operator.ge, ast.LtE: operator.le}

    def evaluate(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return node.value
        if isinstance(node, ast.Name):
            return registers[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in binary:
            return binary[type(node.op)](evaluate(node.left), evaluate(node.right))
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in compare:
            return compare[type(node.ops[0])](evaluate(node.left), evaluate(node.comparators[0]))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and len(node.args) == 1 and not node.keywords:
            # Values model debugger read results, including observed x86
            # poi sign extension; never silently normalize poi to a DWORD.
            value = memory[evaluate(node.args[0])]
            if node.func.id == "poi":
                return value
            bits = {"wo": 16, "by": 8}[node.func.id]
            return value & ((1 << bits) - 1)
        raise AssertionError("unsupported expression fixture: " + ast.dump(node))
    return bool(evaluate(ast.parse(text, mode="eval").body))


def breakpoint_command(compiled, number):
    matches = re.findall(r'^bp' + str(number) + r' ([0-9a-f]{8}) "(.*)"$', compiled, re.M)
    if len(matches) != 1:
        raise AssertionError("missing/duplicate breakpoint " + str(number))
    return int(matches[0][0], 16), matches[0][1]


def guard_expression(command):
    match = re.match(r"^\.if \((.*?)\) \{ ", command)
    if not match:
        raise AssertionError("expected a top-level fail-closed condition")
    return match[1]


class SelectionPathTests(unittest.TestCase):
    def test_paths_are_literal_capture_children(self):
        self.assertEqual(probe.capture_directory(r"C:\ClashCaptures\army-1\pair.raw"),
                         "C:/ClashCaptures/army-1/pair.raw")
        for value in (None, 1, "", "C:/ClashCaptures", "C:/ClashCaptures2/x", "C:/ClashTests/x",
                      "D:/ClashCaptures/x", "C:ClashCaptures/x", "ClashCaptures/x", r"\\host\ClashCaptures\x",
                      "C:/ClashCaptures/../x", "C:/ClashCaptures/./x", "C:/ClashCaptures/x:stream",
                      "C:/ClashCaptures/x;g", 'C:/ClashCaptures/x"g', "C:/ClashCaptures/x\ng", "C:/ClashCaptures/ł"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                probe.capture_directory(value)


@unittest.skipUnless(ORIGINAL.is_file() and SAVE.is_file(), "user-owned original and exact inspected save required")
class SelectionProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, cls.save = ORIGINAL.read_bytes(), SAVE.read_bytes()
        cls.initial_files = (ORIGINAL.read_bytes(), SAVE.read_bytes())
        cls.capture_existed = Path(CAPTURE).exists()
        real_build = probe.builder.build_candidate
        if CANDIDATE.is_file():
            cls.candidate = CANDIDATE.read_bytes()
        else:
            cls.candidate = real_build(cls.original, probe.RESOLUTION, minimap_viewport=True)[0]

        def record_build(*args, **kwargs):
            cls.build_result = real_build(*args, **kwargs)
            return cls.build_result
        with patch.object(probe.builder, "build_candidate", side_effect=record_build):
            cls.packet = probe.build_selection_probe(cls.original, cls.candidate, cls.save,
                                                     capture_dir=CAPTURE, minimap_viewport=True)
        cls.compiled = cls.packet["compiled_probe"]

    def test_full_authentication_determinism_and_no_output(self):
        self.assertEqual(probe.verify_sources(), probe.PINNED_SOURCES)
        with patch.object(probe.builder, "build_candidate", return_value=self.build_result):
            again = probe.build_selection_probe(self.original, self.candidate, self.save,
                                                capture_dir=CAPTURE, minimap_viewport=True)
        self.assertEqual(again, self.packet)
        self.assertEqual(self.packet["candidate_sha256"], probe.sha(self.candidate))
        self.assertEqual(self.packet["probe_sha256"], probe.sha(self.compiled.encode("ascii")))
        self.assertEqual(self.packet["save_sha256"], probe.SAVE_SHA256)
        self.assertEqual(self.packet["initial_extra_sha256"], probe.sha(self.packet["initial_extra"].encode("ascii")))
        self.assertEqual(self.packet["stage"], probe.builder.STAGE)
        for key in ("runtime_executed", "manual_input_proof", "promotion_ready", "native_predicate_forced"):
            self.assertIs(self.packet[key], False)
        self.assertEqual((ORIGINAL.read_bytes(), SAVE.read_bytes()), self.initial_files)
        self.assertEqual(Path(CAPTURE).exists(), self.capture_existed)
        self.assertLess(max(map(len, self.compiled.splitlines())), 4096)
        self.assertFalse(re.search(r"__[A-Z0-9_]+__", self.compiled))

    def test_source_decoded_call_returns_and_loaded_coverage(self):
        returns = self.packet["native_call_returns"]
        self.assertEqual((returns["portraits"], returns["redraw"]), (0x423B32, 0x423B3C))
        entry = self.packet["observer_vas"]["90"]
        for call, target, expected in ((0x423B2D, 0x423420, 0x423B32),
                                       (0x423B37, 0x418700, 0x423B3C),
                                       (returns["native_draw"] - 5, entry, returns["native_draw"]),
                                       (returns["composition_draw"] - 5, entry, returns["composition_draw"])):
            self.assertEqual(probe._call_return(self.candidate, call, target), expected)
            with self.assertRaises(ValueError):
                probe._call_return(self.candidate, call, target + 1)
        for bad_boundary in (0x423B31, 0x423B3B):
            with self.assertRaises(ValueError):
                probe._call_return(self.candidate, bad_boundary, 0x423420)
        checks = {int(va, 16): int(value, 16) for va, value in
                  re.findall(r"\(by\(([0-9a-f]{8})\) != 0x([0-9a-f]{2})\)", self.compiled)}
        # Every byte of each native observation scope is checked before arming
        # breakpoints, including complete CALL operands and fall-through PCs.
        for va, size in ((0x408030, 269), (0x406980, 675), (0x40A500, 247),
                         (0x423B00, 63), (0x423420, 825), (0x406FA0, 6)):
            for offset, value in enumerate(probe._read(self.candidate, va, size)):
                self.assertEqual(checks[va + offset], value)
        self.assertLess(self.compiled.index("SHSEL_BYTES_PASS"), self.compiled.index("bp80 "))

    def state(self):
        registers = dict(tid=123, t2=123, t1=0x600000, t0=7, t3=0x800000,
                         t4=1, t5=1, t6=0, t7=0, t8=0x7FF000, t9=0, esp=0x7FF004, eax=1)
        memory = {0x5202E4: 0x600000, 0x511B58: 3, 0x514194: 3, 0x526994: 1,
                  0x5202E0: 0x900000, 0x900000: 1024, 0x900002: 768, 0x900004: 0xA00000}
        return registers, memory

    def test_native_fallback_is_recorded_but_composition_must_succeed(self):
        regs, memory = self.state()
        for number, accepted in ((91, {0, 1}), (92, {1})):
            va, command = breakpoint_command(self.compiled, number)
            condition = guard_expression(command)
            regs["t9"] = va
            for status in (0, 1, 2, 0xFFFFFFFF):
                regs["eax"] = status
                self.assertEqual(expression_value(condition, regs, memory), status in accepted)
            regs["eax"] = 1
            for field, invalid in (("tid", 124), ("t9", va + 1), ("esp", regs["t8"]), ("t5", 2)):
                bad = dict(regs, **{field: invalid})
                self.assertFalse(expression_value(condition, bad, memory), field)
            self.assertIn("SHSEL_DRAW_RETURN route=" + ("native" if number == 91 else "composition"), command)
            self.assertIn("status=%d", command)
        self.assertIn("font7_cache=%p", breakpoint_command(self.compiled, 90)[1])
        after = guard_expression(breakpoint_command(self.compiled, 89)[1])
        regs.update(t0=8, t5=2, t6=2, t7=1, t4=0)
        self.assertTrue(expression_value(after, regs, memory))
        regs["t7"] = 0
        self.assertFalse(expression_value(after, regs, memory))
        regs.update(t7=1, t6=1)
        self.assertFalse(expression_value(after, regs, memory))

    def test_handoff_diagnostics_report_each_unchanged_predicate(self):
        registers = dict(eip=0x406FA0, t14=1, t13=4, t1=0x600000)
        memory = {0x5199D8: 0x40AD40, 0x526994: 0, 0x526990: 0,
                  0x5202EC: 0, 0x511B58: 0xFFFFFFFF, 0x514194: 0xFFFFFFFF,
                  0x6222E0: 100, 0x6222E4: 100, 0x6222EC: 17,
                  0x624765: 0x00130010, 0x624769: 0}
        for marker, changes in (
            ("SHSEL_HANDOFF_CHECKS", (("eip", 0), ("t14", 0), ("t13", 3),
                                      (0x5199D8, 0), (0x526994, 1), (0x526990, 1),
                                      (0x5202EC, 1), (0x511B58, 3), (0x514194, 3))),
            ("SHSEL_WORLD_CHECKS", ((0x6222E0, 99), (0x6222E4, 99), (0x6222EC, 0),
                                    (0x624765, 0), (0x624769, 1)))):
            text = re.search(marker + r" [^;]+;", self.compiled)[0]
            args = text.split(", ", 1)[1][:-1].split(", ")
            self.assertEqual(len(args), len(changes))
            # Exactly the same predicates remain in the subsequent guard;
            # diagnostic values cannot bypass admission or stand in for it.
            self.assertIn(".if (" + " & ".join(args) + ") {", self.compiled)
            self.assertEqual([expression_value(expr, registers, memory) for expr in args], [True] * len(args))
            for index, (key, value) in enumerate(changes):
                r, m = dict(registers), dict(memory)
                (r if isinstance(key, str) else m)[key] = value
                self.assertEqual([expression_value(expr, r, m) for expr in args],
                                 [j != index for j in range(len(args))])
        positions = [self.compiled.index(marker) for marker in
                     ("PTILE_TRACE_CLOSED", "SHSEL_HANDOFF eip", "SHSEL_HANDOFF_CHECKS", "SHSEL_WORLD_CHECKS", "SHSEL_BEGIN")]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("selected=(%I64x,%d) prior=(%I64x,%d)", self.compiled)

    def test_ordered_native_selection_and_stop_only_capture(self):
        self.assertEqual(set(self.packet["observer_vas"]), {str(i) for i in range(80, 93)})
        for number in range(80, 93):
            va, command = breakpoint_command(self.compiled, number)
            self.assertEqual(va, self.packet["observer_vas"][str(number)])
            self.assertIn("\nbd " + str(number) + "\n", self.compiled)
            self.assertIn("be " + str(number), self.compiled)
            self.assertIn("SHSEL_REJECT", command)
        ready = breakpoint_command(self.compiled, 80)[1]
        self.assertIn("SHSEL_HOST_READY", ready)
        self.assertNotRegex(ready, r"(?:^|;\s*)(?:g|gc|gh|gn)\b")
        regs, memory = self.state()
        regs.update(t0=9, esp=regs["t3"], t5=2, t6=2, t7=1)
        self.assertTrue(expression_value(guard_expression(ready), regs, memory))
        for field, invalid in (("t0", 8), ("esp", regs["t3"] - 4), ("t6", 1), ("t7", 0)):
            self.assertFalse(expression_value(guard_expression(ready), dict(regs, **{field: invalid}), memory))
        success = guard_expression(breakpoint_command(self.compiled, 81)[1])
        regs.update(t0=2, eax=1, esp=regs["t3"] - 24)
        self.assertTrue(expression_value(success, regs, memory))
        regs["eax"] = 0  # Same native RET path can be predicate rejection.
        self.assertFalse(expression_value(success, regs, memory))
        self.assertIn("@ecx == 0n38", breakpoint_command(self.compiled, 87)[1])
        self.assertIn("@esi == 0n16", breakpoint_command(self.compiled, 87)[1])
        self.assertIn("r esp=@esp-4; ed @esp 00406fa1; r esp=@esp-4; ed @esp 00406980; r eip=00408030", self.compiled)
        for number, name in ((88, "before-redraw"), (89, "after-redraw")):
            self.assertIn(f".writemem {CAPTURE}/{name}.raw poi(poi(005202e0)+4) L0n786432", breakpoint_command(self.compiled, number)[1])
        # Disclosure is mandatory and neither native EAX nor selection/squads
        # are forced anywhere in the new diagnostic observer commands.
        observer_text = "\n".join(breakpoint_command(self.compiled, i)[1] for i in range(80, 93))
        self.assertNotRegex(observer_text, r"\br (?:eax|@eax)=|\b(?:ed|eb|ew) 00511b58")
        self.assertIn("SHSEL_CONTROLLED scroll=(10,17) screen=(448,176)", self.compiled)

    def test_empty_selection_identity_is_low_dword_for_both_cdb_read_forms(self):
        checks = re.search(r"SHSEL_HANDOFF_CHECKS [^;]+;", self.compiled)[0]
        args = checks.split(", ", 1)[1][:-1].split(", ")
        regs, memory = self.state()
        regs.update(t0=1, esi=16, ecx=38, edx=3)
        memory[0x5202EC] = 0
        occupancy = guard_expression(breakpoint_command(self.compiled, 87)[1])
        for value in (0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF, 0, 3, 0xFFFFFFFE, 0xFFFFFFFFFFFFFFFE, 0x7FFFFFFF):
            memory[0x511B58] = memory[0x514194] = value
            expected = value in (0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF)
            self.assertEqual(expression_value(args[-2], regs, memory), expected)
            self.assertEqual(expression_value(args[-1], regs, memory), expected)
            self.assertEqual(expression_value(occupancy, regs, memory), expected)
        # Preserve the diagnosed failure: a direct comparison fails for the
        # actual sign-extended read, despite the stored DWORD being -1.
        memory[0x511B58] = 0xFFFFFFFFFFFFFFFF
        self.assertFalse(expression_value("poi(00511b58) == ffffffff", regs, memory))

    def test_unknown_sources_original_save_candidate_and_variant_fail_closed(self):
        with patch.dict(probe.PINNED_SOURCES, {"tools/build_framed_army_candidate.py": "0" * 64}):
            with self.assertRaisesRegex(ValueError, "source differs"):
                probe.verify_sources()
        options = dict(capture_dir=CAPTURE, minimap_viewport=True)
        for original, candidate, save, changes in (
            (bytearray(self.original), self.candidate, self.save, {}),
            (self.original[:-1] + bytes([self.original[-1] ^ 1]), self.candidate, self.save, {}),
            (self.original, self.candidate, self.save[:-1] + bytes([self.save[-1] ^ 1]), {}),
            (self.original, self.candidate, self.save, {"minimap_viewport": 1}),
            (self.original, self.candidate[:-1] + bytes([self.candidate[-1] ^ 1]), self.save, {})):
            with self.subTest(changes=changes), patch.object(probe.builder, "build_candidate", return_value=self.build_result):
                with self.assertRaises(ValueError):
                    probe.build_selection_probe(original, candidate, save, **(options | changes))
        # Variant mismatch must compare a whole independently reconstructed
        # image, not accept a caller's metadata/hash assertion.
        wrong_variant = bytes([self.candidate[0] ^ 1]) + self.candidate[1:]
        with patch.object(probe.builder, "build_candidate", return_value=(wrong_variant, {}, "")):
            with self.assertRaisesRegex(ValueError, "whole army candidate"):
                probe.build_selection_probe(self.original, self.candidate, self.save, **options)


if __name__ == "__main__":
    unittest.main()
