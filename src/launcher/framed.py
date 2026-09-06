from __future__ import annotations

from dataclasses import replace
import importlib
import json
from pathlib import Path
import sys
from typing import Any, Callable

import core

PROFILE = "framed"
DIRECTORY = "framed-minimap"
STAGE = core.patch_clash95_hd.DEFAULT_STAGE + "-combinedui-partialtiles-initialpaint-framed-validation"
BUILDER_SHA256 = "4178745fabb1e2270efcbdc72bf4999f97b0bca23bdad78db743a5db1b724d7a"
BUILD_REPORT = "framed-build.json"
PROBE = "framed-probe.cdb"
WARNING = (
    "Framed rendering with minimap correction is experimental at every resolution. "
    "Ordinary maps and AI banners are supported by the candidate recipe; other "
    "screens retain native fallback. Runtime, manual input, and stable promotion "
    "are not established by building this profile."
)


def source_status() -> dict[str, Any]:
    if getattr(sys, "frozen", False):
        return {"passed": False, "error": "The framed profile requires the source-tree launcher; use Classic in a packaged launcher."}
    from run_framed_offline_tests import source_preflight
    result = source_preflight(core.REPO_ROOT)
    if result.get("builder_sha256") != BUILDER_SHA256:
        result = dict(result, passed=False, error="The reviewed framed builder source has changed.")
    return result


def _bindings() -> dict[str, str]:
    status = source_status()
    if status.get("passed") is not True:
        failed = ", ".join(name for name, row in status.get("checks", {}).items() if not row.get("passed"))
        raise core.LauncherError(status.get("error") or f"Framed source verification failed: {failed}")
    return {"tools/build_framed_candidate.py": status["builder_sha256"],
            **{name: row["actual_sha256"] for name, row in status["checks"].items()}}


def plan_candidate(*, stage: str | None = None, **kwargs: Any) -> core.CandidatePlan:
    if stage not in (None, STAGE):
        raise core.LauncherError("The framed profile cannot be combined with another --stage.")
    if getattr(sys, "frozen", False):
        raise core.LauncherError("The framed profile requires the source-tree launcher.")
    plan = core.plan_candidate(stage=core.patch_clash95_hd.DEFAULT_STAGE, **kwargs)
    profile = core.patch_clash95_hd.parse_resolution(plan.resolution)
    if profile.key != plan.resolution:
        raise core.LauncherError("Framed resolution must use canonical WxH spelling.")
    directory = plan.candidates_root / DIRECTORY / plan.resolution
    plan = replace(plan, stage=STAGE, candidate_dir=directory,
                   candidate_exe=directory / f"clash95_hd_{plan.resolution}.exe",
                   wrapper_target=directory / core.WRAPPER_DLL_NAME,
                   dxcfg_target=directory / core.DXCFG_NAME,
                   manifest_path=directory / core.MANIFEST_NAME)
    _assert_plan(plan)
    return plan


def _paths(plan: core.CandidatePlan) -> tuple[Path, ...]:
    return (plan.candidate_exe, plan.candidate_dir / BUILD_REPORT,
            plan.candidate_dir / PROBE, plan.wrapper_target, plan.dxcfg_target,
            plan.manifest_path)


def _assert_plan(plan: core.CandidatePlan) -> None:
    core.assert_plan_paths(plan)
    if core.patch_clash95_hd.parse_resolution(plan.resolution).key != plan.resolution:
        raise core.LauncherError("Framed resolution must use canonical WxH spelling.")
    expected_dir = plan.candidates_root / DIRECTORY / plan.resolution
    expected = (expected_dir / f"clash95_hd_{plan.resolution}.exe",
                expected_dir / BUILD_REPORT, expected_dir / PROBE,
                expected_dir / core.WRAPPER_DLL_NAME, expected_dir / core.DXCFG_NAME,
                expected_dir / core.MANIFEST_NAME)
    if plan.stage != STAGE or plan.candidate_dir != expected_dir or _paths(plan) != expected:
        raise core.LauncherError("Framed candidate plan does not match its isolated profile.")
    for target in (plan.candidate_dir, *_paths(plan)):
        if (not core.is_under(target, plan.candidates_root)
                or core.is_under(target, plan.clash_dir) or core.is_under(target, core.REPO_ROOT)):
            raise core.LauncherError(f"Unsafe framed output path: {target}")
        if target.exists() and target.is_file() and target.stat().st_nlink != 1:
            raise core.LauncherError(f"Framed outputs must not use hard links: {target}")
        if any(path.is_symlink() or getattr(path, "is_junction", lambda: False)()
               for path in (target, *target.parents)):
            raise core.LauncherError(f"Framed outputs must not follow symbolic links: {target}")


def _original(plan: core.CandidatePlan) -> bytes:
    data = plan.base_exe.read_bytes()
    if (plan.expected_base_sha != core.patch_clash95_hd.EXPECTED_SHA256
            or core.sha256_bytes(data) != core.patch_clash95_hd.EXPECTED_SHA256):
        raise core.LauncherError("Base executable SHA-256 mismatch; framed building has no override.")
    return data


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _build(original: bytes, resolution: str) -> tuple[bytes, dict[str, Any], str]:
    builder = importlib.import_module("build_framed_candidate")
    return builder.build_candidate(original, resolution, minimap_viewport=True)


