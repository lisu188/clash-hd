"""Offline complete-HD launcher safety and provenance fixtures; no runtime."""
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
sys.path.insert(0, str(ROOT / "src/launcher"))
import bootstrap
bootstrap.ensure_repo_paths()
import completehd
import core
import framed
import presets
import run
from src.display_plan import resolve_display_plan
from src.patcher import complete_hd_candidate as builder


class CompleteHdLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="clash-completehd-launcher-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.game = self.root / "game"
        self.game.mkdir()
        self.original = b"synthetic fixture original; never executed"
        self.image = self.original + b" synthetic complete-HD changes"
        self.probe = "synthetic offline fixture probe\n"
        (self.game / core.BASE_EXE_NAME).write_bytes(self.original)
        (self.game / core.WRAPPER_DLL_NAME).write_bytes(b"synthetic wrapper; never loaded")
        self.metadata = {"schema": 1, "stage": builder.STAGE, "resolution": "1920x1080",
                         "recipe_revision": builder.REVISION, "candidate_sha256": core.sha256_bytes(self.image),
                         "source_hashes": {"fixture-only.py": "a" * 64},
                         "patch_records": [{"fixture_only": True}], "probe_sha256": core.sha256_bytes(self.probe.encode())}
        self.recipe = SimpleNamespace(BASE_SHA256=core.sha256_bytes(self.original), STAGE=builder.STAGE,
            RESOLUTIONS=builder.RESOLUTIONS, _write_bundle=builder._write_bundle,
            build_candidate=Mock(side_effect=lambda original, resolution: (self.image, self.metadata.copy(), self.probe)))
        self.addCleanup(patch.stopall)
        patch.object(completehd, "_builder", return_value=self.recipe).start()
        patch.object(completehd, "CANDIDATE_ROOT", self.root / "candidates").start()
        self.plan = completehd.plan_candidate(resolution="1920x1080", clash_dir=self.game,
            candidates_root=self.root / "candidates", expected_base_sha=self.recipe.BASE_SHA256)

    def deploy(self):
        result = completehd.ensure_candidate(self.plan)
        completehd.deploy_runtime_files(self.plan, result)
        return result

    def test_paths_and_geometry_are_separate_from_classic_and_framed(self):
        classic = core.plan_candidate()
        framed_plan = framed.plan_candidate()
        self.assertEqual(classic.resolution, "800x600")
        self.assertEqual(self.plan.candidate_dir.parts[-2:], ("completehd-validation", "1920x1080"))
        self.assertEqual(len({classic.candidate_dir, framed_plan.candidate_dir, self.plan.candidate_dir}), 3)
        self.assertFalse(self.plan.candidates_root.exists())
        display = core.display_for_plan(self.plan)
        self.assertEqual(display.terrain, (32, 16, 1887, 1063))
        self.assertEqual(display.full_tiles, (29, 16))
        self.assertEqual(display.coverage_tiles, (29, 17))
        self.assertEqual(display.partial_pixels, (0, 24))
        self.assertEqual(len(display.frame_bands), 4)
        self.assertEqual(len(display.action_cells), 6)

    def test_unknown_resolution_stage_feature_and_profile_rejected(self):
        for resolution in ("1600x900", "1366x768", "1921x1080", "640x480"):
            with self.subTest(resolution=resolution), self.assertRaises(core.LauncherError):
                completehd.plan_candidate(resolution=resolution)
        with self.assertRaises(core.LauncherError):
            completehd.plan_candidate(stage=core.patch_clash95_hd.DEFAULT_STAGE)
        with self.assertRaises(ValueError):
            resolve_display_plan(renderer="completehd", minimap_viewport=False)
        with self.assertRaises(core.LauncherError):
            completehd.ensure_candidate(replace(self.plan, renderer="classic"))

    def test_builder_bundle_matches_shared_serialization_and_has_no_runtime(self):
        with patch.object(core, "launch_game", side_effect=AssertionError("no runtime")):
            result = completehd.ensure_candidate(self.plan)
        self.recipe.build_candidate.assert_called_with(self.original, "1920x1080")
        self.assertEqual(self.plan.candidate_exe.read_bytes(), self.image)
        self.assertEqual(self.plan.candidate_exe.with_suffix(".candidate.json").read_bytes(),
                         (json.dumps(self.metadata, indent=2) + "\n").encode())
        self.assertEqual(self.plan.candidate_exe.with_suffix(".cdb").read_bytes(), self.probe.encode())
        self.assertEqual(len(result["artifact_sha256"]), 3)
        self.assertFalse(result["game_runtime_executed"])
        self.assertFalse(result["manual_input_proof"])
        self.assertFalse(result["promotion_ready"])
        self.assertEqual(self.plan.base_exe.read_bytes(), self.original)

    def test_existing_bundle_is_reused_only_when_identical(self):
        completehd.ensure_candidate(self.plan)
        self.assertTrue(completehd.ensure_candidate(self.plan)["reused"])
        for name in ("candidate", "metadata", "probe"):
            path = completehd._paths(self.plan)[("candidate", "metadata", "probe").index(name)]
            old = path.read_bytes()
            path.write_bytes(old + b"changed")
            with self.assertRaises(core.LauncherError):
                completehd.ensure_candidate(self.plan)
            self.assertEqual(path.read_bytes(), old + b"changed")
            path.write_bytes(old)

    def test_unknown_original_or_unsafe_paths_fail_before_build(self):
        self.plan.base_exe.write_bytes(b"unknown original")
        with self.assertRaises(core.LauncherError):
            completehd.ensure_candidate(self.plan)
        self.recipe.build_candidate.assert_not_called()
        with self.assertRaises(core.LauncherError):
            completehd.plan_candidate(candidates_root=self.root / "outside", clash_dir=self.game)
        self.assertFalse(self.plan.candidates_root.exists())

    def test_launch_verification_rebuilds_candidate_and_binds_wrapper(self):
        self.deploy()
        completehd.verify_launch(self.plan)
        for path in completehd._paths(self.plan)[:5]:
            old = path.read_bytes()
            path.write_bytes(old + b"tamper")
            with self.subTest(path=path), self.assertRaises(core.LauncherError):
                completehd.verify_launch(self.plan)
            path.write_bytes(old)

    def test_rehashed_tampering_does_not_replace_reconstruction(self):
        self.deploy()
        self.plan.candidate_exe.write_bytes(b"wrong candidate")
        manifest = core.read_candidate_manifest(self.plan)
        bad_sha = core.sha256_bytes(self.plan.candidate_exe.read_bytes())
        manifest["artifact_sha256"][self.plan.candidate_exe.name] = bad_sha
        manifest["output_sha256"] = bad_sha
        self.plan.manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(core.LauncherError):
            completehd.verify_launch(self.plan)

    def test_cli_prepare_does_not_launch_and_double_flag_is_preserved(self):
        with patch.object(run, "build_plan", return_value=self.plan), \
             patch.object(core, "launch_game", side_effect=AssertionError("unexpected runtime")), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(run.main(["--profile", "completehd", "--launch"]), 2)
            self.assertEqual(run.main(["--profile", "completehd", "--prepare"]), 0)
        with self.assertRaises(PermissionError):
            core.launch_game(self.plan, confirmed=False)

    def test_manifest_advertises_only_six_experimental_complete_resolutions(self):
        manifest = presets.load_manifest()
        options = presets.load_options(manifest, "completehd")
        self.assertEqual({option.key for option in options}, set(builder.RESOLUTIONS))
        self.assertTrue(all(option.is_experimental for option in options))
        self.assertEqual(presets.default_key(manifest, "completehd"), "800x600")
        self.assertEqual(presets.default_key(manifest), "800x600")
        manifest["profiles"]["completehd"]["resolutions"]["1920x1080"]["status"] = "validated"
        with self.assertRaises(presets.ManifestError):
            presets.validate_manifest(manifest)


