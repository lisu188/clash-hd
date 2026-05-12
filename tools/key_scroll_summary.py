#!/usr/bin/env python3
"""Summarize Clash95 key-state scroll CDB probe logs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REDRAW_RE = re.compile(
    r"KEYSCROLL_REDRAW seq=(?P<seq>\d+) scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"end12=\((?P<endx>-?\d+),(?P<endy>-?\d+)\) map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) "
    r"max_hd=\((?P<hdx>-?\d+),(?P<hdy>-?\d+)\) max_old=\((?P<oldx>-?\d+),(?P<oldy>-?\d+)\)"
)
ENTRY_RE = re.compile(
    r"KEYSCROLL_ENTRY seq=(?P<seq>\d+) scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) max_hd=\((?P<hdx>-?\d+),(?P<hdy>-?\d+)\) "
    r"max_old=\((?P<oldx>-?\d+),(?P<oldy>-?\d+)\) keys right=(?P<right>[0-9a-fA-F]+) "
    r"down=(?P<down>[0-9a-fA-F]+)"
)
BRANCH_RE = re.compile(
    r"(?P<kind>KEYSCROLL_RIGHT|KEYSCROLL_DOWN) seq=(?P<seq>\d+) "
    r"scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\)"
)
INVOKE_RE = re.compile(
    r"KEYSCROLL_INVOKE_HELPER seq=(?P<seq>\d+) reason=(?P<reason>[xy]) "
    r"scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"max_hd=\((?P<hdx>-?\d+),(?P<hdy>-?\d+)\)"
)
BOUNDARY_READY_RE = re.compile(
    r"KEYSCROLL_BOUNDARY_READY invokes=(?P<invokes>\d+) "
    r"scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"max_hd=\((?P<hdx>-?\d+),(?P<hdy>-?\d+)\)"
)
PLAYGAME_RE = re.compile(
    r"KEYSCROLL_PLAYGAME gd=(?P<gd>\S+) map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) "
    r"scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\)"
)

INT_FIELDS = {
    "seq",
    "scrollx",
    "scrolly",
    "endx",
    "endy",
    "mapw",
    "maph",
    "hdx",
    "hdy",
    "oldx",
    "oldy",
    "invokes",
}


def convert(match: re.Match[str], line_no: int, kind: str) -> dict:
    row: dict[str, int | str] = {"kind": kind, "line_no": line_no}
    for key, value in match.groupdict().items():
        if value is None:
            continue
        if key in INT_FIELDS:
            row[key] = int(value)
        elif key in {"right", "down"}:
            row[key] = int(value, 16)
        else:
            row[key] = value
    return row


def parse_log(path: Path) -> dict[str, list[dict]]:
    rows: dict[str, list[dict]] = {
        "playgame": [],
        "entry": [],
        "right": [],
        "down": [],
        "invoke": [],
        "boundary_ready": [],
        "redraw": [],
        "av": [],
    }
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        playgame = PLAYGAME_RE.search(line)
        if playgame:
            rows["playgame"].append(convert(playgame, line_no, "KEYSCROLL_PLAYGAME"))
            continue
        entry = ENTRY_RE.search(line)
        if entry:
            rows["entry"].append(convert(entry, line_no, "KEYSCROLL_ENTRY"))
            continue
        branch = BRANCH_RE.search(line)
        if branch:
            bucket = "right" if branch.group("kind") == "KEYSCROLL_RIGHT" else "down"
            rows[bucket].append(convert(branch, line_no, branch.group("kind")))
            continue
        invoke = INVOKE_RE.search(line)
        if invoke:
            rows["invoke"].append(convert(invoke, line_no, "KEYSCROLL_INVOKE_HELPER"))
            continue
        boundary_ready = BOUNDARY_READY_RE.search(line)
        if boundary_ready:
            rows["boundary_ready"].append(convert(boundary_ready, line_no, "KEYSCROLL_BOUNDARY_READY"))
            continue
        redraw = REDRAW_RE.search(line)
        if redraw:
            rows["redraw"].append(convert(redraw, line_no, "KEYSCROLL_REDRAW"))
            continue
        if line.strip() == "AV_KEYSCROLL":
            rows["av"].append({"kind": "AV_KEYSCROLL", "line_no": line_no})
    return rows


def unique_pairs(rows: list[dict], x_field: str = "scrollx", y_field: str = "scrolly") -> list[dict]:
    counts: dict[tuple[int, int], int] = {}
    for row in rows:
        key = (int(row[x_field]), int(row[y_field]))
        counts[key] = counts.get(key, 0) + 1
    return [{"x": x, "y": y, "count": count} for (x, y), count in sorted(counts.items())]


def summarize(path: Path) -> dict:
    rows = parse_log(path)
    redraws = rows["redraw"]
    boundary_rows = [
        row for row in redraws
        if int(row["scrollx"]) == int(row["hdx"]) and int(row["scrolly"]) == int(row["hdy"])
    ]
    overrun_rows = [
        row for row in redraws
        if int(row["endx"]) > int(row["mapw"]) or int(row["endy"]) > int(row["maph"])
    ]
    old_overflow_rows = [
        row for row in redraws
        if int(row["oldx"]) + 12 > int(row["mapw"]) or int(row["oldy"]) + 9 > int(row["maph"])
    ]
    return {
        "log": str(path),
        "playgame_rows": len(rows["playgame"]),
        "entry_rows": len(rows["entry"]),
        "right_rows": len(rows["right"]),
        "down_rows": len(rows["down"]),
        "invoke_rows": len(rows["invoke"]),
        "boundary_ready_rows": len(rows["boundary_ready"]),
        "redraw_rows": len(redraws),
        "av_rows": len(rows["av"]),
        "scroll_values": unique_pairs(redraws),
        "right_values": unique_pairs(rows["right"]),
        "down_values": unique_pairs(rows["down"]),
        "invoke_values": unique_pairs(rows["invoke"]),
        "boundary_rows": boundary_rows[:5],
        "boundary_ready": rows["boundary_ready"][:5],
        "boundary_reached": bool(boundary_rows),
        "overrun_rows": overrun_rows[:5],
        "overrun_count": len(overrun_rows),
        "old_overflow_risk_count": len(old_overflow_rows),
        "first_playgame": rows["playgame"][:1],
        "first_entry": rows["entry"][:1],
        "first_redraw": redraws[:1],
        "final_redraw": redraws[-1:] if redraws else [],
    }


def print_summary(summary: dict) -> None:
    print(f"log: {summary['log']}")
    print(
        "rows: playgame={playgame_rows} entry={entry_rows} right={right_rows} "
        "down={down_rows} invoke={invoke_rows} boundary_ready={boundary_ready_rows} "
        "redraw={redraw_rows} av={av_rows}".format(**summary)
    )
    print(f"boundary_reached: {summary['boundary_reached']}")
    print(f"overrun_count: {summary['overrun_count']}")
    print(f"old_overflow_risk_count: {summary['old_overflow_risk_count']}")
    if summary["first_playgame"]:
        print(f"first_playgame: {summary['first_playgame'][0]}")
    if summary["first_entry"]:
        print(f"first_entry: {summary['first_entry'][0]}")
    if summary["first_redraw"]:
        print(f"first_redraw: {summary['first_redraw'][0]}")
    if summary["final_redraw"]:
        print(f"final_redraw: {summary['final_redraw'][0]}")
    print(f"boundary_rows: {summary['boundary_rows']}")
    print(f"boundary_ready: {summary['boundary_ready']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize key-state scroll CDB probe logs.")
    parser.add_argument("log", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--require-hd-boundary", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = summarize(args.log)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2), encoding="ascii")
    print_summary(summary)
    if args.require_hd_boundary and (not summary["boundary_reached"] or summary["overrun_count"]):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
