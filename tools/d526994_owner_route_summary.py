#!/usr/bin/env python3
"""Summarize Clash95 dword_526994 owner-route CDB probe logs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


MARKERS = (
    "D526994_ROUTE_PLAYGAME_SETUP_40A400",
    "D526994_ROUTE_FORCE_423B40",
    "D526994_ROUTE_40A490_ENTRY",
    "D526994_ROUTE_40A490_CALL_40A500",
    "D526994_ROUTE_40A500_ENTRY",
    "D526994_ROUTE_423B40_CALL",
    "D526994_ROUTE_423B00_CALL",
    "D526994_ROUTE_423760_CALL",
    "D526994_OWNER_423760_ENTRY",
    "D526994_OWNER_423B00_ENTRY",
    "D526994_OWNER_423B40_ENTRY",
    "D526994_ROUTE_CALLBACK_TEST",
)

OWNER_MARKERS = (
    "D526994_OWNER_423760_ENTRY",
    "D526994_OWNER_423B00_ENTRY",
    "D526994_OWNER_423B40_ENTRY",
)

SURFDUMP_MARKERS = (
    "SURFDUMP_MAIN_HIT",
    "SURFDUMP_PLAYGAME",
    "SURFDUMP_REDRAW",
    "SURFDUMP_READY",
    "SURFDUMP_HOST_READY",
    "SURFDUMP_DONE",
    "AV_SURFDUMP",
)

VALUE_PATTERNS = {
    "flag526994": re.compile(r"flag526994=([0-9a-fA-F`]+)"),
    "flag_before": re.compile(r"flag_before=([0-9a-fA-F`]+)"),
    "callback": re.compile(r"callback=([0-9a-fA-F`]+)"),
    "selected": re.compile(r"selected(?:_before)?=(-?\d+)"),
    "prior": re.compile(r"prior(?:_before)?=(-?\d+)"),
}


def collect_values(lines: list[str]) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {key: [] for key in VALUE_PATTERNS}
    for line in lines:
        for key, pattern in VALUE_PATTERNS.items():
            match = pattern.search(line)
            if match:
                values[key].append(match.group(1).replace("`", ""))
    return values


def summarize_log(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    marker_lines = {
        marker: [line for line in lines if marker in line]
        for marker in MARKERS
    }
    surf_lines = {
        marker: [line for line in lines if marker in line]
        for marker in SURFDUMP_MARKERS
    }
    owner_count = sum(len(marker_lines[marker]) for marker in OWNER_MARKERS)
    route_count = sum(len(marker_lines[marker]) for marker in MARKERS if marker.startswith("D526994_ROUTE_"))
    av_count = len(surf_lines["AV_SURFDUMP"])
    return {
        "log": str(path),
        "marker_counts": {marker: len(rows) for marker, rows in marker_lines.items()},
        "surface_counts": {marker: len(rows) for marker, rows in surf_lines.items()},
        "owner_count": owner_count,
        "route_count": route_count,
        "av_count": av_count,
        "values": collect_values(lines),
        "first_owner_line": next(
            (row for marker in OWNER_MARKERS for row in marker_lines[marker]),
            "",
        ),
        "first_force_line": marker_lines["D526994_ROUTE_FORCE_423B40"][0]
        if marker_lines["D526994_ROUTE_FORCE_423B40"]
        else "",
        "ready": bool(surf_lines["SURFDUMP_READY"]),
    }


def write_markdown(path: Path, summary: dict[str, object]) -> None:
    counts = summary["marker_counts"]
    surface_counts = summary["surface_counts"]
    values = summary["values"]
    lines = [
        "# dword_526994 Owner Route Summary",
        "",
        f"- Log: `{summary['log']}`",
        f"- Ready: {summary['ready']}",
        f"- Owner entries: {summary['owner_count']}",
        f"- Route rows: {summary['route_count']}",
        f"- AV rows: {summary['av_count']}",
        f"- First forced route: `{summary['first_force_line'] or 'not observed'}`",
        f"- First owner: `{summary['first_owner_line'] or 'not observed'}`",
        "",
        "## Marker Counts",
    ]
    for marker in MARKERS:
        lines.append(f"- {marker}: {counts[marker]}")
    lines.extend(["", "## Surface Counts"])
    for marker in SURFDUMP_MARKERS:
        lines.append(f"- {marker}: {surface_counts[marker]}")
    lines.extend(["", "## Observed Values"])
    for key, observed in values.items():
        unique = sorted(set(observed))
        lines.append(f"- {key}: {', '.join(unique) if unique else 'none'}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="CDB log to summarize")
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--require-owner", action="store_true")
    args = parser.parse_args(argv)

    summary = summarize_log(args.log)
    if args.write_json:
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_md:
        write_markdown(args.write_md, summary)

    print(
        "owner_count={owner_count} route_count={route_count} ready={ready} av_count={av_count}".format(
            **summary
        )
    )
    first_owner = summary["first_owner_line"]
    if first_owner:
        print(first_owner)
    if args.require_owner and int(summary["owner_count"]) <= 0:
        print("ERROR: no D526994_OWNER_* entries found", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