class SourceOnlyCompleteHdTests(unittest.TestCase):
    def test_frozen_source_only_profile_fails_without_importing_builder(self):
        with patch.object(sys, "frozen", True, create=True), \
             patch.object(completehd.importlib, "import_module", side_effect=AssertionError("no source import")):
            self.assertFalse(completehd.source_status()["passed"])
            with self.assertRaises(core.LauncherError):
                completehd.plan_candidate()

    def test_real_source_preflight_and_six_geometry_plans_are_read_only(self):
        status = completehd.source_status()
        self.assertTrue(status["passed"], status)
        for resolution in builder.RESOLUTIONS:
            complete = resolve_display_plan(renderer="completehd", resolution=resolution)
            reference = resolve_display_plan(renderer="framed", resolution=resolution)
            self.assertEqual((complete.terrain, complete.full_tiles, complete.coverage_tiles, complete.action_cells),
                             (reference.terrain, reference.full_tiles, reference.coverage_tiles, reference.action_cells))
            self.assertEqual(complete.stage, builder.STAGE)

    def test_enabled_minimap_source_drift_fails_preflight(self):
        import build_framed_candidate
        path = ROOT / build_framed_candidate.MINIMAP_SOURCE
        read = Path.read_bytes
        with patch.object(Path, "read_bytes", lambda item: b"synthetic source drift" if item == path else read(item)):
            status = completehd.source_status()
        self.assertFalse(status["passed"], status)
        self.assertFalse(status["checks"][build_framed_candidate.MINIMAP_SOURCE]["passed"])


if __name__ == "__main__":
    unittest.main()
