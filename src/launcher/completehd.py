"""Source-only launcher adapter for the shared, unpromoted complete-HD builder."""
from __future__ import annotations

from dataclasses import replace
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
from typing import Any, Callable

import core

PROFILE = "completehd"
DIRECTORY = "completehd-validation"
STAGE = core.patch_clash95_hd.DEFAULT_STAGE + "-completehd-validation"
CANDIDATE_ROOT = Path("C:/ClashTests")
WARNING = (
    "Complete HD is experimental at every resolution. The candidate combines the adventure frame, "
    "minimap correction, native modal canvas and army panel, with centered native battles. "
    "Rendering, controls, screen transitions and endurance still require complete validation."
)


WIDGET_PROFILE = "modalwidgets"
WIDGET_DIRECTORY = "modalwidgets-validation"
WIDGET_STAGE = core.patch_clash95_hd.DEFAULT_STAGE + "-completehd-modalwidgets-validation"
WIDGET_WARNING = (
    "Modal widgets HD is experimental at every resolution. It adds native modal composition, "
    "centered barracks quantity text and context-dependent widget bounds above Complete HD. "
    "Startup does not prove map controls, barracks artwork, screen transitions or save/load."
)


CLASSIC_MENU_DIRECTORY = "classic-menu-validation"
CLASSIC_MENU_STAGE = core.patch_clash95_hd.DEFAULT_STAGE + "-menuwidgets-validation"
CLASSIC_MENU_WARNING = "Wide Classic uses experimental menu-only descriptor bounds. Map input and gameplay still require independent validation."


def _profile(profile: str) -> tuple[str, str, str]:
    if profile == "classic":
        return CLASSIC_MENU_DIRECTORY, CLASSIC_MENU_STAGE, CLASSIC_MENU_WARNING
    if profile == PROFILE:
        return DIRECTORY, STAGE, WARNING
    if profile == WIDGET_PROFILE:
        return WIDGET_DIRECTORY, WIDGET_STAGE, WIDGET_WARNING
    raise core.LauncherError("Unknown source-only HD profile.")


def _builder(profile: str = PROFILE):
    if getattr(sys, "frozen", False):
        raise core.LauncherError("Complete HD requires the source-tree launcher.")
    _profile(profile)
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
    if profile == WIDGET_PROFILE:
        module = importlib.import_module("tools.build_framed_modal_widgets_candidate")
        if module.STAGE != WIDGET_STAGE or module.REVISION != "owned_modal_widget_bounds_v1":
            raise core.LauncherError("Modal-widget builder identity differs.")
        return SimpleNamespace(__file__=module.__file__, STAGE=module.STAGE, REVISION=module.REVISION,
            BASE_SHA256=module.pe.ORIGINAL_SHA256, RESOLUTIONS=module.complete.RESOLUTIONS,
            build_candidate=module.build_candidate, _write_bundle=module.complete._write_bundle)
    return importlib.import_module("src.patcher.complete_hd_candidate")


def source_status(profile: str = PROFILE) -> dict[str, Any]:
    """Check the same inherited source pins without reading or running a game."""
    try:
        adapter = _builder(profile)
        pins = dict(adapter.PINNED) if profile == "classic" else {}
        for name in (() if profile == "classic" else ("build_partial_tile_candidate", "build_framed_candidate",
                     "build_framed_modal_candidate", "build_framed_army_candidate")):
            module = importlib.import_module(name)
            sources = dict(module.PINNED_SOURCES)
            if name == "build_framed_candidate":
                sources[module.MINIMAP_SOURCE] = module.MINIMAP_SOURCE_SHA256
            if name == "build_partial_tile_candidate":
                sources["src/patcher/initial_map_paint.py"] = module.INITIAL_SOURCE_SHA256
            for path, expected in sources.items():
                if path in pins and pins[path] != expected:
                    raise ValueError(f"Conflicting inherited source pin: {path}")
                pins[path] = expected
        if profile == WIDGET_PROFILE:
            text_pins = importlib.import_module("tools.modal_primary_text_context").FROZEN_TEXT_SOURCES
            for path, expected in text_pins.items():
                if path in pins and pins[path] != expected:
                    raise ValueError(f"Conflicting inherited text source pin: {path}")
                pins[path] = expected
        checks = {path: {"expected_sha256": expected, "actual_sha256": core.sha256_bytes((core.REPO_ROOT / path).read_bytes())}
                  for path, expected in pins.items()}
        for row in checks.values():
            row["passed"] = row["expected_sha256"] == row["actual_sha256"]
        return {"passed": all(row["passed"] for row in checks.values()), "checks": checks,
                "builder_sha256": core.sha256_bytes(Path(adapter.__file__).read_bytes()),
                "runtime_executed": False}
    except (OSError, ValueError, ImportError, core.LauncherError) as exc:
        return {"passed": False, "error": str(exc), "runtime_executed": False}


