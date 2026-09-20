"""Source-only widget-profile tests with synthetic bytes; no game is launched."""
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
import copy
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
import gui
import modalwidgets
import presets
import run
from src.display_plan import resolve_display_plan
from tools import build_framed_modal_widgets_candidate as builder


class WidgetLauncherTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="clash-widget-launcher-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.game = self.root / "game"; self.game.mkdir()
        self.original = b"synthetic original, never run"
        self.image = self.original + b" synthetic widget candidate"
        self.probe = "synthetic widget probe\n"
        (self.game / core.BASE_EXE_NAME).write_bytes(self.original)
        (self.game / core.WRAPPER_DLL_NAME).write_bytes(b"synthetic wrapper, never loaded")
        self.metadata = dict(schema=1, stage=builder.STAGE, recipe_revision=builder.REVISION,
            resolution="1920x1080", candidate_sha256=core.sha256_bytes(self.image),
            probe_sha256=core.sha256_bytes(self.probe.encode()), source_hashes={"fixture-only.py":"a"*64},
            edits=[{"fixture_only":True},{"fixture_only":True}])
        self.recipe = SimpleNamespace(STAGE=builder.STAGE, RESOLUTIONS=builder.complete.RESOLUTIONS,
            BASE_SHA256=core.sha256_bytes(self.original), _write_bundle=builder.complete._write_bundle,
            build_candidate=Mock(side_effect=lambda original,resolution: (self.image, self.metadata.copy(), self.probe)))
        patched = patch.object(completehd, "_builder", return_value=self.recipe)
        patched.start(); self.addCleanup(patched.stop)
        patched = patch.object(completehd, "CANDIDATE_ROOT", self.root/"candidates")
        patched.start(); self.addCleanup(patched.stop)
        self.plan = modalwidgets.plan_candidate(resolution="1920x1080", clash_dir=self.game,
            candidates_root=self.root/"candidates", expected_base_sha=self.recipe.BASE_SHA256)

    def deploy(self):
        result = modalwidgets.ensure_candidate(self.plan)
        modalwidgets.deploy_runtime_files(self.plan,result)
        return result

    def test_widget_candidate_paths_do_not_alias_other_profiles(self):
        self.assertEqual(self.plan.renderer,"modalwidgets")
        self.assertEqual(self.plan.stage,builder.STAGE)
        self.assertEqual(self.plan.candidate_dir.parts[-2:],("modalwidgets-validation","1920x1080"))
        paths = completehd._paths(self.plan)
        self.assertEqual(len(paths),len(set(paths)))
        for name in ("completehd-validation","framed-validation"):
            self.assertNotIn(name,self.plan.candidate_exe.parts)
        self.assertFalse(self.plan.candidates_root.exists())

    def test_exact_widget_bundle_and_manifest_preserve_recipe_and_revision(self):
        with patch.object(core,"launch_game",side_effect=AssertionError("no game")):
            result=self.deploy()
        manifest=core.read_candidate_manifest(self.plan)
        self.assertEqual(self.plan.candidate_exe.read_bytes(),self.image)
        self.assertEqual(self.plan.candidate_exe.with_suffix(".candidate.json").read_bytes(),
                         (json.dumps(self.metadata,indent=2)+"\n").encode())
        self.assertEqual(result["patch_count"],2)
        self.assertEqual(result["profile"],"modalwidgets")
        self.assertEqual(result["display_plan"]["recipe_revision"],builder.REVISION)
        self.assertEqual(manifest["warning"],modalwidgets.WARNING)
        self.assertEqual(manifest["stage"],builder.STAGE)
        self.assertFalse(manifest["promotion_ready"])
        self.assertEqual(self.plan.base_exe.read_bytes(),self.original)
        self.assertFalse(result["game_runtime_executed"])
        self.assertFalse(result["manual_input_proof"])
        self.assertTrue(modalwidgets.ensure_candidate(self.plan)["reused"])
        modalwidgets.verify_launch(self.plan)

    def test_rehashed_exe_probe_manifest_or_wrapper_cannot_bypass_verification(self):
        self.deploy()
        for path in completehd._paths(self.plan)[:5]:
            old=path.read_bytes(); path.write_bytes(old+b"tamper")
            with self.subTest(path=path.name),self.assertRaises(core.LauncherError):
                modalwidgets.verify_launch(self.plan)
            path.write_bytes(old)
        manifest=core.read_candidate_manifest(self.plan)
        self.plan.candidate_exe.write_bytes(b"wrong EXE")
        digest=core.sha256_bytes(b"wrong EXE")
        manifest["output_sha256"]=digest; manifest["artifact_sha256"][self.plan.candidate_exe.name]=digest
        self.plan.manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(core.LauncherError):modalwidgets.verify_launch(self.plan)

    def test_plan_cannot_mix_widget_and_complete_stage_or_output(self):
        for changed in (replace(self.plan,renderer="completehd"),replace(self.plan,stage=completehd.STAGE),
                        replace(self.plan,candidate_dir=self.plan.candidate_dir.parent/"completehd-validation"),
                        replace(self.plan,base_exe=self.plan.candidate_exe)):
            with self.subTest(plan=changed.renderer),self.assertRaises(core.LauncherError):
                modalwidgets.ensure_candidate(changed)
        with self.assertRaises(core.LauncherError):
            modalwidgets.plan_candidate(stage=completehd.STAGE)
        for resolution in ("1600x900","640x480","1921x1080"):
            with self.assertRaises(core.LauncherError):modalwidgets.plan_candidate(resolution=resolution)
        self.assertFalse(self.plan.candidates_root.exists())

    def test_builder_returned_recipe_and_bundle_identifiers_must_match(self):
        changes = dict(stage=completehd.STAGE,recipe_revision="complete_hd_v1",resolution="800x600",
                       candidate_sha256="b"*64,probe_sha256="b"*64)
        for key,value in changes.items():
            old=self.metadata[key];self.metadata[key]=value
            with self.subTest(field=key),self.assertRaisesRegex(core.LauncherError,"different recipe"):
                modalwidgets.ensure_candidate(self.plan)
            self.metadata[key]=old
        self.assertFalse(self.plan.candidates_root.exists())

    def test_unknown_original_and_unsafe_output_fail_before_construction(self):
        self.plan.base_exe.write_bytes(b"unknown")
        with self.assertRaises(core.LauncherError):modalwidgets.ensure_candidate(self.plan)
        self.recipe.build_candidate.assert_not_called()
        with self.assertRaises(core.LauncherError):
            modalwidgets.plan_candidate(clash_dir=self.game,candidates_root=self.root/"outside")
        self.assertFalse(self.plan.candidates_root.exists())

    def test_prepare_remains_nonexecuting_and_play_requires_both_flags(self):
        with patch.object(run,"build_plan",return_value=self.plan), \
             patch.object(core,"launch_game",side_effect=AssertionError("no process")), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(run.main(["--profile","modalwidgets","--launch"]),2)
            self.assertEqual(run.main(["--profile","modalwidgets","--prepare"]),0)
        with self.assertRaises(PermissionError):core.launch_game(self.plan,confirmed=False)


