"""Candidate-reference/selected-report contracts; no game or native launch."""
from __future__ import annotations

from contextlib import ExitStack
import argparse
from pathlib import Path
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import hd_multires_qualification as qualification
ORIGINAL = None


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="clash-hd-qualification-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def bundle(self, cell="framed/1920x1080"):
        profile, resolution = cell.split("/")
        original, image, probe = b"authored original fixture", b"authored image fixture", "authored canonical probe\r\n"
        source = "src/display_plan.py"
        metadata = dict(profile=profile, resolution=resolution,
            stage=qualification.candidate.stage(profile), recipe_revision=qualification.candidate.REVISION,
            bounded_small_world_integrated=profile != "classic", expanded_battle_installed=False,
            source_hashes={source: qualification.sha((ROOT / source).read_bytes())})
        files = {"base_executable": self.root / "original.exe", "executable": self.root / "candidate.exe",
                 "metadata": self.root / "candidate.json", "probe": self.root / "candidate.cdb"}
        data = dict(base_executable=original, executable=image, metadata=qualification.encode(metadata), probe=probe.encode())
        for name, path in files.items():
            path.write_bytes(data[name])
        manifest = self.root / "bundle.json"
        manifest.write_bytes(qualification.encode(dict(schema=qualification.SCHEMA, cell_id=cell,
            artifacts={name: qualification.reference(path) for name, path in files.items()})))
        return manifest, files, original, image, metadata, probe

    def context(self, original, image, metadata, probe):
        # Exercise the private reference/serialization core with authored bytes.
        # Production authentication retains its canonical issuer separately.
        stack = ExitStack()
        rebuild = lambda original, resolution, *, profile: (image, metadata, probe)
        stack.enter_context(patch.object(qualification, "authenticate_bundle", side_effect=lambda path:
            qualification._authenticate_bundle(path, rebuild, qualification.sha(original))))
        return stack

    def test_inventory_is_exactly_twelve_and_keeps_full_release_target(self):
        report = qualification.selected_report([])
        self.assertEqual(len(report["cells"]), 12)
        self.assertEqual(report["full_release_cell_count"], 36)
        self.assertEqual(report["measured_endurance_seconds_per_cell"], 17640)
        self.assertEqual(report["accepted_cells"], 0)
        self.assertTrue(all(not row["qualification_passed"] for row in report["cells"]))
        self.assertFalse(report["stable_stage_should_change"])

    def test_authentication_rebuilds_all_three_artifacts_and_never_grants_runtime(self):
        manifest, files, original, image, metadata, probe = self.bundle()
        with self.context(original, image, metadata, probe):
            context = qualification.authenticate_bundle(manifest)
        self.assertEqual(context["identity"]["cell_id"], "framed/1920x1080")
        self.assertTrue(context["source_authentication_passed"])
        for name in ("runtime_evidence_verified", "manual_input_proof", "promotion_ready"):
            self.assertIs(context[name], False)

    def test_self_consistent_substituted_candidate_still_fails_reconstruction(self):
        manifest, files, original, image, metadata, probe = self.bundle()
        files["executable"].write_bytes(b"self-consistent substitute")
        bundle = json.loads(manifest.read_bytes())
        bundle["artifacts"]["executable"] = qualification.reference(files["executable"])
        manifest.write_bytes(qualification.encode(bundle))
        with self.context(original, image, metadata, probe), self.assertRaisesRegex(ValueError, "independently reconstructed"):
            qualification.authenticate_bundle(manifest)

    def test_mixed_metadata_and_probe_fail_even_after_reference_hash_updates(self):
        for name in ("metadata", "probe"):
            manifest, files, original, image, metadata, probe = self.bundle()
            files[name].write_bytes(b"{}" if name == "metadata" else b"foreign profile probe")
            bundle = json.loads(manifest.read_bytes())
            bundle["artifacts"][name] = qualification.reference(files[name])
            manifest.write_bytes(qualification.encode(bundle))
            with self.context(original, image, metadata, probe), self.assertRaisesRegex(ValueError, "independently reconstructed"):
                qualification.authenticate_bundle(manifest)

    def test_reference_hash_failure_prevents_constructor(self):
        manifest, files, *_ = self.bundle()
        files["executable"].write_bytes(b"changed")
        with patch.object(qualification.candidate, "build_candidate", side_effect=AssertionError("must not construct")):
            with self.assertRaisesRegex(ValueError, "SHA-256 differs"):
                qualification.authenticate_bundle(manifest)

    def test_unknown_original_and_nonselected_cell_reject(self):
        manifest, files, *_ = self.bundle()
        with self.assertRaisesRegex(ValueError, "unknown original"):
            qualification.authenticate_bundle(manifest)
        bundle = json.loads(manifest.read_bytes())
        bundle["cell_id"] = "framed/3440x1440"
        manifest.write_bytes(qualification.encode(bundle))
        with self.assertRaisesRegex(ValueError, "twelve exact"):
            qualification.authenticate_bundle(manifest)

    def test_public_original_identity_and_producer_alias_cannot_select_authentication(self):
        manifest, files, original, image, metadata, probe = self.bundle()
        with patch.object(qualification.candidate, "ORIGINAL_SHA256", qualification.sha(original)), \
                patch.object(qualification.candidate, "build_candidate", side_effect=AssertionError("public producer called")):
            with self.assertRaisesRegex(ValueError, "unknown original"):
                qualification.authenticate_bundle(manifest)

    def test_duplicate_keys_links_oversize_and_output_overwrite_reject(self):
        bad = self.root / "bad.json"
        bad.write_bytes(b'{"schema":1,"schema":2}')
        with self.assertRaises(ValueError):
            qualification.read_json(bad)
        with self.assertRaisesRegex(ValueError, "bounded size"):
            qualification.read_file(bad, 1)
        existing = self.root / "retained.json"
        existing.write_bytes(b"retained")
        with self.assertRaises(FileExistsError):
            qualification._write_new(existing, b"replacement")
        self.assertEqual(existing.read_bytes(), b"retained")
        linked = self.root / "linked.json"
        os.link(existing, linked)
        with self.assertRaisesRegex(ValueError, "non-linked"):
            qualification.plain_path(linked)

    def test_duplicate_cells_are_failures_and_cannot_promote_a_partial_report(self):
        manifest, files, original, image, metadata, probe = self.bundle()
        with self.context(original, image, metadata, probe):
            report = qualification.selected_report([manifest, manifest])
        self.assertEqual(report["authenticated_cells"], 1)
        self.assertEqual(report["accepted_cells"], 0)
        self.assertTrue(any("duplicate selected cell" in error for error in report["failures"]))
        row = report["cells"][1]
        self.assertTrue(row["lanes"]["resolution_coverage"]["passed"])
        self.assertEqual(sum(lane["passed"] for lane in row["lanes"].values()), 1)
        self.assertFalse(row["candidate_bound_expanded_battle_passed"])


