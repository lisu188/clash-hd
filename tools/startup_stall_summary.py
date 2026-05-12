#!/usr/bin/env python3
"""Summarize Clash95 startup-stall and dword_526994 CDB probe logs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


MARKERS = (
    "STARTUP_STARTMENU_ENTRY",
    "STARTUP_CALL_UI_STARTANIMS",
    "STARTUP_UI_STARTANIMS_ENTRY",
    "STARTUP_UI_DD_PUMP_BEFORE_SLEEP",
    "STARTUP_UI_SLEEP_1200",
    "STARTUP_UI_AFTER_SLEEP_BEFORE_LOGO",
    "STARTUP_UI_AVI_CALL",
    "STARTUP_UI_AVI_RETURN",
    "STARTUP_UI_ANIMS_AFTER_AVI_BRANCH",
    "STARTUP_UI_STARTANIMS_RETURN",
    "STARTUP_AFTER_UI_STARTANIMS",
    "STARTUP_MAIN_DISPATCH_REACHED",
    "STARTUP_VIDEO_IN_ENTRY",
    "STARTUP_VIDEO_AFTER_MODE_BEGIN",
    "STARTUP_VIDEO_OUT_LOG",
    "STARTUP_AVI_THREAD_SLEEP",
    "STARTUP_AUDIO_THREAD_SLEEP",
    "STARTUP_CSS_ISPLAYING_ENTRY",
    "STARTUP_SAMPLECACHE_SLEEP",
    "D526994_OWNER_423760_ENTRY",
    "D526994_OWNER_423B00_ENTRY",
    "D526994_OWNER_423B40_ENTRY",
    "D526994_MIN_CALLBACK_TEST",
    "SURFDUMP_MAIN_HIT",
    "SURFDUMP_LOAD_COORD",
    "SURFDUMP_LOADSAVE",
    "SURFDUMP_PLAYGAME",
    "SURFDUMP_READY",
    "AV_SURFDUMP",
)

KEY_VALUE_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)=(?P<value>\([^)]+\)|\S+)")


def parse_log(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    marker_counts = {marker: 0 for marker in MARKERS}
    rows: list[dict[str, Any]] = []

    for line_no, line in enumerate(text.splitlines(), start=1):
        matched_marker = None
        for marker in MARKERS:
            if marker in line:
                marker_counts[marker] += 1
                matched_marker = marker
                break
        if not matched_marker:
            continue
        row: dict[str, Any] = {"line_no": line_no, "kind": matched_marker, "raw": line.strip()}
        for match in KEY_VALUE_RE.finditer(line):
            row[match.group("key")] = match.group("value")
        rows.append(row)

    startup_rows = [row for row in rows if row["kind"].startswith("STARTUP_")]
    d526994_rows = [row for row in rows if row["kind"].startswith("D526994_")]
    route_rows = [
        row
        for row in rows
        if row["kind"].startswith("SURFDUMP_") or row["kind"] == "AV_SURFDUMP"
    ]
    last_row = rows[-1] if rows else None
    last_startup_row = startup_rows[-1] if startup_rows else None
    last_route_row = route_rows[-1] if route_rows else None

    return {
        "log": str(path),
        "marker_counts": marker_counts,
        "row_counts": {
            "startup_rows": len(startup_rows),
            "d526994_rows": len(d526994_rows),
            "route_rows": len(route_rows),
            "main_hits": marker_counts["SURFDUMP_MAIN_HIT"],
            "playgame": marker_counts["SURFDUMP_PLAYGAME"],
            "ready": marker_counts["SURFDUMP_READY"],
            "av": marker_counts["AV_SURFDUMP"],
            "owner_423760": marker_counts["D526994_OWNER_423760_ENTRY"],
            "owner_423b00": marker_counts["D526994_OWNER_423B00_ENTRY"],
            "owner_423b40": marker_counts["D526994_OWNER_423B40_ENTRY"],
            "callback_tests": marker_counts["D526994_MIN_CALLBACK_TEST"],
        },
        "last_row": last_row,
        "last_startup_row": last_startup_row,
        "last_route_row": last_route_row,
        "rows": rows,
    }


def write_markdown(summary: dict[str, Any], path: Path, screenshot: str | None) -> None:
    lines = [
        "# Startup Stall CDB Summary",
        "",
        f"- Log: `{summary['log']}`",
        f"- Row counts: `{summary['row_counts']}`",
        f"- Last startup row: `{summary['last_startup_row']}`",
        f"- Last route row: `{summary['last_route_row']}`",
        f"- Last observed row: `{summary['last_row']}`",
    ]
    if screenshot:
        lines.extend(["", f"![surface]({screenshot})"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Clash95 startup-stall CDB probe logs.")
    parser.add_argument("--log", required=True, type=Path, help="CDB log path")
    parser.add_argument("--screenshot", help="optional surface PNG path for Markdown reports")
    parser.add_argument("--write-json", type=Path, help="write JSON summary")
    parser.add_argument("--write-markdown", type=Path, help="write Markdown summary")
    parser.add_argument("--require-startup", action="store_true", help="exit 2 unless startup rows exist")
    args = parser.parse_args()

    summary = parse_log(args.log)
    if args.write_json:
        args.write_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.write_markdown:
        write_markdown(summary, args.write_markdown, args.screenshot)

    print(f"log: {summary['log']}")
    print(f"row_counts: {summary['row_counts']}")
    print(f"last_startup_row: {summary['last_startup_row']}")
    print(f"last_route_row: {summary['last_route_row']}")
    print(f"last_row: {summary['last_row']}")

    if args.require_startup and summary["row_counts"]["startup_rows"] <= 0:
        print("error: no STARTUP_* rows were observed")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
