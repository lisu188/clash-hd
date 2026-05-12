#!/usr/bin/env python3
"""Check local links and image artifacts in a Markdown evidence index."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote


LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
WINDOWS_ABS_RE = re.compile(r"^[a-zA-Z]:[\\/]")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


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


def clean_target(target: str) -> str:
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    if " " in target and not WINDOWS_ABS_RE.match(target):
        # Support the common markdown form: (path "optional title").
        parts = re.split(r"\s+['\"]", target, maxsplit=1)
        target = parts[0]
    target = target.split("#", 1)[0]
    target = target.split("?", 1)[0]
    return unquote(target.strip())


def is_external(target: str) -> bool:
    if WINDOWS_ABS_RE.match(target):
        return False
    return bool(EXTERNAL_RE.match(target)) or target.startswith("#") or target == ""


def resolve_target(index_path: Path, target: str) -> Path | None:
    target = clean_target(target)
    if is_external(target):
        return None
    normalized = target.replace("\\", "/")
    if WINDOWS_ABS_RE.match(normalized) or Path(normalized).is_absolute():
        return Path(normalized)
    return (index_path.parent / normalized).resolve()


def collect_targets(markdown: str) -> tuple[list[str], list[str]]:
    body = strip_fenced_code(markdown)
    image_targets = IMAGE_RE.findall(body)
    link_targets = LINK_RE.findall(body)
    return link_targets, image_targets


def target_record(index_path: Path, raw_target: str, kind: str) -> dict[str, Any]:
    cleaned = clean_target(raw_target)
    resolved = resolve_target(index_path, raw_target)
    exists = None if resolved is None else resolved.exists()
    extension = "" if resolved is None else resolved.suffix.lower()
    return {
        "kind": kind,
        "target": raw_target,
        "cleaned": cleaned,
        "resolved": None if resolved is None else str(resolved),
        "exists": exists,
        "extension": extension,
        "is_image_extension": extension in IMAGE_EXTENSIONS,
    }


def build_report(index_path: Path) -> dict[str, Any]:
    markdown = index_path.read_text(encoding="utf-8")
    link_targets, image_targets = collect_targets(markdown)
    link_records = [target_record(index_path, target, "link") for target in link_targets]
    image_records = [target_record(index_path, target, "image") for target in image_targets]
    all_records = link_records + image_records
    missing = [record for record in all_records if record["exists"] is False]
    image_missing = [record for record in image_records if record["exists"] is False]
    image_wrong_ext = [
        record
        for record in image_records
        if record["exists"] is True and not record["is_image_extension"]
    ]
    return {
        "index": str(index_path),
        "counts": {
            "links": len(link_records),
            "images": len(image_records),
            "local_records": sum(1 for record in all_records if record["exists"] is not None),
            "missing": len(missing),
            "image_missing": len(image_missing),
            "image_wrong_extension": len(image_wrong_ext),
        },
        "links": link_records,
        "images": image_records,
        "missing": missing,
        "image_missing": image_missing,
        "image_wrong_extension": image_wrong_ext,
        "passed": not missing and not image_wrong_ext and bool(image_records),
    }


def print_summary(report: dict[str, Any]) -> None:
    counts = report["counts"]
    print(f"evidence index: {report['index']}")
    print(
        "links={links} images={images} local={local_records} missing={missing} "
        "image_missing={image_missing} image_wrong_extension={image_wrong_extension}".format(
            **counts
        )
    )
    print(f"status: {'PASS' if report['passed'] else 'FAIL'}")
    if not report["images"]:
        print("failure: no image artifacts referenced")
    for record in report["missing"]:
        print(f"missing {record['kind']}: {record['target']} -> {record['resolved']}")
    for record in report["image_wrong_extension"]:
        print(f"bad image extension: {record['target']} -> {record['resolved']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "index",
        nargs="?",
        type=Path,
        default=Path("captures/hd-map-evidence-current.md"),
        help="Markdown evidence index to check",
    )
    parser.add_argument("--write-json", type=Path, help="write full check report")
    parser.add_argument("--require-pass", action="store_true", help="exit 2 unless all local links and image artifacts pass")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.index.is_file():
        raise SystemExit(f"Evidence index does not exist: {args.index}")
    report = build_report(args.index.resolve())
    print_summary(report)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.require_pass and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
