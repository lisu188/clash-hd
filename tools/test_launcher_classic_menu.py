"""Wide Classic launcher routing; synthetic bundles never execute a game."""
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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/launcher'))
import bootstrap
bootstrap.ensure_repo_paths()
import classic
import completehd
import core
import gui
import presets
import run
from src.patcher import classic_menu_candidate as builder
from src.patcher import complete_hd_candidate as complete


class ClassicMenuRoutingTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='classic-menu-launcher-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve();self.game=self.root/'game';self.game.mkdir()
        (self.game/core.BASE_EXE_NAME).write_bytes(b'synthetic original')
        (self.game/core.WRAPPER_DLL_NAME).write_bytes(b'synthetic wrapper')
        self.args=dict(clash_dir=self.game,candidates_root=self.root/'candidates')
        guard=patch.object(completehd,'CANDIDATE_ROOT',self.root/'candidates');guard.start();self.addCleanup(guard.stop)

    def test_native_defaults_and_explicit_legacy_stage_keep_exact_core_plan(self):
        for resolution in ('800x600','1024x768'):
            with patch.object(completehd,'_builder',side_effect=AssertionError('no extension')):
                self.assertEqual(classic.plan_candidate(resolution=resolution,**self.args),core.plan_candidate(resolution=resolution,**self.args))
        stage=core.patch_clash95_hd.DEFAULT_STAGE
        self.assertEqual(classic.plan_candidate(resolution='1920x1080',stage=stage,**self.args),
                         core.plan_candidate(resolution='1920x1080',stage=stage,**self.args))
        self.assertFalse(self.args['candidates_root'].exists())

    def test_affected_presets_use_new_identity_without_aliasing_old_candidates(self):
        for resolution in ('1280x720','1280x960','1366x768','1920x1080','2560x1440','3440x1440','3840x2160'):
            with self.subTest(resolution=resolution):
                plan=classic.plan_candidate(resolution=resolution,**self.args)
                old=core.plan_candidate(resolution=resolution,**self.args)
                expected=presets.resolve_plan(renderer='classic',resolution=resolution)
                self.assertEqual((plan.stage,expected.recipe_revision),(builder.STAGE,builder.REVISION))
                self.assertEqual(plan.renderer,'classic')
                self.assertEqual(plan.candidate_dir.parts[-2:],('classic-menu-validation',resolution))
                self.assertNotEqual(plan.candidate_exe,old.candidate_exe)
                self.assertEqual(core.display_for_plan(plan).terrain,core.display_for_plan(old).terrain)
                self.assertFalse(expected.minimap_viewport)
        for resolution in ('1144x768','1600x900'):
            self.assertEqual(classic.plan_candidate(resolution=resolution,**self.args).stage,builder.STAGE)

    def test_default_manifest_preserves_options_and_rejects_wrong_routing_metadata(self):
        m=presets.load_manifest();self.assertEqual(m['default'],'800x600')
        self.assertEqual(m['default_renderer'],'classic')
        self.assertEqual(len(m['profiles']['classic']['resolutions']),9)
        for key,value in (('minimum_width',True),('minimum_width',1146),('stage','wrong'),('recipe_revision','wrong')):
            bad=copy.deepcopy(m);bad['profiles']['classic']['wide_menu_recipe'][key]=value
            with self.subTest(key=key),self.assertRaises(presets.ManifestError):presets.validate_manifest(bad)
        legacy=copy.deepcopy(m);legacy['profiles']['classic'].pop('wide_menu_recipe')
        presets.validate_manifest(legacy)
        self.assertEqual(presets.resolve_plan(renderer='classic',resolution='1920x1080',manifest=legacy).stage,m['stable_stage'])

    def test_source_only_wide_selection_fails_closed_but_native_default_remains_available(self):
        self.assertTrue(classic.source_status()['passed'])
        with patch.object(sys,'frozen',True,create=True):
            self.assertEqual(classic.plan_candidate(resolution='800x600',**self.args).stage,core.patch_clash95_hd.DEFAULT_STAGE)
            with self.assertRaises(core.LauncherError):classic.plan_candidate(resolution='1920x1080',**self.args)
        with patch.object(builder,'build_candidate',side_effect=AssertionError('no build')):
            self.assertTrue(classic.source_status()['passed'])
        for resolution in ('799x600','1921x1080'):
            with self.assertRaises(core.LauncherError):classic.plan_candidate(resolution=resolution,**self.args)

    def test_cli_and_gui_select_corrected_classic_without_running_a_game(self):
        with patch.object(core,'launch_game',side_effect=AssertionError('no game')),redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(run.main(['--profile','classic','--resolution','1920x1080','--describe-plan']),0)
        value=json.loads(stream.getvalue());self.assertEqual(value['plan']['stage'],builder.STAGE)
        self.assertFalse(value['game_runtime_executed'])
        app=SimpleNamespace(profile_var=SimpleNamespace(get=lambda:'classic'))
        self.assertIs(gui.LauncherApp._backend(app),classic)


class ClassicMenuBundleTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='classic-menu-bundle-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve();self.game=self.root/'game';self.game.mkdir()
        self.original=b'synthetic original, not executable';self.image=b'synthetic PE extension';self.probe='synthetic probe\n'
        (self.game/core.BASE_EXE_NAME).write_bytes(self.original)
        (self.game/core.WRAPPER_DLL_NAME).write_bytes(b'synthetic wrapper')
        self.meta=dict(stage=builder.STAGE,recipe_revision=builder.REVISION,resolution='1920x1080',
            candidate_sha256=core.sha256_bytes(self.image),probe_sha256=core.sha256_bytes(self.probe.encode()),
            source_hashes={'fixture.py':'a'*64},patch_records=[{'synthetic':True}],edits=[{'synthetic':True}])
        self.adapter=SimpleNamespace(STAGE=builder.STAGE,REVISION=builder.REVISION,BASE_SHA256=core.sha256_bytes(self.original),
            RESOLUTIONS={'1920x1080'},build_candidate=Mock(side_effect=lambda *a:(self.image,self.meta.copy(),self.probe)),
            _write_bundle=complete._write_bundle)
        for guard in (patch.object(completehd,'_builder',return_value=self.adapter),patch.object(completehd,'CANDIDATE_ROOT',self.root/'candidates')):
            guard.start();self.addCleanup(guard.stop)
        self.plan=classic.plan_candidate(resolution='1920x1080',clash_dir=self.game,candidates_root=self.root/'candidates',
                                          expected_base_sha=self.adapter.BASE_SHA256)

    def deploy(self):
        result=classic.ensure_candidate(self.plan)
        classic.deploy_runtime_files(self.plan,result)
        return result

    def test_exact_shared_pipeline_reconstructs_and_deploys_without_launch(self):
        with patch.object(core,'launch_game',side_effect=AssertionError('no game')):
            result=self.deploy();classic.verify_launch(self.plan)
        self.assertEqual(result['profile'],'classic')
        self.assertFalse(result['minimap_viewport'])
        self.assertEqual(result['display_plan']['recipe_revision'],builder.REVISION)
        self.assertEqual(self.plan.candidate_exe.read_bytes(),self.image)
        self.assertTrue(classic.ensure_candidate(self.plan)['reused'])
        self.assertEqual(self.plan.base_exe.read_bytes(),self.original)
        manifest=core.read_candidate_manifest(self.plan)
        self.assertEqual(manifest['stage'],builder.STAGE)
        self.assertEqual(manifest['warning'],classic.WARNING)
        self.assertFalse(manifest['promotion_ready'])

    def test_old_plan_alias_or_rehashed_modified_artifacts_do_not_pass(self):
        self.deploy()
        for name in completehd._paths(self.plan)[:5]:
            before=name.read_bytes();name.write_bytes(before+b'changed')
            with self.subTest(name=name.name),self.assertRaises(core.LauncherError):classic.verify_launch(self.plan)
            name.write_bytes(before)
        bad=replace(self.plan,candidate_dir=self.plan.candidates_root/'1920x1080')
        with self.assertRaises(core.LauncherError):classic.ensure_candidate(bad)
        manifest=core.read_candidate_manifest(self.plan)
        self.plan.candidate_exe.write_bytes(b'rehashed modification')
        value=core.sha256_bytes(b'rehashed modification')
        manifest['output_sha256']=value;manifest['artifact_sha256'][self.plan.candidate_exe.name]=value
        self.plan.manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(core.LauncherError):classic.verify_launch(self.plan)

    def test_wrong_recipe_or_original_is_rejected_before_output(self):
        for key,value in (('stage',core.patch_clash95_hd.DEFAULT_STAGE),('recipe_revision','legacy'),('resolution','800x600')):
            old=self.meta[key];self.meta[key]=value
            with self.subTest(key=key),self.assertRaises(core.LauncherError):classic.ensure_candidate(self.plan)
            self.meta[key]=old
        self.plan.base_exe.write_bytes(b'unknown')
        with self.assertRaises(core.LauncherError):classic.ensure_candidate(self.plan)
        self.assertFalse(self.plan.candidate_dir.exists())

    def test_prepare_and_unconfirmed_cli_do_not_create_game_process(self):
        with patch.object(run,'build_plan',return_value=self.plan),patch.object(core,'launch_game',side_effect=AssertionError('no game')),redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(run.main(['--profile','classic','--prepare']),0)
            self.assertEqual(run.main(['--profile','classic','--launch']),2)
        with self.assertRaises(PermissionError):core.launch_game(self.plan,confirmed=False)

if __name__=='__main__':unittest.main(verbosity=2)