def ensure_candidate(plan: core.CandidatePlan, progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    say = progress or (lambda message: None)
    try:
        _assert_plan(plan)
        bindings = _bindings()
        original = _original(plan)
        image, metadata, probe = _build(original, plan.resolution)
        output_sha = core.sha256_bytes(image)
        if (metadata.get("stage") != STAGE or metadata.get("resolution") != plan.resolution
                or metadata.get("output_sha256") != output_sha
                or metadata.get("minimap_viewport") is not True
                or metadata.get("validation_stage_only") is not True
                or any(metadata.get(key) is not False for key in ("runtime_executed", "manual_input_proof", "promotion_ready"))
                or metadata.get("source_sha256") != {name: sha for name, sha in bindings.items() if name != "tools/build_framed_candidate.py"}):
            raise core.LauncherError("Framed builder metadata does not match the requested candidate.")
        report = dict(metadata)
        report.pop("generated_at", None)
        artifacts = {plan.candidate_exe: image, plan.candidate_dir / BUILD_REPORT: _json_bytes(report),
                     plan.candidate_dir / PROBE: probe.encode("utf-8")}
        reused = all(path.is_file() for path in artifacts)
        for path, content in artifacts.items():
            if path.exists() and (not path.is_file() or path.read_bytes() != content):
                raise core.LauncherError(f"Refusing to replace a different framed artifact: {path}. Clean this profile first.")
        plan.candidate_dir.mkdir(parents=True, exist_ok=True)
        for path, content in artifacts.items():
            if not path.exists():
                with path.open("xb") as stream:
                    stream.write(content)
            if path.read_bytes() != content:
                raise core.LauncherError(f"Framed artifact verification failed: {path}")
        say(WARNING)
        say(f"{'Reused' if reused else 'Prepared'} framed candidate: {plan.candidate_exe}")
        return {"reused": reused, "base_sha256": core.sha256_bytes(original),
                "output_sha256": output_sha,
                "patch_count": len(metadata.get("selected_patches", [])) + len(metadata.get("hooks", [])),
                "profile": PROFILE, "minimap_viewport": True, "source_sha256": bindings,
                "artifact_sha256": {path.name: core.sha256_bytes(content) for path, content in artifacts.items()},
                "game_runtime_executed": False, "manual_input_proof": False, "promotion_ready": False}
    except (OSError, ValueError, ImportError) as exc:
        raise core.LauncherError(f"Framed preparation failed: {exc}") from exc


def _verify_artifacts(plan: core.CandidatePlan, record: dict[str, Any], *, deployed: bool) -> None:
    if (record.get("profile") != PROFILE or record.get("minimap_viewport") is not True
            or record.get("source_sha256") != _bindings()
            or record.get("base_sha256") != core.sha256_bytes(_original(plan))
            or any(record.get(key) is not False for key in ("game_runtime_executed", "manual_input_proof", "promotion_ready"))):
        raise core.LauncherError("Framed candidate provenance does not match this source checkout.")
    paths = _paths(plan)[:5 if deployed else 3]
    hashes = record.get("artifact_sha256")
    if not isinstance(hashes, dict) or set(hashes) != {path.name for path in paths}:
        raise core.LauncherError("Framed artifact manifest is incomplete.")
    for path in paths:
        if not path.is_file() or core.sha256_bytes(path.read_bytes()) != hashes[path.name]:
            raise core.LauncherError(f"Framed artifact changed or is missing: {path}")
    if record.get("output_sha256") != hashes[plan.candidate_exe.name]:
        raise core.LauncherError("Framed output identity does not match its artifact manifest.")


def deploy_runtime_files(plan: core.CandidatePlan, candidate_result: dict[str, Any] | None = None,
                         progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    try:
        _assert_plan(plan)
        if not isinstance(candidate_result, dict):
            raise core.LauncherError("Prepare a verified framed candidate before deployment.")
        _verify_artifacts(plan, candidate_result, deployed=False)
        if not plan.wrapper_source.is_file():
            return {"wrapper": "missing", "wrapper_dll_sha256": None, "manifest": "not_written"}
        result = core.deploy_runtime_files(plan, candidate_result, progress=progress)
        manifest = core.read_candidate_manifest(plan)
        if not isinstance(manifest, dict):
            raise core.LauncherError("Deployment did not produce a candidate manifest.")
        manifest.update({key: value for key, value in candidate_result.items() if key != "reused"})
        manifest["artifact_sha256"] = {
            **candidate_result["artifact_sha256"],
            **{path.name: core.sha256_bytes(path.read_bytes()) for path in (plan.wrapper_target, plan.dxcfg_target)}}
        manifest["warning"] = WARNING
        plan.manifest_path.write_bytes(_json_bytes(manifest))
        return result
    except (OSError, ValueError) as exc:
        raise core.LauncherError(f"Framed deployment failed: {exc}") from exc


def verify_launch(plan: core.CandidatePlan) -> None:
    try:
        _assert_plan(plan)
        manifest = core.read_candidate_manifest(plan)
        if (not isinstance(manifest, dict) or manifest.get("schema") != core.MANIFEST_SCHEMA
                or manifest.get("stage") != STAGE or manifest.get("resolution") != plan.resolution
                or manifest.get("scaling_mode") != plan.scaling_mode):
            raise core.LauncherError("Framed launch requires a matching deployed manifest.")
        _verify_artifacts(plan, manifest, deployed=True)
    except (OSError, ValueError) as exc:
        raise core.LauncherError(f"Framed launch failed: {exc}") from exc
