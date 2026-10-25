"""Selected HD recipe replay and bounds retain the full release policy."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import resolution_release_matrix as matrix
import matrix_release_evidence as release
from test_resolution_release_matrix import SyntheticBundle, write
from test_matrix_release_evidence import Fixture as ReleaseFixture


class MultiresMatrixTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="hd-multires-matrix-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest, self.inventory = matrix._inventory(matrix.ROOT)

    def fixture(self, profile="classic", resolution="1920x1080", *, legacy=False):
        return SyntheticBundle(self.root / (profile + resolution + str(legacy)),
            self.manifest, profile, resolution, legacy=legacy)

    def test_twelve_selected_recipes_are_fixed_but_full_matrix_remains_36(self):
        self.assertEqual(len(matrix.REQUIRED_IDS), 36)
        selected = [row for row in self.inventory.values()
                    if (row.get("source_recipe") or {}).get("recipe_revision") == "hd_multires_v1"]
        self.assertEqual(len(selected), 12)
        for profile in matrix.PROFILES:
            for resolution in matrix.MULTIRES_PRESETS:
                fixture = self.fixture(profile, resolution)
                context = fixture.authenticate()
                self.assertEqual(context["identity"]["recipe_revision"], "hd_multires_v1")
                self.assertEqual(context["recipe_selection_scope"], "launcher_resolved_recipe")
                self.assertFalse(context["runtime_evidence_verified"])
        report = matrix.evaluate_matrix()
        self.assertFalse(report["passed"])
        self.assertEqual(len(report["cells"]), 36)
        self.assertEqual(len(release.UNIMPLEMENTED_LANES), 15)

    def test_mixed_profile_recipe_stage_probe_and_stale_sources_fail(self):
        for change in ("profile", "recipe", "stage", "probe", "source"):
            fixture = self.fixture("modalwidgets")
            if change == "probe":
                fixture.spec["probe"] = write(Path(fixture.spec["probe"]["path"]), b"wrong probe")
            elif change == "source":
                Path(fixture.source["path"]).write_bytes(b"changed source closure")
            else:
                values = dict(fixture.metadata)
                values[{"profile": "profile", "recipe": "recipe_revision", "stage": "stage"}[change]] = {
                    "profile": "framed", "recipe": "complete_hd_v1", "stage": matrix.evidence.STAGE}[change]
                fixture.spec["metadata"] = write(Path(fixture.spec["metadata"]["path"]), values)
            with self.subTest(change=change), self.assertRaises(ValueError):
                fixture.authenticate()

    def test_new_framed_recipe_cannot_borrow_legacy_timestamp_exception(self):
        fixture = self.fixture("framed")
        fixture.spec["metadata"] = write(Path(fixture.spec["metadata"]["path"]),
            dict(fixture.metadata, generated_at="unapproved extra metadata"))
        with self.assertRaisesRegex(ValueError, "metadata differs"):
            fixture.authenticate()
        legacy = self.fixture("framed", legacy=True)
        legacy.spec["metadata"] = write(Path(legacy.spec["metadata"]["path"]),
            dict(legacy.metadata, generated_at="legacy producer timestamp"))
        self.assertTrue(legacy.authenticate()["byte_rebuild_passed"])
        self.assertEqual(legacy.authenticate()["recipe_selection_scope"], "legacy_source_recipe")

    def test_large_metadata_bound_is_scoped_to_new_selected_recipe(self):
        for legacy in (False, True):
            fixture = self.fixture("completehd", legacy=legacy)
            padded = json.dumps(fixture.metadata).encode() + b" " * 2048
            fixture.spec["metadata"] = write(Path(fixture.spec["metadata"]["path"]), padded)
            with patch.object(matrix, "MAX_JSON_BYTES", 1024), patch.object(matrix, "MULTIRES_METADATA_BYTES", 4096):
                if legacy:
                    with self.assertRaisesRegex(ValueError, "legacy.*unchanged JSON bound"):
                        fixture.authenticate()
                else:
                    self.assertTrue(fixture.authenticate()["byte_rebuild_passed"])
        fixture = self.fixture("framed")
        fixture.spec["metadata"] = write(Path(fixture.spec["metadata"]["path"]), b" " * 4097)
        with patch.object(matrix, "MULTIRES_METADATA_BYTES", 4096), self.assertRaisesRegex(ValueError, "bounded nonempty"):
            fixture.authenticate()

    def test_large_probe_uses_new_bound_during_initial_and_final_rereads(self):
        for legacy in (False, True):
            fixture = self.fixture("classic", legacy=legacy)
            fixture.probe = "p" * 192
            fixture.spec["probe"] = write(Path(fixture.spec["probe"]["path"]), fixture.probe.encode())
            with patch.object(matrix, "MAX_ARTIFACT_BYTES", 128), patch.object(matrix, "MULTIRES_PROBE_BYTES", 256):
                if legacy:
                    with self.assertRaisesRegex(ValueError, "bounded nonempty"):
                        fixture.authenticate()
                else:
                    self.assertTrue(fixture.authenticate()["byte_rebuild_passed"])
        identity = {"profile": "classic", "resolution": "1920x1080", "recipe_revision": "hd_multires_v1",
                    "stage": matrix.evidence.STABLE_STAGE + "-classic-hd-multires-validation"}
        self.assertEqual(matrix.candidate_artifact_limit(identity, "metadata"), 16 * 1024 * 1024)
        self.assertEqual(matrix.candidate_artifact_limit(identity, "probe"), 64 * 1024 * 1024)
        for change in ({"profile": "framed"}, {"resolution": "3440x1440"}, {"recipe_revision": "complete_hd_v1"}):
            self.assertEqual(matrix.candidate_artifact_limit(identity | change, "probe"), matrix.MAX_JSON_BYTES)

    def test_private_reconstruction_ignores_public_producer_and_issuer_aliases(self):
        import src.patcher.hd_multires_candidate as producer
        import src.patcher.hd_multires_issuer as issuer
        trap = Mock(side_effect=AssertionError("mutable public issuer called"))
        selection = SimpleNamespace(recipe_revision="hd_multires_v1",
            stage=matrix.evidence.STABLE_STAGE + "-classic-hd-multires-validation")
        with patch.object(producer, "build_candidate", trap), patch.object(producer, "source_hashes", trap), \
             patch.object(issuer, "create_issuer", trap), patch.object(matrix, "_multires_recipe_reconstructor", trap):
            with self.assertRaisesRegex(ValueError, "unknown original"):
                matrix._rebuild("classic", "1920x1080", b"invalid original", selection, matrix.ROOT)
        trap.assert_not_called()

    def test_matrix_cell_final_recheck_accepts_large_new_probe_without_runtime_credit(self):
        fixture = ReleaseFixture(self.root / "release-large-probe", "classic", "1920x1080")
        fixture.probe = "synthetic probe; no native observations\n" + "x" * (release.MAX_JSON_BYTES + 1)
        fixture.metadata["probe_sha256"] = matrix.sha(fixture.probe.encode())
        fixture.spec["probe"] = write(Path(fixture.spec["probe"]["path"]), fixture.probe.encode())
        fixture.spec["metadata"] = write(Path(fixture.spec["metadata"]["path"]), fixture.metadata)
        with fixture.runtime_free_context():
            context = matrix.authenticate_candidate(fixture.id, fixture.spec, fixture.external,
                fixture.manifest, repo_root=fixture.repo)
        identity = context["identity"] | {"cell_id": fixture.id, "features": {"minimap_viewport": False},
            "launcher_manifest_sha256": fixture.catalog_ref["sha256"],
            "source_closure_sha256": matrix.sha(matrix.canonical(context["source_hashes"]).encode())}
        fixture.index["candidate"] = fixture.spec
        for name, report in fixture.reports.items():
            report["identity"] = identity
            fixture.save_lane(name)
        fixture.save_release()
        report = fixture.evaluate()
        self.assertTrue(report["candidate_authentication_passed"], report["failures"])
        self.assertTrue(report["source_consistency_passed"], report["failures"])
        self.assertTrue(report["lanes"]["resolution_coverage"]["passed"], report["failures"])
        self.assertFalse(report["passed"])
        for name in release.UNIMPLEMENTED_LANES:
            self.assertFalse(report["lanes"][name]["implemented"])
            self.assertFalse(report["lanes"][name]["passed"])

    def test_wrong_profile_preset_stage_or_root_rejects_before_build(self):
        for profile, resolution, stage, root in (
                ("unknown", "1920x1080", matrix.evidence.STABLE_STAGE + "-classic-hd-multires-validation", matrix.ROOT),
                ("classic", "3440x1440", matrix.evidence.STABLE_STAGE + "-classic-hd-multires-validation", matrix.ROOT),
                ("classic", "1920x1080", matrix.evidence.STAGE, matrix.ROOT),
                ("classic", "1920x1080", matrix.evidence.STABLE_STAGE + "-classic-hd-multires-validation", self.root)):
            with self.subTest(profile=profile, resolution=resolution, stage=stage), self.assertRaisesRegex(ValueError, "exact fixed|fixed repository"):
                matrix._rebuild(profile, resolution, b"invalid original",
                    SimpleNamespace(recipe_revision="hd_multires_v1", stage=stage), root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
