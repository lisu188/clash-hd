#!/usr/bin/env python3
"""Summarize Clash95 CDB viewport bounds probe logs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CALL_RE = re.compile(
    r"(?P<kind>VIEWPORT_INIT_CALL|VIEWPORT_SWITCH_CALL) seq=(?P<seq>\d+) "
    r"obj=(?P<obj>\S+) right_arg=(?P<right_arg>-?\d+) bottom_arg=(?P<bottom_arg>-?\d+) "
    r"shift=(?P<shift>-?\d+).*gameplay=(?P<gameplay>-?\d+)"
)
SWITCH_ENTRY_RE = re.compile(
    r"VIEWPORT_SWITCH_ENTRY seq=(?P<seq>\d+) obj=(?P<obj>\S+) "
    r"new_meta=(?P<new_meta>\S+) old_meta=(?P<old_meta>\S+) shift=(?P<shift>-?\d+) "
    r"fields_before=\((?P<minx>-?\d+),(?P<miny>-?\d+),(?P<maxx>-?\d+),(?P<maxy>-?\d+)\) "
    r"gameplay=(?P<gameplay>-?\d+)"
)
VIEWPORT_ENTRY_RE = re.compile(
    r"VIEWPORT_ENTRY seq=(?P<seq>\d+) ret=(?P<ret>\S+) obj=(?P<obj>\S+) "
    r"left_arg=(?P<left_arg>-?\d+) right_arg=(?P<right_arg>-?\d+) "
    r"top_arg=(?P<top_arg>-?\d+) bottom_arg=(?P<bottom_arg>-?\d+) "
    r"shift=(?P<shift>-?\d+) meta=(?P<meta>\S+) .*"
    r"fields_before=\((?P<minx>-?\d+),(?P<miny>-?\d+),(?P<maxx>-?\d+),(?P<maxy>-?\d+)\) "
    r"gameplay=(?P<gameplay>-?\d+)"
)
VIEWPORT_SET_RE = re.compile(
    r"VIEWPORT_SET seq=(?P<seq>\d+) ret=(?P<ret>\S+) obj=(?P<obj>\S+) "
    r"shift=(?P<shift>-?\d+) min=\((?P<minx>-?\d+),(?P<miny>-?\d+)\) "
    r"max=\((?P<maxx>-?\d+),(?P<maxy>-?\d+)\) .*meta=(?P<meta>\S+) .*"
    r"gameplay=(?P<gameplay>-?\d+)"
)
MOUSE_RE = re.compile(
    r"MOUSE_BOUND seq=(?P<seq>\d+) obj=(?P<obj>\S+) x=(?P<x>-?\d+) y=(?P<y>-?\d+) "
    r"dx=(?P<dx>-?\d+) dy=(?P<dy>-?\d+) shift=(?P<shift>-?\d+) "
    r"min=\((?P<minx>-?\d+),(?P<miny>-?\d+)\) max=\((?P<maxx>-?\d+),(?P<maxy>-?\d+)\)"
)
PLAYGAME_RE = re.compile(r"PLAYGAME .*scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\)")


INT_FIELDS = {
    "seq",
    "right_arg",
    "bottom_arg",
    "left_arg",
    "top_arg",
    "shift",
    "gameplay",
    "minx",
    "miny",
    "maxx",
    "maxy",
    "x",
    "y",
    "dx",
    "dy",
    "scrollx",
    "scrolly",
}


def convert(match: re.Match[str], line_no: int, kind: str) -> dict:
    row: dict[str, int | str] = {"kind": kind, "line_no": line_no}
    for key, value in match.groupdict().items():
        if value is None:
            continue
        row[key] = int(value) if key in INT_FIELDS else value
    return row


def parse_log(path: Path) -> dict[str, list[dict]]:
    rows = {
        "calls": [],
        "switch_entries": [],
        "entries": [],
        "sets": [],
        "mouse": [],
        "playgame": [],
        "av": [],
    }
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        call = CALL_RE.search(line)
        if call:
            rows["calls"].append(convert(call, line_no, call.group("kind")))
        switch_entry = SWITCH_ENTRY_RE.search(line)
        if switch_entry:
            rows["switch_entries"].append(convert(switch_entry, line_no, "VIEWPORT_SWITCH_ENTRY"))
        entry = VIEWPORT_ENTRY_RE.search(line)
        if entry:
            rows["entries"].append(convert(entry, line_no, "VIEWPORT_ENTRY"))
        viewport_set = VIEWPORT_SET_RE.search(line)
        if viewport_set:
            rows["sets"].append(convert(viewport_set, line_no, "VIEWPORT_SET"))
        mouse = MOUSE_RE.search(line)
        if mouse:
            rows["mouse"].append(convert(mouse, line_no, "MOUSE_BOUND"))
        playgame = PLAYGAME_RE.search(line)
        if playgame:
            rows["playgame"].append(convert(playgame, line_no, "PLAYGAME"))
        if line.strip() == "AV_VIEWPORT_BOUNDS":
            rows["av"].append({"kind": "AV_VIEWPORT_BOUNDS", "line_no": line_no})
    return rows


def unique_pairs(rows: list[dict], x_field: str, y_field: str) -> list[dict]:
    seen: dict[tuple[int, int], int] = {}
    for row in rows:
        key = (int(row[x_field]), int(row[y_field]))
        seen[key] = seen.get(key, 0) + 1
    return [{"x": x, "y": y, "count": count} for (x, y), count in sorted(seen.items())]


def first_last(rows: list[dict]) -> dict:
    return {"first": rows[:1], "last": rows[-1:] if rows else []}


def summarize(path: Path) -> dict:
    rows = parse_log(path)
    right_bottom_args = unique_pairs(rows["calls"] + rows["entries"], "right_arg", "bottom_arg")
    max_pairs = unique_pairs(rows["sets"], "maxx", "maxy")
    mouse_max_pairs = unique_pairs(rows["mouse"], "maxx", "maxy")
    gameplay_sets = [row for row in rows["sets"] if int(row.get("gameplay", 0))]
    final_set = rows["sets"][-1] if rows["sets"] else None
    final_mouse = rows["mouse"][-1] if rows["mouse"] else None
    summary = {
        "log": str(path),
        "call_rows": len(rows["calls"]),
        "switch_entry_rows": len(rows["switch_entries"]),
        "entry_rows": len(rows["entries"]),
        "set_rows": len(rows["sets"]),
        "mouse_rows": len(rows["mouse"]),
        "playgame_rows": len(rows["playgame"]),
        "av_rows": len(rows["av"]),
        "right_bottom_args": right_bottom_args,
        "max_pairs": max_pairs,
        "mouse_max_pairs": mouse_max_pairs,
        "native_640x480_call_seen": any(pair["x"] == 640 and pair["y"] == 480 for pair in right_bottom_args),
        "hd_800x600_call_seen": any(pair["x"] == 800 and pair["y"] == 600 for pair in right_bottom_args),
        "native_mouse_max_seen": any(pair["x"] == 610 and pair["y"] == 452 for pair in max_pairs + mouse_max_pairs),
        "hd_mouse_max_seen": any(pair["x"] >= 770 and pair["y"] >= 572 for pair in max_pairs + mouse_max_pairs),
        "final_set": rows["sets"][-1:] if rows["sets"] else [],
        "final_gameplay_set": gameplay_sets[-1:] if gameplay_sets else [],
        "final_mouse": rows["mouse"][-1:] if rows["mouse"] else [],
        "final_set_is_native_640x480": bool(final_set and final_set["maxx"] == 610 and final_set["maxy"] == 452),
        "final_set_is_hd_800x600": bool(final_set and final_set["maxx"] >= 770 and final_set["maxy"] >= 572),
        "final_mouse_is_native_640x480": bool(final_mouse and final_mouse["maxx"] == 610 and final_mouse["maxy"] == 452),
        "final_mouse_is_hd_800x600": bool(final_mouse and final_mouse["maxx"] >= 770 and final_mouse["maxy"] >= 572),
        "first_last_call": first_last(rows["calls"]),
        "first_last_set": first_last(rows["sets"]),
        "first_last_mouse": first_last(rows["mouse"]),
    }
    return summary


def print_summary(summary: dict) -> None:
    print(f"log: {summary['log']}")
    print(
        "rows: calls={call_rows} switch_entries={switch_entry_rows} entries={entry_rows} "
        "sets={set_rows} mouse={mouse_rows} playgame={playgame_rows} av={av_rows}".format(**summary)
    )
    print(f"right_bottom_args: {summary['right_bottom_args']}")
    print(f"max_pairs: {summary['max_pairs']}")
    print(f"mouse_max_pairs: {summary['mouse_max_pairs']}")
    print(f"native_640x480_call_seen: {summary['native_640x480_call_seen']}")
    print(f"hd_800x600_call_seen: {summary['hd_800x600_call_seen']}")
    print(f"native_mouse_max_seen: {summary['native_mouse_max_seen']}")
    print(f"hd_mouse_max_seen: {summary['hd_mouse_max_seen']}")
    if summary["final_set"]:
        print(f"final_set: {summary['final_set'][0]}")
        print(f"final_set_is_native_640x480: {summary['final_set_is_native_640x480']}")
        print(f"final_set_is_hd_800x600: {summary['final_set_is_hd_800x600']}")
    if summary["final_mouse"]:
        print(f"final_mouse: {summary['final_mouse'][0]}")
        print(f"final_mouse_is_native_640x480: {summary['final_mouse_is_native_640x480']}")
        print(f"final_mouse_is_hd_800x600: {summary['final_mouse_is_hd_800x600']}")
    if summary["final_gameplay_set"]:
        print(f"final_gameplay_set: {summary['final_gameplay_set'][0]}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize Clash95 viewport bounds CDB logs.")
    parser.add_argument("logs", nargs="+", type=Path)
    parser.add_argument("--write-json", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summaries = [summarize(path) for path in args.logs]
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summaries, indent=2), encoding="ascii")
    for index, summary in enumerate(summaries):
        if index:
            print()
        print_summary(summary)
    if len(summaries) == 2:
        print()
        print("comparison:")
        print(f"baseline_final_set: {summaries[0]['final_set']}")
        print(f"candidate_final_set: {summaries[1]['final_set']}")
        print(f"baseline_final_set_is_native_640x480: {summaries[0]['final_set_is_native_640x480']}")
        print(f"baseline_final_set_is_hd_800x600: {summaries[0]['final_set_is_hd_800x600']}")
        print(f"candidate_final_set_is_native_640x480: {summaries[1]['final_set_is_native_640x480']}")
        print(f"candidate_final_set_is_hd_800x600: {summaries[1]['final_set_is_hd_800x600']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
