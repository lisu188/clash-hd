#!/usr/bin/env python3
"""Small dependency-free keyword search for wiki markdown files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = ROOT / "wiki"


def normalize(text: str) -> str:
    return text.lower()


def extract_headings(text: str) -> list[str]:
    return [
        line.strip("# ").strip()
        for line in text.splitlines()
        if line.lstrip().startswith("#")
    ]


def snippet_for(text: str, terms: list[str], width: int = 140) -> str:
    lower = normalize(text)
    for term in terms:
        idx = lower.find(term)
        if idx >= 0:
            start = max(0, idx - width // 3)
            end = min(len(text), idx + width)
            snippet = re.sub(r"\s+", " ", text[start:end]).strip()
            if start > 0:
                snippet = "..." + snippet
            if end < len(text):
                snippet += "..."
            return snippet
    first = re.sub(r"\s+", " ", text.strip())
    return first[:width] + ("..." if len(first) > width else "")


def score_file(path: Path, query: str) -> tuple[int, str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    terms = [term for term in re.findall(r"\w+", normalize(query)) if term]
    if not terms:
        return 0, ""

    filename = normalize(path.stem.replace("-", " "))
    headings = normalize(" ".join(extract_headings(text)))
    body = normalize(text)

    score = 0
    for term in terms:
        if term in filename:
            score += 8
        if term in headings:
            score += 5
        score += min(body.count(term), 5)

    if score == 0:
        return 0, ""
    return score, snippet_for(text, terms)


def search(query: str, limit: int) -> list[tuple[int, Path, str]]:
    results: list[tuple[int, Path, str]] = []
    for path in sorted(WIKI_DIR.rglob("*.md")):
        score, snippet = score_file(path, query)
        if score:
            results.append((score, path, snippet))
    results.sort(key=lambda item: (-item[0], str(item[1])))
    return results[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Search markdown files under wiki/.")
    parser.add_argument("query", nargs="+", help="query string")
    parser.add_argument("--limit", type=int, default=20, help="maximum results")
    args = parser.parse_args()

    query = " ".join(args.query)
    results = search(query, args.limit)
    if not results:
        print(f"No matches for: {query}")
        return 0

    for score, path, snippet in results:
        rel = path.relative_to(ROOT).as_posix()
        print(f"{score:>3}  {rel}")
        print(f"     {snippet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