def plan_candidate(*, stage: str | None = None, profile: str = PROFILE, **kwargs: Any) -> core.CandidatePlan:
    directory_name, selected_stage, _ = _profile(profile)
    _builder(profile)
    if stage not in (None, selected_stage):
        raise core.LauncherError(f"The {profile} profile cannot use another --stage.")
    plan = core.plan_candidate(stage=selected_stage, renderer=profile, **kwargs)
    directory = plan.candidates_root / directory_name / plan.resolution
    plan = replace(plan, candidate_dir=directory, candidate_exe=directory / f"clash95_hd_{plan.resolution}.exe",
                   wrapper_target=directory / core.WRAPPER_DLL_NAME, dxcfg_target=directory / core.DXCFG_NAME,
                   manifest_path=directory / core.MANIFEST_NAME)
    _assert_plan(plan)
    return plan


def _paths(plan: core.CandidatePlan) -> tuple[Path, ...]:
    return (plan.candidate_exe, plan.candidate_exe.with_suffix(".candidate.json"),
            plan.candidate_exe.with_suffix(".cdb"), plan.wrapper_target, plan.dxcfg_target, plan.manifest_path)


def _assert_plan(plan: core.CandidatePlan) -> None:
    core.assert_plan_paths(plan)
    directory_name, selected_stage, _ = _profile(plan.renderer)
    adapter = _builder(plan.renderer)
    directory = plan.candidates_root / directory_name / plan.resolution
    expected = (directory / f"clash95_hd_{plan.resolution}.exe",
                directory / f"clash95_hd_{plan.resolution}.candidate.json", directory / f"clash95_hd_{plan.resolution}.cdb",
                directory / core.WRAPPER_DLL_NAME, directory / core.DXCFG_NAME, directory / core.MANIFEST_NAME)
    if (plan.stage != selected_stage or plan.stage != adapter.STAGE or plan.resolution not in adapter.RESOLUTIONS
            or plan.candidate_dir != directory or _paths(plan) != expected):
        raise core.LauncherError("Complete-HD plan does not identify its exact isolated profile.")
    for target in (plan.candidate_dir, *_paths(plan)):
        if (not core.is_under(target, CANDIDATE_ROOT) or not core.is_under(target, plan.candidates_root)
                or core.is_under(target, plan.clash_dir) or core.is_under(target, core.REPO_ROOT)):
            raise core.LauncherError(f"Unsafe complete-HD output path: {target}")
        if target.exists() and target.is_file() and target.stat().st_nlink != 1:
            raise core.LauncherError(f"Complete-HD outputs must not use hard links: {target}")
        if any(path.is_symlink() or getattr(path, "is_junction", lambda: False)()
               for path in (target, *target.parents)):
            raise core.LauncherError(f"Complete-HD outputs must not follow symbolic links: {target}")


def _original(plan: core.CandidatePlan) -> bytes:
    original = plan.base_exe.read_bytes()
    adapter = _builder(plan.renderer)
    if plan.expected_base_sha != adapter.BASE_SHA256 or core.sha256_bytes(original) != adapter.BASE_SHA256:
        raise core.LauncherError("Unknown base executable; complete-HD has no SHA override.")
    return original


def _json_bytes(value: dict[str, Any]) -> bytes:
    # Same serialization as complete_hd_candidate.write_candidate.
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def _expected(plan: core.CandidatePlan) -> tuple[dict[Path, bytes], dict[str, Any]]:
    _assert_plan(plan)
    original = _original(plan)
    image, metadata, probe = _builder(plan.renderer).build_candidate(original, plan.resolution)
    display = core.display_for_plan(plan)
    if (not isinstance(metadata, dict) or metadata.get("stage") != plan.stage
            or metadata.get("recipe_revision") != display.recipe_revision
            or metadata.get("resolution") != plan.resolution
            or metadata.get("candidate_sha256") != core.sha256_bytes(image)
            or metadata.get("probe_sha256") != core.sha256_bytes(probe.encode("utf-8"))):
        raise core.LauncherError("HD builder returned a different recipe or bundle identity.")
    paths = _paths(plan)
    artifacts = dict(zip(paths[:3], (image, _json_bytes(metadata), probe.encode("utf-8"))))
    record = {"base_sha256": core.sha256_bytes(original), "output_sha256": core.sha256_bytes(image),
              "display_plan": display.to_dict(), "build_id": display.build_identity(core.sha256_bytes(original), metadata["source_hashes"]),
              "patch_count": len(metadata["patch_records"] if "patch_records" in metadata else metadata["edits"]), "profile": plan.renderer, "minimap_viewport": display.minimap_viewport,
              "source_sha256": metadata["source_hashes"],
              "candidate_manifest": {"path": str(paths[1].resolve()), "sha256": core.sha256_bytes(artifacts[paths[1]])},
              "artifact_sha256": {path.name: core.sha256_bytes(data) for path, data in artifacts.items()},
              "game_runtime_executed": False, "manual_input_proof": False, "promotion_ready": False}
    return artifacts, record


