#!/usr/bin/env python3
"""Tiny synthetic matrix-cell fixtures, never native or release acceptance.

Only the existing private candidate reconstruction seam, known-original hash
and isolated fixture root are substituted. Inventory, candidate authentication,
JSON/ref parsing, resolution replay and all negative grading remain real.
"""
from __future__ import annotations

import contextlib
import copy
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import matrix_release_evidence as release
import resolution_release_matrix as matrix
from test_resolution_release_matrix import SyntheticBundle, write


REAL_ROOT = matrix.ROOT
CATALOG_BYTES = (REAL_ROOT / "src/launcher/resolutions.json").read_bytes()
PRODUCER_BYTES = (REAL_ROOT / release.PRODUCER).read_bytes()


class Fixture(SyntheticBundle):
    def __init__(self, root: Path, profile="classic", resolution="800x600", *, successor=None, catalog=None):
        manifest = json.loads(CATALOG_BYTES if catalog is None else catalog)
        super().__init__(root, manifest, profile, resolution, successor=successor)
        self.catalog_ref = write(self.repo / "src/launcher/resolutions.json", CATALOG_BYTES if catalog is None else catalog)
        self.producer_ref = write(self.repo / release.PRODUCER, PRODUCER_BYTES)
        self.index = {"schema": release.RELEASE_SCHEMA, "cell_id": self.id, "candidate": copy.deepcopy(self.spec),
                      "launcher_manifest": self.catalog_ref, "lanes": {}}
        with self.runtime_free_context():
            context = matrix.authenticate_candidate(self.id, self.spec, self.external, self.manifest, repo_root=self.repo)
            context["identity"] = {**context["identity"], "cell_id": self.id,
                                   "features": copy.deepcopy(self.manifest["profiles"][profile]["features"]),
                                   "launcher_manifest_sha256": self.catalog_ref["sha256"],
                                   "source_closure_sha256": matrix.sha(matrix.canonical(context["source_hashes"]).encode())}
            self.identity = context["identity"]
            checks = release._coverage_checks(context, self.manifest)
        self.reports = {}
        for name in release.REQUIRED_LANES:
            self.reports[name] = {
                "schema": release.LANE_SCHEMA, "lane": name, "identity": copy.deepcopy(self.identity),
                "evidence_class": "repo_resolution_coverage" if name == "resolution_coverage" else "invented_green_runtime",
                "producer": self.producer_ref, "source_artifacts": [self.catalog_ref],
                "checks": copy.deepcopy(checks) if name == "resolution_coverage" else {
                    key: {"passed": True, "failures": []} for key in matrix.evidence.LANES[name][1]},
                "passed": True, "failures": [], "stable_stage_should_change": False,
                "release_resolutions": [resolution],
            }
            self.save_lane(name)
        self.save_release()

    @contextlib.contextmanager
    def runtime_free_context(self):
        # The public API has no root/builder/context override. This explicit
        # test-only namespace contains real tiny source/catalog files.
        with self.authentication(), patch.object(matrix, "ROOT", self.repo):
            yield

    def save_lane(self, name):
        self.index["lanes"][name] = write(self.external / f"{name}.json", self.reports[name])

    def save_release(self):
        self.release_ref = write(self.external / "release.json", self.index)
        self.row = {"id": self.id, "candidate": self.spec, "release_index": self.release_ref}
        self.save_matrix([self.row])

    def evaluate(self):
        with self.runtime_free_context():
            return release.evaluate_release_manifest(Path(self.release_ref["path"]))


class MatrixReleaseTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="matrix-cell-release-tiny-")
        self.addCleanup(self.scratch.cleanup)
        self.directory = Path(self.scratch.name)
        self.count = 0

    def fixture(self, *args, **kwargs):
        self.count += 1
        return Fixture(self.directory / f"case-{self.count}", *args, **kwargs)

    def assert_blocked(self, report):
        for name in ("passed", "evidence_ready", "eligible_for_stable_promotion", "promotion_approved", "promotion_ready",
                     "runtime_evidence_verified", "whole_hd_acceptance_evaluated", "full_game_complete", "stable_stage_should_change"):
            self.assertIs(report[name], False, name)
        self.assertEqual(report["required_lanes"], list(matrix.evidence.LANES))
        self.assertEqual(set(report["lanes"]), set(matrix.evidence.LANES))
        self.assertEqual(len(report["unimplemented_lane_verifiers"]), 15)
        self.assertIn("panel_command", report["unimplemented_lane_verifiers"])
        self.assertEqual(report["unimplemented_acceptance_requirements"], ["candidate_bound_expanded_battle"])
        self.assertTrue(report["failures"])

    def test_public_api_has_no_context_builder_verifier_or_root_override(self):
        self.assertEqual(list(inspect.signature(release.evaluate_release_manifest).parameters), ["path"])
        self.assertEqual(len(release.REQUIRED_LANES), 16)
        self.assertEqual(len(release.UNIMPLEMENTED_LANES), 15)

    def test_real_replay_accepts_all_32_advertised_canonical_source_contexts_only(self):
        manifest = json.loads(CATALOG_BYTES)
        checked = 0
        for profile in matrix.PROFILES:
            for resolution in matrix.PRESETS:
                if resolution not in manifest["profiles"][profile]["resolutions"]:
                    continue
                with self.subTest(profile=profile, resolution=resolution):
                    fixture = self.fixture(profile, resolution)
                    report = fixture.evaluate()
                    self.assert_blocked(report)
                    self.assertTrue(report["candidate_authentication_passed"], report["failures"])
                    self.assertTrue(report["source_consistency_passed"], report["failures"])
                    self.assertTrue(report["lanes"]["resolution_coverage"]["passed"], report["failures"])
                    self.assertEqual(report["candidate_context"]["identity"], fixture.identity)
                    checked += 1
        self.assertEqual(checked, 32)

    def test_classic_stable_and_wide_features_are_not_complete_hd_defaults(self):
        for resolution in ("800x600", "1280x720"):
            fixture = self.fixture("classic", resolution)
            report = fixture.evaluate()
            identity = report["candidate_context"]["identity"]
            self.assertEqual(identity["features"], {"minimap_viewport": False})
            self.assertTrue(report["lanes"]["resolution_coverage"]["passed"], report["failures"])
            self.assertEqual(identity["recipe_revision"], "classic-frozen-800-v1" if resolution == "800x600" else "classic_menu_widgets_v1")
            if resolution == "800x600":
                self.assertIsNone(identity["probe_sha256"])

    def test_all_36_unregistered_successors_authenticate_without_launcher_coverage(self):
        for revision, selected in matrix.VALIDATION_RECIPES.items():
            for resolution in matrix.PRESETS:
                with self.subTest(revision=revision, resolution=resolution):
                    fixture = self.fixture(selected["profile"], resolution, successor=revision)
                    report = fixture.evaluate()
                    self.assert_blocked(report)
                    self.assertTrue(report["candidate_authentication_passed"], report["failures"])
                    coverage = report["lanes"]["resolution_coverage"]
                    self.assertFalse(coverage["passed"])
                    self.assertFalse(coverage["checks"]["advertised_resolution_matches"]["passed"])

    def test_fabricated_green_runtime_and_legacy_panel_never_register(self):
        fixture = self.fixture("completehd", "1920x1080")
        fixture.reports["panel_command"]["evidence_class"] = "observed_relocated_panel_native_callback"
        fixture.save_lane("panel_command")
        fixture.save_release()
        report = fixture.evaluate()
        self.assert_blocked(report)
        for name in release.UNIMPLEMENTED_LANES:
            self.assertFalse(report["lanes"][name]["passed"])
            self.assertFalse(report["lanes"][name]["implemented"])
            self.assertIn(f"matrix-context source-artifact verifier is not implemented for {name}", report["lanes"][name]["failures"])

    def test_missing_and_extra_lanes_preserve_all_16_requirements(self):
        for action in ("missing", "extra"):
            fixture = self.fixture()
            if action == "missing":
                del fixture.index["lanes"]["geometry"]
            else:
                fixture.index["lanes"]["optional_shortcut"] = fixture.index["lanes"]["resolution_coverage"]
            fixture.save_release()
            report = fixture.evaluate()
            self.assert_blocked(report)
            self.assertIn("matrix-cell release must contain exactly all 16 fixed acceptance lanes", report["failures"])

    def test_report_supplied_context_policy_verifier_and_promotion_are_rejected(self):
        for key, value in (("candidate_context", {"byte_rebuild_passed": True}), ("verifier", "arbitrary.module"),
                           ("required_lanes", ["resolution_coverage"]), ("passed", True),
                           ("promotion_decision", {"approved": True})):
            fixture = self.fixture()
            fixture.index[key] = value
            fixture.save_release()
            report = fixture.evaluate()
            self.assert_blocked(report)
            self.assertFalse(report["candidate_authentication_passed"])

    def test_wrong_cell_profile_custom_size_and_metadata_are_rejected(self):
        for cell_id in ("framed/800x600", "classic/1024x768", "classic/802x602", "unknown/800x600", True):
            fixture = self.fixture()
            fixture.index["cell_id"] = cell_id
            fixture.save_release()
            report = fixture.evaluate()
            self.assert_blocked(report)
            self.assertFalse(report["candidate_authentication_passed"], report["failures"])

    def test_rehashed_original_candidate_metadata_probe_and_source_substitutions_fail(self):
        for name in ("original", "candidate", "metadata", "probe", "source"):
            fixture = self.fixture("completehd", "1920x1080")
            if name == "source":
                Path(fixture.source["path"]).write_bytes(b"changed synthetic source\n")
            else:
                key = {"original": "base_executable", "candidate": "executable", "metadata": "metadata", "probe": "probe"}[name]
                target = Path(fixture.index["candidate"][key]["path"])
                changed = dict(fixture.metadata, resolution="1024x768") if name == "metadata" else b"rehashed changed synthetic artifact"
                fixture.index["candidate"][key] = write(target, changed)
            fixture.save_release()
            report = fixture.evaluate()
            self.assert_blocked(report)
            self.assertFalse(report["candidate_authentication_passed"], (name, report["failures"]))

    def test_missing_required_and_invented_classic_probe_fail(self):
        complete = self.fixture("completehd", "1920x1080")
        del complete.index["candidate"]["probe"]
        complete.save_release()
        classic = self.fixture()
        classic.index["candidate"]["probe"] = write(classic.external / "invented.cdb", b"invented synthetic probe")
        classic.save_release()
        for fixture in (complete, classic):
            report = fixture.evaluate()
            self.assert_blocked(report)
            self.assertFalse(report["candidate_authentication_passed"])

    def test_typed_features_source_closure_and_identity_substitutions_fail(self):
        for key, value in (("features", {"minimap_viewport": 0}), ("source_closure_sha256", "0" * 64),
                           ("profile", "framed"), ("resolution", "1024x768"), ("stage", "wrong"),
                           ("recipe_revision", "wrong"), ("candidate_sha256", "0" * 64)):
            fixture = self.fixture()
            fixture.reports["resolution_coverage"]["identity"][key] = value
            fixture.save_lane("resolution_coverage")
            fixture.save_release()
            report = fixture.evaluate()
            self.assert_blocked(report)
            self.assertFalse(report["lanes"]["resolution_coverage"]["passed"])

    def test_resolution_claims_producer_source_and_types_are_replayed(self):
        for fault in ("green_number", "missing_check", "extra_check", "wrong_producer", "wrong_source", "wrong_resolution"):
            fixture = self.fixture()
            lane = fixture.reports["resolution_coverage"]
            if fault == "green_number":
                lane["checks"]["candidate_byte_gate"]["passed"] = 1
            elif fault == "missing_check":
                del lane["checks"]["candidate_byte_gate"]
            elif fault == "extra_check":
                lane["checks"]["runtime_pass"] = {"passed": True, "failures": []}
            elif fault == "wrong_producer":
                lane["producer"] = fixture.source
            elif fault == "wrong_source":
                lane["source_artifacts"] = [write(fixture.external / "copied-catalog.json", CATALOG_BYTES)]
            else:
                lane["release_resolutions"] = ["800x600", "1024x768"]
            fixture.save_lane("resolution_coverage")
            fixture.save_release()
            report = fixture.evaluate()
            self.assertFalse(report["lanes"]["resolution_coverage"]["passed"], fault)

    def test_copied_launcher_manifest_cannot_replace_actual_catalog(self):
        fixture = self.fixture()
        fixture.index["launcher_manifest"] = write(fixture.external / "lookalike-catalog.json", CATALOG_BYTES)
        fixture.save_release()
        report = fixture.evaluate()
        self.assert_blocked(report)
        self.assertFalse(report["candidate_authentication_passed"])
        self.assertTrue(any("actual current repository launcher manifest" in item for item in report["failures"]))

    def test_invalid_actual_launcher_features_defaults_stage_and_promotions_fail(self):
        for fault in ("features", "default", "stage", "status"):
            fixture = self.fixture()
            manifest = copy.deepcopy(fixture.manifest)
            if fault == "features":
                manifest["profiles"]["classic"]["features"]["minimap_viewport"] = 0
            elif fault == "default":
                manifest["default"] = manifest["profiles"]["classic"]["default"] = "1024x768"
            elif fault == "stage":
                manifest["stable_stage"] = manifest["profiles"]["classic"]["stage"] = "wrong-stable-stage"
            else:
                entry = copy.deepcopy(manifest["resolutions"]["800x600"])
                entry["status"] = "validated"
                manifest["resolutions"]["1024x768"] = entry
                manifest["profiles"]["classic"]["resolutions"]["1024x768"] = copy.deepcopy(entry)
            fixture.index["launcher_manifest"] = write(Path(fixture.catalog_ref["path"]), manifest)
            fixture.save_release()
            report = fixture.evaluate()
            self.assert_blocked(report)
            self.assertFalse(report["lanes"]["resolution_coverage"]["passed"], fault)

    def test_stale_index_lane_candidate_and_catalog_references_fail(self):
        for role in ("lane", "candidate", "catalog"):
            fixture = self.fixture()
            ref = fixture.index["lanes"]["resolution_coverage"] if role == "lane" else (
                fixture.index["candidate"]["metadata"] if role == "candidate" else fixture.catalog_ref)
            target = Path(ref["path"])
            target.write_bytes(target.read_bytes() + b"\n")
            report = fixture.evaluate()
            self.assert_blocked(report)
            self.assertFalse(report["lanes"]["resolution_coverage"]["passed"], role)
        fixture = self.fixture()
        context = fixture.authenticate()
        Path(fixture.release_ref["path"]).write_bytes(Path(fixture.release_ref["path"]).read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            matrix._replay_release(fixture.release_ref, fixture.external, context)

    def test_malformed_duplicate_nonfinite_deep_or_nonobject_index_fails_without_raise(self):
        invalid = (b'{"schema":"a","schema":"b"}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e9999}',
                   b'{"x":' + b'[' * 10000 + b'0' + b']' * 10000 + b'}',
                   b'{"x":' + b'[' * 64 + b'0' + b']' * 64 + b'}', b'[]', b'null', b'false', b'{', b'\xff', b'')
        target = self.directory / "invalid.json"
        for raw in invalid:
            target.write_bytes(raw)
            report = release.evaluate_release_manifest(target)
            self.assert_blocked(report)
            self.assertFalse(report["candidate_authentication_passed"])

    def test_malformed_lane_and_missing_index_are_structured_failures(self):
        fixture = self.fixture()
        ref = write(Path(fixture.index["lanes"]["resolution_coverage"]["path"]), b'{"passed":true,"passed":true}')
        fixture.index["lanes"]["resolution_coverage"] = ref
        fixture.save_release()
        report = fixture.evaluate()
        self.assertFalse(report["lanes"]["resolution_coverage"]["passed"])
        self.assert_blocked(release.evaluate_release_manifest(self.directory / "missing.json"))

    def test_catalog_index_candidate_and_sources_are_rechecked_after_lane_replay(self):
        for role in ("catalog", "index", "candidate", "source"):
            fixture = self.fixture()
            original_checks = release._coverage_checks
            target = {"catalog": Path(fixture.catalog_ref["path"]), "index": Path(fixture.release_ref["path"]),
                      "candidate": Path(fixture.spec["executable"]["path"]), "source": Path(fixture.source["path"])}[role]

            def change_after_real_replay(context, manifest):
                measured = original_checks(context, manifest)
                target.write_bytes(target.read_bytes() + b"\n")
                return measured

            with patch.object(release, "_coverage_checks", side_effect=change_after_real_replay):
                report = fixture.evaluate()
            self.assert_blocked(report)
            self.assertFalse(report["source_consistency_passed"], role)
            self.assertFalse(report["candidate_authentication_passed"], role)
            self.assertFalse(report["lanes"]["resolution_coverage"]["passed"], role)
            self.assertTrue(any("source recheck" in item for item in report["failures"]), role)

    def test_public_calls_reauthenticate_not_cache_supplied_context(self):
        fixture = self.fixture()
        original = matrix.authenticate_candidate
        with fixture.runtime_free_context(), patch.object(matrix, "authenticate_candidate", wraps=original) as authenticate:
            first = release.evaluate_release_manifest(Path(fixture.release_ref["path"]))
            second = release.evaluate_release_manifest(Path(fixture.release_ref["path"]))
        self.assertTrue(first["candidate_authentication_passed"])
        self.assertTrue(second["candidate_authentication_passed"])
        self.assertEqual(authenticate.call_count, 2)

    def test_context_extension_failure_cannot_publish_partial_source_authority(self):
        fixture = self.fixture()
        original_sha = matrix.sha
        source_bytes = matrix.canonical(fixture.source_hashes).encode()

        def reject_source_digest(raw):
            if raw == source_bytes:
                raise ValueError("synthetic closure digest failure after actual authentication")
            return original_sha(raw)

        with patch.object(matrix, "sha", side_effect=reject_source_digest):
            report = fixture.evaluate()
        self.assert_blocked(report)
        self.assertFalse(report["candidate_authentication_passed"])
        self.assertFalse(report["source_consistency_passed"])
        self.assertEqual(report["candidate_context"], {})

    def test_actual_matrix_dispatch_rejects_deep_and_oversized_indexes_without_raise(self):
        for raw in (b'{"schema":"matrix_cell_release_manifest_v1","x":' + b'[' * 10000 + b'0' + b']' * 10000 + b'}',
                    b'{"schema":"matrix_cell_release_manifest_v1","x":"' + b'a' * release.MAX_JSON_BYTES + b'"}'):
            fixture = self.fixture()
            fixture.release_ref = write(Path(fixture.release_ref["path"]), raw)
            fixture.row["release_index"] = fixture.release_ref
            fixture.save_matrix([fixture.row])
            with fixture.runtime_free_context():
                report = matrix.evaluate_matrix(fixture.matrix_path, repo_root=fixture.repo)
            self.assertFalse(report["passed"])
            self.assertTrue(any("release acceptance" in item for item in report["cells"][fixture.id]["failures"]))
            self.assertEqual(len(report["matrix_context_unimplemented_lane_verifiers"]), 15)
            self.assertEqual(report["matrix_context_lane_verifiers"], ["resolution_coverage"])

    def test_failed_outer_candidate_still_bounds_and_rejects_release_json(self):
        for raw in (b'{"schema":"matrix_cell_release_manifest_v1","x":' + b'[' * 10000 + b'0' + b']' * 10000 + b'}',
                    b'{"schema":"matrix_cell_release_manifest_v1","x":"' + b'a' * release.MAX_JSON_BYTES + b'"}'):
            fixture = self.fixture()
            fixture.release_ref = write(Path(fixture.release_ref["path"]), raw)
            fixture.row["release_index"] = fixture.release_ref
            fixture.row["candidate"] = {}
            fixture.save_matrix([fixture.row])
            with fixture.runtime_free_context():
                report = matrix.evaluate_matrix(fixture.matrix_path, repo_root=fixture.repo)
            self.assertFalse(report["passed"])
            cell = report["cells"][fixture.id]
            self.assertFalse(cell["candidate_authentication_passed"])
            self.assertTrue(any("release acceptance" in item for item in cell["failures"]))

    def test_actual_outer_top_index_and_candidate_metadata_malformed_are_structured(self):
        malformed = (b'{"x":' + b'[' * 10000 + b'0' + b']' * 10000 + b'}',
                     b'{"x":' + b'[' * 64 + b'0' + b']' * 64 + b'}',
                     b'{"x":"' + b'a' * matrix.MAX_JSON_BYTES + b'"}')
        for raw in malformed:
            fixture = self.fixture()
            write(fixture.matrix_path, raw)
            with fixture.runtime_free_context():
                report = matrix.evaluate_matrix(fixture.matrix_path, repo_root=fixture.repo)
            self.assertFalse(report["passed"])
            self.assertEqual(report["authenticated_candidate_count"], 0)
            fixture.save_matrix([fixture.row])
            fixture.row["candidate"]["metadata"] = write(Path(fixture.spec["metadata"]["path"]), raw)
            fixture.save_matrix([fixture.row])
            with fixture.runtime_free_context():
                report = matrix.evaluate_matrix(fixture.matrix_path, repo_root=fixture.repo)
            self.assertFalse(report["passed"])
            self.assertFalse(report["cells"][fixture.id]["candidate_authentication_passed"])
            self.assertTrue(any("candidate authentication" in item for item in report["cells"][fixture.id]["failures"]))

    def test_initial_matrix_artifact_and_json_reads_are_bounded_on_tiny_files(self):
        raw = b"tiny synthetic artifact longer than the lowered read cap"
        reference = write(self.directory / "bounded-artifact.txt", raw)
        with patch.object(matrix, "MAX_ARTIFACT_BYTES", 8), self.assertRaisesRegex(ValueError, "bounded nonempty"):
            matrix.read_reference(reference, self.directory)
        self.assertEqual(Path(reference["path"]).read_bytes(), raw)
        reference = write(self.directory / "bounded-object.json", {"fixture": "tiny actual JSON"})
        with patch.object(matrix, "MAX_JSON_BYTES", 8), self.assertRaisesRegex(ValueError, "bounded nonempty"):
            matrix.read_reference(reference, self.directory, object_required=True)
        fixture = self.fixture("framed", "1280x720")
        with fixture.runtime_free_context(), patch.object(matrix, "MAX_ARTIFACT_BYTES", 8):
            report = matrix.evaluate_matrix(fixture.matrix_path, repo_root=fixture.repo)
        self.assertFalse(report["cells"][fixture.id]["candidate_authentication_passed"])
        self.assertTrue(any("bounded nonempty" in item for item in report["cells"][fixture.id]["failures"]))

    def test_matrix_dispatch_reauthenticates_exact_cell_and_artifact_identity(self):
        fixture = self.fixture("framed", "1280x720")
        with fixture.runtime_free_context():
            context = matrix.authenticate_candidate(fixture.id, fixture.spec, fixture.external, fixture.manifest, repo_root=fixture.repo)
            report = matrix._replay_release(fixture.release_ref, fixture.external, context)
        self.assert_blocked(report)
        self.assertTrue(report["lanes"]["resolution_coverage"]["passed"])
        other = copy.deepcopy(context)
        other["identity"]["profile"] = "classic"
        with fixture.runtime_free_context(), self.assertRaisesRegex(ValueError, "selected matrix cell"):
            matrix._replay_release(fixture.release_ref, fixture.external, other)
        fixture.index["candidate"]["executable"] = write(fixture.external / "other.exe", fixture.image)
        fixture.save_release()
        with fixture.runtime_free_context(), self.assertRaisesRegex(ValueError, "rebinds"):
            matrix._replay_release(fixture.release_ref, fixture.external, context)

    def test_matrix_evaluation_uses_new_context_without_legacy_panel_or_release_calls(self):
        fixture = self.fixture("modalwidgets", "1280x960")
        with fixture.runtime_free_context(), patch.object(matrix.evidence, "evaluate_release_manifest") as legacy:
            report = matrix.evaluate_matrix(fixture.matrix_path, repo_root=fixture.repo)
        legacy.assert_not_called()
        self.assertEqual(report["authenticated_candidate_count"], 1)
        cell = report["cells"][fixture.id]
        self.assertTrue(cell["release_evaluation"]["lanes"]["resolution_coverage"]["passed"], cell["failures"])
        self.assertEqual(len(cell["release_evaluation"]["unimplemented_lane_verifiers"]), 15)
        self.assertFalse(cell["passed"])
        self.assertFalse(report["evidence_ready"])


TEST_COUNT = unittest.defaultTestLoader.loadTestsFromTestCase(MatrixReleaseTests).countTestCases()


def run_tests():
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(MatrixReleaseTests))
    if not result.wasSuccessful() or result.skipped:
        raise AssertionError("matrix-cell source release fixture failures")
    return result.testsRun


if __name__ == "__main__":
    run_tests()
