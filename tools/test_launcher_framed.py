from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
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
sys.path.insert(0, str(ROOT / "src" / "launcher"))
import bootstrap
bootstrap.ensure_repo_paths()
import core
import framed
import run

REAL_BUILD = framed._build


class FramedLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="clash-framed-launcher-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.game = self.root / "game"
        self.game.mkdir()
        self.original = b"synthetic input; not a game executable"
        (self.game / core.BASE_EXE_NAME).write_bytes(self.original)
        (self.game / core.WRAPPER_DLL_NAME).write_bytes(b"synthetic wrapper; never loaded")
        self.base_sha = core.sha256_bytes(self.original)
        self.addCleanup(patch.stopall)
        patch.object(core.patch_clash95_hd, "EXPECTED_SHA256", self.base_sha).start()
        self.bindings = {"tools/build_framed_candidate.py": framed.BUILDER_SHA256,
                         "synthetic.py": "b" * 64}
        patch.object(framed, "_bindings", return_value=self.bindings).start()
        self.plan = framed.plan_candidate(resolution="1280x720", clash_dir=self.game,
                                          candidates_root=self.root / "candidates")
        self.image = b"synthetic framed output; never executed"
        self.metadata = {"stage": framed.STAGE, "resolution": "1280x720",
                         "output_sha256": core.sha256_bytes(self.image), "minimap_viewport": True,
                         "validation_stage_only": True, "runtime_executed": False,
                         "manual_input_proof": False, "promotion_ready": False,
                         "source_sha256": {"synthetic.py": "b" * 64},
                         "generated_at": "fixture", "selected_patches": [], "hooks": []}
        self.builder = patch.object(framed, "_build", side_effect=lambda *args:
                                    (self.image, dict(self.metadata), "synthetic probe\n")).start()

    def deploy(self):
        result = framed.ensure_candidate(self.plan)
        framed.deploy_runtime_files(self.plan, result)
        return result

    def cli(self, *arguments):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(run, "build_plan", return_value=self.plan), redirect_stdout(output), redirect_stderr(errors):
            code = run.main(list(arguments))
        return code, output.getvalue(), errors.getvalue()

    def test_profile_paths_are_isolated_and_planning_writes_nothing(self):
        classic = core.plan_candidate(resolution="1280x720", clash_dir=self.game,
                                      candidates_root=self.root / "candidates")
        self.assertNotEqual(classic.candidate_dir, self.plan.candidate_dir)
        self.assertEqual(self.plan.candidate_dir, self.root / "candidates/framed-minimap/1280x720")
        self.assertFalse(self.plan.candidates_root.exists())
        self.assertEqual(classic.stage, core.patch_clash95_hd.DEFAULT_STAGE)

    def test_conflicting_stage_and_invalid_resolution_are_rejected(self):
        with self.assertRaises(core.LauncherError):
            framed.plan_candidate(stage=core.patch_clash95_hd.DEFAULT_STAGE)
        for resolution in ("1281x720", "1280x719", "01280x0720", "640x480"):
            with self.subTest(resolution=resolution), self.assertRaises((core.LauncherError, ValueError)):
                framed.plan_candidate(resolution=resolution)

    def test_preparation_builds_verified_artifacts_without_runtime_or_default_changes(self):
        with patch.object(core, "launch_game", side_effect=AssertionError("unexpected launch")):
            result = framed.ensure_candidate(self.plan)
        self.assertFalse(result["reused"])
        self.assertEqual(len(result["artifact_sha256"]), 3)
        self.assertEqual(self.plan.candidate_exe.read_bytes(), self.image)
        self.assertEqual((self.game / core.BASE_EXE_NAME).read_bytes(), self.original)
        self.assertFalse(self.plan.manifest_path.exists())
        self.assertFalse(result["game_runtime_executed"])
        self.assertFalse(result["manual_input_proof"])
        self.assertFalse(result["promotion_ready"])

    def test_builder_is_called_with_explicit_minimap_correction(self):
        builder = SimpleNamespace(build_candidate=Mock(return_value=(b"", {}, "")))
        with patch.object(framed.importlib, "import_module", return_value=builder):
            REAL_BUILD(self.original, "1280x720")
        builder.build_candidate.assert_called_once_with(self.original, "1280x720", minimap_viewport=True)

    def test_repeat_preparation_reuses_only_identical_artifacts(self):
        framed.ensure_candidate(self.plan)
        first = {p.name: p.read_bytes() for p in self.plan.candidate_dir.iterdir()}
        self.metadata["generated_at"] = "later fixture"
        self.assertTrue(framed.ensure_candidate(self.plan)["reused"])
        self.assertEqual(first, {p.name: p.read_bytes() for p in self.plan.candidate_dir.iterdir()})

    def test_wrong_base_and_source_drift_fail_before_build_or_writes(self):
        (self.game / core.BASE_EXE_NAME).write_bytes(b"unknown input")
        with self.assertRaises(core.LauncherError):
            framed.ensure_candidate(self.plan)
        self.builder.assert_not_called()
        self.assertFalse(self.plan.candidate_dir.exists())
        (self.game / core.BASE_EXE_NAME).write_bytes(self.original)
        with patch.object(framed, "_bindings", side_effect=core.LauncherError("source mismatch")):
            with self.assertRaises(core.LauncherError):
                framed.ensure_candidate(self.plan)
        self.builder.assert_not_called()

    def test_wrong_builder_metadata_never_creates_a_candidate(self):
        changes = {"stage": "wrong", "resolution": "800x600", "output_sha256": "0" * 64,
                   "minimap_viewport": False, "validation_stage_only": False,
                   "runtime_executed": True, "manual_input_proof": True,
                   "promotion_ready": True, "source_sha256": {}}
        for key, value in changes.items():
            with self.subTest(key=key), patch.dict(self.metadata, {key: value}):
                with self.assertRaises(core.LauncherError):
                    framed.ensure_candidate(self.plan)
                self.assertFalse(self.plan.candidate_dir.exists())

    def test_existing_different_artifact_is_not_overwritten(self):
        self.plan.candidate_dir.mkdir(parents=True)
        self.plan.candidate_exe.write_bytes(b"existing foreign candidate")
        with self.assertRaises(core.LauncherError):
            framed.ensure_candidate(self.plan)
        self.assertEqual(self.plan.candidate_exe.read_bytes(), b"existing foreign candidate")
        self.assertFalse((self.plan.candidate_dir / framed.BUILD_REPORT).exists())

    def test_deployment_records_all_five_artifact_hashes(self):
        self.deploy()
        manifest = core.read_candidate_manifest(self.plan)
        self.assertEqual(len(manifest["artifact_sha256"]), 5)
        self.assertEqual(manifest["profile"], "framed")
        self.assertEqual(manifest["stage"], framed.STAGE)
        self.assertEqual(manifest["source_sha256"], self.bindings)
        framed.verify_launch(self.plan)

    def test_missing_wrapper_does_not_reuse_stale_deployment(self):
        result = self.deploy()
        (self.game / core.WRAPPER_DLL_NAME).unlink()
        state = framed.deploy_runtime_files(self.plan, result)
        self.assertEqual(state["wrapper"], "missing")
        self.assertEqual(state["manifest"], "not_written")

    def test_each_changed_artifact_blocks_launch_verification(self):
        self.deploy()
        for path in framed._paths(self.plan)[:5]:
            original = path.read_bytes()
            with self.subTest(path=path.name):
                path.write_bytes(original + b"tampered")
                with self.assertRaises(core.LauncherError):
                    framed.verify_launch(self.plan)
                path.write_bytes(original)
        framed.verify_launch(self.plan)

    def test_incomplete_wrong_profile_and_false_claim_manifests_fail(self):
        self.deploy()
        manifest = core.read_candidate_manifest(self.plan)
        for changes in ({"profile": "classic"}, {"minimap_viewport": False}, {"artifact_sha256": {}},
                        {"stage": "wrong"}, {"resolution": "800x600"}, {"source_sha256": {}},
                        {"manual_input_proof": True}, {"promotion_ready": True},
                        {"output_sha256": "0" * 64}, {"scaling_mode": "unknown"}):
            with self.subTest(changes=changes):
                self.plan.manifest_path.write_text(json.dumps(manifest | changes), encoding="utf-8")
                with self.assertRaises(core.LauncherError):
                    framed.verify_launch(self.plan)

    def test_missing_manifest_and_source_change_block_launch(self):
        with self.assertRaises(core.LauncherError):
            framed.verify_launch(self.plan)
        self.deploy()
        with patch.object(framed, "_bindings", return_value={"different": "c" * 64}):
            with self.assertRaises(core.LauncherError):
                framed.verify_launch(self.plan)

    def test_cleanup_preserves_classic_profile_and_original(self):
        self.deploy()
        classic = self.plan.candidates_root / self.plan.resolution
        classic.mkdir()
        (classic / "keep.txt").write_bytes(b"classic")
        core.clean_candidate_dir(self.plan)
        self.assertFalse(self.plan.candidate_dir.exists())
        self.assertEqual((classic / "keep.txt").read_bytes(), b"classic")
        self.assertEqual((self.game / core.BASE_EXE_NAME).read_bytes(), self.original)

    def test_forged_paths_and_linked_output_are_rejected(self):
        for changes in ({"stage": "classic"}, {"wrapper_target": self.game / "other.dll"},
                        {"candidate_dir": self.root / "outside"}):
            with self.subTest(changes=changes), self.assertRaises(core.LauncherError):
                framed.ensure_candidate(replace(self.plan, **changes))
        self.plan.candidate_dir.mkdir(parents=True)
        try:
            self.plan.candidate_exe.symlink_to(self.game / core.BASE_EXE_NAME)
        except OSError:
            self.skipTest("symbolic links unavailable on this host")
        with self.assertRaises(core.LauncherError):
            framed.ensure_candidate(self.plan)

    def test_prepare_cli_never_calls_launch_even_with_confirmation_flag(self):
        with patch.object(core, "launch_game") as launch:
            code, output, _ = self.cli("--profile", "framed", "--prepare", "--yes-launch")
        self.assertEqual(code, 0)
        self.assertIn('"game_runtime_executed": false', output)
        self.assertTrue(self.plan.candidate_exe.exists())
        launch.assert_not_called()

    def test_prepare_succeeds_without_wrapper_but_reports_not_deployed(self):
        (self.game / core.WRAPPER_DLL_NAME).unlink()
        code, output, _ = self.cli("--profile", "framed", "--prepare")
        self.assertEqual(code, 0)
        self.assertIn('"runtime_deployed": false', output)
        self.assertFalse(self.plan.manifest_path.exists())

    def test_cli_single_launch_flag_cannot_build_or_start(self):
        with patch.object(core, "launch_game") as launch:
            code, _, _ = self.cli("--profile", "framed", "--launch")
        self.assertEqual(code, 2)
        self.builder.assert_not_called()
        launch.assert_not_called()

    def test_cli_confirmed_launch_uses_verified_profile_and_existing_core_gate(self):
        with patch.object(core, "launch_game", return_value=SimpleNamespace(pid=123)) as launch:
            code, _, errors = self.cli("--profile", "framed", "--launch", "--yes-launch")
        self.assertEqual(code, 0, errors)
        launch.assert_called_once_with(self.plan, confirmed=True)

    def test_cli_integrity_error_never_reaches_process_start(self):
        deploy = framed.deploy_runtime_files
        def corrupt(*args, **kwargs):
            result = deploy(*args, **kwargs)
            self.plan.candidate_exe.write_bytes(b"changed after preparation")
            return result
        with patch.object(framed, "deploy_runtime_files", side_effect=corrupt), patch.object(core, "launch_game") as launch:
            code, _, errors = self.cli("--profile", "framed", "--launch", "--yes-launch")
        self.assertEqual(code, 1)
        self.assertIn("changed", errors)
        launch.assert_not_called()

    def test_dry_run_is_read_only_and_reports_profile_source_status(self):
        report = SimpleNamespace(ready_to_patch=True, to_dict=lambda: {})
        with patch.object(core, "check_environment", return_value=report), patch.object(framed, "source_status", return_value={"passed": True}):
            code, output, _ = self.cli("--profile", "framed", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["profile"], "framed")
        self.assertFalse(self.plan.candidate_dir.exists())
        self.builder.assert_not_called()


