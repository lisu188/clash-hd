"""Offline Complete-HD selection protocol fixtures using authenticated local bytes.

Actual candidate reconstruction runs for every supported resolution and for
manifest/candidate rejection cases. A cached, already verified context is used
only for the negative mid-compilation source-change case. No runtime or capture is run.
"""
from __future__ import annotations

import copy
from enum import IntEnum
import json
import os
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import complete_hd_army_selection_probe as probe
from test_framed_army_selection_probe import breakpoint_command, expression_value, guard_expression

ORIGINAL = Path(os.environ.get("CLASH95_ORIGINAL", "C:/Clash/clash95.exe"))
SAVE_CANDIDATES = (
    Path("C:/ClashTests/completehd-validation-20260908/workdir-800x600/save/0.dat"),
    Path("C:/ClashTests/hd-completion/framed-screens-20260906-034725/workdir/save/0.dat"),
)
CAPTURE = "C:/ClashCaptures/completehd-selection-pure-fixture"


class LiteralPathTests(unittest.TestCase):
    def test_manifest_decoder_rejects_duplicate_keys_and_nonfinite_numbers(self):
        for text in ('{"schema":1,"schema":1}', '{"nested":{"stage":"a","stage":"a"}}',
                     '{"value":NaN}', '{"value":Infinity}', '{"value":-Infinity}'):
            with self.subTest(text=text), patch.object(Path, "read_text", return_value=text):
                with self.assertRaises(ValueError):
                    probe.read_manifest(Path("unused-offline-fixture.json"))

    def test_capture_path_cannot_be_commands_or_escape_the_capture_root(self):
        self.assertEqual(probe.capture_directory(r"C:\ClashCaptures\selection-1"),
                         "C:/ClashCaptures/selection-1")
        for value in (None, 1, "", "C:/ClashCaptures", "C:/ClashCaptures2/x", "C:/ClashTests/x",
                      "D:/ClashCaptures/x", "C:ClashCaptures/x", r"\\host\ClashCaptures\x",
                      "C:/ClashCaptures/../x", "C:/ClashCaptures/./x", "C:/ClashCaptures/x:stream",
                      "C:/ClashCaptures/x;g", 'C:/ClashCaptures/x"g', "C:/ClashCaptures/x\ng"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                probe.capture_directory(value)


class DirectApiManifestTests(unittest.TestCase):
    """Malformed Python inputs must fail before any asset or candidate work."""

    def reject(self, nested):
        manifest = {"schema": 1, "stage": probe.builder.STAGE, "resolution": "800x600",
                    "recipe_revision": probe.builder.REVISION, "nested": nested}
        with patch.object(probe.clip, "verify_original", side_effect=AssertionError("original gate reached")) as original, \
             patch.object(probe.runtime, "verify_context", side_effect=AssertionError("reconstruction reached")) as context:
            with self.assertRaisesRegex(ValueError, "JSON|cycle|circular|recursive"):
                probe.build_selection_probe(b"not an executable", b"not a candidate", b"not a save",
                    capture_dir=CAPTURE, candidate_manifest=manifest, resolution="800x600")
            original.assert_not_called()
            context.assert_not_called()

    def test_nested_intenum_cannot_alias_an_integer(self):
        class Schema(IntEnum):
            ONE = 1
        self.reject({"values": [Schema.ONE]})

    def test_nested_int_subclass_cannot_alias_an_integer(self):
        class Integer(int):
            pass
        self.reject({"values": [Integer(1)]})

    def test_nested_str_subclass_cannot_alias_text(self):
        class Text(str):
            pass
        self.reject({"values": [Text("complete_hd_v1")]})

    def test_nested_object_key_subclass_cannot_alias_a_json_key(self):
        class Key(str):
            pass
        self.reject({"values": [{Key("stage"): "complete_hd_v1"}]})

    def test_cycles_fail_as_value_errors_before_authentication(self):
        cyclic_list = []
        cyclic_list.append(cyclic_list)
        cyclic_dict = {}
        cyclic_dict["self"] = cyclic_dict
        for value in (cyclic_list, cyclic_dict):
            with self.subTest(container=type(value).__name__):
                self.reject(value)

    def test_plain_json_values_still_reach_the_original_authentication_gate(self):
        # No synthetic input is authenticated: the real gate remains mandatory.
        manifest = {"values": [True, False, 1, 1.0, None, "text", {}, []]}
        with patch.object(probe.clip, "verify_original", side_effect=ValueError("fixture original gate")) as original, \
             patch.object(probe.runtime, "verify_context", side_effect=AssertionError("reconstruction reached")) as context:
            with self.assertRaisesRegex(ValueError, "fixture original gate"):
                probe.build_selection_probe(b"not an executable", b"not a candidate", b"not a save",
                    capture_dir=CAPTURE, candidate_manifest=manifest, resolution="800x600")
            original.assert_called_once_with(b"not an executable")
            context.assert_not_called()


class CompleteSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        override = os.environ.get("CLASH95_SELECTION_SAVE")
        choices = (Path(override),) if override else SAVE_CANDIDATES
        if not ORIGINAL.is_file():
            raise unittest.SkipTest(f"authenticated local original unavailable: {ORIGINAL}")
        available = [path for path in choices if path.is_file()]
        if not available:
            raise unittest.SkipTest("inspected slot0 save unavailable; set CLASH95_SELECTION_SAVE")
        cls.save_path = next((path for path in available if probe.sha(path.read_bytes()) == probe.SAVE_SHA256), available[0])
        cls.original, cls.save = ORIGINAL.read_bytes(), cls.save_path.read_bytes()
        if probe.sha(cls.original) != probe.builder.BASE_SHA256 or probe.sha(cls.save) != probe.SAVE_SHA256:
            raise AssertionError("local original/save identity differs; authentic fixtures cannot substitute other bytes")
        cls.inputs_before = (cls.original, cls.save)
        cls.capture_existed = Path(CAPTURE).exists()
        cls.cases = {}
        for resolution in probe.builder.RESOLUTIONS:
            print(f"authenticate Complete-HD selection {resolution}", flush=True)
            candidate, metadata, canonical = probe.builder.build_candidate(cls.original, resolution)
            manifest = json.loads(json.dumps(metadata))
            # wraps records the REAL second reconstruction, never a fake verifier.
            with patch.object(probe.runtime, "verify_context", wraps=probe.runtime.verify_context) as verify:
                packet = probe.build_selection_probe(cls.original, candidate, cls.save,
                    capture_dir=CAPTURE, candidate_manifest=manifest, resolution=resolution)
            if verify.call_count != 1:
                raise AssertionError("selection preparation must authenticate the complete context")
            cls.cases[resolution] = {
                "candidate": candidate, "manifest": manifest, "packet": packet,
                "context": {"manifest": metadata, "candidate": candidate, "probe": canonical,
                            "framed": metadata["predecessor"]["base_candidate"]["base_candidate"],
                            "inherited_stage": metadata["predecessor"]["stage"]},
            }

    def build(self, *, resolution="800x600", original=None, candidate=None, save=None, manifest=None):
        case = self.cases[resolution]
        return probe.build_selection_probe(self.original if original is None else original,
            case["candidate"] if candidate is None else candidate, self.save if save is None else save,
            capture_dir=CAPTURE, candidate_manifest=case["manifest"] if manifest is None else manifest,
            resolution=resolution)

    def test_all_six_candidates_are_bound_without_runtime_or_output(self):
        self.assertEqual(set(self.cases), {"800x600", "1024x768", "1280x720", "1280x960", "1920x1080", "802x602"})
        for resolution, case in self.cases.items():
            with self.subTest(resolution=resolution):
                packet, manifest = case["packet"], case["manifest"]
                self.assertEqual(packet["stage"], probe.builder.STAGE)
                self.assertEqual(packet["candidate_recipe"], probe.builder.REVISION)
                self.assertEqual(packet["candidate_sha256"], probe.sha(case["candidate"]))
                self.assertEqual(packet["candidate_manifest_canonical_sha256"], probe.sha(
                    json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()))
                self.assertEqual(packet["inherited_revision"], manifest["predecessor"]["army_revision"])
                self.assertEqual(packet["startup_recipe"], probe.compiler.provenance())
                self.assertEqual(packet["save_sha256"], probe.SAVE_SHA256)
                self.assertEqual(packet["probe_sha256"], probe.sha(packet["compiled_probe"].encode("ascii")))
                self.assertEqual(packet["initial_extra_sha256"], probe.sha(packet["initial_extra"].encode("ascii")))
                self.assertEqual(packet["initial_extra"], case["context"]["probe"])
                self.assertEqual(packet["unit_squad_types"], [16, 16, 1, 1, 1, 1, 1, 1])
                self.assertEqual(packet["capture_class"], "e0_software_diagnostic")
                for key in ("runtime_executed", "manual_input_proof", "promotion_ready", "native_predicate_forced"):
                    self.assertIs(packet[key], False)
                for relative, digest in packet["source_sha256"].items():
                    self.assertEqual(probe.sha((ROOT / relative).read_bytes()), digest, relative)
                self.assertLess(max(map(len, packet["compiled_probe"].splitlines())), 4096)
                self.assertNotRegex(packet["compiled_probe"], r"__[A-Z0-9_]+__")
        self.assertEqual((ORIGINAL.read_bytes(), self.save_path.read_bytes()), self.inputs_before)
        self.assertEqual(Path(CAPTURE).exists(), self.capture_existed)

    def test_all_loaded_contracts_are_exact_and_ordered(self):
        for resolution, case in self.cases.items():
            packet = case["packet"]
            manifest = case["manifest"]
            identity = f"resolution={resolution} candidate_sha256={packet['candidate_sha256']}"
            contracts = (
                f"ARMY_CONTRACT_PASS stage={packet['inherited_stage']} {identity} revision={manifest['predecessor']['army_revision']}",
                f"COMPLETEHD_CONTRACT_PASS stage={probe.builder.STAGE} {identity} revision={probe.builder.REVISION}",
                f"PTILE_CONTRACT_PASS stage={packet['inherited_stage']} {identity}",
            )
            with self.subTest(resolution=resolution):
                for text in (packet["initial_extra"], packet["compiled_probe"]):
                    for contract in contracts:
                        self.assertEqual(text.splitlines().count(".echo " + contract), 1)
                    positions = [text.index(".echo " + contract) for contract in contracts]
                    self.assertEqual(positions, sorted(positions))
                self.assertEqual(probe.runtime.loaded_contract_failures("\n".join(contracts),
                    packet["initial_extra"], case["context"]), [])
                for changed in (contracts[1:], contracts + (contracts[0],), contracts[::-1]):
                    self.assertTrue(probe.runtime.loaded_contract_failures("\n".join(changed),
                        packet["initial_extra"], case["context"]))

    def test_native_loaded_bytes_and_call_return_boundaries_are_preserved(self):
        for resolution, case in self.cases.items():
            packet, candidate = case["packet"], case["candidate"]
            with self.subTest(resolution=resolution):
                checks = {int(va, 16): int(value, 16) for va, value in re.findall(
                    r"\(by\(([0-9a-f]{8})\) != 0x([0-9a-f]{2})\)", packet["compiled_probe"])}
                for va, size in ((0x408030, 269), (0x406980, 675), (0x40A490, 112), (0x40A500, 247),
                                 (0x423B00, 63), (0x423420, 825), (0x406FA0, 6)):
                    for offset, value in enumerate(probe._read(candidate, va, size)):
                        self.assertEqual(checks[va + offset], value)
                self.assertLess(packet["compiled_probe"].index("SHSEL_BYTES_PASS"), packet["compiled_probe"].index("bp80 "))
                returns = packet["native_call_returns"]
                self.assertEqual((returns["portraits"], returns["redraw"]), (0x423B32, 0x423B3C))
                draw = packet["observer_vas"]["90"]
                for call, target in ((0x423B2D, 0x423420), (0x423B37, 0x418700),
                                     (returns["native_draw"] - 5, draw), (returns["composition_draw"] - 5, draw)):
                    self.assertEqual(probe._call_return(candidate, call, target), call + 5)
                    with self.assertRaises(ValueError):
                        probe._call_return(candidate, call, target + 1)

    def test_dynamic_surface_dimensions_dump_lengths_and_nonwrapping_extent(self):
        for resolution, case in self.cases.items():
            width, height = map(int, resolution.split("x"))
            size, maximum = width * height, 0x100000000 - width * height
            for number, phase, name in ((88, 7, "before-redraw"), (89, 8, "after-redraw")):
                with self.subTest(resolution=resolution, observer=number):
                    command = breakpoint_command(case["packet"]["compiled_probe"], number)[1]
                    self.assertIn(f".writemem {CAPTURE}/{name}.raw poi(poi(005202e0)+4) L0n{size}", command)
                    regs = dict(tid=1, t2=1, t1=0x600000, t0=phase, t5=1, t6=1, t4=1, t7=1)
                    memory = {0x5202E4: 0x600000, 0x511B58: 3, 0x514194: 3, 0x526994: 1,
                              0x5202E0: 0x900000, 0x900000: width, 0x900002: height, 0x900004: maximum}
                    condition = guard_expression(command)
                    self.assertTrue(expression_value(condition, regs, memory))
                    for field, value in ((0x900004, maximum + 1), (0x900004, 0xFFFF),
                                         (0x900000, width + 2), (0x900002, height + 2)):
                        self.assertFalse(expression_value(condition, regs, memory | {field: value}))
                    self.assertFalse(expression_value(condition, regs | {"t6": 0}, memory))

    def test_disclosed_controls_do_not_force_selection_or_native_results(self):
        compiled = self.cases["800x600"]["packet"]["compiled_probe"]
        self.assertIn("SHSEL_CONTROLLED scroll=(10,17) screen=(448,176)", compiled)
        self.assertIn("predicate_forced=0", compiled)
        self.assertIn("r esp=@esp-4; ed @esp 00406fa1; r esp=@esp-4; ed @esp 00406980; r eip=00408030", compiled)
        commands = [breakpoint_command(compiled, number)[1] for number in range(80, 93)]
        for command in commands:
            self.assertIn("SHSEL_REJECT", command)
        self.assertNotRegex("\n".join(commands), r"\br\s+@?(?:eax|edx)=|\b(?:ed|eb|ew)\s+00511b58")
        self.assertIn("SHSEL_HOST_READY", commands[0])
        self.assertNotRegex(commands[0], r"(?:^|;\s*)(?:g|gc|gh|gn)\b")
        self.assertIn("(@eax == 1)", guard_expression(commands[1]))
        self.assertIn("((@eax == 0) | (@eax == 1))", guard_expression(commands[11]))
        self.assertIn("(@eax == 1)", guard_expression(commands[12]))
        self.assertTrue(any("not natural or manual" in line for line in self.cases["800x600"]["packet"]["limits"]))

    def test_original_save_candidate_and_resolution_mismatches_fail_closed(self):
        candidate = self.cases["800x600"]["candidate"]
        mutations = (
            {"original": bytearray(self.original)},
            {"original": self.original[:-1] + bytes([self.original[-1] ^ 1])},
            {"save": self.save[:-1] + bytes([self.save[-1] ^ 1])},
            {"candidate": candidate[:-1] + bytes([candidate[-1] ^ 1])},
            {"candidate": self.cases["1024x768"]["candidate"]},
            {"manifest": self.cases["1024x768"]["manifest"]},
        )
        # No reconstruction mocks: hashes/claims cannot bless mismatched bytes.
        for mutation in mutations:
            with self.subTest(fields=list(mutation)), self.assertRaises(ValueError):
                self.build(**mutation)
        for resolution in ("640x480", "1600x900", "1921x1080", None):
            with self.subTest(resolution=resolution), self.assertRaises(ValueError):
                probe.build_selection_probe(self.original, candidate, self.save, capture_dir=CAPTURE,
                    candidate_manifest=self.cases["800x600"]["manifest"], resolution=resolution)

    def test_manifest_stage_recipe_source_and_exact_json_types_are_authenticated(self):
        mutations = {
            "stage": lambda value: value.update(stage="wrong-stage"),
            "recipe": lambda value: value.update(recipe_revision="wrong-recipe"),
            "source": lambda value: value["source_hashes"].update({next(iter(value["source_hashes"])): "0" * 64}),
            "schema-bool": lambda value: value.update(schema=True),
            "schema-float": lambda value: value.update(schema=1.0),
            "candidate-claim": lambda value: value.update(candidate_sha256="a" * 64),
        }
        for name, change in mutations.items():
            manifest = copy.deepcopy(self.cases["800x600"]["manifest"])
            change(manifest)
            with self.subTest(mutation=name), self.assertRaises(ValueError):
                self.build(manifest=manifest)

    def test_reviewed_source_and_mid_compilation_source_changes_fail_closed(self):
        with patch.dict(probe.PINNED_SOURCES, {"tools/framed_army_selection_probe.py": "0" * 64}):
            with self.assertRaisesRegex(ValueError, "source differs"):
                self.build()
        sources = probe.verify_sources()
        with patch.object(probe.runtime, "verify_context", return_value=self.cases["800x600"]["context"]), \
             patch.object(probe, "verify_sources", side_effect=[sources, sources | {"fixture-change": "0" * 64}]):
            with self.assertRaisesRegex(ValueError, "sources changed"):
                self.build()


if __name__ == "__main__":
    unittest.main(verbosity=2)
