#!/usr/bin/env python3
"""Summarize Clash95 castle owner setup CDB probe logs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MARKERS = (
    "CASTLE_INVOKE_PLAYGAME",
    "CASTLE_SCREEN_FULL_ENTRY_422180",
    "CASTLE_SCREEN_OWNER_SET_422207",
    "CASTLE_SCREEN_READY_422674",
    "CASTLE_SCREEN_ENTRY_422020",
    "CASTLE_RENDERHOOK_DRAW_422020",
    "CASTLE_FORCE_HITTEST_254",
    "CASTLE_CMD99_SETUP_422709",
    "CASTLE_DESCRIPTOR_INSTALL_42257E",
    "CASTLE_FORCE_COMMAND99_CLICK",
    "CASTLE_CALLBACK_CALL_42262C",
    "CASTLE_OWNER_SETUP_433C20",
    "CASTLE_WRITE_532150",
    "CASTLE_WRITE_53214C",
    "CASTLE_WRITE_532154",
    "CASTLE_ACTION_4338E0_ENTRY",
    "CASTLE_ACTION_CALL_435BC0",
    "CASTLE_OWNER_435BC0_ENTRY",
    "CASTLE_SURFDUMP_READY",
    "SURFDUMP_PLAYGAME",
    "SURFDUMP_REDRAW",
    "SURFDUMP_READY",
    "SURFDUMP_HOST_READY",
    "SURFDUMP_DONE",
    "AV_SURFDUMP",
)

SETUP_MARKERS = {
    "CASTLE_CMD99_SETUP_422709",
    "CASTLE_DESCRIPTOR_INSTALL_42257E",
    "CASTLE_OWNER_SETUP_433C20",
}

OWNER_GLOBAL_MARKERS = {
    "CASTLE_OWNER_SETUP_433C20",
    "CASTLE_WRITE_532150",
    "CASTLE_WRITE_53214C",
    "CASTLE_WRITE_532154",
}

ACTION_MARKERS = {
    "CASTLE_ACTION_4338E0_ENTRY",
    "CASTLE_ACTION_CALL_435BC0",
    "CASTLE_OWNER_435BC0_ENTRY",
}

VALUE_RE = re.compile(
    r"(?P<key>ret|eip|esi|callback|owner_screen|owner_arg|owner|owner_flag|flags|"
    r"castle_index|current_player|hit_surface|map_surface|eax_index|eax_arg|"
    r"d526a64|d532150|d53214c|d532154|d532150_before|d53214c_before|"
    r"d532154_before|new|surface|base|bytes)="
    r"(?P<value>[-0-9a-fA-F`x]+)"
)
SURFACE_RE = re.compile(r"sz=\((?P<w>-?\d+),(?P<h>-?\d+)\)")


def marker_for_line(line: str) -> str | None:
    stripped = line.lstrip()
    for marker in MARKERS:
        if stripped == marker or stripped.startswith(marker + " "):
            return marker
    return None


def parse_values(line: str) -> dict[str, str]:
    return {
        match.group("key"): match.group("value").replace("`", "")
        for match in VALUE_RE.finditer(line)
    }


def parse_surface(line: str) -> list[int] | None:
    match = SURFACE_RE.search(line)
    if not match:
        return None
    return [int(match.group("w")), int(match.group("h"))]


def parse_log(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    marker_counts = {marker: 0 for marker in MARKERS}
    rows: list[dict[str, Any]] = []
    av_rows: list[dict[str, Any]] = []
    ready_line = 0
    playgame_line = 0

    for line_no, line in enumerate(lines, start=1):
        marker = marker_for_line(line)
        if marker:
            marker_counts[marker] += 1
            row: dict[str, Any] = {
                "line_no": line_no,
                "marker": marker,
                "line": line.lstrip(),
                "values": parse_values(line),
            }
            surface_size = parse_surface(line)
            if surface_size:
                row["surface_size"] = surface_size
            rows.append(row)
        if "SURFDUMP_READY" in line and not ready_line:
            ready_line = line_no
        if "SURFDUMP_PLAYGAME" in line and not playgame_line:
            playgame_line = line_no
        if line.lstrip().startswith("AV_"):
            av_rows.append({"line_no": line_no, "line": line.lstrip()})

    setup_rows = [row for row in rows if row["marker"] in SETUP_MARKERS]
    owner_global_rows = [row for row in rows if row["marker"] in OWNER_GLOBAL_MARKERS]
    action_rows = [row for row in rows if row["marker"] in ACTION_MARKERS]

    classification: list[str] = []
    if marker_counts["SURFDUMP_READY"]:
        classification.append("surface dump reached ready state")
    else:
        classification.append("surface dump did not reach ready state")
    if marker_counts["CASTLE_INVOKE_PLAYGAME"]:
        classification.append("controlled castle-screen invocation was attempted")
    else:
        classification.append("controlled castle-screen invocation was not observed")
    if marker_counts["CASTLE_SCREEN_FULL_ENTRY_422180"] or marker_counts["CASTLE_SCREEN_OWNER_SET_422207"]:
        classification.append("full castle screen body was observed")
    else:
        classification.append("full castle screen body was not observed")
    if marker_counts["CASTLE_SCREEN_ENTRY_422020"] or marker_counts["CASTLE_RENDERHOOK_DRAW_422020"]:
        classification.append("castle screen render/dispatcher entry was observed")
    else:
        classification.append("castle screen render/dispatcher entry was not observed")
    if setup_rows:
        classification.append("command-99 owner setup route was observed")
    else:
        classification.append("command-99 owner setup route was not observed")
    if owner_global_rows:
        classification.append("owner globals dword_532150/dword_53214C/dword_532154 were touched")
    else:
        classification.append("owner globals dword_532150/dword_53214C/dword_532154 were not touched")
    if action_rows:
        classification.append("right-bottom castle action owner path was observed")
    else:
        classification.append("right-bottom castle action owner path was not observed")
    if av_rows:
        classification.append("AV observed")

    return {
        "path": str(path),
        "line_count": len(lines),
        "marker_counts": marker_counts,
        "rows": rows,
        "setup_rows": setup_rows,
        "owner_global_rows": owner_global_rows,
        "action_rows": action_rows,
        "av_rows": av_rows,
        "ready_line": ready_line,
        "playgame_line": playgame_line,
        "classification": classification,
    }


def write_markdown(summary: dict[str, Any], output: Path, surface_png: str | None) -> None:
    counts = summary["marker_counts"]
    lines = [
        "# Castle Owner Setup Probe",
        "",
        f"- Log: `{summary['path']}`",
        f"- Lines: {summary['line_count']}",
        f"- Surface ready line: {summary['ready_line'] or 'not observed'}",
        f"- PlayGame line: {summary['playgame_line'] or 'not observed'}",
        f"- Setup rows: {len(summary['setup_rows'])}",
        f"- Owner global rows: {len(summary['owner_global_rows'])}",
        f"- Action rows: {len(summary['action_rows'])}",
        f"- AV rows: {len(summary['av_rows'])}",
        "",
        "## Classification",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["classification"])
    lines.extend(["", "## Marker Counts", ""])
    lines.extend(f"- {marker}: {counts[marker]}" for marker in MARKERS if counts[marker])
    if not any(counts.values()):
        lines.append("- no known markers observed")
    if surface_png:
        lines.extend(["", "## Screenshot Artifact", "", f"![surface dump]({surface_png})"])
    lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="CDB log to summarize")
    parser.add_argument("--json-out", type=Path, help="Write JSON summary")
    parser.add_argument("--markdown-out", type=Path, help="Write markdown summary")
    parser.add_argument("--surface-png", help="Surface PNG path for markdown embedding")
    parser.add_argument(
        "--require-surface-ready",
        action="store_true",
        help="Fail if SURFDUMP_READY was not observed",
    )
    parser.add_argument(
        "--require-owner-setup",
        action="store_true",
        help="Fail if command-99 owner setup was not observed",
    )
    args = parser.parse_args(argv)

    if not args.log.exists():
        print(f"log not found: {args.log}", file=sys.stderr)
        return 2

    summary = parse_log(args.log)
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.markdown_out:
        write_markdown(summary, args.markdown_out, args.surface_png)

    print(json.dumps(
        {
            "log": str(args.log),
            "ready_line": summary["ready_line"],
            "setup_rows": len(summary["setup_rows"]),
            "owner_global_rows": len(summary["owner_global_rows"]),
            "action_rows": len(summary["action_rows"]),
            "av_rows": len(summary["av_rows"]),
            "classification": summary["classification"],
        },
        indent=2,
    ))

    if args.require_surface_ready and not summary["ready_line"]:
        print("required SURFDUMP_READY marker was not observed", file=sys.stderr)
        return 2
    if args.require_owner_setup and not summary["setup_rows"]:
        print("required owner setup route was not observed", file=sys.stderr)
        return 2
    if summary["av_rows"]:
        print("AV markers were observed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
