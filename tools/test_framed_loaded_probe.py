from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import copy
import io
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import framed_loaded_probe as probe
import build_framed_bounded_input_candidate as cli
import test_framed_bounded_input as fixture
from src.patcher import framed_bounded_input as bounded
from test_pe_extension import independent_image


def candidate(resolution="1280x720"):
    _, parent, metadata = fixture.synthetic_parent(resolution)
    image, report = bounded._upgrade_verified_parent(parent, metadata, resolution)
    report["original_sha256"] = probe.pe.ORIGINAL_SHA256
    report["source_sha256"] = probe.source_identities()
    parsed = probe.pe.inspect_pe(image)
    offset = parsed.file_offset(0x1040, 7)
    report["parent_build"]["hooks"] = [{"offset": offset, "rva": 0x1040, "va": parsed.image_base + 0x1040,
                                          "new_hex": image[offset:offset + 7].hex()}]
    scalar = [SimpleNamespace(offset=parsed.file_offset(0x1051, 11), new=b"\x55" * 11),
              SimpleNamespace(offset=offset, new=b"\x99" * 5)]
    return image, report, scalar


def render(image, report, scalar):
    with patch.object(probe.recipe, "select_patches_for", return_value=scalar):
        return probe.render_probe(image, report)


def mapped(image, loaded_base):
    memory, _, fields, _ = independent_image(image)
    preferred = probe.pe.inspect_pe(image).image_base
    memory = bytearray(memory)
    for at in fields:
        value = struct.unpack_from("<I", memory, at)[0]
        struct.pack_into("<I", memory, at, (value + loaded_base - preferred) & 0xffffffff)
    return memory


READ = re.compile(r"\((by|wo|dwo)\(@\$t19 \+ (0x[0-9a-f]+)\) == (0x[0-9a-f]+|\(\((0x[0-9a-f]+) \+ @\$t19 - (0x[0-9a-f]+)\) & 0xffffffff\))\)")


def evaluate_commands(script, memory, loaded_base, unreadable=None):
    successful = 0
    for line in script.splitlines():
        if ".echo BNDLOAD_MISMATCH" not in line:
            continue
        expected_index = re.search(r"@\$t18 == 0n(\d+)", line)
        if expected_index and successful != int(expected_index[1]):
            continue
        reads = READ.findall(line)
        if not reads:
            raise AssertionError("No recognized checks in generated command")
        ok = True
        for kind, rva, literal, value, preferred in reads:
            rva = int(rva, 16)
            size = {"by": 1, "wo": 2, "dwo": 4}[kind]
            if unreadable is not None and rva <= unreadable < rva + size:
                ok = False
                continue
            actual = int.from_bytes(memory[rva:rva + size], "little")
            expected = ((int(value, 16) + loaded_base - int(preferred, 16)) & 0xffffffff
                        if value else int(literal, 16))
            ok &= actual == expected
        successful += bool(ok)
    return successful


