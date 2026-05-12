#!/usr/bin/env python3
"""Summarize Clash95 CDB minimap action probe logs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ENTRY_RE = re.compile(
    r"ACTION_ENTRY seq=(?P<seq>\d+) flip=(?P<flip>-?\d+) active=(?P<active>-?\d+) "
    r"player=(?P<player>-?\d+) scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\) "
    r"minimap=\((?P<left>-?\d+),(?P<top>-?\d+),(?P<right>-?\d+),(?P<bottom>-?\d+)\) "
    r"lbtn=0x(?P<lbtn>[0-9a-fA-F]+) rbtn=0x(?P<rbtn>[0-9a-fA-F]+)"
)
COMPUTED_RE = re.compile(
    r"ACTION_COMPUTED seq=(?P<seq>\d+) target=\((?P<targetx>-?\d+),(?P<targety>-?\d+)\) "
    r"current=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) active=(?P<active>-?\d+) "
    r"map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\) "
    r"minimap=\((?P<left>-?\d+),(?P<top>-?\d+),(?P<right>-?\d+),(?P<bottom>-?\d+)\) "
    r"lbtn=0x(?P<lbtn>[0-9a-fA-F]+) rbtn=0x(?P<rbtn>[0-9a-fA-F]+)"
)
ACCEPT_RE = re.compile(
    r"ACTION_ACCEPT seq=(?P<seq>\d+) target=\((?P<targetx>-?\d+),(?P<targety>-?\d+)\) "
    r"current=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) max_native=\((?P<maxx>-?\d+),(?P<maxy>-?\d+)\) "
    r"map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\) "
    r"active=(?P<active>-?\d+) lbtn=0x(?P<lbtn>[0-9a-fA-F]+) rbtn=0x(?P<rbtn>[0-9a-fA-F]+)"
)
CLAMP_X_RE = re.compile(
    r"ACTION_CLAMP_X seq=(?P<seq>\d+) target=(?P<targetx>-?\d+) clamp=(?P<clampx>-?\d+) "
    r"target_y=(?P<targety>-?\d+) map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\) active=(?P<active>-?\d+) "
    r"lbtn=0x(?P<lbtn>[0-9a-fA-F]+) rbtn=0x(?P<rbtn>[0-9a-fA-F]+)"
)
WRITE_X_RE = re.compile(
    r"ACTION_WRITE_X seq=(?P<seq>\d+) write=(?P<writex>-?\d+) target_y=(?P<targety>-?\d+) "
    r"before=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) max_native=\((?P<maxx>-?\d+),(?P<maxy>-?\d+)\) "
    r"map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\) "
    r"active=(?P<active>-?\d+) lbtn=0x(?P<lbtn>[0-9a-fA-F]+) rbtn=0x(?P<rbtn>[0-9a-fA-F]+)"
)
CLAMP_Y_RE = re.compile(
    r"ACTION_CLAMP_Y seq=(?P<seq>\d+) requested=(?P<requestedy>-?\d+) clamp=(?P<clampy>-?\d+) "
    r"current_x=(?P<currentx>-?\d+) map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\) active=(?P<active>-?\d+) "
    r"lbtn=0x(?P<lbtn>[0-9a-fA-F]+) rbtn=0x(?P<rbtn>[0-9a-fA-F]+)"
)
FINAL_RE = re.compile(
    r"ACTION_FINAL seq=(?P<seq>\d+) scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"max_native=\((?P<maxx>-?\d+),(?P<maxy>-?\d+)\) map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\) active=(?P<active>-?\d+) "
    r"lbtn=0x(?P<lbtn>[0-9a-fA-F]+) rbtn=0x(?P<rbtn>[0-9a-fA-F]+)"
)
ACTIVE_TOGGLE_RE = re.compile(
    r"MINIMAP_ACTIVE_TOGGLE seq=(?P<seq>\d+) player=(?P<player>-?\d+) active=(?P<active>-?\d+) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\) scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"lbtn=0x(?P<lbtn>[0-9a-fA-F]+) rbtn=0x(?P<rbtn>[0-9a-fA-F]+)"
)
ACTIVE_SET_RE = re.compile(
    r"MINIMAP_ACTIVE_SET seq=(?P<seq>\d+) player=(?P<player>-?\d+) active=(?P<active>-?\d+) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\) scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"lbtn=0x(?P<lbtn>[0-9a-fA-F]+) rbtn=0x(?P<rbtn>[0-9a-fA-F]+)"
)
PLAYGAME_RE = re.compile(
    r"PLAYGAME gd=(?P<gd>\S+) map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) "
    r"scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\) "
    r"minimap=\((?P<left>-?\d+),(?P<top>-?\d+),(?P<right>-?\d+),(?P<bottom>-?\d+)\) "
    r"player=(?P<player>-?\d+) active=(?P<active>-?\d+) lbtn=0x(?P<lbtn>[0-9a-fA-F]+) rbtn=0x(?P<rbtn>[0-9a-fA-F]+)"
)

INT_FIELDS = {
    "seq",
    "flip",
    "active",
    "player",
    "scrollx",
    "scrolly",
    "mapw",
    "maph",
    "mousex",
    "mousey",
    "left",
    "top",
    "right",
    "bottom",
    "targetx",
    "targety",
    "maxx",
    "maxy",
    "clampx",
    "writex",
    "requestedy",
    "clampy",
    "currentx",
}
HEX_FIELDS = {"lbtn", "rbtn"}


def convert(match: re.Match[str], line_no: int, kind: str) -> dict:
    row: dict[str, int | str] = {"line_no": line_no, "kind": kind}
    for key, value in match.groupdict().items():
        if value is None:
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
        "playgame": [],
        "entry": [],
        "computed": [],
        "accept": [],
        "clamp_x": [],
        "write_x": [],
        "clamp_y": [],
        "final": [],
        "active_toggle": [],
        "active_set": [],
        "av": [],
    }
    patterns = [
        ("playgame", PLAYGAME_RE, "PLAYGAME"),
        ("entry", ENTRY_RE, "ACTION_ENTRY"),
        ("computed", COMPUTED_RE, "ACTION_COMPUTED"),
        ("accept", ACCEPT_RE, "ACTION_ACCEPT"),
        ("clamp_x", CLAMP_X_RE, "ACTION_CLAMP_X"),
        ("write_x", WRITE_X_RE, "ACTION_WRITE_X"),
        ("clamp_y", CLAMP_Y_RE, "ACTION_CLAMP_Y"),
        ("final", FINAL_RE, "ACTION_FINAL"),
        ("active_toggle", ACTIVE_TOGGLE_RE, "MINIMAP_ACTIVE_TOGGLE"),
        ("active_set", ACTIVE_SET_RE, "MINIMAP_ACTIVE_SET"),
    ]
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        matched = False
        for bucket, pattern, kind in patterns:
            match = pattern.search(line)
            if match:
                rows[bucket].append(convert(match, line_no, kind))
                matched = True
                break
        if not matched and line.strip() == "AV_MINIMAP_ACTION":
            rows["av"].append({"line_no": line_no, "kind": "AV_MINIMAP_ACTION"})
    return rows


def range_summary(rows: list[dict], field: str) -> dict[str, int] | None:
    values = [int(row[field]) for row in rows if field in row]
    if not values:
        return None
    return {"min": min(values), "max": max(values), "unique": len(set(values))}


def unique_pairs(rows: list[dict], x_field: str, y_field: str, label_x: str = "x", label_y: str = "y") -> list[dict]:
    counts: dict[tuple[int, int], int] = {}
    for row in rows:
        key = (int(row[x_field]), int(row[y_field]))
        counts[key] = counts.get(key, 0) + 1
    return [
        {label_x: key[0], label_y: key[1], "count": count}
        for key, count in sorted(counts.items())
    ]


def summarize(path: Path) -> dict:
    rows = parse_log(path)
    final_scrolls = unique_pairs(rows["final"], "scrollx", "scrolly", "x", "y")
    accepted_targets = unique_pairs(rows["accept"], "targetx", "targety", "x", "y")
    computed_targets = unique_pairs(rows["computed"], "targetx", "targety", "x", "y")
    toggles_on = [row for row in rows["active_toggle"] if int(row["active"]) != 0]
    sets_on = [row for row in rows["active_set"] if int(row["active"]) != 0]
    active_entry_rows = [row for row in rows["entry"] if int(row["active"]) != 0]
    summary = {
        "log": str(path),
        "playgame_rows": len(rows["playgame"]),
        "entry_rows": len(rows["entry"]),
        "active_entry_rows": len(active_entry_rows),
        "computed_rows": len(rows["computed"]),
        "accept_rows": len(rows["accept"]),
        "clamp_x_rows": len(rows["clamp_x"]),
        "write_x_rows": len(rows["write_x"]),
        "clamp_y_rows": len(rows["clamp_y"]),
        "final_rows": len(rows["final"]),
        "active_toggle_rows": len(rows["active_toggle"]),
        "active_set_rows": len(rows["active_set"]),
        "active_toggle_on_rows": len(toggles_on),
        "active_set_on_rows": len(sets_on),
        "av_rows": len(rows["av"]),
        "entry_active_values": sorted({int(row["active"]) for row in rows["entry"]}),
        "toggle_active_values": sorted({int(row["active"]) for row in rows["active_toggle"]}),
        "set_active_values": sorted({int(row["active"]) for row in rows["active_set"]}),
        "computed_target_values": computed_targets,
        "accepted_target_values": accepted_targets,
        "final_scroll_values": final_scrolls,
        "computed_target_x_range": range_summary(rows["computed"], "targetx"),
        "computed_target_y_range": range_summary(rows["computed"], "targety"),
        "entry_mouse_x_range": range_summary(rows["entry"], "mousex"),
        "entry_mouse_y_range": range_summary(rows["entry"], "mousey"),
        "first_playgame": rows["playgame"][:1],
        "first_entry": rows["entry"][:1],
        "first_computed": rows["computed"][:1],
        "first_accept": rows["accept"][:1],
        "first_clamp_x": rows["clamp_x"][:1],
        "first_write_x": rows["write_x"][:1],
        "first_clamp_y": rows["clamp_y"][:1],
        "first_final": rows["final"][:1],
        "first_active_toggle": rows["active_toggle"][:1],
        "first_active_set": rows["active_set"][:1],
        "last_final": rows["final"][-1:] if rows["final"] else [],
    }
    summary["action_path_reached"] = summary["computed_rows"] > 0
    summary["write_path_reached"] = summary["write_x_rows"] > 0 or summary["clamp_x_rows"] > 0
    summary["scroll_changed"] = len(summary["final_scroll_values"]) > 1
    if summary["first_entry"] and summary["first_final"]:
        entry_row = summary["first_entry"][0]
        final_rows = rows["final"]
        summary["any_final_diff_from_first_entry"] = any(
            int(row["scrollx"]) != int(entry_row["scrollx"]) or int(row["scrolly"]) != int(entry_row["scrolly"])
            for row in final_rows
        )
    else:
        summary["any_final_diff_from_first_entry"] = False
    return summary


def print_summary(summary: dict) -> None:
    print(f"log: {summary['log']}")
    print(
        "rows: playgame={playgame_rows} entry={entry_rows} active_entry={active_entry_rows} "
        "computed={computed_rows} accept={accept_rows} write_x={write_x_rows} "
        "clamp_x={clamp_x_rows} clamp_y={clamp_y_rows} final={final_rows} "
        "toggle={active_toggle_rows} set={active_set_rows} av={av_rows}".format(**summary)
    )
    print(f"entry_active_values: {summary['entry_active_values']}")
    print(f"toggle_active_values: {summary['toggle_active_values']}")
    print(f"set_active_values: {summary['set_active_values']}")
    print(f"action_path_reached: {summary['action_path_reached']}")
    print(f"write_path_reached: {summary['write_path_reached']}")
    print(f"scroll_changed: {summary['scroll_changed']}")
    print(f"any_final_diff_from_first_entry: {summary['any_final_diff_from_first_entry']}")
    print(f"computed_target_values: {summary['computed_target_values']}")
    print(f"accepted_target_values: {summary['accepted_target_values']}")
    print(f"final_scroll_values: {summary['final_scroll_values']}")
    if summary["first_entry"]:
        print(f"first_entry: {summary['first_entry'][0]}")
    if summary["first_computed"]:
        print(f"first_computed: {summary['first_computed'][0]}")
    if summary["first_accept"]:
        print(f"first_accept: {summary['first_accept'][0]}")
    if summary["first_write_x"]:
        print(f"first_write_x: {summary['first_write_x'][0]}")
    if summary["first_clamp_x"]:
        print(f"first_clamp_x: {summary['first_clamp_x'][0]}")
    if summary["first_clamp_y"]:
        print(f"first_clamp_y: {summary['first_clamp_y'][0]}")
    if summary["first_final"]:
        print(f"first_final: {summary['first_final'][0]}")
    if summary["first_active_toggle"]:
        print(f"first_active_toggle: {summary['first_active_toggle'][0]}")
    if summary["first_active_set"]:
        print(f"first_active_set: {summary['first_active_set'][0]}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize a Clash95 minimap action CDB probe.")
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
