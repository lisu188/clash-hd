#!/usr/bin/env python3
"""Profile-scoped resolution metadata and shared recipe validation."""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.display_plan import DEFAULT_BOUNDS, RECIPE_REVISION, DisplayPlan, DisplayPlanError, parse_dimensions, resolve_display_plan


MANIFEST_PATH = Path(__file__).resolve().parent / "resolutions.json"
RESOLUTION_KEY_RE = re.compile(r"([1-9][0-9]{2,3})x([1-9][0-9]{2,3})")
VALID_STATUSES = ("stable", "validated", "experimental")


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class ResolutionOption:
    key: str
    width: int
    height: int
    status: str
    tiles: tuple[int, int] | None
    evidence: dict[str, str] | None

    @property
    def is_experimental(self) -> bool:
        return self.status == "experimental"


def parse_resolution_key(key: str) -> tuple[int, int]:
    match = RESOLUTION_KEY_RE.fullmatch(key) if type(key) is str else None
    if not match:
        raise ManifestError(f"Resolution key must look like 800x600, got: {key!r}")
    return int(match.group(1)), int(match.group(2))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError(f"Duplicate resolution manifest key: {key}")
        result[key] = value
    return result


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise ManifestError(f"Resolutions manifest not found: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ManifestError(f"Resolutions manifest is not valid JSON: {path}: {exc}") from exc
    validate_manifest(manifest)
    return manifest


def _profile(manifest: dict[str, Any], renderer: str) -> dict[str, Any]:
    if type(renderer) is not str or renderer not in RECIPE_REVISION:
        raise ManifestError(f"Unknown renderer profile: {renderer!r}")
    if manifest["schema"] == 2:
        return manifest["profiles"][renderer]
    stage = str(manifest.get("stable_stage"))
    entries = manifest["resolutions"]
    if renderer == "framed":
        stage += "-combinedui-partialtiles-initialpaint-framed-validation"
        entries = {key: {"status": "experimental", "tiles": None, "evidence": None} for key in entries}
    return {"stage": stage, "recipe_revision": RECIPE_REVISION[renderer],
            "features": {"minimap_viewport": renderer == "framed"},
            "default": manifest["default"], "resolutions": entries}


def _scope(config: dict[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(config[key]) for key in ("stage", "recipe_revision", "features")}


def _bounds(manifest: dict[str, Any]) -> tuple[tuple[int, int], tuple[int, int]]:
    data = manifest.get("custom_bounds") or {"min": list(DEFAULT_BOUNDS[0]), "max": list(DEFAULT_BOUNDS[1])}
    if (not isinstance(data, dict) or any(not isinstance(data.get(key), list) or len(data[key]) != 2
            or any(type(n) is not int for n in data[key]) for key in ("min", "max"))):
        raise ManifestError("custom_bounds requires integer min/max dimension pairs.")
    low, high = tuple(data["min"]), tuple(data["max"])
    if any(not DEFAULT_BOUNDS[0][i] <= low[i] <= high[i] <= DEFAULT_BOUNDS[1][i] for i in (0, 1)):
        raise ManifestError("custom_bounds must stay within the 800x600..3840x2160 launcher envelope.")
    return low, high


def validate_manifest(manifest: dict[str, Any]) -> None:
    if not isinstance(manifest, dict) or type(manifest.get("schema")) is not int or manifest["schema"] not in (1, 2):
        raise ManifestError("Resolutions manifest must have schema 1 or 2.")
    if not isinstance(manifest.get("resolutions"), dict) or not manifest["resolutions"]:
        raise ManifestError("Resolutions manifest lists no Classic compatibility resolutions.")
    if type(manifest.get("custom_allowed")) is not bool:
        raise ManifestError("custom_allowed must be an explicit boolean.")
    if type(manifest.get("default")) is not str or manifest["default"] not in manifest["resolutions"]:
        raise ManifestError("Classic default must identify an available resolution.")
    if type(manifest.get("stable_stage")) is not str or not manifest["stable_stage"]:
        raise ManifestError("Classic stable_stage is missing.")
    bounds = _bounds(manifest)
    if manifest["schema"] == 2:
        profiles = manifest.get("profiles")
        if not isinstance(profiles, dict) or set(profiles) != set(RECIPE_REVISION):
            raise ManifestError("Schema 2 requires separate Classic and Framed profiles.")
        if not all(isinstance(config, dict) for config in profiles.values()):
            raise ManifestError("Renderer profiles must be objects.")
        classic = profiles["classic"]
        if (manifest.get("default_renderer") != "classic" or manifest.get("default") != classic.get("default")
                or manifest["stable_stage"] != classic.get("stage") or manifest["resolutions"] != classic.get("resolutions")):
            raise ManifestError("Legacy fields must exactly project the Classic profile, not another renderer.")
    for renderer in RECIPE_REVISION:
        config = _profile(manifest, renderer)
        if (config.get("recipe_revision") != RECIPE_REVISION[renderer] or type(config.get("stage")) is not str
                or not config["stage"] or config.get("features") != {"minimap_viewport": renderer == "framed"}
                or type(config.get("features", {}).get("minimap_viewport")) is not bool):
            raise ManifestError(f"Unrecognized {renderer} recipe or feature configuration.")
        entries = config.get("resolutions")
        if not isinstance(entries, dict) or not entries or type(config.get("default")) is not str or config["default"] not in entries:
            raise ManifestError(f"{renderer} must have an available default resolution.")
        for key, entry in entries.items():
            parse_resolution_key(key)
            try:
                parse_dimensions(key, bounds)
            except DisplayPlanError as exc:
                raise ManifestError(str(exc)) from exc
            if not isinstance(entry, dict) or entry.get("status") not in VALID_STATUSES:
                raise ManifestError(f"Resolution {renderer}/{key} has invalid status metadata.")
            tiles, evidence = entry.get("tiles"), entry.get("evidence")
            if tiles is not None and (not isinstance(tiles, list) or len(tiles) != 2 or any(type(n) is not int or n <= 0 for n in tiles)):
                raise ManifestError(f"Resolution {renderer}/{key} has invalid tile metadata.")
            if evidence is not None and (not isinstance(evidence, dict) or not evidence
                    or any(type(value) is not str or not value for value in evidence.values())):
                raise ManifestError(f"Resolution {renderer}/{key} has invalid evidence references.")
            if entry["status"] != "experimental":
                if evidence is None:
                    raise ManifestError(f"Resolution {renderer}/{key} has no evidence references for its status.")
                if manifest["schema"] == 2:
                    scope = entry.get("evidence_scope")
                    if (not isinstance(scope, dict) or scope != _scope(config)
                            or not isinstance(scope.get("features"), dict)
                            or type(scope["features"].get("minimap_viewport")) is not bool):
                        raise ManifestError(f"Resolution {renderer}/{key} evidence belongs to a different recipe or feature set.")


def load_options(manifest: dict[str, Any] | None = None, renderer: str = "classic") -> list[ResolutionOption]:
    manifest = manifest if manifest is not None else load_manifest()
    validate_manifest(manifest)
    result = []
    for key, entry in _profile(manifest, renderer)["resolutions"].items():
        width, height = parse_resolution_key(key)
        result.append(ResolutionOption(key, width, height, entry["status"],
                                       tuple(entry["tiles"]) if entry.get("tiles") else None,
                                       copy.deepcopy(entry.get("evidence"))))
    return result


def default_key(manifest: dict[str, Any] | None = None, renderer: str = "classic") -> str:
    manifest = manifest if manifest is not None else load_manifest()
    validate_manifest(manifest)
    return _profile(manifest, renderer)["default"]


def stable_stage(manifest: dict[str, Any] | None = None) -> str:
    manifest = manifest if manifest is not None else load_manifest()
    validate_manifest(manifest)
    return manifest["stable_stage"]


def custom_bounds(manifest: dict[str, Any] | None = None) -> tuple[tuple[int, int], tuple[int, int]]:
    manifest = manifest if manifest is not None else load_manifest()
    return _bounds(manifest)


def validate_custom_resolution(width: int, height: int, manifest: dict[str, Any] | None = None) -> list[str]:
    manifest = manifest if manifest is not None else load_manifest()
    validate_manifest(manifest)
    if not manifest["custom_allowed"]:
        return ["Custom resolutions are disabled by the manifest."]
    if type(width) is not int or type(height) is not int:
        return ["Custom resolution dimensions must be integers, excluding booleans."]
    try:
        parse_dimensions(f"{width}x{height}", _bounds(manifest))
    except DisplayPlanError as exc:
        return [str(exc)]
    return []


def resolve_plan(*, renderer: str = "classic", resolution: str = "800x600", stage: str | None = None,
                 scaling_mode: str = "integer", manifest: dict[str, Any] | None = None) -> DisplayPlan:
    manifest = manifest if manifest is not None else load_manifest()
    validate_manifest(manifest)
    config = _profile(manifest, renderer)
    parse_dimensions(resolution, _bounds(manifest))
    if resolution not in config["resolutions"] and not manifest["custom_allowed"]:
        raise DisplayPlanError("custom_disabled", "Custom resolutions are disabled for this renderer.")
    return resolve_display_plan(renderer=renderer, resolution=resolution, stage=stage if stage is not None else config["stage"],
                                scaling_mode=scaling_mode, minimap_viewport=config["features"]["minimap_viewport"],
                                bounds=_bounds(manifest))


def resolution_info(resolution: str, *, renderer: str = "classic", stage: str | None = None,
                    scaling_mode: str = "integer", manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = manifest if manifest is not None else load_manifest()
    validate_manifest(manifest)
    config = _profile(manifest, renderer)
    result = {"renderer": renderer, "resolution": resolution, "status": "experimental",
              "recipe_eligible": False, "evidence_references": None, "runtime_evidence_verified": False}
    try:
        plan = resolve_plan(renderer=renderer, resolution=resolution, stage=stage, scaling_mode=scaling_mode, manifest=manifest)
    except DisplayPlanError as exc:
        result.update(error_code=exc.code, error=str(exc))
        return result
    entry = config["resolutions"].get(resolution)
    if entry is not None and plan.stage == config["stage"] and plan.recipe_revision == config["recipe_revision"]:
        result.update(status=entry["status"], evidence_references=copy.deepcopy(entry.get("evidence")))
    result.update(recipe_eligible=True, display_plan=plan.to_dict())
    return result


def patcher_supports_resolutions(patcher: Any) -> bool:
    return callable(getattr(patcher, "parse_resolution", None)) and callable(getattr(patcher, "select_patches_for", None))
