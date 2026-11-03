#!/usr/bin/env python3
"""Prepare/authenticate the selected twelve cells without promoting a release.

The full 36-cell release policy is unchanged. This tool rebuilds candidate
bytes, metadata and the canonical probe; pending runtime lanes never pass on
the strength of a source report or a user-supplied boolean.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "src/launcher")]
from src.patcher import hd_multires_candidate as candidate
import complete_hd_evidence as policy
import presets

SCHEMA = "hd_multires_candidate_bundle_v1"
QUALIFICATION_SCHEMA = "hd_multires_selected_qualification_v1"
SELECTED_IDS = tuple(f"{p}/{r}" for r in candidate.RESOLUTIONS for p in candidate.PROFILES)
MAX_BYTES = {"base_executable": 16 * 1024 * 1024, "executable": 16 * 1024 * 1024,
             "metadata": 16 * 1024 * 1024, "probe": 64 * 1024 * 1024}
ARTIFACT_NAMES = tuple(MAX_BYTES)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(value) -> bytes:
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf-8")


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def plain_path(path: Path, *, existing: bool = True) -> Path:
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            if existing and part == path:
                raise
            continue
        if (stat.S_ISLNK(info.st_mode) or getattr(part, "is_junction", lambda: False)()
                or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise ValueError("artifact paths must not follow links or reparse points")
    if existing and (not path.is_file() or path.stat().st_nlink != 1):
        raise ValueError("artifact must be one regular non-linked file")
    return path


def read_file(path: Path, maximum: int) -> bytes:
    path = plain_path(path)
    before = path.stat()
    if before.st_size > maximum:
        raise ValueError("artifact exceeds its bounded size")
    data = path.read_bytes()
    after = path.stat()
    if len(data) > maximum or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("artifact changed during read")
    return data


def read_json(path: Path, maximum=2 * 1024 * 1024):
    return policy.parse_evidence_json(read_file(path, maximum), "HD multiresolution artifact")


def reference(path: Path) -> dict:
    path = plain_path(path)
    return dict(path=str(path), sha256=sha(path.read_bytes()))


def _reference(ref, base: Path, maximum: int) -> tuple[Path, bytes]:
    if (type(ref) is not dict or set(ref) != {"path", "sha256"}
            or type(ref["path"]) is not str or not ref["path"]
            or type(ref["sha256"]) is not str or not policy.SHA_RE.fullmatch(ref["sha256"])):
        raise ValueError("immutable path/SHA-256 artifact reference required")
    path = plain_path(base / ref["path"])
    data = read_file(path, maximum)
    if sha(data) != ref["sha256"].lower():
        raise ValueError("artifact SHA-256 differs: " + str(path))
    return path, data


def _selected(cell_id):
    if type(cell_id) is not str or cell_id not in SELECTED_IDS:
        raise ValueError("select one of the twelve exact profile/resolution cells")
    return cell_id.split("/")


def _authenticate_bundle(path: Path, rebuild, expected_original_sha: str) -> dict:
    path = plain_path(path)
    bundle_raw = read_file(path, 2 * 1024 * 1024)
    bundle = policy.parse_evidence_json(bundle_raw, "HD bundle")
    if type(bundle) is not dict or set(bundle) != {"schema", "cell_id", "artifacts"} or bundle["schema"] != SCHEMA:
        raise ValueError("fixed HD candidate bundle schema required")
    profile, resolution = _selected(bundle["cell_id"])
    artifacts = bundle["artifacts"]
    if type(artifacts) is not dict or set(artifacts) != set(ARTIFACT_NAMES):
        raise ValueError("exact original/executable/metadata/probe inventory required")
    loaded = {name: _reference(artifacts[name], path.parent, MAX_BYTES[name]) for name in ARTIFACT_NAMES}
    if len({p for p, _ in loaded.values()}) != len(loaded):
        raise ValueError("candidate artifacts must be distinct files")
    original = loaded["base_executable"][1]
    if sha(original) != expected_original_sha:
        raise ValueError("unknown original executable SHA-256")
    catalog_path = ROOT / "src/launcher/resolutions.json"
    catalog_raw = read_file(catalog_path, 2 * 1024 * 1024)
    catalog = policy.parse_evidence_json(catalog_raw, "actual launcher catalog")
    presets.validate_manifest(catalog)
    display = presets.resolve_plan(renderer=profile, resolution=resolution, manifest=catalog)
    image, metadata, probe = rebuild(original, resolution, profile=profile)
    recorded = policy.parse_evidence_json(loaded["metadata"][1], "candidate metadata")
    if (loaded["executable"][1] != image or canonical(recorded) != canonical(metadata)
            or loaded["probe"][1] != probe.encode("utf-8")):
        raise ValueError("candidate bundle differs from the independently reconstructed recipe")
    if (metadata["stage"] != display.stage or metadata["recipe_revision"] != display.recipe_revision
            or metadata["bounded_small_world_integrated"] is not display.bounded_world_renderer):
        raise ValueError("launcher plan and reconstructed candidate differ")
    for name, expected in metadata["source_hashes"].items():
        source_path = plain_path(ROOT / name)
        if not source_path.is_relative_to(ROOT) or sha(source_path.read_bytes()) != expected:
            raise ValueError("candidate source identity changed")
    # Recheck the actual input references/catalog, not a copy of their claims.
    for name in ARTIFACT_NAMES:
        if _reference(artifacts[name], path.parent, MAX_BYTES[name])[1] != loaded[name][1]:
            raise ValueError("candidate artifact changed during authentication")
    if read_file(path, 2 * 1024 * 1024) != bundle_raw or read_file(catalog_path, 2 * 1024 * 1024) != catalog_raw:
        raise ValueError("bundle or actual launcher catalog changed during authentication")
    identity = dict(cell_id=bundle["cell_id"], profile=profile, resolution=resolution,
        stage=metadata["stage"], recipe_revision=metadata["recipe_revision"],
        base_sha256=expected_original_sha, candidate_sha256=sha(image),
        probe_sha256=sha(probe.encode()), source_closure_sha256=sha(canonical(metadata["source_hashes"])),
        launcher_manifest_sha256=sha(catalog_raw))
    return dict(identity=identity, artifacts=artifacts, source_hashes=metadata["source_hashes"],
        source_authentication_passed=True, bounded_small_world_installed=metadata["bounded_small_world_integrated"],
        expanded_battle_installed=metadata["expanded_battle_installed"],
        runtime_evidence_verified=False, manual_input_proof=False, promotion_ready=False)


def _bind_authenticator():
    """Retain a raw canonical issuer, never a replaceable public producer."""
    path = ROOT / "src/patcher/hd_multires_issuer.py"
    raw = read_file(path, 4 * 1024 * 1024)
    values = {"__file__": str(path), "__name__": "_clash95_selected_qualification_issuer", "__package__": None}
    exec(compile(raw, str(path), "exec"), values)
    build, _ = values["create_issuer"]()
    implement = _authenticate_bundle
    original_sha = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"

    def authenticate_bundle(path):
        return implement(path, build, original_sha)

    return authenticate_bundle


authenticate_bundle = _bind_authenticator()


def selected_report(bundles: list[Path]) -> dict:
    by_id, failures = {}, []
    for path in bundles:
        try:
            context = authenticate_bundle(path)
            cell_id = context["identity"]["cell_id"]
            if cell_id in by_id:
                raise ValueError("duplicate selected cell: " + cell_id)
            by_id[cell_id] = context
        except (OSError, ValueError, KeyError, TypeError, ImportError) as error:
            failures.append(str(path) + ": " + str(error))
    rows = []
    for cell_id in SELECTED_IDS:
        context = by_id.get(cell_id)
        rows.append(dict(cell_id=cell_id, candidate_context=context,
            source_authentication_passed=bool(context),
            lanes={name: dict(passed=False, status="pending", required_checks=list(checks),
                              reason="fresh candidate-bound native evidence/verifier is required")
                   for name, (_, checks) in policy.LANES.items() if name != "resolution_coverage"}
                  | {"resolution_coverage": dict(passed=bool(context),
                         status="source_authenticated" if context else "missing_candidate")},
            candidate_bound_expanded_battle_passed=False, qualification_passed=False))
    return dict(schema=QUALIFICATION_SCHEMA, required_cell_ids=list(SELECTED_IDS), cells=rows,
        authenticated_cells=len(by_id), accepted_cells=0, full_release_cell_count=36,
        measured_endurance_seconds_per_cell=sum(seconds for _, _, seconds in policy.SHORT_STEPS)+14400,
        runtime_evidence_verified=False, manual_input_proof=False, promotion_ready=False,
        full_game_complete=False, stable_stage_should_change=False, failures=failures,
        limitation="This selected report authenticates construction only; fifteen native acceptance lanes and expanded battle remain pending.")


def _write_new(path: Path, data: bytes):
    path = plain_path(path, existing=False)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _reserve(path: Path, pending: int):
    for ancestor in (path, *path.parents):
        if ancestor.exists():
            usage = shutil.disk_usage(ancestor)
            if (usage.free - pending) * 10 <= usage.total:
                raise ValueError("more than ten percent free space must remain after the full bundle write")
            return
    raise ValueError("output volume unavailable")


def prepare_bundle(original_path: Path, output_root: Path, cell_id: str) -> Path:
    profile, resolution = _selected(cell_id)
    original_path = plain_path(original_path)
    output_root = plain_path(output_root, existing=False)
    permitted = Path("C:/ClashTests").resolve()
    if os.name != "nt" or not output_root.is_relative_to(permitted) or output_root.is_relative_to(ROOT):
        raise ValueError("candidate output must be outside the checkout under C:/ClashTests")
    target = output_root / profile / resolution
    paths = {"executable": target / "clash95_hd.exe", "metadata": target / "candidate.json",
             "probe": target / "candidate.cdb"}
    manifest = target / "bundle.json"
    if any(p.exists() for p in (*paths.values(), manifest)):
        raise FileExistsError("candidate bundle destination exists; choose a fresh output root")
    _reserve(output_root, 128 * 1024 * 1024)
    original = read_file(original_path, MAX_BYTES["base_executable"])
    image, metadata, probe = candidate.build_candidate(original, resolution, profile=profile)
    payloads = {"executable": image, "metadata": encode(metadata), "probe": probe.encode()}
    _reserve(output_root, sum(map(len, payloads.values())) + 1024 * 1024)
    if read_file(original_path, MAX_BYTES["base_executable"]) != original:
        raise ValueError("original changed during candidate preparation")
    target.mkdir(parents=True, exist_ok=False)
    for name, data in payloads.items():
        _write_new(paths[name], data)
    refs = {"base_executable": reference(original_path), **{name: reference(p) for name, p in paths.items()}}
    _write_new(manifest, encode(dict(schema=SCHEMA, cell_id=cell_id, artifacts=refs)))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--original", type=Path, default=Path("C:/Clash/clash95.exe"))
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--cell", action="append", choices=SELECTED_IDS)
    parser.add_argument("--bundle", type=Path, action="append", default=[])
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    bundles = list(args.bundle)
    if args.prepare:
        if args.output_root is None:
            parser.error("--prepare requires --output-root")
        for cell_id in args.cell or SELECTED_IDS:
            manifest = prepare_bundle(args.original, args.output_root, cell_id)
            bundles.append(manifest)
            print(json.dumps(dict(prepared=cell_id, bundle=str(manifest))), flush=True)
    elif args.output_root or args.cell:
        parser.error("--output-root/--cell require --prepare")
    report = selected_report(bundles)
    if args.report:
        _write_new(args.report, encode(report))
    print(json.dumps({k: v for k, v in report.items() if k != "cells"}, indent=2))
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
