#!/usr/bin/env python3
"""Conservative dependency-free lint checks for the LLM Wiki."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "wiki"
REQUIRED = [WIKI_DIR / "index.md", WIKI_DIR / "log.md", WIKI_DIR / "overview.md"]
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
RAW_FILE_RE = re.compile(r"(?<!\[source: )\braw/[^\s\])`]+?\.[A-Za-z0-9]{1,8}\b")


def normalize_name(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("_", "-").replace(" ", "-")
    value = re.sub(r"[^a-z0-9-]+", "", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value


def has_frontmatter(text: str) -> bool:
    if not text.startswith("---\n"):
        return False
    lines = text.splitlines()
    return any(line.strip() == "---" for line in lines[1:40])


def first_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def frontmatter_title(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    lines = text.splitlines()
    for line in lines[1:40]:
        if line.strip() == "---":
            break
        if line.lower().startswith("title:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return None


def build_page_index(paths: list[Path]) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        candidates = {
            path.stem,
            path.stem.replace("-", " "),
        }
        title = frontmatter_title(text)
        heading = first_heading(text)
        if title:
            candidates.add(title)
        if heading:
            candidates.add(heading)
        for candidate in candidates:
            key = normalize_name(candidate)
            if key:
                index[key] = path
    return index


def lint() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not WIKI_DIR.exists():
        errors.append("Missing wiki/ directory")
        return errors, warnings

    paths = sorted(WIKI_DIR.rglob("*.md"))
    path_set = set(paths)

    for required in REQUIRED:
        if not required.exists():
            errors.append(f"Missing required file: {required.relative_to(ROOT)}")
        elif required.stat().st_size == 0:
            errors.append(f"Required file is empty: {required.relative_to(ROOT)}")

    page_index = build_page_index(paths)
    incoming: dict[Path, int] = {path: 0 for path in paths}

    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = path.relative_to(ROOT).as_posix()

        if not has_frontmatter(text):
            errors.append(f"Missing YAML frontmatter: {rel}")

        for match in WIKILINK_RE.finditer(text):
            target = match.group(1).strip()
            key = normalize_name(target)
            if key not in page_index:
                errors.append(f"Broken wikilink in {rel}: [[{target}]]")
            else:
                incoming[page_index[key]] = incoming.get(page_index[key], 0) + 1

        for match in RAW_FILE_RE.finditer(text):
            errors.append(
                f"Raw file path without citation syntax in {rel}: {match.group(0)}"
            )

    for path in paths:
        if path.name in {"index.md", "log.md"}:
            continue
        if path not in path_set:
            continue
        if incoming.get(path, 0) == 0:
            warnings.append(f"Possible orphan page: {path.relative_to(ROOT)}")

    return errors, warnings


def main() -> int:
    errors, warnings = lint()

    if errors:
        print("Errors:")
        for error in errors:
            print(f"- {error}")

    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")

    if not errors and not warnings:
        print("wiki_lint: ok")
    elif not errors:
        print("wiki_lint: ok with warnings")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