def ensure_candidate(plan: core.CandidatePlan, progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    try:
        artifacts, record = _expected(plan)
        missing = {}
        for path, content in artifacts.items():
            if path.exists():
                if not path.is_file() or path.read_bytes() != content:
                    raise core.LauncherError(f"Refusing to replace a different complete-HD artifact: {path}. Choose a new candidates root.")
            else:
                missing[path] = content
        plan.candidate_dir.mkdir(parents=True, exist_ok=True)
        _builder(plan.renderer)._write_bundle(tuple(missing), tuple(missing.values()))
        if any(path.read_bytes() != content for path, content in artifacts.items()):
            raise core.LauncherError("Complete-HD artifact changed during preparation.")
        if progress:
            progress(_profile(plan.renderer)[2])
            progress(f"{'Prepared' if missing else 'Reused'} complete-HD candidate: {plan.candidate_exe}")
        return {"reused": not missing, **record}
    except (OSError, ValueError, ImportError) as exc:
        raise core.LauncherError(f"Complete-HD preparation failed: {exc}") from exc


def _verify_artifacts(plan: core.CandidatePlan, record: dict[str, Any], *, deployed: bool) -> None:
    artifacts, expected = _expected(plan)
    paths = _paths(plan)
    for key, value in expected.items():
        if key != "artifact_sha256" and record.get(key) != value:
            raise core.LauncherError(f"Complete-HD candidate provenance differs: {key}")
    if deployed:
        artifacts.update({path: path.read_bytes() for path in paths[3:5]})
    hashes = {path.name: core.sha256_bytes(data) for path, data in artifacts.items()}
    if record.get("artifact_sha256") != hashes or any(path.read_bytes() != data for path, data in artifacts.items()):
        raise core.LauncherError("Complete-HD artifacts differ from the deterministic candidate or deployed identities.")
    if deployed and record.get("deployment_id") != core.deployment_identity(
            expected["build_id"], hashes[core.WRAPPER_DLL_NAME], hashes[core.DXCFG_NAME]):
        raise core.LauncherError("Complete-HD wrapper/configuration identity differs.")


def deploy_runtime_files(plan: core.CandidatePlan, candidate_result: dict[str, Any] | None = None,
                         progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    try:
        if not isinstance(candidate_result, dict):
            raise core.LauncherError("Prepare the complete-HD candidate before deployment.")
        _verify_artifacts(plan, candidate_result, deployed=False)
        if not plan.wrapper_source.is_file():
            return {"wrapper": "missing", "wrapper_dll_sha256": None, "manifest": "not_written"}
        result = core.deploy_runtime_files(plan, candidate_result, progress=progress)
        manifest = core.read_candidate_manifest(plan)
        manifest.update({key: value for key, value in candidate_result.items() if key != "reused"})
        manifest["artifact_sha256"] = {**candidate_result["artifact_sha256"],
                                       **{path.name: core.sha256_bytes(path.read_bytes()) for path in _paths(plan)[3:5]}}
        manifest["warning"] = _profile(plan.renderer)[2]
        plan.manifest_path.write_bytes(_json_bytes(manifest))
        return result
    except (OSError, ValueError) as exc:
        raise core.LauncherError(f"Complete-HD deployment failed: {exc}") from exc


def verify_launch(plan: core.CandidatePlan) -> None:
    try:
        _assert_plan(plan)
        manifest = core.read_candidate_manifest(plan)
        if (not isinstance(manifest, dict) or manifest.get("schema") != core.MANIFEST_SCHEMA
                or manifest.get("stage") != plan.stage or manifest.get("resolution") != plan.resolution
                or manifest.get("scaling_mode") != plan.scaling_mode):
            raise core.LauncherError("Complete-HD launch requires a matching deployed manifest.")
        _verify_artifacts(plan, manifest, deployed=True)
    except (OSError, ValueError) as exc:
        raise core.LauncherError(f"Complete-HD launch verification failed: {exc}") from exc
