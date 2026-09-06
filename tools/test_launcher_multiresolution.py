from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import copy
from dataclasses import replace
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src/launcher")]
import presets
from src.display_plan import DisplayPlanError, resolve_display_plan


class ProfileRegistryTests(unittest.TestCase):
    def setUp(self):
        self.manifest = presets.load_manifest()

    def test_classic_status_is_not_inherited_by_framed(self):
        classic = {row.key: row for row in presets.load_options(self.manifest)}
        framed = {row.key: row for row in presets.load_options(self.manifest, "framed")}
        self.assertEqual(classic["800x600"].status, "stable")
        self.assertEqual(framed["800x600"].status, "experimental")
        self.assertTrue(all(option.evidence is None for option in framed.values()))
        self.assertTrue({"1366x768", "2560x1440", "3440x1440", "3840x2160"} <= framed.keys())
        self.assertEqual(self.manifest["resolutions"], self.manifest["profiles"]["classic"]["resolutions"])

    def test_legacy_schema_reads_without_promoting_framed(self):
        legacy = {key: copy.deepcopy(value) for key, value in self.manifest.items()
                  if key not in ("profiles", "default_renderer")}
        legacy["schema"] = 1
        presets.validate_manifest(legacy)
        self.assertEqual(presets.load_options(legacy)[0].status, "stable")
        self.assertTrue(all(option.is_experimental for option in presets.load_options(legacy, "framed")))
        self.assertEqual(presets.default_key(legacy), "800x600")

    def test_mismatched_evidence_scope_cannot_promote_another_profile(self):
        entry = copy.deepcopy(self.manifest["profiles"]["classic"]["resolutions"]["800x600"])
        self.manifest["profiles"]["framed"]["resolutions"]["800x600"] = entry
        with self.assertRaises(presets.ManifestError):
            presets.validate_manifest(self.manifest)

    def test_unknown_revision_wrong_feature_types_and_scope_are_rejected(self):
        for change in ({"recipe_revision": "future-unreviewed"}, {"features": {"minimap_viewport": 1}},
                       {"features": {"minimap_viewport": False}}, {"stage": None}):
            manifest = copy.deepcopy(self.manifest)
            manifest["profiles"]["framed"].update(change)
            with self.subTest(change=change), self.assertRaises(presets.ManifestError):
                presets.validate_manifest(manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest["profiles"]["classic"]["resolutions"]["800x600"]["evidence_scope"]["features"]["minimap_viewport"] = 0
        manifest["resolutions"] = copy.deepcopy(manifest["profiles"]["classic"]["resolutions"])
        with self.assertRaises(presets.ManifestError):
            presets.validate_manifest(manifest)

    def test_projection_divergence_is_not_silently_ignored(self):
        self.manifest["resolutions"]["800x600"]["status"] = "experimental"
        with self.assertRaises(presets.ManifestError):
            presets.validate_manifest(self.manifest)

    def test_duplicate_json_keys_and_invalid_schemas_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "resolutions.json"
            path.write_text('{"schema": 1, "schema": 2}', encoding="utf-8")
            with self.assertRaises(presets.ManifestError):
                presets.load_manifest(path)
        for schema in (True, 2.0, "2", 3):
            with self.subTest(schema=schema), self.assertRaises(presets.ManifestError):
                presets.validate_manifest(self.manifest | {"schema": schema})

    def test_bad_entry_shapes_and_missing_evidence_fail(self):
        for change in ({"status": "stable"}, {"tiles": [True, 10]}, {"tiles": [10]},
                       {"evidence": []}, {"evidence": {"run": False}}):
            manifest = copy.deepcopy(self.manifest)
            manifest["profiles"]["framed"]["resolutions"]["1366x768"].update(change)
            with self.subTest(change=change), self.assertRaises(presets.ManifestError):
                presets.validate_manifest(manifest)

    def test_custom_policy_applies_before_recipe_access(self):
        manifest = self.manifest | {"custom_allowed": False}
        with self.assertRaises(DisplayPlanError) as error:
            presets.resolve_plan(renderer="framed", resolution="802x602", manifest=manifest)
        self.assertEqual(error.exception.code, "custom_disabled")
        self.assertTrue(presets.validate_custom_resolution(802, 602, manifest))
        self.assertTrue(presets.validate_custom_resolution(True, 720, self.manifest))
        self.assertTrue(presets.validate_custom_resolution(1367, 768, self.manifest))
        self.assertFalse(presets.validate_custom_resolution(1366, 768, self.manifest))

    def test_bounds_cannot_be_expanded_past_launcher_envelope(self):
        for bounds in ({"min": [800, 600], "max": [8192, 8192]}, {"min": [True, 600], "max": [3840, 2160]},
                       {"min": [800, 600], "max": None}):
            with self.subTest(bounds=bounds), self.assertRaises(presets.ManifestError):
                presets.validate_manifest(self.manifest | {"custom_bounds": bounds})

    def test_returned_evidence_is_not_mutable_registry_state(self):
        options = presets.load_options(self.manifest)
        options[0].evidence["normal_run"] = "different"
        self.assertNotEqual(presets.load_options(self.manifest)[0].evidence["normal_run"], "different")


@unittest.skipUnless((ROOT / "src/patcher/patch_clash95_hd.py").is_file(), "complete repository source is required for launcher integration")
class LauncherDisplayIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import core
        import framed
        import run
        import gui
        cls.core, cls.framed, cls.cli_module, cls.gui = core, framed, run, gui

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="clash-display-integration-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = presets.load_manifest()

    def command(self, *arguments):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            result = self.cli_module.main(list(arguments))
        return result, out.getvalue(), err.getvalue()

    def test_profile_plans_use_independent_geometry_and_preserve_paths(self):
        kwargs = dict(resolution="1366x768", clash_dir=self.root / "game", candidates_root=self.root / "candidates")
        classic, framed = self.core.plan_candidate(**kwargs), self.framed.plan_candidate(**kwargs)
        self.assertEqual(classic.candidate_dir, self.root / "candidates/1366x768")
        self.assertEqual(framed.candidate_dir, self.root / "candidates/framed-minimap/1366x768")
        self.assertEqual(classic.renderer, "classic")
        self.assertEqual(framed.renderer, "framed")
        self.assertEqual(classic.to_dict()["display_plan"]["full_tiles"], [20, 11])
        self.assertEqual(framed.to_dict()["display_plan"]["coverage_tiles"], [21, 12])
        self.assertFalse((self.root / "candidates").exists())

    def test_default_resolution_recipe_rejection_reaches_core_and_cli(self):
        with patch.object(self.core.patch_clash95_hd, "select_patches_for",
                          side_effect=self.core.patch_clash95_hd.ResolutionError("fixture recipe rejected")):
            with self.assertRaises(self.core.LauncherError) as error:
                self.core.plan_candidate()
            code, _, errors = self.command("--describe-plan", "--resolution", "800x600")
        self.assertIn("fixture recipe rejected", str(error.exception))
        self.assertEqual(code, 1)
        self.assertIn("fixture recipe rejected", errors)

    def test_list_resolutions_needs_no_environment_probe_or_game(self):
        with (patch.object(self.core, "check_environment") as environment,
              patch.object(self.core, "ensure_candidate") as build,
              patch.object(self.core, "launch_game") as launch):
            code, out, errors = self.command("--profile", "framed", "--list-resolutions")
        self.assertEqual(code, 0, errors)
        data = json.loads(out)
        self.assertEqual(len(data["resolutions"]), 9)
        self.assertTrue(all(row["recipe_eligible"] and row["status"] == "experimental" for row in data["resolutions"]))
        self.assertFalse(data["game_runtime_executed"])
        environment.assert_not_called()
        build.assert_not_called()
        launch.assert_not_called()

    def test_describe_plan_reports_world_and_presentation_without_touching_game_paths(self):
        code, out, errors = self.command("--profile", "framed", "--describe-plan", "--resolution", "1280x720",
            "--map-size", "60", "60", "--client-size", "2560", "1600", "--clash-dir", str(self.root / "missing-game"),
            "--candidates-root", str(self.root / "candidates"))
        self.assertEqual(code, 0, errors)
        data = json.loads(out)
        self.assertEqual(data["presentation_plan"]["content_rectangle"], [0, 80, 2560, 1440])
        self.assertFalse(data["presentation_plan"]["observed_runtime_geometry"])
        self.assertEqual(data["plan"]["display_plan"]["resolution"], "1280x720")
        self.assertTrue(data["world_plan"]["native_full_loop_safe"])
        self.assertFalse((self.root / "candidates").exists())
        self.assertFalse((self.root / "missing-game").exists())

    def test_describe_small_world_fails_honestly_without_permission_to_run_it(self):
        code, out, _ = self.command("--profile", "framed", "--describe-plan", "--resolution", "3840x2160", "--map-size", "40", "30")
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertFalse(data["world_plan"]["native_full_loop_safe"])
        self.assertFalse(data["world_plan"]["bounded_renderer_installed"])
        self.assertIn("blocked_reason", data)

    def test_inspection_cannot_be_combined_with_process_start_or_ignored_geometry(self):
        for flags in (("--describe-plan", "--launch", "--yes-launch"), ("--list-resolutions", "--prepare"),
                      ("--describe-plan", "--dry-run"), ("--map-size", "3", "2", "--prepare"),
                      ("--client-size", "2560", "1440"), ("--map-size", "3", "2", "--list-resolutions")):
            with self.subTest(flags=flags), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.cli_module.parse_args(list(flags))

    def test_registry_status_does_not_cover_another_stage(self):
        row = presets.resolution_info("800x600", stage="display", manifest=self.manifest)
        self.assertTrue(row["recipe_eligible"])
        self.assertEqual(row["status"], "experimental")
        self.assertIsNone(row["evidence_references"])
        self.assertFalse(row["display_plan"]["map_geometry_available"])
        with self.assertRaises(DisplayPlanError):
            resolve_display_plan(stage="display").world_view(60, 60)

    def test_unknown_recipe_and_disabled_custom_are_not_mistaken_for_buildability(self):
        row = presets.resolution_info("1280x720", stage="display", manifest=self.manifest)
        self.assertFalse(row["recipe_eligible"])
        self.assertIn("legacy 800x600", row["error"])
        row = presets.resolution_info("802x602", renderer="framed", manifest=self.manifest | {"custom_allowed": False})
        self.assertFalse(row["recipe_eligible"])
        self.assertEqual(row["error_code"], "custom_disabled")

    def fixture(self):
        from test_launcher_framed import FramedLauncherTests
        fixture = FramedLauncherTests("test_preparation_builds_verified_artifacts_without_runtime_or_default_changes")
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        return fixture

    def test_preparation_and_deployment_bind_display_and_actual_source_hashes(self):
        fixture = self.fixture()
        first = fixture.deploy()
        manifest = self.core.read_candidate_manifest(fixture.plan)
        self.assertEqual(manifest["build_id"], first["build_id"])
        self.assertEqual(manifest["display_plan"], self.core.display_for_plan(fixture.plan).to_dict())
        self.assertEqual(manifest["deployment_id"], self.core.deployment_identity(first["build_id"],
            manifest["artifact_sha256"][self.core.WRAPPER_DLL_NAME], manifest["artifact_sha256"][self.core.DXCFG_NAME]))
        self.framed.verify_launch(fixture.plan)
        self.assertEqual(self.framed.ensure_candidate(fixture.plan)["build_id"], first["build_id"])

    def test_corrupt_display_build_or_deployment_identity_blocks_launch(self):
        fixture = self.fixture()
        fixture.deploy()
        manifest = self.core.read_candidate_manifest(fixture.plan)
        for changes in ({"display_plan": {}}, {"build_id": "0" * 64}, {"deployment_id": "0" * 64}):
            with self.subTest(changes=changes):
                fixture.plan.manifest_path.write_text(json.dumps(manifest | changes), encoding="utf-8")
                with self.assertRaises(self.core.LauncherError):
                    self.framed.verify_launch(fixture.plan)

    def test_wrapper_change_changes_only_deployment_identity(self):
        fixture = self.fixture()
        first = fixture.deploy()
        old = self.core.read_candidate_manifest(fixture.plan)["deployment_id"]
        fixture.plan.wrapper_source.write_bytes(b"second synthetic wrapper; never loaded")
        self.framed.deploy_runtime_files(fixture.plan, first)
        current = self.core.read_candidate_manifest(fixture.plan)
        self.assertEqual(current["build_id"], first["build_id"])
        self.assertNotEqual(current["deployment_id"], old)
        self.framed.verify_launch(fixture.plan)

    def test_classic_builder_retains_byte_gate_with_additive_display_identity(self):
        from test_launcher_core import BASE_BYTES, BASE_SHA
        game = self.root / "game"
        game.mkdir()
        (game / self.core.BASE_EXE_NAME).write_bytes(BASE_BYTES)
        plan = self.core.plan_candidate(resolution="1366x768", clash_dir=game,
                 candidates_root=self.root / "candidates", expected_base_sha=BASE_SHA)
        result = self.core.ensure_candidate(plan)
        self.assertEqual(result["byte_gate"]["unexpected"], 0)
        self.assertEqual(result["byte_gate"]["original"], 0)
        self.assertEqual(len(result["build_id"]), 64)
        self.assertEqual(result["display_plan"]["renderer"], "classic")
        self.assertEqual((game / self.core.BASE_EXE_NAME).read_bytes(), BASE_BYTES)

    def test_gui_preview_uses_profile_geometry_and_saved_directories_without_runtime(self):
        app = object.__new__(self.gui.LauncherApp)
        app.profile_var = SimpleNamespace(get=lambda: "framed")
        app.resolution_var = SimpleNamespace(get=lambda: "1366x768")
        app.scaling_var = SimpleNamespace(get=lambda: "integer")
        app.manifest = self.manifest
        app.settings = {"clash_dir": str(self.root / "game"), "candidates_root": str(self.root / "candidates")}
        app.display_label, app.play_button = Mock(), Mock()
        app.resolution_buttons = [(Mock(), presets.load_options(self.manifest)[0])]
        with patch.object(self.core, "launch_game") as launch:
            app.refresh_display_plan()
        text = app.display_label.configure.call_args.kwargs["text"]
        self.assertIn("framed 1366x768 [experimental]", text)
        self.assertIn("1302x736", text)
        self.assertIn("coverage 21x12", text)
        self.assertEqual(app._selected_plan().clash_dir, self.root / "game")
        app.play_button.configure.assert_called_with(state="normal")
        self.assertFalse(app.experimental_warned)
        launch.assert_not_called()
        app.resolution_var = SimpleNamespace(get=lambda: "1367x768")
        app.refresh_display_plan()
        app.play_button.configure.assert_called_with(state="disabled")


if __name__ == "__main__":
    unittest.main()
