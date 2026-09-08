"""Offline transition-probe authentication and adversarial guard fixtures.

The only real executable use is reading and reconstructing its bytes in memory.
No candidate process, debugger, input, window or capture is created.
"""
import ast
import json
import operator
from pathlib import Path
import re
import unittest
from unittest.mock import patch

import framed_army_transition_probe as probe

ORIGINAL = Path("C:/Clash/clash95.exe")
CANDIDATE = Path("C:/ClashTests/hd-completion/framed-army-v1-1024x768-build-20260906-085300/clash95_army_1024x768_v1.exe")
SAVE = Path("C:/ClashTests/hd-completion/framed-screens-20260906-034725/workdir/save/0.dat")
CAPTURE = "C:/ClashCaptures/army-transition-offline-fixture"


def expression(text, registers, memory):
    """Independent integer oracle; memory may expose sign-extended DWORDs."""
    text = re.sub(r"\b(?:0x[0-9a-f]+|0n[0-9]+|[0-9a-f]+)\b",
        lambda m: str(int(m[0][2:], 10) if m[0].startswith("0n") else int(m[0], 16)), text)
    text = text.replace("@$", "").replace("@", "")
    binary = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
              ast.BitAnd: operator.and_, ast.BitOr: operator.or_}
    compare = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.GtE: operator.ge,
               ast.LtE: operator.le, ast.Gt: operator.gt, ast.Lt: operator.lt}
    def run(n):
        if isinstance(n, ast.Constant) and type(n.value) is int: return n.value
        if isinstance(n, ast.Name): return registers[n.id]
        if isinstance(n, ast.BinOp) and type(n.op) in binary: return binary[type(n.op)](run(n.left), run(n.right))
        if isinstance(n, ast.Compare) and len(n.ops) == 1 and type(n.ops[0]) in compare:
            return compare[type(n.ops[0])](run(n.left), run(n.comparators[0]))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and len(n.args) == 1:
            value = memory[run(n.args[0])]
            if n.func.id == "poi": return value
            return value & ((1 << {"wo": 16, "by": 8}[n.func.id]) - 1)
        raise AssertionError("unhandled oracle expression " + ast.dump(n))
    return bool(run(ast.parse(text, mode="eval").body))


def command(packet, number):
    rows = re.findall(r'^bp' + str(number) + r' ([0-9a-f]{8}) "(.*)"$', packet["compiled_probe"], re.M)
    if len(rows) != 1: raise AssertionError("one exact observer required")
    return int(rows[0][0], 16), rows[0][1]


def condition(packet, number):
    return re.match(r"^\.if \((.*?)\) \{ ", command(packet, number)[1])[1]


