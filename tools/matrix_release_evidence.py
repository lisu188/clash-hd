#!/usr/bin/env python3
"""Source-bound matrix-cell context, not runtime or complete release proof.

The public evaluator always rebuilds the candidate through the production
matrix authenticator and rereads the actual launcher catalog. Only the existing
resolution-coverage requirement has a matrix-context replay. All fifteen runtime
lanes, installed expanded battle and promotion remain explicit failures.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import complete_hd_evidence as evidence
import resolution_release_matrix as matrix


RELEASE_SCHEMA = "matrix_cell_release_manifest_v1"
LANE_SCHEMA = "matrix_cell_lane_evidence_v1"
REQUIRED_LANES = tuple(evidence.LANES)
UNIMPLEMENTED_LANES = tuple(name for name in REQUIRED_LANES if name != "resolution_coverage")
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_CANDIDATE_BYTES = 32 * 1024 * 1024
PRODUCER = "tools/matrix_release_evidence.py"
_RELEASE_KEYS = {"schema", "cell_id", "candidate", "launcher_manifest", "lanes"}
_COVERAGE_KEYS = {"schema", "lane", "identity", "evidence_class", "producer", "source_artifacts",
                  "checks", "passed", "failures", "stable_stage_should_change", "release_resolutions"}


def _same(left: Any, right: Any) -> bool:
    """JSON types, including true/1 and 1/1.0, must not alias."""
    return matrix.canonical(left) == matrix.canonical(right)


def _file_bytes(path: Path, label: str, *, maximum: int = MAX_JSON_BYTES) -> tuple[Path, bytes]:
    target = matrix._plain_path(path)
    with target.open("rb") as source:
        raw = source.read(maximum + 1)
    if not raw or len(raw) > maximum:
        raise ValueError(f"{label} must contain bounded nonempty bytes")
    return target, raw


def _json_file(path: Path, label: str) -> tuple[Path, bytes, dict]:
    target, raw = _file_bytes(path, label)
    value = evidence.parse_evidence_json(raw, label)
    if type(value) is not dict:
        raise ValueError(f"{label} must be an object")
    return target, raw, value


def _reference_bytes(ref: Any, base: Path, label: str,
                     *, maximum: int = MAX_JSON_BYTES) -> tuple[Path, bytes]:
    if (type(ref) is not dict or set(ref) != {"path", "sha256"}
            or not evidence._text(ref.get("path")) or type(ref.get("sha256")) is not str
            or not evidence.SHA_RE.fullmatch(ref["sha256"])):
        raise ValueError(f"{label} requires only a path and SHA-256 reference")
    given = Path(ref["path"])
    path, raw = _file_bytes(given if given.is_absolute() else base / given, label, maximum=maximum)
    if matrix.sha(raw) != ref["sha256"].lower():
        raise ValueError(f"{label} artifact SHA-256 mismatch: {path}")
    return path, raw


def _json_reference(ref: Any, base: Path, label: str) -> tuple[Path, bytes, dict]:
    path, raw = _reference_bytes(ref, base, label)
    value = evidence.parse_evidence_json(raw, label)
    if type(value) is not dict:
        raise ValueError(f"{label} must be an object")
    return path, raw, value


def _coverage_checks(context: dict, manifest: dict) -> dict:
    from src.launcher import presets
    identity = context["identity"]
    profile, resolution = identity["profile"], identity["resolution"]
    config = manifest["profiles"][profile]
    features = {"minimap_viewport": profile != "classic"}
    try:
        selected = presets.resolve_plan(renderer=profile, resolution=resolution, manifest=manifest)
    except ValueError:
        selected = None
    advertised = resolution in config["resolutions"]
    selection_matches = (
        advertised and selected is not None and context["recipe_selection_scope"] == "launcher_resolved_recipe"
        and selected.stage == identity["stage"] and selected.recipe_revision == identity["recipe_revision"]
        and _same(config["features"], features) and _same(identity["features"], features)
        and type(selected.minimap_viewport) is bool and selected.minimap_viewport == features["minimap_viewport"]
    )
    stable_policy = (
        manifest["default_renderer"] == "classic" and manifest["default"] == "800x600"
        and manifest["stable_stage"] == evidence.STABLE_STAGE
        and manifest["profiles"]["classic"]["stage"] == evidence.STABLE_STAGE
        and _same(manifest["resolutions"], manifest["profiles"]["classic"]["resolutions"])
        and manifest["resolutions"]["800x600"]["status"] == "stable"
        and all(config["default"] == "800x600"
                and _same(config["features"], {"minimap_viewport": name != "classic"})
                and all(row["status"] == ("stable" if name == "classic" and key == "800x600" else "experimental")
                        for key, row in config["resolutions"].items())
                for name, config in manifest["profiles"].items())
    )
    values = {
        "patcher_constraints": context.get("byte_rebuild_passed") is True,
        "candidate_byte_gate": context.get("byte_rebuild_passed") is True,
        "advertised_resolution_matches": selection_matches,
        "other_resolutions_not_promoted": stable_policy,
    }
    return {name: {"passed": passed, "failures": [] if passed else [name]} for name, passed in values.items()}


def _lane(name: str, ref: Any, base: Path, context: dict, manifest: dict,
          launcher_ref: dict, retained_refs: list[tuple[dict, Path]]) -> dict:
    failures, report, measured, report_path = [], {}, {}, None
    implemented = name == "resolution_coverage"
    if not implemented:
        failures.append(f"matrix-context source-artifact verifier is not implemented for {name}")
    try:
        report_path, _, report = _json_reference(ref, base, f"{name} lane")
        retained_refs.append((ref, base))
        if report.get("schema") != LANE_SCHEMA or report.get("lane") != name:
            failures.append("lane schema/name does not identify the selected matrix-cell requirement")
        if not context or not _same(report.get("identity"), context["identity"]):
            failures.append("lane identity differs from the freshly authenticated matrix cell")
        if implemented:
            if set(report) != _COVERAGE_KEYS:
                failures.append("resolution lane requires only the fixed source-coverage envelope")
            if report.get("evidence_class") != "repo_resolution_coverage":
                failures.append("resolution lane requires repo_resolution_coverage")
            if report.get("passed") is not True or report.get("failures") != []:
                failures.append("resolution lane is not an affirmative source-coverage report")
            if report.get("stable_stage_should_change") is not False:
                failures.append("resolution lane must preserve the protected stable stage")
            if not context:
                raise ValueError("resolution coverage requires freshly authenticated candidate bytes")
            if report.get("release_resolutions") != [context["identity"]["resolution"]]:
                failures.append("coverage must identify exactly this candidate's resolution")
            producer_path, _ = _reference_bytes(report.get("producer"), report_path.parent, "resolution producer source")
            retained_refs.append((report["producer"], report_path.parent))
            if producer_path != (matrix.ROOT / PRODUCER).resolve():
                failures.append("resolution lane requires the fixed matrix release verifier")
            sources = report.get("source_artifacts")
            if type(sources) is not list or len(sources) != 1:
                failures.append("resolution lane requires exactly the actual pinned launcher manifest")
            else:
                source_path, _, _ = _json_reference(sources[0], report_path.parent, "launcher source")
                retained_refs.append((sources[0], report_path.parent))
                if str(source_path) != launcher_ref["path"] or sources[0]["sha256"].lower() != launcher_ref["sha256"]:
                    failures.append("resolution lane source is not the actual pinned launcher manifest")
            measured = _coverage_checks(context, manifest)
            if not _same(report.get("checks"), measured):
                failures.append("claimed resolution checks differ from source-artifact replay")
            failures.extend(f"source-artifact check failed: {key}" for key, value in measured.items() if not value["passed"])
    except (OSError, ValueError, TypeError, KeyError, AttributeError, ImportError, OverflowError, RecursionError) as exc:
        failures.append(f"{type(exc).__name__}: {exc}")
    return {"lane": name, "implemented": implemented, "passed": not failures,
            "report_path": str(report_path) if report_path else None,
            "report_sha256": ref.get("sha256") if type(ref) is dict else None,
            "required_checks": list(evidence.LANES[name][1]), "checks": measured,
            "runtime_evidence_verified": False, "failures": failures}


def evaluate_release_manifest(path: Path) -> dict:
    """Reauthenticate one exact cell with no supplied context or verifier policy."""
    failures, context, manifest, release, retained_refs = [], {}, {}, {}, []
    release_path, release_raw, launcher_path, launcher_raw, launcher_ref = None, None, None, None, {}
    cell_id = None
    try:
        release_path, release_raw, release = _json_file(Path(path), "matrix-cell release")
        if release.get("schema") != RELEASE_SCHEMA or set(release) != _RELEASE_KEYS:
            raise ValueError("matrix-cell release requires only its fixed schema, cell_id, candidate, launcher_manifest and lanes")
        cell_id = release["cell_id"]
        if type(cell_id) is not str or cell_id not in matrix.REQUIRED_IDS:
            raise ValueError("release cell_id must identify one exact required profile/preset")
        # Pin the real catalog before inventory or reconstruction, then compare
        # both consumers and reread it after every source-artifact lane.
        launcher_path, launcher_raw, parsed = _json_file(matrix.ROOT / "src/launcher/resolutions.json", "actual launcher manifest")
        manifest, _ = matrix._inventory(matrix.ROOT)
        if not _same(parsed, manifest):
            raise ValueError("actual launcher manifest changed during inventory")
        selected_path, _, _ = _json_reference(release["launcher_manifest"], release_path.parent, "launcher manifest")
        launcher_ref = {"path": str(launcher_path), "sha256": matrix.sha(launcher_raw)}
        if selected_path != launcher_path or release["launcher_manifest"]["sha256"].lower() != launcher_ref["sha256"]:
            raise ValueError("release must pin the actual current repository launcher manifest")
        retained_refs.append((release["launcher_manifest"], release_path.parent))
        context = matrix.authenticate_candidate(cell_id, release["candidate"], release_path.parent, manifest,
                                                repo_root=matrix.ROOT)
        profile = context["identity"]["profile"]
        context["identity"] = {**context["identity"], "cell_id": cell_id,
                               "features": dict(manifest["profiles"][profile]["features"]),
                               "launcher_manifest_sha256": launcher_ref["sha256"],
                               "source_closure_sha256": matrix.sha(matrix.canonical(context["source_hashes"]).encode("utf-8"))}
    except (OSError, ValueError, TypeError, KeyError, AttributeError, ImportError, OverflowError, RecursionError) as exc:
        context = {}
        failures.append(f"source context: {type(exc).__name__}: {exc}")
    refs = release.get("lanes")
    if type(refs) is not dict or set(refs) != set(REQUIRED_LANES):
        failures.append("matrix-cell release must contain exactly all 16 fixed acceptance lanes")
    refs = refs if type(refs) is dict else {}
    lanes = {name: _lane(name, refs.get(name), release_path.parent if release_path else Path("."),
                         context, manifest, launcher_ref, retained_refs) for name in REQUIRED_LANES}
    failures.extend(f"{name}: {item}" for name, result in lanes.items() for item in result["failures"])
    # All references and source pins are checked again. This detects observed
    # changes, not immutable files, a native producer or an atomic filesystem.
    final_failures = []
    try:
        if release_path is not None and _json_file(release_path, "matrix-cell release recheck")[1] != release_raw:
            raise ValueError("matrix-cell release changed during evaluation")
        if launcher_path is not None and _json_file(launcher_path, "launcher manifest recheck")[1] != launcher_raw:
            raise ValueError("actual launcher manifest changed during evaluation")
        for ref, base in retained_refs:
            _reference_bytes(ref, base, "retained source-artifact recheck")
        if context:
            for name, ref in context["artifact_refs"].items():
                maximum = MAX_CANDIDATE_BYTES if name in ("base_executable", "executable") else MAX_JSON_BYTES
                _reference_bytes(ref, Path("."), "candidate artifact recheck", maximum=maximum)
            for name, digest in context["source_hashes"].items():
                source = matrix._plain_path(matrix.ROOT / name)
                if not source.is_relative_to(matrix.ROOT.resolve()):
                    raise ValueError("candidate source closure escapes the fixed repository")
                _reference_bytes({"path": str(source), "sha256": digest}, Path("."), "candidate source closure recheck")
    except (OSError, ValueError, TypeError, KeyError, AttributeError, ImportError, OverflowError, RecursionError) as exc:
        final_failures.append(f"source recheck: {type(exc).__name__}: {exc}")
    if final_failures:
        lanes["resolution_coverage"]["passed"] = False
        lanes["resolution_coverage"]["failures"].extend(final_failures)
        failures.extend(final_failures)
    failures.append("candidate-bound installed expanded-battle acceptance verifier is not implemented")
    return {"schema": "matrix_cell_release_evaluation_v1", "evaluation_scope": "source_bound_matrix_cell_context_only",
            "runtime_policy": matrix.RUNTIME_POLICY, "cell_id": cell_id,
            "release_manifest": str(release_path) if release_path else None,
            "release_manifest_sha256": matrix.sha(release_raw) if release_raw is not None else None,
            "launcher_manifest": launcher_ref, "candidate_context": context,
            "candidate_authentication_passed": bool(context) and not final_failures,
            "required_lanes": list(REQUIRED_LANES), "lanes": lanes,
            "unimplemented_lane_verifiers": list(UNIMPLEMENTED_LANES),
            "unimplemented_acceptance_requirements": ["candidate_bound_expanded_battle"],
            "source_consistency_passed": bool(context) and not final_failures,
            "runtime_evidence_verified": False, "whole_hd_acceptance_evaluated": False,
            "passed": False, "evidence_ready": False, "eligible_for_stable_promotion": False,
            "promotion_approved": False, "promotion_ready": False, "full_game_complete": False,
            "stable_stage_should_change": False, "checklist_updated": None, "failures": failures}
