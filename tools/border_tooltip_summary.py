#!/usr/bin/env python3
"""Summarize Clash95 border/tooltip CDB evidence and optional PNG regions."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

from capture_geometry import Image, read_png


REGIONS: dict[str, tuple[int, int, int, int]] = {
    "frame_left": (0, 0, 31, 599),
    "frame_top": (0, 0, 799, 15),
    "right_frame_under_minimap": (586, 230, 799, 527),
    "bottom_tooltip": (32, 528, 585, 599),
    "bottom_right_panel": (586, 528, 799, 599),
    "bottom_frame": (0, 580, 799, 599),
}

MARKERS = (
    "BORDER_FULLREDRAW_ENTER",
    "TOOLTIP_UNITINFO_ENTRY",
    "BORDER_PANEL_DRAW",
    "TOOLTIP_STATUS_DRAW",
    "TOOLTIP_ACTION_BOX",
    "BORDER_PANEL_SPRITE_ENTRY",
    "BORDER_INFO_WINDOW_ENTRY",
    "BORDER_NOTIFY_TEXT_ENTRY",
    "BORDER_MISSION_STATUS_ENTRY",
    "TOOLTIP_TEXT",
    "TOOLTIP_TEXTFMT",
    "BORDER_TOOLTIP_PRESENT",
    "BORDER_TOOLTIP_PRESENT_NULLPTR",
    "APCOMP_ACTION_BOX_ENTRY",
    "APCOMP_COPYBACK_SAMPLES",
    "APCOMPOSE_STATUS_SHIFT_CALL",
    "APCOMPOSE_STATUS_SHIFT_DONE",
    "APCOMPOSE_ACTION_SHIFT_CALL",
    "APCOMPOSE_ACTION_SHIFT_DONE",
    "SURFDUMP_PLAYGAME",
    "SURFDUMP_READY",
)

FULLREDRAW_RE = re.compile(
    r"BORDER_FULLREDRAW_ENTER ret=(?P<ret>\S+) gd=(?P<gd>\S+) "
    r"d526990=(?P<d526990>\S+) d5202e0=(?P<surface>\S+) "
    r"sz=\((?P<width>-?\d+),(?P<height>-?\d+)\) "
    r"scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\) lbtn=0x(?P<lbtn>[0-9a-fA-F]+)"
)
TEXT_RE = re.compile(
    r"(?P<kind>TOOLTIP_TEXT|TOOLTIP_TEXTFMT) ret=(?P<ret>\S+) "
    r"x=(?P<x>-?\d+) y=(?P<y>-?\d+).*"
    r"d5202e0=(?P<surface>\S+) sz=\((?P<width>-?\d+),(?P<height>-?\d+)\) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\)"
)
PRESENT_RE = re.compile(
    r"BORDER_TOOLTIP_PRESENT ret=(?P<ret>\S+) call=(?P<call>\S+) "
    r"src=(?P<src>\S+) srcsz=\((?P<srcw>-?\d+),(?P<srch>-?\d+)\) "
    r"dst=(?P<dst>\S+) dstsz=\((?P<dstw>-?\d+),(?P<dsth>-?\d+)\) "
    r"ltrb=\((?P<left>-?\d+),(?P<top>-?\d+),(?P<right>-?\d+),(?P<bottom>-?\d+)\) "
    r"dxy=\((?P<dx>-?\d+),(?P<dy>-?\d+)\) d5202e0=(?P<surface>\S+) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\)"
)
PRESENT_NULL_RE = re.compile(
    r"BORDER_TOOLTIP_PRESENT_NULLPTR ret=(?P<ret>\S+) call=(?P<call>\S+) "
    r"src=(?P<src>\S+) dst=(?P<dst>\S+) "
    r"ltrb=\((?P<left>-?\d+),(?P<top>-?\d+),(?P<right>-?\d+),(?P<bottom>-?\d+)\) "
    r"dxy=\((?P<dx>-?\d+),(?P<dy>-?\d+)\) d5202e0=(?P<surface>\S+) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\)"
)
SAMPLE_RE = re.compile(
    r"(?P<kind>APCOMP_ACTION_BOX_ENTRY|APCOMP_COPYBACK_SAMPLES|"
    r"APCOMPOSE_STATUS_SHIFT_CALL|APCOMPOSE_STATUS_SHIFT_DONE|"
    r"APCOMPOSE_ACTION_SHIFT_CALL|APCOMPOSE_ACTION_SHIFT_DONE)\b(?P<body>.*)"
)
ENTRY_RES = {
    "unitinfo": re.compile(r"TOOLTIP_UNITINFO_ENTRY\b"),
    "panel": re.compile(r"BORDER_PANEL_DRAW\b"),
    "status": re.compile(r"TOOLTIP_STATUS_DRAW\b"),
    "action_box": re.compile(r"TOOLTIP_ACTION_BOX\b"),
    "panel_sprite": re.compile(r"BORDER_PANEL_SPRITE_ENTRY\b"),
    "info_window": re.compile(r"BORDER_INFO_WINDOW_ENTRY\b"),
    "notify_text": re.compile(r"BORDER_NOTIFY_TEXT_ENTRY\b"),
    "mission_status": re.compile(r"BORDER_MISSION_STATUS_ENTRY\b"),
}

INT_FIELDS = {
    "width",
    "height",
    "scrollx",
    "scrolly",
    "mousex",
    "mousey",
    "x",
    "y",
    "srcw",
    "srch",
    "dstw",
    "dsth",
    "left",
    "top",
    "right",
    "bottom",
    "dx",
    "dy",
}


def to_int(value: str) -> int:
    return int(value)


def convert(match: re.Match[str], line_no: int, kind: str) -> dict[str, Any]:
    row: dict[str, Any] = {"kind": kind, "line_no": line_no}
    for key, value in match.groupdict().items():
        if value is None:
            continue
        if key in INT_FIELDS:
            row[key] = to_int(value)
        elif key == "lbtn":
            row[key] = int(value, 16)
        else:
            row[key] = value
    return row


def parse_log(path: Path) -> dict[str, Any]:
    rows: dict[str, list[dict[str, Any]]] = {
        "fullredraw": [],
        "text": [],
        "present": [],
        "present_null": [],
        "samples": [],
        "entries": [],
        "av": [],
        "surfdump_playgame": [],
        "surfdump_ready": [],
    }
    marker_counts = {marker: 0 for marker in MARKERS}
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        for marker in MARKERS:
            if marker in line:
                marker_counts[marker] += 1

        fullredraw = FULLREDRAW_RE.search(line)
        if fullredraw:
            rows["fullredraw"].append(convert(fullredraw, line_no, "BORDER_FULLREDRAW_ENTER"))
        text = TEXT_RE.search(line)
        if text:
            rows["text"].append(convert(text, line_no, text.group("kind")))
        present = PRESENT_RE.search(line)
        if present:
            row = convert(present, line_no, "BORDER_TOOLTIP_PRESENT")
            row["regions"] = intersecting_regions(row)
            row["native_clip_flags"] = native_clip_flags(row)
            rows["present"].append(row)
        present_null = PRESENT_NULL_RE.search(line)
        if present_null:
            row = convert(present_null, line_no, "BORDER_TOOLTIP_PRESENT_NULLPTR")
            row["regions"] = intersecting_regions(row)
            row["native_clip_flags"] = native_clip_flags(row)
            rows["present_null"].append(row)
        sample = SAMPLE_RE.search(line)
        if sample:
            rows["samples"].append(
                {
                    "kind": sample.group("kind"),
                    "line_no": line_no,
                    "line": line.strip(),
                }
            )

        for name, pattern in ENTRY_RES.items():
            if pattern.search(line):
                rows["entries"].append({"kind": name, "line_no": line_no, "line": line.strip()})
                break

        stripped = line.strip()
        if stripped.startswith("AV_"):
            rows["av"].append({"line_no": line_no, "line": stripped})
        if "SURFDUMP_PLAYGAME" in line:
            rows["surfdump_playgame"].append({"line_no": line_no, "line": line.strip()})
        if "SURFDUMP_READY" in line:
            rows["surfdump_ready"].append({"line_no": line_no, "line": line.strip()})

    return {"rows": rows, "marker_counts": marker_counts}


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


def intersecting_regions(row: dict[str, Any]) -> list[str]:
    rect = present_rect(row)
    return [name for name, region in REGIONS.items() if rects_intersect(rect, region)]


def native_clip_flags(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    for field, values in {
        "right": {607, 639},
        "bottom": {463, 479},
        "dx": {607, 639},
        "dy": {463, 479},
    }.items():
        value = int(row.get(field, -99999))
        if value in values:
            flags.append(f"{field}_{value}")
    rect = present_rect(row)
    if rect[2] in {607, 639}:
        flags.append(f"present_right_{rect[2]}")
    if rect[3] in {463, 479}:
        flags.append(f"present_bottom_{rect[3]}")
    return flags


def logical_rect_to_pixels(
    image: Image,
    rect: tuple[int, int, int, int],
    logical_width: int,
    logical_height: int,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = rect
    scale_x = image.width / logical_width
    scale_y = image.height / logical_height
    return (
        max(0, min(image.width - 1, math.floor(left * scale_x))),
        max(0, min(image.height - 1, math.floor(top * scale_y))),
        max(0, min(image.width - 1, math.ceil((right + 1) * scale_x) - 1)),
        max(0, min(image.height - 1, math.ceil((bottom + 1) * scale_y) - 1)),
    )


def analyze_png(path: Path, logical_width: int, logical_height: int, threshold: int) -> dict[str, Any]:
    image = read_png(path)
    regions: dict[str, Any] = {}
    for name, rect in REGIONS.items():
        x0, y0, x1, y1 = logical_rect_to_pixels(image, rect, logical_width, logical_height)
        total = 0
        nonblack = 0
        black = 0
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                total += 1
                if max(image.rgb_at(x, y)) > threshold:
                    nonblack += 1
                else:
                    black += 1
        regions[name] = {
            "logical_rect": list(rect),
            "image_rect": [x0, y0, x1, y1],
            "nonblack_percent": round(nonblack * 100.0 / total, 3) if total else 0.0,
            "black_percent": round(black * 100.0 / total, 3) if total else 0.0,
        }
    return {
        "path": str(path),
        "image_size": {"width": image.width, "height": image.height},
        "logical_size": {"width": logical_width, "height": logical_height},
        "regions": regions,
    }


def summarize(log: Path, png: Path | None, args: argparse.Namespace) -> dict[str, Any]:
    parsed = parse_log(log)
    rows = parsed["rows"]
    present_by_region = {name: 0 for name in REGIONS}
    null_present_by_region = {name: 0 for name in REGIONS}
    native_clip_rows = []
    for row in rows["present"]:
        for region in row["regions"]:
            present_by_region[region] += 1
        if row["native_clip_flags"]:
            native_clip_rows.append(row)
    null_native_clip_rows = []
    for row in rows["present_null"]:
        for region in row["regions"]:
            null_present_by_region[region] += 1
        if row["native_clip_flags"]:
            null_native_clip_rows.append(row)

    d526990_values = sorted({row.get("d526990") for row in rows["fullredraw"] if row.get("d526990")})
    surface_sizes = sorted({f"{row.get('width')}x{row.get('height')}" for row in rows["fullredraw"]})
    png_summary = analyze_png(png, args.logical_width, args.logical_height, args.threshold) if png else None

    return {
        "log": str(log),
        "marker_counts": parsed["marker_counts"],
        "row_counts": {key: len(value) for key, value in rows.items()},
        "surface_sizes": surface_sizes,
        "d526990_values": d526990_values,
        "d526990_nonzero_seen": any(value not in {None, "00000000", "0"} for value in d526990_values),
        "present_by_region": present_by_region,
        "null_present_by_region": null_present_by_region,
        "native_clip_row_count": len(native_clip_rows),
        "native_clip_rows": native_clip_rows[:20],
        "null_native_clip_row_count": len(null_native_clip_rows),
        "null_native_clip_rows": null_native_clip_rows[:20],
        "text_rows": rows["text"][:40],
        "entry_rows": rows["entries"][:40],
        "fullredraw_rows": rows["fullredraw"][:20],
        "surfdump_ready_rows": rows["surfdump_ready"][:5],
        "av_rows": rows["av"],
        "png": png_summary,
    }


def print_summary(summary: dict[str, Any]) -> None:
    print(f"log: {summary['log']}")
    print(f"row_counts: {summary['row_counts']}")
    print(f"surface_sizes: {summary['surface_sizes']}")
    print(f"d526990_values: {summary['d526990_values']}")
    print(f"d526990_nonzero_seen: {summary['d526990_nonzero_seen']}")
    print(f"present_by_region: {summary['present_by_region']}")
    print(f"null_present_by_region: {summary['null_present_by_region']}")
    print(f"native_clip_row_count: {summary['native_clip_row_count']}")
    print(f"null_native_clip_row_count: {summary['null_native_clip_row_count']}")
    print(f"av_rows: {len(summary['av_rows'])}")
    if summary.get("png"):
        print("png_regions:")
        for name, region in summary["png"]["regions"].items():
            print(
                f"  {name}: nonblack={region['nonblack_percent']}% "
                f"black={region['black_percent']}%"
            )


def write_markdown(summary: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Border Tooltip CDB Summary",
        "",
        f"- Log: `{summary['log']}`",
        f"- Surface sizes: `{summary['surface_sizes']}`",
        f"- `dword_526990` values: `{summary['d526990_values']}`",
        f"- Nonzero `dword_526990` seen: `{summary['d526990_nonzero_seen']}`",
        f"- Present rows by region: `{summary['present_by_region']}`",
        f"- Null-destination present rows by region: `{summary['null_present_by_region']}`",
        f"- Native clip row count: `{summary['native_clip_row_count']}`",
        f"- Null-destination native clip row count: `{summary['null_native_clip_row_count']}`",
        f"- AV rows: `{len(summary['av_rows'])}`",
    ]
    if summary.get("png"):
        lines.extend(["", f"![surface]({summary['png']['path']})", "", "## PNG Regions", ""])
        for name, region in summary["png"]["regions"].items():
            lines.append(
                f"- `{name}`: nonblack `{region['nonblack_percent']}%`, "
                f"black `{region['black_percent']}%`"
            )
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize Clash95 border/tooltip CDB probe logs.")
    parser.add_argument("--log", required=True, type=Path, help="CDB log path")
    parser.add_argument("--png", type=Path, help="surface PNG path")
    parser.add_argument("--write-json", type=Path, help="write JSON summary")
    parser.add_argument("--write-markdown", type=Path, help="write Markdown summary")
    parser.add_argument("--logical-width", type=int, default=800)
    parser.add_argument("--logical-height", type=int, default=600)
    parser.add_argument("--threshold", type=int, default=12)
    parser.add_argument("--require-ready", action="store_true", help="exit 2 unless SURFDUMP_READY exists")
    parser.add_argument("--require-present-region", action="append", default=[], choices=sorted(REGIONS))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = summarize(args.log, args.png, args)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2), encoding="ascii")
    if args.write_markdown:
        write_markdown(summary, args.write_markdown)
    print_summary(summary)

    failures: list[str] = []
    if args.require_ready and not summary["surfdump_ready_rows"]:
        failures.append("SURFDUMP_READY was not observed")
    for region in args.require_present_region:
        if summary["present_by_region"].get(region, 0) <= 0:
            failures.append(f"no present row intersected required region {region}")
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
