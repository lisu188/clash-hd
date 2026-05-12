#!/usr/bin/env python3
"""Gate Clash95 no-popup forced-visible surface-dump evidence.

This is intentionally narrow: it validates the debugger-only
`run_cdb_surface_dump.ps1 -ForceVisibleEdges` proof for the load-slot-0
viewport. It is not a gameplay visibility rule and must not be used to justify
forcing fog/reveal behavior in normal play.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


VISDUMP_RE = re.compile(
    r"SCROLL_VISDUMP "
    r"player=(?P<player>-?\d+) "
    r"screen0=\((?P<screenx>-?\d+),(?P<screeny>-?\d+)\) "
    r"map0=\((?P<mapx>-?\d+),(?P<mapy>-?\d+)\) "
    r"rows=(?P<rows>\d+) "
    r"cols=(?P<cols>\d+) "
    r"tile=\((?P<tilex>\d+),(?P<tiley>\d+)\)"
)
READY_RE = re.compile(
    r"SURFDUMP_READY "
    r"redraw_seq=(?P<redraw>\d+) "
    r"surface=(?P<surface>[0-9a-fA-F`]+) "
    r"size=\((?P<width>\d+),(?P<height>\d+)\) "
    r"base=(?P<base>[0-9a-fA-F`]+) "
    r"bytes=(?P<bytes>\d+)"
)
VEDGE_VISRET_RE = re.compile(
    r"SURFDUMP_VEDGE_VISRET seq=(?P<seq>\d+) "
    r"screen=\((?P<screenx>-?\d+),(?P<screeny>-?\d+)\) "
    r"center=\((?P<centerx>-?\d+),(?P<centery>-?\d+)\) "
    r"vis=(?P<vis>-?\d+)"
)
VEDGE_POST_RE = re.compile(
    r"SURFDUMP_VEDGE_POST seq=(?P<seq>\d+) "
    r"ret=(?P<ret>[0-9a-fA-F`]+) "
    r"screen=\((?P<screenx>-?\d+),(?P<screeny>-?\d+)\) "
    r"sample=(?P<sample>[0-9a-fA-F]{2})"
)
FORCE_RE = re.compile(r"SURFDUMP_FORCE_VISIBLE_EDGES")
VIEWPORT_RE = re.compile(r"SURFDUMP_FORCE_VIEWPORT")


def load_coverage(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def first_image(coverage: dict[str, Any]) -> dict[str, Any]:
    images = coverage.get("images") or []
    return images[0] if images else {}


def parse_pair(value: str) -> tuple[int, int]:
    try:
        left, right = value.split(",", 1)
        return int(left), int(right)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a pair like 10,17") from exc


def parse_log(path: Path) -> dict[str, Any]:
    rows: dict[str, Any] = {
        "ready": [],
        "visdump": [],
        "vedge_visret": [],
        "vedge_post": [],
        "force_visible_edges_rows": 0,
        "force_viewport_rows": 0,
    }
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if READY_RE.search(line):
            match = READY_RE.search(line)
            assert match is not None
            rows["ready"].append(
                {
                    "line_no": line_no,
                    "redraw_seq": int(match.group("redraw")),
                    "surface": match.group("surface").lower().replace("`", ""),
                    "width": int(match.group("width")),
                    "height": int(match.group("height")),
                    "base": match.group("base").lower().replace("`", ""),
                    "bytes": int(match.group("bytes")),
                }
            )
            continue
        if VISDUMP_RE.search(line):
            match = VISDUMP_RE.search(line)
            assert match is not None
            rows["visdump"].append(
                {
                    "line_no": line_no,
                    "player": int(match.group("player")),
                    "screen0": [int(match.group("screenx")), int(match.group("screeny"))],
                    "map0": [int(match.group("mapx")), int(match.group("mapy"))],
                    "rows": int(match.group("rows")),
                    "cols": int(match.group("cols")),
                    "tile": [int(match.group("tilex")), int(match.group("tiley"))],
                }
            )
            continue
        if VEDGE_VISRET_RE.search(line):
            match = VEDGE_VISRET_RE.search(line)
            assert match is not None
            rows["vedge_visret"].append(
                {
                    "line_no": line_no,
                    "seq": int(match.group("seq")),
                    "screen": [int(match.group("screenx")), int(match.group("screeny"))],
                    "center": [int(match.group("centerx")), int(match.group("centery"))],
                    "vis": int(match.group("vis")),
                }
            )
            continue
        if VEDGE_POST_RE.search(line):
            match = VEDGE_POST_RE.search(line)
            assert match is not None
            rows["vedge_post"].append(
                {
                    "line_no": line_no,
                    "seq": int(match.group("seq")),
                    "ret": match.group("ret").lower().replace("`", ""),
                    "screen": [int(match.group("screenx")), int(match.group("screeny"))],
                    "sample": match.group("sample").lower(),
                }
            )
            continue
        if FORCE_RE.search(line):
            rows["force_visible_edges_rows"] += 1
            continue
        if VIEWPORT_RE.search(line):
            rows["force_viewport_rows"] += 1
            continue
    return rows


def summarize(
    coverage_path: Path,
    log_path: Path,
    expect_map0: tuple[int, int],
    expect_visret: int,
    expect_post: int,
) -> dict[str, Any]:
    coverage = load_coverage(coverage_path)
    image = first_image(coverage)
    summary = image.get("summary") or {}
    frame_check = image.get("frame_check") or {}
    log = parse_log(log_path)
    latest_visdump = log["visdump"][-1] if log["visdump"] else None
    report = {
        "coverage_json": str(coverage_path),
        "log": str(log_path),
        "expect_map0": list(expect_map0),
        "expect_vedge_visret": expect_visret,
        "expect_vedge_post": expect_post,
        "gameplay_frame_likely": bool(frame_check.get("gameplay_frame_likely")),
        "blank_active_cells": list(summary.get("blank_active_cells") or []),
        "possible_stale_or_solid_active_cells": list(
            summary.get("possible_stale_or_solid_active_cells") or []
        ),
        "active_cells": int(summary.get("active_cells") or 0),
        "measurable_active_cells": int(summary.get("measurable_active_cells") or 0),
        "ready_count": len(log["ready"]),
        "visdump_count": len(log["visdump"]),
        "latest_visdump": latest_visdump,
        "force_visible_edges_rows": log["force_visible_edges_rows"],
        "force_viewport_rows": log["force_viewport_rows"],
        "vedge_visret_count": len(log["vedge_visret"]),
        "vedge_post_count": len(log["vedge_post"]),
        "vedge_visret_unique_seq_count": len({row["seq"] for row in log["vedge_visret"]}),
        "vedge_post_unique_seq_count": len({row["seq"] for row in log["vedge_post"]}),
        "vedge_visret_nonzero_count": sum(1 for row in log["vedge_visret"] if row["vis"] != 0),
        "vedge_post_nonblack_count": sum(1 for row in log["vedge_post"] if row["sample"] != "00"),
        "first_vedge_visret": log["vedge_visret"][:1],
        "first_vedge_post": log["vedge_post"][:1],
        "failures": [],
    }
    failures = report["failures"]
    if not report["gameplay_frame_likely"]:
        failures.append("gameplay_frame_likely is false")
    if report["blank_active_cells"]:
        failures.append("blank active cells remain: " + ", ".join(report["blank_active_cells"]))
    if report["possible_stale_or_solid_active_cells"]:
        failures.append(
            "stale/solid active cells remain: "
            + ", ".join(report["possible_stale_or_solid_active_cells"])
        )
    if not latest_visdump:
        failures.append("SCROLL_VISDUMP was not logged")
    elif tuple(latest_visdump["map0"]) != expect_map0:
        failures.append(f"latest SCROLL_VISDUMP map0={latest_visdump['map0']} expected={list(expect_map0)}")
    if not report["force_visible_edges_rows"]:
        failures.append("SURFDUMP_FORCE_VISIBLE_EDGES was not logged")
    if not report["force_viewport_rows"]:
        failures.append("SURFDUMP_FORCE_VIEWPORT was not logged")
    if report["vedge_visret_count"] != expect_visret:
        failures.append(f"SURFDUMP_VEDGE_VISRET count={report['vedge_visret_count']} expected={expect_visret}")
    if report["vedge_post_count"] != expect_post:
        failures.append(f"SURFDUMP_VEDGE_POST count={report['vedge_post_count']} expected={expect_post}")
    if report["vedge_visret_nonzero_count"] != report["vedge_visret_count"]:
        failures.append("one or more SURFDUMP_VEDGE_VISRET rows returned zero visibility")
    if report["vedge_post_nonblack_count"] != report["vedge_post_count"]:
        failures.append("one or more SURFDUMP_VEDGE_POST samples remained 00")
    report["passed"] = not failures
    return report


def print_report(report: dict[str, Any]) -> None:
    print(f"coverage: {report['coverage_json']}")
    print(f"log: {report['log']}")
    print(f"passed: {report['passed']}")
    print(f"gameplay_frame_likely: {report['gameplay_frame_likely']}")
    print("blank_active_cells: " + (", ".join(report["blank_active_cells"]) if report["blank_active_cells"] else "-"))
    print(f"latest_visdump: {report['latest_visdump']}")
    print(
        "vedge: visret={vedge_visret_count}/{expect_vedge_visret} "
        "post={vedge_post_count}/{expect_vedge_post} "
        "visret_nonzero={vedge_visret_nonzero_count} "
        "post_nonblack={vedge_post_nonblack_count}".format(**report)
    )
    print(
        "markers: force_visible_edges={force_visible_edges_rows} "
        "force_viewport={force_viewport_rows}".format(**report)
    )
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  {failure}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage_json", type=Path)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--expect-map0", type=parse_pair, default=(10, 17))
    parser.add_argument("--expect-vedge-visret", type=int, default=54)
    parser.add_argument("--expect-vedge-post", type=int, default=54)
    parser.add_argument("--require-forced-visible", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = summarize(
        args.coverage_json,
        args.log,
        args.expect_map0,
        args.expect_vedge_visret,
        args.expect_vedge_post,
    )
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2), encoding="ascii")
    print_report(report)
    if args.require_forced_visible and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
