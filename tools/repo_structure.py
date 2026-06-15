#!/usr/bin/env python3
"""Print and validate the compact repository structure."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_POLICY = "repo-only structure guard; uses read-only git inventory and does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"

TEXT_SUFFIXES = {".md", ".json", ".py", ".ps1", ".txt", ".csv", ".cdb"}
FORBIDDEN_SUFFIXES = {
    ".exe",
    ".dll",
    ".dmp",
    ".dump",
    ".pml",
    ".raw",
    ".iso",
    ".cue",
    ".bin",
    ".sav",
    ".sg",
    ".dat",
}

APPROVED_ROOT_FILES = {
    ".gitignore",
    "AGENTS.md",
    "README.md",
    "dxcfg_windowed.ini",
    "patch_clash95_hd.py",
}
APPROVED_ROOT_DIRS = {
    ".codex-loop",
    ".git",
    "__pycache__",
    "captures",
    "cloud",
    "docs",
    "meta",
    "probes",
    "raw",
    "reports",
    "scripts",
    "src",
    "tools",
    "wiki",
}

REQUIRED_DIRS = (
    "src/patcher",
    "src/ddraw_surfdump_proxy",
    "scripts/build",
    "scripts/capture",
    "scripts/cdb",
    "scripts/debug",
    "scripts/install",
    "scripts/smoke",
    "probes/cdb/startup",
    "probes/cdb/menu",
    "probes/cdb/mouse",
    "probes/cdb/map",
    "probes/cdb/castle",
    "probes/cdb/battle",
    "probes/cdb/ui",
    "probes/cdb/render",
    "probes/cdb/key-scroll",
    "tools",
    "reports",
    "docs/hd",
    "captures/current",
    "captures/archive",
    "cloud/fixtures",
)

REQUIRED_FILES = (
    "docs/hd/README.md",
    "scripts/README.md",
    "probes/README.md",
    "tools/README.md",
    "reports/README.md",
    "captures/README.md",
    "src/patcher/patch_clash95_hd.py",
    "src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp",
    "src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.def",
    "captures/current/hd-map-evidence-current.md",
    "captures/current/hd-map-smoke-current.md",
    "captures/current/post-owner-evidence-current.md",
    "captures/current/patch-manifest-compare-current-vs-partial12.md",
    "captures/current/patch-stage-current-hd-map.json",
)

STALE_REFERENCE_PATTERNS = (
    "scripts/cdb/scripts",
    "scripts\\cdb\\scripts",
    "scripts/smoke/scripts",
    "scripts\\smoke\\scripts",
    "scripts/capture/scripts",
    "scripts\\capture\\scripts",
    "docs/hd/docs/hd",
    "docs/hd/docs\\hd",
    "src/src/ddraw_surfdump_proxy",
    "ddraw_surfdump_proxy/ddraw_surfdump_proxy/",
    "captures/manual-directinput-proof-current.json",
    ".\\run_cdb_",
    ".\\run_clash_",
    ".\\prepare_hd",
)

STALE_SCAN_ROOTS = (
    "AGENTS.md",
    "README.md",
    "docs",
    "reports",
    "scripts",
    "tools",
    "wiki",
    "captures/current",
)
STALE_SCAN_EXCLUDES = {
    "reports/repository_compaction_plan.md",
    "tools/repo_structure.py",
}


@dataclass(frozen=True)
class Section:
    path: str
    description: str
    children: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


ROOT_FILES: tuple[tuple[str, str], ...] = (
    ("README.md", "Project overview, wiki usage, and HD smoke reproduction notes"),
    ("AGENTS.md", "Durable operating instructions for Codex and future agents"),
    (".gitignore", "Local artifact and proprietary-file exclusions"),
    ("patch_clash95_hd.py", "Compatibility wrapper for the HD patcher"),
    ("dxcfg_windowed.ini", "Small wrapper/config file"),
)

SECTIONS: tuple[Section, ...] = (
    Section(
        "src/",
        "Source implementations that are not root compatibility entrypoints",
        (
            ("patcher/", "HD patcher implementation"),
            ("ddraw_surfdump_proxy/", "DirectDraw surface-dump proxy source"),
        ),
    ),
    Section(
        "scripts/",
        "PowerShell entrypoints grouped by build, capture, CDB, debug, install, and smoke workflows",
        (
            ("build/", "Local build helpers"),
            ("capture/", "Window and client-frame capture helpers"),
            ("cdb/", "Repeatable CDB harnesses"),
            ("debug/", "Interactive debugger launch helpers"),
            ("install/", "Debugger/tool installer helpers"),
            ("smoke/", "Visual smoke tests and candidate-preparation entrypoints"),
        ),
    ),
    Section(
        "probes/",
        "Repeatable debugger probe scripts organized by tool and runtime domain",
        (("cdb/", "CDB probes grouped into startup, menu, mouse, map, castle, battle, UI, render, and key-scroll domains"),),
    ),
    Section(
        "tools/",
        "Dependency-light Python parsers, validators, guards, and tests",
    ),
    Section(
        "reports/",
        "Plans, route inventories, matrices, checklists, and PR bodies",
    ),
    Section(
        "docs/hd/",
        "Durable HD architecture, stage inventory, release boundary, and validation notes",
    ),
    Section(
        "captures/",
        "Checked-in evidence summaries split into current and archive lanes",
        (
            ("current/", "Compact current summaries used by reports and repo-only checks"),
            ("archive/", "Historical evidence retained for traceability"),
        ),
    ),
    Section(
        "cloud/",
        "Cloud-check support files and generated fixtures",
        (("fixtures/", "Stable offline fixtures used by tests"),),
    ),
    Section(
        "raw/",
        "User-owned source material for the LLM wiki; agents do not edit sources",
        (
            ("inbox/", "New sources waiting for ingest"),
            ("processed/", "Sources moved only after explicit user approval"),
            ("assets/", "User-provided images, PDFs, media, and attachments"),
        ),
    ),
    Section(
        "wiki/",
        "Agent-maintained Obsidian-compatible durable knowledge base",
        (
            ("index.md", "Catalog of wiki content"),
            ("overview.md", "Starter guide for the wiki"),
            ("log.md", "Append-only maintenance and ingest log"),
            ("sources/", "One source-summary page per ingested source"),
            ("entities/", "People, organizations, projects, products, places, works"),
            ("concepts/", "Reusable ideas, terms, methods, patterns, and theories"),
            ("syntheses/", "Cross-source synthesis pages"),
            ("questions/", "Open questions and research threads"),
            ("comparisons/", "Structured comparisons"),
        ),
    ),
    Section(
        "meta/",
        "Templates and human-readable workflows for wiki maintenance",
        (
            ("templates/", "Page templates"),
            ("workflows/", "Ingest, query, lint, and contradiction workflows"),
        ),
    ),
)


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def iter_existing_sections(root: Path) -> list[Section]:
    return [section for section in SECTIONS if (root / section.path).exists()]


def count_files(root: Path, rel_path: str) -> int:
    path = root / rel_path
    if not path.exists() or not path.is_dir():
        return 0
    return sum(1 for child in path.rglob("*") if child.is_file())


def format_tree(root: Path, include_counts: bool = False) -> str:
    lines: list[str] = ["# Compact Repository Structure", "", "```text", f"{root.name}/"]

    root_entries = [(name, description) for name, description in ROOT_FILES if (root / name).exists()]
    sections = iter_existing_sections(root)
    for index, (name, description) in enumerate(root_entries):
        connector = "|--" if index < len(root_entries) - 1 or sections else "`--"
        lines.append(f"{connector} {name:<25} # {description}")

    for section_index, section in enumerate(sections):
        is_last_section = section_index == len(sections) - 1
        connector = "`--" if is_last_section else "|--"
        count_suffix = f" ({count_files(root, section.path)} files)" if include_counts else ""
        lines.append(f"{connector} {section.path:<25} # {section.description}{count_suffix}")
        child_prefix = "    " if is_last_section else "|   "
        for child_index, (child, child_description) in enumerate(section.children):
            child_connector = "`--" if child_index == len(section.children) - 1 else "|--"
            lines.append(f"{child_prefix}{child_connector} {child:<21} # {child_description}")

    lines.extend(["```", ""])
    return "\n".join(lines)


def format_summary(root: Path) -> str:
    lines = ["## Summary", ""]
    for section in iter_existing_sections(root):
        lines.append(f"- `{section.path}`: {section.description}.")
    lines.append("")
    return "\n".join(lines)


def build_output(root: Path = ROOT, include_counts: bool = False) -> str:
    return format_tree(root, include_counts=include_counts) + format_summary(root)


def is_allowed_root_file(path: Path) -> bool:
    if path.name in APPROVED_ROOT_FILES:
        return True
    lower = path.name.lower()
    return lower.startswith("license") or lower in {
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "uv.lock",
        "package.json",
        "package-lock.json",
    }


def check_root_contents(root: Path) -> Check:
    unexpected: list[str] = []
    for entry in root.iterdir():
        if entry.is_dir():
            if entry.name not in APPROVED_ROOT_DIRS:
                unexpected.append(entry.name + "/")
        elif not is_allowed_root_file(entry):
            unexpected.append(entry.name)
    if unexpected:
        return Check("root_contents", False, "unexpected root entries: " + ", ".join(sorted(unexpected)))
    return Check("root_contents", True, "root contains only approved docs, config, wrappers, and directories")


def check_required_paths(root: Path) -> Check:
    missing = [path for path in (*REQUIRED_DIRS, *REQUIRED_FILES) if not (root / path).exists()]
    if missing:
        return Check("required_paths", False, "missing: " + ", ".join(missing))
    return Check("required_paths", True, "required compact-layout directories and index files exist")


def check_patcher_wrapper(root: Path) -> Check:
    wrapper = root / "patch_clash95_hd.py"
    implementation = root / "src/patcher/patch_clash95_hd.py"
    if not wrapper.exists() or not implementation.exists():
        return Check("patcher_wrapper", False, "root wrapper or src patcher implementation is missing")
    wrapper_text = wrapper.read_text(encoding="utf-8")
    impl_text = implementation.read_text(encoding="utf-8")
    missing_bits: list[str] = []
    delegates_to_impl = "runpy.run_path" in wrapper_text or (
        "importlib.util" in wrapper_text
        and "spec_from_file_location" in wrapper_text
        and "exec_module" in wrapper_text
    )
    if not delegates_to_impl:
        missing_bits.append("wrapper implementation delegation")
    if "src" not in wrapper_text or "patcher" not in wrapper_text:
        missing_bits.append("wrapper src/patcher target")
    for marker in ("EXPECTED_SHA256", "DEFAULT_STAGE", "PATCHES"):
        if marker not in impl_text:
            missing_bits.append(f"implementation {marker}")
    if missing_bits:
        return Check("patcher_wrapper", False, "missing " + ", ".join(missing_bits))
    return Check("patcher_wrapper", True, "root wrapper delegates to src/patcher without changing arguments")


def git_inventory(root: Path) -> list[Path] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return [root / part.decode("utf-8", errors="replace") for part in result.stdout.split(b"\0") if part]


def fallback_inventory(root: Path) -> list[Path]:
    skipped = {".git", ".codex-loop", "__pycache__"}
    paths: list[Path] = []
    for path in root.rglob("*"):
        if any(part in skipped for part in path.parts):
            continue
        if path.is_file():
            paths.append(path)
    return paths


def check_forbidden_artifacts(root: Path) -> Check:
    inventory = git_inventory(root)
    source = "git inventory"
    if inventory is None:
        inventory = fallback_inventory(root)
        source = "filesystem fallback"
    bad = sorted(rel(path, root) for path in inventory if path.suffix.lower() in FORBIDDEN_SUFFIXES)
    if bad:
        return Check("forbidden_artifacts", False, "forbidden files in " + source + ": " + ", ".join(bad[:20]))
    return Check("forbidden_artifacts", True, "no forbidden executable, dump, save, image, or raw artifacts in " + source)


def iter_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for scan_root in STALE_SCAN_ROOTS:
        path = root / scan_root
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(child for child in path.rglob("*") if child.is_file() and child.suffix.lower() in TEXT_SUFFIXES)
    return files


def check_stale_references(root: Path) -> Check:
    hits: list[str] = []
    for path in iter_text_files(root):
        rel_path = rel(path, root)
        if rel_path in STALE_SCAN_EXCLUDES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern in STALE_REFERENCE_PATTERNS:
                if pattern in line:
                    hits.append(f"{rel_path}:{line_no}: {pattern}")
                    break
            if len(hits) >= 30:
                break
        if len(hits) >= 30:
            break
    if hits:
        return Check("stale_references", False, "stale moved-path references: " + "; ".join(hits))
    return Check("stale_references", True, "no stale moved-path references in active docs, tools, scripts, or current evidence")


def check_current_evidence(root: Path) -> Check:
    index = root / "captures/current/hd-map-evidence-current.md"
    if not index.exists():
        return Check("current_evidence", False, "captures/current/hd-map-evidence-current.md is missing")
    text = index.read_text(encoding="utf-8")
    required_refs: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("captures/current/hd-map-smoke-current.md", ("captures/current/hd-map-smoke-current.md", "hd-map-smoke-current.md")),
        (
            "captures/current/post-owner-evidence-current.md",
            ("captures/current/post-owner-evidence-current.md", "post-owner-evidence-current.md"),
        ),
        (
            "captures/current/patch-manifest-compare-current-vs-partial12.md",
            (
                "captures/current/patch-manifest-compare-current-vs-partial12.md",
                "patch-manifest-compare-current-vs-partial12.md",
            ),
        ),
    )
    text_norm = text.replace("\\", "/")
    missing_refs = [ref for ref, variants in required_refs if not any(variant in text_norm for variant in variants)]
    missing_files = [ref for ref, _variants in required_refs if not (root / ref).exists()]
    if missing_refs or missing_files:
        parts: list[str] = []
        if missing_refs:
            parts.append("missing refs: " + ", ".join(missing_refs))
        if missing_files:
            parts.append("missing files: " + ", ".join(missing_files))
        return Check("current_evidence", False, "; ".join(parts))
    return Check("current_evidence", True, "current HD evidence index points at the compact current summaries")


def run_checks(root: Path = ROOT) -> list[Check]:
    return [
        check_root_contents(root),
        check_required_paths(root),
        check_patcher_wrapper(root),
        check_forbidden_artifacts(root),
        check_current_evidence(root),
        check_stale_references(root),
    ]


def format_checks(checks: list[Check]) -> str:
    lines = ["## Structure Checks", ""]
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        lines.append(f"- `{check.name}`: {status} - {check.detail}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--counts",
        action="store_true",
        help="include file counts for top-level directories in the tree",
    )
    parser.add_argument(
        "--require-pass",
        action="store_true",
        help="exit non-zero when repository structure checks fail",
    )
    args = parser.parse_args()
    print(build_output(include_counts=args.counts), end="")
    checks = run_checks()
    print(format_checks(checks), end="")
    if args.require_pass and any(not check.passed for check in checks):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
