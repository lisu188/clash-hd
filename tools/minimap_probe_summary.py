#!/usr/bin/env python3
"""Summarize Clash95 CDB minimap click probe logs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


MINIMAP_BOX_RE = re.compile(
    r"(?P<kind>MINIMAP_INIT|PLAYGAME).*minimap=\((?P<left>-?\d+),(?P<top>-?\d+),"
    r"(?P<width>-?\d+),(?P<height>-?\d+),(?P<right>-?\d+),(?P<bottom>-?\d+)\)"
)
MINIMAP_INIT_RE = re.compile(
    r"MINIMAP_INIT left=(?P<left>-?\d+) top=(?P<top>-?\d+) "
    r"width=(?P<width>-?\d+) height=(?P<height>-?\d+) "
    r"right=(?P<right>-?\d+) bottom=(?P<bottom>-?\d+) scale=(?P<scale>-?\d+)"
)
MINIMAP_ROW_RE = re.compile(
    r"(?P<kind>MINIMAP_TEST|MINIMAP_TRUE) seq=(?P<seq>\d+) "
    r"x=(?P<x>-?\d+) y=(?P<y>-?\d+) "
    r"left=(?P<left>-?\d+) top=(?P<top>-?\d+) "
    r"width=(?P<width>-?\d+) height=(?P<height>-?\d+) "
    r"right=(?P<right>-?\d+) bottom=(?P<bottom>-?\d+) "
    r"scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\) "
    r"lbtn=0x(?P<lbtn>[0-9a-fA-F]+) rbtn=0x(?P<rbtn>[0-9a-fA-F]+)"
)
MAP_ROW_RE = re.compile(
    r"(?P<kind>MAP_REDRAW|MAP_SCROLLHELPER) seq=(?P<seq>\d+) .*"
    r"scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\) "
    r"lbtn=0x(?P<lbtn>[0-9a-fA-F]+) rbtn=0x(?P<rbtn>[0-9a-fA-F]+)"
)
MOUSE_RE = re.compile(
    r"MOUSE seq=(?P<seq>\d+) .*x=(?P<x>-?\d+) y=(?P<y>-?\d+) "
    r".*lbtn=0x(?P<lbtn>[0-9a-fA-F]+) rbtn=0x(?P<rbtn>[0-9a-fA-F]+) "
    r"min=\((?P<minx>-?\d+),(?P<miny>-?\d+)\) max=\((?P<maxx>-?\d+),(?P<maxy>-?\d+)\)"
)


INT_FIELDS = {
    "seq",
    "left",
    "top",
    "width",
    "height",
    "right",
    "bottom",
    "scale",
    "x",
    "y",
    "scrollx",
    "scrolly",
    "mapw",
    "maph",
    "mousex",
    "mousey",
    "minx",
    "miny",
    "maxx",
    "maxy",
}
HEX_FIELDS = {"lbtn", "rbtn"}


def convert(match: re.Match[str], line_no: int, kind: str | None = None) -> dict:
    row: dict[str, int | str] = {"line_no": line_no}
    groups = match.groupdict()
    row["kind"] = kind or groups.get("kind", "")
    for key, value in groups.items():
        if key == "kind" or value is None:
            continue
        if key in HEX_FIELDS:
            row[key] = int(value, 16)
        elif key in INT_FIELDS:
            row[key] = int(value)
        else:
            row[key] = value
    return row


def parse_log(path: Path) -> dict[str, list[dict]]:
    rows = {
        "init": [],
        "box": [],
        "tests": [],
        "true": [],
        "redraw": [],
        "scrollhelper": [],
        "mouse": [],
        "av": [],
    }
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        init = MINIMAP_INIT_RE.search(line)
        if init:
            rows["init"].append(convert(init, line_no, "MINIMAP_INIT"))
        box = MINIMAP_BOX_RE.search(line)
        if box:
            rows["box"].append(convert(box, line_no))
        minimap = MINIMAP_ROW_RE.search(line)
        if minimap:
            row = convert(minimap, line_no)
            rows["true" if row["kind"] == "MINIMAP_TRUE" else "tests"].append(row)
        map_row = MAP_ROW_RE.search(line)
        if map_row:
            row = convert(map_row, line_no)
            rows["redraw" if row["kind"] == "MAP_REDRAW" else "scrollhelper"].append(row)
        mouse = MOUSE_RE.search(line)
        if mouse:
            rows["mouse"].append(convert(mouse, line_no, "MOUSE"))
        if line.strip() == "AV_MINIMAP_CLICK":
            rows["av"].append({"line_no": line_no, "kind": "AV_MINIMAP_CLICK"})
    return rows


def unique_pairs(rows: list[dict], x_field: str = "scrollx", y_field: str = "scrolly") -> list[dict]:
    seen: dict[tuple[int, int], int] = {}
    for row in rows:
        key = (int(row[x_field]), int(row[y_field]))
        seen[key] = seen.get(key, 0) + 1
    return [{"x": x, "y": y, "count": count} for (x, y), count in sorted(seen.items())]


def range_summary(rows: list[dict], field: str) -> dict[str, int] | None:
    values = [int(row[field]) for row in rows if field in row]
    if not values:
        return None
    return {"min": min(values), "max": max(values), "unique": len(set(values))}


def in_box(row: dict) -> bool:
    return (
        int(row["left"]) <= int(row["x"]) <= int(row["right"])
        and int(row["top"]) <= int(row["y"]) <= int(row["bottom"])
    )


def in_old_only_minimap(row: dict) -> bool:
    return 394 <= int(row["x"]) < int(row["left"]) and 16 <= int(row["y"]) <= 229


def summarize(path: Path) -> dict:
    rows = parse_log(path)
    all_map_rows = rows["redraw"] + rows["scrollhelper"]
    true_rows = rows["true"]
    test_rows = rows["tests"]
    button_true_rows = [row for row in true_rows if int(row.get("lbtn", 0)) or int(row.get("rbtn", 0))]
    old_only_tests = [row for row in test_rows if in_old_only_minimap(row)]
    old_only_true = [row for row in true_rows if in_old_only_minimap(row)]
    new_box_true = [row for row in true_rows if in_box(row)]
    summary = {
        "log": str(path),
        "init_rows": len(rows["init"]),
        "box_rows": len(rows["box"]),
        "test_rows": len(test_rows),
        "true_rows": len(true_rows),
        "button_true_rows": len(button_true_rows),
        "old_only_test_rows": len(old_only_tests),
        "old_only_true_rows": len(old_only_true),
        "new_box_true_rows": len(new_box_true),
        "redraw_rows": len(rows["redraw"]),
        "scrollhelper_rows": len(rows["scrollhelper"]),
        "mouse_rows": len(rows["mouse"]),
        "av_rows": len(rows["av"]),
        "minimap_left_values": sorted({int(row["left"]) for row in rows["box"] + test_rows + true_rows if "left" in row}),
        "minimap_right_values": sorted({int(row["right"]) for row in rows["box"] + test_rows + true_rows if "right" in row}),
        "scroll_values": unique_pairs(all_map_rows),
        "true_scroll_values": unique_pairs(true_rows),
        "mouse_x_range": range_summary(rows["mouse"], "x"),
        "mouse_y_range": range_summary(rows["mouse"], "y"),
        "first_init": rows["init"][:1],
        "first_old_only_test": old_only_tests[:1],
        "first_old_only_true": old_only_true[:1],
        "first_new_box_true": new_box_true[:1],
        "last_new_box_true": new_box_true[-1:] if new_box_true else [],
        "first_button_true": button_true_rows[:1],
        "last_button_true": button_true_rows[-1:] if button_true_rows else [],
        "first_redraw": rows["redraw"][:1],
        "last_redraw": rows["redraw"][-1:] if rows["redraw"] else [],
        "first_mouse": rows["mouse"][:1],
        "last_mouse": rows["mouse"][-1:] if rows["mouse"] else [],
    }
    summary["hd_anchor_seen"] = 586 in summary["minimap_left_values"] and 799 in summary["minimap_right_values"]
    summary["old_anchor_rejected"] = summary["old_only_test_rows"] > 0 and summary["old_only_true_rows"] == 0
    summary["new_anchor_accepted"] = summary["new_box_true_rows"] > 0
    summary["scroll_changed"] = len(summary["scroll_values"]) > 1
    return summary


def print_summary(summary: dict) -> None:
    print(f"log: {summary['log']}")
    print(
        "rows: init={init_rows} tests={test_rows} true={true_rows} "
        "button_true={button_true_rows} redraw={redraw_rows} "
        "scrollhelper={scrollhelper_rows} mouse={mouse_rows} av={av_rows}".format(**summary)
    )
    print(f"minimap_left_values: {summary['minimap_left_values']}")
    print(f"minimap_right_values: {summary['minimap_right_values']}")
    print(f"hd_anchor_seen: {summary['hd_anchor_seen']}")
    print(f"old_only_test_rows: {summary['old_only_test_rows']}")
    print(f"old_only_true_rows: {summary['old_only_true_rows']}")
    print(f"old_anchor_rejected: {summary['old_anchor_rejected']}")
    print(f"new_box_true_rows: {summary['new_box_true_rows']}")
    print(f"new_anchor_accepted: {summary['new_anchor_accepted']}")
    print(f"scroll_values: {summary['scroll_values']}")
    print(f"scroll_changed: {summary['scroll_changed']}")
    if summary["first_init"]:
        print(f"first_init: {summary['first_init'][0]}")
    if summary["first_old_only_test"]:
        print(f"first_old_only_test: {summary['first_old_only_test'][0]}")
    if summary["first_new_box_true"]:
        print(f"first_new_box_true: {summary['first_new_box_true'][0]}")
    if summary["last_new_box_true"]:
        print(f"last_new_box_true: {summary['last_new_box_true'][0]}")
    if summary["first_button_true"]:
        print(f"first_button_true: {summary['first_button_true'][0]}")
    if summary["last_redraw"]:
        print(f"last_redraw: {summary['last_redraw'][0]}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize a Clash95 minimap CDB probe.")
    parser.add_argument("log", type=Path)
    parser.add_argument("--write-json", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = summarize(args.log)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2), encoding="ascii")
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