class LoadedProbeTests(unittest.TestCase):
    def test_real_parent_source_pins_remain_verified(self):
        sources = probe.source_identities()
        self.assertEqual(len(sources), 18)
        self.assertEqual(sources["src/patcher/framed_bounded_paint.py"], bounded.BOUNDED_SOURCE_SHA256)

    def test_all_ten_resolutions_have_final_stage_and_complete_code_scope(self):
        for resolution in fixture.SIZES:
            with self.subTest(resolution=resolution):
                image, report, scalar = candidate(resolution)
                frozen = copy.deepcopy(report)
                parsed, checks, facts = probe._contract(image, report, scalar)
                script, summary = render(image, report, scalar)
                self.assertEqual(report, frozen)
                self.assertEqual(summary["stage"], bounded.STAGE)
                self.assertEqual(summary["resolution"], resolution)
                code_rva = report["code_va"] - parsed.image_base
                covered = {i for c in checks for i in range(c.rva, c.rva + c.size)}
                self.assertTrue(set(range(code_rva, code_rva + report["code_bytes"])) <= covered)
                self.assertTrue(set(range(parsed.headers_size)) <= covered)
                self.assertTrue(set(range(0x1040, 0x1047)) <= covered)
                self.assertTrue(set(range(0x1051, 0x105c)) <= covered)
                self.assertEqual(sum(c.size for c in checks), len(covered))
                self.assertEqual(facts["checked_bytes"], len(covered))
                self.assertEqual(summary["probe_sha256"], probe._sha(script.encode("ascii")))
                self.assertTrue(all(len(line) < probe.MAX_COMMAND_BYTES for line in script.splitlines()))

    def test_generated_comparisons_accept_independently_relocated_images(self):
        image, report, scalar = candidate("1366x768")
        script, summary = render(image, report, scalar)
        for base in (0x400000, 0x600000, 0x300000, 0x10000, 0x71000000):
            with self.subTest(base=base):
                self.assertEqual(evaluate_commands(script, mapped(image, base), base), summary["required_chunks"])
        self.assertGreater(summary["relocated_checks"], 0)

    def test_original_parent_and_each_changed_scope_cannot_pass_as_final(self):
        image, report, scalar = candidate()
        parsed = probe.pe.inspect_pe(image)
        script, summary = render(image, report, scalar)
        code_rva = report["code_va"] - parsed.image_base
        positions = [0, 0x3c, parsed.pe_offset + 6, 0x1040, 0x1046, 0x1051, 0x105b,
                     code_rva, code_rva + report["code_bytes"] - 1]
        positions += [edit["rva"] for edit in report["edits"]]
        for rva in positions:
            memory = mapped(image, 0x600000)
            memory[rva] ^= 0x80
            with self.subTest(rva=hex(rva)):
                self.assertLess(evaluate_commands(script, memory, 0x600000), summary["required_chunks"])
        memory = mapped(image, 0x400000)
        for edit in report["edits"]:
            old = bytes.fromhex(edit["old_hex"])
            memory[edit["rva"]:edit["rva"] + len(old)] = old
        self.assertLess(evaluate_commands(script, memory, 0x400000), summary["required_chunks"])

    def test_unreadable_memory_does_not_increment_success_counter(self):
        image, report, scalar = candidate()
        script, summary = render(image, report, scalar)
        memory = mapped(image, 0x400000)
        for unreadable in (0, 0x1040, report["code_va"] - 0x400000):
            self.assertLess(evaluate_commands(script, memory, 0x400000, unreadable), summary["required_chunks"])
        lines = script.splitlines()
        self.assertIn("r @$t18 = 0", lines)
        self.assertIn("r @$t19 = 0", lines)
        self.assertIn("@$ptrsize == 0n4", script)
        self.assertEqual(script.count("r @$t18 = @$t18 + 1"), summary["required_chunks"])
        self.assertIn(f"@$t18 == 0n{summary['required_chunks']}", lines[-2])
        self.assertEqual(script.count("result=pass"), 1)

    def test_repeated_missing_or_reordered_command_cannot_replace_coverage(self):
        image, report, scalar = candidate()
        script, facts = render(image, report, scalar)
        commands = [line for line in script.splitlines() if ".echo BNDLOAD_MISMATCH" in line]
        memory = mapped(image, 0x400000)
        missing = commands[:2] + commands[3:]
        duplicate = commands[:2] + [commands[1]] + commands[3:]
        reordered = [commands[1], commands[0]] + commands[2:]
        for altered in (missing, duplicate, reordered):
            self.assertLess(evaluate_commands("\n".join(altered), memory, 0x400000), facts["required_chunks"])

    def test_another_valid_resolution_and_malformed_public_input_are_rejected(self):
        image, report, scalar = candidate()
        with self.assertRaisesRegex(ValueError, "parent identity"):
            probe._contract(image, report | {"resolution": "1366x768"}, scalar)
        for wrong in (None, [], "not metadata"):
            with self.assertRaises(ValueError):
                probe.render_probe(image, wrong)

    def test_probe_contains_no_target_writes_breakpoints_resume_or_process_exit(self):
        image, report, scalar = candidate()
        script, _ = render(image, report, scalar)
        forbidden = re.compile(r"(?:^|[;{}])\s*(?:e[bwdq]|bp|ba|bu|bc|g|gc|gu|p|t|q|qd|\.call|\.writemem|\.shell)\s", re.M)
        self.assertIsNone(forbidden.search(script))
        assignments = re.findall(r"\br\s+([^=]+)=", script)
        self.assertTrue(assignments)
        self.assertTrue(all(register.strip() in ("@$t18", "@$t19") for register in assignments))
        self.assertNotIn(".effmach", script)

    def test_stage_resolution_identity_and_false_evidence_claims_fail_closed(self):
        image, report, scalar = candidate()
        changes = {"schema": "other", "stage": report["parent_stage"], "resolution": "01280x0720",
                   "output_sha256": "0" * 64, "code_sha256": "0" * 64, "original_sha256": "0" * 64,
                   "source_sha256": {}, "code_va": True, "code_bytes": True,
                   "minimap_viewport": False, "camera_clamp": False, "small_world_input_enabled": False,
                   "bounded_small_world_paint": False, "validation_stage_only": False,
                   "game_runtime_executed": True, "manual_input_proof": True, "promotion_ready": True,
                   "parent_probe_reusable": True, "relocation_directory_sha256": "0" * 64, "highlow_count": 0}
        for key, value in changes.items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                probe._contract(image, report | {key: value}, scalar)

    def test_hook_bytes_mapping_and_empty_scalar_inventory_fail(self):
        image, report, scalar = candidate()
        for changes in ({"rva": 0x1041}, {"offset": 0}, {"va": 0}, {"new_hex": "cc"}, {"new_hex": ""}):
            modified = copy.deepcopy(report)
            modified["parent_build"]["hooks"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                probe._contract(image, modified, scalar)
        for changes in ({"hooks": []}, {"hooks": None}, {"stage": bounded.STAGE}, {"output_sha256": "0" * 64}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                probe._contract(image, report | {"parent_build": report["parent_build"] | changes}, scalar)
        with self.assertRaises(ValueError):
            probe._contract(image, report, [])
        with self.assertRaises(ValueError):
            probe._contract(image, report, [SimpleNamespace(offset=len(image) + 1, new=b"x")])

    def test_parent_reconstruction_and_input_edit_mapping_are_required(self):
        image, report, scalar = candidate()
        for field, value in (("old_hex", "00" * 16), ("new_hex", "cc" * 16), ("rva", 0), ("va", 0), ("offset", 0)):
            modified = copy.deepcopy(report)
            modified["edits"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                probe._contract(image, modified, scalar)
        duplicate = [report["edits"][0], report["edits"][0]]
        with self.assertRaisesRegex(ValueError, "overlapping"):
            probe._contract(image, report | {"edits": duplicate}, scalar)

    def test_unaligned_partial_relocation_ranges_expand_to_whole_fields(self):
        image, report, _ = candidate()
        parsed = probe.pe.inspect_pe(image)
        _, fields = probe.pe._old_relocations(image, parsed)
        field = next(at for at in fields if at % 4 != 0)
        checks, spans = probe._checks(image, parsed, [(field + 1, field + 2)], fields)
        self.assertEqual(spans, [(field, field + 4)])
        self.assertEqual(len(checks), 1)
        self.assertTrue(checks[0].relocated)
        self.assertEqual(checks[0].size, 4)
        with self.assertRaisesRegex(ValueError, "overlapping HIGHLOW"):
            probe._checks(image, parsed, spans, (field, field + 1))

    def test_relocation_expected_values_are_masked_at_32_bits(self):
        check = probe.Check(0x1001, 4, 0x00100000, True)
        expression = check.expression(0x400000)
        self.assertIn("& 0xffffffff", expression)
        memory = bytearray(0x1010)
        struct.pack_into("<I", memory, 0x1001, (0x100000 + 0x10000 - 0x400000) & 0xffffffff)
        line = ".if (" + expression + ") { r @$t18 = @$t18 + 1; } .else { .echo BNDLOAD_MISMATCH chunk=0; }"
        self.assertEqual(evaluate_commands(line, memory, 0x10000), 1)

    def test_probe_is_deterministic_but_bound_to_resolution_and_sources(self):
        image, report, scalar = candidate()
        first = render(image, report, scalar)
        self.assertEqual(first, render(image, report, scalar))
        other = render(*candidate("1366x768"))
        self.assertNotEqual(first[1]["contract_id"], other[1]["contract_id"])
        self.assertFalse(first[1]["game_runtime_executed"])
        self.assertFalse(first[1]["manual_input_proof"])
        self.assertFalse(first[1]["promotion_ready"])
        self.assertIn("Not a whole-process hash", first[1]["scope"])


class ProbeCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bounded-loaded-probe-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / "game" / "clash95.exe"
        self.original.parent.mkdir()
        self.original.write_bytes(b"synthetic non-game original")
        self.image, self.report, self.scalar = candidate()
        self.text, self.facts = render(self.image, self.report, self.scalar)
        self.output, self.json, self.probe = (self.root / name for name in ("candidate.exe", "build.json", "loaded.cdb"))
        self.flags = ["--original", str(self.original), "--resolution", "1280x720",
                      "--output", str(self.output), "--report-json", str(self.json), "--probe-cdb", str(self.probe)]

    def command(self, flags=None):
        with redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()) as errors:
            result = cli.main(self.flags if flags is None else flags)
        return result, output.getvalue(), errors.getvalue()

    def test_preflight_generates_probe_in_memory_without_output_validation_or_writes(self):
        with patch.object(cli.bounded, "build_candidate", return_value=(self.image, self.report)), \
             patch.object(probe.recipe, "select_patches_for", return_value=self.scalar), \
             patch.object(cli, "_outputs", side_effect=AssertionError("preflight output validation")):
            code, output, errors = self.command(self.flags + ["--preflight"])
        self.assertEqual(code, 0, errors)
        self.assertTrue(json.loads(output)["loaded_probe_generated"])
        self.assertFalse(any(p.exists() for p in (self.output, self.json, self.probe)))

    def test_write_retains_candidate_bytes_and_binds_saved_probe_to_report(self):
        with patch.object(cli, "_outputs", return_value=(self.output, self.json, self.probe)), \
             patch.object(cli.bounded, "build_candidate", return_value=(self.image, self.report)), \
             patch.object(probe.recipe, "select_patches_for", return_value=self.scalar):
            code, output, errors = self.command()
        self.assertEqual(code, 0, errors)
        self.assertEqual(self.output.read_bytes(), self.image)
        self.assertEqual(self.probe.read_bytes(), self.text.encode("ascii"))
        manifest = json.loads(self.json.read_text())
        self.assertEqual(manifest["loaded_probe"]["probe_sha256"], probe._sha(self.probe.read_bytes()))
        self.assertFalse(manifest["game_runtime_executed"])
        self.assertEqual(self.original.read_bytes(), b"synthetic non-game original")

    def test_bad_probe_destination_is_rejected_before_builder(self):
        for dest in (self.original, self.output, self.json, ROOT / "bad.cdb", self.root / "wrong.txt"):
            with self.subTest(dest=dest), patch.object(cli.bounded, "build_candidate") as builder:
                flags = self.flags[:-1] + [str(dest)]
                self.assertEqual(self.command(flags)[0], 1)
                builder.assert_not_called()

    def test_existing_probe_and_racing_probe_writer_are_not_overwritten(self):
        self.probe.write_bytes(b"keep")
        with patch.object(cli.bounded, "build_candidate") as builder:
            self.assertEqual(self.command()[0], 1)
            builder.assert_not_called()
        with patch.object(cli, "_outputs", return_value=(self.output, self.json, self.probe)), \
             patch.object(cli.bounded, "build_candidate", return_value=(self.image, self.report)), \
             patch.object(probe.recipe, "select_patches_for", return_value=self.scalar):
            self.assertEqual(self.command()[0], 1)
        self.assertEqual(self.probe.read_bytes(), b"keep")
        self.assertFalse(self.json.exists())

    def test_probe_failure_occurs_before_any_candidate_is_written(self):
        with patch.object(cli, "_outputs", return_value=(self.output, self.json, self.probe)), \
             patch.object(cli.bounded, "build_candidate", return_value=(self.image, self.report)), \
             patch.object(cli.framed_loaded_probe, "render_probe", side_effect=ValueError("contract mismatch")):
            code, _, errors = self.command()
        self.assertEqual(code, 1)
        self.assertIn("contract mismatch", errors)
        self.assertFalse(any(p.exists() for p in (self.output, self.json, self.probe)))

    def test_unknown_original_remains_rejected_before_probe_generation(self):
        with patch.object(cli.framed_loaded_probe, "render_probe") as renderer:
            self.assertEqual(self.command(self.flags + ["--preflight"])[0], 1)
            renderer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
