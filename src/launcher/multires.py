"""Isolated launcher adapter for the twelve versioned HD candidates."""
from __future__ import annotations

from dataclasses import replace
import importlib
from pathlib import Path
from types import SimpleNamespace
import sys

import core
from src.display_plan import (HD_MULTIRES_REVISION, HD_MULTIRES_RESOLUTIONS,
    RECIPE_REVISION, is_multires_selection, multires_stage)

WARNING = ("HD multiresolution candidates are experimental. Source preparation does not "
           "establish rendering, controls, save/load, endurance or release acceptance.")


def selected(profile, resolution, stage=None, manifest=None):
    if not is_multires_selection(profile, resolution, stage):
        return False
    manifest = manifest if manifest is not None else core.presets.load_manifest()
    return bool(manifest.get("profiles", {}).get(profile, {}).get("multires_recipe"))


def is_plan(plan):
    return (plan.renderer in RECIPE_REVISION and plan.resolution in HD_MULTIRES_RESOLUTIONS
            and plan.stage == multires_stage(plan.renderer))


def profile_layout(profile):
    if profile not in RECIPE_REVISION:
        raise core.LauncherError("Unknown HD multiresolution profile.")
    return str(Path("multires") / HD_MULTIRES_REVISION / profile), multires_stage(profile), WARNING


def _builder(profile):
    if profile not in RECIPE_REVISION:
        raise core.LauncherError("Unknown HD multiresolution profile.")
    if getattr(sys, "frozen", False):
        verify = getattr(core.bootstrap, "require_bundled_sources", None)
        if not callable(verify):
            raise core.LauncherError("Verified bundled HD sources are unavailable.")
        try:
            verify()
        except (OSError, ValueError) as error:
            raise core.LauncherError(str(error)) from error
    component = importlib.import_module("src.patcher.hd_multires_candidate")
    if (tuple(component.PROFILES) != tuple(RECIPE_REVISION) or
            tuple(component.RESOLUTIONS) != HD_MULTIRES_RESOLUTIONS or
            component.REVISION != HD_MULTIRES_REVISION or
            component.stage(profile) != multires_stage(profile)):
        raise core.LauncherError("HD multiresolution builder identity differs.")
    # Reuse the independently authored atomic bundle writer, not a game tool.
    writer = importlib.import_module("src.patcher.complete_hd_candidate")._write_bundle
    return SimpleNamespace(__file__=component.__file__, STAGE=component.stage(profile),
        REVISION=component.REVISION, RESOLUTIONS=component.RESOLUTIONS,
        BASE_SHA256=component.ORIGINAL_SHA256,
        build_candidate=lambda original, resolution: component.build_candidate(original, resolution, profile=profile),
        source_hashes=lambda: component.source_hashes(profile), _write_bundle=writer)


def source_status(profile):
    try:
        adapter = _builder(profile)
        pins = adapter.source_hashes()
        if not isinstance(pins, dict) or not pins:
            raise ValueError("HD multiresolution source inventory is empty.")
        checks = {}
        for name, expected in pins.items():
            relative = Path(name)
            if (relative.is_absolute() or "\\" in name or ":" in name or
                    any(part in ("", ".", "..") for part in name.split("/"))):
                raise ValueError("HD source path must be canonical and relative.")
            path = core.REPO_ROOT / relative
            if path.resolve(strict=True) != path or any(
                    item.is_symlink() or getattr(item, "is_junction", lambda: False)()
                    for item in (path, *path.parents)):
                raise ValueError("HD source path must not use links.")
            actual = core.sha256_bytes(path.read_bytes())
            checks[name] = {"expected_sha256": expected, "actual_sha256": actual,
                            "passed": expected == actual}
        return {"passed": all(row["passed"] for row in checks.values()), "checks": checks,
                "builder_sha256": core.sha256_bytes(Path(adapter.__file__).read_bytes()),
                "runtime_executed": False}
    except (OSError, ValueError, ImportError, core.LauncherError) as error:
        return {"passed": False, "error": str(error), "runtime_executed": False}


def plan_candidate(*, profile, stage=None, **kwargs):
    resolution = kwargs.get("resolution", "800x600")
    if not selected(profile, resolution, stage, kwargs.get("manifest")):
        raise core.LauncherError("Select one of the three registered HD successor resolutions.")
    _builder(profile)
    plan = core.plan_candidate(renderer=profile, stage=multires_stage(profile), **kwargs)
    directory_name, _, _ = profile_layout(profile)
    directory = plan.candidates_root / directory_name / plan.resolution
    plan = replace(plan, candidate_dir=directory,
        candidate_exe=directory / f"clash95_hd_{plan.resolution}.exe",
        wrapper_target=directory / core.WRAPPER_DLL_NAME,
        dxcfg_target=directory / core.DXCFG_NAME,
        manifest_path=directory / core.MANIFEST_NAME)
    import completehd
    completehd._assert_plan(plan)
    return plan


def ensure_candidate(plan, progress=None):
    import completehd
    return completehd.ensure_candidate(plan, progress=progress)


def deploy_runtime_files(plan, candidate_result=None, progress=None):
    import completehd
    return completehd.deploy_runtime_files(plan, candidate_result, progress=progress)


def verify_launch(plan):
    import completehd
    return completehd.verify_launch(plan)
