#!/usr/bin/env python3
"""Summarize Clash95 hover/selection UI CDB probe logs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MARKERS = (
    "HOVSEL_FORCE_STATE",
    "HOVSEL_REDRAW_ENTRY",
    "HOVSEL_UNITINFO_ENTRY",
    "HOVSEL_UNITINFO_CALL",
    "HOVSEL_PANEL_DRAW",
    "HOVSEL_GRID_DRAW",
    "HOVSEL_STATUS_DRAW",
    "HOVSEL_ACTION_BOX",
    "HOVSEL_STATE_HELPER",
    "HOVSEL_HOVER_HANDLER",
    "HOVSEL_ACTION_UI_ENTRY",
    "HOVSEL_TEXT",
    "HOVSEL_TEXTFMT",
    "HOVSEL_PRESENT",
    "HOVSEL_PRESENT_NULL",
    "SURFDUMP_PLAYGAME",
    "SURFDUMP_REDRAW",
    "SURFDUMP_READY",
    "AV_SURFDUMP",
)

ENTRY_MARKERS = {
    "HOVSEL_UNITINFO_ENTRY",
    "HOVSEL_UNITINFO_CALL",
    "HOVSEL_PANEL_DRAW",
    "HOVSEL_GRID_DRAW",
    "HOVSEL_STATUS_DRAW",
    "HOVSEL_ACTION_BOX",
    "HOVSEL_STATE_HELPER",
    "HOVSEL_HOVER_HANDLER",
    "HOVSEL_ACTION_UI_ENTRY",
}

REGIONS: dict[str, tuple[int, int, int, int]] = {
    "frame_left": (0, 0, 31, 599),
    "frame_top": (0, 0, 799, 15),
    "right_frame_under_minimap": (586, 230, 799, 527),
    "bottom_tooltip": (32, 528, 585, 599),
    "bottom_right_panel": (586, 528, 799, 599),
    "bottom_frame": (0, 580, 799, 599),
}

PRESENT_RE = re.compile(
    r"HOVSEL_PRESENT ret=(?P<ret>\S+) call=(?P<call>\S+) "
    r"src=(?P<src>\S+) srcsz=\((?P<srcw>-?\d+),(?P<srch>-?\d+)\) "
    r"dst=(?P<dst>\S+) dstw=(?P<dstw>-?\d+) "
    r"src_ltrb=\((?P<left>-?\d+),(?P<top>-?\d+),(?P<right>-?\d+),(?P<bottom>-?\d+)\) "
    r"dxy=\((?P<dx>-?\d+),(?P<dy>-?\d+)\) "
    r"render=(?P<render>\S+) map_surface=(?P<map_surface>\S+) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\)"
)
FORCE_RE = re.compile(
    r"HOVSEL_FORCE_STATE seq=(?P<seq>-?\d+) mode=(?P<mode>\S+) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\).*"
    r"selected=(?P<selected>-?\d+) action=(?P<action>-?\d+) "
    r"d532218=(?P<d532218>\S+) d532220=(?P<d532220>-?\d+)"
)
REDRAW_RE = re.compile(
    r"HOVSEL_REDRAW_ENTRY seq=(?P<seq>-?\d+) surface=(?P<surface>\S+) "
    r"sz=\((?P<width>-?\d+),(?P<height>-?\d+)\).*"
    r"bottom_sample=(?P<bottom_sample>[0-9a-fA-F]+) "
    r"right_sample=(?P<right_sample>[0-9a-fA-F]+)"
)

INT_FIELDS = {
    "seq",
    "srcw",
    "srch",
    "dstw",
    "left",
    "top",
    "right",
    "bottom",
    "dx",
    "dy",
    "mousex",
    "mousey",
    "selected",
    "action",
    "d532220",
    "width",
    "height",
}


def parse_int(value: str) -> int:
    return int(value, 0)


def convert(match: re.Match[str], line_no: int, kind: str) -> dict[str, Any]:
    row: dict[str, Any] = {"kind": kind, "line_no": line_no}
    for key, value in match.groupdict().items():
        if key in {"bottom_sample", "right_sample"}:
            row[key] = int(value, 16)
        elif key in INT_FIELDS:
            row[key] = parse_int(value)
        else:
            row[key] = value.replace("`", "")
    return row


def rects_intersect(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return ax0 <= bx1 and bx0 <= ax1 and ay0 <= by1 and by0 <= ay1


def present_rect(row: dict[str, Any]) -> tuple[int, int, int, int]:
    left = int(row["dx"])
    top = int(row["dy"])
    right = left + max(0, int(row["right"]) - int(row["left"]))
    bottom = top + max(0, int(row["bottom"]) - int(row["top"]))
    return left, top, right, bottom


def row_regions(row: dict[str, Any]) -> list[str]:
    rect = present_rect(row)
    return [name for name, region in REGIONS.items() if rects_intersect(rect, region)]


def native_clip_flags(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    rect = present_rect(row)
    if int(row["right"]) in {607, 639}:
        flags.append(f"src_right_{row['right']}")
    if int(row["bottom"]) in {463, 479}:
        flags.append(f"src_bottom_{row['bottom']}")
    if rect[2] in {607, 639}:
        flags.append(f"present_right_{rect[2]}")
    if rect[3] in {463, 479}:
        flags.append(f"present_bottom_{rect[3]}")
    return flags


def parse_log(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    marker_counts = {marker: 0 for marker in MARKERS}
    force_states: list[dict[str, Any]] = []
    redraws: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    presents: list[dict[str, Any]] = []
    null_presents: list[dict[str, Any]] = []
    av_rows: list[dict[str, Any]] = []
    surfdump_redraw_lines: list[int] = []
    ready_line = 0

    for line_no, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        for marker in MARKERS:
            if stripped == marker or stripped.startswith(marker + " "):
                marker_counts[marker] += 1
        if "SURFDUMP_REDRAW " in line:
            surfdump_redraw_lines.append(line_no)
        if "SURFDUMP_READY" in line and not ready_line:
            ready_line = line_no
        if stripped.startswith("AV_"):
            av_rows.append({"line_no": line_no, "line": stripped})

        force = FORCE_RE.search(line)
        if force:
            force_states.append(convert(force, line_no, "HOVSEL_FORCE_STATE"))
        redraw = REDRAW_RE.search(line)
        if redraw:
            redraws.append(convert(redraw, line_no, "HOVSEL_REDRAW_ENTRY"))
        present = PRESENT_RE.search(line)
        if present:
            row = convert(present, line_no, "HOVSEL_PRESENT")
            row["present_rect"] = list(present_rect(row))
            row["regions"] = row_regions(row)
            row["native_clip_flags"] = native_clip_flags(row)
            presents.append(row)
        if "HOVSEL_PRESENT_NULL" in line:
            null_presents.append({"line_no": line_no, "line": stripped})
        for marker in ENTRY_MARKERS:
            if stripped == marker or stripped.startswith(marker + " "):
                entries.append({"kind": marker, "line_no": line_no, "line": stripped})
                break

    region_counts = {name: 0 for name in REGIONS}
    native_clip_rows = []
    for row in presents:
        for region in row["regions"]:
            region_counts[region] += 1
        if row["native_clip_flags"]:
            native_clip_rows.append(row)

    entry_count = len(entries)
    last_redraw_line = max(surfdump_redraw_lines) if surfdump_redraw_lines else 0
    entries_after_last_redraw = [row for row in entries if last_redraw_line and row["line_no"] > last_redraw_line]
    presents_after_last_redraw = [row for row in presents if last_redraw_line and row["line_no"] > last_redraw_line]

    classification: list[str] = []
    if marker_counts["SURFDUMP_READY"]:
        classification.append("surface dump reached gameplay ready state")
    if len(force_states) >= 4:
        modes = ", ".join(row.get("mode", "unknown") for row in force_states)
        classification.append(f"debugger forced {len(force_states)} hover states: {modes}")
    elif force_states:
        classification.append("debugger forced partial hover position sequence")
    if entry_count == 0:
        classification.append("target UI functions were not reached under the observed hover sequence")
    else:
        classification.append("at least one target UI function was reached")
    if presents:
        if any(row["regions"] for row in presents):
            classification.append("filtered presents intersect bottom or right UI regions")
        else:
            classification.append("filtered presents stayed outside bottom and right UI regions")
    elif entry_count:
        classification.append("target functions ran but no filtered low-level present rows were observed")
    if native_clip_rows:
        classification.append("one or more present rows use native 640x480-era clip edges")
    if last_redraw_line and entry_count and not entries_after_last_redraw:
        classification.append("target UI rows occurred before the last map redraw and may be overwritten")
    if presents_after_last_redraw:
        classification.append("filtered UI presents occurred after the last map redraw")
    if av_rows:
        classification.append("AV observed")

    return {
        "log": str(path),
        "marker_counts": marker_counts,
        "force_states": force_states,
        "redraws": redraws,
        "entries": entries,
        "presents": presents,
        "null_presents": null_presents,
        "region_counts": region_counts,
        "native_clip_row_count": len(native_clip_rows),
        "native_clip_rows": native_clip_rows,
        "surfdump_redraw_lines": surfdump_redraw_lines,
        "last_redraw_line": last_redraw_line,
        "ready_line": ready_line,
        "entries_after_last_redraw": entries_after_last_redraw,
        "presents_after_last_redraw": presents_after_last_redraw,
        "classification": classification,
        "ready": marker_counts["SURFDUMP_READY"] > 0,
        "av_count": len(av_rows),
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Hover Selection UI Summary",
        "",
        f"- Log: `{summary['log']}`",
        f"- Ready: {summary['ready']}",
        f"- AV rows: {summary['av_count']}",
        f"- Target UI entries: {len(summary['entries'])}",
        f"- Filtered present rows: {len(summary['presents'])}",
        f"- Native clip rows: {summary['native_clip_row_count']}",
        f"- Last map redraw line: {summary['last_redraw_line']}",
        "",
        "## Classification",
    ]
    lines.extend(f"- {item}" for item in summary["classification"])

    lines.extend(["", "## Marker Counts"])
    for marker in MARKERS:
        lines.append(f"- {marker}: {summary['marker_counts'][marker]}")

    lines.extend(["", "## Region Present Counts"])
    for name, count in summary["region_counts"].items():
        lines.append(f"- {name}: {count}")

    lines.extend(["", "## Forced Hover States"])
    for row in summary["force_states"]:
        lines.append(
            "- seq={seq} mode={mode} mouse=({mousex},{mousey}) selected={selected} action={action} d532218={d532218} d532220={d532220}".format(
                **row
            )
        )
    if not summary["force_states"]:
        lines.append("- none")

    lines.extend(["", "## First Entries"])
    for row in summary["entries"][:20]:
        lines.append(f"- line {row['line_no']}: {row['kind']}")
    if not summary["entries"]:
        lines.append("- none")

    lines.extend(["", "## First Presents"])
    for row in summary["presents"][:20]:
        lines.append(
            "- line {line_no}: ret={ret} rect={present_rect} regions={regions} native_clip={native_clip_flags}".format(
                **row
            )
        )
    if not summary["presents"]:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--require-hover-sequence", action="store_true")
    args = parser.parse_args(argv)

    summary = parse_log(args.log)
    if args.write_json:
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_md:
        write_markdown(args.write_md, summary)

    print(
        "ready={ready} av_count={av_count} force_states={force_states} entries={entries} presents={presents} native_clip_rows={native_clip}".format(
            ready=summary["ready"],
            av_count=summary["av_count"],
            force_states=len(summary["force_states"]),
            entries=len(summary["entries"]),
            presents=len(summary["presents"]),
            native_clip=summary["native_clip_row_count"],
        )
    )
    for item in summary["classification"]:
        print(f"- {item}")
    if args.require_ready and not summary["ready"]:
        print("ERROR: SURFDUMP_READY not observed", file=sys.stderr)
        return 1
    if args.require_hover_sequence and len(summary["force_states"]) < 4:
        print("ERROR: full hover sequence was not observed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
