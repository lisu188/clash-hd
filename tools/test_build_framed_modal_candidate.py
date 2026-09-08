#!/usr/bin/env python3
"""Offline modal integration: independent PE loader, edit replay and CLI bounds.

Real candidate images stay in memory. File-output cases use plainly synthetic
non-PE bytes in a private temporary directory. No game/debugger is launched.
"""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import build_framed_modal_candidate as builder
from test_pe_extension import independent_image, rebase

ORIGINAL = Path("C:/Clash/clash95.exe")
BASE_IMAGES = {
    "800x600": "c0867837388e93507bc190c0e722717cd904eacd1562db835860ae60ed704373",
    "1024x768": "69899e07f70dde2094264be694300e00c7a778f1391ac7797b74c59c56ee1ce0",
    "1280x720": "6329940475c49c0db92398ec29264044cea8a0476b48a40529a3c104f37da78f",
    "1280x960": "181b720d759e9c7af62eedcaca74e0dc08cdd5db28048e9b611e70775961c9f9",
    "1920x1080": "034e184ee3c48fbea6a31a2b55a6339451f7f32f11fa77ce97e0e457ebedc3c1",
    "802x602": "2a75641f1aa1b3132ae50b5e8ed768458e5e6d6985e9cfba702ced85ffec8161",
}
SITES = {0x422180: 5, 0x422020: 5, 0x401E30: 5, 0x51B6D0: 6, 0x51BC20: 6, 0x4224B2: 5}


def sites_for(resolution):
    # The existing 800-wide recipe keeps its action wrapper in the original
    # small cave; larger profiles relocate that exact wrapper before this work.
    sites = dict(SITES)
    if resolution == "800x600":
        sites[0x51316F] = sites.pop(0x51BC20)
    return sites


def sha(data):
    return hashlib.sha256(data).hexdigest()


def loaded_checks(probe):
    checks = []
    pattern = r"\((wo|by)\(([0-9a-f]{8})\) != ([0-9a-f]+)\)"
    for line in probe.splitlines():
        if not any(marker in line for marker in ("PTILE_CONTRACT_FAIL", "MCANVAS_CONTRACT_FAIL")):
            continue
        residual = re.sub(pattern, "READ", line)
        if not re.fullmatch(r"\.if \(READ(?: \| READ)*\) \{ \.echo (?:PTILE|MCANVAS)_CONTRACT_FAIL; q \}", residual):
            raise AssertionError("unexpected loaded-check grammar")
        checks.extend((int(va, 16), 2 if reader == "wo" else 1, int(value, 16))
                      for reader, va, value in re.findall(pattern, line))
    if not checks:
        raise AssertionError("missing loaded checks")
    return checks


def replay(image, edits):
    data = bytearray(image)
    for row in edits:
        offset = row["offset"]
        old, new = bytes.fromhex(row["old_hex"]), bytes.fromhex(row["new_hex"])
        if data[offset:offset + len(old)] != old or (not old and offset != len(data)):
            raise AssertionError("old bytes or append order differ")
        data[offset:offset + len(old)] = new
    return bytes(data)


