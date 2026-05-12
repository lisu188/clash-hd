#!/usr/bin/env python3
"""Build and validate the searchable Codex Cloud fixture bundle.

The fixture tree gives cloud agents enough static context and archived runtime
evidence to reason about the Clash95 HD work without cloning proprietary game
binaries or needing local Windows debugger tools.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "cloud" / "fixtures" / "manifest.json"
FIXTURE_ROOT = ROOT / "cloud" / "fixtures"

BLOCKED_EXTENSIONS = {
    ".7z",
    ".bin",
    ".dll",
    ".dmp",
    ".exe",
    ".iso",
    ".lib",
    ".obj",
    ".pdb",
    ".rar",
    ".raw",
    ".sav",
}
BLOCKED_PATH_PARTS = {
    ".git",
    "crack",
    "ddraw-proxy-build",
    "keygen",
    "selected_decompilation.c",
    "system32",
    "syswow64",
}
TEXT_EXTENSIONS = {".cdb", ".csv", ".json", ".md", ".txt"}
USER_PATH_RE = re.compile(r"C:[\\/]+Users[\\/]+[^\\/\s\"']+", re.IGNORECASE)


def repo_file(path: str, target: str, reason: str) -> dict[str, Any]:
    return {"source": f"repo:{path}", "target": target, "reason": reason}


def repo_json_key(path: str, target: str, key: str, reason: str) -> dict[str, Any]:
    return {**repo_file(path, target, reason), "json_key": key}


def external_file(path: str, target: str, reason: str) -> dict[str, Any]:
    return {"source": f"external:{path}", "target": target, "reason": reason}


def run_files(run: str, target_prefix: str, names: list[str], reason: str) -> list[dict[str, Any]]:
    return [
        repo_file(f"captures/{run}/{name}", f"{target_prefix}/{run}/{name}", reason)
        for name in names
    ]


def default_entries() -> list[dict[str, Any]]:
    normal = "cdb-surface-dump-20260506-190037"
    forced = "cdb-surface-dump-20260506-201114"
    castle = "cdb-surface-dump-20260512-082418"
    hd_run_files = [
        "RUN-SUMMARY.md",
        "cdb-surface-dump.log",
        "map-tile-coverage.json",
        "map-tile-coverage.txt",
        "summary.json",
        "surface.png",
        "surface.png.json",
        "visibility-coverage-summary.json",
        "visibility-coverage.txt",
    ]
    entries = [
        external_file(
            "C:/Clash/reverse/ghidra-out/README.md",
            "ghidra-out/README.md",
            "Notes for the lightweight Ghidra export.",
        ),
        external_file(
            "C:/Clash/reverse/ghidra-out/metadata.txt",
            "ghidra-out/metadata.txt",
            "Image base, language, entry points, and memory blocks.",
        ),
        external_file(
            "C:/Clash/reverse/ghidra-out/imports.csv",
            "ghidra-out/imports.csv",
            "Imported Win32, DirectX, AVI, and audio symbols.",
        ),
        external_file(
            "C:/Clash/reverse/ghidra-out/functions.csv",
            "ghidra-out/functions.csv",
            "Function inventory after map-name application.",
        ),
        repo_json_key(
            "captures/hd-map-smoke-current.json",
            "evidence/hd-map/patch-stage-report.json",
            "patch_stage",
            "Archived current HD map patch-byte report for cloud smoke checks.",
        ),
        repo_file(
            "captures/hd-map-evidence-current.md",
            "evidence/hd-map/hd-map-evidence-current.md",
            "Current human-readable evidence index.",
        ),
        repo_file(
            "captures/hd-map-evidence-current-check.json",
            "evidence/hd-map/hd-map-evidence-current-check.json",
            "Evidence-index link check result.",
        ),
        repo_file(
            "captures/hd-map-smoke-current.json",
            "evidence/hd-map/hd-map-smoke-current.json",
            "Current HD map smoke matrix output.",
        ),
        repo_file(
            "captures/hd-map-smoke-current.md",
            "evidence/hd-map/hd-map-smoke-current.md",
            "Current HD map smoke matrix summary.",
        ),
        repo_file(
            "captures/post-owner-evidence-current.json",
            "evidence/hd-map/post-owner-evidence-current.json",
            "Paired normal/forced-visible post-owner evidence matrix.",
        ),
        repo_file(
            "captures/post-owner-evidence-current.md",
            "evidence/hd-map/post-owner-evidence-current.md",
            "Readable paired post-owner evidence matrix.",
        ),
        repo_file(
            "captures/patch-manifest-compare-current-vs-partial12.json",
            "evidence/hd-map/patch-manifest-compare-current-vs-partial12.json",
            "Current-vs-partial12 patch manifest comparison.",
        ),
        repo_file(
            "captures/patch-manifest-compare-current-vs-partial12.md",
            "evidence/hd-map/patch-manifest-compare-current-vs-partial12.md",
            "Readable current-vs-partial12 patch manifest comparison.",
        ),
    ]
    entries.extend(run_files(normal, "evidence/hd-map/runs", hd_run_files, "Normal post-owner visibility-zero proof."))
    entries.extend(
        run_files(
            normal,
            "evidence/hd-map/runs",
            [
                "POST-OWNER-TILE-VISIBILITY.md",
                "post-owner-tile-visibility-action-summary.json",
                "post-owner-ui-bounds.json",
            ],
            "Focused normal post-owner tile visibility details.",
        )
    )
    entries.extend(run_files(forced, "evidence/hd-map/runs", hd_run_files, "Seven-cell forced-visible proof."))
    entries.extend(
        run_files(
            forced,
            "evidence/hd-map/runs",
            [
                "post-owner-forced-visible-summary.json",
                "post-owner-forced-visible-summary.txt",
            ],
            "Focused seven-cell forced-visible proof details.",
        )
    )
    entries.extend(
        run_files(
            castle,
            "evidence/castle-barracks-centered/runs",
            [
                "RUN-SUMMARY.md",
                "castle-barracks-action-click-summary.json",
                "castle-barracks-action-click-summary.md",
                "castle-ui-center-geometry.json",
                "cdb-surface-dump.log",
                "map-tile-coverage.txt",
                "patch-stage-report.json",
                "summary.json",
                "surface.png",
                "surface.png.json",
                "visibility-coverage.txt",
            ],
            "Current castle/barracks centered UI proof.",
        )
    )
    return sorted(entries, key=lambda row: row["target"])


def default_source_repo() -> Path:
    env = os.environ.get("CLASH_HD_SOURCE_REPO")
    if env:
        return Path(env)
    sibling = ROOT.parent / "clash-hd"
    if sibling.exists() and sibling != ROOT:
        return sibling
    return ROOT


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def sanitize_text(text: str, source_repo: Path) -> str:
    replacements = {
        str(source_repo): "<SOURCE_REPO>",
        str(source_repo).replace("\\", "/"): "<SOURCE_REPO>",
        str(ROOT): "<CLOUD_WORKTREE>",
        str(ROOT).replace("\\", "/"): "<CLOUD_WORKTREE>",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(
        r"C:[\\/]+Users[\\/]+[^\\/]+[\\/]+OneDrive[\\/]+Pulpit[\\/]+git[\\/]+clash-hd",
        "<SOURCE_REPO>",
        text,
        flags=re.IGNORECASE,
    )
    text = USER_PATH_RE.sub("<USER_HOME>", text)
    return text


def has_blocked_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    parts = {part for part in normalized.split("/") if part}
    return any(part in normalized or part in parts for part in BLOCKED_PATH_PARTS)


def validate_entry_paths(entry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    target = str(entry.get("target") or "")
    source = str(entry.get("source") or "")
    suffix = Path(target).suffix.lower()
    if suffix in BLOCKED_EXTENSIONS:
        errors.append(f"blocked target extension for {target}")
    if has_blocked_path(target):
        errors.append(f"blocked target path for {target}")
    if source.lower().endswith(tuple(BLOCKED_EXTENSIONS)):
        errors.append(f"blocked source extension for {source}")
    if has_blocked_path(source):
        errors.append(f"blocked source path for {source}")
    return errors


def resolve_source(source: str, source_repo: Path) -> Path:
    if source.startswith("repo:"):
        return source_repo / source[len("repo:") :]
    if source.startswith("external:"):
        return Path(source[len("external:") :])
    raise ValueError(f"unsupported source prefix: {source}")


def target_path(target: str) -> Path:
    path = FIXTURE_ROOT / target
    resolved = path.resolve()
    if FIXTURE_ROOT.resolve() not in (resolved, *resolved.parents):
        raise ValueError(f"target escapes fixture root: {target}")
    return path


def copy_entry(entry: dict[str, Any], source_repo: Path) -> dict[str, Any]:
    source = resolve_source(str(entry["source"]), source_repo)
    target = target_path(str(entry["target"]))
    if not source.is_file():
        raise FileNotFoundError(f"missing fixture source: {entry['source']} -> {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    source_data = source.read_bytes()
    source_sha = sha256_bytes(source_data)
    if entry.get("json_key"):
        data = json.loads(source_data.decode("utf-8-sig"))
        for key in str(entry["json_key"]).split("."):
            data = data[key]
        text = json.dumps(data, indent=2) + "\n"
        target.write_text(sanitize_text(text, source_repo), encoding="utf-8", newline="\n")
    elif is_text_file(target):
        text = source_data.decode("utf-8-sig", errors="replace")
        target.write_text(sanitize_text(text, source_repo), encoding="utf-8", newline="\n")
    else:
        target.write_bytes(source_data)
    return {
        **entry,
        "source_sha256": source_sha,
        "sha256": sha256_file(target),
        "bytes": target.stat().st_size,
    }


def load_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(path: Path, entries: list[dict[str, Any]]) -> None:
    manifest = {
        "manifest_version": 1,
        "description": "Searchable Codex Cloud fixture bundle for Clash95 HD repo-only work.",
        "policy": {
            "blocked_extensions": sorted(BLOCKED_EXTENSIONS),
            "blocked_path_parts": sorted(BLOCKED_PATH_PARTS),
            "content_user_paths": "forbidden",
            "selected_decompilation": "excluded unless separately approved",
        },
        "entries": sorted(entries, key=lambda row: row["target"]),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for entry in manifest.get("entries") or []:
        errors.extend(validate_entry_paths(entry))
        target = target_path(str(entry.get("target") or ""))
        if not target.is_file():
            errors.append(f"missing fixture target: {entry.get('target')}")
            continue
        actual = sha256_file(target)
        expected = str(entry.get("sha256") or "")
        if expected and actual != expected:
            errors.append(f"sha256 mismatch for {entry.get('target')}: expected {expected}, got {actual}")
        if is_text_file(target):
            text = target.read_text(encoding="utf-8", errors="ignore")
            if USER_PATH_RE.search(text):
                errors.append(f"user-profile path leaked into fixture: {entry.get('target')}")
    for path in FIXTURE_ROOT.rglob("*"):
        if not path.is_file() or path == DEFAULT_MANIFEST:
            continue
        rel = path.relative_to(FIXTURE_ROOT).as_posix()
        if path.suffix.lower() in BLOCKED_EXTENSIONS:
            errors.append(f"blocked file exists in fixture tree: {rel}")
        if has_blocked_path(rel):
            errors.append(f"blocked path exists in fixture tree: {rel}")
    return errors


def build_zip(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(FIXTURE_ROOT.rglob("*")):
            if not path.is_file():
                continue
            info = zipfile.ZipInfo(path.relative_to(FIXTURE_ROOT.parent).as_posix())
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--source-repo", type=Path, default=default_source_repo())
    parser.add_argument("--refresh", action="store_true", help="recompute fixture files and manifest hashes")
    parser.add_argument("--validate-only", action="store_true", help="validate committed fixture files without reading sources")
    parser.add_argument("--zip", action="store_true", help="also write cloud/cloud-fixtures.zip")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_manifest(args.manifest)
    refresh = args.refresh or manifest is None

    if args.validate_only:
        if manifest is None:
            print(f"missing manifest: {args.manifest}", file=sys.stderr)
            return 2
    elif refresh:
        entries = [copy_entry(entry, args.source_repo) for entry in default_entries()]
        write_manifest(args.manifest, entries)
        manifest = load_manifest(args.manifest)
    else:
        copied = [copy_entry(entry, args.source_repo) for entry in manifest.get("entries") or []]
        for current, expected in zip(copied, manifest.get("entries") or []):
            if current.get("sha256") != expected.get("sha256"):
                print(f"fixture source changed for {expected.get('target')}; rerun with --refresh", file=sys.stderr)
                return 2

    assert manifest is not None
    errors = validate_manifest(manifest)
    if errors:
        print("fixture validation failed:")
        for error in errors:
            print(f"- {error}")
        return 2
    if args.zip:
        build_zip(ROOT / "cloud" / "cloud-fixtures.zip")
    print(f"fixture validation passed: {len(manifest.get('entries') or [])} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
