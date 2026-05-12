#!/usr/bin/env python3
"""Summarize Clash95 CDB descriptor-trace logs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


MARKERS = (
    "DESC_40A400_ENTRY",
    "DESC_40A400_CALL_419D80",
    "DESC_40A400_AFTER_419D80",
    "DESC_SINGLE_419D60_ENTRY",
    "DESC_419D80_ENTRY",
    "DESC_SCAN",
    "DESC_SKIP_X640",
    "DESC_DRAW",
    "DESC_DRAWCALL_4191F0",
    "DESC_DRAWCALL_4191F0_PRESENT1",
    "DESC_DRAWCALL_4191F0_PRESENT2",
    "DESC_PRESENT_4191F0",
    "DESC_419DC0_ENTRY",
    "DESC_419DC0_SWITCH_TO_MAP",
    "DESC_419DC0_RESTORE_META",
    "SURFDUMP_PLAYGAME",
    "SURFDUMP_READY",
    "AV_SURFDUMP",
)

SCAN_RE = re.compile(
    r"DESC_SCAN ptr=(?P<ptr>\S+) x=(?P<x>-?\d+) y=(?P<y>-?\d+) "
    r"flags=0x(?P<flags>[0-9a-fA-F]+) draw=(?P<draw>\S+) hit=(?P<hit>\S+) "
    r"data=(?P<data>\S+) next=(?P<next>\S+) is511d40=(?P<is511d40>\d+)"
)
DRAW_RE = re.compile(
    r"DESC_DRAW ptr=(?P<ptr>\S+) x=(?P<x>-?\d+) y=(?P<y>-?\d+) "
    r"flags=0x(?P<flags>[0-9a-fA-F]+) draw=(?P<draw>\S+) hit=(?P<hit>\S+).*"
    r"is511d40=(?P<is511d40>\d+)"
)
CALL_RE = re.compile(
    r"DESC_DRAWCALL_4191F0 ret=(?P<ret>\S+) desc=(?P<desc>\S+) "
    r"x=(?P<x>-?\d+) y=(?P<y>-?\d+) flags=0x(?P<flags>[0-9a-fA-F]+) "
    r"sprite=(?P<sprite>\S+) draw_index=(?P<draw_index>-?\d+) "
    r"alt_index=(?P<alt_index>-?\d+) render=(?P<render>\S+) map_surface=(?P<map_surface>\S+)"
)


def as_int(value: str) -> int:
    return int(value, 0)


def convert(match: re.Match[str], line_no: int) -> dict[str, Any]:
    row: dict[str, Any] = {"line_no": line_no}
    for key, value in match.groupdict().items():
        if key in {"x", "y", "draw_index", "alt_index", "is511d40"}:
            row[key] = as_int(value)
        elif key == "flags":
            row[key] = int(value, 16)
        else:
            row[key] = value.replace("`", "")
    return row


def summarize_log(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    marker_counts = {marker: 0 for marker in MARKERS}
    scans: list[dict[str, Any]] = []
    draws: list[dict[str, Any]] = []
    drawcalls: list[dict[str, Any]] = []
    skip_lines: list[str] = []

    for line_no, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        for marker in MARKERS:
            if stripped == marker or stripped.startswith(marker + " "):
                marker_counts[marker] += 1
        if "DESC_SKIP_X640" in line:
            skip_lines.append(line.strip())
        scan = SCAN_RE.search(line)
        if scan:
            scans.append(convert(scan, line_no))
        draw = DRAW_RE.search(line)
        if draw:
            draws.append(convert(draw, line_no))
        call = CALL_RE.search(line)
        if call:
            drawcalls.append(convert(call, line_no))

    draw_callbacks = Counter(row["draw"] for row in scans)
    drawn_callbacks = Counter(row["draw"] for row in draws)
    scanned_511d40 = [row for row in scans if row.get("is511d40")]
    drawn_511d40 = [row for row in draws if row.get("is511d40")]
    skipped_511d40 = [
        line for line in skip_lines if "is511d40=1" in line
    ]

    classification: list[str] = []
    if marker_counts["DESC_40A400_ENTRY"] and marker_counts["DESC_419D80_ENTRY"]:
        classification.append("sub_40A400 reached descriptor drawer")
    if scanned_511d40 and not skipped_511d40:
        classification.append("dword_511D40 entries were scanned without x>=640 skips")
    if drawn_511d40:
        classification.append("dword_511D40 entries reached their draw callbacks")
    if marker_counts["DESC_PRESENT_4191F0"] == 0 and marker_counts["DESC_DRAWCALL_4191F0"]:
        classification.append("generic descriptor draw ran but no direct 004024E0 helper call was observed")
    if marker_counts["AV_SURFDUMP"]:
        classification.append("AV observed")

    return {
        "log": str(path),
        "marker_counts": marker_counts,
        "scans": scans,
        "draws": draws,
        "drawcalls": drawcalls,
        "skip_lines": skip_lines,
        "scanned_511d40_count": len(scanned_511d40),
        "drawn_511d40_count": len(drawn_511d40),
        "skipped_511d40_count": len(skipped_511d40),
        "draw_callbacks": dict(draw_callbacks),
        "drawn_callbacks": dict(drawn_callbacks),
        "classification": classification,
        "ready": marker_counts["SURFDUMP_READY"] > 0,
        "av_count": marker_counts["AV_SURFDUMP"],
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Descriptor Trace Summary",
        "",
        f"- Log: `{summary['log']}`",
        f"- Ready: {summary['ready']}",
        f"- AV rows: {summary['av_count']}",
        f"- Scanned `dword_511D40` entries: {summary['scanned_511d40_count']}",
        f"- Drawn `dword_511D40` entries: {summary['drawn_511d40_count']}",
        f"- Skipped `dword_511D40` entries: {summary['skipped_511d40_count']}",
        "",
        "## Classification",
    ]
    if summary["classification"]:
        lines.extend(f"- {item}" for item in summary["classification"])
    else:
        lines.append("- no descriptor classification available")

    lines.extend(["", "## Marker Counts"])
    for marker in MARKERS:
        lines.append(f"- {marker}: {summary['marker_counts'][marker]}")

    lines.extend(["", "## Draw Callbacks"])
    callbacks = summary["draw_callbacks"]
    if callbacks:
        for callback, count in sorted(callbacks.items()):
            lines.append(f"- {callback}: scanned {count}, drawn {summary['drawn_callbacks'].get(callback, 0)}")
    else:
        lines.append("- none")

    lines.extend(["", "## First Drawn Descriptors"])
    for row in summary["draws"][:12]:
        lines.append(
            "- ptr={ptr} x={x} y={y} flags=0x{flags:02x} draw={draw} hit={hit} is511d40={is511d40}".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--require-drawn-511d40", action="store_true")
    args = parser.parse_args(argv)

    summary = summarize_log(args.log)
    if args.write_json:
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_md:
        write_markdown(args.write_md, summary)

    print(
        "ready={ready} av_count={av_count} scanned_511d40={scanned_511d40_count} drawn_511d40={drawn_511d40_count} skipped_511d40={skipped_511d40_count}".format(
            **summary
        )
    )
    for item in summary["classification"]:
        print(f"- {item}")
    if args.require_ready and not summary["ready"]:
        print("ERROR: SURFDUMP_READY not observed", file=sys.stderr)
        return 1
    if args.require_drawn_511d40 and summary["drawn_511d40_count"] <= 0:
        print("ERROR: no dword_511D40 descriptor draw observed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
