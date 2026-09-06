#!/usr/bin/env python3
"""Offline source/command/stack fixtures; no debugger, candidate file or runtime."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import copy
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

import framed_noop_progress_probe as diagnostic
import test_initial_map_paint_trace as trace_fixture
from partial_tile_trace_probe import validate_event_integrity

ORIGINAL = Path("C:/Clash/clash95.exe")
RESOLUTIONS = ("800x600", "1024x768", "1280x720", "1280x960", "1920x1080", "802x602")


def rendered(extra: str) -> str:
    # Synthetic complete command file: no execution and no real startup route.
    return 'bc *\nbp 00401234 ".echo SYNTHETIC_UNUSED; gc"\n' + extra + '\ng\n'


class InventoryTests(unittest.TestCase):
    def test_implicit_explicit_ids_and_unchanged_input(self):
        text = ('bc *\nbp 00401234 "gc"\nbp2 00402234 "gc"\n'
                'bp 00403234 "gc"\nbp 70 00404234 "be 71; gc"\n'
                'bp71 00405234 "bd 71; gc"\ng\n')
        before = text.encode("ascii")
        report = diagnostic.inspect_breakpoints(text)
        self.assertEqual(report["occupied_ids"], [0, 1, 2, 70, 71])
        self.assertEqual(report["breakpoint_id"], 80)
        self.assertEqual(text.encode("ascii"), before)
        self.assertEqual(report["rendered_probe_sha256"], diagnostic.sha(before))

    def test_collision_site_control_and_implicit_allocation(self):
        for added in ('bp80 00401111 "gc"', 'bp 80 00401111 "gc"',
                      'bp81 00418afd "gc"', 'bp81 00418b02 "gc"', 'be 80', 'bd 80',
                      'bp2 00402345 "be 80; gc"', 'bp2 00402345 "bd *; gc"',
                      'bp2 00402345 "bc 1; gc"', 'bp2 00402345 "bp80 00402020; gc"'):
            with self.subTest(added=added), self.assertRaises(ValueError):
                diagnostic.inspect_breakpoints('bc *\nbp 00401234 "gc"\n' + added + '\ng\n')
        implicit = 'bc *\n' + ''.join(f'bp {0x410000 + index:08x} "gc"\n' for index in range(81)) + 'g\n'
        with self.assertRaisesRegex(ValueError, "occupied"):
            diagnostic.inspect_breakpoints(implicit)
        self.assertEqual(diagnostic.inspect_breakpoints(implicit, breakpoint_id=81)["breakpoint_id"], 81)

    def test_unknown_duplicate_dynamic_and_incomplete_fail(self):
        valid = 'bc *\nbp70 00401234 "gc"\ng\n'
        variants = [valid.replace('bc *\n', ''), valid + 'gc\n', valid.replace('g\n', ''),
                    valid.replace('bp70', 'bu70'), valid.replace('bp70 00401234', 'bp70 module!name'),
                    valid.replace('\ng\n', '\nbp71 00401234 "gc"\ng\n'),
                    valid.replace('\ng\n', '\nbp70 00405678 "gc"\ng\n'),
                    valid.replace('\ng\n', '\nbc *\ng\n'),
                    valid.replace('\ng\n', '\n$$><other.cdb\ng\n'),
                    valid.replace('\ng\n', '\n.scriptload other.js\ng\n'),
                    valid.replace('\ng\n', '\ng\ng\n'), valid + '\x00',
                    valid.replace('gc', diagnostic.MARKER + '; gc')]
        for index, text in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(ValueError):
                diagnostic.inspect_breakpoints(text)
        for bp in (True, 79, 100, "80", 80.0):
            with self.subTest(bp=bp), self.assertRaises(ValueError):
                diagnostic.inspect_breakpoints(valid, breakpoint_id=bp)

    def test_independent_native_stack_and_caller_oracle(self):
        # Execute only the authenticated PUSH/SUB/ADD/POP/RET arithmetic in
        # Python, with independent literal opcodes and a synthetic stack.
        caller, entry_sp = 0x4166FA, 0xEDC98
        regs = {"ebx": 11, "ecx": 22, "esi": 33, "edi": 44, "ebp": 55}
        memory, sp = {entry_sp: caller}, entry_sp
        native = bytes.fromhex("535156575583ec08")
        self.assertEqual(diagnostic.PROLOGUE, native)
        push_names = {0x53: "ebx", 0x51: "ecx", 0x56: "esi", 0x57: "edi", 0x55: "ebp"}
        for opcode in native[:5]:
            sp -= 4; memory[sp] = regs[push_names[opcode]]
        sp -= native[-1]
        self.assertEqual(sp, entry_sp - 28)
        self.assertEqual(memory[sp + 28], caller)
        epilogue = bytes.fromhex("83c4085d5f5e595bc3")
        self.assertEqual(diagnostic.EPILOGUE, epilogue)
        self.assertEqual(diagnostic.PRE_ADD_VA + 3, diagnostic.POST_ADD_VA)
        sp += epilogue[2]
        self.assertEqual(sp, entry_sp - 20)
        self.assertEqual(memory[sp + 20], caller)
        # The former+28 slot is wrong after ADD; it is not a saved caller.
        self.assertNotIn(sp + 28, memory)
        restored = {}
        for opcode, name in zip(epilogue[3:8], ("ebp", "edi", "esi", "ecx", "ebx")):
            self.assertEqual(opcode, {"ebp": 0x5D, "edi": 0x5F, "esi": 0x5E, "ecx": 0x59, "ebx": 0x5B}[name])
            restored[name] = memory[sp]; sp += 4
        self.assertEqual(restored, regs)
        self.assertEqual(memory[sp], caller)
        sp += 4
        self.assertEqual(sp, entry_sp + 4)

    def test_extra_diagnostics_do_not_change_or_deduplicate_strict_trace(self):
        for repeated in (False, True):
            events = trace_fixture.initial_events(framed=True) + trace_fixture.auxiliary(noop=True)
            if repeated:
                events.append(copy.deepcopy(events[-1]))
            log, extra = trace_fixture.fixture(events, stage=diagnostic.STAGE)
            original = validate_event_integrity(log, extra, reset_bp=76)
            marker = (diagnostic.MARKER + " tid=abc eip=00418afd esp=001fffec "
                      "world=(20,20) caller=0040ad80 entry_esp=00200000 trace_seq=8")
            # Retain startup observations and every original line, inserting
            # one diagnostic after each native early-exit record.
            expanded = [marker]
            for line in log.splitlines():
                expanded.append(line)
                if line.startswith("PTILE_NATIVE_NOOP_EXIT "):
                    expanded.append(marker)
            diagnostic_log = "\n".join(expanded) + "\n"
            checked = validate_event_integrity(diagnostic_log, extra, reset_bp=76)
            self.assertEqual(checked["passed"], original["passed"])
            self.assertEqual([row["text"] for row in checked["raw_records"]],
                             [row["text"] for row in original["raw_records"]])
            report = trace_fixture.evaluate(diagnostic_log, extra, stage=diagnostic.STAGE)
            self.assertEqual(report["passed"], not repeated, report["failures"])
            if repeated:
                self.assertTrue(any("fresh matching guard" in failure for failure in report["failures"]))
                self.assertEqual(sum(row["marker"] == "PTILE_NATIVE_NOOP_EXIT" for row in checked["raw_records"]), 2)


@unittest.skipUnless(ORIGINAL.is_file(), "requires user-owned original for in-memory verification")
class BoundDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()
        cls.candidates = {size: diagnostic.builder.build_candidate(cls.original, size) for size in RESOLUTIONS}

    def prepare(self, size="800x600", **overrides):
        candidate, _, extra = self.candidates[size]
        args = dict(original=self.original, candidate=candidate, candidate_sha256=diagnostic.sha(candidate),
                    stage=diagnostic.STAGE, resolution=size, rendered_probe=rendered(extra))
        args.update(overrides)
        return diagnostic.build_diagnostic(**args)

    def test_six_resolutions_exact_bytes_readonly_printf_and_binding(self):
        for size in RESOLUTIONS:
            with self.subTest(size=size):
                result = self.prepare(size)
                candidate, _, extra = self.candidates[size]
                snippet = result["snippet"]
                self.assertTrue(result["prepared"])
                self.assertFalse(result["acceptance"] or result["promotion_ready"] or result["manual_input_proof"])
                self.assertEqual(result["candidate_sha256"], diagnostic.sha(candidate))
                self.assertNotIn("PTILE_", snippet.upper())
                self.assertNotIn("r @$", snippet)
                self.assertNotRegex(snippet, r"(?:^|[;{}])\s*(?:eb|ew|ed|eq|eip|esp|r|be|bd|bc)\b")
                line = next(row for row in snippet.splitlines() if row.startswith("bp"))
                self.assertEqual(line, 'bp80 00418afd ".printf \\"FRAMED_NOOP_POST_ADD tid=%x eip=%p esp=%p '
                                 'world=(%d,%d) caller=%p entry_esp=%p trace_seq=%u\\\\n\\", '
                                 '@$tid, @eip, @esp, @eax, @edx, poi(@esp+0n20), @esp+0n20, @$t9; gc"')
                # No condition or debugger counter hides any post-ADD hit.
                self.assertNotIn(".if", line)
                reads = [(int(va, 16), int(value, 16)) for va, value in re.findall(
                    r"by\(([0-9a-f]{8})\) != ([0-9a-f]{2})", snippet)]
                expected = {va: value for span in result["byte_spans"]
                            for va, value in enumerate(bytes.fromhex(span["bytes"]), int(span["va"], 16))}
                self.assertEqual(set(expected), set(range(0x418A90, 0x418B03)))
                omitted = result["already_declared_breakpoint_bytes"]
                self.assertEqual([(row["va"], row["expected_byte"]) for row in omitted], [("00418afa", "83")])
                del expected[0x418AFA]
                self.assertEqual(dict(reads), expected)
                self.assertEqual(len(reads), len(expected))
                self.assertTrue(set(range(0x418AFD, 0x418B03)) <= set(expected))
                for va, value in reads:
                    self.assertEqual(diagnostic._span(candidate, va, 1)[1], bytes([value]))
                self.assertEqual(result["observation"]["post_add_stack_to_entry"], 20)
                self.assertEqual(result["inventory"]["rendered_probe_sha256"], diagnostic.sha(rendered(extra).encode("ascii")))
                self.assertTrue(all(len(row) < 4096 for row in snippet.splitlines()))

    def test_wrong_sha_original_candidate_resolution_stage_and_probe_reject(self):
        candidate, _, extra = self.candidates["800x600"]
        changed = bytearray(candidate)
        changed[diagnostic._span(candidate, diagnostic.POST_ADD_VA, 1)[0]] ^= 1
        variants = [dict(candidate_sha256="0" * 64), dict(candidate_sha256="abc"),
                    dict(original=self.original[:-1]), dict(candidate=self.original, candidate_sha256=diagnostic.sha(self.original)),
                    dict(candidate=bytes(changed), candidate_sha256=diagnostic.sha(changed)),
                    dict(resolution="1024x768"), dict(resolution="0800x600"),
                    dict(stage=trace_fixture.trace.STAGE), dict(stage=diagnostic.STAGE + "-other"),
                    dict(rendered_probe=rendered(extra.replace("bp74 00418afa", "bp74 00418afb"))),
                    dict(rendered_probe=rendered(extra + extra)),
                    dict(rendered_probe=rendered(extra) + 'bp80 00401111 "gc"\n')]
        for index, changes in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.prepare(**changes)
        with patch.dict(diagnostic.builder.PINNED_SOURCES, {"tools/partial_tile_trace_probe.py": "0" * 64}):
            with self.assertRaisesRegex(ValueError, "source changed"):
                self.prepare()

    def test_crlf_input_is_bound_without_rewriting_and_alternate_free_id(self):
        extra = self.candidates["800x600"][2]
        probe = rendered(extra).replace("\n", "\r\n")
        result = self.prepare(rendered_probe=probe, breakpoint_id=81)
        self.assertEqual(result["inventory"]["rendered_probe_sha256"], diagnostic.sha(probe.encode("ascii")))
        self.assertIn('bp81 00418afd "', result["snippet"])

    def test_saved_failed_run_complete_probe_inventory_when_available(self):
        path = Path("C:/ClashCaptures/hd-completion/framed-v1-800x600-20260906-023304/"
                    "cdb-surface-dump-20260906-043323/clash95_surface_dump_probe.generated.cdb")
        if not path.is_file():
            self.skipTest("optional archived generated probe is unavailable")
        before = path.read_bytes()
        result = self.prepare(rendered_probe=before.decode("ascii"))
        self.assertEqual(path.read_bytes(), before)
        self.assertNotIn(80, result["inventory"]["occupied_ids"])
        self.assertEqual(result["candidate_sha256"], "7fad16f167205fb34ecbc99a6a1ff6180c710807f99b19f25efb48a8b1c8d15b")


class CliTests(unittest.TestCase):
    def test_stdout_only_synthetic_cli_and_missing_file(self):
        with tempfile.TemporaryDirectory(prefix="framed-noop-fixture-") as directory:
            root = Path(directory)
            original, candidate, probe = (root / name for name in ("original.synthetic", "candidate.synthetic", "probe.cdb"))
            original.write_bytes(b"SYNTHETIC ORIGINAL")
            candidate.write_bytes(b"SYNTHETIC CANDIDATE")
            probe.write_text("SYNTHETIC PROBE", encoding="ascii")
            before = {path.name: path.read_bytes() for path in root.iterdir()}
            argv = ["probe", "--original", str(original), "--candidate", str(candidate),
                    "--candidate-sha256", "a" * 64, "--stage", diagnostic.STAGE,
                    "--resolution", "800x600", "--rendered-probe", str(probe)]
            for as_json in (False, True):
                output = io.StringIO()
                with patch.object(sys, "argv", argv + (["--json"] if as_json else [])), \
                        patch.object(diagnostic, "build_diagnostic", return_value={"prepared": True, "snippet": "SYNTHETIC\n"}) as build, \
                        redirect_stdout(output):
                    self.assertEqual(diagnostic.main(), 0)
                self.assertEqual(build.call_args.args, (b"SYNTHETIC ORIGINAL", b"SYNTHETIC CANDIDATE"))
                self.assertEqual(json.loads(output.getvalue())["snippet"] if as_json else output.getvalue(), "SYNTHETIC\n")
                self.assertEqual(before, {path.name: path.read_bytes() for path in root.iterdir()})
            missing = argv.copy(); missing[missing.index(str(probe))] = str(root / "missing.cdb")
            output, error = io.StringIO(), io.StringIO()
            with patch.object(sys, "argv", missing), redirect_stdout(output), redirect_stderr(error):
                self.assertEqual(diagnostic.main(), 1)
            self.assertEqual(output.getvalue(), "")
            self.assertIn("diagnostic preparation failed", error.getvalue())
            self.assertEqual(before, {path.name: path.read_bytes() for path in root.iterdir()})


if __name__ == "__main__":
    unittest.main()
