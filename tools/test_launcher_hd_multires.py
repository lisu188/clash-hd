"""Twelve-cell launcher routing and deterministic provenance, without a game."""
from __future__ import annotations

import copy
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src/launcher")]
import bootstrap
bootstrap.ensure_repo_paths()
import classic
import completehd
import core
import framed
import modalwidgets
import multires
import presets
from src import display_plan
from src.patcher import complete_hd_candidate as writer

BACKENDS = {"classic": classic, "framed": framed, "completehd": completehd, "modalwidgets": modalwidgets}


class MultiresLauncherTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="hd-multires-launcher-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.game = self.root / "game"
        self.game.mkdir()
        self.original = b"synthetic original; never executed"
        (self.game / core.BASE_EXE_NAME).write_bytes(self.original)
        (self.game / core.WRAPPER_DLL_NAME).write_bytes(b"synthetic wrapper; never loaded")
        self.pins = {"src/launcher/multires.py": core.sha256_bytes((ROOT / "src/launcher/multires.py").read_bytes())}
        self.capabilities = {name: name != "classic" for name in BACKENDS}
        self.component = SimpleNamespace(REVISION=display_plan.HD_MULTIRES_REVISION,
            RESOLUTIONS=display_plan.HD_MULTIRES_RESOLUTIONS,
            stage=display_plan.multires_stage, bounded_small_world=lambda name: self.capabilities[name])
        self.builder_calls = []
        self.metadata_changes = {}
        for guard in (
                patch.dict(sys.modules, {"src.patcher.hd_multires_candidate": self.component}),
                patch.object(multires, "_builder", side_effect=self.adapter),
                patch.object(completehd, "CANDIDATE_ROOT", self.root / "candidates"),
                patch.object(core, "launch_game", side_effect=AssertionError("no runtime in source fixtures"))):
            guard.start()
            self.addCleanup(guard.stop)

    def adapter(self, profile):
        def build(original, resolution):
            self.builder_calls.append((original, profile, resolution))
            image = original + f"|{profile}/{resolution}".encode()
            probe = f"synthetic {profile}/{resolution}\n"
            metadata = dict(profile=profile, stage=display_plan.multires_stage(profile),
                recipe_revision=display_plan.HD_MULTIRES_REVISION, resolution=resolution,
                candidate_sha256=core.sha256_bytes(image), probe_sha256=core.sha256_bytes(probe.encode()),
                source_hashes=self.pins.copy(), patch_records=[{"synthetic": True}],
                bounded_small_world_integrated=self.capabilities[profile], runtime_verified=False,
                manual_input_proof=False, promotion_ready=False)
            metadata.update(self.metadata_changes)
            return image, metadata, probe
        return SimpleNamespace(BASE_SHA256=core.sha256_bytes(self.original),
            STAGE=display_plan.multires_stage(profile), RESOLUTIONS=display_plan.HD_MULTIRES_RESOLUTIONS,
            build_candidate=build, source_hashes=lambda: self.pins.copy(),
            _write_bundle=writer._write_bundle, __file__=str(ROOT / "src/launcher/multires.py"))

    def plan(self, profile, resolution="1920x1080"):
        return BACKENDS[profile].plan_candidate(resolution=resolution, clash_dir=self.game,
            candidates_root=self.root / "candidates", expected_base_sha=core.sha256_bytes(self.original))

    def test_twelve_exact_cells_have_isolated_identity_and_preserve_default(self):
        directories = set()
        for profile in BACKENDS:
            for resolution in display_plan.HD_MULTIRES_RESOLUTIONS:
                plan = self.plan(profile, resolution)
                display = core.display_for_plan(plan)
                self.assertEqual(display.recipe_revision, "hd_multires_v1")
                self.assertEqual(plan.candidate_dir.parts[-4:], ("multires", "hd_multires_v1", profile, resolution))
                self.assertEqual(display.minimap_viewport, profile != "classic")
                self.assertEqual(presets.resolution_info(resolution, renderer=profile)["status"], "experimental")
                self.assertFalse(display.to_dict()["game_runtime_executed"])
                directories.add(plan.candidate_dir)
        self.assertEqual(len(directories), 12)
        self.assertFalse((self.root / "candidates").exists())
        self.assertFalse(self.builder_calls)
        fallback = classic.plan_candidate(resolution="800x600", clash_dir=self.game, candidates_root=self.root / "candidates")
        self.assertEqual(fallback.stage, core.patch_clash95_hd.DEFAULT_STAGE)
        self.assertEqual(presets.default_key(), "800x600")

    def test_every_backend_builds_and_reverifies_its_exact_bundle_without_runtime(self):
        for profile in BACKENDS:
            for resolution in display_plan.HD_MULTIRES_RESOLUTIONS:
                with self.subTest(profile=profile, resolution=resolution):
                    backend, plan = BACKENDS[profile], self.plan(profile, resolution)
                    record = backend.ensure_candidate(plan)
                    backend.deploy_runtime_files(plan, record)
                    backend.verify_launch(plan)
                    self.assertTrue(backend.ensure_candidate(plan)["reused"])
                    self.assertEqual(record["profile"], profile)
                    self.assertEqual(record["source_sha256"], self.pins)
                    self.assertFalse(record["game_runtime_executed"])
                    self.assertFalse(record["manual_input_proof"])
                    self.assertFalse(record["promotion_ready"])
        self.assertEqual((self.game / core.BASE_EXE_NAME).read_bytes(), self.original)
        self.assertEqual({(p, r) for _, p, r in self.builder_calls},
                         {(p, r) for p in BACKENDS for r in display_plan.HD_MULTIRES_RESOLUTIONS})

    def test_rehashed_tampering_and_cross_cell_metadata_cannot_replace_reconstruction(self):
        plan = self.plan("framed")
        record = framed.ensure_candidate(plan)
        framed.deploy_runtime_files(plan, record)
        for path in completehd._paths(plan)[:5]:
            original = path.read_bytes()
            path.write_bytes(original + b"tamper")
            with self.subTest(path=path.name), self.assertRaises(core.LauncherError):
                framed.verify_launch(plan)
            path.write_bytes(original)
        plan.candidate_exe.write_bytes(b"forged")
        manifest = core.read_candidate_manifest(plan)
        manifest["output_sha256"] = core.sha256_bytes(b"forged")
        manifest["artifact_sha256"][plan.candidate_exe.name] = manifest["output_sha256"]
        plan.manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(core.LauncherError):
            framed.verify_launch(plan)
        with self.assertRaises(core.LauncherError):
            completehd.ensure_candidate(replace(plan, renderer="completehd"))

    def test_changed_recipe_sources_capability_or_acceptance_reject_before_writes(self):
        plan = self.plan("modalwidgets")
        cases = ({"profile": "completehd"}, {"source_hashes": {"wrong.py": "a" * 64}},
                 {"bounded_small_world_integrated": False}, {"runtime_verified": True},
                 {"recipe_revision": "complete_hd_v1"}, {"resolution": "3840x2160"})
        for change in cases:
            self.metadata_changes = change
            with self.subTest(change=change), self.assertRaises(core.LauncherError):
                modalwidgets.ensure_candidate(plan)
            self.assertFalse(plan.candidate_dir.exists())
        self.metadata_changes = {}
        plan.base_exe.write_bytes(b"unknown")
        count = len(self.builder_calls)
        with self.assertRaises(core.LauncherError):
            modalwidgets.ensure_candidate(plan)
        self.assertEqual(len(self.builder_calls), count)

    def test_small_world_capability_is_per_profile_and_does_not_promote_legacy(self):
        for profile in BACKENDS:
            plan = core.display_for_plan(self.plan(profile, "3840x2160"))
            world = plan.world_view(1, 1, 99, 99)
            self.assertFalse(world.native_full_loop_safe)
            self.assertEqual(world.scroll, (0, 0))
            self.assertEqual(world.to_dict()["bounded_renderer_installed"], self.capabilities[profile])
            with self.assertRaises(display_plan.DisplayPlanError):
                world.require_native_full_loop()
            if self.capabilities[profile]:
                world.require_world_rendering()
            else:
                with self.assertRaises(display_plan.DisplayPlanError):
                    world.require_world_rendering()
            legacy_stage = presets.load_manifest()["profiles"][profile]["stage"]
            legacy = display_plan.resolve_display_plan(renderer=profile, resolution="1920x1080", stage=legacy_stage)
            self.assertFalse(legacy.bounded_world_renderer)
            with self.assertRaises(display_plan.DisplayPlanError):
                legacy.world_view(1, 1).require_native_full_loop()

    def test_classic_bounded_partial_cells_retain_its_native_ui_and_geometry(self):
        self.capabilities["classic"] = True
        for resolution in display_plan.HD_MULTIRES_RESOLUTIONS:
            display = core.display_for_plan(self.plan("classic", resolution))
            width, height = map(int, resolution.split("x"))
            self.assertEqual(display.terrain, (32, 16, width - 1, height - 1))
            self.assertEqual(display.coverage_tiles, ((width - 32 + 63) // 64, (height - 16 + 63) // 64))
            self.assertEqual(display.partial_pixels, ((width - 32) % 64, (height - 16) % 64))
            self.assertEqual(display.frame_bands, ())
            self.assertEqual(display.action_cells, ())
            self.assertFalse(display.minimap_viewport)
            self.assertIn("native Classic UI", display.to_dict()["coverage_policy"])
            display.world_view(1, 1).require_world_rendering()

    def test_manifest_successor_recipe_is_closed_and_cannot_inherit_stable_badges(self):
        manifest = presets.load_manifest()
        for profile in BACKENDS:
            for field, value in (("stage", "unknown"), ("recipe_revision", "unknown"),
                                 ("resolutions", ["1920x1080"])):
                bad = copy.deepcopy(manifest)
                bad["profiles"][profile]["multires_recipe"][field] = value
                with self.subTest(profile=profile, field=field), self.assertRaises(presets.ManifestError):
                    presets.validate_manifest(bad)
        self.assertEqual(presets.resolution_info("800x600")["status"], "stable")
        for profile in BACKENDS:
            self.assertIsNone(presets.resolution_info("1920x1080", renderer=profile)["evidence_references"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
