#!/usr/bin/env python3
"""Summarize Clash95 CDB mouse-state probe logs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


MOUSE_RE = re.compile(
    r"MOUSE obj=(?P<obj>\S+) x=(?P<x>-?\d+) y=(?P<y>-?\d+) "
    r"rawx=0x(?P<rawx>[0-9a-fA-F]+) rawy=0x(?P<rawy>[0-9a-fA-F]+) "
    r"dx=(?P<dx>-?\d+) dy=(?P<dy>-?\d+) shift=(?P<shift>\d+) "
    r"speed=(?P<speed>-?\d+) buttons=(?P<buttons>-?\d+) "
    r"lbtn=0x(?P<lbtn>[0-9a-fA-F]+) rbtn=0x(?P<rbtn>[0-9a-fA-F]+) "
    r"min=\((?P<minx>-?\d+),(?P<miny>-?\d+)\) "
    r"max=\((?P<maxx>-?\d+),(?P<maxy>-?\d+)\)"
)

MENUHIT_RE = re.compile(
    r"MENUHIT (?:seq=(?P<seq>\d+) )?x=(?P<x>-?\d+) y=(?P<y>-?\d+) "
    r"rawx=0x(?P<rawx>[0-9a-fA-F]+) rawy=0x(?P<rawy>[0-9a-fA-F]+) "
    r"dx=(?P<dx>-?\d+) dy=(?P<dy>-?\d+) shift=(?P<shift>\d+) "
    r"lbtn=0x(?P<lbtn>[0-9a-fA-F]+) rbtn=0x(?P<rbtn>[0-9a-fA-F]+) "
    r"mask=(?P<mask>-?\d+) min=\((?P<minx>-?\d+),(?P<miny>-?\d+)\) "
    r"max=\((?P<maxx>-?\d+),(?P<maxy>-?\d+)\) "
    r"entry=0x(?P<entry>[0-9a-fA-F]+) ex=(?P<ex>-?\d+) ey=(?P<ey>-?\d+)"
)


INT_FIELDS = ("x", "y", "dx", "dy", "shift", "speed", "buttons", "minx", "miny", "maxx", "maxy")
HEX_FIELDS = ("rawx", "rawy", "lbtn", "rbtn")
MENUHIT_INT_FIELDS = ("x", "y", "dx", "dy", "shift", "mask", "minx", "miny", "maxx", "maxy", "ex", "ey")
MENUHIT_HEX_FIELDS = ("rawx", "rawy", "lbtn", "rbtn", "entry")


def parse_rows(text: str) -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        match = MOUSE_RE.search(line)
        if not match:
            continue
        row: dict[str, int | str] = {"kind": "MOUSE", "line_no": line_no, "obj": match.group("obj")}
        for field in INT_FIELDS:
            row[field] = int(match.group(field))
        for field in HEX_FIELDS:
            row[field] = int(match.group(field), 16)
        rows.append(row)
    return rows


def parse_menuhit_rows(text: str) -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        match = MENUHIT_RE.search(line)
        if not match:
            continue
        row: dict[str, int | str] = {"kind": "MENUHIT", "line_no": line_no}
        if match.group("seq") is not None:
            row["seq"] = int(match.group("seq"))
        for field in MENUHIT_INT_FIELDS:
            row[field] = int(match.group(field))
        for field in MENUHIT_HEX_FIELDS:
            row[field] = int(match.group(field), 16)
        rows.append(row)
    return rows


def range_summary(rows: list[dict[str, int | str]], field: str) -> dict[str, int]:
    values = [int(row[field]) for row in rows]
    return {"min": min(values), "max": max(values), "unique": len(set(values))}


def summarize(path: Path) -> dict:
    text = path.read_text(errors="replace")
    rows = parse_rows(text)
    menuhit_rows = parse_menuhit_rows(text)
    summary: dict = {
        "log": str(path),
        "mouse_rows": len(rows),
        "menuhit_rows": len(menuhit_rows),
    }
    if not rows and not menuhit_rows:
        return summary

    if rows:
        summary["ranges"] = {
            field: range_summary(rows, field)
            for field in ("x", "y", "dx", "dy", "rawx", "rawy", "buttons", "lbtn", "rbtn")
        }
        summary["objects"] = sorted({str(row["obj"]) for row in rows})
        summary["max_bounds_seen"] = {
            "x": max(int(row["maxx"]) for row in rows),
            "y": max(int(row["maxy"]) for row in rows),
        }
        summary["final_max_bounds"] = {
            "x": int(rows[-1]["maxx"]),
            "y": int(rows[-1]["maxy"]),
        }
        summary["preclamp_over_bounds"] = sum(
            1 for row in rows if int(row["x"]) > int(row["maxx"]) or int(row["y"]) > int(row["maxy"])
        )
        summary["preclamp_at_final_max"] = sum(
            1
            for row in rows
            if int(row["x"]) == summary["final_max_bounds"]["x"]
            and int(row["y"]) == summary["final_max_bounds"]["y"]
        )
        summary["zero_delta_rows"] = sum(1 for row in rows if int(row["dx"]) == 0 and int(row["dy"]) == 0)
        summary["button_rows"] = sum(1 for row in rows if int(row["buttons"]) != 0)
        summary["left_button_rows"] = sum(1 for row in rows if int(row["lbtn"]) != 0)
        summary["right_button_rows"] = sum(1 for row in rows if int(row["rbtn"]) != 0)
        summary["first_rows"] = rows[:5]
        summary["last_rows"] = rows[-5:]
    if menuhit_rows:
        menuhit_range_fields = ["x", "y", "dx", "dy", "rawx", "rawy", "lbtn", "rbtn", "mask", "entry", "ex", "ey"]
        if "seq" in menuhit_rows[0]:
            menuhit_range_fields.insert(0, "seq")
        summary["menuhit_ranges"] = {
            field: range_summary(menuhit_rows, field)
            for field in menuhit_range_fields
        }
        entry_counts: dict[tuple[int, int, int], int] = {}
        for row in menuhit_rows:
            key = (int(row["entry"]), int(row["ex"]), int(row["ey"]))
            entry_counts[key] = entry_counts.get(key, 0) + 1
        summary["menuhit_entries"] = [
            {"entry": entry, "ex": ex, "ey": ey, "count": count}
            for (entry, ex, ey), count in sorted(entry_counts.items(), key=lambda item: item[1], reverse=True)
        ]
        summary["menuhit_button_rows"] = sum(
            1 for row in menuhit_rows if int(row["lbtn"]) != 0 or int(row["rbtn"]) != 0
        )
        summary["menuhit_over_bounds"] = sum(
            1
            for row in menuhit_rows
            if int(row["x"]) > int(row["maxx"])
            or int(row["y"]) > int(row["maxy"])
            or int(row["x"]) < int(row["minx"])
            or int(row["y"]) < int(row["miny"])
        )
        summary["menuhit_first_rows"] = menuhit_rows[:5]
        summary["menuhit_last_rows"] = menuhit_rows[-5:]
    return summary


def print_summary(summary: dict) -> None:
    print(f"log: {summary['log']}")
    print(f"mouse_rows: {summary['mouse_rows']}")
    print(f"menuhit_rows: {summary['menuhit_rows']}")
    if summary["mouse_rows"]:
        for field, values in summary["ranges"].items():
            print(f"{field}: min={values['min']} max={values['max']} unique={values['unique']}")
        print(f"final_max_bounds: {summary['final_max_bounds']}")
        print(f"preclamp_over_bounds: {summary['preclamp_over_bounds']}")
        print(f"preclamp_at_final_max: {summary['preclamp_at_final_max']}")
        print(f"zero_delta_rows: {summary['zero_delta_rows']}")
        print(
            "button_rows: {button_rows} left_button_rows: {left_button_rows} "
            "right_button_rows: {right_button_rows}".format(**summary)
        )
    if summary["menuhit_rows"]:
        print(f"menuhit_button_rows: {summary['menuhit_button_rows']}")
        print(f"menuhit_over_bounds: {summary['menuhit_over_bounds']}")
        for field, values in summary["menuhit_ranges"].items():
            print(f"menuhit_{field}: min={values['min']} max={values['max']} unique={values['unique']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize Clash95 CDB mouse-state probe logs.")
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
