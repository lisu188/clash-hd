#!/usr/bin/env python3
"""Synthetic offline matrix fixtures; no runtime proof."""
from __future__ import annotations

import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import types
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

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
        self.probe = None if successor is None and profile == "classic" and resolution == "800x600" else "fixture-only canonical probe\n"
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
        for revision, selected in matrix.VALIDATION_RECIPES.items():
            display = SimpleNamespace(recipe_revision=revision, stage=selected["stage"])
            wrong_profile = "framed" if selected["profile"] == "classic" else "classic"
            cases = ((wrong_profile, "1920x1080", display), (selected["profile"], "802x602", display),
                     (selected["profile"], "1920x1080", SimpleNamespace(recipe_revision=revision, stage="wrong")))
            for profile, resolution, proposed in cases:
                with self.subTest(revision=revision, profile=profile, resolution=resolution, stage=proposed.stage), \
                     patch.object(matrix.importlib, "import_module") as load:
                    with self.assertRaisesRegex(ValueError, "exact profile, preset and stage"):
                        matrix._rebuild(profile, resolution, b"synthetic", proposed, matrix.ROOT)
                    load.assert_not_called()

    def test_successor_loaded_module_paths_and_constants_are_bound(self):
        for revision, selected in matrix.VALIDATION_RECIPES.items():
            if revision == "complete_hd_all_presets_v1":
                # Complete has a canonical byte loader, covered independently
                # below; its public recipe module is never admitted.
                continue
            display = SimpleNamespace(recipe_revision=revision, stage=selected["stage"])
            attributes = dict(__file__=str(matrix.ROOT / matrix.RECIPE_SOURCES[revision][0]),
                              ROOT=matrix.ROOT, STAGE=selected["stage"], REVISION=revision, RESOLUTIONS=matrix.PRESETS)
            mutations = (("__file__", str(self.root / "other.py")), ("ROOT", self.root),
                         ("STAGE", matrix.evidence.STAGE), ("REVISION", matrix.evidence.RECIPE_REVISION),
                         ("RESOLUTIONS", ("1920x1080",)))
            for name, value in mutations:
                module = SimpleNamespace(**dict(attributes, **{name: value}))
                with self.subTest(revision=revision, attribute=name), patch.object(matrix.importlib, "import_module", return_value=module):
                    with self.assertRaisesRegex(ValueError, "another checkout|fixed source contract"):
                        matrix._rebuild(selected["profile"], "1920x1080", b"synthetic", display, matrix.ROOT)

    def test_successor_call_interface_and_legacy_framed_option(self):
        selections = [(revision, selected["profile"], selected["stage"], {})
                      for revision, selected in matrix.VALIDATION_RECIPES.items()
                      if revision != "complete_hd_all_presets_v1"]
        selections.append(("four-border-partial-initial-v1", "framed", "fixture-only-legacy-stage",
                           {"minimap_viewport": True}))
        pins = {"fixture-only-source.py": "a" * 64}
        for revision, profile, stage, options in selections:
            build = Mock(return_value=(b"synthetic", {"source_hashes": pins}, "synthetic probe"))
            module = SimpleNamespace(__file__=str(matrix.ROOT / matrix.RECIPE_SOURCES[revision][0]),
                                     ROOT=matrix.ROOT, STAGE=stage, REVISION=revision, RESOLUTIONS=matrix.PRESETS,
                                     build_candidate=build)
            display = SimpleNamespace(recipe_revision=revision, stage=stage)
            with self.subTest(revision=revision), patch.object(matrix, "_source_hashes", return_value=pins), \
                 patch.object(matrix.importlib, "import_module", return_value=module):
                matrix._rebuild(profile, "1920x1080", b"synthetic", display, matrix.ROOT)
            build.assert_called_once_with(b"synthetic", "1920x1080", **options)

    def test_successor_extra_timestamp_is_rejected_without_removing_legacy_compatibility(self):
        for revision, selected in matrix.VALIDATION_RECIPES.items():
            fixture = SyntheticBundle(self.root, self.manifest, selected["profile"], successor=revision)
            changed = dict(fixture.metadata, generated_at={"invented": True})
            fixture.spec["metadata"] = write(Path(fixture.spec["metadata"]["path"]), changed)
            with self.subTest(revision=revision), self.assertRaisesRegex(ValueError, "metadata differs"):
                fixture.authenticate()
        legacy = SyntheticBundle(self.root, self.manifest, "framed")
        legacy.spec["metadata"] = write(Path(legacy.spec["metadata"]["path"]),
                                        dict(legacy.metadata, generated_at="2026-10-05T00:00:00Z"))
        self.assertIs(legacy.authenticate()["byte_rebuild_passed"], True)

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
        fixture = self.fixture("framed")
        wrong = SimpleNamespace(__file__=str(self.root / "wrong.py"))
        with patch.object(matrix.importlib, "import_module", return_value=wrong):
            with self.assertRaisesRegex(ValueError, "another checkout"):
                matrix._rebuild("framed", "1920x1080", b"synthetic", fixture.display, matrix.ROOT)
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

