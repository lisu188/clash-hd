from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest,zipfile
root=Path.cwd()
identities=json.loads((root/'tools/classic_launcher_checkpoint.json').read_text())
for name,row in identities.items():
    path=root/name
    if row['before_blob_sha']:
        raw=path.read_bytes()
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=row['before_blob_sha']:
            raise SystemExit('Unreviewed source before integration: '+name)
    elif name!='tools/test_launcher_classic_menu.py' and path.exists():
        raise SystemExit('New source path already exists: '+name)
p=root/'src/display_plan.py';s=p.read_text()
s=s.replace('        selected_stage = patcher.DEFAULT_STAGE if stage is None else stage','        selected_stage = patcher.DEFAULT_STAGE if stage is None else stage\n        selected_revision = RECIPE_REVISION[renderer]\n        scalar_stage = selected_stage')
needle='''        else:
            _require(type(selected_stage) is str and selected_stage in patcher.STAGE_GROUPS,'''
replace='''        else:
            menu_stage = patcher.DEFAULT_STAGE + "-menuwidgets-validation"
            if selected_stage == menu_stage:
                menu = importlib.import_module("src.patcher.classic_menu_candidate")
                _require(menu.STAGE == menu_stage and menu.REVISION == "classic_menu_widgets_v1"
                         and menu.supports(resolution), "unsupported_recipe", "Classic menu correction requires an affected supported resolution.")
                scalar_stage = patcher.DEFAULT_STAGE
                selected_revision = menu.REVISION
            _require(type(scalar_stage) is str and scalar_stage in patcher.STAGE_GROUPS,'''
assert s.count(needle)==1;s=s.replace(needle,replace)
s=s.replace('patcher.select_patches_for(selected_stage, profile)','patcher.select_patches_for(scalar_stage, profile)')
s=s.replace('patcher.STAGE_GROUPS[selected_stage]', 'patcher.STAGE_GROUPS[scalar_stage]')
s=s.replace('selected_stage, RECIPE_REVISION[renderer], width, height','selected_stage, selected_revision, width, height')
p.write_text(s)
p=root/'src/launcher/completehd.py';s=p.read_text()
s=s.replace('def _profile(profile: str)', '''CLASSIC_MENU_DIRECTORY = "classic-menu-validation"
CLASSIC_MENU_STAGE = core.patch_clash95_hd.DEFAULT_STAGE + "-menuwidgets-validation"
CLASSIC_MENU_WARNING = "Wide Classic uses experimental menu-only descriptor bounds. Map input and gameplay still require independent validation."


def _profile(profile: str)''')
s=s.replace('    if profile == PROFILE:\n','    if profile == "classic":\n        return CLASSIC_MENU_DIRECTORY, CLASSIC_MENU_STAGE, CLASSIC_MENU_WARNING\n    if profile == PROFILE:\n',1)
needle='''    _profile(profile)
    if profile == WIDGET_PROFILE:'''
replace='''    _profile(profile)
    if profile == "classic":
        module = importlib.import_module("src.patcher.classic_menu_candidate")
        if module.STAGE != CLASSIC_MENU_STAGE or module.REVISION != "classic_menu_widgets_v1":
            raise core.LauncherError("Classic menu builder identity differs.")
        class Supported:
            def __contains__(self, value):
                return module.supports(value)
        complete = importlib.import_module("src.patcher.complete_hd_candidate")
        return SimpleNamespace(__file__=module.__file__, STAGE=module.STAGE, REVISION=module.REVISION,
            BASE_SHA256=module.BASE_SHA256, RESOLUTIONS=Supported(), PINNED=module.PINNED,
            build_candidate=module.build_candidate, _write_bundle=complete._write_bundle)
    if profile == WIDGET_PROFILE:'''
assert s.count(needle)==1;s=s.replace(needle,replace)
s=s.replace('''        pins = {}
        for name in ("build_partial_tile_candidate", "build_framed_candidate",
                     "build_framed_modal_candidate", "build_framed_army_candidate"):''','''        pins = dict(adapter.PINNED) if profile == "classic" else {}
        for name in (() if profile == "classic" else ("build_partial_tile_candidate", "build_framed_candidate",
                     "build_framed_modal_candidate", "build_framed_army_candidate")):''')
