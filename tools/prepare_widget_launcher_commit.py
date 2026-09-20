from pathlib import Path
import copy, json
import hashlib, os, subprocess, sys, unittest, zipfile
root=Path.cwd()
identities=json.loads((root/'tools/widget_launcher_integration.json').read_text())
for name,row in identities.items():
    path=root/name
    if row['before_blob_sha']:
        raw=path.read_bytes()
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=row['before_blob_sha']:
            raise SystemExit('Unreviewed launcher input: '+name)
    elif name!='tools/test_launcher_modalwidgets.py' and path.exists():
        raise SystemExit('New launcher path is occupied: '+name)

p=root/'src/launcher/completehd.py'
s=p.read_text()
s=s.replace('from pathlib import Path\n','from pathlib import Path\nfrom types import SimpleNamespace\n')
s=s.replace('\n\ndef _builder():', '''

WIDGET_PROFILE = "modalwidgets"
WIDGET_DIRECTORY = "modalwidgets-validation"
WIDGET_STAGE = core.patch_clash95_hd.DEFAULT_STAGE + "-completehd-modalwidgets-validation"
WIDGET_WARNING = (
    "Modal widgets HD is experimental at every resolution. It adds native modal composition, "
    "centered barracks quantity text and context-dependent widget bounds above Complete HD. "
    "Startup does not prove map controls, barracks artwork, screen transitions or save/load."
)


def _profile(profile: str) -> tuple[str, str, str]:
    if profile == PROFILE:
        return DIRECTORY, STAGE, WARNING
    if profile == WIDGET_PROFILE:
        return WIDGET_DIRECTORY, WIDGET_STAGE, WIDGET_WARNING
    raise core.LauncherError("Unknown source-only HD profile.")


def _builder(profile: str = PROFILE):''')
s=s.replace('    return importlib.import_module("src.patcher.complete_hd_candidate")','''    _profile(profile)
    if profile == WIDGET_PROFILE:
        module = importlib.import_module("tools.build_framed_modal_widgets_candidate")
        if module.STAGE != WIDGET_STAGE or module.REVISION != "owned_modal_widget_bounds_v1":
            raise core.LauncherError("Modal-widget builder identity differs.")
        return SimpleNamespace(__file__=module.__file__, STAGE=module.STAGE, REVISION=module.REVISION,
            BASE_SHA256=module.pe.ORIGINAL_SHA256, RESOLUTIONS=module.complete.RESOLUTIONS,
            build_candidate=module.build_candidate, _write_bundle=module.complete._write_bundle)
    return importlib.import_module("src.patcher.complete_hd_candidate")''')
s=s.replace('def source_status() -> dict[str, Any]:','def source_status(profile: str = PROFILE) -> dict[str, Any]:')
s=s.replace('        adapter = _builder()','        adapter = _builder(profile)')
s=s.replace('        checks = {path:', '''        if profile == WIDGET_PROFILE:
            text_pins = importlib.import_module("tools.modal_primary_text_context").FROZEN_TEXT_SOURCES
            for path, expected in text_pins.items():
                if path in pins and pins[path] != expected:
                    raise ValueError(f"Conflicting inherited text source pin: {path}")
                pins[path] = expected
        checks = {path:''')
s=s.replace('def plan_candidate(*, stage: str | None = None, **kwargs: Any)', 'def plan_candidate(*, stage: str | None = None, profile: str = PROFILE, **kwargs: Any)')
s=s.replace('''    _builder()
    if stage not in (None, STAGE):
        raise core.LauncherError("The completehd profile cannot use another --stage.")
    plan = core.plan_candidate(stage=STAGE, renderer=PROFILE, **kwargs)
    directory = plan.candidates_root / DIRECTORY / plan.resolution''','''    directory_name, selected_stage, _ = _profile(profile)
    _builder(profile)
    if stage not in (None, selected_stage):
        raise core.LauncherError(f"The {profile} profile cannot use another --stage.")
    plan = core.plan_candidate(stage=selected_stage, renderer=profile, **kwargs)
    directory = plan.candidates_root / directory_name / plan.resolution''')
s=s.replace('''    adapter = _builder()
    directory = plan.candidates_root / DIRECTORY / plan.resolution''','''    directory_name, selected_stage, _ = _profile(plan.renderer)
    adapter = _builder(plan.renderer)
    directory = plan.candidates_root / directory_name / plan.resolution''')