class CompleteRecipeIntegrationTests(unittest.TestCase):
    """Canonical loader rejection tests without candidate or native outputs."""
    ROOT = matrix.ROOT
    HELPER = ROOT / "tools/resolution_recipe_authentication.py"
    STAGES = {
        "complete_hd_v1": "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-validation",
        "complete_hd_all_presets_v1": "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-allpresets-validation",
    }

    def display(self, revision="complete_hd_v1"):
        return SimpleNamespace(recipe_revision=revision, stage=self.STAGES[revision])

    def call(self, revision="complete_hd_v1", *, profile="completehd", resolution="1920x1080", display=None):
        return matrix._rebuild(profile, resolution, b"marked invalid original; no game material",
                               display or self.display(revision), self.ROOT)

    def namespaces(self):
        return {name: module for name, module in sys.modules.items()
                if name.startswith(("_clash_matrix_complete_auth_", "_clash_recipe_authenticator_"))}

    def test_two_complete_routes_ignore_public_recipe_and_helper_exports(self):
        trap = Mock(side_effect=AssertionError("mutable public producer/helper executed"))
        aliases = {}
        for name in ("resolution_recipe_authentication", "tools.resolution_recipe_authentication",
                     "src.patcher.complete_hd_candidate", "src.patcher.complete_hd_all_presets_candidate"):
            module = types.ModuleType(name); module.__file__ = str(self.HELPER)
            module.build_candidate = module.rebuild_recipe = module._factory = trap
            aliases[name] = module
        with patch.dict(sys.modules, aliases), patch.object(matrix.importlib, "import_module", trap):
            for revision in self.STAGES:
                with self.subTest(revision=revision), self.assertRaisesRegex(ValueError, "exact original executable"):
                    self.call(revision)
        trap.assert_not_called()

    def test_later_public_loader_path_pin_and_predicate_aliases_are_not_authority(self):
        trap = Mock(side_effect=AssertionError("public loader alias executed"))
        with contextlib.ExitStack() as stack:
            for name, value in (("_complete_recipe_reconstructor", trap), ("_bind_complete_rebuild", trap),
                                ("_plain_path", trap), ("sha", trap), ("ROOT", Path("relative")),
                                ("COMPLETE_AUTH_SOURCE", "caller.py"), ("COMPLETE_AUTH_SHA256", "0" * 64),
                                ("sys", SimpleNamespace()), ("types", SimpleNamespace()), ("uuid", SimpleNamespace())):
                stack.enter_context(patch.object(matrix, name, value))
            for revision in self.STAGES:
                with self.subTest(revision=revision), self.assertRaisesRegex(ValueError, "exact original executable"):
                    self.call(revision)
        trap.assert_not_called()

    def test_wrong_selection_rejects_before_helper_or_recipe_execution(self):
        read = Path.read_bytes; reads = []
        def observed(path):
            if path == self.HELPER: reads.append(path)
            return read(path)
        with patch.object(Path, "read_bytes", observed), patch.object(matrix.importlib, "import_module") as public:
            for revision in self.STAGES:
                for changed in (dict(profile="classic"), dict(resolution="802x602"),
                                dict(display=SimpleNamespace(recipe_revision=revision, stage="wrong"))):
                    with self.subTest(revision=revision, changed=changed), self.assertRaisesRegex(ValueError, "exact profile, preset and stage"):
                        self.call(revision, **changed)
            public.assert_not_called()
        self.assertEqual(reads, [])

    def test_unknown_recipe_stays_in_legacy_rejection_branch(self):
        with patch.object(matrix.importlib, "import_module") as public, self.assertRaisesRegex(ValueError, "fixed profile registry"):
            self.call(display=SimpleNamespace(recipe_revision="caller_recipe", stage=self.STAGES["complete_hd_v1"]))
        public.assert_not_called()

    def test_all_preset_route_checks_original_and_legacy_unsupported_sizes_reject(self):
        with patch.object(matrix.importlib, "import_module") as public:
            for resolution in matrix.PRESETS:
                with self.subTest(resolution=resolution), self.assertRaisesRegex(ValueError, "exact original executable"):
                    self.call("complete_hd_all_presets_v1", resolution=resolution)
            for resolution in ("1366x768", "2560x1440", "3440x1440", "3840x2160"):
                with self.subTest(legacy_unsupported=resolution), self.assertRaisesRegex(ValueError, "exact supported preset"):
                    self.call("complete_hd_v1", resolution=resolution)
            public.assert_not_called()

    def test_other_repository_root_rejects_before_helper_reads(self):
        read = Mock(side_effect=AssertionError("source read before fixed ROOT check"))
        with patch.object(Path, "read_bytes", read), self.assertRaisesRegex(ValueError, "fixed repository ROOT"):
            matrix._rebuild("completehd", "1920x1080", b"invalid", self.display(), self.ROOT.parent)
        read.assert_not_called()

    def test_changed_or_missing_canonical_helper_fails_before_execution(self):
        read = Path.read_bytes; trap = Mock(side_effect=AssertionError("public module import executed"))
        for mode in ("changed", "missing"):
            def altered(path, mode=mode):
                if path == self.HELPER:
                    if mode == "missing": raise FileNotFoundError("modeled missing canonical helper")
                    return b"raise AssertionError('unapproved bytes must never execute')\n"
                return read(path)
            with self.subTest(mode=mode), patch.object(Path, "read_bytes", altered), \
                    patch.object(matrix, "COMPLETE_AUTH_SHA256", matrix.sha(b"raise AssertionError('unapproved bytes must never execute')\n")), \
                    patch.object(matrix.importlib, "import_module", trap):
                with self.assertRaises((ValueError, FileNotFoundError)):
                    self.call()
        trap.assert_not_called()

    def test_noncanonical_helper_path_symlink_and_junction_ancestors_reject(self):
        resolve = Path.resolve
        def redirected(path, *args, **kwargs):
            return self.ROOT / "caller.py" if path == self.HELPER else resolve(path, *args, **kwargs)
        with patch.object(Path, "resolve", redirected), self.assertRaisesRegex(ValueError, "fixed canonical ROOT"):
            self.call()
        is_symlink = Path.is_symlink
        with patch.object(Path, "is_symlink", lambda path: path == self.HELPER.parent or is_symlink(path)), \
                self.assertRaisesRegex(ValueError, "reparse ancestor"):
            self.call()
        if hasattr(Path, "is_junction"):
            is_junction = Path.is_junction
            with patch.object(Path, "is_junction", lambda path: path == self.ROOT or is_junction(path)), \
                    self.assertRaisesRegex(ValueError, "reparse ancestor"):
                self.call()

    def test_native_reparse_attribute_and_changed_source_stamp_reject(self):
        stat = Path.stat
        def reparse(path, *args, **kwargs):
            value = stat(path, *args, **kwargs)
            if path != self.ROOT or kwargs.get("follow_symlinks") is False: return value
            return SimpleNamespace(st_mode=value.st_mode,
                st_file_attributes=getattr(value, "st_file_attributes", 0) | 0x400)
        with patch.object(Path, "stat", reparse), self.assertRaisesRegex(ValueError, "reparse ancestor"):
            self.call()
        calls = 0
        def changed(path, *args, **kwargs):
            nonlocal calls
            value = stat(path, *args, **kwargs)
            if path != self.HELPER or kwargs.get("follow_symlinks") is False: return value
            calls += 1
            return SimpleNamespace(st_dev=value.st_dev, st_ino=value.st_ino, st_size=value.st_size,
                st_mode=value.st_mode, st_mtime_ns=value.st_mtime_ns + (1 if calls >= 3 else 0), st_file_attributes=0)
        with patch.object(Path, "stat", changed), self.assertRaisesRegex(ValueError, "changed while reading"):
            self.call()

    def test_oversized_helper_rejects_before_reading_or_compiling(self):
        stat = Path.stat
        def oversized(path, *args, **kwargs):
            value = stat(path, *args, **kwargs)
            if path != self.HELPER or kwargs.get("follow_symlinks") is False: return value
            return SimpleNamespace(st_dev=value.st_dev, st_ino=value.st_ino, st_mode=value.st_mode,
                st_size=2 * 1024**2 + 1, st_mtime_ns=value.st_mtime_ns, st_file_attributes=0)
        read = Mock(side_effect=AssertionError("oversized source read"))
        with patch.object(Path, "stat", oversized), patch.object(Path, "read_bytes", read), \
                self.assertRaisesRegex(ValueError, "source read bound"):
            self.call()
        read.assert_not_called()

    def test_source_changes_after_private_execution_or_failed_api_keep_no_result(self):
        read = Path.read_bytes
        for after in (6, 8):
            count = 0; before = self.namespaces()
            def changed(path):
                nonlocal count
                raw = read(path)
                if path == self.HELPER:
                    count += 1
                    if count >= after: return raw[:-1] + bytes([raw[-1] ^ 1])
                return raw
            with self.subTest(after=after), patch.object(Path, "read_bytes", changed):
                with self.assertRaisesRegex(ValueError, "source pin differs") as raised:
                    self.call()
                self.assertGreaterEqual(count, after)
                if after == 8:
                    self.assertIsInstance(raised.exception.__context__, ValueError)
                    self.assertIn("exact original executable", str(raised.exception.__context__))
            self.assertEqual(self.namespaces(), before)

    def test_cleanup_preserves_replaced_namespace_identity(self):
        read = Path.read_bytes; replaced = {}; foreign = types.ModuleType("foreign_fixture")
        def replace(path):
            if path == self.HELPER and not replaced:
                matches = {name: value for name, value in self.namespaces().items()
                           if name.startswith("_clash_matrix_complete_auth_")}
                if matches:
                    name = next(iter(matches)); replaced[name] = matches[name]; sys.modules[name] = foreign
            return read(path)
        try:
            with patch.object(Path, "read_bytes", replace), self.assertRaises(ValueError):
                self.call()
            self.assertEqual(len(replaced), 1)
            self.assertIs(sys.modules[next(iter(replaced))], foreign)
        finally:
            for name in replaced:
                if sys.modules.get(name) is foreign: del sys.modules[name]


if __name__ == "__main__":
    unittest.main(verbosity=2)