s=s.replace('"profile": plan.renderer, "minimap_viewport": True,','"profile": plan.renderer, "minimap_viewport": display.minimap_viewport,')
p.write_text(s)
p=root/'src/launcher/classic.py';p.write_text('''"""Preserve native Classic defaults and route wide menus through their verified extension."""
from dataclasses import replace

import core
import completehd
import presets

WARNING = completehd.CLASSIC_MENU_WARNING
STAGE = completehd.CLASSIC_MENU_STAGE


def source_status():
    return completehd.source_status("classic")


def plan_candidate(*, stage=None, **kwargs):
    manifest = kwargs.get("manifest") or presets.load_manifest()
    display = presets.resolve_plan(renderer="classic", resolution=kwargs.get("resolution", "800x600"),
                                   stage=stage, scaling_mode=kwargs.get("scaling_mode", "integer"), manifest=manifest)
    if display.stage != STAGE:
        return core.plan_candidate(stage=stage, **kwargs)
    completehd._builder("classic")
    base = core.plan_candidate(stage=core.patch_clash95_hd.DEFAULT_STAGE, **kwargs)
    directory = base.candidates_root / completehd.CLASSIC_MENU_DIRECTORY / base.resolution
    plan = replace(base, stage=STAGE, candidate_dir=directory,
                   candidate_exe=directory / f"clash95_hd_{base.resolution}.exe",
                   wrapper_target=directory / core.WRAPPER_DLL_NAME, dxcfg_target=directory / core.DXCFG_NAME,
                   manifest_path=directory / core.MANIFEST_NAME)
    completehd._assert_plan(plan)
    return plan


def _backend(plan):
    return completehd if plan.stage == STAGE else core


def ensure_candidate(plan, progress=None):
    return _backend(plan).ensure_candidate(plan, progress=progress)


def deploy_runtime_files(plan, candidate_result=None, progress=None):
    return _backend(plan).deploy_runtime_files(plan, candidate_result, progress=progress)


def verify_launch(plan):
    if plan.stage == STAGE:
        completehd.verify_launch(plan)
''')
p=root/'src/launcher/presets.py';s=p.read_text()
needle='''        entries = config.get("resolutions")'''
replace='''        wide = config.get("wide_menu_recipe")
        if wide is not None:
            if renderer != "classic" or wide != {"minimum_width": 1144,
                    "stage": manifest["stable_stage"] + "-menuwidgets-validation",
                    "recipe_revision": "classic_menu_widgets_v1"} or type(wide.get("minimum_width")) is not int:
                raise ManifestError("Unrecognized Classic wide-menu recipe.")
        entries = config.get("resolutions")'''
assert s.count(needle)==1;s=s.replace(needle,replace)
needle='''    return resolve_display_plan(renderer=renderer, resolution=resolution, stage=stage if stage is not None else config["stage"],'''
replace='''    selected_stage = stage if stage is not None else config["stage"]
    if stage is None and renderer == "classic" and config.get("wide_menu_recipe"):
        if parse_dimensions(resolution, _bounds(manifest))[0] >= config["wide_menu_recipe"]["minimum_width"]:
            selected_stage = config["wide_menu_recipe"]["stage"]
    return resolve_display_plan(renderer=renderer, resolution=resolution, stage=selected_stage,'''
assert s.count(needle)==1;s=s.replace(needle,replace);p.write_text(s)
p=root/'src/launcher/resolutions.json';m=json.loads(p.read_text());m['profiles']['classic']['wide_menu_recipe']={'minimum_width':1144,'stage':m['stable_stage']+'-menuwidgets-validation','recipe_revision':'classic_menu_widgets_v1'};p.write_text(json.dumps(m,indent=2)+'\n')
for name in ('run','gui'):
 p=root/f'src/launcher/{name}.py';s=p.read_text();s=s.replace('import framed\n','import framed\nimport classic\n');s=s.replace('{"classic": core,','{"classic": classic,');p.write_text(s)
p=root/'src/launcher/classic.py';s=p.read_text()
old='    display = presets.resolve_plan(renderer="classic", resolution=kwargs.get("resolution", "800x600"),\n                                   stage=stage, scaling_mode=kwargs.get("scaling_mode", "integer"), manifest=manifest)\n'
new='    try:\n        display = presets.resolve_plan(renderer="classic", resolution=kwargs.get("resolution", "800x600"),\n                                       stage=stage, scaling_mode=kwargs.get("scaling_mode", "integer"), manifest=manifest)\n    except ValueError as error:\n        raise core.LauncherError(str(error)) from error\n'
if s.count(old)!=1:raise SystemExit('Unexpected Classic facade selection site')
p.write_text(s.replace(old,new))
p=root/'tools/test_launcher_framed.py';s=p.read_text().replace('import framed\n','import framed\nimport classic\n').replace('self.assertIs(app._backend(), core)','self.assertIs(app._backend(), classic)')
p.write_bytes(s.replace('\n','\r\n').encode())
for name,row in identities.items():
    if hashlib.sha256((root/name).read_bytes()).hexdigest()!=row['after_sha256']:
        raise SystemExit('Unreviewed integration result: '+name)
output=Path(os.environ['RUNNER_TEMP'])/'classic-launcher-review';output.mkdir()
sys.path[:0]=[str(root),str(root/'tools')]
from run_framed_offline_tests import source_preflight
preflight=source_preflight(root)
with (output/'tests.log').open('w') as log:
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover('tools',pattern='test_launcher*.py'))
report=dict(source_preflight=preflight,tests_run=result.testsRun,skipped=result.skipped,
    errors=[(str(t),v) for t,v in result.errors],failures=[(str(t),v) for t,v in result.failures],
    source_hashes={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in identities},
    game_runtime_executed=False,promotion_ready=False)
(output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
with zipfile.ZipFile(output/'changed-source.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name in identities:archive.write(root/name,name)
if not preflight['passed'] or not result.wasSuccessful() or result.skipped or result.testsRun!=105:
    raise SystemExit('Launcher suite or frozen source check failed')
subprocess.run(['git','diff','--check'],check=True)
subprocess.run(['git','config','user.name','github-actions[bot]'],check=True)
subprocess.run(['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],check=True)
subprocess.run(['git','add','--',*identities],check=True)
subprocess.run(['git','commit','-m','Select verified menu-only guards for wide Classic launcher presets'],check=True)
(output/'commit.txt').write_text(subprocess.check_output(['git','rev-parse','HEAD'],text=True))
subprocess.run(['git','push','origin','HEAD:codex/classic-menu-launcher'],check=True)