class EntryPointTests(unittest.TestCase):
    def test_classic_is_default_and_modes_are_exclusive(self):
        self.assertEqual(run.parse_args([]).profile, "classic")
        for flags in (("--prepare", "--launch"), ("--prepare", "--dry-run"), ("--profile", "unknown")):
            with self.subTest(flags=flags), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                run.parse_args(list(flags))

    def test_source_pin_preflight_matches_existing_unmodified_builder(self):
        status = framed.source_status()
        self.assertTrue(status["passed"], status)
        self.assertEqual(status["builder_sha256"], framed.BUILDER_SHA256)
        self.assertEqual(len(status["checks"]), 14)

    def test_packaged_launcher_refuses_framed_without_importing_builder(self):
        with patch.object(sys, "frozen", True, create=True), patch.object(framed.importlib, "import_module") as importer:
            self.assertFalse(framed.source_status()["passed"])
            with self.assertRaises(core.LauncherError):
                framed.plan_candidate()
            importer.assert_not_called()

    def test_gui_profile_badges_and_backend_change_without_launch(self):
        import gui
        app = object.__new__(gui.LauncherApp)
        app.profile_var = SimpleNamespace(get=lambda: "framed")
        app.profile_label = Mock()
        button = Mock()
        app.resolution_buttons = [(button, SimpleNamespace(key="800x600", status="stable"))]
        app.experimental_warned = True
        app.on_profile_change()
        self.assertFalse(app.experimental_warned)
        self.assertIs(app._backend(), framed)
        button.configure.assert_called_with(text="800x600  [Experimental]")
        app.profile_var = SimpleNamespace(get=lambda: "classic")
        app.on_profile_change()
        self.assertIs(app._backend(), core)
        button.configure.assert_called_with(text="800x600  [Stable]")

    def test_framed_gui_does_not_overwrite_classic_settings(self):
        import gui
        app = object.__new__(gui.LauncherApp)
        app.profile_var = SimpleNamespace(get=lambda: "framed")
        with patch.object(gui.settings_mod, "save_settings") as save:
            app._save_settings()
        save.assert_not_called()

    def test_framed_gui_cancel_never_prepares_or_launches_even_at_stable_resolution(self):
        import gui
        app = object.__new__(gui.LauncherApp)
        app.profile_var = SimpleNamespace(get=lambda: "framed")
        app.experimental_warned = False
        app.environment = SimpleNamespace(base_exe=SimpleNamespace(passed=True), running_processes=SimpleNamespace(passed=True))
        app.refresh_environment = Mock()
        app._selected_option = Mock(return_value=SimpleNamespace(is_experimental=False))
        app._selected_plan = Mock(side_effect=AssertionError("unexpected preparation"))
        app.log = Mock()
        with patch.object(gui.messagebox, "askokcancel", return_value=False) as confirm:
            app._play_sequence()
        confirm.assert_called_once()
        app._selected_plan.assert_not_called()


if __name__ == "__main__":
    unittest.main()