@unittest.skipUnless(ORIGINAL.is_file(), "requires user-owned original; candidate bytes stay in memory")
class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()
        cls.results = {resolution: builder.build_candidate(cls.original, resolution, minimap_viewport=True)
                       for resolution in BASE_IMAGES}

    def test_distinct_stage_replay_and_all_six_previous_images_preserved(self):
        for resolution, (image, metadata, probe) in self.results.items():
            with self.subTest(resolution=resolution):
                previous = metadata["base_candidate"]
                base = replay(self.original, [*previous["selected_patches"], *previous["edits"]])
                self.assertEqual(sha(base), BASE_IMAGES[resolution])
                self.assertEqual(sha(base), metadata["base_candidate_sha256"])
                self.assertEqual(replay(base, metadata["edits"]), image)
                self.assertEqual(metadata["output_sha256"], sha(image))
                self.assertEqual(metadata["stage"], builder.STAGE)
                self.assertEqual(previous["stage"], builder.BASE_STAGE)
                self.assertNotEqual(builder.STAGE, builder.BASE_STAGE)
                self.assertTrue(builder.STAGE.endswith("-modalcanvas-validation"))
                self.assertEqual(metadata["initial_probe_sha256"], sha(probe.encode()))
                for key in ("installation_ready", "runtime_executed", "manual_input_proof", "promotion_ready"):
                    self.assertFalse(metadata[key], key)
        self.assertEqual(ORIGINAL.read_bytes(), self.original)

    def test_independent_loader_and_relocation_oracle(self):
        for resolution, (image, metadata, _) in self.results.items():
            with self.subTest(resolution=resolution):
                previous = metadata["base_candidate"]
                base = replay(self.original, [*previous["selected_patches"], *previous["edits"]])
                before, old_sections, old_fixups, _ = independent_image(base)
                memory, sections, fixups, _ = independent_image(image)
                self.assertEqual(sections[:-2], old_sections)
                self.assertEqual((sections[-2][0], sections[-2][-1]), (b".hdmodal", 0x60000020))
                self.assertEqual((sections[-1][0], sections[-1][-1]), (b".hdstate", 0xC0000040))
                self.assertEqual(sections[-1][1] - sections[-2][1], 0x20000)
                self.assertEqual(memory[sections[-1][1]:sections[-1][1] + 4096], bytes(4096))
                self.assertEqual(metadata["removed_highlow"], [])
                added = {metadata["code_rva"] + row["offset"] for row in metadata["relocations"] if row["kind"] == "abs32"}
                self.assertEqual(set(fixups), set(old_fixups) | added)
                self.assertEqual(len(fixups), len(set(fixups)))
                old_payload = previous["code_va"] - 0x400000
                old_size = previous["extension_payload_size"]
                self.assertEqual(memory[old_payload:old_payload + old_size], before[old_payload:old_payload + old_size])
                observed = {row["va"]: len(bytes.fromhex(row["new_hex"])) for row in metadata["hooks"]}
                self.assertEqual(observed, sites_for(resolution))
                for delta in (-0x100000, 0x02000000):
                    moved = rebase(memory, fixups, delta)
                    for row in metadata["relocations"]:
                        rva = metadata["code_rva"] + row["offset"]
                        if row["kind"] == "abs32":
                            self.assertEqual(struct.unpack_from("<I", moved, rva)[0], (row["target"] + delta) & 0xFFFFFFFF)
                        else:
                            self.assertEqual(moved[rva:rva + 4], memory[rva:rva + 4])
                    for row in metadata["hooks"]:
                        rva = row["rva"]
                        new = bytes.fromhex(row["new_hex"])
                        self.assertEqual(moved[rva:rva + len(new)], new)
                        self.assertEqual(new[0], 0xE8 if row["va"] == 0x4224B2 else 0xE9)
                        target = row["va"] + delta + 5 + struct.unpack_from("<i", new, 1)[0]
                        self.assertIn(target - delta, metadata["modal_entry_vas"].values())

    def test_loaded_check_coverage_and_single_byte_mutation_rejection(self):
        for resolution, (image, metadata, probe) in self.results.items():
            with self.subTest(resolution=resolution):
                memory, _, _, _ = independent_image(image)
                checks = loaded_checks(probe)
                guarded = set()
                for va, length, value in checks:
                    actual = memory[va - 0x400000:va - 0x400000 + length]
                    self.assertEqual(int.from_bytes(actual, "little"), value)
                    guarded.update(range(va, va + length))
                    # Independent mutation oracle on every checked operand byte.
                    for index in range(length):
                        mutated = bytearray(actual)
                        mutated[index] ^= 1
                        self.assertNotEqual(int.from_bytes(mutated, "little"), value)
                pe_image = builder.pe.inspect_pe(image)
                required = set()
                for section in pe_image.sections:
                    required.update(range(0x400000 + section.header_offset, 0x400000 + section.header_offset + 40))
                for va, length in sites_for(resolution).items():
                    required.update(range(va, va + length))
                required.update(range(metadata["code_va"], metadata["code_va"] + metadata["code_bytes"]))
                required.update(range(metadata["state_va"], metadata["state_va"] + 4096))
                required.update(range(0x400000 + pe_image.optional_offset + 136, 0x400000 + pe_image.optional_offset + 144))
                required.update(range(0x400000 + pe_image.relocation_rva,
                                      0x400000 + pe_image.relocation_rva + pe_image.relocation_size))
                for row in metadata["authenticated_legacy_continuations"]:
                    required.update(range(row["entry_va"], row["entry_va"] + row["span_bytes"]))
                self.assertTrue(required <= guarded)
                self.assertLess(probe.rindex("MCANVAS_CONTRACT_FAIL"), probe.index("bp70 "))
                self.assertEqual(probe.count(f"PTILE_CONTRACT_PASS stage={builder.STAGE} "), 1)
                self.assertEqual(probe.count(f"MCANVAS_CONTRACT_PASS stage={builder.STAGE} "), 1)
                self.assertNotIn(f"stage={builder.BASE_STAGE} ", probe)
                self.assertTrue(all(len(line) < 4096 for line in probe.splitlines()))
                self.assertIsNone(re.search(r"(?:^|[;{])\s*(?:e[bdwq]|r\s+(?:eip|esp|eax))\b", probe))

    def test_invalid_source_original_geometry_and_implicit_feature_rejected(self):
        changed = bytearray(self.original)
        changed[0x1000] ^= 1
        with self.assertRaises(ValueError):
            builder.build_candidate(bytes(changed), "1024x768")
        for resolution, feature in (("01024x768", False), ("1025x768", False), ("1024x768", 1)):
            with self.assertRaises(ValueError):
                builder.build_candidate(self.original, resolution, minimap_viewport=feature)
        read = Path.read_bytes
        target = (builder.ROOT / "src/patcher/framed_modal_canvas.py").resolve()
        def changed_source(path):
            return read(path) + b"\n# unreviewed change\n" if path.resolve() == target else read(path)
        with patch.object(Path, "read_bytes", changed_source), self.assertRaises(ValueError):
            builder.build_candidate(self.original, "1024x768")


class OutputBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="clash-modal-builder-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / "original.bin"
        self.original.write_bytes(b"synthetic original - not a PE")
        self.candidates = self.root / "candidates"
        self.captures = self.root / "captures"
        self.output = self.candidates / "synthetic.exe"
        self.report = self.captures / "report.json"
        self.probe = self.captures / "probe.cdb"
        self.recipe = (b"synthetic candidate - not a PE", {"source_sha256": {}, "fixture": True}, ".echo SYNTHETIC_NO_RUNTIME\n")

    def invoke(self, extra, expect=0, **overrides):
        argv = ["builder", "--original", str(self.original), "--resolution", "1024x768", *extra]
        with patch.object(sys, "argv", argv), patch.object(builder, "CANDIDATE_ROOT", self.candidates), \
             patch.object(builder, "CAPTURE_ROOT", self.captures), \
             patch.object(builder, "build_candidate", return_value=self.recipe, **overrides) as build, \
             redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()):
            if expect:
                with self.assertRaises(SystemExit) as error:
                    builder.main()
                self.assertEqual(error.exception.code, expect)
            else:
                self.assertEqual(builder.main(), 0)
            return build.call_count, output.getvalue()

    def args(self, output=None, report=None, probe=None):
        return ["--output", str(output or self.output), "--report-json", str(report or self.report),
                "--probe-out", str(probe or self.probe)]

    def test_preflight_has_no_outputs_and_cannot_accept_output_paths(self):
        count, output = self.invoke(["--preflight"])
        self.assertEqual(count, 1)
        self.assertFalse(json.loads(output)["runtime_executed"])
        self.assertFalse(self.candidates.exists())
        self.assertFalse(self.captures.exists())
        self.assertEqual(self.invoke(["--preflight", *self.args()], expect=2)[0], 0)

    def test_exclusive_artifacts_preserve_existing_files_and_source(self):
        self.invoke(self.args())
        self.assertEqual(self.output.read_bytes(), self.recipe[0])
        self.assertEqual(json.loads(self.report.read_text()), self.recipe[1])
        self.assertEqual(self.probe.read_text(), self.recipe[2])
        before = {p: p.read_bytes() for p in (self.original, self.output, self.report, self.probe)}
        self.assertEqual(self.invoke(self.args(), expect=2)[0], 0)
        self.assertEqual({p: p.read_bytes() for p in before}, before)

    def test_forbidden_paths_fail_before_candidate_generation(self):
        cases = [self.args(output=self.original), self.args(output=builder.ROOT / "bad.exe"),
                 self.args(output=self.root / "outside.exe"), self.args(output=self.candidates / "bad.dll"),
                 self.args(report=self.root / "outside.json"), self.args(probe=self.captures / "bad.ps1"),
                 self.args(report=self.output), []]
        for args in cases:
            with self.subTest(args=args):
                self.assertEqual(self.invoke(args, expect=2)[0], 0)
        self.assertFalse(self.candidates.exists())
        self.assertFalse(self.captures.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
