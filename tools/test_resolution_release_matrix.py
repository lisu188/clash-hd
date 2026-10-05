#!/usr/bin/env python3
"""Synthetic offline matrix fixtures; no runtime proof."""
from __future__ import annotations

import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import resolution_release_matrix as matrix


def write(path: Path, value) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, bytes) else (json.dumps(value) + "\n").encode()
    path.write_bytes(data)
    return {"path": str(path), "sha256": matrix.sha(data)}


class SyntheticBundle:
    def __init__(self, root: Path, manifest: dict, profile="completehd", resolution="1920x1080", *, successor=None):
        self.root, self.manifest = root, manifest
        self.repo, self.external = root / "repo", root / "external"
        self.id = f"{profile}/{resolution}"
        from src.launcher import presets
        if successor is None:
            self.display = presets.resolve_plan(renderer=profile, resolution=resolution, manifest=manifest)
        else:
            selected = matrix.VALIDATION_RECIPES[successor]
            self.display = SimpleNamespace(stage=selected["stage"], recipe_revision=successor)
        self.original = b"fixture-only original, not game material"
        self.image = self.original + b"synthetic candidate change"
        self.probe = None if profile == "classic" and resolution == "800x600" else "fixture-only canonical probe\n"
        self.source = write(self.repo / "tools/fixture_producer.py", b"# synthetic producer source\n")
        self.source_hashes = {"tools/fixture_producer.py": self.source["sha256"]}
        self.metadata = {"schema": "synthetic-authentication-fixture-only", "stage": self.display.stage,
                         "resolution": resolution, "recipe_revision": self.display.recipe_revision,
                         "candidate_sha256": matrix.sha(self.image), "base_sha256": matrix.sha(self.original),
                         "source_hashes": self.source_hashes, "probe_sha256": matrix.sha(self.probe.encode()) if self.probe else None}
        self.spec = {"base_executable": write(self.external / "base.exe", self.original),
                     "executable": write(self.external / "candidate.exe", self.image),
                     "metadata": write(self.external / "candidate.json", self.metadata)}
        if self.probe is not None:
            self.spec["probe"] = write(self.external / "candidate.cdb", self.probe.encode())
        self.index = {"schema": matrix.evidence.RELEASE_SCHEMA, "candidate": copy.deepcopy(self.spec), "lanes": {}}
        self.release_ref = write(self.external / "release.json", self.index)
        self.matrix_path = self.external / "matrix.json"
        self.row = {"id": self.id, "candidate": self.spec, "release_index": self.release_ref}
        self.save_matrix([self.row])

    def save_matrix(self, rows):
        write(self.matrix_path, {"schema": matrix.MATRIX_SCHEMA, "rows": rows})

    def rebuilt(self, *_):
        return {"image": self.image, "metadata": copy.deepcopy(self.metadata), "probe": self.probe,
                "projection": getattr(self, "projection", False), "source_hashes": self.source_hashes.copy()}

    @contextlib.contextmanager
    def authentication(self):
        with patch.object(matrix.evidence, "BASE_SHA256", matrix.sha(self.original)), \
             patch.object(matrix, "CANDIDATE_ROOT", self.external), \
             patch.object(matrix, "_rebuild", side_effect=self.rebuilt):
            yield

    def authenticate(self):
        with self.authentication():
            return matrix.authenticate_candidate(self.id, self.spec, self.external, self.manifest, repo_root=self.repo)


class MatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.inventory = matrix._inventory(matrix.ROOT)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="clash-hd-release-matrix-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, profile="completehd", resolution="1920x1080"):
        return SyntheticBundle(self.root, self.manifest, profile, resolution)

    def evaluate_rows(self, rows):
        path = self.root / "matrix.json"
        write(path, {"schema": matrix.MATRIX_SCHEMA, "rows": rows})
        return matrix.evaluate_matrix(path)

    def assert_blocked(self, report):
        for field in ("passed", "evidence_ready", "promotion_approved", "promotion_ready", "full_game_complete", "stable_stage_should_change"):
            self.assertIs(report[field], False, field)
        self.assertEqual(len(report["cells"]), 36)
        self.assertTrue(report["failures"])

    def test_fixed_preset_matrix(self):
        self.assertEqual(len(matrix.REQUIRED_IDS), 36)
        self.assertEqual(len(set(matrix.REQUIRED_IDS)), 36)
        self.assertEqual({key.split("/")[0] for key in matrix.REQUIRED_IDS}, set(matrix.PROFILES))
        self.assertFalse(any("802x602" in key for key in matrix.REQUIRED_IDS))
        self.assertEqual(len(matrix.REQUIRED_ACCEPTANCE), 17)

    def test_inventory_absent_presets_and_wide_classic(self):
        self.assertEqual(sum(row["preset_advertised"] for row in self.inventory.values()), 28)
        missing = {key for key, row in self.inventory.items() if not row["preset_advertised"]}
        self.assertEqual(missing, {f"{p}/{r}" for p in ("completehd", "modalwidgets")
                                  for r in ("1366x768", "2560x1440", "3440x1440", "3840x2160")})
        self.assertEqual(self.inventory["classic/800x600"]["source_recipe"]["recipe_revision"], "classic-frozen-800-v1")
        self.assertEqual(self.inventory["classic/1280x720"]["source_recipe"]["recipe_revision"], "classic_menu_widgets_v1")
        self.assertIs(self.inventory["completehd/3840x2160"]["recipe_eligible"], False)

    def test_missing_manifest_fails(self):
        report = matrix.evaluate_matrix()
        self.assert_blocked(report)
        self.assertEqual(report["authenticated_candidate_count"], 0)
        self.assertEqual(len(report["unimplemented_lane_verifiers"]), 14)
        for row in report["cells"].values():
            self.assertIn("candidate-bound expanded-battle production acceptance verifier is not implemented", row["failures"])

    def test_missing_explicit_manifest_fails(self):
        report = matrix.evaluate_matrix(self.root / "missing.json")
        self.assert_blocked(report)
        self.assertTrue(any("missing.json" in error for error in report["failures"]))

    def test_legacy_schema_is_not_matrix(self):
        path = self.root / "legacy.json"
        write(path, {"schema": matrix.evidence.RELEASE_SCHEMA, "passed": True})
        report = matrix.evaluate_matrix(path)
        self.assert_blocked(report)
        self.assertTrue(any("supported schema" in error for error in report["failures"]))

    def test_duplicate_json_key_fails(self):
        path = self.root / "duplicate.json"
        path.write_bytes(b'{"schema":"resolution_release_matrix_v1","rows":[],"rows":[]}')
        report = matrix.evaluate_matrix(path)
        self.assert_blocked(report)
        self.assertTrue(any("duplicate JSON key" in error for error in report["failures"]))

    def test_duplicate_rows_fail(self):
        row = {"id": "classic/800x600", "candidate": {}, "release_index": {}}
        report = self.evaluate_rows([row, row])
        self.assert_blocked(report)
        self.assertTrue(any("duplicate matrix cell" in error for error in report["failures"]))

    def test_unknown_profile_and_custom_resolution_fail(self):
        for cell_id in ("unknown/800x600", "completehd/802x602"):
            with self.subTest(cell_id=cell_id):
                report = self.evaluate_rows([{"id": cell_id, "candidate": {}, "release_index": {}}])
                self.assert_blocked(report)
                self.assertTrue(any("unsupported matrix cell" in error for error in report["failures"]))

    def test_caller_green_booleans_are_not_an_index(self):
        path = self.root / "claimed.json"
        write(path, {"schema": matrix.MATRIX_SCHEMA, "rows": [], "passed": True, "promotion_ready": True})
        self.assert_blocked(matrix.evaluate_matrix(path))
        report = self.evaluate_rows([{"id": "classic/800x600", "candidate": {}, "release_index": {}, "passed": True}])
        self.assert_blocked(report)
        self.assertTrue(any("requires only id" in error for error in report["failures"]))

    def test_omitted_cell_has_explicit_missing_evidence(self):
        report = self.evaluate_rows([])
        self.assert_blocked(report)
        self.assertIn("matrix index must contain exactly all 36 required profile/preset cells", report["failures"])
        self.assertIn("candidate immutable references are missing", report["cells"]["classic/800x600"]["failures"])

    def test_reference_requires_digest_and_rejects_mutation(self):
        ref = write(self.root / "artifact.json", {"synthetic": True})
        with self.assertRaisesRegex(ValueError, "64-hex"):
            matrix.read_reference({"path": ref["path"]}, self.root)
        Path(ref["path"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            matrix.read_reference(ref, self.root)

    def test_authentication_is_not_runtime(self):
        fixture = self.fixture()
        context = fixture.authenticate()
        self.assertIs(context["byte_rebuild_passed"], True)
        self.assertIs(context["runtime_evidence_verified"], False)
        self.assertEqual(context["identity"]["candidate_sha256"], matrix.sha(fixture.image))
        self.assertEqual(context["identity"]["profile"], "completehd")

    def test_all_preset_successors_authenticate_source_without_changing_launcher(self):
        before = matrix.canonical(self.manifest)
        for revision, selected in matrix.VALIDATION_RECIPES.items():
            for resolution in matrix.PRESETS:
                with self.subTest(revision=revision, resolution=resolution):
                    fixture = SyntheticBundle(self.root, self.manifest, selected["profile"], resolution,
                                              successor=revision)
                    context = fixture.authenticate()
                    self.assertEqual(context["identity"]["recipe_revision"], revision)
                    self.assertEqual(context["identity"]["stage"], selected["stage"])
                    self.assertEqual(context["identity"]["resolution"], resolution)
                    self.assertEqual(context["recipe_selection_scope"], "unregistered_source_validation_recipe")
                    self.assertIs(context["runtime_evidence_verified"], False)
                    self.assertEqual(context["preset_advertised"],
                                     resolution in self.manifest["profiles"][selected["profile"]]["resolutions"])
        self.assertEqual(matrix.canonical(self.manifest), before)

    def test_successor_rehashed_wrong_profile_or_stage_fails(self):
        fixture = SyntheticBundle(self.root, self.manifest, successor="complete_hd_all_presets_v1")
        with fixture.authentication(), self.assertRaisesRegex(ValueError, "exact profile and stage"):
            matrix.authenticate_candidate("modalwidgets/1920x1080", fixture.spec, fixture.external,
                                          self.manifest, repo_root=fixture.repo)
        changed = dict(fixture.metadata, stage=matrix.evidence.STAGE)
        fixture.spec["metadata"] = write(Path(fixture.spec["metadata"]["path"]), changed)
        with self.assertRaisesRegex(ValueError, "exact profile and stage"):
            fixture.authenticate()

    def test_successor_rehashed_candidate_metadata_probe_and_sources_fail(self):
        mutations = ("candidate", "metadata", "probe", "source")
        for name in mutations:
            with self.subTest(mutation=name):
                fixture = SyntheticBundle(self.root, self.manifest, successor="complete_hd_all_presets_v1")
                if name == "candidate":
                    fixture.spec["executable"] = write(Path(fixture.spec["executable"]["path"]), fixture.image + b"changed")
                elif name == "metadata":
                    fixture.spec["metadata"] = write(Path(fixture.spec["metadata"]["path"]),
                                                     dict(fixture.metadata, resolution="1024x768"))
                elif name == "probe":
                    fixture.spec["probe"] = write(Path(fixture.spec["probe"]["path"]), b"changed probe")
                else:
                    Path(fixture.source["path"]).write_bytes(b"changed source")
                with self.assertRaises(ValueError):
                    fixture.authenticate()

    def test_successor_production_rebuild_rejects_profile_stage_and_custom_size(self):
        revision = "complete_hd_all_presets_v1"
        selected = matrix.VALIDATION_RECIPES[revision]
        display = SimpleNamespace(recipe_revision=revision, stage=selected["stage"])
        cases = (("modalwidgets", "1920x1080", display), ("completehd", "802x602", display),
                 ("completehd", "1920x1080", SimpleNamespace(recipe_revision=revision, stage="wrong")))
        for profile, resolution, proposed in cases:
            with self.subTest(profile=profile, resolution=resolution, stage=proposed.stage), \
                 patch.object(matrix.importlib, "import_module") as load:
                with self.assertRaisesRegex(ValueError, "exact profile, preset and stage"):
                    matrix._rebuild(profile, resolution, b"synthetic", proposed, matrix.ROOT)
                load.assert_not_called()

    def test_successor_loaded_module_paths_and_constants_are_bound(self):
        revision = "complete_hd_all_presets_v1"
        selected = matrix.VALIDATION_RECIPES[revision]
        display = SimpleNamespace(recipe_revision=revision, stage=selected["stage"])
        attributes = dict(__file__=str(matrix.ROOT / matrix.RECIPE_SOURCES[revision][0]),
                          ROOT=matrix.ROOT, STAGE=selected["stage"], REVISION=revision, RESOLUTIONS=matrix.PRESETS)
        mutations = (("__file__", str(self.root / "other.py")), ("ROOT", self.root),
                     ("STAGE", matrix.evidence.STAGE), ("REVISION", matrix.evidence.RECIPE_REVISION),
                     ("RESOLUTIONS", ("1920x1080",)))
        for name, value in mutations:
            module = SimpleNamespace(**dict(attributes, **{name: value}))
            with self.subTest(attribute=name), patch.object(matrix.importlib, "import_module", return_value=module):
                with self.assertRaisesRegex(ValueError, "another checkout|fixed source contract"):
                    matrix._rebuild("completehd", "1920x1080", b"synthetic", display, matrix.ROOT)

    def test_successor_source_authentication_does_not_fill_missing_runtime_or_advertisement(self):
        fixture = SyntheticBundle(self.root, self.manifest, "modalwidgets", "3840x2160",
                                  successor="modal_widgets_all_presets_v1")
        with fixture.authentication(), \
             patch.object(matrix, "_inventory", return_value=(self.manifest, copy.deepcopy(self.inventory))):
            report = matrix.evaluate_matrix(fixture.matrix_path, repo_root=fixture.repo)
        self.assert_blocked(report)
        self.assertEqual(report["authenticated_candidate_count"], 1)
        cell = report["cells"][fixture.id]
        self.assertIs(cell["preset_advertised"], False)
        self.assertIn("required preset is absent from this launcher profile", cell["failures"])
        self.assertIs(cell["candidate_context"]["byte_rebuild_passed"], True)
        self.assertIs(cell["runtime_evidence_verified"], False)
        self.assertTrue(any("legacy complete-HD" in error for error in cell["failures"]))

    def test_rehashed_candidate_fails(self):
        fixture = self.fixture()
        fixture.spec["executable"] = write(Path(fixture.spec["executable"]["path"]), fixture.image + b"changed")
        with self.assertRaisesRegex(ValueError, "candidate bytes differ"):
            fixture.authenticate()

    def test_unknown_original_fails(self):
        fixture = self.fixture()
        fixture.spec["base_executable"] = write(Path(fixture.spec["base_executable"]["path"]), b"unknown fixture original")
        with self.assertRaisesRegex(ValueError, "unknown original"):
            fixture.authenticate()

    def test_rehashed_metadata_fails(self):
        fixture = self.fixture()
        changed = dict(fixture.metadata, stage="wrong-validation-stage")
        fixture.spec["metadata"] = write(Path(fixture.spec["metadata"]["path"]), changed)
        with self.assertRaisesRegex(ValueError, "producer metadata differs"):
            fixture.authenticate()

    def test_metadata_types_are_exact(self):
        for profile, resolution in (("completehd", "1920x1080"), ("classic", "800x600")):
            fixture = self.fixture(profile, resolution)
            fixture.projection = profile == "classic"
            fixture.metadata.update(schema=1, nested={"runtime_executed": False, "count": 1})
            for field, value in (("schema", True), ("runtime_executed", 0), ("count", True)):
                changed = copy.deepcopy(fixture.metadata)
                target = changed if field == "schema" else changed["nested"]
                target[field] = value
                fixture.spec["metadata"] = write(Path(fixture.spec["metadata"]["path"]), changed)
                with self.subTest(profile=profile, field=field), self.assertRaisesRegex(ValueError, "metadata differs"):
                    fixture.authenticate()

    def test_nonfinite_json_is_rejected(self):
        for token in ("NaN", "Infinity", "-Infinity", "1e999"):
            with self.subTest(token=token), self.assertRaisesRegex(ValueError, "nonfinite"):
                matrix.json_object(('{"value":' + token + '}').encode(), "synthetic")

    def test_production_rebuild_root_is_fixed(self):
        fixture = self.fixture()
        with patch.object(matrix.importlib, "import_module") as load:
            with self.assertRaisesRegex(ValueError, "fixed repository ROOT"):
                matrix._rebuild("completehd", "1920x1080", b"synthetic", fixture.display, self.root)
            load.assert_not_called()

    def test_loaded_recipe_and_classic_implementation_paths_are_bound(self):
        fixture = self.fixture()
        wrong = SimpleNamespace(__file__=str(self.root / "wrong.py"))
        with patch.object(matrix.importlib, "import_module", return_value=wrong):
            with self.assertRaisesRegex(ValueError, "another checkout"):
                matrix._rebuild("completehd", "1920x1080", b"synthetic", fixture.display, matrix.ROOT)
        fixture = self.fixture("classic", "800x600")
        shim = SimpleNamespace(__file__=str(matrix.ROOT / "patch_clash95_hd.py"), _IMPL=wrong)
        with patch.object(matrix.importlib, "import_module", return_value=shim):
            with self.assertRaisesRegex(ValueError, "Classic shim"):
                matrix._rebuild("classic", "800x600", b"synthetic", fixture.display, matrix.ROOT)

    def test_changed_or_missing_canonical_probe_fails(self):
        fixture = self.fixture()
        fixture.spec["probe"] = write(Path(fixture.spec["probe"]["path"]), b"noncanonical probe")
        with self.assertRaisesRegex(ValueError, "probe differs"):
            fixture.authenticate()
        del fixture.spec["probe"]
        with self.assertRaisesRegex(ValueError, "probe differs"):
            fixture.authenticate()

    def test_changed_source_fails(self):
        fixture = self.fixture()
        Path(fixture.source["path"]).write_bytes(b"changed source")
        with self.assertRaisesRegex(ValueError, "sources changed"):
            fixture.authenticate()

    def test_source_escape_is_rejected(self):
        outside = write(self.root / "outside.py", b"outside fixture")
        with self.assertRaisesRegex(ValueError, "escapes repository"):
            matrix._source_hashes({"../outside.py": outside["sha256"]}, self.root / "repo")

    def test_original_candidate_alias_is_rejected(self):
        fixture = self.fixture()
        fixture.spec["executable"] = fixture.spec["base_executable"]
        with self.assertRaisesRegex(ValueError, "isolated external"):
            fixture.authenticate()

    def test_symlink_is_rejected(self):
        fixture = self.fixture()
        target = Path(fixture.spec["executable"]["path"])
        with patch.object(Path, "is_symlink", new=lambda self: self == target):
            with self.assertRaisesRegex(ValueError, "symlink or junction"):
                fixture.authenticate()

    def test_unsupported_preset_fails(self):
        fixture = self.fixture()
        with fixture.authentication():
            with self.assertRaisesRegex(ValueError, "not advertised"):
                matrix.authenticate_candidate("completehd/3840x2160", fixture.spec, fixture.external,
                                              self.manifest, repo_root=fixture.repo)

    def test_frozen_classic_has_no_manufactured_probe(self):
        fixture = self.fixture("classic", "800x600")
        context = fixture.authenticate()
        self.assertIsNone(context["identity"]["probe_sha256"])
        fixture.spec["probe"] = write(fixture.external / "invented.cdb", b"invented probe")
        with self.assertRaisesRegex(ValueError, "no canonical probe"):
            fixture.authenticate()

    def test_report_cannot_choose_verifier(self):
        fixture = self.fixture()
        fixture.spec["verifier"] = "arbitrary.module"
        with self.assertRaisesRegex(ValueError, "recipe-specific probe"):
            fixture.authenticate()

    def test_release_candidate_path_rebinding_fails(self):
        fixture = self.fixture()
        context = fixture.authenticate()
        fixture.index["candidate"]["executable"] = write(fixture.external / "other.exe", fixture.image)
        fixture.release_ref = write(Path(fixture.release_ref["path"]), fixture.index)
        with self.assertRaisesRegex(ValueError, "rebinds.*executable"):
            matrix._replay_release(fixture.release_ref, fixture.external, context)

    def test_metadata_rebinding_and_probe_drop_fail(self):
        fixture = self.fixture()
        context = fixture.authenticate()
        fixture.index["candidate"]["metadata"] = write(fixture.external / "other.json", fixture.metadata)
        fixture.release_ref = write(Path(fixture.release_ref["path"]), fixture.index)
        with self.assertRaisesRegex(ValueError, "rebinds.*metadata"):
            matrix._replay_release(fixture.release_ref, fixture.external, context)
        del fixture.index["candidate"]["probe"]
        fixture.release_ref = write(Path(fixture.release_ref["path"]), fixture.index)
        with self.assertRaisesRegex(ValueError, "references differ"):
            matrix._replay_release(fixture.release_ref, fixture.external, context)

    def test_legacy_replay_cannot_cover_other_profiles(self):
        fixture = self.fixture("modalwidgets", "1920x1080")
        context = fixture.authenticate()
        with patch.object(matrix.evidence, "evaluate_release_manifest") as evaluate:
            with self.assertRaisesRegex(ValueError, "only its exact Complete HD"):
                matrix._replay_release(fixture.release_ref, fixture.external, context)
            evaluate.assert_not_called()

    def test_legacy_replay_requires_matching_measured_identity(self):
        fixture = self.fixture()
        context = fixture.authenticate()
        with patch.object(matrix.evidence, "evaluate_release_manifest", return_value={"candidate_context": {"identity": {}}}):
            with self.assertRaisesRegex(ValueError, "replayed release identity differs"):
                matrix._replay_release(fixture.release_ref, fixture.external, context)

    def test_green_claim_cannot_fill_gates(self):
        fixture = self.fixture()
        context = fixture.authenticate()
        identity = {key: value for key, value in context["identity"].items() if key != "profile"}
        synthetic = {"evidence_ready": True, "passed": True, "promotion_ready": True,
                     "candidate_context": {"identity": identity}, "failures": []}
        with fixture.authentication(), \
             patch.object(matrix, "_inventory", return_value=(self.manifest, copy.deepcopy(self.inventory))), \
             patch.object(matrix.evidence, "evaluate_release_manifest", return_value=synthetic) as replay:
            report = matrix.evaluate_matrix(fixture.matrix_path, repo_root=fixture.repo)
        self.assert_blocked(report)
        self.assertEqual(report["authenticated_candidate_count"], 1)
        replay.assert_called_once_with(Path(fixture.release_ref["path"]).resolve(),
                                      candidate_manifest=Path(fixture.spec["metadata"]["path"]).resolve())
        errors = report["cells"][fixture.id]["failures"]
        self.assertEqual(sum("production lane verifier is not implemented" in error for error in errors), 14)
        self.assertIn("candidate-bound expanded-battle production acceptance verifier is not implemented", errors)

    def test_matrix_index_changes_during_evaluation_fail(self):
        fixture = self.fixture()
        def mutate(*args, **kwargs):
            fixture.matrix_path.write_bytes(b"changed matrix index")
            raise ValueError("synthetic candidate failure")
        with patch.object(matrix, "authenticate_candidate", side_effect=mutate):
            report = matrix.evaluate_matrix(fixture.matrix_path)
        self.assert_blocked(report)
        self.assertIn("matrix index changed during evaluation", report["failures"])

    def test_stdout_cli_fails_without_writes(self):
        before = set(self.root.rglob("*"))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = matrix.main([])
        self.assertEqual(status, 2)
        self.assert_blocked(json.loads(output.getvalue()))
        self.assertEqual(set(self.root.rglob("*")), before)

    def test_optional_report_is_fresh_and_never_overwrites(self):
        target = self.root / "result.json"
        with contextlib.redirect_stdout(io.StringIO()):
            status = matrix.main(["--write-json", str(target)])
        self.assertEqual(status, 2)
        initial = target.read_bytes()
        self.assert_blocked(json.loads(initial))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            status = matrix.main(["--write-json", str(target)])
        self.assertEqual(status, 2)
        self.assertEqual(target.read_bytes(), initial)

if __name__ == "__main__":
    unittest.main(verbosity=2)
