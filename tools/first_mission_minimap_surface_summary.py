#!/usr/bin/env python3
"""Summarize first-mission minimap/backing-surface CDB evidence."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_LOG = Path("captures/archive/cdb-surface-dump-20260616-153751/cdb-surface-dump.log")
DEFAULT_COVERAGE_JSON = Path("captures/archive/cdb-surface-dump-20260616-153751/map-tile-coverage-full.json")
DEFAULT_VISIBILITY_JSON = Path("captures/archive/cdb-surface-dump-20260616-153751/visibility-coverage-full.json")
DEFAULT_JSON = Path("captures/current/first-mission-minimap-surface-current.json")
DEFAULT_MD = Path("captures/current/first-mission-minimap-surface-current.md")

INIT_RE = re.compile(
    r"FMMS_MINIMAP_INIT left=(?P<left>-?\d+) top=(?P<top>-?\d+) "
    r"width=(?P<width>-?\d+) height=(?P<height>-?\d+) "
    r"right=(?P<right>-?\d+) bottom=(?P<bottom>-?\d+) "
    r"backing=(?P<backing>[0-9a-fA-F]+) "
    r"backing_sz=\((?P<backing_width>-?\d+),(?P<backing_height>-?\d+)\) "
    r"backing_base=(?P<backing_base>[0-9a-fA-F]+) scale=(?P<scale>-?\d+)"
)
DIRTY_RE = re.compile(
    r"FMMS_MINIMAP_DIRTY_ENTRY seq=(?P<seq>\d+) ret=(?P<ret>[0-9a-fA-F]+) "
    r"bounds=\((?P<left>-?\d+),(?P<top>-?\d+),(?P<right>-?\d+),(?P<bottom>-?\d+)\) "
    r"backing=(?P<backing>[0-9a-fA-F]+) "
    r"backing_sz=\((?P<backing_width>-?\d+),(?P<backing_height>-?\d+)\) "
    r"backing_base=(?P<backing_base>[0-9a-fA-F]+) "
    r"map_surface=(?P<map_surface>[0-9a-fA-F]+) "
    r"map_sz=\((?P<map_width>-?\d+),(?P<map_height>-?\d+)\) "
    r"regs=\((?P<regs>[0-9a-fA-F,]+)\) "
    r"backing_samples=\((?P<backing_samples>[0-9a-fA-F,]+)\) "
    r"map_samples=\((?P<map_samples>[0-9a-fA-F,]+)\)"
)
DIRTY_UNAVAILABLE_RE = re.compile(r"FMMS_MINIMAP_DIRTY_ENTRY .*sample_status=unavailable")
FULL_RE = re.compile(
    r"FMMS_FULLREDRAW_AFTER_LOWER redraw=(?P<redraw>\d+) "
    r"surface=(?P<surface>[0-9a-fA-F]+) "
    r"size=\((?P<width>-?\d+),(?P<height>-?\d+)\) "
    r"minimap_samples=\((?P<minimap_samples>[0-9a-fA-F,]+)\) "
    r"right_panel_samples=\((?P<right_panel_samples>[0-9a-fA-F,]+)\) "
    r"bottom_samples=\((?P<bottom_samples>[0-9a-fA-F,]+)\)"
)
SELECT_RE = re.compile(r"FMMS_UNITSEL_SELECT_SUCCESS .*selected_after=(?P<selected>-?\d+)")
DONE_RE = re.compile(r"FMMS_UNITSEL_DONE selected=(?P<selected>-?\d+) ")
READY_RE = re.compile(
    r"SURFDUMP_READY redraw_seq=(?P<redraw>\d+) surface=(?P<surface>[0-9a-fA-F]+) "
    r"size=\((?P<width>-?\d+),(?P<height>-?\d+)\)"
)

INT_FIELDS = {
    "seq",
    "left",
    "top",
    "width",
    "height",
    "right",
    "bottom",
    "backing_width",
    "backing_height",
    "map_width",
    "map_height",
    "redraw",
    "scale",
    "selected",
}


def as_int(value: str) -> int:
    return int(value)


def as_hex_int(value: str) -> int:
    return int(value, 16)


def samples(text: str) -> list[int]:
    return [as_hex_int(part) for part in text.split(",") if part]


def convert(match: re.Match[str], line_no: int, kind: str) -> dict[str, Any]:
    row: dict[str, Any] = {"line_no": line_no, "kind": kind}
    for key, value in match.groupdict().items():
        if key in INT_FIELDS:
            row[key] = as_int(value)
        elif key.endswith("samples"):
            row[key] = samples(value)
        elif key == "regs":
            row[key] = [as_hex_int(part) for part in value.split(",")]
        else:
            row[key] = value
    return row


def parse_log(path: Path) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = {
        "init": [],
        "dirty": [],
        "dirty_unavailable": [],
        "full": [],
        "select": [],
        "done": [],
        "ready": [],
        "av": [],
    }
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if match := INIT_RE.search(line):
            rows["init"].append(convert(match, line_no, "FMMS_MINIMAP_INIT"))
        if match := DIRTY_RE.search(line):
            rows["dirty"].append(convert(match, line_no, "FMMS_MINIMAP_DIRTY_ENTRY"))
        elif DIRTY_UNAVAILABLE_RE.search(line):
            rows["dirty_unavailable"].append({"line_no": line_no, "kind": "FMMS_MINIMAP_DIRTY_ENTRY"})
        if match := FULL_RE.search(line):
            rows["full"].append(convert(match, line_no, "FMMS_FULLREDRAW_AFTER_LOWER"))
        if match := SELECT_RE.search(line):
            rows["select"].append(convert(match, line_no, "FMMS_UNITSEL_SELECT_SUCCESS"))
        if match := DONE_RE.search(line):
            rows["done"].append(convert(match, line_no, "FMMS_UNITSEL_DONE"))
        if match := READY_RE.search(line):
            rows["ready"].append(convert(match, line_no, "SURFDUMP_READY"))
        if "Access violation" in line or line.strip().startswith("AV_"):
            rows["av"].append({"line_no": line_no, "kind": "AV"})
    return rows


def flatten_sample_values(rows: list[dict[str, Any]], key: str) -> list[int]:
    values: list[int] = []
    for row in rows:
        values.extend(int(value) for value in row.get(key, []))
    return values


def counter_items(values: list[int]) -> list[dict[str, Any]]:
    counts = Counter(values)
    return [
        {"value": f"0x{value:02x}", "count": count}
        for value, count in counts.most_common()
    ]


def black_like_percent(values: list[int]) -> float:
    if not values:
        return 0.0
    black_like = sum(1 for value in values if value in {0x00, 0x01})
    return round(black_like * 100.0 / len(values), 3)


def unique_rects(rows: list[dict[str, Any]]) -> list[list[int]]:
    rects = {
        (int(row["left"]), int(row["top"]), int(row["right"]), int(row["bottom"]))
        for row in rows
        if {"left", "top", "right", "bottom"} <= row.keys()
    }
    return [list(rect) for rect in sorted(rects)]


def unique_sizes(rows: list[dict[str, Any]], prefix: str = "") -> list[list[int]]:
    width_key = f"{prefix}width"
    height_key = f"{prefix}height"
    sizes = {
        (int(row[width_key]), int(row[height_key]))
        for row in rows
        if width_key in row and height_key in row
    }
    return [list(size) for size in sorted(sizes)]


def load_json_if_present(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def extract_coverage_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {
            "available": False,
            "blank_active_cells": [],
            "flagged_active_cells": None,
            "measurable_active_cells": None,
            "gameplay_frame_likely": None,
            "edge_coverage": {},
        }
    image = (payload.get("images") or [{}])[0]
    summary = image.get("summary") or {}
    frame_check = image.get("frame_check") or {}
    return {
        "available": True,
        "blank_active_cells": list(summary.get("blank_active_cells") or []),
        "flagged_active_cells": summary.get("flagged_active_cells"),
        "measurable_active_cells": summary.get("measurable_active_cells"),
        "gameplay_frame_likely": frame_check.get("gameplay_frame_likely"),
        "edge_coverage": frame_check.get("edge_coverage") or {},
    }


def extract_visibility_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {
            "available": False,
            "blank_cells": [],
            "explained_blank_cells": [],
            "unexplained_blank_cells": [],
            "status_counts": {},
        }
    return {
        "available": True,
        "blank_cells": list(payload.get("blank_cells") or []),
        "explained_blank_cells": list(payload.get("explained_blank_cells") or []),
        "unexplained_blank_cells": list(payload.get("unexplained_blank_cells") or []),
        "status_counts": dict(payload.get("status_counts") or {}),
    }


def summarize(
    path: Path,
    coverage_json: Path | None = None,
    visibility_json: Path | None = None,
) -> dict[str, Any]:
    rows = parse_log(path)
    coverage_payload = load_json_if_present(coverage_json)
    visibility_payload = load_json_if_present(visibility_json)
    coverage = extract_coverage_summary(coverage_payload)
    visibility = extract_visibility_summary(visibility_payload)
    backing_values = flatten_sample_values(rows["dirty"], "backing_samples")
    dirty_map_values = flatten_sample_values(rows["dirty"], "map_samples")
    full_minimap_values = flatten_sample_values(rows["full"], "minimap_samples")
    full_right_values = flatten_sample_values(rows["full"], "right_panel_samples")
    full_bottom_values = flatten_sample_values(rows["full"], "bottom_samples")
    last_full = rows["full"][-1] if rows["full"] else None
    selected_values = [int(row["selected"]) for row in rows["select"] + rows["done"]]

    minimap_anchor_ok = [586, 16, 799, 229] in unique_rects(rows["dirty"])
    backing_size_ok = [214, 214] in unique_sizes(rows["dirty"], "backing_")
    map_surface_ok = [800, 600] in unique_sizes(rows["dirty"], "map_")
    unit_selected = any(value >= 0 for value in selected_values)
    ready_seen = bool(rows["ready"])
    av_free = not rows["av"]
    backing_black_like = black_like_percent(backing_values)
    full_minimap_black_like = black_like_percent(full_minimap_values)
    right_panel_black_like = black_like_percent(full_right_values)
    bottom_black_like = black_like_percent(full_bottom_values)
    blank_active_cells = coverage["blank_active_cells"]
    explained_blank_cells = visibility["explained_blank_cells"]
    unexplained_blank_cells = visibility["unexplained_blank_cells"]
    blank_set = set(blank_active_cells)
    explained_set = set(explained_blank_cells)
    all_blank_cells_visibility_explained = bool(blank_set) and not unexplained_blank_cells and blank_set <= explained_set

    passed = all(
        [
            path.exists(),
            ready_seen,
            av_free,
            unit_selected,
            minimap_anchor_ok,
            backing_size_ok,
            map_surface_ok,
            bool(rows["dirty"]),
            bool(rows["full"]),
        ]
    )

    if backing_black_like >= 80.0 and minimap_anchor_ok and backing_size_ok:
        interpretation = (
            "minimap backing is already mostly black-like before final HD surface sampling"
        )
    else:
        interpretation = "minimap backing needs more sampling before assigning cause"
    if all_blank_cells_visibility_explained:
        blocker = (
            "right/bottom map blanks are visibility-zero explained; remaining UI work is "
            "tooltip/status owner-state and natural panel composition"
        )
    elif right_panel_black_like >= 80.0 or bottom_black_like >= 80.0:
        blocker = "right/bottom panel samples remain mostly black-like"
    else:
        blocker = "right/bottom sampled panels are not mostly black-like"

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "log": str(path),
        "coverage_json": str(coverage_json) if coverage_json else None,
        "visibility_json": str(visibility_json) if visibility_json else None,
        "passed": passed,
        "counts": {key: len(value) for key, value in rows.items()},
        "ready_seen": ready_seen,
        "av_free": av_free,
        "unit_selected": unit_selected,
        "selected_values": sorted(set(selected_values)),
        "minimap_anchor_ok": minimap_anchor_ok,
        "backing_size_ok": backing_size_ok,
        "map_surface_ok": map_surface_ok,
        "minimap_bounds": unique_rects(rows["dirty"]),
        "backing_sizes": unique_sizes(rows["dirty"], "backing_"),
        "map_sizes": unique_sizes(rows["dirty"], "map_"),
        "backing_sample_counts": counter_items(backing_values),
        "dirty_map_sample_counts": counter_items(dirty_map_values),
        "full_minimap_sample_counts": counter_items(full_minimap_values),
        "full_right_panel_sample_counts": counter_items(full_right_values),
        "full_bottom_sample_counts": counter_items(full_bottom_values),
        "backing_black_like_percent": backing_black_like,
        "full_minimap_black_like_percent": full_minimap_black_like,
        "right_panel_black_like_percent": right_panel_black_like,
        "bottom_black_like_percent": bottom_black_like,
        "coverage_available": coverage["available"],
        "coverage_gameplay_frame_likely": coverage["gameplay_frame_likely"],
        "coverage_flagged_active_cells": coverage["flagged_active_cells"],
        "coverage_measurable_active_cells": coverage["measurable_active_cells"],
        "coverage_edge_coverage": coverage["edge_coverage"],
        "blank_active_cells": blank_active_cells,
        "visibility_available": visibility["available"],
        "visibility_blank_cells": visibility["blank_cells"],
        "visibility_explained_blank_cells": explained_blank_cells,
        "visibility_unexplained_blank_cells": unexplained_blank_cells,
        "visibility_status_counts": visibility["status_counts"],
        "all_blank_cells_visibility_explained": all_blank_cells_visibility_explained,
        "last_fullredraw_sample": last_full,
        "first_dirty": rows["dirty"][:1],
        "last_dirty": rows["dirty"][-1:] if rows["dirty"] else [],
        "interpretation": interpretation,
        "blocker": blocker,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# First Mission Minimap Surface Summary",
        "",
        f"- Overall: {'PASS' if report['passed'] else 'FAIL'}",
        f"- Log: `{report['log']}`",
        f"- Ready seen: `{report['ready_seen']}`",
        f"- AV free: `{report['av_free']}`",
        f"- Unit selected: `{report['unit_selected']}`",
        f"- Minimap anchor OK: `{report['minimap_anchor_ok']}`",
        f"- Backing size OK: `{report['backing_size_ok']}`",
        f"- Map surface OK: `{report['map_surface_ok']}`",
        f"- Minimap bounds: `{report['minimap_bounds']}`",
        f"- Backing black-like samples: `{report['backing_black_like_percent']}`%",
        f"- Final minimap black-like samples: `{report['full_minimap_black_like_percent']}`%",
        f"- Right-panel black-like samples: `{report['right_panel_black_like_percent']}`%",
        f"- Bottom black-like samples: `{report['bottom_black_like_percent']}`%",
        f"- Coverage JSON: `{report['coverage_json']}`",
        f"- Visibility JSON: `{report['visibility_json']}`",
        f"- Blank active cells: `{report['blank_active_cells']}`",
        f"- Visibility unexplained blank cells: `{report['visibility_unexplained_blank_cells']}`",
        f"- All blank cells visibility-explained: `{report['all_blank_cells_visibility_explained']}`",
        f"- Interpretation: {report['interpretation']}",
        f"- Blocker: {report['blocker']}",
        "",
        "## Coverage",
        "",
        f"- Gameplay frame likely: `{report['coverage_gameplay_frame_likely']}`",
        f"- Flagged active cells: `{report['coverage_flagged_active_cells']}`",
        f"- Measurable active cells: `{report['coverage_measurable_active_cells']}`",
        f"- Visibility status counts: `{report['visibility_status_counts']}`",
        "",
        "## Counts",
        "",
    ]
    for key, value in sorted(report["counts"].items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Sample Values", ""])
    for key in (
        "backing_sample_counts",
        "dirty_map_sample_counts",
        "full_minimap_sample_counts",
        "full_right_panel_sample_counts",
        "full_bottom_sample_counts",
    ):
        values = ", ".join(f"{item['value']}={item['count']}" for item in report[key][:8])
        lines.append(f"- `{key}`: {values if values else 'none'}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", nargs="?", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--coverage-json", type=Path, default=DEFAULT_COVERAGE_JSON)
    parser.add_argument("--visibility-json", type=Path, default=DEFAULT_VISIBILITY_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = summarize(args.log, args.coverage_json, args.visibility_json)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2), encoding="ascii")
    if args.write_markdown:
        write_markdown(report, args.write_markdown)
    print(f"overall: {'PASS' if report['passed'] else 'FAIL'}")
    print(f"interpretation: {report['interpretation']}")
    print(f"blocker: {report['blocker']}")
    if args.require_pass and not report["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
