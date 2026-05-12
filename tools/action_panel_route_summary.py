#!/usr/bin/env python3
"""Summarize Clash95 action-panel route CDB probe logs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MARKERS = (
    "APROUTE_PLAYGAME_SETUP_40A400",
    "APROUTE_PLAYGAME_CALL_40A500",
    "APROUTE_40A400_ENTRY",
    "APROUTE_40A500_ENTRY",
    "APROUTE_40A500_CALL_423B40",
    "APROUTE_40A500_CALL_423B00",
    "APROUTE_WRITE_532218",
    "APROUTE_WRITE_5322C8",
    "APROUTE_CASTLE_UI_ENTRY",
    "APROUTE_CASTLE_UI_CALL_435BC0",
    "APROUTE_OWNER_435BC0_ENTRY",
    "APROUTE_OWNER_POLL_435B90",
    "APROUTE_HOVER_435A00_ENTRY",
    "APROUTE_SCROLLBOX_435AC0_ENTRY",
    "APROUTE_GRID_HIT_ENTRY",
    "APROUTE_GRID_HIT_FAIL",
    "APROUTE_GRID_HIT_OK",
    "APROUTE_CLICK_DISPATCH_435620",
    "APROUTE_PANEL_DRAW_4347A0",
    "APROUTE_GRID_DRAW_434E20",
    "APROUTE_STATUS_DRAW_435280",
    "APROUTE_ACTION_BOX_435500",
    "APSTATE_NUDGE_SKIPPED",
    "APSTATE_WRITE_532150",
    "APSTATE_WRITE_53214C",
    "APSTATE_WRITE_532154",
    "APSTATE_NUDGE_ATTEMPT",
    "APSTATE_OWNER_FLAG_SET",
    "APSTATE_FORCED_CALL_4338E0",
    "APSTATE_4338E0_ENTRY",
    "APSTATE_433914_CALL_435BC0",
    "APSTATE_OWNER_435BC0_ENTRY",
    "APSTATE_OWNER_POLL_EXIT_ARM",
    "APSTATE_OWNER_POLL_435B90",
    "APSTATE_PANEL_DRAW_4347A0",
    "APSTATE_GRID_DRAW_434E20",
    "APSTATE_STATUS_DRAW_435280",
    "APSTATE_ACTION_BOX_435500",
    "APSTATE_FORCED_RETURN",
    "APPOST_WRITE_532150",
    "APPOST_WRITE_53214C",
    "APPOST_WRITE_532154",
    "APPOST_WRITE_532218",
    "APPOST_WRITE_5322C8",
    "APPOST_OWNER_SETUP_CALL",
    "APPOST_OWNER_FLAG_FORCED",
    "APPOST_433C20_ENTRY",
    "APPOST_ACTION_CALL",
    "APPOST_4338E0_ENTRY",
    "APPOST_433914_CALL_435BC0",
    "APPOST_4338E0_AFTER_435BC0",
    "APPOST_OWNER_435BC0_ENTRY",
    "APPOST_OWNER_POLL_EXIT_ARM",
    "APPOST_OWNER_POLL_435B90",
    "APPOST_PANEL_DRAW_4347A0",
    "APPOST_GRID_DRAW_434E20",
    "APPOST_STATUS_DRAW_435280",
    "APPOST_ACTION_BOX_435500",
    "APREDIR_SET_MAP_TARGET",
    "APREDIR_AFTER_BACKUP_COPY",
    "APREDIR_BEFORE_RESTORE",
    "APREDIR_AFTER_ACTION_BOX",
    "APREDIR_COPYBACK_SET_MAP_TARGET",
    "APREDIR_COPYBACK_AFTER_CALL",
    "APPOST_SURFDUMP_READY",
    "SURFDUMP_PLAYGAME",
    "SURFDUMP_REDRAW",
    "SURFDUMP_READY",
    "SURFDUMP_HOST_READY",
    "SURFDUMP_DONE",
    "AV_SURFDUMP",
)

OWNER_MARKERS = {
    "APROUTE_WRITE_532218",
    "APROUTE_CASTLE_UI_ENTRY",
    "APROUTE_CASTLE_UI_CALL_435BC0",
    "APROUTE_OWNER_435BC0_ENTRY",
    "APSTATE_OWNER_FLAG_SET",
    "APSTATE_FORCED_CALL_4338E0",
    "APSTATE_4338E0_ENTRY",
    "APSTATE_433914_CALL_435BC0",
    "APSTATE_OWNER_435BC0_ENTRY",
    "APSTATE_WRITE_532150",
    "APSTATE_WRITE_53214C",
    "APSTATE_WRITE_532154",
    "APPOST_WRITE_532150",
    "APPOST_WRITE_53214C",
    "APPOST_WRITE_532154",
    "APPOST_WRITE_532218",
    "APPOST_WRITE_5322C8",
    "APPOST_OWNER_SETUP_CALL",
    "APPOST_OWNER_FLAG_FORCED",
    "APPOST_433C20_ENTRY",
    "APPOST_ACTION_CALL",
    "APPOST_4338E0_ENTRY",
    "APPOST_433914_CALL_435BC0",
    "APPOST_4338E0_AFTER_435BC0",
    "APPOST_OWNER_435BC0_ENTRY",
}

PANEL_MARKERS = {
    "APROUTE_OWNER_POLL_435B90",
    "APROUTE_HOVER_435A00_ENTRY",
    "APROUTE_SCROLLBOX_435AC0_ENTRY",
    "APROUTE_GRID_HIT_ENTRY",
    "APROUTE_GRID_HIT_FAIL",
    "APROUTE_GRID_HIT_OK",
    "APROUTE_CLICK_DISPATCH_435620",
    "APROUTE_PANEL_DRAW_4347A0",
    "APROUTE_GRID_DRAW_434E20",
    "APROUTE_STATUS_DRAW_435280",
    "APROUTE_ACTION_BOX_435500",
    "APSTATE_OWNER_POLL_EXIT_ARM",
    "APSTATE_OWNER_POLL_435B90",
    "APSTATE_PANEL_DRAW_4347A0",
    "APSTATE_GRID_DRAW_434E20",
    "APSTATE_STATUS_DRAW_435280",
    "APSTATE_ACTION_BOX_435500",
    "APPOST_OWNER_POLL_EXIT_ARM",
    "APPOST_OWNER_POLL_435B90",
    "APPOST_PANEL_DRAW_4347A0",
    "APPOST_GRID_DRAW_434E20",
    "APPOST_STATUS_DRAW_435280",
    "APPOST_ACTION_BOX_435500",
    "APREDIR_SET_MAP_TARGET",
    "APREDIR_AFTER_BACKUP_COPY",
    "APREDIR_BEFORE_RESTORE",
    "APREDIR_AFTER_ACTION_BOX",
    "APREDIR_COPYBACK_SET_MAP_TARGET",
    "APREDIR_COPYBACK_AFTER_CALL",
}

DRAW_MARKERS = {
    "APROUTE_PANEL_DRAW_4347A0",
    "APROUTE_GRID_DRAW_434E20",
    "APROUTE_STATUS_DRAW_435280",
    "APROUTE_ACTION_BOX_435500",
    "APSTATE_PANEL_DRAW_4347A0",
    "APSTATE_GRID_DRAW_434E20",
    "APSTATE_STATUS_DRAW_435280",
    "APSTATE_ACTION_BOX_435500",
    "APPOST_PANEL_DRAW_4347A0",
    "APPOST_GRID_DRAW_434E20",
    "APPOST_STATUS_DRAW_435280",
    "APPOST_ACTION_BOX_435500",
}

VALUE_RE = re.compile(
    r"(?P<key>d532150|d53214c|d532154|d532218|d5322c8|d532220|d532210|selected|prior|new|owner|owner_arg|owner_global|owner_flag|owner_flag_old|owner_flag_new|surface|base|bytes)="
    r"(?P<value>[-0-9a-fA-F`]+)"
)
SCROLL_RE = re.compile(r"scroll=\((?P<x>-?\d+),(?P<y>-?\d+)\)")
MOUSE_RE = re.compile(r"mouse=\((?P<x>-?\d+),(?P<y>-?\d+)\)")
SURFACE_RE = re.compile(r"sz=\((?P<w>-?\d+),(?P<h>-?\d+)\)")


def marker_for_line(line: str) -> str | None:
    stripped = line.lstrip()
    for marker in MARKERS:
        if stripped == marker or stripped.startswith(marker + " "):
            return marker
    return None


def parse_values(line: str) -> dict[str, str]:
    return {match.group("key"): match.group("value").replace("`", "") for match in VALUE_RE.finditer(line)}


def parse_pair(pattern: re.Pattern[str], line: str) -> list[int] | None:
    match = pattern.search(line)
    if not match:
        return None
    return [int(match.group("x")), int(match.group("y"))]


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
            row = {
                "line_no": line_no,
                "marker": marker,
                "line": line.lstrip(),
                "values": parse_values(line),
            }
            mouse = parse_pair(MOUSE_RE, line)
            if mouse:
                row["mouse"] = mouse
            scroll = parse_pair(SCROLL_RE, line)
            if scroll:
                row["scroll"] = scroll
            surface = parse_surface(line)
            if surface:
                row["surface_size"] = surface
            rows.append(row)
        if "SURFDUMP_READY" in line and not ready_line:
            ready_line = line_no
        if "SURFDUMP_PLAYGAME" in line and not playgame_line:
            playgame_line = line_no
        if line.lstrip().startswith("AV_"):
            av_rows.append({"line_no": line_no, "line": line.lstrip()})

    owner_rows = [row for row in rows if row["marker"] in OWNER_MARKERS]
    panel_rows = [row for row in rows if row["marker"] in PANEL_MARKERS]
    draw_rows = [row for row in rows if row["marker"] in DRAW_MARKERS]
    nonzero_owner_rows = [
        row
        for row in rows
        if row["values"].get("d532218", "").lower() not in {"", "00000000", "0"}
        or row["values"].get("new", "").lower() not in {"", "00000000", "0"}
    ]

    classification: list[str] = []
    if marker_counts["SURFDUMP_READY"]:
        classification.append("surface dump reached gameplay ready state")
    else:
        classification.append("surface dump did not reach gameplay ready state")
    if marker_counts["APROUTE_PLAYGAME_SETUP_40A400"] or marker_counts["APROUTE_PLAYGAME_CALL_40A500"]:
        classification.append("PlayGame setup route rows were observed")
    if owner_rows:
        classification.append("action-panel owner/global route was reached")
    else:
        classification.append("action-panel owner/global route was not reached")
    if marker_counts["APSTATE_FORCED_CALL_4338E0"]:
        classification.append("debugger-only owner/action-panel call was forced without mouse-global writes")
    if marker_counts["APPOST_OWNER_SETUP_CALL"]:
        classification.append("post-redraw debugger-only owner setup was attempted on the gameplay surface")
    if marker_counts["APPOST_ACTION_CALL"]:
        classification.append("post-owner action route 004338E0 was forced on the gameplay surface")
    if marker_counts["APPOST_SURFDUMP_READY"]:
        classification.append("surface was dumped after the post-owner action route")
    if marker_counts["APREDIR_SET_MAP_TARGET"]:
        classification.append("debugger-only action-box render target redirect was attempted")
    if marker_counts["APREDIR_AFTER_ACTION_BOX"]:
        classification.append("action-box redirect returned to the caller with map/scratch samples logged")
    if marker_counts["APREDIR_COPYBACK_SET_MAP_TARGET"]:
        classification.append("debugger-only post-action copyback target redirect was attempted")
    if marker_counts["APREDIR_COPYBACK_AFTER_CALL"]:
        classification.append("post-action copyback redirect returned with map/scratch samples logged")
    if marker_counts["APSTATE_NUDGE_SKIPPED"]:
        classification.append("state-route nudge skipped because the owner global was unavailable")
    if marker_counts["APSTATE_FORCED_RETURN"]:
        classification.append("forced owner/action-panel call returned to PlayGame")
    if panel_rows:
        classification.append("one or more action-panel poll hit-test or draw rows fired")
    else:
        classification.append("no action-panel poll hit-test or draw rows fired")
    if draw_rows:
        classification.append("right-bottom action/status draw functions executed")
    else:
        classification.append("right-bottom action/status draw functions did not execute")
    if nonzero_owner_rows:
        classification.append("nonzero dword_532218 owner evidence was observed")
    else:
        classification.append("dword_532218 stayed zero in observed route rows")
    if av_rows:
        classification.append("AV observed")

    return {
        "log": str(path),
        "marker_counts": marker_counts,
        "rows": rows,
        "owner_rows": owner_rows,
        "panel_rows": panel_rows,
        "draw_rows": draw_rows,
        "nonzero_owner_rows": nonzero_owner_rows,
        "ready": marker_counts["SURFDUMP_READY"] > 0,
        "playgame_line": playgame_line,
        "ready_line": ready_line,
        "av_count": len(av_rows),
        "av_rows": av_rows,
        "classification": classification,
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Action Panel Route Summary",
        "",
        f"- Log: `{summary['log']}`",
        f"- Ready: {summary['ready']}",
        f"- AV rows: {summary['av_count']}",
        f"- Owner/global rows: {len(summary['owner_rows'])}",
        f"- Panel route rows: {len(summary['panel_rows'])}",
        f"- Draw rows: {len(summary['draw_rows'])}",
        f"- Nonzero owner rows: {len(summary['nonzero_owner_rows'])}",
        f"- PlayGame line: {summary['playgame_line']}",
        f"- Ready line: {summary['ready_line']}",
        "",
        "## Classification",
    ]
    lines.extend(f"- {item}" for item in summary["classification"])

    lines.extend(["", "## Marker Counts"])
    for marker in MARKERS:
        lines.append(f"- {marker}: {summary['marker_counts'][marker]}")

    lines.extend(["", "## First Route Rows"])
    for row in summary["rows"][:40]:
        lines.append(f"- line {row['line_no']}: {row['line']}")
    if not summary["rows"]:
        lines.append("- none")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--require-owner", action="store_true")
    args = parser.parse_args(argv)

    summary = parse_log(args.log)
    if args.write_json:
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_md:
        write_markdown(args.write_md, summary)

    print(
        "ready={ready} av_count={av_count} owner_rows={owners} panel_rows={panels} draw_rows={draws} nonzero_owner_rows={nonzero}".format(
            ready=summary["ready"],
            av_count=summary["av_count"],
            owners=len(summary["owner_rows"]),
            panels=len(summary["panel_rows"]),
            draws=len(summary["draw_rows"]),
            nonzero=len(summary["nonzero_owner_rows"]),
        )
    )
    for item in summary["classification"]:
        print(f"- {item}")
    if args.require_ready and not summary["ready"]:
        print("ERROR: SURFDUMP_READY not observed", file=sys.stderr)
        return 1
    if args.require_owner and not summary["owner_rows"]:
        print("ERROR: no action-panel owner/global rows observed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
