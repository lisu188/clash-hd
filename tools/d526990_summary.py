#!/usr/bin/env python3
"""Summarize Clash95 dword_526990 CDB callback probe logs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


MARKERS = (
    "D526990_WRITE",
    "D526990_SETUP_WRITE",
    "D526994_WRITE",
    "D526994_OWNER_423760_ENTRY",
    "D526994_OWNER_423760_SET1",
    "D526994_OWNER_423760_REDRAW1",
    "D526994_OWNER_423760_RESTORE",
    "D526994_OWNER_423760_REDRAW2",
    "D526994_OWNER_423B00_ENTRY",
    "D526994_OWNER_423B00_SET1",
    "D526994_OWNER_423B00_REDRAW",
    "D526994_OWNER_423B40_ENTRY",
    "D526994_OWNER_423B40_CLEAR",
    "D526994_OWNER_423B40_REDRAW",
    "D526994_SETUP_CALLBACK_TEST",
    "D526994_SETUP_FALLBACK_START",
    "D526994_MIN_CALLBACK_TEST",
    "D526990_FULLREDRAW_ENTER",
    "D526990_SECOND_PASS_CHECK",
    "D526990_FALLBACK_LOOP_START",
    "D526990_FALLBACK_LOOP_DONE",
    "D526990_CALLBACK_TEST",
    "D526990_CALLBACK_CALL",
    "D526990_CALLBACK_AFTER",
    "SURFDUMP_PLAYGAME",
    "SURFDUMP_READY",
    "AV_SURFDUMP",
)

KEY_VALUE_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)=(?P<value>\([^)]+\)|\S+)")


def parse_log(path: Path) -> dict[str, Any]:
    marker_counts = {marker: 0 for marker in MARKERS}
    rows: list[dict[str, Any]] = []

    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
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

    callback_values = sorted(
        {
            str(row.get("callback"))
            for row in rows
            if row.get("callback") not in (None, "00000000", "0")
        }
    )
    write_values = [
        str(row.get("value") or row.get("callback"))
        for row in rows
        if row["kind"] in {"D526990_WRITE", "D526990_SETUP_WRITE"} and (row.get("value") or row.get("callback"))
    ]
    flag_values = sorted(
        {
            str(row.get("flag526994"))
            for row in rows
            if row.get("flag526994") not in (None, "")
        }
    )

    return {
        "log": str(path),
        "marker_counts": marker_counts,
        "row_counts": {
            "d526990_rows": sum(1 for row in rows if row["kind"].startswith("D526990_")),
            "d526994_rows": sum(1 for row in rows if row["kind"].startswith("D526994_")),
            "writes": marker_counts["D526990_WRITE"] + marker_counts["D526990_SETUP_WRITE"],
            "d526994_writes": marker_counts["D526994_WRITE"],
            "owner_423760_entries": marker_counts["D526994_OWNER_423760_ENTRY"],
            "owner_423b00_entries": marker_counts["D526994_OWNER_423B00_ENTRY"],
            "owner_423b40_entries": marker_counts["D526994_OWNER_423B40_ENTRY"],
            "fullredraw_entries": marker_counts["D526990_FULLREDRAW_ENTER"],
            "callback_tests": (
                marker_counts["D526990_CALLBACK_TEST"]
                + marker_counts["D526994_SETUP_CALLBACK_TEST"]
                + marker_counts["D526994_MIN_CALLBACK_TEST"]
            ),
            "callback_calls": marker_counts["D526990_CALLBACK_CALL"],
            "fallback_starts": marker_counts["D526990_FALLBACK_LOOP_START"] + marker_counts["D526994_SETUP_FALLBACK_START"],
            "fallback_done": marker_counts["D526990_FALLBACK_LOOP_DONE"],
            "surfdump_playgame": marker_counts["SURFDUMP_PLAYGAME"],
            "surfdump_ready": marker_counts["SURFDUMP_READY"],
            "av": marker_counts["AV_SURFDUMP"],
        },
        "callback_values": callback_values,
        "callback_nonzero_seen": bool(callback_values),
        "write_values": write_values,
        "flag526994_values": flag_values,
        "rows": rows,
    }


def write_markdown(summary: dict[str, Any], path: Path, screenshot: str | None) -> None:
    lines = [
        "# dword_526990 CDB Summary",
        "",
        f"- Log: `{summary['log']}`",
        f"- Row counts: `{summary['row_counts']}`",
        f"- Nonzero callback seen: `{summary['callback_nonzero_seen']}`",
        f"- Callback values: `{summary['callback_values']}`",
        f"- Write values: `{summary['write_values']}`",
        f"- `dword_526994` values: `{summary['flag526994_values']}`",
    ]
    if screenshot:
        lines.extend(["", f"![surface]({screenshot})"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Clash95 dword_526990 CDB probe logs.")
    parser.add_argument("--log", required=True, type=Path, help="CDB log path")
    parser.add_argument("--screenshot", help="optional surface PNG path for Markdown reports")
    parser.add_argument("--write-json", type=Path, help="write JSON summary")
    parser.add_argument("--write-markdown", type=Path, help="write Markdown summary")
    parser.add_argument("--require-ready", action="store_true", help="exit 2 unless SURFDUMP_READY exists")
    parser.add_argument("--require-callback-test", action="store_true", help="exit 2 unless callback test rows exist")
    args = parser.parse_args()

    summary = parse_log(args.log)
    if args.write_json:
        args.write_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.write_markdown:
        write_markdown(summary, args.write_markdown, args.screenshot)

    print(f"log: {summary['log']}")
    print(f"row_counts: {summary['row_counts']}")
    print(f"callback_values: {summary['callback_values']}")
    print(f"callback_nonzero_seen: {summary['callback_nonzero_seen']}")
    print(f"write_values: {summary['write_values']}")
    print(f"flag526994_values: {summary['flag526994_values']}")

    if args.require_ready and summary["row_counts"]["surfdump_ready"] <= 0:
        print("error: SURFDUMP_READY was not observed")
        return 2
    if args.require_callback_test and summary["row_counts"]["callback_tests"] <= 0:
        print("error: D526990_CALLBACK_TEST was not observed")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
