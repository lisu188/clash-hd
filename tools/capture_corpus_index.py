#!/usr/bin/env python3
"""Build a read-only index of capture artifacts and references.

This is a repo-only scanner. It does not delete, move, launch, or mutate any
capture artifact.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote


RUNTIME_POLICY = "repo-only capture index; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
DEFAULT_JSON = Path("captures/current/capture-corpus-index-current.json")
DEFAULT_MD = Path("captures/current/capture-corpus-index-current.md")
CURRENT_REFERENCE_SOURCES = [
    Path("captures/current/hd-map-evidence-current.md"),
]
ARCHIVED_REFERENCE_SOURCES = [
    Path("README.md"),
    Path("docs/hd/HD_MOD_PROGRESS.md"),
    Path(".codex-loop/NEXT.md"),
    Path(".codex-loop/STATE.md"),
    Path("wiki/sources/current-hd-map-evidence.md"),
    Path("wiki/syntheses/current-clash95-hd-state.md"),
]

CAPTURE_REF_RE = re.compile(r"(?<![A-Za-z0-9_])captures[\\/][^\s\]\)>'\"`,]+", re.IGNORECASE)
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
WINDOWS_ABS_RE = re.compile(r"^[a-zA-Z]:[\\/]")
PLACEHOLDER_RE = re.compile(r"(\*|yyyy|hhmmss|\.\.\.|fixture-run|transition-run)", re.IGNORECASE)


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def normalize_capture_ref(raw: str) -> str:
    value = raw.strip().strip(".,;:")
    return value.replace("\\", "/")


def canonical_capture_ref(root: Path, ref: str) -> str:
    norm = normalize_capture_ref(ref)
    if (root / norm).exists():
        return norm
    prefix = "captures/"
    archive_prefix = "captures/archive/"
    if norm.lower().startswith(prefix) and not norm.lower().startswith(archive_prefix):
        suffix = norm[len(prefix) :]
        if suffix.lower().startswith("cdb-surface-dump-"):
            archived = archive_prefix + suffix
            if (root / archived).exists():
                return archived
    return norm


def is_placeholder_ref(value: str) -> bool:
    return bool(PLACEHOLDER_RE.search(value))


def strip_fenced_code(markdown: str) -> str:
    lines: list[str] = []
    in_fence = False
    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            lines.append(line)
    return "\n".join(lines)


def clean_target(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1].strip()
    if " " in value and not WINDOWS_ABS_RE.match(value):
        value = re.split(r"\s+['\"]", value, maxsplit=1)[0]
    value = value.split("#", 1)[0]
    value = value.split("?", 1)[0]
    value = value.replace("\\\\", "\\")
    return unquote(value.rstrip(".,;:)]}'\"").strip())


def is_external_ref(value: str) -> bool:
    if WINDOWS_ABS_RE.match(value):
        return False
    return bool(EXTERNAL_RE.match(value)) or value.startswith("#") or value == ""


def capture_ref_from_target(root: Path, source_path: Path, raw: str) -> str | None:
    cleaned = clean_target(raw)
    if is_external_ref(cleaned) or PLACEHOLDER_RE.search(cleaned):
        return None
    normalized = cleaned.replace("\\", "/")
    if normalized.lower().startswith("captures/"):
        return normalize_capture_ref(normalized)
    if WINDOWS_ABS_RE.match(normalized) or Path(normalized).is_absolute():
        candidate = Path(normalized)
    else:
        candidate = source_path.parent / normalized
    try:
        relative = candidate.resolve().relative_to((root / "captures").resolve())
    except ValueError:
        return None
    return f"captures/{relative.as_posix()}"


def first_capture_entry(ref: str) -> str | None:
    norm = normalize_capture_ref(ref)
    parts = norm.split("/")
    if len(parts) < 2 or parts[0].lower() != "captures":
        return None
    if len(parts) >= 3 and parts[1].lower() in {"archive", "current"}:
        return f"{parts[1]}/{parts[2]}"
    return parts[1]


def iter_capture_artifacts(captures_root: Path) -> list[tuple[str, Path]]:
    artifacts: list[tuple[str, Path]] = []
    for path in sorted(captures_root.iterdir(), key=lambda item: item.name.lower()):
        if path.is_dir() and path.name.lower() in {"archive", "current"}:
            artifacts.extend(
                (f"{path.name}/{child.name}", child)
                for child in sorted(path.iterdir(), key=lambda item: item.name.lower())
            )
        else:
            artifacts.append((path.name, path))
    return artifacts


def extract_refs(root: Path, path: Path) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    body = strip_fenced_code(text) if path.suffix.lower() == ".md" else text
    refs = {
        canonical_capture_ref(root, match.group(0))
        for match in CAPTURE_REF_RE.finditer(body)
        if not is_placeholder_ref(match.group(0))
    }
    for pattern in (IMAGE_RE, LINK_RE):
        for match in pattern.finditer(body):
            ref = capture_ref_from_target(root, path, match.group(1))
            if ref:
                refs.add(canonical_capture_ref(root, ref))
    return sorted(refs)


def classify_era(path: Path) -> tuple[str, str]:
    name = path.name.lower()
    if name.startswith("clicktest-") or name.startswith("visual-smoke-"):
        return "visible_era", "legacy visible/click or visual-smoke artifact"
    if name.startswith("sandbox-") or name.startswith("virtualbox-"):
        return "visible_era", "Windows Sandbox/VM-era artifact"
    if name.startswith("cdb-surface-dump-"):
        text = ""
        for child in [path / "summary.json", path / "RUN-SUMMARY.md"]:
            if child.exists() and child.is_file():
                text += "\n" + child.read_text(encoding="utf-8-sig", errors="replace")
        lower = text.lower()
        if "allowvisibledesktop=true" in lower or "visible desktop fallback: true" in lower:
            return "cdb_surface_dump_visible_fallback", "CDB surface dump reports visible desktop fallback"
        if "hidden desktop" in lower or "no visible desktop window" in lower or "allowvisibledesktop=false" in lower:
            return "hidden_cdb_surface_dump", "CDB surface dump reports hidden/no-popup desktop"
        return "cdb_surface_dump_unverified", "CDB surface dump metadata did not state hidden/visible desktop"
    return "other_capture_artifact", "non-runtime report or unclassified capture artifact"


def source_refs(root: Path, sources: list[Path], reference_class: str) -> dict[str, dict[str, Any]]:
    refs: dict[str, dict[str, Any]] = {}
    for source in sources:
        source_path = root / source
        for ref in extract_refs(root, source_path):
            entry = first_capture_entry(ref)
            if not entry:
                continue
            refs.setdefault(
                ref,
                {
                    "ref": ref,
                    "entry": entry,
                    "reference_class": reference_class,
                    "sources": [],
                    "exists": (root / ref).exists(),
                    "entry_exists": (root / "captures" / entry).exists(),
                },
            )
            refs[ref]["sources"].append(source.as_posix())
    return refs


def build_index(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    captures_root = root / args.captures_root
    current_refs = source_refs(root, args.current_source, "current_referenced")
    archived_refs = source_refs(root, args.archived_source, "archived_referenced")
    current_entries = {record["entry"] for record in current_refs.values()}
    archived_entries = {record["entry"] for record in archived_refs.values()}

    missing_current_refs = [ref for ref, record in sorted(current_refs.items()) if not record["exists"]]
    artifacts: list[dict[str, Any]] = []
    failures: list[str] = []
    if not captures_root.exists():
        failures.append(f"captures root is missing: {captures_root}")
        entries: list[Path] = []
    else:
        entries = iter_capture_artifacts(captures_root)

    for entry, path in entries:
        era, reason = classify_era(path)
        if entry in current_entries:
            ref_status = "current_referenced"
        elif entry in archived_entries:
            ref_status = "archived_referenced"
        else:
            ref_status = "stale_unreferenced"
        record = {
            "name": entry,
            "path": str(path),
            "artifact_kind": "directory" if path.is_dir() else "file",
            "reference_status": ref_status,
            "era": era,
            "classification_reason": reason,
            "has_surface_png": (path / "surface.png").exists() if path.is_dir() else False,
            "has_run_summary": (path / "RUN-SUMMARY.md").exists() if path.is_dir() else False,
        }
        artifacts.append(record)
        if ref_status == "current_referenced" and era in {"visible_era", "sandbox_vm_era"}:
            failures.append(f"current evidence references {era} artifact: captures/{entry}")
        if ref_status == "current_referenced" and era == "cdb_surface_dump_visible_fallback":
            failures.append(f"current evidence references visible-desktop CDB surface dump: captures/{entry}")

    for ref in missing_current_refs:
        failures.append(f"current reference is missing: {ref}")

    counts: dict[str, int] = {}
    era_counts: dict[str, int] = {}
    for artifact in artifacts:
        counts[artifact["reference_status"]] = counts.get(artifact["reference_status"], 0) + 1
        era_counts[artifact["era"]] = era_counts.get(artifact["era"], 0) + 1

    stale_visible = [
        artifact["name"]
        for artifact in artifacts
        if artifact["reference_status"] != "current_referenced"
        and artifact["era"] in {"visible_era", "sandbox_vm_era"}
    ]

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": "current evidence capture references must resolve and must not reactivate visible-era or sandbox/VM artifacts as active blockers",
        "captures_root": str(captures_root),
        "artifact_count": len(artifacts),
        "current_reference_count": len(current_refs),
        "archived_reference_count": len(archived_refs),
        "missing_current_refs": missing_current_refs,
        "reference_status_counts": dict(sorted(counts.items())),
        "era_counts": dict(sorted(era_counts.items())),
        "stale_visible_or_sandbox_count": len(stale_visible),
        "stale_visible_or_sandbox_examples": stale_visible[:20],
        "current_refs": current_refs,
        "archived_refs": archived_refs,
        "artifacts": artifacts,
        "failures": failures,
    }


def print_index(index: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(index['passed']))}")
    print(f"runtime-policy: {index['runtime_policy']}")
    print(f"artifacts: {index['artifact_count']}")
    print(f"current-refs: {index['current_reference_count']}")
    print(f"stale-visible-or-sandbox: {index['stale_visible_or_sandbox_count']}")
    if index["failures"]:
        print("failures:")
        for failure in index["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, index: dict[str, Any]) -> None:
    lines = [
        "# Capture Corpus Index",
        "",
        f"- Overall: {status_text(bool(index['passed']))}",
        f"- Generated: `{index['generated_at']}`",
        f"- Runtime policy: {index['runtime_policy']}",
        f"- Guard policy: {index['guard_policy']}",
        f"- Captures root: `{index['captures_root']}`",
        f"- Artifact count: `{index['artifact_count']}`",
        f"- Current references: `{index['current_reference_count']}`",
        f"- Archived references: `{index['archived_reference_count']}`",
        f"- Missing current refs: `{index['missing_current_refs']}`",
        f"- Stale visible/sandbox artifacts: `{index['stale_visible_or_sandbox_count']}`",
        "",
        "## Reference Status Counts",
        "",
    ]
    for name, count in index["reference_status_counts"].items():
        lines.append(f"- `{name}`: `{count}`")
    lines.extend(["", "## Era Counts", ""])
    for name, count in index["era_counts"].items():
        lines.append(f"- `{name}`: `{count}`")
    lines.extend(["", "## Stale Visible Or Sandbox Examples", ""])
    if index["stale_visible_or_sandbox_examples"]:
        lines.extend(f"- `captures/{name}`" for name in index["stale_visible_or_sandbox_examples"])
    else:
        lines.append("- None")
    if index["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in index["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--captures-root", type=Path, default=Path("captures"))
    parser.add_argument("--current-source", type=Path, action="append", default=list(CURRENT_REFERENCE_SOURCES))
    parser.add_argument("--archived-source", type=Path, action="append", default=list(ARCHIVED_REFERENCE_SOURCES))
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    index = build_index(args)
    print_index(index)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, index)
    if args.require_pass and not index["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
