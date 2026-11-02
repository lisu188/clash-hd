#!/usr/bin/env python3
"""Canonical hidden-soak probe composition: parity pins and fail-closed inputs."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hidden_soak_probe_composition as composition

RAW_PATH = r"C:\ClashCaptures\hd-soak\hidden\hidden-soak-20261102-143328-102-map-pan\frames\surface.raw"
# Exercises every substitution, CRLF/LF mixing, a case-variant anchor, base-text
# dollars, literal backslashes in the inserted text and the extra template trim.
SYNTHETIC_PROBE_TEMPLATE = (
    b"$$ synthetic base probe with literal $$ and $& in base text\r\n"
    b".echo slot=__LOAD_SLOT__ x=__LOAD_MOUSE_RAW_X__ y=__LOAD_MOUSE_RAW_Y__\n"
    b'bp 00447000 "__PRE_ENTRY_LOAD_COORD_ACTION__ gc"\r\n'
    b"__START_ANIMS_BP__\r\n"
    b'BP 0040b660 "__VISIBILITY_PLAYGAME_ACTION__.echo play; gc"\r\n'
    b'bp 00412345 "__VISIBILITY_PATCH_ACTION____SURFACE_DUMP_ACTION__"\r\n'
    b".writemem __RAW_PATH__ 00000000 L4\r\n"
    b"g\r\n")
SYNTHETIC_SOAK_TEMPLATE = (
    b"  \r\n\t\r\n"
    b".echo extra duration=__SOAK_DURATION_TICKS__ pan=__SOAK_PAN__ every=__PAN_INTERVAL_TICKS__\r\n"
    b"r @$t7 = 0; r @$t13 = __LOAD_SLOT__\n"
    b'.printf \\"x=__LOAD_MOUSE_RAW_X__ y=__LOAD_MOUSE_RAW_Y__\\\\n\\"\r\n'
    b'bp 00407d20 "gc"\r\n'
    b"\r\n\r\n  ")
# Parameter sets: the seven hidden rungs plus both validated range boundaries.
CASES = {
    "D0": ("map-pan", 120, 10, 2), "S1": ("map-idle", 120, 10, 2), "S2": ("map-idle", 600, 10, 2),
    "S3": ("map-pan", 600, 10, 2), "S4": ("map-pan", 1800, 10, 2), "L1": ("map-idle", 7200, 10, 2),
    "L2": ("map-pan", 7200, 10, 2), "edge-low": ("map-pan", 60, 1, 0), "edge-high": ("map-idle", 28800, 600, 9),
}
# Bytes the legacy inline PowerShell composition wrote for the synthetic
# templates under Windows PowerShell 5.1; see the parity receipt.
SYNTHETIC_LEGACY_SHA256 = {
    "D0": "44635eadc4ec1154072dc6ce39fa4a78dbf44c0185fc099cff9b7ad7a20bd6f9",
    "S1": "07beb59358ce075bb46915a02df54258864c20bf42e5c40fdc03ec03ecf180e1",
    "S2": "acaf5ad2e36f962d1bfbc15b113e4d72b1ba256b7b0e45dedaa1a0c22a101631",
    "S3": "f7fc50962df90e7a0ee0c2f332b4180da3a1d731873086138697f9ef8a0df392",
    "S4": "f1ac45c0cb25e095fad46a3bfaea7f0163d8bbac1282daaf80e97603601057cb",
    "L1": "c618f7f93ab7d3164970b7a2513d642bff03481afcd6e42a12fa2747bb6cbee8",
    "L2": "05de5c3d1405235d37c0ad6de36835a54928aeff2ddc0a6d4190ff4dddb2086c",
    "edge-low": "f941f72b81549714ca58e85980b25164b01a2d618e372a4adddc4e8c841e4aee",
    "edge-high": "3536f86798b092eb02762f00852db07579a0023a22b4c24a2a198e805f72dc7e",
}
PARITY_RECEIPT = ROOT / "reports" / "hidden-soak-probe-composition-parity-20261102.json"


def compose(probe: bytes, soak: bytes, case: str, **overrides) -> bytes:
    route, duration, pan_interval, slot = CASES[case]
    parameters = dict(route=route, duration_sec=duration, pan_interval_sec=pan_interval, load_slot=slot,
                      raw_path=RAW_PATH) | overrides
    return composition.compose_probe(probe, soak, **parameters)


class CompositionTests(unittest.TestCase):
    def test_synthetic_templates_reproduce_the_legacy_powershell_bytes(self):
        self.assertEqual(set(SYNTHETIC_LEGACY_SHA256), set(CASES))
        for case, expected in SYNTHETIC_LEGACY_SHA256.items():
            with self.subTest(case=case):
                probe = compose(SYNTHETIC_PROBE_TEMPLATE, SYNTHETIC_SOAK_TEMPLATE, case)
                self.assertEqual(hashlib.sha256(probe).hexdigest(), expected)
        probe = compose(SYNTHETIC_PROBE_TEMPLATE, SYNTHETIC_SOAK_TEMPLATE, "D0").decode("ascii")
        self.assertTrue(probe.startswith("$$ synthetic base probe with literal $$ and $& in base text\r\n"))
        self.assertIn("\r\nbp 0040B660 \".echo play; gc\"\r\n", probe)
        self.assertNotIn("BP 0040b660", probe)
        self.assertIn('.printf \\"x=00005000 y=00003480\\\\n\\"', probe)
        self.assertIn(".writemem C:/ClashCaptures/hd-soak/hidden/", probe)
        self.assertTrue(probe.endswith("g\r\n\r\n"))

    def test_repository_templates_reproduce_the_parity_receipt(self):
        receipt = json.loads(PARITY_RECEIPT.read_text(encoding="utf-8"))
        self.assertTrue(receipt["passed"])
        self.assertEqual(receipt["raw_path"], RAW_PATH)
        templates = {}
        for role, row in receipt["templates"]["real"].items():
            templates[role] = (ROOT / row["path"]).read_bytes()
            self.assertEqual((hashlib.sha256(templates[role]).hexdigest(), len(templates[role])), (row["sha256"], row["size"]),
                             f"{row['path']} changed: rerun tools/hidden_soak_probe_composition_parity.py on Windows")
        for kind, expected in (("real", None), ("synthetic", SYNTHETIC_LEGACY_SHA256)):
            rows = [row for row in receipt["cases"] if row["templates"] == kind]
            self.assertEqual({row["case"] for row in rows}, set(CASES))
            for row in rows:
                with self.subTest(kind=kind, case=row["case"]):
                    self.assertTrue(row["byte_equal"])
                    self.assertEqual(CASES[row["case"]], (row["route"], row["duration_sec"], row["pan_interval_sec"], row["load_slot"]))
                    if expected is not None:
                        self.assertEqual(row["generated_probe_sha256"], expected[row["case"]])
                        continue
                    probe = compose(templates["probe_template"], templates["soak_probe_template"], row["case"])
                    self.assertEqual((hashlib.sha256(probe).hexdigest(), len(probe)),
                                     (row["generated_probe_sha256"], row["generated_probe_size"]))

    def test_inputs_the_legacy_producer_would_reinterpret_are_rejected(self):
        soak = SYNTHETIC_SOAK_TEMPLATE
        bad_soak = {f"dotnet token {token!r}": soak.replace(b"r @$t7", b"r @" + token + b"t7")
                    for token in (b"$$", b"$&", b"$_", b"$0", b"$1", b"${x}", b"$'", b"$`", b"$+")}
        bad_soak |= {
            "standalone g": soak.replace(b'bp 00407d20 "gc"', b' G \r\nbp 00407d20 "gc"'),
            "missing placeholder": soak.replace(b"__SOAK_PAN__", b"1"),
            "non-ASCII": soak + "\u00e9".encode("utf-8"), "UTF-8 BOM": b"\xef\xbb\xbf" + soak,
            "vertical tab": soak.replace(b"r @$t7", b"\x0br @$t7"), "NUL": soak + b"\x00",
            "unit separator": soak.replace(b"r @$t7", b"\x1fr @$t7"), "empty": b"", "text": soak.decode("ascii"),
        }
        for label, value in bad_soak.items():
            with self.subTest(soak=label), self.assertRaises(composition.ProbeCompositionError):
                compose(SYNTHETIC_PROBE_TEMPLATE, value, "D0")
        probe = SYNTHETIC_PROBE_TEMPLATE
        bad_probe = {
            "no anchor": probe.replace(b"BP 0040b660 ", b"bp 0040b661 "),
            "second anchor": probe + b'bP 0040B660 "gc"\r\n',
            "leftover placeholder": probe + b".echo __UNKNOWN_PLACEHOLDER__\r\n",
            "non-ASCII": probe.replace(b"synthetic", "synth\u00e9tic".encode("utf-8")),
        }
        for label, value in bad_probe.items():
            with self.subTest(probe=label), self.assertRaises(composition.ProbeCompositionError):
                compose(value, SYNTHETIC_SOAK_TEMPLATE, "D0")

    def test_parameters_outside_the_runner_contract_are_rejected(self):
        for overrides in ({"route": "menu-idle"}, {"route": "MAP-PAN"}, {"duration_sec": 59}, {"duration_sec": 28801},
                          {"duration_sec": True}, {"duration_sec": 120.0}, {"pan_interval_sec": 0},
                          {"pan_interval_sec": 601}, {"load_slot": -1}, {"load_slot": 10}, {"load_slot": False},
                          {"raw_path": ""}, {"raw_path": None}, {"raw_path": 'C:\\frames"\\surface.raw'},
                          {"raw_path": "C:\\frames\n\\surface.raw"}, {"raw_path": "C:\\caf\u00e9\\surface.raw"}):
            with self.subTest(overrides=overrides), self.assertRaises(composition.ProbeCompositionError):
                compose(SYNTHETIC_PROBE_TEMPLATE, SYNTHETIC_SOAK_TEMPLATE, "D0", **overrides)

    def test_cli_writes_one_new_probe_and_reports_what_it_composed(self):
        with tempfile.TemporaryDirectory(prefix="clash-probe-composition-") as directory:
            root = Path(directory)
            (root / "probe.cdb").write_bytes(SYNTHETIC_PROBE_TEMPLATE)
            (root / "soak.cdb").write_bytes(SYNTHETIC_SOAK_TEMPLATE)
            output = root / "generated.cdb"
            argv = ["--probe-template", str(root / "probe.cdb"), "--soak-template", str(root / "soak.cdb"),
                    "--route", "map-pan", "--duration-sec", "120", "--pan-interval-sec", "10", "--load-slot", "2",
                    "--raw-path", RAW_PATH, "--output", str(output)]
            with redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(composition.main(argv), 0)
            receipt = json.loads(stdout.getvalue())
            expected = compose(SYNTHETIC_PROBE_TEMPLATE, SYNTHETIC_SOAK_TEMPLATE, "D0")
            self.assertEqual(output.read_bytes(), expected)
            self.assertEqual(receipt, {
                "schema": "hidden_soak_probe_composition_v1", "composer_sha256": composition.composer_sha256(),
                "parameters": {"route": "map-pan", "duration_sec": 120, "pan_interval_sec": 10, "load_slot": 2,
                               "raw_path": RAW_PATH},
                "generated_probe_sha256": hashlib.sha256(expected).hexdigest(), "generated_probe_size": len(expected),
                "probe_template_sha256": hashlib.sha256(SYNTHETIC_PROBE_TEMPLATE).hexdigest(),
                "probe_template_size": len(SYNTHETIC_PROBE_TEMPLATE),
                "soak_probe_template_sha256": hashlib.sha256(SYNTHETIC_SOAK_TEMPLATE).hexdigest(),
                "soak_probe_template_size": len(SYNTHETIC_SOAK_TEMPLATE)})
            with redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(composition.main(argv), 1)  # An existing probe is never replaced.
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("ERROR", stderr.getvalue())
            self.assertEqual(output.read_bytes(), expected)
            (root / "soak.cdb").write_bytes(SYNTHETIC_SOAK_TEMPLATE.replace(b"__SOAK_PAN__", b"1"))
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(composition.main([*argv[:-1], str(root / "rejected.cdb")]), 1)
            self.assertFalse((root / "rejected.cdb").exists())


    def test_hidden_runner_composes_only_through_this_module(self):
        source = (ROOT / "scripts/cdb/run_hidden_soak.ps1").read_text(encoding="ascii")
        self.assertEqual(source.count("$compositionRaw = & $pythonExe -B $composer --probe-template"), 1)
        for retired in ("[regex]::Replace($probeText", "$extraProbeText", "__START_ANIMS_BP__",
                        "Set-Content -LiteralPath $generatedProbe", "SURFDUMP_SKIP_AVI_SLEEP"):
            self.assertNotIn(retired, source)
        for recorded in ("probe_composition = [ordered]@{", "composer_sha256 = $composerReceipt.sha256",
                         "pan_interval_sec = $PanIntervalSec", "raw_path = $rawSurfacePath",
                         "@{ Path = $composer; Receipt = $composerReceipt }"):
            self.assertIn(recorded, source)
        self.assertEqual(source.count("@{ Path = $composer; Receipt = $composerReceipt }"), 2)


def run_tests():
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(CompositionTests))
    if not result.wasSuccessful():
        raise AssertionError("hidden-soak probe composition failures")


if __name__ == "__main__":
    run_tests()