@unittest.skipUnless(ORIGINAL.is_file() and CANDIDATE.is_file() and SAVE.is_file(), "exact user-owned inputs required")
class TransitionProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, cls.candidate, cls.save = ORIGINAL.read_bytes(), CANDIDATE.read_bytes(), SAVE.read_bytes()
        cls.existed = Path(CAPTURE).exists()
        real = probe.base.build_selection_probe
        def recorded(*args, **kwargs):
            cls.base_packet = real(*args, **kwargs)
            return cls.base_packet
        with patch.object(probe.base, "build_selection_probe", side_effect=recorded):
            cls.packet = probe.build_transition_probe(cls.original, cls.candidate, cls.save,
                capture_dir=CAPTURE, minimap_viewport=True)

    def test_exact_source_candidate_and_save_reconstruction_without_writes(self):
        self.assertEqual(probe.verify_sources()["tools/framed_army_selection_probe.py"], probe.BASE_SHA256)
        self.assertEqual(self.packet["candidate_sha256"], probe.sha(self.candidate))
        self.assertEqual(self.packet["probe_sha256"], probe.sha(self.packet["compiled_probe"].encode("ascii")))
        self.assertEqual([s["unit"] for s in self.packet["steps"]], [3, 1, 2, 0, 3, -1])
        self.assertEqual([len(s["types"]) for s in self.packet["steps"]], [8, 4, 2, 1, 8, 0])
        for key in ("runtime_executed", "manual_input_proof", "promotion_ready", "native_predicate_forced", "selected_value_forced"):
            self.assertIs(self.packet[key], False)
        self.assertEqual((ORIGINAL.read_bytes(), CANDIDATE.read_bytes(), SAVE.read_bytes()),
                         (self.original, self.candidate, self.save))
        self.assertEqual(Path(CAPTURE).exists(), self.existed)
        bad = bytearray(self.candidate); bad[-1] ^= 1
        with self.assertRaisesRegex(ValueError, "whole army candidate reconstruction"):
            probe.build_transition_probe(self.original, bytes(bad), self.save, capture_dir=CAPTURE)
        with patch.object(probe, "BASE_SHA256", "0" * 64), self.assertRaisesRegex(ValueError, "frozen selection"):
            probe.build_transition_probe(self.original, self.candidate, self.save, capture_dir=CAPTURE)

    def test_exact_loaded_boundaries_and_native_tail_return(self):
        checks = {int(va, 16): int(value, 16) for va, value in re.findall(
            r"\(by\(([0-9a-f]{8})\) != 0x([0-9a-f]{2})\)", self.packet["compiled_probe"])}
        for va, size in probe.NATIVE_SPANS:
            for offset, value in enumerate(probe.base._read(self.candidate, va, size)):
                self.assertEqual(checks[va + offset], value)
        self.assertEqual(self.packet["map_return_vas"], dict(open=0x423B3C, switch=0x40A5EA, close=0x423B64, deselect=0x409DC8))
        self.assertEqual(probe.base._call_return(self.candidate, 0x40A5E5, 0x423B90), 0x40A5EA)
        self.assertEqual(probe.base._read(self.candidate, 0x423BA9, 5), bytes.fromhex("e9524bffff"))
        self.assertEqual(set(self.packet["observer_vas"]), {str(n) for n in range(100, 120)})
        for n in range(100, 120):
            self.assertEqual(command(self.packet, n)[0], self.packet["observer_vas"][str(n)])

    def test_supplemental_files_are_exact_bounded_source_quiet_commands(self):
        files = self.packet["supplemental_commands"]
        self.assertEqual(set(files), {CAPTURE + f"/transition-{n}.cdb" for n in range(1, 7)})
        combined = self.packet["compiled_probe"] + "\n" + "\n".join(files.values())
        self.assertLess(max(map(len, combined.splitlines())), 4096)
        self.assertEqual(combined.count("ATX_HOST_READY"), 1)
        self.assertNotRegex(combined, r"__[A-Z_]+__")
        for n, (path, text) in enumerate(files.items(), 1):
            self.assertEqual(self.packet["supplemental_sha256"][path], probe.sha(text.encode("ascii")))
            self.assertIn(f"/step-{n}.raw", text)
            self.assertIn(f"/step-{n}.header.raw", text)
            self.assertNotIn(r'\"', text)
            self.assertNotIn(r'\\n', text)
            self.assertIn(r'\n"', text)
            self.assertIn('$$>a<\\"' + path + '\\"', command(self.packet, 100)[1])
        final = files[CAPTURE + "/transition-6.cdb"]
        self.assertNotRegex(final, r"(?:^|;\s*)(?:g|gc|gh|gn)\b")
        # The separately authenticated frozen startup controls menu entry.
        # Audit only the new transition commands for result-forcing writes;
        # those menu controls are not army click predicates.
        transition_commands = "\n".join(line for line in self.packet["compiled_probe"].splitlines() if "ATX_" in line)
        transition_commands += "\n" + "\n".join(files.values())
        writes = re.findall(r"\b(?:ed|eb|ew)\s+([^ ;]+)", transition_commands)
        self.assertTrue(writes)
        self.assertLessEqual(set(writes), {"00544cfc", "00544d00", "005451c0", "00544d04", "@$t1+222e8", "@esp"})
        self.assertNotRegex(transition_commands, r"\br eax=1\b")

    def state(self, step):
        s = self.packet["steps"][step - 1]
        registers = {"tid": 123, "t2": 123, "t1": 0x600000, "t3": 0x800000, "esp": 0x800000,
            "t0": step, "t4": 10 if step == 6 else 8, "t5": 2 if s["lower"] else 0,
            "t6": 2 if s["lower"] else 0, "t7": 1 if s["lower"] else 0,
            "t10": s["unit"] & 0xffffffff, "t11": s["old"] & 0xffffffff,
            "t18": s["lower"], "t19": s["prior"] & 0xffffffff,
            "t16": 2 if step == 6 else 1, "t17": 2 if step == 6 else 1}
        memory = {0x5202E4: 0x600000, 0x5199D8: 0x40AD40, 0x5202EC: 0, 0x5202E0: 0x900000,
            0x900000: 1024, 0x900002: 768, 0x9000B8: 0x50EE24,
            0x511B58: s["unit"] & 0xffffffff, 0x514194: s["unit"] if s["lower"] else 0xffffffff,
            0x526994: s["lower"]}
        return registers, memory

    def test_all_six_snapshot_guards_require_complete_state_and_calls(self):
        guard = condition(self.packet, 100)
        for step in range(1, 7):
            r, m = self.state(step)
            self.assertTrue(expression(guard, r, m), step)
            for name, wrong in (("tid", 124), ("esp", r["esp"] - 4), ("t4", 5),
                                ("t6", r["t6"] + 1), ("t16", 0), ("t17", 0)):
                self.assertFalse(expression(guard, dict(r, **{name: wrong}), m), (step, name))
            for address, wrong in ((0x5199D8, 0), (0x5202EC, 1), (0x900002, 480),
                                   (0x9000B8, 0x50EEC4), (0x511B58, 99), (0x514194, 99), (0x526994, 2)):
                self.assertFalse(expression(guard, r, dict(m, **{}) | {address: wrong}), (step, address))
            if r["t18"]:
                self.assertFalse(expression(guard, dict(r, t7=0), m))
            else:
                self.assertFalse(expression(guard, dict(r, t5=1, t6=1), m))

    def test_sign_extended_sentinels_and_actual_selection_result(self):
        r, m = self.state(6)
        for expected in (0xffffffff, 0xffffffffffffffff):
            for actual in (0xffffffff, 0xffffffffffffffff):
                self.assertTrue(expression(condition(self.packet, 100), dict(r, t10=expected),
                    m | {0x511B58: actual, 0x514194: actual}))
        r, m = self.state(1)
        r.update(t4=2, eax=1, esp=r["t3"] - 24)
        self.assertTrue(expression(condition(self.packet, 102), r, m))
        for value in (0, 2, 0xffffffff):
            self.assertFalse(expression(condition(self.packet, 102), dict(r, eax=value), m))
        self.assertIn("& 0x00000000ffffffff", command(self.packet, 118)[1])
        self.assertNotIn("& 0xffffffff", self.packet["compiled_probe"])

    def test_wrong_route_return_or_overlapping_draw_rejects(self):
        for n, step, phase in ((113, 1, 7), (114, 2, 7), (115, 4, 7), (116, 6, 9)):
            r, m = self.state(step)
            va = command(self.packet, n)[0]
            r.update(t4=phase, t14=r["t3"]-40, esp=r["t3"]-36, t15=va, t16=1, t17=0)
            self.assertTrue(expression(condition(self.packet, n), r, m))
            self.assertFalse(expression(condition(self.packet, n), dict(r, t15=va+1), m))
            self.assertFalse(expression(condition(self.packet, n), dict(r, esp=r["esp"]+4), m))
        r, m = self.state(2)
        va = command(self.packet, 111)[0]
        r.update(t4=7, t9=va, t8=r["t3"]-40, esp=r["t3"]-36, t5=2, t6=1, eax=1)
        self.assertTrue(expression(condition(self.packet, 111), r, m))
        self.assertFalse(expression(condition(self.packet, 111), dict(r, eax=0), m))
        self.assertFalse(expression(condition(self.packet, 111), dict(r, t6=2), m))


if __name__ == "__main__":
    unittest.main()
