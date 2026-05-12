#!/usr/bin/env python3
"""Compare two Clash95 patch-stage JSON manifests.

Inputs are JSON files produced by:

    tools/patch_stage_report.py --write-json <path>

The comparison is repo-only: it never reads or writes executables and never
launches the game or debugger.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


PATCH_COMPARE_FIELDS = (
    "group",
    "rva_hex",
    "va_hex",
    "old",
    "new",
    "actual",
    "status",
    "note",
)
METADATA_FIELDS = (
    "exe",
    "stage",
    "exe_sha256",
    "expected_base_sha256",
    "image_base_hex",
    "patch_count",
)
BAD_STATUSES = {"original", "unexpected"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="ascii"))


def sorted_records(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records = list(manifest.get("patches") or [])
    return sorted(
        records,
        key=lambda item: (
            int(item.get("offset", 0)),
            str(item.get("group", "")),
            str(item.get("note", "")),
        ),
    )


def duplicate_offsets(records: list[dict[str, Any]]) -> set[str]:
    counts = Counter(str(record.get("offset_hex") or record.get("offset")) for record in records)
    return {offset for offset, count in counts.items() if count > 1}


def record_key(record: dict[str, Any], duplicate_keys: set[str]) -> str:
    offset = str(record.get("offset_hex") or record.get("offset"))
    if offset in duplicate_keys:
        return "{offset}|{group}|{note}".format(
            offset=offset,
            group=record.get("group", ""),
            note=record.get("note", ""),
        )
    return offset


def index_records(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    duplicates = duplicate_offsets(records)
    return {record_key(record, duplicates): record for record in records}


def compact_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "offset": record.get("offset_hex") or record.get("offset"),
        "group": record.get("group"),
        "status": record.get("status"),
        "old": record.get("old"),
        "new": record.get("new"),
        "actual": record.get("actual"),
        "note": record.get("note"),
    }


def compare_values(left: Any, right: Any) -> dict[str, Any] | None:
    if left == right:
        return None
    return {"left": left, "right": right}


def compare_record(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any] | None:
    changes: dict[str, Any] = {}
    for field in PATCH_COMPARE_FIELDS:
        diff = compare_values(left.get(field), right.get(field))
        if diff is not None:
            changes[field] = diff
    if not changes:
        return None
    return {
        "offset": left.get("offset_hex") or right.get("offset_hex"),
        "left": compact_record(left),
        "right": compact_record(right),
        "changes": changes,
    }


def compare_groups(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_groups = left.get("groups") or {}
    right_groups = right.get("groups") or {}
    result: dict[str, Any] = {}
    for group in sorted(set(left_groups) | set(right_groups)):
        diff = compare_values(left_groups.get(group), right_groups.get(group))
        if diff is not None:
            result[group] = diff
    return result


def metadata_diffs(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in METADATA_FIELDS:
        diff = compare_values(left.get(field), right.get(field))
        if diff is not None:
            result[field] = diff
    status_diff = compare_values(left.get("status_counts"), right.get("status_counts"))
    if status_diff is not None:
        result["status_counts"] = status_diff
    left_gate = (left.get("current_hd_map_gate") or {}).get("passed")
    right_gate = (right.get("current_hd_map_gate") or {}).get("passed")
    gate_diff = compare_values(left_gate, right_gate)
    if gate_diff is not None:
        result["current_hd_map_gate.passed"] = gate_diff
    return result


def nonpatched_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        compact_record(record)
        for record in records
        if str(record.get("status", "")).lower() in BAD_STATUSES
    ]


def build_comparison(left_path: Path, right_path: Path) -> dict[str, Any]:
    left = load_json(left_path)
    right = load_json(right_path)
    left_records = sorted_records(left)
    right_records = sorted_records(right)
    left_index = index_records(left_records)
    right_index = index_records(right_records)
    left_keys = set(left_index)
    right_keys = set(right_index)

    added = [compact_record(right_index[key]) for key in sorted(right_keys - left_keys)]
    removed = [compact_record(left_index[key]) for key in sorted(left_keys - right_keys)]
    changed = []
    for key in sorted(left_keys & right_keys):
        diff = compare_record(left_index[key], right_index[key])
        if diff is not None:
            changed.append(diff)

    group_diffs = compare_groups(left, right)
    metadata = metadata_diffs(left, right)
    left_bad = nonpatched_records(left_records)
    right_bad = nonpatched_records(right_records)
    record_diff_count = len(added) + len(removed) + len(changed)
    structural_diff_count = record_diff_count + len(group_diffs) + len(metadata)

    return {
        "left_path": str(left_path),
        "right_path": str(right_path),
        "left_summary": {
            "exe": left.get("exe"),
            "stage": left.get("stage"),
            "exe_sha256": left.get("exe_sha256"),
            "patch_count": left.get("patch_count"),
            "status_counts": left.get("status_counts") or {},
            "current_hd_map_gate_passed": (left.get("current_hd_map_gate") or {}).get("passed"),
        },
        "right_summary": {
            "exe": right.get("exe"),
            "stage": right.get("stage"),
            "exe_sha256": right.get("exe_sha256"),
            "patch_count": right.get("patch_count"),
            "status_counts": right.get("status_counts") or {},
            "current_hd_map_gate_passed": (right.get("current_hd_map_gate") or {}).get("passed"),
        },
        "counts": {
            "left_records": len(left_records),
            "right_records": len(right_records),
            "common_records": len(left_keys & right_keys),
            "added_records": len(added),
            "removed_records": len(removed),
            "changed_records": len(changed),
            "metadata_diffs": len(metadata),
            "group_diffs": len(group_diffs),
            "left_nonpatched": len(left_bad),
            "right_nonpatched": len(right_bad),
            "record_diff_count": record_diff_count,
            "structural_diff_count": structural_diff_count,
        },
        "metadata_diffs": metadata,
        "group_diffs": group_diffs,
        "added_records": added,
        "removed_records": removed,
        "changed_records": changed,
        "left_nonpatched_records": left_bad,
        "right_nonpatched_records": right_bad,
        "passed": structural_diff_count == 0 and not left_bad and not right_bad,
    }


def print_record(record: dict[str, Any]) -> str:
    return (
        "{offset} {group} status={status} old={old} new={new} actual={actual} note={note}"
    ).format(
        offset=record.get("offset"),
        group=record.get("group"),
        status=record.get("status"),
        old=record.get("old"),
        new=record.get("new"),
        actual=record.get("actual"),
        note=record.get("note"),
    )


def print_summary(comparison: dict[str, Any], limit: int) -> None:
    counts = comparison["counts"]
    print("Patch manifest comparison")
    print(f"left:  {comparison['left_path']}")
    print(f"right: {comparison['right_path']}")
    print(
        "records: left={left_records} right={right_records} common={common_records} "
        "added={added_records} removed={removed_records} changed={changed_records}".format(
            **counts
        )
    )
    print(
        "diffs: metadata={metadata_diffs} groups={group_diffs} record={record_diff_count}".format(
            **counts
        )
    )
    print(
        "nonpatched: left={left_nonpatched} right={right_nonpatched}".format(**counts)
    )

    if comparison["metadata_diffs"]:
        print("metadata changes:")
        for key, diff in comparison["metadata_diffs"].items():
            print(f"  {key}: {diff['left']} -> {diff['right']}")
    if comparison["group_diffs"]:
        print("group changes:")
        for key, diff in comparison["group_diffs"].items():
            print(f"  {key}: {diff['left']} -> {diff['right']}")
    if comparison["added_records"]:
        print("added records:")
        for record in comparison["added_records"][:limit]:
            print("  + " + print_record(record))
    if comparison["removed_records"]:
        print("removed records:")
        for record in comparison["removed_records"][:limit]:
            print("  - " + print_record(record))
    if comparison["changed_records"]:
        print("changed records:")
        for record in comparison["changed_records"][:limit]:
            changed_fields = ", ".join(record["changes"])
            print(f"  * {record['offset']} fields={changed_fields}")
            print("    left:  " + print_record(record["left"]))
            print("    right: " + print_record(record["right"]))
    if comparison["left_nonpatched_records"]:
        print("left original/unexpected records:")
        for record in comparison["left_nonpatched_records"][:limit]:
            print("  ! " + print_record(record))
    if comparison["right_nonpatched_records"]:
        print("right original/unexpected records:")
        for record in comparison["right_nonpatched_records"][:limit]:
            print("  ! " + print_record(record))
    if not comparison["metadata_diffs"] and not comparison["group_diffs"] and not counts["record_diff_count"]:
        print("record_diffs: none")


def markdown_record(record: dict[str, Any], prefix: str = "") -> str:
    return (
        f"| {prefix}{record.get('offset')} | {record.get('group')} | "
        f"{record.get('status')} | `{record.get('old')}` | `{record.get('new')}` | "
        f"`{record.get('actual')}` | {record.get('note')} |"
    )


def write_markdown(path: Path, comparison: dict[str, Any], limit: int) -> None:
    counts = comparison["counts"]
    lines = [
        "# Patch Manifest Comparison",
        "",
        f"- Left: `{comparison['left_path']}`",
        f"- Right: `{comparison['right_path']}`",
        f"- Records: left={counts['left_records']} right={counts['right_records']} "
        f"common={counts['common_records']} added={counts['added_records']} "
        f"removed={counts['removed_records']} changed={counts['changed_records']}",
        f"- Diffs: metadata={counts['metadata_diffs']} groups={counts['group_diffs']} "
        f"records={counts['record_diff_count']}",
        f"- Nonpatched: left={counts['left_nonpatched']} right={counts['right_nonpatched']}",
        "",
    ]
    if comparison["metadata_diffs"]:
        lines.extend(["## Metadata Changes", ""])
        for key, diff in comparison["metadata_diffs"].items():
            lines.append(f"- `{key}`: `{diff['left']}` -> `{diff['right']}`")
        lines.append("")
    if comparison["group_diffs"]:
        lines.extend(["## Group Changes", ""])
        for key, diff in comparison["group_diffs"].items():
            lines.append(f"- `{key}`: `{diff['left']}` -> `{diff['right']}`")
        lines.append("")
    for title, records, prefix in (
        ("Added Records", comparison["added_records"], "+"),
        ("Removed Records", comparison["removed_records"], "-"),
        ("Left Original/Unexpected Records", comparison["left_nonpatched_records"], "!"),
        ("Right Original/Unexpected Records", comparison["right_nonpatched_records"], "!"),
    ):
        if not records:
            continue
        lines.extend([
            f"## {title}",
            "",
            "| Offset | Group | Status | Old | New | Actual | Note |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ])
        lines.extend(markdown_record(record, prefix) for record in records[:limit])
        lines.append("")
    if comparison["changed_records"]:
        lines.extend(["## Changed Records", ""])
        for record in comparison["changed_records"][:limit]:
            lines.append(f"### {record['offset']}")
            lines.append("")
            lines.append(f"- Fields: {', '.join(record['changes'])}")
            lines.append("")
            lines.append("| Side | Group | Status | Old | New | Actual | Note |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- |")
            for side in ("left", "right"):
                compact = record[side]
                lines.append(
                    f"| {side} | {compact.get('group')} | {compact.get('status')} | "
                    f"`{compact.get('old')}` | `{compact.get('new')}` | "
                    f"`{compact.get('actual')}` | {compact.get('note')} |"
                )
            lines.append("")
    if not comparison["metadata_diffs"] and not comparison["group_diffs"] and not counts["record_diff_count"]:
        lines.extend(["## Record Diffs", "", "None.", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path, help="older or baseline patch-stage JSON")
    parser.add_argument("right", type=Path, help="newer or candidate patch-stage JSON")
    parser.add_argument("--write-json", type=Path, help="write full comparison JSON")
    parser.add_argument("--write-markdown", type=Path, help="write human-readable markdown")
    parser.add_argument("--limit", type=int, default=20, help="maximum records to print per section")
    parser.add_argument("--fail-on-diff", action="store_true", help="exit 2 if any metadata, group, or record diff is present")
    parser.add_argument("--fail-on-bad-status", action="store_true", help="exit 2 if either manifest contains original/unexpected records")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    comparison = build_comparison(args.left, args.right)
    print_summary(comparison, args.limit)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, comparison, args.limit)
    if args.fail_on_diff and comparison["counts"]["structural_diff_count"]:
        return 2
    if args.fail_on_bad_status and (
        comparison["counts"]["left_nonpatched"] or comparison["counts"]["right_nonpatched"]
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