s=s.replace('''if (plan.renderer != PROFILE or plan.stage != adapter.STAGE or plan.resolution not in adapter.RESOLUTIONS''', '''if (plan.stage != selected_stage or plan.stage != adapter.STAGE or plan.resolution not in adapter.RESOLUTIONS''')
s=s.replace('''    if plan.expected_base_sha != _builder().BASE_SHA256 or core.sha256_bytes(original) != _builder().BASE_SHA256:''','''    adapter = _builder(plan.renderer)
    if plan.expected_base_sha != adapter.BASE_SHA256 or core.sha256_bytes(original) != adapter.BASE_SHA256:''')
s=s.replace('_builder().build_candidate(original, plan.resolution)','_builder(plan.renderer).build_candidate(original, plan.resolution)')
s=s.replace('"patch_count": len(metadata["patch_records"]), "profile": PROFILE,','"patch_count": len(metadata["patch_records"] if "patch_records" in metadata else metadata["edits"]), "profile": plan.renderer,')
s=s.replace('_builder()._write_bundle(tuple(missing), tuple(missing.values()))','_builder(plan.renderer)._write_bundle(tuple(missing), tuple(missing.values()))')
s=s.replace('progress(WARNING)','progress(_profile(plan.renderer)[2])')
s=s.replace('manifest["warning"] = WARNING','manifest["warning"] = _profile(plan.renderer)[2]')
s=s.replace('manifest.get("stage") != STAGE','manifest.get("stage") != plan.stage')
p.write_text(s)
p=root/'src/launcher/modalwidgets.py'
p.write_text('''"""Explicit experimental launcher profile using the shared isolated HD pipeline."""
from functools import partial

import completehd

PROFILE = completehd.WIDGET_PROFILE
DIRECTORY = completehd.WIDGET_DIRECTORY
STAGE = completehd.WIDGET_STAGE
WARNING = completehd.WIDGET_WARNING
source_status = partial(completehd.source_status, profile=PROFILE)
plan_candidate = partial(completehd.plan_candidate, profile=PROFILE)
ensure_candidate = completehd.ensure_candidate
deploy_runtime_files = completehd.deploy_runtime_files
verify_launch = completehd.verify_launch
''')
p=root/'src/display_plan.py';s=p.read_text()
s=s.replace('"completehd": "complete_hd_v1"}', '"completehd": "complete_hd_v1", "modalwidgets": "owned_modal_widget_bounds_v1"}')
s=s.replace('Renderer must be classic, framed or completehd.','Renderer must be classic, framed, completehd or modalwidgets.')
s=s.replace('renderer != "completehd" or minimap','renderer not in ("completehd", "modalwidgets") or minimap')
s=s.replace('if renderer in ("framed", "completehd"):', 'if renderer in ("framed", "completehd", "modalwidgets"):')
s=s.replace('if renderer == "completehd":\n                complete = importlib.import_module("src.patcher.complete_hd_candidate")','''if renderer in ("completehd", "modalwidgets"):
                complete = importlib.import_module("src.patcher.complete_hd_candidate" if renderer == "completehd"
                                                  else "tools.build_framed_modal_widgets_candidate")''')
