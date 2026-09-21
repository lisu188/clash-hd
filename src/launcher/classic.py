"""Preserve native Classic defaults and route wide menus through their verified extension."""
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
    try:
        display = presets.resolve_plan(renderer="classic", resolution=kwargs.get("resolution", "800x600"),
                                       stage=stage, scaling_mode=kwargs.get("scaling_mode", "integer"), manifest=manifest)
    except ValueError as error:
        raise core.LauncherError(str(error)) from error
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
