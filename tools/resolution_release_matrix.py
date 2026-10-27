#!/usr/bin/env python3
"""Read-only 36-cell readiness; immutable references never substitute for proof.

Candidate authentication does not establish release acceptance. Missing lane
and expanded-battle verifiers remain failures; no status is promoted.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import sys
import types
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _directory in (ROOT, ROOT / "tools"):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import complete_hd_evidence as evidence

MATRIX_SCHEMA = "resolution_release_matrix_v1"
PROFILES = ("classic", "framed", "completehd", "modalwidgets")
PRESETS = ("800x600", "1024x768", "1280x720", "1280x960", "1366x768",
           "1920x1080", "2560x1440", "3440x1440", "3840x2160")
REQUIRED_IDS = tuple(f"{profile}/{resolution}" for profile in PROFILES for resolution in PRESETS)
CUSTOM_REGRESSION = "802x602"
CANDIDATE_ROOT = Path("C:/ClashTests")
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
MULTIRES_REVISION = "hd_multires_v1"
MULTIRES_PRESETS = ("1920x1080", "2560x1440", "3840x2160")
MULTIRES_METADATA_BYTES = 16 * 1024 * 1024
MULTIRES_PROBE_BYTES = 64 * 1024 * 1024
RUNTIME_POLICY = "read-only candidate/evidence checks; no runtime, capture, input, status or promotion writes"
REQUIRED_ACCEPTANCE = (*evidence.LANES, "candidate_bound_expanded_battle")
# These describe the additive cell schema, not the legacy 1920x1080 registry.
# In particular the legacy native panel adapter is not matrix-context proof.
MATRIX_CONTEXT_LANE_VERIFIERS = ("resolution_coverage",)
MATRIX_CONTEXT_UNIMPLEMENTED_LANES = tuple(name for name in evidence.LANES if name not in MATRIX_CONTEXT_LANE_VERIFIERS)
# Repository code selects recipes.
RECIPE_MODULES = {
    "classic-frozen-800-v1": "patch_clash95_hd",
    "classic_menu_widgets_v1": "src.patcher.classic_menu_candidate",
    "four-border-partial-initial-v1": "build_framed_candidate",
    "complete_hd_v1": "src.patcher.complete_hd_candidate",
    "owned_modal_widget_bounds_v1": "build_framed_modal_widgets_candidate",
    "complete_hd_all_presets_v1": "src.patcher.complete_hd_all_presets_candidate",
    "modal_widgets_all_presets_v1": "src.patcher.modal_widgets_all_presets_candidate",
    "classic_all_presets_v1": "src.patcher.classic_all_presets_candidate",
    "framed_all_presets_v1": "src.patcher.framed_all_presets_candidate",
    MULTIRES_REVISION: "src.patcher.hd_multires_candidate",
}
# Source authentication is available before launcher registration. These fixed
# validation recipes never replace the launcher-resolved recipes above; an
# unadvertised preset and missing runtime/promotion proof remain gate failures.
VALIDATION_RECIPES = {
    "classic_all_presets_v1": {
        "profile": "classic", "stage": evidence.STABLE_STAGE + "-classic-allpresets-validation",
    },
    "framed_all_presets_v1": {
        "profile": "framed", "stage": evidence.STABLE_STAGE + "-framed-allpresets-validation",
    },
    "complete_hd_all_presets_v1": {
        "profile": "completehd", "stage": evidence.STABLE_STAGE + "-completehd-allpresets-validation",
    },
    "modal_widgets_all_presets_v1": {
        "profile": "modalwidgets", "stage": evidence.STABLE_STAGE + "-modalwidgets-allpresets-validation",
    },
}
PROFILE_RECIPES = {
    "classic": ("classic-frozen-800-v1", "classic_menu_widgets_v1", MULTIRES_REVISION),
    "framed": ("four-border-partial-initial-v1", MULTIRES_REVISION),
    "completehd": ("complete_hd_v1", MULTIRES_REVISION),
    "modalwidgets": ("owned_modal_widget_bounds_v1", MULTIRES_REVISION),
}
RECIPE_SOURCES = {
    "classic-frozen-800-v1": ("patch_clash95_hd.py", "src/patcher/patch_clash95_hd.py", "src/display_plan.py"),
    "classic_menu_widgets_v1": ("src/patcher/classic_menu_candidate.py",),
    "four-border-partial-initial-v1": ("tools/build_framed_candidate.py",),
    "complete_hd_v1": ("src/patcher/complete_hd_candidate.py",),
    "owned_modal_widget_bounds_v1": ("tools/build_framed_modal_widgets_candidate.py",),
    "complete_hd_all_presets_v1": ("src/patcher/complete_hd_all_presets_candidate.py",),
    "modal_widgets_all_presets_v1": (
        "src/patcher/modal_widgets_all_presets_candidate.py", "src/patcher/owned_modal_all_presets_emit.py"),
    "classic_all_presets_v1": ("src/patcher/classic_all_presets_candidate.py",),
    "framed_all_presets_v1": ("src/patcher/framed_all_presets_candidate.py",),
    MULTIRES_REVISION: ("src/patcher/hd_multires_candidate.py", "src/patcher/hd_multires_issuer.py"),
}
COMPLETE_AUTH_SOURCE = "tools/resolution_recipe_authentication.py"
COMPLETE_AUTH_SHA256 = "60157b38b6ba2975b2c0cdd3e24e5221ac4a122b42f3ac5a52373ddcc1840a82"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def json_object(data: bytes, label: str) -> dict:
    def finite_number(token):
        number = float(token)
        if not math.isfinite(number):
            raise ValueError("nonfinite JSON number is invalid")
        return number
    try:
        value = json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_object,
                           parse_constant=finite_number, parse_float=finite_number)
    except RecursionError as exc:
        raise ValueError(f"{label} exceeds JSON parser capacity") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    pending = [(value, 1)]
    while pending:
        container, depth = pending.pop()
        if depth > evidence.MAX_JSON_CONTAINER_DEPTH:
            raise ValueError(f"{label} JSON container nesting exceeds {evidence.MAX_JSON_CONTAINER_DEPTH}")
        children = container.values() if isinstance(container, dict) else container
        pending.extend((child, depth + 1) for child in children if isinstance(child, (dict, list)))
    return value


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _plain_path(path: Path) -> Path:
    absolute = path.absolute()
    for ancestor in (absolute, *absolute.parents):
        if ancestor.is_symlink() or getattr(ancestor, "is_junction", lambda: False)():
            raise ValueError(f"artifact must not follow a symlink or junction: {absolute}")
        if ancestor.exists() and getattr(ancestor.stat(), "st_file_attributes", 0) & 0x400:
            raise ValueError(f"artifact must not follow a reparse point: {absolute}")
    return absolute.resolve()


def _bounded_bytes(path: Path, label: str, maximum: int) -> bytes:
    with path.open("rb") as source:
        data = source.read(maximum + 1)
    if not data or len(data) > maximum:
        raise ValueError(f"{label} must contain bounded nonempty bytes")
    return data


def _json_bytes(path: Path, label: str) -> bytes:
    """Reference envelopes/metadata are bounded even on failure paths."""
    return _bounded_bytes(path, label, MAX_JSON_BYTES)


def read_reference(ref: Any, base: Path, *, object_required=False, maximum=None) -> tuple[Path, Any]:
    if (not isinstance(ref, dict) or set(ref) != {"path", "sha256"}
            or not evidence._text(ref.get("path"))
            or not isinstance(ref.get("sha256"), str) or not evidence.SHA_RE.fullmatch(ref["sha256"])):
        raise ValueError("immutable reference requires only a real path and 64-hex sha256")
    given = Path(ref["path"])
    path = _plain_path(given if given.is_absolute() else base / given)
    limit = MAX_JSON_BYTES if object_required else MAX_ARTIFACT_BYTES
    data = _bounded_bytes(path, str(path), limit if maximum is None else maximum)
    if sha(data) != ref["sha256"].lower():
        raise ValueError(f"artifact SHA-256 mismatch: {path}")
    return path, json_object(data, str(path)) if object_required else data


def _multires_identity(identity: dict) -> bool:
    profile, resolution = identity.get("profile"), identity.get("resolution")
    return (profile in PROFILES and resolution in MULTIRES_PRESETS
            and identity.get("recipe_revision") == MULTIRES_REVISION
            and identity.get("stage") == evidence.STABLE_STAGE + f"-{profile}-hd-multires-validation")


def candidate_artifact_limit(identity: dict, name: str, *, json_default=None, binary_default=None) -> int:
    """Large sidecars belong only to the exact twelve-cell source recipe."""
    if _multires_identity(identity):
        if name == "metadata":
            return MULTIRES_METADATA_BYTES
        if name == "probe":
            return MULTIRES_PROBE_BYTES
    return (MAX_ARTIFACT_BYTES if binary_default is None else binary_default) if name in (
        "base_executable", "executable") else (MAX_JSON_BYTES if json_default is None else json_default)


def _source_hashes(names, repo_root: Path) -> dict[str, str]:
    result = {}
    for name in names:
        if not isinstance(name, str) or not name or "\\" in name:
            raise ValueError("producer source paths must be repository-relative")
        relative = Path(name)
        path = _plain_path(repo_root / relative)
        if relative.is_absolute() or ".." in relative.parts or not path.is_relative_to(repo_root.resolve()):
            raise ValueError(f"producer source escapes repository: {name}")
        result[name] = sha(path.read_bytes())
    return result


def _inventory(repo_root: Path) -> tuple[dict, dict]:
    from src.launcher import presets
    manifest = presets.load_manifest(repo_root / "src/launcher/resolutions.json")
    if manifest.get("schema") != 2 or set(manifest.get("profiles", {})) != set(PROFILES):
        raise ValueError("matrix requires the actual four-profile schema-2 launcher catalog")
    if (manifest.get("default_renderer") != "classic" or manifest.get("default") != "800x600"
            or manifest.get("stable_stage") != evidence.STABLE_STAGE):
        raise ValueError("matrix preserves the protected Classic/800x600 fallback")
    cells = {}
    for cell_id in REQUIRED_IDS:
        profile, resolution = cell_id.split("/")
        row = {"id": cell_id, "profile": profile, "resolution": resolution,
               "preset_advertised": resolution in manifest["profiles"][profile]["resolutions"],
               "recipe_eligible": False, "source_recipe": None, "recipe_failures": []}
        try:
            display = presets.resolve_plan(renderer=profile, resolution=resolution, manifest=manifest)
            if display.recipe_revision not in PROFILE_RECIPES[profile]:
                raise ValueError("resolved recipe is not in the fixed profile registry")
            if display.recipe_revision == MULTIRES_REVISION and not _multires_identity({
                    "profile": profile, "resolution": resolution, "stage": display.stage,
                    "recipe_revision": display.recipe_revision}):
                raise ValueError("multiresolution recipe requires its exact profile, preset and stage")
            row.update(recipe_eligible=True, source_recipe={"stage": display.stage,
                       "recipe_revision": display.recipe_revision,
                       "features": {"minimap_viewport": display.minimap_viewport}})
        except (ValueError, OSError, ImportError) as exc:
            row["recipe_failures"].append(str(exc))
        cells[cell_id] = row
    return manifest, cells


def _rebuild(profile: str, resolution: str, original: bytes, display, repo_root: Path) -> dict:
    if repo_root.resolve() != ROOT.resolve():
        raise ValueError("production reconstruction requires the fixed repository ROOT")
    revision = display.recipe_revision
    validation = VALIDATION_RECIPES.get(revision)
    if validation is not None:
        if (validation["profile"] != profile or resolution not in PRESETS
                or display.stage != validation["stage"]):
            raise ValueError("validation recipe does not belong to this exact profile, preset and stage")
    elif revision not in PROFILE_RECIPES[profile]:
        raise ValueError("resolved recipe is not in the fixed profile registry")
    before = _source_hashes(RECIPE_SOURCES[revision], repo_root)
    module = importlib.import_module(RECIPE_MODULES[revision])
    if Path(module.__file__).resolve() != (ROOT / RECIPE_SOURCES[revision][0]).resolve():
        raise ValueError("loaded recipe module belongs to another checkout")
    if validation is not None and (
            getattr(module, "ROOT", None) != ROOT or getattr(module, "STAGE", None) != validation["stage"]
            or getattr(module, "REVISION", None) != revision or getattr(module, "RESOLUTIONS", None) != PRESETS):
        raise ValueError("loaded validation recipe constants differ from the fixed source contract")
    if revision == "classic-frozen-800-v1":
        if Path(module._IMPL.__file__).resolve() != (ROOT / "src/patcher/patch_clash95_hd.py").resolve():
            raise ValueError("Classic shim loaded a patcher from another checkout")
        parsed = module.parse_resolution(resolution)
        patches = module.select_patches_for(display.stage, parsed)
        module.validate_input(original, patches)
        image = module.apply_patches(original, patches)
        inputs = {"generated/scalar-patches.json": display.scalar_patch_sha256}
        metadata = {"schema": 1, "profile": profile, "stage": display.stage,
                    "resolution": resolution, "scaling_mode": "integer",
                    "base_sha256": sha(original), "output_sha256": sha(image),
                    "patch_count": len(patches), "display_plan": display.to_dict(),
                    "build_inputs": inputs, "build_id": display.build_identity(sha(original), inputs)}
        probe, projection, source_pins = None, True, {}
    else:
        options = {"minimap_viewport": True} if profile == "framed" and validation is None else {}
        image, metadata, probe = module.build_candidate(original, resolution, **options)
        projection = False
        source_pins = metadata.get("source_hashes", metadata.get("source_sha256", {}))
        if not isinstance(source_pins, dict) or not source_pins:
            raise ValueError("candidate builder lacks producer source pins")
    actual_sources = _source_hashes(source_pins, repo_root)
    if actual_sources != source_pins or before != _source_hashes(before, repo_root):
        raise ValueError("candidate producer source identity changed or differs from pinned bytes")
    if not isinstance(image, bytes) or not isinstance(metadata, dict) or (probe is not None and not isinstance(probe, str)):
        raise ValueError("fixed recipe returned invalid candidate bundle types")
    return {"image": image, "metadata": metadata, "probe": probe, "projection": projection,
            "source_hashes": {**before, **actual_sources}}


def _complete_recipe_reconstructor():
    """Capture fixed source execution, never an imported public helper export."""
    root, path, pin = ROOT, ROOT / COMPLETE_AUTH_SOURCE, COMPLETE_AUTH_SHA256
    registered, module_type, fresh = sys.modules, types.ModuleType, uuid.uuid4
    digest, compiler, execute = hashlib.sha256, compile, exec
    def read_source():
        if path.resolve(strict=True) != path or not path.is_relative_to(root):
            raise ValueError("Complete recipe helper escaped the fixed canonical ROOT")
        for entry in (path, *path.parents):
            if (entry.is_symlink() or getattr(entry, "is_junction", lambda: False)()
                    or getattr(entry.stat(), "st_file_attributes", 0) & 0x400):
                raise ValueError("Complete recipe helper has a reparse ancestor")
        before = path.stat()
        if not 0 < before.st_size <= 2 * 1024**2:
            raise ValueError("Complete recipe helper exceeded its source read bound")
        raw = path.read_bytes()
        after = path.stat()
        stamp = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
        if stamp(before) != stamp(after) or len(raw) != before.st_size:
            raise ValueError("Complete recipe helper changed while reading or exceeded its bound")
        if digest(raw).hexdigest() != pin:
            raise ValueError("Complete recipe helper source pin differs")
        return raw, stamp(after)
    def rebuild(original, *, profile, resolution, recipe_revision, stage):
        raw, stamp = read_source()
        name = "_clash_matrix_complete_auth_" + fresh().hex
        if name in registered:
            raise ValueError("private Complete recipe namespace collision")
        module = module_type(name); module.__file__ = str(path)
        registered[name] = module
        try:
            execute(compiler(raw, str(path), "exec"), module.__dict__)
            if module.__file__ != str(path) or module.__name__ != name:
                raise ValueError("private Complete recipe helper identity changed")
            if read_source() != (raw, stamp):
                raise ValueError("Complete recipe helper changed during private execution")
            api = module.rebuild_recipe
            return api(original, profile=profile, resolution=resolution,
                       recipe_revision=recipe_revision, stage=stage)
        finally:
            try:
                if read_source() != (raw, stamp):
                    raise ValueError("Complete recipe helper changed during reconstruction")
            finally:
                if registered.get(name) is module:
                    del registered[name]
    return rebuild


def _bind_complete_rebuild(legacy):
    # Keep the five-argument override interface. Capture the private loader
    # before later public aliases can replace the recipe or helper callable.
    complete, root = _complete_recipe_reconstructor(), ROOT
    revisions = frozenset(("complete_hd_v1", "complete_hd_all_presets_v1"))
    stages = {"complete_hd_v1": evidence.STAGE,
              "complete_hd_all_presets_v1": VALIDATION_RECIPES["complete_hd_all_presets_v1"]["stage"]}
    presets = tuple(PRESETS)
    def rebuild(profile, resolution, original, display, repo_root):
        if display.recipe_revision in revisions:
            if repo_root.resolve() != root.resolve():
                raise ValueError("production reconstruction requires the fixed repository ROOT")
            if profile != "completehd" or resolution not in presets or display.stage != stages[display.recipe_revision]:
                raise ValueError("Complete recipe does not belong to this exact profile, preset and stage")
            return complete(original, profile=profile, resolution=resolution,
                            recipe_revision=display.recipe_revision, stage=display.stage)
        return legacy(profile, resolution, original, display, repo_root)
    return rebuild


_rebuild = _bind_complete_rebuild(_rebuild)


def _multires_recipe_reconstructor():
    """Capture canonical raw issuance before mutable public aliases exist."""
    root = ROOT
    path = root / "src/patcher/hd_multires_issuer.py"
    plain, bounded, digest = _plain_path, _bounded_bytes, sha
    compiler, execute = compile, exec
    profiles, presets, revision = tuple(PROFILES), tuple(MULTIRES_PRESETS), MULTIRES_REVISION
    stable_stage = evidence.STABLE_STAGE

    def read_source():
        if plain(path) != path or not path.is_relative_to(root):
            raise ValueError("HD issuer must retain its fixed canonical source path")
        before = path.stat()
        raw = bounded(path, "HD issuer source", 4 * 1024 * 1024)
        after = path.stat()
        stamp = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns)
        if stamp(before) != stamp(after) or len(raw) != before.st_size:
            raise ValueError("HD issuer source changed while reading")
        return raw, stamp(after)

    captured = read_source()
    issuer_sha = digest(captured[0])
    values = {"__file__": str(path), "__name__": "_matrix_hd_multires_source_issuer", "__package__": None}
    execute(compiler(captured[0], str(path), "exec"), values)
    issuer, _ = values["create_issuer"]()
    if read_source() != captured:
        raise ValueError("HD issuer source changed during capture")

    def rebuild(original, *, profile, resolution, recipe_revision, stage):
        if (profile not in profiles or resolution not in presets or recipe_revision != revision
                or stage != stable_stage + f"-{profile}-hd-multires-validation"):
            raise ValueError("HD recipe requires its exact fixed profile, preset and stage")
        if read_source() != captured:
            raise ValueError("captured HD issuer source differs")
        try:
            image, metadata, probe = issuer(original, resolution, profile=profile)
            if (type(image) is not bytes or type(metadata) is not dict or type(probe) is not str
                    or metadata.get("profile") != profile or metadata.get("resolution") != resolution
                    or metadata.get("stage") != stage or metadata.get("recipe_revision") != recipe_revision
                    or metadata.get("candidate_sha256") != digest(image)
                    or metadata.get("probe_sha256") != digest(probe.encode("utf-8"))
                    or metadata.get("source_hashes", {}).get("src/patcher/hd_multires_issuer.py") != issuer_sha):
                raise ValueError("canonical HD source bundle identity differs")
            return {"image": image, "metadata": metadata, "probe": probe, "projection": False,
                    "source_hashes": metadata["source_hashes"]}
        finally:
            if read_source() != captured:
                raise ValueError("HD issuer source changed during reconstruction")
    return rebuild


def _bind_multires_rebuild(legacy):
    canonical, root = _multires_recipe_reconstructor(), ROOT
    revision = MULTIRES_REVISION
    def rebuild(profile, resolution, original, display, repo_root):
        if display.recipe_revision == revision:
            if repo_root.resolve() != root.resolve():
                raise ValueError("production reconstruction requires the fixed repository ROOT")
            return canonical(original, profile=profile, resolution=resolution,
                recipe_revision=display.recipe_revision, stage=display.stage)
        return legacy(profile, resolution, original, display, repo_root)
    return rebuild


_rebuild = _bind_multires_rebuild(_rebuild)


def authenticate_candidate(cell_id: str, spec: Any, base: Path, manifest: dict,
                           *, repo_root: Path = ROOT) -> dict:
    """Reconstruct candidate bytes without runtime."""
    if cell_id not in REQUIRED_IDS or not isinstance(spec, dict):
        raise ValueError("candidate must belong to one exact required matrix cell")
    if not {"base_executable", "executable", "metadata"} <= set(spec) <= {"base_executable", "executable", "metadata", "probe"}:
        raise ValueError("candidate requires base_executable, executable, metadata and recipe-specific probe references")
    profile, resolution = cell_id.split("/")
    from src.launcher import presets
    try:
        selected = presets.resolve_plan(renderer=profile, resolution=resolution, manifest=manifest)
    except (ValueError, OSError, ImportError):
        selected = None
    selected_hd = selected is not None and _multires_identity({"profile": profile, "resolution": resolution,
        "stage": selected.stage, "recipe_revision": selected.recipe_revision})
    paths, values, refs = {}, {}, {}
    for name in ("base_executable", "executable", "metadata", "probe"):
        if name not in spec:
            continue
        reference = spec[name]
        maximum = MULTIRES_METADATA_BYTES if selected_hd and name == "metadata" else None
        if name == "probe" and selected_hd and values["metadata"].get("recipe_revision") == MULTIRES_REVISION:
            maximum = MULTIRES_PROBE_BYTES
        path, value = read_reference(reference, base, object_required=name == "metadata", maximum=maximum)
        if name == "metadata" and value.get("recipe_revision") != MULTIRES_REVISION and path.stat().st_size > MAX_JSON_BYTES:
            raise ValueError("legacy candidate metadata exceeds its unchanged JSON bound")
        if name == "metadata" and value.get("recipe_revision") == MULTIRES_REVISION and (
                not selected_hd or value.get("profile") != profile or value.get("resolution") != resolution
                or value.get("stage") != selected.stage):
            raise ValueError("HD producer metadata differs from the exact selected profile, preset or stage")
        paths[name], values[name] = path, value
        refs[name] = {"path": str(path), "sha256": reference["sha256"].lower()}
    candidate_path = paths["executable"]
    if (candidate_path.suffix.lower() != ".exe" or candidate_path == paths["base_executable"]
            or not candidate_path.is_relative_to(CANDIDATE_ROOT.resolve())
            or candidate_path.is_relative_to(repo_root.resolve()) or candidate_path.stat().st_nlink != 1):
        raise ValueError("candidate must be an isolated external executable under C:/ClashTests")
    for name in ("metadata", "probe"):
        if name in paths and not paths[name].is_relative_to(CANDIDATE_ROOT.resolve()):
            raise ValueError("candidate sidecars must remain under C:/ClashTests")
    if len(set(paths.values())) != len(paths):
        raise ValueError("candidate artifacts must be distinct")
    original, actual, metadata = values["base_executable"], values["executable"], values["metadata"]
    if sha(original) != evidence.BASE_SHA256:
        raise ValueError("unknown original executable SHA-256; matrix has no override")
    revision = metadata.get("recipe_revision")
    if revision == MULTIRES_REVISION and not selected_hd:
        raise ValueError("HD recipe is not selected by this exact launcher profile/preset")
    validation = VALIDATION_RECIPES.get(revision) if isinstance(revision, str) else None
    advertised = resolution in manifest["profiles"][profile]["resolutions"]
    if validation is not None:
        if validation["profile"] != profile or metadata.get("stage") != validation["stage"]:
            raise ValueError("validation recipe does not belong to this exact profile and stage")
        display = SimpleNamespace(recipe_revision=revision, stage=validation["stage"])
        selection_scope = "unregistered_source_validation_recipe"
    else:
        if not advertised:
            raise ValueError("candidate preset is not advertised by the actual launcher profile")
        if revision in PROFILE_RECIPES[profile] and revision != MULTIRES_REVISION and selected is not None and selected.recipe_revision != revision:
            try:
                display = presets.resolve_plan(renderer=profile, resolution=resolution,
                    stage=metadata.get("stage"), manifest=manifest)
            except (ValueError, OSError, ImportError) as error:
                raise ValueError("candidate producer metadata differs from its fixed legacy stage") from error
            if display.recipe_revision != revision:
                raise ValueError("legacy recipe revision differs from its fixed explicit stage")
            selection_scope = "legacy_source_recipe"
        else:
            display = presets.resolve_plan(renderer=profile, resolution=resolution, manifest=manifest)
            selection_scope = "launcher_resolved_recipe"
    try:
        rebuilt = _rebuild(profile, resolution, original, display, repo_root)
    except SystemExit as exc:
        raise ValueError(f"candidate old-byte validation rejected the original: {exc}") from exc
    expected_metadata = json.loads(canonical(rebuilt["metadata"]))
    if rebuilt["projection"]:
        extras = {"generated_at", "launcher_version", "wrapper_dll_sha256", "deployment_id"}
        if (set(metadata) - set(expected_metadata) - extras or not set(expected_metadata) <= set(metadata)
                or canonical({key: metadata[key] for key in expected_metadata}) != canonical(expected_metadata)):
            raise ValueError("Classic producer metadata differs from exact source reconstruction")
    else:
        observed = dict(metadata)
        expected_metadata = dict(expected_metadata)
        if profile == "framed" and display.recipe_revision == "four-border-partial-initial-v1":
            # Only the legacy Framed recipe emits this wall-clock field.
            observed.pop("generated_at", None)
            expected_metadata.pop("generated_at", None)
        if canonical(observed) != canonical(expected_metadata):
            raise ValueError("candidate producer metadata differs from exact source reconstruction")
    if actual != rebuilt["image"]:
        raise ValueError("candidate bytes differ from exact source reconstruction")
    probe = rebuilt["probe"]
    if probe is None:
        if "probe" in values:
            raise ValueError("the frozen Classic recipe produces no canonical probe sidecar")
    elif values.get("probe") != probe.encode("utf-8"):
        raise ValueError("candidate probe differs from exact source reconstruction")
    if metadata.get("stage") != display.stage or metadata.get("resolution") != resolution:
        raise ValueError("candidate metadata differs from resolved profile stage or resolution")
    if _source_hashes(rebuilt["source_hashes"], repo_root) != rebuilt["source_hashes"]:
        raise ValueError("candidate sources changed during authentication")
    for name, reference in refs.items():
        maximum = None
        if revision == MULTIRES_REVISION:
            maximum = MULTIRES_METADATA_BYTES if name == "metadata" else MULTIRES_PROBE_BYTES if name == "probe" else None
        read_reference(reference, base, maximum=maximum)
    identity = {"profile": profile, "stage": display.stage, "resolution": resolution,
                "recipe_revision": display.recipe_revision, "base_sha256": sha(original),
                "candidate_sha256": sha(actual), "metadata_sha256": refs["metadata"]["sha256"],
                "probe_sha256": refs.get("probe", {}).get("sha256")}
    return {"identity": identity, "artifact_refs": refs,
            "candidate_path": str(candidate_path), "metadata_path": str(paths["metadata"]),
            "source_hashes": rebuilt["source_hashes"], "byte_rebuild_passed": True,
            "recipe_selection_scope": selection_scope, "preset_advertised": advertised,
            "runtime_evidence_verified": False}


def _replay_release(ref: Any, base: Path, context: dict) -> dict:
    # Both supported indexes contain only small reference envelopes. Parse the
    # schema through the bounded strict reader before either dispatch branch.
    from matrix_release_evidence import _json_reference, RELEASE_SCHEMA as CELL_RELEASE_SCHEMA
    path, _, release = _json_reference(ref, base, "release index")
    # The additive matrix schema reauthenticates through its public evaluator;
    # the outer candidate context cannot stand in for current source bytes.
    if release.get("schema") == CELL_RELEASE_SCHEMA:
        from matrix_release_evidence import evaluate_release_manifest
        result = evaluate_release_manifest(path)
        expected = context["identity"]
        measured = result.get("candidate_context", {})
        if result.get("cell_id") != f"{expected['profile']}/{expected['resolution']}":
            raise ValueError("matrix-cell release differs from the selected matrix cell")
        if (canonical(measured.get("artifact_refs")) != canonical(context["artifact_refs"])
                or canonical({key: measured.get("identity", {}).get(key) for key in expected}) != canonical(expected)
                or canonical(measured.get("source_hashes")) != canonical(context["source_hashes"])):
            raise ValueError("matrix-cell release rebinds the authenticated matrix candidate or source closure")
        _json_reference(ref, base, "release index recheck")
        return result
    if release.get("schema") != evidence.RELEASE_SCHEMA:
        raise ValueError("no production adapter exists for this release index schema")
    supplied = release.get("candidate")
    expected = context["artifact_refs"]
    if not isinstance(supplied, dict) or set(supplied) != set(expected):
        raise ValueError("release index candidate references differ from the matrix candidate")
    for name in expected:
        supplied_path, _ = read_reference(supplied[name], path.parent)
        if (str(supplied_path) != expected[name]["path"]
                or supplied[name]["sha256"].lower() != expected[name]["sha256"]):
            raise ValueError(f"release index rebinds the matrix candidate {name}")
    identity = context["identity"]
    if (identity["profile"], identity["resolution"], identity["stage"], identity["recipe_revision"]) != (
            "completehd", "1920x1080", evidence.STAGE, evidence.RECIPE_REVISION):
        raise ValueError("legacy complete-HD v1 acceptance supports only its exact Complete HD/1920x1080 recipe")
    result = evidence.evaluate_release_manifest(path, candidate_manifest=Path(context["metadata_path"]))
    measured = result.get("candidate_context", {}).get("identity")
    if measured != {key: value for key, value in identity.items() if key != "profile"}:
        raise ValueError("replayed release identity differs from the authenticated matrix candidate")
    read_reference(ref, base)
    return result


def evaluate_matrix(path: Path | None = None, *, repo_root: Path = ROOT) -> dict:
    """Return all required cells, including missing/unsupported failures; never write."""
    failures, matrix, cells, raw_sha, input_path = [], {}, {}, None, None
    try:
        manifest, cells = _inventory(repo_root)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, ImportError, OverflowError, RecursionError) as exc:
        failures.append(f"launcher inventory: {exc}")
        manifest = {}
        cells = {key: {"id": key, "profile": key.split("/")[0], "resolution": key.split("/")[1],
                      "preset_advertised": False, "recipe_eligible": False,
                      "source_recipe": None, "recipe_failures": [str(exc)]} for key in REQUIRED_IDS}
    rows = {}
    try:
        if path is None:
            raise ValueError("matrix manifest is missing; readiness inventory is not runtime acceptance")
        input_path = _plain_path(Path(path))
        raw = _json_bytes(input_path, "matrix index")
        raw_sha = sha(raw)
        matrix = json_object(raw, "matrix index")
        if matrix.get("schema") != MATRIX_SCHEMA or set(matrix) != {"schema", "rows"}:
            raise ValueError("matrix index requires only its supported schema and immutable rows")
        if not isinstance(matrix["rows"], list):
            raise ValueError("matrix rows must be a list")
        for row in matrix["rows"]:
            if not isinstance(row, dict) or set(row) != {"id", "candidate", "release_index"}:
                raise ValueError("matrix row requires only id, candidate and release_index")
            cell_id = row["id"]
            if not isinstance(cell_id, str) or cell_id not in REQUIRED_IDS:
                raise ValueError(f"unsupported matrix cell: {cell_id!r}; custom 802x602 remains experimental")
            if cell_id in rows:
                raise ValueError(f"duplicate matrix cell: {cell_id}")
            rows[cell_id] = row
        if set(rows) != set(REQUIRED_IDS):
            failures.append("matrix index must contain exactly all 36 required profile/preset cells")
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError) as exc:
        failures.append(str(exc))
        rows = {}
    missing_verifiers = [name for name in evidence.LANES if name not in evidence.LANE_VERIFIERS]
    for cell_id, cell in cells.items():
        errors = list(cell["recipe_failures"])
        if not cell["preset_advertised"]:
            errors.append("required preset is absent from this launcher profile")
        context, release_result = {}, None
        row = rows.get(cell_id)
        if row is None:
            errors.extend(("candidate immutable references are missing", "release index immutable reference is missing"))
        else:
            base = input_path.parent
            try:
                context = authenticate_candidate(cell_id, row["candidate"], base, manifest, repo_root=repo_root)
            except (OSError, ValueError, TypeError, KeyError, AttributeError, ImportError, OverflowError, RecursionError) as exc:
                errors.append(f"candidate authentication: {exc}")
            try:
                if not context:
                    from matrix_release_evidence import _json_reference
                    _json_reference(row["release_index"], base, "release index without candidate authority")
                    raise ValueError("release acceptance requires authenticated candidate bytes first")
                release_result = _replay_release(row["release_index"], base, context)
                if release_result.get("evidence_ready") is not True:
                    errors.extend(f"release acceptance: {item}" for item in release_result.get("failures", []))
                    errors.append("release acceptance did not affirmatively establish every production lane")
            except (OSError, ValueError, TypeError, KeyError, AttributeError, ImportError, OverflowError, RecursionError) as exc:
                errors.append(f"release acceptance: {exc}")
        errors.extend(f"production lane verifier is not implemented: {name}" for name in missing_verifiers)
        errors.append("candidate-bound expanded-battle production acceptance verifier is not implemented")
        cell.update(candidate_authentication_passed=bool(context), candidate_context=context,
                    release_evaluation=release_result, required_acceptance=list(REQUIRED_ACCEPTANCE),
                    runtime_evidence_verified=False, passed=False, failures=list(dict.fromkeys(errors)))
        failures.extend(f"{cell_id}: {item}" for item in cell["failures"])
    if input_path is not None and raw_sha is not None:
        try:
            if sha(_json_bytes(input_path, "matrix index recheck")) != raw_sha:
                raise ValueError("matrix index changed during evaluation")
        except (OSError, ValueError) as exc:
            failures.append(str(exc))
    return {"schema": "resolution_release_matrix_readiness_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(), "runtime_policy": RUNTIME_POLICY,
            "evaluation_scope": "all_four_profiles_nine_presets_complete_release_readiness",
            "matrix_manifest": str(input_path) if input_path else None, "matrix_manifest_sha256": raw_sha,
            "required_cell_count": len(REQUIRED_IDS), "required_cells": list(REQUIRED_IDS), "cells": cells,
            "advertised_preset_count": sum(cell["preset_advertised"] for cell in cells.values()),
            "authenticated_candidate_count": sum(cell["candidate_authentication_passed"] for cell in cells.values()),
            "custom_regression_resolution": CUSTOM_REGRESSION, "custom_resolutions_promoted": False,
            "unimplemented_lane_verifiers": missing_verifiers,
            "matrix_context_lane_verifiers": list(MATRIX_CONTEXT_LANE_VERIFIERS),
            "matrix_context_unimplemented_lane_verifiers": list(MATRIX_CONTEXT_UNIMPLEMENTED_LANES),
            "unimplemented_acceptance_requirements": ["candidate_bound_expanded_battle"],
            "passed": False, "evidence_ready": False, "promotion_approved": False, "promotion_ready": False,
            "stable_stage_should_change": False, "checklist_updated": None, "full_game_complete": False,
            "failures": failures}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-manifest", type=Path, help="Immutable 36-cell index; omission reports missing readiness")
    parser.add_argument("--write-json", type=Path, help="Optional fresh report; stdout only by default")
    args = parser.parse_args(argv)
    report = evaluate_matrix(args.matrix_manifest)
    if args.write_json is not None:
        try:
            target = _plain_path(args.write_json)
            if args.matrix_manifest is not None and target == _plain_path(args.matrix_manifest):
                raise ValueError("evaluation output cannot replace its input")
            # No directory creation or replacement of earlier artifacts.
            with target.open("x", encoding="utf-8") as output:
                output.write(json.dumps(report, indent=2) + "\n")
        except (OSError, ValueError) as exc:
            print(f"cannot write fresh matrix evaluation: {exc}", file=sys.stderr)
            return 2
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