class WidgetProfileSourceTests(unittest.TestCase):
    def test_real_builder_source_preflight_and_geometry_do_not_build_or_launch(self):
        with patch.object(builder,"build_candidate",side_effect=AssertionError("unexpected construction")):
            status=modalwidgets.source_status();self.assertTrue(status["passed"],status)
            adapter=completehd._builder("modalwidgets")
            self.assertEqual(adapter.STAGE,builder.STAGE)
            self.assertEqual(adapter.REVISION,builder.REVISION)
            self.assertEqual(adapter.BASE_SHA256,builder.pe.ORIGINAL_SHA256)
            for resolution in builder.complete.RESOLUTIONS:
                display=resolve_display_plan(renderer="modalwidgets",resolution=resolution)
                complete=resolve_display_plan(renderer="completehd",resolution=resolution)
                self.assertEqual((display.terrain,display.action_cells,display.native_offset),
                                 (complete.terrain,complete.action_cells,complete.native_offset))
                self.assertNotEqual(display.build_identity("a"*64,{"x.py":"b"*64}),
                                    complete.build_identity("a"*64,{"x.py":"b"*64}))
                self.assertEqual(display.stage,builder.STAGE)
            self.assertFalse(status["runtime_executed"])

    def test_text_source_drift_and_frozen_launcher_refuse_widget_profile(self):
        path=ROOT/"src/patcher/framed_modal_primary_text.py";read=Path.read_bytes
        with patch.object(Path,"read_bytes",lambda p: b"drift" if p==path else read(p)):
            status=modalwidgets.source_status()
        self.assertFalse(status["passed"])
        self.assertFalse(status["checks"]["src/patcher/framed_modal_primary_text.py"]["passed"])
        with patch.object(sys,"frozen",True,create=True), \
             patch.object(completehd.importlib,"import_module",side_effect=AssertionError("no source imports")):
            self.assertFalse(modalwidgets.source_status()["passed"])
            with self.assertRaises(core.LauncherError):modalwidgets.plan_candidate()

    def test_manifest_keeps_classic_default_and_six_experimental_widget_options(self):
        manifest=presets.load_manifest();options=presets.load_options(manifest,"modalwidgets")
        self.assertEqual(manifest["default_renderer"],"classic")
        self.assertEqual(manifest["default"],"800x600")
        self.assertEqual(presets.default_key(manifest,"modalwidgets"),"800x600")
        self.assertEqual({o.key for o in options},set(builder.complete.RESOLUTIONS))
        self.assertTrue(all(o.is_experimental and o.evidence is None for o in options))
        for field,value in (("stage",completehd.STAGE),("default","1024x768"),("recipe_revision","complete_hd_v1")):
            bad=copy.deepcopy(manifest);bad["profiles"]["modalwidgets"][field]=value
            with self.assertRaises(presets.ManifestError):presets.validate_manifest(bad)
        for status in ("validated","stable"):
            bad=copy.deepcopy(manifest);bad["profiles"]["modalwidgets"]["resolutions"]["1920x1080"]["status"]=status
            with self.assertRaises(presets.ManifestError):presets.validate_manifest(bad)
        with self.assertRaises(ValueError):resolve_display_plan(renderer="modalwidgets",minimap_viewport=False)
        with self.assertRaises(core.LauncherError):completehd._builder("wrong")

    def test_cli_inspection_and_gui_routing_use_widget_backend_without_launch(self):
        output=io.StringIO()
        with redirect_stdout(output),patch.object(core,"launch_game",side_effect=AssertionError("no process")):
            self.assertEqual(run.main(["--profile","modalwidgets","--describe-plan","--resolution","1920x1080"]),0)
        result=json.loads(output.getvalue())
        self.assertEqual(result["plan"]["stage"],builder.STAGE)
        self.assertFalse(result["game_runtime_executed"])
        self.assertFalse(result["candidate_paths_validated"])
        app=SimpleNamespace(profile_var=SimpleNamespace(get=lambda:"modalwidgets"))
        self.assertIs(gui.LauncherApp._backend(app),modalwidgets)
        self.assertIn("experimental",gui.PROFILE_NAMES["modalwidgets"])
        with patch.object(run.settings_mod,"load_settings",return_value={"last_resolution":"1366x768","scaling_mode":"integer",
                "clash_dir":"C:/Clash","candidates_root":"C:/ClashTests/launcher"}), \
             patch.object(modalwidgets,"plan_candidate",return_value=object()) as plan:
            run.build_plan(run.parse_args(["--profile","modalwidgets"]))
        self.assertEqual(plan.call_args.kwargs["resolution"],"800x600")


if __name__ == "__main__":unittest.main(verbosity=2)
