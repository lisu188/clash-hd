#!/usr/bin/env python3
"""Validate the debugger-only post-owner forced-visible seven-cell proof.

This gate is deliberately narrow. It proves that the current HD map path fills
the seven previously blank post-owner cells when CDB temporarily sets only
their save-visibility bits. It must not be treated as a gameplay patch or a
reason to reveal fog in normal play.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REQUIRED_CELLS = ("r6c10", "r6c11", "r7c10", "r7c11", "r8c0", "r8c10", "r8c11")

FORCE_RE = re.compile(r"APPOST_FORCE_VISIBLE_SEVEN timing=playgame")
FORCE_DONE_RE = re.compile(r"APPOST_FORCE_VISIBLE_SEVEN_DONE timing=playgame")
ACTION_RE = re.compile(r"APPOST_ACTION_CALL ")
READY_RE = re.compile(r"APPOST_SURFDUMP_READY ")
APVIS_RE = re.compile(
    r"APVIS_CELL "
    r"id=(?P<id>\S+) "
    r"screen=\((?P<screenx>-?\d+),(?P<screeny>-?\d+)\) "
    r"map=\((?P<mapx>-?\d+),(?P<mapy>-?\d+)\) "
    r"byte=(?P<byte>[0-9a-fA-F]{2}) "
    r"mask=(?P<mask>[0-9a-fA-F]{2}) "
    r"hit=(?P<hit>[0-9a-fA-F]{2}) "
    r"sample=(?P<sample>[0-9a-fA-F]{2}) "
    r"center_sample=(?P<center>[0-9a-fA-F]{2})"
)


def load_coverage(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def first_image(coverage: dict[str, Any]) -> dict[str, Any]:
    images = coverage.get("images") or []
    return images[0] if images else {}


def parse_log(path: Path) -> dict[str, Any]:
    rows: dict[str, Any] = {
        "force_rows": 0,
        "force_done_rows": 0,
        "action_rows": 0,
        "ready_rows": 0,
        "apvis": {},
    }
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if FORCE_RE.search(line):
            rows["force_rows"] += 1
        if FORCE_DONE_RE.search(line):
            rows["force_done_rows"] += 1
        if ACTION_RE.search(line):
            rows["action_rows"] += 1
        if READY_RE.search(line):
            rows["ready_rows"] += 1
        match = APVIS_RE.search(line)
        if match:
            cell_id = match.group("id")
            rows["apvis"][cell_id] = {
                "line_no": line_no,
                "screen": [int(match.group("screenx")), int(match.group("screeny"))],
                "map": [int(match.group("mapx")), int(match.group("mapy"))],
                "byte": match.group("byte").lower(),
                "mask": match.group("mask").lower(),
                "hit": match.group("hit").lower(),
                "sample": match.group("sample").lower(),
                "center_sample": match.group("center").lower(),
            }
    return rows


def summarize(coverage_path: Path, log_path: Path, required_cells: tuple[str, ...]) -> dict[str, Any]:
    coverage = load_coverage(coverage_path)
    image = first_image(coverage)
    summary = image.get("summary") or {}
    frame_check = image.get("frame_check") or {}
    log = parse_log(log_path)
    blank_active_cells = list(summary.get("blank_active_cells") or [])
    stale_cells = list(summary.get("possible_stale_or_solid_active_cells") or [])
    apvis = log["apvis"]
    missing = [cell for cell in required_cells if cell not in apvis]
    zero_hit = [cell for cell in required_cells if cell in apvis and apvis[cell]["hit"] == "00"]
    still_blank = [cell for cell in required_cells if cell in blank_active_cells]
    failures: list[str] = []

    if not frame_check.get("gameplay_frame_likely"):
        failures.append("gameplay_frame_likely is false")
    if not log["force_rows"]:
        failures.append("APPOST_FORCE_VISIBLE_SEVEN was not logged")
    if not log["force_done_rows"]:
        failures.append("APPOST_FORCE_VISIBLE_SEVEN_DONE was not logged")
    if not log["action_rows"]:
        failures.append("APPOST_ACTION_CALL was not logged")
    if not log["ready_rows"]:
        failures.append("APPOST_SURFDUMP_READY was not logged")
    if missing:
        failures.append("missing APVIS_CELL rows: " + ", ".join(missing))
    if zero_hit:
        failures.append("forced cells still have zero visibility hits: " + ", ".join(zero_hit))
    if still_blank:
        failures.append("forced cells still blank in coverage: " + ", ".join(still_blank))
    if blank_active_cells:
        failures.append("blank active cells remain: " + ", ".join(blank_active_cells))
    if stale_cells:
        failures.append("possible stale/solid active cells remain: " + ", ".join(stale_cells))

    return {
        "coverage_json": str(coverage_path),
        "log": str(log_path),
        "required_cells": list(required_cells),
        "gameplay_frame_likely": bool(frame_check.get("gameplay_frame_likely")),
        "active_cells": int(summary.get("active_cells") or 0),
        "measurable_active_cells": int(summary.get("measurable_active_cells") or 0),
        "blank_active_cells": blank_active_cells,
        "possible_stale_or_solid_active_cells": stale_cells,
        "force_rows": log["force_rows"],
        "force_done_rows": log["force_done_rows"],
        "action_rows": log["action_rows"],
        "ready_rows": log["ready_rows"],
        "apvis_cells": {cell: apvis[cell] for cell in required_cells if cell in apvis},
        "missing_cells": missing,
        "zero_hit_cells": zero_hit,
        "still_blank_cells": still_blank,
        "failures": failures,
        "passed": not failures,
    }


def print_report(report: dict[str, Any]) -> None:
    print(f"coverage: {report['coverage_json']}")
    print(f"log: {report['log']}")
    print(f"passed: {report['passed']}")
    print(f"gameplay_frame_likely: {report['gameplay_frame_likely']}")
    print(f"blank_active_cells: {', '.join(report['blank_active_cells']) if report['blank_active_cells'] else '-'}")
    print(
        "markers: force={force_rows} done={force_done_rows} action={action_rows} ready={ready_rows}".format(
            **report
        )
    )
    print(f"missing_cells: {', '.join(report['missing_cells']) if report['missing_cells'] else '-'}")
    print(f"zero_hit_cells: {', '.join(report['zero_hit_cells']) if report['zero_hit_cells'] else '-'}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  {failure}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage_json", type=Path)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--require-post-owner-forced-visible", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = summarize(args.coverage_json, args.log, REQUIRED_CELLS)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print_report(report)
    if args.require_post_owner_forced_visible and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