s=s.replace('resolution in complete.RESOLUTIONS','resolution in (complete.RESOLUTIONS if renderer == "completehd" else complete.complete.RESOLUTIONS)')
p.write_text(s)
p=root/'src/launcher/presets.py';s=p.read_text()
s=s.replace('if renderer == "completehd":','if renderer in ("completehd", "modalwidgets"):')
s=s.replace('permits the completehd profile.', 'permits the source-only HD profiles.')
s=s.replace('''config["stage"] != manifest["stable_stage"] + "-completehd-validation"''','''config["stage"] != manifest["stable_stage"] + ("-completehd-validation" if renderer == "completehd" else "-completehd-modalwidgets-validation")''')
s=s.replace('if renderer == "completehd" and entry["status"] != "experimental":', 'if renderer in ("completehd", "modalwidgets") and entry["status"] != "experimental":')
p.write_text(s)
p=root/'src/launcher/resolutions.json';s=p.read_text();d=json.loads(s)
v=copy.deepcopy(d['profiles']['completehd']);v['stage']=d['stable_stage']+'-completehd-modalwidgets-validation';v['recipe_revision']='owned_modal_widget_bounds_v1';d['profiles']['modalwidgets']=v
p.write_text(json.dumps(d,indent=2)+'\n')
p=root/'src/launcher/run.py';s=p.read_text().replace('import completehd\n','import completehd\nimport modalwidgets\n')
s=s.replace('choices=("classic", "framed", "completehd")','choices=("classic", "framed", "completehd", "modalwidgets")')
s=s.replace('"completehd": completehd}', '"completehd": completehd, "modalwidgets": modalwidgets}')
s=s.replace('args.profile == "completehd"','args.profile in ("completehd", "modalwidgets")')
p.write_text(s)
p=root/'src/launcher/gui.py';s=p.read_text().replace('import completehd\n','import completehd\nimport modalwidgets\n')
s=s.replace('"completehd": "Complete HD (experimental)"}', '"completehd": "Complete HD (experimental)",\n                 "modalwidgets": "Modal widgets HD (experimental)"}')
s=s.replace('"completehd": completehd}', '"completehd": completehd, "modalwidgets": modalwidgets}')
s=s.replace('self.profile_var.get() == "completehd"','self.profile_var.get() in ("completehd", "modalwidgets")')
s=s.replace('''            self.component_list.delete(0, "end")''','''            if self.profile_var.get() == "modalwidgets":
                components = ("Complete HD adventure frame and minimap", "Native modal composition and army panel",
                              "Centered barracks quantity text", "Context-dependent native modal widget bounds")
            self.component_list.delete(0, "end")''')
p.write_text(s)

p=root/'src/launcher/completehd.py';s=p.read_text()
old = '    display = core.display_for_plan(plan)\n    paths = _paths(plan)'
new = '    display = core.display_for_plan(plan)\n    if (not isinstance(metadata, dict) or metadata.get("stage") != plan.stage\n            or metadata.get("recipe_revision") != display.recipe_revision\n            or metadata.get("resolution") != plan.resolution\n            or metadata.get("candidate_sha256") != core.sha256_bytes(image)\n            or metadata.get("probe_sha256") != core.sha256_bytes(probe.encode("utf-8"))):\n        raise core.LauncherError("HD builder returned a different recipe or bundle identity.")\n    paths = _paths(plan)'
if s.count(old)!=1:raise SystemExit('Expected launcher identity insertion site differs')
p.write_text(s.replace(old,new))
p=root/'tools/test_launcher_modalwidgets.py'
p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
for name,row in identities.items():
    if hashlib.sha256((root/name).read_bytes()).hexdigest()!=row['after_sha256']:
        raise SystemExit('Review output differs: '+name)
output=Path(os.environ['RUNNER_TEMP'])/'widget-launcher-review';output.mkdir()
sys.path[:0]=[str(root),str(root/'tools')]
from run_framed_offline_tests import source_preflight
preflight=source_preflight(root)
if not preflight['passed']:raise SystemExit('Patcher source preflight failed')
suite=unittest.defaultTestLoader.discover('tools',pattern='test_launcher*.py')
with (output/'launcher-tests.log').open('w') as stream:
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
report=dict(schema=1,source_preflight=preflight,tests_run=result.testsRun,
    failures=[(str(t),v) for t,v in result.failures],errors=[(str(t),v) for t,v in result.errors],skipped=result.skipped,
    source_hashes={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in identities},
    game_runtime_executed=False,manual_input_proof=False,promotion_ready=False)
(output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
with zipfile.ZipFile(output/'changed-source.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name in identities:archive.write(root/name,name)
if not result.wasSuccessful() or result.testsRun!=96 or result.skipped:
    raise SystemExit('Isolated launcher tests failed or skipped')
subprocess.run(['git','diff','--check'],check=True)
subprocess.run(['git','add','--',*identities],check=True)
subprocess.run(['git','config','user.name','github-actions[bot]'],check=True)
subprocess.run(['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],check=True)
subprocess.run(['git','commit','-m','Expose the exact experimental modal-widget recipe through the shared launcher'],check=True)
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
(output/'commit.txt').write_text(head+'\n')
subprocess.run(['git','push','origin','HEAD:codex/widget-launcher'],check=True)