class OriginalAliasTests(unittest.TestCase):
    def test_public_producer_alias_cannot_authenticate_a_forged_bundle(self):
        if ORIGINAL is None:
            self.skipTest("genuine-original negative requires explicit --original-backed")
        with tempfile.TemporaryDirectory(prefix="clash-hd-original-alias-") as directory:
            root = Path(directory)
            paths = {"base_executable": ORIGINAL, "executable": root / "forged.exe",
                     "metadata": root / "forged.json", "probe": root / "forged.cdb"}
            image, probe = b"forged executable with consistent hashes", "forged canonical probe"
            metadata = dict(profile="framed", resolution="1920x1080", stage=qualification.candidate.stage("framed"),
                recipe_revision="hd_multires_v1", bounded_small_world_integrated=True,
                expanded_battle_installed=False, source_hashes={})
            paths["executable"].write_bytes(image)
            paths["metadata"].write_bytes(qualification.encode(metadata))
            paths["probe"].write_text(probe)
            manifest = root / "bundle.json"
            manifest.write_bytes(qualification.encode(dict(schema=qualification.SCHEMA, cell_id="framed/1920x1080",
                artifacts={name: qualification.reference(path) for name, path in paths.items()})))
            import src.patcher.hd_multires_issuer as public_issuer
            with patch.object(qualification.candidate, "build_candidate", return_value=(image, metadata, probe)), \
                    patch.object(public_issuer, "create_issuer", side_effect=AssertionError("public issuer called")):
                with self.assertRaisesRegex(ValueError, "independently reconstructed"):
                    qualification.authenticate_bundle(manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", type=Path)
    args, rest = parser.parse_known_args()
    ORIGINAL = args.original_backed
    unittest.main(argv=[sys.argv[0], *rest])
