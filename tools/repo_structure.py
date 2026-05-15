#!/usr/bin/env python3
"""Print a compact, stable overview of this repository's structure."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Section:
    path: str
    description: str
    children: tuple[tuple[str, str], ...] = ()


ROOT_FILES: tuple[tuple[str, str], ...] = (
    ("README.md", "Project overview, wiki usage, and HD smoke reproduction notes"),
    ("AGENTS.md", "Durable operating instructions for Codex and future agents"),
    ("*.md", "Clash95 HD mod analysis, patch notes, and progress reports"),
    ("*.ps1", "Windows harnesses for building, launching, capturing, and probing"),
    ("patch_clash95_hd.py", "Main binary patch helper; writes candidates outside the repo"),
)

SECTIONS: tuple[Section, ...] = (
    Section(
        "tools/",
        "Dependency-light Python helpers for evidence, patch, geometry, and wiki checks",
    ),
    Section(
        "captures/",
        "Checked-in evidence artifacts, screenshots, JSON/CSV summaries, and matrices",
        (("clicktest-*/", "Timestamped menu/input visual regression outputs"),),
    ),
    Section(
        "probes/",
        "Repeatable debugger probe scripts organized by tool and topic",
        (("cdb/", "CDB probes grouped into map, menu, mouse, castle, render, UI, startup, and key-scroll topics"),),
    ),
    Section(
        "ddraw_surfdump_proxy/",
        "Minimal x86 DirectDraw proxy source used by hidden-desktop surface dumps",
        (
            ("ddraw_surfdump_proxy.cpp", "Proxy implementation"),
            ("ddraw_surfdump_proxy.def", "Export definition file"),
        ),
    ),
    Section(
        "reports/",
        "Human-readable validation and recovery reports for focused investigations",
    ),
    Section(
        "cloud/",
        "Cloud-check support files and generated fixtures",
        (("fixtures/", "Fixture data used by cloud checks"),),
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


def iter_existing_sections(root: Path) -> list[Section]:
    return [section for section in SECTIONS if (root / section.path).exists()]


def count_files(root: Path, rel_path: str) -> int:
    path = root / rel_path
    if not path.exists() or not path.is_dir():
        return 0
    return sum(1 for child in path.rglob("*") if child.is_file())


def format_tree(root: Path, include_counts: bool = False) -> str:
    lines: list[str] = ["# Compact Repository Structure", "", "```text", f"{root.name}/"]

    root_entries = list(ROOT_FILES)
    sections = iter_existing_sections(root)
    for index, (name, description) in enumerate(root_entries):
        connector = "├──" if index < len(root_entries) - 1 or sections else "└──"
        lines.append(f"{connector} {name:<25} # {description}")

    for section_index, section in enumerate(sections):
        is_last_section = section_index == len(sections) - 1
        connector = "└──" if is_last_section else "├──"
        count_suffix = f" ({count_files(root, section.path)} files)" if include_counts else ""
        lines.append(f"{connector} {section.path:<25} # {section.description}{count_suffix}")
        child_prefix = "    " if is_last_section else "│   "
        for child_index, (child, child_description) in enumerate(section.children):
            child_connector = "└──" if child_index == len(section.children) - 1 else "├──"
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--counts",
        action="store_true",
        help="include file counts for top-level directories in the tree",
    )
    args = parser.parse_args()
    print(build_output(include_counts=args.counts), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
